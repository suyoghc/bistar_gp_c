"""Post-hoc audit checks for M2cR ledgers, chains, and manifests.

The JSON Schema contracts establish line/record shape.  This module supplies
the stream and filesystem checks those contracts intentionally cannot express:
append-only ledger transitions, cross-line consumption derivation, live hash
comparison, git-object resolution, and the result payload's exact identity.
"""

from __future__ import annotations

import json
import math
import os
import re
import struct
import subprocess
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from bistar_gp.m2cr.serialization import canonical_bytes, canonical_sha256, sha256_file

__all__ = [
    "V117_CANONICAL_SHA256",
    "validate_ledger",
    "verify_ledger_against_evidence",
    "verify_chain",
    "verify_infrastructure_manifest",
    "band_masses_sum_identity",
    "verify_environment_freeze",
]


_REPO_ROOT = Path(__file__).resolve().parents[2]
_LEDGER_SCHEMA_PATH = (
    _REPO_ROOT / "docs/m2c_freeze/m2c_authorization_ledger.schema_v1.json"
)
_LEDGER_PATH = _REPO_ROOT / "docs/m2c_freeze/m2c_authorization_ledger.jsonl"
_EXECUTION_RECORD_SCHEMA_PATH = (
    _REPO_ROOT / "docs/m2c_freeze/m2c_execution_record.schema_v1.json"
)
_V117_PATH = _REPO_ROOT / "docs/m2c_freeze/gtoy_profile_freeze_v1.17.json"
V117_CANONICAL_SHA256 = (
    "65381bc774e894dd9aaf2207cadd9cfa2f2735dafceff4bb39492086a9e522e2"
)
_EVENT_ID = re.compile(r"^m2cr-ev-(\d{6})$")
_LAUNCH_ID = re.compile(r"^m2cr-launch-[0-9]{8}-[0-9]{2}$")
_EVIDENCE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_R2_CODE_RELPATHS = {
    "bistar_gp/m2cr/__init__.py",
    "bistar_gp/m2cr/serialization.py",
    "bistar_gp/m2cr/coordinates.py",
    "bistar_gp/m2cr/events.py",
    "bistar_gp/m2cr/gates_v2.py",
    "bistar_gp/m2cr/records.py",
    "bistar_gp/m2cr/capture.py",
    "bistar_gp/m2cr/bootstrap.py",
    "bistar_gp/m2cr/payload_boundary.py",
    "bistar_gp/m2cr/environment_freeze.py",
    "bistar_gp/m2cr/audit.py",
    "bistar_gp/m2cr/measure.py",
}
_INFRASTRUCTURE_ARTIFACT_KEYS = {
    "child_env_mapping",
    "importable_artifact_manifest",
    "interpreter_pin",
    "preboundary_attestation_set",
    "environment_freeze_manifest",
    "dependency_lock",
}
_INFRASTRUCTURE_R1_SCHEMA_KEYS = {
    "execution_record",
    "authorization_ledger",
}
_R3_DIAGNOSTIC_SCHEMA_BASENAME = "m2c_diagnostic_record.schema_v1.json"
_PAYLOAD_MARKER_FIELDS = {
    "authorization_id",
    "launch_attempt_id",
    "execution_commit",
    "chain",
    "attestation_evidence_digests",
    "prelaunch_sha256",
}


def _schema_error(error: Any) -> str:
    location = "/".join(str(part) for part in error.absolute_path)
    return f"schema violation at {location or '<root>'}: {error.message}"


