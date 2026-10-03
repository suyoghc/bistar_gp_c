# Adversarial cross-check of single-reporter findings — Fable, 2026-09-06

Checker: Fable 5.1 (claude-fable-5-1), full repository access, on
`paper/case-e-debias` at `a07e61e`. Read restriction lifted by the author on
2026-09-06 after `fable_review.md` was filed; I then read `COLLATION.md`,
`codex_review.md`, `kimi_k3_review.md`, and `glm_5_3_review.md`. Standard
applied: attempt to refute each single-reporter finding against the code and
the committed artifacts; default REFUTED when the evidence is ambiguous;
never check my own findings. All probes ran in the session scratchpad; no
repository file other than this one was written; no git mutation.

Single-reporter items after the driver's clustering and my own report:
Codex F3, F4, F5, F7, F10 and GLM F5. (Fable F3's diagnostic gap, F8, F9,
F10, and the MLL-double-weighting half of F6 are Fable-only and are for the
other channel; they are listed at the end for the driver.)

## Dispositions

### Codex F3 (S2 claimed) — Case D's stored HMC comparisons were produced by a sampler that targeted the prior — **CONFIRMED; recommend S1 (statistical, author adjudication)**
What I checked:
- `git log --diff-filter=A -- experiments/practice_EvansEtAL/results_hmc/aggregate.json`
  gives one commit, `7026ad6` (2026-02-16, "della! hmc hierarchical"); no
  later commit touches `results_hmc/`, and `experiments/practice_EvansEtAL/run.py`
  is byte-identical to its last commit `9015ee4` of the same day.
- `run.py:45` imports `fit_hmc` from `bistar_gp.fit` and `:413-418` calls it,
  then `extract_gp_predictives`. `git show 7026ad6:bistar_gp/fit.py:149-154`
  is the target Codex describes: `model.pyro_sample_from_prior()` and
  `likelihood.pyro_sample_from_prior()` with both return values discarded,
  then `likelihood(model(x))` scored on the ORIGINAL (MAP-fitted) modules
  inside a `pyro.plate`. The `fit.py` history has no commit between the
  2026-02-13 initial commit and 2026-06-30, so no other producer existed.
- The repository's own record establishes the consequence:
  `Notes/DECISIONS.md` D6 (2026-07-02, lines 194-235) states that under this
  pattern "the obs likelihood was independent of the sampled latents and NUTS
  targeted the **prior**: every `fit_hmc` 'posterior' draw was a prior draw",
  and calls the defect "pre-existing". D6's withdrawal paragraph names only
  `bistar_gp/cache/*.npz` and `runs/mauna_loa_sub150_hmc_*`; the practice
  artifacts were never withdrawn, and D64 (2026-08-11) imported them as the
  "HMC-mode practice run".
