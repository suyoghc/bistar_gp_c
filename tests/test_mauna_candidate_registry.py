"""Synthetic-only regression tests for the decision A4 Mauna registry.

No test in this module loads Mauna Loa observations or reads persisted run
artifacts. The fixtures exercise universe identity, harmonized seasonal phases,
the D11 optimizer route, and BMS* normalization entirely on generated arrays.
"""

from pathlib import Path

import numpy as np
import pytest

from bistar_gp.candidates import CandidateModel, LinearModel
from bistar_gp.mauna_loa_candidates import (
    APPENDIX_TREND3,
    MAIN_LADDER,
    MAUNA_HEADLINE_TAU,
    MAUNA_METRICS,
    MAUNA_PRIMARY_METRIC,
    MAUNA_TAU_GRID,
    ExponentialHarmonic2Model,
    LinearHarmonic2Model,
    assert_single_universe,
    build_universe,
)


@pytest.fixture(scope="module")
def quadratic_harmonic_fixture():
    """Seeded quadratic trend with two fixed seasonal harmonics."""
    rng = np.random.default_rng(20260711)
    x = np.linspace(0.0, 10.0, 120)
    mean = (0.018 * x ** 2 + 0.22 * x - 0.35
            + 0.8 * np.sin(2 * np.pi * x + 0.3)
            + 0.25 * np.sin(4 * np.pi * x - 0.55))
    y = mean + 0.04 * rng.normal(size=x.size)
    return x, y, mean


def _full_nll(y, mean, sigma):
    """Full Gaussian negative log likelihood used by decision D11."""
    sigma2 = sigma ** 2
    residuals = y - mean
    return (0.5 * len(y) * np.log(2 * np.pi * sigma2)
            + 0.5 * np.sum(residuals ** 2) / sigma2)


def test_universe_composition_tags_and_fresh_instances():
    ladder = build_universe(MAIN_LADDER)
    appendix = build_universe(APPENDIX_TREND3)
    ladder_again = build_universe(MAIN_LADDER)
    appendix_again = build_universe(APPENDIX_TREND3)

    assert [model.name for model in ladder] == [
        "Linear", "Quadratic", "Quad+Sin", "Quad+2Harm",
    ]
    assert [model.name for model in appendix] == [
        "Linear+2Harm", "Quad+2Harm", "Exponential+2Harm",
    ]
    assert all(model.universe == MAIN_LADDER for model in ladder)
    assert all(model.universe == APPENDIX_TREND3 for model in appendix)
    assert all(a is not b for a, b in zip(ladder, ladder_again))
    assert all(a is not b for a, b in zip(appendix, appendix_again))


def test_shared_quadratic_member_has_class_and_fit_identity(
        quadratic_harmonic_fixture):
    x, y, _ = quadratic_harmonic_fixture
    ladder_model = build_universe(MAIN_LADDER)[-1]
    appendix_model = build_universe(APPENDIX_TREND3)[1]

    assert type(ladder_model) is type(appendix_model)

    ladder_model.fit(x, y)
    appendix_model.fit(x, y)
    ladder_result = ladder_model.predict(x)
    appendix_result = appendix_model.predict(x)

    assert ladder_result.parameters == appendix_result.parameters
    assert np.array_equal(ladder_result.mean, appendix_result.mean)
    assert np.array_equal(ladder_result.cov, appendix_result.cov)
    assert _full_nll(y, ladder_result.mean, ladder_model.sigma) == (
        _full_nll(y, appendix_result.mean, appendix_model.sigma)
    )


def test_historical_cosine_phase_maps_to_harmonized_sine_prediction():
    """At period 1, cos(theta) maps to sin(theta + pi/2)."""
    rng = np.random.default_rng(19)
    x = np.linspace(0.0, 10.0, 180)
    dense_x = np.linspace(0.0, 10.0, 1001)
    a, b = 0.27, -0.6
    A1, phi1 = 1.1, 0.35
    A2, historical_phi2 = 0.32, -0.7
    noise = 1e-4

    def historical_mean(x_eval):
        return (a * x_eval + b
                + A1 * np.sin(2 * np.pi * x_eval + phi1)
                + A2 * np.cos(4 * np.pi * x_eval + historical_phi2))

    y = historical_mean(x) + noise * rng.normal(size=x.size)
    model = LinearHarmonic2Model()
    model.fit(x, y)

    fitted_mean = model.predict(dense_x).mean
    assert np.max(np.abs(fitted_mean - historical_mean(dense_x))) < 6e-5

    fitted_train_mean = model.predict(x).mean
    fitted_nll = _full_nll(y, fitted_train_mean, model.sigma)
    mapped_params = [
        a, b, A1, phi1, A2, historical_phi2 + np.pi / 2,
    ]
    mapped_mean = model._f(x, mapped_params)
    mapped_nll = _full_nll(y, mapped_mean, noise)
    assert fitted_nll <= mapped_nll + 1e-8


