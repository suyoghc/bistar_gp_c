"""Hermetic tests for the prereg v1.17 M2c profile-integration algorithm."""

import numpy as np
import pytest
from scipy.optimize import OptimizeResult

from bistar_gp import profile_integration as integration
from bistar_gp.m2c_freeze import (
    CAP_LADDER_LOWER_DIAGNOSTIC,
    CAP_LADDER_UPPER_DIAGNOSTIC,
    EPS_DOMAIN,
    EPS_GRID,
    FULL_DOMAIN_HI,
    FULL_DOMAIN_LO,
    FULL_DOMAIN_N_NODES,
    FULL_DOMAIN_N_WITH_EDGES,
    HESS_H_CENTER,
    HESS_H_SWEEP,
    PROFILE_GRID_BASE_HI,
    REFINE_L_MAX,
    PROFILE_GRID_BASE_LO,
    PROFILE_GRID_BASE_N,
    PROFILE_GRID_RATIO,
    RCOND_MIN,
    TOY_BAND_EDGES,
)


BAND_KEYS = ("P_noise_lo", "P_noise_mid", "P_noise_hi")
NUISANCE_ORDER = ("ls", "os", "lv")


def _quadratic_oracle(A, center=None):
    A = np.asarray(A, dtype=np.float64)
    if center is None:
        center = np.zeros(A.shape[0], dtype=np.float64)
    center = np.asarray(center, dtype=np.float64)

    def g(u):
        delta = np.asarray(u, dtype=np.float64) - center
        return -0.5 * float(delta @ A @ delta)

    def grad(u):
        return -A @ (np.asarray(u, dtype=np.float64) - center)

    return g, grad


def _bands(lo, mid, hi):
    return {
        "P_noise_lo": lo,
        "P_noise_mid": mid,
        "P_noise_hi": hi,
    }


def test_p3_grid_geometry_and_nested_refinement():
    base = integration.base_grid()
    assert base.size == PROFILE_GRID_BASE_N
    assert PROFILE_GRID_RATIO == pytest.approx(
        (PROFILE_GRID_BASE_HI / PROFILE_GRID_BASE_LO)
        ** (1.0 / (PROFILE_GRID_BASE_N - 1)),
        rel=0,
        abs=0,
    )
    np.testing.assert_allclose(
        base[1:] / base[:-1], PROFILE_GRID_RATIO, rtol=2e-15, atol=0.0
    )

    full = integration.full_domain_grid(with_edges=False)
    full_with_edges = integration.full_domain_grid()
    assert full.size == FULL_DOMAIN_N_NODES
    assert full_with_edges.size == FULL_DOMAIN_N_WITH_EDGES
    assert np.count_nonzero(
        (full > FULL_DOMAIN_LO) & (full < PROFILE_GRID_BASE_LO)
    ) == 76
    assert np.count_nonzero(
        (full > PROFILE_GRID_BASE_HI) & (full < FULL_DOMAIN_HI)
    ) == 64
    assert np.count_nonzero(full == FULL_DOMAIN_LO) == 1
    assert np.count_nonzero(full == FULL_DOMAIN_HI) == 1
    for edge in TOY_BAND_EDGES:
        assert np.count_nonzero(full_with_edges == edge) == 1

    assert base[24] == pytest.approx(0.14579, rel=1e-4)
    assert base[24] < TOY_BAND_EDGES[0] < base[25]
    assert base[25] == pytest.approx(0.16778, rel=1e-4)
    assert base[29] == pytest.approx(0.29435, rel=1e-4)
    assert base[29] < TOY_BAND_EDGES[1] < base[30]
    assert base[30] == pytest.approx(0.33877, rel=1e-4)

    refined = integration.nested_refine(full_with_edges)
    assert refined.size == 2 * full_with_edges.size - 1
    np.testing.assert_array_equal(refined[0::2], full_with_edges)


