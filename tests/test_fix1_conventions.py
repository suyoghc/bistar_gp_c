"""
FIX-9 (2026-09 review): the three aggregation conventions of section 2.3 in
the package, so Cases A and C share one implementation.

Pins: `pooled` equals soft_transfer(normalize_per_draw=False) posteriors to
1e-12 and is bit-identical to the pre-fix _boltzmann_posterior arithmetic;
`rowmin` equals normalize_per_draw=True; `expected_posterior` equals a
per-row softmax averaged over rows and is bit-identical to the Case A
script's arithmetic; its tau-to-0 limit equals the FIX-3 split credit on a
tied fixture; a global G offset leaves all three unchanged and a per-row
offset changes `pooled` only; prior_sensitivity_study._boltzmann_posterior
delegates to the pooled variant.
"""

import importlib.util
import os
import sys

import numpy as np
import pytest
from scipy.special import softmax

import bistar_gp
from bistar_gp.bms_star import aggregate_convention, hard_win_statistics, soft_transfer

VARIANTS = ("pooled", "rowmin", "expected_posterior")
EXPERIMENTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "experiments")


def _import_pss():
    """prior_sensitivity_study imports its sibling scripts by bare name."""
    if EXPERIMENTS_DIR not in sys.path:
        sys.path.insert(0, EXPERIMENTS_DIR)
    return pytest.importorskip("prior_sensitivity_study")
# Driver-provided copy of the case-A script; set FIX1_FIXTURE_DIR to the directory
# holding e7_convention_sensitivity.py to exercise it (skipped otherwise).
E7_FIXTURE = os.path.join(os.environ.get("FIX1_FIXTURE_DIR", ""), "e7_convention_sensitivity.py")


def _old_boltzmann_posterior(G, tau):
    """Verbatim pre-fix experiments/prior_sensitivity_study._boltzmann_posterior."""
    lw = -G / tau
    w = np.exp(lw - lw.max())
    s = w.mean(axis=0)
    tot = s.sum()
    return s / tot if tot > 0 else np.ones(G.shape[1]) / G.shape[1]


def _case_a_aggregate(G, tau, variant):
    """Verbatim arithmetic of experiments/e7_convention_sensitivity.aggregate
    (paper/case-a-vanbork), with pss._boltzmann_posterior inlined."""
    if variant == "pooled":
        return _old_boltzmann_posterior(G, tau)
    if variant == "rowmin":
        Ge = G - G.min(axis=1, keepdims=True)
        return _old_boltzmann_posterior(Ge, tau)
    if variant == "expected_posterior":
        lw = -(G - G.min(axis=1, keepdims=True)) / tau
        w = np.exp(lw)
        w = w / w.sum(axis=1, keepdims=True)
        s = w.mean(axis=0)
        return s / s.sum()
    raise ValueError(variant)


def _G(seed=0, n=9, m=4, scale=3.0):
    return np.random.default_rng(seed).uniform(0.0, scale, size=(n, m))


@pytest.mark.parametrize("seed", [0, 1, 2])
@pytest.mark.parametrize("tau", [0.05, 0.3, 1.0, 10.0])
def test_bit_identical_to_the_case_a_arithmetic(seed, tau):
    G = _G(seed)
    for variant in VARIANTS:
        assert np.array_equal(aggregate_convention(G, tau, variant), _case_a_aggregate(G, tau, variant))


def test_pooled_and_rowmin_match_soft_transfer():
    G, names = _G(3), list("abcd")
    for tau in (0.1, 1.0, 5.0):
        pooled = aggregate_convention(G, tau, "pooled")
        rowmin = aggregate_convention(G, tau, "rowmin")
        st_false = soft_transfer(G, tau, names, normalize_per_draw=False).instance_posteriors
        st_true = soft_transfer(G, tau, names, normalize_per_draw=True).instance_posteriors
        assert np.allclose(pooled, st_false, atol=1e-12)
        assert np.allclose(rowmin, st_true, atol=1e-12)
        assert np.array_equal(pooled, _old_boltzmann_posterior(G, tau))


def test_expected_posterior_is_the_average_per_row_softmax():
    G = _G(4)
    for tau in (0.2, 1.0):
        ref = softmax(-G / tau, axis=1).mean(axis=0)
        assert np.allclose(aggregate_convention(G, tau, "expected_posterior"), ref, atol=1e-12)


def test_expected_posterior_low_tau_limit_is_split_credit():
    G = np.array([[0.0, 0.0, 1.0],
                  [0.0, 1.0, 0.0],
                  [2.0, 2.0, 2.0],
                  [0.5, 0.0, 0.7]])
    # rows: {0,1} tied; {0,2} tied; all three tied; candidate 1 alone
    hand = np.array([(0.5 + 0.5 + 1 / 3 + 0.0) / 4,
                     (0.5 + 0.0 + 1 / 3 + 1.0) / 4,
                     (0.0 + 0.5 + 1 / 3 + 0.0) / 4])
    credit = hard_win_statistics(G)[0]
    assert np.allclose(credit, hand, atol=1e-12)
    assert np.allclose(aggregate_convention(G, 1e-9, "expected_posterior"), hand, atol=1e-12)


def test_offsets():
    G = _G(5)
    rows = np.random.default_rng(9).normal(size=(G.shape[0], 1))
    for tau in (0.3, 2.0):
        for variant in VARIANTS:
            base = aggregate_convention(G, tau, variant)
            assert np.allclose(aggregate_convention(G + 7.5, tau, variant), base, atol=1e-12)
            shifted = aggregate_convention(G + rows, tau, variant)
            if variant == "pooled":
                assert not np.allclose(shifted, base, atol=1e-6)
            else:
                assert np.allclose(shifted, base, atol=1e-12)


def test_unknown_variant_raises_and_export_exists():
    with pytest.raises(ValueError, match="unknown aggregation variant"):
        aggregate_convention(_G(), 1.0, "median")
    assert bistar_gp.aggregate_convention is aggregate_convention


def test_prior_sensitivity_study_delegates():
    pss = _import_pss()
    G = _G(11)
    for tau in (0.1, 1.0):
        assert np.array_equal(pss._boltzmann_posterior(G, tau), aggregate_convention(G, tau, "pooled"))
        assert np.array_equal(pss._boltzmann_posterior(G, tau), _old_boltzmann_posterior(G, tau))


@pytest.mark.skipif(not os.environ.get("FIX1_FIXTURE_DIR") or not os.path.exists(E7_FIXTURE),
                    reason="FIX1_FIXTURE_DIR with e7_convention_sensitivity.py not provided")
def test_matches_the_case_a_script_fixture():
    pss = _import_pss()
    spec = importlib.util.spec_from_file_location("e7_fixture", E7_FIXTURE)
    mod = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("prior_sensitivity_study", pss)
    try:
        spec.loader.exec_module(mod)
    except Exception as exc:  # the fixture's own imports are not under test
        pytest.skip(f"fixture not importable here: {exc!r}")
    G = _G(12)
    for tau in (0.1, 1.0, 3.0):
        for variant in VARIANTS:
            assert np.array_equal(aggregate_convention(G, tau, variant), mod.aggregate(G, tau, variant))
