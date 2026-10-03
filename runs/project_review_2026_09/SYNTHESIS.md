# Project review 2026-09-26: synthesis (revision 1.3, Fable, 2026-09-26)

Revision 1.1 folds in the Opus channel (landed after revision 1) and the
verifications of its single-reporter claims; revision 1's text is kept and
amended in place, with the new items marked (Opus). Revision 1.2 adds
section 9: the plan check by Codex gpt-6-astra xhigh
(`codex_astra_plan_check.md`, PLAN OK WITH AMENDMENTS), the verification of
its factual claims, and the amended plan. Where section 9 and sections 5-6
differ, section 9 governs. Revision 1.3 adds section 10: the independent
Opus 5.5 check of Astra's amendments (`opus_plan_check.md`), Fable's
verification of its claims, and the final adopted changes; where section 10
and section 9 differ, section 10 governs.

Target: fix-branch head `ddf8c9d` (PR #42) and the project state (seven
unmerged branches, manuscript apparatus, records). Brief:
`docs/paper-sie-jmp/prompts/project-review-2026-09-26.txt`. Collation rule
(HANDOFF-cases section 4): multi-reporter findings go to the fix queue;
single-reporter findings were probe-verified here with a default of refuted;
severity was adjudicated on reachability (a paper path or a documented call
pattern; injected exceptions and never-used argument values count as latent).

## 1. Channels and verdicts

| Channel | Access | Code | Project | Output |
|---|---|---|---|---|
| Codex gpt-6-astra xhigh | full repo; suite (interrupted, see B6), all five case regenerations, 11 probes | REVISE (C01-C11) | NOT READY (P01-P08) | `codex_astra_review.md` (53 KB) |
| Fable 5.1 (this session; implemented the fix passes, disclosed) | full repo; four case regenerations + Case E oracle, T1/T4/T5 probes, merge-tree map | APPROVE (A1-A7, all S4) | NOT READY (B1-B13) | `fable51_review.md` |
| Opus (subagent; reports itself as `claude-opus-5-5[1m]`, effort max) | full repo; full suite (1346/5/1, 532 s), all five case regenerations, Case D source regeneration (50 subjects), prior-IS regeneration, six formula mutants, 10 probes | REVISE (C1-C14, one S1) | NOT READY (PF1-PF11) | `opus_review.md` (50 KB) |
| Kimi K3 (`moonshotai/kimi-k3`, OpenRouter, package-only) | code package + project package | REVISE (C1-C12) | NOT READY (P-1..P-16) | `kimi_k3_review_code.md`, `kimi_k3_review_project.md` |
| GLM 5.3 (`z-ai/glm-5.3`, OpenRouter, package-only) | same two packages | REVISE (C1-C13) | NOT READY (PJ-1..PJ-12) | `glm_5_3_review_code.md`, `glm_5_3_review_project.md` |

Five of five channels say NOT READY. On the code, four say REVISE and one
(the implementer) APPROVE; the difference is the grade given to
latent failure paths, not a disagreement about the mathematics: every
channel independently verified the fix-pass arithmetic (total-variance
moments, group conditioning, joint log-sum-exp, Hellinger exponents, tie
credit, the three conventions, the Laplace identities). The adjudicated code
verdict below is **REVISE**: one S1 (A-20, the Case D source run, found by
Opus and reproduced independently by Fable) and two reachable-by-construction
S2 defects (A-2, A-3) that no paper path exercises.

## 2. How the findings were verified

- Codex's probe scripts (`proj_review/codex/probe_core.py`,
  `probe_remaining.py`) were rerun by Fable with the fix worktree forced
  onto the path; every printed line reproduced.
- Package-only claims (Kimi, GLM) were probed by Fable
  (`proj_review/fable/probe_channel_claims.py` and greps); results below.
- Regenerations against `ddf8c9d`, done independently by Codex and Fable
  from scratch environments: Case A (external validation and E7), B, C, D
  identical to the committed artifacts except ESS fields of Case B at 2e-14
  relative; Case E byte-identical. These two independent replays agree.
- Merge topology: Codex (three-argument `merge-tree`), Opus (legacy
  `merge-tree` over all 21 pairs) and Fable (pairwise `merge-tree`) agree:
  every branch pair conflicts on `Notes/DECISIONS.md` only.
- Opus's single-reporter claims were verified by Fable: the Case D source
  regeneration was rerun independently (`proj_review/fable/probe_caseD_regen.py`,
  608 s, pyro/torch/numpy seed 0, fixed package) and its winner tables are
  identical to Opus's regeneration; the grid-placement table was reproduced
  (`probe_grid_placement.py`); the seed-0 prior-IS pool regenerated
  bit-identically (`probe_is_determinism.py`, 71 s); the git history behind
  the Case D archive was read with `git show 7026ad6:bistar_gp/fit.py`; the
  build defects were grepped in the tex.

## 3. Code findings, collated

Reporter keys: X = Codex, F = Fable, K = Kimi, G = GLM. "Adj." is the
adjudicated severity; the channels' own grades stay in their files.

