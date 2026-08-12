# 6. Case D: M-open calibration through a warranted decline [DRAFT]

## Calibration before an M-open claim

A relative winner does not establish adequacy. BMS* retains the raw
divergences (G(\psi,\theta)), so it can ask whether even the closest candidate
remains far from the GP patterns. That absolute reading needs a reference
distribution under known truth. Without one, a large-looking value has no
calibrated interpretation. Formal M-open calibration therefore remains an open
problem.

The practice-law artifacts offer a bounded first step, not an M-open test. Their
data directory contains no Evans et al. observations. `run.py` instead generated
50 synthetic series with seed 42, divided equally between power and exponential
truth. Each subject's generating form appears among the two fitted candidates.
The source artifacts record between 20 and 79 observations per subject, and the
regret analysis uses their common first 20 trials. We use these data to study
distinguishability and mimicry and to establish correct-specification reference
levels for (G); we do not infer how either candidate fits the real Evans
corpus.[^case-d-empirical] Evans et al.'s broader candidate discussion motivates
the context, while every result below concerns only Power and Exponential, the
pair retained in the stored fits.[^case-d-evans]

## Two failure geometries

Two obstacles require separate diagnoses. F1 concerns scaffold
representability. A stationary RBF kernel assigns one global lengthscale, while
power and exponential curves differ through a location-dependent rate of
curvature change. The scaffold can smooth over the local feature needed for
discrimination. F2 concerns intrinsic mimicry. Across some parameter regions,
the candidate families generate nearly indistinguishable patterns, so changing
the scoring rule cannot create information absent from the data.

Navarro, Pitt, and Myung's landscaping method maps such variation in
distinguishability over retention-model parameter spaces. Their analysis shows
why a close fit at one observed data set cannot establish that the models were
distinguishable there: one candidate may mimic another over a broad region.[^case-d-navarro]
Their empirical setting concerned retention rather than practice, so the link
here concerns failure geometry, not a replication. Under that geometry, weak
separation can reflect a warranted decline rather than a failed demand for a
winner. The synthetic known-truth design sharpens the interpretation: when the
correct family appears in the roster yet remains hard to recover, F1, F2, or
both have constrained the comparison.

## What the stored comparisons declined

We prefer `results_hmc/` over the MAP-mode directory because it contains the
HMC-mode practice run requested for this case. Its aggregate baseline assigns
18 subjects to Power and 32 to Exponential under BIC, although the generator
split equals 25 and 25; 41 of 50 labels match known truth. The BMS* winner labels
at the stored median temperature, τ = 1.778, vary substantially with the legacy
pointwise metric:

| GP configuration | `pw_hellinger`, Power / Exponential | `pw_mse`, Power / Exponential | `pw_nll`, Power / Exponential |
|---|---:|---:|---:|
| practitioner | 22 / 28 | 6 / 44 | 10 / 40 |
| moderate | 32 / 18 | 7 / 43 | 12 / 38 |
| agnostic | 27 / 23 | 7 / 43 | 12 / 38 |
| all configurations agree | 39 / 50 | 49 / 50 | 48 / 50 |

These practice artifacts predate W1. They contain `pw_nll`, `pw_mse`, and
`pw_hellinger`, not the manuscript's primary `pw_kl_vcal`; no new metric was
authorized for Case D, and we do not relabel the stored quantities.
`pw_nll` comes closest to the W1 primary role because it combines mean mismatch
with pointwise variance calibration. Under `pw_nll`, known-truth accuracy equals
35 of 50 for practitioner and 37 of 50 for both moderate and agnostic. More
importantly for a decline, median winning probabilities equal only 0.522, 0.522,
and 0.518 across those configurations. Winner stability therefore coexists with
weak pairwise separation and a systematic preference for Exponential. The
much sharper `pw_mse` decisions prevent a metric-general claim that BMS*
declined. The calibrated claim applies to the `pw_nll` read and its associated
regret geometry.[^case-d-empirical]

## Absolute divergence magnitudes

Rankings discard the common level of mismatch. The stored `pw_nll`
diagnostics retain the mean (G) over 100 GP draws for each fitted candidate.
The cohort means below come directly from those stored values; the Case D
script aggregates them without recomputing (G).

| GP configuration | Power truth: (G_{\mathrm{Power}}) | Power truth: (G_{\mathrm{Exp}}) | Exponential truth: (G_{\mathrm{Power}}) | Exponential truth: (G_{\mathrm{Exp}}) |
|---|---:|---:|---:|---:|
| practitioner | 4.799 | 4.775 | 5.003 | 4.582 |
| moderate | 4.858 | 4.830 | 5.045 | 4.688 |
| agnostic | 4.834 | 4.811 | 5.045 | 4.715 |

The power-generated rows exhibit the mimicry signature: both magnitudes nearly
coincide, and the wrong exponential candidate has the slightly smaller cohort
mean. The exponential-generated rows separate more clearly and favor the known
truth. At synthetic exponential subject 25, the practitioner `pw_nll` means
equal 4.881 for Power and 4.852 for Exponential, an absolute difference of
0.029. A ranking reports only Exponential; the paired magnitudes show how
little separates the candidates for that subject.[^case-d-empirical]

