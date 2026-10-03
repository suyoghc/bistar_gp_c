## 1. Verdict

**REVISE:** retain the pass and repair the confirmed failure-handling, accumulation, numerical-stability, and validation gaps before committing; the core corrected mathematics and the Case E byte-identity oracle pass independent checks.

## 2. Findings on (a)

Reviewed the uncommitted `fix/code-review-2026-09` tree based on `71540836`, against the work order, revision-3 ledger, review/cross-check documents, notation, methods specification, and HANDOFF §2. Source references below point to `/Users/sc8918/Documents/GitHub/bistar_gp_c-fix`. No newly incorrect current manuscript artifact was established, so none of these findings is S1.

For reproduction commands, define:

```sh
S=/private/tmp/claude-501/-Users-sc8918-Documents-GitHub-bistar-gp-c/c59de7f7-0de6-4670-81b4-02e7226015e7/scratchpad/fix1_review/codex
```

Every finding below is **CONFIRMED** by my execution. The probes and corresponding `.log` files are in `$S`; no implementation changes were made.

| ID | FIX | Severity | Status | Path:line | Claim |
|---|---|---|---|---|---|
| R1 | 1 | S2 | CONFIRMED | [aggregation_v3.py:385](/Users/sc8918/Documents/GitHub/bistar_gp_c-fix/bistar_gp/aggregation_v3.py:385) | The new unknown-site error is swallowed and becomes `-inf`. |
| R2 | 2 | S2 | CONFIRMED | [debias.py:175](/Users/sc8918/Documents/GitHub/bistar_gp_c-fix/bistar_gp/debias.py:175) | Non-strict decomposition retains partially recorded failed draws. |
| R3 | 2 | S2 | CONFIRMED | [debias.py:154](/Users/sc8918/Documents/GitHub/bistar_gp_c-fix/bistar_gp/debias.py:154) | String accumulator keys collide with legal component names. |
| R4 | 3 | S4 | CONFIRMED | [bms_star.py:559](/Users/sc8918/Documents/GitHub/bistar_gp_c-fix/bistar_gp/bms_star.py:559) | Required metric identity remains optional, contrary to the work order. |
| R5 | 3 | S2 | CONFIRMED | [bms_star.py:590](/Users/sc8918/Documents/GitHub/bistar_gp_c-fix/bistar_gp/bms_star.py:590) | Class validation admits mismatched label/probability lengths. |
| R6 | 3, 6 | S2 | CONFIRMED | [aggregation_v3.py:426](/Users/sc8918/Documents/GitHub/bistar_gp_c-fix/bistar_gp/aggregation_v3.py:426), [bms_star.py:464](/Users/sc8918/Documents/GitHub/bistar_gp_c-fix/bistar_gp/bms_star.py:464) | Large finite offsets corrupt weighted normalization and ESS. |
| R7 | 5 | S2 | CONFIRMED | [laplace_evidence.py:335](/Users/sc8918/Documents/GitHub/bistar_gp_c-fix/bistar_gp/laplace_evidence.py:335), [:577](/Users/sc8918/Documents/GitHub/bistar_gp_c-fix/bistar_gp/laplace_evidence.py:577) | Optimizer handlers swallow strict evaluation failures. |
| R8 | 5 | S2 | CONFIRMED | [laplace_evidence.py:414](/Users/sc8918/Documents/GitHub/bistar_gp_c-fix/bistar_gp/laplace_evidence.py:414), [:366](/Users/sc8918/Documents/GitHub/bistar_gp_c-fix/bistar_gp/laplace_evidence.py:366), [:468](/Users/sc8918/Documents/GitHub/bistar_gp_c-fix/bistar_gp/laplace_evidence.py:468) | NaN selection and diagnostic propagation remain inconsistent. |
| R9 | 8 | S2 | CONFIRMED | [external_targets.py:67](/Users/sc8918/Documents/GitHub/bistar_gp_c-fix/bistar_gp/external_targets.py:67), [:94](/Users/sc8918/Documents/GitHub/bistar_gp_c-fix/bistar_gp/external_targets.py:94) | The target checker accepts a NaN posterior column. |
| R10 | 2/tests | S4 | CONFIRMED | [test_fix1_decomposition.py:117](/Users/sc8918/Documents/GitHub/bistar_gp_c-fix/tests/test_fix1_decomposition.py:117) | Tests miss deletion of all between-draw off-diagonal covariance. |

