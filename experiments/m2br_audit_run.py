"""M2bR corrected historical-impact AUDIT driver.

These are deliberately single-chain, MAP-initialized comparisons.  They do
not load the validation start manifest: the frozen audit protocol requires
``init_to_map=True``, and the vague/gamma-relaxed audit arms have no frozen
validation starts.  Every output is labelled "corrected single-chain
comparison" and cannot establish convergence or close W2/W3.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from functools import partial
from pathlib import Path

import numpy as np
import torch

from bistar_gp.e1_potential import fit_hmc_e1
from bistar_gp.fit import fit_map

if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from m2br_run_common import (
    METRICS,
    NOISE_SITE,
    PROJECTIONS,
    REPO_ROOT,
    SEED,
    TAUS,
    Deadline,
    atomic_write_json,
    basin_occupancy,
    build_cell_model,
    deterministic_mock_sampler,
    diagnostics_payload,
    emit_run_plan,
    env_provenance,
    pin_execution_environment,
    json_sha256,
    persist_failure,
    require_absent,
    sample_array_hashes,
    sample_arrays_sha256,
    score_samples,
    stamp_model_config,
    toy_scoring_context,
    transactional_persist,
)
import prior_sensitivity_study as study

AUDIT_RUNS = (
    {"run_id": "d12_informative_td7", "config": "informative", "td": 7},
    {"run_id": "d12_informative_td10", "config": "informative", "td": 10},
    {"run_id": "d18_toy_elicited_td7", "config": "toy_elicited", "td": 7},
    {"run_id": "d18_toy_elicited_td10", "config": "toy_elicited", "td": 10},
    {"run_id": "d18_vague_td7", "config": "vague", "td": 7},
    {"run_id": "d18_gamma_relaxed_td7", "config": "gamma_relaxed", "td": 7},
)

DEFAULT_OUTPUT_DIR = REPO_ROOT / "runs" / "m2br_corrected_impact"
# Standalone --verify-arms writes here, a namespace DISJOINT from the audit
# execution namespace, so the preflight never creates a no-overwrite path that
# --execute (whose first step re-runs the same verification) later needs.
PREFLIGHT_OUTPUT_DIR = REPO_ROOT / "runs" / "m2br_preflight"
LABEL = "corrected single-chain comparison"
UNCHANGED_CONFIGS = ("informative", "toy_elicited", "vague", "gamma_relaxed")
UNCHANGED_SEEDS = (0, 1, 2)
VERIFY_ATOL = 1e-12
SUMMARY_FIELDS = (
    "ess",
    "P_noise_lo", "P_noise_lo_se", "P_noise_lo_ess",
    "P_noise_mid", "P_noise_mid_se", "P_noise_mid_ess",
    "P_noise_hi", "P_noise_hi_se", "P_noise_hi_ess",
)


def audit_paths(output_dir, run_id):
    output_dir = Path(output_dir)
    return {
        "samples": output_dir / f"samples_{run_id}_e1.npz",
        "diagnostics": output_dir / f"diagnostics_{run_id}.json",
        "results": output_dir / f"results_{run_id}.json",
        "failure": output_dir / f"failure_{run_id}.json",
    }


def _numeric_mismatches(actual, expected, path=""):
    """Return strict-schema numeric mismatches with the protocol tolerance."""
    mismatches = []
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return [{"field": path, "actual": actual, "expected": expected}]
        for key in expected:
            child = f"{path}.{key}" if path else str(key)
            if key not in actual:
                mismatches.append({"field": child, "actual": "<missing>",
                                   "expected": expected[key]})
            else:
                mismatches.extend(_numeric_mismatches(actual[key], expected[key], child))
        for key in actual.keys() - expected.keys():
            child = f"{path}.{key}" if path else str(key)
            mismatches.append({"field": child, "actual": actual[key],
                               "expected": "<missing>"})
        return mismatches
    if isinstance(expected, (list, tuple)):
        if not isinstance(actual, (list, tuple)) or len(actual) != len(expected):
            return [{"field": path, "actual": actual, "expected": expected}]
        for index, value in enumerate(expected):
            mismatches.extend(_numeric_mismatches(
                actual[index], value, f"{path}[{index}]"))
        return mismatches
    numeric = (int, float, np.integer, np.floating)
    if (isinstance(expected, numeric) and not isinstance(expected, (bool, np.bool_))
            and isinstance(actual, numeric) and not isinstance(actual, (bool, np.bool_))):
        if not np.isclose(float(actual), float(expected), rtol=0.0,
                          atol=VERIFY_ATOL, equal_nan=False):
            mismatches.append({"field": path, "actual": float(actual),
                               "expected": float(expected),
                               "absolute_difference": abs(float(actual) - float(expected))})
    elif actual != expected:
        mismatches.append({"field": path, "actual": actual, "expected": expected})
    return mismatches


def _summary_result(actual, expected):
    wanted = {field: expected[field] for field in SUMMARY_FIELDS if field in expected}
    missing = [field for field in SUMMARY_FIELDS if field not in expected]
    mismatches = _numeric_mismatches(
        {field: actual[field] for field in SUMMARY_FIELDS}, wanted)
    mismatches.extend({"field": field, "actual": actual[field],
                       "expected": "<missing>"} for field in missing)
    return {"status": "PASS" if not mismatches else "FAIL",
            "atol": VERIFY_ATOL, "mismatches": mismatches}


def _recompute_sir(config, per_seed_pools, pooled_ths, pooled_lml):
    """Faithfully reproduce stage_is_one's deterministic transformation."""
    x, y, _info, x_eval_torch, candidate_results = toy_scoring_context()
    per_metric, g_by_metric, noise, indices = study._sir_bms(
        study.STUDY_CONFIGS[config], x, y, x_eval_torch, candidate_results,
        pooled_ths, pooled_lml, 1000, sir_seed=42)
    weights = np.exp(pooled_lml - pooled_lml.max())
    ess = float(weights.sum() ** 2 / (weights ** 2).sum())
    bootstrap = {}
    rng = np.random.default_rng(1)
    for metric in ("pw_kl_vcal", "kl_forward"):
        g_matrix = g_by_metric[metric]
        reps = np.empty((1000, g_matrix.shape[1]))
        for replicate in range(1000):
            rows = rng.integers(0, g_matrix.shape[0], g_matrix.shape[0])
            reps[replicate] = study._boltzmann_posterior(g_matrix[rows], 1.0)
        bootstrap[metric] = {
            "se": [float(v) for v in reps.std(axis=0)],
            "q025": [float(v) for v in np.quantile(reps, 0.025, axis=0)],
            "q975": [float(v) for v in np.quantile(reps, 0.975, axis=0)],
        }
    per_seed = {}
    for seed in UNCHANGED_SEEDS:
        ths, lml = per_seed_pools[seed]
        metrics, _, _, _ = study._sir_bms(
            study.STUDY_CONFIGS[config], x, y, x_eval_torch,
            candidate_results, ths, lml, 1000, sir_seed=42)
        per_seed[str(seed)] = metrics["pw_kl_vcal"]["posteriors"]["1.0"]
    return {
        "config": config,
        "pooled_is_ess": ess,
        "ess_floor_ok": bool(ess >= 100),
        "n_sir_draws": 1000,
        "n_unique_sir_draws": int(len(np.unique(indices))),
        "sir_occupancy": {
            "P_noise_lo": float(np.mean(noise < study.NOISE_SPLIT_LO)),
            "P_noise_mid": float(np.mean((noise >= study.NOISE_SPLIT_LO)
                                          & (noise <= study.NOISE_SPLIT_HI))),
            "P_noise_hi": float(np.mean(noise > study.NOISE_SPLIT_HI)),
        },
        "bootstrap_tau1": bootstrap,
        "per_is_seed_pw_kl_vcal_tau1": per_seed,
        "metrics": per_metric,
        "model_names": [candidate.name for candidate in candidate_results],
    }


