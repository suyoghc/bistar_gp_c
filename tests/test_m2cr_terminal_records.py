from __future__ import annotations

from copy import deepcopy

import pytest

from bistar_gp.m2cr.capture import (
    RecordAssemblyError,
    _last_resort_terminal_record,
    aggregates_from_node_records,
    assemble_terminal_record,
    empty_aggregates,
    validate_terminal_record,
)


AUTHORIZATION_ID = "m2cr-auth-20260716-01"
LAUNCH_ATTEMPT_ID = "m2cr-launch-20260716-01"
RUN_ID = "m2cr-test-run"
EXECUTION_COMMIT = "a" * 40
V117 = "65381bc774e894dd9aaf2207cadd9cfa2f2735dafceff4bb39492086a9e522e2"


def _chain(kind: str) -> dict[str, str]:
    chain = {
        "v117_canonical_sha256": V117,
        "infrastructure_manifest_sha256": "1" * 64,
        "environment_freeze_manifest_sha256": "2" * 64,
        "protocol_manifest_sha256": "3" * 64,
        "execution_commit": EXECUTION_COMMIT,
        "authorization_id": AUTHORIZATION_ID,
    }
    if kind == "result":
        chain.update(diagnostic_record_sha256="4" * 64, amendment_manifest="none")
    return chain


STAGES = [
    {
        "stage_id": "level0",
        "stage_class": "verdict",
        "status": "COMPLETED",
        "nodes_evaluated": 1,
        "nodes_total": 1,
    }
]
AGGREGATES = empty_aggregates()
EVIDENCE = {
    "raw_manifest_sha256": "5" * 64,
    "node_evidence_digests": [{"node_index": 0, "record_sha256": "6" * 64}],
    "event_stream_balanced": True,
}
RESULT_PAYLOAD = {
    "result_payload": {
        "profile_band_masses": {"lo": 0.2, "mid": 0.5, "hi": 0.3, "sum": 1.0},
        "numerical_sensitivity": {"lo": 0.0, "mid": 0.0, "hi": 0.0},
        "realized_grids": [
            {"stage_id": "level0", "n_nodes": 1, "min_noise": 0.1, "max_noise": 0.1}
        ],
    }
}
STOP = {
    "stage": "curvature",
    "reason": "synthetic stop",
    "node_index": 0,
    "observed": {},
}
INTERRUPTION = {
    "ceiling_hours": 12.0,
    "signal_sequence": ["SIGTERM", "SIGKILL"],
    "grace_seconds": 30,
    "sigkill_issued": True,
}
FAULT = {
    "fault_class": "child_death",
    "detail": "synthetic child death",
    "reconstructed": False,
    "payload_started": True,
}
NOT_STARTED = {"prelaunch_sha256": "7" * 64, "reason": "spawn failed"}


@pytest.mark.parametrize(
    ("kind", "status"),
    [
        ("diagnostic", "COMPLETED"),
        ("result", "COMPLETED"),
        ("result", "ALGORITHM_STOP"),
        ("diagnostic", "ABORTED_BUDGET"),
        ("result", "ABORTED_BUDGET"),
        ("diagnostic", "INFRA_FAILURE"),
        ("result", "INFRA_FAILURE"),
        ("diagnostic", "NOT_STARTED"),
        ("result", "NOT_STARTED"),
    ],
)
def test_every_representable_status_kind_branch_validates(
    kind: str, status: str
) -> None:
    arguments = {
        "record_kind": kind,
        "status": status,
        "run_id": RUN_ID,
        "launch_attempt_id": LAUNCH_ATTEMPT_ID,
        "chain": _chain(kind),
    }
    if status in {"COMPLETED", "ALGORITHM_STOP"}:
        arguments.update(evidence=EVIDENCE, stages=STAGES, aggregates=AGGREGATES)
    if status == "COMPLETED" and kind == "result":
        arguments["payload"] = RESULT_PAYLOAD
    elif status == "ALGORITHM_STOP":
        arguments["stop_info"] = STOP
    elif status == "ABORTED_BUDGET":
        arguments.update(
            evidence=EVIDENCE,
            stages=STAGES,
            aggregates=AGGREGATES,
            interruption_info=INTERRUPTION,
        )
    elif status == "INFRA_FAILURE":
        arguments.update(evidence=EVIDENCE, infra_fault=FAULT)
    elif status == "NOT_STARTED":
        arguments["not_started_info"] = NOT_STARTED
    record = assemble_terminal_record(**arguments)
    validate_terminal_record(record)


def test_diagnostic_completed_is_explicitly_not_a_result() -> None:
    record = assemble_terminal_record(
        record_kind="diagnostic",
        status="COMPLETED",
        run_id=RUN_ID,
        launch_attempt_id=LAUNCH_ATTEMPT_ID,
        chain=_chain("diagnostic"),
        evidence=EVIDENCE,
        stages=STAGES,
        aggregates=AGGREGATES,
    )
    assert record["not_a_result"] is True
    stripped = deepcopy(record)
    stripped.pop("not_a_result")
    with pytest.raises(RecordAssemblyError):
        validate_terminal_record(stripped)