def validate_ledger(jsonl_text: str) -> dict[str, Any]:
    """Validate ledger lines and every prospective cross-line transition.

    In particular, an ``authorization_consumed`` line is accepted only when
    ``derived_from`` resolves to an earlier, genuine ``payload_started`` line
    whose authorization id, launch-attempt id, and marker digest all match.
    Historical records are never eligible derivation sources.
    """

    schema = json.loads(_LEDGER_SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    errors: list[str] = []
    parsed: list[tuple[int, dict[str, Any]]] = []
    lines = jsonl_text.splitlines()
    for line_number, raw in enumerate(lines, start=1):
        if not raw.strip():
            errors.append(f"line {line_number}: blank ledger line")
            continue
        try:
            event = json.loads(raw)
        except json.JSONDecodeError as exc:
            errors.append(f"line {line_number}: invalid JSON: {exc.msg}")
            continue
        if not isinstance(event, dict):
            errors.append(f"line {line_number}: ledger event is not an object")
            continue
        for schema_failure in sorted(
            validator.iter_errors(event),
            key=lambda item: tuple(str(part) for part in item.absolute_path),
        ):
            errors.append(f"line {line_number}: {_schema_error(schema_failure)}")
        parsed.append((line_number, event))

    seen_event_ids: set[str] = set()
    prior_event_number = -1
    grants: dict[str, dict[str, Any]] = {}
    historical: dict[str, dict[str, Any]] = {}
    attempts: dict[str, dict[str, Any]] = {}
    events_by_id: dict[str, dict[str, Any]] = {}
    consumed_sources: set[str] = set()
    payload_event_ids: set[str] = set()

    for line_number, event in parsed:
        event_id = event.get("event_id")
        if isinstance(event_id, str):
            if event_id in seen_event_ids:
                errors.append(f"line {line_number}: duplicate event_id {event_id}")
            match = _EVENT_ID.fullmatch(event_id)
            if match:
                number = int(match.group(1))
                if number <= prior_event_number:
                    errors.append(
                        f"line {line_number}: non-monotone event_id {event_id}; "
                        "event ids must be strictly increasing"
                    )
                prior_event_number = max(prior_event_number, number)
            seen_event_ids.add(event_id)

        kind = event.get("event")
        authorization_id = event.get("authorization_id")
        launch_id = event.get("launch_attempt_id")

        if kind == "historical_authorization_record":
            if authorization_id in historical or authorization_id in grants:
                errors.append(
                    f"line {line_number}: duplicate authorization id {authorization_id}"
                )
            elif isinstance(authorization_id, str):
                historical[authorization_id] = event

        elif kind == "authorization_granted":
            if authorization_id in grants or authorization_id in historical:
                errors.append(
                    f"line {line_number}: duplicate authorization id {authorization_id}"
                )
            elif isinstance(authorization_id, str):
                grants[authorization_id] = event

        elif kind == "launch_attempt_started":
            if authorization_id not in grants:
                errors.append(
                    f"line {line_number}: launch attempt cites unknown or non-grant "
                    f"authorization {authorization_id}"
                )
            if launch_id in attempts:
                errors.append(
                    f"line {line_number}: duplicate launch_attempt_id {launch_id}"
                )
            elif isinstance(launch_id, str):
                attempts[launch_id] = {
                    "authorization_id": authorization_id,
                    "payload_event": None,
                    "pre_payload_terminal": None,
                    "terminal": None,
                }

        elif kind == "payload_started":
            state = attempts.get(launch_id)
            if state is None:
                errors.append(
                    f"line {line_number}: payload_started for unknown launch attempt "
                    f"{launch_id}"
                )
            else:
                if state["authorization_id"] != authorization_id:
                    errors.append(
                        f"line {line_number}: payload_started authorization does not "
                        f"match launch attempt {launch_id}"
                    )
                if state["pre_payload_terminal"] is not None:
                    errors.append(
                        f"line {line_number}: payload_started occurs after a "
                        f"pre-payload terminal outcome for {launch_id}"
                    )
                if state["payload_event"] is not None:
                    errors.append(
                        f"line {line_number}: duplicate payload_started for {launch_id}"
                    )
                state["payload_event"] = event
                bound = event.get("bound_to")
                if isinstance(bound, dict):
                    if bound.get("authorization_id") != authorization_id:
                        errors.append(
                            f"line {line_number}: bound_to authorization_id mismatch"
                        )
                    if bound.get("launch_attempt_id") != launch_id:
                        errors.append(
                            f"line {line_number}: bound_to launch_attempt_id mismatch"
                        )
                    grant = grants.get(authorization_id)
                    frozen_chain = grant.get("frozen_chain", {}) if grant else {}
                    for key in (
                        "execution_commit",
                        "environment_freeze_manifest_sha256",
                    ):
                        if frozen_chain and bound.get(key) != frozen_chain.get(key):
                            errors.append(
                                f"line {line_number}: bound_to {key} does not match grant"
                            )
                if isinstance(event_id, str):
                    payload_event_ids.add(event_id)

        elif kind == "pre_payload_terminal_outcome":
            state = attempts.get(launch_id)
            if state is None:
                errors.append(
                    f"line {line_number}: pre_payload_terminal_outcome for unknown "
                    f"launch attempt {launch_id}"
                )
            else:
                if state["authorization_id"] != authorization_id:
                    errors.append(
                        f"line {line_number}: pre-payload outcome authorization mismatch"
                    )
                if state["payload_event"] is not None:
                    errors.append(
                        f"line {line_number}: pre_payload_terminal_outcome after "
                        f"payload_started for {launch_id}"
                    )
                if state["pre_payload_terminal"] is not None or state["terminal"] is not None:
                    errors.append(
                        f"line {line_number}: duplicate terminal transition for {launch_id}"
                    )
                state["pre_payload_terminal"] = event

        elif kind == "terminal_outcome":
            state = attempts.get(launch_id)
            if state is None:
                errors.append(
                    f"line {line_number}: terminal_outcome for unknown launch attempt "
                    f"{launch_id}"
                )
            else:
                if state["authorization_id"] != authorization_id:
                    errors.append(
                        f"line {line_number}: terminal_outcome authorization mismatch"
                    )
                if state["payload_event"] is None:
                    errors.append(
                        f"line {line_number}: terminal_outcome before payload_started "
                        f"for {launch_id}"
                    )
                if state["pre_payload_terminal"] is not None or state["terminal"] is not None:
                    errors.append(
                        f"line {line_number}: duplicate terminal transition for {launch_id}"
                    )
                state["terminal"] = event
                grant = grants.get(authorization_id)
                scope = grant.get("scope") if isinstance(grant, dict) else None
                granted_kind = (
                    scope.get("record_kind") if isinstance(scope, dict) else None
                )
                terminal_kind = event.get("record_kind")
                if (
                    isinstance(granted_kind, str)
                    and isinstance(terminal_kind, str)
                    and terminal_kind != granted_kind
                ):
                    errors.append(
                        f"line {line_number}: terminal_outcome record_kind "
                        f"{terminal_kind} does not match grant scope {granted_kind}"
                    )

        elif kind == "authorization_consumed":
            derived = event.get("derived_from")
            source_id = derived.get("event_id") if isinstance(derived, dict) else None
            source = events_by_id.get(source_id) if isinstance(source_id, str) else None
            if source is None:
                errors.append(
                    f"line {line_number}: authorization_consumed derived_from does not "
                    f"resolve to an existing earlier event {source_id}"
                )
            elif source.get("event") == "historical_authorization_record":
                errors.append(
                    f"line {line_number}: historical_authorization_record is excluded "
                    "from prospective consumption derivation"
                )
            elif source.get("event") != "payload_started":
                errors.append(
                    f"line {line_number}: authorization_consumed must derive from a "
                    "payload_started event"
                )
            else:
                if source.get("authorization_id") != authorization_id:
                    errors.append(
                        f"line {line_number}: consumed authorization_id does not match "
                        "payload_started"
                    )
                if source.get("launch_attempt_id") != launch_id:
                    errors.append(
                        f"line {line_number}: consumed launch_attempt_id does not match "
                        "payload_started"
                    )
                if isinstance(derived, dict) and derived.get(
                    "payload_started_sha256"
                ) != source.get("payload_started_sha256"):
                    errors.append(
                        f"line {line_number}: consumed marker digest does not match "
                        "payload_started"
                    )
                if source_id in consumed_sources:
                    errors.append(
                        f"line {line_number}: payload_started {source_id} consumed twice"
                    )
                elif isinstance(source_id, str):
                    consumed_sources.add(source_id)

        elif kind == "superseding_correction":
            target = event.get("supersedes_event_id")
            if target not in events_by_id:
                errors.append(
                    f"line {line_number}: correction targets missing or later event {target}"
                )

        if isinstance(event_id, str) and event_id not in events_by_id:
            events_by_id[event_id] = event

    for event_id in sorted(payload_event_ids - consumed_sources):
        errors.append(
            f"payload_started {event_id} has no derived authorization_consumed event"
        )
    for launch_id, state in sorted(attempts.items()):
        if state["payload_event"] is not None and state["terminal"] is None:
            errors.append(
                f"launch attempt {launch_id} has payload_started but no terminal_outcome"
            )
    return {
        "ok": not errors,
        "errors": errors,
        "line_count": len(lines),
        "event_count": len(parsed),
    }


def _attempt_dir(evidence_root: Path, launch_id: Any) -> Path:
    if not isinstance(launch_id, str) or _LAUNCH_ID.fullmatch(launch_id) is None:
        raise ValueError(f"invalid launch-attempt evidence key: {launch_id!r}")
    root = evidence_root.resolve()
    attempt = (root / launch_id).resolve()
    try:
        attempt.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"launch-attempt evidence escapes root: {launch_id}") from exc
    return attempt


