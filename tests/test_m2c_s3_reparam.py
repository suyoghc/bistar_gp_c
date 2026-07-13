"""Hermetic S3 maps/equivalence battery and mocked sampler wiring."""

import math
from types import SimpleNamespace

import numpy as np
import pytest

torch = pytest.importorskip("torch")
pyro = pytest.importorskip("pyro")

from tests.test_e1_potential import _built

import bistar_gp.s3_reparam as s3
from bistar_gp.e1_potential import (
    _NotPSDRejectingPotential,
    build_e1_potential,
)
from bistar_gp.m2c_freeze_s2s3 import (
    S3_N_STATES,
    S3_ROUNDTRIP_TOL,
    S3_SLOGDET_TOL,
)
from bistar_gp.sampler_diagnostics import PotentialEvalTracker


torch.set_default_dtype(torch.float64)


@pytest.mark.parametrize("z", (
    torch.tensor([0.1, -0.2, 0.3, 0.4, -0.5, 0.6, -0.7]),
    torch.tensor([8.0, -8.0, 2.0, 8.0, 15.0, -15.0, -15.0]),
))
def test_seven_coordinate_maps_and_both_logdet_identities(z):
    u = s3.z_to_u(z)
    theta = s3.z_to_theta(z)
    torch.testing.assert_close(
        s3.u_to_z(u), z, rtol=0.0, atol=S3_ROUNDTRIP_TOL)
    torch.testing.assert_close(
        s3.theta_to_z(theta), z, rtol=0.0, atol=S3_ROUNDTRIP_TOL)
    torch.testing.assert_close(
        s3.z_to_u(s3.u_to_z(u)), u, rtol=0.0, atol=S3_ROUNDTRIP_TOL)
    torch.testing.assert_close(
        s3.z_to_theta(s3.theta_to_z(theta)), theta,
        rtol=0.0, atol=S3_ROUNDTRIP_TOL)

    u_auto = s3.autodiff_log_abs_det(s3.z_to_u, z)
    theta_auto = s3.autodiff_log_abs_det(s3.z_to_theta, z)
    assert abs(float(s3.log_abs_det_u_from_z(z) - u_auto)) <= S3_SLOGDET_TOL
    assert abs(float(s3.log_abs_det_theta_from_z(z) - theta_auto)) <= S3_SLOGDET_TOL
    assert float(s3.log_abs_det_u_from_z(z)) == 0.0


@pytest.fixture(scope="module")
def mauna_e1():
    # Existing Mauna-structure-only seed-0, n=120, MAP(150, lr=0.05) fixture.
    model, likelihood, x, y = _built("mauna_structure")
    return build_e1_potential(model, likelihood, x, y)


def test_m0_roles_and_33_state_equivalence_battery(mauna_e1):
    roles = s3.resolve_m0_site_roles(mauna_e1)
    assert set(roles.semantic_sites) == set(mauna_e1.sites)
    states = s3.frozen_s3_states(mauna_e1, roles)
    assert len(states) == S3_N_STATES
    assert len({label for label, _state in states}) == S3_N_STATES

    result = s3.validate_s3_equivalence(mauna_e1)
    assert result.executed_labels == tuple(label for label, _state in states)
    assert result.max_u_slogdet_error <= S3_SLOGDET_TOL
    assert result.max_theta_slogdet_error <= S3_SLOGDET_TOL
    assert result.max_u_roundtrip_error <= S3_ROUNDTRIP_TOL
    assert result.max_theta_roundtrip_error <= S3_ROUNDTRIP_TOL
    # Target-to-output bridge: the manual exp(z_to_u) constrained map matches
    # E1's own transforms bit-for-bit for M0 (all seven sites are positive, so
    # e1.transforms[.].inv IS exp).  Recorded as EXACTLY zero, not merely small.
    assert result.max_constrained_bridge_error == 0.0


