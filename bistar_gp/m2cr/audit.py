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
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from bistar_gp.m2cr.capture import MANDATORY_MARKER_ATTESTATIONS
from bistar_gp.m2cr.environment_freeze import read_manifest_header
from bistar_gp.m2cr.serialization import (
    canonical_bytes,
    canonical_dumps,
    canonical_sha256,
    sha256_file,
)

__all__ = [
    "ClosureDerivationError",
    "V117_CANONICAL_SHA256",
    "derive_closure_events",
    "validate_ledger",
    "verify_closure",
    "verify_ledger_against_evidence",
    "verify_chain",
    "verify_infrastructure_manifest",
    "verify_evidence_ceiling_compliance",
    "band_masses_sum_identity",
    "verify_environment_freeze",
    "verify_preboundary_closure_complete",
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
_EVIDENCE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_RAW_MANIFEST_NAME = "RAW_MANIFEST.sha256"
_TERMINAL_RECORD_NAME = "terminal_record.json"
_RAW_MANIFEST_LINE = re.compile(r"^([0-9a-f]{64})  (\S[^\n]*)$")
# After R3 the protocol manifest is committed and never declarable-absent.
# The remaining members are produced only by R4 (diagnostic-record instance)
# and R5 (amendment manifest); D45 historical ledger semantics are unchanged.
_DECLARABLE_ABSENT = {
    "diagnostic_record_sha256",
    "amendment_manifest",
}
# Plan section 4.5.5 Stage-A frozen parent-supplied mapping, restated here so
# the auditor verifies the freeze independently of the generator.
_FROZEN_CHILD_ENV_FIXED = {
    "PYTHONHASHSEED": "0",
    "OMP_NUM_THREADS": "10",
    "OMP_DYNAMIC": "FALSE",
    "MKL_NUM_THREADS": "10",
    "VECLIB_MAXIMUM_THREADS": "10",
    "LC_ALL": "C",
    "TZ": "UTC",
    "PATH": "/usr/bin:/bin",
}
_RUN_LOCAL_KEYS = {
    "HOME",
    "TMPDIR",
    "XDG_CACHE_HOME",
    "XDG_CONFIG_HOME",
    "XDG_DATA_HOME",
    "XDG_STATE_HOME",
}
_IMPORTABLE_MANIFEST_ROOT_IDS = {
    "worktree",
    "stdlib",
    "lib-dynload",
    "site-packages",
}
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
    "native_stack_expectations",
    "evidence_ceilings",
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


class ClosureDerivationError(ValueError):
    """Captured evidence cannot yield one schema-expressible closure."""


def _record_asserts_payload_started(record: Mapping[str, Any]) -> bool | None:
    """Return the terminal record's definite payload-start assertion, if any."""

    status = record.get("status")
    if status in {"COMPLETED", "ALGORITHM_STOP"}:
        return True
    if status == "NOT_STARTED":
        return False
    if status == "INFRA_FAILURE":
        fault = record.get("fault")
        assertion = fault.get("payload_started") if isinstance(fault, dict) else None
        return assertion if isinstance(assertion, bool) else None
    return None


def _schema_error(error: Any) -> str:
    location = "/".join(str(part) for part in error.absolute_path)
    return f"schema violation at {location or '<root>'}: {error.message}"


def validate_ledger(jsonl_text: str) -> dict[str, Any]:
    """Validate ledger lines and every prospective cross-line transition.

    In particular, an ``authorization_consumed`` line is accepted only when
    ``derived_from`` resolves to an earlier, genuine ``payload_started`` line
    whose authorization id, launch-attempt id, and marker digest all match.
    Historical records are never eligible derivation sources.  A grant whose
    scope declares ``one_shot`` cannot start another launch attempt after its
    consumption, and every launch attempt must close through exactly one
    terminal channel (``pre_payload_terminal_outcome`` xor
    ``terminal_outcome``) by the end of the ledger.
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
    consumed_authorizations: set[str] = set()
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
            else:
                scope = grants[authorization_id].get("scope")
                one_shot = scope.get("one_shot") if isinstance(scope, dict) else None
                if one_shot is True and authorization_id in consumed_authorizations:
                    errors.append(
                        f"line {line_number}: launch attempt {launch_id} starts "
                        f"after one-shot authorization {authorization_id} was "
                        "consumed"
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
                # Plan §4.3: the scientific authorization is consumed iff
                # payload_started exists, so one-shot state flips HERE, not at
                # the later derived authorization_consumed line — otherwise a
                # relaunch between the two would pass the one-shot gate
                # (external audit F6).
                if isinstance(authorization_id, str):
                    consumed_authorizations.add(authorization_id)
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
            # Fail closed for one-shot scoping: any consumption event marks the
            # authorization consumed even when its derivation is itself invalid.
            if isinstance(authorization_id, str):
                consumed_authorizations.add(authorization_id)

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
        elif state["pre_payload_terminal"] is None and state["terminal"] is None:
            errors.append(
                f"launch attempt {launch_id} is dangling: it reached no terminal "
                "channel (pre_payload_terminal_outcome or terminal_outcome)"
            )
    return {
        "ok": not errors,
        "errors": errors,
        "line_count": len(lines),
        "event_count": len(parsed),
    }


def _run_directories(root: Path, errors: list[str]) -> dict[str, Path]:
    """Index the capture layout ``evidence_root/<run_id>/`` by launch attempt.

    Each committed run directory is self-contained and carries its own
    terminal record (plan section 4.4), whose ``launch_attempt_id`` associates
    the directory with its ledger events.  A directory without a parseable
    terminal record is simply not indexed, so every event pointing at it
    fails closed.
    """

    mapping: dict[str, Path] = {}
    if not root.is_dir():
        errors.append(f"evidence root is not a directory: {root}")
        return mapping
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        record_path = child / _TERMINAL_RECORD_NAME
        if not record_path.is_file():
            continue
        try:
            record = json.loads(record_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if not isinstance(record, dict):
            continue
        launch_id = record.get("launch_attempt_id")
        if not isinstance(launch_id, str):
            continue
        if launch_id in mapping:
            errors.append(
                f"ambiguous evidence: launch attempt {launch_id} has terminal "
                f"records in both {mapping[launch_id].name}/ and {child.name}/"
            )
            continue
        mapping[launch_id] = child
    return mapping


def _relpath_is_safe(relpath: str) -> bool:
    if relpath.startswith("/") or "\\" in relpath:
        return False
    parts = relpath.split("/")
    return all(part not in ("", ".", "..") for part in parts)


def _audit_raw_manifest(
    run_dir: Path,
    label: str,
    checks: list[dict[str, Any]],
    errors: list[str],
) -> None:
    """Strictly parse Layer 3 and prove it complete over Layer 2.

    Lines are ``<64hex>  <relpath>`` sorted strictly by relpath.  The listed
    set must equal the run directory's files minus ``RAW_MANIFEST.sha256``
    and ``terminal_record.json`` (the capture exclusion), and every listed
    file is rehashed.  Extra, missing, and tampered files all fail.
    """

    before = len(errors)
    manifest_path = run_dir / _RAW_MANIFEST_NAME
    entries: list[tuple[str, str]] = []
    try:
        text = manifest_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        errors.append(f"{label}: raw manifest is unreadable: {exc}")
        text = None
    if text is not None:
        if text and not text.endswith("\n"):
            errors.append(f"{label}: raw manifest lacks a final newline")
        else:
            previous: str | None = None
            for line_number, line in enumerate(text.split("\n")[:-1], start=1):
                match = (
                    _RAW_MANIFEST_LINE.fullmatch(line) if "\r" not in line else None
                )
                if match is None:
                    errors.append(
                        f"{label}: malformed raw manifest line {line_number}"
                    )
                    entries = []
                    break
                digest, relpath = match.group(1), match.group(2)
                if not _relpath_is_safe(relpath):
                    errors.append(
                        f"{label}: unsafe raw manifest relpath at line {line_number}"
                    )
                    entries = []
                    break
                if previous is not None and not (relpath > previous):
                    errors.append(
                        f"{label}: raw manifest relpaths are not strictly sorted "
                        f"at line {line_number}"
                    )
                    entries = []
                    break
                previous = relpath
                entries.append((digest, relpath))
            else:
                # Exclude only the ROOT two files by exact relative path, not
                # every nested file sharing a basename (external audit F7).
                excluded = {_RAW_MANIFEST_NAME, _TERMINAL_RECORD_NAME}
                actual = {
                    path.relative_to(run_dir).as_posix()
                    for path in run_dir.rglob("*")
                    if path.is_file()
                    and path.relative_to(run_dir).as_posix() not in excluded
                }
                listed = {relpath for _, relpath in entries}
                for relpath in sorted(actual - listed):
                    errors.append(f"{label}: unlisted evidence file {relpath}")
                for relpath in sorted(listed - actual):
                    errors.append(
                        f"{label}: listed evidence file is missing: {relpath}"
                    )
                for digest, relpath in entries:
                    target = run_dir / relpath
                    if not target.is_file():
                        continue
                    if sha256_file(target) != digest:
                        errors.append(
                            f"{label}: raw manifest digest mismatch for {relpath}"
                        )
    checks.append(
        {
            "label": label,
            "path": os.fspath(manifest_path),
            "status": "passed" if len(errors) == before else "failed",
            "entries": len(entries),
        }
    )


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
    """Verify prospective ledger digests against the capture evidence layout.

    The layout is the capture driver's ``<evidence_root>/<run_id>/`` (plan
    sections 3.1 and 4.4): ``prelaunch.json``, ``spawned.json``,
    ``payload_started.json``, ``events.jsonl``, ``stdout.txt``,
    ``stderr.txt``, attestation JSONs at the run root (a marker attestation's
    logical ``NAME`` resolves to its evidence-file ``<STEM>.json`` through
    capture's single ``MANDATORY_MARKER_ATTESTATIONS`` contract, under which
    four of the ten mandatory names are aliased — e.g. ``bytecode_scan`` ->
    ``bytecode.json`` — and any non-mandatory self-named attestation resolves
    to itself), per-node record files,
    ``RAW_MANIFEST.sha256``, and ``terminal_record.json``.  Run directories
    are associated to ledger events through their terminal record's
    ``launch_attempt_id``.  Terminal and pre-payload terminal records are
    rehashed against the cited digests and validated against the committed
    execution-record schema; ``RAW_MANIFEST.sha256`` is strictly parsed,
    proven complete over the directory, and every listed file rehashed.
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
        return {
            "ok": False,
            "errors": errors,
            "checks": checks,
            "event_count": stream_report["event_count"],
        }
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

    audited_kinds = {
        "payload_started",
        "terminal_outcome",
        "pre_payload_terminal_outcome",
    }
    run_dirs = _run_directories(root, errors)
    closure_kinds_by_launch: dict[str, set[str]] = {}
    for event in events:
        kind = event.get("event")
        launch_id = event.get("launch_attempt_id")
        if kind in audited_kinds and isinstance(launch_id, str):
            closure_kinds_by_launch.setdefault(launch_id, set()).add(kind)

    for launch_id, run_dir in sorted(run_dirs.items()):
        marker_present = (run_dir / "payload_started.json").is_file()
        try:
            record = json.loads(
                (run_dir / _TERMINAL_RECORD_NAME).read_text(encoding="utf-8")
            )
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if not isinstance(record, dict):
            continue
        assertion = _record_asserts_payload_started(record)
        if record.get("status") == "INFRA_FAILURE" and assertion is None:
            errors.append(
                f"run {run_dir.name}: terminal record INFRA_FAILURE "
                "fault.payload_started is missing or not boolean"
            )
        elif assertion is not None and assertion != marker_present:
            errors.append(
                f"run {run_dir.name}: terminal record payload_started assertion "
                f"{assertion} disagrees with marker file presence {marker_present}"
            )

        closure_kinds = closure_kinds_by_launch.get(launch_id, set())
        if marker_present:
            if "pre_payload_terminal_outcome" in closure_kinds:
                errors.append(
                    f"marker present but attempt {launch_id} is closed pre-payload"
                )
            if not {"payload_started", "terminal_outcome"} <= closure_kinds:
                errors.append(
                    f"marker present but attempt {launch_id} lacks payload closure"
                )
        else:
            if closure_kinds & {"payload_started", "terminal_outcome"}:
                errors.append(
                    f"marker absent but attempt {launch_id} has a payload-branch "
                    "closure"
                )
            if "pre_payload_terminal_outcome" not in closure_kinds:
                errors.append(
                    f"marker absent but attempt {launch_id} lacks pre-payload closure"
                )

    for event in events:
        kind = event.get("event")
        if kind not in audited_kinds:
            continue
        launch_id = event.get("launch_attempt_id")
        if not isinstance(launch_id, str):
            errors.append(f"{kind}: event lacks a launch_attempt_id")
            continue
        attempt = run_dirs.get(launch_id)
        if attempt is None:
            errors.append(
                f"{kind}:{launch_id}: no run directory under the evidence root "
                "carries a terminal record for this launch attempt"
            )
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
                # Resolve the marker's logical attestation NAME to its on-disk
                # evidence-file STEM through capture's single authoritative
                # contract (D52 Update 10): four of the ten mandatory names are
                # aliased (e.g. bytecode_scan -> bytecode.json), and a
                # non-mandatory self-named attestation resolves to itself.  This
                # replaces the prior `<name>.json` assumption that false-rejected
                # real capture evidence for the aliased names.
                stem = MANDATORY_MARKER_ATTESTATIONS.get(name, name)
                _read_hashed_file(
                    attempt / f"{stem}.json",
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

        # terminal_outcome and pre_payload_terminal_outcome share the record
        # authentication path: resolve the cited digest, rehash, and validate
        # the record against the committed execution-record schema.
        label = (
            f"terminal_record:{launch_id}"
            if kind == "terminal_outcome"
            else f"pre_payload_terminal_record:{launch_id}"
        )
        terminal_path = attempt / _TERMINAL_RECORD_NAME
        raw_terminal = _read_hashed_file(
            terminal_path,
            event.get("terminal_record_sha256"),
            label,
            checks,
            errors,
        )
        if kind == "terminal_outcome":
            _read_hashed_file(
                attempt / _RAW_MANIFEST_NAME,
                event.get("raw_manifest_sha256"),
                f"raw_manifest:{launch_id}",
                checks,
                errors,
            )
        # A pre-payload failure still commits complete Layer-2/3 evidence
        # (plan §4.3), so the strict Layer-3 audit covers both terminal
        # kinds; only the ledger digest cross-check is terminal_outcome's,
        # whose event carries raw_manifest_sha256.
        _audit_raw_manifest(
            attempt, f"raw_manifest_audit:{launch_id}", checks, errors
        )
        if raw_terminal is None:
            continue
        try:
            record = json.loads(raw_terminal)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"{label}: malformed JSON: {exc}")
            continue
        failures = sorted(
            record_validator.iter_errors(record),
            key=lambda item: tuple(str(part) for part in item.absolute_path),
        )
        for failure in failures:
            errors.append(f"{label}: {_schema_error(failure)}")
        if not isinstance(record, dict):
            continue
        evidence = record.get("evidence")
        if isinstance(evidence, dict) and "raw_manifest_sha256" in evidence:
            raw_manifest_path = attempt / _RAW_MANIFEST_NAME
            try:
                rehashed_raw_manifest = sha256_file(raw_manifest_path)
            except OSError as exc:
                errors.append(
                    f"{label}: cannot rehash {_RAW_MANIFEST_NAME}: {exc}"
                )
            else:
                expected_raw_manifest = evidence.get("raw_manifest_sha256")
                status = (
                    "passed"
                    if expected_raw_manifest == rehashed_raw_manifest
                    else "failed"
                )
                checks.append(
                    {
                        "label": f"terminal_record_raw_manifest:{launch_id}",
                        "path": os.fspath(raw_manifest_path),
                        "status": status,
                        "expected": expected_raw_manifest,
                        "actual": rehashed_raw_manifest,
                    }
                )
                if status == "failed":
                    errors.append(
                        f"{label}: terminal record evidence.raw_manifest_sha256 "
                        f"does not equal the rehashed {_RAW_MANIFEST_NAME} file"
                    )
        if record.get("run_id") != attempt.name:
            errors.append(
                f"{label}: record run_id does not name its evidence directory "
                f"{attempt.name}"
            )
        bound_fields = ("launch_attempt_id", "status")
        if kind == "terminal_outcome":
            bound_fields = ("launch_attempt_id", "record_kind", "status")
        for field in bound_fields:
            if record.get(field) != event.get(field):
                errors.append(f"{label}: {field} mismatch")
        chain = record.get("chain")
        if not isinstance(chain, dict) or chain.get("authorization_id") != event.get(
            "authorization_id"
        ):
            errors.append(f"{label}: authorization_id mismatch")
        else:
            grant = grants.get(event.get("authorization_id"))
            frozen_chain = grant.get("frozen_chain") if isinstance(grant, dict) else {}
            for field, expected in (
                frozen_chain.items() if isinstance(frozen_chain, dict) else ()
            ):
                if chain.get(field) != expected:
                    errors.append(f"{label}: chain {field} mismatch")
        if kind == "terminal_outcome":
            if not isinstance(evidence, dict) or evidence.get(
                "raw_manifest_sha256"
            ) != event.get("raw_manifest_sha256"):
                errors.append(f"{label}: raw_manifest_sha256 mismatch")

    return {
        "ok": not errors,
        "errors": errors,
        "checks": checks,
        "event_count": stream_report["event_count"],
    }


