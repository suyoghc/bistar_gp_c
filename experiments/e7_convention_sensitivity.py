"""
E7 — aggregation-convention sensitivity on the VALIDATED toy path (WP0b).

Question (D60 fork): the shipped soft-transfer default pools unnormalized
Boltzmann contributions across GP draws (`normalize_per_draw=False`); van Bork,
Romeijn & Wagenmakers' Eq. 4 semantics (prior model probability = expected
posterior across the data prior) instead demand normalizing each draw into a
posterior over models BEFORE averaging. D60 showed the default fails their
Target A while the per-draw variants reproduce it. This experiment measures how
much the PAPER-FACING toy numbers move across three aggregation variants, so
the author can decide the fork with the cost in view.

Validated basis (M2bR banner + W4/W7): `toy_elicited` config, SIR-resampled
predictives from the pooled 3-seed prior-IS draws — the exact machinery of
`experiments/prior_sensitivity_study.py` stage IS (functions imported from it,
same seeds, same subsample conventions; SIR headline at tau=1 is 0.441). No
withdrawn HMC anywhere.

Variants, applied to the SAME G matrices:
  (a) pooled      — shipped default (`_boltzmann_posterior`): mean of
                    exp(-G/tau) over draws, normalize once.
  (b) rowmin      — shipped `soft_transfer(..., normalize_per_draw=True)`:
                    subtract per-draw min G, then as (a).
  (c) expected-posterior — van Bork Eq. 4: normalize each draw's Boltzmann
                    weights into a posterior over models, then average.

Metrics: pw_kl_vcal (W1 primary) + kl_forward (W1 appendix). Taus: the study's
grid. Outputs: runs/e7_convention_sensitivity/{results.json, README.md}.

Run from the repo root:
    python experiments/e7_convention_sensitivity.py
"""

import os, sys, json, datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import torch

torch.set_default_dtype(torch.float64)

import prior_sensitivity_study as pss
import fit_method_metric_comparison as fmc
from bistar_gp import generate_toy_data
from bistar_gp.candidates import build_toy_candidates

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(REPO, "runs", "e7_convention_sensitivity")

CONFIG = "toy_elicited"
IS_SEEDS = [0, 1, 2]
N_PRED = 1000                      # matches the ratified SIR headline run
METRICS = ["pw_kl_vcal", "kl_forward"]
REPORT_TAUS = ["0.1", "0.3", "1.0", "3.0", "10.0"]


def aggregate(G, tau, variant):
    """Three aggregation conventions over the same (n_draws x n_models) G."""
    if variant == "pooled":                       # shipped default
        return pss._boltzmann_posterior(G, tau)
    if variant == "rowmin":                       # shipped npd=True semantics
        Ge = G - G.min(axis=1, keepdims=True)
        return pss._boltzmann_posterior(Ge, tau)
    if variant == "expected_posterior":           # van Bork Eq. 4
        lw = -(G - G.min(axis=1, keepdims=True)) / tau
        w = np.exp(lw)
        w = w / w.sum(axis=1, keepdims=True)      # per-draw posterior
        s = w.mean(axis=0)                        # equal-weight data prior
        return s / s.sum()
    raise ValueError(variant)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    # ── Data + candidates: the study's exact conventions ───────────
    x, y, _ = generate_toy_data()                 # thesis toy: N=20 defaults
    x_np, y_np = x.numpy(), y.numpy()
    x_eval = torch.tensor(
        np.linspace(x_np.min() - 1, x_np.max() + 1, 60)).double()
    candidate_results = []
    for cand in build_toy_candidates():
        cand.fit(x_np, y_np)
        candidate_results.append(cand.predict(x_eval.numpy()))
    names = [cr.name for cr in candidate_results]

    # ── SIR predictives from pooled prior-IS (validated path) ──────
    pc = pss.STUDY_CONFIGS[CONFIG]
    ths, lml = pss.load_pooled_is(CONFIG, IS_SEEDS)
    per_metric, G_by_metric, _, idx = pss._sir_bms(
        pc, x, y, x_eval, candidate_results, ths, lml, N_PRED)
    print(f"SIR draws: {len(np.unique(idx))}/{N_PRED} unique")

    # sanity anchor: the pooled pw_kl_vcal tau=1 row must reproduce the
    # ratified SIR headline (0.441 for Sin+Linear) within MC tolerance
    anchor = per_metric["pw_kl_vcal"]["posteriors"]["1.0"]
    print("anchor (pooled, pw_kl_vcal, tau=1):",
          " ".join(f"{v:.3f}" for v in anchor))

    out = {"config": CONFIG, "n_pred": N_PRED, "is_seeds": IS_SEEDS,
           "model_names": names,
           "generated": datetime.date.today().isoformat(),
           "anchor_pooled_pw_kl_vcal_tau1": anchor,
           "results": {}}

    print(f"\n{'metric':<12} {'tau':<6} {'variant':<20} " +
          " ".join(f"{n:<14}" for n in names))
    for metric in METRICS:
        G = G_by_metric[metric]
        out["results"][metric] = {}
        for tau_s in REPORT_TAUS:
            tau = float(tau_s)
            out["results"][metric][tau_s] = {}
            for variant in ("pooled", "rowmin", "expected_posterior"):
                post = aggregate(G, tau, variant)
                out["results"][metric][tau_s][variant] = [float(v)
                                                          for v in post]
                print(f"{metric:<12} {tau_s:<6} {variant:<20} " +
                      " ".join(f"{v:<14.4f}" for v in post))
        # max movement across variants, per tau
        mv = {t: float(np.max(np.abs(
                np.array(out["results"][metric][t]["pooled"]) -
                np.array(out["results"][metric][t]["expected_posterior"]))))
              for t in REPORT_TAUS}
        out["results"][metric]["max_abs_movement_pooled_vs_eqp"] = mv
        print(f"{metric}: max |pooled - expected_posterior| by tau: " +
              ", ".join(f"{t}: {v:.4f}" for t, v in mv.items()))

    with open(os.path.join(OUT_DIR, "results.json"), "w") as f:
        json.dump(out, f, indent=2)
    print("\nSaved:", os.path.join(OUT_DIR, "results.json"))


if __name__ == "__main__":
    main()
