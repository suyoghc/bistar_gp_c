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

import hashlib
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
    canonical_sha256,
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
    "TerminalAlreadyExists",
    "TerminalDurabilityUncertain",
    "TerminalPublicationError",
    "TerminalWriteError",
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
    "origin_binding_pre",
    "sourceless",
    "import_inventory",
    "stage_c",
    "payload",
    "failure",
)
# The marker-bound attestation names every protocol exit must carry, mapped to
# the attestation-path key holding each one's evidence file (external-audit
# findings 1 and 2: the parent re-verifies the marker's evidence set at exit,
# so a protocol claim cannot ride a marker missing the mandatory pre-walk,
# origin-binding, or spec-binding attestations, and a payload cannot rewrite a
# marker-bound evidence file undetected).
_MANDATORY_MARKER_ATTESTATIONS = {
    "effect_proofs": "effect_proofs",
    "path_and_stage_a": "stage_a",
    "bytecode_scan": "bytecode",
    "audit_canary": "audit_canary",
    "stage_b_os": "stage_b_os",
    "stage_b_raw": "stage_b_raw",
    "native_stack": "native_stack",
    "sourceless_check": "sourceless",
    "importable_manifest_pre": "manifest_pre",
    "origin_binding_pre": "origin_binding_pre",
}
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
    "origin_binding_pre.json",
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
    """Run identity and routing ONLY (external-audit finding 2).

    Every static fact capable of affecting pre-boundary execution or
    certification — the frozen environment mapping, the interpreter path,
    resolved-target digest and flags, the bootstrap path, the four roots, the
    importable-artifact manifest, the pre-boundary attestation set, the
    attestation directives, and the dependency lock — is derived by
    :func:`_authenticate_launch_spec` from the committed artifact graph under
    ``worktree_root``, chain-bound.  The caller cannot author an expected
    security value: the former static fields are no longer representable on
    this config at all, so a directly-constructed ``LaunchConfig`` carries no
    authority beyond naming which worktree to launch from (where the chain's
    infrastructure digest fails closed on the wrong one), where to put the run,
    and the run's identity.

    ``wall_clock_ceiling_hours`` is a safety bound, not a security value: the
    caller may only shorten it; capture refuses any value above the ratified
    :data:`WALL_CLOCK_CEILING_HOURS`.  ``waiter`` is the established test-only
    grace-period hook.
    """

    worktree_root: str
    run_dir: str
    authorization_id: str
    launch_attempt_id: str
    run_id: str
    record_kind: str
    chain: dict[str, Any]
    wall_clock_ceiling_hours: float = WALL_CLOCK_CEILING_HOURS
    waiter: Callable[[subprocess.Popen[Any], float], Any] = field(
        default=_default_waiter, compare=False, repr=False
    )


@dataclass(frozen=True)
class AuthenticatedLaunchSpec:
    """The single static launch authority (external-audit finding 2).

    Only ever produced by :func:`_authenticate_launch_spec`, which derives and
    digest-authenticates every member from the committed Layer-0 artifact graph
    under the launch worktree, bound to the authorized chain.  It is not a
    freely constructible trust token: ``capture_run`` derives its own instance
    and never accepts one from the caller.  ``spec_sha256`` is the canonical
    digest of the complete static document; the bootstrap config embeds it
    (transport-bound through argv), ``prelaunch.json`` records it, and the
    child re-records it in the marker-bound ``effect_proofs.json`` attestation,
    so the parent and the child cannot consume different static authorities.
    """

    worktree_root: str
    frozen_env: Mapping[str, Any]
    interpreter_path: str
    interpreter_realpath: str
    interpreter_sha256: str
    interpreter_flags: tuple[str, ...]
    four_roots: Mapping[str, str]
    importable_manifest_path: str
    preboundary_attestation_set_path: str
    preboundary_closure: tuple[Mapping[str, Any], ...]
    attestation_directives: Mapping[str, Any]
    dependency_lock: Mapping[str, Any]
    site_packages: str
    environment_freeze_manifest_sha256: str
    infrastructure_manifest_sha256: str
    bootstrap_path: str
    evidence_ceilings: Mapping[str, int]
    spec_sha256: str


class RecordAssemblyError(ValueError):
    """A terminal branch or payload could not satisfy the frozen R1 schema."""


class TerminalPublicationError(Exception):
    """Terminal publication did not confirm a durable authoritative record.

    Base of the truthful publication-state hierarchy (external-audit finding 6).
    ``capture_run`` (and ``reconcile_run``) return a terminal record ONLY when
    that record is the authoritative no-clobber record and its required
    durability has been confirmed; every other publication outcome is a typed
    exception, so a returned record can never misrepresent an un-committed or
    not-durably-committed record as the terminal outcome.
    """


class TerminalWriteError(TerminalPublicationError):
    """Nothing was published: the temp creation, the payload write, the content
    fsync, or the hard-link (for a reason OTHER than an existing terminal)
    failed before the final terminal name existed on disk.

    ``attempted_record`` is the record that could not be committed and ``cause``
    the underlying error, so the caller sees a truthful non-outcome instead of a
    record misrepresented as committed.
    """

    def __init__(
        self, message: str, *, attempted_record: Mapping[str, Any], cause: BaseException
    ) -> None:
        super().__init__(message)
        self.attempted_record = dict(attempted_record)
        self.cause = cause


class TerminalDurabilityUncertain(TerminalPublicationError):
    """The record bytes are visible at the final terminal name (the atomic
    hard-link succeeded and the content was fsync'd) but the run-directory fsync
    failed, so crash-durability of the directory entry is unconfirmed.

    ``record`` is the authoritative on-disk record and ``digest`` its sha256;
    only durability is uncertain.  This is surfaced explicitly rather than
    reported as a confirmed-durable publication or silently swallowed.
    """

    def __init__(
        self,
        message: str,
        *,
        record: Mapping[str, Any],
        digest: str,
        cause: BaseException,
    ) -> None:
        super().__init__(message)
        self.record = dict(record)
        self.digest = digest
        self.cause = cause


class TerminalAlreadyExists(RecordAssemblyError):
    """The no-clobber publication lost to an existing terminal (EEXIST): a valid
    prior or racing writer's record is the authoritative one on disk.

    Kept a :class:`RecordAssemblyError` subclass so the established race-loser
    and reconciliation-refused handling and their ``already exists`` contract are
    preserved; distinct from the publication-FAILURE hierarchy above because an
    existing terminal is the no-clobber protocol working, not a failure.
    """


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


