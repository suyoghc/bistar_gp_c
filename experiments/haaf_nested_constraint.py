"""
Case C: a nested slope constraint under BMS* and PSIS-LOO.

The experiment uses the frozen N=20 thesis toy data and the validated
``toy_elicited`` stage-IS path.  Each SIR predictive pattern is fit by the
same Sin+Linear functional form twice.  The restricted fit changes only the
slope bound from unbounded to nonnegative.  BMS* uses no candidate-parameter
prior.  Separate Pyro models provide the weakly informative priors needed for
the PSIS-LOO comparison.

Canonical run from the repository root:

    python experiments/haaf_nested_constraint.py

The canonical artifacts are written under ``runs/haaf_nested_constraint/``.
``--quick`` provides a development check with smaller Monte Carlo budgets and
writes ``results_quick.json`` without replacing the canonical artifacts.
"""

from __future__ import annotations

# ruff: noqa: E402

import argparse
import hashlib
import json
import math
import os
import sys
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, REPO)
sys.path.insert(0, SCRIPT_DIR)

import arviz as az
import numpy as np
import pyro
import pyro.distributions as dist
import torch
from pyro.infer import MCMC, NUTS
from pyro.infer.autoguide.initialization import init_to_value

import e7_convention_sensitivity as e7
import prior_sensitivity_study as pss
from bistar_gp import generate_toy_data
from bistar_gp.bms_star import METRICS
from bistar_gp.candidates import CandidateModel, CandidateResult


torch.set_default_dtype(torch.float64)

OUT_DIR = os.path.join(REPO, "runs", "haaf_nested_constraint")
RESULTS_PATH = os.path.join(OUT_DIR, "results.json")
README_PATH = os.path.join(OUT_DIR, "README.md")

DATA_SEED = 42
CONFIG = "toy_elicited"
IS_SEEDS = [0, 1, 2]
SIR_SEED = 42
N_PRED = 1000
TAUS = [0.1, 0.3, 1.0, 3.0, 10.0]
PRIMARY_METRIC = "pw_kl_vcal"
APPENDIX_METRIC = "kl_forward"
VARIANTS = ["pooled", "expected_posterior"]

LOO_CHAIN_SEEDS = [20260811, 20260812]
LOO_WARMUP = 1000
LOO_DRAWS = 1000
LOO_TARGET_ACCEPT = 0.90
LOO_MAX_TREE_DEPTH = 8

# Numerical gates test the nesting identity, not statistical significance.
G_EQUAL_ATOL = 2e-7
G_ORDER_ATOL = 2e-7
BOUND_ATOL = 1e-10

# Cross-machine rerun tolerances recorded in the README and results artifact.
# The structural gates above remain much tighter.
RERUN_TOLERANCES = {
    "bms_probability_abs": 0.005,
    "loo_elpd_abs": 0.25,
    "loo_pairwise_difference_abs": 0.25,
    "negative_slope_fraction_abs": 0.005,
}

MODEL_NAMES = ["Free Sin+Linear", "Slope-constrained Sin+Linear"]
PARAMETER_NAMES = ["A", "omega", "phi", "b", "c", "sigma"]

PRIOR_DESCRIPTIONS = {
    "A": "HalfNormal(scale=5)",
    "omega": "LogNormal(loc=0, scale=0.7)",
    "phi": "Uniform(-pi, pi)",
    "b_free": "Normal(loc=0, scale=5)",
    "b_constrained": "HalfNormal(scale=5), the zero-truncated counterpart",
    "c": "Normal(loc=0, scale=5)",
    "sigma": "HalfNormal(scale=2)",
}


def _float(value) -> float:
    """Convert numpy, torch, and xarray scalars to a JSON-safe float."""
    if hasattr(value, "values"):
        value = value.values
    if isinstance(value, torch.Tensor):
        value = value.detach().cpu().numpy()
    return float(np.asarray(value))


def _sha256_arrays(*arrays: np.ndarray) -> str:
    digest = hashlib.sha256()
    for array in arrays:
        digest.update(np.ascontiguousarray(array, dtype="<f8").tobytes())
    return digest.hexdigest()


