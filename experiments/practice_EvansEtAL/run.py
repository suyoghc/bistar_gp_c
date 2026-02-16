"""
BMS* for the Law of Practice.

Runs BI* on all individual learning series from Evans et al. (2018) /
Heathcote et al. (2000) — 475 subjects, 24 experiments.

Usage:
    python run.py --demo                           # synthetic test
    python run.py --data_dir ./data/evans2018      # real data, MAP
    python run.py --data_dir ./data --mode hmc     # full Bayesian
"""

import numpy as np
import torch
import os
import sys
import json
import time
import argparse
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Optional
import warnings
warnings.filterwarnings("ignore")

torch.set_default_dtype(torch.float64)

# ── Path setup ────────────────────────────────────────────────────
# Add project root so we can import bistar_gp
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Local sandbox imports
from candidates import (
    build_practice_candidates, build_core_candidates,
    CandidateResult,
)
from kernels import (
    PRACTICE_CONFIGS, build_kernel, build_likelihood,
    get_kernel_builder, get_likelihood_builder,
)

# Core bistar_gp imports
from bistar_gp.model import build_model
from bistar_gp.fit import fit_map, fit_hmc
from bistar_gp.bms_star import (
    extract_gp_predictives, run_bms_star, GPPosteriorSample,
)


# ═══════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════

@dataclass
class LearningCurve:
    """One individual learning series."""
    dataset_id: str
    subject_id: int
    condition: str
    task_type: str
    trial: np.ndarray
    rt: np.ndarray
    n_trials: int


@dataclass
class NormalizedCurve:
    """Normalized for GP: x->[0,1], y->z-score."""
    x: np.ndarray
    y: np.ndarray
    x_raw: np.ndarray
    y_raw: np.ndarray
    x_min: float; x_max: float
    y_mean: float; y_std: float
    curve: LearningCurve


@dataclass
class SubjectResult:
    """Complete results for one learning curve."""
    dataset_id: str
    subject_id: int
    condition: str
    task_type: str
    n_trials: int
    bistar_winners: Dict
    bistar_probs: Dict
    bic_log_ml: Dict[str, float]
    bic_winner: str
    fitted_params: Dict[str, Dict]
    gp_hyperparameters: Dict
    n_gp_samples: int
    elapsed_seconds: float


# ═══════════════════════════════════════════════════════════════════
# Data Loading
# ═══════════════════════════════════════════════════════════════════

def load_data(data_dir: str) -> List[LearningCurve]:
    """
    Load learning curves from Evans et al. (2018) data.
    Tries CSV, then .mat. Falls back to synthetic demo.
    """
    data_dir = Path(data_dir)
    curves = []

    for csv_file in data_dir.glob("*.csv"):
        try:
            curves.extend(_parse_csv(csv_file))
        except Exception as e:
            print(f"  Warning: {csv_file.name}: {e}")

    for mat_file in data_dir.glob("*.mat"):
        try:
            from scipy.io import loadmat
            curves.extend(_parse_mat(mat_file))
        except Exception as e:
            print(f"  Warning: {mat_file.name}: {e}")

    if not curves:
        print(f"\n  No data in {data_dir}")
        print(f"  Download from: https://osf.io/7yx6b/")
        print(f"  Generating synthetic demo instead...\n")
        curves = generate_demo_data()

    return curves


def _parse_csv(filepath: Path) -> List[LearningCurve]:
    """Parse CSV into learning curves. Adapt to actual column names."""
    import csv
    from collections import defaultdict

    with open(filepath, 'r') as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return []

    cols = rows[0].keys()

    # Detect columns
    sub_col = _find_col(cols, ['subject', 'sub', 'Subject', 'participant', 'user_id', 'id'])
    trial_col = _find_col(cols, ['trial', 'block', 'Trial', 'Block', 'trial_num', 'practice'])
    rt_col = _find_col(cols, ['rt', 'RT', 'response_time', 'mean_rt', 'meanRT', 'time'])
    cond_col = _find_col(cols, ['condition', 'cond', 'Condition', 'task'])

    if not all([sub_col, trial_col, rt_col]):
        raise ValueError(f"Can't identify columns. Found: {list(cols)}")

    grouped = defaultdict(lambda: ([], []))
    for row in rows:
        try:
            key = (row[sub_col], row.get(cond_col, "default") if cond_col else "default")
            grouped[key][0].append(float(row[trial_col]))
            grouped[key][1].append(float(row[rt_col]))
        except (ValueError, KeyError):
            continue

    curves = []
    dataset_id = filepath.stem
    for (sub, cond), (trials, rts) in grouped.items():
        trials, rts = np.array(trials), np.array(rts)
        order = np.argsort(trials)
        trials, rts = trials[order], rts[order]
        if len(trials) < 5:
            continue
        curves.append(LearningCurve(
            dataset_id=dataset_id, subject_id=int(sub) if sub.isdigit() else hash(sub) % 10000,
            condition=str(cond), task_type=_infer_task(dataset_id),
            trial=trials, rt=rts, n_trials=len(trials),
        ))
    return curves


