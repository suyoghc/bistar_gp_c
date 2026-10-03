# Project review 2026-09-26, project package — Kimi K3 (package-only channel), 2026-09-26

*Driver note: produced by `moonshotai/kimi-k3` via OpenRouter, prompt 69042 tokens, completion 9448 tokens, finish_reason `stop`, 324 s. Package: project-review brief + project map + HANDOFF-cases + HANDOFF sections 2-3 + manuscript sections 01-08 and appendices + D60-D68 + ledger rev 3 + fix1 synthesis rev 3. No text altered below this note.*

# Review — BI*/BMS*-GP project (Part B), package-only channel

Package contents note: this package contains no numbered source listings. All code-path line citations below are second-hand, quoted from D68, the ledger, or HANDOFF-code-review.md, and are tagged NEEDS-REPO-VERIFICATION where I could not read the file. Manuscript citations are to the tex files reproduced in the package. I ran nothing; every execution-dependent claim is PLAUSIBLE and tagged.

---

## 1. Verdict

**Code: REVISE** — the package evidence (D68, fix1_synthesis.md revision 3) is consistent with the fix passes having closed the nine collated defect classes without introducing an S1, but I could not verify one line of it, and the recorded pass-2 seams (optional `metric_name`, the `samples` dual meaning, the implicit roster, Case C's cross-branch import) remain open at the reviewed head.

**Project: NOT READY for submission.** Blocking list, in order:

1. **Ledger Item 3 (Case D, S1-class).** Section 6's stored comparisons come from a `fit_hmc` that targeted the prior. The manuscript section (06-case-D.tex) still presents the winner-count table at τ=1.778, the raw_draw_wins table (39.0/39.9/41.5 vs 98.7/94.6/92.1 percent), the cohort mean_G reference levels, and the τ-grid medians. The ledger's recommended option (v) — suspend the posterior interpretation now, regenerate the comparison layer as the endpoint — has no recorded author decision in this package, and PR #38 still stands OPEN (not Draft) in the project map against the ledger's "return #38 to Draft now" instruction.
2. **Ledger Item 4 (notation row, S2).** A-notation.tex still defines ψ as "a sampled function f with observation variance defines ψ = N(f(x), σ²_ψ I)", and 02-machinery.tex §2.1 still says "draw a function conditional on them", while the implemented row integrates the latent function out. Option (C) (amend the definition plus a disclosed sensitivity artifact) has no recorded decision; the Ḡ half is disclosed in 02-machinery.tex but the ψ half is not.
3. **Ledger Item 5 (reporting commitment, S2).** 02-machinery.tex commits every soft-transfer table to report tau-free draw-win fractions; neither the Case A pooled table (03-case-A.tex, §3.4 movement numbers) nor Case C's Table 5.1 (05-case-C.tex) carries them, and the E7 artifact reportedly carries neither ESS nor hard-win fields.
4. **Fix pass 2 incomplete** (required `metric_name` with its two callers, `check_external_targets` wiring into the Case A script, Case C's cross-branch import replacement, `samples` dual meaning, provenance-prose trim).
5. **Merge plan unexecuted**: seven open PRs (#36–#42), with a demonstrated A-before-C script dependency and unverified case-script compatibility with the fix-branch package API.

---

## 2. Code findings (Part A, as far as the package supports it)

I cannot review code from this package. The table gives a per-target judgement; everything marked NRV = NEEDS-REPO-VERIFICATION, PLAUSIBLE.

| ID | Target / module | Severity | Status | Location (as cited in package) | Claim |
|---|---|---|---|---|---|
| C1 | T1 Ḡ plug-in surrogate | S2 (disclosed) | CONFIRMED at manuscript level | `bistar_gp/laplace_evidence.py:135` (cited in HANDOFF §3); 02-machinery.tex | The surrogate is real and is now disclosed in section 2 ("The surrogate is not consistent for the per-draw average..."); the notation amendment remains open on #40's ledger and in A-notation.tex. |
| C2 | T2 discarded per-draw covariance | S1 (poster), none (manuscript) | CONFIRMED at manuscript level | `bistar_gp/debias.py:131,:206` (cited in D68); 07-debias.tex | Every band from `decompose_model_hmc`/`decompose_model_mcmc` was understated; the manuscript's only decomposition (Case E) deliberately used `decompose_additive_gp` with retained cross-covariance, so no manuscript number inherits the defect; the D58 poster cards do (Items 1–2, no recorded correction decision). |
| C3 | T3 global-shift stabilization | — | NRV, PLAUSIBLE-correct | `bistar_gp/bms_star.py:449-455` (cited in HANDOFF §3) | Cannot assess the cancellation argument; no paper number is known to depend on it. |
| C4 | T4 weight concentration | S2, partially addressed | PLAUSIBLE | D68 FIX-3; ledger Item 5 | `boltzmann_weight_ess` now exists per D68; the measured E7 concentrations (appendix kl_forward τ=0.1 ESS 1.15–2.47 per candidate) mean the Case A appendix sentence "collapses to approximately 0.000" rests on one to eight draws — no diagnostic stood beside it at commit time. |
| C5 | T5 evaluation grid (n_eval=60) | S3 | NRV, PLAUSIBLE | `bistar_gp/config.py:172` (cited in HANDOFF §3) | No grid-sensitivity analysis appears in any section or D-entry in this package; the choice is undocumented as a choice in the manuscript. |
| C6 | T6 metric scoping (W1) | S4 seam | CONFIRMED at manuscript level; code NRV | D68 FIX-7; fix1_synthesis.md pass-2 note | Prose honors W1 throughout. Code now carries `PRIMARY_METRIC`/`APPENDIX_METRICS` and a 1c warning on the implicit roster, but `metric_name` remains optional at the reviewed head and `metrics_v2.py:398` / `mcse_strategy.py:177` call without it; the mcse caller cannot supply the identity without an M2c contract change. |
| C7 | T7 M2bR banner | — | CONFIRMED honored in manuscript; code NRV | 03-case-A.tex; A-notation.tex | No section cites the withdrawn caches; `WITHDRAWN_CACHES` and `load_hmc_samples(allow_withdrawn=False)` exist per D68 but I cannot verify enforcement. |
| C8 | T8 universe firewall completeness | S3 | NRV, PLAUSIBLE | `bistar_gp/bms_star.py:368,:409,:480,:529` (cited in HANDOFF §3); D68 FIX-4 | D68 claims the firewall now precedes any metric call in every candidate-aware entry point; whether `soft_transfer`/`compute_G_matrix` primitives remain reachable across universes is unverifiable here. |
| C9 | T9 Case E script guards | — | PLAUSIBLE-correct, NRV | D67 review-fix addendum; fix1_synthesis.md | The AST guard, raise-on-unmatched-site, and jitter probe are documented in detail; the recorded oracle byte-identity against the fix package is the strongest single consistency signal in the package (three sha256, two consecutive runs). |
| C10 | T10 test adequacy | S3 | PLAUSIBLE | ledger Item 5; D68 | 79+17+4 fix1 tests exist per D68; the van Bork targets have a package module (`external_targets.py`) but are not yet wired into the Case A script (pass 2), so the manuscript's six-decimal Target B claim has no committed regression pin on the manuscript path. Unprotected claims: the Case C tie (Table 5.1 values), the Case D raw_draw_wins table, the E7 anchor row 0.183/0.192/0.441/0.184 (pinned only inside the E7 script's own assertion, per D61, NRV). |
| C11 | T11 sentinels | S2 closed, S3 residue | PLAUSIBLE, NRV | D68 FIX-5; `laplace_evidence.py:126-127,:253` (cited in HANDOFF §3) | Strict-raise/NaN replacement is recorded; the one S2 it surfaced (R7, an evaluation failure caught as an optimizer fault) was closed in 1b. Residual question for pass 2: does anything downstream inspect the new `OptimizerRecord` provenance, and did any committed run (e.g., `runs/occam_dial/`) ever take the fallback? D62 records all-converged, `n_clipped=0`, so PLAUSIBLE-clean on paper paths. |
| C12 | `aggregate_convention` finite-G guard | S3 | PLAUSIBLE, NRV | fix1_synthesis.md rev 3 (GLM F1) | Pre-1c, a NaN G matrix returned a uniform posterior under pooled/rowmin; 1c added an entry guard. Recorded as fixed; unverified. |

**Per-finding detail.** The two findings I can substantiate from the package alone are manuscript-level:

- **C1 detail (T1).** 02-machinery.tex now states the construction honestly: "It first collapses the sampled patterns into a single averaged pattern ψ̄ ... The computed object therefore reports the divergence from ψ̄ rather than the mean of the per-draw divergences, and the discrepancy between them varies with φ, so it does not cancel from a normalized comparison across candidates." That disclosure survives the fix passes because it is prose, not code. What does not survive: A-notation.tex still glosses Ḡ as "G averaged across data patterns, as a function of candidate parameters φ; the object inside Z_M" with no surrogate qualifier, and the ψ row still says "a sampled function f". Suggested change: adopt ledger Item 4 option (C) verbatim — commit a baseline for the untracked `00-notation.md` first, then amend the ψ, Ḡ, and τ-limit entries in one act. The pinning test would be the disclosed sensitivity artifact itself (implemented row vs sampled-function row on the exact E7 inputs, hashes committed).
- **C4 detail (T4).** The ledger's measured ESS values (pw_kl_vcal τ=0.1: 34/38/551/34; kl_forward τ=0.1: 1.15/2.25/2.47/1.14) quantify the concentration behind numbers printed in 03-case-A.tex. The manuscript's appendix attribution sentence ("collapses to approximately 0.000 for τ≤1") is a statement about one to eight effective draws; section 3.4 does not say so. Suggested change: ledger Item 5 option (a) — persist ESS and tie-aware hard-win credit in the E7 artifact and quote them beside the appendix sentence; the G = [[0,0],[10,11]] tie-rule pin is already specified in the ledger. NRV for artifact contents.

**Test that would pin C5/T5:** rerun the E7 anchor row at n_eval ∈ {30, 60, 120} on identical SIR draws and assert the Sin+Linear weight ordering is stable; no such pin is recorded anywhere in the package.

---

## 3. Project findings

| ID | Scope | Severity | Status | Location | Claim |
|---|---|---|---|---|---|
| P-1 | P1 | BLOCKER | CONFIRMED | 06-case-D.tex; ledger Item 3 | Section 6's comparison tables rest on prior-targeting HMC draws; the section still presents them as the HMC-mode practice run and PR #38 is still OPEN. |
| P-2 | P1 | BLOCKER | CONFIRMED | A-notation.tex; 02-machinery.tex §2.1–2.2; ledger Item 4 | Notation defines a sampled-function ψ row; the implementation integrates f out; 02-machinery's own scalar-variance clause "never holds on the implemented row" (ledger). Ḡ surrogate disclosed; ψ row not. |
| P-3 | P1 | MAJOR | CONFIRMED | 02-machinery.tex vs 03-case-A.tex §3.4, 05-case-C.tex Table 5.1 | The section-2 commitment to tau-free draw-win fractions in every soft-transfer table is unmet by both case tables in this package. |
| P-4 | P1 | MINOR | CONFIRMED | 07-debias.tex vs `bistar_gp/debias.py` (cited) | FIX-2 inheritance: manuscript clean by deliberate avoidance (Case E used `decompose_additive_gp`/`decompose_component`); the poster cards 6–8 inherit the understatement and have no recorded correction decision (Items 1–2). The manuscript does not mark the poster issue because the poster is out of manuscript scope; the D58 record needs Update 5 regardless. |
| P-5 | P2 | BLOCKER | CONFIRMED (two-channel verified, per ledger) | ledger "New finding for the collation" | Case C's script imports `e7_convention_sensitivity`, which exists only on the Case A branch; Case C's committed artifact does not regenerate from its own branch. Pass 2 (`aggregate_convention` import) is open. |
| P-6 | P2 | MAJOR | PLAUSIBLE, NRV | D68 (FIX-1 strict raise; `soft_transfer_weighted` raising; `PredictiveList`; `DecompositionResult.group`); D62 | Case A–D scripts were written against the pre-fix package. Case E is verified compatible (oracle byte-identical). Whether `occam_dial_figure.py`, `e6_nesting_monotonicity.py`, `haaf_nested_constraint.py`, `regret_curves_mopen.py`, `vanbork_external_validation.py`, `e7_convention_sensitivity.py` rerun clean against `ddf8c9d` is unrecorded in this package; the sentinel-to-raise change in the Laplace path is the highest-risk interaction for E6 (PLAUSIBLE-clean given D62's all-converged record). |
| P-7 | P2 | MINOR | CONFIRMED | project map; D60 Resolution | PR #39's title still reads "fork awaits author" although D60 Resolution (2026-08-12) closed the fork and 03-case-A.tex carries the resolution prose; title/record staleness. |
| P-8 | P3 | MAJOR | CONFIRMED | 06-case-D.tex; D64 | The practice artifacts escaped D6's withdrawal list; no D6 addendum exists in this package, and D64's scope premise ("the HMC-mode practice run") stands un-amended. |
| P-9 | P3 | MINOR | CONFIRMED | 08-discussion.tex; D67 F9 | "All four reviewer rounds are recorded for every case" was false when written (Case E round pending); D67's closure addendum makes it plausibly true now, but the synthesis-ledger item F9 has no recorded closure in this package. |
| P-10 | P3 | MINOR | CONFIRMED | A-notation.tex; 03/05 sections | Section-0 constraints otherwise honored: no withdrawn-cache citation, pw_kl_vcal primary with kl_forward appendix-confined, W4 framing explicit in 02 and 03, no Mauna material, no arrow glyphs in prose (math-mode `\rightarrow` in the notation table and "τ-to-zero" phrasing in 03 are within the rule as written). |
| P-11 | P4 | MAJOR | PLAUSIBLE, NRV | D68; fix1_synthesis.md | Suite counts (1346/5/1, 493 s) are driver-reported only; the known failure is the lock-drift test with a recorded decision (remove pypdf, do not weaken the test) that has no recorded execution. Two FIX1_FIXTURE_DIR-gated pins skip in the plain suite, so the sentinel/strict behavior they pin is unexercised in CI-default runs. |
| P-12 | P4 | S3-class (project MINOR) | PLAUSIBLE, NRV | D68 FIX-9 | The FIX-9 bit-identity test pins `aggregate_convention` to the Case A script's arithmetic — implementation-coupled by design; it pins equivalence, not correctness of either. |
| P-13 | P5 | MAJOR | CONFIRMED | 07-debias.tex; 03-case-A.tex §3.5; 02-machinery.tex footnote | A reader cannot regenerate: `runs/prior_sensitivity/stage_a_toy_elicited.json` (cited as uncommitted local material carrying the single-mode claim), `runs/viz_unification/p3_priors_canonical/` (0.992 reach paragraph, D65-disclosed exception), the mechanism-figure arm ("uncommitted in this repository"), and the tex build itself (`build_tex.py` and the section-07 registry fix F8 are untracked, driver-side). |
| P-14 | P5 | BLOCKER | CONFIRMED | ledger Item 3 (Codex F4 fold) | Case D's stored artifacts cannot be honestly regenerated: on the current package the single-kernel site's HMC samples are dropped/rejected, so a naive rerun "would silently score default-kernel predictives". Regeneration requires the ledger's hardened-producer prerequisite. |
| P-15 | P5 | MINOR | CONFIRMED | D67 vs package 07-debias.tex | The tex staleness D67 recorded is resolved in this package's copy (section 07 carries the full text), so `build_tex.py` was rerun after the fix pass; the registry fix is untracked, so the regeneration chain is reproducible only in the author's worktree. |
| P-16 | P6 | BLOCKER | CONFIRMED | ledger; project map | Decision debt: ledger Items 1–5 all lack recorded author decisions as of 2026-09-26; pass 2 unstarted; seven PRs open. |

### P2 merge plan

Order I would use, with demonstrated conflicts:

1. **#42 (fix branch) first, after fix pass 2 completes.** Everything else must be re-verified against it; pass 2's Case-C import replacement removes the cross-branch hazard at the source.
2. **#39 (Case A).** Depends on pass 2 (`check_external_targets` wiring) and on Item 4/5 decisions (sensitivity artifact, ESS/draw-win table amendments). Title correction (P-7) at merge.
3. **#37 (Case C), strictly after #39** unless pass 2 lands first: the demonstrated conflict is `experiments/haaf_nested_constraint.py:46` importing `e7_convention_sensitivity`, absent from main and from Case C's own branch (ledger, verified by two channels). Merging C before A leaves a broken import on main. DECISIONS.md conflict: none — D63 vs D60/D61/D65 are disjoint numbers.
4. **#36 (Case B).** The ledger requires "a refreshed dependency and wording verification after the package fixes merge"; content files are disjoint from A/C, so a mechanical merge, but artifact regeneration against `ddf8c9d` is unproven (P-6).
5. **#41 (Case E).** Lowest risk: the oracle is byte-identical against the fix package (D68, recorded three times).
6. **#38 (Case D) last among cases, gated on Item 3.** If option (v)/(iii) is taken, the section is rewritten against regenerated artifacts; merging before that decision imports a known S1-class exposure into main.
7. **#40 (synthesis) final**, after all case sections settle, since 01/02/08 quote the case outcomes and carry the F9 sentence and the Item 4 notation amendments.

Textual merge conflicts are minimal (disjoint section files, disjoint D-numbers); the real conflicts are semantic: the package API changes (P-6) and the unamended notation (P-2).

---

## 4. Verified-correct list (package-level checks)

- **No D-number collision** across the seven divergent DECISIONS.md files: D60/D61/D65 (A), D62 (B), D63 (C), D64 (D), D66 (synthesis), D67 (E), D68 (fix) are pairwise disjoint. CONFIRMED from the collected log.
- **M2bR banner honored in every tex section**: SIR 0.441 and "corrected NUTS ≈ 0.42" appear as separate-but-agreeing (A-notation.tex); no withdrawn-cache path appears in any section. CONFIRMED within the package.
- **W1 honored in prose**: kl_forward confined to appendix framing in 03-case-A.tex and 02-machinery.tex. CONFIRMED.
- **W4 honored**: the viz_unification reach paragraph (03-case-A.tex §3.5) and the mechanism illustration (02-machinery.tex) both carry explicit informative-configuration, MAP-based, methods-validation framing. CONFIRMED.
- **No Mauna material** in any of sections 01–08, A, B. CONFIRMED.
- **D60 fork resolution propagated**: 03-case-A.tex carries the dial-resolution prose where the placeholder stood; no `[FORK-DECISION-PLACEHOLDER]` remains in the tex. CONFIRMED (PR title stale, P-7).
- **Ḡ surrogate disclosure** in 02-machinery.tex is statistically accurate as written, including the non-cancellation statement. CONFIRMED.
- **Case E avoidance of the defective decomposition routines** is real at the manuscript level and is the correct construction (joint posterior on summed kernel blocks, cross-covariance retained, mixture quantiles). CONFIRMED as described; NRV for code.
- **The Remark 1 one-sidedness argument** (02-machinery.tex) is mathematically correct as stated, and Case C's design (shared candidate pools forcing exact equality at shared optima) is the right way to keep optimizer noise out of a containment identity. CONFIRMED.
- **Case D's affine identity claim** (pw_nll = 0.5·log(2πσ²) + pw_mse/(2σ²), max abs error 1.78e-15 over 300 pairs) is internally consistent with the tables printed in 06-case-D.tex; the scale-invariance warning derived from it is sound. CONFIRMED as algebra; the underlying G values inherit P-1.
- **Case E oracle byte-identity** (three sha256, recorded in the project map, D68, and fix1_synthesis rev 3 with consistent values: 65c9ff5f…, c1153549…, 7096cd6e…). Recorded consistently in three places; execution NRV.

---

## 5. Recommendations (priority order, two-week horizon)

1. **Author decisions on ledger Items 3 and 4, in that order** (0.5 day of author time; the options and defaults are fully specified). Unblocks: everything else; PR #38 disposition; the notation amendment. Recommended defaults as recorded: Item 3 option (v) with (iii) as endpoint; Item 4 option (C).
2. **Execute the Item 3 immediate half**: PR #38 to Draft, dated D6 addendum extending the withdrawal to `experiments/practice_EvansEtAL/results_hmc/`, D64 scope-premise addendum (0.5 day, Notes/PR operations only). Unblocks: honest PR statuses; stops the S1-class exposure from deepening.
3. **Fix pass 2** (1–2 days): required `metric_name` via ledger option (i) (keep the M2c contract, pass the name at `metrics_v2.py:398`), Case A `check_external_targets` wiring, Case C import switch to `aggregate_convention`, `samples` dual-meaning resolution, provenance-prose trim. Unblocks: #42 merge, the A→C ordering hazard.
4. **Item 5 option (a)** (0.5–1 day compute + prose): extend the E7 artifact with ESS, tie-aware hard-win credit, attainment; amend §3.4 and add Case C's one diagnostic line (derivable from saved counts, no LOO rerun). Unblocks: #39 and #37 re-approval.
5. **Item 4 option (C) execution** (1 day): commit `00-notation.md` baseline, amend ψ/Ḡ/τ-limit entries, commit the E7-row sensitivity script and artifact. Unblocks: #40.
6. **Merge in the order of section 3** (1 day mechanical, plus re-verification runs: suite ~8 min, Case E oracle ~1 min, case-script reruns NRV for runtime). Unblocks: a single coherent head for assembly.
7. **Case D regeneration** (ledger estimate: order of an hour of compute plus a fresh §4 review round; budget 3–4 days elapsed). Unblocks: #38 and section 6's survival in any form.
8. **D58 poster correction act** (Items 1–2, option B): separate repository, bounded correction commit (1–2 days). Not manuscript-blocking but a dissemination-correction risk that grows with time.
9. **Commit the tex toolchain** (`build_tex.py`, registry, notation file) (0.5 day). Unblocks: P-13's reader-reproducibility gap for assembly.
10. **Grid-sensitivity pin for T5** (0.5 day): E7 anchor at three grid sizes. Unblocks: closing the last undocumented default on the paper path.

---

## 6. Commands run and outcomes; what I could not run

**Commands run: none.** This channel received no repository access, no shell, and no source listings; the package above is the entire evidence base.

Could not run, and therefore could not verify:

- The test suite (`python -m pytest tests/ -q -p no:cacheprovider`; driver-reported 1346 passed / 5 skipped / 1 failed, 493 s at pass 1c). Suite counts, skip gating, and the known failure are all NRV.
- The Case E oracle (driver-reported byte-identical, three sha256). NRV.
- Every code-path citation (debias.py:131/206, bms_star.py:368/409/449-455/480/529, laplace_evidence.py:126-127/135/253, config.py:172, model.py:76-78/99-104, metrics_v2.py:398, mcse_strategy.py:177, decompose.py:93). All quoted second-hand from D68, the ledger, or HANDOFF §3; all NRV.
- Branch-topology claims I took from the ledger's `git ls-tree` verification (the Case C cross-branch import). I treated it as CONFIRMED because two independent channels verified it and the fix list embodies it, but I did not run git.
- Whether the case scripts on #36–#39 rerun against `ddf8c9d` (P-6), whether any committed run ever took a sentinel fallback (C11), and the FIX1_FIXTURE_DIR-gated pins' behavior (P-11). All NRV.
- The other channels' output files in `runs/project_review_2026_09/`, per constraint; no cross-channel comparison was possible.

Where the package's internal records conflicted with each other I flagged the conflict rather than resolving it (PR #38 status, P-1/P-8; PR #39 title, P-7; the F9 sentence, P-9). Where they agreed I treated execution-dependent content as PLAUSIBLE and said so.

Kimi K3 (package-only channel)
