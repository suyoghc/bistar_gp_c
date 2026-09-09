"""
FIX-6 (2026-09 review): weighted aggregation in joint log space and posterior
draw weighting.

Pins: G = [[1000, 1001], [0, 0]], log_weights = [0, -1000], tau = 1 returns
[0.59384548, 0.40615452] (the pre-fix code underflowed to uniform); a common
log-weight shift cancels; all-absent support raises; the two-state posterior
example (equal prior masses, likelihood ratio 1:9, one mean-0 row and nine
mean-2 rows, unit variances, candidate means 0 and 2) gives mean divergences
[1.8, 0.2] under uniform weighting and the double-counted [1.9756, 0.0244]
under the explicit likelihood tilt; non-finite draws fail at entry of
average_gp_posterior.
"""

import logging

import numpy as np
import pytest
from scipy.special import logsumexp

import bistar_gp.metrics_v2  # noqa: F401  registers pw_kl_vcal
from bistar_gp.aggregation_v3 import average_gp_posterior, soft_transfer_weighted
from bistar_gp.bms_star import GPPosteriorSample
from bistar_gp.induced_prior import (
    ModelParameterSpace, ParameterSpec, compute_induced_prior,
)

NAMES = ["a", "b"]


def test_pinned_underflow_case_is_exact():
    G = np.array([[1000.0, 1001.0], [0.0, 0.0]])
    lw = np.array([0.0, -1000.0])
    r = soft_transfer_weighted(G, 1.0, NAMES, lw)
    assert np.allclose(r.instance_posteriors, [0.59384548, 0.40615452], atol=1e-8)
    exact = np.array([2.0, 1.0 + np.exp(-1.0)])
    assert np.allclose(r.instance_posteriors, exact / exact.sum(), atol=1e-12)
    assert r.metric_name == "weighted" and r.weight_ess.shape == (2,)
    assert np.all(r.weight_ess >= 1.0) and np.all(r.weight_ess <= 2.0 + 1e-12)


def test_common_log_weight_shift_cancels():
    rng = np.random.default_rng(6)
    G = rng.normal(size=(7, 3))
    lw = rng.normal(size=7)
    a = soft_transfer_weighted(G, 0.7, ["x", "y", "z"], lw).instance_posteriors
    b = soft_transfer_weighted(G, 0.7, ["x", "y", "z"], lw + 123.0).instance_posteriors
    c = soft_transfer_weighted(G, 0.7, ["x", "y", "z"], lw - 999.0).instance_posteriors
    assert np.allclose(a, b, atol=1e-12) and np.allclose(a, c, atol=1e-12)


def test_matches_direct_formula_in_the_representable_regime():
    rng = np.random.default_rng(7)
    G = rng.uniform(0.0, 3.0, size=(6, 4))
    lw = rng.normal(size=6)
    tau = 0.9
    w = np.exp(lw)
    terms = w[:, None] * np.exp(-G / tau)
    direct = terms.sum(axis=0) / w.sum()
    r = soft_transfer_weighted(G, tau, list("pqrs"), lw)
    assert np.allclose(r.instance_posteriors, direct / direct.sum(), atol=1e-12)
    ess = terms.sum(axis=0) ** 2 / (terms ** 2).sum(axis=0)
    assert np.allclose(r.weight_ess, ess, rtol=1e-10)
    # scores are the direct scores up to one global factor
    ratio = r.instance_scores / direct
    assert np.allclose(ratio, ratio[0], rtol=1e-10)


def test_all_absent_support_raises():
    G = np.zeros((3, 2))
    with pytest.raises(ValueError, match="no draw carries a finite log weight"):
        soft_transfer_weighted(G, 1.0, NAMES, np.full(3, -np.inf))
    with pytest.raises(ValueError):
        soft_transfer_weighted(G, 1.0, NAMES, np.array([np.nan, -np.inf, np.nan]))


def test_absent_draws_are_dropped_not_uniformized():
    G = np.array([[0.0, 5.0], [5.0, 0.0], [0.0, 5.0]])
    lw = np.array([0.0, -np.inf, 0.0])            # the middle draw is absent
    r = soft_transfer_weighted(G, 1.0, NAMES, lw)
    exact = np.array([1.0, np.exp(-5.0)])
    assert np.allclose(r.instance_posteriors, exact / exact.sum(), atol=1e-12)


