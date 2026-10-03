# Implementation review of fix pass 1 — GLM 5.3 (package-only channel), 2026-09-08

*Driver note: produced by `z-ai/glm-5.3` via OpenRouter, prompt 80595 tokens, completion 39689 tokens, finish_reason `stop`, 558 s. Package: fix1 package-only brief + specification + cumulative diff + new files + post-fix listings. No text altered below this note.*

# FIX PASS 1 review — GLM 5.3 (package-only channel)

Convention for this channel: I could not execute anything. "CONFIRMED" below means established by line-reference reading of the supplied diff plus standard deterministic semantics (e.g., NumPy NaN propagation, closed-form algebra I re-derived by hand); every claim that would need an interpreter or a repository file is tagged NEEDS-REPO-VERIFICATION and stated as PLAUSIBLE. Line numbers are post-change ("+"-side) numbers derived from the hunk headers.

## 1. Verdict

**APPROVE** for the pass as a whole: all nine FIXes compute what the work order and the manuscript require, the mathematics I could check by hand is correct (law-of-total-variance moments, full-covariance group conditioning, the /8 Bhattacharyya exponent, joint log-sum-exp weighting, split tie credit, the three aggregation conventions), the refuted items were not implemented, and the residual findings are one latent S3 (a silent uniform fallback in the new `aggregate_convention` on non-finite input) plus S4 hygiene items, one of which (the `metric_name` keyword) already awaits the author's R4 disposition.

## 2. Findings on (a)

| ID | FIX | Severity | Status | path:line | Claim |
|---|---|---|---|---|---|
| F1 | FIX-9 | S3 | CONFIRMED (code reading; NaN semantics standard) | bistar_gp/bms_star.py:681–715 (fallback at :714–715) | `aggregate_convention` silently returns the uniform posterior for non-finite G under `pooled`/`rowmin` |
| F2 | FIX-3 | S4 (contract, pending author) | CONFIRMED | bistar_gp/bms_star.py:583, :664 | `metric_name` left optional ("unspecified" stamp) contrary to FIX-3(b)'s required keyword |
| F3 | FIX-2d | S4 (scope deviation) | CONFIRMED | experiments/bistar_debias_mauna_loa.py:393, :428 | `main()`'s two decomposition call sites edited beyond "the grouping function only" |
| F4 | FIX-6 | S4 | CONFIRMED | bistar_gp/aggregation_v3.py:410–433 | `soft_transfer_weighted` lacks the non-finite G guard its sibling `soft_transfer` now has |
| F5 | report | S4 | CONFIRMED | fix1_report.md, FIX-6 section | "a legacy positional call still works" is false for callers that pass `log_mlls` |
| F6 | report | S4 | CONFIRMED | fix1_report.md, Verification §2 | pass-1 arithmetic "collected 1331 = 1253 pre-existing + 79 new" is off by one |
| F7 | FIX-2a | S4 | CONFIRMED | bistar_gp/debias.py:45–60, :69–75 | `samples` retained with dual meaning instead of removed-and-aliased as ordered |
| F8 | FIX-2 | S4 | CONFIRMED | bistar_gp/debias.py:125–140 | `group()` on a typo'd singleton name raises "not requested … pass groups=[…]", inviting an impossible request |

### F1 (S3) — `aggregate_convention` uniformizes non-finite input

What is wrong. The pooled/rowmin tail (bms_star.py:712–715) is

```python
lw = -G_eff / tau
w = np.exp(lw - lw.max())
s = w.mean(axis=0)
tot = s.sum()
return s / tot if tot > 0 else np.ones(G.shape[1]) / G.shape[1]
```

There is no finiteness validation at entry (unlike `soft_transfer`, bms_star.py:600–604). For a G containing NaN, `lw.max()` is NaN, every `w` entry is NaN, `tot` is NaN, and `tot > 0` is False, so the function returns the uniform posterior — exactly the pre-fix silent behavior that FIX-3/1b removed from `soft_transfer` (whose old code had the same dead fallback). `expected_posterior` (bms_star.py:707–712) instead returns NaN, so the three variants disagree on invalid input. An all-`+inf` G reaches the same fallback via `exp(-inf - (-inf)) = exp(nan)`.

Failure scenario. `aggregate_convention(np.array([[np.nan, 1.0],[0.0, 1.0]]), 1.0, "pooled")` returns `[0.5, 0.5]` with no error; `soft_transfer` on the same matrix raises. On package-produced paths (`compute_G_matrix` output, `prior_sensitivity_study._boltzmann_posterior`) G is finite, so the path is latent — S3, not S2.

