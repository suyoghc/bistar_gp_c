"""Stdlib-first B14-stack v5 child bootstrap.

This file is executable under ``-S -s -P -B -X pycache_prefix=...``.  It
imports no project module until the initial path has been replaced with the
four canonical frozen roots.
"""

from __future__ import annotations

import collections.abc
import ctypes
import copy
import hashlib
import importlib
import importlib.machinery
import importlib.util
import json
import math
import os
import re
import sys
import tempfile
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping

__all__ = [
    "classify_pyc_candidate",
    "classify_stage_b_deltas",
    "environment_delta",
    "main",
    "parse_raw_environ_block",
    "scan_pyc_candidates",
]

_SENTINEL = "m2cr-hash-sentinel"
_BOUND_SENTINEL_HASH = _SENTINEL.__hash__
_KMP_NAME_PREFIX = "__KMP_REGISTERED_LIB_"
_KMP_VALUE_RE = re.compile(r"^0x[0-9a-fA-F]+-[cC][aA][fF][eE][0-9a-fA-F]{4}-.+$")
_CF_VALUE_RE = re.compile(r"^0x[0-9a-fA-F]+:0x[0-9a-fA-F]+:0x[0-9a-fA-F]+$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_MANIFEST_ROOT_IDS = ("worktree", "stdlib", "lib-dynload", "site-packages")
_MANIFEST_ENTRY_FIELDS = {"root", "relpath", "artifact_type", "sha256", "size"}
_ARTIFACT_TYPES = {
    "source",
    "extension",
    "orphan_bytecode",
    "legacy_bytecode",
    "importable_archive",
}
# Payload-boundary/serialization stdlib dependencies must already be loaded
# before the child replaces sys.path with a hermetic four-root test fixture.
_PRELOADED_STDLIB = (collections.abc, copy, math)


def _canonical_bytes(obj: Any) -> bytes:
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _atomic_write_json(path: str | os.PathLike[str], obj: Any) -> str:
    target = os.path.realpath(os.fspath(path))
    directory = os.path.dirname(target) or "."
    os.makedirs(directory, exist_ok=True)
    data = _canonical_bytes(obj)
    fd, temporary = tempfile.mkstemp(prefix=".m2cr-tmp-", dir=directory)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.rename(temporary, target)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise
    directory_fd = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: str | os.PathLike[str]) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(1 << 20)
            if not chunk:
                return digest.hexdigest()
            digest.update(chunk)


class _ControlWriter:
    def __init__(self, event_fd: int) -> None:
        self._handle = os.fdopen(event_fd, "w", encoding="utf-8", buffering=1)
        self._seq = 0

    def emit(self, event: str, **fields: Any) -> None:
        payload = {"seq": self._seq, "event": event}
        payload.update(fields)
        self._handle.write(_canonical_bytes(payload).decode("utf-8") + "\n")
        self._handle.flush()
        self._seq += 1

    def close(self) -> None:
        self._handle.close()


class PayloadContext:
    """Hermetic payload context exposing only the durable event emitter."""

    def __init__(self, writer: _ControlWriter) -> None:
        self._writer = writer

    def emit(self, event: str, **fields: Any) -> None:
        self._writer.emit(event, **fields)


def parse_raw_environ_block(
    raw: bytes | bytearray | list[bytes | str] | tuple[bytes | str, ...],
) -> dict[str, str]:
    """Parse a raw C environment view and reject duplicate keys."""

    entries: list[bytes | str]
    if isinstance(raw, (bytes, bytearray)):
        entries = [entry for entry in bytes(raw).split(b"\0") if entry]
    else:
        entries = list(raw)
    result: dict[str, str] = {}
    for raw_entry in entries:
        if isinstance(raw_entry, bytes):
            entry = raw_entry.decode("utf-8", errors="surrogateescape")
        elif isinstance(raw_entry, str):
            entry = raw_entry
        else:
            raise ValueError("raw environment entries must be bytes or strings")
        if "=" not in entry:
            raise ValueError(f"raw environment entry has no equals sign: {entry!r}")
        key, value = entry.split("=", 1)
        if not key:
            raise ValueError("raw environment key is empty")
        if key in result:
            raise ValueError(f"duplicate raw environment key: {key}")
        result[key] = value
    return result


def _raw_environ() -> dict[str, str]:
    if sys.platform != "darwin":
        return dict(os.environ)
    libc = ctypes.CDLL(None)
    getter = libc._NSGetEnviron
    getter.restype = ctypes.POINTER(ctypes.POINTER(ctypes.c_char_p))
    environment = getter()[0]
    entries: list[bytes] = []
    index = 0
    while environment[index]:
        entries.append(environment[index])
        index += 1
    return parse_raw_environ_block(entries)


