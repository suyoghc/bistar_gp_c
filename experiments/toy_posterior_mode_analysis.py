"""
Why VI and HMC disagree on the thesis toy (D12 evidence chain, corrected D13).

The comparison run (experiments/fit_method_metric_comparison.py) found the two
thesis implementations in DIFFERENT hyperparameter regimes: HMC/hmc_laplace at
noise ~0.05 with short scales, VI at noise ~0.55 with prior-scale kernels.
This script assembles the evidence for the corrected story (D12 + the D13
correction, adjudicated against an independent codex verification):

  1. VI stability: three seeds and a 4x-longer run land at the same point —
     the VI solution is a converged ELBO optimum, not optimizer drift.
  2. The exact log joint is BIMODAL: the low-noise MAP (noise~0.074, global
     density mode, log joint -33.4) and a genuine second local max found by
     optimization from the VI region (noise~0.59, ls~8.4, log joint -36.8),
     with a valley (~ -43) on the log-space segment between them. The
     decomposition shows the tug-of-war: the low mode has the better data fit,
     the high mode the better prior score.
  3. Prior importance sampling (unbiased, mixing-free — the mass AUTHORITY
     here): the high-noise basin holds ~3x the posterior mass. So VI migrates
     to the DOMINANT basin; HMC/MAP stay in the minority basin that contains
     the global density mode (and selects the true model). The uncorrected
     RW-MH referee had this BACKWARDS before D13: proposing in raw space
     without the softplus Jacobian inflates small-noise mass (P(noise<0.15)
     0.65-0.81 uncorrected vs ~0.19 true).
  4. RW-MH referee (Jacobian-corrected by D13): demonstrates basin CROSSING
     (both basins visited within one chain) but per-chain splits scatter
     widely across seeds — kept as mixing evidence, not a mass estimate.
  5. If the comparison run's cached draws exist, per-method basin occupancy
     P(noise < 0.15): hmc/hmc_laplace 1.0, vi 0.0 — each sampler is
     mode-blind in opposite directions.

Usage: python experiments/toy_posterior_mode_analysis.py [--skip-mh] [--is-n N]
"""

import sys, os, argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import torch
import torch.nn.functional as F
import gpytorch
from scipy.optimize import minimize

from bistar_gp import generate_toy_data, build_model
from bistar_gp.config import (PRIOR_CONFIGS, build_kernels_from_config,
                              build_likelihood_from_config)
from bistar_gp.fit import fit_map, fit_vi, fit_mcmc_simple, _mh_log_joint
from bistar_gp.model import apply_hp_value

torch.set_default_dtype(torch.float64)

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SAMPLES_DIR = os.path.join(REPO_ROOT, "runs", "fit_method_metric_comparison")
PC = PRIOR_CONFIGS["informative"]
NOISE_SPLIT = 0.15   # basin boundary: well between the ~0.07 and ~0.59 modes

SHORT = {"covar_module.kernels.0.base_kernel.lengthscale_prior": "ls",
         "covar_module.kernels.0.outputscale_prior": "os",
         "covar_module.kernels.1.variance_prior": "lv",
         "likelihood.noise_covar.noise_prior": "noise"}
LONG = {v: k for k, v in SHORT.items()}
ORDER = ["ls", "os", "lv", "noise"]


def fresh(x, y):
    k, n = build_kernels_from_config(PC)
    lik = build_likelihood_from_config(PC)
    return build_model(x, y, k, n, lik)


def map_fitted(x, y):
    m, l = fresh(x, y)
    torch.manual_seed(42)
    fit_map(m, l, x, y, n_iter=300, lr=0.05, verbose=False)
    return m, l


def vi_stability(x, y):
    print("── 1. VI stability (seed and step count) ──")
    for seed, n_steps in [(0, 5000), (1, 5000), (2, 5000), (0, 20000)]:
        m, l = map_fitted(x, y)
        s = fit_vi(m, l, x, y, n_samples=500, n_steps=n_steps, verbose=False,
                   seed=seed)
        r = {SHORT[k]: round(float(v.mean()), 3) for k, v in s.items()}
        print(f"  seed={seed} steps={n_steps}: {r}")


def log_joint(x, y, vals):
    m, l = fresh(x, y)
    for k, v in vals.items():
        apply_hp_value(m, l, LONG[k], float(v))
    mll = gpytorch.mlls.ExactMarginalLogLikelihood(l, m)
    try:
        return _mh_log_joint(mll, m, l, x, y)
    except Exception:
        return -np.inf


def decompose(x, y, vals):
    """(summed log marginal likelihood, log prior) at constrained values.
    gpytorch adds priors as constrained-space densities (no Jacobian), so the
    subtraction recovers exactly sum(GammaPrior.log_prob) — verified to 1e-12
    in the codex adjudication pass."""
    total = log_joint(x, y, vals)
    m, l = fresh(x, y)
    for k, v in vals.items():
        apply_hp_value(m, l, LONG[k], float(v))
    with torch.no_grad(), gpytorch.settings.cholesky_jitter(1e-4):
        pred = l(m(x))
        log_ml = gpytorch.distributions.MultivariateNormal(
            pred.mean, pred.covariance_matrix).log_prob(y).item()
    return log_ml, total - log_ml


