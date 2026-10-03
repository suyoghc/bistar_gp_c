"""
BMS* (Bayesian Model Selection Star) implementation.

Extends Bayesian induction (Chandramouli & Shiffrin, 2016) by:
1. Using GP hyperpriors to define prior/posterior over data distributions (ψ)
2. Computing divergence G between GP posterior samples and candidate model predictions
3. Soft transfer: transferring GP-derived posteriors onto candidate model instances

Supports: KL(ψ||θ), KL(θ||ψ), Symmetric KL, Hellinger distance
"""

import logging

import numpy as np
import torch
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

torch.set_default_dtype(torch.float64)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# Divergence Metrics for Multivariate Gaussians
# ═══════════════════════════════════════════════════════════════════

def _safe_logdet(M):
    """Log determinant via Cholesky with jitter fallback."""
    n = M.shape[0]
    for jitter in [0.0, 1e-10, 1e-8, 1e-6, 1e-4]:
        try:
            L = np.linalg.cholesky(M + jitter * np.eye(n))
            return 2.0 * np.sum(np.log(np.diag(L)))
        except np.linalg.LinAlgError:
            continue
    # Fallback: use eigenvalues
    eigs = np.linalg.eigvalsh(M)
    eigs = np.maximum(eigs, 1e-10)
    return np.sum(np.log(eigs))


def _safe_solve(A, B):
    """Solve A x = B with regularization fallback."""
    n = A.shape[0]
    for jitter in [0.0, 1e-10, 1e-8, 1e-6, 1e-4]:
        try:
            return np.linalg.solve(A + jitter * np.eye(n), B)
        except np.linalg.LinAlgError:
            continue
    return np.linalg.lstsq(A, B, rcond=None)[0]


def kl_divergence(mu_p, cov_p, mu_q, cov_q):
    """
    KL(p || q) for multivariate Gaussians.
    p = N(mu_p, cov_p), q = N(mu_q, cov_q)

    KL(p||q) = 0.5 * [tr(Σ_q^{-1} Σ_p) + (μ_q - μ_p)^T Σ_q^{-1} (μ_q - μ_p)
                       - k + ln(|Σ_q| / |Σ_p|)]
    """
    k = len(mu_p)
    diff = mu_q - mu_p

    cov_q_inv_cov_p = _safe_solve(cov_q, cov_p)
    cov_q_inv_diff = _safe_solve(cov_q, diff)

    trace_term = np.trace(cov_q_inv_cov_p)
    quad_term = diff @ cov_q_inv_diff
    logdet_term = _safe_logdet(cov_q) - _safe_logdet(cov_p)

    return 0.5 * (trace_term + quad_term - k + logdet_term)


def kl_forward(mu_psi, cov_psi, mu_theta, cov_theta):
    """KL(ψ || θ): 'if ψ is true, how much info is lost using θ?'"""
    return kl_divergence(mu_psi, cov_psi, mu_theta, cov_theta)


def kl_backward(mu_psi, cov_psi, mu_theta, cov_theta):
    """KL(θ || ψ): 'if θ is true, how surprised would ψ be?'"""
    return kl_divergence(mu_theta, cov_theta, mu_psi, cov_psi)


def kl_symmetric(mu_psi, cov_psi, mu_theta, cov_theta):
    """Jeffreys divergence: (KL(ψ||θ) + KL(θ||ψ)) / 2"""
    return 0.5 * (kl_forward(mu_psi, cov_psi, mu_theta, cov_theta) +
                  kl_backward(mu_psi, cov_psi, mu_theta, cov_theta))


def bhattacharyya_distance(mu_p, cov_p, mu_q, cov_q):
    """
    Bhattacharyya distance between two Gaussians.
    D_B = (1/8)(μ_p - μ_q)^T Σ^{-1} (μ_p - μ_q) + (1/2) ln(|Σ| / sqrt(|Σ_p||Σ_q|))
    where Σ = (Σ_p + Σ_q) / 2
    """
    cov_avg = 0.5 * (cov_p + cov_q)
    diff = mu_p - mu_q

    cov_avg_inv_diff = _safe_solve(cov_avg, diff)
    quad_term = 0.125 * diff @ cov_avg_inv_diff

    logdet_avg = _safe_logdet(cov_avg)
    logdet_p = _safe_logdet(cov_p)
    logdet_q = _safe_logdet(cov_q)
    logdet_term = 0.5 * (logdet_avg - 0.5 * (logdet_p + logdet_q))

    return quad_term + logdet_term


def hellinger_distance(mu_psi, cov_psi, mu_theta, cov_theta):
    """
    Squared Hellinger distance: H^2 = 1 - exp(-D_B)
    Bounded in [0, 1], symmetric, proper metric.
    """
    db = bhattacharyya_distance(mu_psi, cov_psi, mu_theta, cov_theta)
    return 1.0 - np.exp(-db)


# ═══════════════════════════════════════════════════════════════════
# Pointwise Divergence Metrics (univariate, averaged over locations)
# ═══════════════════════════════════════════════════════════════════
#
# Joint metrics on n-dimensional Gaussians are dominated by covariance
# structure in high dimensions. Pointwise metrics strip this out:
# compare marginals N(μ_k, σ²_k) at each location k, then average.
# This isolates *mean accuracy* from covariance structure mismatch.