# RW-MH referee (prior_sensitivity_study.mh_noise_occupancy) unchanged-arm
# reference. The referee ran ONLY for toy_elicited (the D18 noise-marginal
# deep-dive; prior_sensitivity_study.stage_noise_marginal defaults its config
# list to ["toy_elicited"]). For every other config there is no RW-MH arm to
# re-verify -- that is NOT_APPLICABLE, not a missing artifact. Pinned D18
# reference values (prior_sensitivity_study.py FIGURE dict rwmh_* and the
# stored results_noise_marginal_toy_elicited.json rw_mh rows):
RWMH_CONFIGS = ("toy_elicited",)
# Full D18 reference occupancy triplets (P_noise_lo, P_noise_mid, P_noise_hi)
# per seed 42/1/2, from the stored results_noise_marginal_toy_elicited.json
# rw_mh rows. Pinning all three (not just lo) blocks a compensating mid/high
# drift that preserves lo, the sum, and the 30000-grid integrality.
RWMH_OCCUPANCY_BY_SEED = (
    (0.7958666666666666, 0.16753333333333334, 0.0366),      # seed 42
    (0.8082333333333334, 0.1755, 0.016266666666666665),     # seed 1
    (0.8428333333333333, 0.1402, 0.016966666666666668),     # seed 2
)
RWMH_LO_BY_SEED = tuple(triplet[0] for triplet in RWMH_OCCUPANCY_BY_SEED)
RWMH_LO_HI_CROSSINGS = (44, 40, 38)
RWMH_N_SAMPLES, RWMH_N_BURNIN, RWMH_PROPOSAL_SCALE = 30000, 5000, 0.1


