"""
BMS* Experiment on Mauna Loa CO2 Data

Transfers GP hyperparameter beliefs into parametric model priors for:
  Linear        (2 params)  — constant growth, no season
  Quadratic     (3 params)  — accelerating growth, no season
  Quad+Sin      (5 params)  — accelerating + annual sinusoid
  Quad+2Harm    (7 params)  — accelerating + annual + semi-annual

GP kernel: trend (long-ℓ RBF) + seasonal (periodic P=1yr) + medium-term (mid-ℓ RBF)

Each run creates a self-contained directory under runs/ with:
  config.json, command.sh, samples/, results/, data/

Usage:
    # Quick MAP test
    python bms_star_mauna_loa.py --mode map

    # Full HMC, subsample for speed
    python bms_star_mauna_loa.py --mode hmc --subsample 150 --tag sub150

    # Full HMC, all data
    python bms_star_mauna_loa.py --mode hmc --tag full

    # Reuse samples from a previous run for new model comparison
    python bms_star_mauna_loa.py --load-run mauna_loa_sub150_hmc_20260215_1430

    # List all past runs
    python bms_star_mauna_loa.py --list-runs
"""

import sys, os, argparse, io
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import torch
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from bistar_gp import load_mauna_loa, build_model, build_likelihood
from bistar_gp.model import build_mauna_loa_kernels
from bistar_gp.fit import fit_map, fit_hmc, print_hyperparameters
from bistar_gp.mauna_loa_candidates import build_mauna_loa_candidates
from bistar_gp.bms_star import (
    extract_gp_predictives, GPPosteriorSample,
    run_bms_star,
    plot_bms_star_results,
    plot_G_heatmaps,
    plot_candidate_predictions,
    print_bms_star_table,
)
from bistar_gp.run_manager import (
    make_run_name, create_run_dir, find_run_dir,
    save_run_config, save_command,
    save_samples, load_samples,
    save_gp_predictives, load_gp_predictives,
    save_training_data, save_bms_tables,
    print_runs,
)

torch.set_default_dtype(torch.float64)


# ═══════════════════════════════════════════════════════════════════
# HMC-safe kernel builder (Positive constraints for Pyro)
# ═══════════════════════════════════════════════════════════════════

def build_mauna_loa_kernels_hmc():
    import gpytorch
    from gpytorch.kernels import ScaleKernel, RBFKernel, PeriodicKernel
    from gpytorch.constraints import Positive
    from gpytorch.priors import GammaPrior, LogNormalPrior

    trend = ScaleKernel(
        RBFKernel(
            lengthscale_constraint=Positive(),
            lengthscale_prior=LogNormalPrior(4.0, 1.0),
        ),
        outputscale_constraint=Positive(),
        outputscale_prior=GammaPrior(4.0, 0.5),
    )
    seasonal = ScaleKernel(
        PeriodicKernel(
            period_length_constraint=Positive(),
            period_length_prior=LogNormalPrior(0.0, 0.01),
            lengthscale_constraint=Positive(),
            lengthscale_prior=GammaPrior(3.0, 2.0),
        ),
        outputscale_constraint=Positive(),
        outputscale_prior=GammaPrior(3.0, 1.0),
    )
    seasonal.base_kernel.period_length = 1.0
    medium = ScaleKernel(
        RBFKernel(
            lengthscale_constraint=Positive(),
            lengthscale_prior=GammaPrior(3.0, 1.0),
        ),
        outputscale_constraint=Positive(),
        outputscale_prior=GammaPrior(2.0, 1.0),
    )
    return [trend, seasonal, medium], ["trend", "seasonal", "medium_term"]


def build_mauna_loa_likelihood_hmc():
    import gpytorch
    from gpytorch.constraints import Positive
    from gpytorch.priors import GammaPrior
    return gpytorch.likelihoods.GaussianLikelihood(
        noise_constraint=Positive(),
        noise_prior=GammaPrior(1.75, 1.0),
    )


# ═══════════════════════════════════════════════════════════════════
# MAP-based GP predictive extraction
# ═══════════════════════════════════════════════════════════════════

