# Case D regret curves

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
trials; all contain the common trials 1 through 20 used for the regret figure.

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
and no HMC. Subject `i` uses NumPy seed `20260811 + i`.

## Estimand and band

The implemented formula equals
`regret_theta(t) = E_draws[abs(mu_GP(t) - mu_theta(t))]`. A chat-derived Q&A in
the local limits note mentions a squared difference, but the formal formula and
the Case D work order specify the absolute difference. The mean at each trial
pools 25 subjects times 100 draws within a truth cohort. The shaded band spans
the 10th and 90th percentiles of those same 2,500 subject-draw absolute errors;
it describes dispersion across subjects and posterior function draws, not a
confidence interval for the cohort mean.

For the power-generated cohort, 70.0% of the summed
20-trial discrimination gap occurs in trials 1 through 5, and the first 10
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
`pw_nll` provides the closest available role to the W1 primary, but the script
does not rename it or introduce a new metric.

Files:

- `results.json`: provenance, fidelity checks, regret curves, discrimination
  gaps, stored selection summaries, and aggregated stored G magnitudes.
- `regret_curves.png`: two truth-cohort panels with pooled dispersion bands and
  per-trial candidate discrimination gaps.
