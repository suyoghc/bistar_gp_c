"""
aggregation_v3.py — Alternative BMS* aggregation strategies

The v2 metrics showed that the variance-ratio trap was masking a deeper issue:
GP posterior mean variability across HMC samples. The correct model (Sin+Linear)
matches the *averaged* GP well but has high-variance G across individual samples.
The Boltzmann average rewards consistency over occasional excellence.

Three fixes, each attacking a different part of the problem:

  Strategy 1: AVERAGED GP POSTERIOR
    Collapse all GP samples into one averaged ψ̄, then compute G(ψ̄, θ) once.
    Bypasses sample-level averaging entirely.

  Strategy 2: ROBUST AGGREGATION
    Keep individual G values but replace Boltzmann with robust summaries:
    (a) Median G per candidate (robust to outlier samples)
    (b) Trimmed mean (drop worst 20% of GP samples per candidate)
    (c) Rank-based: for each ψ, rank candidates, then average ranks

  Strategy 3: MARGINAL LIKELIHOOD WEIGHTING
    Weight each HMC sample by p(y|X,θ_i) before averaging.
    High-likelihood samples (well-fitting hyperparameters) count more;
    outlier samples (very long/short lengthscales) get downweighted.
"""

import numpy as np
import torch
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from bistar_gp.bms_star import (
    GPPosteriorSample, METRICS, compute_G_matrix, BMSStarResult,
    _extract_marginals,
)

torch.set_default_dtype(torch.float64)


# ═══════════════════════════════════════════════════════════════════
# Strategy 1: Averaged GP Posterior
# ═══════════════════════════════════════════════════════════════════

def average_gp_posterior(gp_samples: List[GPPosteriorSample]) -> GPPosteriorSample:
    """
    Collapse GP samples into one averaged predictive distribution.

    The marginal predictive p(y*|X,y) = ∫ p(y*|X,y,θ) p(θ|X,y) dθ
    is approximated by the mixture of Gaussians from HMC samples.
    For a Gaussian mixture, the mean and covariance of the mixture are:

      μ̄ = (1/N) Σ μ_i
      Σ̄ = (1/N) Σ [Σ_i + (μ_i - μ̄)(μ_i - μ̄)^T]

    The second term captures the inter-sample mean spread — this is
    the "hyperparameter uncertainty" that inflates the marginal variance.
    """
    N = len(gp_samples)
    means = np.array([s.mean for s in gp_samples])   # (N, n_eval)
    mu_bar = means.mean(axis=0)                        # (n_eval,)

    # Average covariance + inter-sample mean spread
    n_eval = len(mu_bar)
    cov_bar = np.zeros((n_eval, n_eval))
    for s in gp_samples:
        diff = s.mean - mu_bar
        cov_bar += s.cov + np.outer(diff, diff)
    cov_bar /= N

    return GPPosteriorSample(
        mean=mu_bar,
        cov=cov_bar,
        hyperparameters={"averaged": True, "n_samples": N},
    )


def score_averaged_gp(gp_samples: List[GPPosteriorSample],
                      candidate_results: list,
                      metric_names: Optional[List[str]] = None,
                      ) -> Dict[str, np.ndarray]:
    """
    Strategy 1: Score candidates against the averaged GP posterior.

    No τ parameter needed — just one G value per candidate per metric.
    Returns normalized posteriors (lower G → higher posterior).

    Returns:
        results[metric_name] = {
            "G_values": np.ndarray (n_theta,),
            "posteriors": np.ndarray (n_theta,),  # softmax of -G
            "names": List[str],
        }
    """
    if metric_names is None:
        metric_names = ["pw_kl_vcal", "pw_hellinger_vcal", "pw_nll_gp",
                        "pw_mse", "pw_hellinger_mean"]

    psi_bar = average_gp_posterior(gp_samples)
    instance_names = [cr.name for cr in candidate_results]
    results = {}

    for metric_name in metric_names:
        metric_fn = METRICS[metric_name]
        G_values = np.array([
            metric_fn(psi_bar.mean, psi_bar.cov, cr.mean, cr.cov)
            for cr in candidate_results
        ])

        # Convert to posteriors: exp(-G) / Σ exp(-G)
        # Use log-space for stability
        log_scores = -G_values
        log_scores -= log_scores.max()
        scores = np.exp(log_scores)
        posteriors = scores / scores.sum()

        results[metric_name] = {
            "G_values": G_values,
            "posteriors": posteriors,
            "names": instance_names,
        }

        print(f"  [Averaged GP] {metric_name}:")
        for name, g, p in zip(instance_names, G_values, posteriors):
            print(f"    {name:<15} G={g:.4f}  posterior={p:.4f}")

    return results


