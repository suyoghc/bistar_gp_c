"""
Configuration for BMS* experiments.

Defines:
- Named GP hyperprior configurations for sensitivity analysis
- Sample caching paths and behavior
- Experiment parameters (n_points, n_samples, τ range, etc.)
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# ── Paths ─────────────────────────────────────────────────────────

CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")


# ── Prior Configurations ──────────────────────────────────────────

@dataclass
class PriorConfig:
    """
    Named hyperprior configuration for the GP.

    Each config specifies the prior family and parameters for:
    - SE kernel: lengthscale, outputscale
    - Linear kernel: variance
    - Noise variance
    """
    name: str
    description: str

    # SE lengthscale prior: (family, param1, param2)
    se_lengthscale_prior: Tuple[str, float, float]
    se_lengthscale_bounds: Tuple[float, float]

    # SE outputscale prior
    se_outputscale_prior: Tuple[str, float, float]
    se_outputscale_bounds: Tuple[float, float]

    # Linear kernel variance prior
    linear_variance_prior: Tuple[str, float, float]
    linear_variance_bounds: Tuple[float, float]

    # Noise prior
    noise_prior: Tuple[str, float, float]
    noise_bounds: Tuple[float, float]


# Named prior configurations for sensitivity analysis
PRIOR_CONFIGS: Dict[str, PriorConfig] = {

    "informative": PriorConfig(
        name="informative",
        description="Moderate Gamma priors — current default. Concentrates mass around reasonable values.",
        se_lengthscale_prior=("gamma", 6.0, 0.85),
        se_lengthscale_bounds=(0.5, 30.0),
        se_outputscale_prior=("gamma", 6.0, 0.85),
        se_outputscale_bounds=(0.1, 20.0),
        linear_variance_prior=("gamma", 6.0, 0.85),
        linear_variance_bounds=(0.01, 20.0),
        noise_prior=("gamma", 1.75, 1.0),
        noise_bounds=(1e-4, 10.0),
    ),

    "vague": PriorConfig(
        name="vague",
        description="Broad LogNormal priors — lets data dominate. Tests BMS* under minimal prior info.",
        se_lengthscale_prior=("lognormal", 0.0, 2.0),
        se_lengthscale_bounds=(0.1, 100.0),
        se_outputscale_prior=("lognormal", 0.0, 2.0),
        se_outputscale_bounds=(0.01, 100.0),
        linear_variance_prior=("lognormal", 0.0, 2.0),
        linear_variance_bounds=(0.001, 100.0),
        noise_prior=("lognormal", -1.0, 2.0),
        noise_bounds=(1e-5, 50.0),
    ),

    "misspecified_tight": PriorConfig(
        name="misspecified_tight",
        description="Tight Gamma concentrated away from truth. Prior actively fights the data.",
        se_lengthscale_prior=("gamma", 20.0, 4.0),   # concentrates near 5, true is ~1-2
        se_lengthscale_bounds=(1.0, 50.0),
        se_outputscale_prior=("gamma", 20.0, 4.0),
        se_outputscale_bounds=(0.5, 50.0),
        linear_variance_prior=("gamma", 20.0, 4.0),
        linear_variance_bounds=(0.1, 50.0),
        noise_prior=("gamma", 5.0, 5.0),              # concentrates near 1, true is ~0.09
        noise_bounds=(1e-3, 20.0),
    ),

    "low_noise": PriorConfig(
        name="low_noise",
        description="Informative kernel priors but very small noise prior — overconfident GP.",
        se_lengthscale_prior=("gamma", 6.0, 0.85),
        se_lengthscale_bounds=(0.5, 30.0),
        se_outputscale_prior=("gamma", 6.0, 0.85),
        se_outputscale_bounds=(0.1, 20.0),
        linear_variance_prior=("gamma", 6.0, 0.85),
        linear_variance_bounds=(0.01, 20.0),
        noise_prior=("gamma", 2.0, 20.0),             # concentrates near 0.1
        noise_bounds=(1e-5, 1.0),
    ),

    "high_noise": PriorConfig(
        name="high_noise",
        description="Informative kernel priors but large noise prior — underconfident GP.",
        se_lengthscale_prior=("gamma", 6.0, 0.85),
        se_lengthscale_bounds=(0.5, 30.0),
        se_outputscale_prior=("gamma", 6.0, 0.85),
        se_outputscale_bounds=(0.1, 20.0),
        linear_variance_prior=("gamma", 6.0, 0.85),
        linear_variance_bounds=(0.01, 20.0),
        noise_prior=("gamma", 2.0, 0.5),              # concentrates near 4
        noise_bounds=(0.1, 50.0),
    ),
}


# ── Experiment Configuration ──────────────────────────────────────

@dataclass
class ExperimentConfig:
    """Full experiment configuration."""

    # Data
    n_points: int = 50
    noise_std: float = 0.3
    bias_slope: float = 0.25
    seed: int = 42
    x_range: Tuple[float, float] = (-10.0, 10.0)

    # Evaluation grid
    n_eval: int = 60

    # HMC
    n_hmc_samples: int = 500
    n_warmup: int = 200
    n_posterior_samples: int = 200     # subsample from HMC for BMS*

    # BMS*
    tau_range: Tuple[float, float] = (-1, 2)  # log10 scale
    n_taus: int = 30
    metrics: List[str] = field(default_factory=lambda: [
        "kl_forward", "kl_backward", "kl_symmetric", "hellinger",
        "pw_kl_forward", "pw_kl_backward", "pw_kl_symmetric", "pw_hellinger",
        "pw_mse", "pw_nll",
    ])

    # Prior sensitivity
    prior_configs: List[str] = field(default_factory=lambda: [
        "informative", "vague", "misspecified_tight", "low_noise", "high_noise"
    ])

    # Caching
    use_cache: bool = True            # load cached samples if available
    save_cache: bool = True           # save new samples to cache
    cache_dir: str = CACHE_DIR
    force_rerun: bool = False         # ignore cache, rerun everything

    def get_cache_path(self, prior_name: str) -> str:
        """Path to cached HMC samples for a given prior config."""
        os.makedirs(self.cache_dir, exist_ok=True)
        return os.path.join(
            self.cache_dir,
            f"hmc_samples_{prior_name}_n{self.n_hmc_samples}_s{self.seed}.npz"
        )

    def cache_exists(self, prior_name: str) -> bool:
        return os.path.exists(self.get_cache_path(prior_name))


# ── Cache I/O ─────────────────────────────────────────────────────

def save_hmc_samples(samples: Dict, path: str):
    """Save HMC samples dict to .npz file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # numpy savez expects arrays
    import numpy as np
    np.savez(path, **{k: np.array(v) for k, v in samples.items()})
    print(f"  Cached HMC samples → {path}")


