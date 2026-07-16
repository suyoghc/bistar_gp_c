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

__all__ = [
    "R2_CODE_RELPATHS",
    "R1_SCHEMA_RELPATHS",
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


def _valid_corresponding_source(root: Path, pyc_relpath: str) -> bool:
    parts = pyc_relpath.split("/")
    if len(parts) < 2 or parts[-2] != "__pycache__":
        return False
    tagged_stem = parts[-1][:-4]
    source_stem = tagged_stem.split(".", 1)[0]
    source_parts = parts[:-2] + [source_stem + ".py"]
    source = root.joinpath(*source_parts)
    try:
        target = source.resolve(strict=True)
    except (FileNotFoundError, RuntimeError, OSError):
        return False
    return target.is_file() and _inside(target, root.resolve(strict=True))


def _artifact_type(root: Path, relpath: str) -> str | None:
    name = relpath.rsplit("/", 1)[-1]
    if name.endswith(".py"):
        return "source"
    if any(name.endswith(suffix) for suffix in _EXTENSION_SUFFIXES):
        return "extension"
    if name.endswith(".pyc"):
        if "/__pycache__/" in f"/{relpath}":
            if _valid_corresponding_source(root, relpath):
                return None
            return "orphan_bytecode"
        return "legacy_bytecode"
    if name.endswith(_ARCHIVE_SUFFIXES):
        return "importable_archive"
    return None


def walk_importable_artifacts(
    roots: list[tuple[str, str | os.PathLike[str]]],
) -> Iterator[dict[str, Any]]:
    """Yield the B15(ii)-scoped artifact inventory in canonical order.

    Entries contain exactly ``root``, ``relpath``, ``artifact_type``,
    ``sha256``, and ``size``.  In-root symlinks are recorded under their
    logical path with the resolved target's bytes.  Escaping, broken, and
    cyclic symlinks raise :class:`ValueError` so an inventory cannot silently
    omit an importable spelling.
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
                    "sha256": sha256_file(file_path),
                    "size": file_path.stat().st_size,
                }
            )
    entries.sort(key=lambda entry: (entry["root"], entry["relpath"]))
    yield from entries


def build_importable_artifact_manifest(
    roots: list[tuple[str, str | os.PathLike[str]]],
    out_path: str | os.PathLike[str],
) -> dict[str, Any]:
    """Atomically stream the complete inventory as canonical JSONL."""

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


def _attestation_entry(path: Path, include_hashes: bool) -> dict[str, Any]:
    entry: dict[str, Any] = {"path": os.fspath(path)}
    if include_hashes:
        entry["sha256"] = sha256_file(path)
    return entry


def build_preboundary_attestation_set(
    interpreter_path: str | os.PathLike[str] = _INTERPRETER,
    *,
    dyld_path: str | os.PathLike[str] = "/usr/lib/dyld",
    dyld_cache_dir: str | os.PathLike[str] = _DYLD_CACHE_DIR,
    bootstrap_closure_paths: Iterable[str | os.PathLike[str]] = (),
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
    pattern = re.compile(rf"^{re.escape(_DYLD_CACHE_BASENAME)}\.(\d+)$")
    subcaches_with_index: list[tuple[int, Path]] = []
    for candidate in cache_dir.iterdir():
        match = pattern.fullmatch(candidate.name)
        if match and candidate.is_file():
            subcaches_with_index.append((int(match.group(1)), candidate))
    subcaches = [
        path for _, path in sorted(subcaches_with_index, key=lambda item: item[0])
    ]
    if include_hashes and len(subcaches) != declared_subcache_count:
        raise ValueError(
            "dyld shared-cache subcache count mismatch: "
            f"declared {declared_subcache_count}, discovered {len(subcaches)}"
        )
    closure = sorted((Path(path) for path in bootstrap_closure_paths), key=os.fspath)
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
            _attestation_entry(path, include_hashes) for path in closure
        ],
    }
    if not include_hashes:
        artifact["test_fixture"] = True
    return artifact


def _path_spec(value: Any) -> tuple[str, Path]:
    if isinstance(value, Mapping):
        display = os.fspath(value["path"])
        filesystem_value = value.get("filesystem_path", value["path"])
        return display, Path(filesystem_value)
    display = os.fspath(value)
    return display, Path(value)


def build_environment_freeze_manifest(
    artifact_paths: Mapping[str, Any],
) -> dict[str, Any]:
    """Aggregate and pin exactly the four static v5 freeze artifacts."""

    if set(artifact_paths) != set(_FREEZE_ARTIFACT_KEYS):
        raise ValueError(
            "artifact_paths must contain exactly " + ", ".join(_FREEZE_ARTIFACT_KEYS)
        )
    artifacts: dict[str, dict[str, str]] = {}
    for name in sorted(_FREEZE_ARTIFACT_KEYS):
        display, path = _path_spec(artifact_paths[name])
        if _parsed_content_is_test_fixture(path):
            raise ValueError(
                f"freeze manifest cannot pin test-fixture artifact: {display}"
            )
        artifacts[name] = {"path": display, "sha256": sha256_file(path)}
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
        for entry in walk_importable_artifacts([("site_packages", site_path)])
        if entry["artifact_type"] == "extension"
    ]
    extension_hashes = sorted(entry["sha256"] for entry in extensions)
    return {
        "pip_freeze": completed.stdout,
        "dists": dists,
        "binary_extension_count": len(extension_hashes),
        "binary_extensions_sha256": canonical_sha256(extension_hashes),
        "caveats": [
            "RECORD proves listed files' bytes only; it is not a completeness manifest.",
            "RECORD does not cover .pyc (torch's RECORD lists .pyc entries with blank hashes).",
            "This dependency lock is supplementary to the importable-artifact manifest, which carries completeness.",
        ],
    }


def _display_code_path(path: Path) -> str:
    if not path.is_absolute():
        return path.as_posix()
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _named_path_items(values: Any) -> list[tuple[str, Any]]:
    if isinstance(values, Mapping):
        return [(str(name), value) for name, value in values.items()]
    return [(_display_code_path(Path(value)), value) for value in values]


def build_infrastructure_manifest(paths: Mapping[str, Any]) -> dict[str, Any]:
    """Build the acyclic Layer-1a manifest over caller-enumerated Layer 0.

    ``paths`` has three categories: ``code`` (mapping from repo-relative path
    to filesystem path, or a path sequence), ``artifacts`` (logical name to
    path), and ``r1_schemas`` (logical name to path).  Integration passes all
    entries in :data:`R2_CODE_RELPATHS`.  Every category uses an exact logical
    key set; missing and extra pins both fail closed.
    """

    expected_categories = {"code", "artifacts", "r1_schemas"}
    if set(paths) != expected_categories:
        raise ValueError("paths must contain code, artifacts, and r1_schemas")
    named_code = _named_path_items(paths["code"])
    named_artifacts = _named_path_items(paths["artifacts"])
    named_r1_schemas = _named_path_items(paths["r1_schemas"])
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
            if _references_r3_diagnostic_schema(display) or (
                _references_r3_diagnostic_schema(os.fspath(file_path.resolve()))
            ):
                raise ValueError("the R3 diagnostic schema cannot be pinned by Layer 1a")
            result[name] = {"path": display, "sha256": sha256_file(file_path)}
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
            "infrastructure-manifest",
        ),
    )
    parser.add_argument("--out", required=True)
    parser.add_argument("--root", action="append", default=[], metavar="ID=PATH")
    parser.add_argument("--interpreter", default=_INTERPRETER)
    parser.add_argument("--site-packages")
    parser.add_argument("--artifact", action="append", default=[], metavar="NAME=PATH")
    parser.add_argument("--code", action="append", default=[], metavar="RELPATH=PATH")
    parser.add_argument("--r1-schema", action="append", default=[], metavar="NAME=PATH")
    parser.add_argument("--bootstrap-closure", action="append", default=[])
    parser.add_argument("--dyld", default="/usr/lib/dyld")
    parser.add_argument("--dyld-cache-dir", default=_DYLD_CACHE_DIR)
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
            include_hashes=args.include_hashes,
        )
    elif kind == "environment-freeze-manifest":
        artifact = build_environment_freeze_manifest(
            _key_value_pairs(args.artifact, "--artifact")
        )
    elif kind == "dependency-lock":
        if not args.site_packages:
            raise SystemExit("--site-packages is required")
        artifact = build_dependency_lock(args.interpreter, args.site_packages)
    else:
        artifact = build_infrastructure_manifest(
            {
                "code": _key_value_pairs(args.code, "--code"),
                "artifacts": _key_value_pairs(args.artifact, "--artifact"),
                "r1_schemas": _key_value_pairs(args.r1_schema, "--r1-schema"),
            }
        )
    atomic_write_canonical_json(args.out, artifact)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