The table also blocks an overstatement about M-open inadequacy. Correctly
specified candidates can produce mean (G) values from 4.582 to 4.858 in these
cohort summaries, while a wrong but mimicking candidate can occupy much of the
same scale. A future inadequacy rule must compare an observed magnitude with a
reference distribution under correct specification, conditional on metric,
configuration, sample size, and noise. These known-truth `mean_G` distributions
supply the kind of calibration material such a rule needs, but Case D does not
set a rejection threshold.

## Regret localizes the comparison

The subject JSONs omit GP curves and draws. The new reconstruction regenerates
the synthetic observations, verifies each stored candidate fit through its BIC
residual structure, rebuilds an exact GP at the stored hyperparameters, and
draws 100 seeded latent posterior functions per subject. No refitting and no
new HMC occur. For candidate θ and trial (t), the reported estimand follows the
binding absolute-difference formula

\[
\operatorname{regret}_{\theta}(t)
= \mathbb{E}_{\mathrm{draws}}
  \left[\left|\mu_{\mathrm{GP}}(t)-\mu_{\theta}(t)\right|\right].
\]

Each line pools 25 subjects and 100 draws within a truth cohort. The shaded band
spans the pooled 10th and 90th percentiles of the resulting 2,500 absolute
errors at each trial; it describes subject-and-draw dispersion, not uncertainty
in the cohort mean.

![Regret curves for the two synthetic truth cohorts](../../runs/regret_curves_mopen/regret_curves.png)

| Truth cohort | Mean Power regret | Mean Exponential regret | Peak discrimination gap | Gap in trials 1–5 | Gap in trials 1–10 |
|---|---:|---:|---:|---:|---:|
| Power | 21.383 | 20.681 | 33.782 at trial 1 | 70.0% | 82.2% |
| Exponential | 35.587 | 14.855 | 91.452 at trial 1 | 41.7% | 77.7% |

The discrimination profile concentrates toward the beginning but does not
collapse to only the first few trials. For power-generated curves, trial 1
produces regrets of 116.333 for Power and 82.551 for Exponential, so the GP
reconstruction favors the wrong family precisely where the largest gap occurs.
The later gap rapidly contracts. For exponential-generated curves, trial 1
produces regrets of 131.415 for Power and 39.963 for Exponential, and appreciable
separation continues through the first half of the grid. Regret therefore
explains both sides of the aggregate result: strong localization can support
correct recovery, as in the exponential cohort, or expose a scaffold-induced
preference for the wrong mimicking curve, as in the power cohort.[^case-d-empirical]

One provenance limitation matters. `run.py` writes one
`gp_hyperparameters` block immediately after the first successful configuration
MAP fit. With the default order, all 50 source files record the practitioner MAP
point even though `results_hmc/` subsequently uses HMC samples for its stored
BMS* diagnostics. The JSONs do not retain those HMC hyperparameter draws. The
regret curves consequently condition at the stored practitioner MAP point and
sample functions from that exact conditional GP; they should not be described
as reconstructed HMC trajectories.

## Positioning and optional extension

Averell and Heathcote showed that power-versus-exponential conclusions about
forgetting can change between individual-level and population-level analyses.
Their result warns against treating one comparison procedure or aggregation
level as a resolution of the functional-form debate.[^case-d-averell] Case D
supports a narrower conclusion. On synthetic practice curves, the legacy
`pw_nll` comparison expresses weak confidence, its raw divergence magnitudes
provide correct-specification reference levels, and regret identifies where
the scaffold helps or misleads. Nothing here adjudicates the real practice data
or the forgetting literature.

> **[E8B-PLACEHOLDER] UNBUILT OPTIONAL MODULE.** The proposed extension would
> refit in semi-log and log-log spaces, with an explicit lognormal or
> heteroskedastic noise correction, to turn curvature-rate differences into a
> global linearity comparison; a Murre and Dros real-data companion would
> remain separate from the present synthetic cohort. The driver deferred
> `e8b_transform_space.py` in this pass. The author may commission the module or
> excise this entire block; the current evidence makes no transform-space
> claim.

[^case-d-navarro]: 🟢 peer-reviewed — Navarro, D. J., Pitt, M. A., & Myung, I. J. (2004). Assessing the distinguishability of models and the informativeness of data. *Cognitive Psychology, 49*(1), 47–84. https://doi.org/10.1016/j.cogpsych.2003.11.001
[^case-d-evans]: 🟢 peer-reviewed — Evans, N. J., Brown, S. D., Mewhort, D. J. K., & Heathcote, A. (2018). Refining the law of practice. *Psychological Review, 125*(4), 592–605.
[^case-d-averell]: 🟢 peer-reviewed — Averell, L., & Heathcote, A. (2011). The form of the forgetting curve and the fate of memories. *Journal of Mathematical Psychology, 55*(1), 25–35.
[^case-d-empirical]: 🟠 empirical — `experiments/regret_curves_mopen.py`; `runs/regret_curves_mopen/results.json` and `regret_curves.png`. The script reads `experiments/practice_EvansEtAL/results_hmc/aggregate.json` and its 50 subject JSONs, asserts reconstruction fidelity, and records all reported practice-run numbers in one artifact.

---
*Provenance: `runs/regret_curves_mopen/` · `experiments/regret_curves_mopen.py` · D64.*
