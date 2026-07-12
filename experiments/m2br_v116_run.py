"""Gated M2bR v1.16 informative-only validation escalation (D34).

Importing this module never starts a sampler.  Real HMC is available only
through ``fit_hmc_e1`` and requires both the programmatic ``authorized=True``
gate and the CLI ``--execute`` gate.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from functools import partial
from pathlib import Path

import numpy as np

from bistar_gp.e1_potential import fit_hmc_e1
from bistar_gp.sampler_diagnostics import SamplerDiagnostics

if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import m2br_validation_run as validation
from m2br_run_common import (
    EXPECTED_MANIFEST_SHA256,
    FREEZE_PATH,
    NOISE_SITE,
    PROJECTIONS,
    REPO_ROOT,
    Deadline,
    atomic_write_json,
    basin_occupancy,
    build_cell_model,
    canonical_start_sha256,
    deterministic_mock_sampler,
    diagnostics_payload,
    env_provenance,
    json_sha256,
    pin_execution_environment,
    persist_failure,
    require_absent,
    sample_array_hashes,
    sample_arrays_sha256,
    score_samples,
    sha256_bytes,
    stamp_model_config,
    toy_scoring_context,
    transactional_persist,
)

V116_CELL = {"cell": "V1e", "config": "informative", "td": 7}
N_WARMUP = 3000
N_SAMPLES = 8000
N_PREDICTIVES = 200
N_CHAINS = 4
CEILING_SECONDS = 90 * 60
RESERVE_SECONDS = 600

V116_PLAN_PATH = REPO_ROOT / "docs" / "m2br_freeze" / "v116_run_plan.json"
EXPECTED_V116_PLAN_SHA256 = (
    "db177b8b265082312fc8e48bc44cdd5c02bb9f238cac362d641db6e84f0290fd"
)
DEFAULT_OUTPUT_DIR = REPO_ROOT / "runs" / "m2br_v116_informative"


def load_v116_plan(path=V116_PLAN_PATH, *, frozen=None):
    """Read once and verify the exact author-ratified v1.16 machine pin."""
    path = Path(path)
    plan_bytes = path.read_bytes()
    actual_hash = sha256_bytes(plan_bytes)
    if actual_hash != EXPECTED_V116_PLAN_SHA256:
        raise ValueError(
            "v1.16 run-plan pinned sha256 mismatch: "
            f"expected {EXPECTED_V116_PLAN_SHA256}, got {actual_hash}")
    plan = json.loads(plan_bytes)

    expected_fields = {
        "addendum": "v1.16",
        "config": "informative",
        "cells": [{"cell": "V1e", "config": "informative",
                   "max_tree_depth": 7}],
        "chains": N_CHAINS,
        "seeds": list(range(N_CHAINS)),
        "changed_parameters_only": {
            "n_warmup": N_WARMUP, "n_draws": N_SAMPLES},
        "parent_freeze_manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "output_namespace": "runs/m2br_v116_informative/ (untracked)",
    }
    for field, expected in expected_fields.items():
        if plan.get(field) != expected:
            raise ValueError(
                f"v1.16 run-plan field {field!r} mismatch: "
                f"expected {expected!r}, got {plan.get(field)!r}")

    unchanged = plan.get("unchanged", {})
    if unchanged.get("sampler") != "fit_hmc_e1":
        raise ValueError("v1.16 run-plan sampler must remain fit_hmc_e1")
    if unchanged.get("n_predictives_per_chain") != N_PREDICTIVES:
        raise ValueError("v1.16 run-plan predictive count mismatch")
    if unchanged.get("primary_estimator") != (
            "R-B pooled 4x200=800, one normalization"):
        raise ValueError("v1.16 run-plan primary estimator mismatch")
    if unchanged.get("authority_reference_informative_pooled_lo_mid_hi") != [
            0.2768, 0.131, 0.5922]:
        raise ValueError("v1.16 run-plan authority reference mismatch")
    budget = plan.get("budget", {})
    if budget.get("ceiling_min") != 90 or budget.get("reserve_s") != 600:
        raise ValueError("v1.16 run-plan deadline budget mismatch")

    if frozen is not None:
        expected_hashes = list(frozen["informative"]["hashes"])
        pinned_starts = plan.get("frozen_starts_reused_from_v1.14", [])
        observed = [record.get("semantic_sha256") for record in pinned_starts]
        chains = [record.get("chain") for record in pinned_starts]
        seeds = [record.get("seed") for record in pinned_starts]
        if (observed != expected_hashes or chains != list(range(N_CHAINS))
                or seeds != list(range(N_CHAINS))):
            raise ValueError(
                "v1.16 run-plan frozen-start semantic sha256 mismatch")
    return plan


def v116_chain_paths(output_dir, chain):
    prefix = Path(output_dir) / f"chain{chain}"
    return {
        "samples": Path(str(prefix) + "_samples.npz"),
        "predictives": Path(str(prefix) + "_predictives.npz"),
        "diagnostics": Path(str(prefix) + "_diagnostics.json"),
        "results": Path(str(prefix) + "_results.json"),
        "failure": Path(str(prefix) + "_failure.json"),
    }


def run_v116_chain(chain, frozen, *, sampler_fn=fit_hmc_e1,
                   output_dir=DEFAULT_OUTPUT_DIR, scoring_fn=score_samples,
                   authorized=False):
    """Run one v1.16 chain with the sole numerical change: 3000/8000."""
    if sampler_fn is fit_hmc_e1 and authorized is not True:
        raise PermissionError(
            "real fit_hmc_e1 requires authorized=True (CLI: --execute)")
    config, td = V116_CELL["config"], V116_CELL["td"]
    run_id = f"{V116_CELL['cell']}.chain{chain}"
    paths = v116_chain_paths(output_dir, chain)
    for path in paths.values():
        require_absent(path)

    child_env = pin_execution_environment() if sampler_fn is fit_hmc_e1 else None

    x, y, _info, x_eval_torch, candidate_results = toy_scoring_context()
    model, likelihood, _, _ = build_cell_model(config, x, y)
    stamp_model_config(model, config)
    init_values = frozen[config]["init_values"][chain]
    expected_hash = frozen[config]["hashes"][chain]
    init_values = validation.guard_validation_start(model, init_values)
    if canonical_start_sha256(init_values) != expected_hash:
        raise ValueError("guarded validation start changed its frozen semantic hash")

    fit_started = time.monotonic()
    try:
        samples, diag = sampler_fn(
            model, likelihood, x, y,
            init_values=init_values,
            init_to_map=False,
            seed=chain,
            max_tree_depth=td,
            n_samples=N_SAMPLES,
            n_warmup=N_WARMUP,
            return_diagnostics=True,
            verbose=False,
        )
        fit_seconds = time.monotonic() - fit_started
        scoring_started = time.monotonic()
        scored = scoring_fn(
            samples, model, likelihood, x, y, x_eval_torch,
            candidate_results, n_predictives=N_PREDICTIVES)
        scoring_seconds = time.monotonic() - scoring_started
    except BaseException as exc:
        failure = persist_failure(paths["failure"], run_id, exc)
        return {"status": "failed", "run_id": run_id, "failure": failure}

    predictive_arrays = validation._predictive_arrays(scored["gp_samples"])
    sample_hash = sample_arrays_sha256(samples)
    predictive_hash = sample_arrays_sha256(predictive_arrays)
    diag_record = diagnostics_payload(diag)
    diag_hash = json_sha256(diag_record)
    provenance = env_provenance()
    result_record = {
        "status": "completed",
        "role": "v1.16 validation chain diagnostic (not primary cell estimator)",
        "cell": V116_CELL["cell"],
        "chain": chain,
        "seed": chain,
        "config": config,
        "max_tree_depth": td,
        "n_samples": N_SAMPLES,
        "n_warmup": N_WARMUP,
        "n_predictives": scored["n_predictives"],
        "frozen_start_semantic_sha256": expected_hash,
        "basin_occupancy": basin_occupancy(samples[NOISE_SITE]),
        "site_summaries": scored["site_summaries"],
        "separately_normalized_bms_diagnostic": scored["metrics"],
        "timing": {"fit_seconds": fit_seconds,
                   "scoring_seconds": scoring_seconds},
        "hashes": {
            "samples_semantic_sha256": sample_hash,
            "sample_arrays": sample_array_hashes(samples),
            "predictives_semantic_sha256": predictive_hash,
            "diagnostics_payload_sha256": diag_hash,
        },
        "provenance": provenance,
        "execution_environment": child_env,
    }
    diag_record.update({
        "cell": V116_CELL["cell"], "chain": chain,
        "frozen_start_semantic_sha256": expected_hash,
        "samples_semantic_sha256": sample_hash,
        "provenance": provenance,
    })
    transactional_persist(
        json_artifacts={paths["diagnostics"]: diag_record,
                        paths["results"]: result_record},
        npz_artifacts={paths["predictives"]: predictive_arrays,
                       paths["samples"]: samples},
        samples_path=paths["samples"],
    )
    return {"status": "completed", "run_id": run_id,
            "paths": {key: str(path) for key, path in paths.items()
                      if key != "failure"}}


def _load_chain_artifacts(output_dir):
    samples, diagnostics, predictives = [], [], []
    for chain in range(N_CHAINS):
        paths = v116_chain_paths(output_dir, chain)
        with np.load(paths["samples"]) as cache:
            samples.append({site: cache[site] for site in cache.files})
        with open(paths["diagnostics"]) as handle:
            payload = json.load(handle)
        diag_keys = set(SamplerDiagnostics.__dataclass_fields__)
        diagnostics.append(SamplerDiagnostics.from_dict(
            {key: payload[key] for key in diag_keys}))
        predictives.append(validation._load_predictives(paths["predictives"]))
    return samples, diagnostics, predictives


def finalize_v116_cell(frozen, output_dir=DEFAULT_OUTPUT_DIR):
    result_path = Path(output_dir) / "cell_results.json"
    require_absent(result_path)
    chain_samples, chain_diagnostics, chain_predictives = (
        _load_chain_artifacts(output_dir))
    informative = frozen["informative"]
    acceptance = validation.evaluate_cell_acceptance(
        chain_samples, chain_diagnostics, informative["authority"],
        informative["reportable_bands"], expected_draws=N_SAMPLES)
    candidate_results = toy_scoring_context()[4]
    rb = validation.aggregate_validation_bms(
        chain_predictives, candidate_results,
        expected_per_chain=N_PREDICTIVES)
    payload = {
        "cell": V116_CELL["cell"],
        "config": V116_CELL["config"],
        "max_tree_depth": V116_CELL["td"],
        "n_samples_per_chain": N_SAMPLES,
        "n_warmup_per_chain": N_WARMUP,
        "status": "passed" if acceptance["passed"] else "failed_validation",
        "acceptance": acceptance,
        "replacement_numbers": rb if acceptance["passed"] else None,
        "computed_bms_for_diagnostic_record": rb,
        "historical_counterparts": (
            "eligible for supersession" if acceptance["passed"]
            else "WITHDRAWN/UNVALIDATED"),
        "provenance": env_provenance(),
    }
    atomic_write_json(result_path, payload)
    return payload


def _persist_stop(output_dir, run_id, reason):
    payload = {"status": "stopped", "first_unexecuted_run": run_id,
               "reason": reason}
    atomic_write_json(Path(output_dir) / "stop.json", payload)
    return payload


def run_v116(*, sampler_fn=fit_hmc_e1, output_dir=DEFAULT_OUTPUT_DIR,
             deadline=None, isolate=True, scoring_fn=score_samples,
             manifest_path=FREEZE_PATH, plan_path=V116_PLAN_PATH,
             authorized=False):
    """Run the one informative-td7 v1.16 cell under the 90-minute ceiling."""
    if sampler_fn is fit_hmc_e1 and authorized is not True:
        raise PermissionError(
            "real fit_hmc_e1 requires authorized=True (CLI: --execute)")
    deadline = deadline or Deadline(
        CEILING_SECONDS, reserve_seconds=RESERVE_SECONDS)
    if deadline.t0 is None:
        deadline.start()

    # Both pins are verified inside the one monotonic run clock and before any
    # output directory or sampler boundary.  The frozen loader hashes and then
    # parses the same bytes, and every chain re-guards its in-memory start.
    frozen = validation.load_frozen_starts(manifest_path)
    load_v116_plan(plan_path, frozen=frozen)
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    report = {"status": "running", "completed_cells": [],
              "failed_cells": [], "failed_chains": [],
              "first_unexecuted_run": None}
    report["execution_environment"] = (
        pin_execution_environment() if sampler_fn is fit_hmc_e1 else None)

    cell_failed = False
    for chain in range(N_CHAINS):
        run_id = f"{V116_CELL['cell']}.chain{chain}"
        projection = PROJECTIONS[V116_CELL["td"]]
        if not deadline.may_start(run_id, projection):
            report["status"] = "stopped"
            report["first_unexecuted_run"] = run_id
            _persist_stop(output_dir, run_id, "projection_gate")
            return report
        fn = partial(
            run_v116_chain, chain, frozen, sampler_fn=sampler_fn,
            output_dir=output_dir, scoring_fn=scoring_fn,
            authorized=authorized)
        if isolate:
            isolated = deadline.run_isolated(
                fn, projection, deadline.sampling_cutoff(), run_id=run_id,
                failure_path=v116_chain_paths(output_dir, chain)["failure"])
            if isolated["status"] == "timed_out":
                report["status"] = "stopped"
                report["first_unexecuted_run"] = run_id
                _persist_stop(
                    output_dir, run_id, "absolute_cutoff_timeout")
                return report
            result = isolated.get("value", isolated)
        else:
            result = fn()
        if result["status"] != "completed":
            cell_failed = True
            report["failed_chains"].append(run_id)

    if cell_failed:
        report["failed_cells"].append(V116_CELL["cell"])
        atomic_write_json(Path(output_dir) / "cell_failure.json", {
            "status": "failed_technical",
            "cell": V116_CELL["cell"],
            "historical_counterparts": "WITHDRAWN/UNVALIDATED",
            "failed_chains": report["failed_chains"],
        })
        report["status"] = "completed_with_failures"
        return report

    result = finalize_v116_cell(frozen, output_dir)
    if result["status"] == "passed":
        report["completed_cells"].append(V116_CELL["cell"])
        report["status"] = "completed"
    else:
        report["failed_cells"].append(V116_CELL["cell"])
        report["status"] = "completed_with_failures"
    return report


def _print_plan(plan, frozen):
    print("M2bR v1.16 informative-only escalation plan (no sampling):")
    print(json.dumps(plan, indent=2, sort_keys=True))
    for chain, semantic_hash in enumerate(frozen["informative"]["hashes"]):
        print(f"chain{chain} verified start sha256 {semantic_hash}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--execute", action="store_true",
                      help="explicitly authorize real v1.16 HMC")
    mode.add_argument("--dry-run", action="store_true",
                      help="use the deterministic mock sampler")
    mode.add_argument("--emit-plan", action="store_true",
                      help="print and verify the v1.16 pin without sampling")
    args = parser.parse_args(argv)

    frozen = validation.load_frozen_starts()
    plan = load_v116_plan(frozen=frozen)
    if not args.execute and not args.dry_run:
        _print_plan(plan, frozen)
        print("No --execute supplied; exiting without running any sampler.")
        return 0
    if args.dry_run:
        output = DEFAULT_OUTPUT_DIR / "_dryrun"
        print(f"DRY RUN: deterministic mock sampler; outputs -> {output}")
        report = run_v116(
            sampler_fn=deterministic_mock_sampler, output_dir=output,
            isolate=False)
    else:
        output = DEFAULT_OUTPUT_DIR
        print("WARNING: --execute will run REAL HMC under the ratified v1.16 protocol.")
        report = run_v116(
            sampler_fn=fit_hmc_e1, output_dir=output, authorized=True)
    print(json.dumps(report, indent=2))
    return 0 if report["status"] in {
        "completed", "completed_with_failures"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
