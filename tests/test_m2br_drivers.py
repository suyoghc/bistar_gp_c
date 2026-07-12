"""Hermetic contract tests for the M2bR AUDIT/VALIDATION drivers.

No test calls the production sampler.  Sampler boundaries are either never
reached or receive an injected deterministic/raising function.
"""

from __future__ import annotations

import copy
import json
import math
import signal
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from bistar_gp.bms_star import soft_transfer
from bistar_gp.sampler_diagnostics import SamplerDiagnostics
from experiments.m2br_audit_run import run_audit, verify_unchanged_arms
from experiments.m2br_run_common import (
    EXPECTED_MANIFEST_SHA256,
    FREEZE_PATH,
    NOISE_SITE,
    SITE_NAMES,
    Deadline,
    atomic_write_json,
    canonical_start_sha256,
    require_absent,
    run_isolated,
    score_samples,
    transactional_persist,
)
from experiments.m2br_validation_run import (
    VALIDATION_CELLS,
    _reconstruct_start,
    aggregate_validation_bms,
    authority_coverage_check,
    chains_to_inference_data,
    evaluate_acceptance_from_stats,
    guard_validation_start,
    load_frozen_starts,
    run_validation,
    run_validation_chain,
)
from experiments.m2br_run_common import build_cell_model
from experiments import prior_sensitivity_study as pss


def _four_chain_fixture(n_draws=800):
    rng = np.random.default_rng(20260712)
    centers = dict(zip(SITE_NAMES, (2.0, 1.0, 0.08, 0.22)))
    return [{
        site: center + rng.normal(0.0, 0.02 * max(center, 0.1), n_draws)
        for site, center in centers.items()
    } for _ in range(4)]


def _diagnostics(n_draws=20, *, notpsd=None):
    counts = list(notpsd or [0] * n_draws)
    if len(counts) != n_draws:
        raise ValueError("wrong test diagnostic length")
    return SamplerDiagnostics(
        sampler="hermetic_mock",
        n_chains=1,
        n_draws=n_draws,
        n_warmup=5,
        site_names=SITE_NAMES,
        max_tree_depth=7,
        step_size=0.1,
        divergence_draws=((),),
        acceptance_rate=(0.9,),
        leapfrog_counts=(tuple([3] * n_draws),),
        notpsd_rejections=sum(counts),
        notpsd_rejections_warmup=0,
        notpsd_rejections_per_draw=(tuple(counts),),
        unavailable=(),
    )


def test_arviz_four_chain_conversion_and_diagnostics_are_computable():
    import arviz as az

    idata = chains_to_inference_data(
        _four_chain_fixture(), expected_draws=800)
    assert set(idata.posterior.data_vars) == set(SITE_NAMES)
    for site in SITE_NAMES:
        assert idata.posterior[site].shape == (4, 800)
    rhat = az.rhat(idata, method="rank")
    bulk = az.ess(idata, method="bulk")
    tail = az.ess(idata, method="tail")
    for site in SITE_NAMES:
        assert math.isfinite(float(rhat[site]))
        assert math.isfinite(float(bulk[site]))
        assert math.isfinite(float(tail[site]))


def _passing_stats():
    occupancy = {"P_lo": 0.30, "P_mid": 0.20, "P_hi": 0.50, "n": 2000}
    return {
        "rhat": {site: 1.001 for site in SITE_NAMES},
        "ess_bulk": {site: 1000.0 for site in SITE_NAMES},
        "ess_tail": {site: 900.0 for site in SITE_NAMES},
        "per_chain_occupancy": [dict(occupancy) for _ in range(4)],
        "pooled_occupancy": dict(occupancy, n=8000),
        "divergence_rate": 0.0005,
        "depth_saturation_rate": 0.05,
        "notpsd_early_counts": [0, 0, 0, 0],
        "notpsd_post_warmup_rate": 0.0005,
        "notpsd_post_warmup_total": 1,
        "authority_coverage": {
            "lo": {"passed": True}, "mid": {"passed": True}},
        "arviz_version": "0.23.4",
    }


