"""M2c profile-integration numerics frozen by prereg v1.17.

The grid, optimization, curvature, quadrature, and sensitivity algorithms in
this module implement rev-5 sections 1, 2b, 2c, and 4.  They are deliberately
model-agnostic: scientific profile evaluation is supplied by callers, while
the functions here can be tested with analytic synthetic oracles.
"""

from collections.abc import Callable, Mapping, Sequence
from typing import Any

import numpy as np
from scipy.optimize import minimize

from bistar_gp.m2c_freeze import (
    AGREE_DG_REL,
    AGREE_DU_INF,
    CAP_LADDER_LOWER_DIAGNOSTIC,
    CAP_LADDER_UPPER_DIAGNOSTIC,
    DIRECTIONAL_EPS,
    DIRECTIONAL_TOL,
    DIRECTION_RNG_SEEDS,
    EPS_DOMAIN,
    EPS_GRID,
    FULL_DOMAIN_HI,
    FULL_DOMAIN_LO,
    FULL_DOMAIN_N_NODES,
    FULL_DOMAIN_N_WITH_EDGES,
    HESS_H_CENTER,
    HESS_H_SWEEP,
    LBFGSB_FTOL,
    LBFGSB_GTOL,
    LBFGSB_MAXFUN,
    LBFGSB_MAXITER,
    LOGDET_STABILITY_TOL,
    PROFILE_GRID_BASE_HI,
    PROFILE_GRID_BASE_LO,
    PROFILE_GRID_BASE_N,
    PROFILE_GRID_RATIO,
    RCOND_MIN,
    REFINE_L_MAX,
    RESTART_JITTER_SCALE,
    RESTART_RNG_BASE,
    RETRY_FTOL,
    RETRY_GTOL,
    RETRY_MAXITER,
    SYMMETRY_TOL,
    TAU_STAT,
    TOY_BAND_EDGES,
)


_BAND_KEYS = ("P_noise_lo", "P_noise_mid", "P_noise_hi")


def _as_increasing_grid(grid: np.ndarray | Sequence[float]) -> np.ndarray:
    """Return a validated one-dimensional, finite, increasing grid."""

    array = np.asarray(grid, dtype=np.float64)
    if array.ndim != 1 or array.size < 2:
        raise ValueError("grid must be a one-dimensional array with at least two nodes")
    if not np.all(np.isfinite(array)):
        raise ValueError("grid nodes must be finite")
    if not np.all(np.diff(array) > 0.0):
        raise ValueError("grid nodes must be strictly increasing")
    return array


def base_grid() -> np.ndarray:
    """Return the frozen P3 40-node base grid (rev-5 section 1)."""

    grid = np.geomspace(
        PROFILE_GRID_BASE_LO,
        PROFILE_GRID_BASE_HI,
        PROFILE_GRID_BASE_N,
        dtype=np.float64,
    )
    ratios = grid[1:] / grid[:-1]
    assert np.allclose(ratios, PROFILE_GRID_RATIO, rtol=2e-15, atol=0.0)
    return grid


