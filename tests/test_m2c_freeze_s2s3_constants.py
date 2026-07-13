"""Byte-exact pins for prereg v1.17 rev-5 §§5.1-5.2 constants."""

from bistar_gp import m2c_freeze_s2s3 as frozen


def test_s2_constants_are_pinned():
    assert frozen.S2_FD_STEP == 1e-5
    assert frozen.S2_STABILITY_MULTIPLIERS == (0.5, 1.0, 2.0)
    assert frozen.S2_SKEW_TOL == 1e-5
    assert frozen.S2_STEP_STABILITY_TOL == 1e-3
    assert frozen.S2_DIRECTIONAL_TOL == 1e-3
    assert frozen.S2_WHITENING_TOL == 1e-8
    assert frozen.S2_EIG_FLOOR == 1e-6
    assert frozen.S2_ORACLE_TOL == 1e-10


def test_s3_constants_are_pinned():
    assert frozen.S3_SLOGDET_TOL == 1e-10
    assert frozen.S3_ROUNDTRIP_TOL == 1e-10
    assert frozen.S3_DENSITY_TOL == 1e-9
    assert frozen.S3_GRAD_ABS == 1e-4
    assert frozen.S3_GRAD_REL == 1e-4
    assert frozen.S3_N_STATES == 33
    assert frozen.S3_PRIOR_DRAW_SEEDS == tuple(range(100, 110))
    assert frozen.S3_NEIGHBORHOOD_SEEDS == (0, 1, 2, 3, 4)
    assert frozen.S3_NEIGHBORHOOD_SIGMAS == (0.1, 1.0)

