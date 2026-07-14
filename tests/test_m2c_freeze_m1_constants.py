"""Pins for every prereg v1.17 M2c PR-C frozen constant."""

import math

from bistar_gp import m2c_freeze_m1 as frozen


def test_every_m1_freeze_constant_is_literal_pinned():
    assert frozen.OVERLAP_ALIGNMENT_THRESHOLD == 0.90
    assert frozen.Q_OVERLAP_CAP == 0.05
    assert frozen.M1_OUTPUTSCALE_MEDIAN == 2.4e-4
    assert frozen.M1_OUTPUTSCALE_SIGMA == 1.2
    assert frozen.M1_LENGTHSCALE_Z_LOC == -1.2528
    assert frozen.M1_LENGTHSCALE_Z_SCALE == 1.082
    assert frozen.M1_LENGTHSCALE_LOWER == 0.1
    assert frozen.M1_LENGTHSCALE_UPPER == 1.0
    assert frozen.M1_MATERN_NU == 1.5
    assert frozen.M1_LENGTHSCALE_QREF == (0.16, 0.30, 0.58)
    assert frozen.M1_LENGTHSCALE_MEDIAN == 0.30
    assert frozen.M1_SHORT_SCALE_NAME == "short_scale"
    assert frozen.M1_OVERLAP_REQUIRED_COMPONENTS == (
        "trend",
        "seasonal",
        "medium_term",
    )
    assert frozen.NUGGET_REFERENCE == 1.9e-4
    assert frozen.NUGGET_FLAG_THRESHOLD == 0.05
    assert frozen.M1_CORRELATION_CAP_REFERENCE_ONLY == 0.95
    assert frozen.M1_GATE_EIGENVALUE_FLOOR_REFERENCE_ONLY == 1e-3


def test_outputscale_log_location_and_reference_only_pair_are_pinned():
    assert math.isclose(
        math.log(frozen.M1_OUTPUTSCALE_MEDIAN), math.log(2.4e-4)
    )
    assert (
        frozen.M1_CORRELATION_CAP_REFERENCE_ONLY,
        frozen.M1_GATE_EIGENVALUE_FLOOR_REFERENCE_ONLY,
    ) == (0.95, 1e-3)
