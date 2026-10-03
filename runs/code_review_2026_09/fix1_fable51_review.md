# Fix pass 1 review, Fable 5.1 channel (claude-fable-5-1, reasoning effort max), 2026-09-08

Review target: the uncommitted working tree of `/Users/sc8918/Documents/GitHub/bistar_gp_c-fix`
(branch `fix/code-review-2026-09`, HEAD `71540836`; 15 tracked files modified, +1126/-314;
untracked `bistar_gp/external_targets.py` and nine `tests/test_fix1_*.py`). Brief:
`docs/paper-sie-jmp/prompts/code-review-fix1-review.txt` with the three channel overrides
(output file, scratch directory, package-resolution trap). I did not open
`fix1_codex_review.md` or `fix1_synthesis.md`. The implementer's `fix1_report.md` was read as a
claim; every statement below that rests on it was re-derived. Zero writes outside the scratch
directory and this file; zero git mutations; read-only `git show` was used to fetch the case-A
fixtures and the pre-fix modules into scratch.

Every probe printed `bistar_gp.__file__` and asserted it starts with the fix worktree
(`probes/common.py`), so no probe exercised the editable install that points at the main
worktree.

## 1. Verdict

**APPROVE.** All nine fixes compute what the work order and the manuscript require on every
manuscript path: the Case E oracle reproduces byte-identically against the fix package
(my own rerun, 59.7 s, sha256 65c9ff5f / c1153549 / 7096cd6e), the pooled soft-transfer
arithmetic and the MAP decomposition are bit-identical to the pre-fix code, the toy candidate
fits behind E7 are bit-identical, and the suite is green apart from the known lock-drift
failure. The seven findings are S3/S4 (two opt-in-mode defects each fixable in three lines or
fewer, four hygiene items, one disclosed deviation awaiting an author disposition); none
changes a number.

## 2. Findings on (a)

| ID | FIX | Sev | Status | Location (fix worktree) | Claim |
|---|---|---|---|---|---|
| F1 | FIX-5 | S3 | CONFIRMED | `bistar_gp/laplace_evidence.py:414` | Under `strict=False`, `laplace_log_Z_Mx`'s best-start selection is order dependent when one start evaluates to NaN: starts `[good, bad]` give log_Z = 0.934, `[bad, good]` give NaN. |
| F2 | FIX-6 | S3 | CONFIRMED | `bistar_gp/induced_prior.py:208-212` | The pre-fix positional call `compute_induced_prior(space, draws, x_eval, log_mlls, ...)` now silently computes the uniform average (1.8 on the two-state fixture; pre-fix 1.9756); only a `logging.warning` marks the substituted estimator. |
| F3 | FIX-2 | S4 | CONFIRMED | `bistar_gp/debias.py:97-98`, `:153` | `group_key` keeps duplicate names, so a requested group `["a","a"]` double-counts the block (mean = 2 x mean_a, name `a+a`). |
| F4 | FIX-3 | S4 | CONFIRMED | `bistar_gp/bms_star.py:626` (raise at `:463`) | `soft_transfer` now raises `ValueError` on any non-finite G entry (pre-fix: silent uniform posterior for a NaN entry). An improvement in substance, but undisclosed, unpinned, and the message names `boltzmann_weight_ess`. |
| F5 | FIX-3 | S4 | CONFIRMED (disclosed) | `bistar_gp/bms_star.py:559` | `metric_name` optional ("unspecified") where the work order says required; two package callers outside the editable set omit it. Needs the author's disposition. |
| F6 | tests | S4 | CONFIRMED | `tests/test_fix1_external_targets.py:81`, `tests/test_fix1_conventions.py:139` | Two fixture-gated pins skip unless `FIX1_FIXTURE_DIR` is set; the plain suite reports 1325 passed / 5 skipped, not the 1327 / 3 of the report. Both pass with `git show` fixtures. |
| F7 | tests | S4 | CONFIRMED | `tests/test_fix1_sentinels.py:65-80` | `test_raising_predictor_yields_nan_not_a_win_under_non_strict` asserts less than its name: under `strict=False` the healthy model's posterior is NaN as well (`{'Good': nan, 'Bad': nan}`); the all-NaN semantics of a normalized comparison is neither asserted nor documented. |

No S1 or S2 finding. Nothing in the REFUTED list was implemented (section 4).

