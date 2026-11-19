# Case B (paper/case-b-occam-dial) — §4 review record

Branch tip reviewed: 9d6d95c (paper(case-b): occam dial figure + E6 nesting
monotonicity check — D62). Package: `review_package_caseB.md` (identical for
every reviewer; §0 constraints + §2 work order + section + README + JSONs
(e6 abridged) + full diff).

## Reviewer channels (HANDOFF §4 table, with session deviations recorded)

| Reviewer | Channel used | Round-1 verdict |
|---|---|---|
| GPT 5.6 sol (xhigh) | Codex CLI fresh session, repo read access | REVISE (3 findings) |
| Opus 5 | Claude Code in-session subagent (model=opus), repo read access | REVISE (8 findings) |
| Gemini | gemini MCP server NOT CONNECTED; author-directed substitution this session: direct Generative Language API, model `gemini-3.1-pro-preview`, Griffiths API key, thinkingLevel HIGH, package-only (no repo access). Attempt 1 (default thinking) preserved as `_attempt1`; author said "try again"; retry is the operative round-1 review (same package). Both attempts agree. | REVISE (1 finding) |
| Kimi K3 | No CLI configured; paste-ready package at `kimi_k3_package.md` — **author-run, PENDING**; protocol proceeded with the three available reviewers | pending |

Raw outputs: `round1_codex-gpt-5.6-sol.md`, `round1_opus-5.md`,
`round1_gemini-3.1-pro-preview.md` (+`_attempt1`).

## Collated findings and cross-verification (rules 1-2)

