"""
Candidate registry for the two Mauna Loa BMS* universes.

The main four-model ladder compares trend and seasonal complexity. The
harmonized three-model appendix compares linear, quadratic, and exponential
trend laws while holding two seasonal harmonics fixed at periods 1 and 0.5.
All seasonal candidates therefore use fixed angular frequencies 2*pi and
4*pi and the sine phase convention.

Decision A4 requires separate BMS* normalizations for these universes. They
must never be merged into one candidate normalization. Study scripts call
``assert_single_universe`` immediately before ``run_bms_star`` so accidental
cross-universe comparisons fail loudly. The appendix's quadratic member aliases
the ladder's ``QuadHarmonic2Model``, making shared-member identity structural.

The module deliberately does not import ``metrics_v2``. Consumers perform that
side-effect import before using ``MAUNA_METRICS`` so this registry stays light.
"""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Callable, Mapping, Sequence, Tuple

import numpy as np
from bistar_gp.candidates import (
    CandidateModel,
    CandidateResult,
    LinearModel,
    QuadraticModel,
)

TWO_PI = 2 * np.pi

MAIN_LADDER = "main_ladder"
APPENDIX_TREND3 = "appendix_trend3"

MAUNA_PRIMARY_METRIC = "pw_kl_vcal"
MAUNA_METRICS = (
    "pw_kl_vcal",       # A4 primary (W1-ratified default)
    # The five legacy Mauna metrics (plan section 0), kept for continuity:
    "pw_mse",
    "pw_nll",
    "pw_hellinger",
    "pw_kl_forward",
    "pw_kl_symmetric",
    # A4 appendix-sensitivity addition: the DISTRIBUTION-LEVEL forward KL
    # (covariance-sensitive, unlike the pointwise pw_kl_forward above) —
    # "existing Mauna metrics plus kl_forward" in plan sections 2 and 7.
    "kl_forward",
)
MAUNA_TAU_GRID = (0.1, 0.3, 1.0, 3.0, 10.0)
MAUNA_HEADLINE_TAU = 1.0

A4_NORMALIZATION_RULE = (
    "Decision A4: normalize this universe separately and never merge it with "
    "another Mauna BMS* universe."
)


class QuadSinModel(CandidateModel):
    """
    y = a·t² + b·t + c + A·sin(2πt + φ) + ε

    Quadratic trend + single annual harmonic.
    5 structural parameters + noise.
    """

    name = "Quad+Sin"

    def __init__(self):
        self.a = 0.0
        self.b = 0.0
        self.c = 0.0
        self.A = 0.0
        self.phi = 0.0
        self.sigma = 1.0

    @staticmethod
    def _f(x, params):
        a, b, c, A, phi = params
        return a * x**2 + b * x + c + A * np.sin(TWO_PI * x + phi)

    def fit(self, x, y):
        # Initialize from quadratic fit
        c2 = np.polyfit(x, y, 2)
        resid = y - np.polyval(c2, x)
        A_init = np.std(resid) * 2

        best_nll = np.inf
        best_params = None

        for phi_init in [0.0, np.pi / 2, np.pi, 3 * np.pi / 2]:
            for A_mult in [0.5, 1.0, 2.0]:
                p0 = [c2[0], c2[1], c2[2],
                       A_mult * A_init, phi_init,
                       np.log(max(np.std(resid) * 0.3, 1e-3))]
                try:
                    result, nll = self._fit_mle(x, y, self._f, p0)
                    if nll < best_nll:
                        best_nll = nll
                        best_params = result
                except Exception:
                    continue

        if best_params is not None:
            self.a, self.b, self.c = best_params[0], best_params[1], best_params[2]
            self.A, self.phi = best_params[3], best_params[4]
            self.sigma = np.exp(best_params[5])
        else:
            self.a, self.b, self.c = c2[0], c2[1], c2[2]
            self.A, self.phi = A_init, 0.0
            self.sigma = np.std(resid)

    def predict(self, x_eval):
        mean = self._f(x_eval, [self.a, self.b, self.c, self.A, self.phi])
        return self._make_result(
            x_eval, mean, self.sigma ** 2,
            {"a": self.a, "b": self.b, "c": self.c,
             "A": self.A, "phi": self.phi, "sigma": self.sigma},
        )


