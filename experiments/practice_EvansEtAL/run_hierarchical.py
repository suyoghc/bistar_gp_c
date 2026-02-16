"""
Hierarchical GP experiment for law of practice.

Usage:
    python run_hierarchical.py --demo --kernel rbf
    python run_hierarchical.py --demo --kernel matern32
    python run_hierarchical.py --demo --kernel matern52
    python run_hierarchical.py --demo --kernel rbf --kernel matern32  # compare both

Runs the full pipeline:
  1. Generate/load data
  2. MAP fit all subjects → population prior
  3. HMC per subject with population priors
  4. Extract GP predictives → score candidates → aggregate
"""

import argparse
import json
import numpy as np
import torch
import sys
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from candidates import build_core_candidates
from hierarchical import (
    run_hierarchical_pipeline, build_hierarchical_kernel,
    PopulationPrior,
)
from run import generate_demo_data, normalize, NormalizedCurve
from bistar_gp.model import build_model
from bistar_gp.fit import fit_map
from bistar_gp.bms_star import (
    extract_gp_predictives, compute_G_matrix, soft_transfer,
    GPPosteriorSample,
)

torch.set_default_dtype(torch.float64)


def extract_predictives_for_subject(mcmc_samples, model, lik,
                                    x_train, y_train, x_eval,
                                    pop_prior, kernel_type,
                                    n_posterior_samples=100):
    """Extract GP predictive draws using hierarchical kernel builder."""
    kernel_builder, lik_builder = build_hierarchical_kernel(
        pop_prior, kernel_type
    )
    samples = extract_gp_predictives(
        model, lik, x_train, y_train, x_eval,
        mcmc_samples, kernel_builder, lik_builder,
        n_posterior_samples=n_posterior_samples,
    )
    return samples


def score_subject(gp_samples_raw, candidate_results,
                  metrics=None, taus=None):
    """Score one subject: G matrix → soft transfer → winners."""
    if metrics is None:
        metrics = ["pw_mse", "pw_hellinger", "pw_nll"]
    if taus is None:
        taus = np.logspace(-1, 2, 20)

    results = {}
    for metric in metrics:
        G = compute_G_matrix(gp_samples_raw, candidate_results, metric)
        results[metric] = {}
        for tau in taus:
            bms = soft_transfer(G, tau, [cr.name for cr in candidate_results])
            bms.metric_name = metric
            winner_idx = np.argmax(bms.instance_posteriors)
            results[metric][float(tau)] = {
                "winner": bms.instance_names[winner_idx],
                "posteriors": {
                    name: float(p) for name, p in
                    zip(bms.instance_names, bms.instance_posteriors)
                },
            }
    return results