# ═══════════════════════════════════════════════════════════════════
# Strategy 2: Robust Aggregation
# ═══════════════════════════════════════════════════════════════════

@dataclass
class RobustResult:
    """Results from robust aggregation."""
    metric_name: str
    method: str               # "median", "trimmed_mean", "rank"
    instance_names: List[str]
    summary_values: np.ndarray  # (n_theta,) — the summary statistic per candidate
    posteriors: np.ndarray      # (n_theta,) — normalized


def robust_median(G_matrix: np.ndarray,
                  instance_names: List[str],
                  metric_name: str = "") -> RobustResult:
    """
    Median G across GP samples per candidate.

    Robust to outlier GP samples (very short or very long lengthscale).
    Median minimizes absolute deviation — a single bad GP sample
    can't dominate the score.
    """
    medians = np.median(G_matrix, axis=0)

    # Lower G → better → higher posterior
    log_scores = -medians
    log_scores -= log_scores.max()
    scores = np.exp(log_scores)
    posteriors = scores / scores.sum()

    return RobustResult(
        metric_name=metric_name,
        method="median",
        instance_names=list(instance_names),
        summary_values=medians,
        posteriors=posteriors,
    )


def robust_trimmed_mean(G_matrix: np.ndarray,
                        instance_names: List[str],
                        trim_fraction: float = 0.2,
                        metric_name: str = "") -> RobustResult:
    """
    Trimmed mean: drop the top and bottom trim_fraction of G values
    per candidate before averaging.

    With trim_fraction=0.2 and 200 samples, drops the 40 highest and
    40 lowest G values per candidate. Removes both "too easy" and
    "too hard" GP samples.
    """
    n_psi = G_matrix.shape[0]
    n_trim = int(n_psi * trim_fraction)

    trimmed_means = np.zeros(G_matrix.shape[1])
    for j in range(G_matrix.shape[1]):
        col = np.sort(G_matrix[:, j])
        trimmed = col[n_trim:n_psi - n_trim] if n_trim > 0 else col
        trimmed_means[j] = trimmed.mean()

    log_scores = -trimmed_means
    log_scores -= log_scores.max()
    scores = np.exp(log_scores)
    posteriors = scores / scores.sum()

    return RobustResult(
        metric_name=metric_name,
        method=f"trimmed_mean_{trim_fraction:.0%}",
        instance_names=list(instance_names),
        summary_values=trimmed_means,
        posteriors=posteriors,
    )


def robust_rank(G_matrix: np.ndarray,
                instance_names: List[str],
                metric_name: str = "") -> RobustResult:
    """
    Rank-based aggregation: for each GP sample, rank candidates 1-K
    (1 = lowest G = best). Then average ranks across samples.

    Completely nonparametric — immune to scale differences between
    GP samples. A model that consistently ranks #1 or #2 wins,
    regardless of the absolute G values.
    """
    n_psi, n_theta = G_matrix.shape

    # For each row (GP sample), compute ranks
    ranks = np.zeros_like(G_matrix)
    for i in range(n_psi):
        ranks[i] = np.argsort(np.argsort(G_matrix[i])) + 1  # 1-indexed

    avg_ranks = ranks.mean(axis=0)

    # Lower rank → better → higher posterior
    # Convert: use exp(-rank) and normalize
    log_scores = -avg_ranks
    log_scores -= log_scores.max()
    scores = np.exp(log_scores)
    posteriors = scores / scores.sum()

    return RobustResult(
        metric_name=metric_name,
        method="rank",
        instance_names=list(instance_names),
        summary_values=avg_ranks,
        posteriors=posteriors,
    )


