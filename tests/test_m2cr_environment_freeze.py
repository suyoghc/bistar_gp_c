"""Hermetic tests for the M2cR static environment-freeze generators."""

from __future__ import annotations

import importlib.machinery
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from bistar_gp.m2cr.environment_freeze import (
    build_child_env_mapping,
    build_dependency_lock,
    build_environment_freeze_manifest,
    build_importable_artifact_manifest,
    build_interpreter_pin,
    build_preboundary_attestation_set,
    classify_pyc_candidate,
    read_manifest_header,
    walk_importable_artifacts,
)
from bistar_gp.m2cr.serialization import (
    atomic_write_canonical_json,
    canonical_bytes,
    canonical_sha256,
    sha256_file,
)


def _write(path: Path, data: bytes = b"x") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def _synthetic_import_tree(root: Path) -> None:
    _write(root / "pkg/module.py", b"source")
    _write(root / "pkg/__pycache__/module.cpython-313.pyc", b"matched")
    _write(root / "pkg/__pycache__/orphan.any-tag.pyc", b"orphan")
    _write(root / "pkg/legacy.pyc", b"legacy")
    extension_suffix = importlib.machinery.EXTENSION_SUFFIXES[0]
    _write(root / f"pkg/native{extension_suffix}", b"extension")
    _write(root / "vendor.zip", b"archive")
    _write(root / "not-importable.txt", b"ignored")


def test_walker_classifies_b15ii_scope_exactly(tmp_path: Path):
    root = tmp_path / "root"
    _synthetic_import_tree(root)
    entries = list(walk_importable_artifacts([("fake", root)]))
    by_path = {entry["relpath"]: entry for entry in entries}

    assert "pkg/module.py" in by_path
    assert by_path["pkg/module.py"]["artifact_type"] == "source"
    assert by_path["pkg/module.py"]["loader"] == "SourceFileLoader"
    assert "pkg/__pycache__/module.cpython-313.pyc" not in by_path
    assert by_path["pkg/__pycache__/orphan.any-tag.pyc"]["artifact_type"] == (
        "orphan_bytecode"
    )
    assert by_path["pkg/__pycache__/orphan.any-tag.pyc"]["loader"] == (
        "SourcelessFileLoader"
    )
    assert by_path["pkg/legacy.pyc"]["artifact_type"] == "legacy_bytecode"
    assert by_path["pkg/legacy.pyc"]["loader"] == "SourcelessFileLoader"
    extension = next(
        entry for entry in entries if entry["artifact_type"] == "extension"
    )
    assert extension["sha256"] == sha256_file(root / extension["relpath"])
    assert extension["loader"] == "ExtensionFileLoader"
    assert by_path["vendor.zip"]["artifact_type"] == "importable_archive"
    assert by_path["vendor.zip"]["loader"] == "zipimporter"
    assert list(by_path) == sorted(by_path)
    assert all(
        set(entry) == {"root", "relpath", "artifact_type", "loader", "sha256", "size"}
        for entry in entries
    )


