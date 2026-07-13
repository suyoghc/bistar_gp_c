"""M2c S3 M0 reparameterization (prereg v1.17, rev-5 §5.2).

S3 is defined only for the seven M0 scalar sites: trend, seasonal, and
medium-term lengthscale/outputscale pairs plus observation noise.  Site roles
are resolved structurally from the model's semantic component inventory and
raw parameters, then emitted in authoritative ``E1Potential.sites`` order.
Any inventory or role ambiguity is a fail-closed STOP for S3.

The sampler-capable route at the bottom is verified in PR B only through
mocked NUTS/MCMC.  Rev-5 §5.2 freezes no mass override for S3, so the route
preserves S1f/Pyro's default mass adaptation while sampling the seven-vector
z coordinate.
"""

from dataclasses import dataclass
from typing import Mapping

import numpy as np
import torch

from .e1_potential import _run_e1_nuts_route, build_e1_potential
from .fit import DEFAULT_JITTER
from .m2c_freeze_s2s3 import (
    S3_DENSITY_TOL,
    S3_GRAD_ABS,
    S3_GRAD_REL,
    S3_NEIGHBORHOOD_SEEDS,
    S3_NEIGHBORHOOD_SIGMAS,
    S3_N_STATES,
    S3_PRIOR_DRAW_SEEDS,
    S3_ROUNDTRIP_TOL,
    S3_SLOGDET_TOL,
)


torch.set_default_dtype(torch.float64)
S3_COORDINATE = "z"
S3_Z_NAMES = (
    "ell_trend", "ell_seasonal", "ell_medium", "log_total_scale",
    "alr_trend", "alr_seasonal", "log_noise_ratio",
)
S3_SEMANTIC_SITE_ROLES = (
    "trend_lengthscale", "seasonal_lengthscale", "medium_lengthscale",
    "trend_outputscale", "seasonal_outputscale", "medium_outputscale",
    "noise",
)


class S3GateError(RuntimeError):
    """A mandatory rev-5 §5.2 inventory/equivalence gate failed."""


@dataclass(frozen=True)
class S3SiteRoles:
    """Semantic M0 roles mapped to E1's actual sample-site names."""

    trend_lengthscale: str
    seasonal_lengthscale: str
    medium_lengthscale: str
    trend_outputscale: str
    seasonal_outputscale: str
    medium_outputscale: str
    noise: str

    @property
    def semantic_sites(self) -> tuple[str, ...]:
        return tuple(getattr(self, role) for role in S3_SEMANTIC_SITE_ROLES)


@dataclass(frozen=True)
class S3EquivalenceResult:
    """Execution-complete summary of the frozen 33-state battery."""

    executed_labels: tuple[str, ...]
    max_u_slogdet_error: float
    max_theta_slogdet_error: float
    max_u_roundtrip_error: float
    max_theta_roundtrip_error: float
    max_density_error: float
    max_gradient_error: float


def _outside_definition(site_count: int) -> S3GateError:
    return S3GateError(
        "S3 STOP: site inventory is outside the frozen S3 definition "
        f"(expected M0's 7 sites, found {site_count})")


