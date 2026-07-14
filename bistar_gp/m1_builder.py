"""M1 constrained short-scale Matérn component (prereg v1.17 A3)."""

import math

import torch
from gpytorch.constraints import Interval, Positive
from gpytorch.kernels import MaternKernel, ScaleKernel
from gpytorch.priors import LogNormalPrior
from gpytorch.priors.prior import Prior
from gpytorch.priors.utils import _bufferize_attributes
from torch.distributions import Normal, TransformedDistribution, constraints
from torch.distributions.transforms import AffineTransform, SigmoidTransform
from torch.nn import Module as TModule

from .m2c_freeze_m1 import (
    M1_LENGTHSCALE_LOWER,
    M1_LENGTHSCALE_UPPER,
    M1_LENGTHSCALE_Z_LOC,
    M1_LENGTHSCALE_Z_SCALE,
    M1_MATERN_NU,
    M1_OUTPUTSCALE_MEDIAN,
    M1_OUTPUTSCALE_SIGMA,
    M1_SHORT_SCALE_NAME,
)


class LogitNormal(TransformedDistribution):
    """z ~ Normal(loc, scale); x = lower + (upper-lower)*sigmoid(z) on the hard interval."""
    arg_constraints = {"loc": constraints.real, "scale": constraints.positive}

    def __init__(self, loc, scale, lower=0.0, upper=1.0, validate_args=None):
        loc = torch.as_tensor(loc, dtype=torch.get_default_dtype())
        scale = torch.as_tensor(scale, dtype=torch.get_default_dtype())
        self._lower = float(lower)
        self._span = float(upper) - float(lower)
        base = Normal(loc, scale, validate_args=validate_args)
        super().__init__(base, [SigmoidTransform(), AffineTransform(self._lower, self._span)],
                         validate_args=validate_args)

    @property
    def loc(self):
        return self.base_dist.loc

    @property
    def scale(self):
        return self.base_dist.scale

    @property
    def support(self):
        return constraints.interval(self._lower, self._lower + self._span)


class LogitNormalPrior(Prior, LogitNormal):
    """Logit-normal prior on [lower, upper]; mirrors gpytorch LogNormalPrior."""

    def __init__(self, loc, scale, lower=0.1, upper=1.0, validate_args=None, transform=None):
        TModule.__init__(self)
        LogitNormal.__init__(self, loc=loc, scale=scale, lower=lower, upper=upper,
                             validate_args=validate_args)
        _bufferize_attributes(self, ("loc", "scale"))
        self._transform = transform

    def expand(self, batch_shape):
        batch_shape = torch.Size(batch_shape)
        return LogitNormalPrior(self.loc.expand(batch_shape), self.scale.expand(batch_shape),
                                self._lower, self._lower + self._span)


def build_m1_matern_component():
    """M1 constrained short-scale Matern-3/2 (adds lengthscale + outputscale => 2 sites)."""
    return ScaleKernel(
        MaternKernel(
            nu=M1_MATERN_NU,
            lengthscale_constraint=Interval(
                M1_LENGTHSCALE_LOWER, M1_LENGTHSCALE_UPPER
            ),
            lengthscale_prior=LogitNormalPrior(
                M1_LENGTHSCALE_Z_LOC,
                M1_LENGTHSCALE_Z_SCALE,
                M1_LENGTHSCALE_LOWER,
                M1_LENGTHSCALE_UPPER,
            ),
        ),
        outputscale_constraint=Positive(),
        outputscale_prior=LogNormalPrior(
            math.log(M1_OUTPUTSCALE_MEDIAN), M1_OUTPUTSCALE_SIGMA
        ),
    ).double()


def augment_with_m1_short_scale(kernel_components, component_names):
    """Return new component/name lists with the M1 short-scale term appended."""
    m1 = build_m1_matern_component()
    return (
        list(kernel_components) + [m1],
        list(component_names) + [M1_SHORT_SCALE_NAME],
    )


def build_mauna_loa_m1_kernels():
    """Build the frozen Mauna M0 decomposition augmented with M1."""
    from .model import build_mauna_loa_kernels

    kernels, names = build_mauna_loa_kernels()
    return augment_with_m1_short_scale(kernels, names)


__all__ = [
    "LogitNormalPrior",
    "build_m1_matern_component",
    "augment_with_m1_short_scale",
    "build_mauna_loa_m1_kernels",
]
