"""
laplace_evidence.py — Laplace Approximation for BI* Model Evidence

Replaces importance sampling (which fails in >3D parameter spaces)
with a Laplace approximation around the MAP estimate under the
GP-induced prior.

The model evidence integral:

  p(y | M_j, ψ) = ∫ p(y | φ, M_j) · p_induced(φ | ψ) dφ

is approximated as:

  log p(y | M_j, ψ) ≈ log p(y | φ*) - Ḡ(φ*)/τ + (d/2)log(2π) - (1/2)log|H|

where:
  φ* = argmax [log p(y|φ) - Ḡ(φ)/τ]   (MAP under induced prior)
  H  = Hessian of -[log p(y|φ) - Ḡ(φ)/τ] at φ*
  d  = number of parameters
  Ḡ(φ) = divergence between GP posterior and candidate prediction at φ

The three terms have clear interpretations:
  (1) log p(y|φ*) — data fit at MAP
  (2) -Ḡ(φ*)/τ  — GP-induced prior penalty (how well GP "likes" these params)
  (3) (d/2)log(2π) - (1/2)log|H| — Occam factor (complexity penalty)

This is what makes BI* different from BIC/AIC:
  Term (2) transfers qualitative GP beliefs into model comparison.
  Informative GP → small Ḡ for correct model → correct model wins.
  Vague GP → similar Ḡ for all models → reverts to standard BIC-like behavior.
"""

import logging

import numpy as np
from typing import Dict, List, Optional, Tuple
from scipy.optimize import minimize
from dataclasses import dataclass, field

from bistar_gp.bms_star import GPPosteriorSample, METRICS
from bistar_gp.induced_prior import ModelParameterSpace, build_toy_parameter_spaces
from bistar_gp.aggregation_v3 import average_gp_posterior
import bistar_gp.metrics_v2  # noqa: F401 — registers pw_* metrics (incl. the default pw_kl_vcal) into METRICS

logger = logging.getLogger(__name__)


def numerical_hessian(f, x, eps=1e-5):
    """
    Compute Hessian of f at x via central finite differences.
    f: R^d → R
    Returns (d, d) matrix.
    """
    d = len(x)
    H = np.zeros((d, d))
    f0 = f(x)

    for i in range(d):
        for j in range(i, d):
            x_pp = x.copy(); x_pp[i] += eps; x_pp[j] += eps
            x_pm = x.copy(); x_pm[i] += eps; x_pm[j] -= eps
            x_mp = x.copy(); x_mp[i] -= eps; x_mp[j] += eps
            x_mm = x.copy(); x_mm[i] -= eps; x_mm[j] -= eps

            H[i, j] = (f(x_pp) - f(x_pm) - f(x_mp) + f(x_mm)) / (4 * eps**2)
            H[j, i] = H[i, j]

    return H


def compute_G_at_params(
    param_dict: Dict[str, float],
    param_space: ModelParameterSpace,
    x_eval: np.ndarray,
    avg_gp: GPPosteriorSample,
    metric_fn,
) -> float:
    """Compute G between candidate prediction at φ and averaged GP."""
    try:
        mu_theta = param_space.predict_fn(x_eval, param_dict)
    except Exception:
        return 1e6

    sigma = param_dict.get(param_space.noise_param, 0.3)
    sigma2 = max(sigma ** 2, 1e-8)
    n_eval = len(x_eval)
    cov_theta = sigma2 * np.eye(n_eval)

    try:
        return metric_fn(avg_gp.mean, avg_gp.cov, mu_theta, cov_theta)
    except (np.linalg.LinAlgError, ValueError):
        return 1e6


