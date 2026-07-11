"""
BMS* on Mauna Loa CO2 using the harmonized appendix trend-law universe.

Decision A4 and plan section 3 freeze the seasonal period at 1.0, use two
fixed-frequency sine harmonics, and apply the shared D11 multi-start full-NLL
protocol to Linear+2Harm, Quad+2Harm, and Exponential+2Harm. This appendix
universe provides a trend-law contrast only. Its BMS* normalization always
remains separate from the four-model main ladder normalization.

The GP decomposes into trend + seasonal + medium-term components. BMS* scores
each parametric candidate against GP posterior draws, with ``pw_kl_vcal`` as
the decision A4 primary metric and the frozen temperature grid reported in full.

Usage:
    python bms_star_mauna_loa.py                    # full run
    python bms_star_mauna_loa.py --map-only         # skip HMC, MAP only
    python bms_star_mauna_loa.py --n-hmc 100        # fewer HMC samples
"""

import sys, os, argparse, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import torch
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from bistar_gp import load_mauna_loa, build_model
# Registers pw_kl_vcal in bms_star.METRICS for the MAUNA_METRICS contract.
import bistar_gp.metrics_v2  # noqa: F401
from bistar_gp.model import build_mauna_loa_kernels, build_likelihood
from bistar_gp.fit import fit_map, print_hyperparameters, fit_hmc
from bistar_gp.mauna_loa_candidates import (
    APPENDIX_TREND3,
    MAUNA_HEADLINE_TAU,
    MAUNA_METRICS,
    MAUNA_TAU_GRID,
    assert_single_universe,
    build_universe,
)
from bistar_gp.bms_star import (
    extract_gp_predictives,
    run_bms_star,
    plot_bms_star_results,
    plot_G_heatmaps,
    plot_candidate_predictions,
    print_bms_star_table,
)

torch.set_default_dtype(torch.float64)


