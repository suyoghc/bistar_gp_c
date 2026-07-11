"""E1 equivalence battery (D19 M2b; plan §2 Stage B + §6.15 row 1; prereg
addenda v1.2/v1.3/v1.4).

Gates the E1 direct-parameter potential against the corrected S1 pyro target
BEFORE any science use. The numeric tolerances and point-generation
distributions below are FROZEN by prereg addendum v1.4
(docs/prereg-addenda-d19.md) — do not tune them to make a failure pass; an
E1 defect is fixed in E1, and a genuine tolerance revision is a new
append-only addendum.

Battery structure (v1.4 item letters):
  (a) site inventory and ordering; duplicate-prior/site guards (D6 class)
  (b) potential agreement with the S1 oracle over the frozen point sets
  (c) gradient agreement — E1 autograd vs CENTRAL FINITE DIFFERENCES of the
      oracle potential (v1.3: the oracle's own autograd is broken for kernel
      sites and is never a reference), plus E1 autograd vs E1's own FD
  (d) directional Hessians — E1 double-backward HVP vs second differences of
      the oracle potential along frozen directions
  (e) likelihood vs prior/Jacobian components, each against an independent
      oracle at paired constrained states
  (f) transform round-trips
  (g) posterior-predictive equality on PAIRED identical constrained states
      (v1.2 point 5 — never on independent chains)
  (h) invalid-SPD behavior parity
  (i) A10 frozen-period exclusion
  (j) S1f sampler smoke: fit_hmc dict schema + diagnostics honesty contract

All data here is SYNTHETIC (toy structure and a synthetic monthly series on
the Mauna model structure) — the battery is a code-level property; no real
Mauna value is read (§6.5 ordering).
"""

import copy

import numpy as np
import pytest

torch = pytest.importorskip("torch")
gpytorch = pytest.importorskip("gpytorch")
pyro = pytest.importorskip("pyro")

from bistar_gp.e1_potential import build_e1_potential, fit_hmc_e1, _site_parameter_map
from bistar_gp.fit import fit_map, DEFAULT_JITTER
from bistar_gp.model import (
    MAUNA_FROZEN_PERIOD,
    apply_hp_value,
    build_mauna_loa_kernels,
    build_model,
    build_toy_kernels,
)

torch.set_default_dtype(torch.float64)

# ── Frozen battery constants (prereg addendum v1.4) ─────────────────────────

TOL_POTENTIAL_REL = 1e-9        # |dV| <= TOL * max(1, |V_oracle|)
TOL_GRAD_ABS = 1e-4             # per coordinate, vs central FD of the oracle
TOL_GRAD_REL = 1e-4             # ... relative to max coordinate magnitude
TOL_HVP_REL = 1e-3              # directional Hessian vs oracle 2nd difference
TOL_COMPONENT_REL = 1e-9        # likelihood / prior / Jacobian pieces
TOL_ROUNDTRIP = 1e-10           # u -> theta -> u and theta -> raw -> theta
TOL_PREDICTIVE = 1e-9           # paired-state predictive mean/variance

FD_STEP_GRAD = 1e-5             # central-difference step (per coordinate)
FD_STEP_HVP = 1e-3              # second-difference step (directional)

MAP_NEIGHBORHOOD_SIGMAS = (0.1, 1.0)
MAP_NEIGHBORHOOD_SEEDS = (0, 1, 2, 3, 4)
PRIOR_DRAW_SEEDS = tuple(range(100, 110))
HVP_DIRECTION_SEEDS = (200, 201, 202)

