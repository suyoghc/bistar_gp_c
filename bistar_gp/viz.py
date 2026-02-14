"""
Visualization for GP decomposition — reproduces thesis figure styles.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from typing import Optional, Dict

plt.rcParams.update({"font.size": 12, "axes.labelsize": 14, "figure.dpi": 150, "lines.linewidth": 1.5})

COLORS = {"data": "black", "true": "red", "mean": "orange", "band": "lightgreen", "samples": "steelblue", "bias": "green"}


def plot_full_prediction(result, true_func=None, title="GP Prediction", n_samples=15, ax=None):
    """Full GP prediction — thesis Fig 10a style."""
    if ax is None:
        _, ax = plt.subplots(figsize=(10, 6))

    x = result.x_test

    # Confidence band
    ax.fill_between(x, result.full_mean - 2*result.full_std, result.full_mean + 2*result.full_std,
                     alpha=0.2, color=COLORS["band"], label="95% CI")

    # Function samples
    min_samps = min(c.samples.shape[0] for c in result.components.values())
    for i in range(min(n_samples, min_samps)):
        combined = sum(c.samples[i] for c in result.components.values())
        ax.plot(x, combined, color=COLORS["samples"], alpha=0.15, linewidth=0.8)

    ax.plot(x, result.full_mean, color=COLORS["mean"], linewidth=2.5, label="Predicted mean")
    if true_func is not None:
        ax.plot(x, true_func, color=COLORS["true"], linewidth=2, linestyle="--", label="True function")
    ax.scatter(result.x_train, result.y_train, color=COLORS["data"], marker="x", s=40, zorder=5, label="Data")
    ax.set_xlabel("$x$"); ax.set_ylabel("$y$"); ax.set_title(title); ax.legend(fontsize=10)
    return ax


def plot_component(result, component_name, true_func=None, color="orange",
                   title=None, n_samples=15, show_data=True, ax=None):
    """Single decomposed component — thesis Fig 11a/11b style."""
    if ax is None:
        _, ax = plt.subplots(figsize=(10, 5))

    comp = result.components[component_name]
    x = result.x_test

    ax.fill_between(x, comp.mean - 2*comp.std, comp.mean + 2*comp.std, alpha=0.2, color=color, label="±2 SE")
    for i in range(min(n_samples, comp.samples.shape[0])):
        ax.plot(x, comp.samples[i], color=COLORS["samples"], alpha=0.12, linewidth=0.8)
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