@pytest.mark.parametrize(("criterion", "mutate"), [
    ("rhat", lambda s: s["rhat"].__setitem__(SITE_NAMES[0], 1.01)),
    ("ess_bulk", lambda s: s["ess_bulk"].__setitem__(SITE_NAMES[0], 400.0)),
    ("ess_tail", lambda s: s["ess_tail"].__setitem__(SITE_NAMES[0], 400.0)),
    ("occupancy", lambda s: s["per_chain_occupancy"][0].__setitem__("P_lo", 0.36)),
    ("divergence_rate", lambda s: s.__setitem__("divergence_rate", 0.001)),
    ("depth_saturation_rate", lambda s: s.__setitem__("depth_saturation_rate", 0.10)),
    ("notpsd_early_window", lambda s: s["notpsd_early_counts"].__setitem__(2, 1)),
    ("notpsd_rate", lambda s: s.__setitem__("notpsd_post_warmup_rate", 0.001)),
    ("authority_coverage", lambda s: s["authority_coverage"]["mid"].__setitem__("passed", False)),
])
def test_each_acceptance_criterion_has_pass_and_named_fail(criterion, mutate):
    passing = evaluate_acceptance_from_stats(_passing_stats())
    assert passing["passed"]
    assert passing["failed_criteria"] == []

    failing_stats = _passing_stats()
    mutate(failing_stats)
    failing = evaluate_acceptance_from_stats(failing_stats)
    assert not failing["passed"]
    assert criterion in failing["failed_criteria"]


def test_authority_coverage_matches_hand_worked_formula():
    result = authority_coverage_check(
        chain_mass=0.40, bulk_ess=400, authority_mass=0.35,
        authority_se=0.01)
    expected_se_chain = math.sqrt(0.4 * 0.6 / 400)
    expected_limit = 2 * math.sqrt(0.01 ** 2 + expected_se_chain ** 2)
    assert result["chain_se"] == pytest.approx(expected_se_chain, abs=1e-15)
    assert result["absolute_difference"] == pytest.approx(0.05, abs=1e-15)
    assert result["two_se_limit"] == pytest.approx(expected_limit, abs=1e-15)
    assert result["passed"] == (0.05 <= expected_limit)


def test_four_site_contract_rejects_wrong_init_set_through_guard():
    frozen = load_frozen_starts()
    model, _likelihood, _x, _y = build_cell_model("informative")
    wrong = dict(frozen["informative"]["init_values"][0])
    wrong.pop(SITE_NAMES[0])
    with pytest.raises(ValueError, match="four-site"):
        guard_validation_start(model, wrong)


def _g_run_fn(draws, candidates, metric_names, taus):
    names = [candidate.name for candidate in candidates]
    g = np.asarray(draws, dtype=float)
    result = {metric_names[0]: {}}
    for tau in taus:
        bms = soft_transfer(g, float(tau), names)
        bms.metric_name = metric_names[0]
        result[metric_names[0]][float(tau)] = bms
    return result


class _Candidate:
    def __init__(self, name):
        self.name = name


def test_rb_primary_is_pooled_800_not_mean_of_normalized_chains():
    row_types = ([0.0, 10.0], [10.0, 0.0], [0.0, 1.0], [0.0, 1.0])
    chain_g = [[row] * 200 for row in row_types]
    result = aggregate_validation_bms(
        chain_g, [_Candidate("a"), _Candidate("b")],
        metric_names=["fixture_g"], taus=[1.0], run_fn=_g_run_fn)

    pooled_g = np.asarray([row for chain in chain_g for row in chain])
    expected = soft_transfer(pooled_g, 1.0, ["a", "b"]).instance_posteriors
    primary = np.asarray(
        result["primary"]["fixture_g"]["instance_posteriors"]["1.0"])
    diagnostic_mean = np.asarray(
        result["cross_chain_diagnostics"]["fixture_g"]["1.0"]
        ["per_chain_mean_diagnostic_only"])
    assert result["n_pooled_predictives"] == 800
    assert primary == pytest.approx(expected, abs=1e-15)
    assert np.max(np.abs(primary - diagnostic_mean)) > 1e-6
    assert "DIAGNOSTIC ONLY" in result["diagnostic_label"]


