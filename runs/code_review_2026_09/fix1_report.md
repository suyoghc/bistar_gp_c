# Fix pass 1 report (code review 2026-09)

- Worktree: `/Users/sc8918/Documents/GitHub/bistar_gp_c-fix`, branch `fix/code-review-2026-09` from `71540836`.
- Dispatch: `docs/paper-sie-jmp/prompts/code-review-fix1.txt`. Implementer: Fable (Claude), 2026-09-07.
- Git operations performed by the implementer: none (the one worktree-creation command was the driver-authorized exception; no add, commit, stash, checkout, or status was run). The driver runs `git status --short` in the worktree as the file-set check.
- Uncommitted. The driver commits after review.

## Files touched (all inside the editable set)

Package (edited): `bistar_gp/model.py`, `bms_star.py`, `aggregation_v3.py`, `debias.py`, `decompose.py`, `metrics_v2.py`, `laplace_evidence.py`, `induced_prior.py`, `candidates.py`, `config.py`, `__init__.py`. Package (new): `bistar_gp/external_targets.py` (FIX-8 names a new module as the intended form).
Experiments (edited): `bistar_debias_mauna_loa.py`, `bistar_induced_prior.py`, `bistar_induced_prior_v2.py`, `prior_sensitivity_study.py`.
Tests (new, nine files, 79 tests): `tests/test_fix1_sites.py` (9), `test_fix1_decomposition.py` (10), `test_fix1_diagnostics.py` (6), `test_fix1_metrics_firewall.py` (6), `test_fix1_sentinels.py` (6), `test_fix1_weighting.py` (11), `test_fix1_roles.py` (6), `test_fix1_external_targets.py` (6), `test_fix1_conventions.py` (19).
A `diff -rq` of `bistar_gp/`, `tests/`, `experiments/` against the main worktree lists exactly these files. Nothing under `runs/`, `docs/`, `Notes/`, `docs/m2c_freeze/`, `experiments/practice_EvansEtAL/`, or the poster directories was written.

## FIX-by-FIX

### FIX-1 site names and draw integrity
- `model.py` `select_hmc_sites`: when no `covar_module.kernels.` key exists, falls back to keys starting with `covar_module.` (single-kernel naming), then to the legacy `kernel_components.` names. `apply_hp_value`: new `covar_module.<...>` branch, accepted only when the model has exactly one kernel component and `model.covar_module` is that component; otherwise returns False.
- `bms_star.py` `extract_gp_predictives(..., rng=None, strict=True)`: raises ValueError when no kernel site is recognized, when a site is unrecognized, or when applying a site fails, and RuntimeError when a draw fails; `strict=False` warns and drops instead. `hp_dict` records only applied values. Returns `PredictiveList` (a `list` subclass carrying `attempted_indices`, `retained_indices`, `dropped`, `n_dropped`; behaves as the plain list it replaces).
- `experiments/prior_sensitivity_study.py` `_sir_bms`: raises RuntimeError when the retained predictive count differs from the SIR draw count.
- Signature changes: `extract_gp_predictives` gains keyword-only-by-position `rng`, `strict`; return type is a list subclass. No call site in the editable set passes positional arguments beyond the old ones.

