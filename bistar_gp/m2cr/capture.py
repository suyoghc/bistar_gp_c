"""Parent-side M2cR capture, terminal resolution, and reconciliation.

Frozen child exit-code protocol: ``0`` is a COMPLETED claim and ``3`` is an
ALGORITHM_STOP claim.  Every other return code is non-protocol and cannot by
itself certify a scientific or diagnostic outcome.  The parent applies plan
section 4.3's first-match precedence before writing the terminal envelope.

``events.jsonl`` and stdout/stderr are streaming Layer-2 evidence with the
per-line/append flush durability discipline of plan section 3.2.  Plan section
3.1's write-temp, fsync, atomic-rename discipline governs one-shot artifacts:
prelaunch/spawned attestations, the payload marker, raw manifest, and terminal
record.

Run-directory layout (plan section 4.4 self-contained directory): every
artifact of one launch attempt is confined to ``run_dir``.  The frozen layout
is enumerated by :data:`RUN_DIR_LAYOUT`; every attestation/output path in the
bootstrap config must resolve inside ``run_dir`` and capture refuses to spawn
otherwise.  A run directory is single-use: capture refuses to launch over any
prior run evidence (:data:`FRESH_RUN_DIR_BLOCKERS`).
"""

from __future__ import annotations

import json
import math
import os
import re
import signal
import subprocess
import tempfile
import threading
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bistar_gp.m2cr.events import check_stream_balance, parent_event_pipe
from bistar_gp.m2cr.payload_boundary import BoundaryViolation, verify_marker
from bistar_gp.m2cr.records import validate_fragment
from bistar_gp.m2cr.serialization import (
    atomic_write_bytes,
    atomic_write_canonical_json,
    canonical_bytes,
    sha256_file,
)

__all__ = [
    "ALGORITHM_STOP_EXIT_CODE",
    "BOOTSTRAP_CONFIG_NAME",
    "COMPLETED_EXIT_CODE",
    "FRESH_RUN_DIR_BLOCKERS",
    "FROZEN_INTERPRETER_FLAGS",
    "GRACE_SECONDS",
    "RAW_MANIFEST_NAME",
    "RUN_DIR_LAYOUT",
    "TERMINAL_RECORD_NAME",
    "WALL_CLOCK_CEILING_HOURS",
    "LaunchConfig",
    "RecordAssemblyError",
    "aggregates_from_node_records",
    "assemble_terminal_record",
    "capture_run",
    "empty_aggregates",
    "enumerate_bootstrap_closure",
    "launch_config_from_freeze",
    "reconcile_run",
    "run_capture",
    "validate_chain",
    "validate_terminal_record",
    "verify_preboundary_attestation_set",
    "write_raw_manifest",
]

COMPLETED_EXIT_CODE = 0
ALGORITHM_STOP_EXIT_CODE = 3
GRACE_SECONDS = 30
BOOTSTRAP_CONFIG_NAME = "bootstrap_config.json"
RAW_MANIFEST_NAME = "RAW_MANIFEST.sha256"
TERMINAL_RECORD_NAME = "terminal_record.json"
V117_CANONICAL_SHA256 = (
    "65381bc774e894dd9aaf2207cadd9cfa2f2735dafceff4bb39492086a9e522e2"
)
# Ratified safety ceiling (plan §7, ballot B10): 8 h wall clock for the
# full-closure diagnostic and for a future result run.  A safety ceiling,
# never a validated runtime prediction or a scientific threshold.
WALL_CLOCK_CEILING_HOURS = 8.0
# Frozen launch flags (plan §4.5.1); the pycache token is realized per run.
FROZEN_INTERPRETER_FLAGS = (
    "-S",
    "-s",
    "-P",
    "-B",
    "-X",
    "pycache_prefix={pycache_prefix}",
)
# Child attestation/output names routed into run_dir (bootstrap contract).
_ATTESTATION_NAMES = (
    "effect_proofs",
    "stage_a",
    "bytecode",
    "audit_canary",
    "stage_b_os",
    "stage_b_raw",
    "native_stack",
    "manifest_pre",
    "manifest_post",
    "sourceless",
    "import_inventory",
    "stage_c",
    "payload",
    "failure",
)
# Frozen self-contained run-directory layout (plan §4.4): every artifact one
# launch attempt may produce, relative to run_dir.  Trailing "/" marks a
# directory subtree.
RUN_DIR_LAYOUT = (
    "bootstrap_config.json",
    "prelaunch.json",
    "spawned.json",
    "events.jsonl",
    "stdout.txt",
    "stderr.txt",
    "payload_started.json",
    "effect_proofs.json",
    "stage_a.json",
    "bytecode.json",
    "audit_canary.json",
    "stage_b_os.json",
    "stage_b_raw.json",
    "native_stack.json",
    "manifest_pre.json",
    "manifest_post.json",
    "sourceless.json",
    "import_inventory.json",
    "stage_c.json",
    "payload.json",
    "bootstrap_failure.json",
    "nodes/",
    "home/",
    "tmp/",
    "xdg/",
    "pycache/",
    RAW_MANIFEST_NAME,
    TERMINAL_RECORD_NAME,
)
# A run directory holding any of these is a consumed launch attempt; capture
# refuses to reuse it (plan §4.3/§4.4).
FRESH_RUN_DIR_BLOCKERS = (
    "prelaunch.json",
    "spawned.json",
    "payload_started.json",
    "events.jsonl",
    RAW_MANIFEST_NAME,
    TERMINAL_RECORD_NAME,
)
_LAST_RESORT_DETAIL_LIMIT = 4000

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_GIT_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_RUN_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{2,63}$")
_LAUNCH_ID_RE = re.compile(r"^m2cr-launch-[0-9]{8}-[0-9]{2}$")
_AUTH_ID_RE = re.compile(r"^m2cr-auth-[0-9]{8}-[0-9]{2}$")
_PROTOCOL_STATUS = {
    COMPLETED_EXIT_CODE: "COMPLETED",
    ALGORITHM_STOP_EXIT_CODE: "ALGORITHM_STOP",
}
_FAULT_CLASSES = {
    "capture_fault",
    "attestation_fault",
    "environment_fault",
    "child_death",
    "missing_postcheck",
    "evidence_overflow",
    "schema_invalid_payload",
    "other",
}
_AGGREGATE_FIELDS = (
    "restart_count",
    "retry_count",
    "retry_failure_count",
    "rcond_fail_count",
    "symmetry_fail_count",
    "battery_fail_count",
)
_RUN_LOCAL_LAYOUT = {
    "HOME": "home",
    "TMPDIR": "tmp",
    "XDG_CACHE_HOME": "xdg/cache",
    "XDG_CONFIG_HOME": "xdg/config",
    "XDG_DATA_HOME": "xdg/data",
    "XDG_STATE_HOME": "xdg/state",
}


def _default_waiter(process: subprocess.Popen[Any], timeout: float) -> int:
    return process.wait(timeout=timeout)


@dataclass(frozen=True)
class LaunchConfig:
    interpreter_path: str
    interpreter_flags: Sequence[str]
    bootstrap_path: str
    worktree_root: str
    run_dir: str
    frozen_env: Mapping[str, Any]
    authorization_id: str
    launch_attempt_id: str
    run_id: str
    record_kind: str
    chain: dict[str, Any]
    wall_clock_ceiling_hours: float
    waiter: Callable[[subprocess.Popen[Any], float], Any] = field(
        default=_default_waiter, compare=False, repr=False
    )
    # Plan §4.5.2: path of the frozen pre-boundary attestation set; when set,
    # capture verifies every pinned digest on disk before any spawn.
    preboundary_attestation_set: str | None = None
    # Hermetic-test escape hatches only ("interpreter", "dyld"); the
    # bootstrap-closure entries are never skippable.
    preboundary_skip: Sequence[str] = ()


