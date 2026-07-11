"""D19 M2b real-data E1 NUTS microbenchmark (plan 1.2/A6; addenda v1.2, v1.3).

Replaces the kernel-cost proxy rows of `docs/plan-d19-mauna.md` section 1.2
(marked "PENDING the M2b E1 NUTS microbenchmark") with measured numbers, per
milestone M2b (plan section 4) and decision A6 (section 7). Two measurement
families per scale: (1) per-evaluation cost of the S1 oracle potential
against the E1 direct potential, value and value+gradient, which checks the
~200x deep-copy overhead claim E1 exists to remove; (2) short td7 NUTS runs
on both paths, priced in wall milliseconds per sampling-stage leapfrog. The
S1 pyro path runs only at the smallest requested scale because A6 confines
it to sub-150 work; S1f runs at every scale.

Persistence firewall (prereg addendum v1.2, point 6; a preregistration
constraint, not a style choice): this script persists and prints ONLY timing
fields, potential-evaluation counts/costs, and leapfrog counts. Posterior
samples, hyperparameter values (MAP included), divergences, acceptance
rates, step sizes, R-hat/ESS, and every other per-site or scientific
diagnostic are discarded unread. Concretely: all fits run verbose=False, no
mcmc summary is ever called, sample dicts are deleted without reading their
values, and of each SamplerDiagnostics record only the leapfrog_counts
field is consumed. The benchmark prices a leapfrog; it never previews a
posterior (plan section 6.5 ordering/blinding).

Addendum v1.3 caveat carried by every S1-vs-S1f number here: both paths
share the corrected single-count target, but the S1 oracle's autograd omits
the likelihood contribution for kernel-hyperparameter coordinates (v1.3
Finding 2). Cost-per-leapfrog stays well-defined for both paths;
cost-per-effective-draw comparisons must cite that addendum.

Data: the training-only loader (`load_mauna_loa_training`; the v1.1
holdout-seal note governs), normalized inside the loader on training-span
statistics exactly as `experiments/d19_bench.py` consumes it. Sub-scales use
that script's whole-span, season-preserving even-index design
(np.linspace over indices). --synthetic swaps in a synthetic monthly fixture
for mechanics validation only; in that mode nothing is persisted.
"""

import argparse
import json
import os
import platform
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch

torch.set_default_dtype(torch.float64)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = REPO_ROOT / "runs" / "d19_planning" / "e1_nuts_microbench.json"

FIREWALL_NOTE = ("prereg v1.2 point 6: timing, potential-evaluation and "
                 "leapfrog-count fields only; samples and scientific "
                 "diagnostics discarded unread")
LEAPFROG_CAVEAT = "warmup is inside the wall time"

# A6 (plan section 7): the S1 pyro path is approved for sub-150 work only,
# so the microbenchmark refuses to launch it at any larger scale.
S1_MAX_SCALE = 150


def timed_ms(fn, reps, warmup=3):
    """Median and mean wall milliseconds per call, after warmup calls.

    Return values of fn are discarded: only clock readings leave this
    function (the v1.2 point-6 firewall).
    """
    for _ in range(warmup):
        fn()
    ts = []
    for _ in range(reps):
        t0 = time.perf_counter()
        fn()
        ts.append(time.perf_counter() - t0)
    return {"median_ms": float(np.median(ts) * 1e3),
            "mean_ms": float(np.mean(ts) * 1e3),
            "reps": int(reps), "warmup_calls": int(warmup)}


def select_scale(x_full, y_full, n):
    """The d19_bench sub-scale rule: whole-span, season-preserving
    even-index subsample (np.round(np.linspace) over indices); the full set
    passes through untouched."""
    n_full = len(x_full)
    if n == n_full:
        return x_full, y_full
    idx = np.round(np.linspace(0, n_full - 1, n)).astype(int)
    return x_full[idx], y_full[idx]


def synthetic_monthly_fixture(n_months, seed):
    """Monthly CO2-shaped fixture (trend + seasonal + noise) for mechanics
    validation only; it carries no Mauna data. Normalization mirrors the real
    loader's convention: y standardized and x mean-centered on the span."""
    rng = np.random.default_rng(seed)
    x_years = np.arange(n_months, dtype=float) / 12.0
    y_ppm = (315.0 + 1.4 * x_years + 0.012 * x_years ** 2
             + 3.0 * np.sin(2.0 * np.pi * x_years)
             + rng.normal(0.0, 0.3, n_months))
    y = (y_ppm - y_ppm.mean()) / y_ppm.std()
    x = x_years - x_years.mean()
    return torch.tensor(x).double(), torch.tensor(y).double()


def collect_meta():
    def module_version(name):
        try:
            import importlib
            return importlib.import_module(name).__version__
        except Exception:
            return None

    try:
        sha = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT,
            capture_output=True, text=True, timeout=10).stdout.strip() or None
    except Exception:
        sha = None
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git_sha": sha,
        "torch": torch.__version__,
        "gpytorch": module_version("gpytorch"),
        "pyro": module_version("pyro"),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "torch_num_threads": torch.get_num_threads(),
        "cpu_count": os.cpu_count(),
        "hostname": platform.node(),
    }


