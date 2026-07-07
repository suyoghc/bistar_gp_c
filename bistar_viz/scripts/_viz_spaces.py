"""
Shared machinery for the unified viz scripts (docs/plan-viz-unification.md).

Provides the canonical sigma-free ModelParameterSpaces (§3: unified on the
model_priors_laplace.py bounds — the D3-designated viz reference), the
trajectory-script legacy variants (harness comparisons only), and the
averaged-GP construction on package primitives (§2, the V2-verified recipe).

Prior parity is ENFORCED here (§6.8): the GP is built from
PRIOR_CONFIGS["informative"] via build_kernels_from_config — the legacy
scripts' Gamma(6,0.85)^3 + Gamma(1.75,1.0) priors — and asserted at runtime.
build_toy_kernels() would silently swap in a Gamma(2,2) lengthscale prior.
"""

import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import numpy as np

from bistar_gp.induced_prior import ParameterSpec, ModelParameterSpace

COLORS = {"Linear": "#e74c3c", "Sinusoidal": "#3498db",
          "Sin+Linear": "#27ae60", "Quadratic": "#9b59b6"}
STACK_ORDER = ["Sin+Linear", "Sinusoidal", "Linear", "Quadratic"]


def _spaces(linear_bounds, quad_bounds):
    """Sigma-free spaces (no noise parameter: Z_Mx integrates over the mean
    parameters only, matching both legacy scripts)."""
    return {
        "Linear": ModelParameterSpace(
            model_name="Linear",
            param_specs=[ParameterSpec("a", linear_bounds[0], None),
                         ParameterSpec("b", linear_bounds[1], None)],
            predict_fn=lambda x, p: p["a"] * x + p["b"],
            noise_param="sigma"),
        "Sinusoidal": ModelParameterSpace(
            model_name="Sinusoidal",
            param_specs=[ParameterSpec("A", (0.01, 5.0), None),
                         ParameterSpec("omega", (0.1, 5.0), None),
                         ParameterSpec("phi", (-np.pi, np.pi), None)],
            predict_fn=lambda x, p: p["A"] * np.sin(p["omega"] * x + p["phi"]),
            noise_param="sigma"),
        "Sin+Linear": ModelParameterSpace(
            model_name="Sin+Linear",
            param_specs=[ParameterSpec("A", (0.01, 5.0), None),
                         ParameterSpec("omega", (0.1, 5.0), None),
                         ParameterSpec("phi", (-np.pi, np.pi), None),
                         ParameterSpec("b", (-2.0, 2.0), None),
                         ParameterSpec("c", (-5.0, 5.0), None)],
            predict_fn=lambda x, p: (p["A"] * np.sin(p["omega"] * x + p["phi"])
                                     + p["b"] * x + p["c"]),
            noise_param="sigma"),
        "Quadratic": ModelParameterSpace(
            model_name="Quadratic",
            param_specs=[ParameterSpec("a", quad_bounds[0], None),
                         ParameterSpec("b", quad_bounds[1], None),
                         ParameterSpec("c", quad_bounds[2], None)],
            predict_fn=lambda x, p: p["a"] * x ** 2 + p["b"] * x + p["c"],
            noise_param="sigma"),
    }


def canonical_spaces():
    """Unified canonical bounds = the model_priors_laplace.py legacy set."""
    return _spaces(linear_bounds=[(-2.0, 2.0), (-5.0, 5.0)],
                   quad_bounds=[(-0.5, 0.5), (-2.0, 2.0), (-5.0, 5.0)])


def trajectory_legacy_spaces():
    """The trajectory script's wider Linear/Quadratic boxes — used only by
    the comparison harness to reproduce its legacy figures (plan §0 V3)."""
    return _spaces(linear_bounds=[(-3.0, 3.0), (-5.0, 5.0)],
                   quad_bounds=[(-1.0, 1.0), (-3.0, 3.0), (-5.0, 5.0)])