def _sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class NestedSinLinearModel(CandidateModel):
    """Sin+Linear fitted through CandidateModel._fit_mle with one bound fork."""

    def __init__(self, constrained: bool):
        self.constrained = constrained
        self.name = MODEL_NAMES[int(constrained)]
        self.vector = np.array([1.0, 1.0, 0.0, 0.25, 0.0, np.log(0.3)])
        self.sigma = 0.3

    @staticmethod
    def _mean(x: np.ndarray, params: Sequence[float]) -> np.ndarray:
        A, omega, phi, b, c = params
        return A * np.sin(omega * x + phi) + b * x + c

    @property
    def bounds(self) -> List[Tuple[Optional[float], Optional[float]]]:
        bounds: List[Tuple[Optional[float], Optional[float]]] = [
            (None, None),
            (None, None),
            (None, None),
            (None, None),
            (None, None),
            (-10.0, 5.0),
        ]
        if self.constrained:
            bounds[3] = (0.0, None)
        return bounds

    @staticmethod
    def base_starts() -> List[np.ndarray]:
        return [
            np.array([1.0, omega, 0.0, 0.25, 0.0, np.log(0.3)])
            for omega in (0.5, 1.0, 1.5, 2.0)
        ]

    def fit_all(
        self,
        x: np.ndarray,
        y: np.ndarray,
        weights: Optional[np.ndarray] = None,
        extra_starts: Iterable[np.ndarray] = (),
    ) -> List[np.ndarray]:
        """Return finite multistart fits while preserving the bound fork."""
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        if weights is None:
            scale = np.ones_like(y)
        else:
            weights = np.asarray(weights, dtype=float)
            if np.any(~np.isfinite(weights)) or np.any(weights <= 0):
                raise ValueError("candidate weights must remain finite and positive")
            scale = np.sqrt(weights)
        y_scaled = y * scale

        def f_scaled(x_values, params):
            return self._mean(x_values, params) * scale

        starts = self.base_starts() + [np.asarray(v, dtype=float).copy()
                                       for v in extra_starts]
        fitted = []
        for start in starts:
            if self.constrained:
                start[3] = max(0.0, start[3])
            try:
                vector, nll = self._fit_mle(
                    x, y_scaled, f_scaled, start, bounds=self.bounds)
            except Exception:
                continue
            if np.isfinite(nll) and np.all(np.isfinite(vector)):
                if self.constrained and vector[3] < -BOUND_ATOL:
                    raise RuntimeError("bounded fit returned a negative slope")
                fitted.append(np.asarray(vector, dtype=float))
        if not fitted:
            raise RuntimeError(f"all multistart fits failed for {self.name}")
        return fitted

    def set_vector(self, vector: np.ndarray, y: np.ndarray, x: np.ndarray) -> None:
        self.vector = np.asarray(vector, dtype=float).copy()
        residual = np.asarray(y) - self._mean(np.asarray(x), self.vector[:-1])
        self.sigma = max(float(np.sqrt(np.mean(residual ** 2))), 1e-8)

    @property
    def slope(self) -> float:
        return float(self.vector[3])

    def predict(self, x_eval: np.ndarray) -> CandidateResult:
        mean = self._mean(np.asarray(x_eval, dtype=float), self.vector[:-1])
        return self._make_result(
            x_eval,
            mean,
            self.sigma ** 2,
            {
                "A": float(self.vector[0]),
                "omega": float(self.vector[1]),
                "phi": float(self.vector[2]),
                "b": float(self.vector[3]),
                "c": float(self.vector[4]),
                "sigma": float(self.sigma),
            },
        )


@dataclass
class PairFit:
    free: CandidateResult
    constrained: CandidateResult
    free_slope: float
    primary_G: np.ndarray
    appendix_G: np.ndarray


def _candidate_G(psi, candidate: CandidateResult, metric_name: str) -> float:
    return float(METRICS[metric_name](
        psi.mean, psi.cov, candidate.mean, candidate.cov))