def resolve_m0_site_roles(e1) -> S3SiteRoles:
    """Resolve the seven M0 roles structurally; reject ambiguity.

    In particular, a four-site toy and a future nine-site M1 arm are outside
    the frozen S3 definition.  The latter remains PR-C work and is never
    represented as if it had S3 coverage here.
    """
    sites = tuple(e1.sites)
    if len(sites) != 7 or len(set(sites)) != 7:
        raise _outside_definition(len(sites))

    model = getattr(e1, "_model", None)
    likelihood = getattr(e1, "_likelihood", None)
    site_map = getattr(e1, "_site_map", None)
    if model is None or likelihood is None or not isinstance(site_map, dict):
        raise S3GateError(
            "S3 STOP: seven-site inventory lacks structural role metadata")

    component_names = tuple(getattr(model, "component_names", ()))
    kernels = tuple(getattr(model, "kernel_components", ()))
    expected_names = ("trend", "seasonal", "medium_term")
    if (len(component_names) != 3 or len(kernels) != 3
            or len(set(component_names)) != 3
            or set(component_names) != set(expected_names)):
        raise S3GateError(
            "S3 STOP: M0 site-role ambiguity in component inventory: "
            f"names={component_names}")

    kernel_by_name = dict(zip(component_names, kernels))
    parameter_name_by_id = {
        id(parameter): name for name, parameter in model.named_parameters()
    }

    def parameter_name(parameter, role):
        name = parameter_name_by_id.get(id(parameter))
        if name is None:
            raise S3GateError(
                f"S3 STOP: raw parameter for {role} is not model-registered")
        return name

    targets = {}
    for semantic, component_name in (
            ("trend", "trend"),
            ("seasonal", "seasonal"),
            ("medium", "medium_term")):
        kernel = kernel_by_name[component_name]
        base = getattr(kernel, "base_kernel", None)
        raw_lengthscale = getattr(base, "raw_lengthscale", None)
        raw_outputscale = getattr(kernel, "raw_outputscale", None)
        if raw_lengthscale is None or raw_outputscale is None:
            raise S3GateError(
                f"S3 STOP: component {component_name} lacks an unambiguous "
                "lengthscale/outputscale pair")
        targets[f"{semantic}_lengthscale"] = parameter_name(
            raw_lengthscale, f"{semantic} lengthscale")
        targets[f"{semantic}_outputscale"] = parameter_name(
            raw_outputscale, f"{semantic} outputscale")

    raw_noise = getattr(getattr(likelihood, "noise_covar", None),
                        "raw_noise", None)
    if raw_noise is None:
        raise S3GateError("S3 STOP: likelihood noise role is ambiguous")
    targets["noise"] = parameter_name(raw_noise, "noise")

    sites_by_parameter = {}
    for site in sites:
        entry = site_map.get(site)
        if entry is None or len(entry) < 2:
            raise S3GateError(
                f"S3 STOP: missing E1 parameter metadata for site {site}")
        sites_by_parameter.setdefault(entry[1], []).append(site)

    resolved = {}
    for role in S3_SEMANTIC_SITE_ROLES:
        matches = sites_by_parameter.get(targets[role], [])
        if len(matches) != 1:
            raise S3GateError(
                f"S3 STOP: site-role ambiguity for {role}: {matches}")
        resolved[role] = matches[0]
    if set(resolved.values()) != set(sites):
        raise S3GateError(
            "S3 STOP: resolved semantic roles do not cover the seven-site "
            "E1 inventory exactly")
    return S3SiteRoles(**resolved)


def _seven_vector(value, label="S3 vector") -> torch.Tensor:
    value = torch.as_tensor(value, dtype=torch.float64)
    if value.ndim == 0 or value.shape[-1] != 7:
        raise ValueError(f"{label} must have final dimension 7")
    if not bool(torch.isfinite(value).all()):
        raise ValueError(f"{label} must be finite")
    return value


def _log_d(z: torch.Tensor) -> torch.Tensor:
    return torch.logsumexp(torch.stack(
        (torch.zeros_like(z[..., 4]), z[..., 4], z[..., 5]), dim=-1),
        dim=-1)


def z_to_u(z) -> torch.Tensor:
    """Map z to semantic E1 log coordinates.

    The returned semantic order is lengthscales (trend, seasonal, medium),
    outputscales (trend, seasonal, medium), then noise.
    """
    z = _seven_vector(z, "z")
    log_d = _log_d(z)
    s, a_t, a_s, ratio = z[..., 3], z[..., 4], z[..., 5], z[..., 6]
    return torch.stack((
        z[..., 0], z[..., 1], z[..., 2],
        s + a_t - log_d,
        s + a_s - log_d,
        s - log_d,
        s + ratio,
    ), dim=-1)


def u_to_z(u) -> torch.Tensor:
    """Inverse semantic E1-log-coordinate map."""
    u = _seven_vector(u, "u")
    s = torch.logsumexp(u[..., 3:6], dim=-1)
    return torch.stack((
        u[..., 0], u[..., 1], u[..., 2], s,
        u[..., 3] - u[..., 5],
        u[..., 4] - u[..., 5],
        u[..., 6] - s,
    ), dim=-1)


def z_to_theta(z) -> torch.Tensor:
    """Map z to constrained M0 hyperparameters in semantic site order."""
    return torch.exp(z_to_u(z))


def theta_to_z(theta) -> torch.Tensor:
    """Inverse constrained semantic map."""
    theta = _seven_vector(theta, "theta")
    if not bool((theta > 0.0).all()):
        raise ValueError("theta must be strictly positive")
    return u_to_z(torch.log(theta))


def log_abs_det_u_from_z(z) -> torch.Tensor:
    """Analytic ``log|det du/dz| = 0`` (volume preserving)."""
    z = _seven_vector(z, "z")
    return torch.zeros_like(z[..., 0])