# ═══════════════════════════════════════════════════════════════════
# Canonical Z_Mx / evidence / posterior  (docs/plan-zmx-laplace.md, DECISIONS D3)
# ═══════════════════════════════════════════════════════════════════
#
# All log-integrals use the generic Laplace identity
#     log ∫ exp(−f(φ)) dφ  ≈  −f(φ*) + (d/2)log(2π) − ½log|H|,   H = ∇²f(φ*), φ* = argmin f.
# The τ and −log V_ref bookkeeping falls out of the choice of f:
#   Z_Mx:             f = Ḡ (τ enters analytically) → log Z = −Ḡ*/τ + (d/2)log(2πτ) − ½log|H_Ḡ|
#   ordinary evidence f = −log p(y|φ)
#   N(M):             f = −[log p(y|φ) − Ḡ/τ]    (joint MAP)
#   induced evidence  p(y|M,ψ) = N(M)/Z_prior(M),  Z_prior = Z_Mx with Occam (the V cancels)
#
# The occam flag has ONE meaning module-wide: include the −log V_ref term of the
# normalized uniform reference prior p_ref = 1/V_ref. occam=False integrates
# against the raw Lebesgue measure on the box (faithful no-Occam BI*). Every
# construction must apply the SAME reference measure, otherwise cross-construction
# gaps (the ablation ladder's "GP contribution") absorb per-model V_ref
# differences — for the toy spaces a ~3.9-nat cross-model artifact.


@dataclass
class ZMxResult:
    """Data-free GP-informed model prior Z_Mx (§1.2 of the plan)."""
    model_name: str
    log_Z: float                 # log Z_Mx, Occam-adjusted
    G_at_min: float              # Ḡ(φ_G*)
    phi_min: Dict[str, float]
    occam: bool
    log_volume: float            # log V_ref
    logdet_H: float
    n_params: int
    tau: float
    converged: bool
    n_clipped: int = 0           # Hessian eigenvalues clipped: >0 means |H| was regularized


@dataclass
class EvidenceResult:
    """Within-model evidence (kind='ordinary' or 'induced')."""
    model_name: str
    log_evidence: float
    kind: str
    log_N: Optional[float] = None          # induced: log ∫ p(y|φ) exp(−Ḡ/τ) p_ref dφ
    log_Z_prior: Optional[float] = None    # induced: log Z_Mx^{Occam}
    log_lik_at_map: Optional[float] = None
    phi_star: Dict[str, float] = field(default_factory=dict)
    n_params: int = 0
    converged: bool = True
    n_clipped: int = 0           # Hessian eigenvalues clipped: >0 means |H| was regularized


@dataclass
class ModelPosteriorResult:
    """Normalized model posterior under a chosen assembly (§2 of the plan)."""
    construction: str                      # 'baseline' | 'I' | 'II'
    occam: bool
    tau: float
    model_names: List[str]
    posteriors: Dict[str, float]
    log_kernel: Dict[str, float]           # unnormalized log p(M|D) per model
    components: Dict[str, Dict[str, float]]


def _log_reference_volume(param_space) -> float:
    """log V_ref = Σ log(upper − lower) over the uniform reference-prior box."""
    return float(np.sum([np.log(ps.bounds[1] - ps.bounds[0])
                         for ps in param_space.param_specs]))


def _laplace_logdet(H: np.ndarray, floor: float = 1e-8, cap: float = 1e12) -> Tuple[float, int]:
    """log|H| from eigenvalues clipped to [floor, cap]; robust to non-PSD/cliff curvature.

    Clipping prevents both a negative/near-zero eigenvalue (from a saddle or flat
    direction) and a cliff at a bounds-adjacent MAP from fabricating ~1e17 curvature.
    A floored direction contributes −½·log(floor) ≈ +9.2 nats to the log-integral,
    an arbitrary regularization rather than geometry — so n_clipped is propagated
    into every result (ZMxResult/EvidenceResult.n_clipped, the Construction-II
    components detail) and a warning is logged; treat any n_clipped > 0 evidence
    value as floor-dependent.
    """
    H = 0.5 * (H + H.T)
    eig = np.linalg.eigvalsh(H)
    clipped = np.clip(eig, floor, cap)
    n_clipped = int(np.sum((eig < floor) | (eig > cap)))
    return float(np.sum(np.log(clipped))), n_clipped


def _packers(param_space):
    specs = param_space.param_specs
    def pack(pd):
        return np.array([pd[ps.name] for ps in specs])
    def unpack(vec):
        return {ps.name: float(vec[j]) for j, ps in enumerate(specs)}
    return pack, unpack


def _x0_and_bounds(param_space, mle_params):
    specs = param_space.param_specs
    bounds = [(ps.bounds[0], ps.bounds[1]) for ps in specs]
    if mle_params is not None:
        x0 = np.array([mle_params[ps.name] for ps in specs])
    else:
        x0 = np.array([(b[0] + b[1]) / 2 for b in bounds])
    return x0, bounds


