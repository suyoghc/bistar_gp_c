Model: gpt-6-astra, effort: xhigh

# Implementation review — gpt-6-astra, effort xhigh, 2026-09-05

VERDICT: FINDINGS

Review completed on 2026-09-06 against paper/case-e-debias at a07e61ea6433b0ec0bd430e31a37324a61e2669b, with the other manuscript branches read through git show. I read the governing handoff, machinery specification, frozen notation, five case sections, and both substitution records. I did not read the other independent review.

There are two demonstrated D58 artifact errors, six substantive implementation or specification findings, and two unexercised numerical failure paths. Successful regeneration does not establish that the regenerated quantity has the claimed interpretation.

## Test-suite result and review limits

The requested suite did not reproduce the driver's 1249 passed, 1 failed, 2 skipped baseline in this sandbox.

- The initial run was interrupted before completion. On retry, the suite encountered 46 collection errors because ArviZ's daily-warning code attempted to update its cache outside the writable sandbox after the date changed.
- With an in-memory patch limited to that warning's date lookup, the completed run collected 1252 tests: **1240 passed, 9 failed, 3 skipped, 279 warnings in 354.24 seconds**. Pytest caching and Python bytecode writes were disabled.
- One failure confirmed the known dependency-lock drift: pypdf==6.14.2 is the sole added freeze entry; the lock was not changed.
- Three failures in test_m2br_drivers arose because my stdin-based bootstrap was not importable by multiprocessing spawn. These are review-harness failures, not demonstrated sampler defects.
- One additional environment-freeze test launched a fresh subprocess that again encountered ArviZ's cache-write denial.
- Four real-root integration tests attempted git stash create to snapshot the dirty working tree and failed at the sandbox boundary. No such mutation succeeded. I did not bypass the restriction or retry those operations.

The completed run therefore does not support a claim that the eight additional failures are repository regressions. It also does not independently establish the driver's full green result apart from the known lock failure.

I made no implementation, manuscript, dependency, or committed-artifact changes. The requested tests and libraries used temporary fixtures/cache directories; regeneration outputs were intercepted in memory. The sole deliberate output-file edit is this report. No new Mauna inference was performed. The review emphasizes the shared numerical machinery and the five manuscript paths; it is not a claim of exhaustive verification of every branch in all 34 package modules.

## Findings

### F1 — S1 — bistar_gp/debias.py:206

Defect: The HMC decomposition discards each draw's conditional component covariance and reports only the spread of conditional means. The same defect exists in decompose_model_mcmc at line 131. The handoff's identification of decompose_model is inaccurate: that MAP wrapper retains conditional covariance.

Failure scenario: With repeated identical hyperparameter draws, these wrappers return zero component and full-function standard deviations even when the conditional GP posterior variance is positive. For varying draws they still omit the positive within-draw contribution.

Evidence: [The HMC wrapper](/Users/sc8918/Documents/GitHub/bistar_gp_c/bistar_gp/debias.py:206) drops the covariance and constructs diagonal covariance matrices at line 225. The required identity is Cov(f | y) = E[Cov(f | y, eta)] + Cov(E[f | y, eta]). I opened [the committed D58 decomposition](/Users/sc8918/Documents/GitHub/bistar_gp_c/runs/poster_d58/fit_full461_seed0/decomposition.npz): all three stored component standard deviations exactly equal the population standard deviation of their 200 stored conditional-mean rows; full_std likewise exactly equals the standard deviation of their summed means. The D58 fit/render path consumes these values, and the committed interpretation figure was inspected. Thus the omission reaches displayed uncertainty. The artifact does not retain conditional covariances, so its missing variance cannot be quantified from the saved decomposition alone; the 200-draw record does not justify a numerical correction factor.

Fix: Retain and combine conditional covariance and between-draw covariance, including the full function. Distinguish conditional-mean rows from function samples. Correct the interpretation of affected frozen poster bands through the author's record process; this finding requests no Mauna experiment.