def _scalar_kl(mu_p, var_p, mu_q, var_q):
    """KL(p || q) for univariate Gaussians."""
    return 0.5 * (np.log(var_q / var_p) + var_p / var_q + (mu_p - mu_q)**2 / var_q - 1.0)


def _scalar_hellinger(mu_p, var_p, mu_q, var_q):
    """Squared Hellinger distance for univariate Gaussians."""
    db = 0.25 * np.log(0.25 * (var_p / var_q + var_q / var_p + 2)) + \
         0.25 * (mu_p - mu_q)**2 / (var_p + var_q)
    return 1.0 - np.exp(-db)


def _extract_marginals(mu, cov):
    """Extract pointwise means and variances from (mu, cov)."""
    var = np.diag(cov).copy()
    var = np.maximum(var, 1e-10)  # numerical safety
    return mu, var


def pw_kl_forward(mu_psi, cov_psi, mu_theta, cov_theta):
    """Pointwise KL(ψ_k || θ_k), averaged over locations."""
    mu_p, var_p = _extract_marginals(mu_psi, cov_psi)
    mu_q, var_q = _extract_marginals(mu_theta, cov_theta)
    return np.mean(_scalar_kl(mu_p, var_p, mu_q, var_q))


def pw_kl_backward(mu_psi, cov_psi, mu_theta, cov_theta):
    """Pointwise KL(θ_k || ψ_k), averaged over locations."""
    mu_p, var_p = _extract_marginals(mu_psi, cov_psi)
    mu_q, var_q = _extract_marginals(mu_theta, cov_theta)
    return np.mean(_scalar_kl(mu_q, var_q, mu_p, var_p))


def pw_kl_symmetric(mu_psi, cov_psi, mu_theta, cov_theta):
    """Pointwise symmetric KL, averaged over locations."""
    return 0.5 * (pw_kl_forward(mu_psi, cov_psi, mu_theta, cov_theta) +
                  pw_kl_backward(mu_psi, cov_psi, mu_theta, cov_theta))


def pw_hellinger(mu_psi, cov_psi, mu_theta, cov_theta):
    """Pointwise squared Hellinger, averaged over locations."""
    mu_p, var_p = _extract_marginals(mu_psi, cov_psi)
    mu_q, var_q = _extract_marginals(mu_theta, cov_theta)
    return np.mean(_scalar_hellinger(mu_p, var_p, mu_q, var_q))


def pw_mse(mu_psi, cov_psi, mu_theta, cov_theta):
    """
    Pointwise mean squared error (ignores variance entirely).
    Pure mean-accuracy baseline — no distributional comparison.
    """
    return np.mean((mu_psi - mu_theta)**2)


def pw_nll(mu_psi, cov_psi, mu_theta, cov_theta):
    """
    Pointwise negative log-likelihood of ψ means under θ marginals.
    Equivalent to: how well does θ's predictive distribution cover ψ's mean?
    Sensitive to both mean accuracy and calibration.
    """
    mu_p, _ = _extract_marginals(mu_psi, cov_psi)
    mu_q, var_q = _extract_marginals(mu_theta, cov_theta)
    return np.mean(0.5 * np.log(2 * np.pi * var_q) + 0.5 * (mu_p - mu_q)**2 / var_q)


# Registry of available metrics
class _MetricRegistry(dict):
    """METRICS[name] imports the v2 metrics on the first miss (FIX-7), so the
    primary metric pw_kl_vcal, defined in metrics_v2, resolves for a caller
    that never imported that module (ExperimentConfig.metrics names it).
    Registered names resolve exactly as in a plain dict; .keys() on the
    implicit run_bms_star path lists v2 names only after their first import,
    as before."""

    def __missing__(self, name):
        from . import metrics_v2  # noqa: F401  registers into this dict
        if name in self:
            return dict.__getitem__(self, name)
        raise KeyError(f"unknown metric {name!r}; registered: {sorted(self)}")


METRICS = _MetricRegistry({
    # Joint (full n-dimensional Gaussian)
    "kl_forward": kl_forward,       # KL(ψ || θ)
    "kl_backward": kl_backward,     # KL(θ || ψ)
    "kl_symmetric": kl_symmetric,   # Jeffreys divergence
    "hellinger": hellinger_distance, # H^2(ψ, θ)
    # Pointwise (univariate marginals, averaged)
    "pw_kl_forward": pw_kl_forward,
    "pw_kl_backward": pw_kl_backward,
    "pw_kl_symmetric": pw_kl_symmetric,
    "pw_hellinger": pw_hellinger,
    "pw_mse": pw_mse,               # mean-only baseline
    "pw_nll": pw_nll,               # mean + variance calibration
})


# ═══════════════════════════════════════════════════════════════════
# GP Predictive Extraction from HMC Samples
# ═══════════════════════════════════════════════════════════════════

@dataclass
class GPPosteriorSample:
    """One draw from the GP posterior over data distributions (one ψ)."""
    mean: np.ndarray       # (n_eval,)
    cov: np.ndarray        # (n_eval, n_eval)
    hyperparameters: Dict[str, float]