def test_constrained_bridge_gate_catches_a_wrong_manual_map(mauna_e1, monkeypatch):
    """A manual constrained map disagreeing with E1's transforms must STOP.

    The target is evaluated in E1's u coordinates, so the reported draws now go
    through ``e1.constrain(z_to_e1_u(.))``.  The frozen closed-form map
    ``z_to_e1_theta = exp(z_to_u)`` is retained but must AGREE with that path at
    every battery state.  Corrupt the manual map on one site and confirm the
    bridge gate — not some incidental round-trip check — fires.
    """
    real_map = s3.z_to_e1_theta
    corrupt_site = mauna_e1.sites[0]

    def wrong_map(z, e1, roles=None):
        theta = dict(real_map(z, e1, roles))
        # Additive, so |manual - e1.constrain| = 1.0 >> 1e-10 at every state,
        # regardless of the site's constrained magnitude.
        theta[corrupt_site] = theta[corrupt_site] + 1.0
        return theta

    monkeypatch.setattr(s3, "z_to_e1_theta", wrong_map)
    with pytest.raises(s3.S3GateError, match=r"constrained bridge.*E1 constrain"):
        s3.validate_s3_equivalence(mauna_e1)


def test_four_site_toy_is_outside_frozen_s3_definition():
    model, likelihood, x, y = _built("toy")
    e1 = build_e1_potential(model, likelihood, x, y)
    with pytest.raises(s3.S3GateError, match="outside the frozen S3 definition"):
        s3.resolve_m0_site_roles(e1)


def test_nine_site_m1_is_reported_outside_definition_not_as_coverage():
    # M1's builder is PR-C work.  This inventory-only sentinel verifies that
    # nine-site coverage remains explicitly UNVERIFIED rather than claimed.
    e1 = SimpleNamespace(sites=tuple(f"site-{index}" for index in range(9)))
    with pytest.raises(s3.S3GateError, match="outside the frozen S3 definition"):
        s3.resolve_m0_site_roles(e1)


class _FakeE1:
    def __init__(self, roles, z_map):
        self.sites = ("tl", "to", "sl", "so", "ml", "mo", "noise")
        semantic_u = s3.z_to_u(z_map)
        semantic = dict(zip(s3.S3_SEMANTIC_SITE_ROLES, semantic_u))
        by_site = {
            getattr(roles, role): value for role, value in semantic.items()
        }
        self.init_params = {site: by_site[site].clone() for site in self.sites}
        self._model = torch.nn.Linear(1, 1)
        self._likelihood = torch.nn.Linear(1, 1)
        self.received_states = []

    def potential_fn(self, state):
        self.received_states.append({
            site: value.detach().clone() for site, value in state.items()
        })
        return sum((value ** 2).sum() for value in state.values())

    def constrain(self, u):
        # E1's positive sites use biject_to(positive) = ExpTransform.
        return {site: torch.exp(u[site]) for site in self.sites}


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
                params = {s3.S3_COORDINATE: draw}
                self.kernel.potential_fn(params)
                self.kwargs["hook_fn"](self.kernel, params, "Sample", index)

        def get_samples(self):
            return {s3.S3_COORDINATE: torch.stack(draws)}

        def diagnostics(self):
            return {
                "divergences": {"chain 0": []},
                "acceptance rate": {"chain 0": 1.0},
            }

        def summary(self):
            raise AssertionError("verbose=False must not request a summary")

    monkeypatch.setattr(pyro.infer.mcmc, "NUTS", MockNUTS)
    monkeypatch.setattr(pyro.infer.mcmc, "MCMC", MockMCMC)


