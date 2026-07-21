"""Hermetic tests for the D19 timing-record persistence firewall."""

import ast
import builtins
import copy
import importlib
import json
import os
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


SOURCE_PATH = Path("experiments/d19_bench.py")
SOURCE_TEXT = SOURCE_PATH.read_text()
TREE = ast.parse(SOURCE_TEXT)
d19 = importlib.import_module("experiments.d19_bench")


def _valid_record():
    """Return one complete record satisfying every schema and cross-field rule."""
    return {
        "record": {
            "kind": d19.SCHEMA_KIND,
            "schema_version": d19.SCHEMA_VERSION,
            "firewall_note": d19.FIREWALL_NOTE,
        },
        "threads": {
            "threads_requested": 2,
            "omp_num_threads_configured": 2,
            "mkl_num_threads_configured": 2,
            "openblas_num_threads_configured": 2,
            "veclib_maximum_threads_configured": 2,
            "torch_num_threads_effective": 2,
            "torch_num_interop_threads_effective": 1,
            "thread_configuration_checks_passed": True,
            "thread_control_scope_note": d19.THREAD_SCOPE_NOTE,
        },
        "environment": {
            "timestamp": "2026-07-20T12:00:00+00:00",
            "git_sha": "a" * 40,
            "python": "3.12.1",
            "platform": "test-platform",
            "hostname": "test-host",
            "cpu_count": 4,
            "torch": "2.10.0",
            "gpytorch": "1.14",
            "pyro": "1.9.1",
            "numpy": "2.0.0",
        },
        "run_config": {
            "scale": "sub",
            "design_label": d19.DESIGN_LABEL,
            "n_points": 150,
            "seed": 0,
            "budget_s": 240.0,
            "n_iter_map": 300,
            "n_iter_profile": 150,
            "n_prior_evals_stage1": 100,
            "n_prior_evals_stage2": 1000,
        },
        "data_provenance": {
            "openml_data_id": 41187,
            "source": "vendored",
            "canonical_sha256": d19.EXPECTED_CANONICAL_SHA256,
            "n_train_points": 461,
        },
        "structure": {
            "n_sampled_sites": 7,
            "dim_unconstrained": 7,
        },
        "timings": {
            "map_fit": {
                "status": "measured",
                "n_iter": 300,
                "total_s": 30.0,
                "per_iter_s": 0.1,
            },
            "initialize_model": {
                "status": "measured",
                "total_s": 1.0,
            },
            "potential_value_eval": {
                "status": "measured",
                "median_s": 0.2,
                "mean_s": 0.21,
                "min_s": 0.1,
                "max_s": 0.3,
                "reps": 5,
                "warmup_calls": 1,
            },
            "gradient": {
                "status": "measured",
                "median_s": 0.4,
                "mean_s": 0.42,
                "min_s": 0.3,
                "max_s": 0.5,
                "reps": 5,
                "warmup_calls": 1,
            },
            "hessian": {
                "status": "measured",
                "total_s": 4.0,
                "extrapolated_from_gradient_s": None,
            },
            "prior_eval_stage1": {
                "status": "measured",
                "n_evals": 100,
                "total_s": 10.0,
                "per_eval_s": 0.1,
                "n_failed_potential_evals": 0,
            },
            "prior_eval_stage2": {
                "status": "measured",
                "n_evals": 1000,
                "total_s": 100.0,
                "per_eval_s": 0.1,
                "n_failed_potential_evals": 1,
            },
            "profile_grid_point": {
                "status": "measured",
                "n_iter": 150,
                "total_s": 15.0,
                "per_iter_s": 0.1,
                "laplace_det_bound_s": 4.0,
                "composite_per_point_est_s": 19.0,
            },
        },
        "warning_counts": [
            {"category": "UserWarning", "count": 2},
        ],
        "totals": {
            "elapsed_s": 160.0,
        },
    }


GOLDEN_PATHS = (
    "data_provenance.canonical_sha256",
    "data_provenance.n_train_points",
    "data_provenance.openml_data_id",
    "data_provenance.source",
    "environment.cpu_count",
    "environment.git_sha",
    "environment.gpytorch",
    "environment.hostname",
    "environment.numpy",
    "environment.platform",
    "environment.pyro",
    "environment.python",
    "environment.timestamp",
    "environment.torch",
    "record.firewall_note",
    "record.kind",
    "record.schema_version",
    "run_config.budget_s",
    "run_config.design_label",
    "run_config.n_iter_map",
    "run_config.n_iter_profile",
    "run_config.n_points",
    "run_config.n_prior_evals_stage1",
    "run_config.n_prior_evals_stage2",
    "run_config.scale",
    "run_config.seed",
    "structure.dim_unconstrained",
    "structure.n_sampled_sites",
    "threads.mkl_num_threads_configured",
    "threads.omp_num_threads_configured",
    "threads.openblas_num_threads_configured",
    "threads.thread_configuration_checks_passed",
    "threads.thread_control_scope_note",
    "threads.threads_requested",
    "threads.torch_num_interop_threads_effective",
    "threads.torch_num_threads_effective",
    "threads.veclib_maximum_threads_configured",
    "timings.gradient.max_s",
    "timings.gradient.mean_s",
    "timings.gradient.median_s",
    "timings.gradient.min_s",
    "timings.gradient.reps",
    "timings.gradient.status",
    "timings.gradient.warmup_calls",
    "timings.hessian.extrapolated_from_gradient_s",
    "timings.hessian.status",
    "timings.hessian.total_s",
    "timings.initialize_model.status",
    "timings.initialize_model.total_s",
    "timings.map_fit.n_iter",
    "timings.map_fit.per_iter_s",
    "timings.map_fit.status",
    "timings.map_fit.total_s",
    "timings.potential_value_eval.max_s",
    "timings.potential_value_eval.mean_s",
    "timings.potential_value_eval.median_s",
    "timings.potential_value_eval.min_s",
    "timings.potential_value_eval.reps",
    "timings.potential_value_eval.status",
    "timings.potential_value_eval.warmup_calls",
    "timings.prior_eval_stage1.n_evals",
    "timings.prior_eval_stage1.n_failed_potential_evals",
    "timings.prior_eval_stage1.per_eval_s",
    "timings.prior_eval_stage1.status",
    "timings.prior_eval_stage1.total_s",
    "timings.prior_eval_stage2.n_evals",
    "timings.prior_eval_stage2.n_failed_potential_evals",
    "timings.prior_eval_stage2.per_eval_s",
    "timings.prior_eval_stage2.status",
    "timings.prior_eval_stage2.total_s",
    "timings.profile_grid_point.composite_per_point_est_s",
    "timings.profile_grid_point.laplace_det_bound_s",
    "timings.profile_grid_point.n_iter",
    "timings.profile_grid_point.per_iter_s",
    "timings.profile_grid_point.status",
    "timings.profile_grid_point.total_s",
    "totals.elapsed_s",
    "warning_counts[].category",
    "warning_counts[].count",
)