Reproduction. I could not execute; the claim rests on the code shape at bms_star.py:681–715 plus standard NaN semantics of `np.max`/`np.exp`. Execution check NEEDS-REPO-VERIFICATION; the finding itself is CONFIRMED by reading.

Suggested change. Three lines at the top of the function: `if not np.all(np.isfinite(G)): raise ValueError("aggregate_convention requires a finite G matrix")`. The fallback branch is provably dead for finite G (the global-max entry gives `exp(0) = 1`, so `tot > 0` always), so the raise cannot perturb the pinned bit-identity with the Case A script, which the pins check only on finite fixtures. Because FIX-9's contract is "matches the case-A script exactly", the driver/author should sign off, but the deviation is confined to inputs the script never produces.

Pin. One test in tests/test_fix1_conventions.py: `aggregate_convention` raises on a NaN matrix for all three variants, and on an all-`+inf` matrix.

### F2 (S4) — `metric_name` optional in `soft_transfer`

FIX-3(b) ordered: "`soft_transfer` requires `metric_name` (no 'unknown' stamp)". The pass made it optional with None recorded as "unspecified" (bms_star.py:583, :664) and pinned that in test_fix1_diagnostics.py. The report's correction 2 discloses it and routes it to the author as R4. My judgment: the deviation was forced — the editable set includes `metrics_v2.py` but not `mcse_strategy.py`, whose call site (report: mcse_strategy.py:177, PLAUSIBLE, NEEDS-REPO-VERIFICATION) omits the name — so a required keyword was infeasible without violating work-order rule 2. "unspecified" is not the banned "unknown" string, but it is the same concept. This needs an author disposition: either migrate `mcse_strategy.py:177` in the commit round and require the keyword, or record a DECISIONS addendum accepting the documented legacy exception. Not a correctness fault in what the pass computes.

### F3 (S4) — Mauna script scope

Work-order rule 2 permits editing "the grouping function only" of bistar_debias_mauna_loa.py, but FIX-2(d) requires `compute_debiased` to read `result.group(...)`, and group moments can only be formed per draw at decomposition time. The two mandates conflict; the pass resolved it the only possible way (passing `groups=INTERPRETATION_GROUPS` at bistar_debias_mauna_loa.py:393 and :428) and disclosed it as deviation 1. Justified. No figure was regenerated, so no committed number moved.

### F4 (S4) — asymmetric non-finite guard

