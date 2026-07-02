"""
Regression tests for HMC sample-site naming across code eras.

The model.py single-registration fix renamed every kernel latent from
"kernel_components.{i}.*" to "covar_module.kernels.{i}.*", and the fit_hmc fix
moved the noise latent from "noise_covar.noise_prior" to
"likelihood.noise_covar.noise_prior". Consumers that hand-parsed the old names
(extract_gp_predictives, decompose_model_hmc, average-GP aggregation, the
mechanism hp_patterns) silently dropped every kernel hyperparameter draw and
evaluated GP predictives at default initialization values. All naming logic
now goes through bistar_gp.model.select_hmc_sites / apply_hp_value, tested
here against the three archive eras found on disk.
"""

import numpy as np
import pytest

torch = pytest.importorskip("torch")
gpytorch = pytest.importorskip("gpytorch")

from bistar_gp.model import (
    apply_hp_value,
    build_likelihood,
    build_model,
    build_toy_kernels,
    select_hmc_sites,
)

torch.set_default_dtype(torch.float64)

# Era A — archives written by the current code (single registration).
CURRENT_KEYS = [
    "covar_module.kernels.0.base_kernel.lengthscale_prior",
    "covar_module.kernels.0.outputscale_prior",
    "covar_module.kernels.1.variance_prior",
    "likelihood.noise_covar.noise_prior",
]

# Era B — archives from the double-registration era (e.g. bistar_gp/cache/*.npz,
# runs/*/samples/hmc_samples.npz): duplicate kernel sites where the
# kernel_components.* copies are disconnected prior draws, plus two noise sites
# where the bare one was sampled last and is the connected latent.
LEGACY_KEYS = [
    "covar_module.kernels.0.base_kernel.lengthscale_prior",
    "covar_module.kernels.0.outputscale_prior",
    "covar_module.kernels.1.variance_prior",
    "kernel_components.0.base_kernel.lengthscale_prior",
    "kernel_components.0.outputscale_prior",
    "kernel_components.1.variance_prior",
    "likelihood.noise_covar.noise_prior",
    "noise_covar.noise_prior",
]


@pytest.fixture
def toy_model():
    x = torch.linspace(0, 6, 30)
    y = torch.sin(x) + 0.25 * x
    kers, names = build_toy_kernels()
    model, lik = build_model(x, y, kers, names)
    return model, lik, x, y


def test_select_sites_current_archive():
    sites = select_hmc_sites(CURRENT_KEYS)
    assert sorted(sites) == sorted(CURRENT_KEYS)


def test_select_sites_legacy_archive():
    """From a duplicate-era archive, pick exactly the connected latents."""
    sites = select_hmc_sites(LEGACY_KEYS)
    assert sorted(sites) == sorted([
        "covar_module.kernels.0.base_kernel.lengthscale_prior",
        "covar_module.kernels.0.outputscale_prior",
        "covar_module.kernels.1.variance_prior",
        "noise_covar.noise_prior",
    ])


def test_select_sites_covers_every_hyperparameter(toy_model):
    """Whatever the model emits, selection must keep one site per prior."""
    model, lik, x, y = toy_model
    emitted = [name for name, *_ in model.named_priors()]
    sites = select_hmc_sites(emitted)
    assert len(sites) == len(emitted), (emitted, sites)


@pytest.mark.parametrize("prefix", ["covar_module.kernels.", "kernel_components."])
def test_apply_hp_value_sets_kernel_hyperparameters(toy_model, prefix):
    model, lik, x, y = toy_model
    assert apply_hp_value(model, lik, f"{prefix}0.base_kernel.lengthscale_prior", 2.5)
    assert apply_hp_value(model, lik, f"{prefix}0.outputscale_prior", 1.75)
    assert apply_hp_value(model, lik, f"{prefix}1.variance_prior", 0.6)
    assert model.kernel_components[0].base_kernel.lengthscale.item() == pytest.approx(2.5)
    assert model.kernel_components[0].outputscale.item() == pytest.approx(1.75)
    assert model.kernel_components[1].variance.item() == pytest.approx(0.6)


@pytest.mark.parametrize("name", ["likelihood.noise_covar.noise_prior",
                                  "noise_covar.noise_prior"])
def test_apply_hp_value_sets_noise(toy_model, name):
    model, lik, x, y = toy_model
    assert apply_hp_value(model, lik, name, 0.42)
    assert lik.noise.item() == pytest.approx(0.42)


def test_apply_hp_value_rejects_unknown_sites(toy_model):
    model, lik, x, y = toy_model
    assert not apply_hp_value(model, lik, "mean_module.constant_prior", 1.0)


def test_extract_gp_predictives_uses_kernel_posterior_draws(toy_model):
    """The predictive must move with the kernel draws, not just the noise.

    Before the fix, only the noise key survived the site filter, so every
    GPPosteriorSample was built at default kernel hyperparameters and all
    BMS* scoring ran against non-posterior GP draws.
    """
    from bistar_gp.bms_star import extract_gp_predictives

    model, lik, x, y = toy_model
    x_eval = torch.linspace(0, 6, 15)
    # Two synthetic draws with very different kernel hyperparameters.
    samples = {
        "covar_module.kernels.0.base_kernel.lengthscale_prior": np.array([0.3, 5.0]),
        "covar_module.kernels.0.outputscale_prior": np.array([2.0, 0.1]),
        "covar_module.kernels.1.variance_prior": np.array([0.5, 0.5]),
        "likelihood.noise_covar.noise_prior": np.array([0.1, 0.1]),
    }
    draws = extract_gp_predictives(model, lik, x, y, x_eval, samples,
                                   kernel_builder=build_toy_kernels,
                                   n_posterior_samples=2)
    assert len(draws) == 2
    for d in draws:
        kernel_keys = [k for k in d.hyperparameters if "kernels" in k]
        assert len(kernel_keys) == 3, sorted(d.hyperparameters)
    applied = sorted(
        d.hyperparameters["covar_module.kernels.0.base_kernel.lengthscale_prior"]
        for d in draws
    )
    assert applied == pytest.approx([0.3, 5.0])
    assert not np.allclose(draws[0].mean, draws[1].mean)


def test_find_hp_key_matches_current_and_legacy_names():
    from bistar_gp.mechanism import find_hp_key

    pattern = "covar_module.kernels.0.base_kernel.lengthscale"
    current = {k: 1.0 for k in CURRENT_KEYS}
    legacy_only = {k: 1.0 for k in LEGACY_KEYS if not k.startswith("covar_module")}
    assert find_hp_key(current, pattern) == \
        "covar_module.kernels.0.base_kernel.lengthscale_prior"
    assert find_hp_key(legacy_only, pattern) == \
        "kernel_components.0.base_kernel.lengthscale_prior"
    # The bare-index pattern used for the toy linear channel.
    assert find_hp_key(current, "covar_module.kernels.1") == \
        "covar_module.kernels.1.variance_prior"


def test_mechanism_channels_resolve_against_current_naming(toy_model):
    """Every toy channel pattern must find a key in a current-era hp dict."""
    from bistar_gp.mechanism import find_hp_key, toy_mechanism_config

    hp_dict = {k: 1.0 for k in CURRENT_KEYS}
    for channel in toy_mechanism_config().channels:
        assert find_hp_key(hp_dict, channel.hp_pattern) is not None, channel.hp_pattern