def _leaf_paths(value, prefix=""):
    paths = []
    if type(value) is dict:
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else key
            paths.extend(_leaf_paths(child, child_prefix))
    elif type(value) is list:
        if value:
            paths.extend(_leaf_paths(value[0], prefix + "[]"))
    else:
        paths.append(prefix)
    return paths


def _walk_values(value, tokens=(), display="$"):
    if type(value) is dict:
        for key, child in value.items():
            yield from _walk_values(child, tokens + (key,), f"{display}.{key}")
    elif type(value) is list:
        for index, child in enumerate(value):
            yield from _walk_values(child, tokens + (index,), f"{display}[{index}]")
    else:
        yield tokens, display, value


def _object_locations(value, tokens=(), display="$"):
    if type(value) is dict:
        yield tokens, display
        for key, child in value.items():
            yield from _object_locations(child, tokens + (key,), f"{display}.{key}")
    elif type(value) is list:
        for index, child in enumerate(value):
            yield from _object_locations(child, tokens + (index,), f"{display}[{index}]")


def _at(record, tokens):
    value = record
    for token in tokens:
        value = value[token]
    return value


def _set(record, tokens, value):
    parent = _at(record, tokens[:-1])
    parent[tokens[-1]] = value


def _get_path(record, tokens):
    return _at(record, tokens[:-1])[tokens[-1]]


def _schema_leaves(schema, tokens=()):
    if isinstance(schema, d19.ListOf):
        yield from _schema_leaves(schema.item_schema, tokens + (0,))
    elif isinstance(schema, d19._LeafValidator):
        yield tokens, schema
    else:
        for key, child in schema.items():
            yield from _schema_leaves(child, tokens + (key,))


def _schema_keys(schema):
    keys = []
    if isinstance(schema, d19.ListOf):
        keys.extend(_schema_keys(schema.item_schema))
    elif type(schema) is dict:
        for key, child in schema.items():
            keys.append(key)
            keys.extend(_schema_keys(child))
    return keys


def _function(name):
    return next(node for node in TREE.body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == name)


# STATIC / AST

def test_training_loader_is_the_sole_loader():
    loader_calls = []
    for node in ast.walk(TREE):
        if isinstance(node, ast.Call):
            func = node.func
            name = func.id if isinstance(func, ast.Name) else (
                func.attr if isinstance(func, ast.Attribute) else "")
            if name.startswith("load_mauna_loa"):
                loader_calls.append(name)
    assert loader_calls == ["load_mauna_loa_training"]


def test_no_holdout_symbol_referenced():
    identifiers = {node.id for node in ast.walk(TREE) if isinstance(node, ast.Name)}
    attributes = {node.attr for node in ast.walk(TREE)
                  if isinstance(node, ast.Attribute)}
    assert not ({"load_mauna_loa", "x_test", "y_test"} & (identifiers | attributes))


def test_no_forbidden_identifier_used_as_emitted_key():
    """No emitted key is forbidden by EITHER denial layer, and none needs an
    exemption: the two-layer split (exact matching for prohibited names that
    are substrings of ratified ones, substring matching only for
    non-colliding families) makes the tables cleanly disjoint from the
    emitted inventory."""

    emitted_keys = set()
    for path in GOLDEN_PATHS:
        emitted_keys.update(piece for piece in path.replace("[]", "").split("."))
    assert emitted_keys
    assert not {key for key in emitted_keys
                if any(token in key.lower()
                       for token in d19.FORBIDDEN_KEY_SUBSTRINGS)}
    assert not {key for key in emitted_keys
                if key.lower() in d19.FORBIDDEN_EXACT_KEYS}
    assert all(not d19._key_is_forbidden(key) for key in emitted_keys)


def test_no_eigendecomposition_call():
    banned = {"eigvalsh", "eigvals", "eig", "cond", "slogdet"}
    called = set()
    for node in ast.walk(TREE):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                called.add(node.func.attr)
            elif isinstance(node.func, ast.Name):
                called.add(node.func.id)
    assert not (called & banned)


def test_no_sampler_or_leapfrog_symbol():
    names = []
    for node in ast.walk(TREE):
        if isinstance(node, ast.Name):
            names.append(node.id.lower())
        elif isinstance(node, ast.Attribute):
            names.append(node.attr.lower())
    assert not any(any(token in name for token in ("sampler", "leapfrog", "nuts", "mcmc"))
                   for name in names)


