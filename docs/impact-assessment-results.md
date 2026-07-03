# Impact Assessment Results — old vs new correctness fixes

Deterministic old-vs-new comparison from `experiments/impact_assessment.py`, run on
Della (`slurm-impact-*`, 2026-07-03).

- **OLD** = `9016a55` (parent of PR #1, the original pre-fix baseline)
- **NEW** = `41c5bb9` (`fix/laplace-zmx` HEAD, D7)
- **Section run:** toy/synthetic `collect()` only (`--mauna` dropped — see caveat below)

## Provenance

- **Della job 10608943** (2026-07-03, `short/cpu`, 8 cores / 8 GB / 30 min) — the successful
  toy-section run this report summarizes. Raw outputs on Della under
  `/scratch/gpfs/SUYOGHC/bistar_gp_c/`: `old.json`, `new.json`, `impact_report.txt`.
- **Della job 10584302** (2026-07-02, 8 h TIMEOUT) — the first attempt including `--mauna`
  at `SUB=150, NHMC=200, NWARM=200`. Died 14/400 warmup iterations into the real-data HMC
  with the NUTS step size collapsing 7.2e-01 → 3.3e-07 and per-iteration cost growing to
  ~72 min — the sampler-geometry evidence cited in the caveat below. Its `collect()`
  sections completed and match job 10608943.
- Environment: conda `bistar_gp` (torch 2.10.0, gpytorch 1.15.1, pyro 1.9.1), the exact
  versions the D4–D7 fixes were validated against locally.

Each section is fed identical, fixed inputs so only the code under test varies.

## What each row shows

### `hmc_latent_sites`: 7 → 4  (double prior-registration fix, D2)
The old `AdditiveGPModel` registered each kernel hyperparameter twice — once as a
`kernel_components.*` `ModuleList` site and once as a `covar_module.kernels.*` site —
so HMC saw 7 latent sites for 4 real parameters. The fix (plain list, single
registration path) leaves exactly the 4 real ones. The old names carried both
prefixes; the new names carry only `covar_module.kernels.*` + `likelihood.noise_covar`.

### `decompose_full_std`: order-of-magnitude uncertainty correction (cross-covariance fix, D2)
```
full_std  OLD: (0.19, 0.65, 1.30, 1.94, 2.55)   grows to 2.55 at the edge
          NEW: (0.18, 0.09, 0.09, 0.09, 0.19)   correct, tight
          x:   (0.0,  1.5,  3.0,  4.5,  6.0)     identical grid (the one "unchanged" row)
```
The old code summed the per-component posterior covariances, dropping the
inter-component cross terms, which inflated the predictive std and made it blow up
with `x`. The fix computes the true joint (sum-kernel) posterior covariance. The
`full_mean` shifts only ~0.02 (RNG/init differences from the model refactor — the
mean was never the defect).

### `mcmc_simple_post_std`: posterior width corrected (per-datum tempering fix, D2)
Directly comparable row (present in both trees):
```
likelihood.noise_covar.raw_noise   OLD 1.977 → NEW 0.247   (~8x tighter)
```
The old MH target used gpytorch's per-datum-averaged MLL, i.e. `posterior^(1/n)` — a
badly over-flattened target. Multiplying the MLL by `n` recovers the true summed log
joint. Every hyperparameter tightened the same way (old `raw_lengthscale` std 1.82 →
new 0.42, etc.). The kernel rows also demonstrate the D2 rename: old
`kernel_components.*` vs new `covar_module.kernels.*` appear as `— missing —` on each
side rather than silently vanishing — this is the `compare()` union-of-keys fix working.

### `bms_star_posteriors`: soft_transfer axis fix (D2)
Modest on this synthetic G-matrix: `kl_forward@tau1` moves ~0.003–0.004 per model;
pointwise metrics essentially zero. The per-draw (axis-1) max shift the old code used
does not cancel in the over-draw mean, so it reweights draws; the magnitude of the
distortion grows with the spread of `G` across draws, so real data can show more.

Summary line: **36 changed, 1 unchanged** (the single unchanged row is the decompose
x-grid — a sanity check that both trees evaluate at the same points).

## Scope / caveat

This report validates the **PR #1 / D2** correctness fixes (soft_transfer,
decomposition cross-covariance, double prior-registration, `fit_mcmc_simple`
tempering). It does **not** capture the later branch fixes:

- **D4** (sample-site consumer rename fallout), **D5** (Laplace `V_ref` / analytic-τ /
  `soft_transfer_weighted`) — not exercised by the toy sections.
- **D6** (fit_hmc was sampling the prior, not the posterior) — only manifests in the
  **real HMC path** (`--mauna`), which is currently blocked by a NUTS geometry
  problem: the Mauna Loa 3-component GP posterior is stiff (step size collapses to
  ~1e-7, tree depth saturates, ~72 min/iteration). See the sampler work in
  `Notes/DECISIONS.md`.

To capture the D6 impact on real data, the `--mauna` section must run once the NUTS
sampler is made tractable (MAP init, `max_tree_depth` cap, smaller subsample).