def test_reparam_route_uses_z_map_composition_mapping_and_shared_core(monkeypatch):
    roles = s3.S3SiteRoles(
        trend_lengthscale="tl", seasonal_lengthscale="sl",
        medium_lengthscale="ml", trend_outputscale="to",
        seasonal_outputscale="so", medium_outputscale="mo", noise="noise",
    )
    z_map = torch.tensor([0.1, -0.2, 0.3, 0.4, -0.5, 0.6, -0.7])
    fake = _FakeE1(roles, z_map)
    validated = []
    monkeypatch.setattr(s3, "build_e1_potential", lambda *args, **kwargs: fake)
    monkeypatch.setattr(s3, "resolve_m0_site_roles", lambda e1: roles)
    monkeypatch.setattr(
        s3, "validate_s3_equivalence", lambda e1: validated.append(e1))

    draws = (z_map, z_map + torch.tensor([0.2, -0.1, 0.05, 0.3, 0.4, -0.2, 0.1]))
    captured = {}
    _install_mock_sampler(monkeypatch, draws, captured)

    samples, diagnostics = s3.fit_hmc_e1_reparam(
        fake._model, fake._likelihood, torch.zeros(1), torch.zeros(1),
        n_samples=2, n_warmup=1, verbose=False, seed=0,
        return_diagnostics=True,
    )

    assert validated == [fake]
    # Rev-5 §5.2 freezes no S3 mass override: preserve S1f/Pyro adaptation.
    assert captured["nuts"]["adapt_mass_matrix"] is True
    assert captured["nuts"]["adapt_step_size"] is True
    torch.testing.assert_close(
        captured["mcmc"]["initial_params"][s3.S3_COORDINATE],
        z_map, rtol=0.0, atol=S3_ROUNDTRIP_TOL,
    )

    tracker = captured["nuts"]["potential_fn"]
    assert isinstance(tracker, PotentialEvalTracker)
    assert isinstance(tracker._model_fn, _NotPSDRejectingPotential)
    probe = z_map + 0.25
    tracker({s3.S3_COORDINATE: probe})
    expected_u = s3.z_to_u(probe)
    actual_semantic_u = torch.stack([
        fake.received_states[-1][getattr(roles, role)]
        for role in s3.S3_SEMANTIC_SITE_ROLES
    ])
    torch.testing.assert_close(actual_semantic_u, expected_u)

    theta_draws = s3.z_to_theta(torch.stack(draws))
    for index, role in enumerate(s3.S3_SEMANTIC_SITE_ROLES):
        np.testing.assert_allclose(
            samples[getattr(roles, role)], theta_draws[:, index].numpy())
    assert diagnostics.sampler == "nuts_e1_s3"
    assert diagnostics.notpsd_rejections == 0
    assert diagnostics.notpsd_rejections_per_draw == ((0, 0),)


def test_semantic_coordinate_map_is_independently_anchored():
    """Anchor z->u/theta to rev-5 §5.2(a) with hard-coded golden values.

    The 33-state equivalence battery only checks self-consistency (expected and
    actual values both flow through ``z_to_u``/``z_to_theta``), so a bijective
    relabeling of the seven coordinates — e.g. swapping trend and seasonal
    lengthscales together with a matching inverse — passes every equivalence,
    round-trip, Jacobian, density, and gradient gate.  These distinct-valued
    golden vectors pin the exact coordinate->hyperparameter assignment, so any
    permutation or formula drift fails HERE rather than shipping green.
    """
    # Distinct across all seven coordinates so ANY permutation is detectable.
    z = torch.tensor([0.5, 1.5, 2.5, 1.0, math.log(2.0), math.log(3.0), 0.25])
    # Hand-derived from §5.2(a).  D = 1 + e^{a_t} + e^{a_s} = 1 + 2 + 3 = 6, so
    # the outputscale slots are 1 - log 3, 1 - log 2, 1 - log 6 and noise = s+r.
    golden_u = torch.tensor([
        0.5, 1.5, 2.5,
        -0.0986122886681098,   # trend outputscale  = s + a_t - logD = 1 - log 3
        0.3068528194400547,    # seasonal outputscale = s + a_s - logD = 1 - log 2
        -0.7917594692280550,   # medium outputscale = s - logD       = 1 - log 6
        1.25,                  # noise              = s + r
    ])
    torch.testing.assert_close(s3.z_to_u(z), golden_u, rtol=0.0, atol=1e-12)
    torch.testing.assert_close(
        s3.z_to_theta(z), torch.exp(golden_u), rtol=0.0, atol=1e-12)
    # Explicit positional pins: a trend<->seasonal swap would put 1.5 at slot 0.
    assert float(s3.z_to_u(z)[0]) == 0.5
    assert float(s3.z_to_u(z)[1]) == 1.5
    assert float(s3.z_to_u(z)[6]) == 1.25
    # Inverses recover z exactly from the golden images.
    torch.testing.assert_close(s3.u_to_z(golden_u), z, rtol=0.0, atol=1e-12)
    torch.testing.assert_close(
        s3.theta_to_z(torch.exp(golden_u)), z, rtol=0.0, atol=1e-12)
    # Pin the frozen slot->role and z-name order (with the structural role->site
    # resolution this anchors z[0] -> trend-lengthscale SITE end to end).
    assert s3.S3_SEMANTIC_SITE_ROLES == (
        "trend_lengthscale", "seasonal_lengthscale", "medium_lengthscale",
        "trend_outputscale", "seasonal_outputscale", "medium_outputscale",
        "noise")
    assert s3.S3_Z_NAMES == (
        "ell_trend", "ell_seasonal", "ell_medium", "log_total_scale",
        "alr_trend", "alr_seasonal", "log_noise_ratio")


