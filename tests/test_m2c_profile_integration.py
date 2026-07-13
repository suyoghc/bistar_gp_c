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
ORACLE_A = np.diag([1.0, 4.0, 9.0])
ORACLE_MU = np.array([0.4, -0.7, 1.1], dtype=np.float64)
ORACLE_ETA0 = 0.22
ORACLE_SIGMA = 0.8


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


def _oracle_c(noise):
    return -0.5 * (
        (np.log(float(noise)) - np.log(ORACLE_ETA0)) / ORACLE_SIGMA
    ) ** 2


def _gaussian_profile_oracle(indefinite_at=None):
    def matrix(noise):
        if indefinite_at is not None and float(noise) == float(indefinite_at):
            return np.diag([1.0, 4.0, -2.0])
        return ORACLE_A

    def g_of(u, noise):
        delta = np.asarray(u, dtype=np.float64) - ORACLE_MU
        A = matrix(noise)
        return -0.5 * float(delta @ A @ delta) + _oracle_c(noise)

    def grad_of(u, noise):
        A = matrix(noise)
        return -A @ (np.asarray(u, dtype=np.float64) - ORACLE_MU)

    return g_of, grad_of


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


def test_cap_ladder_grids_honour_caller_band_edges():
    # Mauna arm uses per-arm q25/q75 edges, NOT the toy 0.15/0.30. The
    # diagnostic cap grids must carry the caller's edges (regression for the
    # dropped-Mauna-edges defect), and must not silently inject toy edges.
    mauna_edges = (0.5, 3.0)
    ladders = integration.cap_ladder_grids(band_edges=mauna_edges)
    upper_10 = ladders["upper"][10.0]
    for edge in mauna_edges:
        assert np.count_nonzero(upper_10 == edge) == 1
    for toy_edge in TOY_BAND_EDGES:
        assert np.count_nonzero(upper_10 == toy_edge) == 0
    # Default still inserts the toy edges.
    default_upper_10 = integration.cap_ladder_grids()["upper"][10.0]
    for toy_edge in TOY_BAND_EDGES:
        assert np.count_nonzero(default_upper_10 == toy_edge) == 1


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


def test_profile_logm_on_grid_matches_gaussian_profile_oracle():
    g_of, grad_of = _gaussian_profile_oracle()
    grid = np.geomspace(0.02, 2.0, 9)
    result = integration.profile_logm_on_grid(
        g_of,
        grad_of,
        grid,
        ORACLE_MU,
        NUISANCE_ORDER,
    )

    expected_logdet = float(np.linalg.slogdet(ORACLE_A)[1])
    expected = np.asarray([_oracle_c(noise) for noise in grid]) + (
        1.5 * np.log(2.0 * np.pi) - 0.5 * expected_logdet
    )
    assert result["stop"] is False
    assert result["stop_index"] is None
    assert len(result["u_stars"]) == grid.size
    for u_star in result["u_stars"]:
        np.testing.assert_allclose(u_star, ORACLE_MU, rtol=0, atol=1e-10)
    np.testing.assert_allclose(
        result["logdet"], expected_logdet, rtol=0, atol=1e-10
    )
    np.testing.assert_allclose(result["logm"], expected, rtol=0, atol=1e-8)


@pytest.fixture(scope="module")
def corrected_gaussian_oracle():
    g_of, grad_of = _gaussian_profile_oracle()
    return integration.corrected_profile_band_masses(
        g_of,
        grad_of,
        ORACLE_MU,
        NUISANCE_ORDER,
        TOY_BAND_EDGES,
        quantile_qs=(0.25, 0.75),
    )


