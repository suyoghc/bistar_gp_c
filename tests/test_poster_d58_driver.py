"""D58 poster-driver guards (docs/d58-poster-execution-protocol.md; PREP).

Hermetic by construction: synthetic tensors and tmp directories only — no
real Mauna load, no network, no fit, no figure rendering. What is proven:

  * source-level seal guard on the driver AND its Slurm script (training-only
    loader present; full-loader call and holdout-array tokens absent) — the
    test_mauna_provenance.py pattern extended to the D58 surfaces;
  * the prediction grid ends exactly at the final training coordinate;
  * the output-directory guard admits only fresh run directories strictly
    inside runs/poster_d58/ (no namespace root, no runs/d19_*, no outside
    path, no clobber of anything existing);
  * the four-variable thread contract fails closed on conflicts and on
    too-late application;
  * the render gate refuses an incomplete census, a malformed manifest, and a
    hash mismatch, and accepts a manifest the driver itself wrote;
  * module import is hermetic (no heavy imports at import time), so the
    Slurm-argparse guard and these tests can load the driver safely;
  * the P1a specification is byte-pinned in both the argparse defaults and
    the committed Slurm invocation, with the firewall label transcribed
    independently.
"""

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
DRIVER_PATH = REPO_ROOT / "experiments" / "poster_d58_mauna.py"
SLURM_PATH = REPO_ROOT / "experiments" / "submit_d58_poster_fit.slurm"

FORBIDDEN_TOKENS = ("x_" + "test", "y_" + "test", "load_mauna_loa(")