### F1, S3, CONFIRMED. Non-strict multi-start selection depends on start order

What is wrong. `laplace_log_Z_Mx` keeps `best` by `run[2] < best[2]` (`laplace_evidence.py:414`).
With `strict=False`, a start whose objective is NaN returns early from `_laplace_log_integral`
with `f_star = NaN` (`:341-348`). `NaN < x` and `x < NaN` are both false, so whichever run
comes first is kept: a NaN first start hides a finite later start, and a finite first start
hides a NaN later start. The returned `log_Z`, `converged`, and `phi_min` therefore depend on
the order of `starts`, while `n_starts_failed` is the same in both orders.

Reproduction (`probes/p2_laplace_nonstrict.py`, section A; predictor raises for `a < -0.5`,
GP mean `0.5x - 0.3`):

```
starts a=[0.5, -0.9]: log_Z=0.9341231533115104 G_at_min=0.0 converged=True n_starts_failed=1 phi_min={'a': 0.5, 'b': -0.3}
starts a=[-0.9, 0.5]: log_Z=nan G_at_min=nan converged=False n_starts_failed=1 phi_min={'a': -0.9, 'b': 0.0}
```

Under `strict=True` (the default) the same starts raise `RuntimeError: compute_G_at_params:
predict_fn of 'Lin' raised ZeroDivisionError ...` (section B), which is the intended
behaviour; the defect is confined to the opt-in mode, hence S3.

Suggested change (three lines at `:414`): prefer finite objectives, fall back to the NaN run
only when every start is NaN.

```python
finite = np.isfinite(run[2])
if best is None or (finite and not np.isfinite(best[2])) or (finite and run[2] < best[2]):
    best = run
```

Test to pin it (`tests/test_fix1_sentinels.py`): the two-start fixture above in both orders
gives identical `log_Z`, `converged=True`, and `n_starts_failed == 1`.

### F2, S3, CONFIRMED. A supplied `log_mlls` under the default weighting is discarded with a warning

