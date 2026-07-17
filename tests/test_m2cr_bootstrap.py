from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from importlib.machinery import SourceFileLoader
from importlib.util import spec_from_file_location
from pathlib import Path
from types import ModuleType

import pytest

import bistar_gp.m2cr.bootstrap as bootstrap_module
import bistar_gp.m2cr.environment_freeze as environment_freeze
from bistar_gp.m2cr.bootstrap import (
    _encode_nonfinite,
    _header_roots_fault,
    disallowed_native_modules,
    _inventory,
    _load_importable_artifact_manifest,
    _verify_importable_artifact_manifest,
    classify_new_loaded_images,
    classify_pyc_candidate,
    classify_stage_b_deltas,
    parse_raw_environ_block,
    scan_pyc_candidates,
)
from bistar_gp.m2cr.environment_freeze import (
    build_importable_artifact_manifest,
    walk_importable_artifacts,
)
from bistar_gp.m2cr.serialization import canonical_dumps, sha256_file


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
SOURCE_LOADER_CLASS = f"{SourceFileLoader.__module__}.{SourceFileLoader.__qualname__}"

pytestmark = pytest.mark.skipif(
    sys.platform != "darwin", reason="raw _NSGetEnviron is Darwin-specific"
)

# Cross-worker seam: the shared bytecode classifier and the v2 walker land in
# environment_freeze.py in a sibling change; the scan delegates to them.
_SHARED_CLASSIFIER_LANDED = hasattr(environment_freeze, "classify_pyc_candidate")
requires_shared_classifier = pytest.mark.skipif(
    not _SHARED_CLASSIFIER_LANDED,
    reason=(
        "cross-worker seam: environment_freeze.classify_pyc_candidate has "
        "not landed yet; the scan delegates to it and fails closed until "
        "integration reconciles"
    ),
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
    data_path: Path | None = None,
    profile_import: bool = False,
) -> str:
    lines: list[str] = []
    if profile_import:
        lines.append("import bistar_gp.profile_integration")
    if mode == "drift":
        lines.append("os.environ['M2CR_DRIFT'] = '1'")
    elif mode == "nonfinite":
        lines.append(
            'context.emit("EVAL_RESULT", node_index=0, g=float("nan"))'
        )
    elif mode == "tamper_baseline":
        lines.extend(
            [
                "import json as _json",
                "from pathlib import Path as _Path",
                '_target = _Path(os.environ["HOME"]).parent / "stage_b_os.json"',
                "_doc = _json.loads(_target.read_text())",
                '_doc["baseline"]["OMP_NUM_THREADS"] = "99"',
                "_target.write_text(_json.dumps(_doc, sort_keys=True, "
                'separators=(",", ":")))',
            ]
        )
    elif mode == "open_worktree" and data_path is not None:
        lines.append(f"open({os.fspath(data_path)!r}, 'rb').read()")
    if thread_log is not None:
        lines.append(
            f"assert open({os.fspath(thread_log)!r}, encoding='utf-8').read() "
            "== 'intra=10\\ninterop=10\\n'"
        )
    if not lines:
        lines.append("pass")
    mutation = "\n    ".join(lines)
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
    torch_build_expected: object = "auto",
    profile: str | None = None,
) -> tuple[subprocess.CompletedProcess[bytes], Path, list[dict[str, object]]]:
    worktree = tmp_path / "worktree"
    run_dir = worktree / "run"
    worktree.mkdir(parents=True)
    run_dir.mkdir()
    fake_profile_path: Path | None = None
    if profile is None:
        (worktree / "bistar_gp").symlink_to(
            REPOSITORY_ROOT / "bistar_gp", target_is_directory=True
        )
    else:
        # The profile check needs a hashable in-worktree fake module; only
        # the m2cr subpackage is shared with the repository.
        package_dir = worktree / "bistar_gp"
        package_dir.mkdir()
        (package_dir / "m2cr").symlink_to(
            REPOSITORY_ROOT / "bistar_gp" / "m2cr", target_is_directory=True
        )
        fake_profile_path = package_dir / "profile_integration.py"
        fake_profile_path.write_text(
            "FROZEN_PROFILE_MARKER = 1\n", encoding="utf-8"
        )
    data_path: Path | None = None
    if mode == "open_worktree":
        data_path = worktree / "payload_data.txt"
        data_path.write_bytes(b"frozen worktree bytes\n")
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
            data_path=data_path,
            profile_import=profile is not None,
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
_threads = {{"intra": 0, "interop": 0}}


