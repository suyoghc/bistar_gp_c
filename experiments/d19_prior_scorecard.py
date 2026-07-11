"""D19 Stage-0 prior-predictive scorecard v2 (training-only; no test value read).

Frozen record of the D19 planning-session scorecard (2026-07-10), ported verbatim
from the planning scratchpad with repo-relative paths; the sampling and bootstrap
seed streams are unchanged, so the output reproduces
`runs/d19_planning/scorecard_v2.json` deterministically. Holdout-seal note
(docs/plan-d19-mauna.md section 6.6): the legacy loader materializes the test
split mechanically; this script binds `_xte/_yte` unused and never reads a test
value. Arm definitions here are
the A2-ratified parameters (see `docs/plan-d19-mauna.md` section 7); do not edit
them in place — a revised arm is a NEW named arm per the pre-registration.

Codex-round-3 corrections implemented:
  (1) n=2000 fixed-seed draws per arm; bootstrap (B=1000) uncertainty on every
      observed percentile and on the q2.5/q97.5 interval endpoints.
  (2) statistics replaced by functionals applied IDENTICALLY to the realized train
      series and to every simulated draw: deseasonalized trend change via
      full-calendar-year (exactly 12 months) annual means; decadal change via annual
      means 10 years apart; seasonal peak-to-trough after within-year linear
      detrending (one shared 12x12 projection, monthly grid is equispaced);
      total range; monthly first-difference sd.
  (3) numerically stabilized: correlation-space Cholesky with relative jitter and
      escalation ladder [1e-8, 1e-6, 1e-4]; per-draw errstate guards; nonfinite and
      escalation counts reported per arm, nothing silently discarded.
Acceptance rule (unchanged, declared in v1 before any computation): adoption
candidates must place every realized reference inside the central 95% interval;
attribution arms are judged on rows their revised block governs. New confidence
flag: a row passes WITH CONFIDENCE if the bootstrap 95% CI of the realized
percentile stays inside (0.025, 0.975).
"""
import json
from pathlib import Path

import numpy as np
import torch

torch.set_default_dtype(torch.float64)
from bistar_gp import load_mauna_loa

YSTD = 14.58342466738224
N_DRAWS, B_BOOT = 2000, 1000
JITTERS = [1e-8, 1e-6, 1e-4]
OUT_PATH = Path(__file__).resolve().parents[1] / "runs" / "d19_planning" / "scorecard_v2.json"

x_tr, y_tr, _xte, _yte, info = load_mauna_loa(normalize=True, test_years=5.0)
assert abs(float(info["y_std"]) - YSTD) < 1e-9, (
    f"data drift: realized y_std {info['y_std']!r} != pinned {YSTD!r}")
x = x_tr.numpy()
y_ppm = y_tr.numpy() * YSTD
n = len(x)
D = np.abs(x[:, None] - x[None, :])
cal = x + info["x_offset"]
year_of = np.floor(cal).astype(int)

full_years = [yr for yr in np.unique(year_of) if (year_of == yr).sum() == 12]
year_idx = {yr: np.where(year_of == yr)[0] for yr in full_years}
# shared within-year linear-detrend projection (12 equispaced points)
t12 = np.arange(12, dtype=float)
X12 = np.stack([np.ones(12), t12], axis=1)
P12 = np.eye(12) - X12 @ np.linalg.solve(X12.T @ X12, X12.T)

y0, y1 = full_years[0], full_years[-1]
ydec = y0 + 10 if (y0 + 10) in year_idx else min(full_years, key=lambda z: abs(z - (y0 + 10)))

def annual_mean(s, yr):
    return s[..., year_idx[yr]].mean(axis=-1)

def functionals(S):
    """S: (m, n) array of series in ppm. Returns dict of (m,) statistic arrays."""
    out = {}
    out["trend_change"] = np.abs(annual_mean(S, y1) - annual_mean(S, y0))
    out["decadal_change"] = np.abs(annual_mean(S, ydec) - annual_mean(S, y0))
    ptts = [ (S[:, year_idx[yr]] @ P12.T).max(axis=1) - (S[:, year_idx[yr]] @ P12.T).min(axis=1)
             for yr in full_years ]
    out["seasonal_ptt_detr"] = np.mean(np.stack(ptts, axis=0), axis=0)
    out["total_range"] = S.max(axis=1) - S.min(axis=1)
    out["diff_sd"] = np.std(np.diff(S, axis=1), axis=1)
    return out

