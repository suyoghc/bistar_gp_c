"""Byte-pinning tests for the PR-D divergence/MCSE freeze constants."""

from bistar_gp import m2c_freeze_dm as frozen


def test_every_divergence_and_mcse_constant_is_literal_pinned():
    assert frozen.DIVERGENCE_RATE_CAP == 0.001
    assert frozen.DIVERGENCE_CONC_FACTOR == 3
    assert frozen.DIVERGENCE_MIN_EVENT_FLOOR == 2
    assert frozen.DIVERGENCE_TIME_WINDOW_FRAC == 0.10
    assert frozen.MCSE_MBB_B == 1000
    assert frozen.MCSE_MBB_SEED == 20260712
    assert frozen.MCSE_BLOCK_LEN_FACTOR == 2
    assert frozen.MCSE_PRECISION_GATE == 0.02
    assert frozen.MCSE_SIR_REFERENCE == 0.441
    assert frozen.MCSE_SIR_REFERENCE_SE == 0.005
    assert frozen.W5_INDEPENDENT_POOL_SCATTER == (0.419, 0.438, 0.431)


def test_freeze_module_exports_every_pinned_name():
    expected = {
        "DIVERGENCE_RATE_CAP",
        "DIVERGENCE_CONC_FACTOR",
        "DIVERGENCE_MIN_EVENT_FLOOR",
        "DIVERGENCE_TIME_WINDOW_FRAC",
        "MCSE_MBB_B",
        "MCSE_MBB_SEED",
        "MCSE_BLOCK_LEN_FACTOR",
        "MCSE_PRECISION_GATE",
        "MCSE_SIR_REFERENCE",
        "MCSE_SIR_REFERENCE_SE",
        "W5_INDEPENDENT_POOL_SCATTER",
    }
    assert set(frozen.__all__) == expected
