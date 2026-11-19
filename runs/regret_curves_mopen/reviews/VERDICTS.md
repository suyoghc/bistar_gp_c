# Case D (paper/case-d-mopen) — §4 review record

Branch tip reviewed: a4b92c0 (paper(case-d): M-open calibration via regret
localization — D64). Package: `review_package_caseD.md` (identical for every
reviewer; §0 constraints + §2 work order + driver-verified facts + section +
README + abridged results.json + diff).

## Reviewer channels

| Reviewer | Channel used | Round-1 verdict |
|---|---|---|
| GPT 5.6 sol (xhigh) | Codex CLI fresh session, repo read access | REVISE (4 findings) |
| Opus 5 | Claude Code in-session subagent (model=opus), FRESH agent, repo read access | REVISE (11 findings) |
| Gemini | Direct Generative Language API `gemini-3.1-pro-preview`, Griffiths key, thinkingLevel HIGH, package-only (author-directed substitution; MCP server not connected) | APPROVE (0 findings) |
| Kimi K3 | Paste-ready package `kimi_k3_package.md` — **author-run, PENDING** | pending |

Raw outputs: `round1_codex-gpt-5.6-sol.md`, `round1_opus-5.md`,
`round1_gemini-3.1-pro-preview.md`. Verdict conflict resolved by rule 3 (fix
queue non-empty, REVISE governs).

## Collation and cross-verification

Two-reporter clusters (rule 1, presumed real):

| ID | Sev | Substance | Reporters |
|---|---|---|---|
| F-D1 | S1/S2 | The pw_nll "weak confidence" vs pw_mse "sharp" contrast is a unit artifact: pw_nll = 0.5·log(2πσ_θ²) + pw_mse/(2σ_θ²) EXACTLY (verified on all 300 stored mean_G values, max err 1.78e-15), the same statistic under a candidate-specific affine map scored at shared τ; no τ on the stored 15-point grid closes the gap; pw_nll is also NOT the W1 primary's analogue (candidate-variance weighting vs pw_kl_vcal's GP-variance weighting; pw_mse closer). The τ-free scale-invariant support for the section's asymmetry thesis is the stored raw_draw_wins: truth wins 39.0% of draws in the power cohort vs 98.7% in the exponential cohort | Codex (DC1 + DC2) + Opus (DO1) |
| F-D2 | S2 | The implemented estimand is E over LATENT FUNCTION DRAWS at the stored MAP point, not the kb formula's average of posterior means over hyper draws; Jensen-inflates every regret by ≈ the per-trial latent SD and compresses the gap trial-dependently; the mean-vs-draw substitution is undisclosed while the MAP-vs-HMC substitution is disclosed | Codex (DC3) + Opus (DO4) |

Single-reporter findings (rule 2, adversarially checked; default-refuted on
ambiguity; never the originator):

