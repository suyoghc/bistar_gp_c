"""Hermetic stream, chain, manifest, and bit-identity audit tests."""

from __future__ import annotations

import json
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
from bistar_gp.m2cr.environment_freeze import build_environment_freeze_manifest
from bistar_gp.m2cr.serialization import (
    atomic_write_canonical_json,
    canonical_dumps,
    sha256_file,
)


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "docs/m2c_freeze/m2c_authorization_ledger.jsonl"
AUTH = "m2cr-auth-20260716-01"
LAUNCH = "m2cr-launch-20260716-01"
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


def _write_attempt_evidence(tmp_path: Path):
    attempt = tmp_path / LAUNCH
    attempt.mkdir()
    prelaunch = attempt / "prelaunch.json"
    atomic_write_canonical_json(prelaunch, {"launch_attempt_id": LAUNCH})
    attestation_dir = attempt / "attestations"
    attestation_dir.mkdir()
    attestation = attestation_dir / "environment.json"
    atomic_write_canonical_json(attestation, {"status": "passed"})
    raw_manifest = attempt / "RAW_MANIFEST.sha256"
    raw_manifest.write_text("payload_started.json  example\n", encoding="utf-8")
    raw_manifest_digest = sha256_file(raw_manifest)

    commit = _commit()
    chain = {
        "v117_canonical_sha256": V117_CANONICAL_SHA256,
        "infrastructure_manifest_sha256": SHA_A,
        "environment_freeze_manifest_sha256": SHA_C,
        "protocol_manifest_sha256": SHA_B,
        "execution_commit": commit,
        "authorization_id": AUTH,
    }
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
    marker_path = attempt / "payload_started.json"
    atomic_write_canonical_json(marker_path, marker)

    terminal = {
        "schema_version": 1,
        "record_kind": "diagnostic",
        "status": "INFRA_FAILURE",
        "not_a_result": True,
        "run_id": "run_20260716",
        "launch_attempt_id": LAUNCH,
        "chain": chain,
        "fault": {
            "fault_class": "missing_postcheck",
            "detail": "hermetic fixture",
            "reconstructed": False,
            "payload_started": True,
        },
        "evidence": {
            "raw_manifest_sha256": raw_manifest_digest,
            "node_evidence_digests": [],
            "event_stream_balanced": False,
        },
    }
    terminal_path = attempt / "terminal_record.json"
    atomic_write_canonical_json(terminal_path, terminal)

    events = _valid_events()
    events[2]["payload_started_sha256"] = sha256_file(marker_path)
    events[3]["status"] = "INFRA_FAILURE"
    events[3]["terminal_record_sha256"] = sha256_file(terminal_path)
    events[3]["raw_manifest_sha256"] = raw_manifest_digest
    events[4]["derived_from"]["payload_started_sha256"] = sha256_file(marker_path)
    return _jsonl(events), attempt


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


def _diagnostic_chain():
    return {
        "v117_canonical_sha256": V117_CANONICAL_SHA256,
        "infrastructure_manifest_sha256": SHA_A,
        "environment_freeze_manifest_sha256": SHA_B,
        "protocol_manifest_sha256": SHA_C,
        "execution_commit": _commit(),
        "authorization_id": "m2cr-auth-20260714-01",
    }


def _chain_expectations():
    return {
        "infrastructure_manifest_sha256": SHA_A,
        "environment_freeze_manifest_sha256": SHA_B,
    }


def test_verify_chain_passes_r2_members_and_reports_r3_expected_absent():
    report = verify_chain(_diagnostic_chain(), _chain_expectations(), "diagnostic")
    assert report["ok"], report["errors"]
    assert report["checks"]["protocol_manifest_sha256"]["status"] == (
        "expected_absent"
    )


def test_verify_chain_rejects_wrong_v117_constant():
    chain = _diagnostic_chain()
    chain["v117_canonical_sha256"] = "0" * 64
    _assert_reason(
        verify_chain(chain, _chain_expectations(), "diagnostic"),
        "v117_canonical",
    )


def test_verify_chain_rejects_tampered_infrastructure_digest():
    chain = _diagnostic_chain()
    chain["infrastructure_manifest_sha256"] = SHA_D
    _assert_reason(
        verify_chain(chain, _chain_expectations(), "diagnostic"),
        "infrastructure_manifest_sha256",
    )


def test_verify_chain_rejects_unknown_authorization():
    chain = _diagnostic_chain()
    chain["authorization_id"] = "m2cr-auth-20990101-01"
    _assert_reason(
        verify_chain(chain, _chain_expectations(), "diagnostic"),
        "authorization_id",
    )


def test_result_chain_missing_result_only_members_fails():
    _assert_reason(
        verify_chain(_diagnostic_chain(), _chain_expectations(), "result"),
        "diagnostic_record_sha256",
    )


def test_chain_rejects_extra_member_for_explicit_kind():
    chain = _diagnostic_chain()
    chain["unexpected"] = SHA_D
    _assert_reason(
        verify_chain(chain, _chain_expectations(), "diagnostic"),
        "unexpected effective-chain member",
    )


def test_expected_absent_cannot_apply_to_infrastructure_members():
    expectations = {
        "environment_freeze_manifest_sha256": SHA_B,
        "expected_absent": {
            "infrastructure_manifest_sha256",
            "protocol_manifest_sha256",
        },
    }
    report = verify_chain(_diagnostic_chain(), expectations, "diagnostic")
    _assert_reason(report, "non-R3/R5 chain members")
    assert report["checks"]["infrastructure_manifest_sha256"]["status"] == (
        "unverifiable"
    )


def test_environment_freeze_verifier_rehashes_every_pin(tmp_path: Path):
    names = (
        "child_env_mapping",
        "importable_artifact_manifest",
        "interpreter_pin",
        "preboundary_attestation_set",
    )
    paths = {}
    for name in names:
        path = tmp_path / f"{name}.json"
        path.write_text(name, encoding="utf-8")
        paths[name] = path
    manifest_path = tmp_path / "freeze.json"
    atomic_write_canonical_json(
        manifest_path, build_environment_freeze_manifest(paths)
    )
    assert verify_environment_freeze(manifest_path)["ok"]
    paths["interpreter_pin"].write_text("changed", encoding="utf-8")
    _assert_reason(verify_environment_freeze(manifest_path), "sha256 mismatch")


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
