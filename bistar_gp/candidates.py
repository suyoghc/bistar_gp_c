"""
Parametric candidate models for BMS* comparison.

Each model has:
    fit(x, y)       → learn parameters via MLE
    predict(x_eval) → (mean, cov) predictive distribution
    name            → string identifier
    params()        → dict of fitted parameters
"""

import numpy as np
from scipy.optimize import minimize
from dataclasses import dataclass
from typing import Tuple, Dict, Optional


@dataclass
class CandidateResult:
    """Predictive distribution from a candidate model."""
    name: str
    mean: np.ndarray          # (n_eval,)
    cov: np.ndarray           # (n_eval, n_eval)
    noise_var: float
    parameters: Dict[str, float]
    # Universe identity for the Mauna A4 separate-normalization rule: stamped
    # by _make_result from the producing model's tag, so the guard can
    # validate the exact list handed to run_bms_star rather than the model
    # list it was derived from. None for non-registry candidates (the toy
    # universe has no A4 rule).
    universe: Optional[str] = None


class CandidateModel:
    """Base class for parametric candidate models."""

    name: str = "base"

    def fit(self, x: np.ndarray, y: np.ndarray) -> None:
        raise NotImplementedError

    def predict(self, x_eval: np.ndarray) -> CandidateResult:
        raise NotImplementedError

    def _fit_mle(self, x, y, f_predict, p0, bounds=None):
        """
        Generic MLE fitting. f_predict(x, params) -> mean vector.
        Assumes Gaussian noise: y ~ N(f(x; params), sigma^2 I).
        Last element of params is log(sigma).

        Returns (params, nll). Multi-start callers must compare restarts by
        this nll — the FULL negative log likelihood including the
        0.5*n*log(2*pi*sigma^2) term. The residual term alone is useless for
        that comparison: at any converged MLE sigma^2 = mean(residuals^2), so
        0.5*sum(r^2)/sigma^2 = n/2 for EVERY restart, and selection degrades
        to optimizer-noise tie-breaking (which picked a degenerate
        near-linear "sinusoid" on the thesis toy data).
        """
        def neg_log_lik(params):
            log_sigma = params[-1]
            sigma2 = np.exp(2 * log_sigma)
            mu = f_predict(x, params[:-1])
            residuals = y - mu
            n = len(y)
            return 0.5 * n * np.log(2 * np.pi * sigma2) + 0.5 * np.sum(residuals**2) / sigma2

        result = minimize(neg_log_lik, p0, bounds=bounds, method="L-BFGS-B")
        return result.x, result.fun

    def _make_result(self, x_eval, mean, noise_var, params_dict):
        """Build CandidateResult with isotropic noise covariance."""
        n = len(x_eval)
        cov = noise_var * np.eye(n)
        return CandidateResult(
            name=self.name,
            mean=mean,
            cov=cov,
            noise_var=noise_var,
            parameters=params_dict,
            universe=getattr(self, "universe", None),
        )


class LinearModel(CandidateModel):
    """y = ax + b + eps"""

    name = "Linear"

    def __init__(self):
        self.a = 0.0
        self.b = 0.0
        self.sigma = 1.0

    def fit(self, x, y):
        def f(x, params):
            return params[0] * x + params[1]

        p0 = [0.0, 0.0, np.log(0.5)]
        result, _ = self._fit_mle(x, y, f, p0)
        self.a, self.b = result[0], result[1]
        self.sigma = np.exp(result[2])

    def predict(self, x_eval):
        mean = self.a * x_eval + self.b
        return self._make_result(
            x_eval, mean, self.sigma**2,
            {"a": self.a, "b": self.b, "sigma": self.sigma},
        )


