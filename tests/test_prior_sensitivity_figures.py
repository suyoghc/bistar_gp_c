"""
Regression tests for the toy_elicited_n20 registry graduation and the
prior-sensitivity figures stage (D18 ratification; see Notes/DECISIONS.md).

Gates:
1. the registry entry carries exactly the study's toy_elicited parameters,
   records provenance, and never enters the default experiment sweep;
2. pointing STUDY_CONFIGS["toy_elicited"] at the registry entry leaves the
   cache fingerprint unchanged, so the cached D18 draws stay valid;
3. the figures stage fails fast with the complete list of missing
   artifacts instead of regenerating anything (all 15 names pinned);
4. the figures stage builds both figures from existing artifacts alone —
   any fitting, sampling, or predictive-extraction call is an immediate
   failure — the assert-equal validation gate demonstrably ran, the output
   stems match the names the paper plan pins, and every non-auxiliary
   loaded value carries a pinned expectation (machine-local: needs runs/);
5. the validation gate fails in the negative direction (a perturbed pinned
   expectation raises), so silently weakening it is detectable;
6. hermetic loader/renderer coverage: a synthetic artifact set exercises
   load_figure_data, validate_figure_data, and both figure renderers on
   machines without the local runs/ artifacts.
"""

import json
import math
import os
import sys
from pathlib import Path

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from bistar_gp.config import PRIOR_CONFIGS, ExperimentConfig

EXPERIMENTS_DIR = str(Path(__file__).resolve().parents[1] / "experiments")


@pytest.fixture(scope="module")
def pss():
    if EXPERIMENTS_DIR not in sys.path:
        sys.path.insert(0, EXPERIMENTS_DIR)
    import prior_sensitivity_study as mod
    return mod


def test_registry_entry_params_exact_and_out_of_default_sweep():
    pc = PRIOR_CONFIGS["toy_elicited_n20"]
    assert pc.se_lengthscale_prior == ("lognormal", math.log(4.5), 0.9)
    assert pc.se_lengthscale_bounds == (0.1, 100.0)
    assert pc.se_outputscale_prior == ("lognormal", math.log(1.5), 1.0)
    assert pc.se_outputscale_bounds == (0.01, 100.0)
    assert pc.linear_variance_prior == ("lognormal", math.log(0.04), 1.5)
    assert pc.linear_variance_bounds == (1e-4, 10.0)
    assert pc.noise_prior == ("lognormal", math.log(0.3), 1.0)
    assert pc.noise_bounds == (1e-4, 10.0)
    # W4 constraint: the description records provenance and scope.
    assert "N=20" in pc.description
    assert "D18" in pc.description
    # Registry-only: the default sweep is unchanged and never includes it.
    sweep = ExperimentConfig().prior_configs
    assert "toy_elicited_n20" not in sweep
    assert sweep == ["informative", "vague", "misspecified_tight",
                     "low_noise", "high_noise"]


# The fingerprint the D18 sampler caches were stamped with. The registry
# swap must reproduce it exactly; a mismatch would silently invalidate the
# cached draws (run_method_fingerprinted deletes stale caches).
PINNED_FINGERPRINT = ("(('lognormal', 1.5040773967762742, 0.9), "
                      "('lognormal', 0.4054651081081644, 1.0), "
                      "('lognormal', -3.2188758248682006, 1.5), "
                      "('lognormal', -1.2039728043259361, 1.0))")


def test_study_swap_preserves_cache_fingerprint(pss):
    assert pss.STUDY_CONFIGS["toy_elicited"] is PRIOR_CONFIGS["toy_elicited_n20"]
    fp = pss._config_fingerprint(pss.STUDY_CONFIGS["toy_elicited"])
    assert fp == PINNED_FINGERPRINT
    # Cross-check against the on-disk sidecars where the local caches exist
    # (runs/ is machine-local, so absence is not a failure).
    for tag in ("hmc_td7", "hmc_td10", "vi_td7", "map_td7"):
        sidecar = os.path.join(
            pss.RUN_DIR, f"samples_toy_elicited_{tag}.npz.fingerprint")
        if os.path.exists(sidecar):
            with open(sidecar) as f:
                assert f.read().strip() == fp, sidecar


