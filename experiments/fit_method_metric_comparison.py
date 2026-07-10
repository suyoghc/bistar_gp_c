"""
Comparative results run: fit_gp method x G-metric grid on the thesis toy problem.

Runs the full BMS* pipeline on sin(x) + 0.25x, N=20 (the thesis chapter's toy,
generate_toy_data defaults) across all four GP hyperparameter-inference options
(D9: hmc, vi, map, hmc_laplace) and the main divergence-metric options
(D10: pw_kl_vcal, pw_nll_gp, pw_kl_mean, pw_hellinger_vcal, kl_forward), so the
defaults can be chosen on results rather than on argument alone
(docs/inference-and-metric-options.md section 3).

Per (method x metric) cell: BMS* model posteriors at several tau values plus the
hard best-match win fractions (the thesis chapter's own aggregation, tau -> 0).
Per method: hyperparameter posterior summaries (mean/sd/quantiles, crude ESS),
including the VI-vs-HMC agreement check the thesis ran in Appendix II.

Outputs:
    docs/fit-method-metric-comparison.md            (generated tables)
    runs/fit_method_metric_comparison/results.json  (raw numbers)

Usage:
    python experiments/fit_method_metric_comparison.py            # full run
    python experiments/fit_method_metric_comparison.py --quick    # smoke test
    python experiments/fit_method_metric_comparison.py --methods hmc vi
"""

import sys, os, json, time, argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import torch

from bistar_gp import generate_toy_data, build_model
from bistar_gp.fit import fit_map, fit_gp, GP_INFERENCE_METHODS
from bistar_gp.candidates import build_toy_candidates
from bistar_gp.config import (
    PRIOR_CONFIGS, build_kernels_from_config, build_likelihood_from_config,
)
from bistar_gp.bms_star import extract_gp_predictives, run_bms_star
import bistar_gp.metrics_v2  # noqa: F401 — registers pw_kl_vcal etc. into METRICS

torch.set_default_dtype(torch.float64)

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RUN_DIR = os.path.join(REPO_ROOT, "runs", "fit_method_metric_comparison")
# Canonical outputs (full runs only; --quick writes *_quick files under runs/
# so a smoke test can never masquerade as the real comparison).
DOC_PATH = os.path.join(REPO_ROOT, "docs", "fit-method-metric-comparison.md")
JSON_PATH = os.path.join(RUN_DIR, "results.json")

SEED = 42
PRIOR_NAME = "informative"          # the repo's default GP hyperprior config
METRICS = ["pw_kl_vcal", "pw_nll_gp", "pw_kl_mean", "pw_hellinger_vcal",
           "kl_forward"]
TAUS = [0.1, 0.3, 1.0, 3.0, 10.0]
TAU_MAIN = 1.0                      # tau for the headline table

SITE_LABELS = {
    "covar_module.kernels.0.base_kernel.lengthscale_prior": "SE lengthscale",
    "covar_module.kernels.0.outputscale_prior": "SE outputscale",
    "covar_module.kernels.1.variance_prior": "Linear variance",
    "likelihood.noise_covar.noise_prior": "Noise variance",
}


