"""
FIX-4 (2026-09 review): Hellinger exponents and the firewall boundary.

Pins: N(0,1) versus N(1,1) gives 1 - exp(-1/8) for both metrics_v2 Hellinger
variants, equality gives 0, and a variance-rescaled pair matches the base
pw_hellinger; every candidate-aware entry point rejects mixed and partially
tagged rosters before any metric call, while same-universe and all-untagged
rosters pass.
"""

import numpy as np
import pytest

import bistar_gp.metrics_v2  # noqa: F401  registers the v2 metrics
from bistar_gp.aggregation_v3 import (
    run_robust_aggregation, run_weighted_bms_star, score_averaged_gp,
)
from bistar_gp.bms_star import (
    METRICS, GPPosteriorSample, compute_G_matrix, hellinger_distance,
    pw_hellinger, run_bms_star, soft_transfer,
)
from bistar_gp.candidates import CandidateResult


def test_equal_variance_hellinger_identity():
    mu_p, cov_p, mu_q, cov_q = np.array([0.0]), np.eye(1), np.array([1.0]), np.eye(1)
    expected = 1.0 - np.exp(-1.0 / 8.0)
    assert expected == pytest.approx(0.11750309741540454)
    assert hellinger_distance(mu_p, cov_p, mu_q, cov_q) == pytest.approx(expected)
    assert pw_hellinger(mu_p, cov_p, mu_q, cov_q) == pytest.approx(expected)
    assert METRICS["pw_hellinger_vcal"](mu_p, cov_p, mu_q, cov_q) == pytest.approx(expected)
    assert METRICS["pw_hellinger_mean"](mu_p, cov_p, mu_q, cov_q) == pytest.approx(expected)
    assert METRICS["pw_hellinger_vcal"](mu_p, cov_p, mu_p, cov_p) == 0.0
    assert METRICS["pw_hellinger_mean"](mu_p, cov_p, mu_p, cov_p) == 0.0


def test_vcal_matches_base_pointwise_hellinger_at_matched_variances():
    rng = np.random.default_rng(2)
    n = 6
    mu_p, mu_q = rng.normal(size=n), rng.normal(size=n)
    var_p = rng.uniform(0.2, 3.0, size=n)
    cov_p = np.diag(var_p)
    # base metric with the candidate variance set equal to the GP variance
    base = pw_hellinger(mu_p, cov_p, mu_q, cov_p)
    assert METRICS["pw_hellinger_vcal"](mu_p, cov_p, mu_q, np.eye(n)) == pytest.approx(base)
    assert METRICS["pw_hellinger_mean"](mu_p, cov_p, mu_q, np.eye(n)) == pytest.approx(
        pw_hellinger(mu_p, np.eye(n), mu_q, np.eye(n)))


def _gp(n_eval=4, k=3, seed=0):
    rng = np.random.default_rng(seed)
    return [GPPosteriorSample(mean=rng.normal(size=n_eval), cov=np.diag(np.full(n_eval, 0.1)),
                              hyperparameters={"draw": float(i)}) for i in range(k)]


def _cand(name, universe, n_eval=4, shift=0.0):
    return CandidateResult(name=name, mean=np.full(n_eval, shift), cov=np.eye(n_eval) * 0.1,
                           noise_var=0.1, parameters={}, universe=universe)


MIXED = [_cand("Quad+2Harm", "main_ladder"), _cand("Quad+2Harm", "appendix_trend3", shift=0.1)]
PARTIAL = [_cand("Quad+2Harm", "appendix_trend3"), _cand("Linear", None, shift=0.1)]
SAME = [_cand("Linear+2Harm", "appendix_trend3"), _cand("Quad+2Harm", "appendix_trend3", shift=0.1)]
UNTAGGED = [_cand("Linear", None), _cand("Quadratic", None, shift=0.1)]


@pytest.mark.parametrize("roster", [MIXED, PARTIAL], ids=["mixed", "partial"])
def test_every_entry_point_rejects_bad_rosters(roster):
    gp = _gp()
    with pytest.raises(ValueError, match="A4"):
        compute_G_matrix(gp, roster, "pw_mse")
    with pytest.raises(ValueError, match="A4"):
        run_bms_star(gp, roster, ["pw_mse"], np.array([1.0]))
    with pytest.raises(ValueError, match="A4"):
        score_averaged_gp(gp, roster, ["pw_mse"])
    with pytest.raises(ValueError, match="A4"):
        run_robust_aggregation(gp, roster, ["pw_mse"])
    with pytest.raises(ValueError, match="A4"):
        run_weighted_bms_star(gp, roster, np.zeros(3), ["pw_mse"], np.array([1.0]))


@pytest.mark.parametrize("roster", [SAME, UNTAGGED], ids=["same-universe", "untagged"])
def test_permitted_rosters_pass_every_entry_point(roster):
    gp = _gp()
    G = compute_G_matrix(gp, roster, "pw_mse")
    assert G.shape == (3, 2)
    assert soft_transfer(G, 1.0, [c.name for c in roster], metric_name="pw_mse").instance_posteriors.sum() == pytest.approx(1.0)
    assert run_bms_star(gp, roster, ["pw_mse"], np.array([1.0]))["pw_mse"][1.0].instance_posteriors.sum() == pytest.approx(1.0)
    assert score_averaged_gp(gp, roster, ["pw_mse"])["pw_mse"]["posteriors"].sum() == pytest.approx(1.0)
    assert run_robust_aggregation(gp, roster, ["pw_mse"])["pw_mse"]["median"].posteriors.sum() == pytest.approx(1.0)
    r = run_weighted_bms_star(gp, roster, np.zeros(3), ["pw_mse"], np.array([1.0]))
    assert r["pw_mse"][1.0].instance_posteriors.sum() == pytest.approx(1.0)
