# Scratchpad

Working notes: current plan, open questions, in-progress state. Clean out completed items.

## Done this session (D11/D12, comparison campaign)

- **Method × metric comparison (D12)** — `experiments/fit_method_metric_comparison.py`,
  tables in `docs/fit-method-metric-comparison.md` (+ capped-NUTS appendix
  `docs/appendix-tree-depth-cap.md`, `_td7` outputs). Headlines: toy posterior BIMODAL under
  `informative` priors (evidence: `experiments/toy_posterior_mode_analysis.py`);
  hmc/map/hmc_laplace pick Sin+Linear under every metric (hard assignment 200/200); VI
  converges stably to the prior mode and picks the WRONG model — thesis App. II "VI ≈ HMC"
  does not replicate. pw_kl_vcal ≡ pw_nll_gp empirically; kl_forward sharpest but brittle.
  D9/D10 defaults (hmc, pw_kl_vcal) results-confirmed (user to ratify). depth-7 cap:
  ~9× cheaper, model posteriors shift ≤0.011. Raw draws cached
  (`runs/fit_method_metric_comparison/samples_*.npz`) — sampler hours never re-paid.
- **candidates.py restart-selection bug (D11)** — multi-start MLE selection was a no-op
  (criterion constant n/2 at any MLE); Sin+Linear had collapsed to a degenerate near-linear
  fit (same no-op + a tuple-unpack breakage in the two Mauna candidates, codex catch).
  Fixed via full-NLL comparison at all six `_fit_mle` call sites + `tests/test_candidates.py`.
  **91 tests pass.**
  First-run outputs preserved as `results_degenerate_candidates.json`.

## New open item (from D11)

- **Recheck Mauna candidate fits post-D11**: the real-data impact results (D6/D8 section of
  `docs/impact-assessment-results.md`) fitted QuadSin/Quad+2Harm with the old no-op restart
  selection (first restart always kept). Their initialization is data-driven (polyfit +
  residual amplitude) so the first restart plausibly converged fine, but the headline
  Linear→Quad+2Harm reversal should be re-verified against the fixed selection before paper
  numbers.

## Open questions for the user (from D12)

- Ratify defaults: keep `method="hmc"`, `metric_name="pw_kl_vcal"`? (results now support both)
- VI's role in the paper: thesis-primary but mode-blind here — present as caveat or drop?
- The `informative` prior config actively fights the toy data scale (truth-ish log joint −57
  vs −33 MAP) — revisit priors, or keep as a prior-sensitivity talking point?
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
  a pre-existing non-blocking follow-up. Panel verdict: NO-GO pre-fix → GO after D6.
- **Prior/posterior predictive sampling (D7)** — `fit.sample_prior` (i.i.d., no NUTS) +
  `extract_gp_predictives(condition_on_data=)`: one pipeline for both prior and posterior predictive
  checks. **72 tests pass** (6 new). Adversarially reviewed → SHIP, no defects.

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
  `docs/impact-assessment-results.md`. Quantifies the D2 fixes: latent sites 7→4, decompose
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
  latent sites 13→7; decompose 0.92→0.03. NEW chain NOT converged (ESS≈1, Rhat 4–81) so exact
  probs soft but DIRECTION robust (mechanistically forced by near-zero noise). Ran locally
  (Della abandoned: della-h16 ~5× slower/op + thread-thrash + jitter-retry ballooning). Noise-
  prior change remains a deliberately-untaken MODELING decision; converged full-Bayes = open fork.
- **Figure regeneration** — needs a torch runtime (the project `.venv` lacks torch; tests run
  on system `python3`). This is the paper-facing session.
- **kb/Wiki/GP-Induced Model Priors.md** — update to Construction II canonical (gitignored, local).
- **Occam default** — currently `occam=False` (faithful BI*); with-Occam intended as sensitivity.
- Minor: remove the 13 `sys.path` hacks now that `pyproject.toml` exists (`pip install -e .`);
  add a cache key covering all result-determining config.

## Branches / PRs

- **PR #1** — MERGED to `main` (hygiene, 5 correctness fixes, plan, Notes workflow).
- **PR #2** (`fix/laplace-zmx`, draft: https://github.com/suyoghc/bistar_gp_c/pull/2) — D3 core +
  full caller migration + eval follow-ups + docs. Flip to "Ready" after the viz unification and
  figure regeneration (the two held items above).