class QuadHarmonic2Model(CandidateModel):
    """
    y = a·t² + b·t + c + A₁·sin(2πt + φ₁) + A₂·sin(4πt + φ₂) + ε

    Quadratic trend + two harmonics (annual + semi-annual).
    The Mauna Loa seasonal cycle is asymmetric: sharp drawdown in
    northern-hemisphere summer, gradual recovery.  The second harmonic
    captures that shape.
    7 structural parameters + noise.
    """

    name = "Quad+2Harm"

    def __init__(self):
        self.a = 0.0
        self.b = 0.0
        self.c = 0.0
        self.A1 = 0.0
        self.phi1 = 0.0
        self.A2 = 0.0
        self.phi2 = 0.0
        self.sigma = 1.0

    @staticmethod
    def _f(x, params):
        a, b, c, A1, phi1, A2, phi2 = params
        return (a * x**2 + b * x + c
                + A1 * np.sin(TWO_PI * x + phi1)
                + A2 * np.sin(2 * TWO_PI * x + phi2))

    def fit(self, x, y):
        c2 = np.polyfit(x, y, 2)
        resid = y - np.polyval(c2, x)
        A_init = np.std(resid) * 2

        best_nll = np.inf
        best_params = None

        for phi1_init in [0.0, np.pi / 2, np.pi]:
            for phi2_init in [0.0, np.pi]:
                for A_scale in [0.5, 1.0]:
                    p0 = [c2[0], c2[1], c2[2],
                           A_scale * A_init, phi1_init,
                           A_scale * A_init * 0.3, phi2_init,
                           np.log(max(np.std(resid) * 0.1, 1e-3))]
                    try:
                        result, nll = self._fit_mle(x, y, self._f, p0)
                        if nll < best_nll:
                            best_nll = nll
                            best_params = result
                    except Exception:
                        continue

        if best_params is not None:
            self.a, self.b, self.c = best_params[0], best_params[1], best_params[2]
            self.A1, self.phi1 = best_params[3], best_params[4]
            self.A2, self.phi2 = best_params[5], best_params[6]
            self.sigma = np.exp(best_params[7])
        else:
            self.a, self.b, self.c = c2[0], c2[1], c2[2]
            self.A1, self.phi1 = A_init, 0.0
            self.A2, self.phi2 = A_init * 0.3, 0.0
            self.sigma = np.std(resid)

    def predict(self, x_eval):
        mean = self._f(x_eval, [self.a, self.b, self.c,
                                 self.A1, self.phi1, self.A2, self.phi2])
        return self._make_result(
            x_eval, mean, self.sigma ** 2,
            {"a": self.a, "b": self.b, "c": self.c,
             "A1": self.A1, "phi1": self.phi1,
             "A2": self.A2, "phi2": self.phi2, "sigma": self.sigma},
        )


def _harmonic_initialization(x, residuals):
    """Return canonical sine amplitudes and phases from a linear projection."""
    design = np.column_stack([
        np.sin(TWO_PI * x),
        np.cos(TWO_PI * x),
        np.sin(2 * TWO_PI * x),
        np.cos(2 * TWO_PI * x),
    ])
    s1, c1, s2, c2 = np.linalg.lstsq(design, residuals, rcond=None)[0]
    return (
        np.hypot(s1, c1),
        np.arctan2(c1, s1),
        np.hypot(s2, c2),
        np.arctan2(c2, s2),
    )