def _log_likelihood(param_space, x_train, y_train, param_dict) -> float:
    try:
        mu = param_space.predict_fn(x_train, param_dict)
    except Exception:
        return -1e10
    sigma = param_dict.get(param_space.noise_param, 0.3)
    sigma2 = max(sigma ** 2, 1e-8)
    n = len(y_train)
    resid = y_train - mu
    return -0.5 * n * np.log(2 * np.pi * sigma2) - 0.5 * np.sum(resid ** 2) / sigma2


def _laplace_log_integral(neg_log_f, x0, bounds, d, eps=1e-4):
    """Generic Laplace: returns (log_integral, x_star, f_star, logdet, converged, n_clipped)."""
    try:
        res = minimize(neg_log_f, x0, bounds=bounds, method="L-BFGS-B",
                       options={"maxiter": 500, "ftol": 1e-10})
        x_star, converged = res.x, bool(res.success)
    except Exception:
        x_star, converged = np.asarray(x0, dtype=float), False
    f_star = float(neg_log_f(x_star))
    H = numerical_hessian(neg_log_f, x_star, eps=eps)
    logdet, n_clipped = _laplace_logdet(H)
    if n_clipped:
        logger.warning(
            "Laplace Hessian regularized: %d of %d eigenvalues clipped at x*=%s; "
            "the log-integral carries a floor/cap-dependent term", n_clipped, d, x_star)
    log_integral = -f_star + 0.5 * d * np.log(2 * np.pi) - 0.5 * logdet
    return log_integral, x_star, f_star, logdet, converged, n_clipped


def laplace_log_Z_Mx(param_space, x_eval, avg_gp, *, metric_name="pw_kl_vcal",
                     tau=1.0, occam=False, mle_params=None) -> ZMxResult:
    """Data-free GP-informed model prior Z_Mx = ∫ exp(−Ḡ/τ) [p_ref] dφ (§1.2).

    Expands at φ_G* = argmin Ḡ with the Hessian of Ḡ. NO data likelihood. With
    occam=True the uniform reference prior p_ref = 1/V_ref contributes −log V_ref.

    τ enters analytically (argmin Ḡ/τ = argmin Ḡ and H_{Ḡ/τ} = H_Ḡ/τ):
        log Z(τ) = −Ḡ*/τ + (d/2)·log(2πτ) − ½·log|H_Ḡ|
    so the optimization, the Hessian, and the eigenvalue clipping in
    _laplace_logdet are all evaluated once on Ḡ itself — which eigenvalues get
    floored cannot depend on τ, keeping τ-sweeps free of clipping artifacts.
    """
    metric_fn = METRICS[metric_name]
    d = param_space.n_params
    _, unpack = _packers(param_space)
    x0, bounds = _x0_and_bounds(param_space, mle_params)

    def neg_log_f(vec):
        pd = unpack(vec)
        if pd.get(param_space.noise_param, 0.3) <= 0:
            return 1e10
        return compute_G_at_params(pd, param_space, x_eval, avg_gp, metric_fn)

    log_int, x_star, G_star, logdet, conv, n_clip = _laplace_log_integral(neg_log_f, x0, bounds, d)
    # log_int is the τ=1 integral −Ḡ* + (d/2)log(2π) − ½log|H_Ḡ|; rescale to τ.
    log_int_tau = log_int + G_star - G_star / tau + 0.5 * d * np.log(tau)
    log_V = _log_reference_volume(param_space)
    log_Z = log_int_tau - (log_V if occam else 0.0)
    return ZMxResult(model_name=param_space.model_name, log_Z=log_Z,
                     G_at_min=G_star, phi_min=unpack(x_star), occam=occam,
                     log_volume=log_V, logdet_H=logdet, n_params=d, tau=tau,
                     converged=conv, n_clipped=n_clip)