def full_domain_grid(
    band_edges: Sequence[float] = TOY_BAND_EDGES,
    with_edges: bool = True,
) -> np.ndarray:
    """Return the deterministic P3 lattice over the full frozen domain.

    The 182-node lattice has 76 nodes below the base grid, 40 base nodes,
    64 nodes above it, and the two exact cap nodes.  Requested band edges are
    inserted as exact, sorted-unique nodes.
    """

    lower = PROFILE_GRID_BASE_LO * PROFILE_GRID_RATIO ** -np.arange(
        1, 77, dtype=np.float64
    )
    upper = PROFILE_GRID_BASE_HI * PROFILE_GRID_RATIO ** np.arange(
        1, 65, dtype=np.float64
    )
    grid = np.sort(
        np.concatenate(
            (
                np.asarray([FULL_DOMAIN_LO], dtype=np.float64),
                lower,
                base_grid(),
                upper,
                np.asarray([FULL_DOMAIN_HI], dtype=np.float64),
            )
        )
    )
    assert grid.size == FULL_DOMAIN_N_NODES
    assert np.count_nonzero(grid == FULL_DOMAIN_LO) == 1
    assert np.count_nonzero(grid == FULL_DOMAIN_HI) == 1
    assert np.count_nonzero(
        (grid > FULL_DOMAIN_LO) & (grid < PROFILE_GRID_BASE_LO)
    ) == 76
    assert np.count_nonzero(
        (grid > PROFILE_GRID_BASE_HI) & (grid < FULL_DOMAIN_HI)
    ) == 64

    if with_edges:
        edges = np.asarray(tuple(band_edges), dtype=np.float64)
        if edges.ndim != 1 or not np.all(np.isfinite(edges)):
            raise ValueError("band edges must be a finite one-dimensional sequence")
        if np.any(edges <= FULL_DOMAIN_LO) or np.any(edges >= FULL_DOMAIN_HI):
            raise ValueError("band edges must lie strictly inside the full domain")
        grid = np.unique(np.concatenate((grid, edges)))
        if tuple(float(edge) for edge in edges) == TOY_BAND_EDGES:
            assert grid.size == FULL_DOMAIN_N_WITH_EDGES
    return grid


def cap_ladder_grids() -> dict[str, dict[float, np.ndarray]]:
    """Return the earlier decade-cap grids used only as a diagnostic trace.

    Upper pullbacks retain the full lower cap; lower pullbacks retain the full
    upper cap.  Exact stage caps and toy band edges are present in every grid
    where they lie in the retained domain.  These grids never encode a
    pass/fail verdict.
    """

    full = full_domain_grid()
    upper: dict[float, np.ndarray] = {}
    for cap in CAP_LADDER_UPPER_DIAGNOSTIC:
        stage = full[full < cap]
        upper[cap] = np.unique(
            np.concatenate((stage, np.asarray([cap], dtype=np.float64)))
        )

    lower: dict[float, np.ndarray] = {}
    for cap in CAP_LADDER_LOWER_DIAGNOSTIC:
        stage = full[full > cap]
        lower[cap] = np.unique(
            np.concatenate((np.asarray([cap], dtype=np.float64), stage))
        )
    return {"upper": upper, "lower": lower}


def nested_refine(grid: np.ndarray | Sequence[float]) -> np.ndarray:
    """Insert geometric midpoints while retaining every existing node."""

    coarse = _as_increasing_grid(grid)
    if not np.all(coarse > 0.0):
        raise ValueError("geometric refinement requires strictly positive nodes")
    midpoints = np.sqrt(coarse[:-1] * coarse[1:])
    refined = np.empty(2 * coarse.size - 1, dtype=np.float64)
    refined[0::2] = coarse
    refined[1::2] = midpoints
    assert refined.size == 2 * coarse.size - 1
    assert np.array_equal(refined[0::2], coarse)
    return refined


def refine_until_converged(
    band_masses_on_grid: Callable[[np.ndarray], Mapping[str, float]],
    grid0: np.ndarray | Sequence[float],
) -> dict[str, Any]:
    """Drive the frozen P3 nested-grid refinement convergence/STOP gate (rev-5 §1 L62-73).

    ``band_masses_on_grid`` is a caller-supplied callable ``grid -> {P_noise_lo/mid/hi}``. The
    real profile evaluator is supplied ONLY by the gated v1.18 recompute; hermetic tests pass a
    synthetic level-indexed callable. ``grid0`` is the converged level-0 grid (base + band edges +
    full-domain extension). Insert one nested geometric-midpoint level at a time and, at level ℓ,
    define δ_quad^(ℓ)(b) = |P_b(level ℓ) − P_b(level ℓ−1)|. Refine while
    max_b δ_quad^(ℓ)(b) ≥ EPS_GRID, up to REFINE_L_MAX levels; the reported δ_quad is
    δ_quad^(ℓ_final). If the largest band sensitivity is still ≥ EPS_GRID at level REFINE_L_MAX ⇒
    STOP (rev-5: no silent acceptance of an unconverged quadrature; this is a successive-grid
    sensitivity estimate, not a proven discretization bound).
    """

    grids = [_as_increasing_grid(grid0)]
    masses = [_band_values(band_masses_on_grid(grids[0]))]
    delta: dict[str, float] | None = None
    converged = False
    for _level in range(1, REFINE_L_MAX + 1):
        grids.append(nested_refine(grids[-1]))
        masses.append(_band_values(band_masses_on_grid(grids[-1])))
        delta = {
            key: abs(masses[-1][key] - masses[-2][key]) for key in _BAND_KEYS
        }
        if max(delta.values()) < EPS_GRID:
            converged = True
            break
    return {
        "delta_quad": delta,
        "converged": converged,
        "stop": not converged,
        "n_refinements": len(grids) - 1,
        "grids": grids,
        "masses_by_level": masses,
        "reason": (
            ""
            if converged
            else "grid refinement did not converge below EPS_GRID within "
            f"REFINE_L_MAX={REFINE_L_MAX}"
        ),
    }


