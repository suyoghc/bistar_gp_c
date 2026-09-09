"""
FIX-1 (2026-09 review): site assignment and draw integrity.

Pins: single-kernel site names are selected and applied; predictives follow
the supplied kernel draws for single-kernel models (they were identical
before the fix); multi-kernel and legacy names keep their assignments; an
unrecognized site raises under strict mode; a sample dict without kernel
sites raises; a forced per-draw failure cannot yield a full-length result
under strict mode and is counted under non-strict mode; decompose_model_mcmc
matches raw parameters by name; _sir_bms refuses a short predictive list.
"""

import os
import sys
from types import SimpleNamespace

import numpy as np
import pytest

torch = pytest.importorskip("torch")
gpytorch = pytest.importorskip("gpytorch")

from gpytorch.constraints import Positive
from gpytorch.kernels import LinearKernel, RBFKernel, ScaleKernel
from gpytorch.priors import GammaPrior

import bistar_gp.decompose as decompose_mod
from bistar_gp.bms_star import PredictiveList, extract_gp_predictives
from bistar_gp.debias import _raw_parameter_map, decompose_model_mcmc
from bistar_gp.model import (
    apply_hp_value, build_likelihood, build_model, build_toy_kernels,
    select_hmc_sites,
)

torch.set_default_dtype(torch.float64)
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _single_kernel_builder():
    se = ScaleKernel(
        RBFKernel(lengthscale_constraint=Positive(),
                  lengthscale_prior=GammaPrior(4.0, 12.0)),
        outputscale_constraint=Positive(),
        outputscale_prior=GammaPrior(4.0, 4.0),
    )
    return [se], ["smooth"]


@pytest.fixture
def single_kernel_model():
    x = torch.linspace(0, 1, 10)
    y = 1.0 / (1.0 + 5.0 * x)
    kernels, names = _single_kernel_builder()
    model, lik = build_model(x, y, kernels, names, build_likelihood())
    return model, lik, x, y


@pytest.fixture
def toy_model():
    x = torch.linspace(0, 6, 30)
    y = torch.sin(x) + 0.25 * x
    kers, names = build_toy_kernels()
    model, lik = build_model(x, y, kers, names)
    return model, lik, x, y


SINGLE_SITES = ["covar_module.outputscale_prior",
                "covar_module.base_kernel.lengthscale_prior",
                "likelihood.noise_covar.noise_prior"]


def test_single_kernel_sites_are_selected_and_applied(single_kernel_model):
    model, lik, _, _ = single_kernel_model
    emitted = [name for name, *_ in model.named_priors()]
    assert set(emitted) == set(SINGLE_SITES)
    selected = select_hmc_sites(emitted)
    assert set(selected) == set(SINGLE_SITES)
    assert apply_hp_value(model, lik, "covar_module.base_kernel.lengthscale_prior", 0.37)
    assert apply_hp_value(model, lik, "covar_module.outputscale_prior", 2.5)
    assert apply_hp_value(model, lik, "likelihood.noise_covar.noise_prior", 0.11)
    assert float(model.kernel_components[0].base_kernel.lengthscale) == pytest.approx(0.37)
    assert float(model.kernel_components[0].outputscale) == pytest.approx(2.5)
    assert float(lik.noise) == pytest.approx(0.11)


def test_single_kernel_predictives_follow_the_supplied_draws(single_kernel_model):
    """The Codex F4 probe: two draws with lengthscales 0.05 and 2.0 gave
    byte-identical predictives before the fix."""
    model, lik, x, y = single_kernel_model
    samples = {
        "covar_module.base_kernel.lengthscale_prior": np.array([0.05, 2.0]),
        "covar_module.outputscale_prior": np.array([0.2, 4.0]),
        "likelihood.noise_covar.noise_prior": np.array([0.1, 0.1]),
    }
    draws = extract_gp_predictives(model, lik, x, y, torch.linspace(0, 1, 5), samples,
                                   kernel_builder=_single_kernel_builder,
                                   n_posterior_samples=2, rng=np.random.default_rng(0))
    assert isinstance(draws, PredictiveList)
    assert len(draws) == 2 and draws.n_dropped == 0
    assert sorted(draws.retained_indices) == [0, 1]
    assert not np.allclose(draws[0].mean, draws[1].mean)
    assert not np.allclose(draws[0].cov, draws[1].cov)
    for d in draws:
        assert "covar_module.base_kernel.lengthscale_prior" in d.hyperparameters
        assert "covar_module.outputscale_prior" in d.hyperparameters


def test_multi_kernel_and_legacy_names_keep_their_assignments(toy_model):
    model, lik, _, _ = toy_model
    for prefix in ("covar_module.kernels.", "kernel_components."):
        assert apply_hp_value(model, lik, f"{prefix}0.base_kernel.lengthscale_prior", 2.5)
        assert apply_hp_value(model, lik, f"{prefix}0.outputscale_prior", 1.75)
        assert apply_hp_value(model, lik, f"{prefix}1.variance_prior", 0.6)
        assert float(model.kernel_components[0].base_kernel.lengthscale) == pytest.approx(2.5)
        assert float(model.kernel_components[1].variance) == pytest.approx(0.6)
    current = ["covar_module.kernels.0.base_kernel.lengthscale_prior",
               "covar_module.kernels.0.outputscale_prior",
               "covar_module.kernels.1.variance_prior",
               "likelihood.noise_covar.noise_prior"]
    assert select_hmc_sites(current) == current
    legacy = current + ["kernel_components.0.base_kernel.lengthscale_prior",
                        "noise_covar.noise_prior"]
    selected = select_hmc_sites(legacy)
    assert selected == current[:3] + ["noise_covar.noise_prior"]


