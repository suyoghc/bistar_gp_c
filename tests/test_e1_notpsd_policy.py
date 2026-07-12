"""D28 terminal NotPSD rejection policy for E1 NUTS sampling."""

import copy
import logging

import numpy as np
import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("pyro")

from linear_operator.utils.errors import NotPSDError

import bistar_gp.e1_potential as e1_module
from bistar_gp.e1_potential import (
    E1_NOTPSD_FAIL_RATE,
    E1Potential,
    _NotPSDRejectingPotential,
    build_e1_potential,
    fit_hmc_e1,
)
from bistar_gp.fit import fit_map
from bistar_gp.model import build_model, build_toy_kernels
from bistar_gp.sampler_diagnostics import PotentialEvalTracker

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


def test_known_warmup_and_sampling_injections_are_split_and_fail(
        stable_map_setup, monkeypatch, caplog):
    model, likelihood, x, y = _copy_setup(stable_map_setup)
    original_potential = E1Potential.potential_fn
    original_hook = PotentialEvalTracker.hook
    inject_next = False
    injection_stages = []

    def injected(self, state):
        nonlocal inject_next
        if inject_next:
            inject_next = False
            raise NotPSDError("planted D28 test failure")
        return original_potential(self, state)

    def scheduled_hook(self, kernel, params, stage, i):
        nonlocal inject_next
        original_hook(self, kernel, params, stage, i)
        key = (str(stage), int(i))
        if key in {("Warmup", 1), ("Sample", 0)}:
            injection_stages.append(key)
            inject_next = True

    monkeypatch.setattr(E1Potential, "potential_fn", injected)
    monkeypatch.setattr(PotentialEvalTracker, "hook", scheduled_hook)
    with caplog.at_level(logging.WARNING, logger="bistar_gp.e1_potential"):
        with pytest.raises(RuntimeError, match="D29.*rate") as caught:
            fit_hmc_e1(
                model, likelihood, x, y, n_samples=6, n_warmup=6,
                verbose=False, seed=0, max_tree_depth=3,
                return_diagnostics=False)

    assert injection_stages == [("Warmup", 1), ("Sample", 0)]
    diagnostics = caught.value.diagnostics
    assert diagnostics.notpsd_rejections == 2
    assert diagnostics.notpsd_rejections_warmup == 1
    assert diagnostics.notpsd_rejections_per_draw == ((0, 1, 0, 0, 0, 0),)
    assert diagnostics.notpsd_post_warmup_total == 1
    assert diagnostics.notpsd_post_warmup_rate >= E1_NOTPSD_FAIL_RATE
    assert f"{diagnostics.notpsd_post_warmup_rate:.12g}" in str(caught.value)
    assert any(
        record.levelno == logging.WARNING
        and "D29" in record.message
        and "[1]" in record.message
        for record in caplog.records)


def test_warmup_only_rejection_reports_info_without_gate(
        stable_map_setup, monkeypatch, caplog):
    model, likelihood, x, y = _copy_setup(stable_map_setup)
    original_potential = E1Potential.potential_fn
    original_hook = PotentialEvalTracker.hook
    inject_next = False

    def injected(self, state):
        nonlocal inject_next
        if inject_next:
            inject_next = False
            raise NotPSDError("planted warmup-only failure")
        return original_potential(self, state)

    def scheduled_hook(self, kernel, params, stage, i):
        nonlocal inject_next
        original_hook(self, kernel, params, stage, i)
        if (str(stage), int(i)) == ("Warmup", 1):
            inject_next = True

    monkeypatch.setattr(E1Potential, "potential_fn", injected)
    monkeypatch.setattr(PotentialEvalTracker, "hook", scheduled_hook)
    with caplog.at_level(logging.INFO, logger="bistar_gp.e1_potential"):
        samples, diagnostics = fit_hmc_e1(
            model, likelihood, x, y, n_samples=6, n_warmup=6,
            verbose=False, seed=0, max_tree_depth=3,
            return_diagnostics=True)

    assert all(np.isfinite(draws).all() for draws in samples.values())
    assert diagnostics.notpsd_rejections == 1
    assert diagnostics.notpsd_rejections_warmup == 1
    assert diagnostics.notpsd_rejections_per_draw == ((0, 0, 0, 0, 0, 0),)
    assert diagnostics.notpsd_post_warmup_rate == 0.0
    assert any(record.levelno == logging.INFO and "D29" in record.message
               for record in caplog.records)
    assert not any(record.levelno >= logging.WARNING and "D29" in record.message
                   for record in caplog.records)


def test_any_post_warmup_rejection_warns_below_failure_gate(
        stable_map_setup, monkeypatch, caplog):
    model, likelihood, x, y = _copy_setup(stable_map_setup)
    original_potential = E1Potential.potential_fn
    original_hook = PotentialEvalTracker.hook
    inject_next = False

    def injected(self, state):
        nonlocal inject_next
        if inject_next:
            inject_next = False
            raise NotPSDError("planted warning-only failure")
        return original_potential(self, state)

    def scheduled_hook(self, kernel, params, stage, i):
        nonlocal inject_next
        original_hook(self, kernel, params, stage, i)
        if (str(stage), int(i)) == ("Sample", 0):
            inject_next = True

    monkeypatch.setattr(E1Potential, "potential_fn", injected)
    monkeypatch.setattr(PotentialEvalTracker, "hook", scheduled_hook)
    monkeypatch.setattr(e1_module, "E1_NOTPSD_FAIL_RATE", 1.0)
    with caplog.at_level(logging.WARNING, logger="bistar_gp.e1_potential"):
        samples, diagnostics = fit_hmc_e1(
            model, likelihood, x, y, n_samples=6, n_warmup=6,
            verbose=False, seed=0, max_tree_depth=3,
            return_diagnostics=True)

    assert all(np.isfinite(draws).all() for draws in samples.values())
    assert diagnostics.notpsd_rejections_per_draw == ((0, 1, 0, 0, 0, 0),)
    assert diagnostics.notpsd_post_warmup_rate < 1.0
    assert any("D29" in record.message and "[1]" in record.message
               for record in caplog.records)


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
    assert diagnostics.notpsd_rejections_warmup == 0
    assert diagnostics.notpsd_rejections_per_draw == ((0, 0, 0, 0, 0, 0),)