def _validated_density_and_grid(
    m: np.ndarray | Sequence[float],
    grid: np.ndarray | Sequence[float],
) -> tuple[np.ndarray, np.ndarray]:
    nodes = _as_increasing_grid(grid)
    density = np.asarray(m, dtype=np.float64)
    if density.shape != nodes.shape:
        raise ValueError("density and grid must have the same one-dimensional shape")
    if not np.all(np.isfinite(density)) or np.any(density < 0.0):
        raise ValueError("density values must be finite and nonnegative")
    return density, nodes


def linear_interpolant_edge_value(
    m: np.ndarray | Sequence[float],
    grid: np.ndarray | Sequence[float],
    edge: float,
) -> float:
    """Evaluate the grid's piecewise-linear density at an edge node."""

    density, nodes = _validated_density_and_grid(m, grid)
    edge = float(edge)
    if not np.isfinite(edge) or edge < nodes[0] or edge > nodes[-1]:
        raise ValueError("edge must lie inside the grid domain")
    exact = np.flatnonzero(nodes == edge)
    if exact.size:
        return float(density[exact[0]])
    right = int(np.searchsorted(nodes, edge))
    left = right - 1
    weight = (edge - nodes[left]) / (nodes[right] - nodes[left])
    return float(density[left] + (density[right] - density[left]) * weight)


def split_trapezoids_at_edges(
    m: np.ndarray | Sequence[float],
    grid: np.ndarray | Sequence[float],
    band_edges: Sequence[float],
) -> tuple[np.ndarray, np.ndarray]:
    """Insert edge nodes with values from the existing linear interpolant."""

    density, nodes = _validated_density_and_grid(m, grid)
    edges = np.asarray(tuple(band_edges), dtype=np.float64)
    if edges.ndim != 1 or not np.all(np.isfinite(edges)):
        raise ValueError("band edges must be a finite one-dimensional sequence")
    if np.any(edges < nodes[0]) or np.any(edges > nodes[-1]):
        raise ValueError("band edges must lie inside the grid domain")

    inserted_values = np.asarray(
        [linear_interpolant_edge_value(density, nodes, edge) for edge in edges],
        dtype=np.float64,
    )
    combined_grid = np.concatenate((nodes, edges))
    combined_density = np.concatenate((density, inserted_values))
    order = np.argsort(combined_grid, kind="mergesort")
    combined_grid = combined_grid[order]
    combined_density = combined_density[order]
    keep = np.concatenate(([True], np.diff(combined_grid) != 0.0))
    return combined_density[keep], combined_grid[keep]


def total_preservation_under_edge_split(
    m: np.ndarray | Sequence[float],
    grid: np.ndarray | Sequence[float],
    band_edges: Sequence[float],
) -> dict[str, Any]:
    """Report the invariant trapezoid total before and after edge splitting."""

    density, nodes = _validated_density_and_grid(m, grid)
    split_m, split_grid = split_trapezoids_at_edges(density, nodes, band_edges)
    total_before = float(np.trapz(density, nodes))
    total_after = float(np.trapz(split_m, split_grid))
    return {
        "m": split_m,
        "grid": split_grid,
        "total_before": total_before,
        "total_after": total_after,
        "difference": total_after - total_before,
    }