def _parse_mat(filepath: Path) -> List[LearningCurve]:
    """Parse Matlab .mat file."""
    from scipy.io import loadmat
    mat = loadmat(str(filepath), squeeze_me=True)
    curves = []
    for key in mat:
        if key.startswith('_'):
            continue
        data = mat[key]
        if isinstance(data, np.ndarray) and data.ndim == 2:
            n_trials, n_subs = data.shape
            for s in range(n_subs):
                rt = data[:, s]
                valid = ~np.isnan(rt)
                if valid.sum() < 5:
                    continue
                curves.append(LearningCurve(
                    dataset_id=filepath.stem, subject_id=s,
                    condition="default", task_type=_infer_task(filepath.stem),
                    trial=np.arange(1, n_trials+1)[valid].astype(float),
                    rt=rt[valid].astype(float), n_trials=int(valid.sum()),
                ))
    return curves


def _find_col(cols, candidates):
    for c in candidates:
        if c in cols:
            return c
    return None


def _infer_task(dataset_id: str) -> str:
    d = dataset_id.upper()
    if d.startswith("MS") or d.startswith("AA"): return "memory_search"
    if d.startswith("VS"): return "visual_search"
    if d.startswith("KEY") or d.startswith("MOTOR"): return "motor"
    if d.startswith("RULE"): return "rule_learning"
    return "unknown"


def generate_demo_data(n_subjects=50, seed=42) -> List[LearningCurve]:
    """Synthetic: half power, half exponential. Known ground truth."""
    rng = np.random.RandomState(seed)
    curves = []
    for i in range(n_subjects):
        n = rng.randint(20, 80)
        t = np.arange(1, n + 1, dtype=float)
        if i < n_subjects // 2:
            a, b, c = rng.uniform(200, 600), rng.uniform(0.2, 0.8), rng.uniform(200, 500)
            rt = a * t ** (-b) + c
            label = "power"
        else:
            a, b, c = rng.uniform(200, 600), rng.uniform(0.02, 0.15), rng.uniform(200, 500)
            rt = a * np.exp(-b * t) + c
            label = "exponential"
        rt += rng.normal(0, rt * 0.08)
        rt = np.maximum(rt, 50)
        curves.append(LearningCurve(
            dataset_id=f"synth_{label}", subject_id=i,
            condition="default", task_type="synthetic",
            trial=t, rt=rt, n_trials=n,
        ))
    return curves


# ═══════════════════════════════════════════════════════════════════
# Preprocessing
# ═══════════════════════════════════════════════════════════════════

def normalize(curve: LearningCurve) -> NormalizedCurve:
    x, y = curve.trial.astype(float), curve.rt.astype(float)
    x_min, x_max = x.min(), x.max()
    y_mean, y_std = y.mean(), max(y.std(), 1e-10)
    return NormalizedCurve(
        x=(x - x_min) / max(x_max - x_min, 1e-10),
        y=(y - y_mean) / y_std,
        x_raw=x, y_raw=y,
        x_min=x_min, x_max=x_max,
        y_mean=y_mean, y_std=y_std,
        curve=curve,
    )


# ═══════════════════════════════════════════════════════════════════
# MAP Predictive Extraction (fast alternative to HMC)
# ═══════════════════════════════════════════════════════════════════

