[CHANNEL OVERRIDE, PACKAGE-ONLY]
You are the GLM 5.3 channel. You cannot run code or open the repository;
everything you may use is in this package. Claims needing execution or files
not included here must be tagged NEEDS-REPO-VERIFICATION and marked PLAUSIBLE.
This package covers PART B (project) of the brief, with Part A only as far as the manuscript text supports it; the package sources are in a separate package reviewed by the same channel. Return the complete review as your reply in the
brief's OUTPUT FORMAT (the single-output-file instruction is replaced by
"return the review text"); in section 6 state what you could not run. Sign
only as "GLM 5.3 (package-only channel)". Line numbers in the listings are
the file's own line numbers at ddf8c9d; cite them as path:line.

==================== BRIEF ====================
[TASK CONTEXT]
You are one of five independent reviewers of the CURRENT CODE AND PROJECT
STATE of the BI*/BMS*-GP repository (Chandramouli & Shiffrin framework:
Gaussian-process data priors, G divergence, Boltzmann soft transfer,
Laplace/MC/IS model evidence, additive-kernel decomposition; a journal
manuscript in preparation). Review date 2026-09-26.

Code under review: the fix-branch head `ddf8c9d` on `fix/code-review-2026-09`
(PR #42, a fast-forward of `main` 7154083 plus fix passes 1/1b/1c of the
2026-09 implementation review), checked out read-only at
  /Users/sc8918/Documents/GitHub/bistar_gp_c-fix