def band_masses(
    logm: np.ndarray | Sequence[float],
    grid: np.ndarray | Sequence[float],
    band_edges: Sequence[float],
) -> dict[str, Any]:
    """Integrate the three profile bands as a float-safe partition.

    Band edges must already be exact grid nodes.  The normalization total is
    the sum of the three inclusive band integrals, never a separate whole-grid
    integration, so no straddling trapezoid can be omitted.
    """

    nodes = _as_increasing_grid(grid)
    values = np.asarray(logm, dtype=np.float64)
    if values.shape != nodes.shape:
        raise ValueError("logm and grid must have the same one-dimensional shape")
    if np.any(np.isnan(values)) or np.any(np.isposinf(values)):
        raise ValueError("logm may contain -inf, but not NaN or +inf")
    finite = np.isfinite(values)
    if not np.any(finite):
        raise ValueError("logm must contain at least one finite value")

    edges = np.asarray(tuple(band_edges), dtype=np.float64)
    if edges.shape != (2,) or not np.all(np.diff(edges) > 0.0):
        raise ValueError("exactly two strictly increasing band edges are required")
    edge_indices: list[int] = []
    for edge in edges:
        matches = np.flatnonzero(nodes == edge)
        assert matches.size == 1, "each band edge must already be an exact grid node"
        edge_indices.append(int(matches[0]))
    if edge_indices[0] == 0 or edge_indices[1] == nodes.size - 1:
        raise ValueError("band edges must lie strictly inside the grid domain")

    density = np.zeros_like(values)
    density[finite] = np.exp(values[finite] - np.max(values[finite]))
    boundaries = (0, edge_indices[0], edge_indices[1], nodes.size - 1)
    integrals = np.asarray(
        [
            np.trapz(
                density[boundaries[index] : boundaries[index + 1] + 1],
                nodes[boundaries[index] : boundaries[index + 1] + 1],
            )
            for index in range(3)
        ],
        dtype=np.float64,
    )
    total = float(np.sum(integrals, dtype=np.float64))
    if not np.isfinite(total) or total <= 0.0:
        raise ValueError("profile density must have positive finite integrated mass")
    probabilities = integrals / total
    return {
        **{key: float(probabilities[index]) for index, key in enumerate(_BAND_KEYS)},
        "band_int": integrals,
        "total": total,
    }


def quantile_exact_quadratic(
    m: np.ndarray | Sequence[float],
    grid: np.ndarray | Sequence[float],
    q: float,
) -> float:
    """Invert the exact CDF of a piecewise-linear density."""

    density, nodes = _validated_density_and_grid(m, grid)
    q = float(q)
    if not np.isfinite(q) or q < 0.0 or q > 1.0:
        raise ValueError("q must be finite and lie in [0, 1]")
    if q == 0.0:
        return float(nodes[0])
    if q == 1.0:
        return float(nodes[-1])

    widths = np.diff(nodes)
    interval_mass = 0.5 * (density[:-1] + density[1:]) * widths
    cumulative = np.concatenate(
        (np.asarray([0.0], dtype=np.float64), np.cumsum(interval_mass))
    )
    total = float(cumulative[-1])
    if not np.isfinite(total) or total <= 0.0:
        raise ValueError("density must have positive finite integrated mass")
    target = q * total
    right_node = int(np.searchsorted(cumulative, target, side="left"))
    interval = max(0, right_node - 1)
    interval = min(interval, nodes.size - 2)
    needed = target - cumulative[interval]
    width = widths[interval]
    m_left = density[interval]
    slope = (density[interval + 1] - m_left) / width

    if slope == 0.0:
        if m_left == 0.0:
            raise ValueError("quantile falls in a zero-mass segment")
        offset = needed / m_left
    else:
        discriminant = m_left * m_left + 2.0 * slope * needed
        if discriminant < 0.0 and np.isclose(discriminant, 0.0):
            discriminant = 0.0
        if discriminant < 0.0:
            raise ArithmeticError("negative discriminant in quadratic CDF inversion")
        denominator = m_left + np.sqrt(discriminant)
        if denominator != 0.0:
            offset = 2.0 * needed / denominator
        else:
            offset = (-m_left + np.sqrt(discriminant)) / slope
    if offset < -1e-12 or offset > width + 1e-12:
        raise ArithmeticError("quadratic CDF root lies outside its interval")
    return float(nodes[interval] + np.clip(offset, 0.0, width))


