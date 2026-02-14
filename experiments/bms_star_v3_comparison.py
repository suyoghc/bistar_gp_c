"""
BMS* V3 Aggregation Strategies Comparison

Tests three alternative aggregation strategies against original Boltzmann:
  1. Averaged GP posterior (bypass per-sample scoring)
  2. Robust aggregation (median, trimmed mean, rank)
  3. Marginal likelihood weighting (quality-weighted Boltzmann)

Uses cached HMC samples + v2 calibrated metrics.

Usage:
    python experiments/bms_star_v3_comparison.py --priors informative
"""

import sys, os, argparse
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import torch
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from bistar_gp import generate_toy_data, build_model
from bistar_gp.candidates import build_toy_candidates
from bistar_gp.config import (
    PRIOR_CONFIGS, ExperimentConfig,
    build_kernels_from_config, build_likelihood_from_config,
    load_hmc_samples,
    RESULTS_DIR,
)
from bistar_gp.bms_star import (
    extract_gp_predictives,
    run_bms_star,
    print_bms_star_table,
    METRICS,
)

# Register v2 metrics
import bistar_gp.metrics_v2

# Import v3 aggregation strategies
from bistar_gp.aggregation_v3 import (
    score_averaged_gp,
    run_robust_aggregation,
    compute_log_marginal_likelihoods,
    run_weighted_bms_star,
    plot_strategy_comparison,
    plot_all_strategies_grid,
    plot_weighted_tau_sensitivity,
    plot_mll_distribution,
)

torch.set_default_dtype(torch.float64)

# Metrics to test across all strategies
COMPARISON_METRICS = [
    "pw_kl_vcal", "pw_hellinger_vcal", "pw_nll_gp",
    "pw_mse", "pw_hellinger_mean",
]


