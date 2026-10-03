# Independent code and project review, 2026-09-26

## 1. Verdict

**Code: REVISE.** The canonical results I replayed survive `ddf8c9d`, but reachable paths still manufacture evidence from failed evaluations, accept incomplete posterior draws, misrepresent decomposition samples, and produce an incorrectly normalized importance integral.

**Project: NOT READY for submission.** Resolve these blockers:

1. Reconcile the mathematical definitions of a GP pattern, averaged divergence, and per-pattern projection with the estimators actually used.
2. Correct the claim that normalized pooled probabilities preserve an absolute misspecification signal that expected-posterior reporting necessarily loses.
3. Assemble the seven branches, resolve their decision-log conflicts, and publish the manuscript apparatus and reproducibility dependencies under one immutable revision.
4. Close the remaining failure-handling defects and add independent pins for them.
5. Complete an integration test run in an environment where the suite's Git-mutating tests are authorized; disposition the dependency-lock drift without silently changing historical evidence.
6. Audit and mark the legacy uncertainty figures and associated prose affected by FIX-2; finish the author and assembly ledger.

I found **no new S1 error in the canonical manuscript numbers that I actually regenerated**. That conclusion does not validate unreplayed PSIS-LOO chains, missing local reach-check artifacts, or unidentified poster assets.

### Evidence conventions

Unqualified code paths and line numbers refer to `ddf8c9d`. `MAIN-local:` identifies untracked or working-tree manuscript material, not a committed release. Paper prefixes below identify these exact locally available remote-tracking revisions; no network verification of PR state was performed.

| Prefix | Branch | Head | Decision tail |
|---|---|---|---|
| A | `origin/paper/case-a-vanbork` | `76135be` | D60, D61, D65 |
| B | `origin/paper/case-b-occam-dial` | `32c0a58` | D62 |
| C | `origin/paper/case-c-haaf` | `0adde90` | D63 |
| D | `origin/paper/case-d-mopen` | `ff4c353` | D64 |
| E | `origin/paper/case-e-debias` | `a07e61e` | D67 |
| S | `origin/paper/synthesis-sections` | `096dd01` | D66 |
| F | `fix/code-review-2026-09` | `ddf8c9d` | D68 |

Commands below use:

```sh
R=/Users/sc8918/Documents/GitHub/bistar_gp_c-fix
M=/Users/sc8918/Documents/GitHub/bistar_gp_c
S=/private/tmp/claude-501/-Users-sc8918-Documents-GitHub-bistar-gp-c/c59de7f7-0de6-4670-81b4-02e7226015e7/scratchpad/proj_review/codex
export PYTHONPATH="$R" PYTHONDONTWRITEBYTECODE=1
export TMPDIR="$S" MPLCONFIGDIR="$S/mpl" XDG_CACHE_HOME="$S/cache"
```

The scratch probes print `bistar_gp.__file__`. Each resolved to `$R/bistar_gp/__init__.py`, avoiding the editable installation's MAIN-worktree target. Prior review reports supplied context; the findings below depend on source inspection, new probes, or regenerated artifacts.

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

## 3. Project findings

### Summary

| ID | Scope | Severity | Status | Location | Claim |
|---|---|---|---|---|---|
| P01 | P1 | BLOCKER | CONFIRMED | `MAIN-local:docs/paper-sie-jmp/00-notation.md:9`; `S:docs/paper-sie-jmp/02-machinery.md:44` | The common notation still combines different pattern and divergence estimands. |
| P02 | P1 | MAJOR | CONFIRMED | `A:docs/paper-sie-jmp/03-case-A-external-validation.md:129`; `S:docs/paper-sie-jmp/02-machinery.md:98` | The absolute-inadequacy argument overstates what normalized pooled probabilities retain. |
| P03 | P2 | BLOCKER | CONFIRMED | All seven branch decision tails; `C:experiments/haaf_nested_constraint.py:46` | No integrated revision exists; decision-log conflicts and the A-before-C import are demonstrable. |
| P04 | P3 | MAJOR | CONFIRMED | `A:docs/paper-sie-jmp/03-case-A-external-validation.md:159`; `S:docs/paper-sie-jmp/08-discussion.md:156` | W1 placement and several status/assembly statements remain inconsistent with the repository. |
| P05a | P1, P3 | MAJOR | CONFIRMED | `experiments/toy_example.py:87`; `MAIN-local:CogSci Poster/QA_PREP.md:218` | Legacy wrapper outputs inherit FIX-2; the thin-band explanation remains unqualified. |
| P05b | P1, P5 | MAJOR | PLAUSIBLE | Current poster layout and legacy asset selection | A displayed poster may still contain affected assets; no asset manifest established which version was selected. |
| P06 | P4 | MAJOR | CONFIRMED | `tests/test_fix1_external_targets.py:33`; `tests/test_m2cr_environment_freeze.py:533` | The suite provides useful mathematics checks but misses the new defects and lacks a complete review-compliant run here. |
| P07 | P5 | BLOCKER | CONFIRMED | `MAIN-local:docs/paper-sie-jmp/build_tex.py:27`; `C:runs/haaf_nested_constraint/results.json` | Public regeneration depends on untracked inputs and an uncommitted assembly tool. |
| P08 | P6 | BLOCKER | CONFIRMED | Findings C01–C11 and P01–P07 | Submission needs an integrated correction, provenance, and verification pass; a clean mathematical narrative alone will not close it. |

