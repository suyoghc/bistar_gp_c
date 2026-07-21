"""D19 planning benchmark with a timing-only persistence firewall.

The preregistration firewall permits only timing, evaluation-count,
configuration, and environment-provenance fields to leave this process.
Posterior samples and disallowed diagnostics are discarded unread. Transient
prior proposals and MAP-derived values ARE read internally, because pricing the
prior-evaluation and profile workloads requires applying them, but they remain
local: hyperparameters, noise values, posterior summaries, curvature spectra,
and per-site values are never printed or serialized. Errors are reduced to the
exception class before they reach the terminal, including a post-parse
SystemExit, whose argument Python would otherwise print verbatim.

The heavy-import/workload region is silenced at file-descriptor level so native
extensions are covered as well as Python writes. Residual limitations are:
argparse writes before capture is installed; a native library could cache an
output fd before installation; faulthandler or fatal-signal output can bypass
normal cleanup; and shutdown-time output can occur after the original fds have
been restored.
"""

import argparse
import copy
import json
import math
import os
import platform
import re
import statistics
import subprocess
import sys
import tempfile
import time
import warnings
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import partial
from pathlib import Path


SCHEMA_KIND = "d19_bench_timing_record"
SCHEMA_VERSION = 1

FIREWALL_NOTE = (
    "prereg v1.2 point 6 and v1.6 item 6 (ratified v1.9 item 1, v1.11 item 4): "
    "this artifact carries only timing, evaluation-count, configuration and "
    "environment fields. Posterior samples and disallowed diagnostics are "
    "discarded unread. Transient prior proposals and MAP-derived values are "
    "read internally ONLY to execute the frozen timing workloads that require "
    "them. None of them is printed or serialized: no hyperparameter, noise, "
    "posterior, curvature-spectrum or per-site value leaves this process."
)

THREAD_SCOPE_NOTE = (
    "OMP_NUM_THREADS, MKL_NUM_THREADS, OPENBLAS_NUM_THREADS and "
    "VECLIB_MAXIMUM_THREADS were set by this process before importing numpy, "
    "torch, gpytorch or pyro, and torch intra-op threads were set and verified "
    "equal to the request. thread_configuration_checks_passed certifies only "
    "those checks: heavy scientific modules absent when the environment was "
    "set, the four environment variables equal to the request, and torch "
    "intra-op equal to the request. It does NOT certify actual BLAS worker "
    "counts, torch inter-op control, a process-wide ceiling, or exact physical "
    "workers. VECLIB_MAXIMUM_THREADS is a maximum, not a guarantee. Torch "
    "inter-op threads were observed, never set."
)

DESIGN_LABEL = (
    "whole-span season-preserving even-index subsample "
    "(np.round(np.linspace) over indices)"
)

ALLOWED_THREADS = (1, 2, 3, 4)
THREAD_ENV_VARS = ("OMP_NUM_THREADS", "MKL_NUM_THREADS",
                   "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")
HEAVY_MODULES = ("numpy", "torch", "gpytorch", "pyro")

EXPECTED_N_TRAIN_POINTS = 461
EXPECTED_N_SAMPLED_SITES = 7
EXPECTED_DIM_UNCONSTRAINED = 7
SCALE_N_POINTS = {"sub": 150, "full": 461}
MAUNA_OPENML_DATA_ID = 41187
EXPECTED_CANONICAL_SHA256 = (
    "5bcdc813b4c3b570c9947acfaa0d3ff8cb5f89094b3e4e5121f72535a0cc0910")

WARNING_CATEGORIES = ("ConvergenceWarning", "DeprecationWarning",
                      "FutureWarning", "LinAlgWarning", "NumericalWarning",
                      "RuntimeWarning", "UserWarning", "other")

# Two-layer key denial. The path-aware closed schema below is the PRIMARY
# enforcement: it rejects every unknown key and every valid key at the wrong
# nesting level. These two tables are defence in depth against a careless
# schema edit, and are split because some prohibited names are substrings of
# ratified ones (`sampled_sites` of `n_sampled_sites`, `map_` of `map_fit`,
# `ess` of `hessian`). Exact matching handles those; substring matching is
# reserved for families that collide with no ratified key.
# Exact layer. Necessarily an enumeration rather than a rule: `map_fit` is
# ratified while `map_values` is prohibited, and no pattern separates them, so
# the families whose substrings collide with ratified keys are listed by name.
# This layer is defence in depth and CANNOT be complete; the path-aware
# closed-world schema is the actual guarantee, and it rejects every unknown key
# whether or not that key appears below.
FORBIDDEN_EXACT_KEYS = (
    # `sample*` — collides with the ratified `n_sampled_sites`
    "sample", "samples", "sample_values", "sampled_sites", "n_samples",
    "posterior_samples", "prior_samples", "sample_stats",
    # `ess`/`n_eff` — collides with the ratified `hessian`
    "ess", "n_ess", "ess_mean", "ess_bulk", "ess_tail", "n_eff", "ess_per_sec",
    # `map_*` — collides with the ratified `map_fit`
    "map_values", "map_value", "map_params", "map_parameters", "map_estimate",
    "map_point", "map_hyperparameters", "map_noise_variance_normalized",
    # per-site values — `period`/`site` families not otherwise covered
    "per_site_value", "per_site_values", "site_values",
    # legacy provenance keys retired by C2/C3
    "openml_name", "openml_version",
    "n_raw", "n_monthly", "cutoff_rule", "single_thread",
)

