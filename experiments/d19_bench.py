"""D19 planning micro-benchmarks (read-only on the model code; writes JSON only).

Frozen record of the D19 planning-session benchmark script (2026-07-10), ported
from the planning scratchpad with repo-relative output paths. The committed
reference outputs are `runs/d19_planning/bench_{sub,full}.json` (macOS arm64,
14 cores, torch 2.10.0, 10 threads); timings are machine- and load-dependent, so
re-runs overwrite honestly rather than reproduce those files. Re-run this same
script on Della (with threads pinned) before assigning any Della job — decision
A7 and risk R6 in `docs/plan-d19-mauna.md`.

Measures, at --scale sub (150-point whole-span season-preserving subsample) and
--scale full (all training months): one log-joint eval, one gradient, one Hessian
in the pyro unconstrained coordinates (SPD status + 1e-6-floor count reported),
100/1000 prior-proposal evals (extrapolated if the budget would be exceeded),
one MAP fit, and one profile-Laplace grid-point optimization. Also verifies the
sampled-site inventory and records data provenance. Timings are warmed up and
repeated; every section is budget-guarded and results are dumped incrementally.
"""

import argparse, hashlib, json, os, platform, time
from functools import partial
from pathlib import Path

import numpy as np
import torch

torch.set_default_dtype(torch.float64)

DEFAULT_OUT_DIR = Path(__file__).resolve().parents[1] / "runs" / "d19_planning"


