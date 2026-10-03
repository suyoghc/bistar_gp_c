"""
Fix pass 2a (2026-09-26 project review, SYNTHESIS section 10): package
contracts, one pinning test per queue item. Each test fails on the pre-2a
code (the fix branch at 69deeda).

2a-1  compute_G_matrix: an all-failed table and a candidate that failed on
      every draw raise; a partial failure keeps the penalty and is logged.
2a-2  compute_induced_prior: failed parameter points carry zero mass (strict
      raises); every point failing raises; the ESS counts valid points only.
2a-3  extraction and decomposition require every sampled site, and one
      draw count across arrays whatever the dictionary order.
2a-4  is_log_Z_Mx rejects an empty or invalid tau ladder.
2a-5  a sinusoid fit with no successful restart raises.
2a-6  DecompositionResult.noise_var is the retained-draw mean, order-free.
2a-7  the withdrawn-cache registry follows D33/D34 and guards the
      fit-method experiment's cache read.
2a-8  soft_transfer warns below an ESS floor; ties split the console credit
      and the SIR serialization records tie-aware draw-win statistics.
2a-9  the tau sweep and the ablation ladder carry the Laplace records;
      compute_cholesky logs each jitter escalation.
2a-10 the Case D producer fails loud and records seed, counts, diagnostics
      and the sampled draws.
"""

import json
import logging
import os
import re
import sys
import warnings
from types import SimpleNamespace

import numpy as np
import pytest
from scipy.optimize import OptimizeResult

torch = pytest.importorskip("torch")
pytest.importorskip("gpytorch")

from gpytorch.constraints import Positive
from gpytorch.kernels import RBFKernel, ScaleKernel
from gpytorch.priors import GammaPrior

import bistar_gp.laplace_evidence as le
import bistar_gp.metrics_v2  # noqa: F401  registers pw_kl_vcal
from bistar_gp import generate_toy_data
from bistar_gp.aggregation_v3 import compute_log_marginal_likelihoods
from bistar_gp.bms_star import (
    METRICS, GPPosteriorSample, compute_G_matrix, extract_gp_predictives,
    run_bms_star, soft_transfer,
)
from bistar_gp.candidates import CandidateModel, CandidateResult, SinLinearModel, SinusoidalModel
from bistar_gp.config import PRIOR_CONFIGS, WITHDRAWN_CACHES, is_withdrawn_cache, load_hmc_samples
from bistar_gp.debias import _raw_parameter_map, decompose_model_hmc, decompose_model_mcmc
from bistar_gp.decompose import compute_cholesky
from bistar_gp.errors import EvaluationFailure
from bistar_gp.induced_prior import ModelParameterSpace, ParameterSpec, compute_induced_prior
from bistar_gp.model import build_model, build_toy_kernels

torch.set_default_dtype(torch.float64)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPERIMENTS = os.path.join(REPO, "experiments")
PRACTICE = os.path.join(EXPERIMENTS, "practice_EvansEtAL")

SITES = {
    "ls": "covar_module.kernels.0.base_kernel.lengthscale_prior",
    "os": "covar_module.kernels.0.outputscale_prior",
    "lv": "covar_module.kernels.1.variance_prior",
    "noise": "likelihood.noise_covar.noise_prior",
}


def _toy_samples(ls, os_, lv, noise):
    return {SITES["ls"]: np.asarray(ls, float), SITES["os"]: np.asarray(os_, float),
            SITES["lv"]: np.asarray(lv, float), SITES["noise"]: np.asarray(noise, float)}


@pytest.fixture
def toy():
    x = torch.linspace(-6, 6, 14)
    y = torch.sin(x) + 0.25 * x
    kers, names = build_toy_kernels()
    model, lik = build_model(x, y, kers, names)
    return model, lik, x, y, torch.linspace(-7, 7, 9)


@pytest.fixture
def registered():
    """Register throwaway metrics for one test and remove them afterwards."""
    names = []

    def register(name, fn):
        METRICS[name] = fn
        names.append(name)
        return name

    yield register
    for name in names:
        del METRICS[name]


def _single_kernel_builder():
    k = ScaleKernel(RBFKernel(lengthscale_constraint=Positive(),
                              lengthscale_prior=GammaPrior(2.0, 2.0)),
                    outputscale_constraint=Positive(),
                    outputscale_prior=GammaPrior(2.0, 1.0))
    return [k], ["se"]


# ── 2a-1 ────────────────────────────────────────────────────────────

