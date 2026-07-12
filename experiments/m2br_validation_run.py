"""M2bR multi-chain scientific VALIDATION driver (V1, V3, V2, V4)."""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from functools import partial
from pathlib import Path

import numpy as np
import torch

from bistar_gp.bms_star import GPPosteriorSample, run_bms_star
from bistar_gp.e1_potential import fit_hmc_e1
from bistar_gp.fit import _guard_init_values

if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from m2br_run_common import (
    EXPECTED_MANIFEST_SHA256,
    FREEZE_PATH,
    FREEZE_SHA256,
    METRICS,
    NOISE_SITE,
    PROJECTIONS,
    REPO_ROOT,
    SITE_NAMES,
    TAUS,
    Deadline,
    atomic_write_json,
    basin_occupancy,
    build_cell_model,
    canonical_start_sha256,
    deterministic_mock_sampler,
    diagnostics_payload,
    emit_run_plan,
    env_provenance,
    json_sha256,
    pin_execution_environment,
    persist_failure,
    require_absent,
    sample_array_hashes,
    sample_arrays_sha256,
    score_samples,
    serialize_bms_results,
    sha256_bytes,
    stamp_model_config,
    toy_scoring_context,
    transactional_persist,
)

VALIDATION_CELLS = (
    {"cell": "V1", "config": "informative", "td": 7},
    {"cell": "V3", "config": "toy_elicited", "td": 7},
    {"cell": "V2", "config": "informative", "td": 10},
    {"cell": "V4", "config": "toy_elicited", "td": 10},
)
DEFAULT_OUTPUT_DIR = REPO_ROOT / "runs" / "m2br_validation"


def _reconstruct_start(record):
    sites = tuple(record.get("sites", ()))
    if set(sites) != set(SITE_NAMES) or len(sites) != len(SITE_NAMES):
        raise ValueError(f"frozen chain {record.get('chain')} has wrong site set")
    values = {}
    for site in SITE_NAMES:
        if site not in record["shapes"] or site not in record["values"]:
            raise ValueError(f"frozen start omits {site}")
        shape = tuple(int(d) for d in record["shapes"][site])
        array = np.asarray(record["values"][site], dtype=np.float64)
        if array.size != math.prod(shape, start=1):
            raise ValueError(f"frozen value/shape mismatch for {site}")
        values[site] = torch.from_numpy(array.reshape(shape).copy()).double()
    actual = canonical_start_sha256(values)
    expected = record.get("semantic_sha256")
    if actual != expected:
        raise ValueError(
            f"frozen start semantic sha256 mismatch for chain {record.get('chain')}: "
            f"expected {expected}, recomputed {actual}")
    return values, actual


def load_frozen_starts(path=FREEZE_PATH, *, verify_file_hash=True):
    """Load and verify every frozen constrained start before any injection."""
    path = Path(path)
    del verify_file_hash  # retained for call compatibility; verification is mandatory
    manifest_bytes = path.read_bytes()
    actual_file_hash = sha256_bytes(manifest_bytes)
    if actual_file_hash != EXPECTED_MANIFEST_SHA256:
        raise ValueError(
            "start-freeze manifest pinned sha256 mismatch: "
            f"expected {EXPECTED_MANIFEST_SHA256}, got {actual_file_hash}")
    # Parse the exact bytes that were hashed; never reopen across this boundary.
    manifest = json.loads(manifest_bytes)
    loaded = {}
    for config in ("informative", "toy_elicited"):
        entry = manifest["configs"][config]
        records = sorted(entry["chains"], key=lambda r: int(r["chain"]))
        if [int(r["chain"]) for r in records] != [0, 1, 2, 3]:
            raise ValueError(f"{config}: manifest must contain chains 0/1/2/3")
        init_values, hashes = [], []
        for expected_seed, record in enumerate(records):
            if int(record["seed"]) != expected_seed:
                raise ValueError(f"{config}: chain/seed mismatch at {expected_seed}")
            values, semantic_hash = _reconstruct_start(record)
            init_values.append(values)
            hashes.append(semantic_hash)
        loaded[config] = {
            "records": records,
            "init_values": init_values,
            "hashes": hashes,
            "authority": entry["pooled"],
            "reportable_bands": list(entry["reportable_bands"]),
        }
    return loaded