def _read_hashed_file(
    path: Path,
    expected: Any,
    label: str,
    checks: list[dict[str, Any]],
    errors: list[str],
) -> bytes | None:
    if not path.is_file():
        errors.append(f"{label}: dangling digest; evidence file is missing: {path}")
        checks.append({"label": label, "path": os.fspath(path), "status": "failed"})
        return None
    actual = sha256_file(path)
    status = "passed" if actual == expected else "failed"
    checks.append(
        {
            "label": label,
            "path": os.fspath(path),
            "status": status,
            "expected": expected,
            "actual": actual,
        }
    )
    if status == "failed":
        errors.append(f"{label}: sha256 mismatch for {path}")
        return None
    return path.read_bytes()


def verify_ledger_against_evidence(
    jsonl_text: str,
    evidence_root: str | os.PathLike[str],
) -> dict[str, Any]:
    """Verify prospective ledger digests against an attempt-keyed evidence tree.

    The hermetic layout is ``<evidence_root>/<launch_attempt_id>/`` with
    ``payload_started.json``, ``prelaunch.json``, ``terminal_record.json``, and
    ``RAW_MANIFEST.sha256``.  Marker attestation entries named ``NAME`` resolve
    to ``attestations/NAME.json``.  Terminal records are validated against the
    committed execution-record schema and bound back to their ledger event.
    """

    stream_report = validate_ledger(jsonl_text)
    errors = list(stream_report["errors"])
    checks: list[dict[str, Any]] = []
    root = Path(evidence_root)
    try:
        record_schema = json.loads(
            _EXECUTION_RECORD_SCHEMA_PATH.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"cannot load execution-record schema: {exc}")
        return {"ok": False, "errors": errors, "checks": checks}
    record_validator = Draft202012Validator(record_schema)
    events: list[dict[str, Any]] = []
    for raw in jsonl_text.splitlines():
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            events.append(parsed)
    grants = {
        event.get("authorization_id"): event
        for event in events
        if event.get("event") == "authorization_granted"
    }

    for event in events:
        kind = event.get("event")
        if kind not in {"payload_started", "terminal_outcome"}:
            continue
        launch_id = event.get("launch_attempt_id")
        try:
            attempt = _attempt_dir(root, launch_id)
        except ValueError as exc:
            errors.append(str(exc))
            continue

        if kind == "payload_started":
            marker_path = attempt / "payload_started.json"
            raw_marker = _read_hashed_file(
                marker_path,
                event.get("payload_started_sha256"),
                f"payload_started:{launch_id}",
                checks,
                errors,
            )
            if raw_marker is None:
                continue
            try:
                marker = json.loads(raw_marker)
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                errors.append(f"payload_started:{launch_id}: malformed marker: {exc}")
                continue
            try:
                marker_is_canonical = raw_marker == canonical_bytes(marker)
            except (TypeError, ValueError):
                marker_is_canonical = False
            if (
                not isinstance(marker, dict)
                or set(marker) != _PAYLOAD_MARKER_FIELDS
                or not marker_is_canonical
            ):
                errors.append(
                    f"payload_started:{launch_id}: marker shape or canonical bytes mismatch"
                )
                continue
            bound = event.get("bound_to")
            bound = bound if isinstance(bound, dict) else {}
            for field in ("authorization_id", "launch_attempt_id", "execution_commit"):
                expected = bound.get(field, event.get(field))
                if marker.get(field) != expected:
                    errors.append(
                        f"payload_started:{launch_id}: marker {field} mismatch"
                    )
            marker_chain = marker.get("chain")
            grant = grants.get(event.get("authorization_id"))
            frozen_chain = grant.get("frozen_chain") if isinstance(grant, dict) else {}
            if not isinstance(marker_chain, dict):
                errors.append(f"payload_started:{launch_id}: marker chain is malformed")
            else:
                for field, expected in (
                    frozen_chain.items() if isinstance(frozen_chain, dict) else ()
                ):
                    if marker_chain.get(field) != expected:
                        errors.append(
                            f"payload_started:{launch_id}: marker chain {field} mismatch"
                        )
                if marker_chain.get("authorization_id") != event.get("authorization_id"):
                    errors.append(
                        f"payload_started:{launch_id}: marker chain authorization_id mismatch"
                    )
                bound_freeze = bound.get("environment_freeze_manifest_sha256")
                if marker_chain.get(
                    "environment_freeze_manifest_sha256"
                ) != bound_freeze:
                    errors.append(
                        f"payload_started:{launch_id}: marker chain environment-freeze "
                        "digest mismatch"
                    )
            prelaunch_digest = marker.get("prelaunch_sha256")
            _read_hashed_file(
                attempt / "prelaunch.json",
                prelaunch_digest,
                f"prelaunch:{launch_id}",
                checks,
                errors,
            )
            attestations = marker.get("attestation_evidence_digests")
            if not isinstance(attestations, list):
                errors.append(
                    f"payload_started:{launch_id}: attestation digests are malformed"
                )
                continue
            attestation_names: list[str] = []
            for item in attestations:
                if not isinstance(item, dict) or set(item) != {
                    "name",
                    "evidence_sha256",
                }:
                    errors.append(
                        f"payload_started:{launch_id}: attestation digest is malformed"
                    )
                    continue
                name = item.get("name")
                if not isinstance(name, str) or _EVIDENCE_NAME.fullmatch(name) is None:
                    errors.append(
                        f"payload_started:{launch_id}: unsafe attestation evidence name"
                    )
                    continue
                attestation_names.append(name)
                _read_hashed_file(
                    attempt / "attestations" / f"{name}.json",
                    item.get("evidence_sha256"),
                    f"attestation:{launch_id}:{name}",
                    checks,
                    errors,
                )
            if attestation_names != sorted(attestation_names) or len(
                attestation_names
            ) != len(set(attestation_names)):
                errors.append(
                    f"payload_started:{launch_id}: attestation names are not "
                    "unique and sorted"
                )
            continue

        terminal_path = attempt / "terminal_record.json"
        raw_terminal = _read_hashed_file(
            terminal_path,
            event.get("terminal_record_sha256"),
            f"terminal_record:{launch_id}",
            checks,
            errors,
        )
        _read_hashed_file(
            attempt / "RAW_MANIFEST.sha256",
            event.get("raw_manifest_sha256"),
            f"raw_manifest:{launch_id}",
            checks,
            errors,
        )
        if raw_terminal is None:
            continue
        try:
            record = json.loads(raw_terminal)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"terminal_record:{launch_id}: malformed JSON: {exc}")
            continue
        failures = sorted(
            record_validator.iter_errors(record),
            key=lambda item: tuple(str(part) for part in item.absolute_path),
        )
        for failure in failures:
            errors.append(
                f"terminal_record:{launch_id}: {_schema_error(failure)}"
            )
        if not isinstance(record, dict):
            continue
        for field in ("launch_attempt_id", "record_kind", "status"):
            if record.get(field) != event.get(field):
                errors.append(f"terminal_record:{launch_id}: {field} mismatch")
        chain = record.get("chain")
        if not isinstance(chain, dict) or chain.get("authorization_id") != event.get(
            "authorization_id"
        ):
            errors.append(
                f"terminal_record:{launch_id}: authorization_id mismatch"
            )
        else:
            grant = grants.get(event.get("authorization_id"))
            frozen_chain = grant.get("frozen_chain") if isinstance(grant, dict) else {}
            for field, expected in (
                frozen_chain.items() if isinstance(frozen_chain, dict) else ()
            ):
                if chain.get(field) != expected:
                    errors.append(
                        f"terminal_record:{launch_id}: chain {field} mismatch"
                    )
        evidence = record.get("evidence")
        if not isinstance(evidence, dict) or evidence.get(
            "raw_manifest_sha256"
        ) != event.get("raw_manifest_sha256"):
            errors.append(
                f"terminal_record:{launch_id}: raw_manifest_sha256 mismatch"
            )

    return {
        "ok": not errors,
        "errors": errors,
        "checks": checks,
        "event_count": stream_report["event_count"],
    }


