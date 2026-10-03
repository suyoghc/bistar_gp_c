**Verdict: REVISE.** Keep the implementation and make targeted corrections; no wholesale rewrite is warranted. I found no numerical regression in E7 or the Case E oracle.

**Record accuracy:** Mostly supported, but the registry count is wrong, some contract-completeness claims are overstated, and “these pass once … committed” exceeds the verification reported.

**Findings**

All paths refer to the reviewed working tree.

| ID | Item | Severity | Status | File:line | Claim and concrete failure scenario | Suggested change | Pin |
|---|---|---|---|---|---|---|---|
| X01 | A-7 | S3 | CONFIRMED by probe | [aggregation_v3.py:261](/Users/sc8918/Documents/GitHub/bistar_gp_c-fix2a/bistar_gp/aggregation_v3.py:261) | Integer inputs truncate average ranks. `robust_rank(np.array([[0,0,1]]), …)` returns ranks `[1,1,3]` and probabilities `[.46831,.46831,.06338]`; the equivalent float matrix returns the correct `[1.5,1.5,3]` and `[.44982,.44982,.10037]`. | Use floating rank storage, preferably `rankdata(..., axis=1)` directly. | Assert integer/float input equivalence and exact expected average ranks. |
| X02 | 2a-2 | S3 | CONFIRMED by probe | [induced_prior.py:291](/Users/sc8918/Documents/GitHub/bistar_gp_c-fix2a/bistar_gp/induced_prior.py:291) | The evaluation contract covers only two metric exception classes. A registered metric raising `FloatingPointError` for negative parameter values escapes unchanged under both `strict=True` and `strict=False`. Strict does not produce contextual `EvaluationFailure`; permissive evaluation cannot assign those failed points zero mass. | Route supported numerical evaluation exceptions through the same point-failure handling. Preserve the cause and parameter context. | Mixed valid/raising regions, parameterized over `FloatingPointError` and `RuntimeError`, in both modes. |
| X03 | 2a-10 | S3 | CONFIRMED by probe | [run.py:446](/Users/sc8918/Documents/GitHub/bistar_gp_c-fix2a/experiments/practice_EvansEtAL/run.py:446) | Successful sampling evidence disappears when extraction fails. With a sampler returning draws and diagnostics, a raising extractor, and `strict=False`, the result contains only `sampler_records[cfg]["failed"]`; `hmc_samples` is empty and returned-draw counts/diagnostics are lost. | Record sampling output immediately after sampling succeeds; add extraction status afterward. Persist available draws even when extraction fails. | Successful sampler followed by failing extractor; assert saved draws, diagnostics, requested/returned counts and extraction failure. |
| X04 | 2a-10 | S3 | CONFIRMED by probe | [run.py:437](/Users/sc8918/Documents/GitHub/bistar_gp_c-fix2a/experiments/practice_EvansEtAL/run.py:437) | MAP extraction bypasses `_missing`. A raising `extract_map_predictives` under `run_all(..., mode="map", strict=False, verbose=False)` returns no subject result and writes no subject failure record. This contradicts the stated permissive configuration-failure contract. | Handle MAP extraction through the same contextual failure recorder. | Inject a MAP-extraction exception; retain a subject record identifying the failed configuration. |
| X05 | 2a-7; open item 7 | S4 | CONFIRMED by probe | [config.py:34](/Users/sc8918/Documents/GitHub/bistar_gp_c-fix2a/bistar_gp/config.py:34) | Both historical `samples_toy_elicited_hmc_td{7,10}.npz` names remain loadable without authorization or warning. D33 says corrected results replace the **withdrawn historical** numbers and calls the original caches invalid. Supersession does not rehabilitate those files. The handoff’s explicit enumeration omitted them, but deriving the registry from D33 exposes this remaining commitment gap. | Register both historical paths; preserve corrected replacement archives and prior-IS pools. | Assert the complete independently specified historical-path set, rather than principally iterating the implementation’s registry. |
| X06 | 2a-3 | S4 | CONFIRMED by probe and source read | [bms_star.py:393](/Users/sc8918/Documents/GitHub/bistar_gp_c-fix2a/bistar_gp/bms_star.py:393); [debias.py:461](/Users/sc8918/Documents/GitHub/bistar_gp_c-fix2a/bistar_gp/debias.py:461) | The old no-kernel shortcut bypasses the new complete inventory message. Supplying only the toy noise site raises, but names none of the three missing kernel sites. Thus “naming every missing site” is not fully implemented. | Let inventory validation report all missing sites before the legacy shortcut. | Noise-only and empty dictionaries on both routes; assert every required missing name. |
| X07 | A-5 tests | S3 | CONFIRMED by probe | [test_fix2a_contracts.py:592](/Users/sc8918/Documents/GitHub/bistar_gp_c-fix2a/tests/test_fix2a_contracts.py:592) | The joint-sampling pin checks only marginal variances. I replaced the implementation in memory with independent normal draws having the correct diagonal variances; the entire A-5 test still passed. Such curves have the wrong joint distribution. | Check empirical cross-covariance against the full posterior covariance. | A correlated fixture on which a diagonal-only sampler fails. |
| X08 | A-5 robustness | S3 | CONFIRMED by probe | [viz.py:61](/Users/sc8918/Documents/GitHub/bistar_gp_c-fix2a/bistar_gp/viz.py:61) | Fixed `1e-10` jitter introduces a plotting failure for a numerically semidefinite posterior. With toy training points on `[-10,10]`, 100 evaluation points, and SE outputscale and linear variance both `1e6`, decomposition succeeds but its covariance has minimum eigenvalue about `−4e−8`; plotting raises `LinAlgError`. This is latent, not a paper-path regression. | Use scale-aware handling of roundoff-sized negative eigenvalues, with an explicit signal for regularization; reject materially indefinite covariance. | Plot the reproduced high-scale posterior and verify the resulting full covariance. |
| X09 | Report/D70 | S4 | CONFIRMED by probe and source read | [report:46](/Users/sc8918/Documents/GitHub/bistar_gp_c-fix2a/runs/project_review_2026_09/fix2a_report.md:46), [report:90](/Users/sc8918/Documents/GitHub/bistar_gp_c-fix2a/runs/project_review_2026_09/fix2a_report.md:90); [DECISIONS.md:5917](/Users/sc8918/Documents/GitHub/bistar_gp_c-fix2a/Notes/DECISIONS.md:5917) | The registry has **15**, not 16, entries. Demonstrating that adding `errors.py` repairs an import does not establish that all four complete realroot launch tests pass after commit. | Correct the count; say the missing-module failure should be resolved, with launch verification pending. Qualify completeness claims affected by X02–X06. | Count the actual registry; run the launch tests later in the authorized isolated committed environment. |

