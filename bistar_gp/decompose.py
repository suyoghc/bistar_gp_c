"""
Additive kernel decomposition for Gaussian Processes.

Implements Eq. 5 from Chandramouli & Shiffrin:
Given a GP with sum kernel k_sum = k_1 + k_2 + ... + k_n,
decompose posterior predictions into individual component GPs.

Pure PyTorch — no GPyTorch dependency. This is the mathematical core.
"""

import logging

import numpy as np
import torch
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)


def compute_cholesky(
    K_sum_XX: torch.Tensor,
    noise_var: float,
    jitter: float = 1e-6,
) -> torch.Tensor:
    """
    Compute Cholesky factor of (K_sum(X,X) + sigma_y^2 I).
    Shared across all component decompositions.
    Progressive jitter fallback on failure; each escalation is logged with
    its level (fix pass 2a, SYNTHESIS A-23) and the return value is unchanged.
    """
    n = K_sum_XX.shape[0]
    A = K_sum_XX + (noise_var + jitter) * torch.eye(n, dtype=K_sum_XX.dtype, device=K_sum_XX.device)
    try:
        return torch.linalg.cholesky(A)
    except RuntimeError:
        for extra in [1e-5, 1e-4, 1e-3, 1e-2]:
            logger.warning("compute_cholesky: factorization of K + (noise + %g) I "
                           "failed; retrying with extra jitter %g", jitter, extra)
            try:
                return torch.linalg.cholesky(
                    A + extra * torch.eye(n, dtype=A.dtype, device=A.device)
                )
            except RuntimeError:
                continue
        raise RuntimeError("Cholesky failed even with large jitter. Check hyperparameters.")


def decompose_component(
    K_i_XstarX: torch.Tensor,
    K_i_XstarXstar: torch.Tensor,
    K_i_XXstar: torch.Tensor,
    L: torch.Tensor,
    y: torch.Tensor,
    mean: Optional[torch.Tensor] = None,
) -> Tuple[torch.Tensor, torch.Tensor]:
    """
    Posterior for component i of an additive kernel (Eq. 5).

    f_i(x*) | X, Y ~ GP(
        k_i(x*, X) (K_sum + sigma_y^2 I)^{-1} y,
        k_i(x*, x*) - k_i(x*, X) (K_sum + sigma_y^2 I)^{-1} k_i(X, x*)
    )

    Args:
        K_i_XstarX:     k_i(X*, X), shape (n_test, n_train)
        K_i_XstarXstar: k_i(X*, X*), shape (n_test, n_test)
        K_i_XXstar:     k_i(X, X*), shape (n_train, n_test)
        L:              Cholesky of (K_sum(X,X) + sigma_y^2 I)
        y:              observed data, shape (n_train,)
        mean:           optional mean at training points

    Returns:
        (mean_i, cov_i)
    """
    y_centered = (y - mean) if mean is not None else y

    alpha = torch.cholesky_solve(y_centered.unsqueeze(-1), L).squeeze(-1)
    V = torch.linalg.solve_triangular(L, K_i_XXstar, upper=False)

    mean_i = K_i_XstarX @ alpha
    cov_i = K_i_XstarXstar - V.T @ V

    return mean_i, cov_i


def decompose_additive_gp(
    component_kernels_XX: List[torch.Tensor],
    component_kernels_XstarX: List[torch.Tensor],
    component_kernels_XstarXstar: List[torch.Tensor],
    component_kernels_XXstar: List[torch.Tensor],
    noise_var: float,
    y: torch.Tensor,
    jitter: float = 1e-6,
    mean: Optional[torch.Tensor] = None,
) -> List[Tuple[torch.Tensor, torch.Tensor]]:
    """
    Full additive decomposition: return posterior (mean, cov) for each component.
    Single Cholesky, shared across all components.
    """
    K_sum_XX = sum(component_kernels_XX)
    L = compute_cholesky(K_sum_XX, noise_var, jitter)

    return [
        decompose_component(KxsX, KxsXs, KXxs, L, y, mean)
        for KxsX, KxsXs, KXxs in zip(
            component_kernels_XstarX,
            component_kernels_XstarXstar,
            component_kernels_XXstar,
        )
    ]


def sample_from_component(
    mean_i: torch.Tensor,
    cov_i: torch.Tensor,
    n_samples: int = 25,
    jitter: float = 1e-6,
) -> torch.Tensor:
    """Draw function samples from a component posterior. Shape: (n_samples, n_test)."""
    n = cov_i.shape[0]
    cov_j = cov_i + jitter * torch.eye(n, dtype=cov_i.dtype, device=cov_i.device)
    try:
        L = torch.linalg.cholesky(cov_j)
    except RuntimeError:
        diag = torch.clamp(torch.diag(cov_i), min=1e-8)
        L = torch.diag(torch.sqrt(diag))

    z = torch.randn(n_samples, n, dtype=mean_i.dtype, device=mean_i.device)
    return mean_i.unsqueeze(0) + z @ L.T


def mixture_central_interval(mean_draws, var_draws, mass=0.95, n_iter=100):
    """Exact central interval of an equally weighted Gaussian mixture.

    ``mean_draws`` and ``var_draws`` have shape (n_draws, n_points); the
    return is (lo, hi), each of shape (n_points,). Quantiles are obtained by
    bisecting the mixture CDF, so the interval is the mixture's own central
    ``mass`` interval rather than a Gaussian approximation to it (ported from
    experiments/toy_debias_demo.py in the 2026-09 review fix pass; the
    reference implementation there is unchanged).
    """
    from scipy.special import ndtr

    mean_draws = np.asarray(mean_draws, dtype=float)
    var_draws = np.asarray(var_draws, dtype=float)
    if mean_draws.ndim == 1:
        mean_draws = mean_draws[None, :]
        var_draws = var_draws[None, :]
    if mean_draws.shape != var_draws.shape:
        raise ValueError("mean_draws and var_draws must have the same shape")
    if not (0.0 < mass < 1.0):
        raise ValueError("mass must lie strictly between 0 and 1")
    sd = np.sqrt(np.clip(var_draws, 1e-24, None))
    tail = (1.0 - mass) / 2.0

    def quantile(p):
        lo = (mean_draws - 12.0 * sd).min(axis=0)
        hi = (mean_draws + 12.0 * sd).max(axis=0)
        for _ in range(n_iter):
            mid = 0.5 * (lo + hi)
            cdf = ndtr((mid[None, :] - mean_draws) / sd).mean(axis=0)
            below = cdf < p
            lo = np.where(below, mid, lo)
            hi = np.where(below, hi, mid)
        return 0.5 * (lo + hi)

    return quantile(tail), quantile(1.0 - tail)