What is wrong. `compute_induced_prior` now defaults to `weighting="uniform"` and, when
`log_mlls` is supplied anyway, logs a warning and ignores it (`induced_prior.py:208-212`).
The pre-fix signature made `log_mlls` the fourth positional argument, so every pre-fix call
pattern that passes MLL weights now runs a different estimator. For `fit_hmc` posterior draws
that substitution is the corrected answer (FIX-6b's point, and the three repository callers
were updated). For the one case where the tilt is right, prior draws with self-normalized
importance weights, the caller's explicit weights are dropped and the uniform average is
returned with no error. HANDOFF-code-review section 2, item 3 ("fallbacks that substitute a
different estimator") describes this class.

Reproduction (`probes/p3_misc.py`, section 1, two-state fixture, `kl_forward`):

```
legacy positional call G: [1.8 1.8] | uniform G: [1.8 1.8] | PRE-FIX same call G: [1.97560976 1.97560976]
LOG bistar_gp.induced_prior: compute_induced_prior: log_mlls are ignored under weighting='uniform' (correct for posterior draws)
```

Suggested change (shorter than the current branch): treat the combination as a conflict.

```python
if weighting == "uniform":
    if log_mlls is not None:
        raise ValueError("log_mlls supplied under weighting='uniform'; pass "
                         "weighting='likelihood_tilted' for prior draws or drop log_mlls "
                         "for posterior draws")
    mll_weights = np.full(n_draws, 1.0 / n_draws)
```

No repository caller passes `log_mlls` any more, so nothing breaks. Test:
`test_uniform_default_ignores_log_mlls_with_a_warning` flips to `pytest.raises(ValueError)`.

### F3, S4, CONFIRMED. Duplicate names in a requested group are double-counted

What is wrong. `DecompositionResult.group_key` sorts but does not deduplicate
(`debias.py:97-98`); `_DrawAccumulator.__init__` stores `list(key)` as the members (`:153`)
and `decompose_model` sums `_blocks_sum(km, key, ...)` over the raw key (`:308-310`). A
group `["a","a"]` therefore sums `K_a` twice.

Reproduction (`probes/p3_misc.py`, section 2, three-component MAP fixture):

```
group_key(['a','a']) = ('a', 'a') | group name: a+a | mean == 2*mean_a: True | mean == mean_a: False
```

No caller requests duplicates (`INTERPRETATION_GROUPS` lists are unique), so hygiene only.
Suggested change: `return tuple(sorted(set(names)))`; then `["a","a"]` resolves to the
singleton branch and returns the component. Test (`tests/test_fix1_decomposition.py`):
`res.group(["a","a"]) is res.components["a"]` and `decompose_model(..., groups=[["a","a"]])`
stores no group.

### F4, S4, CONFIRMED. `soft_transfer` now rejects non-finite G, undisclosed and unpinned

What is wrong. `soft_transfer` calls `boltzmann_weight_ess(G_effective, tau)` (`:626`), which
raises `ValueError("boltzmann_weight_ess requires finite G values")` (`:463`). The pre-fix
function returned the uniform posterior for a matrix with a NaN entry (its `total > 0` test
fails on NaN). The new behaviour closes a silent-wrong-answer path and matches the work order's
"validated finite scores", so the substance is right; but the report's signature/contract
list does not mention it, no test pins it, and the message blames a helper.

Reproduction (`probes/p3_misc.py`, section 3, `G = [[0,1],[nan,0.5],[0.2,0.3]]`):

```
new raises ValueError : boltzmann_weight_ess requires finite G values
pre-fix: [0.5 0.5]
```

Reach: `compute_G_matrix` always returns finite values (probe `p3b_port.py` section 7: a
singular draw under `kl_forward` gives the penalty 33.04, `finite: True`), and
`mcse_strategy._validated_inputs` rejects non-finite G before its `soft_transfer` call
(`mcse_strategy.py:73-74`), so the paper paths cannot hit it; only hand-built matrices can.
Suggested change: validate at `soft_transfer` entry with a message naming `soft_transfer`,
list the contract change in the report, and add a two-line `pytest.raises` test to
`tests/test_fix1_diagnostics.py`.

### F5, S4, CONFIRMED (disclosed). `metric_name` optional instead of required

The work order (FIX-3b) says `soft_transfer` "requires `metric_name`"; the pass made it
`Optional[str] = None`, stamped "unspecified" (`bms_star.py:559`, `:632`), and pinned that in
`test_soft_transfer_carries_diagnostics_and_keeps_probabilities`. The addendum to the report
discloses it and gives the reason: `bistar_gp/metrics_v2.py:398` and
`bistar_gp/mcse_strategy.py:177` call `soft_transfer(G, tau, names, ...)` without a metric and
neither file is in the editable set (verified by grep). The spirit of the item (no invented
identity) is met; the letter is not. Author disposition needed: accept the optional keyword
now and make it required in fix pass 2 together with the two callers, or record a documented
legacy exception. My recommendation is the former.

### F6, S4, CONFIRMED. Two pins skip in the plain suite

`test_driver_fixture_passes` and `test_matches_the_case_a_script_fixture` skip unless
`FIX1_FIXTURE_DIR` names a directory holding `vanbork_results.json` and
`e7_convention_sensitivity.py`. My plain run reported 1325 passed / 5 skipped / 1 failed; the
report's 1327 / 3 / 1 therefore came from a run with the variable set. With fixtures fetched
by `git show paper/case-a-vanbork:...` into scratch, both files pass (25 passed, 0 skipped,
2.76 s). The embedded `COMMITTED` rows and the inline `_case_a_aggregate` copy mean the
substance of both pins is still exercised without the variable, so the loss is one level of
independence, not coverage. Suggested: state the variable in the two test docstrings and in
the report's suite line, or fall back to a `git show` of the case-A branch when that branch
exists locally.

### F7, S4, CONFIRMED. A sentinel test asserts less than its name

`test_raising_predictor_yields_nan_not_a_win_under_non_strict` asserts
`np.isnan(mpr.posteriors["Bad"])`. Under `strict=False` the healthy model's posterior is NaN
too, because `softmax` over a kernel with one NaN entry returns NaN everywhere
(`probes/p2_laplace_nonstrict.py`, section D: `posteriors: {'Good': nan, 'Bad': nan}`). That
outcome is the honest one for a normalized comparison (no candidate wins), and I verified it
is not a silent-win path; but the test should assert the all-NaN semantics explicitly and the
`ModelPosteriorResult.all_converged` docstring should say that a non-strict failure in one
model voids the whole posterior.

## 3. Recommendations on (b)

Method: for each FIX I asked whether a shorter or more elegant implementation would have the
same behaviour on the pinned contracts, what it would cost in lines, API surface, risk to the
Case E byte-identity oracle and the pinned contracts, and test churn.

| FIX | Recommendation | Reason in one line |
|---|---|---|
| FIX-1 | KEEP | `PredictiveList` is the smallest carrier that still iterates as a list; the strict branches are verbose but explicit. |
| FIX-2 | SIMPLIFY IN PLACE (small) | One single-draw `ComponentResult` helper removes the MAP-path duplication with zero numerical change; `group_key` dedup (F3). No rewrite. |
| FIX-3 | KEEP | Two ten-line pure helpers, pinned; the class-name guard is four lines. |
| FIX-4 | KEEP | Two constants and one guard call. |
| FIX-5 | SIMPLIFY IN PLACE | Add the three-line finite-preferring selection (F1); keep the threaded flag; do not move the policy onto `ModelParameterSpace`. |
| FIX-6 | SIMPLIFY IN PLACE | Turn the warn-and-ignore branch into a raise (F2); the function gets shorter. |
| FIX-7 | KEEP (optional micro-simplification) | Registry and loader are the right size; `_resolve_metric` could become a `__missing__` on `METRICS` and cover every `METRICS[name]` site. |
| FIX-8 | KEEP | 108 lines with docstrings; three tiny Target B functions could be two, not worth churn. |
| FIX-9 | KEEP | Six duplicated lines guarded by a bit-identity test; DRY-ing buys nothing the test does not already guarantee. |
| Overall | KEEP, no rewrite | The pass should not be deleted and redone; fold the four small in-place edits (F1, F2, F3, F4) before commit and trim the provenance prose. |

### FIX-1 (sites and draw integrity): KEEP

`select_hmc_sites` gains one fallback line plus comment; `apply_hp_value` gains a guarded
branch that maps the bare `covar_module.<hp>` names to component 0 only when
`model.covar_module is model.kernel_components[0]` (`model.py:112-120`), exactly the work
order's condition. `PredictiveList` (`bms_star.py:222-241`, 14 lines of code) subclasses
`list`; pickling, deepcopy, slicing, `json.dumps`, and truthiness behave as for a list
(`probes/p3_misc.py`, section 4). Alternatives considered: returning a `NamedTuple` or a
dataclass with a `.samples` list (breaks every `len(gp_samples)` / `for s in gp_samples`
caller, 12 call sites); attaching attributes to a plain `list` (impossible). The three
`if strict: raise ... else: logger.warning(msg); continue` blocks in `extract_gp_predictives`
(`:321-361`) and the two in `decompose_model_hmc` could share a five-line local helper
(`_fail(msg, exc=None)`), saving about 15 lines; optional. `_raw_parameter_map` mirrors
`fit_mcmc_simple`'s own dedup-by-identity, first-name-kept walk (`fit.py:144-152`), so the
name matching is correct by construction and the permutation test pins it.

### FIX-2 (moments, groups, intervals): SIMPLIFY IN PLACE, small

The accretion named in the brief is real: `decompose_model` builds `ComponentResult` by hand
for components (`debias.py:264-276`), the full posterior (`:324-328`), and groups
(`:314-318`), each time with `n_draws=1`, `between_var=zeros`, and a `[None, :]` reshape,
while `_DrawAccumulator._finalize_target` (`:189-206`) builds the same object for draw paths.

Option A, route the MAP path through `_DrawAccumulator` (one `add_draw`, `finalize`, then
overwrite `samples`/`samples_kind` with the function draws). Cost: about 50 lines removed,
but the accumulator symmetrizes `cov` (`0.5*(c + c.T)`) and clips variances at 0 rather than
1e-10, so the MAP path would no longer be bit-identical to the pre-fix code; today it is
(`probes/p4_decomp.py`, section 4: all seven fields identical under the same torch seed). No
manuscript number depends on the MAP path (Case E uses `decompose_additive_gp` directly), but
the Mauna MAP mode and `impact_assessment.py` do. Not worth the risk for prose-free code.

Option B (recommended): one helper, zero numerical change, about 25 lines removed.

```python
def _single_draw(name, mean, cov, samples=None, kind="conditional_means", floor=1e-10):
    mean, cov = np.asarray(mean), np.asarray(cov)
    var = np.clip(np.diag(cov), floor, None)
    return ComponentResult(
        name=name, mean=mean, std=np.sqrt(var), cov=cov,
        samples=mean[None, :] if samples is None else samples, samples_kind=kind,
        conditional_means=mean[None, :], conditional_vars=var[None, :],
        within_var_mean=var, between_var=np.zeros(len(var)), n_draws=1)
```

The three MAP call sites and the empty-group branch of `DecompositionResult.group`
(`:110-119`) become one-liners. Keep `torch.clamp(..., min=1e-10)` on the component path so
the existing `std` values stay bit-identical (the helper reproduces it in numpy on the same
float64 values). Also apply the `group_key` dedup of F3.

`_DrawAccumulator` itself is the right shape: one Cholesky of the entire training covariance
per draw serving components, full posterior, and groups (`:171-186`), running sums instead of
stored matrices, population moments (`np.cov(..., bias=True)` agrees with `M.var(axis=0)`,
verified). `mixture_central_interval` is a faithful port: bit-identical to the script's
function on 60 random comparisons, and the only non-docstring differences are the
`n_iter=100` keyword, the shape/mass validation, and a 1-D promotion (`probes/p3b_port.py`).

### FIX-3 (diagnostics): KEEP

`boltzmann_weight_ess` and `hard_win_statistics` are pure, ten lines each, and match their
definitions to 1e-15 (`probes/p5_arith.py`, sections 2 and 3). Computing the ESS on
`G_effective` (the weights actually aggregated) and the tie statistics on the raw matrix is
the right split. The `class_names` guard is four lines. The `BMSStarResult` fields are
optional with `None` defaults, so every keyword construction elsewhere still works.

### FIX-4 (Hellinger, firewall): KEEP

Two exponents and two docstrings; one guard call at the boundary that still holds candidate
metadata, plus the explicit call in `score_averaged_gp`, which builds no G matrix. Nothing
to remove.

### FIX-5 (sentinels, provenance): SIMPLIFY IN PLACE

The brief names the `strict` flag threaded through nine functions. I considered three
alternatives.

1. Drop the non-strict mode (always raise). Removes the flag from nine signatures and six
   closures, the NaN early return in `_laplace_log_integral`, the identity-Hessian fallback in
   `_multistart_G_optima`, and two tests: about 60 lines less, and F1 disappears by
   construction. Cost: the work order asked for `strict=False`, and an exploratory stress run
   would have to catch exceptions itself. A legitimate REWRITE, but it deletes a requested
   surface.
2. Put the policy on `ModelParameterSpace` (`param_space.strict`), the object that owns the
   failing `predict_fn`. Removes all nine parameters. Cost: the policy becomes invisible at
   the call site and travels with a data object; a reviewer reading `model_posterior(...)`
   cannot see which mode produced the number. Rejected.
3. Keep the threading and fix the selection (F1, three lines). Recommended. The threading is
   the honest cost of an explicit per-call policy that no repository caller uses yet.

`OptimizerRecord` (`:196-213`) and `_optimizer_record` (`:315-322`) are 25 lines that replace
"nothing carried either fact to the caller"; `_select_restart` (`candidates.py:81-93`) is 12
lines and a no-op on the E7 fits (`probes/p1_candidates.py`: all 16 restarts of the two
multi-start models report success, fitted parameters bit-identical to the pre-fix code). The
7-tuple returned by `_laplace_log_integral` is at the edge of readability; a small
`_LaplaceRun` NamedTuple would cost 8 lines and make `best[2]` read `best.f_star`. Optional.

### FIX-6 (weighted aggregation, posterior weighting): SIMPLIFY IN PLACE

`soft_transfer_weighted` is now shorter than before (net -7 lines), exact, and matches the
pre-fix posteriors to 3e-16 in the representable regime while fixing the pinned underflow
case (`probes/p5_arith.py`, section 4). The `compute_induced_prior` weighting branch is 20
lines; making the `log_mlls`-under-uniform case a raise (F2) removes the warning branch and
its test scaffolding. `average_gp_posterior`'s entry validation is eight lines and names the
offending draw, as requested.

### FIX-7 (roles, withdrawn caches): KEEP, one optional micro-simplification

`PRIMARY_METRIC`, `APPENDIX_METRICS`, `WITHDRAWN_CACHES`, `is_withdrawn_cache` (12 lines) and
the loader guard are the right size. The guard is path-based, so a renamed copy of a withdrawn
cache passes; the work order asked for a path registry, so this is a documented limit, not a
finding. `_resolve_metric` (`bms_star.py:492-509`) fixes the lookup only inside
`compute_G_matrix`, while `METRICS[metric_name]` is also indexed directly in
`induced_prior.py`, `laplace_evidence.py` (six sites), and `aggregation_v3.py`. A
`dict` subclass would cover all of them in fewer lines (`metrics_v2` registers with one
`METRICS.update(...)`, which a subclass supports):

```python
class _MetricRegistry(dict):
    """METRICS[name] imports the v2 metrics on first miss (FIX-7)."""
    def __missing__(self, name):
        from . import metrics_v2  # noqa: F401  (registers into this dict)
        if name in self:
            return dict.__getitem__(self, name)
        raise KeyError(f"unknown metric {name!r}; registered: {sorted(self)}")
```

Cost: 8 lines replacing 18, `METRICS` stays a `dict` instance, `METRICS.keys()` semantics on
the implicit `run_bms_star` path unchanged (v2 names still appear only after the first
import, as today). Risk: nil to the oracle and contracts. Optional; the current form works.

### FIX-8 (external targets): KEEP

The checker recomputes both errors from the rows, cross-checks the stored field, validates
names and unit mass, and selects the smallest-tau row regardless of order. The three Target B
helpers (`vanbork_target_b_densities`, `_weight`, `vanbork_target_b`) could be two functions;
not worth churn.

### FIX-9 (aggregation conventions): KEEP

`aggregate_convention` duplicates the six-line pooled arithmetic of `soft_transfer`
deliberately, so that Cases A and C share the Case A script's exact operation order.
`probes/p5_arith.py` section 1 confirms all three of `soft_transfer(normalize_per_draw=False)`,
`soft_transfer(normalize_per_draw=True)` and `aggregate_convention` are bit-identical to the
pre-fix `soft_transfer` on 30 random matrices. Having `soft_transfer` delegate to
`aggregate_convention` for its posteriors would remove the duplication but would need the
helper to also return the unnormalized scores; the bit-identity test already guarantees what
DRY-ing would.

### Overall

KEEP the pass; fold F1 (3 lines), F2 (a shorter branch), F3 (1 line), F4 (an entry check and
a test line) into the same commit; consider the `_single_draw` helper and the metric-registry
`__missing__` as follow-ups. Two observations on size. First, roughly a third of the added
package lines are provenance prose: the package diff carries 18 added lines mentioning
"2026-09" and 26 mentioning "FIX-n". One line per function ("2026-09 review FIX-2") is
enough once `Notes/DECISIONS.md` records the pass; the docstrings should describe the
behaviour, not the review history. Second, the diff is +1126/-314 for nine fixes, 79 tests, a
new module, and four experiment updates; measured against the mandated surface (new result
fields, group conditioning, mixture intervals, optimizer records, a registry, three
conventions, closed forms) that is not large.

## 4. Verified-correct list

Mathematics (a)1.

- Law of total variance: `std**2 = mean_d(diag C_d) + Var_d(m_d)` with population moments;
  `cov = mean_d(C_d) + Cov_d(m_d)` via `np.cov(..., bias=True)`; `diag(cov)` agrees with
  `std**2` to 1e-16 and the total covariance is symmetric and PSD to round-off
  (`probes/p4_decomp.py`, sections 1-3; `tests/test_fix1_decomposition.py` pins the two terms
  against an independent per-draw computation). The pre-fix `std` equals the new
  `sqrt(between_var)` exactly (section 5), which reproduces the original finding's mechanism.
- Group conditioning uses the Cholesky factor of the entire training covariance plus noise for
  components, the full posterior, and every group (`debias.py:171-186`; MAP path `:288-310`
  with `L_sum` over all names). Pinned by `test_requested_pair_group_matches_direct_conditioning`
  and `test_map_groups_condition_on_the_full_factor`.
- Mixture central interval: CDF bisection over the equally weighted Gaussian mixture, 100
  iterations, bit-identical to `experiments/toy_debias_demo.py`'s function
  (`probes/p3b_port.py`); coverage checked on a Gaussian and an asymmetric mixture in
  `test_mixture_interval_helper_coverage`.
- Joint log-sum-exp in `soft_transfer_weighted`: pinned case `[0.59384548, 0.40615452]`
  reproduced; representable-regime agreement with the pre-fix code 3e-16; ESS matches
  `(sum w)^2 / sum w^2` on the joint terms.
- Hellinger: `1 - exp(-1/8) = 0.11750309741540454` for both variants; `D_B = delta^2/(8 sigma^2)`
  is the equal-variance Bhattacharyya distance.
- Boltzmann ESS in log space: matches the direct definition to 9e-16; column-shift invariant;
  finite under underflow.
- Exact-tie split credit: `G = [[0,0],[10,11]]` gives attainment `[1, 0.5]`, credit
  `[0.75, 0.25]`, limiting rowmin `[2/3, 1/3]`, limiting pooled `[1/2, 1/2]`, limiting
  expected-posterior `[0.75, 0.25]` (`probes/p5_arith.py`, section 2), the full ledger fixture.
- Three conventions: bit-identical to the Case A script's `aggregate` (fixture test run by me
  with the `git show` copy) and to the pre-fix `_boltzmann_posterior`; `prior_sensitivity_study`
  delegates.