def _chain_check(
    checks: dict[str, dict[str, Any]],
    name: str,
    status: str,
    **details: Any,
) -> None:
    checks[name] = {"status": status, **details}


def _committed_authorizations() -> set[str]:
    result: set[str] = set()
    for raw in _LEDGER_PATH.read_text(encoding="utf-8").splitlines():
        event = json.loads(raw)
        if event.get("event") in {
            "authorization_granted",
            "historical_authorization_record",
        }:
            result.add(event["authorization_id"])
    return result


def verify_chain(
    record_chain: dict[str, Any],
    expectations: dict[str, Any],
    record_kind: str,
) -> dict[str, Any]:
    """Verify each effective-chain member or state why it is unavailable.

    ``record_kind`` selects the exact B18 member set; chain shape is never
    inferred from whichever optional members happen to be present.
    ``expectations`` supplies committed digests under their chain-field names.
    During R2, R3/R5-owned artifacts may receive an explicit
    ``expected_absent`` status.  Pass ``verify_execution_commit=False`` to
    skip git-object lookup.
    """

    checks: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    if record_kind not in {"diagnostic", "result"}:
        return {
            "ok": False,
            "errors": ["record_kind must be 'diagnostic' or 'result'"],
            "checks": checks,
        }
    supplied_v117 = record_chain.get("v117_canonical_sha256")
    try:
        parsed_v117 = json.loads(_V117_PATH.read_text(encoding="utf-8"))
        recomputed_v117 = canonical_sha256(parsed_v117)
    except (OSError, json.JSONDecodeError) as exc:
        recomputed_v117 = None
        errors.append(f"cannot recompute v1.17 canonical hash: {exc}")
    if (
        supplied_v117 == V117_CANONICAL_SHA256
        and recomputed_v117 == V117_CANONICAL_SHA256
    ):
        _chain_check(
            checks,
            "v117_canonical_sha256",
            "passed",
            actual=supplied_v117,
        )
    else:
        _chain_check(
            checks,
            "v117_canonical_sha256",
            "failed",
            actual=supplied_v117,
            constant=V117_CANONICAL_SHA256,
            recomputed=recomputed_v117,
        )
        errors.append("v117_canonical_sha256 does not equal const and live canonical hash")

    default_absent = {
        "protocol_manifest_sha256",
        "diagnostic_record_sha256",
        "amendment_manifest",
    }
    expected_absent = set(expectations.get("expected_absent", default_absent))
    invalid_absent = expected_absent - default_absent
    if invalid_absent:
        errors.append(
            "expected_absent contains non-R3/R5 chain members: "
            + ", ".join(sorted(invalid_absent))
        )
    expected_absent &= default_absent
    diagnostic_members = {
        "v117_canonical_sha256",
        "infrastructure_manifest_sha256",
        "environment_freeze_manifest_sha256",
        "protocol_manifest_sha256",
        "execution_commit",
        "authorization_id",
    }
    result_members = diagnostic_members | {
        "diagnostic_record_sha256",
        "amendment_manifest",
    }
    required_members = result_members if record_kind == "result" else diagnostic_members
    missing_members = sorted(required_members - set(record_chain))
    unknown_members = sorted(set(record_chain) - required_members)
    for name in missing_members:
        _chain_check(
            checks,
            name,
            "failed",
            reason="required effective-chain member is missing",
        )
        errors.append(f"required effective-chain member is missing: {name}")
    for name in unknown_members:
        _chain_check(
            checks,
            name,
            "failed",
            actual=record_chain[name],
            reason="member is outside the exact B18 enumeration",
        )
        errors.append(f"unexpected effective-chain member: {name}")
    digest_members = (
        "infrastructure_manifest_sha256",
        "environment_freeze_manifest_sha256",
        "protocol_manifest_sha256",
        "diagnostic_record_sha256",
        "amendment_manifest",
    )
    for name in digest_members:
        if name not in record_chain:
            continue
        actual = record_chain[name]
        expected = expectations.get(name)
        if expected is not None:
            if actual == expected:
                _chain_check(checks, name, "passed", actual=actual)
            else:
                _chain_check(
                    checks, name, "failed", actual=actual, expected=expected
                )
                errors.append(f"{name} does not match committed artifact digest")
        elif name == "amendment_manifest" and actual == "none":
            _chain_check(
                checks,
                name,
                "passed",
                actual=actual,
                reason="explicitly records that no amendment exists",
            )
        elif name in expected_absent:
            _chain_check(
                checks,
                name,
                "expected_absent",
                actual=actual,
                reason="R3 artifact does not exist during milestone R2",
            )
        else:
            _chain_check(
                checks,
                name,
                "unverifiable",
                actual=actual,
                reason="caller supplied no committed-artifact digest",
            )
            errors.append(f"{name} is unverifiable without a committed-artifact digest")

    commit = record_chain.get("execution_commit")
    if not isinstance(commit, str) or not _HEX40.fullmatch(commit):
        _chain_check(checks, "execution_commit", "failed", actual=commit)
        errors.append("execution_commit is not 40 lowercase hex")
    elif expectations.get("verify_execution_commit", True):
        completed = subprocess.run(
            ["git", "-C", os.fspath(_REPO_ROOT), "cat-file", "-e", f"{commit}^{{commit}}"],
            capture_output=True,
            text=True,
        )
        if completed.returncode == 0:
            _chain_check(checks, "execution_commit", "passed", actual=commit)
        else:
            _chain_check(
                checks,
                "execution_commit",
                "failed",
                actual=commit,
                reason="git cat-file could not resolve it as a commit",
            )
            errors.append("execution_commit is not resolvable in this repository")
    else:
        _chain_check(
            checks,
            "execution_commit",
            "skipped",
            actual=commit,
            reason="git resolution disabled by caller",
        )

    authorization_id = record_chain.get("authorization_id")
    if authorization_id in _committed_authorizations():
        _chain_check(
            checks, "authorization_id", "passed", actual=authorization_id
        )
    else:
        _chain_check(
            checks, "authorization_id", "failed", actual=authorization_id
        )
        errors.append("authorization_id is not a grant or historical record in the ledger")
    return {"ok": not errors, "errors": errors, "checks": checks}


