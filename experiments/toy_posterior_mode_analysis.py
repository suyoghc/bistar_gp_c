"""
Why VI and HMC disagree on the thesis toy (D12 evidence chain).

The comparison run (experiments/fit_method_metric_comparison.py) found the two
thesis implementations in DIFFERENT hyperparameter regimes: HMC/hmc_laplace at
noise ~0.05 with short scales, VI at noise ~0.55 with prior-scale kernels.
This script assembles the evidence that the posterior is bimodal and each
method captures one mode:

  1. VI stability: three seeds and a 4x-longer run land at the same point —
     the VI solution is a converged ELBO optimum, not optimizer drift.
  2. Log-joint decomposition at each solution: the HMC mode has the best data
     fit (log ML) but is prior-penalized; the VI mode is prior-favored with
     the worst data fit; MAP has the highest joint density.
  3. Random-walk MH referee (no NUTS step-size pathology, D4-fixed target):
     visits BOTH basins; the small-noise likelihood mode holds the majority
     of mass across seeds.
  4. If the comparison run's cached draws exist, per-method basin occupancy
     P(noise < 0.15): hmc/hmc_laplace ~1.0, vi ~0.0 — each sampler is
     mode-blind in opposite directions.

Usage: python experiments/toy_posterior_mode_analysis.py [--skip-mh]
"""

import sys, os, argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import torch
import torch.nn.functional as F
import gpytorch

from bistar_gp import generate_toy_data, build_model
from bistar_gp.config import (PRIOR_CONFIGS, build_kernels_from_config,
                              build_likelihood_from_config)
from bistar_gp.fit import fit_map, fit_vi, fit_mcmc_simple, _mh_log_joint
from bistar_gp.model import apply_hp_value

torch.set_default_dtype(torch.float64)

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SAMPLES_DIR = os.path.join(REPO_ROOT, "runs", "fit_method_metric_comparison")
PC = PRIOR_CONFIGS["informative"]
NOISE_SPLIT = 0.15   # basin boundary: well between the ~0.05 and ~0.55 modes

SHORT = {"covar_module.kernels.0.base_kernel.lengthscale_prior": "ls",
         "covar_module.kernels.0.outputscale_prior": "os",
         "covar_module.kernels.1.variance_prior": "lv",
         "likelihood.noise_covar.noise_prior": "noise"}
LONG = {v: k for k, v in SHORT.items()}


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


def decompose(x, y, vals):
    """(summed log marginal likelihood, log prior) at constrained values."""
    m, l = fresh(x, y)
    for k, v in vals.items():
        apply_hp_value(m, l, LONG[k], v)
    mll = gpytorch.mlls.ExactMarginalLogLikelihood(l, m)
    total = _mh_log_joint(mll, m, l, x, y)
    with torch.no_grad(), gpytorch.settings.cholesky_jitter(1e-4):
        pred = l(m(x))
        log_ml = gpytorch.distributions.MultivariateNormal(
            pred.mean, pred.covariance_matrix).log_prob(y).item()
    return log_ml, total - log_ml


def log_joint_table(x, y, solutions):
    print("\n── 2. log joint = log ML + log prior at each solution ──")
    print(f"  {'solution':<10} {'log ML':>10} {'log prior':>10} {'log joint':>10}")
    for name, v in solutions.items():
        ml, pr = decompose(x, y, v)
        print(f"  {name:<10} {ml:>10.2f} {pr:>10.2f} {ml + pr:>10.2f}")


def mh_referee(x, y, seeds=(42, 1, 2, 3)):
    print("\n── 3. random-walk MH referee (30k draws, MAP init) ──")
    for seed in seeds:
        m, l = map_fitted(x, y)
        raw = fit_mcmc_simple(m, l, x, y, n_samples=30000, n_burnin=5000,
                              proposal_scale=0.1, verbose=False, seed=seed)
        noise = F.softplus(
            torch.tensor(raw["likelihood.noise_covar.raw_noise"])).numpy()
        print(f"  seed={seed}: P(noise<{NOISE_SPLIT})={np.mean(noise < NOISE_SPLIT):.3f}  "
              f"P(noise>0.30)={np.mean(noise > 0.30):.3f}  mean={noise.mean():.3f}")


def cached_basin_occupancy():
    print(f"\n── 4. basin occupancy of the comparison run's cached draws ──")
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
    args = parser.parse_args()

    x, y, _ = generate_toy_data()   # thesis toy: sin(x)+0.25x, N=20

    vi_stability(x, y)

    # Solution points: HMC/VI means from the comparison run's hyperparameter
    # table (runs/fit_method_metric_comparison/results.json), MAP from
    # fit_map(300), truth-ish = data-generating values (os = var(sin) = 0.5,
    # lv = slope^2 = 0.0625, noise = 0.5^2).
    solutions = {
        "MAP point": {"ls": 2.1794, "os": 3.7594, "lv": 5.3006, "noise": 0.0736},
        "HMC mean":  {"ls": 1.4556, "os": 0.8493, "lv": 0.1722, "noise": 0.0527},
        "VI mean":   {"ls": 7.3478, "os": 6.6918, "lv": 7.4383, "noise": 0.5707},
        "truth-ish": {"ls": 1.5,    "os": 0.5,    "lv": 0.0625, "noise": 0.25},
    }
    log_joint_table(x, y, solutions)

    if not args.skip_mh:
        mh_referee(x, y)

    cached_basin_occupancy()


if __name__ == "__main__":
    main()