def guard_validation_start(model, init_values):
    """Exercise fit_hmc_e1's exact four-site guard before sampler injection."""
    if set(init_values) != set(SITE_NAMES):
        raise ValueError(
            f"validation start must have the frozen four-site set; got "
            f"{sorted(init_values)}")
    return _guard_init_values(model, init_values)


def chains_to_inference_data(chain_samples, *, expected_draws=2000):
    """Convert four constrained sample dictionaries to ArviZ chain/draw form."""
    import arviz as az

    if len(chain_samples) != 4:
        raise ValueError("validation requires exactly four chains")
    if any(set(samples) != set(SITE_NAMES) for samples in chain_samples):
        raise ValueError("every chain must contain the exact four-site schema")
    flattened = {site: [
        np.asarray(chain[site], dtype=float).reshape(-1) for chain in chain_samples
    ] for site in SITE_NAMES}
    observed = {values.size for by_chain in flattened.values() for values in by_chain}
    if observed != {int(expected_draws)}:
        raise ValueError(
            "post-warmup draw cardinality mismatch: "
            f"expected {expected_draws} per chain/site, got {sorted(observed)}")
    draws = {site: np.stack(by_chain, axis=0)
             for site, by_chain in flattened.items()}
    lengths = {array.shape[1] for array in draws.values()}
    if len(lengths) != 1:
        raise ValueError("all sites/chains must have the same draw count")
    return az.from_dict(posterior=draws)


def _dataset_scalars(dataset):
    return {site: float(np.asarray(dataset[site]).reshape(-1)[0])
            for site in SITE_NAMES}


def authority_coverage_check(chain_mass, bulk_ess, authority_mass, authority_se):
    """Return the exact preregistered two-standard-error coverage calculation."""
    p = float(chain_mass)
    ess = float(bulk_ess)
    se_chain = math.sqrt(p * (1.0 - p) / ess) if ess > 0 else math.inf
    difference = abs(p - float(authority_mass))
    limit = 2.0 * math.sqrt(float(authority_se) ** 2 + se_chain ** 2)
    return {
        "chain_mass": p,
        "authority_mass": float(authority_mass),
        "authority_se": float(authority_se),
        "bulk_ess_pooled": ess,
        "chain_se": se_chain,
        "absolute_difference": difference,
        "two_se_limit": limit,
        "passed": bool(math.isfinite(limit) and difference <= limit),
    }


def _band_indicator(noise, band):
    noise = np.asarray(noise)
    if band == "lo":
        return noise < 0.15
    if band == "mid":
        return (noise >= 0.15) & (noise <= 0.30)
    if band == "hi":
        return noise > 0.30
    raise KeyError(band)


def _diagnostic_rates(chain_diagnostics):
    divergences = 0
    divergence_draws = 0
    saturated = 0
    leapfrog_draws = 0
    notpsd = 0
    potential_evals = 0
    early = []
    observations_available = {
        "divergence": True, "saturation": True, "notpsd": True}
    for diag in chain_diagnostics:
        if diag.divergence_draws is None:
            observations_available["divergence"] = False
        else:
            divergences += sum(len(indices) for indices in diag.divergence_draws)
            divergence_draws += diag.n_chains * diag.n_draws
        if diag.leapfrog_counts is None or diag.max_tree_depth is None:
            observations_available["saturation"] = False
        else:
            cap = 2 ** diag.max_tree_depth - 1
            flat = [n for chain in diag.leapfrog_counts for n in chain]
            saturated += sum(n >= cap for n in flat)
            leapfrog_draws += len(flat)
        if diag.notpsd_rejections_per_draw is None or diag.leapfrog_counts is None:
            observations_available["notpsd"] = False
            early.append(None)
        else:
            counts = [n for chain in diag.notpsd_rejections_per_draw for n in chain]
            early.append(int(sum(counts[:50])))
            notpsd += sum(counts)
            potential_evals += sum(
                n for chain in diag.leapfrog_counts for n in chain)
    return {
        "divergence_rate": (divergences / divergence_draws
                            if observations_available["divergence"] and divergence_draws
                            else None),
        "depth_saturation_rate": (saturated / leapfrog_draws
                                  if observations_available["saturation"] and leapfrog_draws
                                  else None),
        "notpsd_early_counts": early,
        "notpsd_post_warmup_rate": (notpsd / potential_evals
                                    if observations_available["notpsd"] and potential_evals
                                    else None),
        "notpsd_post_warmup_total": (notpsd
                                     if observations_available["notpsd"] else None),
    }


