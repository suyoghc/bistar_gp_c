"""
induced_prior.py — GP-Induced Priors on Parametric Model Parameters

This is the core BI* mechanism:

  GP kernel priors (qualitative beliefs about data patterns)
    → GP posterior ψ (updated beliefs about data)
      → Induced prior on model parameters φ
        → Bayesian model selection with informed priors

The key equation from Extending Bayesian Induction:

  p(φ_j | ψ, M_j) ∝ exp(-G(ψ, θ_j(φ)) / τ) · p₀(φ_j)

where:
  - ψ = GP posterior (data distribution belief)
  - θ_j(φ) = candidate model M_j's prediction given parameters φ
  - G = divergence between GP and candidate
  - τ = temperature (controls sharpness of transfer)
  - p₀(φ) = reference prior on parameters (broad/uninformative)

The GP prior choice (kernel structure + hyperpriors) determines ψ,
which in turn determines p(φ | ψ). This is how qualitative beliefs
about data patterns (periodicity, trends, smoothness) get transferred
into quantitative priors on model parameters (amplitude, frequency, slope).

Expected qualitative behavior:
  - Informative GP prior → tight ψ → sharp induced prior near truth
  - Vague GP prior → wide ψ → diffuse induced prior, less informative
  - Misspecified GP prior → biased ψ → shifted induced prior, may mislead
"""

import numpy as np
from typing import List, Dict, Optional, Tuple, Callable
from dataclasses import dataclass

from bistar_gp.bms_star import GPPosteriorSample, METRICS
from bistar_gp.candidates import CandidateResult


# ═══════════════════════════════════════════════════════════════════
# Parameter Space Definitions
# ═══════════════════════════════════════════════════════════════════

@dataclass
class ParameterSpec:
    """Specification for one model parameter."""
    name: str
    bounds: Tuple[float, float]    # sampling range
    true_value: Optional[float]     # ground truth (if known)
    mle_value: Optional[float] = None


@dataclass
class ModelParameterSpace:
    """Parameter space for a candidate model."""
    model_name: str
    param_specs: List[ParameterSpec]
    predict_fn: Callable  # (x_eval, param_dict) → mean array
    noise_param: str = "sigma"  # name of the noise parameter

    @property
    def param_names(self):
        return [ps.name for ps in self.param_specs]

    @property
    def n_params(self):
        return len(self.param_specs)

    def sample_reference_prior(self, n_samples: int, seed: int = None) -> np.ndarray:
        """
        Sample from broad reference prior p₀(φ).
        Uniform over bounds for each parameter.
        Returns (n_samples, n_params).
        """
        rng = np.random.RandomState(seed)
        samples = np.zeros((n_samples, self.n_params))
        for j, ps in enumerate(self.param_specs):
            samples[:, j] = rng.uniform(ps.bounds[0], ps.bounds[1], n_samples)
        return samples