def test_pyc_classification_handles_dotted_stems_pytest_tags_orphans_legacy_plain(
    tmp_path: Path,
):
    """Fix A1: dotted source stems and dotted (pytest) cache tags are
    source-backed; true orphans, legacy, and plain stems classify exactly."""

    root = tmp_path / "root"
    _write(root / "pkg/v0.9.0.a.py", b"dotted-stem source")
    _write(root / "pkg/__pycache__/v0.9.0.a.cpython-313.pyc", b"dotted cache")
    _write(root / "pkg/mod.py", b"module source")
    _write(root / "pkg/__pycache__/mod.cpython-313-pytest-8.3.3.pyc", b"pytest cache")
    _write(root / "pkg/plain.py", b"plain source")
    _write(root / "pkg/__pycache__/plain.cpython-313.pyc", b"plain cache")
    _write(root / "pkg/__pycache__/untagged.pyc", b"untagged cache")
    _write(root / "pkg/untagged.py", b"untagged source")
    _write(root / "pkg/__pycache__/orphan.cpython-313.pyc", b"true orphan")
    _write(root / "pkg/legacy.pyc", b"legacy")

    backed = (
        "pkg/__pycache__/v0.9.0.a.cpython-313.pyc",
        "pkg/__pycache__/mod.cpython-313-pytest-8.3.3.pyc",
        "pkg/__pycache__/plain.cpython-313.pyc",
        "pkg/__pycache__/untagged.pyc",
    )
    for relpath in backed:
        assert classify_pyc_candidate(root, relpath) is None, relpath
    assert classify_pyc_candidate(root, "pkg/__pycache__/orphan.cpython-313.pyc") == (
        "orphan_bytecode"
    )
    assert classify_pyc_candidate(root, "pkg/legacy.pyc") == "legacy_bytecode"
    assert classify_pyc_candidate(root, "pkg/mod.py") is None

    included = {
        entry["relpath"]: entry["artifact_type"]
        for entry in walk_importable_artifacts([("fake", root)])
        if entry["relpath"].endswith(".pyc")
    }
    assert included == {
        "pkg/__pycache__/orphan.cpython-313.pyc": "orphan_bytecode",
        "pkg/legacy.pyc": "legacy_bytecode",
    }


def test_numpy_distributor_local_addition_changes_set_and_manifest_digest(
    tmp_path: Path,
):
    site = tmp_path / "site-packages"
    _write(site / "numpy/__init__.py", b"from . import _distributor_init\n")
    _write(site / "numpy/_distributor_init.py", b"pass\n")
    before_path = tmp_path / "before.jsonl"
    before = build_importable_artifact_manifest([("site", site)], before_path)
    before_set = {
        entry["relpath"] for entry in walk_importable_artifacts([("site", site)])
    }

    local = _write(site / "numpy/_distributor_init_local.py", b"configured = True\n")
    after_path = tmp_path / "after.jsonl"
    after = build_importable_artifact_manifest([("site", site)], after_path)
    after_set = {
        entry["relpath"] for entry in walk_importable_artifacts([("site", site)])
    }
    assert after_set - before_set == {"numpy/_distributor_init_local.py"}
    assert before_set - after_set == set()
    assert after["sha256_of_manifest"] != before["sha256_of_manifest"]

    local.unlink()
    restored_path = tmp_path / "restored.jsonl"
    restored = build_importable_artifact_manifest([("site", site)], restored_path)
    restored_set = {
        entry["relpath"] for entry in walk_importable_artifacts([("site", site)])
    }
    assert before_set - restored_set == set()
    assert restored_set == before_set
    assert restored["sha256_of_manifest"] == before["sha256_of_manifest"]


def test_manifest_generation_is_byte_deterministic(tmp_path: Path):
    root = tmp_path / "root"
    _synthetic_import_tree(root)
    first_path = tmp_path / "first.jsonl"
    second_path = tmp_path / "second.jsonl"
    first = build_importable_artifact_manifest([("root", root)], first_path)
    second = build_importable_artifact_manifest([("root", root)], second_path)
    assert first == second
    assert first_path.read_bytes() == second_path.read_bytes()
    assert first["total_bytes_of_manifest"] == len(first_path.read_bytes())
    assert first["sha256_of_manifest"] == sha256_file(first_path)


def test_manifest_opens_with_v2_header_carrying_resolved_roots(tmp_path: Path):
    root = tmp_path / "root"
    _synthetic_import_tree(root)
    manifest_path = tmp_path / "manifest.jsonl"
    summary = build_importable_artifact_manifest([("fake", root)], manifest_path)
    lines = manifest_path.read_text(encoding="utf-8").splitlines()
    header = json.loads(lines[0])
    assert header == {
        "kind": "m2cr_importable_artifact_manifest",
        "schema_version": 2,
        "roots": {"fake": os.fspath(root.resolve())},
    }
    assert read_manifest_header(manifest_path) == header
    entries = [json.loads(line) for line in lines[1:]]
    assert summary["total_entries"] == len(entries)
    assert {entry["loader"] for entry in entries} == {
        "SourceFileLoader",
        "SourcelessFileLoader",
        "ExtensionFileLoader",
        "zipimporter",
    }


