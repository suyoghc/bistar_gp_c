"""Hermetic A3 tests for the prereg v1.17 M1 Matérn builder."""

import math

import numpy as np
import pytest


torch = pytest.importorskip("torch")
gpytorch = pytest.importorskip("gpytorch")
pytest.importorskip("pyro")

from bistar_gp.e1_potential import build_e1_potential
from bistar_gp.m1_builder import (
    LogitNormalPrior,
    augment_with_m1_short_scale,
    build_m1_matern_component,
    build_mauna_loa_m1_kernels,
)
from bistar_gp.m2c_freeze_m1 import (
    M1_LENGTHSCALE_LOWER,
    M1_LENGTHSCALE_QREF,
    M1_LENGTHSCALE_UPPER,
    M1_LENGTHSCALE_Z_LOC,
    M1_LENGTHSCALE_Z_SCALE,
    M1_MATERN_NU,
    M1_OUTPUTSCALE_MEDIAN,
    M1_OUTPUTSCALE_SIGMA,
    M1_SHORT_SCALE_NAME,
)
from bistar_gp.model import (
    MAUNA_FROZEN_PERIOD,
    build_mauna_loa_kernels,
    build_model,
)


torch.set_default_dtype(torch.float64)


def _prior(**kwargs):
    return LogitNormalPrior(
        M1_LENGTHSCALE_Z_LOC,
        M1_LENGTHSCALE_Z_SCALE,
        M1_LENGTHSCALE_LOWER,
        M1_LENGTHSCALE_UPPER,
        **kwargs,
    )


def _synthetic_monthly(n=36):
    """Deterministic synthetic monthly structure; no scientific data."""
    x = torch.arange(n, dtype=torch.float64) / 12.0
    y = 0.05 * x + 0.3 * torch.sin(2.0 * torch.pi * x)
    return x, y


@pytest.fixture(scope="module")
def m1_e1():
    x, y = _synthetic_monthly()
    kernels, names = build_mauna_loa_m1_kernels()
    model, likelihood = build_model(x, y, kernels, names)
    return x, y, model, likelihood, build_e1_potential(
        model, likelihood, x, y
    )


def test_logit_normal_normalizes_by_quadrature_on_hard_support():
    prior = _prior(validate_args=False)
    eps = torch.tensor(1e-9)
    points = torch.linspace(
        M1_LENGTHSCALE_LOWER + eps,
        M1_LENGTHSCALE_UPPER - eps,
        20001,
    )
    density = torch.exp(prior.log_prob(points))
    integral = torch.trapezoid(density, points)
    assert integral.item() == pytest.approx(1.0, abs=1e-3)
    assert not prior.support.check(
        torch.tensor(M1_LENGTHSCALE_LOWER - 1e-12)
    )
    assert not prior.support.check(
        torch.tensor(M1_LENGTHSCALE_UPPER + 1e-12)
    )


def test_logit_normal_rejects_outside_support_and_samples_strictly_inside():
    prior = _prior()
    for outside in (
        M1_LENGTHSCALE_LOWER - 1e-12,
        M1_LENGTHSCALE_UPPER + 1e-12,
    ):
        with pytest.raises(ValueError):
            prior.log_prob(torch.tensor(outside))

    with torch.random.fork_rng():
        torch.manual_seed(419)
        samples = prior.sample((10000,))
    assert torch.all(samples > M1_LENGTHSCALE_LOWER)
    assert torch.all(samples < M1_LENGTHSCALE_UPPER)


def test_hard_support_is_the_closed_interval_and_endpoints_are_unreachable():
    # The freeze pins "hard support [0.1, 1.0]" — a CLOSED interval, so the exact
    # endpoints are in support (this is freeze-faithful, not a leak).  Over the
    # practically-reachable raw range the HMC/MLL path never lands on an endpoint:
    # gpytorch's Interval(0.1, 1.0) maps raw to 0.1 + 0.9*sigmoid(raw), strictly
    # interior until float64 sigmoid saturates only at extreme |raw| ~ 40.
    prior = _prior()
    assert prior.support.check(torch.tensor(M1_LENGTHSCALE_LOWER))
    assert prior.support.check(torch.tensor(M1_LENGTHSCALE_UPPER))
    constraint = build_m1_matern_component().base_kernel.raw_lengthscale_constraint
    raws = torch.tensor([-12.0, -3.0, 0.0, 3.0, 12.0])
    constrained = constraint.transform(raws)
    assert torch.all(constrained > M1_LENGTHSCALE_LOWER)
    assert torch.all(constrained < M1_LENGTHSCALE_UPPER)


def test_fixed_seed_sampling_and_analytic_lengthscale_quantiles():
    prior = _prior()
    with torch.random.fork_rng():
        torch.manual_seed(20260713)
        samples = prior.sample((200000,))
    empirical = torch.quantile(samples, torch.tensor([0.1, 0.5, 0.9]))
    assert np.allclose(empirical.numpy(), M1_LENGTHSCALE_QREF, atol=0.01)

    standard = torch.distributions.Normal(0.0, 1.0)
    z_quantiles = standard.icdf(torch.tensor([0.1, 0.5, 0.9]))
    analytic = M1_LENGTHSCALE_LOWER + (
        M1_LENGTHSCALE_UPPER - M1_LENGTHSCALE_LOWER
    ) * torch.sigmoid(
        M1_LENGTHSCALE_Z_LOC + M1_LENGTHSCALE_Z_SCALE * z_quantiles
    )
    assert np.allclose(analytic.numpy(), (0.1600, 0.3000, 0.5801), atol=1e-4)