def _rw_mh_code_params_ok():
    """Code-level provenance for the params that are NOT stored per row
    (retained draws, burn-in, proposal scale): inspect the referee's defaults
    and the proposal_scale literal in prior_sensitivity_study.mh_noise_occupancy,
    AND confirm the frozen caller stage_noise_marginal_one invokes it with no
    override of those defaults."""
    import inspect
    try:
        sig = inspect.signature(study.mh_noise_occupancy)
        src = inspect.getsource(study.mh_noise_occupancy)
        caller = "".join(inspect.getsource(study.stage_noise_marginal_one).split())
    except (TypeError, OSError, AttributeError):
        return False
    return (tuple(sig.parameters["seeds"].default) == (42, 1, 2)
            and sig.parameters["n_samples"].default == RWMH_N_SAMPLES
            and sig.parameters["n_burnin"].default == RWMH_N_BURNIN
            and f"proposal_scale={RWMH_PROPOSAL_SCALE}" in src
            and "mh_noise_occupancy(pc,x,y)" in caller)


def _verify_rw_mh(config, source_dir):
    """Broadened AUDIT §3 step-4 RW-MH re-verification.

    Returns (entry, performed). For a config that never ran the RW-MH referee
    the entry is NOT_APPLICABLE (performed=False) -- distinct from a missing
    artifact. For toy_elicited it checks: exactly three rows with seeds
    42/1/2; per-row occupancy sums to 1 and every band mass x 30000 is integral
    (confirming the 30,000 retained draws that are not stored per row);
    P_noise_lo per seed and the lo/hi crossing counts unchanged vs the pinned
    D18 reference at atol=1e-12; and the referee's code-level params
    (30,000 retained, 5,000 burn-in, proposal scale 0.1)."""
    if config not in RWMH_CONFIGS:
        return ({"status": "NOT_APPLICABLE",
                 "reason": ("RW-MH referee (noise-marginal stage) is "
                            "toy_elicited-only per "
                            "prior_sensitivity_study.stage_noise_marginal; this "
                            "config never ran an RW-MH arm, so there is no "
                            "unchanged reference to verify")}, False)
    rw_path = source_dir / f"results_noise_marginal_{config}.json"
    if not rw_path.is_file():
        # Required for toy_elicited (the only RW-MH config); absence is a
        # verification FAILURE, never a silent skip that could permit sampling.
        return ({"status": "FAIL",
                 "reason": f"missing required local artifact: {rw_path}"}, False)
    try:
        rows = json.loads(rw_path.read_bytes())["rw_mh"]
        seeds = [int(row["seed"]) for row in rows]
        occ_sum_ok = integral_ok = True
        for row in rows:
            total = (float(row["P_noise_lo"]) + float(row["P_noise_mid"])
                     + float(row["P_noise_hi"]))
            if abs(total - 1.0) > 1e-9:
                occ_sum_ok = False
            for band in ("P_noise_lo", "P_noise_mid", "P_noise_hi"):
                scaled = float(row[band]) * RWMH_N_SAMPLES
                if abs(scaled - round(scaled)) > 1e-6:
                    integral_ok = False
        # Reject non-integer counts before int() coercion could hide drift
        # (e.g. a stored crossing 44.9 must not pass as 44).
        counts_integral = all(
            float(row["seed"]) == int(row["seed"])
            and float(row["lo_hi_crossings"]) == int(row["lo_hi_crossings"])
            for row in rows)
        checks = {
            "exactly_three_rows": len(rows) == 3,
            "seed_and_crossing_counts_integral": counts_integral,
            "seeds_42_1_2": seeds == [42, 1, 2],
            "occupancies_sum_to_one": occ_sum_ok,
            "retained_30000_integral": integral_ok,
            # Pin the FULL (lo, mid, hi) occupancy triplet per seed at 1e-12 --
            # a lo-only pin would miss a compensating mid/high drift.
            "occupancy_triplet_unchanged": (
                len(rows) == len(RWMH_OCCUPANCY_BY_SEED) and all(
                    abs(float(row["P_noise_lo"]) - ref[0]) <= VERIFY_ATOL
                    and abs(float(row["P_noise_mid"]) - ref[1]) <= VERIFY_ATOL
                    and abs(float(row["P_noise_hi"]) - ref[2]) <= VERIFY_ATOL
                    for row, ref in zip(rows, RWMH_OCCUPANCY_BY_SEED))),
            "lo_hi_crossings_unchanged": (
                [int(row["lo_hi_crossings"]) for row in rows]
                == list(RWMH_LO_HI_CROSSINGS)),
            "code_params_30000_5000_0p1": _rw_mh_code_params_ok(),
        }
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return ({"status": "FAIL", "reason": str(exc)}, False)
    failed = [name for name, ok in checks.items() if not ok]
    return ({"status": "PASS" if not failed else "FAIL",
             "atol": VERIFY_ATOL,
             "seeds": seeds,
             "checks": checks,
             "failed_checks": failed,
             "verified_params": {"n_samples": RWMH_N_SAMPLES,
                                 "n_burnin": RWMH_N_BURNIN,
                                 "proposal_scale": RWMH_PROPOSAL_SCALE},
             "reference": {
                 "occupancy_by_seed": [list(t) for t in RWMH_OCCUPANCY_BY_SEED],
                 "lo_hi_crossings": list(RWMH_LO_HI_CROSSINGS)}},
            True)


