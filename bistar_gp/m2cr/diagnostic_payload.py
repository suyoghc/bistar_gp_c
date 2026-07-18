"""Hermetic R3 diagnostic payload/orchestrator (prereg v1.21 sections 2--3).

All protocol mechanics consume injected callables and NumPy values. Executing
``_real_components`` outside an authorized R4 capture launch is prohibited.
"""

from __future__ import annotations

import copy
import json
import math
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from bistar_gp.m2c_freeze import (
    D23_SENTINEL_MIN_REL,
    FD_STEP_GRAD,
    HESS_H_CENTER,
    REFINE_L_MAX,
    SYMMETRY_TOL,
    TOL_GRAD_ABS,
    TOL_GRAD_REL,
    TOY_BAND_EDGES,
)
from bistar_gp.m2cr import diagnostic
from bistar_gp.m2cr.capture import aggregates_from_node_records
from bistar_gp.m2cr.coordinates import (
    CANONICAL_AXIS_ORDER,
    derive_role_map,
    storage_to_canonical_permutation,
    vector_storage_to_canonical,
)
from bistar_gp.m2cr.gates_v2 import curvature_gate_v2, optimize_conditional_v2
from bistar_gp.m2cr.records import (
    build_battery_record,
    build_curvature_record,
    build_per_node_record,
    build_two_start_optimizer_record,
    build_warm_start_ref,
)
from bistar_gp.m2cr.serialization import encode_float, encode_vector

__all__ = [
    "DIAGNOSTIC_STAGE_ORDER",
    "build_closure",
    "run_diagnostic",
    "finalize_document_for_validation",
    "diagnostic_payload_entry",
]

