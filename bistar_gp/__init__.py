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
from .candidates import build_toy_candidates, LinearModel, SinusoidalModel, SinLinearModel, QuadraticModel
from .bms_star import (
    extract_gp_predictives, compute_G_matrix, run_bms_star, soft_transfer,
    kl_forward, kl_backward, kl_symmetric, hellinger_distance,
    pw_kl_forward, pw_kl_backward, pw_kl_symmetric, pw_hellinger, pw_mse, pw_nll,
    METRICS,
    plot_bms_star_results, plot_G_heatmaps, plot_candidate_predictions, print_bms_star_table,
)
from .mauna_loa_candidates import (
    QuadSinModel, QuadHarmonic2Model, build_mauna_loa_candidates,
)
from .config import PRIOR_CONFIGS, ExperimentConfig, build_kernels_from_config, build_likelihood_from_config

__all__ = [
    "decompose_additive_gp", "sample_from_component",
    "AdditiveGPModel", "build_model", "build_toy_kernels", "build_mauna_loa_kernels", "build_likelihood",
    "fit_map", "fit_mcmc_simple", "print_hyperparameters",
    "decompose_model", "decompose_model_mcmc", "DecompositionResult", "ComponentResult",
    "generate_toy_data", "load_mauna_loa",
    "build_toy_candidates", "LinearModel", "SinusoidalModel", "SinLinearModel", "QuadraticModel",
    "extract_gp_predictives", "compute_G_matrix", "run_bms_star", "soft_transfer",
    "kl_forward", "kl_backward", "kl_symmetric", "hellinger_distance",
    "pw_kl_forward", "pw_kl_backward", "pw_kl_symmetric", "pw_hellinger", "pw_mse", "pw_nll",
    "METRICS",
    "plot_bms_star_results", "plot_G_heatmaps", "plot_candidate_predictions", "print_bms_star_table",
    "PRIOR_CONFIGS", "ExperimentConfig", "build_kernels_from_config", "build_likelihood_from_config",
]
