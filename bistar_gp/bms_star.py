"""
BMS* (Bayesian Model Selection Star) implementation.

Extends Bayesian induction (Chandramouli & Shiffrin, 2016) by:
1. Using GP hyperpriors to define prior/posterior over data distributions (ψ)
2. Computing divergence G between GP posterior samples and candidate model predictions
3. Soft transfer: transferring GP-derived posteriors onto candidate model instances

Supports: KL(ψ||θ), KL(θ||ψ), Symmetric KL, Hellinger distance
"""

import numpy as np
import torch
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

torch.set_default_dtype(torch.float64)


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
METRICS = {
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
}


# ═══════════════════════════════════════════════════════════════════
# GP Predictive Extraction from HMC Samples
# ═══════════════════════════════════════════════════════════════════

@dataclass
class GPPosteriorSample:
    """One draw from the GP posterior over data distributions (one ψ)."""
    mean: np.ndarray       # (n_eval,)
    cov: np.ndarray        # (n_eval, n_eval)
    hyperparameters: Dict[str, float]


def extract_gp_predictives(model, likelihood, x_train, y_train, x_eval,
                           mcmc_samples, kernel_builder,
                           likelihood_builder=None,
                           n_posterior_samples=200, jitter=1e-4):
    """
    Extract full GP predictive distributions for each HMC sample.

    Each sample defines a specific GP with specific hyperparameters,
    which implies a specific multivariate Gaussian over y at x_eval.
    These are the ψ's in BMS*.

    Args:
        model: fitted AdditiveGPModel (for component_names)
        likelihood: fitted likelihood
        x_train, y_train: training data
        x_eval: evaluation points
        mcmc_samples: dict from fit_hmc
        kernel_builder: callable returning (kernels, names)
        likelihood_builder: callable returning a likelihood. If None, uses
                           default with Positive() constraint.
        n_posterior_samples: how many samples to use
        jitter: numerical stability

    Returns:
        List[GPPosteriorSample]
    """
    from .model import build_model
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
    indices = np.random.choice(total_mcmc, min(n_posterior_samples, total_mcmc), replace=False)

    relevant_keys = [k for k in mcmc_samples.keys()
                     if k.startswith("kernel_components") or k.startswith("noise_covar")]

    results = []

    for idx in indices:
        kernels, names = kernel_builder()
        fresh_likelihood = likelihood_builder()
        fresh_model, fresh_likelihood = build_model(x_train, y_train, kernels, names, fresh_likelihood)

        # Set parameters from this MCMC sample
        hp_dict = {}
        for pyro_name in relevant_keys:
            val = float(mcmc_samples[pyro_name][idx])
            hp_dict[pyro_name] = val

            try:
                if "noise_covar.noise" in pyro_name:
                    fresh_likelihood.noise = val
                    continue

                parts = pyro_name.split(".")
                comp_idx = int(parts[1])
                kernel = fresh_model.kernel_components[comp_idx]

                if "base_kernel.lengthscale" in pyro_name:
                    kernel.base_kernel.lengthscale = val
                elif "base_kernel.period_length" in pyro_name:
                    kernel.base_kernel.period_length = val
                elif "outputscale" in pyro_name:
                    kernel.outputscale = val
                elif "variance" in pyro_name:
                    kernel.variance = val
            except (IndexError, AttributeError, RuntimeError):
                continue

        fresh_model.eval()
        fresh_likelihood.eval()

        # Compute full joint GP predictive: p(y* | X, y, θ)
        with torch.no_grad():
            try:
                noise_var = fresh_likelihood.noise.item()

                # K_sum at train points
                K_XX = fresh_model.covar_module(x_train, x_train).evaluate().detach()
                K_XstarX = fresh_model.covar_module(x_eval, x_train).evaluate().detach()
                K_XstarXstar = fresh_model.covar_module(x_eval, x_eval).evaluate().detach()
                K_XXstar = fresh_model.covar_module(x_train, x_eval).evaluate().detach()

                # Cholesky of K_XX + σ²I
                L = compute_cholesky(K_XX, noise_var, jitter)

                # Predictive mean: K_*X (K_XX + σ²I)^{-1} y
                alpha = torch.cholesky_solve(y_train.unsqueeze(-1), L).squeeze(-1)
                pred_mean = (K_XstarX @ alpha).numpy()

                # Predictive covariance: K_** - K_*X (K_XX + σ²I)^{-1} K_X* + σ²I
                V = torch.linalg.solve_triangular(L, K_XXstar, upper=False)
                pred_cov = (K_XstarXstar - V.T @ V).numpy()

                # Add observation noise to predictive covariance
                pred_cov += noise_var * np.eye(len(x_eval))

                results.append(GPPosteriorSample(
                    mean=pred_mean,
                    cov=pred_cov,
                    hyperparameters=hp_dict,
                ))
            except RuntimeError:
                continue

    print(f"  Extracted {len(results)}/{len(indices)} GP predictives")
    return results


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
    metric_fn = METRICS[metric_name]
    n_psi = len(gp_samples)
    n_theta = len(candidate_results)
    G = np.zeros((n_psi, n_theta))

    for i, psi in enumerate(gp_samples):
        for j, theta in enumerate(candidate_results):
            try:
                G[i, j] = metric_fn(psi.mean, psi.cov, theta.mean, theta.cov)
            except (np.linalg.LinAlgError, ValueError):
                G[i, j] = np.inf

    # Replace any inf/nan with large finite value
    max_finite = np.nanmax(G[np.isfinite(G)]) if np.any(np.isfinite(G)) else 1e6
    G = np.where(np.isfinite(G), G, 10 * max_finite)

    return G