def build_toy_parameter_spaces(true_params: Dict = None) -> Dict[str, ModelParameterSpace]:
    """
    Build parameter spaces for the four toy candidate models.

    True data: y = sin(x) + 0.25x + noise(0.3)
    """
    if true_params is None:
        true_params = {
            "A": 1.0, "omega": 1.0, "phi": 0.0,
            "slope": 0.25, "intercept": 0.0, "sigma": 0.3,
        }

    spaces = {}

    # Linear: y = a*x + b + eps
    spaces["Linear"] = ModelParameterSpace(
        model_name="Linear",
        param_specs=[
            ParameterSpec("a", (-1.0, 1.0), true_value=0.25),
            ParameterSpec("b", (-3.0, 3.0), true_value=0.0),
            ParameterSpec("sigma", (0.05, 3.0), true_value=None),  # no "true" for wrong model
        ],
        predict_fn=lambda x, p: p["a"] * x + p["b"],
    )

    # Sinusoidal: y = A*sin(omega*x + phi) + eps
    spaces["Sinusoidal"] = ModelParameterSpace(
        model_name="Sinusoidal",
        param_specs=[
            ParameterSpec("A", (0.1, 3.0), true_value=1.0),
            ParameterSpec("omega", (0.3, 3.0), true_value=1.0),
            ParameterSpec("phi", (-np.pi, np.pi), true_value=0.0),
            ParameterSpec("sigma", (0.05, 3.0), true_value=None),
        ],
        predict_fn=lambda x, p: p["A"] * np.sin(p["omega"] * x + p["phi"]),
    )

    # Sin+Linear: y = A*sin(omega*x + phi) + b*x + c + eps
    spaces["Sin+Linear"] = ModelParameterSpace(
        model_name="Sin+Linear",
        param_specs=[
            ParameterSpec("A", (0.1, 3.0), true_value=1.0),
            ParameterSpec("omega", (0.3, 3.0), true_value=1.0),
            ParameterSpec("phi", (-np.pi, np.pi), true_value=0.0),
            ParameterSpec("b", (-1.0, 1.0), true_value=0.25),
            ParameterSpec("c", (-3.0, 3.0), true_value=0.0),
            ParameterSpec("sigma", (0.05, 3.0), true_value=None),
        ],
        predict_fn=lambda x, p: (p["A"] * np.sin(p["omega"] * x + p["phi"])
                                  + p["b"] * x + p["c"]),
    )

    # Quadratic: y = a*x^2 + b*x + c + eps
    spaces["Quadratic"] = ModelParameterSpace(
        model_name="Quadratic",
        param_specs=[
            ParameterSpec("a", (-0.2, 0.2), true_value=None),
            ParameterSpec("b", (-1.0, 1.0), true_value=None),
            ParameterSpec("c", (-3.0, 3.0), true_value=None),
            ParameterSpec("sigma", (0.05, 3.0), true_value=None),
        ],
        predict_fn=lambda x, p: p["a"] * x**2 + p["b"] * x + p["c"],
    )

    return spaces


# ═══════════════════════════════════════════════════════════════════
# GP-Induced Prior Computation
# ═══════════════════════════════════════════════════════════════════

@dataclass
class InducedPriorResult:
    """Result of computing the GP-induced prior over model parameters."""
    model_name: str
    prior_name: str          # which GP prior config
    param_names: List[str]
    param_samples: np.ndarray   # (n_samples, n_params) — reference prior draws
    log_weights: np.ndarray     # (n_samples,) — log induced prior weight per sample
    weights: np.ndarray         # (n_samples,) — normalized weights
    G_per_sample: np.ndarray    # (n_samples,) — average G across GP samples
    tau: float
    effective_sample_size: float
    mle_values: Optional[Dict[str, float]] = None
    true_values: Optional[Dict[str, float]] = None


