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

import numpy as np
from typing import Dict, List, Optional, Tuple
from scipy.optimize import minimize
from dataclasses import dataclass, field

from bistar_gp.bms_star import GPPosteriorSample, METRICS
from bistar_gp.induced_prior import ModelParameterSpace, build_toy_parameter_spaces
from bistar_gp.aggregation_v3 import average_gp_posterior


@dataclass
class LaplaceResult:
    """Result of Laplace evidence computation for one model."""
    model_name: str
    prior_name: str
    # MAP estimate
    phi_star: Dict[str, float]       # MAP parameters
    phi_mle: Dict[str, float]        # MLE parameters (for comparison)
    # Evidence decomposition
    log_evidence: float              # total log evidence
    log_lik_at_map: float            # term (1): data fit
    G_at_map: float                  # Ḡ(φ*) — GP divergence at MAP
    prior_penalty: float             # term (2): -Ḡ/τ
    occam_factor: float              # term (3): complexity
    # Metadata
    n_params: int
    tau: float
    converged: bool


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


def compute_laplace_evidence(
    param_space: ModelParameterSpace,
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_eval: np.ndarray,
    avg_gp: GPPosteriorSample,
    metric_name: str = "pw_kl_vcal",
    tau: float = 1.0,
    mle_params: Optional[Dict[str, float]] = None,
    prior_name: str = "",
) -> LaplaceResult:
    """
    DEPRECATED (see docs/plan-zmx-laplace.md, DECISIONS D3). This computes a Laplace
    approximation to log ∫ p(y|φ)·exp(−Ḡ/τ) dφ — a likelihood-weighted joint that the
    framework does NOT define as Z_Mx (the paper's Z_Mx is the data-free model prior).
    Use `laplace_log_Z_Mx` for the model prior, `laplace_log_evidence_induced` /
    `laplace_log_evidence_ordinary` for evidences, and `model_posterior` for selection.
    Retained temporarily until callers migrate.

    Laplace approximation to model evidence under GP-induced prior.

    Steps:
      1. Find φ* = MAP under induced prior (optimize from MLE)
      2. Compute Hessian H at φ*
      3. Assemble log evidence = log_lik + prior_penalty + occam_factor
    """
    metric_fn = METRICS[metric_name]
    specs = param_space.param_specs
    d = param_space.n_params

    # Pack/unpack helpers
    def pack(pd):
        return np.array([pd[ps.name] for ps in specs])

    def unpack(vec):
        return {ps.name: float(vec[j]) for j, ps in enumerate(specs)}

    # ── Log likelihood ──
    def log_likelihood(param_dict):
        try:
            mu = param_space.predict_fn(x_train, param_dict)
        except Exception:
            return -1e10
        sigma = param_dict.get(param_space.noise_param, 0.3)
        sigma2 = max(sigma ** 2, 1e-8)
        n = len(y_train)
        residuals = y_train - mu
        return -0.5 * n * np.log(2 * np.pi * sigma2) - 0.5 * np.sum(residuals**2) / sigma2

    # ── Negative log joint (to minimize) ──
    def neg_log_joint(vec):
        pd = unpack(vec)

        # Enforce sigma > 0
        sigma_val = pd.get(param_space.noise_param, 0.3)
        if sigma_val <= 0:
            return 1e10

        ll = log_likelihood(pd)
        G = compute_G_at_params(pd, param_space, x_eval, avg_gp, metric_fn)
        return -(ll - G / tau)

    # ── Initialize from MLE ──
    if mle_params is not None:
        x0 = pack(mle_params)
    else:
        # Center of bounds
        x0 = np.array([(ps.bounds[0] + ps.bounds[1]) / 2 for ps in specs])

    bounds = [(ps.bounds[0], ps.bounds[1]) for ps in specs]

    # ── Optimize ──
    try:
        result = minimize(neg_log_joint, x0, bounds=bounds, method='L-BFGS-B',
                          options={'maxiter': 500, 'ftol': 1e-10})
        phi_star = unpack(result.x)
        converged = result.success
    except Exception:
        phi_star = mle_params if mle_params else unpack(x0)
        converged = False

    # ── Evaluate terms at φ* ──
    log_lik_star = log_likelihood(phi_star)
    G_star = compute_G_at_params(phi_star, param_space, x_eval, avg_gp, metric_fn)
    prior_penalty = -G_star / tau
    log_joint_star = log_lik_star + prior_penalty

    # ── Hessian ──
    try:
        H = numerical_hessian(neg_log_joint, pack(phi_star), eps=1e-4)

        # Ensure positive definite
        eigvals = np.linalg.eigvalsh(H)
        if np.any(eigvals <= 0):
            # Add regularization
            reg = abs(min(eigvals.min(), 0)) + 1e-4
            H += reg * np.eye(d)

        sign, logdet = np.linalg.slogdet(H)
        if sign <= 0:
            logdet = d * np.log(1e-4)  # fallback

        occam_factor = (d / 2) * np.log(2 * np.pi) - 0.5 * logdet
    except Exception:
        occam_factor = 0.0  # fallback: no complexity correction
        logdet = 0.0

    log_evidence = log_joint_star + occam_factor

    # ── Report ──
    print(f"\n  [{param_space.model_name}] Laplace evidence ({prior_name}, τ={tau}):")
    print(f"    MAP params: {phi_star}")
    print(f"    log_lik    = {log_lik_star:>10.2f}  (data fit)")
    print(f"    -G/τ       = {prior_penalty:>10.2f}  (GP prior penalty, G={G_star:.4f})")
    print(f"    Occam      = {occam_factor:>10.2f}  ({d} params)")
    print(f"    ─────────────────────────")
    print(f"    log evid   = {log_evidence:>10.2f}")
    if mle_params:
        G_mle = compute_G_at_params(mle_params, param_space, x_eval, avg_gp, metric_fn)
        print(f"    [MLE G={G_mle:.4f} vs MAP G={G_star:.4f}]")

    return LaplaceResult(
        model_name=param_space.model_name,
        prior_name=prior_name,
        phi_star=phi_star,
        phi_mle=mle_params or {},
        log_evidence=log_evidence,
        log_lik_at_map=log_lik_star,
        G_at_map=G_star,
        prior_penalty=prior_penalty,
        occam_factor=occam_factor,
        n_params=d,
        tau=tau,
        converged=converged,
    )