def derive_closure_events(
    evidence_root: str | os.PathLike[str],
    run_id: str,
    pre_closure_ledger_jsonl: str,
    *,
    date: str,
) -> list[dict[str, Any]]:
    """Derive the unique ordered closure for one captured run directory."""

    run_dir = Path(evidence_root) / run_id
    terminal_path = run_dir / _TERMINAL_RECORD_NAME
    try:
        raw_terminal = terminal_path.read_bytes()
    except OSError as exc:
        raise ClosureDerivationError(
            f"terminal record is missing or unreadable: {exc}"
        ) from exc
    try:
        record = json.loads(raw_terminal.decode("utf-8", errors="strict"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ClosureDerivationError(f"terminal record is malformed: {exc}") from exc
    if not isinstance(record, dict):
        raise ClosureDerivationError("terminal record is not an object")

    try:
        record_schema = json.loads(
            _EXECUTION_RECORD_SCHEMA_PATH.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise ClosureDerivationError(
            f"cannot load execution-record schema: {exc}"
        ) from exc
    record_failures = sorted(
        Draft202012Validator(record_schema).iter_errors(record),
        key=lambda item: tuple(str(part) for part in item.absolute_path),
    )
    if record_failures:
        raise ClosureDerivationError(
            f"terminal record is schema-invalid: {_schema_error(record_failures[0])}"
        )
    if record.get("run_id") != run_id:
        raise ClosureDerivationError(
            "terminal record run_id does not name its evidence directory"
        )

    status = record["status"]
    launch_id = record["launch_attempt_id"]
    record_kind = record["record_kind"]
    chain = record["chain"]
    authorization_id = chain["authorization_id"]
    marker_path = run_dir / "payload_started.json"
    marker_present = marker_path.is_file()
    assertion = _record_asserts_payload_started(record)
    if status == "INFRA_FAILURE" and assertion is None:
        raise ClosureDerivationError(
            "terminal record INFRA_FAILURE fault.payload_started is missing or not "
            "boolean"
        )
    if assertion is not None and assertion != marker_present:
        raise ClosureDerivationError(
            "terminal record payload_started assertion "
            f"{assertion} disagrees with marker file presence {marker_present}"
        )

    try:
        ledger_schema = json.loads(_LEDGER_SCHEMA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ClosureDerivationError(
            f"cannot load authorization-ledger schema: {exc}"
        ) from exc
    ledger_validator = Draft202012Validator(ledger_schema)
    events: list[dict[str, Any]] = []
    seen_event_ids: set[str] = set()
    prior_event_number = -1
    for line_number, raw in enumerate(
        pre_closure_ledger_jsonl.splitlines(), start=1
    ):
        if not raw.strip():
            raise ClosureDerivationError(
                f"pre-closure ledger line {line_number} is blank"
            )
        try:
            event = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ClosureDerivationError(
                f"pre-closure ledger line {line_number} is invalid JSON: {exc.msg}"
            ) from exc
        if not isinstance(event, dict):
            raise ClosureDerivationError(
                f"pre-closure ledger line {line_number} is not an object"
            )
        failures = sorted(
            ledger_validator.iter_errors(event),
            key=lambda item: tuple(str(part) for part in item.absolute_path),
        )
        if failures:
            raise ClosureDerivationError(
                f"pre-closure ledger line {line_number} is schema-invalid: "
                f"{_schema_error(failures[0])}"
            )
        event_id = event["event_id"]
        match = _EVENT_ID.fullmatch(event_id)
        if match is None:
            raise ClosureDerivationError(
                f"pre-closure ledger line {line_number} has an invalid event_id"
            )
        event_number = int(match.group(1))
        if event_id in seen_event_ids:
            raise ClosureDerivationError(
                f"pre-closure ledger has duplicate event_id {event_id}"
            )
        if event_number <= prior_event_number:
            raise ClosureDerivationError(
                "pre-closure ledger event ids are not strictly increasing"
            )
        seen_event_ids.add(event_id)
        prior_event_number = event_number
        events.append(event)

    grants = [
        event
        for event in events
        if event.get("event") == "authorization_granted"
        and event.get("authorization_id") == authorization_id
    ]
    if len(grants) != 1:
        raise ClosureDerivationError(
            f"pre-closure ledger must contain exactly one grant for {authorization_id}"
        )
    grant = grants[0]
    frozen_chain = grant["frozen_chain"]
    for field, expected in frozen_chain.items():
        if chain.get(field) != expected:
            raise ClosureDerivationError(
                f"terminal record chain {field} does not match the grant"
            )
    if grant["scope"]["record_kind"] != record_kind:
        raise ClosureDerivationError(
            "terminal record record_kind does not match the grant scope"
        )

    launches = [
        event
        for event in events
        if event.get("event") == "launch_attempt_started"
        and event.get("launch_attempt_id") == launch_id
        and event.get("authorization_id") == authorization_id
    ]
    if len(launches) != 1:
        raise ClosureDerivationError(
            "pre-closure ledger must contain exactly one matching "
            f"launch_attempt_started for {launch_id}"
        )
    if any(
        event.get("launch_attempt_id") == launch_id
        and event.get("event")
        in {
            "payload_started",
            "terminal_outcome",
            "pre_payload_terminal_outcome",
            "authorization_consumed",
        }
        for event in events
    ):
        raise ClosureDerivationError(
            f"pre-closure ledger already contains a closure event for {launch_id}"
        )

    base_number = max(
        (int(_EVENT_ID.fullmatch(event["event_id"]).group(1)) for event in events),
        default=0,
    ) + 1

    evidence = record.get("evidence")
    raw_manifest_sha: str | None = None
    if isinstance(evidence, dict) and "raw_manifest_sha256" in evidence:
        raw_manifest_path = run_dir / _RAW_MANIFEST_NAME
        try:
            raw_manifest_sha = sha256_file(raw_manifest_path)
        except OSError as exc:
            raise ClosureDerivationError(
                f"{_RAW_MANIFEST_NAME} is missing or unreadable: {exc}"
            ) from exc
        if evidence["raw_manifest_sha256"] != raw_manifest_sha:
            raise ClosureDerivationError(
                "terminal record evidence.raw_manifest_sha256 does not equal the "
                f"rehashed {_RAW_MANIFEST_NAME} file"
            )

    def event_id(offset: int) -> str:
        return f"m2cr-ev-{base_number + offset:06d}"

    derived: list[dict[str, Any]]
    if marker_present:
        try:
            raw_marker = marker_path.read_bytes()
            marker = json.loads(raw_marker.decode("utf-8", errors="strict"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ClosureDerivationError(
                f"payload marker is missing, unreadable, or malformed: {exc}"
            ) from exc
        try:
            marker_is_canonical = raw_marker == canonical_bytes(marker)
        except (TypeError, ValueError):
            marker_is_canonical = False
        if (
            not isinstance(marker, dict)
            or set(marker) != _PAYLOAD_MARKER_FIELDS
            or not marker_is_canonical
        ):
            raise ClosureDerivationError(
                "payload marker is not an exact canonical marker object"
            )
        if marker.get("authorization_id") != authorization_id:
            raise ClosureDerivationError(
                "payload marker authorization_id disagrees with the terminal record"
            )
        if marker.get("launch_attempt_id") != launch_id:
            raise ClosureDerivationError(
                "payload marker launch_attempt_id disagrees with the terminal record"
            )
        if marker.get("execution_commit") != chain.get("execution_commit"):
            raise ClosureDerivationError(
                "payload marker execution_commit disagrees with the terminal record"
            )
        marker_chain = marker.get("chain")
        if marker_chain != chain:
            raise ClosureDerivationError(
                "payload marker chain disagrees with the terminal record"
            )
        allowed_statuses = {
            "diagnostic": {"COMPLETED", "ABORTED_BUDGET", "INFRA_FAILURE"},
            "result": {
                "COMPLETED",
                "ALGORITHM_STOP",
                "ABORTED_BUDGET",
                "INFRA_FAILURE",
            },
        }
        if status not in allowed_statuses.get(record_kind, set()):
            raise ClosureDerivationError(
                f"status {status} is not schema-expressible as a {record_kind} "
                "terminal_outcome"
            )
        if raw_manifest_sha is None:
            raise ClosureDerivationError(
                "payload-branch terminal record lacks evidence.raw_manifest_sha256"
            )
        try:
            terminal_record_sha = sha256_file(terminal_path)
            marker_sha = sha256_file(marker_path)
        except OSError as exc:
            raise ClosureDerivationError(
                f"closure evidence file is missing or unreadable: {exc}"
            ) from exc
        derived = [
            {
                "schema_version": 1,
                "event": "payload_started",
                "event_id": event_id(0),
                "authorization_id": marker["authorization_id"],
                "launch_attempt_id": marker["launch_attempt_id"],
                "date": date,
                "payload_started_sha256": marker_sha,
                "bound_to": {
                    "authorization_id": marker["authorization_id"],
                    "launch_attempt_id": marker["launch_attempt_id"],
                    "execution_commit": marker["execution_commit"],
                    "environment_freeze_manifest_sha256": marker["chain"][
                        "environment_freeze_manifest_sha256"
                    ],
                },
            },
            {
                "schema_version": 1,
                "event": "terminal_outcome",
                "event_id": event_id(1),
                "authorization_id": authorization_id,
                "launch_attempt_id": launch_id,
                "date": date,
                "record_kind": record_kind,
                "status": status,
                "terminal_record_sha256": terminal_record_sha,
                "raw_manifest_sha256": raw_manifest_sha,
            },
            {
                "schema_version": 1,
                "event": "authorization_consumed",
                "event_id": event_id(2),
                "authorization_id": authorization_id,
                "launch_attempt_id": launch_id,
                "date": date,
                "derived_from": {
                    "event": "payload_started",
                    "event_id": event_id(0),
                    "payload_started_sha256": marker_sha,
                },
            },
        ]
    else:
        if status not in {"INFRA_FAILURE", "NOT_STARTED"}:
            raise ClosureDerivationError(
                f"status {status} is not schema-expressible as a "
                "pre_payload_terminal_outcome"
            )
        try:
            terminal_record_sha = sha256_file(terminal_path)
        except OSError as exc:
            raise ClosureDerivationError(
                f"terminal record is missing or unreadable: {exc}"
            ) from exc
        derived = [
            {
                "schema_version": 1,
                "event": "pre_payload_terminal_outcome",
                "event_id": event_id(0),
                "authorization_id": authorization_id,
                "launch_attempt_id": launch_id,
                "date": date,
                "status": status,
                "terminal_record_sha256": terminal_record_sha,
                "consumes": False,
            }
        ]

    for offset, event in enumerate(derived):
        failures = sorted(
            ledger_validator.iter_errors(event),
            key=lambda item: tuple(str(part) for part in item.absolute_path),
        )
        if failures:
            raise ClosureDerivationError(
                f"derived closure event {offset + 1} is not schema-expressible: "
                f"{_schema_error(failures[0])}"
            )
    return derived


def verify_closure(
    pre_closure_ledger_jsonl: str,
    closure_ledger_jsonl: str,
    evidence_root: str | os.PathLike[str],
    run_id: str,
    *,
    date: str,
) -> dict[str, Any]:
    """Require byte-exact deterministic closure plus both standing audits."""

    try:
        derived = derive_closure_events(
            evidence_root, run_id, pre_closure_ledger_jsonl, date=date
        )
    except ClosureDerivationError as exc:
        return {"ok": False, "errors": [str(exc)]}

    errors: list[str] = []
    expected = pre_closure_ledger_jsonl + "".join(
        canonical_dumps(event) + "\n" for event in derived
    )
    if closure_ledger_jsonl != expected:
        errors.append(
            "closure ledger does not exactly equal the pre-closure ledger plus "
            "the deterministically derived canonical closure events"
        )

    stream_report = validate_ledger(closure_ledger_jsonl)
    if not stream_report["ok"]:
        errors.extend(
            f"ledger validation: {error}" for error in stream_report["errors"]
        )
    evidence_report = verify_ledger_against_evidence(
        closure_ledger_jsonl, evidence_root
    )
    if not evidence_report["ok"]:
        errors.extend(
            f"evidence verification: {error}"
            for error in evidence_report["errors"]
        )
    return {"ok": not errors, "errors": errors}


def _chain_check(
    checks: dict[str, dict[str, Any]],
    name: str,
    status: str,
    **details: Any,
) -> None:
    checks[name] = {"status": status, **details}


def _ledger_authorization_state(ledger_jsonl: str) -> dict[str, Any]:
    """Split committed authorizations into grants, historical ids, consumed ids."""

    grants: dict[str, dict[str, Any]] = {}
    historical: set[str] = set()
    consumed: set[str] = set()
    for raw in ledger_jsonl.splitlines():
        if not raw.strip():
            continue
        try:
            event = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        kind = event.get("event")
        authorization_id = event.get("authorization_id")
        if not isinstance(authorization_id, str):
            continue
        if kind == "authorization_granted":
            grants[authorization_id] = event
        elif kind == "historical_authorization_record":
            historical.add(authorization_id)
        elif kind in ("payload_started", "authorization_consumed"):
            # Plan §4.3: the scientific authorization is consumed iff
            # payload_started exists, so the consumed set flips at
            # payload_started, not only at the later derived
            # authorization_consumed line — otherwise verify_chain's
            # require_unconsumed check would authorize a relaunch in the crash
            # window between the two (external audit round-2 F5).
            consumed.add(authorization_id)
    return {"grants": grants, "historical": historical, "consumed": consumed}


def verify_chain(
    record_chain: dict[str, Any],
    expectations: dict[str, Any],
    record_kind: str,
    *,
    require_unconsumed: bool = False,
    ledger_jsonl: str | None = None,
) -> dict[str, Any]:
    """Verify each effective-chain member or state why it is unavailable.

    ``record_kind`` selects the exact B18 member set; chain shape is never
    inferred from whichever optional members happen to be present.
    ``expectations`` supplies committed digests under their chain-field names.
    A member with no caller-supplied expectation FAILS unless the caller
    explicitly lists it in ``expectations["expected_absent"]``, which is
    allowed only for the R4/R5-produced diagnostic record and amendment
    manifest.  The chain's ``authorization_id`` must
    resolve to a prospective ``authorization_granted`` ledger event; a
    ``historical_authorization_record`` never satisfies a chain (prereg v1.19:
    every future execution requires its own fresh explicit authorization).
    When the grant freezes an execution commit, the chain's commit must equal
    it.  ``require_unconsumed=True`` additionally rejects a grant the ledger
    already shows consumed (for pre-launch audits).  ``ledger_jsonl``
    overrides the committed ledger text (hermetic audits of proposed ledger
    states).  Pass ``verify_execution_commit=False`` to skip git-object
    lookup.
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

    # No default expected_absent: absence is a caller declaration, never an
    # assumption (fix A7).
    expected_absent = set(expectations.get("expected_absent", ()))
    invalid_absent = expected_absent - _DECLARABLE_ABSENT
    if invalid_absent:
        errors.append(
            "expected_absent contains members that are not the R4/R5-produced "
            "chain members: "
            + ", ".join(sorted(invalid_absent))
        )
    expected_absent &= _DECLARABLE_ABSENT
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
                reason="caller explicitly declared this R3/R5 member absent",
            )
        else:
            _chain_check(
                checks,
                name,
                "failed",
                actual=actual,
                reason="unverifiable: no committed artifact expectation supplied",
            )
            errors.append(
                f"{name} unverifiable: no committed artifact expectation supplied"
            )

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
    if ledger_jsonl is None:
        try:
            ledger_jsonl = _LEDGER_PATH.read_text(encoding="utf-8")
        except OSError as exc:
            ledger_jsonl = ""
            errors.append(f"cannot read the committed authorization ledger: {exc}")
    state = _ledger_authorization_state(ledger_jsonl)
    grant = state["grants"].get(authorization_id)
    if grant is not None:
        _chain_check(checks, "authorization_id", "passed", actual=authorization_id)
        frozen_chain = grant.get("frozen_chain")
        frozen_commit = (
            frozen_chain.get("execution_commit")
            if isinstance(frozen_chain, dict)
            else None
        )
        if frozen_commit is not None and commit != frozen_commit:
            _chain_check(
                checks,
                "grant_execution_commit",
                "failed",
                actual=commit,
                expected=frozen_commit,
                reason="chain execution_commit does not equal the grant's frozen commit",
            )
            errors.append(
                "execution_commit does not equal the commit frozen by the grant"
            )
        elif frozen_commit is not None:
            _chain_check(
                checks, "grant_execution_commit", "passed", actual=commit
            )
        if require_unconsumed and authorization_id in state["consumed"]:
            _chain_check(
                checks,
                "authorization_unconsumed",
                "failed",
                actual=authorization_id,
                reason="the ledger already shows this authorization consumed",
            )
            errors.append("authorization is already consumed in the ledger")
        elif require_unconsumed:
            _chain_check(
                checks, "authorization_unconsumed", "passed", actual=authorization_id
            )
    elif authorization_id in state["historical"]:
        _chain_check(
            checks,
            "authorization_id",
            "failed",
            actual=authorization_id,
            reason=(
                "historical_authorization_record never satisfies a chain; every "
                "future execution requires its own fresh prospective grant"
            ),
        )
        errors.append(
            "authorization_id resolves to a historical_authorization_record, "
            "not a prospective authorization_granted event"
        )
    else:
        _chain_check(checks, "authorization_id", "failed", actual=authorization_id)
        errors.append("authorization_id is not a prospective grant in the ledger")
    return {"ok": not errors, "errors": errors, "checks": checks}


def _discover_repo_root(start: Path) -> Path | None:
    """Return the nearest ancestor holding ``.git`` (a dir, or a worktree file)."""

    for candidate in (start, *start.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def _pin_resolution_base(
    manifest_path: Path, repo_root: str | os.PathLike[str] | None
) -> Path:
    """Resolve relative pins against the repo root, never the process CWD.

    An explicit ``repo_root`` wins; otherwise the manifest file's own
    repository is discovered by walking up to a ``.git`` entry, falling back
    to the manifest's directory for detached copies.  Repo-relative pins are
    what keep a manifest verifiable inside any worktree (fix A9).
    """

    if repo_root is not None:
        return Path(repo_root).resolve()
    discovered = _discover_repo_root(manifest_path.parent)
    return discovered if discovered is not None else manifest_path.parent


def _resolve_pinned_path(stored: str, resolution_base: Path) -> Path | None:
    path = Path(stored)
    if path.is_absolute():
        return path if path.is_file() else None
    candidate = resolution_base / path
    return candidate if candidate.is_file() else None


def _verify_pin(
    *,
    label: str,
    stored_path: str,
    expected: Any,
    resolution_base: Path,
    checks: list[dict[str, Any]],
    errors: list[str],
) -> Path | None:
    path = _resolve_pinned_path(stored_path, resolution_base)
    if path is None:
        checks.append(
            {"label": label, "path": stored_path, "status": "failed", "reason": "missing"}
        )
        errors.append(f"{label}: pinned file is missing: {stored_path}")
        return None
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
    return path


def verify_infrastructure_manifest(
    manifest_path: str | os.PathLike[str],
    repo_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Recompute every Layer-1a pin (the standing manifest==code check).

    Relative pins resolve against ``repo_root`` (default: the manifest
    file's repository, discovered by walking up to a ``.git`` entry).
    """

    path = Path(manifest_path).resolve()
    resolution_base = _pin_resolution_base(path, repo_root)
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
            resolution_base=resolution_base,
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
            resolved_pin = _resolve_pinned_path(pin["path"], resolution_base)
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
                resolution_base=resolution_base,
                checks=checks,
                errors=errors,
            )
    return {"ok": not errors, "errors": errors, "checks": checks}


def verify_evidence_ceiling_compliance(
    manifest_path: str | os.PathLike[str],
    repo_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """v1.20 §2 scope 1 + §4: static-artifact ceiling enforcement (audit CI).

    Authenticates the ``evidence_ceilings`` pin through the infrastructure
    manifest, parses the artifact CLOSED-WORLD (the auditor consumes only the
    one committed machine authority, restating no numeric value), then checks
    every artifact-table pinned file AND the infrastructure manifest file
    itself against the runtime-envelope/static-artifact per-file ceiling.
    The manifest's kind, schema version, top-level shape, and EXACT artifact
    key set are required first (Codex R2a review MAJOR): a stripped or
    reshaped manifest must fail this audit on its own, never silently shrink
    static coverage while reporting ``ok``.  Static freeze artifacts are
    governed here, never inside any per-run bundle; a breach fails
    regeneration/audit CI closed.
    """

    from bistar_gp.m2cr.environment_freeze import parse_evidence_ceilings

    path = Path(manifest_path).resolve()
    resolution_base = _pin_resolution_base(path, repo_root)
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
    shape_errors: list[str] = []
    if manifest.get("kind") != "m2cr_infrastructure_manifest":
        shape_errors.append("wrong infrastructure manifest kind")
    if manifest.get("schema_version") != 1:
        shape_errors.append("wrong infrastructure manifest schema_version")
    if set(manifest) != {"kind", "schema_version", "code", "artifacts", "r1_schemas"}:
        shape_errors.append(
            "infrastructure manifest has a non-canonical top-level key set"
        )
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict):
        shape_errors.append("infrastructure manifest lacks an artifacts section")
    elif set(artifacts) != _INFRASTRUCTURE_ARTIFACT_KEYS:
        shape_errors.append(
            "infrastructure manifest artifacts section does not have its "
            "exact required key set; static ceiling coverage would be "
            "incomplete"
        )
    if shape_errors:
        return {"ok": False, "errors": shape_errors, "checks": []}
    pin = artifacts.get("evidence_ceilings")
    if (
        not isinstance(pin, dict)
        or not isinstance(pin.get("path"), str)
        or not isinstance(pin.get("sha256"), str)
    ):
        return {
            "ok": False,
            "errors": [
                "infrastructure manifest does not pin evidence_ceilings"
            ],
            "checks": [],
        }
    ceilings_file = _resolve_pinned_path(pin["path"], resolution_base)
    if ceilings_file is None or not ceilings_file.is_file():
        return {
            "ok": False,
            "errors": [f"pinned evidence_ceilings absent: {pin['path']}"],
            "checks": [],
        }
    if sha256_file(ceilings_file) != pin["sha256"]:
        return {
            "ok": False,
            "errors": [
                "evidence_ceilings sha256 does not match its infrastructure pin"
            ],
            "checks": [],
        }
    try:
        ceilings = parse_evidence_ceilings(
            json.loads(ceilings_file.read_text(encoding="utf-8"))
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {
            "ok": False,
            "errors": [f"evidence_ceilings artifact malformed: {exc}"],
            "checks": [],
        }
    per_file = ceilings["runtime_envelope_static_artifact_per_file_bytes"]

    def check_size(label: str, target: Path) -> None:
        try:
            observed = target.stat().st_size
        except OSError as exc:
            errors.append(f"{label}: unreadable for size check: {exc}")
            return
        checks.append(
            {"label": label, "observed_bytes": observed, "ceiling_bytes": per_file}
        )
        if observed > per_file:
            errors.append(
                f"{label}: observed {observed} B exceeds the "
                f"runtime-envelope/static-artifact per-file ceiling "
                f"{per_file} B"
            )

    for name, artifact_pin in sorted(artifacts.items()):
        if not isinstance(artifact_pin, dict) or not isinstance(
            artifact_pin.get("path"), str
        ):
            errors.append(f"artifacts:{name}: malformed pin")
            continue
        resolved = _resolve_pinned_path(artifact_pin["path"], resolution_base)
        if resolved is None or not resolved.is_file():
            errors.append(
                f"artifacts:{name}: pinned file absent for size check: "
                f"{artifact_pin['path']}"
            )
            continue
        check_size(f"artifacts:{name}", resolved)
    check_size("infrastructure_manifest", path)
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


def _json_object(path: Path) -> dict[str, Any]:
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("artifact is not a JSON object")
    return parsed


def _freeze_semantic_failures(name: str, artifact_path: Path) -> list[str]:
    """Validate one pinned freeze artifact against its frozen semantics.

    Plan sections 4.5.5 and 4.5.7 (prereg v1.19 section 2) freeze the
    artifact *contents*, not merely their digests: the exact Stage-A mapping,
    a complete interpreter pin, a genuine (non-fixture, count-consistent)
    pre-boundary attestation set, and a v2 importable manifest opening with
    the four-root header.
    """

    failures: list[str] = []
    if name == "child_env_mapping":
        try:
            mapping = _json_object(artifact_path)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            return [f"unparseable child_env_mapping: {exc}"]
        if mapping.get("fixed") != _FROZEN_CHILD_ENV_FIXED:
            failures.append(
                "child_env_mapping fixed pairs do not equal the frozen "
                "Stage-A mapping exactly"
            )
        run_local = mapping.get("run_local_keys")
        if (
            not isinstance(run_local, list)
            or len(run_local) != len(_RUN_LOCAL_KEYS)
            or set(run_local) != _RUN_LOCAL_KEYS
        ):
            failures.append(
                "child_env_mapping run_local_keys is not exactly the six "
                "run-local keys"
            )
    elif name == "interpreter_pin":
        try:
            pin = _json_object(artifact_path)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            return [f"unparseable interpreter_pin: {exc}"]
        version = pin.get("version")
        members = {
            "path": pin.get("path"),
            "realpath": pin.get("realpath"),
            "sha256": pin.get("sha256"),
            "version_string": (
                version.get("version_string") if isinstance(version, dict) else None
            ),
        }
        for member, value in sorted(members.items()):
            if not isinstance(value, str) or not value:
                failures.append(f"interpreter_pin lacks a nonempty {member}")
    elif name == "preboundary_attestation_set":
        try:
            attestation = _json_object(artifact_path)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            return [f"unparseable preboundary_attestation_set: {exc}"]
        if attestation.get("test_fixture", False) is not False:
            failures.append(
                "preboundary_attestation_set declares test_fixture; fixtures "
                "cannot be frozen"
            )
        cache = attestation.get("dyld_shared_cache")
        cache = cache if isinstance(cache, dict) else {}
        if cache.get("discovered_subcache_count") != cache.get(
            "declared_subcache_count"
        ):
            failures.append(
                "preboundary_attestation_set discovered subcache count does "
                "not equal the declared count"
            )
        closure = attestation.get("bootstrap_closure")
        if not isinstance(closure, list) or not closure:
            failures.append(
                "preboundary_attestation_set bootstrap closure is empty"
            )
        else:
            # The bootstrap provably imports stdlib modules (json, hashlib,
            # importlib, ...) before the audit boundary, so a COMPLETE closure
            # per plan §4.5.2 must carry stdlib-origin entries, not just the
            # bootstrap file itself. A single-entry closure fails here
            # structurally, without needing to re-enumerate (external audit
            # F1); verify_preboundary_closure_complete does the exhaustive
            # re-enumeration check.
            paths = [
                entry.get("path", "")
                for entry in closure
                if isinstance(entry, Mapping)
            ]
            if not any("lib/python3." in path for path in paths):
                failures.append(
                    "preboundary_attestation_set bootstrap closure carries no "
                    "stdlib-origin entry; it cannot be the complete pre-boundary "
                    "closure required by plan §4.5.2"
                )
    elif name == "importable_artifact_manifest":
        try:
            header = read_manifest_header(artifact_path)
        except (OSError, ValueError) as exc:
            return [f"importable manifest lacks a valid v2 header: {exc}"]
        if set(header["roots"]) != _IMPORTABLE_MANIFEST_ROOT_IDS:
            failures.append(
                "importable manifest header roots are not exactly "
                "{worktree, stdlib, lib-dynload, site-packages}"
            )
    return failures


def verify_environment_freeze(
    freeze_manifest_path: str | os.PathLike[str],
    repo_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Rehash and semantically validate the static v5 freeze manifest.

    Beyond digest equality, each pinned artifact is parsed and checked
    against its frozen semantics (fix A8); failures are reported per member.
    Relative pins resolve against ``repo_root`` (default: the manifest
    file's repository, discovered by walking up to a ``.git`` entry).
    """

    path = Path(freeze_manifest_path).resolve()
    resolution_base = _pin_resolution_base(path, repo_root)
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
        resolved = _verify_pin(
            label=f"artifact:{name}",
            stored_path=pin["path"],
            expected=pin.get("sha256"),
            resolution_base=resolution_base,
            checks=checks,
            errors=errors,
        )
        if resolved is None:
            continue
        failures = _freeze_semantic_failures(name, resolved)
        checks.append(
            {
                "label": f"semantic:{name}",
                "path": pin["path"],
                "status": "failed" if failures else "passed",
                "reasons": failures,
            }
        )
        for failure in failures:
            errors.append(f"semantic:{name}: {failure}")
    return {"ok": not errors, "errors": errors, "checks": checks}


def verify_preboundary_closure_complete(
    attestation_set_path: str | os.PathLike[str],
    interpreter_path: str | os.PathLike[str],
    bootstrap_path: str | os.PathLike[str],
    worktree_root: str | os.PathLike[str],
) -> dict[str, Any]:
    """Prove the committed pre-boundary closure is complete (plan §4.5.2).

    Re-enumerates the bootstrap's import-only closure independently (via
    ``capture.enumerate_bootstrap_closure``) and requires every enumerated
    file origin to be pinned in the committed attestation set. An artifact
    that lists only ``bootstrap.py`` while the real closure imports 70+
    stdlib/native modules fails here (external audit F1). This spawns the
    pinned interpreter import-only; it performs no scientific computation.
    """

    from bistar_gp.m2cr.capture import enumerate_bootstrap_closure

    errors: list[str] = []

    def normalize(path: str) -> str:
        # A bistar_gp package module is identified by its package-relative
        # path, so the same module keys identically whether the freeze was
        # generated in one detached worktree and verified from another (the
        # per-launch worktree, plan §4.3). Host-global stdlib/native origins
        # carry no bistar_gp segment and keep their absolute realpath.
        real = os.path.realpath(path)
        marker = os.sep + "bistar_gp" + os.sep
        index = real.rfind(marker)
        if index != -1:
            return real[index + len(os.sep):]
        return real

    def committed_key(entry: Mapping[str, Any]) -> str | None:
        # F3: worktree-origin entries store a package-relative ``relpath``
        # (e.g. ``bistar_gp/m2cr/bootstrap.py``), which already matches the
        # normalized form of an enumerated worktree origin.  Host-global
        # entries keep an absolute ``path`` and are normalized to their
        # realpath.
        if entry.get("root") == "worktree" and isinstance(
            entry.get("relpath"), str
        ):
            return entry["relpath"]
        if isinstance(entry.get("path"), str):
            return normalize(entry["path"])
        return None

    artifact = json.loads(
        Path(attestation_set_path).resolve(strict=True).read_text(encoding="utf-8")
    )
    closure = artifact.get("bootstrap_closure")
    committed = {
        key
        for entry in closure
        if isinstance(entry, Mapping)
        for key in (committed_key(entry),)
        if key is not None
    } if isinstance(closure, list) else set()

    enumerated = enumerate_bootstrap_closure(
        interpreter_path, bootstrap_path, worktree_root
    )
    origins = {normalize(entry["origin"]) for entry in enumerated}
    missing = sorted(origins - committed)
    if missing:
        errors.append(
            "committed pre-boundary closure omits "
            f"{len(missing)} enumerated origin(s); first: {missing[0]}"
        )
    return {
        "ok": not errors,
        "errors": errors,
        "enumerated_count": len(origins),
        "committed_count": len(committed),
    }