### P01. Separate the estimands throughout the manuscript

The generated specification `MAIN-local:docs/paper-sie-jmp/tex/sections/02-machinery.tex:47–67` honestly explains the moment-matched surrogate. It nevertheless first defines the same symbol as the mean divergence. Frozen notation line 13 still gives only that latter definition.

The distinction is substantive. With two equally weighted GP patterns having means -2 and 2 and variance 1, the primary metric gives:

| Candidate mean | Mean of per-pattern G | G against moment-matched GP |
|---|---:|---:|
| 0 | 2 | 0 |
| 2 | 4 | 0.4 |

**Reproduction:** `python "$S/probe_core.py"`, block C5; implementation at `aggregation_v3.py:50–104` and `laplace_evidence.py:148`. The discrepancy depends on the candidate. More draws do not remove it, and no general error bound was found.

There are two further definition seams:

- Frozen notation lines 9–10 describes sampled latent functions combined with scalar observation variance. `extract_gp_predictives` instead constructs a conditional predictive Gaussian per hyperparameter draw, analytically retaining latent covariance and adding observation noise (`bms_star.py:386–407`). Nonlinear G need not commute with integrating latent functions.
- Machinery describes per-pattern minimum-G projection (`S:docs/paper-sie-jmp/02-machinery.md:30–42,117–145`). Case C implements variance-weighted per-pattern candidate fitting and selection. E7 instead fits each candidate once to observed data (`A:experiments/e7_convention_sensitivity.py:77–92`). The nesting theorem's minimum-G premise must not be attributed to every table generated by the package.

**Impact:** Case B uses one MAP predictive; the between-hyperparameter surrogate gap vanishes there. Target B's point-data-prior example also does not test a general mixture gap. E7 and Case C use per-pattern G tables, not the moment-matched evidence integral. Thus this finding blocks the general description without invalidating all these numbers.

**Change and pin:** Give the intended and implemented divergence different symbols, name predictive-distribution versus sampled-function patterns explicitly, and state which candidate-fitting protocol each result uses. Preserve the two-pattern counterexample as a definition-level test. The unqualified hard-partition limit in frozen notation line 16 must also be qualified by aggregation convention, as machinery already does.

### P02. Pooled normalization does not preserve a uniform absolute level

Case A says that adopting expected-posterior reporting would foreclose misspecification diagnosis, whereas pooled reporting retains the relevant magnitudes. Machinery and discussion repeat this rationale.

For any common constant c, normalized pooled probabilities computed from `G+c` equal those computed from G. Pooled aggregation preserves differences in total support **between rows**, but its normalized probabilities cannot distinguish uniformly good from uniformly bad absolute fits. The package's stabilized `instance_scores` also discard a common offset. Both conventions can retain and report the original G matrix separately.

**Reproduction:** `python "$S/probe_core.py"`, final block, uses `G=[[0,2],[100,100]]`, tau 1:

```text
pooled [0.8807970779778823, 0.11920292202211755]
shift_invariant True
```

Adding 1000 to every entry preserves those probabilities. Source: `bms_star.py:630–669`; claim: `A:docs/paper-sie-jmp/03-case-A-external-validation.md:129–138`, `S:docs/paper-sie-jmp/02-machinery.md:98–109`, `S:docs/paper-sie-jmp/08-discussion.md:14–18`.

**Change:** Describe relative reweighting across patterns accurately. Present absolute inadequacy using raw divergences and a calibrated reference, independently of either normalized probability convention. Case D supplies reference material, not a validated universal rejection threshold. Add the common-offset invariance example to the manuscript-facing tests.

### P03. Merge plan and API compatibility