class PredictiveList(list):
    """List of GPPosteriorSample with draw-integrity bookkeeping (FIX-1).

    Behaves exactly like the plain list it replaces (len, iteration, indexing,
    truthiness) and additionally records which draw indices were attempted,
    which were retained, and why any were dropped, so a caller can see when
    the returned ensemble is a numerically selected subset of the draws.
    """

    def __init__(self, items=(), attempted_indices=None, retained_indices=None,
                 dropped=None):
        super().__init__(items)
        self.attempted_indices = list(attempted_indices or [])
        self.retained_indices = list(retained_indices or [])
        self.dropped = list(dropped or [])   # (draw index, reason) pairs

    @property
    def n_dropped(self):
        return len(self.dropped)


def extract_gp_predictives(model, likelihood, x_train, y_train, x_eval,
                           mcmc_samples, kernel_builder,
                           likelihood_builder=None,
                           n_posterior_samples=200, jitter=1e-4,
                           condition_on_data=True, rng=None, strict=True):
    """
    Extract full GP predictive distributions for each hyperparameter sample.

    Each sample defines a specific GP with specific hyperparameters,
    which implies a specific multivariate Gaussian over y at x_eval.
    These are the ψ's in BMS*.

    condition_on_data selects which predictive, so the SAME machinery serves both
    Bayesian-workflow checks:
      True  (default): POSTERIOR predictive p(y* | X, y, θ) — condition on the
             training data. Feed fit_hmc posterior draws → posterior predictive check.
      False: PRIOR predictive p(y* | θ) — the GP prior at x_eval (ZeroMean → mean 0,
             cov K_θθ(x_eval) + σ²I), no conditioning on y. Feed sample_prior draws
             → prior predictive check. x_train/y_train are then unused.

    Args:
        model: fitted AdditiveGPModel (for component_names)
        likelihood: fitted likelihood
        x_train, y_train: training data (used only when condition_on_data=True)
        x_eval: evaluation points
        mcmc_samples: dict from fit_hmc (posterior) or sample_prior (prior)
        kernel_builder: callable returning (kernels, names)
        likelihood_builder: callable returning a likelihood. If None, uses
                           default with Positive() constraint.
        n_posterior_samples: how many samples to use
        jitter: numerical stability
        condition_on_data: posterior (True) vs prior (False) predictive
        rng: optional numpy.random.Generator for the draw subsampling;
             None preserves the legacy global-np.random behavior
        strict: True (default) raises on any silent-wrong-answer path: a
             sample site apply_hp_value does not recognize, an exception
             while applying a site, a sample dict with no recognized kernel
             site, or a draw whose predictive fails numerically. False keeps
             the pre-2026-09 behavior (warn, skip the site or drop the draw)
             for exploratory use; the dropped draws are then recorded on the
             returned PredictiveList.

    Returns:
        PredictiveList (a list of GPPosteriorSample carrying
        attempted_indices, retained_indices, dropped, n_dropped)
    """
    from .model import build_model, select_hmc_sites, apply_hp_value
    from .decompose import compute_cholesky
    import gpytorch
    from gpytorch.constraints import Positive
    from gpytorch.priors import GammaPrior

    def _default_likelihood():
        return gpytorch.likelihoods.GaussianLikelihood(
            noise_constraint=Positive(),
            noise_prior=GammaPrior(1.75, 1.0),
        )

    if likelihood_builder is None:
        likelihood_builder = _default_likelihood

    x_train = x_train.double() if isinstance(x_train, torch.Tensor) else torch.tensor(x_train).double()
    y_train = y_train.double() if isinstance(y_train, torch.Tensor) else torch.tensor(y_train).double()
    x_eval = x_eval.double() if isinstance(x_eval, torch.Tensor) else torch.tensor(x_eval).double()

    first_key = list(mcmc_samples.keys())[0]
    total_mcmc = len(mcmc_samples[first_key])
    n_take = min(n_posterior_samples, total_mcmc)
    if rng is not None:
        indices = rng.choice(total_mcmc, n_take, replace=False)
    else:
        # legacy path: global np.random state (callers that need
        # reproducibility without the rng= parameter seed globally)
        indices = np.random.choice(total_mcmc, n_take, replace=False)

    relevant_keys = select_hmc_sites(mcmc_samples.keys())
    kernel_keys = [k for k in relevant_keys
                   if not k.endswith("noise_covar.noise_prior")]
    if not kernel_keys:
        msg = ("extract_gp_predictives: no kernel hyperparameter site was "
               f"recognized among {sorted(mcmc_samples.keys())}; every "
               "predictive would be built at the fresh model's initialization "
               "kernel values (only the noise would vary)")
        if strict:
            raise ValueError(msg)
        logger.warning(msg)

    results = []
    retained = []
    dropped = []

    for idx in indices:
        kernels, names = kernel_builder()
        fresh_likelihood = likelihood_builder()
        fresh_model, fresh_likelihood = build_model(x_train, y_train, kernels, names, fresh_likelihood)

        # Set parameters from this MCMC sample. Only values that were
        # actually applied are recorded as the draw's hyperparameters.
        hp_dict = {}
        for pyro_name in relevant_keys:
            val = float(mcmc_samples[pyro_name][idx])
            try:
                applied = apply_hp_value(fresh_model, fresh_likelihood, pyro_name, val)
            except (IndexError, AttributeError, RuntimeError) as exc:
                msg = (f"extract_gp_predictives: applying site {pyro_name!r} "
                       f"for draw {int(idx)} raised {type(exc).__name__}: {exc}")
                if strict:
                    raise ValueError(msg) from exc
                logger.warning(msg)
                continue
            if not applied:
                msg = (f"extract_gp_predictives: apply_hp_value did not recognize "
                       f"site {pyro_name!r} (draw {int(idx)}); the fresh model "
                       "keeps its initialization value for that hyperparameter")
                if strict:
                    raise ValueError(msg)
                logger.warning(msg)
                continue
            hp_dict[pyro_name] = val

        fresh_model.eval()
        fresh_likelihood.eval()

        with torch.no_grad():
            try:
                noise_var = fresh_likelihood.noise.item()
                K_XstarXstar = fresh_model.covar_module(x_eval, x_eval).evaluate().detach()

                if condition_on_data:
                    # Posterior predictive p(y* | X, y, θ)
                    K_XX = fresh_model.covar_module(x_train, x_train).evaluate().detach()
                    K_XstarX = fresh_model.covar_module(x_eval, x_train).evaluate().detach()
                    K_XXstar = fresh_model.covar_module(x_train, x_eval).evaluate().detach()

                    # Cholesky of K_XX + σ²I
                    L = compute_cholesky(K_XX, noise_var, jitter)
                    # Predictive mean: K_*X (K_XX + σ²I)^{-1} y
                    alpha = torch.cholesky_solve(y_train.unsqueeze(-1), L).squeeze(-1)
                    pred_mean = (K_XstarX @ alpha).numpy()
                    # Predictive covariance: K_** - K_*X (K_XX + σ²I)^{-1} K_X*
                    V = torch.linalg.solve_triangular(L, K_XXstar, upper=False)
                    pred_cov = (K_XstarXstar - V.T @ V).numpy()
                else:
                    # Prior predictive p(y* | θ): the GP prior at x_eval, no
                    # conditioning on data. ZeroMean → mean 0; x_train/y_train unused.
                    pred_mean = fresh_model.mean_module(x_eval).detach().numpy()
                    pred_cov = K_XstarXstar.numpy().copy()

                # Add observation noise to the predictive covariance
                pred_cov = pred_cov + noise_var * np.eye(len(x_eval))

                results.append(GPPosteriorSample(
                    mean=pred_mean,
                    cov=pred_cov,
                    hyperparameters=hp_dict,
                ))
                retained.append(int(idx))
            except RuntimeError as exc:
                if strict:
                    raise RuntimeError(
                        f"extract_gp_predictives: the predictive for draw "
                        f"{int(idx)} failed ({exc}); pass strict=False to drop "
                        "failing draws and record them instead") from exc
                dropped.append((int(idx), str(exc)))
                continue

    print(f"  Extracted {len(results)}/{len(indices)} GP predictives")
    if dropped:
        logger.warning("extract_gp_predictives dropped %d of %d draws: %s",
                       len(dropped), len(indices),
                       [d for d, _ in dropped][:10])
    return PredictiveList(results, attempted_indices=[int(i) for i in indices],
                          retained_indices=retained, dropped=dropped)


