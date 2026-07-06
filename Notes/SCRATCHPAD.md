# Scratchpad

Working notes: current plan, open questions, in-progress state. Clean out completed items.

## Done this session (D11/D12/D13, comparison campaign)

- **Method × metric comparison (D12, corrected by D13)** —
  `experiments/fit_method_metric_comparison.py`, tables in
  `docs/fit-method-metric-comparison.md` (+ capped-NUTS appendix
  `docs/appendix-tree-depth-cap.md`, `_td7` outputs). Corrected headlines: toy posterior
  BIMODAL under `informative` priors — low-noise mode = global DENSITY max (MAP, −33.4);
  high-noise prior-scale mode holds ~3× the MASS (prior-IS 0.19/0.67). hmc/map/hmc_laplace
  report the density-mode basin and pick Sin+Linear under every metric (hard assignment
  200/200); VI migrates to the dominant-mass basin and picks Sinusoidal — thesis App. II
  "VI ≈ HMC" does not replicate; reads as PRIOR MISSPECIFICATION expressed through method
  choice. pw_kl_vcal ≡ pw_nll_gp empirically; kl_forward sharpest but brittle; pw_kl_vcal
  default results-confirmed; METHOD default is now a real user fork (density mode vs mass —
  see D12 Decision). depth-7 cap: ~9× cheaper, model posteriors shift ≤0.011. Raw draws
  cached (`runs/fit_method_metric_comparison/samples_*.npz`) — sampler hours never re-paid.
- **candidates.py restart-selection bug (D11)** — multi-start MLE selection was a no-op
  (criterion constant n/2 at any MLE); Sin+Linear had collapsed to a degenerate near-linear
  fit (same no-op + a tuple-unpack breakage in the two Mauna candidates, codex catch).
  Fixed via full-NLL comparison at all six `_fit_mle` call sites + `tests/test_candidates.py`.
  First-run outputs preserved as `results_degenerate_candidates.json`.
- **fit_mcmc_simple sampled the wrong measure (D13)** — raw-space MH without the softplus
  Jacobian; inflated small-hyperparameter mass ~3× and briefly inverted the D12 mass story
  (caught by a post-commit codex verification, upheld by independent prior-IS + exact-mode
  optimization; D12 corrected in place). Fixed via `_raw_log_jacobian` in the MH target +
  analytic regression test. **92 tests pass.**

## New open item (from D11)

- **Recheck Mauna candidate fits post-D11**: the real-data impact results (D6/D8 section of
  `docs/impact-assessment-results.md`) fitted QuadSin/Quad+2Harm with the old no-op restart
  selection (first restart always kept). Their initialization is data-driven (polyfit +
  residual amplitude) so the first restart plausibly converged fine, but the headline
  Linear-to-Quad+2Harm reversal should be re-verified against the fixed selection before paper
  numbers.

## Open questions for the user (from D12/D13)

- `metric_name="pw_kl_vcal"`: results-confirmed — ratify?
- METHOD default (genuine fork, D12 Decision): keep `hmc` (reports the density-mode basin,
  picks the true model, thesis-style) with the mass split disclosed — or first revisit the
  `informative` priors (truth-ish log joint −57 vs −33 MAP; the bimodality and the whole
  method disagreement may dissolve under better-calibrated priors)?
- VI's role in the paper: thesis-primary; here it faithfully reports the DOMINANT-mass basin
  of a misspecified-prior posterior — present as the bimodality/prior-sensitivity story?
- Then: Task 2 — the ~20 severity-2 cleanups (below).

## Done this session (on `fix/laplace-zmx`, PR #2)

- **Z_Mx / Laplace reconciliation** (DECISIONS D3) — Construction II canonical. Canonical API in
  `laplace_evidence.py` (`laplace_log_Z_Mx`, `laplace_log_evidence_ordinary`/`_induced`,
  `model_posterior(baseline|I|II)`, `_laplace_logdet`); callers migrated; figures redesigned
  (decomposition + ablation ladder); deprecated `compute_(all_)laplace_evidence`/`LaplaceResult`
  removed; module self-registers its default metric. **42 tests pass.**
- **Eval follow-ups:** `pyproject.toml`; dedup `build_toy_kernels`; `InducedPriorResult` collision
  renamed; optional RNG `seed=` on `fit_mcmc_simple`/`fit_hmc`; `numerical_hessian` boundary issue
  fixed in the new module via `_laplace_logdet` (old copy removed).

