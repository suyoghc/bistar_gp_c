# Project review 2026-09-26, code package — Kimi K3 (package-only channel), 2026-09-26

*Driver note: produced by `moonshotai/kimi-k3` via OpenRouter, prompt 87859 tokens, completion 10866 tokens, finish_reason `stop`, 540 s. Package: project-review brief + HANDOFF sections 2-3 + notation + section 02 + line-numbered sources of 11 modules at ddf8c9d. No text altered below this note.*

# Independent Implementation-Correctness and Project Review — BI*/BMS*-GP at `ddf8c9d`

Channel: **Kimi K3 (package-only channel)**. No code was executed; no repository files beyond the listings in this package were consulted. Every claim that requires running code, reading paper-branch files, or inspecting `runs/` artifacts is tagged **NEEDS-REPO-VERIFICATION** and marked PLAUSIBLE. Line citations are the listings' own line numbers at `ddf8c9d`.

---

## 1. Verdict

**Code: REVISE.** The 2026-09 fix passes materially hold up under re-inspection — the FIX-2 total-variance decomposition, the sentinel removal in the evidence path, the ESS diagnostics, and the firewall placement are all mathematically correct as written — but the Ḡ plug-in surrogate (T1) remains an open, unquantified estimator substitution on the manuscript's load path, and several S3/S4 seams the brief names (implicit metric roster, `samples` dual meaning, order-dependent `noise_var`, withdrawn-cache guard bypassable) remain live.

**Project: NOT READY for submission.** Blocking list:
1. **T1 surrogate unquantified** — every Z_M / model-posterior number in sections 2, 4, 5 flows through `compute_G_at_params(avg_gp…)` (`bistar_gp/laplace_evidence.py:148`); the manuscript discloses the substitution but no error bound or per-artifact sensitivity exists on the evidence in this package (NEEDS-REPO-VERIFICATION for the artifact inventory).
2. **Seven unmerged branches with diverging DECISIONS ledgers (P2)** and demonstrated API breakages of paper-branch case scripts against the fix-branch package (strict extraction, `compute_induced_prior` weighting, `soft_transfer_weighted` raising, `DecompositionResult.group` request-time contract).
3. **FIX-2 inheritance sweep** — every band previously produced by `decompose_model_hmc`/`decompose_model_mcmc` was understated; which manuscript/poster statements inherited that, and whether they are marked, cannot be confirmed from this package (NEEDS-REPO-VERIFICATION).
4. **Suite not run by this channel** — expected counts 1346 passed / 5 skipped / 1 failed are unverified here.

---

## 2. Code findings

### Summary table