**Reproduction:** `python "$S/project_probe.py"` inspected branch contents and performed three-argument, read-only `git merge-tree 7154083 ddf8c9d origin/paper/<branch>` comparisons. For each of the six paper branches:

```text
merge_vs_fix_changed_in_both [... Notes/DECISIONS.md ...]
merge_conflict_marker_count 1
```

The branches append distinct decision tails at the same base location. A clean textual merge of source files would not settle these historical records or API semantics.

The Case C script imports `e7_convention_sensitivity` at line 46 and calls its aggregator at lines 412–425. An isolated import with only Case C plus fix-branch experiment paths failed:

```text
ModuleNotFoundError: No module named 'e7_convention_sensitivity'
```

Adding Case A's experiment directory made the import succeed. This dependency is real.

I would integrate in this order:

1. Complete the necessary fixes on F and establish the integration baseline.
2. Merge A, preserving D60, D61 and D65.
3. Merge B and D62.
4. Merge C and D63, either after A or after replacing the cross-script import with package `aggregate_convention`.
5. Merge D and D64.
6. Merge E and D67.
7. Merge synthesis and D66 last, then add the currently untracked notation/build apparatus and regenerate the assembled manuscript.

B, D and E have no demonstrated mutual code-order dependency; this sequence makes review of their claims straightforward. Preserve D68 and all paper tails. D59 remains intentionally absent; do not renumber or recover it from the stash. Correct stale status through dated addenda.

| Changed contract | Actual compatibility judgment |
|---|---|
| Strict predictive extraction | E7 and Case C retained all 1,000 requested predictives on replay. Their current valid caches work. Future bad draws now raise; do not restore silent dropping to get a script through. C03 remains an incomplete-validation gap. |
| `compute_induced_prior` weighting | Posterior draws use uniform weights; likelihood tilting requires an explicit request. Legacy callers passing log marginal likelihoods implicitly can now raise. The named case scripts do not directly call this API, so I did not demonstrate a case-branch break here. |
| `soft_transfer_weighted` | All absent/nonfinite input weights now raise. Joint log-space arithmetic works. No named paper case depended on its old uniform fallback. |
| `PredictiveList` | List compatibility works with Case C's capture wrapper. Converting or slicing to an ordinary list can lose diagnostics; serialization must preserve them intentionally. |
| `DecompositionResult.group` | Groups require conditional cross-covariance computation at decomposition time. Rebuilding only the historical seven dataclass fields loses the new attached summaries. Case E uses its own low-level decomposition and survives unchanged. |
| `samples` | Compatibility preserved two meanings, but C05 shows why treating this solely as naming hygiene understates the remaining problem. |

### P04. Record and policy reconciliation

**M2bR:** The canonical case routes I inspected/replayed did not use withdrawn informative-configuration HMC evidence. The package loader now guards it; C11 shows the remaining experiment-loader hole.

**W1:** Primary results use `pw_kl_vcal`. Case A nevertheless prints substantive joint-metric results inside section 3.4 at lines 159–168 while calling them appendix-only. A label does not move that material to an appendix. Move it physically. Case D's legacy metrics are explicitly disclosed at `D:docs/paper-sie-jmp/06-case-D-mopen-calibration.md:68–73`; they do not establish fresh primary-metric validation.

**W4:** Case B and the Case A reach-check paragraph explicitly use informative-configuration MAP methods-validation framing. I found no reason to relabel these as posterior validation.

**Status versus history:** A's D60 Resolution at `A:Notes/DECISIONS.md:5791–5798` and D61 status update at lines 5849–5851 close the aggregation reporting fork. Older “open” prose in the handoff and preceding historical paragraphs must not be used to reopen it. Conversely, independent author/assembly decisions in D66 and D67 remain unresolved by numerical replay. Stale “Kimi pending” review paragraphs remain in several decision tails; update status by addendum, using actual sign-off records.

Concrete assembly defects remain:

- `S:docs/paper-sie-jmp/08-discussion.md:156` calls section 7 uncommitted and says it supplies no reported number. E has a committed section, script and numeric artifact.
- `C:docs/paper-sie-jmp/05-case-C-nested-constraints.md:8–10` retains a provisional source/criticism note.
- `D:docs/paper-sie-jmp/06-case-D-mopen-calibration.md:220–227` retains the optional E8B placeholder. Either commission that work separately or remove the placeholder; it need not block this paper scientifically.
- D67's open author items at `E:Notes/DECISIONS.md:5983–5991,6016–6019` concern initialization provenance, local mode evidence, uncertainty-floor scope, optional enrichment and review/assembly substitutions. This review supplies an independent implementation check; it does not silently ratify author decisions.

