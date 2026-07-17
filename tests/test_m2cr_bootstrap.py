from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
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

# Codex round-3 C1 (Stage C): the hermetic fake native stack.  Every launch
# through the real bootstrap now carries the complete mandatory attestation
# directive set, so the fake torch/numpy modules and the frozen fake values
# below are the single source the tests and the capture-level fake bundle
# share.
FAKE_CF_VALUE = "0x1F5:0x0:0x0"
FAKE_STAGE_B_EXPECTED = {"__CF_USER_TEXT_ENCODING": FAKE_CF_VALUE}
FAKE_TORCH_BUILD_MARKERS = ["FAKE_BLAS=accelerate", "USE_MKL=OFF"]
FAKE_NUMPY_BUILD_MARKERS = ["FAKE_NUMPY_BLAS=accelerate"]
FAKE_PROFILE_SOURCE = "FROZEN_PROFILE_MARKER = 1\n"
MANDATORY_DIRECTIVES = (
    "native_stack_modules",
    "expected_profile_integration_sha256",
    "torch_build_expected",
    "numpy_build_expected",
    "stage_b_expected",
    "loaded_image_allowlist",
    "expected_loaded_images",
)
# The setup probe's deliberately non-loading expectation: well-formed (it
# passes require_mandatory_attestation_directives) but guaranteed to fail
# authentication AFTER the measured Stage-B evidence is recorded, so the probe
# can never emit payload_started.json.
UNAUTHENTICATED_PROBE_EXPECTATION = [
    {"path": "/m2cr-fixture/unauthenticated-probe.dylib", "sha256": "0" * 64}
]

pytestmark = pytest.mark.skipif(
    sys.platform != "darwin", reason="raw _NSGetEnviron is Darwin-specific"
)


def _fake_torch_source(thread_log: Path, variant: str) -> str:
    """Source of the fake torch package: registers the PID-bound KMP entry and
    the frozen __CF_USER_TEXT_ENCODING in the RAW C environment (mirroring
    libomp/CoreFoundation, invisible to os.environ), exposes the frozen build
    description and the 10/10 thread controls."""

    interop_tail = (
        "raise RuntimeError('synthetic interop failure')"
        if variant == "raise"
        else "return None"
    )
    intra_readback = (
        "return 9" if variant == "wrong-readback" else 'return _threads["intra"]'
    )
    return f"""import ctypes
import os
from pathlib import Path

_libc = ctypes.CDLL(None)
_libc.setenv(b"__CF_USER_TEXT_ENCODING", b"{FAKE_CF_VALUE}", 1)
_libc.setenv(
    f"__KMP_REGISTERED_LIB_{{os.getpid()}}".encode(),
    b"0x1234-cafe1234-libomp.dylib",
    1,
)
_log = Path({os.fspath(thread_log)!r})
_threads = {{"intra": 0, "interop": 0}}


class _Config:
    @staticmethod
    def show():
        return "{FAKE_TORCH_BUILD_MARKERS[0]}\\n{FAKE_TORCH_BUILD_MARKERS[1]}"


__config__ = _Config()


def set_num_threads(value):
    _threads["intra"] = value
    _log.write_text(f"intra={{value}}\\n", encoding="utf-8")

def set_num_interop_threads(value):
    _threads["interop"] = value
    with _log.open("a", encoding="utf-8") as handle:
        handle.write(f"interop={{value}}\\n")
    {interop_tail}

def get_num_threads():
    {intra_readback}

def get_num_interop_threads():
    return _threads["interop"]
"""


def _fake_numpy_source() -> str:
    return (
        "def show_config():\n"
        f"    print({FAKE_NUMPY_BUILD_MARKERS[0]!r})\n"
    )


def write_fake_native_stack(worktree: Path, *, torch_variant: str = "ok") -> Path:
    """Materialize fake torch + numpy at the worktree root (sys.path index 0
    shadows the real site-packages) and return the torch thread-call log."""

    thread_log = worktree / "thread_calls.txt"
    torch_dir = worktree / "torch"
    torch_dir.mkdir()
    (torch_dir / "__init__.py").write_text(
        _fake_torch_source(thread_log, torch_variant), encoding="utf-8"
    )
    (worktree / "numpy.py").write_text(_fake_numpy_source(), encoding="utf-8")
    return thread_log