Contracts (a)2.

- `DecompositionResult` keeps exactly the seven positional fields
  (`dataclasses.fields` pinned in `test_rebuild_contract_unchanged` and
  `tests/test_poster_d58_driver.py`); `experiments/poster_d58_mauna.py:544-552` rebuilds
  positionally and `:541` constructs `ComponentResult` with the five legacy keywords, which
  the new defaulted fields accept.
- `PredictiveList` behaves as the list it replaces (probe section 4).
- `BMSStarResult` additions are optional and defaulted; every constructor in the package uses
  keywords.

Regressions (a)3.

- Case E oracle: `experiments/toy_debias_demo.py` (sha256 4d5fdfc5, identical to the main
  worktree copy) run from scratch with `bistar_gp` symlinked to the fix package (realpath
  printed and verified), 59.69 s: results.json 65c9ff5f..., debias_figure.png c1153549...,
  README.md 7096cd6e..., byte-identical to the committed `runs/toy_debias_demo/` files.
- `soft_transfer`: posteriors and scores bit-identical to the pre-fix function on 30 random
  matrices under both `normalize_per_draw` values; default `False` unchanged.
- `decompose_model` (MAP): all seven fields bit-identical to the pre-fix code.
- Toy candidate fits (`build_toy_candidates().fit` on `generate_toy_data()`, the E7 inputs):
  bit-identical; all 16 restarts of the two multi-start models report success, so FIX-5c's
  preference rule changes nothing on that path.
