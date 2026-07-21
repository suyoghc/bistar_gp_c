"""Fail-closed validation for the staged D19 A7 timing evidence set."""

import argparse
import hashlib
import importlib.util
import json
import math
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


REPO_ROOT = Path(__file__).resolve().parents[1]
VEHICLE_PATH = REPO_ROOT / "experiments" / "d19_bench.py"
_VEHICLE_SPEC = importlib.util.spec_from_file_location(
    "_d19_frozen_bench_vehicle", VEHICLE_PATH)
if _VEHICLE_SPEC is None or _VEHICLE_SPEC.loader is None:
    raise ImportError(f"cannot load frozen vehicle at {VEHICLE_PATH}")
_VEHICLE = importlib.util.module_from_spec(_VEHICLE_SPEC)
_VEHICLE_SPEC.loader.exec_module(_VEHICLE)
validate_record = _VEHICLE.validate_record
FirewallViolation = _VEHICLE.FirewallViolation
FORBIDDEN_EXACT_KEYS = tuple(_VEHICLE.FORBIDDEN_EXACT_KEYS)
FORBIDDEN_KEY_SUBSTRINGS = tuple(_VEHICLE.FORBIDDEN_KEY_SUBSTRINGS)
del _VEHICLE


EXPECTED_VERSIONS = {
    "python": "3.11.14",
    "torch": "2.10.0+cu128",
    "gpytorch": "1.15.1",
    "pyro": "1.9.1",
    "numpy": "2.4.2",
}
EXPECTED_BUDGET_S = 600.0
EXPECTED_SEED = 0
EXPECTED_ITERATIONS = {
    "n_iter_map": 300,
    "n_iter_profile": 150,
    "n_prior_evals_stage1": 100,
    "n_prior_evals_stage2": 1000,
}
EXPECTED_N_POINTS = {"sub": 150, "full": 461}
FROZEN_NODE_SPECS = (
    "della-h17n[2-3]",
    "della-i13n[1-24]",
    "della-r3c1n[1-16]",
    "della-r3c2n[1-16]",
    "della-r3c3n[1-16]",
    "della-r3c4n[1-16]",
)
EXPECTED_ACTIVE_FEATURES = "intel,cascade,rh9"
EXPECTED_NODE_COUNT = 90
ANCHORS = {
    "bench_sub.json": (
        "ed5c7bf4467c83896dc43d46d17564f052c806808877b031733a16822eb070a2",
        3663,
    ),
    "bench_full.json": (
        "ea47270d599213187d9fbb6bb2e018b0c166fcd4c6ae5c4d6e476bd0b6ff5b34",
        3451,
    ),
}

CELL_ORDER = tuple(
    (scale, threads) for scale in ("sub", "full") for threads in (1, 2, 3, 4)
)
BENCH_FILES = tuple(
    f"bench_{scale}_threads_{threads}.json" for scale, threads in CELL_ORDER
)

