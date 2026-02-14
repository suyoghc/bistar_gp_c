"""
BMS* Experiment on Toy Data — with Prior Sensitivity Analysis

For each named prior configuration:
  1. Check cache for existing HMC samples
  2. If missing (or force_rerun), run HMC and cache results
  3. Extract GP predictives (ψ's)
  4. Score candidate models under all metrics × τ values
  5. Compare posteriors across priors

Usage:
    python bms_star_toy.py                    # uses cache if available
    python bms_star_toy.py --force-rerun      # rerun everything
    python bms_star_toy.py --priors informative vague   # specific priors only
"""

import sys, os, argparse
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import torch
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from bistar_gp import generate_toy_data, build_model
from bistar_gp.fit import fit_map
from bistar_gp.candidates import build_toy_candidates
from bistar_gp.config import (
    PRIOR_CONFIGS, ExperimentConfig,
    build_kernels_from_config, build_likelihood_from_config,
    save_hmc_samples, load_hmc_samples,
    RESULTS_DIR,
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


def get_or_run_hmc(prior_name, prior_config, x_train, y_train, config):
    """Load cached HMC samples or run fresh."""

    cache_path = config.get_cache_path(prior_name)

    # Try cache first
    if config.use_cache and not config.force_rerun and config.cache_exists(prior_name):
        return load_hmc_samples(cache_path)

    # Run HMC
    print(f"\n  Running HMC for prior '{prior_name}'...")
    print(f"    {prior_config.description}")

    kernels, names = build_kernels_from_config(prior_config)
    likelihood = build_likelihood_from_config(prior_config)
    model, likelihood = build_model(x_train, y_train, kernels, names, likelihood)

    # Quick MAP first (stabilizes HMC initialization)
    fit_map(model, likelihood, x_train, y_train, n_iter=200, lr=0.05, verbose=False)

    try:
        from bistar_gp.fit import fit_hmc
        kernels2, names2 = build_kernels_from_config(prior_config)
        likelihood2 = build_likelihood_from_config(prior_config)
        model2, likelihood2 = build_model(x_train, y_train, kernels2, names2, likelihood2)

        mcmc_samples = fit_hmc(
            model2, likelihood2, x_train, y_train,
            n_samples=config.n_hmc_samples, n_warmup=config.n_warmup,
        )

        for k, v in mcmc_samples.items():
            print(f"    {k}: mean={v.mean():.4f}, std={v.std():.4f}")

    except ImportError:
        print("    Pyro not available — using MCMC simple fallback")
        from bistar_gp.fit import fit_mcmc_simple
        mcmc_samples = fit_mcmc_simple(
            model, likelihood, x_train, y_train,
            n_samples=config.n_hmc_samples, n_burnin=config.n_warmup,
            verbose=True,
        )

    # Cache
    if config.save_cache:
        save_hmc_samples(mcmc_samples, cache_path)

    return mcmc_samples


def run_single_prior(prior_name, prior_config, x_train, y_train,
                     x_eval, x_eval_torch, candidate_results, config):
    """Run full BMS* analysis for one prior configuration."""

    print(f"\n{'═' * 60}")
    print(f"  Prior: {prior_name}")
    print(f"  {prior_config.description}")
    print(f"{'═' * 60}")

    # 1. Get HMC samples
    mcmc_samples = get_or_run_hmc(prior_name, prior_config, x_train, y_train, config)

    # 2. Extract GP predictives
    print(f"\n  Extracting GP predictives...")
    kernel_builder = lambda: build_kernels_from_config(prior_config)

    # Need a model instance for extract_gp_predictives
    kernels, names = build_kernels_from_config(prior_config)
    likelihood = build_likelihood_from_config(prior_config)
    model, likelihood = build_model(x_train, y_train, kernels, names, likelihood)

    gp_samples = extract_gp_predictives(
        model, likelihood, x_train, y_train, x_eval_torch,
        mcmc_samples, kernel_builder=kernel_builder,
        likelihood_builder=lambda: build_likelihood_from_config(prior_config),
        n_posterior_samples=config.n_posterior_samples, jitter=1e-4,
    )

    if len(gp_samples) == 0:
        print(f"  WARNING: No valid GP predictives for prior '{prior_name}'. Skipping.")
        return None, None

    # 3. Run BMS*
    print(f"\n  Running BMS*...")
    taus = np.logspace(*config.tau_range, config.n_taus)
    results = run_bms_star(gp_samples, candidate_results, config.metrics, taus)

    # Print table at a few τ values
    for tau in [1.0, 5.0, 10.0]:
        print_bms_star_table(results, tau)

    return results, gp_samples


def plot_prior_sensitivity(all_results, config, tau_target=5.0):
    """
    Compare model posteriors across prior configurations at a fixed τ.
    One bar group per prior, bars colored by model.
    """
    prior_names = list(all_results.keys())
    metric_names = config.metrics
    n_priors = len(prior_names)

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.flatten()
    model_colors = ['#e74c3c', '#3498db', '#2ecc71', '#9b59b6']

    for ax_idx, metric_name in enumerate(metric_names[:4]):
        ax = axes[ax_idx]

        # Collect posteriors across priors
        model_names = None
        posteriors_by_prior = []
        for prior_name in prior_names:
            results = all_results[prior_name]
            if results is None:
                continue
            taus = sorted(results[metric_name].keys())
            closest_tau = min(taus, key=lambda t: abs(t - tau_target))
            bms = results[metric_name][closest_tau]
            posteriors_by_prior.append((prior_name, bms.instance_posteriors))
            if model_names is None:
                model_names = bms.instance_names

        if not posteriors_by_prior:
            continue

        n_groups = len(posteriors_by_prior)
        n_models = len(model_names)
        x = np.arange(n_groups)
        width = 0.8 / n_models

        for m_idx, model_name in enumerate(model_names):
            vals = [p[1][m_idx] for p in posteriors_by_prior]
            offset = (m_idx - n_models / 2 + 0.5) * width
            ax.bar(x + offset, vals, width, label=model_name,
                   color=model_colors[m_idx % len(model_colors)])

        ax.set_xticks(x)
        ax.set_xticklabels([p[0] for p in posteriors_by_prior], rotation=30, ha='right')
        ax.set_ylabel("Posterior probability")
        ax.set_title(f"{metric_name.replace('_', ' ').title()}")
        ax.set_ylim(0, 1)
        ax.legend(fontsize=7)
        ax.grid(True, alpha=0.2, axis='y')

    fig.suptitle(f"Prior Sensitivity: BMS* Posteriors at τ ≈ {tau_target}", fontsize=14)
    fig.tight_layout()
    return fig


def plot_prior_tau_comparison(all_results, config):
    """
    τ sensitivity curves, one row per prior, one column per metric.
    Shows how prior choice affects the full τ-posterior landscape.
    """
    prior_names = [p for p in all_results if all_results[p] is not None]
    metric_names = config.metrics[:4]
    n_priors = len(prior_names)
    n_metrics = len(metric_names)

    fig, axes = plt.subplots(n_priors, n_metrics,
                             figsize=(4 * n_metrics, 3 * n_priors),
                             squeeze=False)
    model_colors = ['#e74c3c', '#3498db', '#2ecc71', '#9b59b6']

    for row, prior_name in enumerate(prior_names):
        results = all_results[prior_name]
        for col, metric_name in enumerate(metric_names):
            ax = axes[row][col]
            taus = sorted(results[metric_name].keys())
            model_names = results[metric_name][taus[0]].instance_names
            n_models = len(model_names)

            posteriors = np.zeros((len(taus), n_models))
            for t_idx, tau in enumerate(taus):
                posteriors[t_idx] = results[metric_name][tau].instance_posteriors

            for m_idx, name in enumerate(model_names):
                ax.semilogx(taus, posteriors[:, m_idx],
                           color=model_colors[m_idx % len(model_colors)],
                           linewidth=1.5, label=name if row == 0 else None)

            ax.set_ylim(-0.05, 1.05)
            ax.grid(True, alpha=0.2)
            if row == 0:
                ax.set_title(metric_name.replace('_', ' ').title(), fontsize=10)
            if col == 0:
                ax.set_ylabel(prior_name, fontsize=10, fontweight='bold')
            if row == n_priors - 1:
                ax.set_xlabel("τ")

    # Single legend at top
    handles, labels = axes[0][0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='upper center', ncol=4, fontsize=9,
              bbox_to_anchor=(0.5, 1.02))

    fig.suptitle("Prior × Metric × Temperature: Full BMS* Landscape", fontsize=14, y=1.05)
    fig.tight_layout()
    return fig


def plot_joint_vs_pointwise(results, prior_name, tau_target=1.0):
    """
    Side-by-side bar chart: joint metrics (top row) vs pointwise (bottom row).
    Makes the covariance-vs-mean story visually obvious.
    """
    joint_names = [k for k in results if not k.startswith("pw_")]
    pw_names = [k for k in results if k.startswith("pw_")]

    n_joint = len(joint_names)
    n_pw = len(pw_names)
    ncols = max(n_joint, n_pw)

    fig, axes = plt.subplots(2, ncols, figsize=(3.5 * ncols, 7))
    if ncols == 1:
        axes = axes.reshape(2, 1)
    model_colors = ['#e74c3c', '#3498db', '#2ecc71', '#9b59b6']

    for row, (metric_list, row_label) in enumerate([
        (joint_names, "Joint (full covariance)"),
        (pw_names, "Pointwise (marginals only)"),
    ]):
        for col, metric_name in enumerate(metric_list):
            ax = axes[row][col]
            taus = sorted(results[metric_name].keys())
            closest_tau = min(taus, key=lambda t: abs(t - tau_target))
            bms = results[metric_name][closest_tau]

            bars = ax.bar(range(len(bms.instance_names)), bms.instance_posteriors,
                         color=model_colors[:len(bms.instance_names)])
            ax.set_xticks(range(len(bms.instance_names)))
            ax.set_xticklabels(bms.instance_names, rotation=30, ha='right', fontsize=8)
            ax.set_ylim(0, 1)
            ax.set_title(metric_name, fontsize=9)
            ax.grid(True, alpha=0.2, axis='y')

            if col == 0:
                ax.set_ylabel(row_label, fontsize=9, fontweight='bold')

        # Hide unused columns
        for col in range(len(metric_list), ncols):
            axes[row][col].set_visible(False)

    fig.suptitle(f"Joint vs Pointwise — Prior: {prior_name} — τ ≈ {tau_target}", fontsize=14)
    fig.tight_layout()
    return fig


def main():
    parser = argparse.ArgumentParser(description="BMS* Toy Experiment")
    parser.add_argument("--force-rerun", action="store_true", help="Ignore cache")
    parser.add_argument("--priors", nargs="+", default=None, help="Specific prior configs")
    parser.add_argument("--no-cache", action="store_true", help="Don't use or save cache")
    args = parser.parse_args()

    config = ExperimentConfig()
    config.force_rerun = args.force_rerun
    if args.no_cache:
        config.use_cache = False
        config.save_cache = False
    if args.priors:
        config.prior_configs = args.priors

    os.makedirs(RESULTS_DIR, exist_ok=True)

    print("=" * 60)
    print("  BMS* Experiment: Toy Data + Prior Sensitivity")
    print("=" * 60)
    print(f"  Priors:  {config.prior_configs}")
    print(f"  Cache:   use={config.use_cache}, save={config.save_cache}, force={config.force_rerun}")
    print(f"  HMC:     n_samples={config.n_hmc_samples}, warmup={config.n_warmup}")
    print(f"  BMS*:    {config.n_taus} τ values, {len(config.metrics)} metrics")

    # ── 1. Generate data (same across all priors) ─────────────────
    x_train, y_train, info = generate_toy_data(
        n_points=config.n_points, noise_std=config.noise_std,
        bias_slope=config.bias_slope, seed=config.seed,
        x_range=config.x_range,
    )
    x_np = x_train.numpy()
    y_np = y_train.numpy()
    x_eval = np.linspace(x_np.min() - 1, x_np.max() + 1, config.n_eval)
    x_eval_torch = torch.tensor(x_eval).double()

    print(f"\n  Data: {len(x_train)} points, true model = sin(x) + 0.25x + N(0, {config.noise_std}²)")

    # ── 2. Fit candidate models (same across all priors) ──────────
    print("\n── Fitting Candidate Models ──")
    candidates = build_toy_candidates()
    candidate_results = []
    for cand in candidates:
        cand.fit(x_np, y_np)
        cr = cand.predict(x_eval)
        candidate_results.append(cr)
        print(f"  {cr.name:<15} σ={cr.noise_var**0.5:.4f}")

    # ── 3. Run BMS* for each prior ────────────────────────────────
    all_results = {}
    all_gp_samples = {}

    for prior_name in config.prior_configs:
        if prior_name not in PRIOR_CONFIGS:
            print(f"\n  WARNING: Unknown prior '{prior_name}', skipping")
            continue

        prior_config = PRIOR_CONFIGS[prior_name]
        results, gp_samples = run_single_prior(
            prior_name, prior_config, x_train, y_train,
            x_eval, x_eval_torch, candidate_results, config,
        )
        all_results[prior_name] = results
        all_gp_samples[prior_name] = gp_samples

    # ── 4. Plots ──────────────────────────────────────────────────
    print("\n── Generating Plots ──")

    # Per-prior plots
    for prior_name, results in all_results.items():
        if results is None:
            continue

        # Split metrics into joint vs pointwise
        joint_metrics = {k: v for k, v in results.items() if not k.startswith("pw_")}
        pw_metrics = {k: v for k, v in results.items() if k.startswith("pw_")}

        # τ sensitivity — joint metrics
        if joint_metrics:
            fig1a = plot_bms_star_results(joint_metrics)
            fig1a.suptitle(f"Joint Metrics — Prior: {prior_name}", fontsize=14)
            path1a = os.path.join(RESULTS_DIR, f"bms_tau_joint_{prior_name}.png")
            fig1a.savefig(path1a, bbox_inches="tight", dpi=150)
            print(f"  Saved: {path1a}")

        # τ sensitivity — pointwise metrics
        if pw_metrics:
            fig1b = plot_bms_star_results(pw_metrics)
            fig1b.suptitle(f"Pointwise Metrics — Prior: {prior_name}", fontsize=14)
            path1b = os.path.join(RESULTS_DIR, f"bms_tau_pointwise_{prior_name}.png")
            fig1b.savefig(path1b, bbox_inches="tight", dpi=150)
            print(f"  Saved: {path1b}")

        # G heatmaps — all metrics
        fig2 = plot_G_heatmaps(results)
        path2 = os.path.join(RESULTS_DIR, f"bms_G_{prior_name}.png")
        fig2.savefig(path2, bbox_inches="tight", dpi=150)
        print(f"  Saved: {path2}")

        # Candidate predictions overlay
        gp_samps = all_gp_samples.get(prior_name)
        if gp_samps:
            fig3 = plot_candidate_predictions(
                x_eval, gp_samps, candidate_results, x_np, y_np,
            )
            fig3.suptitle(f"Candidates vs GP — Prior: {prior_name}", fontsize=14)
            path3 = os.path.join(RESULTS_DIR, f"bms_candidates_{prior_name}.png")
            fig3.savefig(path3, bbox_inches="tight", dpi=150)
            print(f"  Saved: {path3}")

        # Joint vs Pointwise comparison bar chart
        fig_cmp = plot_joint_vs_pointwise(results, prior_name)
        path_cmp = os.path.join(RESULTS_DIR, f"bms_joint_vs_pw_{prior_name}.png")
        fig_cmp.savefig(path_cmp, bbox_inches="tight", dpi=150)
        print(f"  Saved: {path_cmp}")

        # Full table at τ=1 for all metrics
        print(f"\n  ── All metrics at τ≈1 for prior '{prior_name}' ──")
        print_bms_star_table(results, 1.0)

    # Cross-prior comparison plots
    valid_results = {k: v for k, v in all_results.items() if v is not None}
    if len(valid_results) > 1:
        fig4 = plot_prior_sensitivity(valid_results, config, tau_target=5.0)
        path4 = os.path.join(RESULTS_DIR, "bms_prior_sensitivity.png")
        fig4.savefig(path4, bbox_inches="tight", dpi=150)
        print(f"  Saved: {path4}")

        fig5 = plot_prior_tau_comparison(valid_results, config)
        path5 = os.path.join(RESULTS_DIR, "bms_prior_tau_landscape.png")
        fig5.savefig(path5, bbox_inches="tight", dpi=150)
        print(f"  Saved: {path5}")

    plt.close("all")

    # ── 5. Summary ────────────────────────────────────────────────
    print("\n── Summary ──")
    print(f"  Results saved to: {RESULTS_DIR}/")
    if config.save_cache:
        print(f"  HMC cache saved to: {config.cache_dir}/")
    print("\n  To rerun from scratch:  python bms_star_toy.py --force-rerun")
    print("  To run specific priors: python bms_star_toy.py --priors informative vague")
    print("\n  Done!")


if __name__ == "__main__":
    main()