def compute_all_laplace_evidences(
    param_spaces: Dict[str, ModelParameterSpace],
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_eval: np.ndarray,
    avg_gp: GPPosteriorSample,
    mle_params: Dict[str, Dict[str, float]],
    metric_name: str = "pw_kl_vcal",
    tau: float = 1.0,
    prior_name: str = "",
) -> Dict[str, LaplaceResult]:
    """
    Compute Laplace evidence for all candidate models.
    Returns dict model_name → LaplaceResult.
    """
    results = {}
    for model_name, ps in param_spaces.items():
        results[model_name] = compute_laplace_evidence(
            ps, x_train, y_train, x_eval, avg_gp,
            metric_name=metric_name, tau=tau,
            mle_params=mle_params.get(model_name),
            prior_name=prior_name,
        )

    # Compute posteriors
    log_evs = np.array([results[m].log_evidence for m in param_spaces])
    names = list(param_spaces.keys())
    log_evs -= log_evs.max()
    posteriors = np.exp(log_evs)
    posteriors /= posteriors.sum()

    print(f"\n  Model Posteriors (Laplace, {prior_name}, τ={tau}):")
    for name, p, lr in zip(names, posteriors, results.values()):
        marker = " ★" if p == posteriors.max() else ""
        print(f"    {name:<15} p={p:.4f}  "
              f"[fit={lr.log_lik_at_map:.1f}, prior={lr.prior_penalty:.1f}, "
              f"occam={lr.occam_factor:.1f}]{marker}")

    return results


# ═══════════════════════════════════════════════════════════════════
# Canonical Z_Mx / evidence / posterior  (docs/plan-zmx-laplace.md, DECISIONS D3)
# ═══════════════════════════════════════════════════════════════════
#
# All log-integrals use the generic Laplace identity
#     log ∫ exp(−f(φ)) dφ  ≈  −f(φ*) + (d/2)log(2π) − ½log|H|,   H = ∇²f(φ*), φ* = argmin f.
# The τ and −log V_ref bookkeeping falls out of the choice of f:
#   Z_Mx (no Occam):  f = Ḡ/τ                    → log Z = −Ḡ*/τ + (d/2)log(2πτ) − ½log|H_Ḡ|
#   Z_Mx (Occam):     subtract log V_ref (p_ref = 1/V_ref uniform)
#   ordinary evidence f = −log p(y|φ),  minus log V_ref (normalized reference prior)
#   N(M):             f = −[log p(y|φ) − Ḡ/τ]    (joint MAP), minus log V_ref if Occam
#   induced evidence  p(y|M,ψ) = N(M)/Z_prior(M),  Z_prior = Z_Mx with Occam (the V cancels)


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
    """Generic Laplace: returns (log_integral, x_star, f_star, logdet, converged)."""
    try:
        res = minimize(neg_log_f, x0, bounds=bounds, method="L-BFGS-B",
                       options={"maxiter": 500, "ftol": 1e-10})
        x_star, converged = res.x, bool(res.success)
    except Exception:
        x_star, converged = np.asarray(x0, dtype=float), False
    f_star = float(neg_log_f(x_star))
    H = numerical_hessian(neg_log_f, x_star, eps=eps)
    logdet, _ = _laplace_logdet(H)
    log_integral = -f_star + 0.5 * d * np.log(2 * np.pi) - 0.5 * logdet
    return log_integral, x_star, f_star, logdet, converged


