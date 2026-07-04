"""
GP hyperparameter-inference options (fit_gp, DECISIONS D9) and the G-metric
identity (D10).

Every inference method must return the SAME dict schema as fit_hmc
(site name -> (n,) array of constrained values), so any option flows through
extract_gp_predictives / BMS* / decomposition unchanged. Defaults follow the
thesis chapter (full-Bayes sampling; VI was its primary implementation, HMC
the cross-check, MAP the explicit contrast).

The D10 identity: the viz scripts' "pointwise variance-weighted MSE" G is
numerically IDENTICAL to the package's default metric pw_kl_vcal — the
"single-G decision" was a naming difference, not a mathematical one.
"""

import importlib.util
from pathlib import Path

import numpy as np
import pytest

torch = pytest.importorskip("torch")
gpytorch = pytest.importorskip("gpytorch")
pytest.importorskip("pyro")

from bistar_gp.model import build_toy_kernels, build_model
from bistar_gp.fit import fit_gp, fit_map, GP_INFERENCE_METHODS

torch.set_default_dtype(torch.float64)

EXPECTED_SITES = {
    "covar_module.kernels.0.base_kernel.lengthscale_prior",
    "covar_module.kernels.0.outputscale_prior",
    "covar_module.kernels.1.variance_prior",
    "likelihood.noise_covar.noise_prior",
}

# cheap-but-real settings per method for the schema tests
FAST_KWARGS = {
    "hmc": dict(n_samples=2, n_warmup=2, verbose=False, seed=0, max_tree_depth=4),
    "vi": dict(n_samples=25, n_steps=50, verbose=False, seed=0),
    "map": dict(n_iter=50),
    "hmc_laplace": dict(n_samples=2, n_warmup=2, verbose=False, seed=0,
                        max_tree_depth=4),
}


@pytest.fixture
def toy():
    x = torch.linspace(0, 6, 12)
    y = torch.sin(x) + 0.25 * x
    kers, names = build_toy_kernels()
    model, lik = build_model(x, y, kers, names)
    fit_map(model, lik, x, y, n_iter=100, lr=0.05, verbose=False)
    return model, lik, x, y


@pytest.mark.parametrize("method", GP_INFERENCE_METHODS)
def test_fit_gp_returns_shared_schema(toy, method):
    """Every option: same site names, (n,) float arrays, finite, positive."""
    model, lik, x, y = toy
    s = fit_gp(model, lik, x, y, method=method, **FAST_KWARGS[method])
    assert set(s) == EXPECTED_SITES, (method, sorted(s))
    for k, v in s.items():
        assert isinstance(v, np.ndarray) and v.ndim == 1, (method, k, v)
        assert np.isfinite(v).all(), (method, k)
        assert (v > 0).all(), (method, k)   # constrained space, positive supports


def test_fit_gp_map_is_point_estimate(toy):
    model, lik, x, y = toy
    s = fit_gp(model, lik, x, y, method="map", n_iter=50)
    assert all(v.shape == (1,) for v in s.values())
    # and it equals the model's current (MAP-fitted) hyperparameters
    assert s["likelihood.noise_covar.noise_prior"][0] == pytest.approx(
        float(lik.noise), rel=1e-6)


def test_fit_gp_unknown_method_raises(toy):
    model, lik, x, y = toy
    with pytest.raises(ValueError, match="unknown method"):
        fit_gp(model, lik, x, y, method="nuts_but_wrong")


def test_vi_posterior_concentrates_relative_to_prior(toy):
    """VI must produce a data-informed posterior, not prior-width draws:
    the noise posterior sd from VI should be far below the Gamma(1.75,1)
    prior sd (~1.32) on this nearly-noiseless toy."""
    model, lik, x, y = toy
    s = fit_gp(model, lik, x, y, method="vi", n_samples=200, n_steps=400,
               verbose=False, seed=0)
    noise = s["likelihood.noise_covar.noise_prior"]
    assert noise.std() < 0.5, noise.std()
    assert noise.mean() < 0.5, noise.mean()   # prior mean is 1.75


def test_fit_gp_samples_flow_through_predictive_pipeline(toy):
    """Schema compatibility end-to-end: each method's output feeds
    extract_gp_predictives unchanged."""
    from bistar_gp.bms_star import extract_gp_predictives

    model, lik, x, y = toy
    x_eval = torch.linspace(0, 6, 8)
    for method in ("map", "vi"):
        s = fit_gp(model, lik, x, y, method=method, **FAST_KWARGS[method])
        draws = extract_gp_predictives(model, lik, x, y, x_eval, s,
                                       kernel_builder=build_toy_kernels,
                                       n_posterior_samples=5)
        assert len(draws) >= 1, method
        assert draws[0].mean.shape == (8,), method


# ── D10: the G-metric identity ─────────────────────────────────────

def _load_viz_module():
    path = (Path(__file__).resolve().parents[1] / "bistar_viz" / "scripts"
            / "model_priors_laplace.py")
    spec = importlib.util.spec_from_file_location("viz_mpl", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_viz_variance_weighted_mse_is_pw_kl_vcal():
    """The viz scripts' compute_G ("pointwise variance-weighted MSE") equals
    the package default metric pw_kl_vcal exactly (same formula:
    mean((mu_gp - mu_theta)^2 / (2 sigma^2_gp))) — the 'single-G decision'
    is a naming difference, not a mathematical fork."""
    import bistar_gp.metrics_v2  # noqa: F401 — registers pw_kl_vcal
    from bistar_gp.bms_star import METRICS

    viz = _load_viz_module()
    rng = np.random.default_rng(0)
    x_eval = np.linspace(-3, 3, 25)
    gp_mean = rng.normal(size=25)
    gp_var = rng.uniform(0.05, 2.0, size=25)      # above the viz 1e-6 floor

    params = {"a": 0.4, "b": -0.2}
    predict_fn = lambda x, p: p["a"] * x + p["b"]
    mu_theta = predict_fn(x_eval, params)

    g_viz = viz.compute_G(params, predict_fn, gp_mean, gp_var, x_eval)
    g_pkg = METRICS["pw_kl_vcal"](gp_mean, np.diag(gp_var),
                                  mu_theta, np.eye(25))
    assert g_viz == pytest.approx(g_pkg, rel=1e-12)