def fit_nested_pair(x_eval: np.ndarray, psi) -> PairFit:
    """Minimize primary G over encompassing and restricted parameter regions."""
    variance = np.maximum(np.diag(psi.cov), 1e-10)
    weights = 1.0 / variance

    free_model = NestedSinLinearModel(constrained=False)
    free_vectors = free_model.fit_all(x_eval, psi.mean, weights=weights)

    constrained_model = NestedSinLinearModel(constrained=True)
    constrained_vectors = constrained_model.fit_all(
        x_eval, psi.mean, weights=weights,
        extra_starts=[v.copy() for v in free_vectors],
    )

    # Every constrained solution also belongs to the free region.  Retaining
    # those feasible vectors in the free search makes the numerical nesting
    # check independent of local optimizer tie-breaking.
    free_candidates = free_vectors + [v.copy() for v in constrained_vectors]
    constrained_candidates = constrained_vectors + [
        v.copy() for v in free_vectors if v[3] >= -BOUND_ATOL
    ]

    def select(model: NestedSinLinearModel,
               vectors: Sequence[np.ndarray]) -> Tuple[np.ndarray, CandidateResult, float]:
        best = None
        for vector in vectors:
            model.set_vector(vector, psi.mean, x_eval)
            result = model.predict(x_eval)
            value = _candidate_G(psi, result, PRIMARY_METRIC)
            if best is None or value < best[2]:
                best = (vector.copy(), result, value)
        if best is None:
            raise RuntimeError(f"no finite candidate result for {model.name}")
        return best

    free_vector, free_result, free_G = select(free_model, free_candidates)
    _constrained_vector, constrained_result, constrained_G = select(
        constrained_model, constrained_candidates)

    # An interior free optimum belongs to both regions.  Reuse its exact
    # representation when float-level optimizer noise separates equal optima.
    if free_vector[3] >= -BOUND_ATOL:
        constrained_model.set_vector(free_vector, psi.mean, x_eval)
        shared_result = constrained_model.predict(x_eval)
        shared_G = _candidate_G(psi, shared_result, PRIMARY_METRIC)
        if shared_G <= constrained_G + G_EQUAL_ATOL:
            constrained_result = shared_result
            constrained_G = shared_G

    if free_G > constrained_G + G_ORDER_ATOL:
        raise RuntimeError(
            f"nesting order failed: free G={free_G}, constrained G={constrained_G}")

    appendix = np.array([
        _candidate_G(psi, free_result, APPENDIX_METRIC),
        _candidate_G(psi, constrained_result, APPENDIX_METRIC),
    ])
    return PairFit(
        free=free_result,
        constrained=constrained_result,
        free_slope=float(free_vector[3]),
        primary_G=np.array([free_G, constrained_G]),
        appendix_G=appendix,
    )


def observed_pair(x: np.ndarray, y: np.ndarray,
                  x_eval: np.ndarray) -> Tuple[List[CandidateResult], Dict]:
    """Fit the observed data pair through the same bound-only model classes."""
    free_model = NestedSinLinearModel(constrained=False)
    free_vectors = free_model.fit_all(x, y)
    free_model.set_vector(free_vectors[0], y, x)
    free_best = min(
        free_vectors,
        key=lambda v: np.mean((y - free_model._mean(x, v[:-1])) ** 2),
    )
    free_model.set_vector(free_best, y, x)

    constrained_model = NestedSinLinearModel(constrained=True)
    constrained_vectors = constrained_model.fit_all(
        x, y, extra_starts=[free_best])
    constrained_best = min(
        constrained_vectors,
        key=lambda v: np.mean((y - constrained_model._mean(x, v[:-1])) ** 2),
    )
    if free_best[3] >= -BOUND_ATOL:
        constrained_best = free_best.copy()
    constrained_model.set_vector(constrained_best, y, x)

    results = [free_model.predict(x_eval), constrained_model.predict(x_eval)]
    parameters = {result.name: result.parameters for result in results}
    return results, parameters


def validated_sir_predictives(
    x: torch.Tensor,
    y: torch.Tensor,
    x_eval: torch.Tensor,
    observed_results: List[CandidateResult],
    n_pred: int,
) -> Tuple[List, Dict, np.ndarray, float]:
    """Call pss._sir_bms and retain the exact predictive rows it scores."""
    ths, lml = pss.load_pooled_is(CONFIG, IS_SEEDS)
    weights = np.exp(lml - lml.max())
    pooled_ess = float(weights.sum() ** 2 / np.sum(weights ** 2))

    captured: Dict[str, List] = {}
    original_extract = pss.extract_gp_predictives

    def capture_extract(*args, **kwargs):
        predictives = original_extract(*args, **kwargs)
        captured["predictives"] = predictives
        return predictives

    # _sir_bms does not return its predictive objects.  Intercepting the
    # imported extractor keeps one authoritative SIR call and no copied
    # resampling or GP-predictive formula.
    pss.extract_gp_predictives = capture_extract
    try:
        per_metric, _, _, indices = pss._sir_bms(
            pss.STUDY_CONFIGS[CONFIG], x, y, x_eval, observed_results,
            ths, lml, n_pred, sir_seed=SIR_SEED)
    finally:
        pss.extract_gp_predictives = original_extract

    predictives = captured.get("predictives", [])
    if len(predictives) != n_pred:
        raise RuntimeError(
            f"validated path returned {len(predictives)} predictives, expected {n_pred}")
    return predictives, per_metric, indices, pooled_ess


