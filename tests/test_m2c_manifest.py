"""Hermetic schema and manifest==code checks for M2c v1.17/v1.18."""

import hashlib
import json
import re
from pathlib import Path

from jsonschema import Draft202012Validator

from bistar_gp import m2c_freeze_dm as dm
from bistar_gp import m2c_freeze_m1 as m1
from bistar_gp import m2c_freeze_s2s3 as s2s3
from bistar_gp.m2c_manifest import (
    FROZEN_AT_GIT_SHA,
    build_v117_algorithm_manifest,
    build_v117_manifest,
    manifest_sha256,
)


ROOT = Path(__file__).resolve().parents[1]
V117_PATH = ROOT / "docs/m2c_freeze/gtoy_profile_freeze_v1.17.json"
# The SCHEMA lives at *.schema.json; the bare *.json path is RESERVED (rev-5
# §6 L375) for the post-recompute filled result instance and must stay absent.
V118_SCHEMA_PATH = ROOT / "docs/m2c_freeze/gtoy_profile_result_v1.18.schema.json"
V118_RESERVED_INSTANCE_PATH = ROOT / "docs/m2c_freeze/gtoy_profile_result_v1.18.json"


# Verbatim rev-5 section 6 v1.17 field contract.
V117_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": [
        "freeze_version", "kind", "frozen_at_git_sha", "provenance",
        "references", "algorithm", "mcse_strategy", "tolerances",
        "predicates", "historical_provenance",
    ],
    "properties": {
        "freeze_version": {"const": "v1.17"},
        "kind": {"const": "m2c-gtoy-profile-algorithm-freeze"},
        "frozen_at_git_sha": {
            "type": "string", "pattern": "^[0-9a-f]{40}$"
        },
        "provenance": {
            "type": "object",
            "required": ["versions", "host", "cpu_count", "threads", "blas", "scipy"],
            "properties": {
                "versions": {"type": "object"},
                "scipy": {"type": "string"},
                "blas": {"type": "string"},
                "host": {"type": "string"},
                "cpu_count": {"type": "integer"},
                "threads": {"type": "integer"},
            },
        },
        "references": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "value", "source", "test"],
                "properties": {
                    "name": {"type": "string"},
                    "value": {},
                    "se": {},
                    "source": {"type": "string"},
                    "test": {"type": "string"},
                    "sha256": {"type": "string"},
                },
            },
        },
        "algorithm": {
            "type": "object",
            "required": [
                "profile_integration_sha256", "grid", "p3",
                "gradient_battery", "optimizer_gate", "curvature_gate",
            ],
            "properties": {
                "profile_integration_sha256": {
                    "type": "string", "pattern": "^[0-9a-f]{64}$"
                },
                "grid": {
                    "type": "object",
                    "required": [
                        "base", "ratio_expr", "ratio_f64", "full_domain",
                        "cap_ladders_diagnostic", "max_nodes", "test",
                    ],
                },
                "p3": {
                    "type": "object",
                    "required": [
                        "eps_domain", "eps_grid", "l_max",
                        "nested_construction", "test",
                    ],
                },
                "gradient_battery": {
                    "type": "object",
                    "required": [
                        "fd_step", "tol_abs", "tol_rel", "point_set",
                        "d23_sentinel", "test",
                    ],
                },
                "optimizer_gate": {
                    "type": "object",
                    "required": [
                        "method", "lbfgsb_controls", "restart_policy",
                        "tau_stat", "dg_agree", "du_agree", "two_start", "test",
                    ],
                },
                "curvature_gate": {
                    "type": "object",
                    "required": [
                        "h_sweep", "center_h", "logdet_stability", "symmetry",
                        "directional_tol", "direction_rng", "spd_required",
                        "rcond_min", "retry_policy", "stop_on_fail", "test",
                    ],
                },
            },
        },
        "mcse_strategy": {
            "type": "object",
            "required": [
                "estimator", "iact_series", "block_len_rule",
                "block_cap_behavior", "B", "seed", "test",
            ],
        },
        "tolerances": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "value", "rationale", "tag", "test"],
            },
        },
        "predicates": {
            "type": "array",
            "items": {
                "type": "object",
                "required": [
                    "name", "formula", "threshold", "fixture", "failure",
                    "field", "test", "tag",
                ],
            },
        },
        "historical_provenance": {
            "type": "object",
            "required": ["buggy_triplet", "sum", "note"],
        },
    },
}


def _committed_v117():
    return json.loads(V117_PATH.read_text(encoding="utf-8"))


def _predicate(manifest, name):
    matches = [entry for entry in manifest["predicates"] if entry["name"] == name]
    assert len(matches) == 1
    return matches[0]