# Tail/boundary stress offsets, applied to u_map coordinates by site-name
# substring. Per v1.2 point 4 the frozen period contributes no coordinate and
# no Interval boundary appears among the seven sites: the stress set is
# near-zero noise, near-singular kernels (long lengthscales + large signal on
# a tiny nugget), and extreme lengthscale/outputscale magnitudes.
TAIL_OFFSETS = (
    ("near_zero_noise", {"noise": -15.0}),
    ("large_noise", {"noise": +8.0}),
    ("long_lengthscales", {"lengthscale": +8.0}),
    ("short_lengthscales", {"lengthscale": -8.0}),
    ("large_outputscales", {"outputscale": +8.0, "variance": +8.0}),
    ("small_outputscales", {"outputscale": -8.0, "variance": -8.0}),
    ("near_singular", {"lengthscale": +8.0, "outputscale": +8.0,
                       "variance": +8.0, "noise": -15.0}),
)

# Beyond-float64 stress: both paths must behave identically (h).
INVALID_SPD_OFFSETS = (
    ("degenerate_noise", {"noise": -40.0}),
    ("blown_scales", {"outputscale": +30.0, "variance": +30.0, "noise": -40.0}),
)

# ── Fixtures ────────────────────────────────────────────────────────────────


def _toy_data():
    torch.manual_seed(0)
    x = torch.linspace(0, 5, 40).double()
    y = torch.sin(2 * x) + 0.3 * torch.randn(40).double()
    return x, y


def _synthetic_monthly(n=120, seed=0):
    """Synthetic monthly-style series for the Mauna MODEL STRUCTURE — not
    Mauna data (the battery is a code-level gate; §6.5)."""
    rng = np.random.default_rng(seed)
    x = np.arange(n) / 12.0
    y = 0.05 * x + 0.3 * np.sin(2 * np.pi * x) + 0.05 * rng.standard_normal(n)
    return torch.tensor(x).double(), torch.tensor(y).double()


def _built(structure):
    if structure == "toy":
        x, y = _toy_data()
        kernels, names = build_toy_kernels()
    else:
        x, y = _synthetic_monthly()
        kernels, names = build_mauna_loa_kernels()
    model, lik = build_model(x, y, kernels, names)
    fit_map(model, lik, x, y, n_iter=150, verbose=False)
    return model, lik, x, y


@pytest.fixture(scope="module", params=["toy", "mauna_structure"])
def battery(request):
    model, lik, x, y = _built(request.param)
    e1 = build_e1_potential(model, lik, x, y)
    return request.param, model, lik, x, y, e1


# ── Frozen point sets ───────────────────────────────────────────────────────


def _map_neighborhood_states(e1):
    u0 = {s: v.clone() for s, v in e1.init_params.items()}
    states = [("map", u0)]
    for sigma in MAP_NEIGHBORHOOD_SIGMAS:
        for seed in MAP_NEIGHBORHOOD_SEEDS:
            g = torch.Generator().manual_seed(seed)
            u = {s: u0[s] + sigma * torch.randn(u0[s].shape, generator=g,
                                                dtype=torch.float64)
                 for s in e1.sites}
            states.append((f"map+{sigma}sd/seed{seed}", u))
    return states


def _prior_draw_states(e1, model):
    priors = {t[0]: t[2] for t in model.named_priors()}
    states = []
    for seed in PRIOR_DRAW_SEEDS:
        torch.manual_seed(seed)
        theta = {s: priors[s].sample() for s in e1.sites}
        states.append((f"prior/seed{seed}", e1.unconstrain(theta)))
    return states


def _offset_states(e1, offsets):
    u0 = {s: v.clone() for s, v in e1.init_params.items()}
    states = []
    for label, spec in offsets:
        u = {s: u0[s].clone() for s in e1.sites}
        for key, off in spec.items():
            for s in e1.sites:
                if key in s:
                    u[s] = u[s] + off
        states.append((label, u))
    return states


def _all_regular_states(e1, model):
    return (_map_neighborhood_states(e1) + _prior_draw_states(e1, model)
            + _offset_states(e1, TAIL_OFFSETS))


def _finite_potential(fn, u):
    try:
        v = fn(u)
    except RuntimeError:
        return None
    v = float(v)
    return v if np.isfinite(v) else None


# ── (a) inventory and ordering ─────────────────────────────────────────────


