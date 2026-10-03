"""
FIX-2 (2026-09 review): law-of-total-variance decomposition moments, joint
group posteriors, and exact mixture central intervals.

Pins: identical hyperparameter draws keep positive conditional variance and
nonzero off-diagonal covariance; a two-draw fixture satisfies
std^2 = E_d[var_d] + Var_d[mean_d] against a direct per-draw computation;
the group of every component reproduces the full posterior in mean, total
variance, and mixture quantiles, and differs from the independence sum on
an anticorrelated pair; a singleton group is its component; an empty group
is zero; group key order is irrelevant; an unrequested group raises; the
mixture interval helper has the stated CDF coverage; the MAP path keeps its
values; the DecompositionResult positional contract is unchanged.
"""

import dataclasses

import numpy as np
import pytest

torch = pytest.importorskip("torch")
gpytorch = pytest.importorskip("gpytorch")

from gpytorch.constraints import Positive
from gpytorch.kernels import LinearKernel, RBFKernel, ScaleKernel
from gpytorch.priors import GammaPrior
from scipy.special import ndtr

from bistar_gp.debias import (
    ComponentResult, DecompositionResult, decompose_model, decompose_model_hmc,
)
from bistar_gp.decompose import (
    compute_cholesky, decompose_additive_gp, decompose_component,
    mixture_central_interval,
)
from bistar_gp.model import build_model, build_toy_kernels

torch.set_default_dtype(torch.float64)

SITES = {
    "ls": "covar_module.kernels.0.base_kernel.lengthscale_prior",
    "os": "covar_module.kernels.0.outputscale_prior",
    "lv": "covar_module.kernels.1.variance_prior",
    "noise": "likelihood.noise_covar.noise_prior",
}


def _samples(ls, os_, lv, noise):
    return {SITES["ls"]: np.asarray(ls, float), SITES["os"]: np.asarray(os_, float),
            SITES["lv"]: np.asarray(lv, float), SITES["noise"]: np.asarray(noise, float)}


@pytest.fixture
def toy():
    x = torch.linspace(-6, 6, 14)
    y = torch.sin(x) + 0.25 * x
    kers, names = build_toy_kernels()
    model, lik = build_model(x, y, kers, names)
    x_test = torch.linspace(-7, 7, 11)
    return model, lik, x, y, x_test


def _direct_draw(x, y, x_test, ls, os_, lv, noise, jitter=1e-4):
    """Per-draw conditional moments computed independently of debias.py."""
    kers, names = build_toy_kernels()
    model, lik = build_model(x, y, kers, names)
    model.kernel_components[0].base_kernel.lengthscale = ls
    model.kernel_components[0].outputscale = os_
    model.kernel_components[1].variance = lv
    lik.noise = noise
    model.eval(); lik.eval()
    km = model.get_component_kernel_matrices(x, x_test)
    with torch.no_grad():
        per = decompose_additive_gp([km[n]["XX"] for n in names], [km[n]["XstarX"] for n in names],
                                    [km[n]["XstarXstar"] for n in names], [km[n]["XXstar"] for n in names],
                                    noise, y, jitter)
        L = compute_cholesky(sum(km[n]["XX"] for n in names), noise, jitter)
        fm, fc = decompose_component(sum(km[n]["XstarX"] for n in names),
                                     sum(km[n]["XstarXstar"] for n in names),
                                     sum(km[n]["XXstar"] for n in names), L, y)
    return {n: (m.numpy(), c.numpy()) for (m, c), n in zip(per, names)}, (fm.numpy(), fc.numpy())


def test_identical_draws_keep_conditional_variance(toy):
    model, lik, x, y, x_test = toy
    samples = _samples([1.0] * 3, [1.0] * 3, [0.05] * 3, [0.1] * 3)
    res = decompose_model_hmc(model, lik, x, y, x_test, samples, kernel_builder=build_toy_kernels,
                              n_posterior_samples=3, rng=np.random.default_rng(0))
    for comp in res.components.values():
        assert np.all(comp.std > 0)
        assert np.max(np.abs(comp.cov - np.diag(np.diag(comp.cov)))) > 0
        assert np.allclose(comp.between_var, 0.0, atol=1e-14)
        assert np.allclose(comp.std ** 2, comp.within_var_mean)
        assert comp.samples_kind == "conditional_means" and comp.n_draws == 3
    assert np.all(res.full_std > 0)