def acceptance_stats(chain_samples, chain_diagnostics, authority,
                     reportable_bands, *, expected_draws=2000):
    import arviz as az

    idata = chains_to_inference_data(
        chain_samples, expected_draws=expected_draws)
    rhat = _dataset_scalars(az.rhat(idata, method="rank"))
    ess_bulk = _dataset_scalars(az.ess(idata, method="bulk"))
    ess_tail = _dataset_scalars(az.ess(idata, method="tail"))
    noise = np.stack([
        np.asarray(chain[NOISE_SITE], dtype=float).reshape(-1)
        for chain in chain_samples
    ])
    per_chain_occupancy = [basin_occupancy(chain) for chain in noise]
    pooled_occupancy = basin_occupancy(noise.reshape(-1))
    coverage = {}
    for band in reportable_bands:
        indicator = _band_indicator(noise, band).astype(float)
        band_idata = az.from_dict(posterior={"band": indicator})
        band_ess = float(np.asarray(az.ess(band_idata, method="bulk")["band"]))
        coverage[band] = authority_coverage_check(
            pooled_occupancy[f"P_{band}"], band_ess,
            authority[f"P_noise_{band}"], authority[f"P_noise_{band}_se"])
    return {
        "rhat": rhat,
        "ess_bulk": ess_bulk,
        "ess_tail": ess_tail,
        "per_chain_occupancy": per_chain_occupancy,
        "pooled_occupancy": pooled_occupancy,
        "authority_coverage": coverage,
        **_diagnostic_rates(chain_diagnostics),
        "arviz_version": az.__version__,
    }


def evaluate_acceptance_from_stats(stats):
    """Apply every frozen threshold and name every failed criterion."""
    def finite_all(values):
        return all(math.isfinite(float(v)) for v in values)

    rhat_values = list(stats["rhat"].values())
    bulk_values = list(stats["ess_bulk"].values())
    tail_values = list(stats["ess_tail"].values())
    pooled = stats["pooled_occupancy"]
    occupancy_deviations = {
        band: max(abs(chain[f"P_{band}"] - pooled[f"P_{band}"])
                  for chain in stats["per_chain_occupancy"])
        for band in ("lo", "mid", "hi")
    }
    early = stats["notpsd_early_counts"]
    criteria = {
        "rhat": {"passed": finite_all(rhat_values) and all(v < 1.01 for v in rhat_values),
                 "threshold": "every site < 1.01", "values": stats["rhat"]},
        "ess_bulk": {"passed": finite_all(bulk_values) and all(v > 400 for v in bulk_values),
                     "threshold": "every site > 400", "values": stats["ess_bulk"]},
        "ess_tail": {"passed": finite_all(tail_values) and all(v > 400 for v in tail_values),
                     "threshold": "every site > 400", "values": stats["ess_tail"]},
        "occupancy": {"passed": all(v <= 0.05 for v in occupancy_deviations.values()),
                      "threshold": "per-chain absolute deviation <= 0.05",
                      "max_deviation": occupancy_deviations},
        "divergence_rate": {
            "passed": stats["divergence_rate"] is not None
                      and stats["divergence_rate"] < 0.001,
            "threshold": "< 0.001", "value": stats["divergence_rate"]},
        "depth_saturation_rate": {
            "passed": stats["depth_saturation_rate"] is not None
                      and stats["depth_saturation_rate"] < 0.10,
            "threshold": "< 0.10", "value": stats["depth_saturation_rate"]},
        "notpsd_early_window": {
            "passed": all(value == 0 for value in early) if early else False,
            "threshold": "zero in each chain's first 50 post-warmup draws",
            "per_chain_counts": early},
        "notpsd_rate": {
            "passed": stats["notpsd_post_warmup_rate"] is not None
                      and stats["notpsd_post_warmup_rate"] < 0.001,
            "threshold": "< 0.001", "value": stats["notpsd_post_warmup_rate"]},
        "authority_coverage": {
            "passed": bool(stats["authority_coverage"])
                      and all(value["passed"]
                              for value in stats["authority_coverage"].values()),
            "threshold": "absolute difference <= combined two-SE limit",
            "bands": stats["authority_coverage"]},
    }
    failed = [name for name, result in criteria.items() if not result["passed"]]
    return {"passed": not failed, "failed_criteria": failed,
            "criteria": criteria, "stats": stats}