**Fix pass 2 inventory:** Required metric identity and its two callers; removal of the samples ambiguity with caller migration; actual wiring of Case A's external-target check; replacement of Case C's cross-branch aggregator import; and trimming provenance prose from code. The metric-keyword change must respect the recorded frozen-code boundary. These items are not all cosmetic: C05 and the import failure show observable consequences. Add the new failure-path defects to that queue.

**Reproduction:** `python "$S/project_probe.py"` prints the decision-tail inventory and line-numbered status excerpts; `git show <prefix>:<path> | nl -ba` reproduces the section passages above. No inference from review verdicts substitutes for the code/artifact checks.

### P05. FIX-2 inheritance needs an asset-specific correction

The repaired wrappers now include mean conditional covariance plus covariance of conditional means. Existing pre-fix calls in `experiments/toy_example.py:87–98` and the MCMC path at `experiments/toy_example_noMCMC.py:84` would have generated understated bands. Regenerating through the repaired moments changes those bands, while C05 still affects plotted sample curves and interval labeling.

A concrete prose problem remains at `MAIN-local:CogSci Poster/QA_PREP.md:218–221`: the answer attributes thin decomposition bands to sample size and moderate noise, without identifying the missing conditional-variance problem. The local candidate-figure README already distinguishes an old means-only toy figure from a separately generated honest-band figure (`MAIN-local:CogSci Poster/candidate figures/README.md:40–44`). The correction is therefore incomplete across the presentation record.

**Reproduction:** Read those passages with `nl -ba`; compare the one-draw result in C05, where the old across-mean spread is zero and the corrected full standard deviation is positive.

**Scope:** I did not establish which legacy asset the current final layout embeds. P05b therefore remains PLAUSIBLE. An asset manifest or inspection of the actual source layout must settle it. Do not infer the defect's magnitude for an unidentified figure.

The current Case E artifact does **not** inherit the omitted-variance defect: its script already stores per-draw conditional variances and computes mixture intervals independently. Its complete JSON, README and PNG replay byte-identically. Case D uses a separate MAP-conditional reconstruction. I found no basis for declaring all sections 01–08 numerically invalid because of FIX-2.

### P06. Test value, missing pins, and the actual run

The suite has valuable independent checks: Gaussian identities, direct conditional covariance calculations, identical-draw total-variance checks, quadrature comparisons, reference-volume bookkeeping, defensive-proposal density checks, and explicit high-temperature Laplace failure examples. These support the corrected decomposition and standard estimator paths.

Coverage remains uneven:

- The new C01–C10 failures were not prevented by the passing tests.
- `tests/test_fix1_external_targets.py:33–53` embeds committed numbers as literals. Testing the checker against those literals does not demonstrate that the general package evidence estimator reproduces Target B.
- Its optional artifact fixture improves drift detection, but does not replace an independently computed package-level target.
- E7's “must reproduce” anchor at `A:experiments/e7_convention_sensitivity.py:95–99` prints a value without asserting it.
- Case C explicitly constructs overlapping candidate pools. Its nesting gate validates an implemented ordering contract; it cannot establish discovery of global optima. The manuscript correctly calls this an identity of the protocol.
- The new BMS* ESS and tie fields are not carried into the older SIR artifact serialization at `experiments/prior_sensitivity_study.py:698–705`. That code still uses first-index `argmin`. Console output at `bms_star.py:797–801` likewise reports every exact tie as a win for the first candidate. My Case C replay printed 1,000 free “wins” despite 999 exact primary-metric ties.
- Some group tests merely check access/alias identities, but companion direct-conditioning tests provide substantive mathematical coverage. I do not dismiss the decomposition suite as wholly tautological.

**Actual counts, not the expected baseline:** I started the requested full-suite command once. It was interrupted after **1,137 passed, 4 skipped, 1 failed in 288.11 seconds**. I then ran the remaining safe test nodes: **205 passed, 1 skipped in 22.02 seconds**. Across completed distinct nodes: **1,342 passed, 5 skipped, 1 failed; four real-root integration tests were not completed**. Combined reported test runtime: **310.13 seconds**. Separately supplying the two branch fixtures produced **2 passed in 3.00 seconds**; those replace two skips rather than adding two new distinct tests.

The failure was `test_committed_dependency_lock_reproduces_at_head`, at `tests/test_m2cr_environment_freeze.py:533`. Independent comparison confirmed:

```text
added ['pypdf==6.14.2']
removed []
```

The preceding distribution/binary checks passed. I did not modify the dependency lock.

