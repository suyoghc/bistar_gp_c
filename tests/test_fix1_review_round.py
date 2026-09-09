"""
Fix pass 1b (2026-09 review round on fix pass 1): pins for the accepted
findings R1-R10 of the Codex review and the Fable self-check SC-1.

R1  an unknown sample site escapes compute_log_marginal_likelihoods;
R2  a draw that fails part-way is dropped whole (no partial rows);
R3  a component named like a group label cannot collide with the group;
R5  class labels need one entry per column and no repeats;
R6  large common offsets cancel exactly in the weighted posterior and ESS;
R7  a strict evaluation failure inside the optimizer raises, never a
    start-point expansion;
R8  start order is irrelevant under NaN objectives, a non-finite Hessian
    is flagged, and NaN ESS differs from absent support;
R9  the external-target checker rejects NaN columns and stored fields;
R10 the total covariance MATRIX (not only its diagonal) matches a direct
    per-draw conditioning plus the between-draw covariance of the means;
and the universe firewall rejects a roster before any metric call.
"""

import copy
import json

import numpy as np
import pytest

torch = pytest.importorskip("torch")
gpytorch = pytest.importorskip("gpytorch")

from gpytorch.kernels import LinearKernel, RBFKernel, ScaleKernel

import bistar_gp.metrics_v2  # noqa: F401
from bistar_gp import debias
from bistar_gp.aggregation_v3 import compute_log_marginal_likelihoods, soft_transfer_weighted
from bistar_gp.bms_star import (
    METRICS, GPPosteriorSample, boltzmann_weight_ess, compute_G_matrix, log_weight_ess,
    soft_transfer,
)
from bistar_gp.candidates import CandidateResult
from bistar_gp.debias import _raw_parameter_map, decompose_model_hmc, decompose_model_mcmc
from bistar_gp.decompose import compute_cholesky, decompose_additive_gp, decompose_component
from bistar_gp.external_targets import check_external_targets, external_target_errors
from bistar_gp.induced_prior import ModelParameterSpace, ParameterSpec
from bistar_gp.laplace_evidence import (
    EvaluationFailure, _weight_ess, is_log_Z_Mx, laplace_log_Z_Mx,
    laplace_log_evidence_ordinary,
)
from bistar_gp.model import build_model, build_toy_kernels

torch.set_default_dtype(torch.float64)

SITES = {
    "ls": "covar_module.kernels.0.base_kernel.lengthscale_prior",
    "os": "covar_module.kernels.0.outputscale_prior",
    "lv": "covar_module.kernels.1.variance_prior",
    "noise": "likelihood.noise_covar.noise_prior",
}


def _samples(ls, os_, lv, noise):
    return {SITES["ls"]: np.asarray(ls, float), SITES["os"]: np.asarray(os_, float),
            SITES["lv"]: np.asarray(lv, float), SITES["noise"]: np.asarray(noise, float)}


@pytest.fixture
def toy():
    x = torch.linspace(-6, 6, 14)
    y = torch.sin(x) + 0.25 * x
    kers, names = build_toy_kernels()
    model, lik = build_model(x, y, kers, names)
    return model, lik, x, y, torch.linspace(-7, 7, 11)


def _direct_draw(x, y, x_test, ls, os_, lv, noise, jitter=1e-4):
    kers, names = build_toy_kernels()
    model, lik = build_model(x, y, kers, names)
    model.kernel_components[0].base_kernel.lengthscale = ls
    model.kernel_components[0].outputscale = os_
    model.kernel_components[1].variance = lv
    lik.noise = noise
    model.eval(); lik.eval()
    km = model.get_component_kernel_matrices(x, x_test)
    with torch.no_grad():
        per = decompose_additive_gp([km[n]["XX"] for n in names], [km[n]["XstarX"] for n in names],
                                    [km[n]["XstarXstar"] for n in names], [km[n]["XXstar"] for n in names],
                                    noise, y, jitter)
        L = compute_cholesky(sum(km[n]["XX"] for n in names), noise, jitter)
        fm, fc = decompose_component(sum(km[n]["XstarX"] for n in names),
                                     sum(km[n]["XstarXstar"] for n in names),
                                     sum(km[n]["XXstar"] for n in names), L, y)
    return {n: (m.numpy(), c.numpy()) for (m, c), n in zip(per, names)}, (fm.numpy(), fc.numpy())


# ── R1 ──────────────────────────────────────────────────────────────

