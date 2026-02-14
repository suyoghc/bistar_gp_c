"""
BI* Sample Size Sweep: When Do GP Priors Matter?

Key insight: BI* matters when data alone can't distinguish models.
We show this with three scenarios:

1. STANDARD: sin(x) + 0.25x on [-10, 10], noise=0.3
   → Even n=5 resolves the signal. GP prior is always irrelevant.
   → Shows that BI* doesn't hurt when data is clear.

2. HIGH NOISE: sin(x) + 0.25x on [-10, 10], noise=1.5
   → At small n, models fit similarly. GP prior breaks ties.
   → At large n, data wins. Priors converge.

3. NARROW X: sin(x) + 0.25x on [-3, 3], noise=0.3
   → sin(x) ≈ x on this range, so Linear and Sin+Linear look identical.
   → GP prior (which "knows" about periodicity from kernel) is the tiebreaker.
   → This is the cleanest BI* demonstration.

Usage:
    python experiments/bistar_sample_size_sweep.py --priors informative vague misspecified_tight
"""

import sys, os, argparse
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import torch
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from bistar_gp import generate_toy_data, build_model
from bistar_gp.config import (
    PRIOR_CONFIGS, ExperimentConfig,
    build_kernels_from_config, build_likelihood_from_config,
    load_hmc_samples,
    RESULTS_DIR,
)
from bistar_gp.bms_star import extract_gp_predictives, METRICS
import bistar_gp.metrics_v2

from bistar_gp.aggregation_v3 import average_gp_posterior
from bistar_gp.induced_prior import build_toy_parameter_spaces
from bistar_gp.laplace_evidence import (
    compute_all_laplace_evidences,
    compute_laplace_evidence,
)
from bistar_gp.candidates import (
    LinearModel, SinusoidalModel, SinLinearModel, QuadraticModel,
)

torch.set_default_dtype(torch.float64)


# ── Data Scenarios ──

SCENARIOS = {
    "standard": {
        "description": "Standard toy: clear signal, GP prior irrelevant",
        "x_range": (-10.0, 10.0),
        "noise_std": 0.3,
        "n_full": 50,
    },
    "high_noise": {
        "description": "High noise: ambiguous data, GP prior breaks ties",
        "x_range": (-10.0, 10.0),
        "noise_std": 1.5,
        "n_full": 50,
    },
    "narrow_x": {
        "description": "Narrow range: sin≈x, GP prior identifies periodicity",
        "x_range": (-3.0, 3.0),
        "noise_std": 0.3,
        "n_full": 50,
    },
}


def generate_scenario_data(scenario_name, n_points, seed=42):
    """Generate toy data for a given scenario."""
    sc = SCENARIOS[scenario_name]
    np.random.seed(seed)
    torch.manual_seed(seed)

    x = np.linspace(sc["x_range"][0], sc["x_range"][1], n_points)
    y_true = np.sin(x) + 0.25 * x
    y = y_true + np.random.normal(0, sc["noise_std"], n_points)

    x_t = torch.tensor(x, dtype=torch.float64)
    y_t = torch.tensor(y, dtype=torch.float64)

    return x, y, x_t, y_t


def subsample_data(x_full, y_full, n_sub, seed=42):
    """Stratified subsample preserving x coverage."""
    n_full = len(x_full)
    if n_sub >= n_full:
        return x_full.copy(), y_full.copy()

    indices = np.linspace(0, n_full - 1, n_sub).astype(int)
    return x_full[indices], y_full[indices]


