from __future__ import annotations

import json
from pathlib import Path

import pytest

from bistar_gp.m2cr.payload_boundary import (
    BoundaryViolation,
    PayloadBoundary,
    verify_marker,
)
from bistar_gp.m2cr.serialization import (
    atomic_write_canonical_json,
    canonical_dumps,
    sha256_file,
)


AUTHORIZATION_ID = "m2cr-auth-20260716-01"
LAUNCH_ATTEMPT_ID = "m2cr-launch-20260716-01"
EXECUTION_COMMIT = "a" * 40
CHAIN = {
    "v117_canonical_sha256": "65381bc774e894dd9aaf2207cadd9cfa2f2735dafceff4bb39492086a9e522e2",
    "infrastructure_manifest_sha256": "1" * 64,
    "environment_freeze_manifest_sha256": "2" * 64,
    "protocol_manifest_sha256": "3" * 64,
    "execution_commit": EXECUTION_COMMIT,
    "authorization_id": AUTHORIZATION_ID,
}
ATTESTATIONS = ("effect", "environment", "path", "bytecode", "audit")


def _boundary(tmp_path: Path) -> PayloadBoundary:
    tmp_path.mkdir(parents=True, exist_ok=True)
    atomic_write_canonical_json(tmp_path / "prelaunch.json", {"launch": 1})
    boundary = PayloadBoundary(
        tmp_path,
        AUTHORIZATION_ID,
        LAUNCH_ATTEMPT_ID,
        EXECUTION_COMMIT,
        CHAIN,
    )
    boundary.register_required_attestations(*ATTESTATIONS)
    return boundary


def _pass_all(boundary: PayloadBoundary) -> None:
    for offset, name in enumerate(ATTESTATIONS, start=1):
        boundary.record_attestation(name, True, f"{offset:x}" * 64)


def test_guarded_scientific_spies_cannot_run_before_marker(tmp_path: Path) -> None:
    boundary = _boundary(tmp_path)
    calls: list[str] = []
    spies = [
        boundary.guard(lambda name=name: calls.append(name))
        for name in (
            "data_gen",
            "map",
            "model_eval",
            "diagnostic_eval",
            "result_payload",
        )
    ]
    for spy in spies:
        with pytest.raises(BoundaryViolation, match="not completed"):
            spy()
    assert calls == []
    assert boundary.phase_log == []


def test_mark_refuses_missing_or_failed_attestations(tmp_path: Path) -> None:
    missing = _boundary(tmp_path / "missing")
    missing.record_attestation(ATTESTATIONS[0], True, "a" * 64)
    with pytest.raises(BoundaryViolation, match="missing"):
        missing.mark()

    failed = _boundary(tmp_path / "failed")
    for name in ATTESTATIONS:
        failed.record_attestation(name, name != "path", "b" * 64)
    with pytest.raises(BoundaryViolation, match="failed"):
        failed.mark()


def test_marker_directly_precedes_first_guarded_operation(tmp_path: Path) -> None:
    boundary = _boundary(tmp_path)
    _pass_all(boundary)
    boundary.mark()
    calls: list[str] = []
    operations = [
        boundary.guard(lambda name=name: calls.append(name))
        for name in (
            "data_gen",
            "map",
            "model_eval",
            "diagnostic_eval",
            "result_payload",
        )
    ]
    operations[0]()
    assert calls == ["data_gen"]
    assert boundary.phase_log == [
        "attestations_complete",
        "marker_written",
        "payload_entered",
    ]
    for operation in operations[1:]:
        operation()
    assert calls == [
        "data_gen",
        "map",
        "model_eval",
        "diagnostic_eval",
        "result_payload",
    ]


def test_marker_is_atomic_canonical_hash_bound_and_tamper_evident(
    tmp_path: Path,
) -> None:
    boundary = _boundary(tmp_path)
    _pass_all(boundary)
    digest = boundary.mark()
    marker_path = tmp_path / "payload_started.json"
    raw = marker_path.read_bytes()
    marker = json.loads(raw)
    assert raw == canonical_dumps(marker).encode()
    assert digest == sha256_file(marker_path)
    assert not list(tmp_path.glob(".m2cr-tmp-*"))

    common = {
        "authorization_id": AUTHORIZATION_ID,
        "launch_attempt_id": LAUNCH_ATTEMPT_ID,
        "execution_commit": EXECUTION_COMMIT,
        "chain": CHAIN,
        "expected_sha256": digest,
    }
    assert verify_marker(marker_path, **common) == digest
    for field, wrong in (
        ("authorization_id", "m2cr-auth-20260716-02"),
        ("launch_attempt_id", "m2cr-launch-20260716-02"),
        ("execution_commit", "b" * 40),
        ("chain", {**CHAIN, "protocol_manifest_sha256": "f" * 64}),
    ):
        with pytest.raises(BoundaryViolation, match="mismatch"):
            verify_marker(marker_path, **{**common, field: wrong})

    marker_path.write_bytes(raw + b"\n")
    with pytest.raises(BoundaryViolation, match="canonical"):
        verify_marker(marker_path, **common)
    marker_path.write_bytes(raw[:-1] + b"!")
    with pytest.raises(BoundaryViolation, match="malformed"):
        verify_marker(marker_path, **common)
    marker_path.unlink()
    with pytest.raises(BoundaryViolation, match="missing"):
        verify_marker(marker_path, **common)


def test_marker_from_different_boundary_instance_fails_closed(tmp_path: Path) -> None:
    first = _boundary(tmp_path)
    _pass_all(first)
    first.mark()
    second = PayloadBoundary(
        tmp_path,
        "m2cr-auth-20260716-02",
        "m2cr-launch-20260716-02",
        EXECUTION_COMMIT,
        {**CHAIN, "authorization_id": "m2cr-auth-20260716-02"},
    )
    second.register_required_attestation("effect")
    second.record_attestation("effect", True, "d" * 64)
    guarded = second.guard(lambda: None)
    with pytest.raises(BoundaryViolation, match="not completed"):
        guarded()
    with pytest.raises(BoundaryViolation, match="mismatch"):
        verify_marker(
            tmp_path / "payload_started.json",
            authorization_id=second.authorization_id,
            launch_attempt_id=second.launch_attempt_id,
            execution_commit=second.execution_commit,
            chain=second.chain,
        )


def test_guard_rechecks_digest_after_canonical_byte_substitution(
    tmp_path: Path,
) -> None:
    boundary = _boundary(tmp_path)
    _pass_all(boundary)
    boundary.mark()
    marker_path = tmp_path / "payload_started.json"
    marker = json.loads(marker_path.read_text())
    marker["attestation_evidence_digests"][0]["evidence_sha256"] = "e" * 64
    atomic_write_canonical_json(marker_path, marker)
    with pytest.raises(BoundaryViolation, match="digest"):
        boundary.guard(lambda: None)()
