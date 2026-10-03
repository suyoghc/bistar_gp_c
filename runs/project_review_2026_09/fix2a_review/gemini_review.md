<!-- channel gemini, model gemini-3.1-pro-preview via gemini, attempt 1, 2026-10-03 07:48:16, 45s -->

**Verdict:** APPROVE. The code changes correctly and completely implement the 2a work order and the defect specifications. The implementer's report and D70 draft are accurate, comprehensive, and honest.

### Findings

| ID | Item | Severity | Status | Location | Claim | Concrete failure scenario | Suggested change | Pin |
|---|---|---|---|---|---|---|---|---|
| GEM-1 | 2a-1 | S3 | CONFIRMED by source read | `bms_star.py:649` | A dead row (every candidate failing on one draw) receives the uniform penalty; under `normalize_per_draw=True` this adds uniform mass to all candidates for that draw. | Reachable if a metric fails for all candidates on a specific outlier draw. | Log the dead row; consider if dropping it is better than injecting uniform mass. (Can wait for author decision as noted in open item 1). | `test_dead_row_handling` |
| GEM-2 | 2a-8 | S4 | CONFIRMED by source read | `bms_star.py:756` | The ESS warning floor is fixed at `100.0`, which causes false positive warnings whenever `n_draws < 100` (e.g., the 20-predictive smoke run). | Running any pipeline with small evaluation budgets raises spurious ESS warnings. | Use a relative floor or `min(100.0, n_draws * 0.1)`. (Can wait for author decision as noted in open item 2). | `test_ess_warn_scales_with_budget` |

### Verified correct

- **2a-1 (failed divergence tables):** Verified by source read (`bms_star.py:623-649`). The `ValueError` for empty tables and `EvaluationFailure` for all-failed tables and dead columns are properly implemented. The penalty logic is correctly retained only for partial failures, and logging correctly groups counts by candidate name.
- **2a-2 (strict induced prior):** Verified by source read (`induced_prior.py:255-300`). `EvaluationFailure` is raised for individual points under `strict=True`, or logged and zero-weighted under `strict=False`. The ESS calculation accurately excludes zero-weighted failed points. 
- **2a-3 (strict extraction):** Verified by source read (`bms_star.py:257, 362`). `sample_draw_count` robustly checks for a single, consistent leading dimension across all required arrays prior to any indexing, rendering it order-invariant. `missing_sample_sites` successfully accounts for legacy alias mapping.
- **2a-4 (empty IS ladder):** Verified by source read (`laplace_evidence.py:648`). The input tuple is verified to be non-empty, finite, and strictly positive. 
- **2a-5 (silent sinusoid fallback):** Verified by source read (`candidates.py:96-105`). `_require_restart` properly captures exceptions from all attempts and raises an `EvaluationFailure` carrying the final exception rather than defaulting to preset values.
- **2a-6 (noise_var):** Verified by source read (`debias.py:87-97`). `noise_var` is explicitly set to the mean of `noise_draws` across retained samples, making it invariant to permutation.
- **2a-7 (withdrawn caches):** Verified by source read (`config.py:25-50`). `WITHDRAWN_CACHES` cleanly incorporates the D33 and D34 exclusions. `fit_method_metric_comparison.py` uses `load_hmc_samples` correctly.
- **2a-8 (concentration and ties):** Verified by source read (`bms_star.py:756-763`, `experiments/prior_sensitivity_study.py:702-707`). The ESS floor warning triggers appropriately, and `hard_win_credit` successfully splits ties rather than leaning on `argmin`.
- **2a-9 (dropped records):** Verified by source read (`laplace_evidence.py:1034-1060`, `decompose.py:34`). The `TauSweepPosteriors` and `LadderPosteriors` data structures properly shepherd `converged`, `n_clipped`, and `n_starts_failed` through the execution tree. Jitter escalations emit `logger.warning`.
- **2a-10 (Case D producer):** Verified by source read (`practice_EvansEtAL/run.py:381-546`). The pipeline threads the random seed thoroughly down to the predictive subsampler and cleanly bails via `raise` or writes error diagnostics into `sampler_records` based on `strict`.

### Answers to questions 5, 6 and 7

**Question 5: Deviations**  
All 9 deviations are acceptable. None need to be reverted. 
- The edits to `test_bms_aggregation.py` (Deviation 1) accurately accommodate the new penalty semantics without weakening the original validation intent. 
- The broader inclusion of `ValueError` on empty tables (Deviation 2) and `n_penalized_evaluations` (Deviation 3) are good defensive programming improvements.
- The modifications to the MAP visualizer (Deviation 8) to sample from the joint multivariate normal strictly improve the statistical correctness of the plot.
- Deviations 4, 5, 6, 7, and 9 correctly execute the unstated logical implications of the work order.

**Question 6: Open items**  
None of the 8 open items need to be fixed inside 2a before it is committed. Items 1 and 2 (dead row normalization and ESS floor scaling) are minor behavioral tweaks that do not jeopardize manuscript figures. Items 4, 5, and 6 touch code outside the scope of the 2a queue list and should wait for a subsequent fix pass or author intervention. The dependency lock drift (Item 8) must be resolved by the author as part of the environment freeze. 

**Question 7: Author's standing question**

| Item | Verdict | Comment |
|---|---|---|
| 2a-1 | KEEP | Concise and robust matrix logic. |
| 2a-2 | KEEP | Clean integration of `strict` branching. |
| 2a-3 | KEEP | The `sample_draw_count` helper completely isolates the length logic. |
| 2a-4 | KEEP | Minimal and effective check. |
| 2a-5 | KEEP | `_require_restart` is an elegant wrapper. |
| 2a-6 | KEEP | Perfectly implements the requested behavior. |
| 2a-7 | KEEP | Correctly applies the guarded loading mechanisms. |
| 2a-8 | KEEP | Accurate implementation of the tie mechanics. |
| 2a-9 | KEEP | Minimal sub-classing successfully preserves existing APIs while tunneling data. |
| 2a-10 | KEEP | Detailed provenance and seed propagation. |
| Optional | KEEP | All optional items were executed cleanly. |

### What you ran or read
- I am a package-only channel, so I executed no code.
- Read and analyzed the work order (`HANDOFF-fix-pass-2.md`), adjudicated findings (`SYNTHESIS.md`), and defect specifications (`codex_astra_review.md`, `opus_review.md`).
- Reviewed the complete git diff of tracked files (`69deeda` to `fix/pass-2a`) and the full text of the newly added files (`bistar_gp/errors.py`, `tests/test_fix2a_contracts.py`).
- Read and evaluated the implementer's report (`fix2a_report.md`) and the draft decision entry D70.