def test_2a1_failed_divergences_raise_or_are_flagged(registered, caplog):
    def mse(mp, cp, mq, cq):
        return float(np.mean((np.asarray(mp) - np.asarray(mq)) ** 2))

    def always(mp, cp, mq, cq):
        raise ValueError("always failing metric")

    def candidate_b_fails(mp, cp, mq, cq):
        if float(mq[0]) == 99.0:
            raise np.linalg.LinAlgError("candidate cannot be evaluated")
        return mse(mp, cp, mq, cq)

    def two_cells_fail(mp, cp, mq, cq):
        # draw 1 fails for candidate a (mean 1), draw 2 for candidate c (mean 0)
        if (float(mp[0]), float(mq[0])) in {(7.0, 1.0), (1.0, 0.0)}:
            raise ValueError("one cell cannot be evaluated")
        return -5.0 + 0.01 * mse(mp, cp, mq, cq)          # negative-valued

    def draw_one_fails(mp, cp, mq, cq):
        if float(mp[0]) == 7.0:
            raise ValueError("one draw cannot be evaluated for any candidate")
        return mse(mp, cp, mq, cq)

    always_m = registered("_fix2a_always", always)
    cand_m = registered("_fix2a_candidate_b", candidate_b_fails)
    draw_m = registered("_fix2a_two_cells", two_cells_fail)
    row_m = registered("_fix2a_dead_row", draw_one_fails)

    gp = [GPPosteriorSample(mean=np.array([m, 0.0, 0.0]), cov=np.eye(3), hyperparameters={})
          for m in (0.0, 7.0, 1.0)]
    a = CandidateResult(name="a", mean=np.ones(3), cov=np.eye(3), noise_var=1.0, parameters={})
    b = CandidateResult(name="b", mean=np.array([99.0, 0.0, 0.0]), cov=np.eye(3),
                        noise_var=1.0, parameters={})
    c = CandidateResult(name="c", mean=np.zeros(3), cov=np.eye(3), noise_var=1.0, parameters={})

    with pytest.raises(EvaluationFailure, match="all 6 divergence evaluations"):
        compute_G_matrix(gp, [a, c], always_m)
    with pytest.raises(EvaluationFailure, match="all 6"):
        run_bms_star(gp, [a, c], metric_names=[always_m], taus=np.array([1.0]))
    with pytest.raises(EvaluationFailure, match=r"\['b'\] failed on every one of the 3 draws"):
        compute_G_matrix(gp, [a, b], cand_m)
    # a draw that fails for every candidate is a failure too (review round R4)
    with pytest.raises(EvaluationFailure, match=r"draw\(s\) \[1\] failed for every one of the 2"):
        compute_G_matrix(gp, [a, c], row_m)

    with caplog.at_level(logging.WARNING, logger="bistar_gp.bms_star"):
        G = compute_G_matrix(gp, [a, c], draw_m)
    failed = np.zeros(G.shape, dtype=bool)
    failed[1, 0] = failed[2, 1] = True
    max_finite = G[~failed].max()
    assert np.all(G[failed] == max_finite + 10.0 * (abs(max_finite) + 1.0))
    assert np.all(G[failed] > max_finite)                  # a failure never wins
    warned = [r.getMessage() for r in caplog.records if "evaluations failed" in r.getMessage()]
    assert len(warned) == 1 and "2 of 6" in warned[0] and "('a', 1), ('c', 1)" in warned[0]

    caplog.clear()                                         # repeated names keep their counts
    twin = CandidateResult(name="a", mean=np.zeros(3), cov=np.eye(3), noise_var=1.0, parameters={})
    with caplog.at_level(logging.WARNING, logger="bistar_gp.bms_star"):
        compute_G_matrix(gp, [a, twin], draw_m)
    assert any("('a', 1), ('a', 1)" in r.getMessage() for r in caplog.records)
    with pytest.raises(ValueError, match="empty table"):
        compute_G_matrix([], [a, c], draw_m)


# ── 2a-2 ────────────────────────────────────────────────────────────

def test_2a2_induced_prior_failed_points_carry_no_mass(registered):
    x = np.linspace(0.0, 1.0, 5)
    gp = [GPPosteriorSample(mean=np.zeros(5), cov=np.eye(5), hyperparameters={})]
    # The Codex C02 configuration: NaN predictions for a < 0, valid G ~ 2e6
    # elsewhere, so the former 1e6 sentinel outranked every valid point.
    space = ModelParameterSpace(
        model_name="Shift", param_specs=[ParameterSpec("a", (-1.0, 1.0), None)],
        predict_fn=lambda x_, p: np.full_like(x_, np.nan) if p["a"] < 0 else np.full_like(x_, 2000.0),
        noise_param="sigma")
    kw = dict(metric_name="pw_kl_vcal", tau=100.0, n_param_samples=20, seed=42)

    with pytest.raises(EvaluationFailure, match="every divergence evaluation failed"):
        compute_induced_prior(space, gp, x, **kw)

    res = compute_induced_prior(space, gp, x, strict=False, **kw)
    failed = res.param_samples[:, 0] < 0
    n_failed = int(failed.sum())
    assert 0 < n_failed < 20
    assert res.n_failed_points == n_failed
    assert np.all(res.weights[failed] == 0.0) and np.all(np.isnan(res.G_per_sample[failed]))
    assert res.weights[~failed].sum() == pytest.approx(1.0)
    # every valid point has the same G, so the ESS is exactly their number
    assert res.effective_sample_size == pytest.approx(20 - n_failed)

    def _raise(x_, p):
        raise ZeroDivisionError("always failing predictor")

    raising = ModelParameterSpace(model_name="Raise", param_specs=space.param_specs,
                                  predict_fn=_raise, noise_param="sigma")
    with pytest.raises(EvaluationFailure, match="always failing predictor"):
        compute_induced_prior(raising, gp, x, **kw)
    with pytest.raises(EvaluationFailure, match="every one of the 20 parameter points"):
        compute_induced_prior(raising, gp, x, strict=False, **kw)

    # metric failures of the classes compute_G_at_params handles follow the
    # same contract in both modes (review round R11)
    for exc_type in (FloatingPointError, RuntimeError):
        def failing_metric(mp, cp, mq, cq, exc_type=exc_type):
            if float(np.mean(mq)) < 0:
                raise exc_type("metric failed for a negative parameter")
            return float(np.mean((np.asarray(mp) - np.asarray(mq)) ** 2))
        name = registered(f"_fix2a_{exc_type.__name__}", failing_metric)
        shift = ModelParameterSpace(model_name="C", param_specs=[ParameterSpec("c", (-1.0, 1.0), None)],
                                    predict_fn=lambda x_, p: p["c"] + 0.0 * x_, noise_param="sigma")
        with pytest.raises(EvaluationFailure, match="every divergence evaluation failed"):
            compute_induced_prior(shift, gp, x, metric_name=name, n_param_samples=10, seed=0)
        res = compute_induced_prior(shift, gp, x, metric_name=name, n_param_samples=10, seed=0,
                                    strict=False)
        assert res.n_failed_points == int((res.param_samples[:, 0] < 0).sum()) > 0