### F2 — S1 — experiments/bistar_debias_mauna_loa.py:97

Defect: Combining labeled components assumes posterior independence. Additive prior components become dependent after conditioning on their sum.

Failure scenario: Assign every component to truth and none to bias, as the D58 “Believer” interpretation does. The truth process must then have the same uncertainty as the full process. The implementation instead adds marginal variances and drops all cross-covariances.

Evidence: [compute_debiased](/Users/sc8918/Documents/GitHub/bistar_gp_c/experiments/bistar_debias_mauna_loa.py:97) explicitly sums component standard deviations squared under an “independent components” comment. On the opened D58 artifact, the grid mean of this sum is **0.003969823126724952**, whereas the grid mean of the variance of the summed stored rows is **0.0000017302240418020973**: a factor of **2294.398315370894**. These are normalized-coordinate variances. The latter agrees exactly with stored full_std squared. This is an internal contradiction even under F1's incomplete, conditional-mean-only convention. The committed [three-interpretations figure](/Users/sc8918/Documents/GitHub/bistar_gp_c/runs/poster_d58/fit_full461_seed0/figures/card7_three_interpretations.png) uses this grouping path.

Fix: Compute group uncertainty from the joint posterior, using summed kernel blocks or joint component draws with conditional covariance retained. Add an invariant that assigning every component to truth reproduces the full posterior band. Adding F1's missing marginal variances alone does not fix this defect.

### F3 — S2 — bistar_gp/fit.py:150 at historical commit 7026ad6

Defect: The committed historical producer associated with Case D's stored HMC comparisons calls pyro_sample_from_prior but discards the returned sampled modules. Its observation distribution is evaluated on the original model and likelihood. It also places an already multivariate observation inside a data plate.

Failure scenario: Execute the historical nested pyro_model while conditioning every hyperparameter sample site first to 0.1 and then to 2.0. The likelihood should change. In the failure probe its mean and covariance were identical, with maximum differences both zero; the observation had batch shape [8] and event shape [8].

Evidence: Read-only history places the stored aggregate and subject artifacts at commit 7026ad61c53e274f4bc0fb12ebda809bb4f9e5fe. At that commit, fit.py lines 149–154 discard both sampled-module return values before evaluating the likelihood. I executed that historical function structure with the historical model in the review environment, using a trace rather than new HMC. Case D explicitly imports these stored comparisons and describes their draws as HMC-derived. Its new reconstruction checks BIC residual fidelity and reconstructs MAP-conditional functions; neither checks the historical HMC target. The source files retain no hyperparameter draws or producing runtime SHA that would establish an alternative corrected producer. Consequently, I do not assert corrected winner counts or that the current single-kernel defect in F4 caused the historical numbers.

Fix: Resolve the producer provenance before treating the legacy comparison summaries as posterior evidence. If they came from the committed historical path, withdraw that interpretation or regenerate the Case D comparisons through a corrected, explicitly identified route with retained samples. A byte-identical replot cannot resolve this issue.

### F4 — S2 — bistar_gp/model.py:76

Defect: Hyperparameter selection and assignment omit the site names generated by a single-kernel model.

Failure scenario: Build the single scaled RBF model used by the practice experiment. Supply two posterior rows with lengthscales 0.05 and 2.0, outputscales 0.2 and 4.0, and identical noise 0.1. Predictive extraction should reflect the different kernels. Instead, both retained predictions have identical means and covariances.

Evidence: [Model construction](/Users/sc8918/Documents/GitHub/bistar_gp_c/bistar_gp/model.py:32) leaves a single kernel directly under covar_module. Its sites are covar_module.outputscale_prior and covar_module.base_kernel.lengthscale_prior. [select_hmc_sites](/Users/sc8918/Documents/GitHub/bistar_gp_c/bistar_gp/model.py:76) accepts only the multi-kernel covar_module.kernels prefix or the legacy kernel_components prefix. apply_hp_value also returns False for the single-kernel names. [Predictive extraction](/Users/sc8918/Documents/GitHub/bistar_gp_c/bistar_gp/bms_star.py:286) therefore retains only noise and leaves the fresh kernel at its defaults. The concrete eight-training-point probe retained 2/2 predictions, with zero maximum differences in both mean and covariance; its metadata contained only noise. This is a live source path in the Case D practice experiment.

