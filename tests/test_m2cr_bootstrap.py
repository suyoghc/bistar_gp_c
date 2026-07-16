from __future__ import annotations

import json
import os
import subprocess
import sys
from importlib.util import spec_from_file_location
from pathlib import Path
from types import ModuleType

import pytest

from bistar_gp.m2cr.bootstrap import (
    _inventory,
    _load_importable_artifact_manifest,
    _verify_importable_artifact_manifest,
    classify_pyc_candidate,
    classify_stage_b_deltas,
    parse_raw_environ_block,
    scan_pyc_candidates,
)
from bistar_gp.m2cr.environment_freeze import build_importable_artifact_manifest
from bistar_gp.m2cr.serialization import canonical_dumps


MINICONDA_PYTHON = "/opt/homebrew/Caskroom/miniconda/base/bin/python3.13"
MINICONDA_ROOT = Path("/opt/homebrew/Caskroom/miniconda/base")
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = REPOSITORY_ROOT / "bistar_gp/m2cr/bootstrap.py"
SENTINEL_HASH = -2671292046718125608
AUTHORIZATION_ID = "m2cr-auth-20260716-01"
LAUNCH_ATTEMPT_ID = "m2cr-launch-20260716-01"
EXECUTION_COMMIT = "a" * 40
CHAIN = {
    "v117_canonical_sha256": "65381bc774e894dd9aaf2207cadd9cfa2f2735dafceff4bb39492086a9e522e2",
    "infrastructure_manifest_sha256": "1" * 64,
    "environment_freeze_manifest_sha256": "2" * 64,
    "protocol_manifest_sha256": "3" * 64,
    "execution_commit": EXECUTION_COMMIT,
    "authorization_id": AUTHORIZATION_ID,
}

pytestmark = pytest.mark.skipif(
    sys.platform != "darwin", reason="raw _NSGetEnviron is Darwin-specific"
)


def _failed_node_record() -> dict[str, object]:
    attempt = {
        "is_jittered_restart": False,
        "start": [0.0, 0.0, 0.0],
        "u": [0.0, 0.0, 0.0],
        "g": 0.0,
        "gradient": [0.0, 0.0, 0.0],
        "grad_inf_norm": 0.0,
        "status": 0,
        "reported_success": True,
        "finite": True,
        "stationary": True,
        "accepted": False,
        "message": "synthetic",
    }
    warm_start = {
        "identity": {"kind": "mode_u"},
        "vector": [0.0, 0.0, 0.0],
        "selection_reason": "initial_mode_u",
    }
    return {
        "node_index": 0,
        "noise": 0.1,
        "persisted_axis_order": ["ls", "os", "lv"],
        "computation_storage_order": ["site.ls", "site.os", "site.lv"],
        "incoming_warm_start": warm_start,
        "outgoing_warm_start": warm_start,
        "optimizer": {
            "starts": [
                {"label": "warm", "attempts": [attempt]},
                {"label": "mode", "attempts": [attempt]},
            ],
            "u_star": None,
            "g_star": 0.0,
            "grad_inf_norm": 0.0,
            "both_success": False,
            "agree": False,
            "agree_g": False,
            "agree_u": False,
            "restart_count": 0,
            "stop": True,
            "reason": "synthetic optimizer stop",
        },
        "accepted": False,
        "selected_optimum": None,
    }