def log_abs_det_theta_from_z(z) -> torch.Tensor:
    """Analytic constrained-coordinate Jacobian log determinant."""
    z = _seven_vector(z, "z")
    return (
        z[..., 0] + z[..., 1] + z[..., 2]
        + 4.0 * z[..., 3] + z[..., 6] + z[..., 4] + z[..., 5]
        - 3.0 * _log_d(z)
    )


def autodiff_log_abs_det(map_fn, z) -> torch.Tensor:
    """Autodiff ``slogdet`` reference for one seven-vector state."""
    z = _seven_vector(z, "z")
    if z.ndim != 1:
        raise ValueError("autodiff slogdet reference accepts one state")
    jacobian = torch.autograd.functional.jacobian(map_fn, z)
    sign, logabsdet = torch.linalg.slogdet(jacobian)
    if float(sign) == 0.0:
        return torch.full_like(logabsdet, -torch.inf)
    return logabsdet


def _semantic_to_e1_state(values: torch.Tensor, e1,
                          roles: S3SiteRoles) -> dict[str, torch.Tensor]:
    values = _seven_vector(values)
    semantic = dict(zip(S3_SEMANTIC_SITE_ROLES, values.unbind(dim=-1)))
    by_site = {
        getattr(roles, role): value for role, value in semantic.items()
    }
    leading = tuple(values.shape[:-1])
    state = {}
    for site in e1.sites:
        template = torch.as_tensor(e1.init_params[site])
        if template.numel() != 1:
            raise S3GateError(
                f"S3 STOP: site {site} is not scalar ({tuple(template.shape)})")
        state[site] = by_site[site].reshape(leading + tuple(template.shape))
    return state


def _e1_state_to_semantic(state: Mapping[str, torch.Tensor], e1,
                          roles: S3SiteRoles) -> torch.Tensor:
    values = []
    leading = None
    for role in S3_SEMANTIC_SITE_ROLES:
        site = getattr(roles, role)
        template = torch.as_tensor(e1.init_params[site])
        if template.numel() != 1:
            raise S3GateError(
                f"S3 STOP: site {site} is not scalar ({tuple(template.shape)})")
        value = torch.as_tensor(state[site], dtype=torch.float64)
        trailing = len(template.shape)
        this_leading = tuple(value.shape[:-trailing]) if trailing else tuple(value.shape)
        if leading is None:
            leading = this_leading
        elif this_leading != leading:
            raise ValueError("E1 state sites have inconsistent leading shapes")
        values.append(value.reshape(this_leading))
    return torch.stack(values, dim=-1)


def z_to_e1_u(z, e1, roles: S3SiteRoles | None = None):
    """Map z to a dict emitted in ``e1.sites`` order."""
    roles = resolve_m0_site_roles(e1) if roles is None else roles
    return _semantic_to_e1_state(z_to_u(z), e1, roles)


def e1_u_to_z(u, e1, roles: S3SiteRoles | None = None):
    """Map an E1 site dict to z through resolved semantic roles."""
    roles = resolve_m0_site_roles(e1) if roles is None else roles
    return u_to_z(_e1_state_to_semantic(u, e1, roles))


def z_to_e1_theta(z, e1, roles: S3SiteRoles | None = None):
    """Map z directly to a constrained dict in ``e1.sites`` order."""
    roles = resolve_m0_site_roles(e1) if roles is None else roles
    return _semantic_to_e1_state(z_to_theta(z), e1, roles)


def e1_theta_to_z(theta, e1, roles: S3SiteRoles | None = None):
    """Map a constrained E1 site dict to z."""
    roles = resolve_m0_site_roles(e1) if roles is None else roles
    return theta_to_z(_e1_state_to_semantic(theta, e1, roles))


def s3_potential(e1, z, roles: S3SiteRoles | None = None):
    """V3(z) = V_E1(u(z)); the unconstrained Jacobian log-det is zero."""
    roles = resolve_m0_site_roles(e1) if roles is None else roles
    return e1.potential_fn(z_to_e1_u(z, e1, roles)) - log_abs_det_u_from_z(z)