def evaluate_cell_acceptance(chain_samples, chain_diagnostics, authority,
                             reportable_bands, *, expected_draws=2000):
    return evaluate_acceptance_from_stats(
        acceptance_stats(chain_samples, chain_diagnostics, authority,
                         reportable_bands, expected_draws=expected_draws))


def _serialize_bms(results, metric_names, taus):
    out = {}
    for metric in metric_names:
        first = results[metric][taus[0]]
        g = np.asarray(first.G_matrix, dtype=float)
        winners = np.argmin(g, axis=1)
        out[metric] = {
            "instance_posteriors": {
                str(tau): np.asarray(results[metric][tau].instance_posteriors,
                                     dtype=float).tolist()
                for tau in taus
            },
            "G_matrix": g.tolist(),
            "hard_win_fractions": [float(np.mean(winners == j))
                                   for j in range(g.shape[1])],
        }
    return out


def aggregate_validation_bms(chain_predictives, candidate_results,
                             metric_names=METRICS, taus=TAUS,
                             run_fn=run_bms_star, expected_per_chain=200):
    """R-B: one pooled normalization is primary; chain means are diagnostic."""
    if len(chain_predictives) != 4:
        raise ValueError("R-B aggregation requires exactly four chains")
    chain_counts = [len(chain) for chain in chain_predictives]
    if chain_counts != [int(expected_per_chain)] * 4:
        raise ValueError(
            "R-B predictive cardinality mismatch: expected "
            f"{expected_per_chain} per chain and {4 * expected_per_chain} pooled, "
            f"got per-chain {chain_counts} and pooled {sum(chain_counts)}")
    tau_array = np.asarray(taus, dtype=float)
    per_chain_results = [
        run_fn(chain, candidate_results, list(metric_names), tau_array)
        for chain in chain_predictives
    ]
    concatenated = [draw for chain in chain_predictives for draw in chain]
    pooled_results = run_fn(
        concatenated, candidate_results, list(metric_names), tau_array)
    primary = _serialize_bms(pooled_results, metric_names, taus)
    per_chain = [_serialize_bms(result, metric_names, taus)
                 for result in per_chain_results]
    diagnostic = {}
    for metric in metric_names:
        diagnostic[metric] = {}
        for tau in taus:
            values = np.asarray([
                result[metric][tau].instance_posteriors
                for result in per_chain_results
            ], dtype=float)
            diagnostic[metric][str(tau)] = {
                "per_chain": values.tolist(),
                "per_chain_mean_diagnostic_only": values.mean(axis=0).tolist(),
                # Diagnostic-only spread over four chains; frozen text omits ddof.
                "cross_chain_sd": values.std(axis=0).tolist(),
            }
    return {
        "primary_label": (
            "PRIMARY: concatenated equal-chain predictives, one BMS* normalization"
        ),
        "primary": primary,
        "diagnostic_label": (
            "DIAGNOSTIC ONLY: separately normalized chains, mean, and cross-chain SD"
        ),
        "per_chain": per_chain,
        "cross_chain_diagnostics": diagnostic,
        "n_pooled_predictives": len(concatenated),
    }


def validation_chain_paths(output_dir, cell, chain):
    directory = Path(output_dir) / cell
    prefix = directory / f"chain{chain}"
    return {
        "samples": Path(str(prefix) + "_samples.npz"),
        "predictives": Path(str(prefix) + "_predictives.npz"),
        "diagnostics": Path(str(prefix) + "_diagnostics.json"),
        "results": Path(str(prefix) + "_results.json"),
        "failure": Path(str(prefix) + "_failure.json"),
    }


def _predictive_arrays(gp_samples):
    return {
        "means": np.stack([sample.mean for sample in gp_samples]),
        "covs": np.stack([sample.cov for sample in gp_samples]),
    }


def _load_predictives(path):
    with np.load(path) as cache:
        means, covs = cache["means"], cache["covs"]
    return [GPPosteriorSample(mean=mean, cov=cov, hyperparameters={})
            for mean, cov in zip(means, covs)]