# Independently transcribed from the D56 authorization. This is deliberately
# not derived from the vehicle's SCHEMA object.
EXPECTED_KEY_PATHS = frozenset((
    "record.kind",
    "record.schema_version",
    "record.firewall_note",
    "threads.threads_requested",
    "threads.omp_num_threads_configured",
    "threads.mkl_num_threads_configured",
    "threads.openblas_num_threads_configured",
    "threads.veclib_maximum_threads_configured",
    "threads.torch_num_threads_effective",
    "threads.torch_num_interop_threads_effective",
    "threads.thread_configuration_checks_passed",
    "threads.thread_control_scope_note",
    "environment.timestamp",
    "environment.git_sha",
    "environment.python",
    "environment.platform",
    "environment.hostname",
    "environment.cpu_count",
    "environment.torch",
    "environment.gpytorch",
    "environment.pyro",
    "environment.numpy",
    "run_config.scale",
    "run_config.design_label",
    "run_config.n_points",
    "run_config.seed",
    "run_config.budget_s",
    "run_config.n_iter_map",
    "run_config.n_iter_profile",
    "run_config.n_prior_evals_stage1",
    "run_config.n_prior_evals_stage2",
    "data_provenance.openml_data_id",
    "data_provenance.source",
    "data_provenance.canonical_sha256",
    "data_provenance.n_train_points",
    "structure.n_sampled_sites",
    "structure.dim_unconstrained",
    "timings.map_fit.status",
    "timings.map_fit.n_iter",
    "timings.map_fit.total_s",
    "timings.map_fit.per_iter_s",
    "timings.initialize_model.status",
    "timings.initialize_model.total_s",
    "timings.potential_value_eval.status",
    "timings.potential_value_eval.median_s",
    "timings.potential_value_eval.mean_s",
    "timings.potential_value_eval.min_s",
    "timings.potential_value_eval.max_s",
    "timings.potential_value_eval.reps",
    "timings.potential_value_eval.warmup_calls",
    "timings.gradient.status",
    "timings.gradient.median_s",
    "timings.gradient.mean_s",
    "timings.gradient.min_s",
    "timings.gradient.max_s",
    "timings.gradient.reps",
    "timings.gradient.warmup_calls",
    "timings.hessian.status",
    "timings.hessian.total_s",
    "timings.hessian.extrapolated_from_gradient_s",
    "timings.prior_eval_stage1.status",
    "timings.prior_eval_stage1.n_evals",
    "timings.prior_eval_stage1.total_s",
    "timings.prior_eval_stage1.per_eval_s",
    "timings.prior_eval_stage1.n_failed_potential_evals",
    "timings.prior_eval_stage2.status",
    "timings.prior_eval_stage2.n_evals",
    "timings.prior_eval_stage2.total_s",
    "timings.prior_eval_stage2.per_eval_s",
    "timings.prior_eval_stage2.n_failed_potential_evals",
    "timings.profile_grid_point.status",
    "timings.profile_grid_point.n_iter",
    "timings.profile_grid_point.total_s",
    "timings.profile_grid_point.per_iter_s",
    "timings.profile_grid_point.laplace_det_bound_s",
    "timings.profile_grid_point.composite_per_point_est_s",
    "warning_counts",
    "totals.elapsed_s",
))

CHECK_NAMES = (
    "V1 file set",
    "V2 strict JSON",
    "V3 vehicle firewall",
    "V4 key-path inventory",
    "V5 forbidden scans",
    "V6 finite nonnegative fields",
    "V7 filename and run configuration",
    "V8 thread agreement",
    "V9 provenance",
    "V10 node scope",
    "V11 log discipline",
    "V12 scheduler truth",
    "V13 timestamps",
    "V14 provenance manifest",
    "V15 superseded-anchor integrity",
)


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


def expand_node_pool(specs=FROZEN_NODE_SPECS):
    """Expand the six frozen single-range node specifications."""
    nodes = set()
    for spec in specs:
        match = re.fullmatch(r"([^\[]+)\[(\d+)-(\d+)\]", spec)
        if match is None:
            raise ValueError(f"malformed frozen node range: {spec}")
        prefix, first_text, last_text = match.groups()
        first = int(first_text)
        last = int(last_text)
        if first > last:
            raise ValueError(f"reversed frozen node range: {spec}")
        for number in range(first, last + 1):
            node = f"{prefix}{number}"
            if node in nodes:
                raise ValueError(f"duplicate expanded node: {node}")
            nodes.add(node)
    return nodes


def _sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _reject_json_constant(token):
    raise ValueError(f"non-standard JSON constant {token}")


def _object_without_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _load_json_strict(path):
    with path.open("r", encoding="utf-8", errors="strict") as handle:
        return json.load(
            handle,
            parse_constant=_reject_json_constant,
            object_pairs_hook=_object_without_duplicate_keys,
        )


def _filename_tokens(filename):
    match = re.fullmatch(r"bench_(sub|full)_threads_([1-4])\.json", filename)
    if match is None:
        return None
    return match.group(1), int(match.group(2))


