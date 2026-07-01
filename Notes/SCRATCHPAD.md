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

## Still open (held deliberately)

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