def run_experiment(kernel_types, n_hmc_samples=200, n_warmup=100,
                   output_dir="results_hierarchical"):
    """Run full hierarchical experiment."""
    import os
    os.makedirs(output_dir, exist_ok=True)

    # Generate data
    print("Generating demo data...")
    curves = generate_demo_data(50)
    normalized = [normalize(c) for c in curves]

    # Prepare normalized data tuples
    subjects_data = [(nc.x, nc.y) for nc in normalized]

    for kernel_type in kernel_types:
        print(f"\n{'#'*60}")
        print(f"# Kernel: {kernel_type}")
        print(f"{'#'*60}")

        # Run hierarchical pipeline
        pop_prior, subject_results = run_hierarchical_pipeline(
            subjects_data, kernel_type=kernel_type,
            n_hmc_samples=n_hmc_samples, n_warmup=n_warmup,
            verbose=False,
        )

        # Save population prior
        pop_dict = {
            "kernel_type": kernel_type,
            "ls_mu": pop_prior.ls_mu, "ls_sigma": pop_prior.ls_sigma,
            "os_mu": pop_prior.os_mu, "os_sigma": pop_prior.os_sigma,
            "noise_mu": pop_prior.noise_mu, "noise_sigma": pop_prior.noise_sigma,
            "n_subjects": pop_prior.n_subjects,
            "ls_range": [float(pop_prior.lengthscales.min()),
                         float(pop_prior.lengthscales.max())],
            "os_range": [float(pop_prior.outputscales.min()),
                         float(pop_prior.outputscales.max())],
            "noise_range": [float(pop_prior.noises.min()),
                            float(pop_prior.noises.max())],
        }
        with open(f"{output_dir}/population_prior_{kernel_type}.json", "w") as f:
            json.dump(pop_dict, f, indent=2)
        pop_prior.summary()

        # Score each subject
        all_results = []
        n_power_correct = 0
        n_exp_correct = 0

        for i, nc in enumerate(normalized):
            if i % 10 == 0:
                print(f"\n  Scoring subject {i}/{len(normalized)}...")

            mcmc, model, lik = subject_results[i]
            x_train = torch.tensor(nc.x).double()
            y_train = torch.tensor(nc.y).double()
            x_eval = torch.linspace(0, 1, 50).double()
            x_eval_raw = x_eval.numpy() * (nc.x_max - nc.x_min) + nc.x_min

            # GP predictives
            gp_samples = extract_predictives_for_subject(
                mcmc, model, lik, x_train, y_train, x_eval,
                pop_prior, kernel_type, n_posterior_samples=100,
            )

            # Denormalize
            gp_raw = [
                GPPosteriorSample(
                    mean=s.mean * nc.y_std + nc.y_mean,
                    cov=s.cov * (nc.y_std ** 2),
                    hyperparameters=s.hyperparameters,
                )
                for s in gp_samples
            ]

            # Candidates on raw data
            candidates = build_core_candidates()
            crs = []
            for c in candidates:
                c.fit(nc.x_raw, nc.y_raw)
                crs.append(c.predict(x_eval_raw))

            # BIC
            from scipy.stats import norm as scipy_norm
            bic_results = {}
            for c in candidates:
                c.fit(nc.x_raw, nc.y_raw)
                pred = c.predict(nc.x_raw)
                residuals = nc.y_raw - pred.mean
                n = len(nc.y_raw)
                k = len(pred.parameters)
                sigma2 = np.sum(residuals**2) / n
                ll = -0.5 * n * np.log(2 * np.pi * sigma2) - 0.5 * n
                bic = k * np.log(n) - 2 * ll
                bic_results[c.name] = float(bic)
            bic_winner = min(bic_results, key=bic_results.get)

            # BI* scoring
            bistar_results = score_subject(gp_raw, crs)

            # Determine ground truth
            curve = curves[i]
            true_model = "Power" if "power" in curve.dataset_id else "Exponential"

            # Track accuracy (use pw_nll, median tau)
            taus = sorted(bistar_results["pw_nll"].keys())
            mid_tau = taus[len(taus)//2]
            bistar_winner = bistar_results["pw_nll"][mid_tau]["winner"]

            if true_model == "Power" and bistar_winner == "Power":
                n_power_correct += 1
            elif true_model == "Exponential" and bistar_winner == "Exponential":
                n_exp_correct += 1

            # HMC lengthscale stats
            ls_key = [k for k in mcmc.keys() if 'lengthscale' in k]
            ls_stats = {}
            if ls_key:
                ls_vals = np.array(mcmc[ls_key[0]])
                ls_stats = {
                    "mean": float(ls_vals.mean()),
                    "std": float(ls_vals.std()),
                    "min": float(ls_vals.min()),
                    "max": float(ls_vals.max()),
                }

            subj_result = {
                "subject_id": i,
                "true_model": true_model,
                "n_trials": int(curve.n_trials),
                "kernel_type": kernel_type,
                "bic_winner": bic_winner,
                "bic_scores": bic_results,
                "bistar_winners": {},
                "hmc_lengthscale": ls_stats,
            }

            for metric in bistar_results:
                subj_result["bistar_winners"][metric] = {}
                for tau_val in bistar_results[metric]:
                    subj_result["bistar_winners"][metric][str(tau_val)] = \
                        bistar_results[metric][tau_val]

            all_results.append(subj_result)

            # Save per-subject
            fname = f"sub_{i:02d}_{true_model.lower()}_{kernel_type}.json"
            with open(f"{output_dir}/{fname}", "w") as f:
                json.dump(subj_result, f, indent=2, default=str)

        # Summary
        n_power = sum(1 for c in curves if c.true_model == "Power")
        n_exp = sum(1 for c in curves if c.true_model == "Exponential")

        print(f"\n{'='*60}")
        print(f"RESULTS: {kernel_type} hierarchical")
        print(f"{'='*60}")
        print(f"Power recovery:       {n_power_correct}/{n_power}")
        print(f"Exponential recovery: {n_exp_correct}/{n_exp}")
        print(f"Total accuracy:       {n_power_correct + n_exp_correct}/{n_power + n_exp}")

        # BIC comparison
        bic_power = sum(
            1 for r in all_results
            if r["true_model"] == "Power" and r["bic_winner"] == "Power"
        )
        bic_exp = sum(
            1 for r in all_results
            if r["true_model"] == "Exponential" and r["bic_winner"] == "Exponential"
        )
        print(f"\nBIC baseline:")
        print(f"  Power:       {bic_power}/{n_power}")
        print(f"  Exponential: {bic_exp}/{n_exp}")
        print(f"  Total:       {bic_power + bic_exp}/{n_power + n_exp}")

        # Save summary
        summary = {
            "kernel_type": kernel_type,
            "n_subjects": len(curves),
            "n_hmc_samples": n_hmc_samples,
            "bistar_pw_nll": {
                "power_correct": n_power_correct,
                "power_total": n_power,
                "exp_correct": n_exp_correct,
                "exp_total": n_exp,
                "total_correct": n_power_correct + n_exp_correct,
            },
            "bic": {
                "power_correct": bic_power,
                "exp_correct": bic_exp,
                "total_correct": bic_power + bic_exp,
            },
            "population_prior": pop_dict,
        }
        with open(f"{output_dir}/summary_{kernel_type}.json", "w") as f:
            json.dump(summary, f, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true",
                        help="Use synthetic demo data (50 subjects)")
    parser.add_argument("--kernel", action="append", default=[],
                        choices=["rbf", "matern32", "matern52"],
                        help="Kernel types to test (can repeat)")
    parser.add_argument("--n_hmc_samples", type=int, default=200)
    parser.add_argument("--n_warmup", type=int, default=100)
    parser.add_argument("--output_dir", type=str,
                        default="results_hierarchical")
    args = parser.parse_args()

    if not args.demo:
        print("Only --demo mode implemented so far")
        sys.exit(1)

    kernel_types = args.kernel if args.kernel else ["rbf"]

    run_experiment(
        kernel_types=kernel_types,
        n_hmc_samples=args.n_hmc_samples,
        n_warmup=args.n_warmup,
        output_dir=args.output_dir,
    )
