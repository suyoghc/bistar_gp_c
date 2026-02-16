"""
Hierarchical GP for practice law experiments.

Two-stage empirical Bayes:
  Stage 1: MAP fit each subject → collect per-subject hyperparameters
  Stage 2: Fit LogNormal population distributions to hyperparameters
  Stage 3: HMC per subject with population priors → stabilized draws

The population prior replaces the hand-tuned agnostic/practitioner configs.
Each subject borrows strength from all others.
"""

import numpy as np
import torch
import gpytorch
from gpytorch.kernels import ScaleKernel, RBFKernel, MaternKernel
from gpytorch.constraints import Positive
from gpytorch.priors import LogNormalPrior, GammaPrior
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)
torch.set_default_dtype(torch.float64)


# ═══════════════════════════════════════════════════════════════════
# Data structures
# ═══════════════════════════════════════════════════════════════════

@dataclass
class SubjectHyperparams:
    """MAP hyperparameters for one subject."""
    subject_id: int
    lengthscale: float
    outputscale: float
    noise: float
    mll: float  # marginal log-likelihood at MAP


@dataclass
class PopulationPrior:
    """Population-level LogNormal prior parameters.

    If hyperparameters h_i ~ LogNormal(mu, sigma), then:
      log(h_i) ~ Normal(mu, sigma)

    We estimate mu, sigma from the MAP hyperparameters across subjects.
    """
    # LogNormal parameters (on log scale)
    ls_mu: float
    ls_sigma: float
    os_mu: float
    os_sigma: float
    noise_mu: float
    noise_sigma: float
    # Raw values used to fit
    n_subjects: int
    lengthscales: np.ndarray = field(repr=False)
    outputscales: np.ndarray = field(repr=False)
    noises: np.ndarray = field(repr=False)

    def summary(self):
        """Print population prior summary."""
        print(f"\n{'='*50}")
        print(f"Population Prior (n={self.n_subjects} subjects)")
        print(f"{'='*50}")
        for name, mu, sigma, vals in [
            ("lengthscale", self.ls_mu, self.ls_sigma, self.lengthscales),
            ("outputscale", self.os_mu, self.os_sigma, self.outputscales),
            ("noise", self.noise_mu, self.noise_sigma, self.noises),
        ]:
            median = np.exp(mu)
            mean = np.exp(mu + sigma**2 / 2)
            print(f"  {name}:")
            print(f"    LogNormal(mu={mu:.3f}, sigma={sigma:.3f})")
            print(f"    median={median:.4f}, mean={mean:.4f}")
            print(f"    raw range: [{vals.min():.4f}, {vals.max():.4f}]")
        print()


# ═══════════════════════════════════════════════════════════════════
# Stage 1: MAP fit all subjects
# ═══════════════════════════════════════════════════════════════════

def _build_map_kernel(kernel_type="rbf"):
    """Build a single-component GP kernel for MAP fitting.

    Uses weak priors — just enough to keep optimization stable.
    Population prior will replace these in Stage 3.
    """
    if kernel_type == "rbf":
        base = RBFKernel(
            lengthscale_constraint=Positive(),
            lengthscale_prior=GammaPrior(2.0, 2.0),  # weak
        )
    elif kernel_type == "matern32":
        base = MaternKernel(
            nu=1.5,
            lengthscale_constraint=Positive(),
            lengthscale_prior=GammaPrior(2.0, 2.0),
        )
    elif kernel_type == "matern52":
        base = MaternKernel(
            nu=2.5,
            lengthscale_constraint=Positive(),
            lengthscale_prior=GammaPrior(2.0, 2.0),
        )
    else:
        raise ValueError(f"Unknown kernel type: {kernel_type}")

    kernel = ScaleKernel(
        base,
        outputscale_constraint=Positive(),
        outputscale_prior=GammaPrior(2.0, 2.0),
    )
    return kernel