Adversarial checks used the protocol wording ("attempt to refute this specific
finding against the artifacts; default to refuted if the evidence is
ambiguous"), routed to a non-originator.

| ID | Sev | Substance | Reporters | Cross-check | Status |
|---|---|---|---|---|---|
| F1 | S1 | Work-order item 2's REVIEW_AND_VET resolution never reaches the committed branch (kb/ gitignored, .gitignore:36; zero kb/ files ever tracked), so a clean checkout loses it | Gemini + Codex (≥2: presumed real). Opus round-1 rationale dissents in part ("mistaken, not a defect") | not required (rule 1) | FIX QUEUE (driver-adjudicated §0-compliant form below); force-add/.gitignore variant ESCALATED TO AUTHOR |
| F2 | S2 | Sinusoidal occam=True crossing over-precise: bracket swing 0.040 nats < common-mode IS SE ≈0.043 (ESS 883/1454 at the bracket); six-decimal location unsupported; ±1 SE shifts crossing ≈±1 grid step (τ ≈ 1.39–1.58). Linear crossing sign-supported (SE 0.012 vs swing 0.354) | Codex + Opus (independent, ≥2) | not required | FIX QUEUE + AUTHOR ADJUDICATION (statistical S2, rule 5) |
| O2 | S2 | E6 min-Ḡ inequality true by construction (exact-subset boxes + mean-only metric + embedded-optimum seeding, e6:67-80,191-192,230); cannot fail, so §4.2's "supports the reachable-set claim" overstates; empirical weight belongs on margins + finite-τ crossings | Opus | Codex: CONFIRMED (metrics_v2.py:43-55 mean-only; e6_results zero embedding error) | FIX QUEUE + AUTHOR ADJUDICATION (statistical S2, rule 5) |
| O3 | S3 | Figure τ=0.3 is 1.6% above the occam=True Linear crossing 0.295184; p2 gap 0.0867 nats (BF 1.09) — near-tie never cross-referenced; p1/p2 ordering τ-marginal | Opus | Gemini: CONFIRMED | FIX QUEUE |
| O4 | S3 | Six-decimal probabilities without MC error; ESS-implied SE ≈0.005 on probabilities > 0.003 anchor tolerance; tolerance is a same-seed reproduction gate, not accuracy | Opus | Codex: CONFIRMED (SE(log Z) ≈0.0079/0.0170/0.0380; p2 gap SE ≈0.0188) | FIX QUEUE |
| O5 | S3 | `model_posterior` JSON key + README "Fresh n=50 posteriors" mislabel the induced model PRIOR (producer names it priors; y-axis says prior; W4-adjacent misreading) | Opus | Gemini: CONFIRMED | FIX QUEUE |
| O6 | S3 | p1 Laplace arm serializes ess:null only; `_viz_spaces.py:244-248` discards ZMxResult n_clipped/converged; floor-dependent +9.2-nats-per-direction term unverifiable from the committed artifact | Opus | Codex: CONFIRMED | FIX QUEUE |
| O7 | S4 | `optional_local_crosscheck.available` + README line bake local untracked-file availability into committed artifacts; clean-clone rerun regenerates different content | Opus | Gemini: CONFIRMED | FIX QUEUE |
| O8 | S4 | `_crossings` edge case: left==0.0 emitted regardless of right sign; exact interior zero double-counted; NOT exercised (min abs deltas 0.0055-2.97) | Opus | Codex: CONFIRMED (not exercised; no number changes) | FIX QUEUE (guard only) |
| C3 | S4 | Committed D62 "figures and logs only ... cannot serve as an input" factually false (delta_table.md, ess_by_stage.md, legacy_scripts/ exist; crosscheck is an enforced 0.003 assertion gate when present) and internally inconsistent with D62's own Alternatives paragraph | Codex | Opus: CONFIRMED | FIX QUEUE |

Findings REFUTED in cross-check: none. Verdict conflicts: none (all three
active reviewers said REVISE).

## Rule-3 verdict at round 1

Fix queue non-empty. **REVISE**. One Codex fix pass (rule 4) follows, then ONE
re-review round of the changed hunks only, by the raisers of the surviving
findings (Codex: F1, F2, C3; Opus: F2, O2-O8; Gemini: F1). No third round;
residuals escalate to the author.

## Driver adjudications embedded in the fix specification

- F1 §0-compliant fix: mirror the corrected REVIEW_AND_VET resolution
  paragraph verbatim into the committed `runs/occam_dial/README.md`; update
  the local kb file's paragraph (stays gitignored); note the mirror in D62.
  The reviewer-proposed force-add of `kb/Wiki/REVIEW_AND_VET.md` (or a
  .gitignore change) would create the repo's first tracked kb/ file and
  conflicts with §0's commit-scope list — that variant is an author decision,
  recorded in the ledger below.
- F2 fix: three-seed IS replication of the E6 sweeps + coarsened,
  uncertainty-honest crossing statements (details in the fix prompt).

## Author-adjudication ledger (open items at merge proposal)

1. F2 (S2, statistical): sign off the corrected Sinusoidal-crossing
   uncertainty treatment (rule 5 mandatory).
2. O2 (S2, statistical): sign off the reframed E6 evidential claim (rule 5
   mandatory).
3. F1 variant: decide whether the kb/Wiki/REVIEW_AND_VET.md file itself
   should ever be committed (would be the first tracked kb/ file; repo-
   structure precedent; cross-vault conventions in OBS_ResearchDB
   D7/D8/D11/D12/D18/D19).
4. Kimi K3 round-1 review: run `kimi_k3_package.md` and feed findings back;
   any new findings enter a fresh cross-verification cycle.

(Continued below after the fix pass and re-review round.)

## Fix pass 1 (rule 4) — commit c15a65f

All ten queue fixes implemented by Codex gpt-5.6-sol xhigh
(`docs/paper-sie-jmp/prompts/case-B-fix1.txt`; report in the rereview
package). Driver reran both scripts clean; D60/D61 integrity re-verified;
branch diff vs main unchanged in file scope. The three-seed IS replication
empirically reproduced the reviewer-predicted crossing uncertainty: per-seed
Sinusoidal crossings 1.484 / 1.584 / 1.382 (predicted interval 1.39-1.58),
Linear stable at 0.295-0.296.

## Re-review round (changed hunks only, by the raisers)

| Reviewer | Findings re-reviewed | Outcome |
|---|---|---|
| Codex gpt-5.6-sol | F1, F2, C3 | all RESOLVED; no new defects |
| Opus 5 | F2, O2-O8 | all RESOLVED; TWO defects introduced by the hunks: NEW-1 (S3, inconsistent summary interval mixing interpolated root with grid edge, excluding two of three per-seed crossings), NEW-2 (S4, unguarded null dereference in `_resolution_paragraph` for the no-crossing case) |
| Gemini 3.1 Pro | F1 | RESOLVED; no new defects |

Raw outputs: `rereview_codex-gpt-5.6-sol.md`, `rereview_opus-5.md`,
`rereview_gemini-3.1-pro-preview.md`; package `rereview_package_caseB.md`.

## Post-re-review handling of NEW-1 / NEW-2

Rule 4 permits no third review round, so the two hunk-introduced defects were
fixed by a bounded Codex micro-fix
(`scratchpad case-B-fix2 prompt`, report `/tmp/case-B-fix2.txt` content
summarized here: corrected sentence "The enclosing grid-and-seed uncertainty
interval is about τ 1.33 to 1.59."; null-guards + in-script self-test) and
verified MECHANICALLY by the driver rather than by reviewers:
- NEW-1: recomputed from the regenerated `e6_results.json` — union of the
  enclosing shifted-root grid bracket [1.333521, 1.584893] and the per-seed
  spread [1.381999, 1.584500], outward-rounded, equals [1.33, 1.59]; the
  printed sentence matches in section, README (mirror), kb local copy, and
  D62; the interval now contains all three per-seed crossings. The one line
  present only in the README relative to the kb paragraph is the mandated
  local-by-design explanation sentence (FIX-F1 spec).
- NEW-2: guard code inspected (`linear_u is None` / `sinusoidal_u is None` /
  nested `tau_interval_log_interpolated is None` branches); the in-script
  no-crossing self-test runs on every invocation and both scripts rerun
  exit 0.
This driver-verified status (reviewer sign-off structurally unavailable under
the no-third-round rule) is disclosed here and folded into ledger item 1.

## Final §4 verdict for the branch

Round-1 REVISE discharged: 11/11 cross-verified findings RESOLVED and
re-review-confirmed by their raisers; the two hunk-introduced defects fixed
and driver-verified. **Protocol outcome: REVISE resolved — branch proposed to
the author for merge, subject to the ledger:**
1. F2 + NEW-1 (S2 statistical): sign off the crossing-uncertainty treatment.
2. O2 (S2 statistical): sign off the reframed E6 evidential claim.
3. F1 variant: decide the kb/Wiki force-add question (first-ever tracked kb/
   file; otherwise the committed README mirror carries the resolution).
4. Kimi K3 round: run `kimi_k3_package.md`; any findings enter a fresh
   cross-verification cycle before merge.
Nothing merges autonomously (§4).

## Kimi K3 round (author-directed, 2026-08-12)

Channel: `moonshotai/kimi-k3` via OpenRouter (author's key), package-only, on
the ORIGINAL round-1 package (pre-fix state). **Verdict: REVISE (against the
round-1 state)** — 4 findings, raw output `round1_kimi-k3.md`. Collation
against the completed record:

- KB1 [S1] (kb/Wiki resolution absent from the diff): the FOURTH independent
  reporter of F1, already resolved in c15a65f (committed README mirror;
  kb/ gitignored by design). Convergent validation of the fix; no action.
- KB2 [S3] (occam=True sweep = raw minus log-volume, unverifiable from
  package): package-access limitation, and Kimi's own internal arithmetic
  cross-check passed. The equivalence was verified with repo access in
  round 1 (Opus: p2 minus p3 log Z equals each model's _log_reference_volume
  to ~1e-15). No action.
- KB3 [S4] (footnote em-dash tags): house citation convention, correctly
  hedged by Kimi itself. No action.
- KB4 [S4] (D3/D5 citation): driver-verified against the committed baseline
  — D3 defines the Z_Mx/model-prior machinery and D5 the reference-volume
  consistency, exactly the occam-convention provenance; the frozen notation
  file carries the same D3/D5/D17 citation. Citation stands; no action.
- Kimi's verified-correct list independently reconfirms every headline
  number, the crossing consistency, and full constraint compliance.

Net: zero new actionable findings; the one blocking item was already fixed.
The Kimi round strengthens F1's evidence (four independent reporters) and
adds an independent full-number verification pass.

## Author sign-off and Ready (2026-08-12)

The author signed off the statistical items by direct instruction: item 1
(the F2 + NEW-1 crossing-uncertainty treatment: τ ≈ 1.5 with the enclosing
grid-and-seed interval 1.33 to 1.59) and item 2 (the O2 reframing: E6 as a
machinery check with measured margins). Item 3 (kb force-add variant): the
committed README mirror stands as the resolution carrier; no kb/ file is
force-added. The Kimi K3 round is complete (fourth-reporter convergence on
the resolved F1; zero new findings). At the author's direction, PR #36
leaves Draft: **READY**.