def test_diagnostic_algorithm_stop_is_unrepresentable() -> None:
    with pytest.raises(RecordAssemblyError, match="unrepresentable"):
        assemble_terminal_record(
            record_kind="diagnostic",
            status="ALGORITHM_STOP",
            run_id=RUN_ID,
            launch_attempt_id=LAUNCH_ATTEMPT_ID,
            chain=_chain("diagnostic"),
            evidence=EVIDENCE,
            stages=STAGES,
            aggregates=AGGREGATES,
            stop_info=STOP,
        )
    hand_built = {
        "schema_version": 1,
        "record_kind": "diagnostic",
        "status": "ALGORITHM_STOP",
        "not_a_result": True,
        "run_id": RUN_ID,
        "launch_attempt_id": LAUNCH_ATTEMPT_ID,
        "chain": _chain("diagnostic"),
        "stop": STOP,
        "stages": STAGES,
        "aggregates": AGGREGATES,
        "evidence": EVIDENCE,
    }
    with pytest.raises(RecordAssemblyError):
        validate_terminal_record(hand_built)


def test_aggregates_count_both_pre_and_post_retry_evaluations() -> None:
    nodes = [
        {
            "node_index": 0,
            "stage_id": "level0",
            "optimizer": {"restart_count": 2},
            "battery": {"pass": False},
            "curvature": {
                "retry": {"fired": True, "positively_accepted": False},
                "pre_retry": {
                    "spd": False,
                    "conditioning_ok": False,
                    "symmetry_ok": False,
                },
                "post_retry": {
                    "spd": True,
                    "conditioning_ok": False,
                    "symmetry_ok": True,
                },
            },
        },
        {
            "node_index": 1,
            "stage_id": "cap_1e-6",
            "optimizer": {"restart_count": 1},
            "battery": {"pass": True},
            "curvature": {
                "retry": {"fired": False},
                "pre_retry": {
                    "spd": True,
                    "conditioning_ok": True,
                    "symmetry_ok": False,
                },
            },
        },
    ]
    totals = aggregates_from_node_records(
        nodes, {"level0": "verdict", "cap_1e-6": "diagnostic"}
    )
    assert totals["verdict_class"] == {
        "restart_count": 2,
        "retry_count": 1,
        "retry_failure_count": 1,
        "rcond_fail_count": 2,
        "symmetry_fail_count": 1,
        "battery_fail_count": 1,
    }
    assert totals["diagnostic_class"] == {
        "restart_count": 1,
        "retry_count": 0,
        "retry_failure_count": 0,
        "rcond_fail_count": 0,
        "symmetry_fail_count": 1,
        "battery_fail_count": 0,
    }


@pytest.mark.parametrize("stage", ["budget", "infrastructure"])
def test_stop_stage_excludes_budget_and_infrastructure(stage: str) -> None:
    with pytest.raises(RecordAssemblyError):
        assemble_terminal_record(
            record_kind="result",
            status="ALGORITHM_STOP",
            run_id=RUN_ID,
            launch_attempt_id=LAUNCH_ATTEMPT_ID,
            chain=_chain("result"),
            evidence=EVIDENCE,
            stages=STAGES,
            aggregates=AGGREGATES,
            stop_info={**STOP, "stage": stage},
        )


def test_grace_seconds_is_frozen_to_thirty() -> None:
    bad = {**INTERRUPTION, "grace_seconds": 29}
    with pytest.raises(RecordAssemblyError):
        assemble_terminal_record(
            record_kind="result",
            status="ABORTED_BUDGET",
            run_id=RUN_ID,
            launch_attempt_id=LAUNCH_ATTEMPT_ID,
            chain=_chain("result"),
            evidence=EVIDENCE,
            stages=STAGES,
            aggregates=AGGREGATES,
            interruption_info=bad,
        )


@pytest.mark.parametrize("kind", ["diagnostic", "result"])
def test_last_resort_record_is_schema_valid_by_construction(kind: str) -> None:
    """FIX C4: the assembly fallback validates even over degenerate inputs."""

    record = _last_resort_terminal_record(
        record_kind=kind,
        run_id=RUN_ID,
        launch_attempt_id=LAUNCH_ATTEMPT_ID,
        chain=_chain(kind),
        evidence={
            "raw_manifest_sha256": "not-a-digest",
            "node_evidence_digests": [
                {"node_index": True, "record_sha256": "6" * 64},
                {"node_index": -1, "record_sha256": "6" * 64},
                {"node_index": 2, "record_sha256": "junk"},
                {"node_index": 1, "record_sha256": "6" * 64},
            ],
            "event_stream_balanced": "yes",
        },
        detail="x" * 100_000,
        payload_started=True,
    )
    validate_terminal_record(record)
    assert record["status"] == "INFRA_FAILURE"
    assert record["fault"]["fault_class"] == "other"
    assert record["fault"]["reconstructed"] is False
    assert record["fault"]["payload_started"] is True
    assert len(record["fault"]["detail"]) == 4000
    assert record["evidence"]["raw_manifest_sha256"] == "0" * 64
    assert record["evidence"]["node_evidence_digests"] == [
        {"node_index": 1, "record_sha256": "6" * 64}
    ]
    assert record["evidence"]["event_stream_balanced"] is True
    assert (record.get("not_a_result") is True) == (kind == "diagnostic")


def test_last_resort_record_survives_empty_detail_and_evidence() -> None:
    """FIX C4: the fallback cannot itself fail on missing inputs."""

    record = _last_resort_terminal_record(
        record_kind="diagnostic",
        run_id=RUN_ID,
        launch_attempt_id=LAUNCH_ATTEMPT_ID,
        chain=_chain("diagnostic"),
        evidence={},
        detail="",
        payload_started=False,
    )
    validate_terminal_record(record)
    assert record["fault"]["detail"].endswith("terminal assembly failed")
    assert record["fault"]["detail"].startswith("last-resort envelope")
    assert record["evidence"]["node_evidence_digests"] == []
    assert record["evidence"]["event_stream_balanced"] is False