def _payload_source(
    mode: str,
    *,
    marker_path: Path | None = None,
    import_side_effect: Path | None = None,
    thread_log: Path | None = None,
) -> str:
    if mode == "drift":
        mutation = "os.environ['M2CR_DRIFT'] = '1'"
    elif thread_log is not None:
        mutation = (
            f"assert open({os.fspath(thread_log)!r}, encoding='utf-8').read() "
            "== 'intra=10\\ninterop=10\\n'"
        )
    else:
        mutation = "pass"
    import_spy = ""
    if import_side_effect is not None and marker_path is not None:
        import_spy = f"""
from pathlib import Path
import hashlib
_marker = Path({os.fspath(marker_path)!r})
if not _marker.is_file():
    raise RuntimeError("payload imported before marker")
Path({os.fspath(import_side_effect)!r}).write_text(
    hashlib.sha256(_marker.read_bytes()).hexdigest(), encoding="utf-8"
)
"""
    return f"""import os
{import_spy}

def run(context):
    context.emit("STAGE_BEGIN", stage_id="level0")
    context.emit("NODE_BEGIN", node_index=0)
    {mutation}
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
                "rcond_fail_count": 0, "symmetry_fail_count": 0, "battery_fail_count": 0
            }},
            "diagnostic_class": {{
                "restart_count": 0, "retry_count": 0, "retry_failure_count": 0,
                "rcond_fail_count": 0, "symmetry_fail_count": 0, "battery_fail_count": 0
            }}
        }},
        "node_records": {[_failed_node_record()]!r}
    }}
"""


def _frozen_environment(run_dir: Path) -> dict[str, str]:
    directories = {
        "HOME": run_dir / "home",
        "TMPDIR": run_dir / "tmp",
        "XDG_CACHE_HOME": run_dir / "xdg/cache",
        "XDG_CONFIG_HOME": run_dir / "xdg/config",
        "XDG_DATA_HOME": run_dir / "xdg/data",
        "XDG_STATE_HOME": run_dir / "xdg/state",
    }
    for path in directories.values():
        path.mkdir(parents=True, exist_ok=True)
    return {
        "PYTHONHASHSEED": "0",
        "OMP_NUM_THREADS": "10",
        "OMP_DYNAMIC": "FALSE",
        "MKL_NUM_THREADS": "10",
        "VECLIB_MAXIMUM_THREADS": "10",
        "LC_ALL": "C",
        "TZ": "UTC",
        "PATH": "/usr/bin:/bin",
        **{key: os.fspath(path.resolve()) for key, path in directories.items()},
    }


