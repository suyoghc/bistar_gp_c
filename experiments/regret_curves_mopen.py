#!/usr/bin/env python3
"""Reconstruct Case D deviation curves from the frozen practice artifacts.

The script does not fit candidates, optimize GP hyperparameters, or run HMC.
It regenerates the seeded synthetic observations, verifies the stored BIC
values from the stored candidate parameters, conditions an exact GP at the
stored practitioner MAP hyperparameters, and evaluates two absolute-deviation
estimands on the common first-20-trial grid.
"""

from __future__ import annotations

import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np
import torch

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
PRACTICE_DIR = ROOT / "experiments" / "practice_EvansEtAL"
SOURCE_DIR = PRACTICE_DIR / "results_hmc"
OUTPUT_DIR = ROOT / "runs" / "regret_curves_mopen"

DATA_SEED = 42
DRAW_SEED_BASE = 20_260_811
N_SUBJECTS = 50
N_DRAWS = 100
TRIAL_GRID = np.arange(1.0, 21.0)
BIC_ABS_TOL = 1e-8
CONDITIONING_JITTER = 1e-6
PSD_ABS_TOL = 1e-8
FIGURE_SIZE_LIMIT = 2_000_000

# Importing the read-only practice modules must not update their bytecode.
sys.dont_write_bytecode = True
sys.path.insert(0, str(PRACTICE_DIR))
import run as practice_run  # noqa: E402
from candidates import ExponentialModel, PowerModel  # noqa: E402
from kernels import PRACTICE_CONFIGS, build_kernel, build_likelihood  # noqa: E402


def _json_ready(value: Any) -> Any:
    """Convert numpy containers and scalars to strict JSON values."""
    if isinstance(value, dict):
        return {str(k): _json_ready(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(v) for v in value]
    if isinstance(value, np.ndarray):
        return [_json_ready(v) for v in value.tolist()]
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, (np.floating, float)):
        value = float(value)
        if not math.isfinite(value):
            raise ValueError(f"Non-finite JSON value: {value}")
        return value
    if isinstance(value, (np.integer, int)):
        return int(value)
    return value


def _summary(values: list[float] | np.ndarray) -> dict[str, Any]:
    arr = np.asarray(values, dtype=float)
    if arr.size == 0:
        raise ValueError("Cannot summarize an empty collection")
    return {
        "n": int(arr.size),
        "mean": float(arr.mean()),
        "sd": float(arr.std(ddof=1)) if arr.size > 1 else 0.0,
        "q10": float(np.quantile(arr, 0.10)),
        "median": float(np.median(arr)),
        "q90": float(np.quantile(arr, 0.90)),
        "min": float(arr.min()),
        "max": float(arr.max()),
    }


def _candidate_from_params(name: str, params: dict[str, float]):
    if name == "Power":
        candidate = PowerModel()
    elif name == "Exponential":
        candidate = ExponentialModel()
    else:
        raise ValueError(f"Unsupported stored candidate: {name}")
    for key in ("a", "b", "c", "sigma"):
        setattr(candidate, key, float(params[key]))
    return candidate


def _stored_bic_from_regenerated_data(
    candidate, x_raw: np.ndarray, y_raw: np.ndarray
) -> float:
    """Mirror CandidateModel.log_marginal_likelihood without refitting."""
    pred = candidate.predict(x_raw)
    residuals = y_raw - pred.mean
    sigma2 = pred.noise_var
    n = y_raw.size
    k = candidate.n_free_params + 1
    log_likelihood = (
        -0.5 * n * np.log(2.0 * np.pi * sigma2)
        - 0.5 * np.sum(residuals**2) / sigma2
    )
    return float(log_likelihood - 0.5 * k * np.log(n))


def _conditioned_latent_posterior(
    ncurve,
    hp: dict[str, float],
    trial_grid: np.ndarray,
    subject_seed: int,
) -> tuple[np.ndarray, np.ndarray, dict[str, float]]:
    """Return latent draws and mean after conditioning at stored MAP HPs."""
    x_train = torch.as_tensor(ncurve.x, dtype=torch.float64)
    y_train = torch.as_tensor(ncurve.y, dtype=torch.float64)
    x_eval_norm = (trial_grid - ncurve.x_min) / (ncurve.x_max - ncurve.x_min)
    x_eval = torch.as_tensor(x_eval_norm, dtype=torch.float64)

    kernels, names = build_kernel(PRACTICE_CONFIGS["practitioner"])
    likelihood = build_likelihood(PRACTICE_CONFIGS["practitioner"])
    model, likelihood = practice_run.build_model(
        x_train, y_train, kernels, names, likelihood
    )
    with torch.no_grad():
        model.kernel_components[0].base_kernel.lengthscale = float(hp["lengthscale"])
        model.kernel_components[0].outputscale = float(hp["outputscale"])
        likelihood.noise = float(hp["noise"])

    model.eval()
    likelihood.eval()
    with torch.no_grad():
        k_xx = model.covar_module(x_train, x_train).to_dense()
        k_sx = model.covar_module(x_eval, x_train).to_dense()
        k_ss = model.covar_module(x_eval, x_eval).to_dense()
        eye = torch.eye(x_train.numel(), dtype=torch.float64)
        chol = torch.linalg.cholesky(
            k_xx + (float(hp["noise"]) + CONDITIONING_JITTER) * eye
        )
        alpha = torch.cholesky_solve(y_train[:, None], chol).squeeze(1)
        posterior_mean = k_sx @ alpha
        v = torch.linalg.solve_triangular(chol, k_sx.T, upper=False)
        posterior_cov = k_ss - v.T @ v

    mean = posterior_mean.cpu().numpy()
    cov = posterior_cov.cpu().numpy()
    cov = 0.5 * (cov + cov.T)
    eigenvalues, eigenvectors = np.linalg.eigh(cov)
    min_eigenvalue = float(eigenvalues.min())
    if min_eigenvalue < -PSD_ABS_TOL:
        raise AssertionError(
            f"Posterior covariance minimum eigenvalue {min_eigenvalue:.3e} "
            f"falls below {-PSD_ABS_TOL:.1e}"
        )
    eigenvalues = np.maximum(eigenvalues, 0.0)
    factor = eigenvectors @ np.diag(np.sqrt(eigenvalues))
    rng = np.random.default_rng(subject_seed)
    standard_normal = rng.standard_normal((N_DRAWS, trial_grid.size))
    draws_normalized = mean[None, :] + standard_normal @ factor.T
    draws_raw = draws_normalized * ncurve.y_std + ncurve.y_mean
    posterior_mean_raw = mean * ncurve.y_std + ncurve.y_mean
    return draws_raw, posterior_mean_raw, {
        "minimum_posterior_covariance_eigenvalue": min_eigenvalue,
    }