def extract_map_predictives(model, likelihood, x_train, y_train, x_eval,
                            n_samples=100, perturbation_scale=0.05):
    """
    MAP + Laplace-style perturbation for fast ψ extraction.
    Perturbs MAP hyperparameters in unconstrained space.
    """
    model.eval(); likelihood.eval()

    # Collect raw params
    param_refs = []
    raw_params = []
    for name, p in list(model.named_parameters()) + list(likelihood.named_parameters()):
        if p.requires_grad and p.numel() == 1:
            raw_params.append(p.data.item())
            param_refs.append((name, p))
    raw_params = np.array(raw_params)

    samples = []
    rng = np.random.RandomState(42)

    for i in range(n_samples):
        perturbed = raw_params if i == 0 else raw_params + perturbation_scale * rng.randn(len(raw_params))

        for j, (_, p) in enumerate(param_refs):
            p.data.fill_(perturbed[j])

        try:
            with torch.no_grad():
                noise_var = likelihood.noise.item()
                if noise_var < 1e-10:
                    continue
                n_train = x_train.shape[0]

                K_XX = model.covar_module(x_train, x_train).evaluate().detach()
                K_XsX = model.covar_module(x_eval, x_train).evaluate().detach()
                K_XsXs = model.covar_module(x_eval, x_eval).evaluate().detach()
                K_XXs = model.covar_module(x_train, x_eval).evaluate().detach()

                L = torch.linalg.cholesky(
                    K_XX + (noise_var + 1e-6) * torch.eye(n_train).double()
                )
                alpha = torch.cholesky_solve(y_train.unsqueeze(-1), L).squeeze(-1)
                pred_mean = (K_XsX @ alpha).numpy()

                V = torch.linalg.solve_triangular(L, K_XXs, upper=False)
                pred_cov = (K_XsXs - V.T @ V).numpy() + noise_var * np.eye(len(x_eval))

                hp_dict = {name: float(perturbed[j]) for j, (name, _) in enumerate(param_refs)}
                samples.append(GPPosteriorSample(mean=pred_mean, cov=pred_cov, hyperparameters=hp_dict))
        except (RuntimeError, np.linalg.LinAlgError):
            continue

    # Restore MAP
    for j, (_, p) in enumerate(param_refs):
        p.data.fill_(raw_params[j])

    return samples


# ═══════════════════════════════════════════════════════════════════
# Single-Subject Pipeline
# ═══════════════════════════════════════════════════════════════════

