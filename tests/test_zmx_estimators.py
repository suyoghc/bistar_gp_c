"""
Sampling estimators for Z_Mx (mc_log_Z_Mx / is_log_Z_Mx) and the batch-2b
package additions — the test checklist of docs/plan-viz-unification.md §6.

Estimator ground rules being pinned:
  - is_log_Z_Mx is ORDINARY defensive-mixture IS (the proposal density is
    evaluated exactly), not SNIS — Z_Mx is itself the normalizer.
  - occam bookkeeping is one module-wide convention (D5): Laplace's
    occam=True subtracts log V; MC's box-uniform mean is already
    occam-normalized so occam=False ADDS log V; IS estimates the raw
    integral so occam=True subtracts log V.
  - log Z <= 0 at large tau holds only for the OCCAM-NORMALIZED quantity.
"""

import numpy as np
import pytest
from types import SimpleNamespace

pytest.importorskip("torch")  # import chain (bms_star) needs torch

import bistar_gp.laplace_evidence as le
from bistar_gp.laplace_evidence import (
    laplace_log_Z_Mx, mc_log_Z_Mx, is_log_Z_Mx, compute_G_at_params,
    _DefensiveProposal, _log_reference_volume,
)
from bistar_gp.bms_star import METRICS
from bistar_gp.induced_prior import ParameterSpec, ModelParameterSpace

X_EVAL = np.linspace(0.0, 4.0, 15)
GP = SimpleNamespace(mean=0.5 * X_EVAL - 0.3, cov=np.eye(15) * 0.05)


def lin_space(z_bounds=None):
    """Sigma-free linear space; optional DEAD parameter z (ignored by
    predict_fn) for the controlled volume tests."""
    specs = [ParameterSpec("a", (-1.0, 1.0), None),
             ParameterSpec("b", (-1.0, 1.0), None)]
    if z_bounds is not None:
        specs.append(ParameterSpec("z", z_bounds, None))
    return ModelParameterSpace(
        model_name="Lin", param_specs=specs,
        predict_fn=lambda x, p: p["a"] * x + p["b"], noise_param="sigma")


@pytest.fixture
def mse_metric():
    name = "_mse_est_test"
    METRICS[name] = lambda mp, cp, mq, cq: float(
        np.mean((np.asarray(mp) - np.asarray(mq)) ** 2))
    yield name
    del METRICS[name]


def _grid_truth(ps, metric_name, taus, n_grid=121):
    """Raw Lebesgue integral over the 2-D (a,b) box by quadrature."""
    gs = np.linspace(-1, 1, n_grid)
    mf = METRICS[metric_name]
    G = np.array([[compute_G_at_params({"a": a, "b": b}, ps, X_EVAL, GP, mf)
                   for b in gs] for a in gs])
    cell = (gs[1] - gs[0]) ** 2
    return [float(np.log(np.sum(np.exp(-G / t)) * cell)) for t in taus]


# ── §6.1 MC vs grid ─────────────────────────────────────────────────

def test_mc_matches_grid_truth():
    ps = lin_space()
    taus = [0.1, 1.0, 10.0]
    truth = _grid_truth(ps, "pw_kl_vcal", taus)
    r = mc_log_Z_Mx(ps, X_EVAL, GP, taus, n_mc=40_000, seed=0)
    assert not r.occam and r.estimator == "mc"
    # low tau: weights starve (documented); mid/high: tight
    assert r.log_Z[0] == pytest.approx(truth[0], abs=0.15)
    assert r.log_Z[1] == pytest.approx(truth[1], abs=0.05)
    assert r.log_Z[2] == pytest.approx(truth[2], abs=0.05)
    assert r.ess[0] < r.ess[2]   # starvation is monotone toward low tau


# ── §6.2 controlled cross-estimator volume invariance (D5) ─────────