**R1 — Site validation does not escape the MLL routine.** `apply_hp_value` returning False raises at lines 359–362, inside a `try` whose handler converts `ValueError` to `-inf`. This defeats FIX-1's required site error and permits subsequent weighting to exclude the draw without identifying the bad site.

Command: `python -B "$S/probe_failures.py"`.

```text
Computed 0/1 valid log marginal likelihoods
MLL_UNKNOWN_SITE [-inf]
```

The sample contains `covar_module.kernels.0.alpha_prior`. Move site application outside the numerical-factorization handler, or give assignment failures a distinct exception that must escape it. Add an MLL-specific unknown-site test asserting the exception and site name; the extractor-only test does not exercise this handler.

**R2 — Accumulation is not atomic per draw.** `_DrawAccumulator.add_draw` appends each component immediately; `self.n` increments only after all components/full/groups succeed. The HMC wrapper catches a later `RuntimeError` and continues without rolling back those writes. A failed draw therefore contaminates some summaries while the retained count excludes it.

Command: `python -B "$S/probe_decomposition.py"`; inject failure on the second conditional calculation of the first draw.

```text
PARTIAL_DRAW retained 1 dropped 1 component_rows {'a': 2, 'b': 1, 'c': 1} full_rows 1
PARTIAL_DRAW_VARIANCE_MISMATCH 0.6206123700812902
```

The last number is `max(abs(diag(cov) - std**2))` for component `a`. Compute all targets into a temporary record for one draw, then commit the whole record. Add failure-after-first-component and failure-in-group tests; assert every row count equals the retained count and compare with a run containing only the successful draw.

**R3 — Internal target names are not collision-safe.** Components use their names as dictionary keys; groups use `','.join(names)`; the full posterior uses `'__full__'`. The model API does not reserve these strings. With components `['a', 'b', 'a,b']` and requested group `['a', 'b']`, a component and a different random quantity share the same accumulator.

Command: `python -B "$S/probe_decomposition.py"`.

```text
GROUP_NAME_COLLISION n_draws 2 component_rows 4 group_rows 4 component_equals_group True
```

Use tagged tuple keys, for example `('component', name)`, `('group', tuple(names))`, and a distinct full-posterior key; also reject duplicate group members. Pin names containing commas and `'__full__'` against direct conditioning. No public signature change is necessary.

**R4 — The metric requirement was replaced by a different policy.** FIX-3(b) says `soft_transfer` requires `metric_name`. The implementation accepts None and stamps `'unspecified'`; the new test explicitly requires that behavior at `tests/test_fix1_diagnostics.py:75`. This is an unadjudicated work-order deviation, not a demonstrated probability error.

Command: `python -B "$S/probe_failures.py"`.

```text
METRIC_OMITTED unspecified
```

There is a real instruction conflict to resolve: existing calls omit the metric, including `bistar_gp/metrics_v2.py:398`, `bistar_gp/mcse_strategy.py:177`, and the unchanged aggregation tests. Merely making the argument mandatory would break those contracts. The review disposition should explicitly authorize either a caller migration to a required keyword or a documented legacy exception to the work order. For the required-keyword route, pin omitted/None rejection and a supplied-name serialization round trip; do not claim the current omission test pins FIX-3 as written.

**R5 — Class validation checks uniqueness but not cardinality.** Comparing `len(set(class_names))` with the instance count allows extra duplicate labels whenever the unique count happens to match.

Command: `python -B "$S/probe_failures.py"`; two instances and `class_names=['A','B','B']`.

```text
CLASS_LENGTH (['A', 'B', 'B'], [0.4535508968392993, 0.5464491031607007])
```

Require `len(instance_names) == G.shape[1]`, `len(class_names) == G.shape[1]`, and unique class labels for the supported one-to-one mapping. Add this extra-label fixture alongside the existing same-length grouping rejection.

**R6 — Log space alone does not prevent cancellation.** Weighted posteriors subtract two large log-sum-exp values without first removing their common offset. ESS similarly subtracts almost equal large quantities. With nine identical draws, equal candidates must have posterior `[0.5,0.5]` and ESS `[9,9]` at every common score offset.

Command: `python -B "$S/probe_failures.py"`; `G=np.full((9,2), offset)`, `tau=1`, zero log weights.

