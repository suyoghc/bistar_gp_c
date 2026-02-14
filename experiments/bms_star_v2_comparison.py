"""
BMS* V2 Metrics Comparison

Runs the new calibrated metrics alongside the originals using cached
HMC samples. No re-running of HMC needed — this is pure post-processing.

Produces:
  1. G-matrix diagnostics for ALL metrics (original + v2)
  2. τ sensitivity curves for v2 metrics
  3. Side-by-side bar chart: mean G per candidate, original vs calibrated
  4. Combined comparison plot at selected τ values

Usage:
    python experiments/bms_star_v2_comparison.py
    python experiments/bms_star_v2_comparison.py --priors informative
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
    load_hmc_samples,
    RESULTS_DIR,
)
from bistar_gp.bms_star import (
    extract_gp_predictives,
    run_bms_star,
    compute_G_matrix,
    soft_transfer,
    plot_bms_star_results,
    print_bms_star_table,
    METRICS,
)

# Import v2 metrics — this registers them into METRICS
from bistar_gp.metrics_v2 import (
    METRICS_V2,
    diagnose_all_metrics,
    diagnose_G_matrix,
    plot_G_diagnostic_comparison,
    plot_v2_tau_sensitivity,
)

torch.set_default_dtype(torch.float64)


def plot_combined_tau_comparison(gp_samples, candidate_results, taus=None, figsize=None):
    """
    Side-by-side τ sensitivity: original pointwise metrics (left columns)
    vs calibrated v2 metrics (right columns).

    Pairs:
      pw_kl_forward    vs  pw_kl_vcal
      pw_hellinger     vs  pw_hellinger_vcal
      pw_hellinger     vs  pw_hellinger_mean
      pw_nll           vs  pw_nll_gp
      pw_mse           vs  pw_nmse
    """
    if taus is None:
        taus = np.logspace(-1, 2, 30)

    pairs = [
        ("pw_kl_forward",   "pw_kl_vcal",        "KL Forward → KL Var-Cal"),
        ("pw_kl_symmetric", "pw_kl_sym_vcal",     "KL Symmetric → KL Sym Var-Cal"),
        ("pw_hellinger",    "pw_hellinger_vcal",   "Hellinger → Hellinger Var-Cal"),
        ("pw_hellinger",    "pw_hellinger_mean",   "Hellinger → Hellinger Mean-Only"),
        ("pw_nll",          "pw_nll_gp",           "NLL(ψ under θ) → NLL(θ under ψ)"),
        ("pw_mse",          "pw_nmse",             "MSE → Normalized MSE"),
    ]

    instance_names = [cr.name for cr in candidate_results]
    colors = ['#e74c3c', '#3498db', '#2ecc71', '#9b59b6']

    nrows = len(pairs)
    if figsize is None:
        figsize = (12, 3 * nrows)

    fig, axes = plt.subplots(nrows, 2, figsize=figsize, sharey='row')

    for row_idx, (orig_name, v2_name, label) in enumerate(pairs):
        for col_idx, metric_name in enumerate([orig_name, v2_name]):
            ax = axes[row_idx, col_idx]

            print(f"  Computing: {metric_name}...")
            G = compute_G_matrix(gp_samples, candidate_results, metric_name)

            posteriors = np.zeros((len(taus), len(instance_names)))
            for t_idx, tau in enumerate(taus):
                bms = soft_transfer(G, tau, instance_names)
                posteriors[t_idx] = bms.instance_posteriors

            for m_idx, name in enumerate(instance_names):
                ax.plot(taus, posteriors[:, m_idx], color=colors[m_idx],
                        linewidth=2, label=name)

            ax.set_xscale('log')
            ax.set_ylim(0, 1)
            ax.set_title(metric_name, fontsize=10,
                         fontweight='bold' if col_idx == 1 else 'normal')
            ax.grid(True, alpha=0.3)

            if col_idx == 0:
                ax.set_ylabel(label.split('→')[0].strip(), fontsize=8)
            if row_idx == nrows - 1:
                ax.set_xlabel('τ (temperature)', fontsize=9)
            if row_idx == 0 and col_idx == 1:
                ax.legend(fontsize=7, loc='upper right')

    fig.suptitle("Original (left) vs Calibrated (right) — τ Sensitivity",
                 fontsize=14, fontweight='bold')
    fig.tight_layout()
    return fig


def plot_posterior_comparison_bars(gp_samples, candidate_results, tau=1.0):
    """
    Bar chart at a fixed τ: posterior per candidate, one group per metric.
    Shows all original PW metrics and all v2 metrics.
    """
    instance_names = [cr.name for cr in candidate_results]
    colors = ['#e74c3c', '#3498db', '#2ecc71', '#9b59b6']

    original_pw = ["pw_kl_forward", "pw_kl_backward", "pw_kl_symmetric",
                   "pw_hellinger", "pw_mse", "pw_nll"]
    v2_list = list(METRICS_V2.keys())
    all_metrics = original_pw + v2_list

    posteriors_by_metric = {}
    for metric_name in all_metrics:
        G = compute_G_matrix(gp_samples, candidate_results, metric_name)
        bms = soft_transfer(G, tau, instance_names)
        posteriors_by_metric[metric_name] = bms.instance_posteriors

    n_metrics = len(all_metrics)
    n_models = len(instance_names)
    fig, ax = plt.subplots(figsize=(max(14, n_metrics * 1.2), 5))

    x = np.arange(n_metrics)
    width = 0.8 / n_models

    for m_idx, model_name in enumerate(instance_names):
        vals = [posteriors_by_metric[m][m_idx] for m in all_metrics]
        offset = (m_idx - n_models / 2 + 0.5) * width
        ax.bar(x + offset, vals, width, label=model_name,
               color=colors[m_idx % len(colors)])

    # Visual separator between original and v2
    sep_x = len(original_pw) - 0.5
    ax.axvline(sep_x, color='black', linestyle='--', alpha=0.5, linewidth=1)
    ax.text(sep_x - 0.3, 0.95, "Original ←", ha='right', fontsize=8,
            transform=ax.get_xaxis_transform())
    ax.text(sep_x + 0.3, 0.95, "→ Calibrated (v2)", ha='left', fontsize=8,
            transform=ax.get_xaxis_transform())

    ax.set_xticks(x)
    ax.set_xticklabels(all_metrics, rotation=45, ha='right', fontsize=8)
    ax.set_ylabel("Posterior probability")
    ax.set_title(f"BMS* Posteriors at τ = {tau:.1f} — All Metrics", fontsize=13)
    ax.set_ylim(0, 1)
    ax.legend(fontsize=9, loc='upper left')
    ax.grid(True, alpha=0.2, axis='y')

    fig.tight_layout()
    return fig


def main():
    parser = argparse.ArgumentParser(description="BMS* V2 metrics comparison")
    parser.add_argument("--priors", nargs="+", default=["informative"],
                        help="Which prior configs to analyze")
    parser.add_argument("--tau-comparison", type=float, nargs="+", default=[0.5, 1.0, 5.0],
                        help="τ values for bar chart comparison")
    args = parser.parse_args()

    config = ExperimentConfig()

    # ── Generate data ──
    np.random.seed(config.seed)
    torch.manual_seed(config.seed)
    x_train, y_train, _ = generate_toy_data(
        n_points=config.n_points, noise_std=config.noise_std,
        bias_slope=config.bias_slope, seed=config.seed,
    )
    x_train_np = x_train.numpy()
    y_train_np = y_train.numpy()
    x_eval = np.linspace(*config.x_range, config.n_eval)
    x_eval_torch = torch.tensor(x_eval, dtype=torch.float64)

    # ── Fit candidates ──
    print("\nFitting candidate models...")
    candidate_models = build_toy_candidates()
    candidate_results = []
    
    for model in candidate_models:
        model.fit(x_train_np, y_train_np)
        cr = model.predict(x_eval)       # x_eval is already numpy (from np.linspace)
        candidate_results.append(cr)
        print(f"  {cr.name}: σ = {np.sqrt(cr.noise_var):.4f}, params = {cr.parameters}")

    instance_names = [cr.name for cr in candidate_results]

    os.makedirs(RESULTS_DIR, exist_ok=True)
    os.makedirs(os.path.join(RESULTS_DIR, "v2"), exist_ok=True)

    for prior_name in args.priors:
        if prior_name not in PRIOR_CONFIGS:
            print(f"WARNING: Unknown prior '{prior_name}', skipping.")
            continue

        prior_config = PRIOR_CONFIGS[prior_name]
        print(f"\n{'═' * 60}")
        print(f"  Prior: {prior_name} — {prior_config.description}")
        print(f"{'═' * 60}")

        # ── Load cached HMC samples ──
        cache_path = config.get_cache_path(prior_name)
        if not os.path.exists(cache_path):
            print(f"  ERROR: No cached HMC samples at {cache_path}")
            print(f"  Run bms_star_toy.py first to generate samples.")
            continue

        mcmc_samples = load_hmc_samples(cache_path)
        print(f"  Loaded {len(list(mcmc_samples.values())[0])} HMC samples from cache")

        # ── Extract GP predictives ──
        print(f"  Extracting GP predictives...")
        kernel_builder = lambda: build_kernels_from_config(prior_config)
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
            print(f"  WARNING: No valid GP predictives. Skipping.")
            continue

        # ──────────────────────────────────────────────────────────
        # 1. DIAGNOSTICS: G-matrix stats for ALL metrics
        # ──────────────────────────────────────────────────────────
        print(f"\n{'─' * 60}")
        print(f"  DIAGNOSTICS — All Metrics")
        print(f"{'─' * 60}")

        # Only pointwise + v2 (skip joint KL — we know it's dominated by covariance)
        diag_metrics = [
            "pw_kl_forward", "pw_kl_backward", "pw_kl_symmetric",
            "pw_hellinger", "pw_mse", "pw_nll",
        ] + list(METRICS_V2.keys())

        all_stats = diagnose_all_metrics(gp_samples, candidate_results, diag_metrics)

        # Save diagnostic bar chart
        fig = plot_G_diagnostic_comparison(all_stats, instance_names,
                                           metric_groups={
                                               "Original Pointwise": [
                                                   "pw_kl_forward", "pw_kl_backward",
                                                   "pw_kl_symmetric", "pw_hellinger",
                                                   "pw_mse", "pw_nll",
                                               ],
                                               "V2 Calibrated": list(METRICS_V2.keys()),
                                           })
        fig.savefig(os.path.join(RESULTS_DIR, "v2",
                    f"G_diagnostic_{prior_name}.png"), dpi=150, bbox_inches='tight')
        plt.close(fig)

        # ──────────────────────────────────────────────────────────
        # 2. τ SENSITIVITY: V2 metrics
        # ──────────────────────────────────────────────────────────
        print(f"\n  Computing v2 τ sensitivity curves...")
        taus = np.logspace(*config.tau_range, config.n_taus)

        fig = plot_v2_tau_sensitivity(gp_samples, candidate_results, taus)
        fig.savefig(os.path.join(RESULTS_DIR, "v2",
                    f"tau_v2_{prior_name}.png"), dpi=150, bbox_inches='tight')
        plt.close(fig)

        # ──────────────────────────────────────────────────────────
        # 3. SIDE-BY-SIDE: Original vs Calibrated τ curves
        # ──────────────────────────────────────────────────────────
        print(f"\n  Computing side-by-side comparison...")
        fig = plot_combined_tau_comparison(gp_samples, candidate_results, taus)
        fig.savefig(os.path.join(RESULTS_DIR, "v2",
                    f"tau_comparison_{prior_name}.png"), dpi=150, bbox_inches='tight')
        plt.close(fig)

        # ──────────────────────────────────────────────────────────
        # 4. BAR CHARTS: Posteriors at fixed τ, all metrics
        # ──────────────────────────────────────────────────────────
        for tau in args.tau_comparison:
            print(f"\n  Posterior comparison at τ = {tau}...")
            fig = plot_posterior_comparison_bars(gp_samples, candidate_results, tau)
            tau_str = f"{tau:.1f}".replace('.', 'p')
            fig.savefig(os.path.join(RESULTS_DIR, "v2",
                        f"posteriors_tau{tau_str}_{prior_name}.png"),
                        dpi=150, bbox_inches='tight')
            plt.close(fig)

        # ──────────────────────────────────────────────────────────
        # 5. FULL BMS* RUN with v2 metrics (for tables)
        # ──────────────────────────────────────────────────────────
        print(f"\n  Running BMS* with v2 metrics...")
        v2_results = run_bms_star(gp_samples, candidate_results,
                                   list(METRICS_V2.keys()), taus)

        for tau in args.tau_comparison:
            print_bms_star_table(v2_results, tau)

    print(f"\n  Results saved to {os.path.join(RESULTS_DIR, 'v2')}/")
    print("  Done.")


if __name__ == "__main__":
    main()