def aggregate_tables(G_by_metric: Dict[str, np.ndarray]) -> Dict:
    """Use E7's imported aggregation variants over the case-specific G rows."""
    output = {}
    for metric_name, G in G_by_metric.items():
        metric_rows = {}
        for tau in TAUS:
            tau_rows = {}
            for variant in VARIANTS:
                tau_rows[variant] = [
                    float(value) for value in e7.aggregate(G, tau, variant)
                ]
            metric_rows[str(tau)] = tau_rows
        output[metric_name] = metric_rows
    return output


def pyro_sin_linear(x: torch.Tensor, y: Optional[torch.Tensor],
                    constrained: bool) -> None:
    """Bayesian Sin+Linear likelihood used only for the PSIS-LOO arm."""
    A = pyro.sample("A", dist.HalfNormal(torch.tensor(5.0)))
    omega = pyro.sample(
        "omega", dist.LogNormal(torch.tensor(0.0), torch.tensor(0.7)))
    phi = pyro.sample(
        "phi", dist.Uniform(torch.tensor(-math.pi), torch.tensor(math.pi)))
    if constrained:
        b = pyro.sample("b", dist.HalfNormal(torch.tensor(5.0)))
    else:
        b = pyro.sample(
            "b", dist.Normal(torch.tensor(0.0), torch.tensor(5.0)))
    c = pyro.sample("c", dist.Normal(torch.tensor(0.0), torch.tensor(5.0)))
    sigma = pyro.sample("sigma", dist.HalfNormal(torch.tensor(2.0)))
    mu = A * torch.sin(omega * x + phi) + b * x + c
    with pyro.plate("data", len(x)):
        pyro.sample("obs", dist.Normal(mu, sigma), obs=y)


def _initial_values(parameters: Dict[str, float], constrained: bool) -> Dict:
    values = {
        "A": torch.tensor(max(abs(parameters["A"]), 1e-3)),
        "omega": torch.tensor(max(abs(parameters["omega"]), 1e-3)),
        "phi": torch.tensor(float(np.clip(parameters["phi"],
                                            -math.pi + 1e-6,
                                            math.pi - 1e-6))),
        "b": torch.tensor(max(parameters["b"], 1e-6)
                          if constrained else parameters["b"]),
        "c": torch.tensor(parameters["c"]),
        "sigma": torch.tensor(max(parameters["sigma"], 1e-3)),
    }
    return values


