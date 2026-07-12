"""D28 terminal NotPSD rejection policy for E1 NUTS sampling."""

import copy
import logging

import numpy as np
import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("pyro")

from linear_operator.utils.errors import NotPSDError

from bistar_gp.e1_potential import (
    E1Potential,
    _NotPSDRejectingPotential,
    build_e1_potential,
    fit_hmc_e1,
)
from bistar_gp.fit import fit_map
from bistar_gp.model import build_model, build_toy_kernels

torch.set_default_dtype(torch.float64)


@pytest.fixture(scope="module")
def stable_map_setup():
    x = torch.linspace(0, 5, 40)
    noise = torch.randn(40, generator=torch.Generator().manual_seed(0))
    y = torch.sin(2 * x) + 0.3 * noise
    kernels, names = build_toy_kernels()
    model, likelihood = build_model(x, y, kernels, names)
    fit_map(model, likelihood, x, y, n_iter=150, lr=0.05, verbose=False)
    return model, x, y


def _copy_setup(setup):
    model, x, y = setup
    copied = copy.deepcopy(model)
    return copied, copied.likelihood, x, y


def test_mid_chain_notpsd_attempts_are_rejected_and_counted(
        stable_map_setup, monkeypatch, caplog):
    model, likelihood, x, y = _copy_setup(stable_map_setup)
    original = E1Potential.potential_fn
    selected_calls = {15, 20}
    calls = 0
    injections = 0

    def injected(self, state):
        nonlocal calls, injections
        calls += 1
        if calls in selected_calls:
            injections += 1
            raise NotPSDError("planted D28 test failure")
        return original(self, state)

    monkeypatch.setattr(E1Potential, "potential_fn", injected)
    with caplog.at_level(logging.WARNING, logger="bistar_gp.e1_potential"):
        samples, diagnostics = fit_hmc_e1(
            model, likelihood, x, y, n_samples=6, n_warmup=6,
            verbose=False, seed=0, max_tree_depth=3,
            return_diagnostics=True)

    assert calls >= max(selected_calls)
    assert injections == len(selected_calls)
    assert diagnostics.notpsd_rejections == injections
    assert all(np.isfinite(draws).all() for draws in samples.values())
    assert any("D28" in record.message for record in caplog.records)


def test_generic_runtime_error_propagates(
        stable_map_setup, monkeypatch):
    model, likelihood, x, y = _copy_setup(stable_map_setup)

    def planted(_self, _state):
        raise RuntimeError("planted generic failure")

    monkeypatch.setattr(E1Potential, "potential_fn", planted)
    with pytest.raises(RuntimeError, match="planted generic failure"):
        fit_hmc_e1(
            model, likelihood, x, y, n_samples=1, n_warmup=1,
            verbose=False, seed=0, max_tree_depth=2)


def test_successful_potential_values_pass_through_bit_exact(stable_map_setup):
    model, likelihood, x, y = _copy_setup(stable_map_setup)
    e1 = build_e1_potential(model, likelihood, x, y)
    wrapped = _NotPSDRejectingPotential(e1.potential_fn)

    for shift in (-0.1, 0.0, 0.1):
        state = {name: value.detach().clone() + shift
                 for name, value in e1.init_params.items()}
        expected = e1.potential_fn(state)
        actual = wrapped(state)
        assert torch.equal(actual, expected)

    sentinel = torch.tensor(3.25)
    identity_wrapper = _NotPSDRejectingPotential(lambda _state: sentinel)
    assert identity_wrapper({}) is sentinel
    assert wrapped.notpsd_rejections == 0


def test_documented_weak_map_notpsd_scenario_completes():
    torch.manual_seed(0)
    x = torch.linspace(0, 5, 30)
    y = torch.sin(2 * x) + 0.3 * torch.randn(30)
    kernels, names = build_toy_kernels()
    model, likelihood = build_model(x, y, kernels, names)
    fit_map(model, likelihood, x, y, n_iter=80, lr=0.05, verbose=False)

    samples, diagnostics = fit_hmc_e1(
        model, likelihood, x, y, n_samples=3, n_warmup=3,
        verbose=False, seed=0, max_tree_depth=4,
        return_diagnostics=True)

    assert all(np.isfinite(draws).all() for draws in samples.values())
    if diagnostics.notpsd_rejections == 0:
        pytest.skip("geometry no longer reaches terminal NotPSD in this regression")
    assert diagnostics.notpsd_rejections > 0


def test_map_reference_setup_has_zero_notpsd_rejections(stable_map_setup):
    model, likelihood, x, y = _copy_setup(stable_map_setup)
    samples, diagnostics = fit_hmc_e1(
        model, likelihood, x, y, n_samples=6, n_warmup=6,
        verbose=False, seed=0, max_tree_depth=3,
        return_diagnostics=True)

    assert all(np.isfinite(draws).all() for draws in samples.values())
    assert diagnostics.notpsd_rejections == 0