```text
UNIFORM_ESS_1000000000000.0 [9.00036944 9.00036944]
WEIGHTED_EQUAL_G_1000000000000.0 ([0.500015973347615, 0.500015973347615], ...)
UNIFORM_ESS_1e+16 [1. 1.]
WEIGHTED_EQUAL_G_1e+16 ([1.0, 1.0], [1.0, 1.0])
```

Form the joint log contributions, subtract one global maximum before aggregating candidate scores, and normalize the resulting moderate log scores. For ESS only, subtract each column's maximum before calculating its ratio. Never apply separate column shifts to posterior scores. Add large-offset normalization, ESS bounds, and shift-invariance pins. Correct the misleading explanation at `bms_star.py:456`: a column factor cancels within that column's ESS, not across candidate posterior normalization. Canonical unweighted `soft_transfer` arithmetic need not change.

**R7 — Strict evaluation errors are mistaken for optimizer errors.** A predictor that succeeds at the starting point and Hessian stencil but raises at L-BFGS-B's `1e-8` finite-difference point causes `compute_G_at_params` to raise correctly. `_laplace_log_integral` catches that error as though the optimizer itself failed, re-evaluates the valid starting point, and returns finite evidence. `_multistart_G_optima` has the same problem.

Command: `python -B "$S/probe_failures.py"`.

```text
OPT_EVAL_FAILURE_STRICT_True (0.9189385332046727, False, ...)
ORDINARY_EVAL_FAILURE_STRICT (-0.7546864996220103, False, ...)
IS_EVAL_FAILURE_STRICT ([0.5601627852778468], [36.67334126964317], 1, ...)
```

The records contain the predictor exception, but strict mode did not raise. This differs from the intentionally supported, flagged fallback after a genuine optimizer-only failure. Use a distinct evaluation exception and re-raise it through both optimizer handlers. Keep ordinary optimizer failures recorded as requested. Also fix `compute_G_at_params:149`: a metric raising `RuntimeError` escapes even with `strict=False` (`METRIC_RUNTIME_NONSTRICT RAISED RuntimeError metric runtime failure`). Add partially failing predictors and multiple metric exception types; the always-raising fixture cannot expose the fallback defect because re-evaluating its start raises again.

**R8 — Non-strict NaNs are not handled consistently.** Three independently reproduced cases remain:

Command: `python -B "$S/probe_failures.py"`.

```text
NAN_START_ORDER_[{'a': -0.5}, {'a': 0.5}] (nan, nan, {'a': -0.5}, 1)
NAN_START_ORDER_[{'a': 0.5}, {'a': -0.5}] (0.0, 0.9189385332047829, {'a': 0.5}, 1)
HESSIAN_NAN_CONVERGED (nan, True, 0, {'success': True, ...})
MC_NAN_ESS ([nan], [0.0])
```

A NaN first start becomes the absorbing “best” because subsequent finite values cannot compare less than NaN. A predictor failing only on the Hessian stencil produces NaN evidence with `converged=True` and zero failed starts. `_weight_ess` maps a NaN total to the same zero used for legitimately absent support. The existing non-strict test explicitly pins that zero at `tests/test_fix1_sentinels.py:70`.

Select among finite start results explicitly, with an order-independent all-invalid outcome. Validate the Hessian before decomposition; preserve the optimizer's actual record while marking the integral invalid. Return NaN ESS for invalid evaluations and retain zero only for all-`-inf` support. Pin both start orders, stencil failure, and NaN versus absent-support ESS. I did **not** reproduce a NaN becoming a finite winning model posterior through `model_posterior`'s final softmax; that stronger allegation is not a finding.

**R9 — NaN defeats the external-target assertions.** Python's `max(finite_error, nan)` can retain the finite first argument. The preceding mass check also passes because `abs(nan-1) > tolerance` is False. Replacing the second model's minimum-tau probability by NaN therefore preserves the reported success. A NaN stored error field similarly passes its comparison.

Command: `python -B "$S/probe_failures.py"`; corrupted files are `$S/target_A_nan.json`, `$S/target_B_nan.json`, and `$S/target_stored_nan.json`.

```text
TARGET_NAN_A {'A': 0.0, 'B': 6.404745348520535e-07}
TARGET_NAN_B {'A': 0.0, 'B': 6.404745348520535e-07}
TARGET_STORED_NAN {'A': 0.0, 'B': 6.404745348520535e-07}
```

