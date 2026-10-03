"""
Visualization for GP decomposition — reproduces thesis figure styles.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from typing import Optional, Dict

plt.rcParams.update({"font.size": 12, "axes.labelsize": 14, "figure.dpi": 150, "lines.linewidth": 1.5})

COLORS = {"data": "black", "true": "red", "mean": "orange", "band": "lightgreen", "samples": "steelblue", "bias": "green"}

TRACE_LABELS = {"function_draws": "function draws",
                "conditional_means": "per-draw conditional means"}


def _band(summary, mean, std, mass=0.95):
    """(lower, upper, label) for a posterior band (fix pass 2a, SYNTHESIS A-5).

    A summary carrying per-draw conditional moments gets the mixture's own
    central interval; mean +/- 2 sd of a hyperparameter mixture is not a 95%
    interval, so without those moments the band is labelled as what it is.
    """
    if getattr(summary, "conditional_means", None) is not None \
            and getattr(summary, "conditional_vars", None) is not None:
        lo, hi = summary.central_interval(mass)
        return lo, hi, f"{mass:.0%} central interval"
    return mean - 2 * std, mean + 2 * std, "mean ± 2 sd"


def _plot_traces(ax, x, traces, kind, n_samples):
    for i, trace in enumerate(traces[:n_samples]):
        ax.plot(x, trace, color=COLORS["samples"], alpha=0.15, linewidth=0.8,
                label=TRACE_LABELS.get(kind, kind) if i == 0 else None)


def _joint_draws(summary, n_samples, seed):
    """Joint draws from N(summary.mean, summary.cov) by eigendecomposition.

    Negative eigenvalues within 1e-8 of the largest eigenvalue's magnitude are
    roundoff and are clipped at zero (posterior covariances computed as
    K** - V'V carry about 1e-14 relative); a materially indefinite covariance
    raises (review round R9; a fixed Cholesky jitter failed on high-scale
    posteriors)."""
    cov = 0.5 * (summary.cov + summary.cov.T)
    w, v = np.linalg.eigh(cov)
    tol = 1e-8 * max(np.abs(w).max(), np.finfo(float).tiny)
    if w.min() < -tol:
        raise ValueError(f"posterior covariance is materially indefinite (minimum "
                         f"eigenvalue {w.min():.3g}, tolerance {tol:.3g})")
    z = np.random.default_rng(seed).standard_normal((n_samples, len(w)))
    return summary.mean + (z * np.sqrt(np.clip(w, 0.0, None))) @ v.T


def plot_full_prediction(result, true_func=None, title="GP Prediction", n_samples=15, ax=None,
                         seed=0):
    """Full GP prediction — thesis Fig 10a style.

    For a result produced by this package the traces are never a sum of
    separately drawn component samples, which drops the cross-component
    posterior covariance (SYNTHESIS A-5): on hyperparameter-draw paths they
    are the per-draw conditional means of the summed function, and on the MAP
    path joint draws from the full posterior N(mean, cov) with a fixed `seed`.
    A result rebuilt without per-draw provenance (no ``full``, as the frozen
    D58 poster driver rebuilds one) renders exactly as before fix pass 2a, so
    pinned figures re-render byte for byte; its band label and summed traces
    keep the A-5 defects until the D58 correction (fix pass 2c).
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(10, 6))

    x = result.x_test
    full = getattr(result, "full", None)

    if full is None:
        ax.fill_between(x, result.full_mean - 2*result.full_std, result.full_mean + 2*result.full_std,
                         alpha=0.2, color=COLORS["band"], label="95% CI")
        min_samps = min(c.samples.shape[0] for c in result.components.values())
        for i in range(min(n_samples, min_samps)):
            combined = sum(c.samples[i] for c in result.components.values())
            ax.plot(x, combined, color=COLORS["samples"], alpha=0.15, linewidth=0.8)
    else:
        lo, hi, band_label = _band(full, result.full_mean, result.full_std)
        ax.fill_between(x, lo, hi, alpha=0.2, color=COLORS["band"], label=band_label)
        if full.samples_kind == "conditional_means" and full.n_draws > 1:
            _plot_traces(ax, x, full.conditional_means, "conditional_means", n_samples)
        elif full.n_draws == 1:
            _plot_traces(ax, x, _joint_draws(full, n_samples, seed), "function_draws", n_samples)

    ax.plot(x, result.full_mean, color=COLORS["mean"], linewidth=2.5, label="Predicted mean")
    if true_func is not None:
        ax.plot(x, true_func, color=COLORS["true"], linewidth=2, linestyle="--", label="True function")
    ax.scatter(result.x_train, result.y_train, color=COLORS["data"], marker="x", s=40, zorder=5, label="Data")
    ax.set_xlabel("$x$"); ax.set_ylabel("$y$"); ax.set_title(title); ax.legend(fontsize=10)
    return ax