**Protocol conflict and my execution limitation:** I discovered after launch that the requested suite itself runs prohibited Git mutations. `tests/test_m2cr_historical_anchor.py:139–155` adds/removes a worktree against the shared repository; `tests/test_m2cr_r4_launch.py:54–56` creates scratch commits; `tests/test_m2cr_realroot_integration.py:129–149` invokes `git stash create`. The first mutation tests had already run before discovery. I interrupted my process and excluded the remaining four real-root tests. Thus I cannot characterize the suite execution as wholly read-only, or claim the expected uninterrupted 1,346-pass result. I did not intentionally invoke Git mutation commands outside those test internals, and final fix-worktree `git status --short` was empty. The test protocol needs isolation/authorization before a complete rerun.

### P07. Reproducibility is strong locally but incomplete for a reader

#### Section-by-section trace and replay

| Section | Named source and artifact | Independent judgment at the fix head |
|---|---|---|
| 01 Introduction | `S:docs/paper-sie-jmp/01-intro.md`; downstream cases | No independent numeric estimate to rerun. General claims inherit the estimand and aggregation qualifications in P01–P02. |
| 02 Machinery | Package modules; `S:docs/paper-sie-jmp/02-machinery.md`; generated `MAIN-local:docs/paper-sie-jmp/tex/sections/02-machinery.tex` | Core primary metric, pooled algebra and volume bookkeeping checked. Definitions still need reconciliation; no artifact can repair an ambiguous target. |
| 03 Case A | `A:experiments/vanbork_external_validation.py`, `e7_convention_sensitivity.py`; `runs/vanbork_external_validation/results.json`, `runs/e7_convention_sensitivity/results.json` | Both regenerated JSONs equal committed values apart from the generation date. External checks: A error 0; B error 6.404745348520535e-7. Primary E7 headline reproduces 0.183, 0.192, 0.441, 0.184. The local multi-parameter reach check remains outside this reproduced chain. |
| 04 Case B | `B:experiments/occam_dial_figure.py`, `e6_nesting_monotonicity.py`; `runs/occam_dial/figure_results.json`, `e6_results.json` | Regenerated log integrals and probabilities equal committed values. Only ESS roundoff changed, at most 1.82e-11 and 3.82e-10 respectively. The optional local cross-check was unavailable in the scratch route and records that fact. Runtime 12.00 and 28.91 seconds. |
| 05 Case C | `C:experiments/haaf_nested_constraint.py`; `runs/haaf_nested_constraint/results.json` | Exact original NumPy grid and 1,000 SIR predictives reproduce the primary BMS tables with maximum difference 0.0: 999 ties, one negative free slope, G gap 0.00036011417986084315. Refitting took 124.34 seconds. PSIS-LOO chains were inspected but not rerun. |
| 06 Case D | `D:experiments/regret_curves_mopen.py`; `runs/regret_curves_mopen/results.json` | JSON regenerated identically in 0.65 seconds from tracked subject summaries. BIC reconstruction error 5.684e-14, below 1e-8 tolerance. This does not rerun the original HMC fits. |
| 07 Case E | `E:experiments/toy_debias_demo.py`; `runs/toy_debias_demo/` | Full seeded sampling/decomposition replay produced byte-identical JSON, README and PNG. The stated slope, RMSE, band-width and coverage results survive the fix head. The external mode-search assertion still depends on separate local evidence. |
| 08 Discussion | `S:docs/paper-sie-jmp/08-discussion.md`; cases above | No independent estimate. The calibrated M-open qualification is appropriately cautious, but absolute-support and section-7 provenance statements require correction. |

These replays use case scripts read from their paper branches **with the fixed package**. They do not show that a checkout of `ddf8c9d` alone contains the complete manuscript pipeline.

Additional limits matter:

1. **Case A's mathematical target does not exercise the general evidence implementation.** The external-validation script implements its own Bernoulli divergence/softmax/quadrature (`A:experiments/vanbork_external_validation.py:69–147`). Its successful reproduction supports that special construction. It does not establish end-to-end correctness of package Laplace/MC/IS for arbitrary GP mixtures.

2. **The SIR inputs are local dependencies.** E7 and Case C require three 60,000-draw prior-IS pools. `prior_sensitivity_study.load_pooled_is` reads them at lines 389–397; prior-IS generation exists at lines 342–362, but the release needs an explicit prerequisite recipe or an archived immutable input bundle. I verified the actual pool hashes against Case C's artifact. I did not regenerate all 180,000 prior-IS draws.