def _load_driver():
    spec = importlib.util.spec_from_file_location("_d58_driver_under_test",
                                                  DRIVER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


driver = _load_driver()


# ── source-level seal guard (plan §6.6; author boundary ruling 2026-07-23) ──

def test_driver_stays_on_the_training_only_loader():
    text = DRIVER_PATH.read_text()
    assert "load_mauna_loa_training" in text, (
        "driver must consume the §6.6 training-only loader")
    for forbidden in FORBIDDEN_TOKENS:
        assert forbidden not in text, (
            f"driver references {forbidden!r}; sealed holdout values and the "
            "full loader must not appear in D58 poster code (§6.6)")


def test_slurm_script_carries_no_holdout_token():
    text = SLURM_PATH.read_text()
    for forbidden in FORBIDDEN_TOKENS:
        assert forbidden not in text, (
            f"Slurm script references {forbidden!r} (§6.6)")


def test_driver_asserts_the_period_freeze_twice():
    text = DRIVER_PATH.read_text()
    assert text.count("assert_mauna_period_frozen(") >= 2, (
        "A10: the driver must assert the frozen period after build AND after "
        "the fit")


def test_firewall_label_transcribed():
    # Independently transcribed phrases (the D55 FIREWALL_NOTE lesson): a
    # revert of the poster-only firewall label must fail here.
    text = DRIVER_PATH.read_text()
    assert "non-paper-grade" in text
    assert "docs/d58-poster-execution-protocol.md" in text
    assert "feeds no D19 gate" in text


# ── training-span grid (boundary = final training coordinate) ───────────────

def test_grid_spans_training_span_exactly():
    torch = pytest.importorskip("torch")
    x = torch.linspace(-2.31, 4.77, 37, dtype=torch.float64)
    grid = driver.training_span_grid(x, 500)
    assert len(grid) == 500
    assert grid[0].item() == x.min().item()
    assert grid[-1].item() == x.max().item()
    assert bool((grid[1:] >= grid[:-1]).all())


def test_grid_refuses_degenerate_span():
    torch = pytest.importorskip("torch")
    x = torch.full((5,), 1.25, dtype=torch.float64)
    with pytest.raises(SystemExit, match="GRID-DEGENERATE"):
        driver.training_span_grid(x, 10)


# ── output-directory guard (unique namespace, fail-closed, no-clobber) ──────

def test_output_dir_accepts_fresh_run_dir(tmp_path):
    target = driver.resolve_output_dir("runs/poster_d58/fit_x",
                                       repo_root=str(tmp_path))
    assert Path(target).is_dir()
    assert Path(target) == (tmp_path / "runs" / "poster_d58" / "fit_x").resolve()


@pytest.mark.parametrize("raw", [
    "runs/poster_d58",                # the namespace root itself
    "runs/d19_a7_timing/fit_x",       # a D19 evidence namespace
    "runs/figures_regen/fit_x",       # outside the D58 namespace
    "experiments/results_bms_mauna_loa",  # tracked-artifact directory
    "elsewhere/fit_x",                # outside runs/ entirely
])
def test_output_dir_refuses_foreign_namespaces(tmp_path, raw):
    with pytest.raises(SystemExit, match="OUTPUT-DIR-NAMESPACE"):
        driver.resolve_output_dir(raw, repo_root=str(tmp_path))


def test_output_dir_refuses_absolute_escape(tmp_path):
    outside = tmp_path.parent / "d58_escape"
    with pytest.raises(SystemExit, match="OUTPUT-DIR-NAMESPACE"):
        driver.resolve_output_dir(str(outside), repo_root=str(tmp_path))


def test_output_dir_requires_a_value(tmp_path):
    with pytest.raises(SystemExit, match="OUTPUT-DIR-MISSING"):
        driver.resolve_output_dir("", repo_root=str(tmp_path))


def test_output_dir_never_clobbers(tmp_path):
    existing = tmp_path / "runs" / "poster_d58" / "fit_x"
    existing.mkdir(parents=True)
    with pytest.raises(SystemExit, match="OUTPUT-DIR-NO-CLOBBER"):
        driver.resolve_output_dir("runs/poster_d58/fit_x",
                                  repo_root=str(tmp_path))
    (existing / "provenance.json").write_text("{}")
    with pytest.raises(SystemExit, match="OUTPUT-DIR-NO-CLOBBER"):
        driver.resolve_output_dir("runs/poster_d58/fit_x",
                                  repo_root=str(tmp_path))


# ── thread contract (v1.23 §6 pin; driver-owned, pre-import) ─────────────────

def test_thread_pin_sets_all_four_variables():
    env = {}
    applied = driver.apply_thread_pin(environ=env, loaded_modules={})
    assert applied == {var: "3" for var in driver.THREAD_VARS}
    assert env == applied


def test_thread_pin_accepts_matching_preset():
    env = {"OMP_NUM_THREADS": "3"}
    driver.apply_thread_pin(environ=env, loaded_modules={})
    assert all(env[var] == "3" for var in driver.THREAD_VARS)


def test_thread_pin_fails_closed_on_conflict():
    env = {"MKL_NUM_THREADS": "4"}
    with pytest.raises(SystemExit, match="THREAD-PIN-CONFLICT"):
        driver.apply_thread_pin(environ=env, loaded_modules={})


@pytest.mark.parametrize("mod", ["numpy", "torch", "bistar_gp"])
def test_thread_pin_fails_closed_when_applied_late(mod):
    with pytest.raises(SystemExit, match="THREAD-PIN-LATE"):
        driver.apply_thread_pin(environ={}, loaded_modules={mod: object()})


# ── render gate (census + manifest hash gate) ────────────────────────────────

def _make_payload(run_dir):
    run_dir.mkdir(parents=True)
    for name in driver.EXPECTED_ARTIFACTS:
        if name == driver.MANIFEST_NAME:
            continue
        (run_dir / name).write_text(f"payload of {name}\n")


def test_render_gate_accepts_a_driver_written_manifest(tmp_path):
    run_dir = tmp_path / "fit_x"
    _make_payload(run_dir)
    driver.write_manifest(str(run_dir))
    assert driver.verify_run_dir(str(run_dir)) is True


def test_render_gate_refuses_incomplete_census(tmp_path):
    run_dir = tmp_path / "fit_x"
    _make_payload(run_dir)
    driver.write_manifest(str(run_dir))
    (run_dir / "samples.npz").unlink()
    with pytest.raises(SystemExit, match="RENDER-CENSUS"):
        driver.verify_run_dir(str(run_dir))


def test_render_gate_refuses_hash_mismatch(tmp_path):
    run_dir = tmp_path / "fit_x"
    _make_payload(run_dir)
    driver.write_manifest(str(run_dir))
    (run_dir / "samples.npz").write_text("tampered\n")
    with pytest.raises(SystemExit, match="RENDER-HASH-GATE"):
        driver.verify_run_dir(str(run_dir))


def test_render_gate_refuses_malformed_manifest(tmp_path):
    run_dir = tmp_path / "fit_x"
    _make_payload(run_dir)
    (run_dir / driver.MANIFEST_NAME).write_text("not a manifest line\n")
    with pytest.raises(SystemExit, match="RENDER-MANIFEST"):
        driver.verify_run_dir(str(run_dir))


# ── hermetic import + frozen census ──────────────────────────────────────────

def test_module_import_is_hermetic():
    code = (
        "import importlib.util, sys\n"
        f"spec = importlib.util.spec_from_file_location('m', {str(DRIVER_PATH)!r})\n"
        "mod = importlib.util.module_from_spec(spec)\n"
        "spec.loader.exec_module(mod)\n"
        "heavy = [m for m in ('numpy', 'torch', 'gpytorch', 'pyro', 'bistar_gp')\n"
        "         if m in sys.modules]\n"
        "assert not heavy, f'heavy imports at module import: {heavy}'\n"
        "assert len(mod.EXPECTED_ARTIFACTS) == 6\n"
        "print('HERMETIC-OK')\n"
    )
    proc = subprocess.run([sys.executable, "-B", "-c", code],
                          capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, proc.stderr
    assert "HERMETIC-OK" in proc.stdout


def test_expected_census_is_frozen():
    assert driver.EXPECTED_ARTIFACTS == (
        "fit_config.json", "samples.npz", "diagnostics.json",
        "decomposition.npz", "provenance.json", "PROVENANCE.sha256")
    assert driver.FIGURE_NAMES == (
        "card6_mauna_decomposition.png", "card7_three_interpretations.png",
        "card8_debiased_ppm.png", "card8_removed_bias.png")
    assert driver.OUTPUT_NAMESPACE.replace("\\", "/") == "runs/poster_d58"


# ── P1a specification byte-pins (argparse defaults + Slurm invocation) ───────

def test_argparse_defaults_pin_the_p1_specification():
    args = driver.build_parser().parse_args(
        ["--mode", "fit", "--output-dir", "runs/poster_d58/fit_x"])
    assert (args.seed, args.n_warmup, args.n_samples,
            args.max_tree_depth, args.n_grid) == (0, 200, 200, 7, 500)


def test_argparse_requires_mode_and_output_dir():
    parser = driver.build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--mode", "fit"])
    with pytest.raises(SystemExit):
        parser.parse_args(["--output-dir", "runs/poster_d58/fit_x"])
    with pytest.raises(SystemExit):
        parser.parse_args(["--mode", "science", "--output-dir", "x"])


def test_slurm_invocation_pins_the_p1_specification():
    text = SLURM_PATH.read_text()
    for token in (
        "#SBATCH --cpus-per-task=3",
        "#SBATCH --mem=8G",
        "#SBATCH --time=02:00:00",
        "#SBATCH --chdir=/scratch/gpfs/SUYOGHC/bistar_gp_d58",
        "#SBATCH --output=runs/poster_d58/slurm-%j.out",
        "#SBATCH --constraint=cascade",
        "#SBATCH --exclude=della-h12n[1-13],della-h12n[17-18],della-h17n1,della-i13n25",
        'export PS1="${PS1-}"',
        "intel,cascade,rh9",
        "sbatch --export=NONE experiments/submit_d58_poster_fit.slurm",
        "FIT_DIR=runs/poster_d58/fit_full461_seed0",
        "--seed 0 --n-warmup 200 --n-samples 200 --max-tree-depth 7 --n-grid 500",
        "no retry",
    ):
        assert token in text, f"Slurm script lost the pinned token {token!r}"


def test_slurm_pins_threads_to_three_nowhere_else():
    # cpus-per-task is the only thread control the script owns (the driver
    # owns the four variables + torch intra-op); no stray export of a thread
    # variable may appear in the script.
    text = SLURM_PATH.read_text()
    for var in driver.THREAD_VARS:
        assert f"export {var}" not in text, (
            f"Slurm script exports {var}; the driver owns the pre-import "
            "thread contract (D55/A7 division of responsibility)")