The MAIN worktree /Users/sc8918/Documents/GitHub/bistar_gp_c (read-only) is on
`paper/case-e-debias` and holds, untracked, the manuscript apparatus:
docs/paper-sie-jmp/{00-notation.md, HANDOFF-cases.md, HANDOFF-code-review.md,
prompts/, build_tex.py, tex/sections/*.tex}. Six unmerged paper branches
(PRs #36-#41) carry the case sections and decision entries D59-D67; read them
with read-only git only (`git show origin/<branch>:<path>`, `git log`,
`git diff`, `git merge-tree`). The project map (branches, PRs, D-entry
inventory, runs/, suite counts) is in runs/project_review_2026_09/project_map.md.
Prior review records (runs/code_review_2026_09/, the case branches' review
records) are CONTEXT, not evidence, and must not bound your review: derive
your own findings, on the whole project, not only the fix-pass surface.

[SCOPE, PART A: CODE]
Does the package at `ddf8c9d` compute what the manuscript claims? Standard:
docs/paper-sie-jmp/HANDOFF-code-review.md section 2; named targets T1-T11 of
its section 3 remain in scope, now against the post-fix code. Specification:
tex/sections/02-machinery.tex (and the case sections where they state what a
number is), 00-notation.md. Hunt for: wrong mathematics, contract breaks,
silent fallbacks that substitute a different estimator, sentinels that can
win, path-dependent results (draw order, start order, dict order), numerical
regimes that matter on the paper paths (N=20 toy, tau in [0.1, 100], KL and
pw_kl_vcal magnitudes), tests that would pass against wrong code, and the
seams the fix passes left (the required `metric_name` deferred to pass 2, the
`samples` dual meaning, the implicit metric roster, provenance prose).

[SCOPE, PART B: PROJECT]
P1 Manuscript-code consistency: for each section 01-08, do the numbers,
   conventions and terms come from code at this head via a named
   experiments/ script into a runs/ artifact, and do the section's claims
   survive the fix passes (in particular FIX-2: every earlier band from
   decompose_model_hmc/mcmc was understated; which manuscript or poster
   statements inherit that, and are they marked)?
P2 Branch topology and merge plan: seven unmerged branches whose
   Notes/DECISIONS.md diverge (D59-D67 on paper branches, D68 on the fix
   branch), the A-before-C script dependency, package API changes on the fix
   branch versus what the case scripts on the paper branches expect
   (strict extraction now raises where scripts once relied on dropped draws;
   `compute_induced_prior` weighting; `soft_transfer_weighted` raising;
   `PredictiveList`; `DecompositionResult.group`). State the merge order you
   would use and the conflicts or breakages you can demonstrate.
P3 The record: HANDOFF-cases.md section 0 constraints (M2bR banner, W1
   primary metric, W4 framing, no Mauna material) honoured in the sections;
   open ledger items; D-entry statuses versus reality; the fix pass 2 list.
P4 Test suite: value of the tests on the paper paths (tautological or
   implementation-coupled tests; missing pins), the known failure, the
   fixture-gated skips, runtime.
P5 Reproducibility and provenance: runs/ artifacts versus the scripts that
   claim to produce them; hashes; the Case E oracle; what a reader of the
   manuscript could not regenerate.
P6 Publication readiness: the blocking list, the risks, and what you would
   do in the next two weeks, in priority order with effort estimates.

[PROTOCOL]
- Repo-access channels: run the suite once in the fix worktree
  (`cd /Users/sc8918/Documents/GitHub/bistar_gp_c-fix && python -m pytest
  tests/ -q -p no:cacheprovider`; expect 1346 passed, 5 skipped, 1 failed =
  the known dependency-lock drift test; report your counts and runtime), then
  probe. Package-resolution trap: `bistar_gp` is an editable install pointing
  at the MAIN worktree; a probe script outside the fix worktree imports the
  UNFIXED package unless you force the path (`PYTHONPATH=/Users/sc8918/
  Documents/GitHub/bistar_gp_c-fix` or `sys.path.insert(0, ...)`). Print
  `bistar_gp.__file__` once per probe.
- Reproduce every claim (path:line at ddf8c9d, or branch:path:line for paper
  branches, plus a command and an output excerpt). Mark each finding
  CONFIRMED (reproduced) or PLAUSIBLE (argued). Package-only channels tag
  execution-dependent claims NEEDS-REPO-VERIFICATION.
- Severity, code: S1 a manuscript-path number is wrong; S2 wrong under a
  reachable configuration; S3 latent, guarded; S4 hygiene. Severity,
  project: BLOCKER (must be resolved before submission), MAJOR (would draw a
  referee's objection or a retraction risk), MINOR.
- Adversarial stance toward every record, report and test in the repository.

[CONSTRAINTS]
- READ-ONLY on both worktrees: create, edit or delete nothing under either,
  except your single output file below; no git add/commit/stash/checkout/
  reset/branch/rebase/worktree anywhere; never touch stash@{0}.
- Scratch: only the directory named in your channel override.
- No network, no new dependencies, no Mauna Loa inference, no change to the
  dependency lock. Do not open the other channels' output files in
  runs/project_review_2026_09/ (some may exist while you work).
- Hard constraints of HANDOFF-cases.md section 0 apply to what you write:
  the informative-config HMC caches are withdrawn (never cite
  runs/fit_method_metric_comparison/samples_hmc.npz or
  runs/toy_tau_metric_comparison/); pw_kl_vcal is the primary metric and
  kl_forward appendix-only; no arrow glyphs; no "X is the Y" role-noun
  constructions; no "lives/sits" for abstracta.

[OUTPUT FORMAT]
Write EXACTLY ONE file (the path is in your channel override) with:
1. Verdict. Code: APPROVE / REVISE / REJECT, one sentence. Project: READY /
   NOT READY for submission, with the blocking list.
2. Code findings: summary table (ID, target or module, severity,
   CONFIRMED/PLAUSIBLE, path:line, one-line claim), then per-finding detail
   (what is wrong, reproduction, suggested change, the test that would pin it).
3. Project findings: summary table (ID, P1-P6, severity, CONFIRMED/PLAUSIBLE,
   location, claim), then detail, including your merge plan for P2.
4. Verified-correct list (what you checked and found right, so the
   synthesizer can see coverage).
5. Recommendations: prioritized, each with an effort estimate and what it
   unblocks.
6. Commands run and their outcomes; what you could not run.
Sign only with your channel label. Do not claim to be another reviewer.

[SUCCESS CRITERIA]
Every T1-T11 target and every P1-P6 item has an explicit judgement; every
finding carries a reproduction or is marked PLAUSIBLE; the suite counts are
reported (repo-access channels); the single output file exists.

==================== PROJECT MAP ====================
# Project map at review time (generated 2026-09-26, read-only git)

## Code under review
- Fix branch head: ddf8c9d on fix/code-review-2026-09 = PR #42 (OPEN), fast-forward of main 7154083.
- Worktrees: main worktree /Users/sc8918/Documents/GitHub/bistar_gp_c on paper/case-e-debias (a07e61e) with local Notes edits and untracked docs/paper-sie-jmp (notation, HANDOFFs, prompts, tex build); fix worktree /Users/sc8918/Documents/GitHub/bistar_gp_c-fix (clean).

## Branches (remote heads, last commit date)
- origin/fix/code-review-2026-09 ddf8c9d 2026-09-08 review(2026-09): synthesis note on the required metric_name cost for fix pass 2 (PR #42)
- origin/paper/case-e-debias a07e61e 2026-08-13 paper(case-e): re-review closure — four micro-fixes, §4 record committed, D67 closure addendum
- origin/paper/synthesis-sections 096dd01 2026-08-12 paper(synthesis): re-review closure — three micro-fixes, §4 record committed, D66 review addendum
- origin/paper/case-a-vanbork 76135be 2026-08-12 paper(case-a): author-directed figure — Target A dial + Target B convergence from the committed artifact
- origin/paper/case-d-mopen ff4c353 2026-08-12 paper(case-d): author sign-off — statistical items closed, Ready
- origin/paper/case-c-haaf 0adde90 2026-08-12 paper(case-c): author sign-off — statistical items closed, Ready
- origin/paper/case-b-occam-dial 32c0a58 2026-08-12 paper(case-b): author sign-off — statistical items closed, README mirror stands, Ready
- origin/main 7154083 2026-07-26 Merge pull request #35 from suyoghc/notes/d58-post-closeout
- origin/notes/d58-post-closeout 9742c43 2026-07-26 notes(d58): D58 Update 4 factual closeout — run/evidence/render record for job 11572645; audited with one bounded correction pass (ACT 3, Notes-only)
- origin/evidence/d58-poster-render-11572645 783e434 2026-07-25 evidence(d58): adopt author-rendered poster figures for job 11572645 — four boundary-enforced PNGs + FIGURES.sha256 (render-only; no interpretation)
- origin/evidence/d58-poster-run-11572645 18a1c55 2026-07-25 evidence(d58): raw poster-run evidence for Slurm job 11572645 at M58 — six-artifact census + Slurm logs + sacct capture (A1-A7 PASS; poster-only, non-paper-grade)
- origin/feat/d58-poster-prep ed475cc 2026-07-24 docs(d58): Notes-only truth correction — focused-suite split 53+13+13; D58 Update 3 records the final confirmation (F1-F4 CONFIRMED-CLOSED, one MINOR count finding, author-adjudicated)
- origin/docs/d19-v123-measured-results 8c98e20 2026-07-23 docs(d19-v123): record Draft PR #31 in the pre-identified Notes line (Notes-only tail)
- origin/evidence/d19-a7-timing-11517022 bbc75ec 2026-07-23 docs(d19-a7): C57 — bounded non-evidence correction of the recovery record §3 wording + review Notes
- origin/fix/d19-a7-d56d-condition 2386d06 2026-07-23 docs(d19-a7): D56 Update 12 — D56d review gate + single bounded correction pass (Notes-only tail after R56d)
- origin/fix/d19-a7-d56c-env 2369477 2026-07-22 docs(d19-a7): D56 Update 10 — D56c review round, option-(b) correction, both fixes CONFIRMED-CLOSED (Notes-only tail after R56c)
- origin/fix/d19-a7-d56b-ps1 b5ccb3e 2026-07-22 docs(d19-a7): D56 Update 8 — exact-head round (SPLIT verdict) + author-accepted continuation residual; Notes-only truth correction
- origin/evidence/d19-a7-failed-attempt-11485635 c6f499c 2026-07-22 evidence(d19-a7): D56 Update 5 — attempt 1 (job 11485635) FAILED pre-cell; four-file failure evidence byte-pinned at runs/d19_a7_failed_11485635/ per narrow author clarification
- origin/docs/d19-a7-d56a-launch-closure 5c44ca0 2026-07-21 docs(d19-a7): D56a correction pass — close the audit BLOCKER with item-6 total-surface closure (H'..M56a name-diff limited to Notes/, docs/, and the blob-pinned guard file)
- origin/feat/d19-a7-d56-execution-protocol 5af82a9 2026-07-21 docs(d19-a7): D56 Update 3 — Ready-gate full suite caught the slurm-argparse guard incompatibility; test-only correction b50350e recorded; full suite 1157/2; allowlist now seven files
- origin/feat/d19-a7-d55-bench-timing-firewall f7f9ec2 2026-07-21 test(d19-a7): D55 Update 1 — pin FIREWALL_NOTE and DESIGN_LABEL to literals
- origin/chore/chatlog-session-d54 8162c73 2026-07-20 docs(notes): CHATLOG — 2026-07-20 session (post-M2cR D19 disposition; D54 cascade retirement PR #21 MERGED 7277b421; A7/D55 authorized-unstarted)
- origin/feat/d19-m2cr-d54-cascade-retirement c761320 2026-07-20 docs(d19-m2cr): D54 Update 1 — exact-head acceptance audit APPROVE; Notes-only Ready closure
- origin/feat/d19-m2cr-r4-diagnostic-execution b1c6e49 2026-07-19 docs(d19-m2cr): R5 record audit CLOSEOUT — Fable Max APPROVE_RECORD at evidence head f78d16a; §6.3 first match row 2 (PRESERVE_STOP; evidence_incomplete_no_amendment); author confirmed; Notes-only (D53)
- origin/feat/d19-m2cr-r3a-launch-vehicle 4440a55 2026-07-19 docs(d19-m2cr): D51 Update 1 computation-provenance wording correction (author-directed)
- origin/feat/d19-m2cr-r3-diagnostic-protocol 70e8172 2026-07-18 docs(d19-m2cr): precise computation-provenance wording (author-directed correction)
- origin/feat/d19-m2cr-r2a-evidence-ceilings 5ab5743 2026-07-18 docs(d19-m2cr): D49 Update 1 (R2a complete) + SCRATCHPAD alignment + report figure sync at final regen
- origin/feat/d19-m2cr-r2-infrastructure 8623614 2026-07-18 docs(d19-m2cr): R2 closure corrections — reviewed-head/tail distinction + Codex closure audit
- origin/docs/d46-m2cr-ballot-close 574bf2e 2026-07-16 docs(d19-m2c): R1 — M2cR taxonomy freeze: prereg addendum v1.19, execution-record schema + v2 per-node contract, canonical JSONL authorization ledger; D47; schema/docs only
- origin/docs/d45-m2c-v118-stop-record f302ce9 2026-07-14 docs(d19-m2c): D45 review-fixes — POST-STOP attribution, schema-STOP claim softened, verdict provenance, manifest wording
- origin/feat/d19-m2c-pr-d cfbc7c6 2026-07-14 docs(d19-m2c): PR D — fix D44 banner 'two Update sections'→singular (final audit nit); D44
- origin/feat/d19-m2c-pr-c b44cffd 2026-07-14 docs(d19-m2c): PR C — record Ready preflight + flip PR #12 to Ready; D43
- origin/feat/d19-m2c-pr-b 8d3564e 2026-07-13 docs(d19-m2c): PR B — precise provenance wording; mark PR #11 Ready
- origin/feat/d19-m2c-pr-a 0a317b2 2026-07-13 docs(d19-m2c): SCRATCHPAD — PR #10 flipped to Ready (S2 closed; not merged)
- origin/feat/d19-m2c 804f96f 2026-07-13 docs(d19-m2c): D40 — M2c numerical freeze ratified; prereg v1.17 appended; rev-5 package pinned
- origin/feat/d19-m2br de41965 2026-07-12 docs(d19-m2br): D38 — author decisions: close M2bR, open M2c, accept informative withdrawn, scope G-toy revision to M2c
- origin/feat/d19-m2b-e1 59a3cc7 2026-07-11 feat(d19-m2b): author ratifies decision-table rows 8 and 9 (D31; prereg v1.13) — all 9 items ratified; PR to Ready
- origin/feat/d19-m2a-infra 0d90699 2026-07-11 fix(d19-m2a): enforce A4 universe firewall in run_bms_star; prove diagnostics non-perturbation (D20 review round 3)
- origin/docs/d19-mauna-freeze a077c6e 2026-07-10 docs(d19): freeze Mauna plan + pre-registration v1.0 before results (M1)
- origin/feat/toy-elicited-n20-figures 7dcb9cb 2026-07-10 fix(figures): reserve Figure A caption space inside the figure
- origin/study/prior-sensitivity ec127a9 2026-07-09 study(prior): D18 prior-sensitivity study — D12 bimodality is prior-induced; toy_elicited recommended
- origin/fix/laplace-zmx d850d78 2026-07-08 fix(experiments): align Mauna debias HMC with D8 pattern
- origin/fix/bms-correctness 09fadda 2026-07-01 docs: adopt antagonistic_collab Notes/ decision-log workflow

## Open pull requests
- #42 OPEN fix/code-review-2026-09: fix(review-2026-09): fix passes 1/1b/1c — nine implementation fixes, four-channel review (D68) (updated 2026-09-09)
- #41 DRAFT paper/case-e-debias: paper(case-e): section 07 toy debias demonstration — D67 (updated 2026-08-13)
- #40 DRAFT paper/synthesis-sections: paper(synthesis): sections 1, 2, 8 from the case record — D66 [four-model review complete; author adjudications open] (updated 2026-08-12)
- #39 OPEN paper/case-a-vanbork: paper(case-a): van Bork external validation with the fork placeholder — D60/D61/D65 [four-model review complete; fork awaits author] (updated 2026-08-12)
- #38 OPEN paper/case-d-mopen: paper(case-d): M-open calibration via regret localization — D64 [four-model review complete; author adjudications open] (updated 2026-08-12)
- #37 OPEN paper/case-c-haaf: paper(case-c): Haaf nested slope constraint under BMS* and PSIS-LOO — D63 [four-model review complete; author adjudications open] (updated 2026-08-12)
- #36 OPEN paper/case-b-occam-dial: paper(case-b): occam dial + E6 nesting check — D62 [four-model review complete; author adjudications open] (updated 2026-08-12)
- #22 OPEN chore/chatlog-session-d54: docs(notes): CHATLOG — 2026-07-20 session (D54 cascade retirement merged; A7/D55 next) (updated 2026-07-20)

## Decision-log entries per branch (Notes/DECISIONS.md)
- main: D1..D58 
- fix/code-review-2026-09: D1..D58 D68 
- paper/case-a-vanbork: D1..D58 D60 D61 D65 
- paper/case-b-occam-dial: D1..D58 D62 
- paper/case-c-haaf: D1..D58 D63 
- paper/case-d-mopen: D1..D58 D64 
- paper/case-e-debias: D1..D58 D67 
- paper/synthesis-sections: D1..D58 D66 

## Manuscript sources
- paper/case-a-vanbork: docs/paper-sie-jmp/03-case-A-external-validation.md 
- paper/case-b-occam-dial: docs/paper-sie-jmp/04-case-B-occam-dial.md 
- paper/case-c-haaf: docs/paper-sie-jmp/05-case-C-nested-constraints.md 
- paper/case-d-mopen: docs/paper-sie-jmp/06-case-D-mopen-calibration.md 
- paper/case-e-debias: docs/paper-sie-jmp/07-debias-bridge.md 
- paper/synthesis-sections: docs/paper-sie-jmp/01-intro.md docs/paper-sie-jmp/02-machinery.md docs/paper-sie-jmp/08-discussion.md 
- tex build (untracked, main worktree): docs/paper-sie-jmp/tex/sections/{01-intro,02-machinery,03-case-A,04-case-B,05-case-C,06-case-D,07-debias,08-discussion,A-notation,B-provenance}.tex, generated by docs/paper-sie-jmp/build_tex.py from the md sections.

## Tracked runs/ at the fix head
- runs/code_review_2026_09
- runs/d19_a7_failed_11485635
- runs/d19_a7_timing
- runs/d19_a7_timing_original_incomplete_11517022
- runs/d19_a7_timing_recovery_record_11517022.md
- runs/d19_planning
- runs/mauna_loa_sub150_hmc_20260215_0702
- runs/poster_d58

## Test suite at the fix head (driver runs, 2026-09-08)
- python -m pytest tests/ -q -p no:cacheprovider in the fix worktree: 1346 passed, 5 skipped, 1 failed (tests/test_m2cr_environment_freeze.py::test_committed_dependency_lock_reproduces_at_head, pypdf added to the environment since the lock), 493 s. Skips: two FIX1_FIXTURE_DIR-gated pins, three environmental.
- Case E oracle (experiments/toy_debias_demo.py from paper/case-e-debias against the fix package): byte-identical to runs/toy_debias_demo/ (sha256 65c9ff5f / c1153549 / 7096cd6e).

## Prior review records (context, not evidence)
- runs/code_review_2026_09/ (committed on the fix branch): 2026-09-05 four-channel implementation review, collation, ledger revision 3, fix-pass reviews (Codex, Fable 5.1, Kimi K3, GLM 5.3), fix1_synthesis.md revisions 1-3 with the fix pass 2 list.
- runs/toy_debias_demo/reviews/ and the case branches' review records (see each branch).

==================== HANDOFF-cases.md (case protocol, section 0 constraints) ====================
# HANDOFF — remaining paper cases, one branch each

2026-08-11. Governs execution of the four case-study work packages for the JMP
special-issue manuscript (plan: `~/.claude/plans/should-we-split-these-
synchronous-wand.md`; skeletons in `docs/paper-sie-jmp/`). Implementation by
**Codex `gpt-5.6-sol`, reasoning `xhigh`** (the A7/D56b review-protocol model).
Reviews by four independent models with cross-verification (§4).

## 0. Global protocol (applies to every case)

**Branching.** One branch per case off `main`:
`paper/case-a-vanbork`, `paper/case-b-occam-dial`, `paper/case-c-haaf`,
`paper/case-d-mopen`. Work in this clone (local-only files such as
`Notes/WRITEUP_DECISIONS.md` are gitignored but present in the working tree —
Codex may READ them, must never `git add` them).

**Hard constraints (repeat verbatim in every Codex prompt):**
- M2bR banner: `informative`-config HMC is WITHDRAWN. Usable numbers:
  `toy_elicited` SIR (headline 0.441), prior-IS, MAP, SIR hard-best-match
  rates, corrected NUTS ≈ 0.42. Never cite the withdrawn cache
  (`runs/fit_method_metric_comparison/samples_hmc.npz`) or
  `runs/toy_tau_metric_comparison/` (poster-only per W7).
- W1: primary metric `pw_kl_vcal`; `kl_forward` appendix-only.
- W4: `runs/viz_unification/*` numbers are `informative`-config, MAP-based,
  methods-validation role — prose must frame them so.
- No Mauna Loa material of any kind (D58 prereg boundary not to be tested).
- No changes to `bistar_gp/` package defaults or public APIs.
- Style: no arrow glyphs in prose; no "X is the Y" role-noun constructions;
  no "lives/sits" for abstracta; minimal em-dashes (see repo CLAUDE.md +
  user's global rules quoted in `docs/paper-sie-jmp/00-notation.md`).
- Every reported number must be regenerable from a named `experiments/`
  script into a `runs/` artifact; each case commits a same-commit
  `Notes/DECISIONS.md` entry (next free D number).
- Commit scope per branch: `experiments/` script(s), `docs/paper-sie-jmp/`
  section, `Notes/DECISIONS.md` entry, and (deliberately, if evidence-worthy)
  the `runs/` JSON — never figures over 2 MB, never gitignored Notes files.

**Canonical implementation invocation** (pipe the case prompt via stdin):

```bash
git checkout main && git checkout -b paper/case-X-<slug>
cat docs/paper-sie-jmp/prompts/case-X-impl.txt | codex exec --yolo \
  --skip-git-repo-check -m gpt-5.6-sol \
  -c 'model_reasoning_effort="xhigh"' -o /tmp/case-X-impl.txt -
```

The driver session composes `case-X-impl.txt` from §2's work order + §0's
constraints, reads `/tmp/case-X-impl.txt`, verifies (§3), then runs §4.

## 1. Sequencing and blockers

| Case | Status | Blocker |
|---|---|---|
| B (occam dial) | UNBLOCKED | — |
| C (Haaf) | UNBLOCKED for build | "sharpest criticism" framing stays provisional until Kellen & Klauer 2020 PDF is read (WANTED.md) |
| D (M-open) | UNBLOCKED | verify what `experiments/practice_EvansEtAL/run.py` already outputs before writing new regret code |
| A (van Bork) | **BLOCKED on the D60/D61 fork** (author call: canonical aggregation convention) | draft everything except the fork paragraph; leave `[FORK-DECISION-PLACEHOLDER]` |

Recommended order: B and C in parallel, then D, then A.

## 2. Work orders

### Case B — `paper/case-b-occam-dial`
Scope: E4 figure + E6 check + section `04-case-B-occam-dial.md`.
1. `experiments/occam_dial_figure.py`: side-by-side model posteriors under
   occam=False vs occam=True from the MAP-based viz_unification artifacts
   (`runs/viz_unification/p3_priors_canonical/`, `p1_priors_lap_occam/`;
   D17 numbers 0.934 vs 0.693 at n=50), nesting relations annotated
   (Linear ⊂ Sin+Linear via A=0; Sinusoidal ⊂ Sin+Linear via b=c=0;
   Quadratic not nested). Output `runs/occam_dial/`.
2. `experiments/e6_nesting_monotonicity.py`: verify min_φ Ḡ(encompassing) ≤
   min_φ Ḡ(restricted) for both nested pairs across a τ-relevant grid, using
   the existing Ḡ/multi-start machinery in `bistar_gp/laplace_evidence.py`
   (do NOT reimplement). Output JSON + a one-paragraph resolution of the
   `kb/Wiki/REVIEW_AND_VET.md` "Nesting monotonicity" entry (edit that file:
   mark resolved with the numbers).
3. Flesh out `docs/paper-sie-jmp/04-case-B-occam-dial.md` from the stub +
   `kb/Wiki/Subset Problem and the Data Prior.md` (W4 framing discipline).
Acceptance: figure regenerates; E6 verdict stated either way (a violation is
a REPORTABLE finding, not a failure); DECISIONS entry present.

### Case C — `paper/case-c-haaf`
Scope: the one real build. `experiments/haaf_nested_constraint.py`:
1. Candidate pair differing ONLY by a parameter-region constraint within one
   functional form (mirror Haaf & Klaassen's ordinal-constraint setting):
   free Sin+Linear vs slope-constrained (b ≥ 0) Sin+Linear, both via
   `bistar_gp/candidates.py` `_fit_mle` with bounds.
2. Constraint-consistent synthetic data (true b > 0), N=20 convention,
   seeded.
3. BMS* scoring on the validated path: reuse
   `experiments/prior_sensitivity_study.py` stage-IS machinery exactly as
   `experiments/e7_convention_sensitivity.py` does (imports, not copies);
   report pooled AND expected-posterior variants (fork-agnostic table).
4. PSIS-LOO head-to-head on the identical data via `arviz` (add to
   requirements only if absent), for the same two candidates fitted as
   Bayesian models with weakly-informative priors — document those priors;
   they exist only on the LOO side of the comparison.
5. Section `05-case-C-nested-constraints.md` from the stub. Output
   `runs/haaf_nested_constraint/`.
Acceptance: the comparison table shows, on identical data, what LOO awards
the constrained candidate vs what BMS* awards it; whichever way it comes out
is reported (a null result is reportable); DECISIONS entry present.

### Case D — `paper/case-d-mopen`
Scope: regret curves + section; E8b optional module.
1. FIRST inventory `experiments/practice_EvansEtAL/` (`run.py`, diag scripts,
   `data/`): if regret-per-trial is already computed, reuse; else add
   `experiments/regret_curves_mopen.py` implementing
   regret_θ(t) = E_draws|μ_GP(t) − μ_θ(t)| per the formula in
   `kb/Wiki/Limits Diagnostics and Open Questions.md`, on that experiment's
   existing fitted artifacts (no new HMC).
2. Section `06-case-D-mopen-calibration.md`: the decline-is-correct argument
   (Navarro, Pitt & Myung 2004 digest in
   `kb/Digests/Clippings/data_prior_regimes/`), divergence magnitudes as the
   absolute inadequacy read, regret curves showing WHERE candidates fail.
3. OPTIONAL `experiments/e8b_transform_space.py` (semi-log + log-log refit,
   lognormal noise correction) — implement behind `[E8B-PLACEHOLDER]` blocks
   in the section so the author can excise cleanly.
Acceptance: regret figure regenerates from existing artifacts; section
drafted; DECISIONS entry present.

### Case A — `paper/case-a-vanbork`
Scope: writing-heavy; compute exists (`runs/vanbork_external_validation/`,
`runs/e7_convention_sensitivity/`, both with READMEs; D60, D61).
1. Flesh out `03-case-A-external-validation.md`: mapping table, Target B
   six-decimal reproduction + the Laplace special-case argument, Target A
   convention dependence, E7 movement numbers, the kl_forward attribution
   (D61 finding 2) — leaving `[FORK-DECISION-PLACEHOLDER]` where the
   canonical-convention statement goes.
2. Add the multi-parameter reach demo paragraph citing
   `runs/viz_unification/p3_priors_canonical/` under W4 framing.
Acceptance: every number in the section traces to the two run dirs;
placeholder intact; no new compute.

## 3. Driver-session verification (before any review)

Per branch: `python experiments/<new script>.py` reruns clean from the branch
tip; figures/JSON regenerate (numbers within pinned tolerances where the
script pins them); `git diff main --stat` contains only the §0 commit scope;
DECISIONS entry number does not collide (check `grep -c '^## D' Notes/DECISIONS.md`).

## 4. Review protocol — four models, independently, then cross-verify

For each branch, after §3 passes, obtain FOUR independent reviews. Each
reviewer receives the same package: `git diff main` for the branch, the case's
section file, the run README(s), and §0's constraints. Reviewers must NOT see
each other's outputs in round 1.

| Reviewer | Channel | Invocation sketch |
|---|---|---|
| GPT 5.6 sol (xhigh) | Codex CLI, fresh session, review-only prompt | same canonical command, prompt = review template below, `-o /tmp/caseX-rev-codex.txt` |
| Opus 5 | Claude in-session subagent (Agent tool, model=opus) or `claude -p --model opus` once CLI OAuth is restored | review template |
| Gemini | `gemini` MCP server (`gemini-analyze-code` / `gemini-analyze-text` on the diff) when connected | review template |
| Kimi K3 | author's Kimi channel (no CLI configured in this repo — **author supplies the command or runs it by hand**; template below is paste-ready) | review template |

Review template (all four):

```
Review the attached branch diff for the BI*/BMS*-GP paper case <X>.
Verdict: APPROVE or REVISE. Findings as a numbered list:
[severity S1-S4] [file:line] claim — why it is wrong — concrete fix.
Check specifically: (1) constraint compliance [paste §0 list]; (2) numerical
claims vs the runs/ JSONs; (3) statistical correctness of the method logic;
(4) prose style rules; (5) anything the section claims that the artifacts do
not support. Do not propose scope expansions.
```

**Cross-verification rules:**
1. Collate findings across the four reviews. A finding reported by ≥2
   reviewers is presumed real → fix queue.
2. A finding reported by exactly ONE reviewer is adversarially checked: send
   it to one OTHER reviewer (rotate; never the originator) with "attempt to
   refute this specific finding against the artifacts; default to refuted if
   the evidence is ambiguous." Survivors → fix queue; refuted → logged as
   rejected with the refutation.
3. Verdict conflicts (some APPROVE, some REVISE) are decided by the fix
   queue, not by vote: empty queue → APPROVE stands; non-empty → REVISE.
4. Fixes implemented by Codex (same canonical invocation, prompt = fix queue
   + diff); then ONE re-review round of the changed hunks only, by the two
   reviewers who raised the surviving findings. No third round — residuals
   escalate to the author.
5. Author adjudicates anything the protocol cannot settle, and always
   adjudicates S1/S2 findings touching statistical claims.

**Record-keeping per branch:** review outputs under
`runs/<case run dir>/reviews/` (raw reviewer outputs + a `VERDICTS.md`
summarizing findings, refutations, fixes, final verdict). The branch's
DECISIONS entry gets a one-line review-outcome addendum before merge is
proposed. Merges are proposed to the author; nothing merges autonomously.

## 5. Out of scope for all branches

The D60 fork decision (author). Kellen & Klauer PDF acquisition. Overleaf
conversion. Any Mauna computation. Poster files. `bistar_gp/` API changes.

==================== REVIEW STANDARD: HANDOFF-code-review.md sections 2-3 ====================
## 2. The standard: what "implemented correctly" means here

A finding is anything where one of these fails.

1. **Claim fidelity.** A quantity the paper names is computed by code that
   computes something else. The known instance of this class, already
   confirmed and still open on #40's ledger, is the Ḡ plug-in surrogate
   (§3, T1); find the rest.
2. **Commitment enforcement.** A decision recorded in `Notes/DECISIONS.md` or
   the writeup banners is not actually enforced by the code that is supposed
   to enforce it, so a caller can silently violate it. The precedent is the A4
   universe firewall, which accepted mixed candidate universes and silently
   normalized across them until it was guarded.
3. **Silent-wrong-answer paths.** A failure that produces a plausible number
   instead of an error. Discarded return values, swallowed exceptions,
   fallbacks that substitute a different estimator, and jitter escalation that
   is not counted all belong here.
4. **Estimator honesty.** An uncertainty summary that understates or
   misdescribes what it measures, or a diagnostic reported next to a quantity
   it is not comparable with.
5. **Reproducibility.** A committed artifact that the named script does not
   regenerate, or regenerates differently, within its stated tolerance.
6. **Test adequacy.** A claim the manuscript rests on that no test would catch
   if it broke.

### Severity

- **S1** — a number, figure, or artifact the manuscript or the D58 poster
  presents is wrong, or is right only by accident.
- **S2** — substantive: the computation diverges from the claim, a commitment
  is unenforced, or an uncertainty is materially misstated, but no published
  number is yet known to be wrong.
- **S3** — scope, robustness, or an unexercised silent-failure path.
- **S4** — hygiene, naming, or documentation that could mislead a future
  maintainer.

Every finding needs a **concrete failure scenario**: inputs or a call sequence
that produce the wrong outcome. A finding with no failure scenario is a
question, and belongs in the questions section instead.

---

## 3. Named targets

These come from the driver's scan of 2026-09-05. They are **starting points, not
conclusions**. Confirm or refute each on the evidence, and say which. Finding
that a named target is a non-issue is a useful result; report it under "what I
verified clean" with the reasoning. Do not stop at this list.

**T1 — the Ḡ plug-in surrogate.** `bistar_gp/laplace_evidence.py:135` passes
`avg_gp.mean, avg_gp.cov` to the metric, so G is evaluated once against a
moment-matched averaged pattern rather than averaged over per-draw
divergences. `docs/paper-sie-jmp/00-notation.md` glosses Ḡ as averaged across
data patterns. The synthesis review confirmed the gap and the section now
calls the quantity a plug-in surrogate; the notation amendment remains open on
#40's ledger. Question for the reviewer: which committed numbers depend on the
difference, and is the surrogate's error bounded or characterized anywhere?
Driver observation to follow up: the averaged-pattern construction at
`bistar_gp/aggregation_v3.py:77` (`mu_bar = w @ means`) emits divide-by-zero,
overflow, and invalid-value RuntimeWarnings during
`tests/test_zmx_estimators.py::test_prior_stage_flows_to_finite_is_log_Z`.
The weight validator just above rejects non-finite weights, so the
non-finite values arrive in `means`. Establish whether that is confined to
deliberate prior-stage stress inputs or can reach a reported number.

**T2 — the decomposition routines discard per-draw conditional covariance.**
*Driver correction, 2026-09-06 (raised by the Codex channel): the two affected
routines are `decompose_model_mcmc` (`bistar_gp/debias.py:131`) and
`decompose_model_hmc` (`:206`). The MAP wrapper `decompose_model` is NOT
affected; it computes the full posterior covariance from summed kernel blocks
at `:70-84` and explicitly retains inter-component cross-covariance. The
original wording of this target named the wrong function.*
`decompose_model_mcmc` and `decompose_model_hmc` iterate
`for (mean_i, _), comp_name in zip(...)` (`bistar_gp/debias.py:131` and
`:206`), dropping each draw's covariance, and both report
`cov=np.diag(std**2)` (`:144`, `:225`) where `std` is the across-draw spread
of means alone. Case E deliberately avoided this routine for that reason.
Live callers of the HMC variant:
`experiments/toy_example.py:87`, `experiments/mauna_loa.py:74`,
`experiments/bistar_debias_mauna_loa.py:410`,
`experiments/poster_d58_mauna.py:459`. A local workaround exists at
`experiments/honest_band_decomposition.py`, and
`experiments/toy_n20_poster_figures.py:80` carries a comment about it.
Question: does any **paper-facing or D58-poster-facing** band understate
uncertainty as a result, and if so by how much? Treat this as potentially S1.

**T3 — aggregation dial enforcement.** D60 fixed pooled aggregation as
canonical with `normalize_per_draw=False` shipped unchanged
(`bistar_gp/bms_star.py:412`, `:513`). The global-shift stabilization at
`:449-455` carries a comment arguing a per-row max would silently behave like
`normalize_per_draw` even when the flag is False. Verify that argument is
correct and that the shift actually cancels in the normalization.

**T4 — MLL weight concentration.** BMS\* averages Boltzmann weights across GP
draws. `bistar_gp/induced_prior.py` computes an effective sample size for its
own importance sampling, but the driver found no Pareto-k or ESS diagnostic on
the weights that drive model scores. Question: can a small number of draws
dominate a reported model probability without any diagnostic firing, and does
that occur in any committed artifact?

**T5 — the evaluation grid.** `bistar_gp/config.py:172` sets `n_eval: int =
60` as a default, and every pointwise divergence averages over exactly those
locations. Question: is any reported conclusion sensitive to the grid's size
or placement, and is the choice documented anywhere as a choice?

**T6 — metric scoping (W1).** `pw_kl_vcal` is the primary metric and
`kl_forward` is appendix-only. Question: is that enforced in code, or is it
convention that a caller can silently violate?

**T7 — the M2bR banner.** The `informative`-config HMC results are WITHDRAWN;
`runs/fit_method_metric_comparison/samples_hmc.npz` and
`runs/toy_tau_metric_comparison/` must never be cited. Question: does any code
path read, regenerate, or surface those artifacts in a way that could reach a
paper-facing number?

**T8 — universe firewall completeness.**
`_assert_candidate_universes_consistent` (`bistar_gp/bms_star.py:480`) closed
the A4 gap, and `run_bms_star` calls it at `:529`. But `soft_transfer`
(`:409`) and `compute_G_matrix` (`:368`) are public and perform the
aggregation without passing through that guard. Question: can a caller reach a
normalized cross-universe probability through the primitives, and does
anything in `experiments/` do so? Also check whether an untagged or
partially-tagged roster still passes the guard itself.

**T9 — Case E's new script.** `experiments/toy_debias_demo.py` (committed at
`8f1326d`, hardened at `a5b9cf8`) has never been seen by Codex. It carries an
AST-based guard asserting the library's sampler constants, a raise on
unmatched hyperparameter sites, and a jitter probe. Audit all three, plus the
mixture-interval construction and the law-of-total-variance inversion added in
the fix pass.

**T10 — test adequacy.** 67 test files. Question: for each of the
manuscript's load-bearing claims, would any test fail if the claim stopped
holding? Name the claims that no test protects.

**T11 — sentinel returns and swallowed exceptions in the evidence path.**
`bistar_gp/laplace_evidence.py:126-127` catches bare `Exception` and returns
`1e6`; `:136-137` catches `LinAlgError`/`ValueError` and returns `1e6`. Under
`exp(-G/tau)` a score of 1e6 becomes indistinguishable from zero weight, so a
parameter region that fails numerically is scored as an extremely poor fit
rather than reported as a failure. `_log_likelihood` returns `-1e10` on any
exception (`:253`), and both Laplace optimizers fall back to the starting
point when `minimize` raises (`:268` sets `converged=False`; `:486` records no
flag at all). Questions: how often does each path fire in the committed runs,
does anything downstream inspect `converged`, and can a Z_M or a model
probability in the manuscript depend on a silently substituted sentinel?

---


==================== MANUSCRIPT (LaTeX build of the branch md sections) ====================

---------- 01-intro.tex ----------
%% Generated from docs/paper-sie-jmp/01-intro.md
%% Source branch: paper/synthesis-sections
%% Do not hand-edit; see docs/paper-sie-jmp/build_tex.py
\section{Introduction}

\subsection{Data priors and the model-evaluation problem}

This contribution enters the third \emph{Journal of Mathematical Psychology}
special issue devoted to statistical model evaluation, following the
collections associated with Myung, Forster, and Browne and with Wagenmakers and
Waldorp.\footnote{\evidencetier{peer-reviewed} Myung, Forster, and Browne (2000) and Wagenmakers and Waldorp (2006), earlier \emph{Journal of Mathematical Psychology} special-issue contributions on model selection and evaluation.} Across those collections, the recurring problem has
not been a shortage of scoring rules. The harder question concerns what a score
should evaluate when scientific models overlap, approximate rather than contain
the data-generating process, or earn good fit through flexibility. The present
paper answers by taking possible data patterns, rather than separately chosen
parameter priors, as the common reference for evaluation.

That choice continues the data-prior program introduced in the JMP contributions
by Chandramouli and Shiffrin and by Shiffrin, Chandramouli, and Grünwald.\footnote{\evidencetier{peer-reviewed} Chandramouli and Shiffrin (2016), ``Extending Bayesian induction,'' \emph{Journal of Mathematical Psychology}, 72, 38--42; Shiffrin, Chandramouli, and Grünwald (2016), ``Bayes factors, relations to minimum description length, and overlapping model classes,'' \emph{Journal of Mathematical Psychology}, 72, 56--77.}
Their BI* table assigns prior probability to data patterns \(\psi\), updates
those patterns after observing data, and derives model evaluation from their
relation to candidate predictions. A data prior therefore provides the
through-line from the original finite table to the present Gaussian-process
implementation. GP hyperpriors construct \(p_0(\psi)\) over a continuous family
of plausible patterns; projection transfers that belief to candidate instances;
and integration or soft transfer produces model-level quantities without a
hand-specified parameter prior for every candidate.

This reallocation of judgment does not remove prior choice. It asks the analyst
to state beliefs about observable regularity, variation, trend, and noise in a
shared scaffold. Those choices can be inspected through prior predictive
patterns and applied consistently to every candidate. The resulting comparison
addresses how well each candidate approximates a common posterior over data
patterns, rather than how well separately equipped Bayesian models predict
under different within-model priors.

\subsection{Fit propensity over a weighted data space}

Bonifay and Cai's fit-propensity program supplies a particularly close point of
contact. Fit propensity evaluates how readily a model attains good fit over
possible data, so observed fit cannot be interpreted apart from the range of
patterns a model can accommodate.\footnote{\evidencetier{peer-reviewed} Bonifay and Cai (2017), ``On the complexity of item response theory models,'' \emph{Multivariate Behavioral Research}, 52(4), 465--484.} The present construction shares
that data-space orientation but replaces an undifferentiated set of possible
data with \(p_0(\psi)\), a scientifically weighted distribution. It also makes
the evaluative consequences explicit: \(G\) defines relevant predictive
similarity, \(\tau\) controls the softness of credit, \texttt{occam} selects the
reference measure for \(Z_M\), and aggregation determines whether absolute
inadequacy remains visible. Fit propensity and data priors thus ask compatible
questions about model behavior before a single observed-data fit receives an
evidential interpretation.

\subsection{Contributions and case-study plan}

The paper makes four contributions.

\begin{enumerate}
\def\labelenumi{(\roman{enumi})}
\item
  It constructs a stand-alone data prior \(p_0(\psi)\) from GP kernel
  hyperpriors, replacing enumeration of the BI* table with a continuous and
  inspectable distribution over data patterns.
\item
  It induces parameter and model priors by projecting those patterns onto
  candidate predictions and integrating compatibility, without requiring a
  separate hand-specified parameter prior for every model.
\item
  It subjects the machinery to four cases. The first provides external
  validation of the induced-prior and soft-transfer computations against data
  priors supplied by other authors, which leaves the GP scaffold itself untested;
  the remaining three cover nested-model reference measures, a satisfied parameter
  constraint against PSIS-LOO, and calibration under known synthetic
  truth.\footnote{\evidencetier{empirical} assembled-manuscript sections 3--6, read from the case branches at \texttt{docs/paper-sie-jmp/03-case-A-external-validation.md}, \texttt{docs/paper-sie-jmp/04-case-B-occam-dial.md}, \texttt{docs/paper-sie-jmp/05-case-C-nested-constraints.md}, and \texttt{docs/paper-sie-jmp/06-case-D-mopen-calibration.md}; supporting artifacts and decisions are listed in the provenance footer below.}
\item
  It makes the evaluative choices explicit as dials rather than burying them
  in an implementation. Case B, section 4, jointly prices \(\tau\) and \texttt{occam};
  Case A, section 3, prices aggregation against external correspondence and the
  retention of absolute divergence; Case C, section 5, shows what follows when the
  table path has no volume term; and Case D, section 6, establishes why a shared
  numerical \(\tau\) cannot support probability comparisons across differently
  scaled metrics.
\end{enumerate}

The cases produce deliberately mixed outcomes. Case A reproduces independent
closed-form targets and validates a hybrid \(Z_M\) special case, though its
examples insert the published data priors directly and therefore exercise the
induced-prior and soft-transfer machinery without testing the GP scaffold. It
also exposes the aggregation trade, because the canonical pooled convention does
not reproduce the non-overlapping target that the per-draw routes recover. Case
B uses an \texttt{informative}-configuration, MAP-based methods-validation example to
show that reference-volume normalization can change a nested-model comparison at
finite temperature. Case C returns the important null: the table path gives an
effective tie with a direction fixed by containment, while PSIS-LOO remains
directionally inconclusive for the satisfied constraint. Case D remains
synthetic-only; it contributes known-truth reference material and a
metric-scale warning without claiming a real-data result or
setting an inadequacy threshold.\footnote{\evidencetier{empirical} assembled-manuscript sections 3--6, read from the case branches at \texttt{docs/paper-sie-jmp/03-case-A-external-validation.md}, \texttt{docs/paper-sie-jmp/04-case-B-occam-dial.md}, \texttt{docs/paper-sie-jmp/05-case-C-nested-constraints.md}, and \texttt{docs/paper-sie-jmp/06-case-D-mopen-calibration.md}; supporting artifacts and decisions are listed in the provenance footer below.}

---------- 02-machinery.tex ----------
%% Generated from docs/paper-sie-jmp/02-machinery.md
%% Source branch: paper/synthesis-sections
%% Do not hand-edit; see docs/paper-sie-jmp/build_tex.py
\section{Machinery}

\subsection{From the BI* table to a GP data prior}

The BI* table begins with possible data patterns \(\psi\) as rows and possible
observations as columns. A row carries prior weight \(p_0(\psi)\); observing a
column updates the row weights by Bayes' rule. Candidate models enter only after
that data-space update, through the predictive patterns they can reproduce.
Figure 1 of the foundational JMP account gives the finite construction.\footnote{\evidencetier{peer-reviewed} Chandramouli and Shiffrin (2016), ``Extending Bayesian induction,'' \emph{Journal of Mathematical Psychology}, 72, 38--42; Shiffrin, Chandramouli, and Grünwald (2016), ``Bayes factors, relations to minimum description length, and overlapping model classes,'' \emph{Journal of Mathematical Psychology}, 72, 56--77.}

A Gaussian process replaces enumeration with a generative data prior. Draw the
kernel hyperparameters, draw a function conditional on them, and combine that
function with observation variance to obtain one \(\psi\). Repetition induces
\(p_0(\psi)\). The squared-exponential plus linear construction uses four
positive hyperparameters with direct qualitative interpretations: \(\ell\)
controls the scale over which nonlinear variation remains smooth,
\(\sigma^2_{SE}\) controls the amplitude of that smooth variation,
\(\sigma^2_b\) controls the strength of linear trend, and \(\sigma^2_y\)
controls observation-scale variation. Gamma hyperpriors in the prior-only
mechanism illustration make those beliefs inspectable before data enter.\footnote{\evidencetier{empirical} \texttt{bistar\_gp/config.py}; the prior-only arm of \texttt{experiments/mechanism\_figure\_poster.py}, local methods material that remains uncommitted in this repository, serves construction visualization and supplies no reported number or posterior estimate.}

The mechanism illustration has an \texttt{informative}-configuration,
prior-predictive methods-validation role. It explains the construction rather
than supplying a paper-facing posterior estimate. Each case states its own GP
configuration and inferential path; no \texttt{informative}-configuration HMC result
enters the account here.

\subsection{\texorpdfstring{Projection, induced priors, and \(Z_M\)}{Projection, induced priors, and Z\_M}}

For a candidate family, projection fits the candidate instance that minimizes
\(G(\psi,\theta)\) for each sampled pattern. Under \texttt{pw\_kl\_vcal}, the candidate
variance is calibrated to the GP pattern, so the parameter-dependent part of
the divergence reduces to variance-weighted squared error. When a drawn pattern
carries one scalar noise variance shared across the evaluation locations, that
weight factors out of the minimization, and the variance-calibrated argmin
coincides with the Gaussian maximum-likelihood refit. The correspondence holds
algebraically rather than as a sampled regularity. Where the pattern variance
varies across locations, the weights no longer factor out and the two
projections need no longer coincide. The collection of fitted instances should
be read as samples from the pushforward of \(p_0(\psi)\) through this
projection, not as draws from a separately elicited within-model parameter
prior.\footnote{\evidencetier{empirical} the \texttt{pw\_kl\_vcal} definition in \texttt{bistar\_gp/metrics\_v2.py}, from which the shared-scalar-variance coincidence of the two projections follows algebraically; conceptual account in \texttt{kb/Wiki/GP-Induced\ Model\ Priors.md}.}

Model-level induction averages before integrating. For candidate parameters
\(\phi\), \(\bar G(\phi)\) averages \(G\) across data patterns, and

\[
Z_M = \int \exp\{-\bar G(\phi)/\tau\}\,d\phi.
\]

The implementation reaches that average by moment matching rather than by
averaging per-draw divergences. It first collapses the sampled patterns into a
single averaged pattern \(\bar\psi\), whose mean equals the weighted mean of the
per-draw means and whose covariance adds a between-draw mean-spread term to the
weighted average of the per-draw covariances, and then evaluates \(G\) once
against \(\bar\psi\). The computed object therefore reports the divergence from
\(\bar\psi\) rather than the mean of the per-draw divergences, and the
discrepancy between them varies with \(\phi\), so it does not cancel from a
normalized comparison across candidates. Take the notation's ``averaged across
data patterns'' gloss as the intended reading of \(\bar G(\phi)\) and the
moment-matched evaluation as the plug-in surrogate for it used throughout. The
surrogate is not consistent for the per-draw average, because the gap between
them reflects the construction rather than sampling error that accumulating
draws would remove.\footnote{\evidencetier{empirical} \texttt{bistar\_gp/aggregation\_v3.py}, whose \texttt{average\_gp\_posterior} forms the weighted mean and the covariance carrying the between-draw mean-spread term, and \texttt{bistar\_gp/laplace\_evidence.py}, whose \texttt{compute\_G\_at\_params} evaluates the divergence against that averaged pattern.}

With \texttt{occam=False}, the integral uses raw Lebesgue measure, which follows the
canonical BI* convention. With \texttt{occam=True}, division by \(V_{\mathrm{ref}}\)
changes the reference measure from total compatible volume to average
compatible density. The flag therefore encodes a substantive position on how
parameter-region volume should affect a model prior; it does not merely select
a numerical correction. Case B, section 4, demonstrates that consequence under
the required \texttt{informative}-configuration, MAP-based methods-validation
framing.\footnote{\evidencetier{empirical} assembled-manuscript section 4 on \texttt{paper/case-b-occam-dial}; \texttt{experiments/occam\_dial\_figure.py}; \texttt{experiments/e6\_nesting\_monotonicity.py}; \texttt{runs/occam\_dial/}; Notes/DECISIONS.md D17 and D62.}

\subsection{Soft transfer, temperature, and aggregation}

Soft transfer retains per-pattern variation rather than averaging first. Under
pooled aggregation,

\[
p(\theta\mid y) \propto
\sum_i \exp\{-G(\psi_i,\theta)/\tau\}.
\]

Small \(\tau\) concentrates credit on the best matches, and larger \(\tau\)
spreads it across candidates. The low-temperature limit itself depends on the
aggregation convention set out below rather than on temperature alone. As
\(\tau\) approaches zero under pooled aggregation, the sum concentrates on the
globally smallest divergences across all draws, so draws whose best available
match remains poor contribute negligible support. The per-draw conventions
defined below, row-min and expected-posterior, instead resolve each draw
separately, and where a draw has a unique closest candidate they recover hard
best-match assignment within that draw, so their low-temperature limit reflects
the rate at which candidates attain their draw's smallest divergence.
Temperature must therefore be swept and reported together with the convention,
not fixed silently.

Aggregation supplies a third dial. Pooled aggregation preserves the absolute
support contributed by each pattern and normalizes only after summing. The
row-min convention subtracts each pattern's smallest divergence before the
same pooled normalization. Expected-posterior aggregation first normalizes
candidate support within each pattern and then averages, matching Eq. 4 of van
Bork, Romeijn, and Wagenmakers. Per-pattern normalization spends equal total
credit on a pattern even when every candidate fits poorly, whereas pooled
aggregation retains that absolute inadequacy information.

The D60 Resolution adopts aggregation as an explicit evaluation dial.
Canonical reporting uses pooled aggregation to preserve absolute divergence
magnitudes, the M-open signal, and continuity with the validated results.
Expected-posterior aggregation accompanies it wherever external correspondence
with Eq. 4 matters. Canonical pooled reporting carries an explicit price: pooled
aggregation does not reproduce Case A's Target A, which the per-draw routes
recover, and the dial records that failure rather than absorbing it into a
silent default. Neither convention receives a universal-correctness claim;
Case A, section 3, reports the cost of each choice.\footnote{\evidencetier{empirical} \texttt{experiments/vanbork\_external\_validation.py}; \texttt{runs/vanbork\_external\_validation/}; \texttt{experiments/e7\_convention\_sensitivity.py}; \texttt{runs/e7\_convention\_sensitivity/}; Notes/DECISIONS.md D60 Resolution and Precision addenda, and D61.}

\textbf{Remark 1 (one-sidedness under nested candidate regions).} Score a candidate
family \(M\) on draw \(\psi_i\) by its best available match,

\[
G_i(M)=\min_{\theta\in M}G(\psi_i,\theta)
=\min_{q\in\mathcal{P}(M)}G(\psi_i,q),
\]

where \(\mathcal{P}(M)\) collects the predictive distributions the family can
reach as \(\theta\) ranges over its parameters. Stating the score through the
reachable set, rather than through containment of parameter vectors, admits an
embedded restriction that carries fewer parameters than its encompassing
family: nesting requires only \(\mathcal{P}(M_r)\subseteq\mathcal{P}(M_e)\), and
the two parameter spaces may then have unequal dimension. Whenever that
containment holds, minimizing over the larger set cannot return a larger value,
so for every draw

\[
G_i(M_e)\leq G_i(M_r).
\]

The inequality follows from reachable-set containment, not from a sampled
regularity. Under any of the three conventions above, each of which is monotone
in the per-draw scores, table-path aggregation preserves that ordering and can
never favor the restriction at any \(\tau\); only the gap magnitude is
empirical. Consequently, crediting a satisfied restriction belongs to the
\(Z_M\) side, where the volume or reference-measure term controlled by \texttt{occam}
can reward the restricted region, not to the table path. Cases B and C, sections
4 and 5, provide the complementary worked instances.\footnote{\evidencetier{empirical} assembled-manuscript sections 4 and 5 on the Case B and Case C branches; \texttt{runs/occam\_dial/e6\_results.json}; \texttt{runs/haaf\_nested\_constraint/results.json}; Notes/DECISIONS.md D62 and D63.}

\subsection{Metric roles and scale discipline}

Joint divergences compare the full GP predictive covariance with the
candidate's joint predictive covariance. That comparison can make structural
covariance mismatch dominate the mean-pattern question of interest. Pointwise
metrics instead compare marginal predictions at each evaluation location.
Following W1, \texttt{pw\_kl\_vcal} provides the primary metric: variance calibration
reduces it to GP-uncertainty-weighted squared error. The full joint
\texttt{kl\_forward} remains an appendix-only stress metric.\footnote{\evidencetier{peer-reviewed} Gneiting and Raftery (2007), ``Strictly proper scoring rules, prediction, and estimation,'' \emph{JASA}, 102(477), 359--378; Varin, Reid, and Firth (2011), ``An overview of composite likelihood methods,'' \emph{Statistica Sinica}, 21, 5--42. W1 fixes the manuscript roles of \texttt{pw\_kl\_vcal} and \texttt{kl\_forward}.}

D61 sharpens the appendix attribution. The observed \texttt{kl\_forward} fragility
arises largely from pooled aggregation's sensitivity to outlying predictive
draws rather than from the metric alone. Appendix reporting should therefore
pair its pooled soft-transfer result with the aggregation convention and a
draw-level diagnostic, rather than treating a collapsed pooled weight as an
unqualified metric verdict.\footnote{\evidencetier{empirical} \texttt{experiments/e7\_convention\_sensitivity.py}; \texttt{runs/e7\_convention\_sensitivity/results.json} and \texttt{README.md}; Notes/DECISIONS.md D61.}

\textbf{SCALE-INVARIANCE WARNING.} Soft-transfer probability magnitudes cannot be
compared across metrics at a shared numerical \(\tau\). Even under a common
positive affine rescaling of \(G\), the multiplicative scale changes the
effective temperature and can make the normalized probabilities arbitrarily
sharp or diffuse without changing the underlying within-draw ordering. Case D,
section 6, exhibits an exact candidate-specific affine identity between two
stored metrics and shows why a common temperature does not repair their scale
difference.\footnote{\evidencetier{empirical} assembled-manuscript section 6 on \texttt{paper/case-d-mopen}; \texttt{experiments/regret\_curves\_mopen.py}; \texttt{runs/regret\_curves\_mopen/results.json}; Notes/DECISIONS.md D64.}

Reporting must therefore compare probabilities within a metric, over a stated
\(\tau\) sweep. Every soft-transfer table should also report tau-free draw-win
fractions: the fraction of data-pattern draws on which each candidate attains
the smallest \(G\). That statistic remains invariant under a common positive
affine rescaling and separates ordering from temperature-dependent sharpness.
Case D supplies the worked instance.\footnote{\evidencetier{empirical} assembled-manuscript section 6 on \texttt{paper/case-d-mopen}; \texttt{experiments/regret\_curves\_mopen.py}; \texttt{runs/regret\_curves\_mopen/results.json}; Notes/DECISIONS.md D64.}

---------- 03-case-A.tex ----------
%% Generated from docs/paper-sie-jmp/03-case-A-external-validation.md
%% Source branch: paper/case-a-vanbork
%% Do not hand-edit; see docs/paper-sie-jmp/build_tex.py
\section{Case A: external validation against van Bork, Romeijn, and Wagenmakers}

van Bork, Romeijn, and Wagenmakers derive model probabilities from expected
predictive support under an independently specified data prior. Their proposal
cites the BI\emph{/BMS} line as related prior work, but their closed-form examples
were developed without reference to the present implementation. They therefore
provide external checks on the induced-prior and soft-transfer machinery.
Because their examples supply the data prior directly, these checks bypass its
GP construction.\footnote{\evidencetier{peer-reviewed} van Bork, R., Romeijn, J.-W., \& Wagenmakers, E.-J. (2025). Simplicity in Bayesian nested-model comparisons: Popper's disagreement with Wrinch and Jeffreys revisited. \emph{Synthese}. https://doi.org/10.1007/s11229-025-05286-y.} The section reproduces both of their closed-form targets,
locates their construction inside the induced-prior machinery, and returns one
counterclaim about what their aggregation semantics costs.

\subsection{Correspondence of the constructions}

The correspondence below remains deliberately qualified. Both approaches
evaluate models against a distribution over possible data, but they need not
assign the same semantics to every intermediate quantity.

\begin{longtable}[]{@{}
  >{\raggedright\arraybackslash}p{(\linewidth - 4\tabcolsep) * \real{0.3333}}
  >{\raggedright\arraybackslash}p{(\linewidth - 4\tabcolsep) * \real{0.3333}}
  >{\raggedright\arraybackslash}p{(\linewidth - 4\tabcolsep) * \real{0.3333}}@{}}
\toprule\noalign{}
\begin{minipage}[b]{\linewidth}\raggedright
van Bork et al.
\end{minipage} & \begin{minipage}[b]{\linewidth}\raggedright
Present notation and computation
\end{minipage} & \begin{minipage}[b]{\linewidth}\raggedright
Qualification
\end{minipage} \\
\midrule\noalign{}
\endhead
\bottomrule\noalign{}
\endlastfoot
Data prior, a probability over outputs specified independently of the candidate models & \(p_0(\psi)\), a distribution over data patterns & In the general framework, GP hyperpriors induce \(p_0(\psi)\). The validation examples instead insert the authors' supplied data prior, so they do not test the GP scaffold. \\
Expected support against the data prior, expressed through Rosenkrantz-style verisimilitude & A divergence-based score \(G(\psi,\theta)\), followed by \(\bar G(\phi)\) when averaged over data patterns & Their support increases with predictive agreement; our divergence decreases with it. Additive and scale conventions therefore prevent a literal identification. \\
Prior model probability from expected posterior probability under their Eq. 4 & Normalize model support within each draw \(\psi\), then average under \(p_0(\psi)\) & This order matches expected-posterior aggregation. It does not match pooled aggregation, which sums unnormalized support across draws before model normalization. Their Eq. 4 treats each per-atom quantity as a Bayesian posterior model probability under an infinite-data idealization, whereas ours applies a Boltzmann softmax as \(\tau\) approaches zero. Target A agreement follows because both collapse to the same hard nearest-model assignment. \\
Completely overlapping models with distinct within-model parameter priors & Hybrid \(Z_M=\int p_M(\phi)\exp\{-\bar G_M(\phi)/\tau\}\,d\phi\) & The within-model density \(p_M(\phi)\) replaces the usual Lebesgue or \(V_{\mathrm{ref}}\)-normalized reference measure, so the check concerns an extension of the standard \(Z_M\). \\
A restricted model nested in an encompassing model & \(M_r\subset M_e\) & We adopt their nesting notation. Normalized predictive weights over a candidate roster do not thereby become set-additive probabilities over hypotheses. \\
\end{longtable}

\subsection{Target B: completely overlapping models}

Their coin example compares \(M_x\), with
\(\theta\sim\operatorname{Beta}(50,50)\), against \(M_z\), with
\(\theta\sim\operatorname{Beta}(2,2)\), under a data prior that places a point
mass at \(\psi^*=1/2\). The hybrid computation approaches the published
probability for \(M_x\) monotonically over the reported low-temperature rows:

\begin{longtable}[]{@{}rr@{}}
\toprule\noalign{}
\(\tau\) & Computed \(p(M_x)\) \\
\midrule\noalign{}
\endhead
\bottomrule\noalign{}
\endlastfoot
\(10^{-2}\) & 0.792607 \\
\(10^{-4}\) & 0.840781 \\
\(10^{-6}\) & 0.841413 \\
\(10^{-7}\) & 0.841419 \\
Their closed form, evaluated at double precision & 0.841420 \\
\end{longtable}

The paper prints the prior densities as 7.96 and 1.50 and the model weight as
approximately 0.84; the quotient formed from those printed densities equals
0.841438. Thus, the six-decimal comparison uses their closed form evaluated at
double precision rather than a printed six-decimal value. At the smallest
reported temperature, the absolute error against that evaluated limit equals
\(6.4\times10^{-7}\). The computed prior densities at the maximum-likelihood
point, 7.9589 for \(M_x\) and 1.5000 for \(M_z\), also reproduce the quoted
7.96 and 1.50 values.\footnote{\evidencetier{empirical} \texttt{experiments/vanbork\_external\_validation.py}; \texttt{runs/vanbork\_external\_validation/results.json} and \texttt{README.md}; Notes/DECISIONS.md D60; Notes/DECISIONS.md D60 Resolution (2026-08-12).
  Figure: \texttt{experiments/vanbork\_figure.py} re-plots the committed artifact values without recomputation.}

The agreement follows from a Laplace special case. With a point data prior,
\(\bar G(\phi)=G(\psi^*,\phi)\). Around the candidate optimum
\(\theta^*=1/2\), which coincides with the data-prior atom,

\[
Z_M \approx p_M(\theta^*)
\sqrt{\frac{2\pi\tau}{\bar G_M''(\theta^*)}}.
\]

Both models use the same Bernoulli family, so they share the local curvature:
\(\bar G_x''(\theta^*)=\bar G_z''(\theta^*)\). That factor and the remaining
common terms cancel after normalization across models. As \(\tau\) approaches
zero, the normalized hybrid scores consequently converge to the ratio of the
within-model prior densities at \(\theta^*\). The authors' published formula
thus coincides with the shared-family, point-data-prior, zero-temperature limit
of the hybrid \(Z_M\). Target B supplies the first passing test of this
within-model-prior extension, which had previously remained an open
implementation question.\footnote{\evidencetier{empirical} \texttt{experiments/vanbork\_external\_validation.py}; \texttt{runs/vanbork\_external\_validation/results.json} and \texttt{README.md}; Notes/DECISIONS.md D60; Notes/DECISIONS.md D60 Resolution (2026-08-12).
  Figure: \texttt{experiments/vanbork\_figure.py} re-plots the committed artifact values without recomputation.}

\subsection{Target A: aggregation changes the limiting answer}

The non-overlapping example assigns data-prior mass 0.4 at a Bernoulli
proportion of 0.16 and mass 0.6 at 0.19, then compares point models at 0.15 and
0.20. van Bork et al.'s answer assigns model probabilities 0.4 and 0.6. The
three implemented aggregation routes behave differently:

\begin{longtable}[]{@{}
  >{\raggedright\arraybackslash}p{(\linewidth - 4\tabcolsep) * \real{0.3000}}
  >{\raggedleft\arraybackslash}p{(\linewidth - 4\tabcolsep) * \real{0.4000}}
  >{\raggedright\arraybackslash}p{(\linewidth - 4\tabcolsep) * \real{0.3000}}@{}}
\toprule\noalign{}
\begin{minipage}[b]{\linewidth}\raggedright
Aggregation route
\end{minipage} & \begin{minipage}[b]{\linewidth}\raggedleft
Low-temperature result
\end{minipage} & \begin{minipage}[b]{\linewidth}\raggedright
Target A verdict
\end{minipage} \\
\midrule\noalign{}
\endhead
\bottomrule\noalign{}
\endlastfoot
Pooled, \texttt{normalize\_per\_draw=False} & 0.000 / 1.000 & Fails \\
Normalize each data-prior atom, then average & 0.400 / 0.600 & Exact \\
Shipped \texttt{normalize\_per\_draw=True} semantics (per-draw minimum shift) & 0.400 / 0.600 & Exact \\
\end{longtable}

\begin{figure}
\centering
\pandocbounded{\includegraphics[width=\linewidth]{figures/vanbork_targets.png}}
\caption{Target A aggregation and Target B temperature validation}
\end{figure}

\emph{Figure. Panel (a) compares the three Target A aggregation routes at the
smallest artifact temperature with the published targets. Panel (b) plots our
Target B \(p(M_x)\) across the artifact temperatures with their closed form
evaluated at double precision. Source: \texttt{runs/vanbork\_external\_validation/results.json}.
The figure re-plots committed artifact values without recomputation.}

Both per-draw routes have converged to the exact target by
\(\tau=10^{-4}\).\footnote{\evidencetier{empirical} \texttt{experiments/vanbork\_external\_validation.py}; \texttt{runs/vanbork\_external\_validation/results.json} and \texttt{README.md}; Notes/DECISIONS.md D60; Notes/DECISIONS.md D60 Resolution (2026-08-12).
  Figure: \texttt{experiments/vanbork\_figure.py} re-plots the committed artifact values without recomputation.} The shipped semantics and Eq. 4 aggregation remain
distinct computations: the former subtracts per-row minima and normalizes once
after pooling, whereas the latter normalizes each row into a model posterior
before averaging. They coincide in the \(\tau\)-to-zero unique-winner limit
exercised by Target A. The result exposes a modeling choice rather than a
numerical defect. Pooled aggregation preserves absolute divergence magnitudes:
a draw that every candidate fits poorly contributes less total support. That
property carries the M-open inadequacy signal, but pooled aggregation fails
Target A. Expected-posterior aggregation matches Eq. 4 and avoids that failure,
but each draw must spend one full unit of credit even when every candidate fits
poorly. The latter choice therefore discards the absolute-magnitude signal.

The author adopted the aggregation convention as an explicit evaluation dial
alongside \(\tau\) and \texttt{occam}. Canonical reporting keeps pooled aggregation to
preserve absolute divergence magnitudes, the M-open signal, and continuity with
every ratified number; the shipped \texttt{normalize\_per\_draw=False} default remains
unchanged. In Case A, the expected-posterior variant from Eq. 4 accompanies
pooled results wherever correspondence with van Bork et al.'s semantics matters,
while the \texttt{kl\_forward} aggregation attribution remains confined to the appendix.
Neither convention is declared universally correct.\footnote{\evidencetier{empirical} \texttt{experiments/vanbork\_external\_validation.py}; \texttt{runs/vanbork\_external\_validation/results.json} and \texttt{README.md}; Notes/DECISIONS.md D60; Notes/DECISIONS.md D60 Resolution (2026-08-12).
  Figure: \texttt{experiments/vanbork\_figure.py} re-plots the committed artifact values without recomputation.}

The E7 README recorded this stance as a candidate, which the author adopted on
2026-08-12.\footnote{\evidencetier{empirical} \texttt{experiments/e7\_convention\_sensitivity.py}; \texttt{runs/e7\_convention\_sensitivity/results.json} and \texttt{README.md}; Notes/DECISIONS.md D61. The committed Notes/DECISIONS.md D18 record supplies the \texttt{toy\_elicited} SIR hard fraction 0.696 (696/1000), whose correspondence with E7 is also noted in the E7 README.}

\textbf{Claim:} van Bork, Romeijn, and Wagenmakers advance the expected-support
construction as a principled source of prior model probability: candidates
earn probability through expected predictive alignment with the data prior,
and even completely overlapping models become distinguishable, grounding a
Wrinch-Jeffreys-style simplicity preference in prediction rather than
fiat.\footnote{\evidencetier{peer-reviewed} van Bork, R., Romeijn, J.-W., \& Wagenmakers, E.-J. (2025). Simplicity in Bayesian nested-model comparisons: Popper's disagreement with Wrinch and Jeffreys revisited. \emph{Synthese}. https://doi.org/10.1007/s11229-025-05286-y.} Section 3.2 locates that construction inside the present framework:
their formula arises from the hybrid \(Z_M\) in the zero-temperature,
shared-family, point-data-prior limit, and the case reproduces both published
targets. Containment rather than rivalry describes the relation: the framework
exposes through explicit controls what their construction fixes implicitly,
namely \(\tau\), \texttt{occam}, and the aggregation dial.

\textbf{Counterclaim:} the framework identifies a cost. Their Eq. 4 semantics
forces per-draw normalization, so every data-prior draw spends one full unit of
credit even when no candidate fits it, and absolute divergence magnitudes
disappear. Those magnitudes carry the framework's misspecification signal:
uniformly high divergence indicates that no candidate is adequate, as
exercised by the M-open reading in Case D, section 6. Adopted as canonical,
their construction would therefore silently foreclose misspecification
diagnosis, a cost the published account does not price. The evaluation dial
prices it explicitly: pooled aggregation retains the magnitudes, the Eq. 4
variant purchases external correspondence, and the trade remains visible at
the point of use.\footnote{\evidencetier{empirical} \texttt{experiments/e7\_convention\_sensitivity.py}; \texttt{runs/e7\_convention\_sensitivity/results.json} and \texttt{README.md}; Notes/DECISIONS.md D61. The committed Notes/DECISIONS.md D18 record supplies the \texttt{toy\_elicited} SIR hard fraction 0.696 (696/1000), whose correspondence with E7 is also noted in the E7 README.} Neither reading restores set-additive probabilities over
a hypothesis space (mapping row 5), so Popper's nesting constraint is dissolved
rather than answered by this family of constructions; section 4 prices the
residual disagreement empirically through the \texttt{occam} dial.

\subsection{Measured sensitivity on the validated toy path}

E7 evaluates the fork on the validated \texttt{toy\_elicited} SIR path. Under the
primary \texttt{pw\_kl\_vcal} metric at \(\tau=1\), pooled aggregation gives model
probabilities 0.183, 0.192, 0.441, and 0.184 for Linear, Sinusoidal,
Sin+Linear, and Quadratic, respectively. This row reproduces the ratified SIR
headline. Under this metric, Sin+Linear remains the highest-weight candidate at
every tested aggregation variant and temperature. The maximum absolute movement
between pooled and expected-posterior aggregation equals 0.31 at \(\tau=0.1\),
0.072 at \(\tau=1\), and 0.001 at \(\tau=10\); at \(\tau=1\), the Sin+Linear
weight changes from 0.441 to 0.513.\footnote{\evidencetier{empirical} \texttt{experiments/e7\_convention\_sensitivity.py}; \texttt{runs/e7\_convention\_sensitivity/results.json} and \texttt{README.md}; Notes/DECISIONS.md D61. The committed Notes/DECISIONS.md D18 record supplies the \texttt{toy\_elicited} SIR hard fraction 0.696 (696/1000), whose correspondence with E7 is also noted in the E7 README.} Within each metric, all three
aggregation variants use the same \(G\) matrix from one SIR realization
(\(n_{\mathrm{pred}}=1000\)), so the reported movements are paired differences
rather than differences of independent estimates.

The appendix-only \texttt{kl\_forward} stress metric reveals a sharper attribution.
With pooled aggregation, the Sin+Linear weight collapses to approximately
0.000 for \(\tau\leq1\). Expected-posterior aggregation instead gives 0.696 at
\(\tau=0.1\) in the E7 \texttt{results.json}. Analytically, expected-posterior
aggregation converges by construction to hard best-match fractions as \(\tau\)
approaches zero. At the reported precision, the E7 value equals the
\texttt{toy\_elicited} SIR hard fraction 0.696 (696/1000) in the committed D18 record,
a correspondence also noted in the E7 README. The earlier \texttt{kl\_forward}
fragility therefore reflects pooled-aggregation sensitivity to outlying draws,
not a property of the metric alone.\footnote{\evidencetier{empirical} \texttt{experiments/e7\_convention\_sensitivity.py}; \texttt{runs/e7\_convention\_sensitivity/results.json} and \texttt{README.md}; Notes/DECISIONS.md D61. The committed Notes/DECISIONS.md D18 record supplies the \texttt{toy\_elicited} SIR hard fraction 0.696 (696/1000), whose correspondence with E7 is also noted in the E7 README.}

\subsection{Multi-parameter reach under methods-validation framing}

An earlier informative-configuration, MAP-based visualization arm provides a
methods-validation reach check rather than a paper-facing inferential
headline. In \texttt{runs/viz\_unification/p3\_priors\_canonical/}, the multi-parameter
Sin+Linear candidate receives 0.992 at \(n=50\) and stays at or above 0.93
across all evaluated \(n\). This result shows that the same induced-prior
machinery extends beyond the closed-form coin targets to a richer candidate
family. It does not replace the validated \texttt{toy\_elicited} SIR result above.\footnote{\evidencetier{empirical} D17-recorded findings for the local, untracked \texttt{runs/viz\_unification/p3\_priors\_canonical/} arm, generated by \texttt{bistar\_viz/scripts/viz\_unification\_compare.py} through \texttt{bistar\_viz/scripts/model\_priors\_laplace.py}. The informative-configuration, MAP-based Sin+Linear candidate receives 0.992 at \(n=50\) and stays at or above 0.93 across all evaluated \(n\); the committed Notes/DECISIONS.md D17 record supplies their citation provenance and the \texttt{bistar\_viz} scripts regenerate them.}

---------- 04-case-B.tex ----------
%% Generated from docs/paper-sie-jmp/04-case-B-occam-dial.md
%% Source branch: paper/case-b-occam-dial
%% Do not hand-edit; see docs/paper-sie-jmp/build_tex.py
\section{Case B: the occam flag as the Popper/Wrinch-Jeffreys dial}

van Bork, Romeijn, and Wagenmakers restate Popper's objection to the
Wrinch-Jeffreys treatment of nested models: if M\_r \ensuremath{\subset} M\_e, assigning more prior
probability to the restricted model M\_r violates the encompassing-model
constraint. Wrinch and Jeffreys instead permit a simplicity preference for
M\_r. Their analysis motivates a direct question for the induced model prior
Z\_M: which position does its reference measure encode?\footnote{\evidencetier{peer-reviewed} van Bork, Romeijn, and Wagenmakers (2025), \emph{Synthese}, doi:10.1007/s11229-025-05286-y.}

The toy roster contains two relevant restrictions. Linear follows from
Sin+Linear at A=0, and Sinusoidal follows at b=c=0. Quadratic does not form a
restriction of Sin+Linear. The \texttt{occam} flag changes the measure used in Z\_M:
\texttt{occam=False} integrates against raw Lebesgue measure, following the canonical
BI* convention, whereas \texttt{occam=True} divides by the reference volume
V\_ref.\footnote{\evidencetier{empirical} \texttt{Notes/DECISIONS.md} D3, D5, and D17; legacy regeneration through \texttt{bistar\_viz/scripts/viz\_unification\_compare.py} at pinned commit \texttt{a87356a}.}

\subsection{An attribution ladder, not a two-arm ablation}

Figure 4 recomputes the three D17 attribution arms at n=50 and \ensuremath{\tau}=0.3, with the
\texttt{informative} GP configuration and a MAP predictive. These values serve
methods validation and legacy comparison. They do not provide paper-facing
posterior inference about which model generated the data.\footnote{\evidencetier{empirical} \texttt{experiments/occam\_dial\_figure.py}; \texttt{runs/occam\_dial/figure\_results.json}.}

\begin{figure}
\centering
\pandocbounded{\includegraphics[width=\linewidth]{figures/occam_dial.png}}
\caption{Three-arm Occam-dial comparison at n=50}
\end{figure}

\textbf{Figure 4.} Induced model priors for the nested toy roster. The p1 and p3
panels differ in both the Z\_M estimator and the \texttt{occam} convention, so the p2
panel prevents a conflated attribution. Replacing pure Laplace with IS while
retaining \texttt{occam=True} changes the Linear and Sin+Linear probabilities from
0.534 and 0.382 in p1 to 0.507 and 0.465 in p2. Changing only the convention
in the next step gives 0.007 and 0.992 in p3. At p2, ESS implies SE(log Z) of
approximately 0.008, 0.017, and 0.038 nats for Linear, Sin+Linear, and
Sinusoidal, respectively, with probability SE approximately 0.005. The estimator
change narrows the gap; removing the V\_ref normalization decides the verdict.
The dial figure argues about the \texttt{occam} convention's effect, not about which
model generated the data.

The figure's \ensuremath{\tau}=0.3 evaluation point falls 1.6 percent above the \texttt{occam=True}
Linear/Sin+Linear crossing at \ensuremath{\tau}\ensuremath{\approx}0.295. The p2 log Z\_M gap of 0.0867 nats gives
a Bayes factor of about 1.09, so the \texttt{occam=True} panels report an essentially
tied comparison. The p1/p2 ``Linear preferred'' reading therefore remains
\ensuremath{\tau}-marginal, while the p2-to-p3 magnitude change provides the robust content.

The earlier contradiction supplies useful historical context but not new
evidence. D17 records 0.934 for Sin+Linear in the legacy trajectory script and
0.693 for Linear in the legacy priors script, which hard-coded
\texttt{occam=True}. The pinned-commit extraction in
\texttt{viz\_unification\_compare.py} regenerates those legacy arms. The new figure
does not invoke or parse that extraction.\footnote{\evidencetier{empirical} \texttt{Notes/DECISIONS.md} D3, D5, and D17; legacy regeneration through \texttt{bistar\_viz/scripts/viz\_unification\_compare.py} at pinned commit \texttt{a87356a}.}

\subsection{E6: best achievable divergence under exact nesting}

As \ensuremath{\tau} approaches zero, the leading contribution to Z\_M comes from
min\_\ensuremath{\phi} \ensuremath{\bar{G}}(\ensuremath{\phi}). The reachable-set argument therefore requires

\[
\min_{\phi}\bar G(M_e) \leq \min_{\phi}\bar G(M_r).
\]

Different parameter dimensions prevent a Lebesgue-monotonicity argument in
parameter space. Given the two exact embeddings and the mean-only divergence,
however, the inequality follows analytically from reachable-set containment in
data space. The visualization box uses A \ensuremath{\geq} 0.01 as a numerical cutoff, so E6
alone extends the encompassing amplitude bound to A \ensuremath{\geq} 0. All other bounds
match the visualization arms. The restricted optima seed the encompassing
multi-start optimization, and the package divergence calculation reproduces
each restricted value at its embedding within the declared 10\^{}-10 tolerance.
E6 thereby confirms that the implementation reproduces the analytic
consequence, providing a machinery check rather than empirical support for the
containment claim.\footnote{\evidencetier{empirical} \texttt{experiments/e6\_nesting\_monotonicity.py}; \texttt{runs/occam\_dial/e6\_results.json}.}

For this n=50, \texttt{informative}-configuration, MAP-based averaged GP, the machinery
check obtains min\_\ensuremath{\phi} \ensuremath{\bar{G}}=0.046 for Sin+Linear, 2.425 for Linear, and 2.546 for
Sinusoidal. It quantifies restricted-minus-encompassing margins of 2.379 and
2.501 nats, respectively, far above the 10\^{}-8 comparison tolerance. The
empirical content of E6 consists of these margins and the finite-\ensuremath{\tau} Z\_M
crossings.\footnote{\evidencetier{empirical} \texttt{experiments/e6\_nesting\_monotonicity.py}; \texttt{runs/occam\_dial/e6\_results.json}.}

Finite \ensuremath{\tau} separates the two reference measures. One IS call per model per seed
evaluates 161 temperatures for seeds 0, 1, and 2. With \texttt{occam=False},
Sin+Linear retains the larger pairwise Z\_M throughout the grid for all three
seeds, so neither nested pair crosses. With \texttt{occam=True}, the Linear crossing
occurs at \ensuremath{\tau}=0.295, 0.295, and 0.296 across seeds 0, 1, and 2. Seed 0 has grid
bracket {[}0.282, 0.299{]}, the per-seed spread is {[}0.295, 0.296{]}, and its
ESS-implied one-SE shift interval is {[}0.295, 0.296{]}. The seed-0 bracket delta
swing of 0.354 nats exceeds the ESS-implied SE of approximately 0.012 nats, so
the three-decimal Linear crossing is sign-supported. The Sinusoidal crossing
occurs at 1.484, 1.584, and 1.382 across those seeds; it should be summarized
only as \ensuremath{\tau} \ensuremath{\approx} 1.5. Its seed-0 bracket is {[}1.413, 1.496{]}, the per-seed spread is
{[}1.382, 1.584{]}, and the seed-0 ESS shift roots are {[}1.392, 1.563{]}. The enclosing
grid-and-seed uncertainty interval is about \ensuremath{\tau} 1.33 to 1.59.
Crossing resolution is set by the larger of grid spacing and Monte Carlo error.
Thus low temperature supports Popper's encompassing constraint in both
conventions for this example, while V\_ref normalization permits the
finite-temperature simplicity preference associated with Wrinch and
Jeffreys.\footnote{\evidencetier{empirical} \texttt{experiments/e6\_nesting\_monotonicity.py}; \texttt{runs/occam\_dial/e6\_results.json}.}

The two controls should therefore remain explicit. Temperature governs how
strongly best achievable divergence dominates integrated compatibility, while
\texttt{occam} selects raw or volume-normalized reference measure. Their joint
sensitivity describes the Popper/Wrinch-Jeffreys disagreement without turning
a methods-validation example into a claim about model truth.

---------- 05-case-C.tex ----------
%% Generated from docs/paper-sie-jmp/05-case-C-nested-constraints.md
%% Source branch: paper/case-c-haaf
%% Do not hand-edit; see docs/paper-sie-jmp/build_tex.py
\section{Case C: a satisfied nested constraint under BMS* and LOO}

Haaf, Klaassen, and Rouder examine theories represented by restrictions on a
common parameter space. In their ordinal examples, WAIC and leave-one-out
cross-validation do not favor the restricted model even when the data comply
with its constraint. They argue that a forced partition into disjoint regions
can replace scientifically meaningful overlapping models with regions that
carry no theoretical interpretation.\footnote{\evidencetier{peer-reviewed} Haaf, Klaassen, and Rouder (2025). Bayes factor vs.~posterior predictive model assessment: Insights from ordinal constraints. \emph{Computational Brain \& Behavior}. https://doi.org/10.1007/s42113-025-00240-0} {[}Provisional framing: Kellen and
Klauer (2020) has not yet been read, so the phrase ``sharpest published
criticism'' remains provisional.{]}

Our experiment mirrors the parameter-region issue directly. It does not rely
on the toy example's cross-family nesting. The encompassing candidate
\(M_e\) uses

\[
y(x)=A\sin(\omega x+\phi)+bx+c+\epsilon,
\]

with unrestricted \(b\). The restricted candidate \(M_r \subset M_e\) uses the
same expression and imposes \(b\geq 0\). Both candidates call the same bounded
MLE routine, receive four shared base starts, and share every bound except the
lower bound on \(b\). The restricted fit additionally receives the free
solutions, clipped at \(b=0\) when necessary, and each candidate's selection
pool includes the other candidate's feasible vectors. This deliberate
asymmetry forces exact equality at shared optima instead of turning optimizer
noise into a gap. The frozen \(N=20\) data use seed 42 and the true slope
\(b=0.25\), so the restriction holds in truth.\footnote{\evidencetier{empirical} \texttt{experiments/haaf\_nested\_constraint.py}; \texttt{runs/haaf\_nested\_constraint/results.json} and \texttt{README.md} (data seed 42; prior-IS seeds 0, 1, 2; SIR seed 42; NUTS seeds 20260811 and 20260812).}

\subsection{BMS* comparison}

The BMS* calculation follows the validated \texttt{toy\_elicited} stage-IS path. It
pools prior-IS caches from seeds 0, 1, and 2, draws 1,000 SIR predictives with
seed 42, and evaluates 60 locations. For every predictive data pattern
\(\psi\), the fits are obtained by variance-weighted maximum likelihood toward
each \(\psi\); the primary \texttt{pw\_kl\_vcal} value \(G(\psi,\theta)\) is then minimized
by selection over the shared candidate pool, within each candidate's parameter
region.
Thus the calculation supplies candidate instances from a shared \(\psi\) rather
than introducing candidate-parameter priors. Such priors contribute only to
the separate LOO comparison below.\footnote{\evidencetier{empirical} \texttt{experiments/haaf\_nested\_constraint.py}; \texttt{runs/haaf\_nested\_constraint/results.json} and \texttt{README.md} (data seed 42; prior-IS seeds 0, 1, 2; SIR seed 42; NUTS seeds 20260811 and 20260812).}

The nesting relation fixes the primary-metric ordering as an identity of the
protocol: \(M_r\subset M_e\) implies
\(\min_{\theta\in M_r}G\geq\min_{\theta\in M_e}G\) for every predictive. The
cross-seeded candidate pools enforce this set inclusion numerically, while
re-evaluation of the same feasible vector gives exact equality at a shared
optimum. The \(2\times10^{-7}\) runtime gates guard against machinery
regressions; they do not provide an empirical nesting test. On 999
predictives, the free optimum had \(b\geq0\) and the primary \(G\) gap equaled
exactly zero. One predictive had a negative free optimum, for a fraction of
0.001, and restricted minus free \(G\) equaled 0.000360 on that row.\footnote{\evidencetier{empirical} \texttt{experiments/haaf\_nested\_constraint.py}; \texttt{runs/haaf\_nested\_constraint/results.json} and \texttt{README.md} (data seed 42; prior-IS seeds 0, 1, 2; SIR seed 42; NUTS seeds 20260811 and 20260812).}

This same set inclusion fixes the probability direction before Table 5.1.
The restricted candidate can never exceed the free candidate under either
aggregation at any \(\tau\); only the gap's magnitude depends on the sampled
predictives.\footnote{\evidencetier{empirical} \texttt{experiments/haaf\_nested\_constraint.py}; \texttt{runs/haaf\_nested\_constraint/results.json} and \texttt{README.md} (data seed 42; prior-IS seeds 0, 1, 2; SIR seed 42; NUTS seeds 20260811 and 20260812).}

Table 5.1 reports both aggregation conventions across the preregistered
temperature grid. Each pair normalizes over only the free and restricted
candidates.\footnote{\evidencetier{empirical} \texttt{experiments/haaf\_nested\_constraint.py}; \texttt{runs/haaf\_nested\_constraint/results.json} and \texttt{README.md} (data seed 42; prior-IS seeds 0, 1, 2; SIR seed 42; NUTS seeds 20260811 and 20260812).}

\begin{longtable}[]{@{}
  >{\raggedleft\arraybackslash}p{(\linewidth - 8\tabcolsep) * \real{0.2000}}
  >{\raggedleft\arraybackslash}p{(\linewidth - 8\tabcolsep) * \real{0.2000}}
  >{\raggedleft\arraybackslash}p{(\linewidth - 8\tabcolsep) * \real{0.2000}}
  >{\raggedleft\arraybackslash}p{(\linewidth - 8\tabcolsep) * \real{0.2000}}
  >{\raggedleft\arraybackslash}p{(\linewidth - 8\tabcolsep) * \real{0.2000}}@{}}
\toprule\noalign{}
\begin{minipage}[b]{\linewidth}\raggedleft
\(\tau\)
\end{minipage} & \begin{minipage}[b]{\linewidth}\raggedleft
pooled free
\end{minipage} & \begin{minipage}[b]{\linewidth}\raggedleft
pooled restricted
\end{minipage} & \begin{minipage}[b]{\linewidth}\raggedleft
expected-posterior free
\end{minipage} & \begin{minipage}[b]{\linewidth}\raggedleft
expected-posterior restricted
\end{minipage} \\
\midrule\noalign{}
\endhead
\bottomrule\noalign{}
\endlastfoot
0.1 & 0.500 & 0.500 & 0.500 & 0.500 \\
0.3 & 0.500 & 0.500 & 0.500 & 0.500 \\
1.0 & 0.500 & 0.500 & 0.500 & 0.500 \\
3.0 & 0.500 & 0.500 & 0.500 & 0.500 \\
10.0 & 0.500 & 0.500 & 0.500 & 0.500 \\
\end{longtable}

At the headline value \(\tau=1\), both conventions therefore give an effective
tie. The free-minus-restricted probability gap remains smaller than
\(10^{-5}\) at every \(\tau\) under both conventions and comes entirely from the
single negative-slope draw. Its monotone contraction with \(\tau\) follows
deterministically from the Boltzmann aggregation, not from a measured
temperature effect.\footnote{\evidencetier{empirical} \texttt{experiments/haaf\_nested\_constraint.py}; \texttt{runs/haaf\_nested\_constraint/results.json} and \texttt{README.md} (data seed 42; prior-IS seeds 0, 1, 2; SIR seed 42; NUTS seeds 20260811 and 20260812).}

The result does not support a claim that BMS* preferentially rewards a
satisfied restriction. BMS* assigns the restricted candidate
essentially half the probability without partitioning the parameter space,
but the encompassing candidate can reproduce every restricted optimum. The
single predictive with a negative slope creates the entire primary-metric gap.
Without an explicit parameter-volume or complexity term, the satisfied
restriction supplies equality on shared optima rather than an automatic
advantage. Soft transfer makes that null result visible across \(\tau\); a hard
best-match treatment would retain only the limiting row assignments.

\subsection{PSIS-LOO comparison}

Both Bayesian candidates use the identical 20 observations and likelihood.
Their weakly informative priors apply only to this LOO arm: \(A\sim\)
HalfNormal(5), \(\omega\sim\) LogNormal(0, 0.7), \(\phi\sim\)
Uniform(\(-\pi,\pi\)), \(c\sim\) Normal(0, 5), and \(\sigma\sim\)
HalfNormal(2). The free model uses \(b\sim\) Normal(0, 5); the restricted model
uses the corresponding zero-truncated distribution, \(b\sim\) HalfNormal(5).
No prior from this list enters the BMS* calculation.\footnote{\evidencetier{empirical} \texttt{experiments/haaf\_nested\_constraint.py}; \texttt{runs/haaf\_nested\_constraint/results.json} and \texttt{README.md} (data seed 42; prior-IS seeds 0, 1, 2; SIR seed 42; NUTS seeds 20260811 and 20260812).}

Pyro NUTS ran two sequential chains with seeds 20260811 and 20260812. Each
chain used 1,000 warmup iterations and retained 1,000 draws, with target
acceptance probability 0.90 and maximum tree depth 8. Both chains for both
candidates initialized deterministically at the same observed-data MLE through
\texttt{init\_to\_value}: \(A=0.886352\), \(\omega=1.030240\), \(\phi=-0.029881\),
\(b=0.251277\), \(c=0.028723\), and \(\sigma=0.321232\). Sampled-grid aliases near
\(\omega=4.939\) and \(6.999\) make the \(\omega\)/\(\phi\) likelihood multimodal.
Both fits recorded zero divergences. Rank-normalized \(\widehat R\) reached at
most 1.003 for the free fit and 1.002 for the restricted fit; minimum bulk
effective sample sizes were 1,004 and 1,638, respectively. These diagnostics
support within-mode convergence only, not exploration across modes.\footnote{\evidencetier{empirical} \texttt{experiments/haaf\_nested\_constraint.py}; \texttt{runs/haaf\_nested\_constraint/results.json} and \texttt{README.md} (data seed 42; prior-IS seeds 0, 1, 2; SIR seed 42; NUTS seeds 20260811 and 20260812).}

\begin{longtable}[]{@{}
  >{\raggedright\arraybackslash}p{(\linewidth - 10\tabcolsep) * \real{0.1364}}
  >{\raggedleft\arraybackslash}p{(\linewidth - 10\tabcolsep) * \real{0.1818}}
  >{\raggedleft\arraybackslash}p{(\linewidth - 10\tabcolsep) * \real{0.1818}}
  >{\raggedleft\arraybackslash}p{(\linewidth - 10\tabcolsep) * \real{0.1818}}
  >{\raggedleft\arraybackslash}p{(\linewidth - 10\tabcolsep) * \real{0.1818}}
  >{\raggedright\arraybackslash}p{(\linewidth - 10\tabcolsep) * \real{0.1364}}@{}}
\toprule\noalign{}
\begin{minipage}[b]{\linewidth}\raggedright
candidate
\end{minipage} & \begin{minipage}[b]{\linewidth}\raggedleft
\texttt{elpd\_loo}
\end{minipage} & \begin{minipage}[b]{\linewidth}\raggedleft
SE
\end{minipage} & \begin{minipage}[b]{\linewidth}\raggedleft
\texttt{p\_loo}
\end{minipage} & \begin{minipage}[b]{\linewidth}\raggedleft
max Pareto \(k\)
\end{minipage} & \begin{minipage}[b]{\linewidth}\raggedright
warning
\end{minipage} \\
\midrule\noalign{}
\endhead
\bottomrule\noalign{}
\endlastfoot
free Sin+Linear & -13.074 & 3.458 & 5.343 & 0.564 & no \\
slope-constrained Sin+Linear & -12.661 & 3.594 & 5.169 & 0.718 & yes, one observation \\
\end{longtable}

The constrained-minus-free \texttt{elpd\_loo} difference equals 0.413 with a paired SE
of 0.256, computed with \texttt{ddof=0} to match the ArviZ convention.\footnote{\evidencetier{empirical} \texttt{experiments/haaf\_nested\_constraint.py}; \texttt{runs/haaf\_nested\_constraint/results.json} and \texttt{README.md} (data seed 42; prior-IS seeds 0, 1, 2; SIR seed 42; NUTS seeds 20260811 and 20260812).} The
difference is directionally inconclusive: its magnitude is smaller than twice
its paired SE, the constrained estimate carries a Pareto-\(k\) warning because
one observation exceeds the 0.697 good-\(k\) threshold, and the paired SE covers
data-level pointwise variability only, without MCMC error. Haaf, Klaassen, and
Rouder report this kind of null-to-inconclusive LOO difference as the failure
mode for a satisfied nested constraint.\footnote{\evidencetier{peer-reviewed} Haaf, Klaassen, and Rouder (2025). Bayes factor vs.~posterior predictive model assessment: Insights from ordinal constraints. \emph{Computational Brain \& Behavior}. https://doi.org/10.1007/s42113-025-00240-0} Pareto shape values above about
0.7 can make the importance-sampling approximation unreliable, so a decisive
direction would require exact refits or a more robust cross-validation
calculation.\footnote{\evidencetier{peer-reviewed} Vehtari, Gelman, and Gabry (2017). Practical Bayesian model evaluation using leave-one-out cross-validation and WAIC. \emph{Statistics and Computing}, 27(5), 1413--1432.}

The two slope priors coincide up to normalization on \(b>0\), so LOO has no
structural contrast wherever negative-slope posterior mass is negligible. The
artifact's own full-data local Gaussian diagnostic gives posterior SD
0.0129506 for \(b\), places the boundary 19.4028 SDs away, and gives a Gaussian
left-tail probability of \(3.65\times10^{-84}\). This local approximation
supports the reading that the constraint binds only where the locally
approximated posterior carries negligible mass. It does not prove that the
global posteriors or leave-one-out fold posteriors are exactly identical, and
it does not establish that the entire observed gap comes from estimator
noise.\footnote{\evidencetier{empirical} \texttt{experiments/haaf\_nested\_constraint.py}; \texttt{runs/haaf\_nested\_constraint/results.json} and \texttt{README.md} (data seed 42; prior-IS seeds 0, 1, 2; SIR seed 42; NUTS seeds 20260811 and 20260812).}

The LOO arm therefore reproduces the null-to-inconclusive failure mode without
supporting a directional claim. BMS* also gives a numerical tie, with a
one-sided direction fixed by nesting and a magnitude determined by the single
negative-slope SIR draw.

---------- 06-case-D.tex ----------
%% Generated from docs/paper-sie-jmp/06-case-D-mopen-calibration.md
%% Source branch: paper/case-d-mopen
%% Do not hand-edit; see docs/paper-sie-jmp/build_tex.py
\section{Case D: M-open calibration through a warranted decline {[}DRAFT{]}}

\subsection{Calibration before an M-open claim}

A relative winner does not establish adequacy. BMS* retains the raw
divergences (G(\psi,\theta)), so it can ask whether even the closest candidate
remains far from the GP patterns. That absolute reading needs a reference
distribution under known truth. Without one, a large-looking value has no
calibrated interpretation. Formal M-open calibration therefore remains an open
problem.

The practice-law artifacts offer a bounded first step, not an M-open test. Their
data directory contains no Evans et al.~observations. \texttt{run.py} instead generated
50 synthetic series with seed 42, divided equally between power and exponential
truth. Each subject's generating form appears among the two fitted candidates.
The source artifacts record between 20 and 79 observations per subject, and the
stored practice (G) values were computed on 50 uniformly spaced points spanning
each subject's full series. The reconstructed deviation curves instead cover
integer trials 1 through 20. For the longest subjects, that early grid spans
19/78, or 24.4\%, of the full continuous trial range. Any linkage between those
curves and the stored aggregate comparisons therefore applies only to their
shared early-trial region. We use these data to study distinguishability and
mimicry and to establish correct-specification reference levels for (G); we do
not infer how either candidate fits the real Evans corpus.\footnote{\evidencetier{empirical} \texttt{experiments/regret\_curves\_mopen.py}; \texttt{runs/regret\_curves\_mopen/results.json} and \texttt{regret\_curves.png}. The script reads \texttt{experiments/practice\_EvansEtAL/results\_hmc/aggregate.json} and its 50 subject JSONs, asserts reconstruction fidelity, and records all reported practice-run numbers in one artifact.}
Evans et al.'s broader candidate discussion motivates the context, while every
result below concerns only Power and Exponential, the pair retained in the
stored fits.\footnote{\evidencetier{peer-reviewed} Evans, N. J., Brown, S. D., Mewhort, D. J. K., \& Heathcote, A. (2018). Refining the law of practice. \emph{Psychological Review, 125}(4), 592--605.}

\subsection{Two failure geometries}

Two obstacles require separate diagnoses. F1 concerns scaffold
representability. A stationary RBF kernel assigns one global lengthscale, while
power and exponential curves differ through a location-dependent rate of
curvature change. The scaffold can smooth over the local feature needed for
discrimination. F2 concerns intrinsic mimicry. Across some parameter regions,
the candidate families generate nearly indistinguishable patterns, so changing
the scoring rule cannot create information absent from the data.

Navarro, Pitt, and Myung's landscaping method maps such variation in
distinguishability over retention-model parameter spaces. Their analysis shows
why a close fit at one observed data set cannot establish that the models were
distinguishable there: one candidate may mimic another over a broad region.\footnote{\evidencetier{peer-reviewed} Navarro, D. J., Pitt, M. A., \& Myung, I. J. (2004). Assessing the distinguishability of models and the informativeness of data. \emph{Cognitive Psychology, 49}(1), 47--84. https://doi.org/10.1016/j.cogpsych.2003.11.001}
Their empirical setting concerned retention rather than practice, so the link
here concerns failure geometry, not a replication. Under that geometry, weak
separation can reflect a warranted decline rather than a failed demand for a
winner. The synthetic known-truth design sharpens the interpretation: when the
correct family appears in the roster yet remains hard to recover, F1, F2, or
both have constrained the comparison.

\subsection{What the stored comparisons declined}

We prefer \texttt{results\_hmc/} over the MAP-mode directory because it contains the
HMC-mode practice run requested for this case. Its aggregate baseline assigns
18 subjects to Power and 32 to Exponential under BIC, although the generator
split equals 25 and 25; 41 of 50 labels match known truth. The BMS* winner labels
at the stored median temperature, \ensuremath{\tau} = 1.778, vary substantially with the legacy
pointwise metric:

\begin{longtable}[]{@{}
  >{\raggedright\arraybackslash}p{(\linewidth - 6\tabcolsep) * \real{0.2000}}
  >{\raggedleft\arraybackslash}p{(\linewidth - 6\tabcolsep) * \real{0.2667}}
  >{\raggedleft\arraybackslash}p{(\linewidth - 6\tabcolsep) * \real{0.2667}}
  >{\raggedleft\arraybackslash}p{(\linewidth - 6\tabcolsep) * \real{0.2667}}@{}}
\toprule\noalign{}
\begin{minipage}[b]{\linewidth}\raggedright
GP configuration
\end{minipage} & \begin{minipage}[b]{\linewidth}\raggedleft
\texttt{pw\_hellinger}, Power / Exponential
\end{minipage} & \begin{minipage}[b]{\linewidth}\raggedleft
\texttt{pw\_mse}, Power / Exponential
\end{minipage} & \begin{minipage}[b]{\linewidth}\raggedleft
\texttt{pw\_nll}, Power / Exponential
\end{minipage} \\
\midrule\noalign{}
\endhead
\bottomrule\noalign{}
\endlastfoot
practitioner & 22 / 28 & 6 / 44 & 10 / 40 \\
moderate & 32 / 18 & 7 / 43 & 12 / 38 \\
agnostic & 27 / 23 & 7 / 43 & 12 / 38 \\
\end{longtable}

Across the 50 subjects, all three configurations select the same winner for 39
subjects under \texttt{pw\_hellinger}, 49 under \texttt{pw\_mse}, and 48 under \texttt{pw\_nll}.

These practice artifacts predate W1. They contain \texttt{pw\_nll}, \texttt{pw\_mse}, and
\texttt{pw\_hellinger}, not the manuscript's primary \texttt{pw\_kl\_vcal}; no new metric was
authorized for Case D, and we do not relabel the stored quantities.
Legacy \texttt{pw\_nll} weights squared error by the candidate's fitted noise variance,
whereas \texttt{pw\_kl\_vcal} weights it by the GP variance. On that weighting axis,
\texttt{pw\_mse} lies closer to the manuscript primary.

For all 300 stored configuration-by-subject-by-candidate \texttt{mean\_G} pairs,
\texttt{pw\_nll\ =\ 0.5\ log(2\ pi\ sigma\_theta\^{}2)\ +\ pw\_mse/(2\ sigma\_theta\^{}2)} to maximum
absolute error \(1.78 \times 10^{-15}\). Thus \texttt{pw\_nll} and \texttt{pw\_mse} apply a
candidate-specific affine map to the same squared-error statistic; the divisor
\texttt{2\ sigma\_theta\^{}2} ranges from 743 to 7,161, approximately 750 to 7,150. BMS*
scores \texttt{exp(-G/tau)} at a shared \(\tau\), so soft-transfer probability magnitudes
are not comparable across metrics on different scales. No value on the stored
15-point grid removes the gap: at \(\tau=0.1\), the power-cohort \texttt{pw\_nll} medians
are 0.581, 0.569, and 0.557 for practitioner, moderate, and agnostic,
respectively, while the all-subject practitioner \texttt{pw\_mse} median remains 0.987
at \(\tau=31.6\).\footnote{\evidencetier{empirical} \texttt{experiments/regret\_curves\_mopen.py}; \texttt{runs/regret\_curves\_mopen/results.json} and \texttt{regret\_curves.png}. The script reads \texttt{experiments/practice\_EvansEtAL/results\_hmc/aggregate.json} and its 50 subject JSONs, asserts reconstruction fidelity, and records all reported practice-run numbers in one artifact.}

The tau-free, scale-invariant \texttt{pw\_nll} \texttt{raw\_draw\_wins} diagnostic carries the
asymmetry instead:

\begin{longtable}[]{@{}
  >{\raggedright\arraybackslash}p{(\linewidth - 4\tabcolsep) * \real{0.2727}}
  >{\raggedleft\arraybackslash}p{(\linewidth - 4\tabcolsep) * \real{0.3636}}
  >{\raggedleft\arraybackslash}p{(\linewidth - 4\tabcolsep) * \real{0.3636}}@{}}
\toprule\noalign{}
\begin{minipage}[b]{\linewidth}\raggedright
GP configuration
\end{minipage} & \begin{minipage}[b]{\linewidth}\raggedleft
Power truth: true-family draw wins / subject majorities
\end{minipage} & \begin{minipage}[b]{\linewidth}\raggedleft
Exponential truth: true-family draw wins / subject majorities
\end{minipage} \\
\midrule\noalign{}
\endhead
\bottomrule\noalign{}
\endlastfoot
practitioner & 39.0\% / 9 of 25 & 98.7\% / 25 of 25 \\
moderate & 39.9\% / 8 of 25 & 94.6\% / 25 of 25 \\
agnostic & 41.5\% / 9 of 25 & 92.1\% / 25 of 25 \\
\end{longtable}

These \texttt{pw\_nll} counts describe how often the known-truth candidate attains the
smaller raw divergence on the 100 stored GP draws per subject. They support a
metric-specific asymmetric-recovery statement without interpreting a
temperature-dependent probability magnitude.\footnote{\evidencetier{empirical} \texttt{experiments/regret\_curves\_mopen.py}; \texttt{runs/regret\_curves\_mopen/results.json} and \texttt{regret\_curves.png}. The script reads \texttt{experiments/practice\_EvansEtAL/results\_hmc/aggregate.json} and its 50 subject JSONs, asserts reconstruction fidelity, and records all reported practice-run numbers in one artifact.}

\subsection{Absolute divergence magnitudes}

Rankings discard the common level of mismatch. The stored \texttt{pw\_nll}
diagnostics retain the mean (G) over 100 GP draws for each fitted candidate.
The cohort means below come directly from those stored values; the Case D
script aggregates them without recomputing (G).

\begin{longtable}[]{@{}
  >{\raggedright\arraybackslash}p{(\linewidth - 8\tabcolsep) * \real{0.1579}}
  >{\raggedleft\arraybackslash}p{(\linewidth - 8\tabcolsep) * \real{0.2105}}
  >{\raggedleft\arraybackslash}p{(\linewidth - 8\tabcolsep) * \real{0.2105}}
  >{\raggedleft\arraybackslash}p{(\linewidth - 8\tabcolsep) * \real{0.2105}}
  >{\raggedleft\arraybackslash}p{(\linewidth - 8\tabcolsep) * \real{0.2105}}@{}}
\toprule\noalign{}
\begin{minipage}[b]{\linewidth}\raggedright
GP configuration
\end{minipage} & \begin{minipage}[b]{\linewidth}\raggedleft
Power truth: (G\_\{\mathrm{Power}\})
\end{minipage} & \begin{minipage}[b]{\linewidth}\raggedleft
Power truth: (G\_\{\mathrm{Exp}\})
\end{minipage} & \begin{minipage}[b]{\linewidth}\raggedleft
Exponential truth: (G\_\{\mathrm{Power}\})
\end{minipage} & \begin{minipage}[b]{\linewidth}\raggedleft
Exponential truth: (G\_\{\mathrm{Exp}\})
\end{minipage} \\
\midrule\noalign{}
\endhead
\bottomrule\noalign{}
\endlastfoot
practitioner & 4.799 & 4.775 & 5.003 & 4.582 \\
moderate & 4.858 & 4.830 & 5.045 & 4.688 \\
agnostic & 4.834 & 4.811 & 5.045 & 4.715 \\
\end{longtable}

Within these \texttt{pw\_nll} summaries, the power-generated rows exhibit the mimicry
signature: both magnitudes nearly coincide, and the wrong exponential candidate
has the slightly smaller cohort mean. The \texttt{pw\_nll} exponential-generated rows
separate more clearly and favor the known truth. At synthetic exponential
subject 25, the practitioner \texttt{pw\_nll} means
equal 4.881 for Power and 4.852 for Exponential, an absolute difference of
0.029. A ranking reports only Exponential; the paired magnitudes show how
little separates the candidates for that subject.\footnote{\evidencetier{empirical} \texttt{experiments/regret\_curves\_mopen.py}; \texttt{runs/regret\_curves\_mopen/results.json} and \texttt{regret\_curves.png}. The script reads \texttt{experiments/practice\_EvansEtAL/results\_hmc/aggregate.json} and its 50 subject JSONs, asserts reconstruction fidelity, and records all reported practice-run numbers in one artifact.}

The \texttt{pw\_nll} table also blocks an overstatement about M-open inadequacy.
Correctly specified candidates can produce \texttt{pw\_nll} mean (G) values from 4.582
to 4.858 in these cohort summaries, while a wrong but mimicking candidate can
occupy much of the same scale. A future inadequacy rule must compare an observed
magnitude with a
reference distribution under correct specification, conditional on metric,
configuration, sample size, and noise. These known-truth \texttt{mean\_G} distributions
supply the kind of calibration material such a rule needs, but Case D does not
set a rejection threshold.

\subsection{MAP-conditional deviation localizes the comparison}

The subject JSONs omit GP curves and draws. The new reconstruction regenerates
the synthetic observations, verifies each stored candidate fit through its BIC
residual structure, rebuilds an exact GP at the stored hyperparameters, and
computes its latent posterior mean plus 100 seeded latent posterior functions
per subject. No refitting and no new HMC occur.

One provenance and estimand limitation matters. \texttt{run.py} writes one
\texttt{gp\_hyperparameters} block immediately after the first successful configuration
MAP fit. With the default order, all 50 source files record the practitioner MAP
point even though \texttt{results\_hmc/} subsequently uses HMC samples for its stored
BMS* diagnostics. The JSONs do not retain those HMC hyperparameter draws, so
neither reconstruction below averages posterior mean functions over
hyperparameter draws as in the limits-note formula. The solid curves instead
report the MAP-conditional posterior expected absolute deviation of the latent
function,

\[
R^{\mathrm{draw}}_{\theta}(t)
= \mathbb{E}_{f\mid y,\hat{\eta}}
  \left[\left|f(t)-\mu_{\theta}(t)\right|\right],
\]

and the dashed curves report the mean-based plug-in at the same MAP point,

\[
R^{\mathrm{mean}}_{\theta}(t)
= \left|\mathbb{E}\!\left[f(t)\mid y,\hat{\eta}\right]
  -\mu_{\theta}(t)\right|.
\]

Jensen's inequality orders the exact estimands: the exact
\(R^{\mathrm{draw}}_{\theta}(t)\) is no smaller than
\(R^{\mathrm{mean}}_{\theta}(t)\) for each subject, candidate, and trial. The
finite 100-draw Monte Carlo estimates carry Monte Carlo error and may invert
locally, as at trial 1 for the Power candidate under Power truth (116.333 versus
116.506) and Exponential truth (131.415 versus 131.572). Latent posterior spread
therefore inflates candidate deviations and generally compresses their gap by a
trial-dependent amount, so the two estimands should not be substituted silently.

Each solid line pools 25 subjects and 100 draws within a truth cohort. Its band
spans the pooled 10th and 90th percentiles of the resulting 2,500 absolute
errors at each trial; it describes subject-and-draw dispersion, not uncertainty
in the cohort mean. Each dashed line averages the 25 subject-level plug-in
deviations; corresponding subject quantiles remain in \texttt{results.json}.

\begin{figure}
\centering
\pandocbounded{\includegraphics[width=\linewidth]{figures/regret_curves.png}}
\caption{MAP-conditional deviation curves for the two synthetic truth cohorts}
\end{figure}

\begin{longtable}[]{@{}
  >{\raggedright\arraybackslash}p{(\linewidth - 12\tabcolsep) * \real{0.1154}}
  >{\raggedright\arraybackslash}p{(\linewidth - 12\tabcolsep) * \real{0.1154}}
  >{\raggedleft\arraybackslash}p{(\linewidth - 12\tabcolsep) * \real{0.1538}}
  >{\raggedleft\arraybackslash}p{(\linewidth - 12\tabcolsep) * \real{0.1538}}
  >{\raggedleft\arraybackslash}p{(\linewidth - 12\tabcolsep) * \real{0.1538}}
  >{\raggedleft\arraybackslash}p{(\linewidth - 12\tabcolsep) * \real{0.1538}}
  >{\raggedleft\arraybackslash}p{(\linewidth - 12\tabcolsep) * \real{0.1538}}@{}}
\toprule\noalign{}
\begin{minipage}[b]{\linewidth}\raggedright
Estimand
\end{minipage} & \begin{minipage}[b]{\linewidth}\raggedright
Truth cohort
\end{minipage} & \begin{minipage}[b]{\linewidth}\raggedleft
Mean Power deviation (RT units)
\end{minipage} & \begin{minipage}[b]{\linewidth}\raggedleft
Mean Exponential deviation (RT units)
\end{minipage} & \begin{minipage}[b]{\linewidth}\raggedleft
Peak gap (RT units)
\end{minipage} & \begin{minipage}[b]{\linewidth}\raggedleft
Gap in trials 1--5
\end{minipage} & \begin{minipage}[b]{\linewidth}\raggedleft
Gap in trials 1--10
\end{minipage} \\
\midrule\noalign{}
\endhead
\bottomrule\noalign{}
\endlastfoot
MAP-conditional posterior expected absolute deviation & Power & 21.383 & 20.681 & 33.782 at trial 1 & 70.0\% & 82.2\% \\
Posterior-mean plug-in & Power & 17.638 & 17.325 & 34.052 at trial 1 & 63.3\% & 74.0\% \\
MAP-conditional posterior expected absolute deviation & Exponential & 35.587 & 14.855 & 91.452 at trial 1 & 41.7\% & 77.7\% \\
Posterior-mean plug-in & Exponential & 33.901 & 10.764 & 92.890 at trial 1 & 40.0\% & 75.0\% \\
\end{longtable}

Both profiles concentrate toward the beginning but do not collapse to only the
first few trials. For the MAP-conditional posterior expected absolute deviation
under power truth, trial 1 produces 116.333 RT units for Power and 82.551 for
Exponential, with the wrong family closer where the largest gap occurs. Under
exponential truth, the corresponding values equal 131.415 and 39.963, and
appreciable separation continues through the first half of the grid. The two
estimands therefore show a consistent descriptive localization under the
stored practitioner-MAP scaffold. Within the shared early-trial region, that
localization agrees with the asymmetric practitioner \texttt{pw\_nll} raw-draw result;
it cannot explain the portion of the stored aggregate comparison evaluated
later in each subject's full series.\footnote{\evidencetier{empirical} \texttt{experiments/regret\_curves\_mopen.py}; \texttt{runs/regret\_curves\_mopen/results.json} and \texttt{regret\_curves.png}. The script reads \texttt{experiments/practice\_EvansEtAL/results\_hmc/aggregate.json} and its 50 subject JSONs, asserts reconstruction fidelity, and records all reported practice-run numbers in one artifact.}

The branch contains exactly one practitioner-MAP RBF reconstruction, and all
three stored configurations use the RBF family. These artifacts cannot identify
whether the localized \texttt{pw\_nll} recovery asymmetry originates in F1
representability, F2 mimicry, metric behavior, or sampling noise. That
non-identifiability matches the F1/F2-agnostic interpretation above.

\subsection{Positioning and optional extension}

Averell and Heathcote showed that power-versus-exponential conclusions about
forgetting can change between individual-level and population-level analyses.
Their result warns against treating one comparison procedure or aggregation
level as a resolution of the functional-form debate.\footnote{\evidencetier{peer-reviewed} Averell, L., \& Heathcote, A. (2011). The form of the forgetting curve and the fate of memories. \emph{Journal of Mathematical Psychology, 55}(1), 25--35.} Case D
supports a narrower conclusion. On synthetic practice curves, the legacy
\texttt{pw\_nll} raw-draw results show asymmetric recovery, its raw divergence
magnitudes provide correct-specification reference levels, and both
MAP-conditional deviation estimands descriptively localize part of that
asymmetry in the shared early-trial region. Nothing here identifies its cause or
adjudicates the real practice data or the forgetting literature.

\begin{quote}
\textbf{{[}E8B-PLACEHOLDER{]} UNBUILT OPTIONAL MODULE.} The proposed extension would
refit in semi-log and log-log spaces, with an explicit lognormal or
heteroskedastic noise correction, to turn curvature-rate differences into a
global linearity comparison; a Murre and Dros real-data companion would
remain separate from the present synthetic cohort. The driver deferred
\texttt{e8b\_transform\_space.py} in this pass. The author may commission the module or
excise this entire block; the current evidence makes no transform-space
claim.
\end{quote}

---------- 07-debias.tex ----------
%% Generated from docs/paper-sie-jmp/07-debias-bridge.md
%% Source branch: paper/case-e-debias
%% Do not hand-edit; see docs/paper-sie-jmp/build_tex.py
\section{From evaluation to debiasing}

The accepted proposal and thesis chapter 5 set two goals for this program:
evaluating candidate models through data priors, and mitigating bias. Sections
1 through 6 and 8 develop the first. The second follows from the same
construction rather than from new machinery. Candidates are graded against the
posterior over data patterns \ensuremath{\psi}, and that posterior supports more than grading.
Under an additive kernel the function underlying each \ensuremath{\psi} decomposes into
components, each component admits a substantive label, and labeling one
component as bias turns its removal into marginalization. Evaluation and
mitigation therefore draw on one object.\footnote{\evidencetier{thesis} Chandramouli (2020), doctoral dissertation, Indiana University; Chapter 5 instantiates BI* with Gaussian Processes and states the debiasing program. \evidencetier{framework} Chandramouli and Shiffrin (2016), ``Extending Bayesian induction,'' \emph{Journal of Mathematical Psychology}, 72, 38--42.}

\subsection{The demonstration}

Section 3.4 grades candidate models against the posterior this same GP
configuration induces on the N=20 seed-42 instance described below, and puts
most weight on the Sin+Linear candidate, 0.441 under pw\_kl\_vcal at \ensuremath{\tau}=1 with
pooled aggregation on the SIR path. The demonstration here decomposes that same
GP posterior, estimated now by NUTS rather than by SIR, into an SE and a linear
component; the winning candidate's sinusoid-plus-drift shape mirrors that
additive split without being the object decomposed.\footnote{\evidencetier{empirical} \texttt{experiments/toy\_debias\_demo.py}; \texttt{runs/toy\_debias\_demo/results.json} and \texttt{README.md} (data seed 42; MAP-init torch seed 42; NUTS chain seeds 20260813 and 20260814). Single-mode geometry for this prior configuration: \texttt{runs/prior\_sensitivity/stage\_a\_toy\_elicited.json} records \texttt{coherent\_geometry} true, no separating valley, and one verified local maximum holding pooled prior-importance-sampling mass 1.0; local material that remains uncommitted in this repository. The D12 bimodality finding is scoped to the \texttt{informative} configuration and does not describe this one. The Case A evaluation of the same N=20 seed-42 instance is reported in section 3.4 of the assembled manuscript; no other Case A number is re-quoted here.}

The data come from \texttt{generate\_toy\_data()} at its defaults: N=20 points on
{[}-10, 10{]}, seed 42, observation noise 0.5, and y = sin(x) + 0.25x + noise. The
generator itself names the linear term the bias, so the demonstration inherits
a known true process and a known bias process instead of asserting either.\footnote{\evidencetier{empirical} \texttt{experiments/toy\_debias\_demo.py}; \texttt{runs/toy\_debias\_demo/results.json} and \texttt{README.md} (data seed 42; MAP-init torch seed 42; NUTS chain seeds 20260813 and 20260814). Single-mode geometry for this prior configuration: \texttt{runs/prior\_sensitivity/stage\_a\_toy\_elicited.json} records \texttt{coherent\_geometry} true, no separating valley, and one verified local maximum holding pooled prior-importance-sampling mass 1.0; local material that remains uncommitted in this repository. The D12 bimodality finding is scoped to the \texttt{informative} configuration and does not describe this one. The Case A evaluation of the same N=20 seed-42 instance is reported in section 3.4 of the assembled manuscript; no other Case A number is re-quoted here.}

The GP uses the SE plus linear additive kernel under the \texttt{toy\_elicited}
data-elicited prior, the configuration validated for this N=20 instance. That
prior sets its lognormal medians from this same sample's observable summaries,
an empirical-Bayes-style construction, so the posterior statements below are
conditional on that fixed prior rather than unqualified full Bayes.
Hyperparameters come from the corrected NUTS path in two seeded chains,
20260813 and 20260814, with 500 warmup and 500 retained draws each, target
acceptance 0.8 and maximum tree depth 8. Both chains initialize at the same MAP
point, so the rank-normalized R-hat reported here measures mixing within the
mode the optimizer selected and not agreement between dispersed starts. The
multi-basin geometry recorded for the \texttt{informative} configuration does not
carry over to this one: the wide-start mode hunt for \texttt{toy\_elicited}
verified a single local maximum holding the entire pooled
prior-importance-sampling mass with no separating valley, and its converged
point agrees with the MAP used here to within 2e-8 in every hyperparameter. The
shared start remains disclosed because a common initialization still leaves
R-hat silent about regions no chain visited. The run gives no divergences and
no tree-depth saturation, and across the four hyperparameters the
rank-normalized R-hat is at most 1.0025, bulk ESS at least 602.4, and tail ESS
at least 502.6.\footnote{\evidencetier{empirical} \texttt{experiments/toy\_debias\_demo.py}; \texttt{runs/toy\_debias\_demo/results.json} and \texttt{README.md} (data seed 42; MAP-init torch seed 42; NUTS chain seeds 20260813 and 20260814). Single-mode geometry for this prior configuration: \texttt{runs/prior\_sensitivity/stage\_a\_toy\_elicited.json} records \texttt{coherent\_geometry} true, no separating valley, and one verified local maximum holding pooled prior-importance-sampling mass 1.0; local material that remains uncommitted in this repository. The D12 bimodality finding is scoped to the \texttt{informative} configuration and does not describe this one. The Case A evaluation of the same N=20 seed-42 instance is reported in section 3.4 of the assembled manuscript; no other Case A number is re-quoted here.}

Every one of the 1,000 retained draws is decomposed by the package
additive-kernel machinery into an SE component, treated as the truth candidate,
and a linear component, treated as the bias candidate; all 1,000 decompositions
succeed.\footnote{\evidencetier{empirical} decomposition through \texttt{bistar\_gp.decompose.decompose\_additive\_gp}, the package implementation of the thesis Eq. 5 additive-kernel decomposition, with the joint posterior from \texttt{decompose\_component} on the summed kernel blocks so the inter-component cross-covariance is retained; success counts and the linear-component structure checks in \texttt{runs/toy\_debias\_demo/results.json}.} The debiased predictive of the true process consists of the
SE-component posterior with the linear component marginalized out. That
marginalization happens analytically within a draw, because the component
posterior the decomposition returns already forms the marginal of the joint
conditional Gaussian, and by Monte Carlo across draws for the hyperparameters.
Reported intervals are exact central intervals of the resulting draw mixture
rather than Gaussian approximations to it, and all bands are latent-function
bands with no observation noise added.\footnote{\evidencetier{empirical} \texttt{experiments/toy\_debias\_demo.py}; \texttt{runs/toy\_debias\_demo/results.json} and \texttt{README.md} (data seed 42; MAP-init torch seed 42; NUTS chain seeds 20260813 and 20260814). Single-mode geometry for this prior configuration: \texttt{runs/prior\_sensitivity/stage\_a\_toy\_elicited.json} records \texttt{coherent\_geometry} true, no separating valley, and one verified local maximum holding pooled prior-importance-sampling mass 1.0; local material that remains uncommitted in this repository. The D12 bimodality finding is scoped to the \texttt{informative} configuration and does not describe this one. The Case A evaluation of the same N=20 seed-42 instance is reported in section 3.4 of the assembled manuscript; no other Case A number is re-quoted here.}

\begin{figure}
\centering
\pandocbounded{\includegraphics[width=\linewidth]{figures/debias_figure.png}}
\caption{Composite fit, labeled components, and the debiased predictive against the known truth}
\end{figure}

\textbf{Figure 7.} Three readings of one posterior on the N=20 toy. Panel (a) shows
the composite posterior predictive against the observed data, which the
composite describes well. Panel (b) shows the two labeled components with their
95 percent central intervals against the generating sin(x) and 0.25x curves.
Panel (c) shows the debiased predictive against the known true process. The
three panels share a common y axis, so band widths are directly comparable
across them. The annotated slope, RMSE, coverage, and band-width readouts are
computed from the artifact values.

Turning to recovery, the bias-slope posterior has mean 0.197 with standard
deviation 0.072 and a 95 percent central interval of {[}0.033, 0.323{]}, which
contains the generating value 0.250. On a grid of 201 equally spaced points
inside the training span, the composite posterior mean differs from sin(x) by
an RMSE of 1.430 and the debiased posterior mean by 0.403, a reduction of 1.028
or 71.9 percent. Between-chain scatter in those two quantities is small: 1.431
and 1.430 for the composite arm, 0.403 and 0.402 for the debiased arm.\footnote{\evidencetier{empirical} \texttt{experiments/toy\_debias\_demo.py}; \texttt{runs/toy\_debias\_demo/results.json} and \texttt{README.md} (data seed 42; MAP-init torch seed 42; NUTS chain seeds 20260813 and 20260814). Single-mode geometry for this prior configuration: \texttt{runs/prior\_sensitivity/stage\_a\_toy\_elicited.json} records \texttt{coherent\_geometry} true, no separating valley, and one verified local maximum holding pooled prior-importance-sampling mass 1.0; local material that remains uncommitted in this repository. The D12 bimodality finding is scoped to the \texttt{informative} configuration and does not describe this one. The Case A evaluation of the same N=20 seed-42 instance is reported in section 3.4 of the assembled manuscript; no other Case A number is re-quoted here.}

The composite value of 1.430 has a plain reading that should be stated rather
than left to the reader. On the same grid the drift 0.25x has RMS 1.451, so the
composite arm's discrepancy with sin(x) essentially reproduces the displacement
it was fitted to include. The debias claim concerns how much of that known
displacement marginalization removes, and it removes most of it. What remains,
0.403, is not negligible against the true process's own RMS of 0.690.\footnote{\evidencetier{empirical} \texttt{experiments/toy\_debias\_demo.py}; \texttt{runs/toy\_debias\_demo/results.json} and \texttt{README.md} (data seed 42; MAP-init torch seed 42; NUTS chain seeds 20260813 and 20260814). Single-mode geometry for this prior configuration: \texttt{runs/prior\_sensitivity/stage\_a\_toy\_elicited.json} records \texttt{coherent\_geometry} true, no separating valley, and one verified local maximum holding pooled prior-importance-sampling mass 1.0; local material that remains uncommitted in this repository. The D12 bimodality finding is scoped to the \texttt{informative} configuration and does not describe this one. The Case A evaluation of the same N=20 seed-42 instance is reported in section 3.4 of the assembled manuscript; no other Case A number is re-quoted here.}

The debiased band covers sin(x) at 174 of the 201 grid points, 0.866 against a
nominal 0.95. Neighboring grid points share nearly the same posterior, so the
figure summarizes pointwise coverage rather than testing calibration over
independent trials; read that way it records mild undercoverage and not a
validated interval procedure. The coverage figure also inherits the
conditioning noted above, because the prior was elicited from the same sample
the band conditions on.\footnote{\evidencetier{empirical} \texttt{experiments/toy\_debias\_demo.py}; \texttt{runs/toy\_debias\_demo/results.json} and \texttt{README.md} (data seed 42; MAP-init torch seed 42; NUTS chain seeds 20260813 and 20260814). Single-mode geometry for this prior configuration: \texttt{runs/prior\_sensitivity/stage\_a\_toy\_elicited.json} records \texttt{coherent\_geometry} true, no separating valley, and one verified local maximum holding pooled prior-importance-sampling mass 1.0; local material that remains uncommitted in this repository. The D12 bimodality finding is scoped to the \texttt{informative} configuration and does not describe this one. The Case A evaluation of the same N=20 seed-42 instance is reported in section 3.4 of the assembled manuscript; no other Case A number is re-quoted here.}

\subsection{What the demonstration does and does not establish}

Two limits deserve statement.

First, identifying the linear component as bias is a modeling choice rather
than an inference. Construction licenses the choice here, because the generator
produced the drift. No generator supplies that warrant in an application, and
the analyst must justify the kernel labeling on substantive grounds before a
marginalization result means what its name suggests. The decomposition
machinery will split an additive posterior whichever way the labels are
assigned, and the split acquires interpretation only from the labeling
argument.

Second, the data determine the split far less sharply than they determine the
fit. The debiased band has mean width 1.836 on the grid while the composite
band has mean width 1.032 and the linear component's 1.458, so the observations
constrain the sum more tightly than either component alone. The mean total
variances behind those bands, 0.2368 for the SE component, 0.1752 for the
linear component, and 0.0667 for the composite, imply a posterior
cross-covariance between the two components near \ensuremath{-}0.173 and a grid-averaged
correlation near \ensuremath{-}0.85: at this sample size the data pin the sum far better
than the split. Whether that gap persists as N grows is the substantive form of
the expectation recorded in section 8.5, and this demonstration, run at a
single sample size, does not test it.\footnote{\evidencetier{empirical} \texttt{experiments/toy\_debias\_demo.py}; \texttt{runs/toy\_debias\_demo/results.json} and \texttt{README.md} (data seed 42; MAP-init torch seed 42; NUTS chain seeds 20260813 and 20260814). Single-mode geometry for this prior configuration: \texttt{runs/prior\_sensitivity/stage\_a\_toy\_elicited.json} records \texttt{coherent\_geometry} true, no separating valley, and one verified local maximum holding pooled prior-importance-sampling mass 1.0; local material that remains uncommitted in this repository. The D12 bimodality finding is scoped to the \texttt{informative} configuration and does not describe this one. The Case A evaluation of the same N=20 seed-42 instance is reported in section 3.4 of the assembled manuscript; no other Case A number is re-quoted here.}

The full development belongs to the companion line. The program originates in
thesis chapter 5, and the real-data study proceeds under its own
preregistration; no real-data result is reported or forecast here.\footnote{\evidencetier{thesis} Chandramouli (2020), doctoral dissertation, Indiana University; Chapter 5 instantiates BI* with Gaussian Processes and states the debiasing program. \evidencetier{framework} Chandramouli and Shiffrin (2016), ``Extending Bayesian induction,'' \emph{Journal of Mathematical Psychology}, 72, 38--42.}

---------- 08-discussion.tex ----------
%% Generated from docs/paper-sie-jmp/08-discussion.md
%% Source branch: paper/synthesis-sections
%% Do not hand-edit; see docs/paper-sie-jmp/build_tex.py
\section{Discussion}

\subsection{The three evaluation dials, revisited}

The cases replace a single model-probability answer with an auditable set of
evaluative choices. Temperature controls how strongly small divergences
dominate. The \texttt{occam} flag controls whether \(Z_M\) integrates total compatible
volume or normalizes by \(V_{\mathrm{ref}}\). Aggregation controls whether
data-pattern draws contribute according to their absolute support or spend
equal total credit after within-draw normalization. Each choice changes the
question being answered, so sensitivity analysis cannot substitute for naming
the convention.\footnote{\evidencetier{empirical} assembled-manuscript sections 3--6 and their case artifacts: \texttt{runs/vanbork\_external\_validation/}, \texttt{runs/e7\_convention\_sensitivity/}, \texttt{runs/occam\_dial/}, \texttt{runs/haaf\_nested\_constraint/}, and \texttt{runs/regret\_curves\_mopen/}; Notes/DECISIONS.md D60--D64.}

Case A prices aggregation most directly. Expected-posterior aggregation obtains
external correspondence with van Bork, Romeijn, and Wagenmakers, while pooled
aggregation retains absolute divergence magnitudes needed for an M-open reading
yet does not reproduce their non-overlapping target, and naming aggregation as a
dial states that price instead of concealing it. The same case gives the hybrid
\(Z_M\) construction a passing shared-family special-case test. Case B then
shows how \(\tau\) and \texttt{occam} interact in nested comparisons: low temperature
emphasizes best achievable divergence, while reference-volume normalization can
permit a finite-temperature simplicity preference. Case C shows that changing
\(\tau\) or the table-path aggregation cannot reverse containment. Case D adds
the scale qualification: temperature has meaning only relative to the scale of
\(G\), so comparisons across metrics require tau-free draw-win fractions
alongside soft probabilities.\footnote{\evidencetier{empirical} assembled-manuscript sections 3--6 and their case artifacts: \texttt{runs/vanbork\_external\_validation/}, \texttt{runs/e7\_convention\_sensitivity/}, \texttt{runs/occam\_dial/}, \texttt{runs/haaf\_nested\_constraint/}, and \texttt{runs/regret\_curves\_mopen/}; Notes/DECISIONS.md D60--D64.}

The bridge from Case B to Case C resolves an apparent tension. Case C shows
that neither the table path nor LOO credits a satisfied constraint in its
head-to-head example. For the table path, candidate-region containment fixes
the direction per draw; for LOO, the artifact's local diagnostic places
negligible mass in the excluded region and the comparison remains
inconclusive. Case B identifies the machinery that can credit the restriction:
the volume or reference-measure term on the \(Z_M\) side. A Bayes-factor-style
prior-mass reward corresponds to the \(V_{\mathrm{ref}}\)-normalization choice,
not to best-instance table-path aggregation. Making \texttt{occam} explicit keeps that
reward available without quietly attributing it to predictive fit.\footnote{\evidencetier{empirical} assembled-manuscript sections 4 and 5 on \texttt{paper/case-b-occam-dial} and \texttt{paper/case-c-haaf}; \texttt{runs/occam\_dial/e6\_results.json}; \texttt{runs/haaf\_nested\_constraint/results.json}; Notes/DECISIONS.md D62 and D63.}

\subsection{Calibrating the M-open signal}

Absolute divergence offers information that a relative ranking discards, but
its interpretation needs calibration. A high best-candidate \(G\) can reflect
misspecification, ordinary sampling variation, the GP scaffold, or the metric's
scale. A defensible inadequacy claim therefore requires a reference distribution
under known correct specification, conditional on the metric, data-prior
configuration, design, and noise regime.

Formal M-open calibration remains open. Case D contributes the first
correct-specification reference material for this program: known-truth
distributions of mean \(G\) under a synthetic design in which the generating
family appears among the candidates. Those distributions reveal overlap and
asymmetric distinguishability that a winner label would hide. They do not set
a rejection threshold, validate a universal scale, or establish an M-open
finding for observed data.\footnote{\evidencetier{empirical} assembled-manuscript section 6 on \texttt{paper/case-d-mopen}; \texttt{experiments/regret\_curves\_mopen.py}; \texttt{runs/regret\_curves\_mopen/results.json}; Notes/DECISIONS.md D64.}

\subsection{Relation to elpd and PSIS-LOO}

The relation to elpd and PSIS-LOO concerns shared operations rather than an
identity of inferential targets. Both traditions use pointwise predictive
evaluation and can use importance weighting over posterior draws. PSIS-LOO
fits each candidate with its own parameter prior and estimates held-out
predictive accuracy: reweighting its posterior draws by the importance ratios
approximates each leave-one-out predictive quantity, a generalized Pareto fit to
the largest of those ratios stabilizes them, and the fitted shape estimate flags
cases where the approximation becomes unreliable. BMS*-GP instead
evaluates all candidates against shared data patterns \(\psi\), uses
\texttt{pw\_kl\_vcal} as the primary divergence, and reserves within-model priors for an
explicit hybrid extension. Its target concerns proximity to a common
data-space posterior, not leave-one-out prediction.\footnote{\evidencetier{peer-reviewed} Vehtari, Gelman, and Gabry (2017), ``Practical Bayesian model evaluation using leave-one-out cross-validation and WAIC,'' \emph{Statistics and Computing}, 27(5), 1413--1432. Argument provenance: \texttt{kb/Wiki/Vehtari-Gelman-Gabry\ Connection.md}.}

Case C sharpens the distinction through a head-to-head comparison on identical
data. PSIS-LOO returns a null-to-inconclusive difference for the satisfied
constraint, consistent with the failure mode identified by Haaf, Klaassen, and
Rouder. The BMS* table path also returns an effective tie, but for a different
structural reason: the encompassing region contains every restricted optimum
and can never have larger best-instance divergence. The shared outcome does not
make the methods interchangeable. It locates the missing restriction reward in
both comparisons and directs any such reward to an explicit prior-volume
choice.\footnote{\evidencetier{empirical} \texttt{experiments/haaf\_nested\_constraint.py}; \texttt{runs/haaf\_nested\_constraint/results.json} and \texttt{README.md}; Notes/DECISIONS.md D63. \evidencetier{peer-reviewed} Haaf, Klaassen, and Rouder (2025), ``Bayes factor vs.~posterior predictive model assessment: Insights from ordinal constraints,'' \emph{Computational Brain \& Behavior}.}

\subsection{Open questions}

Several extensions now have sharper starting points.

\begin{itemize}
\item
  \textbf{Hybrid \(Z_M\).} Case A, section 3, upgrades the hybrid from a proposal to
  a construction with a passing Target B special-case test. Work remains on
  general candidate families, on prior knowledge independent of the analyzed
  data, and on the relation between within-model density and the \texttt{occam}
  reference measure.\footnote{\evidencetier{empirical} assembled-manuscript section 3 on \texttt{paper/case-a-vanbork}; \texttt{experiments/vanbork\_external\_validation.py}; \texttt{runs/vanbork\_external\_validation/results.json}; Notes/DECISIONS.md D60 Resolution and Precision addenda.}
\item
  \textbf{Learning \(\tau\).} The present work treats temperature as a sweep.
  Calibration across tasks with known truth could replace a conventional value
  with a design- and metric-specific learning rule.
\item
  \textbf{Decision-theoretic \(G\).} Scientific losses differ across applications.
  A utility-weighted divergence could state which predictive discrepancies
  matter, while preserving the shared data-prior scaffold.
\item
  \textbf{Non-stationary kernels.} Case D leaves scaffold representability and
  intrinsic mimicry unidentified. Kernels with location-dependent smoothness
  could address the first mechanism, but they cannot manufacture information
  when candidate families genuinely mimic one another.
\item
  \textbf{Aggregation semantics.} D60 resolves the reporting convention, not the
  substantive choice for every application. Pooled aggregation remains
  canonical; expected-posterior aggregation remains necessary when Eq. 4
  correspondence matters. A future decision rule should connect that choice to
  whether absolute inadequacy or equal per-pattern credit answers the scientific
  question.
\end{itemize}

\subsection{Costs and scope conditions}

The method moves judgment into the data prior, kernel, metric, temperature,
reference measure, and aggregation rule. These choices become visible and
testable, but they still require substantive knowledge. When beliefs about a
bias process come largely from outside the observed data, additional sample
size need not remove the associated uncertainty, and honest inference can retain
an uncertainty floor. That expectation belongs to the program rather than to
any of the four cases reported here, and section 7 of the assembled manuscript
carries the debiasing development that would make it
concrete.\footnote{\evidencetier{empirical} forward reference to assembled-manuscript section 7, drafted at \texttt{docs/paper-sie-jmp/07-debias-bridge.md}, local material that remains uncommitted in this repository and supplies no reported number; none of the four cases reported here estimates an uncertainty floor.}

Two scope conditions follow from Case D. Under F1, the GP scaffold may fail to
represent the feature that distinguishes the candidates, so comparison reflects
the scaffold's resolution as well as the candidate theories. Under F2, the
candidate families may mimic one another over the informative design region,
so no scoring rule can recover information that the data do not contain. The
synthetic case could not identify which mechanism produced its asymmetry, and
its deviation curves covered only part of the region used by the stored
aggregate scores. BMS*-GP should therefore report scaffold checks, local
deviation diagnostics, and the possibility that a weak separation remains
unresolved across all four sources Case D leaves open, namely F1
representability, F2 mimicry, metric behavior, and sampling noise, rather than
treating every weak separation as a demand for a sharper
posterior.\footnote{\evidencetier{empirical} assembled-manuscript section 6; \texttt{experiments/regret\_curves\_mopen.py}; \texttt{runs/regret\_curves\_mopen/}; Notes/DECISIONS.md D64.}

\subsection{Verification and reproducibility}

Every reported number has a named regenerating \texttt{experiments/} script and a
corresponding \texttt{runs/} artifact; D65 records the provenance exception for the
D17-recorded local methods-validation reach check. Each case section underwent
independent review within a four-model adversarial cross-verification protocol.
All four reviewer rounds are recorded for every case, with the fourth, Kimi K3,
run at the author's direction on the same round-1 packages. The findings,
refutations, fixes, and author sign-off records are committed under
\texttt{runs/\textless{}case\textgreater{}/reviews/} in this repository, and the corresponding
\texttt{Notes/DECISIONS.md} entry records the review outcome.\footnote{\evidencetier{empirical} case review archives under \texttt{runs/vanbork\_external\_validation/reviews/}, \texttt{runs/occam\_dial/reviews/}, \texttt{runs/haaf\_nested\_constraint/reviews/}, and \texttt{runs/regret\_curves\_mopen/reviews/}; corresponding review outcomes in Notes/DECISIONS.md D62--D65.}

---------- A-notation.tex ----------
\section{Notation}

\begin{longtable}[]{@{}
  >{\raggedright\arraybackslash}p{(\linewidth - 2\tabcolsep) * \real{0.5000}}
  >{\raggedright\arraybackslash}p{(\linewidth - 2\tabcolsep) * \real{0.5000}}@{}}
\toprule\noalign{}
\begin{minipage}[b]{\linewidth}\raggedright
Symbol
\end{minipage} & \begin{minipage}[b]{\linewidth}\raggedright
Meaning
\end{minipage} \\
\midrule\noalign{}
\endhead
\bottomrule\noalign{}
\endlastfoot
\ensuremath{\psi} (psi) & one data pattern: a probability distribution over outcomes at the evaluation points; one BI* table row. In the GP implementation, a sampled function f with observation variance defines \ensuremath{\psi} = N(f(x), \ensuremath{\sigma}\ensuremath{^{2}}\_\ensuremath{\psi} I) \\
p\ensuremath{_{0}}(\ensuremath{\psi}) & the data prior: the distribution over data patterns induced by the GP hyperpriors (sample hyperparameters, then a function) \\
\ensuremath{\ell}, \ensuremath{\sigma}\ensuremath{^{2}}\_SE, \ensuremath{\sigma}\ensuremath{^{2}}\_b, \ensuremath{\sigma}\ensuremath{^{2}}\_y & kernel hyperparameters: SE lengthscale, SE variance, linear-kernel variance, observation-noise variance \\
G(\ensuremath{\psi}, \ensuremath{\theta}) & divergence between one data pattern and one candidate predictive; per-draw, UNAVERAGED \\
\ensuremath{\bar{G}}(\ensuremath{\phi}) & G averaged across data patterns, as a function of candidate parameters \ensuremath{\phi}; the object inside Z\_M \\
pw\_kl\_vcal & primary metric (W1): variance-calibrated pointwise KL, equal to GP-uncertainty-weighted MSE \\
kl\_forward & appendix-only stress metric (W1): full joint KL, covariance-sensitive \\
\ensuremath{\tau} (tau) & Boltzmann temperature of soft transfer; \ensuremath{\tau}\ensuremath{\rightarrow}0 recovers hard best-match partitioning; always reported as a sweep \\
soft transfer & p(\ensuremath{\theta} \textbackslash{} \\
Z\_M & induced model prior: \ensuremath{\int} exp(\ensuremath{-}\ensuremath{\bar{G}}(\ensuremath{\phi})/\ensuremath{\tau}) d\ensuremath{\phi} (occam=False) or the V\_ref-normalized variant (occam=True) \\
occam & the reference-measure flag on Z\_M: False = raw Lebesgue (canonical, faithful to original BI*), True = normalize by V\_ref \\
M\_r \ensuremath{\subset} M\_e & restricted model nested in encompassing model (van Bork et al.'s notation, adopted for Cases A/B/C) \\
SIR / prior-IS / NUTS & estimator names; toy\_elicited SIR 0.441 and corrected NUTS \ensuremath{\approx} 0.42 reported as separate-but-agreeing (M2bR banner) \\
\end{longtable}

---------- B-provenance.tex ----------
\section{Computational provenance}

Every number reported in this manuscript regenerates from a named script in the source repository into a committed run artifact. The sections and their sources follow.

\begin{description}
\item[1. Introduction] Provenance: no empirical estimate is re-quoted in this section. Case-result summaries draw on \texttt{runs/vanbork\_external\_validation/} and \texttt{runs/e7\_convention\_sensitivity/} $\cdot$ \texttt{experiments/vanbork\_external\_validation.py} and \texttt{experiments/e7\_convention\_sensitivity.py} $\cdot$ Notes/DECISIONS.md D60, D61; \texttt{runs/occam\_dial/} $\cdot$ \texttt{experiments/occam\_dial\_figure.py} and \texttt{experiments/e6\_nesting\_monotonicity.py} $\cdot$ D62; \texttt{runs/haaf\_nested\_constraint/} $\cdot$ \texttt{experiments/haaf\_nested\_constraint.py} $\cdot$ D63; \texttt{runs/regret\_curves\_mopen/} $\cdot$ \texttt{experiments/regret\_curves\_mopen.py} $\cdot$ D64. Argument provenance: \texttt{kb/Wiki/BI-star Framework.md}, \texttt{kb/Wiki/Data Priors Citation Landscape.md}, and \texttt{kb/Wiki/Paper Writing Guide.md}.
\item[2. Machinery] Provenance: no empirical estimate is re-quoted in this section. Construction, projection, and the averaged-pattern evaluation of \(\bar G\): \texttt{bistar\_gp/config.py}, \texttt{bistar\_gp/metrics\_v2.py}, \texttt{bistar\_gp/aggregation\_v3.py}, and \texttt{bistar\_gp/laplace\_evidence.py} $\cdot$ the prior-only mechanism arm of \texttt{experiments/mechanism\_figure\_poster.py}, cited as uncommitted local methods material for construction visualization only. Aggregation: \texttt{runs/vanbork\_external\_validation/} and \texttt{runs/e7\_convention\_sensitivity/} $\cdot$ \texttt{experiments/vanbork\_external\_validation.py} and \texttt{experiments/e7\_convention\_sensitivity.py} $\cdot$ D60, D61. Nesting and metric scale: \texttt{runs/occam\_dial/}, \texttt{runs/haaf\_nested\_constraint/}, and \texttt{runs/regret\_curves\_mopen/} $\cdot$ \texttt{experiments/e6\_nesting\_monotonicity.py}, \texttt{experiments/haaf\_nested\_constraint.py}, and \texttt{experiments/regret\_curves\_mopen.py} $\cdot$ D62, D63, D64.
\item[3. Case A: external validation against van Bork, Romeijn, and Wagenmakers] Provenance: \texttt{runs/vanbork\_external\_validation/} $\cdot$ \texttt{experiments/vanbork\_external\_validation.py} $\cdot$ Notes/DECISIONS.md D60; \texttt{runs/e7\_convention\_sensitivity/} $\cdot$ \texttt{experiments/e7\_convention\_sensitivity.py} $\cdot$ Notes/DECISIONS.md D61. The W4 reach check follows the D17-recorded citation path stated in [^4]. Argument provenance: \texttt{kb/Raw/papers/important/vanBork\_Romeijn\_Wagenmakers\_2025\_subset\_problem.md} and \texttt{kb/Wiki/Subset Problem and the Data Prior.md}.
\item[4. Case B: the occam flag as the Popper/Wrinch-Jeffreys dial] Provenance: \texttt{runs/occam\_dial/} $\cdot$ \texttt{experiments/occam\_dial\_figure.py} $\cdot$ \texttt{experiments/e6\_nesting\_monotonicity.py} $\cdot$ \texttt{Notes/DECISIONS.md} D17, D62.
\item[5. Case C: a satisfied nested constraint under BMS* and LOO] Provenance: \texttt{runs/haaf\_nested\_constraint/} $\cdot$ \texttt{experiments/haaf\_nested\_constraint.py} $\cdot$ Notes/DECISIONS.md D63.
\item[6. Case D: M-open calibration through a warranted decline [DRAFT]] Provenance: \texttt{runs/regret\_curves\_mopen/} $\cdot$ \texttt{experiments/regret\_curves\_mopen.py} $\cdot$ D64.
\item[7. From evaluation to debiasing] Provenance: \texttt{runs/toy\_debias\_demo/} $\cdot$ \texttt{experiments/toy\_debias\_demo.py} $\cdot$ \texttt{Notes/DECISIONS.md} D67.
\item[8. Discussion] Provenance: no empirical estimate is re-quoted in this section. Cases A–D: \texttt{runs/vanbork\_external\_validation/}, \texttt{runs/e7\_convention\_sensitivity/}, \texttt{runs/occam\_dial/}, \texttt{runs/haaf\_nested\_constraint/}, and \texttt{runs/regret\_curves\_mopen/} $\cdot$ \texttt{experiments/vanbork\_external\_validation.py}, \texttt{experiments/e7\_convention\_sensitivity.py}, \texttt{experiments/occam\_dial\_figure.py}, \texttt{experiments/e6\_nesting\_monotonicity.py}, \texttt{experiments/haaf\_nested\_constraint.py}, and \texttt{experiments/regret\_curves\_mopen.py} $\cdot$ Notes/DECISIONS.md D60–D65. Argument provenance: \texttt{kb/Wiki/Vehtari-Gelman-Gabry Connection.md}, \texttt{kb/Wiki/Limits Diagnostics and Open Questions.md}, and \texttt{CogSci Poster/OPEN\_QUESTIONS.md}.
\end{description}

==================== DECISION LOG ENTRIES D59+ (collected across branches; D1-D58 are on main) ====================

--- D60 (from origin/paper/case-a-vanbork) ---
## D60: External validation against van Bork, Romeijn & Wagenmakers (2025) — two published closed-form targets reproduced; the aggregation convention is adjudicated, and the M-open signal is in tension with it — 2026-08-11

**Problem:** Every demonstration of the induced-prior / soft-transfer machinery
to date is self-validating: we generate data from a known process and check that
the framework recovers it. That establishes internal consistency, not external
correctness. The full-text ingest of van Bork, Romeijn & Wagenmakers (2025,
*Synthese*, doi:10.1007/s11229-025-05286-y) surfaced two model probabilities the
authors derive in closed form from Rosenkrantz-style expected support against a
"data prior" — independent ground truth, computed with no reference to this
implementation.

**Decision:** New driver `experiments/vanbork_external_validation.py`
(local, seconds, no HMC and no GP: the paper supplies the data prior directly,
so only the scoring half is under test). Outputs to
`runs/vanbork_external_validation/{results.json, README.md}`.

**Result — both targets reproduced.**

*Target B (completely overlapping models, their beta example):* data prior a
point mass at s/n = 1/2; M_x: theta ~ beta(50,50) vs M_z: theta ~ beta(2,2).
Paper's answer 7.96/(7.96+1.50) = 0.841420. Ours converges to **0.841419** by
tau = 1e-7 (abs err 6.4e-7); our densities at the MLE (7.9589, 1.5000) match
their quoted 7.96/1.50. This required the HYBRID form
Z_M = ∫ p_M(theta) exp(-G(theta)/tau) d theta, i.e. a within-model parameter
prior in place of the Lebesgue/V_ref reference measure — the hybrid listed as an
OPEN question. Analytic account: Laplace gives Z_M ≈ p_M(theta*)·sqrt(2 pi tau /
G''(theta*)); both models share the Bernoulli family, so G'' cancels and the
normalized ratio converges to the ratio of prior densities at theta*. **Their
published formula is therefore the tau→0, shared-family, point-data-prior
special case of Z_M.** The hybrid open question now has a passing test.

*Target A (non-overlapping point models):* data prior 0.4 on s/n→0.16, 0.6 on
s/n→0.19; models theta=0.15 vs theta=0.20; paper's answer 0.4/0.6. Three
aggregation variants at tau→0:
- pooled (**shipped default, `normalize_per_draw=False`**): → **0.000/1.000, FAILS**
- per-atom renormalization then average (paper Eq. 4): → 0.400/0.600, exact
- shipped `soft_transfer(..., normalize_per_draw=True)`: → 0.400/0.600, exact

**Adjudication and the tension it exposes (OPEN — author call required):** the
paper defines the prior model probability as the *expected posterior* across the
data prior (their Eq. 4), which mandates normalizing each data-prior atom into a
posterior over models before averaging. Under that reading the canonical default
is wrong and `normalize_per_draw=True` is correct. But the two conventions serve
different goals and the choice is not free:
- **Per-draw** matches the expected-posterior derivation, but destroys absolute
  divergence magnitudes — every draw must spend one full unit of credit, so a
  draw that no candidate fits votes exactly as forcefully as one that all
  candidates fit.
- **Pooled** preserves absolute magnitudes, which is precisely what carries the
  **M-open inadequacy signal** (uniformly high divergence ⇒ no candidate is
  adequate) that D-series work and the poster both claim as a distinguishing
  feature.
So the framework cannot simultaneously have the paper's expected-posterior
semantics and the M-open magnitude signal from a single aggregation. This is a
substantive modeling fork, not a bug, and it is recorded here unresolved.

**Scope note:** no poster figure is invalidated by this entry. All toy and Mauna
runs use equal-weight GP draws, where the two conventions differ far less than
in Target A's unequal-mass two-atom construction, and no claim on the poster
depends on the unequal-mass case. Whether the toy/Mauna posteriors move
materially under `normalize_per_draw=True` is UNTESTED — that check (E7) should
precede any published claim that the framework reproduces the paper's targets.

**Alternatives considered:** (a) validate against the paper's coin example using
the GP scaffold — rejected, the example is binomial with a given data prior, so
the scaffold has nothing to construct; (b) declare the default convention wrong
and switch it — rejected, the M-open tension above makes this an author-level
modeling decision, not a fix.

**Resolution (2026-08-12, author):** the aggregation convention is adopted as
an explicit evaluation dial alongside tau and occam (the E7 README's candidate
stance, ratified). Canonical reporting keeps pooled aggregation: absolute
divergence magnitudes, the M-open signal, and continuity with all ratified
numbers are preserved, and the shipped normalize_per_draw=False default is
unchanged. The expected-posterior (Eq. 4) variant is reported alongside wherever
external correspondence matters; paper Case A reports both, and its section 3
replaces the fork placeholder with this statement. The kl_forward aggregation
attribution stays appendix-only (W1). Neither convention is declared universally
correct. This closes the fork left OPEN above; the adjudication paragraph stands
as written for the record.

**Precision addendum (2026-08-12, author-approved via the Case A review):** two
clarifications recorded without altering the body above. (1) The Target A
table's row (c) reports the shipped `soft_transfer(..., normalize_per_draw=
True)` semantics: per-draw minimum shift with a single post-pooling
normalization. That computation differs from row (b)'s per-atom
renormalization at finite tau and coincides with it in the tau-to-zero
unique-winner limit the table reports, which is why both rows read
0.400/0.600. (2) "0.841420" above denotes the authors' closed form evaluated
at double precision; the paper prints 7.96, 1.50, and approximately 0.84
(printed-density quotient 0.841438).

--- D61 (from origin/paper/case-a-vanbork) ---
## D61: E7 aggregation-convention sensitivity on the validated toy path — winner robust; kl_forward fragility attributed to pooled aggregation — 2026-08-11

**Problem:** D60's external validation showed the shipped pooled soft-transfer
convention fails van Bork et al.'s Target A while per-draw conventions
reproduce it, exposing a fork (expected-posterior semantics vs M-open
magnitudes). Before the JMP special-issue paper can cite either, the movement
of the paper-facing toy numbers under the conventions had to be measured on the
VALIDATED estimator path (M2bR banner: `toy_elicited` SIR; no withdrawn HMC).

**Decision:** New driver `experiments/e7_convention_sensitivity.py`: reuses
`prior_sensitivity_study.py`'s stage-IS machinery verbatim (pooled 3-seed
prior-IS, SIR n_pred=1000, same seeds/subsample conventions), computes G for
pw_kl_vcal (W1 primary) and kl_forward (W1 appendix), aggregates under (a)
pooled/shipped default, (b) shipped normalize_per_draw=True (row-min), (c)
expected-posterior (van Bork Eq. 4). Output
`runs/e7_convention_sensitivity/{results.json, README.md}`. Anchor check: the
pooled pw_kl_vcal tau=1 row reproduces the ratified SIR headline exactly
(0.183/0.192/0.441/0.184).

**Result:** (1) pw_kl_vcal: Sin+Linear wins under every variant at every tau;
max movement 0.313 at tau=0.1, 0.072 at tau=1 (0.441 to 0.513), 0.001 at
tau=10 — qualitative claims convention-robust. (2) NEW ATTRIBUTION: the
kl_forward fragility recorded in W1/D18 is largely pooled-aggregation outlier
sensitivity, not intrinsic to the metric: pooled collapses Sin+Linear to
~0.000 at tau<=1 while expected-posterior yields 0.696 at tau=0.1, exactly the
raw hard-best-match fraction (696/1000) — the tau->0 identity between
expected-posterior aggregation and hard-win rates holds by construction and
passed numerically. (3) Fork (OPEN, author): pooled keeps M-open magnitudes
and continuity with all ratified numbers but fails van Bork Target A;
expected-posterior matches their Eq.-4 semantics and rescues kl_forward but
spends exactly one unit of credit per draw. Candidate paper stance recorded in
the run README: treat the aggregation convention as an explicit evaluation
dial alongside tau and occam.

**Status:** E7 CLOSED as an experiment; D60 fork remains OPEN pending author
call. Paper Case A blocked only on that call.

**Status update (2026-08-12):** the D60 fork is RESOLVED (see the D60 Resolution
addendum: aggregation adopted as an explicit evaluation dial; pooled canonical);
Case A is unblocked and its placeholder is replaced.

--- D65 (from origin/paper/case-a-vanbork) ---
## D65: Case A external-validation section with the aggregation fork preserved — 2026-08-12

**Problem:** The Case A manuscript stub needed a self-contained external
validation argument from the finalized D60 and D61 artifacts: an honest mapping
to van Bork, Romeijn, and Wagenmakers; the six-decimal completely-overlapping
target and its Laplace explanation; the non-overlapping target's dependence on
aggregation; the validated toy-path sensitivity; the appendix-only
`kl_forward` attribution; and a multi-parameter reach paragraph. The author has
not yet selected a canonical aggregation convention, and the writing task did
not authorize new compute or artifact regeneration.

**Decision:** Replaced the stub in
`docs/paper-sie-jmp/03-case-A-external-validation.md` with a mapping table and
the full Case A account. Numerical claims use
`runs/vanbork_external_validation/{results.json,README.md}` and
`runs/e7_convention_sensitivity/{results.json,README.md}`, generated by
`experiments/vanbork_external_validation.py` and
`experiments/e7_convention_sensitivity.py`. The section keeps the author-decision
placeholder on a standalone line at the canonical-convention slot. Surrounding
prose states both sides of the fork and labels the E7
evaluation-dial framing as a candidate rather than a decision. It treats
`pw_kl_vcal` as primary and confines `kl_forward` to an appendix attribution.

The multi-parameter paragraph follows W4: it labels
`runs/viz_unification/p3_priors_canonical/` as an
`informative`-configuration, MAP-based methods-validation check. Because that
directory remains local and untracked, its 0.992 Sin+Linear value at \(n=50\)
and values at or above 0.93 across evaluated \(n\) use the committed
D17-recorded citation pattern and name the regenerating `bistar_viz` scripts
explicitly. They do not enter the validated `toy_elicited` SIR headline.

**Alternatives considered:** Selecting pooled aggregation was rejected because
it would preempt the author and would leave Target A unresolved. Selecting
expected-posterior aggregation was rejected because it would also preempt the
author and would discard the absolute divergence magnitudes used for the
M-open signal. Treating the untracked viz-unification directory as committed
numerical authority was rejected in favor of the authorized D17-recorded
provenance exception. New computation, rerunning either finalized experiment,
and modifying scripts or run artifacts were all rejected by the Case A work
order.

**Result:** The section reports Target B's progression from 0.792607 to
0.841419 against their closed form evaluated at double precision (0.841420 to
six decimals), with absolute error against that evaluated limit
\(6.4\times10^{-7}\), and connects the agreement to cancellation of shared
Bernoulli curvature in the hybrid Laplace approximation. It reports Target A
as 0.000/1.000 under pooled aggregation versus the exact 0.400/0.600 under both
per-draw routes, with convergence by \(\tau=10^{-4}\). On the validated
`toy_elicited` SIR path, it records the 0.183/0.192/0.441/0.184 pooled anchor,
the 0.31, 0.072, and 0.001 maximum movements, and the appendix-only
`kl_forward` change from approximately 0.000 under pooled aggregation to 0.696
under expected-posterior aggregation, equal to 696/1000 hard wins at the
reported precision. This branch commits D60 and D61, which record the finalized
compute provenance, together with D65. No experiment or artifact-generation
command ran during the original section-drafting pass. The review fix pass ran
the single authorized E7 verification; its regenerated JSON differed only in
the generated-date field, and the saved artifact was restored afterward.

**Review outcome (2026-08-12):** §4 four-model protocol complete (Codex gpt-5.6-sol xhigh REVISE-6; Opus 5 fresh-agent REVISE-11; Gemini 3.1 Pro package-only REVISE-1; Kimi K3 author-run pending) — 15 collated findings; F-A1 (consistency-check attribution; 3 reporters) and F-A2 (rowmin/Eq.-4 distinction; 2 reporters) plus 7 confirmed singles fixed in 7b653cf; AC1/AC3/AC4/AC6/AO4/AO5 REFUTED in adversarial cross-checks and logged, the checks endorsing the author-record policy (D60/D61 byte-untouched; proposed D60 addendum on the author ledger); three hunk-introduced S4 cosmetics fixed by bounded micro-fix with driver mechanical verification (no third round per rule 4); [FORK-DECISION-PLACEHOLDER] intact throughout; full record runs/vanbork_external_validation/reviews/VERDICTS.md; author adjudications open: the D60 fork itself, the D60 addendum proposal, author-record policy ratification, Kimi round.

**Author-directed addition (2026-08-12, post-sign-off):** the section gains an explicit claim/counterclaim framing (their expected-support construction subsumed as the zero-temperature hybrid-Z_M special case; the counterclaim that Eq.-4 per-draw semantics forecloses the M-open magnitude signal, priced by the aggregation dial); no numbers added.

**Author-directed addition (2026-08-12, post-sign-off): figure.** experiments/vanbork_figure.py renders runs/vanbork_external_validation/target_figure.png from results.json (plotted-equals-artifact asserted; no recomputation); embedded in section 3.3.

--- D62 (from origin/paper/case-b-occam-dial) ---
## D62: Case B Occam dial and E6 nesting check — 2026-08-11

**Problem:** Case B needed a regenerable E4 figure that separated the D17
estimator and `occam` changes, plus an E6 numerical check of the claim that an
encompassing model cannot have a worse best achievable divergence than either
of its exact restrictions. The local untracked `runs/viz_unification/` directory
contains figures, logs, `delta_table.md`, `ess_by_stage.md` diagnostics, and
extracted legacy scripts, so it cannot serve as the authoritative committed data
source and the figure arms must be recomputed. When `delta_table.md` is present,
the figure script parses it and enforces a 0.003 same-seed cross-check gate. The
canonical visualization box also starts the sinusoid amplitude at 0.01, while
exact Linear nesting requires A=0.

**Decision:** Added `experiments/occam_dial_figure.py` and
`experiments/e6_nesting_monotonicity.py`, both writing to
`runs/occam_dial/`. Both scripts build the `informative`-configuration,
MAP-based averaged GP through `bistar_viz/scripts/_viz_spaces.py` at n=50,
with data seed 42, 80 evaluation points, and primary metric `pw_kl_vcal`.
The figure runs the p1 pure-Laplace `occam=True`, p2 IS `occam=True`, and p3 IS
`occam=False` arms at τ=0.3, IS seed 0, `n_is=40000`, and five seeded
perturbations per start. Its 0.003 absolute-probability anchor tolerance provides
a same-seed reproduction gate for three-decimal source anchors, not an accuracy
claim. The p1 arm calls `laplace_log_Z_Mx` directly to retain each model's
`n_clipped` and `converged` diagnostics and asserts that those direct log Z_M
values match the arm values. E6 calls
`_multistart_G_optima`, `compute_G_at_params`, and `is_log_Z_Mx` from
`bistar_gp/laplace_evidence.py`; it does not reimplement Ḡ. E6 extends
only the encompassing amplitude boundary to A=0, seeds its optimizer with
the exact restricted optima, and uses seeds 0, 1, and 2 with `n_is=100000` per
seed over 161 log-spaced temperatures. One IS call per model per seed supplies
the raw sweep, and the package reference-volume helper supplies the
`occam=True` sweep. Given the exact embeddings and mean-only divergence, each
min-Ḡ inequality follows analytically from box containment; the retained check
confirms the implementation reproduces that consequence and quantifies the
margins. The min-Ḡ tolerance equals 10^-8, with a 10^-10 exact-embedding check.

**Alternatives considered:** Reading `delta_table.md` or the local logs as the
figure data source was rejected because those artifacts remain local and
untracked; the table provides only the machine-dependent 0.003 same-seed
cross-check when present. Comparing p1 directly with p3 as a pure `occam`
ablation was rejected because the arms also
change the Z_M estimator; p2 isolates the estimator step. Retaining the
0.01 amplitude cutoff for E6 was rejected because it excludes the stated
A=0 restriction. Reimplementing the divergence or optimizer was rejected
in favor of the package machinery required by the work order.

**Result:** `runs/occam_dial/figure_results.json` reproduces the n=50 induced
model priors: p1 Linear 0.534, Sinusoidal 0.076, Sin+Linear 0.382, Quadratic
0.008; p2 Linear 0.507, Sinusoidal 0.020, Sin+Linear 0.465, Quadratic 0.008;
p3 Linear 0.007, Sinusoidal 0.001, Sin+Linear 0.992, Quadratic 0.000. At p2,
ESS implies SE(log Z) of approximately 0.008, 0.017, and 0.038 nats for Linear,
Sin+Linear, and Sinusoidal, respectively, with probability SE approximately
0.005. Every p1 model has `n_clipped=0` and `converged=True`. The p1-to-p2
estimator change narrows the Linear versus Sin+Linear gap, and the p2-to-p3
convention change provides the robust magnitude change. D17's legacy 0.934 and
0.693 values remain explicitly labeled as recorded legacy findings and are not
recomputed by the new scripts.

E6 confirms the analytic box-containment consequence and quantifies
restricted-minus-encompassing margins of 2.379 nats for Linear and 2.501 nats
for Sinusoidal. Under `occam=False`, neither pair crosses for seeds 0, 1, or 2.
Under `occam=True`, the Linear crossing occurs at τ=0.295, 0.295, and 0.296;
the seed-0 bracket is [0.282, 0.299], the per-seed spread is [0.295, 0.296],
and the ESS-implied one-SE shift interval is [0.295, 0.296]. Its bracket delta
swing of 0.354 nats exceeds the approximately 0.012-nat SE, supporting the
three-decimal crossing. The Sinusoidal crossing occurs at 1.484, 1.584, and
1.382 and supports only τ ≈ 1.5; the seed-0 bracket is [1.413, 1.496], the
per-seed spread is [1.382, 1.584], and the ESS shift roots are [1.392, 1.563].
The enclosing grid-and-seed uncertainty interval is about τ 1.33 to 1.59.
Crossing resolution is set by the larger of grid spacing and
Monte Carlo error. The empirical content comprises these margins and finite-τ
crossings. The REVIEW_AND_VET resolution text is mirrored into the committed
`runs/occam_dial/README.md` because `kb/` is gitignored. The figure remains
below the 2 MB limit. Exact rerun commands:
`python experiments/occam_dial_figure.py` and
`python experiments/e6_nesting_monotonicity.py`.

**Review outcome (2026-08-11):** §4 four-model protocol complete (Codex gpt-5.6-sol xhigh; Opus 5; Gemini 3.1 Pro via author-directed API substitution; Kimi K3 author-run pending) — round-1 REVISE with 11 cross-verified findings (0 refuted), all RESOLVED via fix pass c15a65f plus a bounded micro-fix for two hunk-introduced defects (driver-verified mechanically; no third review round per rule 4); full record runs/occam_dial/reviews/VERDICTS.md; author adjudications open: F2/NEW-1 and O2 statistical sign-offs, kb force-add variant, Kimi round.

--- D63 (from origin/paper/case-c-haaf) ---
## D63: Case C nested slope constraint under BMS* and PSIS-LOO — 2026-08-11

**Problem:** Case C needed a direct mirror of Haaf, Klaassen, and Rouder's
parameter-region comparison, not the toy example's cross-family nesting. The
comparison had to use the constraint-consistent, data-elicited $N=20$ toy
instance and place a free Sin+Linear candidate beside an otherwise identical
$b\geq0$ candidate. BMS* had to follow the validated `toy_elicited` SIR path
under both pooled and expected-posterior aggregation, while PSIS-LOO had to fit
Bayesian versions of the same pair on identical observations. The original
directional claim could not determine how the comparison came out.

**Decision:** Added `experiments/haaf_nested_constraint.py`, which writes
`runs/haaf_nested_constraint/{results.json,README.md}`. The canonical command
`python experiments/haaf_nested_constraint.py` uses
`generate_toy_data()` defaults ($N=20$, data seed 42, true $b=0.25$, noise
standard deviation 0.5). Both candidates call
`bistar_gp.candidates.CandidateModel._fit_mle`; they receive four shared base
starts and share all bounds except the lower slope bound, unrestricted for the
free candidate and zero for the restricted candidate. The restricted fit also
receives the free solutions, clipped at $b=0$ when necessary, and each
candidate's selection pool includes the other candidate's feasible vectors.
This deliberate asymmetric warm start and candidate pooling forces exact
equality at shared optima instead of turning optimizer noise into a gap. A
common log-sigma bound of [-10, 5] prevents exploratory underflow. Each shared
$\psi$ receives a fresh fit, so the per-draw free-slope sign can account for
the BMS* gap.

The BMS* arm imports `prior_sensitivity_study.py`, loads the local
`toy_elicited` prior-IS caches for seeds 0, 1, and 2, and calls the validated
stage-IS machinery with SIR seed 42 and `n_pred=1000`. It imports the pooled
and expected-posterior aggregations from
`e7_convention_sensitivity.py`, reports $\tau\in\{0.1,0.3,1,3,10\}$, uses
`pw_kl_vcal` as the primary metric, and confines `kl_forward` to an appendix
stress table. Candidate-parameter priors do not enter BMS*.

The LOO arm alone uses weakly informative priors: $A\sim$ HalfNormal(5),
$\omega\sim$ LogNormal(0, 0.7), $\phi\sim$ Uniform($-\pi,\pi$),
$c\sim$ Normal(0, 5), and $\sigma\sim$ HalfNormal(2); the free candidate uses
$b\sim$ Normal(0, 5), while the restricted candidate uses $b\sim$
HalfNormal(5). Pyro NUTS runs sequential chains with seeds 20260811 and
20260812, each with 1,000 warmup iterations and 1,000 retained draws, target
acceptance probability 0.90, and maximum tree depth 8. Every chain initializes
deterministically at the common observed-data MLE through `init_to_value`.
ArviZ computes pointwise PSIS-LOO. The $2\times10^{-7}$ structural G gates
guard machinery regressions rather than empirically testing nesting;
cross-machine artifact tolerances equal 0.005 for probabilities and the slope
fraction, 0.25 elpd for each LOO estimate, and 0.25 elpd for the paired
difference.

**Alternatives considered:** Drawing new data was rejected because it would
break the binding between the $N=20$ observations, their data-elicited GP
prior, and the validated M2bR basis. Changing `bistar_gp/` was rejected because
the existing protected `_fit_mle(..., bounds=...)` hook supplies the needed
constraint. Fitting each candidate only once to the observations was rejected
because the positive observed-data slope would make the two predictions
identical and could not produce the required per-$\psi$ slope diagnostic.
Reimplementing the SIR or aggregation formulas was rejected in favor of the
required imports. The work order does not fix a chain count; the driver prompt
allowed a single chain at this scale; two seeded chains were used instead to
obtain rank-normalized $\widehat R$ diagnostics. A figure was omitted
because the table and slope-sign count contain the full comparison.

**Result:** The pooled prior-IS ESS equals 4,464.53, and the 1,000 SIR rows
contain 883 unique cached draws. The free best-fit slope falls below zero on
1/1,000 rows, a fraction of 0.001. The remaining 999 rows have identical
primary G values for both candidates because the same feasible vector is
re-evaluated. On the one negative-slope row, restricted minus free G equals
0.000360. The one-sided ordering follows by set inclusion; the runtime gates
record zero machinery-regression violations.

At $\tau=1$, both aggregation conventions assign 0.500 to each candidate.
The free-minus-restricted probability gap remains smaller than $10^{-5}$ at
every $\tau$ under both conventions and comes entirely from the single
negative-slope draw. Its monotone contraction with $\tau$ follows
deterministically from Boltzmann aggregation, not from a measured temperature
effect. The restricted candidate cannot exceed the free candidate because the
restricted region is a subset; only the gap magnitude is empirical.

PSIS-LOO reports `elpd_loo=-13.074` (SE 3.458, `p_loo=5.343`) for the free
candidate and `elpd_loo=-12.661` (SE 3.594, `p_loo=5.169`) for the restricted
candidate. The restricted-minus-free difference equals 0.413 with paired SE
0.256, computed with `ddof=0` to match the ArviZ convention. Both NUTS fits
have zero divergences; maximum rank-normalized
$\widehat R$ equals 1.003 free and 1.002 restricted, and minimum bulk ESS
equals 1,004 and 1,638. The free maximum Pareto $k$ equals 0.564 with no
warning. The restricted maximum equals 0.718, and ArviZ flags one observation
above its 0.697 good-$k$ threshold. Because both candidates' chains initialize
at the same MLE and sampled-grid aliases occur near $\omega=4.939$ and 6.999,
the $\widehat R$ and ESS values support within-mode convergence only.

The difference is directionally inconclusive: its magnitude is smaller than
twice its paired SE, the constrained estimate carries a Pareto-$k$ warning,
and the paired SE covers data-level pointwise variability only, without MCMC
error. Haaf, Klaassen, and Rouder report this kind of null-to-inconclusive LOO
difference as the failure mode for a satisfied nested constraint.

The two slope priors coincide up to normalization on $b>0$, so LOO has no
structural contrast wherever negative-slope posterior mass is negligible. The
artifact's own full-data local Gaussian diagnostic gives posterior SD
0.0129506 for $b$, places the boundary 19.4028 SDs away, and gives a Gaussian
left-tail probability of $3.65\times10^{-84}$. This local approximation
supports the reading that the constraint binds only where the locally
approximated posterior carries negligible mass. It does not prove that the
global posteriors or leave-one-out fold posteriors are exactly identical, and
it does not establish that the entire observed gap comes from estimator
noise. Case C therefore records a null-to-inconclusive LOO comparison and an
effective BMS* tie without a directional claim.

**Review outcome (2026-08-11):** §4 four-model protocol complete (Codex gpt-5.6-sol xhigh REVISE-3; Opus 5 fresh-agent REVISE-10; Gemini 3.1 Pro package-only APPROVE-0 via author-directed API substitution; Kimi K3 author-run pending) — 13 collated findings, OC1 REFUTED as stated in adversarial cross-check with its narrowed core implemented, all others confirmed and RESOLVED via fix pass 0ce03ba plus a bounded micro-fix for one S4 naming defect (driver-verified; no third round per rule 4); notable outcome corrections: LOO direction reported as inconclusive (the null-to-inconclusive difference matches the Haaf/Klaassen/Rouder failure mode), BMS* one-sidedness stated as structural, table at declared-tolerance precision; full record runs/haaf_nested_constraint/reviews/VERDICTS.md; author adjudications open: OC1' LOO interpretation, kl_forward documentation + precision policy, arviz manifest scope note, Kimi round.

--- D64 (from origin/paper/case-d-mopen) ---
## D64: Case D synthetic distinguishability calibration and MAP-conditional deviation localization — 2026-08-11

**Problem:** Case D needed per-trial deviation curves and an honest M-open
calibration argument from the existing practice-law artifacts, without rerunning
`experiments/practice_EvansEtAL/run.py`, changing its artifacts, or starting new
HMC. Inventory found no deviation implementation and no files under the practice
data directory. The 50 `results_hmc/` subject files therefore concern only
`generate_demo_data(n_subjects=50, seed=42)`, with 25 power-generated and 25
exponential-generated series. Both generating forms appear in the fitted pair,
so the cohort supports a distinguishability and mimicry study plus
correct-specification reference levels for stored divergence magnitudes, not a
real-Evans-data analysis or a direct M-open misspecification finding. Direct
inspection also corrected one work-order shorthand: the stored and regenerated
training series range from 20 to 79 trials rather than containing 20 trials
each. Stored practice G values use a 50-point uniform grid over every subject's
full series, while the reconstructed curves use integer trials 1 through 20.
For the longest subjects, those trials span 24.4% of the full continuous trial
range, so linkage to the aggregate G results stays within the shared early
region.

**Decision:** Added `experiments/regret_curves_mopen.py`, which writes
`runs/regret_curves_mopen/{results.json,README.md,regret_curves.png}`. It prefers
the read-only `experiments/practice_EvansEtAL/results_hmc/` directory, imports
`generate_demo_data` and the Power and Exponential classes from the practice
experiment rather than copying them, and evaluates stored fitted parameters on
the regenerated full subject series before any deviation calculation. Data seed
42 regenerates the observations. Subject `i` receives posterior-function seed
`20260811 + i`, with 100 latent conditional GP draws and no added observation
noise. The common evaluation grid contains trials 1 through 20. At each trial,
the solid curve reports the MAP-conditional posterior expected absolute
deviation of the latent function,
`E_{f|y,eta_hat}[abs(f(t) - mu_theta(t))]`; its band spans the pooled 10th and
90th percentiles across 25 subjects times 100 draws within each truth cohort,
so it describes dispersion rather than a confidence interval for the mean. A
dashed overlay reports the mean-based plug-in
`abs(E[f(t)|y,eta_hat] - mu_theta(t))`, aggregated over the same 25 subjects.
Jensen's inequality orders the exact estimands: the exact latent-draw deviation
is no smaller than the plug-in deviation per subject, candidate, and trial. The
finite 100-draw Monte Carlo estimates carry Monte Carlo error and may invert
locally, as at trial 1 for the Power candidate under Power truth (116.333 versus
116.506) and Exponential truth (131.415 versus 131.572). Unequal inflation
changes the candidate gap trial-dependently, which motivates reporting both
estimands.
The formal limits-note equation and the Case D work order specify an absolute
difference; a chat-derived Q&A in the same note says squared difference, and
the binding absolute form takes precedence.

`run.py` loops through practitioner, moderate, and agnostic configurations. It
sets the single `gp_hyperparameters` block only while that block remains empty,
immediately after a successful configuration MAP fit and before the HMC branch.
All 50 source files contain every configuration's diagnostics, so their stored
lengthscale, outputscale, and noise values come from the first, practitioner MAP
fit even in `results_hmc/`. The subject JSONs do not retain HMC hyperparameter
draws. The deviation script therefore rebuilds the practitioner RBF GP at that
stored point and performs exact conditioning with normalized-variance jitter
`1e-6`; it neither refits hyperparameters nor reconstructs HMC trajectories.
Because the limits-note target averages posterior mean functions over
hyperparameter draws, neither MAP-conditional reconstruction equals that
target. Reporting both the latent-draw expected deviation and the posterior-mean
plug-in makes the mean-versus-draw substitution explicit next to the MAP-versus-
HMC limitation.

The stored `bistar_G_diagnostics` values are aggregated without recomputing G.
Those artifacts predate W1 and contain `pw_nll`, `pw_mse`, and
`pw_hellinger`, not `pw_kl_vcal`. Legacy `pw_nll` weights by candidate fitted
noise variance, while `pw_kl_vcal` weights by GP variance; `pw_mse` lies closer
on that axis. The script verifies the candidate-specific affine identity between
stored `pw_nll` and `pw_mse`, records the full temperature-scale diagnostic, and
aggregates the tau-free `pw_nll` `raw_draw_wins` statistic for all three
configurations. `docs/paper-sie-jmp/06-case-D-mopen-calibration.md` states these
limits, separates F1 scaffold representability from F2 intrinsic mimicry, and
positions the result against Navarro, Pitt, and Myung (2004), Evans et al.
(2018), and Averell and Heathcote (2011).

**Alternatives considered:** Using `results/` was rejected because the work
order prefers the HMC-mode artifacts. `results_diag/` and
`results_hierarchical/` were not consulted because no documented need emerged.
Rerunning the practice scripts, refitting candidate or GP parameters, and
starting HMC were rejected by scope and because the required reconstruction
uses frozen artifacts. A squared deviation was rejected because it conflicts with
the binding formula. A normalized 20-point refit was rejected in favor of
conditioning on every regenerated observation and evaluating only the common
20-trial grid. The optional transform-space E8b module was deferred by the
driver; no `experiments/e8b_transform_space.py` was created, and the section
retains an explicit `[E8B-PLACEHOLDER]` block for later commissioning or clean
excision.

**Result:** The fidelity gate recomputed 100 stored candidate BIC log marginal
likelihoods from regenerated observations and stored parameters. Maximum and
mean absolute errors equal `5.684e-14` and `5.116e-15`, below the asserted
`1e-8` tolerance. The minimum posterior-covariance eigenvalue across subjects
equals `-2.400e-15`, within the `1e-8` numerical PSD tolerance. Two consecutive
runs produced identical SHA-1 values for all three outputs. The figure occupies
182,245 bytes, below 2 MB.

For power-generated curves, the MAP-conditional posterior expected absolute
deviation averages 21.383 for Power and 20.681 for Exponential across 20 trials;
the mean-based plug-in averages 17.638 and 17.325. Their trial-1 peak gaps equal
33.782 and 34.052. For exponential-generated curves, the corresponding
MAP-conditional means equal 35.587 and 14.855, and the plug-in means equal
33.901 and 10.764; their trial-1 peak gaps equal 91.452 and 92.890. The
MAP-conditional early-gap shares remain 70.0% and 82.2% through trials 5 and 10
under power truth, versus 41.7% and 77.7% under exponential truth. The plug-in
shares equal 63.3% and 74.0%, versus 40.0% and 75.0%. Both estimands therefore
give a consistent descriptive localization under the stored practitioner-MAP
scaffold.

The aggregated stored practitioner `pw_nll` means equal 4.799 for Power and
4.775 for Exponential under power truth, versus 5.003 and 4.582 under
exponential truth. Synthetic exponential subject 25 supplies a particularly
clear mimicry example: 4.881 for Power and 4.852 for Exponential, an absolute
difference of 0.029. These known-truth levels show what a future absolute
inadequacy calibration must condition on; Case D sets no rejection threshold.
Every one of the 300 stored `mean_G` pairs satisfies
`pw_nll = 0.5*log(2*pi*sigma_theta^2) + pw_mse/(2*sigma_theta^2)`, with maximum
absolute error `1.78e-15`; the divisor `2*sigma_theta^2` ranges from 743 to
7,161. Shared-temperature probability magnitudes therefore do not support a
cross-metric confidence contrast. No temperature on the stored 15-point grid
closes the gap: at `tau=0.1`, the power-cohort `pw_nll` medians are 0.581, 0.569,
and 0.557 for practitioner, moderate, and agnostic, respectively, while the
all-subject practitioner `pw_mse` median remains 0.987 at `tau=31.6`. On the
tau-free practitioner `pw_nll`
diagnostic, the true family wins 974/2,500 draws (39.0%) under power truth, with
9/25 subject majorities, versus 2,467/2,500 (98.7%) and 25/25 under exponential
truth. Moderate gives 39.9% with 8/25 versus 94.6% with 25/25; agnostic gives
41.5% with 9/25 versus 92.1% with 25/25.

Exactly one practitioner-MAP RBF reconstruction appears in this branch, and all
three stored configurations use RBF kernels. The early-trial localization
cannot identify whether the `pw_nll` asymmetry comes from F1 representability,
F2 mimicry, metric behavior, or sampling noise. It remains consistent with the
tau-free asymmetry only within the shared early-trial region.

The bytewise inventory hash for every file under
`experiments/practice_EvansEtAL/` remained
`528fea7d955841cf496883df4f96bb85b8357b4a` before and after execution.

**Review outcome (2026-08-12):** §4 four-model protocol complete (Codex gpt-5.6-sol xhigh REVISE-4; Opus 5 fresh-agent REVISE-11; Gemini 3.1 Pro package-only APPROVE-0 via author-directed API substitution; Kimi K3 author-run pending) — 14 collated findings; two-reporter clusters F-D1 (pw_nll/pw_mse contrast a unit artifact; exact affine identity; thesis re-carried by tau-free raw_draw_wins 39.0/39.9/41.5 vs 98.7/94.6/92.1 percent) and F-D2 (estimand relabeled MAP-conditional; posterior-mean plug-in added, asymmetry survives) plus DC4/DO5/DO8/DO9/DO11 confirmed and fixed in c57a70e; DO2/DO3/DO6/DO7/DO10 REFUTED in adversarial cross-check and logged; two hunk-introduced S3s fixed by bounded micro-fix with driver mechanical verification (no third round per rule 4); full record runs/regret_curves_mopen/reviews/VERDICTS.md; author adjudications open: F-D1/F-D2 statistical sign-offs, F-D3 framing, Kimi round.

--- D67 (from origin/paper/case-e-debias) ---
## D67: Case E toy debias demonstration — evaluation and mitigation from one posterior — 2026-08-13

**Problem:** The thesis (ch. 5) and the accepted proposal set two goals for the
BI*/BMS*-GP program: model evaluation via data priors, and bias mitigation.
Manuscript sections 1-6 and 8 deliver the first; section 7
(`docs/paper-sie-jmp/07-debias-bridge.md`) was still a stub, so the second goal
appeared in the paper only as a promise. The demonstration had to be small,
in-paper, and honest, and it had to be built without touching the D58 Mauna Loa
preregistration boundary, which reserves the real-data development for the
companion line.

**Decision:** Added `experiments/toy_debias_demo.py` and the run directory
`runs/toy_debias_demo/` (`results.json`, `README.md`, `debias_figure.png`), and
replaced the section 7 stub with the full section carrying that one figure.

Data: `bistar_gp.generate_toy_data()` at its defaults (N=20 on [-10, 10], seed
42, observation noise 0.5, `bias_slope=0.25`, y = sin(x) + 0.25x + noise), so
the true process and the bias process are both known by construction.

Fit: SE + linear additive kernel under `PRIOR_CONFIGS["toy_elicited_n20"]`, the
registry entry byte-identical to `experiments/prior_sensitivity_study.py`
STUDY_CONFIGS `toy_elicited`. Hyperparameters from the CORRECTED sampler path
`bistar_gp.fit.fit_hmc` (`nuts_e1`); the pre-correction Pyro NUTS setup is not
used. Two chains, seeds 20260813 and 20260814, 500 warmup + 500 retained draws
each (1,000 pooled), `target_accept_prob` 0.8, `max_tree_depth` 8, initial step
size 0.1 with adaptation. INIT DISCLOSURE: both chains start at the SAME MAP
point (`fit_map`, torch seed 42, 500 iterations, lr 0.05), so the reported
rank-normalized R-hat is WITHIN-MODE evidence about mixing around the
optimizer's mode, not between-mode agreement from dispersed starts; the toy
hyperparameter posterior is multi-basin (D12). The disclosure is carried in
`results.json` (`config.init_strategy`), in the run README, and in the section
prose, per the standing requirement from the Case C review.

Decomposition: the package machinery only. `bistar_gp.decompose
.decompose_additive_gp` for the SE (truth-candidate) and linear
(bias-candidate) components, and `decompose_component` on the summed kernel
blocks for the joint posterior, so the inter-component cross-covariance is
retained rather than dropped by summing component covariances. Debiasing by
marginalization: analytic within a draw (the returned component posterior
already forms the marginal of the joint conditional Gaussian) and Monte Carlo
across draws for the hyperparameters. Bands are latent-function bands with no
observation noise, matching the convention documented in
`experiments/honest_band_decomposition.py`; summary sds use the law of total
variance, and reported intervals are EXACT central intervals of the draw
mixture obtained by CDF bisection rather than mean ± 2 sd approximations.

Slope read: gpytorch's `LinearKernel` gives k(x, x') = v x x', so the linear
component's posterior mean is exactly linear and its posterior covariance
exactly Var(b|θ) x xᵀ. Both properties are verified per draw and the worst
deviations recorded (4.456e-13 for linearity, 1.896e-15 for rank-one variance),
which licenses reading the slope moments off the decomposition output instead
of introducing a separate formula.

**Alternatives considered:** Importing `bistar_gp.debias.decompose_model_hmc`
was rejected because it discards each draw's conditional covariance
(`bistar_gp/debias.py:206`), so its bands show across-draw mean spread alone
and would have understated the debiased uncertainty and wrecked the coverage
number. Importing `total_variance_decomposition` from
`experiments/honest_band_decomposition.py` was rejected because it returns
summary bands only, whereas the recovery numbers need per-draw component
moments for the mixture quantiles; that helper's total-variance and
latent-band conventions are followed and cited, not copied, and this script
makes a single consistent pass over the package decomposition. A mean ± 2 sd
band was rejected in favour of exact mixture quantiles. Random subsampling of
draws (the `np.random.choice` convention in the older helpers) was rejected in
favour of using all 1,000 draws, which removes an RNG dependence from the
reported numbers. Any Mauna Loa material was excluded by scope.

**Result:** First run kept; no iteration toward better numbers. Diagnostics
clean: 0 divergences, rank-normalized R-hat at most 1.0025, bulk ESS at least
602.4, tail ESS at least 502.6, tree-depth saturation rate 0.0, and 1,000 of
1,000 decompositions successful.

Recovery, with uncertainty layers, all in
`runs/toy_debias_demo/results.json`:
- bias-slope posterior mean 0.197, sd 0.072, 95% central interval
  [0.033, 0.323], which CONTAINS the generating 0.250 (posterior layer);
- RMSE against sin(x) on a 201-point grid inside the training span: composite
  posterior mean 1.430, debiased posterior mean 0.403, a reduction of 1.028 or
  71.9% (between-chain scatter 1.431/1.430 and 0.403/0.402);
- coverage of sin(x) by the debiased 95% band 0.866 (174 of 201 grid points),
  i.e. mild UNDERCOVERAGE, reported as it came out;
- scale references on the same grid: the drift 0.25x has RMS 1.451 and sin(x)
  has RMS 0.690, so the composite arm's discrepancy essentially reproduces the
  drift it was fitted to include, and the residual 0.403 is not negligible;
- mean band width 1.836 debiased versus 1.032 composite, i.e. the data
  constrain the SUM of the components far more tightly than either component
  alone. That number is what makes the section 8.5 uncertainty-floor sentence
  concrete, and section 7 now states the connection.

Determinism: byte-stable. Two consecutive runs reproduced BOTH `results.json`
and `debias_figure.png` byte for byte (results.json sha256
`e73f067276e7bd61026dbcde835d9e1461d5dd604a448cd5176e3b0687eaaa3c`, figure
sha256 `6ebd195f8bf9c224361853ba16b36af1f2e4010ffec912fb6bb44766b5e58907`) on
python 3.13.11 / torch 2.10.0 / numpy 1.26.4 / arviz 0.23.4. Byte-stability is
asserted within one environment only; across environments the README pins
numeric tolerances (recovery 1e-6 absolute, R-hat 1e-3, ESS 1 effective draw).
Rerun: `python experiments/toy_debias_demo.py` from the repository root, about
one minute on a laptop CPU, no network and no new dependencies. Figure size
264 KiB, well under the 2 MB limit.

Scope, stated in the section, the run README, and `results.json`
(`scope.mauna_loa_contact = "none"`): synthetic toy only; no Mauna Loa script
or artifact is imported, executed, or cited, so the D58 preregistration
boundary is untouched, and no real-data number is reported or forecast.
KERNEL-LABELING CAVEAT: identifying the linear component as bias is a modeling
CHOICE, licensed here only because the generator produced the drift. The
decomposition will split an additive posterior whichever way the labels are
assigned, so in an application the analyst must justify the labeling on
substantive grounds before a marginalization result means what its name
suggests.

**Status:** Section 7 fleshed out at `docs/paper-sie-jmp/07-debias-bridge.md`
with the one figure and evidence-tier footnotes; the derived
`docs/paper-sie-jmp/tex/sections/07-debias.tex` still holds the old stub text
and needs regeneration through `docs/paper-sie-jmp/build_tex.py` at assembly
time. No review round has been run on this case yet (HANDOFF §4 protocol not
yet applied to Case E). No git mutation was performed by the implementing
session.

**Review-fix addendum (2026-08-13):** The HANDOFF §4 round-1 review has since
run against branch tip `8f1326d`, and this pass implements its confirmed queue.
The body above is left as committed; everything below records what changed.

Round-1 verdicts (`runs/toy_debias_demo/reviews/VERDICTS.md`, raw outputs
`round1_*.md`, checker notes `check_*.md`): Opus 5 REVISE with 15 findings and
an independent bit-exact reproduction of every committed number; Gemini
(`gemini-3.1-pro-preview`, HIGH) APPROVE; Kimi K3
(`moonshotai/kimi-k3`) APPROVE; Codex GPT 5.6 sol ABSENT and disclosed
(usage lock to 2026-08-18), so the synthesis-round substitution pattern applies
and a substitute implementer, not a reviewer, executed the fixes. Verdict
conflict resolved by rule 3: the queue was non-empty, so REVISE governed. Three
single-reporter findings were REFUTED by adversarial check and logged with
their refutations rather than silently dropped: F2 (coverage comparators; the
sentence makes an absolute claim with a correct caveat, and the omitted numbers
would favour the debiased arm), F5 ("removes most of it"; true under every
candidate statistic, both framings already supplied), and F6 (latent-band
terminology; the convention is disclosed in section, README, and JSON). Two
items were routed to the assembly ledger on the synthesis branch instead of
being fixed here: F9, the synthesis 8.6 sentence "All four reviewer rounds are
recorded for every case", which Case E falsifies once it becomes section 7, and
the known staleness in the 8.5 footnote wording. F8, the missing
`build_tex.py` registry entries for section 07 (branch pin, FIGURES and
FIGURE_PATHS, tier map extension), was fixed driver-side in untracked tooling
and is therefore not part of this diff.

Twelve queued items were implemented: FIX-1 through FIX-11 in
`experiments/toy_debias_demo.py`, `docs/paper-sie-jmp/07-debias-bridge.md`, and
the regenerated `runs/toy_debias_demo/` artifacts, plus this addendum. The
sampling was NOT touched: same seeds, same budget, same estimators, and every
number the committed entry reported is bit-identical after the rerun.

INIT-STRATEGY PROVENANCE, CORRECTED (FIX-1, review F1). The claim above that
"the toy hyperparameter posterior is multi-basin (D12)" misattributes D12. The
D12 bimodality finding is scoped to the `informative` prior configuration
(D12 Finding 1: two modes, valley ≈ −43 between them, mass split ~3:1), not to
the `toy_elicited` configuration this demonstration uses.
`runs/prior_sensitivity/stage_a_toy_elicited.json` certifies the opposite
geometry for the configuration actually run: `coherent_geometry` true,
`valleys` empty, `bimodal` false, and a single mode with
`verified_local_max` true holding `pooled_is_mass` 1.0, recovered from all 27
wide starts of the mode hunt (every start converges to log joint −18.913602).
That mode's converged point agrees with this run's MAP in every hyperparameter:
the largest absolute discrepancy is 1.69e-8 (SE lengthscale), so the corrected
artifacts state agreement "to within 2e-8" rather than the review's "~1e-9",
which the driver's own recomputation does not support. The correction is
carried in all four places the misattribution appeared: section 07 §7.1, the
`config.init_strategy` string in the script, the run README via
`write_readme`, and here. The shared-init disclosure itself is UNCHANGED and
still stands, on the narrower and correct ground that a common start leaves
R-hat silent about regions no chain visited. The stage_a artifact is cited
through the disclosed local-material pattern used by synthesis sections 02 and
08, since it is not committed in this repository.

NEW DERIVED NUMBERS, all regenerable from the script and recorded in
`results.json` so no prose number is orphaned:
- `recovery.bias_band_mean_width` 1.4584026383414934, the linear component's
  own mixture band (FIX-3, F4). Section 07 now reads "the composite band has
  mean width 1.032 and the linear component's 1.458", which the previous
  "either component alone" phrasing asserted without evidence;
- grid-mean total variances 0.2368453522059466 (SE), 0.17521904311580203
  (linear), 0.06668550257966654 (composite), and the cross-covariance
  −0.17268944637104106 with correlation −0.8477010316953286 read off them
  (FIX-2, F3). Means add across the decomposition and the law of total variance
  is linear, so the composite total variance equals the two component total
  variances plus twice their total cross-covariance; inverting that identity
  introduces no new estimator. These replace the old N-asymptotic sentence
  ("additional observations sharpen the composite while leaving the attribution
  comparatively uncertain, and honest inference retains an uncertainty floor
  that sample size does not remove"), which asserted behaviour in N from a
  single N=20 run. Section 07 now states only what was measured, and says
  explicitly that whether the gap persists as N grows is untested here;
- `decomposition.n_draws_needing_extra_jitter` 0 of 1000 (FIX-7, F12).
  `compute_cholesky` escalates jitter silently, so each draw is now probed at
  the base 1e-4 first and the escalations counted; the count came out 0 and is
  reported as it came out.

CODE HARDENING. FIX-7 also makes an unmatched `apply_hp_value` site raise
RuntimeError instead of discarding the returned False, which had been a
silent-wrong-answer path: a site-naming drift would have decomposed a
prior-initialized model without any error. FIX-8 (F13) adds
`assert_library_sampler_settings()`, which parses
`bistar_gp.e1_potential.fit_hmc_e1` and compares the literal `step_size`,
`target_accept_prob`, `adapt_step_size`, and `sampler_name` it passes to
`_run_e1_nuts_route` against the constants this script mirrors into
`results.json`, cross-checks the route's signature defaults, and verifies that
`bistar_gp.fit.fit_hmc` still routes to `fit_hmc_e1`; any drift now fails the
run loudly instead of silently falsifying the recorded configuration. FIX-9
(F14 + Kimi K2) renames `sampler.acceptance_rate_by_chain` to
`move_fraction_by_chain` and adds `move_fraction_note`, because pyro's
0.992/0.998 counts post-warmup iterations that moved and is not comparable to
the targeted mean Metropolis acceptance that `target_accept_prob` 0.8 sets; the
README diagnostics line states the distinction, and the section prose still
does not mention acceptance.

FIGURE. FIX-4 (F7) sets `sharey=True` alongside the existing `sharex=True`, so
the band-width contrast the section's second limit rests on is now visible
across panels, and annotates panel (a) with mean band width 1.032 and panel (c)
with 1.836 in the existing annotation style.

PROSE. FIX-5 (F10) opens §7.1 with the evaluation-side cross-link: section 3.4
grades candidates on this same N=20 seed-42 instance under the same
data-elicited configuration and places most weight on Sin+Linear at 0.441 under
pw_kl_vcal at τ=1 on the SIR path, while the demonstration decomposes the
posterior of that same additive structure on the corrected NUTS path, the two
estimators reported separately; no other Case A number is re-quoted. FIX-6
(F11) records that `toy_elicited` sets its lognormal medians from this same
sample's observable summaries, an empirical-Bayes-style construction, so the
posterior statements are conditional on that fixed prior rather than
unqualified full Bayes, and the coverage paragraph now notes that the coverage
figure inherits the same conditioning. FIX-10 (F15) detaches divergences and
tree-depth saturation, which are per-trajectory quantities, from the
per-hyperparameter list. FIX-11 (Kimi K1 + Gemini GE1) removes the role-noun
constructions from the ancillary text: the README's "thesis ch. 5 is the source
of the program" becomes "the program originates in thesis ch. 5", and the
script docstring's "the SE component is the truth candidate, the linear
component the bias candidate" becomes "serves as ... as"; a sweep of the
script's remaining strings and comments found one further instance, in the new
FIX-8 docstring, which was reworded before the run.

DETERMINISM AND ARTIFACT HASHES AFTER THE FIX PASS. Two consecutive reruns of
`python experiments/toy_debias_demo.py` reproduced all three artifacts byte for
byte on python 3.13.11 / torch 2.10.0 / numpy 1.26.4 / arviz 0.23.4:
- `results.json` sha256
  `65c9ff5f14b9a5f3aca8267745d6b368d95b831e85a610f6844b74e1b33712bb`
  (was `e73f067276e7bd61026dbcde835d9e1461d5dd604a448cd5176e3b0687eaaa3c`);
- `debias_figure.png` sha256
  `c1153549ca55d9d644804790ef9a4627f8d82bedd157ec348ecb519f551a4723`
  (was `6ebd195f8bf9c224361853ba16b36af1f2e4010ffec912fb6bb44766b5e58907`),
  271,642 bytes, still far under the 2 MB limit;
- `README.md` sha256
  `7096cd6e4d3d02f8971cee294fa3e50a2c7248272320e9cc72cfc45994f889af`.

A field-by-field diff of `results.json` against the committed version shows
exactly the intended changes and nothing else: nine added keys, the
`acceptance_rate_by_chain` to `move_fraction_by_chain` rename carrying the same
0.992/0.998 values, and the rewritten `config.init_strategy` prose. Every
pre-existing numeric field is bit-identical, including slope 0.197 / sd 0.072 /
[0.033, 0.323], RMSE 1.430 and 0.403 with reduction 71.9%, coverage 0.866
(174/201), band widths 1.836 and 1.032, R-hat max 1.0025, bulk ESS 602.4, tail
ESS 502.6, 0 divergences, tree-depth saturation 0.0, the MAP point, the two
final step sizes, and the linearity and rank-one structure deviations.

The author-adjudication ledger in `VERDICTS.md` remains open at merge proposal,
with four items: sign-off on the F1 init-provenance correction and whether
`runs/prior_sensitivity/stage_a_toy_elicited.json` should be committed as
evidence rather than cited as local material; sign-off on the F3 floor-sentence
restriction and whether to commission the optional N-sweep (20/50/200) that
would test the floor claim outright; the F2 enrichment option, the
driver-verified composite and bias coverages 0.821 and 1.000, available but not
required; and ratification of the substitute-implementer and
driver-verification deviations, or a Codex re-review once the usage lock lifts
on 2026-08-18. No git mutation was performed by this fix pass.

**Closure addendum (2026-08-13):** §4 protocol complete for Case E. Re-review
round (changed hunks, by raisers): Opus 5 all ten queue findings RESOLVED
(repo-verified, including executing the FIX-8 guard with three negative
controls; its own round-1 "~1e-9" MAP-to-mode figure corrected to the
committed 1.690e-8 measurement); Kimi K3 both RESOLVED (relabel judged more
accurate than its own proposal); Gemini GE1 RESOLVED, changed-hunk checklist
clean. Eight hunk-introduced defects: seven Opus (N1 S3 cross-link conflated
the parametric Sin+Linear candidate with the GP kernel posterior; N2-N7 S4)
and one Kimi (jitter-probe claim breadth), resolved as four micro-fixes to
section 07 by the substitute agent (MF-1 covers N1+N2+N3: grades candidates
AGAINST the induced posterior, "described below", the pooled-aggregation
qualifier on 0.441; MF-2 "the band conditions on"; MF-3 caption records the
shared y axis; MF-4 "grid-averaged correlation"), one correction recorded
here (N7: the fix-pass addendum's field-count sentence undercounted — the
results.json delta against 8f1326d is ten added keys, nine in recovery and
decomposition plus sampler.move_fraction_note, together with the
acceptance_rate_by_chain/move_fraction_by_chain rename pair and the rewritten
config.init_strategy), and one refutation on source evidence (Kimi's probe
finding: decompose_additive_gp performs a single shared Cholesky of the
summed training matrix, bistar_gp/decompose.py:93, and the demo never calls
sample_from_component, so the probe covers every factorization executed).
Review record committed at runs/toy_debias_demo/reviews/ (VERDICTS.md +
round1/check/rereview raw outputs). Protocol outcome: REVISE resolved —
branch proposed for merge subject to the five-item author ledger in
VERDICTS.md (F1 and F3 statistical sign-offs; F2 enrichment option; the
substitute/driver substitutions to ratify; the two assembly-ledger items F9
and the 8.5 footnote on the synthesis branch). Nothing merges autonomously.

--- D66 (from origin/paper/synthesis-sections) ---
## D66: Synthesis sections integrate the four case studies — 2026-08-12

**Problem:** The synthesis branch still contained stubs for the Introduction,
Machinery, and Discussion after the four case sections were completed on their
separate branches. The assembled manuscript needed those sections to adopt the
case prose conventions, expose the author-resolved evaluation dials, carry the
Case B-to-C nesting logic into the general account, and state the Case D scale
and calibration limits without copying case results or treating knowledge-base
files as numerical authority.

**Decision:** Replaced the stubs in `docs/paper-sie-jmp/01-intro.md`,
`docs/paper-sie-jmp/02-machinery.md`, and
`docs/paper-sie-jmp/08-discussion.md` with final manuscript prose under the
frozen notation in `docs/paper-sie-jmp/00-notation.md`.

Section 1 frames the contribution for the third JMP model-evaluation special
issue, treats data priors as the through-line from the foundational JMP papers,
connects the construction to Bonifay and Cai's fit-propensity program, makes the
three evaluation dials the unifying contribution, and previews the four cases
with Case C's null and Case D's synthetic-only scope stated directly. Section 2
develops the data prior, projection and induced priors, \(Z_M\), soft transfer,
aggregation, and metric roles. It adds a numbered containment remark: for
\(M_r\subset M_e\), best-instance divergence orders the encompassing candidate
no worse on every shared pattern, so no listed table-path aggregation can favor
the restriction at any \(\tau\); restriction credit belongs to the
reference-measure side controlled by `occam`. It also records the D60
Resolution, retains W1 and the D61 `kl_forward` attribution, and adds the Case D
scale-invariance reporting rule. Section 8 revisits the dials, states the Case
B-to-C bridge, preserves M-open calibration as open while recognizing Case D's
known-truth reference material, upgrades hybrid \(Z_M\) with the Case A Target B
test, distinguishes BMS*-GP from elpd and PSIS-LOO using Case C, records the
verification protocol, and treats F1 and F2 as scope conditions.

The verification paragraph reflects the completed case review archives. All
four reviewer rounds are recorded for every case, with the fourth, Kimi K3, run
at the author's direction on the same round-1 packages; the findings,
refutations, fixes, and author sign-off records are committed under
`runs/<case>/reviews/` in this repository. D65 records the provenance exception
for the D17-recorded local methods-validation reach check, which Section 8
states explicitly in the same terms.

The case sections remain on their source branches and are cited at their
assembled-manuscript paths: Case A from `paper/case-a-vanbork` at
`docs/paper-sie-jmp/03-case-A-external-validation.md`; Case B from
`paper/case-b-occam-dial` at
`docs/paper-sie-jmp/04-case-B-occam-dial.md`; Case C from
`paper/case-c-haaf` at
`docs/paper-sie-jmp/05-case-C-nested-constraints.md`; and Case D from
`paper/case-d-mopen` at
`docs/paper-sie-jmp/06-case-D-mopen-calibration.md`. Synthesis footnotes name
the case-generating `experiments/` scripts, `runs/` artifacts, and decision
entries. Knowledge-base paths support arguments only.

**Alternatives considered:** Re-quoting case headline values was rejected in
favor of a zero-new-empirical-numbers policy. Copying the absent case files onto
the synthesis branch was rejected because final assembly supplies sections 3
through 6 from their case branches. Choosing a new canonical aggregation or
`occam` convention was rejected in favor of the D60 Resolution and the frozen
defaults. Treating the local `kb/` vault or an uncommitted visualization path as
numerical authority was rejected; cross-branch case artifacts and decision
records provide the empirical provenance.

**Result:** The three synthesis sections contain no re-quoted empirical
estimate. Their only numerals belong to section and equation references,
notation, decision identifiers, and bibliographic metadata. All requested
case-derived additions appear in the designated sections, provenance footers
name the supporting scripts, artifacts, and decisions, and D66 was appended at
the end of the decision log. No experiment, artifact-generation command,
network request, or state-mutating git operation ran during the synthesis pass.

**Review outcome (2026-08-12):** §4 protocol complete with ALL FOUR reviewers live in round 1 (Codex gpt-5.6-sol xhigh REVISE-5; Opus 5 fresh-agent REVISE-12; Gemini 3.1 Pro APPROVE-0; Kimi K3 APPROVE-2) — 19 collated findings; 9 confirmed + 1 checker-split (SC2, driver-adjudicated to fix) fixed in d6ee868 by a DISCLOSED SUBSTITUTE implementer (fresh Opus subagent; Codex usage-locked to 2026-08-18 after round 1, its cross-checks rerouted to non-originators and its re-review replaced by driver mechanical verification); 8 findings REFUTED and logged; re-review by available raisers all RESOLVED; three hunk-introduced defects fixed by micro-fix (plug-in-surrogate framing; section-7 forward-reference; projection softening) and driver-verified; full record runs/synthesis_sections/reviews/VERDICTS.md; author adjudications open: SC1 Gbar surrogate + frozen-notation amendment, SC2 pooled-limit sign-off, substitute-implementer ratification, uncommitted-local-material policy.

--- D68 (from origin/fix/code-review-2026-09) ---
## D68: Code review 2026-09 fix pass 1 — nine implementation fixes with pinning tests, four-channel review, pass 1b folds — 2026-09-08

**Problem:** The 2026-09 implementation-correctness review (four channels: Fable, Codex
gpt-6-astra xhigh, Kimi K3, GLM 5.3; governing document
`docs/paper-sie-jmp/HANDOFF-code-review.md`; record `runs/code_review_2026_09/`) collated
nine defect classes in the package against manuscript section 02, adjudicated in
`runs/code_review_2026_09/ledger_draft.md` revision 3 and dispatched as
`docs/paper-sie-jmp/prompts/code-review-fix1.txt`. The S1 item: `decompose_model_hmc` and
`decompose_model_mcmc` reported `std` as the across-draw spread of the conditional means
alone (dropping every draw's conditional variance), so every band they produced was
understated (D58 Mauna cards by an order of magnitude), and the Mauna debias script added
component variances as if independent (dropping cross-covariances). S2/S3 items: single-
kernel pyro site names silently dropped by `select_hmc_sites`/`apply_hp_value`; draws dropped
without accounting in `extract_gp_predictives`; `soft_transfer_weighted` stabilizing draw
weights and Boltzmann factors separately (underflow to a uniform posterior);
`compute_induced_prior` applying likelihood weights to posterior draws (density
proportional to p(eta) p(y|eta)^2); metrics_v2 Hellinger variants using /4 sigma^2 instead of
/8 sigma^2; the 1e6 / -1e10 failure sentinels in `laplace_evidence.py` that a metric could
turn into a winning score; no draw-concentration diagnostic behind a pooled score; the W1
metric roles and the M2bR withdrawn caches unrepresented in code; the van Bork targets never
asserted; Case C importing the Case A script across branches for the aggregation conventions.

**Decision:** Fix pass 1 implemented in the sibling worktree
`/Users/sc8918/Documents/GitHub/bistar_gp_c-fix` (branch `fix/code-review-2026-09` from
`71540836`) by Fable at the author's choice ("I code all nine"), under the work order's
editable set and with the author-authorized package-change exception. FIX-1 site names and
draw integrity (`model.py`, `bms_star.py` `PredictiveList`, `prior_sensitivity_study._sir_bms`
raise). FIX-2 law-of-total-variance moments, joint group posteriors conditioned with the
Cholesky factor of the ENTIRE training covariance (`DecompositionResult.group`), exact mixture
central intervals ported from `experiments/toy_debias_demo.py` into
`bistar_gp/decompose.mixture_central_interval`, `compute_debiased` rewritten on group outputs;
the seven-field `DecompositionResult` positional contract kept. FIX-3 `boltzmann_weight_ess`,
`hard_win_statistics` (exact-tie split credit), four optional `BMSStarResult` fields,
`soft_transfer(metric_name=)`. FIX-4 Hellinger /8 sigma^2; universe firewall before any metric
call in every candidate-aware entry point. FIX-5 `strict=True` raise / `strict=False` NaN in
place of the sentinels, `OptimizerRecord` provenance, restart selection in `candidates.py`,
strictly-worse penalty for failed draws in `induced_prior.py`. FIX-6 joint log-sum-exp
weighting, `compute_induced_prior(weighting="uniform" | "likelihood_tilted")` with the three
legacy callers set to uniform for `fit_hmc` draws, finite-input checks in
`average_gp_posterior`. FIX-7 `PRIMARY_METRIC`, `APPENDIX_METRICS`, `WITHDRAWN_CACHES`,
`load_hmc_samples(allow_withdrawn=False)`, appendix-metric warning on the implicit
`run_bms_star` path. FIX-8 `bistar_gp/external_targets.py` (van Bork Targets A and B closed
forms, `check_external_targets`). FIX-9 `aggregate_convention(G, tau, variant)` bit-identical
to the Case A script's arithmetic; `prior_sensitivity_study._boltzmann_posterior` delegates.
Nine test files `tests/test_fix1_*.py` (79 tests). Refuted items stayed out: no E6 failure
gate, no finiteness explanation of the `aggregation_v3.py:77` warnings, no change to the
pooled arithmetic or the `normalize_per_draw=False` default (D60).

**Alternatives considered:** dispatching Codex Astra as implementer (rejected by the author
for this pass); prepending the primary metric to `ExperimentConfig.metrics` (rejected:
`experiments/bms_star_toy.py` slices `metrics[:4]`; appended instead, with on-demand
registration of metrics_v2 so the config-named primary metric resolves); making
`soft_transfer(metric_name=)` required as the work order said (deferred: two package callers
outside the editable set omit it, `metrics_v2.py:398`, `mcse_strategy.py:177`; author accepted
the optional keyword 2026-09-08, required in fix pass 2 with those callers).

**Result:** Case E regression oracle (`experiments/toy_debias_demo.py` on
`paper/case-e-debias`, run against this package) byte-identical to the committed
`runs/toy_debias_demo/` artifacts (sha256 65c9ff5f..., c1153549..., 7096cd6e...). Full suite
at the reviewed pass-1 state: 1327 passed, 3 skipped, 1 failed (the known lock-drift test
`test_committed_dependency_lock_reproduces_at_head`, pypdf). Reviewed by Codex gpt-6-astra
xhigh (REVISE, R1-R10) and a fresh Fable 5.1 instance (APPROVE, F1-F7); adjudication in
`runs/code_review_2026_09/fix1_synthesis.md`; no S1, one S2 (a strict evaluation failure
inside the optimizer's own evaluations was caught as an optimizer fault). Both channels
answered the rewrite question ("delete and implement a more concise version?") with keep and
simplify in place. Pass 1b (next commit) folds the accepted items.

**Status:** pass 1 committed as reviewed; pass 1b follows in the same branch; fix pass 2
(case-A script wiring of `check_external_targets`, Case C convention import, required
`metric_name` with its two callers) OPEN; Kimi K3 and GLM 5.3 outputs on the fix pass pending.

**Update 1 (2026-09-08, pass 1b):** review-round folds applied in this branch after the
Codex and Fable 5.1 reviews (adjudication `runs/code_review_2026_09/fix1_synthesis.md`
revision 2): atomic per-draw accumulation with typed keys and one `_summarize` factory
shared by the MAP and draw paths (`debias.py`; `group_key` deduplicates); `EvaluationFailure`
raised by the evaluators and re-raised by both optimizer handlers, order-independent
`_select_start` over finite objectives, non-finite Hessian stencils flagged
(`laplace_evidence.py`); one `log_weight_ess` routine (NaN for NaN, 0 for absent support),
finite-G validation and class-label cardinality at `soft_transfer` entry,
`_MetricRegistry.__missing__` replacing `_resolve_metric` (`bms_star.py`); sample sites
applied outside the numerical handler and one global shift in `soft_transfer_weighted` with
`instance_scores` on the pre-fix scale (`aggregation_v3.py`); `log_mlls` under uniform
weighting raises (`induced_prior.py`); finite validation before every reduction in
`external_targets.py`. `tests/test_fix1_review_round.py` (17 tests) and three test edits.
Suite in this worktree: 1342 passed, 5 skipped (two fixture-gated pins needing
`FIX1_FIXTURE_DIR`, three environmental), 1 known failure; Case E oracle byte-identical.
`metric_name` stays optional by author disposition (2026-09-08); required in fix pass 2 with
`metrics_v2.py:398` and `mcse_strategy.py:177`. Delta against the reviewed state:
`runs/code_review_2026_09/fix1_bundle/fix1b_delta.diff`.

**Update 2 (2026-09-08, pass 1c):** the two package-only channels reviewed the committed
head `856b911` through OpenRouter (Kimi K3 `moonshotai/kimi-k3` APPROVE K3-1..K3-6; GLM 5.3
`z-ai/glm-5.3` APPROVE F1-F8; record and verification in
`runs/code_review_2026_09/fix1_synthesis.md` revision 3). Folds: finite-G validation at
entry of `soft_transfer_weighted` (the head already raised from `hard_win_statistics`; the
"silent NaN" claim of K3-3/GLM-F4 is refuted as stated) and of `aggregate_convention` (GLM F1:
the Case A script's `tot > 0 else uniform` tail returned a uniform posterior for a NaN
matrix; finite-input arithmetic untouched); a warning on the implicit `run_bms_star` path
when the primary metric is not in the registered roster (K3-1; the roster is unchanged; no
experiment script uses the implicit roster); the clipped conditional variance written back
into the accumulated covariance so `diag(cov) == std**2` under a numerically negative
diagonal (K3-4); an unknown singleton in `DecompositionResult.group` names the component
(GLM F8). Not adopted: `PredictiveList` slice bookkeeping (K3-5; the record is the extraction
history). Tests: three in `tests/test_fix1_review_round.py`, one in `tests/test_fix1_roles.py`.
Suite 1346 passed, 5 skipped, 1 known failure; Case E oracle byte-identical.

==================== AUTHOR ADJUDICATION LEDGER (runs/code_review_2026_09/ledger_draft.md, revision 3) ====================
# Author-adjudication ledger — DRAFT revision 3, 2026-09-06 (Fable)

Revision 3 folds in the Codex channel's independent recommendations
(`codex_recommendations.md`, gpt-6-astra at xhigh, written from an
options-only copy of revision 2). Both repo-access channels now recommend
the same option on every item. Changes from revision 2: Item 3 gains the
suspension option and adopts it; Items 1 and 2 carry the D58 record
mechanics and interval semantics; Item 5 carries an explicit tie rule and
Case C's derivable values; a verified reproducibility finding that neither
review reported is added for the collation; the dependency-lock drift and
the pull-request statuses are recorded as decisions.

Scope: the S1/S2 statistical items that survived the four-channel collation
and both adversarial cross-checks (`COLLATION.md`, `fable_review.md`,
`codex_review.md`, `fable_crosscheck.md`, `codex_crosscheck.md`). Items are
ordered by what they block: 3, 4 and 5 touch READY pull requests and the
frozen notation; 1 and 2 touch the frozen D58 poster record. Nothing here is
fixed, committed, or merged without the author.

---

## Item 3 — Case D's stored comparisons were produced by a sampler that targeted the prior

**Severity / reporters:** S1 recommended (Codex F3 at S2, escalated in the
Fable cross-check); Codex F4 (S2) is the regeneration-path corollary and is
folded in. Cross-verified against history, the D6 record, and current code.

**Established.**
- `experiments/practice_EvansEtAL/results_hmc/` was added in one commit,
  `7026ad6` (2026-02-16), never touched since; `run.py` is unchanged since
  `9015ee4` the same day and calls the package `fit_hmc` (`run.py:45`, `:413`).
- `fit_hmc` at `7026ad6` (`fit.py:149-154`) discards the return values of
  `pyro_sample_from_prior()` and scores the likelihood on the original,
  MAP-fitted modules. `Notes/DECISIONS.md` D6 (2026-07-02) records the
  consequence: "every `fit_hmc` 'posterior' draw was a prior draw", and calls
  the defect pre-existing. No other `fit_hmc` existed before 2026-06-30.
- D6's withdrawal list names `bistar_gp/cache/*.npz` and
  `runs/mauna_loa_sub150_hmc_*` only. The practice artifacts escaped it, and
  D64 (2026-08-11) imported them as "the HMC-mode practice run".
- The historical extractor applied the sampled kernel values by name, so each
  stored "GP draw" is a data-conditioned predictive under hyperparameters
  drawn from the configuration's hyperprior, not from the posterior.
- On current code the single-kernel practice model's sites
  (`covar_module.outputscale_prior`, `covar_module.base_kernel.lengthscale_prior`)
  are dropped by `select_hmc_sites` (`model.py:76-78`) and rejected by
  `apply_hp_value` (`model.py:99-104`); two draws with lengthscales 0.05/2.0
  give byte-identical predictives. The corrected sampler emits exactly those
  names, so regenerating the artifacts today would silently score
  default-kernel predictives (Codex F4).

**Reach.** Section 6 material computed from `bistar_probs` and
`bistar_G_diagnostics`: the winner-count table at τ=1.778 and the 39/49/48
agreement counts; the cohort `mean_G` table and the subject-25 example; the
`raw_draw_wins` table (39.0/39.9/41.5 versus 98.7/94.6/92.1 percent), which
is the carrier the F-D1 rewrite adopted for the asymmetry thesis; the τ-grid
medians (0.581/0.569/0.557 and 0.987); the "known-truth reference levels"
argument. D64's scope decision not to rerun the practice scripts was taken
under the HMC premise. PR #38 was marked READY on these numbers.
**Unaffected:** the BIC counts (18/32, 41 of 50), the MAP-conditional
deviation reconstruction and its early-trial localization (the stored
`gp_hyperparameters` come from `fit_map`, which worked), the affine identity
(algebraic on the stored values), and the F1/F2 geometry framing.

**Decision required.** Whether the stored-comparison material stays in Case
D, and in what form; the status of PR #38 while that is decided; and a dated
D6 addendum extending the withdrawal to `results_hmc/`.

**Options.**
- (i) *Withdraw* the stored-comparison material outright. Section 6 keeps
  the BIC counts, the reconstruction, and the geometry prose; loses the three
  tables, the example, the medians, and the reference-levels argument. No
  compute; a substantial rewrite; the asymmetry thesis has no carrier.
- (ii) *Relabel.* Keep every number, describe the draws as data-conditioned
  predictives under hyperprior-drawn hyperparameters (sampler of record D6),
  and reinterpret the tables as hyperprior-sensitivity reference material.
  Cheapest; but it changes the question the tables answer, the F-D1/F-D2
  sign-offs were given under the HMC reading, and a reinterpreted comparison
  left in the live argument can survive into submission.
- (iii) *Regenerate* on the corrected sampler. Prerequisites: fix the
  single-kernel site handling with a sensitivity test (fix pass 1); harden
  the practice producer (explicit `--demo --mode hmc --output_dir <new>`
  with a reviewed seed and settings contract, retained draws, sampler
  identity recorded, the broad exception handlers removed); split the
  reconstruction and comparison input paths in `regret_curves_mopen.py`; run
  the 50 subjects × 3 configurations on `nuts_e1` (new local compute, order
  of an hour as a planning estimate); re-derive every section-6 stored
  number; a fresh §4 review round for Case D; dated addenda to D64 (scope
  premise) and D6 (withdrawal list). Keep the comparison design and the
  legacy metric identities fixed; a new primary-metric analysis is a
  separate scope choice.
- (iv) *(ii) now, (iii) before submission.*
- (v) *Suspend now, regenerate the comparison layer as the endpoint*
  (Codex): withdraw the posterior interpretation immediately, preserve the
  BIC and MAP baselines as explicitly identified inputs, keep the old
  comparisons as historical evidence, and replace only the comparison layer
  with the regenerated results. Unlike (iv), no reinterpreted comparison
  stays in the live argument while the run is pending. A failed or
  inconclusive replacement yields a narrower section, not a rescued one.

**Recommended default:** (v), with (iii) as the endpoint (both channels).
Return PR #38 to Draft now; write the D6 addendum now regardless of the
choice; decide Item 4 before the run; check whether `results_diag/` and
`results_hierarchical/` are pre-2026-07-02 HMC products that belong on the
same withdrawal list. If the schedule cannot hold a defensible run, take
(i) rather than (ii).

---

## Item 4 — The computed table row is not the row the frozen notation defines

**Severity / reporters:** S2 (Codex F5; cross-check confirmed and quantified;
revision-1 wording corrected by Codex).

**Established.** `extract_gp_predictives` (`bms_star.py:323-337`) forms, per
hyperparameter draw η, the predictive N(m_η, S_η + σ²_η I) with the latent
function integrated out; it never draws f. `docs/paper-sie-jmp/00-notation.md`
("a sampled function f with observation variance defines ψ = N(f(x), σ²_ψ I)")
and §2.1 ("draw a function conditional on them, and combine that function
with observation variance to obtain one ψ") define a sampled-function row.
On E7's exact path (same caches, seeds, grid, candidates; implemented G
reproduced to 0.0), with the notation's construction implemented literally
as one function draw per hyperparameter draw, Linear / Sinusoidal /
Sin+Linear / Quadratic:

| Row | pooled τ=1 | pooled τ=0.1 | Eq.-4 τ=1 | hard-win | mean G |
|---|---|---|---|---|---|
| implemented (the artifacts) | 0.183 / 0.192 / **0.441** / 0.184 | 0.121 / 0.125 / **0.634** / 0.121 | 0.159 / 0.169 / 0.513 / 0.159 | 0.012 / 0.014 / 0.973 / 0.001 | 1.51 / 1.45 / 0.29 / 1.51 |
| notation row, one sampled f per draw (seed 0; 10 seeds in brackets) | 0.158 / 0.176 / **0.509** [0.501–0.509] / 0.158 | 0.249 / 0.233 / **0.272** [0.23–0.29; first in 2 of 10 seeds] / 0.246 | 0.109 / 0.128 / 0.654 / 0.109 | 0.012 / 0.018 / 0.963 / 0.007 | 3.15 / 2.87 / 0.88 / 3.15 |

Under the notation's own definition the Case A headline moves from 0.441 to
0.50–0.51; the pooled τ=0.1 preference for Sin+Linear (0.634) disappears
into a four-way near-tie whose winner depends on the function-draw seed;
the absolute G scale carrying the M-open signal roughly doubles; hard-win
fractions and Eq.-4 orderings are stable. The sampled function adds a
candidate-independent per-draw term that pooled aggregation retains and
Eq.-4 aggregation cancels, so the row choice interacts with the D60 dial at
low τ. The exp(−E_f[G]/τ) variant tabulated in revision 1 is a different
estimator from the notation's construction and is excluded from the claim.

**Reach.** Every soft-transfer number in Case A (E7) and Case C; the stored
Case D G values (same predictive rows, Item 3); Case B's Ḡ, which is the MAP
predictive row; the M2bR banner's SIR 0.441 anchor and its continuity with
D18/D60/D61; §2.2's projection paragraph, whose "one scalar noise variance
shared across locations" case is exactly the notation row and never holds
on the implemented row (posterior variance varies across locations). Not
Case E, whose latent-function decomposition estimand is defined separately.

**Decision required.** Which row definition governs the manuscript.

**Options.**
- (A) *Keep the implemented row and amend the definition.* Notation ψ row
  and §2.1 rewritten as "each hyperparameter draw defines one pattern,
  ψ(η; D) = N(m_η(D), S_η(D) + σ²_η I), the hyperparameter-conditional
  predictive with the latent function integrated out"; the prior-only
  construction described separately; §2.2's scalar-variance clause
  re-scoped as the special case. All committed numbers stand; no compute.
- (B) *Adopt the notation's sampled-function row.* Implement f-draws in the
  extractor; regenerate E7 and Case C; redesign Case B's Ḡ path; Case D
  cannot follow except through Item 3. Headline 0.441 becomes about 0.50,
  the pooled τ=0.1 row becomes a seed-dependent near-tie, absolute G
  doubles, continuity with every ratified number is lost; fresh rounds for
  A, B, C, and the synthesis; function-draw Monte Carlo noise enters every
  comparison.
- (C) *(A) plus a disclosed, reproducible sensitivity*: a committed script
  and artifact with the exact E7 inputs, hashes, and function seeds, cited
  once with the statement that the row definition is a convention whose
  low-τ pooled consequences are visible there.

**Recommended default:** (C) (both channels), under these conditions from
the Codex channel, which I adopt: give the substantive predictive-pattern
rationale before the continuity argument, so the choice does not read as
post-hoc definition selection; amend the Ḡ entry in the same change,
stating that Case B retains one MAP predictive so the additional averaging
gap is zero there; align the notation's unconditional τ-limit gloss with the
synthesis's convention-dependent, unique-winner qualification; commit a
baseline for `00-notation.md` first (it is untracked on every branch); and
budget a narrow Case A methods review in addition to the synthesis review,
not "synthesis text only".

---

## Item 5 — Section 2.4's reporting commitment is unmet by Case A's own table and artifact

**Severity / reporters:** S2 (statistical). Fable F3, promoted after Codex's
independent confirmation that §2.4 calls for tau-free draw-win fractions in
every soft-transfer table and a draw-level diagnostic beside appendix
`kl_forward` results, while E7's script and saved artifact carry neither.
Codex's T4 independently measured the same concentration.

**Established.** `run_bms_star` computes draw wins and only prints them
(`bms_star.py:545-549`); `_sir_bms` returns `hard_win_fractions` and E7
discards them; `BMSStarResult` carries no weight ESS. On E7's exact path,
the per-candidate effective number of draws behind the pooled weights (of
1000): pw_kl_vcal τ=1 669/685/978/669 (the headline is not concentrated);
τ=0.1 34/38/551/34; appendix `kl_forward` τ=1 6.1/8.4/104/6.1 and τ=0.1
1.15/2.25/2.47/1.14. Hard-win fractions under pw_kl_vcal are
0.012/0.014/0.973/0.001, with `argmin` silently awarding ties to the first
candidate.

**Reach.** Case A §3.4 (PR #39, READY): the pooled tables, and the appendix
sentence that the Sin+Linear `kl_forward` weight "collapses to approximately
0.000", which is a one-to-eight-draw statement;
`runs/e7_convention_sensitivity/results.json`. Case C's Table 5.1 (PR #37,
READY) is also a soft-transfer table and falls under the same rule; its
values are derivable from the saved counts without rerunning the LOO
sampler: attainment 1.000 / 0.999, strict unique wins 0.001 / 0, tie
fraction 0.999, equal-split credit 0.5005 / 0.4995.

**Decision required.** Whether the commitment is met by extending the E7
artifact, §3.4, and Case C's table, or stated as a limitation; and the tie
rule.

**Options.**
- (a) *Meet it.* `BMSStarResult` carries per-candidate weight ESS, tie-aware
  hard-win credit, attainment fractions, and tie frequency; E7 persists
  them (rerun seconds; every existing number bit-exact); §3.4 quotes the
  fractions and puts the ESS beside the appendix sentence; Case C gains one
  diagnostic line derived from its saved counts, with no LOO rerun.
- (b) *State a limitation* in §2.4 or §3.4 without changing the artifact.

**Tie rule (Codex, adopted):** exact ties on validated finite scores; report
equal-split credit h_j = mean_i[1(j ∈ T_i)/|T_i|] (sums to one), attainment
a_j = mean_i[1(j ∈ T_i)], and the tied-row fraction; never let candidate
order break a tie; introduce new field names rather than redefining the
archived `raw_draw_wins`. Pin with G = [[0, 0], [10, 11]]: attainment
[1, 0.5], split credit [0.75, 0.25], limiting row-min [2/3, 1/3], limiting
pooled [0.5, 0.5].

**Recommended default:** (a) with the tie rule (both channels). Label the
ESS as a concentration summary, not an MCMC ESS or an error bar.

---

## Item 1 — D58 Mauna cards draw bands that are not posterior bands (S1-a)

**Severity / reporters:** S1. All four channels (Kimi F1, GLM F1, Fable F1,
Codex F1); driver T2. Both repo channels opened the committed artifact.

**Established.** `decompose_model_hmc` discards each draw's conditional
covariance (`debias.py:206`) and reports `std` as the across-draw spread of
conditional means (`:222-225`; same in `decompose_model_mcmc`, `:131-144`).
Recomputing from the committed `samples.npz` (200 draws, training-only
loader, no new inference, 12 s) reproduces the committed `comp__*__std` and
`full_std` to 7.1e-13, and the law-of-total-variance sd is, in ppm at the
grid median: trend 9.34 against 0.650 committed (14.4×), seasonal 9.34
against 0.648 (14.4×), medium_term 0.177 against 0.036 (4.9×), full GP
0.132 against 0.014 (9.3×, the band card 6a labels "95% CI"; component bands
are labelled "±2 SE"). The cause of the large trend/seasonal within-draw
spread is structural: the period-1 periodic kernel with lengthscale ≈1.5
carries a near-constant direction that trades against the RBF trend's level,
so the split is unidentified within a draw (each ≈9.3 ppm) while the sum is
tight (0.13 ppm). Mean curves are unaffected.

**Reach.** `runs/poster_d58/fit_full461_seed0/figures/card6..card8` (render
evidence `783e434`; closeout D58 Update 4 at `71540836`); the byte-identical
pins in `poster/assets/d58/` (poster-repo branch
`handoff/d58-figures-11572645`, commit `7401281`, local-only); the older
`CogSci Poster/Fig X` images from the same routine. **Not the manuscript:**
Case E used the correct construction and the toy poster figures used
`honest_band_decomposition.py`.

**Decision required.** (1) Which of the two image sets the presented poster
carried, which fixes the dissemination correction but not the defect in
the pinned set. (2) The correction path under the D58 record process
(`docs/d58-poster-execution-protocol.md`). (3) The interval semantics of any
corrected band. (4) Whether the corrected figures disclose the level-split
non-identifiability or the modeling change to remove it.

**Options.**
- (A) *Addendum only.* D58 Update 5 records the band semantics; the pinned
  figures stay. No compute; the record's only render stays wrong.
- (B) *Corrected pinned set plus addendum, as a separately authorized
  correction act.* Recompute from the committed `samples.npz`, the hashed
  training arrays, grid, and normalization metadata with per-draw
  conditional moments retained; a new correction driver, since the old
  renderer only rebuilds the incomplete saved arrays and writes into the
  original `figures/`; a new output namespace outside the original fit
  directory, whose closed-world census permits only the existing `figures/`;
  input hashes, code head, moment schema, tolerances, and new figure hashes
  recorded; originals byte-pinned. Interval semantics: pointwise central 95
  percent posterior credible intervals of the retained draw mixture for the
  latent process, conditional on the recorded fit (the Case E CDF-bisection
  construction), which makes the "95%" label true; if only total variance is
  implemented, the truthful label is "±2 posterior SD" without "95%" or
  "SE". The trend and seasonal panels will show bands of roughly ±19 ppm
  around a cycle of a few ppm; that is what the posterior says under this
  kernel and must not be suppressed by centering or refitting.
- (C) *(B) plus a modeling change* (a seasonal component with a fixed level)
  to make the split identifiable. Requires a new Mauna fit under its own
  preregistration; companion-line work, not D58.
- Interim option (Codex): a means-only replacement that omits uncertainty
  explicitly, if a faithful correction cannot be produced under an
  authorized act in time.

**Recommended default:** (B) with the mixture-quantile construction and the
level-split disclosure in Update 5 (both channels); (C) noted as
companion-line work; D58's spent PREP/POST rounds do not authorize this act,
so commission a new bounded correction, evidence commit, and poster hand-off
on a new branch in that repository; identify the presented poster's actual
assets before specifying the public-facing correction, without letting that
question block the corrected evidence.

---

## Item 2 — Grouped "truth"/"bias" bands assume independent components (S1-b)

**Severity / reporters:** S1. Codex F2; the grouping half of Fable F1; Kimi
and GLM supplied the contrast with the MAP variant that retains
cross-covariance.

**Established.** `compute_debiased` (`bistar_debias_mauna_loa.py:97`, `:106`)
forms grouped uncertainty as `sqrt(Σ comp.std²)` under an "independent
components" comment. Assigning every component to truth (the Believer
interpretation) must reproduce the full posterior band. Two magnitudes,
both in ppm at the grid median:
- *The pinned cards as rendered* (committed mean-spread marginals, summed
  independently) against the corrected joint SD: Believer 0.919 against
  0.132 (7× too wide); Moderate 0.918 against 0.132 (7× too wide); Skeptic
  0.648 against 9.34 (14× too narrow; a single component, so Item 1 alone).
  Codex's 2294× is the same comparison in variance units on the committed
  rows.
- *The grouping defect in isolation* (independence sum on the corrected
  marginals 9.34/9.34/0.18): Believer and Moderate both 13.2 against a joint
  0.132, 100× too wide in SD.
Repairing Item 1's marginals alone therefore makes the grouped bands worse,
not better; the grouped band needs the joint posterior of the summed group
blocks per draw, which `decomposition.npz` does not retain and `samples.npz`
allows.

**Reach.** Cards 7 and 8 (row 0 of card 7, both card-8 strips) and the
older `bistar_three_interpretations_hmc.png` / `bistar_debiased_ppm_hmc.png`.
Not the manuscript.

**Decision required.** Whether the grouped bands are corrected in the same
act as Item 1 or only disclosed.

**Options.** Fold into Item 1 (B), or into (A) with grouped uncertainty
omitted until joint moments exist (Codex's interim).

**Recommended default:** fold into Item 1 (B) (both channels), with the
group conditioning done per draw on the summed group blocks using the
Cholesky factor of the entire fitted training covariance plus noise (never a
group-only factorization), symmetric for truth and removed-bias groups, and
the all-components-truth identity holding for means, total variance, and
mixture quantiles as the acceptance condition before any grouped card is
published. Add that identity, the singleton and empty-group identities, and
an anticorrelated two-component fixture to the test suite.

---

## New finding for the collation (reproducibility, S3; not an adjudication item)

`paper/case-c-haaf:experiments/haaf_nested_constraint.py:46` imports
`e7_convention_sensitivity`, which exists only on `paper/case-a-vanbork`
(absent from `main`, `paper/case-b-occam-dial`, and Case C's own branch;
verified with `git ls-tree`). Case C's committed artifact therefore does
not regenerate from its own branch; the Fable rerun succeeded only because
both scripts were copied into one scratch directory. Found by the Codex
recommendations pass, verified by Fable. Fix: move the aggregation
conventions into the package (fix pass 1, FIX-9) and have both scripts
import them; merge order A before C.

## Other decisions recorded

- **Dependency-lock drift.** Remove `pypdf` from the designated interpreter
  (`/opt/homebrew/Caskroom/miniconda/base/bin/python3.13`, which the freeze
  test targets) and keep PDF tooling elsewhere; do not refresh the lock or
  weaken the test (both channels).
- **Pull-request statuses.** #38 to Draft now; #39 and #37 reopen for the
  bounded reporting amendments of Item 5 and the Item 4 sensitivity; #36
  needs a refreshed dependency and wording verification after the package
  fixes merge, without treating its numbers as withdrawn; #40 and #41 stay
  Draft until their own ledger items close.

## Items considered and deliberately not placed on this ledger

- **Codex F6 / Fable F4 (Ḡ surrogate and notation).** Folded into Item 4's
  notation change.
- **Codex F7 (Hellinger variants, S2).** Fix pass 1; no adjudication.
- **Codex F4.** Folded into Item 3 as the regeneration prerequisite.
- **Fable F8 (metric defaults, S4).** Fix pass 1. The two channels differ
  only on scope: Codex enforces roles at manuscript-facing entry points and
  leaves generic defaults; Fable additionally adds the primary metric to
  `ExperimentConfig.metrics`. Both go to the fix pass; no author decision.

## Suggested record actions once the items are decided

D6 addendum (withdrawal list), D64 addendum (scope premise and chosen
option), D58 Update 5 (both defects, the interval construction, original and
corrected hashes, presented-poster provenance, each act in the past tense
after it happens), the notation baseline commit followed by the ψ, Ḡ, and
τ-limit amendments, the PR status changes above, and the fix-pass lineage:
fix pass 1 (package, decision-independent; dispatch
`docs/paper-sie-jmp/prompts/code-review-fix1.txt`) before any regeneration,
then fix pass 2 (decision-gated script and artifact work: E7 extension and
Case C diagnostic line, the Item 4 sensitivity artifact, the practice
producer and Case D regeneration, the D58 correction act).

==================== FIX-PASS SYNTHESIS (runs/code_review_2026_09/fix1_synthesis.md, revision 3) ====================
# Fix pass 1: review-round synthesis (revision 3, 2026-09-08, Fable)

Revision 3 adds the two package-only channels (Kimi K3, GLM 5.3), their verification, and fix pass 1c. Revisions 1 and 2 follow unchanged below the revision-3 section.

## Revision 3: package-only channels, verification, pass 1c

### Channels, complete

| Channel | Access | Verdict | Output |
|---|---|---|---|
| Codex gpt-6-astra xhigh | full repo | REVISE (R1-R10) | `fix1_codex_review.md` |
| Fable 5.1 fresh instance | full repo | APPROVE (F1-F7) | `fix1_fable51_review.md` |
| Kimi K3 (`moonshotai/kimi-k3`, OpenRouter, package-only) | brief + HANDOFF §2-3 + section 02 + notation + work order + report + cumulative diff 71540836..856b911 (294 KB, 80.6k prompt tokens) | APPROVE (K3-1..K3-6) | `fix1_kimi_k3_review.md` |
| GLM 5.3 (`z-ai/glm-5.3`, OpenRouter, package-only, same package) | same | APPROVE (F1-F8, GLM numbering) | `fix1_glm_5_3_review.md` |

Both package-only channels reviewed the committed head `856b911` (pass 1 + 1b). Their first attempts returned no usable text because both are thinking models and spent the whole completion budget on reasoning (GLM: 19998 of 20000 tokens, one character of answer); the rerun capped reasoning and raised the answer budget (`scratchpad/fix1_review/openrouter_review.py`; raw responses kept beside the outputs).

### Verification of the package-only findings (probes on the committed head, `probe_round3.py`)

| ID | Claim | Status at `856b911` | Adjudicated | Pass 1c |
|---|---|---|---|---|
| K3-1 | implicit `run_bms_star(metric_names=None)` roster lacks `pw_kl_vcal` in a process that never imported metrics_v2, with no warning | CONFIRMED (fresh-process probe: False) | S4: pre-existing behaviour (identical before the pass); no experiment script uses the implicit roster (all pass explicit lists) | warning added when the primary metric is absent; roster unchanged; cold-process pin |
| K3-2 = GLM F2 = R4/F5 | `metric_name` optional | disclosed | S4, author accepted optional 2026-09-08 | none |
| K3-3 = GLM F4 | weighted path returns all-NaN posteriors silently on a NaN G | REFUTED as stated: the head raises `ValueError` from `hard_win_statistics` | S4 (message names a helper) | entry guard with the caller's name; pin |
| K3-4 | `diag(cov) != std**2` when a conditional variance is numerically negative | CONFIRMED (0.019879 vs 0.019880 with an injected -1e-6 diagonal) | S4 | clipped diagonal written back into the accumulated covariance; pin |
| K3-5 | `PredictiveList` slicing drops the bookkeeping | CONFIRMED by design | S4, not adopted: the bookkeeping is the extraction history (Codex recommended exactly this); noted in the report | none |
| K3-6 | downstream parsing of single-kernel site names unverified | REFUTED: pinned by `test_fix1_sites.py` and by Fable 5.1's sensitivity probe | not a finding | none |
| GLM F1 | `aggregate_convention` returns a UNIFORM posterior for NaN or +inf under pooled/rowmin | CONFIRMED ([0.5, 0.5]; expected_posterior gives NaN) | S3 (latent; package-produced G is finite) | finite-G guard at entry; finite-input arithmetic untouched; pin |
| GLM F3 | Mauna call-site deviation | justified | S4 | none |
| GLM F5 | report sentence "a legacy positional call still works" false after 1b | CONFIRMED | S4 | report correction |
| GLM F6 | report arithmetic 1253 + 79 | CONFIRMED (pre-existing collected was 1252) | S4 | report correction |
| GLM F7 | `samples` dual meaning | justified (poster driver read-only) | S4, fix pass 2 | report note |
| GLM F8 | unknown singleton gets a misleading "not requested" message | CONFIRMED | S4 | names the unknown component; pin |

GLM's NEEDS-REPO-VERIFICATION items (suite counts, oracle hashes, the two callers outside the editable set, `_guarded_neg_log` NaN handling) are all settled by the repo-access channels' runs and by the pinned tests.

### Fix pass 1c (applied 2026-09-08, same branch)

Files: `bistar_gp/{aggregation_v3,bms_star,debias}.py`; `tests/test_fix1_review_round.py` (+3), `tests/test_fix1_roles.py` (+1). Verification: full suite in the fix worktree, plain run: 1346 passed, 5 skipped, 1 failed (the known dependency-lock drift test), 493.11 s (8 min 13 s); collected 1352 = 1348 + 4 new. Log: scratchpad `fixpass1/full_suite_1c_worktree.log`. Case E oracle: byte-identical against the worktree package (three sha256 identical, 60.8 s).

### Verdict, all four channels

Two APPROVE (Fable 5.1, Kimi K3, GLM 5.3 make three) and one REVISE (Codex) whose queue is closed by pass 1b; no S1 at any point; the one S2 (R7) closed in 1b; every S3 closed in 1b or 1c except none outstanding. On (b), all four channels: keep the pass, do not rewrite; pass 1b is the concise form. Remaining for fix pass 2: required `metric_name` with its two callers, removal of the `samples` dual meaning once the poster driver is editable, wiring `check_external_targets` into the case-A script, replacing Case C's cross-branch import with `aggregate_convention`, and a trim of provenance prose in docstrings.

### Fix pass 2 note on the required `metric_name` (2026-09-08)

The two package callers that omit the metric are not equal. `metrics_v2.py:398`
has the name in scope and can pass it. `mcse_strategy.py:177` aggregates a
pooled G matrix inside `mcse_strategy_estimate(G, tau, names, ...)`, which
receives no metric identity at all; requiring the keyword there means adding
a `metric_name` parameter to an M2c function (`docs/m2c_freeze/
gtoy_profile_freeze_v1.17.json` records its contract and
`tests/test_m2c_mcse_strategy.py` pins it) or stamping a placeholder, which is
what the work order forbade. The author's options for fix pass 2: (i) keep
`metric_name` optional as a documented rule ("a pure aggregation over a G
matrix carries the metric identity only when the caller has it") and pass it
at the one caller that has it; (ii) thread `metric_name` through
`mcse_strategy_estimate` as an optional keyword recorded on its report. Both
leave the M2c arithmetic untouched. Pushed as PR #42 with this note; no
pass-2 code was written.

---

# Revision 2 (2026-09-08)


Revision 1 (2026-09-07) covered the Codex channel. Revision 2 adds the
Fable 5.1 channel, records the adjudication of both, and reports fix pass
1b, which folds the accepted items into the same uncommitted worktree.
Scope: `/Users/sc8918/Documents/GitHub/bistar_gp_c-fix` (branch
`fix/code-review-2026-09`, base `71540836`). Questions: (a) is the recent
code correct; (b) should the fix be deleted and re-implemented more
concisely.

## Channels

| Channel | Status | Output |
|---|---|---|
| Codex gpt-6-astra xhigh (full repo; suite, oracle, probes) | landed 2026-09-07 | `fix1_codex_review.md` (REVISE, R1-R10) |
| Fable 5.1 fresh instance (subagent, no shared context; full repo; suite, oracle, probes) | landed 2026-09-08 | `fix1_fable51_review.md` (APPROVE, F1-F7) |
| Fable (implementer's self-check; not an independent channel) | | SC-1 = R8(i) = F1 |
| Kimi K3, GLM 5.3 (package-only) | pending, author-run | brief `docs/paper-sie-jmp/prompts/code-review-fix1-review.txt`; bundle `fix1_bundle/` |

The user chose Fable 5.1 for the fourth slot instead of Opus. Its
independence is one of context, not of model: it saw none of my reasoning
or the other channel's file (it was told not to open them, and its report
says it did not), so its agreement with Codex on R8(i)/F1 and R4/F5 counts
as two-reporter under HANDOFF-cases §4.

## Verification of the two channels

Codex: all ten probes rerun with the fix worktree forced onto the path;
every line reproduced (revision 1). Fable 5.1: every probe asserted the
package path itself; its seven findings were checked by reading the cited
lines and, for F1, by my own earlier probe; each is now pinned by a test
that discriminates the pass-1 code from pass 1b. Both channels reran the
suite (Codex 1327/3/1 with the fixture variable, Fable 1325/5/1 without)
and the Case E oracle (three sha256 identical).

## (a) Findings, adjudicated, with pass 1b disposition

Severity: S1 manuscript number wrong; S2 wrong under a reachable
configuration; S3 latent, guarded; S4 hygiene. Reachability means a paper
path or a documented call pattern; injected exceptions and offsets of 1e12
do not count. Codex graded six items S2 that I grade S3/S4 on that basis;
Fable 5.1 graded everything S3/S4 independently. The fix list is the same
under either reading.

| ID | Channels | Grade (Codex / Fable 5.1 / adjudicated) | Pass 1b disposition |
|---|---|---|---|
| R1 unknown site swallowed to -inf in `compute_log_marginal_likelihoods` | Codex | S2 / - / S3 (all draws share keys, so the all-absent guard raises; `extract_gp_predictives` cannot emit an unknown key) | FIXED: sites applied outside the numeric handler; pin R1 |
| R2 non-atomic `add_draw` under `strict=False` | Codex | S2 / - / S3 (needs an injected failure) | FIXED: every target conditioned into a per-draw record, committed together; pin R2 |
| R3 accumulator key collision (`"a,b"`, `"__full__"`) | Codex | S2 / - / S4 | FIXED: typed tuple keys; pin R3 |
| F3 duplicate names in a group double-count | Fable 5.1 | - / S4 / S4 | FIXED: `group_key` deduplicates (Fable's one-line form); pin in R3 test |
| R4 = F5 `metric_name` optional versus "required" | Codex + Fable 5.1 (two-reporter) | S4 / S4 / S4, author decision | NOT CHANGED. Both channels recommend: accept the optional keyword now, make it required in fix pass 2 together with the two callers outside the editable set (`metrics_v2.py:398`, `mcse_strategy.py:177`). Proposed disposition below. |
| R5 class-label cardinality unchecked | Codex | S2 / - / S4 (no caller passes `class_names`) | FIXED: one label per column, no repeats, plus an `instance_names` length check; pin R5 |
| R6 large common offsets cancel imprecisely in weighted posterior and ESS | Codex | S2 / - / S3 (8e-13 at offset 1e4, 2e-11 at 1e6, visible only at 1e12) | FIXED: one global shift before the log-sum-exps; one ESS routine with per-column max; pins R6 (exact at 1e16) |
| R7 strict evaluation failure inside the optimizer becomes a flagged start-point expansion | Codex | S2 / - / S2 | FIXED: `EvaluationFailure(RuntimeError)` raised by the evaluators and re-raised by both optimizer handlers; genuine optimizer faults keep their fallback; pin R7 |
| R8(i) = F1 = SC-1 start-order dependence under NaN | Codex + Fable 5.1 (two-reporter) | S2 / S3 / S3 | FIXED: `_select_start` picks the minimum over finite objectives, NaN only when all are non-finite; pin R8 |
| R8(ii) NaN evidence reported with `converged=True` | Codex | S2 / - / S3 | FIXED: Hessian finiteness checked before the log-determinant; record kept, `converged` cleared; pin R8 |
| R8(iii) `_weight_ess` returns 0 for NaN and for absent support alike | Codex | S2 / - / S4 | FIXED: `log_weight_ess` returns NaN for NaN, 0 for all -inf; pin |
| R9 target checker accepts a NaN column | Codex | S2 / - / S3 | FIXED: finite validation of the selected row and the stored field before any reduction; pins R9 (each column, both blocks, stored field) |
| R10 covariance pin checks the diagonal only | Codex | S4 / - / S4 | FIXED: full-matrix pin against direct conditioning plus the between-draw covariance; the fixture has off-diagonal between-draw terms |
| F2 `log_mlls` under the default uniform weighting is discarded with a warning (legacy positional calls run a different estimator) | Fable 5.1 | - / S3 / S3 | FIXED: the combination raises; the warning branch is gone; pin in `test_fix1_weighting.py` |
| F4 `soft_transfer` now raises on non-finite G (undisclosed, unpinned, helper-named message) | Fable 5.1 | - / S4 / S4 | FIXED: validated at `soft_transfer` entry with its own message; pin; disclosed here (pre-fix returned a uniform posterior; `compute_G_matrix` never emits non-finite values) |
| F6 two fixture-gated pins skip in the plain suite (1325/5 versus the report's 1327/3) | Fable 5.1 | - / S4 / S4 | DOCUMENTED: both counts stated in the report; the embedded values and inline arithmetic keep the substance exercised without the variable |
| F7 sentinel test does not assert the all-NaN posterior semantics | Fable 5.1 | - / S4 / S4 | FIXED: assertion and `ModelPosteriorResult` docstring |
| Codex firewall suggestion (prove "before any metric call") | Codex | S4 | FIXED: counting-metric pin |
| Codex non-findings: `instance_scores` scale, report's `rng` misattribution, `samples` rationale | Codex | S4 | scores restored to the pre-fix scale (pin); report addendum carries the other two |

No S1 at any point. Verdict on (a): the pass computes what the work order
and the manuscript require; the one S2 (R7) and every S3/S4 above are
closed by pass 1b except R4/F5, which is the author's call.

## (b) A better, more concise, more elegant fix?

Both channels: do not delete and re-implement. Codex: SIMPLIFY IN PLACE for
FIX-1, 2, 3, 5, 6, 8, KEEP for 4, 7, 9. Fable 5.1: KEEP overall, SIMPLIFY
IN PLACE for FIX-2, 5, 6, and two optional micro-simplifications (a
single-draw helper; a metric registry with `__missing__`). Convergence is
complete on the verdict and near-complete on the means:

- Both name the duplicated `ComponentResult` packaging in `debias.py` as
  the accretion. Pass 1b routes the MAP path, the accumulator, the full
  posterior and the groups through one `_summarize` factory (Codex's
  "summary constructor", Fable's `_single_draw` helper), with zero
  numerical change (the MAP path stays bit-identical: sqrt of the same
  floored variances). Fable 5.1 explicitly rejected routing MAP through the
  accumulator because the accumulator symmetrizes and floors at 0; pass 1b
  does not do that.
- Both want the `strict` flag kept explicit rather than moved onto
  `ModelParameterSpace` or a policy object; both want a distinct evaluation
  exception that the optimizer handlers cannot swallow. Done.
- Codex wants one ESS helper shared by the weighted path and
  `boltzmann_weight_ess`; the package had three copies (laplace, bms_star,
  inline). Pass 1b has one, `log_weight_ess`, used by all three.
- Fable 5.1's `_MetricRegistry.__missing__` replaces `_resolve_metric`
  (18 lines) with 8 and covers every `METRICS[name]` site in the package,
  not only `compute_G_matrix`. Adopted.
- Both keep FIX-9's six duplicated pooled lines under the bit-identity
  test rather than couple `soft_transfer` to `aggregate_convention`. Kept.
- Divergence, minor: Codex would reject repeated group members; Fable 5.1
  would deduplicate. Pass 1b deduplicates (shorter, no error surface).
- Fable 5.1 also asks for less provenance prose in docstrings (18 "2026-09"
  and 26 "FIX-n" mentions). Not done in 1b; a trim is safe to do at commit
  time or in pass 2, and Notes/DECISIONS.md is the right home for the
  review history.

Recommendation on the author's question ("delete this fix and implement a
better, more concise, more elegant version?"): no. Keep the pass; pass 1b
is the concise version of it.

## Fix pass 1b (applied 2026-09-08, same worktree, uncommitted)

Files: `bistar_gp/{aggregation_v3,bms_star,debias,external_targets,induced_prior,laplace_evidence}.py`;
`tests/{test_fix1_conventions,test_fix1_sentinels,test_fix1_weighting}.py` edited;
`tests/test_fix1_review_round.py` new (17 tests, R1-R10 + F2-F4 + firewall).
Delta against the reviewed pass-1 state: `fix1_bundle/fix1b_delta.diff`;
cumulative base-to-now: `fix1_bundle/fix1b_cumulative_tracked.diff`,
`fix1_bundle/fix1b_status.txt`.

Verification: full suite in the fix worktree, plain run (no fixture variable): 1342 passed, 5 skipped, 1 failed, 466.06 s (7 min 46 s); the failure is the known `test_m2cr_environment_freeze.py::test_committed_dependency_lock_reproduces_at_head`; the skips are the two fixture-gated pins plus the three pre-existing environmental skips; collected 1348 = 1331 + 17 new. The two fixture-gated files pass with `FIX1_FIXTURE_DIR=<scratch>/fixpass1/fixtures` (run separately). Log: scratchpad `fixpass1/full_suite_1b_worktree.log`. Case E oracle against the synced
worktree package: three sha256 identical (60.3 s). Pass 1b was developed on
a scratch copy while the Fable 5.1 reviewer read the worktree, then copied
back file-for-file (post-sync `diff -rq` empty).

## Author decisions

1. R4/F5: proposed disposition, from both channels: accept `metric_name`
   optional in this commit; fix pass 2 makes it required and migrates
   `bistar_gp/metrics_v2.py:398` and `bistar_gp/mcse_strategy.py:177`.
2. Severity record: Codex's S2 grades versus the adjudicated S3/S4 (table
   above); the fix list is unaffected.
3. Commit shape: one commit (pass 1 + 1b, as the worktree now stands) with
   this synthesis and the two channel reviews cited, or two commits from
   the bundle's two diffs. The reviewed pass-1 state is reconstructible
   from `fix1_bundle/fix1_tracked.diff` + `fix1_new_files.txt`.
4. Kimi K3 and GLM 5.3: still pending; revision 3 when they land.

## Dispositions (2026-09-08, author)

1. R4/F5: `metric_name` accepted optional in this commit; fix pass 2 makes it
   required together with `bistar_gp/metrics_v2.py:398` and
   `bistar_gp/mcse_strategy.py:177`.
2. Severity record: the adjudicated grades in the table stand; each channel's
   own grades remain in its file.
3. Commit shape: two code commits on `fix/code-review-2026-09` (pass 1 exactly
   as reviewed, then pass 1b) followed by this record; D68 in
   `Notes/DECISIONS.md` with Update 1 for pass 1b.
4. Kimi K3 and GLM 5.3 outputs on the fix pass: to be obtained through
   OpenRouter with the package-only brief and folded into revision 3.
