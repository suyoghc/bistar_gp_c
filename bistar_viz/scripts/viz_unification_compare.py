"""
Rerunnable legacy-vs-ported comparison harness (plan-viz-unification §5).

Extracts the LEGACY self-contained scripts from the pinned pre-port commit
(git show — replace-in-place cannot orphan this comparison), patches their
hardcoded /home/claude output dirs, runs them headless, runs the ported
scripts across an attribution LADDER of configurations, parses every arm's
printed priors into one delta table, and overlays the four Z_Mx estimators
(legacy hybrid / IS / Laplace / MC) on the τ-sweep (plan §4).

Attribution ladder for the priors script (each adjacent gap isolates ONE
change): legacy → ported laplace+occam (averaged-GP estimator change) →
ported is+occam (Z estimator change) → ported canonical is+no-occam (occam
convention). For the trajectory script (legacy occam OFF already): legacy →
ported legacy-spaces+perturbed-starts (averaged-GP + Z estimator) →
canonical (bounds convention).

Usage: python viz_unification_compare.py [--out-dir runs/viz_unification]
           [--quick]
"""

import argparse
import os
import re
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

# Last commit containing the self-contained legacy scripts (D16).
LEGACY_COMMIT = "a87356a"
LEGACY_SCRIPTS = ["model_priors_laplace.py", "model_prior_trajectory_laplace.py"]
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MODEL_NAMES = ["Linear", "Sinusoidal", "Sin+Linear", "Quadratic"]


def extract_legacy(out_dir):
    legacy_dir = os.path.join(out_dir, "legacy_scripts")
    os.makedirs(legacy_dir, exist_ok=True)
    for name in LEGACY_SCRIPTS:
        src = subprocess.run(
            ["git", "show", f"{LEGACY_COMMIT}:bistar_viz/scripts/{name}"],
            capture_output=True, text=True, check=True, cwd=REPO_ROOT).stdout
        # separate figure dirs: both legacy scripts save an identically named
        # model_prior_flow_laplace.png (codex finding — second run would
        # overwrite the first)
        fig_dir = os.path.join(out_dir, "legacy_figures",
                               name.replace(".py", ""))
        os.makedirs(fig_dir, exist_ok=True)
        assert 'out_dir = "/home/claude/model_prior_plots"' in src, \
            f"pinned legacy {name} lost its expected out_dir line"
        src = src.replace('out_dir = "/home/claude/model_prior_plots"',
                          f'out_dir = "{fig_dir}"')
        with open(os.path.join(legacy_dir, name), "w") as f:
            f.write(src)
    return legacy_dir


def run(cmd, cwd, log_path):
    with open(log_path, "w") as log:
        subprocess.run(cmd, cwd=cwd, stdout=log, stderr=subprocess.STDOUT,
                       check=True)


def parse_priors(log_path, tag):
    """Both print formats:
    - single-line sweep/stage rows: 'n= 10: Linear=13.3%  ...' (legacy sweep
      at n_hyper=150; ported scripts throughout at n_draws default 150)
    - the legacy priors script's stage BLOCKS (n_hyper=200):
      'n = 10:' followed by four '<model>: p(M|psi) = 77.9%' lines
    Distinct suffixes keep the two legacy resolutions apart (codex finding:
    the old parser silently captured only the sweep rows)."""
    rows = {}
    block_n = None
    block = {}
    with open(log_path) as f:
        for line in f:
            m = re.match(r"\s*n\s*=\s*(\d+)\s*:\s*$", line)
            if m:
                block_n, block = int(m.group(1)), {}
                continue
            if block_n is not None:
                bm = re.match(r"\s*(\S[^:]*?)\s*:\s*p\(M.*?=\s*([\d.]+)%", line)
                if bm and bm.group(1) in MODEL_NAMES:
                    block[bm.group(1)] = float(bm.group(2)) / 100
                    if len(block) == len(MODEL_NAMES):
                        rows[f"{tag}/stage_n={block_n}"] = [
                            block[m] for m in MODEL_NAMES]
                        block_n = None
                    continue
                block_n = None
            sm = re.match(r"\s*n\s*=\s*(\d+)\s*:\s+(.*%)", line)
            if sm and "=" in sm.group(2):
                probs = [float(x) / 100
                         for x in re.findall(r"=\s*([\d.]+)%", sm.group(2))]
                if len(probs) == len(MODEL_NAMES):
                    rows[f"{tag}/n={int(sm.group(1))}"] = probs
    return rows


