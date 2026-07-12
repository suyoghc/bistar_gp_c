# M2bR v1.16 — informative-only validation escalation (numerical protocol RATIFIED; NOT executed)

Status: **numerical protocol RATIFIED by the author (2026-07-12, D34); NO chain has been launched
and no sampler has run for this addendum.** The author ratified the exact numbers below; the
failure diagnosis and rationale were corrected (per a codex recheck) WITHOUT changing the protocol.
This is a bounded, one-shot escalation of the informative validation cells (V1/V2) that FAILED
under the D33 4×2000 design. It changes ONLY the per-chain warmup/draw budget; it does not touch
the frozen starts, seeds, acceptance thresholds, authority reference, model, target, or metric.
Before any launch, a v1.16 machine-readable pin (`docs/m2br_freeze/v116_run_plan.json`) fixes the
parameters and the driver is built, hermetically tested, and independently reviewed.

## Why (D33 failure signature — informative, td7; td10 ≡ td7 so it is dropped)

Per-chain diagnostics (V1); occupancy deviation is vs the **pooled** hi-band mass 0.6171:

| chain (start) | seed | fit s | acc rate | step size | divergences | occ hi | dev vs pooled | hi-band indicator ESS |
|---|---|---|---|---|---|---|---|---|
| 0 (MAP) | 0 | 155.9 | 0.9975 | 0.176 | 0 | 0.721 | **+0.104** | 95.6 |
| 1 (median lo) | 1 | 123.2 | 0.9865 | 0.220 | 2 | 0.588 | −0.029 | 62.6 |
| 2 (median mid) | 2 | 93.6 | 0.909 | 0.332 | **6** | 0.567 | −0.050 | 65.8 |
| 3 (median hi) | 3 | 178.5 | 0.9975 | 0.150 | 0 | 0.593 | −0.025 | 70.4 |

The four failed criteria are **not** one uniform "marginal" band; they split into two distinct
mechanisms plus two near-threshold misses:

- **Occupancy reproducibility — the material miss.** Per-chain max hi-band deviation **0.104 > 0.05**
  (need ≤ 0.05), driven by **chain 0** running high (0.721 vs pooled 0.617). This is the criterion
  that misses materially. NOTE (correction): the earlier "~6-SE gap" claim was WRONG — it treated the
  pooled noise bulk-ESS (382.2, across all four chains) as if it were per-chain. Recomputing the
  hi-band *indicator* ESS per chain gives ≈ 95.6 (chain 0) and ≈ 65.8 (chain 2), so the 0.721 vs
  0.567 difference is only **≈ 2.0 combined MCSE**. The occupancy pattern is **consistent with
  incomplete mixing but does NOT exclude ordinary finite-chain variation**; the preregistered
  criterion fails on the raw 0.104 deviation regardless of that interpretation.
- **Divergences — a distinct, chain-localized problem.** Pooled 8/8000 = 0.001 (need < 0.001),
  concentrated in **chain 2** (6 of 8; **chain 1** contributes the other 2). Chain 2's step size
  (0.332) is ~2× the others', i.e. a different adaptation outcome. This is a separate issue from the
  occupancy deviation, which chain 0 drives.
- **Bulk-ESS** lengthscale 378.5 / noise 382.2 (need > 400): near-threshold, ~6% short.
- **R-hat** max 1.0114 (need < 1.01): near-threshold.

Measured cost anchor: mean per-chain fit ≈ 137.8 s for 3000 iterations (1000 warmup + 2000 draws)
= **≈ 45.9 ms/iteration** on this host (10 threads).

## Design (RATIFIED; UNCHANGED unless listed)

- **Config/cells:** `informative` only, **td7 only** (informative td7 ≡ td10 in D33 — the depth cap
  never binds — so td10 adds nothing). One cell.
- **Starts + seeds:** the SAME four frozen manifest v1.14 informative starts, semantic-sha256-verified
  before injection (chain 0 MAP `72a7e891…`, chain 1 median-lo `c9f37584…`, chain 2 median-mid
  `2db18020…`, chain 3 median-hi `5cf298a7…`), seeds 0/1/2/3. No re-selection, no new starts.
- **CHANGED — per-chain budget (the only change):** warmup **1000 → 3000**; draws **2000 → 8000**.
- **UNCHANGED:** target acceptance 0.8; `fit_hmc_e1` E1 target; the 4-site toy model; the frozen toy
  data; MAP-init procedure; 200 predictives/chain; R-B pooled primary estimator (pooled 4×200 = 800,
  identical rule); ALL acceptance thresholds (rank R-hat < 1.01 every site; bulk+tail ESS > 400 pooled;
  per-chain occupancy dev ≤ 0.05; divergence < 0.1%; saturation < 10%; NotPSD gate); the authority
  reference (prior-IS pooled 0.2768/0.1310/0.5922) and the authority-coverage criterion.
- **Implementation:** a NEW driver `experiments/m2br_v116_run.py` that IMPORTS (does not modify) the
  frozen `experiments/m2br_validation_run.py` frozen-start injection + acceptance machinery and
  `m2br_run_common`, and runs the informative td7 cell with 3000/8000. Gated behind `--execute` +
  `authorized=True`; fresh untracked output namespace `runs/m2br_v116_informative/`. HMC only via
  `fit_hmc_e1`. Built, hermetically tested (mock sampler), and independently reviewed BEFORE launch.

## Budget (fixed; stop-and-report, identical mechanics to the audit §4 / validation)

Per-chain: (3000 + 8000) × 45.9 ms ≈ **505 s ≈ 8.4 min** sampling + ≈ 120 s MAP/scoring/diagnostics
≈ **10.5 min/chain**. Four chains sequential ≈ **42 min**. Because informative leapfrog counts grow
with draws, budget conservatively: **CEILING 90 min local wall, 600 s reserve**, one monotonic clock,
per-chain projection gate, absolute cutoff, samples-last atomic persist. **One final stop-and-report
outcome. No in-run extension.**

## Rationale = HYPOTHESES under test (no pass is projected or promised)

The escalation TESTS, it does not promise repair:

- **Longer warmup (3000)** tests whether additional adaptation reduces the **chain-2 divergence
  concentration** (its under-adapted step 0.332). It may or may not.
- **More draws (8000)** *should* improve bulk-ESS **if the autocorrelation time stays stable**, and
  gives more opportunity for between-region mixing.
- **R-hat and per-chain occupancy** may improve **only if the chains actually mix** better; more draws
  alone do not guarantee the 0.104 deviation drops under 0.05 if the chains explore genuinely
  different regions.
- No pass is projected or promised. This is a hypothesis-testing run, not a scheduled fix.

## Decision rule (one shot)

- **PASS** (all criteria, incl. occupancy ≤ 0.05 and divergence < 0.001): the informative corrected
  numbers become eligible to SUPERSEDE the withdrawn 0.673 headline; W2's informative
  prior-misspecification case study is updated (a further author decision).
- **FAIL** (any criterion): the informative numbers stay WITHDRAWN/UNVALIDATED. The next step is then a
  STRATEGY change (reparameterization, a tuned mass matrix, or a different sampler) proposed as a
  further addendum — **not** another budget bump. This escalation is the last "same-strategy, longer-run"
  attempt.

## Explicitly out of scope

`vague` and `gamma_relaxed` get NO validation cell (gamma_relaxed attribution-only; vague optional
appendix robustness). No VI/`hmc_laplace`/Mauna/profile-Laplace. td10 informative. Any G-toy/M2c work.
No sampler runs until the v1.16 pin is committed and the driver is built, tested, and reviewed — and
even then only on a separate explicit launch authorization.