- The historical extractor did apply the sampled values: at `7026ad6`
  `extract_gp_predictives` filtered `kernel_components.*` and `noise_covar.*`
  sites (the names the era's `nn.ModuleList` registration produced) and set
  them by name. So each stored "GP draw" is a data-conditioned predictive
  under hyperparameters drawn from the hyperprior, not from the posterior.
  Every stored subject file carries all three configurations, so the
  `except Exception: continue` around the HMC branch did not fire.
Consequence: the §6 tables built from `bistar_probs`/`bistar_G_diagnostics`
(winner counts at τ=1.778, the `raw_draw_wins` asymmetry 39.0/98.7 percent,
the cohort `mean_G` levels, the subject-25 example, the τ-grid medians) are
correctly aggregated from the files but describe a posterior computation
that never happened. That meets the S1 wording ("right only by accident" at
best). The MAP-conditional reconstruction half of Case D is unaffected: it
uses the stored `fit_map` point, which was produced by a working optimizer.
Refutation attempts that failed: no alternative producer in history; no
runtime SHA or hyperparameter draws in the JSONs to argue a corrected
sampler was used; the D6 text forecloses the "informative prior makes the
draws posterior-like" defence because the target was exactly the prior.

### Codex F4 (S2 claimed) — single-kernel site names are dropped by `select_hmc_sites` and `apply_hp_value` — **CONFIRMED (S2)**
Executed with the practice builder on current code: the single-kernel model's
sites are `likelihood.noise_covar.noise_prior`, `covar_module.outputscale_prior`,
`covar_module.base_kernel.lengthscale_prior`; `select_hmc_sites` keeps only
the noise site (`model.py:76-78` require a `covar_module.kernels.` or
`kernel_components.` prefix); `apply_hp_value` returns False for both kernel
sites (`model.py:99-104`); two draws with lengthscale 0.05/2.0 and outputscale
0.2/4.0 yield predictives with max |mean diff| 0.0 and max |cov diff| 0.0,
recorded hyperparameters containing only the noise, and the fresh kernel at
its initialization value 0.6931 for both parameters. The corrected sampler
today (`fit_hmc` → `nuts_e1`) emits exactly those `covar_module.*` names for
this model, so any regeneration of the Case D practice artifacts on current
code would silently score default-kernel predictives. Live source path
confirmed; no committed manuscript number was produced on current code
through it (the stored artifacts predate the name migration, see F3).

### Codex F5 (S2 claimed) — the implemented table row is the hyperparameter-conditional predictive, not the notation's sampled-function row — **CONFIRMED (S2), and material**
Code: `extract_gp_predictives` (`bms_star.py:323-337`) forms
N(m_η, S_η + σ²I) per hyperparameter draw and never draws f. Prose:
`00-notation.md` ("a sampled function f with observation variance defines
ψ = N(f(x), σ²_ψ I)") and §2.1 ("draw a function conditional on them, and
combine that function with observation variance to obtain one ψ").
Quantification on E7's exact path (same caches, seeds, grid, candidates;
implemented G reproduced from the captured predictives to 0.0), Linear /
Sinusoidal / Sin+Linear / Quadratic:

| Row definition | pooled τ=1 | pooled τ=0.1 | Eq.-4 τ=1 | mean G per candidate |
|---|---|---|---|---|
| implemented predictive row (the artifact) | 0.183 / 0.192 / **0.441** / 0.184 | 0.121 / 0.125 / **0.634** / 0.121 | 0.159 / 0.169 / 0.513 / 0.159 | 1.51 / 1.45 / 0.29 / 1.51 |
| notation row, expectation over f (analytic) | 0.156 / 0.176 / **0.513** / 0.156 | 0.298 / 0.288 / **0.116** / 0.298 | 0.107 / 0.127 / 0.659 / 0.107 | 3.13 / 2.85 / 0.88 / 3.13 |
| notation row, one sampled f per draw (seed 0) | 0.158 / 0.176 / **0.509** / 0.158 | 0.249 / 0.233 / **0.272** / 0.246 | 0.109 / 0.128 / 0.654 / 0.109 | 3.15 / 2.87 / 0.88 / 3.15 |

Under the notation's own definition the Case A headline moves from 0.441 to
about 0.51, the pooled τ=0.1 ordering inverts (Sin+Linear drops from 0.634
to 0.12–0.27, because the per-draw latent-variance term σ²_lat/(2σ²) is a
candidate-independent row offset that pooled aggregation does not cancel),
and the absolute G scale carrying the M-open signal roughly doubles.
Hard-win fractions are stable (0.973 versus 0.973 / 0.963). The numbers in
the manuscript are correct for the implemented row; the definition in the
frozen notation and §2.1 is not the one computed. Which definition should
govern is the author's decision (Codex's open question 1); until it is
made, this is a claim-fidelity gap at S2 that touches every soft-transfer
number in Cases A and C, not only Ḡ.