def tau_overlay(out_dir, legacy_dir, quick):
    """Plan §4: legacy hybrid vs IS vs Laplace vs MC on the τ-sweep, per
    model, on the SAME averaged GP (the legacy script's own, at n=50)."""
    import importlib.util
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from types import SimpleNamespace

    spec = importlib.util.spec_from_file_location(
        "legacy_traj", os.path.join(legacy_dir,
                                    "model_prior_trajectory_laplace.py"))
    leg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(leg)

    import _viz_spaces as V
    from bistar_gp.laplace_evidence import (laplace_log_Z_Mx, mc_log_Z_Mx,
                                            is_log_Z_Mx)

    x_eval = np.linspace(-10, 10, 80)
    x50, y50 = leg.generate_data(50, seed=42)
    rng = np.random.RandomState(42)
    gp_mean, gp_var = leg.compute_avg_gp(x_eval, x50, y50, leg.INFORMATIVE,
                                         n_hyp=150, rng=rng, use_data=True)
    avg_gp = SimpleNamespace(mean=gp_mean, cov=np.diag(gp_var))
    spaces = V.trajectory_legacy_spaces()   # the legacy script's own boxes
    taus = np.logspace(-1.5, 2.5, 12 if quick else 30)
    n_samp = 20_000 if quick else 60_000

    fig, axes = plt.subplots(1, len(MODEL_NAMES), figsize=(22, 5),
                             sharex=True)
    for ax, name in zip(axes, MODEL_NAMES):
        ps, st = spaces[name], V.STARTS[name]
        mspec = leg.MODELS[name]
        G_pre = leg.precompute_G_samples(mspec, gp_mean, gp_var, x_eval,
                                         n_mc=n_samp)
        hyb = [leg.compute_Z_hybrid(mspec, gp_mean, gp_var, x_eval, t,
                                    G_precomputed=G_pre) for t in taus]
        lap = [laplace_log_Z_Mx(ps, x_eval, avg_gp, tau=t, starts=st).log_Z
               for t in taus]
        # legacy hybrid/Laplace omit -log V (trajectory convention): occam=False
        iss = is_log_Z_Mx(ps, x_eval, avg_gp, taus, n_is=n_samp, seed=0,
                          starts=st).log_Z
        mc = mc_log_Z_Mx(ps, x_eval, avg_gp, taus, n_mc=n_samp, seed=0).log_Z
        # the legacy MC estimate is occam-normalized (mean over the box);
        # shift to the raw convention for a like-for-like overlay
        log_V = float(sum(np.log(b[1] - b[0]) for b in mspec["bounds"]))
        hyb = np.array(hyb) + log_V
        ax.plot(taus, iss, "-", lw=2.5, color="#2c3e50", label="IS (reference)")
        ax.plot(taus, hyb, "--", lw=2, color="#e67e22", label="legacy hybrid")
        ax.plot(taus, lap, ":", lw=2, color="#c0392b", label="Laplace")
        ax.plot(taus, mc, "-.", lw=2, color="#16a085", label="MC")
        ax.set_xscale("log")
        ax.set_title(name, fontsize=12, fontweight="bold")
        ax.set_xlabel("τ")
        ax.grid(True, alpha=0.2)
    axes[0].set_ylabel("log Z_Mx (raw Lebesgue convention)")
    axes[0].legend(fontsize=9)
    fig.suptitle("Z_Mx estimators on the legacy averaged GP (n=50, legacy "
                 "spaces): the legacy hybrid's Laplace half inherits the "
                 "high-τ blow-up; IS is seam-free", fontsize=12,
                 fontweight="bold", y=1.04)
    fig.tight_layout()
    path = os.path.join(out_dir, "tau_estimator_overlay.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"tau overlay -> {path}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out-dir",
                   default=os.path.join(REPO_ROOT, "runs", "viz_unification"))
    p.add_argument("--quick", action="store_true")
    args = p.parse_args()
    out_dir = os.path.abspath(args.out_dir)
    os.makedirs(out_dir, exist_ok=True)
    scripts_dir = os.path.dirname(os.path.abspath(__file__))

    legacy_dir = extract_legacy(out_dir)
    print(f"legacy scripts extracted from {LEGACY_COMMIT} -> {legacy_dir}")

    for name in LEGACY_SCRIPTS:
        log = os.path.join(out_dir, f"legacy_{name}.log")
        print(f"running legacy {name} ...")
        run([sys.executable, os.path.join(legacy_dir, name)], REPO_ROOT, log)

    quick = ["--quick"] if args.quick else []
    ported_runs = [
        # priors attribution ladder (adjacent gaps isolate one change each):
        (["model_priors_laplace.py", "--estimator", "laplace", "--occam",
          "--out-dir", os.path.join(out_dir, "p1_priors_lap_occam")] + quick,
         "p1_priors_lap_occam"),
        (["model_priors_laplace.py", "--estimator", "is", "--occam",
          "--out-dir", os.path.join(out_dir, "p2_priors_is_occam")] + quick,
         "p2_priors_is_occam"),
        (["model_priors_laplace.py",
          "--out-dir", os.path.join(out_dir, "p3_priors_canonical")] + quick,
         "p3_priors_canonical"),
        # trajectory ladder:
        (["model_prior_trajectory_laplace.py", "--legacy-spaces",
          "--n-perturb", "20",
          "--out-dir", os.path.join(out_dir, "t1_traj_legacyconv")] + quick,
         "t1_traj_legacyconv"),
        (["model_prior_trajectory_laplace.py",
          "--out-dir", os.path.join(out_dir, "t2_traj_canonical")] + quick,
         "t2_traj_canonical"),
    ]
    results = {}
    for cmd, tag in ported_runs:
        log = os.path.join(out_dir, f"{tag}.log")
        print(f"running {tag} ...")
        run([sys.executable] + cmd, scripts_dir, log)
        results.update(parse_priors(log, tag))
    for name, tag in zip(LEGACY_SCRIPTS, ("legacy_priors", "legacy_traj")):
        results.update(parse_priors(
            os.path.join(out_dir, f"legacy_{name}.log"), tag))

    table = os.path.join(out_dir, "delta_table.md")
    with open(table, "w") as f:
        f.write("# viz unification: per-stage model priors, all arms\n\n")
        f.write("Priors ladder: legacy (LML-weighted prior-IS averaged GP, "
                "pure Laplace, occam ON; stage_n rows at n_hyper=200, sweep "
                "rows at 150) vs p1 (averaged-GP estimator change) vs p2 "
                "(Z estimator change) vs p3 (occam convention). Trajectory "
                "ladder: legacy vs t1 (averaged-GP + Z estimator, same "
                "spaces/starts convention) vs t2 (bounds convention).\n\n")
        f.write("| run/stage | " + " | ".join(MODEL_NAMES) + " |\n")
        f.write("|---|" + "---|" * len(MODEL_NAMES) + "\n")
        for k, v in results.items():
            f.write(f"| {k} | " + " | ".join(f"{x:.3f}" for x in v) + " |\n")
    print(f"delta table -> {table}")

    tau_overlay(out_dir, legacy_dir, args.quick)


if __name__ == "__main__":
    main()