def run_one(ncurve: NormalizedCurve,
            prior_configs=None, mode="map",
            n_hmc_samples=200, n_warmup=100,
            n_eval=50, n_posterior_samples=100,
            metrics=None, taus=None, verbose=False) -> SubjectResult:
    """Full BI* pipeline for one subject."""

    t0 = time.time()
    if prior_configs is None:
        prior_configs = ["practitioner", "moderate", "agnostic"]
    if metrics is None:
        metrics = ["pw_hellinger", "pw_mse", "pw_nll"]
    if taus is None:
        taus = np.logspace(-1, 1.5, 15)

    curve = ncurve.curve
    x_train = torch.tensor(ncurve.x).double()
    y_train = torch.tensor(ncurve.y).double()
    x_eval_t = torch.linspace(0, 1, n_eval).double()
    x_eval_np = x_eval_t.numpy()

    # ── Fit candidates ──
    candidates = build_practice_candidates()
    candidate_results = []
    fitted_params = {}
    bic_log_ml = {}

    for cand in candidates:
        try:
            cand.fit(ncurve.x, ncurve.y)
            pred = cand.predict(x_eval_np)
            candidate_results.append(pred)
            fitted_params[cand.name] = pred.parameters
            bic_log_ml[cand.name] = cand.log_marginal_likelihood(ncurve.x, ncurve.y)
        except Exception as e:
            if verbose: print(f"    {cand.name} failed: {e}")
            mean = np.full(n_eval, ncurve.y.mean())
            candidate_results.append(CandidateResult(
                name=cand.name, mean=mean, cov=np.eye(n_eval) * ncurve.y.var(),
                noise_var=ncurve.y.var(), parameters={}, n_params=cand.n_free_params + 1,
            ))
            fitted_params[cand.name] = {}
            bic_log_ml[cand.name] = -np.inf

    bic_winner = max(bic_log_ml, key=bic_log_ml.get)

    # ── Run BI* across prior configs ──
    bistar_winners = {}
    bistar_probs = {}
    gp_hp = {}
    n_gp = 0

    for cfg_name in prior_configs:
        config = PRACTICE_CONFIGS[cfg_name]

        kernels, names = build_kernel(config)
        lik = build_likelihood(config)
        model, lik = build_model(x_train, y_train, kernels, names, lik)

        try:
            fit_map(model, lik, x_train, y_train, n_iter=300, lr=0.05, verbose=False)
        except Exception:
            continue

        if not gp_hp:
            gp_hp = {
                "lengthscale": model.kernel_components[0].base_kernel.lengthscale.item(),
                "outputscale": model.kernel_components[0].outputscale.item(),
                "noise": lik.noise.item(),
            }

        # Extract ψ's
        if mode == "map":
            gp_samples = extract_map_predictives(
                model, lik, x_train, y_train, x_eval_t, n_samples=n_posterior_samples,
            )
        else:
            try:
                mcmc_samples = fit_hmc(model, lik, x_train, y_train,
                                       n_samples=n_hmc_samples, n_warmup=n_warmup, verbose=False)
                gp_samples = extract_gp_predictives(
                    model, lik, x_train, y_train, x_eval_t, mcmc_samples,
                    get_kernel_builder(cfg_name), get_likelihood_builder(cfg_name),
                    n_posterior_samples=n_posterior_samples,
                )
            except Exception:
                continue

        if not gp_samples:
            continue
        n_gp = max(n_gp, len(gp_samples))

        # BMS*
        try:
            results = run_bms_star(gp_samples, candidate_results, metric_names=metrics, taus=taus)
        except Exception:
            continue

        bistar_winners[cfg_name] = {}
        bistar_probs[cfg_name] = {}

        for metric_name, tau_results in results.items():
            bistar_winners[cfg_name][metric_name] = {}
            bistar_probs[cfg_name][metric_name] = {}
            for tau, bms_r in tau_results.items():
                winner_idx = np.argmax(bms_r.class_posteriors)
                bistar_winners[cfg_name][metric_name][float(tau)] = bms_r.instance_names[winner_idx]
                bistar_probs[cfg_name][metric_name][float(tau)] = {
                    n: float(p) for n, p in zip(bms_r.instance_names, bms_r.class_posteriors)
                }

    return SubjectResult(
        dataset_id=curve.dataset_id, subject_id=curve.subject_id,
        condition=curve.condition, task_type=curve.task_type,
        n_trials=curve.n_trials,
        bistar_winners=bistar_winners, bistar_probs=bistar_probs,
        bic_log_ml=bic_log_ml, bic_winner=bic_winner,
        fitted_params=fitted_params, gp_hyperparameters=gp_hp,
        n_gp_samples=n_gp, elapsed_seconds=time.time() - t0,
    )


# ═══════════════════════════════════════════════════════════════════
# Batch Execution
# ═══════════════════════════════════════════════════════════════════