| ID | Target / module | Sev | Status | path:line | Claim |
|---|---|---|---|---|---|
| C1 | T1 plug-in surrogate | S2 | CONFIRMED (by inspection) | bistar_gp/laplace_evidence.py:148; aggregation_v3.py:91-98 | Ḡ computed once against the moment-matched averaged pattern; gap is φ-dependent and unbounded-characterized nowhere |
| C2 | T4 weight concentration | S3 | PLAUSIBLE | bistar_gp/bms_star.py:660; aggregation_v3.py:275 | ESS diagnostic now computed but never thresholded or asserted; dominance still possible silently downstream |
| C3 | T6 W1 metric roles | S3 | CONFIRMED (by inspection) | bistar_gp/config.py:24-25; bms_star.py:768-784 | pw_kl_vcal primacy is convention + warnings only; an explicit `metric_names=["kl_forward"]` call passes with no signal |
| C4 | T7 withdrawn caches | S3 | CONFIRMED (by inspection) | bistar_gp/config.py:31-46,253-269 | Guard lives only inside `load_hmc_samples`; a direct `np.load` bypasses it entirely |
| C5 | T8 firewall completeness | S3 | CONFIRMED (by inspection) | bistar_gp/bms_star.py:549,718-745; soft_transfer:578 | Firewall sits at G-matrix construction; a hand-built G matrix reaches `soft_transfer`/`soft_transfer_weighted`/`aggregate_convention` unguarded |
| C6 | All-failed metric → uniform posterior | S3 | CONFIRMED (by inspection) | bistar_gp/bms_star.py:568-573 | If every metric evaluation raises, G is a constant 1e6 and posteriors are exactly uniform with no flag |
| C7 | All-failed induced-prior draw rows | S3 | CONFIRMED (by inspection) | bistar_gp/induced_prior.py:268-273 | `g_vals[:] = 1e6` on total failure yields a uniform induced prior with full ESS |
| C8 | Path-dependent `noise_var` in decomposition results | S3 | CONFIRMED (by inspection) | bistar_gp/debias.py:406-417, 461, 492, 517-518 | `DecompositionResult.noise_var` is the LAST retained draw's noise; depends on rng subsample order and dropped-draw sequence |
| C9 | Implicit metric roster is import-history dependent | S3 | CONFIRMED (by inspection) | bistar_gp/bms_star.py:763-765; metrics_v2.py:193 | `list(METRICS.keys())` content and order vary with whether `metrics_v2` was imported first (dict order) |
| C10 | `ComponentResult.samples` dual meaning | S4 | CONFIRMED (by inspection) | bistar_gp/debias.py:44-49, 55-57 | `samples` means function draws on MAP path, conditional means on draw paths; disambiguated only by `samples_kind` |
| C11 | `log_weights` field shifted | S4 | CONFIRMED (by inspection) | bistar_gp/induced_prior.py:284,318 | Stored `log_weights` retain the max-shift and are not the raw induced log weights −Ḡ/τ |
| C12 | compute_G_matrix docstring roster stale | S4 | CONFIRMED (by inspection) | bistar_gp/bms_star.py:540 | Docstring lists only 4 metrics though 18 are registered (registry effect) |
| C13 | T2 FIX-2 verification | — | VERIFIED CORRECT | bistar_gp/debias.py:146-163, 195-263 | Total-variance moments, group conditioning with full-kernel Cholesky, typed target keys — correct |
| C14 | T3 global-shift argument | — | VERIFIED CORRECT | bistar_gp/bms_star.py:639-646 | Global scalar shift cancels exactly in cross-candidate normalization; per-row shift would not |

### Detail

**C1 (T1, S2).** `compute_G_at_params` evaluates the metric against `avg_gp.mean, avg_gp.cov` (`laplace_evidence.py:148`), where `avg_gp` is the mixture moment-match built in `average_gp_posterior` (`aggregation_v3.py:91-98`). The notation file glosses Ḡ as "averaged across data patterns"; the machinery section now calls the implementation a plug-in surrogate and asserts non-consistency. Both statements are consistent with the code. What the package does NOT contain: any bound, expansion, or numeric characterization of the gap E_i[G(ψ_i, φ)] − G(ψ̄, φ), and no test file name suggests one (the 67 test files include no surrogate-gap test). **Failure scenario (concrete):** with per-draw means m_i and covariances C_i, `pw_kl_vcal` against ψ̄ equals mean_i[0.5(μ_θ−m_i)²/diag(C_i)] only if C_i are all equal to Σ̄; with heterogeneous per-draw variances (exactly what HMC hyperparameter spread produces), the plug-in reweights every location by diag(Σ̄) instead of diag(C_i), and for a candidate concentrated where the spread term inflates Σ̄, the ranking across candidates can reverse relative to the per-draw average. Which committed numbers depend: all `laplace_log_Z_Mx`, `mc/is_log_Z_Mx`, `model_posterior` outputs on every figure path — NEEDS-REPO-VERIFICATION. **Suggested change:** add a per-draw-average Ḡ estimator (the G matrix machinery already computes per-draw divergences) and report both, or prove/report a bound for the paper configurations (N=20 toy, τ ∈ [0.1, 100]). **Pinning test:** construct three draws with known Gaussians where the two estimators differ by a closed-form amount; assert the code path used in figure scripts reports the disclosed quantity within tolerance of each, so the choice is explicit.