def _inventory(value, prefix=""):
    paths = set()
    if type(value) is not dict:
        return paths
    for key, child in value.items():
        path = f"{prefix}.{key}" if prefix else str(key)
        if path == "warning_counts":
            paths.add(path)
            continue
        if type(child) is dict:
            paths.update(_inventory(child, path))
        else:
            paths.add(path)
    return paths


def _scan_forbidden_text(text):
    lowered = text.lower()
    found = []
    for token in FORBIDDEN_KEY_SUBSTRINGS:
        if token in lowered:
            found.append(f"substring {token!r}")
    for token in FORBIDDEN_EXACT_KEYS:
        if re.search(rf"\b{re.escape(token)}\b", lowered) is not None:
            found.append(f"whole-word token {token!r}")
    return found


def _artifact_scan_text(record):
    sanitized = json.loads(json.dumps(record))
    record_block = sanitized.get("record")
    if type(record_block) is dict:
        record_block.pop("firewall_note", None)
    threads_block = sanitized.get("threads")
    if type(threads_block) is dict:
        threads_block.pop("thread_control_scope_note", None)
    return json.dumps(sanitized, sort_keys=True).lower()


def _walk_numeric_fields(value, path="$"):
    problems = []
    if type(value) is dict:
        for key, child in value.items():
            child_path = f"{path}.{key}"
            count_field = (
                key.startswith("n_")
                or key == "count"
                or key.endswith("_count")
                or key in {
                    "cpu_count", "reps", "warmup_calls", "threads_requested",
                    "omp_num_threads_configured", "mkl_num_threads_configured",
                    "openblas_num_threads_configured",
                    "veclib_maximum_threads_configured",
                    "torch_num_threads_effective",
                    "torch_num_interop_threads_effective",
                }
            )
            if (key.endswith("_s") or count_field) and child is not None:
                numeric = type(child) in (int, float)
                finite = numeric and math.isfinite(float(child))
                if not finite or child < 0:
                    problems.append(
                        f"{child_path} is not a finite nonnegative number")
            problems.extend(_walk_numeric_fields(child, child_path))
    elif type(value) is list:
        for index, child in enumerate(value):
            problems.extend(_walk_numeric_fields(child, f"{path}[{index}]"))
    return problems


def _parse_duration(value):
    match = re.fullmatch(r"(?:(\d+)-)?(\d+):(\d{2}):(\d{2})", value or "")
    if match is None:
        raise ValueError(f"invalid SLURM duration {value!r}")
    days, hours, minutes, seconds = match.groups()
    if int(minutes) >= 60 or int(seconds) >= 60:
        raise ValueError(f"invalid SLURM duration {value!r}")
    return int(days or 0) * 86400 + int(hours) * 3600 + int(minutes) * 60 + int(seconds)


def _parse_sacct(path, job_id):
    text = path.read_text(encoding="utf-8", errors="strict")
    lines = [line for line in text.splitlines() if line]
    if not lines:
        raise ValueError("job_metadata.txt is empty")
    header = lines[0].split("|")
    required = {
        "JobID", "State", "ExitCode", "Elapsed", "Timelimit", "TotalCPU",
        "MaxRSS", "NodeList", "Submit", "Start", "End",
    }
    if not required.issubset(set(header)):
        missing = sorted(required - set(header))
        raise ValueError(f"sacct header missing {missing}")
    rows = []
    for line in lines[1:]:
        values = line.split("|")
        if len(values) == len(header) + 1 and values[-1] == "":
            values.pop()
        if len(values) != len(header):
            raise ValueError(f"malformed sacct row {line!r}")
        rows.append(dict(zip(header, values)))
    parents = [row for row in rows if row.get("JobID") == str(job_id)]
    if len(parents) != 1:
        raise ValueError(f"expected one parent sacct row for job {job_id}, got {len(parents)}")
    return parents[0]


def _parse_local_cluster_time(value, cluster_zone):
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is not None:
        raise ValueError(f"sacct time unexpectedly carries an offset: {value!r}")
    return parsed.replace(tzinfo=cluster_zone)


