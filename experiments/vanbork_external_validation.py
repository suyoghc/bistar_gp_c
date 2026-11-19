"""
External validation of the BI*/BMS* scoring machinery against two closed-form
model probabilities published by van Bork, Romeijn & Wagenmakers (2025,
Synthese, doi:10.1007/s11229-025-05286-y), Section 4.

Both targets are derived there from Rosenkrantz-style expected support against
a "data prior", with no reference to this implementation. They therefore serve
as independent ground truth for the induced-prior / soft-transfer half of the
framework (the GP scaffold is not exercised: in both cases the paper GIVES the
data prior, so we supply it directly and test the scoring).

TARGET A — non-overlapping point models (their two-point example).
  Data prior: mass 4/10 on s/n -> 0.16, mass 6/10 on s/n -> 0.19.
  Models:     M1: theta = 0.15,  M2: theta = 0.20.
  Their answer: p(M1) = 0.4, p(M2) = 0.6, argued via asymptotic posterior
  model probabilities that go to 0/1 under each data-prior atom.
  Our route: Boltzmann soft transfer p(M) ∝ sum_i w_i exp(-G(psi_i, M)/tau)
  with G the Bernoulli KL. Tests the tau -> 0 (hard-partition) limit.

TARGET B — completely overlapping models (their beta example, Fig. 1).
  Data prior: point mass on s/n -> 1/2.
  Models:     M_x: theta ~ beta(50,50),  M_z: theta ~ beta(2,2).
  Their answer: the normalized ratio of prior densities at the MLE,
  7.96 / (7.96 + 1.50) ~= 0.84 for M_x.
  Our route: the HYBRID form of the induced model prior,
      Z_M = integral p_M(theta) exp(-Gbar(theta)/tau) d theta,
  i.e. Z_M with a within-model parameter prior in place of the Lebesgue /
  V_ref reference measure. This is the "data prior + parameter hyperprior
  hybrid" listed as an open question in CogSci Poster/OPEN_QUESTIONS.md; the
  paper supplies a target number for it.

  Analytic expectation: as tau -> 0, Laplace gives
      Z_M ~= p_M(theta*) sqrt(2 pi tau / G''(theta*)),
  and since both models share the Bernoulli family, G and G'' are identical
  across them, so the Hessian factor cancels and the normalized Z ratio
  converges to the ratio of prior densities at theta* = 1/2 -- exactly their
  formula. Their result is thus the tau -> 0, shared-family, point-data-prior
  special case of Z_M.

Run from the repo root:
    python experiments/vanbork_external_validation.py
"""

import os, json, datetime

import numpy as np
from scipy.stats import beta as beta_dist

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(REPO, "runs", "vanbork_external_validation")

TAUS = [1.0, 0.1, 0.01, 1e-3, 1e-4, 1e-5, 1e-6, 1e-7]


def kl_bernoulli(p, q, eps=1e-300):
    """KL( Bern(p) || Bern(q) ) in nats."""
    p = np.clip(p, eps, 1 - eps)
    q = np.clip(q, eps, 1 - eps)
    return p * np.log(p / q) + (1 - p) * np.log((1 - p) / (1 - q))


def softmax_weights(neg_energies):
    m = np.max(neg_energies)
    w = np.exp(neg_energies - m)
    return w / w.sum()


# ── TARGET A ──────────────────────────────────────────────────────────
def target_a():
    psi_atoms = np.array([0.16, 0.19])      # limiting relative frequencies
    psi_mass = np.array([0.4, 0.6])         # the paper's data prior
    models = {"M1 (theta=0.15)": 0.15, "M2 (theta=0.20)": 0.20}
    names = list(models)
    thetas = np.array([models[n] for n in names])

    # G[i, j] = divergence from data-prior atom i to model j
    G = np.array([[kl_bernoulli(p, t) for t in thetas] for p in psi_atoms])

    rows_pooled, rows_perdraw, rows_shipped = [], [], []
    for tau in TAUS:
        # (a) pooled: sum unnormalized Boltzmann contributions, normalize once
        contrib = psi_mass[:, None] * np.exp(-(G - G.min()) / tau)
        pooled = contrib.sum(axis=0)
        pooled = pooled / pooled.sum()
        rows_pooled.append({"tau": tau,
                            **{n: float(v) for n, v in zip(names, pooled)}})

        # (b) per-draw: normalize each atom's Boltzmann weights into a posterior
        #     over models FIRST, then average with the data-prior mass. This is
        #     the paper's Eq. 4, prior model probability = expected posterior.
        per_atom = np.exp(-(G - G.min(axis=1, keepdims=True)) / tau)
        per_atom = per_atom / per_atom.sum(axis=1, keepdims=True)
        perdraw = (psi_mass[:, None] * per_atom).sum(axis=0)
        rows_perdraw.append({"tau": tau,
                             **{n: float(v) for n, v in zip(names, perdraw)}})

        # (c) exact shipped semantics of bms_star.soft_transfer with
        #     normalize_per_draw=True: subtract the per-row MINIMUM (no row
        #     renormalization), weight by atom mass, then normalize once.
        shipped = (psi_mass[:, None] *
                   np.exp(-(G - G.min(axis=1, keepdims=True)) / tau)).sum(axis=0)
        shipped = shipped / shipped.sum()
        rows_shipped.append({"tau": tau,
                             **{n: float(v) for n, v in zip(names, shipped)}})
    return {"names": names, "target": {"M1 (theta=0.15)": 0.4,
                                       "M2 (theta=0.20)": 0.6},
            "G": G.tolist(), "rows": rows_perdraw,
            "rows_pooled": rows_pooled, "rows_perdraw": rows_perdraw,
            "rows_shipped_npd_true": rows_shipped}