**C2 (T4, S3).** `soft_transfer` now computes `weight_ess` (`bms_star.py:660`) and `soft_transfer_weighted` computes `log_weight_ess(log_terms)` (`aggregation_v3.py:443`), but nothing asserts a minimum ESS, no caller-visible warning fires, and `run_bms_star` prints only raw-win counts (`bms_star.py:798-801`). **Failure scenario:** at τ=0.1 (inside the manuscript sweep τ ∈ [0.1, 100]) with G ranges of typical pw_kl_vcal magnitude, a single draw can carry essentially all weight for one candidate; `weight_ess ≈ 1` is recorded in the result object but never surfaces unless the caller inspects it. Whether this occurs in a committed artifact: NEEDS-REPO-VERIFICATION. **Change:** warn (as `is_log_Z_Mx` does at `laplace_evidence.py:696-701`) when min per-candidate ESS falls below a stated floor; report weight_ess in every soft-transfer table per section 2's own reporting rule. **Pinning test:** G matrix with one dominant cell; assert the warning fires.

**C3 (T6, S3).** `PRIMARY_METRIC`/`APPENDIX_METRICS` exist (`config.py:24-25`) and the implicit path of `run_bms_star` warns (`bms_star.py:768-784`), but an explicit `metric_names=["kl_forward"]` receives no warning, and `ExperimentConfig.metrics` (`config.py:212-217`) still lists `kl_forward` first with the primary metric appended last "so positional uses keep their meaning" — i.e., legacy positional slices select the appendix metric by construction. **Failure scenario:** any manuscript-facing script doing `metrics[:4]` scores only joint metrics including `kl_forward` and nothing warns. Which scripts do this: NEEDS-REPO-VERIFICATION. **Change:** make the appendix metric opt-in (raise unless `allow_appendix=True`) on manuscript-facing entry points. **Test:** assert `run_bms_star(..., metric_names=["kl_forward"])` warns/errors.

**C4 (T7, S3).** `load_hmc_samples` refuses withdrawn caches (`config.py:262-268`), but the guard is a path-string check inside one loader; nothing prevents `np.load("runs/toy_tau_metric_comparison/…")` directly, and `is_withdrawn_cache` matches only the two listed entries. Whether any script reads them directly: NEEDS-REPO-VERIFICATION. **Change:** quarantine the artifacts out of `runs/` (or delete them per the banner); the guard is then belt-and-suspenders. **Test:** assert no file under the two prefixes is reachable by any experiments/ script (grep-level test would suffice).

**C5 (T8, S3).** The A4 firewall is correctly placed at `compute_G_matrix` (`bms_star.py:549`) and duplicated in `score_averaged_gp` (`aggregation_v3.py:130`); partially-tagged rosters raise (`bms_star.py:737`). But `soft_transfer` (`bms_star.py:578`), `soft_transfer_weighted` (`aggregation_v3.py:401`), and `aggregate_convention` (`bms_star.py:679`) accept a bare G matrix and cannot know universes; a caller that builds two per-universe G matrices through the guarded path and concatenates the columns reaches a normalized cross-universe posterior with no signal. Whether anything in `experiments/` does this: NEEDS-REPO-VERIFICATION. Also note the guard validates *consistency*, not *authorization*: any novel string tag is accepted as a universe. **Change:** attach the universe set to the G matrix (or require a `universes=` argument on `soft_transfer`) so the normalization boundary itself is guarded. **Test:** concatenated two-universe G matrix → `soft_transfer` raises.

**C6 (S3).** `compute_G_matrix` penalty logic (`bms_star.py:568-573`): if NO entry is finite, `penalty = 1e6` and the whole matrix becomes 1e6; `soft_transfer` then passes the finite check (`:610`) and returns an exactly uniform posterior. A fully failing metric is indistinguishable from a genuinely tied comparison. **Failure scenario:** a metric that raises on every pair (e.g., mis-shaped candidate cov) under a caller that catches nothing — uniform posteriors flow into a table. **Change:** raise when fewer than some fraction of entries are finite. **Test:** always-raising metric → error, not uniform.