def test_logit_normal_change_of_variables_matches_normal_target():
    prior = _prior()
    z = torch.tensor([-4.0, -1.5, 0.0, 0.75, 3.5])
    sigmoid = torch.sigmoid(z)
    span = M1_LENGTHSCALE_UPPER - M1_LENGTHSCALE_LOWER
    lengthscale = M1_LENGTHSCALE_LOWER + span * sigmoid
    expected = torch.distributions.Normal(
        M1_LENGTHSCALE_Z_LOC, M1_LENGTHSCALE_Z_SCALE
    ).log_prob(z) - torch.log(span * sigmoid * (1.0 - sigmoid))
    assert torch.allclose(prior.log_prob(lengthscale), expected, atol=1e-9, rtol=0.0)


def test_m1_component_has_the_exact_frozen_kernel_and_priors():
    component = build_m1_matern_component()
    assert isinstance(component, gpytorch.kernels.ScaleKernel)
    assert isinstance(component.base_kernel, gpytorch.kernels.MaternKernel)
    assert component.base_kernel.nu == M1_MATERN_NU
    constraint = component.base_kernel.raw_lengthscale_constraint
    assert constraint.lower_bound.item() == M1_LENGTHSCALE_LOWER
    assert constraint.upper_bound.item() == M1_LENGTHSCALE_UPPER
    assert isinstance(component.base_kernel.lengthscale_prior, LogitNormalPrior)
    assert isinstance(component.outputscale_prior, gpytorch.priors.LogNormalPrior)
    assert component.outputscale_prior.loc.item() == math.log(M1_OUTPUTSCALE_MEDIAN)
    assert component.outputscale_prior.scale.item() == M1_OUTPUTSCALE_SIGMA
    assert component.raw_outputscale.dtype == torch.float64


def test_e1_short_scale_transform_target_round_trip(m1_e1):
    _x, _y, _model, _likelihood, e1 = m1_e1
    theta = e1.constrain(e1.init_params)
    recovered = e1.constrain(e1.unconstrain(theta))
    short_sites = [site for site in e1.sites if "kernels.3." in site]
    assert len(short_sites) == 2
    for site in short_sites:
        assert torch.allclose(recovered[site], theta[site], atol=1e-9, rtol=0.0)


def test_exact_nine_site_inventory_and_m0_delta(m1_e1):
    x, y, _model, _likelihood, e1 = m1_e1
    assert len(e1.sites) == 9
    assert sum("noise_covar.noise" in site for site in e1.sites) == 1
    short_sites = [site for site in e1.sites if "kernels.3." in site]
    assert len(short_sites) == 2
    assert any("lengthscale" in site for site in short_sites)
    assert any("outputscale" in site for site in short_sites)
    assert not any("period" in site for site in e1.sites)

    kernels, names = build_mauna_loa_kernels()
    m0_model, m0_likelihood = build_model(x, y, kernels, names)
    m0_e1 = build_e1_potential(m0_model, m0_likelihood, x, y)
    assert len(m0_e1.sites) == 7
    assert len(e1.sites) - len(m0_e1.sites) == 2


def test_augment_is_non_mutating_and_preserves_seasonal_a10_stamp():
    original_kernels, original_names = build_mauna_loa_kernels()
    original_seasonal = original_kernels[1]
    augmented_kernels, augmented_names = augment_with_m1_short_scale(
        original_kernels, original_names
    )

    assert len(original_kernels) == 3
    assert len(original_names) == 3
    assert len(augmented_kernels) == 4
    assert augmented_names == original_names + [M1_SHORT_SCALE_NAME]
    assert augmented_kernels is not original_kernels
    assert augmented_names is not original_names
    assert augmented_kernels[1] is original_seasonal

    seasonal = augmented_kernels[1].base_kernel
    assert seasonal.period_length.item() == MAUNA_FROZEN_PERIOD
    assert not seasonal.raw_period_length.requires_grad
    assert seasonal._a10_frozen_period == MAUNA_FROZEN_PERIOD


def test_augment_fails_closed_on_a_malformed_m0_inventory():
    kernels, names = build_mauna_loa_kernels()
    # length mismatch
    with pytest.raises(ValueError, match="length mismatch"):
        augment_with_m1_short_scale(kernels, names[:-1])
    # empty inventory
    with pytest.raises(ValueError, match="empty"):
        augment_with_m1_short_scale([], [])
    # non-string / empty name
    with pytest.raises(ValueError, match="non-empty strings"):
        augment_with_m1_short_scale(kernels, ["trend", "seasonal", ""])
    # duplicate names
    with pytest.raises(ValueError, match="duplicate"):
        augment_with_m1_short_scale(kernels, ["trend", "trend", "medium_term"])
    # already-augmented (existing short_scale) — refuse to double-augment
    augmented_kernels, augmented_names = augment_with_m1_short_scale(kernels, names)
    with pytest.raises(ValueError, match="already present"):
        augment_with_m1_short_scale(augmented_kernels, augmented_names)