# ═══════════════════════════════════════════════════════════════════
# BMS* Scoring: Soft Transfer
# ═══════════════════════════════════════════════════════════════════

@dataclass
class BMSStarResult:
    """Results from BMS* analysis."""
    metric_name: str
    tau: float
    # Instance-level
    instance_names: List[str]
    instance_scores: np.ndarray        # (n_instances,) — unnormalized
    instance_posteriors: np.ndarray     # (n_instances,) — normalized, sum to 1
    # Class-level (same as instance for non-nested models)
    class_names: List[str]
    class_posteriors: np.ndarray        # (n_classes,) — normalized
    # Raw G matrix for diagnostics
    G_matrix: np.ndarray               # (n_psi, n_theta)
    # Draw-level diagnostics (2026-09 review FIX-3). weight_ess is the
    # per-candidate effective number of draws behind the pooled score,
    # (sum_i w_ij)^2 / sum_i w_ij^2 with w_ij = exp(-G_ij/tau) on the weights
    # actually aggregated: a concentration summary, not an MCMC ESS and not an
    # error bar. hard_win_credit splits each draw's unit of credit equally
    # among its exact co-minimizers (sums to one across candidates);
    # attainment is the fraction of draws on which a candidate attains the
    # row minimum (ties counted for every co-minimizer); tie_fraction is the
    # fraction of draws whose minimum is tied.
    weight_ess: Optional[np.ndarray] = None
    hard_win_credit: Optional[np.ndarray] = None
    attainment: Optional[np.ndarray] = None
    tie_fraction: Optional[float] = None


def log_weight_ess(log_w, axis: int = 0):
    """Effective sample size (sum w)^2 / sum w^2 from LOG weights.

    The one ESS routine of the package (fix pass 1b): the per-column maximum
    is subtracted before exponentiation, so a large common offset cancels
    exactly instead of surviving as a difference of two large log-sum-exps
    (review R6), and no weight can overflow. Entries of -inf contribute
    nothing. A column whose weights are all -inf has ESS 0 (absent support);
    a column containing NaN has ESS NaN (an invalid evaluation), which is
    deliberately distinct from absent support (review R8). A 1-D input
    returns a float.
    """
    lw = np.asarray(log_w, dtype=float)
    one_d = lw.ndim == 1
    if one_d:
        lw = lw[:, None]
        axis = 0
    nan_col = np.isnan(lw).any(axis=axis)
    m = np.max(np.where(np.isnan(lw), -np.inf, lw), axis=axis, keepdims=True)
    supported = np.isfinite(m)
    w = np.exp(lw - np.where(supported, m, 0.0))
    with np.errstate(invalid="ignore", divide="ignore"):
        ess = w.sum(axis=axis) ** 2 / (w ** 2).sum(axis=axis)
    ess = np.where(np.squeeze(supported, axis=axis), ess, 0.0)
    ess = np.where(nan_col, np.nan, ess)
    return float(ess[0]) if one_d else ess