class RecordAssemblyError(ValueError):
    """A terminal branch or payload could not satisfy the frozen R1 schema."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _zero_aggregate_block() -> dict[str, int]:
    return {field_name: 0 for field_name in _AGGREGATE_FIELDS}


def empty_aggregates() -> dict[str, dict[str, int]]:
    return {
        "verdict_class": _zero_aggregate_block(),
        "diagnostic_class": _zero_aggregate_block(),
    }


def _class_for_node(node: Mapping[str, Any], stage_class_map: Mapping[Any, str]) -> str:
    candidates = (node.get("stage_id"), node.get("node_index"))
    for candidate in candidates:
        if candidate in stage_class_map:
            value = stage_class_map[candidate]
            break
    else:
        value = node.get("stage_class")
    if value not in {"verdict", "diagnostic"}:
        raise ValueError(f"node has no verdict/diagnostic stage class: {node!r}")
    return f"{value}_class"


def aggregates_from_node_records(
    node_records: Sequence[Mapping[str, Any]], stage_class_map: Mapping[Any, str]
) -> dict[str, dict[str, int]]:
    """Compute only the six plan section 5.3 well-defined sums."""

    totals = empty_aggregates()
    for node in node_records:
        block = totals[_class_for_node(node, stage_class_map)]
        optimizer = node.get("optimizer", {})
        if isinstance(optimizer, Mapping):
            restart_count = optimizer.get("restart_count", 0)
            if (
                not isinstance(restart_count, int)
                or isinstance(restart_count, bool)
                or restart_count < 0
            ):
                raise ValueError(
                    "optimizer restart_count must be a nonnegative integer"
                )
            block["restart_count"] += restart_count

        battery = node.get("battery")
        if isinstance(battery, Mapping) and battery.get("pass") is False:
            block["battery_fail_count"] += 1

        curvature = node.get("curvature")
        if not isinstance(curvature, Mapping):
            continue
        retry = curvature.get("retry")
        if isinstance(retry, Mapping) and retry.get("fired") is True:
            block["retry_count"] += 1
            if retry.get("positively_accepted") is not True:
                block["retry_failure_count"] += 1
        evaluations = [curvature.get("pre_retry")]
        if "post_retry" in curvature:
            evaluations.append(curvature.get("post_retry"))
        for evaluation in evaluations:
            if not isinstance(evaluation, Mapping):
                continue
            if (
                evaluation.get("spd") is not True
                or evaluation.get("conditioning_ok") is not True
            ):
                block["rcond_fail_count"] += 1
            if evaluation.get("symmetry_ok") is not True:
                block["symmetry_fail_count"] += 1
    return totals


def _require_pattern(value: Any, pattern: re.Pattern[str], label: str) -> str:
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        raise RecordAssemblyError(f"{label} has an invalid frozen shape")
    return value


def validate_chain(chain: Mapping[str, Any], record_kind: str) -> dict[str, Any]:
    """Runtime-check the exact B18 chain shape before Layer 4 is written."""

    if not isinstance(chain, Mapping):
        raise RecordAssemblyError("chain must be an object")
    diagnostic_keys = {
        "v117_canonical_sha256",
        "infrastructure_manifest_sha256",
        "environment_freeze_manifest_sha256",
        "protocol_manifest_sha256",
        "execution_commit",
        "authorization_id",
    }
    result_keys = diagnostic_keys | {"diagnostic_record_sha256", "amendment_manifest"}
    expected = diagnostic_keys if record_kind == "diagnostic" else result_keys
    if record_kind not in {"diagnostic", "result"}:
        raise RecordAssemblyError("record_kind must be diagnostic or result")
    if set(chain) != expected:
        raise RecordAssemblyError(
            f"chain members differ from the frozen {record_kind} enumeration"
        )
    if chain["v117_canonical_sha256"] != V117_CANONICAL_SHA256:
        raise RecordAssemblyError("v1.17 canonical digest mismatch")
    digest_fields = {
        "infrastructure_manifest_sha256",
        "environment_freeze_manifest_sha256",
        "protocol_manifest_sha256",
    }
    if record_kind == "result":
        digest_fields.add("diagnostic_record_sha256")
    for name in digest_fields:
        _require_pattern(chain[name], _SHA256_RE, name)
    if record_kind == "result" and chain["amendment_manifest"] != "none":
        _require_pattern(chain["amendment_manifest"], _SHA256_RE, "amendment_manifest")
    _require_pattern(chain["execution_commit"], _GIT_COMMIT_RE, "execution_commit")
    _require_pattern(chain["authorization_id"], _AUTH_ID_RE, "authorization_id")
    return dict(chain)


def _schema_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "docs/m2c_freeze/m2c_execution_record.schema_v1.json"
    )


def validate_terminal_record(
    record: Mapping[str, Any], schema_path: str | os.PathLike[str] | None = None
) -> None:
    """Validate a complete terminal envelope with Draft 2020-12."""

    try:
        from jsonschema import Draft202012Validator
    except ImportError as exc:
        raise RecordAssemblyError(
            "jsonschema is required for terminal assembly"
        ) from exc
    path = Path(schema_path) if schema_path is not None else _schema_path()
    with path.open("r", encoding="utf-8") as handle:
        schema = json.load(handle)
    validator = Draft202012Validator(schema)
    errors = sorted(
        validator.iter_errors(dict(record)), key=lambda item: list(item.path)
    )
    if errors:
        first = errors[0]
        location = "/".join(str(part) for part in first.absolute_path) or "<root>"
        raise RecordAssemblyError(
            f"terminal record schema error at {location}: {first.message}"
        )
    try:
        canonical_bytes(record)
    except (TypeError, ValueError) as exc:
        raise RecordAssemblyError(
            f"terminal record is not canonical-JSON encodable: {exc}"
        ) from exc


def assemble_terminal_record(
    *,
    record_kind: str,
    status: str,
    run_id: str,
    launch_attempt_id: str,
    chain: Mapping[str, Any],
    evidence: Mapping[str, Any] | None = None,
    stages: Sequence[Mapping[str, Any]] | None = None,
    aggregates: Mapping[str, Any] | None = None,
    payload: Mapping[str, Any] | None = None,
    stop_info: Mapping[str, Any] | None = None,
    interruption_info: Mapping[str, Any] | None = None,
    infra_fault: Mapping[str, Any] | None = None,
    not_started_info: Mapping[str, Any] | None = None,
    schema_path: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Assemble and validate one closed execution-record branch."""

    checked_chain = validate_chain(chain, record_kind)
    _require_pattern(run_id, _RUN_ID_RE, "run_id")
    _require_pattern(launch_attempt_id, _LAUNCH_ID_RE, "launch_attempt_id")
    base: dict[str, Any] = {
        "schema_version": 1,
        "record_kind": record_kind,
        "status": status,
        "run_id": run_id,
        "launch_attempt_id": launch_attempt_id,
        "chain": checked_chain,
    }
    if record_kind == "diagnostic":
        base["not_a_result"] = True

    if status == "COMPLETED":
        if evidence is None or stages is None or aggregates is None:
            raise RecordAssemblyError(
                "COMPLETED requires evidence, stages, and aggregates"
            )
        base.update(
            stages=list(stages), aggregates=dict(aggregates), evidence=dict(evidence)
        )
        if record_kind == "result":
            if payload is None or not isinstance(
                payload.get("result_payload"), Mapping
            ):
                raise RecordAssemblyError("result COMPLETED requires result_payload")
            base["result_payload"] = dict(payload["result_payload"])
    elif status == "ALGORITHM_STOP":
        if record_kind != "result":
            raise RecordAssemblyError("diagnostic ALGORITHM_STOP is unrepresentable")
        if evidence is None or stages is None or aggregates is None:
            raise RecordAssemblyError(
                "ALGORITHM_STOP requires evidence, stages, and aggregates"
            )
        selected_stop = stop_info
        if selected_stop is None and payload is not None:
            selected_stop = payload.get("stop")
        if not isinstance(selected_stop, Mapping):
            raise RecordAssemblyError("ALGORITHM_STOP requires stop_info")
        base.update(
            stop=dict(selected_stop),
            stages=list(stages),
            aggregates=dict(aggregates),
            evidence=dict(evidence),
        )
    elif status == "ABORTED_BUDGET":
        if interruption_info is None or evidence is None:
            raise RecordAssemblyError(
                "ABORTED_BUDGET requires interruption and evidence"
            )
        base.update(
            interruption=dict(interruption_info),
            stages=list(stages or []),
            aggregates=dict(aggregates or empty_aggregates()),
            evidence=dict(evidence),
        )
    elif status == "INFRA_FAILURE":
        if infra_fault is None or evidence is None:
            raise RecordAssemblyError("INFRA_FAILURE requires fault and evidence")
        base.update(fault=dict(infra_fault), evidence=dict(evidence))
        if stages is not None:
            base["stages"] = list(stages)
        if aggregates is not None:
            base["aggregates"] = dict(aggregates)
    elif status == "NOT_STARTED":
        if not_started_info is None:
            raise RecordAssemblyError("NOT_STARTED requires not_started_info")
        base["not_started"] = dict(not_started_info)
    else:
        raise RecordAssemblyError(f"unknown terminal status: {status}")
    validate_terminal_record(base, schema_path)
    return base


