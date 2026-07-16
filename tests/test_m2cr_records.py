"""Schema and canonical-axis tests for Layer-2 record builders."""

import copy

import numpy as np
import pytest
from jsonschema import ValidationError
from scipy.optimize import OptimizeResult

import bistar_gp.m2cr.gates_v2 as gates
from bistar_gp.m2c_freeze import TOL_GRAD_ABS, TOL_GRAD_REL
from bistar_gp.m2cr.coordinates import (
    matrix_canonical_to_storage,
    matrix_storage_to_canonical,
    storage_to_canonical_permutation,
    vector_canonical_to_storage,
    vector_storage_to_canonical,
)
from bistar_gp.m2cr.records import (
    build_battery_record,
    build_curvature_record,
    build_per_node_record,
    build_two_start_optimizer_record,
    build_warm_start_ref,
    validate_fragment,
)

STORAGE_ORDER = (
    "SITE.outputscale",
    "SITE.base_kernel.lengthscale",
    "SITE.kernels.1.variance",
)
PERM = storage_to_canonical_permutation(STORAGE_ORDER)


def _quadratic():
    matrix = np.array([[4.0, 0.5, 0.1], [0.5, 2.0, 0.2], [0.1, 0.2, 9.0]])
    center = np.array([0.2, -0.4, 0.3])

    def g(u):
        delta = np.asarray(u, dtype=np.float64) - center
        return -0.5 * float(delta @ matrix @ delta)

    def grad(u):
        return -matrix @ (np.asarray(u, dtype=np.float64) - center)

    return g, grad, center, matrix


@pytest.fixture
def fragments():
    g, grad, center, _matrix = _quadratic()
    opt_v2 = gates.optimize_conditional_v2(
        lambda u: -g(u), lambda u: -grad(u), np.ones(3), -np.ones(3)
    )
    cur_v2 = gates.curvature_gate_v2(g, grad, center, STORAGE_ORDER)
    optimizer = build_two_start_optimizer_record(opt_v2, PERM)
    curvature = build_curvature_record(cur_v2, PERM)
    scale = 3.0
    threshold = TOL_GRAD_ABS + TOL_GRAD_REL * scale
    battery = build_battery_record(
        [
            {
                "role": role,
                "fd_step": 1.0e-5,
                "reference_value": reference,
                "functional_value": reference + 1.0e-6,
                "absolute_error": 1.0e-6,
                "threshold": threshold,
                "pass": True,
            }
            for role, reference in zip(("ls", "os", "lv"), (2.0, -3.0, 0.5))
        ]
    )
    incoming = build_warm_start_ref(
        {"kind": "mode_u"}, [0.0, 0.0, 0.0], "initial_mode_u"
    )
    selected = vector_storage_to_canonical(center, PERM)
    outgoing = build_warm_start_ref(
        {"kind": "accepted_node", "stage_id": "level0", "node_index": 4},
        selected,
        "accepted_current_node",
    )
    node = build_per_node_record(
        4,
        0.2,
        STORAGE_ORDER,
        incoming,
        outgoing,
        optimizer,
        True,
        selected,
        battery,
        curvature,
    )
    return {
        "opt_v2": opt_v2,
        "cur_v2": cur_v2,
        "optimizer": optimizer,
        "curvature": curvature,
        "battery": battery,
        "incoming": incoming,
        "outgoing": outgoing,
        "node": node,
    }


def test_all_built_fragments_validate(fragments):
    pointers = {
        "optimizer": "#/$defs/two_start_optimizer_record",
        "curvature": "#/$defs/curvature_record",
        "battery": "#/$defs/battery_record",
        "incoming": "#/$defs/warm_start_ref",
        "node": "#/$defs/per_node_record",
    }
    for name, pointer in pointers.items():
        validate_fragment(fragments[name], pointer)
    validate_fragment(
        fragments["curvature"]["pre_retry"], "#/$defs/curvature_evaluation"
    )
    validate_fragment(fragments["curvature"]["retry"], "#/$defs/retry")


def test_persisted_vectors_and_matrices_are_canonical_but_spectrum_is_not(fragments):
    opt_v2 = fragments["opt_v2"]
    record = fragments["optimizer"]
    np.testing.assert_array_equal(
        record["starts"][0]["attempts"][0]["start"],
        vector_storage_to_canonical(
            opt_v2["attempts_by_start"]["warm"][0]["start"], PERM
        ),
    )
    evaluation = fragments["cur_v2"]["evaluations"]["pre_retry"]
    stored = fragments["curvature"]["pre_retry"]
    np.testing.assert_array_equal(
        stored["raw_hessian"],
        matrix_storage_to_canonical(evaluation["raw_hessian"], PERM),
    )
    np.testing.assert_array_equal(stored["eigenvalues"], evaluation["eigenvalues"])


def test_permutation_and_conjugation_round_trip_both_directions():
    vector_storage = np.array([10.0, 20.0, 30.0])
    vector_canonical = vector_storage_to_canonical(vector_storage, PERM)
    np.testing.assert_array_equal(
        vector_canonical_to_storage(vector_canonical, PERM), vector_storage
    )
    matrix_storage = np.arange(9, dtype=np.float64).reshape(3, 3)
    matrix_canonical = matrix_storage_to_canonical(matrix_storage, PERM)
    np.testing.assert_array_equal(
        matrix_canonical_to_storage(matrix_canonical, PERM), matrix_storage
    )
    np.testing.assert_array_equal(
        matrix_storage_to_canonical(
            matrix_canonical_to_storage(matrix_canonical, PERM), PERM
        ),
        matrix_canonical,
    )


