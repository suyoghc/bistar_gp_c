"""
FIX-7 (2026-09 review): metric roles (W1) and the withdrawn-cache registry
(M2bR banner), package side.

Pins: ExperimentConfig().metrics contains the primary metric and keeps the
legacy entries; run_bms_star warns about appendix-only metrics only on the
implicit metric_names=None path; load_hmc_samples refuses every registered
withdrawn path and admits it, with a warning, under allow_withdrawn=True.
"""

import logging
import os
import subprocess
import sys
import warnings

import numpy as np
import pytest

import bistar_gp.metrics_v2  # noqa: F401  registers pw_kl_vcal
from bistar_gp.bms_star import GPPosteriorSample, run_bms_star
from bistar_gp.candidates import CandidateResult
from bistar_gp.config import (
    APPENDIX_METRICS, PRIMARY_METRIC, WITHDRAWN_CACHES, ExperimentConfig,
    is_withdrawn_cache, load_hmc_samples,
)


def test_metric_roles_in_config():
    assert PRIMARY_METRIC == "pw_kl_vcal"
    assert APPENDIX_METRICS == ("kl_forward",)
    metrics = ExperimentConfig().metrics
    assert PRIMARY_METRIC in metrics
    legacy = ["kl_forward", "kl_backward", "kl_symmetric", "hellinger",
              "pw_kl_forward", "pw_kl_backward", "pw_kl_symmetric", "pw_hellinger",
              "pw_mse", "pw_nll"]
    assert metrics[:len(legacy)] == legacy      # positional slices keep their meaning


def test_primary_metric_resolves_without_an_explicit_v2_import():
    """experiments/bms_star_toy.py hands ExperimentConfig().metrics to
    run_bms_star without importing metrics_v2; the lookup must register it."""
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    code = (
        "import numpy as np\n"
        "from bistar_gp.bms_star import GPPosteriorSample, compute_G_matrix, METRICS\n"
        "from bistar_gp.candidates import CandidateResult\n"
        "from bistar_gp.config import ExperimentConfig, PRIMARY_METRIC\n"
        "assert PRIMARY_METRIC not in METRICS\n"
        "gp = [GPPosteriorSample(mean=np.zeros(3), cov=np.eye(3), hyperparameters={})]\n"
        "c = [CandidateResult(name='a', mean=np.ones(3), cov=np.eye(3), noise_var=1.0, parameters={})]\n"
        "for m in ExperimentConfig().metrics:\n"
        "    G = compute_G_matrix(gp, c, m)\n"
        "    assert G.shape == (1, 1) and np.isfinite(G).all(), m\n"
        "assert PRIMARY_METRIC in METRICS\n"
        "print('ok')\n"
    )
    out = subprocess.run([sys.executable, "-c", code], cwd=repo, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip().endswith("ok")


def _gp(n_eval=4, k=3, seed=0):
    rng = np.random.default_rng(seed)
    return [GPPosteriorSample(mean=rng.normal(size=n_eval), cov=np.diag(np.full(n_eval, 0.1)),
                              hyperparameters={"draw": float(i)}) for i in range(k)]


def _cand(name, shift=0.0, n_eval=4):
    return CandidateResult(name=name, mean=np.full(n_eval, shift), cov=np.eye(n_eval) * 0.1,
                           noise_var=0.1, parameters={}, universe=None)


def _appendix_warnings(records):
    return [r for r in records if "appendix-only" in r.getMessage()]


def test_appendix_warning_fires_only_on_the_implicit_path(caplog):
    gp, cands = _gp(), [_cand("a"), _cand("b", shift=1.0)]
    taus = np.array([1.0])
    with caplog.at_level(logging.WARNING, logger="bistar_gp.bms_star"):
        out = run_bms_star(gp, cands, taus=taus)
    assert "kl_forward" in out and PRIMARY_METRIC in out
    warned = _appendix_warnings(caplog.records)
    assert len(warned) == 1 and "kl_forward" in warned[0].getMessage()
    assert PRIMARY_METRIC in warned[0].getMessage()

    caplog.clear()
    with caplog.at_level(logging.WARNING, logger="bistar_gp.bms_star"):
        run_bms_star(gp, cands, metric_names=["kl_forward"], taus=taus)
        run_bms_star(gp, cands, metric_names=[PRIMARY_METRIC], taus=taus)
        run_bms_star(gp, cands, metric_names=[PRIMARY_METRIC, "kl_forward"], taus=taus)
    assert _appendix_warnings(caplog.records) == []


def test_implicit_roster_announces_a_missing_primary_metric():
    """Kimi K3-1: in a process that never imported metrics_v2 the implicit
    roster lacks pw_kl_vcal; the roster is unchanged, the omission is logged."""
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    code = (
        "import logging, numpy as np\n"
        "logging.basicConfig(level=logging.WARNING)\n"
        "from bistar_gp.bms_star import GPPosteriorSample, run_bms_star, METRICS\n"
        "from bistar_gp.candidates import CandidateResult\n"
        "gp = [GPPosteriorSample(mean=np.zeros(3), cov=np.eye(3), hyperparameters={})]\n"
        "c = [CandidateResult(name='a', mean=np.ones(3), cov=np.eye(3), noise_var=1.0, parameters={}),"
        " CandidateResult(name='b', mean=np.zeros(3), cov=np.eye(3), noise_var=1.0, parameters={})]\n"
        "out = run_bms_star(gp, c, taus=np.array([1.0]))\n"
        "print('ROSTER', 'pw_kl_vcal' in out, len(out))\n"
    )
    res = subprocess.run([sys.executable, "-c", code], cwd=repo, capture_output=True, text=True)
    assert res.returncode == 0, res.stderr
    assert "ROSTER False 10" in res.stdout
    assert "primary metric pw_kl_vcal is not in the implicit roster" in res.stderr


def test_withdrawn_registry_contents():
    assert "runs/fit_method_metric_comparison/samples_hmc.npz" in WITHDRAWN_CACHES
    assert "runs/toy_tau_metric_comparison/" in WITHDRAWN_CACHES


def test_loader_refuses_withdrawn_caches_and_admits_under_flag(tmp_path):
    for entry in WITHDRAWN_CACHES:
        rel = entry + "samples.npz" if entry.endswith("/") else entry
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez(path, a=np.arange(3.0))
        assert is_withdrawn_cache(path) and is_withdrawn_cache(str(path))
        with pytest.raises(RuntimeError, match="M2bR"):
            load_hmc_samples(str(path))
        with pytest.warns(UserWarning, match="WITHDRAWN"):
            out = load_hmc_samples(str(path), allow_withdrawn=True)
        assert np.allclose(out["a"], np.arange(3.0))
    # a deeper file under the withdrawn prefix is refused too
    deep = tmp_path / "runs/toy_tau_metric_comparison/sub/x.npz"
    deep.parent.mkdir(parents=True, exist_ok=True)
    np.savez(deep, a=np.zeros(1))
    with pytest.raises(RuntimeError):
        load_hmc_samples(str(deep))


def test_loader_admits_other_caches_silently(tmp_path):
    ok = tmp_path / "runs/other_study/samples_hmc.npz"
    ok.parent.mkdir(parents=True, exist_ok=True)
    np.savez(ok, a=np.arange(2.0))
    assert not is_withdrawn_cache(ok)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        out = load_hmc_samples(str(ok))
    assert np.allclose(out["a"], np.arange(2.0))