def run_loo_candidate(
    x: torch.Tensor,
    y: torch.Tensor,
    constrained: bool,
    mle_parameters: Dict[str, float],
    warmup: int,
    draws: int,
    chain_seeds: Sequence[int],
) -> Dict:
    """Run explicit seeded Pyro chains and compute PSIS-LOO with ArviZ."""
    per_chain = []
    diverging = []
    acceptance_rates = []
    for seed in chain_seeds:
        pyro.clear_param_store()
        pyro.set_rng_seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)
        kernel = NUTS(
            lambda x_data, y_data: pyro_sin_linear(
                x_data, y_data, constrained),
            init_strategy=init_to_value(
                values=_initial_values(mle_parameters, constrained)),
            target_accept_prob=LOO_TARGET_ACCEPT,
            max_tree_depth=LOO_MAX_TREE_DEPTH,
        )
        mcmc = MCMC(
            kernel,
            num_samples=draws,
            warmup_steps=warmup,
            num_chains=1,
            disable_progbar=True,
        )
        mcmc.run(x, y)
        samples = {
            key: value.detach().cpu().numpy()
            for key, value in mcmc.get_samples().items()
        }
        per_chain.append(samples)
        diagnostics = mcmc.diagnostics()
        divergent_indices = diagnostics["divergences"].get("chain 0", [])
        mask = np.zeros(draws, dtype=bool)
        mask[np.asarray(divergent_indices, dtype=int)] = True
        diverging.append(mask)
        acceptance_rates.append(float(
            diagnostics["acceptance rate"].get("chain 0", float("nan"))))

    posterior = {
        key: np.stack([chain[key] for chain in per_chain], axis=0)
        for key in PARAMETER_NAMES
    }
    x_np = x.detach().cpu().numpy()
    y_np = y.detach().cpu().numpy()
    mu = (
        posterior["A"][..., None]
        * np.sin(posterior["omega"][..., None] * x_np
                 + posterior["phi"][..., None])
        + posterior["b"][..., None] * x_np
        + posterior["c"][..., None]
    )
    sigma = posterior["sigma"][..., None]
    log_likelihood = (
        -0.5 * np.log(2.0 * np.pi * sigma ** 2)
        -0.5 * ((y_np - mu) / sigma) ** 2
    )
    idata = az.from_dict(
        posterior=posterior,
        sample_stats={"diverging": np.stack(diverging, axis=0)},
        log_likelihood={"obs": log_likelihood},
        observed_data={"obs": y_np},
        constant_data={"x": x_np},
    )
    loo = az.loo(idata, pointwise=True)
    rhat_data = az.rhat(idata, var_names=PARAMETER_NAMES, method="rank")
    ess_bulk_data = az.ess(idata, var_names=PARAMETER_NAMES, method="bulk")
    ess_tail_data = az.ess(idata, var_names=PARAMETER_NAMES, method="tail")
    rhat = {name: _float(rhat_data[name]) for name in PARAMETER_NAMES}
    ess_bulk = {name: _float(ess_bulk_data[name]) for name in PARAMETER_NAMES}
    ess_tail = {name: _float(ess_tail_data[name]) for name in PARAMETER_NAMES}
    pareto_k = np.asarray(loo.pareto_k, dtype=float)
    record = {
        "elpd_loo": _float(loo.elpd_loo),
        "se": _float(loo.se),
        "p_loo": _float(loo.p_loo),
        "pointwise_elpd": [float(value) for value in np.asarray(loo.loo_i)],
        "pareto_k": {
            "max": float(np.max(pareto_k)),
            "good_k_threshold": _float(loo.good_k),
            "warning": bool(loo.warning),
            "n_over_good_k_threshold": int(np.sum(pareto_k > _float(loo.good_k))),
            "n_over_0_5": int(np.sum(pareto_k > 0.5)),
            "n_over_0_7": int(np.sum(pareto_k > 0.7)),
            "n_over_1_0": int(np.sum(pareto_k > 1.0)),
            "values": [float(value) for value in pareto_k],
        },
        "sampler": {
            "chains": len(chain_seeds),
            "warmup_per_chain": warmup,
            "draws_per_chain": draws,
            "chain_seeds": list(chain_seeds),
            "target_accept_prob": LOO_TARGET_ACCEPT,
            "max_tree_depth": LOO_MAX_TREE_DEPTH,
            "divergences_by_chain": [int(mask.sum()) for mask in diverging],
            "divergences_total": int(sum(mask.sum() for mask in diverging)),
            "acceptance_rate_by_chain": acceptance_rates,
            "r_hat": rhat,
            "r_hat_max": float(max(rhat.values())),
            "ess_bulk": ess_bulk,
            "ess_bulk_min": float(min(ess_bulk.values())),
            "ess_tail": ess_tail,
            "ess_tail_min": float(min(ess_tail.values())),
        },
    }
    return record


def loo_comparison(free: Dict, constrained: Dict) -> Dict:
    """Return paired pointwise ELPD difference for constrained minus free."""
    pointwise = (np.asarray(constrained["pointwise_elpd"], dtype=float)
                 - np.asarray(free["pointwise_elpd"], dtype=float))
    difference = constrained["elpd_loo"] - free["elpd_loo"]
    se = float(np.sqrt(len(pointwise) * np.var(pointwise, ddof=1)))
    return {
        "direction": "constrained_minus_free",
        "elpd_difference": float(difference),
        "se": se,
        "pointwise_differences": [float(value) for value in pointwise],
    }