def soft_transfer(G_matrix: np.ndarray, tau: float,
                  instance_names: List[str],
                  class_names: Optional[List[str]] = None) -> BMSStarResult:
    """
    Soft BMS* scoring.

    score(θ_j) = (1/N) Σ_i exp(-G(ψ_i, θ_j) / τ)

    For class-level, average within classes (not sum, to avoid size bias).

    Args:
        G_matrix: (n_psi, n_theta) divergence matrix
        tau: temperature parameter
        instance_names: names for each θ
        class_names: if None, each instance is its own class

    Returns:
        BMSStarResult with normalized posteriors
    """
    n_psi, n_theta = G_matrix.shape

    if class_names is None:
        class_names = instance_names

    # Instance scores: average Boltzmann weight across GP samples
    # score(θ_j) = (1/N) Σ_i exp(-G_ij / τ)
    log_weights = -G_matrix / tau
    # Numerical stability: subtract max per column
    log_weights_shifted = log_weights - log_weights.max(axis=1, keepdims=True)
    weights = np.exp(log_weights_shifted)
    instance_scores = weights.mean(axis=0)

    # Normalize to get instance posteriors
    total = instance_scores.sum()
    if total > 0:
        instance_posteriors = instance_scores / total
    else:
        instance_posteriors = np.ones(n_theta) / n_theta

    # Class posteriors = instance posteriors (1:1 mapping for now)
    class_posteriors = instance_posteriors.copy()

    metric_name = "unknown"  # will be set by caller
    return BMSStarResult(
        metric_name=metric_name,
        tau=tau,
        instance_names=list(instance_names),
        instance_scores=instance_scores,
        instance_posteriors=instance_posteriors,
        class_names=list(class_names),
        class_posteriors=class_posteriors,
        G_matrix=G_matrix,
    )


def run_bms_star(gp_samples: List[GPPosteriorSample],
                 candidate_results: list,
                 metric_names: List[str] = None,
                 taus: np.ndarray = None) -> Dict[str, Dict[float, BMSStarResult]]:
    """
    Run full BMS* analysis across metrics and temperatures.

    Returns:
        results[metric_name][tau] = BMSStarResult
    """
    if metric_names is None:
        metric_names = list(METRICS.keys())
    if taus is None:
        taus = np.logspace(-1, 2, 20)

    instance_names = [cr.name for cr in candidate_results]
    results = {}

    for metric_name in metric_names:
        print(f"\n  Computing G matrix: {metric_name}...")
        G = compute_G_matrix(gp_samples, candidate_results, metric_name)

        print(f"    G stats — min: {G.min():.2f}, median: {np.median(G):.2f}, max: {G.max():.2f}")

        results[metric_name] = {}
        for tau in taus:
            bms_result = soft_transfer(G, tau, instance_names)
            bms_result.metric_name = metric_name
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