def _resolve_pinned_path(stored: str, manifest_path: Path) -> Path | None:
    path = Path(stored)
    if path.is_absolute():
        return path if path.is_file() else None
    # A temp manifest can sit at the root of a copied tree; prefer its ancestry.
    for parent in (manifest_path.parent, *manifest_path.parents):
        candidate = parent / path
        if candidate.is_file():
            return candidate
    candidate = Path.cwd() / path
    return candidate if candidate.is_file() else None


def _verify_pin(
    *,
    label: str,
    stored_path: str,
    expected: Any,
    manifest_path: Path,
    checks: list[dict[str, Any]],
    errors: list[str],
) -> None:
    path = _resolve_pinned_path(stored_path, manifest_path)
    if path is None:
        checks.append(
            {"label": label, "path": stored_path, "status": "failed", "reason": "missing"}
        )
        errors.append(f"{label}: pinned file is missing: {stored_path}")
        return
    actual = sha256_file(path)
    status = "passed" if actual == expected else "failed"
    checks.append(
        {
            "label": label,
            "path": stored_path,
            "status": status,
            "expected": expected,
            "actual": actual,
        }
    )
    if status == "failed":
        errors.append(f"{label}: sha256 mismatch for {stored_path}")


def verify_infrastructure_manifest(
    manifest_path: str | os.PathLike[str],
) -> dict[str, Any]:
    """Recompute every Layer-1a pin (the standing manifest==code check)."""

    path = Path(manifest_path).resolve()
    errors: list[str] = []
    checks: list[dict[str, Any]] = []
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "errors": [f"cannot read manifest: {exc}"], "checks": []}
    if not isinstance(manifest, dict):
        return {
            "ok": False,
            "errors": ["infrastructure manifest is not an object"],
            "checks": [],
        }
    if manifest.get("kind") != "m2cr_infrastructure_manifest":
        errors.append("wrong infrastructure manifest kind")
    if manifest.get("schema_version") != 1:
        errors.append("wrong infrastructure manifest schema_version")
    expected_keys = {"kind", "schema_version", "code", "artifacts", "r1_schemas"}
    if set(manifest) != expected_keys:
        errors.append("infrastructure manifest has a non-canonical top-level key set")
    code = manifest.get("code")
    if not isinstance(code, dict):
        errors.append("infrastructure manifest code section is not an object")
        code = {}
    elif set(code) != _R2_CODE_RELPATHS:
        errors.append(
            "infrastructure manifest code section does not have the exact "
            "required 12-module key set"
        )
    for stored_path, pin in sorted(code.items()):
        if not isinstance(pin, dict) or set(pin) != {"sha256"}:
            errors.append(f"code:{stored_path}: malformed pin")
            continue
        _verify_pin(
            label=f"code:{stored_path}",
            stored_path=stored_path,
            expected=pin["sha256"],
            manifest_path=path,
            checks=checks,
            errors=errors,
        )
    category_keys = {
        "artifacts": _INFRASTRUCTURE_ARTIFACT_KEYS,
        "r1_schemas": _INFRASTRUCTURE_R1_SCHEMA_KEYS,
    }
    for category, required_keys in category_keys.items():
        pins = manifest.get(category)
        if not isinstance(pins, dict):
            errors.append(f"infrastructure manifest {category} section is not an object")
            continue
        if set(pins) != required_keys:
            errors.append(
                f"infrastructure manifest {category} section does not have its "
                "exact required key set"
            )
        for name, pin in sorted(pins.items()):
            if (
                not isinstance(pin, dict)
                or set(pin) != {"path", "sha256"}
                or not isinstance(pin.get("path"), str)
            ):
                errors.append(f"{category}:{name}: malformed pin")
                continue
            if Path(pin["path"]).name == _R3_DIAGNOSTIC_SCHEMA_BASENAME:
                errors.append(
                    f"{category}:{name}: R3 diagnostic schema cannot be pinned by Layer 1a"
                )
                continue
            resolved_pin = _resolve_pinned_path(pin["path"], path)
            if (
                resolved_pin is not None
                and resolved_pin.resolve().name == _R3_DIAGNOSTIC_SCHEMA_BASENAME
            ):
                errors.append(
                    f"{category}:{name}: R3 diagnostic schema cannot be pinned by Layer 1a"
                )
                continue
            _verify_pin(
                label=f"{category}:{name}",
                stored_path=pin["path"],
                expected=pin.get("sha256"),
                manifest_path=path,
                checks=checks,
                errors=errors,
            )
    return {"ok": not errors, "errors": errors, "checks": checks}