def compute_induced_prior(
    param_space: ModelParameterSpace,
    gp_samples: List[GPPosteriorSample],
    x_eval: np.ndarray,
    log_mlls: np.ndarray,
    metric_name: str = "pw_kl_vcal",
    tau: float = 1.0,
    n_param_samples: int = 10000,
    seed: int = 42,
) -> InducedPriorResult:
    """
    Compute the GP-induced prior over model parameters.

    For each parameter sample φ:
      1. Generate candidate prediction θ(φ) at x_eval
      2. Compute MLL-weighted average G across GP samples:
         Ḡ(φ) = Σ_i w_i G(ψ_i, θ(φ)) / Σ_i w_i
      3. Induced prior weight: exp(-Ḡ(φ) / τ)

    Uses MLL-weighting (Strategy 3) since we showed it works best.
    """
    metric_fn = METRICS[metric_name]

    # Prepare MLL weights
    valid = np.isfinite(log_mlls)
    lw = log_mlls.copy()
    lw[~valid] = -np.inf
    lw -= lw[valid].max()
    mll_weights = np.exp(lw)
    mll_weights /= mll_weights.sum()

    # Sample parameters from reference prior
    param_samples = param_space.sample_reference_prior(n_param_samples, seed=seed)

    # For each parameter sample, compute MLL-weighted G
    G_per_sample = np.zeros(n_param_samples)

    for s_idx in range(n_param_samples):
        # Build parameter dict
        param_dict = {ps.name: param_samples[s_idx, j]
                      for j, ps in enumerate(param_space.param_specs)}

        # Generate prediction
        try:
            mu_theta = param_space.predict_fn(x_eval, param_dict)
        except Exception:
            G_per_sample[s_idx] = np.inf
            continue

        sigma = param_dict.get(param_space.noise_param, 0.3)
        sigma2 = sigma ** 2
        n_eval = len(x_eval)
        cov_theta = sigma2 * np.eye(n_eval)

        # MLL-weighted average G across GP samples
        g_vals = np.zeros(len(gp_samples))
        for i, psi in enumerate(gp_samples):
            try:
                g_vals[i] = metric_fn(psi.mean, psi.cov, mu_theta, cov_theta)
            except (np.linalg.LinAlgError, ValueError):
                g_vals[i] = np.inf

        # Replace inf with large value
        finite_mask = np.isfinite(g_vals)
        if finite_mask.any():
            g_vals[~finite_mask] = 10 * np.max(g_vals[finite_mask])
        else:
            g_vals[:] = 1e6

        G_per_sample[s_idx] = np.sum(mll_weights * g_vals)

    # Compute induced prior weights
    log_weights = -G_per_sample / tau

    # Numerical stability
    finite = np.isfinite(log_weights)
    if finite.any():
        log_weights[~finite] = -np.inf
        log_weights -= np.max(log_weights[finite])
    else:
        log_weights[:] = 0.0

    weights = np.exp(log_weights)
    total = weights.sum()
    if total > 0:
        weights /= total
    else:
        weights[:] = 1.0 / n_param_samples

    # Effective sample size
    ess = 1.0 / np.sum(weights ** 2) if np.sum(weights ** 2) > 0 else 0

    # Collect true and MLE values
    true_vals = {ps.name: ps.true_value for ps in param_space.param_specs
                 if ps.true_value is not None}
    mle_vals = {ps.name: ps.mle_value for ps in param_space.param_specs
                if ps.mle_value is not None}

    # Weighted statistics
    print(f"\n  [{param_space.model_name}] Induced prior (τ={tau}, metric={metric_name}):")
    print(f"    ESS: {ess:.0f} / {n_param_samples}")
    for j, ps in enumerate(param_space.param_specs):
        w_mean = np.sum(weights * param_samples[:, j])
        w_std = np.sqrt(np.sum(weights * (param_samples[:, j] - w_mean)**2))
        true_str = f"  true={ps.true_value}" if ps.true_value is not None else ""
        print(f"    {ps.name:<8}: mean={w_mean:.4f} ± {w_std:.4f}{true_str}")

    return InducedPriorResult(
        model_name=param_space.model_name,
        prior_name="",  # set by caller
        param_names=[ps.name for ps in param_space.param_specs],
        param_samples=param_samples,
        log_weights=log_weights + np.log(total) if total > 0 else log_weights,
        weights=weights,
        G_per_sample=G_per_sample,
        tau=tau,
        effective_sample_size=ess,
        mle_values=mle_vals if mle_vals else None,
        true_values=true_vals if true_vals else None,
    )


