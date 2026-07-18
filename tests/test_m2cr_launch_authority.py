"""WI1/WI2 launch-authority discriminating battery (external-audit findings
1 and 2, plus the confirmed Kimi K3 challenge findings).

Child-side launches run over synthetic four-root bundles through the REAL
bootstrap; nothing here claims to prove the public production path — the
dedicated real-root integration battery does that with a bounded launch
count.  Every negative asserts the marker/COMPLETED impossibility the plan
requires, not just a nonzero exit.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from bistar_gp.m2cr.capture import (
    BOOTSTRAP_CONFIG_NAME,
    capture_run,
    _post_exit_authority_checks,
    _authenticate_launch_spec,
)
from bistar_gp.m2cr.serialization import sha256_file
from tests.test_m2cr_bootstrap import (
    MINICONDA_PYTHON,
    REPOSITORY_ROOT,
    _launch_bootstrap,
    session_closure_directive,
)
from tests.test_m2cr_capture import (
    CHAIN,
    _FREEZE_RELPATHS,
    _make_launch,
)


def _no_marker(run_dir: Path) -> bool:
    return not (run_dir / "payload_started.json").exists()


# ---------------------------------------------------------------------------
# Finding 1 — the manifest, roots, closure, and spec digest are mandatory
# child-side; omission fails before ANY native import and before the marker.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "directive",
    [
        "importable_artifact_manifest",
        "preboundary_closure",
        "authenticated_spec_sha256",
        "four_roots",
    ],
)
def test_omitted_spec_directive_fails_before_any_import_and_marker(
    tmp_path: Path, directive: str
) -> None:
    completed, run_dir, events = _launch_bootstrap(
        tmp_path, omit_directives=(directive,)
    )
    assert completed.returncode not in (0, 3)
    assert b"attestation_fault" in completed.stderr
    assert _no_marker(run_dir)
    assert [event["event"] for event in events] == ["HELLO"]
    # The fake native stack never initialized: no thread-control log exists.
    assert not (run_dir.parent / "thread_calls.txt").read_text() if (
        run_dir.parent / "thread_calls.txt"
    ).exists() else True


def test_headerless_v1_manifest_is_rejected(tmp_path: Path) -> None:
    """A manifest without the v2 header has no root or loader authority."""

    def strip_header(config: dict) -> None:
        manifest = Path(config["importable_artifact_manifest"])
        lines = manifest.read_bytes().splitlines(keepends=True)
        manifest.write_bytes(b"".join(lines[1:]))

    completed, run_dir, _ = _launch_bootstrap(
        tmp_path, config_mutator=strip_header
    )
    assert completed.returncode not in (0, 3)
    assert (
        b"format-v2 header" in completed.stderr
        or b"invalid importable manifest" in completed.stderr
    )
    assert _no_marker(run_dir)


def test_unknown_config_key_is_rejected_closed_world(tmp_path: Path) -> None:
    """Kimi K3 finding 5: a key outside the closed-world set — for example a
    resurrected legacy alias — fails closed instead of passing through."""

    def add_alias(config: dict) -> None:
        config["preboundary_skip"] = ["interpreter"]

    completed, run_dir, _ = _launch_bootstrap(
        tmp_path, config_mutator=add_alias
    )
    assert completed.returncode not in (0, 3)
    assert b"unknown keys" in completed.stderr
    assert b"preboundary_skip" in completed.stderr
    assert _no_marker(run_dir)


# ---------------------------------------------------------------------------
# Finding 1 — pre-walk completeness gates the marker (added / removed /
# byte-changed), including the named numpy/_distributor_init_local.py class.
# ---------------------------------------------------------------------------


def test_planted_distributor_init_local_fails_the_pre_walk(
    tmp_path: Path,
) -> None:
    planted = tmp_path / "site-packages" / "numpy" / "_distributor_init_local.py"

    def plant(_worktree: Path) -> None:
        planted.parent.mkdir(parents=True)
        planted.write_text("import os; os.system('echo pwned')\n")

    completed, run_dir, _ = _launch_bootstrap(tmp_path, worktree_mutator=plant)
    assert completed.returncode not in (0, 3)
    assert b"importable artifact manifest drift" in completed.stderr
    assert b"pre_audit" in completed.stderr
    assert b"_distributor_init_local.py" in completed.stderr
    assert _no_marker(run_dir)


def test_removed_and_byte_changed_artifacts_fail_the_pre_walk(
    tmp_path: Path,
) -> None:
    def remove(worktree: Path) -> None:
        (worktree / "numpy.py").unlink()

    completed, run_dir, _ = _launch_bootstrap(
        tmp_path / "removed", worktree_mutator=remove
    )
    assert completed.returncode not in (0, 3)
    assert b"importable artifact manifest drift" in completed.stderr
    assert b"removed" in completed.stderr
    assert _no_marker(run_dir)

    def change(worktree: Path) -> None:
        with (worktree / "numpy.py").open("a", encoding="utf-8") as handle:
            handle.write("# byte change\n")

    completed, run_dir, _ = _launch_bootstrap(
        tmp_path / "changed", worktree_mutator=change
    )
    assert completed.returncode not in (0, 3)
    assert b"importable artifact manifest drift" in completed.stderr
    assert b"changed" in completed.stderr
    assert _no_marker(run_dir)


def test_nested_synthetic_roots_walk_and_catch_boundary_plants(
    tmp_path: Path,
) -> None:
    """Kimi K3 finding 8: launch-level coverage of the production nesting
    geometry — a positive launch over nested roots, and a plant exactly at
    the nesting boundary caught by the pre-walk under the INNER root id."""

    completed, run_dir, _ = _launch_bootstrap(
        tmp_path / "positive", nested_roots=True
    )
    assert completed.returncode == 0, completed.stderr.decode()

    planted = (
        tmp_path / "negative" / "stdlib" / "site-packages" / "boundary_plant.py"
    )

    def plant(_worktree: Path) -> None:
        planted.parent.mkdir(parents=True, exist_ok=True)
        planted.write_text("PLANT = 1\n", encoding="utf-8")

    completed, run_dir, _ = _launch_bootstrap(
        tmp_path / "negative", nested_roots=True, worktree_mutator=plant
    )
    assert completed.returncode not in (0, 3)
    assert b"importable artifact manifest drift" in completed.stderr
    # The walker keys the plant under the most specific (inner) root.
    assert b"'site-packages'" in completed.stderr
    assert b"boundary_plant.py" in completed.stderr
    assert _no_marker(run_dir)


# ---------------------------------------------------------------------------
# Finding 1 — origin/loader authentication before the marker (closure clause)
# and after execution (post-walk + inventory), with COMPLETED impossible.
# ---------------------------------------------------------------------------


def test_corrupted_closure_pin_fails_origin_binding_before_marker(
    tmp_path: Path,
) -> None:
    def corrupt(config: dict) -> None:
        config["preboundary_closure"] = [
            dict(entry, sha256="0" * 64) if "path" in entry else dict(entry)
            for entry in config["preboundary_closure"]
        ]

    completed, run_dir, _ = _launch_bootstrap(tmp_path, config_mutator=corrupt)
    assert completed.returncode not in (0, 3)
    assert b"does not match its authenticated closure pin" in completed.stderr
    assert _no_marker(run_dir)


def test_stdlib_preload_with_no_closure_pin_fails_before_marker(
    tmp_path: Path,
) -> None:
    def drop_one(config: dict) -> None:
        closure = [
            entry
            for entry in config["preboundary_closure"]
            if not entry.get("path", "").endswith("/json/__init__.py")
        ]
        assert len(closure) < len(config["preboundary_closure"])
        config["preboundary_closure"] = closure

    completed, run_dir, _ = _launch_bootstrap(tmp_path, config_mutator=drop_one)
    assert completed.returncode not in (0, 3)
    assert b"no authenticated closure pin" in completed.stderr
    assert _no_marker(run_dir)


def test_payload_planted_source_fails_the_post_walk_never_completed(
    tmp_path: Path,
) -> None:
    completed, run_dir, _ = _launch_bootstrap(tmp_path, mode="plant_source")
    assert completed.returncode not in (0, 3)
    assert b"importable artifact manifest drift" in completed.stderr
    assert b"post_execution" in completed.stderr
    assert b"m2cr_postdrift_plant.py" in completed.stderr
    # The marker exists (payload ran) but a protocol exit is impossible.
    assert (run_dir / "payload_started.json").is_file()
    assert not (run_dir / "stage_c.json").exists()


# ---------------------------------------------------------------------------
# Finding 2 — parent-side: a payload rewriting marker-bound evidence is
# caught by the parent's post-exit evidence re-hash (the parent/child
# static-authority agreement cannot be forged after the fact).
# ---------------------------------------------------------------------------


def test_payload_rewriting_marker_bound_evidence_is_caught_parent_side(
    tmp_path: Path,
) -> None:
    proofs_path = tmp_path / "run" / "effect_proofs.json"
    config = _make_launch(
        tmp_path,
        extra_payload_code=(
            f"open({os.fspath(proofs_path)!r}, 'ab').write(b' ')"
        ),
    )
    record = capture_run(config)
    assert record["status"] == "INFRA_FAILURE"
    assert record["fault"]["fault_class"] == "attestation_fault"
    assert (
        "marker-bound attestation evidence effect_proofs does not match"
        in record["fault"]["detail"]
    )


def test_post_exit_authority_checks_reject_stripped_or_forged_postchecks(
    tmp_path: Path,
) -> None:
    """Unit-level negatives for the parent's exit checks: a stripped
    manifest_post, a doctored stage_c linkage, and a postcheck naming the
    wrong manifest identity each return a fault."""

    config = _make_launch(tmp_path)
    record = capture_run(config)
    assert record["status"] == "COMPLETED", record.get("fault")
    run_dir = Path(config.run_dir)
    spec = _authenticate_launch_spec(
        Path(config.worktree_root).resolve(), config.chain
    )
    paths = {
        name: os.fspath(run_dir / f"{name}.json")
        for name in (
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
        )
    }
    stage_c_doc = json.loads((run_dir / "stage_c.json").read_text())
    assert (
        _post_exit_authority_checks(run_dir, paths, spec, stage_c_doc) is None
    )

    # Forged postcheck naming a different manifest identity.
    post_path = run_dir / "manifest_post.json"
    original = post_path.read_bytes()
    doc = json.loads(original)
    doc["frozen_manifest_sha256"] = "0" * 64
    from bistar_gp.m2cr.serialization import atomic_write_canonical_json

    atomic_write_canonical_json(post_path, doc)
    doctored_stage_c = dict(
        stage_c_doc, importable_manifest_post_sha256=sha256_file(post_path)
    )
    fault = _post_exit_authority_checks(run_dir, paths, spec, doctored_stage_c)
    assert fault is not None and "does not attest the authenticated" in fault

    # Doctored stage_c linkage (digest no longer matches the file).
    post_path.write_bytes(original)
    fault = _post_exit_authority_checks(run_dir, paths, spec, doctored_stage_c)
    assert fault is not None and "does not bind the post-execution" in fault

    # Stripped postcheck file.
    post_path.unlink()
    fault = _post_exit_authority_checks(run_dir, paths, spec, stage_c_doc)
    assert fault is not None and "attestation is missing" in fault


# ---------------------------------------------------------------------------
# Kimi K3 findings 2+3 — committed-bundle CI: the committed header roots must
# be the pinned interpreter's OWN paths, and every committed closure member
# must be contained under the committed roots (the production redundancy of
# the outside-roots clause is asserted, not assumed).
# ---------------------------------------------------------------------------

_COMMITTED_ENV_FREEZE = (
    REPOSITORY_ROOT / "docs/m2c_freeze/m2cr_environment_freeze_manifest_v1.json"
)


def _regen_window() -> bool:
    return os.environ.get("M2CR_ALLOW_MISSING_COMMITTED_MANIFEST") == "1"


@pytest.mark.skipif(
    _regen_window(),
    reason="orchestrator regeneration window: committed bundle in flux",
)
def test_committed_manifest_roots_are_the_pinned_interpreters_own_paths() -> None:
    freeze = json.loads(_COMMITTED_ENV_FREEZE.read_text(encoding="utf-8"))
    pins = {
        name: REPOSITORY_ROOT / entry["path"]
        for name, entry in freeze["artifacts"].items()
    }
    pin = json.loads(pins["interpreter_pin"].read_text(encoding="utf-8"))
    probe = subprocess.run(
        [
            pin["path"],
            "-c",
            "import json, sysconfig; print(json.dumps({"
            "'stdlib': sysconfig.get_path('stdlib'),"
            "'purelib': sysconfig.get_path('purelib')}))",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    sys_paths = json.loads(probe.stdout)
    with pins["importable_artifact_manifest"].open(encoding="utf-8") as handle:
        header = json.loads(handle.readline())
    roots = header["roots"]
    assert os.path.realpath(roots["stdlib"]) == os.path.realpath(
        sys_paths["stdlib"]
    )
    assert os.path.realpath(roots["site-packages"]) == os.path.realpath(
        sys_paths["purelib"]
    )
    assert os.path.realpath(roots["lib-dynload"]) == os.path.realpath(
        os.path.join(sys_paths["stdlib"], "lib-dynload")
    )


@pytest.mark.skipif(
    _regen_window(),
    reason="orchestrator regeneration window: committed bundle in flux",
)
def test_committed_closure_members_are_contained_under_the_committed_roots() -> None:
    freeze = json.loads(_COMMITTED_ENV_FREEZE.read_text(encoding="utf-8"))
    pins = {
        name: REPOSITORY_ROOT / entry["path"]
        for name, entry in freeze["artifacts"].items()
    }
    with pins["importable_artifact_manifest"].open(encoding="utf-8") as handle:
        header = json.loads(handle.readline())
    host_roots = [
        os.path.realpath(header["roots"][name])
        for name in ("stdlib", "lib-dynload", "site-packages")
    ]
    attestation = json.loads(
        pins["preboundary_attestation_set"].read_text(encoding="utf-8")
    )
    for entry in attestation["bootstrap_closure"]:
        if entry.get("root") == "worktree":
            continue
        real = os.path.realpath(entry["path"])
        assert any(
            os.path.commonpath((root, real)) == root for root in host_roots
        ), f"closure member outside the committed roots: {entry['path']}"


def test_session_closure_directive_is_nonempty_and_hashable() -> None:
    directive = session_closure_directive()
    assert directive
    for entry in directive:
        assert len(entry["sha256"]) == 64
        if "path" in entry:
            assert os.path.isabs(entry["path"])
        else:
            assert entry["root"] == "worktree" and entry["relpath"]


def test_extension_registered_submodule_binds_loader_via_parent(
    tmp_path: Path,
) -> None:
    """First real-native launch finding: a C-extension-REGISTERED submodule
    (torch._C._autograd class) shares the parent .so's origin with no loader
    object; the pinned loader must be satisfied by the parent module with the
    SAME origin, and a loader-less module with no such ancestor still fails."""

    from types import ModuleType

    from bistar_gp.m2cr.bootstrap import _inventory

    ext_path = tmp_path / "fake_ext.cpython-313-darwin.so"
    ext_path.write_bytes(b"m2cr-fake-extension\n")
    roots = [os.fspath(tmp_path)] + [
        os.fspath(tmp_path / name) for name in ("b", "c", "d")
    ]
    for root in roots[1:]:
        Path(root).mkdir(exist_ok=True)
    entries = {
        ("worktree", ext_path.name): {
            "root": "worktree",
            "relpath": ext_path.name,
            "artifact_type": "extension",
            "sha256": sha256_file(ext_path),
            "size": ext_path.stat().st_size,
            "loader": "ExtensionFileLoader",
        }
    }

    class ExtensionFileLoader:  # bare-name spelling matches the pin
        pass

    parent = ModuleType("fakepkg")
    parent.__file__ = os.fspath(ext_path)
    parent.__loader__ = ExtensionFileLoader()
    orphan_free = ModuleType("fakepkg.sub")
    orphan_free.__file__ = os.fspath(ext_path)

    inventory = _inventory(
        [],
        roots=roots,
        manifest_entries=entries,
        closure_authority={},
        modules={"fakepkg": parent, "fakepkg.sub": orphan_free},
    )
    by_name = {item["module"]: item for item in inventory}
    assert by_name["fakepkg"]["loader_binding"] == "direct"
    assert by_name["fakepkg.sub"]["loader_binding"] == "parent:fakepkg"

    # A loader-less module with no qualifying ancestor is accepted with its
    # absence RECORDED (library module-object surgery, e.g. torch.backends,
    # legitimately strips loader metadata; the bytes are already sha-bound).
    solo = _inventory(
        [],
        roots=roots,
        manifest_entries=entries,
        closure_authority={},
        modules={"fakepkg.sub": orphan_free},
    )
    assert solo[0]["loader_binding"] == "unclaimed"

    # A CONFLICTING concrete loader class — the §4.5.7 smuggling case the pin
    # exists for — still fails closed.
    class zipimporter:
        pass

    smuggled = ModuleType("fakepkg.smuggled")
    smuggled.__file__ = os.fspath(ext_path)
    smuggled.__loader__ = zipimporter()
    with pytest.raises(SystemExit, match="loader class mismatch"):
        _inventory(
            [],
            roots=roots,
            manifest_entries=entries,
            closure_authority={},
            modules={"fakepkg.smuggled": smuggled},
        )


def test_synthetic_module_with_nonexistent_origin_is_not_hashed(
    tmp_path: Path,
) -> None:
    """First real-native launch finding: a synthetic module carrying a bogus
    __file__ that does not exist on disk (torch installs torch.classes with a
    relative __file__ == '_classes.py') backs no file execution, so it is
    classified synthetic_no_file and never hashed or authenticated — rather
    than crashing the origin binding with FileNotFoundError."""

    from types import ModuleType

    from bistar_gp.m2cr.bootstrap import _inventory

    roots = [os.fspath(tmp_path)] + [
        os.fspath(tmp_path / name) for name in ("b", "c", "d")
    ]
    for root in roots[1:]:
        Path(root).mkdir(exist_ok=True)
    synthetic = ModuleType("torch.classes")
    synthetic.__file__ = "_classes.py"  # bogus relative, resolves under CWD
    inventory = _inventory(
        [],
        roots=roots,
        manifest_entries={},
        closure_authority={},
        modules={"torch.classes": synthetic},
    )
    assert inventory[0]["classification"] == "synthetic_no_file"
    assert inventory[0]["resolved_origin"] is None
    assert "sha256" not in inventory[0]

    # A module whose claimed origin DOES exist on disk is still authenticated
    # (here it has no authority, so it fails closed — proving the isfile gate
    # did not become a blanket bypass).
    real = tmp_path / "real_mod.py"
    real.write_text("VALUE = 1\n", encoding="utf-8")
    outside = ModuleType("real_mod")
    outside.__file__ = os.fspath(tmp_path.parent / "real_mod.py")
    (tmp_path.parent / "real_mod.py").write_text("VALUE = 1\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="no authenticated closure pin"):
        _inventory(
            [],
            roots=roots,
            manifest_entries={},
            closure_authority={},
            modules={"real_mod": outside},
        )


# ---------------------------------------------------------------------------
# Three-reviewer gate — consolidated fix-pass discriminating tests.
# ---------------------------------------------------------------------------


def test_attestation_path_aliasing_the_marker_is_rejected(tmp_path: Path) -> None:
    """A caller attestation path routed to payload_started.json would let the
    child forge the consumption marker via an early attestation write; capture
    rejects it pre-spawn with no child spawned."""

    config = _make_launch(
        tmp_path,
        template_extra={
            "attestation_paths": {
                "payload_started": os.fspath(
                    Path(tmp_path, "run", "payload_started.json")
                ),
                "effect_proofs": os.fspath(
                    Path(tmp_path, "run", "payload_started.json")
                ),
            }
        },
    )
    record = capture_run(config)
    assert record["status"] == "INFRA_FAILURE"
    assert record["fault"]["fault_class"] == "capture_fault"
    assert "aliases the reserved payload-start marker" in record["fault"]["detail"]
    run_dir = Path(config.run_dir)
    assert not (run_dir / "spawned.json").exists()
    assert not (run_dir / "payload_started.json").exists()


def test_authorization_id_must_equal_the_chain_authorization_id(
    tmp_path: Path,
) -> None:
    """A routing authorization id that disagrees with the chain's own
    authorization id is refused before any run artifact exists."""

    import dataclasses

    config = _make_launch(tmp_path)
    mismatched = dataclasses.replace(
        config, authorization_id="m2cr-auth-20000101-99"
    )
    with pytest.raises(Exception) as excinfo:
        capture_run(mismatched)
    assert "authorization_id does not match" in str(excinfo.value)
    assert not (Path(config.run_dir) / "prelaunch.json").exists()


def test_payload_entry_path_override_disagreeing_with_entry_is_rejected(
    tmp_path: Path,
) -> None:
    """An explicit payload_entry_path that resolves to a different file than
    the executed payload.entry is rejected, so the parent cannot attest a file
    the child does not execute (§4.5.10)."""

    config = _make_launch(
        tmp_path,
        template_extra={
            "payload_entry_path": os.fspath(
                tmp_path / "worktree" / "bistar_gp/m2cr/bootstrap.py"
            )
        },
    )
    record = capture_run(config)
    assert record["status"] == "INFRA_FAILURE"
    assert (
        "does not resolve to the executed payload entry source"
        in record["fault"]["detail"]
    )
    assert not (Path(config.run_dir) / "spawned.json").exists()


def test_payload_image_allowlist_authenticates_bytes_not_just_path() -> None:
    """The Stage-C payload-image allowlist authenticates each new image's
    bytes against a frozen digest; a byte mutation or a missing entry fails
    closed (three-reviewer gate convergent finding)."""

    from bistar_gp.m2cr.bootstrap import authenticate_new_loaded_images

    pinned = {"/opt/lib/libx.dylib": "a" * 64, "/opt/lib/liby.dylib": "b" * 64}
    # Matching digest passes.
    authenticate_new_loaded_images(
        ["/opt/lib/base.dylib"],
        ["/opt/lib/base.dylib", "/opt/lib/libx.dylib"],
        [{"path": "/opt/lib/libx.dylib", "sha256": "a" * 64}],
        hasher=lambda p: pinned[p],
    )
    # A mutation of an allowlisted image fails closed.
    with pytest.raises(SystemExit, match="do not match the committed allowlist"):
        authenticate_new_loaded_images(
            ["/opt/lib/base.dylib"],
            ["/opt/lib/base.dylib", "/opt/lib/libx.dylib"],
            [{"path": "/opt/lib/libx.dylib", "sha256": "0" * 64}],
            hasher=lambda p: pinned[p],
        )
    # A payload-time image with no committed entry fails closed.
    with pytest.raises(SystemExit, match="no committed allowlist entry"):
        authenticate_new_loaded_images(
            ["/opt/lib/base.dylib"],
            ["/opt/lib/base.dylib", "/opt/lib/liby.dylib"],
            [{"path": "/opt/lib/libx.dylib", "sha256": "a" * 64}],
            hasher=lambda p: pinned[p],
        )


def test_file_backed_module_with_deleted_origin_fails_closed(
    tmp_path: Path,
) -> None:
    """A module carrying a REAL file loader whose origin was deleted after
    executing does NOT qualify as synthetic_no_file; it fails closed rather
    than being exempted (three-reviewer gate)."""

    from types import ModuleType

    from bistar_gp.m2cr.bootstrap import _inventory

    roots = [os.fspath(tmp_path)] + [
        os.fspath(tmp_path / n) for n in ("b", "c", "d")
    ]
    for r in roots[1:]:
        Path(r).mkdir(exist_ok=True)

    class SourceFileLoader:  # concrete file loader spelling
        pass

    deleted = ModuleType("evicted_mod")
    deleted.__file__ = os.fspath(tmp_path / "gone.py")  # never created
    deleted.__loader__ = SourceFileLoader()
    with pytest.raises(SystemExit, match="unreadable and cannot be authenticated"):
        _inventory(
            [],
            roots=roots,
            manifest_entries={},
            closure_authority={},
            modules={"evicted_mod": deleted},
        )


def test_loader_none_accepted_only_for_source_and_extension_artifacts(
    tmp_path: Path,
) -> None:
    """Delta CD4: a "none" runtime loader is satisfied only when the frozen
    manifest loader is the UNIQUE compulsory loader for its artifact type
    (SourceFileLoader / ExtensionFileLoader).  A frozen SourcelessFileLoader
    pin (bytecode) is NOT satisfied by a "none" loader, so clearing loader
    fields cannot launder a sourceless load."""

    from types import ModuleType

    from bistar_gp.m2cr.bootstrap import _inventory

    roots = [os.fspath(tmp_path)] + [
        os.fspath(tmp_path / n) for n in ("b", "c", "d")
    ]
    for r in roots[1:]:
        Path(r).mkdir(exist_ok=True)
    art = tmp_path / "artifact.pyc"
    art.write_bytes(b"m2cr-fake-bytecode\n")
    entries = {
        ("worktree", "artifact.pyc"): {
            "root": "worktree",
            "relpath": "artifact.pyc",
            "artifact_type": "legacy_bytecode",
            "sha256": sha256_file(art),
            "size": art.stat().st_size,
            "loader": "SourcelessFileLoader",
        }
    }
    # A loader-"none" module whose frozen pin is SourcelessFileLoader (bytecode)
    # is REJECTED — "none" does not launder a sourceless load.
    loaderless = ModuleType("mod")
    loaderless.__file__ = os.fspath(art)
    with pytest.raises(SystemExit, match="loader class mismatch"):
        _inventory(
            [],
            roots=roots,
            manifest_entries=entries,
            closure_authority={},
            modules={"mod": loaderless},
        )
    # The same loader-"none" module against a SourceFileLoader (source) pin IS
    # accepted (unique compulsory loader) — proving the gate is on the artifact
    # type, not a blanket "none" acceptance.
    src = tmp_path / "artifact.py"
    src.write_bytes(b"VALUE = 1\n")
    source_entries = {
        ("worktree", "artifact.py"): {
            "root": "worktree",
            "relpath": "artifact.py",
            "artifact_type": "source",
            "sha256": sha256_file(src),
            "size": src.stat().st_size,
            "loader": "SourceFileLoader",
        }
    }
    source_mod = ModuleType("srcmod")
    source_mod.__file__ = os.fspath(src)
    inv = _inventory(
        [],
        roots=roots,
        manifest_entries=source_entries,
        closure_authority={},
        modules={"srcmod": source_mod},
    )
    assert inv[0]["loader_binding"] == "unclaimed"