REF = {k: float(v[0]) for k, v in functionals(y_ppm[None, :]).items()}

def c_rbf(l):   return np.exp(-D**2 / (2 * l**2))
def c_per(l):   return np.exp(-2 * np.sin(np.pi * D)**2 / l**2)
def c_m32(l):
    a = np.sqrt(3) * D / l
    return (1 + a) * np.exp(-a)

def draw_site(rng, site):
    kind = site[0]
    if kind == "ln":    return float(np.exp(rng.normal(site[1], site[2])))
    if kind == "gamma": return float(rng.gamma(site[1], 1.0 / site[2]))
    if kind == "logitn":
        z = rng.normal(site[1], site[2])
        return float(site[3] + (site[4] - site[3]) / (1 + np.exp(-z)))
    raise ValueError(kind)

def sample_comp(rng, v, C, counts):
    for j, jit in enumerate(JITTERS):
        try:
            L = np.linalg.cholesky(C + jit * np.eye(n))
        except np.linalg.LinAlgError:
            continue
        f = np.sqrt(v) * (L @ rng.standard_normal(n))
        if not np.all(np.isfinite(f)):
            counts["nonfinite_component"] += 1
            return None
        if j > 0:
            counts["jitter_escalations"] += 1
        return f
    counts["chol_failures"] += 1
    return None

LN, G = "ln", "gamma"
BASE_KERNEL = dict(t_ls=(LN,4.0,1.0), t_os=(G,4.0,0.5), s_ls=(G,3.0,2.0), s_os=(G,3.0,1.0),
                   m_ls=(G,3.0,1.0), m_os=(G,2.0,1.0))
ELIC_KERNEL = lambda tos_mu: dict(t_ls=(LN,np.log(30),1.0), t_os=(LN,tos_mu,1.0),
                                  s_ls=(G,3.0,2.0), s_os=(LN,np.log(0.025),1.0),
                                  m_ls=(LN,np.log(4.0),0.6), m_os=(LN,np.log(1.2e-3),1.0))
NOISE0, NOISE_E = (G,1.75,1.0), (LN,np.log(4.2e-4),1.0)
M1_SITES = dict(x_os=(LN,np.log(2.4e-4),1.2), x_ls=("logitn",-1.2528,1.082,0.1,1.0))

def make_arms(tos_mu, tag):
    return {
        f"P-kernel-{tag}":  (dict(**ELIC_KERNEL(tos_mu), noise=NOISE0), False),
        f"P-comb-{tag}":    (dict(**ELIC_KERNEL(tos_mu), noise=NOISE_E), False),
        f"P-comb+M1-{tag}": (dict(**ELIC_KERNEL(tos_mu), noise=NOISE_E), True),
    }

ARMS = {"P0": (dict(**BASE_KERNEL, noise=NOISE0), False),
        "P-noise": (dict(**BASE_KERNEL, noise=NOISE_E), False)}
ARMS.update(make_arms(np.log(1.5), "v1"))
ARMS.update(make_arms(np.log(2.5), "v1b"))

