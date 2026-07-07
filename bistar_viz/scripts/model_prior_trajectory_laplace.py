"""
BI* Model Prior Trajectory — unified onto bistar_gp.laplace_evidence
(docs/plan-viz-unification.md §4; DECISIONS D10/D16/D17).

Replaces the self-contained legacy script (last at commit a87356a; the
comparison harness re-extracts and runs it). Changes vs the legacy figures:

  - SPACES unified on the canonical (model_priors_laplace) bounds — the
    legacy trajectory used wider Linear (-3,3) and Quadratic boxes (plan §0
    V3); pass --legacy-spaces to reproduce those.
  - Z_Mx from is_log_Z_Mx (reference estimator) everywhere, replacing the
    legacy pure-Laplace n-sweep AND the legacy Laplace/MC sigmoid-blend
    hybrid in the τ-sweep (one estimator, no seam; the whole τ ladder is a
    reweighting of one sample set per model).
  - OCCAM: the legacy trajectory script omitted −log V (occam OFF) while its
    sibling hard-wired occam ON — the scripts now share one flag (default
    off = the D3 canonical convention, which here matches this script's own
    legacy behavior).
  - AVERAGED GP: fit_gp draws via _viz_spaces.averaged_gp (estimator change
    per D10; --gp-method map is the disclosed point-predictive default).

Usage: python model_prior_trajectory_laplace.py [--out-dir DIR]
           [--gp-method map|vi|hmc] [--occam] [--tau 0.3] [--quick]
           [--legacy-spaces]
"""