def test_new_candidates_route_all_restarts_through_shared_fit_mle(monkeypatch):
    calls = []

    def fake_fit_mle(self, x, y, f_predict, p0, bounds=None):
        calls.append((type(self), np.asarray(p0), bounds))
        return np.asarray(p0, dtype=float), float(len(calls))

    monkeypatch.setattr(CandidateModel, "_fit_mle", fake_fit_mle)
    x = np.linspace(0.0, 2.0, 24)
    y = 0.2 * x + np.sin(2 * np.pi * x)

    LinearHarmonic2Model().fit(x, y)
    linear_calls = [call for call in calls if call[0] is LinearHarmonic2Model]
    assert len(linear_calls) == 12

    ExponentialHarmonic2Model().fit(x, y)
    exponential_calls = [
        call for call in calls if call[0] is ExponentialHarmonic2Model
    ]
    assert len(exponential_calls) == 16

    experiment = (
        Path(__file__).resolve().parent.parent
        / "experiments" / "bms_star_mauna_loa.py"
    ).read_text()
    assert "differential_evolution" not in experiment


def test_single_universe_guard_accepts_valid_and_rejects_merges():
    ladder = build_universe(MAIN_LADDER)
    appendix = build_universe(APPENDIX_TREND3)
    assert assert_single_universe(ladder) == MAIN_LADDER
    assert assert_single_universe(appendix) == APPENDIX_TREND3

    with pytest.raises(ValueError, match="Mixed.*Linear.*Linear\\+2Harm"):
        assert_single_universe([ladder[0], appendix[0]])
    with pytest.raises(ValueError, match="Untagged.*Linear"):
        assert_single_universe([LinearModel()])
    with pytest.raises(ValueError, match="empty"):
        assert_single_universe([])


def test_metric_and_temperature_contracts_are_registered():
    import bistar_gp.metrics_v2  # noqa: F401
    from bistar_gp.bms_star import METRICS

    legacy_metrics = {
        "pw_mse", "pw_nll", "pw_hellinger", "pw_kl_forward",
        "pw_kl_symmetric",
    }
    assert MAUNA_PRIMARY_METRIC == "pw_kl_vcal"
    assert MAUNA_METRICS[0] == MAUNA_PRIMARY_METRIC
    # Five legacy metrics plus the DISTRIBUTION-LEVEL kl_forward, the A4
    # appendix-sensitivity addition (plan sections 2 and 7: "existing Mauna
    # metrics plus kl_forward"); pw_kl_forward is one of the legacy five and
    # does not satisfy that clause.
    assert set(MAUNA_METRICS[1:]) == legacy_metrics | {"kl_forward"}
    assert MAUNA_METRICS[-1] == "kl_forward"
    assert all(metric in METRICS for metric in MAUNA_METRICS)
    assert MAUNA_TAU_GRID == (0.1, 0.3, 1.0, 3.0, 10.0)
    assert MAUNA_HEADLINE_TAU == 1.0
    assert MAUNA_HEADLINE_TAU in MAUNA_TAU_GRID


