from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import shutil
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
from tests.test_m2cr_bootstrap import (
    FAKE_NUMPY_BUILD_MARKERS,
    FAKE_PROFILE_SOURCE,
    FAKE_STAGE_B_EXPECTED,
    FAKE_TORCH_BUILD_MARKERS,
    MANDATORY_DIRECTIVES,
    SENTINEL_HASH,
    measured_expected_loaded_images,
    write_fake_native_stack,
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
# The real m2cr modules the child imports after its sys.path replacement; the
# synthetic launch worktree carries byte-identical copies so the REAL bootstrap
# and its project closure run from the worktree, exactly as in production.
_M2CR_CHILD_MODULES = (
    "bootstrap.py",
    "environment_freeze.py",
    "payload_boundary.py",
    "serialization.py",
)
_INFRA_RELPATH = "docs/m2c_freeze/m2cr_infrastructure_manifest_v1.json"


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
    import bistar_gp.profile_integration
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
    import bistar_gp.profile_integration
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


def _fake_site_packages_lock_semantics(root: Path) -> dict[str, object]:
    """Populate the synthetic site-packages and return the semantic
    dependency-lock fields, computed test-side from first principles.

    The committed fake lock is NOT generated by running the recompute under
    test: every field (the dist RECORD digest, the extension count, and the
    binary-extension aggregate over the canonical sorted digest list) is
    constructed here with stdlib hashing over bytes this fixture wrote, so the
    real ``verify_dependency_lock_semantics`` recompute is exercised unchanged
    against an independently constructed expectation.
    """

    dist_info = root / "fakepkg-1.0.dist-info"
    dist_info.mkdir(parents=True)
    (dist_info / "METADATA").write_text(
        "Name: fakepkg\nVersion: 1.0\n", encoding="utf-8"
    )
    record_bytes = b"fakepkg/__init__.py,sha256=0000,10\n"
    (dist_info / "RECORD").write_bytes(record_bytes)
    extension_bytes = b"M2CR-FAKE-EXTENSION-BYTES"
    (root / "fakeext.cpython-313-darwin.so").write_bytes(extension_bytes)
    extension_sha = hashlib.sha256(extension_bytes).hexdigest()
    aggregate = hashlib.sha256(
        json.dumps(
            [extension_sha], sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()
    return {
        "dists": [
            {
                "name": "fakepkg",
                "version": "1.0",
                "record_sha256": hashlib.sha256(record_bytes).hexdigest(),
            }
        ],
        "binary_extension_count": 1,
        "binary_extensions_sha256": aggregate,
    }


def _make_launch(
    tmp_path: Path,
    *,
    mode: str = "completed",
    ceiling_hours: float = 0.01,
    waiter=None,
    missing_interpreter: bool = False,
    wrong_environment: bool = False,
    extra_payload_code: str = "",
    expectations_mutator=None,
    lock_mutator=None,
    template_extra: dict | None = None,
) -> LaunchConfig:
    """Build a complete, self-consistent hermetic launch (Codex round-3 C1
    Stage C).

    The synthetic worktree carries byte-identical copies of the real child-side
    m2cr modules, the fake native stack (torch + numpy), a fake
    profile_integration stub, AND the committed fake bundle under
    ``docs/m2c_freeze``: an infrastructure manifest whose pins authenticate the
    native-stack expectations artifact (with the session-measured
    expected_loaded_images), the first-principles fake dependency lock, and a
    v2-header importable manifest binding the synthetic site-packages.  The
    LaunchConfig chain binds ``infrastructure_manifest_sha256`` to the real
    digest of that manifest, so ``capture_run`` derives, authenticates, binds,
    and enforces through the exact unconditional production path — there is no
    test-only bypass and no provenance-token-conditioned enforcement.
    """

    worktree = tmp_path / "worktree"
    run_dir = tmp_path / "run"
    (worktree / "bistar_gp" / "m2cr").mkdir(parents=True)
    run_dir.mkdir()
    for name in _M2CR_CHILD_MODULES:
        shutil.copy2(
            REPOSITORY_ROOT / "bistar_gp" / "m2cr" / name,
            worktree / "bistar_gp" / "m2cr" / name,
        )
    profile_path = worktree / "bistar_gp" / "profile_integration.py"
    profile_path.write_text(FAKE_PROFILE_SOURCE, encoding="utf-8")
    write_fake_native_stack(worktree)
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
    lock_semantics = _fake_site_packages_lock_semantics(extra_roots[2])
    roots = [
        os.fspath(worktree.resolve()),
        *(os.fspath(root.resolve()) for root in extra_roots),
    ]

    freeze_dir = worktree / "docs" / "m2c_freeze"
    freeze_dir.mkdir(parents=True)
    expectations = {
        "kind": "m2cr_native_stack_expectations",
        "schema_version": 1,
        "native_stack_modules": ["torch", "numpy"],
        "expected_profile_integration_sha256": sha256_file(profile_path),
        "expected_sentinel_hash": SENTINEL_HASH,
        "torch_build_expected": list(FAKE_TORCH_BUILD_MARKERS),
        "numpy_build_expected": list(FAKE_NUMPY_BUILD_MARKERS),
        "stage_b_expected": dict(FAKE_STAGE_B_EXPECTED),
        "loaded_image_allowlist": [],
        "expected_loaded_images": measured_expected_loaded_images(),
    }
    if expectations_mutator is not None:
        expectations_mutator(expectations)
    expectations_path = freeze_dir / "m2cr_native_stack_expectations_v1.json"
    atomic_write_canonical_json(expectations_path, expectations)

    lock = {
        "pip_freeze": "",
        "excluded_editable_installs": [],
        **lock_semantics,
        "caveats": [],
    }
    if lock_mutator is not None:
        lock_mutator(lock)
    lock_path = freeze_dir / "m2cr_dependency_lock_v1.json"
    atomic_write_canonical_json(lock_path, lock)

    manifest_path = freeze_dir / "m2cr_importable_artifact_manifest_v1.jsonl"
    header = {
        "kind": "m2cr_importable_artifact_manifest",
        "schema_version": 2,
        "roots": {
            "worktree": roots[0],
            "stdlib": roots[1],
            "lib-dynload": roots[2],
            "site-packages": roots[3],
        },
    }
    manifest_path.write_text(canonical_dumps(header) + "\n", encoding="utf-8")

    infra = {
        "kind": "m2cr_infrastructure_manifest",
        "schema_version": 1,
        "artifacts": {
            "native_stack_expectations": {
                "path": "docs/m2c_freeze/m2cr_native_stack_expectations_v1.json",
                "sha256": sha256_file(expectations_path),
            },
            "dependency_lock": {
                "path": "docs/m2c_freeze/m2cr_dependency_lock_v1.json",
                "sha256": sha256_file(lock_path),
            },
            "importable_artifact_manifest": {
                "path": (
                    "docs/m2c_freeze/m2cr_importable_artifact_manifest_v1.jsonl"
                ),
                "sha256": sha256_file(manifest_path),
            },
        },
    }
    infra_path = worktree / _INFRA_RELPATH
    atomic_write_canonical_json(infra_path, infra)
    chain = {**CHAIN, "infrastructure_manifest_sha256": sha256_file(infra_path)}

    bootstrap_config = {
        "four_roots": roots,
        # expected_sentinel_hash is now a mandatory attestation directive DERIVED
        # from the committed native-stack expectations artifact and bound by
        # capture_run (finding 3) — the caller template no longer carries it.
        "payload": {"entry": "fake_payload:run", "pass_context": True},
        "payload_entry_path": os.fspath(payload_path),
        "attestation_paths": {
            "payload_started": os.fspath(run_dir / "payload_started.json")
        },
    }
    if template_extra:
        bootstrap_config.update(template_extra)
    environment = _frozen_environment(run_dir, unexpected=wrong_environment)
    if wrong_environment:
        bootstrap_config["expected_frozen_env"] = _frozen_environment(run_dir)
    (run_dir / BOOTSTRAP_CONFIG_NAME).write_text(
        canonical_dumps(bootstrap_config), encoding="utf-8"
    )
    arguments = {
        "interpreter_path": "/definitely/missing/python"
        if missing_interpreter
        else MINICONDA_PYTHON,
        "interpreter_flags": (
            "-S",
            "-s",
            "-P",
            "-B",
            "-X",
            "pycache_prefix={pycache_prefix}",
        ),
        "bootstrap_path": os.fspath(worktree / "bistar_gp/m2cr/bootstrap.py"),
        "worktree_root": os.fspath(worktree),
        "run_dir": os.fspath(run_dir),
        "frozen_env": environment,
        "authorization_id": AUTHORIZATION_ID,
        "launch_attempt_id": LAUNCH_ATTEMPT_ID,
        "run_id": "m2cr-capture-test",
        "record_kind": "diagnostic",
        "chain": chain,
        "wall_clock_ceiling_hours": ceiling_hours,
    }
    if waiter is not None:
        arguments["waiter"] = waiter
    return LaunchConfig(**arguments)


def _rebind_infra(config: LaunchConfig, mutate) -> LaunchConfig:
    """Apply ``mutate(infra, worktree)`` to the bundle's infrastructure
    manifest, rewrite it canonically, and rebind the chain to the new digest —
    so a negative test can weaken exactly one authenticated pin while the
    chain binding itself stays valid."""

    worktree = Path(config.worktree_root)
    infra_path = worktree / _INFRA_RELPATH
    infra = json.loads(infra_path.read_text(encoding="utf-8"))
    mutate(infra, worktree)
    atomic_write_canonical_json(infra_path, infra)
    return dataclasses.replace(
        config,
        chain={**config.chain, "infrastructure_manifest_sha256": sha256_file(infra_path)},
    )


def _manifest_entries(run_dir: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in (run_dir / RAW_MANIFEST_NAME).read_text().splitlines():
        digest, relative = line.split("  ", 1)
        result[relative] = digest
    return result


def test_happy_path_real_subprocess_and_frozen_write_order(tmp_path: Path) -> None:
    """The positive fake-bundle launch reaches COMPLETED through the exact
    unconditional production path: capture_run derives + authenticates the
    committed bundle from the worktree manifests, binds all eight mandatory
    directives, verifies the semantic dependency lock, spawns the REAL
    bootstrap (which attests the fake native stack and authenticates the
    measured loaded images before the marker), then publishes the marker-bound
    terminal record (Codex round-3 C1, Stage C)."""

    config = _make_launch(tmp_path)
    record = capture_run(config)
    run_dir = Path(config.run_dir)
    assert record["status"] == "COMPLETED", record.get("fault")
    assert record["not_a_result"] is True
    assert (run_dir / "spawned.json").exists()
    assert (run_dir / "payload_started.json").exists()
    assert (
        json.loads((run_dir / "events.jsonl").read_text().splitlines()[0])["event"]
        == "HELLO"
    )
    assert record["evidence"]["event_stream_balanced"] is True
    # C1 layer 2: the consumed bootstrap config carries exactly the committed
    # expectations' mandatory directives, derived and bound by capture_run.
    consumed = json.loads((run_dir / BOOTSTRAP_CONFIG_NAME).read_text())
    expectations = json.loads(
        (Path(config.worktree_root)
         / "docs/m2c_freeze/m2cr_native_stack_expectations_v1.json").read_text()
    )
    for directive in MANDATORY_DIRECTIVES:
        assert consumed[directive] == expectations[directive]
    # C1 layer 1: the real bootstrap imported and attested the fake stack from
    # the worktree, and the mandatory profile comparison ran and matched.
    inventory = json.loads((run_dir / "import_inventory.json").read_text())
    fake_torch = next(
        item for item in inventory["modules"] if item["module"] == "torch"
    )
    assert fake_torch["origin"].startswith(os.fspath(Path(config.worktree_root)))
    profile_check = inventory["profile_integration_check"]
    assert profile_check["module_loaded"] is True and profile_check["match"] is True
    native = json.loads((run_dir / "native_stack.json").read_text())
    assert native["loaded_images_stage_b"]
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


def test_popen_failure_with_no_confirmed_spawn_is_not_started(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ratified F5 split, rule-1 branch: a spawn attempted AT Popen that fails
    (an exec-level OSError) after every pre-spawn attestation passed is
    NOT_STARTED — the only NOT_STARTED path.  All earlier failures are
    pre-payload INFRA_FAILURE (the companion missing-interpreter test)."""

    config = _make_launch(tmp_path)
    real_popen = subprocess.Popen

    def failing_popen(argv, *args: object, **kwargs: object):
        # Fail ONLY the child bootstrap spawn; the pre-spawn dependency-lock
        # recompute's own subprocesses (pip freeze) must keep running so every
        # pre-spawn attestation genuinely passed before Popen.
        if any(os.fspath(part).endswith("bootstrap.py") for part in argv):
            raise OSError("simulated exec failure at Popen")
        return real_popen(argv, *args, **kwargs)

    monkeypatch.setattr(capture_module.subprocess, "Popen", failing_popen)
    record = capture_run(config)
    assert record["status"] == "NOT_STARTED"
    assert "simulated exec failure at Popen" in record["not_started"]["reason"]
    assert record["not_started"]["prelaunch_sha256"] == sha256_file(
        Path(config.run_dir) / "prelaunch.json"
    )
    assert not (Path(config.run_dir) / "spawned.json").exists()
    assert not (Path(config.run_dir) / "payload_started.json").exists()
    validate_terminal_record(record)


def test_missing_interpreter_is_pre_spawn_infra_failure_not_not_started(
    tmp_path: Path,
) -> None:
    """Codex round-3 C1 consequence of the ratified F5 split: with the
    dependency-lock semantic recompute unconditional, a missing/bad pinned
    interpreter now fails the pre-spawn attestation phase (the recompute
    cannot run) and commits INFRA_FAILURE — it never reaches Popen, so it can
    no longer surface as NOT_STARTED."""

    config = _make_launch(tmp_path, missing_interpreter=True)
    record = capture_run(config)
    assert record["status"] == "INFRA_FAILURE"
    assert record["fault"]["fault_class"] == "attestation_fault"
    assert "pre-spawn attestation failure" in record["fault"]["detail"]
    assert "dependency-lock recompute failed" in record["fault"]["detail"]
    assert record["fault"]["payload_started"] is False
    assert not (Path(config.run_dir) / "spawned.json").exists()
    assert not (Path(config.run_dir) / "prelaunch.json").exists()
    assert (Path(config.run_dir) / TERMINAL_RECORD_NAME).is_file()
    validate_terminal_record(record)


def test_parent_death_reconciliation_marks_only_envelope_reconstructed(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "reconcile"
    _write_reconcile_evidence(run_dir)
    # F6: identity is derived from the CAPTURED prelaunch provenance, so no
    # caller config is required and the reconstructed record carries the
    # run's real identity, not a freshly supplied one.
    record = reconcile_run(run_dir)
    assert record["status"] == "INFRA_FAILURE"
    assert record["fault"]["reconstructed"] is True
    assert record["fault"]["payload_started"] is False
    assert record["run_id"] == "m2cr-reconcile-test"
    assert record["launch_attempt_id"] == LAUNCH_ATTEMPT_ID
    assert record["chain"] == CHAIN
    validate_terminal_record(record)


def _write_reconcile_evidence(run_dir: Path) -> None:
    """Write the raw evidence a parent-death reconciliation reconstructs over,
    including a prelaunch.json carrying the run's real identity provenance."""

    run_dir.mkdir()
    prelaunch = {
        "schema_version": 1,
        "config": {
            "record_kind": "diagnostic",
            "run_id": "m2cr-reconcile-test",
            "launch_attempt_id": LAUNCH_ATTEMPT_ID,
            "chain": CHAIN,
        },
    }
    (run_dir / "prelaunch.json").write_text(canonical_dumps(prelaunch))
    (run_dir / "spawned.json").write_text(canonical_dumps({"pid": 123}))
    (run_dir / "events.jsonl").write_text(
        canonical_dumps({"seq": 0, "event": "HELLO"}) + "\n"
    )
    (run_dir / "stdout.txt").write_bytes(b"partial stdout")
    (run_dir / "stderr.txt").write_bytes(b"")


def test_reconciliation_refuses_a_config_that_disagrees_with_provenance(
    tmp_path: Path,
) -> None:
    """F6: a caller config whose identity contradicts the captured
    prelaunch.json provenance refuses reconciliation rather than silently
    relabelling one run's raw evidence with another run's identity."""

    run_dir = tmp_path / "reconcile"
    _write_reconcile_evidence(run_dir)
    wrong_config = {
        "record_kind": "diagnostic",
        "run_id": "m2cr-some-other-run",
        "launch_attempt_id": LAUNCH_ATTEMPT_ID,
        "chain": CHAIN,
    }
    with pytest.raises(RecordAssemblyError, match="disagrees with captured"):
        reconcile_run(run_dir, wrong_config)
    assert not (run_dir / TERMINAL_RECORD_NAME).exists()


def test_reconciliation_is_idempotent_and_never_overwrites_a_terminal(
    tmp_path: Path,
) -> None:
    """F6: reconciliation never overwrites an existing terminal record
    (plan §4.3 "Nothing vanishes and no state is silently reclassified")."""

    run_dir = tmp_path / "reconcile"
    _write_reconcile_evidence(run_dir)
    first = reconcile_run(run_dir)
    validate_terminal_record(first)
    with pytest.raises(RecordAssemblyError, match="already exists"):
        reconcile_run(run_dir)


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


def test_config_mutation_after_write_is_rejected_and_voids_certification(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Round-4 (Codex delta review): a mutation of the mutable
    bootstrap_config.json in the window between the parent's authenticated
    write and the child's read is defeated twice over — the child rejects the
    bytes against the argv-bound digest before consuming any directive (no
    marker), and the parent's post-exit re-hash of the config voids
    certification as a capture fault."""

    config = _make_launch(tmp_path)
    real_popen = subprocess.Popen

    def substitute_directive_then_spawn(argv, *args, **kwargs):
        # Mutate ONLY the child bootstrap's config argument (a caller-style
        # substitution of one committed directive value); the pre-spawn
        # dependency-lock recompute's own subprocesses pass through untouched.
        config_argument = os.fspath(argv[-3]) if len(argv) >= 3 else ""
        if config_argument.endswith(BOOTSTRAP_CONFIG_NAME):
            template = json.loads(Path(config_argument).read_text())
            template["expected_profile_integration_sha256"] = "c" * 64
            Path(config_argument).write_text(
                canonical_dumps(template), encoding="utf-8"
            )
        return real_popen(argv, *args, **kwargs)

    monkeypatch.setattr(
        capture_module.subprocess, "Popen", substitute_directive_then_spawn
    )
    record = capture_run(config)
    run_dir = Path(config.run_dir)
    assert (run_dir / "spawned.json").exists()
    assert (
        json.loads((run_dir / "events.jsonl").read_text().splitlines()[0])["event"]
        == "HELLO"
    )
    # The child refused the mutated bytes before consuming any directive.
    failure = json.loads((run_dir / "bootstrap_failure.json").read_text())
    assert failure["fault_class"] == "attestation_fault"
    assert "bootstrap config digest mismatch" in failure["detail"]
    assert not (run_dir / "payload_started.json").exists()
    assert not (run_dir / "effect_proofs.json").exists()
    # The parent's post-exit static re-attestation independently voids the run.
    assert record["status"] == "INFRA_FAILURE"
    assert record["fault"]["fault_class"] == "capture_fault"
    assert (
        "bootstrap config changed between write and post-exit attestation"
        in record["fault"]["detail"]
    )
    assert record["fault"]["payload_started"] is False
    validate_terminal_record(record)


def test_config_mutation_during_run_is_caught_at_post_exit(
    tmp_path: Path,
) -> None:
    """Round-4 (Codex delta review): a mutation of bootstrap_config.json
    DURING the run — after the child already verified its argv-bound digest at
    startup — is caught by the parent's post-exit re-hash and voids
    certification, even though the child exited with a protocol claim."""

    config = _make_launch(
        tmp_path,
        extra_payload_code=(
            "open(os.path.join("
            f"{os.fspath(tmp_path / 'run')!r}, 'bootstrap_config.json'), "
            "'ab').write(b' ')"
        ),
    )
    record = capture_run(config)
    run_dir = Path(config.run_dir)
    assert (run_dir / "payload_started.json").exists()
    assert (run_dir / "payload.json").exists()
    assert record["status"] == "INFRA_FAILURE"
    assert record["fault"]["fault_class"] == "capture_fault"
    assert (
        "bootstrap config changed between write and post-exit attestation"
        in record["fault"]["detail"]
    )
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


def test_escaping_attestation_path_commits_infra_pre_spawn(tmp_path: Path) -> None:
    """FIX C6 + F5: an attestation path escaping run_dir is a pre-spawn
    infrastructure failure; it now COMMITS an INFRA_FAILURE terminal record
    with no child spawned (plan §4.3 "Nothing vanishes"), rather than escaping
    capture_run."""

    config = _make_launch(tmp_path)
    run_dir = Path(config.run_dir)
    template = json.loads((run_dir / BOOTSTRAP_CONFIG_NAME).read_text())
    template["attestation_paths"]["stage_a"] = os.fspath(
        tmp_path / "outside" / "stage_a.json"
    )
    (run_dir / BOOTSTRAP_CONFIG_NAME).write_text(
        canonical_dumps(template), encoding="utf-8"
    )
    record = capture_run(config)
    assert record["status"] == "INFRA_FAILURE"
    assert record["fault"]["fault_class"] == "capture_fault"
    assert "pre-spawn infrastructure failure" in record["fault"]["detail"]
    assert "escapes the self-contained run" in record["fault"]["detail"]
    assert (run_dir / TERMINAL_RECORD_NAME).is_file()
    assert not (run_dir / "prelaunch.json").exists()
    assert not (run_dir / "spawned.json").exists()


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


def test_tampered_preboundary_attestation_commits_infra_without_spawn(
    tmp_path: Path,
) -> None:
    """F5 (supersedes C7(b) "refuses with no spawn"): a pre-spawn digest
    mismatch COMMITS an INFRA_FAILURE terminal record + launch-attempt
    evidence with no child spawned, rather than escaping capture_run
    (plan §4.3 "Nothing vanishes"; author decision F5 = INFRA_FAILURE)."""

    attestation_path, closure_file = _preboundary_attestation_document(
        tmp_path, tampered=True
    )
    config = dataclasses.replace(
        _make_launch(tmp_path),
        preboundary_attestation_set=os.fspath(attestation_path),
        preboundary_skip=("interpreter", "dyld"),
    )
    record = capture_run(config)
    assert record["status"] == "INFRA_FAILURE"
    assert record["fault"]["fault_class"] == "attestation_fault"
    assert "pre-spawn attestation failure" in record["fault"]["detail"]
    assert "preboundary attestation mismatch" in record["fault"]["detail"]
    run_dir = Path(config.run_dir)
    # The terminal record is durably committed; no child was ever spawned.
    assert (run_dir / TERMINAL_RECORD_NAME).is_file()
    assert not (run_dir / "spawned.json").exists()
    validate_terminal_record(record)
    # The closure entries are never skippable: no such token exists.
    with pytest.raises(ValueError, match="unknown preboundary skip tokens"):
        verify_preboundary_attestation_set(
            attestation_path, skip=("interpreter", "dyld", "closure")
        )


def test_pre_spawn_setup_failure_commits_infra_without_spawn(
    tmp_path: Path,
) -> None:
    """F5: a pre-spawn INFRASTRUCTURE failure (a missing bootstrap source, a
    resolve(strict=True) error) also commits an INFRA_FAILURE terminal record
    rather than escaping capture_run; it is classed capture_fault, not
    attestation_fault."""

    config = dataclasses.replace(
        _make_launch(tmp_path),
        bootstrap_path=os.fspath(tmp_path / "does-not-exist" / "bootstrap.py"),
    )
    record = capture_run(config)
    assert record["status"] == "INFRA_FAILURE"
    assert record["fault"]["fault_class"] == "capture_fault"
    assert "pre-spawn infrastructure failure" in record["fault"]["detail"]
    assert (Path(config.run_dir) / TERMINAL_RECORD_NAME).is_file()
    assert not (Path(config.run_dir) / "spawned.json").exists()
    validate_terminal_record(record)


def test_preboundary_worktree_entry_verifies_against_the_launch_worktree(
    tmp_path: Path,
) -> None:
    """F3: a worktree-origin closure pin is verified by (relpath, sha256)
    against THIS launch's worktree, so a content-matching per-launch worktree
    at a DIFFERENT absolute path passes, and a content mismatch fails closed —
    the freeze-time absolute path is never trusted."""

    from bistar_gp.m2cr.environment_freeze import _attestation_entry

    freeze_worktree = tmp_path / "freeze_worktree"
    (freeze_worktree / "bistar_gp/m2cr").mkdir(parents=True)
    member = freeze_worktree / "bistar_gp/m2cr/probe_closure.py"
    member.write_text("PROBE = 1\n", encoding="utf-8")
    # The generator classifies a pin inside the worktree as worktree-relative
    # and retains no freeze-time absolute path; a host pin keeps its path.
    entry = _attestation_entry(
        member, True, worktree_root=freeze_worktree.resolve()
    )
    assert entry["root"] == "worktree"
    assert entry["relpath"] == "bistar_gp/m2cr/probe_closure.py"
    assert "path" not in entry
    host_entry = _attestation_entry(member, True)
    assert host_entry["path"] == os.fspath(member) and "root" not in host_entry
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
        "bootstrap_closure": [entry],
    }
    attestation_path = tmp_path / "set.json"
    atomic_write_canonical_json(attestation_path, artifact)

    # A DIFFERENT worktree with byte-identical content passes.
    launch_worktree = tmp_path / "launch_worktree"
    (launch_worktree / "bistar_gp/m2cr").mkdir(parents=True)
    (launch_worktree / "bistar_gp/m2cr/probe_closure.py").write_text(
        "PROBE = 1\n", encoding="utf-8"
    )
    outcome = verify_preboundary_attestation_set(
        attestation_path,
        worktree_root=os.fspath(launch_worktree),
        skip=("interpreter", "dyld"),
    )
    assert outcome["closure"] == 1

    # A content mismatch in the launch worktree fails closed.
    (launch_worktree / "bistar_gp/m2cr/probe_closure.py").write_text(
        "PROBE = 2\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="preboundary attestation mismatch"):
        verify_preboundary_attestation_set(
            attestation_path,
            worktree_root=os.fspath(launch_worktree),
            skip=("interpreter", "dyld"),
        )

    # A worktree-relative entry with no worktree_root supplied fails closed.
    with pytest.raises(ValueError, match="no worktree_root was supplied"):
        verify_preboundary_attestation_set(
            attestation_path, skip=("interpreter", "dyld")
        )

    # CP-3: a lexically safe relpath that is a symlink resolving OUTSIDE the
    # launch worktree fails closed, even if the external target's bytes match —
    # the freeze-time bytes cannot be satisfied by an out-of-tree file.
    external = tmp_path / "external_probe.py"
    external.write_text("PROBE = 1\n", encoding="utf-8")  # byte-identical
    member_path = launch_worktree / "bistar_gp/m2cr/probe_closure.py"
    member_path.unlink()
    member_path.symlink_to(external)
    with pytest.raises(ValueError, match="resolves outside the launch worktree"):
        verify_preboundary_attestation_set(
            attestation_path,
            worktree_root=os.fspath(launch_worktree),
            skip=("interpreter", "dyld"),
        )


def test_prelaunch_failure_commits_infra_pre_spawn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CP-4: a failure in prelaunch provenance (or event-pipe setup) after the
    attestation checks but before spawn also commits an INFRA_FAILURE record
    rather than escaping capture_run (§4.3 "Nothing vanishes")."""

    config = _make_launch(tmp_path)

    def boom(*args: object, **kwargs: object) -> dict:
        raise OSError("simulated bootstrap disappearance during prelaunch")

    monkeypatch.setattr(capture_module, "_prelaunch", boom)
    record = capture_run(config)
    assert record["status"] == "INFRA_FAILURE"
    assert record["fault"]["fault_class"] == "capture_fault"
    assert "pre-spawn prelaunch failure" in record["fault"]["detail"]
    assert (Path(config.run_dir) / TERMINAL_RECORD_NAME).is_file()
    assert not (Path(config.run_dir) / "spawned.json").exists()
    validate_terminal_record(record)


def test_terminal_publish_is_no_clobber_in_both_paths(tmp_path: Path) -> None:
    """Codex round-3 C4: the terminal record is published with atomic no-clobber
    semantics, so neither normal capture nor reconciliation can overwrite an
    existing terminal — the second writer (the race loser) fails closed."""

    run_dir = tmp_path / "run"
    run_dir.mkdir()
    record = {
        "schema_version": 1,
        "record_kind": "diagnostic",
        "status": "INFRA_FAILURE",
        "run_id": "m2cr-noclobber",
        "launch_attempt_id": LAUNCH_ATTEMPT_ID,
        "chain": dict(CHAIN),
        "fault": {
            "fault_class": "other",
            "detail": "first",
            "reconstructed": False,
            "payload_started": False,
        },
        "evidence": {
            "raw_manifest_sha256": "0" * 64,
            "node_evidence_digests": [],
            "event_stream_balanced": False,
        },
        "not_a_result": True,
    }
    digest = capture_module._write_terminal(run_dir, record)
    assert isinstance(digest, str) and len(digest) == 64
    assert (run_dir / TERMINAL_RECORD_NAME).is_file()
    # A second publish (the race loser, whether capture or reconcile) fails
    # closed rather than overwriting the first.
    with pytest.raises(RecordAssemblyError, match="already exists"):
        capture_module._write_terminal(run_dir, {**record, "fault": {**record["fault"], "detail": "second"}})
    # The on-disk record is unchanged (the first writer's).
    on_disk = json.loads((run_dir / TERMINAL_RECORD_NAME).read_text())
    assert on_disk["fault"]["detail"] == "first"


@pytest.mark.parametrize(
    ("exc_type", "message"),
    [
        (RuntimeError, "thread resource exhausted"),
        (PermissionError, "event pipe permission denied"),
    ],
)
def test_event_pipe_start_failure_commits_infra_pre_spawn(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    exc_type: type[BaseException],
    message: str,
) -> None:
    """Codex round-3 C3: any ordinary Exception in the pre-spawn phase — a
    RuntimeError from the event-pipe start (thread-resource exhaustion) or a
    PermissionError — is caught by the broadened handler and commits an
    INFRA_FAILURE record rather than escaping capture_run after
    prelaunch.json is written."""

    config = _make_launch(tmp_path)
    real_pipe = capture_module.parent_event_pipe

    class _BoomPipe:
        def __init__(self, inner: object) -> None:
            self._inner = inner
            self.hello_event = threading.Event()

        def start(self) -> None:
            raise exc_type(message)

        def join(self, *args: object, **kwargs: object) -> None:
            return None

    monkeypatch.setattr(
        capture_module,
        "parent_event_pipe",
        lambda events_path: _BoomPipe(real_pipe(events_path)),
    )
    record = capture_run(config)
    assert record["status"] == "INFRA_FAILURE"
    assert "pre-spawn prelaunch failure" in record["fault"]["detail"]
    assert message in record["fault"]["detail"]
    assert (Path(config.run_dir) / TERMINAL_RECORD_NAME).is_file()
    validate_terminal_record(record)


def test_capture_run_rejects_a_stripped_or_substituted_consumed_template(
    tmp_path: Path,
) -> None:
    """CP-1a strengthened by Codex round-3 C1: capture_run derives the
    mandatory directives from the committed bundle and re-validates the
    template it actually consumes, so a rewrite of the mutable
    bootstrap_config.json that strips or substitutes any mandatory directive
    (here: an emptied native stack and a swapped profile hash) is rejected as
    caller substitution — INFRA_FAILURE before any spawn, with no
    profile-token gate."""

    config = _make_launch(tmp_path)
    run_dir = Path(config.run_dir)
    template = json.loads((run_dir / BOOTSTRAP_CONFIG_NAME).read_text())
    template["expected_profile_integration_sha256"] = "a" * 64
    template["native_stack_modules"] = []
    (run_dir / BOOTSTRAP_CONFIG_NAME).write_text(
        canonical_dumps(template), encoding="utf-8"
    )
    record = capture_run(config)
    assert record["status"] == "INFRA_FAILURE"
    assert record["fault"]["fault_class"] == "attestation_fault"
    assert "substitutes the committed" in record["fault"]["detail"]
    assert not (run_dir / "spawned.json").exists()
    assert not (run_dir / "payload_started.json").exists()
    assert (run_dir / TERMINAL_RECORD_NAME).is_file()
    validate_terminal_record(record)


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
    # F1 (round-3): a committed native-stack expectations artifact carries the
    # mandatory attestation directives; the factory derives them from here.
    expectations_path = artifacts_dir / "native_stack_expectations.json"
    atomic_write_canonical_json(
        expectations_path,
        {
            "kind": "m2cr_native_stack_expectations",
            "schema_version": 1,
            "native_stack_modules": ["numpy", "torch"],
            "expected_profile_integration_sha256": "a" * 64,
            "expected_sentinel_hash": SENTINEL_HASH,
            "torch_build_expected": ["BLAS_INFO=accelerate"],
            "numpy_build_expected": ["name: accelerate"],
            "stage_b_expected": {},
            "loaded_image_allowlist": [],
            "expected_loaded_images": [
                {"path": "/frozen/libexample.dylib", "sha256": "b" * 64}
            ],
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
                },
                "native_stack_expectations": {
                    "path": os.fspath(expectations_path),
                    "sha256": sha256_file(expectations_path),
                },
            },
            "r1_schemas": {},
        },
    )
    template_path = tmp_path / "bootstrap_template.json"
    # A lean template: F1 (round-3) derives the mandatory attestation directives
    # from the committed expectations artifact, so the caller template carries
    # none of them (a caller-substituted value would be rejected).
    atomic_write_canonical_json(
        template_path,
        {
            "expected_sentinel_hash": -2671292046718125608,
            "payload": {"entry": "fake_payload:run", "pass_context": True},
        },
    )
    return {
        "freeze": freeze_path,
        "infrastructure": infrastructure_path,
        "template": template_path,
        "expectations": expectations_path,
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


@pytest.mark.parametrize(
    "substitution, match",
    [
        ({"native_stack_modules": ["scipy"]}, "substitutes the committed native_stack_modules"),
        ({"native_stack_modules": []}, "substitutes the committed native_stack_modules"),
        (
            {"expected_profile_integration_sha256": "c" * 64},
            "substitutes the committed expected_profile_integration_sha256",
        ),
        (
            {"expected_loaded_images": []},
            "substitutes the committed expected_loaded_images",
        ),
        (
            {"torch_build_expected": ["FAKE=1"]},
            "substitutes the committed torch_build_expected",
        ),
    ],
)
def test_launch_config_from_freeze_rejects_caller_substituted_directives(
    tmp_path: Path, substitution: dict, match: str
) -> None:
    """F1 (round-3): the mandatory attestation directives are DERIVED from the
    committed expectations artifact; a caller template that substitutes any of
    them (a different native stack, profile hash, loaded-image set, or build
    marker) is rejected before payload start."""

    fixture = _freeze_fixture(tmp_path)
    template = {
        "expected_sentinel_hash": -2671292046718125608,
        "payload": {"entry": "fake_payload:run", "pass_context": True},
        **substitution,
    }
    atomic_write_canonical_json(fixture["template"], template)
    with pytest.raises(ValueError, match=match):
        launch_config_from_freeze(
            fixture["freeze"],
            fixture["infrastructure"],
            run_dir=fixture["run_dir"],
            run_id="m2cr-substitution-test",
            authorization_id=AUTHORIZATION_ID,
            launch_attempt_id=LAUNCH_ATTEMPT_ID,
            record_kind="diagnostic",
            chain=_bound_chain(fixture["freeze"], fixture["infrastructure"]),
            bootstrap_template_path=fixture["template"],
            worktree_root=fixture["worktree"],
        )


def test_launch_config_from_freeze_derives_mandatory_directives(
    tmp_path: Path,
) -> None:
    """F1 (round-3): the derived config's bootstrap_config.json carries exactly
    the committed expectations' mandatory directives, regardless of the lean
    caller template."""

    fixture = _freeze_fixture(tmp_path)
    launch_config_from_freeze(
        fixture["freeze"],
        fixture["infrastructure"],
        run_dir=fixture["run_dir"],
        run_id="m2cr-derive-directives",
        authorization_id=AUTHORIZATION_ID,
        launch_attempt_id=LAUNCH_ATTEMPT_ID,
        record_kind="diagnostic",
        chain=_bound_chain(fixture["freeze"], fixture["infrastructure"]),
        bootstrap_template_path=fixture["template"],
        worktree_root=fixture["worktree"],
    )
    written = json.loads(
        (fixture["run_dir"] / BOOTSTRAP_CONFIG_NAME).read_text()
    )
    expectations = json.loads(fixture["expectations"].read_text())
    for key in (
        "native_stack_modules",
        "expected_profile_integration_sha256",
        "expected_loaded_images",
        "torch_build_expected",
        "stage_b_expected",
    ):
        assert written[key] == expectations[key]


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
    # A lean template: F1 (round-3) derives the mandatory directives from the
    # committed native-stack expectations artifact.
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


def test_post_prelaunch_setup_failure_is_infra_failure_not_not_started(
    tmp_path: Path,
) -> None:
    """External audit round-2 F4b + Codex round-3 C2: a failure opening
    stdout.txt (a pre-Popen infrastructure setup step) is a pre-payload
    infrastructure fault, so it is INFRA_FAILURE with no payload_started — NOT
    NOT_STARTED, which is reserved for a spawn attempted at Popen but never
    confirmed."""

    config = _make_launch(tmp_path)
    run_dir = Path(config.run_dir)
    # Turn stdout.txt into a directory so the pre-Popen open() fails.
    (run_dir / "stdout.txt").mkdir()
    record = capture_run(config)
    assert record["status"] == "INFRA_FAILURE"
    assert record["fault"]["fault_class"] == "capture_fault"
    assert "pre-spawn setup failure" in record["fault"]["detail"]
    assert record["fault"]["payload_started"] is False
    assert not (run_dir / "spawned.json").exists()
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


def _assert_pre_spawn_attestation_infra(
    record: dict, run_dir: Path, *, detail: str
) -> None:
    assert record["status"] == "INFRA_FAILURE"
    assert record["fault"]["fault_class"] == "attestation_fault"
    assert "pre-spawn attestation failure" in record["fault"]["detail"]
    assert detail in record["fault"]["detail"]
    assert record["fault"]["payload_started"] is False
    assert not (run_dir / "prelaunch.json").exists()
    assert not (run_dir / "spawned.json").exists()
    assert not (run_dir / "payload_started.json").exists()
    assert (run_dir / TERMINAL_RECORD_NAME).is_file()
    validate_terminal_record(record)


@pytest.mark.parametrize(
    "case",
    [
        "manifest_missing",
        "chain_binding_mismatch",
        "pin_missing",
        "pin_hash_mismatch",
        "pin_escapes_worktree",
    ],
)
def test_bundle_derivation_failures_commit_infra_pre_spawn(
    tmp_path: Path, case: str
) -> None:
    """Codex round-3 C1 (requirement 2): capture_run's trust root is the
    committed infrastructure manifest under the launch worktree, bound to the
    authorized chain — a missing manifest, a chain-binding mismatch, a missing
    or tampered artifact pin, and a pin escaping the worktree each fail closed
    with a committed pre-payload INFRA_FAILURE and no spawn."""

    config = _make_launch(tmp_path)
    worktree = Path(config.worktree_root)
    if case == "manifest_missing":
        (worktree / _INFRA_RELPATH).unlink()
        detail = "committed infrastructure manifest not found"
    elif case == "chain_binding_mismatch":
        config = dataclasses.replace(
            config,
            chain={**config.chain, "infrastructure_manifest_sha256": "1" * 64},
        )
        detail = "does not match the authorized chain binding"
    elif case == "pin_missing":

        def drop_lock(infra: dict, _worktree: Path) -> None:
            del infra["artifacts"]["dependency_lock"]

        config = _rebind_infra(config, drop_lock)
        detail = "does not pin dependency_lock"
    elif case == "pin_hash_mismatch":
        expectations_path = (
            worktree / "docs/m2c_freeze/m2cr_native_stack_expectations_v1.json"
        )
        with expectations_path.open("a", encoding="utf-8") as handle:
            handle.write("\n")
        detail = "sha256 does not match the infrastructure manifest"
    else:

        def escape_pin(infra: dict, mutate_worktree: Path) -> None:
            outside = mutate_worktree.parent / "outside_expectations.json"
            atomic_write_canonical_json(outside, {"outside": True})
            infra["artifacts"]["native_stack_expectations"] = {
                "path": "../outside_expectations.json",
                "sha256": sha256_file(outside),
            }

        config = _rebind_infra(config, escape_pin)
        detail = "resolves outside the launch worktree"
    record = capture_run(config)
    _assert_pre_spawn_attestation_infra(
        record, Path(config.run_dir), detail=detail
    )


@pytest.mark.parametrize("directive", MANDATORY_DIRECTIVES)
def test_expectations_artifact_missing_any_directive_fails_closed(
    tmp_path: Path, directive: str
) -> None:
    """Codex round-3 C1 + finding 3: a committed expectations artifact that lacks
    ANY of the eight mandatory directives (including the profile hash, the
    build-pinned sentinel hash, and the expected loaded-image set) cannot bind a
    launch — INFRA_FAILURE before any spawn, never a directive default."""

    def drop(expectations: dict) -> None:
        del expectations[directive]

    config = _make_launch(tmp_path, expectations_mutator=drop)
    record = capture_run(config)
    _assert_pre_spawn_attestation_infra(
        record,
        Path(config.run_dir),
        detail=f"native-stack expectations artifact lacks mandatory {directive}",
    )


@pytest.mark.parametrize(
    ("directive", "value"),
    [
        ("expected_profile_integration_sha256", "c" * 64),
        (
            "expected_loaded_images",
            [{"path": "/caller/substituted.dylib", "sha256": "d" * 64}],
        ),
        ("expected_sentinel_hash", 123456789),
    ],
)
def test_caller_substituted_authority_value_is_rejected(
    tmp_path: Path, directive: str, value: object
) -> None:
    """Codex round-3 C1 / F1 / finding 3: a caller template that carries its own
    value for a mandatory directive — a substituted profile hash, a caller-chosen
    expected loaded-image set, or a template-selected sentinel hash — is rejected
    against the committed derivation before payload start, so changing only the
    caller expectation can never make the check pass."""

    config = _make_launch(tmp_path, template_extra={directive: value})
    record = capture_run(config)
    _assert_pre_spawn_attestation_infra(
        record,
        Path(config.run_dir),
        detail=f"substitutes the committed {directive}",
    )


def test_sentinel_hash_is_build_pinned_derived_and_enforced(tmp_path: Path) -> None:
    """Finding 3: the build-pinned bound sentinel __hash__ value (§4.5.8) is
    derived from the committed native-stack expectations, bound into the consumed
    config, and enforced by the child's effect proofs — a malformed committed
    value is rejected pre-spawn, a wrong committed value fails the child's
    bound-hash proof, and the positive launch carries the derived value."""

    # Positive: the consumed config carries the sentinel derived from the
    # committed expectations (not a caller value), and the launch reaches
    # COMPLETED through the real bound-hash effect proof.
    config = _make_launch(tmp_path)
    record = capture_run(config)
    assert record["status"] == "COMPLETED", record.get("fault")
    consumed = json.loads(
        (Path(config.run_dir) / BOOTSTRAP_CONFIG_NAME).read_text()
    )
    assert consumed["expected_sentinel_hash"] == SENTINEL_HASH
    proofs = json.loads((Path(config.run_dir) / "effect_proofs.json").read_text())
    assert proofs["checks"]["bound_hash"] is True
    assert proofs["sentinel_hash"] == SENTINEL_HASH

    # Malformed committed value: rejected pre-spawn by the directive validator.
    malformed = _make_launch(
        tmp_path / "malformed",
        expectations_mutator=lambda e: e.update(expected_sentinel_hash="nope"),
    )
    rec = capture_run(malformed)
    _assert_pre_spawn_attestation_infra(
        rec,
        Path(malformed.run_dir),
        detail="expected_sentinel_hash must be an integer",
    )

    # Wrong committed value: well-formed but not the build-pinned hash, so the
    # child's bound-hash effect proof fails closed with no marker.
    wrong = _make_launch(
        tmp_path / "wrong",
        expectations_mutator=lambda e: e.update(
            expected_sentinel_hash=SENTINEL_HASH + 1
        ),
    )
    rec = capture_run(wrong)
    assert rec["status"] == "INFRA_FAILURE"
    assert not (Path(wrong.run_dir) / "payload_started.json").exists()
    failure = json.loads(
        (Path(wrong.run_dir) / "bootstrap_failure.json").read_text()
    )
    assert failure["fault_class"] == "attestation_fault"
    assert "bound_hash" in failure["detail"]


def test_dependency_lock_semantic_mismatch_refuses_launch(tmp_path: Path) -> None:
    """Codex round-3 C1 + F4: the semantic dependency-lock fields are
    recomputed against the DERIVED committed lock unconditionally before
    spawn; a dist RECORD digest drift refuses the launch with a committed
    INFRA_FAILURE."""

    def corrupt(lock: dict) -> None:
        lock["dists"][0]["record_sha256"] = "0" * 64

    config = _make_launch(tmp_path, lock_mutator=corrupt)
    record = capture_run(config)
    _assert_pre_spawn_attestation_infra(
        record,
        Path(config.run_dir),
        detail="dependency-lock semantic fields",
    )
    assert "do not match the committed lock" in record["fault"]["detail"]


def _valid_same_run_winner(config: LaunchConfig) -> dict:
    """A schema-valid INFRA_FAILURE terminal record bound to THIS run — the shape
    a legitimate reconciliation/racing publisher would leave on disk, and the
    only kind of occupant _race_winner_or_raise returns as the authoritative
    winner (Codex hardening round 2)."""

    return {
        "schema_version": 1,
        "record_kind": config.record_kind,
        "status": "INFRA_FAILURE",
        "run_id": config.run_id,
        "launch_attempt_id": config.launch_attempt_id,
        "chain": dict(config.chain),
        "fault": {
            "fault_class": "capture_fault",
            "detail": "reconstructed after parent death",
            "reconstructed": True,
            "payload_started": False,
        },
        "evidence": {
            "raw_manifest_sha256": "0" * 64,
            "node_evidence_digests": [],
            "event_stream_balanced": False,
        },
        "not_a_result": True,
    }


def test_racing_terminal_publication_is_never_clobbered_by_capture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Codex round-3 C4 at the capture level: when a reconciliation racing this
    capture publishes a valid same-run terminal first, the capture publish loses
    on EEXIST and returns the durable on-disk winner verbatim — it never
    overwrites it, and the launch-attempt evidence survives alongside."""

    config = _make_launch(tmp_path)
    winner = _valid_same_run_winner(config)
    real_write = capture_module._write_terminal

    def racing_write(rd: Path, record: dict) -> str:
        if record.get("status") == "COMPLETED":
            real_write(rd, winner)  # a reconciler wins just before capture
        return real_write(rd, record)

    monkeypatch.setattr(capture_module, "_write_terminal", racing_write)
    record = capture_run(config)
    run_dir = Path(config.run_dir)
    assert record == winner
    assert json.loads((run_dir / TERMINAL_RECORD_NAME).read_text()) == winner
    assert (run_dir / RAW_MANIFEST_NAME).is_file()
    assert (run_dir / "payload_started.json").is_file()


def test_canonical_squatter_is_not_returned_as_winner(tmp_path: Path) -> None:
    """Codex hardening round 2: a canonical-but-schema-invalid occupant (here an
    empty object) is NOT an authoritative terminal record, so capture_run raises
    TerminalWriteError rather than returning it — capture_run's return value is
    always a schema-valid terminal record or a raised exception, never a
    non-record. The squatter is preserved, never clobbered."""

    config = _make_launch(
        tmp_path,
        extra_payload_code=(
            "open(os.path.join("
            f"{os.fspath(tmp_path / 'run')!r}, 'terminal_record.json'), "
            "'wb').write(b'{}')"
        ),
    )
    with pytest.raises(capture_module.TerminalWriteError, match="schema-invalid"):
        capture_run(config)
    assert (Path(config.run_dir) / TERMINAL_RECORD_NAME).read_bytes() == b"{}"


def test_wrong_run_winner_is_not_returned(tmp_path: Path) -> None:
    """Codex hardening round 2: a canonical, schema-VALID terminal record for a
    DIFFERENT run is still a squatter — capture_run raises rather than returning
    another run's record as this run's outcome. (The run-id mismatch alone
    triggers the refusal; the foreign record is schema-valid so the check reaches
    the identity comparison.)"""

    foreign = {
        "schema_version": 1,
        "record_kind": "diagnostic",
        "status": "INFRA_FAILURE",
        "run_id": "m2cr-some-other-run",
        "launch_attempt_id": LAUNCH_ATTEMPT_ID,
        "chain": dict(CHAIN),
        "fault": {
            "fault_class": "capture_fault",
            "detail": "a different run's record",
            "reconstructed": True,
            "payload_started": False,
        },
        "evidence": {
            "raw_manifest_sha256": "0" * 64,
            "node_evidence_digests": [],
            "event_stream_balanced": False,
        },
        "not_a_result": True,
    }
    validate_terminal_record(foreign)  # confirm the occupant is genuinely valid
    foreign_bytes = json.dumps(
        foreign, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    config = _make_launch(
        tmp_path,
        extra_payload_code=(
            "open(os.path.join("
            f"{os.fspath(tmp_path / 'run')!r}, 'terminal_record.json'), "
            f"'wb').write({foreign_bytes!r})"
        ),
    )
    with pytest.raises(capture_module.TerminalWriteError, match="DIFFERENT run"):
        capture_run(config)


def test_write_terminal_fsyncs_the_record_and_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Codex round-3 C4: _write_terminal durably publishes — the record bytes
    are fsync'd before the atomic no-clobber link and the run directory is
    fsync'd after it."""

    run_dir = tmp_path / "run"
    run_dir.mkdir()
    calls: list[int] = []
    real_fsync = os.fsync

    def recording_fsync(fd: int) -> None:
        calls.append(fd)
        real_fsync(fd)

    monkeypatch.setattr(capture_module.os, "fsync", recording_fsync)
    digest = capture_module._write_terminal(run_dir, {"durable": True})
    assert isinstance(digest, str) and len(digest) == 64
    assert len(calls) == 2, "one file fsync before link, one directory fsync after"


def test_mid_run_config_mutation_cannot_redirect_the_failure_record(
    tmp_path: Path,
) -> None:
    """Round-4 (Codex round 3): the failure route is cached from the IN-MEMORY
    authenticated config at startup, never re-read from disk — so a payload
    that rewrites bootstrap_config.json's attestation_paths.failure DURING the
    run and then provokes a post-marker fault cannot redirect the failure
    evidence; it lands at the parent-contained route, and the mutation itself
    voids certification at post-exit."""

    outside = tmp_path / "outside" / "hijacked_failure.json"
    run_dir_path = tmp_path / "run"
    extra = (
        "import json as _json\n"
        f"    _cfg_path = os.path.join({os.fspath(run_dir_path)!r}, "
        "'bootstrap_config.json')\n"
        "    _cfg = _json.loads(open(_cfg_path).read())\n"
        f"    _cfg['attestation_paths']['failure'] = {os.fspath(outside)!r}\n"
        "    open(_cfg_path, 'w').write(_json.dumps(_cfg, sort_keys=True, "
        "separators=(',', ':')))"
    )
    config = _make_launch(
        tmp_path, mode="delete_marker", extra_payload_code=extra
    )
    record = capture_run(config)
    run_dir = Path(config.run_dir)
    # The child's post-payload Stage-C marker failure persisted its evidence
    # at the route cached from the authenticated startup bytes — never at the
    # path the mid-run mutation named.
    assert not outside.exists()
    assert not outside.parent.exists()
    failure = json.loads((run_dir / "bootstrap_failure.json").read_text())
    assert failure["fault_class"] == "attestation_fault"
    assert "payload marker" in failure["detail"]
    # The mutation itself independently voids certification at post-exit.
    assert record["status"] == "INFRA_FAILURE"
    assert record["fault"]["fault_class"] == "capture_fault"
    assert (
        "bootstrap config changed between write and post-exit attestation"
        in record["fault"]["detail"]
    )
    validate_terminal_record(record)


def test_race_loser_with_unreadable_squatter_raises_write_error(
    tmp_path: Path,
) -> None:
    """Finding 6 (hardening-cycle correction): when the terminal name is occupied
    by a non-protocol writer's unreadable/noncanonical bytes, nothing of ours was
    durably published, so capture_run raises TerminalWriteError (carrying the
    attempted record) rather than returning a never-published record — the
    finding-6 return-only-authoritative-durable-record contract. The squatter is
    preserved on disk, never clobbered. (This supersedes the round-4 behavior of
    returning the in-memory record, which contradicted the WI6 contract.)"""

    config = _make_launch(
        tmp_path,
        extra_payload_code=(
            "open(os.path.join("
            f"{os.fspath(tmp_path / 'run')!r}, 'terminal_record.json'), "
            "'wb').write(b'NOT-JSON-SQUATTER')"
        ),
    )
    with pytest.raises(capture_module.TerminalWriteError) as excinfo:
        capture_run(config)
    run_dir = Path(config.run_dir)
    # The squatter is preserved (never clobbered); our record carried by the
    # exception was COMPLETED but was not published.
    assert (run_dir / TERMINAL_RECORD_NAME).read_bytes() == b"NOT-JSON-SQUATTER"
    assert excinfo.value.attempted_record["status"] == "COMPLETED"
    assert "occupied by a non-authoritative or unreadable file" in str(excinfo.value)


def test_write_terminal_mode_honors_the_caller_umask(tmp_path: Path) -> None:
    """Round-4 (Codex round 2): the published terminal keeps the historical
    open-with-0o644-under-umask semantics; publication must not override a
    restrictive caller umask."""

    run_dir = tmp_path / "run"
    run_dir.mkdir()
    previous = os.umask(0o077)
    try:
        capture_module._write_terminal(run_dir, {"durable": True})
    finally:
        os.umask(previous)
    mode = (run_dir / TERMINAL_RECORD_NAME).stat().st_mode & 0o777
    assert mode == 0o600


def test_write_terminal_full_write_loop_survives_short_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Round-4 (Codex + Opus convergent): a POSIX short write must never
    publish truncated terminal bytes — the full-write loop completes the
    payload even when each os.write consumes at most 7 bytes."""

    run_dir = tmp_path / "run"
    run_dir.mkdir()
    real_write = os.write

    def short_write(fd: int, data: bytes) -> int:
        return real_write(fd, bytes(data)[:7])

    monkeypatch.setattr(capture_module.os, "write", short_write)
    record = {"durable": True, "padding": "x" * 200}
    digest = capture_module._write_terminal(run_dir, record)
    on_disk = (run_dir / TERMINAL_RECORD_NAME).read_bytes()
    assert on_disk == json.dumps(
        record, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    assert hashlib.sha256(on_disk).hexdigest() == digest


def test_write_terminal_surfaces_directory_fsync_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Round-4 + finding 6: a directory-fsync failure surfaces as the typed
    TerminalDurabilityUncertain state — the publication is visible and
    byte-complete, but crash-durability is unconfirmed, so it is reported
    explicitly (carrying the on-disk record + digest) rather than swallowed OR
    reported as a confirmed-durable publication."""

    run_dir = tmp_path / "run"
    run_dir.mkdir()
    calls: list[int] = []
    real_fsync = os.fsync

    def failing_directory_fsync(fd: int) -> None:
        calls.append(fd)
        if len(calls) == 2:
            raise OSError("simulated directory fsync EIO")
        real_fsync(fd)

    monkeypatch.setattr(capture_module.os, "fsync", failing_directory_fsync)
    with pytest.raises(
        capture_module.TerminalDurabilityUncertain, match="could not be fsync"
    ) as excinfo:
        capture_module._write_terminal(run_dir, {"durable": True})
    # The bytes ARE visible at the final name; the exception carries the
    # authoritative record + digest, only durability is uncertain.
    on_disk = json.loads((run_dir / TERMINAL_RECORD_NAME).read_text())
    assert on_disk == {"durable": True}
    assert excinfo.value.record == {"durable": True}
    assert excinfo.value.digest == hashlib.sha256(
        json.dumps({"durable": True}, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    assert isinstance(excinfo.value.cause, OSError)


def test_concurrent_same_process_publishers_cannot_interfere(
    tmp_path: Path,
) -> None:
    """Round-4 (Codex): PID-only temp naming let same-process concurrent
    publishers unlink and hard-link each other's in-flight temp; the
    per-call-unique mkstemp temp guarantees exactly one winner whose published
    bytes are intact, every loser failing closed on EEXIST, and no temp
    residue."""

    for round_index in range(10):
        run_dir = tmp_path / f"run{round_index}"
        run_dir.mkdir()
        results: dict[int, tuple[str, str | None, dict]] = {}
        barrier = threading.Barrier(4)

        def publish(index: int, target: Path) -> None:
            record = {"writer": index, "round": round_index}
            barrier.wait()
            try:
                digest = capture_module._write_terminal(target, record)
                results[index] = ("ok", digest, record)
            except RecordAssemblyError:
                results[index] = ("lost", None, record)

        threads = [
            threading.Thread(target=publish, args=(index, run_dir))
            for index in range(4)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        winners = [value for value in results.values() if value[0] == "ok"]
        assert len(winners) == 1, results
        _, digest, record = winners[0]
        on_disk = (run_dir / TERMINAL_RECORD_NAME).read_bytes()
        assert on_disk == json.dumps(
            record, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        assert hashlib.sha256(on_disk).hexdigest() == digest
        assert [path.name for path in run_dir.iterdir()] == [
            TERMINAL_RECORD_NAME
        ], "no temp residue may survive publication"


def test_pre_spawn_race_loser_returns_the_on_disk_terminal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Round-4 (GLM): when another writer (a reconciliation racing this
    capture) publishes the terminal during the pre-spawn window, the pre-spawn
    race loser returns the durable on-disk record verbatim — exactly like the
    normal-capture race loser — never an in-memory record that was never
    published."""

    config = _make_launch(tmp_path)
    run_dir = Path(config.run_dir)
    planted = _valid_same_run_winner(config)

    def racing_prelaunch(*args: object, **kwargs: object) -> dict:
        capture_module._write_terminal(run_dir, planted)
        raise OSError("simulated failure after losing the publish race")

    monkeypatch.setattr(capture_module, "_prelaunch", racing_prelaunch)
    record = capture_run(config)
    assert record == planted
    assert json.loads((run_dir / TERMINAL_RECORD_NAME).read_text()) == planted


def test_normal_and_fallback_publication_both_route_through_write_terminal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Codex round-3 C4: both the normal terminal publication and the
    last-resort fallback publish through the single durable no-clobber
    _write_terminal protocol (whose fsync behavior is proven above)."""

    published: list[str] = []
    real_write = capture_module._write_terminal

    def spying_write(run_dir: Path, record: dict) -> str:
        published.append(record.get("status", "<none>"))
        return real_write(run_dir, record)

    monkeypatch.setattr(capture_module, "_write_terminal", spying_write)

    normal = capture_run(_make_launch(tmp_path / "normal"))
    assert normal["status"] == "COMPLETED", normal.get("fault")
    assert published == ["COMPLETED"]

    published.clear()

    def exploding_assembly(*args: object, **kwargs: object) -> dict:
        raise RecordAssemblyError("synthetic assembly explosion for durability")

    monkeypatch.setattr(
        capture_module, "assemble_terminal_record", exploding_assembly
    )
    fallback_config = _make_launch(tmp_path / "fallback")
    fallback = capture_run(fallback_config)
    assert fallback["status"] == "INFRA_FAILURE"
    assert published == ["INFRA_FAILURE"]
    on_disk = json.loads(
        (Path(fallback_config.run_dir) / TERMINAL_RECORD_NAME).read_text()
    )
    assert on_disk == fallback


# ---------------------------------------------------------------------------
# Finding 6: truthful terminal-publication states.  _write_terminal returns a
# digest ONLY on a confirmed-durable publication; every other outcome is a
# distinct typed exception, so capture_run/reconcile_run never return a record
# that misrepresents an uncommitted or not-durably-committed outcome.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "mode",
    ["short_write_zero", "content_write_oserror", "content_fsync_oserror", "link_oserror"],
)
def test_write_terminal_write_failures_publish_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    """A temp-write, content-fsync, or non-EEXIST hard-link failure leaves the
    final name untouched: TerminalWriteError is raised carrying the attempted
    record + cause, and nothing is published."""

    run_dir = tmp_path / "run"
    run_dir.mkdir()
    record = {"attempted": True}
    real_write, real_fsync, real_link = os.write, os.fsync, os.link
    if mode == "short_write_zero":
        monkeypatch.setattr(capture_module.os, "write", lambda fd, data: 0)
    elif mode == "content_write_oserror":

        def boom_write(fd: int, data: bytes) -> int:
            raise OSError("simulated content write EIO")

        monkeypatch.setattr(capture_module.os, "write", boom_write)
    elif mode == "content_fsync_oserror":
        calls: list[int] = []

        def boom_fsync(fd: int) -> None:
            calls.append(fd)
            raise OSError("simulated content fsync EIO")  # the first fsync

        monkeypatch.setattr(capture_module.os, "fsync", boom_fsync)
    else:

        def boom_link(src: str, dst: str) -> None:
            raise PermissionError("simulated hard-link EPERM")

        monkeypatch.setattr(capture_module.os, "link", boom_link)
    with pytest.raises(capture_module.TerminalWriteError) as excinfo:
        capture_module._write_terminal(run_dir, record)
    assert excinfo.value.attempted_record == record
    assert isinstance(excinfo.value.cause, OSError)
    assert not (run_dir / TERMINAL_RECORD_NAME).exists()
    # No temp residue either.
    assert list(run_dir.iterdir()) == []


def test_write_terminal_directory_open_failure_is_durability_uncertain(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If the record is linked into place but the run-directory cannot even be
    opened for fsync, the bytes are visible yet durability is unconfirmed —
    TerminalDurabilityUncertain, not a confirmed publication."""

    run_dir = tmp_path / "run"
    run_dir.mkdir()
    real_open = os.open

    def failing_dir_open(path, flags, *args, **kwargs):
        if flags == os.O_RDONLY:
            raise OSError("simulated directory open EACCES")
        return real_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(capture_module.os, "open", failing_dir_open)
    with pytest.raises(capture_module.TerminalDurabilityUncertain):
        capture_module._write_terminal(run_dir, {"durable": True})
    assert json.loads((run_dir / TERMINAL_RECORD_NAME).read_text()) == {
        "durable": True
    }


def test_write_terminal_eexist_is_terminal_already_exists_even_for_malformed_winner(
    tmp_path: Path,
) -> None:
    """An occupied final name yields TerminalAlreadyExists regardless of whether
    the occupant is a valid record or a malformed squatter — the no-clobber
    protocol never overwrites, and classifying the occupant is the caller's job."""

    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / TERMINAL_RECORD_NAME).write_bytes(b"NOT-JSON-SQUATTER")
    with pytest.raises(
        capture_module.TerminalAlreadyExists, match="already exists"
    ):
        capture_module._write_terminal(run_dir, {"loser": True})
    # The squatter is preserved, never clobbered.
    assert (run_dir / TERMINAL_RECORD_NAME).read_bytes() == b"NOT-JSON-SQUATTER"


def test_capture_run_propagates_a_normal_publication_write_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Finding 6: when the normal terminal publication cannot commit anything,
    capture_run raises TerminalWriteError carrying the real assembled record —
    it does NOT return that record as though it were durably committed."""

    config = _make_launch(tmp_path)

    def failing_write(run_dir: Path, record: dict) -> str:
        raise capture_module.TerminalWriteError(
            "simulated publication failure",
            attempted_record=record,
            cause=OSError("ENOSPC"),
        )

    monkeypatch.setattr(capture_module, "_write_terminal", failing_write)
    with pytest.raises(capture_module.TerminalWriteError) as excinfo:
        capture_run(config)
    assert excinfo.value.attempted_record["status"] == "COMPLETED"
    assert isinstance(excinfo.value.cause, OSError)


def test_capture_run_propagates_a_pre_spawn_publication_write_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Finding 6: a pre-spawn INFRA_FAILURE whose terminal cannot be published
    surfaces as TerminalWriteError rather than a returned, never-committed
    record — the ratified "never silently reclassify" invariant now fails
    LOUDLY when there is genuinely no terminal on disk."""

    # Force a pre-spawn attestation failure (missing committed infra manifest),
    # so capture_run enters the pre-spawn publication handler.
    config = _make_launch(tmp_path)
    (Path(config.worktree_root) / _INFRA_RELPATH).unlink()

    def failing_write(run_dir: Path, record: dict) -> str:
        raise capture_module.TerminalWriteError(
            "simulated pre-spawn publication failure",
            attempted_record=record,
            cause=OSError("EROFS"),
        )

    monkeypatch.setattr(capture_module, "_write_terminal", failing_write)
    with pytest.raises(capture_module.TerminalWriteError) as excinfo:
        capture_run(config)
    assert excinfo.value.attempted_record["status"] == "INFRA_FAILURE"


def test_reconcile_run_propagates_a_publication_write_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Finding 6: reconciliation surfaces a publication write failure truthfully
    instead of returning a reconstructed record that was never committed."""

    run_dir = tmp_path / "reconcile"
    _write_reconcile_evidence(run_dir)

    def failing_write(root: Path, record: dict) -> str:
        raise capture_module.TerminalWriteError(
            "simulated reconcile publication failure",
            attempted_record=record,
            cause=OSError("ENOSPC"),
        )

    monkeypatch.setattr(capture_module, "_write_terminal", failing_write)
    with pytest.raises(capture_module.TerminalWriteError) as excinfo:
        reconcile_run(run_dir)
    assert excinfo.value.attempted_record["status"] == "INFRA_FAILURE"
    assert excinfo.value.attempted_record["fault"]["reconstructed"] is True


def test_normal_capture_racing_reconciliation_returns_the_durable_winner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Finding 6 / C4: when a reconciliation publishes this run's terminal in the
    window before normal capture's own publication, capture hits EEXIST
    (TerminalAlreadyExists) and returns the durable on-disk winner verbatim — it
    never clobbers, never escapes, and never returns an un-published record."""

    config = _make_launch(tmp_path)
    run_dir = Path(config.run_dir)
    reconciled = _valid_same_run_winner(config)
    real_write = capture_module._write_terminal

    def racing_write(rd: Path, record: dict) -> str:
        # A reconciler wins the publish race just before capture publishes.
        if record.get("status") == "COMPLETED":
            real_write(rd, reconciled)
        return real_write(rd, record)

    monkeypatch.setattr(capture_module, "_write_terminal", racing_write)
    record = capture_run(config)
    assert record == reconciled
    assert json.loads((run_dir / TERMINAL_RECORD_NAME).read_text()) == reconciled


def test_reconcile_run_refuses_on_a_racing_terminal_valid_or_squatter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Codex hardening round 2: reconcile_run's contract is REFUSE on any
    pre-existing terminal, so when a terminal appears in the window between its
    precheck and its own publish — whether a valid winner or a malformed squatter
    — it raises TerminalAlreadyExists (a RecordAssemblyError refusal) and never
    returns an un-published reconstructed record.  Distinct from the capture
    race-loser contract (which returns the valid winner); reconcile does not
    reconstruct over an occupied name."""

    for occupant in (b'{"a":1}', b"NOT-JSON-SQUATTER"):
        run_dir = tmp_path / f"reconcile-{len(occupant)}"
        _write_reconcile_evidence(run_dir)
        real_write = capture_module._write_terminal

        def racing_write(rd: Path, record: dict, _bytes=occupant) -> str:
            # A racing writer occupies the terminal name between reconcile's
            # precheck and its publish.
            (rd / TERMINAL_RECORD_NAME).write_bytes(_bytes)
            return real_write(rd, record)

        monkeypatch.setattr(capture_module, "_write_terminal", racing_write)
        with pytest.raises(RecordAssemblyError, match="already exists"):
            reconcile_run(run_dir)
        # The occupant is preserved; reconcile never clobbered it.
        assert (run_dir / TERMINAL_RECORD_NAME).read_bytes() == occupant
        monkeypatch.undo()