**C7 (S3).** Same class at the draw level in `compute_induced_prior`: `g_vals[:] = 1e6` when every GP-draw evaluation fails (`induced_prior.py:272-273`), after which all parameter samples share G=1e6, weights are uniform, and `effective_sample_size = n_param_samples` — the diagnostic reports perfect health for a total failure. **Change:** raise. **Test:** metric raising on all draws → error.

**C8 (S3).** `DecompositionResult.noise_var` is `last_noise` — the noise of the LAST successfully decomposed draw (`debias.py:492,498,517-518`; `decompose_model_mcmc` analog at `:406-417`). The value depends on the subsample order (`rng.choice`, `:444-447`) and on which draws dropped. Two runs with different seeds report different `noise_var` for the same posterior. **Change:** record the mean (or full vector) of retained draws' noise. **Test:** two seeds → identical `noise_var` up to tolerance, or the field becomes a vector.

**C9 (S3).** `run_bms_star` implicit roster is `list(METRICS.keys())` at call time (`bms_star.py:763-765`); v2 metrics register on `metrics_v2` import (`metrics_v2.py:193`), so the roster's content and iteration order depend on import history — a path-dependent result set (results dict keys differ). The pass-1b warning (`:776-784`) announces omission but preserves the behavior deliberately. Deferred-work acknowledgment is in the code; severity S3 because figure scripts on paper branches may rely on the implicit roster. NEEDS-REPO-VERIFICATION for callers.

**C10 (S4).** The brief-named seam is real and documented (`debias.py:44-49`): `samples` holds function draws (MAP) or conditional means (draw paths). Positional consumers on paper branches that assumed function draws get means silently. S4 because `samples_kind` disambiguates; flag for pass-2 rename.

**C11 (S4).** `InducedPriorResult.log_weights` is stored as shifted log weights plus `log(total)` (`induced_prior.py:284-291,318`), which reconstructs neither the raw −Ḡ/τ nor the normalized log weights — it retains the arbitrary max-shift. A downstream consumer exponentiating it gets the right normalized weights only after re-normalizing; treating it as unnormalized log density is wrong by a constant. S4 documentation/semantics.

**C12 (S4).** `compute_G_matrix` docstring (`bms_star.py:540`) names only the four original joint metrics though the registry resolves 18. Misleads a maintainer about valid `metric_name` values.

---

### Named targets T1–T11: explicit judgements