def test_bare_covar_module_name_is_rejected_on_a_multi_kernel_model(toy_model):
    model, lik, _, _ = toy_model
    assert not apply_hp_value(model, lik, "covar_module.outputscale_prior", 1.0)
    assert not apply_hp_value(model, lik, "mean_module.constant_prior", 1.0)


def _toy_samples(n=2):
    return {
        "covar_module.kernels.0.base_kernel.lengthscale_prior": np.linspace(0.3, 5.0, n),
        "covar_module.kernels.0.outputscale_prior": np.linspace(2.0, 0.1, n),
        "covar_module.kernels.1.variance_prior": np.full(n, 0.5),
        "likelihood.noise_covar.noise_prior": np.full(n, 0.1),
    }


def test_unrecognized_site_raises_under_strict_and_warns_otherwise(toy_model, caplog):
    model, lik, x, y = toy_model
    samples = _toy_samples()
    samples["covar_module.kernels.0.base_kernel.alpha_prior"] = np.array([0.5, 50.0])
    x_eval = torch.linspace(0, 6, 7)
    with pytest.raises(ValueError, match="alpha_prior"):
        extract_gp_predictives(model, lik, x, y, x_eval, samples,
                               kernel_builder=build_toy_kernels, n_posterior_samples=2)
    import logging
    with caplog.at_level(logging.WARNING, logger="bistar_gp.bms_star"):
        draws = extract_gp_predictives(model, lik, x, y, x_eval, samples,
                                       kernel_builder=build_toy_kernels,
                                       n_posterior_samples=2, strict=False)
    assert len(draws) == 2
    assert any("alpha_prior" in rec.message for rec in caplog.records)
    # the unapplied value is not recorded as provenance
    assert all("alpha_prior" not in d.hyperparameters for d in draws)


def test_sample_dict_without_kernel_sites_raises(toy_model):
    model, lik, x, y = toy_model
    noise_only = {"likelihood.noise_covar.noise_prior": np.array([0.1, 0.2])}
    with pytest.raises(ValueError, match="no kernel hyperparameter site"):
        extract_gp_predictives(model, lik, x, y, torch.linspace(0, 6, 5), noise_only,
                               kernel_builder=build_toy_kernels, n_posterior_samples=2)


def test_forced_draw_failure_cannot_yield_a_full_result(toy_model, monkeypatch):
    model, lik, x, y = toy_model
    samples = _toy_samples(3)
    calls = {"n": 0}
    real = decompose_mod.compute_cholesky

    def failing(K, noise_var, jitter=1e-6):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("simulated factorization failure")
        return real(K, noise_var, jitter)

    monkeypatch.setattr(decompose_mod, "compute_cholesky", failing)
    x_eval = torch.linspace(0, 6, 5)
    with pytest.raises(RuntimeError, match="simulated factorization failure"):
        extract_gp_predictives(model, lik, x, y, x_eval, samples,
                               kernel_builder=build_toy_kernels, n_posterior_samples=3,
                               rng=np.random.default_rng(0))
    calls["n"] = 0
    draws = extract_gp_predictives(model, lik, x, y, x_eval, samples,
                                   kernel_builder=build_toy_kernels, n_posterior_samples=3,
                                   rng=np.random.default_rng(0), strict=False)
    assert len(draws) == 2 and draws.n_dropped == 1
    assert len(draws.attempted_indices) == 3
    assert draws.dropped[0][0] == draws.attempted_indices[1]


def test_decompose_model_mcmc_matches_raw_parameters_by_name(toy_model):
    model, lik, x, y = toy_model
    names = list(_raw_parameter_map(model, lik))
    rng = np.random.default_rng(1)
    raw = {n: rng.normal(size=3) for n in names}
    x_test = torch.linspace(-1, 7, 9)
    ref = decompose_model_mcmc(model, lik, x, y, x_test, raw, n_posterior_samples=3,
                               rng=np.random.default_rng(0))
    permuted = {n: raw[n] for n in reversed(names)}
    out = decompose_model_mcmc(model, lik, x, y, x_test, permuted, n_posterior_samples=3,
                               rng=np.random.default_rng(0))
    assert np.allclose(out.full_mean, ref.full_mean)
    for n in ref.components:
        assert np.allclose(out.components[n].mean, ref.components[n].mean)
        assert np.allclose(out.components[n].std, ref.components[n].std)
    with pytest.raises(KeyError, match="unknown keys"):
        decompose_model_mcmc(model, lik, x, y, x_test, {**raw, "nonexistent.raw_x": raw[names[0]]},
                             n_posterior_samples=3, rng=np.random.default_rng(0))
    missing = {n: raw[n] for n in names[1:]}
    with pytest.raises(KeyError, match="parameters without a key"):
        decompose_model_mcmc(model, lik, x, y, x_test, missing, n_posterior_samples=3,
                             rng=np.random.default_rng(0))


def test_sir_bms_refuses_a_short_predictive_list(monkeypatch):
    sys.path.insert(0, os.path.join(REPO, "experiments"))
    pss = pytest.importorskip("prior_sensitivity_study")
    from bistar_gp import generate_toy_data
    x, y, _ = generate_toy_data()
    monkeypatch.setattr(pss, "extract_gp_predictives",
                        lambda *a, **k: [SimpleNamespace(mean=np.zeros(3), cov=np.eye(3))] * 2)
    ths = np.abs(np.random.default_rng(0).normal(size=(5, 4))) + 0.1
    lml = np.zeros(5)
    with pytest.raises(RuntimeError, match="retained of 3"):
        pss._sir_bms(pss.STUDY_CONFIGS["toy_elicited"], x, y, torch.linspace(-11, 11, 6),
                     [], ths, lml, 3)
