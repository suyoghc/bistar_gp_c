"""
Parametric candidate models for the Law of Practice debate.

Competing models for how RT decreases with practice trials:
  - Power:             RT(t) = a * t^(-b) + c
  - Exponential:       RT(t) = a * exp(-b*t) + c  
  - Delayed Exponential: RT(t) = a * exp(-b*(t-d)) + c, with delay d >= 0
  - APEX:              RT(t) = a * t^(-b) * exp(-c*t) + d

References:
  Heathcote, Brown & Mewhort (2000). Psychon Bull Rev.
  Evans, Brown, Mewhort & Heathcote (2018). Psych Review.
"""

import numpy as np
from scipy.optimize import minimize, differential_evolution
from dataclasses import dataclass
from typing import Dict
import warnings

warnings.filterwarnings("ignore", category=RuntimeWarning)


@dataclass
class CandidateResult:
    """Predictive distribution from a candidate model."""
    name: str
    mean: np.ndarray          # (n_eval,)
    cov: np.ndarray           # (n_eval, n_eval)
    noise_var: float
    parameters: Dict[str, float]
    n_params: int             # for BIC/AIC comparison


class CandidateModel:
    """Base class for practice law candidate models."""

    name: str = "base"
    n_free_params: int = 0

    def fit(self, x: np.ndarray, y: np.ndarray) -> None:
        raise NotImplementedError

    def predict(self, x_eval: np.ndarray) -> CandidateResult:
        raise NotImplementedError

    def log_marginal_likelihood(self, x: np.ndarray, y: np.ndarray) -> float:
        """
        Approximate log marginal likelihood via BIC-Laplace approximation.
        For standard Bayes factor comparison baseline.
        """
        pred = self.predict(x)
        n = len(y)
        residuals = y - pred.mean
        sigma2 = pred.noise_var
        k = self.n_free_params + 1  # +1 for noise

        ll = -0.5 * n * np.log(2 * np.pi * sigma2) - 0.5 * np.sum(residuals**2) / sigma2
        return ll - 0.5 * k * np.log(n)

    def _fit_multistart(self, x, y, f_predict, bounds, n_starts=20):
        """
        Robust fitting with differential evolution + multistart L-BFGS-B.
        Practice models have nasty likelihood surfaces.
        """
        n = len(y)

        def neg_log_lik(params):
            log_sigma = params[-1]
            sigma2 = np.exp(2 * log_sigma)
            if sigma2 < 1e-12 or sigma2 > 1e8:
                return 1e10
            mu = f_predict(x, params[:-1])
            if not np.all(np.isfinite(mu)):
                return 1e10
            residuals = y - mu
            return 0.5 * n * np.log(2 * np.pi * sigma2) + 0.5 * np.sum(residuals**2) / sigma2

        # Stage 1: Differential evolution (global)
        try:
            de_result = differential_evolution(
                neg_log_lik, bounds, maxiter=200, seed=42,
                tol=1e-6, polish=True
            )
            best_params = de_result.x
            best_nll = de_result.fun
        except Exception:
            best_params = np.array([(b[0] + b[1]) / 2 for b in bounds])
            best_nll = np.inf

        # Stage 2: Multistart L-BFGS-B refinement
        rng = np.random.RandomState(42)
        for _ in range(n_starts):
            p0 = np.array([rng.uniform(b[0], b[1]) for b in bounds])
            try:
                result = minimize(neg_log_lik, p0, method="L-BFGS-B", bounds=bounds)
                if result.fun < best_nll:
                    best_nll = result.fun
                    best_params = result.x
            except Exception:
                continue

        return best_params

    def _make_result(self, x_eval, mean, noise_var, params_dict):
        """Build CandidateResult with isotropic noise covariance."""
        n = len(x_eval)
        cov = noise_var * np.eye(n)
        return CandidateResult(
            name=self.name, mean=mean, cov=cov,
            noise_var=noise_var, parameters=params_dict,
            n_params=self.n_free_params + 1,
        )


class PowerModel(CandidateModel):
    """
    Power law: RT(t) = a * t^(-b) + c
    The classic (Newell & Rosenbloom, 1981).
    """
    name = "Power"
    n_free_params = 3

    def __init__(self):
        self.a = 1.0; self.b = 0.5; self.c = 0.0; self.sigma = 1.0

    def fit(self, x, y):
        def f(t, params):
            a, b, c = params
            return a * np.maximum(t, 0.5) ** (-b) + c

        y_range = y.max() - y.min()
        bounds = [
            (0.01, 10 * y_range), (0.01, 3.0),
            (y.min() * 0.5, y.max()), (np.log(0.001), np.log(max(y_range, 0.01))),
        ]
        params = self._fit_multistart(x, y, f, bounds)
        self.a, self.b, self.c = params[0], params[1], params[2]
        self.sigma = np.exp(params[3])

    def predict(self, x_eval):
        mean = self.a * np.maximum(x_eval, 0.5) ** (-self.b) + self.c
        return self._make_result(
            x_eval, mean, self.sigma**2,
            {"a": self.a, "b": self.b, "c": self.c, "sigma": self.sigma},
        )


