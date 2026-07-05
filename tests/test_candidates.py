"""
Candidate-model MLE fitting, especially multi-start restart selection.

Regression context (DECISIONS D11): the restart pickers in SinusoidalModel and
SinLinearModel compared restarts by the residual term 0.5*sum(r^2)/sigma^2
alone. At any converged MLE sigma^2 = mean(r^2), so that quantity is n/2 for
EVERY restart — selection degenerated to optimizer-noise tie-breaking and kept
the first restart (omega_init=0.5), whose basin on the thesis toy data is a
degenerate near-linear "sinusoid" (A=116.8, omega=0.034). The fix compares the
FULL negative log likelihood returned by _fit_mle.
"""

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from bistar_gp import generate_toy_data
from bistar_gp.candidates import SinLinearModel, CandidateModel


@pytest.fixture(scope="module")
def thesis_toy():
    x, y, _ = generate_toy_data()   # sin(x) + 0.25x + N(0, 0.5^2), N=20
    return x.numpy(), y.numpy()


def test_sin_linear_recovers_sinusoid_on_thesis_toy(thesis_toy):
    """The true-model candidate must find the sin(x) + 0.25x basin, not the
    degenerate giant-amplitude near-zero-frequency solution the broken
    restart selection used to keep (omega=0.034, sigma=0.69)."""
    x, y = thesis_toy
    m = SinLinearModel()
    m.fit(x, y)
    assert 0.9 < abs(m.omega) < 1.15, m.omega
    assert 0.2 < m.b < 0.3, m.b
    assert m.sigma < 0.45, m.sigma          # ~0.32; true-parameter residual sd 0.35


def test_mauna_candidates_use_tuple_return_and_recover_params():
    """codex finding: the Mauna candidates also call _fit_mle but kept the old
    single-return unpacking — result[:-1] became a 1-tuple, _f raised inside
    the broad except, and EVERY restart silently fell through to the crude
    fallback fit. Pin that the multi-start path works: on synthetic
    quad + seasonal data the fitted sigma must be near the true noise, which
    the fallback (sigma = std of quadratic residuals, seasonal signal
    included) cannot achieve."""
    from bistar_gp.mauna_loa_candidates import QuadSinModel, QuadHarmonic2Model

    rng = np.random.default_rng(0)
    x = np.linspace(0.0, 10.0, 240)
    noise = 0.15
    y = (0.01 * x ** 2 + 1.5 * x + 315.0
         + 3.0 * np.sin(2 * np.pi * x)
         + 0.9 * np.sin(4 * np.pi * x + 0.5)
         + noise * rng.normal(size=x.size))
    seasonal_scale = np.std(y - np.polyval(np.polyfit(x, y, 2), x))  # ~2.3

    for cls in (QuadSinModel, QuadHarmonic2Model):
        m = cls()
        m.fit(x, y)
        assert m.sigma < 0.5 * seasonal_scale, (cls.__name__, m.sigma)
    # the 2-harmonic model should essentially reach the noise floor
    m2 = QuadHarmonic2Model()
    m2.fit(x, y)
    assert m2.sigma < 2.5 * noise, m2.sigma
    assert abs(m2.A1) == pytest.approx(3.0, abs=0.3)


def test_fit_mle_returns_full_nll(thesis_toy):
    """_fit_mle's second return value is the FULL Gaussian NLL at the fitted
    params (including the 0.5*n*log(2*pi*sigma^2) term), the only quantity a
    multi-start caller can validly compare across restarts."""
    x, y = thesis_toy
    f = lambda x, p: p[0] * x + p[1]
    params, nll = CandidateModel()._fit_mle(x, y, f, [0.0, 0.0, np.log(0.5)])
    sigma2 = np.exp(2 * params[-1])
    resid = y - f(x, params[:-1])
    expected = (0.5 * len(y) * np.log(2 * np.pi * sigma2)
                + 0.5 * np.sum(resid ** 2) / sigma2)
    assert nll == pytest.approx(expected, rel=1e-10)
    # and the residual-only criterion is n/2 at the MLE — the degeneracy that
    # made it useless for restart selection
    assert 0.5 * np.sum(resid ** 2) / sigma2 == pytest.approx(len(y) / 2,
                                                              rel=1e-4)