Validate all selected probabilities and supplied stored error fields as finite before mass checks or reductions. Pin corruption of each column separately, including NaN in both column orders. Keep the independent error recomputation; it is useful.

**R10 — The covariance pin is incomplete.** I replaced only `between_cov = np.cov(M, rowvar=False, bias=True)` with `between_cov = np.diag(M.var(axis=0))` in memory, leaving repository files untouched.

Command: `python -B "$S/probe_test_mutant.py"`.

```text
MUTATION: discard every off-diagonal between-draw covariance, leaving marginal variances correct
10 passed, 205 warnings in 0.31s
```

The current implementation is correct on this point; the test is inadequate. Compare the entire component/full/group covariance against independently conditioned matrices plus an explicit outer-product covariance of conditional means. My independent fixture has nonzero between-draw off-diagonals, so this is not a vacuous requirement. The all-component interval comparison at test lines 130–135 also compares the same object with itself; retain that API identity test, but supplement it with CDF coverage computed from independent group moments.

## 3. Recommendations on (b)

Costs below are estimates of code touched/net change, not proposed patches. “KEEP” still permits the specific missing tests above.

| Item | Explicit judgement on (a) | Recommendation on (b) |
|---|---|---|
| FIX-1 | Partial: single-kernel and raw-name fixes work; MLL site enforcement fails R1. | SIMPLIFY IN PLACE |
| FIX-2 | Core moments, conditioning and quantiles are correct; R2/R3 and R10 remain. | SIMPLIFY IN PLACE |
| FIX-3 | Ordinary diagnostics work; R4/R5/R6 prevent full compliance. | SIMPLIFY IN PLACE |
| FIX-4 | Correct exponents and candidate-aware firewall placement. | KEEP |
| FIX-5 | Genuine optimizer records and negative-metric penalty work; R7/R8 remain. | SIMPLIFY IN PLACE |
| FIX-6 | Underflow fixture and posterior weighting work; large-offset normalization fails R6. | SIMPLIFY IN PLACE |
| FIX-7 | Required metric roles and registered-path cache refusals work. | KEEP |
| FIX-8 | Closed forms and finite corruption checks work; NaN validation fails R9. | SIMPLIFY IN PLACE |
| FIX-9 | All three conventions match the required arithmetic. | KEEP |
| `__init__` | New exports resolve; existing exports remain. | KEEP |
| Overall | Valuable, substantially correct repairs with bounded remaining defects. | SIMPLIFY IN PLACE; do not delete and reimplement the pass. |

**FIX-1.** Keep the small `PredictiveList` subclass: approximately 20 lines buys the required list compatibility and extraction provenance. Treat its metadata as the history of extraction, rather than trying to update it through every subsequent list mutation. Move MLL assignment outside its numerical handler; if sharing assignment code, use a small `_apply_selected_sites(...)` helper without unifying raw MCMC and constrained Pyro values. Roughly 10–25 lines touched, no new public API, a few targeted tests, low oracle risk because successful setter order need not change.

**FIX-2.** Keep the accumulator architecture and separate MAP/draw numerical paths. Refactor `add_draw` into “condition every target for this draw, then commit”; use typed keys. A temporary collection of full matrices for **one** draw meets the memory requirement, unlike retaining every draw's matrices. Consolidate repeated `ComponentResult` packaging into a small summary constructor or factory, preserving MAP's function samples, random-number consumption, existing variance floors, and sum order. Approximately 40–80 lines touched, potentially 15–35 net fewer after consolidating packaging; no public signature or seven-field dataclass change. Add 4–6 meaningful tests. Oracle risk is low if low-level conditioning and MAP sampling stay unchanged; rerun the byte oracle after the refactor.

The `samples` alias needs explicit deprecation documentation. Its retention has a concrete compatibility reason: the read-only poster driver writes `comp.samples` at `experiments/poster_d58_mauna.py:477` and reconstructs with the `samples=` keyword at line 541. Do not remove that contract merely to reduce fields. The work order's narrower “editable caller” exception and the actual preserved poster contract should be reconciled explicitly in the report.