class _Config:
    @staticmethod
    def show():
        return "FAKE_BLAS=accelerate\\nUSE_MKL=OFF"


__config__ = _Config()


def set_num_threads(value):
    _threads["intra"] = value
    _log.write_text(f"intra={{value}}\\n", encoding="utf-8")

def set_num_interop_threads(value):
    _threads["interop"] = value
    with _log.open("a", encoding="utf-8") as handle:
        handle.write(f"interop={{value}}\\n")
    {"raise RuntimeError('synthetic interop failure')" if fake_torch == "raise" else "return None"}

def get_num_threads():
    {"return 9" if fake_torch == "wrong-readback" else 'return _threads["intra"]'}

def get_num_interop_threads():
    return _threads["interop"]
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
    if fake_torch is not None:
        if torch_build_expected == "auto":
            config["torch_build_expected"] = [
                "FAKE_BLAS=accelerate",
                "USE_MKL=OFF",
            ]
        elif torch_build_expected is not None:
            config["torch_build_expected"] = torch_build_expected
    if profile is not None:
        assert fake_profile_path is not None
        config["expected_profile_integration_sha256"] = (
            sha256_file(fake_profile_path) if profile == "match" else "f" * 64
        )
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
    # The frozen §4.5.8 proof set must be present in full; a silently dropped
    # proof would otherwise keep this aggregation green.
    assert set(first_proofs["checks"]) == {
        "optimize",
        "hash_randomization",
        "bound_hash",
        "safe_path",
        "no_user_site",
        "dont_write_bytecode",
        "no_site",
        "isolated",
        "ignore_environment",
    }
    # pycache_prefix equality is proven through its own SystemExit path
    # (bootstrap._effect_proofs verifies canonical equality separately and
    # records the realized value), not as a checks entry.
    assert first_proofs["pycache_prefix"]
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
    modules = inventory["modules"]
    payload_entry = next(item for item in modules if item["module"] == "fake_payload")
    assert payload_entry["origin"].endswith("/fake_payload.py")
    assert payload_entry["loader_class"].endswith("SourceFileLoader")
    assert not any(item["module"] == "torch" for item in modules)
    assert inventory["profile_integration_check"] is None
    assert [event["event"] for event in events] == [
        "HELLO",
        "PAYLOAD_STARTED",
        "STAGE_BEGIN",
        "NODE_BEGIN",
        "NODE_END",
        "STAGE_END",
    ]


@requires_shared_classifier
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


def test_duplicate_raw_keys_and_delta_rules(tmp_path: Path) -> None:
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


@requires_shared_classifier
def test_tolerant_scan_accepts_dotted_and_pytest_tag_caches(tmp_path: Path) -> None:
    """FIX C1: source-backed dotted-stem and pytest-tag caches pass the scan."""

    package = tmp_path / "pkg"
    cache = package / "__pycache__"
    cache.mkdir(parents=True)
    (package / "mod.py").write_text("pass\n", encoding="utf-8")
    (cache / "mod.cpython-313.pyc").write_bytes(b"pyc")
    (package / "v0.9.0.a.py").write_text("pass\n", encoding="utf-8")
    (cache / "v0.9.0.a.cpython-313.pyc").write_bytes(b"pyc")
    (cache / "mod.cpython-313-pytest-8.3.3.pyc").write_bytes(b"pyc")
    assert scan_pyc_candidates([os.fspath(tmp_path)]) == []
    assert classify_pyc_candidate(cache / "mod.cpython-313.pyc") is None
    assert classify_pyc_candidate(cache / "v0.9.0.a.cpython-313.pyc") is None
    assert classify_pyc_candidate(cache / "mod.cpython-313-pytest-8.3.3.pyc") is None