# The legacy multi-start init lists, as starts= dicts (plan §3).
STARTS = {
    "Linear": [{"a": 0.25, "b": 0.0}, {"a": 0.0, "b": 0.0},
               {"a": 0.5, "b": 1.0}],
    "Sinusoidal": [{"A": 1.0, "omega": 1.0, "phi": 0.0},
                   {"A": 0.5, "omega": 0.5, "phi": 0.0},
                   {"A": 2.0, "omega": 1.5, "phi": 1.0},
                   {"A": 1.0, "omega": 2.0, "phi": -1.0},
                   {"A": 1.5, "omega": 0.7, "phi": 0.5}],
    "Sin+Linear": [{"A": 1.0, "omega": 1.0, "phi": 0.0, "b": 0.25, "c": 0.0},
                   {"A": 0.5, "omega": 0.5, "phi": 0.0, "b": 0.1, "c": 0.0},
                   {"A": 2.0, "omega": 1.5, "phi": 1.0, "b": 0.5, "c": 1.0},
                   {"A": 1.0, "omega": 2.0, "phi": -1.0, "b": 0.0, "c": 0.0},
                   {"A": 1.5, "omega": 0.7, "phi": 0.5, "b": 0.3, "c": -0.5},
                   {"A": 0.8, "omega": 1.0, "phi": 0.0, "b": 0.25, "c": 0.0}],
    "Quadratic": [{"a": 0.0, "b": 0.25, "c": 0.0},
                  {"a": 0.01, "b": 0.0, "c": 0.0},
                  {"a": -0.05, "b": 0.5, "c": 1.0}],
}


def perturbed_starts(name, spaces, n_perturb, seed=42, scale=0.3):
    """STARTS[name] plus n_perturb seeded Gaussian perturbations of each,
    clipped to 0.99·bounds — the trajectory legacy script's multi-start
    convention (pinned at a87356a:model_prior_trajectory_laplace.py:217-229),
    reproduced for the harness comparison."""
    base = STARTS[name]
    specs = spaces[name].param_specs
    rng = np.random.RandomState(seed)
    out = list(base)
    for p0 in base:
        vec0 = np.array([p0[ps.name] for ps in specs])
        for _ in range(n_perturb):
            vec = vec0 + rng.normal(0, scale, len(specs))
            vec = np.array([np.clip(v, ps.bounds[0] * 0.99, ps.bounds[1] * 0.99)
                            for v, ps in zip(vec, specs)])
            out.append({ps.name: float(v) for ps, v in zip(specs, vec)})
    return out


def generate_data(n, noise_std=0.3, seed=42, x_range=(-10, 10)):
    """Legacy toy data: uniform-random sorted x, sin(x) + 0.25x + noise."""
    rng = np.random.RandomState(seed)
    x = np.sort(rng.uniform(*x_range, n))
    return x, np.sin(x) + 0.25 * x + rng.normal(0, noise_std, n)


def assert_prior_parity(model, likelihood):
    """Fail loudly if the built GP's priors are not the legacy-matching
    informative config (plan §6.8): Gamma(6,0.85) on SE lengthscale/
    outputscale and linear variance, Gamma(1.75,1.0) on noise."""
    want = {
        "covar_module.kernels.0.base_kernel.lengthscale_prior": (6.0, 0.85),
        "covar_module.kernels.0.outputscale_prior": (6.0, 0.85),
        "covar_module.kernels.1.variance_prior": (6.0, 0.85),
        "likelihood.noise_covar.noise_prior": (1.75, 1.0),
    }
    seen = {}
    for name, _, prior, _, _ in model.named_priors():
        try:
            seen[name] = (float(prior.concentration), float(prior.rate))
        except AttributeError:   # non-Gamma prior (e.g. LogNormal) registered
            seen[name] = type(prior).__name__
    for name, params in want.items():
        got = seen.get(name)
        if (not isinstance(got, tuple)) or not np.allclose(got, params):
            raise AssertionError(
                f"prior parity violated: {name} is {got}, legacy figures "
                f"require Gamma{params} (use build_kernels_from_config("
                f"PRIOR_CONFIGS['informative']), not build_toy_kernels())")


