"""
GP kernel and prior configurations for learning curve analysis.

Key insight: both power and exponential laws are smooth, monotone decreasing.
The GP kernel encodes this WITHOUT assuming either functional form.

Kernel: ScaleKernel(RBFKernel) — just smooth variation.
All priors on NORMALIZED data (x->[0,1], y->z-score) for universality.

Three hyperprior configs for sensitivity analysis.
"""

import gpytorch
from gpytorch.kernels import ScaleKernel, RBFKernel
from gpytorch.constraints import Positive
from gpytorch.priors import GammaPrior, LogNormalPrior
from dataclasses import dataclass
from typing import Tuple, Dict, Callable


@dataclass
class PracticePriorConfig:
    """Named hyperprior configuration for learning curve GP."""
    name: str
    description: str
    lengthscale_prior: Tuple[str, float, float]
    outputscale_prior: Tuple[str, float, float]
    noise_prior: Tuple[str, float, float]


PRACTICE_CONFIGS: Dict[str, PracticePriorConfig] = {

    "practitioner": PracticePriorConfig(
        name="practitioner",
        description="Informed: gradual learning, moderate noise. ℓ~0.2-0.5 on [0,1].",
        lengthscale_prior=("gamma", 4.0, 12.0),   # mode ~0.25, mean ~0.33
        outputscale_prior=("gamma", 4.0, 4.0),     # mode ~0.75, mean ~1.0
        noise_prior=("gamma", 2.0, 8.0),           # mode ~0.125, mean ~0.25
    ),

    "moderate": PracticePriorConfig(
        name="moderate",
        description="Wider than practitioner, still rules out noise-fitting.",
        lengthscale_prior=("gamma", 2.0, 6.0),     # mean ~0.33, wider
        outputscale_prior=("gamma", 2.0, 2.0),     # mean ~1.0, broader
        noise_prior=("gamma", 1.5, 4.0),           # mean ~0.375
    ),

    "agnostic": PracticePriorConfig(
        name="agnostic",
        description="Minimally informative. Tests robustness to GP hyperprior.",
        lengthscale_prior=("lognormal", -1.5, 1.0),  # median ~0.22, very wide
        outputscale_prior=("lognormal", 0.0, 1.0),   # median ~1.0, wide
        noise_prior=("lognormal", -1.5, 1.0),        # wide
    ),
}


def _make_prior(family: str, p1: float, p2: float):
    if family == "gamma":
        return GammaPrior(p1, p2)
    elif family == "lognormal":
        return LogNormalPrior(p1, p2)
    raise ValueError(f"Unknown prior family: {family}")


def build_kernel(config: PracticePriorConfig):
    """
    Build GP kernel for learning curves. Just RBF — no linear, no periodic.
    Returns (kernel_components, component_names).
    """
    se = ScaleKernel(
        RBFKernel(
            lengthscale_constraint=Positive(),
            lengthscale_prior=_make_prior(*config.lengthscale_prior),
        ),
        outputscale_constraint=Positive(),
        outputscale_prior=_make_prior(*config.outputscale_prior),
    )
    return [se], ["smooth_decay"]


def build_likelihood(config: PracticePriorConfig):
    return gpytorch.likelihoods.GaussianLikelihood(
        noise_constraint=Positive(),
        noise_prior=_make_prior(*config.noise_prior),
    )


def get_kernel_builder(config_name: str = "moderate") -> Callable:
    """Callable that builds fresh kernel components."""
    config = PRACTICE_CONFIGS[config_name]
    return lambda: build_kernel(config)


def get_likelihood_builder(config_name: str = "moderate") -> Callable:
    """Callable that builds a fresh likelihood."""
    config = PRACTICE_CONFIGS[config_name]
    return lambda: build_likelihood(config)