Fix: Handle single-kernel site paths in both helpers and validate that every required sampled kernel parameter was selected and applied. Test prediction sensitivity to supplied draws for both single-kernel and additive models.

### F5 — S2 — bistar_gp/bms_star.py:323

Defect: The package's GP table row differs from the row defined in the frozen notation and machinery section. The specification samples a function f and forms N(f(x), noise I). Extraction integrates the function out and forms N(m_eta, S_eta + noise I), once per hyperparameter draw.

Failure scenario: At one location, let the conditional latent mean be zero, latent variance one, observation variance one, and candidate mean one. The implemented variance-calibrated divergence is 1/4. Averaging the specified function-level divergence over f distributed as N(0,1) gives E[(1-f)^2/2] = 1. These operations are not equivalent.

Evidence: [The extractor](/Users/sc8918/Documents/GitHub/bistar_gp_c/bistar_gp/bms_star.py:323) computes conditional means and covariances, adds observation variance, and never draws f. Its prior-only branch likewise returns zero mean with the kernel covariance. In the observed prior-stage test path, all 40 extracted means were identically zero. In contrast, [frozen notation](/Users/sc8918/Documents/GitHub/bistar_gp_c/docs/paper-sie-jmp/00-notation.md:9) and synthesis section 2.1 explicitly define function-level rows. Case A's E7 and Case C use the predictive-distribution path. This discrepancy exists before F6's additional averaging over hyperparameters.

Fix: Explicitly choose and consistently define the implemented predictive-distribution row, or implement the specified function-level row and revalidate affected comparisons. Integrating f out is a legitimate modeling choice, but nonlinear divergence and Boltzmann transformations prevent presenting it as an equivalent computational shortcut.

### F6 — S2 — bistar_gp/laplace_evidence.py:135

Defect: The known moment-matched plug-in computes G of an averaged predictive distribution, not the average of G. The synthesis now discloses this correctly; the frozen definition and estimator interpretation remain unresolved.

Failure scenario: Use two equally weighted scalar predictives with means 0 and 2 and variances 1 and 4. For candidate mean q, the intended mean divergence is q²/4 + (q-2)²/16, minimized at q=0.4 with value 0.2. The moment-matched distribution has mean 1 and variance 3.5, giving (q-1)²/7, minimized at q=1 with value zero.

Evidence: The numerical probe returned intended/surrogate values **0.2 / 0.05142857142857143** at q=0.4 and **0.3125 / 0** at q=1. [compute_G_at_params](/Users/sc8918/Documents/GitHub/bistar_gp_c/bistar_gp/laplace_evidence.py:135) and [average_gp_posterior](/Users/sc8918/Documents/GitHub/bistar_gp_c/bistar_gp/aggregation_v3.py:77) implement exactly this distinction. No general error bound was found; without restrictions on the component means and variances, no uniform bound follows.

The prior adjudication overstates Case B's exposure: its committed E4/E6 construction retains **one MAP predictive**, so the hyperparameter-averaging gap is exactly zero there. Case A's cited MAP-based model-prior arm has the same qualification. I did not identify a numerical error in a five-case headline caused specifically by this multi-draw surrogate gap. Multi-draw model-prior consumers remain affected.

Fix: Resolve the frozen-notation ledger item and keep the intended and implemented quantities distinct. Any claim of approximation accuracy needs its own conditions and verification. Do not describe additional draws as curing the structural gap.

### F7 — S2 — bistar_gp/metrics_v2.py:70