def _load_source_artifacts() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not SOURCE_DIR.is_dir():
        raise FileNotFoundError(f"Missing source artifact directory: {SOURCE_DIR}")
    aggregate = json.loads((SOURCE_DIR / "aggregate.json").read_text())
    paths = sorted(SOURCE_DIR.glob("synth_*_sub*_default.json"))
    if len(paths) != N_SUBJECTS:
        raise AssertionError(f"Expected {N_SUBJECTS} subject JSONs, found {len(paths)}")
    subjects = []
    for path in paths:
        record = json.loads(path.read_text())
        record["_source_file"] = path.name
        subjects.append(record)
    if int(aggregate["n"]) != len(subjects):
        raise AssertionError("aggregate.json and subject-file counts disagree")
    return aggregate, subjects


def _aggregate_stored_g(subjects: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize stored mean_G values; do not recompute divergences."""
    first = subjects[0]["bistar_G_diagnostics"]
    output: dict[str, Any] = {}
    for config in first:
        output[config] = {}
        for metric in first[config]:
            output[config][metric] = {}
            for cohort in ("power_truth", "exponential_truth", "all_subjects"):
                if cohort == "all_subjects":
                    selected = subjects
                else:
                    label = "synth_power" if cohort == "power_truth" else "synth_exponential"
                    selected = [s for s in subjects if s["dataset_id"] == label]
                output[config][metric][cohort] = {}
                for candidate in ("Power", "Exponential"):
                    values = [
                        float(s["bistar_G_diagnostics"][config][metric]["per_model"][candidate]["mean_G"])
                        for s in selected
                    ]
                    output[config][metric][cohort][candidate] = _summary(values)
    return output


def _aggregate_truth_raw_draw_wins(
    subjects: list[dict[str, Any]], metric: str = "pw_nll"
) -> dict[str, Any]:
    """Aggregate tau-free wins by the known-truth candidate."""
    first = subjects[0]["bistar_G_diagnostics"]
    output: dict[str, Any] = {
        "metric": metric,
        "description": (
            "Tau-free fraction of stored GP draws on which the known-truth "
            "candidate has the smaller raw G value"
        ),
        "subject_majority_definition": "Strictly more than half of a subject's stored draws",
        "by_configuration": {},
    }
    for config in first:
        output["by_configuration"][config] = {}
        for cohort, dataset_id, truth in (
            ("power_truth", "synth_power", "Power"),
            ("exponential_truth", "synth_exponential", "Exponential"),
        ):
            selected = [s for s in subjects if s["dataset_id"] == dataset_id]
            wins = []
            draw_counts = []
            for subject in selected:
                diagnostics = subject["bistar_G_diagnostics"][config][metric]
                wins.append(int(diagnostics["per_model"][truth]["raw_draw_wins"]))
                draw_counts.append(int(diagnostics["n_draws"]))
            if len(set(draw_counts)) != 1:
                raise AssertionError(f"Stored draw counts vary for {config}/{cohort}/{metric}")
            total_draws = int(sum(draw_counts))
            truth_wins = int(sum(wins))
            output["by_configuration"][config][cohort] = {
                "truth_candidate": truth,
                "n_subjects": len(selected),
                "n_draws_per_subject": draw_counts[0],
                "n_draws_total": total_draws,
                "truth_raw_draw_wins": truth_wins,
                "truth_raw_draw_win_fraction": truth_wins / total_draws,
                "n_subjects_truth_strict_majority": int(
                    sum(win > draw_count / 2 for win, draw_count in zip(wins, draw_counts))
                ),
                "n_subjects_truth_exact_tie": int(
                    sum(win == draw_count / 2 for win, draw_count in zip(wins, draw_counts))
                ),
            }
    return output


def _metric_scale_diagnostics(subjects: list[dict[str, Any]]) -> dict[str, Any]:
    """Verify the stored pw_nll/pw_mse affine identity and tau-scale behavior."""
    identity_errors = []
    divisors = []
    configurations = tuple(subjects[0]["bistar_G_diagnostics"])
    for subject in subjects:
        for config in configurations:
            for candidate in ("Power", "Exponential"):
                sigma = float(subject["fitted_params"][candidate]["sigma"])
                sigma2 = sigma**2
                pw_mse = float(
                    subject["bistar_G_diagnostics"][config]["pw_mse"]["per_model"][
                        candidate
                    ]["mean_G"]
                )
                pw_nll = float(
                    subject["bistar_G_diagnostics"][config]["pw_nll"]["per_model"][
                        candidate
                    ]["mean_G"]
                )
                reconstructed = 0.5 * math.log(2.0 * math.pi * sigma2) + pw_mse / (
                    2.0 * sigma2
                )
                identity_errors.append(abs(pw_nll - reconstructed))
                divisors.append(2.0 * sigma2)

    tau_grid = sorted(float(t) for t in subjects[0]["bistar_probs"][configurations[0]]["pw_nll"])
    probability_medians: dict[str, Any] = {}
    for config in configurations:
        probability_medians[config] = {}
        for metric in ("pw_nll", "pw_mse"):
            probability_medians[config][metric] = {}
            for cohort, dataset_id in (
                ("power_truth", "synth_power"),
                ("exponential_truth", "synth_exponential"),
                ("all_subjects", None),
            ):
                selected = (
                    subjects
                    if dataset_id is None
                    else [s for s in subjects if s["dataset_id"] == dataset_id]
                )
                probability_medians[config][metric][cohort] = [
                    {
                        "tau": tau,
                        "median_max_candidate_probability": float(
                            np.median(
                                [
                                    max(
                                        float(p)
                                        for p in subject["bistar_probs"][config][metric][
                                            str(tau)
                                        ].values()
                                    )
                                    for subject in selected
                                ]
                            )
                        ),
                    }
                    for tau in tau_grid
                ]

    return {
        "affine_identity": {
            "formula": (
                "pw_nll = 0.5 * log(2 * pi * sigma_theta^2) "
                "+ pw_mse / (2 * sigma_theta^2)"
            ),
            "description": (
                "Candidate-specific affine identity checked on every stored "
                "configuration, subject, and candidate mean_G pair"
            ),
            "n_stored_mean_G_pairs_checked": len(identity_errors),
            "max_absolute_error": max(identity_errors),
            "two_sigma_squared_divisor_min": min(divisors),
            "two_sigma_squared_divisor_max": max(divisors),
            "shared_tau_invariance": False,
            "non_invariance_note": (
                "BMS* scores exp(-G/tau) at one shared tau, so probability "
                "magnitudes are not comparable across differently scaled metrics."
            ),
        },
        "stored_tau_grid_probability_medians": {
            "description": (
                "Median maximum candidate probabilities from the stored 15-point "
                "tau grid; retained only to demonstrate metric-scale non-invariance"
            ),
            "n_tau_values": len(tau_grid),
            "tau_grid": tau_grid,
            "by_configuration_metric_cohort": probability_medians,
        },
    }


def _selection_summary(
    source_aggregate: dict[str, Any], subjects: list[dict[str, Any]]
) -> dict[str, Any]:
    """Expose source counts plus probability and known-truth summaries."""
    bistar: dict[str, Any] = {}
    for config, metric_records in source_aggregate["bistar"].items():
        bistar[config] = {}
        for metric in metric_records:
            maximum_probabilities = []
            correct = 0
            cohort_winners: dict[str, Counter] = {
                "power_truth": Counter(),
                "exponential_truth": Counter(),
            }
            reference_tau = None
            for subject in subjects:
                tau_records = subject["bistar_probs"][config][metric]
                tau_values = sorted(float(t) for t in tau_records)
                reference_tau = tau_values[len(tau_values) // 2]
                probabilities = tau_records[str(reference_tau)]
                winner = max(probabilities, key=probabilities.get)
                truth = "Power" if subject["dataset_id"] == "synth_power" else "Exponential"
                cohort = "power_truth" if truth == "Power" else "exponential_truth"
                cohort_winners[cohort][winner] += 1
                correct += int(winner == truth)
                maximum_probabilities.append(max(float(p) for p in probabilities.values()))
            bistar[config][metric] = {
                "reference_tau": float(reference_tau),
                "winner_counts_all_subjects": source_aggregate["bistar"][config][metric],
                "winner_counts_by_cohort": {
                    cohort: dict(counts) for cohort, counts in cohort_winners.items()
                },
                "known_truth_correct": correct,
                "known_truth_accuracy": correct / len(subjects),
                "maximum_candidate_probability": _summary(maximum_probabilities),
            }

    bic_by_cohort = {}
    for cohort, dataset_id, truth in (
        ("power_truth", "synth_power", "Power"),
        ("exponential_truth", "synth_exponential", "Exponential"),
    ):
        selected = [s for s in subjects if s["dataset_id"] == dataset_id]
        counts = Counter(s["bic_winner"] for s in selected)
        bic_by_cohort[cohort] = {
            "winner_counts": dict(counts),
            "known_truth_correct": sum(s["bic_winner"] == truth for s in selected),
            "n": len(selected),
        }

    robustness = {}
    for metric, counts in source_aggregate["robustness"].items():
        total = int(counts["agree"]) + int(counts["disagree"])
        robustness[metric] = {
            **counts,
            "fraction_all_configs_agree": float(counts["agree"]) / total,
        }
    return {
        "bic_winner_counts_all_subjects": source_aggregate["bic"],
        "bic_by_cohort": bic_by_cohort,
        "bistar_at_stored_median_tau": bistar,
        "robustness_across_configs": robustness,
    }


def _summarize_deviation_estimand(
    deviations: dict[str, dict[str, list[np.ndarray]]],
    *,
    n_atoms_per_subject: int,
    atom_description: str,
    estimand_description: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Pool a per-subject deviation estimand and compute common summaries."""
    curves: dict[str, Any] = {}
    gaps: dict[str, Any] = {}
    headlines: dict[str, Any] = {}
    for cohort in ("power_truth", "exponential_truth"):
        curves[cohort] = {}
        means = {}
        for candidate in ("Power", "Exponential"):
            pooled = np.concatenate(deviations[cohort][candidate], axis=0)
            expected_shape = (25 * n_atoms_per_subject, TRIAL_GRID.size)
            if pooled.shape != expected_shape:
                raise AssertionError(
                    f"Unexpected pooled deviation shape for {cohort}/{candidate}: "
                    f"{pooled.shape} != {expected_shape}"
                )
            mean = pooled.mean(axis=0)
            means[candidate] = mean
            curves[cohort][candidate] = {
                "estimand": estimand_description,
                "n_subjects": 25,
                "n_atoms_per_subject": n_atoms_per_subject,
                "atom_description": atom_description,
                "n_pooled_atoms_per_trial": int(pooled.shape[0]),
                "mean": mean,
                "band_q10": np.quantile(pooled, 0.10, axis=0),
                "band_q90": np.quantile(pooled, 0.90, axis=0),
            }
        gap = np.abs(means["Power"] - means["Exponential"])
        total_gap = float(gap.sum())
        first_five = float(gap[:5].sum())
        peak_index = int(np.argmax(gap))
        gaps[cohort] = {
            "estimand": estimand_description,
            "definition": (
                "Absolute difference between the two candidates' pooled mean "
                "absolute deviations at each trial"
            ),
            "absolute_mean_deviation_gap": gap,
        }
        headlines[cohort] = {
            "estimand": estimand_description,
            "peak_trial": int(TRIAL_GRID[peak_index]),
            "peak_gap": float(gap[peak_index]),
            "mean_gap_trials_1_to_5": float(gap[:5].mean()),
            "mean_gap_trials_6_to_20": float(gap[5:].mean()),
            "first_five_fraction_of_total_gap": first_five / total_gap if total_gap else 0.0,
            "first_ten_fraction_of_total_gap": (
                float(gap[:10].sum()) / total_gap if total_gap else 0.0
            ),
            "power_regret_mean_over_20_trials": float(means["Power"].mean()),
            "exponential_regret_mean_over_20_trials": float(
                means["Exponential"].mean()
            ),
        }
    return curves, gaps, headlines


def _plot_regret_curves(
    regret_curves: dict[str, Any],
    discrimination_gap: dict[str, Any],
    mean_based_regret_curves: dict[str, Any],
    mean_based_discrimination_gap: dict[str, Any],
    path: Path,
) -> None:
    colors = {"Power": "#315B8A", "Exponential": "#C65A34"}
    labels = {"power_truth": "Power-generated", "exponential_truth": "Exponential-generated"}
    fig, axes = plt.subplots(
        2,
        2,
        figsize=(10.2, 6.6),
        sharex="col",
        gridspec_kw={"height_ratios": [3.0, 1.25]},
    )
    for column, cohort in enumerate(("power_truth", "exponential_truth")):
        ax = axes[0, column]
        for candidate in ("Power", "Exponential"):
            record = regret_curves[cohort][candidate]
            mean_record = mean_based_regret_curves[cohort][candidate]
            mean = np.asarray(record["mean"])
            mean_based = np.asarray(mean_record["mean"])
            lower = np.asarray(record["band_q10"])
            upper = np.asarray(record["band_q90"])
            ax.plot(
                TRIAL_GRID,
                mean,
                color=colors[candidate],
                lw=2.2,
                label=candidate,
            )
            ax.plot(
                TRIAL_GRID,
                mean_based,
                color=colors[candidate],
                lw=1.9,
                ls="--",
            )
            ax.fill_between(TRIAL_GRID, lower, upper, color=colors[candidate], alpha=0.14)
        ax.set_title(labels[cohort])
        ax.set_ylabel("Absolute deviation (RT units)")
        ax.grid(alpha=0.22, linewidth=0.7)
        ax.legend(frameon=False, fontsize=8)

        gap_ax = axes[1, column]
        gap = np.asarray(discrimination_gap[cohort]["absolute_mean_deviation_gap"])
        mean_gap = np.asarray(
            mean_based_discrimination_gap[cohort]["absolute_mean_deviation_gap"]
        )
        gap_ax.plot(TRIAL_GRID, gap, color="#5D3A7A", lw=2.0)
        gap_ax.plot(
            TRIAL_GRID,
            mean_gap,
            color="#5D3A7A",
            lw=1.8,
            ls="--",
        )
        gap_ax.fill_between(TRIAL_GRID, 0.0, gap, color="#5D3A7A", alpha=0.14)
        gap_ax.axvspan(0.5, 5.5, color="#D4A72C", alpha=0.08)
        gap_ax.set_xlabel("Practice trial")
        gap_ax.set_ylabel("Gap")
        gap_ax.set_xticks([1, 5, 10, 15, 20])
        gap_ax.grid(alpha=0.22, linewidth=0.7)

    fig.suptitle("Candidate deviation under stored practitioner-MAP GP", y=0.995)
    fig.text(
        0.5,
        0.01,
        (
            "Solid: MAP-conditional posterior expected absolute deviation of the latent "
            "function. Dashed: posterior-mean plug-in. Bands show pooled draw dispersion."
        ),
        ha="center",
        fontsize=9,
    )
    fig.tight_layout(rect=(0, 0.035, 1, 0.975))
    fig.savefig(path, dpi=170, bbox_inches="tight", metadata={"Software": "regret_curves_mopen.py"})
    plt.close(fig)


def _write_readme(results: dict[str, Any], path: Path) -> None:
    fidelity = results["reconstruction_fidelity"]
    power = results["headline_regret"]["power_truth"]
    exponential = results["headline_regret"]["exponential_truth"]
    mean_power = results["mean_based_headline_regret"]["power_truth"]
    mean_exponential = results["mean_based_headline_regret"]["exponential_truth"]
    raw_wins = results["stored_truth_raw_draw_wins"]["by_configuration"]
    affine = results["metric_scale_diagnostics"]["affine_identity"]
    tau_medians = results["metric_scale_diagnostics"][
        "stored_tau_grid_probability_medians"
    ]["by_configuration_metric_cohort"]
    power_pw_nll_at_tau_min = [
        tau_medians[config]["pw_nll"]["power_truth"][0][
            "median_max_candidate_probability"
        ]
        for config in ("practitioner", "moderate", "agnostic")
    ]
    practitioner_pw_mse_at_tau_max = tau_medians["practitioner"]["pw_mse"][
        "all_subjects"
    ][-1]["median_max_candidate_probability"]
    readme = f"""# Case D deviation curves

Run from the repository root:

```bash
python experiments/regret_curves_mopen.py
```

The script reads the 50 subject JSONs in
`experiments/practice_EvansEtAL/results_hmc/`. Those artifacts came from
`run.py --demo`: `generate_demo_data(n_subjects=50, seed=42)` produced 25
power-generated and 25 exponential-generated curves. The practice data
directory contains no Evans et al. CSVs, so none of these results concern the
real Evans corpus. The regenerated training series range from {results['provenance']['training_trial_counts']['min']} to {results['provenance']['training_trial_counts']['max']}
trials. The stored practice G values use 50 uniformly spaced points over each
subject's full trial span, whereas both reconstructed estimands use integer
trials 1 through 20. For a 79-trial series, the latter grid covers
{100 * results['provenance']['evaluation_domains']['longest_subject_continuous_span_overlap_fraction']:.1f}% of the full continuous trial span. Comparisons between the reconstructed curves
and stored aggregate G diagnostics therefore concern only their shared early
region.

## Reconstruction

Candidate predictions come from the stored `fitted_params` through the local
`candidates.py` classes. Their residual-based BIC log marginal likelihoods
match the stored values with maximum absolute error {fidelity['bic_log_ml']['max_abs_error']:.3e},
below the asserted {fidelity['bic_log_ml']['absolute_tolerance']:.1e} tolerance.

`run.py` iterates the default configurations in practitioner, moderate,
agnostic order. Immediately after each configuration's MAP fit, it writes the
single `gp_hyperparameters` block only when that block remains empty. The
stored values therefore record the first successful configuration's MAP point,
which equals practitioner for all 50 files, even under `results_hmc/`. The
subject JSONs do not retain the HMC hyperparameter draws. This script rebuilds
the practitioner RBF GP at that stored point, conditions on the complete
regenerated series with normalized-space jitter {CONDITIONING_JITTER:.1e}, and
draws {N_DRAWS} latent posterior functions per subject. It performs no fitting
and no HMC. Subject `i` uses NumPy seed `{DRAW_SEED_BASE} + i`. The limits-note
formula averages posterior mean functions over hyperparameter draws. The stored
files cannot reconstruct that target. The solid curves instead report the
MAP-conditional posterior expected absolute deviation of the latent function,
and the dashed curves report the posterior-mean plug-in at the same MAP point.

## Estimands and bands

The MAP-conditional posterior expected absolute deviation computes
`E_{{f | y, eta_hat}}[abs(f(t) - mu_theta(t))]`. Its mean at each trial pools
25 subjects times 100 draws within a truth cohort. The shaded band spans the
10th and 90th percentiles of those same 2,500 subject-draw absolute deviations;
it describes dispersion, not a confidence interval for the cohort mean. The
mean-based plug-in computes
`abs(E[f(t) | y, eta_hat] - mu_theta(t))` per subject and candidate. Its JSON
band pools the 25 subject values; the figure overlays only its dashed cohort
mean. Jensen's inequality makes the draw-based deviation no smaller than the
plug-in for each subject, candidate, and trial. The latent posterior spread
therefore inflates candidate deviations and generally compresses their gap by a
trial-dependent amount. Both estimands use raw response-time units (RT units).

| Truth cohort | Estimand | Mean Power deviation (RT units) | Mean Exponential deviation (RT units) | Peak gap (RT units) |
|---|---|---:|---:|---:|
| Power | MAP-conditional posterior expected absolute deviation | {power['power_regret_mean_over_20_trials']:.3f} | {power['exponential_regret_mean_over_20_trials']:.3f} | {power['peak_gap']:.3f} at trial {power['peak_trial']} |
| Power | Posterior-mean plug-in | {mean_power['power_regret_mean_over_20_trials']:.3f} | {mean_power['exponential_regret_mean_over_20_trials']:.3f} | {mean_power['peak_gap']:.3f} at trial {mean_power['peak_trial']} |
| Exponential | MAP-conditional posterior expected absolute deviation | {exponential['power_regret_mean_over_20_trials']:.3f} | {exponential['exponential_regret_mean_over_20_trials']:.3f} | {exponential['peak_gap']:.3f} at trial {exponential['peak_trial']} |
| Exponential | Posterior-mean plug-in | {mean_exponential['power_regret_mean_over_20_trials']:.3f} | {mean_exponential['exponential_regret_mean_over_20_trials']:.3f} | {mean_exponential['peak_gap']:.3f} at trial {mean_exponential['peak_trial']} |

For the power-generated cohort, {100 * power['first_five_fraction_of_total_gap']:.1f}% of the summed
20-trial MAP-conditional gap occurs in trials 1 through 5, and the first 10
trials account for {100 * power['first_ten_fraction_of_total_gap']:.1f}%. The largest gap equals
{power['peak_gap']:.3f} RT units at trial {power['peak_trial']}. For the exponential-generated cohort,
the corresponding shares equal {100 * exponential['first_five_fraction_of_total_gap']:.1f}% and
{100 * exponential['first_ten_fraction_of_total_gap']:.1f}%, and the largest gap equals
{exponential['peak_gap']:.3f} RT units at trial {exponential['peak_trial']}.

## Stored divergence diagnostics

`results.json` also aggregates the already stored `mean_G` values by prior
configuration, legacy metric, truth cohort, and candidate. It never recomputes
G. The practice artifacts predate the W1 metric decision and contain
`pw_nll`, `pw_mse`, and `pw_hellinger`; they contain no `pw_kl_vcal`.
The primary `pw_kl_vcal` weights squared error by GP variance. Legacy `pw_nll`
instead weights by each candidate's fitted noise variance; on that axis,
`pw_mse` more closely resembles the primary metric.

Every one of the {affine['n_stored_mean_G_pairs_checked']} stored `mean_G` pairs satisfies
`pw_nll = 0.5*log(2*pi*sigma_theta^2) + pw_mse/(2*sigma_theta^2)`, with maximum
absolute error {affine['max_absolute_error']:.2e}. The candidate-specific divisor
`2*sigma_theta^2` ranges from {affine['two_sigma_squared_divisor_min']:.1f} to
{affine['two_sigma_squared_divisor_max']:.1f}. BMS* applies `exp(-G/tau)` at a
shared temperature, so soft-transfer probability magnitudes cannot be compared
across these differently scaled metrics. No value on the stored 15-point grid
removes that scale gap: at `tau=0.1`, the power-cohort `pw_nll` medians equal
{power_pw_nll_at_tau_min[0]:.3f}, {power_pw_nll_at_tau_min[1]:.3f}, and
{power_pw_nll_at_tau_min[2]:.3f} across practitioner, moderate, and agnostic
(about 0.57), while the all-subject practitioner `pw_mse` median remains
{practitioner_pw_mse_at_tau_max:.3f} at `tau=31.6`.

The tau-free `pw_nll` `raw_draw_wins` diagnostic retains the asymmetry:

| Configuration | Power truth: true-family draw wins | Power subjects with true-family majority | Exponential truth: true-family draw wins | Exponential subjects with true-family majority |
|---|---:|---:|---:|---:|
| practitioner | {100 * raw_wins['practitioner']['power_truth']['truth_raw_draw_win_fraction']:.1f}% | {raw_wins['practitioner']['power_truth']['n_subjects_truth_strict_majority']} / 25 | {100 * raw_wins['practitioner']['exponential_truth']['truth_raw_draw_win_fraction']:.1f}% | {raw_wins['practitioner']['exponential_truth']['n_subjects_truth_strict_majority']} / 25 |
| moderate | {100 * raw_wins['moderate']['power_truth']['truth_raw_draw_win_fraction']:.1f}% | {raw_wins['moderate']['power_truth']['n_subjects_truth_strict_majority']} / 25 | {100 * raw_wins['moderate']['exponential_truth']['truth_raw_draw_win_fraction']:.1f}% | {raw_wins['moderate']['exponential_truth']['n_subjects_truth_strict_majority']} / 25 |
| agnostic | {100 * raw_wins['agnostic']['power_truth']['truth_raw_draw_win_fraction']:.1f}% | {raw_wins['agnostic']['power_truth']['n_subjects_truth_strict_majority']} / 25 | {100 * raw_wins['agnostic']['exponential_truth']['truth_raw_draw_win_fraction']:.1f}% | {raw_wins['agnostic']['exponential_truth']['n_subjects_truth_strict_majority']} / 25 |

Files:

- `results.json`: provenance, fidelity checks, both deviation estimands,
  discrimination gaps, scale diagnostics, tau-free draw wins, stored selection
  summaries, and aggregated stored G magnitudes.
- `regret_curves.png`: two truth-cohort panels with pooled dispersion bands and
  dashed posterior-mean overlays plus per-trial candidate discrimination gaps.
"""
    path.write_text(readme)


def main() -> None:
    torch.set_default_dtype(torch.float64)
    source_aggregate, subject_artifacts = _load_source_artifacts()
    curves = practice_run.generate_demo_data(n_subjects=N_SUBJECTS, seed=DATA_SEED)
    curve_by_key = {(c.dataset_id, c.subject_id): c for c in curves}
    if len(curve_by_key) != N_SUBJECTS:
        raise AssertionError("Synthetic generator returned duplicate or missing subject keys")

    data_file_count = sum(1 for path in (PRACTICE_DIR / "data").rglob("*") if path.is_file())
    if data_file_count != 0:
        raise AssertionError("Practice data directory no longer empty; provenance must be revisited")

    fidelity_rows = []
    covariance_rows = []
    regrets: dict[str, dict[str, list[np.ndarray]]] = {
        "power_truth": {"Power": [], "Exponential": []},
        "exponential_truth": {"Power": [], "Exponential": []},
    }
    mean_based_regrets: dict[str, dict[str, list[np.ndarray]]] = {
        "power_truth": {"Power": [], "Exponential": []},
        "exponential_truth": {"Power": [], "Exponential": []},
    }
    observed_lengths = []

    for artifact in subject_artifacts:
        key = (artifact["dataset_id"], int(artifact["subject_id"]))
        if key not in curve_by_key:
            raise AssertionError(f"No regenerated curve for {key}")
        curve = curve_by_key[key]
        ncurve = practice_run.normalize(curve)
        observed_lengths.append(curve.n_trials)
        if int(artifact["n_trials"]) != curve.n_trials:
            raise AssertionError(
                f"Trial-count mismatch for {key}: stored {artifact['n_trials']}, "
                f"regenerated {curve.n_trials}"
            )
        if int(artifact["n_gp_samples"]) != N_DRAWS:
            raise AssertionError(
                f"Stored draw-count mismatch for {key}: expected {N_DRAWS}, "
                f"found {artifact['n_gp_samples']}"
            )
        if curve.n_trials < TRIAL_GRID.size or not np.array_equal(
            curve.trial[: TRIAL_GRID.size], TRIAL_GRID
        ):
            raise AssertionError(f"Subject {key} lacks the common first-20-trial grid")

        subject_errors = {}
        candidate_means = {}
        for candidate_name in ("Power", "Exponential"):
            candidate = _candidate_from_params(
                candidate_name, artifact["fitted_params"][candidate_name]
            )
            reconstructed_bic = _stored_bic_from_regenerated_data(
                candidate, curve.trial, curve.rt
            )
            stored_bic = float(artifact["bic_log_ml"][candidate_name])
            error = abs(reconstructed_bic - stored_bic)
            subject_errors[candidate_name] = {
                "stored": stored_bic,
                "reconstructed": reconstructed_bic,
                "absolute_error": error,
            }
            if error > BIC_ABS_TOL:
                raise AssertionError(
                    f"BIC reconstruction failed for {artifact['_source_file']} "
                    f"{candidate_name}: {error:.3e} exceeds {BIC_ABS_TOL:.1e}"
                )
            candidate_means[candidate_name] = candidate.predict(TRIAL_GRID).mean

        function_draws, posterior_mean, covariance_check = _conditioned_latent_posterior(
            ncurve,
            artifact["gp_hyperparameters"],
            TRIAL_GRID,
            DRAW_SEED_BASE + int(artifact["subject_id"]),
        )
        cohort = "power_truth" if artifact["dataset_id"] == "synth_power" else "exponential_truth"
        for candidate_name in ("Power", "Exponential"):
            regrets[cohort][candidate_name].append(
                np.abs(function_draws - candidate_means[candidate_name][None, :])
            )
            mean_based_regrets[cohort][candidate_name].append(
                np.abs(posterior_mean - candidate_means[candidate_name])[None, :]
            )

        fidelity_rows.append(
            {
                "source_file": artifact["_source_file"],
                "dataset_id": artifact["dataset_id"],
                "subject_id": int(artifact["subject_id"]),
                "n_trials": int(curve.n_trials),
                "candidate_bic": subject_errors,
            }
        )
        covariance_rows.append(
            {
                "source_file": artifact["_source_file"],
                **covariance_check,
            }
        )

    all_bic_errors = [
        row["candidate_bic"][candidate]["absolute_error"]
        for row in fidelity_rows
        for candidate in ("Power", "Exponential")
    ]
    draw_estimand_description = (
        "MAP-conditional posterior expected absolute deviation of the latent function"
    )
    mean_estimand_description = "Posterior-mean plug-in absolute deviation at the MAP point"
    regret_curves, discrimination_gap, headline_regret = _summarize_deviation_estimand(
        regrets,
        n_atoms_per_subject=N_DRAWS,
        atom_description="Seeded latent function draw conditional on the stored MAP point",
        estimand_description=draw_estimand_description,
    )
    (
        mean_based_regret_curves,
        mean_based_discrimination_gap,
        mean_based_headline_regret,
    ) = _summarize_deviation_estimand(
        mean_based_regrets,
        n_atoms_per_subject=1,
        atom_description="One latent posterior mean function at the stored MAP point",
        estimand_description=mean_estimand_description,
    )

    sub25 = next(
        s
        for s in subject_artifacts
        if s["dataset_id"] == "synth_exponential" and int(s["subject_id"]) == 25
    )
    sub25_pw_nll = sub25["bistar_G_diagnostics"]["practitioner"]["pw_nll"]["per_model"]
    results = {
        "schema_version": 2,
        "provenance": {
            "source_artifact_dir": "experiments/practice_EvansEtAL/results_hmc",
            "source_aggregate": "experiments/practice_EvansEtAL/results_hmc/aggregate.json",
            "source_artifact_mode": "HMC run, with one stored practitioner MAP hyperparameter point per subject",
            "synthetic_data_generator": "experiments/practice_EvansEtAL/run.py::generate_demo_data",
            "synthetic_data_call": "generate_demo_data(n_subjects=50, seed=42)",
            "real_evans_files_present": False,
            "n_subjects": len(subject_artifacts),
            "cohort_sizes": {"power_truth": 25, "exponential_truth": 25},
            "training_trial_counts": {
                "min": int(min(observed_lengths)),
                "max": int(max(observed_lengths)),
                "unique": sorted(set(int(n) for n in observed_lengths)),
            },
            "evaluation_domains": {
                "stored_practice_G": (
                    "50-point uniform grid spanning each subject's full observed trial series"
                ),
                "stored_practice_G_n_points": 50,
                "stored_practice_G_subject_trial_count_range": {
                    "min": int(min(observed_lengths)),
                    "max": int(max(observed_lengths)),
                },
                "reconstructed_deviation_curves": "Integer trials 1 through 20 only",
                "reconstructed_deviation_n_points": int(TRIAL_GRID.size),
                "shared_region": "Integer trials 1 through 20",
                "longest_subject_continuous_span_overlap_fraction": float(
                    (TRIAL_GRID[-1] - TRIAL_GRID[0])
                    / (max(observed_lengths) - TRIAL_GRID[0])
                ),
                "linkage_limit": (
                    "Reconstructed deviation curves can localize stored aggregate "
                    "comparisons only within the shared early-trial region."
                ),
            },
            "evaluation_trial_grid": TRIAL_GRID,
            "data_seed": DATA_SEED,
            "posterior_function_draw_seed_base": DRAW_SEED_BASE,
            "posterior_function_draw_seed_rule": "seed = 20260811 + subject_id",
            "n_draws_per_subject": N_DRAWS,
            "stored_n_gp_samples_per_subject": N_DRAWS,
            "formula": (
                "MAP-conditional posterior expected absolute deviation of the latent "
                "function: E_{f | y, eta_hat}[abs(f(t) - mu_theta(t))]"
            ),
            "mean_based_plugin_formula": (
                "Posterior-mean plug-in absolute deviation at the MAP point: "
                "abs(E[f(t) | y, eta_hat] - mu_theta(t))"
            ),
            "regret_units": "raw response-time units from the synthetic generator",
            "band_definition": (
                "For the MAP-conditional posterior expected absolute deviation of the "
                "latent function, q10 and q90 pool 25 subjects by 100 posterior function "
                "draws within a truth cohort. For the posterior-mean plug-in, q10 and q90 "
                "pool 25 subject values. Both describe dispersion rather than confidence "
                "limits for a cohort mean."
            ),
            "summary_definition": "Summary fields use the arithmetic mean, sample standard deviation with ddof=1, and NumPy linear-interpolation quantiles.",
            "gp_hyperparameters_provenance": "run.py stores gp_hyperparameters once, immediately after the first successful configuration MAP fit. The default loop order starts with practitioner, so all 50 source files carry practitioner MAP values even though results_hmc subsequently runs HMC for GP samples.",
            "gp_reconstruction": (
                "Exact zero-mean RBF GP conditioning at stored lengthscale, outputscale, "
                "and noise; no refit and no hyperparameter sampling; latent posterior "
                "function draws exclude fresh observation noise."
            ),
            "mean_vs_draw_substitution": (
                "The limits-note target averages posterior mean functions over "
                "hyperparameter draws. The stored files do not retain those draws. This "
                "artifact reports both the MAP-conditional posterior expected absolute "
                "deviation of the latent function and a posterior-mean plug-in at the "
                "same stored MAP point."
            ),
            "estimand_relation_note": (
                "By Jensen's inequality, the MAP-conditional posterior expected "
                "absolute deviation of the latent function is no smaller than the "
                "posterior-mean plug-in for each subject, candidate, and trial. Unequal "
                "inflation changes the candidate gap by a trial-dependent amount."
            ),
            "conditioning_jitter_normalized_variance": CONDITIONING_JITTER,
            "legacy_metric_note": (
                "Stored diagnostics contain pw_nll, pw_mse, and pw_hellinger. They "
                "predate W1 and contain no pw_kl_vcal. pw_nll weights squared error by "
                "candidate fitted noise variance; pw_kl_vcal weights it by GP variance."
            ),
            "formula_discrepancy_note": "The formal limits-note equation and Case D work order use absolute difference. A chat-derived Q&A in the same note says squared difference; this artifact follows the binding absolute formula.",
        },
        "reconstruction_fidelity": {
            "bic_log_ml": {
                "check": "Stored fitted-parameter residual structure evaluated on regenerated full subject series",
                "absolute_tolerance": BIC_ABS_TOL,
                "n_values_checked": len(all_bic_errors),
                "max_abs_error": max(all_bic_errors),
                "mean_abs_error": float(np.mean(all_bic_errors)),
                "all_passed": all(error <= BIC_ABS_TOL for error in all_bic_errors),
            },
            "posterior_covariance": {
                "negative_eigenvalue_absolute_tolerance": PSD_ABS_TOL,
                "minimum_eigenvalue_across_subjects": min(
                    row["minimum_posterior_covariance_eigenvalue"] for row in covariance_rows
                ),
                "all_passed": all(
                    row["minimum_posterior_covariance_eigenvalue"] >= -PSD_ABS_TOL
                    for row in covariance_rows
                ),
            },
            "per_subject": fidelity_rows,
        },
        "trial_grid": TRIAL_GRID,
        "regret_band": {
            "estimand": draw_estimand_description,
            "lower_quantile": 0.10,
            "upper_quantile": 0.90,
            "aggregation": (
                "Pooled across subjects and posterior function draws for the "
                "MAP-conditional posterior expected absolute deviation of the latent "
                "function within each truth cohort"
            ),
        },
        "regret_curves": regret_curves,
        "discrimination_gap": discrimination_gap,
        "headline_regret": headline_regret,
        "mean_based_regret_band": {
            "estimand": mean_estimand_description,
            "lower_quantile": 0.10,
            "upper_quantile": 0.90,
            "aggregation": (
                "Pooled across the 25 subject-level posterior-mean plug-in absolute "
                "deviations within each truth cohort"
            ),
        },
        "mean_based_regret_curves": mean_based_regret_curves,
        "mean_based_discrimination_gap": mean_based_discrimination_gap,
        "mean_based_headline_regret": mean_based_headline_regret,
        "stored_selection_summary": _selection_summary(source_aggregate, subject_artifacts),
        "stored_mean_G_summaries": _aggregate_stored_g(subject_artifacts),
        "stored_truth_raw_draw_wins": _aggregate_truth_raw_draw_wins(subject_artifacts),
        "metric_scale_diagnostics": _metric_scale_diagnostics(subject_artifacts),
        "stored_named_examples": {
            "synth_exponential_sub25_practitioner_pw_nll": {
                "source_file": sub25["_source_file"],
                "Power_mean_G": float(sub25_pw_nll["Power"]["mean_G"]),
                "Exponential_mean_G": float(sub25_pw_nll["Exponential"]["mean_G"]),
                "absolute_difference": abs(
                    float(sub25_pw_nll["Power"]["mean_G"])
                    - float(sub25_pw_nll["Exponential"]["mean_G"])
                ),
            }
        },
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results_path = OUTPUT_DIR / "results.json"
    readme_path = OUTPUT_DIR / "README.md"
    figure_path = OUTPUT_DIR / "regret_curves.png"
    results_path.write_text(
        json.dumps(_json_ready(results), indent=2, sort_keys=True, allow_nan=False) + "\n"
    )
    _plot_regret_curves(
        _json_ready(regret_curves),
        _json_ready(discrimination_gap),
        _json_ready(mean_based_regret_curves),
        _json_ready(mean_based_discrimination_gap),
        figure_path,
    )
    if figure_path.stat().st_size >= FIGURE_SIZE_LIMIT:
        raise AssertionError(
            f"Figure size {figure_path.stat().st_size} exceeds {FIGURE_SIZE_LIMIT} bytes"
        )
    _write_readme(_json_ready(results), readme_path)

    print(f"Wrote {results_path.relative_to(ROOT)}")
    print(f"Wrote {readme_path.relative_to(ROOT)}")
    print(
        f"Wrote {figure_path.relative_to(ROOT)} "
        f"({figure_path.stat().st_size} bytes)"
    )
    print(
        "BIC fidelity: "
        f"max_abs_error={max(all_bic_errors):.3e}, tolerance={BIC_ABS_TOL:.1e}"
    )
    for cohort, headline in headline_regret.items():
        mean_headline = mean_based_headline_regret[cohort]
        print(
            f"{cohort}, MAP-conditional posterior expected absolute deviation "
            f"of the latent function: peak trial {headline['peak_trial']}, "
            f"peak gap {headline['peak_gap']:.6f}, "
            f"first-five share {headline['first_five_fraction_of_total_gap']:.3f}"
        )
        print(
            f"{cohort}, posterior-mean plug-in absolute deviation at the MAP point: "
            f"peak trial {mean_headline['peak_trial']}, "
            f"peak gap {mean_headline['peak_gap']:.6f}, "
            f"first-five share {mean_headline['first_five_fraction_of_total_gap']:.3f}"
        )


if __name__ == "__main__":
    main()
