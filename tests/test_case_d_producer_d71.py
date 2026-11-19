"""
Case D producer PR (D71): the changes that decision-sheet lines A1a and A3
and finding A3 of the 2026-11 triage need before the canonical Case D run.
Each test fails on origin/main at f6bd33d.

1. A candidate fit in which no optimizer stage succeeds raises instead of
   returning the box midpoints, and the producer raises under strict.
2. extract_map_predictives perturbs and records each raw parameter once.
3. Draw wins and winner labels split exact ties; the tie-aware record and
   the per-tau weight ESS are serialized beside the archived fields.
4. The default metric roster includes pw_kl_vcal, and --metrics selects.
5. The seed reaches the MAP perturbations.
"""

import importlib
import json
import os
import sys
import warnings
from types import SimpleNamespace

import numpy as np
import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("gpytorch")

from bistar_gp.bms_star import soft_transfer
from bistar_gp.config import PRIMARY_METRIC
from bistar_gp.errors import EvaluationFailure

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRACTICE = os.path.join(REPO, "experiments", "practice_EvansEtAL")
LEGACY = {"pw_hellinger", "pw_mse", "pw_nll"}


@pytest.fixture(scope="module")
def practice():
    """run.py and candidates.py of the Case D producer, from this checkout."""
    if PRACTICE not in sys.path:
        sys.path.insert(0, PRACTICE)
    saved_filters = warnings.filters[:]
    try:
        run = importlib.import_module("run")    # run.py silences warnings at import
        candidates = importlib.import_module("candidates")
    finally:
        warnings.filters[:] = saved_filters
    assert os.path.dirname(run.__file__) == PRACTICE
    assert os.path.dirname(candidates.__file__) == PRACTICE
    return SimpleNamespace(run=run, candidates=candidates)


def _small_run(**overrides):
    kw = dict(prior_configs=["practitioner"], mode="map", verbose=False,
              n_eval=8, n_posterior_samples=4, taus=np.array([1.0]))
    kw.update(overrides)
    return kw


def _producer_gp(run, cfg="practitioner"):
    """The GP that run_one builds for one synthetic subject, before its MAP fit."""
    curve = run.generate_demo_data(n_subjects=1, seed=3)[0]
    nc = run.normalize(curve)
    kernels, names = run.build_kernel(run.PRACTICE_CONFIGS[cfg])
    lik = run.build_likelihood(run.PRACTICE_CONFIGS[cfg])
    x = torch.tensor(nc.x).double()
    y = torch.tensor(nc.y).double()
    model, lik = run.build_model(x, y, kernels, names, lik)
    return model, lik, x, y, torch.linspace(0, 1, 8).double()


# ── 1. a fit with no successful stage raises ───────────────────────

def test_candidate_fit_without_a_successful_stage_raises(practice):
    # A constant series inverts the amplitude box (0.01, 10 * range), so
    # differential evolution and every L-BFGS-B restart raise. The fit used
    # to return the box midpoints (Power: a = 0.005, c = 225.0) as a result.
    x = np.arange(1.0, 21.0)
    flat = np.full(20, 300.0)
    for model in (practice.candidates.PowerModel(), practice.candidates.ExponentialModel()):
        with pytest.raises(EvaluationFailure, match="no optimizer stage succeeded"):
            model.fit(x, flat)

    # an ordinary practice curve still fits
    power = practice.candidates.PowerModel()
    power.fit(x, 300.0 + 200.0 * x ** -0.5)
    assert np.all(np.isfinite([power.a, power.b, power.c, power.sigma]))

    # the producer's candidate-failure path: strict raises naming the
    # candidate; with every candidate failed, non-strict cannot score either
    run = practice.run
    curve = run.LearningCurve(dataset_id="synth_flat", subject_id=0, condition="default",
                              task_type="synthetic", trial=x, rt=flat, n_trials=20)
    with pytest.raises(RuntimeError, match="candidate 'Power' failed to fit"):
        run.run_one(run.normalize(curve), **_small_run(strict=True))
    with pytest.raises(RuntimeError, match=r"no candidate could be fitted \['Exponential', 'Power'\]"):
        run.run_one(run.normalize(curve), **_small_run(strict=False))


# ── 2. MAP extraction collects each raw parameter once ────────────────

def test_map_extraction_perturbs_each_raw_parameter_once(practice):
    # build_model registers the likelihood inside the model, so its raw_noise
    # appears under both parameter listings; it used to be perturbed twice
    # and recorded under two names, the first of them never applied.
    model, lik, x, y, x_eval = _producer_gp(practice.run)
    by_name = {**dict(lik.named_parameters()), **dict(model.named_parameters())}
    scalar = {id(p) for p in by_name.values() if p.requires_grad and p.numel() == 1}
    samples = practice.run.extract_map_predictives(model, lik, x, y, x_eval, n_samples=3)
    assert len(samples) == 3
    for sample in samples:
        refs = [id(by_name[name]) for name in sample.hyperparameters]
        assert len(set(refs)) == len(refs)
        assert set(refs) == scalar


# ── 3. ties split; the tie-aware record is serialized ─────────────────