def verify_unchanged_arms(*, source_dir=None, output_path=None,
                          configs=UNCHANGED_CONFIGS, run_sir=True):
    """Re-verify unaffected prior-IS, deterministic SIR, and stored RW-MH."""
    source_dir = Path(source_dir or REPO_ROOT / "runs" / "prior_sensitivity")
    report = {"status": "PASS", "atol": VERIFY_ATOL, "configs": {}}
    for config in configs:
        entry = {"prior_is": {}, "sir": None, "rw_mh": None}
        report["configs"][config] = entry
        stage_path = source_dir / f"stage_a_{config}.json"
        pool_paths = [source_dir / f"is_draws_{config}_s{seed}.npz"
                      for seed in UNCHANGED_SEEDS]
        missing = [str(path) for path in [stage_path, *pool_paths]
                   if not path.is_file()]
        if missing:
            # Required unchanged-arm evidence is missing: this is a verification
            # FAILURE, not a skip. A skip must never silently permit sampling.
            reason = f"missing required local artifact(s): {', '.join(missing)}"
            entry["prior_is"] = {"status": "FAIL", "reason": reason}
            entry["sir"] = ({"status": "FAIL", "reason": reason} if run_sir
                            else {"status": "SKIP",
                                  "reason": "deterministic SIR disabled by caller"})
            entry["rw_mh"] = _verify_rw_mh(config, source_dir)[0]
            report["status"] = "FAIL"
            continue
        try:
            authority = json.loads(stage_path.read_bytes())["prior_is"]
            pools = {}
            all_ths, all_lml = [], []
            for seed, pool_path in zip(UNCHANGED_SEEDS, pool_paths):
                with np.load(pool_path, allow_pickle=False) as pool:
                    ths = np.asarray(pool["ths"], dtype=np.float64)
                    lml = np.asarray(pool["lml"], dtype=np.float64)
                    stored_seed = int(np.asarray(pool["seed"]).reshape(()))
                if stored_seed != seed:
                    raise ValueError(
                        f"{config}/seed={seed}: stored pool seed is {stored_seed}")
                pools[seed] = (ths, lml)
                all_ths.append(ths)
                all_lml.append(lml)
                entry["prior_is"][str(seed)] = _summary_result(
                    study._is_summary(ths, lml), authority["per_seed"][str(seed)])
            pooled_ths = np.concatenate(all_ths, axis=0)
            pooled_lml = np.concatenate(all_lml, axis=0)
            entry["prior_is"]["pooled"] = _summary_result(
                study._is_summary(pooled_ths, pooled_lml), authority["pooled"])
            prior_failed = any(check["status"] == "FAIL"
                               for check in entry["prior_is"].values())
            entry["prior_is"]["status"] = "FAIL" if prior_failed else "PASS"
        except (OSError, ValueError, KeyError, TypeError) as exc:
            entry["prior_is"] = {"status": "FAIL", "reason": str(exc)}
            # SIR only SKIPs on the explicit run_sir=False opt-out; a prior-IS
            # failure that prevents SIR is itself a FAIL when SIR was required.
            entry["sir"] = ({"status": "FAIL",
                             "reason": "prior-IS verification could not complete"}
                            if run_sir else
                            {"status": "SKIP",
                             "reason": "deterministic SIR disabled by caller"})
            entry["rw_mh"] = _verify_rw_mh(config, source_dir)[0]
            report["status"] = "FAIL"
            continue

        sir_path = source_dir / f"results_is_{config}.json"
        if not run_sir:
            entry["sir"] = {"status": "SKIP",
                            "reason": "deterministic SIR disabled by caller"}
        elif not sir_path.is_file():
            entry["sir"] = {"status": "FAIL",
                            "reason": f"missing required local artifact: {sir_path}"}
            report["status"] = "FAIL"
        else:
            try:
                stored_sir = json.loads(sir_path.read_bytes())
                actual_sir = _recompute_sir(
                    config, pools, pooled_ths, pooled_lml)
                mismatches = _numeric_mismatches(actual_sir, stored_sir)
                entry["sir"] = {
                    "status": "PASS" if not mismatches else "FAIL",
                    "performed": (
                        "seed 42, 1000 SIR draws; bootstrap seed 1, "
                        "1000 replicates; all stored fields"),
                    "atol": VERIFY_ATOL,
                    "mismatches": mismatches,
                }
            except (OSError, ValueError, KeyError, TypeError) as exc:
                entry["sir"] = {"status": "FAIL", "reason": str(exc)}
                report["status"] = "FAIL"

        entry["rw_mh"], _ = _verify_rw_mh(config, source_dir)

        statuses = [entry["prior_is"].get("status"),
                    entry["sir"].get("status"), entry["rw_mh"].get("status")]
        if "FAIL" in statuses:
            report["status"] = "FAIL"
    # Strict: PASS requires every required check to PASS (prior-IS + SIR for all
    # configs, toy_elicited RW-MH PASS, other configs RW-MH NOT_APPLICABLE). A
    # SKIP only ever comes from run_sir=False (an explicit caller opt-out) and
    # never upgrades or downgrades the overall verdict away from PASS/FAIL.
    if output_path is not None:
        atomic_write_json(output_path, report)
    return report


