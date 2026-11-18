Review the attached branch diff for the BI*/BMS*-GP paper case D (M-open
calibration / regret curves). Verdict: APPROVE or REVISE. Findings as a
numbered list:
[severity S1-S4] [file:line] claim — why it is wrong — concrete fix.
Check specifically: (1) constraint compliance [the §0 list below]; (2) numerical
claims vs the runs/ JSONs; (3) statistical correctness of the method logic;
(4) prose style rules; (5) anything the section claims that the artifacts do
not support. Do not propose scope expansions.

§0 CONSTRAINT LIST (from docs/paper-sie-jmp/HANDOFF-cases.md, verbatim):
- M2bR banner: `informative`-config HMC is WITHDRAWN. Usable numbers:
  `toy_elicited` SIR (headline 0.441), prior-IS, MAP, SIR hard-best-match
  rates, corrected NUTS ≈ 0.42. Never cite the withdrawn cache
  (`runs/fit_method_metric_comparison/samples_hmc.npz`) or
  `runs/toy_tau_metric_comparison/` (poster-only per W7).
- W1: primary metric `pw_kl_vcal`; `kl_forward` appendix-only.
- W4: `runs/viz_unification/*` numbers are `informative`-config, MAP-based,
  methods-validation role — prose must frame them so.
- No Mauna Loa material of any kind (D58 prereg boundary not to be tested).
- No changes to `bistar_gp/` package defaults or public APIs.
- Style: no arrow glyphs in prose; no "X is the Y" role-noun constructions;
  no "lives/sits" for abstracta; minimal em-dashes.
- Every reported number must be regenerable from a named `experiments/`
  script into a `runs/` artifact; each case commits a same-commit
  `Notes/DECISIONS.md` entry (next free D number).
- Commit scope per branch: `experiments/` script(s), `docs/paper-sie-jmp/`
  section, `Notes/DECISIONS.md` entry, and (deliberately, if evidence-worthy)
  the `runs/` JSON — never figures over 2 MB, never gitignored Notes files.

CASE D WORK ORDER (§2 of the HANDOFF, verbatim):
Scope: regret curves + section; E8b optional module.
1. FIRST inventory `experiments/practice_EvansEtAL/` (`run.py`, diag scripts,
   `data/`): if regret-per-trial is already computed, reuse; else add
   `experiments/regret_curves_mopen.py` implementing
   regret_θ(t) = E_draws|μ_GP(t) − μ_θ(t)| per the formula in
   `kb/Wiki/Limits Diagnostics and Open Questions.md`, on that experiment's
   existing fitted artifacts (no new HMC).
2. Section `06-case-D-mopen-calibration.md`: the decline-is-correct argument
   (Navarro, Pitt & Myung 2004 digest in
   `kb/Digests/Clippings/data_prior_regimes/`), divergence magnitudes as the
   absolute inadequacy read, regret curves showing WHERE candidates fail.
3. OPTIONAL `experiments/e8b_transform_space.py` (semi-log + log-log refit,
   lognormal noise correction) — implement behind `[E8B-PLACEHOLDER]` blocks
   in the section so the author can excise cleanly.
Acceptance: regret figure regenerates from existing artifacts; section
drafted; DECISIONS entry present.

DRIVER-VERIFIED FACTS (state of the world; do not report these as findings):
- The driver DEFERRED optional item 3 (e8b_transform_space.py is unbuilt by
  scope decision; the section carries an explicitly labeled [E8B-PLACEHOLDER]
  unbuilt-module block; recorded in D64). Deferral is not a defect.
- experiments/practice_EvansEtAL/data/ is EMPTY; all source artifacts are the
  deterministic synthetic demo cohort (generate_demo_data(50, seed=42), 25
  power-truth + 25 exponential-truth, 20-79 trials per subject). The section
  discloses this and evaluates regret on the common first 20 trials.
- practice_EvansEtAL/ is READ-ONLY for this case and was verified
  byte-untouched after implementation (tree hash unchanged; zero modified
  files).
- No regret code preexisted anywhere in practice_EvansEtAL/ (grep verified),
  so work-order item 1's "else add" branch applies.
- Implementation finding the driver accepts as fact: run.py stores ONE
  gp_hyperparameters block per subject, written after the first successful
  configuration MAP fit and before the HMC branch, so all 50 results_hmc/
  files record practitioner MAP hypers and no HMC hyperparameter draws exist
  in any artifact. The reconstruction conditions at that stored MAP point;
  the section states this limitation.
- Reconstruction fidelity was asserted mechanically: exact BIC reproduction
  across all 100 stored values (max abs err 5.684e-14 vs tolerance 1e-8);
  minimum posterior-covariance eigenvalue -2.4e-15 vs PSD tolerance 1e-8.
- The kb Wiki's formal regret line uses the ABSOLUTE difference; a
  chat-derived Q&A in the same file says "squared". The work order pins the
  Wiki formula (absolute); the README and D64 record the discrepancy note.
- kb/ is entirely gitignored (zero kb/ files ever tracked); kb paths may be
  cited for provenance of ARGUMENTS but every NUMBER must trace to runs/
  artifacts, which the section's empirical footnote asserts.
- The stored practice metrics predate W1 (pw_nll, pw_mse, pw_hellinger; no
  pw_kl_vcal). The section states this and does not relabel.
- Driver rerun from the branch tip: exit 0 in ~3.5 s; two consecutive runs
  byte-identical; the committed PNG is 159,881 bytes.
- The uncommitted working-tree Notes/DECISIONS.md carries D60-D63 above the
  committed D64; they belong to other branches and are correctly absent from
  this branch's committed diff.

=== SECTION FILE (docs/paper-sie-jmp/06-case-D-mopen-calibration.md) ===
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


=== RUN README (runs/regret_curves_mopen/README.md) ===
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


