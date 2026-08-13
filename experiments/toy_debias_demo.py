"""Case E — toy debias demonstration: evaluation and mitigation from one posterior.

The thesis (ch. 5) and the accepted proposal set two goals for the BI*/BMS*-GP
program: model evaluation through data priors, and bias mitigation. Manuscript
sections 1-6 and 8 deliver the first. This script supplies the second as a
small, self-contained demonstration on the synthetic toy whose bias process is
known by construction.

Data
----
`bistar_gp.generate_toy_data()` at its defaults: N=20, x on [-10, 10], seed 42,
observation noise 0.5, and y = sin(x) + 0.25 x + noise. The generator itself
names the linear term the bias (``bias_slope=0.25``; the returned info dict
carries ``true_signal``, ``bias``, and ``combined``). The demonstration treats
the sinusoid as the true process and the linear drift as the bias process.

Method
------
1. Fit the SE + linear additive GP under the `toy_elicited` prior
   (``PRIOR_CONFIGS["toy_elicited_n20"]``, byte-identical to the in-script
   `toy_elicited` entry of ``experiments/prior_sensitivity_study.py``).
   Hyperparameters are sampled on the CORRECTED NUTS path, ``bistar_gp.fit
   .fit_hmc`` (the ``nuts_e1`` sampler), in two seeded chains.
2. Decompose every retained draw's GP posterior additively with the package
   machinery ``bistar_gp.decompose.decompose_additive_gp``: the SE component is
   the truth candidate, the linear component the bias candidate. The joint
   posterior of f = f_SE + f_lin comes from ``decompose_component`` applied to
   the summed kernel blocks, so it retains the inter-component cross-covariance
   that a sum of component covariances would drop.
3. Debias by marginalization. Within a draw, the SE-component posterior that
   ``decompose_additive_gp`` returns is already marginal over the linear
   component (it is the marginal of the joint conditional Gaussian). Across
   draws, hyperparameters are marginalized by Monte Carlo. The debiased
   predictive is therefore the finite mixture over retained draws d of
   N(m_SE^d(x), v_SE^d(x)).

Band and interval conventions
-----------------------------
Bands are latent-function intervals with no observation noise added, matching
the convention documented in ``experiments/honest_band_decomposition.py`` and
used by the existing decomposition figures. Summary standard deviations use the
law of total variance,

    total_var(x) = mean_d[ within-draw var(x) ] + var_d[ within-draw mean(x) ],

and reported intervals are EXACT central intervals of the Gaussian mixture,
obtained by bisecting its CDF rather than by a mean +/- 2 sd approximation.
(That helper is read here for its convention only; it returns summary bands
alone, whereas the recovery numbers below need per-draw component moments, so
this script runs its own single pass over the package decomposition.)

Recovered bias slope
--------------------
gpytorch's ``LinearKernel`` has k(x, x') = v x x', so the linear component is
f_lin(x) = b x with b ~ N(0, v) a priori. Consequently the component posterior
mean is exactly linear in x and the component posterior covariance is exactly
the rank-one matrix Var(b | theta) x x^T. Both properties are verified
numerically for every draw and the worst deviations are reported in
``results.json``. The per-draw slope moments are read off the decomposition
output as

    E[b | y, theta] = (m_lin(x_max) - m_lin(x_min)) / (x_max - x_min),
    Var(b | y, theta) = cov_lin(x_ref, x_ref) / x_ref^2,

so no separate formula is introduced: the slope posterior is a functional of
the same component decomposition the figure plots.

Scope
-----
Synthetic toy only. NO Mauna Loa material of any kind is imported, executed, or
cited: the D58 preregistration boundary stands and the real-data development
belongs to the companion line. Identifying "bias" with the linear component is
a modeling CHOICE, licensed here because the generator built the data that way.

Rerun (from the repository root):

    python experiments/toy_debias_demo.py

Outputs land in ``runs/toy_debias_demo/``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import warnings
from pathlib import Path

import numpy as np
import torch
from scipy.special import ndtr

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from bistar_gp import build_model, generate_toy_data                # noqa: E402
from bistar_gp.config import (                                      # noqa: E402
    PRIOR_CONFIGS,
    build_kernels_from_config,
    build_likelihood_from_config,
)
from bistar_gp.decompose import (                                   # noqa: E402
    compute_cholesky,
    decompose_additive_gp,
    decompose_component,
)
from bistar_gp.fit import fit_hmc, fit_map                          # noqa: E402
from bistar_gp.model import apply_hp_value, select_hmc_sites        # noqa: E402

# ── Frozen configuration ─────────────────────────────────────────────────────

PRIOR_KEY = "toy_elicited_n20"          # == prior_sensitivity_study `toy_elicited`
MAP_SEED = 42                           # torch seed for the shared MAP init
MAP_ITERS = 500
MAP_LR = 0.05
CHAIN_SEEDS = (20260813, 20260814)      # one pyro seed per chain
N_WARMUP = 500                          # per chain
N_DRAWS = 500                           # retained per chain
MAX_TREE_DEPTH = 8
TARGET_ACCEPT = 0.8                     # fixed inside fit_hmc_e1
INIT_STEP_SIZE = 0.1                    # fixed inside fit_hmc_e1, then adapted
DECOMP_JITTER = 1e-4                    # matches the existing figure scripts

GRID_LO, GRID_HI, GRID_N = -10.0, 10.0, 201
CREDIBLE_MASS = 0.95
SLOPE_VAR_MIN_ABS_X = 1.0               # |x| floor for the rank-one variance read
BISECT_ITERS = 100

TRUTH_COMPONENT = "unbiased_se"         # truth candidate
BIAS_COMPONENT = "bias_linear"          # bias candidate

COLOR_PRIMARY = "#2E6FB8"               # posterior means and bands
COLOR_REFERENCE = "#C4356B"             # known generating curves
COLOR_BIAS = "#E08214"                  # bias-candidate component
COLOR_DATA = "#222222"


# ── Fitting ──────────────────────────────────────────────────────────────────


def _fresh_model(prior_config, x, y):
    kernels, names = build_kernels_from_config(prior_config)
    likelihood = build_likelihood_from_config(prior_config)
    model, likelihood = build_model(x, y, kernels, names, likelihood)
    return model, likelihood, names


def _map_fitted_model(prior_config, x, y):
    """A freshly built model driven to the same MAP point every time.

    Both chains start from this point, so R-hat below is WITHIN-MODE evidence:
    it reports mixing around the mode the MAP optimizer selected, not
    between-mode agreement from dispersed starts. The toy hyperparameter
    posterior is known to be multi-basin (D12), which is exactly why the
    disclosure matters.
    """
    model, likelihood, names = _fresh_model(prior_config, x, y)
    torch.manual_seed(MAP_SEED)
    fit_map(model, likelihood, x, y, n_iter=MAP_ITERS, lr=MAP_LR, verbose=False)
    return model, likelihood, names


def _map_point(model, likelihood):
    return {
        "se_lengthscale": float(model.kernel_components[0].base_kernel.lengthscale.item()),
        "se_outputscale": float(model.kernel_components[0].outputscale.item()),
        "linear_variance": float(model.kernel_components[1].variance.item()),
        "noise_variance": float(likelihood.noise.item()),
    }


def run_chains(prior_config, x, y, *, verbose):
    """One MAP-initialized nuts_e1 chain per seed; returns samples + diagnostics."""
    chain_samples, chain_diagnostics, map_points = [], [], []
    for seed in CHAIN_SEEDS:
        model, likelihood, _ = _map_fitted_model(prior_config, x, y)
        map_points.append(_map_point(model, likelihood))
        samples, diagnostics = fit_hmc(
            model, likelihood, x, y,
            n_samples=N_DRAWS, n_warmup=N_WARMUP, verbose=False, seed=seed,
            init_to_map=True, max_tree_depth=MAX_TREE_DEPTH,
            return_diagnostics=True,
        )
        chain_samples.append({k: np.asarray(v, dtype=float).reshape(-1)
                              for k, v in samples.items()})
        chain_diagnostics.append(diagnostics)
        if verbose:
            print(f"  chain seed {seed}: {N_DRAWS} draws, "
                  f"{len(diagnostics.divergence_draws[0])} divergences")
    if len({tuple(sorted(p.items())) for p in map_points}) != 1:
        raise RuntimeError("MAP init differed between chains; determinism broken")
    return chain_samples, chain_diagnostics, map_points[0]


def sampler_diagnostics_block(chain_samples, chain_diagnostics):
    """Rank-normalized R-hat and bulk/tail ESS across the seeded chains."""
    import arviz as az

    sites = list(chain_samples[0].keys())
    posterior = {site: np.stack([chain[site] for chain in chain_samples])
                 for site in sites}
    idata = az.from_dict(posterior=posterior)
    rhat = {s: float(np.asarray(az.rhat(idata, method="rank")[s])) for s in sites}
    ess_bulk = {s: float(np.asarray(az.ess(idata, method="bulk")[s])) for s in sites}
    ess_tail = {s: float(np.asarray(az.ess(idata, method="tail")[s])) for s in sites}

    cap = 2 ** MAX_TREE_DEPTH - 1
    saturated = sum(int(n >= cap)
                    for d in chain_diagnostics for chain in d.leapfrog_counts
                    for n in chain)
    n_leapfrog_draws = sum(len(chain)
                           for d in chain_diagnostics for chain in d.leapfrog_counts)
    return {
        "sampler": chain_diagnostics[0].sampler,
        "chains": len(chain_samples),
        "chain_seeds": list(CHAIN_SEEDS),
        "warmup_per_chain": N_WARMUP,
        "draws_per_chain": N_DRAWS,
        "draws_total": N_DRAWS * len(chain_samples),
        "target_accept_prob": TARGET_ACCEPT,
        "max_tree_depth": MAX_TREE_DEPTH,
        "initial_step_size": INIT_STEP_SIZE,
        "step_size_adapted": True,
        "final_step_size_by_chain": [
            None if d.step_size is None else float(d.step_size)
            for d in chain_diagnostics],
        "divergences_by_chain": [int(sum(len(c) for c in d.divergence_draws))
                                 for d in chain_diagnostics],
        "divergences_total": int(sum(len(c) for d in chain_diagnostics
                                     for c in d.divergence_draws)),
        "acceptance_rate_by_chain": [float(d.acceptance_rate[0])
                                     for d in chain_diagnostics],
        "depth_saturated_draws": saturated,
        "depth_saturation_rate": (saturated / n_leapfrog_draws
                                  if n_leapfrog_draws else None),
        "r_hat_rank_normalized": rhat,
        "r_hat_max": float(max(rhat.values())),
        "ess_bulk": ess_bulk,
        "ess_bulk_min": float(min(ess_bulk.values())),
        "ess_tail": ess_tail,
        "ess_tail_min": float(min(ess_tail.values())),
        "arviz_version": az.__version__,
    }


# ── Decomposition over draws ─────────────────────────────────────────────────


def decompose_draws(prior_config, x, y, x_grid, pooled_samples):
    """Per-draw component and joint posterior moments from the package machinery.

    Returns arrays of shape (n_ok, n_grid) for each component mean/variance and
    for the joint posterior, plus the per-draw bias-slope moments and the
    structure checks that license the slope read.
    """
    sites = select_hmc_sites(pooled_samples.keys())
    n_total = len(next(iter(pooled_samples.values())))
    xg = x_grid.numpy()
    span = xg[-1] - xg[0]
    var_idx = np.flatnonzero(np.abs(xg) >= SLOPE_VAR_MIN_ABS_X)

    comp_mean = {TRUTH_COMPONENT: [], BIAS_COMPONENT: []}
    comp_var = {TRUTH_COMPONENT: [], BIAS_COMPONENT: []}
    joint_mean, joint_var = [], []
    slope_mean, slope_var, chain_of_draw = [], [], []
    max_linearity_dev = 0.0
    max_rank_one_dev = 0.0
    n_fail = 0

    for i in range(n_total):
        kernels_i, names_i = build_kernels_from_config(prior_config)
        likelihood_i = build_likelihood_from_config(prior_config)
        model_i, likelihood_i = build_model(x, y, kernels_i, names_i, likelihood_i)
        for site in sites:
            apply_hp_value(model_i, likelihood_i, site, float(pooled_samples[site][i]))
        model_i.eval()
        likelihood_i.eval()
        noise_var = likelihood_i.noise.item()
        blocks = model_i.get_component_kernel_matrices(x, x_grid)

        with torch.no_grad():
            try:
                per_component = decompose_additive_gp(
                    [blocks[n]["XX"] for n in names_i],
                    [blocks[n]["XstarX"] for n in names_i],
                    [blocks[n]["XstarXstar"] for n in names_i],
                    [blocks[n]["XXstar"] for n in names_i],
                    noise_var, y, DECOMP_JITTER,
                )
                chol = compute_cholesky(
                    sum(blocks[n]["XX"] for n in names_i), noise_var, DECOMP_JITTER)
                f_mean, f_cov = decompose_component(
                    sum(blocks[n]["XstarX"] for n in names_i),
                    sum(blocks[n]["XstarXstar"] for n in names_i),
                    sum(blocks[n]["XXstar"] for n in names_i),
                    chol, y,
                )
            except RuntimeError:
                n_fail += 1
                continue

        moments = dict(zip(names_i, per_component))
        for name in (TRUTH_COMPONENT, BIAS_COMPONENT):
            m_i, c_i = moments[name]
            comp_mean[name].append(m_i.numpy())
            comp_var[name].append(np.clip(np.diag(c_i.numpy()), 0.0, None))

        m_lin = moments[BIAS_COMPONENT][0].numpy()
        c_lin = moments[BIAS_COMPONENT][1].numpy()
        b_hat = (m_lin[-1] - m_lin[0]) / span
        var_candidates = np.diag(c_lin)[var_idx] / xg[var_idx] ** 2
        b_var = float(var_candidates[-1])
        max_linearity_dev = max(max_linearity_dev,
                                float(np.max(np.abs(m_lin - b_hat * xg))))
        max_rank_one_dev = max(max_rank_one_dev,
                               float(np.max(np.abs(var_candidates - b_var))))
        slope_mean.append(float(b_hat))
        slope_var.append(max(b_var, 0.0))
        chain_of_draw.append(i // N_DRAWS)

        joint_mean.append(f_mean.numpy())
        joint_var.append(np.clip(np.diag(f_cov.numpy()), 0.0, None))

    n_ok = len(joint_mean)
    if n_ok == 0:
        raise RuntimeError("every draw failed the additive decomposition")

    return {
        "comp_mean": {k: np.stack(v) for k, v in comp_mean.items()},
        "comp_var": {k: np.stack(v) for k, v in comp_var.items()},
        "joint_mean": np.stack(joint_mean),
        "joint_var": np.stack(joint_var),
        "slope_mean": np.asarray(slope_mean),
        "slope_var": np.asarray(slope_var),
        "chain_of_draw": np.asarray(chain_of_draw),
        "n_attempted": n_total,
        "n_ok": n_ok,
        "n_failed": n_fail,
        "max_linearity_deviation": max_linearity_dev,
        "max_rank_one_variance_deviation": max_rank_one_dev,
    }


# ── Mixture summaries ────────────────────────────────────────────────────────


def total_variance_sd(mean_draws, var_draws):
    """Law-of-total-variance standard deviation across draws."""
    return np.sqrt(var_draws.mean(axis=0) + mean_draws.var(axis=0))


def mixture_central_interval(mean_draws, var_draws, mass=CREDIBLE_MASS):
    """Exact central interval of an equally weighted Gaussian mixture.

    ``mean_draws`` and ``var_draws`` have shape (n_draws, n_points); the return
    is (lo, hi), each of shape (n_points,). Quantiles come from bisecting the
    mixture CDF, so the interval is not a Gaussian approximation to the mixture.
    """
    sd = np.sqrt(np.clip(var_draws, 1e-24, None))
    tail = (1.0 - mass) / 2.0

    def quantile(p):
        lo = (mean_draws - 12.0 * sd).min(axis=0)
        hi = (mean_draws + 12.0 * sd).max(axis=0)
        for _ in range(BISECT_ITERS):
            mid = 0.5 * (lo + hi)
            cdf = ndtr((mid[None, :] - mean_draws) / sd).mean(axis=0)
            below = cdf < p
            lo = np.where(below, mid, lo)
            hi = np.where(below, hi, mid)
        return 0.5 * (lo + hi)

    return quantile(tail), quantile(1.0 - tail)


def rmse(values, target):
    return float(np.sqrt(np.mean((values - target) ** 2)))


# ── Figure ───────────────────────────────────────────────────────────────────


def make_figure(path, xg, x_np, y_np, truth, summary):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 3, figsize=(15.0, 4.6), sharex=True)

    ax = axes[0]
    ax.fill_between(xg, summary["joint_lo"], summary["joint_hi"],
                    color=COLOR_PRIMARY, alpha=0.20, linewidth=0,
                    label="95% central interval")
    ax.plot(xg, summary["joint_mean"], color=COLOR_PRIMARY, lw=2.0,
            label="composite posterior mean")
    ax.plot(xg, truth["combined"], color=COLOR_REFERENCE, lw=1.6, ls="--",
            label=r"generating $\sin x + 0.25x$")
    ax.scatter(x_np, y_np, marker="x", s=42, color=COLOR_DATA, lw=1.4,
               label="observed data (N=20)")
    ax.set_title("(a) Composite posterior predictive", fontsize=11)
    ax.set_ylabel("y", fontsize=10)

    ax = axes[1]
    ax.fill_between(xg, summary["truth_lo"], summary["truth_hi"],
                    color=COLOR_PRIMARY, alpha=0.20, linewidth=0)
    ax.plot(xg, summary["truth_mean"], color=COLOR_PRIMARY, lw=2.0,
            label="SE component (truth candidate)")
    ax.fill_between(xg, summary["bias_lo"], summary["bias_hi"],
                    color=COLOR_BIAS, alpha=0.22, linewidth=0)
    ax.plot(xg, summary["bias_mean"], color=COLOR_BIAS, lw=2.0,
            label="linear component (bias candidate)")
    ax.plot(xg, truth["true_signal"], color=COLOR_REFERENCE, lw=1.5, ls="--",
            label=r"generating $\sin x$")
    ax.plot(xg, truth["bias"], color=COLOR_REFERENCE, lw=1.5, ls=":",
            label=r"generating $0.25x$")
    ax.set_title("(b) Labeled components, 95% central intervals", fontsize=11)
    slope = summary["slope"]
    ax.annotate(
        "recovered slope {:.3f} (sd {:.3f})\n95% CI [{:.3f}, {:.3f}]"
        "\ngenerating value {:.3f}".format(
            slope["mean"], slope["sd"], slope["lo"], slope["hi"],
            summary["generating_slope"]),
        xy=(0.03, 0.97), xycoords="axes fraction", va="top", ha="left",
        fontsize=8.5,
        bbox=dict(boxstyle="round,pad=0.35", facecolor="white",
                  edgecolor=COLOR_BIAS, alpha=0.9))

    ax = axes[2]
    ax.fill_between(xg, summary["truth_lo"], summary["truth_hi"],
                    color=COLOR_PRIMARY, alpha=0.20, linewidth=0,
                    label="95% central interval")
    ax.plot(xg, summary["truth_mean"], color=COLOR_PRIMARY, lw=2.0,
            label="debiased posterior mean")
    ax.plot(xg, truth["true_signal"], color=COLOR_REFERENCE, lw=1.6, ls="--",
            label=r"known true process $\sin x$")
    ax.set_title("(c) Debiased predictive against the known truth", fontsize=11)
    ax.annotate(
        "RMSE vs sin x\ncomposite mean {:.3f}\ndebiased mean {:.3f}"
        "\ncoverage of sin x {:.3f}".format(
            summary["rmse_composite"], summary["rmse_debiased"],
            summary["coverage"]),
        xy=(0.03, 0.97), xycoords="axes fraction", va="top", ha="left",
        fontsize=8.5,
        bbox=dict(boxstyle="round,pad=0.35", facecolor="white",
                  edgecolor=COLOR_PRIMARY, alpha=0.9))

    for ax in axes:
        ax.set_xlabel("x", fontsize=10)
        ax.legend(fontsize=7.6, loc="lower right", framealpha=0.9)
        ax.grid(alpha=0.18, lw=0.6)

    fig.suptitle(
        "Debiasing by marginalization on the N=20 toy: one posterior, "
        "three readings", fontsize=12.5)
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


# ── Artifacts ────────────────────────────────────────────────────────────────


def write_readme(path, results):
    rec = results["recovery"]
    diag = results["sampler"]
    dec = results["decomposition"]
    lines = [
        "# Case E — toy debias demonstration",
        "",
        "Bias mitigation by marginalization on the synthetic toy whose bias",
        "process is known by construction. Generated by",
        "`experiments/toy_debias_demo.py`; consumed by manuscript section 7",
        "(`docs/paper-sie-jmp/07-debias-bridge.md`) and logged as",
        "`Notes/DECISIONS.md` D67.",
        "",
        "## Rerun",
        "",
        "```bash",
        "python experiments/toy_debias_demo.py",
        "```",
        "",
        "From the repository root. No network access and no new dependencies;",
        "local CPU, single process, about one minute.",
        "",
        "## Scope note — no Mauna Loa",
        "",
        "Synthetic toy only. This script imports, executes, and cites no Mauna",
        "Loa script or artifact, so the D58 preregistration boundary is not",
        "touched. The real-data development of the debiasing program, including",
        "the preregistered study, belongs to the companion line; thesis ch. 5 is",
        "the source of the program. Nothing here forecasts those numbers.",
        "",
        "Identifying the linear component as bias is a modeling CHOICE. It is",
        "licensed here because `generate_toy_data` built the data that way",
        "(`bias_slope=0.25`); in an application the analyst must justify the",
        "kernel labeling on substantive grounds.",
        "",
        "## Configuration",
        "",
        f"- Data: `generate_toy_data()` defaults, N={results['data']['n_points']}, "
        f"seed {results['data']['seed']}, noise sd {results['data']['noise_std']}, "
        f"bias slope {results['data']['bias_slope']}.",
        f"- Prior: `PRIOR_CONFIGS[\"{results['config']['prior_key']}\"]`, identical to "
        "the `toy_elicited` entry of `experiments/prior_sensitivity_study.py`.",
        f"- Sampler: `{diag['sampler']}` via `bistar_gp.fit.fit_hmc` (the corrected "
        "NUTS path; the pre-correction Pyro setup is not used).",
        f"- {diag['chains']} chains, seeds {diag['chain_seeds']}, "
        f"{diag['warmup_per_chain']} warmup and {diag['draws_per_chain']} retained "
        f"draws each ({diag['draws_total']} pooled).",
        f"- `target_accept_prob` {diag['target_accept_prob']}, `max_tree_depth` "
        f"{diag['max_tree_depth']}, initial step size {diag['initial_step_size']} "
        "with adaptation.",
        f"- Init: BOTH chains start at the SAME MAP point "
        f"(`fit_map`, torch seed {results['config']['map_seed']}, "
        f"{results['config']['map_iters']} iterations, lr {results['config']['map_lr']}). "
        "R-hat below is therefore WITHIN-MODE evidence: it reports mixing around "
        "the mode the optimizer selected, not agreement between dispersed starts. "
        "The toy hyperparameter posterior is known to be multi-basin (D12).",
        f"- Evaluation grid: {results['config']['grid']['n']} equally spaced points "
        f"on [{results['config']['grid']['lo']}, {results['config']['grid']['hi']}], "
        "inside the training span, so no extrapolation enters the numbers.",
        f"- Bands: latent-function, no observation noise; intervals are exact "
        f"{int(100 * results['config']['credible_mass'])}% central intervals of the "
        "draw mixture, obtained by CDF bisection.",
        "",
        "## Diagnostics",
        "",
        f"- Divergences: {diag['divergences_total']} "
        f"(by chain {diag['divergences_by_chain']}).",
        f"- Rank-normalized R-hat, maximum over sites: {diag['r_hat_max']:.4f}.",
        f"- Bulk ESS minimum {diag['ess_bulk_min']:.1f}; "
        f"tail ESS minimum {diag['ess_tail_min']:.1f}.",
        f"- Tree-depth saturation rate: {diag['depth_saturation_rate']:.4f}.",
        f"- Decomposition: {dec['n_ok']} of {dec['n_attempted']} draws succeeded, "
        f"{dec['n_failed']} failed.",
        "",
        "## Recovery",
        "",
        "| quantity | value | uncertainty layer |",
        "|---|---:|---|",
        f"| bias slope posterior mean | {rec['slope']['mean']:.3f} | "
        f"posterior sd {rec['slope']['sd']:.3f}; 95% CI "
        f"[{rec['slope']['lo']:.3f}, {rec['slope']['hi']:.3f}] |",
        f"| generating bias slope | {rec['generating_slope']:.3f} | known by "
        "construction |",
        f"| RMSE, composite mean vs sin x | {rec['rmse_composite']:.3f} | "
        f"per-chain {rec['rmse_composite_by_chain'][0]:.3f} and "
        f"{rec['rmse_composite_by_chain'][1]:.3f} |",
        f"| RMSE, debiased mean vs sin x | {rec['rmse_debiased']:.3f} | "
        f"per-chain {rec['rmse_debiased_by_chain'][0]:.3f} and "
        f"{rec['rmse_debiased_by_chain'][1]:.3f} |",
        f"| RMSE reduction | {rec['rmse_reduction']:.3f} | "
        f"{rec['rmse_reduction_pct']:.1f}% of the composite RMSE |",
        f"| coverage of sin x by the debiased band | {rec['coverage']:.3f} | "
        f"{rec['coverage_points_covered']} of {rec['coverage_points_total']} grid "
        f"points, nominal {rec['coverage_nominal']:.2f} |",
        f"| mean width, debiased band | {rec['debiased_band_mean_width']:.3f} | "
        f"composite band {rec['composite_band_mean_width']:.3f} on the same grid |",
        "",
        "Scale references on the same grid, both known by construction: the bias",
        f"process 0.25x has RMS {rec['bias_process_grid_rms']:.3f} and the true",
        f"process sin x has RMS {rec['true_process_grid_rms']:.3f}. The composite",
        "RMSE therefore reproduces the drift's own magnitude, as it must, since",
        "the composite describes the observed data and the observed data carry",
        "the drift.",
        "",
        f"Coverage caveat: {rec['coverage_caveat']}.",
        "",
        "## Reproducibility",
        "",
        f"- Determinism: every random source is seeded (data {results['data']['seed']}, "
        f"MAP {results['config']['map_seed']}, chains {diag['chain_seeds']}); the "
        "decomposition pass and the interval bisection draw no random numbers at",
        "  all, so nothing downstream of the sampler can drift.",
        "- Verified: on the environment stamped in `results.json` (`environment`),",
        "  two consecutive runs reproduced BOTH `results.json` and",
        "  `debias_figure.png` byte for byte. Byte-stability is asserted only",
        "  within one environment.",
        "- Across environments compare numerically instead, at these tolerances:",
        "  recovery values to 1e-6 absolute, R-hat to 1e-3, ESS to 1 effective",
        "  draw. A torch or pyro version change moves the draws and voids the",
        "  byte comparison without voiding the substantive numbers.",
        "",
        "## Files",
        "",
        "- `results.json` — configuration, seeds, sampler settings and init,",
        "  diagnostics, decomposition counts, recovery numbers, grid definition.",
        "- `debias_figure.png` — the three-panel figure carried by section 7.",
        "- `README.md` — this file.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


# ── Driver ───────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default=str(REPO_ROOT / "runs" / "toy_debias_demo"),
                        help="output directory (default runs/toy_debias_demo)")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    verbose = not args.quiet

    warnings.filterwarnings("ignore", module="linear_operator")
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    prior_config = PRIOR_CONFIGS[PRIOR_KEY]
    x, y, info = generate_toy_data()
    x_grid = torch.linspace(GRID_LO, GRID_HI, GRID_N).double()
    xg = x_grid.numpy()
    truth = {
        "true_signal": np.sin(xg),
        "bias": float(info["bias_slope"]) * xg,
        "combined": np.sin(xg) + float(info["bias_slope"]) * xg,
    }

    if verbose:
        print(f"Case E toy debias demo — N={len(x)}, prior {PRIOR_KEY}")
        print("Sampling hyperparameters on the corrected NUTS path (nuts_e1)...")
    chain_samples, chain_diagnostics, map_point = run_chains(
        prior_config, x, y, verbose=verbose)
    diag = sampler_diagnostics_block(chain_samples, chain_diagnostics)

    pooled = {site: np.concatenate([chain[site] for chain in chain_samples])
              for site in chain_samples[0]}

    if verbose:
        print(f"Decomposing {diag['draws_total']} draws with the package "
              "additive-kernel machinery...")
    dec = decompose_draws(prior_config, x, y, x_grid, pooled)

    truth_mean_draws = dec["comp_mean"][TRUTH_COMPONENT]
    truth_var_draws = dec["comp_var"][TRUTH_COMPONENT]
    bias_mean_draws = dec["comp_mean"][BIAS_COMPONENT]
    bias_var_draws = dec["comp_var"][BIAS_COMPONENT]

    truth_mean = truth_mean_draws.mean(axis=0)
    bias_mean = bias_mean_draws.mean(axis=0)
    joint_mean = dec["joint_mean"].mean(axis=0)

    truth_lo, truth_hi = mixture_central_interval(truth_mean_draws, truth_var_draws)
    bias_lo, bias_hi = mixture_central_interval(bias_mean_draws, bias_var_draws)
    joint_lo, joint_hi = mixture_central_interval(dec["joint_mean"], dec["joint_var"])

    slope_lo, slope_hi = mixture_central_interval(
        dec["slope_mean"][:, None], dec["slope_var"][:, None])
    slope = {
        "mean": float(dec["slope_mean"].mean()),
        "sd": float(total_variance_sd(dec["slope_mean"][:, None],
                                      dec["slope_var"][:, None])[0]),
        "lo": float(slope_lo[0]),
        "hi": float(slope_hi[0]),
    }

    sin_grid = truth["true_signal"]
    rmse_debiased = rmse(truth_mean, sin_grid)
    rmse_composite = rmse(joint_mean, sin_grid)
    chain_ids = dec["chain_of_draw"]
    rmse_debiased_by_chain, rmse_composite_by_chain = [], []
    for c in range(diag["chains"]):
        mask = chain_ids == c
        rmse_debiased_by_chain.append(
            rmse(truth_mean_draws[mask].mean(axis=0), sin_grid))
        rmse_composite_by_chain.append(
            rmse(dec["joint_mean"][mask].mean(axis=0), sin_grid))

    covered = (sin_grid >= truth_lo) & (sin_grid <= truth_hi)
    coverage = float(covered.mean())

    recovery = {
        "generating_slope": float(info["bias_slope"]),
        "slope": slope,
        "slope_minus_generating": float(slope["mean"] - float(info["bias_slope"])),
        "slope_interval_contains_generating": bool(
            slope["lo"] <= float(info["bias_slope"]) <= slope["hi"]),
        "rmse_composite": rmse_composite,
        "rmse_debiased": rmse_debiased,
        "rmse_reduction": float(rmse_composite - rmse_debiased),
        "rmse_reduction_pct": float(
            100.0 * (rmse_composite - rmse_debiased) / rmse_composite),
        "rmse_composite_by_chain": rmse_composite_by_chain,
        "rmse_debiased_by_chain": rmse_debiased_by_chain,
        "debias_improves_rmse": bool(rmse_debiased < rmse_composite),
        "coverage": coverage,
        "coverage_nominal": CREDIBLE_MASS,
        "coverage_points_covered": int(covered.sum()),
        "coverage_points_total": int(covered.size),
        "coverage_caveat": (
            "a pointwise summary over a correlated grid, not a calibration test "
            "with independent trials: neighboring grid points share nearly the "
            "same posterior, so the effective number of checks is far below "
            f"{int(covered.size)}"),
        "debiased_band_mean_width": float(np.mean(truth_hi - truth_lo)),
        "composite_band_mean_width": float(np.mean(joint_hi - joint_lo)),
        "bias_process_grid_rms": rmse(truth["bias"], 0.0),
        "true_process_grid_rms": rmse(sin_grid, 0.0),
    }

    summary = {
        "joint_mean": joint_mean, "joint_lo": joint_lo, "joint_hi": joint_hi,
        "truth_mean": truth_mean, "truth_lo": truth_lo, "truth_hi": truth_hi,
        "bias_mean": bias_mean, "bias_lo": bias_lo, "bias_hi": bias_hi,
        "slope": slope, "generating_slope": float(info["bias_slope"]),
        "rmse_composite": rmse_composite, "rmse_debiased": rmse_debiased,
        "coverage": coverage,
    }
    figure_path = out_dir / "debias_figure.png"
    make_figure(figure_path, xg, x.numpy(), y.numpy(), truth, summary)

    results = {
        "case": "E",
        "title": "Toy debias demonstration: evaluation and mitigation from one posterior",
        "scope": {
            "synthetic_only": True,
            "mauna_loa_contact": "none",
            "kernel_labeling": (
                "the linear component is labeled bias and the SE component truth; "
                "licensed here because generate_toy_data constructed the data that "
                "way, and a modeling choice the analyst must justify elsewhere"),
        },
        "data": {
            "generator": "bistar_gp.generate_toy_data() at defaults",
            "n_points": int(len(x)),
            "seed": 42,
            "x_range": [-10.0, 10.0],
            "noise_std": float(info["noise_std"]),
            "bias_slope": float(info["bias_slope"]),
            "true_process": "sin(x)",
            "bias_process": "0.25 * x",
        },
        "config": {
            "prior_key": PRIOR_KEY,
            "prior_equivalent_to": (
                "experiments/prior_sensitivity_study.py STUDY_CONFIGS['toy_elicited']"),
            "prior_parameters": {
                "se_lengthscale_prior": list(prior_config.se_lengthscale_prior),
                "se_outputscale_prior": list(prior_config.se_outputscale_prior),
                "linear_variance_prior": list(prior_config.linear_variance_prior),
                "noise_prior": list(prior_config.noise_prior),
            },
            "components": {"truth_candidate": TRUTH_COMPONENT,
                           "bias_candidate": BIAS_COMPONENT},
            "map_seed": MAP_SEED,
            "map_iters": MAP_ITERS,
            "map_lr": MAP_LR,
            "init_strategy": (
                "init_to_map: both chains start at the same MAP point, so R-hat is "
                "within-mode evidence about mixing around the optimizer's mode, not "
                "between-mode agreement from dispersed starts (the toy "
                "hyperparameter posterior is multi-basin, D12)"),
            "map_point": map_point,
            "grid": {"lo": GRID_LO, "hi": GRID_HI, "n": GRID_N,
                     "spacing": "equally spaced, inside the training span"},
            "credible_mass": CREDIBLE_MASS,
            "interval_method": (
                "exact central interval of the equally weighted Gaussian mixture "
                "over retained draws, by CDF bisection"),
            "band_convention": "latent function, no observation noise added",
            "decomposition_jitter": DECOMP_JITTER,
        },
        "sampler": diag,
        "decomposition": {
            "machinery": (
                "bistar_gp.decompose.decompose_additive_gp for components; "
                "bistar_gp.decompose.decompose_component on the summed kernel "
                "blocks for the joint posterior"),
            "n_attempted": dec["n_attempted"],
            "n_ok": dec["n_ok"],
            "n_failed": dec["n_failed"],
            "linear_component_structure_check": {
                "max_abs_deviation_from_exact_linearity":
                    dec["max_linearity_deviation"],
                "max_abs_deviation_from_rank_one_variance":
                    dec["max_rank_one_variance_deviation"],
                "note": (
                    "gpytorch LinearKernel gives k(x,x') = v x x', so the component "
                    "posterior mean must be exactly linear and its covariance "
                    "exactly Var(b|theta) x x^T; these are the worst observed "
                    "deviations across retained draws, and they license reading the "
                    "slope moments off the decomposition output"),
            },
        },
        "recovery": recovery,
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "torch": torch.__version__,
            "arviz": diag["arviz_version"],
        },
    }

    results_path = out_dir / "results.json"
    payload = json.dumps(results, indent=2, sort_keys=True) + "\n"
    results_path.write_text(payload, encoding="utf-8")
    write_readme(out_dir / "README.md", results)

    if verbose:
        print(f"\nR-hat max {diag['r_hat_max']:.4f}, bulk ESS min "
              f"{diag['ess_bulk_min']:.1f}, divergences {diag['divergences_total']}")
        print(f"Decomposed {dec['n_ok']}/{dec['n_attempted']} draws "
              f"({dec['n_failed']} failed)")
        print(f"Bias slope {slope['mean']:.3f} (sd {slope['sd']:.3f}, 95% CI "
              f"[{slope['lo']:.3f}, {slope['hi']:.3f}]) vs generating "
              f"{info['bias_slope']:.3f}")
        print(f"RMSE vs sin x: composite {rmse_composite:.3f}, debiased "
              f"{rmse_debiased:.3f} ({recovery['rmse_reduction_pct']:.1f}% lower)")
        print(f"Coverage of sin x by the debiased 95% band: {coverage:.3f}")
        print(f"results.json sha256 "
              f"{hashlib.sha256(payload.encode('utf-8')).hexdigest()}")
        print(f"Figure {figure_path} "
              f"({figure_path.stat().st_size / 1024:.0f} KiB)")


if __name__ == "__main__":
    main()