- `fit_mcmc_simple` key schema matches `_raw_parameter_map` (dedup by identity, first name
  kept, `fit.py:144-152`).
- The practice single-kernel model is built with `build_model` (`practice_EvansEtAL/run.py:392`,
  reads `model.kernel_components[0]` at `:401`), so FIX-1a's `kernel_components` precondition
  holds on the Case D regeneration path.

`strict=False` propagation (a)4.

- `mc_log_Z_Mx` / `is_log_Z_Mx`: a NaN in `G` gives NaN `log_Z` and ESS 0 (`_weight_ess`
  returns 0 on a non-finite total); `model_posterior` gives an all-NaN posterior (no silent
  winner). A start pinned against a failure boundary gives a finite start-point expansion
  flagged `converged=False` with the optimizer record (`probes/p2`, section C), which is the
  pre-existing fallback now made visible. The one defect is F1.

Tests (a)5.

- Each new file fails against the pre-fix code on its central pin (single-kernel predictives
  identical, `std` equal to the between term, 1e6 sentinel finite, uniform fallback on
  underflow, `/4` exponents, missing config entries, no conventions function). The pins listed
  in the work order are all present, with the caveats F6 and F7.

Deviations (a)6.

- Mauna script call sites pass `groups=INTERPRETATION_GROUPS`: necessary, joint moments need
  the summed blocks at decomposition time.
