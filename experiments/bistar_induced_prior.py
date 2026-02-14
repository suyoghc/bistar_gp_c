"""
BI* Induced Prior Demonstration

Shows the core BI* mechanism:
  GP kernel priors (qualitative data pattern beliefs)
    → GP posterior
      → Induced priors on parametric model parameters
        → Model selection with informed priors

Key demonstration:
  Different GP priors → different induced priors → different model selection behavior
  - Informative prior: sharp induced prior, concentrates near true parameters
  - Vague prior: diffuse induced prior, less discriminative
  - Misspecified prior: biased induced prior, may mislead

This is what makes BI* different from standard BIC/AIC:
  the nonparametric GP acts as a bridge between qualitative beliefs
  (expressed through kernel choice) and quantitative model priors.

Usage:
    python experiments/bistar_induced_prior.py --priors informative vague misspecified_tight
    python experiments/bistar_induced_prior.py --priors informative vague misspecified_tight low_noise high_noise
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

from bistar_gp.aggregation_v3 import compute_log_marginal_likelihoods
from bistar_gp.induced_prior import (
    build_toy_parameter_spaces,
    compute_induced_prior,
    compute_all_model_evidences,
    plot_induced_prior_marginals,
    plot_induced_prior_2d,
    plot_prior_comparison_marginals,
    plot_evidence_comparison,
    plot_prior_sharpness_summary,
)

torch.set_default_dtype(torch.float64)


def main():
    parser = argparse.ArgumentParser(description="BI* Induced Prior Demonstration")
    parser.add_argument("--priors", nargs="+",
                        default=["informative", "vague", "misspecified_tight"])
    parser.add_argument("--metric", default="pw_kl_vcal",
                        help="Divergence metric for induced prior")
    parser.add_argument("--tau", type=float, default=1.0,
                        help="Temperature for induced prior transfer")
    parser.add_argument("--n-param-samples", type=int, default=20000,
                        help="Number of parameter samples for induced prior")
    parser.add_argument("--taus-to-show", type=float, nargs="+",
                        default=[0.5, 1.0, 5.0],
                        help="Multiple τ values to compare")
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

    # ── Candidate MLE fits (for reference) ──
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

    # Set MLE values for visualization
    for model_name, ps in param_spaces.items():
        if model_name in mle_params:
            for spec in ps.param_specs:
                if spec.name in mle_params[model_name]:
                    spec.mle_value = mle_params[model_name][spec.name]

    # ── Output directory ──
    out_dir = os.path.join(RESULTS_DIR, "induced_prior")
    os.makedirs(out_dir, exist_ok=True)

    # Storage for cross-prior comparison
    all_induced = {}           # prior_name → {model_name → InducedPriorResult}
    all_evidences = {}         # prior_name → {model_name → log_evidence}

    for prior_name in args.priors:
        if prior_name not in PRIOR_CONFIGS:
            print(f"WARNING: Unknown prior '{prior_name}', skipping.")
            continue

        prior_config = PRIOR_CONFIGS[prior_name]
        print(f"\n{'═' * 65}")
        print(f"  GP Prior: {prior_name} — {prior_config.description}")
        print(f"{'═' * 65}")

        # ── Load cached HMC ──
        cache_path = config.get_cache_path(prior_name)
        if not os.path.exists(cache_path):
            print(f"  ERROR: No cached HMC samples. Run bms_star_toy.py first.")
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

        # ── Compute MLL weights ──
        print(f"\n  Computing log marginal likelihoods...")
        log_mlls = compute_log_marginal_likelihoods(
            gp_samples, x_train, y_train,
            kernel_builder=kernel_builder,
            likelihood_builder=likelihood_builder,
        )

        # ── Compute induced priors for all candidates ──
        induced_priors = {}
        for model_name, ps in param_spaces.items():
            print(f"\n  Computing induced prior for {model_name}...")
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

        all_induced[prior_name] = induced_priors

        # ── Per-prior plots ──

        # 1. Marginal distributions for each model
        for model_name, ip in induced_priors.items():
            fig = plot_induced_prior_marginals(ip)
            fig.savefig(os.path.join(out_dir,
                        f"marginals_{model_name}_{prior_name}.png"),
                        dpi=150, bbox_inches='tight')
            plt.close(fig)

        # 2. 2D scatter for Sin+Linear (A vs omega, b vs A)
        sl_ip = induced_priors.get("Sin+Linear")
        if sl_ip:
            for px, py in [("A", "omega"), ("A", "b"), ("omega", "b")]:
                fig = plot_induced_prior_2d(sl_ip, px, py)
                fig.savefig(os.path.join(out_dir,
                            f"2d_{px}_{py}_{prior_name}.png"),
                            dpi=150, bbox_inches='tight')
                plt.close(fig)

        # ── Model evidence under induced priors ──
        print(f"\n{'─' * 60}")
        print(f"  Model Evidence under GP-Induced Priors ({prior_name})")
        print(f"{'─' * 60}")
        evidences = compute_all_model_evidences(
            induced_priors, x_train_np, y_train_np, param_spaces,
        )
        all_evidences[prior_name] = evidences

    # ══════════════════════════════════════════════════════════════
    # Cross-prior comparison plots (the key BI* demonstration)
    # ══════════════════════════════════════════════════════════════
    if len(all_induced) >= 2:
        print(f"\n{'═' * 65}")
        print(f"  Cross-Prior Comparison — The BI* Story")
        print(f"{'═' * 65}")

        # 3. Prior comparison: same parameter, different GP priors
        for model_name in param_spaces:
            priors_for_model = {pn: all_induced[pn][model_name]
                                for pn in all_induced
                                if model_name in all_induced[pn]}

            for param_name in param_spaces[model_name].param_names:
                if param_name == "sigma":
                    continue  # skip noise, not interesting
                fig = plot_prior_comparison_marginals(
                    priors_for_model, param_name
                )
                fig.savefig(os.path.join(out_dir,
                            f"compare_{model_name}_{param_name}.png"),
                            dpi=150, bbox_inches='tight')
                plt.close(fig)

        # 4. Model evidence comparison across priors
        if all_evidences:
            fig = plot_evidence_comparison(all_evidences)
            fig.savefig(os.path.join(out_dir, "evidence_comparison.png"),
                        dpi=150, bbox_inches='tight')
            plt.close(fig)

        # 5. ESS (sharpness of information transfer)
        fig = plot_prior_sharpness_summary(all_induced)
        fig.savefig(os.path.join(out_dir, "ess_sharpness.png"),
                    dpi=150, bbox_inches='tight')
        plt.close(fig)

    # ══════════════════════════════════════════════════════════════
    # τ sensitivity: how temperature affects the induced prior
    # ══════════════════════════════════════════════════════════════
    if len(args.taus_to_show) > 1 and "informative" in all_induced:
        print(f"\n{'─' * 60}")
        print(f"  τ Sensitivity for Induced Priors (informative)")
        print(f"{'─' * 60}")

        # Recompute Sin+Linear induced prior at different τ values
        prior_name = "informative"
        prior_config = PRIOR_CONFIGS[prior_name]
        kernel_builder = lambda pc=prior_config: build_kernels_from_config(pc)
        likelihood_builder = lambda pc=prior_config: build_likelihood_from_config(pc)

        mcmc_samples = load_hmc_samples(config.get_cache_path(prior_name))
        kernels, names = build_kernels_from_config(prior_config)
        likelihood = build_likelihood_from_config(prior_config)
        gp_model, likelihood = build_model(x_train, y_train, kernels, names, likelihood)
        gp_samples = extract_gp_predictives(
            gp_model, likelihood, x_train, y_train, x_eval_torch,
            mcmc_samples, kernel_builder=kernel_builder,
            likelihood_builder=likelihood_builder,
            n_posterior_samples=config.n_posterior_samples, jitter=1e-4,
        )
        log_mlls = compute_log_marginal_likelihoods(
            gp_samples, x_train, y_train,
            kernel_builder=kernel_builder,
            likelihood_builder=likelihood_builder,
        )

        sl_space = param_spaces["Sin+Linear"]
        tau_induced = {}
        for tau_val in args.taus_to_show:
            print(f"\n  τ = {tau_val}:")
            ip = compute_induced_prior(
                sl_space, gp_samples, x_eval,
                log_mlls=log_mlls,
                metric_name=args.metric,
                tau=tau_val,
                n_param_samples=args.n_param_samples,
                seed=config.seed,
            )
            ip.prior_name = f"informative_tau{tau_val}"
            ip.mle_values = mle_params.get("Sin+Linear")
            tau_induced[tau_val] = ip

        # Plot: how τ shapes the induced prior for key parameters
        for param_name in ["A", "omega", "b"]:
            fig, axes = plt.subplots(1, len(args.taus_to_show),
                                     figsize=(5 * len(args.taus_to_show), 4))
            if len(args.taus_to_show) == 1:
                axes = [axes]

            j = sl_space.param_names.index(param_name)
            true_val = sl_space.param_specs[j].true_value

            for ax, tau_val in zip(axes, args.taus_to_show):
                ip = tau_induced[tau_val]
                vals = ip.param_samples[:, j]
                w = ip.weights

                ax.hist(vals, bins=50, density=True, alpha=0.3, color='gray',
                        label='Reference')
                ax.hist(vals, bins=50, weights=w, density=True, alpha=0.6,
                        color='steelblue', label='Induced')
                if true_val is not None:
                    ax.axvline(true_val, color='red', linestyle='--',
                               linewidth=2, label=f'True={true_val}')
                ax.set_title(f"τ = {tau_val}", fontsize=12)
                ax.set_xlabel(param_name, fontsize=11)
                ax.legend(fontsize=7)
                ax.grid(True, alpha=0.2)

            fig.suptitle(f"Sin+Linear '{param_name}': τ Controls Transfer Sharpness",
                         fontsize=13)
            fig.tight_layout()
            fig.savefig(os.path.join(out_dir,
                        f"tau_sensitivity_{param_name}.png"),
                        dpi=150, bbox_inches='tight')
            plt.close(fig)

    # ══════════════════════════════════════════════════════════════
    # SUMMARY
    # ══════════════════════════════════════════════════════════════
    print(f"\n{'═' * 65}")
    print(f"  SUMMARY: GP Prior → Induced Parameter Prior → Model Selection")
    print(f"{'═' * 65}")

    if all_evidences:
        print(f"\n  Model Posteriors (under GP-induced priors):")
        print(f"  {'Prior':<22} {'Linear':>8} {'Sinusoidal':>10} "
              f"{'Sin+Linear':>10} {'Quadratic':>10}")
        print(f"  {'─' * 62}")

        for prior_name, evs in all_evidences.items():
            log_evs = np.array(list(evs.values()))
            log_evs -= log_evs.max()
            ps = np.exp(log_evs) / np.exp(log_evs).sum()
            names = list(evs.keys())
            print(f"  {prior_name:<22}", end="")
            for p in ps:
                print(f" {p:>9.4f}", end="")
            print()

    print(f"\n  Results saved to {out_dir}/")
    print(f"  Done.")


if __name__ == "__main__":
    main()