### FIX-2 decomposition moments, groups, intervals
- `debias.py` (rewritten). `ComponentResult` gains `samples_kind`, `conditional_means`, `conditional_vars`, `within_var_mean`, `between_var`, `n_draws` (all optional, defaulted) and `central_interval(mass=0.95)`. `DecompositionResult` keeps exactly the seven pinned fields (`tests/test_poster_d58_driver.py` positional contract) and attaches `full`, `groups`, `n_draws_attempted`, `n_draws_retained` as non-field attributes in `__post_init__`; adds `group_key(names)` and `group(names)` (empty group is zero, singleton is the component, all components is the full posterior, a requested group is its stored joint summary, anything else raises KeyError "not requested"). `_DrawAccumulator`: one Cholesky of the entire training covariance plus noise per draw serves every component, the full posterior and every requested group (never a group-only factorization); total covariance = mean of conditional covariances + covariance of conditional means; `std` = sqrt(within + between); `samples` holds the conditional means on draw paths (`samples_kind="conditional_means"`).
- `decompose_model(..., groups=None)`: MAP values unchanged; requested groups are the summed group blocks conditioned with the full-kernel factor; sets `result.full`, `result.groups`.
- `decompose_model_mcmc(..., n_posterior_samples=100, jitter=1e-4, groups=None, rng=None)`: name-matched raw parameter values (`_raw_parameter_map`, deduplicated by identity), KeyError on unknown keys.
- `decompose_model_hmc(..., n_posterior_samples=200, jitter=1e-4, groups=None, strict=True, rng=None)`: `select_hmc_sites` / `apply_hp_value` with a strict raise; kernel_builder names must equal `model.component_names`; records `result.dropped`.
- `decompose.py`: `mixture_central_interval(mean_draws, var_draws, mass=0.95, n_iter=100)` ported from the Case E script (CDF bisection over the equally weighted Gaussian mixture; ValueError on shape mismatch or mass outside (0, 1)). The Case E script is untouched.
- `experiments/bistar_debias_mauna_loa.py`: `compute_debiased(result, truth_components, bias_components, mass=0.95)` reads `result.group(...)` for both sets and returns the joint mean, the total sd, and the mixture central interval bounds (`truth_lo/hi`, `bias_lo/hi`, `interval_mass`, `n_draws`); the `sum of comp.std**2` construction is gone; raises KeyError with guidance when the groups were not requested. New `INTERPRETATION_GROUPS` constant; the two decomposition calls in `main` pass `groups=INTERPRETATION_GROUPS` (see deviations). No figure regenerated.
- Signature changes and call sites: `decompose_model`, `decompose_model_mcmc`, `decompose_model_hmc` gain trailing keywords (existing positional patterns unchanged); `compute_debiased` gains `mass`; its three plotting call sites keep working (the returned dict keeps `truth_mean`, `truth_std`, `bias_mean`, `bias_std`).

### FIX-3 diagnostics and the package surface
- `bms_star.py`: `boltzmann_weight_ess(G, tau)` (exp(2 logsumexp(lw) - logsumexp(2 lw)), lw = -G/tau, per candidate); `hard_win_statistics(G)` (exact ties: split credit summing to one, attainment, tie fraction). `BMSStarResult` gains optional `weight_ess`, `hard_win_credit`, `attainment`, `tie_fraction`. `soft_transfer(G, tau, instance_names, class_names=None, normalize_per_draw=False, metric_name=None)` records the metric name ("unspecified" when None), computes the ESS on the effective G and the win statistics on G; grouped `class_names` (class-level averaging) now raise ValueError. `run_bms_star` passes `metric_name`.
- Canonical pooled arithmetic and the `normalize_per_draw=False` default are unchanged (pinned in `test_fix1_conventions.py`).

### FIX-4 Hellinger exponents and the universe firewall
- `metrics_v2.py`: `pw_hellinger_vcal` uses (mu_p - mu_q)^2 / (8 var_p) and `pw_hellinger_mean` uses (mu_p - mu_q)^2 / 8 (both were /4); docstrings corrected. N(0,1) vs N(1,1) now gives 1 - exp(-1/8) for both, matching `pw_hellinger`.
- `bms_star.py` `compute_G_matrix`: calls `_assert_candidate_universes_consistent` before any metric call; message begins "compute_G_matrix/run_bms_star received candidates spanning multiple universes or a mix of tagged and untagged results".
- `aggregation_v3.py`: `score_averaged_gp` (which never builds a G matrix) calls the guard explicitly; `compute_log_marginal_likelihoods` raises ValueError when `apply_hp_value` returns False.