| # | Finding | Reporters | Adj. | Verified | Disposition |
|---|---|---|---|---|---|
| A-1 | All-failed divergence table becomes a uniform posterior with full ESS and no flag (`compute_G_matrix` penalty = 1e6 when nothing is finite; `soft_transfer` finite check passes) | X C01, K C6, G C2 | S3 (needs a metric that fails on every pair; no paper path) | rerun: `p [0.5, 0.5] ESS [3, 3]` | fix pass 2: raise when no finite entry; a candidate with no finite entry gets a flagged failure, not a penalty |
| A-2 | `compute_induced_prior`: an all-failed parameter point gets G = 1e6, which can beat valid points whose G exceeds 1e6; all-failed everywhere gives uniform weights with full ESS; no strict mode | X C02, K C7, G C6 | S2 (reachable by construction; `compute_induced_prior` is not on a manuscript path) | rerun: `failed_weight 1.0`, `all_raising_uniform` | fix pass 2: port the strict contract (`EvaluationFailure`), NaN in non-strict |
| A-3 | Strict extraction/decomposition does not check the supplied sites against the model's sampled sites: one supplied site is "1/1 extracted" with the other sites at fresh-init values; ragged arrays fail order-dependently | X C03 | S2 (a partial or ragged sample dict is a reachable input; the paper paths supply complete dicts, E7 and Case C retained 1000/1000) | rerun: `accepted 1 dropped 0 applied {one site}`; `RAGGED ... IndexError` | fix pass 2: validate the site set after aliasing, validate lengths before indexing; pins for each missing site and for reordering |
| A-4 | `is_log_Z_Mx(tau_ladder=())` returns twice the integral with perfect ESS (uniform half of the mixture still carries log 0.5) | X C04 | S3 (an argument value no script uses) | rerun: `Z 4.0 exact 2.0` | fix pass 2: reject empty or non-finite ladders (three lines) |
| A-5 | `viz.plot_full_prediction` / `plot_component` sum `ComponentResult.samples` rows as function samples: conditional means (zero latent spread) on draw paths, independent component draws (variance ratio 1.94 versus the joint posterior) on the MAP path; "95% CI" label for a non-Gaussian mixture | X C05 | S3 (consumers: `toy_example.py`, `mauna_loa.py`, `toy_example_noMCMC.py`; the poster driver stores `samples` too, see B-5) | rerun: `hmc_samples_sd_mean 0.0`, `ratio 1.935` | fix pass 2: plot mixture intervals and per-draw means as such; the `samples` dual meaning ends here rather than by renaming |
| A-6 | Sinusoidal and Sin+Linear fits fall back silently to A = omega = 1, phi = 0, sigma = std(y) when every restart raises (`_select_restart` receives an empty list) | X C06, K (T11 sub-finding) | S3 (all 16 paper-path restarts converge; latent) | rerun: `returned_unflagged {...}`; Fable probe: no warning | fix pass 2: raise (or return a flagged candidate) when no restart produced a result |
| A-7 | `robust_rank` double-argsort gives tied candidates unequal probabilities by column order | X C07, G C12 | S4 (diagnostic strategy, not a manuscript path) | rerun | fix pass 2 if cheap: average ranks under a tolerance |
| A-8 | `_safe_logdet` / `_safe_solve` regularize inconsistently (jitter escalation uncounted; self-KL = -1 for a singular pair) | X C08, G C3 | S3 (appendix-only joint metrics; positive predictive noise on every paper path) | rerun: `self_KL -1.0` | fix pass 2 or later: factor once, regularize once, count it |
| A-9 | Metric identity: implicit `run_bms_star` roster depends on import history (10 cold / 17 warm names); `compute_G_matrix` defaults to `kl_forward`; `soft_transfer` records "unspecified", `soft_transfer_weighted` records "weighted" | X C09, K C3/C9, G C1/C4, F A2/A3 | S4 (every experiment script passes explicit rosters; no caller relies on the default) | rerun: `COLD_ROSTER 10 False`; grep: no default-metric caller | fix pass 2: default `compute_G_matrix` to `PRIMARY_METRIC`; explicit rosters at manuscript entry points; the required-`metric_name` policy per the recorded options |
| A-10 | `DecompositionResult.noise_var` is the last retained draw's noise; permuting draws changes it; the poster driver stores it | X C10, K C8, G C9 | S3 (metadata; no moment depends on it; a consumer could read it as a summary) | rerun: `noise_var 1.0` vs `0.1`, moments invariant | fix pass 2: store the retained-draw mean and the per-draw vector |
| A-11 | `fit_method_metric_comparison.run_one_method` calls `np.load` on its cache before the guarded loader, bypassing `WITHDRAWN_CACHES` | X C11, K C4, G C10 | S4 (the withdrawn cache's own producer script; poster-only under W7; no paper path reads it) | source read | fix pass 2: route every cache read through `load_hmc_samples` |
| A-12 | `metric_name` optional; `samples` dual meaning; review-provenance prose in docstrings | all | S4 | recorded | fix pass 2 (existing list) |
| A-13 | ESS is computed but never thresholded or warned on the soft-transfer path; legacy SIR serialization (`_sir_bms`) and the console report use first-index `argmin`, so exact ties count as wins for the first candidate (Case C replay: "1000 wins" over 999 ties) | K C2, X (T4/T10 notes) | S3 | source read | fix pass 2: warning floor as in `is_log_Z_Mx`; serialize `hard_win_credit`, `attainment`, `weight_ess` in the SIR artifact; this is ledger Item 5's code half |
| A-14 | Pass 1b's shared ESS routine changed the arithmetic path; Case B's committed ESS fields regenerate at 2e-14 relative, all non-ESS fields identical | F A1, X (P07 table) | S4 | two independent replays | artifact README pins need a tolerance or a regeneration at integration |
| A-15 | `InducedPriorResult.log_weights` keeps the internal max shift (dual meaning) | K C11, G C13 | S4 | source read | docstring or store the raw values |
| A-16 | Legacy `rng=None` paths use the global NumPy RNG | G C7 | S4; REFUTED as a paper-path risk: the scripts seed globally and E7 replays bit-identically | E7 replay | none |
| A-17 | Primitives on a pre-built G matrix (`soft_transfer`, `aggregate_convention`) cannot enforce the universe firewall | K C5, X (T8) | design; not adopted (the guard belongs where metadata exists; no script concatenates universes) | grep | none |
| A-18 | `decompose_model_mcmc` writes draw values into the caller's model | G C8 | S4 (pre-existing behaviour) | source read | document or restore |
| A-19 | Legacy behaviour changes sanctioned by the work order: `bms_star_toy.py` scores eleven metrics; `decompose_model_hmc(strict=True)` raises where four legacy callers skipped | F A6/A7 | S4 | grep | none; noted in D68 |

| A-20 (Opus) | Case D's stored comparison archive (`experiments/practice_EvansEtAL/results_hmc/`, committed 2026-02-16 at `7026ad6`) was produced by a `fit_hmc` that discarded `pyro_sample_from_prior()` and so sampled the prior (the D6 defect, fixed at `9f75fb0`), with the per-row shift D2 removed later. Regenerating the run with the fixed package (unchanged `run.py`, seed 0) changes section 06's tables: pw_hellinger winners 22/28, 32/18, 27/23 become 5/45, 4/46, 5/45; same-winner counts 39/49/48 become 46/48/49; exponential-truth pw_nll draw wins 98.7/94.6/92.1% become 99.9/99.9/99.6%; cohort mean G moves 0.07-0.23. The BIC baseline (18/32) and the MAP-conditional regret reconstruction are unchanged. | Opus C1; ledger Item 3 (mechanism) | **S1** (a manuscript table changes under the corrected code) | two independent regenerations (Opus 647 s, Fable 608 s) give identical winner tables | regenerate the archive with the fixed package and an explicit seed (add `pw_kl_vcal`), rerun `regret_curves_mopen.py`, rewrite the three tables and the section 08 sentence; or drop the stored-BMS* tables and keep the regret reconstruction; provenance test that every consumed archive postdates `9f75fb0` |
| A-21 (Opus, Codex) | The headline/E7/Case D path scores four candidates fitted ONCE to the observed data, fixed across draws; Remark 1 ("table-path aggregation preserves that ordering and can never favor the restriction at any tau"), intro contribution (ii) and section 08 assume per-draw best-match projection (which Case C implements). The committed E7 artifact's pooled `kl_forward` row at tau = 1 favors the restriction: Linear 0.415, Sin+Linear 3.4e-10. Under `pw_kl_vcal` Linear beats Sin+Linear on 26 of 1000 draws (credit 0.012) and the ordering happens to hold at every tau. | Opus C3, Codex P01 | S2 (a stated guarantee fails on a committed row) | artifact read: `results.kl_forward.1.0.pooled = [0.4145, 0.1816, 0.0, 0.4038]`; E7 script fits candidates once (`cand.fit(x_np, y_np)`) | state the fixed-instance protocol in sections 02 and 3.5; scope Remark 1, intro (ii) and 08 to per-draw projection, or recompute the headline with per-draw projection as Case C does; pin with a nested fixed-instance pair |
| A-22 (Opus) | Grid PLACEMENT moves the headline: pooled `pw_kl_vcal` tau = 1 Sin+Linear 0.441 on [-11, 11] (used), 0.412 on [-13, 13], 0.445 on [-9, 9], 0.439 on the observed [-10, 10]; the appendix `kl_forward` hard-win attribution flips with placement (Sinusoidal 0.943 on [-13, 13], Sin+Linear 0.749 on [-9, 9]), so "0.696 equals the D18 hard fraction" holds only for the placement used. Grid SIZE is stable (0.440-0.441). The manuscript never states the grid as a choice. | Opus C8; Fable/Codex T5 (size only) | S3 code; MAJOR manuscript (B-6 e) | Fable rerun: 0.441 / 0.412 / 0.445 / 0.439 and credit [0.01, 0.29, 0.696, 0.004] vs [0.044, 0.943, 0.008, 0.005] on [-13, 13] | one sentence in section 02 stating 60 points on [x_min - 1, x_max + 1]; a placement-sensitivity line in the E7 README; qualify the 0.696 correspondence |
| A-23 (Opus) | `model_posterior_tau_sweep` and `ablation_ladder_posteriors` return posteriors without `converged`, `n_clipped`, `n_starts_failed`; `compute_cholesky` escalates jitter to 1e-2 uncounted; the Case D generator wraps `fit_hmc` and extraction in `except Exception: continue`, so under strict extraction a failing draw drops a whole configuration silently (did not fire in either regeneration). | Opus C10 | S3 | source read (no `converged` reference after line 1000; jitter loop without a counter) | fix pass 2: propagate the records; count jitter; narrow the generator's except |
| A-24 (Opus) | `WITHDRAWN_CACHES` names the two banner paths only; D33/D34 also withdrew the informative td7/td10 HMC caches, the historical VI values (interim W3) and the vague/gamma_relaxed HMC runs, whose local files (`samples_*_vi_td7.npz`, `samples_vague_hmc_td7.npz`, ...) the loader would accept. No paper script reads any of them. | Opus C6 (scope), with A-11 | S4 | D33/D34 text read; local files listed | derive the registry from the D33/D34 classification |
| A-25 (Opus) | Section 07's "grid-averaged correlation near -0.85" is the correlation implied by grid-mean variances (-0.848); the grid mean of the pointwise correlation is -0.712 (Opus rerun of the chains). | Opus C13 | S4; PLAUSIBLE (the artifact stores no per-point arrays; not rerun by Fable) | wording only | say "the correlation implied by the grid-mean variances" |
| A-26 (Opus) | T1 in numbers: every committed Z_M uses a single MAP predictive, so the surrogate gap affects no committed number; on a draw ensemble it moves Z_M priors by up to 0.15. The matmul RuntimeWarnings at `aggregation_v3.py:91` are a BLAS artifact on finite input. | Opus C14; Fable T1; Codex P01 | S4 (documentation) | consistent with Fable's ratio 0.60 / 0.85 | state the surrogate's scope and magnitude (B-8) |

Refuted or narrowed single-reporter code claims: Opus PF11's "one arrow glyph" is the math-mode `\\rightarrow` in the notation table (allowed by the rule); Kimi P-14 ("a naive Case D
rerun silently scores default-kernel predictives") is refuted for the
current script, which reads tracked subject summaries and extracts no
predictives; GLM C7 refuted as above; Kimi's and GLM's "case scripts break
under the fixed API" is refuted by the two independent replays of Cases A-E
(no script calls a changed API in a breaking way; the strict extraction
retained every requested draw).

## 4. Project findings, collated

### BLOCKER

| # | Finding | Reporters | Verified |
|---|---|---|---|
| B-0 (Opus) | **Case D's section 06 tables rest on the pre-D6 archive and change under the corrected code (A-20).** The section presents the archive as "the HMC-mode practice run"; D4/D6 required regeneration "before any paper number is quoted"; neither the section, its README nor D64 mentions this. PR #38 is still OPEN. This converts ledger Item 3 from a decision into a demonstrated defect: the tables must be regenerated (about 11 minutes of compute plus a rewrite and re-review) or dropped. | Opus C1/PF1; ledger Item 3 | two independent regenerations agree |
| B-1 | Five author decisions on the code-review ledger (`runs/code_review_2026_09/ledger_draft.md` Items 1-5) are open since 2026-09-06. Items 3 (Case D's stored comparisons came from a sampler that targeted the prior), 4 (the psi row: notation says sampled function, code computes the hyperparameter-conditional predictive; headline 0.441 versus 0.50-0.51), 5 (section 2.4's draw-win/ESS reporting commitment is unmet by every soft-transfer table) gate manuscript text; Items 1-2 gate the poster record. Codex P01 widens Item 4: the symbol G-bar names two estimands (mean of per-pattern G versus G on the moment-matched pattern), and the "per-pattern minimum-G projection" of section 02 describes Case C's protocol but not E7's single fit to the observed data. | all four | ledger read; Codex's two-pattern counterexample rerun (`per_draw_mean_G 2.0 plugin_G 0.0`); Fable's headline probe: plug-in G-bar is 0.60 (pw_kl_vcal) and 0.85 (kl_forward) times the per-draw mean, tau = 1 winner posterior 0.403 (plug-in) / 0.526 (mean G) / 0.441 (pooled) |
| B-2 | No integrated revision: seven branches, every pair conflicting on `Notes/DECISIONS.md` (append region after D58; D60-D68 numbers are disjoint so the union is deterministic); Case C imports the Case A script (A before C). No other file conflicts. | all four | two independent merge-tree runs |
| B-3 | One public commit cannot reproduce the manuscript: `00-notation.md`, both HANDOFFs, `build_tex.py` (which selects moving branch names) and the tex build are untracked on every branch; the headline path's prior-IS pools (`runs/prior_sensitivity/`, 63 MB; `toy_elicited` subset 7.2 MB, hash-pinned inside Case C's artifact but committed nowhere; D67 already says the stage-a file "should be committed"); `runs/viz_unification/` untracked (W4 reach check, regenerable from commit `a87356a` per section 04, but the section 3.5 reach artifact was absent at its cited local path); `experiments/mechanism_figure_poster.py` cited in section 02 and never committed; kb/Wiki argument provenance gitignored; fourteen footnotes cite branch names (`paper/case-...`) that stop resolving at merge; Case E imports `arviz` without declaring it (Case C declares it). Mitigation established by Opus and verified by Fable: the seed-0 prior-IS pool regenerates bit-identically from `prior_is_run` in about 71 s, so the pools are a documentation gap (recipe plus hashes), not a determinism gap. | X P07, F B3/B11, K P-13, G PJ-7, Opus PF9/PF7 | git log --all: 0 commits for each; sizes measured; IS regeneration identical |

