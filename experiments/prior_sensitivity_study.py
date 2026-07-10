"""
Prior-sensitivity / re-elicitation study for the D12 bimodality (W2 gate).

D12 found the `informative` GP hyperprior makes the thesis-toy hyperparameter
posterior bimodal: HMC/MAP report the low-noise density-mode basin (selects
the true Sin+Linear model), VI converges to the mass-dominant high-noise basin
(selects Sinusoidal), and truth-ish hyperparameters score far below the MAP
(log joint -57.2 vs -33.4). The suspected cause is scale mismatch: all three
kernel parameters carry Gamma(6, 0.85) priors (mean 7.1, density ~x^5 near 0)
while the toy's true scales are lengthscale ~1.5, outputscale ~0.5 and linear
variance ~0.0625 = slope^2 — log-prior penalties of roughly -3, -8 and -18
nats against the prior's own peak. This study asks whether reasonable
re-elicited priors dissolve the bimodality and stabilize the BI*/BMS* result.

Configs (gamma_relaxed defined here; toy_elicited graduated to the registry
as PRIOR_CONFIGS["toy_elicited_n20"] after the 2026-07-09 scope-tightened
ratification, D18 Status — registry-only, still NOT the package default):
  informative    D12 baseline; stage B numbers come from the existing capped
                 run (runs/fit_method_metric_comparison/results_td7.json).
  vague          the pre-registered broad-LogNormal config in PRIOR_CONFIGS.
  toy_elicited   re-elicited from observable data statistics only (x-range,
                 x-spacing, var(y), mean(x^2)) — no truth values used.
  gamma_relaxed  minimal-change attribution arm: same Gamma family, same noise
                 prior, kernel priors relaxed Gamma(6,0.85) -> Gamma(2,0.5).

PRE-REGISTRATION (2026-07-08, fixed before any stage-B result was read; the
preflight review demanded these rules be committed in advance):
  Roles: toy_elicited is the CANDIDATE REPLACEMENT prior; vague is the
  robustness pole; gamma_relaxed is an ATTRIBUTION arm only and is never
  adopted for paper numbers regardless of its results.
  Coherence criteria (per config): (i) no verified mode pair separated by a
  >1-nat valley, OR every secondary verified mode holds < 5% of pooled
  prior-IS mass; (ii) MAP, HMC draws and prior-IS mass agree on the dominant
  basin; (iii) stage-B VI vs HMC max abs model-posterior difference at tau=1
  under pw_kl_vcal <= 0.10.
  Adoption is WINNER-BLIND: if toy_elicited is coherent it is recommended for
  final toy numbers whatever model it selects; the informative config is then
  reported as the documented prior-misspecification / bimodality case study.
  Outcome patterns: (A) alternates coherent, same winner, VI/HMC agree ->
  adopt toy_elicited, keep informative as the case study. (B) toy_elicited
  coherent but winner differs from Sin+Linear -> still adopt (winner-blind)
  and reframe the toy result accordingly. (C) toy_elicited incoherent ->
  keep informative and frame the toy as a prior-sensitivity example. (D) all
  alternates incoherent (incl. vague) -> geometry is data-intrinsic (N=20);
  small-N framing, prior-sensitivity example. (E) winner varies across
  coherent alternates -> prior-sensitivity example framing.
  Validity floors: the mass-faithful SIR row is reported only if pooled IS
  ESS >= 100 (else flagged); if the adopted config's HMC chain shows
  pathology (any site ESS < 5, or draw occupancy contradicting the prior-IS
  mass by more than 2 SE), spot-check that one config uncapped before
  adoption. The tree-depth cap (7) is inherited from D8/D12 validation on the
  informative geometry and is disclosed as such.

Staged cheap-to-expensive pipeline (W2: MAP/mode checks first, basin occupancy,
HMC only where justified):
  stage a   per config: prior scorecard at truth-ish values, MAP, VI across
            seeds, multi-seed prior importance sampling for basin mass with
            SEs and per-basin ESS (the D13 mass authority), then a wide-start
            Nelder-Mead mode hunt (MAP / VI landings / prior medians /
            truth-ish / fixed D12 basin probes / prior draws / top-weight IS
            draws stratified by noise) with valley checks between verified
            modes and per-mode pooled-IS mass.
  stage b   per config: capped-depth NUTS (max_tree_depth=7), VI and MAP
            through the full BMS* pipeline (reuses
            fit_method_metric_comparison.run_one_method) plus basin occupancy
            of the draws. Sampler caches carry a prior fingerprint sidecar so
            a config edit can never silently reuse stale draws.
  stage is  per config: mass-faithful model selection — SIR-resample
            hyperparameters from the pooled stage-A prior-IS draws and push
            them through the same BMS* pipeline. No sampler cost; includes
            the informative config (the number D12's honest framing lacked).
  stage report  assembles docs/prior-sensitivity-study.md from the JSONs.
  stage figures  Figures A (toy_model_posterior_elicited) and B
            (prior_misspec_geometry) of the W4 plan, built ONLY from the
            existing artifacts above (zero new sampling); every plotted
            headline value is asserted equal to a pinned expectation
            before plotting. Outputs under runs/prior_sensitivity/figures/.

Artifacts under runs/prior_sensitivity/ (local by convention).

Usage:
    python experiments/prior_sensitivity_study.py --stage a [--configs ...]
        [--is-n N] [--is-seeds 0 1 2] [--smoke]
    python experiments/prior_sensitivity_study.py --stage b --configs vague
        [--methods hmc vi map]
    python experiments/prior_sensitivity_study.py --stage is [--configs ...]
    python experiments/prior_sensitivity_study.py --stage report
    python experiments/prior_sensitivity_study.py --stage figures
"""

import sys, os, json, math, argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import torch
import gpytorch
from scipy import stats
from scipy.optimize import minimize

from bistar_gp import generate_toy_data, build_model
from bistar_gp.candidates import build_toy_candidates
from bistar_gp.config import (PRIOR_CONFIGS, PriorConfig,
                              build_kernels_from_config,
                              build_likelihood_from_config)
from bistar_gp.fit import fit_map, fit_vi, _mh_log_joint
from bistar_gp.model import apply_hp_value
from bistar_gp.bms_star import extract_gp_predictives, run_bms_star

import fit_method_metric_comparison as fmc

torch.set_default_dtype(torch.float64)

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RUN_DIR = os.path.join(REPO_ROOT, "runs", "prior_sensitivity")
DOC_PATH = os.path.join(REPO_ROOT, "docs", "prior-sensitivity-study.md")
D12_TD7_JSON = os.path.join(REPO_ROOT, "runs", "fit_method_metric_comparison",
                            "results_td7.json")
D12_TD7_SAMPLES = os.path.join(REPO_ROOT, "runs", "fit_method_metric_comparison",
                               "samples_{method}_td7.npz")

SEED = 42
NOISE_SPLIT_LO = 0.15   # D12 basin boundary (noise variance), kept for comparability
NOISE_SPLIT_HI = 0.30
TRUTHISH = {"ls": 1.5, "os": 0.5, "lv": 0.0625, "noise": 0.25}  # noise = 0.5^2

# Fixed cross-config probe starts at the D12 informative mode locations: all
# configs share the same likelihood surface, so these are legitimate probes of
# both D12 basins even though each config's own modes may relocate.
D12_PROBES = {
    "d12_low_probe": {"ls": 2.1794, "os": 3.7594, "lv": 5.3006, "noise": 0.0736},
    "d12_high_probe": {"ls": 8.4306, "os": 4.4388, "lv": 5.3014, "noise": 0.5917},
}

SHORT = {"covar_module.kernels.0.base_kernel.lengthscale_prior": "ls",
         "covar_module.kernels.0.outputscale_prior": "os",
         "covar_module.kernels.1.variance_prior": "lv",
         "likelihood.noise_covar.noise_prior": "noise"}
LONG = {v: k for k, v in SHORT.items()}
ORDER = ["ls", "os", "lv", "noise"]
SITE_SPECS = {"ls": "se_lengthscale_prior", "os": "se_outputscale_prior",
              "lv": "linear_variance_prior", "noise": "noise_prior"}


# ── Study configs ──────────────────────────────────────────────────

STUDY_CONFIGS = {
    "informative": PRIOR_CONFIGS["informative"],
    "vague": PRIOR_CONFIGS["vague"],
    # Graduated to the registry as `toy_elicited_n20` after the 2026-07-09
    # scope-tightened ratification (D18 Status). Parameters are identical to
    # the original in-script definition, so the cache fingerprint (which
    # covers only the four prior parameter tuples) is unchanged and the
    # cached draws stay valid; artifact filenames key off THIS dict key,
    # which stays `toy_elicited`. Nothing keys off PriorConfig.name.
    "toy_elicited": PRIOR_CONFIGS["toy_elicited_n20"],
    "gamma_relaxed": PriorConfig(
        name="gamma_relaxed",
        description=(
            "Minimal-change attribution arm: keeps the informative config's "
            "Gamma family and its noise prior Gamma(1.75, 1.0) untouched, "
            "but relaxes the three kernel priors from Gamma(6, 0.85) "
            "(mean 7.1, density ~x^5 near 0 — excludes the toy's sub-unit "
            "amplitudes) to Gamma(2, 0.5) (mean 4, sd 2.8, density ~x near "
            "0). Isolates whether the shape-6 small-value exclusion in the "
            "kernel priors drives the bimodality. Attribution only — never "
            "a candidate for final paper numbers."
        ),
        se_lengthscale_prior=("gamma", 2.0, 0.5),
        se_lengthscale_bounds=(0.5, 30.0),
        se_outputscale_prior=("gamma", 2.0, 0.5),
        se_outputscale_bounds=(0.1, 20.0),
        linear_variance_prior=("gamma", 2.0, 0.5),
        linear_variance_bounds=(0.01, 20.0),
        noise_prior=("gamma", 1.75, 1.0),
        noise_bounds=(1e-4, 10.0),
    ),
}


def _config_fingerprint(pc):
    return repr((pc.se_lengthscale_prior, pc.se_outputscale_prior,
                 pc.linear_variance_prior, pc.noise_prior))


def _j(v):
    """JSON-safe float: -inf/inf/nan become None (strict-JSON artifacts)."""
    v = float(v)
    return v if math.isfinite(v) else None


# ── Prior density helpers (numpy/scipy side, mirrors config families) ──

def _prior_dist(spec):
    fam, p1, p2 = spec
    if fam == "gamma":
        return stats.gamma(a=p1, scale=1.0 / p2)
    if fam == "lognormal":
        return stats.lognorm(s=p2, scale=math.exp(p1))
    raise ValueError(f"Unknown prior family: {fam}")


def _prior_rvs(spec, n, rng):
    fam, p1, p2 = spec
    if fam == "gamma":
        return rng.gamma(p1, 1.0 / p2, n)
    if fam == "lognormal":
        return rng.lognormal(p1, p2, n)
    raise ValueError(f"Unknown prior family: {fam}")


# ── Exact log-joint machinery (generalized from toy_posterior_mode_analysis) ──

def fresh(pc, x, y):
    k, n = build_kernels_from_config(pc)
    lik = build_likelihood_from_config(pc)
    return build_model(x, y, k, n, lik)


def map_fitted(pc, x, y, n_iter=300):
    m, l = fresh(pc, x, y)
    torch.manual_seed(SEED)
    fit_map(m, l, x, y, n_iter=n_iter, lr=0.05, verbose=False)
    return m, l


def log_joint(pc, x, y, vals):
    m, l = fresh(pc, x, y)
    for k, v in vals.items():
        apply_hp_value(m, l, LONG[k], float(v))
    mll = gpytorch.mlls.ExactMarginalLogLikelihood(l, m)
    try:
        return _mh_log_joint(mll, m, l, x, y)
    except Exception:
        return -np.inf


def decompose(pc, x, y, vals):
    """(summed log marginal likelihood, log prior) at constrained values.
    gpytorch adds priors as constrained-space densities (no Jacobian) — the
    subtraction recovers the summed prior log density (verified to 1e-12 in
    the D12/D13 codex adjudication)."""
    total = log_joint(pc, x, y, vals)
    m, l = fresh(pc, x, y)
    for k, v in vals.items():
        apply_hp_value(m, l, LONG[k], float(v))
    with torch.no_grad(), gpytorch.settings.cholesky_jitter(1e-4):
        pred = l(m(x))
        log_ml = gpytorch.distributions.MultivariateNormal(
            pred.mean, pred.covariance_matrix).log_prob(y).item()
    return log_ml, total - log_ml


