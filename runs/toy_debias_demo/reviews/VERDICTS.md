# Case E (paper/case-e-debias) — §4 review record

Branch tip reviewed: 8f1326d (section 07 toy debias demonstration — D67).
Package: `review_package_case_e.md` (identical for every reviewer; §0 verbatim
+ driver facts + committed section/D67/results.json/README/script + the
synthesis 08 excerpt for the known 8.5-footnote context).

## Reviewer channels

| Reviewer | Channel | Round-1 verdict |
|---|---|---|
| Opus 5 | fresh in-session subagent, repo read access | REVISE (15 findings; independent bit-exact reproduction of every committed number) |
| Gemini | `gemini-3.1-pro-preview`, thinkingLevel HIGH, package-only | APPROVE (attempt 1 thin, 1 finding, preserved as `round1_gemini_attempt1.md`; attempt 2 substantive per the author's established retry precedent, 7-point checklist clean, 0 new) |
| Kimi K3 | `moonshotai/kimi-k3` via OpenRouter, package-only | APPROVE (2 findings; full numbers audit clean; `decompose_model_hmc` rejection endorsed) |
| Codex GPT 5.6 sol | usage-locked to 2026-08-18 | ABSENT (disclosed; substitution pattern as in the synthesis round) |

Raw outputs: `round1_*.md`, checks in `check_*.md`. Verdict conflict resolved
by rule 3 (queue non-empty; REVISE governs).

## Collation and cross-verification

Two-reporter clusters (rule 1, straight to queue):
- Acceptance-rate presentation (Kimi K2 + Opus F14): pyro's 0.992/0.998 is a
  move fraction, not the targeted mean Metropolis acceptance 0.8.
- Role-noun style in ancillary text (Kimi K1 README + Gemini attempt-1 GE1
  script docstring): same defect class, both verbatim-verified by the driver.

Single-reporter findings (rule 2; default-refuted; checker never the
originator; all Opus-raised). Numeric claims inside the findings were
independently recomputed by the driver from the committed entry points before
checking: composite coverage 0.8209 (165/201), bias coverage 201/201, bias
band mean width 1.4584026383414934, residual drift RMS 0.3046 (79.0 percent
removed), oracle-debiased RMSE 0.3210, unremoved-drift share 57 percent — all
matched the finding text bit-exactly.

| ID | Sev | Substance (abbreviated) | Checker | Outcome |
|---|---|---|---|---|
| F1 | S2 | "multi-basin" misattributes D12 (scoped to `informative`); `stage_a_toy_elicited.json` certifies coherent single-mode geometry, mode == this run's MAP to ~1e-9; repeated in four artifacts | Driver (artifact evidence: stage_a JSON `coherent_geometry: true`, `valleys: []`, one verified mode, `pooled_is_mass: 1.0`; D12 text scoped) | CONFIRMED |
| F2 | S2 | Coverage reported for debiased band only; omitted comparators reverse the reading | Kimi | REFUTED: the sentence makes an absolute statement with a correct caveat, no comparative claim; omitted numbers would favor the debiased arm, so nothing misleads. Enrichment noted on the ledger (driver-verified numbers preserved in this record). REJECTED (logged) |
| F3 | S2 | Uncertainty-floor sentence asserts N-asymptotics from one fixed N=20 run | Kimi | CONFIRMED (one-parameter bias family under a proper prior can sharpen with N; restrict to the measured statement or add an N-sweep) |
| F4 | S3 | "either component alone" true but the bias band width is not in the artifact | Driver (recomputed 1.4584) | CONFIRMED |
| F5 | S3 | "removes most of it" supported by the wrong statistic (71.9 percent is RMSE reduction, not displacement removed; direct figure 79.0) | Kimi | REFUTED: true under every candidate statistic; both framings already supplied; rewrite is preference. REJECTED (logged) |
| F6 | S3 | Latent bands labeled "posterior predictive"; "describes well" unquantified | Kimi | REFUTED: the latent-band convention is explicitly disclosed in section, README, and JSON; terminology looseness, not a methods error. Cosmetic caption residue ("latent posterior predictive") left to assembly. Checker note: the claimed F2/F6 tension in the refutation text is a misreading (both fixes pull the same direction); the refutation core stands without it. REJECTED (logged) |
| F7 | S3 | Panels lack sharey; the width contrast the argument rests on is invisible | Driver (line 392: sharex only) | CONFIRMED |
| F8 | S3 | build_tex.py registries missing 07 branch pin + figure entries; regeneration would silently emit the stub | Driver (registry inspection) | CONFIRMED — fixed driver-side (untracked tooling): 07 pinned to paper/case-e-debias, FIGURES/FIGURE_PATHS entries added, tier map extended for 🟡/🟣/🔵 |
| F9 | S3 | Synthesis 8.6 "All four reviewer rounds are recorded for every case" becomes false once Case E is section 7 | Gemini | CONFIRMED — assembly-ledger item (synthesis branch), paired with the known 8.5 footnote staleness |
| F10 | S3 | Evaluation-mitigation "one object" claim never exhibited; free cross-link to section 3.4's 0.441 on the same instance/config | Gemini | CONFIRMED |
| F11 | S3 | Empirical-Bayes character of `toy_elicited` omitted where coverage is reported | Gemini | CONFIRMED |
| F12 | S4 | `apply_hp_value` return discarded (silent-wrong-answer path); jitter-rescued solves indistinguishable in n_ok | Driver (line 279) | CONFIRMED (latent) |
| F13 | S4 | Sampler settings in results.json are hardcoded mirrors, not observations | Driver (lines 124-125, 227) | CONFIRMED (latent) |
| F15 | S4 | Divergences attached to "across the four hyperparameters" (per-trajectory quantity) | Driver (manifest) | CONFIRMED |

## Fix queue (twelve items, substitute implementer)

FIX-1 init-provenance correction in four artifacts + stage_a citation via the
disclosed local-material pattern (F1) · FIX-2 floor sentence restricted to the
measured N=20 correlation statement, component moments added to the artifact
(F3) · FIX-3 bias band width 1.458 added and quoted (F4) · FIX-4 sharey +
width annotations (F7) · FIX-5 section 3.4 cross-link (F10) · FIX-6
empirical-Bayes conditioning + coverage inheritance (F11) · FIX-7 loud
unmatched-site failure + jitter count (F12) · FIX-8 library-constant guard
(F13) · FIX-9 move-fraction relabel + README clause (F14+K2) · FIX-10
diagnostics sentence restructure (F15) · FIX-11 role-noun sweep in README +
docstring (K1+GE1) · assembly ledger: F9 + the 8.5 footnote wording (synthesis
branch, at assembly); F8 done driver-side.

Rejected with logged refutations: F2, F5, F6.

## Author-adjudication ledger (open at merge proposal)

1. F1 (S2, statistical): sign off the init-provenance correction (the
   misattribution gratuitously discounted the run's own posterior summaries);
   decide whether `runs/prior_sensitivity/stage_a_toy_elicited.json` should be
   committed as evidence (currently cited via the disclosed local-material
   pattern to avoid colliding with a future prior-sensitivity commit).
2. F3 (S2, statistical): sign off the floor-sentence restriction, and decide
   whether to commission the optional N-sweep (20/50/200, ~1 min each) that
   would test the floor claim outright.
3. F2 enrichment option: the driver-verified composite/bias coverages (0.821,
   1.000) exist in this record; adding them to the artifact and prose was
   REFUTED as a required fix but remains available at the author's direction.
4. Substitute-implementer + driver-verification deviations (Codex locked to
   2026-08-18): ratify, or commission a Codex re-review after the lock lifts.

(Continued below after the fix pass and re-review round.)

## Fix pass 1 (rule 4, substitute implementer) — commit a5b9cf8

All twelve queue fixes implemented by the disclosed substitute (a fresh Opus
subagent; Codex usage-locked). One implementer deviation, endorsed: the
round-1 "MAP matches the verified mode to ~1e-9" was not reproducible; the
actual maximum discrepancy is 1.690e-8 (SE lengthscale), so the committed
prose says "within 2e-8". Driver verification: independent rerun reproduced
all three artifacts byte-identically (results.json 65c9ff5f…, figure
c1153549…, README 7096cd6e…); all 24 pre-existing numbers bit-identical; the
nine derived additions present; the acceptance-key rename complete; jitter
count 0/1000.

## Re-review round (changed hunks, by raisers)

| Reviewer | Findings | Outcome |
|---|---|---|
| Opus 5 (raiser channel) | F1, F3, F4, F7, F10, F11, F12, F13, F14, F15 | all ten RESOLVED (repo-verified, incl. executing the FIX-8 guard with three negative controls and confirming its own round-1 1e-9 figure was wrong); SEVEN new defects: N1 (S3, cross-link conflates the parametric candidate with the GP kernel posterior) + N2/N3 folded into its rewrite (forward reference; bare 0.441 without the aggregation convention), N4 (band "scored against" vs "conditions on"), N5 (caption silent on the shared y axis), N6 ("grid-averaged" qualifier), N7 (D67 addendum field-count sentence undercounts the JSON delta) |
| Kimi K3 | K1, K2 | both RESOLVED (relabel judged "arguably more accurate" than its own proposal); ONE new S4-low: the jitter-probe claim may cover fewer factorizations than the decomposition performs |
| Gemini | GE1 | RESOLVED; seven-point checklist on the changed hunks clean; zero new |

Kimi's new finding REFUTED by driver adjudication with source evidence:
`decompose_additive_gp` performs exactly one factorization (the summed
training matrix; "Single Cholesky, shared across all components",
`bistar_gp/decompose.py:93`), and the demo never calls
`sample_from_component`, the only other Cholesky site — so the probe covers
every factorization the decomposition executes, as Opus's F12 re-verification
independently concluded. REJECTED (logged).

## Post-re-review micro-fix (four items, substitute agent)

MF-1 the cross-link paragraph rewritten per the raiser's text (grades
candidates AGAINST the induced posterior; candidate shape mirrors the split
"without being the object decomposed"; "described below"; "with pooled
aggregation" qualifier) — closes N1+N2+N3; MF-2 "the band conditions on"
(N4); MF-3 caption records the shared y axis and the full readout list (N5);
MF-4 "grid-averaged correlation" (N6). N7 is corrected in the D67 closure
addendum (the fix-pass addendum text is a committed record; per the author-
record policy the correction is a dated addendum, not an edit). Driver
verified all four passages, no new numerals beyond 0.441 (committed in Case
A), style greps clean.

## Final §4 verdict for the branch

Round-1 REVISE discharged: 19 raised items collated (2 two-reporter clusters,
13 singles checked adversarially or on artifact evidence — 10 confirmed, 3
refuted with logged refutations); twelve queue fixes RESOLVED by all raisers;
eight hunk-introduced defects (7 Opus + 1 Kimi) resolved as four micro-fixes,
one addendum correction, and one evidence-backed refutation. **Protocol
outcome: REVISE resolved — branch proposed to the author for merge, subject
to the ledger:**
1. F1 (S2, statistical): sign off the init-provenance correction; decide
   whether to commit `runs/prior_sensitivity/stage_a_toy_elicited.json` as
   evidence (currently cited via the disclosed local-material pattern).
2. F3 (S2, statistical): sign off the floor-sentence restriction; optionally
   commission the N-sweep (20/50/200) that would test the floor claim.
3. F2 enrichment option: driver-verified composite/bias coverages (0.821,
   1.000) available at the author's direction.
4. Substitute-implementer + driver-verification deviations (Codex locked to
   2026-08-18): ratify, or commission a Codex re-review after the lock lifts.
5. Assembly ledger (synthesis branch, at assembly): F9 (8.6 "all four
   reviewer rounds for every case" scoping) and the 8.5 footnote "supplies no
   reported number" staleness.
Nothing merges autonomously (§4).
