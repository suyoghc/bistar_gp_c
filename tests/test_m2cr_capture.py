from __future__ import annotations

import json
import os
import signal
import subprocess
import threading
import time
from pathlib import Path

import pytest

import bistar_gp.m2cr.capture as capture_module
from bistar_gp.m2cr.capture import (
    BOOTSTRAP_CONFIG_NAME,
    RAW_MANIFEST_NAME,
    TERMINAL_RECORD_NAME,
    LaunchConfig,
    capture_run,
    reconcile_run,
    validate_terminal_record,
)
from bistar_gp.m2cr.serialization import canonical_dumps, sha256_file


MINICONDA_PYTHON = "/opt/homebrew/Caskroom/miniconda/base/bin/python3.13"
MINICONDA_ROOT = Path("/opt/homebrew/Caskroom/miniconda/base")
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = REPOSITORY_ROOT / "bistar_gp/m2cr/bootstrap.py"
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


def _aggregate_source() -> str:
    return """{
        "verdict_class": {
            "restart_count": 0, "retry_count": 0, "retry_failure_count": 0,
            "rcond_fail_count": 0, "symmetry_fail_count": 0, "battery_fail_count": 0
        },
        "diagnostic_class": {
            "restart_count": 0, "retry_count": 0, "retry_failure_count": 0,
            "rcond_fail_count": 0, "symmetry_fail_count": 0, "battery_fail_count": 0
        }
    }"""


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


def _payload_source(mode: str, marker_path: Path) -> str:
    if mode == "spin":
        body = """
    context.emit("STAGE_BEGIN", stage_id="level0")
    context.emit("NODE_BEGIN", node_index=0)
    while True:
        pass
"""
    else:
        end = (
            ""
            if mode == "unbalanced"
            else 'context.emit("STAGE_END", stage_id="level0")'
        )
        stages = """[{
            "stage_id": "level0", "stage_class": "verdict",
            "status": "COMPLETED", "nodes_evaluated": 1, "nodes_total": 1
        }]"""
        marker_mutation = ""
        if mode == "delete_marker":
            marker_mutation = f"os.unlink({os.fspath(marker_path)!r})"
        elif mode == "tamper_marker":
            marker_mutation = f"open({os.fspath(marker_path)!r}, 'ab').write(b'\\n')"
        node_records = (
            '[{"node_index": 0}]'
            if mode == "invalid"
            else repr([_failed_node_record()])
        )
        aggregates = _aggregate_source()
        if mode == "false_aggregates":
            aggregates = aggregates.replace(
                '"restart_count": 0', '"restart_count": 1', 1
            )
        body = f"""
    import os
    context.emit("STAGE_BEGIN", stage_id="level0")
    context.emit("NODE_BEGIN", node_index=0)
    context.emit("NODE_END", node_index=0)
    {end}
    {marker_mutation}
    return {{
        "status": "COMPLETED",
        "stages": {stages},
        "aggregates": {aggregates},
        "node_records": {node_records}
    }}
"""
    return "def run(context):\n" + body


def _frozen_environment(run_dir: Path, *, unexpected: bool = False) -> dict[str, str]:
    environment = {
        "PYTHONHASHSEED": "0",
        "OMP_NUM_THREADS": "10",
        "OMP_DYNAMIC": "FALSE",
        "MKL_NUM_THREADS": "10",
        "VECLIB_MAXIMUM_THREADS": "10",
        "LC_ALL": "C",
        "TZ": "UTC",
        "PATH": "/usr/bin:/bin",
        "HOME": os.fspath((run_dir / "home").resolve()),
        "TMPDIR": os.fspath((run_dir / "tmp").resolve()),
        "XDG_CACHE_HOME": os.fspath((run_dir / "xdg/cache").resolve()),
        "XDG_CONFIG_HOME": os.fspath((run_dir / "xdg/config").resolve()),
        "XDG_DATA_HOME": os.fspath((run_dir / "xdg/data").resolve()),
        "XDG_STATE_HOME": os.fspath((run_dir / "xdg/state").resolve()),
    }
    if unexpected:
        environment["M2CR_UNEXPECTED"] = "1"
    return environment