def model_values(m, l):
    return {"ls": float(m.covar_module.kernels[0].base_kernel.lengthscale.detach()),
            "os": float(m.covar_module.kernels[0].outputscale.detach()),
            "lv": float(m.covar_module.kernels[1].variance.detach()),
            "noise": float(l.noise.detach())}


# ── Stage A pieces ─────────────────────────────────────────────────

def prior_scorecard(pc):
    """Per-site prior log density at the truth-ish point, plus prior median
    and 90% interval — the 'which hyperparameters fight the toy scale'
    attribution, prior-only (no data)."""
    card = {}
    for site in ORDER:
        d = _prior_dist(getattr(pc, SITE_SPECS[site]))
        card[site] = {
            "logpdf_at_truthish": float(d.logpdf(TRUTHISH[site])),
            "logpdf_at_prior_median": float(d.logpdf(d.ppf(0.5))),
            "median": float(d.ppf(0.5)),
            "q05": float(d.ppf(0.05)), "q95": float(d.ppf(0.95)),
        }
    card["total_logpdf_at_truthish"] = float(
        sum(card[s]["logpdf_at_truthish"] for s in ORDER))
    return card


def nm_polish(pc, x, y, start_vals, maxiter=4000):
    """Nelder-Mead on the exact log joint in log space; returns (vals, lj)."""
    f = lambda logv: -log_joint(pc, x, y, dict(zip(ORDER, np.exp(logv))))
    x0 = np.log([max(start_vals[k], 1e-8) for k in ORDER])
    r = minimize(f, x0, method="Nelder-Mead",
                 options={"xatol": 1e-8, "fatol": 1e-10, "maxiter": maxiter})
    vals = dict(zip(ORDER, np.exp(r.x)))
    return vals, -float(r.fun)


def is_local_max(pc, x, y, vals, lj, eps=0.05, n_random_dirs=8):
    """Perturbation check in log space: axis-aligned exp(+-eps) moves plus
    n_random_dirs random unit directions (axis-only checks pass on diagonal
    ridges; random directions catch correlated ascent, e.g. the
    lengthscale-outputscale trade). Tolerance for NM's finite convergence."""
    logv = np.log([vals[k] for k in ORDER])
    dirs = []
    for i in range(len(ORDER)):
        e = np.zeros(len(ORDER)); e[i] = 1.0
        dirs += [e, -e]
    rng = np.random.default_rng(0)
    for _ in range(n_random_dirs):
        d = rng.normal(size=len(ORDER))
        dirs.append(d / np.linalg.norm(d))
    for d in dirs:
        v = dict(zip(ORDER, np.exp(logv + eps * d)))
        if log_joint(pc, x, y, v) > lj + 1e-6:
            return False
    return True


def dedup_modes(cands, tol=0.15):
    """Merge candidate modes whose log-hyperparameters all agree within tol;
    keep the highest-log-joint representative. Returns list sorted by lj."""
    kept = []
    for vals, lj in sorted(cands, key=lambda c: -c[1]):
        if not np.isfinite(lj):
            continue
        dup = any(max(abs(math.log(vals[k]) - math.log(kv[k]))
                      for k in ORDER) < tol for kv, _ in kept)
        if not dup:
            kept.append((vals, lj))
    return kept


def valley_between(pc, x, y, a, b, n=41):
    """Min log joint along the straight log-space segment. This LOWER-bounds
    the true saddle, so the reported depth UPPER-bounds the true barrier —
    decisive depths (D12: ~6 nats) are safe; verdicts resting on depths in
    the 1-3 nat band are flagged near_threshold and need path refinement."""
    lo = np.log([a[k] for k in ORDER])
    hi = np.log([b[k] for k in ORDER])
    return min(log_joint(pc, x, y, dict(zip(ORDER, np.exp(lo + t * (hi - lo)))))
               for t in np.linspace(0, 1, n))


def _is_draw_path(name, seed, smoke=False):
    tag = "_smoke" if smoke else ""
    return os.path.join(RUN_DIR, f"is_draws_{name}{tag}_s{seed}.npz")


def prior_is_run(pc, name, x, y, n_draws, seed, smoke=False):
    """One prior-IS pass: sample the config's own priors, score the exact
    log ML per draw, persist (draws, log-ML) for pooling / SIR reuse."""
    rng = np.random.default_rng(seed)
    ths = np.column_stack([_prior_rvs(getattr(pc, SITE_SPECS[s]), n_draws, rng)
                           for s in ORDER])
    m, l = fresh(pc, x, y)
    lml = np.empty(n_draws)
    for i, th in enumerate(ths):
        for k, v in zip(ORDER, th):
            apply_hp_value(m, l, LONG[k], float(v))
        with torch.no_grad(), gpytorch.settings.cholesky_jitter(1e-4):
            try:
                pred = l(m(x))
                lml[i] = gpytorch.distributions.MultivariateNormal(
                    pred.mean, pred.covariance_matrix).log_prob(y).item()
            except Exception:
                lml[i] = -np.inf
        m.train(); l.train()
    np.savez(_is_draw_path(name, seed, smoke), ths=ths, lml=lml, seed=seed)
    return ths, lml


def _is_summary(ths, lml):
    """P(basin) with delta-method SEs, per-basin ESS, P_mid, IS posterior
    means. P(A) = E_prior[ML*1_A] / E_prior[ML]; SE via
    sqrt(sum w^2 (1_A - P)^2) / sum w (self-normalized-ratio delta method)."""
    w = np.exp(lml - lml.max())
    tot = w.sum()
    noise = ths[:, ORDER.index("noise")]
    out = {"ess": float(tot ** 2 / (w ** 2).sum())}
    for key, mask in [("P_noise_lo", noise < NOISE_SPLIT_LO),
                      ("P_noise_mid", (noise >= NOISE_SPLIT_LO)
                                      & (noise <= NOISE_SPLIT_HI)),
                      ("P_noise_hi", noise > NOISE_SPLIT_HI)]:
        p = float(w[mask].sum() / tot)
        se = float(np.sqrt(np.sum((w / tot) ** 2 * (mask - p) ** 2)))
        wm = w[mask]
        ess_m = float(wm.sum() ** 2 / (wm ** 2).sum()) if wm.sum() > 0 else 0.0
        out[key] = p
        out[key + "_se"] = se
        out[key + "_ess"] = ess_m
    out["posterior_mean"] = {s: float((w * ths[:, j]).sum() / tot)
                             for j, s in enumerate(ORDER)}
    return out


def load_pooled_is(name, seeds, smoke=False):
    ths, lml = [], []
    for seed in seeds:
        path = _is_draw_path(name, seed, smoke)
        if not os.path.exists(path):
            raise FileNotFoundError(f"missing IS draws {path}; run stage a")
        with np.load(path) as z:
            ths.append(z["ths"]); lml.append(z["lml"])
    return np.vstack(ths), np.concatenate(lml)