**FIX-3.** Keep the four appended optional result fields and the exact-tie helper. Share a private, centered log-weight ESS helper with weighted aggregation; add cardinality checks. This is roughly 15–30 lines touched, no required result-schema changes, and a few diagnostic/contract tests. Resolving R4 is separate: enforcing a required metric needs mechanical migrations, including callers outside the editable set, or an explicit legacy exception. A source scan found two package, three experiment, and eleven test call expressions omitting the metric. Treat that scope honestly. Probability arithmetic and the Case E oracle need not change.

**FIX-4.** The two denominator corrections and early firewall calls are already the right size. Keep them. Add a counting metric to the existing firewall test so “before any metric call” is asserted, not just eventual rejection. Approximately 5–10 test lines; no API or oracle risk. My counting probe confirms the implementation currently calls the metric zero times on rejected rosters.

**FIX-5.** Keep the explicit trailing `strict` arguments; nine-function plumbing is not itself a reason to introduce a policy object or ambient global state. Factor only the repeated optimizer-start/record logic, with a distinct `EvaluationFailure` that optimizer fallback handlers cannot swallow. Make start selection and invalid-Hessian/ESS handling explicit. Roughly 40–70 lines touched, little net growth, no new public API beyond what this pass already adds. Add partially failing predictor, metric-exception, NaN-order, and stencil tests. Preserve genuine optimizer fallback and successful numerical operation order. Keep `_fit_mle(return_status=True)` and `_select_restart`: their size is reasonable and successful-start preference is correct. Case E does not use the Laplace evidence path; existing evidence-value tests remain essential.

**FIX-6.** Keep explicit uniform/likelihood-tilted modes and the three caller corrections. Center joint log contributions as described in R6; share only the ESS helper, not the canonical unweighted arithmetic. Roughly 10–20 lines touched and 2–3 additional tests; no public signature change and no Case E arithmetic impact. `soft_transfer_weighted` also changes the scale of public `instance_scores`: the compatibility probe gives old `[0.56766764, 0.68393972]`, new `[0.8299966, 1.0]` for a representable fixture. Its posterior difference is only `5.55e-17`. No paper consumer of that score scale was established, so this is not a separate finding, but preserve the prior scale where feasible or explicitly report the rescaling rather than attributing it to underflow repair.

**FIX-7.** Keep the two-entry `WITHDRAWN_CACHES` tuple and small path predicate; a provenance database or cache-class hierarchy would be disproportionate. It is a path guard, not an authenticator of arbitrary copied cache contents. Keep lazy `_resolve_metric`: eager registration would change the implicit metric roster for previously untouched calls. Its swallowed `ImportError` could be removed to expose genuine import faults more clearly; that is an optional few-line cleanup. No public API change, minimal test churn, no oracle risk.

**FIX-8.** Keep the constants, beta-density closed form and independent recomputation. Add finite-value validation before reductions, optionally through a private `_validated_min_tau_row(...)` helper. Roughly 10–20 lines touched, no public API changes, 2–4 corruption tests, no oracle risk. The roughly 100-line module does not warrant a rewrite.

**FIX-9 and exports.** Keep the modest duplication of pooled arithmetic for this bounded pass. Delegating conventions through `soft_transfer` would unnecessarily couple a probability-only operation to result metadata, diagnostics and the unresolved metric contract. A future private `_pooled_scores` helper could remove approximately 10–15 lines, but must preserve dtype handling and the exact operation order. There is little benefit now relative to regression-test churn. Keep the straightforward exports.

**Overall.** The better version is this implementation with smaller, explicit failure boundaries and safer accumulator state. A wholesale rewrite would discard verified mathematics, duplicate the compatibility work, and enlarge the risk to pinned contracts without resolving a fundamentally different design problem.

The report's named deviations are mostly justified:

- **Mauna script call sites:** passing `groups=INTERPRETATION_GROUPS` at lines 393 and 428 is necessary for the newly correct grouping function. This exceeds the literal “grouping function only” edit boundary, but is the minimal supporting call-site change. No Mauna inference or figure regeneration was performed in this review.
- **On-demand metric registration:** necessary for config-driven primary-metric calls; the cold-process test verifies it. Keep it lazy.
- **Appending the primary metric:** justified by `experiments/bms_star_toy.py:204`, which slices `metrics[:4]`.
- **Scratch oracle symlink:** justified. I independently verified the copied script equals `paper/case-e-debias`, resolved the scratch package symlink to the fix tree, and reproduced all three hashes.
- **`FIX1_FIXTURE_DIR`:** reasonable for branch-only fixtures during this review. Both fixture tests were enabled in my suite. Long-term CI must provide them or deliberately distinguish optional integration coverage. Once a fixture is supplied, the blanket import-exception skip at `tests/test_fix1_conventions.py:148` should fail rather than silently remove that coverage. Embedded target values and arithmetic tests still run without the fixtures.