FORBIDDEN_KEY_SUBSTRINGS = (
    "hyperparam", "noise", "lengthscale", "outputscale", "raw_",
    "eig", "spd", "rcond", "condition", "cond_", "floor",
    "rhat", "r_hat", "diverg", "accept", "step_size", "stepsize",
    "draw", "posterior", "logprob", "log_prob", "elbo", "mll",
    "leapfrog", "y_mean", "y_std", "x_offset", "span_years", "stride",
    "calendar", "n_test", "test_years", "holdout", "out_path",
    "period",
)

REPO_ROOT = Path(__file__).resolve().parents[1]

# A7 outputs land in their OWN namespace, never the pre-D22 one. The old
# default (`runs/d19_planning/bench_{scale}.json`) addressed the two superseded
# anchors documented in docs/d19-pre-d22-bench-supersession.md, so a rerun would
# have destroyed the historical provenance that document preserves. The
# thread setting is part of the filename so a thread sweep cannot overwrite its
# own earlier rows.
DEFAULT_OUT_DIR = REPO_ROOT / "runs" / "d19_a7_timing"

SUPERSEDED_LEGACY_TARGETS = (
    "runs/d19_planning/bench_sub.json",
    "runs/d19_planning/bench_full.json",
)


def target_path(out_dir, scale, threads):
    """Resolve the output path for one (scale, threads) design point."""
    return (Path(out_dir) / f"bench_{scale}_threads_{threads}.json")


def reject_superseded_target(target):
    """Refuse to address either superseded pre-D22 anchor.

    Called immediately after argument parsing, so it fires before any heavy
    import, data load, or model construction. Under the current filename scheme
    a resolved target cannot coincidentally equal a legacy path; this guard
    exists so that a future change to the naming rule cannot silently start
    overwriting historical provenance.
    """
    resolved = Path(target).expanduser().resolve()
    for relative in SUPERSEDED_LEGACY_TARGETS:
        if resolved == (REPO_ROOT / relative).resolve():
            raise FirewallViolation(
                "refusing to write a superseded pre-D22 anchor path; see "
                "docs/d19-pre-d22-bench-supersession.md")
    return resolved


class FirewallViolation(ValueError):
    """A complete, path-aware list of record firewall violations."""


class _LeafValidator:
    def error(self, value, path):
        raise NotImplementedError


class Const(_LeafValidator):
    def __init__(self, expected):
        self.expected = expected

    def error(self, value, path):
        if type(value) is not type(self.expected) or value != self.expected:
            return f"{path}: expected constant {self.expected!r}"
        return None


class Enum(_LeafValidator):
    def __init__(self, values):
        self.values = tuple(values)

    def error(self, value, path):
        if not any(type(value) is type(item) and value == item
                   for item in self.values):
            return f"{path}: expected one of {self.values!r}"
        return None


class PosInt(_LeafValidator):
    def error(self, value, path):
        if type(value) is not int or value <= 0:
            return f"{path}: expected a positive integer"
        return None


class NonNegInt(_LeafValidator):
    def error(self, value, path):
        if type(value) is not int or value < 0:
            return f"{path}: expected a nonnegative integer"
        return None


class FinFloat(_LeafValidator):
    def __init__(self, minimum=None, inclusive=True):
        self.minimum = minimum
        self.inclusive = inclusive

    def error(self, value, path):
        if type(value) is not float or not math.isfinite(value):
            return f"{path}: expected a finite float"
        if self.minimum is not None:
            good = value >= self.minimum if self.inclusive else value > self.minimum
            if not good:
                relation = ">=" if self.inclusive else ">"
                return f"{path}: expected a finite float {relation} {self.minimum}"
        return None


class Sha256(_LeafValidator):
    def __init__(self, expected=None):
        self.expected = expected

    def error(self, value, path):
        if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
            return f"{path}: expected 64 lowercase hexadecimal characters"
        if self.expected is not None and value != self.expected:
            return f"{path}: does not match the pinned digest"
        return None


class Sha1Hex(_LeafValidator):
    def error(self, value, path):
        if type(value) is not str or re.fullmatch(r"[0-9a-f]{40}", value) is None:
            return f"{path}: expected 40 lowercase hexadecimal characters"
        return None


class Str(_LeafValidator):
    def __init__(self, maxlen):
        self.maxlen = maxlen

    def error(self, value, path):
        if type(value) is not str or len(value) > self.maxlen:
            return f"{path}: expected a string of at most {self.maxlen} characters"
        return None


class TrueOnly(_LeafValidator):
    def error(self, value, path):
        if value is not True:
            return f"{path}: expected exactly True"
        return None


class Nullable(_LeafValidator):
    def __init__(self, validator):
        self.validator = validator

    def error(self, value, path):
        if value is None:
            return None
        return self.validator.error(value, path)


