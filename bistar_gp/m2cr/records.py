"""Canonical Layer-2 record builders for the v2 profile gates."""

from __future__ import annotations

import copy
import json
import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from bistar_gp.m2c_freeze import (
    DIRECTION_RNG_SEEDS,
    HESS_H_SWEEP,
    TOL_GRAD_ABS,
    TOL_GRAD_REL,
)
from bistar_gp.m2cr.coordinates import (
    CANONICAL_AXIS_ORDER,
    derive_role_map,
    matrix_storage_to_canonical,
    vector_storage_to_canonical,
)
from bistar_gp.m2cr.serialization import encode_float, encode_matrix, encode_vector

__all__ = [
    "build_two_start_optimizer_record",
    "build_curvature_record",
    "build_battery_record",
    "build_warm_start_ref",
    "build_per_node_record",
    "validate_fragment",
]

_SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "m2c_freeze"
    / "m2c_execution_record.schema_v1.json"
)
with _SCHEMA_PATH.open(encoding="utf-8") as _schema_handle:
    _EXECUTION_SCHEMA = json.load(_schema_handle)
_SCHEMA_ID = _EXECUTION_SCHEMA["$id"]
_SCHEMA_REGISTRY = Registry().with_resource(
    _SCHEMA_ID, Resource.from_contents(_EXECUTION_SCHEMA)
)


def _canonical_vector(values: Any, perm: Sequence[int]) -> list[Any]:
    return encode_vector(vector_storage_to_canonical(values, perm))


def _canonical_matrix(values: Any, perm: Sequence[int]) -> list[list[Any]]:
    return encode_matrix(matrix_storage_to_canonical(values, perm))


def _optimizer_attempt(attempt: Mapping[str, Any], perm: Sequence[int]) -> dict[str, Any]:
    record = {
        "is_jittered_restart": bool(attempt["is_jittered_restart"]),
        "start": _canonical_vector(attempt["start"], perm),
        "u": _canonical_vector(attempt["u"], perm),
        "g": encode_float(attempt["g"]),
        "gradient": _canonical_vector(attempt["gradient"], perm),
        "grad_inf_norm": encode_float(attempt["grad_inf_norm"]),
        "status": int(attempt["status"]),
        "reported_success": bool(attempt["reported_success"]),
        "finite": bool(attempt["finite"]),
        "stationary": bool(attempt["stationary"]),
        "accepted": bool(attempt["accepted"]),
        "message": str(attempt["message"]),
    }
    if record["is_jittered_restart"]:
        jitter = attempt.get("jitter")
        if not isinstance(jitter, Mapping):
            raise ValueError("a jittered restart requires jitter provenance")
        record["jitter"] = {
            "rng_seed": int(jitter["rng_seed"]),
            "jitter_scale": encode_float(jitter["jitter_scale"]),
            "base_start": _canonical_vector(jitter["base_start"], perm),
            "jitter_vector": _canonical_vector(jitter["jitter_vector"], perm),
            "resulting_start": _canonical_vector(jitter["resulting_start"], perm),
        }
    elif "jitter" in attempt:
        raise ValueError("an original attempt cannot carry jitter provenance")
    return record


def build_two_start_optimizer_record(
    opt_v2: Mapping[str, Any], perm: Sequence[int]
) -> dict[str, Any]:
    """Serialize a v2 optimizer result in canonical named axes."""

    attempts_by_start = opt_v2["attempts_by_start"]
    starts = []
    restart_starts = 0
    for label in ("warm", "mode"):
        attempts = list(attempts_by_start[label])
        if not 1 <= len(attempts) <= 2:
            raise ValueError(f"{label} must carry one or two attempts")
        if bool(attempts[0]["is_jittered_restart"]):
            raise ValueError(f"{label} attempt 0 must be the original")
        if int(attempts[0]["status"]) != 0:
            if len(attempts) != 2:
                raise ValueError(f"{label} failed original requires one restart")
        elif len(attempts) != 1:
            raise ValueError(f"{label} successful original cannot carry a restart")
        if len(attempts) == 2:
            if not bool(attempts[1]["is_jittered_restart"]):
                raise ValueError(f"{label} attempt 1 must be a jittered restart")
            restart_starts += 1
        starts.append(
            {
                "label": label,
                "attempts": [_optimizer_attempt(attempt, perm) for attempt in attempts],
            }
        )
    if int(opt_v2["restart_count"]) != restart_starts:
        raise ValueError("restart_count must equal starts carrying a restart")

    u_star = opt_v2["u_star"]
    return {
        "starts": starts,
        "u_star": None if u_star is None else _canonical_vector(u_star, perm),
        "g_star": encode_float(opt_v2["g_star"]),
        "grad_inf_norm": encode_float(opt_v2["grad_inf_norm"]),
        "both_success": bool(opt_v2["both_success"]),
        "agree": bool(opt_v2["agree"]),
        "agree_g": bool(opt_v2["agree_g"]),
        "agree_u": bool(opt_v2["agree_u"]),
        "restart_count": int(opt_v2["restart_count"]),
        "stop": bool(opt_v2["stop"]),
        "reason": str(opt_v2["reason"]),
    }