Defect: Both variance-calibrated and mean-only Hellinger implementations use twice the correct equal-variance Gaussian exponent.

Failure scenario: Compare N(0,1) and N(1,1). Squared Hellinger distance is 1-exp(-1/8), approximately 0.11750309741540454. Both affected functions return 1-exp(-1/4), approximately 0.22119921692859512.

Evidence: The executed analytic probe matched the correct value in the existing base pointwise Hellinger implementation, but obtained the incorrect value from [pw_hellinger_vcal](/Users/sc8918/Documents/GitHub/bistar_gp_c/bistar_gp/metrics_v2.py:70) and [pw_hellinger_mean](/Users/sc8918/Documents/GitHub/bistar_gp_c/bistar_gp/metrics_v2.py:108). Their docstrings repeat the same incorrect formula. The primary pw_kl_vcal path is unaffected; I found no demonstrated five-case primary number using these two erroneous variants.

Fix: Use denominators 8 times the variance and 8, respectively, and add independent Gaussian-identity checks. Because 1-exp(-d) is nonlinear, a temperature rescaling does not generally repair this error.

### F8 — S2 — bistar_gp/bms_star.py:368

Defect: The universe commitment is enforced by run_bms_star but can be bypassed through the public candidate-to-score primitives.

Failure scenario: Pass one candidate tagged main_ladder and another tagged appendix_trend3 to compute_G_matrix, then pass its result to soft_transfer. A one-row scalar example with candidate means zero and one returns the normalized cross-universe vector [0.62245933, 0.37754067].

Evidence: The executed primitive call returned that vector. Passing the same roster to [the existing guard](/Users/sc8918/Documents/GitHub/bistar_gp_c/bistar_gp/bms_star.py:480) raised the intended ValueError. [compute_G_matrix](/Users/sc8918/Documents/GitHub/bistar_gp_c/bistar_gp/bms_star.py:368) has candidate metadata available but never invokes the guard. Direct primitive callers exist in experiments, but I found no actual mixed-universe manuscript roster among the inspected callers. All-untagged legacy rosters are intentionally accepted; partially tagged rosters are correctly rejected by the guarded wrapper.

Fix: Validate universe consistency at the public boundary that still has candidate metadata, and preserve validated roster identity through normalization where practical. Extend firewall tests to the primitive call sequence.

### F9 — S3 — bistar_gp/laplace_evidence.py:126

Defect: Prediction failures become ordinary finite energies, allowing invalid models to acquire plausible evidence and even win comparisons.

Failure scenario: Let predict_fn raise on every parameter value. compute_G_at_params returns 1e6. An eight-sample MC normalizer then returns finite log Z = -1000000 and ESS = 8. Against a valid one-point candidate whose mean error is 2000 with GP variance one, the valid divergence is 2e6, so normalizing the two energies gives the failed candidate probability one.

Evidence: All three outcomes were reproduced. [The sentinel](/Users/sc8918/Documents/GitHub/bistar_gp_c/bistar_gp/laplace_evidence.py:126) carries no failure count. _log_likelihood similarly substitutes -1e10. Optimizer exception fallbacks can return starting points, and model_posterior omits convergence status from its assembled result. An ESS measures concentration of the values it receives; it cannot certify that those values came from successful evaluations.

This did **not** fire in my Case B arm regeneration: 350868 energy evaluations produced zero sentinel or non-finite results, and all 408 observed optimizer calls completed successfully. Historical failure counts cannot be recovered where artifacts did not record them. A failed proposal optimizer in defensive importance sampling need not itself bias an otherwise exact integral; the finite failure energy is the distinct correctness problem.

Fix: Separate invalid evaluations from legitimate large divergences, fail when no valid support remains, and propagate failure/convergence diagnostics to assembled evidence. Do not certify an all-failed integral with an ordinary ESS.

### F10 — S3 — bistar_gp/aggregation_v3.py:408

