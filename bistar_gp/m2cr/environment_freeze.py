"""Deterministic M2cR environment-freeze artifact generators.

Plan \u00a74.5 freezes a complete, host-scoped execution snapshot.  This module
only inventories and serializes that snapshot; it imports no scientific stack
and performs no work at import time.  All filesystem writes are explicit
``build_*`` operations or the command-line entry point.

The importable-artifact walk implements the B15(ii) scope clarification:
ordinary source-backed ``__pycache__`` files are excluded, while orphan,
legacy, and otherwise sourceless bytecode candidates remain included.
"""

from __future__ import annotations

import argparse
import importlib.machinery
import json
import os
import re
import subprocess
import tempfile
from collections import Counter
from collections.abc import Iterable, Iterator, Mapping, Sequence
from pathlib import Path
from typing import Any

from bistar_gp.m2cr.serialization import (
    atomic_write_canonical_json,
    canonical_dumps,
    canonical_sha256,
    sha256_file,
)

_SHA256_RE = re.compile(r"[0-9a-f]{64}")

# Frozen R2 native-stack attestation spec (external audit round-3 F1/F2). These
# are committed R2 values, NOT deferred to R2a (which is only the numeric
# evidence-ceiling addendum): the native import list, the backend build markers
# that attest Accelerate, and the single frozen Stage-B environment delta. The
# expected loaded-image set and the profile hash are measured/read at generation
# time by build_native_stack_expectations.
R2_NATIVE_STACK_MODULES = ("numpy", "torch")
R2_TORCH_BUILD_EXPECTED = (
    "BLAS_INFO=accelerate",
    "USE_MKL=OFF",
    "USE_MKLDNN=OFF",
    "USE_OPENMP=ON",
)
R2_NUMPY_BUILD_EXPECTED = ("name: accelerate",)
R2_STAGE_B_EXPECTED = {"__CF_USER_TEXT_ENCODING": "0x1F5:0x0:0x0"}

__all__ = [
    "R2_CODE_RELPATHS",
    "R1_SCHEMA_RELPATHS",
    "IMPORTABLE_MANIFEST_KIND",
    "IMPORTABLE_MANIFEST_SCHEMA_VERSION",
    "LOADER_BY_ARTIFACT_TYPE",
    "classify_pyc_candidate",
    "read_manifest_header",
    "walk_importable_artifacts",
    "build_importable_artifact_manifest",
    "build_interpreter_pin",
    "build_child_env_mapping",
    "build_preboundary_attestation_set",
    "build_environment_freeze_manifest",
    "build_dependency_lock",
    "build_infrastructure_manifest",
    "main",
]


R2_CODE_RELPATHS = (
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
)

R1_SCHEMA_RELPATHS = (
    "docs/m2c_freeze/m2c_execution_record.schema_v1.json",
    "docs/m2c_freeze/m2c_authorization_ledger.schema_v1.json",
)

_FREEZE_ARTIFACT_KEYS = (
    "child_env_mapping",
    "importable_artifact_manifest",
    "interpreter_pin",
    "preboundary_attestation_set",
)
_INFRASTRUCTURE_ARTIFACT_KEYS = _FREEZE_ARTIFACT_KEYS + (
    "environment_freeze_manifest",
    "dependency_lock",
    "native_stack_expectations",
)
_INFRASTRUCTURE_R1_SCHEMA_KEYS = (
    "execution_record",
    "authorization_ledger",
)
_R3_DIAGNOSTIC_SCHEMA_BASENAME = "m2c_diagnostic_record.schema_v1.json"
_ARCHIVE_SUFFIXES = (".egg", ".zip")
_EXTENSION_SUFFIXES = tuple(
    sorted(importlib.machinery.EXTENSION_SUFFIXES, key=len, reverse=True)
)
_DYLD_CACHE_BASENAME = "dyld_shared_cache_arm64e"
_DYLD_CACHE_DIR = "/System/Volumes/Preboot/Cryptexes/OS/System/Library/dyld"
_INTERPRETER = "/opt/homebrew/Caskroom/miniconda/base/bin/python3.13"

IMPORTABLE_MANIFEST_KIND = "m2cr_importable_artifact_manifest"
IMPORTABLE_MANIFEST_SCHEMA_VERSION = 2