def boltzmann_weight_ess(G_matrix: np.ndarray, tau: float) -> np.ndarray:
    """Per-candidate effective number of draws behind a pooled Boltzmann score.

    ESS_j = (sum_i w_ij)^2 / sum_i w_ij^2 with w_ij = exp(-G_ij / tau), computed
    from log weights (log_weight_ess) so that a candidate whose raw weights
    underflow still gets a finite value. Invariant under a per-candidate
    column shift of G, which is the multiplicative factor the cross-candidate
    normalization removes.
    """
    lw = -np.asarray(G_matrix, dtype=float) / float(tau)
    if not np.all(np.isfinite(lw)):
        raise ValueError("boltzmann_weight_ess requires finite G values")
    return log_weight_ess(lw, axis=0)


def hard_win_statistics(G_matrix: np.ndarray):
    """Tau-free draw-win statistics with an explicit, order-free tie rule.

    Exact ties on the validated finite scores: for draw i let T_i be the set
    of candidates attaining the row minimum. Returns
      hard_win_credit_j = mean_i [ 1(j in T_i) / |T_i| ]   (sums to one),
      attainment_j      = mean_i [ 1(j in T_i) ],
      tie_fraction      = mean_i [ |T_i| > 1 ].
    A first-argmin rule would silently award every tie to the first candidate.
    """
    G = np.asarray(G_matrix, dtype=float)
    if G.ndim != 2 or not np.all(np.isfinite(G)):
        raise ValueError("hard_win_statistics requires a finite 2-D G matrix")
    row_min = G.min(axis=1, keepdims=True)
    tied = (G == row_min)
    sizes = tied.sum(axis=1, keepdims=True)
    credit = (tied / sizes).mean(axis=0)
    attainment = tied.mean(axis=0)
    tie_fraction = float(np.mean(sizes[:, 0] > 1))
    return credit, attainment, tie_fraction


def compute_G_matrix(gp_samples: List[GPPosteriorSample],
                     candidate_results: list,
                     metric_name: str = "kl_forward") -> np.ndarray:
    """
    Compute divergence matrix G[i, j] = G(ψ_i, θ_j).

    Args:
        gp_samples: list of GPPosteriorSample (the ψ's)
        candidate_results: list of CandidateResult (the θ's)
        metric_name: one of 'kl_forward', 'kl_backward', 'kl_symmetric', 'hellinger'

    Returns:
        G matrix of shape (n_psi, n_theta)
    """
    # A4 universe firewall at the boundary that still holds candidate
    # metadata (2026-09 review FIX-4): every path that builds a G matrix
    # through the package passes here, including the aggregation_v3 entry
    # points that never call run_bms_star.
    _assert_candidate_universes_consistent(candidate_results)

    metric_fn = METRICS[metric_name]          # registers metrics_v2 on a miss
    n_psi = len(gp_samples)
    n_theta = len(candidate_results)
    G = np.zeros((n_psi, n_theta))

    for i, psi in enumerate(gp_samples):
        for j, theta in enumerate(candidate_results):
            try:
                G[i, j] = metric_fn(psi.mean, psi.cov, theta.mean, theta.cov)
            except (np.linalg.LinAlgError, ValueError):
                G[i, j] = np.inf

    # Replace any inf/nan with a value guaranteed to be WORSE (larger) than any
    # finite divergence. A plain `10 * max_finite` is wrong when the metric can
    # be negative (e.g. pw_nll, whose 0.5*log(2*pi*sigma^2) term goes negative):
    # 10*max_finite would then be the *smallest* G, so a failed computation would
    # win the comparison. This penalty is always strictly greater than max_finite.
    if np.any(np.isfinite(G)):
        max_finite = np.nanmax(G[np.isfinite(G)])
        penalty = max_finite + 10.0 * (abs(max_finite) + 1.0)
    else:
        penalty = 1e6
    G = np.where(np.isfinite(G), G, penalty)

    return G