def run_arm(k_arm, name, arm, m1):
    rng = np.random.default_rng([k_arm, 20260710])
    counts = dict(nonfinite_draws=0, nonfinite_component=0, jitter_escalations=0,
                  chol_failures=0)
    sims, shares = [], []
    got = 0
    while got < N_DRAWS:
        h = {k: draw_site(rng, s) for k, s in arm.items()}
        f = sample_comp(rng, h["t_os"], c_rbf(h["t_ls"]), counts)
        g = sample_comp(rng, h["s_os"], c_per(h["s_ls"]), counts)
        m = sample_comp(rng, h["m_os"], c_rbf(h["m_ls"]), counts)
        if f is None or g is None or m is None:
            counts["nonfinite_draws"] += 1; got += 1; continue
        tot = f + g + m
        if m1:
            hx = {k: draw_site(rng, s) for k, s in M1_SITES.items()}
            fx = sample_comp(rng, hx["x_os"], c_m32(hx["x_ls"]), counts)
            if fx is None:
                counts["nonfinite_draws"] += 1; got += 1; continue
            tot = tot + fx
            shares.append(h["noise"] / (h["noise"] + hx["x_os"]))
        else:
            shares.append(h["noise"] / (h["noise"] + h["m_os"]))
        tot = (tot + np.sqrt(h["noise"]) * rng.standard_normal(n)) * YSTD
        if not np.all(np.isfinite(tot)):
            counts["nonfinite_draws"] += 1; got += 1; continue
        sims.append(tot); got += 1
    S = np.stack(sims, axis=0)
    stats = functionals(S)
    stats["nugget_share_vs_short"] = np.array(shares)
    brng = np.random.default_rng([k_arm, 77])
    out = {"counts": counts, "n_finite": int(S.shape[0])}
    for k, v in stats.items():
        v = v[np.isfinite(v)]
        q = np.quantile(v, [0.025, 0.5, 0.975])
        row = dict(q2p5=q[0], q50=q[1], q97p5=q[2])
        bidx = brng.integers(0, len(v), size=(B_BOOT, len(v)))
        bv = v[bidx]
        row["q2p5_se"] = float(np.std(np.quantile(bv, 0.025, axis=1)))
        row["q97p5_se"] = float(np.std(np.quantile(bv, 0.975, axis=1)))
        if k in REF:
            r = REF[k]
            row["realized"] = r
            row["pctile"] = float(np.mean(v <= r))
            bp = np.mean(bv <= r, axis=1)
            row["pctile_ci"] = [float(np.quantile(bp, 0.025)), float(np.quantile(bp, 0.975))]
            row["in95"] = bool(q[0] <= r <= q[2])
            row["confident"] = bool(row["pctile_ci"][0] > 0.025 and row["pctile_ci"][1] < 0.975)
        out[k] = row
    return out

results = {}
for k_arm, (name, (arm, m1)) in enumerate(ARMS.items()):
    results[name] = run_arm(k_arm, name, arm, m1)
    c = results[name]["counts"]
    print(f"{name}: nonfinite={c['nonfinite_draws']} jitter_esc={c['jitter_escalations']} "
          f"chol_fail={c['chol_failures']} n_finite={results[name]['n_finite']}")

print("\nrealized train references (ppm, corrected functionals):",
      json.dumps({k: round(v, 2) for k, v in REF.items()}),
      f"\n  [full years {full_years[0]}-{full_years[-1]}; decadal pair {y0} vs {ydec}; "
      f"annualized trend rate {REF['trend_change']/(y1-y0):.2f} ppm/y]")
for name, sc in results.items():
    print(f"\n== {name} ==")
    for k in ["trend_change","decadal_change","seasonal_ptt_detr","total_range","diff_sd"]:
        v = sc[k]
        print(f"  {k}: q2.5={v['q2p5']:.2f}(±{v['q2p5_se']:.2f}) q50={v['q50']:.2f} "
              f"q97.5={v['q97p5']:.2f}(±{v['q97p5_se']:.2f}) | realized {v['realized']:.2f} "
              f"pctile {v['pctile']:.3f} CI[{v['pctile_ci'][0]:.3f},{v['pctile_ci'][1]:.3f}] "
              f"in95={v['in95']} confident={v['confident']}")
    v = sc["nugget_share_vs_short"]
    print(f"  nugget_share_vs_short: q2.5={v['q2p5']:.2f} q50={v['q50']:.2f} q97.5={v['q97p5']:.2f}")

OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
with open(OUT_PATH, "w") as fjson:
    json.dump({"ref": REF, "results": results, "n_draws": N_DRAWS}, fjson, indent=2, default=float)
print(f"\nsaved {OUT_PATH}")