def extract_gp_predictives_map(model, likelihood, x_train, y_train, x_eval,
                                jitter=1e-4):
    from bistar_gp.decompose import compute_cholesky

    x_train = x_train.double() if isinstance(x_train, torch.Tensor) else torch.tensor(x_train).double()
    y_train = y_train.double() if isinstance(y_train, torch.Tensor) else torch.tensor(y_train).double()
    x_eval = x_eval.double() if isinstance(x_eval, torch.Tensor) else torch.tensor(x_eval).double()

    model.eval()
    likelihood.eval()

    with torch.no_grad():
        noise_var = likelihood.noise.item()
        K_XX = model.covar_module(x_train, x_train).evaluate().detach()
        K_XstarX = model.covar_module(x_eval, x_train).evaluate().detach()
        K_XstarXstar = model.covar_module(x_eval, x_eval).evaluate().detach()
        K_XXstar = model.covar_module(x_train, x_eval).evaluate().detach()

        L = compute_cholesky(K_XX, noise_var, jitter)
        alpha = torch.cholesky_solve(y_train.unsqueeze(-1), L).squeeze(-1)
        pred_mean = (K_XstarX @ alpha).numpy()
        V = torch.linalg.solve_triangular(L, K_XXstar, upper=False)
        pred_cov = (K_XstarXstar - V.T @ V).numpy()
        pred_cov += noise_var * np.eye(len(x_eval))

        hp_dict = {}
        for name, param in model.named_parameters():
            hp_dict[name] = param.item()
        hp_dict["noise"] = noise_var

    print(f"  Extracted 1 GP predictive (MAP)")
    return [GPPosteriorSample(mean=pred_mean, cov=pred_cov, hyperparameters=hp_dict)]


# ═══════════════════════════════════════════════════════════════════
# Plotting
# ═══════════════════════════════════════════════════════════════════

def plot_candidates_vs_data(x_eval, candidate_results, x_train_np, y_train_np,
                             x_test_np=None, y_test_np=None):
    fig, axes = plt.subplots(2, 2, figsize=(14, 10), sharex=True, sharey=True)
    colors = ["#e74c3c", "#3498db", "#2ecc71", "#9b59b6"]
    for ax, cr, color in zip(axes.flatten(), candidate_results, colors):
        ax.scatter(x_train_np, y_train_np, s=3, alpha=0.3, color="gray", label="Train")
        if x_test_np is not None:
            ax.scatter(x_test_np, y_test_np, s=5, alpha=0.5, color="red",
                       marker=".", label="Test")
        ax.plot(x_eval, cr.mean, color=color, linewidth=1.5, label=cr.name)
        sd = cr.noise_var ** 0.5
        ax.fill_between(x_eval, cr.mean - 2 * sd, cr.mean + 2 * sd,
                         alpha=0.15, color=color)
        ax.set_title(f"{cr.name}  (σ={sd:.4f}, {len(cr.parameters)-1} params)")
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.2)
    fig.suptitle("Candidate Models — MLE Fits to Mauna Loa CO₂", fontsize=14)
    fig.tight_layout()
    return fig


def plot_gp_vs_candidates(x_eval, gp_samples, candidate_results,
                           x_train_np, y_train_np):
    fig, ax = plt.subplots(figsize=(14, 6))
    gp_means = np.array([s.mean for s in gp_samples])
    gp_mean = gp_means.mean(axis=0)
    gp_std = gp_means.std(axis=0)
    ax.fill_between(x_eval, gp_mean - 2 * gp_std, gp_mean + 2 * gp_std,
                     alpha=0.2, color="gray", label="GP ±2σ (across ψ)")
    ax.plot(x_eval, gp_mean, color="black", linewidth=1, alpha=0.7, label="GP mean")
    colors = ["#e74c3c", "#3498db", "#2ecc71", "#9b59b6"]
    for cr, color in zip(candidate_results, colors):
        ax.plot(x_eval, cr.mean, color=color, linewidth=1.2, label=cr.name, alpha=0.8)
    ax.scatter(x_train_np, y_train_np, s=3, alpha=0.2, color="gray", zorder=0)
    ax.set_xlabel("Time (normalized)")
    ax.set_ylabel("CO₂ (normalized)")
    ax.set_title("GP Predictive vs Candidate Models")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.2)
    fig.tight_layout()
    return fig