def run_audit_one(run, *, sampler_fn=fit_hmc_e1, output_dir=DEFAULT_OUTPUT_DIR,
                  map_fn=fit_map, scoring_fn=score_samples):
    """Execute one frozen audit arm; suitable for injected hermetic tests."""
    run_id, config, td = run["run_id"], run["config"], int(run["td"])
    paths = audit_paths(output_dir, run_id)
    for key in ("samples", "diagnostics", "results", "failure"):
        require_absent(paths[key])

    # Pin threads INSIDE this (possibly spawned) process so it governs the real
    # sampler, not just the orchestrator. Skipped for the mock sampler so tests
    # never perturb the interpreter's thread count.
    child_env = pin_execution_environment() if sampler_fn is fit_hmc_e1 else None

    x, y, _info, x_eval_torch, candidate_results = toy_scoring_context()
    model, likelihood, _, _ = build_cell_model(config, x, y)
    stamp_model_config(model, config)

    fit_started = time.monotonic()
    try:
        torch.manual_seed(SEED)
        map_fn(model, likelihood, x, y, n_iter=300, lr=0.05, verbose=False)
        samples, diag = sampler_fn(
            model, likelihood, x, y,
            n_samples=2000,
            n_warmup=1000,
            seed=SEED,
            init_to_map=True,
            max_tree_depth=td,
            return_diagnostics=True,
            verbose=False,
        )
        fit_seconds = time.monotonic() - fit_started
        scoring_started = time.monotonic()
        scored = scoring_fn(
            samples, model, likelihood, x, y, x_eval_torch,
            candidate_results, n_predictives=200)
        scoring_seconds = time.monotonic() - scoring_started
    except BaseException as exc:
        failure = persist_failure(paths["failure"], run_id, exc)
        return {"status": "failed", "run_id": run_id, "failure": failure}

    sample_hash = sample_arrays_sha256(samples)
    diag_record = diagnostics_payload(diag)
    diag_hash = json_sha256(diag_record)
    provenance = env_provenance()
    result_record = {
        "status": "completed",
        "label": LABEL,
        "run_id": run_id,
        "config": config,
        "max_tree_depth": td,
        "seed": SEED,
        "n_samples": 2000,
        "n_warmup": 1000,
        "n_predictives": scored["n_predictives"],
        "metrics": list(METRICS),
        "taus": list(TAUS),
        "basin_occupancy": basin_occupancy(samples[NOISE_SITE]),
        "site_summaries": scored["site_summaries"],
        "bms": scored["metrics"],
        "timing": {"fit_seconds": fit_seconds,
                   "scoring_seconds": scoring_seconds},
        "hashes": {
            "samples_semantic_sha256": sample_hash,
            "sample_arrays": sample_array_hashes(samples),
            "diagnostics_payload_sha256": diag_hash,
        },
        "provenance": provenance,
        "execution_environment": child_env,
        "interpretation_limit": (
            "Single-chain historical-impact audit only; not a convergence "
            "validation and not paper-grade replacement evidence."
        ),
    }
    diag_record.update({
        "label": LABEL,
        "run_id": run_id,
        "basin_occupancy": result_record["basin_occupancy"],
        "samples_semantic_sha256": sample_hash,
        "provenance": provenance,
    })

    # Stage the complete run, then expose the consumable sample cache last.
    transactional_persist(
        json_artifacts={paths["diagnostics"]: diag_record,
                        paths["results"]: result_record},
        npz_artifacts={paths["samples"]: samples},
        samples_path=paths["samples"],
    )
    return {"status": "completed", "run_id": run_id,
            "paths": {k: str(v) for k, v in paths.items() if k != "failure"}}