def compute_model_evidence_induced(
    induced_prior: InducedPriorResult,
    x_train: np.ndarray,
    y_train: np.ndarray,
    param_space: ModelParameterSpace,
) -> float:
    """
    Compute marginal likelihood under the GP-induced prior:

      p(y | M_j, ψ) = ∫ p(y | φ, M_j) p(φ | ψ) dφ
                     ≈ Σ_s w_s · p(y | φ_s, M_j)

    where w_s are the induced prior weights and φ_s are parameter samples.
    This is importance sampling with the induced prior as the weight.
    """
    n_samples = len(induced_prior.weights)
    log_liks = np.zeros(n_samples)

    for s_idx in range(n_samples):
        param_dict = {name: induced_prior.param_samples[s_idx, j]
                      for j, name in enumerate(induced_prior.param_names)}

        try:
            mu = param_space.predict_fn(x_train, param_dict)
            sigma = param_dict.get(param_space.noise_param, 0.3)
            sigma2 = sigma ** 2
            residuals = y_train - mu
            n = len(y_train)
            log_liks[s_idx] = -0.5 * n * np.log(2 * np.pi * sigma2) - 0.5 * np.sum(residuals**2) / sigma2
        except Exception:
            log_liks[s_idx] = -np.inf

    # Weighted average: Σ w_s * p(y|φ_s)
    # In log space: log(Σ w_s exp(log_lik_s))
    log_evidence = _log_sum_exp(np.log(induced_prior.weights + 1e-300) + log_liks)

    return log_evidence


def _log_sum_exp(x):
    """Numerically stable log-sum-exp."""
    x = x[np.isfinite(x)]
    if len(x) == 0:
        return -np.inf
    c = x.max()
    return c + np.log(np.sum(np.exp(x - c)))


def compute_all_model_evidences(
    induced_priors: Dict[str, InducedPriorResult],
    x_train: np.ndarray,
    y_train: np.ndarray,
    param_spaces: Dict[str, ModelParameterSpace],
) -> Dict[str, float]:
    """
    Compute model evidence for all candidates under their induced priors.
    Returns dict of model_name → log evidence.
    """
    evidences = {}
    for model_name, ip in induced_priors.items():
        evidences[model_name] = compute_model_evidence_induced(
            ip, x_train, y_train, param_spaces[model_name]
        )
        print(f"    {model_name}: log evidence = {evidences[model_name]:.2f}")

    # Compute posteriors (with equal model priors)
    log_evs = np.array(list(evidences.values()))
    names = list(evidences.keys())
    log_evs_shifted = log_evs - log_evs.max()
    posteriors = np.exp(log_evs_shifted)
    posteriors /= posteriors.sum()

    print(f"\n  Model posteriors (induced prior):")
    for name, p in zip(names, posteriors):
        print(f"    {name:<15} p = {p:.4f}")

    return evidences


# ═══════════════════════════════════════════════════════════════════
# Visualization
# ═══════════════════════════════════════════════════════════════════

def plot_induced_prior_marginals(
    induced_prior: InducedPriorResult,
    figsize: tuple = None,
):
    """
    Plot weighted marginal distributions for each parameter.
    Shows how the GP sculpts the parameter prior.
    """
    import matplotlib.pyplot as plt

    n_params = len(induced_prior.param_names)
    ncols = min(3, n_params)
    nrows = (n_params + ncols - 1) // ncols
    if figsize is None:
        figsize = (4.5 * ncols, 3.5 * nrows)

    fig, axes = plt.subplots(nrows, ncols, figsize=figsize)
    axes = np.atleast_2d(axes).flatten()

    for j, name in enumerate(induced_prior.param_names):
        ax = axes[j]
        vals = induced_prior.param_samples[:, j]
        w = induced_prior.weights

        # Reference prior (unweighted histogram)
        ax.hist(vals, bins=50, density=True, alpha=0.3, color='gray',
                label='Reference prior p₀(φ)')

        # Induced prior (weighted histogram)
        ax.hist(vals, bins=50, weights=w, density=True, alpha=0.6,
                color='steelblue', label='Induced prior p(φ|ψ)')

        # True value
        if (induced_prior.true_values and
                name in induced_prior.true_values and
                induced_prior.true_values[name] is not None):
            ax.axvline(induced_prior.true_values[name], color='red',
                       linestyle='--', linewidth=2, label=f'True = {induced_prior.true_values[name]}')

        # MLE value
        if (induced_prior.mle_values and
                name in induced_prior.mle_values and
                induced_prior.mle_values[name] is not None):
            ax.axvline(induced_prior.mle_values[name], color='orange',
                       linestyle=':', linewidth=2, label=f'MLE = {induced_prior.mle_values[name]:.3f}')

        # Weighted mean
        w_mean = np.sum(w * vals)
        ax.axvline(w_mean, color='steelblue', linestyle='-', linewidth=1.5,
                   alpha=0.7, label=f'Induced mean = {w_mean:.3f}')

        ax.set_xlabel(name, fontsize=11)
        ax.set_ylabel('Density', fontsize=9)
        ax.legend(fontsize=7)
        ax.grid(True, alpha=0.2)

    for j in range(n_params, len(axes)):
        axes[j].set_visible(False)

    fig.suptitle(f"GP-Induced Prior — {induced_prior.model_name} "
                 f"(prior: {induced_prior.prior_name}, τ={induced_prior.tau})",
                 fontsize=13)
    fig.tight_layout()
    return fig


