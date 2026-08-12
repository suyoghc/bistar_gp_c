# Case D deviation curves

Run from the repository root:

```bash
python experiments/regret_curves_mopen.py
```

The script reads the 50 subject JSONs in
`experiments/practice_EvansEtAL/results_hmc/`. Those artifacts came from
`run.py --demo`: `generate_demo_data(n_subjects=50, seed=42)` produced 25
power-generated and 25 exponential-generated curves. The practice data
directory contains no Evans et al. CSVs, so none of these results concern the
real Evans corpus. The regenerated training series range from 20 to 79
trials. The stored practice G values use 50 uniformly spaced points over each
subject's full trial span, whereas both reconstructed estimands use integer
trials 1 through 20. For a 79-trial series, the latter grid covers
24.4% of the full continuous trial span. Comparisons between the reconstructed curves
and stored aggregate G diagnostics therefore concern only their shared early
region.

## Reconstruction

Candidate predictions come from the stored `fitted_params` through the local
`candidates.py` classes. Their residual-based BIC log marginal likelihoods
match the stored values with maximum absolute error 5.684e-14,
below the asserted 1.0e-08 tolerance.

`run.py` iterates the default configurations in practitioner, moderate,
agnostic order. Immediately after each configuration's MAP fit, it writes the
single `gp_hyperparameters` block only when that block remains empty. The
stored values therefore record the first successful configuration's MAP point,
which equals practitioner for all 50 files, even under `results_hmc/`. The
subject JSONs do not retain the HMC hyperparameter draws. This script rebuilds
the practitioner RBF GP at that stored point, conditions on the complete
regenerated series with normalized-space jitter 1.0e-06, and
draws 100 latent posterior functions per subject. It performs no fitting
and no HMC. Subject `i` uses NumPy seed `20260811 + i`. The limits-note
formula averages posterior mean functions over hyperparameter draws. The stored
files cannot reconstruct that target. The solid curves instead report the
MAP-conditional posterior expected absolute deviation of the latent function,
and the dashed curves report the posterior-mean plug-in at the same MAP point.

## Estimands and bands

The MAP-conditional posterior expected absolute deviation computes
`E_{f | y, eta_hat}[abs(f(t) - mu_theta(t))]`. Its mean at each trial pools
25 subjects times 100 draws within a truth cohort. The shaded band spans the
10th and 90th percentiles of those same 2,500 subject-draw absolute deviations;
it describes dispersion, not a confidence interval for the cohort mean. The
mean-based plug-in computes
`abs(E[f(t) | y, eta_hat] - mu_theta(t))` per subject and candidate. Its JSON
band pools the 25 subject values; the figure overlays only its dashed cohort
mean. Jensen's inequality makes the draw-based deviation no smaller than the
plug-in for each subject, candidate, and trial. The latent posterior spread
therefore inflates candidate deviations and generally compresses their gap by a
trial-dependent amount. Both estimands use raw response-time units (RT units).

| Truth cohort | Estimand | Mean Power deviation (RT units) | Mean Exponential deviation (RT units) | Peak gap (RT units) |
|---|---|---:|---:|---:|
| Power | MAP-conditional posterior expected absolute deviation | 21.383 | 20.681 | 33.782 at trial 1 |
| Power | Posterior-mean plug-in | 17.638 | 17.325 | 34.052 at trial 1 |
| Exponential | MAP-conditional posterior expected absolute deviation | 35.587 | 14.855 | 91.452 at trial 1 |
| Exponential | Posterior-mean plug-in | 33.901 | 10.764 | 92.890 at trial 1 |

For the power-generated cohort, 70.0% of the summed
20-trial MAP-conditional gap occurs in trials 1 through 5, and the first 10
trials account for 82.2%. The largest gap equals
33.782 RT units at trial 1. For the exponential-generated cohort,
the corresponding shares equal 41.7% and
77.7%, and the largest gap equals
91.452 RT units at trial 1.

## Stored divergence diagnostics

`results.json` also aggregates the already stored `mean_G` values by prior
configuration, legacy metric, truth cohort, and candidate. It never recomputes
G. The practice artifacts predate the W1 metric decision and contain
`pw_nll`, `pw_mse`, and `pw_hellinger`; they contain no `pw_kl_vcal`.
The primary `pw_kl_vcal` weights squared error by GP variance. Legacy `pw_nll`
instead weights by each candidate's fitted noise variance; on that axis,
`pw_mse` more closely resembles the primary metric.

Every one of the 300 stored `mean_G` pairs satisfies
`pw_nll = 0.5*log(2*pi*sigma_theta^2) + pw_mse/(2*sigma_theta^2)`, with maximum
absolute error 1.78e-15. The candidate-specific divisor
`2*sigma_theta^2` ranges from 743.3 to
7161.5. BMS* applies `exp(-G/tau)` at a
shared temperature, so soft-transfer probability magnitudes cannot be compared
across these differently scaled metrics. No value on the stored 15-point grid
removes that scale gap: at `tau=0.1`, the power-cohort `pw_nll` medians equal
0.581, 0.569, and
0.557 across practitioner, moderate, and agnostic
(about 0.57), while the all-subject practitioner `pw_mse` median remains
0.987 at `tau=31.6`.

The tau-free `pw_nll` `raw_draw_wins` diagnostic retains the asymmetry:

| Configuration | Power truth: true-family draw wins | Power subjects with true-family majority | Exponential truth: true-family draw wins | Exponential subjects with true-family majority |
|---|---:|---:|---:|---:|
| practitioner | 39.0% | 9 / 25 | 98.7% | 25 / 25 |
| moderate | 39.9% | 8 / 25 | 94.6% | 25 / 25 |
| agnostic | 41.5% | 9 / 25 | 92.1% | 25 / 25 |

Files:

- `results.json`: provenance, fidelity checks, both deviation estimands,
  discrimination gaps, scale diagnostics, tau-free draw wins, stored selection
  summaries, and aggregated stored G magnitudes.
- `regret_curves.png`: two truth-cohort panels with pooled dispersion bands and
  dashed posterior-mean overlays plus per-trial candidate discrimination gaps.
