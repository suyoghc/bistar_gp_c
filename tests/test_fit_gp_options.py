"""
GP hyperparameter-inference options (fit_gp, DECISIONS D9) and the G-metric
identity (D10).

Available inference methods return the SAME dict schema as fit_hmc
(site name -> (n,) array of constrained values), so any option flows through
extract_gp_predictives / BMS* / decomposition unchanged. Under D27, public
HMC uses E1 while VI and HMC-Laplace require historical-reproduction opt-ins.

The D10 identity: the viz scripts' "pointwise variance-weighted MSE" G is
numerically IDENTICAL to the package's default metric pw_kl_vcal — the
"single-G decision" was a naming difference, not a mathematical one.
"""


from contextlib import nullcontext

import numpy as np
import pytest

torch = pytest.importorskip("torch")
gpytorch = pytest.importorskip("gpytorch")
pytest.importorskip("pyro")

from bistar_gp.model import build_toy_kernels, build_model
from bistar_gp.fit import (
    GP_INFERENCE_METHODS,
    fit_gp,
    fit_hmc_laplace,
    fit_hmc_legacy_pyro,
    fit_map,
    fit_vi,
)

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
def toy_data():
    x = torch.linspace(0, 6, 12)
    y = torch.sin(x) + 0.25 * x
    return x, y


@pytest.fixture
def toy(toy_data):
    x, y = toy_data
    kers, names = build_toy_kernels()
    model, lik = build_model(x, y, kers, names)
    fit_map(model, lik, x, y, n_iter=100, lr=0.05, verbose=False)
    return model, lik, x, y


@pytest.mark.parametrize("method", ("hmc", "map"))
def test_fit_gp_returns_shared_schema(toy, method):
    """Every available option returns finite constrained arrays."""
    model, lik, x, y = toy
    s = fit_gp(model, lik, x, y, method=method, **FAST_KWARGS[method])
    assert set(s) == EXPECTED_SITES, (method, sorted(s))
    for k, v in s.items():
        assert isinstance(v, np.ndarray) and v.ndim == 1, (method, k, v)
        assert np.isfinite(v).all(), (method, k)
        assert (v > 0).all(), (method, k)   # constrained space, positive supports


def test_method_names_remain_stable_under_d27():
    assert GP_INFERENCE_METHODS == ("hmc", "vi", "map", "hmc_laplace")


@pytest.mark.parametrize("method,match", [
    ("vi", r"D23"),
    ("hmc_laplace", r"D23.*D24"),
])
def test_unavailable_fit_gp_methods_raise_by_default(toy, method, match):
    model, lik, x, y = toy
    with pytest.raises(RuntimeError, match=match):
        fit_gp(model, lik, x, y, method=method)


def test_fit_gp_hmc_uses_e1_and_returns_diagnostics(toy):
    model, lik, x, y = toy
    samples, diagnostics = fit_gp(
        model, lik, x, y, method="hmc", n_samples=2, n_warmup=2,
        verbose=False, seed=0, max_tree_depth=4, return_diagnostics=True)
    assert set(samples) == EXPECTED_SITES
    assert diagnostics.sampler == "nuts_e1"


def test_legacy_pyro_hmc_warns_and_runs(toy):
    model, lik, x, y = toy
    with pytest.warns(UserWarning, match="LEGACY path"):
        samples = fit_hmc_legacy_pyro(
            model, lik, x, y, n_samples=1, n_warmup=1, verbose=False,
            seed=0, max_tree_depth=3)
    assert set(samples) == EXPECTED_SITES


def test_legacy_vi_and_laplace_opt_ins_warn_and_run(toy):
    model, lik, x, y = toy
    with pytest.warns(UserWarning, match="D23"):
        vi_samples = fit_vi(
            model, lik, x, y, n_samples=2, n_steps=1, verbose=False,
            seed=0, allow_legacy=True)
    assert set(vi_samples) == EXPECTED_SITES

    with pytest.warns(UserWarning, match="D23"):
        laplace_samples = fit_hmc_laplace(
            model, lik, x, y, n_samples=1, n_warmup=1, verbose=False,
            seed=0, max_tree_depth=3, allow_legacy=True)
    assert set(laplace_samples) == EXPECTED_SITES


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


