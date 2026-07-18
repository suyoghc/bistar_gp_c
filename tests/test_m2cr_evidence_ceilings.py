"""v1.20 (R2a) evidence-ceiling enforcement battery.

Discriminating requirements (author ballot, D49): exact equality with every
ceiling passes and one byte over fails; ``RAW_MANIFEST.sha256`` can trigger
the per-file or complete-bundle check; the candidate terminal record counts
toward the complete bundle; ``nodes/`` or scratch can breach the bundle while
every per-file ceiling passes; an oversized events/stdout/stderr file fails
its own class even when the bundle stays below its ceiling; no overflow path
truncates, deletes, or omits retained evidence; once a candidate exceeds a
ceiling the outcome remains ``evidence_overflow`` even though the smaller
replacement record would bring the final retained directory under the
ceiling; and a newly introduced ``RUN_DIR_LAYOUT`` file cannot escape
classification or size accounting.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

import bistar_gp.m2cr.capture as capture_module
from bistar_gp.m2cr.audit import verify_evidence_ceiling_compliance
from bistar_gp.m2cr.capture import (
    RAW_MANIFEST_NAME,
    RUN_DIR_LAYOUT,
    TERMINAL_RECORD_NAME,
    assemble_terminal_record,
    capture_run,
    empty_aggregates,
    reconcile_run,
)
from bistar_gp.m2cr.environment_freeze import (
    EVIDENCE_CEILING_MEMBERS,
    EVIDENCE_CEILINGS_KIND,
    EVIDENCE_CEILINGS_RELPATH,
    parse_evidence_ceilings,
)
from bistar_gp.m2cr.measure import classify_run_dir_layout
from bistar_gp.m2cr.serialization import (
    atomic_write_canonical_json,
    canonical_bytes,
    sha256_file,
)
from tests.test_m2cr_capture import (
    AUTHORIZATION_ID,
    CHAIN,
    LAUNCH_ATTEMPT_ID,
    _make_launch,
)

ROOT = Path(__file__).resolve().parents[1]
COMMITTED_CEILINGS = ROOT / EVIDENCE_CEILINGS_RELPATH
COMMITTED_INFRA = ROOT / "docs/m2c_freeze/m2cr_infrastructure_manifest_v1.json"

# The v1.20-ratified values, written INDEPENDENTLY here (never read back from
# the artifact or the report) so agreement is a real cross-check.
V120_EXPECTED = {
    "runtime_envelope_static_artifact_per_file_bytes": 33_554_432,
    "event_stream_bytes": 33_554_432,
    "stdout_bytes": 16_777_216,
    "stderr_bytes": 16_777_216,
    "complete_bundle_bytes": 134_217_728,
}


def _ceilings(**overrides: int) -> dict[str, int]:
    values = {
        "runtime_envelope_static_artifact_per_file_bytes": 10_000,
        "event_stream_bytes": 10_000,
        "stdout_bytes": 10_000,
        "stderr_bytes": 10_000,
        "complete_bundle_bytes": 1_000_000,
    }
    values.update(overrides)
    return values


def _snapshot(run_dir: Path) -> dict[str, bytes]:
    return {
        path.relative_to(run_dir).as_posix(): path.read_bytes()
        for path in sorted(run_dir.rglob("*"))
        if path.is_file()
    }


def _completed_record() -> dict[str, object]:
    return assemble_terminal_record(
        record_kind="diagnostic",
        status="COMPLETED",
        run_id="m2cr-ceilings-test",
        launch_attempt_id=LAUNCH_ATTEMPT_ID,
        chain=CHAIN,
        evidence={
            "raw_manifest_sha256": "a" * 64,
            "node_evidence_digests": [
                {"node_index": 0, "record_sha256": "c" * 64}
            ],
            "event_stream_balanced": True,
        },
        stages=[
            {
                "stage_id": "level0",
                "stage_class": "verdict",
                "status": "COMPLETED",
                "nodes_evaluated": 1,
                "nodes_total": 1,
            }
        ],
        aggregates=empty_aggregates(),
    )


def _infra_record(
    detail: str = "synthetic capture fault", reconstructed: bool = False
) -> dict[str, object]:
    return assemble_terminal_record(
        record_kind="diagnostic",
        status="INFRA_FAILURE",
        run_id="m2cr-ceilings-test",
        launch_attempt_id=LAUNCH_ATTEMPT_ID,
        chain=CHAIN,
        evidence={
            "raw_manifest_sha256": "a" * 64,
            "node_evidence_digests": [],
            "event_stream_balanced": False,
        },
        infra_fault={
            "fault_class": "capture_fault",
            "detail": detail,
            "reconstructed": reconstructed,
            "payload_started": False,
        },
    )


# ---------------------------------------------------------------------------
# The committed artifact and its closed-world parse.


def test_committed_ceilings_artifact_matches_v120_integers():
    document = json.loads(COMMITTED_CEILINGS.read_text(encoding="utf-8"))
    assert document["kind"] == EVIDENCE_CEILINGS_KIND
    assert document["schema_version"] == 1
    assert document["addendum"] == "v1.20"
    parsed = parse_evidence_ceilings(document)
    assert parsed == V120_EXPECTED
    # Cross-derivation of the independently written integers.
    assert V120_EXPECTED[
        "runtime_envelope_static_artifact_per_file_bytes"
    ] == 32 * 1024**2
    assert V120_EXPECTED["event_stream_bytes"] == 32 * 1024**2
    assert V120_EXPECTED["stdout_bytes"] == 16 * 1024**2
    assert V120_EXPECTED["stderr_bytes"] == 16 * 1024**2
    assert V120_EXPECTED["complete_bundle_bytes"] == 128 * 1024**2
    # The artifact itself trivially obeys its own per-file ceiling.
    assert COMMITTED_CEILINGS.stat().st_size <= parsed[
        "runtime_envelope_static_artifact_per_file_bytes"
    ]


def test_parse_evidence_ceilings_closed_world_negatives():
    def document(**mutations):
        base = {
            "kind": EVIDENCE_CEILINGS_KIND,
            "schema_version": 1,
            "addendum": "v1.20",
            "ceilings": dict(V120_EXPECTED),
        }
        base.update(mutations)
        return base

    parse_evidence_ceilings(document())  # the well-formed shape parses
    with pytest.raises(ValueError, match="not an object"):
        parse_evidence_ceilings(["not", "an", "object"])
    with pytest.raises(ValueError, match="exactly"):
        parse_evidence_ceilings(document(extra_key=1))
    with pytest.raises(ValueError, match="wrong kind"):
        parse_evidence_ceilings(document(kind="something_else"))
    with pytest.raises(ValueError, match="schema_version"):
        parse_evidence_ceilings(document(schema_version=2))
    with pytest.raises(ValueError, match="addendum"):
        parse_evidence_ceilings(document(addendum=""))
    missing = dict(V120_EXPECTED)
    missing.pop("stderr_bytes")
    with pytest.raises(ValueError, match="exactly"):
        parse_evidence_ceilings(document(ceilings=missing))
    extra = dict(V120_EXPECTED, surprise_bytes=1)
    with pytest.raises(ValueError, match="exactly"):
        parse_evidence_ceilings(document(ceilings=extra))
    for bad in (True, 0, -5, 1.5, "33554432", None):
        mutated = dict(V120_EXPECTED, stdout_bytes=bad)
        with pytest.raises(ValueError, match="positive integer"):
            parse_evidence_ceilings(document(ceilings=mutated))


def test_committed_infrastructure_manifest_pins_evidence_ceilings():
    manifest = json.loads(COMMITTED_INFRA.read_text(encoding="utf-8"))
    pin = manifest["artifacts"]["evidence_ceilings"]
    assert pin["path"] == EVIDENCE_CEILINGS_RELPATH
    assert pin["sha256"] == sha256_file(COMMITTED_CEILINGS)


def test_audit_static_compliance_passes_on_committed_tree():
    result = verify_evidence_ceiling_compliance(COMMITTED_INFRA, repo_root=ROOT)
    assert result["errors"] == []
    assert result["ok"] is True
    labels = {check["label"] for check in result["checks"]}
    assert "artifacts:importable_artifact_manifest" in labels
    assert "artifacts:evidence_ceilings" in labels
    assert "infrastructure_manifest" in labels


def test_audit_static_compliance_fails_on_oversized_static_artifact(tmp_path):
    freeze = tmp_path / "docs" / "m2c_freeze"
    freeze.mkdir(parents=True)
    ceilings_doc = {
        "kind": EVIDENCE_CEILINGS_KIND,
        "schema_version": 1,
        "addendum": "v1.20",
        "ceilings": _ceilings(
            runtime_envelope_static_artifact_per_file_bytes=100
        ),
    }
    ceilings_path = freeze / "m2cr_evidence_ceilings_v1.json"
    atomic_write_canonical_json(ceilings_path, ceilings_doc)
    fat = freeze / "m2cr_dependency_lock_v1.json"
    fat.write_bytes(b"x" * 101)
    exact = freeze / "m2cr_child_env_mapping_v1.json"
    exact.write_bytes(b"y" * 100)
    infra = {
        "kind": "m2cr_infrastructure_manifest",
        "schema_version": 1,
        "artifacts": {
            "evidence_ceilings": {
                "path": "docs/m2c_freeze/m2cr_evidence_ceilings_v1.json",
                "sha256": sha256_file(ceilings_path),
            },
            "dependency_lock": {
                "path": "docs/m2c_freeze/m2cr_dependency_lock_v1.json",
                "sha256": sha256_file(fat),
            },
            "child_env_mapping": {
                "path": "docs/m2c_freeze/m2cr_child_env_mapping_v1.json",
                "sha256": sha256_file(exact),
            },
        },
    }
    infra_path = freeze / "m2cr_infrastructure_manifest_v1.json"
    atomic_write_canonical_json(infra_path, infra)
    result = verify_evidence_ceiling_compliance(infra_path, repo_root=tmp_path)
    assert result["ok"] is False
    assert any(
        "artifacts:dependency_lock" in error and "101 B exceeds" in error
        for error in result["errors"]
    )
    # Exact equality passes: only the one-over artifact is reported.
    assert not any("child_env_mapping" in error for error in result["errors"])


# ---------------------------------------------------------------------------
# Boundary semantics: exact equality passes; one byte over fails.


@pytest.mark.parametrize(
    "name,member,klass_label",
    [
        ("prelaunch.json", "runtime_envelope_static_artifact_per_file_bytes",
         "runtime-envelope/static-artifact per-file"),
        ("events.jsonl", "event_stream_bytes", "event-stream"),
        ("stdout.txt", "stdout_bytes", "stdout"),
        ("stderr.txt", "stderr_bytes", "stderr"),
    ],
)
def test_boundary_exact_equality_passes_one_byte_over_fails(
    tmp_path, name, member, klass_label
):
    size = 64
    (tmp_path / name).write_bytes(b"x" * size)
    at_limit = capture_module._evidence_ceiling_breaches(
        tmp_path, 0, _ceilings(**{member: size})
    )
    assert at_limit == []
    over = capture_module._evidence_ceiling_breaches(
        tmp_path, 0, _ceilings(**{member: size - 1})
    )
    assert [
        (item["class"], item["path"], item["observed"], item["ceiling"])
        for item in over
    ] == [(klass_label, name, size, size - 1)]


def test_boundary_candidate_record_per_file_and_bundle(tmp_path):
    # Candidate record at exactly the per-file ceiling passes; one byte over
    # fails; and the bundle boundary counts the candidate too.
    assert (
        capture_module._evidence_ceiling_breaches(
            tmp_path,
            500,
            _ceilings(
                runtime_envelope_static_artifact_per_file_bytes=500,
                complete_bundle_bytes=500,
            ),
        )
        == []
    )
    over = capture_module._evidence_ceiling_breaches(
        tmp_path,
        501,
        _ceilings(
            runtime_envelope_static_artifact_per_file_bytes=500,
            complete_bundle_bytes=501,
        ),
    )
    assert len(over) == 1
    assert over[0]["path"] == f"{TERMINAL_RECORD_NAME} (candidate)"
    bundle_over = capture_module._evidence_ceiling_breaches(
        tmp_path,
        501,
        _ceilings(
            runtime_envelope_static_artifact_per_file_bytes=501,
            complete_bundle_bytes=500,
        ),
    )
    assert len(bundle_over) == 1
    assert bundle_over[0]["class"] == "complete-bundle"
    assert bundle_over[0]["observed"] == 501


def test_raw_manifest_triggers_per_file_and_bundle_checks(tmp_path):
    # Requirement 2a: RAW_MANIFEST.sha256 is priced by BOTH the per-file class
    # and the bundle aggregate.
    (tmp_path / RAW_MANIFEST_NAME).write_bytes(b"m" * 90)
    per_file = capture_module._evidence_ceiling_breaches(
        tmp_path,
        0,
        _ceilings(runtime_envelope_static_artifact_per_file_bytes=89),
    )
    assert [(item["class"], item["path"]) for item in per_file] == [
        ("runtime-envelope/static-artifact per-file", RAW_MANIFEST_NAME)
    ]
    bundle = capture_module._evidence_ceiling_breaches(
        tmp_path, 0, _ceilings(complete_bundle_bytes=89)
    )
    assert [(item["class"], item["observed"]) for item in bundle] == [
        ("complete-bundle", 90)
    ]


def test_nodes_and_scratch_breach_bundle_while_per_file_passes(tmp_path):
    # Requirement 2c: no per-file ceiling governs nodes/ or scratch; only the
    # bundle aggregate can fail.
    (tmp_path / "nodes").mkdir()
    (tmp_path / "nodes" / "node_000000.json").write_bytes(b"n" * 400)
    (tmp_path / "home").mkdir()
    (tmp_path / "home" / "payload_scratch.bin").write_bytes(b"s" * 400)
    breaches = capture_module._evidence_ceiling_breaches(
        tmp_path,
        10,
        _ceilings(
            runtime_envelope_static_artifact_per_file_bytes=50,
            complete_bundle_bytes=809,
        ),
    )
    assert [(item["class"], item["observed"]) for item in breaches] == [
        ("complete-bundle", 810)
    ]


def test_stream_class_breach_without_bundle_breach(tmp_path):
    # Requirement 2d: an oversized events/stdout/stderr file fails its own
    # class even when the complete bundle stays far below its ceiling.
    (tmp_path / "events.jsonl").write_bytes(b"e" * 120)
    (tmp_path / "stdout.txt").write_bytes(b"o" * 120)
    (tmp_path / "stderr.txt").write_bytes(b"r" * 120)
    breaches = capture_module._evidence_ceiling_breaches(
        tmp_path,
        0,
        _ceilings(
            event_stream_bytes=119, stdout_bytes=119, stderr_bytes=119
        ),
    )
    assert sorted(item["class"] for item in breaches) == [
        "event-stream",
        "stderr",
        "stdout",
    ]
    assert not any(item["class"] == "complete-bundle" for item in breaches)


def test_bundle_counts_every_regular_file_and_stray(tmp_path):
    # Requirement 4 (completeness): every retained regular file beneath the
    # run directory counts — RAW_MANIFEST.sha256, nested nodes/scratch files,
    # unclassified strays — plus the candidate terminal record; directories
    # themselves are excluded, and a nested file named like the terminal
    # record is still counted (only the ROOT path is the candidate's).
    (tmp_path / RAW_MANIFEST_NAME).write_bytes(b"m" * 11)
    (tmp_path / "prelaunch.json").write_bytes(b"p" * 7)
    (tmp_path / "nodes").mkdir()
    (tmp_path / "nodes" / "node_000000.json").write_bytes(b"n" * 13)
    (tmp_path / "nodes" / TERMINAL_RECORD_NAME).write_bytes(b"t" * 5)
    (tmp_path / "tmp").mkdir()
    (tmp_path / "tmp" / "kmp_scratch").write_bytes(b"k" * 3)
    (tmp_path / "stray_unclassified.bin").write_bytes(b"z" * 17)
    candidate_bytes = 19
    total = 11 + 7 + 13 + 5 + 3 + 17 + candidate_bytes
    assert (
        capture_module._evidence_ceiling_breaches(
            tmp_path, candidate_bytes, _ceilings(complete_bundle_bytes=total)
        )
        == []
    )
    breaches = capture_module._evidence_ceiling_breaches(
        tmp_path, candidate_bytes, _ceilings(complete_bundle_bytes=total - 1)
    )
    assert [(item["class"], item["observed"]) for item in breaches] == [
        ("complete-bundle", total)
    ]


def test_new_layout_member_cannot_escape_classification(monkeypatch, tmp_path):
    # Requirement 4 (fail-closed): a newly introduced RUN_DIR_LAYOUT file
    # without an explicit measurement classification breaks classification
    # itself AND the enforcement path that derives its class map from it.
    extended = RUN_DIR_LAYOUT + ("brand_new_evidence.json",)
    with pytest.raises(ValueError, match="brand_new_evidence.json"):
        classify_run_dir_layout(extended)
    monkeypatch.setattr(capture_module, "RUN_DIR_LAYOUT", extended)
    with pytest.raises(ValueError, match="brand_new_evidence.json"):
        capture_module._evidence_ceiling_breaches(tmp_path, 0, _ceilings())


# ---------------------------------------------------------------------------
# The candidate-record decision.


def test_apply_replaces_completed_candidate_and_preserves_evidence(tmp_path):
    (tmp_path / "events.jsonl").write_bytes(b"e" * 300)
    (tmp_path / RAW_MANIFEST_NAME).write_bytes(b"m" * 20)
    before = _snapshot(tmp_path)
    candidate = _completed_record()
    ceilings = _ceilings(event_stream_bytes=299)
    outcome = capture_module._apply_evidence_ceilings(
        tmp_path, candidate, ceilings
    )
    assert outcome["status"] == "INFRA_FAILURE"
    assert outcome["fault"]["fault_class"] == "evidence_overflow"
    detail = outcome["fault"]["detail"]
    assert "event-stream events.jsonl: observed 300 B exceeds ceiling 299 B" in detail
    assert "displaced candidate outcome: COMPLETED" in detail
    # Requirement 2e: nothing was truncated, deleted, or omitted.
    assert _snapshot(tmp_path) == before
    # Candidate rule: the replacement record is NOT re-priced — even though
    # the final retained directory (with the smaller replacement) would obey
    # the same event ceiling only the candidate's sizes decided the outcome.
    assert outcome["fault"]["reconstructed"] is False
    # The replacement is deliberately minimal: the evidence digest block
    # carries over, while stages/aggregates stay in the RETAINED raw evidence
    # (nodes/, events.jsonl) rather than the replacement envelope, so the
    # replacement is structurally bounded and cannot compound the overflow.
    assert outcome["evidence"] == candidate["evidence"]
    assert "stages" not in outcome
    assert "aggregates" not in outcome


def test_candidate_rule_outcome_stays_failed_when_replacement_fits(tmp_path):
    # Requirement 3: the candidate's own serialization pushes the bundle over;
    # the SMALLER replacement record would fit under the same ceiling, and the
    # outcome is still evidence_overflow.  A result-kind candidate carries a
    # fat ``result_payload`` — dropped by the INFRA_FAILURE replacement branch
    # by schema construction — so replacement < candidate genuinely.
    (tmp_path / "prelaunch.json").write_bytes(b"p" * 10)
    result_chain = {
        **CHAIN,
        "diagnostic_record_sha256": "d" * 64,
        "amendment_manifest": "none",
    }
    candidate = assemble_terminal_record(
        record_kind="result",
        status="COMPLETED",
        run_id="m2cr-ceilings-test",
        launch_attempt_id=LAUNCH_ATTEMPT_ID,
        chain=result_chain,
        evidence={
            "raw_manifest_sha256": "a" * 64,
            "node_evidence_digests": [
                {"node_index": 0, "record_sha256": "c" * 64}
            ],
            "event_stream_balanced": True,
        },
        stages=[
            {
                "stage_id": "level0",
                "stage_class": "verdict",
                "status": "COMPLETED",
                "nodes_evaluated": 1,
                "nodes_total": 1,
            }
        ],
        aggregates=empty_aggregates(),
        payload={
            "result_payload": {
                "profile_band_masses": {
                    "lo": 0.25,
                    "mid": 0.5,
                    "hi": 0.25,
                    "sum": 1.0,
                },
                "numerical_sensitivity": {"lo": 0.0, "mid": 0.0, "hi": 0.0},
                "realized_grids": [
                    {
                        "stage_id": f"padding_grid_{index:04d}_" + "x" * 80,
                        "n_nodes": 1,
                        "min_noise": 0.1,
                        "max_noise": 1.0,
                    }
                    for index in range(40)
                ],
            }
        },
    )
    candidate_bytes = len(canonical_bytes(candidate))
    bundle_ceiling = 10 + candidate_bytes - 1
    outcome = capture_module._apply_evidence_ceilings(
        tmp_path, candidate, _ceilings(complete_bundle_bytes=bundle_ceiling)
    )
    assert outcome["status"] == "INFRA_FAILURE"
    assert outcome["fault"]["fault_class"] == "evidence_overflow"
    assert (
        f"complete-bundle complete_bundle: observed {10 + candidate_bytes} B"
        in outcome["fault"]["detail"]
    )
    # The replacement drops the result_payload (the INFRA branch carries
    # none), so it really IS smaller than the candidate and the final
    # retained directory fits under the very ceiling the candidate breached —
    # proving the outcome was decided on the candidate and never reconsidered.
    assert "result_payload" not in outcome
    replacement_bytes = len(canonical_bytes(outcome))
    assert replacement_bytes < candidate_bytes
    assert (
        capture_module._evidence_ceiling_breaches(
            tmp_path,
            replacement_bytes,
            _ceilings(complete_bundle_bytes=bundle_ceiling),
        )
        == []
    ), "test rig: the replacement must fit for the rule to be discriminating"


def test_apply_elevates_infra_candidate_and_preserves_displaced_fault(tmp_path):
    (tmp_path / "stderr.txt").write_bytes(b"r" * 40)
    candidate = _infra_record(
        detail="terminal envelope reconstructed after parent death",
        reconstructed=True,
    )
    outcome = capture_module._apply_evidence_ceilings(
        tmp_path, candidate, _ceilings(stderr_bytes=39)
    )
    assert outcome["status"] == "INFRA_FAILURE"
    assert outcome["fault"]["fault_class"] == "evidence_overflow"
    assert outcome["fault"]["reconstructed"] is True
    assert (
        "displaced candidate fault: capture_fault: terminal envelope "
        "reconstructed after parent death" in outcome["fault"]["detail"]
    )


def test_apply_passthrough_for_ratified_precedence_statuses(tmp_path):
    (tmp_path / "stdout.txt").write_bytes(b"o" * 999)
    aborted = assemble_terminal_record(
        record_kind="diagnostic",
        status="ABORTED_BUDGET",
        run_id="m2cr-ceilings-test",
        launch_attempt_id=LAUNCH_ATTEMPT_ID,
        chain=CHAIN,
        evidence={
            "raw_manifest_sha256": "a" * 64,
            "node_evidence_digests": [],
            "event_stream_balanced": False,
        },
        interruption_info={
            "ceiling_hours": 8.0,
            "signal_sequence": ["SIGTERM"],
            "grace_seconds": 30,
            "sigkill_issued": False,
        },
    )
    not_started = assemble_terminal_record(
        record_kind="diagnostic",
        status="NOT_STARTED",
        run_id="m2cr-ceilings-test",
        launch_attempt_id=LAUNCH_ATTEMPT_ID,
        chain=CHAIN,
        not_started_info={
            "prelaunch_sha256": "b" * 64,
            "reason": "spawn not confirmed: synthetic",
        },
    )
    tiny = _ceilings(stdout_bytes=1, complete_bundle_bytes=1)
    assert (
        capture_module._apply_evidence_ceilings(tmp_path, aborted, tiny)
        == aborted
    )
    assert (
        capture_module._apply_evidence_ceilings(tmp_path, not_started, tiny)
        == not_started
    )


def test_apply_fails_closed_on_enforcement_error(tmp_path):
    completed = _completed_record()
    # Empty ceilings: the decision cannot price anything — a certifiable
    # candidate must fail CLOSED as a capture_fault INFRA_FAILURE.
    outcome = capture_module._apply_evidence_ceilings(tmp_path, completed, {})
    assert outcome["status"] == "INFRA_FAILURE"
    assert outcome["fault"]["fault_class"] == "capture_fault"
    assert "evidence-ceiling enforcement failed" in outcome["fault"]["detail"]
    # An already-INFRA_FAILURE candidate stays unchanged (already closed).
    infra = _infra_record()
    assert capture_module._apply_evidence_ceilings(tmp_path, infra, {}) == infra


# ---------------------------------------------------------------------------
# End-to-end: the full authenticated production path.


def test_capture_run_replaces_completed_outcome_on_bundle_overflow(tmp_path):
    config = _make_launch(
        tmp_path,
        mode="completed",
        ceilings_mutator=lambda doc: doc["ceilings"].update(
            complete_bundle_bytes=5_000
        ),
    )
    record = capture_run(config)
    assert record["status"] == "INFRA_FAILURE"
    assert record["fault"]["fault_class"] == "evidence_overflow"
    detail = record["fault"]["detail"]
    assert "complete-bundle complete_bundle: observed" in detail
    assert "exceeds ceiling 5000 B" in detail
    assert "displaced candidate outcome: COMPLETED" in detail
    assert record["fault"]["payload_started"] is True
    run_dir = Path(config.run_dir)
    published = json.loads(
        (run_dir / TERMINAL_RECORD_NAME).read_text(encoding="utf-8")
    )
    assert published == record
    # Requirement 2e end to end: the complete oversized evidence is retained.
    for retained in (
        "prelaunch.json",
        "spawned.json",
        "payload_started.json",
        "events.jsonl",
        "stdout.txt",
        "stderr.txt",
        RAW_MANIFEST_NAME,
        "payload.json",
    ):
        assert (run_dir / retained).is_file(), retained


# ---------------------------------------------------------------------------
# Reconciliation coverage.


def _reconciliation_fixture(
    tmp_path, *, bundle_ceiling: int
) -> tuple[Path, str]:
    worktree = tmp_path / "worktree"
    freeze = worktree / "docs" / "m2c_freeze"
    freeze.mkdir(parents=True)
    ceilings_doc = {
        "kind": EVIDENCE_CEILINGS_KIND,
        "schema_version": 1,
        "addendum": "v1.20",
        "ceilings": _ceilings(complete_bundle_bytes=bundle_ceiling),
    }
    ceilings_path = freeze / "m2cr_evidence_ceilings_v1.json"
    atomic_write_canonical_json(ceilings_path, ceilings_doc)
    infra = {
        "kind": "m2cr_infrastructure_manifest",
        "schema_version": 1,
        "artifacts": {
            "evidence_ceilings": {
                "path": "docs/m2c_freeze/m2cr_evidence_ceilings_v1.json",
                "sha256": sha256_file(ceilings_path),
            }
        },
    }
    infra_path = freeze / "m2cr_infrastructure_manifest_v1.json"
    atomic_write_canonical_json(infra_path, infra)
    return worktree, sha256_file(infra_path)


def _reconciliation_run_dir(tmp_path, worktree_root: str, infra_sha: str) -> Path:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    chain = {**CHAIN, "infrastructure_manifest_sha256": infra_sha}
    prelaunch = {
        "schema_version": 1,
        "config": {
            "record_kind": "diagnostic",
            "run_id": "m2cr-ceilings-test",
            "launch_attempt_id": LAUNCH_ATTEMPT_ID,
            "authorization_id": AUTHORIZATION_ID,
            "chain": chain,
            "worktree_root": worktree_root,
        },
    }
    atomic_write_canonical_json(run_dir / "prelaunch.json", prelaunch)
    (run_dir / "stdout.txt").write_bytes(b"o" * 4_000)
    return run_dir


def test_reconcile_run_applies_ceilings_from_captured_provenance(tmp_path):
    worktree, infra_sha = _reconciliation_fixture(tmp_path, bundle_ceiling=1_000)
    run_dir = _reconciliation_run_dir(
        tmp_path, os.fspath(worktree), infra_sha
    )
    record = reconcile_run(run_dir)
    assert record["status"] == "INFRA_FAILURE"
    assert record["fault"]["fault_class"] == "evidence_overflow"
    assert record["fault"]["reconstructed"] is True
    assert "complete-bundle" in record["fault"]["detail"]
    assert (
        "displaced candidate fault: capture_fault: terminal envelope "
        "reconstructed after parent death" in record["fault"]["detail"]
    )


def test_reconcile_run_discloses_unavailable_ceilings(tmp_path):
    run_dir = _reconciliation_run_dir(
        tmp_path, os.fspath(tmp_path / "gone-worktree"), "c" * 64
    )
    record = reconcile_run(run_dir)
    assert record["status"] == "INFRA_FAILURE"
    assert record["fault"]["fault_class"] == "capture_fault"
    assert record["fault"]["reconstructed"] is True
    assert "evidence-ceiling check unavailable" in record["fault"]["detail"]