# ═══════════════════════════════════════════════════════════════════
# Main Experiment
# ═══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="BMS* on Mauna Loa CO2")
    parser.add_argument("--map-only", action="store_true", help="Skip HMC")
    parser.add_argument("--n-hmc", type=int, default=100, help="HMC samples")
    parser.add_argument("--n-warmup", type=int, default=100, help="HMC warmup")
    parser.add_argument("--n-eval", type=int, default=300, help="Evaluation grid points")
    parser.add_argument("--output-dir", type=str, default="results_bms_mauna_loa")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    print("=" * 60)
    print("  BMS* on Mauna Loa CO₂")
    print("  Candidates: Linear, Quadratic, Exponential (all + 2Harm)")
    print("=" * 60)

    # ── 1. Load data ──────────────────────────────────────────────
    x_train, y_train, x_test, y_test, info = load_mauna_loa(
        normalize=True, test_years=5.0
    )
    x_np = x_train.numpy()
    y_np = y_train.numpy()
    print(f"\n  Train: {len(x_train)}, Test: {len(x_test)}")
    print(f"  Normalization: y_mean={info['y_mean']:.2f}, y_std={info['y_std']:.2f}")

    # Evaluation grid — covers train + test range
    x_all = torch.cat([x_train, x_test])
    x_eval_np = np.linspace(x_all.min().item(), x_all.max().item(), args.n_eval)
    x_eval = torch.tensor(x_eval_np).double()

    # ── 2. Fit candidate models ───────────────────────────────────
    print("\n── Fitting Candidate Models ──")
    candidates = build_universe(APPENDIX_TREND3)
    candidate_results = []

    for cand in candidates:
        print(f"  Fitting {cand.name}...")
        cand.fit(x_np, y_np)
        cr = cand.predict(x_eval_np)
        candidate_results.append(cr)
        print(f"    σ = {cr.noise_var**0.5:.6f}")
        # Print parameters
        for k, v in cr.parameters.items():
            print(f"    {k} = {v:.6f}")

    # Quick check: candidate predictions at endpoints
    print("\n  Candidate residual RMSEs (train):")
    for cand in candidates:
        cr_train = cand.predict(x_np)
        rmse = np.sqrt(np.mean((y_np - cr_train.mean)**2))
        print(f"    {cand.name}: {rmse:.6f} (normalized), {rmse * info['y_std']:.2f} ppm")

    # ── 3. MAP fit GP ─────────────────────────────────────────────
    print("\n── MAP GP Fit ──")
    kernels, names = build_mauna_loa_kernels()
    likelihood = build_likelihood()
    model, likelihood = build_model(x_train, y_train, kernels, names, likelihood)
    losses = fit_map(model, likelihood, x_train, y_train,
                     n_iter=800, lr=0.02, print_every=200)
    print_hyperparameters(model, likelihood)

    if args.map_only:
        print("\n  --map-only: Skipping HMC. No BMS* scoring.")
        # Still plot candidates vs data
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.scatter(x_np, y_np, c='k', marker='x', s=10, alpha=0.5, label='Train')
        ax.scatter(x_test.numpy(), y_test.numpy(), c='red', marker='.', s=10, alpha=0.5, label='Test')
        colors = ['#e74c3c', '#3498db', '#2ecc71']
        for cr, color in zip(candidate_results, colors):
            ax.plot(x_eval_np, cr.mean, color=color, linewidth=2, label=cr.name)
        ax.legend()
        ax.set_title("Mauna Loa: Candidate Models")
        fig.savefig(os.path.join(args.output_dir, "candidates_vs_data.png"),
                    bbox_inches="tight", dpi=150)
        print(f"  Saved: {args.output_dir}/candidates_vs_data.png")
        return

    # ── 4. HMC ────────────────────────────────────────────────────
    print(f"\n── HMC ({args.n_hmc} samples, {args.n_warmup} warmup) ──")
    kernels2, names2 = build_mauna_loa_kernels()
    likelihood2 = build_likelihood()
    model2, likelihood2 = build_model(x_train, y_train, kernels2, names2, likelihood2)

    # MAP-fit THIS model so fit_hmc's init_to_map starts in the typical set, and
    # cap the NUTS tree depth: the Mauna noise posterior concentrates near zero,
    # so uncapped depth-10 trees are intractable (see DECISIONS D8).
    fit_map(model2, likelihood2, x_train, y_train, n_iter=300, lr=0.02, verbose=False)
    mcmc_samples = fit_hmc(
        model2, likelihood2, x_train, y_train,
        n_samples=args.n_hmc, n_warmup=args.n_warmup,
        max_tree_depth=7,
    )

    # Save HMC samples for reuse
    cache_path = os.path.join(args.output_dir, "hmc_samples.pt")
    torch.save(mcmc_samples, cache_path)
    print(f"  Cached HMC samples: {cache_path}")

    # ── 5. Extract GP predictives ─────────────────────────────────
    print("\n── Extracting GP Predictives ──")
    kernel_builder = lambda: build_mauna_loa_kernels()

    gp_samples = extract_gp_predictives(
        model2, likelihood2, x_train, y_train, x_eval,
        mcmc_samples, kernel_builder=kernel_builder,
        n_posterior_samples=min(100, args.n_hmc),
        jitter=1e-4,
    )

    if len(gp_samples) == 0:
        print("  ERROR: No valid GP predictives. Aborting.")
        return

    # ── 6. Run BMS* ───────────────────────────────────────────────
    print("\n── Running BMS* ──")
    assert_single_universe(candidates)
    metrics = list(MAUNA_METRICS)
    taus = np.array(MAUNA_TAU_GRID)
    results = run_bms_star(gp_samples, candidate_results, metrics, taus)

    # Decision A4 reports every pre-registered temperature.
    for tau in MAUNA_TAU_GRID:
        print_bms_star_table(results, tau)

    # ── 7. Save results ───────────────────────────────────────────
    print("\n── Saving Results ──")

    # Summary JSON
    summary = {"n_gp_samples": len(gp_samples), "n_candidates": len(candidate_results)}
    for metric_name in metrics:
        bms = results[metric_name][MAUNA_HEADLINE_TAU]
        summary[metric_name] = {
            "tau": float(MAUNA_HEADLINE_TAU),
            "posteriors": {name: float(p) for name, p in
                          zip(bms.instance_names, bms.instance_posteriors)},
            "winner": bms.instance_names[int(np.argmax(bms.instance_posteriors))],
        }
    with open(os.path.join(args.output_dir, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)

    # ── 8. Plots ──────────────────────────────────────────────────
    print("\n── Generating Plots ──")

    # τ sensitivity — pointwise metrics
    fig1 = plot_bms_star_results(results)
    fig1.suptitle("BMS* Mauna Loa: Model Posteriors vs τ", fontsize=14)
    path1 = os.path.join(args.output_dir, "bms_tau_curves.png")
    fig1.savefig(path1, bbox_inches="tight", dpi=150)
    print(f"  Saved: {path1}")

    # G heatmaps
    fig2 = plot_G_heatmaps(results)
    path2 = os.path.join(args.output_dir, "bms_G_heatmaps.png")
    fig2.savefig(path2, bbox_inches="tight", dpi=150)
    print(f"  Saved: {path2}")

    # Candidate predictions vs GP posterior
    fig3 = plot_candidate_predictions(
        x_eval_np, gp_samples, candidate_results, x_np, y_np,
    )
    fig3.suptitle("Mauna Loa: Candidates vs GP Posterior", fontsize=14)
    path3 = os.path.join(args.output_dir, "bms_candidates_vs_gp.png")
    fig3.savefig(path3, bbox_inches="tight", dpi=150)
    print(f"  Saved: {path3}")

    # Custom: candidates vs data with test set
    fig4, ax = plt.subplots(figsize=(14, 6))
    ax.scatter(x_np, y_np, c='k', marker='x', s=10, alpha=0.3, label='Train')
    ax.scatter(x_test.numpy(), y_test.numpy(), c='red', marker='.', s=15,
              alpha=0.5, label='Test (held out)')
    colors = ['#e74c3c', '#3498db', '#2ecc71']
    for cr, color in zip(candidate_results, colors):
        ax.plot(x_eval_np, cr.mean, color=color, linewidth=2, label=cr.name)
    # GP mean
    gp_means = np.array([s.mean for s in gp_samples])
    gp_mean = gp_means.mean(axis=0)
    gp_std = gp_means.std(axis=0)
    ax.plot(x_eval_np, gp_mean, 'k-', linewidth=1.5, alpha=0.7, label='GP mean')
    ax.fill_between(x_eval_np, gp_mean - 2*gp_std, gp_mean + 2*gp_std,
                    alpha=0.15, color='gray')
    ax.legend(fontsize=9)
    ax.set_xlabel("Time (normalized)")
    ax.set_ylabel("CO₂ (normalized)")
    ax.set_title("Mauna Loa: All Candidates + GP Posterior")
    ax.grid(True, alpha=0.2)
    path4 = os.path.join(args.output_dir, "all_candidates_vs_gp.png")
    fig4.savefig(path4, bbox_inches="tight", dpi=150)
    print(f"  Saved: {path4}")

    plt.close("all")

    # ── 9. Final summary ──────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  BMS* Mauna Loa — Summary")
    print("=" * 60)
    for metric_name in metrics:
        winner = summary[metric_name]["winner"]
        posteriors = summary[metric_name]["posteriors"]
        tau = summary[metric_name]["tau"]
        p_str = ", ".join(f"{k}: {v:.3f}" for k, v in posteriors.items())
        print(f"  {metric_name} (τ={tau:.1f}): Winner = {winner}")
        print(f"    [{p_str}]")

    print(f"\n  Results in: {args.output_dir}/")
    print("  Done!")


if __name__ == "__main__":
    main()