class ExponentialModel(CandidateModel):
    """
    Exponential: RT(t) = a * exp(-b*t) + c
    Heathcote et al. (2000) challenger.
    """
    name = "Exponential"
    n_free_params = 3

    def __init__(self):
        self.a = 1.0; self.b = 0.1; self.c = 0.0; self.sigma = 1.0

    def fit(self, x, y):
        def f(t, params):
            a, b, c = params
            return a * np.exp(-b * t) + c

        y_range = y.max() - y.min()
        bounds = [
            (0.01, 10 * y_range), (1e-4, 2.0),
            (y.min() * 0.5, y.max()), (np.log(0.001), np.log(max(y_range, 0.01))),
        ]
        params = self._fit_multistart(x, y, f, bounds)
        self.a, self.b, self.c = params[0], params[1], params[2]
        self.sigma = np.exp(params[3])

    def predict(self, x_eval):
        mean = self.a * np.exp(-self.b * x_eval) + self.c
        return self._make_result(
            x_eval, mean, self.sigma**2,
            {"a": self.a, "b": self.b, "c": self.c, "sigma": self.sigma},
        )


class DelayedExponentialModel(CandidateModel):
    """
    Delayed Exponential: RT(t) = a * exp(-b * max(t-d, 0)) + c
    Evans et al. (2018): allows initial plateau.
    """
    name = "DelayedExp"
    n_free_params = 4

    def __init__(self):
        self.a = 1.0; self.b = 0.1; self.c = 0.0; self.d = 0.0; self.sigma = 1.0

    def fit(self, x, y):
        def f(t, params):
            a, b, c, d = params
            return a * np.exp(-b * np.maximum(t - d, 0)) + c

        y_range = y.max() - y.min()
        t_range = x.max() - x.min()
        bounds = [
            (0.01, 10 * y_range), (1e-4, 2.0),
            (y.min() * 0.5, y.max()), (0.0, t_range * 0.5),
            (np.log(0.001), np.log(max(y_range, 0.01))),
        ]
        params = self._fit_multistart(x, y, f, bounds)
        self.a, self.b, self.c, self.d = params[0], params[1], params[2], params[3]
        self.sigma = np.exp(params[4])

    def predict(self, x_eval):
        mean = self.a * np.exp(-self.b * np.maximum(x_eval - self.d, 0)) + self.c
        return self._make_result(
            x_eval, mean, self.sigma**2,
            {"a": self.a, "b": self.b, "c": self.c, "d": self.d, "sigma": self.sigma},
        )


class APEXModel(CandidateModel):
    """
    APEX: RT(t) = a * t^(-b) * exp(-c*t) + d
    Heathcote et al. (2000) hybrid. Nests Power (c=0) and Exp (b=0).
    """
    name = "APEX"
    n_free_params = 4

    def __init__(self):
        self.a = 1.0; self.b = 0.5; self.c = 0.0; self.d = 0.0; self.sigma = 1.0

    def fit(self, x, y):
        def f(t, params):
            a, b, c, d = params
            t_safe = np.maximum(t, 0.5)
            return a * t_safe ** (-b) * np.exp(-c * t_safe) + d

        y_range = y.max() - y.min()
        bounds = [
            (0.01, 10 * y_range), (0.0, 3.0), (0.0, 2.0),
            (y.min() * 0.5, y.max()), (np.log(0.001), np.log(max(y_range, 0.01))),
        ]
        params = self._fit_multistart(x, y, f, bounds)
        self.a, self.b, self.c, self.d = params[0], params[1], params[2], params[3]
        self.sigma = np.exp(params[4])

    def predict(self, x_eval):
        t_safe = np.maximum(x_eval, 0.5)
        mean = self.a * t_safe ** (-self.b) * np.exp(-self.c * t_safe) + self.d
        return self._make_result(
            x_eval, mean, self.sigma**2,
            {"a": self.a, "b": self.b, "c": self.c, "d": self.d, "sigma": self.sigma},
        )


def build_practice_candidates():
    """All 4 competing models."""
    return [PowerModel(), ExponentialModel(), DelayedExponentialModel(), APEXModel()]

def build_core_candidates():
    """Just Power vs Exponential — the classic debate."""
    return [PowerModel(), ExponentialModel()]