def run_robust_aggregation(gp_samples: List[GPPosteriorSample],
                           candidate_results: list,
                           metric_names: Optional[List[str]] = None,
                           ) -> Dict[str, Dict[str, RobustResult]]:
    """
    Run all three robust aggregation methods across metrics.

    Returns:
        results[metric_name][method] = RobustResult
    """
    if metric_names is None:
        metric_names = ["pw_kl_vcal", "pw_hellinger_vcal", "pw_nll_gp",
                        "pw_mse", "pw_hellinger_mean"]

    instance_names = [cr.name for cr in candidate_results]
    results = {}

    for metric_name in metric_names:
        print(f"\n  Computing G matrix: {metric_name}...")
        G = compute_G_matrix(gp_samples, candidate_results, metric_name)

        results[metric_name] = {
            "median": robust_median(G, instance_names, metric_name),
            "trimmed_mean": robust_trimmed_mean(G, instance_names, 0.2, metric_name),
            "rank": robust_rank(G, instance_names, metric_name),
        }

        for method_name, rr in results[metric_name].items():
            print(f"  [{method_name}] {metric_name}:")
            for name, sv, p in zip(rr.instance_names, rr.summary_values, rr.posteriors):
                print(f"    {name:<15} summary={sv:.4f}  posterior={p:.4f}")

    return results


# ═══════════════════════════════════════════════════════════════════
# Strategy 3: Marginal Likelihood Weighting
# ═══════════════════════════════════════════════════════════════════

def compute_log_marginal_likelihoods(
    gp_samples: List[GPPosteriorSample],
    x_train, y_train,
    kernel_builder, likelihood_builder=None,
    jitter: float = 1e-4,
) -> np.ndarray:
    """
    Compute log p(y | X, θ_i) for each HMC sample.

    log p(y|X,θ) = -0.5 * y^T (K+σ²I)^{-1} y
                   -0.5 * log|K+σ²I|
                   -n/2 * log(2π)

    Uses the same fresh-model rebuild approach as extract_gp_predictives.
    """
    from bistar_gp.model import build_model
    from bistar_gp.decompose import compute_cholesky

    x_t = x_train.double() if isinstance(x_train, torch.Tensor) else torch.tensor(x_train).double()
    y_t = y_train.double() if isinstance(y_train, torch.Tensor) else torch.tensor(y_train).double()
    n = len(x_t)

    import gpytorch
    from gpytorch.constraints import Positive
    from gpytorch.priors import GammaPrior

    if likelihood_builder is None:
        def likelihood_builder():
            return gpytorch.likelihoods.GaussianLikelihood(
                noise_constraint=Positive(),
                noise_prior=GammaPrior(1.75, 1.0),
            )

    log_mlls = np.zeros(len(gp_samples))

    for idx, sample in enumerate(gp_samples):
        try:
            kernels, names = kernel_builder()
            fresh_lik = likelihood_builder()
            fresh_model, fresh_lik = build_model(x_t, y_t, kernels, names, fresh_lik)

            # Set hyperparameters
            for pyro_name, val in sample.hyperparameters.items():
                try:
                    if "noise_covar.noise" in pyro_name:
                        fresh_lik.noise = val
                        continue
                    parts = pyro_name.split(".")
                    comp_idx = int(parts[1])
                    kernel = fresh_model.kernel_components[comp_idx]
                    if "base_kernel.lengthscale" in pyro_name:
                        kernel.base_kernel.lengthscale = val
                    elif "outputscale" in pyro_name:
                        kernel.outputscale = val
                    elif "variance" in pyro_name:
                        kernel.variance = val
                except (IndexError, AttributeError, RuntimeError):
                    continue

            fresh_model.eval()
            fresh_lik.eval()

            with torch.no_grad():
                noise_var = fresh_lik.noise.item()
                K_XX = fresh_model.covar_module(x_t, x_t).evaluate().detach()
                L = compute_cholesky(K_XX, noise_var, jitter)

                # α = (K + σ²I)^{-1} y
                alpha = torch.cholesky_solve(y_t.unsqueeze(-1), L).squeeze(-1)

                # log|K + σ²I| = 2 * sum(log(diag(L)))
                log_det = 2.0 * torch.sum(torch.log(torch.diag(L)))

                # log p(y|X,θ)
                data_fit = -0.5 * y_t.dot(alpha)
                complexity = -0.5 * log_det
                constant = -0.5 * n * np.log(2 * np.pi)

                log_mlls[idx] = (data_fit + complexity + constant).item()

        except (RuntimeError, ValueError):
            log_mlls[idx] = -np.inf

    # Report
    valid = np.isfinite(log_mlls)
    print(f"  Computed {valid.sum()}/{len(log_mlls)} valid log marginal likelihoods")
    if valid.any():
        print(f"    Range: [{log_mlls[valid].min():.2f}, {log_mlls[valid].max():.2f}]")
        print(f"    Mean:  {log_mlls[valid].mean():.2f}")

    return log_mlls