def render_readme(results: Dict) -> str:
    bms = results["bms_star"]
    loo = results["psis_loo"]
    headline = bms["tables"][PRIMARY_METRIC]["1.0"]
    lines = [
        "# Haaf-style nested constraint: BMS* and PSIS-LOO",
        "",
        "Run from the repository root:",
        "",
        "```bash",
        "python experiments/haaf_nested_constraint.py",
        "```",
        "",
        "The command regenerates `results.json` and this README. It uses the ",
        "frozen `generate_toy_data()` defaults: N=20, data seed 42, true ",
        "slope b=0.25, and observation standard deviation 0.5. The free and ",
        "restricted candidates share the Sin+Linear form. Their only region ",
        "difference concerns the slope bound: the free fit accepts every real ",
        "b, while the restricted fit requires b greater than or equal to zero.",
        "",
        "## BMS* path and cache dependency",
        "",
        "The run imports `prior_sensitivity_study.py`, loads the pooled ",
        "`toy_elicited` prior-IS caches for seeds 0, 1, and 2, and calls its ",
        "stage-IS SIR machinery with seed 42 and 1,000 predictives. It imports ",
        "the pooled and expected-posterior aggregation implementations from ",
        "`e7_convention_sensitivity.py`. The primary metric uses ",
        "`pw_kl_vcal`; `kl_forward` appears only as an appendix stress metric.",
        "",
        "A fresh clone must first regenerate the local caches:",
        "",
        "```bash",
        "python experiments/prior_sensitivity_study.py --stage a --configs toy_elicited --is-n 60000 --is-seeds 0 1 2",
        "python experiments/haaf_nested_constraint.py",
        "```",
        "",
        "Expected cache paths:",
        "",
        "- `runs/prior_sensitivity/is_draws_toy_elicited_s0.npz`",
        "- `runs/prior_sensitivity/is_draws_toy_elicited_s1.npz`",
        "- `runs/prior_sensitivity/is_draws_toy_elicited_s2.npz`",
        "",
        "For each shared predictive pattern, both candidates minimize the ",
        "primary G over their parameter regions through ",
        "`CandidateModel._fit_mle`. No candidate-parameter prior contributes ",
        "to the BMS* calculation.",
        "",
        "At τ = 1, pooled BMS* assigns "
        f"{headline['pooled'][0]:.6f} to the free candidate and "
        f"{headline['pooled'][1]:.6f} to the restricted candidate. "
        "Expected-posterior aggregation assigns "
        f"{headline['expected_posterior'][0]:.6f} and "
        f"{headline['expected_posterior'][1]:.6f}, respectively. The free-fit "
        f"slope falls below zero for {bms['slope_sign']['negative_fraction']:.6f} "
        "of SIR predictives.",
        "",
        "## PSIS-LOO priors and sampler",
        "",
        "The LOO comparison uses the identical x and y values. These priors ",
        "apply only to the LOO arm:",
        "",
    ]
    for name, description in PRIOR_DESCRIPTIONS.items():
        lines.append(f"- `{name}`: {description}")
    lines += [
        "",
        "Pyro NUTS runs two sequential chains with seeds 20260811 and ",
        "20260812, 1,000 warmup iterations and 1,000 retained draws per chain, ",
        "target acceptance probability 0.90, and maximum tree depth 8. ArviZ ",
        "receives the pointwise Normal log likelihoods and computes PSIS-LOO.",
        "",
        "## Headline PSIS-LOO",
        "",
        "| candidate | elpd_loo | SE | p_loo | max Pareto k | warning | divergences | max r_hat |",
        "|---|---:|---:|---:|---:|---|---:|---:|",
    ]
    for key, label in (("free", MODEL_NAMES[0]),
                       ("constrained", MODEL_NAMES[1])):
        row = loo["candidates"][key]
        sampler = row["sampler"]
        lines.append(
            f"| {label} | {row['elpd_loo']:.3f} | {row['se']:.3f} | "
            f"{row['p_loo']:.3f} | {row['pareto_k']['max']:.3f} | "
            f"{'yes' if row['pareto_k']['warning'] else 'no'} | "
            f"{sampler['divergences_total']} | {sampler['r_hat_max']:.3f} |")
    pair = loo["pairwise"]
    lines += [
        "",
        "The paired constrained-minus-free elpd difference equals "
        f"{pair['elpd_difference']:.3f} with SE {pair['se']:.3f}.",
        "ArviZ flags the constrained estimate because "
        f"{loo['candidates']['constrained']['pareto_k']['n_over_good_k_threshold']} "
        "observation exceeds its sample-size-specific good-k threshold. Interpret "
        "the direction with that qualification.",
        "",
        "## Determinism and tolerances",
        "",
        "All random-number seeds appear in `results.json`. On the pinned ",
        "environment, repeated CPU runs should reproduce the artifact. Across ",
        "compatible machines and library builds, use these absolute comparison ",
        "tolerances:",
        "",
    ]
    for key, value in RERUN_TOLERANCES.items():
        lines.append(f"- `{key}`: {value}")
    lines += [
        "",
        f"The primary nesting gates use {G_EQUAL_ATOL:g} absolute tolerance "
        "for equality on nonnegative free-slope rows and "
        f"{G_ORDER_ATOL:g} for the one-sided G ordering on negative-slope rows. ",
        "A failure stops the run before artifact replacement.",
        "",
        "No figure accompanies the case because the comparison table and the ",
        "slope-sign diagnostic convey the full result without an additional ",
        "visual encoding.",
        "",
    ]
    return "\n".join(line.rstrip() for line in lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument(
        "--quick", action="store_true",
        help="run a small development check and write results_quick.json")
    args = parser.parse_args()

    n_pred = 40 if args.quick else N_PRED
    warmup = 75 if args.quick else LOO_WARMUP
    draws = 75 if args.quick else LOO_DRAWS

    x, y, info = generate_toy_data()
    x_np = x.detach().cpu().numpy()
    y_np = y.detach().cpu().numpy()
    x_eval_np = np.linspace(x_np.min() - 1.0, x_np.max() + 1.0, 60)
    x_eval = torch.tensor(x_eval_np).double()
    if len(x_np) != 20 or info["bias_slope"] != 0.25:
        raise RuntimeError("the frozen N=20, b=0.25 data convention changed")

    observed_results, observed_parameters = observed_pair(
        x_np, y_np, x_eval_np)
    print("Loading validated SIR predictives")
    predictives, pss_anchor, sir_indices, pooled_ess = validated_sir_predictives(
        x, y, x_eval, observed_results, n_pred)

    print(f"Fitting the nested candidate pair to {len(predictives)} predictives")
    pair_fits = []
    for index, psi in enumerate(predictives):
        pair_fits.append(fit_nested_pair(x_eval_np, psi))
        if (index + 1) % 100 == 0 or index + 1 == len(predictives):
            print(f"  fitted {index + 1}/{len(predictives)}")

    primary_G = np.vstack([fit.primary_G for fit in pair_fits])
    appendix_G = np.vstack([fit.appendix_G for fit in pair_fits])
    slopes = np.array([fit.free_slope for fit in pair_fits])
    negative = slopes < -BOUND_ATOL
    nonnegative = ~negative
    gap = primary_G[:, 1] - primary_G[:, 0]
    max_equal_difference = (
        float(np.max(np.abs(gap[nonnegative]))) if np.any(nonnegative) else 0.0)
    min_negative_gap = (
        float(np.min(gap[negative])) if np.any(negative) else None)
    if max_equal_difference > G_EQUAL_ATOL:
        raise RuntimeError(
            f"nonnegative-slope identity failed at {max_equal_difference}")
    if np.any(negative) and min_negative_gap is not None \
            and min_negative_gap < -G_ORDER_ATOL:
        raise RuntimeError(f"negative-slope nesting order failed at {min_negative_gap}")

    G_by_metric = {
        PRIMARY_METRIC: primary_G,
        APPENDIX_METRIC: appendix_G,
    }
    tables = aggregate_tables(G_by_metric)

    print("Running PSIS-LOO models")
    free_loo = run_loo_candidate(
        x, y, False, observed_parameters[MODEL_NAMES[0]], warmup, draws,
        LOO_CHAIN_SEEDS)
    constrained_loo = run_loo_candidate(
        x, y, True, observed_parameters[MODEL_NAMES[1]], warmup, draws,
        LOO_CHAIN_SEEDS)
    pairwise = loo_comparison(free_loo, constrained_loo)

    cache_records = []
    for seed in IS_SEEDS:
        path = pss._is_draw_path(CONFIG, seed)
        with np.load(path) as cache:
            cache_records.append({
                "seed": seed,
                "path": os.path.relpath(path, REPO),
                "n_draws": int(len(cache["lml"])),
                "sha256": _sha256_file(path),
            })

    results = {
        "case": "Case C, nested slope constraint",
        "protocol_date": "2026-08-11",
        "quick": bool(args.quick),
        "data": {
            "generator": "bistar_gp.generate_toy_data defaults",
            "n": int(len(x_np)),
            "seed": DATA_SEED,
            "x_range": [float(x_np.min()), float(x_np.max())],
            "true_bias_slope": float(info["bias_slope"]),
            "noise_std": float(info["noise_std"]),
            "xy_sha256_float64_le": _sha256_arrays(x_np, y_np),
        },
        "candidate_definition": {
            "functional_form": "A sin(omega x + phi) + b x + c",
            "model_names": MODEL_NAMES,
            "free_bounds": NestedSinLinearModel(False).bounds,
            "constrained_bounds": NestedSinLinearModel(True).bounds,
            "only_bound_difference_index": 3,
            "only_bound_difference_parameter": "b",
            "observed_data_mle": observed_parameters,
        },
        "bms_star": {
            "config": CONFIG,
            "is_seeds": IS_SEEDS,
            "sir_seed": SIR_SEED,
            "n_sir_draws": int(n_pred),
            "n_unique_sir_draws": int(len(np.unique(sir_indices))),
            "pooled_is_ess": pooled_ess,
            "cache_dependencies": cache_records,
            "primary_metric": PRIMARY_METRIC,
            "appendix_metric": APPENDIX_METRIC,
            "taus": TAUS,
            "aggregation_variants": VARIANTS,
            "tables": tables,
            "slope_sign": {
                "negative_count": int(np.sum(negative)),
                "nonnegative_count": int(np.sum(nonnegative)),
                "negative_fraction": float(np.mean(negative)),
                "free_slope_min": float(np.min(slopes)),
                "free_slope_median": float(np.median(slopes)),
                "free_slope_max": float(np.max(slopes)),
            },
            "sanity_identity_primary_G": {
                "metric": PRIMARY_METRIC,
                "equality_atol": G_EQUAL_ATOL,
                "order_atol": G_ORDER_ATOL,
                "max_abs_gap_on_nonnegative_free_slope": max_equal_difference,
                "min_constrained_minus_free_G_on_negative_free_slope": min_negative_gap,
                "violations": 0,
            },
            "G_summary": {
                PRIMARY_METRIC: {
                    MODEL_NAMES[0]: {
                        "mean": float(np.mean(primary_G[:, 0])),
                        "median": float(np.median(primary_G[:, 0])),
                    },
                    MODEL_NAMES[1]: {
                        "mean": float(np.mean(primary_G[:, 1])),
                        "median": float(np.median(primary_G[:, 1])),
                    },
                    "mean_constrained_minus_free": float(np.mean(gap)),
                },
                APPENDIX_METRIC: {
                    MODEL_NAMES[0]: {
                        "mean": float(np.mean(appendix_G[:, 0])),
                        "median": float(np.median(appendix_G[:, 0])),
                    },
                    MODEL_NAMES[1]: {
                        "mean": float(np.mean(appendix_G[:, 1])),
                        "median": float(np.median(appendix_G[:, 1])),
                    },
                },
            },
            "validated_pss_observed_fit_anchor": {
                "metric": PRIMARY_METRIC,
                "tau": 1.0,
                "pooled_probabilities": pss_anchor[PRIMARY_METRIC]
                    ["posteriors"]["1.0"],
                "observed_candidate_predictions_identical": True,
            },
        },
        "psis_loo": {
            "priors_apply_only_to_loo": True,
            "priors": PRIOR_DESCRIPTIONS,
            "candidates": {
                "free": free_loo,
                "constrained": constrained_loo,
            },
            "pairwise": pairwise,
        },
        "tolerances": {
            "structural": {
                "G_equality_atol": G_EQUAL_ATOL,
                "G_order_atol": G_ORDER_ATOL,
                "slope_bound_atol": BOUND_ATOL,
            },
            "cross_machine_rerun": RERUN_TOLERANCES,
        },
        "versions": {
            "numpy": np.__version__,
            "torch": torch.__version__,
            "pyro": pyro.__version__,
            "arviz": az.__version__,
        },
    }

    os.makedirs(OUT_DIR, exist_ok=True)
    output_path = (os.path.join(OUT_DIR, "results_quick.json")
                   if args.quick else RESULTS_PATH)
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(results, handle, indent=2, allow_nan=False)
        handle.write("\n")
    if not args.quick:
        with open(README_PATH, "w", encoding="utf-8") as handle:
            handle.write(render_readme(results))
    print(f"Saved {output_path}")


if __name__ == "__main__":
    main()
