"""
Mauna Loa CO2: MAP + HMC decomposition into trend + seasonal + medium-term.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import torch
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from bistar_gp import (
    load_mauna_loa, build_mauna_loa_kernels, build_model, build_likelihood,
    fit_map, print_hyperparameters, decompose_model,
)
from bistar_gp.fit import fit_hmc
from bistar_gp.debias import decompose_model_hmc
from bistar_gp.viz import plot_mauna_loa_decomposition, plot_full_prediction

torch.set_default_dtype(torch.float64)


def main():
    print("=" * 50)
    print("  Mauna Loa CO₂: MAP + HMC")
    print("=" * 50)

    # 1. Data
    x_train, y_train, x_test, y_test, info = load_mauna_loa(normalize=True, test_years=5.0)
    print(f"\nTrain: {len(x_train)}, Test: {len(x_test)}")

    # ── MAP ──────────────────────────────────────────
    print("\n── MAP ──")
    kernels, names = build_mauna_loa_kernels()
    likelihood = build_likelihood()
    model, likelihood = build_model(x_train, y_train, kernels, names, likelihood)

    losses = fit_map(model, likelihood, x_train, y_train, n_iter=800, lr=0.02, print_every=100)
    print_hyperparameters(model, likelihood)

    x_all = torch.cat([x_train, x_test])
    x_pred = torch.linspace(x_all.min().item() - 1, x_all.max().item() + 1, 500).double()

    result_map = decompose_model(model, likelihood, x_train, y_train, x_pred, n_samples=20)

    fig_map = plot_mauna_loa_decomposition(result_map, x_test.numpy(), y_test.numpy())
    fig_map.savefig("mauna_loa_map.png", bbox_inches="tight", dpi=150)
    print("Saved: mauna_loa_map.png")

    # ── HMC ──────────────────────────────────────────
    print("\n── HMC ──")
    kernels2, names2 = build_mauna_loa_kernels()
    likelihood2 = build_likelihood()
    model2, likelihood2 = build_model(x_train, y_train, kernels2, names2, likelihood2)

    print("Running HMC (300 samples, 200 warmup)...")
    print("This will take several minutes with ~500 data points...")
    mcmc_samples = fit_hmc(
        model2, likelihood2, x_train, y_train,
        n_samples=300,
        n_warmup=200,
    )

    print("\nDecomposing HMC samples...")
    result_hmc = decompose_model_hmc(
        model2, likelihood2, x_train, y_train, x_pred,
        mcmc_samples,
        kernel_builder=build_mauna_loa_kernels,
        n_posterior_samples=100,
    )

    fig_hmc = plot_mauna_loa_decomposition(result_hmc, x_test.numpy(), y_test.numpy())
    fig_hmc.savefig("mauna_loa_hmc.png", bbox_inches="tight", dpi=150)
    print("Saved: mauna_loa_hmc.png")

    # ── Side by side ─────────────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    plot_full_prediction(result_map, title="MAP", ax=axes[0])
    axes[0].scatter(x_test.numpy(), y_test.numpy(), color="red", marker=".", s=10, alpha=0.5)
    plot_full_prediction(result_hmc, title="HMC (Full Bayesian)", ax=axes[1])
    axes[1].scatter(x_test.numpy(), y_test.numpy(), color="red", marker=".", s=10, alpha=0.5)
    fig.suptitle("Mauna Loa: MAP vs HMC", fontsize=16)
    fig.tight_layout()
    fig.savefig("mauna_loa_map_vs_hmc.png", bbox_inches="tight", dpi=150)
    print("Saved: mauna_loa_map_vs_hmc.png")

    # ── RMSE ─────────────────────────────────────────
    result_test = decompose_model(model, likelihood, x_train, y_train, x_test, n_samples=5)
    rmse = np.sqrt(np.mean((result_test.full_mean - y_test.numpy())**2))
    print(f"\nMAP RMSE: {rmse * info['y_std']:.2f} ppm")

    plt.close("all")
    print("Done!")


if __name__ == "__main__":
    main()