def laplace_log_evidence_ordinary(param_space, x_train, y_train, *,
                                  mle_params=None, occam=True) -> EvidenceResult:
    """Ordinary marginal likelihood p_ord(D|M) = ∫ p(y|φ) [p_ref] dφ (no GP).

    The GP-free primitive for the baseline and Construction I. With occam=True
    (default) the normalized reference prior contributes −log V_ref, making
    this a proper marginal likelihood; occam=False integrates the likelihood
    against the raw Lebesgue measure, matching what Z_Mx and N(M) do under the
    same flag so that cross-construction gaps stay volume-free.
    """
    d = param_space.n_params
    _, unpack = _packers(param_space)
    x0, bounds = _x0_and_bounds(param_space, mle_params)

    def neg_log_f(vec):
        pd = unpack(vec)
        if pd.get(param_space.noise_param, 0.3) <= 0:
            return 1e10
        return -_log_likelihood(param_space, x_train, y_train, pd)

    log_int, x_star, f_star, logdet, conv, n_clip = _laplace_log_integral(neg_log_f, x0, bounds, d)
    log_ev = log_int - (_log_reference_volume(param_space) if occam else 0.0)
    return EvidenceResult(model_name=param_space.model_name, log_evidence=log_ev,
                          kind="ordinary", log_lik_at_map=-f_star,
                          phi_star=unpack(x_star), n_params=d, converged=conv,
                          n_clipped=n_clip)


def _laplace_log_N(param_space, x_train, y_train, x_eval, avg_gp, metric_fn,
                   tau, mle_params, occam):
    """log N(M) = log ∫ p(y|φ) exp(−Ḡ/τ) [p_ref] dφ via the joint MAP."""
    d = param_space.n_params
    _, unpack = _packers(param_space)
    x0, bounds = _x0_and_bounds(param_space, mle_params)

    def neg_log_joint(vec):
        pd = unpack(vec)
        if pd.get(param_space.noise_param, 0.3) <= 0:
            return 1e10
        ll = _log_likelihood(param_space, x_train, y_train, pd)
        G = compute_G_at_params(pd, param_space, x_eval, avg_gp, metric_fn)
        return -(ll - G / tau)

    log_int, x_star, f_star, logdet, conv, n_clip = _laplace_log_integral(neg_log_joint, x0, bounds, d)
    log_V = _log_reference_volume(param_space)
    log_N = log_int - (log_V if occam else 0.0)
    pd_star = unpack(x_star)
    ll_star = _log_likelihood(param_space, x_train, y_train, pd_star)
    G_star = compute_G_at_params(pd_star, param_space, x_eval, avg_gp, metric_fn)
    # Additive decomposition of log_N at the joint MAP: fit + gp_penalty + occam == log_N.
    detail = {
        "log_N": log_N,
        "log_lik_at_map": ll_star,
        "G_at_map": G_star,
        "gp_penalty": -G_star / tau,
        "occam": 0.5 * d * np.log(2 * np.pi) - 0.5 * logdet - (log_V if occam else 0.0),
        "n_clipped": n_clip,
    }
    return log_N, pd_star, conv, detail


def laplace_log_evidence_induced(param_space, x_train, y_train, x_eval, avg_gp, *,
                                 metric_name="pw_kl_vcal", tau=1.0,
                                 mle_params=None) -> EvidenceResult:
    """Within-model evidence under the GP-induced prior: p(y|M,ψ) = N(M)/Z_prior(M) (§1.3).

    Occam-independent: both N and Z_prior carry −log V_ref, which cancels.
    """
    metric_fn = METRICS[metric_name]
    log_N, phi_star, conv, detail = _laplace_log_N(param_space, x_train, y_train, x_eval, avg_gp,
                                                   metric_fn, tau, mle_params, occam=True)
    zprior = laplace_log_Z_Mx(param_space, x_eval, avg_gp, metric_name=metric_name,
                              tau=tau, occam=True, mle_params=mle_params)
    ll_at = _log_likelihood(param_space, x_train, y_train, phi_star)
    return EvidenceResult(model_name=param_space.model_name,
                          log_evidence=log_N - zprior.log_Z, kind="induced",
                          log_N=log_N, log_Z_prior=zprior.log_Z, log_lik_at_map=ll_at,
                          phi_star=phi_star, n_params=param_space.n_params, converged=conv,
                          n_clipped=detail["n_clipped"] + zprior.n_clipped)