def _curvature_evaluation(
    evaluation: Mapping[str, Any], perm: Sequence[int]
) -> dict[str, Any]:
    logdet_by_h = [
        {
            "h": float(h),
            "logdet": encode_float(evaluation["logdet_by_h"][h]),
        }
        for h in HESS_H_SWEEP
    ]
    directional_records = [
        {
            "seed": int(seed),
            "direction": _canonical_vector(
                evaluation["directional_directions"][seed], perm
            ),
            "second_difference": encode_float(
                evaluation["directional_second_differences"][seed]
            ),
            "error": encode_float(evaluation["directional_errors"][seed]),
        }
        for seed in DIRECTION_RNG_SEEDS
    ]
    return {
        "u_star": _canonical_vector(evaluation["u_star"], perm),
        "raw_hessian": _canonical_matrix(evaluation["raw_hessian"], perm),
        "K": _canonical_matrix(evaluation["K"], perm),
        # Eigenvalues are in ascending spectral order, not coordinate order.
        "eigenvalues": encode_vector(evaluation["eigenvalues"]),
        "logdet": encode_float(evaluation["logdet"]),
        "logdet_by_h": logdet_by_h,
        "logdet_stability_error": encode_float(
            evaluation["logdet_stability_error"]
        ),
        "logdet_stable": bool(evaluation["logdet_stable"]),
        "rcond": encode_float(evaluation["rcond"]),
        "spd": bool(evaluation["spd"]),
        "conditioning_ok": bool(evaluation["conditioning_ok"]),
        "stationary": bool(evaluation["stationary"]),
        "grad_inf_norm": encode_float(evaluation["grad_inf_norm"]),
        "symmetry_error": encode_float(evaluation["symmetry_error"]),
        "symmetry_ok": bool(evaluation["symmetry_ok"]),
        "directional_records": directional_records,
        "directional_ok": bool(evaluation["directional_ok"]),
        "stop": bool(evaluation["stop"]),
        "reason": str(evaluation["reason"]),
    }


def _retry_record(evidence: Mapping[str, Any], perm: Sequence[int]) -> dict[str, Any]:
    if not bool(evidence["fired"]):
        return {"fired": False}
    telemetry = evidence["telemetry"]
    retry = {
        "fired": True,
        "trigger": str(evidence["trigger"]),
        "telemetry": {
            "status": int(telemetry["status"]),
            "reported_success": bool(telemetry["reported_success"]),
            "message": str(telemetry["message"]),
            # EXPLICIT field-specific exception to canonical-axis persistence
            # (prereg v1.19 §9 / plan §3.3).  The protected R1 execution-record
            # schema freezes candidate_vector as the retry optimizer's RAW
            # output "at whatever shape it came back," flattened in call order
            # with observed_shape as the shape authority — so NO canonical
            # permutation is applied even to a well-formed three-element
            # candidate, and this field is deliberately NOT canonical.  The
            # sibling gradient below IS canonicalized, making the raw/canonical
            # asymmetry within one telemetry block intentional and frozen.  The
            # general B1 canonical-position rule governs the typed axes, but the
            # closed schema's field-specific text controls here.  See
            # docs/m2c_freeze/m2c_execution_record.schema_v1.json,
            # retry_fired.telemetry.candidate_vector description, and the
            # asymmetric discriminating test in tests/test_m2cr_records.py.
            "candidate_vector": encode_vector(telemetry["candidate_vector"]),
            "candidate_finite": bool(telemetry["candidate_finite"]),
            "required_shape": [int(value) for value in telemetry["required_shape"]],
            "observed_shape": [int(value) for value in telemetry["observed_shape"]],
            "objective": encode_float(telemetry["objective"]),
            "gradient": _canonical_vector(telemetry["gradient"], perm),
            "stationarity_norm": encode_float(telemetry["stationarity_norm"]),
        },
        "conjuncts": {
            key: bool(evidence["conjuncts"][key])
            for key in (
                "status_zero",
                "reported_success",
                "output_shape_and_finite",
                "objective_finite",
                "gradient_shape_and_finite",
                "stationarity_within_bound",
            )
        },
        "positively_accepted": bool(evidence["positively_accepted"]),
        "fallback_fired": bool(evidence["fallback_fired"]),
    }
    if retry["positively_accepted"] != all(retry["conjuncts"].values()):
        raise ValueError("positively_accepted must equal the retry conjuncts")
    if retry["fallback_fired"]:
        if evidence.get("fallback_target") != "pre_retry_optimum":
            raise ValueError("fallback retry must target the pre-retry optimum")
        retry["fallback_target"] = "pre_retry_optimum"
    elif "fallback_target" in evidence:
        raise ValueError("non-fallback retry cannot carry a fallback target")
    return retry


