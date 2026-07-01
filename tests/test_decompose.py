"""
Tests for the additive-GP decomposition core (bistar_gp/decompose.py).

The load-bearing invariant: for a sum kernel k_sum = sum_i k_i, the posterior
means of the per-component GPs (Eq. 5) must sum exactly to the full GP posterior
mean. Both use the same alpha = (K_sum + sigma^2 I)^{-1} y, so this is an
identity up to floating point and is the strongest single guard on the math.
"""

import torch
import pytest

from bistar_gp.decompose import (
    compute_cholesky,
    decompose_component,
    decompose_additive_gp,
    sample_from_component,
)

torch.manual_seed(0)
DTYPE = torch.float64


def rbf(a, b, lengthscale, variance):
    """RBF/SE kernel matrix between 1-D inputs a (n,) and b (m,) -> (n, m)."""
    d2 = (a.unsqueeze(-1) - b.unsqueeze(-2)) ** 2
    return variance * torch.exp(-0.5 * d2 / lengthscale**2)


@pytest.fixture
def two_component_problem():
    """A 2-component additive RBF GP on a small toy dataset."""
    X = torch.linspace(0, 6, 12, dtype=DTYPE)
    Xs = torch.linspace(-1, 7, 20, dtype=DTYPE)
    y = torch.sin(X) + 0.25 * X  # short-scale + long-scale structure
    noise_var = 0.05

    comps = [
        dict(ls=0.7, var=1.0),   # wiggly component
        dict(ls=4.0, var=0.5),   # smooth trend component
    ]
    K_XX = [rbf(X, X, c["ls"], c["var"]) for c in comps]
    K_XsX = [rbf(Xs, X, c["ls"], c["var"]) for c in comps]
    K_XsXs = [rbf(Xs, Xs, c["ls"], c["var"]) for c in comps]
    K_XXs = [rbf(X, Xs, c["ls"], c["var"]) for c in comps]

    return dict(X=X, Xs=Xs, y=y, noise_var=noise_var,
                K_XX=K_XX, K_XsX=K_XsX, K_XsXs=K_XsXs, K_XXs=K_XXs)


def test_cholesky_reconstructs_matrix(two_component_problem):
    p = two_component_problem
    K_sum = sum(p["K_XX"])
    L = compute_cholesky(K_sum, p["noise_var"])
    n = K_sum.shape[0]
    A = K_sum + (p["noise_var"] + 1e-6) * torch.eye(n, dtype=DTYPE)
    assert torch.allclose(L @ L.T, A, atol=1e-8)
    # lower-triangular
    assert torch.allclose(torch.triu(L, diagonal=1), torch.zeros_like(L))


def test_component_means_sum_to_full_posterior_mean(two_component_problem):
    """The Eq. 5 invariant: sum_i mean_i == full GP posterior mean."""
    p = two_component_problem
    components = decompose_additive_gp(
        p["K_XX"], p["K_XsX"], p["K_XsXs"], p["K_XXs"],
        noise_var=p["noise_var"], y=p["y"],
    )
    summed_mean = sum(mean_i for mean_i, _ in components)

    # Full posterior mean computed independently.
    n = p["X"].shape[0]
    K_sum_XX = sum(p["K_XX"])
    K_sum_XsX = sum(p["K_XsX"])
    A = K_sum_XX + p["noise_var"] * torch.eye(n, dtype=DTYPE)
    alpha = torch.linalg.solve(A, p["y"])
    full_mean = K_sum_XsX @ alpha

    assert torch.allclose(summed_mean, full_mean, atol=1e-6)


def test_component_covariance_is_symmetric_psd(two_component_problem):
    p = two_component_problem
    components = decompose_additive_gp(
        p["K_XX"], p["K_XsX"], p["K_XsXs"], p["K_XXs"],
        noise_var=p["noise_var"], y=p["y"],
    )
    for i, (_, cov_i) in enumerate(components):
        assert torch.allclose(cov_i, cov_i.T, atol=1e-8)
        eigs = torch.linalg.eigvalsh(0.5 * (cov_i + cov_i.T))
        assert eigs.min() > -1e-6  # PSD up to numerical tolerance
        # Conditioning cannot increase variance: posterior diag <= prior diag.
        prior_var = torch.diag(p["K_XsXs"][i])
        assert torch.all(torch.diag(cov_i) <= prior_var + 1e-6)


def test_single_component_equals_full_gp(two_component_problem):
    """With one component, decomposition must reproduce the standard GP posterior."""
    p = two_component_problem
    K_XX = [p["K_XX"][0]]
    K_XsX = [p["K_XsX"][0]]
    K_XsXs = [p["K_XsXs"][0]]
    K_XXs = [p["K_XXs"][0]]
    (mean_i, cov_i), = decompose_additive_gp(
        K_XX, K_XsX, K_XsXs, K_XXs, noise_var=p["noise_var"], y=p["y"],
    )

    n = p["X"].shape[0]
    A = K_XX[0] + p["noise_var"] * torch.eye(n, dtype=DTYPE)
    alpha = torch.linalg.solve(A, p["y"])
    full_mean = K_XsX[0] @ alpha
    full_cov = K_XsXs[0] - K_XsX[0] @ torch.linalg.solve(A, K_XXs[0])

    assert torch.allclose(mean_i, full_mean, atol=1e-6)
    assert torch.allclose(cov_i, full_cov, atol=1e-6)


def test_sample_shape_and_empirical_mean(two_component_problem):
    p = two_component_problem
    (mean_i, cov_i), _ = decompose_additive_gp(
        p["K_XX"], p["K_XsX"], p["K_XsXs"], p["K_XXs"],
        noise_var=p["noise_var"], y=p["y"],
    )
    samples = sample_from_component(mean_i, cov_i, n_samples=5000)
    assert samples.shape == (5000, mean_i.shape[0])
    # Empirical mean of draws should track the posterior mean.
    assert torch.allclose(samples.mean(0), mean_i, atol=0.1)


def test_cholesky_recovers_from_slightly_non_psd_input():
    """A matrix that is non-PSD only at the jitter scale is rescued by the fallback."""
    near_psd = torch.tensor([[1.0, 0.0], [0.0, -1e-7]], dtype=DTYPE)  # min eig -1e-7
    L = compute_cholesky(near_psd, noise_var=0.0, jitter=1e-6)
    assert torch.isfinite(L).all()


def test_cholesky_raises_on_grossly_indefinite_input():
    """Beyond the jitter ladder (up to 1e-2) the failure is surfaced, not hidden."""
    bad = torch.tensor([[1.0, 2.0], [2.0, 1.0]], dtype=DTYPE)  # eigenvalues -1, 3
    with pytest.raises(RuntimeError, match="Cholesky failed"):
        compute_cholesky(bad, noise_var=0.0, jitter=1e-6)