3. **Case D reproduces a derived analysis.** Tracked subject/aggregate JSONs support rerunning the current figure. The original HMC draw chains are not retained in that input bundle, so a reader cannot audit their Monte Carlo behavior from the figure-regeneration command alone. The section correctly distinguishes stored full-domain G from the narrower integer-grid deviation reconstruction (`D:docs/paper-sie-jmp/06-case-D-mopen-calibration.md:16–23,135–178`).

4. **Case E's oracle covers computation, not every provenance assertion.** Sampler settings are guarded, but statements about the external wide-start mode hunt are literal explanatory text at `E:experiments/toy_debias_demo.py:639–645,940–946`. Byte-identical prose does not independently validate that mode analysis. Archive its underlying record or narrow the claim.

5. **The assembled manuscript cannot yet be obtained from one public commit.** Frozen notation and `build_tex.py` are not committed at the reviewed fix head. The builder selects moving branch names (`MAIN-local:docs/paper-sie-jmp/build_tex.py:27–39`), not pinned commit hashes. The Case A reach artifact named in section 3.5 was absent at its cited local path during this review. D65 discloses that exception; disclosure does not make it regenerable.

**Reproduction:** `python "$S/project_probe.py"` reports tracked availability and hashes; `python "$S/artifact_compare.py"` compares regenerated artifacts with exact Git blobs. Selected output:

```text
case_b/figure_results.json ... non_ESS_max 0
case_b/e6_results.json ... non_ESS_max 0
case_d/results.json numeric_differences 0
CASE_E results.json identical True
CASE_E README.md identical True
CASE_E debias_figure.png identical True
```

The Case E oracle hashes are:

```text
results.json
65c9ff5f14b9a5f3aca8267745d6b368d95b831e85a610f6844b74e1b33712bb
README.md
7096cd6e4d3d02f8971cee294fa3e50a2c7248272320e9cc72cfc45994f889af
debias_figure.png
c1153549ca55d9d644804790ef9a4627f8d82bedd157ec348ecb519f551a4723
```

The validated SIR pool hashes, ordered by seeds 0, 1 and 2, are:

```text
a07c4c8e2dc95e37d00334d4555c569fa36d47dae2bb083bbc94e2d32220a552
60d2bdf48235f8baca5f1f2cf15121ea6a518c227927b6cfab890fd8cc37350b
5efb94beec2040cf3eecdb862d4d657d05e6fad385f8a275e79961ceaf3d0a8f
```

The inspected local mode-search JSON hash was `2bb5da3808b55d8c3588985860632e36e482415535a9ee93727a187599ccd115`. This identifies the local input; it does not convert it into released evidence.

## 4. Verified-correct results and target coverage

| Target | Explicit judgment |
|---|---|
| T1, averaged divergence | **PARTIAL: discrepancy confirmed; nonfinite-mean guard repaired.** The weighted moment formula is correct, but its divergence differs from mean G (P01). Current `aggregation_v3.py:82–90` rejects nonfinite means/diagonal variances. The completed prior-stage test passed; replayed paper runs did not show the earlier invalid-mean warning. No general surrogate-error bound established. |
| T2, discarded conditional covariance | **FIXED for returned moments; residual consumer defects.** Current wrappers implement total covariance, including grouped cross-covariance. Identical-draw tests and the C05 probe confirm positive within-draw uncertainty. Existing sample consumers and old assets still need C05/P05 treatment. |
| T3, aggregation dial | **VERIFIED.** One global stabilizing shift cancels. A row-specific shift changes row weights, so it cannot silently replace pooled normalization. Pooled, row-min and expected-posterior returned distinct values 0.880797, 0.637890 and 0.690399 for the first candidate in the same two-row example. P02 concerns interpretation, not this arithmetic. |
| T4, concentration | **PARTIAL: diagnostics exist but propagation is incomplete.** Replayed E7 primary-metric effective sample sizes at tau 0.1 were approximately 33.7, 37.9, 551.4 and 33.8 out of 1,000; at tau 1, approximately 669, 685, 977 and 669. At tau 100 they approached 1,000. The appendix-only joint metric concentrated much more sharply. New ESS fields expose this, but legacy artifacts omit them. These are concentration measures, not independent-sample ESS or uncertainty intervals; SIR duplicates and upstream weighting still matter. |
| T5, evaluation grid | **LIMITED STABILITY VERIFIED.** Primary Sin+Linear support on the same toy path at tau 1 was 0.439757, 0.440674 and 0.441004 for 30, 60 and 120 points on the fixed expanded domain. Restricting 60 points to the observed domain gave 0.438807. The ranking survived these checks. Case C documents 60 locations; general grid/domain sensitivity remains a modeling choice, not a solved invariance property. |
| T6, W1 | **PARTIAL.** Primary roles are declared and implicit defaults warn; C09 and Case A's main-text appendix paragraph remain. |
| T7, withdrawal banner | **PARTIAL.** Guarded package loading works; C11 bypasses it. No withdrawn archive was used in my artifact checks. |
| T8, universe firewall | **VERIFIED at metadata-bearing boundaries.** `compute_G_matrix` now checks at line 549; `score_averaged_gp` also checks. Mixed and partially tagged rosters reject; wholly untagged rosters remain allowed by contract. A bare numeric matrix carries no universe metadata, so pure aggregators cannot reconstruct that provenance. No cross-universe paper probability was demonstrated. |
| T9, Case E | **VERIFIED for the current oracle, with provenance limits.** Full replay byte-identical. Mutating recorded target acceptance, initial step size or adaptation flag made the sampler guard reject. Site application and the actual conditioning-factor jitter probe were inspected. Independent mixture-CDF checks returned 0.025/0.975 at computed endpoints. Current run retained every draw; future decomposition failures can still be counted/dropped by its custom loop, so enforce zero failures for a canonical release. |
| T10, test adequacy | **PARTIAL.** Independent mathematical pins have value; new failure configurations and artifact coupling need coverage. Actual counts and incomplete integration run are reported in P06. |
| T11, sentinels and fallback | **PARTIAL.** The default Laplace evaluation now raises contextual errors; nonstrict failure propagates NaN. Optimizer records make failed starts inspectable. Remaining sentinel/fallback defects persist in the table, induced-prior and candidate paths (C01, C02, C06). |