# The complete required-artifact list, pinned by basename so that dropping
# an entry from _figures_required_artifacts (which would trade the
# fail-fast preflight for a TypeError deep inside the loader) fails here.
REQUIRED_ARTIFACT_BASENAMES = sorted([
    "results_is_toy_elicited.json",
    "results_toy_elicited.json",
    "results_toy_elicited_uncapped.json",
    "stage_a_informative.json",
    "stage_a_toy_elicited.json",
    "results_noise_marginal_toy_elicited.json",
    "samples_toy_elicited_hmc_td7.npz",
    "samples_toy_elicited_hmc_td10.npz",
    "is_draws_informative_s0.npz",
    "is_draws_informative_s1.npz",
    "is_draws_informative_s2.npz",
    "is_draws_toy_elicited_s0.npz",
    "is_draws_toy_elicited_s1.npz",
    "is_draws_toy_elicited_s2.npz",
    "samples_hmc_td7.npz",   # the frozen D12 informative NUTS cache
])

FIGURE_BASENAMES = sorted([
    "toy_model_posterior_elicited.png", "toy_model_posterior_elicited.pdf",
    "prior_misspec_geometry.png", "prior_misspec_geometry.pdf",
])

# Data keys that are deliberately unpinned: raw draw/weight arrays feeding
# the histograms and rugs, aux metadata validated structurally, and the
# per-metric fraction table used for the denominator proof.
UNPINNED_AUX_KEYS = {
    "model_names", "taus",
    "informative_noise_draws", "informative_is_weights",
    "toy_elicited_noise_draws", "toy_elicited_is_weights",
    "informative_nuts_noise_draws", "toy_elicited_nuts_noise_draws_td7",
    "sir_hard_win_fractions_by_metric",
}

# Sampling / fitting / predictive-extraction entry points reachable from
# the module namespace; the figures stage must call none of them. `fresh`
# is the choke point every GP construction in the module flows through.
FORBIDDEN_PSS_NAMES = (
    "fit_map", "fit_vi", "map_fitted", "prior_is_run",
    "run_method_fingerprinted", "_sir_bms", "mh_noise_occupancy",
    "profile_laplace_noise_marginal", "fresh", "build_model",
    "extract_gp_predictives", "run_bms_star",
)
FORBIDDEN_FMC_NAMES = ("run_one_method", "fit_gp", "fit_map")


def _forbid_sampling(pss, monkeypatch):
    def _forbidden(*args, **kwargs):
        raise AssertionError("the figures stage must not fit or sample")
    for name in FORBIDDEN_PSS_NAMES:
        monkeypatch.setattr(pss, name, _forbidden)
    for name in FORBIDDEN_FMC_NAMES:
        monkeypatch.setattr(pss.fmc, name, _forbidden)


def test_figures_preflight_lists_missing_artifacts(pss, tmp_path, monkeypatch):
    monkeypatch.setattr(pss, "RUN_DIR", str(tmp_path))
    monkeypatch.setattr(pss, "D12_INFORMATIVE_HMC_TD7",
                        str(tmp_path / "d12" / "samples_hmc_td7.npz"))
    required = pss._figures_required_artifacts()
    assert sorted(os.path.basename(p) for p in required) \
        == REQUIRED_ARTIFACT_BASENAMES
    with pytest.raises(FileNotFoundError) as exc:
        pss.figures_preflight()
    msg = str(exc.value)
    assert "never samples" in msg
    for base in REQUIRED_ARTIFACT_BASENAMES:
        assert base in msg


def test_figures_stage_builds_without_fitting_or_sampling(
        pss, tmp_path, monkeypatch, capsys):
    missing = [p for p in pss._figures_required_artifacts()
               if not os.path.exists(p)]
    if missing:
        pytest.skip("local study artifacts absent (runs/ is machine-local)")
    _forbid_sampling(pss, monkeypatch)

    # build_figures runs the full chain: preflight, load, assert-equal
    # validation against FIGURE_EXPECTATIONS (rtol=0, atol=1e-12), plot.
    paths = pss.build_figures(out_dir=str(tmp_path))
    out = capsys.readouterr().out
    assert (f"validated {len(pss.FIGURE_EXPECTATIONS)} pinned figure "
            f"values") in out
    assert sorted(os.path.basename(p) for p in paths) == FIGURE_BASENAMES
    for p in paths:
        assert os.path.exists(p)
        assert os.path.getsize(p) > 0
    # Completeness invariant: every loaded value outside the declared aux
    # set must carry a pinned expectation, so a newly plotted headline
    # value cannot ship unvalidated.
    data = pss.load_figure_data()
    assert set(data) - UNPINNED_AUX_KEYS == set(pss.FIGURE_EXPECTATIONS)


TAUS = ["0.1", "0.3", "1.0", "3.0", "10.0"]
MODEL_NAMES = ["Linear", "Sinusoidal", "Sin+Linear", "Quadratic"]


def _write_json(path, payload):
    with open(path, "w") as f:
        json.dump(payload, f)