### MAJOR

| # | Finding | Reporters | Verified |
|---|---|---|---|
| B-4 | `[E8B-PLACEHOLDER] UNBUILT OPTIONAL MODULE` in section 06; section 06's title carries `[DRAFT]` while PR #38 says Ready; section 05 keeps a bracketed "provisional framing" note (Kellen and Klauer 2020 unread); section 08's footnote calls section 7 "uncommitted ... supplies no reported number" while Case E is committed with numbers. | F B2, G PJ-10, X P04, K | tex/md read |
| B-5 | D58 poster bands understated (FIX-2) with no correction in the D58 record or the pinned figure manifest; the poster driver stores `samples` = conditional means; `CogSci Poster/QA_PREP.md` Q24 attributes thin bands to N = 50 and noise; no asset manifest says which figure version the presented layout embeds. Not a manuscript number (Case E used the low-level decomposition; sections 01-08 cite no Mauna or poster material). | F B5, X P05a/b, K P-4, G PJ-13 | record read; QA_PREP line 218 |
| B-6 | Manuscript arguments that overstate the machinery: (a) "pooled aggregation retains absolute divergence magnitudes" (section 03 lines 129-138, 02, 08) is false for the reported normalized probabilities, which are invariant to a common offset; pooled retains between-row differences in total support; absolute inadequacy must be read from raw G (Case D does); (b) the appendix-only `kl_forward` result appears in the main text of section 3.4 (W1 placement); (c) section 8.6 says all four reviewer rounds are recorded for every case: Kimi files exist for A-E, but the D62-D65 review-outcome lines and the case A VERDICTS table still say "author-run pending", and Case E's fourth round (Codex) was absent by disclosure; (d) Remark 1, intro (ii) and section 08 claim a per-draw ordering guarantee for a path that scores fixed instances, and a committed row violates it (A-21); (e) the evaluation grid is a choice that moves the headline by 0.03 and flips the appendix attribution, never stated (A-22); (f) the manuscript has no results appendix, so the "appendix-only" `kl_forward` material has no appendix to be confined to (Opus PF10; `\\appendix` in main.tex introduces only the notation and provenance appendices). | X P02/P04, G PJ-3/PJ-4, K P-9, F, Opus C3/C8/PF10 | Codex offset probe (`shift_invariant True`); md lines read; branch file listing (`round1_kimi-k3.md` on all five branches, dated 2026-08-12/13) |
| B-7 | Tests: no test regenerates a manuscript number (78% of the 1352 tests protect infrastructure and freezes); the E7 anchor prints without asserting; the external-target test embeds literals; the suite contains Git-mutating tests (`test_m2cr_historical_anchor.py:140` worktree add/remove, `test_m2cr_r4_launch.py:56` commits in a scratch repo, `test_m2cr_realroot_integration.py:144` `git stash create`), so a "no git mutation" review protocol cannot run it unmodified (Codex stopped its run; Fable's earlier full runs had executed them). Known failure: pypdf lock drift (Opus recomputed the lock read-only: the single difference is `+pypdf==6.14.2`). Two fixture-gated skips (both pass when supplied; convert to ordinary tests once the artifacts are on `main`). Positive evidence from Opus: six formula mutants on the paper path (noise dropped from psi, candidate-variance weighting, between-draw term dropped, per-draw normalization, tau log term removed, the D2 per-row shift restored) were each killed by 1 to 14 tests; the two assertions of 0.441 in the suite pin frozen constants, not a regeneration. Opus ran the full suite: 1346 passed, 5 skipped, 1 failed, 532 s. | F B6/B13, X P06, K P-11, G PJ-9, Opus PF8 | grep of tests; run logs; mutants |
| B-8 | Reporting gaps the code can now fill: ESS behind the headline (978 of 1000 at tau = 1; 551 at 0.1) and behind the appendix metric (2.5 to 104 at tau <= 1), the surrogate ratio (0.60 / 0.85), the evaluation-grid insensitivity (0.440 / 0.441 / 0.441 / 0.441 at 30 / 60 / 120 / 240 points; Codex: 0.4398 / 0.4407 / 0.4410 at 30 / 60 / 120 and 0.4388 on the observed domain). | F, X, K C2/C5, G C5/C11 | probes by two channels agree |

### MINOR

| # | Finding | Reporters |
|---|---|---|
| B-9 | PR #39 title says "fork awaits author" (D61 records the fork RESOLVED 2026-08-12); #40 and #41 Draft; CHATLOG ends 2026-07-26; SCRATCHPAD opens with D58; D68's Status line still says pass 1b "follows" and the package-only outputs are pending while its Updates 1-2 record them landed; PR #22 (July CHATLOG) conflicts with `main`. | F B9, K P-7, Opus PF7 |
| B-10 | Case C adds `arviz>=0.17` to pyproject/requirements; the M2CR dependency lock needs one recorded refresh together with the pypdf drift. | F B8 |
| B-11 | Case B artifact hash pins versus the 2e-14 ESS regeneration difference (A-14). | F B12, X |
| B-12 | The Case E script's AST guard on sampler literals is text-coupled by design (refactor-fragile). | G C-2 |
| B-13 | Section 07 footnote "no other Case A number is re-quoted here" beside the one re-quoted 0.441: REFUTED as a contradiction (the wording acknowledges the one). | G PJ-11 |
| B-14 | GLM's "guaranteed merge conflict on `aggregate_convention`" and Kimi's "Case E depends most deeply on `DecompositionResult.group`": REFUTED (the Case A function is script-local; Case E uses the low-level decomposition). | G, K |
| B-15 | Build defects (Opus PF11, verified): a raw `[^4]` in `B-provenance.tex:8`; the md-to-tex build repeats the same provenance footnote up to ten times per section (pandoc expands each reuse of a reference footnote); section 04 calls the single MAP predictive an "averaged GP"; one "X is the Y" construction at `07-debias.tex:123`. | Opus PF11 |

## 5. Merge plan (consensus)

All four channels: merge PR #42 first (fast-forward, no conflict), then the
paper branches on one integration branch, resolving `Notes/DECISIONS.md` by
keeping both sides in D order, regenerating each case in place after its
merge, running the suite once at the end, and merging synthesis last. Order
differences (Codex A-B-C-D-E-S; Kimi A-C-B-E-D-S with D gated on Item 3;
Fable B-C-D-A-S-E by D number) are immaterial except two constraints every
channel states: A before C (or replace the import first), and D after the
Item 3 decision. Recommended: #42, then A, C, B, D (after B-0 is resolved and re-reviewed), E, S.
Opus's refinement, adopted: land one Notes-only commit that places D60-D68 in
order first, so every later code merge finds the block present and the
DECISIONS.md conflict disappears; reconcile with the main worktree's
uncommitted D60-D67 working copy before that commit. Add the untracked
apparatus (notation, HANDOFFs, `build_tex.py` pinned to commit hashes) on the
integration branch, convert the two fixture-gated pins to ordinary tests
reading the in-repo artifacts, then regenerate the tex. Opus's regenerations
agree with Codex's and Fable's: A identical apart from its date field, B
identical except ESS last digits, C, D and E byte-identical.

## 6. Recommendations, merged and prioritized

0. Case D source (B-0 / A-20): regenerate `results_hmc` with the fixed
   package and an explicit seed, adding `pw_kl_vcal`; rerun the regret
   script; rewrite the three tables and the section 08 sentence; re-review
   Case D; or drop the stored-BMS* tables and keep the regret reconstruction.
   About 1.5 days including the review. Unblocks PR #38 and the Case D text.
1. Author decisions, ledger Items 1-5, with Item 4 widened to Codex P01
   (two symbols for the two G-bar estimands; state each case's
   candidate-fitting protocol; qualify the tau-to-zero limit by convention).
   Author time: half a day. Unblocks B-1, B-6(a) rewrite, Case D text.
2. Fix pass 2 on `main` after #42 merges, now with the code queue above:
   A-1, A-2, A-3, A-4, A-6 (strict contracts and validation), A-5 and A-10
   (samples and noise metadata), A-9 (metric identity, `compute_G_matrix`
   default), A-11 (cache guard at the experiment loader), A-13 (ESS floor
   warning and SIR serialization), A-7/A-8 if cheap, A-12 (existing list),
   plus the Case A checker wiring and the Case C import. 2-3 days, with
   counterexample pins for each.
3. Integration per section 5, then one suite run in an environment where
   the Git-mutating tests are authorized (or mark them and skip under a
   read-only flag). 1 day.
4. Provenance: commit the notation, HANDOFFs and `build_tex.py` (pinned
   hashes); commit the `toy_elicited` prior-IS subset (7.2 MB) or a manifest
   with its three hashes plus the exact stage-a command; publish a per-case
   artifact manifest (commit, script, seeds, grid, estimator, convention,
   ESS, failure counts, hashes); add slow regeneration tests for E7, Case D
   and Case B with a 1e-12 relative tolerance; assert the E7 anchor. 1.5-2
   days.
5. Manuscript text: B-6 (a)-(f) (including Remark 1's scope, the grid
   statement and a real results appendix for the appendix-only material),
   B-4 (cut or build E8B; drop `[DRAFT]`; resolve the provisional note; fix
   the section 08 footnote), B-8 (one sentence each for ESS, surrogate
   ratio, grid), B-15 (build defects, branch-name footnotes). 1.5 days.
6. D58 record addendum and poster asset manifest (B-5); author decision on
   an erratum. Half a day of record work.
7. Lock refresh (pypdf, arviz) as a recorded M2CR act; PR titles; CHATLOG
   entries for August and September. Half a day.

Total: 8-10 person-days plus author time; consistent with Codex's 9-11 and Opus's 8.5.

## 7. Verified-correct consensus

All landed channels agree, and Codex and Fable each reproduced: the
fix-pass mathematics (T2, T3, T11 core), the universe firewall placement
(T8), the withdrawn-cache loader guard, the Hellinger exponents, the three
conventions, the Laplace tau-rescale identity and reference-volume
conventions, the mixture central interval, the external-target closed forms
and checker order, and the byte-identical Case E oracle. All three repo-access
channels regenerated Cases A-E with the fixed package: identical (A, C, D, E)
or round-off in ESS (B); Opus and Fable each regenerated the seed-0 prior-IS
pool bit-identically; Opus's six formula mutants were all killed. Section 02 is consistent with the code as
implemented (GLM P-C), with the definition seams of B-1 remaining.

## 8. Status at revision 1.1

All five channels landed and are collated. Single-reporter items that could
not be reproduced by Fable are marked PLAUSIBLE in the tables (A-25 only).
The next act is the author's: B-0 and the ledger decisions, then the
integration.


## 9. Plan check by Codex Astra and the amended plan (revision 1.2)

Astra's verdict on the plan of sections 5-6: **PLAN OK WITH AMENDMENTS**
(ten points; `codex_astra_plan_check.md`). It accepts every adjudicated
grade, including the downgrades of its own findings under the reachability
rubric, A-2/A-3 S2, A-21 S2, and A-20 S1 "without reservation".

Factual claims in the check, verified by Fable:

- **Notes-first union does not remove the conflicts.** CONFIRMED. A
  `git merge-file` simulation on the extracted blobs (base = main, ours =
  main plus D60-D68 in order, theirs = each paper branch) still yields two
  to three conflict hunks per branch, because both sides modify the same
  append region. A Notes-only commit on `main` would also make PR #42 a
  non-fast-forward merge. Amendment adopted: merge #42 first, build the
  D60-D68 union on the integration branch, and resolve the Notes conflict
  at each subsequent merge by keeping the union (mechanical, reviewable by
  `grep '^## D'`).
- **The lock recommendation reversed a recorded decision.** CONFIRMED. The
  ledger (revision 3, "Other decisions recorded") says: remove `pypdf` from
  the designated interpreter; keep the historical lock. `arviz` is already
  in `m2cr_dependency_lock_v1.json`, so no refresh is needed for it; Case
  E's undeclared import is a `pyproject`/`requirements` hygiene item only.
  Amendment adopted: follow the recorded decision (uninstall `pypdf`)
  before the final canonical replays and the isolated suite run, and
  record explicitly if the author instead chooses to re-lock.
- **A-8 was S3 in Codex's own review, not a downgraded S2.** CONFIRMED (the
  error was in the prompt sent to Astra, not in the table above).
  Section 1's sentence "the difference is the grade given to latent failure
  paths" is corrected here: the code disagreement also includes A-21, an
  S2 manuscript claim, and A-20, an S1.