def optimize_conditional(
    neg_g: Callable[[np.ndarray], float],
    neg_grad: Callable[[np.ndarray], np.ndarray],
    u0_warm: np.ndarray | Sequence[float],
    u0_mode: np.ndarray | Sequence[float],
) -> dict[str, Any]:
    """Apply the frozen two-start L-BFGS-B conditional-optimizer gate."""

    warm = np.asarray(u0_warm, dtype=np.float64)
    mode = np.asarray(u0_mode, dtype=np.float64)
    if warm.ndim != 1 or mode.shape != warm.shape or warm.size == 0:
        raise ValueError("optimizer starts must be nonempty vectors of equal shape")
    if not np.all(np.isfinite(warm)) or not np.all(np.isfinite(mode)):
        raise ValueError("optimizer starts must be finite")

    options = {
        "maxiter": LBFGSB_MAXITER,
        "maxfun": LBFGSB_MAXFUN,
        "ftol": LBFGSB_FTOL,
        "gtol": LBFGSB_GTOL,
    }
    restart_count = 0
    records: list[dict[str, Any]] = []
    for index, (label, start) in enumerate((("warm", warm), ("mode", mode))):
        result = minimize(
            neg_g,
            start.copy(),
            jac=neg_grad,
            method="L-BFGS-B",
            options=options,
        )
        if int(result.status) != 0:
            restart_count += 1
            rng = np.random.default_rng(RESTART_RNG_BASE + index)
            jittered = start + RESTART_JITTER_SCALE * rng.standard_normal(start.size)
            result = minimize(
                neg_g,
                jittered,
                jac=neg_grad,
                method="L-BFGS-B",
                options=options,
            )

        u_opt = np.asarray(result.x, dtype=np.float64)
        reported_success = int(result.status) == 0 and bool(
            getattr(result, "success", True)
        )
        g_value = float(-np.asarray(neg_g(u_opt), dtype=np.float64))
        grad_g = -np.asarray(neg_grad(u_opt), dtype=np.float64)
        finite = bool(
            u_opt.shape == start.shape
            and np.all(np.isfinite(u_opt))
            and np.isfinite(g_value)
            and grad_g.shape == start.shape
            and np.all(np.isfinite(grad_g))
        )
        grad_inf = float(np.linalg.norm(grad_g, ord=np.inf)) if finite else np.inf
        stationary = bool(finite and grad_inf <= TAU_STAT)
        accepted = bool(reported_success and finite and stationary)
        records.append(
            {
                "label": label,
                "u": u_opt,
                "g": g_value,
                "grad_inf_norm": grad_inf,
                "status": int(result.status),
                "reported_success": reported_success,
                "finite": finite,
                "stationary": stationary,
                "accepted": accepted,
                "message": str(result.message),
            }
        )

    both_success = bool(all(record["accepted"] for record in records))
    comparable = bool(all(record["finite"] for record in records))
    if comparable:
        g_scale = max(1.0, *(abs(record["g"]) for record in records))
        agree_g = abs(records[0]["g"] - records[1]["g"]) <= AGREE_DG_REL * g_scale
        agree_u = (
            np.linalg.norm(records[0]["u"] - records[1]["u"], ord=np.inf)
            <= AGREE_DU_INF
        )
        agree = bool(agree_g and agree_u)
    else:
        agree_g = False
        agree_u = False
        agree = False

    finite_records = [record for record in records if record["finite"]]
    best = max(finite_records, key=lambda record: record["g"]) if finite_records else None
    stop = not (both_success and agree)
    failures: list[str] = []
    for record in records:
        if not record["reported_success"]:
            failures.append(f"{record['label']} optimizer failed")
        elif not record["finite"]:
            failures.append(f"{record['label']} result is non-finite")
        elif not record["stationary"]:
            failures.append(f"{record['label']} result is non-stationary")
    if both_success and not agree_g:
        failures.append("start objective values disagree")
    if both_success and not agree_u:
        failures.append("start optima disagree")

    return {
        "u_star": None if best is None else best["u"].copy(),
        "g_star": np.nan if best is None else float(best["g"]),
        "grad_inf_norm": np.inf if best is None else float(best["grad_inf_norm"]),
        "both_success": both_success,
        "agree": agree,
        "agree_g": bool(agree_g),
        "agree_u": bool(agree_u),
        "restart_count": restart_count,
        "stop": stop,
        "reason": "; ".join(failures),
        "starts": {record["label"]: record for record in records},
    }