def _persist_stop(output_dir, run_id, reason):
    path = Path(output_dir) / "stop.json"
    payload = {
        "status": "stopped",
        "first_unexecuted_run": run_id,
        "reason": reason,
    }
    atomic_write_json(path, payload)
    return payload


def run_audit(*, sampler_fn=fit_hmc_e1, output_dir=DEFAULT_OUTPUT_DIR,
              deadline=None, isolate=True, map_fn=fit_map,
              scoring_fn=score_samples, authorized=False,
              verify_arms_fn=verify_unchanged_arms):
    """Run the frozen list in order with its 2 h stop-and-report rule."""
    if sampler_fn is fit_hmc_e1 and authorized is not True:
        raise PermissionError(
            "real fit_hmc_e1 requires authorized=True (CLI: --execute)")
    deadline = deadline or Deadline(7200, reserve_seconds=600)
    if deadline.t0 is None:
        deadline.start()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    report = {"status": "running", "completed": [], "failed": [],
              "first_unexecuted_run": None}
    # Pin + record the compute environment before real sampling so the frozen
    # leapfrog projections stay valid (skipped for the mock sampler).
    report["execution_environment"] = (
        pin_execution_environment() if sampler_fn is fit_hmc_e1 else None)

    verification = verify_arms_fn(
        output_path=output_dir / "unchanged_arms_verification.json")
    report["unchanged_arms_verification"] = verification
    # Sample ONLY when the unchanged-arm evidence is present and strictly PASS.
    if verification["status"] != "PASS":
        report["status"] = "verification_failed"
        return report

    for run in AUDIT_RUNS:
        run_id, projection = run["run_id"], PROJECTIONS[run["td"]]
        if not deadline.may_start(run_id, projection):
            report["status"] = "stopped"
            report["first_unexecuted_run"] = run_id
            _persist_stop(output_dir, run_id, "projection_gate")
            break
        fn = partial(run_audit_one, run, sampler_fn=sampler_fn,
                     output_dir=output_dir, map_fn=map_fn,
                     scoring_fn=scoring_fn)
        if isolate:
            isolated = deadline.run_isolated(
                fn, projection, deadline.sampling_cutoff(), run_id=run_id,
                failure_path=audit_paths(output_dir, run_id)["failure"])
            if isolated["status"] == "timed_out":
                report["status"] = "stopped"
                report["first_unexecuted_run"] = run_id
                _persist_stop(output_dir, run_id, "absolute_cutoff_timeout")
                break
            result = isolated.get("value", isolated)
        else:
            result = fn()
        if result["status"] == "completed":
            report["completed"].append(run_id)
        else:
            report["failed"].append(run_id)

    if report["status"] == "running":
        report["status"] = "completed_with_failures" if report["failed"] else "completed"
    return report


