# Synthesis package (paper/synthesis-sections) — §4 review record

Branch tip reviewed: 95d1259 (sections 01, 02, 08 — D66). Package:
`review_package_synthesis.md` (identical for every reviewer; §0 + driver
facts + the three synthesis sections + ALL FOUR case sections for
consistency checking + the D66 diff). Writing-only package under a
zero-re-quoted-empirical-estimates policy.

## Reviewer channels — first round with all four reviewers live

| Reviewer | Channel | Round-1 verdict |
|---|---|---|
| GPT 5.6 sol (xhigh) | Codex CLI fresh session, repo access | REVISE (5 findings) |
| Opus 5 | fresh in-session subagent, repo access | REVISE (12 findings) |
| Gemini | `gemini-3.1-pro-preview`, Griffiths key, package-only | APPROVE (0) |
| Kimi K3 | `moonshotai/kimi-k3` via OpenRouter, package-only | APPROVE (2 findings) |

Raw outputs: `round1_*.md`. Verdict conflicts resolved by rule 3 (queue
non-empty; REVISE governs).

## Channel event: Codex usage-lock mid-protocol

After its round-1 review, the Codex channel hit its usage limit (locked to
2026-08-18), before its assigned cross-check batch ran. Deviations, all
disclosed here: (a) its seven checks were REROUTED to non-originators —
package-decidable items to Kimi, items needing repo evidence to Gemini with
the needed source excerpts appended to its package; (b) the fix pass runs
under a SUBSTITUTE implementer (a fresh Opus subagent, not the reviewer
agent); (c) Codex cannot re-review its own confirmed findings — driver
mechanical verification substitutes, disclosed per the established
no-third-round pattern.

## Collation and cross-verification

Two-reporter cluster (rule 1): FS1 — Remark 1's "under any convention"
quantifies past the three proven monotone conventions (Kimi KS2), and its
formalization presupposes a common parameter space that Case B's
cross-family nesting lacks; reachable-set containment with model-level
scores is the correct formulation (Opus SO5). → queue.

Single-reporter findings (rule 2; default-refuted; never the originator):

| ID | Sev | Substance (abbreviated) | Checker | Outcome |
|---|---|---|---|---|
| SC1 | S2 | Ḡ gloss ("averages G across patterns") vs implementation (G evaluated once against the moment-matched averaged GP; difference not φ-constant; notation gloss compounds) | Opus | CONFIRMED (two-draw counterexample: minimizer, minimum, and curvature all move; every Case B / E6 Z_M path uses avg_gp) |
| SC2 | S2 | τ→0 hard-best-match limit attached to POOLED display; pooled's limit is global-minimum domination (Target A: 0.000/1.000), per-draw conventions recover hard rates | Opus AND Kimi (accidental double-route) | SPLIT: Opus CONFIRMED (artifact rows decisive); Kimi REFUTED (sentence defensible as the generic global-winner reading). Driver adjudication under rule 5 (S2 statistical): FIX — the pooled/per-draw distinction is the paper's headline distinction; a sentence two checkers read oppositely cannot stand. Author sign-off requested |
| SC3 | S3 | Projection-check citation rests on a never-committed script whose entry point does not run the check; both machinery footnotes anchor on it | Opus | CONFIRMED (git ls-tree/log across all branches: never committed; entry point stops before the check; sharpening: no numeral was quoted, so the numbers policy held) |
| SC4 | S3 | Bridge overstates Case C's LOO side | Gemini | REFUTED: 8.1 already carries "inconclusive" and "local diagnostic". REJECTED (logged) |
| SC5 | S3 | Non-identifiability narrowed to F1/F2; Case D leaves FOUR sources | Gemini | CONFIRMED |
| SO1 | S2 | "therefore agree" a non-sequitur without the scalar-variance scoping | Gemini (with metrics_v2 + mechanism-script excerpts) | REFUTED: "in the prior-only mechanism check" is adequate scoping. REJECTED (logged); the SC3 rewrite of the same passage carries the algebraic basis anyway |
| SO2 | S2 | "matching Eq. 4" re-introduces the AO2 qualification gap | Kimi | REFUTED: the claim is about operation order, mirroring Case A's own mapping-row language. REJECTED (logged) |
| SO3 | S2 | Draw-win fractions overclaimed as licensing cross-metric comparison | Kimi | REFUTED: the within-metric restriction sentence exists; no cross-metric claim made. REJECTED (logged) |
| SO4 | S2 | M-open material's legacy-metric limitation omitted | Kimi | REFUTED: metric-conditionality is stated; no pw_kl_vcal attribution made. REJECTED (logged) |
| SO6 | S3 | Reporting rule's warrant does not reach the candidate-specific case | Kimi | REFUTED: invariance correctly scoped one sentence earlier. REJECTED (logged) |
| SO7 | S3 | Symmetric dial framing omits that CANONICAL pooled fails Target A | Gemini | CONFIRMED |
| SO8 | S3 | Contribution (iii) invites reading the validation as testing the GP data prior | Gemini | CONFIRMED |
| SO9 | S3 | Uncertainty-floor sentence uncited; belongs to the section-7 development | Gemini (07 stub appended) | CONFIRMED |
| SO10 | S4 | "provides the primary metric" incoherent predication | Kimi | REFUTED (stylistic preference). REJECTED (logged) |
| SO11 | S4 | PSIS-LOO mechanics misstated (ratios/posteriors; smoothing vs k̂ diagnosis) | Kimi | CONFIRMED (also inconsistent with Case C's correct usage) |
| SO12 | S4 | Gneiting-Raftery footnote invites a propriety claim | Kimi | REFUTED: footnote already scoped; no propriety claim made. REJECTED (logged) |
| KS1 | S3 | 8.6 attributes the provenance exception to D17; D66 attributes it to D65 — same commit, two authorities | Gemini | CONFIRMED (verbatim contradiction) |

## Fix queue (ten items, substitute implementer)

FIX-1 Remark 1 reachable-set reformulation + three-convention narrowing
(FS1) · FIX-2 Ḡ implementation honesty (SC1; notation amendment ledgered) ·
FIX-3 pooled-limit separation (SC2, driver-adjudicated) · FIX-4 projection
citation recast (SC3) · FIX-5 four-source non-identifiability (SC5) · FIX-6
pooled-fails-Target-A honesty clause (SO7) · FIX-7 contribution scoping
(SO8) · FIX-8 uncertainty-floor citation (SO9) · FIX-9 PSIS-LOO mechanics
(SO11) · FIX-10 provenance alignment to D65 (KS1).

Rejected with logged refutations: SC4, SO1, SO2, SO3, SO4, SO6, SO10, SO12.

## Author-adjudication ledger (open at merge proposal)

1. SC1 (S2, statistical): sign off the Ḡ implementation-honesty fix AND
   decide the frozen-notation amendment (00-notation.md line for Ḡ: gloss
   says "averaged across data patterns"; implementation evaluates G against
   the moment-matched averaged GP; notation file is change-controlled).
2. SC2 (S2, statistical, checker-split): sign off the pooled-limit
   separation (Opus confirmed on artifact evidence; Kimi defended the
   generic reading; driver adjudicated to fix).
3. Substitute-implementer deviation: ratify the fresh-Opus fix pass and the
   driver-verification substitution for Codex's re-review (channel locked
   to 2026-08-18).