import argparse
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import _viz_spaces as V
from bistar_gp.laplace_evidence import laplace_log_Z_Mx


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    p.add_argument("--out-dir", default=os.path.join(
        os.path.dirname(__file__), "..", "output", "model_prior_trajectory"))
    p.add_argument("--gp-method", default="map", choices=["map", "vi", "hmc"])
    p.add_argument("--occam", action="store_true")
    p.add_argument("--tau", type=float, default=0.3)
    p.add_argument("--n-draws", type=int, default=150)
    p.add_argument("--n-is", type=int, default=40_000)
    p.add_argument("--quick", action="store_true")
    p.add_argument("--legacy-spaces", action="store_true",
                   help="the trajectory script's own wider Linear/Quadratic "
                        "boxes (harness comparisons)")
    p.add_argument("--n-perturb", type=int, default=0,
                   help="seeded random perturbations added per start — the "
                        "legacy trajectory multi-start convention used 20 "
                        "(harness comparisons)")
    args = p.parse_args()

    out_dir = os.path.abspath(args.out_dir)
    os.makedirs(out_dir, exist_ok=True)
    x_eval = np.linspace(-10, 10, 80)
    x_50, y_50 = V.generate_data(50, seed=42)
    spaces = (V.trajectory_legacy_spaces() if args.legacy_spaces
              else V.canonical_spaces())
    names = list(spaces.keys())
    starts_map = ({m: V.perturbed_starts(m, spaces, args.n_perturb)
                   for m in names} if args.n_perturb else None)

    # ── n-sweep at fixed τ ───────────────────────────────────────────
    n_values = list(range(0, 51, 2)) if not args.quick else [0, 10, 30, 50]
    priors_tr = np.empty((len(n_values), len(names)))
    lz_tr = np.empty_like(priors_tr)
    gstar_tr = np.empty_like(priors_tr)
    gp_50 = None
    for i, n in enumerate(n_values):
        gp, _ = V.averaged_gp(x_eval, x_50[:n] if n else None,
                              y_50[:n] if n else None,
                              gp_method=args.gp_method,
                              n_draws=args.n_draws, seed=42)
        if n == max(n_values):
            gp_50 = gp
        _, log_Z, priors, _ = V.model_prior_curves(
            spaces, x_eval, gp, [args.tau], estimator="is",
            occam=args.occam, n_is=args.n_is, starts_map=starts_map)
        priors_tr[i], lz_tr[i] = priors[0], log_Z[0]
        for j, m in enumerate(names):
            gstar_tr[i, j] = laplace_log_Z_Mx(
                spaces[m], x_eval, gp, tau=args.tau, occam=args.occam,
                starts=(starts_map or V.STARTS)[m]).G_at_min
        if n % 10 == 0:
            print(f"  n={n:3d}: " + "  ".join(
                f"{m}={priors_tr[i, j]:.1%}" for j, m in enumerate(names)))

    fig, axes = plt.subplots(1, 3, figsize=(21, 6))
    panels = [(priors_tr, "GP-Informed Model Prior  p(M | ψ)",
               "Model Prior Trajectory"),
              (lz_tr, "log Z_M  (IS estimate)",
               "Log Model Evidence (unnormalized)"),
              (gstar_tr, "G* = min Ḡ(φ)  [best-case divergence]",
               "How Well Each Model Can Match the GP")]
    for ax, (data, ylab, title) in zip(axes, panels):
        for j, m in enumerate(names):
            ax.plot(n_values, data[:, j], "o-", color=V.COLORS[m], lw=2.5,
                    ms=7, label=m)
        ax.set_xlabel("Sample Size n", fontsize=12)
        ax.set_ylabel(ylab, fontsize=12)
        ax.set_title(title, fontsize=13, fontweight="bold")
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.2)
    axes[0].axhline(0.25, color="gray", ls="--", lw=1, alpha=0.5)
    axes[0].set_ylim(-0.02, 1.02)
    fig.suptitle(f"BI* Model Prior Trajectory (IS estimator, τ = {args.tau}, "
                 f"occam={args.occam}, gp={args.gp_method})",
                 fontsize=13, fontweight="bold", y=1.04)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "model_prior_trajectory_laplace.png"),
                dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  saved model_prior_trajectory_laplace.png")

    # ── stacked flow ─────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(12, 6))
    order = [names.index(m) for m in V.STACK_ORDER]
    ax.stackplot(n_values, priors_tr[:, order].T, labels=V.STACK_ORDER,
                 colors=[V.COLORS[m] for m in V.STACK_ORDER], alpha=0.7,
                 edgecolor="white", linewidth=0.5)
    ax.set_xlabel("Sample Size n", fontsize=12)
    ax.set_ylabel("GP-Informed Model Prior  p(M | ψ)", fontsize=12)
    ax.set_title("BI* Model Prior Probability Flow", fontsize=13,
                 fontweight="bold")
    ax.legend(loc="center right", fontsize=10, framealpha=0.9)
    ax.set_ylim(0, 1)
    ax.set_xlim(min(n_values), max(n_values))
    ax.grid(True, alpha=0.15, axis="y")
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "model_prior_flow_laplace.png"),
                dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  saved model_prior_flow_laplace.png")

    # ── τ-sweep at n = max ───────────────────────────────────────────
    taus = np.logspace(-1.5, 2.5, 40 if not args.quick else 12)
    _, _, tau_priors, diag = V.model_prior_curves(
        spaces, x_eval, gp_50, taus, estimator="is", occam=args.occam,
        n_is=args.n_is, starts_map=starts_map)
    min_ess = min(float(np.min(d)) for d in diag.values())
    print(f"  τ-sweep min ESS across models/τ: {min_ess:.0f}")

    fig, ax = plt.subplots(figsize=(10, 6))
    for j, m in enumerate(names):
        ax.plot(taus, tau_priors[:, j], "-", color=V.COLORS[m], lw=2.5,
                label=m)
    ax.axhline(0.25, color="gray", ls="--", lw=1, alpha=0.5, label="Uniform")
    ax.axvline(args.tau, color="gray", ls=":", lw=1.5, alpha=0.7,
               label=f"τ = {args.tau}")
    ax.set_xscale("log")
    ax.set_xlabel("Temperature τ", fontsize=12)
    ax.set_ylabel("GP-Informed Model Prior  p(M | ψ)", fontsize=12)
    ax.set_title(f"τ Controls GP Influence on the Model Prior (n={max(n_values)})\n"
                 "one IS sample set per model, reweighted across the ladder",
                 fontsize=13, fontweight="bold")
    ax.legend(fontsize=10)
    ax.set_ylim(-0.02, 1.02)
    ax.grid(True, alpha=0.2)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "model_prior_tau_laplace.png"),
                dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  saved model_prior_tau_laplace.png")
    print(f"\nFigures in {out_dir}")


if __name__ == "__main__":
    main()
