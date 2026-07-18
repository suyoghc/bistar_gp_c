"""Bounded real-root integration battery for the WI1/WI2 launch authority.

These are the ONLY tests that prove the public production path end to end:
real four roots (candidate worktree + real stdlib + real lib-dynload + real
site-packages), the committed-shape bundle regenerated over that worktree with
the REAL generators, the real native stack imported pre-marker, and the
child's complete pre/post re-walks and origin/loader authentication over the
real roots.  The launch budget is FOUR dedicated child launches:

1. the successful complete production path (COMPLETED);
2. a pre-walk added-artifact failure before the marker;
3. a post-execution mutation failure after the marker (COMPLETED impossible);
4. an origin/loader authority failure at real roots (a corrupted closure pin
   over a consistently re-pinned bundle) before the marker.

Positive and negative launches are separate processes in separate run
directories.  The session-scoped host bundle is generated INDEPENDENTLY
before any test child starts, by this (parent) process, with the same
builders the production regeneration uses; children only consume and
re-verify.  The bundle is cached OUTSIDE the repository, keyed by the
candidate tree id (the stash-created tree, so uncommitted tracked changes are
part of the key and of the launched code), the interpreter resolved-path
digest, the canonical four roots, and the generator source digests; a key
mismatch regenerates.  On a cache hit the bundle is revalidated cheaply (the
dependency-lock semantics are recomputed against the live site-packages and a
deterministic sample of manifest entries is re-hashed); the child's own
complete pre-walk remains the authoritative full check, and every negative
asserts its SPECIFIC planted artifact so unrelated host drift cannot
masquerade as a pass.

No scientific computation occurs: the payload imports the frozen
``bistar_gp.profile_integration`` module (import only, the same attestation
class the committed expectations measure) and emits a synthetic COMPLETED
document.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tarfile
import tempfile
import time
from pathlib import Path

import pytest

from bistar_gp.m2cr.capture import (
    BOOTSTRAP_CONFIG_NAME,
    LaunchConfig,
    capture_run,
    enumerate_bootstrap_closure,
)
from bistar_gp.m2cr.environment_freeze import (
    R1_SCHEMA_RELPATHS,
    R2_CODE_RELPATHS,
    R2_NATIVE_STACK_MODULES,
    R2_NUMPY_BUILD_EXPECTED,
    R2_STAGE_B_EXPECTED,
    R2_TORCH_BUILD_EXPECTED,
    build_child_env_mapping,
    build_dependency_lock,
    build_environment_freeze_manifest,
    build_importable_artifact_manifest,
    build_infrastructure_manifest,
    build_interpreter_pin,
    build_native_stack_expectations,
    build_preboundary_attestation_set,
    verify_dependency_lock_semantics,
)
from bistar_gp.m2cr.serialization import (
    atomic_write_canonical_json,
    canonical_sha256,
    sha256_file,
)
from tests.test_m2cr_bootstrap import _failed_node_record

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
INTERPRETER = "/opt/homebrew/Caskroom/miniconda/base/bin/python3.13"
STDLIB = "/opt/homebrew/Caskroom/miniconda/base/lib/python3.13"
DYNLOAD = STDLIB + "/lib-dynload"
SITE = STDLIB + "/site-packages"
AUTHORIZATION_ID = "m2cr-auth-20260716-01"
LAUNCH_ATTEMPT_ID = "m2cr-launch-20260716-01"
CHAIN_BASE = {
    "v117_canonical_sha256": (
        "65381bc774e894dd9aaf2207cadd9cfa2f2735dafceff4bb39492086a9e522e2"
    ),
    "protocol_manifest_sha256": "3" * 64,
    "execution_commit": "a" * 40,
    "authorization_id": AUTHORIZATION_ID,
}
_FREEZE = "docs/m2c_freeze"

pytestmark = pytest.mark.skipif(
    not os.path.exists(INTERPRETER), reason="hermetic interpreter absent"
)

_PAYLOAD_SOURCE = f"""import os


