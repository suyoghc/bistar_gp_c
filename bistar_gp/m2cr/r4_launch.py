"""Generic M2cR production launch vehicle authorized by D51.

This module implements the narrow R3a infrastructure amendment described by
D51 and the launch boundary in plan sections 3.2, 4.3, 4.4, and 7.  It
consumes a closed-world canonical machine launch packet, validates the complete
launch authority read-only, and only under an explicit ``--execute`` flag
appends the ``launch_attempt_started`` ledger line and invokes the reviewed
factory/driver pair.  :mod:`bistar_gp.m2cr.capture` remains the sole
execution/capture authority; this module embeds no R4-specific ids or hashes.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from bistar_gp.m2cr.audit import validate_ledger, verify_chain
from bistar_gp.m2cr.capture import (
    WALL_CLOCK_CEILING_HOURS,
    RecordAssemblyError,
    capture_run,
    launch_config_from_freeze,
    validate_chain,
)
from bistar_gp.m2cr.serialization import (
    canonical_bytes,
    canonical_dumps,
    sha256_bytes,
    sha256_file,
)


PACKET_KIND = "m2cr_launch_packet"
PACKET_SCHEMA_VERSION = 1
PACKET_KEYS = frozenset(
    {
        "kind",
        "schema_version",
        "milestone",
        "record_kind",
        "authorization_id",
        "launch_attempt_id",
        "run_id",
        "execution_commit",
        "chain",
        "bootstrap_template",
        "manifests",
        "worktree_root",
        "evidence_dir",
        "wall_clock_ceiling_hours",
    }
)
MANIFEST_KEYS = frozenset(
    {"infrastructure", "environment_freeze", "protocol"}
)

# These public strings mirror capture's reviewed private paths.  A test asserts
# equality rather than making production code import private names.
COMMITTED_INFRA_RELPATH = (
    "docs/m2c_freeze/m2cr_infrastructure_manifest_v1.json"
)
COMMITTED_PROTOCOL_RELPATH = "docs/m2c_freeze/m2cr_protocol_manifest_v1.json"

LEDGER_RELPATH = "docs/m2c_freeze/m2c_authorization_ledger.jsonl"
LEDGER_SCHEMA_RELPATH = (
    "docs/m2c_freeze/m2c_authorization_ledger.schema_v1.json"
)
DIAGNOSTIC_PAYLOAD_ENTRY = (
    "bistar_gp.m2cr.diagnostic_payload:diagnostic_payload_entry"
)
DIAGNOSTIC_TEMPLATE_DOCUMENT = {
    "payload": {"entry": DIAGNOSTIC_PAYLOAD_ENTRY, "pass_context": True}
}

# Tests cross-check these pattern strings byte-for-byte against the frozen R1
# ledger schema.  RUN_ID_RE is the reviewed capture run-id rule.
AUTHORIZATION_ID_RE = re.compile(r"^m2cr-auth-[0-9]{8}-[0-9]{2}$")
LAUNCH_ATTEMPT_ID_RE = re.compile(r"^m2cr-launch-[0-9]{8}-[0-9]{2}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
GIT_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
EVENT_ID_RE = re.compile(r"^m2cr-ev-[0-9]{6}$")
RUN_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{2,63}$")

_MANIFEST_NAMES = ("infrastructure", "environment_freeze", "protocol")
# Mirrored because the production import surface is deliberately limited to
# the reviewed public factory/driver validators named by D51.
_FRESH_RUN_DIR_BLOCKERS = (
    "prelaunch.json",
    "spawned.json",
    "payload_started.json",
    "events.jsonl",
    "RAW_MANIFEST.sha256",
    "terminal_record.json",
)

Check = dict[str, str]


def _add_check(
    checks: list[Check], check: str, passed: bool, detail: str
) -> None:
    checks.append(
        {
            "check": check,
            "status": "PASS" if passed else "FAIL",
            "detail": detail,
        }
    )


def _all_pass(checks: Sequence[Check]) -> bool:
    return all(item["status"] == "PASS" for item in checks)


def _safe_relpath(value: Any) -> bool:
    if not isinstance(value, str) or not value or "\\" in value:
        return False
    if value.startswith("/"):
        return False
    return all(segment not in {"", ".", ".."} for segment in value.split("/"))


def _pattern_check(
    checks: list[Check], name: str, value: Any, pattern: re.Pattern[str]
) -> None:
    passed = isinstance(value, str) and pattern.fullmatch(value) is not None
    _add_check(
        checks,
        name,
        passed,
        f"{name} matches its frozen pattern"
        if passed
        else f"{name} does not match {pattern.pattern}",
    )


def load_packet(
    packet_path: str | os.PathLike[str],
) -> tuple[dict[str, Any] | None, bytes | None, list[Check]]:
    """Load and closed-world validate one canonical launch packet."""

    checks: list[Check] = []
    path = Path(packet_path)
    try:
        raw = path.read_bytes()
    except OSError as exc:
        _add_check(checks, "packet_read", False, f"cannot read packet: {exc}")
        return None, None, checks
    _add_check(checks, "packet_read", True, f"read {len(raw)} packet bytes")

    try:
        parsed = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        _add_check(checks, "packet_json", False, f"invalid packet JSON: {exc}")
        return None, raw, checks
    _add_check(checks, "packet_json", True, "packet is valid JSON")

    if not isinstance(parsed, dict):
        _add_check(checks, "packet_object", False, "packet must be an object")
        return None, raw, checks
    _add_check(checks, "packet_object", True, "packet is an object")

    try:
        canonical = raw == canonical_bytes(parsed)
    except (TypeError, ValueError) as exc:
        canonical = False
        canonical_detail = f"packet cannot be canonically serialized: {exc}"
    else:
        canonical_detail = (
            "packet uses canonical serialization"
            if canonical
            else "packet is not in canonical serialization"
        )
    _add_check(checks, "packet_canonical", canonical, canonical_detail)

    actual_keys = set(parsed)
    keys_ok = actual_keys == PACKET_KEYS
    if keys_ok:
        keys_detail = "packet has the exact closed key set"
    else:
        missing = sorted(PACKET_KEYS - actual_keys)
        extra = sorted(actual_keys - PACKET_KEYS)
        keys_detail = f"closed-world key mismatch; missing={missing}, extra={extra}"
    _add_check(checks, "packet_keys", keys_ok, keys_detail)

    kind_ok = parsed.get("kind") == PACKET_KIND
    _add_check(
        checks,
        "packet_kind",
        kind_ok,
        f"kind is {PACKET_KIND!r}"
        if kind_ok
        else f"kind must be {PACKET_KIND!r}",
    )
    schema_version = parsed.get("schema_version")
    schema_ok = (
        isinstance(schema_version, int)
        and not isinstance(schema_version, bool)
        and schema_version == PACKET_SCHEMA_VERSION
    )
    _add_check(
        checks,
        "packet_schema_version",
        schema_ok,
        "schema_version is integer 1"
        if schema_ok
        else "schema_version must be integer 1, not boolean",
    )
    milestone_ok = parsed.get("milestone") == "R4"
    _add_check(
        checks,
        "milestone",
        milestone_ok,
        "milestone is R4" if milestone_ok else "milestone must be R4",
    )
    record_kind_ok = parsed.get("record_kind") == "diagnostic"
    _add_check(
        checks,
        "record_kind",
        record_kind_ok,
        "record_kind is diagnostic"
        if record_kind_ok
        else "record_kind must be diagnostic",
    )

    _pattern_check(
        checks,
        "authorization_id",
        parsed.get("authorization_id"),
        AUTHORIZATION_ID_RE,
    )
    _pattern_check(
        checks,
        "launch_attempt_id",
        parsed.get("launch_attempt_id"),
        LAUNCH_ATTEMPT_ID_RE,
    )
    _pattern_check(checks, "run_id", parsed.get("run_id"), RUN_ID_RE)
    _pattern_check(
        checks, "execution_commit", parsed.get("execution_commit"), GIT_COMMIT_RE
    )

    worktree_root = parsed.get("worktree_root")
    worktree_absolute = (
        isinstance(worktree_root, str) and Path(worktree_root).is_absolute()
    )
    _add_check(
        checks,
        "worktree_root",
        worktree_absolute,
        "worktree_root is an absolute path"
        if worktree_absolute
        else "worktree_root must be an absolute path string",
    )

    chain = parsed.get("chain")
    try:
        validated_chain = validate_chain(chain, "diagnostic")
    except RecordAssemblyError as exc:
        validated_chain = None
        _add_check(checks, "chain", False, str(exc))
    else:
        _add_check(checks, "chain", True, "chain has the exact diagnostic shape")

    chain_authorization_ok = (
        validated_chain is not None
        and validated_chain["authorization_id"] == parsed.get("authorization_id")
    )
    _add_check(
        checks,
        "chain_authorization_id",
        chain_authorization_ok,
        "chain authorization_id equals packet authorization_id"
        if chain_authorization_ok
        else "chain authorization_id must equal packet authorization_id",
    )
    chain_commit_ok = (
        validated_chain is not None
        and validated_chain["execution_commit"] == parsed.get("execution_commit")
    )
    _add_check(
        checks,
        "chain_execution_commit",
        chain_commit_ok,
        "chain execution_commit equals packet execution_commit"
        if chain_commit_ok
        else "chain execution_commit must equal packet execution_commit",
    )

    manifests = parsed.get("manifests")
    manifests_keys_ok = (
        isinstance(manifests, dict) and set(manifests) == MANIFEST_KEYS
    )
    _add_check(
        checks,
        "manifests_keys",
        manifests_keys_ok,
        "manifests has the exact closed key set"
        if manifests_keys_ok
        else "manifests must contain exactly infrastructure, environment_freeze, and protocol",
    )
    valid_pins: dict[str, dict[str, str]] = {}
    for name in _MANIFEST_NAMES:
        pin = manifests.get(name) if isinstance(manifests, dict) else None
        pin_ok = (
            isinstance(pin, dict)
            and set(pin) == {"path", "sha256"}
            and _safe_relpath(pin.get("path"))
            and isinstance(pin.get("sha256"), str)
            and SHA256_RE.fullmatch(pin["sha256"]) is not None
        )
        if pin_ok:
            valid_pins[name] = pin
        _add_check(
            checks,
            f"manifest_{name}",
            pin_ok,
            f"{name} manifest pin is a closed safe path/digest object"
            if pin_ok
            else f"{name} manifest pin must be a closed safe path/digest object",
        )

    infrastructure_path_ok = (
        "infrastructure" in valid_pins
        and valid_pins["infrastructure"]["path"] == COMMITTED_INFRA_RELPATH
    )
    _add_check(
        checks,
        "manifest_infrastructure_path",
        infrastructure_path_ok,
        "infrastructure manifest uses the committed frozen relpath"
        if infrastructure_path_ok
        else f"infrastructure path must be {COMMITTED_INFRA_RELPATH}",
    )
    protocol_path_ok = (
        "protocol" in valid_pins
        and valid_pins["protocol"]["path"] == COMMITTED_PROTOCOL_RELPATH
    )
    _add_check(
        checks,
        "manifest_protocol_path",
        protocol_path_ok,
        "protocol manifest uses the committed frozen relpath"
        if protocol_path_ok
        else f"protocol path must be {COMMITTED_PROTOCOL_RELPATH}",
    )

    digest_members = {
        "infrastructure": "infrastructure_manifest_sha256",
        "environment_freeze": "environment_freeze_manifest_sha256",
        "protocol": "protocol_manifest_sha256",
    }
    for name in _MANIFEST_NAMES:
        member = digest_members[name]
        equality_ok = (
            validated_chain is not None
            and name in valid_pins
            and valid_pins[name]["sha256"] == validated_chain[member]
        )
        _add_check(
            checks,
            f"manifest_{name}_chain",
            equality_ok,
            f"{name} manifest digest equals chain {member}"
            if equality_ok
            else f"{name} manifest digest must equal chain {member}",
        )

    template = parsed.get("bootstrap_template")
    template_ok = (
        isinstance(template, dict)
        and set(template) == {"path", "sha256"}
        and _safe_relpath(template.get("path"))
        and isinstance(template.get("sha256"), str)
        and SHA256_RE.fullmatch(template["sha256"]) is not None
    )
    _add_check(
        checks,
        "bootstrap_template",
        template_ok,
        "bootstrap_template is a closed safe path/digest object"
        if template_ok
        else "bootstrap_template must be a closed safe path/digest object",
    )

    expected_evidence_dir = (
        f"docs/m2c_evidence/{parsed.get('run_id')}/"
        if isinstance(parsed.get("run_id"), str)
        else None
    )
    evidence_ok = (
        expected_evidence_dir is not None
        and parsed.get("evidence_dir") == expected_evidence_dir
    )
    _add_check(
        checks,
        "evidence_dir",
        evidence_ok,
        "evidence_dir is derived exactly from run_id"
        if evidence_ok
        else f"evidence_dir must be {expected_evidence_dir!r}",
    )

    ceiling = parsed.get("wall_clock_ceiling_hours")
    ceiling_ok = (
        isinstance(ceiling, (int, float))
        and not isinstance(ceiling, bool)
        and ceiling == WALL_CLOCK_CEILING_HOURS
    )
    _add_check(
        checks,
        "wall_clock_ceiling_hours",
        ceiling_ok,
        f"ceiling equals the frozen {WALL_CLOCK_CEILING_HOURS} hours"
        if ceiling_ok
        else f"ceiling must equal the frozen {WALL_CLOCK_CEILING_HOURS} hours exactly",
    )
    return parsed, raw, checks


def _git_bytes(
    root: Path, arguments: Sequence[str]
) -> tuple[int | None, bytes, str]:
    try:
        completed = subprocess.run(
            ["git", "-C", os.fspath(root), *arguments],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError as exc:
        return None, b"", str(exc)
    return (
        completed.returncode,
        completed.stdout,
        completed.stderr.decode("utf-8", errors="replace").strip(),
    )


def _repo_root_for_packet(packet_path: Path) -> tuple[Path | None, str]:
    start = packet_path.parent.resolve()
    returncode, stdout, error = _git_bytes(start, ("rev-parse", "--show-toplevel"))
    if returncode != 0:
        return None, error or "git rev-parse did not identify a repository"
    try:
        return Path(os.fsdecode(stdout).strip()).resolve(strict=True), ""
    except OSError as exc:
        return None, str(exc)


def _disk_digest(path: Path) -> tuple[str | None, str]:
    try:
        if not path.is_file():
            return None, f"missing file: {path}"
        return sha256_file(path), ""
    except OSError as exc:
        return None, str(exc)


def _git_show(root: Path, relpath: str) -> tuple[bytes | None, str]:
    returncode, stdout, error = _git_bytes(root, ("show", f"HEAD:{relpath}"))
    if returncode != 0:
        return None, error or f"git show HEAD:{relpath} failed"
    return stdout, ""


def _parsed_ledger_events(ledger_text: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for raw in ledger_text.splitlines():
        try:
            event = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            events.append(event)
    return events


def verify_against_repo(
    packet: Mapping[str, Any],
    packet_path: str | os.PathLike[str],
    repo_root: str | os.PathLike[str],
) -> tuple[list[Check], str | None]:
    """Verify every packet pin and prospective grant against ``repo_root``."""

    checks: list[Check] = []
    root = Path(repo_root)
    path = Path(packet_path)
    resolved_root = root.absolute()
    try:
        resolved_root = root.resolve(strict=True)
        resolved_packet = path.resolve(strict=True)
        relpath = resolved_packet.relative_to(resolved_root).as_posix()
        disk_packet = resolved_packet.read_bytes()
        committed_packet, packet_error = _git_show(resolved_root, relpath)
        packet_ok = committed_packet == disk_packet
        packet_detail = (
            "packet bytes equal the committed HEAD object"
            if packet_ok
            else packet_error or "packet bytes differ from the committed HEAD object"
        )
    except (OSError, ValueError) as exc:
        packet_ok = False
        packet_detail = f"packet is not a strict path under repo_root: {exc}"
    _add_check(checks, "packet_committed", packet_ok, packet_detail)

    template_pin = packet["bootstrap_template"]
    template_relpath = template_pin["path"]
    template_path = resolved_root / template_relpath
    template_digest, template_error = _disk_digest(template_path)
    template_disk_ok = template_digest == template_pin["sha256"]
    _add_check(
        checks,
        "template_disk",
        template_disk_ok,
        "template disk digest equals the packet pin"
        if template_disk_ok
        else template_error
        or f"template digest {template_digest} does not equal packet pin {template_pin['sha256']}",
    )

    try:
        template_bytes = template_path.read_bytes()
        template_document = json.loads(template_bytes)
        template_fixed_ok = (
            template_bytes == canonical_bytes(template_document)
            and packet["record_kind"] == "diagnostic"
            and template_document == DIAGNOSTIC_TEMPLATE_DOCUMENT
        )
        template_fixed_detail = (
            "template is canonical and equals the fixed diagnostic document"
            if template_fixed_ok
            else "template is not the canonical fixed diagnostic document"
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        template_fixed_ok = False
        template_fixed_detail = f"cannot validate fixed template: {exc}"
    _add_check(
        checks,
        "template_canonical_fixed",
        template_fixed_ok,
        template_fixed_detail,
    )

    committed_template, template_commit_error = _git_show(
        resolved_root, template_relpath
    )
    try:
        current_template = template_path.read_bytes()
    except OSError as exc:
        current_template = None
        template_commit_error = str(exc)
    template_committed_ok = (
        committed_template is not None
        and current_template is not None
        and committed_template == current_template
    )
    _add_check(
        checks,
        "template_committed",
        template_committed_ok,
        "template disk bytes equal the committed HEAD object"
        if template_committed_ok
        else template_commit_error or "template disk bytes differ from HEAD",
    )

    for name in _MANIFEST_NAMES:
        pin = packet["manifests"][name]
        manifest_path = resolved_root / pin["path"]
        digest, disk_error = _disk_digest(manifest_path)
        disk_ok = digest == pin["sha256"]
        _add_check(
            checks,
            f"manifest_disk_{name}",
            disk_ok,
            f"{name} manifest disk digest equals the packet pin"
            if disk_ok
            else disk_error
            or f"{name} manifest digest {digest} does not equal packet pin {pin['sha256']}",
        )
        committed, commit_error = _git_show(resolved_root, pin["path"])
        try:
            disk_bytes = manifest_path.read_bytes()
        except OSError as exc:
            disk_bytes = None
            commit_error = str(exc)
        committed_ok = (
            committed is not None
            and disk_bytes is not None
            and committed == disk_bytes
        )
        _add_check(
            checks,
            f"manifest_committed_{name}",
            committed_ok,
            f"{name} manifest disk bytes equal the committed HEAD object"
            if committed_ok
            else commit_error or f"{name} manifest disk bytes differ from HEAD",
        )

    ledger_path = resolved_root / LEDGER_RELPATH
    committed_ledger, ledger_commit_error = _git_show(
        resolved_root, LEDGER_RELPATH
    )
    try:
        ledger_bytes = ledger_path.read_bytes()
        ledger_text = ledger_bytes.decode("utf-8")
        ledger_newline = ledger_bytes.endswith(b"\n")
    except (OSError, UnicodeDecodeError) as exc:
        ledger_bytes = None
        ledger_text = None
        ledger_newline = False
        ledger_commit_error = str(exc)
    ledger_committed_ok = (
        committed_ledger is not None
        and ledger_bytes is not None
        and committed_ledger == ledger_bytes
        and ledger_newline
    )
    _add_check(
        checks,
        "ledger_committed",
        ledger_committed_ok,
        "ledger equals committed HEAD bytes and ends with a newline"
        if ledger_committed_ok
        else ledger_commit_error
        or "ledger must equal committed HEAD bytes and end with a newline",
    )

    if ledger_text is None:
        _add_check(
            checks,
            "ledger_stream_valid",
            False,
            "ledger text is unavailable",
        )
    else:
        try:
            ledger_report = validate_ledger(ledger_text)
            ledger_valid = ledger_report["ok"] is True
            ledger_detail = (
                "ledger stream passes schema and transition validation"
                if ledger_valid
                else f"ledger errors: {ledger_report.get('errors', [])}"
            )
        except Exception as exc:
            ledger_valid = False
            ledger_detail = f"ledger validation failed: {exc}"
        _add_check(
            checks, "ledger_stream_valid", ledger_valid, ledger_detail
        )

    if ledger_text is None:
        _add_check(checks, "chain_and_grant", False, "ledger text is unavailable")
    else:
        expectations = {
            "infrastructure_manifest_sha256": packet["manifests"][
                "infrastructure"
            ]["sha256"],
            "environment_freeze_manifest_sha256": packet["manifests"][
                "environment_freeze"
            ]["sha256"],
            "protocol_manifest_sha256": packet["manifests"]["protocol"][
                "sha256"
            ],
            "verify_execution_commit": False,
        }
        try:
            chain_report = verify_chain(
                dict(packet["chain"]),
                expectations=expectations,
                record_kind="diagnostic",
                require_unconsumed=True,
                ledger_jsonl=ledger_text,
            )
            chain_errors = list(chain_report.get("errors", []))
        except Exception as exc:
            chain_errors = [f"chain verification failed: {exc}"]
        if chain_errors:
            for error in chain_errors:
                _add_check(checks, "chain_and_grant", False, str(error))
        else:
            _add_check(
                checks,
                "chain_and_grant",
                True,
                "effective chain matches packet pins and a fresh prospective grant",
            )

    returncode, _, commit_error = _git_bytes(
        resolved_root,
        ("cat-file", "-e", f"{packet['execution_commit']}^{{commit}}"),
    )
    commit_ok = returncode == 0
    _add_check(
        checks,
        "execution_commit_resolvable",
        commit_ok,
        "execution_commit resolves as a commit in repo_root"
        if commit_ok
        else commit_error or "execution_commit does not resolve as a commit",
    )

    events = _parsed_ledger_events(ledger_text or "")
    grant = next(
        (
            event
            for event in events
            if event.get("event") == "authorization_granted"
            and event.get("authorization_id") == packet["authorization_id"]
        ),
        None,
    )
    packet_frozen_chain = {
        name: value
        for name, value in packet["chain"].items()
        if name != "authorization_id"
    }
    grant_chain_ok = (
        grant is not None and grant.get("frozen_chain") == packet_frozen_chain
    )
    _add_check(
        checks,
        "grant_frozen_chain_equality",
        grant_chain_ok,
        "grant frozen_chain equals all five packet chain members"
        if grant_chain_ok
        else "grant frozen_chain does not equal all five packet chain members",
    )

    launch_fresh = not any(
        event.get("launch_attempt_id") == packet["launch_attempt_id"]
        for event in events
    )
    _add_check(
        checks,
        "launch_attempt_fresh",
        launch_fresh,
        "launch_attempt_id does not appear in the ledger"
        if launch_fresh
        else "launch_attempt_id already appears in the ledger",
    )

    evidence_path = resolved_root / packet["evidence_dir"].rstrip("/")
    evidence_absent = not evidence_path.exists()
    if evidence_absent:
        evidence_detail = "derived evidence directory does not exist"
    else:
        blockers = [
            name
            for name in _FRESH_RUN_DIR_BLOCKERS
            if (evidence_path / name).exists()
        ]
        evidence_detail = (
            f"evidence directory already exists; fresh-run blockers present: {blockers}"
        )
    _add_check(
        checks,
        "evidence_dir_absent",
        evidence_absent,
        evidence_detail,
    )
    return checks, ledger_text


def verify_worktree(
    packet: Mapping[str, Any], repo_root: str | os.PathLike[str]
) -> list[Check]:
    """Verify the distinct, detached, clean launch worktree and its pins."""

    checks: list[Check] = []
    root = Path(repo_root).resolve()
    worktree = Path(packet["worktree_root"])
    worktree_exists = worktree.is_dir()
    _add_check(
        checks,
        "worktree_exists",
        worktree_exists,
        "worktree_root is an existing directory"
        if worktree_exists
        else "worktree_root is not an existing directory",
    )

    if worktree_exists:
        try:
            resolved_worktree = worktree.resolve(strict=True)
            distinct = resolved_worktree != root.resolve(strict=True)
        except OSError as exc:
            resolved_worktree = worktree
            distinct = False
            distinct_detail = str(exc)
        else:
            distinct_detail = (
                "worktree_root is distinct from repo_root"
                if distinct
                else "worktree_root must be distinct from repo_root"
            )
    else:
        resolved_worktree = worktree
        distinct = False
        distinct_detail = "worktree_root is unavailable"
    _add_check(checks, "worktree_distinct", distinct, distinct_detail)

    if worktree_exists:
        returncode, stdout, error = _git_bytes(
            resolved_worktree, ("rev-parse", "HEAD")
        )
        actual_head = os.fsdecode(stdout).strip() if returncode == 0 else None
        head_ok = returncode == 0 and actual_head == packet["execution_commit"]
        head_detail = (
            "worktree HEAD equals execution_commit"
            if head_ok
            else error
            or f"worktree HEAD {actual_head!r} does not equal execution_commit"
        )
    else:
        head_ok = False
        head_detail = "worktree_root is unavailable"
    _add_check(checks, "worktree_head", head_ok, head_detail)

    if worktree_exists:
        returncode, _, error = _git_bytes(
            resolved_worktree, ("symbolic-ref", "-q", "HEAD")
        )
        detached = returncode is not None and returncode != 0
        detached_detail = (
            "worktree HEAD is detached"
            if detached
            else error or "worktree HEAD is attached to a symbolic ref"
        )
    else:
        detached = False
        detached_detail = "worktree_root is unavailable"
    _add_check(checks, "worktree_detached", detached, detached_detail)

    if worktree_exists:
        returncode, stdout, error = _git_bytes(
            resolved_worktree,
            ("status", "--porcelain", "--untracked-files=no"),
        )
        clean = returncode == 0 and stdout == b""
        clean_detail = (
            "worktree has no tracked changes"
            if clean
            else error or "worktree has tracked changes"
        )
    else:
        clean = False
        clean_detail = "worktree_root is unavailable"
    _add_check(checks, "worktree_clean", clean, clean_detail)

    template_pin = packet["bootstrap_template"]
    template_digest, template_error = _disk_digest(
        resolved_worktree / template_pin["path"]
    )
    template_ok = template_digest == template_pin["sha256"]
    _add_check(
        checks,
        "worktree_template",
        template_ok,
        "worktree template digest equals the packet pin"
        if template_ok
        else template_error
        or f"worktree template digest {template_digest} does not equal packet pin",
    )
    for name in _MANIFEST_NAMES:
        pin = packet["manifests"][name]
        digest, error = _disk_digest(resolved_worktree / pin["path"])
        manifest_ok = digest == pin["sha256"]
        _add_check(
            checks,
            f"worktree_manifest_{name}",
            manifest_ok,
            f"worktree {name} manifest digest equals the packet pin"
            if manifest_ok
            else error
            or f"worktree {name} manifest digest {digest} does not equal packet pin",
        )
    return checks


def next_event_id(ledger_text: str) -> str:
    """Return the next strictly increasing six-digit ledger event id."""

    maximum = 0
    for raw in ledger_text.splitlines():
        if not raw.strip():
            continue
        try:
            event = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"cannot scan invalid ledger JSON: {exc}") from exc
        if not isinstance(event, dict):
            continue
        event_id = event.get("event_id")
        if isinstance(event_id, str) and EVENT_ID_RE.fullmatch(event_id):
            maximum = max(maximum, int(event_id.removeprefix("m2cr-ev-")))
    return f"m2cr-ev-{maximum + 1:06d}"


def validate_attempt_event(
    event: Mapping[str, Any], schema_path: str | os.PathLike[str]
) -> None:
    """Raise ``ValueError`` unless ``event`` satisfies the frozen line schema."""

    path = Path(schema_path)
    try:
        schema = json.loads(path.read_bytes())
        validator = Draft202012Validator(schema)
        errors = sorted(
            validator.iter_errors(dict(event)),
            key=lambda item: tuple(str(part) for part in item.absolute_path),
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot load ledger line schema: {exc}") from exc
    if errors:
        first = errors[0]
        location = "/".join(str(part) for part in first.absolute_path) or "<root>"
        raise ValueError(
            f"launch attempt event schema error at {location}: {first.message}"
        )


def _report_base(
    *,
    mode: str,
    packet_path: str,
    packet_sha256: str | None,
    checks: list[Check],
) -> dict[str, Any]:
    return {
        "kind": "m2cr_launch_report",
        "schema_version": 1,
        "mode": mode,
        "packet_path": packet_path,
        "packet_sha256": packet_sha256,
        "ok": _all_pass(checks),
        "checks": checks,
    }


def _print_report(report: Mapping[str, Any]) -> None:
    sys.stdout.write(canonical_dumps(dict(report)) + "\n")
    sys.stdout.flush()


def main(argv: Sequence[str] | None = None) -> int:
    """Validate a launch packet and, only with ``--execute``, launch it."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", required=True)
    parser.add_argument("--execute", action="store_true")
    arguments = parser.parse_args(argv)
    mode = "execute" if arguments.execute else "validate"
    packet_path_text = os.fspath(arguments.packet)

    packet, raw, checks = load_packet(packet_path_text)
    packet_sha = sha256_bytes(raw) if raw is not None else None
    if packet is None or not _all_pass(checks):
        _print_report(
            _report_base(
                mode=mode,
                packet_path=packet_path_text,
                packet_sha256=packet_sha,
                checks=checks,
            )
        )
        return 1

    repo_root, repo_error = _repo_root_for_packet(Path(packet_path_text))
    if repo_root is None:
        _add_check(
            checks,
            "packet_committed",
            False,
            f"cannot locate packet repository: {repo_error}",
        )
        _print_report(
            _report_base(
                mode=mode,
                packet_path=packet_path_text,
                packet_sha256=packet_sha,
                checks=checks,
            )
        )
        return 1

    repo_checks, ledger_text = verify_against_repo(
        packet, packet_path_text, repo_root
    )
    checks.extend(repo_checks)
    checks.extend(verify_worktree(packet, repo_root))
    if not _all_pass(checks) or ledger_text is None:
        _print_report(
            _report_base(
                mode=mode,
                packet_path=packet_path_text,
                packet_sha256=packet_sha,
                checks=checks,
            )
        )
        return 1

    if not arguments.execute:
        _print_report(
            _report_base(
                mode=mode,
                packet_path=packet_path_text,
                packet_sha256=packet_sha,
                checks=checks,
            )
        )
        return 0

    worktree = Path(packet["worktree_root"]).resolve(strict=True)
    run_dir = repo_root / packet["evidence_dir"].rstrip("/")
    manifests = packet["manifests"]
    template = packet["bootstrap_template"]
    try:
        config = launch_config_from_freeze(
            worktree / manifests["environment_freeze"]["path"],
            worktree / COMMITTED_INFRA_RELPATH,
            run_dir=run_dir,
            run_id=packet["run_id"],
            authorization_id=packet["authorization_id"],
            launch_attempt_id=packet["launch_attempt_id"],
            record_kind="diagnostic",
            chain=dict(packet["chain"]),
            bootstrap_template_path=worktree / template["path"],
            worktree_root=worktree,
        )
    except Exception as exc:
        _add_check(checks, "factory", False, str(exc))
        _print_report(
            _report_base(
                mode=mode,
                packet_path=packet_path_text,
                packet_sha256=packet_sha,
                checks=checks,
            )
        )
        return 2
    _add_check(checks, "factory", True, "reviewed launch factory accepted authority")

    attempt_event = {
        "schema_version": 1,
        "event": "launch_attempt_started",
        "event_id": next_event_id(ledger_text),
        "authorization_id": packet["authorization_id"],
        "launch_attempt_id": packet["launch_attempt_id"],
        "date": time.strftime("%Y-%m-%d"),
    }
    try:
        validate_attempt_event(
            attempt_event, repo_root / LEDGER_SCHEMA_RELPATH
        )
    except Exception as exc:
        _add_check(checks, "attempt_event_schema", False, str(exc))
        _print_report(
            _report_base(
                mode=mode,
                packet_path=packet_path_text,
                packet_sha256=packet_sha,
                checks=checks,
            )
        )
        return 1
    _add_check(
        checks,
        "attempt_event_schema",
        True,
        "launch_attempt_started event satisfies the frozen line schema",
    )

    ledger_path = repo_root / LEDGER_RELPATH
    try:
        with ledger_path.open("a", encoding="utf-8") as handle:
            handle.write(canonical_dumps(attempt_event) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        _add_check(checks, "ledger_append", False, str(exc))
        _print_report(
            _report_base(
                mode=mode,
                packet_path=packet_path_text,
                packet_sha256=packet_sha,
                checks=checks,
            )
        )
        return 1
    _add_check(
        checks,
        "ledger_append",
        True,
        "appended and fsynced exactly one canonical launch-attempt line",
    )

    try:
        record = capture_run(config)
    except Exception as exc:
        _add_check(checks, "capture_run", False, repr(exc))
        report = _report_base(
            mode=mode,
            packet_path=packet_path_text,
            packet_sha256=packet_sha,
            checks=checks,
        )
        report["capture_exception"] = repr(exc)
        _print_report(report)
        raise
    _add_check(
        checks,
        "capture_run",
        True,
        "reviewed capture driver returned a published terminal record",
    )

    payload_started_exists = (run_dir / "payload_started.json").is_file()
    payload_json_exists = (run_dir / "payload.json").is_file()
    terminal_path = run_dir / "terminal_record.json"
    terminal_record_sha256 = (
        sha256_file(terminal_path) if terminal_path.is_file() else None
    )
    evidence = record.get("evidence") if isinstance(record, Mapping) else None
    raw_manifest_sha256 = (
        evidence.get("raw_manifest_sha256")
        if isinstance(evidence, Mapping)
        else None
    )
    report = _report_base(
        mode=mode,
        packet_path=packet_path_text,
        packet_sha256=packet_sha,
        checks=checks,
    )
    report.update(
        {
            "run_dir": os.fspath(run_dir),
            "payload_started_exists": payload_started_exists,
            "authorization_consumed": payload_started_exists,
            "terminal_status": record.get("status"),
            "not_a_result": record.get("not_a_result"),
            "payload_json_exists": payload_json_exists,
            "terminal_record_sha256": terminal_record_sha256,
            "raw_manifest_sha256": raw_manifest_sha256,
            "launch_attempt_event_id": attempt_event["event_id"],
        }
    )
    _print_report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