def _parse_artifact_utc(value):
    parsed = datetime.fromisoformat(value)
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError(f"artifact timestamp is not UTC: {value!r}")
    return parsed.astimezone(timezone.utc)


def _parse_hash_lines(text, allowed_prefix=""):
    entries = {}
    problems = []
    for line in text.splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if match is None:
            problems.append(f"malformed hash line {line!r}")
            continue
        digest, filename = match.groups()
        if allowed_prefix and filename.startswith(allowed_prefix):
            filename = filename[len(allowed_prefix):]
        if filename in entries:
            problems.append(f"duplicate hash entry {filename}")
        else:
            entries[filename] = digest
    return entries, problems


def _infer_job_id(evidence_dir, supplied):
    if supplied is not None:
        if re.fullmatch(r"\d+", supplied) is None:
            return None, [f"malformed --job-id {supplied!r}"]
        return supplied, []
    try:
        names = [entry.name for entry in evidence_dir.iterdir()]
    except (OSError, ValueError) as exc:
        return None, [f"cannot inspect evidence directory: {exc}"]
    out_ids = {
        match.group(1) for name in names
        if (match := re.fullmatch(r"slurm-(\d+)\.out", name)) is not None
    }
    err_ids = {
        match.group(1) for name in names
        if (match := re.fullmatch(r"slurm-(\d+)\.err", name)) is not None
    }
    pairs = out_ids & err_ids
    if len(pairs) != 1:
        return None, [f"expected exactly one slurm out/err pair, found {sorted(pairs)}"]
    return next(iter(pairs)), []


def _v1(context):
    reasons = list(context["job_id_errors"])
    evidence_dir = context["evidence_dir"]
    job_id = context["job_id"]
    if job_id is None:
        return reasons or ["job id unavailable"]
    expected = set(BENCH_FILES) | {
        f"slurm-{job_id}.out", f"slurm-{job_id}.err",
        "job_metadata.txt", "PROVENANCE.sha256",
    }
    try:
        entries = list(evidence_dir.iterdir())
    except (OSError, ValueError) as exc:
        return reasons + [f"cannot list evidence directory: {exc}"]
    actual = {entry.name for entry in entries}
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing:
        reasons.append(f"missing entries: {missing}")
    if extra:
        reasons.append(f"unexpected entries: {extra}")
    for entry in entries:
        if entry.name in expected and not entry.is_file():
            reasons.append(f"expected regular file: {entry.name}")
    return reasons


def _v2(context):
    reasons = []
    records = {}
    for filename in BENCH_FILES:
        path = context["evidence_dir"] / filename
        try:
            records[filename] = _load_json_strict(path)
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
            reasons.append(f"{filename}: {exc}")
    context["records"] = records
    return reasons


def _v3(context):
    reasons = []
    for filename in BENCH_FILES:
        if filename not in context["records"]:
            reasons.append(f"{filename}: unavailable after V2")
            continue
        try:
            validate_record(context["records"][filename])
        except FirewallViolation as exc:
            reasons.append(f"{filename}: {exc}")
        except Exception as exc:
            reasons.append(f"{filename}: unexpected {type(exc).__name__}: {exc}")
    return reasons


def _v4(context):
    reasons = []
    for filename, record in context["records"].items():
        actual = _inventory(record)
        missing = sorted(EXPECTED_KEY_PATHS - actual)
        extra = sorted(actual - EXPECTED_KEY_PATHS)
        if missing:
            reasons.append(f"{filename}: missing paths {missing}")
        if extra:
            reasons.append(f"{filename}: extra paths {extra}")
        warning_counts = record.get("warning_counts") if type(record) is dict else None
        if type(warning_counts) is not list:
            reasons.append(f"{filename}: warning_counts is not a list")
        else:
            for index, item in enumerate(warning_counts):
                if type(item) is not dict or set(item) != {"category", "count"}:
                    reasons.append(
                        f"{filename}: warning_counts[{index}] keys are not exact")
    if len(context["records"]) != len(BENCH_FILES):
        reasons.append("not all artifacts were available for inventory")
    return reasons