def test_site_inventory_and_order_match_s1(battery):
    """E1's public coordinates are exactly the initialize_model sites, in the
    order initialize_model produced them, one per registered prior (v1.2
    point 1)."""
    structure, model, lik, x, y, e1 = battery
    expected = 7 if structure == "mauna_structure" else 4
    assert len(e1.sites) == expected, e1.sites
    assert list(e1.sites) == list(e1.init_params), "site order authority broken"
    assert set(e1.sites) == {t[0] for t in model.named_priors()}
    assert len(set(e1.sites)) == len(e1.sites)


def test_duplicate_prior_registration_raises():
    """A module registering the same hyperparameter prior twice (the D4
    double-registration class) must fail the E1 build loudly, not sample a
    phantom latent (v1.2 point 3)."""
    x, y = _toy_data()
    kernels, names = build_toy_kernels()
    model, lik = build_model(x, y, kernels, names)
    se = model.kernel_components[0]
    se.register_prior("outputscale_second_prior",
                      gpytorch.priors.GammaPrior(2.0, 2.0), "outputscale")
    sites = [t[0] for t in model.named_priors()]
    with pytest.raises(RuntimeError, match="raw parameter|disagree|one raw"):
        _site_parameter_map(model, sites)


def test_site_prior_set_mismatch_raises(battery):
    """A pyro site with no matching registered prior (or vice versa) is the
    D6 dropped/invented-latent class: the build must raise."""
    structure, model, lik, x, y, e1 = battery
    with pytest.raises(RuntimeError, match="disagree"):
        _site_parameter_map(model, list(e1.sites) + ["ghost_site_prior"])


# ── (b) potential agreement ────────────────────────────────────────────────


def test_potential_agrees_with_oracle_everywhere(battery):
    """E1 potential equals the corrected S1 oracle on every frozen state
    (MAP neighborhoods, prior draws, tail/boundary) within
    TOL_POTENTIAL_REL (v1.4)."""
    structure, model, lik, x, y, e1 = battery
    checked = 0
    for label, u in _all_regular_states(e1, model):
        vo = _finite_potential(e1.oracle_potential_fn, u)
        ve = _finite_potential(e1.potential_fn, u)
        if vo is None or ve is None:
            # tail states may legitimately defeat float64 on both paths;
            # parity of behavior for these is test (h)
            assert vo is None and ve is None, (
                f"{label}: one path finite, the other not (oracle={vo}, e1={ve})")
            continue
        assert abs(vo - ve) <= TOL_POTENTIAL_REL * max(1.0, abs(vo)), (
            f"{label}: oracle {vo} vs e1 {ve}")
        checked += 1
    assert checked >= 20, f"only {checked} states were comparable"


# ── (c) gradients ──────────────────────────────────────────────────────────


def _central_fd_grad(fn, u, sites):
    g = {}
    for s in sites:
        gp_, gm = {k: v.clone() for k, v in u.items()}, {k: v.clone() for k, v in u.items()}
        flat_p = gp_[s].reshape(-1)
        flat_m = gm[s].reshape(-1)
        grads = torch.zeros_like(flat_p)
        for i in range(flat_p.numel()):
            h = FD_STEP_GRAD * max(1.0, float(flat_p[i].abs()))
            orig = float(flat_p[i])
            flat_p[i] = orig + h
            flat_m[i] = orig - h
            vp = fn({k: (gp_[k] if k == s else u[k]) for k in u})
            vm = fn({k: (gm[k] if k == s else u[k]) for k in u})
            grads[i] = (vp - vm) / (2 * h)
            flat_p[i] = orig
            flat_m[i] = orig
        g[s] = grads.reshape(u[s].shape)
    return g


def _autograd(fn, u, sites):
    ua = {s: u[s].clone().requires_grad_(True) for s in sites}
    gs = torch.autograd.grad(fn(ua), [ua[s] for s in sites])
    return dict(zip(sites, gs))