def _curvature_evaluation(
    g: Callable[[np.ndarray], float],
    grad: Callable[[np.ndarray], np.ndarray],
    u_star: np.ndarray,
    nuisance_order: tuple[str, ...],
) -> dict[str, Any]:
    dimension = u_star.size
    identity = np.eye(dimension, dtype=np.float64)
    raw_by_h: dict[float, np.ndarray] = {}
    symmetric_by_h: dict[float, np.ndarray] = {}
    logdet_by_h: dict[float, float] = {}
    for h in HESS_H_SWEEP:
        hessian = np.empty((dimension, dimension), dtype=np.float64)
        for column in range(dimension):
            plus = np.asarray(grad(u_star + h * identity[column]), dtype=np.float64)
            minus = np.asarray(grad(u_star - h * identity[column]), dtype=np.float64)
            if plus.shape != u_star.shape or minus.shape != u_star.shape:
                raise ValueError("gradient callable returned the wrong shape")
            hessian[:, column] = (plus - minus) / (2.0 * h)
        raw = -hessian
        curvature = 0.5 * (raw + raw.T)
        raw_by_h[h] = raw
        symmetric_by_h[h] = curvature
        sign, logabsdet = np.linalg.slogdet(curvature)
        logdet_by_h[h] = float(logabsdet) if sign != 0 else -np.inf

    raw_center = raw_by_h[HESS_H_CENTER]
    curvature = symmetric_by_h[HESS_H_CENTER]
    symmetry_error = float(
        np.linalg.norm(raw_center - raw_center.T, ord="fro")
        / max(1.0, np.linalg.norm(raw_center, ord="fro"))
    )
    symmetry_ok = bool(np.isfinite(symmetry_error) and symmetry_error <= SYMMETRY_TOL)

    center_logdet = logdet_by_h[HESS_H_CENTER]
    if np.isfinite(center_logdet):
        logdet_errors = {
            h: abs(value - center_logdet) / max(1.0, abs(center_logdet))
            for h, value in logdet_by_h.items()
            if h != HESS_H_CENTER
        }
        logdet_error = float(max(logdet_errors.values(), default=0.0))
    else:
        logdet_errors = {
            h: np.inf for h in HESS_H_SWEEP if h != HESS_H_CENTER
        }
        logdet_error = np.inf
    logdet_stable = bool(
        np.isfinite(logdet_error) and logdet_error <= LOGDET_STABILITY_TOL
    )

    g_center = float(g(u_star))
    # Stationarity of the point the gate evaluates curvature at is mandatory
    # (rev-5 §2b L112-117: never replaced by any other check). It must be
    # re-verified whenever the gate itself re-optimizes u* (the §2c retry),
    # because a SciPy status==0 termination (e.g. on ftol) is not a stationarity
    # certificate — a non-stationary but well-conditioned SPD point would
    # otherwise be silently accepted.
    grad_center = np.asarray(grad(u_star), dtype=np.float64)
    grad_inf_norm = (
        float(np.linalg.norm(grad_center, ord=np.inf))
        if grad_center.shape == u_star.shape and np.all(np.isfinite(grad_center))
        else np.inf
    )
    stationary = bool(np.isfinite(grad_inf_norm) and grad_inf_norm <= TAU_STAT)

    directional_errors: dict[int, float] = {}
    directional_second: dict[int, float] = {}
    for seed in DIRECTION_RNG_SEEDS:
        rng = np.random.default_rng(seed)
        direction = rng.standard_normal(dimension)
        direction /= np.linalg.norm(direction)
        second = float(
            (
                g(u_star + DIRECTIONAL_EPS * direction)
                - 2.0 * g_center
                + g(u_star - DIRECTIONAL_EPS * direction)
            )
            / DIRECTIONAL_EPS**2
        )
        quadratic = float(direction @ curvature @ direction)
        error = abs(quadratic + second) / max(1.0, abs(second))
        directional_second[seed] = second
        directional_errors[seed] = float(error)
    directional_ok = bool(
        all(
            np.isfinite(error) and error <= DIRECTIONAL_TOL
            for error in directional_errors.values()
        )
    )

    eigenvalues = np.linalg.eigvalsh(curvature)
    lambda_min = float(eigenvalues[0])
    lambda_max = float(eigenvalues[-1])
    spd = bool(
        np.all(np.isfinite(eigenvalues))
        and lambda_min > 0.0
        and lambda_max > 0.0
    )
    rcond = float(lambda_min / lambda_max) if lambda_max != 0.0 else np.nan
    conditioning_ok = bool(spd and np.isfinite(rcond) and rcond >= RCOND_MIN)
    stop = not (
        stationary
        and symmetry_ok
        and logdet_stable
        and directional_ok
        and conditioning_ok
    )

    failures = []
    if not stationary:
        failures.append("u_star is non-stationary")
    if not symmetry_ok:
        failures.append("pre-symmetrization check failed")
    if not logdet_stable:
        failures.append("logdet stability check failed")
    if not directional_ok:
        failures.append("directional curvature check failed")
    if not spd:
        failures.append("curvature is not strictly SPD")
    elif not conditioning_ok:
        failures.append("curvature rcond is below the frozen minimum")

    return {
        "K": curvature,
        "eigenvalues": eigenvalues,
        "logdet": center_logdet,
        "rcond": rcond,
        "spd": spd,
        "conditioning_ok": conditioning_ok,
        "stationary": stationary,
        "grad_inf_norm": grad_inf_norm,
        "symmetry_ok": symmetry_ok,
        "symmetry_error": symmetry_error,
        "logdet_stable": logdet_stable,
        "logdet_stability_error": logdet_error,
        "logdet_by_h": logdet_by_h,
        "directional_ok": directional_ok,
        "directional_errors": directional_errors,
        "directional_second_differences": directional_second,
        "nuisance_order": nuisance_order,
        "u_star": u_star.copy(),
        "stop": stop,
        "reason": "; ".join(failures),
    }