4. Uncommitted local methods material (mechanism_figure_poster.py and the
   CogSci figure tree): commit, or keep the local-material citation pattern
   the FIX-4 recast adopts.

(Continued below after the fix pass and re-review round.)

## Fix pass 1 (rule 4, substitute implementer) — commit d6ee868

All ten queue fixes implemented by the disclosed substitute (a fresh Opus
subagent; Codex usage-locked). The implementer verified FIX-2 against
aggregation_v3.py and laplace_evidence.py sources and FIX-3 against Case A's
committed artifact rows. Driver verified all ten fixes present, the
zero-empirical-numerals policy (counts as words), 00-notation.md untouched,
and D60-D65 intact.

## Re-review round (changed hunks, by available raisers)

| Reviewer | Findings | Outcome |
|---|---|---|
| Opus 5 (reviewer agent) | SO5 (FS1), SO7, SO8, SO9, SO11 + invited FIX-4 comment | all RESOLVED (independent verification incl. the τ-limit paragraph against Case A's committed rows); TWO new S3 defects (N1 "estimator" mislabel — structural non-vanishing gap; N2 the section-7 footnote crediting a stub with a development it lacks) + one invited softening (projections "need no longer coincide") |
| Kimi K3 | KS1, KS2 (in FS1) | both RESOLVED; ONE new minor defect converging with N1 (the "estimator" tension) |
| Codex | SC1, SC2, SC3, SC5 | UNAVAILABLE (usage-locked). Driver mechanical verification substituted, disclosed: SC1 the moment-matching paragraph present and source-consistent; SC2 the pooled/per-draw limit separation present; SC3 the projection footnotes re-anchored to metrics_v2 with the uncommitted-script disclosure; SC5 the four sources named verbatim. Formal raiser sign-off deferred to any post-2026-08-18 follow-up the author requests |
| Gemini | raised no round-1 findings | no re-review role |

## Post-re-review micro-fix (three items)

Implemented by the same substitute agent: MF-1 "estimator" replaced by
"plug-in surrogate" with the explicit non-consistency sentence (two
reporters); MF-2 the section-7 reference converted to the assembled-
manuscript forward-reference pattern with the uncommitted-material
disclosure, the "which develops" claim dropped, the no-case-estimates-a-floor
half kept; MF-3 "need no longer coincide" softening. Driver verified all
three sentences present, footnote parity intact, zero new numerals.

## Final §4 verdict for the branch

Round-1 REVISE discharged: 19 collated findings (1 two-reporter cluster, 18
singles of which 9 confirmed, 8 REFUTED with logged refutations, 1
checker-SPLIT resolved by driver adjudication); all queue fixes RESOLVED by
the available raisers; three hunk-introduced defects fixed and
driver-verified. **Protocol outcome: REVISE resolved — branch proposed to
the author for merge, subject to the ledger:**
1. SC1 (S2, statistical): sign off the Ḡ surrogate framing AND decide the
   frozen-notation amendment (00-notation.md Ḡ gloss vs the moment-matched
   implementation).
2. SC2 (S2, statistical, checker-split): sign off the pooled-limit
   separation.
3. Substitute-implementer + driver-verification deviations (Codex locked to
   2026-08-18): ratify, or commission a Codex re-review pass after the lock
   lifts.
4. Uncommitted local methods material (mechanism figure script; the 07
   stub): commit or keep the disclosed local-material citation pattern.
Nothing merges autonomously (§4).
