# Implementation review of fix pass 1 — Kimi K3 (package-only channel), 2026-09-08

*Driver note: produced by `moonshotai/kimi-k3` via OpenRouter, prompt 80571 tokens, completion 11636 tokens, finish_reason `stop`, 166 s. Package: fix1 package-only brief + specification + cumulative diff + new files + post-fix listings. No text altered below this note.*

# Fix Pass 1 Review — Kimi K3 (package-only channel)

## 1. Verdict

**APPROVE** — on a package-only reading, all nine fixes compute what the work order and manuscript require, the 1b folds resolved the real accretion, and no S1/S2 defect is visible in the diff; every execution-dependent claim (suite counts, Case E byte-identity, fixture tests) is NEEDS-REPO-VERIFICATION because this channel cannot run code.

## 2. Findings on (a)

### Summary table

| ID | FIX | Severity | Status | Path:line | Claim |
|---|---|---|---|---|---|
| K3-1 | FIX-7 | S3 | PLAUSIBLE | bistar_gp/bms_star.py:~758 | Implicit `run_bms_star` metric roster depends on `metrics_v2` import history; `metric_names=None` omits `PRIMARY_METRIC` in a process that never triggered a `__missing__` lookup |
| K3-2 | FIX-3 | S4 | CONFIRMED (by reading) | bistar_gp/bms_star.py:~581, ~664 | `metric_name` is optional ("unspecified"), contradicting the work order's "requires `metric_name`"; disclosed in the report addendum (R4) and still pending author disposition |
| K3-3 | FIX-6 | S3 | PLAUSIBLE | bistar_gp/aggregation_v3.py:~413-430 | `soft_transfer_weighted` does not validate finite `G_matrix`; a NaN entry yields an all-NaN posterior with no raise, inconsistent with the `soft_transfer` guard added in 1b |
| K3-4 | FIX-2 | S4 | PLAUSIBLE | bistar_gp/debias.py `_summarize` / `_finalize_target` | `std` uses clipped per-draw variances (`np.clip(np.diag(c), 0, None)`) while `cov` accumulates unclipped symmetrized matrices, so `diag(cov)` can differ from `std**2` on a numerically negative diagonal |
| K3-5 | FIX-1 | S4 | PLAUSIBLE | bistar_gp/bms_star.py:~237-256 | `PredictiveList` slicing/concatenation returns a plain `list`, silently dropping `attempted_indices`/`n_dropped` bookkeeping |
| K3-6 | FIX-1 | S3 | PLAUSIBLE, NEEDS-REPO-VERIFICATION | bistar_gp/model.py:~107-121 | The single-kernel `apply_hp_value` branch sets `comp_idx = 0` from a two- or three-segment name; the downstream hyperparameter-parsing offset (not in the diff) must handle both name shapes — tests claim it does |

### Detail

**K3-1 (S3, PLAUSIBLE).** `_MetricRegistry.__missing__` (bms_star.py:~194-210) registers `metrics_v2` only on a lookup miss. `run_bms_star` with `metric_names=None` does `metric_names = list(METRICS.keys())` (~:758-759), and `keys()` never triggers `__missing__`. So in a fresh process that calls `run_bms_star(...)` without first importing `metrics_v2` or looking up a v2 metric, the implicit roster excludes `pw_kl_vcal` — while `ExperimentConfig.metrics` and the appendix warning both name it as primary. The roles test passes only because `tests/test_fix1_roles.py` imports `bistar_gp.metrics_v2` at module top. Failure scenario: `python -c "from bistar_gp.bms_star import run_bms_star; ..."` scores ten legacy metrics and never the primary one, with no warning that the primary is missing. Suggested change: in `run_bms_star`, when `metric_names is None`, do `from . import metrics_v2  # noqa` before listing keys (one line). Pin: a subprocess test mirroring `test_primary_metric_resolves_without_an_explicit_v2_import` but calling `run_bms_star` with `metric_names=None` and asserting `PRIMARY_METRIC in out`.