def frozen_s3_states(e1, roles: S3SiteRoles | None = None):
    """Return the execution-complete rev-5 §5.2 battery of 33 z states."""
    roles = resolve_m0_site_roles(e1) if roles is None else roles
    z_map = e1_u_to_z(e1.init_params, e1, roles).detach()
    states = [("map", z_map.clone())]

    for sigma in S3_NEIGHBORHOOD_SIGMAS:
        for seed in S3_NEIGHBORHOOD_SEEDS:
            generator = torch.Generator().manual_seed(seed)
            offset = torch.randn(
                z_map.shape, generator=generator, dtype=torch.float64,
                device=z_map.device)
            states.append((
                f"map+{sigma}sd/seed{seed}", z_map + sigma * offset))

    priors = {entry[0]: entry[2] for entry in e1._model.named_priors()}
    if set(priors) != set(e1.sites):
        raise S3GateError("S3 STOP: prior/site inventory mismatch")
    with torch.random.fork_rng():
        for seed in S3_PRIOR_DRAW_SEEDS:
            torch.manual_seed(seed)
            theta = {site: priors[site].sample() for site in e1.sites}
            states.append((
                f"prior/seed{seed}", e1_theta_to_z(theta, e1, roles)))

    def offset_state(label, mutate):
        state = z_map.clone()
        mutate(state)
        states.append((label, state))

    offset_state("r-15", lambda z: z.__setitem__(6, z[6] - 15.0))
    offset_state("r+8", lambda z: z.__setitem__(6, z[6] + 8.0))
    offset_state("lengthscales+8", lambda z: z.__setitem__(
        slice(0, 3), z[0:3] + 8.0))
    offset_state("lengthscales-8", lambda z: z.__setitem__(
        slice(0, 3), z[0:3] - 8.0))
    offset_state("scale+8", lambda z: z.__setitem__(3, z[3] + 8.0))
    offset_state("scale-8", lambda z: z.__setitem__(3, z[3] - 8.0))

    def near_singular(z):
        z[0:3] += 8.0
        z[3] += 8.0
        z[6] -= 15.0

    offset_state("near_singular", near_singular)
    for a_t, a_s in ((-15.0, 0.0), (0.0, -15.0), (15.0, 15.0),
                     (15.0, -15.0), (-15.0, 15.0)):
        state = z_map.clone()
        state[4], state[5] = a_t, a_s
        states.append((f"simplex/{a_t:g},{a_s:g}", state))

    if len(states) != S3_N_STATES:
        raise AssertionError(
            f"frozen S3 state generator made {len(states)}, expected "
            f"{S3_N_STATES}")
    return states


def _max_abs(value: torch.Tensor) -> float:
    return float(torch.as_tensor(value).abs().max())


def _state_equivalence_metrics(e1, z, roles: S3SiteRoles):
    z = _seven_vector(z, "z state").detach().clone()
    u = z_to_u(z)
    theta = z_to_theta(z)

    u_slogdet = abs(float(log_abs_det_u_from_z(z)) - float(
        autodiff_log_abs_det(z_to_u, z)))
    theta_slogdet = abs(float(log_abs_det_theta_from_z(z)) - float(
        autodiff_log_abs_det(z_to_theta, z)))

    z_from_u = u_to_z(u)
    z_from_theta = theta_to_z(theta)
    u_roundtrip = max(
        _max_abs(z_from_u - z),
        _max_abs(z_to_u(z_from_u) - u),
    )
    theta_roundtrip = max(
        _max_abs(z_from_theta - z),
        _max_abs(z_to_theta(z_from_theta) - theta),
    )

    e1_u = z_to_e1_u(z, e1, roles)
    e1_value = e1.potential_fn(e1_u)
    value_s3 = s3_potential(e1, z, roles)
    density_error = abs(float(value_s3 - e1_value))
    density_limit = S3_DENSITY_TOL * max(1.0, abs(float(e1_value)))

    z_required = z.detach().clone().requires_grad_(True)
    value = s3_potential(e1, z_required, roles)
    gradient_s3, = torch.autograd.grad(value, z_required)

    u_required = z_to_u(z).detach().clone().requires_grad_(True)
    e1_at_u = e1.potential_fn(
        _semantic_to_e1_state(u_required, e1, roles))
    gradient_e1, = torch.autograd.grad(e1_at_u, u_required)
    jacobian = torch.autograd.functional.jacobian(z_to_u, z)
    chained = jacobian.T @ gradient_e1
    gradient_error = _max_abs(gradient_s3 - chained)
    gradient_scale = max(1.0, _max_abs(chained))
    gradient_limit = S3_GRAD_ABS + S3_GRAD_REL * gradient_scale

    return {
        "u_slogdet_error": u_slogdet,
        "theta_slogdet_error": theta_slogdet,
        "u_roundtrip_error": u_roundtrip,
        "theta_roundtrip_error": theta_roundtrip,
        "density_error": density_error,
        "density_limit": density_limit,
        "gradient_error": gradient_error,
        "gradient_limit": gradient_limit,
    }