def test_r1_unknown_site_escapes_the_mll_routine():
    x = torch.linspace(-3, 3, 12)
    y = torch.sin(x)
    good = {SITES["ls"]: 1.0, SITES["os"]: 1.0, SITES["lv"]: 0.1, SITES["noise"]: 0.1}
    bad = dict(good, **{"covar_module.kernels.0.alpha_prior": 2.0})
    gp_bad = [GPPosteriorSample(mean=np.zeros(4), cov=np.eye(4), hyperparameters=bad)]
    with pytest.raises(ValueError, match="alpha_prior"):
        compute_log_marginal_likelihoods(gp_bad, x, y, kernel_builder=build_toy_kernels)
    gp_good = [GPPosteriorSample(mean=np.zeros(4), cov=np.eye(4), hyperparameters=good)]
    lm = compute_log_marginal_likelihoods(gp_good, x, y, kernel_builder=build_toy_kernels)
    assert np.isfinite(lm).all()


# ── R2 ──────────────────────────────────────────────────────────────

def test_r2_failed_draw_is_dropped_whole(toy, monkeypatch):
    model, lik, x, y, x_test = toy
    samples = _samples([1.0, 2.0], [1.0, 0.5], [0.05, 0.1], [0.1, 0.2])
    real = debias.decompose_component
    calls = {"n": 0}

    def flaky(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 2:          # second target of the first draw
            raise RuntimeError("injected after the first target")
        return real(*args, **kwargs)

    monkeypatch.setattr(debias, "decompose_component", flaky)
    res = decompose_model_hmc(model, lik, x, y, x_test, samples, kernel_builder=build_toy_kernels,
                              n_posterior_samples=2, strict=False, rng=np.random.default_rng(0))
    assert res.n_draws_retained == 1 and len(res.dropped) == 1
    for comp in list(res.components.values()) + [res.full]:
        assert comp.conditional_means.shape[0] == 1 and comp.n_draws == 1
        assert np.allclose(np.diag(comp.cov), comp.std ** 2)
    calls["n"] = 0
    with pytest.raises(RuntimeError, match="injected"):
        decompose_model_hmc(model, lik, x, y, x_test, samples, kernel_builder=build_toy_kernels,
                            n_posterior_samples=2, rng=np.random.default_rng(0))


# ── R3 ──────────────────────────────────────────────────────────────

def test_r3_component_named_like_a_group_does_not_collide():
    x = torch.linspace(-6, 6, 14)
    y = torch.sin(x) + 0.25 * x
    x_test = torch.linspace(-7, 7, 9)
    model, lik = build_model(x, y, [ScaleKernel(RBFKernel()), LinearKernel(), ScaleKernel(RBFKernel())],
                             ["a", "b", "a,b"])
    pm = _raw_parameter_map(model, lik)
    samples = {n: np.array([float(p.item()), float(p.item()) + 0.1]) for n, p in pm.items()}
    res = decompose_model_mcmc(model, lik, x, y, x_test, samples, n_posterior_samples=2,
                               groups=[["a", "b"]], rng=np.random.default_rng(0))
    comp, grp = res.components["a,b"], res.group(["a", "b"])
    assert not np.allclose(comp.mean, grp.mean)
    assert np.allclose(grp.mean, res.components["a"].mean + res.components["b"].mean, atol=1e-10)
    assert "__full__" not in res.components and res.full.name == "__full__"
    # a repeated name is one member (review F3): no group is stored, the
    # request resolves to the component
    res2 = decompose_model_mcmc(model, lik, x, y, x_test, samples, n_posterior_samples=2,
                                groups=[["a", "a"]], rng=np.random.default_rng(0))
    assert res2.groups == {} and res2.group(["a", "a"]) is res2.components["a"]


# ── R5 ──────────────────────────────────────────────────────────────

def test_f4_soft_transfer_rejects_non_finite_G():
    G = np.array([[0.0, 1.0], [np.nan, 0.5], [0.2, 0.3]])
    with pytest.raises(ValueError, match="soft_transfer: G_matrix contains non-finite"):
        soft_transfer(G, 1.0, ["a", "b"])
    with pytest.raises(ValueError, match="soft_transfer"):
        soft_transfer(np.array([[0.0, np.inf]]), 1.0, ["a", "b"])


def test_round3_weighted_and_convention_paths_reject_non_finite_G():
    """Kimi K3-3 / GLM F4: the weighted path returned all-NaN posteriors
    silently; GLM F1: aggregate_convention returned a UNIFORM posterior."""
    from bistar_gp.bms_star import aggregate_convention
    nan_G = np.array([[0.0, 1.0], [np.nan, 0.5]])
    with pytest.raises(ValueError, match="soft_transfer_weighted: G_matrix contains non-finite"):
        soft_transfer_weighted(nan_G, 1.0, ["a", "b"], np.zeros(2))
    for G in (nan_G, np.full((2, 2), np.inf)):
        for variant in ("pooled", "rowmin", "expected_posterior"):
            with pytest.raises(ValueError, match="finite G matrix"):
                aggregate_convention(G, 1.0, variant)


def test_round3_negative_conditional_diagonal_keeps_cov_and_std_consistent(toy, monkeypatch):
    """Kimi K3-4: a numerically negative conditional variance was clipped in
    std but not in the accumulated covariance."""
    model, lik, x, y, x_test = toy
    real = debias.decompose_component

    def neg_diag(*args, **kwargs):
        m, c = real(*args, **kwargs)
        c = c.clone()
        c[0, 0] = -1e-6
        return m, c

    monkeypatch.setattr(debias, "decompose_component", neg_diag)
    res = decompose_model_hmc(model, lik, x, y, x_test, _samples([1.0, 2.0], [1.0, 0.5], [0.05, 0.1], [0.1, 0.2]),
                              kernel_builder=build_toy_kernels, n_posterior_samples=2,
                              rng=np.random.default_rng(0))
    for comp in list(res.components.values()) + [res.full]:
        assert np.allclose(np.diag(comp.cov), comp.std ** 2, atol=1e-15)
        assert np.all(comp.conditional_vars >= 0.0)


def test_round3_unknown_singleton_names_the_component(toy):
    """GLM F8: a typo'd singleton used to be told to request a group."""
    model, lik, x, y, x_test = toy
    from bistar_gp.debias import decompose_model
    res = decompose_model(model, lik, x, y, x_test, n_samples=2)
    with pytest.raises(KeyError, match="unknown component 'typo'"):
        res.group(["typo"])


def test_r5_class_names_need_one_label_per_column():
    G = np.array([[0.0, 1.0], [1.0, 0.0]])
    with pytest.raises(ValueError):
        soft_transfer(G, 1.0, ["a", "b"], class_names=["A", "B", "B"])
    with pytest.raises(ValueError):
        soft_transfer(G, 1.0, ["a", "b"], class_names=["A"])
    with pytest.raises(ValueError, match="instance_names"):
        soft_transfer(G, 1.0, ["a"])
    assert soft_transfer(G, 1.0, ["a", "b"], class_names=["B", "A"]).class_names == ["B", "A"]


# ── R6 ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("offset", [0.0, 1e4, 1e12, 1e16])
def test_r6_large_common_offsets_cancel_exactly(offset):
    G = np.full((9, 2), offset)
    r = soft_transfer_weighted(G, 1.0, ["a", "b"], np.zeros(9))
    assert np.allclose(r.instance_posteriors, [0.5, 0.5], atol=1e-15)
    assert r.instance_posteriors.sum() == pytest.approx(1.0, abs=1e-15)
    assert np.allclose(r.weight_ess, 9.0, atol=1e-12)
    assert np.allclose(boltzmann_weight_ess(G, 1.0), 9.0, atol=1e-12)
    assert np.allclose(soft_transfer(G, 1.0, ["a", "b"]).weight_ess, 9.0, atol=1e-12)


def test_r6_weighted_scores_keep_the_pre_fix_scale():
    rng = np.random.default_rng(0)
    G, lw, tau = rng.uniform(0, 3, (6, 3)), rng.normal(size=6), 0.7
    w = np.exp(lw - lw.max())
    log_boltz = -G / tau
    log_boltz -= log_boltz.max()
    old = (w[:, None] * np.exp(log_boltz)).sum(0) / w.sum()
    assert np.allclose(soft_transfer_weighted(G, tau, list("abc"), lw).instance_scores, old, rtol=1e-12)


# ── R8(iii): the one ESS routine ────────────────────────────────────

def test_log_weight_ess_distinguishes_nan_from_absent_support():
    assert log_weight_ess(np.array([0.0, 0.0, -np.inf])) == pytest.approx(2.0)
    assert log_weight_ess(np.array([-np.inf, -np.inf])) == 0.0
    assert np.isnan(log_weight_ess(np.array([0.0, np.nan])))
    assert np.isnan(_weight_ess(np.array([0.0, np.nan]))) and _weight_ess(np.array([-np.inf])) == 0.0
    col = log_weight_ess(np.array([[0.0, np.nan, -np.inf], [0.0, 0.0, -np.inf]]), axis=0)
    assert col[0] == pytest.approx(2.0) and np.isnan(col[1]) and col[2] == 0.0
    big = np.array([700.0, 699.0])                 # exp(700) overflows without the shift
    with np.errstate(over="raise"):
        assert log_weight_ess(big) == pytest.approx((1 + np.exp(-1.0)) ** 2 / (1 + np.exp(-2.0)))


# ── R7 / R8: strict evaluation failures and NaN paths in the Laplace routines ──

X_EVAL = np.linspace(0.0, 1.0, 5)
GP = GPPosteriorSample(mean=0.5 * X_EVAL, cov=0.01 * np.eye(5), hyperparameters={})


def _space(predict, name="Probe"):
    return ModelParameterSpace(name, [ParameterSpec("a", (-1.0, 1.0), None),
                                      ParameterSpec("sigma", (0.5, 0.5001), None)], predict)


def _raises_in_band(lo, hi):
    def predict(x, p):
        if lo < p["a"] < hi:
            raise ValueError("predictor failed inside the optimizer's step")
        return p["a"] * x
    return predict


def test_r7_strict_evaluation_failure_inside_the_optimizer_raises():
    ps = _space(_raises_in_band(0.0, 1e-6))          # fine at a=0, the 1e-8 finite-difference point raises
    start = [{"a": 0.0, "sigma": 0.5}]
    with pytest.raises(EvaluationFailure):
        laplace_log_Z_Mx(ps, X_EVAL, GP, tau=1.0, starts=start)
    with pytest.raises(EvaluationFailure):
        is_log_Z_Mx(ps, X_EVAL, GP, [1.0], n_is=50, starts=start)
    x_train = np.linspace(0.0, 1.0, 6)
    with pytest.raises(EvaluationFailure):
        laplace_log_evidence_ordinary(ps, x_train, 0.5 * x_train, mle_params={"a": 0.0, "sigma": 0.5})
    assert issubclass(EvaluationFailure, RuntimeError)     # pass-1 callers catching RuntimeError still do
    z = laplace_log_Z_Mx(ps, X_EVAL, GP, tau=1.0, starts=start, strict=False)
    assert not z.converged                                 # non-strict: a flagged fallback, no raise


def test_r8_start_order_is_irrelevant_under_nan_objectives():
    def predict(x, p):
        if p["a"] < 0:
            raise ValueError("undefined region")
        return p["a"] * x
    ps = _space(predict)
    bad, good = {"a": -0.5, "sigma": 0.5}, {"a": 0.5, "sigma": 0.5}
    r1 = laplace_log_Z_Mx(ps, X_EVAL, GP, tau=1.0, starts=[bad, good], strict=False)
    r2 = laplace_log_Z_Mx(ps, X_EVAL, GP, tau=1.0, starts=[good, bad], strict=False)
    assert np.isfinite(r1.log_Z) and r1.log_Z == r2.log_Z and r1.G_at_min == r2.G_at_min
    assert r1.n_starts_failed == r2.n_starts_failed == 1
    r3 = laplace_log_Z_Mx(ps, X_EVAL, GP, tau=1.0, starts=[bad], strict=False)
    assert np.isnan(r3.log_Z) and not r3.converged and r3.n_starts_failed == 1


def test_r8_non_finite_hessian_stencil_is_flagged():
    def predict(x, p):                      # finite at the optimum a=0.5 and at the 1e-8 gradient step,
        a = p["a"]                          # NaN on the 1e-4 Hessian stencil
        return (np.nan if 1e-6 < abs(a - 0.5) < 1e-3 else a) * x
    ps = _space(predict)
    z = laplace_log_Z_Mx(ps, X_EVAL, GP, tau=1.0, starts=[{"a": 0.5, "sigma": 0.5}], strict=False)
    assert np.isnan(z.log_Z) and z.converged is False and z.n_starts_failed == 1
    assert "non-finite Hessian" in z.optimizer["message"]


# ── R9 ──────────────────────────────────────────────────────────────

FIXTURE = {
    "target_a": {"names": ["M1 (theta=0.15)", "M2 (theta=0.20)"],
                 "rows": [{"tau": 1.0, "M1 (theta=0.15)": 0.49965650872257117, "M2 (theta=0.20)": 0.5003434912774289},
                          {"tau": 1e-07, "M1 (theta=0.15)": 0.4, "M2 (theta=0.20)": 0.6}]},
    "target_b": {"names": ["M_x beta(50,50)", "M_z beta(2,2)"],
                 "rows": [{"tau": 1.0, "M_x beta(50,50)": 0.5296605155174497, "M_z beta(2,2)": 0.47033948448255036},
                          {"tau": 1e-07, "M_x beta(50,50)": 0.841418950016495, "M_z beta(2,2)": 0.15858104998350495}]},
    "abs_error_at_min_tau": {"A": 0.0, "B": 6.404745348520535e-07},
}


def test_r9_nan_columns_and_stored_fields_fail(tmp_path):
    p = tmp_path / "ok.json"
    p.write_text(json.dumps(FIXTURE))
    assert check_external_targets(str(p))["A"] == 0.0
    cases = [("target_a", "M1 (theta=0.15)", "A"), ("target_a", "M2 (theta=0.20)", "A"),
             ("target_b", "M_x beta(50,50)", "B"), ("target_b", "M_z beta(2,2)", "B")]
    for i, (block, col, key) in enumerate(cases):
        bad = copy.deepcopy(FIXTURE)
        bad[block]["rows"][-1][col] = float("nan")
        q = tmp_path / f"bad{i}.json"
        q.write_text(json.dumps(bad))
        with pytest.raises(AssertionError, match=f"external target {key}"):
            check_external_targets(str(q))
        with pytest.raises(AssertionError, match=f"external target {key}"):
            external_target_errors(bad)
    stale = copy.deepcopy(FIXTURE)
    stale["abs_error_at_min_tau"]["B"] = float("nan")
    q = tmp_path / "stale.json"
    q.write_text(json.dumps(stale))
    with pytest.raises(AssertionError, match="stored"):
        check_external_targets(str(q))


# ── R10 ─────────────────────────────────────────────────────────────

def test_r10_total_covariance_matrix_matches_direct_conditioning(toy):
    model, lik, x, y, x_test = toy
    draws = [(0.7, 1.5, 0.05, 0.1), (3.0, 0.4, 0.2, 0.3), (1.2, 0.9, 0.1, 0.05)]
    names = list(model.component_names)
    res = decompose_model_hmc(model, lik, x, y, x_test, _samples(*zip(*draws)),
                              kernel_builder=build_toy_kernels, n_posterior_samples=3,
                              groups=[names], rng=np.random.default_rng(0))
    direct = [_direct_draw(x, y, x_test, *d) for d in draws]
    for name in names:
        means = np.stack([d[0][name][0] for d in direct])
        covs = np.stack([d[0][name][1] for d in direct])
        expected = covs.mean(0) + np.cov(means, rowvar=False, bias=True)
        assert np.allclose(res.components[name].cov, expected, atol=1e-10)
        between = np.cov(means, rowvar=False, bias=True)
        assert np.abs(between - np.diag(np.diag(between))).max() > 1e-6   # the fixture has off-diagonal between-draw terms
    fm = np.stack([d[1][0] for d in direct])
    fc = np.stack([d[1][1] for d in direct])
    assert np.allclose(res.full.cov, fc.mean(0) + np.cov(fm, rowvar=False, bias=True), atol=1e-10)
    assert np.allclose(res.group(names).cov, res.full.cov)


# ── firewall: rejection precedes any metric call ────────────────────

def test_firewall_rejects_before_any_metric_call():
    calls = {"n": 0}

    def counting(mu_p, cov_p, mu_q, cov_q):
        calls["n"] += 1
        return 0.0

    METRICS["__counting__"] = counting
    try:
        gp = [GPPosteriorSample(mean=np.zeros(3), cov=np.eye(3), hyperparameters={})]
        mixed = [CandidateResult("a", np.zeros(3), np.eye(3), 1.0, {}, "toy"),
                 CandidateResult("b", np.zeros(3), np.eye(3), 1.0, {}, None)]
        with pytest.raises(ValueError):
            compute_G_matrix(gp, mixed, "__counting__")
        assert calls["n"] == 0
        same = [CandidateResult("a", np.zeros(3), np.eye(3), 1.0, {}, "toy"),
                CandidateResult("b", np.zeros(3), np.eye(3), 1.0, {}, "toy")]
        compute_G_matrix(gp, same, "__counting__")
        assert calls["n"] == 2
    finally:
        METRICS.pop("__counting__", None)