Defect: Weighted aggregation stabilizes likelihood weights and Boltzmann weights separately, then multiplies them. Their maxima can occur on different rows, causing every product to underflow and triggering an incorrect uniform posterior.

Failure scenario: Use G = [[1000,1001],[0,0]], log_weights = [0,-1000], and tau = 1. All separately formed products underflow. The function returns [0.5,0.5], whereas joint log-space aggregation gives [0.59384548,0.40615452].

Evidence: The executed probe reproduced both the returned vector and the independent log-space calculation. [The affected implementation](/Users/sc8918/Documents/GitHub/bistar_gp_c/bistar_gp/aggregation_v3.py:408) exponentiates the two factors separately and falls back to uniform when their product has zero total. No committed manuscript number was demonstrated to encounter this extreme case.

Fix: Combine log_weight_i - G_ij/tau before stabilization and use log-sum-exp over rows and candidates. Distinguish genuinely absent support from representational underflow.

## Named targets T1-T11

- **T1 — PARTIAL.** The structural surrogate gap is confirmed in F6, but the committed Case B/E6 single-predictive computations have zero such gap. The handoff's warning diagnosis is refuted: I observed divide-by-zero, overflow, and invalid matmul warnings at line 77 with 40 finite, identically zero input means and finite output mean/covariance. The underlying numerical-library warning cause remains unresolved; no corrupted manuscript output was established.
- **T2 — CONFIRMED, with corrected function names.** F1 affects the MCMC/HMC wrappers and reaches D58 bands; the MAP wrapper retains conditional covariance. F2 independently corrupts grouped uncertainty.
- **T3 — REFUTED as a defect.** A single global shift multiplies every candidate score by the same factor and cancels on normalization. Row-dependent shifts change draw influence and implement row-min semantics, not generally expected-posterior semantics. The canonical False default and its tests agree with D60.
- **T4 — CONFIRMED.** Reconstructing E7's saved-pool computation showed concentration of model-score contributions: for appendix kl_forward at tau=0.1, one row supplies 93.048% of total pooled mass and the descriptive row ESS is 1.1498; at tau=1, row ESS is 6.6084 and the ten largest rows supply 96.082%. Here row ESS means 1/sum(a_i²) after normalizing a_i = sum_j exp(-G_ij/tau); it is not MCMC ESS. The primary pw_kl_vcal at tau=1 has row ESS 837.74. Prior-IS ESS 4464.53 diagnoses a different weighting stage. No automatic model-score concentration diagnostic fires, although the manuscript already describes the appendix's outlying-draw sensitivity.
- **T5 — PARTIAL.** Grid size and domain are substantive choices. E7/C use 60 points over [-11,11], B/E6 use 80 over [-10,10], E uses 201 over [-10,10], and D explicitly distinguishes 50 subject-span scoring locations from its 20 early-trial reconstruction locations. These choices are recoverable in scripts/artifacts; C, D, and E disclose them in the sections. No spatial-grid convergence study was found. Temperature-grid and IS-seed sweeps do not establish spatial-grid stability. No demonstrated headline reversal from grid refinement is claimed.
- **T6 — PARTIAL.** Primary/appendix roles are observed by the inspected manuscript-specific reporting paths, but not enforced by a reporting-context API. compute_G_matrix still defaults to kl_forward, and generic runners can emit it. That permits misuse; it is not evidence that an inspected primary table violates W1.
- **T7 — PARTIAL.** Local poster/mechanism scripts still load the withdrawn informative HMC cache and can render posterior outputs without a withdrawal check. I found no ingestion of that cache into the five current case computations. The synthesis explicitly restricts its mechanism illustration to prior-only use. Executable legacy code remains a provenance hazard, not proof of a new paper-facing withdrawn estimate.
- **T8 — PARTIAL.** The public primitive bypass is confirmed in F8. The suspicion that partially tagged rosters pass the guarded wrapper is refuted. Entirely untagged legacy rosters remain permitted by design.
- **T9 — PARTIAL.** Case E's sampler guard, selected-site assignment check, base-jitter probe, mixture quantiles, and total-covariance inversion work on the committed route. Artifact regeneration is exact. Its reported correlation is correctly a ratio formed from grid-mean moments; interpreting it as the arithmetic mean of pointwise correlations would be incorrect.
- **T10 — CONFIRMED.** Existing tests protect substantial algebra and protocol behavior, but do not cover the posterior-band wrapper, group covariance identity, single-kernel extraction, function-level versus predictive-distribution row definition, the two Hellinger variants, primitive firewall bypass, or the demonstrated numerical fallbacks. Passing tests coexist with F1–F10.
- **T11 — CONFIRMED as a failure path; no demonstrated Case B activation.** F9 establishes the failure. The monitored Case B regeneration had zero sentinel evaluations, zero optimizer exceptions, and zero unsuccessful optimizer results. Other historical activation counts are not recoverable from missing diagnostics.

