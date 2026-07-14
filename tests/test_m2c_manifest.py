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
V118_SCHEMA_PATH = ROOT / "docs/m2c_freeze/gtoy_profile_result_v1.18.json"


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


# The frozen base sha is pinned to a LITERAL here so it cannot silently drift
# together with the committed JSON (both would have to change to a new value AND
# still equal this literal, which the assertion forbids).
_PINNED_BASE_SHA = "b3d35b64035a848faa82b6f246333e95ddfae25a"


def test_frozen_sha_and_profile_integration_hash_are_live_pinned():
    manifest = _committed_v117()
    assert re.fullmatch(r"[0-9a-f]{40}", manifest["frozen_at_git_sha"])
    assert manifest["frozen_at_git_sha"] == FROZEN_AT_GIT_SHA == _PINNED_BASE_SHA
    live = hashlib.sha256(
        (ROOT / "bistar_gp/profile_integration.py").read_bytes()
    ).hexdigest()
    assert manifest["algorithm"]["profile_integration_sha256"] == live


def test_frozen_base_sha_is_documented_as_the_pre_pr_d_base_in_the_artifact():
    # The base sha lacks the PR-D algorithm; the committed artifact must SAY so
    # (honest provenance), and the manifest is pinned to the live algorithm by
    # the manifest==code CI, not by this base sha.
    manifest = _committed_v117()
    meaning = manifest["provenance"]["frozen_at_git_sha_meaning"]
    assert "base commit" in meaning
    assert "not present at this sha" in meaning.lower() or "NOT present" in meaning


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


def test_v118_file_is_a_schema_contract_with_no_result_values():
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
    assert schema["properties"]["v117_manifest_sha256"]["pattern"] == "^[0-9a-f]{64}$"
    # EXACT property key set: an injected result-value property (e.g.
    # "result_values") in the schema is rejected, not merely the four contracts.
    assert set(schema["properties"]) == {
        "freeze_version", "kind", "v117_manifest_sha256", "frozen_at_git_sha",
        "provenance", "profile_band_masses", "numerical_sensitivity",
        "realized_grids", "gate_events",
    }
    for name in (
        "profile_band_masses", "numerical_sensitivity", "realized_grids", "gate_events"
    ):
        contract = schema["properties"][name]
        assert "const" not in contract
        assert "default" not in contract
        assert "examples" not in contract
        assert "properties" not in contract