def _is_safe_relpath(relpath: str) -> bool:
    """A forward-slashed, non-absolute relpath with no traversal component."""

    if not relpath or relpath.startswith("/") or "\\" in relpath:
        return False
    return all(part not in ("", ".", "..") for part in relpath.split("/"))


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
    """Resolve the payload entry source the CHILD will execute (§4.5.10).

    The path is derived ONLY from the executed ``payload.entry`` (the module
    the child's ``_resolve_payload`` imports and runs), so the parent's
    prelaunch attestation and post-exit re-attestation hash exactly the file
    that runs.  An explicit ``payload_entry_path`` override is honoured only
    when it resolves to the SAME file as the derived entry — a disagreeing
    override (which would make the parent attest a different file than the
    child executes) is rejected (three-reviewer gate).
    """

    spec = template.get("payload")
    entry = spec.get("entry") if isinstance(spec, Mapping) else spec
    if not isinstance(entry, str) or entry.count(":") != 1:
        raise ValueError("bootstrap payload does not name module:function")
    module_name = entry.split(":", 1)[0]
    # Mirror CPython's FileFinder precedence: a PACKAGE (``foo/__init__.py``)
    # is selected before a same-named module (``foo.py``), so the parent must
    # attest the package when both are present, matching what the child's
    # ``__import__`` actually executes (three-reviewer gate delta CD3; §4.5.10).
    package_path = worktree_root / module_name.replace(".", "/") / "__init__.py"
    module_path = worktree_root / (module_name.replace(".", "/") + ".py")
    if package_path.is_file():
        derived = package_path.resolve()
    elif module_path.is_file():
        derived = module_path.resolve()
    else:
        raise ValueError(
            f"payload entry source was not found for {module_name}"
        )
    explicit = template.get("payload_entry_path")
    if isinstance(explicit, str):
        path = Path(explicit)
        resolved_explicit = (
            (worktree_root / path).resolve()
            if not path.is_absolute()
            else path.resolve()
        )
        if resolved_explicit != derived:
            raise ValueError(
                "payload_entry_path does not resolve to the executed payload "
                f"entry source: override {resolved_explicit}, executed {derived}"
            )
    return derived


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
    # Plan §3.1 excludes exactly the ROOT RAW_MANIFEST.sha256 and the ROOT
    # terminal record — not every nested file that happens to share the
    # basename (external audit round-2 F7). Exclusion is therefore by exact
    # relative path, so e.g. nodes/terminal_record.json stays covered.
    excluded = {RAW_MANIFEST_NAME, TERMINAL_RECORD_NAME}
    return sorted(
        (
            path
            for path in run_dir.rglob("*")
            if path.is_file()
            and path.relative_to(run_dir).as_posix() not in excluded
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


# v1.20 §2: the two stream_allowance layout members map to their dedicated
# ratified ceiling members; a future stream_allowance member without a
# dedicated ceiling must fail closed, never silently inherit one.
_STREAM_CEILING_MEMBERS = {
    "stdout.txt": ("stdout_bytes", "stdout"),
    "stderr.txt": ("stderr_bytes", "stderr"),
}
_PER_FILE_CEILING_MEMBER = "runtime_envelope_static_artifact_per_file_bytes"
_PER_FILE_CLASS_LABEL = "runtime-envelope/static-artifact per-file"


def _ceiling_value(ceilings: Mapping[str, Any], member: str) -> int:
    value = ceilings.get(member)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"evidence ceiling {member} is missing or malformed")
    return value


def _evidence_ceiling_breaches(
    run_dir: Path,
    candidate_record_bytes: int,
    ceilings: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Compute every v1.20 §4 ceiling breach for the CANDIDATE bundle.

    Sizes are exact on-disk byte counts (``st_size``); the candidate terminal
    record is priced at its exact canonical serialization length (the bytes
    the atomic publisher would write).  The per-file class map derives from
    ``classify_run_dir_layout(RUN_DIR_LAYOUT)`` at decision time, so an
    unclassified new layout member fails closed here before any size verdict.
    Residual, disclosed (Codex R2a review; same class as the Layer-3 hashes):
    the decision prices the evidence AFTER Layer 2 closes and the child has
    exited, so no capture-side writer runs afterward; growth between this
    decision and publication would require same-user external mutation,
    which the frozen threat model (v1.19 §5) places out of scope, and the
    content stays digest-bound by ``RAW_MANIFEST.sha256`` so any
    post-decision change is audit-detectable.
    The complete-bundle sum covers every regular file beneath the run
    directory (directories excluded; the root terminal-record path excluded
    from the on-disk sum in favor of the candidate's serialized bytes), so
    ``RAW_MANIFEST.sha256``, every ``nodes/`` and scratch file, and any
    unclassified stray file can never escape the aggregate.
    """

    from bistar_gp.m2cr.measure import classify_run_dir_layout

    classes = classify_run_dir_layout(RUN_DIR_LAYOUT)
    per_file_ceiling = _ceiling_value(ceilings, _PER_FILE_CEILING_MEMBER)
    breaches: list[dict[str, Any]] = []

    def breach(klass: str, path: str, observed: int, limit: int) -> None:
        breaches.append(
            {"class": klass, "path": path, "observed": observed, "ceiling": limit}
        )

    for name, (klass, _reason) in classes.items():
        if name.endswith("/") or name == TERMINAL_RECORD_NAME:
            # Directory members are governed by the bundle aggregate; the
            # terminal record is priced as the candidate below.
            continue
        path = run_dir / name
        if not path.is_file():
            continue
        observed = path.stat().st_size
        if klass in ("fixed_runtime", "conditional"):
            if observed > per_file_ceiling:
                breach(_PER_FILE_CLASS_LABEL, name, observed, per_file_ceiling)
        elif klass == "per_event_stream":
            limit = _ceiling_value(ceilings, "event_stream_bytes")
            if observed > limit:
                breach("event-stream", name, observed, limit)
        elif klass == "stream_allowance":
            mapped = _STREAM_CEILING_MEMBERS.get(name)
            if mapped is None:
                raise ValueError(
                    f"stream_allowance member {name!r} has no dedicated "
                    "ratified ceiling"
                )
            member, label = mapped
            limit = _ceiling_value(ceilings, member)
            if observed > limit:
                breach(label, name, observed, limit)
        else:
            raise ValueError(
                f"file-shaped layout member {name!r} has unpriceable evidence "
                f"class {klass!r}"
            )
    if candidate_record_bytes > per_file_ceiling:
        breach(
            _PER_FILE_CLASS_LABEL,
            f"{TERMINAL_RECORD_NAME} (candidate)",
            candidate_record_bytes,
            per_file_ceiling,
        )
    total = candidate_record_bytes
    for path in run_dir.rglob("*"):
        if not path.is_file():
            continue
        if path.relative_to(run_dir).as_posix() == TERMINAL_RECORD_NAME:
            continue
        total += path.stat().st_size
    bundle_ceiling = _ceiling_value(ceilings, "complete_bundle_bytes")
    if total > bundle_ceiling:
        breach("complete-bundle", "complete_bundle", total, bundle_ceiling)
    return breaches


def _overflow_detail(breaches: Sequence[Mapping[str, Any]], displaced: str) -> str:
    parts = [
        f"{item['class']} {item['path']}: observed {item['observed']} B "
        f"exceeds ceiling {item['ceiling']} B"
        for item in breaches
    ]
    return "evidence overflow: " + "; ".join(parts) + "; " + displaced


def _apply_evidence_ceilings(
    run_dir: Path, record: Mapping[str, Any], ceilings: Mapping[str, Any]
) -> dict[str, Any]:
    """The v1.20 §4 overflow decision over one CANDIDATE terminal record.

    Consumes the candidate's sizes exactly once and never reconsiders the
    outcome because the smaller replacement record would fit (the candidate
    rule); the replacement is not itself re-priced.  Ratified B2 precedence is
    unamended: rule-(1) NOT_STARTED and rule-(2) ABORTED_BUDGET candidates
    pass through unchanged; rule-(4) protocol candidates are replaced outright
    on breach; already-INFRA_FAILURE candidates keep their status with the
    fault class elevated to ``evidence_overflow`` and the displaced fault
    preserved in the detail.  This function never raises: an internal
    enforcement failure fails CLOSED for certifiable candidates (a
    capture_fault INFRA_FAILURE via the cannot-fail last-resort builder) and
    leaves an already-non-certifiable INFRA_FAILURE candidate unchanged.
    """

    candidate = dict(record)
    status = candidate.get("status")
    if status in ("NOT_STARTED", "ABORTED_BUDGET"):
        return candidate
    certifiable = status in ("COMPLETED", "ALGORITHM_STOP")
    payload_started = (run_dir / "payload_started.json").is_file()
    evidence = candidate.get("evidence")
    evidence = dict(evidence) if isinstance(evidence, Mapping) else {}

    def last_resort(detail: str, fault_class: str) -> dict[str, Any]:
        return _last_resort_terminal_record(
            record_kind=str(candidate.get("record_kind", "diagnostic")),
            run_id=str(candidate.get("run_id", "")),
            launch_attempt_id=str(candidate.get("launch_attempt_id", "")),
            chain=(
                candidate.get("chain")
                if isinstance(candidate.get("chain"), Mapping)
                else {}
            ),
            evidence=evidence,
            detail=detail,
            payload_started=payload_started,
            fault_class=fault_class,
        )

    try:
        candidate_bytes = len(canonical_bytes(candidate))
        breaches = _evidence_ceiling_breaches(run_dir, candidate_bytes, ceilings)
    except Exception as exc:
        if certifiable:
            return last_resort(
                "evidence-ceiling enforcement failed for candidate "
                f"{status}: {exc}",
                "capture_fault",
            )
        return candidate
    if not breaches:
        return candidate
    if certifiable:
        displaced = f"displaced candidate outcome: {status}"
    else:
        fault_obj = candidate.get("fault")
        fault_obj = dict(fault_obj) if isinstance(fault_obj, Mapping) else {}
        displaced = (
            "displaced candidate fault: "
            f"{fault_obj.get('fault_class', 'unknown')}: "
            f"{fault_obj.get('detail', '')}"
        )
    detail = _overflow_detail(breaches, displaced)
    fault_obj = candidate.get("fault")
    reconstructed = bool(
        fault_obj.get("reconstructed", False)
        if isinstance(fault_obj, Mapping)
        else False
    )
    try:
        # The replacement is deliberately MINIMAL (fault + the evidence digest
        # block the schema requires): the complete information — per-node
        # records, events, streams, payload — is retained on disk and covered
        # by RAW_MANIFEST.sha256, and a small replacement is structurally
        # bounded so it can never compound the overflow it reports (v1.20 §4,
        # no recursive size semantics).
        return assemble_terminal_record(
            record_kind=candidate["record_kind"],
            status="INFRA_FAILURE",
            run_id=candidate["run_id"],
            launch_attempt_id=candidate["launch_attempt_id"],
            chain=candidate["chain"],
            evidence=evidence,
            infra_fault={
                "fault_class": "evidence_overflow",
                "detail": detail,
                "reconstructed": reconstructed,
                "payload_started": payload_started,
            },
        )
    except Exception as exc:
        return last_resort(
            (detail + f"; replacement assembly failed: {exc}"),
            "evidence_overflow",
        )


def _prelaunch(
    config: LaunchConfig,
    spec: AuthenticatedLaunchSpec,
    bootstrap_path: Path,
    payload_path: Path,
    environment: Mapping[str, str],
) -> dict[str, Any]:
    """Prelaunch provenance: identity from the caller config, every static
    fact from the authenticated spec (finding 2), including the spec digest
    that the marker-bound child attestation must re-record."""

    return {
        "schema_version": 1,
        "created_utc": _utc_now(),
        "config": {
            "interpreter_path": spec.interpreter_realpath,
            "interpreter_flags": list(spec.interpreter_flags),
            "bootstrap_path": os.fspath(bootstrap_path),
            "worktree_root": os.fspath(Path(config.worktree_root).resolve()),
            "run_dir": os.fspath(Path(config.run_dir).resolve()),
            "authorization_id": config.authorization_id,
            "launch_attempt_id": config.launch_attempt_id,
            "run_id": config.run_id,
            "record_kind": config.record_kind,
            "wall_clock_ceiling_hours": config.wall_clock_ceiling_hours,
            "preboundary_attestation_set": spec.preboundary_attestation_set_path,
            "frozen_environment": dict(sorted(environment.items())),
            "chain": dict(config.chain),
            "authenticated_spec_sha256": spec.spec_sha256,
        },
        "bootstrap_sha256": sha256_file(bootstrap_path),
        "payload_entry_path": os.fspath(payload_path),
        "payload_entry_sha256": sha256_file(payload_path),
    }


def _write_terminal(run_dir: Path, record: Mapping[str, Any]) -> str:
    """Atomically publish the terminal record and return its digest ONLY on a
    confirmed-durable publication (Codex round-3 C4; round-4 durability; external
    -audit finding 6 truthful states).

    A fully-written, content-fsync'd temp with a per-call unique random-suffixed
    name (``O_EXCL``-opened with a fresh 64-bit suffix, retried on the improbable
    collision, so concurrent same-process publishers can never unlink or link
    each other's in-flight temp) is hard-linked to the final name — an atomic,
    no-replace publication that fails ``EEXIST`` if a terminal already exists, so
    neither normal capture nor reconciliation can overwrite the other's terminal
    (§4.3 "Nothing vanishes"; §3.1 write-temp / fsync / atomic publish).  The
    payload is written with a full-write loop (a POSIX short write must fail
    closed, never publish truncated bytes), and the run directory is fsync'd so
    the entry is durable.

    Outcomes are distinguished truthfully — a returned digest means the record is
    the durable authoritative record on disk; nothing else returns:

    - temp/write/content-fsync/link failure before the final name existed →
      :class:`TerminalWriteError` (nothing published), carrying the attempted
      record and cause;
    - an existing terminal (EEXIST) → :class:`TerminalAlreadyExists`;
    - link succeeded but the directory fsync failed → the bytes ARE visible but
      durability is unconfirmed → :class:`TerminalDurabilityUncertain`, carrying
      the on-disk record and digest.
    """

    final = run_dir / TERMINAL_RECORD_NAME
    payload = canonical_bytes(dict(record))
    digest = hashlib.sha256(payload).hexdigest()
    # Phase 1 — create, fully write, and content-fsync the temp.  Any failure
    # here leaves the final name untouched: nothing was published.  A
    # per-call-unique O_EXCL, umask-honoring open keeps concurrent publishers
    # from colliding and matches the historical open(0o644)-under-umask mode; a
    # collision with a crash-leftover temp is retried with a fresh suffix.
    tmp: str | None = None
    try:
        descriptor: int | None = None
        for attempt in range(3):
            candidate = os.fspath(
                run_dir / f".{TERMINAL_RECORD_NAME}.{os.urandom(8).hex()}.tmp"
            )
            try:
                descriptor = os.open(
                    candidate, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644
                )
                tmp = candidate
                break
            except FileExistsError:
                if attempt == 2:
                    raise
        assert descriptor is not None and tmp is not None
        try:
            written = 0
            while written < len(payload):
                count = os.write(descriptor, payload[written:])
                if count <= 0:
                    raise OSError(
                        f"terminal record short write at byte {written} of "
                        f"{len(payload)}"
                    )
                written += count
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    except OSError as exc:
        if tmp is not None:
            try:
                os.unlink(tmp)
            except OSError:
                pass
        raise TerminalWriteError(
            f"terminal record could not be written durably to a temp under "
            f"{run_dir}: {exc}",
            attempted_record=record,
            cause=exc,
        ) from exc
    # Phase 2 — atomic no-clobber publish (hard-link temp -> final name).
    try:
        os.link(tmp, final)
    except FileExistsError as exc:
        raise TerminalAlreadyExists(
            f"terminal record already exists at {final}"
        ) from exc
    except OSError as exc:
        raise TerminalWriteError(
            f"terminal record hard-link publication failed at {final}: {exc}",
            attempted_record=record,
            cause=exc,
        ) from exc
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass
    # Phase 3 — the bytes are now visible at the final name.  Fsync the run
    # directory so the entry is crash-durable; a failure here does NOT unpublish
    # the record, it only leaves durability unconfirmed — surfaced, not swallowed.
    try:
        dir_fd = os.open(run_dir, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except OSError as exc:
        raise TerminalDurabilityUncertain(
            f"terminal record is visible at {final} but its directory entry "
            f"could not be fsync'd: {exc}",
            record=record,
            digest=digest,
            cause=exc,
        ) from exc
    return digest


def _race_winner_or_raise(
    run_dir: Path, attempted_record: Mapping[str, Any]
) -> dict[str, Any]:
    """Resolve a no-clobber publication that lost to an existing terminal.

    The AUTHORITATIVE winner is a schema-valid terminal record for THIS run — a
    reconciliation of this run, or a racing capture of the same run — and only
    such a record is returned.  Any other occupant is a §4.5.13 squatter and is
    surfaced as a publication failure rather than returned as the outcome, so
    capture_run's return value is always a schema-valid terminal record (or a
    raised typed exception), never a non-record (finding-6 contract; Codex
    hardening round 2):

    - unreadable or noncanonical bytes → :class:`TerminalWriteError`;
    - canonical but schema-invalid, or a record for a DIFFERENT run →
      :class:`TerminalWriteError` (a canonical squatter is not an authoritative
      record);
    - a valid same-run winner whose directory entry cannot be confirmed durable
      from our vantage (a racing publisher may have linked it but not yet
      fsync'd the directory) → :class:`TerminalDurabilityUncertain`.

    The squatter/occupant is preserved on disk in every failing case, never
    clobbered.  Both capture publication sites share this one resolver.
    """

    final = run_dir / TERMINAL_RECORD_NAME
    try:
        occupant = _read_json_object(final)
    except (OSError, ValueError, RecursionError) as exc:
        raise TerminalWriteError(
            f"the terminal name at {final} is occupied by a non-authoritative "
            f"or unreadable file and this record could not be published: {exc}",
            attempted_record=attempted_record,
            cause=exc,
        ) from exc
    # A canonical JSON object is not necessarily a terminal record: require the
    # occupant to be schema-valid AND bound to this run before treating it as the
    # authoritative winner (else it is a squatter, returned to no one).
    try:
        validate_terminal_record(occupant)
    except RecordAssemblyError as exc:
        raise TerminalWriteError(
            f"the terminal name at {final} is occupied by a canonical but "
            f"schema-invalid file and this record could not be published: {exc}",
            attempted_record=attempted_record,
            cause=exc,
        ) from exc
    same_run = all(
        occupant.get(key) == attempted_record.get(key)
        for key in ("run_id", "launch_attempt_id")
    ) and dict(occupant.get("chain", {})) == dict(attempted_record.get("chain", {}))
    if not same_run:
        raise TerminalWriteError(
            f"the terminal name at {final} is occupied by a terminal record for "
            "a DIFFERENT run and this record could not be published",
            attempted_record=attempted_record,
            cause=ValueError("occupant run identity does not match this run"),
        )
    # The winner is authoritative; confirm its directory entry is durable from
    # our vantage before returning it — a racing publisher may have linked the
    # final name but not yet fsync'd the directory, so we fsync here so the
    # returned record is truthfully crash-durable (Codex hardening round 2).
    try:
        dir_fd = os.open(run_dir, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except OSError as exc:
        raise TerminalDurabilityUncertain(
            f"the authoritative race winner is visible at {final} but its "
            f"directory entry could not be confirmed durable: {exc}",
            record=occupant,
            digest=hashlib.sha256(canonical_bytes(occupant)).hexdigest(),
            cause=exc,
        ) from exc
    return occupant


def _reauthenticate_loaded_images_parent_side(
    expected: Sequence[Mapping[str, Any]],
) -> str | None:
    """Re-hash the committed expected loaded-image set parent-side after exit
    (external audit round-3 revision of F2; round-4 Codex delta review).  The
    parent (not the payload) re-verifies the on-disk native-library bytes
    against the DERIVED committed expectations — the in-memory bundle from
    ``_authenticate_launch_spec``, never the mutable run-dir config a
    payload could rewrite — so payload code can replace neither this check nor
    its input.  Returns a fault string on any mismatch/unreadable image, else
    ``None``.
    """

    for entry in expected:
        if (
            not isinstance(entry, Mapping)
            or not isinstance(entry.get("path"), str)
            or not isinstance(entry.get("sha256"), str)
        ):
            return "post-exit loaded-image re-attestation: malformed expectation"
        try:
            actual = sha256_file(entry["path"])
        except OSError as exc:
            return (
                "post-exit loaded-image re-attestation: "
                f"{entry['path']} unreadable: {exc}"
            )
        if actual != entry["sha256"]:
            return (
                "post-exit loaded-image re-attestation: "
                f"{entry['path']} sha256 changed during run"
            )
    return None


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


def _post_exit_authority_checks(
    run_dir: Path,
    paths: Mapping[str, str],
    spec: AuthenticatedLaunchSpec,
    stage_c_doc: Mapping[str, Any],
) -> str | None:
    """Parent-side post-exit verification that a protocol claim rode the
    complete mandatory attestation set and the SAME static authority the
    parent derived (external-audit findings 1 and 2).

    Returns a fault string (INFRA_FAILURE, attestation_fault) or ``None``:

    - the marker must carry every mandatory attestation name, and each named
      evidence file's on-disk bytes must still hash to the marker's recorded
      digest (a payload that rewrites marker-bound evidence is caught here);
    - ``effect_proofs.json`` must re-record the derived authenticated-spec
      digest, so the child demonstrably consumed the parent's static
      authority;
    - ``stage_c.json`` must bind the post-execution importable-manifest
      re-walk and the origin/loader inventory by digest, and both evidence
      files must exist with exactly those bytes (a missing or stripped
      postcheck fails closed).
    """

    try:
        marker = _read_json_object(run_dir / "payload_started.json")
    except (OSError, ValueError) as exc:
        return f"payload marker unreadable during authority checks: {exc}"
    entries = marker.get("attestation_evidence_digests")
    if not isinstance(entries, list):
        return "payload marker attestation evidence is malformed"
    digests: dict[str, str] = {}
    for item in entries:
        if (
            not isinstance(item, Mapping)
            or not isinstance(item.get("name"), str)
            or not isinstance(item.get("evidence_sha256"), str)
        ):
            return "payload marker attestation evidence entry is malformed"
        digests[item["name"]] = item["evidence_sha256"]
    missing = sorted(set(_MANDATORY_MARKER_ATTESTATIONS) - set(digests))
    if missing:
        return f"payload marker lacks mandatory attestation evidence: {missing}"
    for name, path_key in sorted(_MANDATORY_MARKER_ATTESTATIONS.items()):
        evidence_path = Path(paths[path_key])
        try:
            actual = sha256_file(evidence_path)
        except OSError as exc:
            return f"marker-bound attestation evidence {name} unreadable: {exc}"
        if actual != digests[name]:
            return (
                f"marker-bound attestation evidence {name} does not match its "
                "marker digest"
            )
    try:
        proofs = _read_json_object(Path(paths["effect_proofs"]))
    except (OSError, ValueError) as exc:
        return f"effect proofs unreadable during authority checks: {exc}"
    if proofs.get("authenticated_spec_sha256") != spec.spec_sha256:
        return (
            "child effect proofs did not re-record the derived "
            "authenticated-spec digest (parent and child static authorities "
            "disagree)"
        )
    post_path = Path(paths["manifest_post"])
    try:
        post_actual = sha256_file(post_path)
    except OSError as exc:
        return (
            f"post-execution importable-manifest attestation is missing: {exc}"
        )
    if stage_c_doc.get("importable_manifest_post_sha256") != post_actual:
        return (
            "stage C does not bind the post-execution importable-manifest "
            "attestation"
        )
    # Kimi K3 challenge, finding 9: bind the postcheck CONTENT to the
    # authenticated manifest identity, parent-side — the post-walk evidence
    # must claim completeness against exactly the spec's manifest bytes, so a
    # consistent rewrite of the post-marker pair still has to name the real
    # authenticated authority to pass.
    try:
        post_doc = _read_json_object(post_path)
    except (OSError, ValueError) as exc:
        return f"post-execution importable-manifest attestation malformed: {exc}"
    try:
        authenticated_manifest_sha = sha256_file(spec.importable_manifest_path)
    except OSError as exc:
        return f"authenticated importable manifest unreadable at exit: {exc}"
    if post_doc.get("frozen_manifest_sha256") != authenticated_manifest_sha:
        return (
            "post-execution re-walk does not attest the authenticated "
            "importable manifest"
        )
    if (
        post_doc.get("phase") != "post_execution"
        or post_doc.get("entry_sets_identical") is not True
    ):
        return "post-execution re-walk attestation is incomplete"
    inventory_path = Path(paths["import_inventory"])
    try:
        inventory_actual = sha256_file(inventory_path)
    except OSError as exc:
        return f"import-inventory attestation is missing: {exc}"
    if stage_c_doc.get("import_inventory_sha256") != inventory_actual:
        return "stage C does not bind the import-inventory attestation"
    return None


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
    """Plan §4.4: every attestation/output path resolves inside run_dir, none
    aliases the reserved payload-start marker, and no two collide.

    A caller-routable attestation path that resolves to
    ``payload_started.json`` would let the child create the consumption marker
    while writing an ordinary early attestation (e.g. effect proofs, before the
    manifest pre-walk and origin binding), forging authorization consumption
    with no scientific execution; a collision between two attestation paths
    would let one child write clobber another's evidence.  Both fail closed
    pre-spawn (three-reviewer gate).
    """

    marker = (run_dir / "payload_started.json").resolve()
    # macOS/APFS is case-INSENSITIVE (and os.path.normcase is a no-op on
    # darwin), so ``PAYLOAD_STARTED.json`` and ``payload_started.json`` are the
    # SAME on-disk file; case-fold the path keys so a case-variant alias cannot
    # forge the consumption marker (three-reviewer gate delta CD1).
    def _key(path: Path) -> str:
        return os.fspath(path).casefold()

    marker_key = _key(marker)
    seen: dict[str, str] = {}
    for name in sorted(paths):
        candidate = Path(paths[name]).resolve()
        try:
            candidate.relative_to(run_dir)
        except ValueError as exc:
            raise ValueError(
                f"attestation path {name!r} escapes the self-contained run "
                f"directory: {paths[name]}"
            ) from exc
        candidate_key = _key(candidate)
        if name != "payload_started" and candidate_key == marker_key:
            raise ValueError(
                f"attestation path {name!r} aliases the reserved payload-start "
                f"marker: {paths[name]}"
            )
        if candidate_key in seen:
            raise ValueError(
                f"attestation path {name!r} collides with {seen[candidate_key]!r}: "
                f"{paths[name]}"
            )
        seen[candidate_key] = name


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
    worktree_root: str | os.PathLike[str] | None = None,
) -> dict[str, int]:
    """Verify the §4.5.2 pre-boundary pins on disk, before any spawn.

    Worktree-origin closure entries (``root == "worktree"``) are verified by
    ``(relpath, sha256)`` against ``worktree_root`` — THIS launch's own fresh
    detached worktree — never the freeze-time absolute path (external audit
    round-3 F3), so a content-matching per-launch worktree passes and a
    content mismatch fails closed.  Host-global entries (interpreter, dyld
    family, stdlib/site-packages closure members) keep exact absolute-path
    verification.

    Every member class is always verified: there is no skip parameter and no
    partial mode (external-audit finding 2 removed the former
    ``{"interpreter", "dyld"}`` hermetic-test escape hatches; hermetic tests
    supply fixture-sized sets whose pins are genuine).  Any mismatch, missing
    digest, or unreadable pinned file raises ``ValueError`` with the exact
    reason, refusing the launch with no child spawned.
    """

    artifact = _read_json_object(Path(attestation_set_path).resolve(strict=True))
    worktree = (
        Path(worktree_root).resolve(strict=True)
        if worktree_root is not None
        else None
    )

    def check_entry(entry: Any, label: str) -> None:
        if not isinstance(entry, Mapping):
            raise ValueError(
                f"preboundary attestation entry {label} is malformed"
            )
        expected = entry.get("sha256")
        if not isinstance(expected, str) or _SHA256_RE.fullmatch(expected) is None:
            raise ValueError(
                f"preboundary attestation entry {label} lacks a frozen sha256"
            )
        if entry.get("root") == "worktree":
            relpath = entry.get("relpath")
            if not isinstance(relpath, str) or not _is_safe_relpath(relpath):
                raise ValueError(
                    f"preboundary attestation entry {label} has a missing or "
                    "unsafe worktree relpath"
                )
            if worktree is None:
                raise ValueError(
                    f"preboundary attestation entry {label} is worktree-relative "
                    "but no worktree_root was supplied"
                )
            # CP-3: a lexically safe relpath can still be a symlink whose target
            # resolves outside the launch worktree; resolve strictly and require
            # the physical path to remain beneath the worktree root before
            # hashing, so external bytes cannot satisfy a worktree pin.
            target = (worktree / relpath).resolve()
            try:
                target.relative_to(worktree)
            except ValueError as exc:
                raise ValueError(
                    f"preboundary attestation entry {label} worktree relpath "
                    f"{relpath} resolves outside the launch worktree"
                ) from exc
            display = f"worktree:{relpath}"
        elif isinstance(entry.get("path"), str):
            target = Path(entry["path"])
            display = entry["path"]
        else:
            raise ValueError(
                f"preboundary attestation entry {label} is malformed"
            )
        try:
            actual = sha256_file(target)
        except OSError as exc:
            raise ValueError(
                f"preboundary attestation entry {label} is unreadable: "
                f"{display}: {exc}"
            ) from exc
        if actual != expected:
            raise ValueError(
                f"preboundary attestation mismatch at {label}: "
                f"{display} expected {expected}, actual {actual}"
            )

    checked = {"interpreter": 0, "dyld": 0, "closure": 0}
    check_entry(artifact.get("interpreter_binary"), "interpreter_binary")
    checked["interpreter"] = 1
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
# The fabricated packages carry NO __file__, mirroring the bootstrap's own
# namespace installation: their initializers never execute pre-boundary, so
# they are not closure members (claiming them would be false provenance).
package = ModuleType("bistar_gp")
package.__path__ = [os.path.join(worktree, "bistar_gp")]
package.__package__ = "bistar_gp"
sys.modules["bistar_gp"] = package
subpackage = ModuleType("bistar_gp.m2cr")
subpackage.__path__ = [os.path.join(worktree, "bistar_gp", "m2cr")]
subpackage.__package__ = "bistar_gp.m2cr"
sys.modules["bistar_gp.m2cr"] = subpackage
module = importlib.import_module("bistar_gp.m2cr.bootstrap")
if os.path.realpath(getattr(module, "__file__", "")) != os.path.realpath(
    bootstrap_path
):
    raise SystemExit("closure probe imported an unexpected bootstrap origin")
# main() imports these project modules BEFORE installing the audit hook
# (scan_pyc_candidates -> environment_freeze -> serialization, from the
# pre-import bytecode scan, which precedes the sys.addaudithook call later in
# main()), so a faithful pre-boundary closure must include them (external
# audit round-2 F1). Import
# them here so sys.modules reflects the real pre-hook closure, not just the
# bootstrap module's own top-level imports.
importlib.import_module("bistar_gp.m2cr.environment_freeze")
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


_LAST_RESORT_FAULT_CLASSES = frozenset(
    {
        "capture_fault",
        "attestation_fault",
        "missing_postcheck",
        "evidence_overflow",
        "other",
    }
)


def _last_resort_terminal_record(
    *,
    record_kind: str,
    run_id: str,
    launch_attempt_id: str,
    chain: Mapping[str, Any],
    evidence: Mapping[str, Any],
    detail: str,
    payload_started: bool,
    fault_class: str = "other",
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
            # Guarded so this cannot-fail path never emits an out-of-enum class.
            "fault_class": (
                fault_class
                if fault_class in _LAST_RESORT_FAULT_CLASSES
                else "other"
            ),
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
    # The routing authorization id and the chain's own authorization id must be
    # the SAME grant: the marker names ``config.authorization_id`` while the
    # marker's and terminal record's chain carry ``chain.authorization_id``, so
    # a disagreement would consume one grant while certifying under another
    # (three-reviewer gate).
    if config.authorization_id != config.chain.get("authorization_id"):
        raise RecordAssemblyError(
            "config authorization_id does not match the chain's authorization_id"
        )
    _require_fresh_run_dir(run_dir)
    # Plan §4.3 / author decision F5: once the identity shapes are valid, any
    # pre-spawn infrastructure or attestation failure must still COMMIT an
    # INFRA_FAILURE terminal record + launch-attempt evidence rather than
    # escaping capture_run ("Nothing vanishes and no state is silently
    # reclassified").  A pre-spawn attestation mismatch is INFRA_FAILURE, not
    # NOT_STARTED; NOT_STARTED remains reserved for a spawn that was attempted
    # but never confirmed (precedence rule 1, resolved after the supervised
    # block below).
    pre_spawn_phase = "infrastructure"
    pipe = None
    stdout_handle: Any = None
    stderr_handle: Any = None
    spec: AuthenticatedLaunchSpec | None = None
    bootstrap_config_sha256: str | None = None
    try:
        worktree_root = Path(config.worktree_root).resolve(strict=True)
        # The B10 safety ceiling is a bound, not a caller-authored security
        # value: a caller may shorten it but never exceed the ratified ceiling.
        ceiling = config.wall_clock_ceiling_hours
        if (
            not isinstance(ceiling, (int, float))
            or isinstance(ceiling, bool)
            or not math.isfinite(float(ceiling))
            or float(ceiling) <= 0.0
            or float(ceiling) > WALL_CLOCK_CEILING_HOURS
        ):
            raise ValueError(
                "wall_clock_ceiling_hours must be finite, positive, and at "
                f"most the ratified {WALL_CLOCK_CEILING_HOURS} h ceiling"
            )
        # External-audit finding 2: EVERY static launch fact is derived from
        # the committed artifact graph under the launch worktree, chain-bound,
        # through the single authenticated-spec factory.  The caller config
        # carries no static authority; a missing/unbindable/mismatched
        # artifact fails closed here, before any run artifact exists.
        pre_spawn_phase = "attestation"
        spec = _authenticate_launch_spec(worktree_root, config.chain)
        pre_spawn_phase = "infrastructure"
        local = _prepare_run_directories(run_dir)
        environment, bootstrap_environment = _realize_environment(
            spec.frozen_env, run_dir, local
        )
        bootstrap_path = Path(spec.bootstrap_path).resolve(strict=True)
        bootstrap_config_path = run_dir / BOOTSTRAP_CONFIG_NAME
        template = _load_bootstrap_template(bootstrap_config_path)
        # Every spec-authored static directive is bound into the template with
        # caller substitution REJECTED (a conflicting template value refuses
        # the launch; a missing one is injected).  The caller template keeps
        # only payload selection and run routing.
        pre_spawn_phase = "attestation"
        _bind_attestation_directives(template, spec.attestation_directives)
        _bind_spec_static_directives(
            template,
            spec,
            bootstrap_environment=bootstrap_environment,
            pycache_prefix=local["PYCACHE_PREFIX"],
            worktree_root=worktree_root,
            config=config,
        )
        _require_complete_attestation_directives(template)
        # After the derive/bind/require attestation block, the remaining
        # pre-Popen work (payload-path resolution, template plumbing, run-dir
        # containment) is infrastructure setup again, so its failures keep the
        # ratified C2 classification (capture_fault, "pre-spawn infrastructure
        # failure") rather than inheriting the attestation phase.
        pre_spawn_phase = "infrastructure"
        payload_path = _payload_entry_path(template, worktree_root)
        template.pop("event_fd", None)
        paths = dict(template.get("attestation_paths", {}))
        paths.setdefault(
            "payload_started", os.fspath(run_dir / "payload_started.json")
        )
        for name in _ATTESTATION_NAMES:
            paths.setdefault(name, os.fspath(run_dir / f"{name}.json"))
        paths["payload"] = os.fspath(run_dir / "payload.json")
        paths["failure"] = os.fspath(run_dir / "bootstrap_failure.json")
        paths["stage_c"] = os.fspath(run_dir / "stage_c.json")
        template["attestation_paths"] = paths
        _require_contained_attestation_paths(run_dir, paths)
        # Plan §4.5.2: the pre-boundary set is REQUIRED before spawn — derived
        # from the authenticated graph, never caller-supplied, with no skip
        # mode; a digest mismatch refuses the launch with no child spawned.
        pre_spawn_phase = "attestation"
        verify_preboundary_attestation_set(
            spec.preboundary_attestation_set_path,
            worktree_root=worktree_root,
        )
        # F4 + Codex round-3 C1: recompute the stable semantic dependency-lock
        # fields from the live environment and compare to the DERIVED committed
        # lock — unconditionally, before launch; a third-party-stack drift
        # refuses it.
        lock_fault = _lock_semantic_fault(
            spec.dependency_lock, spec.interpreter_path, spec.site_packages
        )
        if lock_fault is not None:
            raise ValueError(lock_fault)
        # CP-4: prelaunch provenance and the event-pipe setup precede the spawn,
        # so a failure here (e.g. the bootstrap source vanishing during
        # _prelaunch, or the event pipe failing to start) must also commit an
        # INFRA_FAILURE record rather than escape capture_run.
        pre_spawn_phase = "prelaunch"
        prelaunch = _prelaunch(
            config, spec, bootstrap_path, payload_path, environment
        )
        prelaunch_sha256 = atomic_write_canonical_json(
            run_dir / "prelaunch.json", prelaunch
        )
        events_path = run_dir / "events.jsonl"
        pipe = parent_event_pipe(events_path)
        pipe.start()
        # Codex round-3 F5(C2): the bootstrap-config write and stdout/stderr
        # opens are pre-Popen infrastructure setup, so a failure here is a
        # pre-payload infrastructure fault (INFRA_FAILURE), never NOT_STARTED
        # (which is reserved for a spawn attempted at Popen but never
        # confirmed).  Codex round-3 F5(C3): the whole pre-spawn phase catches
        # ordinary Exception (e.g. a RuntimeError from pipe.start()) and commits
        # a terminal record.  (Finding 6 refinement: if committing that terminal
        # record itself cannot be published, the typed publication exception
        # propagates — a terminal record is always ASSEMBLED, but capture_run now
        # surfaces a publication failure truthfully rather than returning an
        # unpublished record.)
        pre_spawn_phase = "setup"
        # Round-4 (Codex delta review): the canonical digest of the exact
        # config bytes written here is handed to the child THROUGH ARGV — a
        # channel a mutation of the on-disk config cannot alter — so the child
        # verifies the bytes it reads against the parent's authenticated
        # derivation before consuming any field (transport binding of the
        # otherwise-mutable bootstrap_config.json handoff).
        bootstrap_config_sha256 = atomic_write_canonical_json(
            bootstrap_config_path, template
        )
        stdout_handle = open(run_dir / "stdout.txt", "wb")
        stderr_handle = open(run_dir / "stderr.txt", "wb")
    except Exception as exc:
        if pipe is not None:
            # Close the parent's write end first, or the pump thread blocks
            # reading and pipe.join() would hang (the write end is normally
            # closed in the supervised block after Popen).
            try:
                pipe.close_write_end_in_parent()
            except BaseException:
                pass
            try:
                pipe.join()
            except BaseException:
                pass
        for handle in (stdout_handle, stderr_handle):
            if handle is not None:
                try:
                    handle.close()
                except OSError:
                    pass
        fault_class = (
            "attestation_fault"
            if pre_spawn_phase == "attestation"
            else "capture_fault"
        )
        record = _last_resort_terminal_record(
            record_kind=config.record_kind,
            run_id=config.run_id,
            launch_attempt_id=config.launch_attempt_id,
            chain=config.chain,
            evidence={},
            detail=f"pre-spawn {pre_spawn_phase} failure: {exc}",
            payload_started=False,
            fault_class=fault_class,
        )
        try:
            # run_dir.mkdir is isolated so its OSError (nothing on disk yet)
            # is the only failure this handler wraps as a write failure; a
            # publication exception from _write_terminal below is never
            # misattributed to directory creation (GLM hardening finding).
            run_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise TerminalWriteError(
                f"pre-spawn terminal publication could not create {run_dir}: "
                f"{exc}",
                attempted_record=record,
                cause=exc,
            ) from exc
        # v1.20 §4 coverage: enforcement is operative from successful
        # launch-spec authentication onward; a failure BEFORE the spec exists
        # has no authenticated ceiling values and publishes as-is (already a
        # non-consuming INFRA_FAILURE).  The elevation path never raises.
        if spec is not None:
            record = _apply_evidence_ceilings(
                run_dir, record, spec.evidence_ceilings
            )
        try:
            _write_terminal(run_dir, record)
            return record
        except TerminalAlreadyExists:
            # A terminal already exists (a reconciliation won the publish race).
            # Return the authoritative durable winner, or — for an unreadable/
            # malformed §4.5.13 squatter — surface a TerminalWriteError rather
            # than returning a never-published record (finding-6 contract); the
            # squatter is preserved, never clobbered.
            return _race_winner_or_raise(run_dir, record)
        # External-audit finding 6: TerminalWriteError (nothing published) and
        # TerminalDurabilityUncertain (visible but durability unconfirmed) from
        # _write_terminal propagate — the pre-spawn INFRA_FAILURE outcome is
        # surfaced truthfully, never returned as a durably-committed record when
        # it is not one.

    # The bootstrap-config write and stdout/stderr opens are now done in the
    # pre-spawn phase above (Codex round-3 F5(C2)); the supervised block spawns
    # and waits.  A failure at Popen (not before it) is the only NOT_STARTED
    # path — an attempted-but-unconfirmed spawn.
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
            spec.interpreter_realpath,
            *_expanded_flags(spec.interpreter_flags, local["PYCACHE_PREFIX"]),
            os.fspath(bootstrap_path),
            os.fspath(bootstrap_config_path),
            str(pipe.write_fd),
            bootstrap_config_sha256,
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
            if handle is None:
                continue
            try:
                handle.flush()
                os.fsync(handle.fileno())
            except OSError as exc:
                if capture_fault is None:
                    capture_fault = f"{label} durability flush failed: {exc}"
            finally:
                handle.close()

    # A durability failure inside the event-pump thread must void
    # certification (external audit round-2 F4a); it is read after join().
    if pipe.pump_error is not None and capture_fault is None:
        capture_fault = f"event-stream pump failed: {pipe.pump_error}"

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
        # Round-4 (Codex delta review): repeat the bootstrap-config transport
        # binding at exit (§4.5.11 "repeat every pre-run static class"), so a
        # mutation of the mutable config file DURING the run — after the child
        # verified its argv-bound digest at startup — still voids
        # certification.
        if capture_fault is None and bootstrap_config_sha256 is not None:
            try:
                if sha256_file(bootstrap_config_path) != bootstrap_config_sha256:
                    capture_fault = (
                        "bootstrap config changed between write and post-exit "
                        "attestation"
                    )
            except OSError as exc:
                capture_fault = (
                    f"post-exit bootstrap-config re-attestation failed: {exc}"
                )
        # Plan §4.5.11: repeat every pre-run static class at exit, parent-side.
        # The pre-boundary set (interpreter, dyld family, and the FULL bootstrap
        # closure) is re-verified here — unconditionally, from the spec — so an
        # ordinary mutation to any of those during execution forces
        # INFRA_FAILURE rather than yielding COMPLETED (external audit F3).
        # The child re-walks the importable-artifact manifest at Stage C;
        # together they cover §4.5.11's classes.
        if capture_fault is None:
            try:
                verify_preboundary_attestation_set(
                    spec.preboundary_attestation_set_path,
                    worktree_root=worktree_root,
                )
            except ValueError as exc:
                capture_fault = f"post-exit pre-boundary re-attestation failed: {exc}"
        # F2 (round-3 revision) + round-4 (Codex delta review): re-hash the
        # committed expected loaded-image set parent-side after exit, against
        # the spec's DERIVED expectations — never a re-read of the mutable
        # run-dir config — so a native-library mutation during the run is
        # caught by the trusted parent (the payload can replace neither the
        # check nor its input).
        if capture_fault is None:
            fault = _reauthenticate_loaded_images_parent_side(
                list(spec.attestation_directives["expected_loaded_images"])
            )
            if fault is not None:
                capture_fault = fault
        # F4 (round-3 revision) + Codex C1: recompute + compare the stable
        # semantic dependency-lock fields parent-side after exit against the
        # spec's DERIVED committed lock (§4.5.11 "lock metadata").
        if capture_fault is None:
            fault = _lock_semantic_fault(
                spec.dependency_lock, spec.interpreter_path, spec.site_packages
            )
            if fault is not None:
                capture_fault = f"post-exit {fault}"

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
                        stage_c_doc = _read_json_object(stage_c_path)
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
                        # Findings 1+2: a protocol claim must ride the complete
                        # mandatory marker-bound attestation set, re-record the
                        # derived spec digest, and bind the post-execution
                        # re-walk + origin inventory — verified parent-side.
                        authority_fault = _post_exit_authority_checks(
                            run_dir, paths, spec, stage_c_doc
                        )
                        if authority_fault is not None:
                            status = "INFRA_FAILURE"
                            fault = ("attestation_fault", authority_fault)
                        elif not balance["balanced"]:
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
    # v1.20 §4: the frozen evidence-size ceilings are applied to the CANDIDATE
    # record after Layer 3, immediately before publication.  ``spec`` is
    # always authenticated on this path; the empty-mapping fallback exists so
    # an impossible None still fails CLOSED inside the decision (missing
    # ceiling values become a capture_fault INFRA_FAILURE for certifiable
    # candidates), never open.
    record = _apply_evidence_ceilings(
        run_dir, record, spec.evidence_ceilings if spec is not None else {}
    )
    try:
        _write_terminal(run_dir, record)
        return record
    except TerminalAlreadyExists:
        # Codex round-3 C4: a terminal already exists (a reconciliation of this
        # run won the publish race).  Nothing vanishes — the durable record is
        # the one already on disk; return that authoritative winner rather than
        # overwrite it.  For an unreadable/noncanonical §4.5.13 squatter, nothing
        # of ours was published, so a TerminalWriteError is surfaced instead of a
        # never-published record (finding-6 contract); the squatter is preserved.
        return _race_winner_or_raise(run_dir, record)
    # External-audit finding 6: TerminalWriteError (nothing published) and
    # TerminalDurabilityUncertain (visible but crash-durability unconfirmed)
    # PROPAGATE — capture_run raises a typed publication exception rather than
    # returning a record that misrepresents an uncommitted or not-durably-
    # committed outcome as the authoritative terminal.


run_capture = capture_run


def _config_value(config: LaunchConfig | Mapping[str, Any], name: str) -> Any:
    if isinstance(config, LaunchConfig):
        return getattr(config, name)
    return config[name]


def _reconciliation_ceilings(
    provenance: Mapping[str, Any],
) -> tuple[dict[str, int] | None, str | None]:
    """Authenticate the frozen evidence ceilings from CAPTURED provenance.

    Reconciliation has no live spec; v1.20 §4 derives the ceilings the same
    way the launch did — the committed infrastructure manifest under the
    captured worktree root, digest-bound to the captured chain, then the
    ``evidence_ceilings`` pin.  Returns ``(ceilings, None)`` on success and
    ``(None, reason)`` when the pinned artifact cannot be authenticated (for
    example the freeze-time worktree no longer exists): recovery is never
    blocked, and the reconstructed record discloses the unavailability.
    """

    try:
        worktree_value = provenance.get("worktree_root")
        if not isinstance(worktree_value, str) or not worktree_value:
            raise ValueError("prelaunch provenance lacks worktree_root")
        chain = provenance.get("chain")
        if not isinstance(chain, Mapping):
            raise ValueError("prelaunch provenance lacks a chain")
        worktree = Path(worktree_value)
        infra_path = worktree / _COMMITTED_INFRA_RELPATH
        if not infra_path.is_file():
            raise ValueError(
                f"infrastructure manifest absent under captured worktree: "
                f"{infra_path}"
            )
        expected_sha = chain.get("infrastructure_manifest_sha256")
        if (
            not isinstance(expected_sha, str)
            or _SHA256_RE.fullmatch(expected_sha) is None
            or sha256_file(infra_path) != expected_sha
        ):
            raise ValueError(
                "infrastructure manifest under the captured worktree does "
                "not match the captured chain binding"
            )
        infra = _read_json_object(infra_path)
        infra_artifacts = infra.get("artifacts")
        if not isinstance(infra_artifacts, Mapping):
            raise ValueError("infrastructure manifest lacks an artifacts section")
        ceilings_path = _authenticated_pin_under_worktree(
            infra_artifacts, "evidence_ceilings", worktree
        )
        from bistar_gp.m2cr.environment_freeze import parse_evidence_ceilings

        return parse_evidence_ceilings(_read_json_object(ceilings_path)), None
    except Exception as exc:
        return None, str(exc)


def reconcile_run(
    run_dir: str | os.PathLike[str],
    config: LaunchConfig | Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble a reconstructed INFRA_FAILURE after parent death.

    Identity (record kind, run id, launch-attempt id, chain) is derived from
    the CAPTURED ``prelaunch.json`` provenance, never from a fresh caller
    config (plan §4.3: "raw content was runtime-captured; only envelope
    assembly is late").  A caller config, if supplied, must MATCH that
    provenance; a disagreement refuses reconciliation rather than silently
    relabelling one run's raw evidence with another run's identity.
    Reconciliation is idempotent: it never overwrites an existing terminal
    record (§4.3 "Nothing vanishes and no state is silently reclassified").
    """

    root = Path(run_dir).resolve()
    prelaunch_path = root / "prelaunch.json"
    if not prelaunch_path.is_file():
        raise RecordAssemblyError("reconciliation requires prelaunch.json")
    if (root / TERMINAL_RECORD_NAME).is_file():
        raise RecordAssemblyError(
            "reconciliation refused: a terminal record already exists at "
            f"{root / TERMINAL_RECORD_NAME}"
        )
    prelaunch = _read_json_object(prelaunch_path)
    provenance = prelaunch.get("config")
    if not isinstance(provenance, Mapping):
        raise RecordAssemblyError(
            "prelaunch.json lacks a config provenance block; cannot bind a "
            "reconstructed envelope to the captured run"
        )
    try:
        record_kind = provenance["record_kind"]
        run_id = provenance["run_id"]
        launch_attempt_id = provenance["launch_attempt_id"]
        chain = provenance["chain"]
    except KeyError as exc:
        raise RecordAssemblyError(
            f"prelaunch.json provenance lacks identity member {exc}"
        ) from exc
    if not isinstance(chain, Mapping):
        raise RecordAssemblyError(
            "prelaunch.json provenance chain is malformed"
        )
    if config is not None:
        for name in ("record_kind", "run_id", "launch_attempt_id"):
            if _config_value(config, name) != provenance[name]:
                raise RecordAssemblyError(
                    f"reconcile config {name} disagrees with captured "
                    "prelaunch provenance"
                )
        if dict(_config_value(config, "chain")) != dict(chain):
            raise RecordAssemblyError(
                "reconcile config chain disagrees with captured prelaunch "
                "provenance"
            )
    balance = _event_balance(root / "events.jsonl")
    node_evidence = _node_evidence(root)
    raw_manifest_sha256 = write_raw_manifest(root)
    evidence = {
        "raw_manifest_sha256": raw_manifest_sha256,
        "node_evidence_digests": node_evidence,
        "event_stream_balanced": bool(balance["balanced"]),
    }
    # v1.20 §4 coverage: reconciliation applies the SAME overflow decision as
    # normal capture, with the ceilings authenticated from the captured
    # provenance; an unauthenticatable ceilings artifact never blocks recovery
    # and is disclosed in the reconstructed record's detail instead.
    ceilings, ceilings_unavailable = _reconciliation_ceilings(provenance)
    detail = "terminal envelope reconstructed after parent death"
    if ceilings is None:
        detail += (
            "; evidence-ceiling check unavailable: "
            f"{ceilings_unavailable or 'unknown reason'}"
        )
    record = assemble_terminal_record(
        record_kind=record_kind,
        status="INFRA_FAILURE",
        run_id=run_id,
        launch_attempt_id=launch_attempt_id,
        chain=dict(chain),
        evidence=evidence,
        infra_fault={
            "fault_class": "capture_fault",
            "detail": detail,
            "reconstructed": True,
            "payload_started": (root / "payload_started.json").is_file(),
        },
    )
    if ceilings is not None:
        record = _apply_evidence_ceilings(root, record, ceilings)
    # CP-5 + Codex round-3 C4: publish through the shared no-clobber, fsync'd,
    # atomic-link protocol so two racing reconcilers — OR reconciliation racing
    # normal capture — cannot overwrite each other's terminal record; the loser
    # fails closed on EEXIST (§4.3 "Nothing vanishes"; §3.1 write-temp / fsync /
    # atomic publish).  _write_terminal raises TerminalAlreadyExists (a
    # RecordAssemblyError) on a pre-existing terminal, which is the
    # reconciliation-refused signal; TerminalWriteError / TerminalDurabilityUncertain
    # propagate so a failed or durability-uncertain reconstruction is surfaced
    # truthfully rather than returned as a durably-committed record (finding 6).
    _write_terminal(root, record)
    return record


_FOUR_ROOT_IDS = ("worktree", "stdlib", "lib-dynload", "site-packages")


def _require_complete_attestation_directives(template: Mapping[str, Any]) -> None:
    """Fail closed unless the bootstrap template carries EVERY mandatory
    pre-scientific attestation directive, well-formed (Codex round-3 C1).

    All eight directives are validated unconditionally (no profile-hash gate):
    a non-empty allow-listed native stack, a lowercase profile-hash, the
    build-pinned bound sentinel __hash__ (finding 3), non-empty torch/numpy
    build-marker lists, a Stage-B object, a loaded-image allowlist, and a
    non-empty expected loaded-image set.  A missing, empty, or malformed
    directive raises ``ValueError`` so capture_run commits a pre-payload
    INFRA_FAILURE before the marker.
    """

    from bistar_gp.m2cr.bootstrap import disallowed_native_modules

    missing = [key for key in _MANDATORY_ATTESTATION_KEYS if key not in template]
    if missing:
        raise ValueError(
            f"bootstrap template lacks mandatory attestation directives: {missing}"
        )
    native = template["native_stack_modules"]
    if (
        not isinstance(native, list)
        or not native
        or not all(isinstance(name, str) for name in native)
    ):
        raise ValueError(
            "bootstrap template must declare a non-empty native_stack_modules list"
        )
    disallowed = disallowed_native_modules(native)
    if disallowed:
        raise ValueError(
            "bootstrap template native_stack_modules outside the frozen "
            f"allowlist: {disallowed}"
        )
    profile = template["expected_profile_integration_sha256"]
    if not isinstance(profile, str) or _SHA256_RE.fullmatch(profile) is None:
        raise ValueError(
            "bootstrap template must carry a lowercase "
            "expected_profile_integration_sha256"
        )
    sentinel = template["expected_sentinel_hash"]
    if not isinstance(sentinel, int) or isinstance(sentinel, bool):
        raise ValueError(
            "bootstrap template expected_sentinel_hash must be an integer"
        )
    for key in ("torch_build_expected", "numpy_build_expected"):
        value = template[key]
        if (
            not isinstance(value, list)
            or not value
            or not all(isinstance(item, str) and item for item in value)
        ):
            raise ValueError(
                f"bootstrap template {key} must be a non-empty string list"
            )
    if not isinstance(template["stage_b_expected"], Mapping):
        raise ValueError("bootstrap template stage_b_expected must be an object")
    if not isinstance(template["loaded_image_allowlist"], list):
        raise ValueError(
            "bootstrap template loaded_image_allowlist must be a list"
        )
    images = template["expected_loaded_images"]
    if not isinstance(images, list) or not images:
        raise ValueError(
            "bootstrap template expected_loaded_images must be a non-empty list"
        )


_MANDATORY_ATTESTATION_KEYS = (
    "native_stack_modules",
    "expected_profile_integration_sha256",
    "expected_sentinel_hash",
    "torch_build_expected",
    "numpy_build_expected",
    "stage_b_expected",
    "loaded_image_allowlist",
    "expected_loaded_images",
)


def _bind_attestation_directives(
    template: dict[str, Any], expectations: Mapping[str, Any]
) -> None:
    """Canonically DERIVE the mandatory pre-scientific attestation directives
    from the committed, infra-pinned native-stack expectations artifact and
    inject them into the template (external audit round-3 revision of F1).

    Every mandatory directive — the native import list, the frozen
    profile_integration hash, the torch/numpy backend build markers, the
    Stage-B environment delta, the loaded-image allowlist, and the F2 expected
    loaded-image set — comes from the committed artifact, not the caller.  A
    caller template that carries a CONFLICTING value for any mandatory directive
    is rejected (caller substitution); a missing directive is injected; the
    committed values are authoritative and cannot be caller-substituted before
    payload start.
    """

    for key in _MANDATORY_ATTESTATION_KEYS:
        if key not in expectations:
            raise ValueError(
                f"native-stack expectations artifact lacks mandatory {key}"
            )
        if key in template and template[key] != expectations[key]:
            raise ValueError(
                f"bootstrap template substitutes the committed {key}; the "
                "mandatory attestation directives are frozen and may not be "
                "caller-supplied"
            )
        template[key] = expectations[key]


def _bind_spec_static_directives(
    template: dict[str, Any],
    spec: AuthenticatedLaunchSpec,
    *,
    bootstrap_environment: Mapping[str, Any],
    pycache_prefix: str,
    worktree_root: Path,
    config: LaunchConfig,
) -> None:
    """Bind every remaining spec-derived static directive into the template,
    rejecting caller substitution (external-audit findings 1 and 2).

    The four roots (worktree slot = THIS launch's worktree), the
    importable-artifact manifest path, the pre-boundary closure, the frozen
    environment, the run-local pycache prefix, the worktree root, the boundary
    identity, and the authenticated-spec digest are all parent-derived.  A
    template that carries a CONFLICTING value for any of them is rejected —
    never silently preferred and never silently overwritten; a missing value
    is injected.
    """

    four_roots = [
        os.fspath(worktree_root.resolve()),
        spec.four_roots["stdlib"],
        spec.four_roots["lib-dynload"],
        spec.four_roots["site-packages"],
    ]
    frozen_env_value = dict(bootstrap_environment)
    bound: dict[str, Any] = {
        "four_roots": four_roots,
        "importable_artifact_manifest": spec.importable_manifest_path,
        "preboundary_closure": [dict(entry) for entry in spec.preboundary_closure],
        "authenticated_spec_sha256": spec.spec_sha256,
        "frozen_env": frozen_env_value,
        "expected_pycache_prefix": pycache_prefix,
        "worktree_root": os.fspath(worktree_root.resolve()),
        "boundary": {
            "authorization_id": config.authorization_id,
            "launch_attempt_id": config.launch_attempt_id,
            "execution_commit": config.chain.get("execution_commit"),
            "chain": dict(config.chain),
        },
    }
    # The legacy expected_frozen_env spelling is an alias for frozen_env; a
    # conflicting alias is a substitution attempt and is rejected the same way.
    alias = template.pop("expected_frozen_env", None)
    if alias is not None and alias != frozen_env_value:
        raise ValueError(
            "bootstrap template substitutes the derived frozen environment "
            "(expected_frozen_env); static launch facts may not be "
            "caller-supplied"
        )
    for key, value in bound.items():
        if key in template and template[key] != value:
            raise ValueError(
                f"bootstrap template substitutes the derived {key}; static "
                "launch facts may not be caller-supplied"
            )
        template[key] = value


_COMMITTED_INFRA_RELPATH = "docs/m2c_freeze/m2cr_infrastructure_manifest_v1.json"


def _authenticated_pin_under_worktree(
    infra_artifacts: Mapping[str, Any], name: str, worktree: Path
) -> Path:
    """Resolve one infrastructure-manifest artifact pin against the launch
    worktree and authenticate its sha256 (Codex round-3 C1, requirement 2)."""

    pin = infra_artifacts.get(name)
    if (
        not isinstance(pin, Mapping)
        or not isinstance(pin.get("path"), str)
        or not isinstance(pin.get("sha256"), str)
    ):
        raise ValueError(f"infrastructure manifest does not pin {name}")
    path = (worktree / pin["path"]).resolve()
    try:
        path.relative_to(worktree.resolve())
    except ValueError as exc:
        raise ValueError(
            f"pinned {name} resolves outside the launch worktree"
        ) from exc
    if not path.is_file():
        raise ValueError(f"pinned {name} not found under the worktree: {path}")
    if sha256_file(path) != pin["sha256"]:
        raise ValueError(
            f"pinned {name} sha256 does not match the infrastructure manifest"
        )
    return path


def _env_freeze_pin_under_worktree(
    freeze: Mapping[str, Any], name: str, worktree: Path
) -> Path:
    """Resolve one aggregating environment-freeze pin under the launch worktree
    and authenticate its sha256 (external-audit finding 2: the four static
    freeze artifacts are authenticated through the committed aggregating
    manifest, itself infra-pinned and chain-bound)."""

    artifacts = freeze.get("artifacts")
    if not isinstance(artifacts, Mapping):
        raise ValueError("environment freeze manifest lacks an artifacts section")
    pin = artifacts.get(name)
    if (
        not isinstance(pin, Mapping)
        or not isinstance(pin.get("path"), str)
        or not isinstance(pin.get("sha256"), str)
        or _SHA256_RE.fullmatch(pin["sha256"]) is None
    ):
        raise ValueError(f"environment freeze manifest does not pin {name}")
    if not _is_safe_relpath(pin["path"]):
        raise ValueError(
            f"environment freeze pin for {name} must be a safe repo-relative "
            "path"
        )
    path = (worktree / pin["path"]).resolve()
    try:
        path.relative_to(worktree.resolve())
    except ValueError as exc:
        raise ValueError(
            f"pinned {name} resolves outside the launch worktree"
        ) from exc
    if not path.is_file():
        raise ValueError(f"pinned {name} not found under the worktree: {path}")
    if sha256_file(path) != pin["sha256"]:
        raise ValueError(
            f"pinned {name} sha256 does not match the environment freeze "
            "manifest"
        )
    return path


def _authenticate_launch_spec(
    worktree_root: Path, chain: Mapping[str, Any]
) -> AuthenticatedLaunchSpec:
    """Authenticate the complete committed Layer-0 graph under the launch
    worktree, chain-bound, and derive the single static launch authority
    (external-audit finding 2).

    capture_run's trust root is the committed manifests inside the launch
    worktree, authenticated against ``chain`` — never a caller-supplied path,
    field, or an internally consistent caller-created bundle.  Raises
    ``ValueError`` on any missing, unbindable, or mismatched artifact so
    capture_run commits a pre-payload INFRA_FAILURE before the marker.
    """

    worktree = Path(worktree_root)
    infra_path = worktree / _COMMITTED_INFRA_RELPATH
    if not infra_path.is_file():
        raise ValueError(
            "committed infrastructure manifest not found under the launch "
            f"worktree: {infra_path}"
        )
    expected_infra_sha = chain.get("infrastructure_manifest_sha256")
    if (
        not isinstance(expected_infra_sha, str)
        or _SHA256_RE.fullmatch(expected_infra_sha) is None
    ):
        raise ValueError(
            "authorized chain lacks a valid infrastructure_manifest_sha256 "
            "binding"
        )
    if sha256_file(infra_path) != expected_infra_sha:
        raise ValueError(
            "infrastructure manifest under the worktree does not match the "
            "authorized chain binding"
        )
    infra = _read_json_object(infra_path)
    infra_artifacts = infra.get("artifacts")
    if not isinstance(infra_artifacts, Mapping):
        raise ValueError("infrastructure manifest lacks an artifacts section")

    # The aggregating environment-freeze manifest: infra-pinned under the
    # worktree AND required to equal the chain's own static binding, so the
    # B18-sub chain member and the artifact the launch actually consumes can
    # never disagree.
    env_freeze_path = _authenticated_pin_under_worktree(
        infra_artifacts, "environment_freeze_manifest", worktree
    )
    env_freeze_sha = sha256_file(env_freeze_path)
    if chain.get("environment_freeze_manifest_sha256") != env_freeze_sha:
        raise ValueError(
            "authorized chain environment_freeze_manifest_sha256 does not "
            "match the committed aggregating manifest under the worktree"
        )
    env_freeze = _read_json_object(env_freeze_path)

    # The four static freeze artifacts, each authenticated via the aggregating
    # manifest's pins.
    env_mapping_path = _env_freeze_pin_under_worktree(
        env_freeze, "child_env_mapping", worktree
    )
    interpreter_pin_path = _env_freeze_pin_under_worktree(
        env_freeze, "interpreter_pin", worktree
    )
    manifest_path = _env_freeze_pin_under_worktree(
        env_freeze, "importable_artifact_manifest", worktree
    )
    attestation_set_path = _env_freeze_pin_under_worktree(
        env_freeze, "preboundary_attestation_set", worktree
    )
    # The infrastructure manifest pins the importable manifest as well; both
    # authorities must name the same authenticated bytes.
    infra_manifest_path = _authenticated_pin_under_worktree(
        infra_artifacts, "importable_artifact_manifest", worktree
    )
    if infra_manifest_path != manifest_path:
        raise ValueError(
            "infrastructure and environment-freeze manifests pin different "
            "importable-artifact manifests"
        )
    expectations_path = _authenticated_pin_under_worktree(
        infra_artifacts, "native_stack_expectations", worktree
    )
    lock_path = _authenticated_pin_under_worktree(
        infra_artifacts, "dependency_lock", worktree
    )
    # v1.20 (R2a): the frozen evidence-size ceilings are a committed Layer-0
    # artifact, infra-pinned and authenticated here so the parent-side
    # overflow decision consumes only the one machine-readable authority.
    ceilings_path = _authenticated_pin_under_worktree(
        infra_artifacts, "evidence_ceilings", worktree
    )
    from bistar_gp.m2cr.environment_freeze import parse_evidence_ceilings

    evidence_ceilings = parse_evidence_ceilings(_read_json_object(ceilings_path))
    expectations = _read_json_object(expectations_path)
    dependency_lock = _read_json_object(lock_path)
    for key in _MANDATORY_ATTESTATION_KEYS:
        if key not in expectations:
            raise ValueError(
                f"native-stack expectations artifact lacks mandatory {key}"
            )

    # Frozen child environment mapping (plan §4.5.5 Stage A).
    mapping = _read_json_object(env_mapping_path)
    fixed = mapping.get("fixed")
    run_local_keys = mapping.get("run_local_keys")
    if (
        not isinstance(fixed, Mapping)
        or not fixed
        or not all(
            isinstance(key, str) and isinstance(value, str)
            for key, value in fixed.items()
        )
        or not isinstance(run_local_keys, list)
        or not all(isinstance(key, str) for key in run_local_keys)
    ):
        raise ValueError(
            "child environment mapping lacks well-formed fixed/run_local_keys "
            "members"
        )
    frozen_env: dict[str, Any] = {
        "fixed": dict(fixed),
        "run_local_keys": list(run_local_keys),
    }

    # Interpreter pin (plan §4.5.1): absolute path, and the resolved target's
    # sha256 re-verified on disk before any spawn.
    pin = _read_json_object(interpreter_pin_path)
    interpreter_path = pin.get("path")
    pinned_realpath = pin.get("realpath")
    pinned_sha = pin.get("sha256")
    if not isinstance(interpreter_path, str) or not os.path.isabs(
        interpreter_path
    ):
        raise ValueError("interpreter pin lacks an absolute interpreter path")
    if not isinstance(pinned_sha, str) or _SHA256_RE.fullmatch(pinned_sha) is None:
        raise ValueError("interpreter pin lacks a frozen sha256")
    actual_realpath = os.path.realpath(interpreter_path)
    if not isinstance(pinned_realpath, str) or actual_realpath != pinned_realpath:
        raise ValueError(
            "interpreter resolved path does not match the frozen interpreter "
            f"pin: pinned {pinned_realpath!r}, resolved {actual_realpath!r}"
        )
    try:
        actual_sha = sha256_file(actual_realpath)
    except OSError as exc:
        raise ValueError(
            f"pinned interpreter target is unreadable: {actual_realpath}: {exc}"
        ) from exc
    if actual_sha != pinned_sha:
        raise ValueError(
            "interpreter resolved-target sha256 does not match the frozen "
            "interpreter pin"
        )

    # Canonical four roots from the importable-manifest v2 header; the worktree
    # slot is per-launch by definition (plan §4.5.1 pins the CWD to the run's
    # own fresh detached worktree) while the three host-global roots derive
    # from the header.
    header_roots = _read_manifest_v2_header(manifest_path)
    four_roots = {
        **{name: os.path.realpath(header_roots[name]) for name in _FOUR_ROOT_IDS},
        "worktree": os.fspath(worktree.resolve()),
    }

    # Pre-boundary closure entries become a child directive so the child can
    # authenticate outside-root file-backed modules against the same committed
    # authority the parent verifies (finding 1's origin/loader rule).
    attestation_doc = _read_json_object(attestation_set_path)
    closure_raw = attestation_doc.get("bootstrap_closure")
    if not isinstance(closure_raw, list) or not closure_raw:
        raise ValueError(
            "preboundary attestation set lacks a non-empty bootstrap_closure"
        )
    closure: list[dict[str, Any]] = []
    for index, entry in enumerate(closure_raw):
        if (
            not isinstance(entry, Mapping)
            or not isinstance(entry.get("sha256"), str)
            or _SHA256_RE.fullmatch(entry["sha256"]) is None
        ):
            raise ValueError(
                f"preboundary bootstrap_closure[{index}] lacks a frozen sha256"
            )
        if entry.get("root") == "worktree":
            relpath = entry.get("relpath")
            if not isinstance(relpath, str) or not _is_safe_relpath(relpath):
                raise ValueError(
                    f"preboundary bootstrap_closure[{index}] has an unsafe "
                    "worktree relpath"
                )
            closure.append(
                {
                    "root": "worktree",
                    "relpath": relpath,
                    "sha256": entry["sha256"],
                }
            )
        elif isinstance(entry.get("path"), str) and os.path.isabs(entry["path"]):
            closure.append({"path": entry["path"], "sha256": entry["sha256"]})
        else:
            raise ValueError(
                f"preboundary bootstrap_closure[{index}] is malformed"
            )

    bootstrap_path = worktree / "bistar_gp/m2cr/bootstrap.py"
    if not bootstrap_path.is_file():
        raise ValueError(f"derived bootstrap is missing: {bootstrap_path}")

    document = {
        "worktree_root": os.fspath(worktree.resolve()),
        "frozen_env": frozen_env,
        "interpreter_path": interpreter_path,
        "interpreter_realpath": actual_realpath,
        "interpreter_sha256": pinned_sha,
        "interpreter_flags": list(FROZEN_INTERPRETER_FLAGS),
        "four_roots": four_roots,
        "importable_manifest_path": os.fspath(manifest_path),
        "preboundary_attestation_set_path": os.fspath(attestation_set_path),
        "preboundary_closure": closure,
        "attestation_directives": {
            key: expectations[key] for key in _MANDATORY_ATTESTATION_KEYS
        },
        "dependency_lock": dependency_lock,
        "site_packages": four_roots["site-packages"],
        "environment_freeze_manifest_sha256": env_freeze_sha,
        "infrastructure_manifest_sha256": expected_infra_sha,
        "bootstrap_path": os.fspath(bootstrap_path.resolve()),
        "evidence_ceilings": evidence_ceilings,
    }
    return AuthenticatedLaunchSpec(
        spec_sha256=canonical_sha256(document),
        worktree_root=document["worktree_root"],
        frozen_env=frozen_env,
        interpreter_path=interpreter_path,
        interpreter_realpath=actual_realpath,
        interpreter_sha256=pinned_sha,
        interpreter_flags=FROZEN_INTERPRETER_FLAGS,
        four_roots=four_roots,
        importable_manifest_path=document["importable_manifest_path"],
        preboundary_attestation_set_path=document[
            "preboundary_attestation_set_path"
        ],
        preboundary_closure=tuple(closure),
        attestation_directives=document["attestation_directives"],
        dependency_lock=dependency_lock,
        site_packages=document["site_packages"],
        environment_freeze_manifest_sha256=env_freeze_sha,
        infrastructure_manifest_sha256=expected_infra_sha,
        bootstrap_path=document["bootstrap_path"],
        evidence_ceilings=evidence_ceilings,
    )


def _lock_semantic_fault(
    committed_lock: Mapping[str, Any], interpreter_path: str, site_packages: str
) -> str | None:
    """Recompute + compare the stable semantic dependency-lock fields against
    the derived committed lock (Codex round-3 C1); a fault string or None."""

    from bistar_gp.m2cr.environment_freeze import verify_dependency_lock_semantics

    try:
        return verify_dependency_lock_semantics(
            committed_lock, interpreter_path, site_packages
        )
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        return f"dependency-lock recompute failed: {exc}"


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
    """Validate the committed launch authority early and return the slim
    identity/routing :class:`LaunchConfig` (external-audit finding 2).

    Every static launch fact is derived by ``capture_run`` itself through
    :func:`_authenticate_launch_spec` under the launch worktree; this factory
    no longer authors or forwards any of them.  It (i) runs the SAME
    authentication factory (fail-fast for callers, one derivation authority,
    no drift between two implementations), (ii) requires the caller's explicit
    freeze/infrastructure manifest paths to hold exactly the bytes the
    worktree-derived spec authenticated — a caller pointing at a different
    bundle than the launch worktree's committed one is refused, (iii) binds
    the chain's authorization id, and (iv) materializes the caller's
    payload-selection template as ``run_dir/bootstrap_config.json``.
    """

    freeze_path = Path(env_freeze_manifest_path).resolve(strict=True)
    infrastructure_path = Path(infrastructure_manifest_path).resolve(strict=True)
    if not isinstance(chain, Mapping):
        raise ValueError("chain must be a mapping")
    worktree = Path(worktree_root).resolve(strict=True)
    spec = _authenticate_launch_spec(worktree, chain)
    actual_freeze_sha = sha256_file(freeze_path)
    if actual_freeze_sha != spec.environment_freeze_manifest_sha256:
        raise ValueError(
            "environment freeze manifest does not match the worktree's "
            "committed authority: expected "
            f"{spec.environment_freeze_manifest_sha256}, actual "
            f"{actual_freeze_sha}"
        )
    actual_infra_sha = sha256_file(infrastructure_path)
    if actual_infra_sha != spec.infrastructure_manifest_sha256:
        raise ValueError(
            "infrastructure manifest does not match the worktree's committed "
            f"authority: expected {spec.infrastructure_manifest_sha256}, "
            f"actual {actual_infra_sha}"
        )
    if chain.get("authorization_id") != authorization_id:
        raise ValueError(
            "chain authorization_id does not match the requested "
            "authorization"
        )

    template = _load_bootstrap_template(
        Path(bootstrap_template_path).resolve(strict=True)
    )
    run_root = Path(run_dir).resolve()
    run_root.mkdir(parents=True, exist_ok=True)
    atomic_write_canonical_json(run_root / BOOTSTRAP_CONFIG_NAME, template)

    arguments: dict[str, Any] = {
        "worktree_root": os.fspath(worktree),
        "run_dir": os.fspath(run_root),
        "authorization_id": authorization_id,
        "launch_attempt_id": launch_attempt_id,
        "run_id": run_id,
        "record_kind": record_kind,
        "chain": dict(chain),
        "wall_clock_ceiling_hours": WALL_CLOCK_CEILING_HOURS,
    }
    if waiter is not None:
        arguments["waiter"] = waiter
    return LaunchConfig(**arguments)