- **T1** — CONFIRMED OPEN (C1). The surrogate persists; manuscript discloses; error uncharacterized; artifact dependence NEEDS-REPO-VERIFICATION. The driver observation about RuntimeWarnings from `mu_bar = w @ means`: `aggregation_v3.py:82-86` now raises on non-finite means before the matmul, so the warning path the driver saw is pre-fix or from a different construction; confinement to stress inputs NEEDS-REPO-VERIFICATION.
- **T2** — FIXED in the library. `decompose_model_mcmc`/`decompose_model_hmc` retain per-draw conditional variance and report law-of-total-variance moments (`debias.py:146-163`, accumulator `:222-244`); group conditioning uses the full-kernel Cholesky (`:227`), so a full group reproduces the full posterior exactly. The MAP path was never affected (driver correction stands). Remaining: which paper/poster bands inherited the understatement — P1 item, NEEDS-REPO-VERIFICATION.
- **T3** — VERIFIED CORRECT. The global-max shift at `bms_star.py:644` is a scalar multiplying every candidate score equally after the over-draw mean; it cancels exactly in `instance_scores/total`. The comment's argument against a per-row max is mathematically right: a row-dependent shift changes the draw weights before averaging, mimicking `normalize_per_draw`.
- **T4** — Diagnostic now exists (C2); enforcement absent; occurrence in committed artifacts NEEDS-REPO-VERIFICATION. Partially resolved.
- **T5** — OPEN as a robustness question. `n_eval=60` (`config.py:200`) has no accompanying sensitivity analysis or test in this package; no failure scenario of incorrectness exists (the grid is a stated choice), so per the standard this is a question, but it deserves a one-paragraph justification in the manuscript and a coarse-grid/fine-grid agreement check. No test pins it.
- **T6** — NOT ENFORCED (C3); convention plus warnings only.
- **T7** — GUARDED BUT BYPASSABLE (C4). The two banned prefixes are refused by `load_hmc_samples`; direct reads are unchecked. No code path in the listings surfaces the artifacts.
- **T8** — CORE GUARD CORRECT, EDGES OPEN (C5). Guard logic itself (untagged allowed; mixed raised) is right and called from `run_bms_star` and both aggregation_v3 entry points that build G. Primitives on pre-built G matrices are unguarded; novel tags pass.
- **T9** — NOT AUDITABLE in this package: `experiments/toy_debias_demo.py` is not among the listings. NEEDS-REPO-VERIFICATION for the AST guard, the unmatched-site raise, the jitter probe, and the law-of-total-variance inversion. What IS auditable — the ported `mixture_central_interval` (`decompose.py:125-160`) — is correct: bracketing at ±12 sd, monotone bisection of the exact mixture CDF via `ndtr`, shape and mass validation; the quantile update direction (`:154-157`) is right.
- **T10** — Test names are visible but contents are not; adequacy judgements are therefore structural. Claims with NO identifiable protecting test by name: the Ḡ surrogate gap (no test file); n_eval sensitivity (none); weight-ESS surfacing (none); withdrawn-cache non-citation in experiments (none); manuscript-number goldens for Z_M/posteriors (test_laplace_zmx.py may cover unit identities — NEEDS-REPO-VERIFICATION for whether it pins manuscript values). The known failure (dependency-lock drift test) and 5 fixture-gated skips are unverifiable here.
- **T11** — FIXED on the named lines. `compute_G_at_params` raises `EvaluationFailure` under strict / NaN under non-strict (`laplace_evidence.py:133-154`); `_log_likelihood` likewise (`:309-320`); optimizer fallback now carries an `OptimizerRecord` and `n_starts_failed` (`:338-397`, `:491-502`), and `ModelPosteriorResult.all_converged` propagates. The `_GUARD_PENALTY=1e10` (`:61,77`) remains a finite sentinel by design; it cannot win (its "evidence" is −1e10-scale), and it is documented. Residual sentinels of the same class survive at C6/C7 and at `candidates.py:170-173` (SinusoidalModel silent fallback to `A=ω=1, σ=std(y)` when all restarts raise — warned only via the all-failed branch of `_select_restart`... in fact the `except Exception: continue` at `:162-163` swallows the failure and the fallback at `:170-173` is silent beyond `_select_restart` returning None; **S3 sub-finding**: a degenerate default sinusoid enters a G matrix with no error; change: raise when every restart raises; test: predict_fn that always raises → fit raises).

---

## 3. Project findings

### Summary table

| ID | Item | Sev | Status | Location | Claim |
|---|---|---|---|---|---|
| P1-a | P1 | BLOCKER | PLAUSIBLE / NEEDS-REPO-VERIFICATION | sections 2,4,5 ↔ laplace_evidence.py:148 | Every Z_M/posterior number inherits the T1 surrogate; sections disclose it, but no bound exists |
| P1-b | P1 | MAJOR | NEEDS-REPO-VERIFICATION | FIX-2 inheritance | Pre-fix bands from decompose_model_hmc/mcmc were understated; whether manuscript/poster statements that used them are marked cannot be checked from listings |
| P2-a | P2 | BLOCKER | CONFIRMED (from listings) | debias.py:102-134; bms_star.py:262; induced_prior.py:208-231 | Fix-branch API breaks paper-branch scripts in at least four demonstrated ways (below) |
| P2-b | P2 | MAJOR | NEEDS-REPO-VERIFICATION | DECISIONS D59–D67 vs D68 | Diverging ledgers across seven unmerged branches |
| P3-a | P3 | MAJOR | PLAUSIBLE | config.py:24-34 | W1/M2bR constraints are partially machine-enforced (good) but no Mauna-material and W4 framing are unverifiable here |
| P4-a | P4 | MAJOR | PLAUSIBLE | test file names | Suite value on paper paths unverifiable; five named gaps (T10) have no test |
| P5-a | P5 | MAJOR | NEEDS-REPO-VERIFICATION | runs/ vs experiments/ | Artifact regeneration, hashes, Case E oracle not inspectable |
| P6-a | P6 | — | — | §5 | Blocking list and two-week plan below |