# Plan section 4.5.7 requires every executed module's resolved origin AND
# loader class to match a frozen manifest entry, so the manifest itself
# records the loader class each artifact type resolves through.
LOADER_BY_ARTIFACT_TYPE = {
    "source": "SourceFileLoader",
    "extension": "ExtensionFileLoader",
    "legacy_bytecode": "SourcelessFileLoader",
    "orphan_bytecode": "SourcelessFileLoader",
    "importable_archive": "zipimporter",
}


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _logical_files(root: Path) -> Iterator[tuple[Path, str]]:
    """Yield files under ``root`` and fail closed on every unsafe symlink."""

    root_real = root.resolve(strict=True)
    if not root_real.is_dir():
        raise NotADirectoryError(root)

    def visit(
        logical_dir: Path,
        rel_parts: tuple[str, ...],
        real_ancestors: frozenset[Path],
    ) -> Iterator[tuple[Path, str]]:
        real_dir = logical_dir.resolve(strict=True)
        if real_dir in real_ancestors:
            raise ValueError(f"cyclic symlink under walked root: {logical_dir}")
        ancestors = real_ancestors | {real_dir}
        with os.scandir(logical_dir) as scan:
            children = sorted(scan, key=lambda entry: entry.name)
        for child in children:
            logical_path = logical_dir / child.name
            child_rel_parts = rel_parts + (child.name,)
            relpath = "/".join(child_rel_parts)
            if child.is_symlink():
                try:
                    target = logical_path.resolve(strict=True)
                except (FileNotFoundError, RuntimeError, OSError) as exc:
                    raise ValueError(
                        f"broken or cyclic symlink under walked root: {logical_path}"
                    ) from exc
                if not _inside(target, root_real):
                    raise ValueError(
                        "symlink escapes walked root: "
                        f"{logical_path} -> {target}"
                    )
                if target.is_dir():
                    yield from visit(logical_path, child_rel_parts, ancestors)
                elif target.is_file():
                    # Hash the resolved target explicitly.  The logical path is
                    # retained because that is the importable spelling.
                    yield target, relpath
                continue
            if child.is_dir(follow_symlinks=False):
                yield from visit(logical_path, child_rel_parts, ancestors)
            elif child.is_file(follow_symlinks=False):
                yield logical_path, relpath

    yield from visit(root, (), frozenset())


def _source_stem_candidates(tagged_stem: str) -> list[str]:
    """Return the possible source stems of one ``__pycache__`` filename stem.

    Cache filenames are ``<source_stem>.<cache_tag>.pyc``, so the source stem
    is the tagged stem with its trailing cache tag stripped at a dot boundary.
    The tag is usually one dot-component (``v0.9.0.a.cpython-313.pyc`` maps to
    ``v0.9.0.a.py``) but may itself contain dots (pytest's rewrite tag:
    ``mod.cpython-313-pytest-8.3.3.pyc`` maps to ``mod.py``), so every dot
    boundary is a candidate strip point.  A stem with no dot carries no tag
    and is its own candidate.
    """

    if "." not in tagged_stem:
        return [tagged_stem]
    pieces = tagged_stem.split(".")
    return [".".join(pieces[:count]) for count in range(len(pieces) - 1, 0, -1)]


def _valid_corresponding_source(root: Path, pyc_relpath: str) -> bool:
    parts = pyc_relpath.split("/")
    if len(parts) < 2 or parts[-2] != "__pycache__":
        return False
    root_real = root.resolve(strict=True)
    tagged_stem = parts[-1][:-4]
    for source_stem in _source_stem_candidates(tagged_stem):
        source_parts = parts[:-2] + [source_stem + ".py"]
        source = root.joinpath(*source_parts)
        try:
            target = source.resolve(strict=True)
        except (FileNotFoundError, RuntimeError, OSError):
            continue
        if target.is_file() and _inside(target, root_real):
            return True
    return False


def classify_pyc_candidate(
    root: str | os.PathLike[str], relpath: str
) -> str | None:
    """Classify one ``.pyc`` candidate exactly as the manifest walker does.

    Returns ``None`` for a normal source-backed ``__pycache__`` entry (the
    B15(ii) exclusion) and for non-``.pyc`` paths, ``"orphan_bytecode"`` for a
    ``__pycache__`` entry with no valid corresponding source inside ``root``,
    and ``"legacy_bytecode"`` for a ``.pyc`` outside ``__pycache__``.  The
    launch-time bootstrap reuses this single classification so the freeze
    generator and the bytecode rejection scan cannot disagree.
    """

    name = relpath.rsplit("/", 1)[-1]
    if not name.endswith(".pyc"):
        return None
    if "/__pycache__/" in f"/{relpath}":
        if _valid_corresponding_source(Path(root), relpath):
            return None
        return "orphan_bytecode"
    return "legacy_bytecode"


def _artifact_type(root: Path, relpath: str) -> str | None:
    name = relpath.rsplit("/", 1)[-1]
    if name.endswith(".py"):
        return "source"
    if any(name.endswith(suffix) for suffix in _EXTENSION_SUFFIXES):
        return "extension"
    if name.endswith(".pyc"):
        return classify_pyc_candidate(root, relpath)
    if name.endswith(_ARCHIVE_SUFFIXES):
        return "importable_archive"
    return None


def walk_importable_artifacts(
    roots: list[tuple[str, str | os.PathLike[str]]],
) -> Iterator[dict[str, Any]]:
    """Yield the B15(ii)-scoped artifact inventory in canonical order.

    Entries contain exactly ``root``, ``relpath``, ``artifact_type``,
    ``loader``, ``sha256``, and ``size``; ``loader`` is the plan-4.5.7 loader
    class the artifact type resolves through.  In-root symlinks are recorded
    under their logical path with the resolved target's bytes.  Escaping,
    broken, and cyclic symlinks raise :class:`ValueError` so an inventory
    cannot silently omit an importable spelling.
    """

    root_ids = [root_id for root_id, _ in roots]
    if len(root_ids) != len(set(root_ids)):
        raise ValueError("root ids must be unique")
    # The four frozen sys.path roots overlap on disk (lib-dynload and
    # site-packages are subdirectories of the stdlib root).  Each artifact
    # belongs to exactly one root: the most specific one, mirroring how the
    # import system resolves it through its own path entry.  The exclusion is
    # derived from the root list itself so the freeze generator and the
    # launch-time completeness check cannot disagree.
    resolved_roots = {
        root_id: Path(root_value).resolve(strict=True)
        for root_id, root_value in roots
    }
    entries: list[dict[str, Any]] = []
    for root_id, root_value in roots:
        if not isinstance(root_id, str) or not root_id:
            raise ValueError("each root id must be a non-empty string")
        root = Path(root_value)
        own_resolved = resolved_roots[root_id]
        nested = [
            other
            for other_id, other in resolved_roots.items()
            if other_id != root_id
            and other != own_resolved
            and _inside(other, own_resolved)
        ]
        for file_path, relpath in _logical_files(root):
            if nested:
                resolved_file = (own_resolved / relpath).resolve()
                if any(_inside(resolved_file, inner) for inner in nested):
                    continue
            artifact_type = _artifact_type(root, relpath)
            if artifact_type is None:
                continue
            entries.append(
                {
                    "root": root_id,
                    "relpath": relpath,
                    "artifact_type": artifact_type,
                    "loader": LOADER_BY_ARTIFACT_TYPE[artifact_type],
                    "sha256": sha256_file(file_path),
                    "size": file_path.stat().st_size,
                }
            )
    entries.sort(key=lambda entry: (entry["root"], entry["relpath"]))
    yield from entries