def test_corrected_profile_band_masses_matches_gaussian_oracle(
    corrected_gaussian_oracle,
):
    result = corrected_gaussian_oracle
    assert result["stop"] is False
    grid = result["grids"]["full"]
    expected_logdet = float(np.linalg.slogdet(ORACLE_A)[1])
    expected_logm = np.asarray([_oracle_c(noise) for noise in grid]) + (
        1.5 * np.log(2.0 * np.pi) - 0.5 * expected_logdet
    )
    expected_masses = integration.band_masses(
        expected_logm, grid, TOY_BAND_EDGES
    )
    for key in BAND_KEYS:
        assert result["band_masses"][key] == pytest.approx(
            expected_masses[key], rel=0, abs=1e-10
        )
    residual = sum(result["band_masses"][key] for key in BAND_KEYS) - 1.0
    assert abs(residual) <= 1e-15

    for sensitivity in (
        result["delta_quad"],
        result["delta_hess"],
        result["delta_tail"],
        result["delta_env"],
    ):
        assert all(np.isfinite(sensitivity[key]) for key in BAND_KEYS)
    assert max(result["delta_quad"].values()) < EPS_GRID
    assert max(result["delta_tail"].values()) < EPS_DOMAIN
    assert max(result["delta_hess"].values()) < 1e-12
    for h in HESS_H_SWEEP:
        np.testing.assert_allclose(
            result["profiles"]["full"]["logdet_by_h"][h],
            expected_logdet,
            rtol=0,
            atol=1e-10,
        )
    assert result["quantiles"][0.25] < result["quantiles"][0.75]


