#!/usr/bin/env python3
"""Create the preregistered M2bR two-stage validation start freeze.

This program is deliberately limited to local authority-artifact verification,
deterministic NumPy selection, deterministic MAP optimization, D30 preflight,
and canonical serialization.  It does not run or initialize an HMC sampler.
"""

import hashlib
import json
import os
import struct
import sys
from pathlib import Path

import numpy as np
import torch


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parent.parent
os.chdir(REPO_ROOT)

# prior_sensitivity_study imports its sibling by its bare module name.
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, os.path.abspath("experiments"))

import bistar_gp.config as gp_config  # noqa: E402
import bistar_gp.data as gp_data  # noqa: E402
import bistar_gp.model as gp_model  # noqa: E402
from bistar_gp.e1_potential import (  # noqa: E402
    build_e1_potential,
    preflight_start_state,
    select_start_state,
)
from bistar_gp.fit import _guard_init_values, _map_init_values, fit_map  # noqa: E402
import prior_sensitivity_study as study  # noqa: E402


CONFIGS = ("informative", "toy_elicited")
POOL_SEEDS = (0, 1, 2)
BAND_ORDER = ("lo", "mid", "hi")
REPORTABLE_THRESHOLD = 0.05
VERIFY_ATOL = 1e-12
EXPECTED_SITES = {
    "likelihood.noise_covar.noise_prior": (1,),
    "covar_module.kernels.0.outputscale_prior": (),
    "covar_module.kernels.0.base_kernel.lengthscale_prior": (1, 1),
    "covar_module.kernels.1.variance_prior": (1, 1),
}
SUMMARY_FIELDS = (
    "P_noise_lo",
    "P_noise_lo_se",
    "P_noise_lo_ess",
    "P_noise_mid",
    "P_noise_mid_se",
    "P_noise_mid_ess",
    "P_noise_hi",
    "P_noise_hi_se",
    "P_noise_hi_ess",
    "ess",
)
EXPECTED_REPORTABLE = {
    "informative": ["lo", "mid", "hi"],
    "toy_elicited": ["lo", "mid"],
}
MANIFEST_PATH = REPO_ROOT / "docs" / "m2br_freeze" / "start_freeze_v1.14.json"


def stop(code, message):
    """Print a protocol STOP and terminate with its registered exit code."""
    print(f"STOP [{code}]: {message}", file=sys.stderr, flush=True)
    raise SystemExit(code)


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compare_summary(config, seed_label, actual, expected):
    for field in SUMMARY_FIELDS:
        if field not in expected:
            stop(2, f"{config}/seed={seed_label}/field={field}: missing authority value")
        actual_value = float(actual[field])
        expected_value = float(expected[field])
        if not np.isclose(
            actual_value, expected_value, rtol=0.0, atol=VERIFY_ATOL
        ):
            stop(
                2,
                f"{config}/seed={seed_label}/field={field}: "
                f"recomputed={actual_value!r}, authority={expected_value!r}, "
                f"atol={VERIFY_ATOL!r}",
            )


def recorded_summary(summary):
    return {field: float(summary[field]) for field in SUMMARY_FIELDS}