def _v5(context):
    reasons = []
    for filename, record in context["records"].items():
        for finding in _scan_forbidden_text(_artifact_scan_text(record)):
            reasons.append(f"{filename}: {finding}")
    for suffix in ("out", "err"):
        path = context.get(f"{suffix}_path")
        if path is None:
            reasons.append(f"slurm .{suffix} path unavailable")
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="strict")
        except (OSError, UnicodeError) as exc:
            reasons.append(f"{path.name}: {exc}")
            continue
        context[f"{suffix}_text"] = text
        for finding in _scan_forbidden_text(text):
            reasons.append(f"{path.name}: {finding}")
    if len(context["records"]) != len(BENCH_FILES):
        reasons.append("not all artifacts were available for forbidden scans")
    return reasons


def _v6(context):
    reasons = []
    for filename, record in context["records"].items():
        for problem in _walk_numeric_fields(record):
            reasons.append(f"{filename}: {problem}")
    if len(context["records"]) != len(BENCH_FILES):
        reasons.append("not all artifacts were available for numeric checks")
    return reasons


def _v7(context):
    reasons = []
    for filename, record in context["records"].items():
        tokens = _filename_tokens(filename)
        if tokens is None:
            reasons.append(f"{filename}: malformed benchmark filename")
            continue
        scale, threads = tokens
        run_config = record.get("run_config", {}) if type(record) is dict else {}
        thread_block = record.get("threads", {}) if type(record) is dict else {}
        checks = {
            "run_config.scale": (run_config.get("scale"), scale),
            "threads.threads_requested": (thread_block.get("threads_requested"), threads),
            "run_config.budget_s": (run_config.get("budget_s"), EXPECTED_BUDGET_S),
            "run_config.seed": (run_config.get("seed"), EXPECTED_SEED),
            "run_config.n_points": (run_config.get("n_points"), EXPECTED_N_POINTS[scale]),
        }
        for field, expected in EXPECTED_ITERATIONS.items():
            checks[f"run_config.{field}"] = (run_config.get(field), expected)
        for field, (actual, expected) in checks.items():
            if actual != expected:
                reasons.append(f"{filename}: {field} {actual!r} != {expected!r}")
    if len(context["records"]) != len(BENCH_FILES):
        reasons.append("not all artifacts were available for filename checks")
    return reasons


def _v8(context):
    reasons = []
    fields = (
        "omp_num_threads_configured",
        "mkl_num_threads_configured",
        "openblas_num_threads_configured",
        "veclib_maximum_threads_configured",
        "torch_num_threads_effective",
        "torch_num_interop_threads_effective",
    )
    for filename, record in context["records"].items():
        tokens = _filename_tokens(filename)
        if tokens is None:
            continue
        threads = tokens[1]
        block = record.get("threads", {}) if type(record) is dict else {}
        if block.get("thread_configuration_checks_passed") is not True:
            reasons.append(f"{filename}: thread_configuration_checks_passed is not True")
        for field in fields:
            if block.get(field) != threads:
                reasons.append(
                    f"{filename}: threads.{field} {block.get(field)!r} != {threads}")
    if len(context["records"]) != len(BENCH_FILES):
        reasons.append("not all artifacts were available for thread checks")
    return reasons


def _v9(context):
    reasons = []
    common = None
    for filename, record in context["records"].items():
        environment = record.get("environment", {}) if type(record) is dict else {}
        if environment.get("git_sha") != context["expected_sha"]:
            reasons.append(f"{filename}: environment.git_sha mismatch")
        for field, expected in EXPECTED_VERSIONS.items():
            if environment.get(field) != expected:
                reasons.append(
                    f"{filename}: environment.{field} {environment.get(field)!r} != {expected!r}")
        fingerprint = tuple(
            environment.get(field) for field in
            ("platform", "hostname", "cpu_count", "python", "torch", "gpytorch", "pyro", "numpy")
        )
        if common is None:
            common = fingerprint
        elif fingerprint != common:
            reasons.append(f"{filename}: environment fingerprint disagrees with other artifacts")
    if len(context["records"]) != len(BENCH_FILES):
        reasons.append("not all artifacts were available for provenance checks")
    return reasons


