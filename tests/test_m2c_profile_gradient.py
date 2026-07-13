"""Hermetic P1 profile-gradient battery (prereg v1.17, rev-5 section 2a).

All fixtures are synthetic. No sampler, scientific data, or profile optimizer
is used here; every tested state is static.
"""

import numpy as np
import pytest


torch = pytest.importorskip("torch")
gpytorch = pytest.importorskip("gpytorch")
pytest.importorskip("pyro")

from bistar_gp.config import (
    PRIOR_CONFIGS,
    build_kernels_from_config,
    build_likelihood_from_config,
)
from bistar_gp.e1_potential import E1Potential
from bistar_gp.fit import _mh_log_joint, fit_map
from bistar_gp.m2c_freeze import (
    D23_SENTINEL_MIN_REL,
    FD_STEP_GRAD,
    PRIOR_DRAW_SEEDS,
    TOL_GRAD_ABS,
    TOL_GRAD_REL,
)
from bistar_gp.model import (
    apply_hp_value,
    build_mauna_loa_kernels,
    build_model,
)
from bistar_gp.profile_potential import ProfilePotential


torch.set_default_dtype(torch.float64)
MAP_NEIGHBORHOOD_SIGMAS = (0.1, 1.0)
MAP_NEIGHBORHOOD_SEEDS = (0, 1, 2, 3, 4)


def _toy_data():
    torch.manual_seed(0)
    x = torch.linspace(0, 5, 40).double()
    y = torch.sin(2 * x) + 0.3 * torch.randn(40).double()
    return x, y


def _synthetic_monthly(n=120, seed=0):
    """Synthetic monthly series for the Mauna model structure only."""
    rng = np.random.default_rng(seed)
    x = np.arange(n) / 12.0
    y = 0.05 * x + 0.3 * np.sin(2 * np.pi * x) + 0.05 * rng.standard_normal(n)
    return torch.tensor(x).double(), torch.tensor(y).double()


def _toy_factory(x, y):
    prior_config = PRIOR_CONFIGS["toy_elicited_n20"]

    def fresh():
        kernels, names = build_kernels_from_config(prior_config)
        likelihood = build_likelihood_from_config(prior_config)
        return build_model(x, y, kernels, names, likelihood)

    return fresh


def _mauna_factory(x, y):
    def fresh():
        kernels, names = build_mauna_loa_kernels()
        return build_model(x, y, kernels, names)

    return fresh


def _make_case(name):
    if name == "toy":
        x, y = _toy_data()
        fresh = _toy_factory(x, y)
    else:
        x, y = _synthetic_monthly()
        fresh = _mauna_factory(x, y)
    model, likelihood = fresh()
    fit_map(model, likelihood, x, y, n_iter=150, lr=0.05, verbose=False)
    profile = ProfilePotential(model, likelihood, x, y)
    return {
        "name": name,
        "model": model,
        "likelihood": likelihood,
        "x": x,
        "y": y,
        "fresh": fresh,
        "profile": profile,
        "fd_cache": {},
    }


@pytest.fixture(scope="module", params=("toy", "mauna_structure"))
def profile_case(request):
    return _make_case(request.param)


@pytest.fixture(scope="module")
def synthetic_9site():
    """Generic additive inventory only; this is explicitly NOT PR-C's M1."""
    x = torch.linspace(0, 3, 30).double()
    y = (torch.sin(x) + 0.1 * torch.cos(3 * x)).double()
    kernels = []
    for index in range(4):
        kernels.append(
            gpytorch.kernels.ScaleKernel(
                gpytorch.kernels.RBFKernel(
                    lengthscale_constraint=gpytorch.constraints.Positive(),
                    lengthscale_prior=gpytorch.priors.LogNormalPrior(
                        0.1 * index, 0.8
                    ),
                ),
                outputscale_constraint=gpytorch.constraints.Positive(),
                outputscale_prior=gpytorch.priors.LogNormalPrior(0.0, 1.0),
            )
        )
    likelihood = gpytorch.likelihoods.GaussianLikelihood(
        noise_constraint=gpytorch.constraints.Positive(),
        noise_prior=gpytorch.priors.LogNormalPrior(-1.0, 1.0),
    )
    model, likelihood = build_model(
        x, y, kernels, [f"generic_{i}" for i in range(4)], likelihood
    )
    return ProfilePotential(model, likelihood, x, y)


def _current_theta(profile, site):
    _prior, fqname, constraint, _shape = profile._site_map[site]
    raw = dict(profile._model.named_parameters())[fqname].detach().clone()
    return constraint.transform(raw) if constraint is not None else raw


def _map_state(case):
    profile = case["profile"]
    u = {
        site: torch.log(_current_theta(profile, site))
        for site in profile.nuisance_sites
    }
    noise = _current_theta(profile, profile.noise_site)
    return u, noise