def _print_plan(plan):
    print("M2bR AUDIT plan (no sampling):")
    for run in AUDIT_RUNS:
        print(f"  {run['run_id']}: {run['config']}, td{run['td']}, seed 42, "
              "1000 warmup + 2000 draws")
    print(f"Run-plan manifest: {REPO_ROOT / 'docs/m2br_freeze/run_plan.json'}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--execute", action="store_true",
                      help="explicitly authorize the real frozen HMC audit")
    mode.add_argument("--dry-run", action="store_true",
                      help="use the deterministic mock sampler")
    mode.add_argument("--verify-arms", action="store_true",
                      help="only re-verify unchanged prior-IS/SIR/RW-MH arms")
    parser.add_argument("--emit-plan", action="store_true",
                        help="emit/verify the combined machine-readable plan")
    args = parser.parse_args(argv)

    if args.verify_arms:
        # Preflight namespace, disjoint from the execution namespace, and
        # idempotent (a preflight check may be re-run; it is not a scientific
        # artifact protected by the no-overwrite rule).
        PREFLIGHT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        preflight_path = PREFLIGHT_OUTPUT_DIR / "unchanged_arms_verification.json"
        if preflight_path.exists():
            preflight_path.unlink()
        report = verify_unchanged_arms(output_path=preflight_path)
        print(json.dumps(report, indent=2))
        # Strict: exit success ONLY for PASS (never SKIP).
        return 0 if report["status"] == "PASS" else 2
    if not args.execute and not args.dry_run:
        plan = emit_run_plan()
        _print_plan(plan)
        print("No --execute supplied; exiting without running any sampler.")
        return 0

    if args.dry_run:
        output = DEFAULT_OUTPUT_DIR / "_dryrun"
        print(f"DRY RUN: deterministic mock sampler; outputs -> {output}")
        report = run_audit(sampler_fn=deterministic_mock_sampler,
                           output_dir=output, isolate=False)
    else:
        output = DEFAULT_OUTPUT_DIR
        print("WARNING: --execute will run REAL HMC under the frozen M2bR AUDIT protocol.")
        report = run_audit(sampler_fn=fit_hmc_e1, output_dir=output,
                           authorized=True)
    print(json.dumps(report, indent=2))
    return 0 if report["status"] in {"completed", "completed_with_failures"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