def plot_induced_prior_2d(
    induced_prior: InducedPriorResult,
    param_x: str,
    param_y: str,
    figsize: tuple = (6, 5),
):
    """
    2D scatter of induced prior over two parameters.
    Point size/color shows weight.
    """
    import matplotlib.pyplot as plt

    idx_x = induced_prior.param_names.index(param_x)
    idx_y = induced_prior.param_names.index(param_y)
    x = induced_prior.param_samples[:, idx_x]
    y = induced_prior.param_samples[:, idx_y]
    w = induced_prior.weights

    # Only plot top-weighted samples for clarity
    threshold = np.percentile(w, 90)
    mask = w > threshold

    fig, ax = plt.subplots(figsize=figsize)

    # Background: all samples (faint)
    ax.scatter(x, y, s=1, alpha=0.1, color='gray')

    # Foreground: high-weight samples
    sc = ax.scatter(x[mask], y[mask], s=20, c=w[mask],
                    cmap='viridis', alpha=0.7, edgecolors='none')
    plt.colorbar(sc, ax=ax, label='Induced prior weight')

    # True values
    true_x = (induced_prior.true_values or {}).get(param_x)
    true_y = (induced_prior.true_values or {}).get(param_y)
    if true_x is not None and true_y is not None:
        ax.scatter([true_x], [true_y], marker='*', s=200, color='red',
                   edgecolors='black', linewidth=1, zorder=10, label='True')

    ax.set_xlabel(param_x, fontsize=12)
    ax.set_ylabel(param_y, fontsize=12)
    ax.set_title(f"Induced Prior — {induced_prior.model_name} "
                 f"({induced_prior.prior_name})", fontsize=12)
    ax.legend()
    ax.grid(True, alpha=0.2)
    fig.tight_layout()
    return fig


def plot_prior_comparison_marginals(
    induced_priors_by_prior: Dict[str, InducedPriorResult],
    param_name: str,
    figsize: tuple = (8, 5),
):
    """
    Compare induced prior marginals across GP prior configs for one parameter.

    This is the key BI* demonstration: same model, same data, but different
    GP priors → different induced priors on model parameters.
    """
    import matplotlib.pyplot as plt

    colors = {
        'informative': '#2ecc71',
        'vague': '#3498db',
        'misspecified_tight': '#e74c3c',
        'low_noise': '#9b59b6',
        'high_noise': '#f39c12',
    }

    fig, ax = plt.subplots(figsize=figsize)

    for prior_name, ip in induced_priors_by_prior.items():
        j = ip.param_names.index(param_name)
        vals = ip.param_samples[:, j]
        w = ip.weights

        # Weighted KDE approximation via histogram
        color = colors.get(prior_name, 'gray')
        ax.hist(vals, bins=60, weights=w, density=True, alpha=0.4,
                color=color, label=f'{prior_name}')

        # Weighted mean line
        w_mean = np.sum(w * vals)
        ax.axvline(w_mean, color=color, linestyle='--', linewidth=1.5, alpha=0.8)

    # True value
    first_ip = list(induced_priors_by_prior.values())[0]
    true_val = (first_ip.true_values or {}).get(param_name)
    if true_val is not None:
        ax.axvline(true_val, color='black', linestyle='-', linewidth=2,
                   label=f'True = {true_val}')

    model_name = first_ip.model_name
    ax.set_xlabel(param_name, fontsize=12)
    ax.set_ylabel('Induced Prior Density', fontsize=11)
    ax.set_title(f"Prior Transfer: How GP Prior Shapes {model_name}'s '{param_name}' Prior",
                 fontsize=13)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.2)
    fig.tight_layout()
    return fig