def _sacct_row(context):
    if "sacct_row" in context:
        return context["sacct_row"], context.get("sacct_error")
    job_id = context["job_id"]
    if job_id is None:
        context["sacct_row"] = None
        context["sacct_error"] = "job id unavailable"
        return None, context["sacct_error"]
    try:
        row = _parse_sacct(context["evidence_dir"] / "job_metadata.txt", job_id)
    except (OSError, UnicodeError, ValueError) as exc:
        context["sacct_row"] = None
        context["sacct_error"] = str(exc)
        return None, str(exc)
    context["sacct_row"] = row
    context["sacct_error"] = None
    return row, None


def _v10(context):
    reasons = []
    try:
        nodes = expand_node_pool()
    except ValueError as exc:
        nodes = set()
        reasons.append(f"internal node-pool expansion error: {exc}")
    if len(nodes) != EXPECTED_NODE_COUNT:
        reasons.append(
            f"internal node-pool expansion produced {len(nodes)}, not {EXPECTED_NODE_COUNT}")
    hostnames = set()
    for filename, record in context["records"].items():
        environment = record.get("environment", {}) if type(record) is dict else {}
        hostname = str(environment.get("hostname", "")).split(".", 1)[0]
        hostnames.add(hostname)
        if hostname not in nodes:
            reasons.append(f"{filename}: hostname {hostname!r} outside frozen node pool")
    row, error = _sacct_row(context)
    if error is not None:
        reasons.append(f"sacct: {error}")
    elif len(hostnames) == 1 and row.get("NodeList") != next(iter(hostnames)):
        reasons.append(
            f"sacct NodeList {row.get('NodeList')!r} != artifact hostname {next(iter(hostnames))!r}")
    out_text = context.get("out_text")
    if out_text is None:
        reasons.append("slurm stdout unavailable")
    else:
        if re.search(r"(?m)^ENV-OK\b", out_text) is None:
            reasons.append("ENV-OK line missing")
        if "PREFLIGHT-FAIL" in out_text or "MATRIX-STOP" in out_text:
            reasons.append("stdout contains PREFLIGHT-FAIL or MATRIX-STOP")
    if len(context["records"]) != len(BENCH_FILES):
        reasons.append("not all artifacts were available for node checks")
    return reasons


def _in_job_hashes(out_text):
    entries = {}
    problems = []
    for line in out_text.splitlines():
        match = re.fullmatch(
            r"([0-9a-f]{64})  runs/d19_a7_timing/(bench_(?:sub|full)_threads_[1-4]\.json)",
            line,
        )
        if match is None:
            continue
        digest, filename = match.groups()
        if filename in entries:
            problems.append(f"duplicate in-job hash for {filename}")
        entries[filename] = digest
    return entries, problems


