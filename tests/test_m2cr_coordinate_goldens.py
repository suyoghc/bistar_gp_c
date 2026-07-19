"""Canonical-coordinate goldens frozen by prereg v1.21 section 8."""

from __future__ import annotations

import copy

import numpy as np

from bistar_gp.m2cr.coordinates import (
    storage_to_canonical_permutation,
    vector_canonical_to_storage,
    vector_storage_to_canonical,
)
from bistar_gp.m2cr.diagnostic import canonical_bridge
from bistar_gp.m2cr.diagnostic_payload import run_diagnostic
from bistar_gp.m2cr.gates_v2 import curvature_gate_v2
from tests.test_m2cr_diagnostic_protocol import (
    STORAGE_ORDER,
    prior_draw_provider,
    small_closure,
)


GOLDEN = {
    200: np.asarray(
        [0.42866767201294514, -0.5836491302931798, -0.689635932705813],
        dtype=np.float64,
    ),
    201: np.asarray(
        [0.6662640616058295, -0.20989424792754147, -0.7155673307938499],
        dtype=np.float64,
    ),
    202: np.asarray(
        [0.8108396382808845, -0.32628960814696545, -0.48587464701075345],
        dtype=np.float64,
    ),
}


def _canonical_quadratic():
    curvature = np.diag(np.asarray([1.0, 4.0, 9.0], dtype=np.float64))
    center = np.asarray([0.2, -0.1, 0.05], dtype=np.float64)

    def g(u):
        delta = np.asarray(u, dtype=np.float64) - center
        return -0.5 * float(delta @ curvature @ delta)

    def grad(u):
        return -(curvature @ (np.asarray(u, dtype=np.float64) - center))

    return curvature, center, g, grad


def test_direction_literals_and_gate_evidence_are_bit_exact() -> None:
    curvature, center, g, grad = _canonical_quadratic()
    for seed in (200, 201, 202):
        realized = np.random.default_rng(seed).standard_normal(3)
        realized /= np.linalg.norm(realized)
        assert np.array_equal(realized, GOLDEN[seed])
    gate = curvature_gate_v2(
        g, grad, center, STORAGE_ORDER, perm=(0, 1, 2)
    )
    for seed in (200, 201, 202):
        assert np.array_equal(gate["directional_directions"][seed], GOLDEN[seed])
    assert np.allclose(gate["K"], curvature, rtol=0.0, atol=1e-14)


def _run_named(bridge, storage_order=STORAGE_ORDER, prior_provider=prior_draw_provider):
    _curvature, _center, canonical_g, canonical_grad = _canonical_quadratic()
    return run_diagnostic(
        small_closure(),
        bridge,
        np.zeros(3, dtype=np.float64),
        0.06,
        lambda _u, _noise: [
            {"reference_value": value, "fd_step": 1e-5}
            for value in (1.0, 2.0, 3.0)
        ],
        lambda u, _noise: canonical_g(u),
        lambda: [
            {"site": role, "worst_relative": 0.02}
            for role in ("ls", "os", "lv")
        ],
        prior_provider,
        storage_order,
        0.061867347763041584,
    )


def test_asymmetric_named_axis_oracle_persists_canonical_evidence() -> None:
    _curvature, _center, g, grad = _canonical_quadratic()
    document = _run_named(lambda _noise: (g, grad))
    first = document["node_records"][0]
    assert [item["role"] for item in first["battery"]["coordinates"]] == [
        "ls",
        "os",
        "lv",
    ]
    assert [
        item["reference_value"] for item in first["battery"]["coordinates"]
    ] == [1.0, 2.0, 3.0]
    evaluation = first["curvature"]["pre_retry"]
    assert np.allclose(evaluation["K"], np.diag([1.0, 4.0, 9.0]), atol=1e-10)
    assert np.allclose(evaluation["eigenvalues"], [1.0, 4.0, 9.0], atol=1e-10)
    for directional in evaluation["directional_records"]:
        assert np.array_equal(
            np.asarray(directional["direction"]), GOLDEN[directional["seed"]]
        )


def _storage_bridge(storage_order):
    _curvature, _center, canonical_g, canonical_grad = _canonical_quadratic()
    perm = storage_to_canonical_permutation(storage_order)

    def g_storage(u_storage):
        return canonical_g(vector_storage_to_canonical(u_storage, perm))

    def grad_storage(u_storage):
        canonical = vector_storage_to_canonical(u_storage, perm)
        return vector_canonical_to_storage(canonical_grad(canonical), perm)

    return canonical_bridge(g_storage, grad_storage, perm)


def _strip_storage_provenance(value):
    if isinstance(value, dict):
        return {
            key: _strip_storage_provenance(item)
            for key, item in value.items()
            if key not in {"computation_storage_order", "storage_site_order"}
        }
    if isinstance(value, list):
        return [_strip_storage_provenance(item) for item in value]
    return value


def test_storage_permutation_changes_only_provenance_strings() -> None:
    canonical_order = STORAGE_ORDER
    permuted_order = (STORAGE_ORDER[2], STORAGE_ORDER[0], STORAGE_ORDER[1])

    def provider_for(order):
        base = prior_draw_provider()
        return {
            "storage_site_order": list(order),
            "states": copy.deepcopy(base["states"]),
        }

    first = _run_named(
        lambda _noise: _storage_bridge(canonical_order),
        canonical_order,
        lambda: provider_for(canonical_order),
    )
    second = _run_named(
        lambda _noise: _storage_bridge(permuted_order),
        permuted_order,
        lambda: provider_for(permuted_order),
    )
    assert _strip_storage_provenance(first) == _strip_storage_provenance(second)