=== RUN JSON (runs/regret_curves_mopen/results.json, ABRIDGED: long numeric arrays elided with first3/last3/min/max; full file in repo) ===
{
 "discrimination_gap": {
  "exponential_truth": {
   "absolute_mean_regret_gap": {
    "__abridged__": "20 floats",
    "first3": [
     91.45226548806231,
     6.217294677623162,
     10.69216541526142
    ],
    "last3": [
     6.6982187269115325,
     6.5971093264756195,
     6.328691469171558
    ],
    "min": 6.217294677623162,
    "max": 91.45226548806231
   },
   "definition": "Absolute difference between pooled candidate mean regrets at each trial"
  },
  "power_truth": {
   "absolute_mean_regret_gap": {
    "__abridged__": "20 floats",
    "first3": [
     33.782138761936736,
     10.260790246432315,
     3.702287263473522
    ],
    "last3": [
     1.4130933527833545,
     1.5235891323442736,
     1.720119931839486
    ],
    "min": 0.19772609917623285,
    "max": 33.782138761936736
   },
   "definition": "Absolute difference between pooled candidate mean regrets at each trial"
  }
 },
 "headline_regret": {
  "exponential_truth": {
   "exponential_regret_mean_over_20_trials": 14.854941889408892,
   "first_five_fraction_of_total_gap": 0.41675465581851007,
   "first_ten_fraction_of_total_gap": 0.7773072434636453,
   "mean_gap_trials_1_to_5": 34.56091363574022,
   "mean_gap_trials_6_to_20": 16.122588903947616,
   "peak_gap": 91.45226548806231,
   "peak_trial": 1,
   "power_regret_mean_over_20_trials": 35.587111976304655
  },
  "power_truth": {
   "exponential_regret_mean_over_20_trials": 20.68093643079586,
   "first_five_fraction_of_total_gap": 0.6998945245662028,
   "first_ten_fraction_of_total_gap": 0.8218809329867263,
   "mean_gap_trials_1_to_5": 11.959756926877747,
   "mean_gap_trials_6_to_20": 1.7093949695910198,
   "peak_gap": 33.782138761936736,
   "peak_trial": 1,
   "power_regret_mean_over_20_trials": 21.382523020596416
  }
 },
 "provenance": {
  "band_definition": "At each trial, q10 and q90 pool the 25 subjects by 100 posterior function draws within a truth cohort and describe dispersion rather than confidence limits for the mean.",
  "cohort_sizes": {
   "exponential_truth": 25,
   "power_truth": 25
  },
  "conditioning_jitter_normalized_variance": 1e-06,
  "data_seed": 42,
  "evaluation_trial_grid": {
   "__abridged__": "20 floats",
   "first3": [
    1.0,
    2.0,
    3.0
   ],
   "last3": [
    18.0,
    19.0,
    20.0
   ],
   "min": 1.0,
   "max": 20.0
  },
  "formula": "regret_theta(t) = E_draws[abs(mu_GP(t) - mu_theta(t))]",
  "formula_discrepancy_note": "The formal limits-note equation and Case D work order use absolute difference. A chat-derived Q&A in the same note says squared difference; this artifact follows the binding absolute formula.",
  "gp_hyperparameters_provenance": "run.py stores gp_hyperparameters once, immediately after the first successful configuration MAP fit. The default loop order starts with practitioner, so all 50 source files carry practitioner MAP values even though results_hmc subsequently runs HMC for GP samples.",
  "gp_reconstruction": "Exact zero-mean RBF GP conditioning at stored lengthscale, outputscale, and noise; no refit and no hyperparameter sampling; latent posterior function draws exclude fresh observation noise.",
  "legacy_metric_note": "Stored diagnostics contain pw_nll, pw_mse, and pw_hellinger. They predate W1 and contain no pw_kl_vcal. pw_nll receives closest-role framing without relabeling or recomputation.",
  "n_draws_per_subject": 100,
  "n_subjects": 50,
  "posterior_function_draw_seed_base": 20260811,
  "posterior_function_draw_seed_rule": "seed = 20260811 + subject_id",
  "real_evans_files_present": false,
  "regret_units": "raw response-time units from the synthetic generator",
  "source_aggregate": "experiments/practice_EvansEtAL/results_hmc/aggregate.json",
  "source_artifact_dir": "experiments/practice_EvansEtAL/results_hmc",
  "source_artifact_mode": "HMC run, with one stored practitioner MAP hyperparameter point per subject",
  "stored_n_gp_samples_per_subject": 100,
  "summary_definition": "Summary fields use the arithmetic mean, sample standard deviation with ddof=1, and NumPy linear-interpolation quantiles.",
  "synthetic_data_call": "generate_demo_data(n_subjects=50, seed=42)",
  "synthetic_data_generator": "experiments/practice_EvansEtAL/run.py::generate_demo_data",
  "training_trial_counts": {
   "max": 79,
   "min": 20,
   "unique": {
    "__abridged__": "32 floats",
    "first3": [
     20,
     21,
     22
    ],
    "last3": [
     73,
     75,
     79
    ],
    "min": 20,
    "max": 79
   }
  }
 },
 "reconstruction_fidelity": {
  "bic_log_ml": {
   "absolute_tolerance": 1e-08,
   "all_passed": true,
   "check": "Stored fitted-parameter residual structure evaluated on regenerated full subject series",
   "max_abs_error": 5.684341886080802e-14,
   "mean_abs_error": 5.115907697472721e-15,
   "n_values_checked": 100
  },
  "per_subject": [
   {
    "candidate_bic": {
     "Exponential": {
      "absolute_error": 0.0,
      "reconstructed": -110.84529683021204,
      "stored": -110.84529683021204
     },
     "Power": {
      "absolute_error": 0.0,
      "reconstructed": -110.74425566162934,
      "stored": -110.74425566162934
     }
    },
    "dataset_id": "synth_exponential",
    "n_trials": 20,
    "source_file": "synth_exponential_sub25_default.json",
    "subject_id": 25
   },
   {
    "candidate_bic": {
     "Exponential": {
      "absolute_error": 0.0,
      "reconstructed": -274.58197585739345,
      "stored": -274.58197585739345
     },
     "Power": {
      "absolute_error": 5.684341886080802e-14,
      "reconstructed": -284.20181831653474,
      "stored": -284.2018183165347
     }
    },
    "dataset_id": "synth_exponential",
    "n_trials": 55,
    "source_file": "synth_exponential_sub26_default.json",
    "subject_id": 26
   },
   {
    "candidate_bic": {
     "Exponential": {
      "absolute_error": 0.0,
      "reconstructed": -226.6175462905604,
      "stored": -226.6175462905604
     },
     "Power": {
      "absolute_error": 0.0,
      "reconstructed": -231.40820928074595,
      "stored": -231.40820928074595
     }
    },
    "dataset_id": "synth_exponential",
    "n_trials": 43,
    "source_file": "synth_exponential_sub27_default.json",
    "subject_id": 27
   },
   {
    "candidate_bic": {
     "Exponential": {
      "absolute_error": 0.0,
      "reconstructed": -110.66589606255963,
      "stored": -110.66589606255963
     },
     "Power": {
      "absolute_error": 0.0,
      "reconstructed": -114.34588307481062,
      "stored": -114.34588307481062
     }
    },
    "dataset_id": "synth_exponential",
    "n_trials": 22,
    "source_file": "synth_exponential_sub28_default.json",
    "subject_id": 28
   },
   {
    "candidate_bic": {
     "Exponential": {
      "absolute_error": 0.0,
      "reconstructed": -161.29309569301924,
      "stored": -161.29309569301924
     },
     "Power": {
      "absolute_error": 0.0,
      "reconstructed": -172.12042862296127,
      "stored": -172.12042862296127
     }
    },
    "dataset_id": "synth_exponential",
    "n_trials": 30,
    "source_file": "synth_exponential_sub29_default.json",
    "subject_id": 29
   },
   {
    "candidate_bic": {
     "Exponential": {
      "absolute_error": 0.0,
      "reconstructed": -228.28023279216146,
      "stored": -228.28023279216146
     },
     "Power": {
      "absolute_error": 0.0,
      "reconstructed": -235.5666580953088,
      "stored": -235.5666580953088
     }
    },
    "dataset_id": "synth_exponential",
    "n_trials": 50,
    "source_file": "synth_exponential_sub30_default.json",
    "subject_id": 30
   },
   {
    "candidate_bic": {
     "Exponential": {
      "absolute_error": 0.0,
      "reconstructed": -113.11646353264054,
      "stored": -113.11646353264054
     },
     "Power": {
      "absolute_error": 0.0,
      "reconstructed": -127.13599267479279,
      "stored": -127.13599267479279
     }
    },
    "dataset_id": "synth_exponential",
    "n_trials": 23,
    "source_file": "synth_exponential_sub31_default.json",
    "subject_id": 31
   },
   {
    "candidate_bic": {
     "Exponential": {
      "absolute_error": 0.0,
      "reconstructed": -290.576272720626,
      "stored": -290.576272720626
     },
     "Power": {
      "absolute_error": 5.684341886080802e-14,
      "reconstructed": -304.824121908406,
      "stored": -304.8241219084061
     }
    },
    "dataset_id": "synth_exponential",
    "n_trials": 59,
    "source_file": "synth_exponential_sub32_default.json",
    "subject_id": 32
   },
   {
    "candidate_bic": {
     "Exponential": {
      "absolute_error": 0.0,
      "reconstructed": -186.35381294494843,
      "stored": -186.35381294494843
     },
     "Power": {
      "absolute_error": 2.842170943040401e-14,
      "reconstructed": -195.33010649979772,
      "stored": -195.33010649979775
     }
    },
    "dataset_id": "synth_exponential",
    "n_trials": 36,
    "source_file": "synth_exponential_sub33_default.json",
    "subject_id": 33
   },
   {
    "candidate_bic": {
     "Exponential": {
      "absolute_error": 0.0,
      "reconstructed": -316.94258158048194,
      "stored": -316.94258158048194
     },
     "Power": {
      "absolute_error": 0.0,
      "reconstructed": -323.6724557265599,
      "stored": -323.6724557265599
     }
    },
    "dataset_id": "synth_exponential",
    "n_trials": 60,
    "source_file": "synth_exponential_sub34_default.json",
    "subject_id": 34
   },
   {
    "candidate_bic": {
     "Exponential": {
      "absolute_error": 0.0,
      "reconstructed": -347.4670070429631,
      "stored": -347.4670070429631
     },
     "Power": {
      "absolute_error": 0.0,
      "reconstructed": -353.6865336951781,
      "stored": -353.6865336951781
     }
    },
    "dataset_id": "synth_exponential",
    "n_trials": 64,
    "source_file": "synth_exponential_sub35_default.json",
    "subject_id": 35
   },
   {
    "candidate_bic": {
     "Exponential": {
      "absolute_error": 0.0,
      "reconstructed": -341.2940888524852,
      "stored": -341.2940888524852
     },
     "Power": {
      "absolute_error": 0.0,
      "reconstructed": -359.57672638721965,
      "stored": -359.57672638721965
     }
    },
    "dataset_id": "synth_exponential",
    "n_trials": 64,
    "source_file": "synth_exponential_sub36_default.json",
    "subject_id": 36
   },
   {
    "candidate_bic": {
     "Exponential": {
      "absolute_error": 0.0,
      "reconstructed": -357.01117935321304,
      "stored": -357.01117935321304
     },
     "Power": {
      "absolute_error": 0.0,
      "reconstructed": -380.4196820844261,
      "stored": -380.4196820844261
     }
    },
    "dataset_id": "synth_exponential",
    "n_trials": 71,
    "source_file": "synth_exponential_sub37_default.json",
    "subject_id": 37
   },
   {
    "candidate_bic": {
     "Exponential": {
      "absolute_error": 0.0,
      "reconstructed": -343.02432462207855,
      "stored": -343.02432462207855
     },
     "Power": {
      "absolute_error": 0.0,
      "reconstructed": -356.86299342107725,
      "stored": -356.86299342107725
     }
    },
    "dataset_id": "synth_exponential",
    "n_trials": 72,
    "source_file": "synth_exponential_sub38_default.json",
    "subject_id": 38
   },
   {
    "candidate_bic": {
     "Exponential": {
      "absolute_error": 1.4210854715202004e-14,
      "reconstructed": -113.40111155876991,
      "stored": -113.4011115587699
     },
     "Power": {
      "absolute_error": 0.0,
      "reconstructed": -115.48387452622796,
      "stored": -115.48387452622796
     }
    },
    "dataset_id": "synth_exponential",
    "n_trials": 20,
    "source_file": "synth_exponential_sub39_default.json",
    "subject_id": 39
   },
   {
    "candidate_bic": {
     "Exponential": {
      "absolute_error": 0.0,
      "reconstructed": -131.42007610659098,
      "stored": -131.42007610659098
     },
     "Power": {
      "absolute_error": 0.0,
      "reconstructed": -143.66622896919802,
      "stored": -143.66622896919802
     }
    },
    "dataset_id": "synth_exponential",
    "n_trials": 25,
    "source_file": "synth_exponential_sub40_default.json",
    "subject_id": 40
   },
   {
    "candidate_bic": {
     "Exponential": {
      "absolute_error": 0.0,
      "reconstructed": -247.73481706678226,
      "stored": -247.73481706678226
     },
     "Power": {
      "absolute_error": 0.0,
      "reconstructed": -253.12288315922703,
      "stored": -253.12288315922703
     }
    },
    "dataset_id": "synth_exponential",
    "n_trials": 51,
    "source_file": "synth_exponential_sub41_default.json",
    "subject_id": 41
   },
   {
    "candidate_bic": {
     "Exponential": {
      "absolute_error": 0.0,
      "reconstructed": -226.3679688124487,
      "stored": -226.3679688124487
     },
     "Power": {
      "absolute_error": 0.0,
      "reconstructed": -231.5645463079967,
      "stored": -231.5645463079967
     }
    },
    "dataset_id": "synth_exponential",
    "n_trials": 43,
    "source_file": "synth_exponential_sub42_default.json",
    "subject_id": 42
   },
   {
    "candidate_bic": {
     "Exponential": {
      "absolute_error": 0.0,
      "reconstructed": -323.6001678367978,
      "stored": -323.6001678367978
     },
     "Power": {
      "absolute_error": 0.0,
      "reconstructed": -348.9621043762841,
      "stored": -348.9621043762841
     }
    },
    "dataset_id": "synth_exponential",
    "n_trials": 64,
    "source_file": "synth_exponential_sub43_default.json",
    "subject_id": 43
   },
   {
    "candidate_bic": {
     "Exponential": {
      "absolute_error": 0.0,
      "reconstructed": -329.3818458087355,
      "stored": -329.3818458087355
     },
     "Power": {
      "absolute_error": 5.684341886080802e-14,
      "reconstructed": -336.9951410717332,
      "stored": -336.99514107173314
     }
    },
    "dataset_id": "synth_exponential",
    "n_trials": 66,
    "source_file": "synth_exponential_sub44_default.json",
    "subject_id": 44
   },
   {
    "candidate_bic": {
     "Exponential": {
      "absolute_error": 0.0,
      "reconstructed": -260.5705312967822,
      "stored": -260.5705312967822
     },
     "Power": {
      "absolute_error": 0.0,
      "reconstructed": -288.1802594209234,
      "stored": -288.1802594209234
     }
    },
    "dataset_id": "synth_exponential",
    "n_trials": 53,
    "source_file": "synth_exponential_sub45_default.json",
    "subject_id": 45
   },
   {
    "candidate_bic": {
     "Exponential": {
      "absolute_error": 0.0,
      "reconstructed": -123.65451869199474,
      "stored": -123.65451869199474
     },
     "Power": {
      "absolute_error": 0.0,
      "reconstructed": -126.19356370892456,
      "stored": -126.19356370892456
     }
    },
    "dataset_id": "synth_exponential",
    "n_trials": 24,
    "source_file": "synth_exponential_sub46_default.json",
    "subject_id": 46
   },
   {
    "candidate_bic": {
     "Exponential": {
      "absolute_error": 0.0,
      "reconstructed": -308.34552113777437,
      "stored": -308.34552113777437
     },
     "Power": {
      "absolute_error": 0.0,
      "reconstructed": -315.46625569132004,
      "stored": -315.46625569132004
     }
    },
    "dataset_id": "synth_exponential",
    "n_trials": 59,
    "source_file": "synth_exponential_sub47_default.json",
    "subject_id": 47
   },
   {
    "candidate_bic": {
     "Exponential": {
      "absolute_error": 0.0,
      "reconstructed": -184.32332906789824,
      "stored": -184.32332906789824
     },
     "Power": {
      "absolute_error": 0.0,
      "reconstructed": -191.9943018157992,
      "stored": -191.9943018157992
     }
    },
    "dataset_id": "synth_exponential",
    "n_trials": 38,
    "source_file": "synth_exponential_sub48_default.json",
    "subject_id": 48
   },
   {
    "candidate_bic": {
     "Exponential": {
      "absolute_error": 0.0,
      "reconstructed": -348.2332730232307,
      "stored": -348.2332730232307
     },
     "Power": {
      "absolute_error": 0.0,
      "reconstructed": -382.5742811239412,
      "stored": -382.5742811239412
     }
    },
    "dataset_id": "synth_exponential",
    "n_trials": 73,
    "source_file": "synth_exponential_sub49_default.json",
    "subject_id": 49
   },
   {
    "candidate_bic": {
     "Exponential": {
      "absolute_error": 0.0,
      "reconstructed": -322.85512496283945,
      "stored": -322.85512496283945
     },
     "Power": {
      "absolute_error": 0.0,
      "reconstructed": -320.7574231473676,
      "stored": -320.7574231473676
     }
    },
    "dataset_id": "synth_power",
    "n_trials": 58,
    "source_file": "synth_power_sub0_default.json",
    "subject_id": 0
   },
   {
    "candidate_bic": {
     "Exponential": {
      "absolute_error": 0.0,
      "reconstructed": -114.84616712753757,
      "stored": -114.84616712753757
     },
     "Power": {
      "absolute_error": 0.0,
      "reconstructed": -110.95194535132971,
      "stored": -110.95194535132971
     }
    },
    "dataset_id": "synth_power",
    "n_trials": 21,
    "source_file": "synth_power_sub10_default.json",
    "subject_id": 10
   },
   {
    "candidate_bic": {
     "Exponential": {
      "absolute_error": 0.0,
      "reconstructed": -390.17959977047786,
      "stored": -390.17959977047786
     },
     "Power": {
      "absolute_error": 0.0,
      "reconstructed": -389.18041168718025,
      "stored": -389.18041168718025
     }
    },
    "dataset_id": "synth_power",
    "n_trials": 75,
    "source_file": "synth_power_sub11_default.json",
    "subject_id": 11
   },
   {
    "candidate_bic": {
     "Exponential": {
      "absolute_error": 0.0,
      "reconstructed": -281.72492205082665,
      "stored": -281.72492205082665
     },
     "Power": {
      "absolute_error": 0.0,
      "reconstructed": -281.4310447184752,
      "stored": -281.4310447184752
     }
    },
    "dataset_id": "synth_power",
    "n_trials": 54,
    "source_file": "synth_power_sub12_default.json",
    "subject_id": 12
   },
   {
    "candidate_bic": {
     "Exponential": {
      "absolute_error": 0.0,
      "reconstructed": -408.79058648921557,
      "stored": -408.79058648921557
     },
     "Power": {
      "absolute_error": 0.0,
      "reconstructed": -403.0483524937024,
      "stored": -403.0483524937024
     }
    },
    "dataset_id": "synth_power",
    "n_trials": 79,
    "source_file": "synth_power_sub13_default.json",
    "subject_id": 13
   },
   {
    "candidate_bic": {
     "Exponential": {
      "absolute_error": 0.0,
      "reconstructed": -105.84894488743257,
      "stored": -105.84894488743257
     },
     "Power": {
      "absolute_error": 0.0,
      "reconstructed": -106.23234732655102,
      "stored": -106.23234732655102
     }
    },
    "dataset_id": "synth_power",
    "n_trials": 20,
    "source_file": "synth_power_sub14_default.json",
    "subject_id": 14
   },
   {
    "candidate_bic": {
     "Exponential": {
      "absolute_error": 0.0,
      "reconstructed": -342.5201220710769,
      "stored": -342.5201220710769
     },
     "Power": {
      "absolute_error": 0.0,
      "reconstructed": -341.18154807422,
      "stored": -341.18154807422
     }
    },
    "dataset_id": "synth_power",
    "n_trials": 66,
    "source_file": "synth_power_sub15_default.json",
    "subject_id": 15
   },
   {
    "candidate_bic": {
     "Exponential": {
      "absolute_error": 0.0,
      "reconstructed": -273.80619381942626,
      "stored": -273.80619381942626
     },
     "Power": {
      "absolute_error": 0.0,
      "reconstructed": -262.35656021540547,
      "stored": -262.35656021540547
     }
    },
    "dataset_id": "synth_power",
    "n_trials": 51,
    "source_file": "synth_power_sub16_default.json",
    "subject_id": 16
   },
   {
    "candidate_bic": {
     "Exponential": {
      "absolute_error": 0.0,
      "reconstructed": -309.0819169068302,
      "stored": -309.0819169068302
     },
     "Power": {
      "absolute_error": 0.0,
      "reconstructed": -301.44595610380355,
      "stored": -301.44595610380355
     }
    },
    "dataset_id": "synth_power",
    "n_trials": 57,
    "source_file": "synth_power_sub17_default.json",
    "subject_id": 17
   },
   {
    "candidate_bic": {
     "Exponential": {
      "absolute_error": 0.0,
      "reconstructed": -362.1531605477585,
      "stored": -362.1531605477585
     },
     "Power": {
      "absolute_error": 0.0,
      "reconstructed": -349.44619463389955,
      "stored": -349.44619463389955
     }
    },
    "dataset_id": "synth_power",
    "n_trials": 69,
    "source_file": "synth_power_sub18_default.json",
    "subject_id": 18
   },
   {
    "candidate_bic": {
     "Exponential": {
      "absolute_error": 0.0,
      "reconstructed": -246.85256578812206,
      "stored": -246.85256578812206
     },
     "Power": {
      "absolute_error": 0.0,
      "reconstructed": -243.26741138024306,
      "stored": -243.26741138024306
     }
    },
    "dataset_id": "synth_power",
    "n_trials": 51,
    "source_file": "synth_power_sub19_default.json",
    "subject_id": 19
   },
   {
    "candidate_bic": {
     "Exponential": {
      "absolute_error": 0.0,
      "reconstructed": -141.6434242010887,
      "stored": -141.6434242010887
     },
     "Power": {
      "absolute_error": 0.0,
      "reconstructed": -141.789272403013,
      "stored": -141.789272403013
     }
    },
    "dataset_id": "synth_power",
    "n_trials": 27,
    "source_file": "synth_power_sub1_default.json",
    "subject_id": 1
   },
   {
    "candidate_bic": {
     "Exponential": {
      "absolute_error": 0.0,
      "reconstructed": -292.91409681513,
      "stored": -292.91409681513
     },
     "Power": {
      "absolute_error": 5.684341886080802e-14,
      "reconstructed": -297.48414256698766,
      "stored": -297.4841425669876
     }
    },
    "dataset_id": "synth_power",
    "n_trials": 65,
    "source_file": "synth_power_sub20_default.json",
    "subject_id": 20
   },
   {
    "candidate_bic": {
     "Exponential": {
      "absolute_error": 1.4210854715202004e-14,
      "reconstructed": -115.23005821131328,
      "stored": -115.23005821131329
     },
     "Power": {
      "absolute_error": 0.0,
      "reconstructed": -115.43013272501831,
      "stored": -115.43013272501831
     }
    },
    "dataset_id": "synth_power",
    "n_trials": 21,
    "source_file": "synth_power_sub21_default.json",
    "subject_id": 21
   },
   {
    "candidate_bic": {
     "Exponential": {
      "absolute_error": 0.0,
      "reconstructed": -116.40146449241428,
      "stored": -116.40146449241428
     },
     "Power": {
      "absolute_error": 0.0,
      "reconstructed": -118.71735675326272,
      "stored": -118.71735675326272
     }
    },
    "dataset_id": "synth_power",
    "n_trials": 22,
    "source_file": "synth_power_sub22_default.json",
    "subject_id": 22
   },
   {
    "candidate_bic": {
     "Exponential": {
      "absolute_error": 0.0,
      "reconstructed": -312.5545337441055,
      "stored": -312.5545337441055
     },
     "Power": {
      "absolute_error": 0.0,
      "reconstructed": -300.7048271361792,
      "stored": -300.7048271361792
     }
    },
    "dataset_id": "synth_power",
    "n_trials": 58,
    "source_file": "synth_power_sub23_default.json",
    "subject_id": 23
   },
   {
    "candidate_bic": {
     "Exponential": {
      "absolute_error": 0.0,
      "reconstructed": -192.8557217157185,
      "stored": -192.8557217157185
     },
     "Power": {
      "absolute_error": 0.0,
      "reconstructed": -193.80135827343764,
      "stored": -193.80135827343764
     }
    },
    "dataset_id": "synth_power",
    "n_trials": 40,
    "source_file": "synth_power_sub24_default.json",
    "subject_id": 24
   },
   {
    "candidate_bic": {
     "Exponential": {
      "absolute_error": 0.0,
      "reconstructed": -306.94683482108957,
      "stored": -306.94683482108957
     },
     "Power": {
      "absolute_error": 0.0,
      "reconstructed": -310.14954251863054,
      "stored": -310.14954251863054
     }
    },
    "dataset_id": "synth_power",
    "n_trials": 62,
    "source_file": "synth_power_sub2_default.json",
    "subject_id": 2
   },
   {
    "candidate_bic": {
     "Exponential": {
      "absolute_error": 0.0,
      "reconstructed": -278.8510173954565,
      "stored": -278.8510173954565
     },
     "Power": {
      "absolute_error": 0.0,
      "reconstructed": -278.2009260732222,
      "stored": -278.2009260732222
     }
    },
    "dataset_id": "synth_power",
    "n_trials": 59,
    "source_file": "synth_power_sub3_default.json",
    "subject_id": 3
   },
   {
    "candidate_bic": {
     "Exponential": {
      "absolute_error": 5.684341886080802e-14,
      "reconstructed": -303.07530599785144,
      "stored": -303.0753059978515
     },
     "Power": {
      "absolute_error": 5.684341886080802e-14,
      "reconstructed": -302.65769104026367,
      "stored": -302.6576910402637
     }
    },
    "dataset_id": "synth_power",
    "n_trials": 59,
    "source_file": "synth_power_sub4_default.json",
    "subject_id": 4
   },
   {
    "candidate_bic": {
     "Exponential": {
      "absolute_error": 0.0,
      "reconstructed": -383.7405348794719,
      "stored": -383.7405348794719
     },
     "Power": {
      "absolute_error": 0.0,
      "reconstructed": -383.2439338626874,
      "stored": -383.2439338626874
     }
    },
    "dataset_id": "synth_power",
    "n_trials": 73,
    "source_file": "synth_power_sub5_default.json",
    "subject_id": 5
   },
   {
    "candidate_bic": {
     "Exponential": {
      "absolute_error": 0.0,
      "reconstructed": -229.85469280038012,
      "stored": -229.85469280038012
     },
     "Power": {
      "absolute_error": 0.0,
      "reconstructed": -225.06408453455268,
      "stored": -225.06408453455268
     }
    },
    "dataset_id": "synth_power",
    "n_trials": 45,
    "source_file": "synth_power_sub6_default.json",
    "subject_id": 6
   },
   {
    "candidate_bic": {
     "Exponential": {
      "absolute_error": 5.684341886080802e-14,
      "reconstructed": -356.9839612044614,
      "stored": -356.9839612044615
     },
     "Power": {
      "absolute_error": 0.0,
      "reconstructed": -344.10949783791176,
      "stored": -344.10949783791176
     }
    },
    "dataset_id": "synth_power",
    "n_trials": 73,
    "source_file": "synth_power_sub7_default.json",
    "subject_id": 7
   },
   {
    "candidate_bic": {
     "Exponential": {
      "absolute_error": 0.0,
      "reconstructed": -357.84319518433017,
      "stored": -357.84319518433017
     },
     "Power": {
      "absolute_error": 5.684341886080802e-14,
      "reconstructed": -359.32367379800394,
      "stored": -359.3236737980039
     }
    },
    "dataset_id": "synth_power",
    "n_trials": 71,
    "source_file": "synth_power_sub8_default.json",
    "subject_id": 8
   },
   {
    "candidate_bic": {
     "Exponential": {
      "absolute_error": 0.0,
      "reconstructed": -214.83465558689832,
      "stored": -214.83465558689832
     },
     "Power": {
      "absolute_error": 0.0,
      "reconstructed": -204.2716035350138,
      "stored": -204.2716035350138
     }
    },
    "dataset_id": "synth_power",
    "n_trials": 43,
    "source_file": "synth_power_sub9_default.json",
    "subject_id": 9
   }
  ],
  "posterior_covariance": {
   "all_passed": true,
   "minimum_eigenvalue_across_subjects": -2.4004932222200888e-15,
   "negative_eigenvalue_absolute_tolerance": 1e-08
  }
 },
 "regret_band": {
  "aggregation": "Pooled across subjects and posterior function draws within each truth cohort",
  "lower_quantile": 0.1,
  "upper_quantile": 0.9
 },
 "regret_curves": {
  "exponential_truth": {
   "Exponential": {
    "band_q10": {
     "__abridged__": "20 floats",
     "first3": [
      11.288214751967974,
      4.396261801712922,
      2.3900764346101484
     ],
     "last3": [
      1.6095383976664608,
      1.746769439511786,
      1.834084855320623
     ],
     "min": 1.538507268326572,
     "max": 11.288214751967974
    },
    "band_q90": {
     "__abridged__": "20 floats",
     "first3": [
      69.51631614358236,
      45.88896241158469,
      30.272441901398494
     ],
     "last3": [
      24.77910579417608,
      25.807652124303647,
      25.89586646244694
     ],
     "min": 23.14989028781049,
     "max": 69.51631614358236
    },
    "mean": {
     "__abridged__": "20 floats",
     "first3": [
      39.96296194466747,
      23.330847840986245,
      15.076566935626557
     ],
     "last3": [
      11.502822951939804,
      12.149311591202997,
      12.393108452381844
     ],
     "min": 10.877891862819657,
     "max": 39.96296194466747
    },
    "n_draws_per_subject": 100,
    "n_subject_draw_atoms_per_trial": 2500,
    "n_subjects": 25
   },
   "Power": {
    "band_q10": {
     "__abridged__": "20 floats",
     "first3": [
      63.1866949387295,
      4.048060579904677,
      4.219033985370305
     ],
     "last3": [
      2.474940813369744,
      2.874412241093728,
      3.151298915236123
     ],
     "min": 2.474940813369744,
     "max": 63.1866949387295
    },
    "band_q90": {
     "__abridged__": "20 floats",
     "first3": [
      203.06932094528037,
      60.196903199610865,
      50.021120116811026
     ],
     "last3": [
      37.29835459704254,
      39.42512863354807,
      39.16367860146126
     ],
     "min": 36.01818809190832,
     "max": 203.06932094528037
    },
    "mean": {
     "__abridged__": "20 floats",
     "first3": [
      131.41522743272978,
      29.548142518609406,
      25.768732350887976
     ],
     "last3": [
      18.201041678851336,
      18.746420917678616,
      18.7217999215534
     ],
     "min": 17.682105494600187,
     "max": 131.41522743272978
    },
    "n_draws_per_subject": 100,
    "n_subject_draw_atoms_per_trial": 2500,
    "n_subjects": 25
   }
  },
  "power_truth": {
   "Exponential": {
    "band_q10": {
     "__abridged__": "20 floats",
     "first3": [
      20.166734822508374,
      5.9451322376609825,
      2.8809555147525545
     ],
     "last3": [
      1.8773686776818863,
      1.8894493047825847,
      1.796821131454743
     ],
     "min": 1.796821131454743,
     "max": 20.166734822508374
    },
    "band_q90": {
     "__abridged__": "20 floats",
     "first3": [
      165.34954717315534,
      71.66821248168323,
      37.21134816103033
     ],
     "last3": [
      30.69937570559497,
      31.306763681184584,
      31.87773548988951
     ],
     "min": 29.93659674609309,
     "max": 165.34954717315534
    },
    "mean": {
     "__abridged__": "20 floats",
     "first3": [
      82.55131856714787,
      35.498748994348915,
      18.472028138211964
     ],
     "last3": [
      14.214621062536567,
      14.250730790457578,
      14.6561233376211
     ],
     "min": 14.150570009396045,
     "max": 82.55131856714787
    },
    "n_draws_per_subject": 100,
    "n_subject_draw_atoms_per_trial": 2500,
    "n_subjects": 25
   },
   "Power": {
    "band_q10": {
     "__abridged__": "20 floats",
     "first3": [
      39.91884334259193,
      4.237254226050231,
      2.9045973332834594
     ],
     "last3": [
      1.9128475634933977,
      1.7914296228822877,
      1.8616069179872625
     ],
     "min": 1.7914296228822877,
     "max": 39.91884334259193
    },
    "band_q90": {
     "__abridged__": "20 floats",
     "first3": [
      220.89732610450812,
      49.78994971539974,
      48.53814917496235
     ],
     "last3": [
      27.985026300013217,
      27.72055134884421,
      27.767894354485318
     ],
     "min": 27.021405721199006,
     "max": 220.89732610450812
    },
    "mean": {
     "__abridged__": "20 floats",
     "first3": [
      116.33345732908461,
      25.2379587479166,
      22.174315401685487
     ],
     "last3": [
      12.801527709753213,
      12.727141658113304,
      12.936003405781614
     ],
     "min": 12.727141658113304,
     "max": 116.33345732908461
    },
    "n_draws_per_subject": 100,
    "n_subject_draw_atoms_per_trial": 2500,
    "n_subjects": 25
   }
  }
 },
 "schema_version": 1,
 "stored_mean_G_summaries": {
  "agnostic": {
   "pw_hellinger": {
    "all_subjects": {
     "Exponential": {
      "max": 0.18531375898146088,
      "mean": 0.1098689013483594,
      "median": 0.10386543994720254,
      "min": 0.06336188483022656,
      "n": 50,
      "q10": 0.07329515837210825,
      "q90": 0.1559772307158973,
      "sd": 0.031248018063003348
     },
     "Power": {
      "max": 0.16389040845977246,
      "mean": 0.10688636568152815,
      "median": 0.10453462948593145,
      "min": 0.06606708727900085,
      "n": 50,
      "q10": 0.08157342881707541,
      "q90": 0.13224495213766205,
      "sd": 0.02309193093257991
     }
    },
    "exponential_truth": {
     "Exponential": {
      "max": 0.18531375898146088,
      "mean": 0.11317127340607522,
      "median": 0.11319959186384826,
      "min": 0.06336188483022656,
      "n": 25,
      "q10": 0.07272118020248922,
      "q90": 0.17113648541158116,
      "sd": 0.03692583667130197
     },
     "Power": {
      "max": 0.1617256677382753,
      "mean": 0.1094976586144469,
      "median": 0.10860355071422807,
      "min": 0.07940380240330373,
      "n": 25,
      "q10": 0.08712297104539472,
      "q90": 0.12883255407343897,
      "sd": 0.020224949084010978
     }
    },
    "power_truth": {
     "Exponential": {
      "max": 0.15749778361642097,
      "mean": 0.10656652929064359,
      "median": 0.10181070473147785,
      "min": 0.06891961597869936,
      "n": 25,
      "q10": 0.07611782928472761,
      "q90": 0.1358884377447555,
      "sd": 0.02464395802983311
     },
     "Power": {
      "max": 0.16389040845977246,
      "mean": 0.10427507274860943,
      "median": 0.09515948307077003,
      "min": 0.06606708727900085,
      "n": 25,
      "q10": 0.07711641930336105,
      "q90": 0.13789634646264656,
      "sd": 0.025796090082980082
     }
    }
   },
   "pw_mse": {
    "all_subjects": {
     "Exponential": {
      "max": 2431.842934767534,
      "mean": 714.1717748532162,
      "median": 525.3137351109953,
      "min": 104.76565343377636,
      "n": 50,
      "q10": 233.179705128573,
      "q90": 1671.9475123679892,
      "sd": 571.2988049110696
     },
     "Power": {
      "max": 3221.66058931496,
      "mean": 1118.1999325059223,
      "median": 888.0640851775224,
      "min": 108.47823518763063,
      "n": 50,
      "q10": 267.93917569469306,
      "q90": 2268.4931079216394,
      "sd": 774.2977414173217
     }
    },
    "exponential_truth": {
     "Exponential": {
      "max": 1808.1870434833709,
      "mean": 609.2291955301771,
      "median": 528.7520909200068,
      "min": 189.64124992993118,
      "n": 25,
      "q10": 286.08206575774255,
      "q90": 925.9211522561227,
      "sd": 341.2423610819271
     },
     "Power": {
      "max": 3221.66058931496,
      "mean": 1434.1158084196452,
      "median": 1257.053173509159,
      "min": 363.07477621263934,
      "n": 25,
      "q10": 556.369828798053,
      "q90": 2352.1212658767927,
      "sd": 762.5834266998248
     }
    },
    "power_truth": {
     "Exponential": {
      "max": 2431.842934767534,
      "mean": 819.1143541762555,
      "median": 478.2071314842464,
      "min": 104.76565343377636,
      "n": 25,
      "q10": 210.5401810212096,
      "q90": 1952.4643416251627,
      "sd": 725.9296992040894
     },
     "Power": {
      "max": 2579.848188579353,
      "mean": 802.2840565922002,
      "median": 545.2015797669754,
      "min": 108.47823518763063,
      "n": 25,
      "q10": 249.08802312815268,
      "q90": 1658.6656633391005,
      "sd": 659.2409463688671
     }
    }
   },
   "pw_nll": {
    "all_subjects": {
     "Exponential": {
      "max": 5.3284222328343205,
      "mean": 4.763091419957126,
      "median": 4.7228004070050265,
      "min": 4.1806476093039775,
      "n": 50,
      "q10": 4.471238528970062,
      "q90": 5.160005688668149,
      "sd": 0.26836174261638973
     },
     "Power": {
      "max": 5.565599890510465,
      "mean": 4.939141081371759,
      "median": 4.968190044837277,
      "min": 4.17504542558414,
      "n": 50,
      "q10": 4.570128529337759,
      "q90": 5.301295803822148,
      "sd": 0.3131657073898058
     }
    },
    "exponential_truth": {
     "Exponential": {
      "max": 5.169519493439631,
      "mean": 4.715016096032026,
      "median": 4.718578424054743,
      "min": 4.336430289926343,
      "n": 25,
      "q10": 4.46543898779273,
      "q90": 4.923599552876055,
      "sd": 0.20641619695966731
     },
     "Power": {
      "max": 5.503530228106203,
      "mean": 5.044770458018034,
      "median": 5.087716193998989,
      "min": 4.593946387120125,
      "n": 25,
      "q10": 4.656514403761624,
      "q90": 5.325196557826574,
      "sd": 0.2523628272018629
     }
    },
    "power_truth": {
     "Exponential": {
      "max": 5.3284222328343205,
      "mean": 4.811166743882226,
      "median": 4.727022389955309,
      "min": 4.1806476093039775,
      "n": 25,
      "q10": 4.497075455431412,
      "q90": 5.216408483322802,
      "sd": 0.3156169796845663
     },
     "Power": {
      "max": 5.565599890510465,
      "mean": 4.833511704725485,
      "median": 4.757942990238933,
      "min": 4.17504542558414,
      "n": 25,
      "q10": 4.535965341439545,
      "q90": 5.2777211349980675,
      "sd": 0.3366005964139396
     }
    }
   }
  },
  "moderate": {
   "pw_hellinger": {
    "all_subjects": {
     "Exponential": {
      "max": 0.19800452795383144,
      "mean": 0.10816214535060248,
      "median": 0.10159662503094496,
      "min": 0.06397323196652732,
      "n": 50,
      "q10": 0.0709260995235993,
      "q90": 0.15525236213781715,
      "sd": 0.035984187886780074
     },
     "Power": {
      "max": 0.18181399255210484,
      "mean": 0.10128953599252474,
      "median": 0.09591091215106065,
      "min": 0.0630554211192391,
      "n": 50,
      "q10": 0.07423659301203117,
      "q90": 0.13094360956037585,
      "sd": 0.02726087681967454
     }
    },
    "exponential_truth": {
     "Exponential": {
      "max": 0.19800452795383144,
      "mean": 0.11728106228759616,
      "median": 0.11960709343879156,
      "min": 0.06853345960807833,
      "n": 25,
      "q10": 0.07147982785393182,
      "q90": 0.1715840596663853,
      "sd": 0.03953141655127291
     },
     "Power": {
      "max": 0.16483776137190234,
      "mean": 0.10579284737804015,
      "median": 0.10056792817900863,
      "min": 0.07717682617230884,
      "n": 25,
      "q10": 0.08289885235629549,
      "q90": 0.1279081971373664,
      "sd": 0.020562401107681868
     }
    },
    "power_truth": {
     "Exponential": {
      "max": 0.1764005980403819,
      "mean": 0.0990432284136088,
      "median": 0.08799882087542535,
      "min": 0.06397323196652732,
      "n": 25,
      "q10": 0.07042224879403518,
      "q90": 0.14665122453383034,
      "sd": 0.030128132853204252
     },
     "Power": {
      "max": 0.18181399255210484,
      "mean": 0.09678622460700934,
      "median": 0.08488410437094591,
      "min": 0.0630554211192391,
      "n": 25,
      "q10": 0.07135707726676493,
      "q90": 0.1404996812181573,
      "sd": 0.03243784314438514
     }
    }
   },
   "pw_mse": {
    "all_subjects": {
     "Exponential": {
      "max": 2596.009540253322,
      "mean": 708.2232922117612,
      "median": 475.8376491946626,
      "min": 67.68386498119456,
      "n": 50,
      "q10": 193.76328469529537,
      "q90": 1628.9123084852731,
      "sd": 620.4979500845176
     },
     "Power": {
      "max": 3221.02293832001,
      "mean": 1143.1471728758124,
      "median": 938.4129267956528,
      "min": 66.10893419501559,
      "n": 50,
      "q10": 262.5250988576272,
      "q90": 2241.6604181066027,
      "sd": 802.856806747426
     }
    },
    "exponential_truth": {
     "Exponential": {
      "max": 1480.455652786827,
      "mean": 547.6942856165269,
      "median": 475.66861913478556,
      "min": 145.33174217693792,
      "n": 25,
      "q10": 333.00292903302994,
      "q90": 881.7747974904383,
      "sd": 285.6509281340386
     },
     "Power": {
      "max": 3221.02293832001,
      "mean": 1436.2068761967146,
      "median": 1322.5312151291798,
      "min": 269.82732302695865,
      "n": 25,
      "q10": 559.4230626068313,
      "q90": 2365.1264110343304,
      "sd": 787.9243160747072
     }
    },
    "power_truth": {
     "Exponential": {
      "max": 2596.009540253322,
      "mean": 868.7522988069956,
      "median": 496.3374799626075,
      "min": 67.68386498119456,
      "n": 25,
      "q10": 171.14959998843074,
      "q90": 2121.8346992564057,
      "sd": 806.7185236375974
     },
     "Power": {
      "max": 2477.3216690587797,
      "mean": 850.0874695549101,
      "median": 509.198749411176,
      "min": 66.10893419501559,
      "n": 25,
      "q10": 213.7041823303907,
      "q90": 1971.0881470312515,
      "sd": 718.5164287347914
     }
    }
   },
   "pw_nll": {
    "all_subjects": {
     "Exponential": {
      "max": 5.369862405154479,
      "mean": 4.7592342612821765,
      "median": 4.720529106130893,
      "min": 4.165906975077859,
      "n": 50,
      "q10": 4.481481368517274,
      "q90": 5.203819429302811,
      "sd": 0.2816887695428852
     },
     "Power": {
      "max": 5.520935043475075,
      "mean": 4.95121512062536,
      "median": 4.960323225484167,
      "min": 4.165390092236595,
      "n": 50,
      "q10": 4.563652553768984,
      "q90": 5.328080582407324,
      "sd": 0.3244847413257521
     }
    },
    "exponential_truth": {
     "Exponential": {
      "max": 5.074613967801049,
      "mean": 4.688094273534259,
      "median": 4.704019216254089,
      "min": 4.305337612142693,
      "n": 25,
      "q10": 4.480468045516398,
      "q90": 4.915785572859853,
      "sd": 0.18819015209761178
     },
     "Power": {
      "max": 5.503382680682958,
      "mean": 5.04485369596999,
      "median": 5.082971856279948,
      "min": 4.585975472137819,
      "n": 25,
      "q10": 4.664593667347624,
      "q90": 5.319494252071634,
      "sd": 0.25810419416414987
     }
    },
    "power_truth": {
     "Exponential": {
      "max": 5.369862405154479,
      "mean": 4.830374249030095,
      "median": 4.724842382021279,
      "min": 4.165906975077859,
      "n": 25,
      "q10": 4.523608722639691,
      "q90": 5.256468399919868,
      "sd": 0.34065267552935663
     },
     "Power": {
      "max": 5.520935043475075,
      "mean": 4.857576545280731,
      "median": 4.754081383668751,
      "min": 4.165390092236595,
      "n": 25,
      "q10": 4.5271955586577945,
      "q90": 5.354189787996241,
      "sd": 0.36067016785869016
     }
    }
   }
  },
  "practitioner": {
   "pw_hellinger": {
    "all_subjects": {
     "Exponential": {
      "max": 0.15121570496770065,
      "mean": 0.0867924909165723,
      "median": 0.08071444363787753,
      "min": 0.04106073840295025,
      "n": 50,
      "q10": 0.046746006176923184,
      "q90": 0.12295842101086164,
      "sd": 0.03127369668119209
     },
     "Power": {
      "max": 0.1504155597506172,
      "mean": 0.08960357243229705,
      "median": 0.0885245955988743,
      "min": 0.04743284175024853,
      "n": 50,
      "q10": 0.061248694422716465,
      "q90": 0.11678155656758596,
      "sd": 0.02397499246019867
     }
    },
    "exponential_truth": {
     "Exponential": {
      "max": 0.14993859830940373,
      "mean": 0.08155964693474375,
      "median": 0.07392102875116423,
      "min": 0.04106073840295025,
      "n": 25,
      "q10": 0.04379533472133408,
      "q90": 0.13131003835207933,
      "sd": 0.032674746710025245
     },
     "Power": {
      "max": 0.14067368885462814,
      "mean": 0.09208333587124087,
      "median": 0.09172172615031682,
      "min": 0.06130310853802029,
      "n": 25,
      "q10": 0.07109348504099924,
      "q90": 0.11197837782575384,
      "sd": 0.018920799263751918
     }
    },
    "power_truth": {
     "Exponential": {
      "max": 0.15121570496770065,
      "mean": 0.09202533489840087,
      "median": 0.08846757983123134,
      "min": 0.0428550225811163,
      "n": 25,
      "q10": 0.0523041926717255,
      "q90": 0.12136240835639696,
      "sd": 0.029532249711686498
     },
     "Power": {
      "max": 0.1504155597506172,
      "mean": 0.08712380899335324,
      "median": 0.08247027274968509,
      "min": 0.04743284175024853,
      "n": 25,
      "q10": 0.05466862350067118,
      "q90": 0.12755867011706548,
      "sd": 0.028332719674363658
     }
    }
   },
   "pw_mse": {
    "all_subjects": {
     "Exponential": {
      "max": 2534.170189840253,
      "mean": 529.5775074001,
      "median": 291.86895538533804,
      "min": 49.2177324394177,
      "n": 50,
      "q10": 119.54270888023765,
      "q90": 1326.4789662311916,
      "sd": 570.5782282908608
     },
     "Power": {
      "max": 2846.9140667899,
      "mean": 1014.7897180631606,
      "median": 828.155255722123,
      "min": 47.88241455880803,
      "n": 50,
      "q10": 206.18352970193882,
      "q90": 2073.0947000505125,
      "sd": 736.7529956116566
     }
    },
    "exponential_truth": {
     "Exponential": {
      "max": 959.6896673246994,
      "mean": 324.75508106546016,
      "median": 238.75631345775895,
      "min": 90.5837162615731,
      "n": 25,
      "q10": 132.81261114127494,
      "q90": 552.9671594914222,
      "sd": 205.12087730826957
     },
     "Power": {
      "max": 2846.9140667899,
      "mean": 1297.1540316682167,
      "median": 1188.4482999626834,
      "min": 207.95996514846024,
      "n": 25,
      "q10": 458.72506680381235,
      "q90": 2149.502020308739,
      "sd": 725.2996913571337
     }
    },
    "power_truth": {
     "Exponential": {
      "max": 2534.170189840253,
      "mean": 734.3999337347398,
      "median": 410.973335246021,
      "min": 49.2177324394177,
      "n": 25,
      "q10": 108.26219466844006,
      "q90": 1855.0680106552118,
      "sd": 731.5797722369879
     },
     "Power": {
      "max": 2321.33381644341,
      "mean": 732.4254044581046,
      "median": 457.43508746540834,
      "min": 47.88241455880803,
      "n": 25,
      "q10": 169.27230252760444,
      "q90": 1683.4198389534974,
      "sd": 645.0301076928481
     }
    }
   },
   "pw_nll": {
    "all_subjects": {
     "Exponential": {
      "max": 5.354252450074387,
      "mean": 4.678814928889871,
      "median": 4.650359763046838,
      "min": 4.142040587766264,
      "n": 50,
      "q10": 4.334035615373534,
      "q90": 5.077653465032615,
      "sd": 0.2813772127113332
     },
     "Power": {
      "max": 5.45298020009383,
      "mean": 4.900992031219464,
      "median": 4.914751280273908,
      "min": 4.142113154555164,
      "n": 50,
      "q10": 4.530930719131785,
      "q90": 5.256654170898235,
      "sd": 0.30580208415412863
     }
    },
    "exponential_truth": {
     "Exponential": {
      "max": 4.923808854259941,
      "mean": 4.58230040391341,
      "median": 4.584490820235111,
      "min": 4.266920062153946,
      "n": 25,
      "q10": 4.333773491728027,
      "q90": 4.85000774435498,
      "sd": 0.20121075954105128
     },
     "Power": {
      "max": 5.416816831269922,
      "mean": 5.003423504787838,
      "median": 5.073711862721793,
      "min": 4.565311975832221,
      "n": 25,
      "q10": 4.609357790537788,
      "q90": 5.288469836491088,
      "sd": 0.25777387190193085
     }
    },
    "power_truth": {
     "Exponential": {
      "max": 5.354252450074387,
      "mean": 4.775329453866333,
      "median": 4.719115922828009,
      "min": 4.142040587766264,
      "n": 25,
      "q10": 4.478331300025513,
      "q90": 5.186473965564747,
      "sd": 0.31898749355924744
     },
     "Power": {
      "max": 5.45298020009383,
      "mean": 4.798560557651089,
      "median": 4.728674810746229,
      "min": 4.142113154555164,
      "n": 25,
      "q10": 4.5135918677813605,
      "q90": 5.211924854410063,
      "sd": 0.32034380120299966
     }
    }
   }
  }
 },
 "stored_named_examples": {
  "synth_exponential_sub25_practitioner_pw_nll": {
   "Exponential_mean_G": 4.851946206185004,
   "Power_mean_G": 4.881274255352302,
   "absolute_difference": 0.029328049167298254,
   "source_file": "synth_exponential_sub25_default.json"
  }
 },
 "stored_selection_summary": {
  "bic_by_cohort": {
   "exponential_truth": {
    "known_truth_correct": 24,
    "n": 25,
    "winner_counts": {
     "Exponential": 24,
     "Power": 1
    }
   },
   "power_truth": {
    "known_truth_correct": 17,
    "n": 25,
    "winner_counts": {
     "Exponential": 8,
     "Power": 17
    }
   }
  },
  "bic_winner_counts_all_subjects": {
   "Exponential": 32,
   "Power": 18
  },
  "bistar_at_stored_median_tau": {
   "agnostic": {
    "pw_hellinger": {
     "known_truth_accuracy": 0.52,
     "known_truth_correct": 26,
     "maximum_candidate_probability": {
      "max": 0.5086351656699876,
      "mean": 0.5017647990263641,
      "median": 0.5012465061227178,
      "min": 0.5000336517556901,
      "n": 50,
      "q10": 0.5002265054408694,
      "q90": 0.5038044037064466,
      "sd": 0.001870355769718003
     },
     "reference_tau": 1.7782794100389228,
     "winner_counts_all_subjects": {
      "Exponential": 23,
      "Power": 27
     },
     "winner_counts_by_cohort": {
      "exponential_truth": {
       "Exponential": 12,
       "Power": 13
      },
      "power_truth": {
       "Exponential": 11,
       "Power": 14
      }
     }
    },
    "pw_mse": {
     "known_truth_accuracy": 0.64,
     "known_truth_correct": 32,
     "maximum_candidate_probability": {
      "max": 1.0,
      "mean": 0.863986968865389,
      "median": 0.9150003603100036,
      "min": 0.540476464423542,
      "n": 50,
      "q10": 0.6156740107298369,
      "q90": 1.0,
      "sd": 0.14057940337928485
     },
     "reference_tau": 1.7782794100389228,
     "winner_counts_all_subjects": {
      "Exponential": 43,
      "Power": 7
     },
     "winner_counts_by_cohort": {
      "exponential_truth": {
       "Exponential": 25
      },
      "power_truth": {
       "Exponential": 18,
       "Power": 7
      }
     }
    },
    "pw_nll": {
     "known_truth_accuracy": 0.74,
     "known_truth_correct": 37,
     "maximum_candidate_probability": {
      "max": 0.5998365301828461,
      "mean": 0.5270770911993057,
      "median": 0.5178784875172757,
      "min": 0.5000660387624092,
      "n": 50,
      "q10": 0.5011426421199726,
      "q90": 0.5701546789345181,
      "sd": 0.02701222111244604
     },
     "reference_tau": 1.7782794100389228,
     "winner_counts_all_subjects": {
      "Exponential": 38,
      "Power": 12
     },
     "winner_counts_by_cohort": {
      "exponential_truth": {
       "Exponential": 25
      },
      "power_truth": {
       "Exponential": 13,
       "Power": 12
      }
     }
    }
   },
   "moderate": {
    "pw_hellinger": {
     "known_truth_accuracy": 0.5,
     "known_truth_correct": 25,
     "maximum_candidate_probability": {
      "max": 0.5121449154202602,
      "mean": 0.5019973859627206,
      "median": 0.5012298146143527,
      "min": 0.5000056805378968,
      "n": 50,
      "q10": 0.5001957156828356,
      "q90": 0.5039249680307916,
      "sd": 0.0022345274924385943
     },
     "reference_tau": 1.7782794100389228,
     "winner_counts_all_subjects": {
      "Exponential": 18,
      "Power": 32
     },
     "winner_counts_by_cohort": {
      "exponential_truth": {
       "Exponential": 9,
       "Power": 16
      },
      "power_truth": {
       "Exponential": 9,
       "Power": 16
      }
     }
    },
    "pw_mse": {
     "known_truth_accuracy": 0.64,
     "known_truth_correct": 32,
     "maximum_candidate_probability": {
      "max": 1.0,
      "mean": 0.8824747196194563,
      "median": 0.9549799063756428,
      "min": 0.5393989656538001,
      "n": 50,
      "q10": 0.626280005266397,
      "q90": 1.0,
      "sd": 0.14481840767972953
     },
     "reference_tau": 1.7782794100389228,
     "winner_counts_all_subjects": {
      "Exponential": 43,
      "Power": 7
     },
     "winner_counts_by_cohort": {
      "exponential_truth": {
       "Exponential": 25
      },
      "power_truth": {
       "Exponential": 18,
       "Power": 7
      }
     }
    },
    "pw_nll": {
     "known_truth_accuracy": 0.74,
     "known_truth_correct": 37,
     "maximum_candidate_probability": {
      "max": 0.5894507181759914,
      "mean": 0.5287001859981573,
      "median": 0.5218032192123964,
      "min": 0.5000715815788948,
      "n": 50,
      "q10": 0.5013968323981451,
      "q90": 0.5751364346043113,
      "sd": 0.028192069079753634
     },
     "reference_tau": 1.7782794100389228,
     "winner_counts_all_subjects": {
      "Exponential": 38,
      "Power": 12
     },
     "winner_counts_by_cohort": {
      "exponential_truth": {
       "Exponential": 25
      },
      "power_truth": {
       "Exponential": 13,
       "Power": 12
      }
     }
    }
   },
   "practitioner": {
    "pw_hellinger": {
     "known_truth_accuracy": 0.66,
     "known_truth_correct": 33,
     "maximum_candidate_probability": {
      "max": 0.5063822999982567,
      "mean": 0.5022002844297735,
      "median": 0.5019529105054292,
      "min": 0.5000971107664142,
      "n": 50,
      "q10": 0.5003774025199903,
      "q90": 0.5046260306691676,
      "sd": 0.0016580902092092327
     },
     "reference_tau": 1.7782794100389228,
     "winner_counts_all_subjects": {
      "Exponential": 28,
      "Power": 22
     },
     "winner_counts_by_cohort": {
      "exponential_truth": {
       "Exponential": 18,
       "Power": 7
      },
      "power_truth": {
       "Exponential": 10,
       "Power": 15
      }
     }
    },
    "pw_mse": {
     "known_truth_accuracy": 0.62,
     "known_truth_correct": 31,
     "maximum_candidate_probability": {
      "max": 1.0,
      "mean": 0.9257766600845908,
      "median": 0.999996724743484,
      "min": 0.5238690083292554,
      "n": 50,
      "q10": 0.7022795578661606,
      "q90": 1.0,
      "sd": 0.1360330173797347
     },
     "reference_tau": 1.7782794100389228,
     "winner_counts_all_subjects": {
      "Exponential": 44,
      "Power": 6
     },
     "winner_counts_by_cohort": {
      "exponential_truth": {
       "Exponential": 25
      },
      "power_truth": {
       "Exponential": 19,
       "Power": 6
      }
     }
    },
    "pw_nll": {
     "known_truth_accuracy": 0.7,
     "known_truth_correct": 35,
     "maximum_candidate_probability": {
      "max": 0.6130004087309219,
      "mean": 0.5333208041713768,
      "median": 0.5223093599124856,
      "min": 0.5000111398788387,
      "n": 50,
      "q10": 0.5013118510642072,
      "q90": 0.5852500893894331,
      "sd": 0.03339744967733155
     },
     "reference_tau": 1.7782794100389228,
     "winner_counts_all_subjects": {
      "Exponential": 40,
      "Power": 10
     },
     "winner_counts_by_cohort": {
      "exponential_truth": {
       "Exponential": 25
      },
      "power_truth": {
       "Exponential": 15,
       "Power": 10
      }
     }
    }
   }
  },
  "robustness_across_configs": {
   "pw_hellinger": {
    "agree": 39,
    "disagree": 11,
    "fraction_all_configs_agree": 0.78
   },
   "pw_mse": {
    "agree": 49,
    "disagree": 1,
    "fraction_all_configs_agree": 0.98
   },
   "pw_nll": {
    "agree": 48,
    "disagree": 2,
    "fraction_all_configs_agree": 0.96
   }
  }
 },
 "trial_grid": {
  "__abridged__": "20 floats",
  "first3": [
   1.0,
   2.0,
   3.0
  ],
  "last3": [
   18.0,
   19.0,
   20.0
  ],
  "min": 1.0,
  "max": 20.0
 }
}