def test_two_draw_total_variance_identity_against_direct_computation(toy):
    model, lik, x, y, x_test = toy
    draws = [(0.7, 1.5, 0.05, 0.1), (3.0, 0.4, 0.2, 0.3)]
    samples = _samples(*zip(*draws))
    res = decompose_model_hmc(model, lik, x, y, x_test, samples, kernel_builder=build_toy_kernels,
                              n_posterior_samples=2, rng=np.random.default_rng(0))
    direct = [_direct_draw(x, y, x_test, *d) for d in draws]
    order = res.n_draws_retained
    assert order == 2
    for name, comp in res.components.items():
        means = np.stack(sorted([d[0][name][0] for d in direct], key=lambda a: a[0]))
        got = np.stack(sorted(list(comp.conditional_means), key=lambda a: a[0]))
        assert np.allclose(got, means)
        vars_ = np.stack(sorted([np.diag(d[0][name][1]) for d in direct], key=lambda a: a[0]))
        gotv = np.stack(sorted(list(comp.conditional_vars), key=lambda a: a[0]))
        assert np.allclose(gotv, vars_)
        assert np.allclose(comp.std ** 2, comp.within_var_mean + comp.between_var)
        assert np.allclose(comp.within_var_mean, vars_.mean(0))
        assert np.allclose(comp.between_var, means.var(0))
        assert np.allclose(np.diag(comp.cov), comp.std ** 2)
    full_means = np.stack([d[1][0] for d in direct])
    full_vars = np.stack([np.diag(d[1][1]) for d in direct])
    assert np.allclose(res.full_mean, full_means.mean(0))
    assert np.allclose(res.full_std ** 2, full_vars.mean(0) + full_means.var(0))


def test_all_components_group_is_the_full_posterior_and_not_the_independence_sum(toy):
    model, lik, x, y, x_test = toy
    samples = _samples([0.7, 3.0], [1.5, 0.4], [0.05, 0.2], [0.1, 0.3])
    names = list(model.component_names)
    res = decompose_model_hmc(model, lik, x, y, x_test, samples, kernel_builder=build_toy_kernels,
                              n_posterior_samples=2, groups=[names], rng=np.random.default_rng(0))
    g = res.group(names)
    assert g is res.full
    assert np.allclose(g.mean, sum(res.components[n].mean for n in names))
    lo_g, hi_g = g.central_interval(0.95)
    lo_f, hi_f = res.full.central_interval(0.95)
    assert np.allclose(lo_g, lo_f) and np.allclose(hi_g, hi_f)
    # means add across the decomposition per draw
    summed = sum(res.components[n].conditional_means for n in names)
    assert np.allclose(summed, res.full.conditional_means)
    # the independence sum of component variances is NOT the full variance
    indep = np.sqrt(sum(res.components[n].std ** 2 for n in names))
    assert not np.allclose(indep, res.full_std, rtol=1e-3)
    cross = 0.5 * (res.full_std ** 2 - sum(res.components[n].std ** 2 for n in names))
    assert np.any(cross < 0)   # SE and linear components are anticorrelated here


def test_singleton_empty_and_unordered_groups(toy):
    model, lik, x, y, x_test = toy
    samples = _samples([0.7, 3.0], [1.5, 0.4], [0.05, 0.2], [0.1, 0.3])
    names = list(model.component_names)
    res = decompose_model_hmc(model, lik, x, y, x_test, samples, kernel_builder=build_toy_kernels,
                              n_posterior_samples=2, rng=np.random.default_rng(0))
    assert res.group([names[0]]) is res.components[names[0]]
    empty = res.group([])
    assert np.allclose(empty.mean, 0) and np.allclose(empty.std, 0)
    assert res.group(list(reversed(names))) is res.full


def _three_component_builder():
    a = ScaleKernel(RBFKernel(lengthscale_constraint=Positive(), lengthscale_prior=GammaPrior(2, 2)),
                    outputscale_constraint=Positive(), outputscale_prior=GammaPrior(6, 0.85))
    b = LinearKernel(variance_constraint=Positive(), variance_prior=GammaPrior(6, 0.85))
    c = ScaleKernel(RBFKernel(lengthscale_constraint=Positive(), lengthscale_prior=GammaPrior(2, 2)),
                    outputscale_constraint=Positive(), outputscale_prior=GammaPrior(6, 0.85))
    return [a, b, c], ["a", "b", "c"]


