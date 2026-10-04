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
