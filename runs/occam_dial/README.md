# Case B: Occam dial and nesting monotonicity

Regenerate from the repository root:

```bash
python experiments/occam_dial_figure.py
python experiments/e6_nesting_monotonicity.py
```

Both scripts use local CPU computation only. They construct the n=50 averaged GP with `PRIOR_CONFIGS["informative"]`, `gp_method="map"`, data seed 42, 80 evaluation points over [-10, 10], and the primary `pw_kl_vcal` metric. MAP retains one GP predictive. The scripts import the shared construction from `bistar_viz/scripts/_viz_spaces.py` and the existing evidence machinery from `bistar_gp/laplace_evidence.py`.

## Figure computation

`occam_dial.png` and `figure_results.json` use τ=0.3, IS seed 0, n_is=40,000, five seeded perturbations per legacy start, and the canonical visualization parameter boxes. The optional `runs/viz_unification/delta_table.md` only supplies a cross-check when present.

The anchor tolerance equals 0.003 in absolute model probability. The published anchors were rounded to three decimals, and the remaining allowance covers small cross-platform optimizer differences. The tolerance remains well below the 0.042 p2 Linear versus Sin+Linear gap.

Fresh n=50 posteriors:

- `p1_priors_lap_occam`: Linear 0.534121, Sinusoidal 0.075747, Sin+Linear 0.382052, Quadratic 0.008080
- `p2_priors_is_occam`: Linear 0.506877, Sinusoidal 0.020499, Sin+Linear 0.464791, Quadratic 0.007834
- `p3_priors_canonical`: Linear 0.007040, Sinusoidal 0.001093, Sin+Linear 0.991758, Quadratic 0.000109

The optional D17 table cross-check was available.

The D17-recorded legacy 0.934 and 0.693 values provide historical context only. `bistar_viz/scripts/viz_unification_compare.py`, with pinned legacy commit `a87356a`, regenerates those legacy arms. Neither new script invokes that git-based extraction path.

## E6 computation

E6 uses 161 log-spaced τ values from 10^-1.5 through 10^2.5, IS seed 0, n_is=100,000, and the same five perturbations per start. One `is_log_Z_Mx` call per model computes the full raw sweep; the package's `_log_reference_volume` helper supplies the occam-normalized sweep. The visualization box uses A >= 0.01 for numerical plotting. E6 alone extends the encompassing Sin+Linear box to A >= 0 so Linear at A=0 forms an exact restriction. All other bounds match the canonical visualization boxes. The embedded restricted optima seed the encompassing multi-start optimization. IS uses interior perturbed starts plus the best encompassing optimum, which avoids flat boundary-Hessian components without changing the integral.

The min-Ḡ comparison tolerance equals 1e-8 in Ḡ units. It only classifies floating-point near-ties and remains many orders of magnitude below the observed margins. τ crossings use linear interpolation in log10(τ) inside the reported adjacent grid bracket; the bracket, rather than extra decimal places in the interpolant, provides the resolution statement.

Fresh E6 results:

- `Linear_within_Sin+Linear`: min Ḡ(restricted)=2.424774370, min Ḡ(encompassing)=0.045516783, margin=2.379257587, holds=True.
  - `occam_false`: no crossing on the grid.
  - `occam_true`: 0.295184 within [0.281838, 0.298538].
- `Sinusoidal_within_Sin+Linear`: min Ḡ(restricted)=2.546229649, min Ḡ(encompassing)=0.045516783, margin=2.500712865, holds=True.
  - `occam_false`: no crossing on the grid.
  - `occam_true`: 1.484355 within [1.412538, 1.496236].

E6 verdict: Both numerical min-Ḡ inequalities hold on the n=50 informative-config, MAP-based toy GP. E6 supports the reachable-set claim for these two exact restrictions, while the finite-τ Z_M ordering still depends on the reference-measure convention.

## Files

- `occam_dial.png`: E4 attribution-ladder figure, kept below 2 MB.
- `figure_results.json`: all freshly computed E4 arm values and anchor checks.
- `e6_results.json`: min-Ḡ optima, exact-embedding checks, both Z_M conventions, ESS diagnostics, the full τ grid, and crossing brackets.