def _ensure_inside(root: Path, candidate: Path) -> None:
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"run-local directory escapes run root: {candidate}") from exc


def _prepare_run_directories(run_dir: Path) -> dict[str, str]:
    run_dir.mkdir(parents=True, exist_ok=True)
    root = run_dir.resolve(strict=True)
    result: dict[str, str] = {}
    for key, relative in _RUN_LOCAL_LAYOUT.items():
        path = (root / relative).resolve()
        _ensure_inside(root, path)
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".m2cr-write-probe"
        try:
            descriptor = os.open(probe, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            os.close(descriptor)
            probe.unlink()
        except OSError as exc:
            raise ValueError(
                f"run-local directory is not writable: {path}: {exc}"
            ) from exc
        result[key] = os.fspath(path)
    pycache = (root / "pycache").resolve()
    _ensure_inside(root, pycache)
    pycache.mkdir(parents=True, exist_ok=True)
    if any(pycache.iterdir()):
        raise ValueError("run-local pycache prefix must be empty")
    result["PYCACHE_PREFIX"] = os.fspath(pycache)
    return result


def _expand_run_local(value: str, run_dir: Path, local: Mapping[str, str]) -> str:
    substitutions = {
        "{run_dir}": os.fspath(run_dir),
        "{home}": local["HOME"],
        "{tmpdir}": local["TMPDIR"],
        "{xdg_cache}": local["XDG_CACHE_HOME"],
        "{xdg_config}": local["XDG_CONFIG_HOME"],
        "{xdg_data}": local["XDG_DATA_HOME"],
        "{xdg_state}": local["XDG_STATE_HOME"],
        "{pycache_prefix}": local["PYCACHE_PREFIX"],
    }
    for token, replacement in substitutions.items():
        value = value.replace(token, replacement)
    return value


def _realize_environment(
    spec: Mapping[str, Any], run_dir: Path, local: Mapping[str, str]
) -> tuple[dict[str, str], dict[str, Any]]:
    if "fixed" in spec and set(spec).issubset({"fixed", "run_local_keys"}):
        fixed_raw = spec.get("fixed")
        local_raw = spec.get("run_local_keys", list(_RUN_LOCAL_LAYOUT))
        if not isinstance(fixed_raw, Mapping):
            raise ValueError("frozen_env.fixed must be a mapping")
        fixed = {
            str(key): _expand_run_local(str(value), run_dir, local)
            for key, value in fixed_raw.items()
        }
        if isinstance(local_raw, Mapping):
            realized_local = {
                str(key): _expand_run_local(str(value), run_dir, local)
                for key, value in local_raw.items()
            }
        elif isinstance(local_raw, Sequence) and not isinstance(
            local_raw, (str, bytes)
        ):
            realized_local = {str(key): local[str(key)] for key in local_raw}
        else:
            raise ValueError("frozen_env.run_local_keys must be a mapping or sequence")
        environment = dict(fixed)
        environment.update(realized_local)
        bootstrap_spec: dict[str, Any] = {
            "fixed": fixed,
            "run_local_keys": realized_local,
        }
    else:
        environment = {
            str(key): _expand_run_local(str(value), run_dir, local)
            for key, value in spec.items()
        }
        for key in _RUN_LOCAL_LAYOUT:
            if key in environment:
                environment[key] = local[key]
        bootstrap_spec = dict(environment)
    if not environment or not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in environment.items()
    ):
        raise ValueError(
            "realized child environment must be a non-empty string mapping"
        )
    return environment, bootstrap_spec