def test_cap_ladder_grids_are_diagnostic_decade_stages():
    ladders = integration.cap_ladder_grids()
    assert tuple(ladders["upper"]) == CAP_LADDER_UPPER_DIAGNOSTIC
    assert tuple(ladders["lower"]) == CAP_LADDER_LOWER_DIAGNOSTIC
    for cap, grid in ladders["upper"].items():
        assert grid[0] == FULL_DOMAIN_LO
        assert grid[-1] == cap
    for cap, grid in ladders["lower"].items():
        assert grid[0] == cap
        assert grid[-1] == FULL_DOMAIN_HI


def test_band_masses_partition_sums_to_one_on_synthetic_profile():
    grid = integration.full_domain_grid()
    logm = -0.5 * ((np.log(grid) - np.log(0.22)) / 0.65) ** 2
    masses = integration.band_masses(logm, grid, TOY_BAND_EDGES)
    residual = sum(masses[key] for key in BAND_KEYS) - 1.0
    assert abs(residual) <= 1e-15
    assert masses["total"] == pytest.approx(np.sum(masses["band_int"]))


def test_edge_split_preserves_total_and_reproduces_historical_defect_class():
    grid = integration.base_grid()
    logm = -0.5 * ((np.log(grid) - np.log(0.21)) / 0.58) ** 2
    m = np.exp(logm - np.max(logm))
    split = integration.total_preservation_under_edge_split(m, grid, TOY_BAND_EDGES)
    assert split["difference"] == pytest.approx(0.0, abs=2e-16)
    assert split["total_after"] == pytest.approx(
        split["total_before"], rel=0, abs=2e-16
    )

    for edge in TOY_BAND_EDGES:
        index = int(np.flatnonzero(split["grid"] == edge)[0])
        assert split["m"][index] == pytest.approx(
            integration.linear_interpolant_edge_value(m, grid, edge),
            rel=0,
            abs=0,
        )
    corrected = integration.band_masses(
        np.log(split["m"]), split["grid"], TOY_BAND_EDGES
    )
    corrected_sum = sum(corrected[key] for key in BAND_KEYS)
    assert corrected_sum == pytest.approx(1.0, abs=1e-15)

    old_integrals = []
    old_masks = (
        grid <= TOY_BAND_EDGES[0],
        (grid >= TOY_BAND_EDGES[0]) & (grid <= TOY_BAND_EDGES[1]),
        grid >= TOY_BAND_EDGES[1],
    )
    whole_total = np.trapz(m, grid)
    for mask in old_masks:
        old_integrals.append(np.trapz(m[mask], grid[mask]))
    old_sum = sum(old_integrals) / whole_total
    assert old_sum < 1.0

    dropped_slivers = 0.0
    for edge in TOY_BAND_EDGES:
        right = int(np.searchsorted(grid, edge))
        dropped_slivers += np.trapz(
            m[right - 1 : right + 1], grid[right - 1 : right + 1]
        )
    assert 1.0 - old_sum == pytest.approx(
        dropped_slivers / whole_total, rel=2e-15, abs=2e-16
    )


@pytest.mark.parametrize(
    ("grid", "density", "q", "expected"),
    [
        (np.array([2.0, 3.0, 5.0]), np.ones(3), 0.35, 3.05),
        (
            np.array([0.0, 0.2, 0.7, 1.0]),
            np.array([0.0, 0.4, 1.4, 2.0]),
            0.36,
            0.6,
        ),
    ],
    ids=("uniform-linear-cdf", "triangular-quadratic-cdf"),
)
def test_exact_quadratic_quantile_matches_analytic_answer(
    grid, density, q, expected
):
    assert integration.quantile_exact_quadratic(density, grid, q) == pytest.approx(
        expected, rel=0, abs=2e-15
    )


def test_optimizer_gate_converges_and_requires_both_starts():
    A = np.diag([1.0, 4.0, 9.0])
    center = np.array([0.4, -0.7, 1.1])
    g, grad = _quadratic_oracle(A, center)
    result = integration.optimize_conditional(
        lambda u: -g(u),
        lambda u: -grad(u),
        np.array([3.0, -2.0, 0.0]),
        np.array([-4.0, 2.0, 5.0]),
    )
    assert result["both_success"] is True
    assert result["agree"] is True
    assert result["stop"] is False
    assert result["restart_count"] == 0
    np.testing.assert_allclose(result["u_star"], center, rtol=0, atol=1e-7)
    assert result["grad_inf_norm"] <= 1e-4
    assert all(record["stationary"] for record in result["starts"].values())