def test_volume_bookkeeping_identical_across_estimators(mse_metric):
    """Peaked-integrand setup: exp(−Ḡ/τ) is negligible outside a core well
    inside the box, so widening the b-bounds from (-1,1) to (-2,2) leaves the
    RAW integral approximately unchanged (analytic tail leakage 0.0009 nats
    at τ=0.1 and 0.036 at τ=0.3 — codex-verified, inside the tolerance)
    while log V grows by log 2. All three estimators must then agree:
    occam=False deltas ≈ 0, occam=True deltas ≈ −log 2 — volume enters ONLY
    through the −log V term (the D5 invariant).

    (A dead-parameter variant is NOT a valid three-way test: a dead direction
    is floored-flat for Laplace, whose fabricated width does not scale with
    the box — the documented n_clipped pathology, asserted separately below.)
    """
    taus = [0.1, 0.3]
    st = [{"a": 0.5, "b": -0.3}]

    # Orthonormalized features (centered, unit-RMS x) make G exactly
    # ISOTROPIC in (a, b) under the mse metric: G = (a-0.5)^2 + (b+0.3)^2.
    # With predict = a*x + b on raw x in [0, 4], the a-b correlation ridge
    # keeps exp(-G/tau) non-negligible in the widened strip and the raw
    # integral genuinely changes — that variant is not a bookkeeping test.
    x2 = np.linspace(-2.0, 2.0, 15)
    xt = x2 / np.sqrt(np.mean(x2 ** 2))
    gp2 = SimpleNamespace(mean=0.5 * xt - 0.3, cov=np.eye(15) * 0.05)

    def spaces(b_hi):
        return ModelParameterSpace(
            model_name="Lin",
            param_specs=[ParameterSpec("a", (-1.0, 1.0), None),
                         ParameterSpec("b", (-b_hi, b_hi), None)],
            predict_fn=lambda x, p: p["a"] * (x / np.sqrt(np.mean(x ** 2)))
                                    + p["b"],
            noise_param="sigma")

    out = {}
    for tag, b_hi in (("narrow", 1.0), ("wide", 2.0)):
        ps = spaces(b_hi)
        for occam in (False, True):
            lap = np.array([laplace_log_Z_Mx(ps, x2, gp2,
                                             metric_name=mse_metric, tau=t,
                                             occam=occam, starts=st).log_Z
                            for t in taus])
            mc = mc_log_Z_Mx(ps, x2, gp2, taus, n_mc=30_000, seed=0,
                             metric_name=mse_metric, occam=occam).log_Z
            iss = is_log_Z_Mx(ps, x2, gp2, taus, n_is=30_000, seed=0,
                              starts=st, metric_name=mse_metric,
                              occam=occam).log_Z
            out[(tag, occam)] = (lap, mc, iss)

    for occam, shift in ((False, 0.0), (True, -np.log(2.0))):
        for i, est in enumerate(("laplace", "mc", "is")):
            delta = out[("wide", occam)][i] - out[("narrow", occam)][i]
            assert np.allclose(delta, shift, atol=0.06), \
                (est, occam, delta, shift)

    # The dead-parameter pathology is FLAGGED, not silent: a z the predict_fn
    # ignores gives a floored-flat Hessian direction (n_clipped > 0), the
    # signal that this Laplace value is floor-dependent and volume-unsafe.
    z = laplace_log_Z_Mx(lin_space(z_bounds=(0.0, 1.0)), X_EVAL, GP,
                         metric_name=mse_metric,
                         starts=[{"a": 0.5, "b": -0.3, "z": 0.5}])
    assert z.n_clipped >= 1


# ── §6.3 IS reference estimator ─────────────────────────────────────

def test_is_matches_grid_across_tau_and_laplace_at_low_tau():
    ps = lin_space()
    taus = [0.1, 0.5, 1.0, 10.0, 100.0]
    truth = _grid_truth(ps, "pw_kl_vcal", taus)
    st = [{"a": 0.5, "b": -0.3}]
    r = is_log_Z_Mx(ps, X_EVAL, GP, taus, n_is=40_000, seed=0, starts=st)
    for lz, tr in zip(r.log_Z, truth):
        assert lz == pytest.approx(tr, abs=0.1)
    assert np.all(r.ess > 1000)
    # unimodal interior optimum at low tau: Laplace and IS agree
    lap = laplace_log_Z_Mx(ps, X_EVAL, GP, tau=0.1, starts=st).log_Z
    assert r.log_Z[0] == pytest.approx(lap, abs=0.05)


