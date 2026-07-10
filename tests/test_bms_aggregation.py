"""
Regression tests for the BMS* aggregation fixes in bistar_gp/bms_star.py.

Two confirmed result-invalidating bugs are guarded here:
  1. soft_transfer used a per-row (per-draw) max for "stability", which does not
     cancel under the over-draw mean + cross-candidate normalization, so it
     reweighted GP draws and silently behaved like normalize_per_draw=False->True.
     The fix subtracts a single global scalar, which is posterior-preserving.
  2. compute_G_matrix replaced failed cells with 10*max_finite, which is the
     SMALLEST value (best score) when the metric can be negative (pw_nll), so a
     numerically failed candidate could win. The fix uses a strictly-worse penalty.
"""

import numpy as np
import pytest
from types import SimpleNamespace

import bistar_gp.bms_star as bs
from bistar_gp.bms_star import soft_transfer, compute_G_matrix

rng = np.random.default_rng(0)


def _posteriors(G, tau, **kw):
    names = [f"m{j}" for j in range(G.shape[1])]
    return soft_transfer(G, tau, names, **kw).instance_posteriors


def test_soft_transfer_matches_direct_formula():
    """Implementation must equal the documented (1/N) Σ_i exp(-G_ij/τ), normalized."""
    G = rng.gamma(2.0, 1.0, size=(7, 4))
    tau = 1.3
    direct = np.exp(-G / tau).mean(axis=0)
    direct = direct / direct.sum()
    assert np.allclose(_posteriors(G, tau), direct, atol=1e-12)


def test_soft_transfer_is_simplex():
    G = rng.gamma(2.0, 1.0, size=(5, 3))
    p = _posteriors(G, 0.7)
    assert np.all(p >= 0)
    assert p.sum() == pytest.approx(1.0)


def test_soft_transfer_invariant_to_global_offset():
    """Adding the SAME constant to every G entry must not change the posterior."""
    G = rng.gamma(2.0, 1.0, size=(6, 4))
    tau = 0.9
    base = _posteriors(G, tau)
    shifted = _posteriors(G + 123.4, tau)
    assert np.allclose(base, shifted, atol=1e-10)


def test_soft_transfer_changes_under_per_draw_offset():
    """A per-DRAW offset is real information and MUST change the posterior.

    This locks in that the old per-row max-subtraction (which cancelled exactly
    such offsets) is gone — otherwise the stabilizer would silently discard
    between-draw differences.
    """
    G = rng.gamma(2.0, 1.0, size=(6, 4))
    tau = 0.9
    base = _posteriors(G, tau)
    per_draw = G + rng.uniform(0, 20, size=(6, 1))  # constant within each row
    assert not np.allclose(base, _posteriors(per_draw, tau), atol=1e-3)


def test_soft_transfer_lower_G_wins():
    G = rng.gamma(2.0, 1.0, size=(8, 3))
    G[:, 0] *= 0.1  # candidate 0 is uniformly closest to the GP
    p = _posteriors(G, 1.0)
    assert p[0] == p.max()


def test_soft_transfer_normalize_per_draw_still_available():
    """The explicit opt-in path must still run and return a valid simplex."""
    G = rng.gamma(2.0, 1.0, size=(5, 3))
    p = _posteriors(G, 1.0, normalize_per_draw=True)
    assert p.sum() == pytest.approx(1.0)
    assert np.all(p >= 0)


# ── soft_transfer_weighted (aggregation_v3) — same bug family as fix 1 ──

def _wposteriors(G, tau=1.0, log_weights=None):
    from bistar_gp.aggregation_v3 import soft_transfer_weighted
    G = np.asarray(G, dtype=float)
    lw = np.zeros(G.shape[0]) if log_weights is None else np.asarray(log_weights, float)
    names = [f"m{j}" for j in range(G.shape[1])]
    return soft_transfer_weighted(G, tau, names, lw).instance_posteriors


def test_weighted_soft_transfer_matches_direct_formula():
    """Must equal the documented Σ_i w_i exp(-G_ij/τ) / Σ_i w_i, normalized."""
    G = rng.gamma(2.0, 1.0, size=(7, 4))
    lw = rng.normal(0, 1, size=7)
    tau = 1.3
    w = np.exp(lw - lw.max())
    direct = (w[:, None] * np.exp(-G / tau)).sum(axis=0) / w.sum()
    direct = direct / direct.sum()
    assert np.allclose(_wposteriors(G, tau, lw), direct, atol=1e-12)


def test_weighted_equal_mass_candidates_split_evenly():
    """Two candidates with equal weighted Boltzmann mass but different best-draw
    G must get exactly 0.5/0.5. The old per-candidate (axis=0) max shift
    multiplied each candidate's score by exp(min_i G_ij/τ), breaking this."""
    tau = 1.0
    g = -np.log(0.5 * (1.0 + np.exp(-3.0)))   # both draws at the log-mean-exp of [0, 3]
    G = np.array([[0.0, g],
                  [3.0, g]])
    assert np.allclose(_wposteriors(G, tau), [0.5, 0.5], atol=1e-12)


def test_weighted_invariant_to_global_G_offset():
    G = rng.gamma(2.0, 1.0, size=(6, 4))
    lw = rng.normal(0, 1, size=6)
    base = _wposteriors(G, 0.9, lw)
    assert np.allclose(base, _wposteriors(G + 123.4, 0.9, lw), atol=1e-10)


# ── compute_G_matrix failure-sentinel ──────────────────────────────

@pytest.fixture
def flaky_metric():
    """A negative-valued metric (like pw_nll) that raises for one candidate."""
    name = "_flaky_test_metric"

    def metric(mu_p, cov_p, mu_q, cov_q):
        if float(mu_q[0]) == 999.0:           # the "failed" candidate
            raise ValueError("simulated numerical failure")
        return -5.0 + float(mu_q[0])          # negative divergence values

    bs.METRICS[name] = metric
    yield name
    del bs.METRICS[name]


def test_failed_cell_is_worse_than_all_finite_for_negative_metric(flaky_metric):
    psi = [SimpleNamespace(mean=np.array([0.0]), cov=np.eye(1)) for _ in range(3)]
    cands = [SimpleNamespace(mean=np.array([float(j)]), cov=np.eye(1)) for j in (0, 1)]
    cands.append(SimpleNamespace(mean=np.array([999.0]), cov=np.eye(1)))  # fails

    G = compute_G_matrix(psi, cands, flaky_metric)
    finite_max = G[:, :2].max()
    assert np.all(G[:, 2] > finite_max)          # failure is the WORST, not best
    assert np.all(np.argmin(G, axis=1) != 2)     # failed candidate never wins a row


def test_failed_candidate_gets_lowest_posterior(flaky_metric):
    psi = [SimpleNamespace(mean=np.array([0.0]), cov=np.eye(1)) for _ in range(3)]
    cands = [SimpleNamespace(mean=np.array([0.0]), cov=np.eye(1)),    # best (G=-5)
             SimpleNamespace(mean=np.array([1.0]), cov=np.eye(1)),    # G=-4
             SimpleNamespace(mean=np.array([999.0]), cov=np.eye(1))]  # fails
    G = compute_G_matrix(psi, cands, flaky_metric)
    p = _posteriors(G, 1.0)
    assert p[0] > p[1] > p[2]