def model_posterior(param_spaces, x_train, y_train, x_eval, avg_gp, mle_params, *,
                    construction="II", metric_name="pw_kl_vcal", tau=1.0,
                    occam=False) -> ModelPosteriorResult:
    """Normalized model posterior under the chosen assembly (§2). II is canonical.

      baseline: p(M|D) ∝ p_ord(D|M)                    (no GP)
      I       : p(M|D) ∝ Z_Mx · p_ord(D|M)             (GP at class level)
      II      : p(M|D) ∝ N(M)                          (GP-induced joint prior)

    The occam flag applies the −log V_ref reference-volume term to EVERY
    integral of the chosen construction (see the module header), so pairwise
    construction gaps isolate GP terms rather than per-model volume bookkeeping.
    """
    metric_fn = METRICS[metric_name]
    names = list(param_spaces.keys())
    log_kernel, components = {}, {}

    for name in names:
        ps = param_spaces[name]
        mp = mle_params.get(name) if mle_params else None
        if construction == "baseline":
            ev = laplace_log_evidence_ordinary(ps, x_train, y_train, mle_params=mp,
                                               occam=occam)
            log_kernel[name] = ev.log_evidence
            components[name] = {"log_ord_evidence": ev.log_evidence}
        elif construction == "I":
            zmx = laplace_log_Z_Mx(ps, x_eval, avg_gp, metric_name=metric_name,
                                   tau=tau, occam=occam, mle_params=mp)
            ev = laplace_log_evidence_ordinary(ps, x_train, y_train, mle_params=mp,
                                               occam=occam)
            log_kernel[name] = zmx.log_Z + ev.log_evidence
            components[name] = {"log_Z_Mx": zmx.log_Z, "log_ord_evidence": ev.log_evidence}
        elif construction == "II":
            log_N, _, _, detail = _laplace_log_N(ps, x_train, y_train, x_eval, avg_gp,
                                                 metric_fn, tau, mp, occam=occam)
            log_kernel[name] = log_N
            components[name] = detail
        else:
            raise ValueError(f"unknown construction {construction!r}")

    logk = np.array([log_kernel[n] for n in names])
    post = np.exp(logk - logk.max())
    post = post / post.sum()
    return ModelPosteriorResult(
        construction=construction, occam=occam, tau=tau, model_names=names,
        posteriors={n: float(p) for n, p in zip(names, post)},
        log_kernel={n: float(log_kernel[n]) for n in names},
        components=components,
    )


# ═══════════════════════════════════════════════════════════════════
# Visualization
# ═══════════════════════════════════════════════════════════════════

def plot_evidence_decomposition(
    results_by_prior: Dict[str, "ModelPosteriorResult"],
    figsize: tuple = None,
):
    """
    Additive decomposition of the Construction-II log kernel log N(M) per model,
    grouped by GP prior. Each bar stacks the parts that sum to log N(M):
      fit  = log p(y|φ*)          (data fit at the joint MAP)
      gp   = −Ḡ(φ*)/τ            (GP-compatibility, varies across priors)
      occam = (d/2)log2π − ½log|H| [− log V_ref]   (Laplace complexity term)

    Pass a dict of prior_name → ModelPosteriorResult (construction="II").
    """
    import matplotlib.pyplot as plt

    prior_names = list(results_by_prior.keys())
    model_names = results_by_prior[prior_names[0]].model_names
    n_priors = len(prior_names)
    n_models = len(model_names)

    colors = {
        'Linear': '#e74c3c',
        'Sinusoidal': '#3498db',
        'Sin+Linear': '#2ecc71',
        'Quadratic': '#9b59b6',
    }

    if figsize is None:
        figsize = (5 * n_priors, 6)

    fig, axes = plt.subplots(1, n_priors, figsize=figsize, sharey=True)
    if n_priors == 1:
        axes = [axes]

    for ax, prior_name in zip(axes, prior_names):
        comps = results_by_prior[prior_name].components
        x = np.arange(n_models)

        for m_idx, model_name in enumerate(model_names):
            c = comps[model_name]
            color = colors.get(model_name, 'gray')
            fit, gp, occ = c["log_lik_at_map"], c["gp_penalty"], c["occam"]

            ax.bar(x[m_idx], fit, color=color, alpha=0.9,
                   label='Data fit' if m_idx == 0 else "")
            ax.bar(x[m_idx], gp, bottom=fit, color=color, alpha=0.5, hatch='///',
                   label='GP prior −Ḡ/τ' if m_idx == 0 else "")
            ax.bar(x[m_idx], occ, bottom=fit + gp, color=color, alpha=0.3, hatch='...',
                   label='Occam' if m_idx == 0 else "")

            ax.plot(x[m_idx], c["log_N"], 'k_', markersize=15, markeredgewidth=2)

        ax.set_xticks(x)
        ax.set_xticklabels(model_names, fontsize=9, rotation=20)
        ax.set_title(f"{prior_name}", fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.2, axis='y')
        if ax == axes[0]:
            ax.set_ylabel("log N(M) components", fontsize=11)

    axes[0].legend(fontsize=8, loc='lower left')
    fig.suptitle("BI* Construction II: log N(M) = Fit + GP prior + Occam",
                 fontsize=14)
    fig.tight_layout()
    return fig