DIAGNOSTIC_STAGE_ORDER = (
    "level0",
    "refine_1",
    "refine_2",
    "refine_3",
    "upper_pullback",
    "lower_pullback",
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DIAGNOSTIC_SCHEMA_PATH = (
    _REPO_ROOT / "docs/m2c_freeze/m2c_diagnostic_record.schema_v1.json"
)
_EXECUTION_SCHEMA_PATH = (
    _REPO_ROOT / "docs/m2c_freeze/m2c_execution_record.schema_v1.json"
)


def _unique(values: Sequence[float] | np.ndarray) -> np.ndarray:
    return np.unique(np.asarray(values, dtype=np.float64))


def _novel(values: np.ndarray, prior: np.ndarray) -> np.ndarray:
    return np.setdiff1d(
        np.asarray(values, dtype=np.float64),
        np.asarray(prior, dtype=np.float64),
        assume_unique=False,
    )


def build_closure(band_edges: Sequence[float] = TOY_BAND_EDGES) -> dict[str, Any]:
    """Materialize the full v1.21 section 2 deterministic verdict closure."""

    # Imported here so importing this payload remains a NumPy-only operation;
    # the frozen primitives themselves are used without modification.
    from bistar_gp.profile_integration import (
        cap_ladder_grids,
        full_domain_grid,
        nested_refine,
    )

    base = _unique(full_domain_grid(band_edges))
    stages: dict[str, np.ndarray] = {"level0": base}
    full_union = base
    refined = base
    for level in range(1, REFINE_L_MAX + 1):
        refined = _unique(nested_refine(refined))
        additions = _novel(refined, full_union)
        stages[f"refine_{level}"] = additions
        full_union = _unique(np.concatenate((full_union, additions)))

    ladders = cap_ladder_grids(band_edges)
    upper = _unique(ladders["upper"][1000.0])
    lower = _unique(ladders["lower"][1e-6])
    for _ in range(REFINE_L_MAX):
        upper = _unique(nested_refine(upper))
        lower = _unique(nested_refine(lower))
    stages["upper_pullback"] = _novel(upper, full_union)
    stages["lower_pullback"] = _novel(lower, full_union)

    all_stage_values = [stages[stage_id] for stage_id in DIAGNOSTIC_STAGE_ORDER]
    concatenated = np.concatenate(all_stage_values)
    closure_node_count = int(concatenated.size)
    union = _unique(concatenated)
    if union.size != closure_node_count:
        raise ValueError("diagnostic closure stages are not pairwise disjoint")
    if closure_node_count > 1481:
        raise ValueError("diagnostic closure exceeds the frozen 1481-node maximum")

    nodes: list[tuple[int, str, float]] = []
    for stage_id in DIAGNOSTIC_STAGE_ORDER:
        for noise in stages[stage_id]:
            nodes.append((len(nodes), stage_id, float(noise)))
    probe_sequence = sorted(nodes, key=lambda entry: entry[2])
    noises = [entry[2] for entry in probe_sequence]
    if any(left >= right for left, right in zip(noises, noises[1:])):
        raise ValueError("diagnostic closure contains a duplicate probe noise")
    return {
        "stages": stages,
        "nodes": nodes,
        "probe_sequence": probe_sequence,
        "closure_node_count": closure_node_count,
    }


def _g2_point(
    *,
    kind: str,
    label: str,
    seed: int | None,
    node_index: int | None,
    u: np.ndarray,
    noise: float,
    bridge: Callable[[float], tuple[Callable[..., Any], Callable[..., Any]]],
    g_hist: Callable[[np.ndarray, float], float],
) -> dict[str, Any]:
    g, _ = bridge(float(noise))
    g_value = float(np.float64(g(np.asarray(u, dtype=np.float64))))
    historical = float(
        np.float64(g_hist(np.asarray(u, dtype=np.float64), float(noise)))
    )
    difference = float(abs(g_value - historical))
    bound = float(1e-9 * max(1.0, abs(historical)))
    return {
        "kind": kind,
        "label": label,
        "seed": seed,
        "node_index": node_index,
        "g_value": encode_float(g_value),
        "g_hist": encode_float(historical),
        "abs_diff": encode_float(difference),
        "bound": bound,
        "pass": bool(np.isfinite(difference) and difference <= bound),
    }


def _purity_result(
    bridge: Callable[[float], tuple[Callable[..., Any], Callable[..., Any]]],
    u: np.ndarray,
    noise: float,
) -> tuple[bool, bool]:
    g, grad = bridge(float(noise))
    first_g = np.float64(g(u))
    first_grad = np.asarray(grad(u), dtype=np.float64)
    second_g = np.float64(g(u))
    second_grad = np.asarray(grad(u), dtype=np.float64)
    return (
        first_g.tobytes() == second_g.tobytes(),
        first_grad.tobytes() == second_grad.tobytes(),
    )


def _validate_closure(closure: Mapping[str, Any]) -> None:
    if set(closure) != {"stages", "nodes", "probe_sequence", "closure_node_count"}:
        raise ValueError("closure has an unknown or missing member")
    stages = closure["stages"]
    if not isinstance(stages, Mapping) or set(stages) != set(DIAGNOSTIC_STAGE_ORDER):
        raise ValueError("closure stages differ from the frozen six-stage set")
    nodes = list(closure["nodes"])
    probe = list(closure["probe_sequence"])
    count = closure["closure_node_count"]
    if isinstance(count, bool) or not isinstance(count, int) or count != len(nodes):
        raise ValueError("closure_node_count does not equal the node inventory")
    if count == 0 or count > 1481:
        raise ValueError("closure node count is outside the frozen bounds")
    expected_indices = list(range(count))
    if [entry[0] for entry in nodes] != expected_indices:
        raise ValueError("closure nodes are not stage-grouped contiguous indices")
    if sorted(nodes, key=lambda entry: entry[2]) != probe:
        raise ValueError("probe_sequence is not the ascending-noise node order")
    if len({float(entry[2]) for entry in probe}) != count:
        raise ValueError("probe_sequence contains duplicate noise values")


def run_diagnostic(
    closure: Mapping[str, Any],
    bridge: Callable[
        [float], tuple[Callable[[np.ndarray], float], Callable[[np.ndarray], np.ndarray]]
    ],
    mode_u_canonical: Sequence[float] | np.ndarray,
    map_noise: float,
    battery_reference: Callable[[np.ndarray, float], Sequence[Mapping[str, Any]]],
    g_hist: Callable[[np.ndarray, float], float],
    d23_provider: Callable[[], Sequence[Mapping[str, Any]]],
    prior_draw_provider: Callable[[], Mapping[str, Any]],
    computation_storage_order: Sequence[str],
    expected_map_noise: float,
    event_sink: Any = None,
) -> dict[str, Any]:
    """Run the complete injected v1.21 sections 2--3 diagnostic protocol."""

    _validate_closure(closure)
    mode = np.asarray(mode_u_canonical, dtype=np.float64)
    if mode.shape != (3,) or not np.all(np.isfinite(mode)):
        raise ValueError("mode_u_canonical must be a finite canonical vector3")
    storage_order = tuple(str(site) for site in computation_storage_order)
    role_map = derive_role_map(storage_order)
    canonical_site_order = tuple(role_map[role] for role in CANONICAL_AXIS_ORDER)

    prior_raw = prior_draw_provider()
    if not isinstance(prior_raw, Mapping) or set(prior_raw) != {
        "storage_site_order",
        "states",
    }:
        raise ValueError("prior_draw_provider returned the wrong shape")
    prior_states_raw = list(prior_raw["states"])
    if [state.get("seed") for state in prior_states_raw] != list(range(100, 110)):
        raise ValueError("prior draws must carry seeds 100 through 109 in order")
    prior_states = [
        {
            "seed": int(state["seed"]),
            "u": encode_vector(np.asarray(state["u"], dtype=np.float64)),
            "noise": float(np.float64(state["noise"])),
        }
        for state in prior_states_raw
    ]

    g2_points = [
        _g2_point(
            kind="map",
            label="map",
            seed=None,
            node_index=None,
            u=mode,
            noise=float(map_noise),
            bridge=bridge,
            g_hist=g_hist,
        )
    ]
    for state, persisted in zip(prior_states_raw, prior_states, strict=True):
        g2_points.append(
            _g2_point(
                kind="prior_draw",
                label=f"prior/seed{persisted['seed']}",
                seed=persisted["seed"],
                node_index=None,
                u=np.asarray(state["u"], dtype=np.float64),
                noise=persisted["noise"],
                bridge=bridge,
                g_hist=g_hist,
            )
        )

    warm_identity: dict[str, Any] = {"kind": "mode_u"}
    warm_vector = mode.copy()
    warm_reason = "initial_mode_u"
    node_records: list[dict[str, Any]] = []
    diagnostic_rows: list[dict[str, Any]] = []
    accepted_g2_inputs: list[tuple[int, np.ndarray, float]] = []
    battery_failures: list[int] = []

    for probe_position, (node_index, stage_id, noise) in enumerate(
        closure["probe_sequence"]
    ):
        if event_sink is not None:
            event_sink.emit(
                "NODE_BEGIN",
                node_index=int(node_index),
                stage_id=str(stage_id),
            )
        g, grad = bridge(float(noise))
        incoming = build_warm_start_ref(
            warm_identity, warm_vector, warm_reason
        )
        optimizer = optimize_conditional_v2(
            lambda u: -float(g(np.asarray(u, dtype=np.float64))),
            lambda u: -np.asarray(grad(np.asarray(u, dtype=np.float64)), dtype=np.float64),
            warm_vector,
            mode,
            event_sink=event_sink,
            node_index=int(node_index),
            perm=(0, 1, 2),
        )
        optimizer_record = build_two_start_optimizer_record(
            optimizer, perm=(0, 1, 2)
        )
        accepted = bool(not optimizer["stop"] and optimizer["u_star"] is not None)
        if not accepted:
            if warm_identity["kind"] == "accepted_node":
                outgoing_reason = "carried_last_accepted_node"
            else:
                outgoing_reason = "carried_mode_u"
            outgoing = build_warm_start_ref(
                warm_identity, warm_vector, outgoing_reason
            )
            node_record = build_per_node_record(
                int(node_index),
                float(noise),
                storage_order,
                incoming,
                outgoing,
                optimizer_record,
                False,
                None,
                stage_id=str(stage_id),
            )
            diagnostic_row = {
                "node_index": int(node_index),
                "probe_position": int(probe_position),
                "stage_id": str(stage_id),
                "noise": float(noise),
                "optimizer_accepted": False,
            }
        else:
            selected = np.asarray(optimizer["u_star"], dtype=np.float64)
            reference = list(battery_reference(selected.copy(), float(noise)))
            if len(reference) != 3:
                raise ValueError("battery_reference must return three coordinates")
            functional = np.asarray(grad(selected), dtype=np.float64)
            if functional.shape != (3,):
                raise ValueError("functional gradient has the wrong shape")
            references = [float(item["reference_value"]) for item in reference]
            scale = max(1.0, *(abs(value) for value in references))
            threshold = TOL_GRAD_ABS + TOL_GRAD_REL * scale
            battery_coordinates = []
            for index, role in enumerate(CANONICAL_AXIS_ORDER):
                error = float(abs(functional[index] - references[index]))
                battery_coordinates.append(
                    {
                        "role": role,
                        "fd_step": float(reference[index]["fd_step"]),
                        "reference_value": references[index],
                        "functional_value": float(functional[index]),
                        "absolute_error": error,
                        "threshold": threshold,
                        "pass": bool(np.isfinite(error) and error <= threshold),
                    }
                )
            battery_record = build_battery_record(battery_coordinates)
            if battery_record["pass"] is not True:
                battery_failures.append(int(node_index))

            curvature = curvature_gate_v2(
                g,
                grad,
                selected,
                nuisance_order=canonical_site_order,
                event_sink=event_sink,
                node_index=int(node_index),
                perm=(0, 1, 2),
            )
            curvature_record = build_curvature_record(
                curvature, perm=(0, 1, 2)
            )
            retry = curvature["retry_evidence"]
            retry_fired = bool(retry["fired"])
            final_phase = "post_retry" if retry_fired else "pre_retry"
            final_evaluation = curvature["evaluations"][final_phase]
            final_u = np.asarray(final_evaluation["u_star"], dtype=np.float64)
            errors = diagnostic.symmetry_error_sweep(grad, final_u)
            analysis = diagnostic.slope_analysis_record(
                diagnostic.SWEEP_H_VALUES, errors
            )
            outgoing_identity = {
                "kind": "accepted_node",
                "stage_id": str(stage_id),
                "node_index": int(node_index),
            }
            outgoing = build_warm_start_ref(
                outgoing_identity, selected, "accepted_current_node"
            )
            node_record = build_per_node_record(
                int(node_index),
                float(noise),
                storage_order,
                incoming,
                outgoing,
                optimizer_record,
                True,
                selected,
                battery_record,
                curvature_record,
                stage_id=str(stage_id),
            )
            pre = curvature["evaluations"]["pre_retry"]
            post = curvature["evaluations"].get("post_retry")
            diagnostic_row = {
                "node_index": int(node_index),
                "probe_position": int(probe_position),
                "stage_id": str(stage_id),
                "noise": float(noise),
                "optimizer_accepted": True,
                "final_evaluation_point": {
                    "phase": final_phase,
                    "u": encode_vector(final_u),
                },
                "raw_symmetry": {
                    "h_center": HESS_H_CENTER,
                    "symmetry_error": encode_float(
                        final_evaluation["symmetry_error"]
                    ),
                    "symmetry_ok": bool(final_evaluation["symmetry_ok"]),
                },
                "sweep": diagnostic.sweep_record(errors),
                "slope_analysis": analysis,
                "curvature_summary": {
                    "retry_fired": retry_fired,
                    "retry_positively_accepted": (
                        bool(retry["positively_accepted"])
                        if retry_fired
                        else None
                    ),
                    "nonstationarity_observed_any_evaluated_point": bool(
                        pre["stationary"] is not True
                        or (post is not None and post["stationary"] is not True)
                    ),
                    "stationary_final": bool(final_evaluation["stationary"]),
                    "spd_final": bool(final_evaluation["spd"]),
                    "rcond_ok_final": bool(final_evaluation["conditioning_ok"]),
                    "directional_ok_final": bool(final_evaluation["directional_ok"]),
                    "logdet_stable_final": bool(final_evaluation["logdet_stable"]),
                },
            }
            accepted_g2_inputs.append((int(node_index), selected.copy(), float(noise)))
            warm_identity = outgoing_identity
            warm_vector = selected.copy()
            warm_reason = "accepted_current_node"

        node_records.append(node_record)
        diagnostic_rows.append(diagnostic_row)
        if not accepted:
            warm_reason = outgoing["selection_reason"]
        if event_sink is not None:
            event_sink.emit(
                "NODE_END",
                node_index=int(node_index),
                stage_id=str(stage_id),
                optimizer_accepted=accepted,
            )

    for node_index, selected, noise in sorted(accepted_g2_inputs):
        g2_points.append(
            _g2_point(
                kind="accepted_optimum",
                label=f"node/{node_index}",
                seed=None,
                node_index=node_index,
                u=selected,
                noise=noise,
                bridge=bridge,
                g_hist=g_hist,
            )
        )

    d23_raw = list(d23_provider())
    if len(d23_raw) != 3:
        raise ValueError("d23_provider must return three site records")
    d23_sites = []
    for item in d23_raw:
        worst = float(item["worst_relative"])
        d23_sites.append(
            {
                "site": str(item["site"]),
                "worst_relative": encode_float(worst),
                "pass": bool(worst > D23_SENTINEL_MIN_REL),
            }
        )

    probe = list(closure["probe_sequence"])
    purity_positions = (0, (len(probe) - 1) // 2, len(probe) - 1)
    purity_labels = ("first", "mid", "last")
    probe_purity = []
    for label, position in zip(purity_labels, purity_positions, strict=True):
        node_index, _stage_id, noise = probe[position]
        g_same, grad_same = _purity_result(bridge, mode, float(noise))
        probe_purity.append(
            {
                "label": label,
                "probe_position": int(position),
                "node_index": int(node_index),
                "noise": float(noise),
                "g_bit_identical": g_same,
                "grad_bit_identical": grad_same,
            }
        )
    mode_g_same, mode_grad_same = _purity_result(
        bridge, mode, float(map_noise)
    )
    purity_pass = bool(
        mode_g_same
        and mode_grad_same
        and all(
            point["g_bit_identical"] and point["grad_bit_identical"]
            for point in probe_purity
        )
    )

    stage_counts = {
        stage_id: int(np.asarray(closure["stages"][stage_id]).size)
        for stage_id in DIAGNOSTIC_STAGE_ORDER
    }
    stages = [
        {
            "stage_id": stage_id,
            "stage_class": "verdict",
            "status": "COMPLETED",
            "nodes_evaluated": stage_counts[stage_id],
            "nodes_total": stage_counts[stage_id],
        }
        for stage_id in DIAGNOSTIC_STAGE_ORDER
    ]
    stage_class_map = {
        int(node_index): "verdict" for node_index, _stage_id, _noise in closure["nodes"]
    }
    node_records.sort(key=lambda record: record["node_index"])
    diagnostic_rows.sort(key=lambda row: row["node_index"])
    aggregates = aggregates_from_node_records(node_records, stage_class_map)
    return {
        "schema_version": 1,
        "kind": "m2c_diagnostic_record",
        "addendum": "v1.21",
        "not_a_result": True,
        "status": "COMPLETED",
        "persisted_axis_order": list(CANONICAL_AXIS_ORDER),
        "computation_storage_order": list(storage_order),
        "coverage": {
            "closure_node_count": int(closure["closure_node_count"]),
            "probe_order": "ascending_noise",
            "node_index_assignment": "stage_grouped",
            "per_stage_node_counts": stage_counts,
        },
        "map_construction": {
            "torch_seed": 42,
            "n_iter": 300,
            "lr": 0.05,
            "prior_config": "toy_elicited_n20",
            "map_noise": float(np.float64(map_noise)),
            "expected_noise": float(np.float64(expected_map_noise)),
            "delta": float(
                np.float64(map_noise) - np.float64(expected_map_noise)
            ),
            "report_only": True,
        },
        "prior_draws": {
            "seeds": list(range(100, 110)),
            "storage_site_order": [str(site) for site in prior_raw["storage_site_order"]],
            "states": prior_states,
        },
        "g2_equivalence": {
            "tolerance_rel": 1e-9,
            "tolerance_floor": 1.0,
            "points": g2_points,
            "all_pass": bool(all(point["pass"] for point in g2_points)),
        },
        "d23_sentinel": {
            "min_rel": D23_SENTINEL_MIN_REL,
            "per_site": d23_sites,
            "pass": bool(all(item["pass"] for item in d23_sites)),
        },
        "g1_battery": {
            "evaluated_count": len(accepted_g2_inputs),
            "failing_node_indices": battery_failures,
            "all_pass": not battery_failures,
        },
        "purity": {
            "u_definition": "mode_u",
            "repeats": 2,
            "mode": {
                "noise": float(np.float64(map_noise)),
                "g_bit_identical": mode_g_same,
                "grad_bit_identical": mode_grad_same,
            },
            "probe_points": probe_purity,
            "pass": purity_pass,
        },
        "per_node_diagnostics": diagnostic_rows,
        "stages": stages,
        "aggregates": aggregates,
        "node_records": node_records,
    }


def _diagnostic_validator() -> Draft202012Validator:
    diagnostic_schema = json.loads(
        _DIAGNOSTIC_SCHEMA_PATH.read_text(encoding="utf-8")
    )
    execution_schema = json.loads(
        _EXECUTION_SCHEMA_PATH.read_text(encoding="utf-8")
    )
    registry = Registry().with_resources(
        [
            (
                diagnostic_schema["$id"],
                Resource.from_contents(diagnostic_schema),
            ),
            (
                execution_schema["$id"],
                Resource.from_contents(execution_schema),
            ),
        ]
    )
    return Draft202012Validator(diagnostic_schema, registry=registry)


def finalize_document_for_validation(
    document: Mapping[str, Any],
    node_evidence_digests: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Reproduce bootstrap persistence and validate the R3 instance schema."""

    persisted = copy.deepcopy(dict(document))
    if "node_records" not in persisted:
        raise ValueError("diagnostic document lacks node_records")
    persisted.pop("node_records")
    persisted["node_evidence_digests"] = [
        copy.deepcopy(dict(item)) for item in node_evidence_digests
    ]
    _diagnostic_validator().validate(persisted)
    return persisted


def _real_components() -> dict[str, Any]:
    """Construct the frozen R4 bridge and reference providers.

    This constructor performs real model/MAP work and therefore may execute
    only after the authorized R4 payload-start boundary (prereg v1.21 section
    9). Imports are deliberately local so module import remains inert.
    """

    import gpytorch
    import torch

    from bistar_gp.config import (
        PRIOR_CONFIGS,
        build_kernels_from_config,
        build_likelihood_from_config,
    )
    from bistar_gp.data import generate_toy_data
    from bistar_gp.e1_potential import build_e1_potential
    from bistar_gp.fit import _mh_log_joint, fit_map
    from bistar_gp.model import apply_hp_value, build_model
    from bistar_gp.profile_integration import profile_potential_callables
    from bistar_gp.profile_potential import ProfilePotential

    torch.set_default_dtype(torch.float64)
    prior_config = PRIOR_CONFIGS["toy_elicited_n20"]
    # v1.21 section 3 / prior_sensitivity_study.map_fitted verbatim: the data
    # generator seeds itself (defaults), the model is built fresh, and
    # torch.manual_seed(42) is applied immediately BEFORE fit_map so the MAP
    # optimization consumes exactly the study's RNG stream.
    x, y, _ = generate_toy_data()

    def fresh() -> tuple[Any, Any]:
        kernels, names = build_kernels_from_config(prior_config)
        likelihood = build_likelihood_from_config(prior_config)
        return build_model(x, y, kernels, names, likelihood)

    model, likelihood = fresh()
    torch.manual_seed(42)
    fit_map(model, likelihood, x, y, n_iter=300, lr=0.05, verbose=False)
    e1 = build_e1_potential(model, likelihood, x, y)
    profile = ProfilePotential(model, likelihood, x, y, sites=e1.sites)
    storage_order = tuple(profile.nuisance_sites)
    permutation = storage_to_canonical_permutation(storage_order)
    storage_g, storage_grad = profile_potential_callables(profile, storage_order)

    def current_theta(site: str) -> Any:
        _prior, fqname, constraint, _shape = profile._site_map[site]
        raw = dict(profile._model.named_parameters())[fqname].detach().clone()
        return constraint.transform(raw) if constraint is not None else raw

    mode_storage = np.asarray(
        [float(torch.log(current_theta(site)).reshape(-1)[0]) for site in storage_order],
        dtype=np.float64,
    )
    mode_canonical = vector_storage_to_canonical(mode_storage, permutation)
    map_noise = float(current_theta(profile.noise_site).reshape(-1)[0])

    def bridge(noise: float) -> tuple[Callable[..., Any], Callable[..., Any]]:
        return diagnostic.canonical_bridge(
            lambda u: storage_g(u, float(noise)),
            lambda u: storage_grad(u, float(noise)),
            permutation,
        )

    def independent_hist(u_canonical: np.ndarray, noise: float) -> float:
        u_storage = diagnostic.vector_canonical_to_storage(
            np.asarray(u_canonical, dtype=np.float64), permutation
        )
        fresh_model, fresh_likelihood = fresh()
        values = {
            site: torch.exp(torch.as_tensor(u_storage[index], dtype=torch.float64))
            for index, site in enumerate(storage_order)
        }
        values[profile.noise_site] = torch.as_tensor(noise, dtype=torch.float64)
        fresh_sites = tuple(name for name, *_ in fresh_model.named_priors())
        if fresh_sites != tuple(profile.sites):
            raise ValueError(
                "fresh-model site order differs from the frozen E1 site order"
            )
        for site in profile.sites:
            if not apply_hp_value(
                fresh_model, fresh_likelihood, site, values[site]
            ):
                raise ValueError(f"could not apply frozen site {site}")
        mll = gpytorch.mlls.ExactMarginalLogLikelihood(
            fresh_likelihood, fresh_model
        )
        scalar = _mh_log_joint(
            mll, fresh_model, fresh_likelihood, x, y
        )
        return float(scalar) + float(np.sum(u_storage, dtype=np.float64))

    def battery_reference(u: np.ndarray, noise: float) -> list[dict[str, float]]:
        result = []
        for index in range(3):
            step = FD_STEP_GRAD * max(1.0, abs(float(u[index])))
            plus = np.asarray(u, dtype=np.float64).copy()
            minus = np.asarray(u, dtype=np.float64).copy()
            plus[index] += step
            minus[index] -= step
            reference = (
                independent_hist(plus, noise) - independent_hist(minus, noise)
            ) / (2.0 * step)
            result.append({"fd_step": step, "reference_value": reference})
        return result

    priors = {name: prior for name, _module, prior, *_ in model.named_priors()}

    def prior_draw_provider() -> dict[str, Any]:
        states = []
        with torch.random.fork_rng():
            for seed in range(100, 110):
                torch.manual_seed(seed)
                theta = {site: priors[site].sample() for site in profile.sites}
                u_storage = np.asarray(
                    [float(torch.log(theta[site]).reshape(-1)[0]) for site in storage_order],
                    dtype=np.float64,
                )
                states.append(
                    {
                        "seed": seed,
                        "u": vector_storage_to_canonical(u_storage, permutation),
                        "noise": float(theta[profile.noise_site].reshape(-1)[0]),
                    }
                )
        return {"storage_site_order": list(storage_order), "states": states}

    def d23_provider() -> list[dict[str, Any]]:
        per_site = {site: 0.0 for site in storage_order}
        for seed in range(5):
            generator = torch.Generator().manual_seed(seed)
            state = {
                site: torch.as_tensor(mode_storage[index], dtype=torch.float64)
                + 0.1
                * torch.randn((), generator=generator, dtype=torch.float64)
                for index, site in enumerate(storage_order)
            }
            naive = profile.g_grad_naive_data(state, map_noise)
            state_storage = np.asarray(
                [float(state[site]) for site in storage_order], dtype=np.float64
            )
            state_canonical = vector_storage_to_canonical(
                state_storage, permutation
            )
            reference_canonical = np.asarray(
                [item["reference_value"] for item in battery_reference(state_canonical, map_noise)],
                dtype=np.float64,
            )
            reference_storage = diagnostic.vector_canonical_to_storage(
                reference_canonical, permutation
            )
            for index, site in enumerate(storage_order):
                if naive[site] is None:
                    per_site[site] = math.inf
                else:
                    relative = abs(float(naive[site]) - reference_storage[index]) / max(
                        1.0, abs(reference_storage[index])
                    )
                    per_site[site] = max(per_site[site], float(relative))
        return [
            {"site": site, "worst_relative": per_site[site]}
            for site in storage_order
        ]

    return {
        "closure": build_closure(),
        "bridge": bridge,
        "mode_u_canonical": mode_canonical,
        "map_noise": map_noise,
        "battery_reference": battery_reference,
        "g_hist": independent_hist,
        "d23_provider": d23_provider,
        "prior_draw_provider": prior_draw_provider,
        "computation_storage_order": storage_order,
        # FIGURE_EXPECTATIONS["toy_elicited_map_noise"], full float64 precision
        # (v1.21 section 3; the rounded 0.06 fixture value is not the constant).
        "expected_map_noise": 0.061867347763041584,
    }


def diagnostic_payload_entry(context: Any) -> dict[str, Any]:
    """R4 ``module:function`` entry; real wiring remains monkeypatchable."""

    return run_diagnostic(**_real_components(), event_sink=context)