# ── 2a-3 ────────────────────────────────────────────────────────────

def test_2a3_incomplete_or_ragged_sample_dicts_raise(toy, caplog):
    model, lik, x, y, x_eval = toy
    full = _toy_samples([0.7, 3.0, 1.2], [1.5, 0.4, 0.9], [0.05, 0.2, 0.1], [0.1, 0.3, 0.2])
    kw = dict(kernel_builder=build_toy_kernels, n_posterior_samples=3)

    def extract(samples, **extra):
        return extract_gp_predictives(model, lik, x, y, x_eval, samples, **kw, **extra)

    def decompose(samples, **extra):
        return decompose_model_hmc(model, lik, x, y, x_eval, samples, **kw, **extra)

    for site in full:
        partial = {k: v for k, v in full.items() if k != site}
        for route in (extract, decompose):
            with pytest.raises(ValueError, match=re.escape(site)):
                route(partial, rng=np.random.default_rng(0))

    ragged = dict(full, **{SITES["ls"]: full[SITES["ls"]][:2]})
    for route in (extract, decompose):
        messages = []
        for order in (list(ragged), list(reversed(ragged))):
            with pytest.raises(ValueError, match="one nonempty leading length") as err:
                route({k: ragged[k] for k in order}, rng=np.random.default_rng(0))
            messages.append(str(err.value))
        assert messages[0] == messages[1]

    a = extract(full, rng=np.random.default_rng(0))
    b = extract({k: full[k] for k in reversed(list(full))}, rng=np.random.default_rng(0))
    assert len(a) == len(b) == 3
    for pa, pb in zip(a, b):
        assert np.array_equal(pa.mean, pb.mean) and np.array_equal(pa.cov, pb.cov)

    # a noise-only dictionary names every missing kernel site (review round R14)
    noise_only = {SITES["noise"]: full[SITES["noise"]]}
    for route in (extract, decompose):
        with pytest.raises(ValueError, match="no kernel hyperparameter site") as err:
            route(noise_only, rng=np.random.default_rng(0))
        assert all(SITES[s] in str(err.value) for s in ("ls", "os", "lv"))

    # strict=False warns about a missing site and keeps going
    with caplog.at_level(logging.WARNING, logger="bistar_gp.bms_star"):
        kept = extract({k: v for k, v in full.items() if k != SITES["lv"]},
                       rng=np.random.default_rng(0), strict=False)
    assert len(kept) == 3
    assert any(SITES["lv"] in r.getMessage() for r in caplog.records)

    # the raw-parameter route checks lengths too
    raw = {n: np.full(3, 0.1) for n in _raw_parameter_map(model, lik)}
    raw[next(iter(raw))] = np.full(2, 0.1)
    with pytest.raises(ValueError, match="one nonempty leading length"):
        decompose_model_mcmc(model, lik, x, y, x_eval, raw, n_posterior_samples=3,
                             rng=np.random.default_rng(0))

    # legacy-era names cover the same sites (no false "missing")
    legacy = {k.replace("covar_module.kernels.", "kernel_components."): v
              for k, v in full.items() if k != SITES["noise"]}
    legacy["noise_covar.noise_prior"] = full[SITES["noise"]]
    assert len(extract(legacy, rng=np.random.default_rng(0))) == 3

    # a single-kernel model's sites, complete and with one removed
    single = {"covar_module.base_kernel.lengthscale_prior": np.array([0.4, 2.0]),
              "covar_module.outputscale_prior": np.array([0.5, 1.5]),
              SITES["noise"]: np.array([0.1, 0.2])}
    kers, names = _single_kernel_builder()
    smodel, slik = build_model(x, y, kers, names)
    sk = dict(kernel_builder=_single_kernel_builder, n_posterior_samples=2)
    assert len(extract_gp_predictives(smodel, slik, x, y, x_eval, single, **sk)) == 2
    with pytest.raises(ValueError, match="covar_module.outputscale_prior"):
        extract_gp_predictives(smodel, slik, x, y, x_eval,
                               {k: v for k, v in single.items() if "outputscale" not in k}, **sk)

    good = {k: float(v[0]) for k, v in full.items()}
    no_noise = {k: v for k, v in good.items() if k != SITES["noise"]}
    with pytest.raises(ValueError, match=re.escape(SITES["noise"])):
        compute_log_marginal_likelihoods(
            [GPPosteriorSample(mean=np.zeros(2), cov=np.eye(2), hyperparameters=no_noise)],
            x, y, kernel_builder=build_toy_kernels)
    lm = compute_log_marginal_likelihoods(
        [GPPosteriorSample(mean=np.zeros(2), cov=np.eye(2), hyperparameters=good)],
        x, y, kernel_builder=build_toy_kernels)
    assert np.isfinite(lm).all()


# ── 2a-4 ────────────────────────────────────────────────────────────