def test_is_deterministic_under_seed_and_warns_when_starved(caplog):
    ps = lin_space()
    st = [{"a": 0.5, "b": -0.3}]
    r1 = is_log_Z_Mx(ps, X_EVAL, GP, [0.5, 5.0], n_is=5_000, seed=7, starts=st)
    r2 = is_log_Z_Mx(ps, X_EVAL, GP, [0.5, 5.0], n_is=5_000, seed=7, starts=st)
    assert np.array_equal(r1.log_Z, r2.log_Z) and np.array_equal(r1.ess, r2.ess)

    import logging
    with caplog.at_level(logging.WARNING, logger="bistar_gp.laplace_evidence"):
        is_log_Z_Mx(ps, X_EVAL, GP, [1e-4], n_is=300, seed=0, starts=st,
                    ess_warn=100.0)
    assert any("ESS below" in rec.message for rec in caplog.records)


# ── §6.4 starts= recovers optima the midpoint start misses ─────────

def test_starts_recover_sinusoid_basin():
    """V1 re-derivation (in-repo): the Ḡ landscape of a sinusoidal candidate
    is multimodal in omega; the box-midpoint start lands in a bad basin."""
    x_eval = np.linspace(-10, 10, 60)
    gp = SimpleNamespace(mean=np.sin(x_eval) + 0.25 * x_eval,
                         cov=np.eye(60) * 0.3)
    sin_space = ModelParameterSpace(
        model_name="Sinusoidal",
        param_specs=[ParameterSpec("A", (0.01, 5.0), None),
                     ParameterSpec("om", (0.1, 5.0), None),
                     ParameterSpec("ph", (-np.pi, np.pi), None)],
        predict_fn=lambda x, p: p["A"] * np.sin(p["om"] * x + p["ph"]),
        noise_param="sigma")
    mid = laplace_log_Z_Mx(sin_space, x_eval, gp)                    # midpoint
    multi = laplace_log_Z_Mx(sin_space, x_eval, gp,
                             starts=[{"A": 1.0, "om": 1.0, "ph": 0.0},
                                     {"A": 0.5, "om": 0.5, "ph": 0.0}])
    assert multi.G_at_min < mid.G_at_min - 1.0, (mid.G_at_min, multi.G_at_min)


# ── §6.5 Laplace large-τ structure vs IS (occam=True only) ─────────

