"""
FIX-5 (2026-09 review): evaluation failures are not finite energies, and
optimizer provenance reaches the caller.

Pins: an always-raising predictor raises under strict mode and yields NaN
evidence with zero ESS under non-strict mode, so it cannot win a comparison
with a finite probability; a valid very large divergence stays a valid
finite evidence; a negative-valued metric cannot reward a failed draw in the
induced prior; a forced optimizer exception and a forced success=False both
reach the caller's record; the multi-start candidate fits prefer successful
restarts; every pre-existing Laplace/estimator value is unchanged (the
existing suites run alongside this file).
"""

from types import SimpleNamespace

import numpy as np
import pytest
from scipy.optimize import OptimizeResult

pytest.importorskip("torch")

import bistar_gp.laplace_evidence as le
from bistar_gp.bms_star import METRICS, GPPosteriorSample
from bistar_gp.candidates import CandidateModel, build_toy_candidates
from bistar_gp.induced_prior import ModelParameterSpace, ParameterSpec, compute_induced_prior
from bistar_gp.laplace_evidence import (
    is_log_Z_Mx, laplace_log_Z_Mx, mc_log_Z_Mx, model_posterior,
)

X_EVAL = np.linspace(0.0, 4.0, 15)
GP = SimpleNamespace(mean=0.5 * X_EVAL - 0.3, cov=np.eye(15) * 0.05)


@pytest.fixture
def mse_metric():
    name = "_mse_fix5_test"
    METRICS[name] = lambda mp, cp, mq, cq: float(np.mean((np.asarray(mp) - np.asarray(mq)) ** 2))
    yield name
    del METRICS[name]


def _space(predict_fn, name="Lin"):
    return ModelParameterSpace(
        model_name=name,
        param_specs=[ParameterSpec("a", (-1.0, 1.0), None), ParameterSpec("b", (-1.0, 1.0), None)],
        predict_fn=predict_fn, noise_param="sigma")


def _raise(x, p):
    raise ZeroDivisionError("always failing predictor")


def test_raising_predictor_raises_under_strict(mse_metric):
    ps = _space(_raise)
    with pytest.raises(RuntimeError, match="always failing predictor"):
        laplace_log_Z_Mx(ps, X_EVAL, GP, metric_name=mse_metric)
    with pytest.raises(RuntimeError, match="always failing predictor"):
        mc_log_Z_Mx(ps, X_EVAL, GP, [1.0], n_mc=50, metric_name=mse_metric)
    with pytest.raises(RuntimeError, match="always failing predictor"):
        is_log_Z_Mx(ps, X_EVAL, GP, [1.0], n_is=50, metric_name=mse_metric,
                    starts=[{"a": 0.5, "b": -0.3}])


def test_raising_predictor_yields_nan_not_a_win_under_non_strict(mse_metric):
    ps = _space(_raise)
    z = laplace_log_Z_Mx(ps, X_EVAL, GP, metric_name=mse_metric, strict=False)
    assert np.isnan(z.log_Z) and not z.converged
    mc = mc_log_Z_Mx(ps, X_EVAL, GP, [1.0], n_mc=50, metric_name=mse_metric, strict=False)
    assert np.isnan(mc.log_Z[0]) and mc.ess[0] == 0.0
    iss = is_log_Z_Mx(ps, X_EVAL, GP, [1.0], n_is=50, metric_name=mse_metric,
                      starts=[{"a": 0.5, "b": -0.3}], strict=False)
    assert np.isnan(iss.log_Z[0]) and iss.ess[0] == 0.0 and iss.n_starts_failed >= 1
    good = _space(lambda x, p: p["a"] * x + p["b"], "Good")
    mpr = model_posterior({"Good": good, "Bad": ps}, X_EVAL, GP.mean, X_EVAL, GP, None,
                          construction="I", metric_name=mse_metric, tau=0.5,
                          occam=False, strict=False)
    assert np.isnan(mpr.posteriors["Bad"])          # not a finite win
    assert mpr.all_converged is False
    assert mpr.components["Bad"]["converged"] is False


def test_valid_huge_divergence_stays_valid(mse_metric):
    far = _space(lambda x, p: 2000.0 + 0.0 * x + p["a"] * 0.0 + p["b"] * 0.0, "Far")
    z = laplace_log_Z_Mx(far, X_EVAL, GP, metric_name=mse_metric, tau=1.0)
    assert np.isfinite(z.log_Z)
    assert z.G_at_min == pytest.approx(np.mean((GP.mean - 2000.0) ** 2))