def soft_transfer(G_matrix: np.ndarray, tau: float,
                  instance_names: List[str],
                  class_names: Optional[List[str]] = None,
                  normalize_per_draw: bool = False,
                  metric_name: Optional[str] = None) -> BMSStarResult:
    """
    Soft BMS* scoring.

    score(θ_j) = (1/N) Σ_i exp(-G(ψ_i, θ_j) / τ)

    Class level: only the one-instance-per-class mapping is supported, in
    which class posteriors equal instance posteriors. Any ``class_names``
    that groups instances raises rather than silently returning instance
    posteriors under a class label (2026-09 review FIX-3).

    Args:
        G_matrix: (n_psi, n_theta) divergence matrix
        tau: temperature parameter
        instance_names: names for each θ
        class_names: None or a 1:1 relabelling of the instances
        normalize_per_draw: if True, subtract per-row minimum before
            Boltzmann weighting. This removes systematic offset so that
            only *relative* divergence within each GP draw matters.
            Prevents microscopic absolute bias from being amplified
            into false certainty across many draws.
        metric_name: the divergence that produced G_matrix. None is recorded
            as "unspecified" rather than an invented identity.

    Returns:
        BMSStarResult with normalized posteriors and draw-level diagnostics
    """
    n_psi, n_theta = G_matrix.shape
    if not np.all(np.isfinite(G_matrix)):
        # A NaN or infinite divergence is never a score. compute_G_matrix
        # returns finite penalties, so only a hand-built matrix reaches this;
        # the pre-fix code returned a uniform posterior for it (review F4).
        raise ValueError("soft_transfer: G_matrix contains non-finite entries")

    if len(instance_names) != n_theta:
        raise ValueError(
            f"soft_transfer: {len(instance_names)} instance_names for "
            f"{n_theta} candidate columns")
    if class_names is None:
        class_names = instance_names
    elif len(class_names) != n_theta or len(set(class_names)) != n_theta:
        # one label per column and no repeats (review R5: a length check
        # alone, or a uniqueness check alone, each admits a malformed list)
        raise ValueError(
            "soft_transfer: class-level averaging over grouped instances is "
            "not implemented; pass class_names=None (or a 1:1 relabelling) "
            "and aggregate classes explicitly")

    # Optionally normalize: subtract best-model score per draw
    G_effective = G_matrix.copy()
    if normalize_per_draw:
        row_mins = G_effective.min(axis=1, keepdims=True)
        G_effective -= row_mins

    # Instance scores: average Boltzmann weight across GP samples
    # score(θ_j) = (1/N) Σ_i exp(-G_ij / τ)
    log_weights = -G_effective / tau
    # Numerical stability: subtract a single GLOBAL scalar. This cancels exactly
    # in the cross-candidate normalization below, so the posterior is unchanged.
    # A per-row (axis=1) max does NOT cancel — it is a per-draw constant applied
    # before the over-draw mean, so it reweights GP draws and silently behaves
    # like normalize_per_draw even when that flag is False.
    log_weights_shifted = log_weights - log_weights.max()
    weights = np.exp(log_weights_shifted)
    instance_scores = weights.mean(axis=0)

    # Normalize to get instance posteriors
    total = instance_scores.sum()
    if total > 0:
        instance_posteriors = instance_scores / total
    else:
        instance_posteriors = np.ones(n_theta) / n_theta

    # Class posteriors = instance posteriors (1:1 mapping, enforced above)
    class_posteriors = instance_posteriors.copy()

    # Draw-level diagnostics on the weights actually aggregated (G_effective)
    # and the tau-free win statistics on the raw matrix.
    weight_ess = boltzmann_weight_ess(G_effective, tau)
    credit, attainment, tie_fraction = hard_win_statistics(G_matrix)

    return BMSStarResult(
        metric_name=metric_name if metric_name is not None else "unspecified",
        tau=tau,
        instance_names=list(instance_names),
        instance_scores=instance_scores,
        instance_posteriors=instance_posteriors,
        class_names=list(class_names),
        class_posteriors=class_posteriors,
        G_matrix=G_matrix,
        weight_ess=weight_ess,
        hard_win_credit=credit,
        attainment=attainment,
        tie_fraction=tie_fraction,
    )


def aggregate_convention(G_matrix: np.ndarray, tau: float, variant: str) -> np.ndarray:
    """The three aggregation conventions of section 2.3 over one G matrix
    (n_draws, n_candidates) at temperature tau (2026-09 review FIX-9; moved
    into the package from the Case A script so that Cases A and C share one
    implementation instead of a cross-branch import).

      "pooled": the shipped default; mean over draws of exp(-G/tau) with one
          global stabilizing shift, normalized once (identical arithmetic to
          soft_transfer with normalize_per_draw=False).
      "rowmin": subtract each draw's minimum first, then as "pooled"
          (identical to soft_transfer with normalize_per_draw=True).
      "expected_posterior": normalize each draw into a posterior over
          candidates, then average (van Bork et al. Eq. 4).
    """
    G = np.asarray(G_matrix, dtype=float)
    if not np.all(np.isfinite(G)):
        # the Case A script's `tot > 0 else uniform` tail would otherwise
        # return a uniform posterior for a NaN matrix (GLM F1); on finite
        # input that tail is dead, so the arithmetic below is unchanged
        raise ValueError("aggregate_convention requires a finite G matrix")
    if variant == "pooled":
        G_eff = G
    elif variant == "rowmin":
        G_eff = G - G.min(axis=1, keepdims=True)
    elif variant == "expected_posterior":
        lw = -(G - G.min(axis=1, keepdims=True)) / tau
        w = np.exp(lw)
        w = w / w.sum(axis=1, keepdims=True)
        s = w.mean(axis=0)
        return s / s.sum()
    else:
        raise ValueError(f"unknown aggregation variant {variant!r}")
    lw = -G_eff / tau
    w = np.exp(lw - lw.max())
    s = w.mean(axis=0)
    tot = s.sum()
    return s / tot if tot > 0 else np.ones(G.shape[1]) / G.shape[1]