def test_read_manifest_header_rejects_headerless_or_malformed_first_line(
    tmp_path: Path,
):
    headerless = tmp_path / "v1.jsonl"
    headerless.write_text(
        '{"artifact_type":"source","relpath":"a.py"}\n', encoding="utf-8"
    )
    with pytest.raises(ValueError, match="wrong kind"):
        read_manifest_header(headerless)
    malformed = tmp_path / "broken.jsonl"
    malformed.write_text("not json\n", encoding="utf-8")
    with pytest.raises(ValueError, match="not valid JSON"):
        read_manifest_header(malformed)
    relative_roots = tmp_path / "relative.jsonl"
    relative_roots.write_text(
        '{"kind":"m2cr_importable_artifact_manifest","roots":{"stdlib":"lib"},'
        '"schema_version":2}\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="absolute resolved paths"):
        read_manifest_header(relative_roots)


def test_symlink_escape_fails_closed_with_offending_path(tmp_path: Path):
    root = tmp_path / "root"
    root.mkdir()
    outside = _write(tmp_path / "outside.py", b"outside")
    (root / "escape.py").symlink_to(outside)
    with pytest.raises(ValueError, match="escape\\.py"):
        list(walk_importable_artifacts([("root", root)]))


def test_broken_and_cyclic_symlinks_fail_closed(tmp_path: Path):
    broken_root = tmp_path / "broken-root"
    broken_root.mkdir()
    (broken_root / "broken.py").symlink_to(tmp_path / "missing.py")
    with pytest.raises(ValueError, match="broken\\.py"):
        list(walk_importable_artifacts([("root", broken_root)]))

    cyclic_root = tmp_path / "cyclic-root"
    cyclic_root.mkdir()
    (cyclic_root / "cycle").symlink_to(cyclic_root)
    with pytest.raises(ValueError, match="cycle"):
        list(walk_importable_artifacts([("root", cyclic_root)]))


def test_child_environment_mapping_matches_frozen_table_exactly():
    mapping = build_child_env_mapping()
    assert mapping["fixed"] == {
        "PYTHONHASHSEED": "0",
        "OMP_NUM_THREADS": "10",
        "OMP_DYNAMIC": "FALSE",
        "MKL_NUM_THREADS": "10",
        "VECLIB_MAXIMUM_THREADS": "10",
        "LC_ALL": "C",
        "TZ": "UTC",
        "PATH": "/usr/bin:/bin",
    }
    assert mapping["run_local_keys"] == [
        "HOME",
        "TMPDIR",
        "XDG_CACHE_HOME",
        "XDG_CONFIG_HOME",
        "XDG_DATA_HOME",
        "XDG_STATE_HOME",
    ]
    assert mapping["path_policy"] == "minimal"
    assert mapping["excluded_prefixes"] == ["PYTHON (all others)", "DYLD_"]
    serialized = canonical_bytes(mapping)
    assert b"OPENBLAS_NUM_THREADS" in serialized
    assert b'"OPENBLAS_NUM_THREADS"' not in canonical_bytes(mapping["fixed"])
    assert b"empirically inert" in serialized
    assert b"ATen precedence" in serialized
    assert b"LC_CTYPE expected absent" in serialized
    assert b"utf8_mode==1 recorded" in serialized


def test_aggregate_manifest_pins_four_artifacts_without_self_digest(tmp_path: Path):
    names = (
        "child_env_mapping",
        "importable_artifact_manifest",
        "interpreter_pin",
        "preboundary_attestation_set",
    )
    paths = {}
    for name in names:
        path = tmp_path / f"{name}.json"
        atomic_write_canonical_json(path, {"kind": name})
        paths[name] = path
    manifest = build_environment_freeze_manifest(paths)
    assert manifest["kind"] == "m2cr_environment_freeze_manifest"
    assert set(manifest["artifacts"]) == set(names)
    for name, path in paths.items():
        # Outside any repository the pin stays absolute (host-global rule).
        assert manifest["artifacts"][name] == {
            "path": os.fspath(path.resolve()),
            "sha256": sha256_file(path),
        }
    data = canonical_bytes(manifest)
    own_digest = canonical_sha256(manifest).encode("ascii")
    assert own_digest not in data
    assert b"environment_freeze_manifest_sha256" not in data


def test_freeze_manifest_stores_repo_relative_pins_for_repo_contained_files(
    tmp_path: Path,
):
    """Fix A9: repo-contained pins are repo-relative; host-global pins stay
    absolute, so a regenerated manifest verifies inside any worktree."""

    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    names = (
        "child_env_mapping",
        "importable_artifact_manifest",
        "interpreter_pin",
        "preboundary_attestation_set",
    )
    paths: dict[str, Path] = {}
    for name in names[:-1]:
        path = repo / "docs" / f"{name}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_canonical_json(path, {"kind": name})
        paths[name] = path
    outside = tmp_path / "host-global.json"
    atomic_write_canonical_json(outside, {"kind": names[-1]})
    paths[names[-1]] = outside

    discovered = build_environment_freeze_manifest(paths)
    explicit = build_environment_freeze_manifest(paths, repo_root=repo)
    for manifest in (discovered, explicit):
        for name in names[:-1]:
            assert manifest["artifacts"][name]["path"] == f"docs/{name}.json"
        assert Path(manifest["artifacts"][names[-1]]["path"]).is_absolute()


def test_interpreter_pin_probes_target_process_and_hashes_resolved_binary():
    pin = build_interpreter_pin(sys.executable)
    assert pin["path"] == sys.executable
    assert pin["realpath"] == os.path.realpath(sys.executable)
    assert pin["version"]["implementation"] == sys.implementation.name
    assert pin["version"]["version_info"][:3] == list(sys.version_info[:3])
    assert pin["version"]["version_string"] == sys.version
    assert pin["sha256"] == sha256_file(pin["realpath"])


def test_preboundary_attestation_enumerates_all_declared_cache_siblings(
    tmp_path: Path,
):
    interpreter = _write(tmp_path / "python", b"interpreter")
    dyld = _write(tmp_path / "dyld", b"dyld")
    cache_dir = tmp_path / "caches"
    _write(cache_dir / "dyld_shared_cache_arm64e", b"main")
    _write(cache_dir / "dyld_shared_cache_arm64e.02", b"two")
    _write(cache_dir / "dyld_shared_cache_arm64e.1", b"one")
    _write(cache_dir / "dyld_shared_cache_x86_64", b"other")
    bootstrap = _write(tmp_path / "bootstrap.py", b"bootstrap")
    stdlib = _write(tmp_path / "stdlib.py", b"stdlib")

    artifact = build_preboundary_attestation_set(
        interpreter,
        dyld_path=dyld,
        dyld_cache_dir=cache_dir,
        bootstrap_closure_paths=[stdlib, bootstrap],
        declared_subcache_count=2,
    )
    cache = artifact["dyld_shared_cache"]
    assert cache["declared_subcache_count"] == 2
    assert cache["discovered_subcache_count"] == 2
    assert [Path(item["path"]).name for item in cache["subcaches"]] == [
        "dyld_shared_cache_arm64e.1",
        "dyld_shared_cache_arm64e.02",
    ]
    assert all("sha256" in item for item in cache["subcaches"])
    assert [item["path"] for item in artifact["bootstrap_closure"]] == sorted(
        [os.fspath(bootstrap), os.fspath(stdlib)]
    )


def test_real_attestation_rejects_declared_subcache_mismatch(tmp_path: Path):
    interpreter = _write(tmp_path / "python", b"interpreter")
    dyld = _write(tmp_path / "dyld", b"dyld")
    cache_dir = tmp_path / "caches"
    _write(cache_dir / "dyld_shared_cache_arm64e", b"main")
    _write(cache_dir / "dyld_shared_cache_arm64e.1", b"one")
    with pytest.raises(ValueError, match="declared 2, discovered 1"):
        build_preboundary_attestation_set(
            interpreter,
            dyld_path=dyld,
            dyld_cache_dir=cache_dir,
            declared_subcache_count=2,
        )


def test_hashless_attestation_is_fixture_only_and_cannot_be_frozen(
    tmp_path: Path,
):
    interpreter = _write(tmp_path / "python", b"interpreter")
    dyld = _write(tmp_path / "dyld", b"dyld")
    cache_dir = tmp_path / "caches"
    _write(cache_dir / "dyld_shared_cache_arm64e", b"main")
    fixture = build_preboundary_attestation_set(
        interpreter,
        dyld_path=dyld,
        dyld_cache_dir=cache_dir,
        include_hashes=False,
    )
    assert fixture["test_fixture"] is True
    assert "sha256" not in fixture["interpreter_binary"]

    paths = {}
    for name in (
        "child_env_mapping",
        "importable_artifact_manifest",
        "interpreter_pin",
        "preboundary_attestation_set",
    ):
        path = tmp_path / f"{name}.json"
        atomic_write_canonical_json(
            path,
            fixture if name == "preboundary_attestation_set" else {"kind": name},
        )
        paths[name] = path
    with pytest.raises(ValueError, match="test-fixture artifact"):
        build_environment_freeze_manifest(paths)


def test_dependency_lock_hashes_records_and_sorted_extension_hashes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    site = tmp_path / "site-packages"
    first = site / "Alpha-1.2.dist-info"
    second = site / "beta_pkg-2.0.dist-info"
    _write(first / "METADATA", b"Name: Alpha\nVersion: 1.2\n")
    first_record = _write(first / "RECORD", b"alpha.py,sha256=x,1\n")
    second_record = _write(second / "RECORD", b"beta.py,,\n")
    extension_suffix = importlib.machinery.EXTENSION_SUFFIXES[0]
    extension = _write(site / f"alpha/native{extension_suffix}", b"native")

    def fake_run(*args, **kwargs):
        assert args[0] == ["/fake/python", "-m", "pip", "freeze"]
        assert kwargs["check"] and kwargs["capture_output"] and kwargs["text"]
        return SimpleNamespace(stdout="Alpha==1.2\nbeta-pkg==2.0\n")

    monkeypatch.setattr(subprocess, "run", fake_run)
    lock = build_dependency_lock("/fake/python", site)
    assert lock["pip_freeze"] == "Alpha==1.2\nbeta-pkg==2.0\n"
    assert lock["dists"] == [
        {"name": "Alpha", "version": "1.2", "record_sha256": sha256_file(first_record)},
        {
            "name": "beta_pkg",
            "version": "2.0",
            "record_sha256": sha256_file(second_record),
        },
    ]
    assert lock["binary_extension_count"] == 1
    assert lock["binary_extensions_sha256"] == canonical_sha256(
        [sha256_file(extension)]
    )
    caveats = " ".join(lock["caveats"])
    assert "listed files' bytes only" in caveats
    assert "not a completeness manifest" in caveats
    assert "does not cover .pyc" in caveats
    assert "supplementary to the importable-artifact manifest" in caveats
    assert lock["excluded_editable_installs"] == []


def test_editable_installs_are_excluded_from_pip_freeze() -> None:
    """F4: editable installs embed a per-checkout VCS commit, so they are
    dropped from the lock's pip_freeze (making it reproducible) and reported by
    egg name; the scientific-stack pins remain."""

    from bistar_gp.m2cr.environment_freeze import _filter_volatile_pip_freeze

    freeze = (
        "numpy==1.26.4\n"
        "-e git+https://example.com/bistar_gp_c.git@1cdb08a8#egg=bistar_gp\n"
        "# Editable install with no version control (other==0.1.0)\n"
        "-e /path/to/other\n"
        "torch==2.10.0\n"
        "-e git+https://example.com/ac.git@15e6c36#egg=antagonistic_collab\n"
    )
    filtered, excluded = _filter_volatile_pip_freeze(freeze)
    assert filtered == "numpy==1.26.4\ntorch==2.10.0\n"
    assert "-e " not in filtered and "@1cdb08a8" not in filtered
    assert excluded == ["-e /path/to/other", "antagonistic_collab", "bistar_gp"]


def test_committed_dependency_lock_reproduces_at_head() -> None:
    """F4: the committed dependency lock recomputes from the frozen
    environment — its reproducible signature (dists RECORD digests, binary
    extension aggregate, editable-free pip_freeze) matches — so a stale lock
    (external audit round-3 F4a) is caught by CI."""

    interpreter = "/opt/homebrew/Caskroom/miniconda/base/bin/python3.13"
    site_packages = Path(
        "/opt/homebrew/Caskroom/miniconda/base/lib/python3.13/site-packages"
    )
    committed_path = (
        Path(__file__).resolve().parents[1]
        / "docs/m2c_freeze/m2cr_dependency_lock_v1.json"
    )
    if not Path(interpreter).exists() or not site_packages.is_dir():
        pytest.skip("Miniconda base environment not present")
    if not committed_path.is_file():
        pytest.skip("committed dependency lock not present")
    committed = json.loads(committed_path.read_text(encoding="utf-8"))
    assert "-e " not in committed["pip_freeze"]  # no volatile editable line
    recomputed = build_dependency_lock(interpreter, site_packages)
    assert recomputed["dists"] == committed["dists"]
    assert (
        recomputed["binary_extensions_sha256"]
        == committed["binary_extensions_sha256"]
    )
    assert recomputed["pip_freeze"] == committed["pip_freeze"]


@pytest.mark.skipif(
    not os.environ.get("M2CR_FULL_FREEZE_TESTS"),
    reason="set M2CR_FULL_FREEZE_TESTS to walk the real multi-gigabyte freeze roots",
)
def test_optional_real_root_walk_is_explicitly_opt_in():
    root = Path("/opt/homebrew/Caskroom/miniconda/base/lib/python3.13")
    assert any(walk_importable_artifacts([("stdlib", root)]))


def test_nested_roots_claim_each_artifact_exactly_once(tmp_path):
    """lib-dynload and site-packages nest inside the stdlib root on disk;
    every artifact must appear under exactly its most specific root."""

    from bistar_gp.m2cr.environment_freeze import walk_importable_artifacts

    stdlib = tmp_path / "lib" / "python3.13"
    dynload = stdlib / "lib-dynload"
    site = stdlib / "site-packages"
    for directory in (stdlib, dynload, site):
        directory.mkdir(parents=True)
    (stdlib / "os_like.py").write_text("STDLIB = True\n")
    (dynload / "fast.cpython-313-darwin.so").write_bytes(b"\x00ext")
    (site / "pkg.py").write_text("PKG = True\n")

    entries = list(
        walk_importable_artifacts(
            [
                ("stdlib", stdlib),
                ("lib-dynload", dynload),
                ("site-packages", site),
            ]
        )
    )
    claimed = [(entry["root"], entry["relpath"]) for entry in entries]
    assert claimed == [
        ("lib-dynload", "fast.cpython-313-darwin.so"),
        ("site-packages", "pkg.py"),
        ("stdlib", "os_like.py"),
    ]
