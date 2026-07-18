"""Role map and canonical-axis permutation (plan §3.3, ballot B1; v1.19 §9)."""

import numpy as np
import pytest

from bistar_gp.m2cr import coordinates as coords

# E1-style storage inventory in the D45-recorded storage order (os, ls, lv),
# whereas the canonical persisted order is (ls, os, lv).
STORAGE_SITES = (
    "model.covar_module.outputscale",
    "model.covar_module.base_kernel.lengthscale",
    "model.covar_module.kernels.1.variance",
)


def test_role_map_matches_the_ratified_markers():
    role_map = coords.derive_role_map(STORAGE_SITES)
    assert role_map == {
        "ls": "model.covar_module.base_kernel.lengthscale",
        "os": "model.covar_module.outputscale",
        "lv": "model.covar_module.kernels.1.variance",
    }


def test_exactly_one_site_per_role_or_stop():
    with pytest.raises(coords.CoordinateRoleError):
        coords.derive_role_map(
            ("a.base_kernel.lengthscale", "b.base_kernel.lengthscale", "c.outputscale")
        )
    with pytest.raises(coords.CoordinateRoleError):
        coords.derive_role_map(("a.outputscale", "b.kernels.1.variance", "c.other"))
    with pytest.raises(coords.CoordinateRoleError):
        coords.derive_role_map(STORAGE_SITES + ("extra.site",))
    with pytest.raises(coords.CoordinateRoleError):
        coords.derive_role_map(STORAGE_SITES[:2])
    with pytest.raises(coords.CoordinateRoleError):
        coords.derive_role_map(STORAGE_SITES + STORAGE_SITES[:1])


def test_permutation_maps_storage_into_canonical_order():
    perm = coords.storage_to_canonical_permutation(STORAGE_SITES)
    # canonical[i] = storage[perm[i]]: ls at storage index 1, os at 0, lv at 2.
    assert perm == (1, 0, 2)


def test_vector_permutation_round_trips_both_directions():
    perm = coords.storage_to_canonical_permutation(STORAGE_SITES)
    storage = np.asarray([10.0, 20.0, 30.0])
    canonical = coords.vector_storage_to_canonical(storage, perm)
    assert canonical.tolist() == [20.0, 10.0, 30.0]
    back = coords.vector_canonical_to_storage(canonical, perm)
    assert np.array_equal(back, storage)
    # And the reverse composition.
    assert np.array_equal(
        coords.vector_storage_to_canonical(
            coords.vector_canonical_to_storage(canonical, perm), perm
        ),
        canonical,
    )


def test_matrix_conjugation_round_trips_and_preserves_quadratic_forms():
    perm = coords.storage_to_canonical_permutation(STORAGE_SITES)
    rng = np.random.default_rng(7)
    matrix = rng.standard_normal((3, 3))
    matrix = matrix + matrix.T
    vector = rng.standard_normal(3)

    canonical_matrix = coords.matrix_storage_to_canonical(matrix, perm)
    canonical_vector = coords.vector_storage_to_canonical(vector, perm)
    # Conjugation is exactly P K P^T: quadratic forms are invariant.
    assert np.isclose(
        vector @ matrix @ vector, canonical_vector @ canonical_matrix @ canonical_vector
    )
    # Spectrum is invariant, so eigenvalues never need permuting.
    assert np.allclose(
        np.linalg.eigvalsh(matrix), np.linalg.eigvalsh(canonical_matrix)
    )
    assert np.array_equal(
        coords.matrix_canonical_to_storage(canonical_matrix, perm), matrix
    )


def test_shape_and_permutation_validation():
    perm = (1, 0, 2)
    with pytest.raises(coords.CoordinateRoleError):
        coords.vector_storage_to_canonical(np.zeros(2), perm)
    with pytest.raises(coords.CoordinateRoleError):
        coords.matrix_storage_to_canonical(np.zeros((2, 3)), perm)
    with pytest.raises(coords.CoordinateRoleError):
        coords.vector_storage_to_canonical(np.zeros(3), (0, 0, 2))


def test_identity_permutation_when_storage_is_already_canonical():
    sites = (
        "m.base_kernel.lengthscale",
        "m.outputscale",
        "m.kernels.1.variance",
    )
    perm = coords.storage_to_canonical_permutation(sites)
    assert perm == (0, 1, 2)
    vec = np.asarray([1.0, 2.0, 3.0])
    assert np.array_equal(coords.vector_storage_to_canonical(vec, perm), vec)