class ListOf(_LeafValidator):
    def __init__(self, item_schema):
        self.item_schema = item_schema

    def error(self, value, path):
        if type(value) is not list:
            return f"{path}: expected a list"
        return None


_NONNEG_FLOAT = FinFloat(minimum=0.0)

SCHEMA = {
    "record": {
        "kind": Const(SCHEMA_KIND),
        "schema_version": Const(SCHEMA_VERSION),
        "firewall_note": Const(FIREWALL_NOTE),
    },
    "threads": {
        "threads_requested": Enum(ALLOWED_THREADS),
        "omp_num_threads_configured": Enum(ALLOWED_THREADS),
        "mkl_num_threads_configured": Enum(ALLOWED_THREADS),
        "openblas_num_threads_configured": Enum(ALLOWED_THREADS),
        "veclib_maximum_threads_configured": Enum(ALLOWED_THREADS),
        "torch_num_threads_effective": Enum(ALLOWED_THREADS),
        "torch_num_interop_threads_effective": PosInt(),
        "thread_configuration_checks_passed": TrueOnly(),
        "thread_control_scope_note": Const(THREAD_SCOPE_NOTE),
    },
    "environment": {
        "timestamp": Str(40),
        "git_sha": Sha1Hex(),
        "python": Str(32),
        "platform": Str(160),
        "hostname": Str(120),
        "cpu_count": PosInt(),
        "torch": Str(32),
        "gpytorch": Str(32),
        "pyro": Str(32),
        "numpy": Str(32),
    },
    "run_config": {
        "scale": Enum(("sub", "full")),
        "design_label": Const(DESIGN_LABEL),
        "n_points": PosInt(),
        "seed": NonNegInt(),
        "budget_s": FinFloat(minimum=0.0, inclusive=False),
        "n_iter_map": PosInt(),
        "n_iter_profile": PosInt(),
        "n_prior_evals_stage1": PosInt(),
        "n_prior_evals_stage2": PosInt(),
    },
    "data_provenance": {
        "openml_data_id": Const(MAUNA_OPENML_DATA_ID),
        "source": Const("vendored"),
        "canonical_sha256": Sha256(EXPECTED_CANONICAL_SHA256),
        "n_train_points": Const(EXPECTED_N_TRAIN_POINTS),
    },
    "structure": {
        "n_sampled_sites": Const(EXPECTED_N_SAMPLED_SITES),
        "dim_unconstrained": Const(EXPECTED_DIM_UNCONSTRAINED),
    },
    "timings": {
        "map_fit": {
            "status": Const("measured"),
            "n_iter": PosInt(),
            "total_s": _NONNEG_FLOAT,
            "per_iter_s": _NONNEG_FLOAT,
        },
        "initialize_model": {
            "status": Const("measured"),
            "total_s": _NONNEG_FLOAT,
        },
        "potential_value_eval": {
            "status": Const("measured"),
            "median_s": _NONNEG_FLOAT,
            "mean_s": _NONNEG_FLOAT,
            "min_s": _NONNEG_FLOAT,
            "max_s": _NONNEG_FLOAT,
            "reps": PosInt(),
            "warmup_calls": NonNegInt(),
        },
        "gradient": {
            "status": Const("measured"),
            "median_s": _NONNEG_FLOAT,
            "mean_s": _NONNEG_FLOAT,
            "min_s": _NONNEG_FLOAT,
            "max_s": _NONNEG_FLOAT,
            "reps": PosInt(),
            "warmup_calls": NonNegInt(),
        },
        "hessian": {
            "status": Enum(("measured", "skipped_for_budget")),
            "total_s": Nullable(_NONNEG_FLOAT),
            "extrapolated_from_gradient_s": Nullable(_NONNEG_FLOAT),
        },
        "prior_eval_stage1": {
            "status": Const("measured"),
            "n_evals": PosInt(),
            "total_s": _NONNEG_FLOAT,
            "per_eval_s": _NONNEG_FLOAT,
            "n_failed_potential_evals": NonNegInt(),
        },
        "prior_eval_stage2": {
            "status": Enum(("measured", "extrapolated_from_stage1")),
            "n_evals": PosInt(),
            "total_s": _NONNEG_FLOAT,
            "per_eval_s": _NONNEG_FLOAT,
            "n_failed_potential_evals": Nullable(NonNegInt()),
        },
        "profile_grid_point": {
            "status": Const("measured"),
            "n_iter": PosInt(),
            "total_s": _NONNEG_FLOAT,
            "per_iter_s": _NONNEG_FLOAT,
            "laplace_det_bound_s": _NONNEG_FLOAT,
            "composite_per_point_est_s": _NONNEG_FLOAT,
        },
    },
    "warning_counts": ListOf({
        "category": Enum(WARNING_CATEGORIES),
        "count": PosInt(),
    }),
    "totals": {
        "elapsed_s": _NONNEG_FLOAT,
    },
}


_VALIDATION_TOKEN = object()


class _ValidatedRecord(dict):
    """Unforgeable proof that `validate_record` accepted this mapping.

    A bare `dict` subclass would be constructible by any caller, so the marker
    would attest to nothing: `_ValidatedRecord({"ess": 1})` could otherwise
    reach the writer and replace a valid artifact with forbidden content. Only
    `validate_record` holds the token.
    """

    def __init__(self, mapping, token=None):
        if token is not _VALIDATION_TOKEN:
            raise FirewallViolation(
                "_ValidatedRecord is constructible only by validate_record()")
        super().__init__(mapping)