def test_draw_wins_and_winner_labels_split_exact_ties(practice, tmp_path, monkeypatch):
    run = practice.run
    # ledger Item 5 pin: draw 0 ties, draw 1 goes to the first candidate
    split_table = np.array([[0.0, 0.0], [10.0, 11.0]])
    # identical columns: every draw ties, and so do the posteriors at every tau
    tied_table = np.array([[1.0, 1.0], [2.0, 2.0]])
    tables = {"pw_nll": split_table, "pw_mse": tied_table}
    taus = np.array([0.5, 1.0, 2.0])

    def scored(metric, tau, names):
        return soft_transfer(tables[metric], tau, names, metric_name=metric)

    def stub_bms(gp_samples, candidate_results, metric_names=None, taus=None,
                 normalize_per_draw=False):
        names = [c.name for c in candidate_results]
        return {m: {t: scored(m, t, names) for t in taus} for m in metric_names}

    monkeypatch.setattr(run, "run_bms_star", stub_bms)
    out = tmp_path / "ties"
    run.run_all(run.generate_demo_data(n_subjects=1, seed=3), out,
                **_small_run(metrics=["pw_nll", "pw_mse"], taus=taus, seed=5))
    (path,) = out.glob("synth_*.json")
    record = json.loads(path.read_text())
    first, second = (c.name for c in run.build_core_candidates())

    diag = record["bistar_G_diagnostics"]["practitioner"]
    per_model = diag["pw_nll"]["per_model"]
    assert per_model[first]["hard_win_credit"] == pytest.approx(0.75)
    assert per_model[second]["hard_win_credit"] == pytest.approx(0.25)
    assert (per_model[first]["attainment"], per_model[second]["attainment"]) == (1.0, 0.5)
    assert diag["pw_nll"]["tie_fraction"] == 0.5
    # the archived first-index count is kept for comparison with the
    # suspended archive
    assert (per_model[first]["raw_draw_wins"], per_model[second]["raw_draw_wins"]) == (2, 0)
    per_model = diag["pw_mse"]["per_model"]
    assert per_model[first]["hard_win_credit"] == per_model[second]["hard_win_credit"] == 0.5
    assert diag["pw_mse"]["tie_fraction"] == 1.0

    # an exact posterior tie names no winner, and the cohort count splits it
    winners = record["bistar_winners"]["practitioner"]
    assert set(winners["pw_mse"].values()) == {None}
    assert set(winners["pw_nll"].values()) == {first}
    aggregate = json.loads((out / "aggregate.json").read_text())
    assert aggregate["bistar"]["practitioner"]["pw_mse"] == {first: 0.5, second: 0.5}
    assert aggregate["bistar"]["practitioner"]["pw_nll"] == {first: 1.0}

    # the per-tau weight ESS of each candidate, beside the posteriors
    ess = record["bistar_weight_ess"]["practitioner"]
    for metric in tables:
        assert set(ess[metric]) == {str(float(t)) for t in taus}
        for t in taus:
            expected = scored(metric, t, [first, second]).weight_ess
            got = ess[metric][str(float(t))]
            assert [got[first], got[second]] == pytest.approx(list(expected))


# ── 4. metric roster and --metrics ────────────────────────────────────

def test_default_roster_scores_pw_kl_vcal_and_metrics_flag_selects(practice, tmp_path,
                                                                    monkeypatch):
    run = practice.run
    res = run.run_all(run.generate_demo_data(n_subjects=1, seed=3), tmp_path / "roster",
                      **_small_run())
    assert set(res[0].bistar_probs["practitioner"]) == LEGACY | {PRIMARY_METRIC}
    assert PRIMARY_METRIC == "pw_kl_vcal"

    seen = {}
    monkeypatch.setattr(run, "run_all", lambda curves, output_dir, **kw: seen.update(kw))
    cli = ["run.py", "--demo", "--output_dir", str(tmp_path / "cli")]
    monkeypatch.setattr(sys, "argv", cli)
    run.main()
    assert set(seen["metrics"]) == LEGACY | {PRIMARY_METRIC}
    monkeypatch.setattr(sys, "argv", cli + ["--metrics", "pw_nll", PRIMARY_METRIC])
    run.main()
    assert seen["metrics"] == ["pw_nll", PRIMARY_METRIC]
    monkeypatch.setattr(sys, "argv", cli + ["--metrics", "pw_not_a_metric"])
    with pytest.raises(SystemExit):
        run.main()


# ── 5. the seed reaches the MAP perturbations ─────────────────────────

def test_seed_reaches_the_map_perturbations(practice, tmp_path, monkeypatch):
    run = practice.run
    model, lik, x, y, x_eval = _producer_gp(run)

    def perturbations(seed):
        return [s.hyperparameters for s in run.extract_map_predictives(
            model, lik, x, y, x_eval, n_samples=3, seed=seed)]

    assert perturbations(1) == perturbations(1)
    assert perturbations(1) != perturbations(2)
    assert perturbations(1)[0] == perturbations(2)[0]      # draw 0 is the MAP point
    assert perturbations(None) == perturbations(42)        # no seed: the historical draws

    seen = []
    real = run.extract_map_predictives

    def spy(*a, **k):
        seen.append(k.get("seed"))
        return real(*a, **k)

    monkeypatch.setattr(run, "extract_map_predictives", spy)
    res = run.run_all(run.generate_demo_data(n_subjects=1, seed=3), tmp_path / "seeded",
                      **_small_run(prior_configs=["practitioner", "moderate"], seed=11))
    assert seen == [11, 11]
    assert res[0].seed == 11
