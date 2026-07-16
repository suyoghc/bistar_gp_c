from __future__ import annotations

import dataclasses
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
    FROZEN_INTERPRETER_FLAGS,
    RAW_MANIFEST_NAME,
    TERMINAL_RECORD_NAME,
    WALL_CLOCK_CEILING_HOURS,
    LaunchConfig,
    RecordAssemblyError,
    capture_run,
    enumerate_bootstrap_closure,
    launch_config_from_freeze,
    reconcile_run,
    validate_terminal_record,
    verify_preboundary_attestation_set,
)
from bistar_gp.m2cr.serialization import (
    atomic_write_canonical_json,
    canonical_dumps,
    sha256_file,
)


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


def _payload_source(
    mode: str, marker_path: Path, extra_code: str = ""
) -> str:
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
    {extra_code}
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
    extra_payload_code: str = "",
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
        _payload_source(
            mode, run_dir / "payload_started.json", extra_payload_code
        ),
        encoding="utf-8",
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
    assert not any(item["module"] == "torch" for item in inventory["modules"])
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


def test_spawn_confirmation_write_failure_propagates_as_capture_fault(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FIX C3(a): a failed spawned.json write can never yield NOT_STARTED."""

    config = _make_launch(tmp_path)
    real_write = capture_module.atomic_write_canonical_json

    def failing_write(path, obj):
        if os.fspath(path).endswith("spawned.json"):
            raise OSError("synthetic spawn confirmation write failure")
        return real_write(path, obj)

    monkeypatch.setattr(
        capture_module, "atomic_write_canonical_json", failing_write
    )
    record = capture_run(config)
    run_dir = Path(config.run_dir)
    assert not (run_dir / "spawned.json").exists()
    assert record["status"] == "INFRA_FAILURE"
    assert record["fault"]["fault_class"] == "capture_fault"
    assert "spawn confirmation lost" in record["fault"]["detail"]
    assert "synthetic spawn confirmation write failure" in record["fault"]["detail"]
    validate_terminal_record(record)


def test_spawn_confirmation_silently_lost_with_child_evidence_is_infra(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FIX C3(b): child evidence without spawned.json is never NOT_STARTED."""

    config = _make_launch(tmp_path)
    real_write = capture_module.atomic_write_canonical_json

    def skipping_write(path, obj):
        if os.fspath(path).endswith("spawned.json"):
            return "0" * 64  # the confirmation silently never became durable
        return real_write(path, obj)

    monkeypatch.setattr(
        capture_module, "atomic_write_canonical_json", skipping_write
    )
    record = capture_run(config)
    run_dir = Path(config.run_dir)
    assert not (run_dir / "spawned.json").exists()
    assert (run_dir / "payload_started.json").exists()
    assert record["status"] == "INFRA_FAILURE"
    assert record["fault"]["fault_class"] == "capture_fault"
    assert "spawn confirmation lost" in record["fault"]["detail"]
    assert "child evidence exists" in record["fault"]["detail"]
    assert record["fault"]["payload_started"] is True
    validate_terminal_record(record)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("run_id", "BAD ID"),
        ("launch_attempt_id", "launch-1"),
        ("authorization_id", "auth-1"),
        ("chain", {"authorization_id": "m2cr-auth-20260716-01"}),
    ],
)
def test_pre_spawn_validation_raises_before_any_artifact(
    tmp_path: Path, field: str, value: object
) -> None:
    """FIX C4: identity validation precedes prelaunch.json and any child."""

    config = _make_launch(tmp_path)
    bad = dataclasses.replace(config, **{field: value})
    with pytest.raises(RecordAssemblyError):
        capture_run(bad)
    run_dir = Path(config.run_dir)
    assert not (run_dir / "prelaunch.json").exists()
    assert not (run_dir / "spawned.json").exists()
    assert not (run_dir / "events.jsonl").exists()
    assert not (run_dir / TERMINAL_RECORD_NAME).exists()
    assert not (run_dir / "home").exists()