The report should additionally disclose R4, the `samples` compatibility exception, and the weighted score rescaling. Its claim that `extract_gp_predictives` newly gains `rng` is inaccurate: `rng` already existed at the base commit; `strict` is the new argument.

## 4. Verified-correct list

- **Sites and draw contracts:** separate single-kernel lengthscale and outputscale changes alter both means and covariances. Current/legacy additive assignments, raw-parameter permutation invariance, strict Cholesky rejection, non-strict drop accounting, `_sir_bms` short-list rejection, and existing likelihood-connectivity tests pass. MCMC raw values are not routed through constrained setters.
- **Decomposition mathematics:** independent NumPy kernel formulas and `solve`, without package decomposition helpers, agree with component, proper-subset group, and full means/covariances to at most `2.78e-16`. Both within-draw covariance and the full covariance of conditional means are present. One Cholesky of the entire training covariance plus noise serves every target (`debias.py:171`). Full covariance is exposed as `result.full.cov` without changing the seven dataclass fields.
- **Intervals:** the Gaussian and asymmetric-mixture checks pass. My asymmetric 90% interval has CDF endpoints `0.05000000000000002` and `0.9499999999999998`. Components, groups and full summaries call the same ported mixture-CDF construction. Singleton/all/empty group behavior is implemented; arbitrary groups must be requested during decomposition.
- **Diagnostics and conventions:** on `G=[[0,0],[10,11]]`, credit is `[0.75,0.25]`, attainment `[1,0.5]`, and tie fraction `0.5`. Low-temperature pooled, rowmin and expected-posterior results are respectively `[0.5,0.5]`, `[2/3,1/3]`, and `[0.75,0.25]`. Ordinary-scale ESS pins pass. Diagnostic fields and metric identity survive a pickle round trip.
- **Hellinger and firewall:** both variants give `0.11750309741540454` for the unit-variance unit-mean-shift fixture; equality and rescaled-variance tests pass. A counting metric is never invoked before rejection through `compute_G_matrix`, `run_bms_star`, `score_averaged_gp`, robust aggregation or weighted aggregation. Same-universe and all-untagged fixtures pass.
- **Evidence and weighting:** genuine optimizer exceptions/non-success reach records; candidate restart selection prefers a successful restart. The corrected mixed-validity penalty is worse than every finite negative metric value. The required joint-weighting fixture gives `[0.59384548,0.40615452]`; uniform posterior averaging gives `[1.8,0.2]`. Finite-entry checks reject manually supplied bad means and covariance diagonals. Existing Laplace/Z-estimator value tests pass in the full suite.
- **Roles and external targets:** primary/appendix constants, implicit-only appendix warning, primary-metric lookup and both registered cache refusal/override paths pass. Cache tests use synthetic scratch data, not withdrawn empirical values. Valid external fixtures give A error `0.0` and B error `6.404745348520535e-07`; finite shifted-column corruption fails.
- **Compatibility:** the seven-field positional decomposition contract and poster keyword construction pass. `PredictiveList` supports ordinary list iteration, indexing, slicing, concatenation and copying; its extraction provenance is retained on the returned object. The four BMS fields are appended with defaults. All five new `__init__` exports resolve.
- **Bit preservation:** old-versus-new source-function probes give 100/100 exact score/posterior comparisons for each unweighted normalization setting, exact additive extraction, and exact MAP component samples/moments under the same seeds. The Case E JSON, PNG and README match byte-for-byte.
- **Refuted items stayed out:** the diff adds no E6 failure gate, gives no non-finiteness explanation for the historical all-finite BLAS warnings, and preserves canonical pooled arithmetic and `normalize_per_draw=False`. I did not reopen the decision-gated row-definition or manuscript-prose questions.

