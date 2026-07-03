"""
BMS* on Mauna Loa CO2: Which parametric trend model best explains the data?

Candidates:
  1. Linear trend + sinusoidal seasonal
  2. Quadratic trend + sinusoidal seasonal
  3. Exponential trend + sinusoidal seasonal

The GP decomposes into trend + seasonal + medium-term (sum kernel).
BMS* scores each parametric candidate against the GP posterior (HMC draws).

Expected result: Quadratic or Exponential wins (CO2 growth is accelerating).

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
from scipy.optimize import minimize, differential_evolution

from bistar_gp import load_mauna_loa, build_model
from bistar_gp.model import build_mauna_loa_kernels, build_likelihood
from bistar_gp.fit import fit_map, print_hyperparameters, fit_hmc
from bistar_gp.candidates import CandidateModel, CandidateResult
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
# Mauna Loa Candidate Models
# ═══════════════════════════════════════════════════════════════════
#
# Each candidate captures: trend(t) + seasonal(t) + noise
# The GP has 3 additive components. Candidates are simpler parametric
# approximations of the full signal. BMS* measures which parametric
# form best matches the GP posterior.

class LinearSeasonalModel(CandidateModel):
    """
    y = a*t + b + A*sin(2π*t/P + φ₁) + B*cos(4π*t/P + φ₂) + ε

    Linear trend + first two Fourier harmonics for seasonal cycle.
    Two harmonics needed because CO2 seasonal is asymmetric
    (sharp spring drawdown, gradual fall release).
    """
    name = "Linear+Seasonal"

    def __init__(self):
        self.params_ = None
        self.sigma = 1.0

    def _predict_fn(self, x, p):
        a, b, A1, P, phi1, A2, phi2 = p
        return a * x + b + A1 * np.sin(2 * np.pi * x / P + phi1) + \
               A2 * np.cos(4 * np.pi * x / P + phi2)

    def fit(self, x, y):
        def neg_ll(params):
            p = params[:-1]
            log_sigma = params[-1]
            sigma2 = np.exp(2 * log_sigma)
            mu = self._predict_fn(x, p)
            residuals = y - mu
            n = len(y)
            return 0.5 * n * np.log(2 * np.pi * sigma2) + 0.5 * np.sum(residuals**2) / sigma2

        # Estimate initial values
        # Linear trend from endpoints
        a_init = (y[-1] - y[0]) / (x[-1] - x[0]) if len(x) > 1 else 0.0
        b_init = np.mean(y) - a_init * np.mean(x)

        bounds = [
            (a_init * 0.5, a_init * 2.0),   # a (slope)
            (b_init - 1.0, b_init + 1.0),    # b (intercept)
            (0.01, 1.0),                      # A1 (seasonal amplitude)
            (0.9, 1.1),                       # P (period ~ 1 year)
            (-np.pi, np.pi),                  # phi1
            (0.001, 0.5),                     # A2 (2nd harmonic)
            (-np.pi, np.pi),                  # phi2
            (np.log(0.01), np.log(1.0)),      # log(sigma)
        ]

        result = differential_evolution(neg_ll, bounds, seed=42, maxiter=500,
                                        tol=1e-8, polish=True)
        self.params_ = result.x[:-1]
        self.sigma = np.exp(result.x[-1])

    def predict(self, x_eval):
        mean = self._predict_fn(x_eval, self.params_)
        return self._make_result(
            x_eval, mean, self.sigma**2,
            {f"p{i}": float(v) for i, v in enumerate(self.params_)},
        )


class QuadraticSeasonalModel(CandidateModel):
    """
    y = a*t² + b*t + c + A*sin(2π*t/P + φ₁) + B*cos(4π*t/P + φ₂) + ε

    Quadratic trend captures the observed acceleration in CO2 growth.
    Should outperform linear. The 'correct' answer for Mauna Loa.
    """
    name = "Quadratic+Seasonal"

    def __init__(self):
        self.params_ = None
        self.sigma = 1.0

    def _predict_fn(self, x, p):
        a, b, c, A1, P, phi1, A2, phi2 = p
        return a * x**2 + b * x + c + A1 * np.sin(2 * np.pi * x / P + phi1) + \
               A2 * np.cos(4 * np.pi * x / P + phi2)

    def fit(self, x, y):
        def neg_ll(params):
            p = params[:-1]
            log_sigma = params[-1]
            sigma2 = np.exp(2 * log_sigma)
            mu = self._predict_fn(x, p)
            residuals = y - mu
            n = len(y)
            return 0.5 * n * np.log(2 * np.pi * sigma2) + 0.5 * np.sum(residuals**2) / sigma2

        # Polyfit for initial estimates
        coeffs = np.polyfit(x, y, 2)
        a_init, b_init, c_init = coeffs

        bounds = [
            (a_init * 0.1, a_init * 5.0) if a_init > 0 else (a_init * 5.0, a_init * 0.1),
            (b_init - 1.0, b_init + 1.0),
            (c_init - 1.0, c_init + 1.0),
            (0.01, 1.0),                       # A1
            (0.9, 1.1),                         # P
            (-np.pi, np.pi),                    # phi1
            (0.001, 0.5),                       # A2
            (-np.pi, np.pi),                    # phi2
            (np.log(0.001), np.log(0.5)),       # log(sigma)
        ]

        result = differential_evolution(neg_ll, bounds, seed=42, maxiter=500,
                                        tol=1e-8, polish=True)
        self.params_ = result.x[:-1]
        self.sigma = np.exp(result.x[-1])

    def predict(self, x_eval):
        mean = self._predict_fn(x_eval, self.params_)
        return self._make_result(
            x_eval, mean, self.sigma**2,
            {f"p{i}": float(v) for i, v in enumerate(self.params_)},
        )


class ExponentialSeasonalModel(CandidateModel):
    """
    y = a*exp(b*t) + c + A*sin(2π*t/P + φ₁) + B*cos(4π*t/P + φ₂) + ε

    Exponential trend — models accelerating growth as compound process.
    Similar to quadratic over the observed range but diverges in extrapolation.
    """
    name = "Exponential+Seasonal"

    def __init__(self):
        self.params_ = None
        self.sigma = 1.0

    def _predict_fn(self, x, p):
        a, b, c, A1, P, phi1, A2, phi2 = p
        # Clamp to avoid overflow
        exponent = np.clip(b * x, -50, 50)
        return a * np.exp(exponent) + c + A1 * np.sin(2 * np.pi * x / P + phi1) + \
               A2 * np.cos(4 * np.pi * x / P + phi2)

    def fit(self, x, y):
        def neg_ll(params):
            p = params[:-1]
            log_sigma = params[-1]
            sigma2 = np.exp(2 * log_sigma)
            try:
                mu = self._predict_fn(x, p)
                if not np.all(np.isfinite(mu)):
                    return 1e10
                residuals = y - mu
                n = len(y)
                return 0.5 * n * np.log(2 * np.pi * sigma2) + 0.5 * np.sum(residuals**2) / sigma2
            except (OverflowError, FloatingPointError):
                return 1e10

        bounds = [
            (0.01, 10.0),                      # a (amplitude)
            (0.001, 0.2),                       # b (growth rate)
            (-5.0, 5.0),                        # c (offset)
            (0.01, 1.0),                        # A1
            (0.9, 1.1),                         # P
            (-np.pi, np.pi),                    # phi1
            (0.001, 0.5),                       # A2
            (-np.pi, np.pi),                    # phi2
            (np.log(0.001), np.log(0.5)),       # log(sigma)
        ]

        result = differential_evolution(neg_ll, bounds, seed=42, maxiter=500,
                                        tol=1e-8, polish=True)
        self.params_ = result.x[:-1]
        self.sigma = np.exp(result.x[-1])

    def predict(self, x_eval):
        mean = self._predict_fn(x_eval, self.params_)
        return self._make_result(
            x_eval, mean, self.sigma**2,
            {f"p{i}": float(v) for i, v in enumerate(self.params_)},
        )


def build_mauna_loa_candidates():
    """Return all 3 candidate trend models for Mauna Loa BMS*."""
    return [
        LinearSeasonalModel(),
        QuadraticSeasonalModel(),
        ExponentialSeasonalModel(),
    ]


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
    print("  Candidates: Linear, Quadratic, Exponential (all + Seasonal)")
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
    candidates = build_mauna_loa_candidates()
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
    metrics = ["pw_mse", "pw_nll", "pw_hellinger", "pw_kl_forward", "pw_kl_symmetric"]
    taus = np.logspace(-1, 2, 25)
    results = run_bms_star(gp_samples, candidate_results, metrics, taus)

    # Print results at key τ values
    for tau in [0.5, 1.0, 5.0, 10.0]:
        print_bms_star_table(results, tau)

    # ── 7. Save results ───────────────────────────────────────────
    print("\n── Saving Results ──")

    # Summary JSON
    summary = {"n_gp_samples": len(gp_samples), "n_candidates": len(candidate_results)}
    for metric_name in metrics:
        taus_sorted = sorted(results[metric_name].keys())
        mid_tau = taus_sorted[len(taus_sorted) // 2]
        bms = results[metric_name][mid_tau]
        summary[metric_name] = {
            "tau": float(mid_tau),
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