# ── two-state posterior example (posterior draws must be weighted uniformly) ──

def _two_state_draws():
    means = [0.0] + [2.0] * 9              # posterior draws already at 1:9
    return [GPPosteriorSample(mean=np.array([m]), cov=np.eye(1), hyperparameters={})
            for m in means]


def _point_space(mean_value):
    # degenerate bounds make the reference prior draw the value exactly
    return ModelParameterSpace(
        model_name=f"const{mean_value}",
        param_specs=[ParameterSpec("m", (mean_value, mean_value), None),
                     ParameterSpec("sigma", (1.0, 1.0), None)],
        predict_fn=lambda x, p: np.full(len(x), p["m"]),
    )


@pytest.mark.parametrize("metric", ["kl_forward", "pw_kl_vcal"])
def test_two_state_posterior_uniform_weighting(metric):
    draws = _two_state_draws()
    x_eval = np.array([0.0])
    for mean_value, expected in ((0.0, 1.8), (2.0, 0.2)):
        res = compute_induced_prior(_point_space(mean_value), draws, x_eval,
                                    metric_name=metric, tau=1.0, n_param_samples=3, seed=0)
        assert np.allclose(res.G_per_sample, expected, atol=1e-12)


def test_two_state_posterior_likelihood_tilt_double_counts():
    draws = _two_state_draws()
    x_eval = np.array([0.0])
    log_mlls = np.log(np.array([1.0] + [9.0] * 9))
    for mean_value, expected in ((0.0, 2.0 * 81 / 82), (2.0, 2.0 / 82)):
        res = compute_induced_prior(_point_space(mean_value), draws, x_eval, log_mlls=log_mlls,
                                    weighting="likelihood_tilted", metric_name="kl_forward",
                                    n_param_samples=2, seed=0)
        assert np.allclose(res.G_per_sample, expected, atol=1e-12)
    assert np.isclose(2.0 * 81 / 82, 1.9756, atol=5e-5)
    assert np.isclose(2.0 / 82, 0.0244, atol=5e-5)


def test_log_mlls_under_uniform_weighting_is_a_conflict():
    """A legacy positional call must not silently run a different estimator
    (fix pass 1b, review F2)."""
    draws = _two_state_draws()
    log_mlls = np.log(np.array([1.0] + [9.0] * 9))
    with pytest.raises(ValueError, match="log_mlls supplied under weighting='uniform'"):
        compute_induced_prior(_point_space(0.0), draws, np.array([0.0]), log_mlls,
                              metric_name="kl_forward", n_param_samples=2, seed=0)
    res = compute_induced_prior(_point_space(0.0), draws, np.array([0.0]),
                                metric_name="kl_forward", n_param_samples=2, seed=0)
    assert np.allclose(res.G_per_sample, 1.8)


def test_tilt_requires_log_mlls_and_unknown_weighting_raises():
    draws = _two_state_draws()
    with pytest.raises(ValueError, match="requires log_mlls"):
        compute_induced_prior(_point_space(0.0), draws, np.array([0.0]),
                              weighting="likelihood_tilted", metric_name="kl_forward",
                              n_param_samples=2)
    with pytest.raises(ValueError, match="unknown weighting"):
        compute_induced_prior(_point_space(0.0), draws, np.array([0.0]),
                              weighting="mll", metric_name="kl_forward", n_param_samples=2)


def test_average_gp_posterior_rejects_nonfinite_draws():
    good = GPPosteriorSample(mean=np.zeros(3), cov=np.eye(3), hyperparameters={})
    bad_mean = GPPosteriorSample(mean=np.array([0.0, np.nan, 0.0]), cov=np.eye(3), hyperparameters={})
    with pytest.raises(ValueError, match=r"non-finite mean in draw\(s\) \[1\]"):
        average_gp_posterior([good, bad_mean])
    bad_cov = GPPosteriorSample(mean=np.zeros(3), cov=np.diag([1.0, np.inf, 1.0]), hyperparameters={})
    with pytest.raises(ValueError, match="covariance diagonal in draw 1"):
        average_gp_posterior([good, bad_cov])
    out = average_gp_posterior([good, good])
    assert np.all(np.isfinite(out.mean)) and np.all(np.isfinite(out.cov))