## What I verified clean

- **Case A:** Both external-validation target structures regenerated exactly in memory in 0.64 seconds. E7's existing-pool calculation reproduced its pooled rows to within 3.9e-16 in 5.71 seconds. The expected-posterior, row-min, and pooled distinction is real; pooled's Target A failure is disclosed.
- **Case B:** The three evidence arms reproduced every checked log normalizer and model probability with maximum absolute difference zero in 10.79 seconds. The MAP predictive count was one. The directly checked Laplace optima converged with no clipped Hessian directions. This was computation-only arm regeneration; I did not rerun the complete E6 temperature/seed experiment or claim byte verification of its figure.
- **Case C:** I read the committed nesting and PSIS-LOO artifact and traced their construction. The paired LOO difference recomputes from saved pointwise differences as 0.4126590617546144 versus stored 0.4126590617546153; the paired SE recomputes exactly as 0.25588686781820247. The stored nested-feasibility check reports zero violations and exact equality on nonnegative free slopes. I did not rerun Case C's full sampler, so this is an artifact/formula check, not an independent sampler reproduction.
- **Case D reconstruction:** All three outputs—results.json, README, and PNG—regenerated byte for byte in 0.53 seconds with output writes intercepted. All 100 BIC fidelity checks passed; maximum error was 5.684341886080802e-14. The smallest reconstructed covariance eigenvalue was -2.4004932222200888e-15, within the stated 1e-8 tolerance. The distinction between MAP-conditional function-draw deviation and posterior-mean plug-in deviation is implemented and disclosed. F3 concerns the older stored comparisons, not this successful reconstruction.
- **Case E:** Results JSON, README, and figure reproduced byte for byte in the independent in-memory run. Its runtime was not separately retained in my review record. The component and composite intervals use the retained Gaussian mixtures directly: averaging Gaussian CDFs and bisecting at 0.025 and 0.975. They retain conditional variance and are not intervals obtained by averaging per-draw endpoints or using only conditional means.
- **Case E safeguards:** The current AST/signature guard passed; changing the mirrored target acceptance to 0.9, initial step size to 0.2, or adaptation flag to False raised RuntimeError. Selected hyperparameter assignment failures raise before decomposition. The decomposition and subsequent composite calculation both factor the same summed training matrix with the same noise and base jitter, so the probe covers the matrix used by both. The reproduced run recorded zero extra-jitter draws.
- **Case E covariance:** The inversion of total variance includes both conditional cross-covariance and covariance of conditional means. The reported -0.847701 correlation summary correctly equals mean cross-covariance divided by the square root of the two mean total variances. The mean pointwise correlation over the 200 locations with nonzero linear variance is about -0.711905; correlation is undefined at x=0 because the linear component is degenerate there. These are different summaries, and neither difference invalidates the mixture bands.
- **Shared algebra/tests:** The base Gaussian divergence identities, canonical pooled normalization, scalar-noise projection equivalence, and reference-volume bookkeeping are supported by independent analytic or quadrature checks in the existing suite. The low-level fixed-hyperparameter decomposition is consistent with Gaussian conditioning. These checks do not protect the wrapper-level omission in F1.