def test_negative_metric_cannot_reward_a_failed_draw():
    name = "_neg_flaky_fix5"

    def metric(mu_p, cov_p, mu_q, cov_q):
        if float(mu_p[0]) == 999.0:
            raise ValueError("simulated failure on the marker draw")
        return -5.0 + 0.01 * float(np.mean((np.asarray(mu_p) - np.asarray(mu_q)) ** 2))

    METRICS[name] = metric
    try:
        ok = GPPosteriorSample(mean=np.zeros(3), cov=np.eye(3), hyperparameters={})
        bad = GPPosteriorSample(mean=np.array([999.0, 0.0, 0.0]), cov=np.eye(3), hyperparameters={})
        ps = ModelParameterSpace(model_name="C", param_specs=[ParameterSpec("c", (0.0, 1.0), None)],
                                 predict_fn=lambda x, p: p["c"] + 0.0 * x, noise_param="sigma")
        ip = compute_induced_prior(ps, [ok, bad], np.zeros(3), np.zeros(2), metric_name=name,
                                   n_param_samples=4, seed=0)
        for s_idx in range(4):
            c = ip.param_samples[s_idx, 0]
            g_ok = metric(ok.mean, ok.cov, np.full(3, c), np.eye(3) * 0.09)
            # the failed draw must pull the average ABOVE the healthy value
            assert ip.G_per_sample[s_idx] > g_ok
    finally:
        del METRICS[name]


def test_forced_optimizer_exception_and_failure_reach_the_caller(mse_metric, monkeypatch):
    ps = _space(lambda x, p: p["a"] * x + p["b"])

    def boom(*a, **k):
        raise RuntimeError("forced optimizer failure")

    monkeypatch.setattr(le, "minimize", boom)
    z = laplace_log_Z_Mx(ps, X_EVAL, GP, metric_name=mse_metric)
    assert z.converged is False and z.n_starts_failed == 1
    assert "forced optimizer failure" in z.optimizer["exception"]

    def not_converged(fun, x0, **k):
        return OptimizeResult(x=np.asarray(x0, float), success=False, status=2,
                              message="forced non-convergence", nit=0, nfev=1, fun=fun(x0))

    monkeypatch.setattr(le, "minimize", not_converged)
    z2 = laplace_log_Z_Mx(ps, X_EVAL, GP, metric_name=mse_metric)
    assert z2.converged is False and z2.n_starts_failed == 1
    assert z2.optimizer["message"] == "forced non-convergence" and z2.optimizer["exception"] is None
    ev = le.laplace_log_evidence_ordinary(ps, X_EVAL, GP.mean)
    assert ev.converged is False and ev.n_starts_failed == 1
    mpr = model_posterior({"Lin": ps}, X_EVAL, GP.mean, X_EVAL, GP, None,
                          construction="II", metric_name=mse_metric, tau=0.5)
    assert mpr.all_converged is False and mpr.components["Lin"]["n_starts_failed"] == 1


def test_candidate_fits_report_status_and_prefer_successful_restarts():
    x = np.linspace(-10, 10, 20)
    y = np.sin(x) + 0.25 * x
    for cand in build_toy_candidates():
        cand.fit(x, y)                       # every toy fit still completes
    cm = CandidateModel()
    params, nll, status = cm._fit_mle(x, y, lambda x_, p: p[0] * x_ + p[1],
                                      [0.0, 0.0, np.log(0.5)], return_status=True)
    assert set(status) == {"success", "status", "message", "nit"}
    assert status["success"] is True and np.isfinite(nll)
    two = cm._fit_mle(x, y, lambda x_, p: p[0] * x_ + p[1], [0.0, 0.0, np.log(0.5)])
    assert len(two) == 2
    worse_but_ok = (np.zeros(3), 5.0, {"success": True, "message": "ok"})
    better_but_failed = (np.ones(3), 1.0, {"success": False, "message": "ABNORMAL"})
    chosen = CandidateModel._select_restart([better_but_failed, worse_but_ok], "T")
    assert chosen is worse_but_ok
    only_failed = CandidateModel._select_restart([better_but_failed], "T")
    assert only_failed is better_but_failed