def _path(parent, key):
    return f"{parent}.{key}"


def _key_is_forbidden(key):
    lowered = key.lower()
    if lowered in FORBIDDEN_EXACT_KEYS:
        return True
    return any(token in lowered for token in FORBIDDEN_KEY_SUBSTRINGS)


def _scan_all_keys(value, path, errors):
    if type(value) is dict:
        for key, child in value.items():
            child_path = _path(path, key)
            if type(key) is not str:
                errors.append(f"{child_path}: object keys must be strings")
            elif _key_is_forbidden(key):
                errors.append(f"{child_path}: forbidden key substring")
            _scan_all_keys(child, child_path, errors)
    elif type(value) is list:
        for index, child in enumerate(value):
            _scan_all_keys(child, f"{path}[{index}]", errors)


def _walk_schema(schema, value, path, errors):
    if isinstance(schema, ListOf):
        error = schema.error(value, path)
        if error is not None:
            errors.append(error)
            return
        for index, item in enumerate(value):
            _walk_schema(schema.item_schema, item, f"{path}[{index}]", errors)
        return

    if isinstance(schema, _LeafValidator):
        error = schema.error(value, path)
        if error is not None:
            errors.append(error)
        return

    if type(value) is not dict:
        errors.append(f"{path}: expected an object")
        return

    expected = set(schema)
    actual = set(value)
    for key in sorted(expected - actual):
        errors.append(f"{_path(path, key)}: missing required key")
    for key in sorted(actual - expected, key=str):
        errors.append(f"{_path(path, key)}: unknown key")
    for key in schema:
        if key in value:
            _walk_schema(schema[key], value[key], _path(path, key), errors)


def _get(record, *parts):
    value = record
    for part in parts:
        if type(value) is not dict or part not in value:
            return None
        value = value[part]
    return value


def _finite_nonnegative(value):
    return type(value) is float and math.isfinite(value) and value >= 0.0


def _validate_cross_fields(record, errors):
    hessian = _get(record, "timings", "hessian")
    if type(hessian) is dict:
        status = hessian.get("status")
        total_s = hessian.get("total_s")
        estimate = hessian.get("extrapolated_from_gradient_s")
        if status == "measured" and not (
                _finite_nonnegative(total_s) and estimate is None):
            errors.append("$.timings.hessian: measured status requires a finite "
                          "total_s and null extrapolated_from_gradient_s")
        if status == "skipped_for_budget" and not (
                total_s is None and _finite_nonnegative(estimate)):
            errors.append("$.timings.hessian: skipped status requires null "
                          "total_s and a finite extrapolated_from_gradient_s")

    stage2 = _get(record, "timings", "prior_eval_stage2")
    if type(stage2) is dict:
        status = stage2.get("status")
        failures = stage2.get("n_failed_potential_evals")
        if status == "measured" and not (
                type(failures) is int and failures >= 0):
            errors.append("$.timings.prior_eval_stage2: measured status requires "
                          "an integer failure count")
        if status == "extrapolated_from_stage1" and failures is not None:
            errors.append("$.timings.prior_eval_stage2: extrapolated status "
                          "requires a null failure count")

    scale = _get(record, "run_config", "scale")
    n_points = _get(record, "run_config", "n_points")
    if scale in SCALE_N_POINTS and n_points != SCALE_N_POINTS[scale]:
        errors.append("$.run_config.n_points: does not agree with scale")

    equalities = (
        (("timings", "map_fit", "n_iter"),
         ("run_config", "n_iter_map")),
        (("timings", "profile_grid_point", "n_iter"),
         ("run_config", "n_iter_profile")),
        (("timings", "prior_eval_stage1", "n_evals"),
         ("run_config", "n_prior_evals_stage1")),
        (("timings", "prior_eval_stage2", "n_evals"),
         ("run_config", "n_prior_evals_stage2")),
    )
    for left, right in equalities:
        left_value = _get(record, *left)
        right_value = _get(record, *right)
        if left_value is not None and right_value is not None \
                and left_value != right_value:
            errors.append(f"$.{'.'.join(left)}: does not agree with "
                          f"$.{'.'.join(right)}")

    threads = _get(record, "threads")
    if type(threads) is dict:
        names = (
            "threads_requested", "omp_num_threads_configured",
            "mkl_num_threads_configured", "openblas_num_threads_configured",
            "veclib_maximum_threads_configured", "torch_num_threads_effective",
        )
        values = [threads.get(name) for name in names]
        if all(value is not None for value in values) and len(set(values)) != 1:
            errors.append("$.threads: configured thread fields do not all agree")

    for name in ("potential_value_eval", "gradient"):
        block = _get(record, "timings", name)
        if type(block) is dict:
            minimum = block.get("min_s")
            median = block.get("median_s")
            maximum = block.get("max_s")
            if all(_finite_nonnegative(item)
                   for item in (minimum, median, maximum)) \
                    and not minimum <= median <= maximum:
                errors.append(f"$.timings.{name}: requires min_s <= median_s <= max_s")

    warning_counts = _get(record, "warning_counts")
    if type(warning_counts) is list and all(type(item) is dict
                                             for item in warning_counts):
        categories = [item.get("category") for item in warning_counts]
        if categories != sorted(categories) or len(categories) != len(set(categories)):
            errors.append("$.warning_counts: categories must be unique and sorted")

    timestamp = _get(record, "environment", "timestamp")
    if type(timestamp) is str:
        try:
            parsed = datetime.fromisoformat(timestamp)
            if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
                raise ValueError
        except (TypeError, ValueError):
            errors.append("$.environment.timestamp: expected ISO-8601 UTC")

    stage1 = _get(record, "timings", "prior_eval_stage1")
    if type(stage1) is dict:
        failures = stage1.get("n_failed_potential_evals")
        n_evals = stage1.get("n_evals")
        if type(failures) is int and type(n_evals) is int and failures > n_evals:
            errors.append("$.timings.prior_eval_stage1.n_failed_potential_evals: "
                          "cannot exceed n_evals")


