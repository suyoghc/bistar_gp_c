"""
Additive kernel decomposition for Gaussian Processes.

Implements Eq. 5 from Chandramouli & Shiffrin:
Given a GP with sum kernel k_sum = k_1 + k_2 + ... + k_n,
decompose posterior predictions into individual component GPs.

Pure PyTorch — no GPyTorch dependency. This is the mathematical core.
"""

import torch
from typing import List, Tuple, Optional


def compute_cholesky(
    K_sum_XX: torch.Tensor,
    noise_var: float,
    jitter: float = 1e-6,
) -> torch.Tensor:
    """
    Compute Cholesky factor of (K_sum(X,X) + sigma_y^2 I).
    Shared across all component decompositions.
    Progressive jitter fallback on failure.
    """
    n = K_sum_XX.shape[0]
    A = K_sum_XX + (noise_var + jitter) * torch.eye(n, dtype=K_sum_XX.dtype, device=K_sum_XX.device)
    try:
        return torch.linalg.cholesky(A)
    except RuntimeError:
        for extra in [1e-5, 1e-4, 1e-3, 1e-2]:
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