def test_terminal_assembly_failure_falls_back_to_last_resort_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FIX C4: an injected assembly error still yields a schema-valid record."""

    config = _make_launch(tmp_path)

    def exploding_assembly(*args, **kwargs):
        raise RecordAssemblyError("synthetic terminal assembly explosion")

    monkeypatch.setattr(
        capture_module, "assemble_terminal_record", exploding_assembly
    )
    record = capture_run(config)
    run_dir = Path(config.run_dir)
    assert record["status"] == "INFRA_FAILURE"
    assert record["fault"]["fault_class"] == "other"
    assert record["fault"]["reconstructed"] is False
    assert "terminal assembly failed for status" in record["fault"]["detail"]
    assert "synthetic terminal assembly explosion" in record["fault"]["detail"]
    written = json.loads((run_dir / TERMINAL_RECORD_NAME).read_text())
    assert written == record
    validate_terminal_record(record)


@pytest.mark.parametrize(
    "blocker",
    [
        "prelaunch.json",
        "spawned.json",
        "payload_started.json",
        "events.jsonl",
        RAW_MANIFEST_NAME,
        TERMINAL_RECORD_NAME,
    ],
)
def test_stale_run_dir_evidence_refuses_launch(tmp_path: Path, blocker: str) -> None:
    """FIX C5: a run directory is single-use; prior evidence refuses launch."""

    config = _make_launch(tmp_path)
    run_dir = Path(config.run_dir)
    (run_dir / blocker).write_bytes(b"stale")
    with pytest.raises(ValueError, match="not reusable"):
        capture_run(config)
    assert not (run_dir / "spawned.json").exists() or blocker == "spawned.json"
    if blocker != "prelaunch.json":
        assert not (run_dir / "prelaunch.json").exists()


def test_escaping_attestation_path_refuses_launch_pre_spawn(tmp_path: Path) -> None:
    """FIX C6: every attestation path must resolve inside run_dir."""

    config = _make_launch(tmp_path)
    run_dir = Path(config.run_dir)
    template = json.loads((run_dir / BOOTSTRAP_CONFIG_NAME).read_text())
    template["attestation_paths"]["stage_a"] = os.fspath(
        tmp_path / "outside" / "stage_a.json"
    )
    (run_dir / BOOTSTRAP_CONFIG_NAME).write_text(
        canonical_dumps(template), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="escapes the self-contained run"):
        capture_run(config)
    assert not (run_dir / "prelaunch.json").exists()
    assert not (run_dir / "spawned.json").exists()
    assert not (run_dir / TERMINAL_RECORD_NAME).exists()


def test_bootstrap_closure_enumeration_is_import_only(tmp_path: Path) -> None:
    """FIX C7(a): the pinned interpreter enumerates the bootstrap closure."""

    closure = enumerate_bootstrap_closure(
        MINICONDA_PYTHON, BOOTSTRAP, REPOSITORY_ROOT
    )
    assert closure
    modules = [entry["module"] for entry in closure]
    assert modules == sorted(modules)
    bootstrap_entries = [
        entry for entry in closure if entry["module"] == "bistar_gp.m2cr.bootstrap"
    ]
    assert len(bootstrap_entries) == 1
    assert bootstrap_entries[0]["origin"] == os.fspath(BOOTSTRAP.resolve())
    for entry in closure:
        assert os.path.isfile(entry["origin"])
    # Import-only: no scientific stack may enter the pre-boundary closure.
    assert "torch" not in modules
    assert "numpy" not in modules
    assert "json" in modules


def _preboundary_attestation_document(
    tmp_path: Path, *, tampered: bool
) -> tuple[Path, Path]:
    closure_file = tmp_path / "closure_member.py"
    closure_file.write_text("CLOSURE = 1\n", encoding="utf-8")
    digest = "0" * 64 if tampered else sha256_file(closure_file)
    artifact = {
        "kind": "m2cr_preboundary_attestation_set",
        "schema_version": 1,
        "interpreter_binary": {"path": "/nonexistent/python", "sha256": "1" * 64},
        "dyld": {"path": "/nonexistent/dyld", "sha256": "2" * 64},
        "dyld_shared_cache": {
            "main": {"path": "/nonexistent/cache", "sha256": "3" * 64},
            "declared_subcache_count": 0,
            "discovered_subcache_count": 0,
            "subcaches": [],
        },
        "bootstrap_closure": [
            {"path": os.fspath(closure_file), "sha256": digest}
        ],
    }
    attestation_path = tmp_path / "preboundary_attestation_set.json"
    atomic_write_canonical_json(attestation_path, artifact)
    return attestation_path, closure_file


def test_preboundary_attestation_set_verifies_before_spawn(tmp_path: Path) -> None:
    """FIX C7(b): pinned digests verify pre-spawn; hermetic skips honored."""

    attestation_path, _ = _preboundary_attestation_document(
        tmp_path, tampered=False
    )
    outcome = verify_preboundary_attestation_set(
        attestation_path, skip=("interpreter", "dyld")
    )
    assert outcome == {"interpreter": 0, "dyld": 0, "closure": 1}
    config = dataclasses.replace(
        _make_launch(tmp_path),
        preboundary_attestation_set=os.fspath(attestation_path),
        preboundary_skip=("interpreter", "dyld"),
    )
    record = capture_run(config)
    assert record["status"] == "COMPLETED"
    validate_terminal_record(record)


def test_preboundary_mutation_during_run_forces_infra_at_post_exit(
    tmp_path: Path,
) -> None:
    """External audit F3: a pre-boundary file valid at spawn but mutated
    during execution is caught by parent-side post-exit re-attestation
    (§4.5.11), forcing INFRA_FAILURE rather than yielding COMPLETED."""

    attestation_path, closure_file = _preboundary_attestation_document(
        tmp_path, tampered=False
    )
    # The payload appends to the pinned closure member while it runs, so the
    # pre-spawn check passes but the post-exit re-attestation fails.
    config = dataclasses.replace(
        _make_launch(
            tmp_path,
            extra_payload_code=(
                f"open({os.fspath(closure_file)!r}, 'ab').write(b'drift\\n')"
            ),
        ),
        preboundary_attestation_set=os.fspath(attestation_path),
        preboundary_skip=("interpreter", "dyld"),
    )
    record = capture_run(config)
    assert record["status"] == "INFRA_FAILURE"
    assert "post-exit pre-boundary re-attestation" in record["fault"]["detail"]
    validate_terminal_record(record)


def test_tampered_preboundary_attestation_refuses_launch(tmp_path: Path) -> None:
    """FIX C7(b): a digest mismatch refuses launch with no spawn."""

    attestation_path, closure_file = _preboundary_attestation_document(
        tmp_path, tampered=True
    )
    config = dataclasses.replace(
        _make_launch(tmp_path),
        preboundary_attestation_set=os.fspath(attestation_path),
        preboundary_skip=("interpreter", "dyld"),
    )
    with pytest.raises(ValueError, match="preboundary attestation mismatch"):
        capture_run(config)
    run_dir = Path(config.run_dir)
    assert not (run_dir / "prelaunch.json").exists()
    assert not (run_dir / "spawned.json").exists()
    assert not (run_dir / TERMINAL_RECORD_NAME).exists()
    # The closure entries are never skippable: no such token exists.
    with pytest.raises(ValueError, match="unknown preboundary skip tokens"):
        verify_preboundary_attestation_set(
            attestation_path, skip=("interpreter", "dyld", "closure")
        )


def _freeze_fixture(tmp_path: Path) -> dict[str, Path]:
    worktree = tmp_path / "worktree"
    (worktree / "bistar_gp" / "m2cr").mkdir(parents=True)
    fake_bootstrap = worktree / "bistar_gp" / "m2cr" / "bootstrap.py"
    fake_bootstrap.write_text("# fixture bootstrap\n", encoding="utf-8")
    roots = {
        "worktree": worktree,
        "stdlib": tmp_path / "stdlib",
        "lib-dynload": tmp_path / "lib-dynload",
        "site-packages": tmp_path / "site-packages",
    }
    for name, root in roots.items():
        root.mkdir(exist_ok=True)

    artifacts_dir = tmp_path / "freeze"
    artifacts_dir.mkdir()
    pin_path = artifacts_dir / "interpreter_pin.json"
    atomic_write_canonical_json(
        pin_path,
        {
            "path": "/fixture/interpreter/python3.13",
            "realpath": "/fixture/interpreter/python3.13",
            "version": {"implementation": "cpython"},
            "sha256": "4" * 64,
        },
    )
    mapping_path = artifacts_dir / "child_env_mapping.json"
    atomic_write_canonical_json(
        mapping_path,
        {
            "fixed": {"PYTHONHASHSEED": "0", "LC_ALL": "C"},
            "run_local_keys": ["HOME", "TMPDIR"],
            "path_policy": "minimal",
        },
    )
    inside = roots["worktree"] / "inside.py"
    inside.write_text("VALUE = 1\n", encoding="utf-8")
    header = {
        "kind": "m2cr_importable_artifact_manifest",
        "schema_version": 2,
        "roots": {
            name: os.fspath(root.resolve()) for name, root in roots.items()
        },
    }
    entry = {
        "root": "worktree",
        "relpath": "inside.py",
        "artifact_type": "source",
        "sha256": sha256_file(inside),
        "size": inside.stat().st_size,
        "loader": "_frozen_importlib_external.SourceFileLoader",
    }
    manifest_path = artifacts_dir / "importable_artifact_manifest.jsonl"
    manifest_path.write_text(
        canonical_dumps(header) + "\n" + canonical_dumps(entry) + "\n",
        encoding="utf-8",
    )
    attestation_path, _ = _preboundary_attestation_document(
        artifacts_dir, tampered=False
    )
    freeze_path = tmp_path / "environment_freeze_manifest.json"
    atomic_write_canonical_json(
        freeze_path,
        {
            "kind": "m2cr_environment_freeze_manifest",
            "schema_version": 1,
            "artifacts": {
                "child_env_mapping": {
                    "path": os.fspath(mapping_path),
                    "sha256": sha256_file(mapping_path),
                },
                "importable_artifact_manifest": {
                    "path": os.fspath(manifest_path),
                    "sha256": sha256_file(manifest_path),
                },
                "interpreter_pin": {
                    "path": os.fspath(pin_path),
                    "sha256": sha256_file(pin_path),
                },
                "preboundary_attestation_set": {
                    "path": os.fspath(attestation_path),
                    "sha256": sha256_file(attestation_path),
                },
            },
        },
    )
    infrastructure_path = tmp_path / "infrastructure_manifest.json"
    atomic_write_canonical_json(
        infrastructure_path,
        {
            "kind": "m2cr_infrastructure_manifest",
            "schema_version": 1,
            "code": {},
            "artifacts": {
                "environment_freeze_manifest": {
                    "path": os.fspath(freeze_path),
                    "sha256": sha256_file(freeze_path),
                }
            },
            "r1_schemas": {},
        },
    )
    template_path = tmp_path / "bootstrap_template.json"
    atomic_write_canonical_json(
        template_path,
        {
            "expected_sentinel_hash": -2671292046718125608,
            "native_stack_modules": [],
            "payload": {"entry": "fake_payload:run", "pass_context": True},
        },
    )
    return {
        "freeze": freeze_path,
        "infrastructure": infrastructure_path,
        "template": template_path,
        "worktree": worktree,
        "manifest": manifest_path,
        "attestation_set": attestation_path,
        "mapping": mapping_path,
        "run_dir": tmp_path / "run",
    }



def _bound_chain(env_freeze_path, infrastructure_path):
    """A chain whose static members match the authenticated artifacts, as
    launch_config_from_freeze now requires (external audit round-2 F2)."""

    return {
        **CHAIN,
        "environment_freeze_manifest_sha256": sha256_file(env_freeze_path),
        "infrastructure_manifest_sha256": sha256_file(infrastructure_path),
        "authorization_id": AUTHORIZATION_ID,
    }


def test_launch_config_from_freeze_derives_all_pins(tmp_path: Path) -> None:
    """FIX C11: hermetic derivation from tmp freeze artifacts."""

    fixture = _freeze_fixture(tmp_path)
    config = launch_config_from_freeze(
        fixture["freeze"],
        fixture["infrastructure"],
        run_dir=fixture["run_dir"],
        run_id="m2cr-derived-test",
        authorization_id=AUTHORIZATION_ID,
        launch_attempt_id=LAUNCH_ATTEMPT_ID,
        record_kind="diagnostic",
        chain=_bound_chain(fixture["freeze"], fixture["infrastructure"]),
        bootstrap_template_path=fixture["template"],
        worktree_root=fixture["worktree"],
    )
    assert config.interpreter_path == "/fixture/interpreter/python3.13"
    assert tuple(config.interpreter_flags) == FROZEN_INTERPRETER_FLAGS
    assert config.frozen_env == {
        "fixed": {"PYTHONHASHSEED": "0", "LC_ALL": "C"},
        "run_local_keys": ["HOME", "TMPDIR"],
    }
    assert Path(config.worktree_root) == fixture["worktree"].resolve()
    assert config.bootstrap_path.endswith("bistar_gp/m2cr/bootstrap.py")
    assert config.preboundary_attestation_set == os.fspath(
        fixture["attestation_set"].resolve()
    )
    assert config.wall_clock_ceiling_hours == WALL_CLOCK_CEILING_HOURS == 8.0
    assert config.run_id == "m2cr-derived-test"
    assert config.record_kind == "diagnostic"
    assert config.chain == _bound_chain(fixture["freeze"], fixture["infrastructure"])
    materialized = json.loads(
        (fixture["run_dir"] / BOOTSTRAP_CONFIG_NAME).read_text()
    )
    assert materialized["four_roots"][0] == os.fspath(
        fixture["worktree"].resolve()
    )
    assert len(materialized["four_roots"]) == 4
    assert materialized["importable_artifact_manifest"] == os.fspath(
        fixture["manifest"].resolve()
    )
    assert materialized["payload"] == {
        "entry": "fake_payload:run",
        "pass_context": True,
    }


def test_launch_config_from_freeze_rejects_tampered_pin(tmp_path: Path) -> None:
    """FIX C11: a freeze-artifact digest mismatch fails the derivation."""

    fixture = _freeze_fixture(tmp_path)
    with fixture["mapping"].open("a", encoding="utf-8") as handle:
        handle.write("\n")
    with pytest.raises(ValueError, match="pin mismatch for 'child_env_mapping'"):
        launch_config_from_freeze(
            fixture["freeze"],
            fixture["infrastructure"],
            run_dir=fixture["run_dir"],
            run_id="m2cr-derived-test",
            authorization_id=AUTHORIZATION_ID,
            launch_attempt_id=LAUNCH_ATTEMPT_ID,
            record_kind="diagnostic",
            chain=dict(CHAIN),
            bootstrap_template_path=fixture["template"],
            worktree_root=REPOSITORY_ROOT,
        )


_COMMITTED_FREEZE = REPOSITORY_ROOT / "docs/m2c_freeze/m2cr_environment_freeze_manifest_v1.json"
_COMMITTED_INFRASTRUCTURE = (
    REPOSITORY_ROOT / "docs/m2c_freeze/m2cr_infrastructure_manifest_v1.json"
)


def _committed_manifest_is_v2() -> bool:
    try:
        freeze = json.loads(_COMMITTED_FREEZE.read_text(encoding="utf-8"))
        manifest_path = Path(
            freeze["artifacts"]["importable_artifact_manifest"]["path"]
        )
        with manifest_path.open("rb") as handle:
            first = json.loads(handle.readline())
        return isinstance(first, dict) and first.get("schema_version") == 2
    except Exception:
        return False


@pytest.mark.skipif(
    not _committed_manifest_is_v2(),
    reason=(
        "cross-worker seam: the committed importable-artifact manifest is "
        "not yet format v2 (header line with roots); the environment_freeze "
        "worker regenerates it — integration reconciles"
    ),
)
def test_committed_freeze_artifacts_derive_the_ratified_pins(
    tmp_path: Path,
) -> None:
    """FIX C11: read-only derivation from the COMMITTED artifacts, no launch."""

    template_path = tmp_path / "template.json"
    atomic_write_canonical_json(
        template_path,
        {"payload": {"entry": "fake_payload:run", "pass_context": True}},
    )
    config = launch_config_from_freeze(
        _COMMITTED_FREEZE,
        _COMMITTED_INFRASTRUCTURE,
        run_dir=tmp_path / "run",
        run_id="m2cr-committed-derivation",
        authorization_id=AUTHORIZATION_ID,
        launch_attempt_id=LAUNCH_ATTEMPT_ID,
        record_kind="diagnostic",
        chain=_bound_chain(_COMMITTED_FREEZE, _COMMITTED_INFRASTRUCTURE),
        bootstrap_template_path=template_path,
        worktree_root=REPOSITORY_ROOT,
    )
    assert config.interpreter_path == MINICONDA_PYTHON
    assert tuple(config.interpreter_flags) == FROZEN_INTERPRETER_FLAGS
    fixed = config.frozen_env["fixed"]
    assert fixed["PYTHONHASHSEED"] == "0"
    assert fixed["OMP_NUM_THREADS"] == "10"
    assert fixed["OMP_DYNAMIC"] == "FALSE"
    assert fixed["MKL_NUM_THREADS"] == "10"
    assert fixed["VECLIB_MAXIMUM_THREADS"] == "10"
    assert fixed["LC_ALL"] == "C"
    assert fixed["TZ"] == "UTC"
    assert config.frozen_env["run_local_keys"] == [
        "HOME",
        "TMPDIR",
        "XDG_CACHE_HOME",
        "XDG_CONFIG_HOME",
        "XDG_DATA_HOME",
        "XDG_STATE_HOME",
    ]
    assert config.wall_clock_ceiling_hours == 8.0


def test_launch_config_rejects_a_chain_unbound_to_the_authenticated_artifacts(
    tmp_path: Path,
) -> None:
    """External audit round-2 F2: the chain's static members and authorization
    id must equal the authenticated artifacts, not free-floating values."""

    fixture = _freeze_fixture(tmp_path)
    good = _bound_chain(fixture["freeze"], fixture["infrastructure"])
    for member in (
        "environment_freeze_manifest_sha256",
        "infrastructure_manifest_sha256",
        "authorization_id",
    ):
        bad = dict(good)
        bad[member] = "0" * 64 if member != "authorization_id" else "m2cr-auth-20000101-99"
        with pytest.raises(ValueError, match="does not match the authenticated"):
            launch_config_from_freeze(
                fixture["freeze"],
                fixture["infrastructure"],
                run_dir=fixture["run_dir"],
                run_id="m2cr-derived-test",
                authorization_id=AUTHORIZATION_ID,
                launch_attempt_id=LAUNCH_ATTEMPT_ID,
                record_kind="diagnostic",
                chain=bad,
                bootstrap_template_path=fixture["template"],
                worktree_root=fixture["worktree"],
            )


def test_raw_files_excludes_only_the_root_two_by_relpath(tmp_path: Path) -> None:
    """External audit round-2 F7: a nested file sharing a root artifact's
    basename stays covered by Layer 3."""

    from bistar_gp.m2cr.capture import _raw_files

    (tmp_path / RAW_MANIFEST_NAME).write_text("m")
    (tmp_path / TERMINAL_RECORD_NAME).write_text("t")
    (tmp_path / "nodes").mkdir()
    (tmp_path / "nodes" / TERMINAL_RECORD_NAME).write_text("nested")
    (tmp_path / "events.jsonl").write_text("e")
    got = {p.relative_to(tmp_path).as_posix() for p in _raw_files(tmp_path)}
    assert "nodes/terminal_record.json" in got
    assert RAW_MANIFEST_NAME not in got and TERMINAL_RECORD_NAME not in got


def test_post_prelaunch_setup_failure_still_assembles_a_terminal_record(
    tmp_path: Path,
) -> None:
    """External audit round-2 F4b: a failure writing the bootstrap config (a
    post-prelaunch setup step) must still yield a schema-valid terminal record,
    not escape capture_run leaving nothing."""

    config = _make_launch(tmp_path)
    run_dir = Path(config.run_dir)
    # Turn stdout.txt into a directory so the post-prelaunch open() fails inside
    # the supervised try; _make_launch does not create it, so this is clean.
    (run_dir / "stdout.txt").mkdir()
    record = capture_run(config)
    # No child could spawn, so this is NOT_STARTED; the key point is a terminal
    # record exists rather than an escaped exception.
    assert record["status"] in {"NOT_STARTED", "INFRA_FAILURE"}
    validate_terminal_record(record)


def test_worktree_file_read_then_deleted_stays_hashed_at_load_time(
    tmp_path: Path,
) -> None:
    """External audit round-2 F6: a worktree data file read during the run and
    then deleted is still recorded with its load-time hash, not lost."""

    import hashlib

    data_path = "worktree_data.txt"
    contents = b"scientific-worktree-input\n"
    expected = hashlib.sha256(contents).hexdigest()
    # The payload writes a worktree file, reads it (load-time hash captured by
    # the audit hook), then deletes it before returning.
    extra = (
        f"_p = os.path.join(os.getcwd(), {data_path!r})\n"
        f"    open(_p, 'wb').write({contents!r})\n"
        f"    open(_p, 'rb').read()\n"
        f"    os.unlink(_p)"
    )
    config = _make_launch(tmp_path, extra_payload_code=extra)
    record = capture_run(config)
    assert record["status"] == "COMPLETED", record.get("fault")
    inventory = json.loads((Path(config.run_dir) / "import_inventory.json").read_text())
    hashed = {
        item["path"]: item["sha256"]
        for item in inventory["worktree_opens"]["hashed"]
    }
    matched = [d for p, d in hashed.items() if p.endswith(data_path)]
    assert matched == [expected], (
        "read-then-deleted worktree file must keep its load-time hash"
    )