def test_laplace_high_tau_blowup_and_ranking_flip_vs_is():
    """The (d/2)log τ term: at large τ Laplace's occam-normalized log Z goes
    POSITIVE (impossible: Z = E_box[exp(−Ḡ/τ)] ≤ 1) and orders models by d,
    while IS keeps log Z ≤ 0 and orders by mean box divergence — on the viz
    spaces this flips Sin+Linear (d=5) vs Sinusoidal (d=3)."""
    x_eval = np.linspace(-10, 10, 60)
    gp = SimpleNamespace(mean=np.sin(x_eval) + 0.25 * x_eval,
                         cov=np.eye(60) * 0.3)
    sin_space = ModelParameterSpace(
        model_name="Sinusoidal",
        param_specs=[ParameterSpec("A", (0.01, 5.0), None),
                     ParameterSpec("om", (0.1, 5.0), None),
                     ParameterSpec("ph", (-np.pi, np.pi), None)],
        predict_fn=lambda x, p: p["A"] * np.sin(p["om"] * x + p["ph"]),
        noise_param="sigma")
    sl_space = ModelParameterSpace(
        model_name="Sin+Linear",
        param_specs=[ParameterSpec("A", (0.01, 5.0), None),
                     ParameterSpec("om", (0.1, 5.0), None),
                     ParameterSpec("ph", (-np.pi, np.pi), None),
                     ParameterSpec("b", (-2.0, 2.0), None),
                     ParameterSpec("c", (-5.0, 5.0), None)],
        predict_fn=lambda x, p: (p["A"] * np.sin(p["om"] * x + p["ph"])
                                 + p["b"] * x + p["c"]),
        noise_param="sigma")
    sin_starts = [{"A": 1.0, "om": 1.0, "ph": 0.0}]
    sl_starts = [{"A": 1.0, "om": 1.0, "ph": 0.0, "b": 0.25, "c": 0.0}]
    TAU = 316.0

    lap_sin = laplace_log_Z_Mx(sin_space, x_eval, gp, tau=TAU, occam=True,
                               starts=sin_starts).log_Z
    lap_sl = laplace_log_Z_Mx(sl_space, x_eval, gp, tau=TAU, occam=True,
                              starts=sl_starts).log_Z
    is_sin = is_log_Z_Mx(sin_space, x_eval, gp, [TAU], n_is=20_000, seed=0,
                         starts=sin_starts, occam=True).log_Z[0]
    is_sl = is_log_Z_Mx(sl_space, x_eval, gp, [TAU], n_is=20_000, seed=0,
                        starts=sl_starts, occam=True).log_Z[0]

    assert lap_sin > 0 and lap_sl > 0          # impossible region: blow-up
    assert is_sin <= 0.05 and is_sl <= 0.05    # true bound (occam-normalized)
    assert lap_sl > lap_sin                    # Laplace orders by d ...
    assert is_sl < is_sin                      # ... truth disagrees: the flip


# ── §6.6 weights= on average_gp_posterior ───────────────────────────

def test_average_gp_posterior_weights_match_viz_formula():
    from bistar_gp.aggregation_v3 import average_gp_posterior
    from bistar_gp.bms_star import GPPosteriorSample

    rng = np.random.default_rng(3)
    n_eval, N = 9, 5
    draws = [GPPosteriorSample(mean=rng.normal(size=n_eval),
                               cov=np.diag(rng.uniform(0.05, 3.0, n_eval)),
                               hyperparameters={})
             for _ in range(N)]
    w = rng.dirichlet(np.ones(N))

    avg = average_gp_posterior(draws, weights=w)
    means = np.array([d.mean for d in draws])
    var = np.array([np.diag(d.cov) for d in draws])
    viz_m = w @ means                                # viz lines 115-116
    viz_v = w @ (var + means ** 2) - viz_m ** 2
    assert np.allclose(avg.mean, viz_m, atol=1e-12)
    assert np.allclose(np.diag(avg.cov), viz_v, atol=1e-12)

    # None == explicit uniform
    a0 = average_gp_posterior(draws)
    a1 = average_gp_posterior(draws, weights=np.ones(N))
    assert np.allclose(a0.mean, a1.mean) and np.allclose(a0.cov, a1.cov)

    with pytest.raises(ValueError, match="weights"):
        average_gp_posterior(draws, weights=np.ones(N - 1))


# ── §6.7 rng= on extract_gp_predictives ─────────────────────────────

def test_extract_gp_predictives_rng_is_deterministic():
    import torch
    from bistar_gp.model import build_toy_kernels, build_model
    from bistar_gp.fit import fit_gp, fit_map
    from bistar_gp.bms_star import extract_gp_predictives

    torch.set_default_dtype(torch.float64)
    x = torch.linspace(0, 6, 12)
    y = torch.sin(x) + 0.25 * x
    kers, names = build_toy_kernels()
    m, l = build_model(x, y, kers, names)
    fit_map(m, l, x, y, n_iter=60, lr=0.05, verbose=False)
    s1 = fit_gp(m, l, x, y, method="map", n_iter=10)
    samples = {k: np.linspace(0.9 * v[0], 1.1 * v[0], 10) for k, v in s1.items()}

    kw = dict(kernel_builder=build_toy_kernels, n_posterior_samples=4)
    d1 = extract_gp_predictives(m, l, x, y, torch.linspace(0, 6, 8), samples,
                                rng=np.random.default_rng(0), **kw)
    d2 = extract_gp_predictives(m, l, x, y, torch.linspace(0, 6, 8), samples,
                                rng=np.random.default_rng(0), **kw)
    assert len(d1) == len(d2) == 4
    for a, b in zip(d1, d2):
        assert np.array_equal(a.mean, b.mean)
    # legacy None path still functions
    d3 = extract_gp_predictives(m, l, x, y, torch.linspace(0, 6, 8), samples,
                                **kw)
    assert len(d3) == 4