**K3-2 (S4, CONFIRMED by reading).** The work order FIX-3(b) says "`soft_transfer` requires `metric_name` (no 'unknown' stamp)". The code makes it `Optional[str] = None` and stamps `"unspecified"` (~:664). The implementer's addendum discloses this and gives a structural reason (two package call sites outside the editable set, `metrics_v2.py:398`, `mcse_strategy.py:177`, omit it). This is a contract deviation from the work order, not a math error; it needs the author disposition the report requests (migrate callers to a required keyword, or record a documented legacy exception). Pin exists (`r2.metric_name == "unspecified"` in tests/test_fix1_diagnostics.py) — the pin enshrines the deviation, which is exactly what the disposition must bless or reverse.

**K3-3 (S3, PLAUSIBLE).** Pass 1b added a finite-G guard to `soft_transfer` ("G_matrix contains non-finite entries") but not to `soft_transfer_weighted`. There, `log_terms = lw[:, None] - G/tau` with a NaN in G gives `shift = np.max(log_terms) = NaN`, and the function returns `instance_posteriors = exp(NaN)` — a silently all-NaN result rather than an error. `run_weighted_bms_star` reaches it via `compute_G_matrix`, which returns finite penalties, so this is reachable only with a hand-built matrix — same reachability class as the `soft_transfer` guard that was judged worth adding (review F4). Suggested change: two lines mirroring the `soft_transfer` check. Pin: `pytest.raises(ValueError)` on a NaN matrix, matching `test_f4_soft_transfer_rejects_non_finite_G`.

**K3-4 (S4, PLAUSIBLE).** In `_DrawAccumulator.add_draw` the per-draw variance is clipped (`np.clip(np.diag(c), 0.0, None)`) but `cov_sum` accumulates `c` unclipped. `_summarize` then reports `std = sqrt(mean V + var M)` while `cov = within_cov + between_cov`. If a symmetrized conditional covariance has a small negative diagonal entry (reachable under jitter floor regimes), `diag(cov) != std**2` and the R2/two-draw pins (`np.allclose(np.diag(comp.cov), comp.std**2)`) would fail only in that regime — currently guarded by well-conditioned fixtures. Suggested change: clip the diagonal of the accumulated covariance the same way, or document the asymmetry. S4 because no paper path is known to hit a negative diagonal.

**K3-5 (S4, PLAUSIBLE).** `PredictiveList` subclasses `list` without overriding `__getitem__`/`__add__`; `draws[:10]` is a plain `list` with no `n_dropped`. A caller that subsamples the predictives (a plausible exploratory move under `strict=False`) loses the integrity record precisely when it matters. Cost of fix: a `__getitem__` override returning `PredictiveList` with sliced bookkeeping, ~6 lines. Latent only; no current caller slices.

**K3-6 (S3, PLAUSIBLE, NEEDS-REPO-VERIFICATION).** The single-kernel branch in `apply_hp_value` maps `covar_module.base_kernel.lengthscale_prior` (3 segments) and `covar_module.outputscale_prior` (2 segments) to `comp_idx = 0`, but the code after the branch that parses the hyperparameter name is outside the diff hunks. If it indexes `parts` at offsets computed for the `.kernels.{i}.` shape, one of the two single-kernel shapes would mis-parse. The pins (`test_single_kernel_sites_are_selected_and_applied`, the 0.05/2.0-lengthscale probe) claim both shapes work; I cannot verify the unseen lines. PLAUSIBLE non-issue; listed so the repo-access channel confirms the downstream parse handles both segment counts.

### Work-order item checks (no finding)