def test_2a4_tau_ladder_is_validated(registered):
    zero = registered("_fix2a_zero", lambda mp, cp, mq, cq: 0.0)
    space = ModelParameterSpace(
        model_name="Box", param_specs=[ParameterSpec("a", (-1.0, 1.0), None),
                                       ParameterSpec("b", (0.0, 2.0), None)],
        predict_fn=lambda x_, p: p["a"] * x_ + p["b"], noise_param="sigma")
    x = np.linspace(0.0, 1.0, 4)
    gp = SimpleNamespace(mean=np.zeros(4), cov=np.eye(4))
    for bad in [(), (0.3, np.nan), (0.3, -1.0), (0.0,)]:
        with pytest.raises(ValueError, match="tau_ladder"):
            le.is_log_Z_Mx(space, x, gp, [1.0], n_is=200, metric_name=zero, tau_ladder=bad)
    # constant integrand: the raw integral is the box volume (2 x 2)
    r = le.is_log_Z_Mx(space, x, gp, [1.0], n_is=20_000, seed=0, metric_name=zero)
    assert np.exp(r.log_Z[0]) == pytest.approx(4.0, rel=0.05)
    # a generator ladder is validated without being consumed
    g = le.is_log_Z_Mx(space, x, gp, [1.0], n_is=20_000, seed=0, metric_name=zero,
                       tau_ladder=(t for t in (0.03, 0.3, 3.0)))
    assert np.array_equal(g.log_Z, r.log_Z)


# ── 2a-5 ────────────────────────────────────────────────────────────

def test_2a5_sinusoid_fit_without_a_successful_restart_raises(monkeypatch):
    x = np.linspace(-10.0, 10.0, 20)
    y = np.sin(x) + 0.25 * x

    def always_raise(*a, **k):
        raise FloatingPointError("restart blew up")

    for cls in (SinusoidalModel, SinLinearModel):
        m = cls()
        monkeypatch.setattr(m, "_fit_mle", always_raise)
        with pytest.raises(EvaluationFailure, match="restart blew up"):
            m.fit(x, y)

        m2 = cls()
        seen = {"n": 0}

        def second_only(*a, **k):
            seen["n"] += 1
            if seen["n"] != 2:
                raise FloatingPointError("only the second restart runs")
            seen["out"] = CandidateModel._fit_mle(m2, *a, **k)
            return seen["out"]

        monkeypatch.setattr(m2, "_fit_mle", second_only)
        m2.fit(x, y)
        params = seen["out"][0]
        assert (m2.A, m2.omega, m2.phi) == (params[0], params[1], params[2])
        assert m2.sigma == np.exp(params[-1])


# ── 2a-6 ────────────────────────────────────────────────────────────

