# Implementation review — Fable, 2026-09-05
VERDICT: FINDINGS

Reviewer: Fable 5.1 (claude-fable-5-1), full repository access, checked out on
`paper/case-e-debias` at `a07e61e`; case branches read with `git show`. No file
other than this one was written inside the repository; all reruns and probes
went to the session scratchpad. No git mutation. `stash@{0}` untouched. The
other channels' reports in this directory were not opened.

Test suite (`python -m pytest tests/ -q`, run 2026-09-05 23:30 local):
**1249 passed, 1 failed, 2 skipped, 279 warnings, 585.2 s.** The single
failure is `tests/test_m2cr_environment_freeze.py::test_committed_dependency_lock_reproduces_at_head`;
the assertion diff in the log contains exactly one added line, `+ pypdf==6.14.2`,
which confirms the driver's environment-drift diagnosis. Lock not modified.

Regeneration reruns (all to scratch; none wrote into `runs/`):

| Script | Runtime | Result against the committed artifact |
|---|---|---|
| `vanbork_external_validation.py` (case-A branch) | 1.3 s | 147 JSON leaves identical except `generated` date |
| `e7_convention_sensitivity.py` (case-A branch) | 6.9 s | 144 leaves identical except `generated` date; anchor row 0.183/0.192/0.441/0.184 reproduced |
| `occam_dial_figure.py` (case-B branch) | 10.0 s | all arm values, log Z, ESS, anchor checks identical; only the machine-dependent `optional_local_crosscheck` block differs (unavailable from scratch, as designed) |
| `e6_nesting_monotonicity.py` (case-B branch) | 27.3 s | 8236 leaves identical (bit-exact) |
| `haaf_nested_constraint.py` (case-C branch) | 214.6 s | 414 leaves identical (bit-exact, both BMS* tables and both NUTS/LOO arms); only my scratch relpaths of the cache dependencies differ; cache sha256s match the artifact |
| `regret_curves_mopen.py` (case-D branch, path constants patched only) | 3.9 s | `results.json`, `regret_curves.png`, `README.md` byte-identical |
| `toy_debias_demo.py --out <scratch>` (Case E, on disk) | 63.4 s | `results.json`, `debias_figure.png`, `README.md` byte-identical (sha256 65c9ff5f…, c1153549…, 7096cd6e…, matching the D67 addendum) |

Reproducibility (standard item 5) therefore holds for every manuscript
artifact on this machine. Nothing long-running was launched beyond these.

## Findings

### F1 — S1 — bistar_gp/debias.py:206 (also :131, :144, :225); experiments/bistar_debias_mauna_loa.py:97
Defect: `decompose_model_hmc` discards each draw's conditional covariance
(`for (mean_i, _), comp_name in zip(...)`) and reports `std` as the
across-draw spread of conditional means alone. The four committed D58 poster
cards (`runs/poster_d58/fit_full461_seed0/figures/card6..card8`, pinned
byte-identically into `poster/assets/d58/` with `FIGURES.sha256`) draw their
bands from that field: card 6 labels the full-GP band "95% CI" and the
component bands "±2 SE" (`bistar_gp/viz.py:23`, `:49`); cards 7 and 8 fill
`mean ± 2·std` (`bistar_debias_mauna_loa.py:154`, `:182`, `:205`, `:256`,
`:317`). A second defect compounds it: `compute_debiased` forms the "truth"
band as `sqrt(Σ comp.std²)` ("independent components", `:97`, `:106`),
dropping the inter-component cross-covariance, which the joint posterior
cannot supply once `cov_i` is gone.
Failure scenario: `python experiments/poster_d58_mauna.py --mode render` on
the committed run directory. Recomputing the decomposition from the committed
`samples.npz` (200 draws, training-only loader, no new inference, 12 s) with
the law of total variance gives, in ppm (y_std 14.583), medians over the
500-point grid:

| Band | Committed sd (spread of means) | Honest sd (within-draw + spread) | Ratio honest/committed (min, median, max) |
|---|---:|---:|---|
| trend component | 0.650 | 9.34 | 13.9, 14.4, 15.4 |
| seasonal component | 0.648 | 9.34 | 14.4, 14.4, 14.4 |
| medium_term component | 0.036 | 0.177 | 2.7, 4.9, 20.2 |
| full GP ("95% CI", card 6a) | 0.014 | 0.132 | 2.4, 9.3, 45.7 |
| debiased "truth", Skeptic (seasonal) | 0.648 | 9.34 | 14.4 |
| debiased "truth", Moderate (trend+seasonal) | 0.918 | 0.132 | 0.13, 0.14, 0.31 (poster band 7× too wide) |
| debiased "truth", Believer (all three) | 0.919 | 0.132 | poster band 7× too wide |

The trend and seasonal components share an unidentified constant level within
each draw (the period-1 periodic kernel with lengthscale ≈1.5 carries a
near-constant direction that trades against the RBF trend's level), so the
posterior of each is wide while their sum is tight; the committed cards hide
this entirely. Mean curves are unaffected.
Evidence: scratch script recomputing the committed `decomposition.npz` fields
reproduces the committed `comp__*__std` and `full_std` to ≤7.1e-13, so the
ratios above compare like with like; card 6 legend labels read directly from
the PNG; `poster/assets/d58/FIGURES.sha256` equals the run-dir manifest. The
manuscript is not affected: Case E deliberately bypassed this routine
(`experiments/toy_debias_demo.py:396-435` keeps per-draw variances and the
joint posterior from summed blocks; verified byte-identical today), and no
paper number derives from `debias.py`. The toy poster figures used
`experiments/honest_band_decomposition.py` (`toy_n20_poster_figures.py:80-92`),
so only the Mauna cards carry the defect.
Fix: in `decompose_model_hmc`/`decompose_model_mcmc` retain `diag(cov_i)` per
draw and report `std = sqrt(mean_d var_d + var_d mean_d)` (the construction
`honest_band_decomposition.total_variance_decomposition` and `toy_debias_demo`
already implement); compute truth/bias band variances per draw from
`decompose_component` on the summed truth/bias blocks instead of
`Σ comp.std²`; stop storing per-draw means under the name `samples`
(`:144`, `:225`) and stop labelling the spread "95% CI"/"±2 SE"
(`viz.py:23`, `:49`); re-render the four cards from the committed
`samples.npz` (no new inference); add a two-draw fixture test asserting the
HMC-path `ComponentResult.std` equals the total-variance sd. Author call
needed on whether the presented poster used these cards (open question 2).

### F2 — S2 — bistar_gp/aggregation_v3.py:117 (score_averaged_gp), :356 (soft_transfer_weighted), :250 (run_robust_aggregation), :398 (run_weighted_bms_star); bistar_gp/bms_star.py:368 (compute_G_matrix), :409 (soft_transfer)
Defect: the A4 universe firewall `_assert_candidate_universes_consistent`
runs only inside `run_bms_star` (`:529`). The two primitives and all four
public aggregation entry points in `aggregation_v3` build the G matrix and
normalize without it, so a mixed-universe roster receives well-formed
cross-universe probabilities.
Failure scenario (executed): two `CandidateResult`s tagged `main_ladder` and
`appendix_trend3`: `run_bms_star` raises; `run_weighted_bms_star(...)` returns
[0.4998, 0.5002]; `score_averaged_gp` returns [0.5014, 0.4986];
`run_robust_aggregation` returns [0.5096, 0.4904]; `compute_G_matrix` +
`soft_transfer` returns [0.4998, 0.5002]. No error in any of the four.
Evidence: scratch script; grep of `experiments/` and `bistar_viz/` shows the
only callers of the bypassing entry points are toy scripts
(`bms_star_v3_comparison.py`, `bms_star_v2_comparison.py`,
`practice_EvansEtAL/*`), so no committed number is affected today.
Fix: move the guard into `compute_G_matrix` (every path that builds G through
the package passes through it) and keep the call in `run_bms_star`; add a
test mirroring `tests/test_bms_star_universe_firewall.py` for the four v3
entry points.

### F3 — S2 (statistical; author adjudication) — bistar_gp/bms_star.py:409-470 (soft_transfer), :545-549 (run_bms_star prints raw wins); experiments/e7_convention_sensitivity.py:91-99, :101-105 (case-A branch)
Defect: no diagnostic anywhere measures how many draws carry a pooled
soft-transfer probability. `run_bms_star` computes tau-free draw wins and
only prints them; `prior_sensitivity_study._sir_bms` returns
`hard_win_fractions` but E7 discards them; `BMSStarResult` carries neither a
weight ESS nor win fractions. Section 2.4 requires every soft-transfer table
to report tau-free draw-win fractions and appendix `kl_forward` reporting to
carry a draw-level diagnostic; the Case A tables in §3.4 and
`runs/e7_convention_sensitivity/results.json` carry neither.
Failure scenario: replicating E7's exact call sequence (`pss._sir_bms`, same
caches, seeds and grid), the per-candidate effective number of draws
(Σw)²/Σw² of the pooled Boltzmann weights, out of 1000:

| Metric, τ | Linear | Sinusoidal | Sin+Linear | Quadratic |
|---|---:|---:|---:|---:|
| pw_kl_vcal, τ=1 (headline) | 669 | 685 | 978 | 669 |
| pw_kl_vcal, τ=0.1 | 34 | 38 | 551 | 34 |
| kl_forward, τ=1 | 6.1 | 8.4 | 104 | 6.1 |
| kl_forward, τ=0.1 | 1.15 | 2.25 | 2.47 | 1.14 |

At τ=0.1 the top ten draws carry 43% of the Linear and Quadratic pw_kl_vcal
scores; the appendix `kl_forward` collapse of Sin+Linear to 4.3e-101 at τ=0.1
rests on five, two, zero and five draws with weight above 1e-6 of the maximum.
The headline pw_kl_vcal τ=1 row is not concentrated and its tau-free hard-win
fractions are 0.012 / 0.014 / 0.973 / 0.001.
Evidence: scratch probe `t4/e7_diag.py`; E7 artifact structure; §2.4 text.
Fix: add per-candidate weight ESS and hard-win fractions to `BMSStarResult`
and return them from `run_bms_star`; persist both in the E7 artifact and
quote the ESS beside the appendix `kl_forward` sentence in §3.4 ("collapses
to approximately 0.000" is a 1-to-8-draw statement).

### F4 — S3 — bistar_gp/laplace_evidence.py:135 with bistar_viz/scripts/_viz_spaces.py:196-214; docs/paper-sie-jmp/02-machinery.md §2.2; docs/paper-sie-jmp/00-notation.md (Ḡ row)
Defect: the surrogate is real (`compute_G_at_params` evaluates the metric once
against `avg_gp`), but every committed Z_M number is computed against a single
MAP predictive: `gp_method="map"` yields length-1 sample arrays, so
`extract_gp_predictives` retains one draw and `average_gp_posterior` of one
draw is that draw (`gp_predictives_retained: 1` in both
`runs/occam_dial/figure_results.json` and `e6_results.json`); Case A Target B
uses a point data prior. No manuscript number averages over patterns at all,
so §2.2's "averages before integrating … moment-matched … used throughout"
and the D62/README phrase "MAP-based averaged GP" describe a computation the
paper never performs, and the surrogate's error is exactly zero in every
committed number and uncharacterized otherwise.
Failure scenario: switching `gp_method` to `"hmc"` in `_viz_spaces.averaged_gp`
produces the φ-dependent moment-matching gap with nothing in the code, tests
or artifacts bounding it.
Evidence: artifact provenance blocks; `average_gp_posterior` with N=1 returns
`mu_bar = mean`, `cov_bar = cov`.
Fix: the open SC1 notation amendment should state both facts (surrogate in
general; single MAP predictive, Ḡ(φ)=G(ψ_MAP,φ), in Case B); replace
"averaged GP" with "MAP predictive" in §4 wording that survives; if a
per-draw average is ever wanted, `compute_G_at_params` must take the draw list.

### F5 — S3 — bistar_gp/bms_star.py:295-304, :341-342 (extract_gp_predictives); same pattern at bistar_gp/debias.py:186-189 and bistar_gp/aggregation_v3.py:339-342
Defect: an unrecognized sample site makes `apply_hp_value` return False; the
return value is discarded, the fresh model keeps its initialization value, the
predictive is computed at the wrong hyperparameter, and `hyperparameters`
records the value that was never applied. Draws whose Cholesky fails are
dropped with a print only. Case E hardened exactly this locally (FIX-7); the
package path used by E7, Case B and Case C did not.
Failure scenario (executed): a sample dict containing
`covar_module.kernels.0.base_kernel.alpha_prior` (passes the
`select_hmc_sites` prefix filter) with alpha 0.05 versus 50.0 yields
predictives with max |mean diff| 0.0 and max |cov diff| 0.0, no error, and
recorded alpha 0.05 / 50.0. Any renamed gpytorch site or added kernel
hyperparameter behaves the same way.
Evidence: scratch `t11/silent_site.py`; `_sir_bms` does not assert the
retained count (Case C's wrapper does, E7 does not).
Fix: raise on a False return (as `toy_debias_demo.py:371-377` does); return
the retained count and assert it equals the requested count in `_sir_bms`.

### F6 — S3 — bistar_gp/induced_prior.py:235; :170-199
Defect: `compute_induced_prior` replaces a failed draw's G with
`10 * max(finite)`, the bug class fixed in `compute_G_matrix`; for a
negative-valued metric (pw_nll_gp) the failed draw gets the best score. The
same function makes MLL weighting mandatory; with posterior draws the
likelihood is counted twice (`experiments/bistar_induced_prior.py:143-166`
feeds fit_hmc draws through `compute_log_marginal_likelihoods` into it).
Failure scenario (executed): healthy draws scoring ≈ −16 and one raising draw:
the raising draw contributes −30 and pulls the weights.
Evidence: scratch `t11/induced_prior_sentinel.py`; grep shows only the legacy
`bistar_induced_prior*.py` scripts call it; no paper number.
Fix: reuse `compute_G_matrix`'s strictly-worse penalty; make `log_mlls`
optional with uniform weights documented as correct for posterior draws (the
`average_gp_posterior` docstring already states that rule).

### F7 — S3 — bistar_gp/laplace_evidence.py:486-490 (_multistart_G_optima), bistar_gp/candidates.py:66-67 (_fit_mle), bistar_gp/laplace_evidence.py:697-700 (model_posterior, construction II)
Defect: `res.success` is never inspected. A non-converged L-BFGS-B run would
silently supply E6's "min Ḡ" (E6's embedding check evaluates the same
non-optimal point and would still pass) and the observed-data candidate
instances behind Case A §3.4 and Case C; Construction II discards `conv`.
Failure scenario: `minimize` returning `success=False` (maxiter or
ABNORMAL_TERMINATION) at any start.
Evidence: recomputed today with the same settings: all 103 E6 starts and all
18 candidate fits converged (status 0), and the best values reproduce the
artifact exactly (2.424774370, 2.546229649, 0.045516783), so no committed
number is affected.
Fix: record success/message per start in `_multistart_G_optima` and the E6
artifact; make `_fit_mle` surface failure; carry `conv` into
`ModelPosteriorResult.components`.

### F8 — S4 — bistar_gp/bms_star.py:368 (compute_G_matrix default `kl_forward`), :513 (run_bms_star `metric_names=None` → all 17 registered), bistar_gp/config.py:182-186
Defect: W1 metric roles are convention only. The G-matrix default is the
appendix metric, `run_bms_star` defaults to every registered metric, and
`ExperimentConfig().metrics` does not contain `pw_kl_vcal` at all.
Failure scenario: `compute_G_matrix(gp, cands)` scores with `kl_forward`
silently; an `ExperimentConfig`-driven run never computes the primary metric.
Fix: default to `pw_kl_vcal`; a single `PRIMARY_METRIC` constant
(`mauna_candidate_registry` already pins one) referenced by the defaults.

### F9 — S4 — experiments/toy_tau_metric_comparison.py:58-59, experiments/toy_n20_poster_figures.py:46-47, experiments/mechanism_figure_poster.py:213-214
Defect: three local figure scripts load the withdrawn informative-config cache
`runs/fit_method_metric_comparison/samples_hmc.npz` with no banner check;
their outputs sit in the local poster-candidate directories (`CogSci
Poster/Fig W/bms_tau_curves.png`, `runs/toy_n20_poster/`, the
`sinlinear_ab_hyperparam_prior_vs_posterior.png` overlay). The paper path is
clean (no case script or its imports touches the banned artifacts; see T7).
Failure scenario: regenerating any of those figures silently uses withdrawn
draws.
Fix: a loader guard that refuses the banned paths unless explicitly
overridden, or retire the caches.

### F10 — S4 — experiments/vanbork_external_validation.py:187-191 (case-A branch); experiments/e6_nesting_monotonicity.py:413-481 (case-B branch)
Defect: the external-validation script prints `|ours − paper|` and never
asserts it; E6 turns a violated min-Ḡ inequality into verdict text rather than
a failure. Neither claim is protected by a pytest either (see T10).
Failure scenario: a regression in `soft_transfer` or the hybrid Z_M grid
would regenerate `results.json` with wrong `abs_error_at_min_tau` and exit 0.
Fix: assert the two errors below a stated tolerance; raise in E6 when
`all_hold` is false; add package tests for the Eq. 4 aggregation, its τ→0
hard-win identity, and the Target A/B closed forms on the artifact's inputs.

## Named targets T1-T11

- **T1 — PARTIAL.** Surrogate confirmed at `laplace_evidence.py:126-137` and in §2.2; its error is exactly zero in every committed number because no committed Z_M sees more than one draw (F4). The driver's RuntimeWarning observation is REFUTED as a data problem: the prior-stage means are exactly zero and finite, all 40 covariances are finite (max |cov| 1787), the averaged pattern is finite, and `np.full(40, 1/40) @ np.zeros((40, 40))` alone emits the same three "in matmul" warnings on this numpy 1.26.4/arm64 build; they are spurious BLAS floating-point flags, not non-finite inputs.
- **T2 — CONFIRMED, S1 for the D58 poster (F1);** manuscript unaffected.
- **T3 — REFUTED (clean).** A global shift multiplies every weight by one constant that cancels in `instance_scores / total`; a per-row max equals `−min_i G/τ` and is exactly `normalize_per_draw=True`; the comment is correct, `test_bms_aggregation.py:45-65` pins both directions, and `prior_sensitivity_study._boltzmann_posterior` (E7/Case C "pooled") is a verbatim replica.
- **T4 — CONFIRMED (F3).** No diagnostic exists; headline τ=1 row unconcentrated (ESS 669–978); appendix `kl_forward` pooled numbers rest on 1–8 effective draws.
- **T5 — REFUTED as a sensitivity risk.** On E7's exact path, `n_eval` 30/60/120/240 gives Sin+Linear 0.4398/0.4407/0.4410/0.4411 at τ=1 and 0.639/0.634/0.631/0.629 at τ=0.1; the grid is recorded in Case C's artifact (`x_eval.n: 60`) but not in E7's, and `config.py:172` documents it as a plain default, not a choice.
- **T6 — CONFIRMED (F8).** Convention only.
- **T7 — PARTIAL.** Paper path clean: the five case scripts and `prior_sensitivity_study._sir_bms` read only the prior-IS caches (sha256 match the Case C artifact); `pss` reads the D12 td7 files only in `_informative_stage_b`/`render_report`, which E7 and Case C never call. Local poster/mechanism scripts read the withdrawn cache (F9).
- **T8 — CONFIRMED (F2).** Bypass demonstrated through all six entry points; no experiment does so today. Guard semantics verified: all-untagged passes by design, partial or mixed raises before G (tests present).
- **T9 — clean.** AST guard reads the literal kwargs that actually govern the run (`e1_potential.py:516-523`: step_size 0.1, adapt True, target 0.8, name nuts_e1) and cross-checks route defaults; the routing check is a docstring substring test but the runtime `diag["sampler"] != "nuts_e1"` check backs it. Unmatched-site raise verified. Jitter probe mirrors `compute_cholesky`'s first attempt on the one summed factorization the decomposition performs. Mixture intervals bisect the exact mixture CDF with equal weights over the 1000 retained draws; the LTV inversion `cross = ½(var_composite − var_SE − var_lin)` is exact because per-draw means add and the joint variance from the summed blocks equals `v_SE + v_lin + 2c`. Slope read is licensed by the recorded 4.5e-13 / 1.9e-15 deviations. Byte-identical rerun.
- **T10 — CONFIRMED in part.** Protected: pooled formula and shift invariance, `pw_kl_vcal` = variance-weighted MSE (`test_fit_gp_options.py:242`), moment-matched mean/variance, Laplace vs brute force, IS vs grid, occam volume bookkeeping, τ-scaling identity, Eq. 5 mean identity, run_bms_star firewall, E1 routing. Unprotected: Eq. 4 expected-posterior aggregation and its τ→0 hard-win identity (script-only), Remark 1's one-sidedness (runtime gates only), the van Bork targets (no assertion), the M2bR banner, W1 roles, the HMC-path band semantics (F1), the v3 firewall bypass (F2), the `converged` flags (F7), and prose-to-artifact agreement for every case (none).
- **T11 — PARTIAL.** The 1e6 sentinels cannot fire on any paper path (numpy predict functions and `pw_kl_vcal` cannot raise; the sigma guard never triggers on sigma-free spaces); `converged=True`, `n_clipped=0` for every p1 model; `_multistart_G_optima` has no flag and Construction II drops it (F7), but every optimization behind a committed number is verified converged. `_log_likelihood`'s −1e10 is not on any paper path.

## What I verified clean

- Section 02 against the code, equation by equation: `pw_kl_vcal` is `mean(½(μ_θ−μ_ψ)²/σ²_ψ)` on the GP marginal variances (posterior variance plus noise, `bms_star.py:344`); pooled soft transfer is the documented mean of `exp(−G/τ)` normalized once; row-min and expected-posterior variants match §2.3 (`e7_convention_sensitivity.py:58-71`); `average_gp_posterior` is the mixture mean and covariance with the between-draw term; Laplace `log Z(τ) = −Ḡ*/τ + (d/2)log(2πτ) − ½log|H_Ḡ|` follows from the τ=1 integral by the identity at `laplace_evidence.py:339-343`; `is_log_Z_Mx` is ordinary (not self-normalized) IS with the exact mixture density; `occam` subtracts `log V_ref` consistently across Laplace, MC and IS; §2.2's claim that the variance-calibrated argmin equals weighted least squares holds because `_fit_mle` profiles σ out (Case C's weighted fit is exactly the `pw_kl_vcal` argmin).
- Prose ↔ artifact: every number in §3 (Target B rows 0.792607/0.840781/0.841413/0.841419, 6.4e-7, 7.9589/1.5000, 0.841438 printed quotient, Target A rows, anchor row, movements 0.3133/0.0720/0.0013, 0.441→0.513, `kl_forward` 0.696), §4 (p1/p2/p3, ESS-implied SE 0.0079/0.0172/0.0380 via √(1/ESS−1/n), probability SE 0.005 by the delta method, gap 0.0867 = BF 1.09, margins 2.379/2.501, crossings and all intervals, [1.33, 1.59]), §5 (883, 4464.53, 0.001, 0.000360, LOO table, 0.413/0.256, 0.0129506/19.4028/3.65e-84, init values, aliases 4.939/6.999), §6 (all deviation means, peak gaps, shares, 116.333/116.506, 131.415/131.572, affine identity 300 pairs/1.78e-15/743–7161, raw-win table, mean-G tables, subject-25 values, τ=0.1 medians, BIC 18/32 and 41/50, agreement 39/49/48, 24.4%) and §7 (all recovery, sampler and decomposition numbers) matches the committed `results.json` values.
- Case B's "MAP predictive" is a converged optimum: raw-space gradient norm 2.1e-5 at the point the figure uses; 5000 further Adam steps change the summed negative log joint by ≤2.3e-5 and the hyperparameters by ≤4e-4.
- E6 minima and embeddings: reproduced exactly; all starts converged (F7 is latent).
- Case D reconstruction: exact conditioning at the stored practitioner MAP with normalized jitter 1e-6, latent draws via the eigen-factor, draw-based and plug-in estimands as described; BIC fidelity 5.7e-14.
- Case C: `_fit_mle` with the slope bound is the only region difference; cross-seeded pools force equality; paired SE uses ddof=0 as ArviZ does; chains seeded per chain with `init_to_value` at the common MLE; pointwise log-likelihoods are the Normal density.
- Case E: guard literals, chain-order bookkeeping (`chain_of_draw = i // 500` matches the concatenation order), coverage and RMSE definitions, `max_tree_depth=8` passed through `fit_hmc` to `fit_hmc_e1`, final step sizes read from the adapted kernel.
- Seeding: every paper script seeds its RNG sources explicitly; `_sir_bms` seeds the SIR draw (`sir_seed=42`) and the legacy subsample path (`np.random.seed(42)`); Case D seeds per subject; all seven reruns reproduced.
- dtype: `torch.set_default_dtype(torch.float64)` is set on import of `bms_star`, `aggregation_v3`, `data`, `model`, `fit`; every paper script also casts to double; no float32 boundary found on any paper path.
- Firewall: `run_bms_star` rejects mixed and partially tagged rosters before computing G; the only tagged callers (`bms_star_mauna_loa.py:178`, `m2br_run_common.py:179`) go through it.
- Banner: no committed case script or its import chain reads `runs/fit_method_metric_comparison/samples_hmc.npz` or `runs/toy_tau_metric_comparison/`.