Further positive checks:

- `pw_kl_vcal` implements the stated mean of squared mean differences divided by twice the GP marginal variance (`metrics_v2.py:43–55`). The corrected variance-calibrated Hellinger denominator is eight times that variance (`:58–74`).
- Defensive ordinary IS uses the full proposal density and a box indicator, not self-normalized weights. Its usual nonempty mixture passes independent volume checks. C04 isolates an untested boundary configuration.
- A one-dimensional interior Gaussian Laplace probe returned log integral `-0.23235401329235006` against analytic `-0.23235401329235011`, with convergence true. Reference-volume factors agree across the standard estimators.
- The high-temperature Laplace/IS disagreement in Case B is intentionally exposed, not silently passed off as accurate integration. The exact nesting extension in E6 includes zero amplitude; it must not be generalized to positive-amplitude boxes that exclude that embedding.
- Weighted transfer with competing extreme log weights and divergences returned `[0.7310585786300048, 0.26894142136999505]`, confirming joint stabilization.
- The new `hard_win_statistics` gives explicit tie credit and attainment; the remaining first-index problem concerns older consumers and `robust_rank`.
- Case C's exact replay supports the effective tie and its per-pattern containment protocol. Its PSIS-LOO prose distinguishes within-mode convergence, a problematic Pareto diagnostic, and an inconclusive paired difference. I did not upgrade this to independently rerun LOO evidence.
- Case E uses total variances and numerical Gaussian-mixture quantiles, and identifies the truth/bias split as a modeling choice. Its N=20 illustration does not establish an asymptotic uncertainty floor.
- Case D distinguishes correct-specification reference distributions from an established M-open diagnosis and does not identify scaffold limitations versus intrinsic mimicry from its current design.

## 5. Recommendations for the next two weeks

Effort estimates below are person-days for focused implementation/review, excluding unexpected long compute or author response delays.

| Priority | Work | Estimate | Unblocks |
|---|---|---:|---|
| 1 | Close C01–C04 and C06: strict evaluation, complete draw validation, all-restart failure, normalized IS boundary behavior. Add independent counterexample tests. | 2–3 days | Trustworthy failure behavior and code approval. |
| 2 | Reconcile P01–P02 with the author: name actual estimands, delimit projection claims, correct the absolute-inadequacy argument, qualify the temperature limit. | 1–1.5 days | A mathematically coherent manuscript specification. |
| 3 | Repair plotting/sample semantics and order-dependent noise; make rank ties symmetric; either reject or coherently regularize singular joint covariances. | 1–1.5 days | Honest uncertainty visualization and permutation stability. |
| 4 | Integrate branches in the stated order; preserve decision histories through addenda; remove the Case C cross-script dependency; settle metric metadata and cache guards. | 1 day | One reviewable integration revision. |
| 5 | Publish a machine-readable artifact manifest: commit, script, config, estimator, grid, seeds, dependencies, hashes, failure counts, ESS and convention. Archive allowed local inputs or supply complete generation recipes. Wire the external targets and E7 anchor into reproducible tests. | 1.5–2 days | Reader regeneration and evidence traceability. |
| 6 | Rerun canonical scripts against the integrated revision, including a deliberate decision on full Case C LOO regeneration. Run the entire suite in an isolated, authorized repository; resolve environment drift under the historical-lock policy. | 1 day plus compute | A valid release-level verification record. |
| 7 | Audit selected poster assets for FIX-2, add corrections where required, move appendix material, close author/assembly ledger entries, commit notation/build inputs, compile and inspect the final manuscript. | 1 day | Submission packaging and consistent public claims. |