def test_predictive_and_draw_cardinality_contracts(monkeypatch):
    import experiments.m2br_run_common as common

    monkeypatch.setattr(common, "extract_gp_predictives",
                        lambda *args, **kwargs: [object()])
    model = SimpleNamespace(_m2br_prior_config=object())
    with pytest.raises(ValueError, match="predictive cardinality"):
        score_samples({}, model, None, None, None, None, [],
                      n_predictives=2, expected_predictives=2)

    with pytest.raises(ValueError, match="draw cardinality"):
        chains_to_inference_data(
            _four_chain_fixture(n_draws=7), expected_draws=8)

    with pytest.raises(ValueError, match="predictive cardinality"):
        aggregate_validation_bms(
            [[[0.0, 1.0]]] * 4,
            [_Candidate("a"), _Candidate("b")],
            metric_names=["fixture_g"], taus=[1.0], run_fn=_g_run_fn,
            expected_per_chain=2)


def test_notpsd_failure_persists_diagnostics_and_no_sample_cache(tmp_path):
    frozen = load_frozen_starts()
    diag = _diagnostics()

    def raising_sampler(*args, **kwargs):
        error = RuntimeError("synthetic terminal NotPSD")
        error.diagnostics = diag
        raise error

    result = run_validation_chain(
        VALIDATION_CELLS[0], 0, frozen,
        sampler_fn=raising_sampler, output_dir=tmp_path)
    assert result["status"] == "failed"
    cell_dir = tmp_path / "V1"
    assert not (cell_dir / "chain0_samples.npz").exists()
    assert not (cell_dir / "chain0_predictives.npz").exists()
    failure = json.loads((cell_dir / "chain0_failure.json").read_text())
    assert failure["exception"]["type"] == "RuntimeError"
    assert failure["diagnostics"]["schema_version"] == 3
    assert failure["diagnostics"]["notpsd_post_warmup_total"] == 0


class _Clock:
    def __init__(self, now=0.0):
        self.now = now

    def __call__(self):
        return self.now


def _slow_task():
    time.sleep(0.2)
    return "too late"


def _ignore_terminate_task():
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    time.sleep(5)


def test_deadline_projection_gate_driver_stop_and_isolated_timeout(tmp_path):
    clock = _Clock()
    deadline = Deadline(100, reserve_seconds=10, clock=clock)
    deadline.start()
    clock.now = 11
    assert not deadline.may_start("first", 80)
    report = run_audit(output_dir=tmp_path / "audit", deadline=deadline,
                       isolate=False,
                       sampler_fn=lambda *a, **k: pytest.fail("sampler reached"),
                       verify_arms_fn=lambda **kwargs: {"status": "SKIP"})
    assert report["first_unexecuted_run"] == "d12_informative_td7"
    stop = json.loads((tmp_path / "audit" / "stop.json").read_text())
    assert stop["first_unexecuted_run"] == "d12_informative_td7"

    timeout = run_isolated(
        _ignore_terminate_task, projection=1,
        hard_cutoff=time.monotonic() + 0.03,
        termination_grace=0.02, run_id="timeout-fixture",
        failure_path=tmp_path / "timeout.json")
    assert timeout["status"] == "timed_out"
    assert json.loads((tmp_path / "timeout.json").read_text())["status"] == "timed_out"


def test_bare_real_driver_calls_require_explicit_authorization(tmp_path):
    with pytest.raises(PermissionError, match="authorized=True"):
        run_audit(output_dir=tmp_path / "audit")
    with pytest.raises(PermissionError, match="authorized=True"):
        run_validation(output_dir=tmp_path / "validation")


