"""
Experiment run manager for reproducible, organized BMS* experiments.

Creates a structured directory per run:

  runs/
    mauna_loa_sub150_hmc_20260215_1430/
      config.json          # all args + git hash + environment
      command.sh           # exact command to reproduce
      samples/
        hmc_samples.npz    # raw HMC posterior samples
        gp_predictives.npz # extracted GP predictives (ψ's)
      results/
        *.png              # all plots
        bms_tables.txt     # printed BMS* tables
      data/
        train.npz          # exact training data used (for reproducibility)

Supports:
  - Automatic timestamped naming or custom run names
  - Saving/loading HMC samples from a specific run
  - Reusing samples from a previous run (--load-run)
  - Listing past runs with metadata
"""

import os
import json
import subprocess
import numpy as np
from datetime import datetime
from typing import Dict, Optional, List


# ── Default base directory ────────────────────────────────────────

RUNS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "runs")


def _git_hash():
    """Get current git commit hash, or 'unknown'."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def _git_dirty():
    """Check if working tree has uncommitted changes."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, timeout=5,
        )
        return len(result.stdout.strip()) > 0
    except Exception:
        return None


# ── Run directory management ──────────────────────────────────────

def make_run_name(experiment: str, mode: str, tag: Optional[str] = None) -> str:
    """
    Generate a run name like: mauna_loa_sub150_hmc_20260215_1430

    Args:
        experiment: e.g. "mauna_loa", "toy"
        mode: e.g. "hmc", "map"
        tag: optional extra tag, e.g. "sub150", "full", "prior_vague"
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    parts = [experiment]
    if tag:
        parts.append(tag)
    parts.append(mode)
    parts.append(timestamp)
    return "_".join(parts)


def create_run_dir(run_name: str, base_dir: str = None) -> str:
    """Create run directory with subdirectories. Returns run_dir path."""
    base = base_dir or RUNS_DIR
    run_dir = os.path.join(base, run_name)
    os.makedirs(os.path.join(run_dir, "samples"), exist_ok=True)
    os.makedirs(os.path.join(run_dir, "results"), exist_ok=True)
    os.makedirs(os.path.join(run_dir, "data"), exist_ok=True)
    return run_dir


def find_run_dir(run_name: str, base_dir: str = None) -> Optional[str]:
    """Find an existing run directory by name (exact or prefix match)."""
    base = base_dir or RUNS_DIR
    if not os.path.exists(base):
        return None

    # Exact match
    exact = os.path.join(base, run_name)
    if os.path.isdir(exact):
        return exact

    # Prefix match (e.g. "mauna_loa_sub150" matches "mauna_loa_sub150_hmc_20260215_1430")
    candidates = sorted([
        d for d in os.listdir(base)
        if d.startswith(run_name) and os.path.isdir(os.path.join(base, d))
    ])
    if len(candidates) == 1:
        return os.path.join(base, candidates[0])
    elif len(candidates) > 1:
        # Return most recent
        return os.path.join(base, candidates[-1])

    return None


# ── Config save/load ──────────────────────────────────────────────

def save_run_config(run_dir: str, args, extra: dict = None):
    """
    Save full experiment configuration for reproducibility.

    Args:
        run_dir: path to run directory
        args: argparse Namespace
        extra: additional metadata (e.g. data stats, GP hyperparameters)
    """
    config = {
        "timestamp": datetime.now().isoformat(),
        "git_hash": _git_hash(),
        "git_dirty": _git_dirty(),
        "args": vars(args) if hasattr(args, "__dict__") else dict(args),
    }
    if extra:
        config["extra"] = extra

    path = os.path.join(run_dir, "config.json")
    with open(path, "w") as f:
        json.dump(config, f, indent=2, default=str)
    print(f"  Config saved → {path}")


def save_command(run_dir: str, argv: list = None):
    """Save the exact command used to launch this run."""
    import sys
    cmd = argv or sys.argv
    path = os.path.join(run_dir, "command.sh")
    with open(path, "w") as f:
        f.write("#!/bin/bash\n")
        f.write(f"# Reproduce this run\n")
        f.write(f"# Generated: {datetime.now().isoformat()}\n")
        f.write(f"cd {os.getcwd()}\n")
        f.write(f"python {' '.join(cmd)}\n")
    print(f"  Command saved → {path}")


def load_run_config(run_dir: str) -> dict:
    """Load config from a previous run."""
    path = os.path.join(run_dir, "config.json")
    with open(path) as f:
        return json.load(f)


# ── Sample save/load ──────────────────────────────────────────────

def save_samples(run_dir: str, hmc_samples: Dict[str, np.ndarray]):
    """Save HMC samples to run directory."""
    path = os.path.join(run_dir, "samples", "hmc_samples.npz")
    np.savez(path, **{k: np.array(v) for k, v in hmc_samples.items()})
    print(f"  HMC samples saved → {path}")
    return path


def load_samples(run_dir: str) -> Dict[str, np.ndarray]:
    """Load HMC samples from a previous run."""
    path = os.path.join(run_dir, "samples", "hmc_samples.npz")
    if not os.path.exists(path):
        raise FileNotFoundError(f"No samples found at {path}")
    data = np.load(path)
    samples = {k: data[k] for k in data.files}
    print(f"  HMC samples loaded ← {path}")
    return samples


def save_gp_predictives(run_dir: str, gp_samples: list):
    """Save extracted GP predictives for reuse in model comparison."""
    means = np.array([s.mean for s in gp_samples])
    covs = np.array([s.cov for s in gp_samples])
    # Save hyperparameters as a list of dicts
    hp_keys = list(gp_samples[0].hyperparameters.keys()) if gp_samples else []
    hp_vals = np.array([[s.hyperparameters.get(k, np.nan) for k in hp_keys]
                        for s in gp_samples])

    path = os.path.join(run_dir, "samples", "gp_predictives.npz")
    np.savez(path, means=means, covs=covs, hp_keys=hp_keys, hp_vals=hp_vals)
    print(f"  GP predictives saved → {path} ({len(gp_samples)} samples)")
    return path


def load_gp_predictives(run_dir: str):
    """Load GP predictives from a previous run."""
    from bistar_gp.bms_star import GPPosteriorSample

    path = os.path.join(run_dir, "samples", "gp_predictives.npz")
    if not os.path.exists(path):
        raise FileNotFoundError(f"No GP predictives found at {path}")

    data = np.load(path, allow_pickle=True)
    means = data["means"]
    covs = data["covs"]
    hp_keys = list(data["hp_keys"])
    hp_vals = data["hp_vals"]

    samples = []
    for i in range(len(means)):
        hp_dict = {k: float(v) for k, v in zip(hp_keys, hp_vals[i])}
        samples.append(GPPosteriorSample(mean=means[i], cov=covs[i],
                                          hyperparameters=hp_dict))

    print(f"  GP predictives loaded ← {path} ({len(samples)} samples)")
    return samples


def save_training_data(run_dir: str, x_train, y_train, info: dict = None):
    """Save exact training data used for this run."""
    path = os.path.join(run_dir, "data", "train.npz")
    save_dict = {"x_train": np.asarray(x_train), "y_train": np.asarray(y_train)}
    if info:
        for k, v in info.items():
            try:
                save_dict[f"info_{k}"] = np.array(v)
            except (ValueError, TypeError):
                pass  # skip non-array-able metadata
    np.savez(path, **save_dict)
    print(f"  Training data saved → {path}")


def save_bms_tables(run_dir: str, text: str):
    """Save printed BMS* tables to a text file."""
    path = os.path.join(run_dir, "results", "bms_tables.txt")
    with open(path, "w") as f:
        f.write(text)


# ── Listing runs ──────────────────────────────────────────────────

def list_runs(base_dir: str = None, experiment_filter: str = None) -> List[dict]:
    """
    List all past runs with their metadata.

    Returns list of dicts with: name, timestamp, args summary.
    """
    base = base_dir or RUNS_DIR
    if not os.path.exists(base):
        return []

    runs = []
    for name in sorted(os.listdir(base)):
        run_dir = os.path.join(base, name)
        if not os.path.isdir(run_dir):
            continue
        if experiment_filter and not name.startswith(experiment_filter):
            continue

        info = {"name": name, "path": run_dir}

        # Try to load config
        config_path = os.path.join(run_dir, "config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path) as f:
                    config = json.load(f)
                info["timestamp"] = config.get("timestamp", "?")
                info["git_hash"] = config.get("git_hash", "?")
                args = config.get("args", {})
                info["mode"] = args.get("mode", "?")
                info["subsample"] = args.get("subsample", None)
                info["n_hmc"] = args.get("n_hmc", None)
            except Exception:
                pass

        # Check what artifacts exist
        info["has_samples"] = os.path.exists(
            os.path.join(run_dir, "samples", "hmc_samples.npz"))
        info["has_gp_pred"] = os.path.exists(
            os.path.join(run_dir, "samples", "gp_predictives.npz"))
        info["n_plots"] = len([
            f for f in os.listdir(os.path.join(run_dir, "results"))
            if f.endswith(".png")
        ]) if os.path.exists(os.path.join(run_dir, "results")) else 0

        runs.append(info)

    return runs


def print_runs(base_dir: str = None, experiment_filter: str = None):
    """Pretty-print all past runs."""
    runs = list_runs(base_dir, experiment_filter)
    if not runs:
        print("  No runs found.")
        return

    print(f"\n  {'Name':<45} {'Mode':<6} {'Sub':<6} {'HMC':<6} {'Samples':<8} {'Plots':<6}")
    print(f"  {'─'*45} {'─'*6} {'─'*6} {'─'*6} {'─'*8} {'─'*6}")
    for r in runs:
        sub = str(r.get("subsample", "—")) if r.get("subsample") else "—"
        hmc = str(r.get("n_hmc", "—")) if r.get("n_hmc") else "—"
        samp = "✓" if r.get("has_samples") else "—"
        pred = "✓" if r.get("has_gp_pred") else "—"
        print(f"  {r['name']:<45} {r.get('mode','?'):<6} {sub:<6} {hmc:<6} "
              f"{samp:<8} {r.get('n_plots',0):<6}")