- `_resolve_metric`: justified by `experiments/bms_star_toy.py:204` slicing
  `config.metrics[:4]` and handing the list to `run_bms_star` without importing `metrics_v2`;
  see FIX-7 above for a wider form.
- Appended primary metric: justified by the same slice.
- Oracle through a scratch symlink: the only way to exercise the fix package with a script
  that inserts its own parent at `sys.path[0]`; I used the same method.
- `FIX1_FIXTURE_DIR`: see F6.
- `metric_name` optional: see F5.
- `samples` retained rather than aliased: justified by `poster_d58_mauna.py:477`, outside the
  editable set; `samples_kind` marks the meaning.

Refuted items (a)7, confirmed NOT implemented.

- No E6 failure gate: no E6 file in the diff (`git diff --stat`), and the E6 script is not in
  the fix worktree.
- No finiteness "explanation" of the `aggregation_v3.py:77` RuntimeWarnings: the only change
  near that line is the requested entry validation (`aggregation_v3.py:82-90`), whose messages
  name a draw and make no claim about the warnings.
- Pooled arithmetic and the `normalize_per_draw=False` default unchanged (bit-identity above;
  signature at `bms_star.py:555-559`).

## 5. Commands run and their outcomes

Scratch: `/private/tmp/claude-501/-Users-sc8918-Documents-GitHub-bistar-gp-c/c59de7f7-0de6-4670-81b4-02e7226015e7/scratchpad/fix1_review/fable51/`.