def per_mode_mass(modes, ths, lml):
    """Assign each pooled IS draw to its nearest mode in log space (L2 over
    the 4 log-hyperparameters); weight-sum. A geometry-adaptive mass measure
    that stays meaningful when a config's modes relocate off the fixed
    0.15/0.30 noise split."""
    if not modes:
        return []
    w = np.exp(lml - lml.max())
    logth = np.log(np.maximum(ths, 1e-300))
    centers = np.array([[math.log(vals[k]) for k in ORDER]
                        for vals, _ in modes])
    d2 = ((logth[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
    nearest = d2.argmin(axis=1)
    tot = w.sum()
    return [float(w[nearest == j].sum() / tot) for j in range(len(modes))]


def stage_a_one(name, pc, x, y, is_n, is_seeds, smoke=False):
    print(f"\n{'=' * 60}\n  stage A: config = {name}\n{'=' * 60}")
    out = {"config": name, "description": pc.description,
           "prior_fingerprint": _config_fingerprint(pc),
           "is_n_per_seed": is_n, "is_seeds": list(is_seeds)}
    vi_steps = 600 if smoke else 5000
    nm_maxiter = 600 if smoke else 4000
    n_prior_starts = 4 if smoke else 12
    vi_seeds = (0, 42) if smoke else (0, 1, 2, 42)

    print("── prior scorecard at truth-ish (ls 1.5, os 0.5, lv 0.0625, "
          "noise 0.25) ──")
    out["prior_scorecard"] = prior_scorecard(pc)
    for s in ORDER:
        c = out["prior_scorecard"][s]
        print(f"  {s:<6} median={c['median']:.3f} 90%=[{c['q05']:.4f}, "
              f"{c['q95']:.3f}]  logpdf(truth)={c['logpdf_at_truthish']:.2f} "
              f"(vs {c['logpdf_at_prior_median']:.2f} at its median)")
    print(f"  total log prior at truth-ish: "
          f"{out['prior_scorecard']['total_logpdf_at_truthish']:.2f}")

    m, l = map_fitted(pc, x, y)
    map_vals = model_values(m, l)
    out["map"] = {"values": map_vals,
                  "log_joint": _j(log_joint(pc, x, y, map_vals))}

    print(f"── VI across seeds ({vi_steps} steps, MAP init; stage-B VI uses "
          f"seed 42) ──")
    vi_runs = {}
    for seed in vi_seeds:
        mv, lv_ = map_fitted(pc, x, y)
        s = fit_vi(mv, lv_, x, y, n_samples=500, n_steps=vi_steps,
                   verbose=False, seed=seed)
        means = {SHORT[k]: float(v.mean()) for k, v in s.items()}
        vi_runs[seed] = means
        print(f"  seed={seed}: " + "  ".join(f"{k}={means[k]:.3f}"
                                             for k in ORDER))
    out["vi_seed_means"] = {str(k): v for k, v in vi_runs.items()}

    print(f"── posterior mass by prior importance sampling "
          f"({len(is_seeds)} seeds x N={is_n}) ──")
    per_seed = {}
    for seed in is_seeds:
        ths_s, lml_s = prior_is_run(pc, name, x, y, is_n, seed, smoke)
        per_seed[str(seed)] = _is_summary(ths_s, lml_s)
        ps = per_seed[str(seed)]
        print(f"  seed={seed}: P_lo={ps['P_noise_lo']:.3f}"
              f"±{ps['P_noise_lo_se']:.3f} P_mid={ps['P_noise_mid']:.3f} "
              f"P_hi={ps['P_noise_hi']:.3f}±{ps['P_noise_hi_se']:.3f}  "
              f"ESS={ps['ess']:.0f} (lo {ps['P_noise_lo_ess']:.0f} / "
              f"hi {ps['P_noise_hi_ess']:.0f})")
    ths, lml = load_pooled_is(name, is_seeds, smoke)
    pooled = _is_summary(ths, lml)
    out["prior_is"] = {"per_seed": per_seed, "pooled": pooled}
    print(f"  pooled: P_lo={pooled['P_noise_lo']:.3f}"
          f"±{pooled['P_noise_lo_se']:.3f} P_mid={pooled['P_noise_mid']:.3f} "
          f"P_hi={pooled['P_noise_hi']:.3f}±{pooled['P_noise_hi_se']:.3f}  "
          f"ESS={pooled['ess']:.0f} (lo {pooled['P_noise_lo_ess']:.0f} / "
          f"hi {pooled['P_noise_hi_ess']:.0f})")

    print("── mode hunt (Nelder-Mead on the exact log joint, wide starts) ──")
    prior_median_start = {s: out["prior_scorecard"][s]["median"] for s in ORDER}
    starts = {"map": map_vals,
              **{f"vi_s{seed}": v for seed, v in vi_runs.items()},
              "prior_median": prior_median_start,
              "truthish": dict(TRUTHISH),
              **D12_PROBES}
    rng = np.random.default_rng(123)
    for i in range(n_prior_starts):
        starts[f"prior_draw_{i}"] = {
            s: float(_prior_rvs(getattr(pc, SITE_SPECS[s]), 1, rng)[0])
            for s in ORDER}
    # Top-weight IS draws per noise stratum: the IS pass already located the
    # high-posterior regions; feed them back as starts instead of discarding.
    w = np.exp(lml - lml.max())
    noise_col = ths[:, ORDER.index("noise")]
    for label, mask in [("lo", noise_col < NOISE_SPLIT_LO),
                        ("mid", (noise_col >= NOISE_SPLIT_LO)
                                & (noise_col <= NOISE_SPLIT_HI)),
                        ("hi", noise_col > NOISE_SPLIT_HI)]:
        idx = np.flatnonzero(mask)
        for rank, j in enumerate(idx[np.argsort(-w[idx])][:2]):
            starts[f"is_top_{label}_{rank}"] = dict(zip(ORDER, ths[j]))

    cands, start_records = [], []
    for label, sv in starts.items():
        vals, lj = nm_polish(pc, x, y, sv, maxiter=nm_maxiter)
        cands.append((vals, lj))
        start_records.append({"start_label": label,
                              "start": {k: float(sv[k]) for k in ORDER},
                              "converged": {k: float(vals[k]) for k in ORDER},
                              "log_joint": _j(lj)})
        print(f"  NM from {label:<15} -> lj={lj:9.2f}  " +
              " ".join(f"{k}={vals[k]:.4f}" for k in ORDER))
    out["mode_hunt_starts"] = start_records

    modes = dedup_modes(cands)
    mode_records = []
    for vals, lj in modes:
        ml, pr = decompose(pc, x, y, vals)
        mode_records.append({
            "values": vals, "log_joint": _j(lj), "log_ml": _j(ml),
            "log_prior": _j(pr),
            "verified_local_max": is_local_max(pc, x, y, vals, lj),
        })
    masses = per_mode_mass(modes, ths, lml)
    for r, mass in zip(mode_records, masses):
        r["pooled_is_mass"] = mass
    out["modes"] = mode_records
    print(f"  distinct modes: {len(mode_records)}")
    for r in mode_records:
        v = r["values"]
        print(f"    lj={r['log_joint']:9.2f} (ml={r['log_ml']:.2f}, "
              f"prior={r['log_prior']:.2f}, local_max="
              f"{r['verified_local_max']}, IS mass={r['pooled_is_mass']:.3f})"
              f"  " + " ".join(f"{k}={v[k]:.4f}" for k in ORDER))

    # Valleys between VERIFIED mode pairs only; the verdict requires a
    # verified pair separated by a >1-nat valley (preflight review: the
    # valley pair must be the verified pair, not any dedup survivor).
    verified_idx = [i for i, r in enumerate(mode_records)
                    if r["verified_local_max"]]
    out["valleys"] = []
    for a_i in range(len(verified_idx)):
        for b_i in range(a_i + 1, len(verified_idx)):
            i, j = verified_idx[a_i], verified_idx[b_i]
            vlj = valley_between(pc, x, y, modes[i][0], modes[j][0])
            depth = min(modes[i][1], modes[j][1]) - vlj
            out["valleys"].append({"between": [i, j],
                                   "valley_log_joint": _j(vlj),
                                   "depth_below_lower_mode": _j(depth)})
            print(f"  valley between verified modes {i},{j}: lj={vlj:.2f} "
                  f"(depth {depth:.2f} below the lower mode)")
    depths = [v["depth_below_lower_mode"] for v in out["valleys"]
              if v["depth_below_lower_mode"] is not None]
    out["bimodal"] = bool(any(d > 1.0 for d in depths))
    out["near_threshold"] = bool(any(0.5 < d <= 3.0 for d in depths))
    # Pre-registered coherence: not bimodal, or every secondary verified mode
    # holds < 5% of pooled IS mass.
    secondary_mass = [r["pooled_is_mass"] for i, r in enumerate(mode_records)
                      if r["verified_local_max"] and i != (verified_idx[0]
                      if verified_idx else -1)]
    out["coherent_geometry"] = bool(
        not out["bimodal"] or all(m0 < 0.05 for m0 in secondary_mass))
    print(f"  bimodal verdict: {out['bimodal']} "
          f"(near_threshold={out['near_threshold']}, "
          f"coherent_geometry={out['coherent_geometry']})")

    ml, pr = decompose(pc, x, y, TRUTHISH)
    out["truthish"] = {"values": dict(TRUTHISH), "log_ml": _j(ml),
                       "log_prior": _j(pr), "log_joint": _j(ml + pr)}
    print(f"  truth-ish: log ML={ml:.2f}  log prior={pr:.2f}  "
          f"log joint={ml + pr:.2f}  (MAP log joint "
          f"{out['map']['log_joint']:.2f})")
    return out


# ── Stage B ────────────────────────────────────────────────────────

def basin_occupancy(cache_path):
    if not os.path.exists(cache_path):
        return None
    with np.load(cache_path) as z:
        noise = z["likelihood.noise_covar.noise_prior"]
    return {"P_noise_lo": float(np.mean(noise < NOISE_SPLIT_LO)),
            "P_noise_mid": float(np.mean((noise >= NOISE_SPLIT_LO)
                                         & (noise <= NOISE_SPLIT_HI))),
            "P_noise_hi": float(np.mean(noise > NOISE_SPLIT_HI)),
            "n": int(len(noise))}


def run_method_fingerprinted(method, budget, pc, x, y, x_eval,
                             candidate_results, n_predictives, cache_path,
                             force_refit=False):
    """fmc.run_one_method plus a prior-fingerprint sidecar on the sampler
    cache: a cache written under a different prior definition is deleted and
    refit instead of silently reused (preflight review, cache-staleness
    finding). A cache with no sidecar (pre-fingerprint era) is stamped with
    the current config once and accepted."""
    fp = _config_fingerprint(pc)
    sidecar = cache_path + ".fingerprint"
    if os.path.exists(cache_path) and not force_refit:
        if os.path.exists(sidecar):
            with open(sidecar) as f:
                stored = f.read().strip()
            if stored != fp:
                print(f"  [cache] STALE prior fingerprint for {cache_path} "
                      f"— the config changed since these draws were sampled; "
                      f"deleting and refitting")
                os.remove(cache_path)
                os.remove(sidecar)
        else:
            print(f"  [cache] no fingerprint sidecar for {cache_path}; "
                  f"stamping with the current config (pre-fingerprint cache, "
                  f"accepted once)")
            with open(sidecar, "w") as f:
                f.write(fp)
    res = fmc.run_one_method(method, budget, pc, x, y, x_eval,
                             candidate_results, n_predictives,
                             cache_path=cache_path, force_refit=force_refit)
    if cache_path and os.path.exists(cache_path) \
            and not os.path.exists(sidecar):
        with open(sidecar, "w") as f:
            f.write(fp)
    return res


def stage_b_one(name, pc, x, y, x_eval, candidate_results, methods,
                n_predictives, force_refit=False, uncapped=False):
    """Full BMS* pipeline per method via the D12 comparison machinery.
    NUTS runs capped at max_tree_depth=7 (D8/D12: result-preserving at
    model-selection precision on the informative geometry, ~9x cheaper;
    the cap's validation does NOT automatically transfer to other
    geometries — disclosed in the report). uncapped=True is the
    pre-registered spot-check arm (pyro default depth 10, cache tag _td10)."""
    td_tag = "_td10" if uncapped else "_td7"
    print(f"\n{'=' * 60}\n  stage B{' (UNCAPPED spot-check)' if uncapped else ''}"
          f": config = {name}\n{'=' * 60}")
    budgets = fmc.method_budgets(quick=False,
                                 max_tree_depth=None if uncapped else 7)
    out = {"config": name, "methods": {}, "uncapped": bool(uncapped),
           "prior_fingerprint": _config_fingerprint(pc)}
    for method in methods:
        print(f"  method = {method}")
        cache_path = os.path.join(RUN_DIR, f"samples_{name}_{method}{td_tag}.npz")
        res = run_method_fingerprinted(
            method, budgets[method], pc, x, y, x_eval, candidate_results,
            n_predictives, cache_path, force_refit)
        res["basin_occupancy"] = basin_occupancy(cache_path)
        out["methods"][method] = res
        print(f"    fit {res['fit_seconds']:.0f}s, occupancy "
              f"{res['basin_occupancy']}")
    return out


# ── Stage IS: mass-faithful model selection by SIR ─────────────────

def _boltzmann_posterior(G, tau):
    """Exact replication of bms_star.soft_transfer's aggregation
    (normalize_per_draw=False, global-shift stabilization)."""
    lw = -G / tau
    w = np.exp(lw - lw.max())
    s = w.mean(axis=0)
    tot = s.sum()
    return s / tot if tot > 0 else np.ones(G.shape[1]) / G.shape[1]


def _sir_bms(pc, x, y, x_eval, candidate_results, ths, lml, n_pred,
             sir_seed=SEED):
    """SIR-resample n_pred hyperparameter draws from IS weights, push them
    through the D12 predictive-extraction + BMS* pipeline. Returns
    (per_metric dict, G matrices per metric, resampled noise column)."""
    w = np.exp(lml - lml.max())
    p = w / w.sum()
    rng = np.random.default_rng(sir_seed)
    idx = rng.choice(len(p), size=n_pred, replace=True, p=p)
    samples = {LONG[s]: ths[idx, j].copy() for j, s in enumerate(ORDER)}

    kernels, knames = build_kernels_from_config(pc)
    likelihood = build_likelihood_from_config(pc)
    model, likelihood = build_model(x, y, kernels, knames, likelihood)
    np.random.seed(SEED)   # match run_one_method's subsample convention
    gp_samples = extract_gp_predictives(
        model, likelihood, x, y, x_eval, samples,
        kernel_builder=lambda: build_kernels_from_config(pc),
        likelihood_builder=lambda: build_likelihood_from_config(pc),
        n_posterior_samples=n_pred, jitter=1e-4,
    )
    if not gp_samples:
        raise RuntimeError("no valid GP predictives from SIR draws")
    results = run_bms_star(gp_samples, candidate_results, fmc.METRICS,
                           np.array(fmc.TAUS))
    per_metric, G_by_metric = {}, {}
    for metric in fmc.METRICS:
        bms_by_tau = results[metric]
        G = bms_by_tau[fmc.TAUS[0]].G_matrix
        G_by_metric[metric] = G
        winners = np.argmin(G, axis=1)
        per_metric[metric] = {
            "posteriors": {str(tau): [float(pp) for pp in
                                      bms_by_tau[tau].instance_posteriors]
                           for tau in fmc.TAUS},
            "hard_win_fractions": [float(np.mean(winners == j))
                                   for j in range(G.shape[1])],
        }
    return per_metric, G_by_metric, ths[idx, ORDER.index("noise")], idx


def stage_is_one(name, pc, x, y, x_eval, candidate_results, n_predictives,
                 is_seeds, smoke=False, n_boot=1000):
    """SIR-resample hyperparameter draws from the pooled stage-A prior-IS
    weights and push them through the same predictive-extraction + BMS*
    pipeline as stage B. Mass-faithful by construction (no mode-locked
    sampler in the loop); validity gated on pooled IS ESS >= 100
    (pre-registered floor). Uncertainty reported two ways: (a) bootstrap
    over SIR draws (resample G-matrix rows, rerun the exact soft_transfer
    aggregation) — the SIR/MC error given the weights; (b) per-IS-seed
    replication (independent 60-200k-draw pools) — the weight-estimation
    scatter."""
    print(f"\n{'=' * 60}\n  stage IS (mass-faithful SIR): config = {name}"
          f"\n{'=' * 60}")
    ths, lml = load_pooled_is(name, is_seeds, smoke)
    w = np.exp(lml - lml.max())
    ess = float(w.sum() ** 2 / (w ** 2).sum())

    per_metric, G_by_metric, noise, idx = _sir_bms(
        pc, x, y, x_eval, candidate_results, ths, lml, n_predictives)

    # (a) bootstrap over SIR draws at tau=1 (primary + appendix metric)
    boot = {}
    rng = np.random.default_rng(1)
    for metric in ("pw_kl_vcal", "kl_forward"):
        G = G_by_metric[metric]
        reps = np.empty((n_boot, G.shape[1]))
        for b in range(n_boot):
            rows = rng.integers(0, G.shape[0], G.shape[0])
            reps[b] = _boltzmann_posterior(G[rows], 1.0)
        boot[metric] = {
            "se": [float(v) for v in reps.std(axis=0)],
            "q025": [float(v) for v in np.quantile(reps, 0.025, axis=0)],
            "q975": [float(v) for v in np.quantile(reps, 0.975, axis=0)],
        }

    # (b) per-IS-seed replication (weight-estimation scatter)
    per_seed = {}
    for seed in is_seeds:
        ths_s, lml_s = load_pooled_is(name, [seed], smoke)
        pm_s, _, _, _ = _sir_bms(pc, x, y, x_eval, candidate_results,
                                 ths_s, lml_s, n_predictives)
        per_seed[str(seed)] = pm_s["pw_kl_vcal"]["posteriors"]["1.0"]

    out = {
        "config": name,
        "pooled_is_ess": ess,
        "ess_floor_ok": bool(ess >= 100),
        "n_sir_draws": int(n_predictives),
        "n_unique_sir_draws": int(len(np.unique(idx))),
        "sir_occupancy": {
            "P_noise_lo": float(np.mean(noise < NOISE_SPLIT_LO)),
            "P_noise_mid": float(np.mean((noise >= NOISE_SPLIT_LO)
                                         & (noise <= NOISE_SPLIT_HI))),
            "P_noise_hi": float(np.mean(noise > NOISE_SPLIT_HI)),
        },
        "bootstrap_tau1": boot,
        "per_is_seed_pw_kl_vcal_tau1": per_seed,
        "metrics": per_metric,
        "model_names": [cr.name for cr in candidate_results],
    }
    top = per_metric["pw_kl_vcal"]["posteriors"]["1.0"]
    se = boot["pw_kl_vcal"]["se"]
    print(f"  pooled IS ESS={ess:.0f} (floor ok: {out['ess_floor_ok']}), "
          f"{out['n_unique_sir_draws']}/{n_predictives} unique SIR draws")
    print(f"  pw_kl_vcal tau=1: " +
          " ".join(f"{v:.3f}±{s_:.3f}" for v, s_ in zip(top, se)) +
          f"  -> top {out['model_names'][int(np.argmax(top))]}")
    print(f"  per-IS-seed Sin+Linear@tau1: " +
          " ".join(f"{v[2]:.3f}" for v in per_seed.values()))
    return out


# ── Stage noise-marginal: arbitrating HMC occupancy vs prior-IS mass ──

def profile_laplace_noise_marginal(pc, x, y, mode_vals, grid):
    """Independent estimate of the noise marginal: for each fixed noise on
    the grid, Laplace-integrate over u = log(ls, os, lv) —
    g(u) = log_joint(exp(u), noise) + sum(u) (log-space Jacobian), and
    log m(noise) = g(u*) + (3/2) log(2 pi) - 0.5 log|-H(u*)|.
    Shares no machinery with prior-IS (no sampling) or NUTS (no chain);
    warm-started along the grid with a fixed fallback start at the mode."""
    out = []
    mode_u = np.log([mode_vals[k] for k in ("ls", "os", "lv")])
    warm = mode_u.copy()
    for nz in grid:
        def g(u):
            vals = {"ls": math.exp(u[0]), "os": math.exp(u[1]),
                    "lv": math.exp(u[2]), "noise": float(nz)}
            lj = log_joint(pc, x, y, vals)
            return lj + float(np.sum(u)) if np.isfinite(lj) else -np.inf
        f = lambda u: -g(np.asarray(u, dtype=float))
        best = None
        for u0 in (warm, mode_u):
            r = minimize(f, u0, method="Nelder-Mead",
                         options={"xatol": 1e-6, "fatol": 1e-8,
                                  "maxiter": 2000})
            if best is None or r.fun < best.fun:
                best = r
        u_star = np.asarray(best.x, dtype=float)
        warm = u_star.copy()
        g0 = g(u_star)
        h = 1e-3
        H = np.zeros((3, 3))
        for i in range(3):
            for j2 in range(i, 3):
                ei = np.zeros(3); ei[i] = h
                ej = np.zeros(3); ej[j2] = h
                if i == j2:
                    H[i, i] = (g(u_star + ei) - 2 * g0 + g(u_star - ei)) / h ** 2
                else:
                    H[i, j2] = H[j2, i] = (
                        g(u_star + ei + ej) - g(u_star + ei - ej)
                        - g(u_star - ei + ej) + g(u_star - ei - ej)
                    ) / (4 * h ** 2)
        sign, logdet = np.linalg.slogdet(-H)
        logm = g0 + 1.5 * math.log(2 * math.pi) - 0.5 * logdet \
            if sign > 0 else None
        out.append({"noise": float(nz),
                    "log_marginal": _j(logm) if logm is not None else None,
                    "hessian_pd": bool(sign > 0),
                    "conditional_opt": {"ls": float(math.exp(u_star[0])),
                                        "os": float(math.exp(u_star[1])),
                                        "lv": float(math.exp(u_star[2]))},
                    "log_joint_at_opt": _j(g0 - float(np.sum(u_star)))})
    return out


def _profile_band_masses(profile, grid):
    """Trapezoid-integrate exp(log m) over the grid; band masses on the
    D12 split."""
    logm = np.array([p["log_marginal"] if p["log_marginal"] is not None
                     else -np.inf for p in profile])
    m = np.exp(logm - np.nanmax(logm[np.isfinite(logm)]))
    total = np.trapz(m, grid)
    def band(lo, hi):
        mask = (grid >= lo) & (grid <= hi)
        if mask.sum() < 2:
            return 0.0
        return float(np.trapz(m[mask], grid[mask]) / total)
    return {"P_noise_lo": band(grid.min(), NOISE_SPLIT_LO),
            "P_noise_mid": band(NOISE_SPLIT_LO, NOISE_SPLIT_HI),
            "P_noise_hi": band(NOISE_SPLIT_HI, grid.max())}


def mh_noise_occupancy(pc, x, y, seeds=(42, 1, 2), n_samples=30000,
                       n_burnin=5000):
    """Jacobian-corrected RW-MH referee (D13): an independent sampler code
    path (no pyro/NUTS, no IS weights). Slow-mixing, so per-seed scatter is
    reported rather than pooled."""
    from bistar_gp.fit import fit_mcmc_simple
    import torch.nn.functional as F
    rows = []
    for seed in seeds:
        m, l = map_fitted(pc, x, y)
        raw = fit_mcmc_simple(m, l, x, y, n_samples=n_samples,
                              n_burnin=n_burnin, proposal_scale=0.1,
                              verbose=False, seed=seed)
        noise = F.softplus(
            torch.tensor(raw["likelihood.noise_covar.raw_noise"])).numpy()
        lo, hi = noise < NOISE_SPLIT_LO, noise > NOISE_SPLIT_HI
        lab = lo[lo | hi]
        rows.append({"seed": int(seed),
                     "P_noise_lo": float(lo.mean()),
                     "P_noise_mid": float((~lo & ~hi).mean()),
                     "P_noise_hi": float(hi.mean()),
                     "lo_hi_crossings": int(np.sum(lab[1:] != lab[:-1]))
                     if lab.size else 0})
    return rows


def stage_noise_marginal_one(name, pc, x, y, is_seeds):
    """Arbitrate the HMC-occupancy vs prior-IS-mass contradiction that fires
    the pre-registered spot-check rule: three estimators that share no
    failure mode (prior-IS with per-band ESS, RW-MH referee, profile-Laplace
    quadrature) against the capped and (if present) uncapped NUTS draws."""
    print(f"\n{'=' * 60}\n  stage noise-marginal: config = {name}"
          f"\n{'=' * 60}")
    out = {"config": name}

    ths, lml = load_pooled_is(name, is_seeds)
    out["prior_is_pooled"] = _is_summary(ths, lml)
    pi = out["prior_is_pooled"]
    print(f"  prior-IS pooled: lo {pi['P_noise_lo']:.3f}±{pi['P_noise_lo_se']:.3f}"
          f" (ESS {pi['P_noise_lo_ess']:.0f})  mid {pi['P_noise_mid']:.3f}"
          f"±{pi['P_noise_mid_se']:.3f} (ESS {pi['P_noise_mid_ess']:.0f})  "
          f"hi {pi['P_noise_hi']:.3f}±{pi['P_noise_hi_se']:.3f}")

    print("  RW-MH referee (Jacobian-corrected, 3 seeds x 30k):")
    out["rw_mh"] = mh_noise_occupancy(pc, x, y)
    for r in out["rw_mh"]:
        print(f"    seed={r['seed']}: lo {r['P_noise_lo']:.3f}  "
              f"mid {r['P_noise_mid']:.3f}  hi {r['P_noise_hi']:.3f}  "
              f"lo/hi crossings {r['lo_hi_crossings']}")

    rec_a = _load_json(os.path.join(RUN_DIR, f"stage_a_{name}.json"))
    if rec_a and rec_a.get("modes"):
        mode_vals = rec_a["modes"][0]["values"]
    else:
        m, l = map_fitted(pc, x, y)
        mode_vals = model_values(m, l)
    grid = np.geomspace(0.005, 1.2, 40)
    profile = profile_laplace_noise_marginal(pc, x, y, mode_vals, grid)
    out["profile_laplace"] = {"grid": [float(v) for v in grid],
                              "profile": profile,
                              "band_masses": _profile_band_masses(profile,
                                                                  grid)}
    bm = out["profile_laplace"]["band_masses"]
    n_pd = sum(p["hessian_pd"] for p in profile)
    print(f"  profile-Laplace quadrature ({n_pd}/{len(profile)} grid points "
          f"with PD Hessian): lo {bm['P_noise_lo']:.3f}  "
          f"mid {bm['P_noise_mid']:.3f}  hi {bm['P_noise_hi']:.3f}")

    out["hmc_capped"] = basin_occupancy(
        os.path.join(RUN_DIR, f"samples_{name}_hmc_td7.npz"))
    out["hmc_uncapped"] = basin_occupancy(
        os.path.join(RUN_DIR, f"samples_{name}_hmc_td10.npz"))
    for lab, occ in [("HMC capped td7", out["hmc_capped"]),
                     ("HMC uncapped td10", out["hmc_uncapped"])]:
        if occ:
            print(f"  {lab}: lo {occ['P_noise_lo']:.3f}  "
                  f"mid {occ['P_noise_mid']:.3f}  hi {occ['P_noise_hi']:.3f}")
        else:
            print(f"  {lab}: (no draws cached)")
    return out


# ── Stage figures: paper figures from existing artifacts ──────────
#
# Figures A and B of the W4 plan, built ONLY from the artifacts the earlier
# stages already wrote under runs/prior_sensitivity/ (plus the frozen D12
# informative NUTS cache). Zero new sampling, zero new fitting: a missing
# artifact is a hard error, never a trigger to regenerate.

FIGURES_DIR = os.path.join(RUN_DIR, "figures")
D12_INFORMATIVE_HMC_TD7 = D12_TD7_SAMPLES.format(method="hmc")

# Every headline value the figures draw is asserted equal to these pinned
# expectations (rtol=0, atol=1e-12) before any plotting happens, so an
# artifact regeneration or a loader bug fails loudly instead of silently
# shipping a changed paper figure. Pinned 2026-07-10 from the D18 artifacts;
# the reading behind them is logged in Notes/DECISIONS.md D18.
FIGURE_EXPECTATIONS = {
    # Figure A(a): posteriors over candidates at tau=1 (pw_kl_vcal)
    "sir_tau1": [0.18339001724428333, 0.1923955140897971,
                 0.44067371117415843, 0.18354075749176121],
    "sir_se_tau1": [0.0015634274134566867, 0.0014802847955890557,
                    0.004603711128454453, 0.001562584075998181],
    "sir_per_seed_sl_tau1": [0.4193920342606442, 0.43844892902038984,
                             0.43064059968542645],
    "hmc_td7_tau1": [0.09823365495671643, 0.10779548523929092,
                     0.6956155236783261, 0.09835533612566655],
    "hmc_td10_sl_tau1": 0.6829264460101571,
    # Figure A(b): FULL posterior vectors across tau = 0.1/0.3/1/3/10, so
    # the rank-stability annotation ("SIR top model: Sin+Linear at every
    # tau") is validated against the competitors, not just the plotted
    # Sin+Linear column.
    "sir_posteriors_by_tau": [
        [0.12080661834058654, 0.12471402532260904,
         0.6336791776415797, 0.12080017869522483],
        [0.11428321467711881, 0.1242309937092506,
         0.6470214904679347, 0.11446430114569593],
        [0.18339001724428333, 0.1923955140897971,
         0.44067371117415843, 0.18354075749176121],
        [0.22466292426479983, 0.2291661941022073,
         0.3214361828057378, 0.22473469882725494],
        [0.24206050570700036, 0.2436430426456574,
         0.2722110986283088, 0.24208535301903347],
    ],
    "hmc_td7_posteriors_by_tau": [
        [1.8299301151582423e-07, 3.977737421444433e-07,
         0.9999992340789238, 1.8515432256175852e-07],
        [0.0023803405721920705, 0.00317230514211834,
         0.9920574210213365, 0.002389933264353046],
        [0.09823365495671643, 0.10779548523929092,
         0.6956155236783261, 0.09835533612566655],
        [0.2006057698580975, 0.20707826728881676,
         0.3916264832920806, 0.20068947956100516],
        [0.23616904886943507, 0.23845080835495713,
         0.2891814052482854, 0.23619873752732234],
    ],
    # Figure A caption: per-estimator predictive counts. The SIR hard
    # fractions double as the proof that all 1000 resampled predictives
    # contributed: validation checks every metric's fractions are exact
    # multiples of 1/n_sir_draws summing to n_sir_draws (a dropped draw in
    # extract_gp_predictives would change the denominator). NUTS counts
    # come from the stage-B artifacts' n_draws / n_predictives fields.
    "sir_hard_win_fractions": [0.012, 0.014, 0.973, 0.001],
    "n_sir_draws": 1000,
    "n_unique_sir_draws": 883,
    "hmc_td7_n_draws": 2000,
    "hmc_td7_n_predictives": 200,
    "hmc_td10_n_draws": 2000,
    "hmc_td10_n_predictives": 200,
    # Figure B: band masses recomputed from the raw pooled IS archives must
    # reproduce the stage-A JSON values (loader-vs-published cross-check)
    "informative_band_masses": [0.27681233655255916, 0.13100921848624894,
                                0.5921784449611923],
    "informative_band_mass_ses": [0.017734119055865614, 0.007023808133515267,
                                  0.015063383185777887],
    "toy_elicited_band_masses": [0.7626600010969103, 0.19107789655272284,
                                 0.04626210235036697],
    "toy_elicited_band_mass_ses": [0.0042828766004713355,
                                   0.0038377294106689635,
                                   0.0008658211496931529],
    # Figure B: noise COORDINATES of the verified 4-D joint-posterior modes
    "informative_mode_noise_coords": [0.07359659801305256, 0.591688467884243],
    "informative_valley_depth_nats": 6.342292769404359,
    "toy_elicited_mode_noise_coords": [0.06186741902432317],
    # Figure B: VI landings, MAP markers, NUTS occupancy
    "informative_vi_noise_landings": [0.5554295364761581, 0.5455063804748477,
                                      0.542531082579625, 0.5711517096958254],
    "informative_map_noise": 0.07359770255695969,
    "toy_elicited_vi_noise_landings": [0.46361706637812744,
                                       0.48518030909454685,
                                       0.44244467118404235,
                                       0.4961007286508642],
    "toy_elicited_map_noise": 0.061867347763041584,
    "informative_nuts_occupancy_td7": [1.0, 0.0, 0.0],
    "toy_elicited_nuts_occupancy_td7": [1.0, 0.0, 0.0],
    "toy_elicited_nuts_occupancy_td10": [1.0, 0.0, 0.0],
    "informative_nuts_n_draws": 2000,
    "toy_elicited_nuts_n_draws_td7": 2000,
    "toy_elicited_nuts_n_draws_td10": 2000,
    # Figure B(b) arbitration citation (D18 Status)
    "rwmh_lo_by_seed": [0.7958666666666666, 0.8082333333333334,
                        0.8428333333333333],
    "rwmh_lo_hi_crossings": [44, 40, 38],
    "profile_laplace_lo": 0.7626153713752779,
}

FIGURE_TAUS = [0.1, 0.3, 1.0, 3.0, 10.0]


def _figures_required_artifacts():
    req = [os.path.join(RUN_DIR, f) for f in (
        "results_is_toy_elicited.json",
        "results_toy_elicited.json",
        "results_toy_elicited_uncapped.json",
        "stage_a_informative.json",
        "stage_a_toy_elicited.json",
        "results_noise_marginal_toy_elicited.json",
        "samples_toy_elicited_hmc_td7.npz",
        "samples_toy_elicited_hmc_td10.npz",
    )]
    req += [_is_draw_path(name, seed)
            for name in ("informative", "toy_elicited") for seed in (0, 1, 2)]
    req.append(D12_INFORMATIVE_HMC_TD7)
    return req


def figures_preflight():
    """Fail fast, listing every absent artifact: the figures stage builds
    ONLY from existing study outputs and never samples or refits."""
    missing = [p for p in _figures_required_artifacts()
               if not os.path.exists(p)]
    if missing:
        raise FileNotFoundError(
            "stage figures builds only from existing study artifacts and "
            "never samples; missing:\n  " + "\n  ".join(missing) +
            "\nRegenerate with the stage a/b/is/noise-marginal commands in "
            "the module docstring (expensive; see D18 for budgets).")


def load_figure_data():
    """Read-only assembly of every number the figures draw. Band masses are
    recomputed from the raw pooled IS archives (not copied from the JSONs)
    so validation cross-checks the raw draws against the published stage-A
    values."""
    figures_preflight()
    sir = _load_json(os.path.join(RUN_DIR, "results_is_toy_elicited.json"))
    res_b = _load_json(os.path.join(RUN_DIR, "results_toy_elicited.json"))
    res_u = _load_json(os.path.join(RUN_DIR,
                                    "results_toy_elicited_uncapped.json"))
    nm = _load_json(os.path.join(RUN_DIR,
                                 "results_noise_marginal_toy_elicited.json"))
    stage_a = {name: _load_json(os.path.join(RUN_DIR,
                                             f"stage_a_{name}.json"))
               for name in ("informative", "toy_elicited")}

    names = sir["model_names"]
    sl = names.index("Sin+Linear")
    sir_post = sir["metrics"]["pw_kl_vcal"]["posteriors"]
    hmc_post = res_b["methods"]["hmc"]["metrics"]["pw_kl_vcal"]["posteriors"]
    d = {
        "model_names": names,
        "taus": [float(t) for t in FIGURE_TAUS],
        "sir_tau1": sir_post["1.0"],
        "sir_se_tau1": sir["bootstrap_tau1"]["pw_kl_vcal"]["se"],
        "sir_per_seed_sl_tau1": [
            sir["per_is_seed_pw_kl_vcal_tau1"][s][sl] for s in ("0", "1", "2")],
        "hmc_td7_tau1": hmc_post["1.0"],
        "hmc_td10_sl_tau1": res_u["methods"]["hmc"]["metrics"]["pw_kl_vcal"]
                                 ["posteriors"]["1.0"][sl],
        "sir_posteriors_by_tau": [sir_post[str(t)] for t in FIGURE_TAUS],
        "hmc_td7_posteriors_by_tau": [hmc_post[str(t)] for t in FIGURE_TAUS],
        "sir_hard_win_fractions":
            sir["metrics"]["pw_kl_vcal"]["hard_win_fractions"],
        "sir_hard_win_fractions_by_metric": {
            m: rec["hard_win_fractions"]
            for m, rec in sir["metrics"].items()},
        "n_sir_draws": sir["n_sir_draws"],
        "n_unique_sir_draws": sir["n_unique_sir_draws"],
        "hmc_td7_n_draws": res_b["methods"]["hmc"]["n_draws"],
        "hmc_td7_n_predictives": res_b["methods"]["hmc"]["n_predictives"],
        "hmc_td10_n_draws": res_u["methods"]["hmc"]["n_draws"],
        "hmc_td10_n_predictives": res_u["methods"]["hmc"]["n_predictives"],
        "rwmh_lo_by_seed": [r["P_noise_lo"] for r in nm["rw_mh"]],
        "rwmh_lo_hi_crossings": [r["lo_hi_crossings"] for r in nm["rw_mh"]],
        "profile_laplace_lo":
            nm["profile_laplace"]["band_masses"]["P_noise_lo"],
    }

    for cfg in ("informative", "toy_elicited"):
        ths, lml = load_pooled_is(cfg, (0, 1, 2))
        summ = _is_summary(ths, lml)
        d[f"{cfg}_band_masses"] = [summ["P_noise_lo"], summ["P_noise_mid"],
                                   summ["P_noise_hi"]]
        d[f"{cfg}_band_mass_ses"] = [summ["P_noise_lo_se"],
                                     summ["P_noise_mid_se"],
                                     summ["P_noise_hi_se"]]
        d[f"{cfg}_noise_draws"] = ths[:, ORDER.index("noise")]
        d[f"{cfg}_is_weights"] = np.exp(lml - lml.max())
        rec = stage_a[cfg]
        d[f"{cfg}_mode_noise_coords"] = [
            r["values"]["noise"] for r in rec["modes"]
            if r["verified_local_max"]]
        d[f"{cfg}_vi_noise_landings"] = [
            rec["vi_seed_means"][s]["noise"] for s in ("0", "1", "2", "42")]
        d[f"{cfg}_map_noise"] = rec["map"]["values"]["noise"]
    d["informative_valley_depth_nats"] = \
        stage_a["informative"]["valleys"][0]["depth_below_lower_mode"]

    def occ_and_n(path):
        occ = basin_occupancy(path)
        return ([occ["P_noise_lo"], occ["P_noise_mid"], occ["P_noise_hi"]],
                occ["n"])

    def noise_draws(path):
        with np.load(path) as z:
            return z["likelihood.noise_covar.noise_prior"]
    te_td7 = os.path.join(RUN_DIR, "samples_toy_elicited_hmc_td7.npz")
    te_td10 = os.path.join(RUN_DIR, "samples_toy_elicited_hmc_td10.npz")
    d["informative_nuts_occupancy_td7"], d["informative_nuts_n_draws"] = \
        occ_and_n(D12_INFORMATIVE_HMC_TD7)
    d["toy_elicited_nuts_occupancy_td7"], d["toy_elicited_nuts_n_draws_td7"] \
        = occ_and_n(te_td7)
    d["toy_elicited_nuts_occupancy_td10"], \
        d["toy_elicited_nuts_n_draws_td10"] = occ_and_n(te_td10)
    d["informative_nuts_noise_draws"] = noise_draws(D12_INFORMATIVE_HMC_TD7)
    d["toy_elicited_nuts_noise_draws_td7"] = noise_draws(te_td7)
    return d


def _check(cond, msg):
    """Explicit raise instead of a bare assert so python -O cannot strip
    the structural figure gates."""
    if not cond:
        raise AssertionError(msg)


def validate_figure_data(data, expectations=FIGURE_EXPECTATIONS):
    """Assert-equal gate (W4): every plotted headline value must match its
    pinned expectation exactly (rtol=0, atol=1e-12) before plotting, and
    every caption claim must be derivable from the loaded artifacts."""
    from numpy.testing import assert_allclose
    for key, expected in expectations.items():
        assert_allclose(
            np.asarray(data[key], dtype=float),
            np.asarray(expected, dtype=float),
            rtol=0, atol=1e-12,
            err_msg=f"figure value drifted from its pinned expectation: "
                    f"{key}")
    _check(data["taus"] == [0.1, 0.3, 1.0, 3.0, 10.0],
           "figure tau grid changed")
    _check(data["model_names"] == ["Linear", "Sinusoidal", "Sin+Linear",
                                   "Quadratic"],
           "candidate model names or order changed")
    # Rank-stability behind the panel-(b) annotation: Sin+Linear must be
    # the SIR top model at EVERY tau, judged against the full vectors.
    sl = data["model_names"].index("Sin+Linear")
    for tau, row in zip(data["taus"], data["sir_posteriors_by_tau"]):
        _check(int(np.argmax(row)) == sl,
               f"SIR top model is not Sin+Linear at tau={tau}")
    # Caption proof that all n_sir_draws predictives contributed: every
    # metric's hard win fractions must be exact multiples of 1/n summing
    # to n (a draw silently dropped in extract_gp_predictives would have
    # changed the denominator).
    n = data["n_sir_draws"]
    for metric, fr in data["sir_hard_win_fractions_by_metric"].items():
        scaled = np.asarray(fr, dtype=float) * n
        _check(bool(np.allclose(scaled, np.round(scaled), atol=1e-9))
               and int(np.round(scaled.sum())) == n,
               f"SIR hard win fractions for {metric} are inconsistent "
               f"with {n} contributing predictives")
    print(f"  validated {len(expectations)} pinned figure values "
          f"(rtol=0, atol=1e-12)")


def _save_fig(fig, out_dir, stem):
    paths = []
    for ext in ("png", "pdf"):
        p = os.path.join(out_dir, f"{stem}.{ext}")
        fig.savefig(p, dpi=200, bbox_inches="tight")
        paths.append(p)
    return paths


def figure_a(data, out_dir):
    """Figure A `toy_model_posterior_elicited`: the N=20 money figure.
    (a) grouped bars at tau=1, SIR (mass-faithful headline) vs NUTS td7
    (density-mode-region answer), bootstrap-SE whiskers, per-IS-seed
    Sin+Linear points, uniform reference. (b) Sin+Linear posterior vs tau."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    names = data["model_names"]
    sl = names.index("Sin+Linear")
    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(11.5, 4.6))

    xs = np.arange(len(names))
    w = 0.38
    ax_a.bar(xs - w / 2, data["sir_tau1"], w,
             yerr=data["sir_se_tau1"], capsize=3,
             color="#2a6f97", label="SIR, mass-faithful (headline)")
    ax_a.bar(xs + w / 2, data["hmc_td7_tau1"], w,
             color="#c8875e", label="NUTS td7 (density-mode region)")
    ax_a.scatter([xs[sl] - w / 2] * 3, data["sir_per_seed_sl_tau1"],
                 s=22, facecolors="none", edgecolors="black", zorder=3,
                 label="per-IS-seed SIR replicates")
    ax_a.axhline(0.25, color="gray", ls="--", lw=1,
                 label="uniform (0.25)")
    ax_a.set_ylim(0, 0.80)
    ax_a.text(xs[sl] + w / 2 + 0.22, data["hmc_td7_tau1"][sl] - 0.02,
              f"td10: {data['hmc_td10_sl_tau1']:.3f}", fontsize=8,
              ha="left")
    ax_a.set_xticks(xs)
    ax_a.set_xticklabels(names)
    ax_a.set_ylabel("model posterior (pw_kl_vcal, tau = 1)")
    ax_a.set_title("(a) BMS* posteriors, toy_elicited prior")
    ax_a.legend(fontsize=8, loc="upper left")

    ax_b.semilogx(data["taus"],
                  [row[sl] for row in data["sir_posteriors_by_tau"]],
                  marker="o", color="#2a6f97", label="SIR, mass-faithful")
    ax_b.semilogx(data["taus"],
                  [row[sl] for row in data["hmc_td7_posteriors_by_tau"]],
                  marker="s", color="#c8875e", label="NUTS td7")
    ax_b.axhline(0.25, color="gray", ls="--", lw=1)
    ax_b.set_xlabel("tau (log scale)")
    ax_b.set_ylabel("Sin+Linear posterior")
    ax_b.set_title("(b) Sin+Linear vs tau")
    ax_b.text(0.03, 0.05, "SIR top model: Sin+Linear at every tau",
              transform=ax_b.transAxes, fontsize=8)
    ax_b.legend(fontsize=8)

    fig.suptitle("N=20 thesis toy under the re-elicited prior "
                 "(registry: toy_elicited_n20)", fontsize=11)
    occ7 = data["toy_elicited_nuts_occupancy_td7"][0]
    occ10 = data["toy_elicited_nuts_occupancy_td10"][0]
    caption = (
        f"SIR: {data['n_sir_draws']} resampled predictives "
        f"({data['n_unique_sir_draws']} unique hyperparameter draws) from "
        f"pooled 3-seed prior-IS; whiskers are bootstrap SEs over SIR "
        f"draws. NUTS td7: {data['hmc_td7_n_predictives']} predictives "
        f"subsampled from {data['hmc_td7_n_draws']} draws; the chain is "
        f"confined to the density-mode region (low-band occupancy "
        f"{occ7:.3f} at td7 and {occ10:.3f} at td10), so its bars answer "
        f"conditionally on that region while SIR carries the full-Bayes "
        f"headline.")
    fig.text(0.01, -0.04, caption, fontsize=7.5, wrap=True)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    paths = _save_fig(fig, out_dir, "toy_model_posterior_elicited")
    plt.close(fig)
    return paths


NOISE_HIST_BINS = np.geomspace(5e-3, 2.0, 90)


def _weighted_noise_hist(ax, noise, weights, color):
    """Weighted histogram of the IS noise marginal, normalized against the
    TOTAL weight rather than the in-window weight, so the display clip at
    2.0 cannot inflate the plotted density (the informative config holds
    0.20% of its weighted mass above the clip; band annotations always use
    all draws via _is_summary)."""
    bins = NOISE_HIST_BINS
    mask = (noise >= bins[0]) & (noise <= bins[-1])
    counts, edges = np.histogram(noise[mask], bins=bins,
                                 weights=weights[mask] / weights.sum())
    ax.stairs(counts / np.diff(edges), edges, fill=True, color=color,
              alpha=0.35)


def figure_b(data, out_dir):
    """Figure B `prior_misspec_geometry`: IS-weighted noise-variance
    marginals for `informative` (bimodal case study) and `toy_elicited`
    (unimodal, NUTS-confined), shared log axis, D12 split lines."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(11.5, 4.8), sharex=True)

    for ax, cfg, color, title in (
            (ax_a, "informative", "#7a5195",
             "(a) informative: prior-induced bimodality"),
            (ax_b, "toy_elicited", "#2a6f97",
             "(b) toy_elicited: unimodal, NUTS still confined")):
        noise = data[f"{cfg}_noise_draws"]
        weights = data[f"{cfg}_is_weights"]
        _weighted_noise_hist(ax, noise, weights, color)
        ax.set_xscale("log")
        for split in (NOISE_SPLIT_LO, NOISE_SPLIT_HI):
            ax.axvline(split, color="gray", ls="--", lw=1)
        for coord in data[f"{cfg}_mode_noise_coords"]:
            ax.axvline(coord, color=color, ls=":", lw=1.4)
            ax.text(coord, 0.97, f"{coord:.4f}", rotation=90, fontsize=7,
                    ha="right", va="top", transform=ax.get_xaxis_transform())
        ax.set_xlim(NOISE_HIST_BINS[0], NOISE_HIST_BINS[-1])
        masses = data[f"{cfg}_band_masses"]
        ses = data[f"{cfg}_band_mass_ses"]
        # Band centers in axes fractions, exact because xlim is pinned to
        # the bin range 5e-3..2.0 (no autoscale margins): the 0.15 / 0.30
        # splits fall at x-fractions 0.568 / 0.683.
        for x_pos, m, s in zip((0.24, 0.625, 0.84), masses, ses):
            ax.text(x_pos, 0.90, f"{m:.3f}±{s:.3f}", fontsize=8,
                    ha="center", transform=ax.transAxes)
        ax.plot(data[f"{cfg}_vi_noise_landings"],
                [0.78] * 4, marker="v", ls="none", color="black",
                markersize=5, transform=ax.get_xaxis_transform())
        ax.text(data[f"{cfg}_vi_noise_landings"][0], 0.81, "VI (4 seeds)",
                fontsize=7, ha="center",
                transform=ax.get_xaxis_transform())
        ax.plot([data[f"{cfg}_map_noise"]], [0.02], marker="^", ls="none",
                color="black", markersize=6,
                transform=ax.get_xaxis_transform())
        ax.text(data[f"{cfg}_map_noise"], 0.055, "MAP", fontsize=7,
                ha="center", transform=ax.get_xaxis_transform())
        ax.set_xlabel("noise variance (log scale)")
        ax.set_title(title, fontsize=10)
    ax_a.set_ylabel("IS-weighted posterior density")

    # (a): the 6.3-nat valley between the verified joint modes, plus a NUTS
    # draw rug (the D12 chain reports only the low basin: 1.00/0.00/0.00).
    lo_m, hi_m = data["informative_mode_noise_coords"]
    ax_a.annotate("", xy=(hi_m, 0.50), xytext=(lo_m, 0.50),
                  xycoords=ax_a.get_xaxis_transform(),
                  arrowprops=dict(arrowstyle="<->", color="black", lw=0.9))
    ax_a.text(math.sqrt(lo_m * hi_m), 0.52,
              f"{data['informative_valley_depth_nats']:.3f}-nat valley\n"
              f"(straight path, joint space)",
              fontsize=7.5, ha="center",
              transform=ax_a.get_xaxis_transform())
    occ = data["informative_nuts_occupancy_td7"]
    ax_a.plot(data["informative_nuts_noise_draws"],
              np.full(len(data["informative_nuts_noise_draws"]), 0.965),
              marker="|", ls="none", color="#c8875e", markersize=7,
              alpha=0.08, transform=ax_a.get_xaxis_transform())
    ax_a.text(0.03, 0.72,
              f"NUTS td7 draw rug (top): occupancy\n"
              f"{occ[0]:.2f} / {occ[1]:.2f} / {occ[2]:.2f} lo/mid/hi\n"
              f"({data['informative_nuts_n_draws']} draws, low basin only)",
              fontsize=7.5, transform=ax_a.transAxes, va="top")

    # (b): confinement contrast + the three-way arbitration citation.
    occ7 = data["toy_elicited_nuts_occupancy_td7"][0]
    occ10 = data["toy_elicited_nuts_occupancy_td10"][0]
    lo_mass = data["toy_elicited_band_masses"][0]
    rw = data["rwmh_lo_by_seed"]
    ax_b.plot(data["toy_elicited_nuts_noise_draws_td7"],
              np.full(len(data["toy_elicited_nuts_noise_draws_td7"]), 0.965),
              marker="|", ls="none", color="#c8875e", markersize=7,
              alpha=0.08, transform=ax_b.get_xaxis_transform())
    ax_b.text(
        0.03, 0.72,
        f"NUTS low-band occupancy {occ7:.3f} (td7)\n"
        f"and {occ10:.3f} (td10) vs prior-IS mass\n"
        f"{lo_mass:.3f}: mode-confined even here.\n"
        f"Arbitration upheld the IS mass\n"
        f"(RW-MH referee {min(rw):.3f}–{max(rw):.3f}\n"
        f"across seeds 42/1/2, profile-Laplace\n"
        f"quadrature {data['profile_laplace_lo']:.3f}).",
        fontsize=7.5, transform=ax_b.transAxes, va="top")

    caption = (
        f"Pooled prior-IS noise marginals (weights exp(lml - max), 3 seeds "
        f"per config); dotted verticals mark the noise coordinates of "
        f"verified 4-D joint-posterior modes; dashed verticals are the D12 "
        f"band split at 0.15/0.30; band annotations are pooled IS masses "
        f"with delta-method SEs, computed from ALL draws. Densities are "
        f"normalized against all draws too; the display clips at noise "
        f"2.0, above which the informative config carries 0.20% of its "
        f"mass. Orange rugs along the top: NUTS td7 noise draws "
        f"({data['informative_nuts_n_draws']} and "
        f"{data['toy_elicited_nuts_n_draws_td7']} per chain).")
    fig.text(0.01, -0.05, caption, fontsize=7.5, wrap=True)
    fig.tight_layout()
    paths = _save_fig(fig, out_dir, "prior_misspec_geometry")
    plt.close(fig)
    return paths


def build_figures(out_dir=None):
    """Preflight, load, validate against the pinned expectations, then draw
    Figures A and B. Returns the list of written paths."""
    out_dir = out_dir or FIGURES_DIR
    data = load_figure_data()
    validate_figure_data(data)
    os.makedirs(out_dir, exist_ok=True)
    return figure_a(data, out_dir) + figure_b(data, out_dir)


# ── Report ─────────────────────────────────────────────────────────

def _load_json(path):
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def _informative_stage_b():
    """Adapt the existing D12 capped run to the stage-B schema (frozen
    baseline — never regenerated by this study)."""
    d12 = _load_json(D12_TD7_JSON)
    if d12 is None:
        return None
    out = {"config": "informative", "methods": {},
           "source": "runs/fit_method_metric_comparison/results_td7.json"}
    for method, res in d12["methods"].items():
        res = dict(res)
        res["basin_occupancy"] = basin_occupancy(
            D12_TD7_SAMPLES.format(method=method))
        out["methods"][method] = res
    return out


def _drift_check():
    """Compare a fresh (current-code) informative vi/map stage-B rerun
    against the frozen 2026-07-05 results_td7.json — the cheap cross-code
    comparability check the preflight review asked for."""
    fresh_run = _load_json(os.path.join(RUN_DIR, "results_informative.json"))
    frozen = _load_json(D12_TD7_JSON)
    if fresh_run is None or frozen is None:
        return None
    deltas = {}
    for method in ("vi", "map"):
        if method not in fresh_run["methods"] or method not in frozen["methods"]:
            continue
        d = 0.0
        for tau in map(str, fmc.TAUS):
            a = fresh_run["methods"][method]["metrics"]["pw_kl_vcal"]["posteriors"][tau]
            b2 = frozen["methods"][method]["metrics"]["pw_kl_vcal"]["posteriors"][tau]
            d = max(d, max(abs(u - v) for u, v in zip(a, b2)))
        deltas[method] = d
    return deltas or None


def _fmt_probs(probs):
    return " | ".join(f"{p:.3f}" for p in probs)


def render_report(model_names):
    a = {name: _load_json(os.path.join(RUN_DIR, f"stage_a_{name}.json"))
         for name in STUDY_CONFIGS}
    b = {name: _load_json(os.path.join(RUN_DIR, f"results_{name}.json"))
         for name in STUDY_CONFIGS if name != "informative"}
    b["informative"] = _informative_stage_b()
    # Recompute occupancy (incl. P_mid) from the cached draws for artifacts
    # written before basin_occupancy reported the mid band.
    for name, rec in b.items():
        if rec is None or name == "informative":
            continue
        for method, res in rec["methods"].items():
            occ = res.get("basin_occupancy")
            if occ is not None and "P_noise_mid" not in occ:
                occ2 = basin_occupancy(os.path.join(
                    RUN_DIR, f"samples_{name}_{method}_td7.npz"))
                if occ2 is not None:
                    res["basin_occupancy"] = occ2
    # Merge the mass-faithful SIR arm as a pseudo-method row per config.
    for name in STUDY_CONFIGS:
        rec_is = _load_json(os.path.join(RUN_DIR, f"results_is_{name}.json"))
        if rec_is and b.get(name):
            flag = "" if rec_is["ess_floor_ok"] else " (ESS<100, UNRELIABLE)"
            b[name]["methods"][f"is_sir{flag}"] = {
                "metrics": rec_is["metrics"],
                "basin_occupancy": {**rec_is["sir_occupancy"],
                                    "n": rec_is["n_sir_draws"]},
                "fit_seconds": 0.0,
            }

    lines = [
        "# Prior-sensitivity / re-elicitation study — thesis toy (W2 gate)",
        "",
        "Generated by `experiments/prior_sensitivity_study.py --stage report` "
        "(rerun to regenerate; the study's reading is logged in "
        "`Notes/DECISIONS.md`, not here).",
        "",
        "Question: is the D12 bimodality (and the VI/HMC disagreement, and "
        "the 'true model from the minority-mass basin' caveat) an artifact "
        "of the `informative` prior fighting the toy data's scale, and does "
        "a reasonable re-elicited prior make the BI*/BMS* toy result stable?",
        "",
        "- Data: thesis toy, sin(x) + 0.25x + N(0, 0.5^2), N=20, seed=42 "
        "(same draws as D12).",
        "- Truth-ish hyperparameters: lengthscale 1.5, outputscale 0.5, "
        "linear variance 0.0625 (= slope^2), noise variance 0.25 (= 0.5^2).",
        "- NUTS arms capped at max_tree_depth=7 (validated as "
        "result-preserving on the informative geometry, D8/D12; the "
        "informative baseline row is the frozen D12 capped run, never "
        "regenerated here). The cap's validation does not automatically "
        "transfer to other prior geometries; per-site crude ESS is reported "
        "as the health indicator and the pre-registered spot-check rule "
        "applies to the adopted config.",
        "- Basin split at noise variance 0.15/0.30 (D12 convention) with "
        "P_mid always reported; per-mode pooled-IS mass supplements the "
        "fixed split where modes relocate.",
        "- `is_sir` rows are the mass-faithful model-selection arm: SIR "
        "resampling from pooled multi-seed prior importance sampling, no "
        "mode-locked sampler in the loop (gated on pooled IS ESS >= 100).",
        "",
        "## Pre-registered decision rules (fixed before stage-B results "
        "were read)",
        "",
        "Roles: `toy_elicited` = candidate replacement prior; `vague` = "
        "robustness pole; `gamma_relaxed` = attribution arm only (never "
        "adopted). Coherence per config: (i) no verified mode pair with a "
        ">1-nat valley, or every secondary verified mode < 5% pooled-IS "
        "mass; (ii) MAP/HMC/prior-IS agree on the dominant basin; (iii) "
        "VI-vs-HMC max abs posterior difference at tau=1 (pw_kl_vcal) "
        "<= 0.10. Adoption of a replacement prior is winner-blind. Outcome "
        "patterns: (A) alternates coherent + same winner + VI/HMC agree -> "
        "adopt toy_elicited, informative becomes the documented "
        "prior-misspecification case study; (B) toy_elicited coherent, "
        "different winner -> still adopt, reframe the toy; (C) toy_elicited "
        "incoherent -> keep informative, frame the toy as a "
        "prior-sensitivity example; (D) all alternates incoherent -> "
        "data-intrinsic geometry, small-N framing; (E) winner varies across "
        "coherent alternates -> prior-sensitivity example framing.",
        "",
        "## Configs",
        "",
        "| config | ls prior | os prior | lv prior | noise prior |",
        "|---|---|---|---|---|",
    ]
    for name, pc in STUDY_CONFIGS.items():
        row = [name]
        for s in ORDER:
            fam, p1, p2 = getattr(pc, SITE_SPECS[s])
            row.append(f"{fam}({p1:.3g}, {p2:.3g})")
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")
    for name, pc in STUDY_CONFIGS.items():
        lines.append(f"- **{name}**: {pc.description}")

    lines += [
        "",
        "## Stage A — prior scorecard (prior-only, no data)",
        "",
        "Log prior density at the truth-ish point per hyperparameter "
        "(vs at the prior's own median). Attribution of D12's "
        "'the prior fights the data scale'.",
        "",
        "| config | ls | os | lv | noise | total at truth-ish |",
        "|---|---|---|---|---|---|",
    ]
    for name, rec in a.items():
        if rec is None:
            continue
        c = rec["prior_scorecard"]
        cells = [f"{c[s]['logpdf_at_truthish']:.2f}" for s in ORDER]
        lines.append(f"| {name} | " + " | ".join(cells) +
                     f" | {c['total_logpdf_at_truthish']:.2f} |")

    lines += [
        "",
        "## Stage A — posterior geometry per config",
        "",
        "Modes from the wide-start Nelder-Mead hunt (MAP, VI landings "
        "seeds 0/1/2/42, prior medians, truth-ish, fixed D12 basin probes, "
        "prior draws, top-weight IS draws per noise stratum). Verified = "
        "axis + random-direction perturbation check. Mass by pooled "
        "multi-seed prior importance sampling with delta-method SEs (the "
        "D13 authority). Bimodal requires a VERIFIED pair separated by a "
        ">1-nat straight-path valley; 'coherent' additionally allows "
        "secondary verified modes holding < 5% pooled mass.",
        "",
        "| config | verified modes | bimodal? | coherent? | MAP noise | "
        "truthish-MAP gap | P(noise<0.15) | P_mid | P(noise>0.30) | "
        "pooled ESS (lo/hi) |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for name, rec in a.items():
        if rec is None:
            continue
        pi = rec["prior_is"]["pooled"]
        n_ver = sum(r["verified_local_max"] for r in rec["modes"])
        gap = rec["map"]["log_joint"] - rec["truthish"]["log_joint"]
        lines.append(
            f"| {name} | {n_ver}/{len(rec['modes'])} | "
            f"{'YES' if rec['bimodal'] else 'no'}"
            f"{' (near thr.)' if rec.get('near_threshold') else ''} | "
            f"{'yes' if rec['coherent_geometry'] else 'NO'} | "
            f"{rec['map']['values']['noise']:.4f} | "
            f"{gap:.1f} | "
            f"{pi['P_noise_lo']:.3f}±{pi['P_noise_lo_se']:.3f} | "
            f"{pi['P_noise_mid']:.3f} | "
            f"{pi['P_noise_hi']:.3f}±{pi['P_noise_hi_se']:.3f} | "
            f"{pi['ess']:.0f} ({pi['P_noise_lo_ess']:.0f}/"
            f"{pi['P_noise_hi_ess']:.0f}) |")

    lines += [
        "",
        "### Mode inventory",
        "",
        "| config | mode | noise | ls | os | lv | log ML | log prior | "
        "log joint | local max? | pooled IS mass |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for name, rec in a.items():
        if rec is None:
            continue
        for i, r in enumerate(rec["modes"]):
            v = r["values"]
            lines.append(
                f"| {name} | {i} | {v['noise']:.4f} | {v['ls']:.3f} | "
                f"{v['os']:.3f} | {v['lv']:.4f} | {r['log_ml']:.2f} | "
                f"{r['log_prior']:.2f} | {r['log_joint']:.2f} | "
                f"{'yes' if r['verified_local_max'] else 'NO'} | "
                f"{r.get('pooled_is_mass', float('nan')):.3f} |")

    lines += [
        "",
        "### VI landing points (per seed)",
        "",
        "| config | seed | ls | os | lv | noise |",
        "|---|---|---|---|---|---|",
    ]
    for name, rec in a.items():
        if rec is None:
            continue
        for seed, v in rec["vi_seed_means"].items():
            lines.append(f"| {name} | {seed} | {v['ls']:.3f} | {v['os']:.3f} "
                         f"| {v['lv']:.4f} | {v['noise']:.4f} |")

    lines += [
        "",
        "## Stage B — BMS* model posteriors (pw_kl_vcal, tau = 1)",
        "",
        "Primary metric per W1. Occupancy columns are P(noise<0.15) / "
        "P_mid / P(noise>0.30) of the method's draws.",
        "",
        "| config | method | " + " | ".join(model_names) +
        " | top model | occupancy lo/mid/hi |",
        "|---|---|" + "---|" * (len(model_names) + 2),
    ]
    for name, rec in b.items():
        if rec is None:
            continue
        for method, res in rec["methods"].items():
            probs = res["metrics"]["pw_kl_vcal"]["posteriors"]["1.0"]
            top = model_names[int(np.argmax(probs))]
            occ = res.get("basin_occupancy")
            occ_s = (f"{occ['P_noise_lo']:.2f}/"
                     f"{occ.get('P_noise_mid', float('nan')):.2f}/"
                     f"{occ['P_noise_hi']:.2f}") if occ else "—"
            lines.append(f"| {name} | {method} | {_fmt_probs(probs)} | "
                         f"{top} | {occ_s} |")

    lines += [
        "",
        "## Stage B — hard best-match win fractions (thesis aggregation)",
        "",
        "| config | method | " + " | ".join(model_names) + " |",
        "|---|---|" + "---|" * len(model_names),
    ]
    for name, rec in b.items():
        if rec is None:
            continue
        for method, res in rec["methods"].items():
            wf = res["metrics"]["pw_kl_vcal"]["hard_win_fractions"]
            lines.append(f"| {name} | {method} | {_fmt_probs(wf)} |")

    lines += [
        "",
        "## Stage B — kl_forward sensitivity (appendix metric, tau = 1)",
        "",
        "| config | method | " + " | ".join(model_names) + " | top model |",
        "|---|---|" + "---|" * (len(model_names) + 1),
    ]
    for name, rec in b.items():
        if rec is None:
            continue
        for method, res in rec["methods"].items():
            probs = res["metrics"]["kl_forward"]["posteriors"]["1.0"]
            top = model_names[int(np.argmax(probs))]
            lines.append(f"| {name} | {method} | {_fmt_probs(probs)} | {top} |")

    lines += [
        "",
        "## Stage B — tau sensitivity of the true model (pw_kl_vcal, "
        "Sin+Linear posterior)",
        "",
        "| config | method | " + " | ".join(f"tau={t}" for t in fmc.TAUS)
        + " |",
        "|---|---|" + "---|" * len(fmc.TAUS),
    ]
    sl = model_names.index("Sin+Linear") if "Sin+Linear" in model_names else 2
    for name, rec in b.items():
        if rec is None:
            continue
        for method, res in rec["methods"].items():
            post = res["metrics"]["pw_kl_vcal"]["posteriors"]
            row = [post[str(t)][sl] for t in fmc.TAUS]
            lines.append(f"| {name} | {method} | {_fmt_probs(row)} |")

    lines += [
        "",
        "## Stage B — VI vs HMC agreement per config",
        "",
        "Max absolute model-posterior difference at tau = 1 (pw_kl_vcal). "
        "Pre-registered agreement threshold: <= 0.10.",
        "",
        "| config | max abs(Δposterior) | within threshold? |",
        "|---|---|---|",
    ]
    for name, rec in b.items():
        if rec is None or "hmc" not in rec["methods"] \
                or "vi" not in rec["methods"]:
            continue
        ph = rec["methods"]["hmc"]["metrics"]["pw_kl_vcal"]["posteriors"]["1.0"]
        pv = rec["methods"]["vi"]["metrics"]["pw_kl_vcal"]["posteriors"]["1.0"]
        d = max(abs(x1 - x2) for x1, x2 in zip(ph, pv))
        lines.append(f"| {name} | {d:.3f} | "
                     f"{'yes' if d <= 0.10 else 'NO'} |")

    lines += [
        "",
        "## Mass-faithful SIR uncertainty (pw_kl_vcal, tau = 1)",
        "",
        "Bootstrap = resampling SIR draws (G-matrix rows) through the exact "
        "soft_transfer aggregation: the SIR/MC error given the IS weights. "
        "Per-IS-seed = the full SIR pipeline repeated on each independent "
        "prior-IS pool: the weight-estimation scatter.",
        "",
        "| config | " + " | ".join(f"{m} ±SE" for m in model_names) +
        " | per-seed Sin+Linear | n SIR draws |",
        "|---|" + "---|" * (len(model_names) + 2),
    ]
    for name in STUDY_CONFIGS:
        rec_is = _load_json(os.path.join(RUN_DIR, f"results_is_{name}.json"))
        if rec_is is None or "bootstrap_tau1" not in rec_is:
            continue
        post = rec_is["metrics"]["pw_kl_vcal"]["posteriors"]["1.0"]
        se = rec_is["bootstrap_tau1"]["pw_kl_vcal"]["se"]
        cells = " | ".join(f"{p:.3f}±{s:.3f}" for p, s in zip(post, se))
        seeds = rec_is.get("per_is_seed_pw_kl_vcal_tau1", {})
        sl_seeds = "/".join(f"{v[sl]:.3f}" for v in seeds.values()) or "—"
        lines.append(f"| {name} | {cells} | {sl_seeds} | "
                     f"{rec_is['n_sir_draws']} |")

    lines += [
        "",
        "## Noise-marginal arbitration and the pre-registered spot-check",
        "",
        "The spot-check rule fires when HMC draw occupancy contradicts the "
        "prior-IS mass by more than 2 SE. Arbitration: three estimators "
        "sharing no failure mode (prior-IS with per-band ESS; the "
        "Jacobian-corrected RW-MH referee, an independent sampler code "
        "path; profile-Laplace quadrature of p(noise|y), no sampling at "
        "all) against the capped and uncapped NUTS draws.",
        "",
        "| config | estimator | P(noise<0.15) | P_mid | P(noise>0.30) |",
        "|---|---|---|---|---|",
    ]
    for name in STUDY_CONFIGS:
        nm = _load_json(os.path.join(RUN_DIR,
                                     f"results_noise_marginal_{name}.json"))
        if nm is None:
            continue
        pi = nm["prior_is_pooled"]
        lines.append(f"| {name} | prior-IS (pooled) | "
                     f"{pi['P_noise_lo']:.3f}±{pi['P_noise_lo_se']:.3f} | "
                     f"{pi['P_noise_mid']:.3f}±{pi['P_noise_mid_se']:.3f} | "
                     f"{pi['P_noise_hi']:.3f}±{pi['P_noise_hi_se']:.3f} |")
        for r in nm["rw_mh"]:
            lines.append(f"| {name} | RW-MH seed {r['seed']} "
                         f"({r['lo_hi_crossings']} lo/hi crossings) | "
                         f"{r['P_noise_lo']:.3f} | {r['P_noise_mid']:.3f} | "
                         f"{r['P_noise_hi']:.3f} |")
        bm = nm["profile_laplace"]["band_masses"]
        lines.append(f"| {name} | profile-Laplace quadrature | "
                     f"{bm['P_noise_lo']:.3f} | {bm['P_noise_mid']:.3f} | "
                     f"{bm['P_noise_hi']:.3f} |")
        for lab, occ in [("NUTS capped td7", nm["hmc_capped"]),
                         ("NUTS uncapped td10", nm["hmc_uncapped"])]:
            if occ:
                lines.append(f"| {name} | {lab} (2000 draws) | "
                             f"{occ['P_noise_lo']:.3f} | "
                             f"{occ['P_noise_mid']:.3f} | "
                             f"{occ['P_noise_hi']:.3f} |")

    for name in STUDY_CONFIGS:
        unc = _load_json(os.path.join(RUN_DIR,
                                      f"results_{name}_uncapped.json"))
        if unc is None:
            continue
        lines += [
            "",
            f"### Uncapped spot-check arm — {name}",
            "",
            "| method | " + " | ".join(model_names) +
            " | top model | occupancy lo/mid/hi |",
            "|---|" + "---|" * (len(model_names) + 2),
        ]
        for method, res in unc["methods"].items():
            probs = res["metrics"]["pw_kl_vcal"]["posteriors"]["1.0"]
            top = model_names[int(np.argmax(probs))]
            occ = res.get("basin_occupancy")
            occ_s = (f"{occ['P_noise_lo']:.2f}/"
                     f"{occ.get('P_noise_mid', float('nan')):.2f}/"
                     f"{occ['P_noise_hi']:.2f}") if occ else "—"
            lines.append(f"| {method} (td10) | {_fmt_probs(probs)} | {top} | "
                         f"{occ_s} |")

    drift = _drift_check()
    lines += ["", "## Baseline drift check", ""]
    if drift:
        lines += [
            "The frozen informative baseline (2026-07-05 code) vs a fresh "
            "vi/map rerun through this study's stage-B path on current "
            "code; max abs pw_kl_vcal posterior difference across all tau:",
            "",
        ] + [f"- {m}: {d:.5f}" for m, d in drift.items()] + [
            "",
            "(vi/map are deterministic given seeds, so any nonzero drift "
            "beyond float noise would indicate a cross-code comparability "
            "problem for the HMC rows too.)",
        ]
    else:
        lines += ["Not run (results_informative.json absent — run "
                  "`--stage b --configs informative --methods vi map`)."]

    lines += ["", "## Reading", "",
              "(Filled in by the decision entry that closes this study — "
              "see Notes/DECISIONS.md.)", ""]
    return "\n".join(lines)


# ── Main ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("--stage", required=True,
                        choices=["a", "b", "is", "noise-marginal", "report",
                                 "figures"])
    parser.add_argument("--uncapped", action="store_true",
                        help="stage b: pyro default max_tree_depth=10 — the "
                             "pre-registered spot-check arm (cache tag _td10, "
                             "results_<config>_uncapped.json)")
    parser.add_argument("--configs", nargs="+", default=None,
                        choices=list(STUDY_CONFIGS))
    parser.add_argument("--methods", nargs="+", default=["hmc", "vi", "map"],
                        choices=["hmc", "vi", "map", "hmc_laplace"])
    parser.add_argument("--is-n", type=int, default=60000,
                        help="prior importance-sampling draws per seed "
                             "(stage a)")
    parser.add_argument("--is-seeds", type=int, nargs="+", default=[0, 1, 2],
                        help="prior-IS seeds (stage a samples each; stage is "
                             "pools them)")
    parser.add_argument("--n-predictives", type=int, default=200)
    parser.add_argument("--force-refit", action="store_true")
    parser.add_argument("--smoke", action="store_true",
                        help="tiny budgets, *_smoke artifacts — pipeline "
                             "validation only")
    args = parser.parse_args()

    os.makedirs(RUN_DIR, exist_ok=True)

    if args.stage == "figures":
        for p in build_figures():
            print(f"  -> {p}")
        return

    x, y, _ = generate_toy_data()   # thesis toy: N=20, defaults
    tag = "_smoke" if args.smoke else ""

    if args.stage == "a":
        configs = args.configs or list(STUDY_CONFIGS)
        is_n = 2000 if args.smoke else args.is_n
        is_seeds = args.is_seeds[:1] if args.smoke else args.is_seeds
        for name in configs:
            out = stage_a_one(name, STUDY_CONFIGS[name], x, y, is_n,
                              is_seeds, smoke=args.smoke)
            path = os.path.join(RUN_DIR, f"stage_a_{name}{tag}.json")
            with open(path, "w") as f:
                json.dump(out, f, indent=2)
            print(f"  -> {path}")
        return

    x_np, y_np = x.numpy(), y.numpy()
    x_eval = np.linspace(x_np.min() - 1, x_np.max() + 1, 60)
    x_eval_torch = torch.tensor(x_eval).double()

    if args.stage in ("b", "is"):
        candidates = build_toy_candidates()
        candidate_results = []
        for cand in candidates:
            cand.fit(x_np, y_np)
            candidate_results.append(cand.predict(x_eval))

    if args.stage == "b":
        configs = args.configs or [n for n in STUDY_CONFIGS
                                   if n != "informative"]
        for name in configs:
            out = stage_b_one(name, STUDY_CONFIGS[name], x, y, x_eval_torch,
                              candidate_results, args.methods,
                              args.n_predictives, args.force_refit,
                              uncapped=args.uncapped)
            out["model_names"] = [cr.name for cr in candidate_results]
            suffix = "_uncapped" if args.uncapped else ""
            path = os.path.join(RUN_DIR, f"results_{name}{suffix}.json")
            with open(path, "w") as f:
                json.dump(out, f, indent=2)
            print(f"  -> {path}")
        return

    if args.stage == "noise-marginal":
        configs = args.configs or ["toy_elicited"]
        for name in configs:
            out = stage_noise_marginal_one(name, STUDY_CONFIGS[name], x, y,
                                           args.is_seeds)
            path = os.path.join(RUN_DIR, f"results_noise_marginal_{name}.json")
            with open(path, "w") as f:
                json.dump(out, f, indent=2)
            print(f"  -> {path}")
        return

    if args.stage == "is":
        configs = args.configs or list(STUDY_CONFIGS)
        n_pred = 20 if args.smoke else args.n_predictives
        is_seeds = args.is_seeds[:1] if args.smoke else args.is_seeds
        for name in configs:
            out = stage_is_one(name, STUDY_CONFIGS[name], x, y, x_eval_torch,
                               candidate_results, n_pred, is_seeds,
                               smoke=args.smoke)
            path = os.path.join(RUN_DIR, f"results_is_{name}{tag}.json")
            with open(path, "w") as f:
                json.dump(out, f, indent=2)
            print(f"  -> {path}")
        return

    if args.stage == "report":
        # Model names from any stage-B artifact (identical across configs).
        names = None
        for name in STUDY_CONFIGS:
            rec = _load_json(os.path.join(RUN_DIR, f"results_{name}.json"))
            if rec and "model_names" in rec:
                names = rec["model_names"]
                break
        if names is None:
            d12 = _load_json(D12_TD7_JSON)
            names = d12["model_names"] if d12 else \
                ["Linear", "Sinusoidal", "Sin+Linear", "Quadratic"]
        md = render_report(names)
        with open(DOC_PATH, "w") as f:
            f.write(md)
        print(f"Report -> {DOC_PATH}")


if __name__ == "__main__":
    main()