def plot_component(result, component_name, true_func=None, color="orange",
                   title=None, n_samples=15, show_data=True, ax=None):
    """Single decomposed component — thesis Fig 11a/11b style.

    A summary produced by this package (``n_draws`` at least 1) gets its band
    and trace labels from what it holds (SYNTHESIS A-5): the band is posterior
    spread, not a standard error. A summary rebuilt without provenance
    (``n_draws`` 0, as the frozen D58 poster driver rebuilds one) renders
    exactly as before fix pass 2a (see plot_full_prediction).
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(10, 5))

    comp = result.components[component_name]
    x = result.x_test

    if getattr(comp, "n_draws", 0) == 0:
        ax.fill_between(x, comp.mean - 2*comp.std, comp.mean + 2*comp.std, alpha=0.2, color=color, label="±2 SE")
        for i in range(min(n_samples, comp.samples.shape[0])):
            ax.plot(x, comp.samples[i], color=COLORS["samples"], alpha=0.12, linewidth=0.8)
    else:
        lo, hi, band_label = _band(comp, comp.mean, comp.std)
        ax.fill_between(x, lo, hi, alpha=0.2, color=color, label=band_label)
        _plot_traces(ax, x, comp.samples, comp.samples_kind, n_samples)
    ax.plot(x, comp.mean, color=color, linewidth=2.5, label=f"{component_name} mean")
    if true_func is not None:
        ax.plot(x, true_func, color=COLORS["true"], linewidth=2, linestyle="--", label="True")
    if show_data:
        ax.scatter(result.x_train, result.y_train, color=COLORS["data"], marker="x", s=30, alpha=0.4, zorder=5)
    ax.set_xlabel("$x$"); ax.set_ylabel("$y$"); ax.set_title(title or component_name); ax.legend(fontsize=10)
    return ax


def plot_decomposition(result, true_components=None, true_combined=None,
                       figsize=None, suptitle="Additive GP Decomposition"):
    """Full decomposition: combined + all components (generalizes Fig 11)."""
    n = len(result.components)
    if figsize is None:
        figsize = (12, 4 * (1 + n))

    fig, axes = plt.subplots(1 + n, 1, figsize=figsize, sharex=True)
    plot_full_prediction(result, true_func=true_combined, title="Full GP Prediction", ax=axes[0])

    colors = ["orange", "green", "purple", "teal", "brown", "pink"]
    for i, (name, comp) in enumerate(result.components.items()):
        tf = true_components.get(name) if true_components else None
        plot_component(result, name, true_func=tf, color=colors[i % len(colors)],
                       title=f"Component: {name}", ax=axes[i+1])

    fig.suptitle(suptitle, fontsize=16, y=1.01)
    fig.tight_layout()
    return fig


def plot_mauna_loa_decomposition(result, x_test_held=None, y_test_held=None, figsize=(14, 16)):
    """Specialized 4-panel Mauna Loa plot."""
    fig = plt.figure(figsize=figsize)
    gs = GridSpec(4, 1, figure=fig, hspace=0.3)

    ax0 = fig.add_subplot(gs[0])
    plot_full_prediction(result, title="(a) Full CO₂ Prediction", ax=ax0)
    if x_test_held is not None:
        ax0.scatter(x_test_held, y_test_held, color="red", marker=".", s=10, alpha=0.5, label="Held-out")
        ax0.legend(fontsize=9)

    for i, (name, title, color) in enumerate([
        ("trend", "(b) Long-term Trend", "orange"),
        ("seasonal", "(c) Seasonal Cycle", "green"),
        ("medium_term", "(d) Medium-term Variations", "purple"),
    ]):
        if name in result.components:
            ax = fig.add_subplot(gs[i+1])
            plot_component(result, name, color=color, title=title, show_data=False, ax=ax)

    return fig
    
def plot_hyperparameter_posteriors(mcmc_samples, param_labels=None, figsize=None):
    """Marginal posterior distributions — thesis Fig 7b style."""
    n_params = len(mcmc_samples)
    if figsize is None:
        figsize = (5 * n_params, 4)

    fig, axes = plt.subplots(1, n_params, figsize=figsize)
    if n_params == 1:
        axes = [axes]

    for ax, (name, samples) in zip(axes, mcmc_samples.items()):
        label = param_labels.get(name, name) if param_labels else name
        ax.hist(samples, bins=50, density=True, alpha=0.6, color="steelblue", label="Posterior")
        ax.set_xlabel(label)
        ax.set_ylabel("Density")
        ax.legend(fontsize=9)

    fig.tight_layout()
    return fig
