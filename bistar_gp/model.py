"""
GPyTorch model wrapper with robustness built in:
- Double precision
- Hyperparameter constraints (away from zero!)
- Clean interface for additive kernel decomposition
"""

import torch
import gpytorch
from gpytorch.kernels import ScaleKernel, RBFKernel, LinearKernel, PeriodicKernel
from gpytorch.constraints import Interval, Positive
from gpytorch.priors import GammaPrior, LogNormalPrior
from typing import List, Optional, Dict, Any

torch.set_default_dtype(torch.float64)


class AdditiveGPModel(gpytorch.models.ExactGP):
    """Exact GP with named additive kernel components for decomposition."""

    def __init__(self, train_x, train_y, likelihood, kernel_components, component_names=None):
        super().__init__(train_x, train_y, likelihood)
        self.mean_module = gpytorch.means.ZeroMean()
        self.component_names = component_names or [f"comp_{i}" for i in range(len(kernel_components))]
        self.kernel_components = torch.nn.ModuleList(kernel_components)

        # Build sum kernel
        self.covar_module = self.kernel_components[0]
        for k in self.kernel_components[1:]:
            self.covar_module = self.covar_module + k

    def forward(self, x):
        mean = self.mean_module(x)
        covar = self.covar_module(x)
        return gpytorch.distributions.MultivariateNormal(mean, covar)

    def get_component_kernel_matrices(self, X_train, X_test):
        """Evaluate each component kernel at train/test points."""
        matrices = {}
        for name, kernel in zip(self.component_names, self.kernel_components):
            matrices[name] = {
                "XX": kernel(X_train, X_train).evaluate().detach(),
                "XstarX": kernel(X_test, X_train).evaluate().detach(),
                "XstarXstar": kernel(X_test, X_test).evaluate().detach(),
                "XXstar": kernel(X_train, X_test).evaluate().detach(),
            }
        return matrices


# ── Kernel builders ──────────────────────────────────────────────

def build_toy_kernels():
    """SE (truth) + Linear (bias) — thesis toy example."""
    se = ScaleKernel(
        RBFKernel(
            lengthscale_constraint=Interval(0.5, 30.0),
            lengthscale_prior=GammaPrior(6.0, 0.85),
        ),
        outputscale_constraint=Interval(0.1, 20.0),
        outputscale_prior=GammaPrior(6.0, 0.85),
    )
    linear = LinearKernel(
        variance_constraint=Interval(0.01, 20.0),
        variance_prior=GammaPrior(6.0, 0.85),
    )
    return [se, linear], ["unbiased_se", "bias_linear"]


def build_mauna_loa_kernels():
    """Trend + Seasonal + Medium-term for CO2 decomposition."""
    trend = ScaleKernel(
        RBFKernel(
            lengthscale_constraint=Interval(10.0, 200.0),
            lengthscale_prior=LogNormalPrior(4.0, 1.0),
        ),
        outputscale_constraint=Interval(1.0, 500.0),
    )

    seasonal = ScaleKernel(
        PeriodicKernel(
            period_length_constraint=Interval(0.99, 1.01),  # fixed at 1 year
            lengthscale_constraint=Interval(0.05, 5.0),
        ),
        outputscale_constraint=Interval(0.1, 50.0),
    )
    seasonal.base_kernel.period_length = 1.0

    medium = ScaleKernel(
        RBFKernel(
            lengthscale_constraint=Interval(0.5, 20.0),
            lengthscale_prior=GammaPrior(3.0, 1.0),
        ),
        outputscale_constraint=Interval(0.01, 10.0),
    )

    return [trend, seasonal, medium], ["trend", "seasonal", "medium_term"]


def build_likelihood(noise_constraint=None, noise_prior=None):
    return gpytorch.likelihoods.GaussianLikelihood(
        noise_constraint=noise_constraint or Positive(),
        noise_prior=noise_prior or GammaPrior(1.75, 1.0),
    )

def build_model(train_x, train_y, kernel_components, component_names, likelihood=None):
    """Build full model. Enforces float64. Returns (model, likelihood)."""
    train_x, train_y = train_x.double(), train_y.double()
    if likelihood is None:
        likelihood = build_likelihood()
    model = AdditiveGPModel(train_x, train_y, likelihood, kernel_components, component_names)
    return model.double(), likelihood.double()

def build_toy_kernels():
    """SE (truth) + Linear (bias) — thesis toy example."""
    se = ScaleKernel(
        RBFKernel(
            lengthscale_constraint=Positive(),
            #lengthscale_prior=GammaPrior(6.0, 0.85),
            lengthscale_prior=GammaPrior(2.0, 2.0),  # mean ~1, favors short lengthscales
        ),
        outputscale_constraint=Positive(),
        outputscale_prior=GammaPrior(6.0, 0.85),
    )
    linear = LinearKernel(
        variance_constraint=Positive(),
        variance_prior=GammaPrior(6.0, 0.85),
    )
    return [se, linear], ["unbiased_se", "bias_linear"]