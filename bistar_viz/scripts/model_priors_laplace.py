"""
BI* Model Prior Probabilities — unified onto bistar_gp.laplace_evidence
(docs/plan-viz-unification.md §2; DECISIONS D10/D16/D17).

Replaces the self-contained legacy script (last at commit a87356a; the
comparison harness viz_unification_compare.py re-extracts and runs it). What
changed and why, relative to the legacy figures:

  - METRIC: none — the legacy "pointwise variance-weighted MSE" is exactly
    pw_kl_vcal (D10, proven to 1e-12).
  - AVERAGED GP (estimator change, D10): draws from fit_gp(--gp-method)
    through extract_gp_predictives + average_gp_posterior, replacing
    LML-importance-weighted PRIOR draws. --gp-method map (default) is a
    point-estimate predictive — the disclosed mechanism-figure default;
    vi/hmc give genuine posterior draws.
  - Z_Mx ESTIMATOR: defensive-mixture IS (is_log_Z_Mx) — the reference
    estimator; pure Laplace mis-ranks models at high τ and carries 0.1-0.25
    posterior distortion mid-range (plan §0 V1). --estimator laplace|mc
    reproduce the alternatives; the decomposition figure is inherently
    Laplace-structured and always uses the (multi-start) Laplace pieces.
  - OCCAM: canonical default occam=False (D3); the legacy script hard-wired
    occam ON — pass --occam to reproduce that convention.

Usage: python model_priors_laplace.py [--out-dir DIR] [--gp-method map|vi|hmc]
           [--estimator is|laplace|mc] [--occam] [--tau 0.3] [--quick]
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


def stage_figures(args, out_dir, x_eval, x_50, y_50, spaces):
    """Bar chart at n=0/10/50 + the Laplace decomposition figure."""
    stages = [("Prior\n(no data)", 0), ("After\nn = 10", 10),
              ("After\nn = 50", 50)]
    names = list(spaces.keys())
    results = []
    for label, n in stages:
        gp, kept = V.averaged_gp(x_eval, x_50[:n] if n else None,
                                 y_50[:n] if n else None,
                                 gp_method=args.gp_method,
                                 n_draws=args.n_draws, seed=42)
        _, log_Z, priors, diag = V.model_prior_curves(
            spaces, x_eval, gp, [args.tau], estimator=args.estimator,
            occam=args.occam, n_is=args.n_is, starts_map=args.starts_map)
        zmx = {m: laplace_log_Z_Mx(spaces[m], x_eval, gp, tau=args.tau,
                                   occam=args.occam,
                                   starts=(args.starts_map or V.STARTS)[m])
               for m in names}
        results.append((label, n, priors[0], zmx, kept))
        print(f"n={n}: retained {kept} draws; priors " +
              " ".join(f"{m}={p:.1%}" for m, p in zip(names, priors[0])))

    fig, axes = plt.subplots(1, 3, figsize=(17, 6), sharey=True)
    for col, (label, n, priors, _, _) in enumerate(results):
        ax = axes[col]
        bars = ax.bar(names, priors, color=[V.COLORS[m] for m in names],
                      alpha=0.85, edgecolor="white", linewidth=1.5)
        for bar, p in zip(bars, priors):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.015,
                    f"{p:.1%}", ha="center", va="bottom", fontsize=12,
                    fontweight="bold")
        ax.axhline(0.25, color="gray", ls="--", lw=1, alpha=0.5,
                   label="Uniform (1/4)" if col == 0 else None)
        ax.set_ylim(0, 1.05)
        ax.set_title(label, fontsize=14, fontweight="bold")
        ax.tick_params(axis="x", rotation=15, labelsize=11)
        ax.grid(True, alpha=0.15, axis="y")
        if col == 0:
            ax.set_ylabel("GP-Informed Model Prior  p(M | ψ)", fontsize=12)
            ax.legend(fontsize=9)
    fig.suptitle(
        f"BI* Model Prior:  p(M|ψ) ∝ Z_M   ({args.estimator} estimator, "
        f"τ = {args.tau}, occam={args.occam}, gp={args.gp_method})",
        fontsize=13, fontweight="bold", y=1.04)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "model_prior_bars_laplace.png"),
                dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  saved model_prior_bars_laplace.png")

    # Decomposition (Laplace-structured by definition: G*/τ vs the Laplace
    # complexity pieces; the reference-estimator priors above need no such
    # decomposition and do not have one).
    fig, axes = plt.subplots(1, 3, figsize=(17, 6))
    for col, (label, n, _, zmx, _) in enumerate(results):
        ax = axes[col]
        g_pen = [zmx[m].G_at_min / args.tau for m in names]
        occ_pen = [-(0.5 * zmx[m].n_params * np.log(2 * np.pi * args.tau)
                     - 0.5 * zmx[m].logdet_H
                     - (zmx[m].log_volume if args.occam else 0.0))
                   for m in names]
        x_pos = np.arange(len(names))
        w = 0.35
        ax.bar(x_pos - w / 2, g_pen, w,
               color=[V.COLORS[m] for m in names], alpha=0.6,
               label="G*/τ (fit penalty)")
        ax.bar(x_pos + w / 2, occ_pen, w,
               color=[V.COLORS[m] for m in names], alpha=0.3, hatch="///",
               label="Occam penalty")
        ax.set_xticks(x_pos)
        ax.set_xticklabels(names, rotation=15, fontsize=10)
        ax.set_title(label, fontsize=13, fontweight="bold")
        ax.grid(True, alpha=0.15, axis="y")
        if col == 0:
            ax.set_ylabel("Penalty (higher = worse)", fontsize=11)
            ax.legend(fontsize=9)
    fig.suptitle("BI* Laplace Decomposition: fit penalty vs complexity "
                 f"(multi-start Laplace, occam={args.occam})",
                 fontsize=12, fontweight="bold", y=1.04)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "model_prior_decomp_laplace.png"),
                dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  saved model_prior_decomp_laplace.png")


def sweep_figures(args, out_dir, x_eval, x_50, y_50, spaces):
    """Prior vs n sweep + stacked probability flow."""
    n_values = [0, 3, 5, 8, 10, 15, 20, 30, 40, 50] if not args.quick \
        else [0, 10, 50]
    names = list(spaces.keys())
    traces = np.empty((len(n_values), len(names)))
    lz_traces = np.empty_like(traces)
    for i, n in enumerate(n_values):
        gp, _ = V.averaged_gp(x_eval, x_50[:n] if n else None,
                              y_50[:n] if n else None,
                              gp_method=args.gp_method,
                              n_draws=args.n_draws, seed=42)
        _, log_Z, priors, _ = V.model_prior_curves(
            spaces, x_eval, gp, [args.tau], estimator=args.estimator,
            occam=args.occam, n_is=args.n_is, starts_map=args.starts_map)
        traces[i], lz_traces[i] = priors[0], log_Z[0]
        print(f"  n={n:3d}: " + "  ".join(
            f"{m}={p:.1%}" for m, p in zip(names, priors[0])))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(17, 6))
    for j, m in enumerate(names):
        ax1.plot(n_values, traces[:, j], "o-", color=V.COLORS[m], lw=2.5,
                 ms=7, label=m)
        ax2.plot(n_values, lz_traces[:, j], "o-", color=V.COLORS[m], lw=2.5,
                 ms=7, label=m)
    ax1.axhline(0.25, color="gray", ls="--", lw=1, alpha=0.5, label="Uniform")
    for ax, ylab, title in ((ax1, "Model Prior p(M | ψ)", "Prior vs data"),
                            (ax2, "log Z_M (unnormalized)", "log Z vs data")):
        ax.set_xlabel("Sample Size n", fontsize=12)
        ax.set_ylabel(ylab, fontsize=12)
        ax.set_title(title, fontsize=13, fontweight="bold")
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.2)
    ax1.set_ylim(-0.02, 1.02)
    fig.suptitle(f"BI* Model Selection ({args.estimator} estimator, "
                 f"τ = {args.tau})", fontsize=14, fontweight="bold", y=1.03)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "model_prior_sweep_laplace.png"),
                dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  saved model_prior_sweep_laplace.png")

    fig, ax = plt.subplots(figsize=(12, 6))
    order = [names.index(m) for m in V.STACK_ORDER]
    ax.stackplot(n_values, traces[:, order].T, labels=V.STACK_ORDER,
                 colors=[V.COLORS[m] for m in V.STACK_ORDER], alpha=0.7,
                 edgecolor="white", lw=0.5)
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


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    p.add_argument("--out-dir", default=os.path.join(
        os.path.dirname(__file__), "..", "output", "model_priors"))
    p.add_argument("--gp-method", default="map", choices=["map", "vi", "hmc"])
    p.add_argument("--estimator", default="is",
                   choices=["is", "laplace", "mc"])
    p.add_argument("--occam", action="store_true",
                   help="subtract log V_ref (the legacy script's hard-wired "
                        "convention); canonical default is off (D3)")
    p.add_argument("--tau", type=float, default=0.3)
    p.add_argument("--n-draws", type=int, default=150)
    p.add_argument("--n-is", type=int, default=40_000)
    p.add_argument("--quick", action="store_true")
    p.add_argument("--n-perturb", type=int, default=5,
                   help="seeded perturbations per start for IS proposal "
                        "coverage (0 disables)")
    args = p.parse_args()

    out_dir = os.path.abspath(args.out_dir)
    os.makedirs(out_dir, exist_ok=True)
    x_eval = np.linspace(-10, 10, 80)
    x_50, y_50 = V.generate_data(50, seed=42)
    spaces = V.canonical_spaces()
    args.starts_map = ({m: V.perturbed_starts(m, spaces, args.n_perturb)
                        for m in spaces} if args.n_perturb else None)

    stage_figures(args, out_dir, x_eval, x_50, y_50, spaces)
    sweep_figures(args, out_dir, x_eval, x_50, y_50, spaces)
    print(f"\nFigures in {out_dir}")


if __name__ == "__main__":
    main()