### Codex F7 (S2 claimed) — `pw_hellinger_vcal` and `pw_hellinger_mean` use twice the correct exponent — **CONFIRMED (S2 as a package defect; no manuscript number)**
Executed: N(0,1) versus N(1,1): correct H² = 1 − exp(−1/8) = 0.11750; joint
`hellinger_distance` and base `pw_hellinger` return 0.11750;
`metrics_v2.pw_hellinger_vcal` and `pw_hellinger_mean` return 0.22120, i.e.
1 − exp(−1/4) (`metrics_v2.py:70`, `:108` divide by 4σ² where the equal-variance
Bhattacharyya exponent is Δ²/(8σ²); the docstrings repeat the error).
Reachability: consumers are `fit_method_metric_comparison.METRICS` (through
`prior_sensitivity_study._sir_bms`, whose `pw_hellinger_vcal` posteriors are
computed but never persisted by E7 or Case C), `bms_star_v2/v3_comparison.py`,
and D-series records in `Notes/DECISIONS.md`; no case section, no committed
`runs/` artifact on any paper branch, and no manuscript number uses either
variant (Case D's stored `pw_hellinger` is the correct base implementation).

### Codex F10 (S3 claimed) — `soft_transfer_weighted` stabilizes the two factors separately and can underflow to a uniform fallback — **CONFIRMED (S3)**
Executed the stated probe: `G=[[1000,1001],[0,0]]`, `log_weights=[0,-1000]`,
τ=1 → `instance_scores=[0,0]`, posteriors `[0.5, 0.5]`; joint log-space
aggregation gives `[0.5938, 0.4062]`. Cause at `aggregation_v3.py:352-363`:
`w = exp(lw − max lw)` and `boltz = exp(−G/τ − max)` are formed separately
and multiplied, so their product can vanish although the joint log-weights
do not. Reachability: `run_weighted_bms_star` is called only by
`bms_star_v3_comparison.py`; no manuscript path.

### GLM F5 (S3 claimed) — `average_gp_posterior` does not validate sample means, offered as the source of the `aggregation_v3.py:77` RuntimeWarnings — **REFUTED as stated; residual hygiene only (S4)**
The causal claim fails on execution: in the prior-stage test path all 40
extracted means are exactly zero and finite, all covariances finite
(max |cov| 1787), and the averaged pattern is finite; the same three
"divide by zero / overflow / invalid value encountered in matmul" warnings
are emitted by `np.full(40, 1/40) @ np.zeros((40, 40))` and by a random finite
40×40 matmul on this numpy 1.26.4 arm64 build. They are spurious BLAS
floating-point flags, not non-finite inputs (Codex's T1 reached the same
conclusion independently). The failure scenario is also unreachable through
the package: a draw whose factorization fails is dropped before it can carry
a non-finite mean (`bms_star.py:341-342`), and the hyperparameter values are
finite draws. What survives is a hygiene point: `average_gp_posterior`
asserts nothing about `means`/`cov`, so a caller constructing
`GPPosteriorSample`s by hand could pass NaNs through. S4.

## Repo-verification notes on the driver's outstanding items

- **C1 / S1-a, S1-b (T2):** verified in `fable_review.md` F1 (committed
  `comp__*__std` reproduced to 7.1e-13; honest bands 14×, 9×, 5×; grouping
  bands 7× the other way). Adding to Codex F2's invariant: on the committed
  draws the Believer band (all components truth) is 0.919 ppm against the
  full-GP 0.132 ppm.
- **C2 (T8):** no `experiments/` or `bistar_viz/` caller passes tagged
  candidates to any bypassing entry point; the only tagged callers go through
  `run_bms_star`. Bypass demonstrated for all six entry points.
- **C3 / Codex F9 (T11):** zero firings on every paper path today: the 1e6
  sentinel cannot raise on the viz/E6 spaces (numpy predict functions,
  `pw_kl_vcal`, sigma-free spaces), all 103 E6 starts and 18 candidate fits
  converged with status 0, and p1's `converged=True`, `n_clipped=0`.
- **C4 (Kimi F4 + GLM F6):** the positional mapping in
  `decompose_model_mcmc` is consistent with its sole live caller:
  `toy_example_noMCMC.py:75-84` feeds `fit_mcmc_simple` output, whose keys are
  `named_parameters` names in the same order and whose values are RAW
  parameters, which `p.data.fill_` expects. The defect is real but latent for
  every existing caller; an HMC-style dict (constrained values, site names)
  would be mis-assigned. Recommend S3, not higher.
- **S-GLM-F4 / Fable F6:** reachability confirmed limited to the legacy
  `bistar_induced_prior*.py` scripts, which take the metric from `--metric`;
  no paper path.
- **S-Kimi-F5 / Fable F5:** two-reporter after my report; the executed
  demonstration is in `fable_review.md` F5.

## Fable-only items awaiting the other channel's check

Fable F3 (draw-concentration diagnostic absent; E7 artifact carries no win
fractions or ESS; Codex's T4 reports the same concentration numbers but
raises no finding), F8 (metric defaults: `compute_G_matrix` → `kl_forward`,
`run_bms_star` → all 17, `ExperimentConfig.metrics` omits `pw_kl_vcal`),
F9 (withdrawn-cache readers among local poster scripts; Codex T7 concurs
without a finding), F10 (no assertion gate in the van Bork script; E6 turns
an inequality violation into verdict text), and the MLL-double-weighting
half of F6 (`compute_induced_prior` weights posterior draws by their marginal
likelihood; `bistar_induced_prior.py:143-166` does exactly that).

## Net effect on the collation

Two new manuscript-facing items enter through Codex alone and survive the
check: F3 (recommended S1: Case D's stored comparisons are prior-hyperparameter
computations presented as HMC) and F5 (S2: the computed table row is not the
row the frozen notation defines, and the difference moves the Case A
headline from 0.441 to about 0.51 and inverts the pooled τ=0.1 ordering).
F4 is the regeneration-path corollary of F3. F7 and F10 are confirmed package
defects with no manuscript reach. GLM F5 is refuted as a cause and reduced to
hygiene.

---

## Corrections recorded after the Codex cross-check (Fable, 2026-09-06)

Codex (gpt-6-astra, xhigh; `codex_crosscheck.md`) checked the Fable-only
items. Its dispositions are accepted, and three statements above or in
`fable_review.md` are corrected here rather than edited in place:

1. **Codex F5 wording (this file, "Dispositions").** "The pooled τ=0.1
   ordering inverts" holds only for the exp(−E_f[G]/τ) variant, which
   averages the divergence before exponentiation and is not the notation's
   construction. Under the literal sampled-function row the pooled τ=0.1
   result is a seed-dependent four-way near-tie (Sin+Linear 0.23–0.29, first
   in 2 of 10 function-draw seeds); the τ=1 headline is 0.501–0.509. The
   corrected statement is the one in `ledger_draft.md` revision 2, Item 4.
2. **Fable F10, E6 half — withdrawn.** `HANDOFF-cases.md:79-80` specifies
   "E6 verdict stated either way (a violation is a REPORTABLE finding, not a
   failure)"; `e6_nesting_monotonicity.py` implements that contract, so the
   proposed raise on `all_hold=False` is not a fix. The van Bork half stands
   at S4 as narrowed by Codex: the script implements its own KL and
   integration and never calls `soft_transfer`, so the unprotected
   regression is in those local calculations, and its `main()` saves
   corrupted errors without failing (Codex probe: forcing the KL to zero gave
   errors of about 0.1 and 0.341 with a normal exit).
3. **Fable F9 path and reach.** The poster-directory figure exists at
   `CogSci Poster/Fig W - Sin and model selection/bms_tau_curves.png` (Codex
   searched a shorthand path), but its sha256 (3984d688…) matches neither
   `runs/toy_tau_metric_comparison/toy_tau_curves.png` (eae88153…) nor the
   `runs/toy_n20_poster/` outputs, and `toy_tau_metric_comparison.py` writes
   `toy_tau_curves.png`, so no producer link to the withdrawn cache is
   established for that file. The finding narrows to what Codex states: the
   three local readers load the withdrawn cache without a withdrawal check,
   and presented-poster use is unestablished (ledger Item 1's open question 2
   already covers it). S4.

Net: F8 S4 (narrowed), F9 S4 (narrowed), F10 S4 (van Bork half only), F6 MLL
half S3 (narrowed: reachable only when valid posterior caches are supplied;
zero `log_mlls` recovers uniform averaging), F3 S2 (formal record; ledger
Item 5 stands). No ledger item changes.
