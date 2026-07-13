"""Pins prereg v1.17 profile-core constants to rev-5 sha256
c3e9db66e189b2a8cad19bf11b5c4acc6518d4b6d2597ae93b0f700587d1ce3f.
"""

import pytest

from bistar_gp import m2c_freeze as frozen


def test_rev5_source_is_cited():
    assert "v1.17" in frozen.__doc__
    assert (
        "c3e9db66e189b2a8cad19bf11b5c4acc6518d4b6d2597ae93b0f700587d1ce3f"
        in frozen.__doc__
    )


def test_p3_grid_and_domain_constants_are_frozen():
    assert frozen.PROFILE_GRID_BASE_LO == 0.005
    assert frozen.PROFILE_GRID_BASE_HI == 1.2
    assert frozen.PROFILE_GRID_BASE_N == 40
    assert frozen.PROFILE_GRID_RATIO == pytest.approx(
        (1.2 / 0.005) ** (1.0 / 39.0), rel=0, abs=0
    )
    assert frozen.FULL_DOMAIN_LO == 1e-7
    assert frozen.FULL_DOMAIN_HI == 1e4
    assert frozen.FULL_DOMAIN_N_NODES == 182
    assert frozen.FULL_DOMAIN_N_WITH_EDGES == 184
    assert frozen.CAP_LADDER_UPPER_DIAGNOSTIC == (10.0, 100.0, 1000.0)
    assert frozen.CAP_LADDER_LOWER_DIAGNOSTIC == (1e-4, 1e-5, 1e-6)
    assert frozen.EPS_DOMAIN == 1e-4
    assert frozen.EPS_GRID == 1e-4
    assert frozen.REFINE_L_MAX == 3
    assert frozen.TOY_BAND_EDGES == (0.15, 0.30)


def test_p1_gradient_constants_are_frozen():
    assert frozen.FD_STEP_GRAD == 1e-5
    assert frozen.TOL_GRAD_ABS == 1e-4
    assert frozen.TOL_GRAD_REL == 1e-4
    assert frozen.PRIOR_DRAW_SEEDS == tuple(range(100, 110))
    assert frozen.D23_SENTINEL_MIN_REL == 1e-2


def test_optimizer_gate_constants_are_frozen():
    assert frozen.LBFGSB_MAXITER == 500
    assert frozen.LBFGSB_MAXFUN == 5000
    assert frozen.LBFGSB_FTOL == 1e-12
    assert frozen.LBFGSB_GTOL == 1e-8
    assert frozen.TAU_STAT == 1e-4
    assert frozen.AGREE_DG_REL == 1e-6
    assert frozen.AGREE_DU_INF == 1e-4
    assert frozen.RESTART_JITTER_SCALE == 1e-3
    assert frozen.RESTART_RNG_BASE == 300


def test_curvature_gate_constants_are_frozen():
    assert frozen.HESS_H_SWEEP == (5e-4, 1e-3, 2e-3)
    assert frozen.HESS_H_CENTER == 1e-3
    assert frozen.LOGDET_STABILITY_TOL == 1e-3
    assert frozen.SYMMETRY_TOL == 1e-6
    assert frozen.DIRECTIONAL_TOL == 1e-3
    assert frozen.DIRECTIONAL_EPS == 1e-3
    assert frozen.DIRECTION_RNG_SEEDS == (200, 201, 202)
    assert frozen.RCOND_MIN == 1e-8
    assert frozen.RETRY_GTOL == 1e-10
    assert frozen.RETRY_FTOL == 1e-14
    assert frozen.RETRY_MAXITER == 1000
