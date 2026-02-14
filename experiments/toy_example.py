"""
Toy Example with full Bayesian MCMC — reproduces thesis Figs 7a, 7b, 10a, 11.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import torch
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from bistar_gp import (
    generate_toy_data, build_toy_kernels, build_model, build_likelihood,
    fit_map, fit_mcmc_simple, print_hyperparameters,
    decompose_model, decompose_model_mcmc,
)
from bistar_gp.viz import plot_decomposition, plot_hyperparameter_posteriors

torch.set_default_dtype(torch.float64)


def main():
    print("=" * 50)
    print("  Toy Example: MAP + MCMC")
    print("=" * 50)

    # 1. Data
    x_train, y_train, info = generate_toy_data(
        n_points=20, noise_std=0.5, bias_slope=0.25, seed=42,
    )
    x_test = torch.linspace(-11.0, 11.0, 200).double()
    x_np = x_test.numpy()
    true_components = {"unbiased_se": np.sin(x_np), "bias_linear": 0.25 * x_np}
    true_combined = np.sin(x_np) + 0.25 * x_np

    # ── MAP ──────────────────────────────────────────
    print("\n── MAP Estimation ──")
    kernels, names = build_toy_kernels()
    model, likelihood = build_model(x_train, y_train, kernels, names)

    # Initialize SE at shorter lengthscale
    model.kernel_components[0].base_kernel.lengthscale = 3.0
    model.kernel_components[0].outputscale = 2.0

    losses = fit_map(model, likelihood, x_train, y_train, n_iter=500, lr=0.05)
    print_hyperparameters(model, likelihood)

    result_map = decompose_model(model, likelihood, x_train, y_train, x_test, n_samples=25)

    fig_map = plot_decomposition(
        result_map, true_components=true_components, true_combined=true_combined,
        suptitle="MAP Decomposition",
    )
    fig_map.savefig("toy_map.png", bbox_inches="tight", dpi=150)
    print("Saved: toy_map.png")

    # ── MCMC ─────────────────────────────────────────
    print("\n── MCMC (Full Bayesian) ──")

    # Rebuild model fresh — initialize at short lengthscale
    # so MCMC starts in a good region
    kernels2, names2 = build_toy_kernels()
    model2, likelihood2 = build_model(x_train, y_train, kernels2, names2)
    model2.kernel_components[0].base_kernel.lengthscale = 3.0
    model2.kernel_components[0].outputscale = 2.0
    likelihood2.noise = 0.3

    # Brief MAP to warm up, then MCMC
    print("Warm-up MAP (100 iters)...")
    fit_map(model2, likelihood2, x_train, y_train, n_iter=100, lr=0.05, verbose=False)
    print_hyperparameters(model2, likelihood2)

    print("Running MCMC (10000 samples, 2000 burnin)...")
    mcmc_samples = fit_mcmc_simple(
        model2, likelihood2, x_train, y_train,
        n_samples=10000,
        n_burnin=2000,
        proposal_scale=0.15,  # slightly larger to explore
    )

    # MCMC decomposition
    result_mcmc = decompose_model_mcmc(
        model2, likelihood2, x_train, y_train, x_test,
        mcmc_samples,
        n_posterior_samples=200,
    )

    fig_mcmc = plot_decomposition(
        result_mcmc, true_components=true_components, true_combined=true_combined,
        suptitle="Full Bayesian (MCMC) Decomposition",
    )
    fig_mcmc.savefig("toy_mcmc.png", bbox_inches="tight", dpi=150)
    print("Saved: toy_mcmc.png")

    # ── Hyperparameter posteriors (thesis Fig 7b) ────
    fig_hyper = plot_hyperparameter_posteriors(mcmc_samples)
    fig_hyper.savefig("toy_hyperparameters.png", bbox_inches="tight", dpi=150)
    print("Saved: toy_hyperparameters.png")

    # ── Side by side comparison ──────────────────────
    fig_compare, axes = plt.subplots(1, 2, figsize=(16, 6))

    from bistar_gp.viz import plot_full_prediction
    plot_full_prediction(result_map, true_func=true_combined, title="MAP", ax=axes[0])
    plot_full_prediction(result_mcmc, true_func=true_combined, title="MCMC (Full Bayesian)", ax=axes[1])

    fig_compare.suptitle("MAP vs Full Bayesian", fontsize=16)
    fig_compare.tight_layout()
    fig_compare.savefig("toy_map_vs_mcmc.png", bbox_inches="tight", dpi=150)
    print("Saved: toy_map_vs_mcmc.png")

    plt.close("all")
    print("\nDone! Compare toy_map.png vs toy_mcmc.png")


if __name__ == "__main__":
    main()