"""No real chain; synthetic contribution series exercising the estimator."""

import math

import numpy as np

from bistar_gp.bms_star import soft_transfer
from bistar_gp.mcse_strategy import mcse_strategy_estimate
from bistar_gp.m2c_freeze_dm import (
    MCSE_MBB_B,
    MCSE_MBB_SEED,
    MCSE_PRECISION_GATE,
    MCSE_SIR_REFERENCE,
    MCSE_SIR_REFERENCE_SE,
    W5_INDEPENDENT_POOL_SCATTER,
)


def _synthetic_g(n_draws=120):
    t = np.arange(n_draws, dtype=np.float64)
    phase = 2.0 * np.pi * t / n_draws
    chains = []
    for offset in (0.0, 0.37):
        smooth = np.sin(phase + offset) + 0.35 * np.sin(2.0 * phase - offset)
        chains.append(np.column_stack((
            0.8 * smooth + 0.001 * t,
            -0.55 * smooth + 0.15 * np.cos(3.0 * phase + offset),
            0.4 * np.cos(phase - offset) + 0.002 * t,
        )))
    return np.asarray(chains, dtype=np.float64)


def test_known_iact_and_frozen_seed_determinism():
    G = _synthetic_g()
    first = mcse_strategy_estimate(G, 1.0, ("a", "b", "c"), 1)
    second = mcse_strategy_estimate(G, 1.0, ("a", "b", "c"), 1)
    assert first["verdict"] == "DETERMINED"
    assert np.isfinite(first["mcse"])
    assert first["mcse"] >= 0.0
    assert first["tau_int"] > 1.0
    assert first["block_len"] == math.ceil(2.0 * first["tau_int"])
    assert first["mcse"] == second["mcse"]


def test_constant_series_is_undetermined():
    G = np.zeros((2, 32, 2), dtype=np.float64)
    report = mcse_strategy_estimate(G, 1.0, ("a", "b"), 0)
    assert report["verdict"] == "UNDETERMINED"
    assert report["mcse"] is None
    assert "zero variance" in report["error"]


def test_too_short_chain_is_undetermined():
    G = _synthetic_g(n_draws=4)
    report = mcse_strategy_estimate(G, 1.0, ("a", "b", "c"), 1)
    assert report["verdict"] == "UNDETERMINED"
    assert report["mcse"] is None
    assert report["block_len"] >= G.shape[1]
    assert "chain too short" in report["error"]


def test_nonfinite_g_is_undetermined():
    G = _synthetic_g()
    G[0, 3, 1] = np.nan
    report = mcse_strategy_estimate(G, 1.0, ("a", "b", "c"), 1)
    assert report["verdict"] == "UNDETERMINED"
    assert report["mcse"] is None
    assert "non-finite" in report["error"]


def test_global_shift_invariance():
    G = _synthetic_g()
    baseline = mcse_strategy_estimate(G, 0.7, ("a", "b", "c"), 2)
    shifted = mcse_strategy_estimate(G + 123.25, 0.7, ("a", "b", "c"), 2)
    assert baseline["verdict"] == shifted["verdict"] == "DETERMINED"
    assert np.isclose(baseline["mcse"], shifted["mcse"], rtol=0.0, atol=1e-12)


def test_separate_reporting_fields_are_present_and_uncombined():
    report = mcse_strategy_estimate(
        _synthetic_g(), 1.0, ("a", "b", "c"), 1
    )
    assert report["precision_gate"] == MCSE_PRECISION_GATE == 0.02
    assert report["mcse_sir_reference"] == MCSE_SIR_REFERENCE == 0.441
    assert report["mcse_sir_reference_se"] == MCSE_SIR_REFERENCE_SE == 0.005
    assert report["w5_independent_pool_scatter"] == W5_INDEPENDENT_POOL_SCATTER
    assert report["B"] == MCSE_MBB_B == 1000
    assert report["seed"] == MCSE_MBB_SEED == 20260712
    assert "separately" in report["reporting_note"]
    assert "combined" not in report


def test_mbb_is_discriminated_from_iid_row_bootstrap():
    G = _synthetic_g(n_draws=160)
    mbb = mcse_strategy_estimate(G, 1.0, ("a", "b", "c"), 1)
    assert mbb["verdict"] == "DETERMINED"
    assert mbb["block_len"] > 1

    pooled = G.reshape(-1, G.shape[-1])
    rng = np.random.default_rng(MCSE_MBB_SEED)
    iid = np.empty(MCSE_MBB_B, dtype=np.float64)
    for replicate in range(MCSE_MBB_B):
        rows = rng.integers(0, pooled.shape[0], pooled.shape[0])
        iid[replicate] = soft_transfer(
            pooled[rows], 1.0, ["a", "b", "c"], normalize_per_draw=False
        ).instance_posteriors[1]
    iid_sd = float(iid.std(ddof=0))
    assert mbb["mcse"] >= iid_sd
    assert not np.isclose(mbb["mcse"], iid_sd, rtol=1e-6, atol=0.0)