def test_requested_pair_group_matches_direct_conditioning_and_unrequested_raises():
    x = torch.linspace(-6, 6, 14)
    y = torch.sin(x) + 0.25 * x
    kers, names = _three_component_builder()
    model, lik = build_model(x, y, kers, names)
    x_test = torch.linspace(-7, 7, 9)
    samples = {
        "covar_module.kernels.0.base_kernel.lengthscale_prior": np.array([0.7, 2.0]),
        "covar_module.kernels.0.outputscale_prior": np.array([1.5, 0.5]),
        "covar_module.kernels.1.variance_prior": np.array([0.05, 0.2]),
        "covar_module.kernels.2.base_kernel.lengthscale_prior": np.array([4.0, 6.0]),
        "covar_module.kernels.2.outputscale_prior": np.array([0.3, 0.6]),
        "likelihood.noise_covar.noise_prior": np.array([0.1, 0.2]),
    }
    res = decompose_model_hmc(model, lik, x, y, x_test, samples, kernel_builder=_three_component_builder,
                              n_posterior_samples=2, groups=[["a", "b"]], rng=np.random.default_rng(0))
    g = res.group(["b", "a"])
    # direct conditioning of the summed a+b blocks with the FULL training factor
    means, vars_ = [], []
    for i in range(2):
        kers_i, names_i = _three_component_builder()
        m_i, l_i = build_model(x, y, kers_i, names_i)
        m_i.kernel_components[0].base_kernel.lengthscale = samples["covar_module.kernels.0.base_kernel.lengthscale_prior"][i]
        m_i.kernel_components[0].outputscale = samples["covar_module.kernels.0.outputscale_prior"][i]
        m_i.kernel_components[1].variance = samples["covar_module.kernels.1.variance_prior"][i]
        m_i.kernel_components[2].base_kernel.lengthscale = samples["covar_module.kernels.2.base_kernel.lengthscale_prior"][i]
        m_i.kernel_components[2].outputscale = samples["covar_module.kernels.2.outputscale_prior"][i]
        l_i.noise = samples["likelihood.noise_covar.noise_prior"][i]
        m_i.eval(); l_i.eval()
        km = m_i.get_component_kernel_matrices(x, x_test)
        with torch.no_grad():
            L = compute_cholesky(sum(km[n]["XX"] for n in names_i), float(l_i.noise), 1e-4)
            mg, cg = decompose_component(km["a"]["XstarX"] + km["b"]["XstarX"],
                                         km["a"]["XstarXstar"] + km["b"]["XstarXstar"],
                                         km["a"]["XXstar"] + km["b"]["XXstar"], L, y)
        means.append(mg.numpy()); vars_.append(np.diag(cg.numpy()))
    means, vars_ = np.stack(means), np.stack(vars_)
    assert np.allclose(np.sort(g.conditional_means, axis=0), np.sort(means, axis=0))
    assert np.allclose(g.std ** 2, vars_.mean(0) + means.var(0))
    with pytest.raises(KeyError, match="not requested"):
        res.group(["a", "c"])


def test_mixture_interval_helper_coverage():
    lo, hi = mixture_central_interval(np.array([[0.0]]), np.array([[4.0]]), mass=0.95)
    assert lo[0] == pytest.approx(-2 * 1.959964, abs=1e-5)
    assert hi[0] == pytest.approx(2 * 1.959964, abs=1e-5)
    means = np.array([[0.0], [0.0], [5.0]])
    vars_ = np.array([[1.0], [1.0], [0.25]])
    lo, hi = mixture_central_interval(means, vars_, mass=0.9)
    cdf = lambda t: ndtr((t - means[:, 0]) / np.sqrt(vars_[:, 0])).mean()
    assert cdf(lo[0]) == pytest.approx(0.05, abs=1e-8)
    assert cdf(hi[0]) == pytest.approx(0.95, abs=1e-8)
    with pytest.raises(ValueError):
        mixture_central_interval(np.zeros((2, 3)), np.ones((2, 2)))


def test_map_path_values_and_moments(toy):
    model, lik, x, y, x_test = toy
    res = decompose_model(model, lik, x, y, x_test, n_samples=4)
    for comp in res.components.values():
        assert np.allclose(comp.std, np.sqrt(np.clip(np.diag(comp.cov), 1e-10, None)))
        assert comp.samples_kind == "function_draws" and comp.samples.shape == (4, len(x_test))
        lo, hi = comp.central_interval(0.95)
        assert np.all(lo < comp.mean) and np.all(hi > comp.mean)
    assert res.full is not None and np.allclose(res.full.std, res.full_std)


