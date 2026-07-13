"""M2c S2 fixed MAP-Hessian metric (prereg v1.17, rev-5 §5.1).

The Hessian is formed only by central finite differences of the validated E1
first gradient.  No ``create_graph``/double-backward path is used.  Every
mass-convention check is fail-closed: if any gate fails, S2 is unavailable
and there is deliberately no identity-metric fallback.

The frozen synthetic Mauna structure currently supplies seven M0 sites.
Nine-site M1 coverage remains UNVERIFIED until the PR-C M1 builder exists;
this module does not claim or emulate it.
"""

from dataclasses import dataclass, field
from typing import Callable, Mapping, Sequence

import numpy as np
import torch

from .e1_potential import (
    _run_e1_nuts_route,
    build_e1_potential,
)
from .fit import DEFAULT_JITTER
from .m2c_freeze import DIRECTIONAL_EPS, DIRECTION_RNG_SEEDS
from .m2c_freeze_s2s3 import (
    S2_DIRECTIONAL_TOL,
    S2_EIG_FLOOR,
    S2_FD_STEP,
    S2_SKEW_TOL,
    S2_STABILITY_MULTIPLIERS,
    S2_STEP_STABILITY_TOL,
    S2_WHITENING_TOL,
)


torch.set_default_dtype(torch.float64)
S2_COORDINATE = "z"


class S2GateError(RuntimeError):
    """A mandatory rev-5 §5.1 gate failed; S2 must stop."""


@dataclass(frozen=True)
class S2FixedMetricResult:
    """Frozen S2 mass convention and its gate diagnostics.

    ``raw_hessian`` is the symmetrized base-step Hessian H.  ``hessian`` and
    ``mass_matrix`` are H_reg; the two names are intentionally equal because
    rev-5 freezes the *position-space mass* as H_reg, not its inverse.
    """

    raw_hessian: torch.Tensor
    hessian: torch.Tensor
    eigenvalues: torch.Tensor
    n_clipped: int
    mass_matrix: torch.Tensor
    inverse_mass_matrix: torch.Tensor
    whitener: torch.Tensor
    gradient_jacobian: torch.Tensor | None = None
    skew_error: float = np.nan
    step_stability_error: float = np.nan
    directional_errors: Mapping[int, float] = field(default_factory=dict)
    whitening_errors: tuple[float, float] = (np.nan, np.nan)


# Short alias for callers that do not need the strategy prefix.
FixedMetricResult = S2FixedMetricResult


def _as_vector(value) -> torch.Tensor:
    vector = torch.as_tensor(value, dtype=torch.float64)
    if vector.ndim != 1 or vector.numel() == 0:
        raise ValueError("S2 coordinates must be a nonempty one-dimensional vector")
    if not bool(torch.isfinite(vector).all()):
        raise ValueError("S2 coordinates must be finite")
    return vector


def _first_gradient(
        potential_fn: Callable[[torch.Tensor], torch.Tensor],
        vector: torch.Tensor) -> torch.Tensor:
    """Validated first gradient only (v1.8 §3; never ``create_graph``)."""
    required = vector.detach().clone().requires_grad_(True)
    value = potential_fn(required)
    if torch.as_tensor(value).numel() != 1:
        raise ValueError("S2 potential callable must return a scalar")
    gradient, = torch.autograd.grad(value, required)
    return gradient.detach()