Public signature changes checked: extractor `strict`; decomposition `groups` plus MCMC/HMC `rng` and HMC `strict`; `soft_transfer.metric_name`; the evidence functions' trailing `strict`; `_fit_mle.return_status`; optional `compute_induced_prior.log_mlls` and `weighting`; `load_hmc_samples.allow_withdrawn`; and the script helper's `mass`. The changed ordinary call sites are `run_bms_star` passing the metric, the two Mauna decomposition calls requesting groups, and the three induced-prior calls selecting uniform weighting (`experiments/bistar_induced_prior.py:166,281`, `experiments/bistar_induced_prior_v2.py:172`). Candidate fit callers request status internally. Existing positional argument ordering is retained; the metric requirement's unresolved exception is R4.

These checks establish the named cases, not exhaustive bit identity for every conceivable caller.

## 5. Commands run and outcomes

The full suite was launched from the fix worktree with its required command. Environment changes only redirected writes and enabled the supplied fixtures:

```sh
export PYTHONDONTWRITEBYTECODE=1
export TMPDIR="$S/tmp"
export MPLCONFIGDIR="$TMPDIR/mpl"
export PYTEST_ADDOPTS="--basetemp=$TMPDIR/pytest"
export FIX1_FIXTURE_DIR=/private/tmp/claude-501/-Users-sc8918-Documents-GitHub-bistar-gp-c/c59de7f7-0de6-4670-81b4-02e7226015e7/scratchpad/fixpass1/fixtures
cd /Users/sc8918/Documents/GitHub/bistar_gp_c-fix
python -m pytest tests/ -q -p no:cacheprovider > "$S/suite.log" 2>&1
```

**Full suite: 1327 passed, 3 skipped, 1 failed, 569 warnings in 546.67 seconds (pytest display: 0:09:06).** The only failure was `tests/test_m2cr_environment_freeze.py::test_committed_dependency_lock_reproduces_at_head`, the expected dependency-lock drift; the failure excerpt shows an added `pypdf==6.14.2` in `pip_freeze`. The dependency lock and environment were not repaired or modified.

| Command/artifact | Outcome |
|---|---|
| `python -B "$S/probe_failures.py"` | Reproduced R1, R4–R9; exits 0 after printing each outcome. |
| `python -B "$S/probe_decomposition.py"` | Independent full covariance checks, separate single-site sensitivity checks, and R2/R3 reproductions; exits 0. |
| `python -B "$S/probe_compatibility.py"` | Base-commit function comparisons, list/dataclass/export checks and weighted score-scale comparison; exits 0. |
| `python -B "$S/probe_mathematics.py"` | Hellinger, mixture coverage, ties, three limits, posterior weighting, counting firewall and serialization checks; exits 0. |
| `python -B "$S/probe_test_mutant.py"` | In-memory wrong-covariance mutant: all ten new decomposition tests still pass in 0.31 s. Its pytest temporary directory was `$S/tmp/mutant_pytest`. |
| `git status`, `git diff --stat/--numstat`, targeted diffs, `git show 71540836:<source>` | Read-only inspection; final fix-tree status retains the original 15 modified and 10 untracked files. |
| `git show paper/case-e-debias:experiments/toy_debias_demo.py` | Equals the main-worktree script; script SHA256 `4d5fdfc571f416212c68021afd3e76595279b6ba0d40e1f2a52ee56cc17dffe9`. |

For the oracle, I copied that unchanged script to `$S/oracle/experiments/toy_debias_demo.py`, created `$S/oracle/bistar_gp` as a symlink to the fix package, and ran from `$S/oracle`:

```sh
/usr/bin/time -p python experiments/toy_debias_demo.py --out ../toy_debias_demo
```

It exited 0 in **61.55 seconds**; log: `$S/oracle.log`. Paired `shasum -a 256` comparisons with the main-worktree committed artifacts are recorded in `$S/oracle_sha256.txt`:

| Artifact | Matching SHA256 |
|---|---|
| `results.json` | `65c9ff5f14b9a5f3aca8267745d6b368d95b831e85a610f6844b74e1b33712bb` |
| `debias_figure.png` | `c1153549ca55d9d644804790ef9a4627f8d82bedd157ec348ecb519f551a4723` |
| `README.md` | `7096cd6e4d3d02f8971cee294fa3e50a2c7248272320e9cc72cfc45994f889af` |

No network, new dependencies, Mauna inference, git mutations, or stash access were used. All probe code, mutations, temporary files, corrupted fixtures and generated artifacts stayed in the authorized scratch directory. The only review output written under either worktree is `runs/code_review_2026_09/fix1_codex_review.md` in the main worktree.