def test_optimizer_rejects_agreeing_nonstationary_starts(monkeypatch):
    def fake_minimize(fun, x0, **kwargs):
        return OptimizeResult(
            x=np.asarray(x0, dtype=np.float64),
            status=0,
            success=True,
            message="synthetic success",
        )

    monkeypatch.setattr(integration, "minimize", fake_minimize)
    start = np.array([0.0, 0.0, 0.0])
    result = integration.optimize_conditional(
        lambda u: 0.0,
        lambda u: np.ones_like(u),
        start,
        start.copy(),
    )
    assert result["agree"] is True
    assert result["both_success"] is False
    assert result["stop"] is True
    assert "non-stationary" in result["reason"]


def test_optimizer_abnormal_termination_restarts_once(monkeypatch):
    A = np.diag([1.0, 4.0, 9.0])
    center = np.array([0.2, -0.1, 0.3])
    g, grad = _quadratic_oracle(A, center)
    scipy_minimize = integration.minimize
    call_count = 0

    def abnormal_then_real(fun, x0, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return OptimizeResult(
                x=np.asarray(x0, dtype=np.float64),
                status=2,
                success=False,
                message="synthetic abnormal termination",
            )
        return scipy_minimize(fun, x0, **kwargs)

    monkeypatch.setattr(integration, "minimize", abnormal_then_real)
    result = integration.optimize_conditional(
        lambda u: -g(u),
        lambda u: -grad(u),
        np.ones(3),
        -np.ones(3),
    )
    assert result["restart_count"] == 1
    assert result["both_success"] is True
    assert result["agree"] is True
    assert result["stop"] is False


def test_curvature_gate_recovers_quadratic_oracle_without_flooring():
    A = np.diag([1.0, 4.0, 9.0])
    g, grad = _quadratic_oracle(A)
    result = integration.curvature_gate(g, grad, np.zeros(3), NUISANCE_ORDER)
    np.testing.assert_allclose(result["K"], A, rtol=0, atol=1e-9)
    np.testing.assert_allclose(
        result["eigenvalues"], np.array([1.0, 4.0, 9.0]), rtol=0, atol=1e-9
    )
    assert result["rcond"] == pytest.approx(1.0 / 9.0, rel=1e-12)
    assert result["spd"] is True
    assert result["symmetry_ok"] is True
    assert result["logdet_stable"] is True
    assert result["directional_ok"] is True
    assert result["retry_count"] == 0
    assert result["stop"] is False


def test_curvature_gate_stops_after_retry_for_indefinite_oracle_without_flooring():
    A = np.diag([1.0, 4.0, -2.0])
    g, grad = _quadratic_oracle(A)
    result = integration.curvature_gate(g, grad, np.zeros(3), NUISANCE_ORDER)
    assert result["spd"] is False
    assert result["stop"] is True
    assert result["retry_count"] == 1
    assert result["eigenvalues"][0] == pytest.approx(-2.0, abs=1e-9)
    assert not np.any(np.isclose(result["eigenvalues"], 1e-3))


def test_curvature_gate_stops_after_retry_for_near_singular_spd_oracle():
    A = np.diag([1e-9, 4.0, 9.0])
    g, grad = _quadratic_oracle(A)
    result = integration.curvature_gate(g, grad, np.zeros(3), NUISANCE_ORDER)
    assert result["spd"] is True
    assert result["rcond"] < RCOND_MIN
    assert result["conditioning_ok"] is False
    assert result["stop"] is True
    assert result["retry_count"] == 1
    assert result["eigenvalues"][0] == pytest.approx(1e-9, rel=1e-12)


def test_numerical_error_components_envelope_and_domain_stop():
    by_level = [
        _bands(0.20, 0.30, 0.50),
        _bands(0.21, 0.29, 0.50),
        _bands(0.205, 0.292, 0.503),
    ]
    quad = integration.delta_quad(by_level)
    assert quad == pytest.approx(_bands(0.005, 0.002, 0.003), abs=1e-15)

    by_h = {
        HESS_H_SWEEP[0]: _bands(0.201, 0.297, 0.502),
        HESS_H_CENTER: _bands(0.200, 0.300, 0.500),
        HESS_H_SWEEP[-1]: _bands(0.198, 0.304, 0.499),
    }
    hess = integration.delta_hess(by_h)
    assert hess == pytest.approx(_bands(0.002, 0.004, 0.002), abs=1e-15)

    full = _bands(0.20, 0.30, 0.50)
    upper_pullback = _bands(0.19995, 0.30002, 0.50003)
    lower_pullback = _bands(0.20008, 0.29999, 0.49991)
    tail = integration.delta_tail(full, upper_pullback, lower_pullback)
    assert tail["upper"] == pytest.approx(
        _bands(5e-5, 2e-5, 3e-5), abs=1e-15
    )
    assert tail["lower"] == pytest.approx(
        _bands(8e-5, 1e-5, 9e-5), abs=1e-15
    )
    assert tail["delta_tail"] == pytest.approx(
        _bands(8e-5, 2e-5, 9e-5), abs=1e-15
    )
    assert tail["stop"] is False

    envelope = integration.heuristic_error_envelope(quad, hess, tail)
    assert envelope["delta_env"] == pytest.approx(
        _bands(0.005, 0.004, 0.003), abs=1e-15
    )
    assert "heuristic" in envelope["label"]
    assert "not a bound" in envelope["label"]

    triggering_upper = dict(upper_pullback)
    triggering_upper["P_noise_mid"] = full["P_noise_mid"] + 2.0 * EPS_DOMAIN
    triggered = integration.delta_tail(full, triggering_upper, lower_pullback)
    assert triggered["upper"]["P_noise_mid"] >= EPS_DOMAIN
    assert triggered["stop"] is True


def test_curvature_retry_rejects_nonstationary_reoptimum(monkeypatch):
    """The §2c retry re-optimizes u*; a SciPy status==0 result at a
    non-stationary but well-conditioned SPD point must still STOP (rev-5 §2b
    L112-117: stationarity is mandatory and never replaced by any other check).
    """
    # g is concave (K SPD) far from 0 in the u0 direction but indefinite at 0,
    # so the initial u*=0 fails SPD and triggers the retry.
    def g(u):
        u = np.asarray(u, dtype=np.float64)
        return -0.25 * u[0] ** 4 + 0.5 * u[0] ** 2 - 2.0 * u[1] ** 2 - 4.5 * u[2] ** 2

    def grad(u):
        u = np.asarray(u, dtype=np.float64)
        return np.array([-u[0] ** 3 + u[0], -4.0 * u[1], -9.0 * u[2]])

    # Initial curvature at 0: K = diag(-1, 4, 9) -> not SPD -> retry.
    initial = integration.curvature_gate(g, grad, np.zeros(3), NUISANCE_ORDER)
    assert initial["spd"] is False

    # Force the retry optimizer to "succeed" at a non-stationary point [2,0,0],
    # where K = diag(11, 4, 9) is SPD and well-conditioned but ||grad||_inf = 6.
    def fake_minimize(fun, x0, **kwargs):
        return OptimizeResult(
            x=np.array([2.0, 0.0, 0.0]),
            status=0,
            success=True,
            message="synthetic non-stationary success",
        )

    monkeypatch.setattr(integration, "minimize", fake_minimize)
    result = integration.curvature_gate(g, grad, np.zeros(3), NUISANCE_ORDER)
    assert result["retry_count"] == 1
    assert result["conditioning_ok"] is True          # retried point IS SPD + well-conditioned
    assert result["spd"] is True
    assert result["stationary"] is False              # ...but non-stationary
    assert result["grad_inf_norm"] == pytest.approx(6.0, rel=1e-9)
    assert result["stop"] is True                     # so it is rejected, not accepted
    assert "non-stationary" in result["reason"]


def _leveled_band_masses(sequence):
    """Callable grid -> band masses that returns the next element per call,
    ignoring the grid nodes (hermetic stand-in for the profile evaluator)."""
    state = {"i": 0}

    def evaluate(_grid):
        triple = sequence[min(state["i"], len(sequence) - 1)]
        state["i"] += 1
        return {
            "P_noise_lo": triple[0],
            "P_noise_mid": triple[1],
            "P_noise_hi": triple[2],
        }

    return evaluate


def test_refine_until_converged_converges_below_eps_grid():
    # level 0 -> level 1 band-mass change is {5e-5, 4e-5, 1e-5}, all < EPS_GRID.
    evaluate = _leveled_band_masses(
        [(0.20, 0.30, 0.50), (0.20005, 0.29996, 0.49999)]
    )
    out = integration.refine_until_converged(evaluate, integration.base_grid())
    assert out["converged"] is True
    assert out["stop"] is False
    assert out["n_refinements"] == 1
    assert max(out["delta_quad"].values()) < EPS_GRID
    assert out["delta_quad"] == pytest.approx(
        {"P_noise_lo": 5e-5, "P_noise_mid": 4e-5, "P_noise_hi": 1e-5}, abs=1e-15
    )


def test_refine_until_converged_stops_when_unconverged_at_l_max():
    # Every level moves a band by 0.01 >= EPS_GRID, so it never converges.
    evaluate = _leveled_band_masses(
        [
            (0.20, 0.30, 0.50),
            (0.21, 0.29, 0.50),
            (0.22, 0.28, 0.50),
            (0.23, 0.27, 0.50),
        ]
    )
    out = integration.refine_until_converged(evaluate, integration.base_grid())
    assert out["converged"] is False
    assert out["stop"] is True
    assert out["n_refinements"] == REFINE_L_MAX
    assert max(out["delta_quad"].values()) >= EPS_GRID
    assert "did not converge" in out["reason"]


def test_refine_until_converged_boundary_delta_equal_eps_grid_stops():
    # Convergence is STRICT (< EPS_GRID); a band moving by EXACTLY EPS_GRID at
    # every level never converges and must STOP at REFINE_L_MAX. Alternating
    # 0.0 / EPS_GRID makes every level-to-level delta bit-exactly EPS_GRID
    # (subtraction against 0.0 is exact, avoiding float-accumulation drift).
    evaluate = _leveled_band_masses(
        [
            (0.0, 0.30, 0.50),
            (EPS_GRID, 0.30, 0.50),
            (0.0, 0.30, 0.50),
            (EPS_GRID, 0.30, 0.50),
        ]
    )
    out = integration.refine_until_converged(evaluate, integration.base_grid())
    assert out["delta_quad"]["P_noise_lo"] == EPS_GRID          # bit-exact
    assert out["converged"] is False                            # strict < fails at equality
    assert out["stop"] is True
    assert out["n_refinements"] == REFINE_L_MAX


def test_refine_until_converged_reports_intermediate_level_delta():
    # Converges at level 2 (level-1 delta >= EPS_GRID, level-2 delta < EPS_GRID);
    # the reported delta is the level-2 delta and refinement stops early.
    evaluate = _leveled_band_masses(
        [
            (0.20, 0.30, 0.50),
            (0.21, 0.30, 0.50),          # level-1 delta {0.01,0,0} >= EPS_GRID
            (0.210005, 0.30, 0.50),      # level-2 delta {5e-6,0,0} <  EPS_GRID
        ]
    )
    out = integration.refine_until_converged(evaluate, integration.base_grid())
    assert out["converged"] is True
    assert out["stop"] is False
    assert out["n_refinements"] == 2
    assert out["delta_quad"] == pytest.approx(
        {"P_noise_lo": 5e-6, "P_noise_mid": 0.0, "P_noise_hi": 0.0}, abs=1e-15
    )