def measure_per_eval(e1, reps):
    """Per-evaluation timings at the MAP init point: S1 oracle vs E1, value
    and value+gradient (one leapfrog's work), plus the oracle/E1 ratios.

    potential_grad toggles requires_grad on the state tensors in place, so
    every call receives a fresh clone of the init state; the clone happens
    inside the timed region for all four measurements symmetrically (seven
    scalar clones, negligible against a Cholesky).
    """
    from pyro.ops.integrator import potential_grad

    def fresh_u():
        return {s: v.detach().clone() for s, v in e1.init_params.items()}

    # Fail loudly on a broken potential, without the value reaching stdout
    # or the JSON (firewall: the message carries no number).
    for label, fn in (("oracle", e1.oracle_potential_fn), ("e1", e1.potential_fn)):
        if not bool(torch.isfinite(fn(fresh_u()))):
            raise RuntimeError(f"{label} potential non-finite at the MAP init point")

    res = {
        "oracle_value": timed_ms(lambda: e1.oracle_potential_fn(fresh_u()), reps),
        "e1_value": timed_ms(lambda: e1.potential_fn(fresh_u()), reps),
        "oracle_value_grad": timed_ms(
            lambda: potential_grad(e1.oracle_potential_fn, fresh_u()), reps),
        "e1_value_grad": timed_ms(
            lambda: potential_grad(e1.potential_fn, fresh_u()), reps),
    }
    res["ratio_oracle_over_e1_value"] = float(
        res["oracle_value"]["median_ms"] / res["e1_value"]["median_ms"])
    res["ratio_oracle_over_e1_grad"] = float(
        res["oracle_value_grad"]["median_ms"] / res["e1_value_grad"]["median_ms"])
    return res


def nuts_record(wall_s, diagnostics, args):
    """Timing and leapfrog fields for one NUTS run. Of the diagnostics
    record, ONLY leapfrog_counts is read (v1.2 point 6); every other field
    stays untouched and the object is dropped by the caller."""
    counts = diagnostics.leapfrog_counts
    rec = {
        "wall_s": float(wall_s),
        "n_draws": int(args.n_samples),
        "n_warmup": int(args.n_warmup),
        "max_tree_depth": int(args.max_tree_depth),
        "seed": int(args.seed),
        "leapfrog_caveat": LEAPFROG_CAVEAT,
    }
    if counts is None:
        # Honesty contract passthrough: no count, no fabricated cost.
        rec["sampling_leapfrogs_per_draw"] = None
        rec["total_sampling_leapfrogs"] = None
        rec["wall_ms_per_leapfrog_incl_warmup_overhead"] = None
    else:
        per_draw = [int(c) for c in counts[0]]
        total = int(sum(per_draw))
        rec["sampling_leapfrogs_per_draw"] = per_draw
        rec["total_sampling_leapfrogs"] = total
        rec["wall_ms_per_leapfrog_incl_warmup_overhead"] = (
            1000.0 * wall_s / total if total > 0 else None)
    return rec


def run_s1f(model, likelihood, x, y, args):
    """S1f: NUTS on the E1 potential (fit_hmc_e1), timing fields only."""
    from bistar_gp.e1_potential import fit_hmc_e1

    t0 = time.perf_counter()
    samples, diagnostics = fit_hmc_e1(
        model, likelihood, x, y,
        n_samples=args.n_samples, n_warmup=args.n_warmup, verbose=False,
        seed=args.seed, max_tree_depth=args.max_tree_depth,
        return_diagnostics=True)
    wall_s = time.perf_counter() - t0
    del samples  # firewall: discarded unread (v1.2 point 6)
    rec = nuts_record(wall_s, diagnostics, args)
    del diagnostics
    return rec


def run_s1(model, likelihood, x, y, args):
    """S1: NUTS on the pyro traced path (fit_hmc), timing fields only."""
    from bistar_gp.fit import fit_hmc

    t0 = time.perf_counter()
    samples, diagnostics = fit_hmc(
        model, likelihood, x, y,
        n_samples=args.n_samples, n_warmup=args.n_warmup, verbose=False,
        seed=args.seed, init_to_map=True, max_tree_depth=args.max_tree_depth,
        return_diagnostics=True)
    wall_s = time.perf_counter() - t0
    del samples  # firewall: discarded unread (v1.2 point 6)
    rec = nuts_record(wall_s, diagnostics, args)
    del diagnostics
    return rec