def main():
    parser = argparse.ArgumentParser(description="BMS* V3 aggregation strategies")
    parser.add_argument("--priors", nargs="+", default=["informative"])
    parser.add_argument("--tau-values", type=float, nargs="+", default=[0.5, 1.0, 5.0])
    args = parser.parse_args()

    config = ExperimentConfig()

    # ── Data ──
    np.random.seed(config.seed)
    torch.manual_seed(config.seed)
    x_train, y_train, info = generate_toy_data(
        n_points=config.n_points, noise_std=config.noise_std,
        bias_slope=config.bias_slope, seed=config.seed,
    )
    x_train_np = x_train.numpy()
    y_train_np = y_train.numpy()
    x_eval = np.linspace(*config.x_range, config.n_eval)
    x_eval_torch = torch.tensor(x_eval, dtype=torch.float64)

    # ── Candidates ──
    print("\nFitting candidate models...")
    candidate_models = build_toy_candidates()
    candidate_results = []
    for model in candidate_models:
        model.fit(x_train_np, y_train_np)
        cr = model.predict(x_eval)
        candidate_results.append(cr)
        print(f"  {cr.name}: σ = {np.sqrt(cr.noise_var):.4f}")

    instance_names = [cr.name for cr in candidate_results]

    v3_dir = os.path.join(RESULTS_DIR, "v3")
    os.makedirs(v3_dir, exist_ok=True)

    taus = np.logspace(*config.tau_range, config.n_taus)

    for prior_name in args.priors:
        if prior_name not in PRIOR_CONFIGS:
            print(f"WARNING: Unknown prior '{prior_name}', skipping.")
            continue

        prior_config = PRIOR_CONFIGS[prior_name]
        print(f"\n{'═' * 60}")
        print(f"  Prior: {prior_name} — {prior_config.description}")
        print(f"{'═' * 60}")

        # ── Load HMC ──
        cache_path = config.get_cache_path(prior_name)
        if not os.path.exists(cache_path):
            print(f"  ERROR: No cached HMC samples. Run bms_star_toy.py first.")
            continue

        mcmc_samples = load_hmc_samples(cache_path)
        print(f"  Loaded {len(list(mcmc_samples.values())[0])} HMC samples")

        # ── Extract GP predictives ──
        print(f"\n  Extracting GP predictives...")
        kernel_builder = lambda pc=prior_config: build_kernels_from_config(pc)
        likelihood_builder = lambda pc=prior_config: build_likelihood_from_config(pc)

        kernels, names = build_kernels_from_config(prior_config)
        likelihood = build_likelihood_from_config(prior_config)
        gp_model, likelihood = build_model(x_train, y_train, kernels, names, likelihood)

        gp_samples = extract_gp_predictives(
            gp_model, likelihood, x_train, y_train, x_eval_torch,
            mcmc_samples, kernel_builder=kernel_builder,
            likelihood_builder=likelihood_builder,
            n_posterior_samples=config.n_posterior_samples, jitter=1e-4,
        )

        if len(gp_samples) == 0:
            print(f"  WARNING: No valid GP predictives. Skipping.")
            continue

        # ══════════════════════════════════════════════════════════
        # Run original Boltzmann for baseline comparison
        # ══════════════════════════════════════════════════════════
        print(f"\n{'─' * 60}")
        print(f"  BASELINE: Original Boltzmann (v2 metrics)")
        print(f"{'─' * 60}")
        original_results = run_bms_star(
            gp_samples, candidate_results, COMPARISON_METRICS, taus
        )

        # ══════════════════════════════════════════════════════════
        # Strategy 1: Averaged GP Posterior
        # ══════════════════════════════════════════════════════════
        print(f"\n{'─' * 60}")
        print(f"  STRATEGY 1: Averaged GP Posterior")
        print(f"{'─' * 60}")
        averaged_results = score_averaged_gp(
            gp_samples, candidate_results, COMPARISON_METRICS
        )

        # ══════════════════════════════════════════════════════════
        # Strategy 2: Robust Aggregation
        # ══════════════════════════════════════════════════════════
        print(f"\n{'─' * 60}")
        print(f"  STRATEGY 2: Robust Aggregation")
        print(f"{'─' * 60}")
        robust_results = run_robust_aggregation(
            gp_samples, candidate_results, COMPARISON_METRICS
        )

        # ══════════════════════════════════════════════════════════
        # Strategy 3: Marginal Likelihood Weighting
        # ══════════════════════════════════════════════════════════
        print(f"\n{'─' * 60}")
        print(f"  STRATEGY 3: Marginal Likelihood Weighting")
        print(f"{'─' * 60}")

        print(f"\n  Computing log marginal likelihoods...")
        log_mlls = compute_log_marginal_likelihoods(
            gp_samples, x_train, y_train,
            kernel_builder=kernel_builder,
            likelihood_builder=likelihood_builder,
        )

        # Plot MLL distribution
        fig = plot_mll_distribution(log_mlls)
        fig.savefig(os.path.join(v3_dir, f"mll_distribution_{prior_name}.png"),
                    dpi=150, bbox_inches='tight')
        plt.close(fig)

        weighted_results = run_weighted_bms_star(
            gp_samples, candidate_results, log_mlls,
            COMPARISON_METRICS, taus,
        )

        # ══════════════════════════════════════════════════════════
        # PLOTS
        # ══════════════════════════════════════════════════════════
        print(f"\n{'─' * 60}")
        print(f"  Generating comparison plots...")
        print(f"{'─' * 60}")

        # 1. Strategy comparison per metric at each τ
        for tau in args.tau_values:
            fig = plot_all_strategies_grid(
                averaged_results, robust_results, weighted_results,
                original_results, COMPARISON_METRICS, tau=tau,
            )
            tau_str = f"{tau:.1f}".replace('.', 'p')
            fig.savefig(os.path.join(v3_dir,
                        f"strategies_tau{tau_str}_{prior_name}.png"),
                        dpi=150, bbox_inches='tight')
            plt.close(fig)

        # 2. Individual strategy comparison for each metric
        for metric_name in COMPARISON_METRICS:
            for tau in [1.0]:
                fig = plot_strategy_comparison(
                    averaged_results, robust_results, weighted_results,
                    original_results, metric_name=metric_name, tau=tau,
                )
                if fig:
                    fig.savefig(os.path.join(v3_dir,
                                f"strat_{metric_name}_{prior_name}.png"),
                                dpi=150, bbox_inches='tight')
                    plt.close(fig)

        # 3. MLL-weighted τ sensitivity
        fig = plot_weighted_tau_sensitivity(weighted_results)
        fig.savefig(os.path.join(v3_dir, f"tau_weighted_{prior_name}.png"),
                    dpi=150, bbox_inches='tight')
        plt.close(fig)

        # ══════════════════════════════════════════════════════════
        # SUMMARY TABLE
        # ══════════════════════════════════════════════════════════
        print(f"\n{'═' * 75}")
        print(f"  SUMMARY: Which strategy gets Sin+Linear right?")
        print(f"{'─' * 75}")
        print(f"  {'Metric':<22} {'Boltz':>8} {'AvgGP':>8} {'Median':>8} "
              f"{'Trim':>8} {'Rank':>8} {'MLL-Wt':>8}")
        print(f"  {'─' * 75}")

        # Find Sin+Linear index
        sl_idx = next(i for i, n in enumerate(instance_names) if "Sin" in n)

        for metric_name in COMPARISON_METRICS:
            # Boltzmann at τ=1
            taus_orig = sorted(original_results[metric_name].keys())
            closest = min(taus_orig, key=lambda t: abs(t - 1.0))
            p_boltz = original_results[metric_name][closest].instance_posteriors[sl_idx]

            # Averaged GP
            p_avg = averaged_results[metric_name]["posteriors"][sl_idx]

            # Robust
            p_med = robust_results[metric_name]["median"].posteriors[sl_idx]
            p_trim = robust_results[metric_name]["trimmed_mean"].posteriors[sl_idx]
            p_rank = robust_results[metric_name]["rank"].posteriors[sl_idx]

            # Weighted
            taus_w = sorted(weighted_results[metric_name].keys())
            closest_w = min(taus_w, key=lambda t: abs(t - 1.0))
            p_wt = weighted_results[metric_name][closest_w].instance_posteriors[sl_idx]

            # Mark winner (>0.25 = above uniform)
            vals = [p_boltz, p_avg, p_med, p_trim, p_rank, p_wt]
            markers = ["" for _ in vals]
            best_idx = np.argmax(vals)
            if vals[best_idx] > 0.25:
                markers[best_idx] = " ★"

            print(f"  {metric_name:<22} "
                  f"{p_boltz:>7.3f}{markers[0]:1s} "
                  f"{p_avg:>7.3f}{markers[1]:1s} "
                  f"{p_med:>7.3f}{markers[2]:1s} "
                  f"{p_trim:>7.3f}{markers[3]:1s} "
                  f"{p_rank:>7.3f}{markers[4]:1s} "
                  f"{p_wt:>7.3f}{markers[5]:1s}")

        print(f"\n  ★ = Sin+Linear's best posterior (above 0.25 = above uniform)")
        print(f"  Results saved to {v3_dir}/")
        print(f"  Done.")


if __name__ == "__main__":
    main()