class LinearHarmonic2Model(CandidateModel):
    """
    y = a*t + b + A1*sin(2*pi*t + phi1) + A2*sin(4*pi*t + phi2) + eps.

    Decision A4 freezes the seasonal period at 1.0 and replaces the historical
    cosine second harmonic with the equivalent sine phase convention. Decision
    D11 governs fitting: twelve L-BFGS-B starts combine amplitude scales
    ``(0.5, 1.0, 1.5)`` with phase-offset pairs ``(0, 0)``, ``(pi/2, 0)``,
    ``(0, pi/2)``, and ``(pi, pi)``; the full Gaussian NLL selects the winner.
    """

    name = "Linear+2Harm"

    def __init__(self):
        self.a = 0.0
        self.b = 0.0
        self.A1 = 0.0
        self.phi1 = 0.0
        self.A2 = 0.0
        self.phi2 = 0.0
        self.sigma = 1.0

    @staticmethod
    def _f(x, params):
        a, b, A1, phi1, A2, phi2 = params
        return (a * x + b
                + A1 * np.sin(TWO_PI * x + phi1)
                + A2 * np.sin(2 * TWO_PI * x + phi2))

    def fit(self, x, y):
        design = np.column_stack([
            x,
            np.ones_like(x),
            np.sin(TWO_PI * x),
            np.cos(TWO_PI * x),
            np.sin(2 * TWO_PI * x),
            np.cos(2 * TWO_PI * x),
        ])
        a, b, s1, c1, s2, c2 = np.linalg.lstsq(design, y, rcond=None)[0]
        A1, phi1 = np.hypot(s1, c1), np.arctan2(c1, s1)
        A2, phi2 = np.hypot(s2, c2), np.arctan2(c2, s2)
        coefficients = np.array([a, b, s1, c1, s2, c2])
        residuals = y - np.sum(design * coefficients, axis=1)
        log_sigma = np.log(max(np.std(residuals), 1e-6))

        best_nll = np.inf
        best_params = None
        phase_offsets = [
            (0.0, 0.0),
            (np.pi / 2, 0.0),
            (0.0, np.pi / 2),
            (np.pi, np.pi),
        ]
        bounds = [(None, None)] * 6 + [(-20.0, 5.0)]
        for amplitude_scale in [0.5, 1.0, 1.5]:
            for phi1_offset, phi2_offset in phase_offsets:
                p0 = [
                    a,
                    b,
                    amplitude_scale * A1,
                    phi1 + phi1_offset,
                    amplitude_scale * A2,
                    phi2 + phi2_offset,
                    log_sigma,
                ]
                try:
                    result, nll = self._fit_mle(
                        x, y, self._f, p0, bounds=bounds,
                    )
                    if nll < best_nll:
                        best_nll = nll
                        best_params = result
                except Exception:
                    continue

        if best_params is not None:
            self.a, self.b = best_params[0], best_params[1]
            self.A1, self.phi1 = best_params[2], best_params[3]
            self.A2, self.phi2 = best_params[4], best_params[5]
            self.sigma = np.exp(best_params[6])
        else:
            self.a, self.b = a, b
            self.A1, self.phi1 = A1, phi1
            self.A2, self.phi2 = A2, phi2
            self.sigma = np.exp(log_sigma)

    def predict(self, x_eval):
        mean = self._f(
            x_eval,
            [self.a, self.b, self.A1, self.phi1, self.A2, self.phi2],
        )
        return self._make_result(
            x_eval,
            mean,
            self.sigma ** 2,
            {"a": self.a, "b": self.b,
             "A1": self.A1, "phi1": self.phi1,
             "A2": self.A2, "phi2": self.phi2, "sigma": self.sigma},
        )