**Verified correct**

- **2a-1:** All-failed tables and dead candidate columns raise; partial failures retain the prescribed negative-metric-safe penalty and warning counts. Empty-table rejection and duplicate-name reporting are reasonable additions.
- **2a-2:** The original sentinel counterexample is repaired: failed points receive zero mass, successful points normalize correctly, ESS excludes failed points, and total failure raises. Exception re-exports preserve existing imports. X02 limits completeness.
- **2a-3:** Individual missing-site rejection, ragged-array order-independent messages, complete-dictionary order invariance, legacy aliases, single-kernel extraction and marginal-likelihood validation pass. X06 concerns the remaining diagnostic shortcut.
- **2a-4/5/6:** Invalid ladders raise; the constant-integrand volume check passes; all-raising sinusoid restarts raise while a successful restart survives; both decomposition routes return mean retained noise variance without changing the seven-field positional contract.
- **2a-7/8:** Every registered cache path is refused before loading, and an ordinary cache still works. ESS threshold checks pass. Console and SIR serialization split exact ties correctly while preserving the legacy key.
- **2a-9:** Sweep/ladder records propagate without breaking tuple unpacking or dictionary use; forced nonconvergence and jitter escalation are exercised. The existing ladder-equivalence test passes.
- **2a-10:** Strict sampler failure stops the run; successful HMC results serialize seed, counts, diagnostics and draws. The permissive failure paths need X03/X04.
- **Optional items:** A-5 uses mixture intervals and correctly labels conditional means. Its ordinary MAP implementation samples the full covariance, although its test does not establish that. A-7 works for floating inputs. A-15 accurately documents the unusual existing log-weight scale; A-18 documents the existing mutation.

E7 regenerated **exactly**, excluding `generated`. Case E reproduced all three reported SHA-256 hashes: `65c9ff5f…`, `c1153549…`, `7096cd6e…`. Frozen MCSE tests and D58 driver contract tests passed. I found no changed successful-path arithmetic that contradicts those results. I did not independently regenerate Cases B, C or D, or rerun the real Case D smoke experiment.