def _build_synthetic_artifacts(pss, run_dir, d12_path):
    """Fabricate a minimal, internally consistent artifact set exercising
    the exact schema load_figure_data reads, and return the expectations
    dict that validate_figure_data must accept for it."""
    os.makedirs(run_dir, exist_ok=True)
    os.makedirs(os.path.dirname(d12_path), exist_ok=True)

    post = {t: [0.2, 0.2, 0.4, 0.2] for t in TAUS}
    _write_json(os.path.join(run_dir, "results_is_toy_elicited.json"), {
        "model_names": MODEL_NAMES,
        "n_sir_draws": 10,
        "n_unique_sir_draws": 9,
        "metrics": {"pw_kl_vcal": {
            "posteriors": post,
            "hard_win_fractions": [0.1, 0.2, 0.6, 0.1],
        }},
        "bootstrap_tau1": {"pw_kl_vcal": {"se": [0.01, 0.01, 0.02, 0.01]}},
        "per_is_seed_pw_kl_vcal_tau1": {s: [0.2, 0.2, 0.4, 0.2]
                                        for s in ("0", "1", "2")},
    })
    for fname, n_draws, n_pred in (
            ("results_toy_elicited.json", 8, 4),
            ("results_toy_elicited_uncapped.json", 8, 4)):
        _write_json(os.path.join(run_dir, fname), {
            "methods": {"hmc": {
                "metrics": {"pw_kl_vcal": {
                    "posteriors": {t: [0.1, 0.1, 0.7, 0.1] for t in TAUS}}},
                "n_draws": n_draws,
                "n_predictives": n_pred,
            }},
        })
    _write_json(os.path.join(run_dir,
                             "results_noise_marginal_toy_elicited.json"), {
        "rw_mh": [{"seed": s, "P_noise_lo": 0.8, "P_noise_mid": 0.15,
                   "P_noise_hi": 0.05, "lo_hi_crossings": 4}
                  for s in (42, 1, 2)],
        "profile_laplace": {"band_masses": {"P_noise_lo": 0.76,
                                            "P_noise_mid": 0.19,
                                            "P_noise_hi": 0.05}},
    })
    stage_a = {
        "informative": {
            "modes": [
                {"values": {"noise": 0.07}, "verified_local_max": True},
                {"values": {"noise": 0.60}, "verified_local_max": True},
            ],
            "valleys": [{"between": [0, 1],
                         "depth_below_lower_mode": 6.0}],
            "vi_seed_means": {s: {"noise": 0.55}
                              for s in ("0", "1", "2", "42")},
            "map": {"values": {"noise": 0.07}},
        },
        "toy_elicited": {
            "modes": [
                {"values": {"noise": 0.06}, "verified_local_max": True},
            ],
            "valleys": [],
            "vi_seed_means": {s: {"noise": 0.46}
                              for s in ("0", "1", "2", "42")},
            "map": {"values": {"noise": 0.06}},
        },
    }
    for cfg, rec in stage_a.items():
        _write_json(os.path.join(run_dir, f"stage_a_{cfg}.json"), rec)

    rng = np.random.default_rng(0)
    masses, mass_ses = {}, {}
    for cfg in ("informative", "toy_elicited"):
        pooled_ths, pooled_lml = [], []
        for seed in (0, 1, 2):
            ths = np.column_stack([
                rng.uniform(0.5, 2.0, 60),          # ls
                rng.uniform(0.5, 2.0, 60),          # os
                rng.uniform(0.01, 0.1, 60),         # lv
                rng.uniform(0.01, 1.0, 60),         # noise
            ])
            lml = np.zeros(60)
            np.savez(os.path.join(run_dir, f"is_draws_{cfg}_s{seed}.npz"),
                     ths=ths, lml=lml, seed=seed)
            pooled_ths.append(ths)
            pooled_lml.append(lml)
        summ = pss._is_summary(np.vstack(pooled_ths),
                               np.concatenate(pooled_lml))
        masses[cfg] = [summ["P_noise_lo"], summ["P_noise_mid"],
                       summ["P_noise_hi"]]
        mass_ses[cfg] = [summ["P_noise_lo_se"], summ["P_noise_mid_se"],
                         summ["P_noise_hi_se"]]

    nuts = np.full(8, 0.05)
    for path in (os.path.join(run_dir, "samples_toy_elicited_hmc_td7.npz"),
                 os.path.join(run_dir, "samples_toy_elicited_hmc_td10.npz"),
                 d12_path):
        np.savez(path, **{"likelihood.noise_covar.noise_prior": nuts})

    return {
        "sir_tau1": [0.2, 0.2, 0.4, 0.2],
        "sir_se_tau1": [0.01, 0.01, 0.02, 0.01],
        "sir_per_seed_sl_tau1": [0.4, 0.4, 0.4],
        "hmc_td7_tau1": [0.1, 0.1, 0.7, 0.1],
        "hmc_td10_sl_tau1": 0.7,
        "sir_posteriors_by_tau": [[0.2, 0.2, 0.4, 0.2]] * 5,
        "hmc_td7_posteriors_by_tau": [[0.1, 0.1, 0.7, 0.1]] * 5,
        "sir_hard_win_fractions": [0.1, 0.2, 0.6, 0.1],
        "n_sir_draws": 10,
        "n_unique_sir_draws": 9,
        "hmc_td7_n_draws": 8,
        "hmc_td7_n_predictives": 4,
        "hmc_td10_n_draws": 8,
        "hmc_td10_n_predictives": 4,
        "informative_band_masses": masses["informative"],
        "informative_band_mass_ses": mass_ses["informative"],
        "toy_elicited_band_masses": masses["toy_elicited"],
        "toy_elicited_band_mass_ses": mass_ses["toy_elicited"],
        "informative_mode_noise_coords": [0.07, 0.60],
        "informative_valley_depth_nats": 6.0,
        "toy_elicited_mode_noise_coords": [0.06],
        "informative_vi_noise_landings": [0.55] * 4,
        "informative_map_noise": 0.07,
        "toy_elicited_vi_noise_landings": [0.46] * 4,
        "toy_elicited_map_noise": 0.06,
        "informative_nuts_occupancy_td7": [1.0, 0.0, 0.0],
        "toy_elicited_nuts_occupancy_td7": [1.0, 0.0, 0.0],
        "toy_elicited_nuts_occupancy_td10": [1.0, 0.0, 0.0],
        "informative_nuts_n_draws": 8,
        "toy_elicited_nuts_n_draws_td7": 8,
        "toy_elicited_nuts_n_draws_td10": 8,
        "rwmh_lo_by_seed": [0.8, 0.8, 0.8],
        "rwmh_lo_hi_crossings": [4, 4, 4],
        "profile_laplace_lo": 0.76,
    }