def find_modes(x, y):
    print("\n── 2. modes of the exact log joint (bimodality proof) ──")
    # Low-noise MAP: the shared MAP prefit's landing point.
    m, l = map_fitted(x, y)
    low = {"ls": float(m.covar_module.kernels[0].base_kernel.lengthscale.detach()),
           "os": float(m.covar_module.kernels[0].outputscale.detach()),
           "lv": float(m.covar_module.kernels[1].variance.detach()),
           "noise": float(l.noise.detach())}
    # High mode: exact-log-joint optimization (Nelder-Mead in log space)
    # started in the VI region.
    f = lambda logv: -log_joint(x, y, dict(zip(ORDER, np.exp(logv))))
    r = minimize(f, np.log([7.3, 6.7, 7.4, 0.57]), method="Nelder-Mead",
                 options={"xatol": 1e-8, "fatol": 1e-10, "maxiter": 4000})
    high = dict(zip(ORDER, np.exp(r.x)))

    solutions = {"low MAP": low, "high mode": high,
                 "truth-ish": {"ls": 1.5, "os": 0.5, "lv": 0.0625,
                               "noise": 0.25}}
    print(f"  {'point':<10} {'noise':>8} {'ls':>8} "
          f"{'log ML':>9} {'log prior':>10} {'log joint':>10}")
    for name, v in solutions.items():
        ml, pr = decompose(x, y, v)
        print(f"  {name:<10} {v['noise']:>8.4f} {v['ls']:>8.3f} "
              f"{ml:>9.2f} {pr:>10.2f} {ml + pr:>10.2f}")
    lo, hi = (np.log([low[k] for k in ORDER]), r.x)
    seg = min(log_joint(x, y, dict(zip(ORDER, np.exp(lo + t * (hi - lo)))))
              for t in np.linspace(0, 1, 21))
    print(f"  valley on the log-space segment between the modes: {seg:.2f}")
    return low, high


def prior_is_mass(x, y, n_draws, seed=0):
    """P(basin) by prior importance sampling: the Gamma priors are exactly
    samplable, so P(A) = E_prior[ML * 1_A] / E_prior[ML] — unbiased and
    independent of any chain's mixing. The mass AUTHORITY in this analysis."""
    print(f"\n── 3. posterior mass by prior importance sampling (N={n_draws}) ──")
    rng = np.random.default_rng(seed)
    ths = np.column_stack([rng.gamma(6.0, 1 / 0.85, n_draws),
                           rng.gamma(6.0, 1 / 0.85, n_draws),
                           rng.gamma(6.0, 1 / 0.85, n_draws),
                           rng.gamma(1.75, 1.0, n_draws)])
    m, l = fresh(x, y)
    lml = np.empty(n_draws)
    for i, th in enumerate(ths):
        for k, v in zip(ORDER, th):
            apply_hp_value(m, l, LONG[k], float(v))
        with torch.no_grad(), gpytorch.settings.cholesky_jitter(1e-4):
            try:
                pred = l(m(x))
                lml[i] = gpytorch.distributions.MultivariateNormal(
                    pred.mean, pred.covariance_matrix).log_prob(y).item()
            except Exception:
                lml[i] = -np.inf
        m.train(); l.train()
    w = np.exp(lml - lml.max())
    noise, tot = ths[:, 3], w.sum()
    print(f"  P(noise<{NOISE_SPLIT}) = {w[noise < NOISE_SPLIT].sum() / tot:.3f}")
    print(f"  P(noise>0.30) = {w[noise > 0.30].sum() / tot:.3f}")
    print(f"  IS effective sample size: {tot ** 2 / (w ** 2).sum():.0f}")


def mh_referee(x, y, seeds=(42, 1, 2)):
    print("\n── 4. RW-MH referee (Jacobian-corrected, D13) ──")
    print("  Basin-crossing evidence only: single-chain splits scatter widely")
    print("  because valley crossings are rare; the mass authority is §3.")
    for seed in seeds:
        m, l = map_fitted(x, y)
        raw = fit_mcmc_simple(m, l, x, y, n_samples=30000, n_burnin=5000,
                              proposal_scale=0.1, verbose=False, seed=seed)
        noise = F.softplus(
            torch.tensor(raw["likelihood.noise_covar.raw_noise"])).numpy()
        lo, hi = noise < NOISE_SPLIT, noise > 0.30
        lab = lo[lo | hi]   # drop mid-valley draws; True=low basin, False=high
        crossings = int(np.sum(lab[1:] != lab[:-1]))
        print(f"  seed={seed}: P(noise<{NOISE_SPLIT})={lo.mean():.3f}  "
              f"P(noise>0.30)={hi.mean():.3f}  low/high crossings={crossings}")


def cached_basin_occupancy():
    print(f"\n── 5. basin occupancy of the comparison run's cached draws ──")
    any_found = False
    for method in ("hmc", "hmc_laplace", "vi", "map"):
        path = os.path.join(SAMPLES_DIR, f"samples_{method}.npz")
        if not os.path.exists(path):
            continue
        any_found = True
        with np.load(path) as z:
            noise = z["likelihood.noise_covar.noise_prior"]
        print(f"  {method:<12} P(noise<{NOISE_SPLIT}) = "
              f"{np.mean(noise < NOISE_SPLIT):.3f}   (n={len(noise)})")
    if not any_found:
        print(f"  (no cached draws under {SAMPLES_DIR}; run the comparison first)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-mh", action="store_true",
                        help="skip the slow MH referee section")
    parser.add_argument("--is-n", type=int, default=60000,
                        help="prior importance-sampling draws")
    args = parser.parse_args()

    x, y, _ = generate_toy_data()   # thesis toy: sin(x)+0.25x, N=20

    vi_stability(x, y)
    find_modes(x, y)
    prior_is_mass(x, y, args.is_n)
    if not args.skip_mh:
        mh_referee(x, y)
    cached_basin_occupancy()


if __name__ == "__main__":
    main()