All **12 new tests fail against `69deeda`**, with the compatibility import adjusted in scratch. This establishes baseline discrimination, not complete defect coverage. Additional missing checks include retained-only noise averaging after a dropped draw, nonzero clipping-record propagation, exact serialized ESS values, and the failure cases above.

The **two adapted D2 tests are not weakened in their relevant penalty guarantee**. Both fail under an old `10 * max_finite` mutant and a `max_finite` mutant. The first also replaces the obsolete dead-column expectation with the required raise.

**Answers**

**5. Deviations:** Accept all nine in principle. Items 1–4 preserve or strengthen the intended contracts; item 5 provides an explicit archival override; item 6 correctly broadens failure handling and seeds predictive selection, but is incomplete under X03/X04. Exact ties in item 7 are a defensible, disclosed alignment with the package rule. Item 8 corrects the sampling interpretation, subject to X07/X08. Copying inputs in item 9 is appropriate. None should be reverted wholesale.

**6. Open items:**

| Report item | Disposition |
|---|---|
| 1. Dead rows | Can wait. The work order explicitly retains partial-failure penalties; excluding entire rows needs a stated estimator policy. |
| 2. Absolute ESS floor | Prefer fixing warning scaling/consolidation now. Uniform small ensembles should not be described as concentrated, and bootstrap warning floods reduce usefulness. Numerical results are unaffected. |
| 3. Penalty overflow | Can wait; disclosed extreme-value robustness issue. |
| 4. `score_averaged_gp` NaN | Can wait for a separate aggregation-validation fix; not introduced by 2a. |
| 5. Practice candidate fallback | Address before the canonical Case D regeneration. Raising or recording candidate failure needs no inferential choice, but exceeds the specifically queued configuration-handler repair. |
| 6. Other direct cache reads | Can wait for explicitly scoped reader wiring; the serialization-only editable boundary matters. |
| 7. Historical toy HMC caches | Fix now as X05; these remain invalid historical inputs. |
| 8. Environment drift | Author/environment decision. Do not modify dependencies or the frozen lock within this pass. |

**7. Rewrite decision:**

| Item | Decision |
|---|---|
| 2a-1 | **KEEP** |
| 2a-2 | **SIMPLIFY IN PLACE:** unify numerical evaluation-failure handling. |
| 2a-3 | **SIMPLIFY IN PLACE:** one inventory-first preflight, without competing missing-site messages. |
| 2a-4 | **KEEP** |
| 2a-5 | **KEEP** |
| 2a-6 | **KEEP** |
| 2a-7 | **KEEP**, completing the historical registry. |
| 2a-8 | **KEEP**, improving warning behavior for small ensembles. |
| 2a-9 | **KEEP**; compatibility containers are justified. |
| 2a-10 | **SIMPLIFY IN PLACE:** record each completed stage before starting the next; share contextual failure handling. |
| A-5 | **SIMPLIFY IN PLACE:** robust full-covariance factorization and a covariance-discriminating pin. |
| A-7 | **SIMPLIFY IN PLACE:** use the floating rank array returned by `rankdata` directly. |
| A-15 | **KEEP** |
| A-18 | **KEEP** |

**8. Record:** Besides X09, qualify the claims about complete missing-site messages, permissive failure records, and average ranks. The verification claims I repeated succeeded. The dependency diagnosis matches exactly: added `imageio-ffmpeg==0.6.0` and `pypdf==6.14.2`, no removed freeze entries, and unchanged binary-extension aggregate. I cannot independently certify the historical full-suite counts or the unrepeated regenerations.

**What I ran or read**

- Read `git diff 69deeda`, both new Python files, the work order, SYNTHESIS dispositions/adopted plan, Codex C01–C11, Opus C4–C10, relevant D33/D34/D68–D70 records, report, callers and tests.
- Ran nine targeted test files with `-p no:cacheprovider`: **144 passed**.
- Ran frozen MCSE tests and the named capture timing test: **9 passed**.
- Extracted `69deeda` using `git archive`; ran the new tests against it: **12 expected failures**.
- Ran two D2 penalty mutants: **both tests rejected each mutant**. Ran the diagonal-only visualization mutant: **incorrect implementation passed**.
- Replayed E7 and Case E in scratch; checked equality/hashes. Ran the concrete probes listed above and recomputed the dependency-lock differences.
- `git diff --check 69deeda` passed. No repository files were edited, no Git-mutating tests ran, and no network, installs or Mauna inference occurred.