def _launch_bootstrap(
    tmp_path: Path,
    *,
    mode: str = "completed",
    env_mutator=None,
    expected_env_mutator=None,
    planted: str | None = None,
    prelaunch: bool = True,
    import_spy: bool = False,
    fake_torch: str | None = None,
    stage_b_expected: dict[str, str] | None = None,
) -> tuple[subprocess.CompletedProcess[bytes], Path, list[dict[str, object]]]:
    worktree = tmp_path / "worktree"
    run_dir = worktree / "run"
    worktree.mkdir(parents=True)
    run_dir.mkdir()
    (worktree / "bistar_gp").symlink_to(
        REPOSITORY_ROOT / "bistar_gp", target_is_directory=True
    )
    side_effect = worktree / "payload_imported.txt"
    marker_path = run_dir / "payload_started.json"
    (worktree / "fake_payload.py").write_text(
        _payload_source(
            mode,
            marker_path=marker_path,
            import_side_effect=side_effect if import_spy else None,
            thread_log=(worktree / "thread_calls.txt")
            if fake_torch is not None
            else None,
        ),
        encoding="utf-8",
    )
    if fake_torch is not None:
        torch = worktree / "torch"
        torch.mkdir()
        torch.joinpath("__init__.py").write_text(
            f"""import ctypes
import os
from pathlib import Path

_libc = ctypes.CDLL(None)
_libc.setenv(b"__CF_USER_TEXT_ENCODING", b"0x1F5:0x0:0x0", 1)
_libc.setenv(
    f"__KMP_REGISTERED_LIB_{{os.getpid()}}".encode(),
    b"0x1234-cafe1234-libomp.dylib",
    1,
)
_log = Path({os.fspath(worktree / "thread_calls.txt")!r})

def set_num_threads(value):
    _log.write_text(f"intra={{value}}\\n", encoding="utf-8")

def set_num_interop_threads(value):
    with _log.open("a", encoding="utf-8") as handle:
        handle.write(f"interop={{value}}\\n")
    {"raise RuntimeError('synthetic interop failure')" if fake_torch == "raise" else "return None"}
""",
            encoding="utf-8",
        )
    if planted == "orphan":
        orphan_dir = worktree / "orphan/__pycache__"
        orphan_dir.mkdir(parents=True)
        (orphan_dir / "missing.cpython-313.pyc").write_bytes(b"pyc")
    elif planted == "legacy":
        (worktree / "legacy.pyc").write_bytes(b"pyc")

    pycache = run_dir / "pycache"
    pycache.mkdir()
    environment = _frozen_environment(run_dir)
    expected_environment = dict(environment)
    if env_mutator is not None:
        env_mutator(environment)
    if expected_env_mutator is not None:
        expected_env_mutator(expected_environment)
    read_fd, write_fd = os.pipe()
    os.set_inheritable(write_fd, True)
    paths = {
        name: os.fspath(run_dir / filename)
        for name, filename in {
            "effect_proofs": "effect_proofs.json",
            "stage_a": "stage_a.json",
            "bytecode": "bytecode.json",
            "audit_canary": "audit_canary.json",
            "stage_b_os": "stage_b_os.json",
            "stage_b_raw": "stage_b_raw.json",
            "sourceless": "sourceless.json",
            "import_inventory": "import_inventory.json",
            "stage_c": "stage_c.json",
            "payload": "payload.json",
            "failure": "bootstrap_failure.json",
            "payload_started": "payload_started.json",
        }.items()
    }
    if prelaunch:
        (run_dir / "prelaunch.json").write_text(
            canonical_dumps({"launch": 1}), encoding="utf-8"
        )
    extra_roots = [
        tmp_path / "stdlib",
        tmp_path / "lib-dynload",
        tmp_path / "site-packages",
    ]
    for root in extra_roots:
        root.mkdir()
    roots = [
        os.fspath(worktree.resolve()),
        *(os.fspath(root.resolve()) for root in extra_roots),
    ]
    config = {
        "four_roots": roots,
        "frozen_env": expected_environment,
        "expected_pycache_prefix": os.fspath(pycache.resolve()),
        "expected_sentinel_hash": SENTINEL_HASH,
        "native_stack_modules": ["torch"] if fake_torch is not None else [],
        "worktree_root": roots[0],
        "attestation_paths": paths,
        "payload": {"entry": "fake_payload:run", "pass_context": True},
        "boundary": {
            "authorization_id": AUTHORIZATION_ID,
            "launch_attempt_id": LAUNCH_ATTEMPT_ID,
            "execution_commit": EXECUTION_COMMIT,
            "chain": CHAIN,
        },
    }
    if stage_b_expected is not None:
        config["stage_b_expected"] = stage_b_expected
    config_path = run_dir / "config.json"
    config_path.write_text(canonical_dumps(config), encoding="utf-8")
    completed = subprocess.run(
        [
            MINICONDA_PYTHON,
            "-S",
            "-s",
            "-P",
            "-B",
            "-X",
            f"pycache_prefix={pycache}",
            os.fspath(BOOTSTRAP),
            os.fspath(config_path),
            str(write_fd),
        ],
        shell=False,
        env=environment,
        cwd=worktree,
        pass_fds=(write_fd,),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=15,
    )
    os.close(write_fd)
    with os.fdopen(read_fd, "r", encoding="utf-8") as handle:
        events = [json.loads(line) for line in handle if line.strip()]
    return completed, run_dir, events


