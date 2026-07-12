"""Hermetic contract tests for the gated M2bR v1.16 driver.

No test calls ``fit_hmc_e1`` or launches a real sampler chain.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from functools import partial

from bistar_gp.bms_star import GPPosteriorSample, soft_transfer
from bistar_gp.sampler_diagnostics import SamplerDiagnostics
from experiments import m2br_v116_run as v116
from experiments import m2br_run_common as common
from experiments.m2br_run_common import (
    FREEZE_PATH,
    SITE_NAMES,
)


@pytest.fixture
def reg():
    """Register test mock samplers as ungated for the duration of a test, then
    clean up so the fail-closed registry does not leak across tests."""
    added = []

    def _register(fn):
        common.register_mock_sampler(fn)
        added.append(fn)
        return fn

    yield _register
    for fn in added:
        common.unregister_mock_sampler(fn)


def _mock_diagnostics(n_draws, n_warmup, depth):
    return SamplerDiagnostics(
        sampler="v116_hermetic_mock",
        n_chains=1,
        n_draws=n_draws,
        n_warmup=n_warmup,
        site_names=SITE_NAMES,
        max_tree_depth=depth,
        step_size=0.1,
        divergence_draws=((),),
        acceptance_rate=(0.9,),
        leapfrog_counts=(tuple([3] * n_draws),),
        notpsd_rejections=0,
        notpsd_rejections_warmup=0,
        notpsd_rejections_per_draw=(tuple([0] * n_draws),),
        unavailable=(),
    )


def _lightweight_scoring(samples, model, likelihood, x, y, x_eval_torch,
                         candidate_results, n_predictives):
    del model, likelihood, x, y, x_eval_torch, candidate_results
    gp_samples = [
        GPPosteriorSample(
            mean=np.array([float(index), 0.0]),
            cov=np.eye(2), hyperparameters={})
        for index in range(n_predictives)
    ]
    summaries = {
        site: {"n": int(np.asarray(values).size)}
        for site, values in samples.items()
    }
    return {
        "gp_samples": gp_samples,
        "n_predictives": len(gp_samples),
        "metrics": {},
        "site_summaries": summaries,
    }


def test_v116_mock_cell_end_to_end_writes_four_chains_and_escalated_budget(
        tmp_path, monkeypatch, reg):
    calls = []

    @reg
    def sampler(model, likelihood, x, y, **kwargs):
        del model, likelihood, x, y
        calls.append(kwargs)
        n = kwargs["n_samples"]
        rng = np.random.default_rng(kwargs["seed"])
        samples = {
            site: np.maximum(
                1e-6, center + rng.normal(0.0, center * 0.01, n))
            for site, center in zip(SITE_NAMES, (2.0, 1.0, 0.08, 0.22))
        }
        diag = _mock_diagnostics(
            n, kwargs["n_warmup"], kwargs["max_tree_depth"])
        return samples, diag

    def acceptance(chain_samples, chain_diagnostics, authority,
                   reportable_bands, *, expected_draws):
        assert expected_draws == 8000
        assert len(chain_samples) == len(chain_diagnostics) == 4
        assert all(len(chain[SITE_NAMES[0]]) == 8000
                   for chain in chain_samples)
        assert reportable_bands == ["lo", "mid", "hi"]
        assert authority["P_noise_lo"] == pytest.approx(0.27681233655255916)
        return {"passed": True, "failed_criteria": [], "stats": {}}

    def aggregate(chain_predictives, candidate_results, **kwargs):
        del candidate_results
        assert [len(chain) for chain in chain_predictives] == [200] * 4
        assert kwargs["expected_per_chain"] == 200
        return {"n_pooled_predictives": 800, "primary": {}}

    monkeypatch.setattr(
        v116.validation, "evaluate_cell_acceptance", acceptance)
    monkeypatch.setattr(
        v116.validation, "aggregate_validation_bms", aggregate)

    output = tmp_path / "v116"
    report = v116.run_v116(
        sampler_fn=sampler, scoring_fn=_lightweight_scoring,
        output_dir=output, isolate=False)

    assert report["status"] == "completed"
    assert report["completed_cells"] == ["V1e"]
    assert len(calls) == 4
    for chain, kwargs in enumerate(calls):
        assert kwargs["seed"] == chain
        assert kwargs["n_warmup"] == 3000
        assert kwargs["n_samples"] == 8000
        assert kwargs["max_tree_depth"] == 7
        assert kwargs["init_to_map"] is False
        assert kwargs["return_diagnostics"] is True

    for chain in range(4):
        paths = v116.v116_chain_paths(output, chain)
        assert all(paths[kind].exists() for kind in (
            "samples", "predictives", "diagnostics", "results"))
        result = json.loads(paths["results"].read_text())
        assert result["n_warmup"] == 3000
        assert result["n_samples"] == 8000
    cell = json.loads((output / "cell_results.json").read_text())
    assert cell["computed_bms_for_diagnostic_record"][
        "n_pooled_predictives"] == 800


def test_real_fit_hmc_e1_requires_programmatic_authorization(tmp_path):
    with pytest.raises(PermissionError, match="authorized=True"):
        v116.run_v116(output_dir=tmp_path)
    assert not list(tmp_path.iterdir())

    frozen = v116.validation.load_frozen_starts()
    with pytest.raises(PermissionError, match="authorized=True"):
        v116.run_v116_chain(0, frozen, output_dir=tmp_path)
    assert not list(tmp_path.iterdir())


def test_manifest_hash_mismatch_aborts_before_sampling(tmp_path, reg):
    tampered = tmp_path / "tampered_manifest.json"
    tampered.write_text(Path(FREEZE_PATH).read_text() + "\n")
    sampled = []

    @reg
    def forbidden_sampler(*args, **kwargs):
        sampled.append((args, kwargs))
        pytest.fail("sampler must not be reached")

    with pytest.raises(ValueError, match="manifest pinned sha256 mismatch"):
        v116.run_v116(
            sampler_fn=forbidden_sampler,
            manifest_path=tampered,
            output_dir=tmp_path / "output",
            isolate=False)
    assert sampled == []
    assert not (tmp_path / "output").exists()


def test_start_semantic_sha_mismatch_aborts_before_sampling(
        tmp_path, monkeypatch, reg):
    frozen = copy.deepcopy(v116.validation.load_frozen_starts())
    frozen["informative"]["init_values"][0][SITE_NAMES[0]][0] += 1e-9
    sampled = []

    monkeypatch.setattr(
        v116.validation, "load_frozen_starts", lambda path: frozen)

    @reg
    def forbidden_sampler(*args, **kwargs):
        sampled.append((args, kwargs))
        pytest.fail("sampler must not be reached")

    with pytest.raises(ValueError, match="frozen semantic hash"):
        v116.run_v116(
            sampler_fn=forbidden_sampler,
            output_dir=tmp_path / "output", isolate=False)
    assert sampled == []
    assert not list((tmp_path / "output").glob("chain*_samples.npz"))


class _Candidate:
    def __init__(self, name):
        self.name = name


def _g_run_fn(draws, candidates, metric_names, taus):
    names = [candidate.name for candidate in candidates]
    g = np.asarray(draws, dtype=float)
    result = {metric_names[0]: {}}
    for tau in taus:
        bms = soft_transfer(g, float(tau), names)
        bms.metric_name = metric_names[0]
        result[metric_names[0]][float(tau)] = bms
    return result


def test_v116_rb_primary_pools_800_rows_with_one_normalization():
    row_types = ([0.0, 10.0], [10.0, 0.0], [0.0, 1.0], [0.0, 1.0])
    chain_g = [[row] * 200 for row in row_types]
    result = v116.validation.aggregate_validation_bms(
        chain_g, [_Candidate("a"), _Candidate("b")],
        metric_names=["fixture_g"], taus=[1.0], run_fn=_g_run_fn)

    pooled_g = np.asarray([row for chain in chain_g for row in chain])
    expected = soft_transfer(
        pooled_g, 1.0, ["a", "b"]).instance_posteriors
    primary = np.asarray(
        result["primary"]["fixture_g"]["instance_posteriors"]["1.0"])
    diagnostic_mean = np.asarray(
        result["cross_chain_diagnostics"]["fixture_g"]["1.0"]
        ["per_chain_mean_diagnostic_only"])
    assert result["n_pooled_predictives"] == 800
    assert primary == pytest.approx(expected, abs=1e-15)
    assert np.max(np.abs(primary - diagnostic_mean)) > 1e-6
    assert "one BMS* normalization" in result["primary_label"]


def test_cli_dry_run_routes_only_to_dryrun_namespace(tmp_path, monkeypatch):
    real_namespace = tmp_path / "m2br_v116_informative"
    calls = []

    def fake_run_v116(**kwargs):
        calls.append(kwargs)
        output = Path(kwargs["output_dir"])
        output.mkdir(parents=True)
        (output / "mock_only.marker").write_text("mock")
        return {"status": "completed", "completed_cells": ["V1e"]}

    monkeypatch.setattr(v116, "DEFAULT_OUTPUT_DIR", real_namespace)
    monkeypatch.setattr(v116, "run_v116", fake_run_v116)

    assert v116.main(["--dry-run"]) == 0
    assert len(calls) == 1
    assert calls[0]["sampler_fn"] is v116.deterministic_mock_sampler
    assert calls[0]["isolate"] is False
    assert calls[0]["output_dir"] == real_namespace / "_dryrun"
    assert (real_namespace / "_dryrun" / "mock_only.marker").exists()
    assert not list(real_namespace.glob("chain*"))


def test_v116_plan_exact_hash_and_frozen_start_pins_agree():
    plan = v116.load_v116_plan(
        frozen=v116.validation.load_frozen_starts())
    assert hashlib.sha256(v116.V116_PLAN_PATH.read_bytes()).hexdigest() == (
        v116.EXPECTED_V116_PLAN_SHA256)
    assert plan["changed_parameters_only"] == {
        "n_warmup": 3000, "n_draws": 8000}


def test_v116_plan_hash_mismatch_aborts_before_sampling(tmp_path, reg):
    """Symmetric to the manifest-tamper test: a mutated v1.16 pin must abort."""
    tampered = tmp_path / "tampered_plan.json"
    tampered.write_text(v116.V116_PLAN_PATH.read_text() + "\n")
    sampled = []

    @reg
    def forbidden_sampler(*args, **kwargs):
        sampled.append((args, kwargs))
        pytest.fail("sampler must not be reached")

    with pytest.raises(ValueError, match="run-plan pinned sha256 mismatch"):
        v116.run_v116(
            sampler_fn=forbidden_sampler,
            plan_path=tampered,
            output_dir=tmp_path / "output",
            isolate=False)
    assert sampled == []
    assert not (tmp_path / "output").exists()


class _TimedOutDeadline:
    """Minimal fake: admits the first chain, then reports an absolute timeout."""
    t0 = 0.0

    def start(self):  # pragma: no cover - t0 is preset
        pass

    def may_start(self, run_id, projection):
        return True

    def sampling_cutoff(self):
        return 1e18

    def run_isolated(self, fn, projection, cutoff, *, run_id, failure_path):
        del fn, projection, cutoff, run_id, failure_path
        return {"status": "timed_out"}


def test_v116_isolated_timeout_stops_and_reports(tmp_path, reg):
    @reg
    def forbidden_sampler(*args, **kwargs):
        pytest.fail("sampler must not be reached on a timed-out chain")

    output = tmp_path / "out"
    report = v116.run_v116(
        sampler_fn=forbidden_sampler,
        output_dir=output,
        deadline=_TimedOutDeadline(),
        isolate=True)

    assert report["status"] == "stopped"
    assert report["first_unexecuted_run"] == "V1e.chain0"
    stop = json.loads((output / "stop.json").read_text())
    assert stop["reason"] == "absolute_cutoff_timeout"
    assert not list(output.glob("chain*_samples.npz"))


def test_v116_execute_cli_routes_to_real_sampler_and_authorized(monkeypatch):
    """The --execute CLI path must wire fit_hmc_e1 + authorized=True (no HMC run)."""
    calls = []

    def fake_run_v116(**kwargs):
        calls.append(kwargs)
        return {"status": "completed", "completed_cells": ["V1e"]}

    monkeypatch.setattr(v116, "run_v116", fake_run_v116)
    assert v116.main(["--execute"]) == 0
    assert len(calls) == 1
    assert calls[0]["sampler_fn"] is v116.fit_hmc_e1
    assert calls[0]["authorized"] is True
    assert calls[0]["output_dir"] == v116.DEFAULT_OUTPUT_DIR


def test_v116_no_overwrite_of_existing_chain_artifact(tmp_path, reg):
    """require_absent must refuse to clobber a prior chain artifact, before sampling."""
    output = tmp_path / "v116"
    output.mkdir(parents=True)
    (output / "chain0_samples.npz").write_text("prior-run-artifact")
    frozen = v116.validation.load_frozen_starts()

    @reg
    def forbidden_sampler(*args, **kwargs):
        pytest.fail("sampler must not run when a prior artifact exists")

    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        v116.run_v116_chain(
            0, frozen, sampler_fn=forbidden_sampler, output_dir=output)


def test_v116_acceptance_fail_marks_withdrawn_and_no_replacement(
        tmp_path, monkeypatch, reg):
    @reg
    def sampler(model, likelihood, x, y, **kwargs):
        del model, likelihood, x, y
        n = kwargs["n_samples"]
        rng = np.random.default_rng(kwargs["seed"])
        samples = {
            site: np.maximum(1e-6, center + rng.normal(0.0, center * 0.01, n))
            for site, center in zip(SITE_NAMES, (2.0, 1.0, 0.08, 0.22))
        }
        diag = _mock_diagnostics(
            n, kwargs["n_warmup"], kwargs["max_tree_depth"])
        return samples, diag

    monkeypatch.setattr(
        v116.validation, "evaluate_cell_acceptance",
        lambda *a, **k: {"passed": False,
                         "failed_criteria": ["occupancy"], "stats": {}})
    monkeypatch.setattr(
        v116.validation, "aggregate_validation_bms",
        lambda *a, **k: {"n_pooled_predictives": 800, "primary": {}})

    output = tmp_path / "v116fail"
    report = v116.run_v116(
        sampler_fn=sampler, scoring_fn=_lightweight_scoring,
        output_dir=output, isolate=False)

    assert report["status"] == "completed_with_failures"
    assert report["failed_cells"] == ["V1e"]
    cell = json.loads((output / "cell_results.json").read_text())
    assert cell["status"] == "failed_validation"
    assert cell["replacement_numbers"] is None
    assert cell["historical_counterparts"] == "WITHDRAWN/UNVALIDATED"


def test_v116_partial_wrapped_real_sampler_is_gated(tmp_path):
    """Fail-closed (D35): a wrapper around fit_hmc_e1 is not the registered mock,
    so it is gated exactly like the real sampler -- closes the identity bypass."""
    wrapped = partial(v116.fit_hmc_e1)
    with pytest.raises(PermissionError, match="authorized=True"):
        v116.run_v116(sampler_fn=wrapped, output_dir=tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_v116_gated_sampler_rejected_when_not_isolated(tmp_path):
    """A gated (real) sampler must run isolated; isolate=False is refused before
    any chain, so the absolute cutoff always applies to real runs (D35)."""
    with pytest.raises(PermissionError, match="isolated"):
        v116.run_v116(sampler_fn=v116.fit_hmc_e1, authorized=True,
                      isolate=False, output_dir=tmp_path / "out")
    assert not (tmp_path / "out").exists()