def environment_delta(
    before: dict[str, str], after: dict[str, str]
) -> dict[str, dict[str, Any]]:
    """Return added, removed, and changed entries between environment views."""

    return {
        "added": {key: after[key] for key in sorted(after.keys() - before.keys())},
        "removed": {key: before[key] for key in sorted(before.keys() - after.keys())},
        "changed": {
            key: {"before": before[key], "after": after[key]}
            for key in sorted(before.keys() & after.keys())
            if before[key] != after[key]
        },
    }


def _delta_is_empty(delta: dict[str, dict[str, Any]]) -> bool:
    return not any(delta[part] for part in ("added", "removed", "changed"))


def classify_stage_b_deltas(
    stage_a_os: dict[str, str],
    stage_a_raw: dict[str, str],
    stage_b_os: dict[str, str],
    stage_b_raw: dict[str, str],
    *,
    pid: int,
    native_stack_modules: list[str] | tuple[str, ...],
    stage_b_expected: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Accept only the config-frozen CF value and PID-bound KMP addition."""

    os_delta = environment_delta(stage_a_os, stage_b_os)
    raw_delta = environment_delta(stage_a_raw, stage_b_raw)
    if not native_stack_modules:
        if not _delta_is_empty(os_delta) or not _delta_is_empty(raw_delta):
            raise ValueError("empty native stack must produce zero environment deltas")
        return {"os_delta": os_delta, "raw_delta": raw_delta, "accepted": []}
    if not _delta_is_empty(os_delta):
        raise ValueError("native initialization changed os.environ")
    if raw_delta["removed"] or raw_delta["changed"]:
        raise ValueError(
            "native initialization removed or changed raw environment entries"
        )

    additions = dict(raw_delta["added"])
    accepted: list[str] = []
    expected = {} if stage_b_expected is None else dict(stage_b_expected)
    if set(expected) - {"__CF_USER_TEXT_ENCODING"} or not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in expected.items()
    ):
        raise ValueError("stage_b_expected has unknown or non-string entries")
    expected_cf = expected.get("__CF_USER_TEXT_ENCODING")
    if expected_cf is not None and _CF_VALUE_RE.fullmatch(expected_cf) is None:
        raise ValueError("frozen __CF_USER_TEXT_ENCODING value has invalid shape")
    actual_cf = additions.pop("__CF_USER_TEXT_ENCODING", None)
    if expected_cf is None:
        if actual_cf is not None:
            raise ValueError("__CF_USER_TEXT_ENCODING was not frozen in config")
    else:
        if actual_cf is None:
            raise ValueError("native stack requires frozen __CF_USER_TEXT_ENCODING")
        if actual_cf != expected_cf:
            raise ValueError("__CF_USER_TEXT_ENCODING does not equal frozen value")
        accepted.append("__CF_USER_TEXT_ENCODING")
    kmp = [
        (key, value)
        for key, value in additions.items()
        if key.startswith(_KMP_NAME_PREFIX)
    ]
    if len(kmp) != 1:
        raise ValueError("native stack requires exactly one KMP registration entry")
    name, value = kmp[0]
    if name != f"{_KMP_NAME_PREFIX}{pid}":
        raise ValueError("KMP registration name is not bound to the child PID")
    if _KMP_VALUE_RE.fullmatch(value) is None:
        raise ValueError("KMP registration value does not match libomp format")
    additions.pop(name)
    accepted.append(name)
    if additions:
        raise ValueError(
            f"unapproved native environment additions: {sorted(additions)}"
        )
    return {"os_delta": os_delta, "raw_delta": raw_delta, "accepted": accepted}


def classify_pyc_candidate(path: str | os.PathLike[str]) -> str | None:
    """Classify a rejected legacy/orphan bytecode candidate, else ``None``."""

    candidate = Path(path)
    if candidate.suffix != ".pyc":
        return None
    if candidate.parent.name != "__pycache__":
        return "legacy_directly_importable"
    try:
        source = Path(importlib.util.source_from_cache(os.fspath(candidate)))
    except (ValueError, NotImplementedError):
        return "orphan"
    return None if source.is_file() else "orphan"


def scan_pyc_candidates(
    scan_roots: list[str] | tuple[str, ...],
) -> list[dict[str, str]]:
    rejected: list[dict[str, str]] = []
    for root in scan_roots:
        canonical_root = os.path.realpath(root)
        for directory, _, files in os.walk(canonical_root):
            for filename in files:
                if not filename.endswith(".pyc"):
                    continue
                path = os.path.join(directory, filename)
                reason = classify_pyc_candidate(path)
                if reason is not None:
                    rejected.append({"path": os.path.realpath(path), "reason": reason})
    return sorted(rejected, key=lambda item: item["path"])


def _canonical_four_roots(values: Any) -> list[str]:
    if not isinstance(values, list) or len(values) != 4:
        raise SystemExit(
            "attestation_fault: four_roots must contain exactly four paths"
        )
    roots: list[str] = []
    for value in values:
        if not isinstance(value, str) or not value or not os.path.isabs(value):
            raise SystemExit("attestation_fault: four_roots contains a relative path")
        canonical = os.path.realpath(value)
        if canonical != value:
            raise SystemExit(
                "attestation_fault: four_roots contains a non-canonical path"
            )
        roots.append(canonical)
    if len(set(roots)) != 4:
        raise SystemExit("attestation_fault: four_roots contains duplicates")
    return roots


def _manifest_roots(roots: list[str]) -> list[tuple[str, str]]:
    return list(zip(_MANIFEST_ROOT_IDS, roots, strict=True))


def _load_importable_artifact_manifest(
    path: str | os.PathLike[str],
) -> tuple[dict[tuple[str, str], dict[str, Any]], str]:
    """Read the frozen JSONL canonically and return its keyed entry set."""

    manifest_path = Path(path)
    try:
        raw = manifest_path.read_bytes()
    except OSError as exc:
        raise SystemExit(
            f"attestation_fault: importable artifact manifest unreadable: {exc}"
        ) from exc
    entries: dict[tuple[str, str], dict[str, Any]] = {}
    offset = 0
    for line_number, line in enumerate(raw.splitlines(keepends=True), start=1):
        offset += len(line)
        if not line.endswith(b"\n"):
            raise SystemExit(
                "attestation_fault: importable artifact manifest lacks final newline"
            )
        encoded = line[:-1]
        try:
            entry = json.loads(encoded.decode("utf-8", errors="strict"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SystemExit(
                f"attestation_fault: malformed importable manifest line {line_number}: {exc}"
            ) from exc
        if not isinstance(entry, dict) or set(entry) != _MANIFEST_ENTRY_FIELDS:
            raise SystemExit(
                f"attestation_fault: invalid importable manifest entry {line_number}"
            )
        if encoded != _canonical_bytes(entry):
            raise SystemExit(
                f"attestation_fault: noncanonical importable manifest line {line_number}"
            )
        root_id = entry.get("root")
        relpath = entry.get("relpath")
        if (
            root_id not in _MANIFEST_ROOT_IDS
            or not isinstance(relpath, str)
            or not relpath
        ):
            raise SystemExit(
                f"attestation_fault: invalid importable manifest key at line {line_number}"
            )
        if entry.get("artifact_type") not in _ARTIFACT_TYPES:
            raise SystemExit(
                f"attestation_fault: invalid artifact type at line {line_number}"
            )
        if _SHA256_RE.fullmatch(str(entry.get("sha256"))) is None:
            raise SystemExit(
                f"attestation_fault: invalid artifact digest at line {line_number}"
            )
        size = entry.get("size")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise SystemExit(
                f"attestation_fault: invalid artifact size at line {line_number}"
            )
        key = (root_id, relpath)
        if key in entries:
            raise SystemExit(
                f"attestation_fault: duplicate importable manifest entry {key}"
            )
        entries[key] = entry
    if offset != len(raw):
        raise SystemExit("attestation_fault: importable manifest framing failure")
    return entries, hashlib.sha256(raw).hexdigest()


def _verify_importable_artifact_manifest(
    roots: list[str],
    frozen_entries: Mapping[tuple[str, str], Mapping[str, Any]],
    *,
    phase: str,
) -> dict[str, Any]:
    """Re-walk all four roots and require exact frozen-entry identity."""

    # This project import is intentionally after the child's sys.path replacement.
    from bistar_gp.m2cr.environment_freeze import walk_importable_artifacts

    actual_entries = {
        (entry["root"], entry["relpath"]): entry
        for entry in walk_importable_artifacts(_manifest_roots(roots))
    }
    frozen_keys = set(frozen_entries)
    actual_keys = set(actual_entries)
    added = sorted(actual_keys - frozen_keys)
    removed = sorted(frozen_keys - actual_keys)
    changed = sorted(
        key
        for key in frozen_keys & actual_keys
        if dict(frozen_entries[key]) != actual_entries[key]
    )
    if added or removed or changed:
        raise SystemExit(
            "attestation_fault: importable artifact manifest drift "
            f"during {phase}; added={added}, removed={removed}, changed={changed}"
        )
    return {
        "phase": phase,
        "entry_count": len(actual_entries),
        "entry_sets_identical": True,
    }


def _install_project_namespace(worktree_root: str) -> None:
    """Expose the R2 modules without executing the scientific package initializer."""

    package_root = os.path.join(worktree_root, "bistar_gp")
    m2cr_root = os.path.join(package_root, "m2cr")
    if not os.path.isdir(m2cr_root):
        raise SystemExit("attestation_fault: worktree lacks bistar_gp/m2cr")
    package = ModuleType("bistar_gp")
    package.__path__ = [package_root]
    package.__package__ = "bistar_gp"
    package.__file__ = os.path.join(package_root, "__init__.py")
    sys.modules["bistar_gp"] = package
    subpackage = ModuleType("bistar_gp.m2cr")
    subpackage.__path__ = [m2cr_root]
    subpackage.__package__ = "bistar_gp.m2cr"
    subpackage.__file__ = os.path.join(m2cr_root, "__init__.py")
    sys.modules["bistar_gp.m2cr"] = subpackage


def _realized_frozen_environment(spec: Any) -> dict[str, str]:
    if not isinstance(spec, dict):
        raise SystemExit("attestation_fault: frozen_env must be an object")
    if set(spec).issubset({"fixed", "run_local_keys"}) and "fixed" in spec:
        fixed = spec.get("fixed")
        local = spec.get("run_local_keys", {})
        if not isinstance(fixed, dict):
            raise SystemExit("attestation_fault: frozen_env.fixed must be an object")
        result = dict(fixed)
        if isinstance(local, dict):
            result.update(local)
        elif isinstance(local, list):
            for key in local:
                if key not in os.environ:
                    raise SystemExit(f"attestation_fault: missing run-local key {key}")
                result[key] = os.environ[key]
        else:
            raise SystemExit(
                "attestation_fault: run_local_keys must be an object or list"
            )
    else:
        result = dict(spec)
    if not all(
        isinstance(key, str) and isinstance(value, str) for key, value in result.items()
    ):
        raise SystemExit(
            "attestation_fault: frozen environment keys and values must be strings"
        )
    return result


def _attestation_paths(config: dict[str, Any]) -> tuple[Path, dict[str, Path]]:
    raw = config.get("attestation_paths")
    if not isinstance(raw, dict):
        raise SystemExit("attestation_fault: attestation_paths must be an object")
    marker_value = raw.get("payload_started")
    if not isinstance(marker_value, str):
        raise SystemExit(
            "attestation_fault: payload_started attestation path is missing"
        )
    run_dir = Path(marker_value).resolve().parent
    defaults = {
        "effect_proofs": "effect_proofs.json",
        "stage_a": "stage_a.json",
        "bytecode": "bytecode_attestation.json",
        "audit_canary": "audit_canary.json",
        "stage_b_os": "stage_b_os.json",
        "stage_b_raw": "stage_b_raw.json",
        "manifest_pre": "importable_manifest_pre.json",
        "manifest_post": "importable_manifest_post.json",
        "sourceless": "sourceless_attestation.json",
        "import_inventory": "import_inventory.json",
        "stage_c": "stage_c.json",
        "payload": "payload.json",
        "failure": "bootstrap_failure.json",
        "payload_started": "payload_started.json",
    }
    paths: dict[str, Path] = {}
    for name, default in defaults.items():
        value = raw.get(name, os.fspath(run_dir / default))
        if not isinstance(value, str):
            raise SystemExit(f"attestation_fault: path {name} must be a string")
        paths[name] = Path(value).resolve()
    return run_dir, paths


def _effect_proofs(config: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "optimize": sys.flags.optimize == 0,
        "hash_randomization": sys.flags.hash_randomization == 0,
        "bound_hash": _BOUND_SENTINEL_HASH() == config.get("expected_sentinel_hash"),
        "safe_path": bool(sys.flags.safe_path),
        "no_user_site": sys.flags.no_user_site == 1,
        "dont_write_bytecode": sys.flags.dont_write_bytecode == 1,
        "no_site": sys.flags.no_site == 1,
        "isolated": sys.flags.isolated == 0,
        "ignore_environment": sys.flags.ignore_environment == 0,
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    if failed:
        raise SystemExit(f"attestation_fault: failed effect proofs {failed}")
    expected_prefix = config.get("expected_pycache_prefix")
    if not isinstance(expected_prefix, str):
        raise SystemExit("attestation_fault: expected_pycache_prefix is missing")
    canonical_prefix = os.path.realpath(expected_prefix)
    actual_prefix = os.path.realpath(sys.pycache_prefix or "")
    if sys.pycache_prefix is None or actual_prefix != canonical_prefix:
        raise SystemExit("attestation_fault: pycache_prefix mismatch")
    return {
        "checks": checks,
        "sentinel_hash": _BOUND_SENTINEL_HASH(),
        "utf8_mode": sys.flags.utf8_mode,
        "pycache_prefix": actual_prefix,
    }


def _resolve_payload(config: dict[str, Any]) -> tuple[Any, bool]:
    spec = config.get("payload")
    pass_context = False
    if isinstance(spec, dict):
        entry = spec.get("entry")
        pass_context = spec.get("pass_context", False)
        if not isinstance(pass_context, bool):
            raise SystemExit("attestation_fault: payload pass_context must be boolean")
    else:
        entry = spec
    if not isinstance(entry, str) or entry.count(":") != 1:
        raise SystemExit("attestation_fault: payload must be module:function")
    module_name, function_name = entry.split(":", 1)
    try:
        module = __import__(module_name, fromlist=["*"])
        function = getattr(module, function_name)
    except BaseException as exc:
        raise SystemExit(f"attestation_fault: payload import failed: {exc}") from exc
    if not callable(function):
        raise SystemExit("attestation_fault: payload entry is not callable")
    return function, pass_context


def _loader_name(module: ModuleType) -> str:
    loader = getattr(module, "__loader__", None)
    if loader is None:
        spec = getattr(module, "__spec__", None)
        loader = getattr(spec, "loader", None) if spec is not None else None
    if loader is None:
        return "none"
    return f"{type(loader).__module__}.{type(loader).__qualname__}"


def _inventory(
    import_events: list[tuple[str, Any]],
    *,
    roots: list[str] | None = None,
    manifest_entries: Mapping[tuple[str, str], Mapping[str, Any]] | None = None,
    modules: Mapping[str, ModuleType | None] | None = None,
) -> list[dict[str, Any]]:
    """Inventory every loaded module and optionally bind every file origin."""

    if (roots is None) != (manifest_entries is None):
        raise SystemExit(
            "attestation_fault: inventory manifest roots/entries are incomplete"
        )
    module_map = sys.modules if modules is None else modules
    audit_filenames: dict[str, str | None] = {}
    for name, filename in import_events:
        audit_filenames.setdefault(
            name, filename if isinstance(filename, str) else None
        )
    result: list[dict[str, Any]] = []
    for name, module in sorted(module_map.items()):
        if module is None:
            continue
        spec = getattr(module, "__spec__", None)
        spec_origin = getattr(spec, "origin", None) if spec is not None else None
        file_origin = getattr(module, "__file__", None)
        origin = spec_origin if isinstance(spec_origin, str) else file_origin
        if not isinstance(origin, str):
            origin = None
        if origin in {"built-in", "frozen"}:
            classification = origin
            resolved_origin = None
        elif origin is None:
            locations = (
                getattr(spec, "submodule_search_locations", None)
                if spec is not None
                else None
            )
            classification = "namespace" if locations is not None else "no_origin"
            resolved_origin = None
        else:
            resolved_origin = os.path.realpath(origin)
            classification = "file"

        item: dict[str, Any] = {
            "module": name,
            "audit_filename": audit_filenames.get(name),
            "origin": origin,
            "resolved_origin": resolved_origin,
            "loader_class": _loader_name(module),
            "classification": classification,
        }
        if manifest_entries is not None and resolved_origin is not None:
            matches: list[tuple[int, str, str, Mapping[str, Any]]] = []
            for root_id, root in _manifest_roots(roots or []):
                try:
                    common = os.path.commonpath((root, resolved_origin))
                except ValueError:
                    continue
                if common != root:
                    continue
                relpath = Path(resolved_origin).relative_to(root).as_posix()
                entry = manifest_entries.get((root_id, relpath))
                if entry is not None:
                    matches.append((len(root), root_id, relpath, entry))
            actual_sha256 = _sha256_file(resolved_origin)
            matching = [
                match for match in matches if match[3].get("sha256") == actual_sha256
            ]
            if not matching:
                raise SystemExit(
                    "attestation_fault: loaded module has unknown or changed origin "
                    f"{name} -> {resolved_origin}"
                )
            _, root_id, relpath, entry = max(matching, key=lambda match: match[0])
            item.update(
                classification="manifest_file",
                manifest_root=root_id,
                manifest_relpath=relpath,
                artifact_type=entry["artifact_type"],
                sha256=actual_sha256,
            )
        result.append(item)
    return result


def _write_node_records(run_dir: Path, result: dict[str, Any]) -> list[dict[str, Any]]:
    node_records = result.pop("node_records", [])
    if not isinstance(node_records, list):
        raise SystemExit("schema_invalid_payload: node_records must be a list")
    evidence: list[dict[str, Any]] = []
    if node_records:
        (run_dir / "nodes").mkdir(parents=True, exist_ok=True)
    for record in node_records:
        if not isinstance(record, dict) or not isinstance(
            record.get("node_index"), int
        ):
            raise SystemExit("schema_invalid_payload: malformed node record")
        node_index = record["node_index"]
        path = run_dir / "nodes" / f"node_{node_index:06d}.json"
        digest = _atomic_write_json(path, record)
        evidence.append({"node_index": node_index, "record_sha256": digest})
    return sorted(evidence, key=lambda item: item["node_index"])


def main(config_path: str | os.PathLike[str], event_fd: int) -> int:
    """Run one child launch.  Every failure raises an explicit ``SystemExit``."""

    writer = _ControlWriter(event_fd)
    writer.emit("HELLO", pid=os.getpid())
    with open(config_path, "r", encoding="utf-8") as handle:
        config = json.load(handle)
    if not isinstance(config, dict):
        raise SystemExit("attestation_fault: bootstrap config is malformed")

    proofs = _effect_proofs(config)
    roots = _canonical_four_roots(config.get("four_roots"))
    if roots[0] != os.path.realpath(config.get("worktree_root", "")):
        raise SystemExit("attestation_fault: worktree root is not four_roots[0]")
    if os.path.realpath(os.getcwd()) != roots[0]:
        raise SystemExit("attestation_fault: child CWD mismatch")
    sys.path[:] = roots
    if sys.path != roots:
        raise SystemExit("attestation_fault: sys.path replacement did not hold")
    _install_project_namespace(roots[0])

    manifest_entries: dict[tuple[str, str], dict[str, Any]] | None = None
    manifest_sha256: str | None = None
    manifest_path = config.get("importable_artifact_manifest")
    if manifest_path is not None:
        if not isinstance(manifest_path, str) or not os.path.isabs(manifest_path):
            raise SystemExit(
                "attestation_fault: importable_artifact_manifest must be an absolute path"
            )
        manifest_entries, manifest_sha256 = _load_importable_artifact_manifest(
            manifest_path
        )

    run_dir, paths = _attestation_paths(config)
    proof_digest = _atomic_write_json(paths["effect_proofs"], proofs)
    expected_environment = _realized_frozen_environment(config.get("frozen_env"))
    if "LC_CTYPE" in expected_environment:
        raise SystemExit(
            "attestation_fault: LC_CTYPE must be absent from the frozen environment"
        )
    stage_a_os = dict(os.environ)
    try:
        stage_a_raw = _raw_environ()
    except ValueError as exc:
        raise SystemExit(
            f"attestation_fault: duplicate raw environment: {exc}"
        ) from exc
    if stage_a_os != expected_environment or stage_a_raw != expected_environment:
        raise SystemExit("attestation_fault: Stage A environment mismatch")
    stage_a_digest = _atomic_write_json(
        paths["stage_a"],
        {
            "os_environ": stage_a_os,
            "raw_environ": stage_a_raw,
            "sys_path": list(sys.path),
            "cwd": os.path.realpath(os.getcwd()),
        },
    )

    prefix = Path(config["expected_pycache_prefix"])
    if any(prefix.iterdir()):
        raise SystemExit(
            "attestation_fault: pycache prefix was not empty before imports"
        )
    rejected = scan_pyc_candidates(roots)
    if rejected:
        raise SystemExit(f"attestation_fault: rejected bytecode candidates {rejected}")
    bytecode_digest = _atomic_write_json(
        paths["bytecode"], {"scan_roots": roots, "rejected": []}
    )

    manifest_pre_digest: str | None = None
    if manifest_entries is not None:
        manifest_pre = _verify_importable_artifact_manifest(
            roots, manifest_entries, phase="pre_audit"
        )
        manifest_pre.update(
            frozen_manifest_path=os.path.realpath(manifest_path),
            frozen_manifest_sha256=manifest_sha256,
        )
        manifest_pre_digest = _atomic_write_json(paths["manifest_pre"], manifest_pre)

    import_events: list[tuple[str, Any]] = []
    canary_token = f"m2cr-audit-{os.getpid()}"
    canary_seen = False

    def audit_hook(event: str, args: tuple[Any, ...]) -> None:
        nonlocal canary_seen
        if event == "import":
            module = args[0] if args else None
            filename = args[1] if len(args) > 1 else None
            if isinstance(module, str):
                import_events.append((module, filename))
        elif event == "m2cr.canary" and args and args[0] == canary_token:
            canary_seen = True

    try:
        sys.addaudithook(audit_hook)
        sys.audit("m2cr.canary", canary_token)
    except BaseException as exc:
        raise SystemExit(
            f"attestation_fault: audit hook installation failed: {exc}"
        ) from exc
    if not canary_seen:
        raise SystemExit("attestation_fault: audit canary was not observed")
    canary_digest = _atomic_write_json(
        paths["audit_canary"],
        {
            "observed": True,
            "token_sha256": hashlib.sha256(canary_token.encode()).hexdigest(),
        },
    )

    native_modules = config.get("native_stack_modules", [])
    if not isinstance(native_modules, list) or not all(
        isinstance(name, str) for name in native_modules
    ):
        raise SystemExit(
            "attestation_fault: native_stack_modules must be a string list"
        )
    loaded_native: dict[str, ModuleType] = {}
    for module_name in native_modules:
        try:
            loaded_native[module_name] = __import__(module_name, fromlist=["*"])
        except BaseException as exc:
            raise SystemExit(
                f"attestation_fault: native import {module_name} failed: {exc}"
            ) from exc
    if "torch" in loaded_native:
        try:
            loaded_native["torch"].set_num_threads(10)
            loaded_native["torch"].set_num_interop_threads(10)
        except BaseException as exc:
            raise SystemExit(
                f"attestation_fault: torch thread controls failed: {exc}"
            ) from exc

    from bistar_gp.m2cr.payload_boundary import (
        BoundaryViolation,
        PayloadBoundary,
        verify_marker,
    )

    stage_b_expected = config.get("stage_b_expected")
    if stage_b_expected is not None and not isinstance(stage_b_expected, dict):
        raise SystemExit("attestation_fault: stage_b_expected must be an object")
    stage_b_os = dict(os.environ)
    try:
        stage_b_raw = _raw_environ()
        delta_classification = classify_stage_b_deltas(
            stage_a_os,
            stage_a_raw,
            stage_b_os,
            stage_b_raw,
            pid=os.getpid(),
            native_stack_modules=native_modules,
            stage_b_expected=stage_b_expected,
        )
    except ValueError as exc:
        raise SystemExit(
            f"environment_fault: Stage B environment delta: {exc}"
        ) from exc
    stage_b_os_digest = _atomic_write_json(
        paths["stage_b_os"],
        {
            "view": "os.environ",
            "baseline": stage_b_os,
            "delta": delta_classification["os_delta"],
        },
    )
    stage_b_raw_digest = _atomic_write_json(
        paths["stage_b_raw"],
        {
            "view": "raw_environ",
            "baseline": stage_b_raw,
            "delta": delta_classification["raw_delta"],
        },
    )

    sourceless = []
    for name, module in sorted(sys.modules.items()):
        loader = getattr(module, "__loader__", None)
        if isinstance(loader, importlib.machinery.SourcelessFileLoader):
            sourceless.append(name)
    if sourceless:
        raise SystemExit(f"attestation_fault: sourceless modules loaded: {sourceless}")
    sourceless_digest = _atomic_write_json(
        paths["sourceless"], {"sourceless_modules": []}
    )

    boundary_config = config.get("boundary")
    if not isinstance(boundary_config, dict):
        raise SystemExit("attestation_fault: boundary config is missing")
    try:
        boundary = PayloadBoundary(
            run_dir,
            boundary_config["authorization_id"],
            boundary_config["launch_attempt_id"],
            boundary_config["execution_commit"],
            boundary_config["chain"],
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise SystemExit(
            f"attestation_fault: malformed boundary config: {exc}"
        ) from exc
    attestation_digests = {
        "effect_proofs": proof_digest,
        "path_and_stage_a": stage_a_digest,
        "bytecode_scan": bytecode_digest,
        "audit_canary": canary_digest,
        "stage_b_os": stage_b_os_digest,
        "stage_b_raw": stage_b_raw_digest,
        "sourceless_check": sourceless_digest,
    }
    if manifest_pre_digest is not None:
        attestation_digests["importable_manifest_pre"] = manifest_pre_digest
    boundary.register_required_attestations(*attestation_digests)
    for name, digest in attestation_digests.items():
        boundary.record_attestation(name, True, digest)
    try:
        marker_sha256 = boundary.mark()
    except BaseException as exc:
        raise SystemExit(
            f"attestation_fault: payload boundary mark failed: {exc}"
        ) from exc
    writer.emit("PAYLOAD_STARTED", marker_sha256=marker_sha256)

    def invoke_payload() -> Any:
        payload_callable, pass_context = _resolve_payload(config)
        context = PayloadContext(writer)
        return payload_callable(context) if pass_context else payload_callable()

    guarded = boundary.guard(invoke_payload)
    try:
        payload_result = guarded()
    except BoundaryViolation as exc:
        raise SystemExit(
            f"attestation_fault: payload marker verification: {exc}"
        ) from exc
    except BaseException as exc:
        raise SystemExit(f"payload_fault: {type(exc).__name__}: {exc}") from exc
    if not isinstance(payload_result, dict):
        raise SystemExit("schema_invalid_payload: payload return must be an object")
    payload_document = dict(payload_result)
    node_evidence = _write_node_records(run_dir, payload_document)
    if "node_evidence_digests" in payload_document:
        raise SystemExit(
            "schema_invalid_payload: payload may not supply node evidence digests"
        )
    payload_document["node_evidence_digests"] = node_evidence
    _atomic_write_json(paths["payload"], payload_document)

    manifest_post_digest: str | None = None
    if manifest_entries is not None:
        manifest_post = _verify_importable_artifact_manifest(
            roots, manifest_entries, phase="post_execution"
        )
        manifest_post.update(
            frozen_manifest_path=os.path.realpath(manifest_path),
            frozen_manifest_sha256=manifest_sha256,
        )
        manifest_post_digest = _atomic_write_json(paths["manifest_post"], manifest_post)

    inventory = _inventory(
        import_events,
        roots=roots if manifest_entries is not None else None,
        manifest_entries=manifest_entries,
    )
    inventory_digest = _atomic_write_json(paths["import_inventory"], inventory)

    try:
        verify_marker(
            paths["payload_started"],
            authorization_id=boundary.authorization_id,
            launch_attempt_id=boundary.launch_attempt_id,
            execution_commit=boundary.execution_commit,
            chain=boundary.chain,
            prelaunch_sha256=_sha256_file(run_dir / "prelaunch.json"),
            expected_sha256=marker_sha256,
        )
    except BoundaryViolation as exc:
        raise SystemExit(
            f"attestation_fault: Stage C payload marker verification failed: {exc}"
        ) from exc

    if list(sys.path) != roots:
        raise SystemExit("attestation_fault: sys.path drift at Stage C")
    if os.path.realpath(os.getcwd()) != roots[0]:
        raise SystemExit("attestation_fault: CWD drift at Stage C")
    _effect_proofs(config)
    post_pyc_rejected = scan_pyc_candidates(roots)
    if post_pyc_rejected:
        raise SystemExit(
            f"attestation_fault: Stage C rejected bytecode candidates {post_pyc_rejected}"
        )
    post_sourceless = [
        name
        for name, module in sorted(sys.modules.items())
        if isinstance(
            getattr(module, "__loader__", None),
            importlib.machinery.SourcelessFileLoader,
        )
    ]
    if post_sourceless:
        raise SystemExit(
            f"attestation_fault: Stage C sourceless modules loaded: {post_sourceless}"
        )
    stage_c_os = dict(os.environ)
    try:
        stage_c_raw = _raw_environ()
    except ValueError as exc:
        raise SystemExit(
            f"environment_fault: duplicate Stage C raw environment: {exc}"
        ) from exc
    if stage_c_os != stage_b_os or stage_c_raw != stage_b_raw:
        raise SystemExit("environment_fault: Stage C environment drift")
    if any(prefix.iterdir()):
        raise SystemExit("attestation_fault: pycache prefix was not empty at Stage C")
    _atomic_write_json(
        paths["stage_c"],
        {
            "os_environ_sha256": hashlib.sha256(
                _canonical_bytes(stage_c_os)
            ).hexdigest(),
            "raw_environ_sha256": hashlib.sha256(
                _canonical_bytes(stage_c_raw)
            ).hexdigest(),
            "sys_path": list(sys.path),
            "pycache_prefix_empty": True,
            "bytecode_candidates": [],
            "sourceless_modules": [],
            "payload_marker_sha256": marker_sha256,
            "import_inventory_sha256": inventory_digest,
            "importable_manifest_post_sha256": manifest_post_digest,
        },
    )
    status = payload_document.get("status")
    if status == "COMPLETED":
        writer.close()
        return 0
    if status == "ALGORITHM_STOP":
        writer.close()
        return 3
    raise SystemExit("schema_invalid_payload: payload status is not a protocol verdict")


def _persist_failure(config_path: str, reason: Any) -> None:
    text = str(reason) if reason is not None else "bootstrap exited"
    fault_class = text.split(":", 1)[0] if ":" in text else "other"
    try:
        with open(config_path, "r", encoding="utf-8") as handle:
            config = json.load(handle)
        _, paths = _attestation_paths(config)
        failure_path = paths["failure"]
    except BaseException:
        failure_path = Path(config_path).resolve().parent / "bootstrap_failure.json"
    try:
        _atomic_write_json(failure_path, {"fault_class": fault_class, "detail": text})
    except BaseException:
        return


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("attestation_fault: expected config path and event fd")
    try:
        event_fd = int(sys.argv[2])
    except ValueError as exc:
        raise SystemExit("attestation_fault: event fd is not an integer") from exc
    try:
        code = main(sys.argv[1], event_fd)
    except SystemExit as exc:
        if exc.code not in (0, 3):
            _persist_failure(sys.argv[1], exc.code)
        raise
    except BaseException as exc:
        _persist_failure(sys.argv[1], f"other: {type(exc).__name__}: {exc}")
        raise
    raise SystemExit(code)
