"""
Debiasing pipeline: fit additive GP → decompose → extract unbiased components.
Works for any number of additive components.
"""

import torch
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass

from .decompose import decompose_additive_gp, sample_from_component


@dataclass
class ComponentResult:
    name: str
    mean: np.ndarray       # (n_test,)
    std: np.ndarray        # (n_test,)
    cov: np.ndarray        # (n_test, n_test)
    samples: np.ndarray    # (n_samples, n_test)


@dataclass
class DecompositionResult:
    x_test: np.ndarray
    x_train: np.ndarray
    y_train: np.ndarray
    components: Dict[str, ComponentResult]
    full_mean: np.ndarray
    full_std: np.ndarray
    noise_var: float


def decompose_model(model, likelihood, x_train, y_train, x_test, n_samples=25, jitter=1e-4):
    """
    Decompose a fitted additive GP into its components.
    Single set of hyperparameters (MAP). For full Bayesian, use decompose_model_mcmc.
    """
    model.eval()
    likelihood.eval()
    x_train, y_train, x_test = x_train.double(), y_train.double(), x_test.double()
    noise_var = likelihood.noise.item()

    km = model.get_component_kernel_matrices(x_train, x_test)
    names = model.component_names

    with torch.no_grad():
        results = decompose_additive_gp(
            [km[n]["XX"] for n in names],
            [km[n]["XstarX"] for n in names],
            [km[n]["XstarXstar"] for n in names],
            [km[n]["XXstar"] for n in names],
            noise_var, y_train, jitter,
        )

    components = {}
    full_mean = torch.zeros(x_test.shape[0], dtype=torch.float64)

    for (mean_i, cov_i), name in zip(results, names):
        samples_i = sample_from_component(mean_i, cov_i, n_samples)
        std_i = torch.sqrt(torch.clamp(torch.diag(cov_i), min=1e-10))
        components[name] = ComponentResult(
            name=name, mean=mean_i.numpy(), std=std_i.numpy(),
            cov=cov_i.numpy(), samples=samples_i.numpy(),
        )
        full_mean += mean_i

    full_cov = sum(c.cov for c in components.values())
    full_std = np.sqrt(np.clip(np.diag(full_cov), 1e-10, None))

    return DecompositionResult(
        x_test=x_test.numpy(), x_train=x_train.numpy(), y_train=y_train.numpy(),
        components=components, full_mean=full_mean.numpy(), full_std=full_std, noise_var=noise_var,
    )


def decompose_model_mcmc(model, likelihood, x_train, y_train, x_test,
                         mcmc_samples, n_posterior_samples=100, jitter=1e-4):
    """
    Full Bayesian decomposition: iterate over MCMC hyperparameter samples.
    Produces wider uncertainty bands (thesis Fig 7a vs Fig 6).
    """
    model.eval()
    likelihood.eval()
    x_train, y_train, x_test = x_train.double(), y_train.double(), x_test.double()
    n_test = x_test.shape[0]

    param_list = [(n, p) for n, p in
                  list(model.named_parameters()) + list(likelihood.named_parameters())
                  if p.requires_grad and p.numel() == 1]
    param_names_ordered = [n for n, _ in param_list]

    mcmc_keys = list(mcmc_samples.keys())
    total_mcmc = len(mcmc_samples[mcmc_keys[0]])
    indices = np.random.choice(total_mcmc, min(n_posterior_samples, total_mcmc), replace=False)

    all_means = {n: [] for n in model.component_names}

    for idx in indices:
        # Set hyperparameters to this MCMC sample
        for i, (_, p) in enumerate(param_list):
            if i < len(mcmc_keys):
                p.data.fill_(mcmc_samples[mcmc_keys[i]][idx])

        noise_var = likelihood.noise.item()
        km = model.get_component_kernel_matrices(x_train, x_test)
        names = model.component_names

        with torch.no_grad():
            try:
                results = decompose_additive_gp(
                    [km[n]["XX"] for n in names], [km[n]["XstarX"] for n in names],
                    [km[n]["XstarXstar"] for n in names], [km[n]["XXstar"] for n in names],
                    noise_var, y_train, jitter,
                )
                for (mean_i, _), comp_name in zip(results, names):
                    all_means[comp_name].append(mean_i.numpy())
            except RuntimeError:
                continue

    components = {}
    full_mean = np.zeros(n_test)
    for comp_name in model.component_names:
        means = np.stack(all_means[comp_name])
        avg = means.mean(0)
        std = means.std(0)
        components[comp_name] = ComponentResult(
            name=comp_name, mean=avg, std=std,
            cov=np.diag(std**2), samples=means,  # samples = means across MCMC
        )
        full_mean += avg

    all_full = sum(np.stack(all_means[n]) for n in model.component_names)
    full_std = all_full.std(0)

    return DecompositionResult(
        x_test=x_test.numpy(), x_train=x_train.numpy(), y_train=y_train.numpy(),
        components=components, full_mean=full_mean, full_std=full_std, noise_var=likelihood.noise.item(),
    )
