"""
Synthetic data generators and real dataset loaders.
"""

import torch
import numpy as np
from typing import Tuple, Optional

torch.set_default_dtype(torch.float64)


def generate_toy_data(n_points=20, x_range=(-10.0, 10.0), noise_std=0.5,
                      bias_slope=0.25, seed=42):
    """
    Thesis toy data: sin(x) + slope*x + noise.
    Returns (x, y, info_dict_with_ground_truth).
    """
    if seed is not None:
        torch.manual_seed(seed)
        np.random.seed(seed)

    x = torch.linspace(x_range[0], x_range[1], n_points).double()
    true_signal = torch.sin(x)
    bias = bias_slope * x
    noise = noise_std * torch.randn_like(x)
    y = true_signal + bias + noise

    info = {
        "true_signal": true_signal.numpy(),
        "bias": bias.numpy(),
        "combined": (true_signal + bias).numpy(),
        "noise_std": noise_std,
        "bias_slope": bias_slope,
    }
    return x, y.double(), info


def load_mauna_loa(normalize=True, test_years=5.0):
    """
    Load Mauna Loa CO2 from sklearn. Falls back to synthetic approximation.
    Returns (x_train, y_train, x_test, y_test, info).
    """
    try:
        from sklearn.datasets import fetch_openml
        co2 = fetch_openml(data_id=41187, as_frame=True)
        df = co2.frame
        df = df[df["average"] > 0]
        x_all = df["year"].values.astype(float) + (df["month"].values.astype(float) - 1) / 12.0
        y_all = df["average"].values.astype(float)
    except Exception:
        print("Could not load from sklearn. Using synthetic approximation.")
        x_all, y_all = _synthetic_mauna_loa()

    idx = np.argsort(x_all)
    x_all, y_all = x_all[idx], y_all[idx]

    cutoff = x_all.max() - test_years
    train_mask = x_all <= cutoff

    x_train, y_train = x_all[train_mask], y_all[train_mask]
    x_test, y_test = x_all[~train_mask], y_all[~train_mask]

    info = {"y_mean": 0.0, "y_std": 1.0, "x_offset": 0.0}

    if normalize:
        info["y_mean"], info["y_std"] = y_train.mean(), y_train.std()
        y_train = (y_train - info["y_mean"]) / info["y_std"]
        y_test = (y_test - info["y_mean"]) / info["y_std"]
        info["x_offset"] = x_train.mean()
        x_train -= info["x_offset"]
        x_test -= info["x_offset"]

    return (
        torch.tensor(x_train).double(), torch.tensor(y_train).double(),
        torch.tensor(x_test).double(), torch.tensor(y_test).double(),
        info,
    )


def _synthetic_mauna_loa(n_years=40):
    """Fallback: synthetic data mimicking Mauna Loa patterns."""
    t = np.linspace(0, n_years, n_years * 12)
    trend = 315 + 1.5 * t + 0.01 * t**2
    seasonal = 3.0 * np.sin(2 * np.pi * t) + 1.5 * np.cos(4 * np.pi * t)
    medium = 2.0 * np.sin(2 * np.pi * t / 10)
    noise = 0.3 * np.random.randn(len(t))
    return 1958 + t, trend + seasonal + medium + noise