@pytest.fixture()
def synthetic_figures(pss, tmp_path, monkeypatch):
    run_dir = str(tmp_path / "run")
    d12_path = str(tmp_path / "d12" / "samples_hmc_td7.npz")
    monkeypatch.setattr(pss, "RUN_DIR", run_dir)
    monkeypatch.setattr(pss, "D12_INFORMATIVE_HMC_TD7", d12_path)
    _forbid_sampling(pss, monkeypatch)
    expectations = _build_synthetic_artifacts(pss, run_dir, d12_path)
    return expectations, str(tmp_path / "out")


def test_hermetic_loader_and_renderers(pss, synthetic_figures):
    expectations, out_dir = synthetic_figures
    # The synthetic expectations must mirror the real pinned key set, so a
    # new pinned key cannot ship without hermetic coverage.
    assert set(expectations) == set(pss.FIGURE_EXPECTATIONS)
    data = pss.load_figure_data()
    assert set(data) - UNPINNED_AUX_KEYS == set(pss.FIGURE_EXPECTATIONS)
    pss.validate_figure_data(data, expectations)
    os.makedirs(out_dir, exist_ok=True)
    paths = pss.figure_a(data, out_dir) + pss.figure_b(data, out_dir)
    assert sorted(os.path.basename(p) for p in paths) == FIGURE_BASENAMES
    for p in paths:
        assert os.path.getsize(p) > 0


def test_validation_gate_fails_on_drifted_value(pss, synthetic_figures):
    expectations, _ = synthetic_figures
    data = pss.load_figure_data()
    drifted = dict(expectations)
    drifted["hmc_td10_sl_tau1"] = expectations["hmc_td10_sl_tau1"] + 1e-9
    with pytest.raises(AssertionError, match="hmc_td10_sl_tau1"):
        pss.validate_figure_data(data, drifted)


def test_validation_gate_fails_on_rank_instability(pss, synthetic_figures):
    expectations, _ = synthetic_figures
    data = pss.load_figure_data()
    # A competitor overtaking Sin+Linear at one tau must trip the
    # rank-stability check even when that row is pinned to match.
    flipped = [0.5, 0.2, 0.1, 0.2]
    data["sir_posteriors_by_tau"] = \
        data["sir_posteriors_by_tau"][:4] + [flipped]
    drifted = dict(expectations)
    drifted["sir_posteriors_by_tau"] = \
        expectations["sir_posteriors_by_tau"][:4] + [flipped]
    with pytest.raises(AssertionError, match="not Sin\\+Linear"):
        pss.validate_figure_data(data, drifted)