def _manifest_header(
    roots: list[tuple[str, str | os.PathLike[str]]],
) -> dict[str, Any]:
    return {
        "kind": IMPORTABLE_MANIFEST_KIND,
        "schema_version": IMPORTABLE_MANIFEST_SCHEMA_VERSION,
        "roots": {
            root_id: os.fspath(Path(root_value).resolve(strict=True))
            for root_id, root_value in roots
        },
    }


def read_manifest_header(path: str | os.PathLike[str]) -> dict[str, Any]:
    """Parse and shape-validate the first-line v2 manifest header.

    Plan section 4.5.4 sources permitted paths from frozen manifest metadata;
    the header is that metadata: ``kind``, ``schema_version`` 2, and a
    ``roots`` mapping from root id to the absolute resolved root path.  A
    missing or malformed header raises :class:`ValueError` so a headerless
    (v1) manifest can never be silently consumed as v2.
    """

    with open(path, "rb") as handle:
        first_line = handle.readline()
    try:
        header = json.loads(first_line.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"importable manifest header is not valid JSON: {exc}")
    if not isinstance(header, dict):
        raise ValueError("importable manifest header is not an object")
    if header.get("kind") != IMPORTABLE_MANIFEST_KIND:
        raise ValueError("importable manifest header has the wrong kind")
    if header.get("schema_version") != IMPORTABLE_MANIFEST_SCHEMA_VERSION:
        raise ValueError("importable manifest header has the wrong schema_version")
    if set(header) != {"kind", "schema_version", "roots"}:
        raise ValueError("importable manifest header has a non-canonical key set")
    roots = header.get("roots")
    if (
        not isinstance(roots, dict)
        or not roots
        or not all(
            isinstance(root_id, str)
            and root_id
            and isinstance(root_path, str)
            and os.path.isabs(root_path)
            for root_id, root_path in roots.items()
        )
    ):
        raise ValueError(
            "importable manifest header roots must map non-empty ids to "
            "absolute resolved paths"
        )
    return header