=== BRANCH DIFF vs main (results.json and PNG excluded from the textual diff; JSON content above) ===
Stat:
 Notes/DECISIONS.md                                |   96 +
 docs/paper-sie-jmp/06-case-D-mopen-calibration.md |  178 ++
 experiments/regret_curves_mopen.py                |  661 ++++++
 runs/regret_curves_mopen/README.md                |   68 +
 runs/regret_curves_mopen/regret_curves.png        |  Bin 0 -> 159881 bytes
 runs/regret_curves_mopen/results.json             | 2330 +++++++++++++++++++++
 6 files changed, 3333 insertions(+)

diff --git a/Notes/DECISIONS.md b/Notes/DECISIONS.md
index 033fee3..bfaca79 100644
--- a/Notes/DECISIONS.md
+++ b/Notes/DECISIONS.md
@@ -5716,3 +5716,99 @@ to be amended later merely to insert them. STOP before Ready or merge. NOT autho
 second correction pass, restoring/applying/dropping stash `5280d1e1…`, D59 work, evidence
 or figure changes, poster-repository work, the captions themselves, Della contact, new
 computation, holdout access, BMS*, Ready, or merge.
+
+## D64: Case D synthetic distinguishability calibration and regret localization — 2026-08-11
+
+**Problem:** Case D needed per-trial regret curves and an honest M-open
+calibration argument from the existing practice-law artifacts, without rerunning
+`experiments/practice_EvansEtAL/run.py`, changing its artifacts, or starting new
+HMC. Inventory found no regret implementation and no files under the practice
+data directory. The 50 `results_hmc/` subject files therefore concern only
+`generate_demo_data(n_subjects=50, seed=42)`, with 25 power-generated and 25
+exponential-generated series. Both generating forms appear in the fitted pair,
+so the cohort supports a distinguishability and mimicry study plus
+correct-specification reference levels for stored divergence magnitudes, not a
+real-Evans-data analysis or a direct M-open misspecification finding. Direct
+inspection also corrected one work-order shorthand: the stored and regenerated
+training series range from 20 to 79 trials rather than containing 20 trials
+each; every series contains the common trials 1 through 20 used in the figure.
+
+**Decision:** Added `experiments/regret_curves_mopen.py`, which writes
+`runs/regret_curves_mopen/{results.json,README.md,regret_curves.png}`. It prefers
+the read-only `experiments/practice_EvansEtAL/results_hmc/` directory, imports
+`generate_demo_data` and the Power and Exponential classes from the practice
+experiment rather than copying them, and evaluates stored fitted parameters on
+the regenerated full subject series before any regret calculation. Data seed
+42 regenerates the observations. Subject `i` receives posterior-function seed
+`20260811 + i`, with 100 latent conditional GP draws and no added observation
+noise. The common evaluation grid contains trials 1 through 20. At each trial,
+the curve reports
+`regret_theta(t) = E_draws[abs(mu_GP(t) - mu_theta(t))]`; its band spans the
+pooled 10th and 90th percentiles across 25 subjects times 100 draws within each
+truth cohort, so it describes dispersion rather than a confidence interval for
+the mean. The formal limits-note equation and the Case D work order specify the
+absolute difference; a chat-derived Q&A in the same note says squared
+difference, and the binding absolute formula takes precedence.
+
+`run.py` loops through practitioner, moderate, and agnostic configurations. It
+sets the single `gp_hyperparameters` block only while that block remains empty,
+immediately after a successful configuration MAP fit and before the HMC branch.
+All 50 source files contain every configuration's diagnostics, so their stored
+lengthscale, outputscale, and noise values come from the first, practitioner MAP
+fit even in `results_hmc/`. The subject JSONs do not retain HMC hyperparameter
+draws. The regret script therefore rebuilds the practitioner RBF GP at that
+stored point and performs exact conditioning with normalized-variance jitter
+`1e-6`; it neither refits hyperparameters nor reconstructs HMC trajectories.
+The stored `bistar_G_diagnostics` values are aggregated without recomputing G.
+Those artifacts predate W1 and contain `pw_nll`, `pw_mse`, and
+`pw_hellinger`, not `pw_kl_vcal`; `pw_nll` receives closest-role framing but no
+renaming. `docs/paper-sie-jmp/06-case-D-mopen-calibration.md` states these
+limits, separates F1 scaffold representability from F2 intrinsic mimicry, and
+positions the result against Navarro, Pitt, and Myung (2004), Evans et al.
+(2018), and Averell and Heathcote (2011).
+
+**Alternatives considered:** Using `results/` was rejected because the work
+order prefers the HMC-mode artifacts. `results_diag/` and
+`results_hierarchical/` were not consulted because no documented need emerged.
+Rerunning the practice scripts, refitting candidate or GP parameters, and
+starting HMC were rejected by scope and because the required reconstruction
+uses frozen artifacts. A squared regret was rejected because it conflicts with
+the binding formula. A normalized 20-point refit was rejected in favor of
+conditioning on every regenerated observation and evaluating only the common
+20-trial grid. The optional transform-space E8b module was deferred by the
+driver; no `experiments/e8b_transform_space.py` was created, and the section
+retains an explicit `[E8B-PLACEHOLDER]` block for later commissioning or clean
+excision.
+
+**Result:** The fidelity gate recomputed 100 stored candidate BIC log marginal
+likelihoods from regenerated observations and stored parameters. Maximum and
+mean absolute errors equal `5.684e-14` and `5.116e-15`, below the asserted
+`1e-8` tolerance. The minimum posterior-covariance eigenvalue across subjects
+equals `-2.400e-15`, within the `1e-8` numerical PSD tolerance. Two consecutive
+runs produced identical SHA-1 values for all three outputs. The figure occupies
+159,881 bytes, below 2 MB.
+
+For power-generated curves, mean regret across 20 trials equals 21.383 for
+Power and 20.681 for Exponential. The gap peaks at 33.782 on trial 1; trials 1
+through 5 account for 70.0% of its summed gap and trials 1 through 10 account
+for 82.2%. For exponential-generated curves, the corresponding means equal
+35.587 and 14.855, the trial-1 peak equals 91.452, and the two early shares
+equal 41.7% and 77.7%. The signal therefore concentrates early without
+vanishing after the first few exponential-cohort trials. The power cohort also
+shows the wrong exponential candidate closer at the largest-gap trial, which
+localizes the stored method's asymmetric recovery failure rather than hiding it
+behind a winner count.
+
+The aggregated stored practitioner `pw_nll` means equal 4.799 for Power and
+4.775 for Exponential under power truth, versus 5.003 and 4.582 under
+exponential truth. Synthetic exponential subject 25 supplies a particularly
+clear mimicry example: 4.881 for Power and 4.852 for Exponential, an absolute
+difference of 0.029. These known-truth levels show what a future absolute
+inadequacy calibration must condition on; Case D sets no rejection threshold.
+The `pw_nll` soft read remains weak despite stable winner labels: median maximum
+candidate probabilities equal 0.522, 0.522, and 0.518 for practitioner,
+moderate, and agnostic. The section confines its warranted-decline claim to
+that legacy closest-role metric because `pw_mse` behaves much more sharply.
+The bytewise inventory hash for every file under
+`experiments/practice_EvansEtAL/` remained
+`528fea7d955841cf496883df4f96bb85b8357b4a` before and after execution.
diff --git a/docs/paper-sie-jmp/06-case-D-mopen-calibration.md b/docs/paper-sie-jmp/06-case-D-mopen-calibration.md
new file mode 100644
index 0000000..f07b4ed
--- /dev/null
+++ b/docs/paper-sie-jmp/06-case-D-mopen-calibration.md
@@ -0,0 +1,178 @@
+# 6. Case D: M-open calibration through a warranted decline [DRAFT]
+
+## Calibration before an M-open claim
+
+A relative winner does not establish adequacy. BMS* retains the raw
+divergences (G(\psi,\theta)), so it can ask whether even the closest candidate
+remains far from the GP patterns. That absolute reading needs a reference
+distribution under known truth. Without one, a large-looking value has no
+calibrated interpretation. Formal M-open calibration therefore remains an open
+problem.
+
+The practice-law artifacts offer a bounded first step, not an M-open test. Their
+data directory contains no Evans et al. observations. `run.py` instead generated
+50 synthetic series with seed 42, divided equally between power and exponential
+truth. Each subject's generating form appears among the two fitted candidates.
+The source artifacts record between 20 and 79 observations per subject, and the
+regret analysis uses their common first 20 trials. We use these data to study
+distinguishability and mimicry and to establish correct-specification reference
+levels for (G); we do not infer how either candidate fits the real Evans
+corpus.[^case-d-empirical] Evans et al.'s broader candidate discussion motivates
+the context, while every result below concerns only Power and Exponential, the
+pair retained in the stored fits.[^case-d-evans]
+
+## Two failure geometries
+
+Two obstacles require separate diagnoses. F1 concerns scaffold
+representability. A stationary RBF kernel assigns one global lengthscale, while
+power and exponential curves differ through a location-dependent rate of
+curvature change. The scaffold can smooth over the local feature needed for
+discrimination. F2 concerns intrinsic mimicry. Across some parameter regions,
+the candidate families generate nearly indistinguishable patterns, so changing
+the scoring rule cannot create information absent from the data.
+
+Navarro, Pitt, and Myung's landscaping method maps such variation in
+distinguishability over retention-model parameter spaces. Their analysis shows
+why a close fit at one observed data set cannot establish that the models were
+distinguishable there: one candidate may mimic another over a broad region.[^case-d-navarro]
+Their empirical setting concerned retention rather than practice, so the link
+here concerns failure geometry, not a replication. Under that geometry, weak
+separation can reflect a warranted decline rather than a failed demand for a
+winner. The synthetic known-truth design sharpens the interpretation: when the
+correct family appears in the roster yet remains hard to recover, F1, F2, or
+both have constrained the comparison.
+
+## What the stored comparisons declined
+
+We prefer `results_hmc/` over the MAP-mode directory because it contains the
+HMC-mode practice run requested for this case. Its aggregate baseline assigns
+18 subjects to Power and 32 to Exponential under BIC, although the generator
+split equals 25 and 25; 41 of 50 labels match known truth. The BMS* winner labels
+at the stored median temperature, τ = 1.778, vary substantially with the legacy
+pointwise metric:
+
+| GP configuration | `pw_hellinger`, Power / Exponential | `pw_mse`, Power / Exponential | `pw_nll`, Power / Exponential |
+|---|---:|---:|---:|
+| practitioner | 22 / 28 | 6 / 44 | 10 / 40 |
+| moderate | 32 / 18 | 7 / 43 | 12 / 38 |
+| agnostic | 27 / 23 | 7 / 43 | 12 / 38 |
+| all configurations agree | 39 / 50 | 49 / 50 | 48 / 50 |
+
+These practice artifacts predate W1. They contain `pw_nll`, `pw_mse`, and
+`pw_hellinger`, not the manuscript's primary `pw_kl_vcal`; no new metric was
+authorized for Case D, and we do not relabel the stored quantities.
+`pw_nll` comes closest to the W1 primary role because it combines mean mismatch
+with pointwise variance calibration. Under `pw_nll`, known-truth accuracy equals
+35 of 50 for practitioner and 37 of 50 for both moderate and agnostic. More
+importantly for a decline, median winning probabilities equal only 0.522, 0.522,
+and 0.518 across those configurations. Winner stability therefore coexists with
+weak pairwise separation and a systematic preference for Exponential. The
+much sharper `pw_mse` decisions prevent a metric-general claim that BMS*
+declined. The calibrated claim applies to the `pw_nll` read and its associated
+regret geometry.[^case-d-empirical]
+
+## Absolute divergence magnitudes
+
+Rankings discard the common level of mismatch. The stored `pw_nll`
+diagnostics retain the mean (G) over 100 GP draws for each fitted candidate.
+The cohort means below come directly from those stored values; the Case D
+script aggregates them without recomputing (G).
+
+| GP configuration | Power truth: (G_{\mathrm{Power}}) | Power truth: (G_{\mathrm{Exp}}) | Exponential truth: (G_{\mathrm{Power}}) | Exponential truth: (G_{\mathrm{Exp}}) |
+|---|---:|---:|---:|---:|
+| practitioner | 4.799 | 4.775 | 5.003 | 4.582 |
+| moderate | 4.858 | 4.830 | 5.045 | 4.688 |
+| agnostic | 4.834 | 4.811 | 5.045 | 4.715 |
+
+The power-generated rows exhibit the mimicry signature: both magnitudes nearly
+coincide, and the wrong exponential candidate has the slightly smaller cohort
+mean. The exponential-generated rows separate more clearly and favor the known
+truth. At synthetic exponential subject 25, the practitioner `pw_nll` means
+equal 4.881 for Power and 4.852 for Exponential, an absolute difference of
+0.029. A ranking reports only Exponential; the paired magnitudes show how
+little separates the candidates for that subject.[^case-d-empirical]
+
+The table also blocks an overstatement about M-open inadequacy. Correctly
+specified candidates can produce mean (G) values from 4.582 to 4.858 in these
+cohort summaries, while a wrong but mimicking candidate can occupy much of the
+same scale. A future inadequacy rule must compare an observed magnitude with a
+reference distribution under correct specification, conditional on metric,
+configuration, sample size, and noise. These known-truth `mean_G` distributions
+supply the kind of calibration material such a rule needs, but Case D does not
+set a rejection threshold.
+
+## Regret localizes the comparison
+
+The subject JSONs omit GP curves and draws. The new reconstruction regenerates
+the synthetic observations, verifies each stored candidate fit through its BIC
+residual structure, rebuilds an exact GP at the stored hyperparameters, and
+draws 100 seeded latent posterior functions per subject. No refitting and no
+new HMC occur. For candidate θ and trial (t), the reported estimand follows the
+binding absolute-difference formula
+
+\[
+\operatorname{regret}_{\theta}(t)
+= \mathbb{E}_{\mathrm{draws}}
+  \left[\left|\mu_{\mathrm{GP}}(t)-\mu_{\theta}(t)\right|\right].
+\]
+
+Each line pools 25 subjects and 100 draws within a truth cohort. The shaded band
+spans the pooled 10th and 90th percentiles of the resulting 2,500 absolute
+errors at each trial; it describes subject-and-draw dispersion, not uncertainty
+in the cohort mean.
+
+![Regret curves for the two synthetic truth cohorts](../../runs/regret_curves_mopen/regret_curves.png)
+
+| Truth cohort | Mean Power regret | Mean Exponential regret | Peak discrimination gap | Gap in trials 1–5 | Gap in trials 1–10 |
+|---|---:|---:|---:|---:|---:|
+| Power | 21.383 | 20.681 | 33.782 at trial 1 | 70.0% | 82.2% |
+| Exponential | 35.587 | 14.855 | 91.452 at trial 1 | 41.7% | 77.7% |
+
+The discrimination profile concentrates toward the beginning but does not
+collapse to only the first few trials. For power-generated curves, trial 1
+produces regrets of 116.333 for Power and 82.551 for Exponential, so the GP
+reconstruction favors the wrong family precisely where the largest gap occurs.
+The later gap rapidly contracts. For exponential-generated curves, trial 1
+produces regrets of 131.415 for Power and 39.963 for Exponential, and appreciable
+separation continues through the first half of the grid. Regret therefore
+explains both sides of the aggregate result: strong localization can support
+correct recovery, as in the exponential cohort, or expose a scaffold-induced
+preference for the wrong mimicking curve, as in the power cohort.[^case-d-empirical]
+
+One provenance limitation matters. `run.py` writes one
+`gp_hyperparameters` block immediately after the first successful configuration
+MAP fit. With the default order, all 50 source files record the practitioner MAP
+point even though `results_hmc/` subsequently uses HMC samples for its stored
+BMS* diagnostics. The JSONs do not retain those HMC hyperparameter draws. The
+regret curves consequently condition at the stored practitioner MAP point and
+sample functions from that exact conditional GP; they should not be described
+as reconstructed HMC trajectories.
+
+## Positioning and optional extension
+
+Averell and Heathcote showed that power-versus-exponential conclusions about
+forgetting can change between individual-level and population-level analyses.
+Their result warns against treating one comparison procedure or aggregation
+level as a resolution of the functional-form debate.[^case-d-averell] Case D
+supports a narrower conclusion. On synthetic practice curves, the legacy
+`pw_nll` comparison expresses weak confidence, its raw divergence magnitudes
+provide correct-specification reference levels, and regret identifies where
+the scaffold helps or misleads. Nothing here adjudicates the real practice data
+or the forgetting literature.
+
+> **[E8B-PLACEHOLDER] UNBUILT OPTIONAL MODULE.** The proposed extension would
+> refit in semi-log and log-log spaces, with an explicit lognormal or
+> heteroskedastic noise correction, to turn curvature-rate differences into a
+> global linearity comparison; a Murre and Dros real-data companion would
+> remain separate from the present synthetic cohort. The driver deferred
+> `e8b_transform_space.py` in this pass. The author may commission the module or
+> excise this entire block; the current evidence makes no transform-space
+> claim.
+
+[^case-d-navarro]: 🟢 peer-reviewed — Navarro, D. J., Pitt, M. A., & Myung, I. J. (2004). Assessing the distinguishability of models and the informativeness of data. *Cognitive Psychology, 49*(1), 47–84. https://doi.org/10.1016/j.cogpsych.2003.11.001
+[^case-d-evans]: 🟢 peer-reviewed — Evans, N. J., Brown, S. D., Mewhort, D. J. K., & Heathcote, A. (2018). Refining the law of practice. *Psychological Review, 125*(4), 592–605.
+[^case-d-averell]: 🟢 peer-reviewed — Averell, L., & Heathcote, A. (2011). The form of the forgetting curve and the fate of memories. *Journal of Mathematical Psychology, 55*(1), 25–35.
+[^case-d-empirical]: 🟠 empirical — `experiments/regret_curves_mopen.py`; `runs/regret_curves_mopen/results.json` and `regret_curves.png`. The script reads `experiments/practice_EvansEtAL/results_hmc/aggregate.json` and its 50 subject JSONs, asserts reconstruction fidelity, and records all reported practice-run numbers in one artifact.
+
+---
+*Provenance: `runs/regret_curves_mopen/` · `experiments/regret_curves_mopen.py` · D64.*
diff --git a/experiments/regret_curves_mopen.py b/experiments/regret_curves_mopen.py
new file mode 100644
index 0000000..fa88948
--- /dev/null
+++ b/experiments/regret_curves_mopen.py
@@ -0,0 +1,661 @@
+#!/usr/bin/env python3
+"""Reconstruct Case D regret curves from the frozen practice artifacts.
+
+The script does not fit candidates, optimize GP hyperparameters, or run HMC.
+It regenerates the seeded synthetic observations, verifies the stored BIC
+values from the stored candidate parameters, conditions an exact GP at the
+stored practitioner MAP hyperparameters, and draws latent functions on the
+common first-20-trial grid.
+"""
+
+from __future__ import annotations
+
+import json
+import math
+import sys
+from collections import Counter
+from pathlib import Path
+from typing import Any
+
+import matplotlib
+import numpy as np
+import torch
+
+matplotlib.use("Agg")
+import matplotlib.pyplot as plt
+
+
+ROOT = Path(__file__).resolve().parents[1]
+PRACTICE_DIR = ROOT / "experiments" / "practice_EvansEtAL"
+SOURCE_DIR = PRACTICE_DIR / "results_hmc"
+OUTPUT_DIR = ROOT / "runs" / "regret_curves_mopen"
+
+DATA_SEED = 42
+DRAW_SEED_BASE = 20_260_811
+N_SUBJECTS = 50
+N_DRAWS = 100
+TRIAL_GRID = np.arange(1.0, 21.0)
+BIC_ABS_TOL = 1e-8
+CONDITIONING_JITTER = 1e-6
+PSD_ABS_TOL = 1e-8
+FIGURE_SIZE_LIMIT = 2_000_000
+
+# Importing the read-only practice modules must not update their bytecode.
+sys.dont_write_bytecode = True
+sys.path.insert(0, str(PRACTICE_DIR))
+import run as practice_run  # noqa: E402
+from candidates import ExponentialModel, PowerModel  # noqa: E402
+from kernels import PRACTICE_CONFIGS, build_kernel, build_likelihood  # noqa: E402
+
+
+def _json_ready(value: Any) -> Any:
+    """Convert numpy containers and scalars to strict JSON values."""
+    if isinstance(value, dict):
+        return {str(k): _json_ready(v) for k, v in value.items()}
+    if isinstance(value, (list, tuple)):
+        return [_json_ready(v) for v in value]
+    if isinstance(value, np.ndarray):
+        return [_json_ready(v) for v in value.tolist()]
+    if isinstance(value, (np.bool_, bool)):
+        return bool(value)
+    if isinstance(value, (np.floating, float)):
+        value = float(value)
+        if not math.isfinite(value):
+            raise ValueError(f"Non-finite JSON value: {value}")
+        return value
+    if isinstance(value, (np.integer, int)):
+        return int(value)
+    return value
+
+
+def _summary(values: list[float] | np.ndarray) -> dict[str, Any]:
+    arr = np.asarray(values, dtype=float)
+    if arr.size == 0:
+        raise ValueError("Cannot summarize an empty collection")
+    return {
+        "n": int(arr.size),
+        "mean": float(arr.mean()),
+        "sd": float(arr.std(ddof=1)) if arr.size > 1 else 0.0,
+        "q10": float(np.quantile(arr, 0.10)),
+        "median": float(np.median(arr)),
+        "q90": float(np.quantile(arr, 0.90)),
+        "min": float(arr.min()),
+        "max": float(arr.max()),
+    }
+
+
+def _candidate_from_params(name: str, params: dict[str, float]):
+    if name == "Power":
+        candidate = PowerModel()
+    elif name == "Exponential":
+        candidate = ExponentialModel()
+    else:
+        raise ValueError(f"Unsupported stored candidate: {name}")
+    for key in ("a", "b", "c", "sigma"):
+        setattr(candidate, key, float(params[key]))
+    return candidate
+
+
+def _stored_bic_from_regenerated_data(
+    candidate, x_raw: np.ndarray, y_raw: np.ndarray
+) -> float:
+    """Mirror CandidateModel.log_marginal_likelihood without refitting."""
+    pred = candidate.predict(x_raw)
+    residuals = y_raw - pred.mean
+    sigma2 = pred.noise_var
+    n = y_raw.size
+    k = candidate.n_free_params + 1
+    log_likelihood = (
+        -0.5 * n * np.log(2.0 * np.pi * sigma2)
+        - 0.5 * np.sum(residuals**2) / sigma2
+    )
+    return float(log_likelihood - 0.5 * k * np.log(n))
+
+
+def _conditioned_function_draws(
+    ncurve,
+    hp: dict[str, float],
+    trial_grid: np.ndarray,
+    subject_seed: int,
+) -> tuple[np.ndarray, dict[str, float]]:
+    """Draw latent GP functions after exact conditioning at stored MAP HPs."""
+    x_train = torch.as_tensor(ncurve.x, dtype=torch.float64)
+    y_train = torch.as_tensor(ncurve.y, dtype=torch.float64)
+    x_eval_norm = (trial_grid - ncurve.x_min) / (ncurve.x_max - ncurve.x_min)
+    x_eval = torch.as_tensor(x_eval_norm, dtype=torch.float64)
+
+    kernels, names = build_kernel(PRACTICE_CONFIGS["practitioner"])
+    likelihood = build_likelihood(PRACTICE_CONFIGS["practitioner"])
+    model, likelihood = practice_run.build_model(
+        x_train, y_train, kernels, names, likelihood
+    )
+    with torch.no_grad():
+        model.kernel_components[0].base_kernel.lengthscale = float(hp["lengthscale"])
+        model.kernel_components[0].outputscale = float(hp["outputscale"])
+        likelihood.noise = float(hp["noise"])
+
+    model.eval()
+    likelihood.eval()
+    with torch.no_grad():
+        k_xx = model.covar_module(x_train, x_train).to_dense()
+        k_sx = model.covar_module(x_eval, x_train).to_dense()
+        k_ss = model.covar_module(x_eval, x_eval).to_dense()
+        eye = torch.eye(x_train.numel(), dtype=torch.float64)
+        chol = torch.linalg.cholesky(
+            k_xx + (float(hp["noise"]) + CONDITIONING_JITTER) * eye
+        )
+        alpha = torch.cholesky_solve(y_train[:, None], chol).squeeze(1)
+        posterior_mean = k_sx @ alpha
+        v = torch.linalg.solve_triangular(chol, k_sx.T, upper=False)
+        posterior_cov = k_ss - v.T @ v
+
+    mean = posterior_mean.cpu().numpy()
+    cov = posterior_cov.cpu().numpy()
+    cov = 0.5 * (cov + cov.T)
+    eigenvalues, eigenvectors = np.linalg.eigh(cov)
+    min_eigenvalue = float(eigenvalues.min())
+    if min_eigenvalue < -PSD_ABS_TOL:
+        raise AssertionError(
+            f"Posterior covariance minimum eigenvalue {min_eigenvalue:.3e} "
+            f"falls below {-PSD_ABS_TOL:.1e}"
+        )
+    eigenvalues = np.maximum(eigenvalues, 0.0)
+    factor = eigenvectors @ np.diag(np.sqrt(eigenvalues))
+    rng = np.random.default_rng(subject_seed)
+    standard_normal = rng.standard_normal((N_DRAWS, trial_grid.size))
+    draws_normalized = mean[None, :] + standard_normal @ factor.T
+    draws_raw = draws_normalized * ncurve.y_std + ncurve.y_mean
+    return draws_raw, {
+        "minimum_posterior_covariance_eigenvalue": min_eigenvalue,
+        "posterior_sd_min_raw": float(np.sqrt(eigenvalues.min()) * ncurve.y_std),
+        "posterior_sd_max_raw": float(np.sqrt(eigenvalues.max()) * ncurve.y_std),
+    }
+
+
+def _load_source_artifacts() -> tuple[dict[str, Any], list[dict[str, Any]]]:
+    if not SOURCE_DIR.is_dir():
+        raise FileNotFoundError(f"Missing source artifact directory: {SOURCE_DIR}")
+    aggregate = json.loads((SOURCE_DIR / "aggregate.json").read_text())
+    paths = sorted(SOURCE_DIR.glob("synth_*_sub*_default.json"))
+    if len(paths) != N_SUBJECTS:
+        raise AssertionError(f"Expected {N_SUBJECTS} subject JSONs, found {len(paths)}")
+    subjects = []
+    for path in paths:
+        record = json.loads(path.read_text())
+        record["_source_file"] = path.name
+        subjects.append(record)
+    if int(aggregate["n"]) != len(subjects):
+        raise AssertionError("aggregate.json and subject-file counts disagree")
+    return aggregate, subjects
+
+
+def _aggregate_stored_g(subjects: list[dict[str, Any]]) -> dict[str, Any]:
+    """Summarize stored mean_G values; do not recompute divergences."""
+    first = subjects[0]["bistar_G_diagnostics"]
+    output: dict[str, Any] = {}
+    for config in first:
+        output[config] = {}
+        for metric in first[config]:
+            output[config][metric] = {}
+            for cohort in ("power_truth", "exponential_truth", "all_subjects"):
+                if cohort == "all_subjects":
+                    selected = subjects
+                else:
+                    label = "synth_power" if cohort == "power_truth" else "synth_exponential"
+                    selected = [s for s in subjects if s["dataset_id"] == label]
+                output[config][metric][cohort] = {}
+                for candidate in ("Power", "Exponential"):
+                    values = [
+                        float(s["bistar_G_diagnostics"][config][metric]["per_model"][candidate]["mean_G"])
+                        for s in selected
+                    ]
+                    output[config][metric][cohort][candidate] = _summary(values)
+    return output
+
+
+def _selection_summary(
+    source_aggregate: dict[str, Any], subjects: list[dict[str, Any]]
+) -> dict[str, Any]:
+    """Expose source counts plus probability and known-truth summaries."""
+    bistar: dict[str, Any] = {}
+    for config, metric_records in source_aggregate["bistar"].items():
+        bistar[config] = {}
+        for metric in metric_records:
+            maximum_probabilities = []
+            correct = 0
+            cohort_winners: dict[str, Counter] = {
+                "power_truth": Counter(),
+                "exponential_truth": Counter(),
+            }
+            reference_tau = None
+            for subject in subjects:
+                tau_records = subject["bistar_probs"][config][metric]
+                tau_values = sorted(float(t) for t in tau_records)
+                reference_tau = tau_values[len(tau_values) // 2]
+                probabilities = tau_records[str(reference_tau)]
+                winner = max(probabilities, key=probabilities.get)
+                truth = "Power" if subject["dataset_id"] == "synth_power" else "Exponential"
+                cohort = "power_truth" if truth == "Power" else "exponential_truth"
+                cohort_winners[cohort][winner] += 1
+                correct += int(winner == truth)
+                maximum_probabilities.append(max(float(p) for p in probabilities.values()))
+            bistar[config][metric] = {
+                "reference_tau": float(reference_tau),
+                "winner_counts_all_subjects": source_aggregate["bistar"][config][metric],
+                "winner_counts_by_cohort": {
+                    cohort: dict(counts) for cohort, counts in cohort_winners.items()
+                },
+                "known_truth_correct": correct,
+                "known_truth_accuracy": correct / len(subjects),
+                "maximum_candidate_probability": _summary(maximum_probabilities),
+            }
+
+    bic_by_cohort = {}
+    for cohort, dataset_id, truth in (
+        ("power_truth", "synth_power", "Power"),
+        ("exponential_truth", "synth_exponential", "Exponential"),
+    ):
+        selected = [s for s in subjects if s["dataset_id"] == dataset_id]
+        counts = Counter(s["bic_winner"] for s in selected)
+        bic_by_cohort[cohort] = {
+            "winner_counts": dict(counts),
+            "known_truth_correct": sum(s["bic_winner"] == truth for s in selected),
+            "n": len(selected),
+        }
+
+    robustness = {}
+    for metric, counts in source_aggregate["robustness"].items():
+        total = int(counts["agree"]) + int(counts["disagree"])
+        robustness[metric] = {
+            **counts,
+            "fraction_all_configs_agree": float(counts["agree"]) / total,
+        }
+    return {
+        "bic_winner_counts_all_subjects": source_aggregate["bic"],
+        "bic_by_cohort": bic_by_cohort,
+        "bistar_at_stored_median_tau": bistar,
+        "robustness_across_configs": robustness,
+    }
+
+
+def _plot_regret_curves(
+    regret_curves: dict[str, Any], discrimination_gap: dict[str, Any], path: Path
+) -> None:
+    colors = {"Power": "#315B8A", "Exponential": "#C65A34"}
+    labels = {"power_truth": "Power-generated", "exponential_truth": "Exponential-generated"}
+    fig, axes = plt.subplots(
+        2,
+        2,
+        figsize=(10.2, 6.6),
+        sharex="col",
+        gridspec_kw={"height_ratios": [3.0, 1.25]},
+    )
+    for column, cohort in enumerate(("power_truth", "exponential_truth")):
+        ax = axes[0, column]
+        for candidate in ("Power", "Exponential"):
+            record = regret_curves[cohort][candidate]
+            mean = np.asarray(record["mean"])
+            lower = np.asarray(record["band_q10"])
+            upper = np.asarray(record["band_q90"])
+            ax.plot(TRIAL_GRID, mean, color=colors[candidate], lw=2.2, label=candidate)
+            ax.fill_between(TRIAL_GRID, lower, upper, color=colors[candidate], alpha=0.14)
+        ax.set_title(labels[cohort])
+        ax.set_ylabel("Absolute regret (RT units)")
+        ax.grid(alpha=0.22, linewidth=0.7)
+        ax.legend(frameon=False)
+
+        gap_ax = axes[1, column]
+        gap = np.asarray(discrimination_gap[cohort]["absolute_mean_regret_gap"])
+        gap_ax.plot(TRIAL_GRID, gap, color="#5D3A7A", lw=2.0)
+        gap_ax.fill_between(TRIAL_GRID, 0.0, gap, color="#5D3A7A", alpha=0.14)
+        gap_ax.axvspan(0.5, 5.5, color="#D4A72C", alpha=0.08)
+        gap_ax.set_xlabel("Practice trial")
+        gap_ax.set_ylabel("Gap")
+        gap_ax.set_xticks([1, 5, 10, 15, 20])
+        gap_ax.grid(alpha=0.22, linewidth=0.7)
+
+    fig.suptitle("Candidate regret under stored practice-run GP hyperparameters", y=0.995)
+    fig.text(
+        0.5,
+        0.01,
+        "Lines show pooled subject-draw means; bands show pooled 10th to 90th percentiles.",
+        ha="center",
+        fontsize=9,
+    )
+    fig.tight_layout(rect=(0, 0.035, 1, 0.975))
+    fig.savefig(path, dpi=170, bbox_inches="tight", metadata={"Software": "regret_curves_mopen.py"})
+    plt.close(fig)
+
+
+def _write_readme(results: dict[str, Any], path: Path) -> None:
+    fidelity = results["reconstruction_fidelity"]
+    power = results["headline_regret"]["power_truth"]
+    exponential = results["headline_regret"]["exponential_truth"]
+    readme = f"""# Case D regret curves
+
+Run from the repository root:
+
+```bash
+python experiments/regret_curves_mopen.py
+```
+
+The script reads the 50 subject JSONs in
+`experiments/practice_EvansEtAL/results_hmc/`. Those artifacts came from
+`run.py --demo`: `generate_demo_data(n_subjects=50, seed=42)` produced 25
+power-generated and 25 exponential-generated curves. The practice data
+directory contains no Evans et al. CSVs, so none of these results concern the
+real Evans corpus. The regenerated training series range from {results['provenance']['training_trial_counts']['min']} to {results['provenance']['training_trial_counts']['max']}
+trials; all contain the common trials 1 through 20 used for the regret figure.
+
+## Reconstruction
+
+Candidate predictions come from the stored `fitted_params` through the local
+`candidates.py` classes. Their residual-based BIC log marginal likelihoods
+match the stored values with maximum absolute error {fidelity['bic_log_ml']['max_abs_error']:.3e},
+below the asserted {fidelity['bic_log_ml']['absolute_tolerance']:.1e} tolerance.
+
+`run.py` iterates the default configurations in practitioner, moderate,
+agnostic order. Immediately after each configuration's MAP fit, it writes the
+single `gp_hyperparameters` block only when that block remains empty. The
+stored values therefore record the first successful configuration's MAP point,
+which equals practitioner for all 50 files, even under `results_hmc/`. The
+subject JSONs do not retain the HMC hyperparameter draws. This script rebuilds
+the practitioner RBF GP at that stored point, conditions on the complete
+regenerated series with normalized-space jitter {CONDITIONING_JITTER:.1e}, and
+draws {N_DRAWS} latent posterior functions per subject. It performs no fitting
+and no HMC. Subject `i` uses NumPy seed `{DRAW_SEED_BASE} + i`.
+
+## Estimand and band
+
+The implemented formula equals
+`regret_theta(t) = E_draws[abs(mu_GP(t) - mu_theta(t))]`. A chat-derived Q&A in
+the local limits note mentions a squared difference, but the formal formula and
+the Case D work order specify the absolute difference. The mean at each trial
+pools 25 subjects times 100 draws within a truth cohort. The shaded band spans
+the 10th and 90th percentiles of those same 2,500 subject-draw absolute errors;
+it describes dispersion across subjects and posterior function draws, not a
+confidence interval for the cohort mean.
+
+For the power-generated cohort, {100 * power['first_five_fraction_of_total_gap']:.1f}% of the summed
+20-trial discrimination gap occurs in trials 1 through 5, and the first 10
+trials account for {100 * power['first_ten_fraction_of_total_gap']:.1f}%. The largest gap equals
+{power['peak_gap']:.3f} RT units at trial {power['peak_trial']}. For the exponential-generated cohort,
+the corresponding shares equal {100 * exponential['first_five_fraction_of_total_gap']:.1f}% and
+{100 * exponential['first_ten_fraction_of_total_gap']:.1f}%, and the largest gap equals
+{exponential['peak_gap']:.3f} RT units at trial {exponential['peak_trial']}.
+
+## Stored divergence diagnostics
+
+`results.json` also aggregates the already stored `mean_G` values by prior
+configuration, legacy metric, truth cohort, and candidate. It never recomputes
+G. The practice artifacts predate the W1 metric decision and contain
+`pw_nll`, `pw_mse`, and `pw_hellinger`; they contain no `pw_kl_vcal`.
+`pw_nll` provides the closest available role to the W1 primary, but the script
+does not rename it or introduce a new metric.
+
+Files:
+
+- `results.json`: provenance, fidelity checks, regret curves, discrimination
+  gaps, stored selection summaries, and aggregated stored G magnitudes.
+- `regret_curves.png`: two truth-cohort panels with pooled dispersion bands and
+  per-trial candidate discrimination gaps.
+"""
+    path.write_text(readme)
+
+
+def main() -> None:
+    torch.set_default_dtype(torch.float64)
+    source_aggregate, subject_artifacts = _load_source_artifacts()
+    curves = practice_run.generate_demo_data(n_subjects=N_SUBJECTS, seed=DATA_SEED)
+    curve_by_key = {(c.dataset_id, c.subject_id): c for c in curves}
+    if len(curve_by_key) != N_SUBJECTS:
+        raise AssertionError("Synthetic generator returned duplicate or missing subject keys")
+
+    data_file_count = sum(1 for path in (PRACTICE_DIR / "data").rglob("*") if path.is_file())
+    if data_file_count != 0:
+        raise AssertionError("Practice data directory no longer empty; provenance must be revisited")
+
+    fidelity_rows = []
+    covariance_rows = []
+    regrets: dict[str, dict[str, list[np.ndarray]]] = {
+        "power_truth": {"Power": [], "Exponential": []},
+        "exponential_truth": {"Power": [], "Exponential": []},
+    }
+    observed_lengths = []
+
+    for artifact in subject_artifacts:
+        key = (artifact["dataset_id"], int(artifact["subject_id"]))
+        if key not in curve_by_key:
+            raise AssertionError(f"No regenerated curve for {key}")
+        curve = curve_by_key[key]
+        ncurve = practice_run.normalize(curve)
+        observed_lengths.append(curve.n_trials)
+        if int(artifact["n_trials"]) != curve.n_trials:
+            raise AssertionError(
+                f"Trial-count mismatch for {key}: stored {artifact['n_trials']}, "
+                f"regenerated {curve.n_trials}"
+            )
+        if int(artifact["n_gp_samples"]) != N_DRAWS:
+            raise AssertionError(
+                f"Stored draw-count mismatch for {key}: expected {N_DRAWS}, "
+                f"found {artifact['n_gp_samples']}"
+            )
+        if curve.n_trials < TRIAL_GRID.size or not np.array_equal(
+            curve.trial[: TRIAL_GRID.size], TRIAL_GRID
+        ):
+            raise AssertionError(f"Subject {key} lacks the common first-20-trial grid")
+
+        subject_errors = {}
+        candidate_means = {}
+        for candidate_name in ("Power", "Exponential"):
+            candidate = _candidate_from_params(
+                candidate_name, artifact["fitted_params"][candidate_name]
+            )
+            reconstructed_bic = _stored_bic_from_regenerated_data(
+                candidate, curve.trial, curve.rt
+            )
+            stored_bic = float(artifact["bic_log_ml"][candidate_name])
+            error = abs(reconstructed_bic - stored_bic)
+            subject_errors[candidate_name] = {
+                "stored": stored_bic,
+                "reconstructed": reconstructed_bic,
+                "absolute_error": error,
+            }
+            if error > BIC_ABS_TOL:
+                raise AssertionError(
+                    f"BIC reconstruction failed for {artifact['_source_file']} "
+                    f"{candidate_name}: {error:.3e} exceeds {BIC_ABS_TOL:.1e}"
+                )
+            candidate_means[candidate_name] = candidate.predict(TRIAL_GRID).mean
+
+        function_draws, covariance_check = _conditioned_function_draws(
+            ncurve,
+            artifact["gp_hyperparameters"],
+            TRIAL_GRID,
+            DRAW_SEED_BASE + int(artifact["subject_id"]),
+        )
+        cohort = "power_truth" if artifact["dataset_id"] == "synth_power" else "exponential_truth"
+        for candidate_name in ("Power", "Exponential"):
+            regrets[cohort][candidate_name].append(
+                np.abs(function_draws - candidate_means[candidate_name][None, :])
+            )
+
+        fidelity_rows.append(
+            {
+                "source_file": artifact["_source_file"],
+                "dataset_id": artifact["dataset_id"],
+                "subject_id": int(artifact["subject_id"]),
+                "n_trials": int(curve.n_trials),
+                "candidate_bic": subject_errors,
+            }
+        )
+        covariance_rows.append(
+            {
+                "source_file": artifact["_source_file"],
+                **covariance_check,
+            }
+        )
+
+    all_bic_errors = [
+        row["candidate_bic"][candidate]["absolute_error"]
+        for row in fidelity_rows
+        for candidate in ("Power", "Exponential")
+    ]
+    regret_curves: dict[str, Any] = {}
+    discrimination_gap: dict[str, Any] = {}
+    headline_regret: dict[str, Any] = {}
+    for cohort in ("power_truth", "exponential_truth"):
+        regret_curves[cohort] = {}
+        means = {}
+        for candidate in ("Power", "Exponential"):
+            pooled = np.concatenate(regrets[cohort][candidate], axis=0)
+            if pooled.shape != (25 * N_DRAWS, TRIAL_GRID.size):
+                raise AssertionError(f"Unexpected pooled regret shape for {cohort}/{candidate}")
+            mean = pooled.mean(axis=0)
+            means[candidate] = mean
+            regret_curves[cohort][candidate] = {
+                "n_subjects": 25,
+                "n_draws_per_subject": N_DRAWS,
+                "n_subject_draw_atoms_per_trial": int(pooled.shape[0]),
+                "mean": mean,
+                "band_q10": np.quantile(pooled, 0.10, axis=0),
+                "band_q90": np.quantile(pooled, 0.90, axis=0),
+            }
+        gap = np.abs(means["Power"] - means["Exponential"])
+        total_gap = float(gap.sum())
+        first_five = float(gap[:5].sum())
+        peak_index = int(np.argmax(gap))
+        discrimination_gap[cohort] = {
+            "definition": "Absolute difference between pooled candidate mean regrets at each trial",
+            "absolute_mean_regret_gap": gap,
+        }
+        headline_regret[cohort] = {
+            "peak_trial": int(TRIAL_GRID[peak_index]),
+            "peak_gap": float(gap[peak_index]),
+            "mean_gap_trials_1_to_5": float(gap[:5].mean()),
+            "mean_gap_trials_6_to_20": float(gap[5:].mean()),
+            "first_five_fraction_of_total_gap": first_five / total_gap if total_gap else 0.0,
+            "first_ten_fraction_of_total_gap": float(gap[:10].sum()) / total_gap if total_gap else 0.0,
+            "power_regret_mean_over_20_trials": float(means["Power"].mean()),
+            "exponential_regret_mean_over_20_trials": float(means["Exponential"].mean()),
+        }
+
+    sub25 = next(
+        s
+        for s in subject_artifacts
+        if s["dataset_id"] == "synth_exponential" and int(s["subject_id"]) == 25
+    )
+    sub25_pw_nll = sub25["bistar_G_diagnostics"]["practitioner"]["pw_nll"]["per_model"]
+    results = {
+        "schema_version": 1,
+        "provenance": {
+            "source_artifact_dir": "experiments/practice_EvansEtAL/results_hmc",
+            "source_aggregate": "experiments/practice_EvansEtAL/results_hmc/aggregate.json",
+            "source_artifact_mode": "HMC run, with one stored practitioner MAP hyperparameter point per subject",
+            "synthetic_data_generator": "experiments/practice_EvansEtAL/run.py::generate_demo_data",
+            "synthetic_data_call": "generate_demo_data(n_subjects=50, seed=42)",
+            "real_evans_files_present": False,
+            "n_subjects": len(subject_artifacts),
+            "cohort_sizes": {"power_truth": 25, "exponential_truth": 25},
+            "training_trial_counts": {
+                "min": int(min(observed_lengths)),
+                "max": int(max(observed_lengths)),
+                "unique": sorted(set(int(n) for n in observed_lengths)),
+            },
+            "evaluation_trial_grid": TRIAL_GRID,
+            "data_seed": DATA_SEED,
+            "posterior_function_draw_seed_base": DRAW_SEED_BASE,
+            "posterior_function_draw_seed_rule": "seed = 20260811 + subject_id",
+            "n_draws_per_subject": N_DRAWS,
+            "stored_n_gp_samples_per_subject": N_DRAWS,
+            "formula": "regret_theta(t) = E_draws[abs(mu_GP(t) - mu_theta(t))]",
+            "regret_units": "raw response-time units from the synthetic generator",
+            "band_definition": "At each trial, q10 and q90 pool the 25 subjects by 100 posterior function draws within a truth cohort and describe dispersion rather than confidence limits for the mean.",
+            "summary_definition": "Summary fields use the arithmetic mean, sample standard deviation with ddof=1, and NumPy linear-interpolation quantiles.",
+            "gp_hyperparameters_provenance": "run.py stores gp_hyperparameters once, immediately after the first successful configuration MAP fit. The default loop order starts with practitioner, so all 50 source files carry practitioner MAP values even though results_hmc subsequently runs HMC for GP samples.",
+            "gp_reconstruction": "Exact zero-mean RBF GP conditioning at stored lengthscale, outputscale, and noise; no refit and no hyperparameter sampling; latent posterior function draws exclude fresh observation noise.",
+            "conditioning_jitter_normalized_variance": CONDITIONING_JITTER,
+            "legacy_metric_note": "Stored diagnostics contain pw_nll, pw_mse, and pw_hellinger. They predate W1 and contain no pw_kl_vcal. pw_nll receives closest-role framing without relabeling or recomputation.",
+            "formula_discrepancy_note": "The formal limits-note equation and Case D work order use absolute difference. A chat-derived Q&A in the same note says squared difference; this artifact follows the binding absolute formula.",
+        },
+        "reconstruction_fidelity": {
+            "bic_log_ml": {
+                "check": "Stored fitted-parameter residual structure evaluated on regenerated full subject series",
+                "absolute_tolerance": BIC_ABS_TOL,
+                "n_values_checked": len(all_bic_errors),
+                "max_abs_error": max(all_bic_errors),
+                "mean_abs_error": float(np.mean(all_bic_errors)),
+                "all_passed": all(error <= BIC_ABS_TOL for error in all_bic_errors),
+            },
+            "posterior_covariance": {
+                "negative_eigenvalue_absolute_tolerance": PSD_ABS_TOL,
+                "minimum_eigenvalue_across_subjects": min(
+                    row["minimum_posterior_covariance_eigenvalue"] for row in covariance_rows
+                ),
+                "all_passed": all(
+                    row["minimum_posterior_covariance_eigenvalue"] >= -PSD_ABS_TOL
+                    for row in covariance_rows
+                ),
+            },
+            "per_subject": fidelity_rows,
+        },
+        "trial_grid": TRIAL_GRID,
+        "regret_band": {
+            "lower_quantile": 0.10,
+            "upper_quantile": 0.90,
+            "aggregation": "Pooled across subjects and posterior function draws within each truth cohort",
+        },
+        "regret_curves": regret_curves,
+        "discrimination_gap": discrimination_gap,
+        "headline_regret": headline_regret,
+        "stored_selection_summary": _selection_summary(source_aggregate, subject_artifacts),
+        "stored_mean_G_summaries": _aggregate_stored_g(subject_artifacts),
+        "stored_named_examples": {
+            "synth_exponential_sub25_practitioner_pw_nll": {
+                "source_file": sub25["_source_file"],
+                "Power_mean_G": float(sub25_pw_nll["Power"]["mean_G"]),
+                "Exponential_mean_G": float(sub25_pw_nll["Exponential"]["mean_G"]),
+                "absolute_difference": abs(
+                    float(sub25_pw_nll["Power"]["mean_G"])
+                    - float(sub25_pw_nll["Exponential"]["mean_G"])
+                ),
+            }
+        },
+    }
+
+    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
+    results_path = OUTPUT_DIR / "results.json"
+    readme_path = OUTPUT_DIR / "README.md"
+    figure_path = OUTPUT_DIR / "regret_curves.png"
+    results_path.write_text(
+        json.dumps(_json_ready(results), indent=2, sort_keys=True, allow_nan=False) + "\n"
+    )
+    _plot_regret_curves(
+        _json_ready(regret_curves), _json_ready(discrimination_gap), figure_path
+    )
+    if figure_path.stat().st_size >= FIGURE_SIZE_LIMIT:
+        raise AssertionError(
+            f"Figure size {figure_path.stat().st_size} exceeds {FIGURE_SIZE_LIMIT} bytes"
+        )
+    _write_readme(_json_ready(results), readme_path)
+
+    print(f"Wrote {results_path.relative_to(ROOT)}")
+    print(f"Wrote {readme_path.relative_to(ROOT)}")
+    print(
+        f"Wrote {figure_path.relative_to(ROOT)} "
+        f"({figure_path.stat().st_size} bytes)"
+    )
+    print(
+        "BIC fidelity: "
+        f"max_abs_error={max(all_bic_errors):.3e}, tolerance={BIC_ABS_TOL:.1e}"
+    )
+    for cohort, headline in headline_regret.items():
+        print(
+            f"{cohort}: peak trial {headline['peak_trial']}, "
+            f"peak gap {headline['peak_gap']:.6f}, "
+            f"first-five share {headline['first_five_fraction_of_total_gap']:.3f}"
+        )
+
+
+if __name__ == "__main__":
+    main()
diff --git a/runs/regret_curves_mopen/README.md b/runs/regret_curves_mopen/README.md
new file mode 100644
index 0000000..e5ca01f
--- /dev/null
+++ b/runs/regret_curves_mopen/README.md
@@ -0,0 +1,68 @@
+# Case D regret curves
+
+Run from the repository root:
+
+```bash
+python experiments/regret_curves_mopen.py
+```
+
+The script reads the 50 subject JSONs in
+`experiments/practice_EvansEtAL/results_hmc/`. Those artifacts came from
+`run.py --demo`: `generate_demo_data(n_subjects=50, seed=42)` produced 25
+power-generated and 25 exponential-generated curves. The practice data
+directory contains no Evans et al. CSVs, so none of these results concern the
+real Evans corpus. The regenerated training series range from 20 to 79
+trials; all contain the common trials 1 through 20 used for the regret figure.
+
+## Reconstruction
+
+Candidate predictions come from the stored `fitted_params` through the local
+`candidates.py` classes. Their residual-based BIC log marginal likelihoods
+match the stored values with maximum absolute error 5.684e-14,
+below the asserted 1.0e-08 tolerance.
+
+`run.py` iterates the default configurations in practitioner, moderate,
+agnostic order. Immediately after each configuration's MAP fit, it writes the
+single `gp_hyperparameters` block only when that block remains empty. The
+stored values therefore record the first successful configuration's MAP point,
+which equals practitioner for all 50 files, even under `results_hmc/`. The
+subject JSONs do not retain the HMC hyperparameter draws. This script rebuilds
+the practitioner RBF GP at that stored point, conditions on the complete
+regenerated series with normalized-space jitter 1.0e-06, and
+draws 100 latent posterior functions per subject. It performs no fitting
+and no HMC. Subject `i` uses NumPy seed `20260811 + i`.
+
+## Estimand and band
+
+The implemented formula equals
+`regret_theta(t) = E_draws[abs(mu_GP(t) - mu_theta(t))]`. A chat-derived Q&A in
+the local limits note mentions a squared difference, but the formal formula and
+the Case D work order specify the absolute difference. The mean at each trial
+pools 25 subjects times 100 draws within a truth cohort. The shaded band spans
+the 10th and 90th percentiles of those same 2,500 subject-draw absolute errors;
+it describes dispersion across subjects and posterior function draws, not a
+confidence interval for the cohort mean.
+
+For the power-generated cohort, 70.0% of the summed
+20-trial discrimination gap occurs in trials 1 through 5, and the first 10
+trials account for 82.2%. The largest gap equals
+33.782 RT units at trial 1. For the exponential-generated cohort,
+the corresponding shares equal 41.7% and
+77.7%, and the largest gap equals
+91.452 RT units at trial 1.
+
+## Stored divergence diagnostics
+
+`results.json` also aggregates the already stored `mean_G` values by prior
+configuration, legacy metric, truth cohort, and candidate. It never recomputes
+G. The practice artifacts predate the W1 metric decision and contain
+`pw_nll`, `pw_mse`, and `pw_hellinger`; they contain no `pw_kl_vcal`.
+`pw_nll` provides the closest available role to the W1 primary, but the script
+does not rename it or introduce a new metric.
+
+Files:
+
+- `results.json`: provenance, fidelity checks, regret curves, discrimination
+  gaps, stored selection summaries, and aggregated stored G magnitudes.
+- `regret_curves.png`: two truth-cohort panels with pooled dispersion bands and
+  per-trial candidate discrimination gaps.