def _test_ids(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "test":
                yield child
            yield from _test_ids(child)
    elif isinstance(value, list):
        for child in value:
            yield from _test_ids(child)


def _all_keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from _all_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _all_keys(child)


def test_committed_v117_validates_against_verbatim_freeze_schema():
    Draft202012Validator.check_schema(V117_SCHEMA)
    Draft202012Validator(V117_SCHEMA).validate(_committed_v117())


def test_manifest_machine_independent_portion_matches_code():
    committed = _committed_v117()
    rebuilt = build_v117_algorithm_manifest()
    for key in (
        "freeze_version", "kind", "references", "algorithm", "mcse_strategy",
        "tolerances", "predicates", "historical_provenance",
    ):
        assert committed[key] == rebuilt[key]


# frozen_at_git_sha is the PR-D IMPLEMENTATION snapshot (Commit A), pinned to a
# LITERAL here so it cannot silently drift together with the committed JSON.
_PINNED_IMPL_SHA = "6d39d38ad000583fcbb4e5311efe57ff5e0c1503"


def test_frozen_sha_and_profile_integration_hash_are_live_pinned():
    manifest = _committed_v117()
    assert re.fullmatch(r"[0-9a-f]{40}", manifest["frozen_at_git_sha"])
    assert manifest["frozen_at_git_sha"] == FROZEN_AT_GIT_SHA == _PINNED_IMPL_SHA
    live = hashlib.sha256(
        (ROOT / "bistar_gp/profile_integration.py").read_bytes()
    ).hexdigest()
    assert manifest["algorithm"]["profile_integration_sha256"] == live


def test_frozen_sha_is_documented_as_the_implementation_snapshot_in_the_artifact():
    # frozen_at_git_sha names the commit that CONTAINS the algorithm code; the
    # committed artifact says so, and the manifest artifact is added in the
    # following commit (a manifest cannot embed its own sha).
    manifest = _committed_v117()
    meaning = manifest["provenance"]["frozen_at_git_sha_meaning"]
    assert "implementation snapshot" in meaning.lower()
    assert "following commit" in meaning.lower()


def test_every_manifest_test_node_id_is_well_formed():
    ids = list(_test_ids(_committed_v117()))
    assert ids
    for node_id in ids:
        assert node_id == "PROPOSED-v1.17" or re.fullmatch(
            r"tests/[^:]+\.py::[A-Za-z_][A-Za-z0-9_]*", node_id
        )


def test_reference_constants_match_frozen_values():
    manifest = _committed_v117()
    refs = {entry["name"]: entry for entry in manifest["references"]}
    assert refs["prior_is_toy_elicited_band_masses"]["value"] == [
        0.762660, 0.191078, 0.046262
    ]
    assert refs["prior_is_toy_elicited_band_masses"]["se"] == [
        0.004283, 0.003838, 0.000866
    ]
    assert refs["rw_mh_toy_elicited_pooled_band_masses"]["value"] == [
        0.815644, 0.161078, 0.023278
    ]
    assert refs["rw_mh_toy_elicited_pooled_band_masses"]["se"] == [
        0.023483, 0.017650, 0.010167
    ]
    assert refs["sir_sin_linear_tau1_probability"]["value"] == dm.MCSE_SIR_REFERENCE
    assert refs["sir_sin_linear_tau1_probability"]["se"] == dm.MCSE_SIR_REFERENCE_SE
    assert refs["w5_independent_pool_scatter"]["value"] == list(
        dm.W5_INDEPENDENT_POOL_SCATTER
    )


def test_predicate_thresholds_equal_frozen_modules():
    manifest = _committed_v117()
    divergence = _predicate(manifest, "divergence_nonclustering")["threshold"]
    assert divergence == {
        "rate_cap": dm.DIVERGENCE_RATE_CAP,
        "concentration_factor": dm.DIVERGENCE_CONC_FACTOR,
        "min_event_floor": dm.DIVERGENCE_MIN_EVENT_FLOOR,
        "time_window_fraction": dm.DIVERGENCE_TIME_WINDOW_FRAC,
    }
    overlap = _predicate(manifest, "m1_covariance_overlap")["threshold"]
    assert overlap["alignment"] == m1.OVERLAP_ALIGNMENT_THRESHOLD
    assert overlap["q_overlap_cap"] == m1.Q_OVERLAP_CAP
    nugget = _predicate(manifest, "m1_nugget_floor")["threshold"]
    assert nugget["noise_reference"] == m1.NUGGET_REFERENCE
    assert nugget["flag_probability"] == m1.NUGGET_FLAG_THRESHOLD
    s2 = _predicate(manifest, "s2_mass_convention")["threshold"]
    assert s2["step_stability"] == s2s3.S2_STEP_STABILITY_TOL
    s3 = _predicate(manifest, "s3_jacobian_equivalence")["threshold"]
    assert s3["n_states"] == s2s3.S3_N_STATES


def test_v117_contains_no_profile_result():
    manifest = _committed_v117()
    # EXACT top-level key set: an injected top-level result payload (e.g.
    # "result_values") is rejected, not merely the four banned names.
    assert set(manifest) == {
        "freeze_version", "kind", "frozen_at_git_sha", "provenance",
        "references", "algorithm", "mcse_strategy", "tolerances",
        "predicates", "historical_provenance",
    }
    keys = set(_all_keys(manifest))
    assert "profile_band_masses" not in keys
    assert "numerical_sensitivity" not in keys
    assert "realized_grids" not in keys
    assert "gate_events" not in keys
    assert "logm" not in keys
    assert "result_values" not in keys


def test_manifest_sha256_is_canonical_and_deterministic():
    manifest = build_v117_manifest()
    canonical = json.dumps(
        manifest, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    assert manifest_sha256(manifest) == hashlib.sha256(canonical).hexdigest()


_V118_SCHEMA = json.loads(V118_SCHEMA_PATH.read_text(encoding="utf-8"))


def _valid_v118_instance():
    """Synthetic (NOT committed) valid v1.18 result instance for schema tests."""
    return {
        "freeze_version": "v1.18",
        "kind": "m2c-gtoy-profile-result-freeze",
        "v117_manifest_sha256": _V118_SCHEMA["properties"]["v117_manifest_sha256"]["const"],
        "frozen_at_git_sha": "0" * 40,
        "provenance": {"note": "synthetic test instance"},
        "profile_band_masses": {"lo": 0.7, "mid": 0.2, "hi": 0.1, "sum": 1.0},
        "numerical_sensitivity": {
            "delta_quad": 1e-4, "delta_hess": 1e-4, "delta_tail": 1e-4
        },
        "realized_grids": {
            "extended": [], "refined_levels": 2, "band_edges": [0.15, 0.30]
        },
        "gate_events": {
            "stop_count": 0, "retry_count": 0, "rcond_fail_count": 0,
            "undetermined": 0,
        },
    }


def test_v118_schema_is_at_schema_path_and_reserves_the_result_instance_path():
    # rev-5 §6 L375 reserves the bare *.json path for the FILLED result instance;
    # PR D delivers only the schema, at *.schema.json.
    assert V118_SCHEMA_PATH.name == "gtoy_profile_result_v1.18.schema.json"
    assert not V118_RESERVED_INSTANCE_PATH.exists()


def test_v118_file_is_a_schema_contract_pinning_v117_with_no_result_values():
    schema = json.loads(V118_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["properties"]["freeze_version"]["const"] == "v1.18"
    assert schema["properties"]["kind"]["const"] == "m2c-gtoy-profile-result-freeze"
    assert set(schema["required"]) == {
        "freeze_version", "kind", "v117_manifest_sha256", "frozen_at_git_sha",
        "provenance", "profile_band_masses", "numerical_sensitivity",
        "realized_grids", "gate_events",
    }
    # v117_manifest_sha256 is a CONST equal to the canonical hash of the ACTUAL
    # committed immutable v1.17 manifest — it references THE frozen manifest, not
    # any 64-hex value (§6 L376).
    assert schema["properties"]["v117_manifest_sha256"]["const"] == manifest_sha256(
        _committed_v117()
    )
    # Top-level additionalProperties:false so a result INSTANCE cannot smuggle
    # extra keys (e.g. injected "result_values").
    assert schema["additionalProperties"] is False
    # EXACT property key set: an injected result-value property is rejected.
    assert set(schema["properties"]) == {
        "freeze_version", "kind", "v117_manifest_sha256", "frozen_at_git_sha",
        "provenance", "profile_band_masses", "numerical_sensitivity",
        "realized_grids", "gate_events",
    }
    # No numeric constraints invented on the nested result values themselves.
    for name in (
        "profile_band_masses", "numerical_sensitivity", "realized_grids", "gate_events"
    ):
        contract = schema["properties"][name]
        assert "const" not in contract
        assert "default" not in contract
        assert "examples" not in contract
        assert "properties" not in contract


def test_v118_schema_validates_a_valid_instance_and_rejects_injections():
    schema = json.loads(V118_SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    # A well-formed result instance validates.
    validator.validate(_valid_v118_instance())
    # An injected top-level result payload is rejected (additionalProperties).
    injected = _valid_v118_instance()
    injected["result_values"] = {"P_noise_lo": 0.7}
    assert not validator.is_valid(injected)
    # A wrong v117_manifest_sha256 is rejected (const binding to the frozen v1.17).
    wrong = _valid_v118_instance()
    wrong["v117_manifest_sha256"] = "0" * 64
    assert not validator.is_valid(wrong)
