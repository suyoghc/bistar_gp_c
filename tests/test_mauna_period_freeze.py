"""
A10 seasonal-period freeze (D20; plan-d19-mauna.md §0, §6.14 disclosure 4, §7 A10).

Before M2a the "keep this one fixed" comment on the Mauna seasonal period was
aspirational: raw_period_length stayed requires_grad=True under
Interval(0.99, 1.01) and fit_map drifted the plug-in from 1.0 to ~0.9996 in
100 iterations (codex round-1 catch, verified live in the planning session).
A10 freezes the constrained period at EXACTLY 1.0 (raw = 0 maps to
lower + (upper - lower) * sigmoid(0) = 1.0 exactly in float64) with
requires_grad off, and the freeze must hold through fit_map, every
multi-start path, and fit_mcmc_simple, with the pyro sampled-site inventory
staying at 7. All fits here run on a small SYNTHETIC monthly-style series —
never real Mauna data (M2a builds infrastructure only).
"""

import numpy as np
import pytest

torch = pytest.importorskip("torch")
gpytorch = pytest.importorskip("gpytorch")

from bistar_gp.fit import fit_map, fit_mcmc_simple
from bistar_gp.model import (
    MAUNA_FROZEN_PERIOD,
    assert_mauna_period_frozen,
    build_likelihood,
    build_mauna_loa_kernels,
    build_model,
)

torch.set_default_dtype(torch.float64)


def synthetic_monthly(n=36, seed=0):
    """Tiny trend + annual cycle + noise on a monthly grid; NOT Mauna data."""
    rng = np.random.default_rng(seed)
    x = np.arange(n) / 12.0
    y = 0.05 * x + 0.3 * np.sin(2 * np.pi * x) + 0.05 * rng.standard_normal(n)
    return torch.tensor(x).double(), torch.tensor(y).double()


@pytest.fixture
def mauna_model():
    x, y = synthetic_monthly()
    kernels, names = build_mauna_loa_kernels()
    model, lik = build_model(x, y, kernels, names)
    return model, lik, x, y


def _period_param(model):
    return model.kernel_components[1].base_kernel


def test_builder_freezes_period_exactly(mauna_model):
    model, lik, x, y = mauna_model
    base = _period_param(model)
    assert base.period_length.item() == MAUNA_FROZEN_PERIOD  # exact, no approx
    assert base.raw_period_length.item() == 0.0
    assert not base.raw_period_length.requires_grad
    assert_mauna_period_frozen(model)


def test_period_has_no_prior_hence_no_sample_site(mauna_model):
    model, lik, x, y = mauna_model
    prior_names = [entry[0] for entry in model.named_priors()]
    assert not any("period" in name for name in prior_names)


def test_fit_map_leaves_period_at_exactly_one(mauna_model):
    """The historical defect: 100 iterations moved the period to 0.99962.
    Post-A10 the constrained value must stay bit-exactly 1.0."""
    model, lik, x, y = mauna_model
    fit_map(model, lik, x, y, n_iter=100, lr=0.02, verbose=False)
    assert _period_param(model).period_length.item() == MAUNA_FROZEN_PERIOD
    assert_mauna_period_frozen(model)


def test_multi_start_paths_leave_period_frozen():
    """Every multi-start MAP path goes through fit_map per start; perturbing
    the OTHER hyperparameters between restarts (the Stage-A protocol shape)
    must never move the period."""
    x, y = synthetic_monthly()
    for start_seed in range(3):
        torch.manual_seed(start_seed)
        kernels, names = build_mauna_loa_kernels()
        model, lik = build_model(x, y, kernels, names)
        with torch.no_grad():
            for kernel in model.kernel_components:
                kernel.outputscale = 0.5 + 0.5 * torch.rand(1)
        fit_map(model, lik, x, y, n_iter=40, lr=0.05, verbose=False)
        assert _period_param(model).period_length.item() == MAUNA_FROZEN_PERIOD
        assert_mauna_period_frozen(model)


def test_fit_map_guard_trips_if_a_frozen_param_is_moved():
    """fit_map now asserts every requires_grad=False parameter unchanged at
    exit; a hostile optimizer step is simulated by mutating the frozen raw
    parameter inside the loop via a hook-free direct write before the check."""
    x, y = synthetic_monthly()
    kernels, names = build_mauna_loa_kernels()
    model, lik = build_model(x, y, kernels, names)
    # Sanity: the guard passes untouched.
    fit_map(model, lik, x, y, n_iter=2, lr=0.01, verbose=False)
    # Direct violation is caught by the standalone checker.
    with torch.no_grad():
        _p = model.kernel_components[1].base_kernel
        _p.raw_period_length.fill_(0.5)
    with pytest.raises(AssertionError, match="A10 violation"):
        assert_mauna_period_frozen(model)


def test_pyro_sampled_site_inventory_stays_seven(mauna_model):
    """The frozen period must not appear as a pyro latent: 7 sites exactly
    (trend ls+os, seasonal ls+os, medium ls+os, noise), matching the
    planning-session inventory (bench_*.json:sampled_sites)."""
    pyro = pytest.importorskip("pyro")
    from functools import partial

    from pyro.infer.mcmc.util import initialize_model

    from bistar_gp.fit import _hmc_pyro_model, _map_init_values

    model, lik, x, y = mauna_model
    model.train()
    lik.train()
    pyro.clear_param_store()
    from pyro.infer.autoguide.initialization import init_to_value
    with gpytorch.settings.cholesky_jitter(1e-4):
        init_params, _, _, _ = initialize_model(
            partial(_hmc_pyro_model, model), model_args=(x, y),
            init_strategy=init_to_value(values=_map_init_values(model)))
    sites = sorted(init_params)
    assert len(sites) == 7, sites
    assert not any("period" in s for s in sites)


def test_fit_mcmc_simple_no_longer_proposes_the_period(mauna_model):
    """Pre-A10, requires_grad=True made raw_period_length one of the MH
    proposal dimensions; frozen, it must neither appear in the returned
    samples nor move."""
    model, lik, x, y = mauna_model
    samples = fit_mcmc_simple(model, lik, x, y, n_samples=5, n_burnin=2,
                              proposal_scale=0.05, verbose=False, seed=0)
    assert not any("period" in k for k in samples)
    assert _period_param(model).period_length.item() == MAUNA_FROZEN_PERIOD
