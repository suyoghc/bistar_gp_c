"""
metrics_v2.py — Calibrated divergence metrics for BMS*

Addresses the variance-ratio trap: standard KL penalizes correct-but-confident
models (small σ²_θ) when comparing against GP predictives (large σ²_ψ that
includes hyperparameter uncertainty). Wrong models with inflated noise
accidentally "match" the GP's width and get lower divergence.

Three families of fixes, each isolating a different aspect of the comparison:

  Group A: Variance-Calibrated — replace θ's variance with ψ's before
           computing the divergence. Forces comparison onto mean accuracy,
           with GP uncertainty as natural weighting.

  Group B: Mean-Only — set all variances to 1. Pure mean comparison
           inheriting the geometric properties of the parent divergence
           (bounded for Hellinger, information-theoretic for KL).

  Group C: GP-Anchored — evaluate θ's mean under ψ's distribution.
           "How probable is θ's prediction under the GP posterior?"
           Naturally weights by GP uncertainty.

All metrics follow the standard signature:
    f(mu_psi, cov_psi, mu_theta, cov_theta) -> float

Import this module to register the new metrics into bms_star.METRICS.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple

# We'll register into the existing METRICS dict
from bistar_gp.bms_star import METRICS, _extract_marginals, GPPosteriorSample


# ═══════════════════════════════════════════════════════════════════
# Group A: Variance-Calibrated Metrics
#
# Idea: Replace σ²_θ with σ²_ψ at each point before computing divergence.
# This removes the "width matching" incentive entirely.
# ═══════════════════════════════════════════════════════════════════

def pw_kl_vcal(mu_psi, cov_psi, mu_theta, cov_theta):
    """
    Variance-calibrated pointwise KL(ψ || θ_cal).

    Replace θ's variance with ψ's variance at each location.
    KL(N(μ_ψ, σ²_ψ) || N(μ_θ, σ²_ψ)) = (μ_θ - μ_ψ)² / (2σ²_ψ)

    Reduces to GP-uncertainty-weighted MSE. Uncertain GP regions
    contribute less — exactly the right behavior.
    """
    mu_p, var_p = _extract_marginals(mu_psi, cov_psi)
    mu_q, _     = _extract_marginals(mu_theta, cov_theta)
    return np.mean(0.5 * (mu_q - mu_p)**2 / var_p)


def pw_hellinger_vcal(mu_psi, cov_psi, mu_theta, cov_theta):
    """
    Variance-calibrated pointwise Hellinger.

    With σ²_θ = σ²_ψ at each point:
      D_B = (μ_ψ - μ_θ)² / (4σ²_ψ)
      H²  = 1 - exp(-D_B)

    Bounded in [0, 1], GP-uncertainty-weighted, saturates for large errors.
    """
    mu_p, var_p = _extract_marginals(mu_psi, cov_psi)
    mu_q, _     = _extract_marginals(mu_theta, cov_theta)
    db = (mu_p - mu_q)**2 / (4.0 * var_p)
    return np.mean(1.0 - np.exp(-db))


def pw_kl_sym_vcal(mu_psi, cov_psi, mu_theta, cov_theta):
    """
    Variance-calibrated symmetric KL.

    With matched variances, forward and backward KL are identical:
      KL(ψ||θ_cal) = KL(θ_cal||ψ) = (μ_θ - μ_ψ)² / (2σ²_ψ)

    So symmetric = forward = backward. Included for completeness
    and to verify this symmetry in practice.
    """
    # Identical to pw_kl_vcal when variances match
    return pw_kl_vcal(mu_psi, cov_psi, mu_theta, cov_theta)


# ═══════════════════════════════════════════════════════════════════
# Group B: Mean-Only Metrics
#
# Idea: Set all variances to 1 (or any constant). Pure mean comparison
# with the divergence's geometric properties preserved.
# ═══════════════════════════════════════════════════════════════════

def pw_hellinger_mean(mu_psi, cov_psi, mu_theta, cov_theta):
    """
    Mean-only pointwise Hellinger.

    Set σ²_ψ = σ²_θ = 1 at every point:
      D_B = (μ_ψ - μ_θ)² / 4
      H²  = 1 - exp(-(μ_ψ - μ_θ)² / 4)

    Bounded [0, 1], symmetric. Large mean errors saturate at 1,
    so outlier GP samples can't dominate. No variance information used.
    """
    mu_p = mu_psi if isinstance(mu_psi, np.ndarray) else np.array(mu_psi)
    mu_q = mu_theta if isinstance(mu_theta, np.ndarray) else np.array(mu_theta)
    db = (mu_p - mu_q)**2 / 4.0
    return np.mean(1.0 - np.exp(-db))


def pw_kl_mean(mu_psi, cov_psi, mu_theta, cov_theta):
    """
    Mean-only pointwise KL.

    Set σ²_ψ = σ²_θ = 1:
      KL = (μ_θ - μ_ψ)² / 2

    Equivalent to MSE/2. Included to show that MSE *is* KL
    when variance is removed from the picture.
    """
    mu_p = mu_psi if isinstance(mu_psi, np.ndarray) else np.array(mu_psi)
    mu_q = mu_theta if isinstance(mu_theta, np.ndarray) else np.array(mu_theta)
    return np.mean(0.5 * (mu_q - mu_p)**2)


# ═══════════════════════════════════════════════════════════════════
# Group C: GP-Anchored Metrics
#
# Idea: Score θ's prediction under ψ's distribution.
# "How likely is θ's mean under the GP posterior at each point?"
# ═══════════════════════════════════════════════════════════════════

def pw_nll_gp(mu_psi, cov_psi, mu_theta, cov_theta):
    """
    GP-anchored NLL: negative log-likelihood of θ's mean under ψ's marginals.

    -log N(μ_θ | μ_ψ, σ²_ψ) = 0.5*ln(2π*σ²_ψ) + 0.5*(μ_θ - μ_ψ)²/σ²_ψ

    The constant 0.5*ln(2πσ²_ψ) is the same for all candidates (it depends
    only on the GP sample), so for ranking it's equivalent to pw_kl_vcal.
    But for absolute G values and τ sensitivity the constant matters.

    Contrast with pw_nll which evaluates ψ's mean under θ's distribution —
    that penalizes θ for being narrow.
    """
    mu_p, var_p = _extract_marginals(mu_psi, cov_psi)
    mu_q, _     = _extract_marginals(mu_theta, cov_theta)
    return np.mean(0.5 * np.log(2 * np.pi * var_p) + 0.5 * (mu_q - mu_p)**2 / var_p)


def pw_nmse(mu_psi, cov_psi, mu_theta, cov_theta):
    """
    Normalized MSE: mean squared error weighted by GP uncertainty.

    avg (μ_θ - μ_ψ)² / σ²_ψ

    = 2 * pw_kl_vcal (exactly).

    Included as a named metric because "normalized MSE" is a more
    intuitive description than "variance-calibrated KL" for some audiences.
    The factor of 2 doesn't affect ranking but affects τ sensitivity.
    """
    mu_p, var_p = _extract_marginals(mu_psi, cov_psi)
    mu_q, _     = _extract_marginals(mu_theta, cov_theta)
    return np.mean((mu_q - mu_p)**2 / var_p)


# ═══════════════════════════════════════════════════════════════════
# Registration
# ═══════════════════════════════════════════════════════════════════

METRICS_V2 = {
    # Group A: Variance-Calibrated
    "pw_kl_vcal":         pw_kl_vcal,
    "pw_hellinger_vcal":  pw_hellinger_vcal,
    "pw_kl_sym_vcal":     pw_kl_sym_vcal,

    # Group B: Mean-Only
    "pw_hellinger_mean":  pw_hellinger_mean,
    "pw_kl_mean":         pw_kl_mean,

    # Group C: GP-Anchored
    "pw_nll_gp":          pw_nll_gp,
    "pw_nmse":            pw_nmse,
}

# Register into the main METRICS dict
METRICS.update(METRICS_V2)


# ═══════════════════════════════════════════════════════════════════
# Diagnostics
# ═══════════════════════════════════════════════════════════════════

def diagnose_G_matrix(G_matrix: np.ndarray,
                      instance_names: List[str],
                      metric_name: str = "") -> Dict:
    """
    Diagnostic summary of a G matrix.

    Reports mean, median, std, min, max per candidate, plus the
    inter-candidate spread (how much the metric differentiates models).

    Returns a dict for programmatic use; also prints a readable table.
    """
    n_psi, n_theta = G_matrix.shape

    stats = {}
    print(f"\n  G-matrix diagnostics: {metric_name}")
    print(f"  {'─' * 70}")
    print(f"  {'Model':<15} {'Mean':>10} {'Median':>10} {'Std':>10} {'Min':>10} {'Max':>10}")
    print(f"  {'─' * 70}")

    means = []
    for j, name in enumerate(instance_names):
        col = G_matrix[:, j]
        s = {
            "mean": np.mean(col),
            "median": np.median(col),
            "std": np.std(col),
            "min": np.min(col),
            "max": np.max(col),
        }
        stats[name] = s
        means.append(s["mean"])
        print(f"  {name:<15} {s['mean']:>10.4f} {s['median']:>10.4f} "
              f"{s['std']:>10.4f} {s['min']:>10.4f} {s['max']:>10.4f}")

    # Inter-candidate spread: how distinguishable are the models?
    means = np.array(means)
    spread = means.max() - means.min()
    cv = np.std(means) / np.mean(means) if np.mean(means) > 0 else 0.0

    print(f"  {'─' * 70}")
    print(f"  Spread (max-min of means): {spread:.4f}")
    print(f"  CV of means:               {cv:.4f}")
    print(f"  Best candidate (lowest G): {instance_names[np.argmin(means)]}")
    print()

    stats["_spread"] = spread
    stats["_cv"] = cv
    stats["_best"] = instance_names[np.argmin(means)]

    return stats


def diagnose_all_metrics(gp_samples: list,
                         candidate_results: list,
                         metric_names: Optional[List[str]] = None) -> Dict[str, Dict]:
    """
    Run diagnostics across all specified metrics.

    Computes G matrix for each metric, prints per-candidate stats,
    and returns a summary dict.

    Args:
        gp_samples: list of GPPosteriorSample
        candidate_results: list of CandidateResult
        metric_names: which metrics to diagnose (default: all registered)

    Returns:
        diagnostics[metric_name] = stats dict from diagnose_G_matrix
    """
    from bistar_gp.bms_star import compute_G_matrix

    if metric_names is None:
        metric_names = list(METRICS.keys())

    instance_names = [cr.name for cr in candidate_results]
    all_stats = {}

    for metric_name in metric_names:
        G = compute_G_matrix(gp_samples, candidate_results, metric_name)
        stats = diagnose_G_matrix(G, instance_names, metric_name)
        all_stats[metric_name] = stats

    # Summary comparison table
    print(f"\n  {'═' * 75}")
    print(f"  SUMMARY: Which candidate wins (lowest mean G) per metric?")
    print(f"  {'─' * 75}")
    print(f"  {'Metric':<22} {'Best':<15} {'Spread':>10} {'CV':>10}")
    print(f"  {'─' * 75}")

    for m in metric_names:
        s = all_stats[m]
        print(f"  {m:<22} {s['_best']:<15} {s['_spread']:>10.4f} {s['_cv']:>10.4f}")
    print()

    return all_stats


def plot_G_diagnostic_comparison(all_stats: Dict[str, Dict],
                                 instance_names: List[str],
                                 metric_groups: Optional[Dict[str, List[str]]] = None):
    """
    Bar chart comparing mean G per candidate, grouped by metric family.

    Args:
        all_stats: output from diagnose_all_metrics
        instance_names: candidate model names
        metric_groups: optional grouping, e.g.
            {"Original PW": ["pw_kl_forward", ...], "Calibrated": ["pw_kl_vcal", ...]}
            If None, auto-groups by prefix.
    """
    import matplotlib.pyplot as plt

    if metric_groups is None:
        # Auto-group: original vs v2
        original = [m for m in all_stats if m in [
            "pw_kl_forward", "pw_kl_backward", "pw_kl_symmetric",
            "pw_hellinger", "pw_mse", "pw_nll",
            "kl_forward", "kl_backward", "kl_symmetric", "hellinger",
        ]]
        v2 = [m for m in all_stats if m in METRICS_V2]
        metric_groups = {}
        if original:
            metric_groups["Original"] = original
        if v2:
            metric_groups["Calibrated (v2)"] = v2

    n_groups = len(metric_groups)
    fig, axes = plt.subplots(1, n_groups, figsize=(7 * n_groups, 5))
    if n_groups == 1:
        axes = [axes]

    model_colors = ['#e74c3c', '#3498db', '#2ecc71', '#9b59b6']

    for ax, (group_name, metrics) in zip(axes, metric_groups.items()):
        n_metrics = len(metrics)
        n_models = len(instance_names)
        x = np.arange(n_metrics)
        width = 0.8 / n_models

        for m_idx, model_name in enumerate(instance_names):
            vals = []
            for metric_name in metrics:
                if metric_name in all_stats and model_name in all_stats[metric_name]:
                    vals.append(all_stats[metric_name][model_name]["mean"])
                else:
                    vals.append(0)
            offset = (m_idx - n_models / 2 + 0.5) * width
            ax.bar(x + offset, vals, width, label=model_name,
                   color=model_colors[m_idx % len(model_colors)])

        ax.set_xticks(x)
        ax.set_xticklabels(metrics, rotation=45, ha='right', fontsize=8)
        ax.set_ylabel("Mean G(ψ, θ)")
        ax.set_title(group_name, fontsize=12, fontweight='bold')
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.2, axis='y')

    fig.suptitle("Mean Divergence per Candidate — Original vs Calibrated", fontsize=14)
    fig.tight_layout()
    return fig


def plot_v2_tau_sensitivity(gp_samples: list,
                            candidate_results: list,
                            taus: np.ndarray = None,
                            figsize=None):
    """
    τ sensitivity curves for the v2 metrics only.

    Mirrors plot_bms_star_results but restricted to the new metrics,
    so you can see them side-by-side with the originals.
    """
    import matplotlib.pyplot as plt
    from bistar_gp.bms_star import compute_G_matrix, soft_transfer

    if taus is None:
        taus = np.logspace(-1, 2, 30)

    v2_names = list(METRICS_V2.keys())
    instance_names = [cr.name for cr in candidate_results]
    n_metrics = len(v2_names)
    ncols = min(4, n_metrics)
    nrows = (n_metrics + ncols - 1) // ncols
    if figsize is None:
        figsize = (4.5 * ncols, 3.5 * nrows)

    fig, axes = plt.subplots(nrows, ncols, figsize=figsize)
    axes = np.atleast_2d(axes).flatten()

    colors = ['#e74c3c', '#3498db', '#2ecc71', '#9b59b6']

    for ax_idx, metric_name in enumerate(v2_names):
        ax = axes[ax_idx]
        print(f"  Computing G matrix: {metric_name}...")
        G = compute_G_matrix(gp_samples, candidate_results, metric_name)

        posteriors = np.zeros((len(taus), len(instance_names)))
        for t_idx, tau in enumerate(taus):
            bms = soft_transfer(G, tau, instance_names)
            posteriors[t_idx] = bms.instance_posteriors

        for m_idx, name in enumerate(instance_names):
            ax.plot(taus, posteriors[:, m_idx], color=colors[m_idx],
                    linewidth=2, label=name)

        ax.set_xscale('log')
        ax.set_xlabel('τ', fontsize=9)
        ax.set_ylabel('Posterior', fontsize=9)
        ax.set_title(metric_name, fontsize=10)
        ax.set_ylim(0, 1)
        ax.legend(fontsize=7)
        ax.grid(True, alpha=0.3)

    for ax_idx in range(n_metrics, len(axes)):
        axes[ax_idx].set_visible(False)

    fig.suptitle("V2 Calibrated Metrics — τ Sensitivity", fontsize=14)
    fig.tight_layout()
    return fig