def validate_record(record):
    """Validate the closed record and return an isolated validated mapping."""
    errors = []
    _scan_all_keys(record, "$", errors)
    _walk_schema(SCHEMA, record, "$", errors)
    if type(record) is dict:
        _validate_cross_fields(record, errors)
    if errors:
        raise FirewallViolation("; ".join(errors))
    return _ValidatedRecord(copy.deepcopy(record), _VALIDATION_TOKEN)


def timed(fn, reps=5, warmup=1):
    """Time calls while discarding every return value."""
    if type(reps) is not int or reps <= 0:
        raise ValueError("reps must be positive")
    if type(warmup) is not int or warmup < 0:
        raise ValueError("warmup must be nonnegative")
    for _ in range(warmup):
        fn()
    durations = []
    for _ in range(reps):
        start = time.perf_counter()
        fn()
        durations.append(float(time.perf_counter() - start))
    return {
        "median_s": float(statistics.median(durations)),
        "mean_s": float(statistics.mean(durations)),
        "min_s": float(min(durations)),
        "max_s": float(max(durations)),
        "reps": int(reps),
        "warmup_calls": int(warmup),
    }


@contextmanager
def _capture_file_descriptors():
    """Discard writes to fds 1 and 2, restoring both even on failure."""
    def best_effort_flush():
        # Workload code may have closed or replaced sys.stdout/sys.stderr. A
        # raising flush must never prevent fd restoration below.
        for stream in (sys.stdout, sys.stderr):
            try:
                stream.flush()
            except Exception:
                pass

    saved_stdout = saved_stderr = devnull = None
    best_effort_flush()
    try:
        # Acquisition inside the try so a partial failure still releases
        # whatever was already acquired.
        saved_stdout = os.dup(1)
        saved_stderr = os.dup(2)
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, 1)
        os.dup2(devnull, 2)
        yield
    finally:
        best_effort_flush()
        # Restore each fd independently: a failure on one must not strand the
        # other, and neither may suppress the in-flight exception.
        for saved, target in ((saved_stdout, 1), (saved_stderr, 2)):
            if saved is not None:
                try:
                    os.dup2(saved, target)
                except OSError:
                    pass
        for descriptor in (devnull, saved_stdout, saved_stderr):
            if descriptor is not None:
                try:
                    os.close(descriptor)
                except OSError:
                    pass


def _summarize_warnings(captured):
    counts = {}
    for item in captured:
        category_name = getattr(item.category, "__name__", "")
        bucket = category_name if category_name in WARNING_CATEGORIES else "other"
        counts[bucket] = counts.get(bucket, 0) + 1
    return [{"category": category, "count": counts[category]}
            for category in sorted(counts)]


def _git_sha():
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT,
        capture_output=True, text=True, timeout=10, check=False)
    return completed.stdout.strip()


def _atomic_write_json(record, target):
    if not isinstance(record, _ValidatedRecord):
        raise FirewallViolation("refusing to persist an unvalidated record")
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=target.parent,
                prefix=f".{target.name}.", suffix=".tmp", delete=False) as handle:
            temporary_path = Path(handle.name)
            json.dump(record, handle, indent=2, sort_keys=True, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, target)
        temporary_path = None
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except FileNotFoundError:
                pass


REPORT_KEYS = frozenset({"kind", "scale", "n_points", "elapsed_s"})


def _validate_and_write(record, target):
    """Validate, render, scan, and only then commit.

    Ordering matters: every fallible check that could reject the run happens
    BEFORE `os.replace`, so a rejected run leaves any existing artifact
    untouched and writes nothing. The returned report is printed by the caller
    after the commit; a failure of that final `print` (a closed pipe, say)
    cannot un-commit an artifact that already passed every firewall check, and
    is not treated as a firewall failure.
    """
    validated = validate_record(record)
    report = _render_stdout_report(validated)
    _atomic_write_json(validated, target)
    return validated, report


