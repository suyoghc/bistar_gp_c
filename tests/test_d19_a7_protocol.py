"""Hermetic tests for the frozen D19 A7 execution protocol."""

import ast
import hashlib
import importlib.util
import json
import re
import subprocess
from pathlib import Path

import pytest


SCRIPT_PATH = Path("experiments/submit_d19_a7_bench.slurm")
VALIDATOR_PATH = Path("experiments/d19_a7_validate.py")
PROTOCOL_PATH = Path("docs/d19-a7-execution-protocol.md")
TEST_PATH = Path("tests/test_d19_a7_protocol.py")
EXPECTED_SHA = "a" * 40
JOB_ID = "12345"
ATTEMPT1_EXEC_ROOT = "/scratch/gpfs/SUYOGHC/bistar_gp_a7_exec"
ATTEMPT2_EXEC_ROOT = "/scratch/gpfs/SUYOGHC/bistar_gp_a7_exec_02"
ATTEMPT3_EXEC_ROOT = "/scratch/gpfs/SUYOGHC/bistar_gp_a7_exec_03"
PS1_CORRECTION = 'export PS1="${PS1-}"'
FAILED_ATTEMPT_DIR = Path("runs/d19_a7_failed_11485635")
FAILED_ATTEMPT_PINS = {
    "PROVENANCE.sha256": ("c420d12425d6afa29e5b204f2ef47496ed7779485922403f88a7f883e9ca4b25", 253),
    "job_metadata.txt": ("09f524460da0ba70e94d5b0ee42a67f11638346f3235f1f904baa44dc67deb37", 451),
    "slurm-11485635.err": ("59be6fc2986c195cdedc5c28bf6f8a03f3cf6513244db911e8b0f049a3ebc9d1", 44),
    "slurm-11485635.out": ("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", 0),
}

EXPECTED_SBATCH_LINES = (
    "#SBATCH --job-name=d19-a7-bench",
    "#SBATCH --account=suyoghc",
    "#SBATCH --partition=cpu",
    "#SBATCH --constraint=cascade",
    "#SBATCH --exclude=della-h12n[1-13],della-h12n[17-18],della-h17n1,della-i13n25",
    "#SBATCH --nodes=1",
    "#SBATCH --ntasks=1",
    "#SBATCH --cpus-per-task=4",
    "#SBATCH --mem=16G",
    "#SBATCH --time=02:00:00",
    "#SBATCH --chdir=/scratch/gpfs/SUYOGHC/bistar_gp_a7_exec_03",
    "#SBATCH --output=runs/d19_a7_timing/slurm-%j.out",
    "#SBATCH --error=runs/d19_a7_timing/slurm-%j.err",
)
EXPECTED_ENV_LITERALS = (
    "/home/sc8918/.conda/envs/bistar_gp",
    "3.11.14",
    "2.10.0+cu128",
    "1.15.1",
    "1.9.1",
    "2.4.2",
)
EXPECTED_POOL_SPECS = (
    "della-h17n[2-3]",
    "della-i13n[1-24]",
    "della-r3c1n[1-16]",
    "della-r3c2n[1-16]",
    "della-r3c3n[1-16]",
    "della-r3c4n[1-16]",
)

EXPECTED_FIREWALL_NOTE = (
    "prereg v1.2 point 6 and v1.6 item 6 (ratified v1.9 item 1, v1.11 item 4): "
    "this artifact carries only timing, evaluation-count, configuration and "
    "environment fields. Posterior samples and disallowed diagnostics are "
    "discarded unread. Transient prior proposals and MAP-derived values are "
    "read internally ONLY to execute the frozen timing workloads that require "
    "them. None of them is printed or serialized: no hyperparameter, noise, "
    "posterior, curvature-spectrum or per-site value leaves this process."
)
EXPECTED_THREAD_SCOPE_NOTE = (
    "OMP_NUM_THREADS, MKL_NUM_THREADS, OPENBLAS_NUM_THREADS and "
    "VECLIB_MAXIMUM_THREADS were set by this process before importing numpy, "
    "torch, gpytorch or pyro, and torch intra-op threads were set and verified "
    "equal to the request. thread_configuration_checks_passed certifies only "
    "those checks: heavy scientific modules absent when the environment was "
    "set, the four environment variables equal to the request, and torch "
    "intra-op equal to the request. It does NOT certify actual BLAS worker "
    "counts, torch inter-op control, a process-wide ceiling, or exact physical "
    "workers. VECLIB_MAXIMUM_THREADS is a maximum, not a guarantee. Torch "
    "inter-op threads were observed, never set."
)
EXPECTED_DESIGN_LABEL = (
    "whole-span season-preserving even-index subsample "
    "(np.round(np.linspace) over indices)"
)
EXPECTED_CANONICAL_SHA256 = (
    "5bcdc813b4c3b570c9947acfaa0d3ff8cb5f89094b3e4e5121f72535a0cc0910"
)
EXPECTED_VERSIONS = {
    "python": "3.11.14",
    "torch": "2.10.0+cu128",
    "gpytorch": "1.15.1",
    "pyro": "1.9.1",
    "numpy": "2.4.2",
}
REAL_SPECTRE_V2_LINE = (
    "Vulnerability Spectre v2:   Mitigation; Enhanced / Automatic IBRS; "
    "IBPB conditional; PBRSB-eIBRS SW sequence"
)
CONDITION_FINDING = "substring 'condition'"


def _script_ps1_correction_line():
    lines = SCRIPT_PATH.read_text(encoding="utf-8").splitlines()
    matches = [line for line in lines if line == PS1_CORRECTION]
    assert len(matches) == 1, "script must carry the correction as an exact line"
    return matches[0]