def crude_ess(chain: np.ndarray) -> float:
    """Effective sample size via Geyer's initial positive sequence — a chain
    diagnostic for the mixing comparison (hmc vs hmc_laplace), not paper-grade
    (single chain, no rank-normalization)."""
    n = len(chain)
    if n < 8 or np.std(chain) == 0:
        return float(n)
    c = chain - chain.mean()
    acov = np.correlate(c, c, "full")[n - 1:] / n
    rho = acov / acov[0]
    tau = 1.0
    for k in range(1, (n - 1) // 2 + 1):
        pair = rho[2 * k - 1] + rho[2 * k]
        if pair < 0:
            break
        tau += 2.0 * pair
    return float(n / tau)


def method_budgets(quick: bool, max_tree_depth=None) -> dict:
    """Per-method fit_gp kwargs. The thesis (App. II) used 10,000 samples with
    1,000 burn-in on its 3-parameter toy; 2,000/1,000 here is the practical
    scale for the 4-hyperparameter toy (a disclosed deviation, see
    docs/inference-and-metric-options.md 'known practical deviations').

    max_tree_depth: when set, injected into the two NUTS methods (hmc,
    hmc_laplace); vi/map have no tree depth. None leaves fit_hmc's pyro
    default of 10 (up to 1023 leapfrog steps/iteration). The capped arm uses
    7 (up to 127 steps), the D8-validated cost/exploration knee — see
    docs/appendix-tree-depth-cap.md."""
    if quick:
        budgets = {
            "hmc": dict(n_samples=20, n_warmup=20, verbose=False, seed=SEED,
                        max_tree_depth=6),
            "vi": dict(n_samples=50, n_steps=100, verbose=False, seed=SEED),
            "map": dict(n_iter=100),
            "hmc_laplace": dict(n_samples=20, n_warmup=20, verbose=False,
                                seed=SEED, max_tree_depth=6),
        }
    else:
        budgets = {
            "hmc": dict(n_samples=2000, n_warmup=1000, verbose=False, seed=SEED),
            "vi": dict(n_samples=2000, n_steps=5000, verbose=False, seed=SEED),
            "map": dict(n_iter=500),
            "hmc_laplace": dict(n_samples=2000, n_warmup=1000, verbose=False,
                                seed=SEED),
        }
    if max_tree_depth is not None:
        for m in ("hmc", "hmc_laplace"):
            budgets[m]["max_tree_depth"] = max_tree_depth
    return budgets


def run_one_method(method, kwargs, prior_config, x_train, y_train, x_eval,
                   candidate_results, n_posterior_samples,
                   cache_path=None, force_refit=False):
    """MAP-fit a fresh model, run fit_gp(method), extract predictives, BMS*.

    cache_path: if set, raw fit_gp draws are loaded from / saved to this .npz —
    the sampler cost (hours for the NUTS methods) is decoupled from the cheap
    candidate/metric/tau side, which can then be recomputed freely.
    """
    kernels, names = build_kernels_from_config(prior_config)
    likelihood = build_likelihood_from_config(prior_config)
    model, likelihood = build_model(x_train, y_train, kernels, names, likelihood)

    if cache_path and os.path.exists(cache_path) and not force_refit:
        with np.load(cache_path) as z:
            samples = {k: z[k] for k in z.files if k != "_fit_seconds"}
            fit_seconds = float(z["_fit_seconds"])
        print(f"  loaded cached draws <- {cache_path}")
    else:
        torch.manual_seed(SEED)
        # Timer covers the shared MAP prefit too: it is part of every
        # method's real cost (hmc/vi/hmc_laplace initialize from it). For
        # method="map" the prefit plus fit_map_samples' own fit_map is
        # continued Adam optimization of the same objective — the reported
        # point is the more-converged one.
        t0 = time.time()
        fit_map(model, likelihood, x_train, y_train, n_iter=300, lr=0.05,
                verbose=False)
        samples = fit_gp(model, likelihood, x_train, y_train, method=method,
                         **kwargs)
        fit_seconds = time.time() - t0
        if cache_path:
            np.savez(cache_path, _fit_seconds=fit_seconds, **samples)
            print(f"  cached draws -> {cache_path}")

    summaries = {}
    for site, draws in samples.items():
        q = np.quantile(draws, [0.05, 0.5, 0.95]) if len(draws) > 1 \
            else np.repeat(draws[0], 3)
        summaries[site] = {
            "n": int(len(draws)),
            "mean": float(draws.mean()),
            "sd": float(draws.std()),
            "q05": float(q[0]), "q50": float(q[1]), "q95": float(q[2]),
            "ess": crude_ess(draws) if len(draws) > 1 else None,
        }

    np.random.seed(SEED)   # extract_gp_predictives subsamples via np.random
    gp_samples = extract_gp_predictives(
        model, likelihood, x_train, y_train, x_eval, samples,
        kernel_builder=lambda: build_kernels_from_config(prior_config),
        likelihood_builder=lambda: build_likelihood_from_config(prior_config),
        n_posterior_samples=n_posterior_samples, jitter=1e-4,
    )
    if not gp_samples:
        raise RuntimeError(f"{method}: no valid GP predictives extracted")

    results = run_bms_star(gp_samples, candidate_results, METRICS,
                           np.array(TAUS))

    per_metric = {}
    for metric in METRICS:
        bms_by_tau = results[metric]
        G = bms_by_tau[TAUS[0]].G_matrix          # same G for every tau
        winners = np.argmin(G, axis=1)
        win_frac = [float(np.mean(winners == j))
                    for j in range(G.shape[1])]
        per_metric[metric] = {
            "posteriors": {str(tau): [float(p) for p in
                                      bms_by_tau[tau].instance_posteriors]
                           for tau in TAUS},
            "hard_win_fractions": win_frac,
        }

    return {
        "fit_seconds": fit_seconds,
        "n_draws": int(len(samples[next(iter(samples))])),
        "n_predictives": len(gp_samples),
        "hyperparameters": summaries,
        "metrics": per_metric,
    }


# ── Markdown rendering ─────────────────────────────────────────────

def _prob_row(cells):
    return " | ".join(f"{p:.3f}" for p in cells)


def render_markdown(out, model_names, budgets, data_desc):
    lines = [
        "# fit_gp method x G-metric comparison under the `informative` "
        "prior — the prior-misspecification case study (thesis toy)",
        "",
        "Generated by `experiments/fit_method_metric_comparison.py` "
        "(rerun to regenerate; observations are logged in "
        "`Notes/DECISIONS.md`, not here).",
        "",
        "Role (D18 ratification, 2026-07-09): the grid below documents the "
        "`informative` prior-misspecification / bimodality case study. The "
        "paper's final N=20 toy numbers use the re-elicited `toy_elicited` "
        "prior instead (registry entry `toy_elicited_n20`); see "
        "`docs/prior-sensitivity-study.md` and Notes/DECISIONS.md D18.",
        "",
        f"- Data: {data_desc}",
        f"- GP hyperprior config: `{PRIOR_NAME}` (SE + Linear kernels)",
        f"- Candidates: {', '.join(model_names)} (MLE-fitted)",
        f"- Metrics: {', '.join(METRICS)}",
        f"- Budgets: " + "; ".join(
            f"{m}: " + ", ".join(f"{k}={v}" for k, v in kw.items()
                                 if k not in ("verbose",))
            for m, kw in budgets.items()),
        "",
        f"## Model posteriors at tau = {TAU_MAIN}",
        "",
        "| method | metric | " + " | ".join(model_names) + " | top model |",
        "|---|---|" + "---|" * (len(model_names) + 1),
    ]
    for method, res in out["methods"].items():
        for metric in METRICS:
            probs = res["metrics"][metric]["posteriors"][str(TAU_MAIN)]
            top = model_names[int(np.argmax(probs))]
            lines.append(f"| {method} | {metric} | {_prob_row(probs)} | {top} |")

    lines += [
        "",
        "## Hard best-match win fractions (thesis aggregation, tau -> 0)",
        "",
        "Fraction of GP posterior draws for which each candidate is the "
        "argmin-G best match (p. 174's assignment rule).",
        "",
        "| method | metric | " + " | ".join(model_names) + " |",
        "|---|---|" + "---|" * len(model_names),
    ]
    for method, res in out["methods"].items():
        for metric in METRICS:
            wf = res["metrics"][metric]["hard_win_fractions"]
            lines.append(f"| {method} | {metric} | {_prob_row(wf)} |")

    lines += [
        "",
        "## tau sensitivity (posterior of the tau=1 top model)",
        "",
        "| method | metric | " + " | ".join(f"tau={t}" for t in TAUS)
        + " | rank stable? |",
        "|---|---|" + "---|" * (len(TAUS) + 1),
    ]
    for method, res in out["methods"].items():
        for metric in METRICS:
            post = res["metrics"][metric]["posteriors"]
            j = int(np.argmax(post[str(TAU_MAIN)]))
            row = [post[str(t)][j] for t in TAUS]
            tops = {int(np.argmax(post[str(t)])) for t in TAUS}
            stable = "yes" if tops == {j} else \
                "no (" + ", ".join(model_names[k] for k in sorted(tops)) + ")"
            lines.append(f"| {method} | {metric} | {_prob_row(row)} | {stable} |")

    lines += [
        "",
        "## Hyperparameter posterior summaries per method",
        "",
        "Constrained space. ESS is a crude single-chain Geyer estimate "
        "(mixing indicator only). MAP rows are point estimates.",
        "",
        "| method | hyperparameter | mean | sd | q05 | q50 | q95 | ESS | fit s |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for method, res in out["methods"].items():
        for site, label in SITE_LABELS.items():
            s = res["hyperparameters"][site]
            ess = f"{s['ess']:.0f}" if s["ess"] is not None else "—"
            lines.append(
                f"| {method} | {label} | {s['mean']:.4f} | {s['sd']:.4f} | "
                f"{s['q05']:.4f} | {s['q50']:.4f} | {s['q95']:.4f} | {ess} | "
                f"{res['fit_seconds']:.0f} |")

    if "hmc" in out["methods"] and "vi" in out["methods"]:
        lines += [
            "",
            "## VI vs HMC agreement (thesis Appendix II cross-check)",
            "",
            "The thesis reported VI (primary) and HMC (cross-check) gave "
            "'similar' results on this toy. abs(Δmean) / pooled sd compares "
            "the two posteriors per hyperparameter; the last column is the "
            "max absolute model-posterior difference at tau = 1 per metric.",
            "",
            "| hyperparameter | HMC mean±sd | VI mean±sd | abs(Δmean)/sd |",
            "|---|---|---|---|",
        ]
        for site, label in SITE_LABELS.items():
            h = out["methods"]["hmc"]["hyperparameters"][site]
            v = out["methods"]["vi"]["hyperparameters"][site]
            pooled = np.sqrt(0.5 * (h["sd"] ** 2 + v["sd"] ** 2))
            z = abs(h["mean"] - v["mean"]) / pooled if pooled > 0 else np.inf
            lines.append(
                f"| {label} | {h['mean']:.4f}±{h['sd']:.4f} | "
                f"{v['mean']:.4f}±{v['sd']:.4f} | {z:.2f} |")
        lines += ["", "| metric | max abs(Δposterior) (HMC vs VI, tau=1) |",
                  "|---|---|"]
        for metric in METRICS:
            ph = out["methods"]["hmc"]["metrics"][metric]["posteriors"][str(TAU_MAIN)]
            pv = out["methods"]["vi"]["metrics"][metric]["posteriors"][str(TAU_MAIN)]
            d = max(abs(a - b) for a, b in zip(ph, pv))
            lines.append(f"| {metric} | {d:.3f} |")

    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("--quick", action="store_true",
                        help="tiny budgets, smoke test only")
    parser.add_argument("--methods", nargs="+", default=None,
                        choices=list(GP_INFERENCE_METHODS))
    parser.add_argument("--n-predictives", type=int, default=200,
                        help="GP predictive draws fed to BMS* per method")
    parser.add_argument("--render-only", action="store_true",
                        help="regenerate the markdown from the saved JSON")
    parser.add_argument("--force-refit", action="store_true",
                        help="ignore cached fit_gp draws and re-run samplers")
    parser.add_argument("--out-suffix", default="",
                        help="suffix for json/md outputs under runs/ (used by "
                             "parallel cache-population runs so they don't "
                             "clobber the canonical files)")
    parser.add_argument("--max-tree-depth", type=int, default=None,
                        help="NUTS tree-depth cap for hmc/hmc_laplace (pyro "
                             "default 10 if unset). The capped appendix arm "
                             "uses 7; capped draws cache separately as "
                             "samples_<method>_td<N>.npz so they never "
                             "overwrite the uncapped draws.")
    args = parser.parse_args()

    if args.render_only:
        with open(JSON_PATH) as f:
            out = json.load(f)
        md = render_markdown(out, out["model_names"],
                             out["config"]["budgets"], out["config"]["data"])
        with open(DOC_PATH, "w") as f:
            f.write(md)
        print(f"Tables -> {DOC_PATH}")
        return

    methods = args.methods or list(GP_INFERENCE_METHODS)
    budgets = method_budgets(args.quick, max_tree_depth=args.max_tree_depth)
    prior_config = PRIOR_CONFIGS[PRIOR_NAME]
    td_tag = f"_td{args.max_tree_depth}" if args.max_tree_depth is not None \
        else ""
    # An explicit --out-suffix wins; otherwise a capped run auto-tags (td_tag)
    # so it never overwrites the canonical uncapped table.
    out_suffix = args.out_suffix or td_tag
    if args.quick:
        json_path = os.path.join(RUN_DIR, "results_quick.json")
        doc_path = os.path.join(RUN_DIR, "tables_quick.md")
    elif out_suffix:
        json_path = os.path.join(RUN_DIR, f"results{out_suffix}.json")
        doc_path = os.path.join(RUN_DIR, f"tables{out_suffix}.md")
    else:
        json_path, doc_path = JSON_PATH, DOC_PATH

    x_train, y_train, info = generate_toy_data()   # thesis toy: N=20, defaults
    x_np, y_np = x_train.numpy(), y_train.numpy()
    x_eval = np.linspace(x_np.min() - 1, x_np.max() + 1, 60)
    x_eval_torch = torch.tensor(x_eval).double()
    data_desc = (f"sin(x) + {info['bias_slope']}x + N(0, {info['noise_std']}^2), "
                 f"N={len(x_train)}, x in [{x_np.min():.0f}, {x_np.max():.0f}], "
                 f"seed={SEED}")
    print(f"Data: {data_desc}")

    candidates = build_toy_candidates()
    candidate_results = []
    for cand in candidates:
        cand.fit(x_np, y_np)
        cr = cand.predict(x_eval)
        candidate_results.append(cr)
        print(f"  candidate {cr.name:<12} sigma={cr.noise_var ** 0.5:.4f}")
    model_names = [cr.name for cr in candidate_results]

    out = {
        "config": {"seed": SEED, "prior": PRIOR_NAME, "metrics": METRICS,
                   "taus": TAUS, "quick": args.quick, "data": data_desc,
                   "n_predictives": args.n_predictives,
                   "budgets": {m: {k: v for k, v in kw.items()
                                   if k != "verbose"}
                               for m, kw in budgets.items()}},
        "model_names": model_names,
        "methods": {},
    }

    os.makedirs(RUN_DIR, exist_ok=True)
    for method in methods:
        print(f"\n{'=' * 60}\n  method = {method}\n{'=' * 60}")
        # quick draws must never be reused; capped draws carry a _td<N> tag so
        # they never overwrite the uncapped samples_<method>.npz.
        cache_path = None if args.quick else os.path.join(
            RUN_DIR, f"samples_{method}{td_tag}.npz")
        out["methods"][method] = run_one_method(
            method, budgets[method], prior_config, x_train, y_train,
            x_eval_torch, candidate_results, args.n_predictives,
            cache_path=cache_path, force_refit=args.force_refit)
        print(f"  fit took {out['methods'][method]['fit_seconds']:.1f}s, "
              f"{out['methods'][method]['n_draws']} draws, "
              f"{out['methods'][method]['n_predictives']} predictives")

    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with open(json_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nRaw results -> {json_path}")

    md = render_markdown(out, model_names, budgets, data_desc)
    with open(doc_path, "w") as f:
        f.write(md)
    print(f"Tables      -> {doc_path}")


if __name__ == "__main__":
    main()
