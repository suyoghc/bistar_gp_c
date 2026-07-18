"""Stdlib-first B14-stack v5 child bootstrap.

This file is executable under ``-S -s -P -B -X pycache_prefix=...``.  It
imports no project module until the initial path has been replaced with the
four canonical frozen roots.
"""

from __future__ import annotations

import argparse
import collections.abc
import contextlib
import ctypes
import copy
import hashlib
import importlib
import importlib.machinery
import importlib.util
import io
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from types import ModuleType
from typing import Any, Iterable, Mapping, Sequence

__all__ = [
    "classify_new_loaded_images",
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

# The frozen native stack (plan §4.5.6): the only modules the bootstrap may
# import BEFORE the payload-start marker. Restricting native_stack_modules to
# this allowlist keeps a malformed template from smuggling the payload or a
# scientific bistar_gp module into the pre-marker import path (external audit
# round-2 F3). No bistar_gp.* module is admissible here — the frozen R2
# modules are installed by _install_project_namespace, and any scientific
# module (model, fit, profile_integration, e1_potential, …) must execute only
# after the marker, through the payload boundary.
_ALLOWED_NATIVE_STACK = frozenset(
    {"torch", "numpy", "scipy", "gpytorch", "linear_operator"}
)
_MANIFEST_ENTRY_FIELDS = {"root", "relpath", "artifact_type", "sha256", "size"}
_ARTIFACT_TYPES = {
    "source",
    "extension",
    "orphan_bytecode",
    "legacy_bytecode",
    "importable_archive",
}
# Stdlib dependencies of the post-path-replacement project imports
# (payload_boundary, serialization, and the shared environment_freeze
# classifier) must already be loaded before the child replaces sys.path with
# a hermetic four-root test fixture.
_PRELOADED_STDLIB = (argparse, collections.abc, copy, math, subprocess)


def _canonical_bytes(obj: Any) -> bytes:
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _encode_nonfinite(value: Any) -> Any:
    """Recursively rewrite nonfinite floats as the frozen §5.4 sentinels.

    A local stdlib-only mirror of the serialization module's sentinel rule:
    the control writer must be usable before the child's ``sys.path`` has
    been replaced, so it cannot import the project serializer. Every control
    and event line passes through this encoder before
    ``json.dumps(allow_nan=False)``.
    """

    if isinstance(value, float):
        if math.isnan(value):
            return {"_nonfinite": "nan"}
        if math.isinf(value):
            return {"_nonfinite": "+inf"} if value > 0 else {"_nonfinite": "-inf"}
        return value
    if isinstance(value, dict):
        return {key: _encode_nonfinite(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_encode_nonfinite(item) for item in value]
    return value


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
        payload = _encode_nonfinite(payload)
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
    # Plan §4.5.5 Stage B is an ACCEPT-ONLY allowlist: it admits at most one
    # PID-bound, format-valid libomp registration entry — it does not mandate
    # its occurrence.  libomp performs the registration lazily (at its first
    # parallel region, which a hermetic no-computation child never reaches),
    # so the first real-native production-path launch (2026-07-18 real-root
    # integration battery) observed zero entries at Stage B on the frozen
    # host; requiring presence had over-read the frozen "accept only" text.
    # Two entries, a wrong-PID name, a malformed value, and any other addition
    # all still fail closed.
    if len(kmp) > 1:
        raise ValueError("native stack admits at most one KMP registration entry")
    if kmp:
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


def _shared_pyc_classifier() -> Any:
    """Resolve the single walker-shared bytecode classifier, fail-closed.

    Plan §4.5.3/§4.5.7 require the freeze-time walker and the launch-time
    scan to agree; both therefore delegate to exactly one classifier,
    ``environment_freeze.classify_pyc_candidate(root, relpath)`` (tolerant
    rule: a ``__pycache__/*.pyc`` is normal source-backed iff a sibling
    source exists for the stem obtained by stripping the trailing
    dot-separated cache-tag components; a stem with no dot keeps itself).
    The import is deliberately late: in the child it resolves only after
    ``sys.path`` was replaced with the four frozen roots.
    """

    from bistar_gp.m2cr import environment_freeze

    classifier = getattr(environment_freeze, "classify_pyc_candidate", None)
    if classifier is None:
        raise SystemExit(
            "attestation_fault: shared pyc classifier "
            "environment_freeze.classify_pyc_candidate is unavailable"
        )
    return classifier


def classify_pyc_candidate(path: str | os.PathLike[str]) -> str | None:
    """Classify a rejected legacy/orphan bytecode candidate, else ``None``.

    Thin API-stable wrapper: it derives ``(root, relpath)`` for one absolute
    candidate path and delegates to the shared walker classifier.
    """

    candidate = Path(path)
    if candidate.suffix != ".pyc":
        return None
    if candidate.parent.name == "__pycache__":
        root = candidate.parent.parent
        relpath = f"__pycache__/{candidate.name}"
    else:
        root = candidate.parent
        relpath = candidate.name
    return _shared_pyc_classifier()(root, relpath)


def scan_pyc_candidates(
    scan_roots: list[str] | tuple[str, ...],
) -> list[dict[str, str]]:
    """Scan the frozen roots, delegating every candidate to the shared rule."""

    rejected: list[dict[str, str]] = []
    classifier: Any = None
    for root in scan_roots:
        canonical_root = os.path.realpath(root)
        for directory, _, files in os.walk(canonical_root):
            for filename in files:
                if not filename.endswith(".pyc"):
                    continue
                path = os.path.join(directory, filename)
                if classifier is None:
                    classifier = _shared_pyc_classifier()
                relpath = os.path.relpath(path, canonical_root).replace(
                    os.sep, "/"
                )
                reason = classifier(canonical_root, relpath)
                if reason is not None:
                    rejected.append({"path": os.path.realpath(path), "reason": reason})
    return sorted(rejected, key=lambda item: item["path"])


def _dyld_loaded_images() -> list[str]:
    """Enumerate every dyld-loaded image path (plan §4.5.6/§4.5.11)."""

    if sys.platform != "darwin":
        return []
    libc = ctypes.CDLL(None)
    count_fn = libc._dyld_image_count
    count_fn.restype = ctypes.c_uint32
    name_fn = libc._dyld_get_image_name
    name_fn.restype = ctypes.c_char_p
    name_fn.argtypes = [ctypes.c_uint32]
    images: set[str] = set()
    for index in range(count_fn()):
        raw = name_fn(index)
        if raw:
            images.add(os.fsdecode(raw))
    return sorted(images)


# Injection point for hermetic tests; the child always uses the real one.
_image_enumerator = _dyld_loaded_images


def classify_new_loaded_images(
    baseline: list[str] | tuple[str, ...],
    current: list[str] | tuple[str, ...],
    allowlist: list[str] | tuple[str, ...],
) -> list[str]:
    """Return every newly loaded image that the frozen allowlist rejects."""

    return sorted(set(current) - set(baseline) - set(allowlist))


def hash_loaded_images(paths: Iterable[str]) -> dict[str, str]:
    """Sha256 every dyld-loaded image that is a regular file on disk.

    Plan §4.5.7 keeps "enumeration AND hashing" for native libraries loaded
    outside normal module imports; §4.5.11 re-attests them at exit.  Only
    on-disk regular files are hashed here — dyld-shared-cache pseudo-entries
    (framework paths that are not standalone files) are covered by the §4.5.2
    dyld-cache hash and are skipped.  In-memory-only native mutation is a
    disclosed out-of-scope residual (§4.5.14).
    """

    hashes: dict[str, str] = {}
    for path in paths:
        try:
            if os.path.isfile(path):
                hashes[path] = _sha256_file(path)
        except OSError:
            # A path that vanishes between enumeration and hashing is recorded
            # as unreadable so it surfaces as drift rather than being dropped.
            hashes[path] = "unreadable"
    return hashes


MANDATORY_ATTESTATION_KEYS = (
    "native_stack_modules",
    "expected_profile_integration_sha256",
    "expected_sentinel_hash",
    "torch_build_expected",
    "numpy_build_expected",
    "stage_b_expected",
    "loaded_image_allowlist",
    "expected_loaded_images",
)

# Closed-world bootstrap-config key set (Kimi K3 challenge, finding 5): the
# child consumes ONLY these top-level keys, and any other key — a legacy alias,
# a removed directive spelling, or a future directive the parent's substitution
# comparison does not yet cover — fails closed rather than passing through
# unexamined.  The parent-side template keys it does not read (payload entry
# routing) are enumerated too, because the parent materializes them into the
# same config document.
KNOWN_CONFIG_KEYS = frozenset(
    {
        "four_roots",
        "frozen_env",
        "expected_pycache_prefix",
        "worktree_root",
        "boundary",
        "payload",
        "payload_entry_path",
        "attestation_paths",
        "importable_artifact_manifest",
        "preboundary_closure",
        "authenticated_spec_sha256",
        *MANDATORY_ATTESTATION_KEYS,
    }
)


def require_mandatory_attestation_directives(config: Mapping[str, Any]) -> None:
    """Fail closed unless every mandatory pre-scientific attestation directive is
    present and well-formed before the marker (Codex round-3 C1, requirement 1).

    No directive defaults or is optional: ``native_stack_modules`` must be a
    non-empty allow-listed list, ``expected_profile_integration_sha256`` a
    lowercase sha256, the build-marker lists non-empty, ``stage_b_expected`` an
    object, ``loaded_image_allowlist`` a list, and ``expected_loaded_images`` a
    non-empty list.  A missing, empty, or malformed directive raises
    ``SystemExit`` before any native import.
    """

    missing = [key for key in MANDATORY_ATTESTATION_KEYS if key not in config]
    if missing:
        raise SystemExit(
            "attestation_fault: missing mandatory attestation directives: "
            f"{missing}"
        )
    native = config["native_stack_modules"]
    if (
        not isinstance(native, list)
        or not native
        or not all(isinstance(name, str) for name in native)
    ):
        raise SystemExit(
            "attestation_fault: native_stack_modules must be a non-empty "
            "string list"
        )
    profile = config["expected_profile_integration_sha256"]
    if not isinstance(profile, str) or _SHA256_RE.fullmatch(profile) is None:
        raise SystemExit(
            "attestation_fault: expected_profile_integration_sha256 must be a "
            "lowercase sha256"
        )
    sentinel = config["expected_sentinel_hash"]
    if not isinstance(sentinel, int) or isinstance(sentinel, bool):
        raise SystemExit(
            "attestation_fault: expected_sentinel_hash must be an integer "
            "(the build-pinned bound sentinel __hash__ value)"
        )
    for key in ("torch_build_expected", "numpy_build_expected"):
        value = config[key]
        if (
            not isinstance(value, list)
            or not value
            or not all(isinstance(item, str) and item for item in value)
        ):
            raise SystemExit(
                f"attestation_fault: {key} must be a non-empty string list"
            )
    if not isinstance(config["stage_b_expected"], dict):
        raise SystemExit(
            "attestation_fault: stage_b_expected must be an object"
        )
    if not isinstance(config["loaded_image_allowlist"], list):
        raise SystemExit(
            "attestation_fault: loaded_image_allowlist must be a list"
        )
    images = config["expected_loaded_images"]
    if not isinstance(images, list) or not images:
        raise SystemExit(
            "attestation_fault: expected_loaded_images must be a non-empty list"
        )


def _require_spec_binding_directives(config: Mapping[str, Any]) -> str:
    """Require the WI1/WI2 spec-derived static directives before any further
    consumption (external-audit findings 1 and 2).

    ``authenticated_spec_sha256`` (the parent's derived static-authority
    digest), ``importable_artifact_manifest`` (an absolute path), and
    ``preboundary_closure`` (a non-empty list of authenticated closure pins)
    are mandatory and unconditional: there is no launch mode without them.
    Returns the validated spec digest.
    """

    spec_digest = config.get("authenticated_spec_sha256")
    if (
        not isinstance(spec_digest, str)
        or _SHA256_RE.fullmatch(spec_digest) is None
    ):
        raise SystemExit(
            "attestation_fault: authenticated_spec_sha256 directive is "
            "missing or malformed"
        )
    manifest_path = config.get("importable_artifact_manifest")
    if not isinstance(manifest_path, str) or not os.path.isabs(manifest_path):
        raise SystemExit(
            "attestation_fault: importable_artifact_manifest directive is "
            "missing or is not an absolute path"
        )
    closure = config.get("preboundary_closure")
    if not isinstance(closure, list) or not closure:
        raise SystemExit(
            "attestation_fault: preboundary_closure directive is missing or "
            "empty"
        )
    return spec_digest


def _closure_authority(
    closure: list[Any], worktree_root: str
) -> dict[str, dict[str, str]]:
    """Resolve the authenticated pre-boundary closure into an origin authority.

    Worktree-relative entries resolve against THIS launch's worktree root;
    absolute entries keep their host-global path.  Returns a mapping from
    resolved real path to ``{"sha256": ..., "loader": ...}`` where the loader
    class is the frozen loader for the entry's artifact type (a ``.py`` member
    resolves through ``SourceFileLoader``, an extension through
    ``ExtensionFileLoader``); a closure member of any other artifact type is
    rejected — the pre-boundary closure is source and extension modules only.
    """

    authority: dict[str, dict[str, str]] = {}
    for index, entry in enumerate(closure):
        if (
            not isinstance(entry, dict)
            or not isinstance(entry.get("sha256"), str)
            or _SHA256_RE.fullmatch(entry["sha256"]) is None
        ):
            raise SystemExit(
                f"attestation_fault: preboundary_closure[{index}] lacks a "
                "frozen sha256"
            )
        if entry.get("root") == "worktree":
            relpath = entry.get("relpath")
            if (
                not isinstance(relpath, str)
                or not relpath
                or relpath.startswith("/")
                or any(part in ("", ".", "..") for part in relpath.split("/"))
            ):
                raise SystemExit(
                    f"attestation_fault: preboundary_closure[{index}] has an "
                    "unsafe worktree relpath"
                )
            target = os.path.realpath(os.path.join(worktree_root, relpath))
            if os.path.commonpath(
                (os.path.realpath(worktree_root), target)
            ) != os.path.realpath(worktree_root):
                raise SystemExit(
                    f"attestation_fault: preboundary_closure[{index}] "
                    "resolves outside the launch worktree"
                )
        elif isinstance(entry.get("path"), str) and os.path.isabs(entry["path"]):
            target = os.path.realpath(entry["path"])
        else:
            raise SystemExit(
                f"attestation_fault: preboundary_closure[{index}] is malformed"
            )
        if target.endswith(".py"):
            loader = "SourceFileLoader"
        elif any(
            target.endswith(suffix)
            for suffix in importlib.machinery.EXTENSION_SUFFIXES
        ):
            loader = "ExtensionFileLoader"
        else:
            raise SystemExit(
                f"attestation_fault: preboundary_closure[{index}] names a "
                "non-source, non-extension artifact"
            )
        authority[target] = {"sha256": entry["sha256"], "loader": loader}
    return authority


def authenticate_loaded_images(
    measured: Mapping[str, str],
    expected: Sequence[Mapping[str, str]],
) -> None:
    """Authenticate on-disk loaded native images against the committed expected
    set BEFORE payload start (external audit round-3 revision of F2).

    Baseline+exit self-comparison alone cannot catch same-path mutation that
    happened BEFORE launch, so every on-disk regular-file loaded image is
    checked against the frozen `(path, sha256)` expectation set: an image with
    no committed expectation, an expected image that did not load, or a sha256
    mismatch each fail closed.  The sha256 subsumes the Mach-O linkage identity
    (load commands are hashed bytes).
    """

    expected_map: dict[str, str] = {}
    for entry in expected:
        if (
            not isinstance(entry, Mapping)
            or not isinstance(entry.get("path"), str)
            or not isinstance(entry.get("sha256"), str)
        ):
            raise SystemExit(
                "attestation_fault: expected_loaded_images entry is malformed"
            )
        expected_map[entry["path"]] = entry["sha256"]
    measured_paths = set(measured)
    expected_paths = set(expected_map)
    unexpected = sorted(measured_paths - expected_paths)
    if unexpected:
        raise SystemExit(
            "attestation_fault: loaded native image has no committed "
            f"expectation: {unexpected}"
        )
    missing = sorted(expected_paths - measured_paths)
    if missing:
        raise SystemExit(
            "attestation_fault: a committed-expected native image did not "
            f"load: {missing}"
        )
    mismatched = sorted(
        path for path in measured_paths if measured[path] != expected_map[path]
    )
    if mismatched:
        raise SystemExit(
            "attestation_fault: loaded native image sha256 does not match its "
            f"committed expectation: {mismatched}"
        )


def loaded_image_hash_drift(
    stage_b_hashes: Mapping[str, str], stage_c_hashes: Mapping[str, str]
) -> list[str]:
    """Return every Stage-B image that is not byte-identical at Stage C.

    Drift includes an image whose bytes changed AND an image that is absent or
    no longer a readable regular file at Stage C (unlinked or replaced by a
    non-file during payload execution): its Stage-B hash has no matching Stage-C
    hash, so it must fail closed rather than be silently dropped (external audit
    checkpoint CP-2; §4.5.11 "any drift is INFRA_FAILURE").
    """

    return sorted(
        path
        for path, digest in stage_b_hashes.items()
        if stage_c_hashes.get(path) != digest
    )


def _loaded_image_allowlist(config: dict[str, Any]) -> list[str]:
    allowlist = config.get("loaded_image_allowlist", [])
    if not isinstance(allowlist, list) or not all(
        isinstance(item, str) for item in allowlist
    ):
        raise SystemExit(
            "attestation_fault: loaded_image_allowlist must be a string list"
        )
    return allowlist


def _torch_thread_readback(module: Any) -> dict[str, int]:
    """Read back both torch thread pools; fail closed unless both are 10."""

    try:
        intra = int(module.get_num_threads())
        interop = int(module.get_num_interop_threads())
    except BaseException as exc:
        raise SystemExit(
            f"attestation_fault: torch thread readback failed: {exc}"
        ) from exc
    if intra != 10 or interop != 10:
        raise SystemExit(
            "attestation_fault: torch thread readback mismatch: "
            f"intra={intra} interop={interop} (both must equal 10)"
        )
    return {"intra": intra, "interop": interop}


def _torch_build_description(module: Any) -> str:
    try:
        return str(module.__config__.show())
    except BaseException as exc:
        raise SystemExit(
            f"attestation_fault: torch build configuration unavailable: {exc}"
        ) from exc


def _numpy_build_description(module: Any) -> str:
    show = getattr(module, "show_config", None)
    if show is None:
        raise SystemExit(
            "attestation_fault: numpy build configuration unavailable"
        )
    buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(buffer):
            result = show()
    except BaseException as exc:
        raise SystemExit(
            f"attestation_fault: numpy build configuration unavailable: {exc}"
        ) from exc
    text = buffer.getvalue()
    if isinstance(result, str):
        text += result
    elif result is not None:
        text += repr(result)
    return text


def _require_build_markers(
    module_name: str, shown: str, config_key: str, expected: Any
) -> dict[str, Any]:
    """Require every config-frozen substring in the build description.

    An absent config key, an empty list, and a missing substring all fail
    closed (plan §4.5.6: a build or runtime backend change fails closed).
    """

    if (
        not isinstance(expected, list)
        or not expected
        or not all(isinstance(item, str) and item for item in expected)
    ):
        raise SystemExit(
            f"attestation_fault: {config_key} must be a frozen non-empty "
            "string list"
        )
    missing = sorted(item for item in expected if item not in shown)
    if missing:
        raise SystemExit(
            f"attestation_fault: {module_name} build markers missing {missing}"
        )
    return {"expected": list(expected), "all_present": True}


def _read_authenticated_json(
    path: Path, expected_sha256: str, label: str
) -> dict[str, Any]:
    """Re-read a persisted attestation, verifying its recorded digest first."""

    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise SystemExit(
            f"attestation_fault: persisted {label} baseline unreadable: {exc}"
        ) from exc
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise SystemExit(
            f"attestation_fault: persisted {label} baseline failed digest "
            "authentication"
        )
    document = json.loads(raw.decode("utf-8"))
    if not isinstance(document, dict):
        raise SystemExit(
            f"attestation_fault: persisted {label} baseline is not an object"
        )
    return document


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


def _manifest_header(candidate: Any) -> dict[str, Any] | None:
    """Return a validated format-v2 header object, or ``None`` for v1."""

    if not isinstance(candidate, dict) or "schema_version" not in candidate:
        return None
    if candidate.get("schema_version") != 2:
        raise SystemExit(
            "attestation_fault: unsupported importable manifest schema_version"
        )
    roots = candidate.get("roots")
    if (
        not isinstance(roots, dict)
        or not roots
        or not all(
            isinstance(root_id, str)
            and isinstance(path, str)
            and os.path.isabs(path)
            for root_id, path in roots.items()
        )
    ):
        raise SystemExit(
            "attestation_fault: importable manifest header roots must map "
            "ids to absolute paths"
        )
    return candidate


def _load_importable_artifact_manifest(
    path: str | os.PathLike[str],
) -> tuple[dict[tuple[str, str], dict[str, Any]], str, dict[str, Any] | None]:
    """Read the frozen JSONL canonically and return its keyed entry set.

    Format v2 carries a leading header line
    ``{"kind": ..., "schema_version": 2, "roots": {id: abspath}}`` and a
    per-entry ``loader`` field; format v1 has neither. Returns
    ``(entries, sha256_of_manifest, header_or_None)``.
    """

    manifest_path = Path(path)
    try:
        raw = manifest_path.read_bytes()
    except OSError as exc:
        raise SystemExit(
            f"attestation_fault: importable artifact manifest unreadable: {exc}"
        ) from exc
    entries: dict[tuple[str, str], dict[str, Any]] = {}
    header: dict[str, Any] | None = None
    expected_fields = _MANIFEST_ENTRY_FIELDS
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
        if line_number == 1:
            header = _manifest_header(entry)
            if header is not None:
                if encoded != _canonical_bytes(header):
                    raise SystemExit(
                        "attestation_fault: noncanonical importable manifest header"
                    )
                expected_fields = _MANIFEST_ENTRY_FIELDS | {"loader"}
                continue
        if not isinstance(entry, dict) or set(entry) != expected_fields:
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
        if header is not None:
            loader = entry.get("loader")
            if not isinstance(loader, str) or not loader:
                raise SystemExit(
                    f"attestation_fault: invalid manifest loader at line {line_number}"
                )
        key = (root_id, relpath)
        if key in entries:
            raise SystemExit(
                f"attestation_fault: duplicate importable manifest entry {key}"
            )
        entries[key] = entry
    if offset != len(raw):
        raise SystemExit("attestation_fault: importable manifest framing failure")
    return entries, hashlib.sha256(raw).hexdigest(), header


def _verify_importable_artifact_manifest(
    roots: list[str],
    frozen_entries: Mapping[tuple[str, str], Mapping[str, Any]],
    *,
    phase: str,
) -> dict[str, Any]:
    """Re-walk all four roots and require exact frozen-entry identity."""

    # This project import is intentionally after the child's sys.path replacement.
    from bistar_gp.m2cr.environment_freeze import walk_importable_artifacts

    def core(entry: Mapping[str, Any]) -> dict[str, Any]:
        # Drift is defined over the on-disk artifact facts. The v2 "loader"
        # annotation is derived metadata enforced per-module at the at-exit
        # inventory check, not by the re-walk.
        return {name: entry[name] for name in sorted(_MANIFEST_ENTRY_FIELDS)}

    actual_entries = {
        (entry["root"], entry["relpath"]): core(entry)
        for entry in walk_importable_artifacts(_manifest_roots(roots))
    }
    frozen_keys = set(frozen_entries)
    actual_keys = set(actual_entries)
    added = sorted(actual_keys - frozen_keys)
    removed = sorted(frozen_keys - actual_keys)
    changed = sorted(
        key
        for key in frozen_keys & actual_keys
        if core(frozen_entries[key]) != actual_entries[key]
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


def disallowed_native_modules(native_modules: list[str]) -> list[str]:
    """Return the native_stack_modules outside the frozen allowlist.

    The top-level package name is what matters (a submodule imports its
    package), and every bistar_gp.* module and the payload are excluded, so
    none can execute before the marker (plan §4.3; external audit round-2 F3).
    """

    return [
        name
        for name in native_modules
        if name.split(".", 1)[0] not in _ALLOWED_NATIVE_STACK
    ]


def _header_roots_fault(
    header_roots: dict[str, Any], four_roots: list[str]
) -> str | None:
    """Validate the manifest header root set against the launch four_roots.

    The three host-global roots (stdlib, lib-dynload, site-packages) are
    frozen absolute paths and require exact physical-path equality. The
    worktree root is per-launch (plan §4.5.1 pins the CWD to the run's OWN
    fresh detached worktree); the header only documents the freeze-time walk
    root, and the worktree's content is verified by the (root_id, relpath,
    sha256) re-walk, independent of physical path. Requiring physical-path
    equality on the worktree would reject every legitimate fresh-worktree
    launch (external audit F2), so it is exempted here.
    """

    if set(header_roots) != set(_MANIFEST_ROOT_IDS):
        return "manifest header roots must name exactly the four frozen root ids"
    for position, root_id in enumerate(_MANIFEST_ROOT_IDS):
        if root_id == "worktree":
            continue
        if os.path.realpath(header_roots[root_id]) != four_roots[position]:
            return "manifest header roots do not match four_roots"
    return None


def _install_project_namespace(worktree_root: str) -> None:
    """Expose the R2 modules without executing the scientific package initializer."""

    package_root = os.path.join(worktree_root, "bistar_gp")
    m2cr_root = os.path.join(package_root, "m2cr")
    if not os.path.isdir(m2cr_root):
        raise SystemExit("attestation_fault: worktree lacks bistar_gp/m2cr")
    # The fabricated packages carry NO __file__: their initializers are
    # deliberately never executed, so claiming a file origin would be false
    # provenance — and the §4.5.7 origin binding would then have to hash a
    # source that never ran (or, in a synthetic worktree, does not exist).
    # They inventory as packages without a file origin.
    package = ModuleType("bistar_gp")
    package.__path__ = [package_root]
    package.__package__ = "bistar_gp"
    sys.modules["bistar_gp"] = package
    subpackage = ModuleType("bistar_gp.m2cr")
    subpackage.__path__ = [m2cr_root]
    subpackage.__package__ = "bistar_gp.m2cr"
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
        "native_stack": "native_stack.json",
        "manifest_pre": "importable_manifest_pre.json",
        "manifest_post": "importable_manifest_post.json",
        "origin_binding_pre": "origin_binding_pre.json",
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
    # Findings 1+2: the child re-records the parent's authenticated-spec
    # digest inside this marker-bound attestation, so the parent can verify at
    # exit that both sides consumed the SAME static authority.
    spec_digest = _require_spec_binding_directives(config)
    return {
        "checks": checks,
        "sentinel_hash": _BOUND_SENTINEL_HASH(),
        "utf8_mode": sys.flags.utf8_mode,
        "pycache_prefix": actual_prefix,
        "authenticated_spec_sha256": spec_digest,
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
    closure_authority: Mapping[str, Mapping[str, str]] | None = None,
    modules: Mapping[str, ModuleType | None] | None = None,
) -> list[dict[str, Any]]:
    """Inventory every loaded module and bind every file origin (§4.5.7).

    With ``manifest_entries`` supplied (the mandatory launch path), every
    file-backed module must be authenticated: a module whose resolved origin
    is under one of the four roots must match a manifest entry by sha256 and
    loader class; a module outside all four roots must match an entry of the
    authenticated pre-boundary closure (``closure_authority``) by exact
    resolved path, sha256, and the frozen loader for its artifact type.
    Either authority failing, or a module with neither, fails closed.
    """

    if (roots is None) != (manifest_entries is None):
        raise SystemExit(
            "attestation_fault: inventory manifest roots/entries are incomplete"
        )
    if (manifest_entries is None) != (closure_authority is None):
        raise SystemExit(
            "attestation_fault: inventory closure authority is incomplete"
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
            # A claimed origin that is not an existing regular file backs NO
            # file execution — nothing can have been loaded from a path that
            # does not exist — so it carries no §4.5.7 authentication
            # obligation.  The canonical case (first real-native
            # production-path launch): torch installs a synthetic
            # ``torch.classes`` module carrying the bogus RELATIVE
            # ``__file__ = "_classes.py"``, which resolves against the child's
            # CWD to a nonexistent ``<worktree>/_classes.py``.  A real
            # smuggled file that DID execute exists on disk (isfile true) and
            # is authenticated below; only genuinely fileless origins are
            # classified here.
            if not os.path.isfile(resolved_origin):
                classification = "synthetic_no_file"
                resolved_origin = None
            else:
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
            containing: list[tuple[int, str, str]] = []
            for root_id, root in _manifest_roots(roots or []):
                try:
                    common = os.path.commonpath((root, resolved_origin))
                except ValueError:
                    continue
                if common != root:
                    continue
                relpath = Path(resolved_origin).relative_to(root).as_posix()
                containing.append((len(root), root_id, relpath))
            actual_sha256 = _sha256_file(resolved_origin)
            # Manifest v2 pins the loader class name (walker spelling is the
            # bare class name; the runtime spelling is module-qualified).
            loader_class = item["loader_class"]
            loader_spellings = {loader_class, loader_class.rsplit(".", 1)[-1]}

            def _loader_satisfies(expected: str) -> str | None:
                """The pinned-loader check; returns the binding note or None.

                A CONFLICTING concrete loader class fails closed — that is the
                §4.5.7 smuggling case the pin exists for (a zipimporter or
                SourcelessFileLoader presenting different bytes-to-execution
                semantics always presents its class).  A runtime loader of
                "none" carries no loading-mechanism claim at all: the first
                real-native production-path launch showed both C-extension-
                REGISTERED submodules (torch._C._autograd, created by the
                parent extension's init code) and library module-object
                surgery (torch.backends replaces its own sys.modules entry
                with a custom module instance) legitimately drop loader
                metadata after a genuine load.  The bytes are already
                sha-authenticated against the manifest and sourceless
                execution is excluded by its dedicated scan, so "none" is
                ACCEPTED AND RECORDED — upgraded to a parent binding when a
                loaded ancestor with the SAME resolved origin carries the
                pinned loader.
                """

                if expected in loader_spellings:
                    return "direct"
                if loader_class != "none":
                    return None
                parent_name = name
                while "." in parent_name:
                    parent_name = parent_name.rsplit(".", 1)[0]
                    parent = module_map.get(parent_name)
                    if parent is None:
                        continue
                    parent_spec = getattr(parent, "__spec__", None)
                    parent_origin = (
                        getattr(parent_spec, "origin", None)
                        if parent_spec is not None
                        else None
                    )
                    if not isinstance(parent_origin, str):
                        parent_origin = getattr(parent, "__file__", None)
                    if (
                        not isinstance(parent_origin, str)
                        or os.path.realpath(parent_origin) != resolved_origin
                    ):
                        continue
                    parent_loader = _loader_name(parent)
                    if expected in {
                        parent_loader,
                        parent_loader.rsplit(".", 1)[-1],
                    }:
                        return f"parent:{parent_name}"
                return "unclaimed"

            if containing:
                matching = [
                    (size, root_id, relpath, manifest_entries[(root_id, relpath)])
                    for size, root_id, relpath in containing
                    if (root_id, relpath) in manifest_entries
                    and manifest_entries[(root_id, relpath)].get("sha256")
                    == actual_sha256
                ]
                if not matching:
                    raise SystemExit(
                        "attestation_fault: loaded module has unknown or changed origin "
                        f"{name} -> {resolved_origin}"
                    )
                _, root_id, relpath, entry = max(
                    matching, key=lambda match: match[0]
                )
                expected_loader = entry.get("loader")
                loader_binding = (
                    "direct"
                    if expected_loader is None
                    else _loader_satisfies(expected_loader)
                )
                if loader_binding is None:
                    raise SystemExit(
                        "attestation_fault: loaded module loader class mismatch "
                        f"{name} -> {loader_class} (manifest pins "
                        f"{expected_loader})"
                    )
                item.update(
                    classification="manifest_file",
                    manifest_root=root_id,
                    manifest_relpath=relpath,
                    artifact_type=entry["artifact_type"],
                    sha256=actual_sha256,
                    loader_binding=loader_binding,
                )
            else:
                # Outside all four roots: the ONLY admissible authority is the
                # authenticated pre-boundary closure (the interpreter-forced
                # pre-replacement stdlib loads); anything else fails closed.
                pin = (closure_authority or {}).get(resolved_origin)
                if pin is None:
                    raise SystemExit(
                        "attestation_fault: loaded module origin is outside "
                        "the four roots and has no authenticated closure pin: "
                        f"{name} -> {resolved_origin}"
                    )
                if actual_sha256 != pin["sha256"]:
                    raise SystemExit(
                        "attestation_fault: outside-root loaded module does "
                        "not match its authenticated closure pin: "
                        f"{name} -> {resolved_origin}"
                    )
                closure_binding = _loader_satisfies(pin["loader"])
                if closure_binding is None:
                    raise SystemExit(
                        "attestation_fault: outside-root loaded module loader "
                        f"class mismatch {name} -> {loader_class} (closure "
                        f"pins {pin['loader']})"
                    )
                item.update(
                    classification="closure_file",
                    sha256=actual_sha256,
                    loader_binding=closure_binding,
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


def _hashed_worktree_opens(
    recorded: set[str], worktree_root: str, load_hashes: dict[str, str]
) -> dict[str, Any]:
    """Report worktree opens, preferring their LOAD-time hashes.

    Plan §4.5.10: every worktree file loaded is hashed. ``load_hashes`` holds
    the digest captured by the audit hook at the moment each worktree file was
    opened, so a file read and then deleted or renamed during cleanup is still
    hashed here rather than lost (external audit round-2 F6). An open target
    that was never load-hashed and is now absent lands in ``unresolved``
    (§4.3 nothing vanishes); that set is only ever populated by paths that
    were never successfully read as a worktree file (e.g. a probe-open of a
    nonexistent path), never by a genuine load.
    """

    root_real = os.path.realpath(worktree_root)
    by_realpath: dict[str, str] = dict(load_hashes)
    unresolved: set[str] = set()
    for raw in recorded:
        try:
            real = os.path.realpath(raw)
        except (OSError, ValueError):
            continue
        if real in by_realpath:
            continue
        try:
            common = os.path.commonpath((root_real, real))
        except ValueError:
            continue
        if common != root_real:
            continue
        if os.path.isfile(real):
            try:
                by_realpath[real] = _sha256_file(real)
            except OSError:
                unresolved.add(real)
        else:
            unresolved.add(real)
    return {
        "hashed": [
            {"path": path, "sha256": digest}
            for path, digest in sorted(by_realpath.items())
        ],
        "unresolved": sorted(unresolved),
    }


def _profile_integration_check(config: dict[str, Any]) -> dict[str, Any] | None:
    """Explicit frozen-hash comparison for ``bistar_gp.profile_integration``.

    Plan §4.5.10: an explicit comparison, never a Python ``assert``. The
    outcome object is recorded in the inventory attestation either way; the
    caller exits on a failed comparison.
    """

    expected = config.get("expected_profile_integration_sha256")
    if expected is None:
        return None
    if not isinstance(expected, str) or _SHA256_RE.fullmatch(expected) is None:
        raise SystemExit(
            "attestation_fault: expected_profile_integration_sha256 must be "
            "a lowercase sha256"
        )
    module = sys.modules.get("bistar_gp.profile_integration")
    check: dict[str, Any] = {
        "expected_sha256": expected,
        "module_loaded": module is not None,
        "actual_sha256": None,
        "match": None,
    }
    if module is None:
        return check
    origin = getattr(module, "__file__", None)
    if not isinstance(origin, str) or not os.path.isfile(origin):
        raise SystemExit(
            "attestation_fault: bistar_gp.profile_integration has no "
            "hashable file origin"
        )
    actual = _sha256_file(origin)
    check["actual_sha256"] = actual
    check["match"] = actual == expected
    return check


def main(
    config_path: str | os.PathLike[str],
    event_fd: int,
    expected_config_sha256: str,
) -> int:
    """Run one child launch.  Every failure raises an explicit ``SystemExit``.

    ``expected_config_sha256`` is the parent's transport binding of the
    authenticated bootstrap config (round-4 Codex delta review): the parent
    passes the canonical digest of the exact config bytes it derived, bound,
    validated, and wrote — through argv, which a mutation of the on-disk
    config file cannot alter.  The child verifies the bytes it actually read
    against that digest BEFORE consuming any field, closing the
    write-to-read mutation window on the otherwise-mutable
    ``bootstrap_config.json`` handoff.  The digest argument is mandatory and
    unconditional: there is no launch mode without it.
    """

    writer = _ControlWriter(event_fd)
    writer.emit("HELLO", pid=os.getpid())
    if (
        not isinstance(expected_config_sha256, str)
        or _SHA256_RE.fullmatch(expected_config_sha256) is None
    ):
        raise SystemExit(
            "attestation_fault: expected bootstrap-config sha256 argument is "
            "malformed"
        )
    with open(config_path, "rb") as handle:
        raw_config = handle.read()
    if hashlib.sha256(raw_config).hexdigest() != expected_config_sha256:
        raise SystemExit(
            "attestation_fault: bootstrap config digest mismatch — the "
            "consumed config does not match the parent's authenticated "
            "derivation"
        )
    config = json.loads(raw_config.decode("utf-8"))
    if not isinstance(config, dict):
        raise SystemExit("attestation_fault: bootstrap config is malformed")
    unknown_keys = sorted(set(config) - KNOWN_CONFIG_KEYS)
    if unknown_keys:
        raise SystemExit(
            "attestation_fault: bootstrap config carries unknown keys "
            f"{unknown_keys}; the consumed configuration is closed-world"
        )

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

    # External-audit finding 1: the importable-artifact manifest, the four
    # roots, the pre-boundary closure, and the spec digest are MANDATORY and
    # unconditional — there is no launch mode without the complete pre-import
    # re-walk and origin/loader authentication.  The directive checks run
    # before any manifest consumption.
    _require_spec_binding_directives(config)
    manifest_path = config["importable_artifact_manifest"]
    manifest_entries, manifest_sha256, manifest_header = (
        _load_importable_artifact_manifest(manifest_path)
    )
    if manifest_header is None:
        raise SystemExit(
            "attestation_fault: importable manifest must carry the format-v2 "
            "header (a headerless v1 manifest has no root or loader authority)"
        )
    fault = _header_roots_fault(manifest_header["roots"], roots)
    if fault is not None:
        raise SystemExit(f"attestation_fault: {fault}")
    closure_authority = _closure_authority(
        config["preboundary_closure"], roots[0]
    )

    run_dir, paths = _attestation_paths(config)
    # Cache the failure route from the IN-MEMORY authenticated config exactly
    # once (round-4 delta review, Codex round 3): _persist_failure must never
    # re-read the mutable on-disk config at failure time, so a mutation AFTER
    # the startup digest verification can neither redirect the failure record
    # nor influence it in any way.
    global _AUTHENTICATED_FAILURE_PATH
    _AUTHENTICATED_FAILURE_PATH = os.fspath(paths["failure"])
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

    # Finding 1: the complete pre-import re-walk is unconditional and gates the
    # marker; payload_started.json is impossible before it succeeds.
    manifest_pre = _verify_importable_artifact_manifest(
        roots, manifest_entries, phase="pre_audit"
    )
    manifest_pre.update(
        frozen_manifest_path=os.path.realpath(manifest_path),
        frozen_manifest_sha256=manifest_sha256,
    )
    manifest_pre_digest = _atomic_write_json(paths["manifest_pre"], manifest_pre)

    import_events: list[tuple[str, Any]] = []
    worktree_opens: set[str] = set()
    worktree_load_hashes: dict[str, str] = {}
    worktree_root_real = os.path.realpath(roots[0])
    canary_token = f"m2cr-audit-{os.getpid()}"
    canary_seen = False
    # Per-thread re-entrancy guard: the _sha256_file open must not recurse into
    # this hook on the SAME thread, but a concurrent worktree open on ANOTHER
    # thread must still be hashed rather than dropped (external audit
    # round-2 re-review, Opus finding 2). threading.local gives each thread its
    # own flag, closing the drop window without the re-entrant-deadlock risk a
    # shared lock would carry.
    hash_guard = threading.local()

    def audit_hook(event: str, args: tuple[Any, ...]) -> None:
        nonlocal canary_seen
        if getattr(hash_guard, "active", False):
            return
        if event == "import":
            module = args[0] if args else None
            filename = args[1] if len(args) > 1 else None
            if isinstance(module, str):
                import_events.append((module, filename))
        elif event == "open" and args:
            target = args[0]
            if isinstance(target, (str, bytes, os.PathLike)):
                try:
                    raw = os.fsdecode(target)
                except (TypeError, ValueError):
                    return
                worktree_opens.add(raw)
                # Plan §4.5.10: hash a worktree file at LOAD time, not at exit,
                # so a payload that reads a worktree data file and then deletes
                # or renames it during cleanup cannot erase the evidence
                # (external audit round-2 F6). The _hashing guard blocks the
                # re-entrant 'open' the hash itself would trigger.
                try:
                    real = os.path.realpath(raw)
                    if (
                        real not in worktree_load_hashes
                        and os.path.commonpath((worktree_root_real, real))
                        == worktree_root_real
                        and os.path.isfile(real)
                    ):
                        hash_guard.active = True
                        try:
                            worktree_load_hashes[real] = _sha256_file(real)
                        finally:
                            hash_guard.active = False
                except (OSError, ValueError):
                    pass
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

    # Codex round-3 C1 (requirement 1): unconditionally require EVERY mandatory
    # pre-scientific attestation directive before the marker — no directive
    # defaults, is optional, or is gated.  A missing, empty, or malformed
    # directive fails closed here, so a lean bootstrap config can never reach
    # payload_started (§4.3 "all pre-scientific attestations complete before the
    # marker").  This is defense-in-depth beneath the parent's derive-and-bind.
    require_mandatory_attestation_directives(config)
    native_modules = config["native_stack_modules"]
    # Fail closed on any module outside the frozen native-stack allowlist: a
    # bistar_gp.* module or the payload smuggled here would execute before the
    # marker, violating the §4.3 boundary (external audit round-2 F3).
    disallowed = disallowed_native_modules(native_modules)
    if disallowed:
        raise SystemExit(
            "attestation_fault: native_stack_modules outside the frozen "
            f"allowlist: {disallowed}"
        )
    loaded_native: dict[str, ModuleType] = {}
    for module_name in native_modules:
        try:
            # importlib.import_module imports EXACTLY the named module — the
            # former __import__(..., fromlist=["*"]) expanded the package's
            # __all__ and imported extra submodules (observed on the first
            # real-native production-path launch: torch's expansion pulled in
            # yaml's extension, an image the committed expectations
            # measurement, which imports the stack plainly, never loads).
            # The child and the freeze-time measurement now load the same
            # closure, and the pre-marker import surface is strictly smaller.
            loaded_native[module_name] = importlib.import_module(module_name)
        except BaseException as exc:
            raise SystemExit(
                f"attestation_fault: native import {module_name} failed: {exc}"
            ) from exc
    native_attestation: dict[str, Any] = {"torch_threads": None, "build_markers": {}}
    if "torch" in loaded_native:
        try:
            loaded_native["torch"].set_num_threads(10)
            loaded_native["torch"].set_num_interop_threads(10)
        except BaseException as exc:
            raise SystemExit(
                f"attestation_fault: torch thread controls failed: {exc}"
            ) from exc
        native_attestation["torch_threads"] = _torch_thread_readback(
            loaded_native["torch"]
        )
        native_attestation["build_markers"]["torch"] = _require_build_markers(
            "torch",
            _torch_build_description(loaded_native["torch"]),
            "torch_build_expected",
            config.get("torch_build_expected"),
        )
    if "numpy" in loaded_native:
        native_attestation["build_markers"]["numpy"] = _require_build_markers(
            "numpy",
            _numpy_build_description(loaded_native["numpy"]),
            "numpy_build_expected",
            config.get("numpy_build_expected"),
        )
    image_allowlist = _loaded_image_allowlist(config)

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
    stage_b_images = list(_image_enumerator())
    stage_b_image_hashes = hash_loaded_images(stage_b_images)
    native_attestation["loaded_images_stage_b"] = stage_b_images
    native_attestation["loaded_images_stage_b_sha256"] = stage_b_image_hashes
    # Record the measured Stage-B images as evidence BEFORE authenticating, so a
    # captured native_stack.json exists even when the authentication below fails
    # closed (nothing vanishes; also enables committed-expectation measurement).
    native_stack_digest = _atomic_write_json(
        paths["native_stack"], native_attestation
    )
    # F2 (round-3 revision) + Codex round-3 C1: authenticate the on-disk loaded
    # images against the committed expected set BEFORE the payload marker,
    # unconditionally (expected_loaded_images is a mandatory directive validated
    # by require_mandatory_attestation_directives above); an image with no
    # committed expectation, or any sha256 mismatch (a same-path pre-launch
    # mutation), fails closed here.
    authenticate_loaded_images(
        stage_b_image_hashes, config["expected_loaded_images"]
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

    # Finding 1: origin/loader authentication of every file-backed module
    # loaded so far — the interpreter-forced pre-replacement stdlib closure,
    # the worktree project modules, and the just-imported native stack — runs
    # BEFORE the marker, against the manifest (under-root origins) and the
    # authenticated pre-boundary closure (outside-root origins).  Any module
    # with neither authority, a byte mismatch, or a loader-class mismatch
    # fails closed here, so payload_started.json is impossible after an
    # unauthenticated load.
    pre_origin_inventory = _inventory(
        import_events,
        roots=roots,
        manifest_entries=manifest_entries,
        closure_authority=closure_authority,
    )
    origin_binding_pre_digest = _atomic_write_json(
        paths["origin_binding_pre"],
        {
            "phase": "pre_marker",
            "modules_checked": len(pre_origin_inventory),
            "manifest_bound": sum(
                1
                for item in pre_origin_inventory
                if item["classification"] == "manifest_file"
            ),
            "closure_bound": sum(
                1
                for item in pre_origin_inventory
                if item["classification"] == "closure_file"
            ),
        },
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
        "native_stack": native_stack_digest,
        "sourceless_check": sourceless_digest,
        # Finding 1: the pre-walk and pre-marker origin binding are mandatory
        # marker-bound attestations; the marker cannot exist without them.
        "importable_manifest_pre": manifest_pre_digest,
        "origin_binding_pre": origin_binding_pre_digest,
    }
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

    # Finding 1: the complete post-execution re-walk and the full origin/loader
    # validation are unconditional; a protocol exit (COMPLETED/ALGORITHM_STOP)
    # is impossible without both.
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
        roots=roots,
        manifest_entries=manifest_entries,
        closure_authority=closure_authority,
    )
    profile_check = _profile_integration_check(config)
    # Kimi K3 challenge, finding 4 (recorded residual): an import audit event
    # whose module is no longer present in sys.modules at inventory time (an
    # import-then-evict) cannot be origin-authenticated after the fact — the
    # audit event does not carry the resolved origin.  The names are recorded
    # here so the evidence discloses the eviction rather than silently
    # narrowing "every executed module" to "every still-resident module";
    # worktree-origin reads remain independently covered by the load-time
    # open-hashing above.
    evicted_imports = sorted(
        {name for name, _ in import_events} - set(sys.modules)
    )
    inventory_document = {
        "modules": inventory,
        "import_events_without_module": evicted_imports,
        "worktree_opens": _hashed_worktree_opens(
            set(worktree_opens), roots[0], dict(worktree_load_hashes)
        ),
        "profile_integration_check": profile_check,
    }
    inventory_digest = _atomic_write_json(
        paths["import_inventory"], inventory_document
    )
    # CP-1b: a launch that declares the profile-hash directive must actually
    # have imported bistar_gp.profile_integration and matched it; a directive
    # present with the module never loaded (match is None) is a fail-open of the
    # §4.5.10 explicit comparison and must fail closed, not pass silently.
    if profile_check is not None and (
        not profile_check["module_loaded"]
        or profile_check["match"] is not True
    ):
        raise SystemExit(
            "attestation_fault: profile_integration explicit hash comparison "
            f"failed (module_loaded={profile_check['module_loaded']}): "
            f"expected {profile_check['expected_sha256']}, actual "
            f"{profile_check['actual_sha256']}"
        )

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
    # Plan §4.5.5: each view is compared to its own PERSISTED, authenticated
    # post-initialization baseline re-read from disk, never to in-memory
    # copies a payload could not have tampered with.
    persisted_stage_b_os = _read_authenticated_json(
        paths["stage_b_os"], stage_b_os_digest, "stage_b_os"
    )
    persisted_stage_b_raw = _read_authenticated_json(
        paths["stage_b_raw"], stage_b_raw_digest, "stage_b_raw"
    )
    baseline_os = persisted_stage_b_os.get("baseline")
    baseline_raw = persisted_stage_b_raw.get("baseline")
    if not isinstance(baseline_os, dict) or not isinstance(baseline_raw, dict):
        raise SystemExit(
            "attestation_fault: persisted Stage B baselines are malformed"
        )
    if stage_c_os != baseline_os or stage_c_raw != baseline_raw:
        raise SystemExit("environment_fault: Stage C environment drift")
    stage_c_images = list(_image_enumerator())
    new_images = classify_new_loaded_images(
        stage_b_images, stage_c_images, image_allowlist
    )
    if new_images:
        raise SystemExit(
            "environment_fault: unapproved native images loaded during "
            f"payload: {new_images}"
        )
    # F2/§4.5.7 "enumeration AND hashing", §4.5.11 rehash at exit: re-hash the
    # on-disk native images and fail closed if any image loaded at Stage B had
    # its on-disk bytes changed during payload execution (an ordinary
    # native-library mutation, in scope per §4.5.13).
    stage_c_image_hashes = hash_loaded_images(stage_c_images)
    image_hash_drift = loaded_image_hash_drift(
        stage_b_image_hashes, stage_c_image_hashes
    )
    if image_hash_drift:
        raise SystemExit(
            "attestation_fault: loaded native image bytes changed during "
            f"payload: {image_hash_drift}"
        )
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
            "loaded_image_check": {
                "stage_b_count": len(stage_b_images),
                "stage_c_count": len(stage_c_images),
                "new_allowed": sorted(
                    (set(stage_c_images) - set(stage_b_images))
                    & set(image_allowlist)
                ),
                "stage_b_hashed_count": len(stage_b_image_hashes),
                "stage_c_hashed_count": len(stage_c_image_hashes),
                "hash_drift": image_hash_drift,
            },
            "payload_marker_sha256": marker_sha256,
            "import_inventory_sha256": inventory_digest,
            "importable_manifest_post_sha256": manifest_post_digest,
            "authenticated_spec_sha256": config["authenticated_spec_sha256"],
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


# Set by main() exactly once, from the IN-MEMORY authenticated config,
# immediately after its attestation paths are derived.  The on-disk config is
# NEVER re-read at failure time (round-4 delta review, Codex rounds 2+3): a
# digest-REJECTED config cannot route the failure record at all, and a config
# mutated AFTER the startup digest verification cannot redirect it either —
# the only trusted route is the one captured from the bytes the parent bound.
_AUTHENTICATED_FAILURE_PATH: str | None = None


def _persist_failure(config_path: str, reason: Any) -> None:
    text = str(reason) if reason is not None else "bootstrap exited"
    fault_class = text.split(":", 1)[0] if ":" in text else "other"
    if _AUTHENTICATED_FAILURE_PATH is not None:
        failure_path = Path(_AUTHENTICATED_FAILURE_PATH)
    else:
        # No authenticated route exists (the failure precedes the digest
        # verification or the attestation-path derivation): the evidence lands
        # beside the consumed config, inside the run directory in production.
        failure_path = (
            Path(config_path).resolve().parent / "bootstrap_failure.json"
        )
    try:
        _atomic_write_json(failure_path, {"fault_class": fault_class, "detail": text})
    except BaseException:
        return


if __name__ == "__main__":
    # The CLI-contract guards persist their evidence too (round-4, Codex
    # round 4): any non-protocol child exit that has a config-path argument
    # leaves a failure record beside it — the pre-derivation fallback route,
    # since no authenticated route can exist before main() runs.
    if len(sys.argv) != 4:
        _CONTRACT_REASON = (
            "attestation_fault: expected config path, event fd, and config "
            "sha256"
        )
        if len(sys.argv) >= 2:
            _persist_failure(sys.argv[1], _CONTRACT_REASON)
        raise SystemExit(_CONTRACT_REASON)
    try:
        event_fd = int(sys.argv[2])
    except ValueError as exc:
        _CONTRACT_REASON = "attestation_fault: event fd is not an integer"
        _persist_failure(sys.argv[1], _CONTRACT_REASON)
        raise SystemExit(_CONTRACT_REASON) from exc
    try:
        code = main(sys.argv[1], event_fd, sys.argv[3])
    except SystemExit as exc:
        if exc.code not in (0, 3):
            _persist_failure(sys.argv[1], exc.code)
        raise
    except BaseException as exc:
        _persist_failure(sys.argv[1], f"other: {type(exc).__name__}: {exc}")
        raise
    raise SystemExit(code)