@requires_shared_classifier
def test_scan_still_rejects_true_orphan_and_legacy_bytecode(tmp_path: Path) -> None:
    """FIX C1: the tolerant rule keeps rejecting genuine orphan/legacy pycs."""

    cache = tmp_path / "__pycache__"
    cache.mkdir()
    orphan = cache / "ghost.cpython-313.pyc"
    orphan.write_bytes(b"pyc")
    legacy = tmp_path / "legacy.pyc"
    legacy.write_bytes(b"pyc")
    rejected = {
        item["path"]: item["reason"]
        for item in scan_pyc_candidates([os.fspath(tmp_path)])
    }
    assert set(rejected) == {os.path.realpath(orphan), os.path.realpath(legacy)}
    assert "orphan" in rejected[os.path.realpath(orphan)]
    assert "legacy" in rejected[os.path.realpath(legacy)]
    assert "orphan" in (classify_pyc_candidate(orphan) or "")
    assert "legacy" in (classify_pyc_candidate(legacy) or "")


@requires_shared_classifier
def test_walker_and_scan_agree_on_bytecode_classifications(tmp_path: Path) -> None:
    """FIX C1: one tmp tree through BOTH the walker and the launch scan."""

    roots = _four_manifest_roots(tmp_path)
    worktree = roots[0][1]
    package = worktree / "pkg"
    cache = package / "__pycache__"
    cache.mkdir(parents=True)
    (package / "mod.py").write_text("pass\n", encoding="utf-8")
    (cache / "mod.cpython-313.pyc").write_bytes(b"pyc")
    (package / "v0.9.0.a.py").write_text("pass\n", encoding="utf-8")
    (cache / "v0.9.0.a.cpython-313.pyc").write_bytes(b"pyc")
    (cache / "mod.cpython-313-pytest-8.3.3.pyc").write_bytes(b"pyc")
    (cache / "ghost.cpython-313.pyc").write_bytes(b"pyc")
    (worktree / "legacy.pyc").write_bytes(b"pyc")
    root_paths = {root_id: root.resolve() for root_id, root in roots}
    walker_view = {
        os.path.realpath(root_paths[entry["root"]] / entry["relpath"]): entry[
            "artifact_type"
        ]
        for entry in walk_importable_artifacts(roots)
        if entry["artifact_type"] in ("orphan_bytecode", "legacy_bytecode")
    }
    scan_view = {
        item["path"]: item["reason"]
        for item in scan_pyc_candidates([os.fspath(root) for _, root in roots])
    }
    assert scan_view == walker_view
    assert len(walker_view) == 2


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
    fake_torch_entry = next(
        item for item in inventory["modules"] if item["module"] == "torch"
    )
    assert fake_torch_entry["origin"].startswith(os.fspath(run_dir.parent))
    native = json.loads((run_dir / "native_stack.json").read_text())
    assert native["torch_threads"] == {"intra": 10, "interop": 10}
    assert native["build_markers"]["torch"] == {
        "expected": ["FAKE_BLAS=accelerate", "USE_MKL=OFF"],
        "all_present": True,
    }
    assert native["loaded_images_stage_b"]
    assert native["loaded_images_stage_b"] == sorted(
        native["loaded_images_stage_b"]
    )
    stage_c = json.loads((run_dir / "stage_c.json").read_text())
    assert stage_c["loaded_image_check"]["new_allowed"] == []
    assert stage_c["loaded_image_check"]["stage_b_count"] == len(
        native["loaded_images_stage_b"]
    )

    failed, failed_run, _ = _launch_bootstrap(
        tmp_path / "failed", fake_torch="raise", stage_b_expected=expected
    )
    assert failed.returncode not in (0, 3)
    assert "torch thread controls failed" in failed.stderr.decode()
    assert not (failed_run / "payload_started.json").exists()


