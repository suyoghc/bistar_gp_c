#!/usr/bin/env python3
"""
impact_assessment.py — deterministic old-vs-new metrics for the correctness fixes.

Uses ONLY the stable API present on BOTH the pre-fix and post-fix branches
(run_bms_star, build_model, fit_map, fit_mcmc_simple, decompose_model, and a Pyro
trace of the model prior), so the SAME file can run in two git worktrees and the
two JSON outputs can be diffed. It deliberately avoids new-only surface
(model_posterior, laplace_log_Z_Mx, the fit seed= kwarg) so it imports cleanly on
the old code too.

What each section isolates:
  - bms_star_posteriors : soft_transfer axis fix (fed FIXED synthetic GP samples +
                          candidates, so only the aggregation math varies).
  - hmc_latent_sites    : AdditiveGPModel double prior-registration fix (7 vs 4).
  - decompose_full_std  : decompose_model cross-covariance fix (full_mean identical,
                          full_std differs).
  - mcmc_simple_post_std: fit_mcmc_simple per-datum tempering fix (old ~n× too wide).

Usage:
  python experiments/impact_assessment.py --out out.json
  python experiments/impact_assessment.py --compare old.json new.json
"""
import os
import sys
import json
import argparse
import subprocess

# Make `import bistar_gp` resolve to THIS worktree's package regardless of cwd.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np


def _git_sha():
    try:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return subprocess.check_output(["git", "-C", root, "rev-parse", "--short", "HEAD"],
                                       text=True).strip()
    except Exception:
        return "unknown"


def collect(seed=0, n_points=40):
    import torch
    from types import SimpleNamespace
    torch.set_default_dtype(torch.float64)
    import bistar_gp.metrics_v2  # noqa: F401 — register pw_* metrics on both branches
    from bistar_gp.bms_star import GPPosteriorSample, run_bms_star

    out = {"seed": seed, "n_points": n_points}

    # ── 1. BMS* aggregation on FIXED synthetic inputs (isolates soft_transfer) ──
    try:
        rng = np.random.default_rng(seed)
        ne = 12

        def spd(scale):
            A = rng.standard_normal((ne, ne))
            return scale * (A @ A.T) + ne * np.eye(ne)

        gp_samples = [GPPosteriorSample(mean=rng.standard_normal(ne), cov=spd(0.3),
                                        hyperparameters={}) for _ in range(8)]
        cands = [SimpleNamespace(name=f"M{j}", mean=rng.standard_normal(ne), cov=spd(0.3))
                 for j in range(4)]
        res = run_bms_star(gp_samples, cands,
                           ["kl_forward", "pw_kl_vcal", "pw_nll"], np.array([1.0, 5.0]))
        bms = {}
        for metric, by_tau in res.items():
            for tau, r in by_tau.items():
                bms[f"{metric}@tau{float(tau):g}"] = {
                    nm: float(p) for nm, p in zip(r.instance_names, r.instance_posteriors)}
        out["bms_star_posteriors"] = bms
    except Exception as e:
        out["bms_star_posteriors"] = {"error": repr(e)[:300]}

    # ── 2. HMC latent-site count (isolates the double prior-registration fix) ──
    try:
        import pyro
        from bistar_gp.model import build_toy_kernels, build_model
        xt = torch.linspace(0, 6, 20); yt = torch.sin(xt) + 0.25 * xt
        m, _ = build_model(xt, yt, *build_toy_kernels())
        tr = pyro.poutine.trace(m.pyro_sample_from_prior).get_trace()
        sites = sorted(nm for nm, s in tr.nodes.items() if s["type"] == "sample")
        out["hmc_latent_sites"] = {"count": len(sites), "names": sites}
    except Exception as e:
        out["hmc_latent_sites"] = {"error": repr(e)[:300]}

    # ── 3. decompose_model full_std (isolates the cross-covariance fix) ──
    try:
        from bistar_gp import generate_toy_data, build_model
        from bistar_gp.model import build_toy_kernels
        from bistar_gp.fit import fit_map
        from bistar_gp.debias import decompose_model
        torch.manual_seed(seed)
        xtr, ytr, _ = generate_toy_data(n_points=n_points, x_range=(0.0, 6.0),
                                        noise_std=0.3, seed=seed)
        m, l = build_model(xtr, ytr, *build_toy_kernels())
        fit_map(m, l, xtr, ytr, n_iter=150, lr=0.05, verbose=False)
        xte = torch.linspace(0.0, 6.0, 25)
        dec = decompose_model(m, l, xtr, ytr, xte, n_samples=5)
        idx = np.linspace(0, 24, 5).astype(int)
        out["decompose_full_std"] = {
            "x": [round(float(xte[i]), 3) for i in idx],
            "full_mean": [round(float(dec.full_mean[i]), 5) for i in idx],
            "full_std": [round(float(dec.full_std[i]), 5) for i in idx],
        }
    except Exception as e:
        out["decompose_full_std"] = {"error": repr(e)[:300]}

    # ── 4. fit_mcmc_simple posterior width (isolates the per-datum tempering fix) ──
    try:
        from bistar_gp import generate_toy_data, build_model
        from bistar_gp.model import build_toy_kernels
        from bistar_gp.fit import fit_mcmc_simple
        np.random.seed(seed); torch.manual_seed(seed)   # global seeds (no seed= kwarg: runs on old too)
        xtr, ytr, _ = generate_toy_data(n_points=n_points, x_range=(0.0, 6.0),
                                        noise_std=0.3, seed=seed)
        m, l = build_model(xtr, ytr, *build_toy_kernels())
        s = fit_mcmc_simple(m, l, xtr, ytr, n_samples=3000, n_burnin=500,
                            proposal_scale=0.1, verbose=False)
        out["mcmc_simple_post_std"] = {k: round(float(np.std(v)), 5) for k, v in s.items()}
    except Exception as e:
        out["mcmc_simple_post_std"] = {"error": repr(e)[:300]}

    return out