def test_effect_proofs_hash_seed_path_audit_and_inventory(tmp_path: Path) -> None:
    first, run_dir, events = _launch_bootstrap(tmp_path / "first")
    second, second_run, _ = _launch_bootstrap(tmp_path / "second")
    assert first.returncode == second.returncode == 0, first.stderr.decode()
    first_proofs = json.loads((run_dir / "effect_proofs.json").read_text())
    second_proofs = json.loads((second_run / "effect_proofs.json").read_text())
    assert first_proofs["checks"] == {name: True for name in first_proofs["checks"]}
    assert (
        first_proofs["sentinel_hash"] == second_proofs["sentinel_hash"] == SENTINEL_HASH
    )
    stage_a = json.loads((run_dir / "stage_a.json").read_text())
    assert stage_a["sys_path"][0].endswith("/worktree")
    assert len(stage_a["sys_path"]) == 4
    assert (
        json.loads((run_dir / "bytecode.json").read_text())["scan_roots"]
        == stage_a["sys_path"]
    )
    assert json.loads((run_dir / "audit_canary.json").read_text())["observed"] is True
    inventory = json.loads((run_dir / "import_inventory.json").read_text())
    payload_entry = next(item for item in inventory if item["module"] == "fake_payload")
    assert payload_entry["origin"].endswith("/fake_payload.py")
    assert payload_entry["loader_class"].endswith("SourceFileLoader")
    assert not any(item["module"] == "torch" for item in inventory)
    assert [event["event"] for event in events] == [
        "HELLO",
        "PAYLOAD_STARTED",
        "STAGE_BEGIN",
        "NODE_BEGIN",
        "NODE_END",
        "STAGE_END",
    ]


@pytest.mark.parametrize("planted", ["orphan", "legacy"])
def test_launch_rejects_orphan_and_legacy_bytecode(
    tmp_path: Path, planted: str
) -> None:
    completed, run_dir, events = _launch_bootstrap(tmp_path, planted=planted)
    assert completed.returncode not in (0, 3)
    assert events[0]["event"] == "HELLO"
    assert not (run_dir / "payload_started.json").exists()
    assert "rejected bytecode" in completed.stderr.decode()


def test_stage_a_rejects_missing_and_extra_environment_entries(tmp_path: Path) -> None:
    missing, missing_run, _ = _launch_bootstrap(
        tmp_path / "missing", env_mutator=lambda env: env.pop("OMP_NUM_THREADS")
    )
    extra, extra_run, _ = _launch_bootstrap(
        tmp_path / "extra", env_mutator=lambda env: env.update(M2CR_UNEXPECTED="1")
    )
    for completed, run_dir in ((missing, missing_run), (extra, extra_run)):
        assert completed.returncode not in (0, 3)
        assert "Stage A environment mismatch" in completed.stderr.decode()
        assert not (run_dir / "payload_started.json").exists()


def test_stage_b_empty_stack_has_zero_delta_and_stage_c_detects_drift(
    tmp_path: Path,
) -> None:
    completed, run_dir, _ = _launch_bootstrap(tmp_path / "clean")
    assert completed.returncode == 0, completed.stderr.decode()
    assert json.loads((run_dir / "stage_b_os.json").read_text())["delta"] == {
        "added": {},
        "removed": {},
        "changed": {},
    }
    drifted, drift_run, _ = _launch_bootstrap(tmp_path / "drift", mode="drift")
    assert drifted.returncode not in (0, 3)
    assert "Stage C environment drift" in drifted.stderr.decode()
    assert not (drift_run / "stage_c.json").exists()
    assert (drift_run / "payload_started.json").exists()