def laplace_log_Z_Mx(param_space, x_eval, avg_gp, *, metric_name="pw_kl_vcal",
                     tau=1.0, occam=False, mle_params=None) -> ZMxResult:
    """Data-free GP-informed model prior Z_Mx = ∫ exp(−Ḡ/τ) [p_ref] dφ (§1.2).

    Expands at φ_G* = argmin Ḡ with the Hessian of Ḡ. NO data likelihood. With
    occam=True the uniform reference prior p_ref = 1/V_ref contributes −log V_ref.
    """
    metric_fn = METRICS[metric_name]
    d = param_space.n_params
    _, unpack = _packers(param_space)
    x0, bounds = _x0_and_bounds(param_space, mle_params)

    def neg_log_f(vec):
        pd = unpack(vec)
        if pd.get(param_space.noise_param, 0.3) <= 0:
            return 1e10
        return compute_G_at_params(pd, param_space, x_eval, avg_gp, metric_fn) / tau

    log_int, x_star, f_star, logdet, conv = _laplace_log_integral(neg_log_f, x0, bounds, d)
    log_V = _log_reference_volume(param_space)
    log_Z = log_int - (log_V if occam else 0.0)
    return ZMxResult(model_name=param_space.model_name, log_Z=log_Z,
                     G_at_min=f_star * tau, phi_min=unpack(x_star), occam=occam,
                     log_volume=log_V, logdet_H=logdet, n_params=d, tau=tau, converged=conv)


def laplace_log_evidence_ordinary(param_space, x_train, y_train, *,
                                  mle_params=None) -> EvidenceResult:
    """Ordinary marginal likelihood p_ord(D|M) = ∫ p(y|φ) p_ref dφ (no GP).

    The GP-free primitive for the baseline and Construction I.
    """
    d = param_space.n_params
    _, unpack = _packers(param_space)
    x0, bounds = _x0_and_bounds(param_space, mle_params)

    def neg_log_f(vec):
        pd = unpack(vec)
        if pd.get(param_space.noise_param, 0.3) <= 0:
            return 1e10
        return -_log_likelihood(param_space, x_train, y_train, pd)

    log_int, x_star, f_star, logdet, conv = _laplace_log_integral(neg_log_f, x0, bounds, d)
    log_ev = log_int - _log_reference_volume(param_space)   # p_ref = 1/V_ref normalized
    return EvidenceResult(model_name=param_space.model_name, log_evidence=log_ev,
                          kind="ordinary", log_lik_at_map=-f_star,
                          phi_star=unpack(x_star), n_params=d, converged=conv)


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

    log_int, x_star, f_star, logdet, conv = _laplace_log_integral(neg_log_joint, x0, bounds, d)
    log_N = log_int - (_log_reference_volume(param_space) if occam else 0.0)
    return log_N, unpack(x_star), conv


def laplace_log_evidence_induced(param_space, x_train, y_train, x_eval, avg_gp, *,
                                 metric_name="pw_kl_vcal", tau=1.0,
                                 mle_params=None) -> EvidenceResult:
    """Within-model evidence under the GP-induced prior: p(y|M,ψ) = N(M)/Z_prior(M) (§1.3).

    Occam-independent: both N and Z_prior carry −log V_ref, which cancels.
    """
    metric_fn = METRICS[metric_name]
    log_N, phi_star, conv = _laplace_log_N(param_space, x_train, y_train, x_eval, avg_gp,
                                           metric_fn, tau, mle_params, occam=True)
    zprior = laplace_log_Z_Mx(param_space, x_eval, avg_gp, metric_name=metric_name,
                              tau=tau, occam=True, mle_params=mle_params)
    ll_at = _log_likelihood(param_space, x_train, y_train, phi_star)
    return EvidenceResult(model_name=param_space.model_name,
                          log_evidence=log_N - zprior.log_Z, kind="induced",
                          log_N=log_N, log_Z_prior=zprior.log_Z, log_lik_at_map=ll_at,
                          phi_star=phi_star, n_params=param_space.n_params, converged=conv)