def build_curvature_record(
    cur_v2: Mapping[str, Any], perm: Sequence[int]
) -> dict[str, Any]:
    """Serialize the retained v2 curvature evaluations and retry evidence."""

    evaluations = cur_v2["evaluations"]
    retry = _retry_record(cur_v2["retry_evidence"], perm)
    record = {
        "retry": retry,
        "pre_retry": _curvature_evaluation(evaluations["pre_retry"], perm),
    }
    if retry["fired"]:
        if "post_retry" not in evaluations:
            raise ValueError("a fired retry requires a post-retry evaluation")
        record["post_retry"] = _curvature_evaluation(
            evaluations["post_retry"], perm
        )
    elif "post_retry" in evaluations:
        raise ValueError("post-retry evaluation present when retry did not fire")
    return record


def _same_float(left: float, right: float) -> bool:
    return left == right or (math.isnan(left) and math.isnan(right))


def build_battery_record(coordinates: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Build the canonical three-coordinate finite-difference battery record."""

    if len(coordinates) != 3:
        raise ValueError("battery requires exactly three canonical coordinates")
    refs = [float(coordinate["reference_value"]) for coordinate in coordinates]
    scale = max(1.0, *(abs(value) for value in refs))
    threshold = TOL_GRAD_ABS + TOL_GRAD_REL * scale
    encoded_coordinates = []
    for role, coordinate in zip(CANONICAL_AXIS_ORDER, coordinates, strict=True):
        if coordinate.get("role") != role:
            raise ValueError("battery coordinates must be ordered (ls, os, lv)")
        supplied_threshold = float(coordinate.get("threshold", threshold))
        if not _same_float(supplied_threshold, threshold):
            raise ValueError("battery threshold is inconsistent with the frozen scale")
        encoded_coordinates.append(
            {
                "role": role,
                "fd_step": encode_float(coordinate["fd_step"]),
                "reference_value": encode_float(coordinate["reference_value"]),
                "functional_value": encode_float(coordinate["functional_value"]),
                "absolute_error": encode_float(coordinate["absolute_error"]),
                "threshold": encode_float(threshold),
                "pass": bool(coordinate["pass"]),
            }
        )
    return {
        "scale": encode_float(scale),
        "pass": bool(all(coordinate["pass"] for coordinate in coordinates)),
        "coordinates": encoded_coordinates,
    }


def build_warm_start_ref(
    identity_dict: Mapping[str, Any],
    vector_canonical: Sequence[float] | np.ndarray,
    selection_reason: str,
) -> dict[str, Any]:
    """Build a closed warm-start reference from an explicit tagged identity."""

    if not isinstance(identity_dict, Mapping):
        raise ValueError("warm-start identity must be a tagged object")
    vector = np.asarray(vector_canonical, dtype=np.float64)
    if vector.shape != (3,):
        raise ValueError("warm-start vector must have three canonical coordinates")
    return {
        "identity": copy.deepcopy(dict(identity_dict)),
        "vector": encode_vector(vector),
        "selection_reason": str(selection_reason),
    }


def build_per_node_record(
    node_index: int,
    noise: float,
    computation_storage_order: Sequence[str],
    incoming_ref: Mapping[str, Any],
    outgoing_ref: Mapping[str, Any],
    optimizer_record: Mapping[str, Any],
    accepted: bool,
    selected_optimum_canonical: Sequence[float] | np.ndarray | None,
    battery_record: Mapping[str, Any] | None = None,
    curvature_record: Mapping[str, Any] | None = None,
    *,
    stage_id: str,
) -> dict[str, Any]:
    """Build one accepted or failed Layer-2 node record fail-closed.

    ``stage_id`` names the stage this node ran in; it enters no record field
    (the schema carries no per-node stage member) and exists to enforce the
    v1.19 §9 relational invariant that an accepted node's outgoing identity
    points at exactly this node.
    """

    storage_order = tuple(str(site) for site in computation_storage_order)
    derive_role_map(storage_order)
    noise_value = float(noise)
    if not math.isfinite(noise_value):
        raise ValueError("noise is finite-only")
    if not isinstance(stage_id, str) or not stage_id:
        raise ValueError("stage_id must be a non-empty string")
    record: dict[str, Any] = {
        "node_index": int(node_index),
        "noise": noise_value,
        "persisted_axis_order": list(CANONICAL_AXIS_ORDER),
        "computation_storage_order": list(storage_order),
        "incoming_warm_start": copy.deepcopy(dict(incoming_ref)),
        "outgoing_warm_start": copy.deepcopy(dict(outgoing_ref)),
        "optimizer": copy.deepcopy(dict(optimizer_record)),
        "accepted": bool(accepted),
    }
    if accepted:
        if selected_optimum_canonical is None:
            raise ValueError("accepted node requires a selected optimum")
        if battery_record is None or curvature_record is None:
            raise ValueError("accepted node requires battery and curvature records")
        selected = np.asarray(selected_optimum_canonical, dtype=np.float64)
        if selected.shape != (3,):
            raise ValueError("selected optimum must have three canonical coordinates")
        encoded_selected = encode_vector(selected)
        # v1.19 §9: an accepted node's outgoing identity points at THIS node
        # and its vector is the selected optimum, so the continuation
        # trajectory reconstructs without external inference.
        expected_identity = {
            "kind": "accepted_node",
            "stage_id": stage_id,
            "node_index": int(node_index),
        }
        if outgoing_ref.get("identity") != expected_identity:
            raise ValueError(
                "accepted node's outgoing identity must point at this node "
                f"({expected_identity}), got {outgoing_ref.get('identity')}"
            )
        if list(outgoing_ref.get("vector", [])) != encoded_selected:
            raise ValueError(
                "accepted node's outgoing vector must equal the selected optimum"
            )
        record["selected_optimum"] = encoded_selected
        record["battery"] = copy.deepcopy(dict(battery_record))
        record["curvature"] = copy.deepcopy(dict(curvature_record))
    else:
        if selected_optimum_canonical is not None:
            raise ValueError("failed node cannot carry a selected optimum")
        if battery_record is not None or curvature_record is not None:
            raise ValueError("failed node cannot carry battery or curvature")
        # v1.19 §9: on optimizer failure the outgoing IDENTITY and VECTOR
        # equal the incoming ones; selection_reason legitimately moves to a
        # carried_* value and is deliberately not compared.
        if incoming_ref.get("identity") != outgoing_ref.get("identity"):
            raise ValueError(
                "failed node must carry its incoming warm-start identity forward"
            )
        if incoming_ref.get("vector") != outgoing_ref.get("vector"):
            raise ValueError(
                "failed node must carry its incoming warm-start vector forward"
            )
        record["selected_optimum"] = None
    return record


def validate_fragment(instance: Any, json_pointer: str) -> None:
    """Validate an instance against one directly addressed frozen ``$def``."""

    if not json_pointer.startswith("#/$defs/") or json_pointer.count("/") != 2:
        raise ValueError("fragment pointer must be exactly #/$defs/<name>")
    name = json_pointer.removeprefix("#/$defs/").replace("~1", "/").replace("~0", "~")
    if name not in _EXECUTION_SCHEMA["$defs"]:
        raise ValueError(f"unknown schema fragment: {json_pointer}")
    validator = Draft202012Validator(
        {"$ref": _SCHEMA_ID + json_pointer}, registry=_SCHEMA_REGISTRY
    )
    validator.validate(instance)