def central_fd_hessian(
        potential_fn: Callable[[torch.Tensor], torch.Tensor],
        center,
        eta: float = S2_FD_STEP,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Return ``(C, H)`` from central FD of the first gradient.

    For coordinate j, ``h_j = eta * max(1, abs(center_j))`` and column j of
    C is the corresponding gradient difference.  H is ``(C + C.T) / 2``.
    This vector-callable surface keeps the numerical core hermetically
    testable with the seedless quadratic oracle.
    """
    center = _as_vector(center)
    eta = float(eta)
    if not np.isfinite(eta) or eta <= 0.0:
        raise ValueError("S2 finite-difference eta must be positive and finite")

    dimension = center.numel()
    columns = torch.empty(
        (dimension, dimension), dtype=torch.float64, device=center.device)
    for column in range(dimension):
        step = eta * max(1.0, abs(float(center[column])))
        plus = center.detach().clone()
        minus = center.detach().clone()
        plus[column] += step
        minus[column] -= step
        columns[:, column] = (
            _first_gradient(potential_fn, plus)
            - _first_gradient(potential_fn, minus)
        ) / (2.0 * step)
    hessian = 0.5 * (columns + columns.T)
    return columns, hessian


def _frobenius_relative(numerator: torch.Tensor,
                        denominator: torch.Tensor) -> float:
    scale = max(1.0, float(torch.linalg.matrix_norm(denominator, ord="fro")))
    return float(torch.linalg.matrix_norm(numerator, ord="fro")) / scale


def compute_fixed_metric(
        potential_fn: Callable[[torch.Tensor], torch.Tensor], center,
) -> S2FixedMetricResult:
    """Build and gate the S2 metric for an abstract vector potential.

    All rev-5 §5.1 checks are evaluated before returning.  A failure raises
    :class:`S2GateError`; flooring is used to make the matrix operations safe
    but can never authorize a raw Hessian with an eigenvalue below 1e-6.
    """
    center = _as_vector(center)
    by_multiplier = {}
    for multiplier in S2_STABILITY_MULTIPLIERS:
        by_multiplier[multiplier] = central_fd_hessian(
            potential_fn, center, eta=S2_FD_STEP * multiplier)

    columns, raw_hessian = by_multiplier[1.0]
    skew_error = _frobenius_relative(columns - columns.T, raw_hessian)
    stability_errors = [
        _frobenius_relative(
            by_multiplier[multiplier][1] - raw_hessian,
            raw_hessian,
        )
        for multiplier in S2_STABILITY_MULTIPLIERS
        if multiplier != 1.0
    ]
    stability_error = max(stability_errors, default=0.0)

    directional_errors = {}
    center_value = potential_fn(center)
    for seed in DIRECTION_RNG_SEEDS:
        rng = np.random.default_rng(seed)
        direction_np = rng.standard_normal(center.numel())
        direction_np /= np.linalg.norm(direction_np)
        direction = torch.as_tensor(
            direction_np, dtype=torch.float64, device=center.device)
        plus = potential_fn(center + DIRECTIONAL_EPS * direction)
        minus = potential_fn(center - DIRECTIONAL_EPS * direction)
        second = float(
            (plus - 2.0 * center_value + minus) / DIRECTIONAL_EPS ** 2)
        # dᵀHd vs the second directional FD of U.  ``raw_hessian`` is the Hessian
        # of the potential U itself, so ``quadratic ≈ +second`` here.  PR-A's
        # profile gate (profile_integration.py) compares ``quadratic + second``
        # because its curvature is K = −H of a *maximized* objective; both forms
        # are self-consistent under their respective sign conventions.
        quadratic = float(direction @ raw_hessian @ direction)
        directional_errors[seed] = (
            abs(quadratic - second) / max(1.0, abs(second)))

    failures = []
    if not np.isfinite(skew_error) or skew_error > S2_SKEW_TOL:
        failures.append(
            f"raw skew {skew_error:.12g} exceeds {S2_SKEW_TOL:.12g}")
    if (not np.isfinite(stability_error)
            or stability_error > S2_STEP_STABILITY_TOL):
        failures.append(
            "step stability "
            f"{stability_error:.12g} exceeds {S2_STEP_STABILITY_TOL:.12g}")
    bad_directions = {
        seed: error for seed, error in directional_errors.items()
        if not np.isfinite(error) or error > S2_DIRECTIONAL_TOL
    }
    if bad_directions:
        failures.append(f"directional curvature failed: {bad_directions}")

    if not bool(torch.isfinite(raw_hessian).all()):
        raise S2GateError(
            "S2 STOP: Hessian is non-finite; no identity fallback")
    eigenvalues, eigenvectors = torch.linalg.eigh(raw_hessian)
    regularized_eigenvalues = torch.clamp(eigenvalues, min=S2_EIG_FLOOR)
    n_clipped = int((eigenvalues < S2_EIG_FLOOR).sum().item())
    hessian = (
        eigenvectors @ torch.diag(regularized_eigenvalues) @ eigenvectors.T)
    whitener = (
        eigenvectors @ torch.diag(regularized_eigenvalues.rsqrt()))
    inverse_mass = whitener @ whitener.T
    identity = torch.eye(
        center.numel(), dtype=torch.float64, device=center.device)
    whitening_left = float(torch.linalg.matrix_norm(
        whitener.T @ hessian @ whitener - identity, ord="fro"))
    whitening_right = float(torch.linalg.matrix_norm(
        hessian @ whitener @ whitener.T - identity, ord="fro"))

    if (not np.isfinite(whitening_left)
            or whitening_left > S2_WHITENING_TOL):
        failures.append(
            f"A.T H_reg A whitening error {whitening_left:.12g} exceeds "
            f"{S2_WHITENING_TOL:.12g}")
    if (not np.isfinite(whitening_right)
            or whitening_right > S2_WHITENING_TOL):
        failures.append(
            f"H_reg A A.T whitening error {whitening_right:.12g} exceeds "
            f"{S2_WHITENING_TOL:.12g}")

    lambda_min = float(eigenvalues[0])
    if (not np.isfinite(lambda_min) or lambda_min < S2_EIG_FLOOR
            or n_clipped != 0):
        failures.append(
            "raw Hessian fails S2 SPD requirement: "
            f"lambda_min={lambda_min:.12g}, n_clipped={n_clipped}; "
            f"required lambda_min >= {S2_EIG_FLOOR:.12g} and n_clipped == 0")

    if failures:
        raise S2GateError(
            "S2 STOP: " + "; ".join(failures) + "; no identity fallback")

    return S2FixedMetricResult(
        raw_hessian=raw_hessian.detach().clone(),
        hessian=hessian.detach().clone(),
        eigenvalues=eigenvalues.detach().clone(),
        n_clipped=n_clipped,
        mass_matrix=hessian.detach().clone(),
        inverse_mass_matrix=inverse_mass.detach().clone(),
        whitener=whitener.detach().clone(),
        gradient_jacobian=columns.detach().clone(),
        skew_error=skew_error,
        step_stability_error=stability_error,
        directional_errors=dict(directional_errors),
        whitening_errors=(whitening_left, whitening_right),
    )


def flatten_e1_state(state: Mapping[str, torch.Tensor],
                     sites: Sequence[str]) -> torch.Tensor:
    """Flatten a scalar-site E1 state in the authoritative site order."""
    sites = tuple(sites)
    if not sites:
        raise ValueError("E1 site inventory must be nonempty")
    return torch.cat([
        torch.as_tensor(state[site], dtype=torch.float64).reshape(-1)
        for site in sites
    ])


def unflatten_e1_state(vector: torch.Tensor,
                       template: Mapping[str, torch.Tensor],
                       sites: Sequence[str]) -> dict[str, torch.Tensor]:
    """Inverse of :func:`flatten_e1_state`, retaining leading draw axes."""
    vector = torch.as_tensor(vector, dtype=torch.float64)
    sites = tuple(sites)
    total = sum(torch.as_tensor(template[site]).numel() for site in sites)
    if vector.ndim == 0 or vector.shape[-1] != total:
        raise ValueError(
            f"flat E1 coordinate has final dimension {vector.shape[-1:]}, "
            f"expected {total}")
    leading = tuple(vector.shape[:-1])
    state = {}
    offset = 0
    for site in sites:
        shape = tuple(torch.as_tensor(template[site]).shape)
        size = torch.as_tensor(template[site]).numel()
        state[site] = vector[..., offset:offset + size].reshape(leading + shape)
        offset += size
    return state


def compute_s2_fixed_metric(e1) -> S2FixedMetricResult:
    """Compute S2 from an :class:`~bistar_gp.e1_potential.E1Potential`."""
    center = flatten_e1_state(e1.init_params, e1.sites)

    def flat_potential(vector):
        return e1.potential_fn(
            unflatten_e1_state(vector, e1.init_params, e1.sites))

    return compute_fixed_metric(flat_potential, center)


# Readable strategy-prefixed alias used by some integration callers.
build_s2_fixed_metric = compute_s2_fixed_metric


def fit_hmc_e1_fixed_metric(
        model, likelihood, train_x, train_y,
        n_samples=500, n_warmup=200, verbose=True, seed=None,
        init_to_map=True, max_tree_depth=10, return_diagnostics=False,
        jitter=DEFAULT_JITTER, init_values=None):
    """S2 pilot route: NUTS in MAP-Hessian-whitened E1 coordinates.

    The route is sampler-capable, but PR B verifies it only with mocked
    NUTS/MCMC.  The fixed position-space mass H_reg is represented by
    ``u = u_MAP + A z`` and identity-metric NUTS with
    ``adapt_mass_matrix=False`` (rev-5 §5.1); step-size adaptation remains on.
    """
    import pyro

    if seed is not None:
        pyro.set_rng_seed(seed)
    e1 = build_e1_potential(
        model, likelihood, train_x, train_y, jitter=jitter,
        init_to_map=init_to_map, init_values=init_values)
    try:
        metric = compute_s2_fixed_metric(e1)
    except Exception:
        model.eval()
        likelihood.eval()
        raise

    center = flatten_e1_state(e1.init_params, e1.sites)
    whitener = metric.whitener

    def z_to_flat_u(z):
        z = torch.as_tensor(z, dtype=torch.float64, device=center.device)
        return center + torch.matmul(z, whitener.T)

    def potential_over_z(coords):
        flat_u = z_to_flat_u(coords[S2_COORDINATE])
        return e1.potential_fn(
            unflatten_e1_state(flat_u, e1.init_params, e1.sites))

    def coords_to_theta(draws):
        state = unflatten_e1_state(
            z_to_flat_u(draws[S2_COORDINATE]), e1.init_params, e1.sites)
        return {
            site: e1.transforms[site].inv(state[site])
            .detach().numpy().reshape(-1)
            for site in e1.sites
        }

    return _run_e1_nuts_route(
        e1,
        potential_over_coords=potential_over_z,
        initial_params={
            S2_COORDINATE: torch.zeros_like(center, dtype=torch.float64)
        },
        coords_to_theta=coords_to_theta,
        # Diagnostics label the reported constrained sites (coords_to_theta's
        # output).  The raw sampler coordinate is a single flat "z" vector, so
        # site_names intentionally describes the reported θ sites, NOT the raw
        # pyro sample dict; nothing keys diagnostics by it.
        site_names=e1.sites,
        sampler_name="nuts_e1_s2",
        n_samples=n_samples,
        n_warmup=n_warmup,
        max_tree_depth=max_tree_depth,
        step_size=0.1,
        adapt_step_size=True,
        adapt_mass_matrix=False,
        target_accept_prob=0.8,
        jitter=jitter,
        verbose=verbose,
        return_diagnostics=return_diagnostics,
    )