def run_validation_chain(cell, chain, frozen, *, sampler_fn=fit_hmc_e1,
                         output_dir=DEFAULT_OUTPUT_DIR,
                         scoring_fn=score_samples):
    """Run one injected-start chain and atomically preserve all observations."""
    cell_id, config, td = cell["cell"], cell["config"], int(cell["td"])
    run_id = f"{cell_id}.chain{chain}"
    paths = validation_chain_paths(output_dir, cell_id, chain)
    for path in paths.values():
        require_absent(path)

    # Pin threads INSIDE this (possibly spawned) chain process so it governs the
    # real sampler; skipped for the mock sampler.
    child_env = pin_execution_environment() if sampler_fn is fit_hmc_e1 else None

    x, y, _info, x_eval_torch, candidate_results = toy_scoring_context()
    model, likelihood, _, _ = build_cell_model(config, x, y)
    stamp_model_config(model, config)
    init_values = frozen[config]["init_values"][chain]
    expected_hash = frozen[config]["hashes"][chain]
    # Guard again on the fresh model immediately before injection.
    init_values = guard_validation_start(model, init_values)
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
            n_samples=2000,
            n_warmup=1000,
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

    predictive_arrays = _predictive_arrays(scored["gp_samples"])
    sample_hash = sample_arrays_sha256(samples)
    predictive_hash = sample_arrays_sha256(predictive_arrays)
    diag_record = diagnostics_payload(diag)
    diag_hash = json_sha256(diag_record)
    provenance = env_provenance()
    result_record = {
        "status": "completed",
        "role": "validation chain diagnostic (not the primary cell estimator)",
        "cell": cell_id,
        "chain": chain,
        "seed": chain,
        "config": config,
        "max_tree_depth": td,
        "n_samples": 2000,
        "n_warmup": 1000,
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
        "cell": cell_id, "chain": chain,
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


def _load_chain_artifacts(output_dir, cell_id):
    from bistar_gp.sampler_diagnostics import SamplerDiagnostics

    samples, diagnostics, predictives = [], [], []
    for chain in range(4):
        paths = validation_chain_paths(output_dir, cell_id, chain)
        with np.load(paths["samples"]) as cache:
            samples.append({site: cache[site] for site in cache.files})
        with open(paths["diagnostics"]) as handle:
            payload = json.load(handle)
        diag_keys = set(SamplerDiagnostics.__dataclass_fields__)
        diagnostics.append(SamplerDiagnostics.from_dict(
            {key: payload[key] for key in diag_keys}))
        predictives.append(_load_predictives(paths["predictives"]))
    return samples, diagnostics, predictives


def finalize_validation_cell(cell, frozen, output_dir=DEFAULT_OUTPUT_DIR):
    cell_id, config = cell["cell"], cell["config"]
    result_path = Path(output_dir) / cell_id / "cell_results.json"
    require_absent(result_path)
    chain_samples, chain_diagnostics, chain_predictives = _load_chain_artifacts(
        output_dir, cell_id)
    acceptance = evaluate_cell_acceptance(
        chain_samples, chain_diagnostics,
        frozen[config]["authority"], frozen[config]["reportable_bands"])
    candidate_results = toy_scoring_context()[4]
    rb = aggregate_validation_bms(chain_predictives, candidate_results)
    payload = {
        "cell": cell_id,
        "config": config,
        "max_tree_depth": cell["td"],
        "status": "passed" if acceptance["passed"] else "failed_validation",
        "acceptance": acceptance,
        "replacement_numbers": rb if acceptance["passed"] else None,
        "computed_bms_for_diagnostic_record": rb,
        "historical_counterparts": (
            "eligible for supersession" if acceptance["passed"]
            else "WITHDRAWN/UNVALIDATED"
        ),
        "provenance": env_provenance(),
    }
    atomic_write_json(result_path, payload)
    return payload


def _persist_stop(output_dir, run_id, reason):
    payload = {"status": "stopped", "first_unexecuted_run": run_id,
               "reason": reason}
    atomic_write_json(Path(output_dir) / "stop.json", payload)
    return payload


def run_validation(*, sampler_fn=fit_hmc_e1, output_dir=DEFAULT_OUTPUT_DIR,
                   deadline=None, isolate=True, scoring_fn=score_samples,
                   manifest_path=FREEZE_PATH, authorized=False):
    """Run V1,V3,V2,V4 with the 6 h per-chain projection gate."""
    if sampler_fn is fit_hmc_e1 and authorized is not True:
        raise PermissionError(
            "real fit_hmc_e1 requires authorized=True (CLI: --execute)")
    deadline = deadline or Deadline(21600, reserve_seconds=600)
    if deadline.t0 is None:
        deadline.start()
    # Protocol section 4: manifest verification is inside the monotonic clock.
    frozen = load_frozen_starts(manifest_path)
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    report = {"status": "running", "completed_cells": [],
              "failed_cells": [], "failed_chains": [],
              "first_unexecuted_run": None}
    report["execution_environment"] = (
        pin_execution_environment() if sampler_fn is fit_hmc_e1 else None)

    for cell in VALIDATION_CELLS:
        cell_failed = False
        for chain in range(4):
            run_id = f"{cell['cell']}.chain{chain}"
            projection = PROJECTIONS[cell["td"]]
            if not deadline.may_start(run_id, projection):
                report["status"] = "stopped"
                report["first_unexecuted_run"] = run_id
                _persist_stop(output_dir, run_id, "projection_gate")
                return report
            fn = partial(run_validation_chain, cell, chain, frozen,
                         sampler_fn=sampler_fn, output_dir=output_dir,
                         scoring_fn=scoring_fn)
            if isolate:
                isolated = deadline.run_isolated(
                    fn, projection, deadline.sampling_cutoff(), run_id=run_id,
                    failure_path=validation_chain_paths(
                        output_dir, cell["cell"], chain)["failure"])
                if isolated["status"] == "timed_out":
                    report["status"] = "stopped"
                    report["first_unexecuted_run"] = run_id
                    _persist_stop(output_dir, run_id, "absolute_cutoff_timeout")
                    return report
                result = isolated.get("value", isolated)
            else:
                result = fn()
            if result["status"] != "completed":
                cell_failed = True
                report["failed_chains"].append(run_id)
        if cell_failed:
            report["failed_cells"].append(cell["cell"])
            # No four-chain acceptance/primary can be constructed.
            failure_path = Path(output_dir) / cell["cell"] / "cell_failure.json"
            atomic_write_json(failure_path, {
                "status": "failed_technical",
                "cell": cell["cell"],
                "historical_counterparts": "WITHDRAWN/UNVALIDATED",
                "failed_chains": [run for run in report["failed_chains"]
                                  if run.startswith(cell["cell"] + ".")],
            })
            continue
        result = finalize_validation_cell(cell, frozen, output_dir)
        if result["status"] == "passed":
            report["completed_cells"].append(cell["cell"])
        else:
            report["failed_cells"].append(cell["cell"])
    report["status"] = (
        "completed_with_failures" if report["failed_cells"] else "completed")
    return report


def _print_plan(frozen):
    print("M2bR VALIDATION plan (no sampling):")
    for cell in VALIDATION_CELLS:
        hashes = frozen[cell["config"]]["hashes"]
        print(f"  {cell['cell']}: {cell['config']}, td{cell['td']}, seeds 0/1/2/3")
        for chain, semantic_hash in enumerate(hashes):
            print(f"    chain{chain} verified start sha256 {semantic_hash}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--execute", action="store_true",
                      help="explicitly authorize real frozen HMC validation")
    mode.add_argument("--dry-run", action="store_true",
                      help="use the deterministic mock sampler")
    parser.add_argument("--emit-plan", action="store_true",
                        help="emit/verify the combined machine-readable plan")
    args = parser.parse_args(argv)

    frozen = load_frozen_starts()
    if not args.execute and not args.dry_run:
        emit_run_plan()
        _print_plan(frozen)
        print("No --execute supplied; exiting without running any sampler.")
        return 0
    if args.dry_run:
        output = DEFAULT_OUTPUT_DIR / "_dryrun"
        print(f"DRY RUN: deterministic mock sampler; outputs -> {output}")
        report = run_validation(sampler_fn=deterministic_mock_sampler,
                                output_dir=output, isolate=False)
    else:
        output = DEFAULT_OUTPUT_DIR
        print("WARNING: --execute will run REAL HMC under the frozen M2bR VALIDATION protocol.")
        report = run_validation(sampler_fn=fit_hmc_e1, output_dir=output,
                                authorized=True)
    print(json.dumps(report, indent=2))
    return 0 if report["status"] in {"completed", "completed_with_failures"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