class SinusoidalModel(CandidateModel):
    """y = A * sin(omega * x + phi) + eps"""

    name = "Sinusoidal"

    def __init__(self):
        self.A = 1.0
        self.omega = 1.0
        self.phi = 0.0
        self.sigma = 1.0

    def fit(self, x, y):
        def f(x, params):
            return params[0] * np.sin(params[1] * x + params[2])

        # Try multiple initializations (omega is tricky)
        best_nll = np.inf
        best_params = None
        for omega_init in [0.5, 1.0, 1.5, 2.0]:
            for A_init in [0.5, 1.0, 2.0]:
                p0 = [A_init, omega_init, 0.0, np.log(0.5)]
                try:
                    result, nll = self._fit_mle(x, y, f, p0)
                    if nll < best_nll:
                        best_nll = nll
                        best_params = result
                except Exception:
                    continue

        if best_params is not None:
            self.A, self.omega, self.phi = best_params[0], best_params[1], best_params[2]
            self.sigma = np.exp(best_params[3])
        else:
            # Fallback: just use initial
            self.A, self.omega, self.phi = 1.0, 1.0, 0.0
            self.sigma = np.std(y)

    def predict(self, x_eval):
        mean = self.A * np.sin(self.omega * x_eval + self.phi)
        return self._make_result(
            x_eval, mean, self.sigma**2,
            {"A": self.A, "omega": self.omega, "phi": self.phi, "sigma": self.sigma},
        )


class SinLinearModel(CandidateModel):
    """y = A * sin(omega * x + phi) + b * x + c + eps"""

    name = "Sin+Linear"

    def __init__(self):
        self.A = 1.0
        self.omega = 1.0
        self.phi = 0.0
        self.b = 0.0
        self.c = 0.0
        self.sigma = 1.0

    def fit(self, x, y):
        def f(x, params):
            return params[0] * np.sin(params[1] * x + params[2]) + params[3] * x + params[4]

        best_nll = np.inf
        best_params = None
        for omega_init in [0.5, 1.0, 1.5, 2.0]:
            p0 = [1.0, omega_init, 0.0, 0.25, 0.0, np.log(0.3)]
            try:
                result, nll = self._fit_mle(x, y, f, p0)
                if nll < best_nll:
                    best_nll = nll
                    best_params = result
            except Exception:
                continue

        if best_params is not None:
            self.A = best_params[0]
            self.omega = best_params[1]
            self.phi = best_params[2]
            self.b = best_params[3]
            self.c = best_params[4]
            self.sigma = np.exp(best_params[5])
        else:
            self.A, self.omega, self.phi = 1.0, 1.0, 0.0
            self.b, self.c = 0.25, 0.0
            self.sigma = np.std(y)

    def predict(self, x_eval):
        mean = self.A * np.sin(self.omega * x_eval + self.phi) + self.b * x_eval + self.c
        return self._make_result(
            x_eval, mean, self.sigma**2,
            {"A": self.A, "omega": self.omega, "phi": self.phi,
             "b": self.b, "c": self.c, "sigma": self.sigma},
        )


class QuadraticModel(CandidateModel):
    """y = a * x^2 + b * x + c + eps"""

    name = "Quadratic"

    def __init__(self):
        self.a = 0.0
        self.b = 0.0
        self.c = 0.0
        self.sigma = 1.0

    def fit(self, x, y):
        def f(x, params):
            return params[0] * x**2 + params[1] * x + params[2]

        p0 = [0.0, 0.0, 0.0, np.log(0.5)]
        result, _ = self._fit_mle(x, y, f, p0)
        self.a, self.b, self.c = result[0], result[1], result[2]
        self.sigma = np.exp(result[3])

    def predict(self, x_eval):
        mean = self.a * x_eval**2 + self.b * x_eval + self.c
        return self._make_result(
            x_eval, mean, self.sigma**2,
            {"a": self.a, "b": self.b, "c": self.c, "sigma": self.sigma},
        )


def build_toy_candidates():
    """Return all 4 candidate models for the toy example."""
    return [LinearModel(), SinusoidalModel(), SinLinearModel(), QuadraticModel()]
