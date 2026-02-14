"""
bistar_gp: Bayesian Inference Plus (BI*) with Gaussian Process decomposition.

Implements the framework from Chandramouli & Shiffrin for:
- Additive GP kernel composition and decomposition
- Bias mitigation via kernel separation
- Full Bayesian inference over hyperparameters
"""

from .decompose import decompose_additive_gp, sample_from_component
from .model import AdditiveGPModel, build_model, build_toy_kernels, build_mauna_loa_kernels, build_likelihood
from .fit import fit_map, fit_mcmc_simple, print_hyperparameters
from .debias import decompose_model, decompose_model_mcmc, DecompositionResult, ComponentResult
from .data import generate_toy_data, load_mauna_loa

__all__ = [
    "decompose_additive_gp", "sample_from_component",
    "AdditiveGPModel", "build_model", "build_toy_kernels", "build_mauna_loa_kernels", "build_likelihood",
    "fit_map", "fit_mcmc_simple", "print_hyperparameters",
    "decompose_model", "decompose_model_mcmc", "DecompositionResult", "ComponentResult",
    "generate_toy_data", "load_mauna_loa",
]