def test_e1_gradient_matches_oracle_finite_differences(battery):
    """E1 autograd equals central finite differences of the ORACLE potential
    on MAP-neighborhood and prior-draw states (v1.3: the oracle's autograd is
    broken for kernel sites and is never the reference)."""
    structure, model, lik, x, y, e1 = battery
    states = _map_neighborhood_states(e1)[:6] + _prior_draw_states(e1, model)[:4]
    for label, u in states:
        if _finite_potential(e1.oracle_potential_fn, u) is None:
            continue
        fd = _central_fd_grad(e1.oracle_potential_fn, u, e1.sites)
        ag = _autograd(e1.potential_fn, u, e1.sites)
        scale = max(1.0, max(float(fd[s].abs().max()) for s in e1.sites))
        for s in e1.sites:
            d = float((ag[s] - fd[s]).abs().max())
            assert d <= TOL_GRAD_ABS + TOL_GRAD_REL * scale, (
                f"{label} / {s}: |e1 autograd - oracle FD| = {d} (scale {scale})")


def test_e1_gradient_matches_its_own_finite_differences(battery):
    """E1's autograd is additionally self-consistent (guards against a broken
    functional-substitution graph reproducing the D23 failure inside E1)."""
    structure, model, lik, x, y, e1 = battery
    states = _map_neighborhood_states(e1)[:3]
    for label, u in states:
        fd = _central_fd_grad(e1.potential_fn, u, e1.sites)
        ag = _autograd(e1.potential_fn, u, e1.sites)
        scale = max(1.0, max(float(fd[s].abs().max()) for s in e1.sites))
        for s in e1.sites:
            d = float((ag[s] - fd[s]).abs().max())
            assert d <= TOL_GRAD_ABS + TOL_GRAD_REL * scale, (label, s, d)


def test_oracle_autograd_defect_is_still_present(battery):
    """The D23 defect this battery routes around: pyro autograd through the
    traced gpytorch target loses the likelihood gradient on kernel sites. If
    an environment upgrade FIXES this, the test fails to alert us that the
    v1.3 disclosure (and the S1-vs-S1f asymmetry note) needs revisiting."""
    structure, model, lik, x, y, e1 = battery
    label, u = _map_neighborhood_states(e1)[1]
    fd = _central_fd_grad(e1.oracle_potential_fn, u, e1.sites)
    ag = _autograd(e1.oracle_potential_fn, u, e1.sites)
    kernel_sites = [s for s in e1.sites if "noise" not in s]
    mismatch = max(float((ag[s] - fd[s]).abs().max()) for s in kernel_sites)
    assert mismatch > 1e-2, (
        "oracle autograd now matches FD on kernel sites — the D23 defect is "
        "gone in this environment; revisit prereg v1.3 before trusting this run")


# ── (d) directional Hessians ───────────────────────────────────────────────


def _unit_direction(u, sites, seed):
    g = torch.Generator().manual_seed(seed)
    v = {s: torch.randn(u[s].shape, generator=g, dtype=torch.float64)
         for s in sites}
    norm = torch.sqrt(sum((v[s] ** 2).sum() for s in sites))
    return {s: v[s] / norm for s in sites}


def _directional_hessian_from_gradient(fn, u, v, sites, h):
    """v^T H v via a central difference OF THE AUTOGRAD GRADIENT — first-order
    machinery only. Double-backward through the gpytorch marginal log-prob
    graph returns silently wrong values (the D24 sentinel below), so the
    battery's Hessian gate never uses create_graph."""
    up = {s: u[s] + h * v[s] for s in sites}
    um = {s: u[s] - h * v[s] for s in sites}
    gp_, gm = _autograd(fn, up, sites), _autograd(fn, um, sites)
    return float(sum(((gp_[s] - gm[s]) / (2 * h) * v[s]).sum() for s in sites))