- **Code review (Fable, 8-angle) + D4 fixes** — review of the branch diff surfaced 33 findings
  (10 severe). Fixed the top cluster (DECISIONS D4): stale `kernel_components` sample-key parsing
  in `bms_star`/`debias`/`aggregation_v3`/`mechanism` (kernel posterior draws silently dropped),
  double noise latent in `fit_hmc`, eval-mode MH target + duplicate proposal dim in
  `fit_mcmc_simple`. New naming helpers `select_hmc_sites`/`apply_hp_value` in `model.py`.
  **56 tests pass** (14 new).

- **Review findings round 2 fixed (DECISIONS D5)** — occam flag now applies the −log V_ref
  reference term consistently across constructions (ablation-ladder gaps volume-free); `Z_Mx`
  computes τ analytically on H_Ḡ (clipping τ-invariant) and `n_clipped` propagates with a warning;
  `soft_transfer_weighted` global-scalar max shift. **63 tests pass** (7 new).
- **Last two severity-3 findings fixed** — `impact_assessment.compare()` diffs the union of old
  and new keys (a section erroring on one side reports as CHANGED instead of vanishing; report is
  now trustworthy for the Della rerun); `bistar_viz/scripts/bistar_sample_size_sweep.py` sys.path
  bootstrap points at the repo root after the file move (runs directly again). **65 tests pass.**
- **Multi-model review + D6 fix** — 5-model panel (Gemini 3.1 Pro / Kimi K2-thinking / GLM-5.2 via
  OpenRouter; codex/gpt-5.5; Fable adjudicating). codex alone caught that `fit_hmc` sampled the
  PRIOR not the posterior (`_hmc_pyro_model` discarded the return of `pyro_sample_from_prior()`).
  Fixed in D6: score through the returned sampled module + new connection regression test. **66
  tests pass.** Kimi's `×n` CRITICAL was a false positive (verified); `fit_mcmc_simple` Jacobian is
  a pre-existing non-blocking follow-up. Panel verdict: NO-GO pre-fix, GO after D6.
- **Prior/posterior predictive sampling (D7)** — `fit.sample_prior` (i.i.d., no NUTS) +
  `extract_gp_predictives(condition_on_data=)`: one pipeline for both prior and posterior predictive
  checks. **72 tests pass** (6 new). Adversarially reviewed: SHIP, no defects.

- **Inference + G options, thesis-anchored (D9/D10)** — `fit_gp(method=hmc|vi|map|hmc_laplace)`,
  one shared samples schema, defaults per thesis Ch.5 (full-Bayes sampling; VI was its primary
  implementation, HMC the cross-check, MAP the contrast). D10: the "single-G decision" DISSOLVED —
  viz variance-weighted MSE ≡ `pw_kl_vcal` (verified to 1e-12), so the default already matches both
  thesis (KL variant) and viz figures; **viz unification UNBLOCKED**. Writeup-ready justifications in
  `docs/inference-and-metric-options.md`. **84 tests pass** (9 new).

## Still open (held deliberately)

- **Remaining review findings** — ~20 severity-2 cleanups (duplication in laplace_evidence
  closures, redundant recomputation in plot_ablation_ladder/tau sweeps, committed .pyc/.DS_Store
  artifacts, walrus-in-ternary in impact_assessment, CLAUDE.md prose nits; full list in the
  review output).
- **HMC archives invalid** — `bistar_gp/cache/*.npz` and `runs/mauna_loa_sub150_hmc_*` predate the
  D2 single-registration fix (biased target); regenerate before paper numbers. Della impact
  assessment must rerun on fixed code.

- **Viz-script unification (UNBLOCKED by D10)** — port `model_priors_laplace.py` /
  `model_prior_trajectory_laplace.py` onto `laplace_log_Z_Mx` with `metric_name="pw_kl_vcal"`
  (proven identical to their G) and posterior draws (better estimator than their prior-IS).
