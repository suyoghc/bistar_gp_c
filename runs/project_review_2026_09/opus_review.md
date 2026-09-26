# Project and code review, 2026-09-26, Opus channel: running as Opus 5.5 (1M context), model ID `claude-opus-5-5[1m]`, reasoning effort max, as reported by my environment

Scope: fix-branch head `ddf8c9d` (`fix/code-review-2026-09`, PR #42) read-only at
`/Users/sc8918/Documents/GitHub/bistar_gp_c-fix`; the six paper branches (PRs #36 to #41)
through read-only git; the manuscript apparatus in the main worktree. Every probe forced
the fix package onto the path and printed `bistar_gp.__file__`; probe scripts and their
outputs are in the scratch directory named in section 6. Nothing was written to either
worktree except this file; `stash@{0}` was not touched.

---

## 1. Verdict

**Code: REVISE.** The nine fixes at `ddf8c9d` hold wherever I could test them and change no
case artifact, but the package keeps several unguarded silent paths (C4, C5, C6, C9, C10),
and three manuscript-facing computations differ from what the manuscript says they are: the
Case D tables were produced by the pre-D2/D6 code and change when regenerated at `ddf8c9d`
(C1, S1), the implemented data pattern ψ differs from the notation's ψ (C2), and the
headline table path scores fixed observed-data fits rather than the per-draw best match
that Remark 1 assumes (C3).

**Project: NOT READY for submission.** Blocking list:

1. **Case D numbers (section 6, and the section 8 sentence built on them).** The three
   stored-BMS* tables come from `experiments/practice_EvansEtAL/results_hmc/`, committed
   2026-02-16 by code whose `fit_hmc` sampled the prior (D6) and whose `soft_transfer` used a
   per-draw shift (D2). Regenerated with the current package, the pw_hellinger winner column
   changes from 22/28, 32/18, 27/23 to 5/45, 4/46, 5/45 and all twelve cohort mean-G values
   move by 0.07 to 0.23 (PF1, C1).
2. **The merge has not happened and cannot happen in an arbitrary order.** Seven branches
   conflict pairwise in `Notes/DECISIONS.md` (21 of 21 pairs), Case C imports a script that
   exists only on the Case A branch, fix pass 2 edits scripts that exist only on case branches, and
   #40/#41 are drafts with open author ledgers (PF5).
3. **Placeholders and draft markers in the assembled text**: Case C's provisional
   Kellen-and-Klauer framing, Case D's `[DRAFT]` title and `[E8B-PLACEHOLDER]` block, a raw
   `[^4]` in the provenance appendix, and a notation row truncated by the build (PF6).

Items I would also clear before submission because a referee will find them and they are
cheap: definitions that the computations contradict (PF2, PF3), the provenance appendix's
"every number regenerates ... into a committed run artifact" sentence (PF9), and a suite
that is red by default and pins no manuscript number (PF8).

---

## 2. Code findings

Severity per the brief: S1 manuscript-path number wrong; S2 wrong under a reachable
configuration; S3 latent, guarded; S4 hygiene.

| ID | Target / module | Sev | Status | Location (at `ddf8c9d` unless noted) | Claim |
|---|---|---|---|---|---|
| C1 | Case D source artifacts | S1 | CONFIRMED | `experiments/practice_EvansEtAL/results_hmc/` (commit `7026ad6`); `run.py:412-423` | Section 6 tables were computed by the pre-D2/D4/D6 package; regenerating at `ddf8c9d` changes them materially |
| C2 | ψ construction (all paper paths) | S2 | CONFIRMED | `bistar_gp/bms_star.py:381-413`; `metrics_v2.py:43-55`; `00-notation.md:9` | The code builds ψ as a hyperparameter-conditional predictive, not as a sampled function with i.i.d. noise; the "argmin coincides with the ML refit" premise never holds on paper paths |
| C3 | Table path vs Remark 1 | S2 | CONFIRMED | `experiments/prior_sensitivity_study.py:664-710`; `02-machinery.md:118-141` | The 0.441/E7/Case D path scores fixed observed-data MLE instances; the nested Linear instance beats Sin+Linear on 26/1000 draws (pw_kl_vcal) and pooled kl_forward favors the restriction, which Remark 1 says cannot happen |
| C4 | T11, `compute_G_matrix` | S3 | CONFIRMED | `bms_star.py:556-573` | Failed metric evaluations become an uncounted finite penalty; a candidate that failed on every draw keeps 0.225 posterior at τ=100; an all-failed matrix yields a uniform posterior |
| C5 | T11, `compute_induced_prior` | S3 | CONFIRMED | `induced_prior.py:245-249, 264-273, 280-296` | Pre-fix fallbacks survive: all-failing predictor returns uniform weights with ESS equal to n and no error |
| C6 | T7, withdrawn caches | S3 | CONFIRMED | `config.py:31-46, 253-273`; `experiments/fit_method_metric_comparison.py:133` | The guard is implemented in `load_hmc_samples`, which no reader of the withdrawn caches calls; the list covers two members of the withdrawn class |
| C7 | T4, draw concentration | S3 | CONFIRMED | `bms_star.py:494-506, 660`; E7 artifact | Weight ESS now exists but never warns and reaches no artifact; committed E7 kl_forward pooled rows rest on ESS 1.1 to 8.4 of 1000 draws for three of the four candidates |
| C8 | T5, evaluation grid | S3 | CONFIRMED | `config.py:200`; E7/Case C scripts (`linspace(min-1, max+1, 60)`) | Primary headline stable to grid size (0.440 to 0.441) but moves with placement (0.412 to 0.445); appendix kl_forward hard fraction moves from 0.696 to between 0.008 and 0.749; choice undocumented |
| C9 | T6, metric roles; roster seam | S3 | CONFIRMED | `bms_star.py:533, 194-206, 763-784`; `config.py:24-25` | Roles are convention: `compute_G_matrix` defaults to kl_forward; the implicit roster depends on import history (10 metrics without pw_kl_vcal vs 17 with it) |
| C10 | T11 residue | S3 | CONFIRMED | `laplace_evidence.py:491-502, 1030-1090, 1144-1199`; `decompose.py:16-38`; `prior_sensitivity_study.py:342-364`; practice `run.py:412-423` | Sweep and ladder APIs discard convergence flags; jitter escalation uncounted; broad `except` plus strict extraction silently drops whole configurations in Case D's generator |
| C11 | T8, firewall reach | S4 | CONFIRMED | `bms_star.py:531-549, 578-614, 679-715`; `induced_prior.py:58-64` | Guard covers every package G builder and rejects partial tags; primitives and the Z_M path cannot see universes (by design, undocumented) |
| C12 | `samples` dual meaning, provenance fields | S4 | CONFIRMED | `debias.py:55-56, 406-410, 461, 498`; `viz.py:27-29, 50-51`; `aggregation_v3.py:443-448` | Conditional means plotted as function draws; `noise_var` holds the last draw's noise; caller's model mutated; weighted path reports unweighted win statistics |
| C13 | T9, Case E script | S4 | CONFIRMED | `paper/case-e-debias:experiments/toy_debias_demo.py:177-218, 844`; `07-debias-bridge.md:114` | Guard accepts the last of several route calls and tests routing by substring; "grid-averaged correlation near −0.85" is a correlation of grid means (the grid mean of the pointwise correlation equals −0.712) |
| C14 | T1, Ḡ surrogate | S4 | CONFIRMED | `laplace_evidence.py:116-154`; `aggregation_v3.py:50-104`; `induced_prior.py:256-275` | No committed number depends on the surrogate gap (all Z_M numbers use one MAP predictive), but the gap is material on draw ensembles and uncharacterized; two Ḡ definitions coexist; the aggregation warnings come from BLAS, not data |

### C1 (S1, CONFIRMED): Case D's stored BMS* tables come from the pre-D2/D4/D6 package

**What is wrong.** Section 6 reads its winner-label table, its pw_nll draw-win table, its
cohort mean-G table and the derived prose ("vary substantially with the legacy pointwise
metric", "the same winner for 39 subjects under pw_hellinger", "from 4.582 to 4.858") from
`experiments/practice_EvansEtAL/results_hmc/` (`06-case-D-mopen-calibration.md:52-124` on
`paper/case-d-mopen`). Those JSONs were committed in `7026ad6` (2026-02-16, Della jobs
4803872/4804071/4804276). At that commit:

- `bistar_gp/fit.py:149-154` scored `obs` through the original module after discarding the
  return value of `model.pyro_sample_from_prior()`, so every `fit_hmc` draw was a prior draw
  (the defect D6 found and fixed in `9f75fb0`, 2026-07-02);
- `bistar_gp/bms_star.py:437` stabilized with `log_weights.max(axis=1, keepdims=True)`, the
  per-draw shift D2 called result-invalidating (fixed in `569ee39`, 2026-06-30);
- `bistar_gp/model.py:25` double-registered kernels through a `ModuleList` (D2/D4).

D4 and D6 both state that archives from that era must be regenerated "before any paper
number is quoted". Neither the Case D section, its README, nor D64 mentions this history.
`run.py:413` also passes no seed to `fit_hmc`, so the stored run was never reproducible.

**Reproduction.** `git show 7026ad6:bistar_gp/fit.py | sed -n 149,154p`; `git show
7026ad6:bistar_gp/bms_star.py | sed -n 437p`; `git log --format="%h %ad" -- experiments/practice_EvansEtAL/results_hmc`.
Then probe P08 regenerated the whole HMC-mode practice run (50 subjects, three
configurations, the unchanged `run.py`, pyro seed 0, 647 s) with the current package and
recomputed the tables with the Case D script's own aggregation functions:

| Quantity (τ = 1.778 for winners) | Stored, quoted in section 6 | Regenerated at `ddf8c9d` |
|---|---|---|
| Winners pw_hellinger, practitioner / moderate / agnostic | 22/28, 32/18, 27/23 | 5/45, 4/46, 5/45 |
| Winners pw_mse | 6/44, 7/43, 7/43 | 7/43, 7/43, 6/44 |
| Winners pw_nll | 10/40, 12/38, 12/38 | 9/41, 10/40, 10/40 |
| Same winner across configurations (hellinger / mse / nll) | 39 / 49 / 48 | 46 / 48 / 49 |
| pw_nll true-family draw wins, Power truth | 39.0%, 39.9%, 41.5% | 38.2%, 39.7%, 42.4% |
| pw_nll true-family draw wins, Exponential truth | 98.7%, 94.6%, 92.1% | 99.9%, 99.9%, 99.6% |
| Cohort mean G, Power truth (G_Power, G_Exp), practitioner | 4.799, 4.775 | 4.661, 4.647 |
| Cohort mean G, Exponential truth (G_Power, G_Exp), practitioner | 5.003, 4.582 | 4.936, 4.483 |
| Range of correctly specified cohort means | 4.582 to 4.858 | 4.483 to 4.661 |

The stored column reproduces the manuscript exactly (so the aggregation is right); the
BIC baseline (18/32) is unchanged, as it should be. The power-truth asymmetry and the
mimicry signature survive; the "substantial" metric dependence of the winner labels and
the configuration dependence of exponential recovery largely do not. One seeded chain per
subject carries Monte Carlo error, but per-subject G spreads are 0.02 to 0.05 (P07), so
cohort-mean shifts of 0.1 to 0.2 and a 22-to-5 change in a winner count exceed it.

**Suggested change.** Regenerate `results_hmc` with the current package and an explicit
seed (and, while regenerating, add `pw_kl_vcal` to the metric list so section 6 can speak
in the W1 primary metric), rerun `experiments/regret_curves_mopen.py`, and rewrite the three
tables and the sentences quoted above; or drop the stored-BMS* tables and keep only the
MAP-conditional regret reconstruction, which is unaffected (it reruns byte-identically).

**Test that would pin it.** A provenance test asserting that every consumed HMC archive
postdates `9f75fb0` (for example a recorded package commit in each subject JSON), plus a
small seeded two-subject regeneration test with pinned draw-win counts.

### C2 (S2, CONFIRMED): the implemented ψ is not the notation's ψ

**What is wrong.** The notation (`00-notation.md:9`) and section 2 (`02-machinery.md:12`)
define one data pattern as a sampled function plus i.i.d. observation noise,
ψ = N(f(x), σ²_ψ I), and section 2 then says that under pw_kl_vcal "the variance-calibrated
argmin coincides with the Gaussian maximum-likelihood refit" when the pattern carries one
scalar variance (`02-machinery.md:35-36`). No paper path draws a function.
`extract_gp_predictives` (`bms_star.py:381-413`) builds, per hyperparameter draw η, the
predictive N(m_η, K_η,post + σ²_η I); the Z_M paths use the same objects (`_viz_spaces.averaged_gp`
with `gp_method="map"`); only the uncommitted mechanism illustration draws functions
(`experiments/mechanism_figure_poster.py:57-72`, main worktree). The notation is also
internally inconsistent: its pw_kl_vcal row calls the metric "GP-uncertainty-weighted
MSE", which presupposes location-varying GP variance, exactly what its ψ row excludes.

**Reproduction.** Probe P02/P03 on the 1000 `toy_elicited` SIR predictives behind the 0.441
headline: per-pattern predictive variance varies by a factor of 1.77 to 6.48 across the 60
evaluation points (median 3.26). For the Linear candidate, the pw_kl_vcal argmin (weighted
least squares) and the ML refit (ordinary least squares) differ in slope by a median 0.0114
(max 0.0204) against a typical slope of 0.239, about 5 percent. Case C's own projection
uses these location-varying weights (`haaf_nested_constraint.py`, `weights = 1.0 / variance`).

**Suggested change.** Define ψ in the notation and section 2 as the implemented object
(the posterior predictive at one hyperparameter draw) and state that the "coincides with
the ML refit" case does not arise on the reported paths; or implement function-draw
patterns. **Test:** pin `extract_gp_predictives`' covariance to the closed-form posterior
covariance plus noise on the posterior branch (mutant M1 below dropped the noise term and
was caught only through the prior-branch test).

### C3 (S2, CONFIRMED): the headline table path is not the table path of Remark 1

**What is wrong.** Section 2's projection paragraph, Remark 1 (`02-machinery.md:118-141`:
"table-path aggregation preserves that ordering and can never favor the restriction at
any τ"), the introduction's contribution (ii) (`01-intro.md:57`) and the Discussion's
"best-instance table-path aggregation" (`08-discussion.md:36`) all assume that each family
is scored per draw by its best available match. Case C implements that. The path behind
the 0.441 headline, the whole E7 table in Case A and the Case D generator does not:
`pss._sir_bms` (`experiments/prior_sensitivity_study.py:664-710`) scores the four
candidates fitted once to the observed data (`bistar_gp/candidates.py`), fixed across draws.
The manuscript never states this.

**Reproduction.** Probe P02 (fix package, committed IS caches): under pw_kl_vcal the Linear
instance has smaller G than the Sin+Linear instance on 26 of 1000 SIR draws and Sinusoidal
on 27 (hard-win credit 0.012, 0.014, 0.973, 0.001); under kl_forward the counts are 275 and
304. Pooled kl_forward at τ = 1 in the committed E7 artifact gives Linear 0.415, Sinusoidal
0.182, Sin+Linear 3.4 × 10⁻¹⁰: the restriction is favored, which Remark 1 says cannot occur
under any convention at any τ. Under the primary metric the ordering happens to hold at
every tested τ.

**Suggested change.** State in section 2 and section 3.5 that the SIR/E7 path scores fixed
observed-data maximum-likelihood instances, and scope Remark 1 (and intro (ii), section 8)
to per-draw projection; or recompute the headline with per-draw projection as Case C does.
**Test:** a unit test that builds a two-candidate nested pair as fixed instances and shows
the per-draw ordering can fail, documenting the scope of the guarantee.

### C4 (S3, CONFIRMED): `compute_G_matrix` still substitutes a finite score for a failed evaluation

`bms_star.py:556-573` converts `LinAlgError`/`ValueError` from a metric into
`max_finite + 10 (|max_finite| + 1)` (or 1e6 when nothing is finite) and records nothing.
The penalty cannot win, but it keeps mass at the top of the paper's τ range. Probe P05
(injected metric failing for one of four candidates on every draw): the failed candidate
receives 0.000, 0.000, 0.077 and 0.225 posterior at τ = 0.1, 1, 10, 100; an all-failed
matrix becomes all 1e6 and a uniform posterior, with no exception and no field on
`BMSStarResult`. No failure occurs on the headline path: recomputing both SIR G matrices
entry by entry from the predictives reproduces them exactly, so no penalty was substituted. **Change:** count failures per column on the result and raise under a
strict flag, matching FIX-5 in the Laplace path. **Test:** inject a failing metric and
assert the error or the recorded count.

### C5 (S3, CONFIRMED): `compute_induced_prior` keeps the sentinels FIX-5 removed elsewhere

`induced_prior.py:245-249` turns a raising predictor into G = ∞ (silently excluded),
`:272-273` sets G = 1e6 when every draw's metric fails, and `:280-293` falls back to uniform
weights when nothing is finite. Probe P05: a predictor that raises everywhere returns
uniform weights with ESS 50.0 of 50 and no error. No case script calls this function.
**Change:** the strict/NaN semantics of `compute_G_at_params`. **Test:** all-failing
predictor raises under strict.

### C6 (S3, CONFIRMED): the withdrawn-cache guard does not guard the readers

`load_hmc_samples(allow_withdrawn=False)` (`config.py:253-273`) refuses the two
`WITHDRAWN_CACHES` entries (`config.py:31-34`), but every script that actually reads those
caches uses `np.load` directly: `experiments/fit_method_metric_comparison.py:133`, and in the
main worktree the untracked `experiments/toy_tau_metric_comparison.py:84` and
`experiments/toy_n20_poster_figures.py:67` (the CogSci poster's toy panels, poster-only
under W7). The list also omits members of the class the M2bR record withdrew (D33/D34:
informative td7/td10 HMC, historical VI, vague and gamma_relaxed HMC), for example
`runs/fit_method_metric_comparison/samples_hmc_td7.npz`, `samples_vi*.npz` and
`runs/prior_sensitivity/samples_vague_hmc_td7.npz`, which `load_hmc_samples` would load
silently. No paper-branch script reads any of them (grep over all case scripts), so no
manuscript number is exposed. **Change:** route the readers through the guard (or guard at
`np.load` call sites with `is_withdrawn_cache`) and derive the list from the D33/D34
classification. **Test:** each reader script refuses a fixture path under a withdrawn name.

### C7 (S3, CONFIRMED): T4, draw concentration is now measurable but never reported

`boltzmann_weight_ess` and `hard_win_statistics` (`bms_star.py:494-528`) populate
`BMSStarResult` (`:660-661`), but nothing warns and no case script or artifact records
them. Probe P02 on the E7 G matrices (regenerated; E7 reproduces with zero difference): pw_kl_vcal ESS at τ = 0.1 is 33.7, 37.9,
551.4, 33.8 and at τ = 1 at least 669 (so the 0.441 rests on broad support); kl_forward ESS
is 1.2, 2.2, 2.5, 1.1 at τ = 0.1 and 6.1, 8.4, 103.9, 6.1 at τ = 1. At τ = 0.1 one draw
carries 93 percent of Linear's pooled weight; at τ = 1 five draws carry 82 percent. Section
2 prescribes pairing the appendix pooled result "with the aggregation convention and a
draw-level diagnostic" (`02-machinery.md:161`); section 3.5 reports the collapse without
one. **Change:** write per-candidate ESS into E7 and Case C outputs and warn below a
threshold. **Test:** a fixture with one dominant draw that triggers the warning.

### C8 (S3, CONFIRMED): T5, grid placement matters and is not documented as a choice

Probe P06 re-extracted the same 1000 SIR draws on six grids (fix package):

| Grid | pw_kl_vcal pooled τ=1 (Sin+Linear) | τ=0.1 | kl_forward hard fraction (Sin+Linear) | kl_forward pooled τ=10 (Sin+Linear) |
|---|---|---|---|---|
| [−11, 11] × 60 (used) | 0.441 | 0.634 | 0.696 | 0.245 |
| [−11, 11] × 30 | 0.440 | 0.639 | 0.674 | 0.284 |
| [−11, 11] × 120 | 0.441 | 0.631 | 0.706 | 0.044 |
| [−10, 10] × 60 | 0.439 | 0.596 | 0.749 | 0.267 |
| [−13, 13] × 60 | 0.412 | 0.590 | 0.008 | 0.004 |
| [−9, 9] × 60 | 0.445 | 0.576 | 0.747 | 0.250 |

The primary conclusion (Sin+Linear highest everywhere) is robust and the headline moves by
at most 0.03; the appendix correspondence "0.696 equals the D18 hard fraction" quoted in
section 3.5 holds only for this placement (with [−13, 13], Sinusoidal takes 0.943 of hard
wins). The manuscript never states the grid (60 points on [x_min − 1, x_max + 1]) as a
choice. **Change:** one sentence in section 2 plus a grid-sensitivity line in the E7 README.

### C9 (S3, CONFIRMED): T6, metric roles are convention; the implicit roster depends on import history

`PRIMARY_METRIC` and `APPENDIX_METRICS` (`config.py:24-25`) only drive a warning on the
implicit `run_bms_star` path (`bms_star.py:763-784`). `compute_G_matrix` defaults to
`metric_name="kl_forward"` (`:533`), the appendix-only metric, silently; `soft_transfer`
records `"unspecified"` when the name is omitted (the deferred fix-pass-2 item). Probe P05
ran `run_bms_star(metric_names=None)` in two fresh processes: 10 metrics without
pw_kl_vcal, versus 17 with it after `import bistar_gp.laplace_evidence`; any `METRICS[...]`
miss, even a typo, also registers the v2 metrics (`_MetricRegistry.__missing__`,
`:202-206`). Every paper script passes metrics explicitly. **Change:** make the default
`PRIMARY_METRIC` (or required), and build the implicit roster from an explicit constant.

### C10 (S3, CONFIRMED): T11 residue

- `model_posterior_tau_sweep` (`laplace_evidence.py:1030-1090`) and
  `ablation_ladder_posteriors` (`:1144-1199`) return only posteriors, discarding
  `converged`, `n_clipped` and `n_starts_failed`; `_select_start` (`:491-502`) prefers the
  lowest finite objective even when that start did not converge.
- `compute_cholesky` (`decompose.py:16-38`) escalates jitter up to 1e-2 without counting;
  the package paths (`extract_gp_predictives`, `decompose_model_hmc`,
  `compute_log_marginal_likelihoods`) inherit that. Case E counts it itself (0 escalations).
- Stage A of the headline pipeline catches every exception into `lml = -inf`
  (`prior_sensitivity_study.py:350-360`); the committed IS caches contain 0 such draws
  (checked all 180,000).
- Case D's generator wraps `fit_hmc` and `extract_gp_predictives` in `except Exception:
  continue` (`experiments/practice_EvansEtAL/run.py:412-423`); with strict extraction one
  failing draw now drops a whole configuration for that subject without a trace. It did not
  fire in the P08 regeneration (all 50 subjects kept 3 configurations).

On the paper paths nothing fired: Case B's committed Laplace arm reports `converged: true`,
`n_clipped: 0` for all four models, and my Case B/E6 reruns raised no `EvaluationFailure`.

### C11 (S4, CONFIRMED): T8, the firewall is complete for package G builders only

Probe P05: all-untagged rosters pass, partially tagged and two-universe rosters raise, a
single universe passes (`bms_star.py:718-745`, called at `:549` and in
`aggregation_v3.py:130`). Concatenating two legally built matrices from different
universes and normalizing through `soft_transfer` or `aggregate_convention` returns
[0.333, 0.333, 0.333] without complaint, and `ModelParameterSpace` has no universe field,
so the Z_M path cannot enforce A4. No experiment concatenates. **Change:** document that
the primitives carry no universe identity.

### C12 (S4, CONFIRMED): the `samples` dual meaning and provenance fields

`ComponentResult.samples` holds per-draw conditional means on the draw paths
(`debias.py:55-56`), yet `bistar_gp/viz.py:27-29, 50-51` plots them as "function samples",
so a figure built from `decompose_model_hmc` now shows law-of-total-variance bands around
spaghetti that carries only the between-draw spread. A positional rebuild (the poster
driver's `rebuild_decomposition_result`) gets `samples_kind="function_draws"` by default
for saved conditional means. `DecompositionResult.noise_var` holds the last retained draw's
noise (`debias.py:461, 498`; P04: 0.2352 reported vs posterior mean 0.2558);
`decompose_model_mcmc` writes each draw into the caller's model parameters and leaves them
at the last draw (`:406-410`); `soft_transfer_weighted` labels its result `"weighted"` and
reports unweighted hard-win statistics next to likelihood-weighted posteriors
(`aggregation_v3.py:443-448`). All are fix-pass-2 hygiene.

### C13 (S4, CONFIRMED): T9, Case E's guards hold; two small weaknesses

Verified: the AST guard passes on this library (my rerun reached the sampler), the site
raise works, the jitter probe tests the same matrix `compute_cholesky` tries first, the
mixture interval brackets and bisects correctly, and the variance identity used for the
cross-covariance holds exactly. Weaknesses: the guard keeps the last `_run_e1_nuts_route`
call it walks (`toy_debias_demo.py:180-184`) and checks routing with a substring test
(`:215`). The prose "a grid-averaged correlation near −0.85" (`07-debias-bridge.md:114`)
reports the correlation of grid-mean moments (−0.848, `:844`); probe P09 (rerun of the
chains) gives a grid mean of the pointwise total correlation of −0.712 (median −0.806,
range −0.94 to −0.04). **Change:** "the correlation implied by the grid-mean variances".

### C14 (S4, CONFIRMED): T1, the Ḡ surrogate

No committed number depends on the surrogate gap: Case B and E6 build `avg_gp` with
`gp_method="map"` (`bistar_viz/scripts/_viz_spaces.py:150-214`), one predictive, for which
the moment-matched pattern and the per-draw average coincide; Case A's Target B has its
own point data prior; Cases C and D use per-draw G. On a draw ensemble the gap is material
and nowhere characterized. Probe P03 (1000 SIR predictives, uniform-box MC, 40,000 points
per model, package cross-check error 0.0): Ḡ_avg − Ḡ_plug ranges 0.61 to 80.2 for Linear
(median ratio 1.46), and normalized Z_M priors move by up to 0.15 (occam=True, τ = 3:
Sinusoidal 0.28 versus 0.43; occam=False, τ = 3: Sin+Linear 0.84 versus 0.78). Two
definitions coexist in the package: `compute_induced_prior` averages per-draw G (the
notation's reading), `compute_G_at_params` uses the plug-in. The driver's follow-up on the
`aggregation_v3.py` matmul warnings closes: `w @ m` on random finite 150 × 80 inputs emits
the same three RuntimeWarnings under numpy 1.26.4 on this machine, with |matmul − einsum|
= 1.5 × 10⁻¹⁶, so the warnings are BLAS floating-point flags, not non-finite data.

### Named targets T1 to T11 (explicit judgements)

| Target | Judgement |
|---|---|
| T1 | PARTIAL. Gap real and φ-dependent (C14); affects no committed number (MAP, N = 1); uncharacterized; warnings are a BLAS artifact |
| T2 | CONFIRMED fixed. `std` equals an independent numpy law-of-total-variance computation to 3.2 × 10⁻¹⁵ and brute-force function sampling to 0.9 percent; group of all components equals the full posterior; pre-fix spread understated the total by a median factor 3.0 to 6.1 on toy draws. No manuscript band inherits the defect; the D58 poster does (PF4) |
| T3 | VERIFIED. `soft_transfer` equals `aggregate_convention("pooled")` bitwise; a per-row shift reproduces `rowmin` exactly, so the code comment's argument holds; the global shift cancels |
| T4 | CONFIRMED (C7) |
| T5 | CONFIRMED (C8) |
| T6 | CONFIRMED convention only (C9) |
| T7 | CONFIRMED guard gap (C6); no paper-facing path reads a withdrawn cache |
| T8 | CONFIRMED complete for package G builders; primitives and Z_M path outside it (C11) |
| T9 | VERIFIED with two S4 notes (C13) |
| T10 | PARTIAL. Package formulas are protected (6 of 6 mutants killed); no manuscript number is (PF8) |
| T11 | Laplace sentinels fixed and silent on paper paths; residue in C4, C5, C10 |

---

## 3. Project findings

| ID | Item | Severity | Status | Location | Claim |
|---|---|---|---|---|---|
| PF1 | P1 | BLOCKER | CONFIRMED | section 6; `08-discussion.md:49`; D64 | Case D quotes numbers the project's own D4/D6 declared unusable; regeneration changes them (C1); undisclosed |
| PF2 | P1 | MAJOR | CONFIRMED | notation rows ψ, τ, Ḡ; `02-machinery.md:12, 35-36, 61` | Definitions contradict the computations: ψ (C2); the τ row's claim that the zero-temperature limit "recovers hard best-match partitioning" contradicts section 2's pooled limit; Ḡ gloss (open SC1) |
| PF3 | P1 | MAJOR | CONFIRMED | sections 1, 2, 3, 8 | "Table path" names two estimators; Remark 1's guarantee is violated by the manuscript's own E7 kl_forward row (C3) |
| PF4 | P1 | MAJOR | CONFIRMED mechanism, PLAUSIBLE magnitude | `runs/poster_d58/`; `poster/POSTER_PLAN.md:70-71`; `poster/assets/d58/SOURCE.md` | FIX-2 inheritance: no manuscript statement; the D58 poster cards 6 to 8 and their "honest bands" statements do, unmarked |
| PF5 | P2 | BLOCKER | CONFIRMED | all seven branches | 21/21 pairwise DECISIONS conflicts; A-before-C; fix pass 2 entangled; merge plan below |
| PF6 | P3 | BLOCKER | CONFIRMED | `05-case-C...md:8`; `06-case-D...md:1, 220`; B-provenance; A-notation | Placeholders, draft markers, build leaks; open ledgers on #40 and #41 |
| PF7 | P3 | MINOR | CONFIRMED | D68 Status; section footnotes; PR #22 | Stale statuses and branch-name citations that die at merge |
| PF8 | P4 | MAJOR | CONFIRMED | `tests/` | No test pins a manuscript number; suite red by default; pins gated |
| PF9 | P5 | MAJOR | CONFIRMED | B-provenance appendix | "Every number regenerates ... into a committed run artifact" is false; list of what a reader cannot regenerate |
| PF10 | P3 | MINOR | CONFIRMED | `03-case-A...md:157-166`; `02-machinery.md:156-161` | W1 says appendix-only, the text says "confined to the appendix", but no kl_forward appendix exists; kl_forward results appear in the section 3 body |
| PF11 | P1 | MINOR | CONFIRMED | sections 4, 7; build | Correlation label (C13); one footnote repeated eight times in section 7; "MAP-based averaged GP" averages one pattern; one arrow glyph and one "is the substantive form" construction |

### PF1 (BLOCKER): Case D

Evidence in C1. Also affected: `08-discussion.md:49` ("Case D contributes the first
correct-specification reference material ... known-truth distributions of mean G"), which
rests on the stored mean-G values, and the section 6 claim that winner labels "vary
substantially with the legacy pointwise metric" (39 agreeing subjects under pw_hellinger
become 46). The regret reconstruction (MAP-conditional, fresh GP at stored MAP
hyperparameters) is sound and reruns byte-identically. The author sign-off on #38
(2026-08-12) predates this provenance question; it needs re-adjudication.

### PF2 (MAJOR): definitions that the computations contradict

- ψ: C2.
- τ: the notation says that the zero-temperature limit "recovers hard best-match partitioning" (`00-notation.md:16`, written there with an arrow glyph);
  section 2 says the pooled limit concentrates on globally smallest divergences. Pooled
  kl_forward at τ = 0.1 on the E7 matrices gives [0.578, 0.000, 0.000, 0.422] while hard
  fractions are [0.010, 0.290, 0.696, 0.004]; pooled pw_kl_vcal gives 0.634 for Sin+Linear
  against a hard fraction of 0.973.
- Ḡ: the "averaged across data patterns" gloss versus the moment-matched plug-in (open
  SC1 on #40). C14 adds that the reported Z_M numbers average over nothing (one MAP
  predictive), which the MAP framing already discloses.
- Build: the soft-transfer row renders as `p(θ \` (A-notation.tex), so the pooled
  definition is missing from the appendix.

### PF3 (MAJOR): two estimators called "the table path"

Evidence in C3. Referee risk: section 2's Remark 1 promises that the table path can never
favor a nested restriction; section 3.5 then reports pooled kl_forward giving Linear 0.415
against Sin+Linear 3.4 × 10⁻¹⁰ on the same toy.

### PF4 (MAJOR): FIX-2 inheritance

No manuscript section inherits the understated bands: Case E deliberately bypassed
`decompose_model_hmc`, and Cases A to D compute no decomposition band. The D58 poster does:
`experiments/poster_d58_mauna.py:459-477` saved the pre-fix `std` into
`runs/poster_d58/fit_full461_seed0/decomposition.npz`, which rendered cards 6, 7 and 8, and
the poster plan's bullet "Skeptic narrow, Moderate wider, Believer widest ... HMC (not MAP)
needed for honest bands" (`poster/POSTER_PLAN.md:70-71`) describes those bands. Neither
`poster/assets/d58/SOURCE.md` nor `runs/poster_d58/` marks them; D68 records the defect,
not the poster. The order-of-magnitude figure in D68 is plausible (my toy analog: 3 to 6
fold) but I did not reproduce it, because that requires Mauna conditioning. The toy poster
panel used the honest-band workaround and is unaffected, but it reads a withdrawn cache
(poster-only under W7; C6).

### PF5 (BLOCKER): branch topology and merge plan

**Demonstrated.** Legacy `git merge-tree <base> <a> <b>` (no object writes) over all 21
pairs of {fix, A, B, C, D, E, synthesis}: every pair reports exactly one "changed in both"
file, `Notes/DECISIONS.md`, with one conflict hunk (each branch appends after D58). No other
textual conflict exists. Case C (`haaf_nested_constraint.py`) imports
`e7_convention_sensitivity`, which `git ls-tree` finds only on `paper/case-a-vanbork`, so #37
cannot run on its own branch or on a main that has C but not A. Case C also adds `arviz` to
`requirements.txt`/`pyproject.toml`; Case E imports `arviz` without declaring it. PR #22
(CHATLOG) also conflicts with current main.

**API compatibility.** I reran every case script from a scratch copy of the merged
experiments tree against the fix package: Case A `vanbork_external_validation.py` and
`e7_convention_sensitivity.py` identical apart from the `generated` date field; Case B
posteriors, log Z, crossings and margins identical, ESS fields differing by at most
2.1 × 10⁻¹⁴ relative (the new `log_weight_ess`); Case C, Case D and Case E byte-identical
(sha256 `e25b69d1`, `3e9a9543`/`1ac70d22`, `65c9ff5f`/`c1153549`/`7096cd6e`). Strict
extraction, `compute_induced_prior` weighting, the raising `soft_transfer_weighted`,
`PredictiveList` and `DecompositionResult.group` break none of them. The one latent
interaction is Case D's generator (C10).

**Merge order I would use.**

1. Resolve the lock-drift failure (author: uninstall `pypdf` or re-lock under
   authorization) so main is green before and after each merge.
2. Merge #42 (fix) first: it is a fast-forward of main, changes no case artifact, and
   gives every later branch the fixed package.
3. Merge #39 (Case A), then wire `check_external_targets` into
   `vanbork_external_validation.py` and turn the two fixture-gated FIX1 pins into ordinary
   tests reading the in-repo artifacts (both pass today when supplied: 2 passed).
4. Merge #37 (Case C) after A, or first replace `e7.aggregate` with
   `bistar_gp.aggregate_convention` (fix pass 2); that swap is output-neutral (the
   aggregate/`e7.aggregate` fixture pin passes bitwise, and E7 reproduces with zero
   difference through `aggregate_convention`).
5. Merge #36 (Case B); do not regenerate its JSON unless the ESS last-digit drift is
   accepted.
6. Hold #38 (Case D) until PF1 is resolved and re-reviewed.
7. Merge #41 (Case E) and then #40 (synthesis) after their ledgers close and PF2, PF3,
   PF6, PF9 are addressed.

For `Notes/DECISIONS.md`, resolve every conflict by D number (A carries D60, D61, D65, so
branch order would interleave numbers), or land one Notes-only PR that places D60 to D68 in
order and then merge code branches with that block already present. Reconcile with the
uncommitted working copy in the main worktree (its D60 to D67 text) before merging, and
leave `stash@{0}` alone.

### PF6 (BLOCKER): placeholders, draft markers, open ledgers

- `05-case-C-nested-constraints.md:8`: "[Provisional framing: Kellen and Klauer (2020) has
  not yet been read ...]".
- `06-case-D-mopen-calibration.md:1` title "[DRAFT]" (though #38 was marked Ready) and
  `:220` the `[E8B-PLACEHOLDER] UNBUILT OPTIONAL MODULE` block.
- `tex/sections/B-provenance.tex:8`: a raw `[^4]` from the Case A footer; `A-notation.tex`:
  truncated soft-transfer row; one arrow glyph in the τ row.
- Open ledgers: #40 SC1 (Ḡ framing and notation amendment), SC2 (pooled-limit separation),
  the Codex re-review item (dischargeable by citing the 2026-09 Codex implementation
  review), uncommitted mechanism script; #41 F1 (commit `stage_a_toy_elicited.json`?), F3
  (floor sentence, optional N sweep), F2 option, the same Codex item, and the synthesis
  assembly items F9 (section 8.6 "all four reviewer rounds for every case") and the 8.5
  footnote. Fix pass 2 list (fix1_synthesis): required `metric_name` with two callers,
  removal of the `samples` dual meaning, `check_external_targets` wiring, Case C's
  `aggregate_convention` swap, provenance-prose trim; items 3 and 4 need case branches merged.

### PF7 (MINOR): record hygiene

D68's Status line still says the Kimi K3 and GLM 5.3 outputs are pending, while its Update 2
records them landed. D4/D6's regeneration mandate is not reflected in D64. Six footnote
citations in sections 2 and 8 name branches (`on paper/case-b-occam-dial` and so on), and
section 1 reads its cases "from the case branches"; all of these stop resolving at merge. PR #22 conflicts with main in `Notes/CHATLOG.md`.

### PF8 (MAJOR): the test suite and the manuscript

- Run: 1346 passed, 5 skipped, 1 failed, 714 warnings in 532.35 s (8 min 53 s wall), matching
  the map. The failure is `test_committed_dependency_lock_reproduces_at_head`; recomputing
  the lock read-only shows the single difference `+pypdf==6.14.2` (324 vs 325 lines), with
  `dists` and binary-extension digests equal, which confirms the driver's diagnosis.
- Skips: two FIX1 pins gated on `FIX1_FIXTURE_DIR` (both pass when I supplied the Case A
  script and the committed van Bork artifact), Mauna period structure, the full freeze walk,
  and local prior-sensitivity artifacts absent in the fix worktree.
- Mutation probe on the paper path (22 test files, 220 tests, each mutant a scratch copy of
  the package): dropping observation noise from ψ killed by 1 test (prior branch only);
  pw_kl_vcal weighting by the candidate's variance, 2; dropping the between-draw term from
  the averaged pattern, 1; expected-posterior normalized over draws, 14; the τ log term
  removed from Laplace Z_M, 5; the D2 per-row shift restored, 4. Formula regressions are
  caught.
- Nothing pins a manuscript number: no test mentions 0.934, 0.693, 0.992, 0.696 or any
  Case C, D or E value; the two assertions of 0.441 compare a constant with itself
  (`test_m2c_mcse_strategy.py:84`, `test_m2c_freeze_dm_constants.py:15`). The case scripts'
  own gates (Case B anchors at tolerance 0.003, Case C structural gates, Case D fidelity
  asserts) run only when the scripts run. A suite that is red by default also hides new
  failures.

### PF9 (MAJOR): what a reader could not regenerate

`B-provenance.tex` opens "Every number reported in this manuscript regenerates from a named
script in the source repository into a committed run artifact." Counter-examples:

- Case D's source (`results_hmc`): produced by an unseeded run of pre-D6 code, not named in
  the provenance appendix, and not regenerable to the quoted values (C1).
- The `toy_elicited` prior-IS caches behind the 0.441 headline, E7 and Case C are committed
  on no branch. Their sha256 in Case C's `results.json` match the local copies
  (`a07c4c8e...`, `60d2bdf4...`, `5efb94be...`), and seed 0 regenerates bit-identically from
  `prior_is_run` in 79 s (probe P10), so the gap is documentation, not determinism.
- `runs/viz_unification/p3_priors_canonical/` (section 3.6's 0.992) is untracked; the Case
  B script recomputes the same arm (0.992) with the fix package, so cite that instead.
- `runs/prior_sensitivity/stage_a_toy_elicited.json` (section 7) and
  `experiments/mechanism_figure_poster.py` (section 2) are local material, disclosed.
- E7 and van Bork JSONs carry a `generated` date, and Case B's figure JSON records whether
  the untracked local table was present, so a clean clone cannot reproduce those bytes.

Verified in the other direction: `build_tex.py --out <scratch>` regenerates the whole
`tex/` tree identically from the branch heads, and the Case E oracle reproduces byte for
byte in 60 s.

### PF10 and PF11 (MINOR)

PF10: W1 keeps kl_forward appendix-only; section 3 says the attribution "remains confined to
the appendix", but the manuscript has only two appendices (notation, provenance), and the
kl_forward attribution with its numbers appears in the section 3.5 body. PF11: C13's label;
the md-to-tex build repeats one long footnote eight times in section 7, and others four
to ten times in sections 3, 5 and 6; section 4 calls the single MAP predictive an
"averaged GP"; `07-debias.tex:123` "Whether that gap persists ... is the substantive form of
the expectation" is an "X is the Y" construction.

### P1 section-by-section judgement

| Section | Script into artifact | Reproduces at `ddf8c9d` | Judgement |
|---|---|---|---|
| 1 Introduction | none (summaries) | n/a | contribution (ii) and (iii) inherit PF3 and PF1 |
| 2 Machinery | none (code references) | n/a | surrogate paragraph accurate; ψ, τ, table-path statements contradicted (PF2, PF3); prescribes a draw-level diagnostic nobody reports (C7) |
| 3 Case A | `vanbork_external_validation.py`, `e7_convention_sensitivity.py` | yes (date field only); `check_external_targets` passes (A 0.0, B 6.40 × 10⁻⁷) | numbers right; kl_forward paragraph grid-fragile and ESS 1 to 8 (C7, C8) |
| 4 Case B | `occam_dial_figure.py`, `e6_nesting_monotonicity.py` | yes (ESS last digits) | numbers right; W4 framing present |
| 5 Case C | `haaf_nested_constraint.py` | byte-identical (needs A's e7 and the IS caches) | numbers right; provisional framing open |
| 6 Case D | `regret_curves_mopen.py` over `results_hmc` | byte-identical from the stored inputs, but the inputs are stale | BLOCKER (PF1) |
| 7 Case E | `toy_debias_demo.py` | byte-identical | numbers right; correlation label (C13) |
| 8 Discussion | none | n/a | Case D sentence inherits PF1; "best-instance table path" inherits PF3 |

### P3 constraints of HANDOFF-cases section 0

M2bR banner honored (no withdrawn cache or informative-config HMC number in any section);
W1 honored in substance with PF10's wording problem, and Case D discloses that its legacy
metrics predate W1; W4 framing present wherever `informative`-configuration MAP numbers
appear; no Mauna material in any section; style: one arrow glyph in the notation appendix,
one "is the" construction, no "lives"/"sits".

### P6 publication readiness

Risks, in order: Case D's tables (certain to change); a referee finding Remark 1
contradicted by section 3.5; the notation appendix contradicting section 2 twice; an
unmerged manuscript whose provenance footnotes cite branches; no regression protection for
any reported number once the case scripts land on main.

---

## 4. Verified correct (coverage for the synthesizer)

- Suite counts and the lock-drift diagnosis (PF8).
- Law-of-total-variance decomposition: component, full and group moments exact against
  numpy (≤ 3.2 × 10⁻¹⁵); brute-force sampling within 0.9 percent; `diag(cov) = std²`; group
  of all components returns the full posterior (P04).
- Pooled aggregation: global shift cancels; `soft_transfer` equals
  `aggregate_convention("pooled")` bitwise; per-row shift equals `rowmin` (P05).
- E7 through the fix package: zero difference in every variant, metric and τ; the 0.441
  anchor reproduces (0.440674); 1000/1000 predictives retained, 883 unique (P02).
- All five case artifacts regenerate under the fix package (PF5); `check_external_targets`
  passes on the committed and the rerun van Bork artifacts; both fixture-gated pins pass.
- Case E oracle byte-identical (60 s); section 7 numbers match its `results.json` (0.197,
  0.072, [0.033, 0.323], 1.430/0.403, 174/201, widths 1.836/1.032/1.458, variances
  0.2368/0.1752/0.0667, R-hat 1.0025, ESS 602.4/502.6, 0 divergences, 0 escalations).
- Spot checks: Case A (0.183/0.192/0.441/0.184; movements 0.313/0.072/0.001; Target B rows
  and 6.40 × 10⁻⁷), Case C (999/1 split, gap 0.000360, LOO difference 0.413 with SE 0.256).
- Candidate restart selection change (FIX-5) is inert on the N = 20 and N = 50 toy data:
  all restarts report success, parameters identical to the pre-fix package (P01).
- Hellinger constants: `/8` matches the equal-variance Bhattacharyya distance and the base
  `_scalar_hellinger`.
- `max_tree_depth` passes through `fit_hmc` to `fit_hmc_e1` to the NUTS route
  (`fit.py:398-414`, `e1_potential.py:478-523`).
- Case B Laplace arm converged with no clipping; no strict evaluation failure on any rerun.
- Prior-IS caches: no failed log-likelihood among 180,000 draws; seed 0 regenerates
  bit-identically.
- `tex/` regenerates identically from branch heads.

---

## 5. Recommendations (priority order, effort, what each unblocks)

1. **Regenerate Case D's source run** with the current package and a fixed seed, adding
   `pw_kl_vcal` to its metrics; rerun `regret_curves_mopen.py`; rewrite the three tables,
   the quoted prose and the section 8 sentence; brief re-review. About 1.5 days (the
   regeneration itself takes 11 minutes). Unblocks #38 and the Discussion.
2. **Fix the definitions**: ψ as the hyperparameter-conditional predictive; the τ row's
   pooled limit; the Ḡ amendment (SC1); state the fixed-instance scoring of the SIR/E7 path
   and scope Remark 1, intro (ii) and section 8 to per-draw projection. About 1 day.
   Unblocks #40's ledger and removes the sharpest referee target.
3. **Clear placeholders and build defects** (Case C framing, Case D draft markers and E8B
   block, `[^4]`, truncated notation row, repeated footnotes, branch-name citations, the
   B-provenance sentence). About 0.5 day plus reading Kellen and Klauer. Unblocks submission
   formatting.
4. **Execute the merge plan** (PF5), with the lock decision first and DECISIONS.md resolved
   by D number. About 1 day. Unblocks fix pass 2 and CI on the assembled code.
5. **Fix pass 2 plus residual code items**: `metric_name` option (i); retire the `samples`
   dual meaning in `viz.py`; wire `check_external_targets`; the Case C swap; strict
   semantics in `compute_G_matrix` and `compute_induced_prior` (C4, C5); default metric
   (C9); reader-side withdrawn-cache guard with a complete list (C6); convergence flags in
   the sweep APIs and a jitter-escalation count (C10); `noise_var` as a posterior summary
   (C12). About 2 days. Unblocks honest failure reporting.
6. **Artifact-level regression tests** after merge: un-gate the two FIX1 pins; add fast
   tests that rerun Case A (1.4 s and 8 s), Case D (3.8 s) and Case B (47 s) scripts or
   check committed JSON invariants (the 0.441 anchor, Target A/B errors, Case B anchors);
   commit the 7 MB of IS caches or document the 79-s stage-A command. About 1 day. Unblocks
   PF8 and PF9.
7. **Diagnostics and disclosures**: per-candidate ESS in E7 and Case C outputs; one
   sentence on the evaluation grid with the C8 numbers; Case E's correlation wording. About
   0.5 day.
8. **Poster erratum**: a dated note in `poster/assets/d58/SOURCE.md` (or a D68 addendum)
   marking cards 6 to 8 as pre-fix bands. About 0.5 day. Closes PF4.

Total about eight working days, inside the two-week window, with items 1 to 4 first.

---

## 6. Commands run and outcomes; what I could not run

Scratch: `/private/tmp/claude-501/-Users-sc8918-Documents-GitHub-bistar-gp-c/c59de7f7-0de6-4670-81b4-02e7226015e7/scratchpad/proj_review/opus/`
(probe scripts in `probes/`, reruns in `out/` and `mirror/runs/`, committed references in
`ref/`, mutants in `mutants/`).

| Command | Outcome |
|---|---|
| `cd bistar_gp_c-fix && PYTHONDONTWRITEBYTECODE=1 python -m pytest tests/ -q -p no:cacheprovider -rs` | 1346 passed, 5 skipped, 1 failed, 714 warnings, 532.35 s (8:53 wall) |
| read-only `build_dependency_lock` recomputation vs `docs/m2c_freeze/m2cr_dependency_lock_v1.json` | only `+pypdf==6.14.2`; dists and binary digests equal |
| `probes/p01_candidate_restarts.py` against both packages | identical candidate fits; all restarts successful |
| `probes/p02_sir_repro.py` (fix package; IS caches read from main worktree) | E7 max difference 0.0; ESS and win statistics (C7, C3); 4.1 s |
| `probes/p03_t1_surrogate.py` | surrogate gap and Z_M prior shifts (C14) |
| `probes/p04_t2_decomp.py` | T2 verification (≤ 3.2 × 10⁻¹⁵; brute force 0.9%); `noise_var` last draw |
| `probes/p05_seams.py` | T3, T6, T8, T11, roster and `samples_kind` results |
| `probes/p06_t5_grid.py` | grid table (C8) |
| `probes/p07_caseD_hmc_rerun.py`, `probes/p08_caseD_full_regen.py` | two-subject and 50-subject Case D regeneration (C1); 647 s |
| `probes/p09_caseE_corr.py` | −0.848 vs −0.712 (C13) |
| `probes/p10_is_regen.py` | IS seed 0 bit-identical, 79 s |
| mirror reruns: `vanbork_external_validation.py` (1.4 s), `e7_convention_sensitivity.py` (8.0 s), `occam_dial_figure.py` (14.3 s), `e6_nesting_monotonicity.py` (32.4 s), `haaf_nested_constraint.py` (3:43), `regret_curves_mopen.py` (3.8 s), `toy_debias_demo.py --out` (59.8 s) | see PF5 |
| `FIX1_FIXTURE_DIR=<scratch> pytest` on the two gated pins | 2 passed |
| six mutants, 22 paper-path test files each (control 220 passed, 2 skipped) | killed by 1, 2, 1, 14, 5, 4 tests |
| `git merge-tree <base> <a> <b>` over 21 branch pairs; `git ls-tree`; `git show 7026ad6:...` | PF5, C1 evidence |
| `python docs/paper-sie-jmp/build_tex.py --out <scratch>` then `diff -rq` | identical to `docs/paper-sie-jmp/tex` |
| numpy matmul warning probe | BLAS artifact (C14) |
| `pytest tests/test_zmx_estimators.py::test_prior_stage_flows_to_finite_is_log_Z -W always::RuntimeWarning` | 1 passed; the three matmul warnings still fire at `aggregation_v3.py:91` on validated finite inputs |
| entry-by-entry recomputation of both SIR G matrices (pw_kl_vcal closed form, package `kl_forward`) | max difference 0.0; no penalty substitution on the headline path (C4) |
| final `git status --short --ignored` and `find -newer` on both worktrees | unchanged; `stash@{0}` intact |

Not run: anything on Mauna Loa (by constraint), so the D58 card magnitude stays PLAUSIBLE;
no LaTeX compilation; no network; no change to the dependency lock. The Case D regeneration
used one seeded chain per subject and configuration, which bounds but does not remove Monte
Carlo error in the regenerated column.

Signed: Opus channel.