def _load_bootstrap_template(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        result = json.load(handle)
    if not isinstance(result, dict):
        raise ValueError("bootstrap config must be an object")
    return result


def _payload_entry_path(template: Mapping[str, Any], worktree_root: Path) -> Path:
    explicit = template.get("payload_entry_path")
    if isinstance(explicit, str):
        path = Path(explicit)
        return (
            (worktree_root / path).resolve()
            if not path.is_absolute()
            else path.resolve()
        )
    spec = template.get("payload")
    entry = spec.get("entry") if isinstance(spec, Mapping) else spec
    if not isinstance(entry, str) or entry.count(":") != 1:
        raise ValueError("bootstrap payload does not name module:function")
    module_name = entry.split(":", 1)[0]
    module_path = worktree_root / (module_name.replace(".", "/") + ".py")
    if module_path.is_file():
        return module_path.resolve()
    package_path = worktree_root / module_name.replace(".", "/") / "__init__.py"
    if package_path.is_file():
        return package_path.resolve()
    raise ValueError(f"payload entry source was not found for {module_name}")


def _expanded_flags(flags: Sequence[str], pycache_prefix: str) -> list[str]:
    return [str(flag).replace("{pycache_prefix}", pycache_prefix) for flag in flags]


def _event_balance(events_path: Path) -> dict[str, Any]:
    if not events_path.is_file():
        return check_stream_balance([])
    with events_path.open("r", encoding="utf-8", errors="replace") as handle:
        return check_stream_balance(handle)


def _read_json_object(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    value = json.loads(raw.decode("utf-8", errors="strict"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} is not an object")
    if raw != canonical_bytes(value):
        raise ValueError(f"{path.name} is not canonical JSON")
    return value


def _node_evidence(run_dir: Path) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    nodes_dir = run_dir / "nodes"
    if not nodes_dir.is_dir():
        return result
    for path in sorted(nodes_dir.glob("*.json")):
        try:
            node = _read_json_object(path)
        except (OSError, ValueError, json.JSONDecodeError, UnicodeDecodeError):
            continue
        node_index = node.get("node_index")
        if (
            isinstance(node_index, int)
            and not isinstance(node_index, bool)
            and node_index >= 0
        ):
            result.append(
                {"node_index": node_index, "record_sha256": sha256_file(path)}
            )
    return sorted(result, key=lambda item: item["node_index"])


def _validated_node_records(
    run_dir: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Canonically parse and schema-validate every protocol node file."""

    nodes_dir = run_dir / "nodes"
    paths = sorted(nodes_dir.rglob("*.json")) if nodes_dir.is_dir() else []
    records: list[dict[str, Any]] = []
    evidence: list[dict[str, Any]] = []
    seen_indexes: set[int] = set()
    for path in paths:
        try:
            record = _read_json_object(path)
            validate_fragment(record, "#/$defs/per_node_record")
        except Exception as exc:
            raise RecordAssemblyError(
                f"invalid per-node evidence file {path.relative_to(run_dir)}: {exc}"
            ) from exc
        node_index = record.get("node_index")
        if (
            not isinstance(node_index, int)
            or isinstance(node_index, bool)
            or node_index < 0
        ):
            raise RecordAssemblyError(
                f"invalid per-node index in {path.relative_to(run_dir)}"
            )
        if node_index in seen_indexes:
            raise RecordAssemblyError(f"duplicate per-node index {node_index}")
        expected_name = f"node_{node_index:06d}.json"
        if path.name != expected_name:
            raise RecordAssemblyError(
                f"per-node filename {path.name} does not match {expected_name}"
            )
        seen_indexes.add(node_index)
        records.append(record)
        evidence.append({"node_index": node_index, "record_sha256": sha256_file(path)})
    records.sort(key=lambda item: item["node_index"])
    evidence.sort(key=lambda item: item["node_index"])
    return records, evidence


def _raw_files(run_dir: Path) -> list[Path]:
    excluded = {RAW_MANIFEST_NAME, TERMINAL_RECORD_NAME}
    return sorted(
        (
            path
            for path in run_dir.rglob("*")
            if path.is_file() and path.name not in excluded
        ),
        key=lambda path: path.relative_to(run_dir).as_posix(),
    )


def write_raw_manifest(run_dir: str | os.PathLike[str]) -> str:
    """Write Layer 3 over every closed Layer-2 file and return its digest."""

    root = Path(run_dir).resolve()
    lines = [
        f"{sha256_file(path)}  {path.relative_to(root).as_posix()}\n"
        for path in _raw_files(root)
    ]
    manifest_path = root / RAW_MANIFEST_NAME
    atomic_write_bytes(manifest_path, "".join(lines).encode("utf-8"))
    return sha256_file(manifest_path)


def _prelaunch(
    config: LaunchConfig,
    bootstrap_path: Path,
    payload_path: Path,
    environment: Mapping[str, str],
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "created_utc": _utc_now(),
        "config": {
            "interpreter_path": os.fspath(Path(config.interpreter_path).resolve()),
            "interpreter_flags": list(config.interpreter_flags),
            "bootstrap_path": os.fspath(bootstrap_path),
            "worktree_root": os.fspath(Path(config.worktree_root).resolve()),
            "run_dir": os.fspath(Path(config.run_dir).resolve()),
            "authorization_id": config.authorization_id,
            "launch_attempt_id": config.launch_attempt_id,
            "run_id": config.run_id,
            "record_kind": config.record_kind,
            "wall_clock_ceiling_hours": config.wall_clock_ceiling_hours,
            "preboundary_attestation_set": config.preboundary_attestation_set,
            "frozen_environment": dict(sorted(environment.items())),
            "chain": dict(config.chain),
        },
        "bootstrap_sha256": sha256_file(bootstrap_path),
        "payload_entry_path": os.fspath(payload_path),
        "payload_entry_sha256": sha256_file(payload_path),
    }


def _write_terminal(run_dir: Path, record: Mapping[str, Any]) -> str:
    return atomic_write_canonical_json(run_dir / TERMINAL_RECORD_NAME, dict(record))


def _bootstrap_fault(run_dir: Path) -> tuple[str, str] | None:
    failure_path = run_dir / "bootstrap_failure.json"
    if not failure_path.is_file():
        return None
    try:
        failure = _read_json_object(failure_path)
    except (OSError, ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        return "attestation_fault", f"malformed bootstrap failure evidence: {exc}"
    fault_class = failure.get("fault_class")
    detail = failure.get("detail")
    if fault_class not in _FAULT_CLASSES:
        if fault_class == "payload_fault":
            fault_class = "child_death"
        else:
            fault_class = "other"
    if not isinstance(detail, str) or not detail:
        detail = "bootstrap exited without usable failure detail"
    return fault_class, detail


def _load_protocol_payload(run_dir: Path) -> dict[str, Any]:
    return _read_json_object(run_dir / "payload.json")


def _stage_class_map_from_records(
    stages: Sequence[Mapping[str, Any]],
    node_records: Sequence[Mapping[str, Any]],
) -> dict[int, str]:
    """Map globally ordered node indices through ordered stage node counts."""

    ordered_nodes = sorted(node_records, key=lambda node: node.get("node_index", -1))
    mapping: dict[int, str] = {}
    offset = 0
    for position, stage in enumerate(stages):
        if not isinstance(stage, Mapping):
            raise RecordAssemblyError(f"stage {position} is not an object")
        stage_class = stage.get("stage_class")
        nodes_evaluated = stage.get("nodes_evaluated")
        if stage_class not in {"verdict", "diagnostic"}:
            raise RecordAssemblyError(f"stage {position} has invalid stage_class")
        if (
            not isinstance(nodes_evaluated, int)
            or isinstance(nodes_evaluated, bool)
            or nodes_evaluated < 0
        ):
            raise RecordAssemblyError(f"stage {position} has invalid nodes_evaluated")
        selected = ordered_nodes[offset : offset + nodes_evaluated]
        if len(selected) != nodes_evaluated:
            raise RecordAssemblyError(
                "stage node counts exceed the validated per-node evidence"
            )
        for node in selected:
            mapping[node["node_index"]] = stage_class
        offset += nodes_evaluated
    if offset != len(ordered_nodes):
        raise RecordAssemblyError(
            "stage node counts do not cover every validated per-node record"
        )
    return mapping


def _protocol_claim_is_valid(
    config: LaunchConfig,
    status: str,
    payload: Mapping[str, Any],
    evidence: Mapping[str, Any],
    node_records: Sequence[Mapping[str, Any]],
) -> tuple[list[Mapping[str, Any]], Mapping[str, Any]]:
    if payload.get("status") != status:
        raise RecordAssemblyError("payload status does not match child protocol exit")
    stages = payload.get("stages")
    aggregates = payload.get("aggregates")
    if not isinstance(stages, list) or not isinstance(aggregates, Mapping):
        raise RecordAssemblyError("payload lacks stages or aggregates")
    if payload.get("node_evidence_digests") != evidence.get("node_evidence_digests"):
        raise RecordAssemblyError(
            "payload node evidence digests do not match validated node files"
        )
    stage_class_map = _stage_class_map_from_records(stages, node_records)
    try:
        recomputed = aggregates_from_node_records(node_records, stage_class_map)
    except ValueError as exc:
        raise RecordAssemblyError(f"could not recompute aggregates: {exc}") from exc
    if dict(aggregates) != recomputed:
        raise RecordAssemblyError(
            f"payload aggregates differ from node records: claimed={dict(aggregates)}, "
            f"recomputed={recomputed}"
        )
    assemble_terminal_record(
        record_kind=config.record_kind,
        status=status,
        run_id=config.run_id,
        launch_attempt_id=config.launch_attempt_id,
        chain=config.chain,
        evidence=evidence,
        stages=stages,
        aggregates=aggregates,
        payload=payload,
    )
    return stages, recomputed


def _verify_protocol_marker(config: LaunchConfig, run_dir: Path) -> None:
    """Parent-side canonical marker validation for every protocol exit claim."""

    try:
        verify_marker(
            run_dir / "payload_started.json",
            authorization_id=config.authorization_id,
            launch_attempt_id=config.launch_attempt_id,
            execution_commit=config.chain.get("execution_commit"),
            chain=config.chain,
            prelaunch_sha256=sha256_file(run_dir / "prelaunch.json"),
        )
    except (BoundaryViolation, OSError) as exc:
        raise RecordAssemblyError(f"invalid payload-start marker: {exc}") from exc


def _require_fresh_run_dir(run_dir: Path) -> None:
    """Refuse to launch over any prior run evidence (plan §4.3/§4.4)."""

    if not run_dir.is_dir():
        return
    present = sorted(
        name for name in FRESH_RUN_DIR_BLOCKERS if (run_dir / name).exists()
    )
    if present:
        raise ValueError(
            "run_dir already holds launch evidence and is not reusable: "
            f"{present}"
        )


def _require_contained_attestation_paths(
    run_dir: Path, paths: Mapping[str, str]
) -> None:
    """Plan §4.4: every attestation/output path resolves inside run_dir."""

    for name in sorted(paths):
        candidate = Path(paths[name]).resolve()
        try:
            candidate.relative_to(run_dir)
        except ValueError as exc:
            raise ValueError(
                f"attestation path {name!r} escapes the self-contained run "
                f"directory: {paths[name]}"
            ) from exc


def _child_evidence_exists(paths: Mapping[str, str], events_path: Path) -> bool:
    """Whether any child-written artifact or event line exists (plan §4.3)."""

    for value in paths.values():
        if Path(value).is_file():
            return True
    try:
        return events_path.is_file() and events_path.stat().st_size > 0
    except OSError:
        return True


def verify_preboundary_attestation_set(
    attestation_set_path: str | os.PathLike[str],
    *,
    skip: Sequence[str] = (),
) -> dict[str, int]:
    """Verify the §4.5.2 pre-boundary pins on disk, before any spawn.

    ``skip`` accepts only ``"interpreter"`` and ``"dyld"`` (the dyld binary
    plus its shared-cache family) as hermetic-test escape hatches; the
    bootstrap-closure entries are never skippable.  Any mismatch, missing
    digest, or unreadable pinned file raises ``ValueError`` with the exact
    reason, refusing the launch with no child spawned.
    """

    skip_tokens = set(skip)
    unknown = skip_tokens - {"interpreter", "dyld"}
    if unknown:
        raise ValueError(f"unknown preboundary skip tokens: {sorted(unknown)}")
    artifact = _read_json_object(Path(attestation_set_path).resolve(strict=True))

    def check_entry(entry: Any, label: str) -> None:
        if not isinstance(entry, Mapping) or not isinstance(
            entry.get("path"), str
        ):
            raise ValueError(
                f"preboundary attestation entry {label} is malformed"
            )
        expected = entry.get("sha256")
        if not isinstance(expected, str) or _SHA256_RE.fullmatch(expected) is None:
            raise ValueError(
                f"preboundary attestation entry {label} lacks a frozen sha256"
            )
        try:
            actual = sha256_file(entry["path"])
        except OSError as exc:
            raise ValueError(
                f"preboundary attestation entry {label} is unreadable: "
                f"{entry['path']}: {exc}"
            ) from exc
        if actual != expected:
            raise ValueError(
                f"preboundary attestation mismatch at {label}: "
                f"{entry['path']} expected {expected}, actual {actual}"
            )

    checked = {"interpreter": 0, "dyld": 0, "closure": 0}
    if "interpreter" not in skip_tokens:
        check_entry(artifact.get("interpreter_binary"), "interpreter_binary")
        checked["interpreter"] = 1
    if "dyld" not in skip_tokens:
        check_entry(artifact.get("dyld"), "dyld")
        cache = artifact.get("dyld_shared_cache")
        if not isinstance(cache, Mapping):
            raise ValueError(
                "preboundary attestation dyld_shared_cache is malformed"
            )
        check_entry(cache.get("main"), "dyld_shared_cache.main")
        subcaches = cache.get("subcaches")
        if not isinstance(subcaches, list):
            raise ValueError(
                "preboundary attestation subcaches must be a list"
            )
        for index, entry in enumerate(subcaches):
            check_entry(entry, f"dyld_shared_cache.subcaches[{index}]")
        checked["dyld"] = 2 + len(subcaches)
    closure = artifact.get("bootstrap_closure")
    if not isinstance(closure, list):
        raise ValueError(
            "preboundary attestation bootstrap_closure must be a list"
        )
    for index, entry in enumerate(closure):
        check_entry(entry, f"bootstrap_closure[{index}]")
    checked["closure"] = len(closure)
    return checked


_CLOSURE_PROBE = """\
import importlib
import json
import os
import sys
import sysconfig
from types import ModuleType

bootstrap_path = sys.argv[1]
worktree = os.path.realpath(sys.argv[2])
stdlib = os.path.realpath(sysconfig.get_path("stdlib"))
dynload = os.path.realpath(os.path.join(stdlib, "lib-dynload"))
site_packages = os.path.realpath(sysconfig.get_path("purelib"))
sys.path[:] = [worktree, stdlib, dynload, site_packages]
package = ModuleType("bistar_gp")
package.__path__ = [os.path.join(worktree, "bistar_gp")]
package.__package__ = "bistar_gp"
package.__file__ = os.path.join(worktree, "bistar_gp", "__init__.py")
sys.modules["bistar_gp"] = package
subpackage = ModuleType("bistar_gp.m2cr")
subpackage.__path__ = [os.path.join(worktree, "bistar_gp", "m2cr")]
subpackage.__package__ = "bistar_gp.m2cr"
subpackage.__file__ = os.path.join(worktree, "bistar_gp", "m2cr", "__init__.py")
sys.modules["bistar_gp.m2cr"] = subpackage
module = importlib.import_module("bistar_gp.m2cr.bootstrap")
if os.path.realpath(getattr(module, "__file__", "")) != os.path.realpath(
    bootstrap_path
):
    raise SystemExit("closure probe imported an unexpected bootstrap origin")
closure = []
for name, loaded in sorted(sys.modules.items()):
    if loaded is None:
        continue
    spec = getattr(loaded, "__spec__", None)
    origin = getattr(spec, "origin", None) if spec is not None else None
    if not isinstance(origin, str):
        origin = getattr(loaded, "__file__", None)
    if (
        isinstance(origin, str)
        and origin not in ("built-in", "frozen")
        and os.path.isfile(origin)
    ):
        closure.append({"module": name, "origin": os.path.realpath(origin)})
print(json.dumps(closure, sort_keys=True))
"""


def enumerate_bootstrap_closure(
    interpreter_path: str | os.PathLike[str],
    bootstrap_path: str | os.PathLike[str],
    worktree_root: str | os.PathLike[str],
) -> list[dict[str, str]]:
    """Enumerate the bootstrap's import-only module closure (plan §4.5.2).

    Spawns the pinned interpreter under the frozen flags with a ``-c`` probe
    that replaces ``sys.path`` with the four roots, imports
    ``bistar_gp.m2cr.bootstrap`` WITHOUT calling ``main``, and reports every
    ``sys.modules`` entry with a file origin as ``{module, origin}``.
    """

    interpreter = Path(interpreter_path).resolve(strict=True)
    bootstrap = Path(bootstrap_path).resolve(strict=True)
    worktree = Path(worktree_root).resolve(strict=True)
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("PYTHON")
    }
    with tempfile.TemporaryDirectory(prefix="m2cr-closure-") as prefix:
        completed = subprocess.run(
            [
                os.fspath(interpreter),
                "-S",
                "-s",
                "-P",
                "-B",
                "-X",
                f"pycache_prefix={prefix}",
                "-c",
                _CLOSURE_PROBE,
                os.fspath(bootstrap),
                os.fspath(worktree),
            ],
            shell=False,
            env=environment,
            cwd=os.fspath(worktree),
            capture_output=True,
            text=True,
            timeout=120,
        )
    if completed.returncode != 0:
        raise ValueError(
            f"bootstrap closure probe failed: {completed.stderr.strip()}"
        )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"bootstrap closure probe emitted malformed JSON: {exc}"
        ) from exc
    if not isinstance(payload, list):
        raise ValueError("bootstrap closure probe must emit a list")
    closure: list[dict[str, str]] = []
    for item in payload:
        if (
            not isinstance(item, dict)
            or set(item) != {"module", "origin"}
            or not all(isinstance(item[key], str) for key in ("module", "origin"))
        ):
            raise ValueError("bootstrap closure probe emitted a malformed entry")
        closure.append({"module": item["module"], "origin": item["origin"]})
    return sorted(closure, key=lambda entry: entry["module"])


def _last_resort_terminal_record(
    *,
    record_kind: str,
    run_id: str,
    launch_attempt_id: str,
    chain: Mapping[str, Any],
    evidence: Mapping[str, Any],
    detail: str,
    payload_started: bool,
) -> dict[str, Any]:
    """Minimal always-schema-valid INFRA_FAILURE fallback (plan §4.3).

    Assembled directly, never through :func:`assemble_terminal_record`, so a
    failure inside branch assembly cannot recurse; identity fields were
    pattern-validated before spawn, evidence members are sanitized here, and
    the detail is truncated to a safe length.  This path cannot itself fail.
    """

    text = str(detail)[:_LAST_RESORT_DETAIL_LIMIT] or "terminal assembly failed"
    digest = evidence.get("raw_manifest_sha256") if isinstance(
        evidence, Mapping
    ) else None
    if not isinstance(digest, str) or _SHA256_RE.fullmatch(digest) is None:
        # The schema requires a digest-shaped member, so the placeholder is
        # the all-zero string; the detail declares it so no reader can take
        # it for a real Layer-3 digest.
        digest = "0" * 64
        text = (
            "last-resort envelope; raw-manifest digest unavailable, "
            "all-zero placeholder substituted. " + text
        )[:_LAST_RESORT_DETAIL_LIMIT]
    node_evidence: list[dict[str, Any]] = []
    raw_nodes = (
        evidence.get("node_evidence_digests")
        if isinstance(evidence, Mapping)
        else None
    )
    if isinstance(raw_nodes, Sequence) and not isinstance(raw_nodes, (str, bytes)):
        for item in raw_nodes:
            if (
                isinstance(item, Mapping)
                and isinstance(item.get("node_index"), int)
                and not isinstance(item.get("node_index"), bool)
                and item["node_index"] >= 0
                and isinstance(item.get("record_sha256"), str)
                and _SHA256_RE.fullmatch(item["record_sha256"]) is not None
            ):
                node_evidence.append(
                    {
                        "node_index": item["node_index"],
                        "record_sha256": item["record_sha256"],
                    }
                )
    node_evidence.sort(key=lambda item: item["node_index"])
    balanced = (
        bool(evidence.get("event_stream_balanced"))
        if isinstance(evidence, Mapping)
        else False
    )
    record: dict[str, Any] = {
        "schema_version": 1,
        "record_kind": record_kind,
        "status": "INFRA_FAILURE",
        "run_id": run_id,
        "launch_attempt_id": launch_attempt_id,
        "chain": dict(chain),
        "fault": {
            "fault_class": "other",
            "detail": text,
            "reconstructed": False,
            "payload_started": bool(payload_started),
        },
        "evidence": {
            "raw_manifest_sha256": digest,
            "node_evidence_digests": node_evidence,
            "event_stream_balanced": balanced,
        },
    }
    if record_kind == "diagnostic":
        record["not_a_result"] = True
    return record


def capture_run(config: LaunchConfig) -> dict[str, Any]:
    """Launch, supervise, resolve, and durably assemble one terminal record."""

    run_dir = Path(config.run_dir).resolve()
    # Plan §4.3: validate the frozen identity shapes BEFORE any prelaunch
    # artifact or child exists, so a malformed launch can never consume
    # anything.
    validate_chain(config.chain, config.record_kind)
    _require_pattern(config.run_id, _RUN_ID_RE, "run_id")
    _require_pattern(config.launch_attempt_id, _LAUNCH_ID_RE, "launch_attempt_id")
    _require_pattern(config.authorization_id, _AUTH_ID_RE, "authorization_id")
    _require_fresh_run_dir(run_dir)
    local = _prepare_run_directories(run_dir)
    environment, bootstrap_environment = _realize_environment(
        config.frozen_env, run_dir, local
    )
    bootstrap_path = Path(config.bootstrap_path).resolve(strict=True)
    worktree_root = Path(config.worktree_root).resolve(strict=True)
    bootstrap_config_path = run_dir / BOOTSTRAP_CONFIG_NAME
    template = _load_bootstrap_template(bootstrap_config_path)
    payload_path = _payload_entry_path(template, worktree_root)
    template.pop("event_fd", None)
    template.update(
        frozen_env=template.pop("expected_frozen_env", bootstrap_environment),
        expected_pycache_prefix=local["PYCACHE_PREFIX"],
        worktree_root=os.fspath(worktree_root),
        boundary={
            "authorization_id": config.authorization_id,
            "launch_attempt_id": config.launch_attempt_id,
            "execution_commit": config.chain.get("execution_commit"),
            "chain": dict(config.chain),
        },
    )
    paths = dict(template.get("attestation_paths", {}))
    paths.setdefault("payload_started", os.fspath(run_dir / "payload_started.json"))
    for name in _ATTESTATION_NAMES:
        paths.setdefault(name, os.fspath(run_dir / f"{name}.json"))
    paths["payload"] = os.fspath(run_dir / "payload.json")
    paths["failure"] = os.fspath(run_dir / "bootstrap_failure.json")
    paths["stage_c"] = os.fspath(run_dir / "stage_c.json")
    template["attestation_paths"] = paths
    _require_contained_attestation_paths(run_dir, paths)
    if config.preboundary_attestation_set is not None:
        # Plan §4.5.2: a pre-boundary digest mismatch refuses the launch;
        # the raised reason records the exact failing entry and no child is
        # ever spawned.
        verify_preboundary_attestation_set(
            config.preboundary_attestation_set, skip=config.preboundary_skip
        )
    prelaunch = _prelaunch(config, bootstrap_path, payload_path, environment)
    prelaunch_sha256 = atomic_write_canonical_json(
        run_dir / "prelaunch.json", prelaunch
    )

    events_path = run_dir / "events.jsonl"
    pipe = parent_event_pipe(events_path)
    pipe.start()
    atomic_write_canonical_json(bootstrap_config_path, template)

    stdout_handle = open(run_dir / "stdout.txt", "wb")
    stderr_handle = open(run_dir / "stderr.txt", "wb")
    process: subprocess.Popen[Any] | None = None
    spawn_error: BaseException | None = None
    capture_fault: str | None = None
    budget_kill = False
    signal_sequence: list[str] = []
    sigkill_issued = False
    spawn_thread: threading.Thread | None = None
    spawn_confirm_errors: list[BaseException] = []
    try:
        argv = [
            os.fspath(Path(config.interpreter_path).resolve()),
            *_expanded_flags(config.interpreter_flags, local["PYCACHE_PREFIX"]),
            os.fspath(bootstrap_path),
            os.fspath(bootstrap_config_path),
            str(pipe.write_fd),
        ]
        process = subprocess.Popen(
            argv,
            shell=False,
            env=environment,
            cwd=worktree_root,
            stdout=stdout_handle,
            stderr=stderr_handle,
            pass_fds=(pipe.write_fd,),
            close_fds=True,
        )

        def mark_spawned() -> None:
            try:
                pipe.hello_event.wait()
                if pipe.hello_payload is not None:
                    atomic_write_canonical_json(
                        run_dir / "spawned.json",
                        {
                            "pid": process.pid,
                            "received_utc": _utc_now(),
                            "hello": pipe.hello_payload,
                        },
                    )
            except BaseException as exc:
                # Plan §4.3: a failed spawn confirmation must surface as a
                # capture fault; it can never silently reclassify the run.
                spawn_confirm_errors.append(exc)

        spawn_thread = threading.Thread(target=mark_spawned, daemon=True)
        spawn_thread.start()
        pipe.close_write_end_in_parent()
        ceiling_seconds = config.wall_clock_ceiling_hours * 3600.0
        if not math.isfinite(ceiling_seconds) or ceiling_seconds <= 0:
            capture_fault = "wall-clock ceiling must be finite and positive"
            process.terminate()
            process.wait()
        else:
            try:
                process.wait(timeout=ceiling_seconds)
            except subprocess.TimeoutExpired:
                budget_kill = True
                process.send_signal(signal.SIGTERM)
                signal_sequence.append("SIGTERM")
                try:
                    config.waiter(process, GRACE_SECONDS)
                except subprocess.TimeoutExpired:
                    pass
                except BaseException as exc:
                    capture_fault = f"grace waiter failed after budget kill: {exc}"
                if process.poll() is None:
                    process.send_signal(signal.SIGKILL)
                    signal_sequence.append("SIGKILL")
                    sigkill_issued = True
                    process.wait()
    except (OSError, ValueError) as exc:
        spawn_error = exc
        pipe.close_write_end_in_parent()
    finally:
        if process is not None and process.poll() is None:
            process.kill()
            process.wait()
        pipe.join()
        pipe.hello_event.set()
        if spawn_thread is not None:
            spawn_thread.join()
        for label, handle in (
            ("stdout", stdout_handle),
            ("stderr", stderr_handle),
        ):
            try:
                handle.flush()
                os.fsync(handle.fileno())
            except OSError as exc:
                if capture_fault is None:
                    capture_fault = f"{label} durability flush failed: {exc}"
            finally:
                handle.close()

    if spawn_confirm_errors and capture_fault is None:
        capture_fault = (
            f"spawn confirmation write failed: {spawn_confirm_errors[0]}"
        )

    spawned_path = run_dir / "spawned.json"
    if spawned_path.is_file():
        try:
            if sha256_file(bootstrap_path) != prelaunch["bootstrap_sha256"]:
                capture_fault = (
                    "bootstrap changed between prelaunch and post-exit attestation"
                )
            elif sha256_file(payload_path) != prelaunch["payload_entry_sha256"]:
                capture_fault = (
                    "payload entry changed between prelaunch and post-exit attestation"
                )
        except OSError as exc:
            capture_fault = f"post-exit source re-attestation failed: {exc}"

    spawned = (run_dir / "spawned.json").is_file()
    balance = _event_balance(events_path)
    node_evidence = _node_evidence(run_dir)
    provisional_evidence = {
        "raw_manifest_sha256": "0" * 64,
        "node_evidence_digests": node_evidence,
        "event_stream_balanced": bool(balance["balanced"]),
    }
    payload: dict[str, Any] | None = None
    stages: Sequence[Mapping[str, Any]] | None = None
    aggregates: Mapping[str, Any] | None = None
    fault: tuple[str, str] | None = None

    # Frozen first-match precedence (plan §4.3).  Rule 1 distinguishes a
    # truly unstarted child from a lost spawn confirmation: when child
    # evidence exists without spawned.json, no state is silently
    # reclassified as NOT_STARTED.
    if not spawned:
        if spawn_confirm_errors or _child_evidence_exists(paths, events_path):
            reason = "spawn confirmation lost"
            if spawn_confirm_errors:
                reason += (
                    f": spawned.json write failed: {spawn_confirm_errors[0]}"
                )
            else:
                reason += ": child evidence exists without spawned.json"
            status = "INFRA_FAILURE"
            fault = ("capture_fault", reason)
        else:
            status = "NOT_STARTED"
    elif budget_kill:
        status = "ABORTED_BUDGET"
    else:
        bootstrap_fault = _bootstrap_fault(run_dir)
        protocol_marker_fault: str | None = None
        payload_claim_evidence = (run_dir / "payload.json").is_file() or (
            process is not None and process.returncode in _PROTOCOL_STATUS
        )
        if payload_claim_evidence:
            try:
                _verify_protocol_marker(config, run_dir)
            except RecordAssemblyError as exc:
                protocol_marker_fault = str(exc)
        if capture_fault is not None:
            status = "INFRA_FAILURE"
            fault = ("capture_fault", capture_fault)
        elif protocol_marker_fault is not None:
            status = "INFRA_FAILURE"
            fault = ("attestation_fault", protocol_marker_fault)
        elif bootstrap_fault is not None:
            status = "INFRA_FAILURE"
            fault = bootstrap_fault
        elif process is not None and process.returncode in _PROTOCOL_STATUS:
            protocol_status = _PROTOCOL_STATUS[process.returncode]
            try:
                _verify_protocol_marker(config, run_dir)
            except RecordAssemblyError as exc:
                status = "INFRA_FAILURE"
                fault = (
                    "attestation_fault",
                    str(exc),
                )
            else:
                stage_c_path = run_dir / "stage_c.json"
                if not stage_c_path.is_file():
                    status = "INFRA_FAILURE"
                    fault = (
                        "missing_postcheck",
                        "protocol exit lacked Stage C attestation",
                    )
                else:
                    try:
                        _read_json_object(stage_c_path)
                    except (
                        OSError,
                        ValueError,
                        json.JSONDecodeError,
                        UnicodeDecodeError,
                    ) as exc:
                        status = "INFRA_FAILURE"
                        fault = (
                            "attestation_fault",
                            f"malformed Stage C attestation: {exc}",
                        )
                    else:
                        if not balance["balanced"]:
                            status = "INFRA_FAILURE"
                            fault = (
                                "capture_fault",
                                f"unbalanced event stream: {balance['reason']}",
                            )
                        else:
                            try:
                                payload = _load_protocol_payload(run_dir)
                                node_records, validated_evidence = (
                                    _validated_node_records(run_dir)
                                )
                                node_evidence = validated_evidence
                                protocol_evidence = {
                                    **provisional_evidence,
                                    "node_evidence_digests": node_evidence,
                                }
                                stages, aggregates = _protocol_claim_is_valid(
                                    config,
                                    protocol_status,
                                    payload,
                                    protocol_evidence,
                                    node_records,
                                )
                            except (
                                OSError,
                                ValueError,
                                json.JSONDecodeError,
                                UnicodeDecodeError,
                            ) as exc:
                                status = "INFRA_FAILURE"
                                fault = ("schema_invalid_payload", str(exc))
                            else:
                                status = protocol_status
        else:
            status = "INFRA_FAILURE"
            code = process.returncode if process is not None else None
            fault = (
                "child_death",
                f"child exited outside protocol with return code {code}",
            )

    raw_manifest_sha256 = write_raw_manifest(run_dir)
    evidence = {
        "raw_manifest_sha256": raw_manifest_sha256,
        "node_evidence_digests": node_evidence,
        "event_stream_balanced": bool(balance["balanced"]),
    }
    try:
        if status == "NOT_STARTED":
            reason = f"spawn not confirmed: {spawn_error or 'no HELLO received'}"
            record = assemble_terminal_record(
                record_kind=config.record_kind,
                status=status,
                run_id=config.run_id,
                launch_attempt_id=config.launch_attempt_id,
                chain=config.chain,
                not_started_info={
                    "prelaunch_sha256": prelaunch_sha256,
                    "reason": reason,
                },
            )
        elif status == "ABORTED_BUDGET":
            record = assemble_terminal_record(
                record_kind=config.record_kind,
                status=status,
                run_id=config.run_id,
                launch_attempt_id=config.launch_attempt_id,
                chain=config.chain,
                evidence=evidence,
                stages=stages or [],
                aggregates=aggregates or empty_aggregates(),
                interruption_info={
                    "ceiling_hours": config.wall_clock_ceiling_hours,
                    "signal_sequence": signal_sequence,
                    "grace_seconds": GRACE_SECONDS,
                    "sigkill_issued": sigkill_issued,
                },
            )
        elif status == "INFRA_FAILURE":
            fault_class, detail = fault or (
                "other",
                "uncategorized infrastructure failure",
            )
            record = assemble_terminal_record(
                record_kind=config.record_kind,
                status=status,
                run_id=config.run_id,
                launch_attempt_id=config.launch_attempt_id,
                chain=config.chain,
                evidence=evidence,
                infra_fault={
                    "fault_class": fault_class,
                    "detail": detail,
                    "reconstructed": False,
                    "payload_started": (run_dir / "payload_started.json").is_file(),
                },
            )
        else:
            try:
                record = assemble_terminal_record(
                    record_kind=config.record_kind,
                    status=status,
                    run_id=config.run_id,
                    launch_attempt_id=config.launch_attempt_id,
                    chain=config.chain,
                    evidence=evidence,
                    stages=stages,
                    aggregates=aggregates,
                    payload=payload,
                )
            except RecordAssemblyError as exc:
                record = assemble_terminal_record(
                    record_kind=config.record_kind,
                    status="INFRA_FAILURE",
                    run_id=config.run_id,
                    launch_attempt_id=config.launch_attempt_id,
                    chain=config.chain,
                    evidence=evidence,
                    infra_fault={
                        "fault_class": "schema_invalid_payload",
                        "detail": str(exc),
                        "reconstructed": False,
                        "payload_started": (
                            run_dir / "payload_started.json"
                        ).is_file(),
                    },
                )
    except Exception as exc:
        # Plan §4.3 last resort: if the chosen branch cannot assemble, a
        # minimal always-schema-valid INFRA_FAILURE record is still written.
        record = _last_resort_terminal_record(
            record_kind=config.record_kind,
            run_id=config.run_id,
            launch_attempt_id=config.launch_attempt_id,
            chain=config.chain,
            evidence=evidence,
            detail=f"terminal assembly failed for status {status}: {exc}",
            payload_started=(run_dir / "payload_started.json").is_file(),
        )
    _write_terminal(run_dir, record)
    return record


run_capture = capture_run


def _config_value(config: LaunchConfig | Mapping[str, Any], name: str) -> Any:
    if isinstance(config, LaunchConfig):
        return getattr(config, name)
    return config[name]


def reconcile_run(
    run_dir: str | os.PathLike[str], config: LaunchConfig | Mapping[str, Any]
) -> dict[str, Any]:
    """Assemble a reconstructed INFRA_FAILURE after parent death."""

    root = Path(run_dir).resolve()
    prelaunch = root / "prelaunch.json"
    if not prelaunch.is_file():
        raise RecordAssemblyError("reconciliation requires prelaunch.json")
    balance = _event_balance(root / "events.jsonl")
    node_evidence = _node_evidence(root)
    raw_manifest_sha256 = write_raw_manifest(root)
    evidence = {
        "raw_manifest_sha256": raw_manifest_sha256,
        "node_evidence_digests": node_evidence,
        "event_stream_balanced": bool(balance["balanced"]),
    }
    record = assemble_terminal_record(
        record_kind=_config_value(config, "record_kind"),
        status="INFRA_FAILURE",
        run_id=_config_value(config, "run_id"),
        launch_attempt_id=_config_value(config, "launch_attempt_id"),
        chain=_config_value(config, "chain"),
        evidence=evidence,
        infra_fault={
            "fault_class": "capture_fault",
            "detail": "terminal envelope reconstructed after parent death",
            "reconstructed": True,
            "payload_started": (root / "payload_started.json").is_file(),
        },
    )
    _write_terminal(root, record)
    return record


_FOUR_ROOT_IDS = ("worktree", "stdlib", "lib-dynload", "site-packages")


def _read_manifest_v2_header(path: Path) -> dict[str, str]:
    """Read the importable-manifest format-v2 header's frozen roots.

    Delegates the header parse to the single shared implementation in
    :mod:`bistar_gp.m2cr.environment_freeze` (a late import keeps capture's
    import surface unchanged), then requires exactly the four frozen root
    ids for launch derivation.
    """

    from bistar_gp.m2cr.environment_freeze import read_manifest_header

    header = read_manifest_header(path)
    roots = header["roots"]
    if set(roots) != set(_FOUR_ROOT_IDS):
        raise ValueError(
            "importable manifest header roots must name exactly the four "
            "frozen root ids"
        )
    return {name: roots[name] for name in _FOUR_ROOT_IDS}


def _pinned_artifact(freeze: Mapping[str, Any], name: str, base: Path) -> Path:
    """Resolve and digest-authenticate one environment-freeze artifact pin."""

    artifacts = freeze.get("artifacts")
    if not isinstance(artifacts, Mapping) or name not in artifacts:
        raise ValueError(f"environment freeze manifest lacks artifact {name!r}")
    entry = artifacts[name]
    if not isinstance(entry, Mapping) or not isinstance(entry.get("path"), str):
        raise ValueError(f"environment freeze pin for {name!r} is malformed")
    path = Path(entry["path"])
    if not path.is_absolute():
        path = (base / path).resolve()
    expected = entry.get("sha256")
    if not isinstance(expected, str) or _SHA256_RE.fullmatch(expected) is None:
        raise ValueError(f"environment freeze pin for {name!r} lacks a sha256")
    actual = sha256_file(path)
    if actual != expected:
        raise ValueError(
            f"environment freeze pin mismatch for {name!r}: expected "
            f"{expected}, actual {actual}"
        )
    return path


def launch_config_from_freeze(
    env_freeze_manifest_path: str | os.PathLike[str],
    infrastructure_manifest_path: str | os.PathLike[str],
    *,
    run_dir: str | os.PathLike[str],
    run_id: str,
    authorization_id: str,
    launch_attempt_id: str,
    record_kind: str,
    chain: Mapping[str, Any],
    bootstrap_template_path: str | os.PathLike[str],
    worktree_root: str | os.PathLike[str],
    waiter: Callable[[subprocess.Popen[Any], float], Any] | None = None,
) -> LaunchConfig:
    """Derive a :class:`LaunchConfig` from the frozen artifacts (plan §3.1/§4.5).

    Authenticates the aggregating environment-freeze manifest against its
    Layer-1a infrastructure pin, authenticates each of the four freeze
    artifacts against the aggregating manifest, then derives: the interpreter
    path from the interpreter pin, the frozen ``-S -s -P -B`` flag set plus
    the per-run pycache prefix, the frozen child environment from the
    child-env mapping artifact, the four roots from the importable-manifest
    format-v2 header, and the attestation-set/manifest paths.  The B10
    safety ceiling (:data:`WALL_CLOCK_CEILING_HOURS`) is applied.  The
    bootstrap template is materialized as ``run_dir/bootstrap_config.json``
    with the derived ``four_roots`` and manifest path injected.
    """

    freeze_path = Path(env_freeze_manifest_path).resolve(strict=True)
    infrastructure_path = Path(infrastructure_manifest_path).resolve(strict=True)
    infrastructure = _read_json_object(infrastructure_path)
    infra_artifacts = infrastructure.get("artifacts")
    if not isinstance(infra_artifacts, Mapping):
        raise ValueError("infrastructure manifest lacks an artifacts section")
    freeze_pin = infra_artifacts.get("environment_freeze_manifest")
    if not isinstance(freeze_pin, Mapping):
        raise ValueError(
            "infrastructure manifest does not pin the environment freeze "
            "manifest"
        )
    actual_freeze_sha = sha256_file(freeze_path)
    if actual_freeze_sha != freeze_pin.get("sha256"):
        raise ValueError(
            "environment freeze manifest does not match its infrastructure "
            f"pin: expected {freeze_pin.get('sha256')}, actual "
            f"{actual_freeze_sha}"
        )
    freeze = _read_json_object(freeze_path)
    # Repo-contained pins are stored repo-relative (audit A9 contract); they
    # resolve against the repository root discovered from the manifest, never
    # against the manifest's own directory.
    base = freeze_path.parent
    probe = freeze_path.parent
    while probe != probe.parent:
        if (probe / ".git").exists():
            base = probe
            break
        probe = probe.parent
    interpreter_pin_path = _pinned_artifact(freeze, "interpreter_pin", base)
    env_mapping_path = _pinned_artifact(freeze, "child_env_mapping", base)
    manifest_path = _pinned_artifact(freeze, "importable_artifact_manifest", base)
    attestation_set_path = _pinned_artifact(
        freeze, "preboundary_attestation_set", base
    )

    pin = _read_json_object(interpreter_pin_path)
    interpreter_path = pin.get("path")
    if not isinstance(interpreter_path, str) or not os.path.isabs(
        interpreter_path
    ):
        raise ValueError("interpreter pin lacks an absolute interpreter path")

    mapping = _read_json_object(env_mapping_path)
    fixed = mapping.get("fixed")
    run_local_keys = mapping.get("run_local_keys")
    if not isinstance(fixed, Mapping) or not isinstance(run_local_keys, list):
        raise ValueError(
            "child environment mapping lacks fixed/run_local_keys members"
        )
    frozen_env: dict[str, Any] = {
        "fixed": dict(fixed),
        "run_local_keys": list(run_local_keys),
    }

    roots = _read_manifest_v2_header(manifest_path)
    # The worktree root is per-launch by definition (plan §4.5.1 pins the
    # CWD to the run's own fresh detached worktree); the manifest header
    # documents the freeze-time walk root, and the manifest's worktree
    # ENTRIES stay content-verified against the launch worktree by the
    # bootstrap's pre-import re-walk, which compares (root id, relpath,
    # sha256) independent of the physical path. Only the three host-global
    # roots derive from the header.
    worktree_root = os.fspath(Path(worktree_root).resolve(strict=True))
    roots = {**roots, "worktree": worktree_root}
    bootstrap_path = Path(worktree_root) / "bistar_gp/m2cr/bootstrap.py"
    if not bootstrap_path.is_file():
        raise ValueError(f"derived bootstrap is missing: {bootstrap_path}")

    template = _load_bootstrap_template(
        Path(bootstrap_template_path).resolve(strict=True)
    )
    template["four_roots"] = [roots[name] for name in _FOUR_ROOT_IDS]
    template["importable_artifact_manifest"] = os.fspath(manifest_path.resolve())
    run_root = Path(run_dir).resolve()
    run_root.mkdir(parents=True, exist_ok=True)
    atomic_write_canonical_json(run_root / BOOTSTRAP_CONFIG_NAME, template)

    arguments: dict[str, Any] = {
        "interpreter_path": interpreter_path,
        "interpreter_flags": FROZEN_INTERPRETER_FLAGS,
        "bootstrap_path": os.fspath(bootstrap_path),
        "worktree_root": worktree_root,
        "run_dir": os.fspath(run_root),
        "frozen_env": frozen_env,
        "authorization_id": authorization_id,
        "launch_attempt_id": launch_attempt_id,
        "run_id": run_id,
        "record_kind": record_kind,
        "chain": dict(chain),
        "wall_clock_ceiling_hours": WALL_CLOCK_CEILING_HOURS,
        "preboundary_attestation_set": os.fspath(attestation_set_path.resolve()),
    }
    if waiter is not None:
        arguments["waiter"] = waiter
    return LaunchConfig(**arguments)