def load_and_verify_pools(config):
    stage_path = REPO_ROOT / "runs" / "prior_sensitivity" / f"stage_a_{config}.json"
    if not stage_path.is_file():
        stop(2, f"{config}: missing authority file {stage_path.relative_to(REPO_ROOT)}")
    try:
        with stage_path.open("r", encoding="utf-8") as handle:
            authority = json.load(handle)["prior_is"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        stop(2, f"{config}: cannot read prior_is from {stage_path}: {exc}")

    pool_records = []
    all_ths = []
    all_lml = []
    all_seeds = []
    all_rows = []

    for expected_seed in POOL_SEEDS:
        relative_path = Path("runs") / "prior_sensitivity" / (
            f"is_draws_{config}_s{expected_seed}.npz"
        )
        path = REPO_ROOT / relative_path
        if not path.is_file():
            stop(2, f"{config}/seed={expected_seed}: missing pool file {relative_path}")
        try:
            with np.load(path, allow_pickle=False) as data:
                ths = np.asarray(data["ths"], dtype=np.float64)
                lml = np.asarray(data["lml"], dtype=np.float64)
                seed_array = np.asarray(data["seed"])
        except (OSError, ValueError, KeyError, TypeError) as exc:
            stop(2, f"{config}/seed={expected_seed}: cannot load {relative_path}: {exc}")

        if ths.ndim != 2 or ths.shape[1] != len(study.ORDER):
            stop(2, f"{config}/seed={expected_seed}: invalid ths shape {ths.shape}")
        if lml.shape != (ths.shape[0],):
            stop(
                2,
                f"{config}/seed={expected_seed}: lml shape {lml.shape} "
                f"does not match ths shape {ths.shape}",
            )
        if seed_array.size != 1:
            stop(2, f"{config}/seed={expected_seed}: seed is not scalar: {seed_array.shape}")
        seed_scalar = int(seed_array.reshape(()))
        if seed_scalar != expected_seed:
            stop(
                2,
                f"{config}/seed={expected_seed}/field=seed: "
                f"pool scalar={seed_scalar}, expected={expected_seed}",
            )

        summary = study._is_summary(ths, lml)
        try:
            expected_summary = authority["per_seed"][str(expected_seed)]
        except (KeyError, TypeError) as exc:
            stop(2, f"{config}/seed={expected_seed}: missing per-seed authority: {exc}")
        compare_summary(config, expected_seed, summary, expected_summary)

        canonical_ths = ths.astype("<f8", copy=False)
        canonical_lml = lml.astype("<f8", copy=False)
        array_bytes = (
            canonical_ths.tobytes(order="C")
            + canonical_lml.tobytes(order="C")
            + struct.pack("<q", seed_scalar)
        )
        record = {
            "seed": expected_seed,
            "path": relative_path.as_posix(),
            "file_sha256": sha256_file(path),
            "array_sha256": hashlib.sha256(array_bytes).hexdigest(),
            "ths_shape": list(ths.shape),
            "lml_shape": list(lml.shape),
            "verify_atol": VERIFY_ATOL,
            "verified_against": (
                f"stage_a_{config}.json:prior_is.per_seed.{expected_seed}"
            ),
        }
        record.update(recorded_summary(summary))
        pool_records.append(record)
        all_ths.append(ths)
        all_lml.append(lml)
        all_seeds.append(np.full(ths.shape[0], expected_seed, dtype=np.int64))
        all_rows.append(np.arange(ths.shape[0], dtype=np.int64))

    pooled_ths = np.concatenate(all_ths, axis=0)
    pooled_lml = np.concatenate(all_lml, axis=0)
    pooled_seeds = np.concatenate(all_seeds, axis=0)
    pooled_rows = np.concatenate(all_rows, axis=0)
    pooled_summary = study._is_summary(pooled_ths, pooled_lml)
    try:
        pooled_authority = authority["pooled"]
    except (KeyError, TypeError) as exc:
        stop(2, f"{config}/pooled: missing authority: {exc}")
    compare_summary(config, "pooled", pooled_summary, pooled_authority)

    pooled_record = recorded_summary(pooled_summary)
    pooled_record["verified_against"] = f"stage_a_{config}.json:prior_is.pooled"
    pooled_record["atol"] = VERIFY_ATOL
    return (
        pool_records,
        pooled_record,
        pooled_ths,
        pooled_lml,
        pooled_seeds,
        pooled_rows,
        pooled_summary,
    )


def build_model(prior_config, x, y):
    kernels, names = gp_config.build_kernels_from_config(prior_config)
    likelihood = gp_config.build_likelihood_from_config(prior_config)
    model, likelihood = gp_model.build_model(x, y, kernels, names, likelihood)
    return model, likelihood


def assert_site_contract(model, likelihood, x, y):
    e1 = build_e1_potential(model, likelihood, x, y)
    assert len(e1.sites) == 4, f"expected exactly four E1 sites, got {e1.sites}"
    assert set(e1.sites) == set(EXPECTED_SITES), (
        f"unexpected E1 sites: expected {sorted(EXPECTED_SITES)}, got {sorted(e1.sites)}"
    )
    ref = _map_init_values(model)
    assert set(ref) == set(e1.sites)
    actual_shapes = {site: tuple(ref[site].shape) for site in ref}
    assert actual_shapes == EXPECTED_SITES, (
        f"site shapes changed: expected {EXPECTED_SITES}, got {actual_shapes}"
    )
    return ref


def band_masks(noise):
    return {
        "lo": noise < study.NOISE_SPLIT_LO,
        "mid": (noise >= study.NOISE_SPLIT_LO) & (noise <= study.NOISE_SPLIT_HI),
        "hi": noise > study.NOISE_SPLIT_HI,
    }


def weighted_quantile_index(mask, q, noise, lml, seeds, rows):
    subset = np.flatnonzero(mask)
    if subset.size == 0:
        raise RuntimeError(f"weighted quantile q={q}: empty band")
    subset_lml = lml[subset]
    weights = np.exp(subset_lml - np.max(subset_lml))
    total = weights.sum()
    if not np.isfinite(total) or total <= 0.0:
        raise RuntimeError(f"weighted quantile q={q}: invalid weight sum {total!r}")
    weights /= total
    order = np.lexsort((rows[subset], seeds[subset], noise[subset]))
    sorted_subset = subset[order]
    sorted_weights = weights[order]
    positions = np.flatnonzero(np.cumsum(sorted_weights) >= q)
    if positions.size == 0:
        # Only a floating-point accumulation shortfall at q=1 could reach here;
        # all preregistered targets are <= 0.75, so fail rather than improvise.
        raise RuntimeError(f"weighted quantile q={q}: cumulative weight never reached q")
    return int(sorted_subset[int(positions[0])])


def candidate_indices(mask, target, noise, seeds, rows):
    subset = np.flatnonzero(mask)
    others = subset[subset != target]
    distances = np.abs(noise[others] - noise[target])
    order = np.lexsort((rows[others], seeds[others], distances))
    return np.concatenate((np.asarray([target], dtype=np.int64), others[order]))


def inverse_short_mapping():
    inverse = {}
    for site, label in study.SHORT.items():
        if label in inverse:
            raise AssertionError(f"SHORT is not one-to-one for label {label}")
        inverse[label] = site
    assert set(inverse) == set(study.ORDER), (
        f"SHORT/ORDER mismatch: SHORT values={sorted(inverse)}, ORDER={study.ORDER}"
    )
    return inverse


def pool_draw_to_init(model, ref, th):
    inverse = inverse_short_mapping()
    init_values = {}
    for label in study.ORDER:
        site = inverse[label]
        value = float(th[study.ORDER.index(label)])
        init_values[site] = torch.tensor(value, dtype=torch.float64).reshape(
            ref[site].shape
        )
    assert set(init_values) == set(ref)
    guarded = _guard_init_values(model, init_values)
    assert set(guarded) == set(ref)
    return guarded


class CandidateSequence:
    """Lazy, priority-ordered init dictionaries for the authority selector."""

    def __init__(self, model, ref, ths, indices):
        self.model = model
        self.ref = ref
        self.ths = ths
        self.indices = indices

    def __len__(self):
        return len(self.indices)

    def __iter__(self):
        for index in self.indices:
            yield pool_draw_to_init(self.model, self.ref, self.ths[int(index)])


def serialize_state(state):
    sites = sorted(state)
    buffer = bytearray()
    shapes = {}
    values = {}
    values_hex = {}
    for site in sites:
        raw = state[site]
        if hasattr(raw, "detach"):
            raw = raw.detach().cpu().numpy()
        value = np.asarray(raw, dtype="<f8")
        buffer += site.encode("utf-8") + b"\x00"
        buffer += struct.pack("<I", value.ndim)
        for dimension in value.shape:
            buffer += struct.pack("<q", int(dimension))
        value_bytes = value.tobytes(order="C")
        buffer += value_bytes
        shapes[site] = list(value.shape)
        values[site] = [float(item) for item in value.reshape(-1)]
        values_hex[site] = value_bytes.hex()
    return {
        "sites": sites,
        "shapes": shapes,
        "values": values,
        "values_hex": values_hex,
        "semantic_sha256": hashlib.sha256(bytes(buffer)).hexdigest(),
    }


def chain_specs(reportable, largest_mass_band):
    count = len(reportable)
    if count == 3:
        return [
            (chain, "band_median", band, 0.50)
            for chain, band in enumerate(reportable, start=1)
        ]
    if count == 2:
        return [
            (1, "band_median", reportable[0], 0.50),
            (2, "band_median", reportable[1], 0.50),
            (3, "largest_mass_filler", largest_mass_band, 0.75),
        ]
    if count == 1:
        return [
            (1, "band_median", reportable[0], 0.50),
            (2, "largest_mass_filler", largest_mass_band, 0.25),
            (3, "largest_mass_filler", largest_mass_band, 0.75),
        ]
    raise AssertionError(f"no reportable bands: {reportable}")


def pool_index(index, seeds, rows):
    return {"seed": int(seeds[index]), "row": int(rows[index])}


def freeze_config(config, x, y):
    (
        pool_records,
        pooled_record,
        ths,
        lml,
        seeds,
        rows,
        pooled_summary,
    ) = load_and_verify_pools(config)

    masses = {band: float(pooled_summary[f"P_noise_{band}"]) for band in BAND_ORDER}
    reportable = [band for band in BAND_ORDER if masses[band] >= REPORTABLE_THRESHOLD]
    assert reportable == EXPECTED_REPORTABLE[config], (
        f"{config}: computed reportable bands {reportable}, "
        f"expected {EXPECTED_REPORTABLE[config]}"
    )
    largest_mass_band = max(reportable, key=lambda band: masses[band])

    prior_config = study.STUDY_CONFIGS[config]
    selection_model, selection_likelihood = build_model(prior_config, x, y)
    ref = assert_site_contract(selection_model, selection_likelihood, x, y)
    noise = ths[:, study.ORDER.index("noise")]
    masks = band_masks(noise)
    chains = []

    for chain, role, band, quantile in chain_specs(reportable, largest_mass_band):
        target = weighted_quantile_index(
            masks[band], quantile, noise, lml, seeds, rows
        )
        priority = candidate_indices(masks[band], target, noise, seeds, rows)
        candidates = CandidateSequence(selection_model, ref, ths, priority)
        try:
            accepted_position, accepted_values, _reports = select_start_state(
                selection_model,
                selection_likelihood,
                x,
                y,
                candidates,
            )
        except RuntimeError as exc:
            stop(
                3,
                f"{config}/chain={chain}: exhausted {len(candidates)} "
                f"D30 candidates in band {band}: {exc}",
            )
        realized = int(priority[accepted_position])
        record = {
            "chain": chain,
            "seed": chain,
            "role": role,
            "band": band,
            "target_quantile": quantile,
            "pool_index": pool_index(realized, seeds, rows),
            "target_pool_index": pool_index(target, seeds, rows),
            "fallback_advance_count": int(accepted_position),
        }
        record.update(serialize_state(accepted_values))
        chains.append(record)

    map_model, map_likelihood = build_model(prior_config, x, y)
    assert_site_contract(map_model, map_likelihood, x, y)
    torch.manual_seed(42)
    fit_map(map_model, map_likelihood, x, y, n_iter=300, lr=0.05, verbose=False)
    map_values = _map_init_values(map_model)
    ok, reason, report = preflight_start_state(
        map_model, map_likelihood, x, y, map_values
    )
    if not ok:
        stop(
            4,
            f"{config}/chain=0 MAP is unstartable: reason={reason}, report={report}",
        )
    map_record = {
        "chain": 0,
        "seed": 0,
        "role": "MAP",
        "band": None,
        "target_quantile": None,
        "pool_index": None,
        "fallback_advance_count": None,
    }
    map_record.update(serialize_state(map_values))
    chains.insert(0, map_record)

    print(
        f"{config}: masses "
        + ", ".join(f"{band}={masses[band]:.12f}" for band in BAND_ORDER)
        + f"; reportable={reportable}; B={len(reportable)}"
    )
    for record in chains:
        target = record.get("target_pool_index")
        realized = record["pool_index"]
        target_text = "-" if target is None else f"({target['seed']},{target['row']})"
        realized_text = (
            "-" if realized is None else f"({realized['seed']},{realized['row']})"
        )
        print(
            f"  chain {record['chain']}: role={record['role']} "
            f"band={record['band']} q={record['target_quantile']} "
            f"target={target_text} realized={realized_text} "
            f"fallback={record['fallback_advance_count']} "
            f"sha256={record['semantic_sha256'][:16]}"
        )

    return {
        "pools": pool_records,
        "pooled": pooled_record,
        "reportable_bands": reportable,
        "B": len(reportable),
        "largest_mass_band": largest_mass_band,
        "chains": chains,
    }


def main():
    torch.set_default_dtype(torch.float64)
    torch.use_deterministic_algorithms(True)
    assert study.ORDER == ["ls", "os", "lv", "noise"]
    assert study.NOISE_SPLIT_LO == 0.15
    assert study.NOISE_SPLIT_HI == 0.30

    x, y, _info = gp_data.generate_toy_data()
    manifest = {
        "protocol": "M2bR two-stage start freeze (validation layer)",
        "prereg_addendum": "v1.14",
        "generated_by": "experiments/m2br_start_freeze.py",
        "band_defs": {
            "lo": "noise<0.15",
            "mid": "0.15<=noise<=0.30",
            "hi": "noise>0.30",
        },
        "reportable_threshold": REPORTABLE_THRESHOLD,
        "map_procedure": {"seed": 42, "n_iter": 300, "lr": 0.05, "source": "fit_map"},
        "configs": {},
        "cells": {
            "V1": {"config": "informative", "td": 7, "start_config": "informative"},
            "V2": {"config": "informative", "td": 10, "start_config": "informative"},
            "V3": {"config": "toy_elicited", "td": 7, "start_config": "toy_elicited"},
            "V4": {"config": "toy_elicited", "td": 10, "start_config": "toy_elicited"},
        },
    }
    for config in CONFIGS:
        manifest["configs"][config] = freeze_config(config, x, y)

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    MANIFEST_PATH.write_text(serialized, encoding="utf-8")
    print(f"manifest: {MANIFEST_PATH.relative_to(REPO_ROOT)}")
    print("FREEZE OK")


if __name__ == "__main__":
    main()