def curvature_gate(
    g: Callable[[np.ndarray], float],
    grad: Callable[[np.ndarray], np.ndarray],
    u_star: np.ndarray | Sequence[float],
    nuisance_order: Sequence[str],
) -> dict[str, Any]:
    """Apply the rev-5 finite-difference curvature gate without flooring.

    A failed SPD/rcond check triggers exactly one tighter re-optimization and
    a complete gate re-evaluation.  The other diagnostics are mandatory but,
    per rev-5 section 2c, do not independently authorize a retry.
    """

    optimum = np.asarray(u_star, dtype=np.float64)
    order = tuple(nuisance_order)
    if optimum.ndim != 1 or optimum.size == 0 or len(order) != optimum.size:
        raise ValueError("u_star and nuisance_order must describe the same nonempty vector")
    if not np.all(np.isfinite(optimum)):
        raise ValueError("u_star must be finite")

    evaluation = _curvature_evaluation(g, grad, optimum, order)
    evaluation["retry_count"] = 0
    evaluation["retry_optimizer_success"] = None
    evaluation["retry_optimizer_status"] = None
    if evaluation["conditioning_ok"]:
        return evaluation

    retry = minimize(
        lambda u: -float(g(np.asarray(u, dtype=np.float64))),
        optimum.copy(),
        jac=lambda u: -np.asarray(grad(np.asarray(u, dtype=np.float64)), dtype=np.float64),
        method="L-BFGS-B",
        options={
            "gtol": RETRY_GTOL,
            "ftol": RETRY_FTOL,
            "maxiter": RETRY_MAXITER,
        },
    )
    retried_optimum = np.asarray(retry.x, dtype=np.float64)
    if retried_optimum.shape != optimum.shape or not np.all(np.isfinite(retried_optimum)):
        retried_optimum = optimum.copy()
    evaluation = _curvature_evaluation(g, grad, retried_optimum, order)
    retry_success = int(retry.status) == 0 and bool(getattr(retry, "success", True))
    evaluation["retry_count"] = 1
    evaluation["retry_optimizer_success"] = retry_success
    evaluation["retry_optimizer_status"] = int(retry.status)
    if not retry_success:
        evaluation["stop"] = True
        suffix = "curvature retry optimization failed"
        evaluation["reason"] = "; ".join(
            part for part in (evaluation["reason"], suffix) if part
        )
    return evaluation


