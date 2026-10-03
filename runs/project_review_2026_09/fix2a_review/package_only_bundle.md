# Review brief: fix pass 2a of the BI*/BMS*-GP package (2026-10-03)

You are one of five independent reviewers (Codex gpt-6-astra, Fable, GLM 5.3, Gemini, Kimi K3) of
an uncommitted fix pass. Review it on its merits; do not defer to the implementer's report.

## What is under review

Repository suyoghc/bistar_gp_c (Bayesian model selection by GP-induced data priors, "BMS*").
Fix pass 2a implements the decision-free package contracts adopted by the 2026-09-26 five-channel
project review (SYNTHESIS section 10). The work order is `docs/paper-sie-jmp/HANDOFF-fix-pass-2.md`
(sections 3 to 6 define the queue items 2a-1 to 2a-10, the optional items, the style and editable-set
rules, the verification and the report). The defect specifications are the SYNTHESIS A-n rows and the
Codex C01-C11 / Opus C4-C10 findings they collate. The implementer's claims are in
`runs/project_review_2026_09/fix2a_report.md` and the draft decision entry D70 in
`Notes/DECISIONS.md`.

- Base: commit `69deeda` (branch `fix/code-review-2026-09`, PR #42).
- Under review: the uncommitted working tree of `/Users/sc8918/Documents/GitHub/bistar_gp_c-fix2a`
  (branch `fix/pass-2a`): edits to `bistar_gp/{__init__,aggregation_v3,bms_star,candidates,config,
  debias,decompose,induced_prior,laplace_evidence,viz}.py`, the new `bistar_gp/errors.py`, edits to
  `experiments/fit_method_metric_comparison.py`, `experiments/practice_EvansEtAL/run.py`,
  `experiments/prior_sensitivity_study.py` (the `_sir_bms` serialization block), the new
  `tests/test_fix2a_contracts.py`, two adapted tests in `tests/test_bms_aggregation.py` (an
  author-approved exception to the editable set, after a consultation recorded in the report), the
  report, and the D70 draft.
- Implementer's verification (verify, do not assume): full suite 1353 passed, 6 failed, 5 skipped,
  with the failures attributed to the known dependency-lock drift, four realroot tests that archive
  only tracked files (the new `errors.py` is untracked), and one timing flake; Case E oracle
  byte-identical; Cases A, C, D regenerated identically; Case B identical except ESS fields at
  2e-14 relative.

## Standard and severity (from `docs/paper-sie-jmp/HANDOFF-code-review.md` section 2)

A finding is anything where claim fidelity, commitment enforcement, silent-wrong-answer paths,
estimator honesty, reproducibility or test adequacy fails. Severity: **S1** a number, figure or
artifact the manuscript or the D58 poster presents is wrong; **S2** the computation diverges from
the claim, a commitment is unenforced, or an uncertainty is materially misstated, under a reachable
configuration; **S3** scope, robustness or an unexercised silent-failure path; **S4** hygiene,
naming, documentation. Every finding needs a concrete failure scenario (inputs or a call sequence
that produce the wrong outcome); without one it is a question. Grade by reachability: a paper path
or a documented call pattern; injected exceptions and never-used argument values count as latent.

## Questions

1. Item by item (2a-1 to 2a-10 and the optional A-5, A-7, A-15, A-18): does the change implement
   the work-order specification and the SYNTHESIS disposition correctly and completely? Name any
   gap, wrong exception type, wrong message, or behaviour the spec did not ask for.
2. Regressions: can any change alter a number on a paper path (the E7/headline SIR path in
   `experiments/prior_sensitivity_study.py::_sir_bms`, Cases A-E), or break a caller (including
   the frozen M2bR/M2c modules and drivers, which must not be edited, and the D58 poster driver)?
3. New holes: does any change introduce a new silent-wrong-answer path, an order dependence, an
   unhandled exception class, a log-only signal where a raise or recorded field is needed, or a
   reproducibility gap?
4. Tests: does each pin discriminate the pre-2a code and the defect class (would a plausible wrong
   implementation pass)? Are the two adapted D2 tests in `tests/test_bms_aggregation.py` weakened in
   any respect? What is missing?
5. The report's deviations (its section "Deviations", items 1-9): acceptable, or should any be
   reverted?
6. The report's open items (its section "Not done", items 1-8): which, if any, should be fixed
   inside 2a before it is committed, and which can wait?
7. The author's standing question for every fix: knowing what you now know, should this pass be
   deleted and re-implemented in a better, more concise, more elegant form? Answer per item with
   KEEP, SIMPLIFY IN PLACE (say how), or REWRITE (say why).
8. Record accuracy: is any claim in the report or the D70 draft false or overstated?

## Output format (markdown, at most about 2500 words)

- **Verdict**: APPROVE or REVISE for the code; one line on the record's accuracy.
- **Findings** table: ID (your channel prefix plus number), item, severity S1-S4, status
  (CONFIRMED by probe, CONFIRMED by source read, PLAUSIBLE, or NEEDS-REPO-VERIFICATION),
  file:line, claim, concrete failure scenario, suggested change, pin that would catch it.
- **Verified correct**: what you checked and found right (with the check).
- **Answers** to questions 5, 6 and 7 (a short table for 7).
- **What you ran or read** (repository channels: commands and outcomes).

## Package-only channel note

You have no repository access. Everything you need is below: the work order, the defect
specifications, the implementer's report and D70 draft, and the complete diff of the fix pass
against the base `69deeda` (tracked files with 15 lines of context, then the full text of the two
new files). You cannot run code; mark any claim that needs execution NEEDS-REPO-VERIFICATION and
say what to run. Line numbers refer to the post-2a files as shown in the diff hunks.

---------------------------------------------------------------------------------------------------
# A. Work order: docs/paper-sie-jmp/HANDOFF-fix-pass-2.md
# HANDOFF — fix pass 2, starting with 2a (package contracts)

Written 2026-09-27 by the Fable session that ran the 2026-09 code review, fix
passes 1/1b/1c, and the 2026-09-26 five-channel project review. A new session
continues from here with no memory of that work; everything it needs is in the
files named below. Read this file completely before touching anything.

## 0. State of the world (2026-09-27)

- Repository `suyoghc/bistar_gp_c`. `main` is `7154083` (2026-07-26, unchanged
  since). Six paper branches are unmerged, PRs #36-#41, all conflicting with
  each other and with the fix branch on `Notes/DECISIONS.md` only.
- Main worktree `/Users/sc8918/Documents/GitHub/bistar_gp_c` is on
  `paper/case-e-debias` (`a07e61e`) with uncommitted Notes edits and the
  UNTRACKED manuscript apparatus `docs/paper-sie-jmp/` (notation, HANDOFFs,
  prompts, `build_tex.py`, the tex build), plus untracked local inputs
  `runs/prior_sensitivity/` (the headline's prior-IS pools, 63 MB) and
  `runs/viz_unification/`. Treat the main worktree as READ-ONLY. Never touch
  `stash@{0}`.
- Fix worktree `/Users/sc8918/Documents/GitHub/bistar_gp_c-fix` is on
  `fix/code-review-2026-09` at `69deeda` (= PR #42, pushed): fix passes 1, 1b,
  1c (D68), the code-review record `runs/code_review_2026_09/`, and the
  project-review record `runs/project_review_2026_09/` (D69). Clean.
- The author's decision sheet `runs/project_review_2026_09/DECISION_SHEET.md`
  (main worktree, untracked) is UNCAST. Fix pass 2a needs none of its lines;
  everything decision-gated (2b, 2c, the Case D canonical run, the manuscript
  amendments, integration) waits for it.
- Governing plan: `runs/project_review_2026_09/SYNTHESIS.md` (on the fix
  branch) section 10, which supersedes sections 5, 6 and 9 where they differ.
  Findings are cited there as A-n (code) and B-n (project).

Traps that cost time before:

- `bistar_gp` is an editable install pointing at the MAIN worktree. Any script
  outside your worktree imports the unfixed package unless you set
  `PYTHONPATH=<your worktree>`; `python -m pytest` inside the worktree is
  fine (cwd first). Print `bistar_gp.__file__` once in every probe and every
  regeneration log.
- The session scratchpad under `/private/tmp/claude-501/...` is purged between
  sessions. Anything you want to keep goes in the worktree (committed) or
  under `runs/project_review_2026_09/` (the record).
- The full suite contains Git-mutating tests (`tests/test_m2cr_historical_anchor.py:140`
  worktree add/remove, `tests/test_m2cr_r4_launch.py:56` scratch commits,
  `tests/test_m2cr_realroot_integration.py:144` `git stash create`). They
  touch the shared `.git` and leave prunable worktree registrations. Running
  the full suite in a linked worktree has been done repeatedly without harm,
  but the record calls for the release-level run in a clone with its own Git
  metadata. For 2a, run the full suite once in your worktree and say so.
- Expected suite at `69deeda`: 1346 passed, 5 skipped, 1 failed. The failure
  is `tests/test_m2cr_environment_freeze.py::test_committed_dependency_lock_reproduces_at_head`
  (pypdf==6.14.2 installed in the user site `~/.local/lib/python3.13/site-packages`;
  decision B1 on the sheet is the author's; do not uninstall it yourself, do
  not touch the lock). Two skips are fixture-gated pins (`FIX1_FIXTURE_DIR`).
- Two frozen groups must not be edited: the M2bR/M2c drivers and modules
  (`experiments/m2br_*.py`, `bistar_gp/m2c_*`, `bistar_gp/m2cr/`,
  `bistar_gp/mcse_strategy.py`, `docs/m2c_freeze/`) and the D58 poster driver
  `experiments/poster_d58_mauna.py`. `mcse_strategy_estimate`'s contract is
  why `metric_name` (B2) is not in 2a.
- No Mauna Loa inference of any kind. No network, no new dependencies.

## 1. Where 2a lives

Create ONE sibling worktree and branch from the fix head (the author
authorizes this single git act by handing you this document):

    git -C /Users/sc8918/Documents/GitHub/bistar_gp_c worktree add \
        /Users/sc8918/Documents/GitHub/bistar_gp_c-fix2a -b fix/pass-2a 69deeda

Work only there. No other git mutation until the report is accepted:
no add, commit, stash, checkout, reset, rebase, push. When the report is
accepted the author commits (or tells you to), with a D70 entry drafted by
you (section 6).

## 2. Read first, in this order

1. `runs/project_review_2026_09/SYNTHESIS.md` sections 3 (the A-n table with
   dispositions), 9 and 10 (the adopted plan).
2. `runs/project_review_2026_09/codex_astra_review.md` C01-C11 (each with a
   reproduction command and output) and `opus_review.md` C1-C14; these are
   the defect specifications for 2a.
3. `docs/paper-sie-jmp/HANDOFF-code-review.md` section 2 (what "correct"
   means here) and `docs/paper-sie-jmp/00-notation.md` (main worktree).
4. `runs/code_review_2026_09/fix1_report.md` and `fix1_synthesis.md`
   (how pass 1 was specified, tested and reported; the pinning-test style is
   `tests/test_fix1_*.py` and `tests/test_fix1_review_round.py`).
5. `Notes/DECISIONS.md` D68 and D69 on the fix branch.

## 3. The 2a queue (decision-free package contracts)

Each item: what, where, the pin. "Raise" means a clear exception naming the
site, candidate or point; "flag" means a recorded count or field, never a
silent substitution. Keep every existing paper-path number bit-identical
(section 5 verifies it); every new behaviour on a failure path may raise.

| # | Item (SYNTHESIS id) | Change | Pin |
|---|---|---|---|
| 2a-1 | A-1: all-failed divergence table becomes a uniform posterior | `bms_star.compute_G_matrix`: raise when no entry is finite; raise when any candidate column has no finite entry (a candidate that failed on every draw is a failure, not "an extremely poor fit"); keep the per-entry penalty for partial failures and log a warning with the counts | always-raising metric raises; one-candidate-fails-everywhere raises; partial failure keeps the penalty and warns; existing `test_fix1_sentinels.py` and `test_fix1_metrics_firewall.py` still pass |
| 2a-2 | A-2: induced prior sentinels | `induced_prior.compute_induced_prior(..., strict=True)`: a raising `predict_fn` or an all-failed point raises `EvaluationFailure` under strict; under `strict=False` the point gets log weight -inf (zero mass) and `n_failed_points` is recorded on the result; ESS over finite weights only; all points failed raises regardless. Move `EvaluationFailure` to a new `bistar_gp/errors.py` and re-export it from `laplace_evidence` (which imports `induced_prior`, so the class cannot stay there) | failed region gets weight 0, not 1; all-raising raises; ESS excludes failed points; `test_fix1_sentinels.py::test_negative_metric_cannot_reward_a_failed_draw` still passes |
| 2a-3 | A-3: strict extraction accepts incomplete site dictionaries | `bms_star.extract_gp_predictives` and `debias.decompose_model_hmc` (and `compute_log_marginal_likelihoods`): after `select_hmc_sites` aliasing, compare the supplied sites with the model's sampled-site inventory (see `tests/test_hmc_sample_sites.py::test_select_sites_covers_every_hyperparameter` for the inventory the package already exposes; the frozen Mauna period carries no prior and is not sampled); under strict raise naming every missing site; validate that all supplied arrays share one leading length before any indexing (raise the same error whatever the dict order) | remove each required site in turn: raises naming it; a ragged dict raises identically under two orders; a full dict is order-invariant; E7 and Case E paths unchanged |
| 2a-4 | A-4: empty IS ladder doubles the integral | `laplace_evidence.is_log_Z_Mx`: reject an empty, non-finite or non-positive `tau_ladder` (ValueError) | `tau_ladder=()` raises; the constant-integrand volume identity holds for the default ladder |
| 2a-5 | A-6: silent sinusoid fallback | `candidates.SinusoidalModel.fit` and `SinLinearModel.fit`: when `_select_restart` returns None, raise `EvaluationFailure` (no preset A = omega = 1 candidate) | all restarts raising: fit raises; one successful restart: fit succeeds; the E7 fits are bit-identical (all restarts succeed there) |
| 2a-6 | A-10: order-dependent `noise_var` | `debias.decompose_model_hmc` / `decompose_model_mcmc`: `DecompositionResult.noise_var` = mean over retained draws; per-draw vector attached as `noise_var_draws` (non-field attribute, like `full`, `groups`); MAP path unchanged | permuting draws leaves every summary and `noise_var` invariant; `test_poster_d58_driver.py` (positional contract, `noise_var` a float) still passes |
| 2a-7 | A-11 + A-24: cache guard | `experiments/fit_method_metric_comparison.py`: route the cache read through `config.load_hmc_samples` (or check `is_withdrawn_cache` before `np.load`); `config.WITHDRAWN_CACHES`: derive the list from D33/D34 (informative td7/td10 HMC caches, the historical VI caches `samples_*_vi_td7.npz`, vague and gamma_relaxed HMC caches under `runs/prior_sensitivity/` and `runs/fit_method_metric_comparison/`), each entry cited to its D-line in a comment | each registered name refused by the loader and by the experiment route with a synthetic fixture; `test_fix1_roles.py` still passes |
| 2a-8 | A-13: ESS never warns; first-index ties in serialization | `bms_star.soft_transfer(..., ess_warn=...)`: warn when the minimum per-candidate `weight_ess` falls below a floor (mirror `is_log_Z_Mx`'s `ess_warn`); `run_bms_star`'s console report: tie-aware credit instead of `argmin` wins; `experiments/prior_sensitivity_study._sir_bms`: add `hard_win_credit`, `attainment`, `tie_fraction`, `weight_ess` beside the existing `hard_win_fractions` key (keep the old key so committed artifacts stay comparable). Do NOT edit the frozen M2bR drivers that also serialize `hard_win_fractions` | a tied matrix serializes equal credit; the warning fires below the floor and not above; E7 regenerates with its existing keys identical |
| 2a-9 | A-23 package half: dropped records | `laplace_evidence.model_posterior_tau_sweep` and `ablation_ladder_posteriors`: carry `converged`, `n_clipped`, `n_starts_failed` (and `all_converged`) in their results; `decompose.compute_cholesky`: log a warning at each jitter escalation naming the level (no signature or return change: the Case E oracle calls it directly and must stay byte-identical) | sweep and ladder results expose the flags; a forced escalation logs; `test_laplace_zmx.py::test_ablation_ladder_matches_model_posterior` still passes |
| 2a-10 | Hardened Case D producer (A-23 generator half; needed by A1 on the sheet before any run) | `experiments/practice_EvansEtAL/run.py`: replace `except Exception: continue` around `fit_hmc` and extraction with fail-loud behaviour (a `strict=True` argument threaded through `run_all`); pass a seed to `fit_hmc` (`seed=` exists on the sampler; thread it from `run_all`); record requested and retained draw counts, the seed and the sampler diagnostics in each subject JSON; write the per-configuration samples to an `.npz` beside the JSON. Do NOT run the 50-subject regeneration (decision A1); a two-subject smoke run in scratch is fine | a raising sampler on one configuration fails the run under strict; the JSON carries seed and counts; `regret_curves_mopen.py` still reads the old JSONs unchanged |
| optional | A-5 (viz), A-7 (rank ties), A-15/A-18 (docstrings) | only if the queue above is green: `viz.py` plots mixture central intervals and labels conditional-mean traces; `robust_rank` averages tied ranks; docstrings for `InducedPriorResult.log_weights` and `decompose_model_mcmc`'s in-place writes | as in SYNTHESIS A-5/A-7 |

Out of scope for 2a (decision-gated or frozen): B2 `metric_name`; A-8
(deferred with a documented restriction on singular covariances); 2b script
wiring (`check_external_targets` into the Case A script, Case C's
`aggregate_convention` import: both need the A and C merges); 2c artifacts
(E7 fields for Item 5, the Item 4 sensitivity, the Case D run, the D58
correction); every manuscript edit.

## 4. Style and record rules (verbatim from the earlier passes)

- No arrow glyphs in prose; no "X is the Y" role-noun constructions; no
  "lives/sits" for abstracta; minimal em-dashes; one line of provenance per
  changed function ("fix pass 2a, SYNTHESIS A-n"), not review history.
- Tests: one new file `tests/test_fix2a_contracts.py`, one test per pin
  above, each discriminating the pre-2a code (the mutant must fail); do not
  weaken or delete an existing test; keep the `FIX1_FIXTURE_DIR` gating as it
  is.
- Editable set: `bistar_gp/{bms_star,induced_prior,laplace_evidence,candidates,debias,decompose,config,errors,__init__,viz,aggregation_v3}.py`,
  `experiments/fit_method_metric_comparison.py`,
  `experiments/prior_sensitivity_study.py` (serialization block only),
  `experiments/practice_EvansEtAL/run.py`, the new test file, and
  `Notes/DECISIONS.md` (the D70 draft only). Nothing else.

## 5. Verification (all of it, reported with counts and hashes)

1. `cd <worktree> && python -m pytest tests/ -q -p no:cacheprovider -rs`:
   expect every pre-existing test to pass (1346 at `69deeda`, plus your new
   file), the same 5 skips, and only the known lock-drift failure.
2. Case E oracle, byte-identical. The script exists only on
   `paper/case-e-debias`; run it from a scratch directory whose `bistar_gp`
   is a symlink to YOUR worktree's package:
       mkdir -p <scratch>/oracle/experiments && cd <scratch>/oracle
       git -C <worktree> show origin/paper/case-e-debias:experiments/toy_debias_demo.py > experiments/toy_debias_demo.py
       ln -s <worktree>/bistar_gp bistar_gp
       python -c "import bistar_gp,os;print(os.path.realpath(bistar_gp.__file__))"
       python experiments/toy_debias_demo.py --out <scratch>/oracle/out --quiet
   then `shasum -a 256` of `results.json`, `debias_figure.png`, `README.md`
   against the committed `runs/toy_debias_demo/` on that branch (or the main
   worktree's copy): 65c9ff5f..., c1153549..., 7096cd6e....
3. Regenerations of Cases A (E7), B, C, D against your package, same symlink
   method (`bistar_viz` and `experiments/practice_EvansEtAL` symlinked from
   your worktree; `runs/prior_sensitivity` and `runs/viz_unification`
   symlinked READ-ONLY from the main worktree; outputs under the scratch
   `runs/`). Scripts and committed references, each fetched with
   `git show origin/<branch>:<path>` (none of them is on the fix branch):

   | Case | Branch | Script | Committed reference |
   |---|---|---|---|
   | A (E7) | `paper/case-a-vanbork` | `experiments/e7_convention_sensitivity.py` | `runs/e7_convention_sensitivity/results.json` |
   | A (targets) | `paper/case-a-vanbork` | `experiments/vanbork_external_validation.py` | `runs/vanbork_external_validation/results.json` |
   | B | `paper/case-b-occam-dial` | `experiments/e6_nesting_monotonicity.py`, `experiments/occam_dial_figure.py` | `runs/occam_dial/e6_results.json`, `runs/occam_dial/figure_results.json` |
   | C | `paper/case-c-haaf` | `experiments/haaf_nested_constraint.py` | `runs/haaf_nested_constraint/results.json` |
   | D (derived replay) | `paper/case-d-mopen` | `experiments/regret_curves_mopen.py` (reads the archive `experiments/practice_EvansEtAL/results_hmc/`) | `runs/regret_curves_mopen/results.json` |
   | E (oracle) | `paper/case-e-debias` | `experiments/toy_debias_demo.py` | `runs/toy_debias_demo/` (three hashes above) |
   Compare numerically to the committed JSONs (a walker that ignores date
   fields; exact equality on numbers). Expected: A, C, D identical for every
   existing key (E7 may gain the 2a-8 keys); B identical except ESS fields at
   about 2e-14 relative (the pass-1b ESS routine). Runtimes: E7 8 s, D 4 s,
   B 13 s and 28 s, C about 4 min (Pyro chains), E 60 s.
4. Every probe and regeneration log prints the package path.

## 6. Report and stop

Write `runs/project_review_2026_09/fix2a_report.md` in YOUR worktree: per
item, files touched, signature changes and every call site updated, the
test count, the suite counts and runtime, the three oracle hashes, the four
regeneration comparisons, deviations with reasons, and the list of items
deliberately not done. Draft the D70 entry in `Notes/DECISIONS.md`
(Problem, Decision, Alternatives considered, Result, Status: "OPEN, awaiting
author commit"). Then STOP: no commit, no push. The author reviews, commits,
and decides whether a review round (Codex gpt-6-astra xhigh via
`codex exec --yolo --skip-git-repo-check -m gpt-6-astra -c 'model_reasoning_effort="xhigh"'`,
a fresh Opus or Fable subagent, and the package-only channels through
OpenRouter with a reasoning cap of 16000 tokens) runs on the branch before
it joins the integration branch.

## 7. After 2a (for orientation only; each needs a sheet line)

2b script wiring after A and C merge; 2c decision-gated artifacts; the
integration branch from PR #42 with the D60-D68 union and per-block hash
reconciliation of `Notes/DECISIONS.md` (a Notes-first commit on `main` does
NOT remove the conflicts; verified); Case D canonical run on two seeds from
a commit containing #42 and 2a; true merges only; the final suite in a clone;
a two-week cut line (E8B, enrichment, broad refactoring, unsupported reach
and mode claims go first).

---------------------------------------------------------------------------------------------------
# B. Adjudicated code findings: runs/project_review_2026_09/SYNTHESIS.md section 3 (A-n table) and section 10
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

---------------------------------------------------------------------------------------------------
# C. Defect specifications: Codex review C01-C11 (runs/project_review_2026_09/codex_astra_review.md)
## 2. Code findings

### Summary

| ID | Target/module | Severity | Status | Location | Claim |
|---|---|---|---|---|---|
| C01 | T11; divergence table | S2 | CONFIRMED | `bistar_gp/bms_star.py:556` | An entirely invalid table becomes uniform posterior support with maximal ESS. |
| C02 | T11; induced prior | S2 | CONFIRMED | `bistar_gp/induced_prior.py:244` | Failed parameter regions can outrank valid regions; total prediction failure returns uniform weights. |
| C03 | Extraction/decomposition | S2 | CONFIRMED | `bistar_gp/bms_star.py:323`; `bistar_gp/debias.py:441` | Strict mode accepts incomplete sites, and unequal array lengths make dictionary order consequential. |
| C04 | IS evidence | S2 | CONFIRMED | `bistar_gp/laplace_evidence.py:559`, `:673` | An empty temperature ladder doubles the integral while reporting perfect ESS. |
| C05 | T2; plotting/sample contract | S2 | CONFIRMED | `bistar_gp/viz.py:23`; `bistar_gp/debias.py:43` | Plotted “function samples” have the wrong distribution on both HMC and MAP paths. |
| C06 | Candidate optimization | S2 | CONFIRMED | `bistar_gp/candidates.py:160`, `:200` | All raising sinusoid restarts silently produce a preset candidate. |
| C07 | Alternative aggregation | S2 | CONFIRMED | `bistar_gp/aggregation_v3.py:250` | Equal divergences receive unequal rank-based probabilities determined by column order. |
| C08 | Joint covariance fallback | S3 | CONFIRMED | `bistar_gp/bms_star.py:27`, `:64` | Inconsistent regularization gives a negative self-divergence for singular covariance. |
| C09 | T6; metric identity | S4 | CONFIRMED | `bistar_gp/bms_star.py:763`; `bistar_gp/aggregation_v3.py:447` | Implicit metric selection depends on import history; some result identities remain absent or misleading. |
| C10 | Decomposition metadata | S2 | CONFIRMED | `bistar_gp/debias.py:461`, `:498`, `:518` | Reported observation variance comes from the last retained draw and changes under draw permutation. |
| C11 | T7; cache boundary | S2 | CONFIRMED | `experiments/fit_method_metric_comparison.py:132` | Direct cache loading bypasses the withdrawal guard. |

### C01. Invalid G values become apparently well-supported evidence

`compute_G_matrix` replaces nonfinite values with a finite penalty. If every evaluation fails, the penalty equals one million. The downstream nonfinite check at `bms_star.py:609` consequently cannot detect the failure.

**Reproduction:** `python "$S/probe_core.py"`, block “C1 all-invalid table.” Three GP predictives containing a NaN mean, two finite candidates, and the primary metric give:

```text
G [[1000000.0, 1000000.0], [1000000.0, 1000000.0], [1000000.0, 1000000.0]]
p [0.5, 0.5] ESS [3.0, 3.0] ties 1.0
```

These diagnostics describe numerical substitutions as three agreeing draws. A partial failure also loses its provenance. This was not observed in the replayed E7 or Case C inputs.

**Change:** Reject failed evaluations by default. If an explicitly permissive mode remains, propagate a validity mask, attempted/retained counts, and reasons; do not turn absent comparisons into evidence.

**Pin:** Entirely invalid tables must raise through both table-building and aggregation entry points. Mixed valid/invalid inputs must have an explicit, tested failure policy and cannot report failed rows as successful ties.

### C02. The induced-prior sentinel can win

At `induced_prior.py:273`, an all-failed set of per-GP divergences for one parameter point receives `G=1e6`. The penalty is local to that point, so valid parameter points can have larger G. Separately, prediction exceptions produce infinity, and the all-nonfinite branch at line 286 resets log weights to zero.

**Reproduction:** `python "$S/probe_core.py"`, block C2. Use one GP `N(0,1)`, `a ~ Uniform(-1,1)`, and prediction NaN for negative a, otherwise `2000+a`. With 20 reference draws, seed 42, primary metric, and tau 100:

```text
failed_weight 1.0 failed_G 1000000.0
minimum_valid_G 2000099.0269522907 ESS 11.0
```

Replacing the predictor with one that always raises gives:

```text
all_raising_uniform [0.05] ESS 19.999999999999993
```

The negative-metric penalty repair did not close either path. The large-G example demonstrates a reachable configuration, not the scale observed in the canonical toy replay.

**Change:** Share the strict evaluation contract used by the repaired Laplace path. An all-failed induced prior must fail; a permissive diagnostic must not return normalized inferential weights.

**Pin:** Include all-raising predictors, all-NaN metric results, and valid G above the former sentinel, in addition to negative-valued metrics.

### C03. “Strict” extraction does not establish a complete draw

Both consumers require at least one recognized kernel key, then apply whichever keys were supplied. They do not compare those keys with the model's required sampled sites. Freshly initialized values fill omitted dimensions. They also infer the draw count from the first dictionary entry and index other arrays without validating their lengths.

Locations: `bms_star.py:323–376`, `debias.py:441–488`, and the prefix-selection helper `model.py:67–94`.

**Reproduction:** `python "$S/probe_core.py"`, block C3, supplies only the toy kernel's output-scale site. The complete model has four sampled sites:

```text
Extracted 1/1 GP predictives
accepted 1 dropped 0
Decomposed 1/1 MCMC samples successfully
decomposition_accepted 1
```

`python "$S/probe_remaining.py"` supplies one output-scale value and two values for each other site:

```text
RAGGED covar_module.kernels.0.outputscale_prior accepted 1
RAGGED likelihood.noise_covar.noise_prior ERROR IndexError index 1 is out of bounds
```

Changing dictionary order changes whether one draw silently disappears or extraction raises.

**Change:** Validate required sites after resolving documented legacy aliases, distinguish intentionally fixed parameters, require consistent nonempty leading dimensions, and validate values before selecting indices.

**Pin:** Remove each required site independently; reorder the same ragged dictionary; confirm identical errors. Full valid dictionaries must remain order invariant.

### C04. Empty IS ladder causes a factor-of-two normalization error

`is_log_Z_Mx(..., tau_ladder=())` constructs a proposal without Gaussian components. Sampling then uses the uniform box for every draw, but `log_q` still assigns it only half the probability mass.

**Reproduction:** `python "$S/probe_remaining.py"`. Integrate constant `exp(-G)=1` over `[-1,1]`, using 10,000 draws:

```text
EMPTY_LADDER (0.03, 0.3, 3.0) Z 2.000711120090614 ESS 8382.82839504874 exact 2.0
EMPTY_LADDER () Z 4.000000000000001 ESS 10000.0 exact 2.0
```

A separate uniform-MC check returned exactly 2. The paper scripts use a nonempty ladder; their replays did not exhibit this error.

**Change:** Reject empty, nonfinite, or nonpositive ladders, or implement a correctly normalized pure-uniform proposal when no Gaussian components exist.

**Pin:** The constant-integrand volume identity must cover zero Gaussian components, not only the usual defensive mixture.

### C05. FIX-2 repaired moments but not the plotted sample distribution

`ComponentResult.samples` contains conditional means on draw-based paths and function draws on the MAP path. `plot_full_prediction` indiscriminately sums rows from this field and labels them function samples. On MAP paths, components were sampled separately from their conditional marginals; their sum lacks posterior cross-component covariance. `plot_component` also ignores `samples_kind`.

**Reproduction:** `python "$S/probe_core.py"`, block C4:

```text
hmc_full_sd_mean 0.5313942277288924 hmc_samples_sd_mean 0.0
map_variance_full 0.28501236959515486
sum_independent_function_variance 0.5515280414738964 ratio 1.9351021229615863
```

The HMC example has one hyperparameter draw: latent uncertainty remains positive, while every displayed conditional-mean sample coincides. The MAP example uses 10,000 samples and demonstrates substantial excess variance after summing independent component samples.

The full band at `viz.py:23–24` additionally labels mean plus/minus two posterior standard deviations “95% CI.” For a non-Gaussian hyperparameter mixture, that does not specify a 95% central interval. The component label “SE” at line 49 conflates posterior spread with estimation error.

**Change:** Plot the available mixture central intervals; distinguish conditional means from function draws; sample the full posterior directly or draw components jointly with their cross-covariances. Renaming the field alone will not repair the MAP sampling error.

**Pin:** Identical-hyperparameter draws must still produce nonzero latent spread; empirical full-function covariance must match direct summed-kernel conditioning. A skewed mixture must use its actual quantiles.

### C06. All optimizer restarts can fail without invalidating a candidate

Both sinusoidal candidate classes catch every restart exception. When no result remains, `fit` sets fixed amplitude/frequency/phase values and a data-derived noise scale. No failure status reaches `CandidateResult`.

**Reproduction:** `python "$S/probe_core.py"`, block C8, replaces `SinLinearModel._fit_mle` with an always-raising function:

```text
returned_unflagged {'A': 1.0, 'omega': 1.0, 'phi': 0.0,
'b': 0.25, 'c': 0.0, 'sigma': 1.1030479641901056}
```

Thus a numerical breakdown can be presented to BMS* as a fitted candidate. The observed-data fits used in the successful replays did not take this fallback.

**Change:** Raise when no usable restart exists. Persist convergence/failure information with fitted candidates if explicitly accepted nonconverged results remain supported.

**Pin:** An all-raising or all-nonfinite restart set must not yield a normal candidate prediction. Test the complete fit-and-score route.

### C07. Rank aggregation breaks permutation symmetry at ties

`robust_rank` uses double `argsort`, assigning distinct ranks to identical values.

**Reproduction:** `python "$S/probe_core.py"`, block C6, supplies a three-row, two-column zero matrix:

```text
{'a': 0.7310585786300049, 'b': 0.2689414213699951}
{'b': 0.7310585786300049, 'a': 0.2689414213699951}
```

Only the candidate names/order changed. This optional aggregation does not generate the manuscript's canonical pooled results.

**Change:** Assign equal or average ranks to ties under a stated tolerance.

**Pin:** Permuting tied and partly tied candidate columns must only permute the returned probabilities; equal candidates must receive equal support.

### C08. Covariance fallback does not compute a coherent regularized divergence

The solve regularizes its first matrix while the trace numerator remains unregularized. Log determinants apply separate fallback choices. For singular identical inputs, these operations do not correspond to one pair of regularized Gaussian distributions.

**Reproduction:** `python "$S/probe_core.py"`, block C7: zero mean and a two-dimensional zero covariance on both sides return `self_KL -1.0`.

**Change:** Require positive-definite inputs, or factor and regularize each covariance once and use those same matrices throughout, exposing the modification.

**Pin:** Self-divergence and nonnegativity across small eigenvalues; reject indefinite inputs rather than silently changing their meaning.

This concerns the appendix-only joint metric. Positive predictive observation noise guards the manuscript paths inspected, so I assign S3 and do not infer an incorrect reported primary-metric result.

### C09. Metric identity still depends on call and import history

**Reproduction:** `python "$S/probe_remaining.py"` launches a fresh process:

```text
COLD_ROSTER 10 False
WARM_ROSTER 17 True
```

The Boolean reports membership of `pw_kl_vcal`; the sole intervening action imports `metrics_v2`. `run_bms_star(metric_names=None)` copies this mutable roster. The fix now warns, but it does not make the default stable. `compute_G_matrix` still defaults to the appendix metric at line 533.

The separate metadata probe returned `metric_default unspecified` for `soft_transfer` and `weighted_metric weighted` for `soft_transfer_weighted`. “Weighted” identifies aggregation, not divergence. Callers at `metrics_v2.py:398` and `mcse_strategy.py:177` do not supply metric identity.

**Change:** Use a deterministic explicit roster for manuscript entry points and propagate actual metric identity. Resolve the deferred required-keyword policy without casually altering frozen inference code.

**Pin:** Fresh-process import-order invariance and end-to-end result identity. The paper scripts examined already pass explicit rosters; this is a remaining API/provenance defect, not a reproduced headline change.

### C10. Reported noise variance depends on draw order

The HMC and raw-parameter decomposition paths return the last successful draw's noise variance. This scalar has no “last draw” label and cannot represent posterior predictive observation variance.

**Reproduction:** `python "$S/probe_remaining.py"`, two otherwise identical draws with variances 0.1 and 1.0:

```text
NOISE_ORDER False noise_var 1.0 mean_noise 0.55
NOISE_ORDER True noise_var 0.10000000000000002 mean_noise 0.55
MOMENTS_INVARIANT True True
```

The full latent moments correctly remain unchanged.

**Change:** Return the retained-draw mean observation variance, or preserve the complete per-draw vector with an explicit summary contract.

**Pin:** Permuting complete draws leaves every ensemble summary invariant. If observation intervals are supported, compare them with an explicit mixture including observation variance.

### C11. The withdrawal guard does not cover the experiment loader

`config.load_hmc_samples` rejects recognized withdrawn inputs by default at `config.py:253–269`. But `fit_method_metric_comparison.run_one_method` directly calls `np.load` when a cache exists, before routing through the guarded sampler.

**Reproduction:** Read-only source comparison:

```sh
nl -ba "$R/bistar_gp/config.py" | sed -n '253,270p'
nl -ba "$R/experiments/fit_method_metric_comparison.py" | sed -n '121,151p'
```

Relevant output:

```text
if is_withdrawn_cache(path):
    ...
    if not allow_withdrawn:
        raise RuntimeError(msg)

if cache_path and os.path.exists(cache_path) and not force_refit:
    with np.load(cache_path) as z:
        samples = ...
```

This confirms the bypass in code flow, not use of withdrawn evidence in the current manuscript. I did not load or derive results from the withdrawn archives.

**Change:** Put the same provenance/withdrawal check at every cache consumption boundary, including experiment-specific loaders.

**Pin:** Pass a designated withdrawn cache name to this public experiment route and assert rejection before `np.load`, using a synthetic fixture.


# C'. Defect specifications: Opus review C4-C14 (runs/project_review_2026_09/opus_review.md)
### C4 (S3, CONFIRMED): `compute_G_matrix` still substitutes a finite score for a failed evaluation

`bms_star.py:556-573` converts `LinAlgError`/`ValueError` from a metric into
`max_finite + 10 (|max_finite| + 1)` (or 1e6 when nothing is finite) and records nothing.
The penalty cannot win, but it keeps mass at the top of the paper's τ range. Probe P05
(injected metric failing for one of four candidates on every draw): the failed candidate
receives 0.000, 0.000, 0.077 and 0.225 posterior at τ = 0.1, 1, 10, 100; an all-failed
matrix becomes all 1e6 and a uniform posterior, with no exception and no field on
`BMSStarResult`. No failure occurs on the headline path: recomputing both SIR G matrices
entry by entry from the predictives reproduces them exactly, so no penalty was substituted. **Change:** count failures per column on the result and raise under a
strict flag, matching FIX-5 in the Laplace path. **Test:** inject a failing metric and
assert the error or the recorded count.

### C5 (S3, CONFIRMED): `compute_induced_prior` keeps the sentinels FIX-5 removed elsewhere

`induced_prior.py:245-249` turns a raising predictor into G = ∞ (silently excluded),
`:272-273` sets G = 1e6 when every draw's metric fails, and `:280-293` falls back to uniform
weights when nothing is finite. Probe P05: a predictor that raises everywhere returns
uniform weights with ESS 50.0 of 50 and no error. No case script calls this function.
**Change:** the strict/NaN semantics of `compute_G_at_params`. **Test:** all-failing
predictor raises under strict.

### C6 (S3, CONFIRMED): the withdrawn-cache guard does not guard the readers

`load_hmc_samples(allow_withdrawn=False)` (`config.py:253-273`) refuses the two
`WITHDRAWN_CACHES` entries (`config.py:31-34`), but every script that actually reads those
caches uses `np.load` directly: `experiments/fit_method_metric_comparison.py:133`, and in the
main worktree the untracked `experiments/toy_tau_metric_comparison.py:84` and
`experiments/toy_n20_poster_figures.py:67` (the CogSci poster's toy panels, poster-only
under W7). The list also omits members of the class the M2bR record withdrew (D33/D34:
informative td7/td10 HMC, historical VI, vague and gamma_relaxed HMC), for example
`runs/fit_method_metric_comparison/samples_hmc_td7.npz`, `samples_vi*.npz` and
`runs/prior_sensitivity/samples_vague_hmc_td7.npz`, which `load_hmc_samples` would load
silently. No paper-branch script reads any of them (grep over all case scripts), so no
manuscript number is exposed. **Change:** route the readers through the guard (or guard at
`np.load` call sites with `is_withdrawn_cache`) and derive the list from the D33/D34
classification. **Test:** each reader script refuses a fixture path under a withdrawn name.

### C7 (S3, CONFIRMED): T4, draw concentration is now measurable but never reported

`boltzmann_weight_ess` and `hard_win_statistics` (`bms_star.py:494-528`) populate
`BMSStarResult` (`:660-661`), but nothing warns and no case script or artifact records
them. Probe P02 on the E7 G matrices (regenerated; E7 reproduces with zero difference): pw_kl_vcal ESS at τ = 0.1 is 33.7, 37.9,
551.4, 33.8 and at τ = 1 at least 669 (so the 0.441 rests on broad support); kl_forward ESS
is 1.2, 2.2, 2.5, 1.1 at τ = 0.1 and 6.1, 8.4, 103.9, 6.1 at τ = 1. At τ = 0.1 one draw
carries 93 percent of Linear's pooled weight; at τ = 1 five draws carry 82 percent. Section
2 prescribes pairing the appendix pooled result "with the aggregation convention and a
draw-level diagnostic" (`02-machinery.md:161`); section 3.5 reports the collapse without
one. **Change:** write per-candidate ESS into E7 and Case C outputs and warn below a
threshold. **Test:** a fixture with one dominant draw that triggers the warning.

### C8 (S3, CONFIRMED): T5, grid placement matters and is not documented as a choice

Probe P06 re-extracted the same 1000 SIR draws on six grids (fix package):

| Grid | pw_kl_vcal pooled τ=1 (Sin+Linear) | τ=0.1 | kl_forward hard fraction (Sin+Linear) | kl_forward pooled τ=10 (Sin+Linear) |
|---|---|---|---|---|
| [−11, 11] × 60 (used) | 0.441 | 0.634 | 0.696 | 0.245 |
| [−11, 11] × 30 | 0.440 | 0.639 | 0.674 | 0.284 |
| [−11, 11] × 120 | 0.441 | 0.631 | 0.706 | 0.044 |
| [−10, 10] × 60 | 0.439 | 0.596 | 0.749 | 0.267 |
| [−13, 13] × 60 | 0.412 | 0.590 | 0.008 | 0.004 |
| [−9, 9] × 60 | 0.445 | 0.576 | 0.747 | 0.250 |

The primary conclusion (Sin+Linear highest everywhere) is robust and the headline moves by
at most 0.03; the appendix correspondence "0.696 equals the D18 hard fraction" quoted in
section 3.5 holds only for this placement (with [−13, 13], Sinusoidal takes 0.943 of hard
wins). The manuscript never states the grid (60 points on [x_min − 1, x_max + 1]) as a
choice. **Change:** one sentence in section 2 plus a grid-sensitivity line in the E7 README.

### C9 (S3, CONFIRMED): T6, metric roles are convention; the implicit roster depends on import history

`PRIMARY_METRIC` and `APPENDIX_METRICS` (`config.py:24-25`) only drive a warning on the
implicit `run_bms_star` path (`bms_star.py:763-784`). `compute_G_matrix` defaults to
`metric_name="kl_forward"` (`:533`), the appendix-only metric, silently; `soft_transfer`
records `"unspecified"` when the name is omitted (the deferred fix-pass-2 item). Probe P05
ran `run_bms_star(metric_names=None)` in two fresh processes: 10 metrics without
pw_kl_vcal, versus 17 with it after `import bistar_gp.laplace_evidence`; any `METRICS[...]`
miss, even a typo, also registers the v2 metrics (`_MetricRegistry.__missing__`,
`:202-206`). Every paper script passes metrics explicitly. **Change:** make the default
`PRIMARY_METRIC` (or required), and build the implicit roster from an explicit constant.

### C10 (S3, CONFIRMED): T11 residue

- `model_posterior_tau_sweep` (`laplace_evidence.py:1030-1090`) and
  `ablation_ladder_posteriors` (`:1144-1199`) return only posteriors, discarding
  `converged`, `n_clipped` and `n_starts_failed`; `_select_start` (`:491-502`) prefers the
  lowest finite objective even when that start did not converge.
- `compute_cholesky` (`decompose.py:16-38`) escalates jitter up to 1e-2 without counting;
  the package paths (`extract_gp_predictives`, `decompose_model_hmc`,
  `compute_log_marginal_likelihoods`) inherit that. Case E counts it itself (0 escalations).
- Stage A of the headline pipeline catches every exception into `lml = -inf`
  (`prior_sensitivity_study.py:350-360`); the committed IS caches contain 0 such draws
  (checked all 180,000).
- Case D's generator wraps `fit_hmc` and `extract_gp_predictives` in `except Exception:
  continue` (`experiments/practice_EvansEtAL/run.py:412-423`); with strict extraction one
  failing draw now drops a whole configuration for that subject without a trace. It did not
  fire in the P08 regeneration (all 50 subjects kept 3 configurations).

On the paper paths nothing fired: Case B's committed Laplace arm reports `converged: true`,
`n_clipped: 0` for all four models, and my Case B/E6 reruns raised no `EvaluationFailure`.

### C11 (S4, CONFIRMED): T8, the firewall is complete for package G builders only

Probe P05: all-untagged rosters pass, partially tagged and two-universe rosters raise, a
single universe passes (`bms_star.py:718-745`, called at `:549` and in
`aggregation_v3.py:130`). Concatenating two legally built matrices from different
universes and normalizing through `soft_transfer` or `aggregate_convention` returns
[0.333, 0.333, 0.333] without complaint, and `ModelParameterSpace` has no universe field,
so the Z_M path cannot enforce A4. No experiment concatenates. **Change:** document that
the primitives carry no universe identity.

### C12 (S4, CONFIRMED): the `samples` dual meaning and provenance fields

`ComponentResult.samples` holds per-draw conditional means on the draw paths
(`debias.py:55-56`), yet `bistar_gp/viz.py:27-29, 50-51` plots them as "function samples",
so a figure built from `decompose_model_hmc` now shows law-of-total-variance bands around
spaghetti that carries only the between-draw spread. A positional rebuild (the poster
driver's `rebuild_decomposition_result`) gets `samples_kind="function_draws"` by default
for saved conditional means. `DecompositionResult.noise_var` holds the last retained draw's
noise (`debias.py:461, 498`; P04: 0.2352 reported vs posterior mean 0.2558);
`decompose_model_mcmc` writes each draw into the caller's model parameters and leaves them
at the last draw (`:406-410`); `soft_transfer_weighted` labels its result `"weighted"` and
reports unweighted hard-win statistics next to likelihood-weighted posteriors
(`aggregation_v3.py:443-448`). All are fix-pass-2 hygiene.

### C13 (S4, CONFIRMED): T9, Case E's guards hold; two small weaknesses

Verified: the AST guard passes on this library (my rerun reached the sampler), the site
raise works, the jitter probe tests the same matrix `compute_cholesky` tries first, the
mixture interval brackets and bisects correctly, and the variance identity used for the
cross-covariance holds exactly. Weaknesses: the guard keeps the last `_run_e1_nuts_route`
call it walks (`toy_debias_demo.py:180-184`) and checks routing with a substring test
(`:215`). The prose "a grid-averaged correlation near −0.85" (`07-debias-bridge.md:114`)
reports the correlation of grid-mean moments (−0.848, `:844`); probe P09 (rerun of the
chains) gives a grid mean of the pointwise total correlation of −0.712 (median −0.806,
range −0.94 to −0.04). **Change:** "the correlation implied by the grid-mean variances".

### C14 (S4, CONFIRMED): T1, the Ḡ surrogate

No committed number depends on the surrogate gap: Case B and E6 build `avg_gp` with
`gp_method="map"` (`bistar_viz/scripts/_viz_spaces.py:150-214`), one predictive, for which
the moment-matched pattern and the per-draw average coincide; Case A's Target B has its
own point data prior; Cases C and D use per-draw G. On a draw ensemble the gap is material
and nowhere characterized. Probe P03 (1000 SIR predictives, uniform-box MC, 40,000 points
per model, package cross-check error 0.0): Ḡ_avg − Ḡ_plug ranges 0.61 to 80.2 for Linear
(median ratio 1.46), and normalized Z_M priors move by up to 0.15 (occam=True, τ = 3:
Sinusoidal 0.28 versus 0.43; occam=False, τ = 3: Sin+Linear 0.84 versus 0.78). Two
definitions coexist in the package: `compute_induced_prior` averages per-draw G (the
notation's reading), `compute_G_at_params` uses the plug-in. The driver's follow-up on the
`aggregation_v3.py` matmul warnings closes: `w @ m` on random finite 150 × 80 inputs emits
the same three RuntimeWarnings under numpy 1.26.4 on this machine, with |matmul − einsum|
= 1.5 × 10⁻¹⁶, so the warnings are BLAS floating-point flags, not non-finite data.


---------------------------------------------------------------------------------------------------
# D. Implementer's report: runs/project_review_2026_09/fix2a_report.md
# Fix pass 2a report (package contracts, 2026-10-02/03)

- Worktree `/Users/sc8918/Documents/GitHub/bistar_gp_c-fix2a`, branch `fix/pass-2a` from `69deeda` (PR #42 head).
- Governing documents: `docs/paper-sie-jmp/HANDOFF-fix-pass-2.md` (main worktree, untracked) and `runs/project_review_2026_09/SYNTHESIS.md` sections 3, 9 and 10. Implementer: Opus 5.5 (Claude Code), fresh session.
- Git operations: the single authorized `git worktree add ... -b fix/pass-2a 69deeda`. The tool call printed `fatal: a branch named 'fix/pass-2a' already exists`; the worktree and branch nonetheless existed immediately afterwards, created 08:33:55 from `69deeda` (reflog `branch: Created from 69deeda`), pristine, so the command most likely executed twice and the first execution succeeded. After that only read-only git commands (`show`, `archive`, `diff`, `status`, `ls-files`, `rev-parse`, `worktree list`, `stash list`, `log`). No add, commit, stash, checkout, reset, rebase or push; `stash@{0}` intact; worktree registrations unchanged after both suite runs (the seven prunable ones from earlier sessions, main, fix, fix2a).
- Author decision during the pass (2026-10-03): `tests/test_bms_aggregation.py` added to the editable set as a one-file exception (section "2a-1 conflict" below), after a read-only consultation of Codex gpt-6-astra (xhigh) and Fable.
- Uncommitted. The author commits after review.

## Files touched

Package (edited): `bistar_gp/{__init__,aggregation_v3,bms_star,candidates,config,debias,decompose,induced_prior,laplace_evidence,viz}.py`. Package (new): `bistar_gp/errors.py`. Experiments (edited): `experiments/fit_method_metric_comparison.py`, `experiments/practice_EvansEtAL/run.py`, `experiments/prior_sensitivity_study.py` (the `_sir_bms` serialization block only). Tests: `tests/test_fix2a_contracts.py` (new, 12 tests) and `tests/test_bms_aggregation.py` (two tests adapted, author-approved). Record: this report and the D70 draft in `Notes/DECISIONS.md`. Nothing else; `git status --short` lists exactly these files. Frozen groups untouched: `experiments/m2br_*.py`, `bistar_gp/m2c_*`, `bistar_gp/m2cr/`, `bistar_gp/mcse_strategy.py`, `docs/m2c_freeze/`, `experiments/poster_d58_mauna.py`.

## Item by item

### 2a-1 (A-1) `compute_G_matrix`: failed divergence tables
- `bistar_gp/bms_star.py`. `EvaluationFailure` when every entry is non-finite, or when a candidate column has no finite entry (the message names the candidates); `ValueError` for an empty table (no draws or no candidates). A partial failure keeps the strictly-worse penalty `max_finite + 10 (|max_finite| + 1)` and logs one warning with the failed count and `(name, count)` pairs, so repeated names keep separate counts. A finite table is returned as computed (same array).
- No signature change. Callers, none edited: `run_bms_star`, `aggregation_v3.run_robust_aggregation`, `run_weighted_bms_star`, `metrics_v2` diagnostics and plots, the practice/v2/impact experiment scripts, and through `run_bms_star` the frozen M2bR drivers, whose behaviour changes only on this failure path (a dead column is implausible there, with candidate covariances sigma^2 I; the drivers were not re-run). The frozen `mcse_strategy` calls `soft_transfer` on prebuilt matrices and never reaches this function.
- Pin: `test_2a1_failed_divergences_raise_or_are_flagged`.

### 2a-2 (A-2) `compute_induced_prior`: strict contract
- `bistar_gp/errors.py` (new): `EvaluationFailure(RuntimeError)`, moved out of `laplace_evidence`, which re-exports it (`from bistar_gp.laplace_evidence import EvaluationFailure` keeps working; `tests/test_fix1_review_round.py` imports it that way); also exported from `bistar_gp`.
- `bistar_gp/induced_prior.py`: `compute_induced_prior(..., strict=True)` (new trailing keyword). A point fails when `predict_fn` raises or when no GP draw yields a finite divergence. Strict raises `EvaluationFailure` naming the point; non-strict gives it `G_per_sample` NaN, log weight -inf and zero weight. Every point failing raises under either setting. Partial within-point failures keep the penalty. `InducedPriorResult` gains `n_failed_points` and `n_penalized_evaluations` (defaulted fields); the ESS `1 / sum(w^2)` runs over normalized weights in which failed points weigh zero; the all-valid arithmetic is unchanged.
- Callers, not edited: `experiments/bistar_induced_prior.py` (two calls) and `bistar_induced_prior_v2.py` (one), which now raise under the default strict contract where a point fails. No case script calls the function.
- Pin: `test_2a2_induced_prior_failed_points_carry_no_mass` (the Codex C02 configuration: failed points weigh 0, not 1).

### 2a-3 (A-3) strict extraction and decomposition: incomplete or ragged site dictionaries
- `bistar_gp/bms_star.py`: `sample_draw_count(samples, keys, caller)` (one non-empty leading length across the indexed arrays, checked before any indexing, message ordered by key) and `missing_sample_sites(model, supplied_keys)` (the model's `named_priors()` inventory against the supplied sites under the aliases `select_hmc_sites` and `apply_hp_value` accept: `kernel_components.{i}.`, the bare noise site, and component 0 of a single-kernel model). `extract_gp_predictives` builds one probe model from `kernel_builder` and the likelihood builder (no random numbers drawn), raises naming every missing site under strict and warns otherwise; unequal lengths raise under either setting. The draw indices are chosen exactly as before (same generator calls in the same order), so a complete dictionary yields the same draws.
- `bistar_gp/debias.py`: the same two checks in `decompose_model_hmc`; `decompose_model_mcmc` gains the equal-length check (its name matching was already complete).
- `bistar_gp/aggregation_v3.py`: `compute_log_marginal_likelihoods` raises on a draw whose hyperparameters lack a sampled site (unconditionally, like its existing raise on an unknown site).
- No signature changes. The frozen Mauna period carries no prior, so it is never required.
- Pin: `test_2a3_incomplete_or_ragged_sample_dicts_raise` (each site removed in turn on both routes; one ragged dictionary in two orders gives one message; a reversed complete dictionary gives identical predictives; legacy names and a single-kernel model pass; the marginal-likelihood route).

### 2a-4 (A-4) `is_log_Z_Mx`: empty ladder
- `bistar_gp/laplace_evidence.py`: `ValueError` for an empty, non-finite or non-positive `tau_ladder`; the ladder is first materialized as a tuple, so a generator argument is not consumed by the check. No other change.
- Pin: `test_2a4_tau_ladder_is_validated` (four invalid ladders raise; a constant integrand returns the box volume 4.0 within 5 percent with the default ladder).

### 2a-5 (A-6) sinusoid fits: no silent preset
- `bistar_gp/candidates.py`: `CandidateModel._require_restart`; `SinusoidalModel.fit` and `SinLinearModel.fit` raise `EvaluationFailure` (restart count and last error) when every restart raised. When a restart succeeds the assignments are the same statements as before.
- Pin: `test_2a5_sinusoid_fit_without_a_successful_restart_raises` (all restarts raising raise; one successful restart gives exactly that restart's parameters).

### 2a-6 (A-10) `noise_var`
- `bistar_gp/debias.py`: `DecompositionResult.noise_var` is the mean over retained draws (a float); the per-draw vector is attached as `noise_var_draws` (non-field attribute; the MAP path stores its one value). `decompose_model_hmc` and `decompose_model_mcmc` both. The internal `_assemble` now takes the retained draws' noise values. The seven-field positional contract holds (`tests/test_poster_d58_driver.py` passes).
- Pin: `test_2a6_noise_var_is_the_retained_draw_mean_and_order_free` (both routes; permuted draws leave every summary and `noise_var` invariant).

### 2a-7 (A-11 with A-24) withdrawn caches
- `bistar_gp/config.py`: `WITHDRAWN_CACHES` derived from D33/D34, each group cited in a comment: informative HMC td10/td7 under both studies, the informative `hmc_laplace` caches (D33 with D22/D26), vague and gamma_relaxed HMC td7, every historical VI cache (D34 ratification 2), plus the existing `runs/toy_tau_metric_comparison/` (D68 FIX-7); 16 entries. The refusal message cites D33/D34 and keeps the words the fix-1 tests match.
- `experiments/fit_method_metric_comparison.py`: `run_one_method(..., allow_withdrawn=False)` reads the cache through `config.load_hmc_samples` (refusal before any load); CLI `--allow-withdrawn` for labelled archival reproduction.
- Caller: `prior_sensitivity_study.run_method_fingerprinted` calls `run_one_method` without the flag, so its stage B now refuses the withdrawn caches (intended; not edited, outside the serialization block).
- Pin: `test_2a7_withdrawn_caches_are_refused_on_every_route` (every registered name refused by the loader and by the experiment route with `np.load` patched to fail; IS pools and MAP caches admitted; a non-withdrawn cache still flows through the route).

### 2a-8 (A-13, code half) concentration and ties
- `bistar_gp/bms_star.py`: `soft_transfer(..., ess_warn=100.0)` logs a warning naming the candidates whose weight ESS is below the floor (the docstring says it is not an MCMC ESS); `run_bms_star`'s console report gives tie-split credit and attainment instead of first-index `argmin` wins.
- `experiments/prior_sensitivity_study.py` `_sir_bms`: `hard_win_credit`, `attainment`, `tie_fraction` and per-tau `weight_ess` beside the unchanged `hard_win_fractions`. The frozen M2bR drivers were not touched.
- E7 gains no keys: `e7_convention_sensitivity.py` reads only `posteriors` and the G matrices from `_sir_bms`. The study's own `results_is_*.json` gain the four keys when next regenerated (not run here).
- Pin: `test_2a8_ess_floor_warning_and_tie_aware_draw_wins` (fires below the floor and not above; tied twins serialize credit [0.5, 0.5] beside the legacy [1.0, 0.0] and print 2/4 wins each).

### 2a-9 (A-23, package half) dropped records
- `bistar_gp/laplace_evidence.py`: `model_posterior_tau_sweep` returns `TauSweepPosteriors`, a tuple subclass that unpacks as `(names, posteriors)` and carries `converged`, `n_clipped`, `n_starts_failed` (shape n_taus x n_models) and `all_converged`; `ablation_ladder_posteriors` returns `LadderPosteriors`, a dict subclass equal to the plain posteriors dict and carrying the same records per construction and model. Both survive `copy.deepcopy` and `pickle`. Callers: `plot_tau_effect_on_evidence` (unpacks) and `plot_ablation_ladder` (indexes), both unchanged, and tests; no script calls either function.
- `bistar_gp/decompose.py`: `compute_cholesky` logs each jitter escalation with its level; signature and return unchanged (the Case E oracle calls it directly).
- Pin: `test_2a9_sweep_and_ladder_carry_records_and_jitter_escalation_logs`.

### 2a-10 hardened Case D producer
- `experiments/practice_EvansEtAL/run.py`: `run_one(..., seed=None, strict=True)` and `run_all(..., seed=None, strict=True)`. Under strict a configuration can no longer go missing silently: MAP-fit, HMC-fit/extraction, empty-predictive and BMS*-scoring failures raise with subject and configuration, and `run_all` re-raises a failing subject; non-strict records the failure under `sampler_records[config]["failed"]`. The seed goes to every `fit_hmc` call and, when given, to the predictive subsample (`np.random.default_rng(seed)`), so each subject reproduces on its own. Each subject JSON adds `seed`, `strict`, `sampler_records` (per configuration: mode, seed, requested and returned draws, warmup, predictives requested/retained/dropped, `fit_hmc` diagnostics via `return_diagnostics=True`); `<stem>_samples.npz` beside it holds `<config>/<site>` draws and `<config>/retained_indices`. CLI `--seed`, `--allow_missing_configs`. `SubjectResult` gains four defaulted fields.
- The 50-subject regeneration (sheet decision A1) was not run. Smoke run in scratch: two demo subjects (one power, one exponential), real E1 NUTS, 40 draws, 40 warmup, 20 predictives, seed 0, strict: 20.6 s; every configuration recorded 40/40 draws, 20/20 predictives, 0 divergences; a second run with the same seed reproduced both JSONs (elapsed time aside) and both `.npz` files exactly.
- `regret_curves_mopen.py` imports `run.py` (`build_model`, `generate_demo_data`, `normalize`, unchanged) and replays the old archive identically (regeneration D below).
- Pin: `test_2a10_case_d_producer_fails_loud_and_records_provenance` (a raising sampler on the second configuration stops the strict run and is recorded by the non-strict one; JSON seed, counts and diagnostics; the `.npz`).

### Optional items (done because the ten were green)
- A-5, `bistar_gp/viz.py`: `plot_full_prediction(..., seed=0)` draws the mixture's own central interval (label "95% central interval") when the summary carries per-draw moments, otherwise "mean ± 2 sd"; traces are the per-draw conditional means on draw paths (labelled) or joint draws from `N(full.mean, full.cov)` on the MAP path, never sums of separately drawn components; a rebuild without `full` gets band and mean only. `plot_component` uses the same band and labels traces by `samples_kind`. Consumers (`toy_example.py`, `mauna_loa.py`, `toy_example_noMCMC.py`) unchanged and not run. Pin: `test_optional_a5_plots_mixture_intervals_and_labelled_traces`.
- A-7, `aggregation_v3.robust_rank`: average ranks for exact ties (`scipy.stats.rankdata`); untied rows rank as before. Pin: `test_optional_a7_rank_aggregation_is_permutation_symmetric` (Codex C07's zero matrix gives 0.5/0.5, previously 0.731/0.269).
- A-15 and A-18: docstrings for `InducedPriorResult.log_weights` (internal scale) and `decompose_model_mcmc`'s in-place writes.

## 2a-1 conflict and the approved test change

The first full run showed two pre-existing tests failing by design: `tests/test_bms_aggregation.py::test_failed_cell_is_worse_than_all_finite_for_negative_metric` and `::test_failed_candidate_gets_lowest_posterior` (commit `569ee39`, D2). Both built a candidate that fails on every draw and asserted the penalty, the configuration SYNTHESIS A-1 adjudicates as the defect (Opus C4: 0.225 posterior at tau = 100). The handoff's 2a-1 pin named only the two fix-1 files, and the file was outside the editable set. Consulted read-only on the options (A adapt, B leave failing, C narrow 2a-1): Codex gpt-6-astra xhigh and Fable both chose A, judged that neither test is weakened (their D2 property, a failed cell never wins under a negative-valued metric, stays tested where the penalty still applies), and advised against a strict flag. The author chose A with Fable's version: the always-failing candidate now pins the raise, a new candidate fails on one draw only, and the second test adds a comparison that fails if the penalty were only the largest finite value. Checked here: both adapted tests pass on 2a and fail on the old `10 * max_finite` penalty and on a `max_finite` penalty; on `69deeda` the first fails (no raise) and the second passes, as it should. The two in-scope hardenings Astra noted (empty table, repeated names) were added at the same time.

## Tests

- `tests/test_fix2a_contracts.py`: 12 tests (10 queue items, 2 optional). Each fails on the pre-2a package (a `69deeda` `git archive` copy in scratch, the one `EvaluationFailure` import pointed at `laplace_evidence`): DID NOT RAISE for 2a-1, 2a-2, 2a-3, 2a-4, 2a-5 and 2a-10; 2a-6 `noise_var` 0.1 versus 0.05 under permutation; 2a-7 the D33 entry missing; 2a-8 `soft_transfer` has no `ess_warn`; 2a-9 the sweep tuple has no `converged`; A-5 label "95% CI"; A-7 [0.731, 0.269].
- `tests/test_bms_aggregation.py`: two tests adapted (above).

## Verification

Every probe and run forced `PYTHONPATH` to the worktree (with `PYTHONDONTWRITEBYTECODE=1`) and logged the package path; every log shows `/Users/sc8918/Documents/GitHub/bistar_gp_c-fix2a/bistar_gp/__init__.py`. Logs are in the session scratchpad (`fix2a/`, `logs/`, `logs_final/`), which is purged between sessions, so the numbers are recorded here.

1. Full suite, `python -m pytest tests/ -q -p no:cacheprovider -rs`, run in the worktree as the handoff allows (the Git-mutating tests ran against the shared `.git`; worktree registrations and `stash@{0}` unchanged afterwards).
   - Run 1 (before the approved D2 test change): 1352 passed, 7 failed, 5 skipped, 365 s; collected 1364 = 1352 at `69deeda` + 12 new.
   - Run 2 (final state; nothing changed after it): 1353 passed, 6 failed, 5 skipped, 729 s (the machine's load average was about 90 during the run). The skips are the same five as at `69deeda` (two fixture-gated pins, three environmental). The failures:
     - `test_m2cr_environment_freeze.py::test_committed_dependency_lock_reproduces_at_head`, the known lock drift; recomputed read-only, the drift is now `+imageio-ffmpeg==0.6.0` in the base site-packages (dists and freeze) and `+pypdf==6.14.2` in the user site (freeze only).
     - `test_m2cr_realroot_integration.py::test_realroot_launch_{1,2,3,4}`: the test snapshots the candidate tree with `git stash create`, which captures tracked modifications only, so the archive lacks the untracked `bistar_gp/errors.py` while the modified tracked modules import it (`ModuleNotFoundError: No module named 'bistar_gp.errors'` in the staged child). Reproduced without Git: importing `bistar_gp.profile_integration` from a copy of the tracked `bistar_gp` files fails identically and succeeds once `errors.py` is added. These pass once the new file is committed. No staging directory was left behind in the realroot cache.
     - `test_m2cr_capture.py::test_budget_kill_outranks_waiter_capture_fault` (run 2 only), a 0.36 s budget test that reported `NOT_STARTED` under the load; passed 5 of 5 times alone and in its whole file (113 passed, 45.7 s).
   - The four files most affected pass (35 tests: `test_fix2a_contracts.py` 12, `test_bms_aggregation.py` 11, `test_fix1_sentinels.py` 6, `test_fix1_metrics_firewall.py` 6).
2. Case E oracle by the handoff's symlink method (`experiments/toy_debias_demo.py` from `origin/paper/case-e-debias`, `bistar_gp` symlinked to the worktree package, realpath printed), run twice (after the main implementation and against the final package), byte-identical both times, 62 s and 61 s:
   - `results.json` 65c9ff5f14b9a5f3aca8267745d6b368d95b831e85a610f6844b74e1b33712bb
   - `debias_figure.png` c1153549ca55d9d644804790ef9a4627f8d82bedd157ec348ecb519f551a4723
   - `README.md` 7096cd6e4d3d02f8971cee294fa3e50a2c7248272320e9cc72cfc45994f889af
3. Regenerations against the final package. Scratch root with `bistar_gp`, `bistar_viz`, `experiments/practice_EvansEtAL`, `experiments/prior_sensitivity_study.py` and `experiments/fit_method_metric_comparison.py` symlinked to the worktree; case scripts and committed references fetched with `git show origin/<branch>:<path>` at the case heads `76135be` (A), `32c0a58` (B), `0adde90` (C), `ff4c353` (D), `a07e61e` (E); inputs copied (deviation 9). Each script ran through `runpy` after importing `bistar_gp`, so its log shows the module it actually used. Comparison by a JSON walker: exact equality on every number (NaN equals NaN), string leaves compared, keys named as dates ignored, added keys listed.

   | Case | Script | Committed reference | Result | Wall time |
   |---|---|---|---|---|
   | A (E7) | `e7_convention_sensitivity.py` | `runs/e7_convention_sensitivity/results.json` | identical: 138 numbers, 6 strings (only `generated` differs); no added keys | 10 s (23 s on the first run, which built the matplotlib font cache) |
   | A (targets) | `vanbork_external_validation.py` | `runs/vanbork_external_validation/results.json` | identical: 141 numbers (only `generated` differs) | 3 s |
   | B | `e6_nesting_monotonicity.py` | `runs/occam_dial/e6_results.json` | identical except 2,815 ESS-derived fields (`ess[]`, `min_ess`, `delta_log_Z_se_at_nominal_bracket[]`), at most 2.1e-14 relative, the counts D69 recorded for the pass-1b ESS routine | 29 s |
   | B | `occam_dial_figure.py` | `runs/occam_dial/figure_results.json` | identical except 8 `ess` fields, at most 1.6e-15 relative | 16 s |
   | C | `haaf_nested_constraint.py` | `runs/haaf_nested_constraint/results.json` | identical: 334 numbers, 44 strings, 36 other leaves | 283 s (212 s on the first run; load average up to 200 at the end of the final run) |
   | D (derived replay) | `regret_curves_mopen.py` | `runs/regret_curves_mopen/results.json` | identical: 2,317 numbers, 168 strings | 4 s |

   The first and final regenerations are identical to each other in every number. On these paths no new failure path fired: no divergence-evaluation failure, no jitter escalation, no missing site. The ESS floor fired six times in E7 (`pw_kl_vcal` and `pw_nll_gp` at tau = 0.1, minimum ESS 33.7 and 21.5 of 1000; `kl_forward` at tau = 0.1, 0.3, 1 and 3, minimum 1.1, 2.3, 6.1 and 14.5, Opus C7's numbers) and twice in Case C (`kl_forward` at tau = 0.1 and 0.3).
4. The main worktree's `runs/prior_sensitivity` and `runs/viz_unification` (100 files) hash identically before and after; the main worktree's status and HEAD (`a07e61e`) and the fix worktree (`69deeda`, clean) are as they were at the start.

## Deviations, each with its reason

1. `tests/test_bms_aggregation.py` edited, by author decision after the consultation (section above).
2. 2a-1 also raises `ValueError` for an empty table and reports repeated names separately (Astra's consultation findings; both inside the item's wording).
3. 2a-2 adds `n_penalized_evaluations` beside the required `n_failed_points`, so partial failures are counted as well as logged.
4. 2a-3 adds the equal-length check to `decompose_model_mcmc`, the same order-dependence one call away; `compute_log_marginal_likelihoods` raises without a strict flag because it has none and already raises unconditionally on unknown sites. The site inventory comes from one probe model per call.
5. 2a-7 adds a `--allow-withdrawn` CLI flag mirroring the loader's keyword; the cache read now prints the loader's message instead of the script's.
6. 2a-10: the strict contract covers every configuration-dropping site (MAP fit, HMC fit and extraction, empty predictive list, BMS* scoring) and `run_all`'s per-subject handler, not only the `fit_hmc`/extraction clause, because each dropped a configuration silently ("fail on a missing configuration", SYNTHESIS section 9 amendment 1); the seed also drives the predictive subsample, without which a seeded run did not reproduce.
7. A-7 ranks exact ties, the package's tie rule (`hard_win_statistics`), rather than ties under a tolerance.
8. A-5 changes what the MAP-path figure traces are (joint draws from a fixed seed instead of the stored component samples) and draws no traces for a rebuild without `full`.
9. The regeneration inputs `runs/prior_sensitivity` and `runs/viz_unification` were copied into scratch (`cp -Rp`) instead of symlinked, so no script could write into the main worktree; all 100 files hash identically in the main worktree before and after.

## Not done, deliberately

- Decision-gated or frozen: B2 `metric_name`; A-8 (deferred with its restriction on singular covariances); 2b script wiring (Case A checker, Case C import); 2c artifacts (E7 Item 5 fields, the Item 4 sensitivity, the Case D run, the D58 correction); every manuscript edit; the 50-subject Case D regeneration.
- Open items found in this pass, for the author:
  1. A dead row (one draw failing for every candidate) still gets the uniform penalty, outside 2a-1's wording; under `normalize_per_draw=True` it adds equal mass to every candidate (Fable).
  2. The absolute ESS floor (100, as in `is_log_Z_Mx`) fires on every call when there are fewer than 100 draws, including uniform weights (ESS equal to the draw count): 270 of 270 calls in the 20-predictive smoke run; also per replicate (B = 1000) inside the frozen `mcse_strategy` when its pooled ESS is low. On the paper paths it fired six times in E7 and twice in Case C (Verification item 3), each a genuine concentration. A floor scaled to the draw count (Fable: `min(100, n_draws)`) or one summary per `run_bms_star` call are the alternatives.
  3. The inherited penalty formula overflows to inf for finite values near the float maximum (unreachable in practice; Astra).
  4. `aggregation_v3.score_averaged_gp` scores without non-finite validation: a raising metric propagates, a NaN result does not raise.
  5. `run.py` still replaces a raising candidate fit with a flat-mean candidate (a silent substitution outside the queue).
  6. `prior_sensitivity_study.basin_occupancy` and the D12 cache paths read withdrawn caches with `np.load` directly (outside the serialization block).
  7. The historical toy_elicited HMC caches (`runs/prior_sensitivity/samples_toy_elicited_hmc_td{7,10}.npz`) are not registered: D33 classifies toy_elicited as SUPERSEDED and the handoff's enumeration omits them; the legacy `bistar_gp/cache/*.npz` archives are outside D33/D34.
  8. The dependency-lock drift has grown since 09-26: besides `pypdf==6.14.2` (user site) the base site-packages now hold `imageio-ffmpeg==0.6.0` (decision B1).

---------------------------------------------------------------------------------------------------
# E. Draft decision entry D70 (Notes/DECISIONS.md)
## D70: Fix pass 2a, decision-free package contracts from the 2026-09-26 review (SYNTHESIS A-1 to A-4, A-6, A-10, A-11 with A-24, A-13 code half, A-23 package half, hardened Case D producer; optional A-5, A-7, A-15, A-18) — 2026-10-03

**Problem:** D69's adopted plan (SYNTHESIS section 10, step 5) splits fix pass 2 into 2a
(package contracts that need no author decision), 2b (script wiring after the A and C merges)
and 2c (decision-gated artifacts). The 2a queue (`docs/paper-sie-jmp/HANDOFF-fix-pass-2.md`
section 3) holds the adjudicated paths on which a failure became a plausible number or a
record was dropped: an all-failed divergence table, or a candidate failing on every draw,
became finite support (A-1); the induced prior let an all-failed point outrank valid ones and
returned uniform weights when every point failed (A-2); strict extraction accepted an
incomplete site dictionary, and ragged arrays raised or dropped a draw depending on dict order
(A-3); an empty IS ladder doubled the integral (A-4); sinusoid fits fell back silently to a
preset candidate (A-6); `noise_var` was the last retained draw's value (A-10); the
fit-method experiment read its cache before the withdrawal guard, whose registry named two of
the caches D33/D34 withdrew (A-11, A-24); the weight ESS never warned, and first-index
`argmin` gave ties to the first candidate (A-13); the tau sweep and the ablation ladder dropped
their convergence records, jitter escalations went unrecorded, and the Case D producer dropped
failing configurations silently and passed no seed (A-23).

**Decision:** Implemented in the worktree `bistar_gp_c-fix2a`, branch `fix/pass-2a` from
`69deeda`; report `runs/project_review_2026_09/fix2a_report.md` (per item: files, signatures,
callers, pins). `compute_G_matrix` raises `EvaluationFailure` when every entry or a whole
candidate column fails and `ValueError` on an empty table, while partial failures keep the
strictly-worse penalty with a logged count. `EvaluationFailure` moves to the new
`bistar_gp/errors.py` (re-exported by `laplace_evidence` and the package);
`compute_induced_prior(..., strict=True)` raises on a failed point, gives it zero weight with
`n_failed_points` under `strict=False`, and raises whenever every point fails.
`extract_gp_predictives`, `decompose_model_hmc` and `compute_log_marginal_likelihoods` compare
the supplied sites with the model's `named_priors()` inventory under the legacy aliases (strict
raises naming each missing site) and validate one leading length before any indexing
(`sample_draw_count`, `missing_sample_sites` in `bms_star.py`; `decompose_model_mcmc` gets the
length check). `is_log_Z_Mx` rejects empty, non-finite or non-positive ladders.
`SinusoidalModel.fit` and `SinLinearModel.fit` raise when every restart raised.
`DecompositionResult.noise_var` is the retained-draw mean, with `noise_var_draws` attached.
`WITHDRAWN_CACHES` has 16 entries derived from D33/D34, each group cited, and
`fit_method_metric_comparison.run_one_method` reads its cache through `load_hmc_samples`
(`allow_withdrawn`, `--allow-withdrawn`). `soft_transfer(..., ess_warn=100.0)` warns below the
floor, `run_bms_star` prints tie-split credit, and `_sir_bms` serializes `hard_win_credit`,
`attainment`, `tie_fraction` and `weight_ess` beside `hard_win_fractions`.
`model_posterior_tau_sweep` and `ablation_ladder_posteriors` return a tuple and a dict subclass
carrying `converged`, `n_clipped`, `n_starts_failed` and `all_converged`; `compute_cholesky`
logs each escalation. `experiments/practice_EvansEtAL/run.py` threads `seed` and `strict=True`
through `run_all`, no configuration goes missing silently, and each subject JSON records the
seed, requested and retained draws and the sampler diagnostics, with the draws in a `.npz`
beside it. Optional items: `viz.py` plots the mixture central interval and labels
conditional-mean traces (MAP traces are joint draws); `robust_rank` averages tied ranks;
docstrings for `InducedPriorResult.log_weights` and the in-place writes of
`decompose_model_mcmc`. Tests: `tests/test_fix2a_contracts.py`, 12 tests, each failing on
`69deeda`. Author decision 2026-10-03: `tests/test_bms_aggregation.py` joins the editable set
as a one-file exception. Its two D2 tests (`569ee39`) asserted the penalty for a candidate
failing on every draw, the configuration A-1 adjudicates as the defect (Opus C4). A read-only
consultation of Codex gpt-6-astra xhigh and Fable chose adaptation, found neither test
weakened and advised against a strict flag. Fable's version, adopted, keeps the D2 property on
a candidate that fails on one draw, pins the raise for the always-failing one, and adds a check
that fails if the penalty were only the largest finite value.

**Alternatives considered:** leaving the two D2 tests failing for the author (B in the
consultation) or narrowing 2a-1 so a dead column keeps the penalty (C, rejected: it restores
A-1); a strict flag on `compute_G_matrix` (rejected by both consultants); keeping
`EvaluationFailure` in `laplace_evidence` (impossible, because `laplace_evidence` imports
`induced_prior`); symlinking the regeneration inputs as the earlier reviews did (copied
instead, so no script could write into the main worktree); a draw-count-scaled ESS floor (left
open).

**Result:** Full suite in the worktree at the final state: 1353 passed, 6 failed, 5 skipped,
729 s at load average about 90 (collected 1364 = 1352 + 12 new; run 1, before the D2 test
adaptation, 1352/7/5 in 365 s). The failures are the known lock-drift test (the drift is now
`pypdf==6.14.2` in the user site plus `imageio-ffmpeg==0.6.0` in the base site-packages); four
`test_m2cr_realroot_integration.py` launch tests whose `git stash create` snapshot omits the
untracked `bistar_gp/errors.py` (reproduced from the tracked files; they pass once the file is
committed); and one timing flake, `test_m2cr_capture.py::test_budget_kill_outranks_waiter_capture_fault`
(0.36 s budget; 5 of 5 alone, its file 113 passed). Case E oracle byte-identical (65c9ff5f...,
c1153549..., 7096cd6e...). Regenerations against the final package: Case A E7 and external
targets, Case C and Case D identical on every existing key; Case B identical except 2,815
ESS-derived fields in `e6_results.json` and 8 in `figure_results.json`, at most 2.1e-14
relative (the pass-1b ESS routine, the counts D69 recorded). The Case D producer's two-subject
smoke run (E1 NUTS, seed 0) reproduces exactly on a seeded rerun.

**Status:** OPEN, awaiting author commit; `bistar_gp/errors.py` must be committed with the
package. Open for the author (report, "Not done"): a dead row under `normalize_per_draw=True`;
the absolute ESS floor firing on every call below 100 draws (270 of 270 calls in the smoke run)
and inside the frozen MCSE loop; the `score_averaged_gp` NaN path; the practice candidate-fit
fallback; direct `np.load` reads in `prior_sensitivity_study` outside its serialization block;
the toy_elicited historical HMC caches; the grown lock drift (sheet B1). A review round on the
branch (Codex, Opus or Fable, package-only channels) is the author's call before it joins the
integration branch.

---------------------------------------------------------------------------------------------------
# F. Diff of tracked files, 69deeda to the 2a working tree (git diff -U15)
```diff
diff --git a/bistar_gp/__init__.py b/bistar_gp/__init__.py
index 8422deb..0b5b3aa 100644
--- a/bistar_gp/__init__.py
+++ b/bistar_gp/__init__.py
@@ -1,24 +1,25 @@
 """
 bistar_gp: Bayesian Inference Plus (BI*) with Gaussian Process decomposition.
 
 Implements the framework from Chandramouli & Shiffrin for:
 - Additive GP kernel composition and decomposition
 - Bias mitigation via kernel separation
 - Full Bayesian inference over hyperparameters
 """
 
+from .errors import EvaluationFailure
 from .decompose import decompose_additive_gp, sample_from_component, mixture_central_interval
 from .model import (
     AdditiveGPModel, build_model, build_toy_kernels, build_mauna_loa_kernels,
     build_likelihood, assert_mauna_period_frozen, MAUNA_FROZEN_PERIOD,
 )
 from .fit import fit_map, fit_mcmc_simple, print_hyperparameters
 from .debias import decompose_model, decompose_model_mcmc, DecompositionResult, ComponentResult
 from .data import generate_toy_data, load_mauna_loa, load_mauna_loa_training
 from .sampler_diagnostics import SamplerDiagnostics
 from .candidates import build_toy_candidates, LinearModel, SinusoidalModel, SinLinearModel, QuadraticModel
 from .bms_star import (
     extract_gp_predictives, compute_G_matrix, run_bms_star, soft_transfer,
     aggregate_convention, boltzmann_weight_ess, hard_win_statistics, PredictiveList,
     kl_forward, kl_backward, kl_symmetric, hellinger_distance,
     pw_kl_forward, pw_kl_backward, pw_kl_symmetric, pw_hellinger, pw_mse, pw_nll,
@@ -28,30 +29,31 @@ from .bms_star import (
 from .mauna_loa_candidates import (
     QuadSinModel, QuadHarmonic2Model, build_mauna_loa_candidates,
 )
 from .config import PRIOR_CONFIGS, ExperimentConfig, build_kernels_from_config, build_likelihood_from_config
 from .m1_builder import (
     build_m1_matern_component, augment_with_m1_short_scale,
     build_mauna_loa_m1_kernels, LogitNormalPrior,
 )
 from .divergence_clustering import DivergenceError, divergence_nonclustering
 from .mcse_strategy import MCSEError, mcse_strategy_estimate
 from .m2c_manifest import (
     build_v117_algorithm_manifest, build_v117_manifest, manifest_sha256,
 )
 
 __all__ = [
+    "EvaluationFailure",
     "decompose_additive_gp", "sample_from_component", "mixture_central_interval",
     "AdditiveGPModel", "build_model", "build_toy_kernels", "build_mauna_loa_kernels", "build_likelihood",
     "assert_mauna_period_frozen", "MAUNA_FROZEN_PERIOD",
     "fit_map", "fit_mcmc_simple", "print_hyperparameters",
     "decompose_model", "decompose_model_mcmc", "DecompositionResult", "ComponentResult",
     "generate_toy_data", "load_mauna_loa", "load_mauna_loa_training",
     "SamplerDiagnostics",
     "build_toy_candidates", "LinearModel", "SinusoidalModel", "SinLinearModel", "QuadraticModel",
     "extract_gp_predictives", "compute_G_matrix", "run_bms_star", "soft_transfer",
     "aggregate_convention", "boltzmann_weight_ess", "hard_win_statistics", "PredictiveList",
     "kl_forward", "kl_backward", "kl_symmetric", "hellinger_distance",
     "pw_kl_forward", "pw_kl_backward", "pw_kl_symmetric", "pw_hellinger", "pw_mse", "pw_nll",
     "METRICS",
     "plot_bms_star_results", "plot_G_heatmaps", "plot_candidate_predictions", "print_bms_star_table",
     "PRIOR_CONFIGS", "ExperimentConfig", "build_kernels_from_config", "build_likelihood_from_config",
diff --git a/bistar_gp/aggregation_v3.py b/bistar_gp/aggregation_v3.py
index 578a5cf..7093e90 100644
--- a/bistar_gp/aggregation_v3.py
+++ b/bistar_gp/aggregation_v3.py
@@ -23,31 +23,32 @@ Three fixes, each attacking a different part of the problem:
     High-likelihood samples (well-fitting hyperparameters) count more;
     outlier samples (very long/short lengthscales) get downweighted.
 """
 
 import logging
 
 import numpy as np
 import torch
 from scipy.special import logsumexp
 from typing import List, Dict, Optional, Tuple
 from dataclasses import dataclass
 
 from bistar_gp.bms_star import (
     GPPosteriorSample, METRICS, compute_G_matrix, BMSStarResult,
     _extract_marginals, _assert_candidate_universes_consistent,
-    aggregate_convention, hard_win_statistics, log_weight_ess,
+    _require_sample_sites, aggregate_convention, hard_win_statistics,
+    log_weight_ess,
 )
 
 logger = logging.getLogger(__name__)
 
 torch.set_default_dtype(torch.float64)
 
 
 # ═══════════════════════════════════════════════════════════════════
 # Strategy 1: Averaged GP Posterior
 # ═══════════════════════════════════════════════════════════════════
 
 def average_gp_posterior(gp_samples: List[GPPosteriorSample],
                          weights=None) -> GPPosteriorSample:
     """
     Collapse GP samples into one averaged predictive distribution.
@@ -234,37 +235,44 @@ def robust_trimmed_mean(G_matrix: np.ndarray,
         summary_values=trimmed_means,
         posteriors=posteriors,
     )
 
 
 def robust_rank(G_matrix: np.ndarray,
                 instance_names: List[str],
                 metric_name: str = "") -> RobustResult:
     """
     Rank-based aggregation: for each GP sample, rank candidates 1-K
     (1 = lowest G = best). Then average ranks across samples.
 
     Completely nonparametric — immune to scale differences between
     GP samples. A model that consistently ranks #1 or #2 wins,
     regardless of the absolute G values.
+
+    Exactly tied candidates share the average of their ranks (fix pass 2a,
+    SYNTHESIS A-7; the tie rule of hard_win_statistics), so the result does
+    not depend on column order; the double argsort it replaces ranked ties
+    by position.
     """
+    from scipy.stats import rankdata
+
     n_psi, n_theta = G_matrix.shape
 
     # For each row (GP sample), compute ranks
     ranks = np.zeros_like(G_matrix)
     for i in range(n_psi):
-        ranks[i] = np.argsort(np.argsort(G_matrix[i])) + 1  # 1-indexed
+        ranks[i] = rankdata(G_matrix[i], method="average")  # 1-indexed
 
     avg_ranks = ranks.mean(axis=0)
 
     # Lower rank → better → higher posterior
     # Convert: use exp(-rank) and normalize
     log_scores = -avg_ranks
     log_scores -= log_scores.max()
     scores = np.exp(log_scores)
     posteriors = scores / scores.sum()
 
     return RobustResult(
         metric_name=metric_name,
         method="rank",
         instance_names=list(instance_names),
         summary_values=avg_ranks,
@@ -344,31 +352,36 @@ def compute_log_marginal_likelihoods(
                 noise_prior=GammaPrior(1.75, 1.0),
             )
 
     log_mlls = np.zeros(len(gp_samples))
 
     for idx, sample in enumerate(gp_samples):
         kernels, names = kernel_builder()
         fresh_lik = likelihood_builder()
         fresh_model, fresh_lik = build_model(x_t, y_t, kernels, names, fresh_lik)
 
         # Set hyperparameters OUTSIDE the numerical handler below. A site the
         # model does not recognize is a silent-wrong-answer path (the
         # likelihood would be scored at the fresh model's initialization
         # value), so it raises and the error must escape (FIX-1; review R1
         # found the pass-1 raise sitting inside the handler that converts
-        # numerical failures into -inf).
+        # numerical failures into -inf). A sampled site the draw does not
+        # carry would be scored at its initialization value, so it raises
+        # too (fix pass 2a, SYNTHESIS A-3).
+        _require_sample_sites(fresh_model, sample.hyperparameters,
+                              f"compute_log_marginal_likelihoods (draw {idx})",
+                              strict=True)
         for pyro_name, val in sample.hyperparameters.items():
             if not apply_hp_value(fresh_model, fresh_lik, pyro_name, val):
                 raise ValueError(
                     f"compute_log_marginal_likelihoods: apply_hp_value did "
                     f"not recognize site {pyro_name!r} for draw {idx}")
 
         fresh_model.eval()
         fresh_lik.eval()
 
         try:
             with torch.no_grad():
                 noise_var = fresh_lik.noise.item()
                 K_XX = fresh_model.covar_module(x_t, x_t).evaluate().detach()
                 L = compute_cholesky(K_XX, noise_var, jitter)
 
diff --git a/bistar_gp/bms_star.py b/bistar_gp/bms_star.py
index 00469b6..125b6b7 100644
--- a/bistar_gp/bms_star.py
+++ b/bistar_gp/bms_star.py
@@ -4,30 +4,32 @@ BMS* (Bayesian Model Selection Star) implementation.
 Extends Bayesian induction (Chandramouli & Shiffrin, 2016) by:
 1. Using GP hyperpriors to define prior/posterior over data distributions (ψ)
 2. Computing divergence G between GP posterior samples and candidate model predictions
 3. Soft transfer: transferring GP-derived posteriors onto candidate model instances
 
 Supports: KL(ψ||θ), KL(θ||ψ), Symmetric KL, Hellinger distance
 """
 
 import logging
 
 import numpy as np
 import torch
 from typing import List, Dict, Tuple, Optional
 from dataclasses import dataclass
 
+from .errors import EvaluationFailure
+
 torch.set_default_dtype(torch.float64)
 logger = logging.getLogger(__name__)
 
 
 # ═══════════════════════════════════════════════════════════════════
 # Divergence Metrics for Multivariate Gaussians
 # ═══════════════════════════════════════════════════════════════════
 
 def _safe_logdet(M):
     """Log determinant via Cholesky with jitter fallback."""
     n = M.shape[0]
     for jitter in [0.0, 1e-10, 1e-8, 1e-6, 1e-4]:
         try:
             L = np.linalg.cholesky(M + jitter * np.eye(n))
             return 2.0 * np.sum(np.log(np.diag(L)))
@@ -243,30 +245,93 @@ class PredictiveList(list):
     the returned ensemble is a numerically selected subset of the draws.
     """
 
     def __init__(self, items=(), attempted_indices=None, retained_indices=None,
                  dropped=None):
         super().__init__(items)
         self.attempted_indices = list(attempted_indices or [])
         self.retained_indices = list(retained_indices or [])
         self.dropped = list(dropped or [])   # (draw index, reason) pairs
 
     @property
     def n_dropped(self):
         return len(self.dropped)
 
 
+def sample_draw_count(mcmc_samples, keys, caller):
+    """The one nonempty leading length shared by the sample arrays `keys`.
+
+    Checked before any draw is indexed, with a message listing every length
+    by sorted key, so a ragged dictionary raises the same ValueError whatever
+    its order (fix pass 2a, SYNTHESIS A-3: the draw count used to come from
+    whichever key came first, so one order dropped a draw silently and
+    another raised IndexError).
+    """
+    lengths = {k: (np.shape(mcmc_samples[k])[0] if np.ndim(mcmc_samples[k]) else None)
+               for k in keys}
+    distinct = set(lengths.values())
+    if len(distinct) != 1 or None in distinct or 0 in distinct:
+        detail = ", ".join(f"{k}: {lengths[k]}" for k in sorted(lengths))
+        raise ValueError(f"{caller}: the sample arrays must share one nonempty "
+                         f"leading length; got {detail}")
+    return distinct.pop()
+
+
+def missing_sample_sites(model, supplied_keys):
+    """Sampled hyperparameter sites of `model` that `supplied_keys` does not
+    supply (fix pass 2a, SYNTHESIS A-3).
+
+    The inventory is ``model.named_priors()``: one pyro sample site per
+    prior, the set fit_hmc samples (a parameter without a prior, such as the
+    frozen Mauna period, is not sampled and not required). Supplied names are
+    compared under the aliases select_hmc_sites and apply_hp_value accept:
+    "kernel_components.{i}." for "covar_module.kernels.{i}.", the bare
+    "noise_covar.noise_prior", and component 0 of a single-kernel model, whose
+    kernel is covar_module itself. A missing site would otherwise keep the
+    fresh model's initialization value in every draw.
+    """
+    components = getattr(model, "kernel_components", None) or []
+    single = len(components) == 1 and model.covar_module is components[0]
+
+    def canonical(name):
+        if name.endswith("noise_covar.noise_prior"):
+            return "likelihood.noise_covar.noise_prior"
+        for prefix in ("covar_module.kernels.", "kernel_components."):
+            if name.startswith(prefix):
+                idx, _, rest = name[len(prefix):].partition(".")
+                if single and idx == "0":
+                    return f"covar_module.{rest}"
+                return f"covar_module.kernels.{idx}.{rest}"
+        return name
+
+    supplied = {canonical(k) for k in supplied_keys}
+    return sorted(name for name, *_ in model.named_priors()
+                  if canonical(name) not in supplied)
+
+
+def _require_sample_sites(model, supplied_keys, caller, strict):
+    """Raise (strict) or warn naming every required site the supply lacks."""
+    missing = missing_sample_sites(model, supplied_keys)
+    if missing:
+        msg = (f"{caller}: the samples supply no draws for the sampled site(s) "
+               f"{missing}; every draw would keep the fresh model's "
+               "initialization value for them")
+        if strict:
+            raise ValueError(msg)
+        logger.warning(msg)
+
+
 def extract_gp_predictives(model, likelihood, x_train, y_train, x_eval,
                            mcmc_samples, kernel_builder,
                            likelihood_builder=None,
                            n_posterior_samples=200, jitter=1e-4,
                            condition_on_data=True, rng=None, strict=True):
     """
     Extract full GP predictive distributions for each hyperparameter sample.
 
     Each sample defines a specific GP with specific hyperparameters,
     which implies a specific multivariate Gaussian over y at x_eval.
     These are the ψ's in BMS*.
 
     condition_on_data selects which predictive, so the SAME machinery serves both
     Bayesian-workflow checks:
       True  (default): POSTERIOR predictive p(y* | X, y, θ) — condition on the
@@ -280,80 +345,88 @@ def extract_gp_predictives(model, likelihood, x_train, y_train, x_eval,
         likelihood: fitted likelihood
         x_train, y_train: training data (used only when condition_on_data=True)
         x_eval: evaluation points
         mcmc_samples: dict from fit_hmc (posterior) or sample_prior (prior)
         kernel_builder: callable returning (kernels, names)
         likelihood_builder: callable returning a likelihood. If None, uses
                            default with Positive() constraint.
         n_posterior_samples: how many samples to use
         jitter: numerical stability
         condition_on_data: posterior (True) vs prior (False) predictive
         rng: optional numpy.random.Generator for the draw subsampling;
              None preserves the legacy global-np.random behavior
         strict: True (default) raises on any silent-wrong-answer path: a
              sample site apply_hp_value does not recognize, an exception
              while applying a site, a sample dict with no recognized kernel
-             site, or a draw whose predictive fails numerically. False keeps
-             the pre-2026-09 behavior (warn, skip the site or drop the draw)
-             for exploratory use; the dropped draws are then recorded on the
-             returned PredictiveList.
+             site, a sampled site of the model with no draws supplied
+             (missing_sample_sites), or a draw whose predictive fails
+             numerically. False keeps the pre-2026-09 behavior (warn, skip
+             the site or drop the draw) for exploratory use; the dropped
+             draws are then recorded on the returned PredictiveList. Sample
+             arrays of unequal length raise under either setting.
 
     Returns:
         PredictiveList (a list of GPPosteriorSample carrying
         attempted_indices, retained_indices, dropped, n_dropped)
     """
     from .model import build_model, select_hmc_sites, apply_hp_value
     from .decompose import compute_cholesky
     import gpytorch
     from gpytorch.constraints import Positive
     from gpytorch.priors import GammaPrior
 
     def _default_likelihood():
         return gpytorch.likelihoods.GaussianLikelihood(
             noise_constraint=Positive(),
             noise_prior=GammaPrior(1.75, 1.0),
         )
 
     if likelihood_builder is None:
         likelihood_builder = _default_likelihood
 
     x_train = x_train.double() if isinstance(x_train, torch.Tensor) else torch.tensor(x_train).double()
     y_train = y_train.double() if isinstance(y_train, torch.Tensor) else torch.tensor(y_train).double()
     x_eval = x_eval.double() if isinstance(x_eval, torch.Tensor) else torch.tensor(x_eval).double()
 
-    first_key = list(mcmc_samples.keys())[0]
-    total_mcmc = len(mcmc_samples[first_key])
-    n_take = min(n_posterior_samples, total_mcmc)
-    if rng is not None:
-        indices = rng.choice(total_mcmc, n_take, replace=False)
-    else:
-        # legacy path: global np.random state (callers that need
-        # reproducibility without the rng= parameter seed globally)
-        indices = np.random.choice(total_mcmc, n_take, replace=False)
-
     relevant_keys = select_hmc_sites(mcmc_samples.keys())
     kernel_keys = [k for k in relevant_keys
                    if not k.endswith("noise_covar.noise_prior")]
     if not kernel_keys:
         msg = ("extract_gp_predictives: no kernel hyperparameter site was "
                f"recognized among {sorted(mcmc_samples.keys())}; every "
                "predictive would be built at the fresh model's initialization "
                "kernel values (only the noise would vary)")
         if strict:
             raise ValueError(msg)
         logger.warning(msg)
 
+    # Fix pass 2a, SYNTHESIS A-3: one draw count shared by every indexed
+    # array, and a draw for every site the model samples.
+    total_mcmc = sample_draw_count(mcmc_samples, relevant_keys or list(mcmc_samples),
+                                   "extract_gp_predictives")
+    kernels, names = kernel_builder()
+    probe_model, _ = build_model(x_train, y_train, kernels, names, likelihood_builder())
+    _require_sample_sites(probe_model, relevant_keys, "extract_gp_predictives", strict)
+
+    n_take = min(n_posterior_samples, total_mcmc)
+    if rng is not None:
+        indices = rng.choice(total_mcmc, n_take, replace=False)
+    else:
+        # legacy path: global np.random state (callers that need
+        # reproducibility without the rng= parameter seed globally)
+        indices = np.random.choice(total_mcmc, n_take, replace=False)
+
     results = []
     retained = []
     dropped = []
 
     for idx in indices:
         kernels, names = kernel_builder()
         fresh_likelihood = likelihood_builder()
         fresh_model, fresh_likelihood = build_model(x_train, y_train, kernels, names, fresh_likelihood)
 
         # Set parameters from this MCMC sample. Only values that were
         # actually applied are recorded as the draw's hyperparameters.
         hp_dict = {}
         for pyro_name in relevant_keys:
             val = float(mcmc_samples[pyro_name][idx])
             try:
@@ -529,91 +602,117 @@ def hard_win_statistics(G_matrix: np.ndarray):
 
 
 def compute_G_matrix(gp_samples: List[GPPosteriorSample],
                      candidate_results: list,
                      metric_name: str = "kl_forward") -> np.ndarray:
     """
     Compute divergence matrix G[i, j] = G(ψ_i, θ_j).
 
     Args:
         gp_samples: list of GPPosteriorSample (the ψ's)
         candidate_results: list of CandidateResult (the θ's)
         metric_name: one of 'kl_forward', 'kl_backward', 'kl_symmetric', 'hellinger'
 
     Returns:
         G matrix of shape (n_psi, n_theta)
+
+    Raises:
+        EvaluationFailure when no entry is finite, or when some candidate has
+        no finite entry: a candidate that failed on every draw is a failure,
+        not an extremely poor fit (fix pass 2a, SYNTHESIS A-1). ValueError for
+        an empty table (no draws or no candidates).
     """
     # A4 universe firewall at the boundary that still holds candidate
     # metadata (2026-09 review FIX-4): every path that builds a G matrix
     # through the package passes here, including the aggregation_v3 entry
     # points that never call run_bms_star.
     _assert_candidate_universes_consistent(candidate_results)
 
     metric_fn = METRICS[metric_name]          # registers metrics_v2 on a miss
     n_psi = len(gp_samples)
     n_theta = len(candidate_results)
+    if n_psi == 0 or n_theta == 0:
+        raise ValueError(f"compute_G_matrix({metric_name}): empty table "
+                         f"({n_psi} draws x {n_theta} candidates)")
     G = np.zeros((n_psi, n_theta))
 
     for i, psi in enumerate(gp_samples):
         for j, theta in enumerate(candidate_results):
             try:
                 G[i, j] = metric_fn(psi.mean, psi.cov, theta.mean, theta.cov)
             except (np.linalg.LinAlgError, ValueError):
                 G[i, j] = np.inf
 
-    # Replace any inf/nan with a value guaranteed to be WORSE (larger) than any
-    # finite divergence. A plain `10 * max_finite` is wrong when the metric can
-    # be negative (e.g. pw_nll, whose 0.5*log(2*pi*sigma^2) term goes negative):
-    # 10*max_finite would then be the *smallest* G, so a failed computation would
-    # win the comparison. This penalty is always strictly greater than max_finite.
-    if np.any(np.isfinite(G)):
-        max_finite = np.nanmax(G[np.isfinite(G)])
-        penalty = max_finite + 10.0 * (abs(max_finite) + 1.0)
-    else:
-        penalty = 1e6
-    G = np.where(np.isfinite(G), G, penalty)
-
-    return G
+    failed = ~np.isfinite(G)
+    if not failed.any():
+        return G
+    names = [getattr(c, "name", str(j)) for j, c in enumerate(candidate_results)]
+    if failed.all():
+        raise EvaluationFailure(
+            f"compute_G_matrix({metric_name}): all {G.size} divergence "
+            f"evaluations ({n_psi} draws x {n_theta} candidates) failed")
+    dead = [names[j] for j in np.flatnonzero(failed.all(axis=0))]
+    if dead:
+        raise EvaluationFailure(
+            f"compute_G_matrix({metric_name}): candidate(s) {dead} failed on "
+            f"every one of the {n_psi} draws")
+    # A partial failure keeps a penalty strictly WORSE (larger) than every
+    # finite divergence, also for negative-valued metrics (pw_nll: a plain
+    # 10 * max_finite would be the smallest G and win), and is announced
+    # with (name, count) pairs, so repeated names keep separate counts.
+    per_candidate = [(names[j], int(n)) for j, n in enumerate(failed.sum(axis=0)) if n]
+    logger.warning(
+        "compute_G_matrix(%s): %d of %d divergence evaluations failed %s; each "
+        "is scored with a penalty worse than every finite value",
+        metric_name, int(failed.sum()), G.size, per_candidate)
+    max_finite = np.max(G[~failed])
+    return np.where(failed, max_finite + 10.0 * (abs(max_finite) + 1.0), G)
 
 
 def soft_transfer(G_matrix: np.ndarray, tau: float,
                   instance_names: List[str],
                   class_names: Optional[List[str]] = None,
                   normalize_per_draw: bool = False,
-                  metric_name: Optional[str] = None) -> BMSStarResult:
+                  metric_name: Optional[str] = None,
+                  ess_warn: Optional[float] = 100.0) -> BMSStarResult:
     """
     Soft BMS* scoring.
 
     score(θ_j) = (1/N) Σ_i exp(-G(ψ_i, θ_j) / τ)
 
     Class level: only the one-instance-per-class mapping is supported, in
     which class posteriors equal instance posteriors. Any ``class_names``
     that groups instances raises rather than silently returning instance
     posteriors under a class label (2026-09 review FIX-3).
 
     Args:
         G_matrix: (n_psi, n_theta) divergence matrix
         tau: temperature parameter
         instance_names: names for each θ
         class_names: None or a 1:1 relabelling of the instances
         normalize_per_draw: if True, subtract per-row minimum before
             Boltzmann weighting. This removes systematic offset so that
             only *relative* divergence within each GP draw matters.
             Prevents microscopic absolute bias from being amplified
             into false certainty across many draws.
         metric_name: the divergence that produced G_matrix. None is recorded
             as "unspecified" rather than an invented identity.
+        ess_warn: log a warning when the smallest per-candidate weight_ess
+            falls below this floor, as is_log_Z_Mx does for its weights
+            (fix pass 2a, SYNTHESIS A-13); None disables it. The weight ESS
+            measures how many draws carry a candidate's pooled score; it is
+            not an MCMC effective sample size.
 
     Returns:
         BMSStarResult with normalized posteriors and draw-level diagnostics
     """
     n_psi, n_theta = G_matrix.shape
     if not np.all(np.isfinite(G_matrix)):
         # A NaN or infinite divergence is never a score. compute_G_matrix
         # returns finite penalties, so only a hand-built matrix reaches this;
         # the pre-fix code returned a uniform posterior for it (review F4).
         raise ValueError("soft_transfer: G_matrix contains non-finite entries")
 
     if len(instance_names) != n_theta:
         raise ValueError(
             f"soft_transfer: {len(instance_names)} instance_names for "
             f"{n_theta} candidate columns")
@@ -647,30 +746,38 @@ def soft_transfer(G_matrix: np.ndarray, tau: float,
 
     # Normalize to get instance posteriors
     total = instance_scores.sum()
     if total > 0:
         instance_posteriors = instance_scores / total
     else:
         instance_posteriors = np.ones(n_theta) / n_theta
 
     # Class posteriors = instance posteriors (1:1 mapping, enforced above)
     class_posteriors = instance_posteriors.copy()
 
     # Draw-level diagnostics on the weights actually aggregated (G_effective)
     # and the tau-free win statistics on the raw matrix.
     weight_ess = boltzmann_weight_ess(G_effective, tau)
     credit, attainment, tie_fraction = hard_win_statistics(G_matrix)
+    if ess_warn is not None and np.min(weight_ess) < ess_warn:
+        worst = int(np.argmin(weight_ess))
+        logger.warning(
+            "soft_transfer(%s, tau=%g): weight ESS below %g for %s (min %.1f of "
+            "%d draws, %s); the pooled score rests on few draws",
+            metric_name or "unspecified", tau, ess_warn,
+            [n for n, e in zip(instance_names, weight_ess) if e < ess_warn],
+            float(weight_ess[worst]), n_psi, instance_names[worst])
 
     return BMSStarResult(
         metric_name=metric_name if metric_name is not None else "unspecified",
         tau=tau,
         instance_names=list(instance_names),
         instance_scores=instance_scores,
         instance_posteriors=instance_posteriors,
         class_names=list(class_names),
         class_posteriors=class_posteriors,
         G_matrix=G_matrix,
         weight_ess=weight_ess,
         hard_win_credit=credit,
         attainment=attainment,
         tie_fraction=tie_fraction,
     )
@@ -782,35 +889,41 @@ def run_bms_star(gp_samples: List[GPPosteriorSample],
                 "run_bms_star: the primary metric %s is not in the implicit "
                 "roster (metrics_v2 not imported yet); pass metric_names "
                 "explicitly to score it", PRIMARY_METRIC)
 
     _assert_candidate_universes_consistent(candidate_results)
 
     instance_names = [cr.name for cr in candidate_results]
     results = {}
 
     for metric_name in metric_names:
         print(f"\n  Computing G matrix: {metric_name}...")
         G = compute_G_matrix(gp_samples, candidate_results, metric_name)
 
         print(f"    G stats — min: {G.min():.2f}, median: {np.median(G):.2f}, max: {G.max():.2f}")
 
-        # Per-draw diagnostic: how often does each model win raw?
-        raw_winners = np.argmin(G, axis=1)
+        # Per-draw diagnostic: how often does each model win raw? Exact ties
+        # split the draw's credit (fix pass 2a, SYNTHESIS A-13: a first-index
+        # argmin gave every tie to the first candidate).
+        credit, attainment, tie_fraction = hard_win_statistics(G)
+        n_draws = G.shape[0]
         for m_idx, name in enumerate(instance_names):
-            n_wins = np.sum(raw_winners == m_idx)
-            print(f"    {name} wins {n_wins}/{len(raw_winners)} draws (raw G)")
+            print(f"    {name} wins {credit[m_idx] * n_draws:g}/{n_draws} draws "
+                  f"(raw G, ties split; attains the minimum on "
+                  f"{attainment[m_idx] * n_draws:g})")
+        if tie_fraction:
+            print(f"    tied minimum on {tie_fraction * n_draws:g} draws")
 
         if normalize_per_draw:
             row_deltas = G - G.min(axis=1, keepdims=True)
             for m_idx, name in enumerate(instance_names):
                 mean_delta = row_deltas[:, m_idx].mean()
                 print(f"    {name} mean Δ from best: {mean_delta:.4f}")
 
         results[metric_name] = {}
         for tau in taus:
             bms_result = soft_transfer(G, tau, instance_names,
                                        normalize_per_draw=normalize_per_draw,
                                        metric_name=metric_name)
             results[metric_name][tau] = bms_result
 
     return results
diff --git a/bistar_gp/candidates.py b/bistar_gp/candidates.py
index f89b650..a573e20 100644
--- a/bistar_gp/candidates.py
+++ b/bistar_gp/candidates.py
@@ -3,30 +3,32 @@ Parametric candidate models for BMS* comparison.
 
 Each model has:
     fit(x, y)       → learn parameters via MLE
     predict(x_eval) → (mean, cov) predictive distribution
     name            → string identifier
     params()        → dict of fitted parameters
 """
 
 import logging
 
 import numpy as np
 from scipy.optimize import minimize
 from dataclasses import dataclass
 from typing import Tuple, Dict, Optional
 
+from .errors import EvaluationFailure
+
 logger = logging.getLogger(__name__)
 
 
 @dataclass
 class CandidateResult:
     """Predictive distribution from a candidate model."""
     name: str
     mean: np.ndarray          # (n_eval,)
     cov: np.ndarray           # (n_eval, n_eval)
     noise_var: float
     parameters: Dict[str, float]
     # Universe identity for the Mauna A4 separate-normalization rule: stamped
     # by _make_result from the producing model's tag, so the guard can
     # validate the exact list handed to run_bms_star rather than the model
     # list it was derived from. None for non-registry candidates (the toy
@@ -81,30 +83,42 @@ class CandidateModel:
     @staticmethod
     def _select_restart(candidates, model_name):
         """Pick the best restart, preferring successful optimizer reports;
         fall back to the best overall with a warning when none succeeded.
         candidates: list of (params, nll, status)."""
         if not candidates:
             return None
         ok = [c for c in candidates if c[2]["success"]]
         pool = ok if ok else candidates
         if not ok:
             logger.warning("%s: no restart reported convergence (%s); using the "
                            "best non-converged result", model_name,
                            candidates[0][2]["message"])
         return min(pool, key=lambda c: c[1])
 
+    @staticmethod
+    def _require_restart(best, model_name, errors):
+        """The selected restart, or EvaluationFailure when every restart
+        raised: a preset parameter vector is not a fitted candidate (fix pass
+        2a, SYNTHESIS A-6; the sinusoid fits used to fall back silently to
+        A = omega = 1, phi = 0, sigma = std(y))."""
+        if best is None:
+            raise EvaluationFailure(
+                f"{model_name}: every one of the {len(errors)} optimizer restarts "
+                f"raised; no fitted candidate exists (last: {errors[-1] if errors else 'none'})")
+        return best
+
     def _make_result(self, x_eval, mean, noise_var, params_dict):
         """Build CandidateResult with isotropic noise covariance."""
         n = len(x_eval)
         cov = noise_var * np.eye(n)
         return CandidateResult(
             name=self.name,
             mean=mean,
             cov=cov,
             noise_var=noise_var,
             parameters=params_dict,
             universe=getattr(self, "universe", None),
         )
 
 
 class LinearModel(CandidateModel):
@@ -141,95 +155,85 @@ class SinusoidalModel(CandidateModel):
 
     name = "Sinusoidal"
 
     def __init__(self):
         self.A = 1.0
         self.omega = 1.0
         self.phi = 0.0
         self.sigma = 1.0
 
     def fit(self, x, y):
         def f(x, params):
             return params[0] * np.sin(params[1] * x + params[2])
 
         # Try multiple initializations (omega is tricky); prefer restarts
         # whose optimizer reported success (FIX-5).
-        restarts = []
+        restarts, errors = [], []
         for omega_init in [0.5, 1.0, 1.5, 2.0]:
             for A_init in [0.5, 1.0, 2.0]:
                 p0 = [A_init, omega_init, 0.0, np.log(0.5)]
                 try:
                     restarts.append(self._fit_mle(x, y, f, p0, return_status=True))
-                except Exception:
-                    continue
-        best = self._select_restart(restarts, self.name)
-        best_params = best[0] if best is not None else None
-
-        if best_params is not None:
-            self.A, self.omega, self.phi = best_params[0], best_params[1], best_params[2]
-            self.sigma = np.exp(best_params[3])
-        else:
-            # Fallback: just use initial
-            self.A, self.omega, self.phi = 1.0, 1.0, 0.0
-            self.sigma = np.std(y)
+                except Exception as exc:
+                    errors.append(f"{type(exc).__name__}: {exc}")
+        best = self._require_restart(self._select_restart(restarts, self.name),
+                                     self.name, errors)
+        best_params = best[0]
+        self.A, self.omega, self.phi = best_params[0], best_params[1], best_params[2]
+        self.sigma = np.exp(best_params[3])
 
     def predict(self, x_eval):
         mean = self.A * np.sin(self.omega * x_eval + self.phi)
         return self._make_result(
             x_eval, mean, self.sigma**2,
             {"A": self.A, "omega": self.omega, "phi": self.phi, "sigma": self.sigma},
         )
 
 
 class SinLinearModel(CandidateModel):
     """y = A * sin(omega * x + phi) + b * x + c + eps"""
 
     name = "Sin+Linear"
 
     def __init__(self):
         self.A = 1.0
         self.omega = 1.0
         self.phi = 0.0
         self.b = 0.0
         self.c = 0.0
         self.sigma = 1.0
 
     def fit(self, x, y):
         def f(x, params):
             return params[0] * np.sin(params[1] * x + params[2]) + params[3] * x + params[4]
 
-        restarts = []
+        restarts, errors = [], []
         for omega_init in [0.5, 1.0, 1.5, 2.0]:
             p0 = [1.0, omega_init, 0.0, 0.25, 0.0, np.log(0.3)]
             try:
                 restarts.append(self._fit_mle(x, y, f, p0, return_status=True))
-            except Exception:
-                continue
-        best = self._select_restart(restarts, self.name)
-        best_params = best[0] if best is not None else None
-
-        if best_params is not None:
-            self.A = best_params[0]
-            self.omega = best_params[1]
-            self.phi = best_params[2]
-            self.b = best_params[3]
-            self.c = best_params[4]
-            self.sigma = np.exp(best_params[5])
-        else:
-            self.A, self.omega, self.phi = 1.0, 1.0, 0.0
-            self.b, self.c = 0.25, 0.0
-            self.sigma = np.std(y)
+            except Exception as exc:
+                errors.append(f"{type(exc).__name__}: {exc}")
+        best = self._require_restart(self._select_restart(restarts, self.name),
+                                     self.name, errors)
+        best_params = best[0]
+        self.A = best_params[0]
+        self.omega = best_params[1]
+        self.phi = best_params[2]
+        self.b = best_params[3]
+        self.c = best_params[4]
+        self.sigma = np.exp(best_params[5])
 
     def predict(self, x_eval):
         mean = self.A * np.sin(self.omega * x_eval + self.phi) + self.b * x_eval + self.c
         return self._make_result(
             x_eval, mean, self.sigma**2,
             {"A": self.A, "omega": self.omega, "phi": self.phi,
              "b": self.b, "c": self.c, "sigma": self.sigma},
         )
 
 
 class QuadraticModel(CandidateModel):
     """y = a * x^2 + b * x + c + eps"""
 
     name = "Quadratic"
 
diff --git a/bistar_gp/config.py b/bistar_gp/config.py
index 162a560..6dbabe6 100644
--- a/bistar_gp/config.py
+++ b/bistar_gp/config.py
@@ -12,36 +12,61 @@ import os
 from dataclasses import dataclass, field
 from typing import Dict, List, Optional, Tuple
 
 # ── Paths ─────────────────────────────────────────────────────────
 
 CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
 RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
 
 # ── Metric roles (W1) and withdrawn caches (M2bR banner) ───────────
 # 2026-09 review FIX-7. The manuscript's primary metric and the appendix-only
 # stress metric; generic APIs keep their defaults, manuscript-facing code
 # and run_bms_star's implicit path refer to these names.
 PRIMARY_METRIC = "pw_kl_vcal"
 APPENDIX_METRICS = ("kl_forward",)
 
-# Caches the M2bR banner withdrew: `informative`-config HMC draws produced by
-# the pre-D6/D22 sampler. load_hmc_samples refuses them unless the caller
-# passes allow_withdrawn=True (and then warns). Entries ending in "/" are
-# directory prefixes; the rest are file paths relative to the repository.
+# Sampler caches whose draws the M2bR record withdrew (D33 and D34; all were
+# produced by the pre-D22 samplers, whose target was p(theta) L(theta)^N).
+# load_hmc_samples refuses them unless the caller passes allow_withdrawn=True
+# (and then warns). Entries ending in "/" are directory prefixes; the rest
+# are file paths relative to the repository. The list is derived from the
+# D33/D34 classification (fix pass 2a, SYNTHESIS A-24); the fit-method study
+# ran the informative config only (experiments/fit_method_metric_comparison.py).
 WITHDRAWN_CACHES = (
+    # D33 supersession determination: informative stays WITHDRAWN/UNVALIDATED
+    # (td10 uncapped and td7 capped; td7 and td10 behave identically there).
     "runs/fit_method_metric_comparison/samples_hmc.npz",
+    "runs/fit_method_metric_comparison/samples_hmc_td7.npz",
+    "runs/prior_sensitivity/samples_informative_hmc_td7.npz",
+    "runs/prior_sensitivity/samples_informative_hmc_td10.npz",
+    # D33 (informative stays withdrawn) with D22/D26: hmc_laplace is
+    # Laplace-whitened NUTS on the same defective informative target.
+    "runs/fit_method_metric_comparison/samples_hmc_laplace.npz",
+    "runs/fit_method_metric_comparison/samples_hmc_laplace_td7.npz",
+    # D33: vague and gamma_relaxed had single-chain audit runs only, so their
+    # historical HMC numbers remain withdrawn.
+    "runs/prior_sensitivity/samples_vague_hmc_td7.npz",
+    "runs/prior_sensitivity/samples_gamma_relaxed_hmc_td7.npz",
+    # D34 ratification 2 (interim-withdrawn W3): every historical VI value.
+    "runs/fit_method_metric_comparison/samples_vi.npz",
+    "runs/fit_method_metric_comparison/samples_vi_td7.npz",
+    "runs/prior_sensitivity/samples_informative_vi_td7.npz",
+    "runs/prior_sensitivity/samples_vague_vi_td7.npz",
+    "runs/prior_sensitivity/samples_gamma_relaxed_vi_td7.npz",
+    "runs/prior_sensitivity/samples_toy_elicited_vi_td7.npz",
+    # D68 FIX-7 (M2bR banner): the toy tau-metric comparison was built on the
+    # withdrawn informative HMC cache above.
     "runs/toy_tau_metric_comparison/",
 )
 
 
 def is_withdrawn_cache(path) -> bool:
     """True when `path` names, or lies under, a withdrawn cache entry."""
     norm = os.path.normpath(os.path.abspath(str(path))).replace(os.sep, "/")
     for entry in WITHDRAWN_CACHES:
         if entry.endswith("/"):
             if "/" + entry.rstrip("/") + "/" in norm + "/":
                 return True
         elif norm.endswith("/" + entry) or norm == entry:
             return True
     return False
 
@@ -241,40 +266,40 @@ class ExperimentConfig:
 
 # ── Cache I/O ─────────────────────────────────────────────────────
 
 def save_hmc_samples(samples: Dict, path: str):
     """Save HMC samples dict to .npz file."""
     os.makedirs(os.path.dirname(path), exist_ok=True)
     # numpy savez expects arrays
     import numpy as np
     np.savez(path, **{k: np.array(v) for k, v in samples.items()})
     print(f"  Cached HMC samples → {path}")
 
 
 def load_hmc_samples(path: str, allow_withdrawn: bool = False) -> Dict:
     """Load HMC samples from .npz file.
 
-    Refuses the caches the M2bR banner withdrew (WITHDRAWN_CACHES) unless
+    Refuses the caches the M2bR record withdrew (WITHDRAWN_CACHES) unless
     allow_withdrawn=True is passed explicitly, in which case it warns; a
     figure or number built from them must be labelled as withdrawn material.
     """
     import warnings
     import numpy as np
     if is_withdrawn_cache(path):
-        msg = (f"{path} is a WITHDRAWN cache (M2bR banner: informative-config "
-               "HMC draws from the pre-D6/D22 sampler must never be cited); "
-               "pass allow_withdrawn=True only for explicitly labelled archival "
+        msg = (f"{path} is a WITHDRAWN cache (M2bR banner, D33/D34: draws from "
+               "the pre-D22 samplers must never be cited); pass "
+               "allow_withdrawn=True only for explicitly labelled archival "
                "reproduction")
         if not allow_withdrawn:
             raise RuntimeError(msg)
         warnings.warn(msg, UserWarning, stacklevel=2)
     data = np.load(path)
     samples = {k: data[k] for k in data.files}
     print(f"  Loaded cached HMC samples ← {path}")
     return samples
 
 
 # ── Kernel Builder from Config ────────────────────────────────────
 
 def build_kernels_from_config(prior_config: PriorConfig):
     """
     Build GP kernel components with priors from a PriorConfig.
diff --git a/bistar_gp/debias.py b/bistar_gp/debias.py
index 1385e5c..030c713 100644
--- a/bistar_gp/debias.py
+++ b/bistar_gp/debias.py
@@ -19,30 +19,31 @@ containing every component reproduces the full posterior exactly.
 """
 
 import functools
 import logging
 import operator
 
 import torch
 import numpy as np
 from typing import Dict, List, Optional, Sequence, Tuple
 from dataclasses import dataclass, field
 
 from .decompose import (
     decompose_additive_gp, decompose_component, compute_cholesky,
     sample_from_component, mixture_central_interval,
 )
+from .bms_star import sample_draw_count, _require_sample_sites
 
 logger = logging.getLogger(__name__)
 
 
 @dataclass
 class ComponentResult:
     """Posterior summary of one additive component (or of a component group).
 
     ``mean``, ``std`` and ``cov`` are TOTAL posterior moments over the
     retained hyperparameter draws (law of total variance). ``samples`` keeps
     its historical position and meaning for the MAP path (function draws);
     on the draw-based paths it holds the per-draw conditional means, and
     ``samples_kind`` says which. ``conditional_means`` and
     ``conditional_vars`` (n_draws, n_test) are what interval construction
     needs; ``within_var_mean`` and ``between_var`` are the two terms whose
@@ -66,46 +67,50 @@ class ComponentResult:
             raise ValueError(
                 f"component {self.name!r} carries no per-draw conditional "
                 "moments; intervals need a decomposition produced by this "
                 "package version")
         return mixture_central_interval(self.conditional_means,
                                         self.conditional_vars, mass=mass)
 
 
 @dataclass
 class DecompositionResult:
     """Decomposition of one additive GP posterior.
 
     The seven fields below are a positional rebuild contract pinned by
     tests/test_poster_d58_driver.py; additional per-draw information is
     attached as non-field attributes in __post_init__ (``full``, ``groups``,
-    ``n_draws_attempted``, ``n_draws_retained``) so that contract holds.
+    ``n_draws_attempted``, ``n_draws_retained``, ``noise_var_draws``) so that
+    contract holds. ``noise_var`` is the mean observation-noise variance over
+    the retained draws and ``noise_var_draws`` the per-draw values, so
+    neither depends on draw order (fix pass 2a, SYNTHESIS A-10).
     """
     x_test: np.ndarray
     x_train: np.ndarray
     y_train: np.ndarray
     components: Dict[str, ComponentResult]
     full_mean: np.ndarray
     full_std: np.ndarray
     noise_var: float
 
     def __post_init__(self):
         # Non-field attributes (not part of dataclasses.fields()).
         self.full: Optional[ComponentResult] = None
         self.groups: Dict[Tuple[str, ...], ComponentResult] = {}
         self.n_draws_attempted: int = 0
         self.n_draws_retained: int = 0
+        self.noise_var_draws: Optional[np.ndarray] = None
 
     @staticmethod
     def group_key(names: Sequence[str]) -> Tuple[str, ...]:
         return tuple(sorted(set(names)))     # a repeated name is one member (review F3)
 
     def group(self, names: Sequence[str]) -> ComponentResult:
         """Joint posterior summary of the sum of the named components.
 
         Groups must be requested at decomposition time (``groups=`` on
         `decompose_model_hmc` / `decompose_model_mcmc`) because their
         conditional moments are computed per hyperparameter draw from the
         summed kernel blocks. A group of every component is the full
         posterior; a singleton is the component; an empty group is zero.
         """
         key = self.group_key(names)
@@ -251,40 +256,45 @@ class _DrawAccumulator:
             between_cov = np.atleast_2d(np.cov(M, rowvar=False, bias=True))
         else:
             between_cov = np.zeros((self.n_test, self.n_test))
         return _summarize(name, M, V, within_cov + between_cov, M, "conditional_means")
 
     def finalize(self):
         if self.n == 0:
             raise RuntimeError("no hyperparameter draw was decomposed")
         components = {n: self._finalize_target(("component", n), n) for n in self.names}
         full = self._finalize_target(("full",), "__full__")
         groups = {key: self._finalize_target(("group", key), "+".join(key))
                   for key in self.group_keys}
         return components, full, groups
 
 
-def _assemble(x_test, x_train, y_train, components, full, groups, noise_var,
+def _assemble(x_test, x_train, y_train, components, full, groups, noise_draws,
               n_attempted, n_retained) -> DecompositionResult:
+    """Package a draw-path decomposition. ``noise_draws`` holds the retained
+    draws' noise variances; ``noise_var`` is their mean (fix pass 2a,
+    SYNTHESIS A-10: it used to be the last retained draw's value)."""
+    noise_draws = np.asarray(noise_draws, dtype=float)
     result = DecompositionResult(
         x_test=x_test.numpy(), x_train=x_train.numpy(), y_train=y_train.numpy(),
         components=components, full_mean=full.mean, full_std=full.std,
-        noise_var=noise_var)
+        noise_var=float(noise_draws.mean()))
     result.full = full
     result.groups = groups
     result.n_draws_attempted = n_attempted
     result.n_draws_retained = n_retained
+    result.noise_var_draws = noise_draws
     return result
 
 
 # ── MAP decomposition ───────────────────────────────────────────────
 
 def decompose_model(model, likelihood, x_train, y_train, x_test, n_samples=25, jitter=1e-4,
                     groups=None):
     """
     Decompose a fitted additive GP into its components.
     Single set of hyperparameters (MAP). For full Bayesian, use decompose_model_hmc.
 
     groups: optional list of component-name lists. Each requested group's
     posterior is the posterior of the summed group kernel conditioned with
     the Cholesky factor of the ENTIRE training covariance (never a
     group-only factorization); retrieve it with ``result.group(names)``.
@@ -338,139 +348,153 @@ def decompose_model(model, likelihood, x_train, y_train, x_test, n_samples=25, j
         with torch.no_grad():
             mean_g_t, cov_g_t = decompose_component(
                 _blocks_sum(km, members, "XstarX"), _blocks_sum(km, members, "XstarXstar"),
                 _blocks_sum(km, members, "XXstar"), L_sum, y_train)
         cov_g = cov_g_t.numpy()
         group_results[key] = _single_draw_summary("+".join(key), mean_g_t.numpy(),
                                                   0.5 * (cov_g + cov_g.T))
 
     result = DecompositionResult(
         x_test=x_test.numpy(), x_train=x_train.numpy(), y_train=y_train.numpy(),
         components=components, full_mean=full_mean.numpy(), full_std=full.std, noise_var=noise_var,
     )
     result.full = full
     result.groups = group_results
     result.n_draws_attempted = result.n_draws_retained = 1
+    result.noise_var_draws = np.array([noise_var])
     return result
 
 
 # ── draw-based decompositions ───────────────────────────────────────
 
 def _raw_parameter_map(model, likelihood):
     """{name: parameter} over model + likelihood scalar parameters, deduplicated
     by object identity with the first name kept (the fit_mcmc_simple naming)."""
     seen = set()
     out = {}
     for n, p in list(model.named_parameters()) + list(likelihood.named_parameters()):
         if p.requires_grad and p.numel() == 1 and id(p) not in seen:
             seen.add(id(p))
             out[n] = p
     return out
 
 
 def decompose_model_mcmc(model, likelihood, x_train, y_train, x_test,
                          mcmc_samples, n_posterior_samples=100, jitter=1e-4,
                          groups=None, rng=None):
     """
     Full Bayesian decomposition over RAW-parameter draws (fit_mcmc_simple
     output: dict keyed by named_parameters names, raw unconstrained values).
 
     Draws are matched to parameters BY NAME (the previous positional pairing
     silently mis-assigned any differently ordered dict); every parameter must
     have a key and every key must name a parameter, or the call raises.
     Bands are law-of-total-variance moments (see the module docstring).
+
+    The draws are written into the caller's ``model`` and ``likelihood`` in
+    place, and the parameters keep the last decomposed draw's values on
+    return (SYNTHESIS A-18); refit or restore the model before reusing it.
     """
     model.eval()
     likelihood.eval()
     x_train, y_train, x_test = x_train.double(), y_train.double(), x_test.double()
     n_test = x_test.shape[0]
 
     param_map = _raw_parameter_map(model, likelihood)
     keys = list(mcmc_samples.keys())
     unknown = [k for k in keys if k not in param_map]
     missing = [n for n in param_map if n not in mcmc_samples]
     if unknown or missing:
         raise KeyError(
             "decompose_model_mcmc: sample keys and model parameters do not "
             f"match by name (unknown keys {unknown}, parameters without a key "
             f"{missing}); positional pairing is no longer performed")
 
-    total_mcmc = len(mcmc_samples[keys[0]])
+    total_mcmc = sample_draw_count(mcmc_samples, keys, "decompose_model_mcmc")
     n_take = min(n_posterior_samples, total_mcmc)
     if rng is not None:
         indices = rng.choice(total_mcmc, n_take, replace=False)
     else:
         indices = np.random.choice(total_mcmc, n_take, replace=False)
 
     names = list(model.component_names)
     acc = _DrawAccumulator(names, n_test, groups)
-    noise_var = float(likelihood.noise.item())
+    noise_draws = []
     for idx in indices:
         for name, p in param_map.items():
             p.data.fill_(float(mcmc_samples[name][idx]))
         noise_var = likelihood.noise.item()
         km = model.get_component_kernel_matrices(x_train, x_test)
         with torch.no_grad():
             acc.add_draw(km, noise_var, y_train, jitter)
+        noise_draws.append(noise_var)
 
     components, full, group_results = acc.finalize()
     return _assemble(x_test, x_train, y_train, components, full, group_results,
-                     noise_var, len(indices), acc.n)
+                     noise_draws, len(indices), acc.n)
 
 
 def decompose_model_hmc(model, likelihood, x_train, y_train, x_test,
                         mcmc_samples, kernel_builder, n_posterior_samples=200,
                         jitter=1e-4, groups=None, strict=True, rng=None):
     """
     Decomposition over Pyro/E1 hyperparameter draws (fit_hmc dict schema:
     constrained values keyed by pyro sample-site name).
 
     kernel_builder: callable that returns (kernel_components, names), e.g.
                     build_toy_kernels or build_mauna_loa_kernels.
     groups: optional list of component-name lists; each requested group's
             joint posterior (sum of the components) is computed per draw and
             available through DecompositionResult.group(names).
-    strict: True (default) raises on an unrecognized or failing sample site
-            and on a draw whose decomposition fails; False keeps the previous
-            skip-and-continue behavior and records the dropped draws.
+    strict: True (default) raises on an unrecognized or failing sample site,
+            on a sampled site of the model with no draws supplied, and on a
+            draw whose decomposition fails; False keeps the previous
+            skip-and-continue behavior and records the dropped draws. Sample
+            arrays of unequal length raise under either setting.
     """
     from .model import build_model, build_likelihood, select_hmc_sites, apply_hp_value
 
     x_train, y_train, x_test = x_train.double(), y_train.double(), x_test.double()
     n_test = x_test.shape[0]
 
-    first_key = list(mcmc_samples.keys())[0]
-    total_mcmc = len(mcmc_samples[first_key])
-    n_take = min(n_posterior_samples, total_mcmc)
-    if rng is not None:
-        indices = rng.choice(total_mcmc, n_take, replace=False)
-    else:
-        indices = np.random.choice(total_mcmc, n_take, replace=False)
-
     relevant_keys = select_hmc_sites(mcmc_samples.keys())
     kernel_keys = [k for k in relevant_keys if not k.endswith("noise_covar.noise_prior")]
     if not kernel_keys:
         msg = ("decompose_model_hmc: no kernel hyperparameter site recognized "
                f"among {sorted(mcmc_samples.keys())}")
         if strict:
             raise ValueError(msg)
         logger.warning(msg)
 
+    # Fix pass 2a, SYNTHESIS A-3: one draw count shared by every indexed
+    # array, and a draw for every site the model samples.
+    total_mcmc = sample_draw_count(mcmc_samples, relevant_keys or list(mcmc_samples),
+                                   "decompose_model_hmc")
+    probe_kernels, probe_names = kernel_builder()
+    probe_model, _ = build_model(x_train, y_train, probe_kernels, probe_names, build_likelihood())
+    _require_sample_sites(probe_model, relevant_keys, "decompose_model_hmc", strict)
+
+    n_take = min(n_posterior_samples, total_mcmc)
+    if rng is not None:
+        indices = rng.choice(total_mcmc, n_take, replace=False)
+    else:
+        indices = np.random.choice(total_mcmc, n_take, replace=False)
+
     names = list(model.component_names)
     acc = _DrawAccumulator(names, n_test, groups)
     dropped = []
-    last_noise = float(likelihood.noise.item())
+    noise_draws = []
 
     for idx in indices:
         kernels, fresh_names = kernel_builder()
         if list(fresh_names) != names:
             raise ValueError(
                 f"kernel_builder names {list(fresh_names)} differ from the "
                 f"model's component names {names}")
         fresh_likelihood = build_likelihood()
         fresh_model, fresh_likelihood = build_model(x_train, y_train, kernels, fresh_names, fresh_likelihood)
 
         for pyro_name in relevant_keys:
             val = float(mcmc_samples[pyro_name][idx])
             try:
                 applied = apply_hp_value(fresh_model, fresh_likelihood, pyro_name, val)
             except (IndexError, AttributeError, RuntimeError) as exc:
@@ -483,38 +507,38 @@ def decompose_model_hmc(model, likelihood, x_train, y_train, x_test,
             if not applied:
                 msg = (f"decompose_model_hmc: apply_hp_value did not recognize "
                        f"site {pyro_name!r} (draw {int(idx)})")
                 if strict:
                     raise ValueError(msg)
                 logger.warning(msg)
 
         fresh_model.eval()
         fresh_likelihood.eval()
         noise_var = fresh_likelihood.noise.item()
         km = fresh_model.get_component_kernel_matrices(x_train, x_test)
 
         with torch.no_grad():
             try:
                 acc.add_draw(km, noise_var, y_train, jitter)
-                last_noise = noise_var
+                noise_draws.append(noise_var)
             except RuntimeError as exc:
                 if strict:
                     raise RuntimeError(
                         f"decompose_model_hmc: decomposition failed for draw "
                         f"{int(idx)} ({exc}); pass strict=False to drop failing "
                         "draws and record them") from exc
                 dropped.append((int(idx), str(exc)))
                 continue
 
     if acc.n == 0:
         raise RuntimeError("All MCMC samples failed decomposition")
 
     print(f"  Decomposed {acc.n}/{len(indices)} MCMC samples successfully")
     if dropped:
         logger.warning("decompose_model_hmc dropped %d of %d draws: %s",
                        len(dropped), len(indices), [d for d, _ in dropped][:10])
 
     components, full, group_results = acc.finalize()
     result = _assemble(x_test, x_train, y_train, components, full, group_results,
-                       last_noise, len(indices), acc.n)
+                       noise_draws, len(indices), acc.n)
     result.dropped = dropped
     return result
diff --git a/bistar_gp/decompose.py b/bistar_gp/decompose.py
index 11852a9..f1c4c86 100644
--- a/bistar_gp/decompose.py
+++ b/bistar_gp/decompose.py
@@ -1,46 +1,53 @@
 """
 Additive kernel decomposition for Gaussian Processes.
 
 Implements Eq. 5 from Chandramouli & Shiffrin:
 Given a GP with sum kernel k_sum = k_1 + k_2 + ... + k_n,
 decompose posterior predictions into individual component GPs.
 
 Pure PyTorch — no GPyTorch dependency. This is the mathematical core.
 """
 
+import logging
+
 import numpy as np
 import torch
 from typing import List, Tuple, Optional
 
+logger = logging.getLogger(__name__)
+
 
 def compute_cholesky(
     K_sum_XX: torch.Tensor,
     noise_var: float,
     jitter: float = 1e-6,
 ) -> torch.Tensor:
     """
     Compute Cholesky factor of (K_sum(X,X) + sigma_y^2 I).
     Shared across all component decompositions.
-    Progressive jitter fallback on failure.
+    Progressive jitter fallback on failure; each escalation is logged with
+    its level (fix pass 2a, SYNTHESIS A-23) and the return value is unchanged.
     """
     n = K_sum_XX.shape[0]
     A = K_sum_XX + (noise_var + jitter) * torch.eye(n, dtype=K_sum_XX.dtype, device=K_sum_XX.device)
     try:
         return torch.linalg.cholesky(A)
     except RuntimeError:
         for extra in [1e-5, 1e-4, 1e-3, 1e-2]:
+            logger.warning("compute_cholesky: factorization of K + (noise + %g) I "
+                           "failed; retrying with extra jitter %g", jitter, extra)
             try:
                 return torch.linalg.cholesky(
                     A + extra * torch.eye(n, dtype=A.dtype, device=A.device)
                 )
             except RuntimeError:
                 continue
         raise RuntimeError("Cholesky failed even with large jitter. Check hyperparameters.")
 
 
 def decompose_component(
     K_i_XstarX: torch.Tensor,
     K_i_XstarXstar: torch.Tensor,
     K_i_XXstar: torch.Tensor,
     L: torch.Tensor,
     y: torch.Tensor,
diff --git a/bistar_gp/induced_prior.py b/bistar_gp/induced_prior.py
index 6836467..e2a908a 100644
--- a/bistar_gp/induced_prior.py
+++ b/bistar_gp/induced_prior.py
@@ -28,30 +28,31 @@ Expected qualitative behavior:
   - Informative GP prior → tight ψ → sharp induced prior near truth
   - Vague GP prior → wide ψ → diffuse induced prior, less informative
   - Misspecified GP prior → biased ψ → shifted induced prior, may mislead
 """
 
 import logging
 
 import numpy as np
 from typing import List, Dict, Optional, Tuple, Callable
 from dataclasses import dataclass
 
 logger = logging.getLogger(__name__)
 
 from bistar_gp.bms_star import GPPosteriorSample, METRICS
 from bistar_gp.candidates import CandidateResult
+from bistar_gp.errors import EvaluationFailure
 
 
 # ═══════════════════════════════════════════════════════════════════
 # Parameter Space Definitions
 # ═══════════════════════════════════════════════════════════════════
 
 @dataclass
 class ParameterSpec:
     """Specification for one model parameter."""
     name: str
     bounds: Tuple[float, float]    # sampling range
     true_value: Optional[float]     # ground truth (if known)
     mle_value: Optional[float] = None
 
 
@@ -145,74 +146,96 @@ def build_toy_parameter_spaces(true_params: Dict = None) -> Dict[str, ModelParam
             ParameterSpec("c", (-3.0, 3.0), true_value=None),
             ParameterSpec("sigma", (0.05, 3.0), true_value=None),
         ],
         predict_fn=lambda x, p: p["a"] * x**2 + p["b"] * x + p["c"],
     )
 
     return spaces
 
 
 # ═══════════════════════════════════════════════════════════════════
 # GP-Induced Prior Computation
 # ═══════════════════════════════════════════════════════════════════
 
 @dataclass
 class InducedPriorResult:
-    """Result of computing the GP-induced prior over model parameters."""
+    """Result of computing the GP-induced prior over model parameters.
+
+    ``weights`` is the normalized induced prior over ``param_samples``.
+    ``log_weights`` is on an internal scale (SYNTHESIS A-15): -G/tau shifted
+    by its maximum, plus log of the sum of the shifted weights; it is neither
+    the raw nor the normalized log weight (the normalized one is
+    ``np.log(weights)``), and failed points carry -inf.
+    """
     model_name: str
     prior_name: str          # which GP prior config
     param_names: List[str]
     param_samples: np.ndarray   # (n_samples, n_params) — reference prior draws
     log_weights: np.ndarray     # (n_samples,) — log induced prior weight per sample
     weights: np.ndarray         # (n_samples,) — normalized weights
-    G_per_sample: np.ndarray    # (n_samples,) — average G across GP samples
+    G_per_sample: np.ndarray    # (n_samples,) — average G across GP samples (NaN at a failed point)
     tau: float
     effective_sample_size: float
     mle_values: Optional[Dict[str, float]] = None
     true_values: Optional[Dict[str, float]] = None
+    # Non-strict evaluation records (fix pass 2a, SYNTHESIS A-2): parameter
+    # points with no valid divergence (zero weight), and single (point, draw)
+    # evaluations replaced by the strictly-worse penalty.
+    n_failed_points: int = 0
+    n_penalized_evaluations: int = 0
 
 
 def compute_induced_prior(
     param_space: ModelParameterSpace,
     gp_samples: List[GPPosteriorSample],
     x_eval: np.ndarray,
     log_mlls: Optional[np.ndarray] = None,
     metric_name: str = "pw_kl_vcal",
     tau: float = 1.0,
     n_param_samples: int = 10000,
     seed: int = 42,
     weighting: str = "uniform",
+    strict: bool = True,
 ) -> InducedPriorResult:
     """
     Compute the GP-induced prior over model parameters.
 
     For each parameter sample φ:
       1. Generate candidate prediction θ(φ) at x_eval
       2. Compute MLL-weighted average G across GP samples:
          Ḡ(φ) = Σ_i w_i G(ψ_i, θ(φ)) / Σ_i w_i
       3. Induced prior weight: exp(-Ḡ(φ) / τ)
 
     weighting (2026-09 review FIX-6):
       "uniform" (default): w_i = 1/N. This is the correct average for
           POSTERIOR draws (fit_hmc output); the draws already carry the
           likelihood, and multiplying by p(y|η_i) again would average under a
           density proportional to p(η) p(y|η)^2.
       "likelihood_tilted": w_i ∝ exp(log_mlls[i]); the self-normalized
           importance weights that turn PRIOR draws into a posterior average.
           Requires log_mlls. Never use with posterior draws.
     The pre-fix code made the likelihood weighting mandatory and its legacy
     callers fed it posterior draws.
+
+    strict (fix pass 2a, SYNTHESIS A-2): a parameter point FAILS when its
+    predict_fn raises or when no GP draw yields a finite divergence there.
+    True (default) raises EvaluationFailure naming the point. False gives the
+    point log weight -inf (zero mass, G_per_sample NaN) and counts it in
+    n_failed_points; the ESS is then over the valid points only. Every point
+    failing raises under either setting. A point where only some draws fail
+    keeps the strictly-worse penalty for those draws, counted in
+    n_penalized_evaluations and logged.
     """
     metric_fn = METRICS[metric_name]
     n_draws = len(gp_samples)
 
     if weighting == "uniform":
         if log_mlls is not None:
             # A legacy positional call would otherwise run a different
             # estimator with only a log line to say so (review F2).
             raise ValueError(
                 "compute_induced_prior: log_mlls supplied under weighting='uniform'; "
                 "pass weighting='likelihood_tilted' for PRIOR draws or drop log_mlls "
                 "for posterior draws")
         mll_weights = np.full(n_draws, 1.0 / n_draws)
     elif weighting == "likelihood_tilted":
         if log_mlls is None:
@@ -223,117 +246,147 @@ def compute_induced_prior(
             raise ValueError("compute_induced_prior: no finite log marginal likelihood")
         lw = log_mlls.copy()
         lw[~valid] = -np.inf
         lw -= lw[valid].max()
         mll_weights = np.exp(lw)
         mll_weights /= mll_weights.sum()
     else:
         raise ValueError(f"unknown weighting {weighting!r}; use 'uniform' or "
                          "'likelihood_tilted'")
 
     # Sample parameters from reference prior
     param_samples = param_space.sample_reference_prior(n_param_samples, seed=seed)
 
     # For each parameter sample, compute MLL-weighted G
     G_per_sample = np.zeros(n_param_samples)
+    failed_points = np.zeros(n_param_samples, dtype=bool)
+    n_penalized = 0
 
     for s_idx in range(n_param_samples):
         # Build parameter dict
         param_dict = {ps.name: param_samples[s_idx, j]
                       for j, ps in enumerate(param_space.param_specs)}
 
         # Generate prediction
         try:
             mu_theta = param_space.predict_fn(x_eval, param_dict)
-        except Exception:
-            G_per_sample[s_idx] = np.inf
+        except Exception as exc:
+            if strict:
+                raise EvaluationFailure(
+                    f"compute_induced_prior: predict_fn of {param_space.model_name!r} "
+                    f"raised {type(exc).__name__} at {param_dict}: {exc}") from exc
+            failed_points[s_idx] = True
+            G_per_sample[s_idx] = np.nan
             continue
 
         sigma = param_dict.get(param_space.noise_param, 0.3)
         sigma2 = sigma ** 2
         n_eval = len(x_eval)
         cov_theta = sigma2 * np.eye(n_eval)
 
         # MLL-weighted average G across GP samples
         g_vals = np.zeros(len(gp_samples))
         for i, psi in enumerate(gp_samples):
             try:
                 g_vals[i] = metric_fn(psi.mean, psi.cov, mu_theta, cov_theta)
             except (np.linalg.LinAlgError, ValueError):
                 g_vals[i] = np.inf
 
         # Replace a failed draw with a value strictly WORSE than every finite
         # one. The old `10 * max(finite)` is the smallest value (the best
         # score) whenever the metric is negative-valued (pw_nll_gp), the bug
         # class compute_G_matrix already documents (2026-09 review FIX-5).
         finite_mask = np.isfinite(g_vals)
-        if finite_mask.any():
+        if not finite_mask.any():
+            # The former G = 1e6 sentinel could outrank valid points whose G
+            # exceeds it (SYNTHESIS A-2); a point with no valid evaluation
+            # carries no mass.
+            if strict:
+                raise EvaluationFailure(
+                    f"compute_induced_prior: every divergence evaluation failed "
+                    f"for {param_space.model_name!r} at {param_dict}")
+            failed_points[s_idx] = True
+            G_per_sample[s_idx] = np.nan
+            continue
+        if not finite_mask.all():
             max_finite = np.max(g_vals[finite_mask])
             g_vals[~finite_mask] = max_finite + 10.0 * (abs(max_finite) + 1.0)
-        else:
-            g_vals[:] = 1e6
+            n_penalized += int((~finite_mask).sum())
 
         G_per_sample[s_idx] = np.sum(mll_weights * g_vals)
 
+    n_failed = int(failed_points.sum())
+    if n_failed == n_param_samples:
+        raise EvaluationFailure(
+            f"compute_induced_prior: every one of the {n_param_samples} parameter "
+            f"points of {param_space.model_name!r} failed; no induced prior exists")
+    if n_failed or n_penalized:
+        logger.warning(
+            "compute_induced_prior(%s): %d of %d parameter points failed (zero "
+            "weight); %d single evaluations scored with the worse-than-finite "
+            "penalty", param_space.model_name, n_failed, n_param_samples, n_penalized)
+
     # Compute induced prior weights
     log_weights = -G_per_sample / tau
+    log_weights[failed_points] = -np.inf
 
     # Numerical stability
     finite = np.isfinite(log_weights)
-    if finite.any():
-        log_weights[~finite] = -np.inf
-        log_weights -= np.max(log_weights[finite])
-    else:
-        log_weights[:] = 0.0
+    if not finite.any():
+        raise EvaluationFailure(
+            f"compute_induced_prior: no parameter point of {param_space.model_name!r} "
+            "carries a finite log weight; refusing to substitute uniform weights")
+    log_weights[~finite] = -np.inf
+    log_weights -= np.max(log_weights[finite])
 
     weights = np.exp(log_weights)
     total = weights.sum()
-    if total > 0:
-        weights /= total
-    else:
-        weights[:] = 1.0 / n_param_samples
+    weights /= total
 
-    # Effective sample size
-    ess = 1.0 / np.sum(weights ** 2) if np.sum(weights ** 2) > 0 else 0
+    # Effective sample size; failed points carry zero weight and drop out
+    ess = 1.0 / np.sum(weights ** 2)
 
     # Collect true and MLE values
     true_vals = {ps.name: ps.true_value for ps in param_space.param_specs
                  if ps.true_value is not None}
     mle_vals = {ps.name: ps.mle_value for ps in param_space.param_specs
                 if ps.mle_value is not None}
 
     # Weighted statistics
     print(f"\n  [{param_space.model_name}] Induced prior (τ={tau}, metric={metric_name}):")
-    print(f"    ESS: {ess:.0f} / {n_param_samples}")
+    print(f"    ESS: {ess:.0f} / {n_param_samples - n_failed}"
+          + (f" valid points ({n_failed} failed)" if n_failed else ""))
     for j, ps in enumerate(param_space.param_specs):
         w_mean = np.sum(weights * param_samples[:, j])
         w_std = np.sqrt(np.sum(weights * (param_samples[:, j] - w_mean)**2))
         true_str = f"  true={ps.true_value}" if ps.true_value is not None else ""
         print(f"    {ps.name:<8}: mean={w_mean:.4f} ± {w_std:.4f}{true_str}")
 
     return InducedPriorResult(
         model_name=param_space.model_name,
         prior_name="",  # set by caller
         param_names=[ps.name for ps in param_space.param_specs],
         param_samples=param_samples,
         log_weights=log_weights + np.log(total) if total > 0 else log_weights,
         weights=weights,
         G_per_sample=G_per_sample,
         tau=tau,
         effective_sample_size=ess,
         mle_values=mle_vals if mle_vals else None,
         true_values=true_vals if true_vals else None,
+        n_failed_points=n_failed,
+        n_penalized_evaluations=n_penalized,
     )
 
 
 def compute_model_evidence_induced(
     induced_prior: InducedPriorResult,
     x_train: np.ndarray,
     y_train: np.ndarray,
     param_space: ModelParameterSpace,
 ) -> float:
     """
     Compute marginal likelihood under the GP-induced prior:
 
       p(y | M_j, ψ) = ∫ p(y | φ, M_j) p(φ | ψ) dφ
                      ≈ Σ_s w_s · p(y | φ_s, M_j)
 
diff --git a/bistar_gp/laplace_evidence.py b/bistar_gp/laplace_evidence.py
index de67fcf..832e96a 100644
--- a/bistar_gp/laplace_evidence.py
+++ b/bistar_gp/laplace_evidence.py
@@ -35,30 +35,31 @@ This is what makes BI* different from BIC/AIC:
   Term (2) transfers qualitative GP beliefs into model comparison.
   Informative GP → small Ḡ for correct model → correct model wins.
   Vague GP → similar Ḡ for all models → reverts to standard BIC-like behavior.
 """
 
 import logging
 
 import numpy as np
 from typing import Dict, List, Optional, Tuple
 from scipy.optimize import minimize
 from scipy.special import softmax, logsumexp
 from scipy.linalg import solve_triangular
 from dataclasses import dataclass, field
 
 from bistar_gp.bms_star import GPPosteriorSample, METRICS, log_weight_ess
+from bistar_gp.errors import EvaluationFailure  # noqa: F401  re-exported; defined in errors (fix pass 2a, SYNTHESIS A-2)
 from bistar_gp.induced_prior import ModelParameterSpace
 import bistar_gp.metrics_v2  # noqa: F401 — registers pw_* metrics (incl. the default pw_kl_vcal) into METRICS
 
 logger = logging.getLogger(__name__)
 
 # Candidate noise sigma used when noise_param is absent from the param specs —
 # a documented contract (tests build sigma-free spaces so integrals run over
 # means only), previously copy-pasted as a magic 0.3 across five sites.
 DEFAULT_FIXED_SIGMA = 0.3
 # Objective value returned for invalid (sigma <= 0) points; large enough that
 # L-BFGS-B never accepts them, finite so finite differences stay defined.
 _GUARD_PENALTY = 1e10
 
 
 def _noise_sigma(param_space, param_dict) -> float:
@@ -180,37 +181,30 @@ class ZMxResult:
     model_name: str
     log_Z: float                 # log Z_Mx, Occam-adjusted
     G_at_min: float              # Ḡ(φ_G*)
     phi_min: Dict[str, float]
     occam: bool
     log_volume: float            # log V_ref
     logdet_H: float
     n_params: int
     tau: float
     converged: bool
     n_clipped: int = 0           # Hessian eigenvalues clipped: >0 means |H| was regularized
     optimizer: Optional[Dict[str, object]] = None   # best start's OptimizerRecord (FIX-5)
     n_starts_failed: int = 0     # starts whose minimize raised or reported failure
 
 
-class EvaluationFailure(RuntimeError):
-    """A candidate predictor or divergence metric failed under strict
-    evaluation (fix pass 1b). Subclass of RuntimeError for compatibility with
-    callers that catch the pass-1 exception; the optimizer fallback handlers
-    re-raise it so it can never turn into a start-point expansion."""
-
-
 @dataclass
 class OptimizerRecord:
     """What scipy's minimize actually reported for one start (2026-09 FIX-5).
 
     Before this record existed, an optimizer that raised fell back to the
     start point with converged=False, and a non-successful result was
     accepted silently; nothing carried either fact to the caller.
     """
     success: bool
     status: Optional[int] = None
     message: str = ""
     nit: Optional[int] = None
     nfev: Optional[int] = None
     exception: Optional[str] = None
 
@@ -643,31 +637,40 @@ def is_log_Z_Mx(param_space, x_eval, avg_gp, taus, *, n_is=100_000, seed=0,
     ladder — the REFERENCE estimator for figure Z_Mx values (plan §1.2).
 
     NOT self-normalized IS: Z_Mx is itself the normalizer, so the proposal
     density q is evaluated exactly and
 
         log I_raw = logmeanexp_i( −Ḡ(φ_i)/τ − log q(φ_i) ),  φ_i ~ q
 
     estimates the RAW Lebesgue integral ∫_box exp(−Ḡ/τ) dφ. occam=False
     returns log I_raw; occam=True returns log I_raw − log V (Laplace-path
     convention). Ḡ and log q are computed once; every τ is a reweighting.
 
     starts: multi-start dicts anchoring the proposal's Gaussian components
     (covariances τ_k·H⁻¹ over tau_ladder); pass the same starts you would
     give laplace_log_Z_Mx. The uniform half of the mixture defends against
     optima the starts missed. Warns when any per-τ ESS < ess_warn.
+
+    tau_ladder must be non-empty, finite and positive (fix pass 2a, SYNTHESIS
+    A-4): with no Gaussian components every draw came from the uniform box
+    while log q still gave the box half the mass, doubling the integral.
     """
+    tau_ladder = tuple(tau_ladder)
+    ladder = np.asarray(tau_ladder, dtype=float)
+    if ladder.size == 0 or not np.all(np.isfinite(ladder)) or np.any(ladder <= 0):
+        raise ValueError(f"is_log_Z_Mx: tau_ladder must be a non-empty sequence of "
+                         f"finite positive values; got {tau_ladder}")
     metric_fn = METRICS[metric_name]
     lo, hi = _box(param_space)
     optima = _multistart_G_optima(param_space, x_eval, avg_gp, metric_fn, starts,
                                   strict=strict)
     records = [rec.as_dict() for *_, rec in optima]
     n_failed = sum(1 for *_, rec in optima if not rec.success)
     # Component covariances tau_k * H^-1, inverted in EIGEN space (never
     # reconstruct-then-inv, codex P2) with per-direction variances capped at
     # the box scale: a floored-flat Hessian direction would otherwise give a
     # ~1e8-variance Gaussian that throws nearly all its samples out of the
     # box. The uniform mixture half keeps the estimator correct either way;
     # the cap keeps it efficient.
     var_cap = float(np.max(0.5 * (hi - lo)) ** 2)
     centers, covs = [], []
     for x_star, _, eigval, eigvec, _rec in optima:
@@ -1015,91 +1018,142 @@ def plot_model_posteriors_by_prior(
                color=colors[m_idx % len(colors)])
 
     ax.set_xticks(x)
     ax.set_xticklabels(prior_names, fontsize=10)
     ax.set_ylabel("Model Posterior p(M|D,ψ)", fontsize=11)
     ax.set_title("BI* Model Selection: How GP Prior Shapes Model Ranking\n"
                  "(Construction II, Laplace)", fontsize=13)
     ax.set_ylim(0, 1)
     ax.axhline(1.0 / n_models, color='gray', linestyle=':', alpha=0.5, label='uniform')
     ax.legend(fontsize=9)
     ax.grid(True, alpha=0.2, axis='y')
     fig.tight_layout()
     return fig
 
 
+class TauSweepPosteriors(tuple):
+    """``(model_names, posteriors)`` exactly as before, carrying the Laplace
+    records the sweep used to drop (fix pass 2a, SYNTHESIS A-23): arrays
+    ``converged``, ``n_clipped``, ``n_starts_failed`` of shape
+    (n_taus, n_models), and ``all_converged``."""
+
+    def __new__(cls, names, posteriors, converged, n_clipped, n_starts_failed):
+        obj = super().__new__(cls, (names, posteriors))
+        obj.converged = np.asarray(converged, dtype=bool)
+        obj.n_clipped = np.asarray(n_clipped, dtype=int)
+        obj.n_starts_failed = np.asarray(n_starts_failed, dtype=int)
+        obj.all_converged = bool(obj.converged.all())
+        return obj
+
+    def __getnewargs__(self):            # pickling and copy.deepcopy
+        return (self[0], self[1], self.converged, self.n_clipped, self.n_starts_failed)
+
+
+class LadderPosteriors(dict):
+    """``{construction: {model_name: posterior}}`` exactly as before, carrying
+    the per-construction, per-model ``converged``, ``n_clipped`` and
+    ``n_starts_failed`` records, and ``all_converged`` (fix pass 2a, SYNTHESIS
+    A-23). Compares equal to the plain dict of posteriors."""
+
+    def __init__(self, posteriors, converged, n_clipped, n_starts_failed):
+        super().__init__(posteriors)
+        self.converged = converged
+        self.n_clipped = n_clipped
+        self.n_starts_failed = n_starts_failed
+        self.all_converged = all(v for per in converged.values() for v in per.values())
+
+
 def model_posterior_tau_sweep(
     param_spaces: Dict[str, ModelParameterSpace],
     x_train: np.ndarray,
     y_train: np.ndarray,
     x_eval: np.ndarray,
     avg_gp: GPPosteriorSample,
     mle_params: Dict[str, Dict[str, float]],
     taus,
     *,
     construction: str = "II",
     metric_name: str = "pw_kl_vcal",
     occam: bool = False,
     strict: bool = True,
 ) -> Tuple[List[str], np.ndarray]:
     """Model posteriors across τ values, exploiting per-construction structure
     instead of re-running the full Laplace machinery at every τ:
 
       baseline — τ-independent: one computation, replicated.
       I        — p_ord is τ-independent (once per model) and Z_Mx rescales
                  ANALYTICALLY from a single τ=1 pass (the same identity
                  laplace_log_Z_Mx uses internally):
                      log Z(τ) = log Z(1) + Ḡ*·(1 − 1/τ) + (d/2)·log τ
       II       — the joint MAP of log p(y|φ) − Ḡ(φ)/τ genuinely moves with τ,
                  so it is honestly recomputed per τ (no shortcut exists).
 
-    Returns (model_names, posteriors[t_idx, m_idx]).
+    Returns (model_names, posteriors[t_idx, m_idx]) as a TauSweepPosteriors,
+    which also carries the per-(τ, model) converged / n_clipped /
+    n_starts_failed records (τ-independent constructions repeat theirs).
     """
     names = list(param_spaces.keys())
     taus = np.asarray(list(taus), dtype=float)
     logk = np.zeros((len(taus), len(names)))
+    converged = np.ones((len(taus), len(names)), dtype=bool)
+    n_clipped = np.zeros((len(taus), len(names)), dtype=int)
+    n_starts_failed = np.zeros((len(taus), len(names)), dtype=int)
+
+    def _record(t_slice, j, comp):
+        converged[t_slice, j] = bool(comp["converged"])
+        n_clipped[t_slice, j] = int(comp["n_clipped"])
+        n_starts_failed[t_slice, j] = int(comp["n_starts_failed"])
 
     if construction == "baseline":
         mpr = model_posterior(param_spaces, x_train, y_train, x_eval, avg_gp,
                               mle_params, construction="baseline",
                               metric_name=metric_name, tau=1.0, occam=occam,
                               strict=strict)
         logk[:] = [mpr.log_kernel[n] for n in names]
+        for j, n in enumerate(names):
+            _record(slice(None), j, mpr.components[n])
     elif construction == "I":
         for j, name in enumerate(names):
             ps = param_spaces[name]
             mp = mle_params.get(name) if mle_params else None
             ev = laplace_log_evidence_ordinary(ps, x_train, y_train,
                                                mle_params=mp, occam=occam,
                                                strict=strict)
             z1 = laplace_log_Z_Mx(ps, x_eval, avg_gp, metric_name=metric_name,
                                   tau=1.0, occam=occam, mle_params=mp,
                                   strict=strict)
             log_Z_tau = (z1.log_Z + z1.G_at_min * (1.0 - 1.0 / taus)
                          + 0.5 * ps.n_params * np.log(taus))
             logk[:, j] = log_Z_tau + ev.log_evidence
+            _record(slice(None), j, {
+                "converged": z1.converged and ev.converged,
+                "n_clipped": z1.n_clipped + ev.n_clipped,
+                "n_starts_failed": z1.n_starts_failed + ev.n_starts_failed})
     elif construction == "II":
         for t_idx, tau in enumerate(taus):
             mpr = model_posterior(param_spaces, x_train, y_train, x_eval,
                                   avg_gp, mle_params, construction="II",
                                   metric_name=metric_name, tau=float(tau),
                                   occam=occam, strict=strict)
             logk[t_idx] = [mpr.log_kernel[n] for n in names]
+            for j, n in enumerate(names):
+                _record(t_idx, j, mpr.components[n])
     else:
         raise ValueError(f"unknown construction {construction!r}")
 
-    return names, softmax(logk, axis=1)
+    return TauSweepPosteriors(names, softmax(logk, axis=1),
+                              converged, n_clipped, n_starts_failed)
 
 
 def plot_tau_effect_on_evidence(
     param_spaces: Dict[str, ModelParameterSpace],
     x_train: np.ndarray,
     y_train: np.ndarray,
     x_eval: np.ndarray,
     avg_gp: GPPosteriorSample,
     mle_params: Dict[str, Dict[str, float]],
     metric_name: str = "pw_kl_vcal",
     taus: np.ndarray = None,
     prior_name: str = "",
     construction: str = "II",
     occam: bool = False,
     figsize: tuple = (10, 5),
@@ -1149,66 +1203,83 @@ def ablation_ladder_posteriors(
     avg_gp: GPPosteriorSample,
     mle_params: Dict[str, Dict[str, float]],
     *,
     metric_name: str = "pw_kl_vcal",
     tau: float = 1.0,
     occam: bool = False,
     precomputed_II: Optional[ModelPosteriorResult] = None,
 ) -> Dict[str, Dict[str, float]]:
     """Posteriors for all three constructions, computing each Laplace
     primitive ONCE per model: p_ord serves both the baseline and Construction
     I (three separate model_posterior calls used to compute it twice), Z_Mx
     serves I, and N(M) serves II. Pass an existing construction="II"
     ModelPosteriorResult (same metric/τ/occam — enforced) to skip the N(M)
     optimizations too.
 
-    Returns {construction: {model_name: posterior}}.
+    Returns {construction: {model_name: posterior}} as a LadderPosteriors,
+    which also carries each construction's per-model converged / n_clipped /
+    n_starts_failed records.
     """
     metric_fn = METRICS[metric_name]
     names = list(param_spaces.keys())
 
     if precomputed_II is not None:
         mismatch = (precomputed_II.construction != "II"
                     or precomputed_II.tau != tau
                     or precomputed_II.occam != occam
                     or precomputed_II.metric_name != metric_name
                     or list(precomputed_II.model_names) != names)
         if mismatch:
             raise ValueError(
                 "precomputed_II must be a construction='II' result with the "
                 "same tau/occam/metric_name/model set as this ladder call")
 
-    logk = {c: [] for c in ("baseline", "I", "II")}
+    constructions = ("baseline", "I", "II")
+    logk = {c: [] for c in constructions}
+    records = {key: {c: {} for c in constructions}
+               for key in ("converged", "n_clipped", "n_starts_failed")}
     for name in names:
         ps = param_spaces[name]
         mp = mle_params.get(name) if mle_params else None
         ev = laplace_log_evidence_ordinary(ps, x_train, y_train, mle_params=mp,
                                            occam=occam)
         zmx = laplace_log_Z_Mx(ps, x_eval, avg_gp, metric_name=metric_name,
                                tau=tau, occam=occam, mle_params=mp)
         if precomputed_II is not None:
             log_N = precomputed_II.log_kernel[name]
+            detail = precomputed_II.components[name]
         else:
-            log_N, _, _, _ = _laplace_log_N(ps, x_train, y_train, x_eval,
-                                            avg_gp, metric_fn, tau, mp,
-                                            occam=occam)
+            log_N, _, _, detail = _laplace_log_N(ps, x_train, y_train, x_eval,
+                                                 avg_gp, metric_fn, tau, mp,
+                                                 occam=occam)
         logk["baseline"].append(ev.log_evidence)
         logk["I"].append(zmx.log_Z + ev.log_evidence)
         logk["II"].append(log_N)
-
-    return {c: {n: float(p) for n, p in zip(names, softmax(np.array(arr)))}
-            for c, arr in logk.items()}
+        per_construction = {
+            "baseline": (ev.converged, ev.n_clipped, ev.n_starts_failed),
+            "I": (zmx.converged and ev.converged, zmx.n_clipped + ev.n_clipped,
+                  zmx.n_starts_failed + ev.n_starts_failed),
+            "II": (detail["converged"], detail["n_clipped"], detail["n_starts_failed"]),
+        }
+        for c, (conv, clip, failed) in per_construction.items():
+            records["converged"][c][name] = bool(conv)
+            records["n_clipped"][c][name] = int(clip)
+            records["n_starts_failed"][c][name] = int(failed)
+
+    posteriors = {c: {n: float(p) for n, p in zip(names, softmax(np.array(arr)))}
+                  for c, arr in logk.items()}
+    return LadderPosteriors(posteriors, **records)
 
 
 def plot_ablation_ladder(
     param_spaces: Dict[str, ModelParameterSpace],
     x_train: np.ndarray,
     y_train: np.ndarray,
     x_eval: np.ndarray,
     avg_gp: GPPosteriorSample,
     mle_params: Dict[str, Dict[str, float]],
     metric_name: str = "pw_kl_vcal",
     tau: float = 1.0,
     occam: bool = False,
     prior_name: str = "",
     figsize: tuple = None,
     precomputed_II: Optional[ModelPosteriorResult] = None,
diff --git a/bistar_gp/viz.py b/bistar_gp/viz.py
index 7e5b6ce..13bb184 100644
--- a/bistar_gp/viz.py
+++ b/bistar_gp/viz.py
@@ -1,66 +1,102 @@
 """
 Visualization for GP decomposition — reproduces thesis figure styles.
 """
 
 import numpy as np
 import matplotlib.pyplot as plt
 from matplotlib.gridspec import GridSpec
 from typing import Optional, Dict
 
 plt.rcParams.update({"font.size": 12, "axes.labelsize": 14, "figure.dpi": 150, "lines.linewidth": 1.5})
 
 COLORS = {"data": "black", "true": "red", "mean": "orange", "band": "lightgreen", "samples": "steelblue", "bias": "green"}
 
+TRACE_LABELS = {"function_draws": "function draws",
+                "conditional_means": "per-draw conditional means"}
 
-def plot_full_prediction(result, true_func=None, title="GP Prediction", n_samples=15, ax=None):
-    """Full GP prediction — thesis Fig 10a style."""
+
+def _band(summary, mean, std, mass=0.95):
+    """(lower, upper, label) for a posterior band (fix pass 2a, SYNTHESIS A-5).
+
+    A summary carrying per-draw conditional moments gets the mixture's own
+    central interval; mean +/- 2 sd of a hyperparameter mixture is not a 95%
+    interval, so without those moments the band is labelled as what it is.
+    """
+    if getattr(summary, "conditional_means", None) is not None \
+            and getattr(summary, "conditional_vars", None) is not None:
+        lo, hi = summary.central_interval(mass)
+        return lo, hi, f"{mass:.0%} central interval"
+    return mean - 2 * std, mean + 2 * std, "mean ± 2 sd"
+
+
+def _plot_traces(ax, x, traces, kind, n_samples):
+    for i, trace in enumerate(traces[:n_samples]):
+        ax.plot(x, trace, color=COLORS["samples"], alpha=0.15, linewidth=0.8,
+                label=TRACE_LABELS.get(kind, kind) if i == 0 else None)
+
+
+def plot_full_prediction(result, true_func=None, title="GP Prediction", n_samples=15, ax=None,
+                         seed=0):
+    """Full GP prediction — thesis Fig 10a style.
+
+    The traces are never a sum of separately drawn component samples, which
+    drops the cross-component posterior covariance (SYNTHESIS A-5): on
+    hyperparameter-draw paths they are the per-draw conditional means of the
+    summed function, and on the MAP path joint draws from the full posterior
+    N(mean, cov) with a fixed `seed`. A result rebuilt without its full
+    posterior gets the band and the mean only.
+    """
     if ax is None:
         _, ax = plt.subplots(figsize=(10, 6))
 
     x = result.x_test
+    full = getattr(result, "full", None)
 
-    # Confidence band
-    ax.fill_between(x, result.full_mean - 2*result.full_std, result.full_mean + 2*result.full_std,
-                     alpha=0.2, color=COLORS["band"], label="95% CI")
+    lo, hi, band_label = _band(full, result.full_mean, result.full_std)
+    ax.fill_between(x, lo, hi, alpha=0.2, color=COLORS["band"], label=band_label)
 
-    # Function samples
-    min_samps = min(c.samples.shape[0] for c in result.components.values())
-    for i in range(min(n_samples, min_samps)):
-        combined = sum(c.samples[i] for c in result.components.values())
-        ax.plot(x, combined, color=COLORS["samples"], alpha=0.15, linewidth=0.8)
+    if full is not None and full.samples_kind == "conditional_means" and full.n_draws > 1:
+        _plot_traces(ax, x, full.conditional_means, "conditional_means", n_samples)
+    elif full is not None and full.n_draws == 1:
+        cov = 0.5 * (full.cov + full.cov.T) + 1e-10 * np.eye(len(x))
+        draws = np.random.default_rng(seed).multivariate_normal(full.mean, cov, size=n_samples,
+                                                                method="cholesky")
+        _plot_traces(ax, x, draws, "function_draws", n_samples)
 
     ax.plot(x, result.full_mean, color=COLORS["mean"], linewidth=2.5, label="Predicted mean")
     if true_func is not None:
         ax.plot(x, true_func, color=COLORS["true"], linewidth=2, linestyle="--", label="True function")
     ax.scatter(result.x_train, result.y_train, color=COLORS["data"], marker="x", s=40, zorder=5, label="Data")
     ax.set_xlabel("$x$"); ax.set_ylabel("$y$"); ax.set_title(title); ax.legend(fontsize=10)
     return ax
 
 
 def plot_component(result, component_name, true_func=None, color="orange",
                    title=None, n_samples=15, show_data=True, ax=None):
     """Single decomposed component — thesis Fig 11a/11b style."""
     if ax is None:
         _, ax = plt.subplots(figsize=(10, 5))
 
     comp = result.components[component_name]
     x = result.x_test
 
-    ax.fill_between(x, comp.mean - 2*comp.std, comp.mean + 2*comp.std, alpha=0.2, color=color, label="±2 SE")
-    for i in range(min(n_samples, comp.samples.shape[0])):
-        ax.plot(x, comp.samples[i], color=COLORS["samples"], alpha=0.12, linewidth=0.8)
+    # band and trace labels from what the summary holds (SYNTHESIS A-5): the
+    # band is posterior spread, not a standard error
+    lo, hi, band_label = _band(comp, comp.mean, comp.std)
+    ax.fill_between(x, lo, hi, alpha=0.2, color=color, label=band_label)
+    _plot_traces(ax, x, comp.samples, comp.samples_kind, n_samples)
     ax.plot(x, comp.mean, color=color, linewidth=2.5, label=f"{component_name} mean")
     if true_func is not None:
         ax.plot(x, true_func, color=COLORS["true"], linewidth=2, linestyle="--", label="True")
     if show_data:
         ax.scatter(result.x_train, result.y_train, color=COLORS["data"], marker="x", s=30, alpha=0.4, zorder=5)
     ax.set_xlabel("$x$"); ax.set_ylabel("$y$"); ax.set_title(title or component_name); ax.legend(fontsize=10)
     return ax
 
 
 def plot_decomposition(result, true_components=None, true_combined=None,
                        figsize=None, suptitle="Additive GP Decomposition"):
     """Full decomposition: combined + all components (generalizes Fig 11)."""
     n = len(result.components)
     if figsize is None:
         figsize = (12, 4 * (1 + n))
diff --git a/experiments/fit_method_metric_comparison.py b/experiments/fit_method_metric_comparison.py
index 0e068c2..004d94c 100644
--- a/experiments/fit_method_metric_comparison.py
+++ b/experiments/fit_method_metric_comparison.py
@@ -23,30 +23,31 @@ Usage:
     python experiments/fit_method_metric_comparison.py --methods hmc vi
 """
 
 import sys, os, json, time, argparse
 
 sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
 
 import numpy as np
 import torch
 
 from bistar_gp import generate_toy_data, build_model
 from bistar_gp.fit import fit_map, fit_gp, GP_INFERENCE_METHODS
 from bistar_gp.candidates import build_toy_candidates
 from bistar_gp.config import (
     PRIOR_CONFIGS, build_kernels_from_config, build_likelihood_from_config,
+    load_hmc_samples,
 )
 from bistar_gp.bms_star import extract_gp_predictives, run_bms_star
 import bistar_gp.metrics_v2  # noqa: F401 — registers pw_kl_vcal etc. into METRICS
 
 torch.set_default_dtype(torch.float64)
 
 REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
 RUN_DIR = os.path.join(REPO_ROOT, "runs", "fit_method_metric_comparison")
 # Canonical outputs (full runs only; --quick writes *_quick files under runs/
 # so a smoke test can never masquerade as the real comparison).
 DOC_PATH = os.path.join(REPO_ROOT, "docs", "fit-method-metric-comparison.md")
 JSON_PATH = os.path.join(RUN_DIR, "results.json")
 
 SEED = 42
 PRIOR_NAME = "informative"          # the repo's default GP hyperprior config
@@ -106,46 +107,48 @@ def method_budgets(quick: bool, max_tree_depth=None) -> dict:
         budgets = {
             "hmc": dict(n_samples=2000, n_warmup=1000, verbose=False, seed=SEED),
             "vi": dict(n_samples=2000, n_steps=5000, verbose=False, seed=SEED),
             "map": dict(n_iter=500),
             "hmc_laplace": dict(n_samples=2000, n_warmup=1000, verbose=False,
                                 seed=SEED),
         }
     if max_tree_depth is not None:
         for m in ("hmc", "hmc_laplace"):
             budgets[m]["max_tree_depth"] = max_tree_depth
     return budgets
 
 
 def run_one_method(method, kwargs, prior_config, x_train, y_train, x_eval,
                    candidate_results, n_posterior_samples,
-                   cache_path=None, force_refit=False):
+                   cache_path=None, force_refit=False, allow_withdrawn=False):
     """MAP-fit a fresh model, run fit_gp(method), extract predictives, BMS*.
 
     cache_path: if set, raw fit_gp draws are loaded from / saved to this .npz —
     the sampler cost (hours for the NUTS methods) is decoupled from the cheap
     candidate/metric/tau side, which can then be recomputed freely.
+    allow_withdrawn: the cache is read through config.load_hmc_samples, which
+    refuses the caches the M2bR record withdrew (fix pass 2a, SYNTHESIS
+    A-11); True admits them, with a warning, for labelled archival
+    reproduction only.
     """
     kernels, names = build_kernels_from_config(prior_config)
     likelihood = build_likelihood_from_config(prior_config)
     model, likelihood = build_model(x_train, y_train, kernels, names, likelihood)
 
     if cache_path and os.path.exists(cache_path) and not force_refit:
-        with np.load(cache_path) as z:
-            samples = {k: z[k] for k in z.files if k != "_fit_seconds"}
-            fit_seconds = float(z["_fit_seconds"])
-        print(f"  loaded cached draws <- {cache_path}")
+        samples = load_hmc_samples(cache_path, allow_withdrawn=allow_withdrawn)
+        fit_seconds = float(samples.pop("_fit_seconds"))
     else:
         torch.manual_seed(SEED)
         # Timer covers the shared MAP prefit too: it is part of every
         # method's real cost (hmc/vi/hmc_laplace initialize from it). For
         # method="map" the prefit plus fit_map_samples' own fit_map is
         # continued Adam optimization of the same objective — the reported
         # point is the more-converged one.
         t0 = time.time()
         fit_map(model, likelihood, x_train, y_train, n_iter=300, lr=0.05,
                 verbose=False)
         samples = fit_gp(model, likelihood, x_train, y_train, method=method,
                          **kwargs)
         fit_seconds = time.time() - t0
         if cache_path:
             np.savez(cache_path, _fit_seconds=fit_seconds, **samples)
@@ -324,30 +327,33 @@ def render_markdown(out, model_names, budgets, data_desc):
     return "\n".join(lines) + "\n"
 
 
 def main():
     parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
     parser.add_argument("--quick", action="store_true",
                         help="tiny budgets, smoke test only")
     parser.add_argument("--methods", nargs="+", default=None,
                         choices=list(GP_INFERENCE_METHODS))
     parser.add_argument("--n-predictives", type=int, default=200,
                         help="GP predictive draws fed to BMS* per method")
     parser.add_argument("--render-only", action="store_true",
                         help="regenerate the markdown from the saved JSON")
     parser.add_argument("--force-refit", action="store_true",
                         help="ignore cached fit_gp draws and re-run samplers")
+    parser.add_argument("--allow-withdrawn", action="store_true",
+                        help="read caches the M2bR record withdrew (D33/D34), "
+                             "with a warning; labelled archival reproduction only")
     parser.add_argument("--out-suffix", default="",
                         help="suffix for json/md outputs under runs/ (used by "
                              "parallel cache-population runs so they don't "
                              "clobber the canonical files)")
     parser.add_argument("--max-tree-depth", type=int, default=None,
                         help="NUTS tree-depth cap for hmc/hmc_laplace (pyro "
                              "default 10 if unset). The capped appendix arm "
                              "uses 7; capped draws cache separately as "
                              "samples_<method>_td<N>.npz so they never "
                              "overwrite the uncapped draws.")
     args = parser.parse_args()
 
     if args.render_only:
         with open(JSON_PATH) as f:
             out = json.load(f)
@@ -402,31 +408,32 @@ def main():
                                for m, kw in budgets.items()}},
         "model_names": model_names,
         "methods": {},
     }
 
     os.makedirs(RUN_DIR, exist_ok=True)
     for method in methods:
         print(f"\n{'=' * 60}\n  method = {method}\n{'=' * 60}")
         # quick draws must never be reused; capped draws carry a _td<N> tag so
         # they never overwrite the uncapped samples_<method>.npz.
         cache_path = None if args.quick else os.path.join(
             RUN_DIR, f"samples_{method}{td_tag}.npz")
         out["methods"][method] = run_one_method(
             method, budgets[method], prior_config, x_train, y_train,
             x_eval_torch, candidate_results, args.n_predictives,
-            cache_path=cache_path, force_refit=args.force_refit)
+            cache_path=cache_path, force_refit=args.force_refit,
+            allow_withdrawn=args.allow_withdrawn)
         print(f"  fit took {out['methods'][method]['fit_seconds']:.1f}s, "
               f"{out['methods'][method]['n_draws']} draws, "
               f"{out['methods'][method]['n_predictives']} predictives")
 
     os.makedirs(os.path.dirname(json_path), exist_ok=True)
     with open(json_path, "w") as f:
         json.dump(out, f, indent=2)
     print(f"\nRaw results -> {json_path}")
 
     md = render_markdown(out, model_names, budgets, data_desc)
     with open(doc_path, "w") as f:
         f.write(md)
     print(f"Tables      -> {doc_path}")
 
 
diff --git a/experiments/practice_EvansEtAL/run.py b/experiments/practice_EvansEtAL/run.py
index 65c4b75..b0d9dc3 100644
--- a/experiments/practice_EvansEtAL/run.py
+++ b/experiments/practice_EvansEtAL/run.py
@@ -6,31 +6,31 @@ Heathcote et al. (2000) — 475 subjects, 24 experiments.
 
 Usage:
     python run.py --demo                           # synthetic test
     python run.py --data_dir ./data/evans2018      # real data, MAP
     python run.py --data_dir ./data --mode hmc     # full Bayesian
 """
 
 import numpy as np
 import torch
 import os
 import sys
 import json
 import time
 import argparse
 from pathlib import Path
-from dataclasses import dataclass
+from dataclasses import dataclass, field
 from typing import List, Dict, Optional
 import warnings
 warnings.filterwarnings("ignore")
 
 torch.set_default_dtype(torch.float64)
 
 # ── Path setup ────────────────────────────────────────────────────
 # Add project root so we can import bistar_gp
 PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
 sys.path.insert(0, str(PROJECT_ROOT))
 
 # Local sandbox imports
 from candidates import (
     build_practice_candidates, build_core_candidates,
     CandidateResult,
@@ -81,30 +81,38 @@ class SubjectResult:
     """Complete results for one learning curve."""
     dataset_id: str
     subject_id: int
     condition: str
     task_type: str
     n_trials: int
     bistar_winners: Dict
     bistar_probs: Dict
     bistar_G_diagnostics: Dict
     bic_log_ml: Dict[str, float]
     bic_winner: str
     fitted_params: Dict[str, Dict]
     gp_hyperparameters: Dict
     n_gp_samples: int
     elapsed_seconds: float
+    # Run provenance (fix pass 2a, SYNTHESIS A-23): the sampler seed, whether
+    # a failing configuration stops the run, and per configuration the
+    # requested and retained draw counts and sampler diagnostics (or why it
+    # is missing). hmc_samples goes to the .npz beside the JSON.
+    seed: Optional[int] = None
+    strict: bool = True
+    sampler_records: Dict = field(default_factory=dict)
+    hmc_samples: Dict = field(default_factory=dict)
 
 
 # ═══════════════════════════════════════════════════════════════════
 # Data Loading
 # ═══════════════════════════════════════════════════════════════════
 
 def load_data(data_dir: str) -> List[LearningCurve]:
     """
     Load learning curves from Evans et al. (2018) data.
     Tries CSV, then .mat. Falls back to synthetic demo.
     """
     data_dir = Path(data_dir)
     curves = []
 
     for csv_file in data_dir.glob("*.csv"):
@@ -319,32 +327,41 @@ def extract_map_predictives(model, likelihood, x_train, y_train, x_eval,
     for j, (_, p) in enumerate(param_refs):
         p.data.fill_(raw_params[j])
 
     return samples
 
 
 # ═══════════════════════════════════════════════════════════════════
 # Single-Subject Pipeline
 # ═══════════════════════════════════════════════════════════════════
 
 def run_one(ncurve: NormalizedCurve,
             prior_configs=None, mode="map",
             n_hmc_samples=200, n_warmup=100,
             n_eval=50, n_posterior_samples=100,
             metrics=None, taus=None, verbose=False,
-            normalize_per_draw=False) -> SubjectResult:
-    """Full BI* pipeline for one subject."""
+            normalize_per_draw=False, seed=None, strict=True) -> SubjectResult:
+    """Full BI* pipeline for one subject.
+
+    seed: passed to every fit_hmc call and, when given, to the predictive
+        subsample (np.random.default_rng(seed)); each subject's result is then
+        reproducible on its own, whatever the order and subset of subjects.
+    strict: True (default) raises when any prior configuration fails (MAP
+        fit, HMC fit, predictive extraction or BMS* scoring) instead of
+        silently dropping it; False keeps going and records the failure in
+        sampler_records (fix pass 2a, SYNTHESIS A-23).
+    """
 
     t0 = time.time()
     if prior_configs is None:
         prior_configs = ["practitioner", "moderate", "agnostic"]
     if metrics is None:
         metrics = ["pw_hellinger", "pw_mse", "pw_nll"]
     if taus is None:
         taus = np.logspace(-1, 1.5, 15)
 
     curve = ncurve.curve
 
     # GP works in normalized space
     x_train = torch.tensor(ncurve.x).double()
     y_train = torch.tensor(ncurve.y).double()
     x_eval_norm = torch.linspace(0, 1, n_eval).double()
@@ -371,86 +388,123 @@ def run_one(ncurve: NormalizedCurve,
             candidate_results.append(CandidateResult(
                 name=cand.name, mean=mean, cov=np.eye(n_eval) * ncurve.y_raw.var(),
                 noise_var=ncurve.y_raw.var(), parameters={}, n_params=cand.n_free_params + 1,
             ))
             fitted_params[cand.name] = {}
             bic_log_ml[cand.name] = -np.inf
 
     bic_winner = max(bic_log_ml, key=bic_log_ml.get)
 
     # ── Run BI* across prior configs ──
     bistar_winners = {}
     bistar_probs = {}
     bistar_G_diagnostics = {}
     gp_hp = {}
     n_gp = 0
+    sampler_records = {}
+    hmc_samples = {}
+
+    def _missing(cfg_name, stage, exc):
+        """A configuration never goes missing silently: raise under strict,
+        otherwise record why it is absent."""
+        msg = (f"{curve.dataset_id}/sub{curve.subject_id} [{cfg_name}]: {stage} "
+               f"failed ({type(exc).__name__}: {exc})")
+        if strict:
+            raise RuntimeError(msg) from exc
+        sampler_records.setdefault(cfg_name, {})["failed"] = msg
 
     for cfg_name in prior_configs:
         config = PRACTICE_CONFIGS[cfg_name]
 
         kernels, names = build_kernel(config)
         lik = build_likelihood(config)
         model, lik = build_model(x_train, y_train, kernels, names, lik)
 
         try:
             fit_map(model, lik, x_train, y_train, n_iter=300, lr=0.05, verbose=False)
-        except Exception:
+        except Exception as exc:
+            _missing(cfg_name, "MAP fit", exc)
             continue
 
         if not gp_hp:
             gp_hp = {
                 "lengthscale": model.kernel_components[0].base_kernel.lengthscale.item(),
                 "outputscale": model.kernel_components[0].outputscale.item(),
                 "noise": lik.noise.item(),
             }
 
         # Extract ψ's (in normalized space)
         if mode == "map":
             gp_samples = extract_map_predictives(
                 model, lik, x_train, y_train, x_eval_norm, n_samples=n_posterior_samples,
             )
+            sampler_records[cfg_name] = {
+                "mode": "map",
+                "n_predictives_requested": n_posterior_samples,
+                "n_predictives_retained": len(gp_samples),
+            }
         else:
             try:
-                mcmc_samples = fit_hmc(model, lik, x_train, y_train,
-                                       n_samples=n_hmc_samples, n_warmup=n_warmup, verbose=False)
+                mcmc_samples, diagnostics = fit_hmc(
+                    model, lik, x_train, y_train, n_samples=n_hmc_samples,
+                    n_warmup=n_warmup, verbose=False, seed=seed,
+                    return_diagnostics=True)
                 gp_samples = extract_gp_predictives(
                     model, lik, x_train, y_train, x_eval_norm, mcmc_samples,
                     get_kernel_builder(cfg_name), get_likelihood_builder(cfg_name),
                     n_posterior_samples=n_posterior_samples,
+                    rng=None if seed is None else np.random.default_rng(seed),
                 )
-            except Exception:
+            except Exception as exc:
+                _missing(cfg_name, "HMC fit or predictive extraction", exc)
                 continue
+            hmc_samples[cfg_name] = {k: np.asarray(v) for k, v in mcmc_samples.items()}
+            hmc_samples[cfg_name]["retained_indices"] = np.asarray(gp_samples.retained_indices)
+            sampler_records[cfg_name] = {
+                "mode": "hmc",
+                "seed": seed,
+                "n_draws_requested": n_hmc_samples,
+                "n_warmup": n_warmup,
+                "n_draws_returned": int(len(next(iter(mcmc_samples.values())))),
+                "n_predictives_requested": n_posterior_samples,
+                "n_predictives_retained": len(gp_samples),
+                "n_predictives_dropped": gp_samples.n_dropped,
+                "sampler_diagnostics": diagnostics.to_dict(),
+            }
 
         if not gp_samples:
+            _missing(cfg_name, "predictive extraction (no predictive retained)",
+                     RuntimeError("empty predictive list"))
             continue
         n_gp = max(n_gp, len(gp_samples))
 
         # Denormalize GP draws to raw (trial, RT) space for candidate comparison
         gp_samples_raw = []
         for s in gp_samples:
             raw_mean = s.mean * ncurve.y_std + ncurve.y_mean
             raw_cov = s.cov * (ncurve.y_std ** 2)
             gp_samples_raw.append(GPPosteriorSample(
                 mean=raw_mean, cov=raw_cov, hyperparameters=s.hyperparameters,
             ))
 
         # BMS* — both GP draws and candidates now in raw space
         try:
             results = run_bms_star(gp_samples_raw, candidate_results,
                                    metric_names=metrics, taus=taus,
                                    normalize_per_draw=normalize_per_draw)
-        except Exception:
+        except Exception as exc:
+            _missing(cfg_name, "BMS* scoring", exc)
             continue
 
         bistar_winners[cfg_name] = {}
         bistar_probs[cfg_name] = {}
         bistar_G_diagnostics[cfg_name] = {}
 
         for metric_name, tau_results in results.items():
             bistar_winners[cfg_name][metric_name] = {}
             bistar_probs[cfg_name][metric_name] = {}
 
             # G matrix diagnostics (same G for all taus within a metric)
             first_tau = sorted(tau_results.keys())[0]
             G = tau_results[first_tau].G_matrix
             model_names = tau_results[first_tau].instance_names
             raw_winners = np.argmin(G, axis=1)
@@ -476,89 +530,109 @@ def run_one(ncurve: NormalizedCurve,
                 winner_idx = np.argmax(bms_r.class_posteriors)
                 bistar_winners[cfg_name][metric_name][float(tau)] = bms_r.instance_names[winner_idx]
                 bistar_probs[cfg_name][metric_name][float(tau)] = {
                     n: float(p) for n, p in zip(bms_r.instance_names, bms_r.class_posteriors)
                 }
 
     return SubjectResult(
         dataset_id=curve.dataset_id, subject_id=curve.subject_id,
         condition=curve.condition, task_type=curve.task_type,
         n_trials=curve.n_trials,
         bistar_winners=bistar_winners, bistar_probs=bistar_probs,
         bistar_G_diagnostics=bistar_G_diagnostics,
         bic_log_ml=bic_log_ml, bic_winner=bic_winner,
         fitted_params=fitted_params, gp_hyperparameters=gp_hp,
         n_gp_samples=n_gp, elapsed_seconds=time.time() - t0,
+        seed=seed, strict=strict, sampler_records=sampler_records,
+        hmc_samples=hmc_samples,
     )
 
 
 # ═══════════════════════════════════════════════════════════════════
 # Batch Execution
 # ═══════════════════════════════════════════════════════════════════
 
-def run_all(curves, output_dir, prior_configs=None, mode="map", verbose=True, **kwargs):
-    """Run BI* on all curves. Save incrementally."""
+def run_all(curves, output_dir, prior_configs=None, mode="map", verbose=True,
+            seed=None, strict=True, **kwargs):
+    """Run BI* on all curves. Save incrementally.
+
+    seed and strict are passed to run_one (see there). Under strict a failing
+    subject stops the run with its error instead of printing FAIL and
+    continuing (fix pass 2a, SYNTHESIS A-23).
+    """
     output_dir = Path(output_dir)
     output_dir.mkdir(parents=True, exist_ok=True)
 
     n_total = len(curves)
     print(f"\n{'='*60}")
     print(f"BMS* for Law of Practice: {n_total} learning curves")
     print(f"Mode: {mode} | Configs: {prior_configs or ['practitioner','moderate','agnostic']}")
+    print(f"Seed: {seed} | Strict: {strict}")
     print(f"Output: {output_dir}")
     print(f"{'='*60}\n")
 
     results = []
     for i, curve in enumerate(curves):
         label = f"{curve.dataset_id}/sub{curve.subject_id}"
         if verbose:
             print(f"[{i+1}/{n_total}] {label} ({curve.n_trials}t)...", end=" ", flush=True)
 
         ncurve = normalize(curve)
         if ncurve.curve.n_trials < 8:
             if verbose: print("SKIP")
             continue
 
         try:
-            r = run_one(ncurve, prior_configs=prior_configs, mode=mode, verbose=False, **kwargs)
+            r = run_one(ncurve, prior_configs=prior_configs, mode=mode, verbose=False,
+                        seed=seed, strict=strict, **kwargs)
             results.append(r)
             if verbose:
                 print(f"BIC={r.bic_winner} t={r.elapsed_seconds:.1f}s")
 
             path = output_dir / f"{curve.dataset_id}_sub{curve.subject_id}_{curve.condition}.json"
             _save_json(r, path)
         except Exception as e:
+            if strict:
+                raise
             if verbose: print(f"FAIL: {e}")
 
     _print_aggregate(results, output_dir)
     return results
 
 
 def _save_json(result: SubjectResult, path: Path):
     d = {
         "dataset_id": result.dataset_id, "subject_id": result.subject_id,
         "condition": result.condition, "task_type": result.task_type,
         "n_trials": result.n_trials, "bic_winner": result.bic_winner,
         "bic_log_ml": result.bic_log_ml, "fitted_params": result.fitted_params,
         "gp_hyperparameters": result.gp_hyperparameters,
         "n_gp_samples": result.n_gp_samples, "elapsed_seconds": result.elapsed_seconds,
         "bistar_winners": _strkeys(result.bistar_winners),
         "bistar_probs": _strkeys(result.bistar_probs),
         "bistar_G_diagnostics": _strkeys(result.bistar_G_diagnostics),
+        "seed": result.seed,
+        "strict": result.strict,
+        "sampler_records": _strkeys(result.sampler_records),
     }
     with open(path, 'w') as f:
         json.dump(d, f, indent=2, default=str)
+    if result.hmc_samples:
+        # the sampled draws themselves, per configuration, beside the JSON
+        np.savez(path.with_name(path.stem + "_samples.npz"),
+                 **{f"{cfg}/{site}": arr for cfg, sites in result.hmc_samples.items()
+                    for site, arr in sites.items()})
 
 
 def _strkeys(d):
     if not isinstance(d, dict): return d
     return {str(k): _strkeys(v) for k, v in d.items()}
 
 
 def _print_aggregate(results, output_dir):
     """Print and save summary statistics."""
     if not results:
         return
 
     n = len(results)
 
     # BIC
@@ -632,30 +706,36 @@ def _print_aggregate(results, output_dir):
 # CLI
 # ═══════════════════════════════════════════════════════════════════
 
 def main():
     p = argparse.ArgumentParser(description="BMS* for Law of Practice")
     p.add_argument("--data_dir", default="./data")
     p.add_argument("--output_dir", default="./results")
     p.add_argument("--mode", default="map", choices=["map", "hmc"])
     p.add_argument("--n_hmc_samples", type=int, default=200)
     p.add_argument("--n_eval", type=int, default=50)
     p.add_argument("--n_posterior_samples", type=int, default=100)
     p.add_argument("--configs", nargs="+", default=["practitioner", "moderate", "agnostic"])
     p.add_argument("--demo", action="store_true", help="Synthetic test data")
     p.add_argument("--normalize_per_draw", action="store_true",
                    help="Subtract per-draw min G before Boltzmann (removes systematic bias)")
+    p.add_argument("--seed", type=int, default=None,
+                   help="Sampler and predictive-subsample seed, recorded in every subject JSON")
+    p.add_argument("--allow_missing_configs", action="store_true",
+                   help="Record a failing prior configuration and continue "
+                        "instead of stopping the run (non-strict)")
     args = p.parse_args()
 
     curves = generate_demo_data(50) if args.demo else load_data(args.data_dir)
     if not curves:
         print("No data. Use --demo."); return
 
     print(f"Loaded {len(curves)} learning curves")
     run_all(curves, args.output_dir, prior_configs=args.configs, mode=args.mode,
             n_hmc_samples=args.n_hmc_samples, n_eval=args.n_eval,
             n_posterior_samples=args.n_posterior_samples,
-            normalize_per_draw=args.normalize_per_draw)
+            normalize_per_draw=args.normalize_per_draw,
+            seed=args.seed, strict=not args.allow_missing_configs)
 
 
 if __name__ == "__main__":
     main()
diff --git a/experiments/prior_sensitivity_study.py b/experiments/prior_sensitivity_study.py
index db5cf6f..52560e4 100644
--- a/experiments/prior_sensitivity_study.py
+++ b/experiments/prior_sensitivity_study.py
@@ -684,36 +684,45 @@ def _sir_bms(pc, x, y, x_eval, candidate_results, ths, lml, n_pred,
     if not gp_samples:
         raise RuntimeError("no valid GP predictives from SIR draws")
     if len(gp_samples) != n_pred:
         raise RuntimeError(
             f"_sir_bms: {len(gp_samples)} GP predictives retained of {n_pred} "
             "SIR draws; the paper path must not score a numerically selected "
             "subset of the draws (2026-09 review FIX-1)")
     results = run_bms_star(gp_samples, candidate_results, fmc.METRICS,
                            np.array(fmc.TAUS))
     per_metric, G_by_metric = {}, {}
     for metric in fmc.METRICS:
         bms_by_tau = results[metric]
         G = bms_by_tau[fmc.TAUS[0]].G_matrix
         G_by_metric[metric] = G
         winners = np.argmin(G, axis=1)
+        tau_free = bms_by_tau[fmc.TAUS[0]]
         per_metric[metric] = {
             "posteriors": {str(tau): [float(pp) for pp in
                                       bms_by_tau[tau].instance_posteriors]
                            for tau in fmc.TAUS},
+            # first-index argmin, kept so committed artifacts stay comparable
             "hard_win_fractions": [float(np.mean(winners == j))
                                    for j in range(G.shape[1])],
+            # tie-aware draw-win record and per-tau weight concentration
+            # (fix pass 2a, SYNTHESIS A-13); weight_ess is not an MCMC ESS
+            "hard_win_credit": [float(c) for c in tau_free.hard_win_credit],
+            "attainment": [float(a) for a in tau_free.attainment],
+            "tie_fraction": float(tau_free.tie_fraction),
+            "weight_ess": {str(tau): [float(e) for e in bms_by_tau[tau].weight_ess]
+                           for tau in fmc.TAUS},
         }
     return per_metric, G_by_metric, ths[idx, ORDER.index("noise")], idx
 
 
 def stage_is_one(name, pc, x, y, x_eval, candidate_results, n_predictives,
                  is_seeds, smoke=False, n_boot=1000):
     """SIR-resample hyperparameter draws from the pooled stage-A prior-IS
     weights and push them through the same predictive-extraction + BMS*
     pipeline as stage B. Mass-faithful by construction (no mode-locked
     sampler in the loop); validity gated on pooled IS ESS >= 100
     (pre-registered floor). Uncertainty reported two ways: (a) bootstrap
     over SIR draws (resample G-matrix rows, rerun the exact soft_transfer
     aggregation) — the SIR/MC error given the weights; (b) per-IS-seed
     replication (independent 60-200k-draw pools) — the weight-estimation
     scatter."""
diff --git a/tests/test_bms_aggregation.py b/tests/test_bms_aggregation.py
index fbb1f98..0ec0aee 100644
--- a/tests/test_bms_aggregation.py
+++ b/tests/test_bms_aggregation.py
@@ -1,34 +1,37 @@
 """
 Regression tests for the BMS* aggregation fixes in bistar_gp/bms_star.py.
 
 Two confirmed result-invalidating bugs are guarded here:
   1. soft_transfer used a per-row (per-draw) max for "stability", which does not
      cancel under the over-draw mean + cross-candidate normalization, so it
      reweighted GP draws and silently behaved like normalize_per_draw=False->True.
      The fix subtracts a single global scalar, which is posterior-preserving.
   2. compute_G_matrix replaced failed cells with 10*max_finite, which is the
      SMALLEST value (best score) when the metric can be negative (pw_nll), so a
      numerically failed candidate could win. The fix uses a strictly-worse penalty.
+     Since fix pass 2a the penalty covers partial failures only; a candidate that
+     fails on every draw raises EvaluationFailure (SYNTHESIS A-1).
 """
 
 import numpy as np
 import pytest
 from types import SimpleNamespace
 
 import bistar_gp.bms_star as bs
 from bistar_gp.bms_star import soft_transfer, compute_G_matrix
+from bistar_gp.errors import EvaluationFailure
 
 rng = np.random.default_rng(0)
 
 
 def _posteriors(G, tau, **kw):
     names = [f"m{j}" for j in range(G.shape[1])]
     return soft_transfer(G, tau, names, **kw).instance_posteriors
 
 
 def test_soft_transfer_matches_direct_formula():
     """Implementation must equal the documented (1/N) Σ_i exp(-G_ij/τ), normalized."""
     G = rng.gamma(2.0, 1.0, size=(7, 4))
     tau = 1.3
     direct = np.exp(-G / tau).mean(axis=0)
     direct = direct / direct.sum()
@@ -115,43 +118,52 @@ def test_weighted_equal_mass_candidates_split_evenly():
 def test_weighted_invariant_to_global_G_offset():
     G = rng.gamma(2.0, 1.0, size=(6, 4))
     lw = rng.normal(0, 1, size=6)
     base = _wposteriors(G, 0.9, lw)
     assert np.allclose(base, _wposteriors(G + 123.4, 0.9, lw), atol=1e-10)
 
 
 # ── compute_G_matrix failure-sentinel ──────────────────────────────
 
 @pytest.fixture
 def flaky_metric():
     """A negative-valued metric (like pw_nll) that raises for one candidate."""
     name = "_flaky_test_metric"
 
     def metric(mu_p, cov_p, mu_q, cov_q):
-        if float(mu_q[0]) == 999.0:           # the "failed" candidate
+        # 999 fails on every draw; 1.5 fails only on the draw with mean 7
+        if float(mu_q[0]) == 999.0 or (float(mu_q[0]) == 1.5 and float(mu_p[0]) == 7.0):
             raise ValueError("simulated numerical failure")
         return -5.0 + float(mu_q[0])          # negative divergence values
 
     bs.METRICS[name] = metric
     yield name
     del bs.METRICS[name]
 
 
 def test_failed_cell_is_worse_than_all_finite_for_negative_metric(flaky_metric):
-    psi = [SimpleNamespace(mean=np.array([0.0]), cov=np.eye(1)) for _ in range(3)]
+    psi = [SimpleNamespace(mean=np.array([m]), cov=np.eye(1)) for m in (0.0, 0.0, 7.0)]
     cands = [SimpleNamespace(mean=np.array([float(j)]), cov=np.eye(1)) for j in (0, 1)]
-    cands.append(SimpleNamespace(mean=np.array([999.0]), cov=np.eye(1)))  # fails
+    cands.append(SimpleNamespace(mean=np.array([1.5]), cov=np.eye(1)))  # fails on draw 2
 
     G = compute_G_matrix(psi, cands, flaky_metric)
-    finite_max = G[:, :2].max()
-    assert np.all(G[:, 2] > finite_max)          # failure is the WORST, not best
+    failed = np.zeros_like(G, dtype=bool)
+    failed[2, 2] = True
+    assert G[2, 2] > G[~failed].max()            # failure is the WORST, not best
     assert np.all(np.argmin(G, axis=1) != 2)     # failed candidate never wins a row
 
+    cands[2] = SimpleNamespace(mean=np.array([999.0]), cov=np.eye(1))  # fails on every draw
+    with pytest.raises(EvaluationFailure):       # a dead column is a failure, not a penalty
+        compute_G_matrix(psi, cands, flaky_metric)
+
 
 def test_failed_candidate_gets_lowest_posterior(flaky_metric):
-    psi = [SimpleNamespace(mean=np.array([0.0]), cov=np.eye(1)) for _ in range(3)]
+    psi = [SimpleNamespace(mean=np.array([m]), cov=np.eye(1)) for m in (0.0, 0.0, 7.0)]
     cands = [SimpleNamespace(mean=np.array([0.0]), cov=np.eye(1)),    # best (G=-5)
              SimpleNamespace(mean=np.array([1.0]), cov=np.eye(1)),    # G=-4
-             SimpleNamespace(mean=np.array([999.0]), cov=np.eye(1))]  # fails
+             SimpleNamespace(mean=np.array([1.5]), cov=np.eye(1))]    # G=-3.5, fails on draw 2
     G = compute_G_matrix(psi, cands, flaky_metric)
     p = _posteriors(G, 1.0)
     assert p[0] > p[1] > p[2]
+    typical = G.copy()
+    typical[2, 2] = G[0, 2]                      # failed cell at the candidate's finite value
+    assert p[2] < _posteriors(typical, 1.0)[2]   # a failure costs mass, never adds it
```

# G. New file: bistar_gp/errors.py (full text)
```python
"""Exceptions shared across the package.

`EvaluationFailure` lives here rather than in `laplace_evidence` because the
modules that raise it (`laplace_evidence`, `induced_prior`, `bms_star`,
`candidates`) import one another in that direction; `laplace_evidence`
re-exports it, so existing imports keep working (fix pass 2a, SYNTHESIS A-2).
"""


class EvaluationFailure(RuntimeError):
    """A candidate predictor, divergence metric or candidate fit failed, and
    no valid number exists for the quantity that needed it.

    Raised under strict evaluation, and wherever a failure would otherwise be
    replaced by a substitute value (a penalty, a preset parameter, a uniform
    weight). A subclass of RuntimeError so that callers catching the earlier
    exception still do; the optimizer fallback handlers in `laplace_evidence`
    re-raise it so it can never turn into a start-point expansion.
    """
```

# G. New file: tests/test_fix2a_contracts.py (full text)
```python
"""
Fix pass 2a (2026-09-26 project review, SYNTHESIS section 10): package
contracts, one pinning test per queue item. Each test fails on the pre-2a
code (the fix branch at 69deeda).

2a-1  compute_G_matrix: an all-failed table and a candidate that failed on
      every draw raise; a partial failure keeps the penalty and is logged.
2a-2  compute_induced_prior: failed parameter points carry zero mass (strict
      raises); every point failing raises; the ESS counts valid points only.
2a-3  extraction and decomposition require every sampled site, and one
      draw count across arrays whatever the dictionary order.
2a-4  is_log_Z_Mx rejects an empty or invalid tau ladder.
2a-5  a sinusoid fit with no successful restart raises.
2a-6  DecompositionResult.noise_var is the retained-draw mean, order-free.
2a-7  the withdrawn-cache registry follows D33/D34 and guards the
      fit-method experiment's cache read.
2a-8  soft_transfer warns below an ESS floor; ties split the console credit
      and the SIR serialization records tie-aware draw-win statistics.
2a-9  the tau sweep and the ablation ladder carry the Laplace records;
      compute_cholesky logs each jitter escalation.
2a-10 the Case D producer fails loud and records seed, counts, diagnostics
      and the sampled draws.
"""

import json
import logging
import os
import re
import sys
import warnings
from types import SimpleNamespace

import numpy as np
import pytest
from scipy.optimize import OptimizeResult

torch = pytest.importorskip("torch")
pytest.importorskip("gpytorch")

from gpytorch.constraints import Positive
from gpytorch.kernels import RBFKernel, ScaleKernel
from gpytorch.priors import GammaPrior

import bistar_gp.laplace_evidence as le
import bistar_gp.metrics_v2  # noqa: F401  registers pw_kl_vcal
from bistar_gp import generate_toy_data
from bistar_gp.aggregation_v3 import compute_log_marginal_likelihoods
from bistar_gp.bms_star import (
    METRICS, GPPosteriorSample, compute_G_matrix, extract_gp_predictives,
    run_bms_star, soft_transfer,
)
from bistar_gp.candidates import CandidateModel, CandidateResult, SinLinearModel, SinusoidalModel
from bistar_gp.config import PRIOR_CONFIGS, WITHDRAWN_CACHES, is_withdrawn_cache, load_hmc_samples
from bistar_gp.debias import _raw_parameter_map, decompose_model_hmc, decompose_model_mcmc
from bistar_gp.decompose import compute_cholesky
from bistar_gp.errors import EvaluationFailure
from bistar_gp.induced_prior import ModelParameterSpace, ParameterSpec, compute_induced_prior
from bistar_gp.model import build_model, build_toy_kernels

torch.set_default_dtype(torch.float64)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPERIMENTS = os.path.join(REPO, "experiments")
PRACTICE = os.path.join(EXPERIMENTS, "practice_EvansEtAL")

SITES = {
    "ls": "covar_module.kernels.0.base_kernel.lengthscale_prior",
    "os": "covar_module.kernels.0.outputscale_prior",
    "lv": "covar_module.kernels.1.variance_prior",
    "noise": "likelihood.noise_covar.noise_prior",
}


def _toy_samples(ls, os_, lv, noise):
    return {SITES["ls"]: np.asarray(ls, float), SITES["os"]: np.asarray(os_, float),
            SITES["lv"]: np.asarray(lv, float), SITES["noise"]: np.asarray(noise, float)}


@pytest.fixture
def toy():
    x = torch.linspace(-6, 6, 14)
    y = torch.sin(x) + 0.25 * x
    kers, names = build_toy_kernels()
    model, lik = build_model(x, y, kers, names)
    return model, lik, x, y, torch.linspace(-7, 7, 9)


@pytest.fixture
def registered():
    """Register throwaway metrics for one test and remove them afterwards."""
    names = []

    def register(name, fn):
        METRICS[name] = fn
        names.append(name)
        return name

    yield register
    for name in names:
        del METRICS[name]


def _single_kernel_builder():
    k = ScaleKernel(RBFKernel(lengthscale_constraint=Positive(),
                              lengthscale_prior=GammaPrior(2.0, 2.0)),
                    outputscale_constraint=Positive(),
                    outputscale_prior=GammaPrior(2.0, 1.0))
    return [k], ["se"]


# ── 2a-1 ────────────────────────────────────────────────────────────

def test_2a1_failed_divergences_raise_or_are_flagged(registered, caplog):
    def mse(mp, cp, mq, cq):
        return float(np.mean((np.asarray(mp) - np.asarray(mq)) ** 2))

    def always(mp, cp, mq, cq):
        raise ValueError("always failing metric")

    def candidate_b_fails(mp, cp, mq, cq):
        if float(mq[0]) == 99.0:
            raise np.linalg.LinAlgError("candidate cannot be evaluated")
        return mse(mp, cp, mq, cq)

    def draw_one_fails(mp, cp, mq, cq):
        if float(mp[0]) == 7.0:
            raise ValueError("one draw cannot be evaluated")
        return -5.0 + 0.01 * mse(mp, cp, mq, cq)          # negative-valued

    always_m = registered("_fix2a_always", always)
    cand_m = registered("_fix2a_candidate_b", candidate_b_fails)
    draw_m = registered("_fix2a_draw_one", draw_one_fails)

    gp = [GPPosteriorSample(mean=np.array([m, 0.0, 0.0]), cov=np.eye(3), hyperparameters={})
          for m in (0.0, 7.0, 1.0)]
    a = CandidateResult(name="a", mean=np.ones(3), cov=np.eye(3), noise_var=1.0, parameters={})
    b = CandidateResult(name="b", mean=np.array([99.0, 0.0, 0.0]), cov=np.eye(3),
                        noise_var=1.0, parameters={})
    c = CandidateResult(name="c", mean=np.zeros(3), cov=np.eye(3), noise_var=1.0, parameters={})

    with pytest.raises(EvaluationFailure, match="all 6 divergence evaluations"):
        compute_G_matrix(gp, [a, c], always_m)
    with pytest.raises(EvaluationFailure, match="all 6"):
        run_bms_star(gp, [a, c], metric_names=[always_m], taus=np.array([1.0]))
    with pytest.raises(EvaluationFailure, match=r"\['b'\] failed on every one of the 3 draws"):
        compute_G_matrix(gp, [a, b], cand_m)

    with caplog.at_level(logging.WARNING, logger="bistar_gp.bms_star"):
        G = compute_G_matrix(gp, [a, c], draw_m)
    finite = np.delete(G, 1, axis=0)
    max_finite = finite.max()
    assert np.all(G[1] == max_finite + 10.0 * (abs(max_finite) + 1.0))
    assert np.all(G[1] > finite.max())                     # a failure never wins
    warned = [r.getMessage() for r in caplog.records if "evaluations failed" in r.getMessage()]
    assert len(warned) == 1 and "2 of 6" in warned[0] and "('a', 1), ('c', 1)" in warned[0]

    caplog.clear()                                         # repeated names keep their counts
    twin = CandidateResult(name="a", mean=np.zeros(3), cov=np.eye(3), noise_var=1.0, parameters={})
    with caplog.at_level(logging.WARNING, logger="bistar_gp.bms_star"):
        compute_G_matrix(gp, [a, twin], draw_m)
    assert any("('a', 1), ('a', 1)" in r.getMessage() for r in caplog.records)
    with pytest.raises(ValueError, match="empty table"):
        compute_G_matrix([], [a, c], draw_m)


# ── 2a-2 ────────────────────────────────────────────────────────────

def test_2a2_induced_prior_failed_points_carry_no_mass():
    x = np.linspace(0.0, 1.0, 5)
    gp = [GPPosteriorSample(mean=np.zeros(5), cov=np.eye(5), hyperparameters={})]
    # The Codex C02 configuration: NaN predictions for a < 0, valid G ~ 2e6
    # elsewhere, so the former 1e6 sentinel outranked every valid point.
    space = ModelParameterSpace(
        model_name="Shift", param_specs=[ParameterSpec("a", (-1.0, 1.0), None)],
        predict_fn=lambda x_, p: np.full_like(x_, np.nan) if p["a"] < 0 else np.full_like(x_, 2000.0),
        noise_param="sigma")
    kw = dict(metric_name="pw_kl_vcal", tau=100.0, n_param_samples=20, seed=42)

    with pytest.raises(EvaluationFailure, match="every divergence evaluation failed"):
        compute_induced_prior(space, gp, x, **kw)

    res = compute_induced_prior(space, gp, x, strict=False, **kw)
    failed = res.param_samples[:, 0] < 0
    n_failed = int(failed.sum())
    assert 0 < n_failed < 20
    assert res.n_failed_points == n_failed
    assert np.all(res.weights[failed] == 0.0) and np.all(np.isnan(res.G_per_sample[failed]))
    assert res.weights[~failed].sum() == pytest.approx(1.0)
    # every valid point has the same G, so the ESS is exactly their number
    assert res.effective_sample_size == pytest.approx(20 - n_failed)

    def _raise(x_, p):
        raise ZeroDivisionError("always failing predictor")

    raising = ModelParameterSpace(model_name="Raise", param_specs=space.param_specs,
                                  predict_fn=_raise, noise_param="sigma")
    with pytest.raises(EvaluationFailure, match="always failing predictor"):
        compute_induced_prior(raising, gp, x, **kw)
    with pytest.raises(EvaluationFailure, match="every one of the 20 parameter points"):
        compute_induced_prior(raising, gp, x, strict=False, **kw)


# ── 2a-3 ────────────────────────────────────────────────────────────

def test_2a3_incomplete_or_ragged_sample_dicts_raise(toy):
    model, lik, x, y, x_eval = toy
    full = _toy_samples([0.7, 3.0, 1.2], [1.5, 0.4, 0.9], [0.05, 0.2, 0.1], [0.1, 0.3, 0.2])
    kw = dict(kernel_builder=build_toy_kernels, n_posterior_samples=3)

    def extract(samples, **extra):
        return extract_gp_predictives(model, lik, x, y, x_eval, samples, **kw, **extra)

    def decompose(samples, **extra):
        return decompose_model_hmc(model, lik, x, y, x_eval, samples, **kw, **extra)

    for site in full:
        partial = {k: v for k, v in full.items() if k != site}
        for route in (extract, decompose):
            with pytest.raises(ValueError, match=re.escape(site)):
                route(partial, rng=np.random.default_rng(0))

    ragged = dict(full, **{SITES["ls"]: full[SITES["ls"]][:2]})
    for route in (extract, decompose):
        messages = []
        for order in (list(ragged), list(reversed(ragged))):
            with pytest.raises(ValueError, match="one nonempty leading length") as err:
                route({k: ragged[k] for k in order}, rng=np.random.default_rng(0))
            messages.append(str(err.value))
        assert messages[0] == messages[1]

    a = extract(full, rng=np.random.default_rng(0))
    b = extract({k: full[k] for k in reversed(list(full))}, rng=np.random.default_rng(0))
    assert len(a) == len(b) == 3
    for pa, pb in zip(a, b):
        assert np.array_equal(pa.mean, pb.mean) and np.array_equal(pa.cov, pb.cov)

    # legacy-era names cover the same sites (no false "missing")
    legacy = {k.replace("covar_module.kernels.", "kernel_components."): v
              for k, v in full.items() if k != SITES["noise"]}
    legacy["noise_covar.noise_prior"] = full[SITES["noise"]]
    assert len(extract(legacy, rng=np.random.default_rng(0))) == 3

    # a single-kernel model's sites, complete and with one removed
    single = {"covar_module.base_kernel.lengthscale_prior": np.array([0.4, 2.0]),
              "covar_module.outputscale_prior": np.array([0.5, 1.5]),
              SITES["noise"]: np.array([0.1, 0.2])}
    kers, names = _single_kernel_builder()
    smodel, slik = build_model(x, y, kers, names)
    sk = dict(kernel_builder=_single_kernel_builder, n_posterior_samples=2)
    assert len(extract_gp_predictives(smodel, slik, x, y, x_eval, single, **sk)) == 2
    with pytest.raises(ValueError, match="covar_module.outputscale_prior"):
        extract_gp_predictives(smodel, slik, x, y, x_eval,
                               {k: v for k, v in single.items() if "outputscale" not in k}, **sk)

    good = {k: float(v[0]) for k, v in full.items()}
    no_noise = {k: v for k, v in good.items() if k != SITES["noise"]}
    with pytest.raises(ValueError, match=re.escape(SITES["noise"])):
        compute_log_marginal_likelihoods(
            [GPPosteriorSample(mean=np.zeros(2), cov=np.eye(2), hyperparameters=no_noise)],
            x, y, kernel_builder=build_toy_kernels)
    lm = compute_log_marginal_likelihoods(
        [GPPosteriorSample(mean=np.zeros(2), cov=np.eye(2), hyperparameters=good)],
        x, y, kernel_builder=build_toy_kernels)
    assert np.isfinite(lm).all()


# ── 2a-4 ────────────────────────────────────────────────────────────

def test_2a4_tau_ladder_is_validated(registered):
    zero = registered("_fix2a_zero", lambda mp, cp, mq, cq: 0.0)
    space = ModelParameterSpace(
        model_name="Box", param_specs=[ParameterSpec("a", (-1.0, 1.0), None),
                                       ParameterSpec("b", (0.0, 2.0), None)],
        predict_fn=lambda x_, p: p["a"] * x_ + p["b"], noise_param="sigma")
    x = np.linspace(0.0, 1.0, 4)
    gp = SimpleNamespace(mean=np.zeros(4), cov=np.eye(4))
    for bad in [(), (0.3, np.nan), (0.3, -1.0), (0.0,)]:
        with pytest.raises(ValueError, match="tau_ladder"):
            le.is_log_Z_Mx(space, x, gp, [1.0], n_is=200, metric_name=zero, tau_ladder=bad)
    # constant integrand: the raw integral is the box volume (2 x 2)
    r = le.is_log_Z_Mx(space, x, gp, [1.0], n_is=20_000, seed=0, metric_name=zero)
    assert np.exp(r.log_Z[0]) == pytest.approx(4.0, rel=0.05)


# ── 2a-5 ────────────────────────────────────────────────────────────

def test_2a5_sinusoid_fit_without_a_successful_restart_raises(monkeypatch):
    x = np.linspace(-10.0, 10.0, 20)
    y = np.sin(x) + 0.25 * x

    def always_raise(*a, **k):
        raise FloatingPointError("restart blew up")

    for cls in (SinusoidalModel, SinLinearModel):
        m = cls()
        monkeypatch.setattr(m, "_fit_mle", always_raise)
        with pytest.raises(EvaluationFailure, match="restart blew up"):
            m.fit(x, y)

        m2 = cls()
        seen = {"n": 0}

        def second_only(*a, **k):
            seen["n"] += 1
            if seen["n"] != 2:
                raise FloatingPointError("only the second restart runs")
            seen["out"] = CandidateModel._fit_mle(m2, *a, **k)
            return seen["out"]

        monkeypatch.setattr(m2, "_fit_mle", second_only)
        m2.fit(x, y)
        params = seen["out"][0]
        assert (m2.A, m2.omega, m2.phi) == (params[0], params[1], params[2])
        assert m2.sigma == np.exp(params[-1])


# ── 2a-6 ────────────────────────────────────────────────────────────

def test_2a6_noise_var_is_the_retained_draw_mean_and_order_free(toy):
    model, lik, x, y, x_eval = toy
    noise = np.array([0.05, 0.1, 0.3])
    samples = _toy_samples([0.7, 3.0, 1.2], [1.5, 0.4, 0.9], [0.05, 0.2, 0.1], noise)
    perm = [2, 0, 1]
    permuted = {k: v[perm] for k, v in samples.items()}
    kw = dict(kernel_builder=build_toy_kernels, n_posterior_samples=3)
    a = decompose_model_hmc(model, lik, x, y, x_eval, samples, rng=np.random.default_rng(0), **kw)
    b = decompose_model_hmc(model, lik, x, y, x_eval, permuted, rng=np.random.default_rng(0), **kw)

    names = list(_raw_parameter_map(model, lik))
    draw_rng = np.random.default_rng(3)
    raw = {n: draw_rng.normal(size=3) for n in names}
    raw_perm = {n: v[perm] for n, v in raw.items()}
    c = decompose_model_mcmc(model, lik, x, y, x_eval, raw, n_posterior_samples=3,
                             rng=np.random.default_rng(0))
    d = decompose_model_mcmc(model, lik, x, y, x_eval, raw_perm, n_posterior_samples=3,
                             rng=np.random.default_rng(0))

    for r1, r2 in ((a, b), (c, d)):
        assert isinstance(r1.noise_var, float)
        assert r1.noise_var == pytest.approx(r2.noise_var, rel=1e-12)
        assert r1.noise_var == pytest.approx(np.mean(r1.noise_var_draws), rel=1e-12)
        assert np.allclose(np.sort(r1.noise_var_draws), np.sort(r2.noise_var_draws))
        assert np.allclose(r1.full_mean, r2.full_mean) and np.allclose(r1.full_std, r2.full_std)
        for n in r1.components:
            for field in ("mean", "std", "cov"):
                assert np.allclose(getattr(r1.components[n], field),
                                   getattr(r2.components[n], field), rtol=1e-10, atol=1e-12)
    assert a.noise_var == pytest.approx(noise.mean(), rel=1e-12)


# ── 2a-7 ────────────────────────────────────────────────────────────

def test_2a7_withdrawn_caches_are_refused_on_every_route(tmp_path, monkeypatch):
    sys.path.insert(0, EXPERIMENTS)
    fmc = pytest.importorskip("fit_method_metric_comparison")
    # the D33/D34 classes: informative HMC (and hmc_laplace), vague and
    # gamma_relaxed HMC, every historical VI cache
    for name in ("runs/fit_method_metric_comparison/samples_hmc_td7.npz",
                 "runs/fit_method_metric_comparison/samples_hmc_laplace.npz",
                 "runs/prior_sensitivity/samples_informative_hmc_td7.npz",
                 "runs/prior_sensitivity/samples_vague_hmc_td7.npz",
                 "runs/prior_sensitivity/samples_gamma_relaxed_hmc_td7.npz",
                 "runs/fit_method_metric_comparison/samples_vi.npz",
                 "runs/prior_sensitivity/samples_toy_elicited_vi_td7.npz"):
        assert name in WITHDRAWN_CACHES
    for kept in ("runs/prior_sensitivity/is_draws_toy_elicited_s0.npz",
                 "runs/fit_method_metric_comparison/samples_map.npz"):
        assert not is_withdrawn_cache(tmp_path / kept)

    x, y, _ = generate_toy_data()
    x_eval = torch.linspace(-11, 11, 6)
    pc = PRIOR_CONFIGS["informative"]
    for entry in WITHDRAWN_CACHES:
        path = tmp_path / (entry + "samples.npz" if entry.endswith("/") else entry)
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez(path, _fit_seconds=1.0, a=np.arange(3.0))
        with pytest.raises(RuntimeError, match="WITHDRAWN"):
            load_hmc_samples(str(path))
        with monkeypatch.context() as m:
            m.setattr(np, "load", lambda *a, **k: pytest.fail(f"np.load reached for {entry}"))
            with pytest.raises(RuntimeError, match="WITHDRAWN"):
                fmc.run_one_method("hmc", {}, pc, x, y, x_eval, [], 2, cache_path=str(path))

    # a cache that is not withdrawn still flows through the guarded route
    ok = tmp_path / "runs/other_study/samples_hmc.npz"
    ok.parent.mkdir(parents=True, exist_ok=True)
    np.savez(ok, _fit_seconds=2.5, **_toy_samples([1.0, 1.5], [0.8, 1.0], [0.05, 0.07], [0.2, 0.25]))
    cands = [CandidateResult(name=n, mean=np.full(6, s), cov=np.eye(6) * 0.25, noise_var=0.25,
                             parameters={}) for n, s in (("lo", 0.0), ("hi", 1.0))]
    out = fmc.run_one_method("hmc", {}, pc, x, y, x_eval, cands, 2, cache_path=str(ok))
    assert out["fit_seconds"] == 2.5 and out["n_draws"] == 2 and out["n_predictives"] == 2
    assert "_fit_seconds" not in out["hyperparameters"]


# ── 2a-8 ────────────────────────────────────────────────────────────

def test_2a8_ess_floor_warning_and_tie_aware_draw_wins(caplog, capsys, monkeypatch):
    concentrated = np.array([[0.0, 0.0], [50.0, 50.0], [50.0, 50.0], [50.0, 50.0]])
    with caplog.at_level(logging.WARNING, logger="bistar_gp.bms_star"):
        r = soft_transfer(concentrated, 1.0, ["a", "b"], metric_name="m", ess_warn=2.0)
    assert np.all(r.weight_ess < 2.0)
    assert any("weight ESS below 2" in rec.getMessage() for rec in caplog.records)
    caplog.clear()
    with caplog.at_level(logging.WARNING, logger="bistar_gp.bms_star"):
        r = soft_transfer(np.zeros((4, 2)), 1.0, ["a", "b"], metric_name="m", ess_warn=2.0)
    assert np.all(r.weight_ess == pytest.approx(4.0))
    assert not any("weight ESS" in rec.getMessage() for rec in caplog.records)

    sys.path.insert(0, EXPERIMENTS)
    pss = pytest.importorskip("prior_sensitivity_study")
    x, y, _ = generate_toy_data()
    monkeypatch.setattr(pss, "extract_gp_predictives", lambda *a, **k: [
        GPPosteriorSample(mean=np.zeros(3), cov=np.eye(3), hyperparameters={})] * 4)
    twins = [CandidateResult(name=n, mean=np.ones(3), cov=np.eye(3) * 0.1, noise_var=0.1,
                             parameters={}) for n in ("first", "second")]
    ths = np.abs(np.random.default_rng(0).normal(size=(6, 4))) + 0.1
    capsys.readouterr()
    per_metric, _, _, _ = pss._sir_bms(pss.STUDY_CONFIGS["toy_elicited"], x, y,
                                       torch.linspace(-11, 11, 3), twins, ths, np.zeros(6), 4)
    printed = capsys.readouterr().out
    assert "first wins 2/4 draws" in printed and "second wins 2/4 draws" in printed
    for metric, rec in per_metric.items():
        assert rec["hard_win_fractions"] == [1.0, 0.0], metric      # legacy key kept as is
        assert rec["hard_win_credit"] == [0.5, 0.5], metric
        assert rec["attainment"] == [1.0, 1.0] and rec["tie_fraction"] == 1.0
        assert set(rec["weight_ess"]) == set(rec["posteriors"])
        assert all(len(v) == 2 for v in rec["weight_ess"].values())


# ── 2a-9 ────────────────────────────────────────────────────────────

def test_2a9_sweep_and_ladder_carry_records_and_jitter_escalation_logs(registered, caplog,
                                                                         monkeypatch):
    mse = registered("_fix2a_mse",
                     lambda mp, cp, mq, cq: float(np.mean((np.asarray(mp) - np.asarray(mq)) ** 2)))
    x = np.linspace(0.0, 4.0, 15)
    gp = SimpleNamespace(mean=0.5 * x - 0.3, cov=np.eye(15) * 0.05)
    specs = [ParameterSpec("a", (-2.0, 2.0), None), ParameterSpec("b", (-2.0, 2.0), None)]
    spaces = {"Lin": ModelParameterSpace("Lin", specs, lambda x_, p: p["a"] * x_ + p["b"]),
              "Quad": ModelParameterSpace("Quad", specs, lambda x_, p: p["a"] * x_ ** 2 + p["b"])}
    y = gp.mean + 0.05
    taus = [0.5, 2.0]

    for construction in ("baseline", "I", "II"):
        sweep = le.model_posterior_tau_sweep(spaces, x, y, x, gp, None, taus,
                                             construction=construction, metric_name=mse)
        names, post = sweep                                   # unpacks as before
        assert names == ["Lin", "Quad"] and post.shape == (2, 2)
        assert sweep.converged.shape == sweep.n_clipped.shape == sweep.n_starts_failed.shape == (2, 2)
        assert sweep.all_converged is True and not sweep.n_starts_failed.any()
    ladder = le.ablation_ladder_posteriors(spaces, x, y, x, gp, None, metric_name=mse, tau=1.0)
    assert set(ladder) == {"baseline", "I", "II"} and ladder.all_converged is True
    assert ladder.converged["II"] == {"Lin": True, "Quad": True}

    def not_converged(fun, x0, **k):
        return OptimizeResult(x=np.asarray(x0, float), success=False, status=2,
                              message="forced non-convergence", nit=0, nfev=1, fun=fun(x0))

    with monkeypatch.context() as m:
        m.setattr(le, "minimize", not_converged)
        sweep = le.model_posterior_tau_sweep(spaces, x, y, x, gp, None, taus,
                                             construction="II", metric_name=mse)
        assert sweep.all_converged is False and not sweep.converged.any()
        assert np.all(sweep.n_starts_failed == 1)
        ladder = le.ablation_ladder_posteriors(spaces, x, y, x, gp, None, metric_name=mse, tau=1.0)
        assert ladder.all_converged is False
        assert ladder.converged["baseline"]["Lin"] is False
        assert ladder.n_starts_failed["I"]["Quad"] == 2       # Z_Mx and p_ord each failed once

    with caplog.at_level(logging.WARNING, logger="bistar_gp.decompose"):
        L = compute_cholesky(torch.zeros(3, 3), 0.0, jitter=-5e-6)   # first retry succeeds
    assert torch.allclose(L @ L.T, 5e-6 * torch.eye(3))
    escalations = [r.getMessage() for r in caplog.records if "extra jitter" in r.getMessage()]
    assert escalations == [escalations[0]] and "1e-05" in escalations[0]


# ── 2a-10 ───────────────────────────────────────────────────────────

class _Diagnostics:
    def __init__(self, n):
        self.n = n

    def to_dict(self):
        return {"sampler": "stub", "n_draws": self.n}


def test_2a10_case_d_producer_fails_loud_and_records_provenance(tmp_path, monkeypatch):
    sys.path.insert(0, PRACTICE)
    saved_filters = warnings.filters[:]
    try:
        practice_run = pytest.importorskip("run")      # run.py silences warnings at import
    finally:
        warnings.filters[:] = saved_filters
    assert os.path.dirname(practice_run.__file__) == PRACTICE

    calls = []

    def fake_fit_hmc(model, likelihood, train_x, train_y, n_samples, n_warmup, verbose,
                     seed=None, return_diagnostics=False, fail_on=None):
        calls.append(seed)
        if fail_on is not None and len(calls) == fail_on:
            raise RuntimeError("sampler exploded")
        draws = {name: np.full(n_samples, float(closure(module).detach().reshape(-1)[0]))
                 for name, module, _prior, closure, _ in model.named_priors()}
        return draws, _Diagnostics(n_samples)

    curves = practice_run.generate_demo_data(n_subjects=1, seed=3)
    kw = dict(prior_configs=["practitioner", "moderate"], mode="hmc", verbose=False,
              n_hmc_samples=6, n_warmup=2, n_eval=8, n_posterior_samples=4,
              taus=np.array([0.5, 1.0]))

    monkeypatch.setattr(practice_run, "fit_hmc",
                        lambda *a, **k: fake_fit_hmc(*a, fail_on=2, **k))
    with pytest.raises(RuntimeError, match=r"\[moderate\]: HMC fit or predictive extraction failed"):
        practice_run.run_all(curves, tmp_path / "strict", seed=7, strict=True, **kw)

    calls.clear()
    lenient = practice_run.run_all(curves, tmp_path / "lenient", seed=7, strict=False, **kw)
    assert set(lenient[0].bistar_probs) == {"practitioner"}
    assert "sampler exploded" in lenient[0].sampler_records["moderate"]["failed"]

    calls.clear()
    monkeypatch.setattr(practice_run, "fit_hmc", lambda *a, **k: fake_fit_hmc(*a, **k))
    practice_run.run_all(curves, tmp_path / "ok", seed=7, strict=True, **kw)
    assert calls == [7, 7]
    (path,) = (tmp_path / "ok").glob("synth_*.json")
    record = json.loads(path.read_text())
    assert record["seed"] == 7 and record["strict"] is True
    for cfg in ("practitioner", "moderate"):
        rec = record["sampler_records"][cfg]
        assert (rec["n_draws_requested"], rec["n_draws_returned"]) == (6, 6)
        assert (rec["n_predictives_requested"], rec["n_predictives_retained"]) == (4, 4)
        assert rec["n_predictives_dropped"] == 0 and rec["seed"] == 7
        assert rec["sampler_diagnostics"] == {"sampler": "stub", "n_draws": 6}
    with np.load(path.with_name(path.stem + "_samples.npz")) as z:
        assert "practitioner/likelihood.noise_covar.noise_prior" in z.files
        assert len(z["moderate/retained_indices"]) == 4


# ── optional items (run because the ten above are green) ────────────

def _recording_axes():
    """Axes stand-in that records fill_between and plot calls."""
    calls = {"bands": [], "lines": []}

    def fill_between(x, lo, hi, **k):
        calls["bands"].append((np.asarray(lo), np.asarray(hi), k.get("label")))

    def plot(x, yv, **k):
        calls["lines"].append((np.asarray(yv), k.get("label")))

    ax = SimpleNamespace(fill_between=fill_between, plot=plot, scatter=lambda *a, **k: None,
                         set_xlabel=lambda *a, **k: None, set_ylabel=lambda *a, **k: None,
                         set_title=lambda *a, **k: None, legend=lambda *a, **k: None)
    return ax, calls


def test_optional_a5_plots_mixture_intervals_and_labelled_traces(toy):
    from bistar_gp import viz
    from bistar_gp.debias import decompose_model

    model, lik, x, y, x_eval = toy
    res = decompose_model_hmc(model, lik, x, y, x_eval,
                              _toy_samples([0.7, 3.0], [1.5, 0.4], [0.05, 0.2], [0.1, 0.3]),
                              kernel_builder=build_toy_kernels, n_posterior_samples=2,
                              rng=np.random.default_rng(0))
    ax, calls = _recording_axes()
    viz.plot_full_prediction(res, ax=ax, n_samples=5)
    (lo, hi, label), = calls["bands"]
    want_lo, want_hi = res.full.central_interval(0.95)
    assert label == "95% central interval"
    assert np.array_equal(lo, want_lo) and np.array_equal(hi, want_hi)
    traces = [(t, lab) for t, lab in calls["lines"] if lab != "Predicted mean"]
    assert len(traces) == 2 and traces[0][1] == "per-draw conditional means"
    assert all(np.array_equal(t, m) for (t, _), m in zip(traces, res.full.conditional_means))

    ax, calls = _recording_axes()
    name = list(res.components)[0]
    viz.plot_component(res, name, ax=ax)
    (lo, hi, label), = calls["bands"]
    assert label == "95% central interval"
    assert np.array_equal(lo, res.components[name].central_interval(0.95)[0])
    assert calls["lines"][0][1] == "per-draw conditional means"

    # MAP path: joint draws from the full posterior, not sums of separately
    # drawn component samples (which lose the cross-covariance)
    res_map = decompose_model(model, lik, x, y, x_eval)
    ax, calls = _recording_axes()
    viz.plot_full_prediction(res_map, ax=ax, n_samples=4000, seed=1)
    draws = np.array([t for t, lab in calls["lines"] if lab != "Predicted mean"])
    assert draws.shape == (4000, len(x_eval))
    assert np.allclose(draws.var(axis=0), np.diag(res_map.full.cov), rtol=0.15, atol=1e-6)


def test_optional_a7_rank_aggregation_is_permutation_symmetric():
    from bistar_gp.aggregation_v3 import robust_rank

    tied = robust_rank(np.zeros((3, 2)), ["a", "b"])
    assert list(tied.posteriors) == [0.5, 0.5]                # was 0.731 / 0.269 by column order
    G = np.array([[0.0, 0.0, 1.0], [2.0, 0.0, 0.0], [1.0, 1.0, 1.0], [0.5, 0.2, 0.9]])
    ref = robust_rank(G, ["a", "b", "c"])
    for perm in ([2, 0, 1], [1, 0, 2]):
        out = robust_rank(G[:, perm], [["a", "b", "c"][j] for j in perm])
        assert np.allclose(out.posteriors, ref.posteriors[perm], rtol=0, atol=1e-15)
        assert np.array_equal(out.summary_values, ref.summary_values[perm])
```
