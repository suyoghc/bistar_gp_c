"""
Regression tests for the modeling/fitting fixes (need gpytorch + pyro).

  - AdditiveGPModel must register each kernel prior exactly once, so HMC sees one
    latent site per hyperparameter (it previously double-registered via both an
    nn.ModuleList and covar_module, creating phantom duplicate latents).
  - fit_mcmc_simple relies on gpytorch's MLL being per-datum-averaged; the fix
    multiplies by n. This test pins that assumption: mll*n == the true summed
    log marginal likelihood, and mll alone does NOT.
  - decompose_model must report the true full posterior covariance (including
    inter-component cross terms), not the sum of component covariances.
"""

import numpy as np
import pytest

torch = pytest.importorskip("torch")
gpytorch = pytest.importorskip("gpytorch")

from bistar_gp.model import build_toy_kernels, build_model, AdditiveGPModel, build_likelihood
from bistar_gp.decompose import compute_cholesky, decompose_component

torch.set_default_dtype(torch.float64)


@pytest.fixture
def toy_model():
    x = torch.linspace(0, 6, 30)
    y = torch.sin(x) + 0.25 * x
    kers, names = build_toy_kernels()
    model, lik = build_model(x, y, kers, names)
    return model, lik, x, y


def test_each_prior_registered_once(toy_model):
    """Toy model has 4 hyperparameters: noise, SE outputscale, SE lengthscale, linear variance.

    The double-registration bug exposed each kernel prior under BOTH a
    kernel_components.* and a covar_module.* path, giving 7 entries; the fix
    leaves a single registration path, so exactly 4 unique priors remain.
    """
    model, lik, x, y = toy_model
    prior_names = [t[0] for t in model.named_priors()]
    assert len(prior_names) == 4, prior_names
    assert len(set(prior_names)) == 4, prior_names
    # The same kernel hyperparameter must not be reachable via two paths.
    assert not (any(n.startswith("kernel_components") for n in prior_names)
                and any(n.startswith("covar_module") for n in prior_names)), prior_names


def test_hmc_sees_one_latent_per_hyperparameter(toy_model):
    pyro = pytest.importorskip("pyro")
    model, lik, x, y = toy_model
    trace = pyro.poutine.trace(model.pyro_sample_from_prior).get_trace()
    sites = [n for n, s in trace.nodes.items() if s["type"] == "sample"]
    assert len(sites) == 4, sites
    assert len(set(sites)) == len(sites), "duplicate latent sites"


def test_mll_is_per_datum_and_fix_recovers_summed_log_joint(toy_model):
    """fit_mcmc_simple's fix (mll * n) must equal the true summed log joint.

    gpytorch's ExactMarginalLogLikelihood returns (log p(y|theta) + prior terms)
    divided by n. The fix multiplies by n; here we reconstruct the log joint
    independently and confirm mll*n recovers it while mll alone does not.
    """
    model, lik, x, y = toy_model
    model.train(); lik.train()
    n = y.numel()
    mll = gpytorch.mlls.ExactMarginalLogLikelihood(lik, model)
    with torch.no_grad():
        mll_val = mll(model(x), y).item()
        data_ll = lik(model(x)).log_prob(y).item()        # log p(y|theta), with noise
        prior_terms = 0.0
        for entry in model.named_priors():
            module, prior, closure = entry[1], entry[2], entry[3]
            prior_terms += float(prior.log_prob(closure(module)).sum())
        log_joint = data_ll + prior_terms
    assert mll_val * n == pytest.approx(log_joint, rel=1e-6)   # the fix is correct
    assert mll_val != pytest.approx(log_joint, rel=1e-3)        # the bug was real (off by n)


def test_decompose_full_cov_includes_cross_terms(toy_model):
    """full_cov must be the sum-kernel posterior cov, not the sum of component covs."""
    from bistar_gp.debias import decompose_model
    model, lik, x, y = toy_model
    x_test = torch.linspace(-1, 7, 20)
    res = decompose_model(model, lik, x, y, x_test, n_samples=5)

    # Independent ground truth: posterior cov of the summed kernel.
    km = model.get_component_kernel_matrices(x, x_test)
    names = model.component_names
    with torch.no_grad():
        K_sum_XX = sum(km[m]["XX"] for m in names)
        L = compute_cholesky(K_sum_XX, lik.noise.item(), 1e-4)
        _, full_cov = decompose_component(
            sum(km[m]["XstarX"] for m in names),
            sum(km[m]["XstarXstar"] for m in names),
            sum(km[m]["XXstar"] for m in names),
            L, y,
        )
    true_std = np.sqrt(np.clip(np.diag(full_cov.numpy()), 1e-10, None))
    assert np.allclose(res.full_std, true_std, atol=1e-6)

    # And it must differ from the (buggy) sum-of-component-covariances std.
    summed = sum(c.cov for c in res.components.values())
    buggy_std = np.sqrt(np.clip(np.diag(summed), 1e-10, None))
    assert not np.allclose(res.full_std, buggy_std, atol=1e-6)
