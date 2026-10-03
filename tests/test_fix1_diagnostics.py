"""
FIX-3 (2026-09 review): draw-level diagnostics and the soft_transfer contract.

Pins: uniform weights give ESS = N; one dominant draw gives ESS near 1; a
per-candidate column shift of G leaves ESS invariant; ESS stays finite when
a candidate's raw weights underflow; G = [[0, 0], [10, 11]] gives attainment
[1, 0.5] and split credit [0.75, 0.25]; the tau-to-zero limit of the
expected-posterior convention equals the split credit on a tied fixture;
existing pooled probabilities are unchanged; grouped class_names raise;
metric_name survives the result and is "unspecified" when absent.
"""

import numpy as np
import pytest

from bistar_gp.bms_star import (
    BMSStarResult, boltzmann_weight_ess, hard_win_statistics, soft_transfer,
)

rng = np.random.default_rng(0)


def test_uniform_weights_give_ess_equal_to_n():
    G = np.tile(rng.gamma(2.0, 1.0, size=(1, 4)), (9, 1))   # every row identical
    assert np.allclose(boltzmann_weight_ess(G, 0.7), 9.0)


def test_one_dominant_draw_gives_ess_near_one():
    G = np.full((50, 3), 1000.0)
    G[7] = 0.0
    ess = boltzmann_weight_ess(G, 1.0)
    assert np.allclose(ess, 1.0, atol=1e-12)


def test_ess_invariant_under_column_shift_and_finite_under_underflow():
    G = rng.gamma(2.0, 1.0, size=(20, 4))
    shifted = G + rng.normal(size=(1, 4)) * 50.0
    assert np.allclose(boltzmann_weight_ess(G, 0.5), boltzmann_weight_ess(shifted, 0.5))
    G2 = np.array([[0.0, 0.0], [5000.0, 5000.0], [0.0, 10000.0]])
    ess = boltzmann_weight_ess(G2, 1.0)
    assert np.all(np.isfinite(ess))
    assert ess[0] == pytest.approx(2.0) and ess[1] == pytest.approx(1.0)
    with pytest.raises(ValueError):
        boltzmann_weight_ess(np.array([[0.0, np.inf]]), 1.0)


def test_tie_rule_on_the_ledger_fixture():
    G = np.array([[0.0, 0.0], [10.0, 11.0]])
    credit, attainment, tie_fraction = hard_win_statistics(G)
    assert np.allclose(attainment, [1.0, 0.5])
    assert np.allclose(credit, [0.75, 0.25])
    assert tie_fraction == pytest.approx(0.5)
    assert credit.sum() == pytest.approx(1.0)
    # candidate order must not break ties
    credit_r, attainment_r, _ = hard_win_statistics(G[:, ::-1])
    assert np.allclose(credit_r, credit[::-1]) and np.allclose(attainment_r, attainment[::-1])
    # tau -> 0 limit of expected-posterior aggregation equals the split credit
    tau = 1e-6
    w = np.exp(-(G - G.min(axis=1, keepdims=True)) / tau)
    eqp = (w / w.sum(axis=1, keepdims=True)).mean(axis=0)
    assert np.allclose(eqp, credit, atol=1e-12)


def test_soft_transfer_carries_diagnostics_and_keeps_probabilities():
    G = rng.gamma(2.0, 1.0, size=(30, 4))
    names = [f"m{j}" for j in range(4)]
    r = soft_transfer(G, 1.3, names, metric_name="pw_mse")
    direct = np.exp(-G / 1.3).mean(axis=0)
    assert np.allclose(r.instance_posteriors, direct / direct.sum(), atol=1e-12)
    assert r.metric_name == "pw_mse"
    assert np.allclose(r.weight_ess, boltzmann_weight_ess(G, 1.3))
    credit, attainment, tie = hard_win_statistics(G)
    assert np.allclose(r.hard_win_credit, credit) and np.allclose(r.attainment, attainment)
    assert r.tie_fraction == tie == 0.0
    r2 = soft_transfer(G, 1.3, names)
    assert r2.metric_name == "unspecified"
    r3 = soft_transfer(G, 0.4, names, normalize_per_draw=True, metric_name="x")
    Ge = G - G.min(axis=1, keepdims=True)
    assert np.allclose(r3.weight_ess, boltzmann_weight_ess(Ge, 0.4))
    assert isinstance(r3, BMSStarResult)


def test_grouped_class_names_raise_and_relabelling_passes():
    G = rng.gamma(2.0, 1.0, size=(5, 3))
    names = ["a", "b", "c"]
    with pytest.raises(ValueError, match="class-level averaging"):
        soft_transfer(G, 1.0, names, class_names=["A", "A", "B"])
    r = soft_transfer(G, 1.0, names, class_names=["A", "B", "C"])
    assert r.class_names == ["A", "B", "C"]
    assert np.allclose(r.class_posteriors, r.instance_posteriors)