def test_duplicate_raw_keys_delta_rules_and_pyc_helpers(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="duplicate"):
        parse_raw_environ_block(b"A=1\0A=2\0")
    empty = classify_stage_b_deltas(
        {"A": "1"}, {"A": "1"}, {"A": "1"}, {"A": "1"}, pid=42, native_stack_modules=[]
    )
    assert empty["accepted"] == []
    accepted = classify_stage_b_deltas(
        {"A": "1"},
        {"A": "1"},
        {"A": "1"},
        {
            "A": "1",
            "__CF_USER_TEXT_ENCODING": "0x1F5:0x0:0x0",
            "__KMP_REGISTERED_LIB_42": "0x1234-cafe1234-libomp.dylib",
        },
        pid=42,
        native_stack_modules=["synthetic_native"],
        stage_b_expected={"__CF_USER_TEXT_ENCODING": "0x1F5:0x0:0x0"},
    )
    assert accepted["accepted"] == [
        "__CF_USER_TEXT_ENCODING",
        "__KMP_REGISTERED_LIB_42",
    ]
    with pytest.raises(ValueError, match="PID"):
        classify_stage_b_deltas(
            {"A": "1"},
            {"A": "1"},
            {"A": "1"},
            {
                "A": "1",
                "__CF_USER_TEXT_ENCODING": "0x1F5:0x0:0x0",
                "__KMP_REGISTERED_LIB_41": "0x1234-cafe1234-libomp.dylib",
            },
            pid=42,
            native_stack_modules=["synthetic_native"],
            stage_b_expected={"__CF_USER_TEXT_ENCODING": "0x1F5:0x0:0x0"},
        )

    with pytest.raises(ValueError, match="frozen value"):
        classify_stage_b_deltas(
            {"A": "1"},
            {"A": "1"},
            {"A": "1"},
            {
                "A": "1",
                "__CF_USER_TEXT_ENCODING": "0x1F5:0x0:0x0",
                "__KMP_REGISTERED_LIB_42": "0x1234-cafe1234-libomp.dylib",
            },
            pid=42,
            native_stack_modules=["synthetic_native"],
            stage_b_expected={"__CF_USER_TEXT_ENCODING": "0x2F5:0x0:0x0"},
        )
    with pytest.raises(ValueError, match="not frozen"):
        classify_stage_b_deltas(
            {"A": "1"},
            {"A": "1"},
            {"A": "1"},
            {
                "A": "1",
                "__CF_USER_TEXT_ENCODING": "0x1F5:0x0:0x0",
                "__KMP_REGISTERED_LIB_42": "0x1234-cafe1234-libomp.dylib",
            },
            pid=42,
            native_stack_modules=["synthetic_native"],
        )

    source = tmp_path / "module.py"
    cache = tmp_path / "__pycache__"
    source.write_text("pass\n")
    cache.mkdir()
    normal = cache / "module.cpython-313.pyc"
    normal.write_bytes(b"pyc")
    orphan = cache / "missing.cpython-313.pyc"
    orphan.write_bytes(b"pyc")
    legacy = tmp_path / "legacy.pyc"
    legacy.write_bytes(b"pyc")
    assert classify_pyc_candidate(normal) is None
    assert classify_pyc_candidate(orphan) == "orphan"
    assert classify_pyc_candidate(legacy) == "legacy_directly_importable"
    rejected = scan_pyc_candidates([os.fspath(tmp_path)])
    assert {item["reason"] for item in rejected} == {
        "orphan",
        "legacy_directly_importable",
    }


def test_payload_module_import_occurs_only_after_marker_and_mark_failure_blocks_it(
    tmp_path: Path,
) -> None:
    completed, run_dir, _ = _launch_bootstrap(tmp_path / "ordered", import_spy=True)
    assert completed.returncode == 0, completed.stderr.decode()
    side_effect = run_dir.parent / "payload_imported.txt"
    marker = run_dir / "payload_started.json"
    assert (
        side_effect.read_text()
        == __import__("hashlib").sha256(marker.read_bytes()).hexdigest()
    )

    failed, failed_run, _ = _launch_bootstrap(
        tmp_path / "mark-failed", import_spy=True, prelaunch=False
    )
    assert failed.returncode not in (0, 3)
    assert "payload boundary mark failed" in failed.stderr.decode()
    assert not (failed_run.parent / "payload_imported.txt").exists()


def test_fake_torch_controls_are_automatic_and_fail_closed(tmp_path: Path) -> None:
    expected = {"__CF_USER_TEXT_ENCODING": "0x1F5:0x0:0x0"}
    completed, run_dir, _ = _launch_bootstrap(
        tmp_path / "ok", fake_torch="ok", stage_b_expected=expected
    )
    assert completed.returncode == 0, completed.stderr.decode()
    assert (run_dir.parent / "thread_calls.txt").read_text().splitlines() == [
        "intra=10",
        "interop=10",
    ]
    inventory = json.loads((run_dir / "import_inventory.json").read_text())
    fake_torch_entry = next(item for item in inventory if item["module"] == "torch")
    assert fake_torch_entry["origin"].startswith(os.fspath(run_dir.parent))

    failed, failed_run, _ = _launch_bootstrap(
        tmp_path / "failed", fake_torch="raise", stage_b_expected=expected
    )
    assert failed.returncode not in (0, 3)
    assert "torch thread controls failed" in failed.stderr.decode()
    assert not (failed_run / "payload_started.json").exists()


