# M2bR — proposed W2/W3 writeup update (PROPOSED, pending author ratification)

Status: **PROPOSED — NOT ratified.** Drafted after the M2bR compute layers ran (D33,
2026-07-12). It proposes how the W2 (method default / dual-number reporting) and W3
(VI framing) writeup decisions should change given the audit + validation OUTCOMES.
No historical doc, `Notes/WRITEUP_DECISIONS.md`, or frozen artifact is edited by this
file; ratification is the author's. Numbers below are traceable to
`docs/m2br_freeze/{audit,validation}_result_manifest.json` and the untracked
`runs/m2br_corrected_impact/` + `runs/m2br_validation/` artifacts.

## What changed empirically (D33 recap)

The pre-M2bR HMC/VI/HMC-Laplace numbers came from the D22 defective target
p(θ)L(θ)^N (the obs plate raised the marginal likelihood to the Nth power), which
over-concentrated the likelihood and pinned NUTS in the low-noise basin — reported
basin occupancy 1.00/0.00/0.00 for **every** config. The corrected E1 target
(`fit_hmc_e1`) removes that defect.

- **AUDIT (single-chain, cannot close W2/W3):** corrected occupancy now tracks the
  unaffected prior-IS authority for every config; BMS* posteriors de-concentrate.
- **VALIDATION (4-chain, preregistered acceptance):**
  - **toy_elicited (V3 td7, V4 td10): PASS all criteria → SUPERSEDES its withdrawn numbers.**
    Validated R-B pooled-800 BMS* posterior (pw_kl_vcal, τ=1): **Sin+Linear 0.4205 (td7) /
    0.4220 (td10)**; hard-win Sin+Linear 0.968/0.970; pooled occupancy (lo/mid/hi)
    **0.7605/0.1856/0.0539 (V3 td7)** and **0.7602/0.1894/0.0504 (V4 td10)**.
  - **informative (V1 td7, V2 td10): FAIL (4 marginal criteria) → stays WITHDRAWN/UNVALIDATED.**

## W2 — method default & the dual-number ("mass-faithful SIR" vs "density-mode NUTS") convention

**Current ratified convention (2026-07-09, W2/W4):** for the `toy_elicited` main toy
figures, report the SIR mass-faithful headline **Sin+Linear 0.441 ± 0.005** (τ=1,
n_pred=1000) as the posterior-mass-faithful number, with the NUTS value **0.696 (capped
td7) / 0.683 (uncapped td10)** reported alongside "as the answer conditional on the
density-mode region, because the chain stays mode-confined even in this unimodal
geometry." Package default `method="hmc"` unchanged.

**Proposed revision (toy_elicited):**
1. **Withdraw the 0.696 / 0.683 NUTS numbers as D22 artifacts** and replace them with the
   validated corrected NUTS **Sin+Linear ≈ 0.42** (0.4205 td7 / 0.4220 td10), occupancy
   ≈ 0.76/0.19/0.05, cross-chain-validated (R-hat ≤ 1.002, bulk-ESS ≥ 2.8k, 0 divergences,
   authority coverage PASS across 4 independent chains from overdispersed frozen starts).
2. **The dual-number framing collapses for `toy_elicited`.** The premise that "the chain
   stays mode-confined" is now falsified: the corrected NUTS explores the full posterior.
   Its pooled occupancy (≈0.76/0.19/0.05) matches the independent **prior-IS pooled
   authority** (0.763/0.191/0.046 — the reference the authority-coverage criterion checks;
   the SIR occupancy is 0.799/0.156/0.045), and its BMS* model posterior (Sin+Linear ≈0.42)
   matches the **SIR mass-faithful model posterior** (Sin+Linear 0.441). NUTS now agrees with
   both sampler-independent references, so it is no longer a mode-vs-mass contrast — they
   concur. Propose reporting a single
   reconciled headline (Sin+Linear ≈ 0.42–0.44, occupancy ≈ 0.76 low-band) with NUTS and
   SIR cited as mutually corroborating, sampler-independent estimates.