def test_2a6_noise_var_is_the_retained_draw_mean_and_order_free(toy, monkeypatch):
    model, lik, x, y, x_eval = toy
    noise = np.array([0.05, 0.1, 0.3])
    samples = _toy_samples([0.7, 3.0, 1.2], [1.5, 0.4, 0.9], [0.05, 0.2, 0.1], noise)
    perm = [2, 0, 1]
    permuted = {k: v[perm] for k, v in samples.items()}
    kw = dict(kernel_builder=build_toy_kernels, n_posterior_samples=3)
    a = decompose_model_hmc(model, lik, x, y, x_eval, samples, rng=np.random.default_rng(0), **kw)
    b = decompose_model_hmc(model, lik, x, y, x_eval, permuted, rng=np.random.default_rng(0), **kw)

    names = list(_raw_parameter_map(model, lik))
    draw_rng = np.random.default_rng(3)
    raw = {n: draw_rng.normal(size=3) for n in names}
    raw_perm = {n: v[perm] for n, v in raw.items()}
    c = decompose_model_mcmc(model, lik, x, y, x_eval, raw, n_posterior_samples=3,
                             rng=np.random.default_rng(0))
    d = decompose_model_mcmc(model, lik, x, y, x_eval, raw_perm, n_posterior_samples=3,
                             rng=np.random.default_rng(0))

    for r1, r2 in ((a, b), (c, d)):
        assert isinstance(r1.noise_var, float)
        assert r1.noise_var == pytest.approx(r2.noise_var, rel=1e-12)
        assert r1.noise_var == pytest.approx(np.mean(r1.noise_var_draws), rel=1e-12)
        assert np.allclose(np.sort(r1.noise_var_draws), np.sort(r2.noise_var_draws))
        assert np.allclose(r1.full_mean, r2.full_mean) and np.allclose(r1.full_std, r2.full_std)
        for n in r1.components:
            for field in ("mean", "std", "cov"):
                assert np.allclose(getattr(r1.components[n], field),
                                   getattr(r2.components[n], field), rtol=1e-10, atol=1e-12)
    assert a.noise_var == pytest.approx(noise.mean(), rel=1e-12)

    # a dropped draw contributes no noise value (non-strict route)
    import bistar_gp.debias as debias_mod
    real, calls = debias_mod.compute_cholesky, {"n": 0}

    def fail_second(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("simulated factorization failure")
        return real(*args, **kwargs)

    monkeypatch.setattr(debias_mod, "compute_cholesky", fail_second)
    e = decompose_model_hmc(model, lik, x, y, x_eval, samples, rng=np.random.default_rng(0),
                            strict=False, **kw)
    retained = sorted(set(range(3)) - {i for i, _ in e.dropped})
    assert len(e.dropped) == 1 and len(e.noise_var_draws) == 2
    assert e.noise_var == pytest.approx(noise[retained].mean(), rel=1e-12)


# ── 2a-7 ────────────────────────────────────────────────────────────

def test_2a7_withdrawn_caches_are_refused_on_every_route(tmp_path, monkeypatch):
    sys.path.insert(0, EXPERIMENTS)
    fmc = pytest.importorskip("fit_method_metric_comparison")
    # the D33/D34 classes: informative HMC (and hmc_laplace), vague and
    # gamma_relaxed HMC, every historical VI cache
    for name in ("runs/fit_method_metric_comparison/samples_hmc_td7.npz",
                 "runs/fit_method_metric_comparison/samples_hmc_laplace.npz",
                 "runs/prior_sensitivity/samples_informative_hmc_td7.npz",
                 "runs/prior_sensitivity/samples_vague_hmc_td7.npz",
                 "runs/prior_sensitivity/samples_gamma_relaxed_hmc_td7.npz",
                 "runs/fit_method_metric_comparison/samples_vi.npz",
                 "runs/prior_sensitivity/samples_toy_elicited_vi_td7.npz",
                 "runs/prior_sensitivity/samples_toy_elicited_hmc_td7.npz",
                 "runs/prior_sensitivity/samples_toy_elicited_hmc_td10.npz"):
        assert name in WITHDRAWN_CACHES
    assert len(WITHDRAWN_CACHES) == 17
    for kept in ("runs/prior_sensitivity/is_draws_toy_elicited_s0.npz",
                 "runs/fit_method_metric_comparison/samples_map.npz"):
        assert not is_withdrawn_cache(tmp_path / kept)

    x, y, _ = generate_toy_data()
    x_eval = torch.linspace(-11, 11, 6)
    pc = PRIOR_CONFIGS["informative"]
    for entry in WITHDRAWN_CACHES:
        path = tmp_path / (entry + "samples.npz" if entry.endswith("/") else entry)
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez(path, _fit_seconds=1.0, a=np.arange(3.0))
        with pytest.raises(RuntimeError, match="WITHDRAWN"):
            load_hmc_samples(str(path))
        with monkeypatch.context() as m:
            m.setattr(np, "load", lambda *a, **k: pytest.fail(f"np.load reached for {entry}"))
            with pytest.raises(RuntimeError, match="WITHDRAWN"):
                fmc.run_one_method("hmc", {}, pc, x, y, x_eval, [], 2, cache_path=str(path))

    # a cache that is not withdrawn still flows through the guarded route
    ok = tmp_path / "runs/other_study/samples_hmc.npz"
    ok.parent.mkdir(parents=True, exist_ok=True)
    np.savez(ok, _fit_seconds=2.5, **_toy_samples([1.0, 1.5], [0.8, 1.0], [0.05, 0.07], [0.2, 0.25]))
    cands = [CandidateResult(name=n, mean=np.full(6, s), cov=np.eye(6) * 0.25, noise_var=0.25,
                             parameters={}) for n, s in (("lo", 0.0), ("hi", 1.0))]
    out = fmc.run_one_method("hmc", {}, pc, x, y, x_eval, cands, 2, cache_path=str(ok))
    assert out["fit_seconds"] == 2.5 and out["n_draws"] == 2 and out["n_predictives"] == 2
    assert "_fit_seconds" not in out["hyperparameters"]


# ── 2a-8 ────────────────────────────────────────────────────────────

def test_2a8_ess_floor_warning_and_tie_aware_draw_wins(caplog, capsys, monkeypatch):
    def ess_warnings(G):
        caplog.clear()
        with caplog.at_level(logging.WARNING, logger="bistar_gp.bms_star"):
            r = soft_transfer(G, 1.0, ["a", "b"], metric_name="m")      # default floor
        return r, [rec.getMessage() for rec in caplog.records if "weight ESS" in rec.getMessage()]

    # one dominant draw: below min(100, 0.1 n) for 1000 draws and for 20 draws
    for n, floor in ((1000, "100"), (20, "2")):
        concentrated = np.full((n, 2), 50.0)
        concentrated[0] = 0.0
        r, warned = ess_warnings(concentrated)
        assert np.all(r.weight_ess < 2.0) and len(warned) == 1
        assert f"weight ESS below {floor} " in warned[0]
    # uniform weights never warn, however few the draws (review round R1)
    for n in (4, 20, 1000):
        r, warned = ess_warnings(np.zeros((n, 2)))
        assert np.all(r.weight_ess == pytest.approx(n)) and warned == []

    sys.path.insert(0, EXPERIMENTS)
    pss = pytest.importorskip("prior_sensitivity_study")
    x, y, _ = generate_toy_data()
    monkeypatch.setattr(pss, "extract_gp_predictives", lambda *a, **k: [
        GPPosteriorSample(mean=np.zeros(3), cov=np.eye(3), hyperparameters={})] * 4)
    twins = [CandidateResult(name=n, mean=np.ones(3), cov=np.eye(3) * 0.1, noise_var=0.1,
                             parameters={}) for n in ("first", "second")]
    ths = np.abs(np.random.default_rng(0).normal(size=(6, 4))) + 0.1
    capsys.readouterr()
    per_metric, _, _, _ = pss._sir_bms(pss.STUDY_CONFIGS["toy_elicited"], x, y,
                                       torch.linspace(-11, 11, 3), twins, ths, np.zeros(6), 4)
    printed = capsys.readouterr().out
    assert "first wins 2/4 draws" in printed and "second wins 2/4 draws" in printed
    for metric, rec in per_metric.items():
        assert rec["hard_win_fractions"] == [1.0, 0.0], metric      # legacy key kept as is
        assert rec["hard_win_credit"] == [0.5, 0.5], metric
        assert rec["attainment"] == [1.0, 1.0] and rec["tie_fraction"] == 1.0
        assert set(rec["weight_ess"]) == set(rec["posteriors"])
        assert all(len(v) == 2 for v in rec["weight_ess"].values())


# ── 2a-9 ────────────────────────────────────────────────────────────

def test_2a9_sweep_and_ladder_carry_records_and_jitter_escalation_logs(registered, caplog,
                                                                         monkeypatch):
    mse = registered("_fix2a_mse",
                     lambda mp, cp, mq, cq: float(np.mean((np.asarray(mp) - np.asarray(mq)) ** 2)))
    x = np.linspace(0.0, 4.0, 15)
    gp = SimpleNamespace(mean=0.5 * x - 0.3, cov=np.eye(15) * 0.05)
    specs = [ParameterSpec("a", (-2.0, 2.0), None), ParameterSpec("b", (-2.0, 2.0), None)]
    spaces = {"Lin": ModelParameterSpace("Lin", specs, lambda x_, p: p["a"] * x_ + p["b"]),
              "Quad": ModelParameterSpace("Quad", specs, lambda x_, p: p["a"] * x_ ** 2 + p["b"])}
    y = gp.mean + 0.05
    taus = [0.5, 2.0]

    for construction in ("baseline", "I", "II"):
        sweep = le.model_posterior_tau_sweep(spaces, x, y, x, gp, None, taus,
                                             construction=construction, metric_name=mse)
        names, post = sweep                                   # unpacks as before
        assert names == ["Lin", "Quad"] and post.shape == (2, 2)
        assert sweep.converged.shape == sweep.n_clipped.shape == sweep.n_starts_failed.shape == (2, 2)
        assert sweep.all_converged is True and not sweep.n_starts_failed.any()
    ladder = le.ablation_ladder_posteriors(spaces, x, y, x, gp, None, metric_name=mse, tau=1.0)
    assert set(ladder) == {"baseline", "I", "II"} and ladder.all_converged is True
    assert ladder.converged["II"] == {"Lin": True, "Quad": True}
    import copy, pickle                                       # the records survive copies
    for clone in (copy.deepcopy(sweep), pickle.loads(pickle.dumps(sweep))):
        assert type(clone) is type(sweep) and clone[0] == sweep[0]
        assert np.array_equal(clone[1], sweep[1]) and np.array_equal(clone.converged, sweep.converged)
        assert clone.all_converged is sweep.all_converged
    for clone in (copy.deepcopy(ladder), pickle.loads(pickle.dumps(ladder))):
        assert type(clone) is type(ladder) and clone == ladder
        assert clone.converged == ladder.converged and clone.all_converged is ladder.all_converged

    def not_converged(fun, x0, **k):
        return OptimizeResult(x=np.asarray(x0, float), success=False, status=2,
                              message="forced non-convergence", nit=0, nfev=1, fun=fun(x0))

    with monkeypatch.context() as m:
        m.setattr(le, "minimize", not_converged)
        sweep = le.model_posterior_tau_sweep(spaces, x, y, x, gp, None, taus,
                                             construction="II", metric_name=mse)
        assert sweep.all_converged is False and not sweep.converged.any()
        assert np.all(sweep.n_starts_failed == 1)
        ladder = le.ablation_ladder_posteriors(spaces, x, y, x, gp, None, metric_name=mse, tau=1.0)
        assert ladder.all_converged is False
        assert ladder.converged["baseline"]["Lin"] is False
        assert ladder.n_starts_failed["I"]["Quad"] == 2       # Z_Mx and p_ord each failed once

    with caplog.at_level(logging.WARNING, logger="bistar_gp.decompose"):
        L = compute_cholesky(torch.zeros(3, 3), 0.0, jitter=-5e-6)   # first retry succeeds
    assert torch.allclose(L @ L.T, 5e-6 * torch.eye(3))
    escalations = [r.getMessage() for r in caplog.records if "extra jitter" in r.getMessage()]
    assert escalations == [escalations[0]] and "1e-05" in escalations[0]


# ── 2a-10 ───────────────────────────────────────────────────────────

class _Diagnostics:
    def __init__(self, n):
        self.n = n

    def to_dict(self):
        return {"sampler": "stub", "n_draws": self.n}


def test_2a10_case_d_producer_fails_loud_and_records_provenance(tmp_path, monkeypatch):
    sys.path.insert(0, PRACTICE)
    saved_filters = warnings.filters[:]
    try:
        practice_run = pytest.importorskip("run")      # run.py silences warnings at import
    finally:
        warnings.filters[:] = saved_filters
    assert os.path.dirname(practice_run.__file__) == PRACTICE

    calls = []

    def fake_fit_hmc(model, likelihood, train_x, train_y, n_samples, n_warmup, verbose,
                     seed=None, return_diagnostics=False, fail_on=None):
        calls.append(seed)
        if fail_on is not None and len(calls) == fail_on:
            raise RuntimeError("sampler exploded")
        draws = {name: np.full(n_samples, float(closure(module).detach().reshape(-1)[0]))
                 for name, module, _prior, closure, _ in model.named_priors()}
        return draws, _Diagnostics(n_samples)

    curves = practice_run.generate_demo_data(n_subjects=1, seed=3)
    kw = dict(prior_configs=["practitioner", "moderate"], mode="hmc", verbose=False,
              n_hmc_samples=6, n_warmup=2, n_eval=8, n_posterior_samples=4,
              taus=np.array([0.5, 1.0]))

    monkeypatch.setattr(practice_run, "fit_hmc",
                        lambda *a, **k: fake_fit_hmc(*a, fail_on=2, **k))
    with pytest.raises(RuntimeError, match=r"\[moderate\]: HMC fit failed"):
        practice_run.run_all(curves, tmp_path / "strict", seed=7, strict=True, **kw)

    calls.clear()
    lenient = practice_run.run_all(curves, tmp_path / "lenient", seed=7, strict=False, **kw)
    assert set(lenient[0].bistar_probs) == {"practitioner"}
    assert "sampler exploded" in lenient[0].sampler_records["moderate"]["failed"]

    calls.clear()
    monkeypatch.setattr(practice_run, "fit_hmc", lambda *a, **k: fake_fit_hmc(*a, **k))
    practice_run.run_all(curves, tmp_path / "ok", seed=7, strict=True, **kw)
    assert calls == [7, 7]
    (path,) = (tmp_path / "ok").glob("synth_*.json")
    record = json.loads(path.read_text())
    assert record["seed"] == 7 and record["strict"] is True and record["candidate_failures"] == {}
    for cfg in ("practitioner", "moderate"):
        rec = record["sampler_records"][cfg]
        assert (rec["n_draws_requested"], rec["n_draws_returned"]) == (6, 6)
        assert (rec["n_predictives_requested"], rec["n_predictives_retained"]) == (4, 4)
        assert rec["n_predictives_dropped"] == 0 and rec["seed"] == 7
        assert rec["sampler_diagnostics"] == {"sampler": "stub", "n_draws": 6}
    with np.load(path.with_name(path.stem + "_samples.npz")) as z:
        assert "practitioner/likelihood.noise_covar.noise_prior" in z.files
        assert len(z["moderate/retained_indices"]) == 4

    # a failed extraction keeps the sampling record and draws (review round R12)
    def extraction_fails(*a, **k):
        raise RuntimeError("extractor exploded")

    with monkeypatch.context() as m:
        m.setattr(practice_run, "extract_gp_predictives", extraction_fails)
        res = practice_run.run_all(curves, tmp_path / "extract", seed=7, strict=False, **kw)
        rec = res[0].sampler_records["practitioner"]
        assert "predictive extraction failed" in rec["failed"] and rec["n_draws_returned"] == 6
        assert "sampler_diagnostics" in rec and "practitioner" in res[0].hmc_samples
        # MAP extraction goes through the same recorder (review round R13)
        m.setattr(practice_run, "extract_map_predictives", extraction_fails)
        map_kw = dict(kw, mode="map")
        res = practice_run.run_all(curves, tmp_path / "map", strict=False, **map_kw)
        assert "MAP predictive extraction failed" in res[0].sampler_records["practitioner"]["failed"]
        with pytest.raises(RuntimeError, match="MAP predictive extraction failed"):
            practice_run.run_all(curves, tmp_path / "map_strict", strict=True, **map_kw)

    # a BMS* scoring failure stops the strict run
    with monkeypatch.context() as m:
        m.setattr(practice_run, "run_bms_star", extraction_fails)
        with pytest.raises(RuntimeError, match=r"\[practitioner\]: BMS\* scoring failed"):
            practice_run.run_all(curves, tmp_path / "bms", seed=7, strict=True, **kw)

    # a candidate whose fit raises is never scored as a flat substitute (review round R3)
    real_build = practice_run.build_core_candidates
    broken_name = {}

    def build_with_a_broken_fit():
        cands = real_build()
        broken_name["name"] = cands[1].name

        def boom(*a, **k):
            raise FloatingPointError("overflow in the candidate fit")

        cands[1].fit = boom
        return cands

    monkeypatch.setattr(practice_run, "build_core_candidates", build_with_a_broken_fit)
    with pytest.raises(RuntimeError, match="failed to fit"):
        practice_run.run_all(curves, tmp_path / "cand_strict", seed=7, strict=True, **kw)
    res = practice_run.run_all(curves, tmp_path / "cand", seed=7, strict=False, **kw)
    name = broken_name["name"]
    assert "overflow in the candidate fit" in res[0].candidate_failures[name]
    assert name not in res[0].bic_log_ml and name not in res[0].fitted_params
    for per_metric in res[0].bistar_probs["practitioner"].values():
        for probs in per_metric.values():
            assert name not in probs
    (path,) = (tmp_path / "cand").glob("synth_*.json")
    assert name in json.loads(path.read_text())["candidate_failures"]


# ── optional items (run because the ten above are green) ────────────

def _recording_axes():
    """Axes stand-in that records fill_between and plot calls."""
    calls = {"bands": [], "lines": []}

    def fill_between(x, lo, hi, **k):
        calls["bands"].append((np.asarray(lo), np.asarray(hi), k.get("label")))

    def plot(x, yv, **k):
        calls["lines"].append((np.asarray(yv), k.get("label")))

    ax = SimpleNamespace(fill_between=fill_between, plot=plot, scatter=lambda *a, **k: None,
                         set_xlabel=lambda *a, **k: None, set_ylabel=lambda *a, **k: None,
                         set_title=lambda *a, **k: None, legend=lambda *a, **k: None)
    return ax, calls


def test_optional_a5_plots_mixture_intervals_and_labelled_traces(toy):
    from bistar_gp import viz
    from bistar_gp.debias import decompose_model

    model, lik, x, y, x_eval = toy
    res = decompose_model_hmc(model, lik, x, y, x_eval,
                              _toy_samples([0.7, 3.0], [1.5, 0.4], [0.05, 0.2], [0.1, 0.3]),
                              kernel_builder=build_toy_kernels, n_posterior_samples=2,
                              rng=np.random.default_rng(0))
    ax, calls = _recording_axes()
    viz.plot_full_prediction(res, ax=ax, n_samples=5)
    (lo, hi, label), = calls["bands"]
    want_lo, want_hi = res.full.central_interval(0.95)
    assert label == "95% central interval"
    assert np.array_equal(lo, want_lo) and np.array_equal(hi, want_hi)
    traces = [(t, lab) for t, lab in calls["lines"] if lab != "Predicted mean"]
    assert len(traces) == 2 and traces[0][1] == "per-draw conditional means"
    assert all(np.array_equal(t, m) for (t, _), m in zip(traces, res.full.conditional_means))

    ax, calls = _recording_axes()
    name = list(res.components)[0]
    viz.plot_component(res, name, ax=ax)
    (lo, hi, label), = calls["bands"]
    assert label == "95% central interval"
    assert np.array_equal(lo, res.components[name].central_interval(0.95)[0])
    assert calls["lines"][0][1] == "per-draw conditional means"

    # MAP path: joint draws from the full posterior, not sums of separately
    # drawn component samples (which lose the cross-covariance); the
    # correlation check rejects a diagonal-only sampler (review round R8)
    res_map = decompose_model(model, lik, x, y, x_eval)
    ax, calls = _recording_axes()
    viz.plot_full_prediction(res_map, ax=ax, n_samples=4000, seed=1)
    draws = np.array([t for t, lab in calls["lines"] if lab != "Predicted mean"])
    assert draws.shape == (4000, len(x_eval))
    cov = res_map.full.cov
    sd = np.sqrt(np.diag(cov))
    keep = sd > 1e-3 * sd.max()
    assert np.allclose(draws.var(axis=0), np.diag(cov), rtol=0.15, atol=1e-6)
    want = (cov / np.outer(sd, sd))[np.ix_(keep, keep)]
    got = np.corrcoef(draws.T)[np.ix_(keep, keep)]
    assert np.abs(want - np.eye(keep.sum())).max() > 0.3      # the fixture is correlated
    assert np.abs(got - want).max() < 0.06

    # a high-scale posterior whose covariance is semidefinite to roundoff
    # (minimum eigenvalue about -5e-14 of the largest) still plots (R9)
    xt = torch.linspace(-10, 10, 20)
    big, big_lik = build_model(xt, torch.sin(xt) + 0.25 * xt, *build_toy_kernels())
    big.kernel_components[0].outputscale = 1e6
    big.kernel_components[1].variance = 1e6
    res_big = decompose_model(big, big_lik, xt, torch.sin(xt) + 0.25 * xt, torch.linspace(-10, 10, 100))
    assert np.linalg.eigvalsh(0.5 * (res_big.full.cov + res_big.full.cov.T)).min() < 0
    ax, calls = _recording_axes()
    viz.plot_full_prediction(res_big, ax=ax, n_samples=3)
    assert len(calls["lines"]) == 4

    # a result rebuilt without provenance (the frozen D58 driver's positional
    # contract) renders exactly as before fix pass 2a (review round R7)
    from bistar_gp.debias import ComponentResult, DecompositionResult
    rebuilt = DecompositionResult(
        res.x_test, res.x_train, res.y_train,
        {n: ComponentResult(name=n, mean=c.mean, std=c.std, cov=np.diag(c.std ** 2), samples=c.samples)
         for n, c in res.components.items()},
        res.full_mean, res.full_std, res.noise_var)
    ax, calls = _recording_axes()
    viz.plot_full_prediction(rebuilt, ax=ax, n_samples=5)
    (lo, hi, label), = calls["bands"]
    assert label == "95% CI" and np.array_equal(lo, res.full_mean - 2 * res.full_std)
    summed = [t for t, lab in calls["lines"] if lab is None]
    assert len(summed) == 2 and np.allclose(summed[0], sum(c.samples[0] for c in res.components.values()))
    ax, calls = _recording_axes()
    viz.plot_component(rebuilt, name, ax=ax)
    assert calls["bands"][0][2] == "±2 SE"
    assert [lab for _, lab in calls["lines"]] == [None, None, f"{name} mean"]


def test_optional_a7_rank_aggregation_is_permutation_symmetric():
    from bistar_gp.aggregation_v3 import robust_rank

    tied = robust_rank(np.zeros((3, 2)), ["a", "b"])
    assert list(tied.posteriors) == [0.5, 0.5]                # was 0.731 / 0.269 by column order
    G = np.array([[0.0, 0.0, 1.0], [2.0, 0.0, 0.0], [1.0, 1.0, 1.0], [0.5, 0.2, 0.9]])
    ref = robust_rank(G, ["a", "b", "c"])
    for perm in ([2, 0, 1], [1, 0, 2]):
        out = robust_rank(G[:, perm], [["a", "b", "c"][j] for j in perm])
        assert np.allclose(out.posteriors, ref.posteriors[perm], rtol=0, atol=1e-15)
        assert np.array_equal(out.summary_values, ref.summary_values[perm])
    # integer input keeps its average ranks (review round R10)
    ints = robust_rank(np.array([[0, 0, 1]]), ["a", "b", "c"])
    floats = robust_rank(np.array([[0.0, 0.0, 1.0]]), ["a", "b", "c"])
    assert np.array_equal(ints.summary_values, [1.5, 1.5, 3.0])
    assert np.array_equal(ints.posteriors, floats.posteriors)
