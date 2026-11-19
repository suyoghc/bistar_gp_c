# Case B: Occam dial and nesting monotonicity

Regenerate from the repository root:

```bash
python experiments/occam_dial_figure.py
python experiments/e6_nesting_monotonicity.py
```

Both scripts use local CPU computation only. They construct the n=50 averaged GP with `PRIOR_CONFIGS["informative"]`, `gp_method="map"`, data seed 42, 80 evaluation points over [-10, 10], and the primary `pw_kl_vcal` metric. MAP retains one GP predictive. The scripts import the shared construction from `bistar_viz/scripts/_viz_spaces.py` and the existing evidence machinery from `bistar_gp/laplace_evidence.py`.

## Figure computation

`occam_dial.png` and `figure_results.json` use τ=0.3, IS seed 0, n_is=40,000, five seeded perturbations per legacy start, and the canonical visualization parameter boxes.

The 0.003 absolute-probability anchor tolerance provides a same-seed reproduction gate for three-decimal source anchors, not an accuracy claim.

At p2, ESS implies SE(log Z) of approximately 0.008, 0.017, and 0.038 nats for Linear, Sin+Linear, and Sinusoidal, respectively; the induced model-probability SE is approximately 0.005.

The script cross-checks against `runs/viz_unification/delta_table.md` when that local untracked file exists; availability is machine-dependent and recorded in `figure_results.json`.

### Fresh n=50 induced model priors

- `p1_priors_lap_occam`: Linear 0.534, Sinusoidal 0.076, Sin+Linear 0.382, Quadratic 0.008
- `p2_priors_is_occam`: Linear 0.507, Sinusoidal 0.020, Sin+Linear 0.465, Quadratic 0.008
- `p3_priors_canonical`: Linear 0.007, Sinusoidal 0.001, Sin+Linear 0.992, Quadratic 0.000

Direct p1 Laplace diagnostics: Linear n_clipped=0, converged=True; Sinusoidal n_clipped=0, converged=True; Sin+Linear n_clipped=0, converged=True; Quadratic n_clipped=0, converged=True.

The D17-recorded legacy 0.934 and 0.693 values provide historical context only. `bistar_viz/scripts/viz_unification_compare.py`, with pinned legacy commit `a87356a`, regenerates those legacy arms. Neither new script invokes that git-based extraction path.

## E6 computation

E6 uses 161 log-spaced τ values from 10^-1.5 through 10^2.5, IS seeds 0, 1, and 2, n_is=100,000 per seed, and the same five perturbations per start. One `is_log_Z_Mx` call per model per seed computes the full raw sweep; the package's `_log_reference_volume` helper supplies the occam-normalized sweep. The visualization box uses A >= 0.01 for numerical plotting. E6 alone extends the encompassing Sin+Linear box to A >= 0 so Linear at A=0 forms an exact restriction. All other bounds match the canonical visualization boxes. The embedded restricted optima seed the encompassing multi-start optimization. IS uses interior perturbed starts plus the best encompassing optimum, which avoids flat boundary-Hessian components without changing the integral.

Given the exact embeddings and mean-only divergence, the min-Ḡ inequality follows analytically from box containment. The retained check confirms that the implementation reproduces that consequence and quantifies the margins. The 1e-8 comparison tolerance only classifies floating-point near-ties. Crossing resolution is set by the larger of grid spacing and Monte Carlo error.

Fresh E6 results:

- `Linear_within_Sin+Linear`: min Ḡ(restricted)=2.425, min Ḡ(encompassing)=0.046, margin=2.379, holds=True.
  - `occam_false`: seed 0: none on the grid; seed 1: none on the grid; seed 2: none on the grid.
  - `occam_true`: seed 0: 0.295 within [0.282, 0.299]; seed 1: 0.295 within [0.282, 0.299]; seed 2: 0.296 within [0.282, 0.299].
- `Sinusoidal_within_Sin+Linear`: min Ḡ(restricted)=2.546, min Ḡ(encompassing)=0.046, margin=2.501, holds=True.
  - `occam_false`: seed 0: none on the grid; seed 1: none on the grid; seed 2: none on the grid.
  - `occam_true`: seed 0: 1.484 within [1.413, 1.496]; seed 1: 1.584 within [1.496, 1.585]; seed 2: 1.382 within [1.334, 1.413].

E6 verdict: Exact embeddings and the mean-only divergence make both min-Ḡ inequalities analytic consequences of box containment. E6 confirms that the implementation reproduces those consequences and quantifies the margins; the finite-τ Z_M crossings provide the remaining empirical content.

## REVIEW_AND_VET resolution (mirrored)

The `kb/` tree is local by design and gitignored; this committed mirror preserves the resolution for clean checkouts.

**Resolution (RESOLVED, E6):** Given exact embeddings and the mean-only `pw_kl_vcal` divergence, each min-Ḡ inequality follows analytically from box containment. E6 confirms that the implementation reproduces this consequence and quantifies restricted-minus-encompassing margins of 2.379 nats for Linear and 2.501 nats for Sinusoidal. Across 161 τ values and IS seeds 0, 1, and 2, raw Lebesgue `occam=False` yields no pairwise crossing. With `occam=True`, Linear crosses at seed 0: 0.295 within [0.282, 0.299]; seed 1: 0.295 within [0.282, 0.299]; seed 2: 0.296 within [0.282, 0.299]; the per-seed interpolant spread is [0.295, 0.296], and the seed-0 ESS-implied one-SE shift interval is [0.295, 0.296]. Its seed-0 bracket delta swing (0.354 nats) exceeds the ESS-implied SE (0.012 nats), which supports reporting τ=0.295. Sinusoidal crosses at seed 0: 1.484 within [1.413, 1.496]; seed 1: 1.584 within [1.496, 1.585]; seed 2: 1.382 within [1.334, 1.413]; the supported summary is τ ≈ 1.5, with per-seed interpolant spread [1.382, 1.584] and seed-0 ESS-implied shift roots [1.392, 1.563]. The enclosing grid-and-seed uncertainty interval is about τ 1.33 to 1.59. Crossing resolution is set by the larger of grid spacing and Monte Carlo error. The empirical content comprises the margins and finite-τ Z_M crossings.

## Files

- `occam_dial.png`: E4 attribution-ladder figure, kept below 2 MB.
- `figure_results.json`: all freshly computed E4 arm values and anchor checks.
- `e6_results.json`: min-Ḡ optima, exact-embedding checks, both Z_M conventions, three-seed ESS diagnostics, the full τ grid, and crossing uncertainty.
