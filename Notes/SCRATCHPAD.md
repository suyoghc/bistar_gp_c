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

## Still open (held deliberately)

- **Remaining review findings** — (a) cross-construction `V_ref` inconsistency with `occam=False`
  contaminating the ablation ladder (laplace_evidence.py:340); (b) 1e-8 eigenvalue floor in
  `_laplace_logdet` can turn non-identifiability into a +9.2-nat evidence bonus, `n_clipped`
  diagnostic discarded; (c) pre-existing non-canceling max shift in
  `aggregation_v3.soft_transfer_weighted:402`; (d) ~20 severity-2 cleanups (full list in the
  review output).
- **HMC archives invalid** — `bistar_gp/cache/*.npz` and `runs/mauna_loa_sub150_hmc_*` predate the
  D2 single-registration fix (biased target); regenerate before paper numbers. Della impact
  assessment must rerun on fixed code.

- **Viz-script unification** — port `model_priors_laplace.py` / `model_prior_trajectory_laplace.py`
  onto `laplace_log_Z_Mx`. Blocked on the single-`G` decision: they use a variance-weighted MSE,
  not a package METRIC. This is the paper's metric-choice question; do NOT force it silently.
- **Figure regeneration + old-vs-new impact assessment** — needs a torch runtime (the project
  `.venv` lacks torch; tests run on system `python3`). This is the paper-facing session.
- **kb/Wiki/GP-Induced Model Priors.md** — update to Construction II canonical (gitignored, local).
- **Occam default** — currently `occam=False` (faithful BI*); with-Occam intended as sensitivity.
- Minor: remove the 13 `sys.path` hacks now that `pyproject.toml` exists (`pip install -e .`);
  add a cache key covering all result-determining config.

## Branches / PRs

- **PR #1** — MERGED to `main` (hygiene, 5 correctness fixes, plan, Notes workflow).
- **PR #2** (`fix/laplace-zmx`, draft: https://github.com/suyoghc/bistar_gp_c/pull/2) — D3 core +
  full caller migration + eval follow-ups + docs. Flip to "Ready" after the viz unification and
  figure regeneration (the two held items above).