def test_vi_learns_from_likelihood_not_just_init(toy_data):
    """VI must LEARN, not merely inherit its initialization (codex finding:
    a MAP-initialized guide passes a concentration check with n_steps=0).
    Start from a FRESH model (constructor defaults, noise ~0.693) so passing
    requires ELBO gradients to actually flow through gpytorch's
    setting_closure into the guide: with 0 steps the noise stays at init;
    with 400 steps it must drop toward the near-zero posterior."""
    x, y = toy_data
    NOISE = "likelihood.noise_covar.noise_prior"

    kers, names = build_toy_kernels()
    m0, l0 = build_model(x, y, kers, names)
    with pytest.warns(UserWarning, match="D23"):
        s0 = fit_vi(m0, l0, x, y, n_samples=100, n_steps=0,
                    verbose=False, seed=0, allow_legacy=True)
    assert s0[NOISE].mean() > 0.4, s0[NOISE].mean()   # init, unlearned

    kers, names = build_toy_kernels()
    m1, l1 = build_model(x, y, kers, names)
    with pytest.warns(UserWarning, match="D23"):
        s1 = fit_vi(m1, l1, x, y, n_samples=100, n_steps=400,
                    verbose=False, seed=0, allow_legacy=True)
    assert s1[NOISE].mean() < 0.2, s1[NOISE].mean()   # learned from data


@pytest.mark.parametrize("method,kw", [
    ("vi", dict(n_samples=5, n_steps=5, verbose=False, seed=0)),
    ("hmc_laplace", dict(n_samples=1, n_warmup=1, verbose=False, seed=0,
                         max_tree_depth=3)),
])
def test_boundary_underflow_survives_all_init_paths(toy_data, method, kw):
    """codex finding: the D8 boundary guard existed only in fit_hmc's inline
    init loop; a hyperparameter that underflowed to exactly 0 crashed the vi
    and hmc_laplace init paths. _map_init_values is now the single guarded
    authority — all MAP-init paths must survive a boundary value."""
    x, y = toy_data
    kers, names = build_toy_kernels()
    m, l = build_model(x, y, kers, names)
    l.noise_covar.raw_noise.data.fill_(-1000.0)   # softplus underflows to 0.0
    assert float(l.noise.detach()) == 0.0
    with pytest.warns(UserWarning, match="D23"):
        s = fit_gp(m, l, x, y, method=method, allow_legacy=True, **kw)
    assert all(np.isfinite(v).all() for v in s.values()), method


def test_hmc_single_sample_keeps_1d_schema(toy):
    """codex finding: fit_hmc's squeeze() returned 0-d arrays at n_samples=1,
    breaking the (n,) schema contract and crashing extract_gp_predictives."""
    from bistar_gp.bms_star import extract_gp_predictives

    model, lik, x, y = toy
    s = fit_gp(model, lik, x, y, method="hmc", n_samples=1, n_warmup=2,
               verbose=False, seed=0, max_tree_depth=4)
    assert all(v.shape == (1,) for v in s.values()), {k: v.shape for k, v in s.items()}
    draws = extract_gp_predictives(model, lik, x, y, torch.linspace(0, 6, 8), s,
                                   kernel_builder=build_toy_kernels,
                                   n_posterior_samples=1)
    assert len(draws) == 1


def test_fit_gp_samples_flow_through_predictive_pipeline(toy):
    """Schema compatibility end-to-end: each method's output feeds
    extract_gp_predictives unchanged."""
    from bistar_gp.bms_star import extract_gp_predictives

    model, lik, x, y = toy
    x_eval = torch.linspace(0, 6, 8)
    for method in ("map", "vi"):
        kw = dict(FAST_KWARGS[method])
        if method == "vi":
            kw["allow_legacy"] = True
        warning_context = (pytest.warns(UserWarning, match="D23")
                           if method == "vi" else nullcontext())
        with warning_context:
            s = fit_gp(model, lik, x, y, method=method, **kw)
        draws = extract_gp_predictives(model, lik, x, y, x_eval, s,
                                       kernel_builder=build_toy_kernels,
                                       n_posterior_samples=5)
        assert len(draws) >= 1, method
        assert draws[0].mean.shape == (8,), method