def soft_transfer_weighted(G_matrix: np.ndarray, tau: float,
                           instance_names: List[str],
                           log_weights: np.ndarray) -> BMSStarResult:
    """
    Weighted Boltzmann soft transfer.

    score(θ_j) = Σ_i w_i exp(-G_ij / τ)  /  Σ_i w_i

    where w_i = exp(log_weight_i - max(log_weight)).

    High marginal-likelihood samples contribute more.
    """
    n_psi, n_theta = G_matrix.shape

    # Normalize log weights to prevent overflow
    valid = np.isfinite(log_weights)
    if not valid.any():
        # Fallback to uniform
        w = np.ones(n_psi)
    else:
        lw = log_weights.copy()
        lw[~valid] = -np.inf
        lw -= lw[valid].max()
        w = np.exp(lw)

    # Weighted Boltzmann scores
    log_boltz = -G_matrix / tau
    log_boltz -= log_boltz.max(axis=0, keepdims=True)
    boltz = np.exp(log_boltz)

    # Weighted average
    instance_scores = (w[:, None] * boltz).sum(axis=0) / w.sum()

    total = instance_scores.sum()
    if total > 0:
        instance_posteriors = instance_scores / total
    else:
        instance_posteriors = np.ones(n_theta) / n_theta

    return BMSStarResult(
        metric_name="weighted",
        tau=tau,
        instance_names=list(instance_names),
        instance_scores=instance_scores,
        instance_posteriors=instance_posteriors,
        class_names=list(instance_names),
        class_posteriors=instance_posteriors.copy(),
        G_matrix=G_matrix,
    )


def run_weighted_bms_star(gp_samples: List[GPPosteriorSample],
                          candidate_results: list,
                          log_mlls: np.ndarray,
                          metric_names: Optional[List[str]] = None,
                          taus: np.ndarray = None,
                          ) -> Dict[str, Dict[float, BMSStarResult]]:
    """
    Run BMS* with marginal likelihood weighting across metrics × τ.

    Same structure as run_bms_star but with weighted aggregation.
    """
    if metric_names is None:
        metric_names = ["pw_kl_vcal", "pw_hellinger_vcal", "pw_nll_gp",
                        "pw_mse", "pw_hellinger_mean"]
    if taus is None:
        taus = np.logspace(-1, 2, 30)

    instance_names = [cr.name for cr in candidate_results]
    results = {}

    for metric_name in metric_names:
        print(f"\n  [Weighted] Computing G matrix: {metric_name}...")
        G = compute_G_matrix(gp_samples, candidate_results, metric_name)

        results[metric_name] = {}
        for tau in taus:
            bms = soft_transfer_weighted(G, tau, instance_names, log_mlls)
            bms.metric_name = metric_name
            results[metric_name][tau] = bms

    return results


# ═══════════════════════════════════════════════════════════════════
# Visualization
# ═══════════════════════════════════════════════════════════════════