This totals approximately 9–11 person-days. If time is tight, remove optional E8B/enrichment placeholders and unreleased reach claims rather than commissioning new scientific extensions. Do not treat those optional extensions as prerequisites to correcting existing evidence.

## 6. Commands run, outcomes, and limits

### Suite and repository inspection

Requested suite, launched once from the fix worktree with scratch temp/cache settings:

```sh
cd "$R"
python -m pytest tests/ -q -p no:cacheprovider
```

The run also directed pytest temporary files into the allowed scratch area. Outcome: interrupted for the Git-mutation conflict; 1,137 passed, 4 skipped, 1 failed, 288.11 seconds. Logs: `$S/suite.log`.

Collection produced 1,352 nodes. A scratch list selected the remaining 206 safe nodes; their pytest run returned 205 passed, 1 skipped, 22.02 seconds (`$S/remaining.log`). Four real-root integration nodes remain uncompleted. The two fixture-gated checks were separately supplied exact branch fixtures and passed (`$S/fixture_tests.log`). One remaining skip explicitly reports absent machine-local prior-sensitivity artifacts.

Read-only repository operations included `git status`, `git log`, `git show`, `git diff` and three-argument `git merge-tree`. Final fix-worktree status was empty; HEAD remained `ddf8c9d`. See P06 for the Git operations invoked internally by the initial suite; they prevent an unqualified read-only-execution claim.

### New probes

```sh
python "$S/probe_core.py"
python "$S/probe_remaining.py"
python "$S/probe_paper.py"
python "$S/project_probe.py"
python "$S/artifact_compare.py"
```

Outcomes: reproduced C01–C10 and P01–P03 counterexamples; checked concentration/grid behavior; enumerated branch conflicts and local dependency hashes; compared regenerated artifacts against exact Git blobs. Additional short probes recorded sampler-guard rejection, mixture-CDF endpoints, the analytic Laplace integral and dependency-lock drift in `probe_case_e_guards.log`, `probe_is.log` and `probe_lock.log`.

An exploratory Case C replay initially constructed the grid with Torch rather than the script's NumPy expression. Its tiny table difference was not attributed to the fix. Repeating with the exact original grid produced zero table difference (`$S/case_c_exact.log`). This distinction matters when interpreting deterministic replay claims.

### Named artifact regeneration

Source files were extracted with read-only `git show origin/paper/<branch>:experiments/<script>.py` into `$S/sources/`. For each run, the fixed package was imported first and printed; output constants were redirected to scratch. E7/Case C read only the allowed local prior-IS pools; Case D read the tracked subject summaries.

Executed:

- A: `vanbork_external_validation.main()` and `e7_convention_sensitivity.main()`; both JSON comparisons equal except date, external target checks pass.
- B: `occam_dial_figure.main()` and `e6_nesting_monotonicity.main()`; probabilities/log integrals equal, ESS roundoff only.
- C: `observed_pair`, `validated_sir_predictives(...,1000)`, then `fit_nested_pair` for all 1,000 draws on the exact script grid; primary tables equal.
- D: `regret_curves_mopen.main()`; JSON equal.
- E: extracted `toy_debias_demo.py` with scratch output and quiet mode; complete seeded sampler/decomposition oracle equal in all three files.

Logs reside only in scratch: `case_a.log`, `case_b.log`, `case_e6.log`, `case_c_exact.log`, `case_d.log`, `case_e.log`. The comparison helper makes the byte/numeric checks reproducible without rerunning expensive chains.

### Not run or not established

No network, dependency installation, lock edit, scientific experiment outside the requested review scope, or use of withdrawn HMC caches. No other current project-review channel's output file was opened. I did not rerun the four remaining real-root integration tests, the Case C PSIS-LOO chains, all prerequisite prior-IS cache generation, or original Case D HMC sampling. I did not compile the assembled LaTeX or establish which legacy poster image the current layout embeds. These limits remain part of the verdict.

Codex gpt-6-astra xhigh