def test_directional_hessians_agree(battery):
    """The directional derivative of E1's (proven-correct) gradient equals the
    second central difference of the oracle potential along frozen unit
    directions — curvature of the shared target, referenced only through
    first-order-correct machinery (v1.4)."""
    structure, model, lik, x, y, e1 = battery
    states = [_map_neighborhood_states(e1)[0], _map_neighborhood_states(e1)[1],
              _prior_draw_states(e1, model)[0]]
    for (label, u) in states:
        for dseed in HVP_DIRECTION_SEEDS:
            v = _unit_direction(u, e1.sites, dseed)
            vhv_e1 = _directional_hessian_from_gradient(
                e1.potential_fn, u, v, e1.sites, FD_STEP_GRAD)
            h = FD_STEP_HVP
            up = {s: u[s] + h * v[s] for s in e1.sites}
            um = {s: u[s] - h * v[s] for s in e1.sites}
            vhv_fd = float((e1.oracle_potential_fn(up)
                            - 2 * e1.oracle_potential_fn(u)
                            + e1.oracle_potential_fn(um)) / h ** 2)
            denom = max(1.0, abs(vhv_fd))
            assert abs(vhv_e1 - vhv_fd) <= TOL_HVP_REL * denom, (
                f"{label}/dir{dseed}: e1 {vhv_e1} vs oracle 2nd-diff {vhv_fd}")


def test_double_backward_hessian_defect_is_still_present(battery):
    """D24 sentinel: create_graph double-backward through the marginal
    log-prob graph gives a silently wrong v^T H v (measured ~16% off on the
    toy at MAP; persists with fast_computations disabled, so the defect is in
    the custom linear-operator autograd Functions, not the fast paths). The
    battery and any M2c S2 mass-matrix construction must therefore use
    first-order machinery (FD of the E1 gradient). If an environment upgrade
    fixes double-backward, this sentinel fails to force a v1.4 revisit —
    exactly like the D23 sentinel above."""
    structure, model, lik, x, y, e1 = battery
    label, u = _map_neighborhood_states(e1)[0]
    v = _unit_direction(u, e1.sites, HVP_DIRECTION_SEEDS[0])

    ua = {s: u[s].clone().requires_grad_(True) for s in e1.sites}
    grads = torch.autograd.grad(e1.potential_fn(ua), [ua[s] for s in e1.sites],
                                create_graph=True)
    gv = sum((gr * v[s]).sum() for gr, s in zip(grads, e1.sites))
    hvp = torch.autograd.grad(gv, [ua[s] for s in e1.sites])
    vhv_dbl = float(sum((t * v[s]).sum() for t, s in zip(hvp, e1.sites)))

    vhv_true = _directional_hessian_from_gradient(
        e1.potential_fn, u, v, e1.sites, FD_STEP_GRAD)
    assert abs(vhv_dbl - vhv_true) > 1e-2 * max(1.0, abs(vhv_true)), (
        "double-backward now matches the first-order Hessian — the D24 "
        "defect is gone in this environment; revisit prereg v1.4 (and the "
        "S2 mass-matrix note) before trusting this run")


# ── (e) components against independent oracles ────────────────────────────


def _independent_pieces(model, x, y, sites, theta):
    m2 = copy.deepcopy(model)
    for s in sites:
        assert apply_hp_value(m2, m2.likelihood, s, theta[s]), s
    m2.train()
    m2.likelihood.train()
    with gpytorch.settings.cholesky_jitter(DEFAULT_JITTER):
        marginal = float(m2.likelihood(m2(x)).log_prob(y))
    priors = {t[0]: t[2] for t in model.named_priors()}
    log_prior = sum(float(priors[s].log_prob(theta[s]).sum()) for s in sites)
    return marginal, log_prior