- **Law of total variance**: `_summarize` computes `std = sqrt(E_d[var_d] + Var_d[mean_d])` with `bias=True`/`ddof=0` consistently in both terms; `_finalize_target` adds `mean_d C_d + Cov_d(m_d)` for the matrix. Correct.
- **Group conditioning**: `_DrawAccumulator.add_draw` forms one Cholesky of `_blocks_sum(km, self.names, "XX")` (the entire training covariance) plus noise and conditions every component, group, and the full posterior with it — never a group-only factor. Correct per FIX-2(b).
- **Mixture interval**: `mixture_central_interval` (decompose.py:~124-160) bisects the equally weighted mixture CDF with the correct update direction (`cdf < p` ⇒ raise `lo`), bracketed at ±12 sd. Correct.
- **Hellinger exponents**: `/ (8 var_p)` and `/ 8` (metrics_v2.py:~62-73, ~103-112) match the equal-variance Bhattacharyya exponent Δ²/(8σ²); the 1−exp(−1/8) pin is right.
- **ESS**: `log_weight_ess` subtracts the per-column max, maps all-`-inf` to 0 and NaN to NaN, and `boltzmann_weight_ess` delegates. Matches FIX-3(a).
- **Exact-tie split credit**: `hard_win_statistics` uses `G == row_min` exact ties, credit sums to one, order-free. Matches.
- **Three conventions**: `aggregate_convention` (bms_star.py:~679-707) reproduces pooled/rowmin/expected_posterior with the same arithmetic order as the pre-fix `_boltzmann_posterior`; the bit-identity pins (`np.array_equal`) are the right strength.
- **Joint log-sum-exp**: `soft_transfer_weighted` forms `lw[:,None] − G/τ` and log-sum-exps once; the pinned underflow case [0.59384548, 0.40615452] is exactly the normalized [2, 1+e⁻¹] vector. Correct.
- **Strict=False NaN paths**: NaN propagates through `_laplace_log_integral` (early NaN return), `_select_start` (order-independent finite minimum), MC/IS (NaN log_Z and NaN ESS), and `model_posterior` (all-NaN softmax, documented). A NaN cannot become a silently "best" score; the joint-void semantics is the honest choice.
- **Contracts**: `DecompositionResult` keeps exactly the seven positional fields (extra state attached in `__post_init__`, not as fields); `ComponentResult` additions are all defaulted keywords; `BMSStarResult` additions are defaulted; `PredictiveList` is a `list`. The poster driver's `samples=` rebuild and `comp.samples` read still work (report addendum item 3).
- **Refuted items**: no E6 failure gate, no finiteness "explanation" of the aggregation_v3.py:77 warnings, no change to pooled arithmetic or the `normalize_per_draw=False` default — all confirmed absent from the diff.
- **Deviations**: mauna `groups=INTERPRETATION_GROUPS` (justified — group moments need the blocks at decomposition time); `_MetricRegistry` replacing `_resolve_metric` (justified, and cleaner); appended primary metric (justified by the `metrics[:4]` slice); scratch-symlink oracle and `FIX1_FIXTURE_DIR` (reasonable given the read-only constraint); `likelihood_tilted` name (the prompt's own example).

## 3. Recommendations on (b)

- **FIX-1 — KEEP.** `PredictiveList` is 20 lines for a real contract (draw provenance); the site-name fallback in `select_hmc_sites`/`apply_hp_value` is the minimal shape. The strict-flag threading is mechanical but each flag is the documented escape hatch. No smaller form survives the pins.
- **FIX-2 — KEEP.** Pass 1b already removed the accretion: `_summarize`/`_single_draw_summary` collapsed the two ComponentResult construction sites, and `_DrawAccumulator`'s typed target keys are the right factoring (one Cholesky per draw serving all targets is both the correct math and the cheap implementation). The `__post_init__` non-field attributes are mildly hacky but are the cheapest way to hold the seven-field contract; a separate wrapper class would cost more API surface for no correctness gain.
- **FIX-3 — SIMPLIFY IN PLACE (one line).** Keep everything; add the `metrics_v2` import on the implicit `run_bms_star` path (K3-1). `log_weight_ess` as the single ESS routine is the right consolidation.
- **FIX-4 — KEEP.** Two exponent changes plus a guard call at the one boundary that holds metadata; nothing to remove.
- **FIX-5 — KEEP.** Nine `strict` keywords look like accretion but each is load-bearing (NaN-vs-raise is a per-entry-point decision); `OptimizerRecord` and `_select_start` are the minimal provenance that makes the sentinel removal auditable. Rewriting to a result-monad would be a larger diff for the same behavior.
- **FIX-6 — KEEP.** The joint log-space form is shorter than the two-stage code it replaced and deletes the uniform fallback outright. The `weighting="uniform"`/`"likelihood_tilted"` split with a conflict raise is the right API sharpening.
- **FIX-7 — KEEP (with K3-1).** `_MetricRegistry` is more elegant than the pass-1 `_resolve_metric` (no mutable registration helper, lazy import in one place). `WITHDRAWN_CACHES` + `is_withdrawn_cache` is small and does exactly the banner enforcement.
- **FIX-8 — KEEP.** Closed forms plus a recompute-from-rows checker; the finite-validation order (validate, then mass check, then reductions) is correct and was the R9 fix.
- **FIX-9 — KEEP.** `aggregate_convention` duplicates `soft_transfer`'s pooled arithmetic deliberately: the bit-identity pins against the Case A script and the pre-fix `_boltzmann_posterior` are the point. Delegating `pooled` to `soft_transfer(...).instance_posteriors` would save ~4 lines but couple the pins to `soft_transfer`'s validation and result construction; not worth it.
- **Overall — KEEP the pass.** After the 1b folds, the remaining accretion is the strict-flag plumbing and the DecompositionResult attribute attachment, both of which are the cheapest forms that satisfy the pinned contracts. Do not rewrite.

## 4. Verified-correct list (by reading)

- Total-variance moments: both terms present, consistent ddof, per-draw full matrices never stored (covariance accumulated as a sum). 
- Group = full posterior identity by construction (same blocks, same factor); singleton and empty groups derived, not stored; duplicate names collapse (`group_key`).
- Mixture CDF bisection direction, bracketing, and `mass` validation.
- Hellinger `/8` in both variants and both docstrings.
- ESS log-space stability (per-column max shift), underflow finiteness, NaN-vs-absent distinction.
- Tie rule exactness and order-freeness; τ→0 expected-posterior equals split credit (pinned).
- Firewall placement in `compute_G_matrix` before the metric lookup, plus the explicit guard in `score_averaged_gp`; all-untagged rosters still permitted.
- Sentinel removal: `1e6`/`-1e10` gone from `compute_G_at_params`/`_log_likelihood`; `EvaluationFailure` re-raised through both optimizer handlers; induced-prior penalty `max + 10(|max|+1)` strictly worse for negative metrics.
- `compute_log_marginal_likelihoods` applies sites outside the numerical handler so an unrecognized site escapes (R1).
- `soft_transfer` pooled arithmetic and default unchanged; grouped `class_names` raise; 1:1 relabeling accepted.
- `decompose_model_mcmc` name-matched raw mapping with both-direction KeyError; not routed through constrained setters.
- Withdrawn-cache registry refuses both entries, honors the `allow_withdrawn=True` warning path, and admits unrelated caches silently.
- `__init__` exports match the work order's surface (`mixture_central_interval`, `aggregate_convention`, `boltzmann_weight_ess`, `hard_win_statistics`, `PredictiveList`).

## 5. What I could not run

This channel has no execution or repository access. Not run: the pytest suite (the report claims 1342 passed / 5 skipped / 1 known lock-drift failed at 466 s for 1b; the brief's expected 1327/3/1 predates 1b — NEEDS-REPO-VERIFICATION); the Case E oracle sha256 comparisons (65c9ff5f…/c1153549…/7096cd6e… — NEEDS-REPO-VERIFICATION, PLAUSIBLE given the unchanged MAP path and trailing-keyword signatures); the two `FIX1_FIXTURE_DIR`-gated tests; every line outside the diff hunks (notably the post-branch hyperparameter parsing in `apply_hp_value`, K3-6, and `run_robust_aggregation`/`run_weighted_bms_star`'s route through `compute_G_matrix`); and `git status --short` file-set confirmation. All findings above are derived from the package text alone; K3-2 is the only one I can call CONFIRMED without execution, and it is a disclosed work-order deviation awaiting author disposition rather than a code defect.

Signed: **Kimi K3 (package-only channel)**
