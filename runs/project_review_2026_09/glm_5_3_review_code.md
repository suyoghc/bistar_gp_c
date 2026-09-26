# Project review 2026-09-26, code package — GLM 5.3 (package-only channel), 2026-09-26

*Driver note: produced by `z-ai/glm-5.3` via OpenRouter, prompt 91414 tokens, completion 11980 tokens, finish_reason `stop`, 59 s. Package: project-review brief + HANDOFF sections 2-3 + notation + section 02 + line-numbered sources of 11 modules at ddf8c9d. No text altered below this note.*

GLM 5.3 (package-only channel) — package-only review of ddf8c9d. No repository access and no execution; every claim below is either CONFIRMED by citation into the supplied listings or marked PLAUSIBLE, and execution- or repository-dependent claims carry NEEDS-REPO-VERIFICATION.

---

## 1. Verdict

**Code: REVISE** — the fix passes genuinely closed the named silent-wrong-answer classes (T2, T11 core, T8, aggregation arithmetic), but the W1/appendix metric discipline is still only convention at the public-primitive level (`compute_G_matrix` defaults to the appendix-only `kl_forward`), and the Ḡ plug-in surrogate (T1) is disclosed but uncharacterized, with at least one silent penalty-substitution path remaining on the induced-prior route.

**Project: NOT READY for submission.** Blocking list (all requiring repository access to close):
- B1. Every D58-poster and case-section band built from `decompose_model_hmc/mcmc` before FIX-2 is understated (the module docstring itself says "by an order of magnitude", bistar_gp/debias.py:5-10); whether every inheriting manuscript/poster statement has been re-marked is unverified. NEEDS-REPO-VERIFICATION.
- B2. The six unmerged case branches (PR #36-#41) were written against the pre-fix package API and will break or silently change under `strict=True` extraction, `compute_induced_prior` weighting, `soft_transfer_weighted` raising, and `PredictiveList`; no merge order has been executed. NEEDS-REPO-VERIFICATION.
- B3. The suite count (expected 1346 passed / 5 skipped / 1 failed, the dependency-lock drift test) could not be run here. NEEDS-REPO-VERIFICATION.
- B4. Section 01-08 number provenance (named experiments/ script to runs/ artifact per section) could not be checked beyond section 02, which is clean. NEEDS-REPO-VERIFICATION.

---

## 2. Code findings

| ID | Target / module | Sev | Status | Location | Claim |
|---|---|---|---|---|---|
| C1 | T6, bms_star | S3 | CONFIRMED | bistar_gp/bms_star.py:533 | `compute_G_matrix`'s public default metric is `kl_forward`, the W1 appendix-only metric |
| C2 | T11, bms_star | S3 | CONFIRMED (code) / PLAUSIBLE (reach) | bistar_gp/bms_star.py:560-573 | failed metric evaluations become a finite penalty indistinguishable from a poor fit |
| C3 | metrics | S3 | CONFIRMED (code) / PLAUSIBLE (impact) | bistar_gp/bms_star.py:27-50 | uncounted jitter escalation / eigenvalue floor silently alters joint-KL values |
| C4 | T6/T10, bms_star | S3 | CONFIRMED | bistar_gp/bms_star.py:763-784 | implicit `run_bms_star` roster is import-order dependent and still scores appendix metrics |
| C5 | T1, laplace_evidence | S2 | PLAUSIBLE | bistar_gp/laplace_evidence.py:148, aggregation_v3.py:91-104 | the Ḡ moment-matched surrogate is disclosed but unbounded/unchacterized |
| C6 | T4/T11, induced_prior | S3 | CONFIRMED | bistar_gp/induced_prior.py:246-273 | `compute_induced_prior` keeps the silent penalty substitution with no `strict` option |
| C7 | reproducibility | S4 | CONFIRMED | bms_star.py:331, debias.py:402, debias.py:447 | legacy global-`np.random` draw selection paths |
| C8 | debias | S4 | CONFIRMED | bistar_gp/debias.py:407-410 | `decompose_model_mcmc` mutates the caller's model in place |
| C9 | debias | S4 | CONFIRMED | bistar_gp/debias.py:461, 518 | `noise_var` in the result is the last retained draw's noise, not a summary |
| C10 | T7, config | S3 | PLAUSIBLE | bistar_gp/config.py:253-273 | withdrawn-cache guard exists only on `load_hmc_samples`; direct `np.load` bypasses it |
| C11 | T5, config | S4 | CONFIRMED | bistar_gp/config.py:200 | `n_eval=60` grid choice undocumented as a choice |
| C12 | aggregation_v3 | S4 | CONFIRMED | bistar_gp/aggregation_v3.py:253-255 | `robust_rank` uses double-argsort, first-argmin tie bias |
| C13 | induced_prior | S4 | CONFIRMED | bistar_gp/induced_prior.py:318 | `log_weights` carries a dual meaning (shifted + `log(total)`) |

### Detail

**C1 (S3, T6).** `compute_G_matrix(gp_samples, candidate_results, metric_name="kl_forward")` — bistar_gp/bms_star.py:533. W1 (config.py:24-25) makes `kl_forward` appendix-only, yet the public primitive's default is exactly that metric; a caller omitting `metric_name` scores the appendix metric with no warning anywhere (the run_bms_star warning at bms_star.py:770-784 fires only on the implicit-roster path, and `metrics_v2.plot_v2_tau_sensitivity` calls `soft_transfer(G, tau, instance_names)` without a metric name, metrics_v2.py:398, recording "unspecified"). Reproduction: any call `compute_G_matrix(ps, crs)` in a case script computes the W1-appendix divergence silently. Suggested change: default to `PRIMARY_METRIC` (importing config or a sentinel that resolves to it), or raise when `metric_name` is omitted in manuscript-facing entry points. Pin: a test calling `compute_G_matrix` with no metric and asserting the result equals the `pw_kl_vcal` matrix (or that it raises).

**C2 (S3, T11 residual).** In `compute_G_matrix`, a metric raising `LinAlgError/ValueError` sets `G[i,j]=inf` (bms_star.py:560-561), then every non-finite entry is replaced by `penalty = max_finite + 10(|max_finite|+1)` (bms_star.py:568-573). The penalty construction is now correct for negative-valued metrics (verified: `max + 10(|max|+1) > max` always), but the substitution itself remains: a candidate whose evaluation fails on every draw receives a finite plausible "extremely poor fit" score rather than an error, and nothing in the returned matrix marks it. Failure scenario: a candidate `predict_fn` that raises `ValueError` under this metric scores `penalty` on all rows and gets posterior ≈ 0 with `weight_ess` finite — indistinguishable from a genuinely terrible model. Suggested change: return a parallel boolean failure mask (or raise in a strict mode) so a paper-facing caller can assert zero failures. Pin: test that a raising metric on one candidate either raises or is reportable as failed, never silently finite.

**C3 (S3).** `_safe_logdet`/`_safe_solve` escalate jitter over [0, 1e-10, 1e-8, 1e-6, 1e-4] and finally floor eigenvalues at 1e-10 (bms_star.py:27-50), silently changing `kl_forward`/`hellinger` values with no counter recorded. This is exactly the "jitter escalation that is not counted" class of the review standard; the affected metrics are appendix-only, so severity is capped at S3, but any appendix `kl_forward` magnitude in τ ∈ [0.1, 100] could carry silent regularization. Pin: a test that a near-singular covariance produces a logged/recorded jitter count.

**C4 (S3, T6/T10).** With `metric_names=None`, `run_bms_star` uses `list(METRICS.keys())` (bms_star.py:765), which is import-order dependent by construction (the `_MetricRegistry.__missing__` docstring, bms_star.py:194-200, admits v2 names appear only after first import), and the appendix metric is still computed and stored in `results`, only announced. Reproduction: the same script with and without a prior `import bistar_gp.metrics_v2` produces different result dicts. Suggested change: on the implicit path, drop `APPENDIX_METRICS` from the roster (or gate them behind an explicit flag). Pin: test that implicit `run_bms_star` results contain no `kl_forward` key, or that the roster is import-order invariant.

**C5 (S2, T1).** The Ḡ surrogate is exactly as described: `compute_G_at_params` evaluates the metric once against `avg_gp.mean, avg_gp.cov` (laplace_evidence.py:148), and `average_gp_posterior` forms the moment-matched mixture (aggregation_v3.py:91-104). Section 02 discloses the plug-in surrogate and its non-consistency, so claim fidelity holds for the machinery section; what remains open is (a) no bound or error characterization of the surrogate exists in the supplied code, and (b) whether any committed Z_M / model-probability ordering depends on the surrogate gap — the section itself states the discrepancy "does not cancel from a normalized comparison across candidates". NEEDS-REPO-VERIFICATION for which committed numbers inherit it. The driver's RuntimeWarning observation at aggregation_v3.py:77 is fixed at this head: non-finite means and covariance diagonals now raise before the weighted products (aggregation_v3.py:83-90), so a reported number cannot be reached by non-finite means. Suggested change (pass 2): add a diagnostic comparing the moment-matched G to the per-draw mean G at the MAP point, reported next to every Z_M.

**C6 (S3, T4/T11).** `compute_induced_prior` retains the pre-fix silent-substitution pattern: a raising `predict_fn` sets `np.inf` (induced_prior.py:246-249), failed draws get the penalty (induced_prior.py:268-273), and there is no `strict` option, unlike the laplace path. The FIX-6 weighting change (raise on `log_mlls` under `weighting="uniform"`, induced_prior.py:208-216) is correct and enforced. Suggested change: port the `strict` contract from `compute_G_at_params`.

**C7 (S4).** `extract_gp_predictives` (bms_star.py:328-331), `decompose_model_mcmc` (debias.py:399-402) and `decompose_model_hmc` (debias.py:444-447) retain the `rng=None` legacy path through the global numpy RNG. A run artifact regenerated by a script that does not pass `rng` or seed globally will not reproduce. NEEDS-REPO-VERIFICATION whether the paper-facing scripts pass `rng`/seed.

**C8/C9 (S4).** `decompose_model_mcmc` writes draw values into the caller's live parameters (`p.data.fill_`, debias.py:408-409) leaving the model at the last draw; and `decompose_model_hmc` reports `noise_var = last_noise`, the last successful draw's noise (debias.py:461, 498, 518), while noise varies per draw — a scalar summary with no spread diagnostic.

**C10 (S3, T7).** The withdrawn-cache guard is real and correct (config.py:31-46 path logic verified, including the directory-prefix case; config.py:262-269 raises unless `allow_withdrawn=True`). But it guards only `load_hmc_samples`; any script reading `runs/fit_method_metric_comparison/samples_hmc.npz` with `np.load` directly bypasses it. Whether any experiments/ script does so: NEEDS-REPO-VERIFICATION.

**C11 (S4, T5).** `n_eval: int = 60` (config.py:200) remains an undocumented default; no supplied code records the grid choice next to a reported pointwise divergence. Sensitivity of conclusions to it: NEEDS-REPO-VERIFICATION.

**C12 (S4).** `robust_rank` (aggregation_v3.py:253-255) uses double argsort, which awards ties to the first candidate — precisely the bias `hard_win_statistics` documents and avoids (bms_star.py:517). Not on the manuscript path (robust aggregation is a diagnostic strategy), but inconsistent with the fixed tie discipline.

**C13 (S4).** `log_weights=log_weights + np.log(total)` (induced_prior.py:318) returns unnormalized log weights after having shifted them internally; the dataclass docstring says "log induced prior weight per sample", which a caller could read as normalized. Same "dual meaning" seam class as the deferred `metric_name`.

### Named-target dispositions not already covered

- **T2 — CONFIRMED FIXED at this head.** `decompose_model_hmc`/`decompose_model_mcmc` now accumulate per-draw conditional moments via `_DrawAccumulator` (debias.py:195-263) and report law-of-total-variance moments in `_summarize` (debias.py:146-163): `std = sqrt(E_d[var_d] + Var_d[mean_d])`, cov = `E_d[C_d] + Cov_d[m_d]` with `bias=True` population covariance (debias.py:251) — mathematically correct. Group moments condition summed blocks with the full-kernel Cholesky (debias.py:227-233), so an all-component group reproduces the full posterior exactly. The `decompose_model` MAP wrapper computes the full posterior covariance from summed blocks including cross-terms (debias.py:318-331). The FIX-2 inheritance question (which poster/manuscript bands were understated and are marked) is P1/B1, NEEDS-REPO-VERIFICATION.
- **T3 — CONFIRMED CORRECT.** The global-shift argument at bms_star.py:639-644 is right: `log_weights.max()` is one scalar over the whole matrix, so `weights.mean(axis=0)` and its normalization carry a common factor that cancels exactly in `instance_scores / total`; a per-row max would not cancel (it is applied before the draw mean) and would reweight draws. `aggregate_convention`'s pooled branch uses the same global `lw.max()` (bms_star.py:712). `normalize_per_draw=False` remains the shipped default on `run_bms_star` (bms_star.py:752) per D60.
- **T4 — largely addressed, residual open.** `weight_ess` per candidate is computed on the weights actually aggregated (bms_star.py:660; `boltzmann_weight_ess`, bms_star.py:494-506, column-shift invariant), and `compute_induced_prior` now defaults to `uniform` with a raise on legacy likelihood weighting of posterior draws (induced_prior.py:208-216) — the double-counting estimator is gone. Whether committed artifacts report `weight_ess`: NEEDS-REPO-VERIFICATION.
- **T8 — CONFIRMED CLEAN at the primitive boundary.** `compute_G_matrix` calls the firewall (bms_star.py:549), as do `run_bms_star` (bms_star.py:786) and `score_averaged_gp` (aggregation_v3.py:130). `soft_transfer` and `soft_transfer_weighted` take pre-built G matrices and appropriately do not re-check; both entry points that build G from candidates are guarded. A fully-untagged roster passes by documented design (legacy/toy); a mixed or multi-tag roster raises (bms_star.py:737-745).
- **T9 — NEEDS-REPO-VERIFICATION.** `experiments/toy_debias_demo.py` is not in the package. The mixture-interval construction it contributed is present as `mixture_central_interval` (decompose.py:125-160) and is correct: bisection on the exact mixture CDF via `ndtr`, variance floored at 1e-24, mass validated strictly in (0,1). The AST guard, hyperparameter-site raise, and jitter probe cannot be audited here — PLAUSIBLE, unverified.
- **T10 — NEEDS-REPO-VERIFICATION** for test content (names only supplied). From the names, the fix-pass surfaces are covered (`test_fix1_*`, `test_decompose`, `test_bms_star_universe_firewall`, `test_laplace_zmx`); whether any test pins C1, C2's failure-mask absence, or the T1 surrogate gap is unverifiable. Claims I can see no test name obviously protecting: the W1 default of `compute_G_matrix` (C1) and the withdrawn-cache bypass outside `load_hmc_samples` (C10).
- **T11 — largely CONFIRMED FIXED.** The 1e6 sentinels are gone: `compute_G_at_params` raises `EvaluationFailure` under strict (laplace_evidence.py:133-154) or returns NaN that propagates through integrals and ESS by design; `_log_likelihood` raises/NaN (laplace_evidence.py:309-325); the Laplace optimizer fallback now records `converged=False` and an `OptimizerRecord` (laplace_evidence.py:353-358), `EvaluationFailure` re-raises and can never become a start-point expansion (laplace_evidence.py:348-352, 609-610); `_select_start` is order-independent over NaN starts (laplace_evidence.py:491-502); `model_posterior` aggregates `all_converged` and warns (laplace_evidence.py:841-845). Residuals: C2/C6 penalty substitution, and `ablation_ladder_posteriors`'s inner calls omit `strict` (laplace_evidence.py:1184-1193) so they inherit the module default `strict=True` — fine, but the omission makes the contract implicit (S4).

---

## 3. Project findings

| ID | Item | Sev | Status | Location | Claim |
|---|---|---|---|---|---|
| P-A | P1 | BLOCKER | NEEDS-REPO-VERIFICATION | case sections 01-08, D58 poster | FIX-2-inheriting band statements unverified as marked |
| P-B | P2 | MAJOR | PLAUSIBLE | PR #36-#41 vs ddf8c9d | case scripts break under the fixed package API |
| P-C | P1 (sec 02) | MINOR | CONFIRMED | tex/sections/02-machinery.tex | section 02 is consistent with the fixed code |
| P-D | P3 | MAJOR | PLAUSIBLE | Notes/DECISIONS.md D59-D68 | D-entry status vs code unverifiable except D60, D5, W1, M2bR |
| P-E | P4 | MAJOR | NEEDS-REPO-VERIFICATION | tests/ | suite value, known failure, fixture skips unverifiable |
| P-F | P5 | MAJOR | NEEDS-REPO-VERIFICATION | runs/ | artifact-vs-script regeneration unverifiable; C7 is a concrete regeneration risk |
| P-G | P6 | — | — | — | see §5 |

**P-C (P1, section 02, CONFIRMED clean).** Every machinery claim I can check against the listings holds: the plug-in-surrogate disclosure matches `average_gp_posterior`/`compute_G_at_params` exactly; the shared-scalar-variance coincidence claim matches `pw_kl_vcal`'s definition (metrics_v2.py:43-55, the variance factors out of the argmin); the three aggregation conventions match `aggregate_convention` (bms_star.py:679-715) including the pooled/rowmin/expected-posterior arithmetic and the D60 pooled-canonical default; the monotonicity Remark needs only reachable-set containment, which the code never contradicts; the scale-invariance warning and tau-free draw-win fractions match `hard_win_statistics` (bms_star.py:509-528) with the explicit tie rule the section's invariance claim requires; the occam reference-measure position matches the module-wide single-meaning convention (laplace_evidence.py:166-174) and the Laplace-vs-MC sign asymmetry (laplace_evidence.py:508-513, 650-652). The M2bR banner sentence ("no informative-configuration HMC result enters the account here") is enforced by the `load_hmc_samples` guard at the loader level. Section 02 cites no number I can falsify from the package.

**P-B (P2, merge plan).** The package at ddf8c9d changed its contract relative to what the case branches were written against: strict extraction raises where scripts once relied on dropped draws (bms_star.py:292-298, debias.py:432-434); `compute_induced_prior` raises on legacy `log_mlls` positional calls (induced_prior.py:208-216); `soft_transfer_weighted` raises on non-finite G (aggregation_v3.py:413-424); `PredictiveList` replaces the plain list (bms_star.py:237-255 — a list subclass, so mostly source-compatible); `DecompositionResult.group` requires groups requested at decomposition time (debias.py:102-134) — a case script calling `.group([...])` post hoc on an old result will `KeyError`. `aggregate_convention` moved into the package "from the Case A script" (bms_star.py:680-684), which means the Case A branch and the fix branch both define it — a guaranteed merge conflict, and the A-before-C dependency the brief names. **Merge order I would use:** (1) merge the fix branch to `main` (it is a fast-forward of main plus fix passes; it is the API authority); (2) rebase PR #36 (Case A / vanbork) first, resolving `aggregate_convention` in favor of the package copy and deleting the script-local one; (3) then the branches that import from Case A (Case C per the dependency), then B, D, E, F in any order, re-running each case script against the fixed package and re-checking each section's numbers; (4) reconcile D59-D67 (paper branches) with D68 (fix branch) in Notes/DECISIONS.md as the final merge. Conflicts/breakages I can demonstrate from the package alone: the `aggregate_convention` duplication (cited above) and the four API raises listed. Actual script-by-script breakage: NEEDS-REPO-VERIFICATION.

**P-D (P3).** Verifiable from the package: D60 pooled-canonical is enforced by the default `normalize_per_draw=False` (bms_star.py:752); the D5/D3/D17 occam single-meaning convention is enforced and self-consistent across the Laplace, MC and IS paths (verified above); W1 is enforced at `run_bms_star`'s implicit path only by a warning, and not at `compute_G_matrix` (C1) — so the D-entry status "W1 enforced in code" would be overstated; the M2bR banner is enforced at one loader (C10). D59-D67 content, the open ledger, and the pass-2 list: NEEDS-REPO-VERIFICATION.

**P-E (P4).** Cannot run or open the 67 test files. The known failure (dependency-lock drift) and the fixture-gated skips: NEEDS-REPO-VERIFICATION. From names alone, the fix-pass tests exist and are plausibly implementation-coupled (e.g. `test_m2c_freeze_*` constants tests are golden-value pins, valuable against silent change but blind to wrong constants).

**P-F (P5).** Concrete regeneration risk demonstrable from the package: the legacy global-RNG paths (C7) mean any runs/ artifact produced without an explicit `rng`/global seed regenerates differently on re-run. Hashes, the Case E oracle (T9's script), and the artifact-script audit: NEEDS-REPO-VERIFICATION. What a reader could not regenerate from the package alone: any manuscript number — the experiments/ scripts and runs/ artifacts are not in this package.

---

## 4. Verified-correct list

- **T2 fix mathematics**: law-of-total-variance moments in `_summarize` (debias.py:146-163); `bias=True` between-draw covariance; group conditioning through the full-kernel Cholesky; all-component group ≡ full posterior; empty/singleton group handling; repeated-name collapse (debias.py:98-134).
- **T3**: the global-shift cancellation argument and its per-row counterfactual are both correct; pooled arithmetic in `aggregate_convention` is identical to `soft_transfer(normalize_per_draw=False)`, rowmin identical to `True`.
- **Divergence formulas**: joint KL, Bhattacharyya (0.5 log(|Σ̄|/√(|Σp||Σq|)) form verified), pointwise scalar KL/Hellinger, `pw_hellinger`'s equal-variance exponents, `pw_hellinger_vcal` (μ²/8σ²), `pw_kl_vcal` reduction to GP-weighted MSE — all match the manuscript's statements, including the corrected v2 exponents documented at metrics_v2.py:66-67, 103-105.
- **Laplace identities**: the τ rescale `log_int + G_star − G_star/τ + (d/2)log τ` equals `−Ḡ*/τ + (d/2)log(2πτ) − ½log|H|` (laplace_evidence.py:437); the same identity in `model_posterior_tau_sweep` construction I (laplace_evidence.py:1077); clipping evaluated once on Ḡ so τ-sweeps are clipping-artifact-free.
- **Estimator conventions**: MC box-uniform estimates the occam-normalized quantity and `occam=False` adds `+log V` (laplace_evidence.py:508-531); IS estimates the raw Lebesgue integral with the exact mixture density (out-of-box = indicator), `occam=True` subtracts (laplace_evidence.py:642-694); the defensive proposal's `log_q` normalization is consistent with its sampler; per-direction variance cap at box scale.
- **Sentinel/NaN semantics**: `log_weight_ess` (NaN column → NaN, all-−inf → 0, global max shift) (bms_star.py:466-491); `soft_transfer`/`soft_transfer_weighted` raise on non-finite G (bms_star.py:610-614, aggregation_v3.py:414-417); the `tot>0 else uniform` tails are dead on finite input (at least one weight is exp(0)=1 under a global shift).
- **Tie discipline**: `hard_win_statistics` co-minimizer credit, attainment, tie fraction (bms_star.py:509-528); the τ-free invariance claim of section 02 rests on this and holds.
- **A4 firewall** coverage at every candidate-list boundary (T8), including the aggregation_v3 entry point.
- **Withdrawn-cache path logic** (config.py:37-46), verified for file, directory, and subdirectory cases.
- **`mixture_central_interval`**: exact mixture quantiles by bisection, shape/mass validation (decompose.py:125-160).
- **`external_targets` checker**: validation-before-tolerance ordering defeats the NaN-passes-max trap (external_targets.py:54-71); recomputation from stored rows; stored-field cross-check.
- **Section 02 vs code** (P-C above), including the single-kernel site-name fix rationale at model.py:76-85 and the A10 period freeze invariants (model.py:141-205).

---

## 5. Recommendations (priority order)

1. **Run the suite in the fix worktree and record counts/runtime** — 0.5 h — closes B3 and establishes the baseline every later step reports against. NEEDS-REPO-VERIFICATION.
2. **Audit FIX-2 inheritance**: list every runs/ artifact and manuscript/poster band produced by `decompose_model_hmc/mcmc` pre-fix, regenerate with the fixed code, and mark every inheriting statement — 2-3 d — closes B1, the largest retraction risk.
3. **Fix C1 (make `pw_kl_vcal` the default of `compute_G_matrix`, or raise on omission) and add a failure mask for C2/C6** — 0.5-1 d — closes the last silent-wrong-answer seams on the paper paths and makes W1 enforceable rather than conventional.
4. **Execute the merge plan of §3 P-B** (fix → main → Case A → C → rest, resolving `aggregate_convention` and re-running each case script) — 3-5 d — closes B2 and lets P1 be checked per section.
5. **Characterize the T1 surrogate**: add a per-draw-mean vs moment-matched G diagnostic at the MAP point and report it beside every Z_M — 1 d — converts C5 from undisclosed-magnitude to bounded.
6. **Provenance sweep**: per section 01-08, name the experiments/ script and runs/ artifact, and pin `rng`/seeds (C7) so artifacts regenerate — 1-2 d — closes B4 and most of P5.
7. Hygiene pass (C3 jitter counting, C8/C9, C12, C13 docstrings, C11 grid documentation) — 1 d — reduces future-review surface.

---

## 6. Commands run and what could not be run

No commands were run: this channel has no repository access and no execution environment. In particular, I could not run: the pytest suite (the expected 1346/5/1 counts and runtime are NEEDS-REPO-VERIFICATION); any probe script (including the `bistar_gp.__file__` editable-install trap check); `git show/log/diff/merge-tree` on the paper branches; the experiments/ scripts (not in the package, including `toy_debias_demo.py` for T9); or any artifact regeneration for P5. All findings above derive solely from the supplied listings (bistar_gp/{bms_star, aggregation_v3, laplace_evidence, debias, decompose, metrics_v2, config, induced_prior, external_targets, candidates, model}.py at ddf8c9d), the frozen notation, the section 02 specification, and the test-file name list.

— GLM 5.3 (package-only channel)