def _assert_candidate_universes_consistent(candidate_results):
    """Firewall the A4 separate-normalization rule at the shared BMS* boundary.

    run_bms_star normalizes candidate probabilities over ONE universe; the
    D19 pre-registration (decision A4, plan section 3) forbids merging the
    Mauna 4-ladder and harmonized 3-set into one normalization. Enforcing
    that only in the Mauna script is caller-dependent — any other caller
    could pass a mixed set and receive silently normalized cross-universe
    probabilities — so the check runs here, before any G matrix is computed:

    - every result untagged (universe is None): allowed (legacy/toy callers
      with plain candidates carry no universe and no A4 obligation);
    - any result tagged: EVERY result must be tagged with the SAME universe;
    - mixed tags, or a mix of tagged and untagged: raise before computing G.
    """
    universes = [getattr(cr, "universe", None) for cr in candidate_results]
    tagged = {u for u in universes if u is not None}
    if not tagged:
        return  # all untagged: legacy/toy, no A4 rule applies
    if None in universes or len(tagged) > 1:
        labels = ", ".join(
            f"{getattr(cr, 'name', '?')}[{getattr(cr, 'universe', None)}]"
            for cr in candidate_results)
        raise ValueError(
            "compute_G_matrix/run_bms_star received candidates spanning "
            "multiple universes or a mix of tagged and untagged results "
            f"({labels}); decision A4 forbids merging Mauna candidate "
            "universes into one normalization")


def run_bms_star(gp_samples: List[GPPosteriorSample],
                 candidate_results: list,
                 metric_names: List[str] = None,
                 taus: np.ndarray = None,
                 normalize_per_draw: bool = False) -> Dict[str, Dict[float, BMSStarResult]]:
    """
    Run full BMS* analysis across metrics and temperatures.

    Args:
        normalize_per_draw: if True, subtract per-draw minimum G before
            Boltzmann. Eliminates systematic absolute-score bias.

    Returns:
        results[metric_name][tau] = BMSStarResult
    """
    implicit_metrics = metric_names is None
    if metric_names is None:
        metric_names = list(METRICS.keys())
    if taus is None:
        taus = np.logspace(-1, 2, 20)
    if implicit_metrics:
        from .config import APPENDIX_METRICS, PRIMARY_METRIC
        appendix = [m for m in metric_names if m in APPENDIX_METRICS]
        if appendix:
            logger.warning(
                "run_bms_star: scoring appendix-only metric(s) %s because "
                "metric_names was not given; W1 makes %s the primary metric",
                appendix, PRIMARY_METRIC)
        if PRIMARY_METRIC not in metric_names:
            # The implicit roster is whatever is registered at call time; the
            # primary metric registers on first use of metrics_v2 (Kimi K3-1).
            # The roster is left as it is so existing implicit calls keep
            # their outputs; the omission is announced instead.
            logger.warning(
                "run_bms_star: the primary metric %s is not in the implicit "
                "roster (metrics_v2 not imported yet); pass metric_names "
                "explicitly to score it", PRIMARY_METRIC)

    _assert_candidate_universes_consistent(candidate_results)

    instance_names = [cr.name for cr in candidate_results]
    results = {}

    for metric_name in metric_names:
        print(f"\n  Computing G matrix: {metric_name}...")
        G = compute_G_matrix(gp_samples, candidate_results, metric_name)

        print(f"    G stats — min: {G.min():.2f}, median: {np.median(G):.2f}, max: {G.max():.2f}")

        # Per-draw diagnostic: how often does each model win raw?
        raw_winners = np.argmin(G, axis=1)
        for m_idx, name in enumerate(instance_names):
            n_wins = np.sum(raw_winners == m_idx)
            print(f"    {name} wins {n_wins}/{len(raw_winners)} draws (raw G)")

        if normalize_per_draw:
            row_deltas = G - G.min(axis=1, keepdims=True)
            for m_idx, name in enumerate(instance_names):
                mean_delta = row_deltas[:, m_idx].mean()
                print(f"    {name} mean Δ from best: {mean_delta:.4f}")

        results[metric_name] = {}
        for tau in taus:
            bms_result = soft_transfer(G, tau, instance_names,
                                       normalize_per_draw=normalize_per_draw,
                                       metric_name=metric_name)
            results[metric_name][tau] = bms_result

    return results


# ═══════════════════════════════════════════════════════════════════
# Visualization
# ═══════════════════════════════════════════════════════════════════

def plot_bms_star_results(results: Dict[str, Dict[float, BMSStarResult]],
                         figsize=None):
    """
    Plot BMS* results: τ sensitivity curves, one panel per metric.
    Automatically sizes grid to fit all metrics.
    """
    import matplotlib.pyplot as plt

    metric_names = list(results.keys())
    n_metrics = len(metric_names)
    ncols = min(4, n_metrics)
    nrows = (n_metrics + ncols - 1) // ncols
    if figsize is None:
        figsize = (4 * ncols, 3.5 * nrows)

    fig, axes = plt.subplots(nrows, ncols, figsize=figsize)
    if n_metrics == 1:
        axes = np.array([axes])
    axes = np.atleast_2d(axes).flatten()

    colors = ['#e74c3c', '#3498db', '#2ecc71', '#9b59b6', '#f39c12']

    for ax_idx, metric_name in enumerate(metric_names):
        ax = axes[ax_idx]
        taus = sorted(results[metric_name].keys())
        instance_names = results[metric_name][taus[0]].instance_names
        n_models = len(instance_names)

        posteriors = np.zeros((len(taus), n_models))
        for t_idx, tau in enumerate(taus):
            posteriors[t_idx] = results[metric_name][tau].instance_posteriors

        for m_idx, name in enumerate(instance_names):
            ax.semilogx(taus, posteriors[:, m_idx],
                       label=name, color=colors[m_idx % len(colors)],
                       linewidth=2)

        ax.set_xlabel("τ")
        ax.set_ylabel("Posterior")
        ax.set_title(metric_name, fontsize=9)
        ax.set_ylim(-0.05, 1.05)
        ax.legend(fontsize=6)
        ax.grid(True, alpha=0.3)

    # Hide unused axes
    for ax_idx in range(n_metrics, len(axes)):
        axes[ax_idx].set_visible(False)

    fig.suptitle("BMS*: Model Posteriors vs Temperature", fontsize=14)
    fig.tight_layout()
    return fig


