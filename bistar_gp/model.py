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

        # Build sum kernel. The component kernels are registered ONLY through
        # covar_module (a plain list here, not an nn.ModuleList) so each kernel
        # prior is registered exactly once. Registering them a second time via a
        # ModuleList made pyro_sample_from_prior create a duplicate HMC latent
        # site per hyperparameter and add the kernel priors to the NUTS target
        # twice, biasing every HMC posterior.
        self.kernel_components = list(kernel_components)
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


# ── HMC sample-site naming ───────────────────────────────────────
#
# fit_hmc/fit_mcmc_simple return dicts keyed by pyro sample-site name. The
# names follow the module tree above: each kernel hyperparameter appears once,
# at "covar_module.kernels.{i}.<hp>_prior", and the noise at
# "likelihood.noise_covar.noise_prior". Archives saved by older code carry
# extra sites: "kernel_components.{i}.*" duplicates (disconnected prior draws
# from the double-registration bug) and a bare "noise_covar.noise_prior" from
# the era when fit_hmc sampled the likelihood separately (in those archives
# the bare site is the one that was wired to the likelihood). Every consumer
# must go through the two helpers below rather than parsing names itself.

def select_hmc_sites(sample_keys):
    """Pick the sample sites actually wired to the likelihood, across eras.

    Returns the kernel hyperparameter keys plus the noise key, preferring the
    current naming and falling back to legacy names only when the current ones
    are absent, so both fresh runs and old cached archives resolve to the
    connected (posterior) latents.
    """
    keys = list(sample_keys)
    kernel_keys = [k for k in keys if k.startswith("covar_module.kernels.")]
    if not kernel_keys:  # archives predating the covar_module naming
        kernel_keys = [k for k in keys if k.startswith("kernel_components.")]
    if "noise_covar.noise_prior" in keys:
        # Legacy archives: the bare site was sampled last and overwrote the
        # likelihood.* one, so it holds the connected draws.
        noise_keys = ["noise_covar.noise_prior"]
    else:
        noise_keys = [k for k in keys if k.endswith("noise_covar.noise_prior")]
    return kernel_keys + noise_keys


def apply_hp_value(model, likelihood, pyro_name, value):
    """Set one hyperparameter on model/likelihood from a sample-site name.

    Accepts both current ("covar_module.kernels.{i}.*") and legacy
    ("kernel_components.{i}.*", "noise_covar.noise*") site names. Returns True
    if the name was recognized and applied, False otherwise.
    """
    if "noise_covar.noise" in pyro_name:
        likelihood.noise = value
        return True
    parts = pyro_name.split(".")
    if parts[0] == "covar_module" and parts[1] == "kernels":
        comp_idx = int(parts[2])
    elif parts[0] == "kernel_components":
        comp_idx = int(parts[1])
    else:
        return False
    kernel = model.kernel_components[comp_idx]
    if "base_kernel.lengthscale" in pyro_name:
        kernel.base_kernel.lengthscale = value
    elif "base_kernel.period_length" in pyro_name:
        kernel.base_kernel.period_length = value
    elif "outputscale" in pyro_name:
        kernel.outputscale = value
    elif "variance" in pyro_name:
        kernel.variance = value
    else:
        return False
    return True


# ── Kernel builders ──────────────────────────────────────────────

MAUNA_FROZEN_PERIOD = 1.0  # A10: seasonal period frozen at exactly 1.0


def assert_mauna_period_frozen(model):
    """A10 invariant check: every periodic component stays at exactly 1.0.

    Call after any MAP / multi-start / sampling path that touches a Mauna
    model. Verifies, for each PeriodicKernel among the model's components,
    that the constrained period equals MAUNA_FROZEN_PERIOD bit-exactly and
    that its raw parameter remains gradient-frozen. Raises AssertionError with
    the offending value otherwise.
    """
    checked = 0
    for kernel in model.kernel_components:
        base = getattr(kernel, "base_kernel", kernel)
        if isinstance(base, PeriodicKernel):
            period = base.period_length.item()
            assert period == MAUNA_FROZEN_PERIOD, (
                f"A10 violation: period_length = {period!r}, expected exactly "
                f"{MAUNA_FROZEN_PERIOD} (docs/plan-d19-mauna.md A10)")
            assert not base.raw_period_length.requires_grad, (
                "A10 violation: raw_period_length is trainable again")
            checked += 1
    assert checked > 0, "no PeriodicKernel found; nothing to check"


def build_mauna_loa_kernels():
    """Trend + Seasonal + Medium-term for CO2 decomposition."""
    trend = ScaleKernel(
        RBFKernel(
            lengthscale_constraint=Positive(),
            lengthscale_prior=LogNormalPrior(4.0, 1.0),
        ),
        outputscale_constraint=Positive(),
        outputscale_prior=GammaPrior(4.0, 0.5),
    )

    seasonal = ScaleKernel(
        PeriodicKernel(
            period_length_constraint=Interval(0.99, 1.01),
            lengthscale_constraint=Positive(),
            lengthscale_prior=GammaPrior(3.0, 2.0),
        ),
        outputscale_constraint=Positive(),
        outputscale_prior=GammaPrior(3.0, 1.0),
    )
    # A10 period freeze (D19/D20): the old "keep this one fixed" comment was
    # aspirational — raw_period_length stayed requires_grad=True, so fit_map
    # drifted the plug-in period to ~0.9996 (standing disclosure 4 in
    # docs/plan-d19-mauna.md §6.14). Freeze it at EXACTLY 1.0: raw = 0 under
    # Interval(0.99, 1.01) maps to lower + (upper-lower)*sigmoid(0) = 1.0
    # exactly in float64 (verified), and with requires_grad off the period has
    # no gradient, no optimizer state, and no fit_mcmc_simple proposal
    # dimension. It carries no prior, so the pyro sample-site inventory stays
    # at 7 (asserted in tests).
    with torch.no_grad():
        seasonal.base_kernel.raw_period_length.fill_(0.0)
    seasonal.base_kernel.raw_period_length.requires_grad_(False)
    assert seasonal.base_kernel.period_length.item() == MAUNA_FROZEN_PERIOD

    medium = ScaleKernel(
        RBFKernel(
            lengthscale_constraint=Positive(),
            lengthscale_prior=GammaPrior(3.0, 1.0),
        ),
        outputscale_constraint=Positive(),
        outputscale_prior=GammaPrior(2.0, 1.0),
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