class ExponentialHarmonic2Model(CandidateModel):
    """
    y = a*exp(b*t) + c + A1*sin(2*pi*t + phi1) + A2*sin(4*pi*t + phi2) + eps.

    The exponent is clamped to ``[-50, 50]`` as in the historical appendix
    class. Decision A4 freezes the period at 1.0 and uses the sine convention.
    The D11 grid uses data-scaled ``a`` values paired with
    ``b in (0.01, 0.05, 0.1, 0.2)``, amplitude scales ``(0.5, 1.0)``, and phase
    offsets ``(0, 0)`` and ``(pi/2, pi/2)``. The best full Gaussian NLL wins.
    """

    name = "Exponential+2Harm"

    def __init__(self):
        self.a = 0.0
        self.b = 0.0
        self.c = 0.0
        self.A1 = 0.0
        self.phi1 = 0.0
        self.A2 = 0.0
        self.phi2 = 0.0
        self.sigma = 1.0

    @staticmethod
    def _f(x, params):
        a, b, c, A1, phi1, A2, phi2 = params
        exponent = np.clip(b * x, -50, 50)
        return (a * np.exp(exponent) + c
                + A1 * np.sin(TWO_PI * x + phi1)
                + A2 * np.sin(2 * TWO_PI * x + phi2))

    def fit(self, x, y):
        slope = np.polyfit(x, y, 1)[0]
        x_mid = float(np.mean(x))
        trend_scale = max(float(np.ptp(y)), float(np.std(y)), 1e-3)
        trend_starts = []
        for b_init in [0.01, 0.05, 0.1, 0.2]:
            if abs(slope) > 1e-8:
                a_init = slope / (
                    b_init * np.exp(np.clip(b_init * x_mid, -50, 50))
                )
            else:
                a_init = trend_scale
            trend_starts.append((a_init, b_init))

        best_nll = np.inf
        best_params = None
        bounds = [
            (None, None),
            (-1.0, 1.0),
            (None, None),
            (None, None),
            (None, None),
            (None, None),
            (None, None),
            (-20.0, 5.0),
        ]
        for a_init, b_init in trend_starts:
            exponent = np.clip(b_init * x, -50, 50)
            c_init = float(np.mean(y - a_init * np.exp(exponent)))
            trend_residuals = y - a_init * np.exp(exponent) - c_init
            A1, phi1, A2, phi2 = _harmonic_initialization(
                x, trend_residuals,
            )
            noise_residuals = trend_residuals - (
                A1 * np.sin(TWO_PI * x + phi1)
                + A2 * np.sin(2 * TWO_PI * x + phi2)
            )
            log_sigma = np.log(max(np.std(noise_residuals), 1e-6))

            for amplitude_scale in [0.5, 1.0]:
                for phase_offset in [0.0, np.pi / 2]:
                    p0 = [
                        a_init,
                        b_init,
                        c_init,
                        amplitude_scale * A1,
                        phi1 + phase_offset,
                        amplitude_scale * A2,
                        phi2 + phase_offset,
                        log_sigma,
                    ]
                    try:
                        result, nll = self._fit_mle(
                            x, y, self._f, p0, bounds=bounds,
                        )
                        if nll < best_nll:
                            best_nll = nll
                            best_params = result
                    except Exception:
                        continue

        if best_params is not None:
            self.a, self.b, self.c = best_params[0], best_params[1], best_params[2]
            self.A1, self.phi1 = best_params[3], best_params[4]
            self.A2, self.phi2 = best_params[5], best_params[6]
            self.sigma = np.exp(best_params[7])
        else:
            a_init, b_init = trend_starts[0]
            exponent = np.clip(b_init * x, -50, 50)
            c_init = float(np.mean(y - a_init * np.exp(exponent)))
            trend_residuals = y - a_init * np.exp(exponent) - c_init
            A1, phi1, A2, phi2 = _harmonic_initialization(x, trend_residuals)
            self.a, self.b, self.c = a_init, b_init, c_init
            self.A1, self.phi1 = A1, phi1
            self.A2, self.phi2 = A2, phi2
            # sigma from the residuals of the FULL fallback mean (trend plus
            # harmonics); the trend-only residual std would inflate the
            # predictive covariance relative to the returned mean and distort
            # BMS* scores (M2a review round, finding 6).
            noise_residuals = trend_residuals - (
                A1 * np.sin(TWO_PI * x + phi1)
                + A2 * np.sin(2 * TWO_PI * x + phi2)
            )
            self.sigma = max(np.std(noise_residuals), 1e-6)

    def predict(self, x_eval):
        mean = self._f(
            x_eval,
            [self.a, self.b, self.c,
             self.A1, self.phi1, self.A2, self.phi2],
        )
        return self._make_result(
            x_eval,
            mean,
            self.sigma ** 2,
            {"a": self.a, "b": self.b, "c": self.c,
             "A1": self.A1, "phi1": self.phi1,
             "A2": self.A2, "phi2": self.phi2, "sigma": self.sigma},
        )