_measured_expected_loaded_images: list[dict[str, str]] | None = None


def measured_expected_loaded_images() -> list[dict[str, str]]:
    """Session-cached loaded-image expectations, measured by the setup probe
    and hashed test-side.

    The probe launches the REAL bootstrap through the real validation path with
    ``UNAUTHENTICATED_PROBE_EXPECTATION`` as its expected set: authentication
    fails closed AFTER the measured Stage-B evidence (native_stack.json) is
    recorded and BEFORE the marker, so the probe never emits
    payload_started.json.  The probe's native_stack.json is UNAUTHENTICATED
    setup evidence, never a successful attestation: only its recorded image
    PATHS are consumed, and each on-disk image is re-hashed here test-side
    (the probe's own recorded hashes are deliberately ignored, so a launch can
    never self-certify its expectation set within one invocation).  Two
    independent probe measurements must agree exactly; a disagreement fails
    the fixture rather than weakening authentication.
    """

    global _measured_expected_loaded_images
    if _measured_expected_loaded_images is None:
        measurements: list[list[str]] = []
        for attempt in ("first", "second"):
            probe_root = Path(
                tempfile.mkdtemp(prefix=f"m2cr-image-probe-{attempt}-")
            )
            try:
                completed, run_dir, events = _launch_bootstrap(
                    probe_root,
                    expected_loaded_images=UNAUTHENTICATED_PROBE_EXPECTATION,
                )
                assert completed.returncode not in (0, 3), (
                    "the dummy-fail probe must fail authentication"
                )
                assert (
                    b"has no committed expectation" in completed.stderr
                ), completed.stderr.decode()
                assert not (run_dir / "payload_started.json").exists(), (
                    "the unauthenticated probe must never emit the marker"
                )
                assert [event["event"] for event in events] == ["HELLO"]
                native = json.loads(
                    (run_dir / "native_stack.json").read_text()
                )
                paths = native["loaded_images_stage_b"]
                assert paths and paths == sorted(paths)
                measurements.append(list(paths))
            finally:
                shutil.rmtree(probe_root, ignore_errors=True)
        if measurements[0] != measurements[1]:
            pytest.fail(
                "repeated unauthenticated probe measurements disagree; "
                "refusing to cache session-scoped loaded-image expectations "
                "rather than weaken authentication: "
                f"{sorted(set(measurements[0]) ^ set(measurements[1]))}"
            )
        expected: list[dict[str, str]] = []
        for path in measurements[0]:
            if not os.path.isfile(path):
                continue
            with open(path, "rb") as handle:
                digest = hashlib.file_digest(handle, "sha256").hexdigest()
            expected.append({"path": path, "sha256": digest})
        assert expected, "the probe must measure at least one on-disk image"
        _measured_expected_loaded_images = expected
    return [dict(entry) for entry in _measured_expected_loaded_images]

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
    profile_import: bool = True,
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
    fake_torch: str = "ok",
    native_stack_modules: list[str] | None = None,
    stage_b_expected: dict[str, str] | None = None,
    torch_build_expected: object = "auto",
    numpy_build_expected: object = "auto",
    expected_loaded_images: object = "measured",
    profile: str = "match",
    omit_directives: tuple[str, ...] = (),
    config_sha256: str | None = None,
    attestation_path_overrides: dict[str, str] | None = None,
) -> tuple[subprocess.CompletedProcess[bytes], Path, list[dict[str, object]]]:
    """Launch the REAL bootstrap in a synthetic four-root worktree.

    Codex round-3 C1 (Stage C): every launch carries the complete
    seven-directive mandatory attestation set by default — the fake native
    stack (torch + numpy), the fake in-worktree profile_integration stub, the
    frozen fake Stage-B/build markers, and the session-measured
    expected_loaded_images — so the config exercises the same unconditional
    production validation and marker path as a real launch.  Negative tests
    weaken exactly one directive via ``omit_directives`` or an explicit
    override; there is no test-only bypass.
    """

    worktree = tmp_path / "worktree"
    run_dir = worktree / "run"
    worktree.mkdir(parents=True)
    run_dir.mkdir()
    # The profile check needs a hashable in-worktree fake module; only the
    # m2cr subpackage is shared with the repository.
    package_dir = worktree / "bistar_gp"
    package_dir.mkdir()
    (package_dir / "m2cr").symlink_to(
        REPOSITORY_ROOT / "bistar_gp" / "m2cr", target_is_directory=True
    )
    fake_profile_path = package_dir / "profile_integration.py"
    fake_profile_path.write_text(FAKE_PROFILE_SOURCE, encoding="utf-8")
    data_path: Path | None = None
    if mode == "open_worktree":
        data_path = worktree / "payload_data.txt"
        data_path.write_bytes(b"frozen worktree bytes\n")
    side_effect = worktree / "payload_imported.txt"
    marker_path = run_dir / "payload_started.json"
    thread_log = write_fake_native_stack(worktree, torch_variant=fake_torch)
    (worktree / "fake_payload.py").write_text(
        _payload_source(
            mode,
            marker_path=marker_path,
            import_side_effect=side_effect if import_spy else None,
            thread_log=thread_log,
            data_path=data_path,
        ),
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
    if attestation_path_overrides:
        paths.update(attestation_path_overrides)
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
    if expected_loaded_images == "measured":
        resolved_images = measured_expected_loaded_images()
    else:
        resolved_images = expected_loaded_images
    config = {
        "four_roots": roots,
        "frozen_env": expected_environment,
        "expected_pycache_prefix": os.fspath(pycache.resolve()),
        "expected_sentinel_hash": SENTINEL_HASH,
        "native_stack_modules": (
            ["torch", "numpy"]
            if native_stack_modules is None
            else native_stack_modules
        ),
        "expected_profile_integration_sha256": (
            sha256_file(fake_profile_path) if profile == "match" else "f" * 64
        ),
        "stage_b_expected": (
            dict(FAKE_STAGE_B_EXPECTED)
            if stage_b_expected is None
            else stage_b_expected
        ),
        "loaded_image_allowlist": [],
        "expected_loaded_images": resolved_images,
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
    if torch_build_expected == "auto":
        config["torch_build_expected"] = list(FAKE_TORCH_BUILD_MARKERS)
    elif torch_build_expected is not None:
        config["torch_build_expected"] = torch_build_expected
    if numpy_build_expected == "auto":
        config["numpy_build_expected"] = list(FAKE_NUMPY_BUILD_MARKERS)
    elif numpy_build_expected is not None:
        config["numpy_build_expected"] = numpy_build_expected
    for directive in omit_directives:
        config.pop(directive, None)
    config_path = run_dir / "config.json"
    config_text = canonical_dumps(config)
    config_path.write_text(config_text, encoding="utf-8")
    # Round-4: the parent transport-binds the exact written config bytes to
    # the child via an argv digest; the harness does the same (an explicit
    # config_sha256 override exercises the mismatch rejection).
    if config_sha256 is None:
        config_sha256 = hashlib.sha256(
            config_text.encode("utf-8")
        ).hexdigest()
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
            config_sha256,
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
    # C1 (Stage C): the mandatory native stack is attested on every launch —
    # the fake torch/numpy resolve from the worktree root, never the real
    # site-packages.
    fake_torch_entry = next(item for item in modules if item["module"] == "torch")
    assert fake_torch_entry["origin"].startswith(
        os.fspath(run_dir.parent.resolve())
    )
    fake_numpy_entry = next(item for item in modules if item["module"] == "numpy")
    assert fake_numpy_entry["origin"].startswith(
        os.fspath(run_dir.parent.resolve())
    )
    # C1: the profile-hash directive is mandatory, so the explicit §4.5.10
    # comparison ran and matched on this successful launch.
    profile_check = inventory["profile_integration_check"]
    assert profile_check["module_loaded"] is True
    assert profile_check["match"] is True
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


def test_stage_b_native_delta_is_classified_and_stage_c_detects_drift(
    tmp_path: Path,
) -> None:
    completed, run_dir, _ = _launch_bootstrap(tmp_path / "clean")
    assert completed.returncode == 0, completed.stderr.decode()
    # The fake native stack must never touch os.environ (only the raw C view
    # carries the accepted CF + PID-bound KMP additions).
    assert json.loads((run_dir / "stage_b_os.json").read_text())["delta"] == {
        "added": {},
        "removed": {},
        "changed": {},
    }
    raw_added = json.loads((run_dir / "stage_b_raw.json").read_text())["delta"][
        "added"
    ]
    assert set(raw_added) == {
        "__CF_USER_TEXT_ENCODING",
        next(key for key in raw_added if key.startswith("__KMP_REGISTERED_LIB_")),
    }
    drifted, drift_run, _ = _launch_bootstrap(tmp_path / "drift", mode="drift")
    assert drifted.returncode not in (0, 3)
    assert "Stage C environment drift" in drifted.stderr.decode()
    assert not (drift_run / "stage_c.json").exists()
    assert (drift_run / "payload_started.json").exists()


def test_empty_native_stack_declaration_fails_closed(tmp_path: Path) -> None:
    """Codex round-3 C1: an EMPTY native-stack declaration is rejected by the
    unconditional mandatory-directive gate before any native import — the lean
    empty-stack launch the old hermetic tests used can never reach the marker."""

    completed, run_dir, events = _launch_bootstrap(
        tmp_path, native_stack_modules=[]
    )
    assert completed.returncode not in (0, 3)
    assert (
        "native_stack_modules must be a non-empty string list"
        in completed.stderr.decode()
    )
    assert [event["event"] for event in events] == ["HELLO"]
    assert not (run_dir / "payload_started.json").exists()
    # Enforcement precedes the native imports and Stage-B measurement.
    assert not (run_dir / "native_stack.json").exists()


@pytest.mark.parametrize("directive", MANDATORY_DIRECTIVES)
def test_each_mandatory_directive_omitted_individually_fails_closed(
    tmp_path: Path, directive: str
) -> None:
    """Codex round-3 C1 (requirement 1): every production marker path requires
    ALL seven mandatory attestation directives — omitting any single one fails
    closed before any native import, with no marker and no Stage-B evidence."""

    completed, run_dir, events = _launch_bootstrap(
        tmp_path, omit_directives=(directive,)
    )
    assert completed.returncode not in (0, 3)
    stderr = completed.stderr.decode()
    assert "missing mandatory attestation directives" in stderr
    assert directive in stderr
    assert [event["event"] for event in events] == ["HELLO"]
    assert not (run_dir / "payload_started.json").exists()
    assert not (run_dir / "native_stack.json").exists()
    failure = json.loads((run_dir / "bootstrap_failure.json").read_text())
    assert failure["fault_class"] == "attestation_fault"


@pytest.mark.parametrize(
    "case", ["missing_expected", "unexpected_additional", "hash_mismatch"]
)
def test_loaded_image_authentication_fails_closed_at_launch(
    tmp_path: Path, case: str
) -> None:
    """Codex round-3 C1 + F2 at the launch level: the real bootstrap's
    measured Stage-B images are authenticated against the committed expected
    set — a committed-expected image that did not load, a loaded image with no
    committed expectation, and an expected-image hash mismatch each fail
    closed AFTER the measured evidence is recorded and BEFORE the marker."""

    measured = measured_expected_loaded_images()
    if case == "missing_expected":
        expected = measured + [
            {"path": "/m2cr-fixture/never-loads.dylib", "sha256": "1" * 64}
        ]
        message = "committed-expected native image did not"
    elif case == "unexpected_additional":
        expected = measured[:-1]
        message = "has no committed expectation"
    else:
        expected = [dict(measured[0], sha256="f" * 64), *measured[1:]]
        message = "does not match its committed expectation"
    completed, run_dir, events = _launch_bootstrap(
        tmp_path, expected_loaded_images=expected
    )
    assert completed.returncode not in (0, 3)
    assert message in completed.stderr.decode()
    assert [event["event"] for event in events] == ["HELLO"]
    # The measured Stage-B evidence is recorded (nothing vanishes), but it is
    # pre-authentication evidence only: the marker must never exist.
    assert (run_dir / "native_stack.json").exists()
    assert not (run_dir / "payload_started.json").exists()
    failure = json.loads((run_dir / "bootstrap_failure.json").read_text())
    assert failure["fault_class"] == "attestation_fault"


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


def test_config_digest_mismatch_fails_closed_before_any_consumption(
    tmp_path: Path,
) -> None:
    """Round-4 (Codex delta review): the child verifies the config bytes it
    read against the parent's argv-bound digest BEFORE consuming any field, so
    a mutation of the mutable bootstrap_config.json between the parent's write
    and the child's read fails closed with no attestation evidence and no
    marker."""

    completed, run_dir, events = _launch_bootstrap(
        tmp_path, config_sha256="e" * 64
    )
    assert completed.returncode not in (0, 3)
    assert "bootstrap config digest mismatch" in completed.stderr.decode()
    assert [event["event"] for event in events] == ["HELLO"]
    assert not (run_dir / "payload_started.json").exists()
    assert not (run_dir / "effect_proofs.json").exists()
    assert not (run_dir / "native_stack.json").exists()
    failure = json.loads((run_dir / "bootstrap_failure.json").read_text())
    assert failure["fault_class"] == "attestation_fault"


def test_rejected_config_cannot_redirect_the_failure_record(
    tmp_path: Path,
) -> None:
    """Round-4 (Codex round 2): a digest-REJECTED config is unauthenticated in
    full — including its attestation_paths — so it cannot redirect the failure
    record to a path it names; the evidence lands beside the config instead,
    and the named path is never created."""

    outside = tmp_path / "outside" / "hijacked_failure.json"
    completed, run_dir, events = _launch_bootstrap(
        tmp_path,
        config_sha256="e" * 64,
        attestation_path_overrides={"failure": os.fspath(outside)},
    )
    assert completed.returncode not in (0, 3)
    assert "bootstrap config digest mismatch" in completed.stderr.decode()
    assert [event["event"] for event in events] == ["HELLO"]
    assert not outside.exists()
    assert not outside.parent.exists()
    # The evidence still exists (nothing vanishes) at the untrusted-config
    # fallback location beside the consumed config.
    failure = json.loads((run_dir / "bootstrap_failure.json").read_text())
    assert failure["fault_class"] == "attestation_fault"
    assert "bootstrap config digest mismatch" in failure["detail"]
    # An AUTHENTICATED config still routes through its attestation_paths: the
    # ordinary omission negative writes its failure record through the config
    # (covered by the existing directive-omission tests, whose configs pass
    # the digest gate).


def test_malformed_digest_argument_and_arity_fail_closed(tmp_path: Path) -> None:
    """Round-4: the config-digest argument is mandatory and unconditional —
    a missing argument (old three-argument contract) and a malformed digest
    each fail closed before any consumption."""

    config_stub = tmp_path / "contract" / "config.json"
    config_stub.parent.mkdir(parents=True)
    config_stub.write_text("{}", encoding="utf-8")
    short = subprocess.run(
        [MINICONDA_PYTHON, os.fspath(BOOTSTRAP), os.fspath(config_stub), "9"],
        capture_output=True,
        timeout=30,
    )
    assert short.returncode not in (0, 3)
    assert (
        "expected config path, event fd, and config sha256"
        in short.stderr.decode()
    )
    # Round-4 (Codex round 4): the CLI-contract guard persists its evidence
    # beside the config too — an arity violation is not evidence-less.
    contract_failure = json.loads(
        (config_stub.parent / "bootstrap_failure.json").read_text()
    )
    assert contract_failure["fault_class"] == "attestation_fault"
    assert "expected config path" in contract_failure["detail"]

    completed, run_dir, events = _launch_bootstrap(
        tmp_path, config_sha256="not-a-sha"
    )
    assert completed.returncode not in (0, 3)
    assert (
        "expected bootstrap-config sha256 argument is malformed"
        in completed.stderr.decode()
    )
    assert not (run_dir / "payload_started.json").exists()


def test_native_stack_allowlist_rejects_bistar_gp_and_payload_modules():
    """External audit round-2 F3: native_stack_modules is restricted to the
    frozen native stack so nothing scientific runs before the marker."""

    assert disallowed_native_modules(["torch", "numpy", "scipy.linalg"]) == []
    assert disallowed_native_modules(["bistar_gp.profile_integration"]) == [
        "bistar_gp.profile_integration"
    ]
    assert disallowed_native_modules(["fake_payload"]) == ["fake_payload"]
    assert disallowed_native_modules(["os", "torch"]) == ["os"]
