# M2bR — proposed W2/W3 writeup update (PROPOSED, pending author ratification)

Status: **PROPOSED — NOT ratified.** Drafted after the M2bR compute layers ran (D33,
2026-07-12); **REVISED 2026-07-12 (rev 2)** after a codex review + author direction that
the rev-1 draft over-merged distinct estimators and over-claimed on VI. This file proposes
how the W2 (method default / dual-number reporting) and W3 (VI framing) writeup decisions
should change given the audit + validation OUTCOMES. No historical doc,
`Notes/WRITEUP_DECISIONS.md`, or frozen artifact is edited by this file; ratification is the
author's, by explicit vote. Numbers are traceable to
`docs/m2br_freeze/{audit,validation}_result_manifest.json` and the untracked
`runs/m2br_corrected_impact/` + `runs/m2br_validation/` artifacts.

**rev-2 changes vs rev-1:** (a) corrected NUTS and SIR are reported as SEPARATE estimators,
not collapsed into a `0.42–0.44` range and not called numerically identical; (b) prior-IS and
SIR are described as ONE related importance-sampling-family reference (they share the same
importance pools), so the genuinely independent comparison is corrected NUTS vs the IS/SIR
family; (c) ALL quantitative and causal VI claims are WITHDRAWN pending a corrected-VI rerun
(VI used the same D22 defective target); (d) all "mass-faithful" language is qualified as
posterior-mass-faithful **conditional on the fixed data-elicited prior**, N=20 toy-only,
empirical-Bayes-style scope — this validates corrected HMC for this toy configuration only,
not globally.

## What changed empirically (D33 recap)

The pre-M2bR HMC/VI/HMC-Laplace numbers came from the D22 defective target p(θ)L(θ)^N (the
obs plate raised the marginal likelihood to the Nth power), which over-concentrated the
likelihood and pinned NUTS in the low-noise basin — reported basin occupancy 1.00/0.00/0.00
for **every** config. The corrected E1 target (`fit_hmc_e1`) removes that defect for HMC.
**VI (`fit_vi`) was hit by the same defect and has NOT been rerun on the corrected target**
(v1.8/v1.9 hold), so no VI number is corrected.

- **AUDIT (single-chain, cannot close W2/W3):** corrected occupancy now tracks the unaffected
  prior-IS authority for every config; BMS* posteriors de-concentrate.
- **VALIDATION (4-chain, preregistered acceptance):**
  - **toy_elicited (V3 td7, V4 td10): PASS all criteria → SUPERSEDES its withdrawn numbers.**
  - **informative (V1 td7, V2 td10): FAIL (4 marginal criteria) → stays WITHDRAWN/UNVALIDATED.**

## W2 — method default & the historical dual-number ("SIR mass-faithful" vs "density-mode NUTS") convention

**Current ratified convention (2026-07-09, W2/W4):** for the `toy_elicited` main toy figures,
report the SIR posterior-mass-faithful headline **Sin+Linear 0.441 ± 0.005** (τ=1,
n_pred=1000, conditional bootstrap SE) as the mass-faithful number, with the NUTS value
**0.696 (capped td7) / 0.683 (uncapped td10)** reported alongside "as the answer conditional
on the density-mode region, because the chain stays mode-confined even in this unimodal
geometry." Package default `method="hmc"` unchanged.

**Proposed revision (toy_elicited) — report the estimators SEPARATELY:**

1. **Withdraw the historical NUTS `0.696` / `0.683` as D22 artifacts.** The premise that "the
   chain stays mode-confined" is falsified: those numbers came from the defective L^N target.

2. **Corrected NUTS — the PRIMARY package-method result** (`method="hmc"` is the package
   default, so the corrected NUTS is the headline the package produces). Validated, 4 chains
   from overdispersed frozen starts, R-B pooled-800:
   - **Sin+Linear 0.4205 (td7), cross-chain SD 0.0063**
   - **Sin+Linear 0.4220 (td10), cross-chain SD 0.0077**
   - pooled occupancy (lo/mid/hi) 0.7605/0.1856/0.0539 (td7), 0.7602/0.1894/0.0504 (td10).

3. **SIR — reported SEPARATELY as corroboration** (NOT merged with the NUTS number):
   - **Sin+Linear 0.441 ± 0.005** (τ=1, n_pred=1000, conditional bootstrap SE), with the
     independent-importance-pool values **0.419 / 0.438 / 0.431** as the second uncertainty
     component (weight-estimation scatter across the three prior-IS pools).

4. **How to state the agreement.** Corrected NUTS and SIR **agree on the model ranking
   (Sin+Linear wins), on the posterior region (low-noise-dominant, occ ≈0.76 lo), and on broad
   magnitude (≈0.42 vs 0.441).** They are NOT numerically identical and must NOT be collapsed
   into a single `0.42–0.44` estimator. The residual ≈0.02 gap is real (distinct estimators).