def test_start_hash_tampering_stops_before_injection(tmp_path):
    payload = json.loads(Path(FREEZE_PATH).read_text())
    record = payload["configs"]["informative"]["chains"][1]
    original_hash = record["semantic_sha256"]
    record["values"][SITE_NAMES[0]][0] += 1e-9
    tampered = tmp_path / "tampered.json"
    tampered.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="pinned sha256 mismatch"):
        load_frozen_starts(tampered)
    assert EXPECTED_MANIFEST_SHA256 != __import__("hashlib").sha256(
        tampered.read_bytes()).hexdigest()

    # Per-start semantic verification remains independently enforced.
    with pytest.raises(ValueError, match="semantic sha256 mismatch"):
        _reconstruct_start(record)
    assert record["semantic_sha256"] == original_hash


def test_unchanged_prior_is_summary_verification_passes_and_detects_drift(tmp_path):
    config = "informative"
    per_seed, all_ths, all_lml = {}, [], []
    for seed in (0, 1, 2):
        ths = np.array([
            [1.0, 1.1, 0.08, 0.10],
            [1.2, 0.9, 0.07, 0.20],
            [0.8, 1.0, 0.09, 0.35],
            [1.1, 1.2, 0.06, 0.50],
        ]) + seed * 1e-3
        lml = np.array([-0.2, -0.1, -1.0, -1.5]) - seed * 0.01
        np.savez(tmp_path / f"is_draws_{config}_s{seed}.npz",
                 ths=ths, lml=lml, seed=seed)
        per_seed[str(seed)] = pss._is_summary(ths, lml)
        all_ths.append(ths)
        all_lml.append(lml)
    authority = {
        "per_seed": per_seed,
        "pooled": pss._is_summary(
            np.concatenate(all_ths), np.concatenate(all_lml)),
    }
    stage_path = tmp_path / f"stage_a_{config}.json"
    stage_path.write_text(json.dumps({"prior_is": authority}))

    passing = verify_unchanged_arms(
        source_dir=tmp_path, configs=(config,), run_sir=False)
    assert passing["status"] == "PASS"
    assert passing["configs"][config]["prior_is"]["status"] == "PASS"

    authority["per_seed"]["1"]["P_noise_mid"] += 1e-8
    stage_path.write_text(json.dumps({"prior_is": authority}))
    failing = verify_unchanged_arms(
        source_dir=tmp_path, configs=(config,), run_sir=False)
    assert failing["status"] == "FAIL"
    check = failing["configs"][config]["prior_is"]["1"]
    assert check["status"] == "FAIL"
    assert any(item["field"] == "P_noise_mid" for item in check["mismatches"])


def test_transaction_commits_samples_last_and_failure_leaves_no_cache(
        tmp_path, monkeypatch):
    import experiments.m2br_run_common as common

    diagnostics = tmp_path / "diagnostics.json"
    results = tmp_path / "results.json"
    samples = tmp_path / "samples.npz"
    real_replace = common.os.replace

    def fail_after_diagnostics(source, destination):
        if Path(destination) == results:
            raise OSError("synthetic failure between diagnostics and samples")
        return real_replace(source, destination)

    monkeypatch.setattr(common.os, "replace", fail_after_diagnostics)
    with pytest.raises(OSError, match="between diagnostics and samples"):
        transactional_persist(
            json_artifacts={diagnostics: {"ok": True}, results: {"ok": True}},
            npz_artifacts={samples: {"x": np.arange(3)}},
            samples_path=samples)
    assert diagnostics.exists()
    assert not samples.exists()
    assert not list(tmp_path.glob("*.tmp-*"))


def test_atomic_refuses_overwrite_and_cleans_partial_on_writer_failure(tmp_path):
    existing = tmp_path / "existing.json"
    existing.write_text("completed")
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        require_absent(existing)
    with pytest.raises(FileExistsError):
        atomic_write_json(existing, {"new": True})
    assert existing.read_text() == "completed"

    target = tmp_path / "partial.json"
    with pytest.raises(TypeError):
        atomic_write_json(target, {"not_json_serializable": object()})
    assert not target.exists()
    assert list(tmp_path.glob("partial.json.tmp-*")) == []
