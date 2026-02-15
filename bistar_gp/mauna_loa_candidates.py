"""
Parametric candidate models for Mauna Loa BMS* comparison.

Complexity ladder:
  1. Linear         y = a·t + b                                          (2 params)
  2. Quadratic      y = a·t² + b·t + c                                   (3 params)
  5. Quad+Sin       y = a·t² + b·t + c + A·sin(2πt + φ)                  (5 params)
  7. Quad+2Harm     y = a·t² + b·t + c + A₁sin(2πt+φ₁) + A₂sin(4πt+φ₂)  (7 params)

Frequencies are FIXED at annual (2π) and semi-annual (4π) in normalized
time where period = 1 year.  This is appropriate for Mauna Loa where
periodicity is known a priori — we are not discovering the frequency,
we are asking whether the seasonal component improves the model.

Reuses LinearModel and QuadraticModel from candidates.py.
"""

import numpy as np
from bistar_gp.candidates import CandidateModel, CandidateResult

TWO_PI = 2 * np.pi


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
                    result = self._fit_mle(x, y, self._f, p0)
                    mu = self._f(x, result[:-1])
                    nll = 0.5 * np.sum((y - mu) ** 2) / np.exp(2 * result[-1])
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
                        result = self._fit_mle(x, y, self._f, p0)
                        mu = self._f(x, result[:-1])
                        nll = 0.5 * np.sum((y - mu) ** 2) / np.exp(2 * result[-1])
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