def run(context):
    import bistar_gp.profile_integration  # frozen module, import only
    context.emit("STAGE_BEGIN", stage_id="level0")
    context.emit("NODE_BEGIN", node_index=0)
    if os.path.exists(os.path.join(os.environ["HOME"], "m2cr_plant_flag")):
        open("m2cr_postdrift_plant.py", "w").write("PLANT = 1\\n")
    context.emit("NODE_END", node_index=0)
    context.emit("STAGE_END", stage_id="level0")
    return {{
        "status": "COMPLETED",
        "stages": [{{
            "stage_id": "level0", "stage_class": "verdict",
            "status": "COMPLETED", "nodes_evaluated": 1, "nodes_total": 1
        }}],
        "aggregates": {{
            "verdict_class": {{
                "restart_count": 0, "retry_count": 0, "retry_failure_count": 0,
                "rcond_fail_count": 0, "symmetry_fail_count": 0,
                "battery_fail_count": 0
            }},
            "diagnostic_class": {{
                "restart_count": 0, "retry_count": 0, "retry_failure_count": 0,
                "rcond_fail_count": 0, "symmetry_fail_count": 0,
                "battery_fail_count": 0
            }}
        }},
        "node_records": {[_failed_node_record()]!r}
    }}
"""


def _cache_root() -> Path:
    base = os.environ.get("XDG_CACHE_HOME") or os.path.join(
        os.path.expanduser("~"), ".cache"
    )
    return Path(base) / "bistar_gp_m2cr_realroot"


def _candidate_tree() -> tuple[str, str, bool]:
    """(archivable commit-ish, tree id, dirty) for the candidate tracked tree.

    ``git stash create`` captures uncommitted TRACKED modifications into an
    unreferenced commit, so the archived tree IS the candidate code even
    mid-cycle; a clean tree falls back to HEAD.
    """

    head = subprocess.run(
        ["git", "-C", os.fspath(REPOSITORY_ROOT), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    stash = subprocess.run(
        ["git", "-C", os.fspath(REPOSITORY_ROOT), "stash", "create"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    commit = stash or head
    tree = subprocess.run(
        [
            "git",
            "-C",
            os.fspath(REPOSITORY_ROOT),
            "rev-parse",
            f"{commit}^{{tree}}",
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return commit, tree, bool(stash)


def _bundle_key() -> dict[str, object]:
    commit, tree, dirty = _candidate_tree()
    generators = {
        relpath: sha256_file(REPOSITORY_ROOT / relpath)
        for relpath in (
            "bistar_gp/m2cr/environment_freeze.py",
            "bistar_gp/m2cr/serialization.py",
            "bistar_gp/m2cr/capture.py",
            "bistar_gp/m2cr/bootstrap.py",
        )
    }
    return {
        "candidate_head": commit if not dirty else f"{commit} (stash of HEAD)",
        "tree_id": tree,
        "dirty_tracked_tree": dirty,
        "interpreter_realpath": os.path.realpath(INTERPRETER),
        "interpreter_sha256": sha256_file(os.path.realpath(INTERPRETER)),
        "four_roots": ["<worktree>", STDLIB, DYNLOAD, SITE],
        "generator_sha256": generators,
        "_archive_commit": commit,
    }


def _generate_bundle(worktree: Path, commit: str) -> dict[str, object]:
    """Extract the candidate tree and regenerate the full committed-shape
    bundle over it with the REAL generators (the established regeneration
    recipe), returning the bound chain."""

    with tempfile.NamedTemporaryFile(suffix=".tar") as archive:
        subprocess.run(
            [
                "git",
                "-C",
                os.fspath(REPOSITORY_ROOT),
                "archive",
                "--format=tar",
                "-o",
                archive.name,
                commit,
            ],
            check=True,
        )
        with tarfile.open(archive.name) as tar:
            tar.extractall(worktree, filter="data")
    (worktree / "fake_payload.py").write_text(_PAYLOAD_SOURCE, encoding="utf-8")

    freeze = worktree / _FREEZE
    atomic_write_canonical_json(
        freeze / "m2cr_interpreter_pin_v1.json", build_interpreter_pin(INTERPRETER)
    )
    atomic_write_canonical_json(
        freeze / "m2cr_child_env_mapping_v1.json", build_child_env_mapping()
    )
    manifest_path = freeze / "m2cr_importable_artifact_manifest_v1.jsonl"
    build_importable_artifact_manifest(
        [
            ("worktree", worktree),
            ("stdlib", STDLIB),
            ("lib-dynload", DYNLOAD),
            ("site-packages", SITE),
        ],
        manifest_path,
    )
    atomic_write_canonical_json(
        freeze / "m2cr_dependency_lock_v1.json",
        build_dependency_lock(INTERPRETER, SITE),
    )
    v117 = json.loads(
        (freeze / "gtoy_profile_freeze_v1.17.json").read_text(encoding="utf-8")
    )
    atomic_write_canonical_json(
        freeze / "m2cr_native_stack_expectations_v1.json",
        build_native_stack_expectations(
            INTERPRETER,
            native_stack_modules=R2_NATIVE_STACK_MODULES,
            profile_integration_sha256=v117["algorithm"][
                "profile_integration_sha256"
            ],
            torch_build_expected=R2_TORCH_BUILD_EXPECTED,
            numpy_build_expected=R2_NUMPY_BUILD_EXPECTED,
            stage_b_expected=R2_STAGE_B_EXPECTED,
            probe_cwd=worktree,
        ),
    )
    closure = enumerate_bootstrap_closure(
        INTERPRETER, worktree / "bistar_gp/m2cr/bootstrap.py", worktree
    )
    atomic_write_canonical_json(
        freeze / "m2cr_preboundary_attestation_set_v1.json",
        build_preboundary_attestation_set(
            INTERPRETER,
            bootstrap_closure_paths=sorted(
                {entry["origin"] for entry in closure}
            ),
            worktree_root=worktree,
        ),
    )
    _finalize_bundle_manifests(worktree)
    return _bundle_chain(worktree)


def _finalize_bundle_manifests(worktree: Path) -> None:
    freeze = worktree / _FREEZE
    atomic_write_canonical_json(
        freeze / "m2cr_environment_freeze_manifest_v1.json",
        build_environment_freeze_manifest(
            {
                "child_env_mapping": freeze / "m2cr_child_env_mapping_v1.json",
                "importable_artifact_manifest": (
                    freeze / "m2cr_importable_artifact_manifest_v1.jsonl"
                ),
                "interpreter_pin": freeze / "m2cr_interpreter_pin_v1.json",
                "preboundary_attestation_set": (
                    freeze / "m2cr_preboundary_attestation_set_v1.json"
                ),
            },
            repo_root=worktree,
        ),
    )
    atomic_write_canonical_json(
        freeze / "m2cr_infrastructure_manifest_v1.json",
        build_infrastructure_manifest(
            {
                "code": {
                    relpath: worktree / relpath for relpath in R2_CODE_RELPATHS
                },
                "artifacts": {
                    "child_env_mapping": freeze / "m2cr_child_env_mapping_v1.json",
                    "importable_artifact_manifest": (
                        freeze / "m2cr_importable_artifact_manifest_v1.jsonl"
                    ),
                    "interpreter_pin": freeze / "m2cr_interpreter_pin_v1.json",
                    "preboundary_attestation_set": (
                        freeze / "m2cr_preboundary_attestation_set_v1.json"
                    ),
                    "environment_freeze_manifest": (
                        freeze / "m2cr_environment_freeze_manifest_v1.json"
                    ),
                    "dependency_lock": freeze / "m2cr_dependency_lock_v1.json",
                    "native_stack_expectations": (
                        freeze / "m2cr_native_stack_expectations_v1.json"
                    ),
                },
                "r1_schemas": {
                    "execution_record": worktree / R1_SCHEMA_RELPATHS[0],
                    "authorization_ledger": worktree / R1_SCHEMA_RELPATHS[1],
                },
            },
            repo_root=worktree,
        ),
    )


def _bundle_chain(worktree: Path) -> dict[str, object]:
    freeze = worktree / _FREEZE
    return {
        **CHAIN_BASE,
        "infrastructure_manifest_sha256": sha256_file(
            freeze / "m2cr_infrastructure_manifest_v1.json"
        ),
        "environment_freeze_manifest_sha256": sha256_file(
            freeze / "m2cr_environment_freeze_manifest_v1.json"
        ),
    }


def _revalidate_cached_bundle(bundle_dir: Path) -> bool:
    """Cheap drift checks on a cache hit (Kimi K3 challenge, finding 6): the
    dependency-lock semantics recompute against the LIVE site-packages, and a
    deterministic sample of manifest entries re-hashes on disk.  The child's
    own complete pre-walk remains the authoritative full check."""

    worktree = bundle_dir / "worktree"
    freeze = worktree / _FREEZE
    try:
        lock = json.loads(
            (freeze / "m2cr_dependency_lock_v1.json").read_text(
                encoding="utf-8"
            )
        )
        if verify_dependency_lock_semantics(lock, INTERPRETER, SITE) is not None:
            return False
        roots = {
            "worktree": os.fspath(worktree),
            "stdlib": STDLIB,
            "lib-dynload": DYNLOAD,
            "site-packages": SITE,
        }
        entries = []
        with (freeze / "m2cr_importable_artifact_manifest_v1.jsonl").open(
            encoding="utf-8"
        ) as handle:
            handle.readline()
            for line in handle:
                entries.append(json.loads(line))
        if not entries:
            return False
        stride = max(1, len(entries) // 64)
        for entry in entries[::stride]:
            target = Path(roots[entry["root"]]) / entry["relpath"]
            if (
                not target.is_file()
                or sha256_file(target) != entry["sha256"]
            ):
                return False
    except (OSError, ValueError, KeyError):
        return False
    return True


_SESSION_BUNDLE: tuple[Path, dict[str, object]] | None = None


def _bundle() -> tuple[Path, dict[str, object]]:
    """The session-scoped authenticated host bundle (generated independently
    before any test child starts; atomic populate; keyed cache)."""

    global _SESSION_BUNDLE
    if _SESSION_BUNDLE is not None:
        return _SESSION_BUNDLE
    key_doc = _bundle_key()
    archive_commit = str(key_doc.pop("_archive_commit"))
    key = canonical_sha256(key_doc)[:24]
    bundle_dir = _cache_root() / key
    key_file = bundle_dir / "key.json"
    if key_file.is_file():
        recorded = json.loads(key_file.read_text(encoding="utf-8"))
        if recorded.get("key") == key and _revalidate_cached_bundle(bundle_dir):
            chain = json.loads(
                (bundle_dir / "chain.json").read_text(encoding="utf-8")
            )
            _SESSION_BUNDLE = (bundle_dir / "worktree", chain)
            return _SESSION_BUNDLE
        shutil.rmtree(bundle_dir, ignore_errors=True)
    _cache_root().mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".m2cr-staging-{os.getpid()}-", dir=_cache_root())
    )
    try:
        worktree = staging / "worktree"
        worktree.mkdir()
        chain = _generate_bundle(worktree, archive_commit)
        atomic_write_canonical_json(staging / "chain.json", chain)
        # key.json is written LAST: a torn population never carries it and is
        # treated as absent, then replaced atomically by rename.
        atomic_write_canonical_json(
            staging / "key.json", {"key": key, **key_doc}
        )
        shutil.rmtree(bundle_dir, ignore_errors=True)
        os.rename(staging, bundle_dir)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    chain = json.loads((bundle_dir / "chain.json").read_text(encoding="utf-8"))
    _SESSION_BUNDLE = (bundle_dir / "worktree", chain)
    return _SESSION_BUNDLE


def _launch(
    worktree: Path,
    chain: dict[str, object],
    run_dir: Path,
    run_id: str,
    *,
    plant_flag: bool = False,
) -> tuple[dict[str, object], float]:
    run_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_canonical_json(
        run_dir / BOOTSTRAP_CONFIG_NAME,
        {
            "payload": {"entry": "fake_payload:run", "pass_context": True},
            "attestation_paths": {
                "payload_started": os.fspath(run_dir / "payload_started.json")
            },
        },
    )
    if plant_flag:
        (run_dir / "home").mkdir(parents=True, exist_ok=True)
        (run_dir / "home" / "m2cr_plant_flag").write_text("1", encoding="utf-8")
    config = LaunchConfig(
        worktree_root=os.fspath(worktree),
        run_dir=os.fspath(run_dir),
        authorization_id=AUTHORIZATION_ID,
        launch_attempt_id=LAUNCH_ATTEMPT_ID,
        run_id=run_id,
        record_kind="diagnostic",
        chain=dict(chain),
    )
    start = time.perf_counter()
    record = capture_run(config)
    elapsed = time.perf_counter() - start
    timings_path = _cache_root() / "last_timings.json"
    try:
        timings = (
            json.loads(timings_path.read_text(encoding="utf-8"))
            if timings_path.is_file()
            else {}
        )
    except ValueError:
        timings = {}
    timings[run_id] = round(elapsed, 2)
    timings_path.parent.mkdir(parents=True, exist_ok=True)
    timings_path.write_text(json.dumps(timings, sort_keys=True), encoding="utf-8")
    return record, elapsed


def test_realroot_launch_1_positive_complete_production_path(
    tmp_path: Path,
) -> None:
    worktree, chain = _bundle()
    record, _ = _launch(
        worktree, chain, tmp_path / "run", "m2cr-realroot-positive"
    )
    assert record["status"] == "COMPLETED", record.get("fault")
    run_dir = tmp_path / "run"
    assert (run_dir / "payload_started.json").is_file()
    manifest_pre = json.loads((run_dir / "manifest_pre.json").read_text())
    assert manifest_pre["entry_sets_identical"] is True
    assert manifest_pre["entry_count"] > 30000
    manifest_post = json.loads((run_dir / "manifest_post.json").read_text())
    assert manifest_post["entry_sets_identical"] is True
    binding = json.loads((run_dir / "origin_binding_pre.json").read_text())
    assert binding["manifest_bound"] > 0
    assert binding["closure_bound"] == 0, (
        "every module in the real-root configuration is under the four "
        "roots, so the strict all-under-roots §4.5.7 form held with the "
        "closure clause unused"
    )
    inventory = json.loads((run_dir / "import_inventory.json").read_text())
    allowed = {
        "manifest_file",
        "closure_file",
        "built-in",
        "frozen",
        "namespace",
        "no_origin",
        "synthetic_no_file",
    }
    unexpected = [
        item
        for item in inventory["modules"]
        if item["classification"] not in allowed
    ]
    assert not unexpected, [item["module"] for item in unexpected]
    # A synthetic module with a nonexistent claimed origin (torch.classes) is
    # classified and NOT hashed — the fix that turned the FileNotFoundError
    # crash into an authenticated inventory.
    assert any(
        item["classification"] == "synthetic_no_file"
        for item in inventory["modules"]
    )


def test_realroot_launch_2_prewalk_added_artifact_fails_before_marker(
    tmp_path: Path,
) -> None:
    worktree, chain = _bundle()
    planted = worktree / "m2cr_rogue_plant.py"
    planted.write_text("ROGUE = 1\n", encoding="utf-8")
    try:
        record, _ = _launch(
            worktree, chain, tmp_path / "run", "m2cr-realroot-added"
        )
    finally:
        planted.unlink(missing_ok=True)
    assert record["status"] == "INFRA_FAILURE"
    assert record["fault"]["fault_class"] == "attestation_fault"
    assert "importable artifact manifest drift" in record["fault"]["detail"]
    assert "m2cr_rogue_plant.py" in record["fault"]["detail"]
    assert "pre_audit" in record["fault"]["detail"]
    assert record["fault"]["payload_started"] is False
    assert not (tmp_path / "run" / "payload_started.json").exists()


def test_realroot_launch_3_post_execution_mutation_never_completes(
    tmp_path: Path,
) -> None:
    worktree, chain = _bundle()
    plant = worktree / "m2cr_postdrift_plant.py"
    try:
        record, _ = _launch(
            worktree,
            chain,
            tmp_path / "run",
            "m2cr-realroot-postdrift",
            plant_flag=True,
        )
    finally:
        plant.unlink(missing_ok=True)
    assert record["status"] == "INFRA_FAILURE"
    assert "importable artifact manifest drift" in record["fault"]["detail"]
    assert "post_execution" in record["fault"]["detail"]
    assert "m2cr_postdrift_plant.py" in record["fault"]["detail"]
    assert record["fault"]["payload_started"] is True
    assert (tmp_path / "run" / "payload_started.json").is_file()


def test_realroot_launch_4_manifest_loader_substitution_fails_closed(
    tmp_path: Path,
) -> None:
    """The reserved fourth launch, exercised: a manifest-authority substitution
    at REAL roots.  A committed manifest entry's frozen loader is flipped to a
    CONFLICTING class (``zipimporter`` on a ``.py`` source), a tampering that
    survives the parent's §4.5.2 pre-boundary verification and the chain
    binding (the infra manifest is re-pinned over the doctored bytes).  The
    child must refuse it with no marker on genuine paths.

    Since the round-3 gate, the child rejects the self-inconsistent loader/type
    pairing at manifest PARSE — a stronger, earlier catch than the prior at-exit
    origin/loader binding — so the launch fails closed before any import.  The
    child-side origin/loader INVENTORY binding for a runtime loader mismatch is
    proven by the fast synthetic battery (`test_m2cr_launch_authority.py`), per
    the plan's allowance to prove that class with a cheaper discriminating
    test."""

    worktree, chain = _bundle()
    copy = tmp_path / "worktree-copy"
    shutil.copytree(worktree, copy)
    manifest_path = copy / _FREEZE / "m2cr_importable_artifact_manifest_v1.jsonl"
    target_key = ("worktree", "bistar_gp/m2cr/serialization.py")
    doctored_lines: list[str] = []
    doctored = 0
    with manifest_path.open(encoding="utf-8") as handle:
        for line in handle:
            entry = json.loads(line)
            if (
                entry.get("root") == target_key[0]
                and entry.get("relpath") == target_key[1]
            ):
                entry["loader"] = "zipimporter"
                doctored += 1
                doctored_lines.append(
                    json.dumps(
                        entry, sort_keys=True, separators=(",", ":")
                    )
                    + "\n"
                )
            else:
                doctored_lines.append(line)
    assert doctored == 1
    manifest_path.write_text("".join(doctored_lines), encoding="utf-8")
    _finalize_bundle_manifests(copy)
    record, _ = _launch(
        copy,
        _bundle_chain(copy),
        tmp_path / "run",
        "m2cr-realroot-loader",
    )
    assert record["status"] == "INFRA_FAILURE"
    assert (
        "loader does not match its artifact type" in record["fault"]["detail"]
    )
    assert record["fault"]["payload_started"] is False
    assert not (tmp_path / "run" / "payload_started.json").exists()