# ═══════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="BMS* on Mauna Loa CO₂")
    parser.add_argument("--mode", choices=["map", "hmc"], default="map",
                        help="MAP (fast, 1 GP sample) or HMC (slow, many samples)")
    parser.add_argument("--force-rerun", action="store_true",
                        help="Rerun HMC even if samples exist in run dir")
    parser.add_argument("--tag", type=str, default=None,
                        help="Tag for run name (e.g. 'sub150', 'full', 'prior_vague')")
    parser.add_argument("--run-name", type=str, default=None,
                        help="Explicit run name (overrides auto-generated)")
    parser.add_argument("--load-run", type=str, default=None,
                        help="Load samples from a previous run (name or prefix)")
    parser.add_argument("--list-runs", action="store_true",
                        help="List all past runs and exit")

    # Data
    parser.add_argument("--test-years", type=float, default=5.0)
    parser.add_argument("--subsample", type=int, default=None,
                        help="Subsample training data to this many points")

    # GP
    parser.add_argument("--n-eval", type=int, default=120)
    parser.add_argument("--n-hmc", type=int, default=300)
    parser.add_argument("--n-warmup", type=int, default=200)
    parser.add_argument("--n-posterior", type=int, default=100)

    # BMS*
    parser.add_argument("--n-taus", type=int, default=30)
    parser.add_argument("--log-tau-min", type=float, default=-1.0)
    parser.add_argument("--log-tau-max", type=float, default=2.0)

    args = parser.parse_args()

    # ── List runs mode ───────────────────────────────────────────
    if args.list_runs:
        print("\n── Past Runs ──")
        print_runs(experiment_filter="mauna_loa")
        return

    # ── Create or load run directory ─────────────────────────────
    if args.load_run:
        run_dir = find_run_dir(args.load_run)
        if run_dir is None:
            print(f"ERROR: Run '{args.load_run}' not found.")
            print_runs(experiment_filter="mauna_loa")
            return
        run_name = os.path.basename(run_dir)
        print(f"\n  Loading from previous run: {run_name}")
    else:
        if args.run_name:
            run_name = args.run_name
        else:
            tag = args.tag
            if tag is None and args.subsample:
                tag = f"sub{args.subsample}"
            run_name = make_run_name("mauna_loa", args.mode, tag)
        run_dir = create_run_dir(run_name)

    results_dir = os.path.join(run_dir, "results")

    print("=" * 60)
    print("  BMS* Experiment: Mauna Loa CO₂")
    print("=" * 60)
    print(f"  Run:       {run_name}")
    print(f"  Run dir:   {run_dir}")
    print(f"  Mode:      {args.mode}")
    print(f"  Eval pts:  {args.n_eval}")
    if args.subsample:
        print(f"  Subsample: {args.subsample}")
    if args.mode == "hmc":
        print(f"  HMC:       {args.n_hmc} samples, {args.n_warmup} warmup")
        print(f"  Posterior: {args.n_posterior} GP samples for BMS*")

    # Save config and command
    if not args.load_run:
        save_command(run_dir)

    # ── 1. Load data ─────────────────────────────────────────────
    print("\n── Loading Data ──")
    x_train, y_train, x_test, y_test, info = load_mauna_loa(
        normalize=True, test_years=args.test_years,
    )
    x_train_np, y_train_np = x_train.numpy(), y_train.numpy()
    x_test_np, y_test_np = x_test.numpy(), y_test.numpy()

    print(f"  Train: {len(x_train)} points, x=[{x_train_np.min():.1f}, {x_train_np.max():.1f}]")
    print(f"  Test:  {len(x_test)} points")
    print(f"  Normalization: y_mean={info['y_mean']:.1f} ppm, y_std={info['y_std']:.1f} ppm")

    # Subsample if requested
    if args.subsample and args.subsample < len(x_train):
        rng = np.random.RandomState(42)
        idx = rng.choice(len(x_train), args.subsample, replace=False)
        idx.sort()
        x_train = x_train[idx]
        y_train = y_train[idx]
        x_train_np, y_train_np = x_train.numpy(), y_train.numpy()
        print(f"  Subsampled to {len(x_train)} points")

    # Save training data and config
    if not args.load_run:
        save_training_data(run_dir, x_train_np, y_train_np, info)
        save_run_config(run_dir, args, extra={
            "n_train": len(x_train),
            "n_test": len(x_test),
            "y_mean": info["y_mean"],
            "y_std": info["y_std"],
        })

    # Eval grid
    x_eval = np.linspace(x_train_np.min(), x_train_np.max(), args.n_eval)
    x_eval_torch = torch.tensor(x_eval).double()

    # ── 2. Fit candidate models ──────────────────────────────────
    print("\n── Fitting Candidate Models ──")
    candidates = build_mauna_loa_candidates()
    candidate_results = []
    for cand in candidates:
        cand.fit(x_train_np, y_train_np)
        cr = cand.predict(x_eval)
        candidate_results.append(cr)
        n_params = len(cr.parameters) - 1
        print(f"  {cr.name:<15} σ={cr.noise_var**0.5:.4f}  ({n_params} params)")
        for pname, pval in cr.parameters.items():
            if pname != "sigma":
                print(f"    {pname:>6} = {pval:.6f}")

    # ── 3. Get GP predictives ────────────────────────────────────
    print(f"\n── GP Predictives ({args.mode.upper()}) ──")

    if args.load_run:
        gp_samples = load_gp_predictives(run_dir)

    elif args.mode == "map":
        kernels, names = build_mauna_loa_kernels()
        likelihood = build_likelihood()
        model, likelihood = build_model(x_train, y_train, kernels, names, likelihood)
        fit_map(model, likelihood, x_train, y_train, n_iter=800, lr=0.02, print_every=200)
        print_hyperparameters(model, likelihood)
        gp_samples = extract_gp_predictives_map(
            model, likelihood, x_train, y_train, x_eval_torch,
        )
        save_gp_predictives(run_dir, gp_samples)

    elif args.mode == "hmc":
        samples_path = os.path.join(run_dir, "samples", "hmc_samples.npz")
        if not args.force_rerun and os.path.exists(samples_path):
            mcmc_samples = load_samples(run_dir)
        else:
            print(f"\n  Running HMC ({args.n_hmc} samples, {args.n_warmup} warmup)...")
            print(f"  Data: {len(x_train)} points")

            kernels, names = build_mauna_loa_kernels_hmc()
            likelihood = build_mauna_loa_likelihood_hmc()
            model, likelihood = build_model(x_train, y_train, kernels, names, likelihood)
            print("  MAP initialization...")
            fit_map(model, likelihood, x_train, y_train, n_iter=500, lr=0.02, print_every=100)

            kernels2, names2 = build_mauna_loa_kernels_hmc()
            likelihood2 = build_mauna_loa_likelihood_hmc()
            model2, likelihood2 = build_model(x_train, y_train, kernels2, names2, likelihood2)

            mcmc_samples = fit_hmc(
                model2, likelihood2, x_train, y_train,
                n_samples=args.n_hmc, n_warmup=args.n_warmup,
            )

            for k, v in mcmc_samples.items():
                print(f"    {k}: mean={v.mean():.4f}, std={v.std():.4f}")

            save_samples(run_dir, mcmc_samples)

        kernels, names = build_mauna_loa_kernels_hmc()
        likelihood = build_mauna_loa_likelihood_hmc()
        model, likelihood = build_model(x_train, y_train, kernels, names, likelihood)

        gp_samples = extract_gp_predictives(
            model, likelihood, x_train, y_train, x_eval_torch,
            mcmc_samples,
            kernel_builder=build_mauna_loa_kernels_hmc,
            likelihood_builder=build_mauna_loa_likelihood_hmc,
            n_posterior_samples=args.n_posterior,
            jitter=1e-4,
        )
        save_gp_predictives(run_dir, gp_samples)

    if len(gp_samples) == 0:
        print("ERROR: No valid GP predictives. Aborting.")
        return

    # ── 4. Run BMS* ──────────────────────────────────────────────
    print(f"\n── BMS* ({len(gp_samples)} ψ samples) ──")
    taus = np.logspace(args.log_tau_min, args.log_tau_max, args.n_taus)

    metrics = [
        "pw_kl_forward", "pw_kl_backward", "pw_kl_symmetric",
        "pw_hellinger", "pw_mse", "pw_nll",
    ]
    if len(x_eval) <= 120:
        metrics = [
            "kl_forward", "kl_backward", "kl_symmetric", "hellinger",
        ] + metrics

    results = run_bms_star(gp_samples, candidate_results, metrics, taus)

    # Capture BMS tables
    table_buf = io.StringIO()
    _orig_stdout = sys.stdout
    for tau in [0.5, 1.0, 5.0, 10.0]:
        sys.stdout = table_buf
        print_bms_star_table(results, tau)
        sys.stdout = _orig_stdout
        print_bms_star_table(results, tau)
    save_bms_tables(run_dir, table_buf.getvalue())

    # ── 5. Plots ─────────────────────────────────────────────────
    print("\n── Generating Plots ──")
    prefix = f"mauna_loa_{args.mode}"

    def _save(fig, name):
        path = os.path.join(results_dir, f"{prefix}_{name}.png")
        fig.savefig(path, bbox_inches="tight", dpi=150)
        print(f"  Saved: {path}")

    fig1 = plot_candidates_vs_data(
        x_eval, candidate_results, x_train_np, y_train_np, x_test_np, y_test_np)
    _save(fig1, "candidates")

    fig2 = plot_gp_vs_candidates(
        x_eval, gp_samples, candidate_results, x_train_np, y_train_np)
    _save(fig2, "gp_vs_cands")

    pw_results = {k: v for k, v in results.items() if k.startswith("pw_")}
    if pw_results:
        fig3 = plot_bms_star_results(pw_results)
        fig3.suptitle(f"Pointwise Metrics — Mauna Loa ({args.mode.upper()})", fontsize=14)
        _save(fig3, "tau_pointwise")

    joint_results = {k: v for k, v in results.items() if not k.startswith("pw_")}
    if joint_results:
        fig4 = plot_bms_star_results(joint_results)
        fig4.suptitle(f"Joint Metrics — Mauna Loa ({args.mode.upper()})", fontsize=14)
        _save(fig4, "tau_joint")

    fig5 = plot_G_heatmaps(results)
    _save(fig5, "G_heatmaps")

    fig6 = plot_candidate_predictions(
        x_eval, gp_samples, candidate_results, x_train_np, y_train_np)
    fig6.suptitle(f"Candidates vs GP — Mauna Loa ({args.mode.upper()})", fontsize=14)
    _save(fig6, "cand_overlay")

    plt.close("all")

    # ── 6. Summary ───────────────────────────────────────────────
    print(f"\n── Summary ──")
    print(f"  Run:         {run_name}")
    print(f"  Run dir:     {run_dir}")
    print(f"  Mode:        {args.mode}")
    print(f"  GP samples:  {len(gp_samples)}")
    print(f"  Eval points: {args.n_eval}")

    print(f"\n  Candidate complexity ladder:")
    for cr in candidate_results:
        n_p = len(cr.parameters) - 1
        print(f"    {cr.name:<15} {n_p} params, σ_MLE = {cr.noise_var**0.5:.4f}")

    print(f"\n  All outputs in: {run_dir}")
    print(f"  To reuse these samples:  python bms_star_mauna_loa.py --load-run {run_name}")
    print(f"  To list all runs:        python bms_star_mauna_loa.py --list-runs")
    print(f"\n  Done!")


if __name__ == "__main__":
    main()