def test_module_level_imports_are_stdlib_only():
    roots = []
    for node in TREE.body:
        if isinstance(node, ast.Import):
            roots.extend(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            roots.append(node.module.split(".")[0])
    assert roots
    assert set(roots) <= set(sys.stdlib_module_names)
    before = set(sys.modules)
    importlib.reload(d19)
    newly_loaded = set(sys.modules) - before
    assert not ({"numpy", "torch", "gpytorch", "pyro"} & newly_loaded)


def test_thread_env_set_before_heavy_imports():
    """Every environment write and the capture install precede the FIRST heavy
    import. Uses max(env) < min(heavy), not min < min: setting one variable
    early and three late must fail."""

    run_node = _function("run")
    heavy_lines = []
    for node in ast.walk(run_node):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in d19.HEAVY_MODULES:
                    heavy_lines.append(node.lineno)
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module.split(".")[0] in d19.HEAVY_MODULES:
                heavy_lines.append(node.lineno)
    env_lines = [node.lineno for node in ast.walk(run_node)
                 if isinstance(node, ast.Subscript)
                 and isinstance(node.value, ast.Attribute)
                 and isinstance(node.value.value, ast.Name)
                 and node.value.value.id == "os" and node.value.attr == "environ"
                 and isinstance(node.ctx, ast.Store)]
    capture_lines = [node.lineno for node in ast.walk(run_node)
                     if isinstance(node, ast.Call)
                     and isinstance(node.func, ast.Name)
                     and node.func.id == "_capture_file_descriptors"]
    assert heavy_lines and env_lines and capture_lines
    assert max(env_lines) < min(heavy_lines)
    assert max(capture_lines) < min(heavy_lines)


def test_no_incremental_write_helper_exists():
    functions = {node.name for node in TREE.body if isinstance(node, ast.FunctionDef)}
    assert not ({"dump", "persist", "incremental_write"} & functions)
    json_dumps = [node for node in ast.walk(TREE) if isinstance(node, ast.Call)
                  and isinstance(node.func, ast.Attribute)
                  and isinstance(node.func.value, ast.Name)
                  and node.func.value.id == "json" and node.func.attr == "dump"]
    replacements = [node for node in ast.walk(TREE) if isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "os" and node.func.attr == "replace"]
    assert len(json_dumps) == 1
    assert len(replacements) == 1


def test_no_synthetic_cli_mode():
    option_strings = {node.value for node in ast.walk(_function("main"))
                      if isinstance(node, ast.Constant)
                      and isinstance(node.value, str)
                      and node.value.startswith("--")}
    assert "--synthetic" not in option_strings


# KEY INVENTORY

def test_emitted_key_path_inventory_is_exact():
    assert tuple(sorted(_leaf_paths(_valid_record()))) == GOLDEN_PATHS
    assert d19.SCHEMA_KIND == "d19_bench_timing_record"
    assert d19.SCHEMA_VERSION == 1
    assert d19.ALLOWED_THREADS == (1, 2, 3, 4)
    assert d19.THREAD_ENV_VARS == (
        "OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
        "VECLIB_MAXIMUM_THREADS")
    assert d19.HEAVY_MODULES == ("numpy", "torch", "gpytorch", "pyro")
    d19.validate_record(_valid_record())


def test_valid_key_at_wrong_path_fails():
    record = _valid_record()
    record["git_sha"] = record["environment"].pop("git_sha")
    with pytest.raises(d19.FirewallViolation) as raised:
        d19.validate_record(record)
    assert "$.git_sha: unknown key" in str(raised.value)
    assert "$.environment.git_sha: missing required key" in str(raised.value)


def test_unknown_key_rejected_at_every_object():
    template = _valid_record()
    locations = list(_object_locations(template))
    for tokens, display in locations:
        record = copy.deepcopy(template)
        _at(record, tokens)["unexpected_field"] = 1
        with pytest.raises(d19.FirewallViolation) as raised:
            d19.validate_record(record)
        assert f"{display}.unexpected_field: unknown key" in str(raised.value)


def test_missing_required_key_rejected():
    """Recursive, not just top level: deleting ANY key at ANY depth must be
    rejected, so an implementation that only checks the outermost object
    fails."""

    template = _valid_record()

    def paths(node, prefix=()):
        if isinstance(node, dict):
            for key, child in node.items():
                yield prefix + (key,)
                yield from paths(child, prefix + (key,))

    all_paths = list(paths(template))
    assert len(all_paths) > 40  # top level alone is 9
    for tokens in all_paths:
        record = copy.deepcopy(template)
        parent = _at(record, tokens[:-1])
        del parent[tokens[-1]]
        with pytest.raises(d19.FirewallViolation) as raised:
            d19.validate_record(record)
        assert "missing required key" in str(raised.value)
        assert ".".join(("$",) + tokens) in str(raised.value)


def test_schema_keys_and_forbidden_substrings_disjoint():
    """The substring layer collides with NO ratified schema key, so
    `_key_is_forbidden` needs no name-based exemption. Prohibited names that
    are substrings of ratified ones (`sampled_sites` of `n_sampled_sites`,
    `map_hyperparameters` of `map_fit`, `ess` of `hessian`) are caught by the
    exact layer instead."""

    schema_keys = set(_schema_keys(d19.SCHEMA)) | {"category", "count"}
    assert not {key for key in schema_keys
                if any(token in key.lower()
                       for token in d19.FORBIDDEN_KEY_SUBSTRINGS)}
    assert not {key for key in schema_keys
                if key.lower() in d19.FORBIDDEN_EXACT_KEYS}
    assert all(not d19._key_is_forbidden(key) for key in schema_keys)

    # The exact layer still rejects every name the substring layer gave up.
    for prohibited in ("sampled_sites", "map_hyperparameters",
                       "map_noise_variance_normalized", "ess", "n_eff",
                       "samples", "single_thread"):
        assert d19._key_is_forbidden(prohibited), prohibited
    # ...and the substring layer still covers its non-colliding families.
    for prohibited in ("eigenvalues", "min_eig", "max_eig", "spd", "rcond",
                       "condition_number_after_floor", "n_below_1e-6_floor",
                       "map_noise_variance", "period_length_sampled",
                       "out_path", "n_test_months", "y_mean_ppm",
                       "leapfrog_counts", "step_size"):
        assert d19._key_is_forbidden(prohibited), prohibited


# VALUE LEVEL

def test_nan_rejected_at_every_float_path():
    template = _valid_record()
    floats = [(tokens, path) for tokens, path, value in _walk_values(template)
              if type(value) is float]
    assert floats
    for tokens, path in floats:
        record = copy.deepcopy(template)
        _set(record, tokens, float("nan"))
        with pytest.raises(d19.FirewallViolation) as raised:
            d19.validate_record(record)
        assert path in str(raised.value)


def test_inf_rejected_at_every_float_path():
    template = _valid_record()
    floats = [(tokens, path) for tokens, path, value in _walk_values(template)
              if type(value) is float]
    for tokens, path in floats:
        for infinity in (float("inf"), float("-inf")):
            record = copy.deepcopy(template)
            _set(record, tokens, infinity)
            with pytest.raises(d19.FirewallViolation) as raised:
                d19.validate_record(record)
            assert path in str(raised.value)


def test_negative_timing_rejected():
    template = _valid_record()
    timing_floats = [(tokens, path) for tokens, path, value in _walk_values(template)
                     if type(value) is float and path.startswith("$.timings.")]
    for tokens, path in timing_floats:
        record = copy.deepcopy(template)
        _set(record, tokens, -0.01)
        with pytest.raises(d19.FirewallViolation) as raised:
            d19.validate_record(record)
        assert path in str(raised.value)


def test_canonical_sha256_pinned_and_format_enforced():
    assert d19.EXPECTED_CANONICAL_SHA256 == (
        "5bcdc813b4c3b570c9947acfaa0d3ff8cb5f89094b3e4e5121f72535a0cc0910")
    for bad in ("0" * 64, "g" * 64, "A" * 64, "a" * 63, None):
        record = _valid_record()
        record["data_provenance"]["canonical_sha256"] = bad
        with pytest.raises(d19.FirewallViolation, match="canonical_sha256"):
            d19.validate_record(record)


def test_pinned_constant_matches_bistar_gp_data():
    """Drift guard, by AST rather than import.

    Importing bistar_gp.data pulls in NumPy and Torch and executes
    `torch.set_default_dtype(torch.float64)` at module scope, which would break
    this file's hermetic contract and mutate process-global interpreter state.
    Reading the literal out of the source proves the same thing with none of
    that.
    """

    source = Path("bistar_gp/data.py").read_text()
    literals = {}
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    literals[target.id] = node.value.value
    assert "MAUNA_CANONICAL_SHA256" in literals
    assert d19.EXPECTED_CANONICAL_SHA256 == literals["MAUNA_CANONICAL_SHA256"]


def test_const_and_enum_fields_reject_arbitrary_strings():
    template = _valid_record()
    checked = 0
    for tokens, validator in _schema_leaves(d19.SCHEMA):
        if isinstance(validator, (d19.Const, d19.Enum)):
            record = copy.deepcopy(template)
            _set(record, tokens, "arbitrary-string-not-in-schema")
            with pytest.raises(d19.FirewallViolation):
                d19.validate_record(record)
            checked += 1
    assert checked >= 10


def test_cross_field_status_consistency():
    cases = []
    record = _valid_record()
    record["timings"]["hessian"]["extrapolated_from_gradient_s"] = 2.0
    cases.append(record)
    record = _valid_record()
    record["timings"]["hessian"] = {
        "status": "skipped_for_budget", "total_s": 2.0,
        "extrapolated_from_gradient_s": None}
    cases.append(record)
    record = _valid_record()
    record["timings"]["prior_eval_stage2"]["n_failed_potential_evals"] = None
    cases.append(record)
    record = _valid_record()
    record["timings"]["prior_eval_stage2"]["status"] = "extrapolated_from_stage1"
    cases.append(record)
    for record in cases:
        with pytest.raises(d19.FirewallViolation):
            d19.validate_record(record)


def test_budget_skipped_statuses_are_accepted_when_consistent():
    """A validator that simply rejected both budget-guarded statuses would pass
    the negative test above. These two records must VALIDATE."""

    skipped = _valid_record()
    skipped["timings"]["hessian"] = {
        "status": "skipped_for_budget",
        "total_s": None,
        "extrapolated_from_gradient_s": 12.5,
    }
    assert d19.validate_record(skipped)

    extrapolated = _valid_record()
    extrapolated["timings"]["prior_eval_stage2"] = {
        "status": "extrapolated_from_stage1",
        "n_evals": extrapolated["run_config"]["n_prior_evals_stage2"],
        "total_s": 10.0,
        "per_eval_s": 0.01,
        "n_failed_potential_evals": None,
    }
    assert d19.validate_record(extrapolated)


def test_iteration_count_agreement_rules_are_each_enforced():
    """X4-X7 individually: one mismatch at a time, so an implementation that
    checks only some of the four pairs fails."""

    pairs = (
        (("timings", "map_fit", "n_iter"), ("run_config", "n_iter_map")),
        (("timings", "profile_grid_point", "n_iter"),
         ("run_config", "n_iter_profile")),
        (("timings", "prior_eval_stage1", "n_evals"),
         ("run_config", "n_prior_evals_stage1")),
        (("timings", "prior_eval_stage2", "n_evals"),
         ("run_config", "n_prior_evals_stage2")),
    )
    for tokens, _counterpart in pairs:
        record = _valid_record()
        _set(record, tokens, _get_path(record, tokens) + 1)
        with pytest.raises(d19.FirewallViolation):
            d19.validate_record(record)


def test_stage1_failure_count_bound_enforced():
    record = _valid_record()
    stage1 = record["timings"]["prior_eval_stage1"]
    stage1["n_failed_potential_evals"] = stage1["n_evals"] + 1
    with pytest.raises(d19.FirewallViolation):
        d19.validate_record(record)


def test_scale_and_n_points_must_agree():
    for scale, n_points in (("sub", 461), ("full", 150)):
        record = _valid_record()
        record["run_config"]["scale"] = scale
        record["run_config"]["n_points"] = n_points
        with pytest.raises(d19.FirewallViolation, match="n_points"):
            d19.validate_record(record)


def test_min_median_max_ordering_enforced():
    """Each inequality violated INDEPENDENTLY. A mutation breaking both at once
    would pass an implementation that checks only one of them."""

    for name in ("potential_value_eval", "gradient"):
        # min > median, but median <= max holds.
        record = _valid_record()
        block = record["timings"][name]
        block["min_s"], block["median_s"], block["max_s"] = 0.3, 0.2, 0.4
        with pytest.raises(d19.FirewallViolation,
                           match="min_s <= median_s <= max_s"):
            d19.validate_record(record)

        # median > max, but min <= median holds.
        record = _valid_record()
        block = record["timings"][name]
        block["min_s"], block["median_s"], block["max_s"] = 0.1, 0.4, 0.2
        with pytest.raises(d19.FirewallViolation,
                           match="min_s <= median_s <= max_s"):
            d19.validate_record(record)


def test_thread_fields_must_agree_with_request():
    fields = (
        "omp_num_threads_configured", "mkl_num_threads_configured",
        "openblas_num_threads_configured", "veclib_maximum_threads_configured",
        "torch_num_threads_effective",
    )
    for field in fields:
        record = _valid_record()
        record["threads"][field] = 3
        with pytest.raises(d19.FirewallViolation, match="do not all agree"):
            d19.validate_record(record)


def test_git_sha_must_be_present_and_40_hex():
    for bad in (None, "", "a" * 39, "a" * 41, "G" * 40, "A" * 40):
        record = _valid_record()
        record["environment"]["git_sha"] = bad
        with pytest.raises(d19.FirewallViolation, match="git_sha"):
            d19.validate_record(record)


# INJECTION

def test_forbidden_key_rejected_at_every_depth():
    records_and_paths = []
    record = _valid_record()
    record["noise_value"] = 1
    records_and_paths.append((record, "$.noise_value"))
    record = _valid_record()
    record["environment"]["raw_value"] = 1
    records_and_paths.append((record, "$.environment.raw_value"))
    record = _valid_record()
    record["warning_counts"][0]["posterior_value"] = 1
    records_and_paths.append((record, "$.warning_counts[0].posterior_value"))
    record = _valid_record()
    record["safe_wrapper"] = [{"period_value": 1}]
    records_and_paths.append((record, "$.safe_wrapper[0].period_value"))
    for record, path in records_and_paths:
        with pytest.raises(d19.FirewallViolation) as raised:
            d19.validate_record(record)
        assert f"{path}: forbidden key substring" in str(raised.value)


def test_forbidden_key_rejected_even_if_added_to_schema(monkeypatch):
    monkeypatch.setitem(d19.SCHEMA, "noise_metric", d19.NonNegInt())
    record = _valid_record()
    record["noise_metric"] = 0
    with pytest.raises(d19.FirewallViolation, match="forbidden key substring"):
        d19.validate_record(record)


def test_dropped_legacy_keys_are_rejected():
    legacy = (
        "map_noise_variance_normalized", "sampled_sites", "single_thread",
        "provenance", "logjoint", "sub_design", "n_test_months",
    )
    for key in legacy:
        record = _valid_record()
        record[key] = 1
        with pytest.raises(d19.FirewallViolation) as raised:
            d19.validate_record(record)
        assert f"$.{key}" in str(raised.value)


# STREAMS

def test_stdout_report_derives_only_from_validated_record():
    source = _valid_record()
    validated = d19.validate_record(source)
    source["run_config"]["scale"] = "full"
    source["run_config"]["n_points"] = 461
    rendered = d19._render_stdout_report(validated)
    assert json.loads(rendered)["scale"] == "sub"
    with pytest.raises(d19.FirewallViolation):
        d19._render_stdout_report(_valid_record())


def test_stdout_carries_no_forbidden_token():
    rendered = d19._render_stdout_report(d19.validate_record(_valid_record()))
    lowered = rendered.lower()
    assert not any(token in lowered for token in d19.FORBIDDEN_KEY_SUBSTRINGS)


_CLI = ["--scale", "sub", "--threads", "2"]


@pytest.mark.parametrize("raised_exception, expected_class", [
    (RuntimeError("noise=123.45 secret-message"), "RuntimeError"),
    (ValueError("lengthscale=3.14159"), "ValueError"),
    # The post-parse SystemExit path: the interpreter would otherwise print
    # this argument verbatim at exit, straight past the firewall.
    (SystemExit("noise=123.45 secret-message"), "SystemExit"),
])
def test_failure_emits_class_name_only_and_nonzero_exit(
        monkeypatch, capsys, raised_exception, expected_class):
    def fail(_args):
        raise raised_exception

    monkeypatch.setattr(d19, "run", fail)
    with pytest.raises(SystemExit) as raised:
        d19._firewalled_main(_CLI)
    captured = capsys.readouterr()
    assert raised.value.code == 1
    # The escaping SystemExit must carry the bare code 1, never a message.
    assert raised.value.args == (1,)
    assert captured.out == ""
    assert captured.err == (
        f"aborted: {expected_class} (message suppressed by the v1.2 "
        "persistence firewall)\n")
    for leaked in ("secret-message", "123.45", "3.14159", "lengthscale",
                   "noise"):
        assert leaked not in captured.err
        assert leaked not in str(raised.value.args)


def test_argparse_errors_still_reach_the_user(capsys):
    """Parse-time SystemExit is deliberately NOT sanitized: it carries only the
    user's own CLI tokens, and silencing it would make the tool unusable."""

    with pytest.raises(SystemExit) as raised:
        d19._firewalled_main(["--scale", "sub"])  # missing --threads
    assert raised.value.code == 2
    assert "--threads" in capsys.readouterr().err


def test_fd_level_capture_discards_native_writes(capfd):
    """Native fd writes are discarded inside the region AND both fds are truly
    restored after it. Writing only inside would let a context manager that
    redirects but never restores pass, because pytest repairs capture later."""

    with d19._capture_file_descriptors():
        os.write(1, b"native-stdout-secret\n")
        os.write(2, b"native-stderr-secret\n")
    os.write(1, b"after-restore-stdout\n")
    os.write(2, b"after-restore-stderr\n")
    captured = capfd.readouterr()
    assert "native-stdout-secret" not in captured.out
    assert "native-stderr-secret" not in captured.err
    # Restoration actually happened: post-exit writes reach the real streams.
    assert "after-restore-stdout" in captured.out
    assert "after-restore-stderr" in captured.err


def test_fd_capture_restores_on_exception(capfd):
    """An exception inside the region must not strand the descriptors."""

    with pytest.raises(RuntimeError):
        with d19._capture_file_descriptors():
            os.write(1, b"swallowed-secret\n")
            raise RuntimeError("boom")
    os.write(1, b"restored-after-exception\n")
    captured = capfd.readouterr()
    assert "swallowed-secret" not in captured.out
    assert "restored-after-exception" in captured.out


def test_fd_capture_restores_when_stream_flush_raises(capfd):
    """A workload that breaks sys.stdout must not prevent restoration: the
    finally block flushes best-effort, then restores regardless."""

    class Exploding:
        def flush(self):
            raise ValueError("flush exploded")

        def write(self, _data):
            return 0

    original = sys.stdout
    try:
        with d19._capture_file_descriptors():
            sys.stdout = Exploding()
    finally:
        sys.stdout = original
    os.write(1, b"restored-despite-flush-failure\n")
    assert "restored-despite-flush-failure" in capfd.readouterr().out


def test_warning_message_never_reaches_record():
    class PoisonWarningMessage:
        category = UserWarning

        @property
        def message(self):
            raise AssertionError("warning message was read")

    summary = d19._summarize_warnings([PoisonWarningMessage()])
    assert summary == [{"category": "UserWarning", "count": 1}]
    assert "warning message was read" not in json.dumps(summary)


def test_unknown_warning_class_buckets_to_other():
    class BespokeScientificWarning(Warning):
        pass

    captured = [SimpleNamespace(category=BespokeScientificWarning)]
    assert d19._summarize_warnings(captured) == [
        {"category": "other", "count": 1}]


def test_warning_counts_unique_and_sorted():
    captured = [
        SimpleNamespace(category=UserWarning),
        SimpleNamespace(category=RuntimeWarning),
        SimpleNamespace(category=UserWarning),
    ]
    assert d19._summarize_warnings(captured) == [
        {"category": "RuntimeWarning", "count": 1},
        {"category": "UserWarning", "count": 2},
    ]
    # One defect at a time: a mutation that is BOTH unsorted and duplicated
    # would pass an implementation enforcing only one of the two properties.
    unsorted_only = _valid_record()
    unsorted_only["warning_counts"] = [
        {"category": "UserWarning", "count": 1},
        {"category": "RuntimeWarning", "count": 1},
    ]
    with pytest.raises(d19.FirewallViolation, match="unique and sorted"):
        d19.validate_record(unsorted_only)

    duplicated_only = _valid_record()
    duplicated_only["warning_counts"] = [
        {"category": "RuntimeWarning", "count": 1},
        {"category": "RuntimeWarning", "count": 2},
    ]
    with pytest.raises(d19.FirewallViolation, match="unique and sorted"):
        d19.validate_record(duplicated_only)


# THREADS

def test_threads_required_and_range_enforced(capsys):
    bad_argv = (
        ["--scale", "sub"],
        ["--scale", "sub", "--threads", "0"],
        ["--scale", "sub", "--threads", "5"],
        ["--scale", "sub", "--threads", "not-an-int"],
    )
    for argv in bad_argv:
        with pytest.raises(SystemExit) as raised:
            d19.main(argv)
        assert raised.value.code == 2
    assert capsys.readouterr().err


def test_preimported_module_aborts_before_data_load(monkeypatch):
    imports = []
    original_import = builtins.__import__

    def spy_import(name, *args, **kwargs):
        imports.append(name)
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", spy_import)
    monkeypatch.setitem(sys.modules, "numpy", object())
    with pytest.raises(RuntimeError, match="before thread setup"):
        d19.main(["--scale", "sub", "--threads", "1"])
    assert "bistar_gp.data" not in imports


def test_thread_scope_note_is_const_and_makes_no_ceiling_claim():
    assert "does NOT certify" in d19.THREAD_SCOPE_NOTE
    assert "process-wide ceiling" in d19.THREAD_SCOPE_NOTE
    assert "inter-op threads were observed, never set" in d19.THREAD_SCOPE_NOTE
    record = _valid_record()
    record["threads"]["thread_control_scope_note"] = "guarantees a hard ceiling"
    with pytest.raises(d19.FirewallViolation, match="thread_control_scope_note"):
        d19.validate_record(record)


# PERSISTENCE

def test_no_file_written_on_failure(tmp_path):
    target = tmp_path / "nested" / "bench_sub.json"
    record = _valid_record()
    record["timings"]["gradient"]["total_s"] = 1.0
    with pytest.raises(d19.FirewallViolation):
        d19._validate_and_write(record, target)
    assert not target.exists()
    assert not target.parent.exists()


def test_invalid_record_cannot_replace_existing_artifact(tmp_path):
    target = tmp_path / "bench_sub.json"
    original = b"existing-valid-artifact\n"
    target.write_bytes(original)
    record = _valid_record()
    record["record"]["kind"] = "wrong"
    with pytest.raises(d19.FirewallViolation):
        d19._validate_and_write(record, target)
    assert target.read_bytes() == original


def test_atomic_write_replaces_existing_artifact(tmp_path, monkeypatch):
    """Honest overwrite is preserved, and it genuinely goes through
    os.replace from a temp file in the SAME directory (a plain write_text
    would satisfy the outcome but not the atomicity contract)."""

    target = tmp_path / "bench_sub_threads_2.json"
    target.write_text("old artifact")

    replaced = []
    real_replace = os.replace

    def spy_replace(src, dst):
        replaced.append((Path(src), Path(dst)))
        return real_replace(src, dst)

    monkeypatch.setattr(d19.os, "replace", spy_replace)
    validated, report = d19._validate_and_write(_valid_record(), target)

    assert len(replaced) == 1
    source, destination = replaced[0]
    assert destination == target
    # Same-directory temp file is what makes os.replace atomic.
    assert source.parent == target.parent
    assert json.loads(target.read_text()) == _valid_record()
    assert isinstance(validated, dict)
    assert json.loads(report)["kind"] == d19.SCHEMA_KIND
    assert list(tmp_path.glob("*.tmp")) == []


def test_same_target_rewritten_without_no_clobber(tmp_path):
    """Repeated runs at the SAME scale/thread target keep replacing honestly;
    no general no-clobber policy was introduced."""

    target = d19.target_path(tmp_path, "sub", 2)
    first, _ = d19._validate_and_write(_valid_record(), target)
    second_record = _valid_record()
    second_record["totals"]["elapsed_s"] = 99.5
    second, _ = d19._validate_and_write(second_record, target)
    assert json.loads(target.read_text())["totals"]["elapsed_s"] == 99.5
    assert first != second


# OUTPUT NAMESPACE

def test_default_output_namespace_is_not_the_superseded_one():
    assert d19.DEFAULT_OUT_DIR == d19.REPO_ROOT / "runs" / "d19_a7_timing"
    assert "d19_planning" not in str(d19.DEFAULT_OUT_DIR)


def test_thread_setting_yields_distinct_filenames(tmp_path):
    names = {d19.target_path(tmp_path, "sub", n).name for n in (1, 2, 3, 4)}
    assert names == {
        "bench_sub_threads_1.json", "bench_sub_threads_2.json",
        "bench_sub_threads_3.json", "bench_sub_threads_4.json",
    }
    assert len(names) == 4


def test_scale_separates_targets(tmp_path):
    sub = d19.target_path(tmp_path, "sub", 2)
    full = d19.target_path(tmp_path, "full", 2)
    assert sub != full
    assert {sub.name, full.name} == {
        "bench_sub_threads_2.json", "bench_full_threads_2.json"}


@pytest.mark.parametrize("legacy", [
    "runs/d19_planning/bench_sub.json",
    "runs/d19_planning/bench_full.json",
])
def test_superseded_legacy_targets_are_refused(legacy):
    with pytest.raises(d19.FirewallViolation):
        d19.reject_superseded_target(d19.REPO_ROOT / legacy)


def test_legacy_target_refused_before_any_workload(monkeypatch, tmp_path):
    """The refusal fires before any heavy import, data load, or model build."""

    imported = []
    real_import = builtins.__import__

    def spy_import(name, *rest, **kwargs):
        if name.split(".")[0] in (*d19.HEAVY_MODULES, "bistar_gp"):
            imported.append(name)
        return real_import(name, *rest, **kwargs)

    monkeypatch.setattr(builtins, "__import__", spy_import)
    monkeypatch.setattr(
        d19, "target_path",
        lambda out_dir, scale, threads:
            d19.REPO_ROOT / "runs" / "d19_planning" / f"bench_{scale}.json")

    args = d19.parse_args(["--scale", "sub", "--threads", "2",
                           "--out-dir", str(tmp_path)])
    with pytest.raises(d19.FirewallViolation):
        d19.run(args)
    assert imported == []


# PRODUCTION WIRING (runtime, hermetic: fake heavy modules via an import spy)

class _StopBeforeWorkload(Exception):
    """Marker raised by a spy to halt run() at a chosen boundary."""


def _fake_torch(num_threads):
    """Minimal torch stand-in; get_num_threads is what the contract checks."""
    return SimpleNamespace(
        set_num_threads=lambda _n: None,
        get_num_threads=lambda: num_threads,
        get_num_interop_threads=lambda: 1,
        set_default_dtype=lambda _d: None,
        float64=object(),
        __version__="0.0.0-fake",
    )


def _install_import_spy(monkeypatch, events, torch_threads, stop_at):
    """Intercept heavy imports, recording env at each, and serve fakes."""
    real_import = builtins.__import__
    fakes = {
        "torch": _fake_torch(torch_threads),
        "numpy": SimpleNamespace(__version__="0.0.0-fake"),
        "gpytorch": SimpleNamespace(__version__="0.0.0-fake"),
        "pyro": SimpleNamespace(__version__="0.0.0-fake"),
    }

    # The pytest session has already imported numpy/torch for other modules, so
    # the production pre-import guard would fire first and mask what these
    # tests are probing. Hide them for the duration; monkeypatch restores them,
    # and the spy serves fakes so the real ones are never re-imported here.
    for name in list(sys.modules):
        if name.split(".")[0] in (*d19.HEAVY_MODULES, "bistar_gp"):
            monkeypatch.delitem(sys.modules, name, raising=False)

    def spy(name, globals=None, locals=None, fromlist=(), level=0):
        root = name.split(".")[0]
        if root in fakes or root == "bistar_gp":
            events.append((root, {v: os.environ.get(v)
                                  for v in d19.THREAD_ENV_VARS}))
            if root == stop_at:
                raise _StopBeforeWorkload(root)
            if root in fakes:
                return fakes[root]
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", spy)
    return fakes


def test_all_four_env_vars_are_set_at_the_first_heavy_import(monkeypatch, tmp_path):
    """Kills the mutant that sets one variable before the first heavy import
    and the other three afterwards: all four are asserted AT that import."""

    for name in d19.THREAD_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    events = []
    _install_import_spy(monkeypatch, events, torch_threads=3, stop_at="numpy")
    args = d19.parse_args(["--scale", "sub", "--threads", "3",
                           "--out-dir", str(tmp_path)])
    with pytest.raises(_StopBeforeWorkload):
        d19.run(args)
    assert events, "no heavy import was attempted"
    _root, env_at_first_import = events[0]
    assert env_at_first_import == {name: "3" for name in d19.THREAD_ENV_VARS}


def test_torch_thread_mismatch_aborts_before_bistar_gp_is_reached(
        monkeypatch, tmp_path):
    """A torch whose intra-op count disagrees with the request must abort
    before any bistar_gp import, loader call, or model construction."""

    events = []
    _install_import_spy(monkeypatch, events, torch_threads=99, stop_at=None)
    args = d19.parse_args(["--scale", "sub", "--threads", "2",
                           "--out-dir", str(tmp_path)])
    with pytest.raises(RuntimeError, match="thread verification failed"):
        d19.run(args)
    assert [root for root, _env in events if root == "bistar_gp"] == []


def test_preimported_heavy_module_aborts_before_any_import(monkeypatch, tmp_path):
    """The pre-import guard fires before the env is written or anything is
    imported, so a poisoned interpreter cannot silently proceed."""

    events = []
    _install_import_spy(monkeypatch, events, torch_threads=2, stop_at=None)
    monkeypatch.setitem(sys.modules, "torch", _fake_torch(2))
    args = d19.parse_args(["--scale", "sub", "--threads", "2",
                           "--out-dir", str(tmp_path)])
    with pytest.raises(RuntimeError, match="imported before thread setup"):
        d19.run(args)
    assert events == []


def test_report_key_inventory_is_exact_and_both_layers_scanned():
    """The stdout report is closed-world, and a value carrying an exact-layer
    token (`ess`) is rejected even though the substring layer gave that token
    up to avoid colliding with `hessian`."""

    validated = d19.validate_record(_valid_record())
    rendered = json.loads(d19._render_stdout_report(validated))
    assert set(rendered) == set(d19.REPORT_KEYS)

    leaky = copy.deepcopy(dict(validated))
    leaky["run_config"]["scale"] = "sub"
    forged = d19.validate_record(leaky)
    dict.__setitem__(forged, "run_config", dict(forged["run_config"]))
    forged["run_config"]["scale"] = "ess"
    with pytest.raises(d19.FirewallViolation):
        d19._render_stdout_report(forged)


def test_validated_record_marker_cannot_be_forged():
    """The write and report paths trust this marker, so it must be
    unforgeable: a bare dict subclass would attest to nothing."""

    with pytest.raises(d19.FirewallViolation):
        d19._ValidatedRecord({"ess": 1})
    with pytest.raises(d19.FirewallViolation):
        d19._ValidatedRecord({"ess": 1}, object())


def test_unvalidated_mapping_cannot_reach_the_writer(tmp_path):
    target = tmp_path / "bench_sub_threads_2.json"
    target.write_text("existing")
    with pytest.raises(d19.FirewallViolation):
        d19._atomic_write_json({"ess": 1}, target)
    assert target.read_text() == "existing"


def test_loader_returned_provenance_flows_into_the_record():
    """C3 requires the loader-RETURNED digest and source, not compile-time
    constants: the record-building path must read them from the loader."""

    source = ast.parse(SOURCE_TEXT)
    run_node = _function("run")
    assigned = {
        target.id
        for node in ast.walk(run_node)
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    }
    assert {"canonical_sha256", "dataset_source"} <= assigned
    subscripts = {
        node.slice.value
        for node in ast.walk(run_node)
        if isinstance(node, ast.Subscript)
        and isinstance(node.value, ast.Name)
        and node.value.id == "training_metadata"
        and isinstance(node.slice, ast.Constant)
    }
    assert subscripts == {"source", "canonical_sha256"}
    # ...and the constants are NOT what the record emits.
    text = SOURCE_TEXT
    assert '"canonical_sha256": canonical_sha256' in text
    assert '"source": dataset_source' in text
