"""Hermetic stream, chain, manifest, and bit-identity audit tests."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import numpy as np

from bistar_gp.m2cr.audit import (
    V117_CANONICAL_SHA256,
    band_masses_sum_identity,
    validate_ledger,
    verify_chain,
    verify_environment_freeze,
    verify_ledger_against_evidence,
)
from bistar_gp.m2cr.environment_freeze import (
    build_child_env_mapping,
    build_environment_freeze_manifest,
    build_importable_artifact_manifest,
    build_preboundary_attestation_set,
)
from bistar_gp.m2cr.serialization import (
    atomic_write_canonical_json,
    canonical_dumps,
    sha256_file,
)


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "docs/m2c_freeze/m2c_authorization_ledger.jsonl"
AUTH = "m2cr-auth-20260716-01"
LAUNCH = "m2cr-launch-20260716-01"
LAUNCH_2 = "m2cr-launch-20260716-02"
RUN_ID = "run_20260716"
DATE = "2026-07-16"
SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64
SHA_D = "d" * 64


def _commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _valid_events():
    commit = _commit()
    return [
        {
            "schema_version": 1,
            "event": "authorization_granted",
            "event_id": "m2cr-ev-000002",
            "authorization_id": AUTH,
            "date": DATE,
            "scope": {"milestone": "R4", "record_kind": "diagnostic", "one_shot": True},
            "frozen_chain": {
                "v117_canonical_sha256": V117_CANONICAL_SHA256,
                "infrastructure_manifest_sha256": SHA_A,
                "protocol_manifest_sha256": SHA_B,
                "environment_freeze_manifest_sha256": SHA_C,
                "execution_commit": commit,
            },
        },
        {
            "schema_version": 1,
            "event": "launch_attempt_started",
            "event_id": "m2cr-ev-000003",
            "authorization_id": AUTH,
            "launch_attempt_id": LAUNCH,
            "date": DATE,
        },
        {
            "schema_version": 1,
            "event": "payload_started",
            "event_id": "m2cr-ev-000004",
            "authorization_id": AUTH,
            "launch_attempt_id": LAUNCH,
            "date": DATE,
            "payload_started_sha256": SHA_D,
            "bound_to": {
                "authorization_id": AUTH,
                "launch_attempt_id": LAUNCH,
                "execution_commit": commit,
                "environment_freeze_manifest_sha256": SHA_C,
            },
        },
        {
            "schema_version": 1,
            "event": "terminal_outcome",
            "event_id": "m2cr-ev-000005",
            "authorization_id": AUTH,
            "launch_attempt_id": LAUNCH,
            "date": DATE,
            "record_kind": "diagnostic",
            "status": "COMPLETED",
            "terminal_record_sha256": SHA_A,
            "raw_manifest_sha256": SHA_B,
        },
        {
            "schema_version": 1,
            "event": "authorization_consumed",
            "event_id": "m2cr-ev-000006",
            "authorization_id": AUTH,
            "launch_attempt_id": LAUNCH,
            "date": DATE,
            "derived_from": {
                "event": "payload_started",
                "event_id": "m2cr-ev-000004",
                "payload_started_sha256": SHA_D,
            },
        },
    ]


def _jsonl(events) -> str:
    return "".join(canonical_dumps(event) + "\n" for event in events)


def _assert_reason(report, fragment: str):
    assert not report["ok"]
    assert any(fragment in error for error in report["errors"]), report["errors"]


def test_committed_historical_ledger_passes_stream_audit():
    report = validate_ledger(LEDGER.read_text(encoding="utf-8"))
    assert report["ok"], report["errors"]


def test_valid_prospective_consumption_sequence_passes():
    report = validate_ledger(_jsonl(_valid_events()))
    assert report["ok"], report["errors"]


def test_payload_started_without_terminal_outcome_fails_closed():
    events = _valid_events()
    del events[3]
    _assert_reason(validate_ledger(_jsonl(events)), "no terminal_outcome")


def test_terminal_kind_must_match_grant_scope():
    events = _valid_events()
    events[3]["record_kind"] = "result"
    _assert_reason(validate_ledger(_jsonl(events)), "does not match grant scope")


def test_consumed_without_payload_started_fails():
    events = _valid_events()[:2]
    consumed = _valid_events()[-1]
    consumed["event_id"] = "m2cr-ev-000004"
    consumed["derived_from"]["event_id"] = "m2cr-ev-000003"
    events.append(consumed)
    _assert_reason(validate_ledger(_jsonl(events)), "payload_started")


def test_consumed_deriving_from_historical_record_fails():
    historical = json.loads(LEDGER.read_text(encoding="utf-8"))
    consumed = {
        "schema_version": 1,
        "event": "authorization_consumed",
        "event_id": "m2cr-ev-000002",
        "authorization_id": historical["authorization_id"],
        "launch_attempt_id": "m2cr-launch-20260714-01",
        "date": "2026-07-14",
        "derived_from": {
            "event": "payload_started",
            "event_id": historical["event_id"],
            "payload_started_sha256": SHA_A,
        },
    }
    report = validate_ledger(_jsonl([historical, consumed]))
    _assert_reason(report, "excluded from prospective consumption derivation")


def test_pre_payload_terminal_outcome_after_payload_started_fails():
    events = _valid_events()[:3]
    events.append(
        {
            "schema_version": 1,
            "event": "pre_payload_terminal_outcome",
            "event_id": "m2cr-ev-000005",
            "authorization_id": AUTH,
            "launch_attempt_id": LAUNCH,
            "date": DATE,
            "status": "INFRA_FAILURE",
            "terminal_record_sha256": SHA_A,
            "consumes": False,
        }
    )
    _assert_reason(validate_ledger(_jsonl(events)), "after payload_started")


def test_duplicate_event_id_fails():
    events = _valid_events()
    events[1]["event_id"] = events[0]["event_id"]
    _assert_reason(validate_ledger(_jsonl(events)), "duplicate event_id")


def test_nonmonotone_event_id_fails():
    events = _valid_events()
    events[0]["event_id"] = "m2cr-ev-000003"
    events[1]["event_id"] = "m2cr-ev-000002"
    _assert_reason(validate_ledger(_jsonl(events)), "non-monotone event_id")


def test_launch_attempt_citing_unknown_grant_fails():
    launch = _valid_events()[1]
    _assert_reason(validate_ledger(_jsonl([launch])), "unknown or non-grant")


def test_correction_targeting_missing_event_fails():
    correction = {
        "schema_version": 1,
        "event": "superseding_correction",
        "event_id": "m2cr-ev-000002",
        "date": DATE,
        "supersedes_event_id": "m2cr-ev-000001",
        "reason": "test correction",
        "correction": "replacement text",
    }
    _assert_reason(validate_ledger(_jsonl([correction])), "targets missing")


def test_terminal_outcome_for_unknown_attempt_fails():
    terminal = _valid_events()[3]
    terminal["event_id"] = "m2cr-ev-000002"
    _assert_reason(validate_ledger(_jsonl([terminal])), "unknown launch attempt")


def _pre_payload_outcome(
    event_id: str, launch_id: str, digest: str = SHA_A
) -> dict:
    return {
        "schema_version": 1,
        "event": "pre_payload_terminal_outcome",
        "event_id": event_id,
        "authorization_id": AUTH,
        "launch_attempt_id": launch_id,
        "date": DATE,
        "status": "INFRA_FAILURE",
        "terminal_record_sha256": digest,
        "consumes": False,
    }


def test_one_shot_relaunch_after_consumption_fails():
    events = _valid_events()
    events.append(
        {
            "schema_version": 1,
            "event": "launch_attempt_started",
            "event_id": "m2cr-ev-000007",
            "authorization_id": AUTH,
            "launch_attempt_id": LAUNCH_2,
            "date": DATE,
        }
    )
    events.append(_pre_payload_outcome("m2cr-ev-000008", LAUNCH_2))
    _assert_reason(
        validate_ledger(_jsonl(events)),
        "after one-shot authorization",
    )


def test_non_one_shot_relaunch_after_consumption_is_legal_when_closed():
    events = _valid_events()
    events[0]["scope"]["one_shot"] = False
    events.append(
        {
            "schema_version": 1,
            "event": "launch_attempt_started",
            "event_id": "m2cr-ev-000007",
            "authorization_id": AUTH,
            "launch_attempt_id": LAUNCH_2,
            "date": DATE,
        }
    )
    events.append(_pre_payload_outcome("m2cr-ev-000008", LAUNCH_2))
    report = validate_ledger(_jsonl(events))
    assert report["ok"], report["errors"]


def test_dangling_launch_attempt_without_terminal_channel_fails():
    events = _valid_events()[:2]
    _assert_reason(validate_ledger(_jsonl(events)), "dangling")


def test_pre_payload_closure_alone_satisfies_attempt_closure():
    events = _valid_events()[:2]
    events.append(_pre_payload_outcome("m2cr-ev-000004", LAUNCH))
    report = validate_ledger(_jsonl(events))
    assert report["ok"], report["errors"]


def test_attempt_reaching_both_terminal_channels_fails():
    events = _valid_events()
    events.append(_pre_payload_outcome("m2cr-ev-000007", LAUNCH))
    _assert_reason(
        validate_ledger(_jsonl(events)),
        "duplicate terminal transition",
    )


def _frozen_chain_dict(commit: str) -> dict:
    return {
        "v117_canonical_sha256": V117_CANONICAL_SHA256,
        "infrastructure_manifest_sha256": SHA_A,
        "environment_freeze_manifest_sha256": SHA_C,
        "protocol_manifest_sha256": SHA_B,
        "execution_commit": commit,
        "authorization_id": AUTH,
    }


def _write_raw_manifest(run_dir: Path) -> str:
    """Write Layer 3 exactly as capture does: sorted '<sha256>  <relpath>'."""

    excluded = {"RAW_MANIFEST.sha256", "terminal_record.json"}
    relpaths = sorted(
        path.relative_to(run_dir).as_posix()
        for path in run_dir.rglob("*")
        if path.is_file() and path.name not in excluded
    )
    manifest = run_dir / "RAW_MANIFEST.sha256"
    manifest.write_text(
        "".join(
            f"{sha256_file(run_dir / relpath)}  {relpath}\n" for relpath in relpaths
        ),
        encoding="utf-8",
    )
    return sha256_file(manifest)


def _infra_failure_record(
    run_id: str,
    launch_id: str,
    chain: dict,
    raw_manifest_digest: str,
    payload_started: bool,
) -> dict:
    return {
        "schema_version": 1,
        "record_kind": "diagnostic",
        "status": "INFRA_FAILURE",
        "not_a_result": True,
        "run_id": run_id,
        "launch_attempt_id": launch_id,
        "chain": chain,
        "fault": {
            "fault_class": "missing_postcheck",
            "detail": "hermetic fixture",
            "reconstructed": False,
            "payload_started": payload_started,
        },
        "evidence": {
            "raw_manifest_sha256": raw_manifest_digest,
            "node_evidence_digests": [],
            "event_stream_balanced": False,
        },
    }


def _write_attempt_evidence(tmp_path: Path):
    """Materialize the capture layout: evidence_root/<run_id>/ files at root."""

    run_dir = tmp_path / RUN_ID
    (run_dir / "nodes").mkdir(parents=True)
    prelaunch = run_dir / "prelaunch.json"
    atomic_write_canonical_json(prelaunch, {"launch_attempt_id": LAUNCH})
    atomic_write_canonical_json(
        run_dir / "spawned.json", {"launch_attempt_id": LAUNCH}
    )
    attestation = run_dir / "environment.json"
    atomic_write_canonical_json(attestation, {"status": "passed"})
    (run_dir / "events.jsonl").write_text(
        '{"event":"STAGE_BEGIN"}\n', encoding="utf-8"
    )
    (run_dir / "stdout.txt").write_text("fixture stdout\n", encoding="utf-8")
    (run_dir / "stderr.txt").write_text("", encoding="utf-8")
    atomic_write_canonical_json(
        run_dir / "nodes" / "node_000000.json", {"node_index": 0}
    )

    commit = _commit()
    chain = _frozen_chain_dict(commit)
    marker = {
        "authorization_id": AUTH,
        "launch_attempt_id": LAUNCH,
        "execution_commit": commit,
        "chain": chain,
        "attestation_evidence_digests": [
            {
                "name": "environment",
                "evidence_sha256": sha256_file(attestation),
            }
        ],
        "prelaunch_sha256": sha256_file(prelaunch),
    }
    marker_path = run_dir / "payload_started.json"
    atomic_write_canonical_json(marker_path, marker)

    raw_manifest_digest = _write_raw_manifest(run_dir)
    terminal = _infra_failure_record(
        RUN_ID, LAUNCH, chain, raw_manifest_digest, payload_started=True
    )
    terminal_path = run_dir / "terminal_record.json"
    atomic_write_canonical_json(terminal_path, terminal)

    events = _valid_events()
    events[2]["payload_started_sha256"] = sha256_file(marker_path)
    events[3]["status"] = "INFRA_FAILURE"
    events[3]["terminal_record_sha256"] = sha256_file(terminal_path)
    events[3]["raw_manifest_sha256"] = raw_manifest_digest
    events[4]["derived_from"]["payload_started_sha256"] = sha256_file(marker_path)
    return _jsonl(events), run_dir


def test_ledger_evidence_verification_accepts_matching_attempt_tree(
    tmp_path: Path,
):
    jsonl, _ = _write_attempt_evidence(tmp_path)
    report = verify_ledger_against_evidence(jsonl, tmp_path)
    assert report["ok"], report["errors"]


def test_ledger_evidence_verification_rejects_tampered_terminal_record(
    tmp_path: Path,
):
    jsonl, attempt = _write_attempt_evidence(tmp_path)
    terminal = attempt / "terminal_record.json"
    terminal.write_bytes(terminal.read_bytes() + b"\n")
    _assert_reason(
        verify_ledger_against_evidence(jsonl, tmp_path),
        "terminal_record",
    )


def test_ledger_evidence_verification_rejects_tampered_marker(tmp_path: Path):
    jsonl, attempt = _write_attempt_evidence(tmp_path)
    marker = attempt / "payload_started.json"
    marker.write_bytes(marker.read_bytes() + b"\n")
    _assert_reason(
        verify_ledger_against_evidence(jsonl, tmp_path),
        "payload_started",
    )


def test_ledger_evidence_verification_rejects_dangling_digest(tmp_path: Path):
    jsonl, attempt = _write_attempt_evidence(tmp_path)
    (attempt / "RAW_MANIFEST.sha256").unlink()
    _assert_reason(
        verify_ledger_against_evidence(jsonl, tmp_path),
        "dangling digest",
    )


def test_ledger_evidence_verification_rejects_tampered_node_file(tmp_path: Path):
    jsonl, run_dir = _write_attempt_evidence(tmp_path)
    node = run_dir / "nodes" / "node_000000.json"
    node.write_bytes(node.read_bytes() + b" ")
    _assert_reason(
        verify_ledger_against_evidence(jsonl, tmp_path),
        "digest mismatch for nodes/node_000000.json",
    )


def test_ledger_evidence_verification_rejects_extra_unlisted_file(tmp_path: Path):
    jsonl, run_dir = _write_attempt_evidence(tmp_path)
    (run_dir / "rogue.json").write_text("{}", encoding="utf-8")
    _assert_reason(
        verify_ledger_against_evidence(jsonl, tmp_path),
        "unlisted evidence file rogue.json",
    )


def test_ledger_evidence_verification_rejects_missing_listed_file(tmp_path: Path):
    jsonl, run_dir = _write_attempt_evidence(tmp_path)
    (run_dir / "stdout.txt").unlink()
    _assert_reason(
        verify_ledger_against_evidence(jsonl, tmp_path),
        "listed evidence file is missing: stdout.txt",
    )


def _write_pre_payload_evidence(tmp_path: Path):
    run_id = "run_20260716_pre"
    run_dir = tmp_path / run_id
    run_dir.mkdir()
    prelaunch = run_dir / "prelaunch.json"
    atomic_write_canonical_json(prelaunch, {"launch_attempt_id": LAUNCH})
    raw_manifest_digest = _write_raw_manifest(run_dir)
    chain = _frozen_chain_dict(_commit())
    record = _infra_failure_record(
        run_id, LAUNCH, chain, raw_manifest_digest, payload_started=False
    )
    record_path = run_dir / "terminal_record.json"
    atomic_write_canonical_json(record_path, record)
    events = _valid_events()[:2]
    events.append(
        {
            "schema_version": 1,
            "event": "pre_payload_terminal_outcome",
            "event_id": "m2cr-ev-000004",
            "authorization_id": AUTH,
            "launch_attempt_id": LAUNCH,
            "date": DATE,
            "status": "INFRA_FAILURE",
            "terminal_record_sha256": sha256_file(record_path),
            "consumes": False,
        }
    )
    return _jsonl(events), run_dir


def test_pre_payload_terminal_evidence_is_authenticated(tmp_path: Path):
    jsonl, _ = _write_pre_payload_evidence(tmp_path)
    report = verify_ledger_against_evidence(jsonl, tmp_path)
    assert report["ok"], report["errors"]


def test_pre_payload_terminal_evidence_rejects_tampered_record(tmp_path: Path):
    jsonl, run_dir = _write_pre_payload_evidence(tmp_path)
    record_path = run_dir / "terminal_record.json"
    record_path.write_bytes(record_path.read_bytes() + b"\n")
    _assert_reason(
        verify_ledger_against_evidence(jsonl, tmp_path),
        "pre_payload_terminal_record",
    )


def _diagnostic_chain():
    return _frozen_chain_dict(_commit())


def _chain_expectations():
    return {
        "infrastructure_manifest_sha256": SHA_A,
        "environment_freeze_manifest_sha256": SHA_C,
        "protocol_manifest_sha256": SHA_B,
    }


def _grant_ledger() -> str:
    """A hermetic ledger holding only the prospective grant."""

    return _jsonl(_valid_events()[:1])


def test_verify_chain_passes_with_protocol_manifest_expectation():
    report = verify_chain(
        _diagnostic_chain(),
        _chain_expectations(),
        "diagnostic",
        ledger_jsonl=_grant_ledger(),
    )
    assert report["ok"], report["errors"]
    assert report["checks"]["protocol_manifest_sha256"]["status"] == "passed"
    assert report["checks"]["grant_execution_commit"]["status"] == "passed"


def test_verify_chain_fails_member_without_expectation_or_declaration():
    expectations = _chain_expectations()
    del expectations["protocol_manifest_sha256"]
    report = verify_chain(
        _diagnostic_chain(),
        expectations,
        "diagnostic",
        ledger_jsonl=_grant_ledger(),
    )
    _assert_reason(
        report, "unverifiable: no committed artifact expectation supplied"
    )
    assert report["checks"]["protocol_manifest_sha256"]["status"] == "failed"


def test_verify_chain_rejects_wrong_v117_constant():
    chain = _diagnostic_chain()
    chain["v117_canonical_sha256"] = "0" * 64
    _assert_reason(
        verify_chain(
            chain, _chain_expectations(), "diagnostic", ledger_jsonl=_grant_ledger()
        ),
        "v117_canonical",
    )


def test_verify_chain_rejects_tampered_infrastructure_digest():
    chain = _diagnostic_chain()
    chain["infrastructure_manifest_sha256"] = SHA_D
    _assert_reason(
        verify_chain(
            chain, _chain_expectations(), "diagnostic", ledger_jsonl=_grant_ledger()
        ),
        "infrastructure_manifest_sha256",
    )


def test_verify_chain_rejects_unknown_authorization():
    chain = _diagnostic_chain()
    chain["authorization_id"] = "m2cr-auth-20990101-01"
    _assert_reason(
        verify_chain(
            chain, _chain_expectations(), "diagnostic", ledger_jsonl=_grant_ledger()
        ),
        "not a prospective grant",
    )


def test_verify_chain_rejects_d45_historical_authorization():
    """Fix A6: the committed D45 historical record never satisfies a chain."""

    chain = _diagnostic_chain()
    chain["authorization_id"] = "m2cr-auth-20260714-01"
    report = verify_chain(chain, _chain_expectations(), "diagnostic")
    _assert_reason(report, "historical_authorization_record")
    assert report["checks"]["authorization_id"]["status"] == "failed"


def test_verify_chain_rejects_grant_commit_mismatch():
    events = _valid_events()[:1]
    events[0]["frozen_chain"]["execution_commit"] = "b" * 40
    _assert_reason(
        verify_chain(
            _diagnostic_chain(),
            _chain_expectations(),
            "diagnostic",
            ledger_jsonl=_jsonl(events),
        ),
        "frozen by the grant",
    )


def test_verify_chain_require_unconsumed_rejects_consumed_grant():
    consumed_ledger = _jsonl(_valid_events())
    _assert_reason(
        verify_chain(
            _diagnostic_chain(),
            _chain_expectations(),
            "diagnostic",
            require_unconsumed=True,
            ledger_jsonl=consumed_ledger,
        ),
        "already consumed",
    )
    report = verify_chain(
        _diagnostic_chain(),
        _chain_expectations(),
        "diagnostic",
        require_unconsumed=True,
        ledger_jsonl=_grant_ledger(),
    )
    assert report["ok"], report["errors"]
    assert report["checks"]["authorization_unconsumed"]["status"] == "passed"


def test_result_chain_missing_result_only_members_fails():
    _assert_reason(
        verify_chain(
            _diagnostic_chain(),
            _chain_expectations(),
            "result",
            ledger_jsonl=_grant_ledger(),
        ),
        "diagnostic_record_sha256",
    )


def test_chain_rejects_extra_member_for_explicit_kind():
    chain = _diagnostic_chain()
    chain["unexpected"] = SHA_D
    _assert_reason(
        verify_chain(
            chain, _chain_expectations(), "diagnostic", ledger_jsonl=_grant_ledger()
        ),
        "unexpected effective-chain member",
    )


def test_expected_absent_cannot_apply_to_infrastructure_members():
    expectations = {
        "environment_freeze_manifest_sha256": SHA_C,
        "expected_absent": {
            "infrastructure_manifest_sha256",
        },
    }
    report = verify_chain(
        _diagnostic_chain(),
        expectations,
        "diagnostic",
        ledger_jsonl=_grant_ledger(),
    )
    _assert_reason(report, "not the R4/R5-produced chain members")
    assert report["checks"]["infrastructure_manifest_sha256"]["status"] == "failed"
    assert "unverifiable" in report["checks"]["infrastructure_manifest_sha256"][
        "reason"
    ]


def test_protocol_manifest_cannot_be_declared_absent_after_r3():
    expectations = {
        **_chain_expectations(),
        "expected_absent": {"protocol_manifest_sha256"},
    }
    report = verify_chain(
        _diagnostic_chain(),
        expectations,
        "diagnostic",
        ledger_jsonl=_grant_ledger(),
    )
    _assert_reason(
        report, "expected_absent contains members that are not the R4/R5-produced"
    )


def test_result_chain_may_declare_only_r4_r5_members_absent():
    chain = {
        **_diagnostic_chain(),
        "diagnostic_record_sha256": SHA_D,
        "amendment_manifest": SHA_A,
    }
    grant = _valid_events()[0]
    grant["scope"]["record_kind"] = "result"
    grant["frozen_chain"]["diagnostic_record_sha256"] = SHA_D
    grant["frozen_chain"]["amendment_manifest"] = SHA_A
    expectations = {
        **_chain_expectations(),
        "expected_absent": {
            "diagnostic_record_sha256",
            "amendment_manifest",
        },
    }
    report = verify_chain(
        chain,
        expectations,
        "result",
        ledger_jsonl=_jsonl([grant]),
    )
    assert report["ok"], report["errors"]
    assert report["checks"]["diagnostic_record_sha256"]["status"] == (
        "expected_absent"
    )
    assert report["checks"]["amendment_manifest"]["status"] == "expected_absent"


def _write_file(path: Path, data: bytes = b"x") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def _valid_freeze_artifacts(base: Path) -> dict[str, Path]:
    """Build the four v5 freeze artifacts with semantically valid content."""

    artifact_dir = base / "freeze"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    env_path = artifact_dir / "child_env_mapping.json"
    atomic_write_canonical_json(env_path, build_child_env_mapping())
    paths["child_env_mapping"] = env_path

    roots = []
    for root_id in ("worktree", "stdlib", "lib-dynload", "site-packages"):
        root_dir = artifact_dir / f"root-{root_id}"
        root_dir.mkdir(exist_ok=True)
        (root_dir / "mod.py").write_text(f"# {root_id}\n", encoding="utf-8")
        roots.append((root_id, root_dir))
    manifest_path = artifact_dir / "importable_artifact_manifest.jsonl"
    build_importable_artifact_manifest(roots, manifest_path)
    paths["importable_artifact_manifest"] = manifest_path

    pin_path = artifact_dir / "interpreter_pin.json"
    atomic_write_canonical_json(
        pin_path,
        {
            "path": "/fake/bin/python3.13",
            "realpath": "/fake/real/bin/python3.13",
            "sha256": SHA_A,
            "version": {"version_string": "3.13.11 hermetic fixture"},
        },
    )
    paths["interpreter_pin"] = pin_path

    interpreter = _write_file(artifact_dir / "python", b"interpreter")
    dyld = _write_file(artifact_dir / "dyld", b"dyld")
    cache_dir = artifact_dir / "caches"
    _write_file(cache_dir / "dyld_shared_cache_arm64e", b"main")
    _write_file(cache_dir / "dyld_shared_cache_arm64e.1", b"one")
    closure = _write_file(artifact_dir / "bootstrap.py", b"bootstrap")
    # A COMPLETE closure carries stdlib-origin entries (external audit F1); a
    # fake lib/python3.* path stands in for the ~73 real stdlib modules.
    stdlib_closure = _write_file(
        artifact_dir / "lib" / "python3.13" / "json" / "__init__.py",
        b"stdlib",
    )
    attestation_path = artifact_dir / "preboundary_attestation_set.json"
    atomic_write_canonical_json(
        attestation_path,
        build_preboundary_attestation_set(
            interpreter,
            dyld_path=dyld,
            dyld_cache_dir=cache_dir,
            bootstrap_closure_paths=[closure, stdlib_closure],
            declared_subcache_count=1,
        ),
    )
    paths["preboundary_attestation_set"] = attestation_path
    return paths


def _handwritten_freeze_manifest(paths: dict[str, Path]) -> dict:
    """Pin artifacts directly (bypasses the builder's fixture guard)."""

    return {
        "kind": "m2cr_environment_freeze_manifest",
        "schema_version": 1,
        "artifacts": {
            name: {"path": os.fspath(path.resolve()), "sha256": sha256_file(path)}
            for name, path in paths.items()
        },
    }


def _freeze_report(tmp_path: Path, paths: dict[str, Path]) -> dict:
    manifest_path = tmp_path / "freeze.json"
    atomic_write_canonical_json(manifest_path, _handwritten_freeze_manifest(paths))
    return verify_environment_freeze(manifest_path)


def test_environment_freeze_verifier_rehashes_every_pin(tmp_path: Path):
    paths = _valid_freeze_artifacts(tmp_path)
    manifest_path = tmp_path / "freeze.json"
    atomic_write_canonical_json(
        manifest_path, build_environment_freeze_manifest(paths)
    )
    report = verify_environment_freeze(manifest_path)
    assert report["ok"], report["errors"]
    assert all(
        check["status"] == "passed" for check in report["checks"]
    ), report["checks"]
    paths["interpreter_pin"].write_text("changed", encoding="utf-8")
    _assert_reason(verify_environment_freeze(manifest_path), "sha256 mismatch")


def test_freeze_semantics_reject_wrong_child_env_pairs(tmp_path: Path):
    paths = _valid_freeze_artifacts(tmp_path)
    mapping = build_child_env_mapping()
    mapping["fixed"]["OMP_NUM_THREADS"] = "8"
    atomic_write_canonical_json(paths["child_env_mapping"], mapping)
    _assert_reason(_freeze_report(tmp_path, paths), "frozen Stage-A mapping")

    mapping = build_child_env_mapping()
    mapping["run_local_keys"] = mapping["run_local_keys"][:-1]
    atomic_write_canonical_json(paths["child_env_mapping"], mapping)
    _assert_reason(_freeze_report(tmp_path, paths), "six run-local keys")


def test_freeze_semantics_reject_incomplete_interpreter_pin(tmp_path: Path):
    paths = _valid_freeze_artifacts(tmp_path)
    atomic_write_canonical_json(
        paths["interpreter_pin"],
        {"path": "/fake/bin/python3.13", "realpath": "", "sha256": SHA_A},
    )
    report = _freeze_report(tmp_path, paths)
    _assert_reason(report, "nonempty realpath")
    _assert_reason(report, "nonempty version_string")


def test_freeze_semantics_reject_fixture_or_inconsistent_attestation_set(
    tmp_path: Path,
):
    paths = _valid_freeze_artifacts(tmp_path)
    attestation = json.loads(
        paths["preboundary_attestation_set"].read_text(encoding="utf-8")
    )
    attestation["test_fixture"] = True
    atomic_write_canonical_json(paths["preboundary_attestation_set"], attestation)
    _assert_reason(_freeze_report(tmp_path, paths), "test_fixture")

    attestation = json.loads(
        paths["preboundary_attestation_set"].read_text(encoding="utf-8")
    )
    del attestation["test_fixture"]
    attestation["dyld_shared_cache"]["declared_subcache_count"] = 2
    atomic_write_canonical_json(paths["preboundary_attestation_set"], attestation)
    _assert_reason(_freeze_report(tmp_path, paths), "declared count")

    attestation["dyld_shared_cache"]["declared_subcache_count"] = 1
    attestation["bootstrap_closure"] = []
    atomic_write_canonical_json(paths["preboundary_attestation_set"], attestation)
    _assert_reason(_freeze_report(tmp_path, paths), "bootstrap closure is empty")

    # External audit F1: a closure carrying only the bootstrap file (no
    # stdlib-origin entry) is structurally incomplete and rejected.
    attestation["bootstrap_closure"] = [
        {"path": "/somewhere/bistar_gp/m2cr/bootstrap.py", "sha256": "0" * 64}
    ]
    atomic_write_canonical_json(paths["preboundary_attestation_set"], attestation)
    _assert_reason(_freeze_report(tmp_path, paths), "no stdlib-origin entry")


def test_freeze_semantics_reject_wrong_or_missing_manifest_header(tmp_path: Path):
    paths = _valid_freeze_artifacts(tmp_path)
    wrong_roots_dir = tmp_path / "wrong-root"
    wrong_roots_dir.mkdir()
    (wrong_roots_dir / "mod.py").write_text("# wrong\n", encoding="utf-8")
    build_importable_artifact_manifest(
        [("fake", wrong_roots_dir)], paths["importable_artifact_manifest"]
    )
    _assert_reason(
        _freeze_report(tmp_path, paths),
        "not exactly",
    )

    paths["importable_artifact_manifest"].write_text(
        '{"artifact_type":"source","relpath":"a.py"}\n', encoding="utf-8"
    )
    _assert_reason(_freeze_report(tmp_path, paths), "valid v2 header")


def test_relative_freeze_pins_resolve_against_repo_root_not_cwd(tmp_path: Path):
    """Fix A9: repo-relative pins verify inside any checkout of the repo."""

    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    paths = _valid_freeze_artifacts(repo)
    manifest = build_environment_freeze_manifest(paths)
    assert all(
        not Path(pin["path"]).is_absolute()
        for pin in manifest["artifacts"].values()
    ), manifest["artifacts"]
    # The manifest itself is stored outside the repo; only repo_root (explicit
    # here, .git discovery in a real checkout) locates the pinned files.
    manifest_path = tmp_path / "outside-freeze.json"
    atomic_write_canonical_json(manifest_path, manifest)
    report = verify_environment_freeze(manifest_path, repo_root=repo)
    assert report["ok"], report["errors"]
    _assert_reason(verify_environment_freeze(manifest_path), "missing")


def test_band_mass_identity_passes_exact_left_to_right_sum():
    lo, mid, hi = 0.2, 0.3, 0.5
    payload = {
        "profile_band_masses": {
            "lo": lo,
            "mid": mid,
            "hi": hi,
            "sum": (lo + mid) + hi,
        }
    }
    assert band_masses_sum_identity(payload)


def test_band_mass_identity_fails_at_one_ulp():
    expected = (0.2 + 0.3) + 0.5
    wrong = float(np.nextafter(np.float64(expected), np.float64(np.inf)))
    assert not band_masses_sum_identity(
        {"lo": 0.2, "mid": 0.3, "hi": 0.5, "sum": wrong}
    )


def test_band_mass_identity_uses_documented_association_order():
    lo, mid, hi = 1.0e16, -1.0e16, 1.0
    left_to_right = (lo + mid) + hi
    right_associated = lo + (mid + hi)
    assert left_to_right != right_associated
    assert band_masses_sum_identity(
        {"lo": lo, "mid": mid, "hi": hi, "sum": left_to_right}
    )
    assert not band_masses_sum_identity(
        {"lo": lo, "mid": mid, "hi": hi, "sum": right_associated}
    )
    assert "left-to-right" in band_masses_sum_identity.__doc__


def test_verify_preboundary_closure_complete_rejects_incomplete_set(tmp_path: Path):
    """External audit F1: a closure missing enumerated origins is rejected;
    the full enumeration passes. Spawns the pinned interpreter import-only."""

    from bistar_gp.m2cr.audit import verify_preboundary_closure_complete
    from bistar_gp.m2cr.capture import enumerate_bootstrap_closure

    interpreter = "/opt/homebrew/Caskroom/miniconda/base/bin/python3.13"
    repo_root = Path(__file__).resolve().parents[1]
    bootstrap = repo_root / "bistar_gp/m2cr/bootstrap.py"
    enumerated = enumerate_bootstrap_closure(interpreter, bootstrap, repo_root)
    assert len(enumerated) > 10  # the real closure is dozens of modules

    def _attestation(origins):
        return {
            "kind": "m2cr_preboundary_attestation_set",
            "schema_version": 1,
            "bootstrap_closure": [
                {"path": origin, "sha256": "0" * 64} for origin in origins
            ],
        }

    full = tmp_path / "full.json"
    atomic_write_canonical_json(
        full, _attestation([entry["origin"] for entry in enumerated])
    )
    ok = verify_preboundary_closure_complete(full, interpreter, bootstrap, repo_root)
    assert ok["ok"], ok["errors"]
    assert ok["committed_count"] >= ok["enumerated_count"]

    # Only the bootstrap itself: the committed set from the current defect.
    partial = tmp_path / "partial.json"
    atomic_write_canonical_json(partial, _attestation([os.fspath(bootstrap)]))
    bad = verify_preboundary_closure_complete(
        partial, interpreter, bootstrap, repo_root
    )
    assert not bad["ok"]
    assert "omits" in bad["errors"][0]


def test_one_shot_relaunch_after_payload_started_fails():
    """External audit F6: a one-shot grant is consumed at payload_started, so
    a second launch attempt after it — even before the derived consumed line —
    fails, not only after authorization_consumed."""

    events = _valid_events()  # grant(one_shot) -> launch1 -> payload -> terminal -> consumed1
    relaunch = {
        "schema_version": 1,
        "event": "launch_attempt_started",
        "event_id": "m2cr-ev-000007",
        "authorization_id": AUTH,
        "launch_attempt_id": LAUNCH_2,
        "date": DATE,
    }
    # Insert the second launch BEFORE the derived authorization_consumed line
    # (index 4), so only the payload_started at index 2 has consumed the grant.
    events = events[:4] + [relaunch] + events[4:]
    # Fix the monotone event-id ordering after insertion.
    for i, ev in enumerate(events, start=2):
        ev["event_id"] = f"m2cr-ev-{i:06d}"
    events[-1]["derived_from"]["event_id"] = events[2]["event_id"]
    _assert_reason(
        validate_ledger(_jsonl(events)),
        "after one-shot authorization",
    )


def test_committed_preboundary_closure_is_complete():
    """External audit F1: the COMMITTED pre-boundary attestation set carries
    the full bootstrap closure, not just bootstrap.py."""

    from bistar_gp.m2cr.audit import verify_preboundary_closure_complete

    interpreter = "/opt/homebrew/Caskroom/miniconda/base/bin/python3.13"
    repo_root = Path(__file__).resolve().parents[1]
    if not Path(interpreter).exists():
        import pytest

        pytest.skip("Miniconda base interpreter not present")
    report = verify_preboundary_closure_complete(
        repo_root / "docs/m2c_freeze/m2cr_preboundary_attestation_set_v1.json",
        interpreter,
        repo_root / "bistar_gp/m2cr/bootstrap.py",
        repo_root,
    )
    assert report["ok"], report["errors"]
    assert report["committed_count"] > 50


def test_verify_chain_treats_payload_started_as_consumed():
    """External audit round-2 F5: verify_chain(require_unconsumed) must reject
    a grant already consumed by a payload_started, not only by the later
    authorization_consumed line."""

    from bistar_gp.m2cr.audit import _ledger_authorization_state

    commit = _commit()
    events = _valid_events()  # grant -> launch -> payload -> terminal -> consumed
    # Prefix ending at payload_started (the crash window).
    prefix = _jsonl(events[:3])
    state = _ledger_authorization_state(prefix)
    assert AUTH in state["consumed"], (
        "payload_started must consume the authorization for verify_chain"
    )