def _map_neighborhood_states(case):
    profile = case["profile"]
    u_map, noise = _map_state(case)
    states = [("map", u_map, noise)]
    for sigma in MAP_NEIGHBORHOOD_SIGMAS:
        for seed in MAP_NEIGHBORHOOD_SEEDS:
            generator = torch.Generator().manual_seed(seed)
            u = {
                site: u_map[site] + sigma * torch.randn(
                    u_map[site].shape,
                    generator=generator,
                    dtype=torch.float64,
                )
                for site in profile.nuisance_sites
            }
            states.append((f"map+{sigma}sd/seed{seed}", u, noise))
    return states


def _prior_draw_states(case):
    profile = case["profile"]
    priors = {name: prior for name, _module, prior, *_ in
              case["model"].named_priors()}
    states = []
    with torch.random.fork_rng():
        for seed in PRIOR_DRAW_SEEDS:
            torch.manual_seed(seed)
            theta = {site: priors[site].sample() for site in profile.sites}
            u = {
                site: torch.log(theta[site])
                for site in profile.nuisance_sites
            }
            states.append((f"prior/seed{seed}", u, theta[profile.noise_site]))
    return states


def _all_static_states(case):
    return _map_neighborhood_states(case) + _prior_draw_states(case)


def _independent_log_joint_g(case, u, noise):
    """Fresh-model scalar path mirroring study.log_joint plus sum(u)."""
    model, likelihood = case["fresh"]()
    profile = case["profile"]
    values = {site: torch.exp(u[site]) for site in profile.nuisance_sites}
    values[profile.noise_site] = noise
    assert tuple(name for name, *_ in model.named_priors()) == profile.sites
    for site in profile.sites:
        assert apply_hp_value(model, likelihood, site, values[site]), site
    mll = gpytorch.mlls.ExactMarginalLogLikelihood(likelihood, model)
    scalar = _mh_log_joint(mll, model, likelihood, case["x"], case["y"])
    return scalar + sum(float(u[site].sum()) for site in profile.nuisance_sites)


def _central_fd(fn, u, sites):
    gradients = {}
    for site in sites:
        flat = u[site].reshape(-1)
        result = torch.zeros_like(flat)
        for index in range(flat.numel()):
            h = FD_STEP_GRAD * max(1.0, abs(float(flat[index])))
            up = {name: value.clone() for name, value in u.items()}
            down = {name: value.clone() for name, value in u.items()}
            up[site].reshape(-1)[index] += h
            down[site].reshape(-1)[index] -= h
            result[index] = (fn(up) - fn(down)) / (2.0 * h)
        gradients[site] = result.reshape(u[site].shape)
    return gradients


def _independent_fd(case, label, u, noise):
    cache = case["fd_cache"]
    if label not in cache:
        profile = case["profile"]
        cache[label] = _central_fd(
            lambda state: _independent_log_joint_g(case, state, noise),
            u,
            profile.nuisance_sites,
        )
    return cache[label]


def _assert_gradient_band(actual, expected, sites, context):
    assert all(torch.isfinite(expected[site]).all() for site in sites), (
        f"{context}: independent finite differences left float64"
    )
    scale = max(
        1.0, max(float(expected[site].abs().max()) for site in sites)
    )
    worst = 0.0
    for site in sites:
        difference = float((actual[site] - expected[site]).abs().max())
        worst = max(worst, difference)
        assert difference <= TOL_GRAD_ABS + TOL_GRAD_REL * scale, (
            f"{context} / {site}: gradient difference {difference} "
            f"at scale {scale}"
        )
    return worst


def test_site_order_and_noise_role_match_e1(profile_case):
    case = profile_case
    profile = case["profile"]
    e1 = E1Potential(
        case["model"], case["likelihood"], case["x"], case["y"]
    )
    expected_count = 4 if case["name"] == "toy" else 7
    assert profile.sites == e1.sites
    assert len(profile.sites) == expected_count
    assert sum("noise_covar.noise" in site for site in profile.sites) == 1
    assert profile.nuisance_sites == tuple(
        site for site in profile.sites if site != profile.noise_site
    )