def test_rebuild_contract_unchanged():
    names = [f.name for f in dataclasses.fields(DecompositionResult)]
    assert names == ["x_test", "x_train", "y_train", "components",
                     "full_mean", "full_std", "noise_var"]
    comp = ComponentResult(name="c", mean=np.zeros(3), std=np.ones(3), cov=np.eye(3),
                           samples=np.zeros((2, 3)))
    res = DecompositionResult(np.zeros(3), np.zeros(2), np.zeros(2), {"c": comp},
                              np.zeros(3), np.ones(3), 0.1)
    assert res.groups == {} and res.full is None
    with pytest.raises(ValueError, match="no per-draw"):
        comp.central_interval()


def test_map_groups_condition_on_the_full_factor():
    """FIX-2d: decompose_model(groups=...) conditions the summed group blocks
    with the Cholesky factor of the ENTIRE training covariance."""
    x = torch.linspace(-6, 6, 14)
    y = torch.sin(x) + 0.25 * x
    kers = [ScaleKernel(RBFKernel()), LinearKernel(), ScaleKernel(RBFKernel())]
    names = ["a", "b", "c"]
    model, lik = build_model(x, y, kers, names)
    x_test = torch.linspace(-7, 7, 11)
    res = decompose_model(model, lik, x, y, x_test, n_samples=3, groups=[["b", "a"]])
    g = res.group(["a", "b"])
    assert g is res.group(["b", "a"]) and g.name == "a+b" and g.n_draws == 1
    assert np.allclose(g.mean, res.components["a"].mean + res.components["b"].mean, atol=1e-10)
    model.eval(); lik.eval()
    km = model.get_component_kernel_matrices(x, x_test)
    with torch.no_grad():
        L = compute_cholesky(sum(km[n]["XX"] for n in names), lik.noise.item(), 1e-4)
        m, c = decompose_component(km["a"]["XstarX"] + km["b"]["XstarX"],
                                   km["a"]["XstarXstar"] + km["b"]["XstarXstar"],
                                   km["a"]["XXstar"] + km["b"]["XXstar"], L, y)
    assert np.allclose(g.mean, m.numpy(), atol=1e-10)
    assert np.allclose(g.cov, c.numpy(), atol=1e-10)
    assert np.allclose(g.std ** 2, np.clip(np.diag(c.numpy()), 1e-10, None), atol=1e-12)
    lo, hi = g.central_interval(0.95)
    assert np.allclose(hi - lo, 2 * 1.959963984540054 * g.std, atol=1e-6)
    indep = res.components["a"].std ** 2 + res.components["b"].std ** 2
    assert not np.allclose(g.std ** 2, indep, rtol=1e-3)
    assert res.group(["a", "b", "c"]) is res.full
    assert res.group(["a"]) is res.components["a"]
    assert np.all(res.group([]).mean == 0.0)
    with pytest.raises(KeyError, match="not requested"):
        res.group(["a", "c"])
    with pytest.raises(KeyError, match="unknown"):
        decompose_model(model, lik, x, y, x_test, groups=[["a", "zzz"]])


def test_mauna_script_compute_debiased_uses_groups():
    """FIX-2d: the script helper reads joint groups and refuses independence sums."""
    pss = pytest.importorskip("experiments.bistar_debias_mauna_loa")
    x = torch.linspace(-6, 6, 14)
    y = torch.sin(x) + 0.25 * x
    kers = [ScaleKernel(RBFKernel()), LinearKernel(), ScaleKernel(RBFKernel())]
    model, lik = build_model(x, y, kers, ["trend", "seasonal", "medium_term"])
    x_test = torch.linspace(-7, 7, 11)
    res = decompose_model(model, lik, x, y, x_test, n_samples=2, groups=pss.INTERPRETATION_GROUPS)
    for interp in pss.INTERPRETATIONS.values():
        out = pss.compute_debiased(res, interp["truth"], interp["bias"])
        truth, bias = res.group(interp["truth"]), res.group(interp["bias"])
        assert np.array_equal(out["truth_mean"], truth.mean) and np.array_equal(out["truth_std"], truth.std)
        assert np.array_equal(out["bias_mean"], bias.mean) and np.array_equal(out["bias_std"], bias.std)
        assert np.all(out["truth_lo"] <= out["truth_mean"]) and np.all(out["truth_hi"] >= out["truth_mean"])
        assert np.allclose(out["truth_mean"] + out["bias_mean"], res.full_mean, atol=1e-10)
    bare = decompose_model(model, lik, x, y, x_test, n_samples=2)
    with pytest.raises(KeyError, match="INTERPRETATION_GROUPS"):
        pss.compute_debiased(bare, ["trend", "seasonal"], ["medium_term"])