- **Old-vs-new impact assessment: toy sections DONE on Della** (job 10608943, 2026-07-03) —
  `docs/impact-assessment-results.md`. Quantifies the D2 fixes: latent sites 7 down to 4, decompose
  full_std order-of-magnitude correction, mcmc_simple ~8x tighter, soft_transfer shifts.
  **`--mauna` section UNBLOCKED (D8)**: fit_hmc gained init_to_map + max_tree_depth; the
  tree cap (7) is the operative fix — head-to-head 1.04 s/it vs 4.9–8.2 s/it, identical
  posteriors. impact_assessment passes it via signature dispatch; both Mauna experiment
  scripts fixed (were MAP-fitting one model, HMC-ing a fresh default one). codex review
  FIX-FIRST findings verified + fixed (boundary-underflow init guard). **75 tests pass.**
  **`--mauna` real-data results DONE (local, 2026-07-04)** — docs/impact-assessment-results.md
  real-data section. Headline: BMS* model selection REVERSES on Mauna Loa CO2 (old picks
  Linear 0.99; new picks Quad+2Harm 0.42) — the D4+D6 fixes change the scientific conclusion.
  Mechanism: old HMC = prior (noise 1.58±1.09 ≈ GammaPrior), new = posterior (noise ≈0.001);
  latent sites 13 down to 7; decompose 0.92 down to 0.03. NEW chain NOT converged (ESS≈1, Rhat 4–81) so exact
  probs soft but DIRECTION robust (mechanistically forced by near-zero noise). Ran locally
  (Della abandoned: della-h16 ~5× slower/op + thread-thrash + jitter-retry ballooning). Noise-
  prior change remains a deliberately-untaken MODELING decision; converged full-Bayes = open fork.
- **Figure regeneration** — needs a torch runtime (the project `.venv` lacks torch; tests run
  on system `python3`). This is the paper-facing session.
- **kb/Wiki/GP-Induced Model Priors.md** — update to Construction II canonical (gitignored, local).
- **Occam default** — currently `occam=False` (faithful BI*); with-Occam intended as sensitivity.
- Minor: remove the 13 `sys.path` hacks now that `pyproject.toml` exists (`pip install -e .`);
  add a cache key covering all result-determining config.

## Cleanup backlog — 8-angle review findings (2026-07-01), annotated vs D4–D13

Reconstructed from the original review; every FIXED/OPEN status re-verified against the
tree at HEAD 6573ff0. 33 kept findings + 1 refuted. Anchored by symbol (lines have moved).
Fold the `laplace_evidence.py` efficiency items into the viz unification (D10 unblocked it) —
you'll be editing those plot functions anyway.

### OPEN — execute these

Correctness-adjacent / deferred:
- [x] laplace_evidence.py :: numerical_hessian + _laplace_logdet :: not bounds-aware; the
  [1e-8,1e12] clip CONSTANTS set the Occam term at a bound-pinned MAP (~+9.2 nats/flat dir).
  D5 surfaced n_clipped but deferred the bounds-aware refactor :: S3-PLAU
- [x] laplace_evidence.py :: plot_evidence_decomposition / plot_prior_penalty_comparison ::
  read Construction-II-only component keys (log_lik_at_map, gp_penalty) with no
  `result.construction` guard → KeyError on a construction="I"/"baseline" result :: S2

Efficiency (redundant recompute — also speeds figure regeneration):
- [x] laplace_evidence.py :: plot_tau_effect_on_evidence :: re-runs full Laplace at every τ
  though baseline is τ-independent and Construction-I rescales analytically :: S2
- [x] laplace_evidence.py :: plot_ablation_ladder :: recomputes laplace_log_evidence_ordinary
  for both "baseline" and "I" per model (identical inputs) :: S2
- [x] laplace_evidence.py :: laplace_log_evidence_induced :: recomputes ll_at via
  _log_likelihood though _laplace_log_N's detail already holds log_lik_at_map :: S2
- [x] experiments/bistar_induced_prior_v2.py :: main → plot_ablation_ladder :: re-runs
  model_posterior(construction="II") already computed earlier in the same loop :: S2
- [x] laplace_evidence.py :: numerical_hessian :: computes f0=f(x) but never uses it, and the
  diagonal (i==j) uses the 4-point cross stencil (~2d+1 redundant objective evals) :: S2

Duplication / reuse:
- [x] laplace_evidence.py :: neg_log_f/neg_log_joint closures + _log_likelihood +
  compute_G_at_params :: the `noise_param, 0.3 <= 0` guard and magic 0.3 default are
  copy-pasted across 5 sites (drift silently desyncs Z_Mx / ordinary / N(M)) :: S2
- [x] laplace_evidence.py :: _log_likelihood :: re-implements the iid Gaussian log-likelihood
  (incl. the 0.3 default) rather than reusing a shared primitive :: S2
- [x] laplace_evidence.py :: model_posterior :: hand-rolls shift-by-max softmax
  (np.exp(logk - logk.max())) — another copy of a normalization snippet :: S2