3. **Package default `method="hmc"` is strengthened, not weakened.** The historical
   disclosure "HMC reports the density-mode basin, not the mass-dominant basin" was, for
   `toy_elicited`, an artifact of the defective target; the corrected HMC is mass-faithful
   on this config. The loud-disclosure discipline should stay, but its `toy_elicited`
   instance is downgraded from "HMC is mode-confined" to "the pre-correction HMC was
   mode-confined due to D22; the corrected sampler is mass-faithful here."

**Proposed status (informative):** the 0.673 headline and its 1.00/0.00/0.00 occupancy
stay **WITHDRAWN**. The corrected single-chain audit suggests broad exploration
(occupancy 0.20/0.10/0.70, ≈uniform model posterior, argmax flipping to Sinusoidal) that
would materially change the informative "prior-misspecification case study," but the
4-chain validation FAILED (R-hat 1.0114, bulk-ESS 378/382 < 400, per-chain occupancy
hi-band spread 0.104 > 0.05, divergence 0.001) — i.e. the corrected informative posterior
was NOT VALIDATED under this preregistered 4×2000 design. (The 0.104 per-chain occupancy
spread does show the four overdispersed chains landing in different regions — evidence of
incomplete mixing across a multi-basin structure — but intrinsic difficulty is an inference
the design cannot settle.) **No W2
informative claim may be updated** until a v1.16+ escalation addendum (more/longer chains
or a strategy change) validates it. Authority coverage passing (pooled agrees with
prior-IS within 2 SE) is suggestive but insufficient — it cannot establish cross-chain
reproducibility, which is exactly what the informative cells miss.

## W3 — VI's framing (wide-basin behavior of the variational fit)

**Current ratified phrasing (2026-07-09):** VI/HMC disagree at τ=1 under every config
(max abs Δposterior 0.45–0.48); the gap is attributed to the variational family (fit_vi
lands in the wide smooth high-noise region regardless of that region's posterior mass:
59% informative / 5% re-elicited), not to posterior geometry; mass is assessed with
sampler-independent estimators (prior-IS, SIR).

**Proposed handling:**
1. **The VI/HMC gap numbers (0.45–0.48) are computed against the DEFECTIVE HMC and must
   be marked provisional.** They cannot be refreshed within M2bR: `fit_vi` is NOT rerun
   before its own repair (v1.8/v1.9 hold), so the VI side is still the defective-target
   result. The quantitative VI/HMC gap therefore stays **UNVALIDATED / pending a VI
   rerun** (out of M2bR scope; a separate corrective milestone).
2. **The qualitative core of W3 survives and is reinforced.** The wide-high-noise-region
   masses W3 cites (0.592 informative / 0.046 toy_elicited) are the unaffected pooled
   prior-IS masses — unchanged. The new corrected evidence that NUTS (validated,
   `toy_elicited` only) now matches the mass-faithful references **weakens HMC as a confound**
   in the VI story: for `toy_elicited`, the corrected HMC is mass-faithful rather than
   mode-confined, so a residual VI/HMC disagreement there is more plausibly a variational-family
   effect. This is NOT a closed attribution — VI has not been rerun on the corrected target, and
   the informative cells did not validate — so it stays a proposed reading pending the VI rerun.
   Recompute the exact VI/HMC gap only after VI is rerun on the
   corrected target.
3. The verbatim paper phrasing that quotes "0.45 to 0.48" and the mode-confinement clause
   should carry a footnote: "HMC/VI numbers predating the D22 correction; the corrected,
   multi-chain-validated NUTS for `toy_elicited` gives Sin+Linear ≈ 0.42 with occupancy
   0.76/0.19/0.05, matching the SIR mass-faithful estimate. VI awaits rerun on the
   corrected target."

## Scope / non-goals

- This proposal updates only the interpretive framing; it does not edit
  `docs/prior-sensitivity-study.md`, `docs/fit-method-metric-comparison.md`, or
  `Notes/WRITEUP_DECISIONS.md` in place (author-ratification actions under D28
  supersession terminology).
- `vague` / `gamma_relaxed` had audit (single-chain) runs only and no validation cell;
  their numbers stay withdrawn (validation is an author option at +2 cells per config).
- No VI, `hmc_laplace`, Mauna, or profile-Laplace rerun is proposed here; M2c stays blocked;
  the A7 Della vehicle stays on hold (v1.8).