def test_components_match_independent_oracles(battery):
    """Likelihood and prior/Jacobian tested separately (§6.15): the marginal
    equals the deep-copy apply_hp_value path, the prior sum equals the
    named_priors sum, the Jacobian equals the transform's own log-abs-det —
    each at paired constrained states, each counted once (v1.2 point 3)."""
    structure, model, lik, x, y, e1 = battery
    states = _map_neighborhood_states(e1)[:4] + _prior_draw_states(e1, model)[:3]
    for label, u in states:
        theta = e1.constrain(u)
        marginal_ref, prior_ref = _independent_pieces(model, x, y, e1.sites, theta)
        jac_ref = sum(
            float(e1.transforms[s].inv.log_abs_det_jacobian(u[s], theta[s]).sum())
            for s in e1.sites)
        lm, lp, lj = e1.components(u)
        assert float(lm) == pytest.approx(marginal_ref, rel=TOL_COMPONENT_REL), label
        assert float(lp) == pytest.approx(prior_ref, rel=TOL_COMPONENT_REL), label
        assert float(lj) == pytest.approx(jac_ref, rel=TOL_COMPONENT_REL), label
        assert float(e1.potential_fn(u)) == pytest.approx(
            -(float(lm) + float(lp) + float(lj)), rel=TOL_COMPONENT_REL), label


# ── (f) round-trips ────────────────────────────────────────────────────────


def test_transform_round_trips(battery):
    structure, model, lik, x, y, e1 = battery
    for label, u in _all_regular_states(e1, model):
        theta = e1.constrain(u)
        u_back = e1.unconstrain(theta)
        for s in e1.sites:
            du = float((u_back[s] - u[s]).abs().max())
            assert du <= TOL_ROUNDTRIP * max(1.0, float(u[s].abs().max())), (
                label, s, du)
        for s in e1.sites:
            _prior, _fq, constraint, _shape = e1._site_map[s]
            if constraint is None:
                continue
            back = constraint.transform(constraint.inverse_transform(theta[s]))
            dt = float((back - theta[s]).abs().max())
            assert dt <= TOL_ROUNDTRIP * max(1.0, float(theta[s].abs().max())), (
                label, s, dt)


# ── (g) posterior-predictive equality on paired states ────────────────────


def test_posterior_predictive_equality_paired_states(battery):
    """One frozen set of constrained states, both parameter-injection paths,
    pointwise-equal predictive mean and variance (v1.2 point 5: paired
    states, never independent chains)."""
    structure, model, lik, x, y, e1 = battery
    x_grid = torch.linspace(float(x.min()), float(x.max()) + 0.5, 25).double()
    states = _prior_draw_states(e1, model)[:3]
    for label, u in states:
        theta = e1.constrain(u)

        # path A: the S1-consumer path (apply_hp_value on a fresh copy)
        mA = copy.deepcopy(model)
        for s in e1.sites:
            assert apply_hp_value(mA, mA.likelihood, s, theta[s]), s
        mA.eval()
        mA.likelihood.eval()
        with torch.no_grad(), gpytorch.settings.cholesky_jitter(DEFAULT_JITTER):
            predA = mA.likelihood(mA(x_grid))
            meanA, varA = predA.mean, predA.variance

        # path B: E1's functional substitution, same theta, same module class
        overrides = {}
        for s in e1.sites:
            _prior, fq, constraint, shape = e1._site_map[s]
            raw = (constraint.inverse_transform(theta[s])
                   if constraint is not None else theta[s])
            overrides[fq] = raw.reshape(shape).detach()
        mB = copy.deepcopy(model)
        mB.eval()
        mB.likelihood.eval()
        with torch.no_grad(), gpytorch.settings.cholesky_jitter(DEFAULT_JITTER):
            predB = torch.func.functional_call(
                _PredictiveWrapper(mB), {"gp." + k: v for k, v in overrides.items()},
                (x_grid,))
            meanB, varB = predB

        dm = float((meanA - meanB).abs().max())
        dv = float((varA - varB).abs().max())
        assert dm <= TOL_PREDICTIVE * max(1.0, float(meanA.abs().max())), (label, dm)
        assert dv <= TOL_PREDICTIVE * max(1.0, float(varA.abs().max())), (label, dv)