The main missing regression checks should assert externally specified identities: total posterior variance at fixed hyperparameters, invariance when all components are relabeled truth, prediction changes when single-kernel draws change, correct equal-variance Hellinger distance, and explicit failure on wholly invalid evidence support. The paper-specific E7 concentration diagnostic and spatial-grid stability are additional evidence gaps, not substitutes for those correctness tests.

## Substitution ratification

**Synthesis: ratify the substituted fixes and the driver's mechanical verification for SC1, SC2, SC3, and SC5, with one correction to SC1's impact statement.**

SC1 correctly identifies a structural, parameter-dependent surrogate gap and now explicitly says that increasing draw count does not remove it. The frozen-notation amendment remains an author decision. I would not ratify the implication that using avg_gp alone establishes a nonzero gap in the reported Case B/E6 numbers: their retained predictive count is one.

For SC2, I reach the driver's FIX disposition. The global-minimum limit of pooled aggregation differs from the draw-wise hard-win limit, and the committed Target A rows substantiate the distinction. For SC3, the revised algebraic scalar-variance justification holds, and the uncommitted mechanism check is disclosed rather than presented as committed numerical validation. For SC5, the current discussion retains the four-source non-identifiability account. Those dispositions stand independently of this review's additional implementation findings.

**Case E: ratify the numerical and methods dispositions of the substituted round, including the three rejected single-reporter findings.**

I agree with the required corrections to initialization provenance, restriction to the observed N=20 result, component-width reporting, shared axes, evaluation/debias distinction, empirical-Bayes conditioning, hyperparameter assignment checks, sampler-setting checks, jitter accounting, move-fraction labeling, and trajectory-level divergence description. The final artifacts reproduce.

I would also reject F2, F5, and F6 as mandatory methods fixes on the reviewed text: the coverage claim does not assert a comparative calibration result; the direct drift-removal calculation supports “most”; and the latent-band convention is explicitly stated. Additional comparator coverage would enrich the presentation but is not needed to make those particular claims true.

I agree with the disposition rejecting the subsequent jitter-coverage finding, but refine the driver's explanation: the script performs another composite factorization after component decomposition; it uses the same matrix, so this does not leave a different solve unprobed.

MF4 requires a precise reading. The stored field explicitly names a correlation formed from mean total variances, and the text identifies those source moments. Under the default-refute standard, I do not promote the ambiguous phrase “grid-averaged correlation” to a new demonstrated statistical error. I ratify the computed summary, not an interpretation of -0.85 as the arithmetic average of pointwise correlations. The latter is about -0.712.

This discharges the request for an independent Codex re-review of the substituted work. It does not resolve the separate author decisions on frozen notation, local initialization evidence, or manuscript assembly.

## Open questions for the author

1. Which row definition should govern the manuscript: a sampled latent function with scalar observation noise, or the hyperparameter-conditional predictive distribution implemented by extraction? F5 requires a scientific definition, separate from the already acknowledged averaged-pattern surrogate.
2. Is there a producing runtime/commit record for Case D's stored HMC comparisons that supersedes the demonstrably incorrect producer committed alongside them? The retained summaries cannot establish this themselves.
3. How should the affected frozen D58 uncertainty figures be qualified in the author record? The saved means establish F1/F2, but do not contain the missing conditional covariance needed to quantify corrected bands.
4. Will model-score concentration and spatial-grid sensitivity be stated as remaining evidence limits? The existing prior-IS ESS and temperature sweeps answer different questions.
5. Should the Case E correlation summary be explicitly named “correlation formed from grid-mean covariance and variances” at assembly? Its formula is already explicit in the artifact; this would remove the remaining interpretive ambiguity.

