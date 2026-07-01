"""
Regression tests for the canonical Z_Mx / evidence / posterior machinery
(bistar_gp/laplace_evidence.py; see docs/plan-zmx-laplace.md, DECISIONS D3).

Guards:
  - laplace_log_Z_Mx (data-free model prior) matches a brute-force grid integral.
  - the Occam toggle subtracts exactly log V_ref.
  - Z_Mx never sees the data (depends only on the GP), and changes with the GP.
  - the induced within-model evidence is Occam/V_ref-independent (the volume cancels).
  - the three constructions assemble as specified; the "Z_Mx × induced-evidence"
    combination telescopes to Construction II (documenting the double-use trap).
  - _laplace_logdet caps cliff curvature and survives non-PSD input.
"""

import numpy as np
import pytest
from types import SimpleNamespace
from numpy.polynomial.legendre import leggauss

pytest.importorskip("torch")  # import chain (bms_star) needs torch

import bistar_gp.laplace_evidence as le
from bistar_gp.laplace_evidence import (
    laplace_log_Z_Mx, laplace_log_evidence_ordinary, laplace_log_evidence_induced,
    model_posterior, _laplace_logdet, _log_reference_volume,
)
from bistar_gp.bms_star import METRICS
from bistar_gp.induced_prior import ParameterSpec, ModelParameterSpace

TAU = 0.5
X_EVAL = np.linspace(0.0, 4.0, 15)
A_TRUE, B_TRUE = 0.5, -0.3
GP_MEAN = A_TRUE * X_EVAL + B_TRUE
AVG_GP = SimpleNamespace(mean=GP_MEAN, cov=np.eye(len(X_EVAL)) * 0.05)


@pytest.fixture
def mse_metric():
    """Controlled smooth metric: mean squared error of the means (ignores cov)."""
    name = "_mse_means_test"
    METRICS[name] = lambda mp, cp, mq, cq: float(np.mean((np.asarray(mp) - np.asarray(mq)) ** 2))
    yield name
    del METRICS[name]


def lin_space(a_bounds=(-1.0, 1.0), b_bounds=(-1.0, 1.0)):
    # noise_param 'sigma' is absent from the specs -> fixed at 0.3 internally,
    # so the integral is over (a, b) only (interior MAP, clean Laplace).
    return ModelParameterSpace(
        model_name="Lin",
        param_specs=[ParameterSpec("a", a_bounds, None), ParameterSpec("b", b_bounds, None)],
        predict_fn=lambda x, p: p["a"] * x + p["b"],
        noise_param="sigma",
    )


def quad_space():
    return ModelParameterSpace(
        model_name="Quad",
        param_specs=[ParameterSpec("a", (-0.5, 0.5), None),
                     ParameterSpec("b", (-1.0, 1.0), None),
                     ParameterSpec("c", (-1.0, 1.0), None)],
        predict_fn=lambda x, p: p["a"] * x ** 2 + p["b"] * x + p["c"],
        noise_param="sigma",
    )


def test_zmx_matches_brute_force(mse_metric):
    # Laplace approximates the integral over R^2 (interior MAP, bounds-agnostic), so the
    # brute-force box must be wide enough to contain the Boltzmann Gaussian's mass.
    HALF = 4.0
    ps = lin_space((-HALF, HALF), (-HALF, HALF))
    res = laplace_log_Z_Mx(ps, X_EVAL, AVG_GP, metric_name=mse_metric, tau=TAU, occam=False)

    n = 300
    nd, w = leggauss(n)
    a = nd * HALF
    wa = w * HALF
    A, B = np.meshgrid(a, a)
    W = np.outer(wa, wa).ravel()
    Gvals = np.array([np.mean((GP_MEAN - (aa * X_EVAL + bb)) ** 2)
                      for aa, bb in zip(A.ravel(), B.ravel())])
    log_brute = np.log(np.sum(W * np.exp(-Gvals / TAU)))
    assert abs(res.log_Z - log_brute) < 0.02


def test_occam_subtracts_log_volume(mse_metric):
    ps = lin_space()
    no_occ = laplace_log_Z_Mx(ps, X_EVAL, AVG_GP, metric_name=mse_metric, tau=TAU, occam=False)
    occ = laplace_log_Z_Mx(ps, X_EVAL, AVG_GP, metric_name=mse_metric, tau=TAU, occam=True)
    assert occ.log_Z - no_occ.log_Z == pytest.approx(-_log_reference_volume(ps), abs=1e-9)