def validate_s3_equivalence(e1) -> S3EquivalenceResult:
    """Run all frozen S3 gates over all 33 states or STOP the arm."""
    roles = resolve_m0_site_roles(e1)
    states = frozen_s3_states(e1, roles)
    executed = []
    metrics = []
    failures = []
    for label, z in states:
        executed.append(label)
        try:
            observed = _state_equivalence_metrics(e1, z, roles)
            metrics.append(observed)
        except Exception as error:
            failures.append(f"{label}: evaluation failed: {error}")
            continue
        checks = (
            ("u slogdet", observed["u_slogdet_error"], S3_SLOGDET_TOL),
            ("theta slogdet", observed["theta_slogdet_error"], S3_SLOGDET_TOL),
            ("u roundtrip", observed["u_roundtrip_error"], S3_ROUNDTRIP_TOL),
            ("theta roundtrip", observed["theta_roundtrip_error"],
             S3_ROUNDTRIP_TOL),
            ("density", observed["density_error"], observed["density_limit"]),
            ("gradient", observed["gradient_error"],
             observed["gradient_limit"]),
        )
        for name, error, limit in checks:
            if not np.isfinite(error) or error > limit:
                failures.append(
                    f"{label}: {name} error {error:.12g} exceeds "
                    f"{limit:.12g}")

    if len(executed) != S3_N_STATES or len(set(executed)) != S3_N_STATES:
        failures.append(
            f"execution completeness failed: {len(executed)} labels, "
            f"{len(set(executed))} unique")
    if failures:
        raise S3GateError("S3 STOP: " + "; ".join(failures))

    def maximum(key):
        return max((entry[key] for entry in metrics), default=0.0)

    return S3EquivalenceResult(
        executed_labels=tuple(executed),
        max_u_slogdet_error=maximum("u_slogdet_error"),
        max_theta_slogdet_error=maximum("theta_slogdet_error"),
        max_u_roundtrip_error=maximum("u_roundtrip_error"),
        max_theta_roundtrip_error=maximum("theta_roundtrip_error"),
        max_density_error=maximum("density_error"),
        max_gradient_error=maximum("gradient_error"),
    )


def fit_hmc_e1_reparam(
        model, likelihood, train_x, train_y,
        n_samples=500, n_warmup=200, verbose=True, seed=None,
        init_to_map=True, max_tree_depth=10, return_diagnostics=False,
        jitter=DEFAULT_JITTER, init_values=None):
    """S3 pilot route: NUTS on the frozen M0 seven-coordinate map.

    The complete 33-state equivalence battery runs before the sampler route.
    PR B's tests replace NUTS/MCMC with deterministic mocks; no real chain is
    part of the S3 verification package.
    """
    import pyro

    if seed is not None:
        pyro.set_rng_seed(seed)
    e1 = build_e1_potential(
        model, likelihood, train_x, train_y, jitter=jitter,
        init_to_map=init_to_map, init_values=init_values)
    try:
        roles = resolve_m0_site_roles(e1)
        validate_s3_equivalence(e1)
    except Exception:
        model.eval()
        likelihood.eval()
        raise

    z_map = e1_u_to_z(e1.init_params, e1, roles).detach().clone()

    def potential_over_z(coords):
        return s3_potential(e1, coords[S3_COORDINATE], roles)

    def coords_to_theta(draws):
        theta = z_to_e1_theta(draws[S3_COORDINATE], e1, roles)
        return {
            site: theta[site].detach().numpy().reshape(-1)
            for site in e1.sites
        }

    return _run_e1_nuts_route(
        e1,
        potential_over_coords=potential_over_z,
        initial_params={S3_COORDINATE: z_map},
        coords_to_theta=coords_to_theta,
        # Diagnostics label the reported constrained sites (coords_to_theta's
        # output).  The raw sampler coordinate is a single flat "z" vector, so
        # site_names intentionally describes the reported θ sites, NOT the raw
        # pyro sample dict; nothing keys diagnostics by it.
        site_names=e1.sites,
        sampler_name="nuts_e1_s3",
        n_samples=n_samples,
        n_warmup=n_warmup,
        max_tree_depth=max_tree_depth,
        step_size=0.1,
        adapt_step_size=True,
        adapt_mass_matrix=True,
        target_accept_prob=0.8,
        jitter=jitter,
        verbose=verbose,
        return_diagnostics=return_diagnostics,
    )