def map_fit_subject(x_norm, y_norm, subject_id=0, kernel_type="rbf",
                    n_iter=300, lr=0.05, verbose=False):
    """MAP fit a single subject. Returns SubjectHyperparams."""
    from bistar_gp.model import AdditiveGPModel
    from bistar_gp.fit import fit_map

    x = torch.tensor(x_norm).double()
    y = torch.tensor(y_norm).double()

    kernel = _build_map_kernel(kernel_type)
    lik = gpytorch.likelihoods.GaussianLikelihood(
        noise_constraint=Positive(),
        noise_prior=GammaPrior(2.0, 2.0),
    )

    model = AdditiveGPModel(x, y, lik, [kernel], ["signal"])
    model = model.double()
    lik = lik.double()

    losses = fit_map(model, lik, x, y, n_iter=n_iter, lr=lr, verbose=verbose)

    ls = kernel.base_kernel.lengthscale.item()
    os = kernel.outputscale.item()
    noise = lik.noise.item()
    final_mll = -losses[-1] if losses else float('nan')

    return SubjectHyperparams(
        subject_id=subject_id,
        lengthscale=ls,
        outputscale=os,
        noise=noise,
        mll=final_mll,
    )


def map_fit_all(subjects_data, kernel_type="rbf", verbose=False):
    """
    Stage 1: MAP fit all subjects.

    Args:
        subjects_data: list of (x_norm, y_norm) tuples
        kernel_type: "rbf", "matern32", or "matern52"

    Returns:
        list of SubjectHyperparams
    """
    results = []
    for i, (x, y) in enumerate(subjects_data):
        if verbose or (i % 10 == 0):
            print(f"  MAP fitting subject {i}/{len(subjects_data)}...")
        hp = map_fit_subject(x, y, subject_id=i, kernel_type=kernel_type,
                             verbose=False)
        results.append(hp)
        if verbose:
            print(f"    ls={hp.lengthscale:.4f} os={hp.outputscale:.4f} "
                  f"noise={hp.noise:.4f}")
    return results


# ═══════════════════════════════════════════════════════════════════
# Stage 2: Fit population distributions
# ═══════════════════════════════════════════════════════════════════

def fit_population_prior(subject_hps: List[SubjectHyperparams],
                         min_sigma=0.1) -> PopulationPrior:
    """
    Fit LogNormal population distributions to MAP hyperparameters.

    LogNormal(mu, sigma) means log(h) ~ Normal(mu, sigma).
    We estimate mu = mean(log(h)), sigma = std(log(h)).

    Args:
        subject_hps: list of SubjectHyperparams from Stage 1
        min_sigma: minimum sigma to prevent over-shrinkage

    Returns:
        PopulationPrior
    """
    ls_vals = np.array([hp.lengthscale for hp in subject_hps])
    os_vals = np.array([hp.outputscale for hp in subject_hps])
    noise_vals = np.array([hp.noise for hp in subject_hps])

    # Clip away from zero for log safety
    ls_vals = np.clip(ls_vals, 1e-6, None)
    os_vals = np.clip(os_vals, 1e-6, None)
    noise_vals = np.clip(noise_vals, 1e-6, None)

    def _fit_lognormal(vals):
        log_vals = np.log(vals)
        mu = np.mean(log_vals)
        sigma = max(np.std(log_vals), min_sigma)
        return mu, sigma

    ls_mu, ls_sigma = _fit_lognormal(ls_vals)
    os_mu, os_sigma = _fit_lognormal(os_vals)
    noise_mu, noise_sigma = _fit_lognormal(noise_vals)

    return PopulationPrior(
        ls_mu=ls_mu, ls_sigma=ls_sigma,
        os_mu=os_mu, os_sigma=os_sigma,
        noise_mu=noise_mu, noise_sigma=noise_sigma,
        n_subjects=len(subject_hps),
        lengthscales=ls_vals,
        outputscales=os_vals,
        noises=noise_vals,
    )


# ═══════════════════════════════════════════════════════════════════
# Stage 3: Build kernels with population priors + HMC
# ═══════════════════════════════════════════════════════════════════