def _render_stdout_report(record):
    if not isinstance(record, _ValidatedRecord):
        raise FirewallViolation("refusing to report an unvalidated record")
    report = {
        "kind": record["record"]["kind"],
        "scale": record["run_config"]["scale"],
        "n_points": record["run_config"]["n_points"],
        "elapsed_s": record["totals"]["elapsed_s"],
    }
    if set(report) != REPORT_KEYS:
        raise FirewallViolation("stdout report key inventory is not exact")
    # Both denial layers, over keys AND rendered values: the exact layer holds
    # tokens (`ess`, `sample`, `map_values`) the substring layer deliberately
    # gave up to avoid colliding with ratified keys, so scanning only the
    # substring layer would let them through.
    for key in report:
        if _key_is_forbidden(key):
            raise FirewallViolation("stdout report carries a forbidden key")
    rendered = json.dumps(report, sort_keys=True)
    lowered = rendered.lower()
    if any(token in lowered for token in FORBIDDEN_KEY_SUBSTRINGS):
        raise FirewallViolation("stdout report failed the forbidden-token scan")
    if any(re.search(rf"\b{re.escape(token)}\b", lowered)
           for token in FORBIDDEN_EXACT_KEYS):
        raise FirewallViolation("stdout report failed the exact-token scan")
    return rendered


def _measurement_block(stats):
    return {
        "status": "measured",
        "median_s": stats["median_s"],
        "mean_s": stats["mean_s"],
        "min_s": stats["min_s"],
        "max_s": stats["max_s"],
        "reps": stats["reps"],
        "warmup_calls": stats["warmup_calls"],
    }


def parse_args(argv=None):
    """Argument parsing ONLY. Any SystemExit raised here is argparse's own and
    carries nothing but the user's CLI tokens, so it is allowed to print."""
    parser = argparse.ArgumentParser(
        description="D19 timing-only planning benchmark")
    parser.add_argument("--scale", choices=("sub", "full"), required=True)
    parser.add_argument("--threads", type=int, choices=ALLOWED_THREADS, required=True)
    parser.add_argument("--budget-s", type=float, default=240.0)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args(argv)
    if args.threads not in ALLOWED_THREADS:
        parser.error("--threads must be one of 1, 2, 3, 4")
    if not math.isfinite(args.budget_s) or args.budget_s <= 0.0:
        parser.error("--budget-s must be a finite positive float")
    return args


def main(argv=None):
    return run(parse_args(argv))


