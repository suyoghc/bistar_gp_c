# Scratchpad

Working notes: current plan, open questions, in-progress state. Clean out completed items.

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

## Still open (held deliberately)

- **Remaining review findings** — ~20 severity-2 cleanups (duplication in laplace_evidence
  closures, redundant recomputation in plot_ablation_ladder/tau sweeps, committed .pyc/.DS_Store
  artifacts, walrus-in-ternary in impact_assessment, CLAUDE.md prose nits; full list in the
  review output).
- **HMC archives invalid** — `bistar_gp/cache/*.npz` and `runs/mauna_loa_sub150_hmc_*` predate the
  D2 single-registration fix (biased target); regenerate before paper numbers. Della impact
  assessment must rerun on fixed code.

- **Viz-script unification** — port `model_priors_laplace.py` / `model_prior_trajectory_laplace.py`
  onto `laplace_log_Z_Mx`. Blocked on the single-`G` decision: they use a variance-weighted MSE,
  not a package METRIC. This is the paper's metric-choice question; do NOT force it silently.
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