def _v11(context):
    reasons = []
    out_text = context.get("out_text")
    err_text = context.get("err_text")
    if out_text is None:
        return ["slurm stdout unavailable"]
    reports = []
    for line in out_text.splitlines():
        stripped = line.strip()
        if not stripped.startswith('{"'):
            continue
        try:
            report = json.loads(
                stripped,
                parse_constant=_reject_json_constant,
                object_pairs_hook=_object_without_duplicate_keys,
            )
        except (ValueError, json.JSONDecodeError) as exc:
            reasons.append(f"malformed report JSON line: {exc}")
            continue
        reports.append(report)
    if len(reports) != len(CELL_ORDER):
        reasons.append(f"report JSON line count {len(reports)} != {len(CELL_ORDER)}")
    for index, report in enumerate(reports):
        if type(report) is not dict or set(report) != {"kind", "scale", "n_points", "elapsed_s"}:
            reasons.append(f"report line {index + 1} has wrong key set")
    exits = []
    for line in out_text.splitlines():
        match = re.match(r"^CELL (sub|full) ([1-4]) exit 0(?:\s|$)", line)
        if match is not None:
            exits.append((match.group(1), int(match.group(2))))
    if tuple(exits) != CELL_ORDER:
        reasons.append(f"CELL exit order {exits!r} != {list(CELL_ORDER)!r}")
    complete_count = sum(
        1 for line in out_text.splitlines() if line.startswith("MATRIX-COMPLETE ")
    )
    if complete_count != 1:
        reasons.append(f"MATRIX-COMPLETE line count {complete_count} != 1")
    in_job, hash_problems = _in_job_hashes(out_text)
    context["in_job_hashes"] = in_job
    reasons.extend(hash_problems)
    if set(in_job) != set(BENCH_FILES):
        reasons.append(
            f"in-job sha256sum set mismatch: {sorted(set(in_job) ^ set(BENCH_FILES))}")
    for label, text in (("stdout", out_text), ("stderr", err_text)):
        if text is None:
            reasons.append(f"slurm {label} unavailable")
            continue
        for finding in _scan_forbidden_text(text):
            reasons.append(f"slurm {label}: {finding}")
    if err_text:
        print("STDERR-BEGIN")
        print(err_text, end="" if err_text.endswith("\n") else "\n")
        print("STDERR-END")
    return reasons


def _v12(context):
    reasons = []
    row, error = _sacct_row(context)
    if error is not None:
        return [error]
    if row.get("State") != "COMPLETED":
        reasons.append(f"parent State {row.get('State')!r} != 'COMPLETED'")
    if row.get("ExitCode") != "0:0":
        reasons.append(f"parent ExitCode {row.get('ExitCode')!r} != '0:0'")
    try:
        elapsed = _parse_duration(row.get("Elapsed"))
        context["elapsed_seconds"] = elapsed
        if elapsed > 2 * 60 * 60:
            reasons.append("parent Elapsed exceeds the scheduler time ceiling")
    except ValueError as exc:
        reasons.append(str(exc))
    return reasons


def _v13(context):
    reasons = []
    row, error = _sacct_row(context)
    if error is not None:
        return [error]
    try:
        cluster_zone = ZoneInfo("America/New_York")
    except (ZoneInfoNotFoundError, ValueError) as exc:
        return [f"zoneinfo failure: {exc}"]
    try:
        start = _parse_local_cluster_time(row.get("Start"), cluster_zone).astimezone(timezone.utc)
        end = _parse_local_cluster_time(row.get("End"), cluster_zone).astimezone(timezone.utc)
        elapsed = _parse_duration(row.get("Elapsed"))
    except (TypeError, ValueError) as exc:
        return [str(exc)]
    lower = start - timedelta(seconds=300)
    upper = end + timedelta(seconds=300)
    for filename, record in context["records"].items():
        try:
            timestamp = _parse_artifact_utc(record["environment"]["timestamp"])
        except (KeyError, TypeError, ValueError) as exc:
            reasons.append(f"{filename}: {exc}")
            continue
        if timestamp < lower or timestamp > upper:
            reasons.append(f"{filename}: artifact timestamp outside scheduler window")
        try:
            total = record["totals"]["elapsed_s"]
            if type(total) not in (int, float) or not math.isfinite(float(total)) or total > elapsed:
                reasons.append(f"{filename}: totals.elapsed_s exceeds parent Elapsed")
        except (KeyError, TypeError):
            reasons.append(f"{filename}: totals.elapsed_s unavailable")
    if len(context["records"]) != len(BENCH_FILES):
        reasons.append("not all artifacts were available for timestamp checks")
    return reasons