@pytest.mark.parametrize("mutation", ["reorder", "missing", "duplicate", "extra", "off_sweep", "dict"])
def test_invalid_logdet_by_h_forms_fail_validation(fragments, mutation):
    record = copy.deepcopy(fragments["curvature"])
    values = record["pre_retry"]["logdet_by_h"]
    if mutation == "reorder":
        values[0], values[1] = values[1], values[0]
    elif mutation == "missing":
        values.pop()
    elif mutation == "duplicate":
        values[1] = copy.deepcopy(values[0])
    elif mutation == "extra":
        values.append({"h": 0.004, "logdet": 0.0})
    elif mutation == "off_sweep":
        values[0]["h"] = 0.0006
    else:
        record["pre_retry"]["logdet_by_h"] = {
            str(item["h"]): item["logdet"] for item in values
        }
    with pytest.raises(ValidationError):
        validate_fragment(record, "#/$defs/curvature_record")


@pytest.mark.parametrize("mutation", ["reorder", "missing"])
def test_invalid_direction_seed_arrays_fail_validation(fragments, mutation):
    record = copy.deepcopy(fragments["curvature"])
    directions = record["pre_retry"]["directional_records"]
    if mutation == "reorder":
        directions[0], directions[1] = directions[1], directions[0]
    else:
        directions.pop()
    with pytest.raises(ValidationError):
        validate_fragment(record, "#/$defs/curvature_record")


def test_float_string_keyed_direction_dict_fails(fragments):
    record = copy.deepcopy(fragments["curvature"])
    record["pre_retry"]["directional_records"] = {
        str(item["seed"]): item for item in record["pre_retry"]["directional_records"]
    }
    with pytest.raises(ValidationError):
        validate_fragment(record, "#/$defs/curvature_record")


def test_opaque_warm_start_identity_fails(fragments):
    warm = copy.deepcopy(fragments["incoming"])
    warm["identity"] = "mode_u"
    with pytest.raises(ValidationError):
        validate_fragment(warm, "#/$defs/warm_start_ref")


def test_restart_attempt_requires_jitter_and_true_restart_tag(monkeypatch):
    calls = 0

    def restart_once(fun, x0, **kwargs):
        nonlocal calls
        calls += 1
        status = 2 if calls == 1 else 0
        return OptimizeResult(
            x=np.zeros(3), status=status, success=status == 0, message="restart"
        )

    monkeypatch.setattr(gates, "minimize", restart_once)
    opt_v2 = gates.optimize_conditional_v2(
        lambda u: 0.0, lambda u: np.zeros(3), np.ones(3), -np.ones(3)
    )
    record = build_two_start_optimizer_record(opt_v2, PERM)
    validate_fragment(record, "#/$defs/two_start_optimizer_record")
    missing = copy.deepcopy(record)
    del missing["starts"][0]["attempts"][1]["jitter"]
    with pytest.raises(ValidationError):
        validate_fragment(missing, "#/$defs/two_start_optimizer_record")
    false_tag = copy.deepcopy(record)
    false_tag["starts"][0]["attempts"][1]["is_jittered_restart"] = False
    with pytest.raises(ValidationError):
        validate_fragment(false_tag, "#/$defs/two_start_optimizer_record")


def test_post_retry_cannot_appear_when_retry_not_fired(fragments):
    record = copy.deepcopy(fragments["curvature"])
    record["post_retry"] = copy.deepcopy(record["pre_retry"])
    with pytest.raises(ValidationError):
        validate_fragment(record, "#/$defs/curvature_record")


def test_battery_scale_threshold_and_aggregate_are_computed():
    scale = 4.0
    threshold = TOL_GRAD_ABS + TOL_GRAD_REL * scale
    coordinates = [
        {
            "role": role,
            "fd_step": 1.0e-5,
            "reference_value": reference,
            "functional_value": reference,
            "absolute_error": 0.0,
            "threshold": threshold,
            "pass": passed,
        }
        for role, reference, passed in zip(
            ("ls", "os", "lv"), (4.0, -2.0, 1.0), (True, False, True)
        )
    ]
    record = build_battery_record(coordinates)
    assert record["scale"] == scale
    assert record["pass"] is False
    with pytest.raises(ValueError, match="threshold"):
        build_battery_record(
            [dict(coordinate, threshold=threshold + 1.0) for coordinate in coordinates]
        )


def test_per_node_branch_invariants_are_fail_closed(fragments):
    args = (
        5,
        0.3,
        STORAGE_ORDER,
        fragments["incoming"],
        fragments["incoming"],
        fragments["optimizer"],
    )
    with pytest.raises(ValueError, match="battery and curvature"):
        build_per_node_record(*args, True, [0.0, 0.0, 0.0])
    with pytest.raises(ValueError, match="battery or curvature"):
        build_per_node_record(
            *args, False, None, battery_record=fragments["battery"]
        )
    with pytest.raises(ValueError, match="selected optimum"):
        build_per_node_record(*args, False, [0.0, 0.0, 0.0])
    failed = build_per_node_record(*args, False, None)
    validate_fragment(failed, "#/$defs/per_node_record")
    invalid = copy.deepcopy(failed)
    invalid["selected_optimum"] = [0.0, 0.0, 0.0]
    with pytest.raises(ValidationError):
        validate_fragment(invalid, "#/$defs/per_node_record")