### P2 detail and merge plan

**Demonstrated breakages** (from the fix-branch listings alone; paper-branch script contents NEEDS-REPO-VERIFICATION, so each is a conditional "if the script does X, it now fails"):

1. `extract_gp_predictives(..., strict=True)` is now the default and raises on unrecognized sites and on any failing draw (`bms_star.py:292-298, 341-343, 361-375, 415-422`); a script that relied on warn-and-drop must pass `strict=False` and then handle `PredictiveList.dropped` (`:237-256`).
2. `compute_induced_prior` raises if `log_mlls` is passed under the default `weighting="uniform"` (`induced_prior.py:208-215`) — legacy positional callers that fed posterior draws with log_mlls now hard-fail (deliberately, review F2).
3. `soft_transfer_weighted` raises on non-finite G and on all-non-finite log weights (`aggregation_v3.py:414-424`) where it previously returned NaN-contaminated or uniform posteriors.
4. `DecompositionResult.group(names)` raises `KeyError` unless the group was requested at decomposition time (`debias.py:131-134`); joint moments cannot be derived post hoc.
5. `aggregate_convention` moved INTO the package (`bms_star.py:679-715`, FIX-9), so Case C's cross-branch import from the Case A script must be rewired — this resolves the A-before-C dependency but is itself a conflict: whichever of the two branch versions of the function is dropped, the surviving one is the package one.
6. `PredictiveList` is a list subclass, so ordinary list use is safe (`bms_star.py:237-256`) — low risk.

**Merge order I would use:** (1) merge `fix/code-review-2026-09` to main first — it is a fast-forward of main plus fixes and changes the shared API, so everything else must rebase onto it; (2) rebase `paper/case-e-debias` next (it depends most deeply on FIX-2/`DecompositionResult.group` and the manuscript apparatus lives untracked on it); (3) `paper/case-a-vanbork`, then `paper/case-c` — with the A-before-C script dependency dissolved by FIX-9, both rewire their convention imports to `bistar_gp.bms_star.aggregate_convention` and the ordering constraint disappears, but C still touches the same machinery section as A, so A first minimizes textual conflict; (4) case-b and case-d (independent runs/ artifacts); (5) the remaining two paper branches in either order. DECISIONS merge: D68 (fix branch) is chronologically last; keep D59–D67 entries verbatim, append a reconciliation note at each entry whose status the fix branch changed (e.g., any entry citing pre-FIX-2 bands). Exact DECISIONS conflicts: NEEDS-REPO-VERIFICATION.

### P3 detail
Machine-checkable constraints are partially enforced in code: W1 (C3 — convention only), M2bR (C4 — loader only). The no-Mauna-material rule is *facilitated* by the A10 freeze machinery (`model.py:141-164`) but nothing in the listings prevents a Mauna number from entering a manuscript artifact; honouring in the sections NEEDS-REPO-VERIFICATION. D-entry statuses versus reality cannot be judged from this package.

### P4 detail
67 test files, many fix-pass-pinned (`test_fix1_*.py` × 10) — these are implementation-coupled by design (they pin the fix surface, which is appropriate), but T10's five named gaps have no corresponding file. The expected counts (1346/5/1) and runtime: NEEDS-REPO-VERIFICATION; this channel ran nothing.

### P5 detail
`external_targets.py` provides a strong provenance pattern: the artifact is re-checked from stored rows with recomputed errors and stored-field cross-validation (`external_targets.py:88-124`) — the manuscript's van Bork numbers are regenerable *and* self-auditing, assuming `check_external_targets` is wired into CI/tests (NEEDS-REPO-VERIFICATION). Everything else — hashes, the Case E oracle, script-to-artifact maps — is outside this package.