def test_explicit_init_values_round_trip_and_take_priority(stable_map_setup):
    model, likelihood, x, y = _copy_setup(stable_map_setup)
    values = {
        name: closure(module).detach().clone() * 1.1
        for name, module, _prior, closure, _setting in model.named_priors()
    }

    e1 = build_e1_potential(
        model, likelihood, x, y, init_to_map=True, init_values=values)

    assert set(e1.init_params) == set(values)
    for site, value in values.items():
        expected = e1.transforms[site](value)
        assert torch.equal(e1.init_params[site], expected)
        assert torch.equal(e1.transforms[site].inv(e1.init_params[site]), value)


def test_explicit_init_values_reject_mismatched_site_set(stable_map_setup):
    model, likelihood, x, y = _copy_setup(stable_map_setup)
    values = {
        name: closure(module).detach().clone()
        for name, module, _prior, closure, _setting in model.named_priors()
    }
    values.pop(next(iter(values)))
    values["unexpected.site"] = torch.tensor(1.0)

    with pytest.raises(ValueError, match="site set mismatch"):
        build_e1_potential(
            model, likelihood, x, y, init_to_map=False, init_values=values)


def _constrained_prior_values(model, scale=1.0):
    return {
        name: closure(module).detach().clone() * scale
        for name, module, _prior, closure, _setting in model.named_priors()
    }


def _degenerate_prior_values(model):
    values = _constrained_prior_values(model)
    for name, value in values.items():
        if "outputscale" in name or "variance" in name:
            values[name] = torch.full_like(value, 1e20)
        elif "noise" in name:
            values[name] = torch.full_like(value, 1e-40)
    return values


def test_preflight_start_state_passes_healthy_near_map(stable_map_setup):
    model, likelihood, x, y = _copy_setup(stable_map_setup)
    values = _constrained_prior_values(model, scale=1.001)

    ok, reason, report = e1_module.preflight_start_state(
        model, likelihood, x, y, values)

    assert ok is True
    assert reason is None
    assert report == {
        "site_set": True,
        "round_trip": True,
        "potential_finite": True,
        "gradient_finite": True,
    }


def test_preflight_start_state_rejects_site_set_mismatch(stable_map_setup):
    model, likelihood, x, y = _copy_setup(stable_map_setup)
    values = _constrained_prior_values(model)
    values["ghost.site"] = torch.tensor(1.0)

    ok, reason, report = e1_module.preflight_start_state(
        model, likelihood, x, y, values)

    assert ok is False
    assert reason == "site_set"
    assert report == {"site_set": False}


def test_preflight_start_state_rejects_degenerate_state(stable_map_setup):
    model, likelihood, x, y = _copy_setup(stable_map_setup)

    ok, reason, report = e1_module.preflight_start_state(
        model, likelihood, x, y, _degenerate_prior_values(model))

    assert ok is False
    assert reason in {"potential_finite", "gradient_finite", "round_trip"}
    assert reason != "site_set"
    assert report["site_set"] is True


def test_select_start_state_returns_first_healthy_candidate(stable_map_setup):
    model, likelihood, x, y = _copy_setup(stable_map_setup)
    first = _constrained_prior_values(model)
    second = _degenerate_prior_values(model)

    index, chosen, reports = e1_module.select_start_state(
        model, likelihood, x, y, [first, second])

    assert index == 0
    assert chosen is first
    assert len(reports) == 1
    assert all(reports[0].values())


def test_select_start_state_skips_degenerate_candidate(stable_map_setup):
    model, likelihood, x, y = _copy_setup(stable_map_setup)
    first = _degenerate_prior_values(model)
    second = _constrained_prior_values(model)

    index, chosen, reports = e1_module.select_start_state(
        model, likelihood, x, y, [first, second])

    assert index == 1
    assert len(reports) == 2
    assert not all(reports[0].values())
    assert all(reports[1].values())
    assert set(chosen) == set(second)
    for site in second:
        assert torch.equal(chosen[site], second[site])


def test_select_start_state_raises_when_every_candidate_fails(
        stable_map_setup):
    model, likelihood, x, y = _copy_setup(stable_map_setup)
    mismatched = _constrained_prior_values(model)
    mismatched["ghost.site"] = torch.tensor(1.0)
    degenerate = _degenerate_prior_values(model)
    _, degenerate_reason, _ = e1_module.preflight_start_state(
        model, likelihood, x, y, degenerate)

    with pytest.raises(RuntimeError) as caught:
        e1_module.select_start_state(
            model, likelihood, x, y, [mismatched, degenerate])

    message = str(caught.value)
    assert "2 candidates" in message
    assert "candidate 0: site_set" in message
    assert f"candidate 1: {degenerate_reason}" in message
