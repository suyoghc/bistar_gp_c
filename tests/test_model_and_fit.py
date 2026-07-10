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


def test_hmc_target_registers_noise_prior_once(toy_model):
    """Trace the ACTUAL fit_hmc target, not just model.pyro_sample_from_prior.

    fit_hmc used to also call likelihood.pyro_sample_from_prior(), which added
    a second, disconnected noise latent ('noise_covar.noise_prior') on top of
    the one the model already emits ('likelihood.noise_covar.noise_prior') —
    5 sites for 4 hyperparameters, with the phantom site returning pure prior
    draws that downstream consumers could mistake for the posterior.
    """
    pyro = pytest.importorskip("pyro")
    from functools import partial
    from bistar_gp.fit import _hmc_pyro_model

    from pyro.poutine.util import site_is_subsample

    model, lik, x, y = toy_model
    model.train(); lik.train()
    trace = pyro.poutine.trace(partial(_hmc_pyro_model, model, x, y)).get_trace()
    latents = [n for n, s in trace.nodes.items()
               if s["type"] == "sample" and not s["is_observed"]
               and not site_is_subsample(s)]
    assert len(latents) == 4, latents
    noise_sites = [n for n in latents if "noise_covar.noise" in n]
    assert len(noise_sites) == 1, latents


def test_hmc_target_connects_latents_to_likelihood(toy_model):
    """The obs likelihood MUST depend on the sampled hyperparameters.

    gpytorch's model.pyro_sample_from_prior() returns a sampled COPY and leaves
    the original model unchanged; if fit_hmc scores the original model instead of
    the returned module, the obs log-prob is constant in the latents and NUTS
    samples the prior, not the posterior. A site-count check cannot catch this —
    only conditioning the latents and watching the obs log-prob move can.
    """
    pyro = pytest.importorskip("pyro")
    from functools import partial
    from bistar_gp.fit import _hmc_pyro_model

    model, lik, x, y = toy_model
    model.train(); lik.train()
    tr = pyro.poutine.trace(partial(_hmc_pyro_model, model, x, y)).get_trace()
    sites = [n for n, s in tr.nodes.items()
             if s["type"] == "sample" and not s["is_observed"] and n.endswith("_prior")]

    def obs_logprob(latents):
        t = pyro.poutine.trace(
            pyro.condition(partial(_hmc_pyro_model, model, x, y), data=latents)).get_trace()
        node = t.nodes["obs"]
        return float(node["fn"].log_prob(node["value"]).sum())

    lp_lo = obs_logprob({s: torch.tensor(0.5) for s in sites})
    lp_hi = obs_logprob({s: torch.tensor(2.5) for s in sites})
    assert abs(lp_lo - lp_hi) > 1.0, (lp_lo, lp_hi)   # obs must move with the latents


def test_fit_hmc_map_init_and_tree_cap_smoke(toy_model):
    """fit_hmc's stiff-posterior knobs (init_to_map, max_tree_depth) must run and
    return one finite array per hyperparameter site."""
    import numpy as np
    from bistar_gp.fit import fit_hmc

    model, lik, x, y = toy_model
    x, y = x[:12], y[:12]
    kers, names = build_toy_kernels()
    m, l = build_model(x, y, kers, names)
    s = fit_hmc(m, l, x, y, n_samples=2, n_warmup=2, verbose=False, seed=0,
                init_to_map=True, max_tree_depth=4)
    assert len(s) == 4, sorted(s)
    assert all(np.isfinite(v).all() for v in s.values())


def test_hmc_map_init_lands_at_model_values(toy_model):
    """The init_to_value strategy must initialize each latent at the model's CURRENT
    constrained hyperparameter value (what init_to_map=True promises for a
    MAP-fitted model) — not at a prior draw or a default.

    Verified through pyro's own initialize_model: the unconstrained initial params,
    mapped back through the returned transforms, must equal the values that
    fit_hmc's init dict is built from. Guards both the name matching (named_priors
    name == pyro site name on the deep-copied sampled module) and the
    constrained-vs-unconstrained space handling.
    """
    pyro = pytest.importorskip("pyro")
    from functools import partial
    from pyro.infer.autoguide.initialization import init_to_value
    from pyro.infer.mcmc.util import initialize_model
    from bistar_gp.fit import _hmc_pyro_model

    model, lik, x, y = toy_model
    # distinctive, non-default values (as if MAP-fitted)
    model.kernel_components[0].base_kernel.lengthscale = 2.5
    model.kernel_components[0].outputscale = 1.7
    model.kernel_components[1].variance = 0.6
    lik.noise = 0.31
    model.train(); lik.train()

    init_values = {entry[0]: entry[3](entry[1]).detach()
                   for entry in model.named_priors()}
    init_params, _, transforms, _ = initialize_model(
        partial(_hmc_pyro_model, model), model_args=(x, y),
        init_strategy=init_to_value(values=init_values))
    for site, unconstrained in init_params.items():
        constrained = transforms[site].inv(unconstrained)
        expected = init_values[site]
        assert torch.allclose(constrained.reshape(-1), expected.reshape(-1),
                              rtol=1e-6), (site, constrained, expected)


def test_hmc_map_init_survives_boundary_values(toy_model):
    """A constrained hyperparameter that underflowed to exactly 0 (boundary of a
    positive support) must not abort NUTS initialization. init_to_value maps the
    boundary to -inf in unconstrained space, and pyro retries the SAME fixed value
    until 'cannot find valid initial params' — fit_hmc clamps such values into the
    support interior instead (codex review finding, verified)."""
    import numpy as np
    from bistar_gp.fit import fit_hmc

    model, lik, x, y = toy_model
    x, y = x[:10], y[:10]
    kers, names = build_toy_kernels()
    m, l = build_model(x, y, kers, names)
    l.noise_covar.raw_noise.data.fill_(-1000.0)   # softplus(-1000) underflows to 0.0
    assert float(l.noise) == 0.0
    s = fit_hmc(m, l, x, y, n_samples=1, n_warmup=1, verbose=False, seed=0,
                init_to_map=True, max_tree_depth=4)
    assert all(np.isfinite(v).all() for v in s.values())


def test_mh_target_is_train_mode_log_joint(toy_model):
    """fit_mcmc_simple's target must be the marginal-likelihood log joint.

    The old code evaluated the target in eval mode, where model(train_x) is
    the posterior predictive conditioned on train_y itself — data used twice,
    biasing the chain toward small-noise/overfit hyperparameters. The helper
    must return the train-mode value even if the caller left eval mode on.
    """
    from bistar_gp.fit import _mh_log_joint

    model, lik, x, y = toy_model
    mll = gpytorch.mlls.ExactMarginalLogLikelihood(lik, model)
    model.train(); lik.train()
    with torch.no_grad():
        expected = (mll(model(x), y) * y.numel()).item()

    model.eval(); lik.eval()
    got = _mh_log_joint(mll, model, lik, x, y)
    assert got == pytest.approx(expected, rel=1e-9)


def test_mcmc_simple_samples_each_parameter_once(toy_model):
    """The likelihood is a submodule of ExactGP, so its raw noise used to enter
    the proposal twice under two names; after dedup exactly 4 dims remain."""
    from bistar_gp.fit import fit_mcmc_simple

    model, lik, x, y = toy_model
    samples = fit_mcmc_simple(model, lik, x, y, n_samples=3, n_burnin=1,
                              verbose=False, seed=0)
    assert len(samples) == 4, sorted(samples)
    assert sum("raw_noise" in k for k in samples) == 1, sorted(samples)


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