def run(args):
    threads = args.threads

    # Resolve and vet the destination BEFORE any heavy import, data load, or
    # model construction, so a refused target costs nothing and touches nothing.
    target = reject_superseded_target(target_path(args.out_dir, args.scale, threads))

    preimported = [name for name in HEAVY_MODULES if name in sys.modules]
    if preimported:
        raise RuntimeError("heavy scientific module was imported before thread setup")

    requested_text = str(threads)
    for name in THREAD_ENV_VARS:
        os.environ[name] = requested_text
    if any(os.environ.get(name) != requested_text for name in THREAD_ENV_VARS):
        raise RuntimeError("thread environment verification failed")

    started = time.perf_counter()
    seed = 0
    n_iter_map = 300
    n_iter_profile = 150
    n_prior_stage1 = 100
    n_prior_stage2 = 1000

    def remaining():
        return args.budget_s - (time.perf_counter() - started)

    with warnings.catch_warnings(record=True) as captured_warnings:
        warnings.simplefilter("always")
        with _capture_file_descriptors():
            import gpytorch
            import numpy as np
            import pyro
            import torch

            # Verify intra-op threads the moment torch is available, BEFORE any
            # project module is imported. A failed thread contract then aborts
            # without pulling in bistar_gp at all, so nothing can load data or
            # build a model on an unverified thread configuration.
            torch.set_num_threads(threads)
            if torch.get_num_threads() != threads:
                raise RuntimeError("torch intra-op thread verification failed")
            torch_interop = int(torch.get_num_interop_threads())
            torch.set_default_dtype(torch.float64)

            from pyro.infer.autoguide.initialization import init_to_value
            from pyro.infer.mcmc.util import initialize_model

            from bistar_gp.data import load_mauna_loa_training
            from bistar_gp.fit import (DEFAULT_JITTER, _hmc_pyro_model,
                                       _map_init_values, fit_map, sample_prior)
            from bistar_gp.model import (apply_hp_value, build_likelihood,
                                         build_mauna_loa_kernels, build_model)

            environment = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "git_sha": _git_sha(),
                "python": platform.python_version(),
                "platform": platform.platform(),
                "hostname": platform.node(),
                "cpu_count": int(os.cpu_count() or 1),
                "torch": str(torch.__version__),
                "gpytorch": str(gpytorch.__version__),
                "pyro": str(pyro.__version__),
                "numpy": str(np.__version__),
            }

            x_train, y_train, training_metadata = load_mauna_loa_training(
                normalize=True, test_years=5.0)
            # C3 permits exactly three provenance values, and requires the
            # digest the loader RETURNED rather than a compile-time constant:
            # the loader verifies it against the vendored dataset and raises on
            # mismatch, so this is the value actually checked during this run.
            # Every other metadata field (normalization statistics, holdout
            # count, split rule, raw/monthly counts) is discarded here.
            dataset_source = str(training_metadata["source"])
            canonical_sha256 = str(training_metadata["canonical_sha256"])
            del training_metadata
            n_full = int(len(x_train))
            if n_full != EXPECTED_N_TRAIN_POINTS:
                raise AssertionError("unexpected training-point count")

            if args.scale == "sub":
                sub = np.round(np.linspace(0, n_full - 1, 150)).astype(int)
                x_use, y_use = x_train[sub], y_train[sub]
            else:
                x_use, y_use = x_train, y_train
            n_points = int(len(x_use))
            if n_points != SCALE_N_POINTS[args.scale]:
                raise AssertionError("scale selection produced an unexpected size")

            kernels, component_names = build_mauna_loa_kernels()
            likelihood = build_likelihood()
            model, likelihood = build_model(
                x_use, y_use, kernels, component_names, likelihood)

            map_stats = timed(
                lambda: fit_map(model, likelihood, x_use, y_use,
                                n_iter=n_iter_map, lr=0.02, verbose=False),
                reps=1, warmup=0)
            map_noise = float(likelihood.noise.item())

            model.train()
            likelihood.train()
            pyro.clear_param_store()
            map_values = _map_init_values(model)
            initialized = []

            def initialize():
                initialized[:] = initialize_model(
                    partial(_hmc_pyro_model, model),
                    model_args=(x_use, y_use),
                    init_strategy=init_to_value(values=map_values))

            initialize_stats = timed(initialize, reps=1, warmup=0)
            init_params, potential_fn, transforms, prototype = initialized
            del transforms, prototype

            sites = sorted(init_params)
            if len(sites) != EXPECTED_N_SAMPLED_SITES \
                    or any("period" in name for name in sites):
                raise AssertionError("sample-site inventory check failed")
            shapes = {name: init_params[name].reshape(-1).shape[0]
                      for name in sites}
            u_map = torch.cat(
                [init_params[name].reshape(-1).double() for name in sites])
            dim_unconstrained = int(len(u_map))
            if dim_unconstrained != EXPECTED_DIM_UNCONSTRAINED:
                raise AssertionError("unexpected unconstrained dimension")

            def unflatten(vector):
                result = {}
                offset = 0
                for name in sites:
                    width = shapes[name]
                    result[name] = vector[offset:offset + width].reshape(
                        init_params[name].shape)
                    offset += width
                return result

            def potential_u(vector):
                with gpytorch.settings.cholesky_jitter(DEFAULT_JITTER):
                    return potential_fn(unflatten(vector))

            potential_stats = timed(
                lambda: potential_u(u_map.clone()), reps=5, warmup=1)

            def gradient_eval():
                vector = u_map.clone().requires_grad_(True)
                potential = potential_u(vector)
                torch.autograd.grad(potential, vector)

            gradient_stats = timed(gradient_eval, reps=5, warmup=1)

            hessian_estimate = float(
                gradient_stats["median_s"] * dim_unconstrained * 6)
            if remaining() > max(3.0 * hessian_estimate, 30.0):
                def construct_hessian():
                    matrix = torch.autograd.functional.hessian(
                        potential_u, u_map.clone())
                    del matrix

                hessian_stats = timed(construct_hessian, reps=1, warmup=0)
                hessian_record = {
                    "status": "measured",
                    "total_s": hessian_stats["median_s"],
                    "extrapolated_from_gradient_s": None,
                }
            else:
                hessian_record = {
                    "status": "skipped_for_budget",
                    "total_s": None,
                    "extrapolated_from_gradient_s": hessian_estimate,
                }

            prior_values = sample_prior(model, n_samples=n_prior_stage2, seed=seed)
            prior_names = list(prior_values)
            marginal_likelihood = gpytorch.mlls.ExactMarginalLogLikelihood(
                likelihood, model)
            model.train()
            likelihood.train()

            def evaluate_prior(index):
                for name in prior_names:
                    apply_hp_value(
                        model, likelihood, name,
                        torch.tensor(float(prior_values[name][index])))
                with gpytorch.settings.cholesky_jitter(DEFAULT_JITTER):
                    prediction = model(x_use)
                    marginal_likelihood(prediction, y_use)

            for index in range(3):
                try:
                    evaluate_prior(index)
                except Exception:
                    pass

            def evaluate_batch(count):
                failures = 0
                for index in range(count):
                    try:
                        evaluate_prior(index)
                    except Exception:
                        failures += 1
                return failures

            stage1_failures = []

            def stage1_batch():
                stage1_failures[:] = [evaluate_batch(n_prior_stage1)]

            stage1_stats = timed(stage1_batch, reps=1, warmup=0)
            stage1_total = stage1_stats["median_s"]
            stage1_record = {
                "status": "measured",
                "n_evals": n_prior_stage1,
                "total_s": stage1_total,
                "per_eval_s": float(stage1_total / n_prior_stage1),
                "n_failed_potential_evals": int(stage1_failures[0]),
            }

            if remaining() > 10.0 * stage1_total * 1.3 + 30.0:
                stage2_failures = []

                def stage2_batch():
                    stage2_failures[:] = [evaluate_batch(n_prior_stage2)]

                stage2_stats = timed(stage2_batch, reps=1, warmup=0)
                stage2_total = stage2_stats["median_s"]
                stage2_record = {
                    "status": "measured",
                    "n_evals": n_prior_stage2,
                    "total_s": stage2_total,
                    "per_eval_s": float(stage2_total / n_prior_stage2),
                    "n_failed_potential_evals": int(stage2_failures[0]),
                }
            else:
                stage2_total = float(stage1_total * 10.0)
                stage2_record = {
                    "status": "extrapolated_from_stage1",
                    "n_evals": n_prior_stage2,
                    "total_s": stage2_total,
                    "per_eval_s": float(stage2_total / n_prior_stage2),
                    "n_failed_potential_evals": None,
                }

            for name, value in map_values.items():
                apply_hp_value(model, likelihood, name, value)
            likelihood.noise = map_noise * 2.0
            likelihood.noise_covar.raw_noise.requires_grad_(False)
            free_parameters = [parameter for parameter in model.parameters()
                               if parameter.requires_grad]
            optimizer = torch.optim.Adam(free_parameters, lr=0.02)

            def profile_optimization():
                for _ in range(n_iter_profile):
                    optimizer.zero_grad()
                    with gpytorch.settings.cholesky_jitter(DEFAULT_JITTER):
                        prediction = model(x_use)
                        objective = -marginal_likelihood(prediction, y_use)
                    objective.backward()
                    optimizer.step()

            try:
                profile_stats = timed(profile_optimization, reps=1, warmup=0)
            finally:
                likelihood.noise_covar.raw_noise.requires_grad_(True)
            profile_total = profile_stats["median_s"]
            laplace_bound = (
                hessian_record["total_s"]
                if hessian_record["status"] == "measured"
                else hessian_record["extrapolated_from_gradient_s"])

            timings = {
                "map_fit": {
                    "status": "measured",
                    "n_iter": n_iter_map,
                    "total_s": map_stats["median_s"],
                    "per_iter_s": float(map_stats["median_s"] / n_iter_map),
                },
                "initialize_model": {
                    "status": "measured",
                    "total_s": initialize_stats["median_s"],
                },
                "potential_value_eval": _measurement_block(potential_stats),
                "gradient": _measurement_block(gradient_stats),
                "hessian": hessian_record,
                "prior_eval_stage1": stage1_record,
                "prior_eval_stage2": stage2_record,
                "profile_grid_point": {
                    "status": "measured",
                    "n_iter": n_iter_profile,
                    "total_s": profile_total,
                    "per_iter_s": float(profile_total / n_iter_profile),
                    "laplace_det_bound_s": float(laplace_bound),
                    "composite_per_point_est_s": float(
                        profile_total + laplace_bound),
                },
            }

    record = {
        "record": {
            "kind": SCHEMA_KIND,
            "schema_version": SCHEMA_VERSION,
            "firewall_note": FIREWALL_NOTE,
        },
        "threads": {
            "threads_requested": threads,
            "omp_num_threads_configured": threads,
            "mkl_num_threads_configured": threads,
            "openblas_num_threads_configured": threads,
            "veclib_maximum_threads_configured": threads,
            "torch_num_threads_effective": threads,
            "torch_num_interop_threads_effective": torch_interop,
            "thread_configuration_checks_passed": True,
            "thread_control_scope_note": THREAD_SCOPE_NOTE,
        },
        "environment": environment,
        "run_config": {
            "scale": args.scale,
            "design_label": DESIGN_LABEL,
            "n_points": n_points,
            "seed": seed,
            "budget_s": float(args.budget_s),
            "n_iter_map": n_iter_map,
            "n_iter_profile": n_iter_profile,
            "n_prior_evals_stage1": n_prior_stage1,
            "n_prior_evals_stage2": n_prior_stage2,
        },
        "data_provenance": {
            "openml_data_id": MAUNA_OPENML_DATA_ID,
            "source": dataset_source,
            "canonical_sha256": canonical_sha256,
            "n_train_points": n_full,
        },
        "structure": {
            "n_sampled_sites": EXPECTED_N_SAMPLED_SITES,
            "dim_unconstrained": dim_unconstrained,
        },
        "timings": timings,
        "warning_counts": _summarize_warnings(captured_warnings),
        "totals": {
            "elapsed_s": float(time.perf_counter() - started),
        },
    }

    _validated, report = _validate_and_write(record, target)
    print(report)


def _abort(exception_class_name):
    print(
        f"aborted: {exception_class_name} (message suppressed by the v1.2 "
        "persistence firewall)",
        file=sys.stderr,
    )
    raise SystemExit(1) from None


def _firewalled_main(argv=None):
    """Sanitized CLI entry point.

    Parsing runs OUTSIDE the guard: argparse's SystemExit carries only the
    user's own CLI tokens and must stay readable. Everything after parsing runs
    inside it, INCLUDING SystemExit: a post-parse `SystemExit("noise=0.123")`
    would otherwise have its argument printed verbatim by the interpreter at
    exit, straight past the class-name-only firewall.
    """
    args = parse_args(argv)
    try:
        run(args)
    except SystemExit as exc:
        if exc.code in (0, None):
            raise
        _abort("SystemExit")
    except BaseException as exc:
        _abort(type(exc).__name__)


if __name__ == "__main__":
    _firewalled_main()