def plot_strategy_comparison(
    averaged_results: Dict,
    robust_results: Dict,
    weighted_results: Dict,
    original_results: Dict = None,
    metric_name: str = "pw_kl_vcal",
    tau: float = 1.0,
    figsize: tuple = None,
):
    """
    Bar chart comparing all strategies for a single metric.

    Groups: Original Boltzmann, Averaged GP, Median, Trimmed Mean, Rank, Weighted
    """
    import matplotlib.pyplot as plt

    groups = []
    posteriors_list = []

    # Original Boltzmann (if provided)
    if original_results and metric_name in original_results:
        taus = sorted(original_results[metric_name].keys())
        closest = min(taus, key=lambda t: abs(t - tau))
        bms = original_results[metric_name][closest]
        groups.append("Boltzmann\n(original)")
        posteriors_list.append(bms.instance_posteriors)
        instance_names = bms.instance_names
    else:
        instance_names = None

    # Averaged GP
    if metric_name in averaged_results:
        ar = averaged_results[metric_name]
        groups.append("Averaged\nGP")
        posteriors_list.append(ar["posteriors"])
        if instance_names is None:
            instance_names = ar["names"]

    # Robust methods
    if metric_name in robust_results:
        for method in ["median", "trimmed_mean", "rank"]:
            rr = robust_results[metric_name][method]
            label = {"median": "Median", "trimmed_mean": "Trimmed\nMean",
                     "rank": "Rank"}[method]
            groups.append(label)
            posteriors_list.append(rr.posteriors)
            if instance_names is None:
                instance_names = rr.instance_names

    # Weighted Boltzmann
    if weighted_results and metric_name in weighted_results:
        taus_w = sorted(weighted_results[metric_name].keys())
        closest = min(taus_w, key=lambda t: abs(t - tau))
        bms_w = weighted_results[metric_name][closest]
        groups.append("MLL-\nWeighted")
        posteriors_list.append(bms_w.instance_posteriors)

    if not groups:
        print(f"  No results for metric {metric_name}")
        return None

    n_groups = len(groups)
    n_models = len(instance_names)
    colors = ['#e74c3c', '#3498db', '#2ecc71', '#9b59b6']

    if figsize is None:
        figsize = (max(10, 2 * n_groups), 5)

    fig, ax = plt.subplots(figsize=figsize)
    x = np.arange(n_groups)
    width = 0.8 / n_models

    for m_idx, model_name in enumerate(instance_names):
        vals = [p[m_idx] for p in posteriors_list]
        offset = (m_idx - n_models / 2 + 0.5) * width
        ax.bar(x + offset, vals, width, label=model_name,
               color=colors[m_idx % len(colors)])

    ax.set_xticks(x)
    ax.set_xticklabels(groups, fontsize=9)
    ax.set_ylabel("Posterior probability")
    ax.set_title(f"Strategy Comparison — {metric_name} (τ={tau:.1f})", fontsize=13)
    ax.set_ylim(0, 1)
    ax.axhline(0.25, color='gray', linestyle=':', alpha=0.5, label='uniform')
    ax.legend(fontsize=8, loc='upper right')
    ax.grid(True, alpha=0.2, axis='y')
    fig.tight_layout()
    return fig


def plot_all_strategies_grid(
    averaged_results: Dict,
    robust_results: Dict,
    weighted_results: Dict,
    original_results: Dict = None,
    metric_names: Optional[List[str]] = None,
    tau: float = 1.0,
    figsize: tuple = None,
):
    """
    Grid of strategy comparisons: one row per metric.
    """
    import matplotlib.pyplot as plt

    if metric_names is None:
        metric_names = list(averaged_results.keys())

    n_metrics = len(metric_names)
    if figsize is None:
        figsize = (14, 3.5 * n_metrics)

    fig, axes = plt.subplots(n_metrics, 1, figsize=figsize)
    if n_metrics == 1:
        axes = [axes]

    colors = ['#e74c3c', '#3498db', '#2ecc71', '#9b59b6']

    for ax, metric_name in zip(axes, metric_names):
        groups = []
        posteriors_list = []
        instance_names = None

        # Gather all strategies
        if original_results and metric_name in original_results:
            taus = sorted(original_results[metric_name].keys())
            closest = min(taus, key=lambda t: abs(t - tau))
            bms = original_results[metric_name][closest]
            groups.append("Boltzmann")
            posteriors_list.append(bms.instance_posteriors)
            instance_names = bms.instance_names

        if metric_name in averaged_results:
            groups.append("Avg GP")
            posteriors_list.append(averaged_results[metric_name]["posteriors"])
            if instance_names is None:
                instance_names = averaged_results[metric_name]["names"]

        if metric_name in robust_results:
            for method, label in [("median", "Median"), ("trimmed_mean", "Trimmed"),
                                  ("rank", "Rank")]:
                groups.append(label)
                posteriors_list.append(robust_results[metric_name][method].posteriors)

        if weighted_results and metric_name in weighted_results:
            taus_w = sorted(weighted_results[metric_name].keys())
            closest = min(taus_w, key=lambda t: abs(t - tau))
            groups.append("MLL-Wt")
            posteriors_list.append(weighted_results[metric_name][closest].instance_posteriors)

        n_groups = len(groups)
        n_models = len(instance_names) if instance_names else 0
        if n_groups == 0 or n_models == 0:
            continue

        x = np.arange(n_groups)
        width = 0.8 / n_models

        for m_idx, model_name in enumerate(instance_names):
            vals = [p[m_idx] for p in posteriors_list]
            offset = (m_idx - n_models / 2 + 0.5) * width
            ax.bar(x + offset, vals, width, label=model_name if ax == axes[0] else "",
                   color=colors[m_idx % len(colors)])

        ax.set_xticks(x)
        ax.set_xticklabels(groups, fontsize=9)
        ax.set_ylabel("Posterior", fontsize=9)
        ax.set_title(metric_name, fontsize=11, fontweight='bold')
        ax.set_ylim(0, 1)
        ax.axhline(0.25, color='gray', linestyle=':', alpha=0.3)
        ax.grid(True, alpha=0.2, axis='y')

    axes[0].legend(fontsize=8, loc='upper right')
    fig.suptitle(f"All Aggregation Strategies at τ = {tau:.1f}", fontsize=14)
    fig.tight_layout()
    return fig