def fit_candidates(x_train, y_train, x_eval):
    """Fit all candidates, return MLE param dicts."""
    models = [LinearModel(), SinusoidalModel(), SinLinearModel(), QuadraticModel()]
    mle_params = {}
    for m in models:
        m.fit(x_train, y_train)
        cr = m.predict(x_eval)
        mle_params[cr.name] = cr.parameters
    return mle_params


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--priors", nargs="+",
                        default=["informative", "vague", "misspecified_tight"])
    parser.add_argument("--metric", default="pw_kl_vcal")
    parser.add_argument("--tau", type=float, default=1.0)
    parser.add_argument("--sample-sizes", type=int, nargs="+",
                        default=[5, 8, 12, 20, 35, 50])
    parser.add_argument("--scenarios", nargs="+",
                        default=["standard", "high_noise", "narrow_x"])
    args = parser.parse_args()

    config = ExperimentConfig()
    param_spaces = build_toy_parameter_spaces()
    model_names = list(param_spaces.keys())

    out_dir = os.path.join(RESULTS_DIR, "sample_size_sweep")
    os.makedirs(out_dir, exist_ok=True)

    # ══════════════════════════════════════════════════════════════
    # First: get averaged GP for each prior (from full n=50 standard data)
    # The GP represents qualitative beliefs formed from prior experience.
    # ══════════════════════════════════════════════════════════════
    x_full, y_full, x_full_t, y_full_t = generate_scenario_data("standard", 50, config.seed)
    x_eval_full = np.linspace(-10, 10, config.n_eval)
    x_eval_full_torch = torch.tensor(x_eval_full, dtype=torch.float64)

    avg_gps = {}
    for prior_name in args.priors:
        if prior_name not in PRIOR_CONFIGS:
            continue

        prior_config = PRIOR_CONFIGS[prior_name]
        cache_path = config.get_cache_path(prior_name)
        if not os.path.exists(cache_path):
            print(f"  No cached HMC for {prior_name}. Skipping.")
            continue

        mcmc_samples = load_hmc_samples(cache_path)
        kernel_builder = lambda pc=prior_config: build_kernels_from_config(pc)
        likelihood_builder = lambda pc=prior_config: build_likelihood_from_config(pc)
        kernels, names = build_kernels_from_config(prior_config)
        likelihood = build_likelihood_from_config(prior_config)
        gp_model, likelihood = build_model(x_full_t, y_full_t, kernels, names, likelihood)

        gp_samples = extract_gp_predictives(
            gp_model, likelihood, x_full_t, y_full_t, x_eval_full_torch,
            mcmc_samples, kernel_builder=kernel_builder,
            likelihood_builder=likelihood_builder,
            n_posterior_samples=config.n_posterior_samples, jitter=1e-4,
        )
        if gp_samples:
            avg_gps[prior_name] = average_gp_posterior(gp_samples)
            print(f"  Averaged GP for {prior_name}: done")

    # ══════════════════════════════════════════════════════════════
    # Sweep: scenario × prior × sample_size
    # ══════════════════════════════════════════════════════════════

    all_posteriors = {}   # scenario → prior → n → {model: posterior}
    all_decomp = {}       # scenario → prior → n → {model: LaplaceResult}

    for scenario_name in args.scenarios:
        sc = SCENARIOS[scenario_name]
        print(f"\n{'═' * 70}")
        print(f"  Scenario: {scenario_name} — {sc['description']}")
        print(f"{'═' * 70}")

        x_sc, y_sc, _, _ = generate_scenario_data(scenario_name, sc["n_full"], config.seed)

        # Eval grid matches scenario x range
        x_eval_sc = np.linspace(sc["x_range"][0], sc["x_range"][1], config.n_eval)

        all_posteriors[scenario_name] = {}
        all_decomp[scenario_name] = {}

        for prior_name in args.priors:
            if prior_name not in avg_gps:
                continue

            # For narrow_x, recompute averaged GP on narrow eval grid
            if scenario_name == "narrow_x":
                x_eval_sc_torch = torch.tensor(x_eval_sc, dtype=torch.float64)
                prior_config = PRIOR_CONFIGS[prior_name]
                mcmc_samples = load_hmc_samples(config.get_cache_path(prior_name))
                kernel_builder = lambda pc=prior_config: build_kernels_from_config(pc)
                likelihood_builder = lambda pc=prior_config: build_likelihood_from_config(pc)
                kernels, names = build_kernels_from_config(prior_config)
                likelihood = build_likelihood_from_config(prior_config)
                gp_model, likelihood = build_model(x_full_t, y_full_t, kernels, names, likelihood)
                gp_samples = extract_gp_predictives(
                    gp_model, likelihood, x_full_t, y_full_t, x_eval_sc_torch,
                    mcmc_samples, kernel_builder=kernel_builder,
                    likelihood_builder=likelihood_builder,
                    n_posterior_samples=config.n_posterior_samples, jitter=1e-4,
                )
                if not gp_samples:
                    continue
                avg_gp_sc = average_gp_posterior(gp_samples)
            else:
                avg_gp_sc = avg_gps[prior_name]

            posteriors_by_n = {}
            decomp_by_n = {}

            for n_sub in args.sample_sizes:
                print(f"\n  {scenario_name} / {prior_name} / n={n_sub}")

                x_sub, y_sub = subsample_data(x_sc, y_sc, n_sub, seed=config.seed)
                mle_params = fit_candidates(x_sub, y_sub, x_eval_sc)

                for mn, ps in param_spaces.items():
                    if mn in mle_params:
                        for spec in ps.param_specs:
                            if spec.name in mle_params[mn]:
                                spec.mle_value = mle_params[mn][spec.name]

                laplace = compute_all_laplace_evidences(
                    param_spaces, x_sub, y_sub, x_eval_sc,
                    avg_gp_sc, mle_params,
                    metric_name=args.metric, tau=args.tau,
                    prior_name=prior_name,
                )

                log_evs = np.array([laplace[m].log_evidence for m in model_names])
                log_evs -= log_evs.max()
                ps = np.exp(log_evs) / np.exp(log_evs).sum()
                posteriors_by_n[n_sub] = dict(zip(model_names, ps))
                decomp_by_n[n_sub] = laplace

            all_posteriors[scenario_name][prior_name] = posteriors_by_n
            all_decomp[scenario_name][prior_name] = decomp_by_n

    # ══════════════════════════════════════════════════════════════
    # PLOTS
    # ══════════════════════════════════════════════════════════════

    colors = {'Linear': '#e74c3c', 'Sinusoidal': '#3498db',
              'Sin+Linear': '#2ecc71', 'Quadratic': '#9b59b6'}
    prior_colors = {
        'informative': '#2ecc71', 'vague': '#3498db',
        'misspecified_tight': '#e74c3c', 'low_noise': '#9b59b6',
        'high_noise': '#f39c12',
    }

    for scenario_name in all_posteriors:
        scenario_data = all_posteriors[scenario_name]
        if not scenario_data:
            continue

        n_priors = len(scenario_data)

        # ── PLOT A: Posteriors vs n (one panel per prior) ──
        fig, axes = plt.subplots(1, n_priors, figsize=(5.5 * n_priors, 5), sharey=True)
        if n_priors == 1:
            axes = [axes]

        for ax, prior_name in zip(axes, scenario_data.keys()):
            pbn = scenario_data[prior_name]
            ns = sorted(pbn.keys())
            for mn in model_names:
                ax.plot(ns, [pbn[n][mn] for n in ns], 'o-',
                        color=colors[mn], linewidth=2.5, markersize=8, label=mn)
            ax.set_xlabel("Sample size n", fontsize=12)
            ax.set_title(f"{prior_name}", fontsize=13, fontweight='bold')
            ax.axhline(0.25, color='gray', linestyle=':', alpha=0.5)
            ax.set_ylim(-0.05, 1.05)
            ax.grid(True, alpha=0.3)
            if ax == axes[0]:
                ax.set_ylabel("Model Posterior", fontsize=12)
            ax.legend(fontsize=9, loc='best')

        sc_desc = SCENARIOS[scenario_name]["description"]
        fig.suptitle(f"BI* Sample Size Sweep: {sc_desc}", fontsize=14)
        fig.tight_layout()
        fig.savefig(os.path.join(out_dir, f"posteriors_vs_n_{scenario_name}.png"),
                    dpi=150, bbox_inches='tight')
        plt.close(fig)

        # ── PLOT B: Sin+Linear convergence across priors ──
        fig, ax = plt.subplots(figsize=(9, 5))
        for pn in scenario_data:
            pbn = scenario_data[pn]
            ns = sorted(pbn.keys())
            sl = [pbn[n].get("Sin+Linear", 0) for n in ns]
            ax.plot(ns, sl, 'o-', color=prior_colors.get(pn, 'gray'),
                    linewidth=2.5, markersize=8, label=pn)
        ax.set_xlabel("Sample size n", fontsize=12)
        ax.set_ylabel("Sin+Linear Posterior", fontsize=12)
        ax.set_title(f"BI* Convergence ({scenario_name}): "
                     f"GP Priors Agree as Data Grows", fontsize=13)
        ax.axhline(0.25, color='gray', linestyle=':', alpha=0.5)
        ax.set_ylim(-0.05, 1.05)
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.savefig(os.path.join(out_dir, f"convergence_{scenario_name}.png"),
                    dpi=150, bbox_inches='tight')
        plt.close(fig)

        # ── PLOT C: Evidence decomposition vs n ──
        first_prior = list(scenario_data.keys())[0]
        if first_prior in all_decomp.get(scenario_name, {}):
            dbn = all_decomp[scenario_name][first_prior]
            ns = sorted(dbn.keys())

            fig, axes = plt.subplots(3, 1, figsize=(10, 12), sharex=True)

            for mn in model_names:
                axes[0].plot(ns, [dbn[n][mn].log_lik_at_map for n in ns],
                             'o-', color=colors[mn], linewidth=2, label=mn)
                axes[1].plot(ns, [dbn[n][mn].prior_penalty for n in ns],
                             'o-', color=colors[mn], linewidth=2, label=mn)

                ratios = []
                for n in ns:
                    lr = dbn[n][mn]
                    total = abs(lr.log_lik_at_map) + abs(lr.prior_penalty) + abs(lr.occam_factor)
                    ratios.append(abs(lr.prior_penalty) / total if total > 0 else 0)
                axes[2].plot(ns, ratios, 'o-', color=colors[mn], linewidth=2, label=mn)

            axes[0].set_ylabel("Data Fit (log lik)", fontsize=11)
            axes[0].set_title(f"Evidence Decomposition ({scenario_name}, {first_prior})",
                              fontsize=13)
            axes[0].legend(fontsize=9)
            axes[0].grid(True, alpha=0.3)

            axes[1].set_ylabel("GP Prior Penalty (-G/τ)", fontsize=11)
            axes[1].legend(fontsize=9)
            axes[1].grid(True, alpha=0.3)

            axes[2].set_xlabel("Sample size n", fontsize=12)
            axes[2].set_ylabel("GP Prior Share", fontsize=11)
            axes[2].set_ylim(0, None)
            axes[2].legend(fontsize=9)
            axes[2].grid(True, alpha=0.3)

            fig.tight_layout()
            fig.savefig(os.path.join(out_dir,
                        f"decomposition_vs_n_{scenario_name}_{first_prior}.png"),
                        dpi=150, bbox_inches='tight')
            plt.close(fig)

    # ── PLOT D: small-n vs large-n across scenarios ──
    small_n = args.sample_sizes[0]
    large_n = args.sample_sizes[-1]
    n_scenarios = len(all_posteriors)

    if n_scenarios > 0:
        fig, axes = plt.subplots(2, n_scenarios, figsize=(5.5 * n_scenarios, 9))
        if n_scenarios == 1:
            axes = axes.reshape(-1, 1)

        for s_idx, scenario_name in enumerate(all_posteriors):
            scenario_data = all_posteriors[scenario_name]
            available_priors = list(scenario_data.keys())
            x_pos = np.arange(len(available_priors))
            bw = 0.8 / len(model_names)

            for row, (n_val, title) in enumerate([(small_n, f"n={small_n}"),
                                                    (large_n, f"n={large_n}")]):
                ax = axes[row, s_idx]
                for m_idx, mn in enumerate(model_names):
                    vals = [scenario_data[pn].get(n_val, {}).get(mn, 0)
                            for pn in available_priors]
                    offset = (m_idx - len(model_names)/2 + 0.5) * bw
                    ax.bar(x_pos + offset, vals, bw, label=mn, color=colors[mn])

                ax.set_xticks(x_pos)
                ax.set_xticklabels(available_priors, fontsize=9)
                ax.set_ylim(0, 1.05)
                ax.axhline(0.25, color='gray', linestyle=':', alpha=0.5)
                ax.grid(True, alpha=0.2, axis='y')

                if s_idx == 0:
                    ax.set_ylabel(f"Model Posterior ({title})", fontsize=10)
                if row == 0:
                    ax.set_title(f"{scenario_name}", fontsize=12, fontweight='bold')
                if row == 0 and s_idx == n_scenarios - 1:
                    ax.legend(fontsize=7, loc='upper right')

        fig.suptitle("BI*: GP Prior Matters at Small n in Ambiguous Scenarios",
                     fontsize=14)
        fig.tight_layout()
        fig.savefig(os.path.join(out_dir, "all_scenarios_comparison.png"),
                    dpi=150, bbox_inches='tight')
        plt.close(fig)

    # ══════════════════════════════════════════════════════════════
    # SUMMARY
    # ══════════════════════════════════════════════════════════════
    print(f"\n{'═' * 80}")
    print(f"  SUMMARY")
    print(f"{'═' * 80}")

    for scenario_name in all_posteriors:
        sc = SCENARIOS[scenario_name]
        print(f"\n  Scenario: {scenario_name} — {sc['description']}")

        for prior_name in all_posteriors[scenario_name]:
            pbn = all_posteriors[scenario_name][prior_name]
            print(f"\n  GP Prior: {prior_name}")
            print(f"  {'n':>4}  {'Linear':>8} {'Sinusoidal':>10} "
                  f"{'Sin+Linear':>10} {'Quadratic':>10}  {'Winner'}")
            print(f"  {'─' * 62}")

            for n in sorted(pbn.keys()):
                ps = pbn[n]
                winner = max(ps, key=ps.get)
                print(f"  {n:>4}", end="")
                for mn in model_names:
                    print(f" {ps[mn]:>9.4f}", end="")
                print(f"   {winner}")

    print(f"\n  Results saved to {out_dir}/")


if __name__ == "__main__":
    main()