### FIX-5 numerical failure sentinels
- `laplace_evidence.py`: `compute_G_at_params(..., strict=True)` and `_log_likelihood(..., strict=True)` raise RuntimeError (NaN when `strict=False`) instead of the 1e6 and -1e10 sentinels. `OptimizerRecord` dataclass (`success`, `status`, `message`, `nit`, `nfev`, `exception`, `as_dict()`), `_optimizer_record(res)`. `_laplace_log_integral` returns a 7-tuple `(log_integral, x_star, f_star, logdet, converged, n_clipped, record)` and returns NaN early on a non-finite `f_star`. `ZMxResult` and `EvidenceResult` gain `optimizer`, `n_starts_failed`; `ModelPosteriorResult.all_converged`; `ZMxSweepResult` gains `n_starts_failed`, `optimizer_records`. `strict=True` keyword added to `laplace_log_Z_Mx`, `mc_log_Z_Mx`, `is_log_Z_Mx`, `laplace_log_evidence_ordinary`, `laplace_log_evidence_induced`, `model_posterior`, `model_posterior_tau_sweep`, `_G_of_matrix`, `_laplace_log_N`. `_multistart_G_optima(..., eps=1e-4, strict=True)` returns 5-tuples with the record and uses an identity Hessian when the numerical Hessian is non-finite. `model_posterior` components carry `converged`, `n_clipped`, `n_starts_failed`, log a warning on failure, and set `all_converged`.
- `candidates.py`: `_fit_mle(self, x, y, f_predict, p0, bounds=None, return_status=False)` returns `(params, nll, status)` on request; `_select_restart(candidates, model_name)` prefers successful restarts and warns otherwise; Linear and Quadratic warn on non-success; Sinusoidal and SinLinear use `_select_restart`.
- `induced_prior.py`: failed-draw penalty is `max_finite + 10 (|max_finite| + 1)`, strictly worse than every finite value also for negative-valued metrics (the old `10 * max` was the best score under pw_nll).
- All new keywords are trailing and defaulted; no call site needed updating. The 7-tuple return of `_laplace_log_integral` and the 5-tuples of `_multistart_G_optima` are internal; every internal unpacking site in `laplace_evidence.py` was updated.

### FIX-6 weighted aggregation and posterior weighting
- `aggregation_v3.py` `soft_transfer_weighted`: forms `log w_i - G_ij / tau` and aggregates with log-sum-exp over draws; non-finite log weights are absent support; all-absent support raises ValueError; no uniform fallback. Result also carries the FIX-3 diagnostics. `average_gp_posterior` raises ValueError naming the offending draw on a non-finite mean or covariance diagonal.
- `induced_prior.py` `compute_induced_prior(param_space, gp_samples, x_eval, log_mlls=None, metric_name="pw_kl_vcal", tau=1.0, n_param_samples=10000, seed=42, weighting="uniform")`: `log_mlls` is optional; `weighting="uniform"` (default) is documented as the correct average for posterior draws and ignores `log_mlls` with a warning; `weighting="likelihood_tilted"` is the explicit MLL path (requires `log_mlls`); unknown values raise.
- Callers updated: `experiments/bistar_induced_prior.py` (two call sites, lines 166 and 281) and `experiments/bistar_induced_prior_v2.py` (line 172) now pass `weighting="uniform"` for the `fit_hmc` caches instead of `log_mlls=log_mlls`.
- Signature change: `log_mlls` moved from required positional to optional keyword in the same position; a legacy positional call still works.