def test_zmx_depends_on_gp_not_data(mse_metric):
    ps = lin_space()
    r1 = laplace_log_Z_Mx(ps, X_EVAL, AVG_GP, metric_name=mse_metric, tau=TAU)
    r2 = laplace_log_Z_Mx(ps, X_EVAL, AVG_GP, metric_name=mse_metric, tau=TAU)
    assert r1.log_Z == r2.log_Z                      # deterministic, no data input
    shifted = SimpleNamespace(mean=GP_MEAN + 5.0, cov=AVG_GP.cov)
    r3 = laplace_log_Z_Mx(ps, X_EVAL, AVG_GP, metric_name=mse_metric, tau=TAU)  # unchanged gp
    r4 = laplace_log_Z_Mx(ps, X_EVAL, shifted, metric_name=mse_metric, tau=TAU)
    assert r3.log_Z != r4.log_Z                      # changes when the GP changes


def test_induced_evidence_is_volume_independent(mse_metric):
    x_train = np.linspace(0, 4, 20)
    y_train = A_TRUE * x_train + B_TRUE
    ev_narrow = laplace_log_evidence_induced(
        lin_space((-1, 1), (-1, 1)), x_train, y_train, X_EVAL, AVG_GP,
        metric_name=mse_metric, tau=TAU)
    ev_wide = laplace_log_evidence_induced(
        lin_space((-2, 2), (-2, 2)), x_train, y_train, X_EVAL, AVG_GP,
        metric_name=mse_metric, tau=TAU)
    # Interior MAP unchanged; the −log V_ref in N and in Z_prior cancels.
    assert ev_narrow.log_evidence == pytest.approx(ev_wide.log_evidence, abs=1e-6)


def _posteriors(construction, spaces, x_train, y_train, metric, occam=False):
    r = model_posterior(spaces, x_train, y_train, X_EVAL, AVG_GP, mle_params=None,
                        construction=construction, metric_name=metric, tau=TAU, occam=occam)
    return np.array([r.posteriors[n] for n in r.model_names]), r.model_names


def test_constructions_assemble_and_differ(mse_metric):
    spaces = {"Lin": lin_space(), "Quad": quad_space()}
    x_train = np.linspace(0, 4, 20)
    y_train = A_TRUE * x_train + B_TRUE
    base, names = _posteriors("baseline", spaces, x_train, y_train, mse_metric)
    pI, _ = _posteriors("I", spaces, x_train, y_train, mse_metric)
    pII, _ = _posteriors("II", spaces, x_train, y_train, mse_metric)
    for p in (base, pI, pII):
        assert p.sum() == pytest.approx(1.0)
        assert np.all(p >= 0)
    assert not np.allclose(pI, pII)          # I and II are different objects
    # baseline == softmax of the ordinary evidences (wiring check)
    ord_logs = np.array([laplace_log_evidence_ordinary(spaces[n], x_train, y_train).log_evidence
                         for n in names])
    man = np.exp(ord_logs - ord_logs.max()); man /= man.sum()
    assert np.allclose(base, man, atol=1e-9)


def test_double_use_collapses_to_construction_II(mse_metric):
    """Z_Mx(occam) × induced-evidence telescopes to Construction II — not an extra boost."""
    spaces = {"Lin": lin_space(), "Quad": quad_space()}
    x_train = np.linspace(0, 4, 20)
    y_train = A_TRUE * x_train + B_TRUE
    names = list(spaces)
    combo = []
    for n in names:
        z = laplace_log_Z_Mx(spaces[n], X_EVAL, AVG_GP, metric_name=mse_metric,
                             tau=TAU, occam=True).log_Z
        ev = laplace_log_evidence_induced(spaces[n], x_train, y_train, X_EVAL, AVG_GP,
                                          metric_name=mse_metric, tau=TAU).log_evidence
        combo.append(z + ev)
    combo = np.array(combo)
    combo_post = np.exp(combo - combo.max()); combo_post /= combo_post.sum()
    pII, _ = _posteriors("II", spaces, x_train, y_train, mse_metric, occam=True)
    assert np.allclose(combo_post, pII, atol=1e-6)


def test_laplace_logdet_caps_and_floors():
    logdet_big, n_big = _laplace_logdet(np.diag([1.0, 1e18]))
    assert n_big == 1
    assert logdet_big < 30.0                       # capped, not ~log(1e18)=41.4
    logdet_neg, n_neg = _laplace_logdet(np.diag([1.0, -5.0]))
    assert np.isfinite(logdet_neg)                 # non-PSD floored, not NaN/inf
    assert n_neg == 1