def band_masses_sum_identity(payload: dict[str, Any]) -> bool:
    """Check the exact float64 identity ``(lo + mid) + hi == sum``.

    Association is deliberately left-to-right: first convert all four fields
    to IEEE-754 binary64 (CPython ``float``), then evaluate
    ``(float64(lo) + float64(mid)) + float64(hi)``.  The supplied ``sum`` must
    have the identical binary64 bit pattern; this is an identity, not a
    tolerance, and it is not reassociated as ``lo + (mid + hi)``.
    """

    masses: Any = payload
    if isinstance(masses, dict) and "result_payload" in masses:
        masses = masses["result_payload"]
    if isinstance(masses, dict) and "profile_band_masses" in masses:
        masses = masses["profile_band_masses"]
    if not isinstance(masses, dict):
        return False
    if any(isinstance(masses.get(name), bool) for name in ("lo", "mid", "hi", "sum")):
        return False
    try:
        lo = float(masses["lo"])
        mid = float(masses["mid"])
        hi = float(masses["hi"])
        supplied = float(masses["sum"])
    except (KeyError, TypeError, ValueError, OverflowError):
        return False
    if not all(math.isfinite(value) for value in (lo, mid, hi, supplied)):
        return False
    computed = (lo + mid) + hi
    return struct.pack(">d", computed) == struct.pack(">d", supplied)