def build_mauna_loa_candidates():
    """
    Return the 4 candidate models for Mauna Loa BMS*.

    Complexity ladder:
      Linear         (2 params) — constant growth, no season
      Quadratic      (3 params) — accelerating growth, no season
      Quad+Sin       (5 params) — accelerating + annual sinusoid
      Quad+2Harm     (7 params) — accelerating + annual + semi-annual
    """
    from bistar_gp.candidates import LinearModel, QuadraticModel
    return [LinearModel(), QuadraticModel(), QuadSinModel(), QuadHarmonic2Model()]


# Both names intentionally reference one class object. No appendix-specific
# quadratic implementation can drift from the main ladder under decision A4.
AppendixQuadHarmonic2Model = QuadHarmonic2Model


@dataclass(frozen=True)
class MaunaUniverseSpec:
    """Immutable factories, role, and A4 normalization rule for one universe."""

    member_factories: Tuple[Callable[[], CandidateModel], ...]
    role: str
    normalization_rule: str = A4_NORMALIZATION_RULE


MAUNA_UNIVERSES: Mapping[str, MaunaUniverseSpec] = MappingProxyType({
    MAIN_LADDER: MaunaUniverseSpec(
        member_factories=(
            LinearModel,
            QuadraticModel,
            QuadSinModel,
            QuadHarmonic2Model,
        ),
        role="Primary BMS* universe.",
    ),
    APPENDIX_TREND3: MaunaUniverseSpec(
        member_factories=(
            LinearHarmonic2Model,
            AppendixQuadHarmonic2Model,
            ExponentialHarmonic2Model,
        ),
        role="Trend-law contrast only.",
    ),
})


def build_universe(key):
    """Build fresh candidates for one registered universe and tag each member."""
    try:
        spec = MAUNA_UNIVERSES[key]
    except KeyError as exc:
        available = ", ".join(sorted(MAUNA_UNIVERSES))
        raise KeyError(f"Unknown Mauna universe {key!r}; choose from {available}") from exc

    models = [factory() for factory in spec.member_factories]
    for model in models:
        model.universe = key
    return models


def assert_single_universe(members: Sequence):
    """Reject empty, untagged, or cross-universe candidate collections.

    Accepts model instances (tagged by build_universe) AND CandidateResult
    objects (tagged by _make_result from the producing model), so callers
    can — and should — validate the EXACT list handed to run_bms_star, not
    just the model list it was derived from (M2a review round, finding 5).
    An entry whose universe is missing or None counts as untagged.
    """
    members = list(members)
    if not members:
        raise ValueError("Mauna candidate collection is empty")

    untagged = [
        getattr(member, "name", type(member).__name__)
        for member in members
        if getattr(member, "universe", None) is None
    ]
    if untagged:
        raise ValueError(
            "Untagged Mauna candidate members: " + ", ".join(untagged)
        )

    universes = {member.universe for member in members}
    if len(universes) != 1:
        offenders = ", ".join(
            f"{getattr(member, 'name', type(member).__name__)} "
            f"[{member.universe}]"
            for member in members
        )
        raise ValueError("Mixed Mauna candidate universes: " + offenders)

    return next(iter(universes))