def model_posterior(param_spaces, x_train, y_train, x_eval, avg_gp, mle_params, *,
                    construction="II", metric_name="pw_kl_vcal", tau=1.0,
                    occam=False) -> ModelPosteriorResult:
    """Normalized model posterior under the chosen assembly (§2). II is canonical.

      baseline: p(M|D) ∝ p_ord(D|M)                    (no GP)
      I       : p(M|D) ∝ Z_Mx · p_ord(D|M)             (GP at class level)
      II      : p(M|D) ∝ N(M)                          (GP-induced joint prior)
    """
    metric_fn = METRICS[metric_name]
    names = list(param_spaces.keys())
    log_kernel, components = {}, {}

    for name in names:
        ps = param_spaces[name]
        mp = mle_params.get(name) if mle_params else None
        if construction == "baseline":
            ev = laplace_log_evidence_ordinary(ps, x_train, y_train, mle_params=mp)
            log_kernel[name] = ev.log_evidence
            components[name] = {"log_ord_evidence": ev.log_evidence}
        elif construction == "I":
            zmx = laplace_log_Z_Mx(ps, x_eval, avg_gp, metric_name=metric_name,
                                   tau=tau, occam=occam, mle_params=mp)
            ev = laplace_log_evidence_ordinary(ps, x_train, y_train, mle_params=mp)
            log_kernel[name] = zmx.log_Z + ev.log_evidence
            components[name] = {"log_Z_Mx": zmx.log_Z, "log_ord_evidence": ev.log_evidence}
        elif construction == "II":
            log_N, _, _ = _laplace_log_N(ps, x_train, y_train, x_eval, avg_gp,
                                         metric_fn, tau, mp, occam=occam)
            log_kernel[name] = log_N
            components[name] = {"log_N": log_N}
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
    results_by_prior: Dict[str, Dict[str, LaplaceResult]],
    figsize: tuple = None,
):
    """
    Stacked bar chart showing the three evidence components per model,
    grouped by GP prior. This is the key BI* visualization.

    For each model bar:
      Bottom: log_lik (data fit) — always positive contribution
      Middle: prior_penalty (-G/τ) — GP-induced, varies across priors
      Top: occam_factor — complexity penalty, fixed per model
    """
    import matplotlib.pyplot as plt

    prior_names = list(results_by_prior.keys())
    model_names = list(results_by_prior[prior_names[0]].keys())
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
        x = np.arange(n_models)

        for m_idx, model_name in enumerate(model_names):
            lr = results_by_prior[prior_name][model_name]
            color = colors.get(model_name, 'gray')

            # Stack: fit + prior + occam
            ax.bar(x[m_idx], lr.log_lik_at_map, color=color, alpha=0.9,
                   label='Data fit' if m_idx == 0 else "")
            ax.bar(x[m_idx], lr.prior_penalty, bottom=lr.log_lik_at_map,
                   color=color, alpha=0.5, hatch='///',
                   label='GP prior' if m_idx == 0 else "")
            ax.bar(x[m_idx], lr.occam_factor,
                   bottom=lr.log_lik_at_map + lr.prior_penalty,
                   color=color, alpha=0.3, hatch='...',
                   label='Occam' if m_idx == 0 else "")

            # Total evidence marker
            ax.plot(x[m_idx], lr.log_evidence, 'k_', markersize=15, markeredgewidth=2)

        ax.set_xticks(x)
        ax.set_xticklabels(model_names, fontsize=9, rotation=20)
        ax.set_title(f"{prior_name}", fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.2, axis='y')
        if ax == axes[0]:
            ax.set_ylabel("Log Evidence Components", fontsize=11)

    axes[0].legend(fontsize=8, loc='lower left')
    fig.suptitle("BI* Evidence Decomposition: Fit + GP Prior + Occam",
                 fontsize=14)
    fig.tight_layout()
    return fig