def timed(fn, reps=5, warmup=1):
    for _ in range(warmup):
        fn()
    ts = []
    for _ in range(reps):
        t0 = time.perf_counter()
        fn()
        ts.append(time.perf_counter() - t0)
    return {"median_s": float(np.median(ts)), "min_s": float(np.min(ts)),
            "max_s": float(np.max(ts)), "reps": reps}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", choices=["sub", "full"], required=True)
    ap.add_argument("--budget-s", type=float, default=240.0)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = ap.parse_args()

    t_start = time.perf_counter()

    def remaining():
        return args.budget_s - (time.perf_counter() - t_start)

    res = {
        "scale": args.scale,
        "platform": platform.platform(),
        "cpu_count": os.cpu_count(),
        "torch_threads_default": torch.get_num_threads(),
        "torch": torch.__version__,
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.out_dir / f"bench_{args.scale}.json"

    def dump():
        res["elapsed_s"] = time.perf_counter() - t_start
        with open(out_path, "w") as f:
            json.dump(res, f, indent=2)

    import gpytorch
    import pyro
    from bistar_gp import load_mauna_loa, build_model
    from bistar_gp.model import build_mauna_loa_kernels, build_likelihood, apply_hp_value
    from bistar_gp.fit import fit_map, sample_prior, _map_init_values, _hmc_pyro_model
    try:
        from bistar_gp.fit import DEFAULT_JITTER
    except ImportError:
        DEFAULT_JITTER = 1e-6

    # ── data + provenance ────────────────────────────────────────────
    x_train, y_train, x_test, y_test, info = load_mauna_loa(normalize=True, test_years=5.0)
    N_full = len(x_train)
    res["provenance"] = {
        "openml_data_id": 41187,
        "n_train_months": int(N_full),
        "n_test_months": int(len(x_test)),
        "y_mean_ppm": float(info["y_mean"]),
        "y_std_ppm": float(info["y_std"]),
        "x_offset_years": float(info["x_offset"]),
        "x_train_min": float(x_train.min()), "x_train_max": float(x_train.max()),
        "span_years": float(x_train.max() - x_train.min()),
    }
    if args.scale == "sub":
        try:
            from sklearn.datasets import fetch_openml
            co2 = fetch_openml(data_id=41187, as_frame=True)
            df = co2.frame
            cols = {c.lower(): c for c in df.columns}
            cc = cols.get("average") or cols.get("co2")
            vals = df[cc].astype(float).values if cc else None
            res["provenance"]["raw_rows_prefilter"] = int(len(df))
            res["provenance"]["raw_columns"] = [str(c) for c in df.columns]
            res["provenance"]["raw_rows_post_co2_gt0"] = int((df[cc].astype(float) > 0).sum()) if cc else None
            if vals is not None:
                res["provenance"]["sha256_co2_column"] = hashlib.sha256(
                    np.ascontiguousarray(vals).tobytes()).hexdigest()
            det = getattr(co2, "details", None) or {}
            res["provenance"]["openml_version"] = det.get("version")
            res["provenance"]["openml_name"] = det.get("name")
        except Exception as e:
            res["provenance"]["raw_fetch_error"] = repr(e)[:200]
    dump()

    # ── scale selection: whole-span, season-preserving even-index design ──
    if args.scale == "sub":
        idx = np.round(np.linspace(0, N_full - 1, 150)).astype(int)
        x_use, y_use = x_train[idx], y_train[idx]
        months = ((((x_use.numpy() + info["x_offset"]) % 1.0) * 12).round().astype(int)) % 12
        res["sub_design"] = {
            "rule": "np.linspace over indices, 150 points, whole span",
            "n": int(len(x_use)),
            "stride_months_mean": float(np.mean(np.diff(x_use.numpy())) * 12),
            "unique_calendar_months_covered": int(len(set(months.tolist()))),
            "span_years": float(x_use.max() - x_use.min()),
        }
    else:
        x_use, y_use = x_train, y_train
    N = int(len(x_use))
    res["N"] = N
    dump()

    # ── MAP fit ──────────────────────────────────────────────────────
    kernels, names = build_mauna_loa_kernels()
    likelihood = build_likelihood()
    model, likelihood = build_model(x_use, y_use, kernels, names, likelihood)
    n_iter_map = 300
    t0 = time.perf_counter()
    fit_map(model, likelihood, x_use, y_use, n_iter=n_iter_map, lr=0.02, verbose=False)
    t_map = time.perf_counter() - t0
    res["map_fit"] = {"n_iter": n_iter_map, "total_s": t_map, "per_iter_s": t_map / n_iter_map}
    res["map_noise_variance_normalized"] = float(likelihood.noise.item())
    res["map_hyperparameters"] = {
        name: float(closure(module).detach().reshape(-1)[0])
        for name, module, prior, closure, _ in model.named_priors()
    }
    dump()

    # ── unconstrained potential via initialize_model (fit_hmc_laplace path) ──
    from pyro.infer.mcmc.util import initialize_model
    from pyro.infer.autoguide.initialization import init_to_value

    model.train(); likelihood.train()
    pyro.clear_param_store()
    map_vals = _map_init_values(model)  # keep to restore after prior-eval loop
    t0 = time.perf_counter()
    init_params, potential_fn, transforms, _ = initialize_model(
        partial(_hmc_pyro_model, model), model_args=(x_use, y_use),
        init_strategy=init_to_value(values=map_vals))
    res["initialize_model_s"] = time.perf_counter() - t0

    sites = sorted(init_params)
    res["sampled_sites"] = sites
    res["n_sampled_sites"] = len(sites)
    res["period_length_sampled"] = any("period" in s for s in sites)

    shapes = {s: init_params[s].reshape(-1).shape[0] for s in sites}
    u_map = torch.cat([init_params[s].reshape(-1).double() for s in sites])
    res["dim_unconstrained"] = int(len(u_map))

    def unflatten(u):
        out, i = {}, 0
        for s in sites:
            n = shapes[s]
            out[s] = u[i:i + n].reshape(init_params[s].shape)
            i += n
        return out

    def potential_u(u):
        with gpytorch.settings.cholesky_jitter(DEFAULT_JITTER):
            return potential_fn(unflatten(u))

    res["logjoint"] = timed(lambda: potential_u(u_map.clone()), reps=5)
    dump()

    def grad_eval():
        u = u_map.clone().requires_grad_(True)
        p = potential_u(u)
        torch.autograd.grad(p, u)

    res["gradient"] = timed(grad_eval, reps=5)
    dump()

    # ── Hessian (budget-guarded) ─────────────────────────────────────
    est_hess = res["gradient"]["median_s"] * len(u_map) * 6
    if remaining() > max(3 * est_hess, 30.0):
        t0 = time.perf_counter()
        H = torch.autograd.functional.hessian(potential_u, u_map.clone())
        t_hess = time.perf_counter() - t0
        H = 0.5 * (H + H.T)
        eig = torch.linalg.eigvalsh(H)
        res["hessian"] = {
            "time_s": t_hess,
            "eigenvalues": [float(v) for v in eig],
            "min_eig": float(eig.min()), "max_eig": float(eig.max()),
            "spd": bool(eig.min() > 0),
            "n_below_1e-6_floor": int((eig < 1e-6).sum()),
            "condition_number_after_floor": float(eig.max() / max(float(eig.min()), 1e-6)),
        }
    else:
        res["hessian"] = {"skipped_for_budget": True, "extrapolated_from_gradient_s": est_hess}
    dump()

    # ── prior-proposal evals ─────────────────────────────────────────
    draws = sample_prior(model, n_samples=1000, seed=0)
    site_names = list(draws.keys())
    mll = gpytorch.mlls.ExactMarginalLogLikelihood(likelihood, model)
    model.train(); likelihood.train()

    def eval_draw(i):
        for k in site_names:
            apply_hp_value(model, likelihood, k, torch.tensor(float(draws[k][i])))
        with gpytorch.settings.cholesky_jitter(DEFAULT_JITTER):
            out = model(x_use)
            return float(mll(out, y_use).item())

    n_fail = 0
    for i in range(3):  # warmup
        try:
            eval_draw(i)
        except Exception:
            pass
    t0 = time.perf_counter()
    for i in range(100):
        try:
            eval_draw(i)
        except Exception:
            n_fail += 1
    t100 = time.perf_counter() - t0
    res["prior_eval_100"] = {"total_s": t100, "per_eval_s": t100 / 100, "n_failed": n_fail}
    dump()

    if remaining() > 10 * t100 * 1.3 + 30.0:
        n_fail2 = 0
        t0 = time.perf_counter()
        for i in range(1000):
            try:
                eval_draw(i)
            except Exception:
                n_fail2 += 1
        t1000 = time.perf_counter() - t0
        res["prior_eval_1000"] = {"total_s": t1000, "per_eval_s": t1000 / 1000,
                                  "n_failed": n_fail2, "measured": True}
    else:
        res["prior_eval_1000"] = {"total_s": 10 * t100, "measured": False,
                                  "note": "linear extrapolation from 100 evals (budget guard)"}
    dump()

    # ── profile-Laplace grid point: freeze noise off-MAP, re-optimize rest ──
    for k, v in map_vals.items():
        apply_hp_value(model, likelihood, k, v)
    likelihood.noise = float(res["map_noise_variance_normalized"]) * 2.0
    likelihood.noise_covar.raw_noise.requires_grad_(False)
    free_params = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.Adam(free_params, lr=0.02)
    n_prof = 150
    t0 = time.perf_counter()
    for _ in range(n_prof):
        opt.zero_grad()
        with gpytorch.settings.cholesky_jitter(DEFAULT_JITTER):
            out = model(x_use)
            loss = -mll(out, y_use)
        loss.backward()
        opt.step()
    t_prof = time.perf_counter() - t0
    likelihood.noise_covar.raw_noise.requires_grad_(True)
    hess_s = res["hessian"].get("time_s", res["hessian"].get("extrapolated_from_gradient_s", 0.0))
    res["profile_grid_point"] = {
        "profile_opt_n_iter": n_prof, "profile_opt_total_s": t_prof,
        "profile_opt_per_iter_s": t_prof / n_prof,
        "laplace_det_bound_s": hess_s,
        "composite_per_point_est_s": t_prof + hess_s,
        "note": "6-of-7-site profile via frozen raw_noise; Laplace-det cost bounded "
                "by the measured 7-dim Hessian time",
    }
    dump()

    # ── single-thread retiming (Della-comparison anchor) ─────────────
    if args.scale == "full" and remaining() > 30.0:
        torch.set_num_threads(1)
        st = {"logjoint": timed(lambda: potential_u(u_map.clone()), reps=3),
              "gradient": timed(grad_eval, reps=3)}
        t0 = time.perf_counter()
        for i in range(10):
            try:
                eval_draw(i)
            except Exception:
                pass
        st["prior_eval_per_eval_s"] = (time.perf_counter() - t0) / 10
        res["single_thread"] = st
        torch.set_num_threads(res["torch_threads_default"])
    dump()
    print(json.dumps({k: v for k, v in res.items()
                      if k in ("scale", "N", "n_sampled_sites", "elapsed_s")}))


if __name__ == "__main__":
    main()