def _write_ps1_repro_driver(tmp_path, correction_placement):
    tail = tmp_path / "tail.sh"
    tail.write_text(
        "# Benign modulefile tail prelude.\n"
        'export _LOCAL_OLD_PS1="${PS1}"\n',
        encoding="utf-8",
    )
    lines = ["#!/bin/bash", "set -euo pipefail"]
    if correction_placement == "before":
        lines.append(_script_ps1_correction_line())
    elif correction_placement not in {"after", "absent"}:
        raise ValueError(f"unknown correction placement: {correction_placement}")
    lines.extend([
        "module() {",
        '  case "$1" in',
        "    purge) ;;",
        '    load) . "${0%/*}/tail.sh" ;;',
        "    *) return 2 ;;",
        "  esac",
        "}",
        "module purge",
        "module load anaconda3/2024.6",
    ])
    if correction_placement == "after":
        lines.append(_script_ps1_correction_line())
    lines.append("echo REPRO-OK")
    driver = tmp_path / f"driver-{correction_placement}.sh"
    driver.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return driver, tail


def _run_ps1_repro(driver):
    return subprocess.run(
        ["/bin/bash", str(driver)],
        check=False,
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin"},
    )


def _load_validator():
    spec = importlib.util.spec_from_file_location("d19_a7_validate_tested", VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("validator import spec unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validator = _load_validator()


def _record(scale, threads, *, hessian_status="measured", stage2_status="measured"):
    if hessian_status == "measured":
        hessian = {
            "status": "measured",
            "total_s": 0.0,
            "extrapolated_from_gradient_s": None,
        }
    else:
        hessian = {
            "status": "skipped_for_budget",
            "total_s": None,
            "extrapolated_from_gradient_s": 0.0,
        }
    if stage2_status == "measured":
        stage2 = {
            "status": "measured",
            "n_evals": 1000,
            "total_s": 0.0,
            "per_eval_s": 0.0,
            "n_failed_potential_evals": 0,
        }
    else:
        stage2 = {
            "status": "extrapolated_from_stage1",
            "n_evals": 1000,
            "total_s": 0.0,
            "per_eval_s": 0.0,
            "n_failed_potential_evals": None,
        }
    return {
        "record": {
            "kind": "d19_bench_timing_record",
            "schema_version": 1,
            "firewall_note": EXPECTED_FIREWALL_NOTE,
        },
        "threads": {
            "threads_requested": threads,
            "omp_num_threads_configured": threads,
            "mkl_num_threads_configured": threads,
            "openblas_num_threads_configured": threads,
            "veclib_maximum_threads_configured": threads,
            "torch_num_threads_effective": threads,
            "torch_num_interop_threads_effective": 4,
            "thread_configuration_checks_passed": True,
            "thread_control_scope_note": EXPECTED_THREAD_SCOPE_NOTE,
        },
        "environment": {
            "timestamp": "2026-07-21T12:00:00+00:00",
            "git_sha": EXPECTED_SHA,
            "python": EXPECTED_VERSIONS["python"],
            "platform": "synthetic-rh9-platform",
            "hostname": "della-r3c2n7",
            "cpu_count": 4,
            "torch": EXPECTED_VERSIONS["torch"],
            "gpytorch": EXPECTED_VERSIONS["gpytorch"],
            "pyro": EXPECTED_VERSIONS["pyro"],
            "numpy": EXPECTED_VERSIONS["numpy"],
        },
        "run_config": {
            "scale": scale,
            "design_label": EXPECTED_DESIGN_LABEL,
            "n_points": 150 if scale == "sub" else 461,
            "seed": 0,
            "budget_s": 600.0,
            "n_iter_map": 300,
            "n_iter_profile": 150,
            "n_prior_evals_stage1": 100,
            "n_prior_evals_stage2": 1000,
        },
        "data_provenance": {
            "openml_data_id": 41187,
            "source": "vendored",
            "canonical_sha256": EXPECTED_CANONICAL_SHA256,
            "n_train_points": 461,
        },
        "structure": {
            "n_sampled_sites": 7,
            "dim_unconstrained": 7,
        },
        "timings": {
            "map_fit": {
                "status": "measured",
                "n_iter": 300,
                "total_s": 0.0,
                "per_iter_s": 0.0,
            },
            "initialize_model": {
                "status": "measured",
                "total_s": 0.0,
            },
            "potential_value_eval": {
                "status": "measured",
                "median_s": 0.0,
                "mean_s": 0.0,
                "min_s": 0.0,
                "max_s": 0.0,
                "reps": 5,
                "warmup_calls": 1,
            },
            "gradient": {
                "status": "measured",
                "median_s": 0.0,
                "mean_s": 0.0,
                "min_s": 0.0,
                "max_s": 0.0,
                "reps": 5,
                "warmup_calls": 1,
            },
            "hessian": hessian,
            "prior_eval_stage1": {
                "status": "measured",
                "n_evals": 100,
                "total_s": 0.0,
                "per_eval_s": 0.0,
                "n_failed_potential_evals": 0,
            },
            "prior_eval_stage2": stage2,
            "profile_grid_point": {
                "status": "measured",
                "n_iter": 150,
                "total_s": 0.0,
                "per_iter_s": 0.0,
                "laplace_det_bound_s": 0.0,
                "composite_per_point_est_s": 0.0,
            },
        },
        "warning_counts": [],
        "totals": {"elapsed_s": 0.0},
    }


def _json_path(evidence_dir, scale="sub", threads=1):
    return evidence_dir / f"bench_{scale}_threads_{threads}.json"


def _write_record(path, record):
    path.write_text(json.dumps(record, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _report_line(scale, elapsed_s):
    return json.dumps(
        {
            "kind": "d19_bench_timing_record",
            "scale": scale,
            "n_points": 150 if scale == "sub" else 461,
            "elapsed_s": elapsed_s,
        },
        separators=(",", ":"),
    )


def _write_stdout(evidence_dir, overrides=None, extra_lines=()):
    overrides = overrides or {}
    lines = [
        "ENV-OK /home/sc8918/.conda/envs/bistar_gp/bin/python "
        "3.11.14 2.10.0+cu128 1.15.1 1.9.1 2.4.2",
    ]
    for scale, threads in ((s, t) for s in ("sub", "full") for t in (1, 2, 3, 4)):
        filename = f"bench_{scale}_threads_{threads}.json"
        record = json.loads((evidence_dir / filename).read_text(encoding="utf-8"))
        lines.append(_report_line(scale, record["totals"]["elapsed_s"]))
        lines.append(f"CELL {scale} {threads} exit 0 end 2026-07-21T12:00:00Z")
    for scale, threads in ((s, t) for s in ("sub", "full") for t in (1, 2, 3, 4)):
        filename = f"bench_{scale}_threads_{threads}.json"
        digest = overrides.get(filename, _sha256(evidence_dir / filename))
        lines.append(f"{digest}  runs/d19_a7_timing/{filename}")
    lines.extend(extra_lines)
    lines.append("MATRIX-COMPLETE 2026-07-21T12:00:00Z")
    (evidence_dir / f"slurm-{JOB_ID}.out").write_text(
        "\n".join(lines) + "\n", encoding="utf-8")


def _write_manifest(evidence_dir, *, include_self=False, omit=None, wrong=None):
    names = [
        *(f"bench_{scale}_threads_{threads}.json"
          for scale in ("sub", "full") for threads in (1, 2, 3, 4)),
        f"slurm-{JOB_ID}.out",
        f"slurm-{JOB_ID}.err",
        "job_metadata.txt",
    ]
    if omit is not None:
        names.remove(omit)
    if include_self:
        names.append("PROVENANCE.sha256")
    lines = []
    for name in names:
        digest = _sha256(evidence_dir / name) if name != "PROVENANCE.sha256" else "0" * 64
        if name == wrong:
            digest = "f" * 64
        lines.append(f"{digest}  {name}")
    (evidence_dir / "PROVENANCE.sha256").write_text(
        "\n".join(lines) + "\n", encoding="utf-8")


def _refresh(evidence_dir):
    _write_stdout(evidence_dir)
    _write_manifest(evidence_dir)


def _valid_evidence(tmp_path):
    evidence_dir = tmp_path / "d19_a7_timing"
    evidence_dir.mkdir()
    for scale in ("sub", "full"):
        for threads in (1, 2, 3, 4):
            _write_record(_json_path(evidence_dir, scale, threads), _record(scale, threads))
    (evidence_dir / f"slurm-{JOB_ID}.err").write_text("", encoding="utf-8")
    (evidence_dir / "job_metadata.txt").write_text(
        "JobID|State|ExitCode|Elapsed|Timelimit|TotalCPU|MaxRSS|NodeList|Submit|Start|End|\n"
        f"{JOB_ID}|COMPLETED|0:0|00:00:00|02:00:00|00:00:00|0K|della-r3c2n7|"
        "2026-07-21T07:59:00|2026-07-21T08:00:00|2026-07-21T08:00:00|\n",
        encoding="utf-8",
    )
    _refresh(evidence_dir)
    return evidence_dir


def _run(evidence_dir):
    return validator.run([
        "--evidence-dir", str(evidence_dir),
        "--expected-sha", EXPECTED_SHA,
    ])


def _mutate_json(evidence_dir, mutator, scale="sub", threads=1):
    path = _json_path(evidence_dir, scale, threads)
    record = json.loads(path.read_text(encoding="utf-8"))
    mutator(record)
    _write_record(path, record)
    _refresh(evidence_dir)


def test_ps1_correction_literal_once_between_strict_mode_and_module_purge():
    text = SCRIPT_PATH.read_text(encoding="utf-8")
    lines = text.splitlines()
    # Line-exact: a commented-out or suffixed variant must not satisfy this.
    assert lines.count(PS1_CORRECTION) == 1
    assert all(line == PS1_CORRECTION for line in lines if PS1_CORRECTION in line)
    assert (
        lines.index("set -euo pipefail")
        < lines.index(PS1_CORRECTION)
        < lines.index("module purge")
    )


def test_ps1_repro_with_correction_survives_fake_modulefile_tail(tmp_path):
    driver, tail = _write_ps1_repro_driver(tmp_path, "before")
    assert tail.read_text(encoding="utf-8").splitlines()[-1] == (
        'export _LOCAL_OLD_PS1="${PS1}"'
    )
    result = _run_ps1_repro(driver)
    assert result.returncode == 0, result.stderr
    assert "REPRO-OK" in result.stdout


@pytest.mark.parametrize("correction_placement", ("absent", "after"))
def test_ps1_repro_without_or_late_correction_dies_under_nounset(
    tmp_path, correction_placement
):
    driver, tail = _write_ps1_repro_driver(tmp_path, correction_placement)
    result = _run_ps1_repro(driver)
    assert result.returncode != 0
    assert "PS1: unbound variable" in result.stderr
    assert "REPRO-OK" not in result.stdout


def _set_option_args(text):
    """Yield every +/- option argument of every `set` command in the script."""
    for line in text.splitlines():
        tokens = line.split()
        for i, token in enumerate(tokens):
            if token != "set":
                continue
            for arg in tokens[i + 1:]:
                if arg.startswith(("+", "-")):
                    yield arg
                else:
                    break


def test_nounset_stays_enabled_and_never_relaxed():
    text = SCRIPT_PATH.read_text(encoding="utf-8")
    assert "set -euo pipefail" in text
    assert re.search(r"set\s+\+[a-z]*u", text) is None
    assert "set +o" not in text
    # Token-level guard: split clusters such as `set +e +u` or `set -e +u`
    # match neither regex above but still disable nounset.
    for arg in _set_option_args(text):
        assert not (arg.startswith("+") and "u" in arg), arg
        assert arg != "+o", arg


def test_every_live_attempt3_binding_uses_the_attempt3_worktree():
    text = SCRIPT_PATH.read_text(encoding="utf-8")
    assert f"--chdir={ATTEMPT3_EXEC_ROOT}" in text
    assert f"EXEC_ROOT={ATTEMPT3_EXEC_ROOT}" in text
    # ATTEMPT1 is a substring of every _0N path, so counting it equals counting
    # _03 only when no bare attempt-1 or attempt-2 path leaked into the script.
    assert text.count(ATTEMPT1_EXEC_ROOT) == text.count(ATTEMPT3_EXEC_ROOT)
    assert ATTEMPT2_EXEC_ROOT not in text

    protocol = PROTOCOL_PATH.read_text(encoding="utf-8")
    assert f"worktree add --detach {ATTEMPT3_EXEC_ROOT} " in protocol
    assert f"{ATTEMPT3_EXEC_ROOT}/runs/d19_a7_timing" in protocol
    # Live prose bindings: the P2 collision target and the P3 change-directory
    # target must name the attempt-3 worktree, not a preserved earlier one.
    assert f"STOP if `{ATTEMPT3_EXEC_ROOT}` exists" in protocol
    assert f"Change to the execution worktree `{ATTEMPT3_EXEC_ROOT}`" in protocol


def test_spent_worktrees_survive_only_as_history_and_are_never_live_targets():
    text = PROTOCOL_PATH.read_text(encoding="utf-8")
    # bare attempt-1 = the root NOT followed by an _0N suffix; attempt-2 = _02.
    bare_attempt1 = re.compile(re.escape(ATTEMPT1_EXEC_ROOT) + r"(?!_0)")
    attempt2 = re.compile(re.escape(ATTEMPT2_EXEC_ROOT) + r"(?!\d)")
    fenced_blocks = text.split("```")[1::2]
    assert fenced_blocks
    # No fenced command block may name either spent worktree as a live target.
    assert all(bare_attempt1.search(block) is None for block in fenced_blocks)
    assert all(attempt2.search(block) is None for block in fenced_blocks)
    # Both spent worktrees still appear (as history/preservation prose).
    assert bare_attempt1.search(text) is not None
    assert attempt2.search(text) is not None
    assert "never remove" in text.lower()
    # Every spent-worktree occurrence must carry history/preservation context on
    # its line, so a live directive can never quietly re-target a spent worktree.
    history_markers = ("preserved", "attempt-1", "attempt-2", "attempt 2", "spent")
    for line in text.splitlines():
        if bare_attempt1.search(line) or attempt2.search(line):
            lowered = line.lower()
            assert any(marker in lowered for marker in history_markers), line


def test_attempt1_failure_evidence_blobs_remain_byte_identical():
    assert sorted(path.name for path in FAILED_ATTEMPT_DIR.iterdir()) == sorted(
        FAILED_ATTEMPT_PINS
    )
    for name, (expected_digest, expected_size) in FAILED_ATTEMPT_PINS.items():
        data = (FAILED_ATTEMPT_DIR / name).read_bytes()
        assert len(data) == expected_size
        assert hashlib.sha256(data).hexdigest() == expected_digest


def test_single_submission_stop_only_semantics_preserved():
    protocol = PROTOCOL_PATH.read_text(encoding="utf-8")
    script = SCRIPT_PATH.read_text(encoding="utf-8")
    submit_command = "sbatch --export=NONE experiments/submit_d19_a7_bench.slurm"
    assert protocol.count(submit_command) == 1
    # Exactly two `sbatch` mentions may exist: the §2 `man sbatch` recon fact
    # and the single P5 command. Any added submission instruction trips this.
    assert protocol.count("sbatch") == 2
    assert "P5 — Submit once." in protocol
    assert "no retry" in protocol
    assert (
        "There is no retry, completion invocation, or continuation without a "
        "new explicit author authorization."
    ) in protocol
    assert "no retry, no continuation" in script
    assert "fresh byte-exact" in protocol


def test_protocol_document_records_the_d56b_amendment():
    text = PROTOCOL_PATH.read_text(encoding="utf-8")
    for literal in (
        "D56b",
        "M56b",
        "7d234e9ffad6b154e7523507658a6999e7bb6c53",
        PS1_CORRECTION,
        ATTEMPT2_EXEC_ROOT,
        # The launch-closure rule's load-bearing members, pinned so that
        # deleting an item while keeping the headline tokens cannot pass.
        "git diff B..M56b -- experiments/submit_d19_a7_bench.slurm "
        "tests/test_d19_a7_protocol.py docs/d19-a7-execution-protocol.md",
        "git diff H'..M56b -- experiments/d19_a7_validate.py "
        "experiments/d19_bench.py bistar_gp/",
        "second parent is the D56b PR head",
        "fresh byte-exact author authorization naming `M56b`",
        "Notes-only and explicitly identified in the launch authorization",
    ):
        assert literal in text


ENV_MANIFEST_PATH = Path("docs/d19_a7_freeze/bistar_env_after.txt")
ENV_MANIFEST_SHA256 = "d832d426ec5a83e3f1da3275c289323c8732f2644038efb15b2eb1567b085aa1"
ENV_MANIFEST_SIZE = 1386
ENV_MANIFEST_LINES = 69
PREREG_PATH = Path("docs/prereg-addenda-d19.md")
D56C_REVIEWED_SURFACE_CLOSURE = (
    "git diff R56c..M56c -- experiments/submit_d19_a7_bench.slurm "
    "tests/test_d19_a7_protocol.py docs/d19-a7-execution-protocol.md "
    "docs/prereg-addenda-d19.md docs/d19_a7_freeze/bistar_env_after.txt"
)


def test_committed_env_manifest_is_pinned():
    data = ENV_MANIFEST_PATH.read_bytes()
    assert len(data) == ENV_MANIFEST_SIZE
    assert hashlib.sha256(data).hexdigest() == ENV_MANIFEST_SHA256
    # pip list --format=freeze terminates every line, so newline count == lines.
    assert data.decode("utf-8").count("\n") == ENV_MANIFEST_LINES


def test_protocol_document_records_the_d56c_amendment():
    text = PROTOCOL_PATH.read_text(encoding="utf-8")
    for literal in (
        "D56c",
        "R56c",
        "M56c",
        ATTEMPT3_EXEC_ROOT,
        "d9c924fc35cc771775732cb431014a25de8a6400",
        "docs/d19_a7_freeze/bistar_env_after.txt",
        "environment re-freeze",
        "v1.23",
        # Preparation-time enforcement must require BOTH checks; omitting either
        # the exact-inventory equality or the import check trips one of these.
        "exact byte-for-byte equality between the live",
        "successful `import bistar_gp` under the five pinned versions",
        "trust interval",
        # The five-file reviewed-surface closure command, pinned verbatim so no
        # closure member (script, tests, protocol, prereg, manifest) can drop.
        D56C_REVIEWED_SURFACE_CLOSURE,
    ):
        assert literal in text
    # F1: the preparation gate must be a conjunction (require BOTH (a) AND (b)),
    # never a disjunction. Rewriting BOTH->EITHER or "and (b)"->"or (b)" drops one
    # of these literals, so the test fails on any weakening of the binding intent.
    assert "must require **BOTH**" in text
    assert "and (b) a successful `import bistar_gp`" in text


def test_prereg_records_the_v122_env_refreeze():
    text = PREREG_PATH.read_text(encoding="utf-8")
    # F2: positively guard the prereg authority — the v1.22 addendum must exist,
    # bind the committed manifest by path AND full sha256, and state the
    # reassignment of the successful measured-results addendum to v1.23.
    # Relabeling or removing any of these (protocol untouched) now fails a test.
    for literal in (
        "## v1.22",
        "docs/d19_a7_freeze/bistar_env_after.txt",
        ENV_MANIFEST_SHA256,
        "is reassigned to this environment re-freeze",
        "measured-results addendum becomes **v1.23**",
    ):
        assert literal in text


def test_submit_script_pins_the_complete_execution_contract():
    text = SCRIPT_PATH.read_text(encoding="utf-8")
    directives = tuple(line for line in text.splitlines() if line.startswith("#SBATCH "))
    assert directives == EXPECTED_SBATCH_LINES
    assert re.search(r"--mail", text, re.IGNORECASE) is None
    assert "set -euo pipefail" in text
    assert '[[ "$EXEC_SHA" =~ ^[0-9a-f]{40}$ ]]' in text
    for literal in EXPECTED_ENV_LITERALS:
        assert literal in text
    assert '"intel,cascade,rh9"' in text
    assert "--budget-s 600" in text
    assert "for scale in sub full; do" in text
    assert "for t in 1 2 3 4; do" in text
    assert "MATRIX-STOP: cell ($scale,$t) rc=$rc; no retry, no continuation" in text
    assert "sha256sum runs/d19_a7_timing/bench_*.json" in text
    assert text.index("UT_RAW=$(git status") < text.index("for scale in sub full")
    assert "|| rc=$?" in text
    assert '[ "$rc" -eq 0 ]' in text
    assert "git diff --quiet" in text
    assert "git diff --cached --quiet" in text
    assert text.count("python -B") >= 2
    assert "HOOK_SCRIPT=$(conda shell.bash hook) || fail 68" in text
    assert 'eval "$HOOK_SCRIPT" || fail 68' in text
    assert "--untracked-files=normal" in text
    for name in (
        "sitecustomize.py", "sitecustomize.pyc",
        "usercustomize.py", "usercustomize.pyc",
    ):
        assert name in text


def test_submit_script_never_owns_thread_variables_or_optimized_assertions():
    text = SCRIPT_PATH.read_text(encoding="utf-8")
    assignment = re.compile(
        r"(?m)^\s*(?:export\s+)?(?:OMP_NUM_THREADS|MKL_NUM_THREADS|"
        r"OPENBLAS_NUM_THREADS|VECLIB_MAXIMUM_THREADS)\s*="
    )
    assert assignment.search(text) is None
    heredoc = text.split("<<'PYEOF'", 1)[1].split("\nPYEOF", 1)[0]
    assert re.search(r"\bassert\s+", heredoc) is None
    assert "mod_path.parents" in heredoc
    assert "startswith(" not in heredoc
    ceiling_line = next(line for line in text.splitlines() if "16G and 02:00:00" in line)
    assert "CEILINGS" in ceiling_line


@pytest.mark.parametrize("text", (
    "conditional",
    "conditionally",
    "unconditional",
    REAL_SPECTRE_V2_LINE,
))
def test_condition_scan_allows_only_the_conditional_family(text):
    assert CONDITION_FINDING not in validator._scan_forbidden_text(text)


@pytest.mark.parametrize("text", (
    "condition",
    "condition number",
    "condition_number",
    "condition-number",
    "conditioned",
    "conditioning",
    "preconditioned",
    "reconditioning",
    "conditions",
    "conditioner",
))
def test_condition_scan_rejects_every_nonconditional_form(text):
    assert CONDITION_FINDING in validator._scan_forbidden_text(text)


def test_other_forbidden_scan_semantics_are_unchanged():
    assert (
        "substring 'hyperparam'"
        in validator._scan_forbidden_text("prehyperparameterpost")
    )
    whole_word_finding = "whole-word token 'ess'"
    assert whole_word_finding in validator._scan_forbidden_text("ess")
    assert whole_word_finding not in validator._scan_forbidden_text("hessian")


def test_valid_synthetic_evidence_passes(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(
        validator, "_dependency_blob_mismatches",
        lambda expected_sha, validator_sha: [],
    )
    evidence_dir = _valid_evidence(tmp_path)
    assert _run(evidence_dir) == 0
    output = capsys.readouterr().out
    for number in range(0, 16):
        assert f"V{number}" in output
    assert "FAIL" not in output


def test_real_conditional_lscpu_line_passes_v5_and_v11(
    tmp_path, capsys, monkeypatch
):
    monkeypatch.setattr(
        validator, "_dependency_blob_mismatches",
        lambda expected_sha, validator_sha: [],
    )
    evidence_dir = _valid_evidence(tmp_path)
    _write_stdout(evidence_dir, extra_lines=(REAL_SPECTRE_V2_LINE,))
    _write_manifest(evidence_dir)
    assert _run(evidence_dir) == 0
    output = capsys.readouterr().out
    assert "V5 forbidden scans: PASS" in output
    assert "V11 log discipline: PASS" in output


def test_condition_number_log_line_fails_v5_and_v11(
    tmp_path, capsys, monkeypatch
):
    monkeypatch.setattr(
        validator, "_dependency_blob_mismatches",
        lambda expected_sha, validator_sha: [],
    )
    evidence_dir = _valid_evidence(tmp_path)
    _write_stdout(evidence_dir, extra_lines=("condition number",))
    _write_manifest(evidence_dir)
    assert _run(evidence_dir) == 1
    output = capsys.readouterr().out
    assert "V5 forbidden scans: FAIL" in output
    assert "V11 log discipline: FAIL" in output


def _mutation_torch(evidence_dir):
    _mutate_json(evidence_dir, lambda record: record["environment"].__setitem__("torch", "drifted"))


def _mutation_sha(evidence_dir):
    _mutate_json(evidence_dir, lambda record: record["environment"].__setitem__("git_sha", "b" * 40))


def _mutation_hostname(evidence_dir):
    _mutate_json(evidence_dir, lambda record: record["environment"].__setitem__("hostname", "della-h12n18"))


def _mutation_missing_json(evidence_dir):
    _json_path(evidence_dir).unlink()


def _mutation_extra_file(evidence_dir):
    (evidence_dir / "extra.txt").write_text("extra\n", encoding="utf-8")


def _mutation_dotfile(evidence_dir):
    (evidence_dir / ".bench_full_threads_1.json.tmp").write_text("stranded\n", encoding="utf-8")


def _mutation_forbidden_log(evidence_dir):
    out_path = evidence_dir / f"slurm-{JOB_ID}.out"
    out_path.write_text(out_path.read_text(encoding="utf-8") + "ess_bulk\n", encoding="utf-8")
    _write_manifest(evidence_dir)


def _mutation_wrong_manifest_hash(evidence_dir):
    _write_manifest(evidence_dir, wrong="bench_sub_threads_1.json")


def _mutation_missing_manifest_file(evidence_dir):
    _write_manifest(evidence_dir, omit="bench_sub_threads_1.json")


def _mutation_manifest_self_entry(evidence_dir):
    _write_manifest(evidence_dir, include_self=True)


def _mutation_timeout(evidence_dir):
    path = evidence_dir / "job_metadata.txt"
    path.write_text(path.read_text(encoding="utf-8").replace("|COMPLETED|", "|TIMEOUT|"), encoding="utf-8")
    _write_manifest(evidence_dir)


def _mutation_budget(evidence_dir):
    _mutate_json(evidence_dir, lambda record: record["run_config"].__setitem__("budget_s", 240.0))


def _mutation_threads(evidence_dir):
    _mutate_json(evidence_dir, lambda record: record["threads"].__setitem__("threads_requested", 2))


def _mutation_in_job_hash(evidence_dir):
    _write_stdout(evidence_dir, overrides={"bench_sub_threads_1.json": "f" * 64})
    _write_manifest(evidence_dir)


def _mutation_duplicate_json_key(evidence_dir):
    path = _json_path(evidence_dir)
    record = json.loads(path.read_text(encoding="utf-8"))
    duplicate = json.dumps(record["record"], sort_keys=True)
    raw = path.read_text(encoding="utf-8").replace(
        "{", f'{{"record": {duplicate}, ', 1
    )
    path.write_text(raw, encoding="utf-8")
    _refresh(evidence_dir)


def _mutation_nan_literal(evidence_dir):
    path = _json_path(evidence_dir)
    raw = path.read_text(encoding="utf-8").replace(
        '"cpu_count": 4', '"cpu_count": NaN', 1
    )
    path.write_text(raw, encoding="utf-8")
    _refresh(evidence_dir)


def _mutation_timestamp_outside_window(evidence_dir):
    _mutate_json(
        evidence_dir,
        lambda record: record["environment"].__setitem__(
            "timestamp", "2026-07-21T20:00:00+00:00"
        ),
    )


def _mutation_sacct_node_mismatch(evidence_dir):
    path = evidence_dir / "job_metadata.txt"
    path.write_text(
        path.read_text(encoding="utf-8").replace("della-r3c2n7", "della-r3c1n9"),
        encoding="utf-8",
    )
    _write_manifest(evidence_dir)


def _mutation_sacct_exit_code(evidence_dir):
    path = evidence_dir / "job_metadata.txt"
    path.write_text(
        path.read_text(encoding="utf-8").replace("|0:0|", "|0:1|"),
        encoding="utf-8",
    )
    _write_manifest(evidence_dir)


def _mutation_sacct_elapsed(evidence_dir):
    path = evidence_dir / "job_metadata.txt"
    path.write_text(
        path.read_text(encoding="utf-8").replace("|00:00:00|02:00:00|", "|03:00:00|02:00:00|"),
        encoding="utf-8",
    )
    _write_manifest(evidence_dir)


def _mutation_report_n_points(evidence_dir):
    path = evidence_dir / f"slurm-{JOB_ID}.out"
    path.write_text(
        path.read_text(encoding="utf-8").replace('"n_points":150', '"n_points":151', 1),
        encoding="utf-8",
    )
    _write_manifest(evidence_dir)


def _mutation_stderr_stop_marker(evidence_dir):
    path = evidence_dir / f"slurm-{JOB_ID}.err"
    path.write_text("MATRIX-STOP: x\n", encoding="utf-8")
    _write_manifest(evidence_dir)


@pytest.mark.parametrize("mutation", (
    _mutation_torch,
    _mutation_sha,
    _mutation_hostname,
    _mutation_missing_json,
    _mutation_extra_file,
    _mutation_dotfile,
    _mutation_forbidden_log,
    _mutation_wrong_manifest_hash,
    _mutation_missing_manifest_file,
    _mutation_manifest_self_entry,
    _mutation_timeout,
    _mutation_budget,
    _mutation_threads,
    _mutation_in_job_hash,
    _mutation_duplicate_json_key,
    _mutation_nan_literal,
    _mutation_timestamp_outside_window,
    _mutation_sacct_node_mismatch,
    _mutation_sacct_exit_code,
    _mutation_sacct_elapsed,
    _mutation_report_n_points,
    _mutation_stderr_stop_marker,
), ids=(
    "torch-version-drift",
    "git-sha-mismatch",
    "hostname-outside-pool",
    "bench-json-missing",
    "extra-file",
    "stranded-dotfile",
    "forbidden-log-token",
    "wrong-provenance-hash",
    "missing-provenance-entry",
    "provenance-self-entry",
    "sacct-timeout",
    "wrong-budget",
    "thread-filename-disagreement",
    "in-job-hash-disagreement",
    "duplicate-json-key",
    "nan-json-literal",
    "artifact-timestamp-outside-window",
    "sacct-node-mismatch",
    "sacct-nonzero-step-exit",
    "sacct-elapsed-over-ceiling",
    "report-n-points-mismatch",
    "stderr-stop-marker",
))
def test_single_evidence_mutations_fail_closed(tmp_path, mutation, monkeypatch):
    monkeypatch.setattr(
        validator, "_dependency_blob_mismatches",
        lambda expected_sha, validator_sha: [],
    )
    evidence_dir = _valid_evidence(tmp_path)
    mutation(evidence_dir)
    assert _run(evidence_dir) == 1


def test_truthful_budget_statuses_pass_and_are_censused(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(
        validator, "_dependency_blob_mismatches",
        lambda expected_sha, validator_sha: [],
    )
    evidence_dir = _valid_evidence(tmp_path)
    path = _json_path(evidence_dir)
    _write_record(
        path,
        _record(
            "sub",
            1,
            hessian_status="skipped_for_budget",
            stage2_status="extrapolated_from_stage1",
        ),
    )
    _refresh(evidence_dir)
    assert _run(evidence_dir) == 0
    output = capsys.readouterr().out
    assert (
        "CENSUS bench_sub_threads_1.json: "
        "hessian=skipped_for_budget stage2=extrapolated_from_stage1"
    ) in output


def test_v0_failure_makes_otherwise_valid_evidence_fail(tmp_path, monkeypatch):
    monkeypatch.setattr(
        validator,
        "_dependency_blob_mismatches",
        lambda expected_sha, validator_sha: ["validation dependency differs"],
    )
    evidence_dir = _valid_evidence(tmp_path)
    assert _run(evidence_dir) == 1


def test_dependency_blob_helper_fails_for_missing_expected_sha():
    assert validator._dependency_blob_mismatches("f" * 40, "f" * 40)


def test_v0_consults_dependency_blob_helper(monkeypatch):
    observed = []

    def fake(expected_sha, validator_sha):
        observed.append((expected_sha, validator_sha))
        return ["sentinel"]

    monkeypatch.setattr(validator, "_dependency_blob_mismatches", fake)
    validator_sha = "b" * 40
    assert validator._v0({
        "expected_sha": EXPECTED_SHA,
        "validator_sha": validator_sha,
    }) == ["sentinel"]
    assert observed == [(EXPECTED_SHA, validator_sha)]


@pytest.mark.parametrize("malformed", (
    "not-40-hex",
    "A" * 40,
    "",
), ids=("non-40-hex", "uppercase", "empty"))
def test_malformed_validator_sha_matches_expected_sha_argument_failure(
    tmp_path, capsys, malformed
):
    assert validator.run([
        "--evidence-dir", str(tmp_path),
        "--expected-sha", malformed,
    ]) == 1
    expected_output = capsys.readouterr().out

    assert validator.run([
        "--evidence-dir", str(tmp_path),
        "--expected-sha", EXPECTED_SHA,
        "--validator-sha", malformed,
    ]) == 1
    validator_output = capsys.readouterr().out
    assert validator_output == expected_output.replace(
        "--expected-sha", "--validator-sha")


def test_omitted_validator_sha_defaults_both_v0_bindings(tmp_path, monkeypatch):
    observed = []

    def fake(expected_sha, validator_sha):
        observed.append((expected_sha, validator_sha))
        return []

    monkeypatch.setattr(validator, "_dependency_blob_mismatches", fake)
    evidence_dir = _valid_evidence(tmp_path)
    assert _run(evidence_dir) == 0
    assert observed == [(EXPECTED_SHA, EXPECTED_SHA)]


@pytest.mark.parametrize(
    ("vehicle_live_blob", "validator_live_blob", "mismatch_path"),
    (
        ("3" * 40, "2" * 40, "experiments/d19_bench.py"),
        ("1" * 40, "4" * 40, "experiments/d19_a7_validate.py"),
    ),
    ids=("vehicle-only-mismatch", "validator-only-mismatch"),
)
def test_v0_dependency_blobs_use_independent_sha_bindings(
    monkeypatch, vehicle_live_blob, validator_live_blob, mismatch_path
):
    expected_sha = "a" * 40
    validator_sha = "b" * 40
    vehicle_path = "experiments/d19_bench.py"
    validator_path = "experiments/d19_a7_validate.py"
    expected_blobs = {
        f"{expected_sha}:{vehicle_path}": "1" * 40,
        f"{validator_sha}:{validator_path}": "2" * 40,
    }
    live_blobs = {
        vehicle_path: vehicle_live_blob,
        validator_path: validator_live_blob,
    }
    observed_commands = []

    def fake_run(command, **kwargs):
        observed_commands.append(command)
        if "rev-parse" in command:
            blob = expected_blobs[command[-1]]
        else:
            relpath = Path(command[-1]).relative_to(
                validator.REPO_ROOT).as_posix()
            blob = live_blobs[relpath]
        return subprocess.CompletedProcess(
            command, 0, stdout=f"{blob}\n", stderr="")

    monkeypatch.setattr(validator.subprocess, "run", fake_run)
    reasons = validator._v0({
        "expected_sha": expected_sha,
        "validator_sha": validator_sha,
    })
    assert len(reasons) == 1
    assert reasons[0].startswith(f"{mismatch_path}: live blob ")
    expected_specs = {
        command[-1] for command in observed_commands if "rev-parse" in command
    }
    assert expected_specs == set(expected_blobs)


def test_ambiguous_dst_fall_back_time_fails_closed():
    with pytest.raises(ValueError, match="ambiguous local cluster time"):
        validator._parse_local_cluster_time(
            "2026-11-01T01:30:00", validator.ZoneInfo("America/New_York")
        )


def test_v4_detects_both_missing_and_extra_paths():
    records = {
        filename: _record(scale, threads)
        for filename, (scale, threads) in zip(validator.BENCH_FILES, validator.CELL_ORDER)
    }
    changed = records["bench_sub_threads_1.json"]
    del changed["record"]["kind"]
    changed["record"]["unreviewed"] = "extra"
    reasons = validator._v4({"records": records})
    assert any("missing paths" in reason and "record.kind" in reason for reason in reasons)
    assert any("extra paths" in reason and "record.unreviewed" in reason for reason in reasons)


def test_v6_detects_negative_total_seconds():
    records = {
        filename: _record(scale, threads)
        for filename, (scale, threads) in zip(validator.BENCH_FILES, validator.CELL_ORDER)
    }
    records["bench_sub_threads_1.json"]["timings"]["map_fit"]["total_s"] = -0.1
    reasons = validator._v6({"records": records})
    assert any("timings.map_fit.total_s" in reason for reason in reasons)


def test_v15_rejects_wrong_monkeypatched_anchor_hash(monkeypatch):
    monkeypatch.setattr(
        validator,
        "ANCHORS",
        {"bench_sub.json": ("0" * 64, 3663)},
    )
    assert validator._v15({})


def test_frozen_node_pool_expands_to_exact_membership():
    nodes = validator.expand_node_pool()
    assert len(nodes) == 90
    assert "della-r3c2n7" in nodes
    assert "della-h17n2" in nodes
    assert "della-h12n18" not in nodes
    assert "della-h16n1" not in nodes
    assert "della-i13n25" not in nodes


def test_validator_source_has_no_assert_and_only_stdlib_imports():
    tree = ast.parse(VALIDATOR_PATH.read_text(encoding="utf-8"))
    assert not any(isinstance(node, ast.Assert) for node in ast.walk(tree))
    allowed = {
        "argparse", "hashlib", "importlib", "json", "math", "re", "sys",
        "subprocess", "datetime", "pathlib", "zoneinfo",
    }
    imported = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add((node.module or "").split(".")[0])
    assert imported <= allowed
    assert not ({"torch", "numpy", "gpytorch", "pyro", "bistar_gp"} & imported)


def test_validator_key_inventory_is_transcription_independent():
    source = VALIDATOR_PATH.read_text(encoding="utf-8")
    assert "EXPECTED_KEY_PATHS = frozenset((" in source
    assert "_VEHICLE.SCHEMA" not in source
    assert ".SCHEMA" not in source


def test_protocol_document_pins_authority_transport_and_topology():
    text = PROTOCOL_PATH.read_text(encoding="utf-8")
    for number in range(1, 12):
        assert f"AC{number}" in text
    assert (
        "della-h12n[1-13],della-h12n[17-18],della-h17n1,della-i13n25"
    ) in text
    for spec in EXPECTED_POOL_SPECS:
        assert spec in text
    for line in text.splitlines():
        if any(token in line for token in ("600", "02:00:00", "16G")):
            assert "ceiling" in line.lower()
    assert re.search(r"expected actual", text, re.IGNORECASE) is None
    assert re.search(r"\d+\s*[-–]\s*\d+\s*min", text, re.IGNORECASE) is None
    lowered = text.lower()
    for term in ("in-job", "provenance.sha256", "local"):
        assert term in lowered
    assert "dotfile" in lowered
    assert "worktree collision" in lowered and "stop" in lowered
    assert "staging destination must not exist" in lowered
    assert "git add -f" in text
    assert "git ls-files" in text
    assert (
        "git diff H'..M56 -- experiments/ bistar_gp/ tests/ "
        "docs/d19-a7-execution-protocol.md"
    ) in text


def test_expected_literals_are_not_imported_from_production_modules():
    source = TEST_PATH.read_text(encoding="utf-8")
    prefix = source.split("def _load_validator", 1)[0]
    imported = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
    assert not any(name.endswith("d19_a7_validate") for name in imported)
    assert not any(name.endswith("d19_bench") for name in imported)
    for name in (
        "EXPECTED_SBATCH_LINES",
        "EXPECTED_ENV_LITERALS",
        "EXPECTED_POOL_SPECS",
        "EXPECTED_FIREWALL_NOTE",
        "EXPECTED_THREAD_SCOPE_NOTE",
        "EXPECTED_DESIGN_LABEL",
        "EXPECTED_CANONICAL_SHA256",
        "EXPECTED_VERSIONS",
    ):
        block = prefix.split(f"{name} =", 1)[1]
        block = block.split("\n\n", 1)[0]
        assert "validator." not in block