def plot_prior_penalty_comparison(
    results_by_prior: Dict[str, "ModelPosteriorResult"],
    figsize: tuple = None,
):
    """
    Bar chart of the GP prior penalty −Ḡ(φ*)/τ per model per prior.

    Isolates the BI* contribution: how much the GP prior favors each model.
    Pass a dict of prior_name → ModelPosteriorResult (construction="II").
    """
    import matplotlib.pyplot as plt

    prior_names = list(results_by_prior.keys())
    model_names = results_by_prior[prior_names[0]].model_names
    n_priors = len(prior_names)
    n_models = len(model_names)

    colors = ['#e74c3c', '#3498db', '#2ecc71', '#9b59b6']

    if figsize is None:
        figsize = (max(10, 2.5 * n_priors), 5)

    fig, ax = plt.subplots(figsize=figsize)
    x = np.arange(n_priors)
    width = 0.8 / n_models

    for m_idx, model_name in enumerate(model_names):
        penalties = [results_by_prior[p].components[model_name]["gp_penalty"]
                     for p in prior_names]
        offset = (m_idx - n_models / 2 + 0.5) * width
        ax.bar(x + offset, penalties, width, label=model_name,
               color=colors[m_idx % len(colors)])

    ax.set_xticks(x)
    ax.set_xticklabels(prior_names, fontsize=10)
    ax.set_ylabel("GP Prior Penalty  −Ḡ(φ*)/τ", fontsize=11)
    ax.set_title("BI* Prior Transfer: GP's Preference for Each Model\n"
                 "(less negative = GP likes it more)", fontsize=13)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.2, axis='y')
    fig.tight_layout()
    return fig


def plot_model_posteriors_by_prior(
    results_by_prior: Dict[str, "ModelPosteriorResult"],
    figsize: tuple = None,
):
    """
    Bar chart: model posteriors p(M|D,ψ) (Construction II), grouped by GP prior.
    Pass a dict of prior_name → ModelPosteriorResult.
    """
    import matplotlib.pyplot as plt

    prior_names = list(results_by_prior.keys())
    model_names = results_by_prior[prior_names[0]].model_names
    n_priors = len(prior_names)
    n_models = len(model_names)

    colors = ['#e74c3c', '#3498db', '#2ecc71', '#9b59b6']

    if figsize is None:
        figsize = (max(10, 2.5 * n_priors), 5)

    fig, ax = plt.subplots(figsize=figsize)
    x = np.arange(n_priors)
    width = 0.8 / n_models

    for m_idx, model_name in enumerate(model_names):
        posteriors = [results_by_prior[p].posteriors[model_name] for p in prior_names]
        offset = (m_idx - n_models / 2 + 0.5) * width
        ax.bar(x + offset, posteriors, width, label=model_name,
               color=colors[m_idx % len(colors)])

    ax.set_xticks(x)
    ax.set_xticklabels(prior_names, fontsize=10)
    ax.set_ylabel("Model Posterior p(M|D,ψ)", fontsize=11)
    ax.set_title("BI* Model Selection: How GP Prior Shapes Model Ranking\n"
                 "(Construction II, Laplace)", fontsize=13)
    ax.set_ylim(0, 1)
    ax.axhline(1.0 / n_models, color='gray', linestyle=':', alpha=0.5, label='uniform')
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.2, axis='y')
    fig.tight_layout()
    return fig


