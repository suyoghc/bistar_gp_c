"""
Mauna Loa CO2 Decomposition: trend + seasonal + medium-term.
Same framework as toy example — more components, real data.
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
from bistar_gp.viz import plot_mauna_loa_decomposition
from gpytorch.constraints import Interval
from gpytorch.priors import GammaPrior

torch.set_default_dtype(torch.float64)


def main():
    print("=" * 50)
    print("  Mauna Loa CO₂ Decomposition")
    print("=" * 50)

    # 1. Data
    x_train, y_train, x_test, y_test, info = load_mauna_loa(normalize=True, test_years=5.0)
    print(f"\nTrain: {len(x_train)} points, Test: {len(x_test)} points")

    # 2. Model
    kernels, names = build_mauna_loa_kernels()
    likelihood = build_likelihood(
        noise_constraint=Interval(1e-5, 1.0),
        noise_prior=GammaPrior(1.5, 2.0),
    )
    model, likelihood = build_model(x_train, y_train, kernels, names, likelihood)

    # 3. Fit
    print("\nFitting (MAP) — may take a few minutes...")
    losses = fit_map(model, likelihood, x_train, y_train, n_iter=800, lr=0.02, print_every=100)
    print_hyperparameters(model, likelihood)

    # 4. Decompose
    x_all = torch.cat([x_train, x_test])
    x_pred = torch.linspace(x_all.min().item() - 1, x_all.max().item() + 1, 500).double()
    result = decompose_model(model, likelihood, x_train, y_train, x_pred, n_samples=20)

    # 5. Plot
    fig = plot_mauna_loa_decomposition(result, x_test.numpy(), y_test.numpy())
    fig.savefig("mauna_loa_decomposition.png", bbox_inches="tight", dpi=150)
    print("Saved: mauna_loa_decomposition.png")

    # 6. Evaluate
    result_test = decompose_model(model, likelihood, x_train, y_train, x_test, n_samples=5)
    rmse = np.sqrt(np.mean((result_test.full_mean - y_test.numpy())**2))
    print(f"\nRMSE (normalized): {rmse:.4f}")
    print(f"RMSE (ppm):        {rmse * info['y_std']:.2f}")

    plt.close("all")
    print("Done!")


if __name__ == "__main__":
    main()