def plot_prior_penalty_comparison(
    results_by_prior: Dict[str, Dict[str, LaplaceResult]],
    figsize: tuple = None,
):
    """
    Bar chart showing just the GP prior penalty (-G/τ) per model per prior.

    This isolates the BI* contribution: how much the GP prior favors each model.
    The differences across priors show the information transfer.
    """
    import matplotlib.pyplot as plt

    prior_names = list(results_by_prior.keys())
    model_names = list(results_by_prior[prior_names[0]].keys())
    n_priors = len(prior_names)
    n_models = len(model_names)

    colors = ['#e74c3c', '#3498db', '#2ecc71', '#9b59b6']

    if figsize is None:
        figsize = (max(10, 2.5 * n_priors), 5)

    fig, ax = plt.subplots(figsize=figsize)
    x = np.arange(n_priors)
    width = 0.8 / n_models

    for m_idx, model_name in enumerate(model_names):
        penalties = []
        for prior_name in prior_names:
            lr = results_by_prior[prior_name][model_name]
            penalties.append(lr.prior_penalty)

        offset = (m_idx - n_models / 2 + 0.5) * width
        ax.bar(x + offset, penalties, width, label=model_name,
               color=colors[m_idx % len(colors)])

    ax.set_xticks(x)
    ax.set_xticklabels(prior_names, fontsize=10)
    ax.set_ylabel("GP Prior Penalty  −G(φ*)/τ", fontsize=11)
    ax.set_title("BI* Prior Transfer: GP's Preference for Each Model\n"
                 "(less negative = GP likes it more)", fontsize=13)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.2, axis='y')
    fig.tight_layout()
    return fig


def plot_model_posteriors_by_prior(
    results_by_prior: Dict[str, Dict[str, LaplaceResult]],
    figsize: tuple = None,
):
    """
    Bar chart: model posteriors under Laplace evidence, grouped by GP prior.
    """
    import matplotlib.pyplot as plt

    prior_names = list(results_by_prior.keys())
    model_names = list(results_by_prior[prior_names[0]].keys())
    n_priors = len(prior_names)
    n_models = len(model_names)

    colors = ['#e74c3c', '#3498db', '#2ecc71', '#9b59b6']

    if figsize is None:
        figsize = (max(10, 2.5 * n_priors), 5)

    fig, ax = plt.subplots(figsize=figsize)
    x = np.arange(n_priors)
    width = 0.8 / n_models

    for m_idx, model_name in enumerate(model_names):
        posteriors = []
        for prior_name in prior_names:
            log_evs = np.array([results_by_prior[prior_name][m].log_evidence
                                for m in model_names])
            log_evs -= log_evs.max()
            ps = np.exp(log_evs) / np.exp(log_evs).sum()
            posteriors.append(ps[m_idx])

        offset = (m_idx - n_models / 2 + 0.5) * width
        ax.bar(x + offset, posteriors, width, label=model_name,
               color=colors[m_idx % len(colors)])

    ax.set_xticks(x)
    ax.set_xticklabels(prior_names, fontsize=10)
    ax.set_ylabel("Model Posterior p(M|y,ψ)", fontsize=11)
    ax.set_title("BI* Model Selection: How GP Prior Shapes Model Ranking\n"
                 "(Laplace Approximation)", fontsize=13)
    ax.set_ylim(0, 1)
    ax.axhline(0.25, color='gray', linestyle=':', alpha=0.5, label='uniform')
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
        log_evs = []
        for model_name in model_names:
            lr = compute_laplace_evidence(
                param_spaces[model_name], x_train, y_train, x_eval, avg_gp,
                metric_name=metric_name, tau=tau,
                mle_params=mle_params.get(model_name),
                prior_name=prior_name,
            )
            log_evs.append(lr.log_evidence)

        log_evs = np.array(log_evs)
        log_evs -= log_evs.max()
        ps = np.exp(log_evs) / np.exp(log_evs).sum()
        posteriors[t_idx] = ps

    colors = ['#e74c3c', '#3498db', '#2ecc71', '#9b59b6']
    fig, ax = plt.subplots(figsize=figsize)

    for m_idx, name in enumerate(model_names):
        ax.plot(taus, posteriors[:, m_idx], color=colors[m_idx],
                linewidth=2.5, label=name)

    ax.set_xscale('log')
    ax.set_ylim(0, 1)
    ax.set_xlabel('τ (transfer temperature)', fontsize=12)
    ax.set_ylabel('Model Posterior', fontsize=12)
    ax.set_title(f"BI* τ Sensitivity (Laplace, {prior_name})\n"
                 f"Low τ = strong GP influence  |  High τ = data only",
                 fontsize=13)
    ax.axhline(0.25, color='gray', linestyle=':', alpha=0.5)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    return fig