def verify_environment_freeze(
    freeze_manifest_path: str | os.PathLike[str],
) -> dict[str, Any]:
    """Rehash all four artifacts pinned by the static v5 freeze manifest."""

    path = Path(freeze_manifest_path).resolve()
    errors: list[str] = []
    checks: list[dict[str, Any]] = []
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "errors": [f"cannot read manifest: {exc}"], "checks": []}
    if manifest.get("kind") != "m2cr_environment_freeze_manifest":
        errors.append("wrong environment-freeze manifest kind")
    if manifest.get("schema_version") != 1:
        errors.append("wrong environment-freeze schema_version")
    if set(manifest) != {"kind", "schema_version", "artifacts"}:
        errors.append("environment-freeze manifest has a non-canonical top-level key set")
    artifacts = manifest.get("artifacts")
    required = {
        "child_env_mapping",
        "importable_artifact_manifest",
        "interpreter_pin",
        "preboundary_attestation_set",
    }
    if not isinstance(artifacts, dict) or set(artifacts) != required:
        errors.append("environment-freeze manifest does not pin exactly four artifacts")
        artifacts = artifacts if isinstance(artifacts, dict) else {}
    for name, pin in sorted(artifacts.items()):
        if not isinstance(pin, dict) or not isinstance(pin.get("path"), str):
            errors.append(f"artifact:{name}: malformed pin")
            continue
        _verify_pin(
            label=f"artifact:{name}",
            stored_path=pin["path"],
            expected=pin.get("sha256"),
            manifest_path=path,
            checks=checks,
            errors=errors,
        )
    return {"ok": not errors, "errors": errors, "checks": checks}