def _fmt(v):
    return f"{v:.4f}" if isinstance(v, float) else str(v)


def compare(old_path, new_path):
    old = json.load(open(old_path)); new = json.load(open(new_path))
    print(f"\n{'='*74}\n  OLD-vs-NEW impact  ({old.get('git_sha','?')}  ->  {new.get('git_sha','?')})\n{'='*74}")

    def leaves(d, prefix=""):
        for k, v in d.items():
            key = f"{prefix}{k}"
            if isinstance(v, dict):
                yield from leaves(v, key + ".")
            elif isinstance(v, list):
                yield key, tuple(v)
            else:
                yield key, v

    o = dict(leaves(old)); n = dict(leaves(new))
    keys = [k for k in n if k not in ("seed", "n_points", "git_sha")]
    changed = same = 0
    for k in sorted(keys):
        ov, nv = o.get(k, "—"), n.get(k)
        if isinstance(ov, (int, float)) and isinstance(nv, (int, float)):
            delta = nv - ov
            mark = "  CHANGED" if abs(delta) > 1e-9 else ""
            if mark:
                changed += 1
            else:
                same += 1
            print(f"  {k:<48} {_fmt(ov):>12} -> {_fmt(nv):<12} {('Δ='+_fmt(delta)) if mark else ''}")
        else:
            mark = "  CHANGED" if ov != nv else ""
            (changed := changed + 1) if mark else (same := same + 1)
            print(f"  {k:<48} {str(ov):>12} -> {str(nv):<12}{mark}")
    print(f"\n  {changed} changed, {same} unchanged.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", help="write metrics JSON to this path")
    ap.add_argument("--compare", nargs=2, metavar=("OLD", "NEW"), help="diff two metrics JSONs")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--n-points", type=int, default=40)
    args = ap.parse_args()

    if args.compare:
        compare(*args.compare)
        return

    metrics = collect(seed=args.seed, n_points=args.n_points)
    metrics["git_sha"] = _git_sha()
    text = json.dumps(metrics, indent=2)
    if args.out:
        with open(args.out, "w") as f:
            f.write(text)
        print(f"wrote {args.out}  (git {metrics['git_sha']})")
    else:
        print(text)


if __name__ == "__main__":
    main()