class _PredictiveWrapper(torch.nn.Module):
    def __init__(self, gp_model):
        super().__init__()
        self.gp = gp_model

    def forward(self, x_grid):
        pred = self.gp.likelihood(self.gp(x_grid))
        return pred.mean, pred.variance


# ── (h) invalid-SPD parity ─────────────────────────────────────────────────


def test_invalid_spd_behavior_parity(battery):
    """States engineered past float64 must produce the SAME outcome on both
    paths: both raise / both non-finite / both finite-and-equal. E1 must not
    silently 'fix' states the S1 target rejects (or vice versa)."""
    structure, model, lik, x, y, e1 = battery
    for label, u in _offset_states(e1, INVALID_SPD_OFFSETS):
        vo = _finite_potential(e1.oracle_potential_fn, u)
        ve = _finite_potential(e1.potential_fn, u)
        if vo is None or ve is None:
            assert vo is None and ve is None, (
                f"{label}: oracle={vo}, e1={ve} — behavior mismatch")
        else:
            assert abs(vo - ve) <= TOL_POTENTIAL_REL * max(1.0, abs(vo)), (
                f"{label}: oracle {vo} vs e1 {ve}")


# ── (i) frozen-period exclusion ────────────────────────────────────────────


def test_period_excluded_and_unmoved(battery):
    """A10 (v1.2 point 4): no period coordinate exists, no period override is
    built, and the constrained period stays exactly 1.0 through potential and
    gradient evaluations across the frozen states."""
    structure, model, lik, x, y, e1 = battery
    if structure != "mauna_structure":
        pytest.skip("period only exists in the Mauna structure")
    assert not any("period" in s for s in e1.sites)
    assert not any("period" in fq for _p, fq, _c, _sh in e1._site_map.values())
    base = model.kernel_components[1].base_kernel
    for label, u in _map_neighborhood_states(e1)[:3]:
        e1.potential_fn(u)
        _autograd(e1.potential_fn, u, e1.sites)
        assert base.period_length.item() == MAUNA_FROZEN_PERIOD, label
        assert not base.raw_period_length.requires_grad


# ── (j) S1f sampler smoke ──────────────────────────────────────────────────


def test_fit_hmc_e1_schema_and_diagnostics():
    """S1f returns the fit_hmc dict schema (constrained (n,) arrays, same
    site names), and its diagnostics honor the honesty contract."""
    x, y = _toy_data()
    kernels, names = build_toy_kernels()
    model, lik = build_model(x, y, kernels, names)
    fit_map(model, lik, x, y, n_iter=100, verbose=False)

    samples, diag = fit_hmc_e1(model, lik, x, y, n_samples=8, n_warmup=8,
                               verbose=False, seed=0, max_tree_depth=5,
                               return_diagnostics=True)
    assert len(samples) == 4, sorted(samples)
    for name, arr in samples.items():
        assert arr.shape == (8,), (name, arr.shape)
        assert np.isfinite(arr).all(), name
        assert (arr > 0).all(), (name, "constrained positives expected")
    assert diag.sampler == "nuts_e1"
    assert diag.n_draws == 8 and diag.n_chains == 1
    assert diag.leapfrog_counts is not None
    assert len(diag.leapfrog_counts[0]) == 8
    assert set(diag.site_names) == set(samples)
    # round-trip through the D20 schema
    from bistar_gp.sampler_diagnostics import SamplerDiagnostics
    assert SamplerDiagnostics.from_json(diag.to_json()) == diag


def test_fit_hmc_e1_single_draw_schema():
    """n_samples=1 must keep the (1,) schema (the fit_hmc reshape contract)."""
    x, y = _toy_data()
    kernels, names = build_toy_kernels()
    model, lik = build_model(x, y, kernels, names)
    fit_map(model, lik, x, y, n_iter=60, verbose=False)
    samples = fit_hmc_e1(model, lik, x, y, n_samples=1, n_warmup=5,
                         verbose=False, seed=0, max_tree_depth=4)
    for name, arr in samples.items():
        assert arr.shape == (1,), (name, arr.shape)