def plot_evidence_comparison(
    evidences_by_prior: Dict[str, Dict[str, float]],
    figsize: tuple = None,
):
    """
    Bar chart: model posteriors under induced priors, grouped by GP prior.

    Shows how GP prior choice affects model selection outcome.
    """
    import matplotlib.pyplot as plt

    prior_names = list(evidences_by_prior.keys())
    model_names = list(evidences_by_prior[prior_names[0]].keys())
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
            evs = evidences_by_prior[prior_name]
            log_evs = np.array(list(evs.values()))
            log_evs -= log_evs.max()
            ps = np.exp(log_evs) / np.exp(log_evs).sum()
            posteriors.append(ps[m_idx])

        offset = (m_idx - n_models / 2 + 0.5) * width
        ax.bar(x + offset, posteriors, width, label=model_name,
               color=colors[m_idx % len(colors)])

    ax.set_xticks(x)
    ax.set_xticklabels(prior_names, fontsize=10)
    ax.set_ylabel("Model Posterior (induced prior)", fontsize=11)
    ax.set_title("BI* Model Selection: How GP Prior Affects Model Ranking", fontsize=13)
    ax.set_ylim(0, 1)
    ax.axhline(0.25, color='gray', linestyle=':', alpha=0.5, label='uniform')
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.2, axis='y')
    fig.tight_layout()
    return fig


def plot_prior_sharpness_summary(
    induced_priors_all: Dict[str, Dict[str, InducedPriorResult]],
    figsize: tuple = None,
):
    """
    Summary plot: ESS (effective sample size) as measure of how much
    the GP prior concentrates each model's parameter prior.

    Higher ESS = more diffuse induced prior = less information transfer.
    Lower ESS = sharper induced prior = more information transfer.
    """
    import matplotlib.pyplot as plt

    prior_names = list(induced_priors_all.keys())
    model_names = list(induced_priors_all[prior_names[0]].keys())
    n_priors = len(prior_names)
    n_models = len(model_names)

    colors = ['#e74c3c', '#3498db', '#2ecc71', '#9b59b6']

    if figsize is None:
        figsize = (max(10, 2.5 * n_priors), 5)

    fig, ax = plt.subplots(figsize=figsize)
    x = np.arange(n_priors)
    width = 0.8 / n_models

    for m_idx, model_name in enumerate(model_names):
        ess_vals = []
        for prior_name in prior_names:
            ip = induced_priors_all[prior_name][model_name]
            ess_vals.append(ip.effective_sample_size)

        offset = (m_idx - n_models / 2 + 0.5) * width
        ax.bar(x + offset, ess_vals, width, label=model_name,
               color=colors[m_idx % len(colors)])

    ax.set_xticks(x)
    ax.set_xticklabels(prior_names, fontsize=10)
    ax.set_ylabel("Effective Sample Size (ESS)", fontsize=11)
    ax.set_title("Prior Information Transfer: Lower ESS = Sharper Induced Prior",
                 fontsize=13)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.2, axis='y')
    fig.tight_layout()
    return fig