def plot_tau_effect_on_evidence(
    param_spaces: Dict[str, ModelParameterSpace],
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_eval: np.ndarray,
    avg_gp: GPPosteriorSample,
    mle_params: Dict[str, Dict[str, float]],
    metric_name: str = "pw_kl_vcal",
    taus: np.ndarray = None,
    prior_name: str = "",
    construction: str = "II",
    occam: bool = False,
    figsize: tuple = (10, 5),
):
    """
    Show how τ controls the balance between GP prior and complexity.

    Low τ: GP prior dominates → correct model wins (if GP is informative)
    High τ: prior weakens → reverts to BIC-like complexity ranking
    """
    import matplotlib.pyplot as plt

    if taus is None:
        taus = np.logspace(-1, 2, 25)

    model_names = list(param_spaces.keys())
    n_models = len(model_names)
    posteriors = np.zeros((len(taus), n_models))

    for t_idx, tau in enumerate(taus):
        mpr = model_posterior(param_spaces, x_train, y_train, x_eval, avg_gp, mle_params,
                              construction=construction, metric_name=metric_name,
                              tau=tau, occam=occam)
        posteriors[t_idx] = [mpr.posteriors[m] for m in model_names]

    colors = ['#e74c3c', '#3498db', '#2ecc71', '#9b59b6']
    fig, ax = plt.subplots(figsize=figsize)

    for m_idx, name in enumerate(model_names):
        ax.plot(taus, posteriors[:, m_idx], color=colors[m_idx % len(colors)],
                linewidth=2.5, label=name)

    ax.set_xscale('log')
    ax.set_ylim(0, 1)
    ax.set_xlabel('τ (transfer temperature)', fontsize=12)
    ax.set_ylabel('Model Posterior', fontsize=12)
    ax.set_title(f"BI* τ Sensitivity (Construction {construction}, {prior_name})\n"
                 f"Low τ = strong GP influence   High τ = data only",
                 fontsize=13)
    ax.axhline(1.0 / n_models, color='gray', linestyle=':', alpha=0.5)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    return fig


def plot_ablation_ladder(
    param_spaces: Dict[str, ModelParameterSpace],
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_eval: np.ndarray,
    avg_gp: GPPosteriorSample,
    mle_params: Dict[str, Dict[str, float]],
    metric_name: str = "pw_kl_vcal",
    tau: float = 1.0,
    occam: bool = False,
    prior_name: str = "",
    figsize: tuple = None,
):
    """
    Baseline / Construction I / Construction II model posteriors side by side.

    baseline: no GP.  I: GP as model prior × ordinary evidence.
    II (canonical): GP-induced joint prior. Each pairwise gap isolates one GP
    contribution (baseline vs I = the GP model prior; I vs II = the induced
    parameter prior; baseline vs II = the total GP contribution).
    """
    import matplotlib.pyplot as plt

    model_names = list(param_spaces.keys())
    constructions = ["baseline", "I", "II"]
    post = {}
    for c in constructions:
        mpr = model_posterior(param_spaces, x_train, y_train, x_eval, avg_gp, mle_params,
                              construction=c, metric_name=metric_name, tau=tau, occam=occam)
        post[c] = mpr.posteriors

    n_c = len(constructions)
    n_models = len(model_names)
    colors = ['#e74c3c', '#3498db', '#2ecc71', '#9b59b6']
    if figsize is None:
        figsize = (max(9, 2.6 * n_c), 5)

    fig, ax = plt.subplots(figsize=figsize)
    x = np.arange(n_c)
    width = 0.8 / n_models
    for m_idx, model_name in enumerate(model_names):
        vals = [post[c][model_name] for c in constructions]
        offset = (m_idx - n_models / 2 + 0.5) * width
        ax.bar(x + offset, vals, width, label=model_name, color=colors[m_idx % len(colors)])

    ax.set_xticks(x)
    ax.set_xticklabels(["baseline\n(no GP)", "I\n(GP model prior)", "II\n(GP joint prior)"],
                       fontsize=10)
    ax.set_ylabel("Model Posterior p(M|D)", fontsize=11)
    ax.set_title(f"BI* Ablation Ladder{(' — ' + prior_name) if prior_name else ''}\n"
                 "baseline vs I: value of GP model prior · I vs II: value of induced parameter prior",
                 fontsize=12)
    ax.set_ylim(0, 1)
    ax.axhline(1.0 / n_models, color='gray', linestyle=':', alpha=0.5)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.2, axis='y')
    fig.tight_layout()
    return fig