## Open questions for the author

1. Case A §3.4 reports "model probabilities" that are soft-transfer scores of one observed-data MLE instance per family, whereas Remark 1 defines the family score as the best instance per draw; the two coincide only in the labelling. Under `pw_kl_vcal` the hard-win fraction for the Sin+Linear instance is 0.973 against 0.441 pooled at τ=1. Should §3.4 say "instance" and report the win fractions, per §2.4's own rule?
2. Which figures did the presented CogSci poster carry: the four D58 cards (F1), the older `bistar_three_interpretations_hmc.png`/`bistar_debiased_ppm_hmc.png` in `CogSci Poster/Fig X` (same `decompose_model_hmc` bands), and `bms_tau_curves.png` in `Fig W` (withdrawn cache, F9)? The poster source is not in this repository, so the reach of F1 and F9 into the presented artifact is the author's to settle.
3. The trend/seasonal level split in the Mauna kernel is unidentified within a draw (within-draw sd ≈ 9.3 ppm each, sum ≈ 0.13 ppm) because the period-1 periodic kernel with lengthscale ≈1.5 carries a near-constant direction. Is "seasonal cycle" the intended label for a component with a free level, and should the companion line constrain it (zero-mean seasonal or a shared constant)?
4. Case B's Lebesgue-measure verdict (p3: 0.992) integrates over the sigma-free parameter boxes defined in `bistar_viz/scripts/_viz_spaces.py:28-68` (A∈[0.01,5], ω∈[0.1,5], φ∈[−π,π], b∈[−2,2], c∈[−5,5]; Linear and Quadratic boxes likewise). The section names them only as "the canonical visualization boxes" via the README. Should §4 state the boxes explicitly, since raw-Lebesgue Z_M depends on them by construction?
5. Proposed wording for the SC1 notation amendment (F4): "Ḡ(φ): G evaluated against the moment-matched averaged pattern ψ̄ (a plug-in surrogate for the per-draw average, not consistent for it); in Case B ψ̄ is the single MAP predictive, so Ḡ(φ)=G(ψ_MAP,φ) exactly."
6. Should the M2bR banner become a code guard (F9), and should the E7 artifact on the READY case-A branch be extended with weight ESS and win fractions (F3), or should those be carried as a Notes addendum only?
