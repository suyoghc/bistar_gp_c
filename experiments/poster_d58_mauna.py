"""D58 poster-grade Mauna Loa driver — POSTER-ONLY, NON-PAPER-GRADE.

Governing protocol: docs/d58-poster-execution-protocol.md (D58; author cast
2026-07-23: dispositions B1-B5, ballot P1a/P2a/P3a, PREP authorization).

Firewall: every artifact this driver produces is a poster-grade presentation
artifact. None of it is a paper result, and none of it may feed any D19 gate,
dossier, arm, strategy, BMS* computation, or selection. The preregistered
paper-grade study (docs/plan-d19-mauna.md) reads only its own namespaces and
never this one.

Seal discipline (plan §6.6): data enters exclusively through the training-only
loader, so the sealed 60-month holdout is mechanically unreachable in this
process. The prediction grid is built from the training tensor alone and ends
at the final training coordinate; split counts and the cutoff rule are quoted
from loader metadata only. A source-level guard test additionally forbids the
full-loader call and holdout-array tokens in this file and in the companion
Slurm script.

Thread pin (prereg v1.23 §6): fit mode owns the pre-import contract — it sets
the four thread environment variables to 3 before any heavy import (failing
closed on a conflicting pre-set value), then pins torch intra-op threads to 3
immediately after `import torch`. Torch inter-op threads are observed and
recorded, never set, matching the committed pin's scope. `cpus-per-task=3`
belongs to the companion Slurm script.

Modes:
  --mode fit     (Della, one shot): training-only load, seeded E1-backed NUTS
                 via the committed `fit_hmc`, component decomposition on the
                 training-span grid, six-artifact census written atomically in
                 recovery-friendly order (config, samples, diagnostics,
                 decomposition, provenance, manifest).
  --mode render  (local, D58-POST): verifies the census against its manifest,
                 rebuilds the decomposition result from arrays, and renders the
                 poster panels into <run>/figures/. Performs no data load and
                 no inference. It loads the tracked plotting module
                 experiments/bistar_debias_mauna_loa.py for its figure
                 functions; that module binds (but render never calls) the
                 full loader.

Determinism note: the decomposition subsamples draws with an unseeded RNG, so
this driver requires n_posterior_samples == retained draws (the full set),
which makes the selection RNG-independent. The protocol freezes that equality.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

THREAD_PIN = "3"
THREAD_VARS = (
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
)
HEAVY_MODULES = ("numpy", "torch", "gpytorch", "pyro", "bistar_gp")

OUTPUT_NAMESPACE = os.path.join("runs", "poster_d58")

# Closed-world artifact census for one fit run (write order = recovery order;
# the manifest is always last and covers the five payload files).
EXPECTED_ARTIFACTS = (
    "fit_config.json",
    "samples.npz",
    "diagnostics.json",
    "decomposition.npz",
    "provenance.json",
    "PROVENANCE.sha256",
)
MANIFEST_NAME = "PROVENANCE.sha256"
FIGURES_DIR_NAME = "figures"

FIGURE_NAMES = (
    "card6_mauna_decomposition.png",
    "card7_three_interpretations.png",
    "card8_debiased_ppm.png",
    "card8_removed_bias.png",
)

DESIGN_LABEL = (
    "D58 poster-grade Mauna fit: poster-only presentation artifact; "
    "non-paper-grade; feeds no D19 gate, dossier, arm, strategy, BMS*, or "
    "selection (docs/d58-poster-execution-protocol.md)"
)


# ── fail-closed guards (pure; unit-tested hermetically) ─────────────────────

def apply_thread_pin(environ=None, loaded_modules=None):
    """Set the four v1.23 §6 thread variables to 3 before heavy imports.

    Fails closed if any variable is pre-set to a conflicting value (an
    operator's explicit different intent is never silently overridden) or if a
    heavy module is already imported (the pin would be too late to bind BLAS
    pools deterministically).
    """
    environ = os.environ if environ is None else environ
    loaded_modules = sys.modules if loaded_modules is None else loaded_modules
    for mod in HEAVY_MODULES:
        if mod in loaded_modules:
            raise SystemExit(
                f"THREAD-PIN-LATE: {mod} already imported; the pre-import "
                "thread contract cannot be applied (v1.23 section 6)")
    for var in THREAD_VARS:
        current = environ.get(var)
        if current is not None and current != THREAD_PIN:
            raise SystemExit(
                f"THREAD-PIN-CONFLICT: {var}={current!r} conflicts with the "
                f"committed pin {THREAD_PIN} (v1.23 section 6); refusing to "
                "override")
        environ[var] = THREAD_PIN
    return {var: environ[var] for var in THREAD_VARS}


def resolve_output_dir(raw, repo_root=REPO_ROOT):
    """Resolve and create the fit output directory, fail-closed.

    The directory must be strictly inside <repo>/runs/poster_d58/ (never the
    namespace root itself, never runs/d19_*, never anywhere else) and must not
    already exist in any form (no-clobber: a spent or partial run is evidence
    and is never overwritten).
    """
    if not raw:
        raise SystemExit("OUTPUT-DIR-MISSING: --output-dir is required")
    candidate = raw if os.path.isabs(raw) else os.path.join(repo_root, raw)
    candidate = os.path.realpath(candidate)
    namespace = os.path.realpath(os.path.join(repo_root, OUTPUT_NAMESPACE))
    if candidate == namespace:
        raise SystemExit(
            "OUTPUT-DIR-NAMESPACE: --output-dir must be a run directory "
            f"inside {OUTPUT_NAMESPACE}/, not the namespace root")
    if os.path.commonpath([candidate, namespace]) != namespace:
        raise SystemExit(
            f"OUTPUT-DIR-NAMESPACE: {raw!r} resolves outside the unique D58 "
            f"namespace {OUTPUT_NAMESPACE}/ (protocol section 4); refusing")
    if os.path.lexists(candidate):
        raise SystemExit(
            f"OUTPUT-DIR-NO-CLOBBER: {candidate} already exists; a prior run "
            "is evidence and is never overwritten (one-shot discipline)")
    os.makedirs(os.path.dirname(candidate), exist_ok=True)
    os.makedirs(candidate, exist_ok=False)
    return candidate


def training_span_grid(x_train, n_grid):
    """Prediction grid over the training span only: [min, max] of x_train.

    Nothing in this driver constructs, receives, or plots any coordinate past
    the final training point (plan §6.6; author boundary ruling 2026-07-23).
    """
    import torch

    lo = x_train.min().item()
    hi = x_train.max().item()
    if not (hi > lo):
        raise SystemExit("GRID-DEGENERATE: training span is empty")
    return torch.linspace(lo, hi, int(n_grid), dtype=torch.float64)


def _json_default(obj):
    """Strict JSON fallback: numpy scalars/arrays and tuples only."""
    import numpy as np

    if isinstance(obj, np.generic):
        return obj.item()
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, tuple):
        return list(obj)
    raise TypeError(f"not JSON-serializable: {type(obj)!r}")


def _atomic_write_text(path, text):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(text)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def atomic_savez(path, arrays):
    """np.savez with the same tmp + fsync + os.replace discipline as the JSON
    writers (a kill can never leave a partial file under the final name).
    Writing through an open file object stops np.savez from appending its own
    .npz suffix to the temporary name."""
    import numpy as np

    tmp = path + ".tmp"
    with open(tmp, "wb") as fh:
        np.savez(fh, **arrays)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def divergence_total(divergence_draws):
    """Total post-warmup divergences across chains; None when unobserved."""
    if divergence_draws is None:
        return None
    return int(sum(len(chain) for chain in divergence_draws))


def td_saturated_count(leapfrog_counts, threshold):
    """Post-warmup draws whose leapfrog count reaches the depth-cap bound
    (2**max_tree_depth - 1); None when the sampler cannot observe it."""
    if leapfrog_counts is None:
        return None
    return int(sum(1 for chain in leapfrog_counts
                   for count in chain if count >= threshold))


def _write_json(path, payload):
    _atomic_write_text(path, json.dumps(payload, indent=2, sort_keys=True,
                                        default=_json_default) + "\n")


def _sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_manifest(run_dir):
    """shasum -c compatible manifest over the five payload files, written last."""
    lines = []
    for name in EXPECTED_ARTIFACTS:
        if name == MANIFEST_NAME:
            continue
        lines.append(f"{_sha256_file(os.path.join(run_dir, name))}  {name}")
    _atomic_write_text(os.path.join(run_dir, MANIFEST_NAME),
                       "\n".join(lines) + "\n")


def verify_run_dir(run_dir):
    """Render-mode gate: closed-world census and manifest hash agreement.

    The run directory must contain exactly the six census artifacts (plus, on
    a re-render only, the REAL (non-symlink) figures/ directory a previous
    render created); anything else fails closed. The manifest must hold exactly
    one valid line per payload file, duplicates rejected, every hash matching.
    """
    allowed = set(EXPECTED_ARTIFACTS)
    entries_on_disk = set(os.listdir(run_dir))
    extra = entries_on_disk - allowed - {FIGURES_DIR_NAME}
    if extra:
        raise SystemExit(
            f"RENDER-CENSUS: unexpected entries {sorted(extra)} in {run_dir}; "
            "the census is closed-world (protocol section 4)")
    figures_path = os.path.join(run_dir, FIGURES_DIR_NAME)
    if (FIGURES_DIR_NAME in entries_on_disk
            and not (os.path.isdir(figures_path)
                     and not os.path.islink(figures_path))):
        raise SystemExit(
            f"RENDER-CENSUS: {FIGURES_DIR_NAME} has a type problem in "
            f"{run_dir}; the one permitted extra must be a REAL "
            "(non-symlink) directory (protocol section 4)")
    for name in EXPECTED_ARTIFACTS:
        path = os.path.join(run_dir, name)
        if not (os.path.isfile(path) and os.path.getsize(path) > 0):
            raise SystemExit(
                f"RENDER-CENSUS: {name} missing or empty in {run_dir}; the "
                "six-artifact census is incomplete (protocol section 4)")
    manifest_path = os.path.join(run_dir, MANIFEST_NAME)
    with open(manifest_path, "r", encoding="utf-8") as fh:
        entries = [ln.rstrip("\n") for ln in fh if ln.strip()]
    expected_payload = [n for n in EXPECTED_ARTIFACTS if n != MANIFEST_NAME]
    if len(entries) != len(expected_payload):
        raise SystemExit(
            f"RENDER-MANIFEST: {len(entries)} lines != "
            f"{len(expected_payload)} expected payload files")
    seen = {}
    for entry in entries:
        try:
            sha, name = entry.split("  ", 1)
        except ValueError:
            raise SystemExit(f"RENDER-MANIFEST: malformed line {entry!r}")
        if len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha):
            raise SystemExit(f"RENDER-MANIFEST: malformed sha256 in {entry!r}")
        if name in seen:
            raise SystemExit(f"RENDER-MANIFEST: duplicate name {name!r}")
        seen[name] = sha
    if sorted(seen) != sorted(expected_payload):
        raise SystemExit(
            f"RENDER-MANIFEST: names {sorted(seen)} != {sorted(expected_payload)}")
    for name, recorded in seen.items():
        actual = _sha256_file(os.path.join(run_dir, name))
        if actual != recorded:
            raise SystemExit(
                f"RENDER-HASH-GATE: {name} sha256 {actual} != recorded "
                f"{recorded}; refusing to render from a tampered or partial run")
    return True


def validate_saved_grid(arrays):
    """Semantic seal check on the transported arrays before any rendering:
    the prediction grid must be finite, nondecreasing, and bounded exactly by
    the training span (author boundary ruling 2026-07-23)."""
    import numpy as np

    grid = arrays["x_pred"]
    x_train = arrays["x_train"]
    if not np.isfinite(grid).all() or not np.isfinite(x_train).all():
        raise SystemExit("RENDER-GRID: non-finite coordinates in the census")
    if not (np.diff(grid) >= 0).all():
        raise SystemExit("RENDER-GRID: prediction grid is not nondecreasing")
    if grid[0] != x_train.min() or grid[-1] != x_train.max():
        raise SystemExit(
            "RENDER-GRID: grid endpoints "
            f"[{grid[0]!r}, {grid[-1]!r}] != training span "
            f"[{x_train.min()!r}, {x_train.max()!r}]; nothing outside the "
            "training span may be rendered (plan section 6.6)")
    return float(grid[0]), float(grid[-1])


_BOUNDARY_ANNOTATIONS = ("forecast →", "← train")


def enforce_training_boundary(fig, lo, hi):
    """Crop every axes of `fig` to exactly [lo, hi] on x (zero margin) and
    strip the tracked plot functions' boundary annotations, so no axis range
    or label suggests anything past the final training coordinate."""
    for ax in fig.get_axes():
        ax.set_xlim(lo, hi)
        for artist in list(ax.texts):
            if artist.get_text().strip() in _BOUNDARY_ANNOTATIONS:
                artist.remove()
    return fig


# ── fit mode (Della, one shot) ───────────────────────────────────────────────

def _git_state(repo_root):
    def _run(*args):
        return subprocess.run(["git", *args], cwd=repo_root, text=True,
                              capture_output=True, check=True).stdout.strip()

    sha = _run("rev-parse", "HEAD")
    dirty = bool(_run("status", "--porcelain", "--untracked-files=no"))
    return sha, dirty


def run_fit(args):
    thread_env = apply_thread_pin()

    import torch

    torch.set_num_threads(int(THREAD_PIN))
    if torch.get_num_threads() != int(THREAD_PIN):
        raise SystemExit(
            f"THREAD-PIN-TORCH: intra-op {torch.get_num_threads()} != "
            f"{THREAD_PIN} after set_num_threads")
    interop_observed = torch.get_num_interop_threads()  # observed, never set
    torch.set_default_dtype(torch.float64)

    import numpy as np
    import gpytorch
    import pyro

    from bistar_gp.data import load_mauna_loa_training
    from bistar_gp.debias import decompose_model_hmc
    from bistar_gp.fit import fit_hmc
    from bistar_gp.model import (
        assert_mauna_period_frozen,
        build_likelihood,
        build_mauna_loa_kernels,
        build_model,
    )

    run_dir = resolve_output_dir(args.output_dir)
    git_sha, git_dirty = _git_state(REPO_ROOT)

    x_train, y_train, info = load_mauna_loa_training(
        normalize=True, test_years=5.0)
    kernels, names = build_mauna_loa_kernels()
    likelihood = build_likelihood()
    model, likelihood = build_model(x_train, y_train, kernels, names,
                                    likelihood)
    assert_mauna_period_frozen(model)

    import platform
    import socket

    config = {
        "design_label": DESIGN_LABEL,
        "driver": "experiments/poster_d58_mauna.py",
        "mode": "fit",
        "git_sha": git_sha,
        "git_dirty_tracked": git_dirty,
        "hostname": socket.gethostname(),
        "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
        "slurm_cpus_per_task": os.environ.get("SLURM_CPUS_PER_TASK"),
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "seed": args.seed,
        "n_warmup": args.n_warmup,
        "n_samples": args.n_samples,
        "max_tree_depth": args.max_tree_depth,
        "target_accept_prob": 0.8,  # committed fit_hmc default, echoed
        "init_to_map": True,        # committed fit_hmc default, echoed
        "n_grid": args.n_grid,
        "n_posterior_samples": args.n_samples,  # full-set determinism rule
        "thread_env": thread_env,
        "torch_intra_op_threads": torch.get_num_threads(),
        "torch_inter_op_threads_observed": interop_observed,
        "versions": {
            "python": platform.python_version(),
            "torch": str(torch.__version__),
            "gpytorch": str(gpytorch.__version__),
            "pyro": str(pyro.__version__),
            "numpy": str(np.__version__),
        },
        "data": dict(info),  # scalars/strings only (loader guarantee)
    }
    _write_json(os.path.join(run_dir, "fit_config.json"), config)

    t_fit = time.monotonic()
    samples, diagnostics = fit_hmc(
        model, likelihood, x_train, y_train,
        n_samples=args.n_samples, n_warmup=args.n_warmup, seed=args.seed,
        max_tree_depth=args.max_tree_depth, return_diagnostics=True)
    fit_elapsed_s = time.monotonic() - t_fit
    assert_mauna_period_frozen(model)

    atomic_savez(os.path.join(run_dir, "samples.npz"), samples)

    from dataclasses import asdict

    diag_payload = asdict(diagnostics)
    saturation_threshold = (2 ** args.max_tree_depth) - 1
    divergences = divergence_total(diagnostics.divergence_draws)
    td_saturated = td_saturated_count(diagnostics.leapfrog_counts,
                                      saturation_threshold)
    samples_finite = {site: bool(np.isfinite(arr).all())
                      for site, arr in samples.items()}
    _write_json(os.path.join(run_dir, "diagnostics.json"), {
        "sampler_diagnostics": diag_payload,
        "derived": {
            "divergence_count_total": divergences,
            "tree_depth_saturation_threshold": saturation_threshold,
            "tree_depth_saturated_draws": td_saturated,
        },
        "samples_finite": samples_finite,
        "fit_elapsed_s": fit_elapsed_s,
    })

    x_pred = training_span_grid(x_train, args.n_grid)
    t_dec = time.monotonic()
    result = decompose_model_hmc(
        model, likelihood, x_train, y_train, x_pred, samples,
        kernel_builder=build_mauna_loa_kernels,
        n_posterior_samples=args.n_samples)
    dec_elapsed_s = time.monotonic() - t_dec

    dec_arrays = {
        "x_pred": x_pred.numpy(),
        "x_train": x_train.numpy(),
        "y_train": y_train.numpy(),
        "full_mean": result.full_mean,
        "full_std": result.full_std,
        "noise_var": np.asarray(result.noise_var),
        "component_names": np.asarray(list(result.components), dtype="U"),
    }
    for name, comp in result.components.items():
        dec_arrays[f"comp__{name}__mean"] = comp.mean
        dec_arrays[f"comp__{name}__std"] = comp.std
        dec_arrays[f"comp__{name}__samples"] = comp.samples
    atomic_savez(os.path.join(run_dir, "decomposition.npz"), dec_arrays)

    first = next(iter(result.components.values()))
    decomposition_n_success = int(first.samples.shape[0])
    dec_finite = all(
        bool(np.isfinite(v).all()) for k, v in dec_arrays.items()
        if k != "component_names")

    provenance = dict(config)
    provenance.update({
        "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "fit_elapsed_s": fit_elapsed_s,
        "decomposition_elapsed_s": dec_elapsed_s,
        "decomposition_n_success": decomposition_n_success,
        "decomposition_n_requested": args.n_samples,
        "samples_all_finite": bool(all(samples_finite.values())),
        "decomposition_all_finite": bool(dec_finite),
        "divergence_count_total": divergences,
        "tree_depth_saturated_draws": td_saturated,
        "artifacts": list(EXPECTED_ARTIFACTS),
    })
    _write_json(os.path.join(run_dir, "provenance.json"), provenance)

    write_manifest(run_dir)
    print(f"FIT-COMPLETE {run_dir} fit={fit_elapsed_s:.1f}s "
          f"decomposition={dec_elapsed_s:.1f}s "
          f"n_success={decomposition_n_success}/{args.n_samples}")
    return run_dir


# ── render mode (local, D58-POST; no data load, no inference) ────────────────

def _load_plot_module():
    """Load the tracked plotting module for its figure functions.

    The module binds the full loader at import time but render mode never
    calls any loader; render consumes committed arrays only.
    """
    import importlib.util

    path = os.path.join(REPO_ROOT, "experiments", "bistar_debias_mauna_loa.py")
    spec = importlib.util.spec_from_file_location("_d58_plot_module", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def rebuild_decomposition_result(arrays):
    """Reconstruct the package's decomposition dataclasses from saved arrays.

    Positional construction, in dataclass field order (prediction grid,
    x_train, y_train, components, full_mean, full_std, noise_var): the first
    field's legacy name refers to prediction locations and is deliberately not
    spelled in this file (source-level seal guard; protocol section 4).
    """
    import numpy as np

    from bistar_gp.debias import ComponentResult, DecompositionResult

    components = {}
    for name in [str(n) for n in arrays["component_names"]]:
        mean = arrays[f"comp__{name}__mean"]
        std = arrays[f"comp__{name}__std"]
        components[name] = ComponentResult(
            name=name, mean=mean, std=std, cov=np.diag(std ** 2),
            samples=arrays[f"comp__{name}__samples"])
    return DecompositionResult(
        arrays["x_pred"],
        arrays["x_train"],
        arrays["y_train"],
        components,
        arrays["full_mean"],
        arrays["full_std"],
        float(arrays["noise_var"]),
    )


def run_render(args):
    run_dir = args.output_dir
    if not os.path.isabs(run_dir):
        run_dir = os.path.join(REPO_ROOT, run_dir)
    run_dir = os.path.realpath(run_dir)
    verify_run_dir(run_dir)

    import matplotlib

    matplotlib.use("Agg")

    import numpy as np

    with np.load(os.path.join(run_dir, "decomposition.npz")) as npz:
        arrays = {k: npz[k] for k in npz.files}
    with open(os.path.join(run_dir, "provenance.json"), encoding="utf-8") as fh:
        provenance = json.load(fh)
    info = {k: provenance["data"][k]
            for k in ("y_mean", "y_std", "x_offset")}

    grid_lo, grid_hi = validate_saved_grid(arrays)
    result = rebuild_decomposition_result(arrays)

    from bistar_gp.viz import plot_mauna_loa_decomposition

    plot_module = _load_plot_module()

    figures_dir = os.path.join(run_dir, FIGURES_DIR_NAME)
    os.makedirs(figures_dir, exist_ok=True)

    # x limits per figure's coordinate system: cards 6-7 plot normalized
    # time; the card-8 strips denormalize to calendar years via x_offset.
    x_offset = float(info["x_offset"])
    produced = []
    renderers = {
        "card6_mauna_decomposition.png":
            (lambda: plot_mauna_loa_decomposition(result), grid_lo, grid_hi),
        "card7_three_interpretations.png":
            (lambda: plot_module.plot_three_interpretations(result),
             grid_lo, grid_hi),
        "card8_debiased_ppm.png":
            (lambda: plot_module.plot_debiased_comparison(result, info),
             grid_lo + x_offset, grid_hi + x_offset),
        "card8_removed_bias.png":
            (lambda: plot_module.plot_residuals_comparison(result, info),
             grid_lo + x_offset, grid_hi + x_offset),
    }
    assert tuple(renderers) == FIGURE_NAMES
    for name, (make, lo, hi) in renderers.items():
        fig = enforce_training_boundary(make(), lo, hi)
        target = os.path.join(figures_dir, name)
        fig.savefig(target, dpi=200, bbox_inches="tight")
        produced.append(target)
        print(f"RENDERED {target}")
    # Figure-provenance manifest, created only now that figures exist
    # (author footprint ruling 2026-07-23); consumed by the D58-POST
    # evidence commit.
    manifest_lines = [
        f"{_sha256_file(os.path.join(figures_dir, name))}  {name}"
        for name in FIGURE_NAMES]
    _atomic_write_text(os.path.join(figures_dir, "FIGURES.sha256"),
                       "\n".join(manifest_lines) + "\n")
    print(f"RENDER-COMPLETE {len(produced)}/{len(FIGURE_NAMES)} figures in "
          f"{figures_dir}")
    return produced


# ── entry point ──────────────────────────────────────────────────────────────

def build_parser():
    parser = argparse.ArgumentParser(
        description="D58 poster-grade Mauna driver (poster-only; "
                    "non-paper-grade; see docs/d58-poster-execution-protocol.md)")
    parser.add_argument("--mode", required=True, choices=("fit", "render"),
                        help="fit: one-shot Della fit; render: local figures "
                             "from a validated run directory")
    parser.add_argument("--output-dir", required=True,
                        help="fit: fresh run directory strictly inside "
                             "runs/poster_d58/ (must not exist); render: a "
                             "transported, hash-validated run directory (for "
                             "the D58-POST flow, under "
                             "runs/poster_d58_incoming/)")
    parser.add_argument("--seed", type=int, default=0,
                        help="fit_hmc seed (P1: 0)")
    parser.add_argument("--n-warmup", type=int, default=200,
                        help="NUTS warmup draws (P1: 200)")
    parser.add_argument("--n-samples", type=int, default=200,
                        help="retained draws; also the decomposition draw "
                             "count, full set for determinism (P1: 200)")
    parser.add_argument("--max-tree-depth", type=int, default=7,
                        help="NUTS depth cap (P1: 7, the td7 efficiency "
                             "control)")
    parser.add_argument("--n-grid", type=int, default=500,
                        help="training-span prediction grid size (P1: 500)")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.mode == "fit":
        return run_fit(args)
    return run_render(args)


if __name__ == "__main__":
    main()