| ID | Sev | Substance | Checker | Outcome |
|---|---|---|---|---|
| DC4 | S2 | "Scaffold-induced preference" is a causal attribution one practitioner-MAP RBF reconstruction cannot identify (all three configs share the RBF family; no scaffold contrast exists in the branch; contradicts the section's own F1/F2-agnostic line) | Opus | CONFIRMED |
| DO2 | S2 | "Absolute divergence magnitude" read is 93.9% candidate-noise entropy; calibrates RT noise scale, not adequacy | Codex | REFUTED as stated: arithmetic verified exactly, but the section already conditions calibration on metric/config/sample-size/noise and sets no threshold; the residual term still measures standardized misfit. REJECTED (logged) |
| DO3 | S2 | Mimicry-signature sentence rests on the one dissenting metric (pw_mse and pw_hellinger favor truth in the power cohort, all configs) | Codex | REFUTED as stated: the six comparison numbers are correct, but the sentence follows an explicitly pw_nll-only table and the section already blocks metric-general claims. REJECTED (logged); the F-D1 rewrite keeps the surviving sentence explicitly metric-scoped |
| DO5 | S3 | Undisclosed domain mismatch: stored G on a 50-point grid over each FULL series (20-79 trials) vs regret on trials 1-20 (≈24.4% of the longest subjects' compared domain) | Codex | CONFIRMED |
| DO6 | S3 | Gap profile is two-mode (secondary max at trial 6), not front-concentrated; figure shading excludes the secondary peak | Codex | REFUTED as stated: trial 20 (6.329) does not equal the trial-2 minimum (6.217); the section's "first half" phrasing includes the trial-6 peak; the figure plots the full gap and the shading is a labeled summary window. REJECTED (logged) |
| DO7 | S3 | No cohort-mean uncertainty; three-decimal precision unsupported (cited pooled q90/q10 ~90x at trial 1) | Gemini | REFUTED as stated: artifact q90/q10 at trial 1 is 3.2-8.2x (max ~17x anywhere), not ~90x. REJECTED (logged) |
| DO8 | S3 | "all configurations agree" row mislabeled under Power/Exponential headers (entries are agreement counts of 50) | Gemini | CONFIRMED |
| DO9 | S4 | posterior_sd_min/max_raw fields dead (never written to results.json), mislabeled (eigenvalue roots), min identically 0 after clamping | Gemini | CONFIRMED |
| DO10 | S4 | practitioner-provenance claim prose-only, unasserted | Codex | REFUTED: aggregation already indexes every config per subject and would abort before writing results.json if practitioner diagnostics were missing; an assertion would add clarity, not a missing gate. REJECTED (logged) |
| DO11 | S4 | Regret table lacks units (results.json and the figure axis carry "RT units") | Gemini | CONFIRMED |

## Fix queue

F-D1 metric-contrast rewrite (affine identity; raw_draw_wins asymmetry
carries the thesis; metric-specific scoping) · F-D2 estimand relabel +
mean-based regret reported alongside + "explains" softened · F-D3 causal
scaffold language removed, non-identifiability stated (DC4) · F-D4 both
evaluation domains named, linkage restricted (DO5) · F-D5 agreement-row
labeling (DO8) · F-D6 dead/mislabeled SD fields removed or corrected (DO9) ·
F-D7 RT units in the regret table (DO11).

Findings REJECTED with logged refutations: DO2, DO3, DO6, DO7, DO10.

## Author-adjudication ledger (open at merge proposal)

1. F-D1 (S1, statistical): sign off the rewritten metric analysis (the
   affine-identity disclosure and the raw_draw_wins-based asymmetry claim).
2. F-D2 (S2, statistical): sign off the dual-estimand presentation
   (draw-based posterior expected absolute deviation + mean-based plug-in).
3. F-D3 (S2): sign off the non-identifiability framing of the failure
   source.
4. Kimi K3 round-1 review: run `kimi_k3_package.md`; findings enter a fresh
   cross-verification cycle.

(Continued below after the fix pass and re-review round.)

## Fix pass 1 (rule 4) — commit c57a70e

All seven queue fixes implemented by Codex gpt-5.6-sol xhigh
(`docs/paper-sie-jmp/prompts/case-D-fix1.txt`); the five rejected findings
were explicitly NOT implemented. The corrections strengthened the result:
the mean-based plug-in preserves the asymmetric localization (power truth
17.638/17.325; exponential truth 33.901/10.764 RT units) and the τ-free
raw_draw_wins asymmetry holds across configs (39.0/39.9/41.5 percent power
truth vs 98.7/94.6/92.1 exponential truth). Driver verification: rerun exit
0, results.json byte-identical; practice_EvansEtAL byte-untouched.

## Re-review round (changed hunks only, by the raisers)

| Reviewer | Findings re-reviewed | Outcome |
|---|---|---|
| Codex gpt-5.6-sol | F-D1 (DC1+DC2), F-D2 (DC3), F-D3 (DC4) | all RESOLVED (independently re-aggregated raw_draw_wins from all 50 source artifacts); ONE new S3: the Jensen sentence claimed categorical dominance per subject/candidate/trial while the finite 100-draw estimates invert at trial 1 (116.333 < 116.506; 131.415 < 131.572) |
| Opus 5 | DO1 (in F-D1), DO4 (F-D2), DO5 (F-D4), DO8 (F-D5), DO9 (F-D6), DO11 (F-D7) + F-D3 conflict check | all RESOLVED (every replacement number independently re-derived: affine-identity gate 1.78e-15, all six raw_draw_wins cells, plug-in headline values, Jensen relationship in all reported aggregates; F-D3 consistent); ONE new S3: the F-D1 hunk cited "approximately 0.573 in the review summary" — a non-artifact number (artifact medians 0.581/0.569/0.557) and a review-process reference inside manuscript prose |

Raw outputs: `rereview_codex-gpt-5.6-sol.md`, `rereview_opus-5.md`; package
`rereview_package_caseD.md`. Gemini raised no round-1 findings (APPROVE) and
so held no re-review role under rule 4.

## Post-re-review handling of the two S3 defects

Bounded Codex micro-fix (rule-4-consistent channel), prose-only:
- The 0.573/"review summary" parenthetical replaced by the three artifact
  medians (0.581, 0.569, 0.557 at τ=0.1) with the pw_mse 0.987 contrast; no
  review-document reference remains in the section.
- The Jensen sentence now orders the EXACT estimands and states that
  finite-draw Monte Carlo estimates may invert locally, citing the two
  trial-1 inversions.
Driver verified mechanically: forbidden strings absent, replacement medians
present, results.json byte-identical (no computation changed), D64 carries
the same corrected sentences. Reviewer sign-off structurally unavailable
(no third round per rule 4); disclosed here.

## Final §4 verdict for the branch

Round-1 REVISE discharged: 14 distinct findings collated (2 two-reporter
clusters, DC4 + DO5 + DO8 + DO9 + DO11 confirmed in adversarial checks,
DO2/DO3/DO6/DO7/DO10 REFUTED and logged); all queue fixes RESOLVED in
re-review; the two hunk-introduced S3s fixed and driver-verified.
**Protocol outcome: REVISE resolved — branch proposed to the author for
merge, subject to the ledger:**
1. F-D1 (S1, statistical): sign off the affine-identity disclosure and the
   raw_draw_wins-based asymmetry claim (rule 5).
2. F-D2 (S2, statistical): sign off the dual-estimand presentation.
3. F-D3 (S2): sign off the non-identifiability framing.
4. Kimi K3 round: run `kimi_k3_package.md`; findings enter a fresh
   cross-verification cycle.
Nothing merges autonomously (§4).

## Kimi K3 round (author-directed, 2026-08-12)

Channel: `moonshotai/kimi-k3` via OpenRouter (author's key), package-only, on
the ORIGINAL round-1 package (pre-fix state). **Verdict: APPROVE** — 3
findings, raw output `round1_kimi-k3.md`. Collation against the completed
record:

- KD1 [S3] (agreement row misparse-prone under Power/Exponential headers):
  converges with DO8, already resolved in c57a70e (F-D5 moved the counts out
  of the table into prose). Third independent voice on that defect.
- KD2 [S4] ("pw_nll combines mean mismatch with pointwise variance
  calibration" undefined by any packaged artifact): converges with the
  RESOLVED F-D1 — that definitional sentence was removed entirely by the fix
  pass (and shown wrong in substance: pw_nll weights by candidate variance).
- KD3 [S4] (footnote em-dash tags): house citation convention. No action.
- Kimi's bonus note that the dead posterior_sd fields are "worth deleting"
  converges with DO9, already resolved (F-D6 deleted them).
- Its verification list independently reconfirms every number it could
  reach, including all twelve cohort mean_G values and both regret tables.

Net: zero new actionable findings; all three substantive observations
converge with already-resolved items. APPROVE against the pre-fix state;
the current tip is strictly stronger.

## Author sign-off and Ready (2026-08-12)

The author signed off the statistical items by direct instruction: item 1
(the F-D1 rewrite: the affine-identity disclosure and the raw-draw-wins
asymmetry carrying the thesis), item 2 (the F-D2 dual-estimand
presentation: MAP-conditional posterior expected absolute deviation plus
the posterior-mean plug-in, with Jensen scoped to the exact estimands), and
item 3 (the F-D3 non-identifiability framing of the failure source). The
Kimi K3 round is complete (full convergence with resolved findings). At the
author's direction, PR #38 leaves Draft: **READY**.
