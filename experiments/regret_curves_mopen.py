#!/usr/bin/env python3
"""Reconstruct Case D regret curves from the frozen practice artifacts.

The script does not fit candidates, optimize GP hyperparameters, or run HMC.
It regenerates the seeded synthetic observations, verifies the stored BIC
values from the stored candidate parameters, conditions an exact GP at the
stored practitioner MAP hyperparameters, and draws latent functions on the
common first-20-trial grid.
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


def _conditioned_function_draws(
    ncurve,
    hp: dict[str, float],
    trial_grid: np.ndarray,
    subject_seed: int,
) -> tuple[np.ndarray, dict[str, float]]:
    """Draw latent GP functions after exact conditioning at stored MAP HPs."""
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
    return draws_raw, {
        "minimum_posterior_covariance_eigenvalue": min_eigenvalue,
        "posterior_sd_min_raw": float(np.sqrt(eigenvalues.min()) * ncurve.y_std),
        "posterior_sd_max_raw": float(np.sqrt(eigenvalues.max()) * ncurve.y_std),
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


def _plot_regret_curves(
    regret_curves: dict[str, Any], discrimination_gap: dict[str, Any], path: Path
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
            mean = np.asarray(record["mean"])
            lower = np.asarray(record["band_q10"])
            upper = np.asarray(record["band_q90"])
            ax.plot(TRIAL_GRID, mean, color=colors[candidate], lw=2.2, label=candidate)
            ax.fill_between(TRIAL_GRID, lower, upper, color=colors[candidate], alpha=0.14)
        ax.set_title(labels[cohort])
        ax.set_ylabel("Absolute regret (RT units)")
        ax.grid(alpha=0.22, linewidth=0.7)
        ax.legend(frameon=False)

        gap_ax = axes[1, column]
        gap = np.asarray(discrimination_gap[cohort]["absolute_mean_regret_gap"])
        gap_ax.plot(TRIAL_GRID, gap, color="#5D3A7A", lw=2.0)
        gap_ax.fill_between(TRIAL_GRID, 0.0, gap, color="#5D3A7A", alpha=0.14)
        gap_ax.axvspan(0.5, 5.5, color="#D4A72C", alpha=0.08)
        gap_ax.set_xlabel("Practice trial")
        gap_ax.set_ylabel("Gap")
        gap_ax.set_xticks([1, 5, 10, 15, 20])
        gap_ax.grid(alpha=0.22, linewidth=0.7)

    fig.suptitle("Candidate regret under stored practice-run GP hyperparameters", y=0.995)
    fig.text(
        0.5,
        0.01,
        "Lines show pooled subject-draw means; bands show pooled 10th to 90th percentiles.",
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
    readme = f"""# Case D regret curves

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
trials; all contain the common trials 1 through 20 used for the regret figure.

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
and no HMC. Subject `i` uses NumPy seed `{DRAW_SEED_BASE} + i`.

## Estimand and band

The implemented formula equals
`regret_theta(t) = E_draws[abs(mu_GP(t) - mu_theta(t))]`. A chat-derived Q&A in
the local limits note mentions a squared difference, but the formal formula and
the Case D work order specify the absolute difference. The mean at each trial
pools 25 subjects times 100 draws within a truth cohort. The shaded band spans
the 10th and 90th percentiles of those same 2,500 subject-draw absolute errors;
it describes dispersion across subjects and posterior function draws, not a
confidence interval for the cohort mean.

For the power-generated cohort, {100 * power['first_five_fraction_of_total_gap']:.1f}% of the summed
20-trial discrimination gap occurs in trials 1 through 5, and the first 10
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
`pw_nll` provides the closest available role to the W1 primary, but the script
does not rename it or introduce a new metric.

Files:

- `results.json`: provenance, fidelity checks, regret curves, discrimination
  gaps, stored selection summaries, and aggregated stored G magnitudes.