### FIX-7 reporting roles and withdrawn caches
- `config.py`: `PRIMARY_METRIC = "pw_kl_vcal"`, `APPENDIX_METRICS = ("kl_forward",)`; `ExperimentConfig.metrics` keeps its ten legacy entries in order and appends the primary metric (appended rather than prepended so `experiments/bms_star_toy.py`'s `config.metrics[:4]` slice keeps its meaning). `WITHDRAWN_CACHES = ("runs/fit_method_metric_comparison/samples_hmc.npz", "runs/toy_tau_metric_comparison/")`, `is_withdrawn_cache(path)`, `load_hmc_samples(path, allow_withdrawn=False)` raises RuntimeError citing the M2bR banner and warns (UserWarning) under the flag.
- `bms_star.py` `run_bms_star`: logs a warning naming the appendix metric(s) and the primary metric when it scores an appendix metric on the implicit `metric_names=None` path only. `_resolve_metric(name)` registers `metrics_v2` on demand inside `compute_G_matrix`, so the primary metric named by the config resolves for callers that never imported `metrics_v2` (bms_star_toy.py hands the config list straight to `run_bms_star`); registered names resolve exactly as before.
- The untracked local figure scripts that read the withdrawn caches were not edited.

### FIX-8 external targets
- `bistar_gp/external_targets.py` (new): `VANBORK_TARGET_A`, `VANBORK_TARGET_B_PRIORS`, `VANBORK_TARGET_B_PSI`, `vanbork_target_b_densities()`, `vanbork_target_b_weight()`, `vanbork_target_b()`, `external_target_errors(results)`, `check_external_targets(results_json_path, tol_a=1e-6, tol_b=1e-5, stored_field_tol=1e-9)`. The checker selects the smallest-tau row of each target, checks the model names and unit mass, recomputes both errors from the rows, and cross-checks the stored `abs_error_at_min_tau` field. On the driver's fixture it reproduces the stored errors exactly (A = 0.0, B = 6.404745348520535e-07). Wiring into the case-A script is fix pass 2.

### FIX-9 aggregation conventions
- `bms_star.py` `aggregate_convention(G, tau, variant)` with `pooled`, `rowmin`, `expected_posterior`; imported into `aggregation_v3.py` and exported from `bistar_gp`. Bit-identical to the Case A script's `aggregate` (checked against the driver's fixture file and against a verbatim copy of the pre-fix `_boltzmann_posterior` arithmetic).
- `experiments/prior_sensitivity_study.py` `_boltzmann_posterior` delegates to `aggregate_convention(G, tau, "pooled")`.

### `bistar_gp/__init__.py`
Exports `mixture_central_interval`, `aggregate_convention`, `boltzmann_weight_ess`, `hard_win_statistics`, `PredictiveList`.

## Verification

1. Full suite, run 1 (`python -m pytest tests/ -q -p no:cacheprovider`, before the final FIX-7 list-order edit and the fixture-path edit in two test files): 1326 passed, 3 skipped, 1 failed, 494.83 s (8 min 14 s). The failure is the known `tests/test_m2cr_environment_freeze.py::test_committed_dependency_lock_reproduces_at_head` (dependency-lock drift). Log: scratchpad `fixpass1/full_suite_run1.log`.
2. Full suite, run 2 (final file state, with `-rs`): 1327 passed, 3 skipped, 1 failed, 535.80 s (8 min 55 s). The failure is again `tests/test_m2cr_environment_freeze.py::test_committed_dependency_lock_reproduces_at_head` (known dependency-lock drift; the lock was not modified). The three skips are pre-existing and environmental: `test_e1_potential.py:652` (period only exists in the Mauna structure), `test_m2cr_environment_freeze.py:624` (M2CR_FULL_FREEZE_TESTS unset), `test_prior_sensitivity_figures.py:169` (machine-local study artifacts absent). Log: scratchpad `fixpass1/full_suite_run2.log`. Total collected 1331 = 1253 pre-existing + 79 new (run 1 collected 1330 because one roles test was added after it started).
3. Case E regression oracle: `toy_debias_demo.py --out <scratch>/fixpass1/toy_debias_demo`, 61 s, against the fix worktree's package (resolved path printed: `/Users/sc8918/Documents/GitHub/bistar_gp_c-fix/bistar_gp`). All three outputs byte-identical to the committed `runs/toy_debias_demo/` files:
   - results.json 65c9ff5f14b9a5f3aca8267745d6b368d95b831e85a610f6844b74e1b33712bb
   - debias_figure.png c1153549ca55d9d644804790ef9a4627f8d82bedd157ec348ecb519f551a4723
   - README.md 7096cd6e4d3d02f8971cee294fa3e50a2c7248272320e9cc72cfc45994f889af