1. `cd /Users/sc8918/Documents/GitHub/bistar_gp_c-fix && python -m pytest tests/ -q -p no:cacheprovider`
   (`suite_full.log`): **1 failed, 1325 passed, 5 skipped**, 506.55 s (8 min 27 s; wall
   507.7 s, user 295.1 s). The failure is
   `tests/test_m2cr_environment_freeze.py::test_committed_dependency_lock_reproduces_at_head`
   (pre-existing lock drift). Skips: the two `FIX1_FIXTURE_DIR` tests (F6),
   `test_prior_sensitivity_figures.py:169` (machine-local artifacts absent),
   `test_m2cr_environment_freeze.py:624` (`M2CR_FULL_FREEZE_TESTS` unset),
   `test_e1_potential.py:652` (period only in the Mauna structure). Collected 1331.
2. `FIX1_FIXTURE_DIR=<scratch>/fixtures python -m pytest tests/test_fix1_external_targets.py tests/test_fix1_conventions.py -q -rs`:
   25 passed, 0 skipped, 2.76 s. Fixtures from `git show paper/case-a-vanbork:experiments/e7_convention_sensitivity.py`
   (sha256 4bbbc828...) and `git show paper/case-a-vanbork:runs/vanbork_external_validation/results.json`
   (sha256 e5596e2a...).
