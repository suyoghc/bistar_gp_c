"""Hermetic protocol tests for the R3 diagnostic orchestrator."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np
import pytest

import bistar_gp.m2cr.diagnostic_payload as payload_module
from bistar_gp.m2c_freeze import REFINE_L_MAX
from bistar_gp.m2cr.capture import (
    _stage_class_map_from_records,
    aggregates_from_node_records,
)
from bistar_gp.m2cr.diagnostic import (
    DECISION_TABLE_ROWS,
    evaluate_decision_table,
)
from bistar_gp.m2cr.diagnostic_payload import (
    DIAGNOSTIC_STAGE_ORDER,
    build_closure,
    diagnostic_payload_entry,
    finalize_document_for_validation,
    run_diagnostic,
)
from bistar_gp.profile_integration import (
    cap_ladder_grids,
    full_domain_grid,
    nested_refine,
)
from tests.test_m2cr_diagnostic_schema import VALIDATOR, valid_instance


STORAGE_ORDER = (
    "toy.base_kernel.lengthscale_prior",
    "toy.outputscale_prior",
    "toy.kernels.1.variance_prior",
)


def small_closure() -> dict:
    stages = {
        stage_id: np.asarray([0.1 * (index + 1)], dtype=np.float64)
        for index, stage_id in enumerate(DIAGNOSTIC_STAGE_ORDER)
    }
    nodes = [
        (index, stage_id, float(stages[stage_id][0]))
        for index, stage_id in enumerate(DIAGNOSTIC_STAGE_ORDER)
    ]
    return {
        "stages": stages,
        "nodes": nodes,
        "probe_sequence": list(nodes),
        "closure_node_count": len(nodes),
    }


def prior_draw_provider() -> dict:
    return {
        "storage_site_order": list(STORAGE_ORDER),
        "states": [
            {
                "seed": seed,
                "u": np.asarray([0.01 * seed, -0.1, 0.2], dtype=np.float64),
                "noise": 0.07 + 1e-4 * (seed - 100),
            }
            for seed in range(100, 110)
        ],
    }


def smooth_bridge(
    *, mismatch: bool = False, flat_noise: float | None = None, nondeterministic=False
):
    calls = {"g": 0}

    def bridge(noise: float):
        if flat_noise is not None and noise == pytest.approx(flat_noise):
            def g_flat(_u):
                return 0.0

            def grad_flat(u):
                return np.zeros_like(np.asarray(u, dtype=np.float64))

            return g_flat, grad_flat
        matrix = np.asarray(
            [[1.0, 2e-6, 0.0], [0.0, 4.0, 0.0], [0.0, 0.0, 9.0]],
            dtype=np.float64,
        )

        def g(u):
            value = -0.5 * float(np.asarray(u) @ matrix @ np.asarray(u))
            if nondeterministic and noise > 0.59 and np.array_equal(u, np.zeros(3)):
                calls["g"] += 1
                value += calls["g"] * np.finfo(np.float64).eps
            return value + (1.0 if mismatch else 0.0)

        def grad(u):
            return -(matrix @ np.asarray(u, dtype=np.float64))

        return g, grad

    return bridge


def run_fake(**overrides) -> dict:
    bridge = overrides.pop("bridge", smooth_bridge())

    def battery_reference(u, _noise):
        _, grad = bridge(_noise)
        values = grad(u)
        return [
            {"reference_value": float(values[index]), "fd_step": 1e-5}
            for index in range(3)
        ]

    arguments = {
        "closure": small_closure(),
        "bridge": bridge,
        "mode_u_canonical": np.zeros(3, dtype=np.float64),
        "map_noise": 0.06,
        "battery_reference": battery_reference,
        "g_hist": lambda u, noise: smooth_bridge()(noise)[0](u),
        "d23_provider": lambda: [
            {"site": role, "worst_relative": 0.02}
            for role in ("ls", "os", "lv")
        ],
        "prior_draw_provider": prior_draw_provider,
        "computation_storage_order": STORAGE_ORDER,
        "expected_map_noise": 0.061867347763041584,
    }
    arguments.update(overrides)
    return run_diagnostic(**arguments)


def test_build_closure_matches_independent_set_arithmetic() -> None:
    closure = build_closure()
    stages = [set(values.tolist()) for values in closure["stages"].values()]
    for index, left in enumerate(stages):
        for right in stages[index + 1 :]:
            assert left.isdisjoint(right)
    assert closure["closure_node_count"] == len(closure["nodes"]) <= 1481

    full = set(full_domain_grid().tolist())
    refined = full_domain_grid()
    expected = set(full)
    for _ in range(REFINE_L_MAX):
        refined = nested_refine(refined)
        expected.update(refined.tolist())
    ladders = cap_ladder_grids()
    for direction, cap in (("upper", 1000.0), ("lower", 1e-6)):
        pullback = ladders[direction][cap]
        for _ in range(REFINE_L_MAX):
            pullback = nested_refine(pullback)
        expected.update(pullback.tolist())
    assert closure["closure_node_count"] == len(expected)
    probe_noises = [entry[2] for entry in closure["probe_sequence"]]
    assert all(a < b for a, b in zip(probe_noises, probe_noises[1:]))
    grouped = [entry[1] for entry in sorted(closure["nodes"])]
    expected_grouped = [
        stage_id
        for stage_id in DIAGNOSTIC_STAGE_ORDER
        for _ in closure["stages"][stage_id]
    ]
    assert grouped == expected_grouped


def test_completed_document_validates_and_aggregates_recompute() -> None:
    document = run_fake()
    assert document["status"] == "COMPLETED"
    digests = [
        {"node_index": row["node_index"], "record_sha256": "0" * 64}
        for row in document["node_records"]
    ]
    persisted = finalize_document_for_validation(document, digests)
    VALIDATOR.validate(persisted)
    stage_map = _stage_class_map_from_records(
        document["stages"], document["node_records"]
    )
    assert document["aggregates"] == aggregates_from_node_records(
        document["node_records"], stage_map
    )
    by_index = {row["node_index"]: row for row in document["node_records"]}
    probe = small_closure()["probe_sequence"]
    for previous, current in zip(probe, probe[1:]):
        assert (
            by_index[current[0]]["incoming_warm_start"]
            == by_index[previous[0]]["outgoing_warm_start"]
        )


def test_optimizer_failure_carries_warm_start_and_later_nodes_continue(
    monkeypatch,
) -> None:
    original = payload_module.optimize_conditional_v2

    def rigged(*args, node_index=None, **kwargs):
        result = original(*args, node_index=node_index, **kwargs)
        if node_index == 2:
            result["stop"] = True
            result["reason"] = "rigged pathological objective"
            result["u_star"] = None
        return result

    monkeypatch.setattr(payload_module, "optimize_conditional_v2", rigged)
    document = run_fake()
    rows = {row["node_index"]: row for row in document["per_node_diagnostics"]}
    records = {row["node_index"]: row for row in document["node_records"]}
    assert rows[2]["optimizer_accepted"] is False
    assert records[2]["outgoing_warm_start"]["identity"] == records[2][
        "incoming_warm_start"
    ]["identity"]
    assert rows[3]["optimizer_accepted"] is True
    assert document["status"] == "COMPLETED"


def test_conditioning_retry_is_record_only_and_loop_continues() -> None:
    document = run_fake(bridge=smooth_bridge(flat_noise=0.3))
    records = {row["node_index"]: row for row in document["node_records"]}
    assert records[2]["curvature"]["retry"]["fired"] is True
    assert records[3]["accepted"] is True
    assert document["status"] == "COMPLETED"


def test_purity_failure_does_not_halt() -> None:
    document = run_fake(bridge=smooth_bridge(nondeterministic=True))
    assert document["purity"]["pass"] is False
    assert document["status"] == "COMPLETED"
    assert len(document["node_records"]) == 6


def test_g2_mismatch_does_not_halt() -> None:
    document = run_fake(bridge=smooth_bridge(mismatch=True))
    assert document["g2_equivalence"]["all_pass"] is False
    assert document["status"] == "COMPLETED"


def _decision_instance() -> dict:
    instance = valid_instance(accepted=True)
    row = instance["per_node_diagnostics"][0]
    row["raw_symmetry"]["symmetry_ok"] = False
    row["slope_analysis"] = {
        "classification": "TRUNCATION_LIKE",
        "slope": 2.0,
        "intercept": 0.0,
    }
    return instance


def test_decision_table_rows_and_precedence() -> None:
    instance = _decision_instance()
    assert evaluate_decision_table(
        instance, terminal_status="COMPLETED", evidence_complete=True
    )["row"] == 8

    cases = []
    row1 = copy.deepcopy(instance)
    row1["purity"]["pass"] = False
    cases.append((row1, "ABORTED_BUDGET", False, 1))
    cases.append((copy.deepcopy(instance), "ABORTED_BUDGET", True, 2))
    cases.append((copy.deepcopy(instance), "COMPLETED", False, 2))
    row3 = copy.deepcopy(instance)
    row3["per_node_diagnostics"][0] = {
        "node_index": 0,
        "probe_position": 0,
        "stage_id": "level0",
        "noise": 0.1,
        "optimizer_accepted": False,
    }
    cases.append((row3, "COMPLETED", True, 3))
    row4 = copy.deepcopy(instance)
    row4["per_node_diagnostics"][0]["curvature_summary"].update(
        retry_fired=True, retry_positively_accepted=False
    )
    cases.append((row4, "COMPLETED", True, 4))
    row5 = copy.deepcopy(instance)
    row5["g1_battery"]["all_pass"] = False
    cases.append((row5, "COMPLETED", True, 5))
    row6 = copy.deepcopy(instance)
    row6["per_node_diagnostics"][0]["raw_symmetry"]["symmetry_ok"] = True
    cases.append((row6, "COMPLETED", True, 6))
    row7 = copy.deepcopy(instance)
    row7["per_node_diagnostics"][0]["curvature_summary"]["spd_final"] = False
    cases.append((row7, "COMPLETED", True, 7))
    row9 = copy.deepcopy(instance)
    row9["per_node_diagnostics"][0]["slope_analysis"] = {
        "classification": "FLAT",
        "slope": 0.0,
        "intercept": 0.0,
    }
    cases.append((row9, "COMPLETED", True, 9))
    # Row 10 is the total fallback. The closed schema's four classifications
    # make it structurally unreachable today, so exercise totality with a
    # distilled future/unknown label while keeping every other input valid.
    row10 = copy.deepcopy(instance)
    row10["per_node_diagnostics"][0]["slope_analysis"]["classification"] = "OTHER"
    cases.append((row10, "COMPLETED", True, 10))
    for document, status, complete, expected in cases:
        assert evaluate_decision_table(
            document, terminal_status=status, evidence_complete=complete
        )["row"] == expected


def test_decision_table_rows_match_committed_parameters() -> None:
    parameters = json.loads(
        (
            Path(__file__).resolve().parents[1]
            / "docs/m2c_freeze/m2cr_diagnostic_protocol_v1.json"
        ).read_text()
    )
    assert DECISION_TABLE_ROWS == parameters["decision_table"]["rows"]
    result = evaluate_decision_table(
        _decision_instance(), terminal_status="COMPLETED", evidence_complete=True
    )
    assert result == {
        "row": 8,
        "track": "precommitted_b4_branch_b7_global_scope_under_full_closure",
    }


def test_payload_entry_glue_uses_injected_components(monkeypatch) -> None:
    components = {
        "closure": small_closure(),
        "bridge": smooth_bridge(),
        "mode_u_canonical": np.zeros(3),
        "map_noise": 0.06,
        "battery_reference": lambda u, noise: [
            {"reference_value": float(smooth_bridge()(noise)[1](u)[index]), "fd_step": 1e-5}
            for index in range(3)
        ],
        "g_hist": lambda u, noise: smooth_bridge()(noise)[0](u),
        "d23_provider": lambda: [
            {"site": role, "worst_relative": 0.02}
            for role in ("ls", "os", "lv")
        ],
        "prior_draw_provider": prior_draw_provider,
        "computation_storage_order": STORAGE_ORDER,
        "expected_map_noise": 0.061867347763041584,
    }
    monkeypatch.setattr(payload_module, "_real_components", lambda: components)

    class FakeContext:
        def emit(self, *_args, **_kwargs):
            return None

    assert diagnostic_payload_entry(FakeContext())["status"] == "COMPLETED"


def test_consistency_verifier_passes_and_catches_tampering() -> None:
    """Kimi panel finding 2: the distilled curvature_summary/raw_symmetry rows
    and the G2 accepted tail are machine-cross-checked against the
    authoritative per-node evidence, never left to trust."""

    from bistar_gp.m2cr.diagnostic import verify_diagnostic_record_consistency

    document = run_fake()
    digests = [
        {"node_index": row["node_index"], "record_sha256": "0" * 64}
        for row in document["node_records"]
    ]
    records = copy.deepcopy(document["node_records"])
    persisted = finalize_document_for_validation(document, digests)
    assert verify_diagnostic_record_consistency(persisted, records) == {
        "ok": True,
        "errors": [],
    }

    def tampered(mutate):
        doc = copy.deepcopy(persisted)
        mutate(doc)
        return verify_diagnostic_record_consistency(doc, records)

    def row(doc, index):
        return next(
            item
            for item in doc["per_node_diagnostics"]
            if item["node_index"] == index
        )

    first = next(
        item["node_index"]
        for item in persisted["per_node_diagnostics"]
        if item["optimizer_accepted"]
    )
    for label, mutate in (
        (
            "spd_final",
            lambda d: row(d, first)["curvature_summary"].update(spd_final=False),
        ),
        (
            "retry_fired",
            lambda d: row(d, first)["curvature_summary"].update(
                retry_fired=True, retry_positively_accepted=True
            ),
        ),
        (
            "final u",
            lambda d: row(d, first)["final_evaluation_point"].update(
                u=[9.0, 9.0, 9.0]
            ),
        ),
        (
            "symmetry_error",
            lambda d: row(d, first)["raw_symmetry"].update(symmetry_error=0.5),
        ),
        (
            "g2 tail order",
            lambda d: d["g2_equivalence"]["points"].__setitem__(
                slice(11, None),
                list(reversed(d["g2_equivalence"]["points"][11:])),
            ),
        ),
    ):
        report = tampered(mutate)
        assert report["ok"] is False, label
        assert report["errors"], label