def _make_launch(
    tmp_path: Path,
    *,
    mode: str = "completed",
    ceiling_hours: float = 0.01,
    waiter=None,
    bad_interpreter: bool = False,
    wrong_environment: bool = False,
) -> LaunchConfig:
    worktree = tmp_path / "worktree"
    run_dir = tmp_path / "run"
    worktree.mkdir(parents=True)
    run_dir.mkdir()
    (worktree / "bistar_gp").symlink_to(
        REPOSITORY_ROOT / "bistar_gp", target_is_directory=True
    )
    payload_path = worktree / "fake_payload.py"
    payload_path.write_text(
        _payload_source(mode, run_dir / "payload_started.json"), encoding="utf-8"
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
    bootstrap_config = {
        "four_roots": roots,
        "expected_sentinel_hash": -2671292046718125608,
        "native_stack_modules": [],
        "payload": {"entry": "fake_payload:run", "pass_context": True},
        "payload_entry_path": os.fspath(payload_path),
        "attestation_paths": {
            "payload_started": os.fspath(run_dir / "payload_started.json")
        },
    }
    environment = _frozen_environment(run_dir, unexpected=wrong_environment)
    if wrong_environment:
        bootstrap_config["expected_frozen_env"] = _frozen_environment(run_dir)
    (run_dir / BOOTSTRAP_CONFIG_NAME).write_text(
        canonical_dumps(bootstrap_config), encoding="utf-8"
    )
    arguments = {
        "interpreter_path": "/definitely/missing/python"
        if bad_interpreter
        else MINICONDA_PYTHON,
        "interpreter_flags": (
            "-S",
            "-s",
            "-P",
            "-B",
            "-X",
            "pycache_prefix={pycache_prefix}",
        ),
        "bootstrap_path": os.fspath(BOOTSTRAP),
        "worktree_root": os.fspath(worktree),
        "run_dir": os.fspath(run_dir),
        "frozen_env": environment,
        "authorization_id": AUTHORIZATION_ID,
        "launch_attempt_id": LAUNCH_ATTEMPT_ID,
        "run_id": "m2cr-capture-test",
        "record_kind": "diagnostic",
        "chain": dict(CHAIN),
        "wall_clock_ceiling_hours": ceiling_hours,
    }
    if waiter is not None:
        arguments["waiter"] = waiter
    return LaunchConfig(**arguments)


def _manifest_entries(run_dir: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in (run_dir / RAW_MANIFEST_NAME).read_text().splitlines():
        digest, relative = line.split("  ", 1)
        result[relative] = digest
    return result


def test_happy_path_real_subprocess_and_frozen_write_order(tmp_path: Path) -> None:
    config = _make_launch(tmp_path)
    record = capture_run(config)
    run_dir = Path(config.run_dir)
    assert record["status"] == "COMPLETED"
    assert record["not_a_result"] is True
    assert (run_dir / "spawned.json").exists()
    assert (
        json.loads((run_dir / "events.jsonl").read_text().splitlines()[0])["event"]
        == "HELLO"
    )
    assert record["evidence"]["event_stream_balanced"] is True
    inventory = json.loads((run_dir / "import_inventory.json").read_text())
    assert not any(item["module"] == "torch" for item in inventory)
    validate_terminal_record(record)

    entries = _manifest_entries(run_dir)
    assert RAW_MANIFEST_NAME not in entries
    assert TERMINAL_RECORD_NAME not in entries
    for relative, digest in entries.items():
        assert sha256_file(run_dir / relative) == digest
    expected_paths = {
        path.relative_to(run_dir).as_posix()
        for path in run_dir.rglob("*")
        if path.is_file() and path.name not in {RAW_MANIFEST_NAME, TERMINAL_RECORD_NAME}
    }
    assert set(entries) == expected_paths
    assert (run_dir / RAW_MANIFEST_NAME).stat().st_mtime_ns <= (
        run_dir / TERMINAL_RECORD_NAME
    ).stat().st_mtime_ns


def test_child_sigkill_preserves_flushed_partial_stream(tmp_path: Path) -> None:
    config = _make_launch(tmp_path, mode="spin")
    result: dict[str, object] = {}

    def capture() -> None:
        result["record"] = capture_run(config)

    thread = threading.Thread(target=capture)
    thread.start()
    spawned_path = Path(config.run_dir) / "spawned.json"
    deadline = time.monotonic() + 10
    while not spawned_path.exists() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert spawned_path.exists()
    events_path = Path(config.run_dir) / "events.jsonl"
    while time.monotonic() < deadline:
        if events_path.exists() and '"event":"NODE_BEGIN"' in events_path.read_text():
            break
        time.sleep(0.01)
    assert '"event":"NODE_BEGIN"' in events_path.read_text()
    os.kill(json.loads(spawned_path.read_text())["pid"], signal.SIGKILL)
    thread.join(timeout=10)
    assert not thread.is_alive()
    record = result["record"]
    assert record["status"] == "INFRA_FAILURE"
    assert record["fault"]["fault_class"] == "child_death"
    assert record["evidence"]["event_stream_balanced"] is False
    lines = (Path(config.run_dir) / "events.jsonl").read_text().splitlines()
    assert any(json.loads(line)["event"] == "NODE_BEGIN" for line in lines)
    validate_terminal_record(record)


def test_budget_kill_outranks_waiter_capture_fault(tmp_path: Path) -> None:
    def faulty_waiter(process: subprocess.Popen[bytes], timeout: float) -> None:
        raise RuntimeError("injected capture fault after SIGTERM")

    config = _make_launch(
        tmp_path, mode="spin", ceiling_hours=0.0001, waiter=faulty_waiter
    )
    record = capture_run(config)
    assert record["status"] == "ABORTED_BUDGET"
    assert record["interruption"]["signal_sequence"][0] == "SIGTERM"
    assert record["interruption"]["grace_seconds"] == 30
    assert record["interruption"]["sigkill_issued"] is True
    validate_terminal_record(record)


def test_stage_a_attestation_fault_is_pre_payload_and_nonconsuming(
    tmp_path: Path,
) -> None:
    config = _make_launch(tmp_path, wrong_environment=True)
    record = capture_run(config)
    run_dir = Path(config.run_dir)
    assert record["status"] == "INFRA_FAILURE"
    assert record["fault"]["fault_class"] == "attestation_fault"
    assert record["fault"]["payload_started"] is False
    assert not (run_dir / "payload_started.json").exists()
    validate_terminal_record(record)


def test_no_confirmed_spawn_is_not_started(tmp_path: Path) -> None:
    config = _make_launch(tmp_path, bad_interpreter=True)
    record = capture_run(config)
    assert record["status"] == "NOT_STARTED"
    assert record["not_started"]["prelaunch_sha256"] == sha256_file(
        Path(config.run_dir) / "prelaunch.json"
    )
    assert not (Path(config.run_dir) / "spawned.json").exists()
    validate_terminal_record(record)


def test_parent_death_reconciliation_marks_only_envelope_reconstructed(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "reconcile"
    run_dir.mkdir()
    (run_dir / "prelaunch.json").write_text(canonical_dumps({"launch": 1}))
    (run_dir / "spawned.json").write_text(canonical_dumps({"pid": 123}))
    (run_dir / "events.jsonl").write_text(
        canonical_dumps({"seq": 0, "event": "HELLO"}) + "\n"
    )
    (run_dir / "stdout.txt").write_bytes(b"partial stdout")
    (run_dir / "stderr.txt").write_bytes(b"")
    config = {
        "record_kind": "diagnostic",
        "run_id": "m2cr-reconcile-test",
        "launch_attempt_id": LAUNCH_ATTEMPT_ID,
        "chain": CHAIN,
    }
    record = reconcile_run(run_dir, config)
    assert record["status"] == "INFRA_FAILURE"
    assert record["fault"]["reconstructed"] is True
    assert record["fault"]["payload_started"] is False
    validate_terminal_record(record)


def test_protocol_exit_with_unbalanced_stream_becomes_capture_fault(
    tmp_path: Path,
) -> None:
    config = _make_launch(tmp_path, mode="unbalanced")
    record = capture_run(config)
    assert record["status"] == "INFRA_FAILURE"
    assert record["fault"]["fault_class"] == "capture_fault"
    assert record["evidence"]["event_stream_balanced"] is False
    validate_terminal_record(record)


def test_schema_invalid_protocol_payload_becomes_infra_failure(tmp_path: Path) -> None:
    config = _make_launch(tmp_path, mode="invalid")
    record = capture_run(config)
    assert record["status"] == "INFRA_FAILURE"
    assert record["fault"]["fault_class"] == "schema_invalid_payload"
    assert "invalid per-node evidence" in record["fault"]["detail"]
    validate_terminal_record(record)


@pytest.mark.parametrize("mode", ["delete_marker", "tamper_marker"])
def test_post_payload_marker_loss_or_tamper_is_infrastructure_failure(
    tmp_path: Path, mode: str
) -> None:
    config = _make_launch(tmp_path, mode=mode)
    record = capture_run(config)
    run_dir = Path(config.run_dir)
    assert (run_dir / "payload.json").exists()
    assert record["status"] == "INFRA_FAILURE"
    assert record["fault"]["fault_class"] == "attestation_fault"
    assert "payload marker" in record["fault"]["detail"]
    assert record["fault"]["payload_started"] is (mode == "tamper_marker")
    validate_terminal_record(record)


def test_false_payload_aggregates_are_recomputed_and_rejected(tmp_path: Path) -> None:
    config = _make_launch(tmp_path, mode="false_aggregates")
    record = capture_run(config)
    assert record["status"] == "INFRA_FAILURE"
    assert record["fault"]["fault_class"] == "schema_invalid_payload"
    assert "aggregates differ" in record["fault"]["detail"]
    validate_terminal_record(record)


def test_config_parse_failure_after_hello_is_infra_not_not_started(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _make_launch(tmp_path)
    real_popen = subprocess.Popen

    def corrupt_config_then_spawn(argv, *args, **kwargs):
        Path(argv[-2]).write_text("{", encoding="utf-8")
        return real_popen(argv, *args, **kwargs)

    monkeypatch.setattr(capture_module.subprocess, "Popen", corrupt_config_then_spawn)
    record = capture_run(config)
    run_dir = Path(config.run_dir)
    assert (run_dir / "spawned.json").exists()
    assert (
        json.loads((run_dir / "events.jsonl").read_text().splitlines()[0])["event"]
        == "HELLO"
    )
    assert (run_dir / "bootstrap_failure.json").exists()
    assert record["status"] == "INFRA_FAILURE"
    assert record["fault"]["fault_class"] == "other"
    validate_terminal_record(record)