def test_fake_torch_readback_and_build_markers_fail_closed(tmp_path: Path) -> None:
    """FIX C8: setter success is insufficient; readback and markers gate."""

    expected = {"__CF_USER_TEXT_ENCODING": "0x1F5:0x0:0x0"}
    readback, readback_run, _ = _launch_bootstrap(
        tmp_path / "readback",
        fake_torch="wrong-readback",
        stage_b_expected=expected,
    )
    assert readback.returncode not in (0, 3)
    assert "torch thread readback mismatch" in readback.stderr.decode()
    assert not (readback_run / "payload_started.json").exists()

    markers, markers_run, _ = _launch_bootstrap(
        tmp_path / "markers",
        fake_torch="ok",
        stage_b_expected=expected,
        torch_build_expected=["ABSENT_MARKER=1"],
    )
    assert markers.returncode not in (0, 3)
    assert "torch build markers missing" in markers.stderr.decode()
    assert not (markers_run / "payload_started.json").exists()

    absent, absent_run, _ = _launch_bootstrap(
        tmp_path / "absent",
        fake_torch="ok",
        stage_b_expected=expected,
        torch_build_expected=None,
    )
    assert absent.returncode not in (0, 3)
    assert "torch_build_expected" in absent.stderr.decode()
    assert not (absent_run / "payload_started.json").exists()


