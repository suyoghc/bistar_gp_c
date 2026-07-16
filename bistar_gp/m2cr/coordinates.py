"""Coordinate semantics: role map, permutation, conjugation (plan §3.3, B1).

Directions and persisted evidence are named-canonical ``(ls, os, lv)`` while
computation stays in E1 storage order. The role map is ratified: the site
containing ``base_kernel.lengthscale`` is ``ls``; ``outputscale`` is ``os``;
``kernels.1.variance`` is ``lv``; exactly one site per role or STOP. Records
carry ``persisted_axis_order`` (a const) and ``computation_storage_order``
(the three E1 site names in computation order) per prereg v1.19 §9; the
ambiguous field name ``nuisance_order`` is not used in persisted records.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

__all__ = [
    "CANONICAL_AXIS_ORDER",
    "ROLE_SITE_MARKERS",
    "CoordinateRoleError",
    "derive_role_map",
    "storage_to_canonical_permutation",
    "vector_storage_to_canonical",
    "vector_canonical_to_storage",
    "matrix_storage_to_canonical",
    "matrix_canonical_to_storage",
]

CANONICAL_AXIS_ORDER = ("ls", "os", "lv")

# Ratified substring markers (plan §3.3).
ROLE_SITE_MARKERS = {
    "ls": "base_kernel.lengthscale",
    "os": "outputscale",
    "lv": "kernels.1.variance",
}


class CoordinateRoleError(ValueError):
    """Raised on any role-map violation; callers treat this as a STOP."""


def derive_role_map(storage_sites: Sequence[str]) -> dict[str, str]:
    """Map each canonical role to exactly one storage site name, or STOP.

    Fail-closed conditions, each raising :class:`CoordinateRoleError`:
    a role matching zero sites, a role matching two or more sites, one site
    claimed by two roles, or an inventory whose sites are not exactly the
    three role sites.
    """

    sites = tuple(storage_sites)
    if len(sites) != len(set(sites)):
        raise CoordinateRoleError(f"duplicate site names in inventory: {list(sites)}")
    role_map: dict[str, str] = {}
    for role in CANONICAL_AXIS_ORDER:
        marker = ROLE_SITE_MARKERS[role]
        matches = [site for site in sites if marker in site]
        if len(matches) != 1:
            raise CoordinateRoleError(
                f"role {role!r} (marker {marker!r}) matched {len(matches)} sites "
                f"in {list(sites)}; exactly one site per role is required (STOP)"
            )
        role_map[role] = matches[0]
    claimed = list(role_map.values())
    if len(set(claimed)) != len(claimed):
        raise CoordinateRoleError(
            f"one site claimed by two roles: {role_map}; the role map must be "
            "a bijection (STOP)"
        )
    unclaimed = [site for site in sites if site not in set(claimed)]
    if unclaimed:
        raise CoordinateRoleError(
            f"sites {unclaimed} carry no canonical role; the three-site "
            "inventory must be exactly the role sites (STOP)"
        )
    return role_map


def storage_to_canonical_permutation(
    storage_sites: Sequence[str],
) -> tuple[int, int, int]:
    """Return ``perm`` with ``canonical[i] = storage[perm[i]]``.

    ``perm[i]`` is the storage index of the site holding canonical role
    ``CANONICAL_AXIS_ORDER[i]``.
    """

    sites = tuple(storage_sites)
    role_map = derive_role_map(sites)
    return tuple(  # type: ignore[return-value]
        sites.index(role_map[role]) for role in CANONICAL_AXIS_ORDER
    )


def _as_perm(perm: Sequence[int]) -> tuple[int, ...]:
    order = tuple(int(index) for index in perm)
    if sorted(order) != list(range(len(order))):
        raise CoordinateRoleError(f"not a permutation: {list(perm)}")
    return order


def vector_storage_to_canonical(
    vector: np.ndarray | Sequence[float], perm: Sequence[int]
) -> np.ndarray:
    values = np.asarray(vector, dtype=np.float64)
    order = _as_perm(perm)
    if values.ndim != 1 or values.size != len(order):
        raise CoordinateRoleError(
            f"vector shape {values.shape} does not match permutation size {len(order)}"
        )
    return values[list(order)]


def vector_canonical_to_storage(
    vector: np.ndarray | Sequence[float], perm: Sequence[int]
) -> np.ndarray:
    values = np.asarray(vector, dtype=np.float64)
    order = _as_perm(perm)
    if values.ndim != 1 or values.size != len(order):
        raise CoordinateRoleError(
            f"vector shape {values.shape} does not match permutation size {len(order)}"
        )
    result = np.empty_like(values)
    for canonical_index, storage_index in enumerate(order):
        result[storage_index] = values[canonical_index]
    return result


def matrix_storage_to_canonical(
    matrix: np.ndarray | Sequence[Sequence[float]], perm: Sequence[int]
) -> np.ndarray:
    """Conjugate by the role permutation: ``K_canon = P K P^T``."""

    values = np.asarray(matrix, dtype=np.float64)
    order = list(_as_perm(perm))
    if values.ndim != 2 or values.shape != (len(order), len(order)):
        raise CoordinateRoleError(
            f"matrix shape {values.shape} does not match permutation size {len(order)}"
        )
    return values[np.ix_(order, order)]


def matrix_canonical_to_storage(
    matrix: np.ndarray | Sequence[Sequence[float]], perm: Sequence[int]
) -> np.ndarray:
    values = np.asarray(matrix, dtype=np.float64)
    order = list(_as_perm(perm))
    if values.ndim != 2 or values.shape != (len(order), len(order)):
        raise CoordinateRoleError(
            f"matrix shape {values.shape} does not match permutation size {len(order)}"
        )
    inverse = np.empty(len(order), dtype=np.int64)
    for canonical_index, storage_index in enumerate(order):
        inverse[storage_index] = canonical_index
    return values[np.ix_(list(inverse), list(inverse))]