- **Only seed 0 of the prior-IS pools had been regenerated.** Now all three:
  seeds 1 and 2 also regenerate bit-identically (74 s each; sha256
  60d2bdf4..., 5efb94be... match the local caches), so the recipe plus
  hashes fully substitutes for committing the 7.2 MB.
- **Branch-name footnotes keep resolving after a merge** while the branches
  exist. CONFIRMED; B-3's wording is corrected to "not immutable citations".
- **The Case D "identical regeneration" in section 4 is a replay of the
  derived analysis from stored summaries**, not a validation of the source
  archive that A-20 invalidates. CONFIRMED; the verified-correct list is to
  be read that way.

Amendments adopted into the plan (numbering follows Astra's check):

1. Suspend before regenerating: return PR #38 to Draft and record the D6
   and D64 addenda now; settle ledger Items 3-5 (Item 4 first, the psi
   definition) before producing replacement evidence; harden the Case D
   producer first (fail on a missing configuration, record requested and
   retained draws and sampler diagnostics, retain the sampling outputs);
   keep the historical archive; keep the BIC and MAP-conditional
   reconstruction separate from the comparison inputs.
2. Merge order as above (#42 first; union on the integration branch).
3. Fix pass 2 queue completed: A-23 (records through the tau sweep and
   ladder, jitter counting, the Case D producer's except clause) and A-24
   (withdrawal registry from D33/D34) are assigned; A-1/A-2 must prevent
   failed evaluations from becoming support or silently changing the draw
   population; A-5 needs mixture intervals, component dependence and
   labelled conditional-mean traces, not a rename; A-9/A-12 stay together
   under the recorded metric-keyword disposition; A-13 reports
   concentration and tie credit without equating weight ESS with MCMC ESS;
   A-15/A-18 documented; A-8 deferred with an explicit restriction on
   singular covariance inputs; no action on A-16/A-17/A-19.
4. Specification repairs over new science: state E7's fixed-instance
   protocol and restrict Remark 1 to per-draw protocols (a per-draw
   headline is an author choice); adding `pw_kl_vcal` to Case D is a scope
   choice distinct from reproducing its legacy comparisons; report the grid
   and surrogate sensitivities without changing grid or estimator; keep
   A-25 as a wording fix, not a confirmed number.
5. Environment resolved before final validation, once, per the recorded
   decision.
6. Merge checks are not release acceptance: final verification follows fix
   pass 2, the environment decision, the apparatus commit and the new
   regeneration tests (computation checks, not JSON rereads); Case D gets a
   source-run provenance check; Git-mutating tests run in an isolated
   repository with its own Git metadata.
7. Artifact contract: pin the builder to the integrated sources; record
   hashes, producer and package revisions, environment, seeds, settings,
   diagnostics and failure counts per artifact; archive or narrow the Case
   A reach and Case E mode-search claims; settle Case C's LOO replay
   status; compile and inspect the PDF after the build fixes.
8. Poster (B-5): start the presented-asset inventory early; dated D58
   addendum plus separately identified corrected assets; the half-day
   estimate covers the record only.
9. Factual corrections above.
10. Budget: 10-12 focused person-days plus review turnaround and compute
    (was 8-10); cut E8B, enrichment, broad A-18 refactoring and unsupported
    reach or mode claims before cutting validation.

Amended order: suspend the Case D claims and preserve the local records;
merge #42; reconcile the Notes union on an integration branch; settle
ledger Items 3-5 while Items 1-2 proceed; complete the fix pass 2
contracts; regenerate and re-review Case D; integrate A, C, B, D, E,
synthesis with targeted replays; prepare provenance and manuscript
amendments alongside; resolve the environment; final canonical replays and
the isolated full suite; compile and inspect; poster record and hygiene
before release.

First morning (Astra's, adopted): prepare the Case D suspension and
addenda and a one-page author decision sheet (psi, candidate-fitting
protocol, legacy-versus-primary metric scope, required draw-win and ESS
reporting); preserve the main worktree's Notes and untracked apparatus;
set up the isolated integration and test location; put the producer's
completeness and diagnostic checks at the front of fix pass 2.


## 10. Opus 5.5 check of Astra's amendments, evaluated (revision 1.3)

Opus (fresh subagent, `claude-opus-5-5[1m]`) judged all ten amendments
SENSIBLE or SENSIBLE WITH A CAVEAT, Astra's grade acceptances SENSIBLE, and
the amended plan **ADOPT WITH CHANGES** (`opus_plan_check.md`). Fable's
evaluation of each of its claims:

| Opus point | Fable's verification | Adopted? |
|---|---|---|
| 1. Case D: suspend first is ledger Item 3's own default; commit the D64/D6 addenda on `paper/case-d-mopen` (not only in the main worktree's uncommitted copy); the D6 addendum must also rule on `results_diag/` and `results_hierarchical/`; regenerate on at least two seeds with diagnostics, because `run.py` passes no seed and requests none and `fit_hmc` runs one chain | CONFIRMED: `results_diag` (`be54c7f`) and `results_hierarchical` (`f6c1d40`) are both 2026-02-16, pre-D6, and the ledger (lines 102-103) asked for exactly this check; `run.py:412-423` calls `fit_hmc` without a seed inside `except Exception: continue`. The two matching regenerations (Opus, Fable) both used seed 0, so they prove determinism, not Monte Carlo robustness. | yes, all four |
| 2. Notes: hunks are one-sided; `--ours` and `--union` both return the union; the safe rule is per-block hash comparison of the incoming branch against the union, since `grep '^## D'` cannot detect a block edited on a branch after the union was built | PARTLY: with Fable's union (rebuilt from the raw branch tails; byte-identical to the earlier one, so Opus's "7 bytes shorter" does not reproduce), `git merge-file --ours` returns the union for all six paper branches, while `--union` differs for five (a separator line) and five branches show one branch-side line per hunk. The construction details differ between the two simulations; the operative conclusion is the same and Opus's safety rule is the better one. | yes: resolve with the integration side and verify per-block hashes, not headings |
| 3. Split fix pass 2 into 2a (package contracts after #42), 2b (script wiring after A and C merge), 2c (decision-gated artifacts); `metric_name` stays with the author's recorded options; A-5 gates no manuscript step because ledger Item 1(B) recomputes the poster from `samples.npz` with a new construction | CONFIRMED: Item 1 option (B) recomputes from the committed `samples.npz`; the split resolves the ordering collision in Astra's order (2a before A and C, 2b after). | yes |
| 4. Fix the `pw_kl_vcal` choice for Case D before the run (no forking path) | judgement; consistent with ledger Item 3(iii) | yes |
| 5. Environment act first, as an author decision: `pypdf` is installed in the user site (`~/.local/lib/python3.13/site-packages`, its only package), the lock test compares installed distributions (`dists` digests and `pip_freeze`) only, `arviz` is already in the lock, and a suite red at every intermediate check hides new failures | CONFIRMED (pypdf location; test lines 505-533; `arviz` present in the lock). The uninstall touches the user site shared by other interpreters, so it is the author's act; the ledger line is a draft recommendation, not an enacted decision. | yes: first, as an author decision |
| 6. Git-mutating tests need a clone with its own metadata; every release run must print `bistar_gp.__file__` because the editable install resolves to the main worktree | CONFIRMED (seven prunable worktree registrations already exist; the import trap is documented in this synthesis) | yes |
| 7. One shared manifest writer (commit, package digest, argv, seeds, versions, counts) rather than per-script provenance apparatus | judgement; consistent with the A7 record's growth | yes |
| 8. Poster: the D58 record goes before release; the corrected-asset act does not gate submission | consistent with Item 1(B) | yes |
| 9. Factual corrections in section 9 are right; GitHub branch deletion not checkable offline | agreed | n/a |
| 10. Budget: state a two-week cut line; one consolidated review round on the integrated revision saves more than any listed cut | judgement; the section 4 protocol (four rounds per PR) does dominate calendar time | yes |
| Order: environment first; decisions do not wait for #42; Case D canonical run from a commit containing #42 and 2a with the package commit an ancestor of the artifact commit | sound | yes |
| Not covered by either plan: the open D66 (SC1/SC2, ratification, uncommitted-material policy) and D67 (F1 stage-a commit, F2, F3, ratification) ledgers block #40/#41; commit `00-notation.md` unchanged before amending it; true merges only so the cited hashes stay in `main`'s history; two seeds for Case D; the import-path proof; the cut line | CONFIRMED for D67's four items (its closing paragraph) and `main`'s merge history (`7154083` has two parents); D66's items PLAUSIBLE (PR #40's title records open adjudications) | yes, all |
| Critique of section 9: the union simulation's separator lines; "recorded decision" wording; seeds 1-2 compared arrays not files | separator claim not reproduced (immaterial); wording accepted; file equality follows from identical arrays under the same `np.savez` (Opus checked) | wording corrected here |

Final adopted plan (supersedes section 9 where they differ):

1. Author sheet first: Item 3's regenerate-or-withdraw fork and Case D's
   metric scope; Item 4's psi row together with D66's SC1/SC2; Item 5's
   reporting and tie rule; the `metric_name` option; the `pypdf` policy;
   the D67 items (F1 stage-a commit, F2, F3, ratification); Items 1-2.
2. Immediately: PR #38 to Draft; the D64 suspension addendum with its D6
   cross-reference committed on `paper/case-d-mopen`, the D6 addendum ruling
   on `results_diag/` and `results_hierarchical/` as well; a checksummed
   copy of the main worktree's untracked apparatus and local inputs;
   `00-notation.md` committed unchanged before any amendment.
3. Environment: the author's `pypdf` decision enacted before any suite is
   used as a gate (expected 1347 passed, 5 skipped afterwards); every
   release run prints `bistar_gp.__file__`.
4. Merge #42 (true merge); build the D60-D68 union on the integration
   branch; at each later merge resolve `Notes/DECISIONS.md` with the
   integration side and verify per-block hashes of the incoming branch.
5. Fix pass 2a on the integration branch (A-1 to A-4, A-6, A-10, A-11 with
   A-24, A-13's code half, A-23's package half, the hardened Case D
   producer).
6. Integrate A, C, then 2b (script wiring: Case A checker, Case C import),
   then B; Case D after its canonical run (two seeds, diagnostics, from a
   commit containing #42 and 2a, `pw_kl_vcal` decided beforehand) and
   re-review; then E and synthesis (after their ledgers close); true merges
   only.
7. 2c decision-gated artifacts (E7 and Item 5 fields, the Item 4
   sensitivity artifact, the D58 correction) and the manuscript amendments
   (B-4, B-6 a-f, B-8, B-15) alongside integration.
8. Provenance contract through one shared manifest writer; builder pinned
   to the integrated commit; regeneration tests as computation checks.
9. Final: canonical replays and the full suite in a clone with its own Git
   metadata; compile and inspect the PDF; one consolidated review round on
   the integrated revision; D58 record; PR and CHATLOG hygiene.
Budget 10-12 focused person-days plus review turnaround, with a two-week
cut line: E8B, enrichment, broad A-18 refactoring and unsupported reach or
mode claims go first.
