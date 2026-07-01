"""
BI* Induced Prior Demonstration (v2 — Laplace Evidence)

Shows the core BI* mechanism:
  GP kernel priors (qualitative data pattern beliefs)
    → GP posterior
      → Induced priors on parametric model parameters
        → Model selection with Laplace-approximated evidence

Key demonstration:
  Different GP priors → different induced priors → different model selection
  The GP prior penalty term (-G/τ) is what transfers qualitative beliefs.

Usage:
    python experiments/bistar_induced_prior_v2.py --priors informative vague misspecified_tight
    python experiments/bistar_induced_prior_v2.py --priors informative vague misspecified_tight low_noise high_noise
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
from bistar_gp.bms_star import extract_gp_predictives, METRICS

# Register v2 metrics
import bistar_gp.metrics_v2

from bistar_gp.aggregation_v3 import (
    average_gp_posterior,
    compute_log_marginal_likelihoods,
)
from bistar_gp.induced_prior import (
    build_toy_parameter_spaces,
    compute_induced_prior,
    plot_induced_prior_marginals,
    plot_induced_prior_2d,
    plot_prior_comparison_marginals,
    plot_prior_sharpness_summary,
)
from bistar_gp.laplace_evidence import (
    model_posterior,
    plot_evidence_decomposition,
    plot_prior_penalty_comparison,
    plot_model_posteriors_by_prior,
    plot_tau_effect_on_evidence,
    plot_ablation_ladder,
)

torch.set_default_dtype(torch.float64)


def main():
    parser = argparse.ArgumentParser(description="BI* Induced Prior + Laplace Evidence")
    parser.add_argument("--priors", nargs="+",
                        default=["informative", "vague", "misspecified_tight"])
    parser.add_argument("--metric", default="pw_kl_vcal")
    parser.add_argument("--tau", type=float, default=1.0)
    parser.add_argument("--n-param-samples", type=int, default=20000)
    parser.add_argument("--taus-to-show", type=float, nargs="+",
                        default=[0.1, 0.5, 1.0, 5.0])
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

    # ── Candidate MLE fits ──
    print("\nFitting candidate models (MLE)...")
    candidate_models = build_toy_candidates()
    mle_params = {}
    for model in candidate_models:
        model.fit(x_train_np, y_train_np)
        cr = model.predict(x_eval)
        mle_params[cr.name] = cr.parameters
        print(f"  {cr.name}: {cr.parameters}")

    # ── Parameter spaces ──
    param_spaces = build_toy_parameter_spaces()
    for model_name, ps in param_spaces.items():
        if model_name in mle_params:
            for spec in ps.param_specs:
                if spec.name in mle_params[model_name]:
                    spec.mle_value = mle_params[model_name][spec.name]

    # ── Output ──
    out_dir = os.path.join(RESULTS_DIR, "induced_prior_v2")
    os.makedirs(out_dir, exist_ok=True)

    # Storage
    all_induced = {}
    all_laplace = {}
    all_avg_gps = {}

    for prior_name in args.priors:
        if prior_name not in PRIOR_CONFIGS:
            print(f"WARNING: Unknown prior '{prior_name}', skipping.")
            continue

        prior_config = PRIOR_CONFIGS[prior_name]
        print(f"\n{'═' * 65}")
        print(f"  GP Prior: {prior_name} — {prior_config.description}")
        print(f"{'═' * 65}")

        # ── Load HMC ──
        cache_path = config.get_cache_path(prior_name)
        if not os.path.exists(cache_path):
            print(f"  ERROR: No cached HMC. Run bms_star_toy.py first.")
            continue
        mcmc_samples = load_hmc_samples(cache_path)

        # ── Extract GP predictives ──
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
        if not gp_samples:
            continue

        # ── Average GP posterior ──
        avg_gp = average_gp_posterior(gp_samples)
        all_avg_gps[prior_name] = avg_gp

        # ── MLL weights (for induced prior computation) ──
        log_mlls = compute_log_marginal_likelihoods(
            gp_samples, x_train, y_train,
            kernel_builder=kernel_builder,
            likelihood_builder=likelihood_builder,
        )

        # ══════════════════════════════════════════════════════════
        # Part 1: Induced Priors (parameter distributions)
        # ══════════════════════════════════════════════════════════
        print(f"\n{'─' * 60}")
        print(f"  Part 1: GP-Induced Parameter Priors")
        print(f"{'─' * 60}")

        induced_priors = {}
        for model_name, ps in param_spaces.items():
            ip = compute_induced_prior(
                ps, gp_samples, x_eval,
                log_mlls=log_mlls,
                metric_name=args.metric,
                tau=args.tau,
                n_param_samples=args.n_param_samples,
                seed=config.seed,
            )
            ip.prior_name = prior_name
            ip.mle_values = mle_params.get(model_name)
            induced_priors[model_name] = ip

            # Plot marginals
            fig = plot_induced_prior_marginals(ip)
            fig.savefig(os.path.join(out_dir,
                        f"marginals_{model_name}_{prior_name}.png"),
                        dpi=150, bbox_inches='tight')
            plt.close(fig)

        all_induced[prior_name] = induced_priors

        # Sin+Linear 2D plots
        sl_ip = induced_priors.get("Sin+Linear")
        if sl_ip:
            for px, py in [("A", "omega"), ("A", "b")]:
                fig = plot_induced_prior_2d(sl_ip, px, py)
                fig.savefig(os.path.join(out_dir,
                            f"2d_{px}_{py}_{prior_name}.png"),
                            dpi=150, bbox_inches='tight')
                plt.close(fig)

        # ══════════════════════════════════════════════════════════
        # Part 2: Laplace Evidence (model comparison)
        # ══════════════════════════════════════════════════════════
        print(f"\n{'─' * 60}")
        print(f"  Part 2: Laplace Evidence Computation")
        print(f"{'─' * 60}")

        mpr = model_posterior(
            param_spaces, x_train_np, y_train_np, x_eval, avg_gp, mle_params,
            construction="II", metric_name=args.metric, tau=args.tau, occam=False,
        )
        all_laplace[prior_name] = mpr

    # ══════════════════════════════════════════════════════════════
    # Cross-prior comparison plots
    # ══════════════════════════════════════════════════════════════
    if len(all_laplace) >= 2:
        print(f"\n{'═' * 65}")
        print(f"  Cross-Prior Comparison — The BI* Story")
        print(f"{'═' * 65}")

        # 1. Evidence decomposition (the key plot)
        fig = plot_evidence_decomposition(all_laplace)
        fig.savefig(os.path.join(out_dir, "evidence_decomposition.png"),
                    dpi=150, bbox_inches='tight')
        plt.close(fig)

        # 2. GP prior penalty comparison
        fig = plot_prior_penalty_comparison(all_laplace)
        fig.savefig(os.path.join(out_dir, "prior_penalty_comparison.png"),
                    dpi=150, bbox_inches='tight')
        plt.close(fig)

        # 3. Model posteriors
        fig = plot_model_posteriors_by_prior(all_laplace)
        fig.savefig(os.path.join(out_dir, "model_posteriors_laplace.png"),
                    dpi=150, bbox_inches='tight')
        plt.close(fig)

        # 4. ESS from induced priors
        fig = plot_prior_sharpness_summary(all_induced)
        fig.savefig(os.path.join(out_dir, "ess_sharpness.png"),
                    dpi=150, bbox_inches='tight')
        plt.close(fig)

        # 5. Cross-prior parameter comparisons
        for model_name in param_spaces:
            priors_for_model = {pn: all_induced[pn][model_name]
                                for pn in all_induced}
            for param_name in param_spaces[model_name].param_names:
                if param_name == "sigma":
                    continue
                fig = plot_prior_comparison_marginals(priors_for_model, param_name)
                fig.savefig(os.path.join(out_dir,
                            f"compare_{model_name}_{param_name}.png"),
                            dpi=150, bbox_inches='tight')
                plt.close(fig)

    # ══════════════════════════════════════════════════════════════
    # τ sensitivity (Laplace evidence version)
    # ══════════════════════════════════════════════════════════════
    for prior_name in args.priors:
        if prior_name not in all_avg_gps:
            continue

        print(f"\n{'─' * 60}")
        print(f"  τ Sensitivity — Laplace Evidence ({prior_name})")
        print(f"{'─' * 60}")

        fig = plot_tau_effect_on_evidence(
            param_spaces, x_train_np, y_train_np, x_eval,
            all_avg_gps[prior_name], mle_params,
            metric_name=args.metric,
            taus=np.logspace(-1, 2, 20),
            prior_name=prior_name,
        )
        fig.savefig(os.path.join(out_dir, f"tau_laplace_{prior_name}.png"),
                    dpi=150, bbox_inches='tight')
        plt.close(fig)

        # Ablation ladder: baseline / Construction I / Construction II (DECISIONS D3).
        fig = plot_ablation_ladder(
            param_spaces, x_train_np, y_train_np, x_eval,
            all_avg_gps[prior_name], mle_params,
            metric_name=args.metric, tau=args.tau, prior_name=prior_name,
        )
        fig.savefig(os.path.join(out_dir, f"ablation_ladder_{prior_name}.png"),
                    dpi=150, bbox_inches='tight')
        plt.close(fig)

    # ══════════════════════════════════════════════════════════════
    # SUMMARY TABLE
    # ══════════════════════════════════════════════════════════════
    print(f"\n{'═' * 80}")
    print(f"  SUMMARY: BI* Evidence Decomposition")
    print(f"{'═' * 80}")

    if all_laplace:
        model_names = list(param_spaces.keys())

        # Table 1: Evidence components
        print(f"\n  log N(M) = Data Fit + GP Prior Penalty + Occam  (Construction II)")
        print(f"  {'Prior':<18} {'Model':<15} {'Fit':>8} {'GP Prior':>10} "
              f"{'Occam':>8} {'log N':>10} {'Post':>8}")
        print(f"  {'─' * 80}")

        for prior_name, mpr in all_laplace.items():
            posteriors = np.array([mpr.posteriors[m] for m in model_names])
            for model_name in model_names:
                c = mpr.components[model_name]
                marker = " ★" if mpr.posteriors[model_name] == posteriors.max() else ""
                print(f"  {prior_name:<18} {model_name:<15} "
                      f"{c['log_lik_at_map']:>8.1f} {c['gp_penalty']:>10.2f} "
                      f"{c['occam']:>8.1f} {c['log_N']:>10.1f} "
                      f"{mpr.posteriors[model_name]:>7.4f}{marker}")
            print()

        # Table 2: Just posteriors
        print(f"\n  Model Posteriors:")
        print(f"  {'Prior':<22} {'Linear':>8} {'Sinusoidal':>10} "
              f"{'Sin+Linear':>10} {'Quadratic':>10}")
        print(f"  {'─' * 62}")

        for prior_name, mpr in all_laplace.items():
            print(f"  {prior_name:<22}", end="")
            for m in model_names:
                print(f" {mpr.posteriors[m]:>9.4f}", end="")
            print()

    print(f"\n  Results saved to {out_dir}/")
    print(f"  Done.")


if __name__ == "__main__":
    main()