def _band_values(masses: Mapping[str, float]) -> dict[str, float]:
    try:
        values = {key: float(masses[key]) for key in _BAND_KEYS}
    except KeyError as exc:
        raise ValueError(f"missing band mass {exc.args[0]}") from exc
    if not all(np.isfinite(value) for value in values.values()):
        raise ValueError("band masses must be finite")
    return values


def delta_quad(
    band_masses_by_level: Sequence[Mapping[str, float]]
    | Mapping[int, Mapping[str, float]],
) -> dict[str, float]:
    """Return final-vs-previous successive-grid sensitivities by band."""

    if isinstance(band_masses_by_level, Mapping):
        levels = [band_masses_by_level[key] for key in sorted(band_masses_by_level)]
    else:
        levels = list(band_masses_by_level)
    if len(levels) < 2:
        raise ValueError("at least two refinement levels are required")
    previous = _band_values(levels[-2])
    final = _band_values(levels[-1])
    return {key: abs(final[key] - previous[key]) for key in _BAND_KEYS}


def delta_hess(
    band_masses_by_h: Mapping[float, Mapping[str, float]],
) -> dict[str, float]:
    """Return the maximum off-center Hessian-step sensitivity by band."""

    try:
        center = _band_values(band_masses_by_h[HESS_H_CENTER])
        alternatives = [
            _band_values(band_masses_by_h[h])
            for h in HESS_H_SWEEP
            if h != HESS_H_CENTER
        ]
    except KeyError as exc:
        raise ValueError(f"missing frozen Hessian step {exc.args[0]}") from exc
    return {
        key: max(abs(values[key] - center[key]) for values in alternatives)
        for key in _BAND_KEYS
    }


def delta_tail(
    P_full: Mapping[str, float],
    P_upper_pullback: Mapping[str, float],
    P_lower_pullback: Mapping[str, float],
) -> dict[str, Any]:
    """Return final one-sided cap sensitivities and their STOP verdict."""

    full = _band_values(P_full)
    upper_pullback = _band_values(P_upper_pullback)
    lower_pullback = _band_values(P_lower_pullback)
    upper = {key: abs(full[key] - upper_pullback[key]) for key in _BAND_KEYS}
    lower = {key: abs(full[key] - lower_pullback[key]) for key in _BAND_KEYS}
    combined = {key: max(upper[key], lower[key]) for key in _BAND_KEYS}
    stop = bool(
        any(value >= EPS_DOMAIN for value in upper.values())
        or any(value >= EPS_DOMAIN for value in lower.values())
    )
    return {
        "upper": upper,
        "lower": lower,
        "delta_tail": combined,
        "stop": stop,
        "reason": "one-sided cap sensitivity reached EPS_DOMAIN" if stop else "",
    }


def heuristic_error_envelope(
    quad: Mapping[str, float],
    hess: Mapping[str, float],
    tail: Mapping[str, float] | Mapping[str, Any],
) -> dict[str, Any]:
    """Return ``max(delta_quad, delta_hess, delta_tail)`` as a heuristic only."""

    quad_values = _band_values(quad)
    hess_values = _band_values(hess)
    tail_source = tail.get("delta_tail", tail)
    tail_values = _band_values(tail_source)
    envelope = {
        key: max(quad_values[key], hess_values[key], tail_values[key])
        for key in _BAND_KEYS
    }
    return {
        "delta_env": envelope,
        "label": "heuristic envelope, not a bound",
    }