def load_hmc_samples(path: str) -> Dict:
    """Load HMC samples from .npz file."""
    import numpy as np
    data = np.load(path)
    samples = {k: data[k] for k in data.files}
    print(f"  Loaded cached HMC samples ← {path}")
    return samples


# ── Kernel Builder from Config ────────────────────────────────────

def build_kernels_from_config(prior_config: PriorConfig):
    """
    Build GP kernel components with priors from a PriorConfig.
    Returns (kernels, names) matching the interface of build_toy_kernels().
    Uses Positive() constraints (not Interval) — Pyro HMC needs open bounds.
    """
    import gpytorch
    from gpytorch.kernels import ScaleKernel, RBFKernel, LinearKernel
    from gpytorch.constraints import Positive
    from gpytorch.priors import GammaPrior, LogNormalPrior

    def make_prior(family, p1, p2):
        if family == "gamma":
            return GammaPrior(p1, p2)
        elif family == "lognormal":
            return LogNormalPrior(p1, p2)
        else:
            raise ValueError(f"Unknown prior family: {family}")

    se = ScaleKernel(
        RBFKernel(
            lengthscale_constraint=Positive(),
            lengthscale_prior=make_prior(*prior_config.se_lengthscale_prior),
        ),
        outputscale_constraint=Positive(),
        outputscale_prior=make_prior(*prior_config.se_outputscale_prior),
    )
    linear = LinearKernel(
        variance_constraint=Positive(),
        variance_prior=make_prior(*prior_config.linear_variance_prior),
    )
    return [se, linear], ["unbiased_se", "bias_linear"]


def build_likelihood_from_config(prior_config: PriorConfig):
    """Build likelihood with noise prior from config. Uses Positive() constraint."""
    import gpytorch
    from gpytorch.constraints import Positive
    from gpytorch.priors import GammaPrior, LogNormalPrior

    def make_prior(family, p1, p2):
        if family == "gamma":
            return GammaPrior(p1, p2)
        elif family == "lognormal":
            return LogNormalPrior(p1, p2)
        else:
            raise ValueError(f"Unknown prior family: {family}")

    return gpytorch.likelihoods.GaussianLikelihood(
        noise_constraint=Positive(),
        noise_prior=make_prior(*prior_config.noise_prior),
    )


# ── Default config ────────────────────────────────────────────────

DEFAULT_CONFIG = ExperimentConfig()