def _v14(context):
    reasons = []
    job_id = context["job_id"]
    if job_id is None:
        return ["job id unavailable"]
    evidence_dir = context["evidence_dir"]
    manifest_path = evidence_dir / "PROVENANCE.sha256"
    try:
        manifest_text = manifest_path.read_text(encoding="utf-8", errors="strict")
    except (OSError, UnicodeError) as exc:
        return [str(exc)]
    manifest, parse_problems = _parse_hash_lines(manifest_text)
    reasons.extend(parse_problems)
    expected = set(BENCH_FILES) | {
        f"slurm-{job_id}.out", f"slurm-{job_id}.err", "job_metadata.txt",
    }
    if "PROVENANCE.sha256" in manifest:
        reasons.append("manifest contains a forbidden self-entry")
    if set(manifest) != expected:
        reasons.append(f"manifest filename set mismatch: {sorted(set(manifest) ^ expected)}")
    local_hashes = {}
    for filename in expected:
        path = evidence_dir / filename
        try:
            local_hashes[filename] = _sha256(path)
        except OSError as exc:
            reasons.append(f"{filename}: {exc}")
            continue
        if manifest.get(filename) != local_hashes[filename]:
            reasons.append(f"{filename}: manifest hash disagrees with local bytes")
    in_job = context.get("in_job_hashes", {})
    for filename in BENCH_FILES:
        local = local_hashes.get(filename)
        if in_job.get(filename) != local:
            reasons.append(f"{filename}: in-job hash disagrees with local bytes")
        if manifest.get(filename) != in_job.get(filename):
            reasons.append(f"{filename}: in-job hash disagrees with PROVENANCE.sha256")
    return reasons


def _v15(context):
    reasons = []
    anchor_dir = REPO_ROOT / "runs" / "d19_planning"
    for filename, (expected_hash, expected_size) in ANCHORS.items():
        path = anchor_dir / filename
        try:
            size = path.stat().st_size
            digest = _sha256(path)
        except OSError as exc:
            reasons.append(f"{filename}: {exc}")
            continue
        if size != expected_size:
            reasons.append(f"{filename}: size {size} != {expected_size}")
        if digest != expected_hash:
            reasons.append(f"{filename}: sha256 {digest} != {expected_hash}")
    return reasons


CHECK_FUNCTIONS = (
    _v1, _v2, _v3, _v4, _v5, _v6, _v7, _v8, _v9, _v10,
    _v11, _v12, _v13, _v14, _v15,
)


def _argument_failure(message):
    for name in CHECK_NAMES:
        print(f"{name}: FAIL")
        print(f"  invalid arguments: {message}")
    return 1


def run(argv=None):
    parser = _ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", required=True)
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--job-id")
    try:
        args = parser.parse_args(argv)
    except ValueError as exc:
        return _argument_failure(str(exc))
    if re.fullmatch(r"[0-9a-f]{40}", args.expected_sha) is None:
        return _argument_failure("--expected-sha must be 40 lowercase hexadecimal characters")

    evidence_dir = Path(args.evidence_dir)
    job_id, job_id_errors = _infer_job_id(evidence_dir, args.job_id)
    context = {
        "evidence_dir": evidence_dir,
        "expected_sha": args.expected_sha,
        "job_id": job_id,
        "job_id_errors": job_id_errors,
        "records": {},
        "out_path": evidence_dir / f"slurm-{job_id}.out" if job_id else None,
        "err_path": evidence_dir / f"slurm-{job_id}.err" if job_id else None,
    }

    all_reasons = []
    for name, check in zip(CHECK_NAMES, CHECK_FUNCTIONS):
        try:
            reasons = check(context)
        except Exception as exc:
            reasons = [f"internal validator error {type(exc).__name__}: {exc}"]
        all_reasons.extend(reasons)
        print(f"{name}: {'PASS' if not reasons else 'FAIL'}")
        for reason in reasons:
            print(f"  {reason}")

    for filename in BENCH_FILES:
        record = context["records"].get(filename)
        if type(record) is dict:
            hessian = record.get("timings", {}).get("hessian", {}).get("status", "unavailable")
            stage2 = record.get("timings", {}).get("prior_eval_stage2", {}).get("status", "unavailable")
        else:
            hessian = "unavailable"
            stage2 = "unavailable"
        print(f"CENSUS {filename}: hessian={hessian} stage2={stage2}")
    return 0 if not all_reasons else 1


def main(argv=None):
    return run(argv)


if __name__ == "__main__":
    sys.exit(main())
