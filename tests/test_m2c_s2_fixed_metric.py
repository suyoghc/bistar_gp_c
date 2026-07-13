"""Hermetic S2 fixed-metric gates and mocked sampler wiring.

The only model evaluations use the existing synthetic E1 fixtures.  NUTS and
MCMC are replaced by deterministic mocks; this file launches no real chain.
M1 nine-site coverage remains UNVERIFIED pending the PR-C builder.
"""

import numpy as np
import pytest

torch = pytest.importorskip("torch")
pyro = pytest.importorskip("pyro")

from tests.test_e1_potential import _built

import bistar_gp.s2_fixed_metric as s2
from bistar_gp.e1_potential import (
    _NotPSDRejectingPotential,
    build_e1_potential,
)
from bistar_gp.m2c_freeze_s2s3 import (
    S2_DIRECTIONAL_TOL,
    S2_EIG_FLOOR,
    S2_ORACLE_TOL,
    S2_SKEW_TOL,
    S2_STEP_STABILITY_TOL,
    S2_WHITENING_TOL,
)
from bistar_gp.sampler_diagnostics import PotentialEvalTracker


torch.set_default_dtype(torch.float64)


@pytest.fixture(scope="module")
def synthetic_e1():
    # Reuse the frozen seed-0 data and MAP(150, lr=0.05) fixture verbatim.
    fixtures = {}
    for structure in ("toy", "mauna_structure"):
        model, likelihood, x, y = _built(structure)
        fixtures[structure] = build_e1_potential(model, likelihood, x, y)
    return fixtures


def test_central_fd_hessian_runs_on_both_frozen_structures(synthetic_e1):
    for structure, e1 in synthetic_e1.items():
        center = s2.flatten_e1_state(e1.init_params, e1.sites)

        def potential(vector):
            return e1.potential_fn(
                s2.unflatten_e1_state(vector, e1.init_params, e1.sites))

        columns, hessian = s2.central_fd_hessian(potential, center)
        expected = 4 if structure == "toy" else 7
        assert columns.shape == hessian.shape == (expected, expected)
        assert torch.isfinite(columns).all()
        assert torch.isfinite(hessian).all()
        torch.testing.assert_close(hessian, hessian.T, rtol=0.0, atol=0.0)


def test_toy_passes_every_s2_mass_convention_gate(synthetic_e1):
    e1 = synthetic_e1["toy"]
    result = s2.compute_s2_fixed_metric(e1)

    assert result.skew_error <= S2_SKEW_TOL
    assert result.step_stability_error <= S2_STEP_STABILITY_TOL
    assert max(result.directional_errors.values()) <= S2_DIRECTIONAL_TOL
    assert max(result.whitening_errors) <= S2_WHITENING_TOL
    assert float(result.eigenvalues.min()) >= S2_EIG_FLOOR
    assert result.n_clipped == 0
    torch.testing.assert_close(
        result.mass_matrix, result.hessian, rtol=0.0, atol=0.0)
    torch.testing.assert_close(
        result.inverse_mass_matrix,
        result.whitener @ result.whitener.T,
        rtol=0.0, atol=0.0,
    )


def test_mauna_structure_stops_instead_of_falling_back(synthetic_e1):
    e1 = synthetic_e1["mauna_structure"]
    with pytest.raises(
            s2.S2GateError,
            match=r"S2 STOP:.*SPD requirement.*no identity fallback"):
        s2.compute_s2_fixed_metric(e1)


def test_seedless_quadratic_oracle_recovers_position_mass_not_inverse():
    expected = torch.diag(torch.tensor([1.0, 4.0, 9.0]))

    def potential(vector):
        return 0.5 * vector @ expected @ vector

    result = s2.compute_fixed_metric(potential, torch.zeros(3))
    relative = float(torch.linalg.matrix_norm(
        result.mass_matrix - expected, ord="fro")) / max(
            1.0, float(torch.linalg.matrix_norm(expected, ord="fro")))
    assert relative <= S2_ORACLE_TOL
    torch.testing.assert_close(
        result.eigenvalues, torch.tensor([1.0, 4.0, 9.0]),
        rtol=0.0, atol=S2_ORACLE_TOL,
    )
    assert result.n_clipped == 0
    assert max(result.whitening_errors) <= S2_WHITENING_TOL
    assert not torch.allclose(result.mass_matrix, result.inverse_mass_matrix)


@pytest.mark.parametrize("smallest", (-1.0, 0.5e-6))
def test_non_spd_or_near_singular_hessian_stops_without_fallback(smallest):
    curvature = torch.diag(torch.tensor([1.0, 4.0, smallest]))

    with pytest.raises(s2.S2GateError, match=r"n_clipped=1.*no identity fallback"):
        s2.compute_fixed_metric(
            lambda vector: 0.5 * vector @ curvature @ vector,
            torch.zeros(3),
        )