- `regret_curves.png`: two truth-cohort panels with pooled dispersion bands and
  per-trial candidate discrimination gaps.
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

        function_draws, covariance_check = _conditioned_function_draws(
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
    regret_curves: dict[str, Any] = {}
    discrimination_gap: dict[str, Any] = {}
    headline_regret: dict[str, Any] = {}
    for cohort in ("power_truth", "exponential_truth"):
        regret_curves[cohort] = {}
        means = {}
        for candidate in ("Power", "Exponential"):
            pooled = np.concatenate(regrets[cohort][candidate], axis=0)
            if pooled.shape != (25 * N_DRAWS, TRIAL_GRID.size):
                raise AssertionError(f"Unexpected pooled regret shape for {cohort}/{candidate}")
            mean = pooled.mean(axis=0)
            means[candidate] = mean
            regret_curves[cohort][candidate] = {
                "n_subjects": 25,
                "n_draws_per_subject": N_DRAWS,
                "n_subject_draw_atoms_per_trial": int(pooled.shape[0]),
                "mean": mean,
                "band_q10": np.quantile(pooled, 0.10, axis=0),
                "band_q90": np.quantile(pooled, 0.90, axis=0),
            }
        gap = np.abs(means["Power"] - means["Exponential"])
        total_gap = float(gap.sum())
        first_five = float(gap[:5].sum())
        peak_index = int(np.argmax(gap))
        discrimination_gap[cohort] = {
            "definition": "Absolute difference between pooled candidate mean regrets at each trial",
            "absolute_mean_regret_gap": gap,
        }
        headline_regret[cohort] = {
            "peak_trial": int(TRIAL_GRID[peak_index]),
            "peak_gap": float(gap[peak_index]),
            "mean_gap_trials_1_to_5": float(gap[:5].mean()),
            "mean_gap_trials_6_to_20": float(gap[5:].mean()),
            "first_five_fraction_of_total_gap": first_five / total_gap if total_gap else 0.0,
            "first_ten_fraction_of_total_gap": float(gap[:10].sum()) / total_gap if total_gap else 0.0,
            "power_regret_mean_over_20_trials": float(means["Power"].mean()),
            "exponential_regret_mean_over_20_trials": float(means["Exponential"].mean()),
        }

    sub25 = next(
        s
        for s in subject_artifacts
        if s["dataset_id"] == "synth_exponential" and int(s["subject_id"]) == 25
    )
    sub25_pw_nll = sub25["bistar_G_diagnostics"]["practitioner"]["pw_nll"]["per_model"]
    results = {
        "schema_version": 1,
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
            "evaluation_trial_grid": TRIAL_GRID,
            "data_seed": DATA_SEED,
            "posterior_function_draw_seed_base": DRAW_SEED_BASE,
            "posterior_function_draw_seed_rule": "seed = 20260811 + subject_id",
            "n_draws_per_subject": N_DRAWS,
            "stored_n_gp_samples_per_subject": N_DRAWS,
            "formula": "regret_theta(t) = E_draws[abs(mu_GP(t) - mu_theta(t))]",
            "regret_units": "raw response-time units from the synthetic generator",
            "band_definition": "At each trial, q10 and q90 pool the 25 subjects by 100 posterior function draws within a truth cohort and describe dispersion rather than confidence limits for the mean.",
            "summary_definition": "Summary fields use the arithmetic mean, sample standard deviation with ddof=1, and NumPy linear-interpolation quantiles.",
            "gp_hyperparameters_provenance": "run.py stores gp_hyperparameters once, immediately after the first successful configuration MAP fit. The default loop order starts with practitioner, so all 50 source files carry practitioner MAP values even though results_hmc subsequently runs HMC for GP samples.",
            "gp_reconstruction": "Exact zero-mean RBF GP conditioning at stored lengthscale, outputscale, and noise; no refit and no hyperparameter sampling; latent posterior function draws exclude fresh observation noise.",
            "conditioning_jitter_normalized_variance": CONDITIONING_JITTER,
            "legacy_metric_note": "Stored diagnostics contain pw_nll, pw_mse, and pw_hellinger. They predate W1 and contain no pw_kl_vcal. pw_nll receives closest-role framing without relabeling or recomputation.",
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
            "lower_quantile": 0.10,
            "upper_quantile": 0.90,
            "aggregation": "Pooled across subjects and posterior function draws within each truth cohort",
        },
        "regret_curves": regret_curves,
        "discrimination_gap": discrimination_gap,
        "headline_regret": headline_regret,
        "stored_selection_summary": _selection_summary(source_aggregate, subject_artifacts),
        "stored_mean_G_summaries": _aggregate_stored_g(subject_artifacts),
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
        _json_ready(regret_curves), _json_ready(discrimination_gap), figure_path
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
        print(
            f"{cohort}: peak trial {headline['peak_trial']}, "
            f"peak gap {headline['peak_gap']:.6f}, "
            f"first-five share {headline['first_five_fraction_of_total_gap']:.3f}"
        )


if __name__ == "__main__":
    main()