def test_native_stack_helpers_are_hermetic_and_injectable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FIX C8: fake-module/fake-enumerator coverage without any real torch."""

    fake_images = ["/usr/lib/fake_a.dylib", "/usr/lib/fake_b.dylib"]
    monkeypatch.setattr(
        bootstrap_module, "_image_enumerator", lambda: list(fake_images)
    )
    assert bootstrap_module._image_enumerator() == fake_images
    assert classify_new_loaded_images(
        ["/a.dylib"], ["/a.dylib", "/b.dylib", "/c.dylib"], ["/c.dylib"]
    ) == ["/b.dylib"]
    real_images = bootstrap_module._dyld_loaded_images()
    assert real_images and real_images == sorted(real_images)
    assert all(isinstance(path, str) for path in real_images)


def test_loaded_image_hashing_detects_on_disk_byte_drift(tmp_path: Path) -> None:
    """F2 (§4.5.7 'enumeration AND hashing', §4.5.11 rehash at exit): on-disk
    loaded images are hashed and an on-disk byte change between Stage B and
    Stage C is caught as drift; non-file entries are skipped (they are covered
    by the §4.5.2 dyld-cache hash)."""

    image = tmp_path / "fake.dylib"
    image.write_bytes(b"MACH-O-A")
    stable = tmp_path / "stable.dylib"
    stable.write_bytes(b"STABLE")
    paths = [os.fspath(image), os.fspath(stable), "/nonexistent/skip.dylib"]

    stage_b = bootstrap_module.hash_loaded_images(paths)
    assert os.fspath(image) in stage_b and os.fspath(stable) in stage_b
    assert "/nonexistent/skip.dylib" not in stage_b  # non-file skipped
    # No drift when bytes are unchanged.
    assert bootstrap_module.loaded_image_hash_drift(stage_b, dict(stage_b)) == []
    # A byte change to one image between Stage B and Stage C is drift.
    image.write_bytes(b"MACH-O-B")
    stage_c = bootstrap_module.hash_loaded_images(paths)
    assert bootstrap_module.loaded_image_hash_drift(stage_b, stage_c) == [
        os.fspath(image)
    ]
    # CP-2: a Stage-B image unlinked (or replaced by a non-file) at Stage C has
    # no Stage-C hash and must still be flagged as drift, not silently dropped.
    image.unlink()
    stage_c_gone = bootstrap_module.hash_loaded_images(paths)
    assert os.fspath(image) not in stage_c_gone
    assert bootstrap_module.loaded_image_hash_drift(stage_b, stage_c_gone) == [
        os.fspath(image)
    ]


def test_loaded_image_authentication_against_committed_expected_set() -> None:
    """F2 (round-3): every on-disk loaded image is authenticated against the
    committed expected (path, sha256) set BEFORE payload start — a same-path
    pre-launch mutation (mismatch), an image with no committed expectation, and
    a committed-expected image that did not load each fail closed."""

    expected = [
        {"path": "/frozen/a.dylib", "sha256": "a" * 64},
        {"path": "/frozen/b.dylib", "sha256": "b" * 64},
    ]
    # Happy path: exact (path, sha256) match authenticates.
    bootstrap_module.authenticate_loaded_images(
        {"/frozen/a.dylib": "a" * 64, "/frozen/b.dylib": "b" * 64}, expected
    )
    # Same-path pre-launch mutation: the on-disk sha256 differs from committed.
    with pytest.raises(SystemExit, match="sha256 does not match its committed"):
        bootstrap_module.authenticate_loaded_images(
            {"/frozen/a.dylib": "f" * 64, "/frozen/b.dylib": "b" * 64}, expected
        )
    # An image with no committed expectation fails closed.
    with pytest.raises(SystemExit, match="has no committed"):
        bootstrap_module.authenticate_loaded_images(
            {
                "/frozen/a.dylib": "a" * 64,
                "/frozen/b.dylib": "b" * 64,
                "/frozen/rogue.dylib": "c" * 64,
            },
            expected,
        )
    # A committed-expected image that did not load fails closed.
    with pytest.raises(SystemExit, match="did not"):
        bootstrap_module.authenticate_loaded_images(
            {"/frozen/a.dylib": "a" * 64}, expected
        )

    fake_torch = ModuleType("torch")
    fake_torch.get_num_threads = lambda: 10
    fake_torch.get_num_interop_threads = lambda: 10
    assert bootstrap_module._torch_thread_readback(fake_torch) == {
        "intra": 10,
        "interop": 10,
    }
    fake_torch.get_num_interop_threads = lambda: 9
    with pytest.raises(SystemExit, match="readback mismatch"):
        bootstrap_module._torch_thread_readback(fake_torch)

    fake_numpy = ModuleType("numpy")
    fake_numpy.show_config = lambda: "BLAS=accelerate\nLAPACK=accelerate"
    description = bootstrap_module._numpy_build_description(fake_numpy)
    outcome = bootstrap_module._require_build_markers(
        "numpy", description, "numpy_build_expected", ["BLAS=accelerate"]
    )
    assert outcome == {"expected": ["BLAS=accelerate"], "all_present": True}
    with pytest.raises(SystemExit, match="numpy build markers missing"):
        bootstrap_module._require_build_markers(
            "numpy", "nothing here", "numpy_build_expected", ["BLAS=accelerate"]
        )
    with pytest.raises(SystemExit, match="numpy_build_expected"):
        bootstrap_module._require_build_markers(
            "numpy", description, "numpy_build_expected", None
        )


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
    frozen, _, _header = _load_importable_artifact_manifest(manifest_path)
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
    frozen, _, _header = _load_importable_artifact_manifest(manifest_path)
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


def _write_v2_manifest(
    path: Path, roots: list[tuple[str, Path]], entries: list[dict[str, object]]
) -> None:
    header = {
        "kind": "m2cr_importable_artifact_manifest",
        "schema_version": 2,
        "roots": {
            root_id: os.fspath(root.resolve()) for root_id, root in roots
        },
    }
    lines = [canonical_dumps(header)] + [
        canonical_dumps(entry) for entry in entries
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_manifest_v2_header_parses_and_loader_is_enforced(tmp_path: Path) -> None:
    """FIX C9: the at-exit inventory rejects a manifest loader mismatch."""

    roots = _four_manifest_roots(tmp_path)
    inside_path = roots[0][1] / "inside.py"
    inside_path.write_text("VALUE = 1\n", encoding="utf-8")
    entry = {
        "root": "worktree",
        "relpath": "inside.py",
        "artifact_type": "source",
        "sha256": sha256_file(inside_path),
        "size": inside_path.stat().st_size,
        "loader": SOURCE_LOADER_CLASS,
    }
    manifest_path = tmp_path / "manifest_v2.jsonl"
    _write_v2_manifest(manifest_path, roots, [entry])
    frozen, _digest, header = _load_importable_artifact_manifest(manifest_path)
    assert header is not None
    assert header["schema_version"] == 2
    assert header["roots"]["worktree"] == os.fspath(roots[0][1].resolve())
    assert frozen[("worktree", "inside.py")]["loader"] == SOURCE_LOADER_CLASS

    inside = ModuleType("inside")
    inside.__file__ = os.fspath(inside_path)
    inside.__spec__ = spec_from_file_location("inside", inside_path)
    root_paths = [os.fspath(root.resolve()) for _, root in roots]
    inventory = _inventory(
        [], roots=root_paths, manifest_entries=frozen, modules={"inside": inside}
    )
    assert inventory[0]["loader_class"] == SOURCE_LOADER_CLASS

    wrong = dict(entry, loader="zipimport.zipimporter")
    _write_v2_manifest(manifest_path, roots, [wrong])
    frozen_wrong, _digest, _header = _load_importable_artifact_manifest(
        manifest_path
    )
    with pytest.raises(SystemExit, match="loader class mismatch"):
        _inventory(
            [],
            roots=root_paths,
            manifest_entries=frozen_wrong,
            modules={"inside": inside},
        )


def test_manifest_v2_entries_require_the_loader_field(tmp_path: Path) -> None:
    """FIX C9: format v2 (header present) makes 'loader' mandatory per entry."""

    roots = _four_manifest_roots(tmp_path)
    inside_path = roots[0][1] / "inside.py"
    inside_path.write_text("VALUE = 1\n", encoding="utf-8")
    entry = {
        "root": "worktree",
        "relpath": "inside.py",
        "artifact_type": "source",
        "sha256": sha256_file(inside_path),
        "size": inside_path.stat().st_size,
    }
    manifest_path = tmp_path / "manifest_v2.jsonl"
    _write_v2_manifest(manifest_path, roots, [entry])
    with pytest.raises(SystemExit, match="invalid importable manifest entry"):
        _load_importable_artifact_manifest(manifest_path)


def test_nonfinite_event_lines_carry_frozen_sentinels(tmp_path: Path) -> None:
    """FIX C2: a payload-emitted NaN reaches events.jsonl as the sentinel."""

    completed, run_dir, events = _launch_bootstrap(tmp_path, mode="nonfinite")
    assert completed.returncode == 0, completed.stderr.decode()
    eval_events = [event for event in events if event["event"] == "EVAL_RESULT"]
    assert len(eval_events) == 1
    assert eval_events[0]["g"] == {"_nonfinite": "nan"}
    assert eval_events[0]["node_index"] == 0
    assert (run_dir / "payload.json").exists()


def test_encode_nonfinite_covers_all_three_kinds_recursively() -> None:
    """FIX C2: the local stdlib sentinel encoder mirrors plan §5.4."""

    encoded = _encode_nonfinite(
        {
            "g": float("nan"),
            "vector": [float("inf"), float("-inf"), 1.5],
            "nested": {"value": (float("nan"),)},
            "count": 3,
            "flag": True,
        }
    )
    assert encoded == {
        "g": {"_nonfinite": "nan"},
        "vector": [{"_nonfinite": "+inf"}, {"_nonfinite": "-inf"}, 1.5],
        "nested": {"value": [{"_nonfinite": "nan"}]},
        "count": 3,
        "flag": True,
    }


def test_worktree_opens_are_hashed_into_the_inventory_attestation(
    tmp_path: Path,
) -> None:
    """FIX C10: files a payload opens under worktree_root are hashed at exit."""

    completed, run_dir, _ = _launch_bootstrap(tmp_path, mode="open_worktree")
    assert completed.returncode == 0, completed.stderr.decode()
    document = json.loads((run_dir / "import_inventory.json").read_text())
    opens = {item["path"]: item["sha256"] for item in document["worktree_opens"]["hashed"]}
    data_path = os.path.realpath(run_dir.parent / "payload_data.txt")
    assert opens[data_path] == hashlib.sha256(
        b"frozen worktree bytes\n"
    ).hexdigest()
    # The payload module source itself was loaded from the worktree.
    assert any(path.endswith("/fake_payload.py") for path in opens)


def test_profile_integration_explicit_hash_check(tmp_path: Path) -> None:
    """FIX C10: expected_profile_integration_sha256 is an explicit gate."""

    ok, ok_run, _ = _launch_bootstrap(tmp_path / "ok", profile="match")
    assert ok.returncode == 0, ok.stderr.decode()
    check = json.loads((ok_run / "import_inventory.json").read_text())[
        "profile_integration_check"
    ]
    assert check["module_loaded"] is True
    assert check["match"] is True
    assert check["actual_sha256"] == check["expected_sha256"]

    bad, bad_run, _ = _launch_bootstrap(tmp_path / "bad", profile="mismatch")
    assert bad.returncode not in (0, 3)
    assert (
        "profile_integration explicit hash comparison failed"
        in bad.stderr.decode()
    )
    # The comparison outcome is recorded either way, then the child exits.
    recorded = json.loads((bad_run / "import_inventory.json").read_text())[
        "profile_integration_check"
    ]
    assert recorded["module_loaded"] is True
    assert recorded["match"] is False
    assert not (bad_run / "stage_c.json").exists()


def test_stage_c_compares_against_persisted_authenticated_baselines(
    tmp_path: Path,
) -> None:
    """FIX C12: a tampered persisted Stage-B baseline fails authentication."""

    completed, run_dir, _ = _launch_bootstrap(tmp_path, mode="tamper_baseline")
    assert completed.returncode not in (0, 3)
    assert (
        "stage_b_os baseline failed digest authentication"
        in completed.stderr.decode()
    )
    assert (run_dir / "payload_started.json").exists()
    assert not (run_dir / "stage_c.json").exists()
    failure = json.loads((run_dir / "bootstrap_failure.json").read_text())
    assert failure["fault_class"] == "attestation_fault"


def test_header_roots_fault_exempts_the_per_launch_worktree(tmp_path: Path) -> None:
    """External audit F2: the worktree header path is per-launch and exempt
    from physical-path equality; the three host-global roots are not."""

    launch_roots = [
        os.fspath(tmp_path / "fresh-worktree"),
        "/opt/base/lib/python3.13",
        "/opt/base/lib/python3.13/lib-dynload",
        "/opt/base/lib/python3.13/site-packages",
    ]
    # Header worktree is the freeze-time temp path, DIFFERENT from the launch
    # worktree, but the three host-global roots match: no fault.
    header = {
        "worktree": "/tmp/freeze-time-worktree",
        "stdlib": "/opt/base/lib/python3.13",
        "lib-dynload": "/opt/base/lib/python3.13/lib-dynload",
        "site-packages": "/opt/base/lib/python3.13/site-packages",
    }
    assert _header_roots_fault(header, launch_roots) is None

    # A mismatched host-global root still faults.
    wrong = dict(header, stdlib="/opt/other/lib/python3.13")
    assert _header_roots_fault(wrong, launch_roots) == (
        "manifest header roots do not match four_roots"
    )

    # A missing root id faults.
    incomplete = {k: v for k, v in header.items() if k != "site-packages"}
    assert "name exactly the four frozen root ids" in _header_roots_fault(
        incomplete, launch_roots
    )


def test_native_stack_allowlist_rejects_bistar_gp_and_payload_modules():
    """External audit round-2 F3: native_stack_modules is restricted to the
    frozen native stack so nothing scientific runs before the marker."""

    assert disallowed_native_modules(["torch", "numpy", "scipy.linalg"]) == []
    assert disallowed_native_modules(["bistar_gp.profile_integration"]) == [
        "bistar_gp.profile_integration"
    ]
    assert disallowed_native_modules(["fake_payload"]) == ["fake_payload"]
    assert disallowed_native_modules(["os", "torch"]) == ["os"]