# ── D10: the G-metric identity ─────────────────────────────────────

def _legacy_viz_compute_G(params, predict_fn, gp_mean, gp_var, x_eval):
    """The LEGACY viz scripts' G, verbatim ("pointwise variance-weighted
    MSE" with its 1e-6 variance floor). The self-contained scripts were
    ported onto the package in D17; the last self-contained copy is pinned
    at commit a87356a (bistar_viz/scripts/model_priors_laplace.py:175-181),
    and this inline reimplementation keeps the D10 identity pinned against
    that formula without a git dependency in the test."""
    try:
        mu = predict_fn(x_eval, params)
        return np.mean((gp_mean - mu) ** 2 / (2 * np.maximum(gp_var, 1e-6)))
    except Exception:
        return 1e10


def test_viz_variance_weighted_mse_is_pw_kl_vcal():
    """The viz scripts' compute_G ("pointwise variance-weighted MSE") equals
    the package default metric pw_kl_vcal exactly (same formula:
    mean((mu_gp - mu_theta)^2 / (2 sigma^2_gp))) — the 'single-G decision'
    is a naming difference, not a mathematical fork.

    Scope (codex finding): the identity holds wherever the GP pointwise
    variance is at or above the viz floor of 1e-6. Below it the two floors
    differ (viz clips var at 1e-6, the package at 1e-10), so the functions
    diverge in the degenerate near-interpolation regime — pinned in the
    companion test below and qualified in docs/inference-and-metric-options.md.
    """
    import bistar_gp.metrics_v2  # noqa: F401 — registers pw_kl_vcal
    from bistar_gp.bms_star import METRICS

    rng = np.random.default_rng(0)
    x_eval = np.linspace(-3, 3, 25)
    gp_mean = rng.normal(size=25)
    gp_var = rng.uniform(0.05, 2.0, size=25)      # above the viz 1e-6 floor

    params = {"a": 0.4, "b": -0.2}
    predict_fn = lambda x, p: p["a"] * x + p["b"]
    mu_theta = predict_fn(x_eval, params)

    g_viz = _legacy_viz_compute_G(params, predict_fn, gp_mean, gp_var, x_eval)
    g_pkg = METRICS["pw_kl_vcal"](gp_mean, np.diag(gp_var),
                                  mu_theta, np.eye(25))
    assert g_viz == pytest.approx(g_pkg, rel=1e-12)


def test_viz_and_package_floors_diverge_below_1e6_variance():
    """Companion to the identity test: BELOW variance 1e-6 the two
    implementations differ by their floors (viz clips at 1e-6, package at
    1e-10), so with gp_var=1e-8 the package G is exactly 100x the viz G.
    Pinned so the divergence regime is documented behavior, not a surprise."""
    import bistar_gp.metrics_v2  # noqa: F401
    from bistar_gp.bms_star import METRICS

    n = 5
    x_eval = np.linspace(0, 1, n)
    gp_mean = np.ones(n)
    gp_var = np.full(n, 1e-8)                     # below viz floor, above pkg floor
    predict_fn = lambda x, p: np.zeros_like(x)    # mean error = 1 everywhere

    g_viz = _legacy_viz_compute_G({}, predict_fn, gp_mean, gp_var, x_eval)
    g_pkg = METRICS["pw_kl_vcal"](gp_mean, np.diag(gp_var),
                                  np.zeros(n), np.eye(n))
    assert g_viz == pytest.approx(1.0 / (2 * 1e-6), rel=1e-9)   # viz floor binds
    assert g_pkg == pytest.approx(1.0 / (2 * 1e-8), rel=1e-9)   # pkg: true var
    assert g_pkg == pytest.approx(100.0 * g_viz, rel=1e-9)