def test_role_resolution_is_anchored_to_independent_model_structure(mauna_e1):
    """Cross-check role->site resolution against the model's kernel structure.

    Independently identify each M0 raw parameter from the model's component
    inventory and E1 site metadata, then require the resolved roles to agree.
    This makes the semantic assignment non-self-certifying at the role level,
    complementing the golden coordinate-map anchor.
    """
    roles = s3.resolve_m0_site_roles(mauna_e1)
    model = mauna_e1._model
    components = dict(zip(model.component_names, model.kernel_components))
    name_by_id = {id(p): n for n, p in model.named_parameters()}
    param_by_site = {
        site: mauna_e1._site_map[site][1] for site in mauna_e1.sites}
    site_by_param = {param: site for site, param in param_by_site.items()}

    def site_of(parameter):
        return site_by_param[name_by_id[id(parameter)]]

    assert roles.trend_lengthscale == site_of(
        components["trend"].base_kernel.raw_lengthscale)
    assert roles.trend_outputscale == site_of(
        components["trend"].raw_outputscale)
    assert roles.seasonal_lengthscale == site_of(
        components["seasonal"].base_kernel.raw_lengthscale)
    assert roles.seasonal_outputscale == site_of(
        components["seasonal"].raw_outputscale)
    assert roles.medium_lengthscale == site_of(
        components["medium_term"].base_kernel.raw_lengthscale)
    assert roles.medium_outputscale == site_of(
        components["medium_term"].raw_outputscale)
    assert roles.noise == site_of(
        mauna_e1._likelihood.noise_covar.raw_noise)


def test_frozen_boundary_states_match_5_2_c_exactly(mauna_e1):
    """Pin the exact rev-5 §5.2(c) near-boundary offsets, not just the count.

    ``test_m0_roles_and_33_state_equivalence_battery`` checks the state count
    and label uniqueness; this pins the frozen -15/+-8 magnitudes, the combined
    near-singular state, and the five exact ALR simplex pairs.  Changing e.g.
    r-15 to r-1, or (15,-15) to (10,-10), fails here.
    """
    roles = s3.resolve_m0_site_roles(mauna_e1)
    states = dict(s3.frozen_s3_states(mauna_e1, roles))
    z_map = s3.e1_u_to_z(mauna_e1.init_params, mauna_e1, roles).detach()

    def expected(mutate):
        z = z_map.clone()
        mutate(z)
        return z

    exact = {
        "map": z_map.clone(),
        "r-15": expected(lambda z: z.__setitem__(6, z[6] - 15.0)),
        "r+8": expected(lambda z: z.__setitem__(6, z[6] + 8.0)),
        "lengthscales+8": expected(
            lambda z: z.__setitem__(slice(0, 3), z[0:3] + 8.0)),
        "lengthscales-8": expected(
            lambda z: z.__setitem__(slice(0, 3), z[0:3] - 8.0)),
        "scale+8": expected(lambda z: z.__setitem__(3, z[3] + 8.0)),
        "scale-8": expected(lambda z: z.__setitem__(3, z[3] - 8.0)),
    }

    def near_singular(z):
        z[0:3] += 8.0
        z[3] += 8.0
        z[6] -= 15.0

    exact["near_singular"] = expected(near_singular)
    simplex_pairs = ((-15.0, 0.0), (0.0, -15.0), (15.0, 15.0),
                     (15.0, -15.0), (-15.0, 15.0))
    for a_t, a_s in simplex_pairs:
        pair = z_map.clone()
        pair[4], pair[5] = a_t, a_s
        exact[f"simplex/{a_t:g},{a_s:g}"] = pair

    for label, want in exact.items():
        torch.testing.assert_close(
            states[label], want, rtol=0.0, atol=0.0)

    # The full frozen label set (interior seed families + the 12 boundary
    # states) must match exactly, so a renamed/dropped/added state is caught.
    expected_labels = set(exact)
    expected_labels |= {
        f"map+{sigma}sd/seed{seed}"
        for sigma in (0.1, 1.0) for seed in range(5)}
    expected_labels |= {f"prior/seed{seed}" for seed in range(100, 110)}
    assert set(states) == expected_labels
    assert len(states) == 33