def build_importable_artifact_manifest(
    roots: list[tuple[str, str | os.PathLike[str]]],
    out_path: str | os.PathLike[str],
) -> dict[str, Any]:
    """Atomically stream the v2 header plus inventory as canonical JSONL."""

    out_path = Path(out_path)
    directory = out_path.parent
    fd, temporary_name = tempfile.mkstemp(dir=directory, prefix=".m2cr-tmp-")
    counts: Counter[str] = Counter()
    total_entries = 0
    total_bytes = 0
    import hashlib

    digest = hashlib.sha256()
    try:
        with os.fdopen(fd, "wb") as handle:
            header_line = (canonical_dumps(_manifest_header(roots)) + "\n").encode(
                "utf-8"
            )
            handle.write(header_line)
            digest.update(header_line)
            total_bytes += len(header_line)
            for entry in walk_importable_artifacts(roots):
                line = (canonical_dumps(entry) + "\n").encode("utf-8")
                handle.write(line)
                digest.update(line)
                total_bytes += len(line)
                total_entries += 1
                counts[entry["artifact_type"]] += 1
            handle.flush()
            os.fsync(handle.fileno())
        os.rename(temporary_name, out_path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except OSError:
            pass
        raise
    directory_fd = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
    return {
        "counts_by_type": dict(sorted(counts.items())),
        "total_entries": total_entries,
        "total_bytes_of_manifest": total_bytes,
        "sha256_of_manifest": digest.hexdigest(),
    }


def build_interpreter_pin(
    interpreter_path: str | os.PathLike[str],
) -> dict[str, Any]:
    """Re-attest a target interpreter independently of this process."""

    path = os.fspath(interpreter_path)
    realpath = os.path.realpath(path)
    probe = (
        "import json,sys;"
        "print(json.dumps({'implementation':sys.implementation.name,"
        "'version_info':list(sys.version_info),'version_string':sys.version},"
        "sort_keys=True,separators=(',',':')))"
    )
    completed = subprocess.run(
        [path, "-c", probe],
        check=True,
        capture_output=True,
        text=True,
    )
    version = json.loads(completed.stdout.strip())
    return {
        "path": path,
        "realpath": realpath,
        "version": version,
        "sha256": sha256_file(realpath),
    }


def build_child_env_mapping() -> dict[str, Any]:
    """Return the exact Stage-A parent-supplied mapping from plan \u00a74.5.5."""

    return {
        "fixed": {
            "PYTHONHASHSEED": "0",
            "OMP_NUM_THREADS": "10",
            "OMP_DYNAMIC": "FALSE",
            "MKL_NUM_THREADS": "10",
            "VECLIB_MAXIMUM_THREADS": "10",
            "LC_ALL": "C",
            "TZ": "UTC",
            "PATH": "/usr/bin:/bin",
        },
        "run_local_keys": [
            "HOME",
            "TMPDIR",
            "XDG_CACHE_HOME",
            "XDG_CONFIG_HOME",
            "XDG_DATA_HOME",
            "XDG_STATE_HOME",
        ],
        "path_policy": "minimal",
        "excluded_prefixes": ["PYTHON (all others)", "DYLD_"],
        "notes": [
            "OPENBLAS_NUM_THREADS dropped as empirically inert (setting it changed nothing).",
            "MKL_NUM_THREADS retained as operative via ATen precedence even with no MKL runtime.",
            "LC_CTYPE expected absent under LC_ALL=C.",
            "utf8_mode==1 recorded.",
        ],
    }


def _attestation_entry(
    path: Path, include_hashes: bool, *, worktree_root: Path | None = None
) -> dict[str, Any]:
    """One pre-boundary pin entry.

    A pin that resolves INSIDE ``worktree_root`` is stored worktree-relative
    (``{"root": "worktree", "relpath": ...}``) so the committed set stays
    launch-invariant and is re-verified against each launch's own fresh
    detached worktree, not the freeze-time worktree path (external audit
    round-3 F3).  Host-global pins (interpreter, dyld, stdlib/site-packages
    closure members) keep their absolute path, which is stable across launches.
    """

    if worktree_root is not None:
        try:
            relpath = Path(path).resolve().relative_to(worktree_root)
        except ValueError:
            relpath = None
        if relpath is not None:
            entry: dict[str, Any] = {
                "root": "worktree",
                "relpath": relpath.as_posix(),
            }
            if include_hashes:
                entry["sha256"] = sha256_file(path)
            return entry
    entry = {"path": os.fspath(path)}
    if include_hashes:
        entry["sha256"] = sha256_file(path)
    return entry


def build_preboundary_attestation_set(
    interpreter_path: str | os.PathLike[str] = _INTERPRETER,
    *,
    dyld_path: str | os.PathLike[str] = "/usr/lib/dyld",
    dyld_cache_dir: str | os.PathLike[str] = _DYLD_CACHE_DIR,
    bootstrap_closure_paths: Iterable[str | os.PathLike[str]] = (),
    worktree_root: str | os.PathLike[str] | None = None,
    include_hashes: bool = True,
    declared_subcache_count: int = 12,
) -> dict[str, Any]:
    """Build the frozen pre-audit-boundary source/native attestation set.

    ``bootstrap_closure_paths`` is deliberately a frozen caller-supplied
    enumeration: integration supplies ``bistar_gp/m2cr/bootstrap.py`` and
    every stdlib/native path that final bootstrap imports before installing
    the audit hook.  Tests substitute small fake files.  The dyld-cache
    enumeration records the plan-declared count separately from what this
    host actually exposes.
    """

    interpreter_realpath = Path(interpreter_path).resolve(strict=True)
    dyld = Path(dyld_path)
    cache_dir = Path(dyld_cache_dir)
    main = cache_dir / _DYLD_CACHE_BASENAME
    if not main.is_file():
        raise FileNotFoundError(main)
    # Declared subcaches carry a two-digit ordinal and, on current macOS, an
    # optional role suffix (dylddata, dyldreadonly, dyldlinkedit).  All twelve
    # numbered files are declared subcaches of the main arm64e cache; the
    # bare-numeric-only spelling would see just four of them.
    pattern = re.compile(
        rf"^{re.escape(_DYLD_CACHE_BASENAME)}\.(\d+)(?:\.[a-z]+)?$"
    )
    subcaches_with_index: list[tuple[int, str, Path]] = []
    for candidate in cache_dir.iterdir():
        match = pattern.fullmatch(candidate.name)
        if match and candidate.is_file():
            subcaches_with_index.append(
                (int(match.group(1)), candidate.name, candidate)
            )
    subcaches = [
        path for _, _, path in sorted(subcaches_with_index, key=lambda item: item[:2])
    ]
    if include_hashes and len(subcaches) != declared_subcache_count:
        raise ValueError(
            "dyld shared-cache subcache count mismatch: "
            f"declared {declared_subcache_count}, discovered {len(subcaches)}"
        )
    closure = sorted((Path(path) for path in bootstrap_closure_paths), key=os.fspath)
    worktree = Path(worktree_root).resolve() if worktree_root is not None else None
    artifact = {
        "kind": "m2cr_preboundary_attestation_set",
        "schema_version": 1,
        "interpreter_binary": _attestation_entry(
            interpreter_realpath, include_hashes
        ),
        "dyld": _attestation_entry(dyld, include_hashes),
        "dyld_shared_cache": {
            "main": _attestation_entry(main, include_hashes),
            "declared_subcache_count": declared_subcache_count,
            "discovered_subcache_count": len(subcaches),
            "subcaches": [
                _attestation_entry(path, include_hashes) for path in subcaches
            ],
        },
        "bootstrap_closure": [
            _attestation_entry(path, include_hashes, worktree_root=worktree)
            for path in closure
        ],
    }
    if not include_hashes:
        artifact["test_fixture"] = True
    return artifact


def _path_spec(value: Any) -> tuple[str | None, Path]:
    """Split one pin input into (explicit display override or None, file path)."""

    if isinstance(value, Mapping):
        display = os.fspath(value["path"])
        filesystem_value = value.get("filesystem_path", value["path"])
        return display, Path(filesystem_value)
    return None, Path(value)


def _discover_repo_root(start: Path) -> Path | None:
    """Return the nearest ancestor holding ``.git`` (a dir, or a worktree file)."""

    for candidate in (start, *start.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def _stored_pin_path(
    file_path: Path, repo_root: str | os.PathLike[str] | None
) -> str:
    """Store repo-contained pins repo-relative; host-global pins absolute.

    Absolute host paths poison worktree audits: a manifest generated in one
    checkout would then only ever verify against that checkout.  Files inside
    the repository (explicit ``repo_root``, or the file's own repository
    discovered by walking up to a ``.git`` entry) are pinned relative to the
    repository root; only host-global targets (interpreter, dyld) stay
    absolute.
    """

    resolved = file_path.resolve()
    if repo_root is not None:
        root: Path | None = Path(repo_root).resolve()
    else:
        root = _discover_repo_root(resolved.parent)
    if root is not None and _inside(resolved, root):
        return resolved.relative_to(root).as_posix()
    return os.fspath(resolved)


def build_environment_freeze_manifest(
    artifact_paths: Mapping[str, Any],
    repo_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Aggregate and pin exactly the four static v5 freeze artifacts."""

    if set(artifact_paths) != set(_FREEZE_ARTIFACT_KEYS):
        raise ValueError(
            "artifact_paths must contain exactly " + ", ".join(_FREEZE_ARTIFACT_KEYS)
        )
    artifacts: dict[str, dict[str, str]] = {}
    for name in sorted(_FREEZE_ARTIFACT_KEYS):
        display, path = _path_spec(artifact_paths[name])
        stored = display if display is not None else _stored_pin_path(path, repo_root)
        if _parsed_content_is_test_fixture(path):
            raise ValueError(
                f"freeze manifest cannot pin test-fixture artifact: {stored}"
            )
        artifacts[name] = {"path": stored, "sha256": sha256_file(path)}
    return {
        "kind": "m2cr_environment_freeze_manifest",
        "schema_version": 1,
        "artifacts": artifacts,
    }


def _parsed_content_is_test_fixture(path: Path) -> bool:
    """Return whether a JSON or JSONL artifact declares fixture-only content."""

    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        try:
            for line in text.splitlines():
                if line.strip():
                    item = json.loads(line)
                    if (
                        isinstance(item, Mapping)
                        and item.get("test_fixture") is True
                    ):
                        return True
        except json.JSONDecodeError:
            return False
        return False
    if isinstance(parsed, Mapping):
        return parsed.get("test_fixture") is True
    if isinstance(parsed, list):
        return any(
            isinstance(item, Mapping) and item.get("test_fixture") is True
            for item in parsed
        )
    return False


def _distribution_identity(dist_info: Path) -> tuple[str, str]:
    metadata = dist_info / "METADATA"
    if metadata.is_file():
        from email.parser import Parser

        parsed = Parser().parsestr(metadata.read_text(encoding="utf-8"))
        name = parsed.get("Name")
        version = parsed.get("Version")
        if name and version:
            return name, version
    stem = dist_info.name[: -len(".dist-info")]
    if "-" not in stem:
        return stem, ""
    return tuple(stem.rsplit("-", 1))  # type: ignore[return-value]


_NATIVE_STACK_MEASURE = r"""
import sys, os, ctypes, json, io, contextlib, hashlib

def _dyld_images():
    libc = ctypes.CDLL(None)
    count = libc._dyld_image_count; count.restype = ctypes.c_uint32
    name = libc._dyld_get_image_name; name.restype = ctypes.c_char_p
    name.argtypes = [ctypes.c_uint32]
    return sorted({os.fsdecode(name(i)) for i in range(count()) if name(i)})

def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()

native_modules = json.loads(sys.argv[1])
for module_name in native_modules:
    __import__(module_name)
loaded = sys.modules
images = [
    {"path": path, "sha256": _sha256(path)}
    for path in _dyld_images()
    if os.path.isfile(path)
]
torch_cfg = ""
if "torch" in loaded:
    torch_cfg = str(loaded["torch"].__config__.show())
numpy_cfg = ""
if "numpy" in loaded:
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        loaded["numpy"].show_config()
    numpy_cfg = buffer.getvalue()
print(json.dumps({
    "torch_config_show": torch_cfg,
    "numpy_config_show": numpy_cfg,
    "stage_b_env": {
        key: os.environ[key]
        for key in ("__CF_USER_TEXT_ENCODING",)
        if key in os.environ
    },
    "expected_loaded_images": images,
}))
"""


# The bootstrap's bound-hash sentinel string (must equal bistar_gp.m2cr.
# bootstrap._SENTINEL); the build-pinned frozen bound ``sentinel.__hash__()``
# value (plan §4.5.8) is measured from it under the frozen ``PYTHONHASHSEED=0``.
_SENTINEL_STRING = "m2cr-hash-sentinel"


def measure_expected_sentinel_hash(
    interpreter_path: str | os.PathLike[str],
) -> int:
    """Measure the build-pinned bound ``sentinel.__hash__()`` value (plan §4.5.8)
    in the frozen interpreter under ``PYTHONHASHSEED=0`` — an interpreter/build
    property, not a caller-chosen value.  The bound-method call bypasses a
    shadowable ``builtins.hash``, mirroring the child's own attestation."""

    completed = subprocess.run(
        [
            os.fspath(interpreter_path),
            "-c",
            "import sys;sys.stdout.write(str(("
            f"{_SENTINEL_STRING!r}).__hash__()))",
        ],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONHASHSEED": "0"},
    )
    return int(completed.stdout.strip())


def build_native_stack_expectations(
    interpreter_path: str | os.PathLike[str],
    *,
    native_stack_modules: Sequence[str],
    profile_integration_sha256: str,
    torch_build_expected: Sequence[str],
    numpy_build_expected: Sequence[str],
    stage_b_expected: Mapping[str, str],
) -> dict[str, Any]:
    """Build the committed R2 native-stack expectation set (external audit
    round-3 revision of F1/F2; external-audit finding 3 adds the sentinel hash).

    The mandatory pre-scientific attestation VALUES are frozen here as committed
    R2 artifacts (not deferred to R2a, which is only the numeric evidence-ceiling
    addendum): the native import list, the frozen `bistar_gp.profile_integration`
    hash, the torch/numpy backend build markers, the Stage-B environment delta,
    the build-pinned bound sentinel `__hash__` value (§4.5.8), and — for F2 — the
    complete set of on-disk regular-file native images loaded by the frozen
    stack, each pinned by `(path, sha256)` (the sha256 subsumes the Mach-O
    linkage identity, since load commands are part of the hashed bytes).
    Measured by importing the stack in the frozen interpreter in a subprocess
    (no scientific evaluation); the author-frozen build/Stage-B markers are
    verified to hold against the measurement before they are committed.
    """

    if _SHA256_RE.fullmatch(profile_integration_sha256) is None:
        raise ValueError("profile_integration_sha256 must be a lowercase sha256")
    expected_sentinel_hash = measure_expected_sentinel_hash(interpreter_path)
    completed = subprocess.run(
        [os.fspath(interpreter_path), "-c", _NATIVE_STACK_MEASURE,
         canonical_dumps(list(native_stack_modules))],
        check=True, capture_output=True, text=True,
    )
    measured = json.loads(completed.stdout)
    for marker in torch_build_expected:
        if marker not in measured["torch_config_show"]:
            raise ValueError(
                f"frozen torch_build_expected marker not present in the "
                f"measured build: {marker!r}"
            )
    for marker in numpy_build_expected:
        if marker not in measured["numpy_config_show"]:
            raise ValueError(
                f"frozen numpy_build_expected marker not present in the "
                f"measured build: {marker!r}"
            )
    if dict(stage_b_expected) != measured["stage_b_env"]:
        raise ValueError(
            "frozen stage_b_expected does not match the measured Stage-B "
            f"environment delta: frozen {dict(stage_b_expected)}, measured "
            f"{measured['stage_b_env']}"
        )
    images = sorted(
        measured["expected_loaded_images"], key=lambda item: item["path"]
    )
    return {
        "kind": "m2cr_native_stack_expectations",
        "schema_version": 1,
        "native_stack_modules": list(native_stack_modules),
        "expected_profile_integration_sha256": profile_integration_sha256,
        "expected_sentinel_hash": expected_sentinel_hash,
        "torch_build_expected": list(torch_build_expected),
        "numpy_build_expected": list(numpy_build_expected),
        "stage_b_expected": dict(stage_b_expected),
        "loaded_image_allowlist": [],
        "expected_loaded_images": images,
    }


def _filter_volatile_pip_freeze(freeze_text: str) -> tuple[str, list[str]]:
    """Drop editable-install lines (and their ``# Editable`` comments) from
    pip-freeze output so the supplementary lock is reproducible across commits.

    An editable install embeds a per-checkout VCS commit
    (``-e git+...@<commit>#egg=<name>``), which made the committed lock stale at
    HEAD (external audit round-3 F4).  Editable installs — the payload's own
    ``bistar_gp`` checkout and other projects' editables — are the volatile
    payload/source layer, and their bytes are carried by the importable-artifact
    manifest and worktree closure, not by this supplementary lock.  The excluded
    egg names are returned for transparency.
    """

    kept: list[str] = []
    excluded: list[str] = []
    for line in freeze_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# Editable install"):
            continue
        if stripped.startswith("-e "):
            excluded.append(
                stripped.split("#egg=", 1)[1] if "#egg=" in stripped else stripped
            )
            continue
        kept.append(line)
    filtered = "\n".join(kept)
    if freeze_text.endswith("\n") and filtered:
        filtered += "\n"
    return filtered, sorted(set(excluded))


def build_dependency_lock(
    interpreter_path: str | os.PathLike[str],
    site_packages: str | os.PathLike[str],
) -> dict[str, Any]:
    """Build the supplementary pip/RECORD/binary-extension dependency lock."""

    completed = subprocess.run(
        [os.fspath(interpreter_path), "-m", "pip", "freeze"],
        check=True,
        capture_output=True,
        text=True,
    )
    filtered_freeze, excluded_editables = _filter_volatile_pip_freeze(
        completed.stdout
    )
    site_path = Path(site_packages)
    dists: list[dict[str, str]] = []
    for record in sorted(site_path.glob("*.dist-info/RECORD"), key=os.fspath):
        name, version = _distribution_identity(record.parent)
        dists.append(
            {
                "name": name,
                "version": version,
                "record_sha256": sha256_file(record),
            }
        )
    dists.sort(key=lambda item: (item["name"].casefold(), item["version"]))
    extensions = [
        entry
        for entry in walk_importable_artifacts([("site-packages", site_path)])
        if entry["artifact_type"] == "extension"
    ]
    extension_hashes = sorted(entry["sha256"] for entry in extensions)
    return {
        "pip_freeze": filtered_freeze,
        "excluded_editable_installs": excluded_editables,
        "dists": dists,
        "binary_extension_count": len(extension_hashes),
        "binary_extensions_sha256": canonical_sha256(extension_hashes),
        "caveats": [
            "RECORD proves listed files' bytes only; it is not a completeness manifest.",
            "RECORD does not cover .pyc (torch's RECORD lists .pyc entries with blank hashes).",
            "This dependency lock is supplementary to the importable-artifact manifest, which carries completeness.",
            "Editable installs are excluded from pip_freeze (they embed a per-checkout VCS commit and are covered by the importable-artifact manifest); their egg names are listed in excluded_editable_installs.",
        ],
    }


def stable_dependency_lock_signature(lock: Mapping[str, Any]) -> dict[str, Any]:
    """The reproducible semantic fields of the dependency lock (external audit
    round-3 F4).

    The dist-info RECORD digests and the binary-extension aggregate reproduce
    across commits and identify the third-party stack; the editable-filtered
    ``pip_freeze`` text and ``excluded_editable_installs`` are informational and
    excluded from the runtime comparison, and the project's own code is bound
    through the worktree/importable-artifact and infrastructure manifests, not
    this lock (avoiding a self-staling embedded commit SHA).
    """

    return {
        "dists": lock.get("dists"),
        "binary_extension_count": lock.get("binary_extension_count"),
        "binary_extensions_sha256": lock.get("binary_extensions_sha256"),
    }


def verify_dependency_lock_semantics(
    committed_lock: Mapping[str, Any],
    interpreter_path: str | os.PathLike[str],
    site_packages: str | os.PathLike[str],
) -> str | None:
    """Recompute the stable semantic dependency-lock fields from the live frozen
    environment and compare to the committed lock (F4 runtime enforcement,
    §4.5.11 "lock metadata").  Returns a fault string on any mismatch, else
    ``None``.
    """

    recomputed = build_dependency_lock(interpreter_path, site_packages)
    if stable_dependency_lock_signature(recomputed) != (
        stable_dependency_lock_signature(committed_lock)
    ):
        return (
            "dependency-lock semantic fields (dist RECORD digests / "
            "binary-extension aggregate) do not match the committed lock"
        )
    return None


def _display_code_path(
    path: Path, repo_root: str | os.PathLike[str] | None
) -> str:
    if not path.is_absolute():
        return path.as_posix()
    base = Path(repo_root) if repo_root is not None else Path.cwd()
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _named_path_items(
    values: Any, repo_root: str | os.PathLike[str] | None = None
) -> list[tuple[str, Any]]:
    if isinstance(values, Mapping):
        return [(str(name), value) for name, value in values.items()]
    return [(_display_code_path(Path(value), repo_root), value) for value in values]


def build_infrastructure_manifest(
    paths: Mapping[str, Any],
    repo_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Build the acyclic Layer-1a manifest over caller-enumerated Layer 0.

    ``paths`` has three categories: ``code`` (mapping from repo-relative path
    to filesystem path, or a path sequence), ``artifacts`` (logical name to
    path), and ``r1_schemas`` (logical name to path).  Integration passes all
    entries in :data:`R2_CODE_RELPATHS`.  Every category uses an exact logical
    key set; missing and extra pins both fail closed.  Repo-contained pins
    are stored repo-relative (see :func:`_stored_pin_path`).
    """

    expected_categories = {"code", "artifacts", "r1_schemas"}
    if set(paths) != expected_categories:
        raise ValueError("paths must contain code, artifacts, and r1_schemas")
    named_code = _named_path_items(paths["code"], repo_root)
    named_artifacts = _named_path_items(paths["artifacts"], repo_root)
    named_r1_schemas = _named_path_items(paths["r1_schemas"], repo_root)
    _require_exact_names("code", named_code, set(R2_CODE_RELPATHS))
    _require_exact_names(
        "artifacts", named_artifacts, set(_INFRASTRUCTURE_ARTIFACT_KEYS)
    )
    _require_exact_names(
        "r1_schemas", named_r1_schemas, set(_INFRASTRUCTURE_R1_SCHEMA_KEYS)
    )
    code: dict[str, dict[str, str]] = {}
    for display, value in sorted(named_code):
        _, file_path = _path_spec(value)
        code[display] = {"sha256": sha256_file(file_path)}

    def pin_named(items: list[tuple[str, Any]]) -> dict[str, dict[str, str]]:
        result: dict[str, dict[str, str]] = {}
        for name, value in sorted(items):
            display, file_path = _path_spec(value)
            stored = (
                display if display is not None else _stored_pin_path(file_path, repo_root)
            )
            if _references_r3_diagnostic_schema(stored) or (
                _references_r3_diagnostic_schema(os.fspath(file_path.resolve()))
            ):
                raise ValueError("the R3 diagnostic schema cannot be pinned by Layer 1a")
            result[name] = {"path": stored, "sha256": sha256_file(file_path)}
        return result

    manifest = {
        "kind": "m2cr_infrastructure_manifest",
        "schema_version": 1,
        "code": code,
        "artifacts": pin_named(named_artifacts),
        "r1_schemas": pin_named(named_r1_schemas),
    }
    return manifest


def _require_exact_names(
    category: str,
    items: list[tuple[str, Any]],
    expected: set[str],
) -> None:
    names = [name for name, _ in items]
    if len(names) != len(expected) or set(names) != expected:
        raise ValueError(
            f"{category} must contain exactly: {', '.join(sorted(expected))}"
        )


def _references_r3_diagnostic_schema(stored_path: str) -> bool:
    return Path(stored_path).name == _R3_DIAGNOSTIC_SCHEMA_BASENAME


def _key_value_pairs(values: Sequence[str], option: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise SystemExit(f"{option} requires NAME=PATH, got {value!r}")
        name, path = value.split("=", 1)
        if not name or not path or name in result:
            raise SystemExit(f"invalid or duplicate {option}: {value!r}")
        result[name] = path
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--generate",
        required=True,
        choices=(
            "importable-artifact-manifest",
            "interpreter-pin",
            "child-env-mapping",
            "preboundary-attestation-set",
            "environment-freeze-manifest",
            "dependency-lock",
            "native-stack-expectations",
            "infrastructure-manifest",
        ),
    )
    parser.add_argument(
        "--v117-freeze",
        default=None,
        help="path to gtoy_profile_freeze_v1.17.json (source of the frozen "
        "profile_integration_sha256 for native-stack-expectations)",
    )
    parser.add_argument("--out", required=True)
    parser.add_argument("--root", action="append", default=[], metavar="ID=PATH")
    parser.add_argument("--interpreter", default=_INTERPRETER)
    parser.add_argument("--site-packages")
    parser.add_argument("--artifact", action="append", default=[], metavar="NAME=PATH")
    parser.add_argument("--code", action="append", default=[], metavar="RELPATH=PATH")
    parser.add_argument("--r1-schema", action="append", default=[], metavar="NAME=PATH")
    parser.add_argument("--bootstrap-closure", action="append", default=[])
    parser.add_argument(
        "--worktree-root",
        default=None,
        help=(
            "worktree root; closure pins resolving inside it are stored "
            "worktree-relative so the set stays launch-invariant (F3)"
        ),
    )
    parser.add_argument("--dyld", default="/usr/lib/dyld")
    parser.add_argument("--dyld-cache-dir", default=_DYLD_CACHE_DIR)
    parser.add_argument(
        "--repo-root",
        default=None,
        help="repository root for repo-relative pin storage (default: discovered)",
    )
    parser.add_argument(
        "--include-hashes", action=argparse.BooleanOptionalAction, default=True
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Generate one explicitly selected freeze artifact."""

    args = _parser().parse_args(argv)
    kind = args.generate
    if kind == "importable-artifact-manifest":
        roots = list(_key_value_pairs(args.root, "--root").items())
        if not roots:
            raise SystemExit("--root ID=PATH is required")
        build_importable_artifact_manifest(roots, args.out)
        return 0
    if kind == "interpreter-pin":
        artifact = build_interpreter_pin(args.interpreter)
    elif kind == "child-env-mapping":
        artifact = build_child_env_mapping()
    elif kind == "preboundary-attestation-set":
        artifact = build_preboundary_attestation_set(
            args.interpreter,
            dyld_path=args.dyld,
            dyld_cache_dir=args.dyld_cache_dir,
            bootstrap_closure_paths=args.bootstrap_closure,
            worktree_root=args.worktree_root,
            include_hashes=args.include_hashes,
        )
    elif kind == "environment-freeze-manifest":
        artifact = build_environment_freeze_manifest(
            _key_value_pairs(args.artifact, "--artifact"),
            repo_root=args.repo_root,
        )
    elif kind == "dependency-lock":
        if not args.site_packages:
            raise SystemExit("--site-packages is required")
        artifact = build_dependency_lock(args.interpreter, args.site_packages)
    elif kind == "native-stack-expectations":
        if not args.v117_freeze:
            raise SystemExit("--v117-freeze is required")
        v117 = json.loads(Path(args.v117_freeze).read_text(encoding="utf-8"))
        profile_sha = v117["algorithm"]["profile_integration_sha256"]
        artifact = build_native_stack_expectations(
            args.interpreter,
            native_stack_modules=R2_NATIVE_STACK_MODULES,
            profile_integration_sha256=profile_sha,
            torch_build_expected=R2_TORCH_BUILD_EXPECTED,
            numpy_build_expected=R2_NUMPY_BUILD_EXPECTED,
            stage_b_expected=R2_STAGE_B_EXPECTED,
        )
    else:
        artifact = build_infrastructure_manifest(
            {
                "code": _key_value_pairs(args.code, "--code"),
                "artifacts": _key_value_pairs(args.artifact, "--artifact"),
                "r1_schemas": _key_value_pairs(args.r1_schema, "--r1-schema"),
            },
            repo_root=args.repo_root,
        )
    atomic_write_canonical_json(args.out, artifact)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