def plot_weighted_tau_sensitivity(
    weighted_results: Dict[str, Dict[float, BMSStarResult]],
    figsize=None,
):
    """τ sensitivity curves for MLL-weighted Boltzmann."""
    import matplotlib.pyplot as plt

    metric_names = list(weighted_results.keys())
    n_metrics = len(metric_names)
    ncols = min(4, n_metrics)
    nrows = (n_metrics + ncols - 1) // ncols
    if figsize is None:
        figsize = (4.5 * ncols, 3.5 * nrows)

    fig, axes = plt.subplots(nrows, ncols, figsize=figsize)
    axes = np.atleast_2d(axes).flatten()
    colors = ['#e74c3c', '#3498db', '#2ecc71', '#9b59b6']

    for ax_idx, metric_name in enumerate(metric_names):
        ax = axes[ax_idx]
        taus = sorted(weighted_results[metric_name].keys())
        instance_names = weighted_results[metric_name][taus[0]].instance_names
        n_models = len(instance_names)

        posteriors = np.zeros((len(taus), n_models))
        for t_idx, tau in enumerate(taus):
            posteriors[t_idx] = weighted_results[metric_name][tau].instance_posteriors

        for m_idx, name in enumerate(instance_names):
            ax.plot(taus, posteriors[:, m_idx], color=colors[m_idx],
                    linewidth=2, label=name)

        ax.set_xscale('log')
        ax.set_ylim(0, 1)
        ax.set_xlabel('τ', fontsize=9)
        ax.set_ylabel('Posterior', fontsize=9)
        ax.set_title(f"{metric_name} (MLL-weighted)", fontsize=10)
        ax.legend(fontsize=7)
        ax.grid(True, alpha=0.3)

    for ax_idx in range(n_metrics, len(axes)):
        axes[ax_idx].set_visible(False)

    fig.suptitle("MLL-Weighted Boltzmann — τ Sensitivity", fontsize=14)
    fig.tight_layout()
    return fig


def plot_mll_distribution(log_mlls: np.ndarray, figsize=(8, 4)):
    """Histogram of log marginal likelihoods across HMC samples."""
    import matplotlib.pyplot as plt

    valid = log_mlls[np.isfinite(log_mlls)]
    fig, ax = plt.subplots(figsize=figsize)
    ax.hist(valid, bins=40, color='steelblue', alpha=0.7, edgecolor='white')
    ax.axvline(np.median(valid), color='red', linestyle='--', label=f'median={np.median(valid):.1f}')
    ax.axvline(np.mean(valid), color='orange', linestyle='--', label=f'mean={np.mean(valid):.1f}')
    ax.set_xlabel("Log Marginal Likelihood")
    ax.set_ylabel("Count")
    ax.set_title("HMC Sample Quality: log p(y|X,θ)")
    ax.legend()
    fig.tight_layout()
    return fig
