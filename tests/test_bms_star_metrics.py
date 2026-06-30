"""
Tests for the divergence metrics in bistar_gp/bms_star.py.

These guard the analytic Gaussian KL / Bhattacharyya / Hellinger formulas
against the mathematical properties they must satisfy: identity-of-indiscernibles,
non-negativity, symmetry (where claimed), and Hellinger's [0, 1] bound. A
numerical KL is cross-checked by Monte Carlo.
"""

import numpy as np
import pytest

from bistar_gp.bms_star import (
    kl_divergence,
    kl_forward,
    kl_backward,
    kl_symmetric,
    bhattacharyya_distance,
    hellinger_distance,
    _safe_logdet,
    _safe_solve,
)

rng = np.random.default_rng(0)


def random_gaussian(k):
    """A random (mean, SPD covariance) pair of dimension k."""
    mu = rng.standard_normal(k)
    A = rng.standard_normal((k, k))
    cov = A @ A.T + k * np.eye(k)  # well-conditioned SPD
    return mu, cov


@pytest.mark.parametrize("k", [1, 3, 8])
def test_kl_self_is_zero(k):
    mu, cov = random_gaussian(k)
    assert kl_divergence(mu, cov, mu, cov) == pytest.approx(0.0, abs=1e-8)


@pytest.mark.parametrize("k", [1, 3, 8])
def test_kl_non_negative(k):
    mu_p, cov_p = random_gaussian(k)
    mu_q, cov_q = random_gaussian(k)
    assert kl_divergence(mu_p, cov_p, mu_q, cov_q) >= -1e-8


def test_kl_is_asymmetric_but_jeffreys_is_symmetric():
    mu_p, cov_p = random_gaussian(4)
    mu_q, cov_q = random_gaussian(4)
    fwd = kl_forward(mu_p, cov_p, mu_q, cov_q)
    bwd = kl_backward(mu_p, cov_p, mu_q, cov_q)
    assert not np.isclose(fwd, bwd)  # KL is directional
    sym_pq = kl_symmetric(mu_p, cov_p, mu_q, cov_q)
    sym_qp = kl_symmetric(mu_q, cov_q, mu_p, cov_p)
    assert sym_pq == pytest.approx(sym_qp, abs=1e-8)
    assert sym_pq == pytest.approx(0.5 * (fwd + bwd), abs=1e-10)


def test_kl_matches_monte_carlo():
    """Analytic Gaussian KL should match a Monte Carlo estimate of E_p[log p/q]."""
    mu_p, cov_p = random_gaussian(2)
    mu_q, cov_q = random_gaussian(2)

    def logpdf(x, mu, cov):
        k = len(mu)
        diff = x - mu
        sol = _safe_solve(cov, diff.T).T
        quad = np.einsum("ij,ij->i", diff, sol)
        return -0.5 * (k * np.log(2 * np.pi) + _safe_logdet(cov) + quad)

    samples = rng.multivariate_normal(mu_p, cov_p, size=200_000)
    mc_kl = np.mean(logpdf(samples, mu_p, cov_p) - logpdf(samples, mu_q, cov_q))
    analytic = kl_divergence(mu_p, cov_p, mu_q, cov_q)
    assert mc_kl == pytest.approx(analytic, rel=0.05)


def test_known_univariate_kl():
    """Closed form for 1-D: KL = log(s_q/s_p) + (s_p^2 + (mu_p-mu_q)^2)/(2 s_q^2) - 1/2."""
    mu_p, var_p = np.array([0.0]), np.array([[1.0]])
    mu_q, var_q = np.array([1.0]), np.array([[4.0]])
    expected = np.log(2.0) + (1.0 + 1.0) / (2 * 4.0) - 0.5
    assert kl_divergence(mu_p, var_p, mu_q, var_q) == pytest.approx(expected, abs=1e-10)


@pytest.mark.parametrize("k", [1, 3, 6])
def test_hellinger_bounds_and_identity(k):
    mu_p, cov_p = random_gaussian(k)
    mu_q, cov_q = random_gaussian(k)
    h_self = hellinger_distance(mu_p, cov_p, mu_p, cov_p)
    h_pq = hellinger_distance(mu_p, cov_p, mu_q, cov_q)
    assert h_self == pytest.approx(0.0, abs=1e-10)
    assert 0.0 <= h_pq <= 1.0


def test_bhattacharyya_symmetric_and_nonneg():
    mu_p, cov_p = random_gaussian(5)
    mu_q, cov_q = random_gaussian(5)
    d_pq = bhattacharyya_distance(mu_p, cov_p, mu_q, cov_q)
    d_qp = bhattacharyya_distance(mu_q, cov_q, mu_p, cov_p)
    assert d_pq == pytest.approx(d_qp, abs=1e-8)
    assert d_pq >= -1e-10


def test_safe_solve_falls_back_on_singular():
    """Singular A must not raise; lstsq fallback should return a finite result."""
    A = np.array([[1.0, 1.0], [1.0, 1.0]])  # singular
    b = np.array([1.0, 1.0])
    x = _safe_solve(A, b)
    assert np.isfinite(x).all()