# ── TARGET B ──────────────────────────────────────────────────────────
def target_b():
    psi_star = 0.5                          # data prior: spike at s/n -> 1/2
    priors = {"M_x beta(50,50)": (50.0, 50.0), "M_z beta(2,2)": (2.0, 2.0)}
    names = list(priors)

    # their published densities at the MLE and the resulting weight
    dens = {n: float(beta_dist.pdf(psi_star, a, b))
            for n, (a, b) in priors.items()}
    dens_ratio_weight = dens[names[0]] / (dens[names[0]] + dens[names[1]])

    # hybrid Z_M = ∫ p_M(theta) exp(-G(theta)/tau) d theta, on a fine grid
    # union of a coarse global grid and a dense grid around theta*,
    # so the exp(-G/tau) peak (width ~ sqrt(tau)/2) stays resolved
    theta = np.unique(np.concatenate([
        np.linspace(1e-6, 1 - 1e-6, 200001),
        psi_star + np.linspace(-0.02, 0.02, 400001),
    ]))
    theta = theta[(theta > 0) & (theta < 1)]
    G = kl_bernoulli(psi_star, theta)       # same G for both models
    rows = []
    for tau in TAUS:
        integrand_core = np.exp(-(G - G.min()) / tau)
        Z = {}
        for n, (a, b) in priors.items():
            trapz = getattr(np, "trapezoid", np.trapz)
            Z[n] = float(trapz(beta_dist.pdf(theta, a, b) * integrand_core,
                               theta))
        tot = sum(Z.values())
        rows.append({"tau": tau, **{n: Z[n] / tot for n in names}})
    return {"names": names,
            "published_densities_at_mle": dens,
            "published_weight_Mx": dens_ratio_weight,
            "target": {names[0]: dens_ratio_weight,
                       names[1]: 1 - dens_ratio_weight},
            "rows": rows}


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    a, b = target_a(), target_b()

    print("=" * 74)
    print("TARGET A — non-overlapping point models (paper: 0.4 / 0.6)")
    print("=" * 74)
    print(f"  divergences G[atom, model]:\n{np.array(a['G'])}")
    for label, key in [("(a) POOLED  (sum, then normalize once)", "rows_pooled"),
                       ("(b) PER-DRAW (normalize per atom, then average) "
                        "= paper Eq. 4", "rows_perdraw"),
                       ("(c) SHIPPED soft_transfer, normalize_per_draw=True",
                        "rows_shipped_npd_true")]:
        print(f"\n  {label}")
        print("    tau".ljust(14) + "".join(n.ljust(22) for n in a["names"]))
        for r in a[key]:
            print(f"    {r['tau']:<10.3g}" +
                  "".join(f"{r[n]:<22.6f}" for n in a["names"]))
        print("    paper target:".ljust(14) +
              "".join(f"{a['target'][n]:<22.6f}" for n in a["names"]))

    print()
    print("=" * 74)
    print("TARGET B — completely overlapping beta models (paper: ~0.84 / 0.16)")
    print("=" * 74)
    print("  prior densities at MLE 0.5:",
          {k: round(v, 4) for k, v in b["published_densities_at_mle"].items()},
          "(paper quotes 7.96 and 1.50)")
    print(f"  paper weight for M_x: {b['published_weight_Mx']:.6f}")
    hdr = "  tau".ljust(12) + "".join(n.ljust(22) for n in b["names"])
    print(hdr)
    for r in b["rows"]:
        print(f"  {r['tau']:<10.3g}" +
              "".join(f"{r[n]:<22.6f}" for n in b["names"]))
    print("  paper target:".ljust(12) +
          "".join(f"{b['target'][n]:<22.6f}" for n in b["names"]))

    # convergence report
    a_err = abs(a["rows"][-1][a["names"][0]] - a["target"][a["names"][0]])
    b_err = abs(b["rows"][-1][b["names"][0]] - b["target"][b["names"][0]])
    print()
    print(f"  |ours - paper| at tau={TAUS[-1]}:  A = {a_err:.2e}   B = {b_err:.2e}")

    out = {"source": "van Bork, Romeijn & Wagenmakers 2025, Synthese, "
                     "doi:10.1007/s11229-025-05286-y, Section 4",
           "generated": datetime.date.today().isoformat(),
           "taus": TAUS, "target_a": a, "target_b": b,
           "abs_error_at_min_tau": {"A": a_err, "B": b_err}}
    with open(os.path.join(OUT_DIR, "results.json"), "w") as f:
        json.dump(out, f, indent=2)
    print("\nSaved:", os.path.join(OUT_DIR, "results.json"))


if __name__ == "__main__":
    main()