4. The two fixture-backed tests (`test_driver_fixture_passes`, `test_matches_the_case_a_script_fixture`) pass with `FIX1_FIXTURE_DIR=<scratch>/fixpass1/fixtures` and skip without it.

## Refuted items confirmed NOT implemented
- No failure gate in E6.
- No finiteness "explanation" of the `aggregation_v3.py:77` RuntimeWarnings.
- No change to `soft_transfer`'s canonical pooled arithmetic or to the `normalize_per_draw=False` default (D60); `test_fix1_conventions.py` pins `pooled` equal to `soft_transfer(normalize_per_draw=False)` posteriors and bit-identical to the pre-fix arithmetic.

## Deviations, each with its reason
1. `experiments/bistar_debias_mauna_loa.py`: besides the grouping function, the two decomposition calls in `main` now pass `groups=INTERPRETATION_GROUPS`, and that constant was added. Joint group moments need the summed kernel blocks at decomposition time, so the grouping function cannot work without the request.
2. Case E oracle location: `experiments/toy_debias_demo.py` exists only on `paper/case-e-debias`, not in the fix worktree (base `71540836`). The main worktree's copy was run from a scratch directory whose `bistar_gp` entry is a symlink to the fix worktree's package (the script inserts its own parent directory at `sys.path[0]`, so this is the only way to exercise the fixed package without writing into either worktree). Nothing was copied into a repository directory.
3. `_resolve_metric` (on-demand `metrics_v2` registration in `compute_G_matrix`) is not in the queue; it keeps `experiments/bms_star_toy.py` working after FIX-7a put `pw_kl_vcal` into `ExperimentConfig.metrics`.
4. FIX-7a appends the primary metric instead of leading with it, for the `metrics[:4]` reason above.
5. FIX-9 was placed in `bms_star.py` (the prompt's stated alternative) and re-exported through `aggregation_v3.py`.
6. The MLL path is named `weighting="likelihood_tilted"`, the prompt's example name.
7. Scratch outputs of the oracle and the first suite log were first written directly under the scratchpad and then moved under `fixpass1/`.
8. Run 2 of the suite started before the final edit of the two fixture-path tests; those two files were rerun separately (item 4 above).

## Corrections after the fix-pass review round (added 2026-09-07, Fable)

Recorded as an addendum; the sections above are left as written.

1. FIX-1 signature statement: `extract_gp_predictives` already had `rng=None` at the base commit `71540836` (read-only `git show` confirms it at bms_star.py:223 there). The new argument of this pass is `strict=True` only. (Codex fix-pass review, section 3.)
2. FIX-3 undisclosed deviation: the work order says `soft_transfer` requires `metric_name`; the pass made it optional (None recorded as "unspecified") and pinned that behaviour in `tests/test_fix1_diagnostics.py`. Reason not stated above: two package call sites outside the editable set omit the metric (`bistar_gp/metrics_v2.py:398`, `bistar_gp/mcse_strategy.py:177`), plus experiment scripts and the existing aggregation tests, so a required keyword would have needed edits the pass was not allowed to make. This is Codex finding R4 and needs an author disposition (required keyword with caller migration, or a documented legacy exception).
3. FIX-2 `samples` field: it was retained, not merely aliased, because the read-only poster driver writes `comp.samples` (`experiments/poster_d58_mauna.py:477`) and rebuilds with `samples=` (line 541). On draw paths it holds the per-draw conditional means, marked by `samples_kind`.
4. FIX-6 `instance_scores` scale: the joint log-space rewrite reports scores shifted by one global constant relative to the pre-fix scale (posteriors unchanged to 1e-16). No consumer of the absolute scale was found; the pre-fix scale is `exp(log_scores + G.min()/tau)` if it is wanted back.

## Fix pass 1b (added 2026-09-08, Fable): review-round folds

Applied in the same uncommitted worktree after the Codex and Fable 5.1
reviews (adjudication in `fix1_synthesis.md` revision 2). Developed on a
scratch copy while the Fable 5.1 reviewer read the worktree, then copied
back file-for-file; post-sync `diff -rq` between copy and worktree was
empty. Delta against the reviewed pass-1 state: `fix1_bundle/fix1b_delta.diff`.

Package changes (six files):
- `bms_star.py`: `log_weight_ess(log_w, axis=0)`, the one ESS routine
  (per-column max subtracted; NaN for NaN input, 0 for all-absent support);
  `boltzmann_weight_ess` delegates to it. `soft_transfer` validates a finite
  `G_matrix` at entry with its own message, checks `instance_names` length,
  and requires one class label per column with no repeats. `METRICS` is a
  `_MetricRegistry(dict)` whose `__missing__` imports `metrics_v2` on the
  first miss; `_resolve_metric` is gone.
- `aggregation_v3.py`: `compute_log_marginal_likelihoods` applies the sample
  sites before entering the numerical handler, so an unrecognized site
  escapes as ValueError. `soft_transfer_weighted` subtracts one global
  shift before both log-sum-exps, reports `instance_scores` on the pre-fix
  scale (`exp(log_scores + G.min()/tau)`), and uses `log_weight_ess`.
- `debias.py`: `_summarize` (one place that packages a `ComponentResult`)
  and `_single_draw_summary`; `_DrawAccumulator` conditions every target
  into a per-draw record and commits it whole, with typed tuple keys
  `("component", name)`, `("group", key)`, `("full",)`; `_validated_groups`
  shared by the MAP and draw paths; `group_key` deduplicates names;
  `_blocks_sum` uses `functools.reduce` so a single block is returned
  unchanged. MAP values unchanged (same floored variances, same sqrt).
- `laplace_evidence.py`: `EvaluationFailure(RuntimeError)` raised by
  `compute_G_at_params` and `_log_likelihood` under `strict=True` and
  re-raised by both optimizer handlers; under `strict=False` a metric
  `RuntimeError` or `FloatingPointError` also becomes NaN; `_select_start`
  chooses the minimum over finite objectives (NaN only when all are
  non-finite); a non-finite Hessian stencil returns NaN with `converged`
  False and the optimizer's record kept; `_weight_ess` delegates to
  `log_weight_ess`; `ModelPosteriorResult` documents the all-NaN semantics.
- `induced_prior.py`: `log_mlls` supplied under `weighting="uniform"` raises
  instead of warning.
- `external_targets.py`: the selected row's posteriors and any stored error
  field are validated finite before the mass check and the reductions.

Tests: `tests/test_fix1_review_round.py` (new, 17 tests: R1, R2, R3+F3,
R5, R6 x5, R7, R8 x2, R8(iii), R9, R10, F4, firewall counting metric);
`test_fix1_sentinels.py` (NaN ESS assertions, all-NaN posterior assertion,
uniform-weighting call), `test_fix1_weighting.py` (F2 conflict raise),
`test_fix1_conventions.py` (a supplied fixture that fails to import now
fails instead of skipping).

Public-behaviour changes beyond pass 1: `soft_transfer` raises on
non-finite G (pre-fix: uniform posterior; unreachable from
`compute_G_matrix`); `compute_induced_prior(..., log_mlls=...)` without
`weighting="likelihood_tilted"` raises; `EvaluationFailure` is a new public
exception (a `RuntimeError` subclass); `METRICS` is a dict subclass.

Verification: full suite in the fix worktree, plain run (no fixture variable): 1342 passed, 5 skipped, 1 failed, 466.06 s (7 min 46 s); the failure is the known `test_m2cr_environment_freeze.py::test_committed_dependency_lock_reproduces_at_head`; the skips are the two fixture-gated pins plus the three pre-existing environmental skips; collected 1348 = 1331 + 17 new. The two fixture-gated files pass with `FIX1_FIXTURE_DIR=<scratch>/fixpass1/fixtures` (run separately). Log: scratchpad `fixpass1/full_suite_1b_worktree.log`. Case E oracle against the synced
worktree package: byte-identical (65c9ff5f / c1153549 / 7096cd6e), 60.3 s.
Not changed: `metric_name` stays optional pending the author's R4/F5
disposition; docstring provenance prose was not trimmed.