def print_scale_table(n, scale_res):
    """Plain-text table of the same timing fields the JSON carries."""
    pe = scale_res["per_eval_ms"]
    any_timing = pe["oracle_value"]
    print(f"\nscale n={n}")
    print(f"  per-eval ms (median / mean; reps={any_timing['reps']}, "
          f"warmup={any_timing['warmup_calls']})")
    rows = (("oracle_value", "S1 oracle value"),
            ("e1_value", "E1 value"),
            ("oracle_value_grad", "S1 oracle value+grad"),
            ("e1_value_grad", "E1 value+grad"))
    for key, label in rows:
        t = pe[key]
        print(f"    {label:<22}{t['median_ms']:12.3f} /{t['mean_ms']:12.3f}")
    print(f"    ratio oracle/e1       value {pe['ratio_oracle_over_e1_value']:8.1f}x"
          f"   grad {pe['ratio_oracle_over_e1_grad']:8.1f}x")
    for key, label in (("s1f", "s1f (E1 potential)"), ("s1", "s1 (pyro path)")):
        rec = scale_res["nuts"].get(key)
        if rec is None:
            continue
        total = rec["total_sampling_leapfrogs"]
        ms_lf = rec["wall_ms_per_leapfrog_incl_warmup_overhead"]
        ms_lf_txt = f"{ms_lf:.3f}" if ms_lf is not None else "n/a"
        total_txt = str(total) if total is not None else "n/a"
        print(f"  nuts {label:<20} td{rec['max_tree_depth']}, "
              f"{rec['n_warmup']}w+{rec['n_draws']}d, seed {rec['seed']}: "
              f"wall {rec['wall_s']:.2f} s, sampling leapfrogs {total_txt}, "
              f"wall ms/leapfrog (incl warmup overhead) {ms_lf_txt}")


def parse_scales(text):
    scales = []
    for tok in text.split(","):
        tok = tok.strip()
        if not tok:
            continue
        n = int(tok)
        if n not in scales:
            scales.append(n)
    if not scales:
        raise SystemExit("--scales contained no usable integers")
    return scales


def main():
    ap = argparse.ArgumentParser(
        description="D19 M2b real-data E1 NUTS microbenchmark (plan 1.2/A6; "
                    "prereg addenda v1.2 point 6, v1.3)")
    ap.add_argument("--scales", default="150,461",
                    help="comma-separated point counts; sub-scales follow the "
                         "d19_bench whole-span even-index design")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--n-warmup", type=int, default=50)
    ap.add_argument("--n-samples", type=int, default=50)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--max-tree-depth", type=int, default=7,
                    help="td7, the Mauna convention")
    ap.add_argument("--reps", type=int, default=20,
                    help="per-evaluation timing repetitions")
    ap.add_argument("--synthetic", action="store_true",
                    help="synthetic monthly fixture, mechanics validation "
                         "only; persists nothing")
    args = ap.parse_args()

    scales = parse_scales(args.scales)

    from bistar_gp.data import load_mauna_loa_training
    from bistar_gp.e1_potential import build_e1_potential
    from bistar_gp.fit import fit_map
    from bistar_gp.model import (assert_mauna_period_frozen,
                                 build_mauna_loa_kernels, build_model)

    if args.synthetic:
        x_full, y_full = synthetic_monthly_fixture(max(scales), seed=args.seed)
    else:
        # Training-only loader (v1.1 seal note); normalization happens inside
        # the loader on training-span statistics, matching d19_bench.
        x_full, y_full, _info = load_mauna_loa_training(
            normalize=True, test_years=5.0)
    n_full = len(x_full)
    bad = [n for n in scales if not (2 <= n <= n_full)]
    if bad:
        raise SystemExit(
            f"scales {bad} outside 2..{n_full} (available training months)")

    smallest = min(scales)
    result = {"meta": collect_meta(),
              "firewall_note": FIREWALL_NOTE,
              "scales": {}}

    def persist():
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with open(args.out, "w") as f:
            json.dump(result, f, indent=2)

    for n in scales:
        x_use, y_use = select_scale(x_full, y_full, n)

        kernels, names = build_mauna_loa_kernels()
        model, likelihood = build_model(x_use, y_use, kernels, names)
        assert_mauna_period_frozen(model)

        fit_map(model, likelihood, x_use, y_use, n_iter=300, verbose=False)
        assert_mauna_period_frozen(model)

        e1 = build_e1_potential(model, likelihood, x_use, y_use)
        per_eval = measure_per_eval(e1, reps=args.reps)

        nuts = {"s1f": run_s1f(model, likelihood, x_use, y_use, args)}
        assert_mauna_period_frozen(model)
        if n == smallest and n <= S1_MAX_SCALE:
            nuts["s1"] = run_s1(model, likelihood, x_use, y_use, args)
            assert_mauna_period_frozen(model)
        elif n == smallest:
            print(f"  s1 skipped: smallest scale {n} exceeds the A6 "
                  f"sub-{S1_MAX_SCALE} confinement")

        result["scales"][str(n)] = {
            "n_points": int(n),
            "per_eval_ms": per_eval,
            "nuts": nuts,
        }
        print_scale_table(n, result["scales"][str(n)])
        if not args.synthetic:
            persist()  # incremental, d19_bench style

    if args.synthetic:
        print("\nsynthetic validation OK")
    else:
        print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