---

## 4. Verified-correct list (coverage record)

1. **FIX-2 total-variance decomposition** (`debias.py:146-163, 195-263`): within/between split, `bias=True` covariance consistency, typed target keys preventing component/group collision, atomic per-draw commit (R2 fix), diag==std² preservation (K3-4 at `:238`). Correct.
2. **Group conditioning** uses the full-kernel Cholesky (`debias.py:227`, MAP analog `:327-341`); a group of all components reduces to the full posterior by construction. Correct.
3. **MAP full-posterior covariance** computed from summed kernel blocks, retaining cross-covariance (`debias.py:318-331`). Correct (driver correction to T2 confirmed).
4. **T3 shift cancellation** (`bms_star.py:639-646`). Correct.
5. **`compute_G_matrix` penalty** is strictly worse than max finite even for negative metrics (`bms_star.py:563-573`). Correct (the pre-fix `10*max` bug class is gone).
6. **`log_weight_ess`** per-column max subtraction, −inf/NaN semantics (`bms_star.py:466-491`). Correct; NaN vs absent-support distinction is sound.
7. **`hard_win_statistics`** order-free tie splitting (`bms_star.py:509-528`). Correct.
8. **`soft_transfer_weighted` joint log-space aggregation** (`aggregation_v3.py:426-444`); the global shift cancels exactly; pre-fix underflow class eliminated. Correct.
9. **Laplace τ-rescale identity** (`laplace_evidence.py:436-437`) and the Construction-I sweep shortcut (`:1077-1078`). Algebraically correct.
10. **MC/IS estimators**: mc adds +log V for occam=False (`laplace_evidence.py:530-531`); is subtracts log V for occam=True (`:692-694`); defensive proposal is exact ordinary IS with untruncated Gaussians + box indicator (`:571-581`). Correct conventions (module header `:169-174`).
11. **Bounds-aware Hessian inset** with width cap (`laplace_evidence.py:375-383`); eigenvalue clip accounting via `n_clipped` (`:272-287`). Correct and honestly propagated.
12. **`_select_start` order-independence for NaN runs** (`laplace_evidence.py:491-502`). Correct.
13. **`mixture_central_interval`** (`decompose.py:125-160`). Correct.
14. **Hellinger formulas**: `_scalar_hellinger` (`bms_star.py:133-137`) matches the standard univariate Bhattacharyya form; the v2 4σ²→8σ² corrections (`metrics_v2.py:66-74, 98-113`) are the right fix.
15. **`pw_kl_vcal`** reduces to GP-uncertainty-weighted MSE exactly as section 2 claims (`metrics_v2.py:43-55`); the shared-scalar-variance/ML-refit correspondence stated in 02-machinery follows from `induced_prior.py:251-254` / `laplace_evidence.py:142-145` (isotropic σ²I candidate covariance). Correct.
16. **A4 guard logic** (`bms_star.py:718-745`): untagged-allowed, mixed-rejected. Correct as far as it goes (see C5).
17. **AdditiveGPModel single-registration fix** (`model.py:26-35`) — double-counted priors eliminated. Correct.
18. **Single-kernel site-name handling** in `select_hmc_sites`/`apply_hp_value` (`model.py:85,110-120`). Correct, guarded to the exactly-one-component case.
19. **`external_targets.check_external_targets`** recomputation-before-trust design (`external_targets.py:88-124`). Correct; the NaN-validation-before-min fix (R9) is right.
20. **Expected-posterior aggregation** (`bms_star.py:703-708`) matches van Bork Eq. 4 as stated: per-draw normalization then averaging; row-min shift inside is an exact stabilizer. Correct.

---

## 5. Recommendations (priority order)