5. **Independence caveat.** Prior-IS and SIR are **one related importance-sampling-family
   reference** — SIR resamples the same prior-IS pools, so they share failure modes and are not
   two independent checks. The genuinely independent cross-method agreement here is **corrected
   NUTS versus the IS/SIR family** (plus the prior-IS pooled band masses 0.763/0.191/0.046 that
   the authority-coverage criterion checks; the SIR occupancy is 0.799/0.156/0.045).

6. **Scope (mandatory qualification).** All "mass-faithful" language reads **posterior-mass-
   faithful conditional on the fixed data-elicited prior**. This is the N=20 thesis-toy
   instance (`generate_toy_data()`: N=20, noise 0.5, seed 42), an empirical-Bayes-style
   result — it validates the corrected HMC for THIS toy configuration only, **not** a global
   validation of HMC. Package default `method="hmc"` stays; the loud-disclosure discipline
   stays, but its `toy_elicited` instance changes from "HMC is mode-confined" to "the
   pre-correction HMC was mode-confined due to D22; the corrected sampler is mass-faithful on
   this configuration."

**Proposed status (informative):** the 0.673 headline and its 1.00/0.00/0.00 occupancy stay
**WITHDRAWN**. The corrected single-chain audit suggests broad exploration (occupancy
0.20/0.10/0.70, ≈uniform model posterior, argmax flipping to Sinusoidal) that would materially
change the informative "prior-misspecification case study," but the 4-chain validation FAILED
(R-hat 1.0114, bulk-ESS 378/382 < 400, per-chain occupancy hi-band spread 0.104 > 0.05,
divergence 0.001) — i.e. the corrected informative posterior was NOT VALIDATED under this
preregistered 4×2000 design. The 0.104 per-chain occupancy spread (chain-2 hi 0.567 vs chain-0
hi 0.721, a ~6-SE gap) shows genuine incomplete mixing across a multi-basin structure, not mere
MC noise; but intrinsic difficulty is an inference the design cannot settle. **No W2 informative
claim may be updated** until the v1.16 informative-only escalation (below) either validates or
fails it. Authority coverage passing (pooled agrees with prior-IS within 2 SE) is suggestive but
insufficient — it cannot establish cross-chain reproducibility, which is exactly what fails.

## W3 — VI's framing (wide-basin behavior of the variational fit) — INTERIM: WITHDRAWN pending corrected VI

**Current ratified phrasing (2026-07-09):** VI/HMC disagree at τ=1 under every config (max abs
Δposterior 0.45–0.48); the gap is attributed to the variational family (fit_vi lands in the
wide smooth high-noise region regardless of that region's posterior mass), not to posterior
geometry.

**Proposed INTERIM status — withdraw, do not reinforce:**

1. **All historical VI values, the VI/HMC gap numbers (0.45–0.48), and the causal
   variational-family interpretation remain WITHDRAWN / UNVALIDATED.** `fit_vi` used the same
   D22 defective target and has NOT been rerun; a corrected HMC cannot validate any causal
   claim about an uncorrected VI. The rev-1 wording that the "qualitative core survives and is
   reinforced" is retracted.

2. **What remains factual:** the unaffected pooled prior-IS basin masses (0.592 informative /
   0.046 toy_elicited high-noise region). These are sampler-independent and stand — but they
   **do not diagnose VI**. They describe where posterior mass is, not what the variational fit
   does.

3. **The variational-family reading is now a HYPOTHESIS, not a conclusion:** "a corrected VI
   (E1-based) may still converge to the wide, low-curvature region regardless of its mass."
   Testing it requires an E1-based VI repair and rerun (a separate corrective milestone, out of
   M2bR scope), then recomputing the VI/HMC gap against the corrected HMC. Until then W3 carries
   no quantitative or causal VI claim.

## v1.16 informative-only escalation — PREPARED, NOT executed

A separate protocol proposal is prepared (not run) at
`docs/m2br-v1.16-informative-escalation-PROPOSAL.md`: td7 only, the same four frozen manifest
starts and seeds, longer independently launched chains, UNCHANGED acceptance thresholds and
authority reference, a fixed budget, and one final stop-and-report outcome — awaiting the
author's explicit vote before any chain launches.

## Scope / non-goals

- This proposal updates only interpretive framing; it does not edit
  `docs/prior-sensitivity-study.md`, `docs/fit-method-metric-comparison.md`, or
  `Notes/WRITEUP_DECISIONS.md` in place (author-ratification actions under D28 supersession
  terminology).
- `vague` / `gamma_relaxed` had audit (single-chain) runs only and **no validation cell is
  proposed** (gamma_relaxed is attribution-only; vague is optional appendix robustness); their
  numbers stay withdrawn.
- No VI, `hmc_laplace`, Mauna, or profile-Laplace rerun is proposed here; M2c stays blocked; the
  A7 Della vehicle stays on hold (v1.8).
