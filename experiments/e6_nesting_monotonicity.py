#!/usr/bin/env python3
"""Run the Case B E6 nesting and finite-τ ordering check.

The script uses the existing multi-start Ḡ optimizer and defensive-mixture IS
implementation. It tests exact Linear and Sinusoidal restrictions inside an
encompassing Sin+Linear parameter space, then computes both reference-measure
conventions over one shared τ grid.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
VIZ_SCRIPTS = REPO_ROOT / "bistar_viz" / "scripts"
EXPERIMENTS = REPO_ROOT / "experiments"
for import_path in (VIZ_SCRIPTS, EXPERIMENTS):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

import _viz_spaces as V  # noqa: E402
from bistar_gp.bms_star import METRICS  # noqa: E402
from bistar_gp.induced_prior import ModelParameterSpace, ParameterSpec  # noqa: E402
from bistar_gp.laplace_evidence import (  # noqa: E402
    _log_reference_volume,
    _multistart_G_optima,
    compute_G_at_params,
    is_log_Z_Mx,
)
from occam_dial_figure import (  # noqa: E402
    DATA_SEED,
    DEFAULT_OUT_DIR,
    IS_SEED,
    MODEL_NAMES,
    N_DRAWS,
    N_PERTURB,
    build_map_gp,
    write_combined_readme,
)


N_IS = 100_000
TAUS = np.logspace(-1.5, 2.5, 161)
MIN_G_TOLERANCE = 1e-8
EMBEDDING_TOLERANCE = 1e-10


def _native(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _native(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_native(v) for v in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.floating, np.integer, np.bool_)):
        return value.item()
    return value


def _exact_encompassing_space() -> ModelParameterSpace:
    """Match canonical bounds while including the exact A=0 boundary."""
    return ModelParameterSpace(
        model_name="Sin+Linear",
        param_specs=[
            ParameterSpec("A", (0.0, 5.0), None),
            ParameterSpec("omega", (0.1, 5.0), None),
            ParameterSpec("phi", (-np.pi, np.pi), None),
            ParameterSpec("b", (-2.0, 2.0), None),
            ParameterSpec("c", (-5.0, 5.0), None),
        ],
        predict_fn=lambda x, p: (
            p["A"] * np.sin(p["omega"] * x + p["phi"])
            + p["b"] * x
            + p["c"]
        ),
        noise_param="sigma",
    )


def _best_optimum(param_space, x_eval, avg_gp, starts):
    optima = _multistart_G_optima(
        param_space,
        x_eval,
        avg_gp,
        METRICS["pw_kl_vcal"],
        starts,
    )
    best = min(optima, key=lambda item: item[1])
    return optima, best


def _parameter_dict(param_space, vector) -> dict[str, float]:
    return {
        spec.name: float(value)
        for spec, value in zip(param_space.param_specs, vector)
    }


def _crossings(taus: np.ndarray, delta: np.ndarray) -> list[dict[str, Any]]:
    found = []
    for index in range(len(taus) - 1):
        left, right = float(delta[index]), float(delta[index + 1])
        if left == 0.0:
            estimate = float(taus[index])
        elif left * right > 0.0:
            continue
        else:
            log_left, log_right = np.log10(taus[index : index + 2])
            estimate = float(
                10.0 ** (log_left - left * (log_right - log_left) / (right - left))
            )
        found.append(
            {
                "lower_grid_index": index,
                "tau_bracket": [float(taus[index]), float(taus[index + 1])],
                "delta_log_Z_bracket": [left, right],
                "tau_log_interpolated": estimate,
                "winner_below": "encompassing" if left > 0.0 else "restricted",
                "winner_above": "encompassing" if right > 0.0 else "restricted",
            }
        )
    return found


def _ordering_summary(
    taus: np.ndarray,
    encompassing_log_z: np.ndarray,
    restricted_log_z: np.ndarray,
) -> dict[str, Any]:
    delta = encompassing_log_z - restricted_log_z
    crossings = _crossings(taus, delta)
    return {
        "delta_definition": "log Z_M(encompassing) - log Z_M(restricted)",
        "delta_log_Z": delta,
        "crossings": crossings,
        "winner_at_tau_min": "encompassing" if delta[0] > 0.0 else "restricted",
        "winner_at_tau_max": "encompassing" if delta[-1] > 0.0 else "restricted",
        "delta_at_tau_min": float(delta[0]),
        "delta_at_tau_max": float(delta[-1]),
        "minimum_absolute_delta_grid_point": {
            "tau": float(taus[int(np.argmin(np.abs(delta)))]),
            "delta_log_Z": float(delta[int(np.argmin(np.abs(delta)))]),
        },
    }


def run(out_dir: Path, *, n_is: int) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    x_eval, _x_50, _y_50, avg_gp, retained = build_map_gp()
    canonical = V.canonical_spaces()
    encompassing = _exact_encompassing_space()

    starts = {
        name: V.perturbed_starts(
            name, canonical, N_PERTURB, seed=DATA_SEED
        )
        for name in MODEL_NAMES
    }
    linear_optima, linear_best = _best_optimum(
        canonical["Linear"], x_eval, avg_gp, starts["Linear"]
    )
    sinusoidal_optima, sinusoidal_best = _best_optimum(
        canonical["Sinusoidal"], x_eval, avg_gp, starts["Sinusoidal"]
    )

    linear_phi = _parameter_dict(canonical["Linear"], linear_best[0])
    sinusoidal_phi = _parameter_dict(
        canonical["Sinusoidal"], sinusoidal_best[0]
    )
    linear_embedding = {
        "A": 0.0,
        "omega": 1.0,
        "phi": 0.0,
        "b": linear_phi["a"],
        "c": linear_phi["b"],
    }
    sinusoidal_embedding = {
        "A": sinusoidal_phi["A"],
        "omega": sinusoidal_phi["omega"],
        "phi": sinusoidal_phi["phi"],
        "b": 0.0,
        "c": 0.0,
    }
    encompassing_starts = [dict(start) for start in starts["Sin+Linear"]]
    encompassing_starts.extend([linear_embedding, sinusoidal_embedding])
    encompassing_optima, encompassing_best = _best_optimum(
        encompassing, x_eval, avg_gp, encompassing_starts
    )
    encompassing_phi = _parameter_dict(encompassing, encompassing_best[0])

    metric = METRICS["pw_kl_vcal"]
    linear_g_embedded = float(
        compute_G_at_params(
            linear_embedding, encompassing, x_eval, avg_gp, metric
        )
    )
    sinusoidal_g_embedded = float(
        compute_G_at_params(
            sinusoidal_embedding, encompassing, x_eval, avg_gp, metric
        )
    )
    linear_embedding_error = abs(linear_g_embedded - float(linear_best[1]))
    sinusoidal_embedding_error = abs(
        sinusoidal_g_embedded - float(sinusoidal_best[1])
    )
    if linear_embedding_error > EMBEDDING_TOLERANCE:
        raise AssertionError(
            f"Linear embedding changes Ḡ by {linear_embedding_error}"
        )
    if sinusoidal_embedding_error > EMBEDDING_TOLERANCE:
        raise AssertionError(
            f"Sinusoidal embedding changes Ḡ by {sinusoidal_embedding_error}"
        )

    spaces = {
        "Linear": canonical["Linear"],
        "Sinusoidal": canonical["Sinusoidal"],
        "Sin+Linear": encompassing,
    }
    starts_by_model = {
        "Linear": starts["Linear"],
        "Sinusoidal": starts["Sinusoidal"],
        # Exact boundary embeddings guarantee the optimization inequality but
        # create flat omega/phi Hessian directions at A=0. The IS proposal
        # instead uses interior starts plus the best encompassing optimum.
        "Sin+Linear": starts["Sin+Linear"] + [encompassing_phi],
    }
    sweeps: dict[str, dict[str, Any]] = {}
    for name, param_space in spaces.items():
        # One package IS call computes the full τ sweep. The package's
        # reference-volume helper then applies the documented occam variant.
        # NumPy 2 on Accelerate can emit spurious matmul floating warnings for
        # the large proposal draw even when every returned diagnostic remains
        # finite, so the scoped errstate accompanies explicit finiteness checks.
        with np.errstate(divide="ignore", over="ignore", invalid="ignore"):
            result = is_log_Z_Mx(
                param_space,
                x_eval,
                avg_gp,
                TAUS,
                n_is=n_is,
                seed=IS_SEED,
                starts=starts_by_model[name],
                metric_name="pw_kl_vcal",
                occam=False,
            )
        if not np.all(np.isfinite(result.log_Z)) or not np.all(
            np.isfinite(result.ess)
        ):
            raise AssertionError(f"non-finite IS result for {name}")
        log_volume = float(_log_reference_volume(param_space))
        normalized_log_z = result.log_Z - log_volume
        sweeps[name] = {
            "occam_false": {
                "log_Z_M": result.log_Z,
                "ess": result.ess,
                "min_ess": float(np.min(result.ess)),
            },
            "occam_true": {
                "log_Z_M": normalized_log_z,
                "ess": result.ess,
                "min_ess": float(np.min(result.ess)),
                "derived_from_raw_with": (
                    "bistar_gp.laplace_evidence._log_reference_volume"
                ),
            },
            "log_reference_volume": log_volume,
            "is_calls": 1,
        }

    pair_inputs = {
        "Linear_within_Sin+Linear": {
            "restricted_name": "Linear",
            "restriction": "A=0; encompassing b and c equal restricted a and b",
            "restricted_best": linear_best,
            "restricted_phi": linear_phi,
            "embedded_phi": linear_embedding,
            "embedded_Gbar": linear_g_embedded,
            "embedding_error": linear_embedding_error,
            "n_restricted_starts": len(linear_optima),
        },
        "Sinusoidal_within_Sin+Linear": {
            "restricted_name": "Sinusoidal",
            "restriction": "b=c=0",
            "restricted_best": sinusoidal_best,
            "restricted_phi": sinusoidal_phi,
            "embedded_phi": sinusoidal_embedding,
            "embedded_Gbar": sinusoidal_g_embedded,
            "embedding_error": sinusoidal_embedding_error,
            "n_restricted_starts": len(sinusoidal_optima),
        },
    }
    nested_pairs = {}
    all_hold = True
    for pair_name, pair_input in pair_inputs.items():
        restricted_name = pair_input["restricted_name"]
        restricted_min = float(pair_input["restricted_best"][1])
        encompassing_min = float(encompassing_best[1])
        margin = restricted_min - encompassing_min
        holds = margin >= -MIN_G_TOLERANCE
        all_hold = all_hold and holds
        orderings = {}
        for convention in ("occam_false", "occam_true"):
            orderings[convention] = _ordering_summary(
                TAUS,
                np.asarray(sweeps["Sin+Linear"][convention]["log_Z_M"]),
                np.asarray(sweeps[restricted_name][convention]["log_Z_M"]),
            )
        nested_pairs[pair_name] = {
            "restricted_model": restricted_name,
            "encompassing_model": "Sin+Linear",
            "restriction": pair_input["restriction"],
            "restricted": {
                "min_Gbar": restricted_min,
                "phi_min": pair_input["restricted_phi"],
                "n_multistarts": pair_input["n_restricted_starts"],
            },
            "encompassing": {
                "min_Gbar": encompassing_min,
                "phi_min": encompassing_phi,
                "n_multistarts": len(encompassing_optima),
            },
            "embedded_restricted_optimum": {
                "phi": pair_input["embedded_phi"],
                "Gbar": pair_input["embedded_Gbar"],
                "absolute_Gbar_error": pair_input["embedding_error"],
                "tolerance": EMBEDDING_TOLERANCE,
                "passed": pair_input["embedding_error"] <= EMBEDDING_TOLERANCE,
            },
            "inequality": "min_φ Ḡ(encompassing) ≤ min_φ Ḡ(restricted)",
            "margin_restricted_minus_encompassing": margin,
            "tolerance": MIN_G_TOLERANCE,
            "inequality_holds": holds,
            "verified_for_tau_count": len(TAUS),
            "minimum_is_tau_independent": True,
            "Z_M_ordering": orderings,
        }

    verdict_text = (
        "Both numerical min-Ḡ inequalities hold on the n=50 informative-config, "
        "MAP-based toy GP. E6 supports the reachable-set claim for these two "
        "exact restrictions, while the finite-τ Z_M ordering still depends on "
        "the reference-measure convention."
        if all_hold
        else
        "At least one numerical min-Ḡ inequality fails on the n=50 informative-config, "
        "MAP-based toy GP, so E6 reports a counterexample to the reachable-set claim."
    )
    results = {
        "schema_version": 1,
        "case": "B",
        "artifact": "e6_nesting_monotonicity",
        "provenance": {
            "gp_config": "informative",
            "gp_method": "map",
            "metric": "pw_kl_vcal",
            "n": 50,
            "data_seed": DATA_SEED,
            "is_seed": IS_SEED,
            "x_eval_count": len(x_eval),
            "x_eval_range": [float(x_eval[0]), float(x_eval[-1])],
            "n_draws_requested": N_DRAWS,
            "gp_predictives_retained": retained,
            "n_is": n_is,
            "n_perturb": N_PERTURB,
            "tau_grid": {
                "definition": "numpy.logspace(-1.5, 2.5, 161)",
                "values": TAUS,
            },
            "spaces": {
                "restricted": "bistar_viz/scripts/_viz_spaces.py:canonical_spaces",
                "encompassing": (
                    "canonical Sin+Linear bounds with the amplitude lower bound "
                    "extended from 0.01 to 0 for exact nesting"
                ),
            },
            "optimizer": "bistar_gp.laplace_evidence._multistart_G_optima",
            "Z_M_estimator": "bistar_gp.laplace_evidence.is_log_Z_Mx",
            "occam_normalization": (
                "bistar_gp.laplace_evidence._log_reference_volume"
            ),
            "start_sets": (
                "restricted optima embedded at the exact boundaries for the "
                "min-Ḡ optimization; interior perturbed starts plus the best "
                "encompassing optimum for IS"
            ),
        },
        "tolerances": {
            "min_Gbar_inequality": MIN_G_TOLERANCE,
            "exact_embedding_Gbar": EMBEDDING_TOLERANCE,
        },
        "nested_pairs": nested_pairs,
        "model_sweeps": sweeps,
        "verdict": {
            "all_min_Gbar_inequalities_hold": all_hold,
            "statement": verdict_text,
            "scope": (
                "numerical check on one n=50 informative-config, MAP-based averaged GP; "
                "not a proof over all data priors or parameterizations"
            ),
        },
    }
    path = out_dir / "e6_results.json"
    path.write_text(
        json.dumps(_native(results), indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    write_combined_readme(out_dir)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--n-is", type=int, default=N_IS)
    args = parser.parse_args()
    results = run(args.out_dir.resolve(), n_is=args.n_is)
    for pair_name, pair in results["nested_pairs"].items():
        print(
            f"{pair_name}: restricted min Ḡ={pair['restricted']['min_Gbar']:.9f}; "
            f"encompassing min Ḡ={pair['encompassing']['min_Gbar']:.9f}; "
            f"margin={pair['margin_restricted_minus_encompassing']:.9f}; "
            f"holds={pair['inequality_holds']}"
        )
        for convention in ("occam_false", "occam_true"):
            crossings = pair["Z_M_ordering"][convention]["crossings"]
            if crossings:
                locations = ", ".join(
                    f"{item['tau_log_interpolated']:.6f}" for item in crossings
                )
            else:
                locations = "none on grid"
            print(f"  {convention} Z_M τ crossings: {locations}")
    print(results["verdict"]["statement"])
    print(f"wrote {args.out_dir.resolve() / 'e6_results.json'}")


if __name__ == "__main__":
    main()