def run_all(curves, output_dir, prior_configs=None, mode="map", verbose=True, **kwargs):
    """Run BI* on all curves. Save incrementally."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    n_total = len(curves)
    print(f"\n{'='*60}")
    print(f"BMS* for Law of Practice: {n_total} learning curves")
    print(f"Mode: {mode} | Configs: {prior_configs or ['practitioner','moderate','agnostic']}")
    print(f"Output: {output_dir}")
    print(f"{'='*60}\n")

    results = []
    for i, curve in enumerate(curves):
        label = f"{curve.dataset_id}/sub{curve.subject_id}"
        if verbose:
            print(f"[{i+1}/{n_total}] {label} ({curve.n_trials}t)...", end=" ", flush=True)

        ncurve = normalize(curve)
        if ncurve.curve.n_trials < 8:
            if verbose: print("SKIP")
            continue

        try:
            r = run_one(ncurve, prior_configs=prior_configs, mode=mode, verbose=False, **kwargs)
            results.append(r)
            if verbose:
                print(f"BIC={r.bic_winner} t={r.elapsed_seconds:.1f}s")

            path = output_dir / f"{curve.dataset_id}_sub{curve.subject_id}_{curve.condition}.json"
            _save_json(r, path)
        except Exception as e:
            if verbose: print(f"FAIL: {e}")

    _print_aggregate(results, output_dir)
    return results


def _save_json(result: SubjectResult, path: Path):
    d = {
        "dataset_id": result.dataset_id, "subject_id": result.subject_id,
        "condition": result.condition, "task_type": result.task_type,
        "n_trials": result.n_trials, "bic_winner": result.bic_winner,
        "bic_log_ml": result.bic_log_ml, "fitted_params": result.fitted_params,
        "gp_hyperparameters": result.gp_hyperparameters,
        "n_gp_samples": result.n_gp_samples, "elapsed_seconds": result.elapsed_seconds,
        "bistar_winners": _strkeys(result.bistar_winners),
        "bistar_probs": _strkeys(result.bistar_probs),
    }
    with open(path, 'w') as f:
        json.dump(d, f, indent=2, default=str)


def _strkeys(d):
    if not isinstance(d, dict): return d
    return {str(k): _strkeys(v) for k, v in d.items()}


def _print_aggregate(results, output_dir):
    """Print and save summary statistics."""
    if not results:
        return

    n = len(results)

    # BIC
    bic_counts = {}
    for r in results:
        bic_counts[r.bic_winner] = bic_counts.get(r.bic_winner, 0) + 1

    # BI* at median tau
    bistar_counts = {}
    for r in results:
        for cfg, metrics_d in r.bistar_winners.items():
            bistar_counts.setdefault(cfg, {})
            for metric, tau_d in metrics_d.items():
                bistar_counts[cfg].setdefault(metric, {})
                taus = sorted(float(t) for t in tau_d.keys())
                if taus:
                    ref_tau = taus[len(taus) // 2]
                    w = tau_d.get(ref_tau, tau_d.get(str(ref_tau), "?"))
                    bistar_counts[cfg][metric][w] = bistar_counts[cfg][metric].get(w, 0) + 1

    # Robustness
    configs = list(bistar_counts.keys())
    robustness = {}
    if len(configs) >= 2:
        for r in results:
            for metric in r.bistar_winners.get(configs[0], {}):
                robustness.setdefault(metric, {"agree": 0, "disagree": 0})
                winners = set()
                for cfg in configs:
                    td = r.bistar_winners.get(cfg, {}).get(metric, {})
                    taus = sorted(float(t) for t in td.keys())
                    if taus:
                        winners.add(td.get(taus[len(taus)//2], td.get(str(taus[len(taus)//2]))))
                if len(winners) == 1:
                    robustness[metric]["agree"] += 1
                elif len(winners) > 1:
                    robustness[metric]["disagree"] += 1

    # Print
    print(f"\n{'='*60}")
    print(f"RESULTS ({n} subjects)")
    print(f"{'='*60}")

    print(f"\nBIC winners:")
    for m, c in sorted(bic_counts.items(), key=lambda x: -x[1]):
        print(f"  {m}: {c}/{n} ({100*c/n:.1f}%)")

    print(f"\nBI* winners (median τ):")
    for cfg, metrics in bistar_counts.items():
        print(f"\n  [{cfg}]")
        for metric, counts in metrics.items():
            total = sum(counts.values())
            parts = ", ".join(f"{m}:{c}" for m, c in sorted(counts.items(), key=lambda x: -x[1]))
            print(f"    {metric}: {parts}")

    if robustness:
        print(f"\nRobustness (all configs agree):")
        for metric, c in robustness.items():
            total = c["agree"] + c["disagree"]
            if total: print(f"  {metric}: {100*c['agree']/total:.1f}%")

    # Save
    agg = {"n": n, "bic": bic_counts, "bistar": bistar_counts, "robustness": robustness}
    with open(output_dir / "aggregate.json", 'w') as f:
        json.dump(agg, f, indent=2, default=str)

    print(f"\n{'='*60}\n")


# ═══════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════

def main():
    p = argparse.ArgumentParser(description="BMS* for Law of Practice")
    p.add_argument("--data_dir", default="./data")
    p.add_argument("--output_dir", default="./results")
    p.add_argument("--mode", default="map", choices=["map", "hmc"])
    p.add_argument("--n_hmc_samples", type=int, default=200)
    p.add_argument("--n_eval", type=int, default=50)
    p.add_argument("--n_posterior_samples", type=int, default=100)
    p.add_argument("--configs", nargs="+", default=["practitioner", "moderate", "agnostic"])
    p.add_argument("--demo", action="store_true", help="Synthetic test data")
    args = p.parse_args()

    curves = generate_demo_data(50) if args.demo else load_data(args.data_dir)
    if not curves:
        print("No data. Use --demo."); return

    print(f"Loaded {len(curves)} learning curves")
    run_all(curves, args.output_dir, prior_configs=args.configs, mode=args.mode,
            n_hmc_samples=args.n_hmc_samples, n_eval=args.n_eval,
            n_posterior_samples=args.n_posterior_samples)


if __name__ == "__main__":
    main()