1. **[BLOCKER, 3–5 days] Quantify the T1 surrogate gap on the paper configurations.** Add a per-draw-average Ḡ path reusing `compute_G_matrix`; run both on the N=20 toy and case spaces across τ ∈ [0.1, 100]; report the discrepancy per committed Z_M/posterior number or prove a bound. Unblocks: manuscript claim fidelity for sections 2/4/5; closes #40's open ledger item substantively rather than rhetorically.
2. **[BLOCKER, 4–6 days] Execute the P2 merge plan** (fix branch → case-e → case-a → case-c → b/d → rest), with the four API adaptations enumerated in §3-P2 applied to each case script and a green suite after each merge. Unblocks: a single buildable manuscript tree; D-ledger reconciliation.
3. **[BLOCKER, 2–3 days] FIX-2 inheritance sweep (P1-b).** Grep every manuscript/poster band for provenance through `decompose_model_hmc`/`decompose_model_mcmc`; mark or regenerate each; add the marking to the affected sections. Unblocks: retraction-risk removal for the D58 poster statements.
4. **[MAJOR, 1–2 days] Close C6/C7 sentinel tails**: raise on all-failed G matrices and all-failed induced-prior rows; pin with tests. Unblocks: the last silent-uniform paths on the scoring route.
5. **[MAJOR, 1 day] Surface weight_ess** with a warning threshold (mirroring `is_log_Z_Mx`, `laplace_evidence.py:696-701`) and include it in every soft-transfer table per section 2's reporting rule. Unblocks: T4 closure; referee-proofing of concentration claims.
6. **[MAJOR, 1–2 days] n_eval sensitivity note (T5)**: rerun one load-bearing comparison at n_eval ∈ {30, 60, 120}; add a manuscript sentence and a tolerance test. Unblocks: the only unexamined discretization on the paper path.
7. **[MAJOR, 0.5 day] Withdrawn-cache hygiene (C4)**: remove or quarantine the two M2bR artifacts so the loader guard is not the only barrier; add a CI grep test. Unblocks: T7 closure.
8. **[MINOR, 0.5 day] Record draw-mean noise_var (C8)** and rename `samples`/`samples_kind` (C10, the deferred pass-2 `metric_name` requirement and provenance prose with it). Unblocks: order-independent decomposition metadata.
9. **[MINOR, 0.5 day] Docstring roster fix (C12)** and explicit `metric_names` on every manuscript-facing `run_bms_star` call (C9). Unblocks: import-history-independent rosters.

---

## 6. Commands run and outcomes; what I could not run

**Commands run: none.** This channel received a package of listings only, under a package-only override; no shell, no interpreter, no repository access. Accordingly:

- **The test suite was NOT run.** The protocol's expected counts (1346 passed, 5 skipped, 1 failed = dependency-lock drift) and runtime are NEEDS-REPO-VERIFICATION; I report no counts of my own.
- **Not run, and why it matters:** (a) any probe of `bistar_gp.__file__` / the editable-install path trap — so no C1–C12 finding carries an execution transcript; each is argued from the cited lines and marked CONFIRMED-by-inspection (logic readable end-to-end in the listings) or PLAUSIBLE; (b) the van Bork artifact check (`check_external_targets`) against `runs/vanbork_external_validation/results.json` — the artifact is not in the package; (c) T9's `experiments/toy_debias_demo.py` — file not included; (d) all P1 per-section number provenance, P2 paper-branch script contents, P3 ledger entries D59–D68, P4 test contents (names only), P5 runs/ artifacts, hashes, and the Case E oracle; (e) the driver observation under T1 (RuntimeWarnings in `test_prior_stage_flows_to_finite_is_log_Z_Mx`) — confinement to stress inputs unresolved; the code path now raises on non-finite means before the matmul (`aggregation_v3.py:82-86`), so the warning may predate the fix — NEEDS-REPO-VERIFICATION.
- **What was done instead:** complete line-level reading of the nine listed modules (bms_star.py, aggregation_v3.py, laplace_evidence.py, debias.py, decompose.py, metrics_v2.py, config.py, induced_prior.py, external_targets.py, candidates.py, model.py), the notation file, the machinery specification, the review standard, and the 67 test file names; every algebraically checkable identity in §4 was re-derived by hand.

Signed: **Kimi K3 (package-only channel)**
