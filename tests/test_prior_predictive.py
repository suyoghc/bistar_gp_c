"""
Prior/posterior predictive sampling: sample_prior + extract_gp_predictives'
condition_on_data flag, the two building blocks for prior/posterior predictive
checks. Both share the fit_hmc dict schema and the same predictive pipeline.
"""

import numpy as np
import pytest

torch = pytest.importorskip("torch")
gpytorch = pytest.importorskip("gpytorch")
pytest.importorskip("pyro")

from bistar_gp.model import build_toy_kernels, build_model, select_hmc_sites
from bistar_gp.fit import sample_prior
from bistar_gp.bms_star import extract_gp_predictives

torch.set_default_dtype(torch.float64)

LS = "covar_module.kernels.0.base_kernel.lengthscale_prior"
OS = "covar_module.kernels.0.outputscale_prior"
VAR = "covar_module.kernels.1.variance_prior"
NOISE = "likelihood.noise_covar.noise_prior"


@pytest.fixture
def toy():
    x = torch.linspace(0, 6, 20)
    y = torch.sin(x) + 0.25 * x
    kers, names = build_toy_kernels()
    model, lik = build_model(x, y, kers, names)
    return model, lik, x, y


def test_sample_prior_matches_fit_hmc_schema(toy):
    model, lik, x, y = toy
    pri = sample_prior(model, n_samples=200, seed=0)
    assert set(pri) == {LS, OS, VAR, NOISE}
    for v in pri.values():
        assert v.shape == (200,)
    # flows through the same site selector fit_hmc output does
    assert set(select_hmc_sites(pri.keys())) == {LS, OS, VAR, NOISE}


def test_sample_prior_is_iid_and_reproducible(toy):
    model, lik, x, y = toy
    a = sample_prior(model, n_samples=150, seed=7)
    b = sample_prior(model, n_samples=150, seed=7)
    for k in a:
        assert np.array_equal(a[k], b[k])          # seed → reproducible
    assert a[LS].std() > 0.1                        # a real spread, not a point
    # i.i.d. draws: no autocorrelation structure imposed (lag-1 corr ~ 0)
    ls = a[LS]
    lag1 = np.corrcoef(ls[:-1], ls[1:])[0, 1]
    assert abs(lag1) < 0.25


def test_sample_prior_is_data_free(toy):
    """Prior draws depend only on the priors, not the model's train targets."""
    model, lik, x, y = toy
    kers, names = build_toy_kernels()
    model2, _ = build_model(x, 10.0 + 0.0 * y, kers, names)   # very different y
    a = sample_prior(model, n_samples=100, seed=3)
    b = sample_prior(model2, n_samples=100, seed=3)
    for k in a:
        assert np.array_equal(a[k], b[k])


def _one_sample():
    return {LS: np.array([1.0]), OS: np.array([1.0]),
            VAR: np.array([0.3]), NOISE: np.array([0.1])}


def test_prior_predictive_is_zero_mean_and_data_free(toy):
    model, lik, x, y = toy
    x_eval = torch.linspace(0, 6, 12)
    s = _one_sample()
    pri = extract_gp_predictives(model, lik, x, y, x_eval, s, build_toy_kernels,
                                 n_posterior_samples=1, condition_on_data=False)
    assert len(pri) == 1
    # ZeroMean GP prior → prior predictive mean is exactly zero
    assert np.allclose(pri[0].mean, 0.0, atol=1e-9)
    # independent of the training targets
    pri2 = extract_gp_predictives(model, lik, x, 5.0 + 0.0 * y, x_eval, s,
                                  build_toy_kernels, n_posterior_samples=1,
                                  condition_on_data=False)
    assert np.allclose(pri[0].mean, pri2[0].mean)
    assert np.allclose(pri[0].cov, pri2[0].cov)
    # Analytic prior predictive diagonal for the toy SE+Linear kernel at these
    # fixed hyperparameters: RBF k(x,x)=outputscale=1, Linear k(x,x)=variance·x²
    # (=0.3·x²), plus noise=0.1.
    xe = x_eval.numpy()
    expected_diag = 1.0 + 0.3 * xe ** 2 + 0.1
    assert np.allclose(np.diag(pri[0].cov), expected_diag, atol=1e-6)


def test_posterior_predictive_depends_on_data(toy):
    model, lik, x, y = toy
    x_eval = torch.linspace(0, 6, 12)
    s = _one_sample()
    post = extract_gp_predictives(model, lik, x, y, x_eval, s, build_toy_kernels,
                                  n_posterior_samples=1, condition_on_data=True)
    post2 = extract_gp_predictives(model, lik, x, 3.0 + 0.0 * y, x_eval, s,
                                   build_toy_kernels, n_posterior_samples=1,
                                   condition_on_data=True)
    # posterior predictive mean tracks the data → changes with y
    assert not np.allclose(post[0].mean, post2[0].mean)
    # and it is not the zero prior mean
    assert np.abs(post[0].mean).max() > 1e-3


def test_posterior_predictive_is_tighter_than_prior(toy):
    """Structural invariant: the posterior predictive variance never exceeds the
    prior predictive variance (a Schur-complement property, holds for any PSD
    kernel). This is a sanity check on the two branches, NOT a data-dependence
    test — that is test_posterior_predictive_depends_on_data above."""
    model, lik, x, y = toy
    x_eval = torch.linspace(0, 6, 12)
    s = _one_sample()
    pri = extract_gp_predictives(model, lik, x, y, x_eval, s, build_toy_kernels,
                                 n_posterior_samples=1, condition_on_data=False)[0]
    post = extract_gp_predictives(model, lik, x, y, x_eval, s, build_toy_kernels,
                                  n_posterior_samples=1, condition_on_data=True)[0]
    assert np.all(np.diag(post.cov) <= np.diag(pri.cov) + 1e-9)
