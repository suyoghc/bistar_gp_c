"""Hermetic tests for the frozen R3 diagnostic-record instance schema."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource


REPO_ROOT = Path(__file__).resolve().parents[1]
DIAGNOSTIC_SCHEMA_PATH = (
    REPO_ROOT / "docs/m2c_freeze/m2c_diagnostic_record.schema_v1.json"
)
EXECUTION_SCHEMA_PATH = (
    REPO_ROOT / "docs/m2c_freeze/m2c_execution_record.schema_v1.json"
)
DIAGNOSTIC_SCHEMA = json.loads(DIAGNOSTIC_SCHEMA_PATH.read_text())
EXECUTION_SCHEMA = json.loads(EXECUTION_SCHEMA_PATH.read_text())
REGISTRY = Registry().with_resources(
    [
        (
            DIAGNOSTIC_SCHEMA["$id"],
            Resource.from_contents(DIAGNOSTIC_SCHEMA),
        ),
        (
            EXECUTION_SCHEMA["$id"],
            Resource.from_contents(EXECUTION_SCHEMA),
        ),
    ]
)
VALIDATOR = Draft202012Validator(DIAGNOSTIC_SCHEMA, registry=REGISTRY)


def _g2_point(kind: str, label: str, seed=None, node_index=None) -> dict:
    return {
        "kind": kind,
        "label": label,
        "seed": seed,
        "node_index": node_index,
        "g_value": 0.0,
        "g_hist": 0.0,
        "abs_diff": 0.0,
        "bound": 1e-9,
        "pass": True,
    }


def valid_instance(*, accepted: bool = False) -> dict:
    """Hand-written instance independent of the production payload builder."""

    prior_states = [
        {"seed": seed, "u": [0.0, 0.0, 0.0], "noise": 0.1}
        for seed in range(100, 110)
    ]
    g2 = [_g2_point("map", "map")]
    g2.extend(
        _g2_point("prior_draw", f"prior/seed{seed}", seed=seed)
        for seed in range(100, 110)
    )
    if accepted:
        row = {
            "node_index": 0,
            "probe_position": 0,
            "stage_id": "level0",
            "noise": 0.1,
            "optimizer_accepted": True,
            "final_evaluation_point": {
                "phase": "pre_retry",
                "u": [0.0, 0.0, 0.0],
            },
            "raw_symmetry": {
                "h_center": 0.001,
                "symmetry_error": 1e-7,
                "symmetry_ok": True,
            },
            "sweep": [
                {"h": h, "symmetry_error": 1e-7}
                for h in (0.00025, 0.0005, 0.001, 0.002, 0.004)
            ],
            "slope_analysis": {
                "classification": "FLAT",
                "slope": 0.0,
                "intercept": -16.11809565095832,
            },
            "curvature_summary": {
                "retry_fired": False,
                "retry_positively_accepted": None,
                "nonstationarity_observed_any_evaluated_point": False,
                "stationary_final": True,
                "spd_final": True,
                "rcond_ok_final": True,
                "directional_ok_final": True,
                "logdet_stable_final": True,
            },
        }
        g2.append(_g2_point("accepted_optimum", "node/0", node_index=0))
    else:
        row = {
            "node_index": 0,
            "probe_position": 0,
            "stage_id": "level0",
            "noise": 0.1,
            "optimizer_accepted": False,
        }
    zero_block = {
        "restart_count": 0,
        "retry_count": 0,
        "retry_failure_count": 0,
        "rcond_fail_count": 0,
        "symmetry_fail_count": 0,
        "battery_fail_count": 0,
    }
    stages = [
        {
            "stage_id": stage_id,
            "stage_class": "verdict",
            "status": "COMPLETED",
            "nodes_evaluated": 1 if stage_id == "level0" else 0,
            "nodes_total": 1 if stage_id == "level0" else 0,
        }
        for stage_id in (
            "level0",
            "refine_1",
            "refine_2",
            "refine_3",
            "upper_pullback",
            "lower_pullback",
        )
    ]
    return {
        "schema_version": 1,
        "kind": "m2c_diagnostic_record",
        "addendum": "v1.21",
        "not_a_result": True,
        "status": "COMPLETED",
        "persisted_axis_order": ["ls", "os", "lv"],
        "computation_storage_order": [
            "kernel.base_kernel.lengthscale_prior",
            "kernel.outputscale_prior",
            "kernel.kernels.1.variance_prior",
        ],
        "coverage": {
            "closure_node_count": 1,
            "probe_order": "ascending_noise",
            "node_index_assignment": "stage_grouped",
            "per_stage_node_counts": {
                "level0": 1,
                "refine_1": 0,
                "refine_2": 0,
                "refine_3": 0,
                "upper_pullback": 0,
                "lower_pullback": 0,
            },
        },
        "map_construction": {
            "torch_seed": 42,
            "n_iter": 300,
            "lr": 0.05,
            "prior_config": "toy_elicited_n20",
            "map_noise": 0.061867347763041584,
            "expected_noise": 0.061867347763041584,
            "delta": 0.0,
            "report_only": True,
        },
        "prior_draws": {
            "seeds": list(range(100, 110)),
            "storage_site_order": [
                "kernel.base_kernel.lengthscale_prior",
                "kernel.outputscale_prior",
                "kernel.kernels.1.variance_prior",
            ],
            "states": prior_states,
        },
        "g2_equivalence": {
            "tolerance_rel": 1e-9,
            "tolerance_floor": 1.0,
            "points": g2,
            "all_pass": True,
        },
        "d23_sentinel": {
            "min_rel": 0.01,
            "per_site": [
                {"site": role, "worst_relative": 0.02, "pass": True}
                for role in ("ls", "os", "lv")
            ],
            "pass": True,
        },
        "g1_battery": {
            "evaluated_count": 1 if accepted else 0,
            "failing_node_indices": [],
            "all_pass": True,
        },
        "purity": {
            "u_definition": "mode_u",
            "repeats": 2,
            "mode": {
                "noise": 0.06,
                "g_bit_identical": True,
                "grad_bit_identical": True,
            },
            "probe_points": [
                {
                    "label": label,
                    "probe_position": 0,
                    "node_index": 0,
                    "noise": 0.1,
                    "g_bit_identical": True,
                    "grad_bit_identical": True,
                }
                for label in ("first", "mid", "last")
            ],
            "pass": True,
        },
        "per_node_diagnostics": [row],
        "stages": stages,
        "aggregates": {
            "verdict_class": copy.deepcopy(zero_block),
            "diagnostic_class": copy.deepcopy(zero_block),
        },
        "node_evidence_digests": [
            {"node_index": 0, "record_sha256": "0" * 64}
        ],
    }


def _invalid(mutator) -> None:
    instance = valid_instance(accepted=True)
    mutator(instance)
    assert not VALIDATOR.is_valid(instance)


def test_hand_written_valid_instance_is_accepted() -> None:
    VALIDATOR.validate(valid_instance())
    VALIDATOR.validate(valid_instance(accepted=True))


@pytest.mark.parametrize(
    "mutator",
    [
        lambda doc: doc.update(unknown=True),
        lambda doc: doc["per_node_diagnostics"][0]["curvature_summary"].pop(
            "spd_final"
        ),
        lambda doc: doc["per_node_diagnostics"][0].update(
            slope_analysis={
                "classification": "UNDEFINED",
                "undefined_reason": "nonfinite_sweep_value",
                "slope": 2.0,
            }
        ),
        lambda doc: doc["per_node_diagnostics"][0]["sweep"][0].update(h=0.0003),
        lambda doc: doc["per_node_diagnostics"][0].update(
            sweep=doc["per_node_diagnostics"][0]["sweep"][:4]
        ),
        lambda doc: doc["per_node_diagnostics"][0].update(
            sweep=list(reversed(doc["per_node_diagnostics"][0]["sweep"]))
        ),
        lambda doc: doc["per_node_diagnostics"][0]["sweep"][0].update(
            symmetry_error={"_nonfinite": "infinity"}
        ),
        lambda doc: doc.update(addendum="v1.20"),
        lambda doc: doc["prior_draws"].update(
            states=list(reversed(doc["prior_draws"]["states"]))
        ),
        lambda doc: doc["per_node_diagnostics"][0].update(
            optimizer_accepted=False
        ),
        lambda doc: doc["stages"][0].update(
            stage_id="cap_1e-3", stage_class="diagnostic"
        ),
        lambda doc: doc.update(stages=doc["stages"][:5]),
        lambda doc: doc.pop("node_evidence_digests"),
    ],
)
def test_negative_schema_surfaces(mutator) -> None:
    _invalid(mutator)