3. Same two files plus `test_prior_sensitivity_figures.py` and `test_m2cr_environment_freeze.py`
   without the variable, `-rs`: 51 passed, 4 skipped, 1 failed (skip identities above).
4. Case E oracle (`oracle/run.log`): script copied from the main worktree
   (sha256 4d5fdfc5 both sides), `bistar_gp` symlink to the fix package, package realpath
   printed as `/Users/sc8918/Documents/GitHub/bistar_gp_c-fix/bistar_gp/__init__.py`,
   `python toy_debias_demo.py --out <scratch>/oracle/out`, real 59.69 s, exit 0; the three
   sha256 values match the committed artifacts (section 4).
5. Probes (all under `probes/`, outputs in `p*.out`):
   `p1_candidates.py` (candidate fit regression and restart census),
   `p2_laplace_nonstrict.py` (F1, F7, boundary case),
   `p3_misc.py` (F2, F3, F4, `PredictiveList`, exports),
   `p3b_port.py` (mixture-interval port fidelity, `compute_G_matrix` finiteness),
   `p4_decomp.py` (FIX-2 moments, MAP bit-identity, pre-fix `std` mechanism),
   `p5_arith.py` (FIX-3/6/9 bit-identity and definitions).
   Pre-fix modules for comparison were extracted with read-only `git show HEAD:...` into
   `old/` (`bms_star_old.py`, `candidates_old.py`, `induced_prior_old.py`) and
   `debias.py` was loaded from `git show` output in memory.
6. Read-only git: `git status --short`, `git diff`, `git diff --stat`, `git show`, `git branch -a`,
   `git log -1 -- runs/toy_debias_demo/results.json` in the fix and main worktrees. No add,
   commit, stash, checkout, reset, branch, or rebase anywhere; `stash@{0}` untouched; no
   network; no Mauna Loa inference; no `pip`; dependency lock unchanged.