def test_fake_stage_b_cf_value_must_equal_exact_frozen_config(tmp_path: Path) -> None:
    wrong, wrong_run, _ = _launch_bootstrap(
        tmp_path / "wrong",
        fake_torch="ok",
        stage_b_expected={"__CF_USER_TEXT_ENCODING": "0x2F5:0x0:0x0"},
    )
    assert wrong.returncode not in (0, 3)
    assert "does not equal frozen value" in wrong.stderr.decode()
    assert not (wrong_run / "payload_started.json").exists()


def _four_manifest_roots(tmp_path: Path) -> list[tuple[str, Path]]:
    roots = [
        ("worktree", tmp_path / "worktree"),
        ("stdlib", tmp_path / "stdlib"),
        ("lib-dynload", tmp_path / "lib-dynload"),
        ("site-packages", tmp_path / "site-packages"),
    ]
    for _, root in roots:
        root.mkdir(parents=True)
    return roots


def test_frozen_manifest_rewalk_passes_and_rejects_added_or_changed_files(
    tmp_path: Path,
) -> None:
    roots = _four_manifest_roots(tmp_path)
    module_path = roots[0][1] / "inside.py"
    module_path.write_text("VALUE = 1\n", encoding="utf-8")
    manifest_path = tmp_path / "manifest.jsonl"
    build_importable_artifact_manifest(roots, manifest_path)
    frozen, _ = _load_importable_artifact_manifest(manifest_path)
    root_paths = [os.fspath(root.resolve()) for _, root in roots]
    assert (
        _verify_importable_artifact_manifest(root_paths, frozen, phase="test")[
            "entry_sets_identical"
        ]
        is True
    )

    added = roots[3][1] / "added.py"
    added.write_text("VALUE = 2\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="added="):
        _verify_importable_artifact_manifest(root_paths, frozen, phase="test")
    added.unlink()
    module_path.write_text("VALUE = 3\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="changed="):
        _verify_importable_artifact_manifest(root_paths, frozen, phase="test")


def test_final_inventory_binds_origins_and_rejects_outside_modules(
    tmp_path: Path,
) -> None:
    roots = _four_manifest_roots(tmp_path)
    inside_path = roots[0][1] / "inside.py"
    inside_path.write_text("VALUE = 1\n", encoding="utf-8")
    manifest_path = tmp_path / "manifest.jsonl"
    build_importable_artifact_manifest(roots, manifest_path)
    frozen, _ = _load_importable_artifact_manifest(manifest_path)
    root_paths = [os.fspath(root.resolve()) for _, root in roots]
    inside = ModuleType("inside")
    inside.__file__ = os.fspath(inside_path)
    inside.__spec__ = spec_from_file_location("inside", inside_path)
    inventory = _inventory(
        [], roots=root_paths, manifest_entries=frozen, modules={"inside": inside}
    )
    assert inventory[0]["resolved_origin"] == os.fspath(inside_path.resolve())
    assert inventory[0]["loader_class"].endswith("SourceFileLoader")

    outside_path = tmp_path / "outside.py"
    outside_path.write_text("VALUE = 2\n", encoding="utf-8")
    outside = ModuleType("outside")
    outside.__file__ = os.fspath(outside_path)
    outside.__spec__ = spec_from_file_location("outside", outside_path)
    with pytest.raises(SystemExit, match="unknown or changed origin"):
        _inventory(
            [],
            roots=root_paths,
            manifest_entries=frozen,
            modules={"outside": outside},
        )