def build_hierarchical_kernel(pop_prior: PopulationPrior,
                              kernel_type="rbf"):
    """
    Build kernel + likelihood using population-derived priors.

    Returns: (kernel_builder, likelihood_builder) callables
        for use with extract_gp_predictives.
    """

    def kernel_builder():
        if kernel_type == "rbf":
            base = RBFKernel(
                lengthscale_constraint=Positive(),
                lengthscale_prior=LogNormalPrior(
                    pop_prior.ls_mu, pop_prior.ls_sigma
                ),
            )
        elif kernel_type == "matern32":
            base = MaternKernel(
                nu=1.5,
                lengthscale_constraint=Positive(),
                lengthscale_prior=LogNormalPrior(
                    pop_prior.ls_mu, pop_prior.ls_sigma
                ),
            )
        elif kernel_type == "matern52":
            base = MaternKernel(
                nu=2.5,
                lengthscale_constraint=Positive(),
                lengthscale_prior=LogNormalPrior(
                    pop_prior.ls_mu, pop_prior.ls_sigma
                ),
            )
        else:
            raise ValueError(f"Unknown kernel type: {kernel_type}")

        kernel = ScaleKernel(
            base,
            outputscale_constraint=Positive(),
            outputscale_prior=LogNormalPrior(
                pop_prior.os_mu, pop_prior.os_sigma
            ),
        )
        return [kernel], ["signal"]

    def likelihood_builder():
        return gpytorch.likelihoods.GaussianLikelihood(
            noise_constraint=Positive(),
            noise_prior=LogNormalPrior(
                pop_prior.noise_mu, pop_prior.noise_sigma
            ),
        )

    return kernel_builder, likelihood_builder


def hmc_fit_subject(x_norm, y_norm, pop_prior: PopulationPrior,
                    kernel_type="rbf", n_samples=200, n_warmup=100,
                    verbose=False):
    """
    Stage 3: HMC fit a single subject using population priors.

    Returns:
        mcmc_samples: dict of parameter name -> numpy array
        model: the fitted model (for extract_gp_predictives)
        likelihood: the fitted likelihood
    """
    from bistar_gp.model import build_model
    from bistar_gp.fit import fit_map, fit_hmc

    x = torch.tensor(x_norm).double()
    y = torch.tensor(y_norm).double()

    kernel_builder, lik_builder = build_hierarchical_kernel(
        pop_prior, kernel_type
    )
    kernels, names = kernel_builder()
    lik = lik_builder()
    model, lik = build_model(x, y, kernels, names, lik)

    # MAP first for HMC initialization
    fit_map(model, lik, x, y, n_iter=200, lr=0.05, verbose=False)

    # HMC with population priors
    mcmc_samples = fit_hmc(
        model, lik, x, y,
        n_samples=n_samples, n_warmup=n_warmup,
        verbose=verbose,
    )

    return mcmc_samples, model, lik


# ═══════════════════════════════════════════════════════════════════
# Full pipeline
# ═══════════════════════════════════════════════════════════════════

def run_hierarchical_pipeline(subjects_data, kernel_type="rbf",
                              n_hmc_samples=200, n_warmup=100,
                              verbose=True):
    """
    Full hierarchical GP pipeline.

    Args:
        subjects_data: list of (x_norm, y_norm) tuples (normalized to [0,1])
        kernel_type: "rbf", "matern32", "matern52"
        n_hmc_samples: HMC samples per subject
        n_warmup: HMC warmup per subject

    Returns:
        pop_prior: PopulationPrior
        subject_results: list of (mcmc_samples, model, lik) tuples
    """
    # Stage 1
    print("=" * 60)
    print("Stage 1: MAP fit all subjects")
    print("=" * 60)
    map_hps = map_fit_all(subjects_data, kernel_type=kernel_type,
                          verbose=verbose)

    # Stage 2
    print("\n" + "=" * 60)
    print("Stage 2: Fit population priors")
    print("=" * 60)
    pop_prior = fit_population_prior(map_hps)
    pop_prior.summary()

    # Stage 3
    print("=" * 60)
    print("Stage 3: HMC with population priors")
    print("=" * 60)
    subject_results = []
    for i, (x, y) in enumerate(subjects_data):
        if i % 5 == 0:
            print(f"\n  HMC subject {i}/{len(subjects_data)}...")
        mcmc, model, lik = hmc_fit_subject(
            x, y, pop_prior,
            kernel_type=kernel_type,
            n_samples=n_hmc_samples,
            n_warmup=n_warmup,
            verbose=(verbose and i == 0),  # verbose only for first
        )
        subject_results.append((mcmc, model, lik))

    return pop_prior, subject_results