`soft_transfer_weighted` (aggregation_v3.py:410–433) accepts a non-finite G without complaint; NaN propagates to NaN posteriors, NaN `weight_ess` (via `log_weight_ess`'s nan-column rule), and NaN scores — so it is *not* a silent-wrong-answer path, merely an inconsistency with `soft_transfer`'s new raise and with F1's fix. Suggested: the same three-line guard. Pin alongside F1's.

### F5 (S4) — report inaccuracy

"Signature change: `log_mlls` moved from required positional to optional keyword in the same position; a legacy positional call still works." A legacy positional call *passing `log_mlls`* now raises (induced_prior.py:200–205, the pass-1b conflict guard), by design and correctly so; only calls omitting `log_mlls` still work. The 1b addendum documents the raise; the pass-1 sentence should be struck in the committed report so a future maintainer does not rely on it.

### F6 (S4) — report arithmetic

"Total collected 1331 = 1253 pre-existing + 79 new" — 1253 + 79 = 1332. Either the pre-existing count is 1252 or one new test was added after run 2 started (the report itself notes a late roles-test edit). The 1b numbers (1348 = 1331 + 17; 1342 + 5 + 1 = 1348) are internally consistent. Cosmetic.

### F7 (S4) — `samples` retained

FIX-2(a) ordered the `samples=means` naming removed (deprecated alias only if needed). The pass kept `samples` populated with per-draw conditional means on draw paths, marked by `samples_kind` (debias.py:45–60), because the read-only poster driver writes `comp.samples` and rebuilds with `samples=` (report correction 3; poster_d58_mauna.py:477, :541 — PLAUSIBLE, file not in package, NEEDS-REPO-VERIFICATION). Justified given the editable-set boundary; the `samples_kind` marker plus the raising `central_interval` on moment-free components (debias.py:69–75) is an adequate guard against the dual meaning being confused. Remove in fix pass 2 when the D58 driver is editable.

### F8 (S4) — misleading KeyError for a typo'd singleton

`group(["typo"])` on an unknown singleton falls through to the "not requested … pass groups=[…]" message (debias.py:125–140), instructing the caller to request a group that `_validated_groups` would reject as unknown anyway. A `if len(key) == 1 and key[0] not in self.components: raise KeyError(f"unknown component {key[0]!r}")` branch would name the real problem. Cosmetic.

### Items checked and found NOT to be findings

- **strict=False NaN paths (brief a.4).** A NaN cannot become a silently "best" score: `_select_start` (laplace_evidence.py:497–507) filters to finite objectives and returns NaN only when all starts failed; `model_posterior`'s softmax is a joint normalization, so one NaN kernel NaNs every posterior (laplace_evidence.py:845–855, pinned in test_fix1_sentinels.py); `log_weight_ess` distinguishes NaN (invalid evaluation) from all-`-inf` (absent support, ESS 0), so the starvation warning cannot be spoofed by a failure (bms_star.py:468–500). One unseen link — `_guarded_neg_log`'s NaN handling — is not in the diff; if it sanitized NaN, the pinned NaN tests (test_raising_predictor_yields_nan_not_a_win_under_non_strict, test_r8_*) could not pass as reported. NEEDS-REPO-VERIFICATION; on the package evidence, PLAUSIBLE-correct.
- **Bit-exactness of the canonical pooled arithmetic (D60).** The `soft_transfer` hunks add validation and diagnostics only; the `G_effective` block, the global-shift stabilization, and the `normalize_per_draw=False` default are untouched, and test_fix1_conventions.py pins `pooled` to `soft_transfer(normalize_per_draw=False)` and to a verbatim copy of the pre-fix `_boltzmann_posterior`. The uniform fallback inside `soft_transfer` is now dead code (G validated finite) rather than changed code.
- **Refuted items.** No E6 file appears in the diff; no finiteness "explanation" of the aggregation_v3.py:77 warnings (the new entry assertions in `average_gp_posterior` are FIX-6(c), required, and pass all-finite input through unchanged); no change to soft_transfer's pooled arithmetic or default.
- **`extract_gp_predictives` "site absent from mcmc_samples"** (FIX-1b wording): vacuous, since `select_hmc_sites` filters from `mcmc_samples.keys()`; the substantive guard (unrecognized site raises) is present at bms_star.py:355–380.
- **`decompose_model_hmc` result `noise_var`**: the new `last_noise` (last *successful* draw) vs the pre-fix last *built* draw differs only on the non-strict failure path, in a field not used by any moment. Not a finding.
- **Duplicate `instance_names` with `class_names=None`**: passes (the uniqueness check runs only on the explicit `class_names` branch, bms_star.py:606–616). No caller break.

## 3. Recommendations on (b)

- **FIX-1 — KEEP.** `PredictiveList` (bms_star.py:237–259) is 20 lines and a genuine `list` subclass; the alternative (a `(list, log)` tuple return) breaks every existing call site for zero gain. The three-scheme site dispatch in model.py:78–118 is inherent to the archive formats and its precedence rules (kernels. prefix wins; bare-`covar_module.` accepted only when `covar_module is kernel_components[0]` and exactly one component) are pinned by test_fix1_sites.py. Right size.
- **FIX-2 — KEEP.** The 1b `_DrawAccumulator` with typed tuple keys, the single `_summarize`, and whole-record draw commits (debias.py:215–280) is the design I would have asked for: one Cholesky of the entire training covariance per draw serves every target, per-draw full matrices are never stored (only `cov_sum`), and the between-draw covariance uses `bias=True`, consistent with `M.var(axis=0)` (ddof=0) so `diag(cov) == std**2` holds exactly. The residual wart is the `samples` dual meaning (F7); delete it in fix pass 2 when the poster driver is editable, not now.
- **FIX-3 — KEEP.** `boltzmann_weight_ess` and `hard_win_statistics` are small pure functions; computing ESS on `G_effective` (the weights actually aggregated) and the win statistics on the raw G is the correct split, since a per-row shift changes within-candidate ESS but not ties.
- **FIX-4 — KEEP.** Two one-line exponent corrections plus a guard moved to the boundary that still holds metadata. Nothing to simplify.
- **FIX-5 — KEEP (accretion acknowledged, alternative rejected).** `strict` threaded as a trailing keyword through nine functions is verbose, but the alternatives — a module-level flag or a context object — add hidden state to a numerical library and a larger API surface than the flag itself. `OptimizerRecord` is the right provenance surface. If anything is trimmable it is `ZMxSweepResult.optimizer_records`, but that is the per-start provenance FIX-5(b) ordered.
- **FIX-6 — KEEP.** The joint log-space form is canonical. The one-line pre-fix-scale restoration of `instance_scores` (aggregation_v3.py:432) is defensible compatibility; drop it only after a consumer audit in fix pass 2.
- **FIX-7 — KEEP.** `_MetricRegistry.__missing__` (bms_star.py:194–206) is already the elegant replacement for the pass-1 `_resolve_metric` that the brief named as accretion — the criticized form no longer exists. `WITHDRAWN_CACHES` as a tuple plus a 12-line predicate is minimal; the prefix and file-entry matching handles deep paths (pinned in test_fix1_roles.py).
- **FIX-8 — KEEP.** The checker recomputes errors from the rows rather than trusting the stored field, and validates finiteness before the mass check (external_targets.py:78–93, R9); the embedded committed rows make the fixture-independent test self-checking, because a transcription error in the Target B row would fail against the recomputed Beta densities, not pass wrongly.
- **FIX-9 — SIMPLIFY IN PLACE (F1 patch), otherwise KEEP.** Add the three-line finiteness guard; do not delegate `soft_transfer` to `aggregate_convention` even though it would remove ~6 duplicated lines — the bit-identity pins on the D60-pinned pooled arithmetic are this pass's safety net, and delegation risks perturbing them for zero behavioral gain until fix pass 2.
- **Overall — KEEP the pass; do not delete and re-implement.** The 1b folds already removed the accretion worth removing (one ESS routine, one ComponentResult constructor, `_resolve_metric`, partial-draw commits). The pass is the right size for what it was ordered to do.

## 4. Verified-correct list

- **FIX-1.** Single-kernel site names selected (model.py:78–87) and applied only when `model.covar_module is kernel_components[0]` with exactly one component (model.py:108–118); multi-kernel and legacy precedence preserved; unrecognized site raises under strict, warns and is excluded from `hp_dict` provenance under non-strict (bms_star.py:355–380); per-draw failure raises under strict and is recorded with index + reason under non-strict (:411–428); `PredictiveList` is a real list; `_sir_bms` count assertion (prior_sensitivity_study.py:686–690); `decompose_model_mcmc` name-matching with unknown/missing key raises (debias.py, `_raw_parameter_map` dedup by identity is sound for `fit_mcmc_simple` raw output).
- **FIX-2.** Law-of-total-variance moments: `std**2 = mean_d(var_d) + var_d(mean_d)` with the population (ddof=0) convention consistently on both the diagonal and the full between-covariance; per-draw conditional covariance retained without storing per-draw full matrices; group conditioning uses the Cholesky of the ENTIRE training covariance plus noise (debias.py, `_DrawAccumulator.add_draw`), so all-components group == full posterior and the anticorrelation cross terms survive (pinned against direct per-draw conditioning in test_fix1_decomposition.py and test_r10). MAP values preserved: the 1e-10 variance floor and sqrt are reproduced exactly through `_single_draw_summary`. Seven-field positional `DecompositionResult` contract intact; new `ComponentResult`/`BMSStarResult` fields all defaulted, so the poster driver's keyword construction still type-checks (whether the driver calls `central_interval` is NEEDS-REPO-VERIFICATION; the D58 correction is fix pass 2 regardless). `mixture_central_interval` (decompose.py:123–160): the ±12σ bracket bounds the mixture CDF by Φ(−12) ≈ 3e-33, 100 bisection iterations are far past convergence, shape and mass validated; coverage pinned on a Gaussian and an asymmetric mixture.
- **FIX-3.** ESS formula (Σw)²/Σw² in log space with per-column max subtraction (overflow-safe; column-shift invariant; underflow-safe — verified by hand on the pinned fixtures); NaN vs absent support distinguished. `hard_win_statistics`: exact-tie split credit sums to one; the ledger fixture [[0,0],[10,11]] gives attainment [1, 0.5], credit [0.75, 0.25] — recomputed by hand. Grouped `class_names` raises; 1:1 relabelling passes.
- **FIX-4.** The equal-variance Gaussian Bhattacharyya distance is Δ²/(8σ²) (from D_B = (Δμ)²/(4(σ₁²+σ₂²)) at σ₁=σ₂), so 1 − exp(−1/8) = 0.11750309741540454 — recomputed by hand; both v2 variants fixed (metrics_v2.py:70, :110) and consistent with the always-correct base `pw_hellinger`. Firewall moved into `compute_G_matrix` (bms_star.py:547–551) and added explicitly to `score_averaged_gp` (aggregation_v3.py:128–131); all-untagged legacy contract preserved; rejection precedes any metric call (pinned by the counting-metric test).
- **FIX-5.** Sentinels (1e6, −1e10) removed; `EvaluationFailure` re-raised by both optimizer handlers so a strict failure can never become a start-point expansion; `_select_start` order-independent under NaN; NaN propagates to NaN log_Z/ESS/posteriors and can never win (see F-item "not a finding" above); the induced-prior penalty `max_finite + 10(|max_finite|+1)` is strictly worse than every finite value for either metric sign — verified algebraically; `_select_restart` prefers successful restarts, as ordered by FIX-5(c).
- **FIX-6.** Joint `log w_i − G_ij/τ` with log-sum-exp: the pinned underflow case gives 2/(2+1+e⁻¹) = 0.59384548… — recomputed by hand; common log-weight shifts cancel exactly; all-absent support raises; absent draws dropped, not uniformized. The pre-fix-scale `instance_scores` restoration is algebraically exact (verified: exp(log[Σw e^{−G/τ}/Σw] + G_min/τ) = Σw e^{−(G−G_min)/τ}/Σw). The two-state posterior example: uniform weighting gives [1.8, 0.2] (recomputed: (1/10)(c²/2) + (9/10)((2−c)²/2)); the tilt gives [162/82, 2/82] = [1.9756, 0.0244] — both correct, and the double-counting diagnosis is right. `average_gp_posterior` finite guards present (aggregation_v3.py:83–90).
- **FIX-7.** Registry on-miss import is sound (`in` does not trigger `__missing__`; the implicit `list(METRICS.keys())` path is unchanged); appendix warning fires only on the implicit path (pinned); withdrawn-cache matching handles file entries, directory prefixes, and deep paths (logic read line-by-line at config.py:38–49; execution NEEDS-REPO-VERIFICATION); the appended primary metric preserves positional slices.
- **FIX-8.** Beta(2,2) pdf at 0.5 = 1.5 exactly; Beta(50,50) pdf at 0.5 = 0.5⁹⁸Γ(100)/Γ(50)² ≈ 7.96 (Stirling check gives ≈ 8.0, consistent with 7.95892373871788); weight 7.9589/9.4589 = 0.84141959049… ✓; the committed min-τ row's Target B error |0.8414189500 − 0.8414195905| = 6.4047e-7 matches the stored field and is under tol_b = 1e-5; NaN validation precedes the mass check (the `max()`-keeps-finite-over-NaN trap is correctly closed).
- **FIX-9.** `pooled` is statement-for-statement the pre-fix `_boltzmann_posterior` (bit-identity plausible); `rowmin` equals `normalize_per_draw=True`; `expected_posterior` is the per-row softmax averaged (van Bork Eq. 4); offset algebra verified by hand: a global offset cancels in all three, a per-row offset changes `pooled` only; the τ→0 limit on the tied fixture equals the split credit.
- **Refuted items** confirmed not implemented (see section 2 tail).
- **Report internal consistency:** the 79 + 17 new test counts match my per-file count of the diff (9+10+6+6+6+11+6+6+19 = 79; review-round file = 17).

## 5. Commands run and their outcomes

None. As the package-only channel I could not run the suite, the Case E oracle, the fixture-gated tests, or any probe; accordingly:

- Suite counts and runtime (implementer claims 1342 passed, 5 skipped, 1 failed — the known `test_m2cr_environment_freeze.py` dependency-lock drift — 466 s for pass 1b): PLAUSIBLE, NEEDS-REPO-VERIFICATION. The counts are internally consistent with the collected total (1348 = 1331 + 17), except for the pass-1 off-by-one noted as F6.
- Case E byte-identity (sha256 65c9ff5f…/c1153549…/7096cd6e…): PLAUSIBLE, NEEDS-REPO-VERIFICATION. Structurally supported: the diff touches no function the script uses except `select_hmc_sites`/`apply_hp_value`, whose new branches are unreachable for the script's multi-kernel `covar_module.kernels.*` site names, and `decompose_additive_gp`/`decompose_component` are unchanged.
- The scratch-symlink oracle mechanism and the `FIX1_FIXTURE_DIR` fixture runs: PLAUSIBLE, NEEDS-REPO-VERIFICATION; nothing in the diff indicates a write into either repository tree.
- The two package call sites said to omit `metric_name` (metrics_v2.py:398, mcse_strategy.py:177) and the poster driver's `comp.samples` use: files not in the package, PLAUSIBLE, NEEDS-REPO-VERIFICATION.

— GLM 5.3 (package-only channel)