def test_authoritative_site_order_is_a_production_contract(profile_case):
    """When the caller supplies the authoritative E1 order, ProfilePotential
    validates it against named_priors and uses it (rev-5 §5.2), failing closed
    on any set mismatch — without constructing the pyro oracle itself."""
    case = profile_case
    e1 = E1Potential(case["model"], case["likelihood"], case["x"], case["y"])
    # Authoritative order accepted and honoured.
    contracted = ProfilePotential(
        case["model"], case["likelihood"], case["x"], case["y"], sites=e1.sites
    )
    assert contracted.sites == e1.sites
    assert contracted.noise_site == case["profile"].noise_site
    # The supplied ORDER is used, not merely the set: a permutation that differs
    # from named_priors order is honoured verbatim (guards against a set-only
    # implementation that would silently keep the discovered order).
    permuted = (e1.sites[1], e1.sites[0]) + e1.sites[2:]
    assert permuted != e1.sites
    permuted_profile = ProfilePotential(
        case["model"], case["likelihood"], case["x"], case["y"], sites=permuted
    )
    assert permuted_profile.sites == permuted
    # A set that cannot be reconciled with named_priors fails closed.
    bad_sites = e1.sites[:-1] + ("covar_module.kernels.99.not_a_real_prior",)
    with pytest.raises(RuntimeError, match="site-order contract"):
        ProfilePotential(
            case["model"], case["likelihood"], case["x"], case["y"], sites=bad_sites
        )
    # A duplicated site (same set, but not one-to-one) also fails closed —
    # otherwise g_value would loop over and double-count that coordinate.
    dup_sites = e1.sites + (e1.sites[0],)
    with pytest.raises(RuntimeError, match="site-order contract"):
        ProfilePotential(
            case["model"], case["likelihood"], case["x"], case["y"], sites=dup_sites
        )


def test_generic_nine_site_inventory_is_supported(synthetic_9site):
    profile = synthetic_9site
    assert len(profile.sites) == 9
    assert len(profile.nuisance_sites) == 8
    assert sum("noise_covar.noise" in site for site in profile.sites) == 1
    u = {
        site: torch.log(_current_theta(profile, site))
        for site in profile.nuisance_sites
    }
    noise = _current_theta(profile, profile.noise_site)
    assert torch.isfinite(profile.g_value(u, noise))
    gradients = profile.g_grad_functional(u, noise)
    assert all(torch.isfinite(value).all() for value in gradients.values())


def test_g_value_matches_independent_log_joint(profile_case):
    case = profile_case
    profile = case["profile"]
    for label, u, noise in _map_neighborhood_states(case)[:4]:
        functional = float(profile.g_value(u, noise))
        independent = _independent_log_joint_g(case, u, noise)
        difference = abs(functional - independent)
        assert difference <= 1e-9 * max(1.0, abs(independent)), (
            f"{case['name']} / {label}: functional {functional}, "
            f"independent {independent}, difference {difference}"
        )


def test_functional_gradient_matches_independent_finite_difference(profile_case):
    case = profile_case
    profile = case["profile"]
    states = _all_static_states(case)
    executed = set()
    worst = 0.0
    for label, u, noise in states:
        actual = profile.g_grad_functional(u, noise)
        expected = _independent_fd(case, label, u, noise)
        worst = max(worst, _assert_gradient_band(
            actual, expected, profile.nuisance_sites,
            f"{case['name']} / {label}",
        ))
        executed.add(label)
    expected_labels = {label for label, _u, _noise in states}
    assert executed == expected_labels, sorted(expected_labels - executed)
    assert len(states) == 21
    print(f"M2C_GRADIENT_MAX {case['name']} {worst:.17g}")


def test_functional_gradient_matches_own_finite_difference(profile_case):
    case = profile_case
    profile = case["profile"]
    worst = 0.0
    for label, u, noise in _map_neighborhood_states(case)[:3]:
        expected = _central_fd(
            lambda state: float(profile.g_value(state, noise)),
            u,
            profile.nuisance_sites,
        )
        actual = profile.g_grad_functional(u, noise)
        worst = max(worst, _assert_gradient_band(
            actual, expected, profile.nuisance_sites,
            f"self-FD {case['name']} / {label}",
        ))
    print(f"M2C_SELF_GRADIENT_MAX {case['name']} {worst:.17g}")


def test_naive_data_gradient_keeps_d23_defect_visible(profile_case):
    """Pin every nuisance site across five non-MAP states, per D23."""
    case = profile_case
    profile = case["profile"]
    states = _map_neighborhood_states(case)[1:6]
    per_site = {site: 0.0 for site in profile.nuisance_sites}
    for label, u, noise in states:
        expected = _independent_fd(case, label, u, noise)
        naive = profile.g_grad_naive_data(u, noise)
        for site in profile.nuisance_sites:
            if naive[site] is None:
                per_site[site] = float("inf")
                continue
            relative = float((naive[site] - expected[site]).abs().max()) / max(
                1.0, float(expected[site].abs().max())
            )
            per_site[site] = max(per_site[site], relative)
    assert len(states) >= 3
    for site, worst_relative in per_site.items():
        assert worst_relative > D23_SENTINEL_MIN_REL, (
            f"naive .data gradient now matches FD(g) on nuisance site {site} "
            f"(worst relative mismatch {worst_relative}); the D23 defect "
            "may be gone in this environment—revisit prereg v1.3/D23 "
            "before trusting this run"
        )
    print(
        f"M2C_D23_MAX {case['name']} "
        f"{max(per_site.values()):.17g}"
    )
