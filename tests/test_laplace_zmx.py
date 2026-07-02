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
    # baseline == softmax of the ordinary evidences (wiring check; occam=False
    # matches model_posterior's default so both use the Lebesgue reference)
    ord_logs = np.array([laplace_log_evidence_ordinary(spaces[n], x_train, y_train,
                                                       occam=False).log_evidence
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


@pytest.fixture
def const_metric():
    """GP-indifferent metric: Ḡ ≡ 2.0 for every parameter value."""
    name = "_const_test"
    METRICS[name] = lambda mp, cp, mq, cq: 2.0
    yield name
    del METRICS[name]


def test_construction_gaps_are_volume_free_without_occam(const_metric):
    """With a GP-indifferent metric (Ḡ ≡ c) and occam=False, II − baseline must
    equal −c/τ for every model regardless of its V_ref. The old code always
    subtracted log V_ref in the ordinary evidence but never in log N, leaking
    per-model volume differences into the ladder's 'GP contribution'."""
    spaces = {"LinNarrow": lin_space((-1, 1), (-1, 1)),
              "LinWide": lin_space((-4, 4), (-4, 4))}
    x_train = np.linspace(0, 4, 20)
    y_train = A_TRUE * x_train + B_TRUE
    base = model_posterior(spaces, x_train, y_train, X_EVAL, AVG_GP, None,
                           construction="baseline", metric_name=const_metric,
                           tau=TAU, occam=False)
    pII = model_posterior(spaces, x_train, y_train, X_EVAL, AVG_GP, None,
                          construction="II", metric_name=const_metric,
                          tau=TAU, occam=False)
    gaps = [pII.log_kernel[n] - base.log_kernel[n] for n in spaces]
    assert gaps[0] == pytest.approx(-2.0 / TAU, abs=1e-6)
    assert gaps[0] == pytest.approx(gaps[1], abs=1e-6)


def test_ordinary_evidence_occam_toggle_controls_volume():
    """occam=False: Lebesgue measure, box-independent for an interior MAP;
    occam=True (default): proper marginal likelihood, shifts by −Δlog V_ref."""
    x_train = np.linspace(0, 4, 20)
    y_train = A_TRUE * x_train + B_TRUE
    narrow, wide = lin_space((-1, 1), (-1, 1)), lin_space((-2, 2), (-2, 2))
    no_n = laplace_log_evidence_ordinary(narrow, x_train, y_train, occam=False)
    no_w = laplace_log_evidence_ordinary(wide, x_train, y_train, occam=False)
    assert no_n.log_evidence == pytest.approx(no_w.log_evidence, abs=1e-6)
    occ_n = laplace_log_evidence_ordinary(narrow, x_train, y_train)
    occ_w = laplace_log_evidence_ordinary(wide, x_train, y_train)
    dV = _log_reference_volume(wide) - _log_reference_volume(narrow)
    assert occ_n.log_evidence - occ_w.log_evidence == pytest.approx(dV, abs=1e-6)


def test_zmx_tau_scaling_is_analytic(mse_metric):
    """log Z(τ) must follow −Ḡ*/τ + (d/2)log(2πτ) − ½log|H_Ḡ| exactly: the
    optimization, Hessian, and eigenvalue clipping are evaluated once on Ḡ, so
    which eigenvalues get floored cannot depend on τ. Under the old f = Ḡ/τ
    implementation, extreme τ pushed H/τ below the absolute floor and bent
    τ-sensitivity curves for numerical rather than statistical reasons."""
    ps = lin_space()
    r1 = laplace_log_Z_Mx(ps, X_EVAL, AVG_GP, metric_name=mse_metric, tau=1.0)
    r2 = laplace_log_Z_Mx(ps, X_EVAL, AVG_GP, metric_name=mse_metric, tau=1e12)
    G, d = r1.G_at_min, r1.n_params
    expected_gap = (-G / 1e12 + G / 1.0) + 0.5 * d * np.log(1e12)
    assert r2.log_Z - r1.log_Z == pytest.approx(expected_gap, rel=1e-12)
    assert r1.logdet_H == r2.logdet_H          # H_Ḡ is τ-free
    assert r1.n_clipped == r2.n_clipped == 0


def test_flat_direction_is_flagged(mse_metric):
    """A parameter the model ignores gives a zero-curvature direction; the
    floored log-det must surface as n_clipped > 0, not vanish silently."""
    ps = ModelParameterSpace(
        model_name="LinDead",
        param_specs=[ParameterSpec("a", (-1.0, 1.0), None),
                     ParameterSpec("b", (-1.0, 1.0), None),
                     ParameterSpec("dead", (-1.0, 1.0), None)],
        predict_fn=lambda x, p: p["a"] * x + p["b"],   # 'dead' unused
        noise_param="sigma",
    )
    r = laplace_log_Z_Mx(ps, X_EVAL, AVG_GP, metric_name=mse_metric, tau=TAU)
    assert r.n_clipped >= 1


def test_laplace_logdet_caps_and_floors():
    logdet_big, n_big = _laplace_logdet(np.diag([1.0, 1e18]))
    assert n_big == 1
    assert logdet_big < 30.0                       # capped, not ~log(1e18)=41.4
    logdet_neg, n_neg = _laplace_logdet(np.diag([1.0, -5.0]))
    assert np.isfinite(logdet_neg)                 # non-PSD floored, not NaN/inf
    assert n_neg == 1


def test_default_metric_registered_on_import():
    """Importing laplace_evidence must register its default metric itself,
    not depend on a caller having imported metrics_v2 first."""
    assert "pw_kl_vcal" in METRICS  # the module's default metric_name


def test_construction_II_component_decomposition(mse_metric):
    """Construction II components must satisfy fit + gp_penalty + occam == log_N,
    and log_N is the (unnormalized) log kernel."""
    ps = {"Lin": lin_space()}
    xt = np.linspace(0.0, 4.0, 20)
    yt = A_TRUE * xt + B_TRUE
    mle = {"Lin": {"a": A_TRUE, "b": B_TRUE}}
    mpr = model_posterior(ps, xt, yt, X_EVAL, AVG_GP, mle,
                          construction="II", metric_name=mse_metric, tau=TAU)
    c = mpr.components["Lin"]
    assert c["log_lik_at_map"] + c["gp_penalty"] + c["occam"] == pytest.approx(c["log_N"], abs=1e-6)
    assert mpr.log_kernel["Lin"] == pytest.approx(c["log_N"], abs=1e-12)