def averaged_gp(x_eval, x_train=None, y_train=None, *, gp_method="map",
                n_draws=150, seed=42, verbose=False):
    """The V2-verified averaged-GP recipe on package primitives.

    n>0 (x_train given): fit_map, then fit_gp(method=gp_method) draws, then
    extract_gp_predictives(rng=seeded), then average_gp_posterior (uniform —
    posterior/point draws carry their own weighting; this REPLACES the legacy
    LML importance weights over prior draws, the disclosed D10 estimator
    change). gp_method="map" yields a POINT-ESTIMATE predictive (a single
    draw), not posterior draws — the disclosed mechanism-figure default
    (plan §2); "vi"/"hmc" give genuine posterior draws.

    n=0: prior stage — sample_prior draws through
    extract_gp_predictives(condition_on_data=False) on placeholder tensors.

    Returns (avg_gp: GPPosteriorSample, n_retained: int).
    """
    import torch
    from bistar_gp import build_model
    from bistar_gp.config import (PRIOR_CONFIGS, build_kernels_from_config,
                                  build_likelihood_from_config)
    from bistar_gp.fit import fit_map, fit_gp, sample_prior
    from bistar_gp.bms_star import extract_gp_predictives
    from bistar_gp.aggregation_v3 import average_gp_posterior

    torch.set_default_dtype(torch.float64)
    pc = PRIOR_CONFIGS["informative"]

    prior_stage = x_train is None or len(x_train) == 0
    if prior_stage:
        # placeholder data: build_model/extract need tensors even though
        # condition_on_data=False never touches them (plan §0 V2 blocker vi)
        xt = torch.linspace(-1.0, 1.0, 4)
        yt = torch.zeros(4)
    else:
        xt = torch.as_tensor(np.asarray(x_train), dtype=torch.float64)
        yt = torch.as_tensor(np.asarray(y_train), dtype=torch.float64)

    kernels, names = build_kernels_from_config(pc)
    likelihood = build_likelihood_from_config(pc)
    model, likelihood = build_model(xt, yt, kernels, names, likelihood)
    assert_prior_parity(model, likelihood)

    if prior_stage:
        draws = sample_prior(model, n_samples=n_draws, seed=seed)
    else:
        fit_map(model, likelihood, xt, yt, n_iter=300, lr=0.05, verbose=False)
        kwargs = {"map": dict(n_iter=200),
                  "vi": dict(n_samples=n_draws, n_steps=3000, verbose=verbose,
                             seed=seed),
                  "hmc": dict(n_samples=n_draws, n_warmup=max(100, n_draws // 2),
                              verbose=verbose, seed=seed)}[gp_method]
        draws = fit_gp(model, likelihood, xt, yt, method=gp_method, **kwargs)

    x_eval_t = torch.as_tensor(np.asarray(x_eval), dtype=torch.float64)
    gp_samples = extract_gp_predictives(
        model, likelihood, xt, yt, x_eval_t, draws,
        kernel_builder=lambda: build_kernels_from_config(pc),
        likelihood_builder=lambda: build_likelihood_from_config(pc),
        n_posterior_samples=n_draws, jitter=1e-4,
        condition_on_data=not prior_stage,
        rng=np.random.default_rng(seed))
    if not gp_samples:
        raise RuntimeError("no valid GP predictives retained")
    return average_gp_posterior(gp_samples), len(gp_samples)


def model_prior_curves(spaces, x_eval, avg_gp, taus, *, estimator="is",
                       occam=False, seed=0, n_is=40_000, n_mc=100_000,
                       starts_map=None):
    """log Z per model per τ under the chosen estimator, plus softmax priors.

    Returns (names, log_Z[(n_tau, n_model)], priors[(n_tau, n_model)],
    diag: {model: per-τ ESS or None}).
    """
    from scipy.special import softmax
    from bistar_gp.laplace_evidence import (laplace_log_Z_Mx, mc_log_Z_Mx,
                                            is_log_Z_Mx)

    taus = np.asarray(list(taus), dtype=float)
    names = list(spaces.keys())
    log_Z = np.empty((len(taus), len(names)))
    diag = {}
    for j, name in enumerate(names):
        ps = spaces[name]
        st = (starts_map or STARTS).get(name)
        if estimator == "is":
            r = is_log_Z_Mx(ps, x_eval, avg_gp, taus, n_is=n_is, seed=seed,
                            starts=st, occam=occam)
            log_Z[:, j], diag[name] = r.log_Z, r.ess
        elif estimator == "mc":
            r = mc_log_Z_Mx(ps, x_eval, avg_gp, taus, n_mc=n_mc, seed=seed,
                            occam=occam)
            log_Z[:, j], diag[name] = r.log_Z, r.ess
        elif estimator == "laplace":
            log_Z[:, j] = [laplace_log_Z_Mx(ps, x_eval, avg_gp, tau=t,
                                            occam=occam, starts=st).log_Z
                           for t in taus]
            diag[name] = None
        else:
            raise ValueError(f"unknown estimator {estimator!r}")
    return names, log_Z, softmax(log_Z, axis=1), diag