class _ExpInverseTransform:
    def inv(self, value):
        return torch.exp(value)


class _FakeE1:
    def __init__(self):
        self.sites = ("alpha", "beta")
        self.init_params = {
            "alpha": torch.tensor(0.2),
            "beta": torch.tensor(-0.4),
        }
        self.transforms = {site: _ExpInverseTransform() for site in self.sites}
        self._model = torch.nn.Linear(1, 1)
        self._likelihood = torch.nn.Linear(1, 1)
        self.received_states = []

    def potential_fn(self, state):
        self.received_states.append({
            site: value.detach().clone() for site, value in state.items()
        })
        return sum((value ** 2).sum() for value in state.values())


def _install_mock_sampler(monkeypatch, draws, captured):
    import pyro.infer.mcmc

    class MockNUTS:
        def __init__(self, **kwargs):
            captured["nuts"] = kwargs
            self.potential_fn = kwargs["potential_fn"]
            self.step_size = kwargs["step_size"]

    class MockMCMC:
        num_chains = 1

        def __init__(self, kernel, **kwargs):
            self.kernel = kernel
            self.kwargs = kwargs
            captured["mcmc"] = kwargs

        def run(self):
            params = self.kwargs["initial_params"]
            self.kernel.potential_fn(params)
            self.kwargs["hook_fn"](self.kernel, params, "Warmup", 0)
            for index, draw in enumerate(draws):
                params = {s2.S2_COORDINATE: draw}
                self.kernel.potential_fn(params)
                self.kwargs["hook_fn"](self.kernel, params, "Sample", index)

        def get_samples(self):
            return {s2.S2_COORDINATE: torch.stack(draws)}

        def diagnostics(self):
            return {
                "divergences": {"chain 0": []},
                "acceptance rate": {"chain 0": 1.0},
            }

        def summary(self):
            raise AssertionError("verbose=False must not request a summary")

    monkeypatch.setattr(pyro.infer.mcmc, "NUTS", MockNUTS)
    monkeypatch.setattr(pyro.infer.mcmc, "MCMC", MockMCMC)


def test_fixed_metric_route_uses_whitened_z_and_shared_safety_core(monkeypatch):
    fake = _FakeE1()
    whitener = torch.tensor([[2.0, 0.25], [0.0, 0.5]])
    identity = torch.eye(2)
    metric = s2.S2FixedMetricResult(
        raw_hessian=identity,
        hessian=identity,
        eigenvalues=torch.ones(2),
        n_clipped=0,
        mass_matrix=identity,
        inverse_mass_matrix=whitener @ whitener.T,
        whitener=whitener,
    )
    monkeypatch.setattr(s2, "build_e1_potential", lambda *args, **kwargs: fake)
    monkeypatch.setattr(s2, "compute_s2_fixed_metric", lambda e1: metric)

    draws = (torch.tensor([0.0, 0.0]), torch.tensor([1.0, -1.0]))
    captured = {}
    _install_mock_sampler(monkeypatch, draws, captured)

    samples, diagnostics = s2.fit_hmc_e1_fixed_metric(
        fake._model, fake._likelihood, torch.zeros(1), torch.zeros(1),
        n_samples=2, n_warmup=1, verbose=False, seed=0,
        return_diagnostics=True,
    )

    assert captured["nuts"]["adapt_mass_matrix"] is False
    assert captured["nuts"]["adapt_step_size"] is True
    assert captured["nuts"]["jit_compile"] is False
    torch.testing.assert_close(
        captured["mcmc"]["initial_params"][s2.S2_COORDINATE],
        torch.zeros(2), rtol=0.0, atol=0.0,
    )

    tracker = captured["nuts"]["potential_fn"]
    assert isinstance(tracker, PotentialEvalTracker)
    assert isinstance(tracker._model_fn, _NotPSDRejectingPotential)
    tracker({s2.S2_COORDINATE: torch.tensor([0.5, -0.25])})
    expected_u = torch.tensor([0.2, -0.4]) + whitener @ torch.tensor([0.5, -0.25])
    actual_u = torch.stack([
        fake.received_states[-1]["alpha"],
        fake.received_states[-1]["beta"],
    ])
    torch.testing.assert_close(actual_u, expected_u)

    flat_u = torch.tensor([0.2, -0.4]) + torch.stack(draws) @ whitener.T
    np.testing.assert_allclose(samples["alpha"], torch.exp(flat_u[:, 0]).numpy())
    np.testing.assert_allclose(samples["beta"], torch.exp(flat_u[:, 1]).numpy())
    assert diagnostics.sampler == "nuts_e1_s2"
    assert diagnostics.notpsd_rejections == 0
    assert diagnostics.notpsd_rejections_warmup == 0
    assert diagnostics.notpsd_rejections_per_draw == ((0, 0),)