def test_synthetic_appendix_bms_star_probabilities_normalize(
        quadratic_harmonic_fixture):
    import bistar_gp.metrics_v2  # noqa: F401
    from bistar_gp.bms_star import GPPosteriorSample, run_bms_star

    x, y, mean = quadratic_harmonic_fixture
    candidates = build_universe(APPENDIX_TREND3)
    assert_single_universe(candidates)
    for candidate in candidates:
        candidate.fit(x, y)
    candidate_results = [candidate.predict(x) for candidate in candidates]

    rng = np.random.default_rng(41)
    gp_samples = [
        GPPosteriorSample(
            mean=mean + rng.normal(scale=0.015, size=x.size),
            cov=np.diag(np.full(x.size, 0.04 ** 2)),
            hyperparameters={"synthetic_draw": float(draw)},
        )
        for draw in range(3)
    ]
    results = run_bms_star(
        gp_samples,
        candidate_results,
        metric_names=[MAUNA_PRIMARY_METRIC],
        taus=np.array(MAUNA_TAU_GRID),
    )

    for tau in MAUNA_TAU_GRID:
        probabilities = results[MAUNA_PRIMARY_METRIC][tau].instance_posteriors
        assert np.isfinite(probabilities).all()
        assert probabilities.sum() == pytest.approx(1.0, abs=1e-12)


def test_results_carry_universe_and_guard_validates_normalization_input():
    """Universe identity must survive into CandidateResult so the guard can
    validate the exact list handed to run_bms_star (review finding 5)."""
    rng = np.random.default_rng(11)
    x = np.linspace(0.0, 6.0, 90)
    y = 0.4 * x + 0.6 * np.sin(2 * np.pi * x) + 0.02 * rng.standard_normal(90)

    main = build_universe(MAIN_LADDER)
    appendix = build_universe(APPENDIX_TREND3)
    main_results, appendix_results = [], []
    for model in main:
        model.fit(x, y)
        main_results.append(model.predict(x))
    for model in appendix:
        model.fit(x, y)
        appendix_results.append(model.predict(x))

    assert all(r.universe == MAIN_LADDER for r in main_results)
    assert all(r.universe == APPENDIX_TREND3 for r in appendix_results)
    assert assert_single_universe(appendix_results) == APPENDIX_TREND3
    with pytest.raises(ValueError, match="Mixed"):
        assert_single_universe(main_results + appendix_results[:1])
    # An untagged result (built outside build_universe) is rejected too.
    bare = LinearHarmonic2Model()
    bare.fit(x, y)
    with pytest.raises(ValueError, match="Untagged"):
        assert_single_universe(appendix_results + [bare.predict(x)])


def test_exponential_forced_fallback_sigma_uses_full_residuals(monkeypatch):
    """When every restart raises, the fallback sigma must come from the
    residuals of the full trend-plus-harmonics mean, not the trend-only
    residuals whose std the harmonics inflate (review finding 6)."""
    rng = np.random.default_rng(23)
    x = np.linspace(0.0, 8.0, 96)
    true_noise = 0.05
    y = (0.5 * np.exp(0.05 * x) + 1.0
         + 0.8 * np.sin(2 * np.pi * x + 0.3)
         + 0.3 * np.sin(4 * np.pi * x + 1.1)
         + true_noise * rng.standard_normal(96))

    def always_fail(self, *args, **kwargs):
        raise RuntimeError("forced restart failure")

    monkeypatch.setattr(
        "bistar_gp.candidates.CandidateModel._fit_mle", always_fail)
    model = ExponentialHarmonic2Model()
    model.fit(x, y)
    # The harmonic amplitude alone is 0.8; a trend-only-residual sigma would
    # be near hypot(0.8, 0.3)/sqrt(2) ~ 0.6. The full-residual sigma must be
    # far below that (the lstsq harmonics absorb the seasonal signal).
    assert model.sigma < 0.3
    result = model.predict(x)
    assert result.noise_var == pytest.approx(model.sigma ** 2)


def test_experiment_script_wiring_is_pinned():
    """Source-level pin for the A4 metric/tau wiring (workflow finding C11):
    reverting the experiment to a hand-rolled metric list or the legacy
    logspace tau grid must fail loudly, not silently drop the prereg grid."""
    script = (Path(__file__).resolve().parent.parent / "experiments"
              / "bms_star_mauna_loa.py").read_text()
    for required in (
        "import bistar_gp.metrics_v2",
        "metrics = list(MAUNA_METRICS)",
        "taus = np.array(MAUNA_TAU_GRID)",
        "results[metric_name][MAUNA_HEADLINE_TAU]",
        "assert_single_universe(candidate_results)",
        "build_universe(APPENDIX_TREND3)",
    ):
        assert required in script, (
            f"bms_star_mauna_loa.py lost its A4 wiring: {required!r} missing")
    assert "np.logspace" not in script, (
        "the legacy logspace tau grid must not replace MAUNA_TAU_GRID")