- [x] experiments/impact_assessment.py :: mauna() :: duplicates the pyro latent-site
  trace/count block verbatim from collect() :: S2
- [~] tests/test_laplace_zmx.py :: lin_space()/quad_space() :: re-implement Linear/Quadratic
  ModelParameterSpace that bistar_gp.induced_prior already builds :: S2-PLAU

Dead code / artifacts:
- [x] laplace_evidence.py :: _packers :: returns (pack, unpack) but `pack` is dead at all 3
  call sites (`_, unpack = _packers(...)`) :: S2
- [x] bistar_viz/scripts/bistar_sample_size_sweep.py :: per-n_sub loop :: dead mutation
  `spec.mle_value = ...` (nothing reads it; leftover from removed compute_all_laplace_evidences) :: S2
- [x] conftest.py :: root sys.path shim :: now redundant — pyproject.toml exists and its own
  comment says "Remove once the project ships a pyproject.toml" (ties into the 13 sys.path hacks) :: S2
- [x] experiments/practice_EvansEtAL/__pycache__/*.pyc :: 6 committed .pyc artifacts the D1
  hygiene sweep missed :: S2

Prose (CLAUDE.md writing-style rules):
- [x] README.md :: "Z_Mx is the **data-free** GP model prior" :: "X is the Y" label ban :: S2
- [x] docs/plan-zmx-laplace.md :: "...are the ingredients." :: "ingredient" metaphor ban :: S2

### OPEN — severity-1 (never addressed — FLAGGED)
- [x] **laplace_evidence.py :: module imports :: `build_toy_parameter_spaces` and
  `average_gp_posterior` imported but unused (1 occurrence each) :: S1**
- [x] **Notes/DECISIONS.md :: prose :: right-arrow (→) chars — CLAUDE.md ban; 16 occurrences and
  GROWING (D4–D13 entries added more) :: S1**

### FIXED
- [x] bms_star.py :: extract_gp_predictives :: stale 'kernel_components' filter dropped kernel draws :: S5 → D4
- [x] fit.py :: fit_hmc/_hmc_pyro_model :: noise prior registered twice → phantom prior-only latent :: S4 → D4 (+D6)
- [x] mechanism.py :: *_mechanism_config hp_patterns :: 'kernel_components.*' no longer matched :: S4 → D4
- [x] fit.py :: fit_mcmc_simple :: MH target scored in eval mode (data twice) :: S4 → D4 (D13 added Jacobian)
- [x] debias.py :: decompose_model_hmc :: same stale 'kernel_components' filter :: S4 → D4
- [x] aggregation_v3.py :: soft_transfer_weighted :: per-candidate (axis=0) max shift distorted posteriors :: S4 → D5
- [x] laplace_evidence.py :: ordinary vs model_posterior :: occam=False V_ref inconsistent across constructions :: S4 → D5
- [x] laplace_evidence.py :: _laplace_logdet/_laplace_log_integral :: n_clipped discarded :: S3 → D5 (floor magnitude still OPEN)
- [x] impact_assessment.py :: compare() :: key set only from NEW json (old-only vanished) :: S3 → severity-3 pair
- [x] bistar_viz/scripts/bistar_sample_size_sweep.py :: sys.path bootstrap :: '..' = bistar_viz/ not root :: S3 → severity-3 pair
- [x] bistar_viz/scripts/bistar_sample_size_sweep.py :: docstring :: stale 'python experiments/...' path :: S2 → severity-3 pair
- [x] impact_assessment.py :: compare() :: walrus-in-ternary counter :: S2 → fixed w/ compare() union commit

### SUPERSEDED (not actionable)
- [~] Notes/DECISIONS.md :: D3 status in a later commit than the change (same-commit rule) :: S2 —
  past-commit process observation; D4–D13 all comply going forward
- [~] Notes/SCRATCHPAD.md :: "This is the *" openers :: S1 — flagged content gone (rewritten); watch style

### REFUTED by the review's own verifier (do NOT action)
- impact_assessment.py :: _git_sha :: claimed to dup run_manager._git_hash — REFUTED (both exist)

## Branches / PRs

- **PR #1** — MERGED to `main` (hygiene, 5 correctness fixes, plan, Notes workflow).
- **PR #2** (`fix/laplace-zmx`, draft: https://github.com/suyoghc/bistar_gp_c/pull/2) — D3 core +
  full caller migration + eval follow-ups + docs. Flip to "Ready" after the viz unification and
  figure regeneration (the two held items above).
