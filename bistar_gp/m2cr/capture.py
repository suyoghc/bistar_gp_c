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
"""

from __future__ import annotations

import json
import math
import os
import re
import signal
import subprocess
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
    "GRACE_SECONDS",
    "RAW_MANIFEST_NAME",
    "TERMINAL_RECORD_NAME",
    "LaunchConfig",
    "RecordAssemblyError",
    "aggregates_from_node_records",
    "assemble_terminal_record",
    "capture_run",
    "empty_aggregates",
    "reconcile_run",
    "run_capture",
    "validate_chain",
    "validate_terminal_record",
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


def capture_run(config: LaunchConfig) -> dict[str, Any]:
    """Launch, supervise, resolve, and durably assemble one terminal record."""

    run_dir = Path(config.run_dir).resolve()
    local = _prepare_run_directories(run_dir)
    environment, bootstrap_environment = _realize_environment(
        config.frozen_env, run_dir, local
    )
    bootstrap_path = Path(config.bootstrap_path).resolve(strict=True)
    worktree_root = Path(config.worktree_root).resolve(strict=True)
    bootstrap_config_path = run_dir / BOOTSTRAP_CONFIG_NAME
    template = _load_bootstrap_template(bootstrap_config_path)
    payload_path = _payload_entry_path(template, worktree_root)
    prelaunch = _prelaunch(config, bootstrap_path, payload_path, environment)
    prelaunch_sha256 = atomic_write_canonical_json(
        run_dir / "prelaunch.json", prelaunch
    )

    events_path = run_dir / "events.jsonl"
    pipe = parent_event_pipe(events_path)
    pipe.start()
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
    for name in (
        "effect_proofs",
        "stage_a",
        "bytecode",
        "audit_canary",
        "stage_b_os",
        "stage_b_raw",
        "manifest_pre",
        "manifest_post",
        "sourceless",
        "import_inventory",
        "stage_c",
        "payload",
        "failure",
    ):
        paths.setdefault(name, os.fspath(run_dir / f"{name}.json"))
    paths["payload"] = os.fspath(run_dir / "payload.json")
    paths["failure"] = os.fspath(run_dir / "bootstrap_failure.json")
    paths["stage_c"] = os.fspath(run_dir / "stage_c.json")
    template["attestation_paths"] = paths
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

    # Frozen first-match precedence.
    if not spawned:
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
    if status == "NOT_STARTED":
        reason = f"spawn not confirmed: {spawn_error or 'no HELLO received'}"
        record = assemble_terminal_record(
            record_kind=config.record_kind,
            status=status,
            run_id=config.run_id,
            launch_attempt_id=config.launch_attempt_id,
            chain=config.chain,
            not_started_info={"prelaunch_sha256": prelaunch_sha256, "reason": reason},
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
        fault_class, detail = fault or ("other", "uncategorized infrastructure failure")
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
                    "payload_started": (run_dir / "payload_started.json").is_file(),
                },
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