def test_profile_orchestrators_fail_closed_on_optimizer_stop(monkeypatch):
    g_of, grad_of = _gaussian_profile_oracle()
    real_optimize = integration.optimize_conditional
    call_count = 0

    def stop_at_second_node(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            return {"stop": True, "reason": "synthetic optimizer stop"}
        return real_optimize(*args, **kwargs)

    monkeypatch.setattr(
        integration, "optimize_conditional", stop_at_second_node
    )
    direct = integration.profile_logm_on_grid(
        g_of,
        grad_of,
        np.array([0.1, 0.2, 0.3]),
        ORACLE_MU,
        NUISANCE_ORDER,
    )
    assert direct["stop"] is True
    assert direct["stop_index"] == 1
    assert direct["logm"] is None
    assert "optimizer: synthetic optimizer stop" in direct["reason"]

    call_count = 0
    corrected = integration.corrected_profile_band_masses(
        g_of,
        grad_of,
        ORACLE_MU,
        NUISANCE_ORDER,
        TOY_BAND_EDGES,
    )
    assert corrected["stop"] is True
    assert corrected["stop_index"] == 1
    assert corrected["band_masses"] is None
    assert corrected["logm"] is None
    assert corrected["profiles"] == {}
    assert "optimizer: synthetic optimizer stop" in corrected["reason"]


def test_profile_logm_fails_closed_on_single_indefinite_curvature_node():
    bad_noise = 0.2
    g_of, grad_of = _gaussian_profile_oracle(indefinite_at=bad_noise)
    result = integration.profile_logm_on_grid(
        g_of,
        grad_of,
        np.array([0.1, bad_noise, 0.3]),
        ORACLE_MU,
        NUISANCE_ORDER,
    )
    assert result["stop"] is True
    assert result["stop_index"] == 1
    assert result["stop_noise"] == bad_noise
    assert result["logm"] is None
    assert "curvature: curvature is not strictly SPD" in result["reason"]


def test_corrected_profile_propagates_refinement_stop(monkeypatch):
    g_of, grad_of = _gaussian_profile_oracle()
    stopped_delta = _bands(2e-4, 1e-4, 3e-4)

    def stopped_refinement(**kwargs):
        return {
            "stop": True,
            "reason": "synthetic refinement stop",
            "delta_quad": stopped_delta,
            "grids": [kwargs["grid0"]],
        }

    monkeypatch.setattr(
        integration, "refine_until_converged", stopped_refinement
    )
    result = integration.corrected_profile_band_masses(
        g_of,
        grad_of,
        ORACLE_MU,
        NUISANCE_ORDER,
        TOY_BAND_EDGES,
    )
    assert result["stop"] is True
    assert result["band_masses"] is None
    assert result["logm"] is None                  # no usable marginal past STOP
    assert result["profiles"] == {}
    assert result["delta_quad"] == stopped_delta
    assert "refinement: synthetic refinement stop" in result["reason"]


def test_corrected_profile_propagates_tail_stop(monkeypatch):
    g_of, grad_of = _gaussian_profile_oracle()

    def stopped_tail(*args):
        return {
            "upper": _bands(0.0, EPS_DOMAIN, 0.0),
            "lower": _bands(0.0, 0.0, 0.0),
            "delta_tail": _bands(0.0, EPS_DOMAIN, 0.0),
            "stop": True,
            "reason": "synthetic tail stop",
        }

    monkeypatch.setattr(integration, "delta_tail", stopped_tail)
    result = integration.corrected_profile_band_masses(
        g_of,
        grad_of,
        ORACLE_MU,
        NUISANCE_ORDER,
        TOY_BAND_EDGES,
    )
    assert result["stop"] is True
    assert result["band_masses"] is None
    assert result["logm"] is None                  # no usable marginal past STOP
    assert result["profiles"] == {}
    assert result["delta_tail"]["P_noise_mid"] == EPS_DOMAIN
    assert "tail: synthetic tail stop" in result["reason"]


def test_corrected_profile_propagates_pullback_subprofile_stop():
    # A curvature STOP that occurs only on the upper/lower one-decade pullback
    # grid (not on the full grid) must still fail the whole corrected profile
    # closed — these branches were previously untested (codex/Sonnet coverage
    # gap). The upper pullback [1e-7, 1e3] contains 1000.0 as its cap node; make
    # the oracle indefinite exactly there so the full grid passes but the
    # upper-pullback profile STOPs.
    g_of, grad_of = _gaussian_profile_oracle(indefinite_at=1000.0)
    result = integration.corrected_profile_band_masses(
        g_of,
        grad_of,
        ORACLE_MU,
        NUISANCE_ORDER,
        TOY_BAND_EDGES,
    )
    assert result["stop"] is True
    assert result["band_masses"] is None
    assert result["logm"] is None
    assert result["profiles"] == {}
    assert "upper-pullback profile" in result["reason"]
    assert "curvature is not strictly SPD" in result["reason"]


def test_profile_logm_calls_optimizer_before_curvature_at_every_node(monkeypatch):
    g_of, grad_of = _gaussian_profile_oracle()
    call_log = []

    def fake_optimize(neg_g, neg_grad, u0_warm, u0_mode):
        call_log.append("optimize")
        u_star = np.asarray(u0_mode, dtype=np.float64).copy()
        return {
            "stop": False,
            "reason": "",
            "u_star": u_star,
            "g_star": -float(neg_g(u_star)),
        }

    def fake_curvature(g, grad, u_star, nuisance_order):
        call_log.append("curvature")
        return {
            "stop": False,
            "reason": "",
            "u_star": np.asarray(u_star, dtype=np.float64).copy(),
            "logdet": float(np.linalg.slogdet(ORACLE_A)[1]),
            "logdet_by_h": {
                h: float(np.linalg.slogdet(ORACLE_A)[1])
                for h in HESS_H_SWEEP
            },
        }

    monkeypatch.setattr(integration, "optimize_conditional", fake_optimize)
    monkeypatch.setattr(integration, "curvature_gate", fake_curvature)
    result = integration.profile_logm_on_grid(
        g_of,
        grad_of,
        np.array([0.1, 0.2, 0.3]),
        ORACLE_MU,
        NUISANCE_ORDER,
    )
    assert result["stop"] is False
    assert call_log == ["optimize", "curvature"] * 3


def test_profile_potential_adapter_matches_single_synthetic_map_evaluation():
    torch = pytest.importorskip("torch")
    pytest.importorskip("gpytorch")
    from bistar_gp.config import (
        PRIOR_CONFIGS,
        build_kernels_from_config,
        build_likelihood_from_config,
    )
    from bistar_gp.fit import fit_map
    from bistar_gp.model import build_model
    from bistar_gp.profile_potential import ProfilePotential

    torch.manual_seed(17)
    x = torch.linspace(0.0, 5.0, 20).double()
    y = (torch.sin(2.0 * x) + 0.15 * torch.randn(20)).double()
    prior = PRIOR_CONFIGS["toy_elicited_n20"]
    kernels, names = build_kernels_from_config(prior)
    likelihood = build_likelihood_from_config(prior)
    model, likelihood = build_model(x, y, kernels, names, likelihood)
    fit_map(model, likelihood, x, y, n_iter=80, lr=0.05, verbose=False)
    profile = ProfilePotential(model, likelihood, x, y)

    parameters = dict(model.named_parameters())
    u_map = {}
    for site in profile.nuisance_sites:
        _prior, fqname, constraint, _raw_shape = profile._site_map[site]
        raw = parameters[fqname].detach().clone()
        theta = constraint.transform(raw) if constraint is not None else raw
        u_map[site] = torch.log(theta)
    _prior, fqname, constraint, _raw_shape = profile._site_map[
        profile.noise_site
    ]
    raw_noise = parameters[fqname].detach().clone()
    noise = constraint.transform(raw_noise) if constraint is not None else raw_noise
    u0 = np.asarray(
        [float(u_map[site].reshape(-1)[0]) for site in profile.nuisance_sites],
        dtype=np.float64,
    )

    expected_value = float(profile.g_value(u_map, noise))
    expected_gradients = profile.g_grad_functional(u_map, noise)
    expected_gradient = np.asarray(
        [
            float(expected_gradients[site].detach().reshape(-1)[0])
            for site in profile.nuisance_sites
        ],
        dtype=np.float64,
    )
    g_of, grad_of = integration.profile_potential_callables(profile)
    assert g_of(u0, float(noise)) == pytest.approx(
        expected_value, rel=0, abs=1e-10
    )
    np.testing.assert_allclose(
        grad_of(u0, float(noise)), expected_gradient, rtol=0, atol=1e-10
    )


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


def test_profile_logm_uses_curvature_retry_reoptimum(monkeypatch):
    # rev-5 §2c: a successful curvature retry re-optimizes u*, so the Laplace
    # value must combine g AND K at the SAME (retried) point. The quadratic
    # oracles used elsewhere reconverge to the identical point, so this path is
    # otherwise untested (codex defect 5 / Sonnet item 1). Simulate a retry that
    # lands at a materially different accepted point and assert the profile uses
    # g(cur["u_star"]), not g(optimizer u*).
    g_of, grad_of = _gaussian_profile_oracle()          # g maximized at ORACLE_MU
    retry_point = ORACLE_MU + np.array([0.5, 0.0, 0.0])
    logdet_A = float(np.linalg.slogdet(ORACLE_A)[1])

    def fake_curvature(g, grad, u_star, nuisance_order):
        # Pretend the §2c retry re-optimized to `retry_point` (SPD, accepted).
        return {
            "stop": False,
            "reason": "",
            "u_star": retry_point.copy(),
            "logdet": logdet_A,
            "logdet_by_h": {h: logdet_A for h in HESS_H_SWEEP},
            "retry_count": 1,
        }

    monkeypatch.setattr(integration, "curvature_gate", fake_curvature)
    grid = np.array([0.2, 0.5])
    result = integration.profile_logm_on_grid(
        g_of, grad_of, grid, ORACLE_MU, NUISANCE_ORDER
    )
    expected_g = g_of(retry_point, 0.2)                 # g at the RETRIED point
    expected_logm = expected_g + 1.5 * np.log(2.0 * np.pi) - 0.5 * logdet_A
    # Discriminating: g at the optimizer point (mu) differs by 0.125 nats.
    assert g_of(ORACLE_MU, 0.2) - expected_g == pytest.approx(0.125, abs=1e-9)
    assert result["logm"][0] == pytest.approx(expected_logm, rel=0, abs=1e-10)
    assert result["g_star"][0] == pytest.approx(expected_g, rel=0, abs=1e-10)
    np.testing.assert_allclose(result["u_stars"][0], retry_point, rtol=0, atol=1e-12)