def plot_G_heatmaps(results: Dict[str, Dict[float, BMSStarResult]],
                    figsize=None):
    """Plot G matrix heatmaps for each metric."""
    import matplotlib.pyplot as plt

    metric_names = list(results.keys())
    n_metrics = len(metric_names)
    ncols = min(5, n_metrics)
    nrows = (n_metrics + ncols - 1) // ncols
    if figsize is None:
        figsize = (3.5 * ncols, 3 * nrows)

    fig, axes = plt.subplots(nrows, ncols, figsize=figsize)
    if n_metrics == 1:
        axes = np.array([axes])
    axes = np.atleast_2d(axes).flatten()

    first_tau = sorted(results[metric_names[0]].keys())[0]

    for ax, metric_name in zip(axes, metric_names):
        bms = results[metric_name][first_tau]
        G = bms.G_matrix

        im = ax.imshow(G, aspect='auto', cmap='viridis')
        ax.set_xlabel("Candidate (θ)", fontsize=7)
        ax.set_ylabel("GP sample (ψ)", fontsize=7)
        ax.set_title(metric_name, fontsize=8)
        ax.set_xticks(range(len(bms.instance_names)))
        ax.set_xticklabels(bms.instance_names, rotation=45, ha='right', fontsize=6)
        plt.colorbar(im, ax=ax, fraction=0.046)

    for ax_idx in range(n_metrics, len(axes)):
        axes[ax_idx].set_visible(False)

    fig.suptitle("Divergence G(ψ, θ) matrices", fontsize=14)
    fig.tight_layout()
    return fig


def plot_candidate_predictions(x_eval, gp_samples, candidate_results,
                               x_train=None, y_train=None, figsize=(14, 8)):
    """Overlay candidate model predictions on GP posterior."""
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 2, figsize=figsize)
    axes = axes.flatten()
    colors = ['#e74c3c', '#3498db', '#2ecc71', '#9b59b6']

    # Compute GP posterior mean and std across samples
    gp_means = np.array([s.mean for s in gp_samples])
    gp_mean = gp_means.mean(axis=0)
    gp_std = gp_means.std(axis=0)

    for ax_idx, (cr, color) in enumerate(zip(candidate_results, colors)):
        ax = axes[ax_idx]

        # GP posterior
        ax.fill_between(x_eval, gp_mean - 2*gp_std, gp_mean + 2*gp_std,
                        alpha=0.2, color='gray', label='GP ±2σ')
        # Individual GP samples (thin lines)
        for s in gp_samples[::max(1, len(gp_samples)//15)]:
            ax.plot(x_eval, s.mean, color='gray', alpha=0.1, linewidth=0.5)
        ax.plot(x_eval, gp_mean, color='gray', linewidth=1.5, label='GP mean')

        # Candidate model
        ax.plot(x_eval, cr.mean, color=color, linewidth=2.5, label=cr.name)
        cr_std = np.sqrt(np.diag(cr.cov))
        ax.fill_between(x_eval, cr.mean - 2*cr_std, cr.mean + 2*cr_std,
                        alpha=0.15, color=color)

        # Data
        if x_train is not None and y_train is not None:
            ax.scatter(x_train, y_train, color='black', marker='x', s=20, zorder=5)

        ax.set_title(cr.name, fontsize=12, fontweight='bold')
        ax.legend(fontsize=7, loc='upper left')
        ax.grid(True, alpha=0.3)

    fig.suptitle("Candidate Models vs GP Posterior", fontsize=14)
    fig.tight_layout()
    return fig


def print_bms_star_table(results: Dict[str, Dict[float, BMSStarResult]],
                         tau: float):
    """Print a clean table of BMS* posteriors at a given τ."""
    metric_names = list(results.keys())
    first = results[metric_names[0]]
    closest_tau = min(first.keys(), key=lambda t: abs(t - tau))
    instance_names = first[closest_tau].instance_names

    # Header
    header = f"{'Model':<15}"
    for m in metric_names:
        header += f"  {m:<15}"
    print(f"\n  BMS* Posteriors at τ = {closest_tau:.2f}")
    print(f"  {'─' * len(header)}")
    print(f"  {header}")
    print(f"  {'─' * len(header)}")

    for i, name in enumerate(instance_names):
        row = f"{name:<15}"
        for m in metric_names:
            p = results[m][closest_tau].instance_posteriors[i]
            row += f"  {p:<15.4f}"
        print(f"  {row}")
    print()