# ── codex step-1 review: robustness regressions ─────────────────────

def test_is_survives_flat_direction_and_caps_proposal(mse_metric):
    """codex P2: a floored-flat Hessian direction (dead parameter) used to
    reconstruct-then-invert a ~1e20-condition matrix (LinAlgError risk) and
    would give a ~1e8-variance proposal component. Inversion now happens in
    eigen space with variances capped at the box scale: the call must
    succeed, stay finite, and keep a usable ESS."""
    ps = lin_space(z_bounds=(0.0, 1.0))   # z is dead: predict_fn ignores it
    st = [{"a": 0.5, "b": -0.3, "z": 0.5}]
    r = is_log_Z_Mx(ps, X_EVAL, GP, [0.5, 5.0], n_is=20_000, seed=0,
                    starts=st, metric_name=mse_metric)
    assert np.all(np.isfinite(r.log_Z))
    assert np.all(r.ess > 500)


def test_weight_ess_zero_when_all_weights_vanish():
    """codex P3: all -inf log-weights must give ESS 0 (so the starvation
    warning fires), not NaN."""
    assert le._weight_ess(np.array([-np.inf, -np.inf])) == 0.0


def test_average_gp_posterior_rejects_nonfinite_weights():
    from bistar_gp.aggregation_v3 import average_gp_posterior
    from bistar_gp.bms_star import GPPosteriorSample

    draws = [GPPosteriorSample(mean=np.zeros(3), cov=np.eye(3),
                               hyperparameters={}) for _ in range(2)]
    for bad in ([np.nan, 1.0], [np.inf, 1.0]):
        with pytest.raises(ValueError, match="finite"):
            average_gp_posterior(draws, weights=bad)


# ── §6.10 proposal consistency (codex watchpoint) ───────────────────

def test_defensive_proposal_density_consistent_with_sampler():
    """Estimate ∫_box 1 dφ = V through the full sample-and-evaluate path:
    E_q[1_box / q] = V validates that log_q matches the sampler exactly —
    the sharp part of ordinary IS. Then check the mixture density integrates
    to 1 by 2-D quadrature over a region containing box and Gaussians."""
    lo, hi = np.array([-1.0, -1.0]), np.array([1.0, 1.0])
    prop = _DefensiveProposal(lo, hi, [np.array([0.5, -0.3])],
                              [np.eye(2) * 0.1])
    rng = np.random.default_rng(1)
    S = prop.sample(rng, 200_000)
    lq, inb = prop.log_q(S)
    V_est = float(np.mean(np.where(inb, np.exp(-lq), 0.0)))
    assert V_est == pytest.approx(4.0, abs=0.06)

    # cell-CENTERED grid: the uniform component's density is discontinuous at
    # the box edge, and boundary-straddling cells of a vertex-aligned grid
    # overcount by perimeter*cell/2*density (~0.01); centering makes the
    # Riemann error second-order.
    h = 0.02
    gs = np.arange(-3.5 + h / 2, 3.5, h)
    XX, YY = np.meshgrid(gs, gs, indexing="ij")
    pts = np.column_stack([XX.ravel(), YY.ravel()])
    lq_grid, _ = prop.log_q(pts)
    mass = float(np.sum(np.exp(lq_grid)) * h ** 2)
    assert mass == pytest.approx(1.0, abs=0.005)
