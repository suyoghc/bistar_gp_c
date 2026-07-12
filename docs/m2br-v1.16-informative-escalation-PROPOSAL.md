# M2bR v1.16 — informative-only validation escalation (PROPOSED, awaiting author vote; NOT executed)

Status: **PROPOSED — awaiting the author's explicit vote. NO chain has been launched; no sampler
has run for this addendum.** This is a bounded, one-shot escalation of the informative validation
cells (V1/V2) that FAILED under the D33 4×2000 design, prepared per author direction (2026-07-12).
It changes ONLY the per-chain warmup/draw budget; it does not touch the frozen starts, seeds,
acceptance thresholds, authority reference, model, target, or metric. Ratification is the author's;
on a yes vote a new manifest addendum (v1.16) pins the exact parameters before any launch.

## Why (D33 failure signature — informative, td7; td10 ≡ td7 so it is dropped)

Four criteria missed, all marginal; per-chain diagnostics (V1):

| chain (start) | seed | fit s | acc rate | step size | divergences | occ hi |
|---|---|---|---|---|---|---|
| 0 (MAP) | 0 | 155.9 | 0.9975 | 0.176 | 0 | 0.721 |
| 1 (median lo) | 1 | 123.2 | 0.9865 | 0.220 | 2 | 0.588 |
| 2 (median mid) | 2 | 93.6 | 0.909 | **0.332** | **6** | 0.567 |
| 3 (median hi) | 3 | 178.5 | 0.9975 | 0.150 | 0 | 0.593 |

- **Divergences:** pooled 8/8000 = 0.001 (need < 0.001). Concentrated in chain 2, whose step size
  (0.332) is ~2× the other chains' — an under-adapted warmup. Longer warmup is the direct lever.
- **Bulk-ESS:** lengthscale 378.5 / noise 382.2 (need > 400) — ~6% short; scales ~linearly with draws.
- **R-hat:** max 1.0114 (need < 1.01) — converges to 1 with more draws + better mixing.
- **Per-chain occupancy hi-band deviation:** 0.104 (need ≤ 0.05). Chain-2 hi 0.567 vs chain-0 hi
  0.721 is a ~6-SE gap given bulk-ESS ≈ 380/chain — genuine incomplete mixing across the multi-basin
  informative posterior, not MC noise. This is the HARDEST criterion and the one most at risk.

Measured cost anchor: mean per-chain fit ≈ 137.8 s for 3000 iterations (1000 warmup + 2000 draws)
= **≈ 45.9 ms/iteration** on this host (10 threads).

## Design (frozen for the escalation; UNCHANGED unless listed)

- **Config/cells:** `informative` only, **td7 only** (informative td7 ≡ td10 in D33 — the depth cap
  never binds — so td10 adds nothing). One cell.
- **Starts + seeds:** the SAME four frozen manifest v1.14 informative starts, semantic-sha256-verified
  before injection (chain 0 MAP `72a7e891…`, chain 1 median-lo `c9f37584…`, chain 2 median-mid
  `2db18020…`, chain 3 median-hi `5cf298a7…`), seeds 0/1/2/3. No re-selection, no new starts.
- **CHANGED — per-chain budget (the only change):**
  - warmup **3000** (was 1000) — 3× to fix step-size adaptation (chain-2 under-adaptation → divergences)
    and improve mixing;
  - draws **8000** (was 2000) — 4× to lift bulk-ESS clear of 400 (≈1500 projected), drive R-hat → 1,
    and halve the per-chain occupancy MC error (0.104 → target ~0.05).
- **UNCHANGED:** target acceptance 0.8; `fit_hmc_e1` E1 target; the 4-site toy model; the frozen toy
  data; MAP-init procedure; 200 predictives/chain; R-B pooled primary estimator (now pooled 4×200=800,
  identical rule); ALL acceptance thresholds (rank R-hat < 1.01 every site; bulk+tail ESS > 400 pooled;
  per-chain occupancy dev ≤ 0.05; divergence < 0.1%; saturation < 10%; NotPSD gate); the authority
  reference (prior-IS pooled 0.2768/0.1310/0.5922) and the authority-coverage criterion.
- **Implementation:** reuse `experiments/m2br_validation_run.py`'s frozen-start injection + acceptance
  machinery with the escalated warmup/draws, gated behind a NEW `--execute` + the v1.16 addendum and a
  fresh output namespace `runs/m2br_v116_informative/` (untracked). No new sampler code; HMC only via
  `fit_hmc_e1`. To be built and hermetically tested BEFORE launch, same as the D33 drivers.

## Budget (fixed; stop-and-report, identical mechanics to the audit §4 / validation)

Per-chain: (3000 + 8000) × 45.9 ms ≈ **505 s ≈ 8.4 min** sampling + ≈ 120 s MAP/scoring/diagnostics
≈ **10.5 min/chain**. Four chains sequential ≈ **42 min**. The informative geometry's leapfrog counts
grow with draws, so budget conservatively: **CEILING 90 min local wall, 600 s reserve**, one monotonic
clock, per-chain projection gate, absolute cutoff, samples-last atomic persist. **One final
stop-and-report outcome. No in-run extension.**

## Decision rule (one shot)

- **PASS** (all criteria, incl. occupancy ≤ 0.05 and divergence < 0.001): the informative corrected
  numbers become eligible to SUPERSEDE the withdrawn 0.673 headline; W2's informative
  prior-misspecification case study is updated (a further author decision).
- **FAIL** (any criterion): the informative numbers stay WITHDRAWN/UNVALIDATED. The next step is then a
  STRATEGY change (reparameterization, a tuned mass matrix, or a different sampler) proposed as a
  further addendum — **not** another budget bump. This escalation is the last "same-strategy, longer-run"
  attempt; success is NOT guaranteed because the 0.104 spread may reflect genuine multi-basin
  non-mixing that a longer same-strategy run cannot resolve.

## Explicitly out of scope

`vague` and `gamma_relaxed` get NO validation cell (gamma_relaxed attribution-only; vague optional
appendix robustness). No VI/`hmc_laplace`/Mauna/profile-Laplace. td10 informative. Any G-toy/M2c work.
No sampler runs until the author votes yes and the v1.16 manifest addendum is pinned.
