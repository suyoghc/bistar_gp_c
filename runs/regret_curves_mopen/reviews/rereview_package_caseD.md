RE-REVIEW ROUND (HANDOFF §4 rule 4) — Case D fix pass 1, changed hunks only.
Branch paper/case-d-mopen; fix commit c57a70e on top of reviewed tip a4b92c0.
Task: for EACH of YOUR OWN previously raised findings that entered the fix queue (per the
dispatch note), judge from the changed hunks whether the fix resolves it. Findings REJECTED
in cross-check (DO2, DO3, DO6, DO7, DO10) were deliberately NOT implemented — do not
re-litigate them. Output per finding: 'REREVIEW-<ID>: RESOLVED' or 'REREVIEW-<ID>:
NOT-RESOLVED' plus 2-4 evidence lines. Additionally report any NEW defect INTRODUCED BY the
changed hunks (hunks only; no scope expansion). Round-1 record:
runs/regret_curves_mopen/reviews/VERDICTS.md.

=== IMPLEMENTER FIX REPORT ===
Implemented all seven Case D fixes.

Files touched: [experiment script](/Users/sc8918/Documents/GitHub/bistar_gp_c/experiments/regret_curves_mopen.py), [results.json](/Users/sc8918/Documents/GitHub/bistar_gp_c/runs/regret_curves_mopen/results.json), [README](/Users/sc8918/Documents/GitHub/bistar_gp_c/runs/regret_curves_mopen/README.md), [figure](/Users/sc8918/Documents/GitHub/bistar_gp_c/runs/regret_curves_mopen/regret_curves.png), [paper section](/Users/sc8918/Documents/GitHub/bistar_gp_c/docs/paper-sie-jmp/06-case-D-mopen-calibration.md), and only [D64](/Users/sc8918/Documents/GitHub/bistar_gp_c/Notes/DECISIONS.md:6014).

- FIX-D1: Removed the W1-analogue and weak/sharp claims; added the exact affine identity, scale non-invariance, full tau diagnostics, and tau-free `pw_nll` aggregates.
- FIX-D2: Relabeled the latent-draw quantity and added the posterior-mean plug-in to JSON, prose, tables, and dashed figure overlays.
- FIX-D3: Replaced causal scaffold attribution with descriptive localization and explicit source non-identifiability.
- FIX-D4: Recorded the full-series 50-point G domain versus trials 1–20, including the 24.4% longest-series span.
- FIX-D5: Moved configuration-agreement counts outside the Power/Exponential table.
- FIX-D6: Removed both dead/mislabeled posterior-SD fields.
- FIX-D7: Added RT units to deviation-table headers.

`pw_nll` true-family raw-draw wins:

| Config | Power truth | Exponential truth |
|---|---:|---:|
| Practitioner | 39.0% (974/2,500; 9/25 majorities) | 98.7% (2,467/2,500; 25/25) |
| Moderate | 39.9% (998/2,500; 8/25; one exact tie) | 94.6% (2,364/2,500; 25/25) |
| Agnostic | 41.5% (1,037/2,500; 9/25) | 92.1% (2,302/2,500; 25/25) |

Headline deviations, Power candidate / Exponential candidate:

- MAP-conditional posterior expected absolute deviation: Power truth 21.383 / 20.681; Exponential truth 35.587 / 14.855.
- Posterior-mean plug-in: Power truth 17.638 / 17.325; Exponential truth 33.901 / 10.764.

Final rerun: exit code 0, 3 seconds. Deterministic output hashes passed. PNG: 182,245 bytes.

`experiments/practice_EvansEtAL/` remained byte-untouched; inventory SHA-1 stayed `528fea7d955841cf496883df4f96bb85b8357b4a`. Rejected fixes were not implemented. No git operations, new dependencies, HMC, or other deviations.
=== FIX DIFF STAT ===
 Notes/DECISIONS.md                                |  100 +-
 docs/paper-sie-jmp/06-case-D-mopen-calibration.md |  181 ++-
 experiments/regret_curves_mopen.py                |  533 ++++++-
 runs/regret_curves_mopen/README.md                |   79 +-
 runs/regret_curves_mopen/regret_curves.png        |  Bin 159881 -> 182245 bytes
 runs/regret_curves_mopen/results.json             | 1687 ++++++++++++++++++++-
 6 files changed, 2368 insertions(+), 212 deletions(-)

=== FIX DIFF (results.json and PNG excluded; regenerated JSON abridged below) ===
diff --git a/Notes/DECISIONS.md b/Notes/DECISIONS.md
index bfaca79..3d33d86 100644
--- a/Notes/DECISIONS.md
+++ b/Notes/DECISIONS.md
@@ -5717,12 +5717,12 @@ second correction pass, restoring/applying/dropping stash `5280d1e1…`, D59 wor
 or figure changes, poster-repository work, the captions themselves, Della contact, new
 computation, holdout access, BMS*, Ready, or merge.
 
-## D64: Case D synthetic distinguishability calibration and regret localization — 2026-08-11
+## D64: Case D synthetic distinguishability calibration and MAP-conditional deviation localization — 2026-08-11
 
-**Problem:** Case D needed per-trial regret curves and an honest M-open
+**Problem:** Case D needed per-trial deviation curves and an honest M-open
 calibration argument from the existing practice-law artifacts, without rerunning
 `experiments/practice_EvansEtAL/run.py`, changing its artifacts, or starting new
-HMC. Inventory found no regret implementation and no files under the practice
+HMC. Inventory found no deviation implementation and no files under the practice
 data directory. The 50 `results_hmc/` subject files therefore concern only
 `generate_demo_data(n_subjects=50, seed=42)`, with 25 power-generated and 25
 exponential-generated series. Both generating forms appear in the fitted pair,
@@ -5731,24 +5731,34 @@ correct-specification reference levels for stored divergence magnitudes, not a
 real-Evans-data analysis or a direct M-open misspecification finding. Direct
 inspection also corrected one work-order shorthand: the stored and regenerated
 training series range from 20 to 79 trials rather than containing 20 trials
-each; every series contains the common trials 1 through 20 used in the figure.
+each. Stored practice G values use a 50-point uniform grid over every subject's
+full series, while the reconstructed curves use integer trials 1 through 20.
+For the longest subjects, those trials span 24.4% of the full continuous trial
+range, so linkage to the aggregate G results stays within the shared early
+region.
 
 **Decision:** Added `experiments/regret_curves_mopen.py`, which writes
 `runs/regret_curves_mopen/{results.json,README.md,regret_curves.png}`. It prefers
 the read-only `experiments/practice_EvansEtAL/results_hmc/` directory, imports
 `generate_demo_data` and the Power and Exponential classes from the practice
 experiment rather than copying them, and evaluates stored fitted parameters on
-the regenerated full subject series before any regret calculation. Data seed
+the regenerated full subject series before any deviation calculation. Data seed
 42 regenerates the observations. Subject `i` receives posterior-function seed
 `20260811 + i`, with 100 latent conditional GP draws and no added observation
 noise. The common evaluation grid contains trials 1 through 20. At each trial,
-the curve reports
-`regret_theta(t) = E_draws[abs(mu_GP(t) - mu_theta(t))]`; its band spans the
-pooled 10th and 90th percentiles across 25 subjects times 100 draws within each
-truth cohort, so it describes dispersion rather than a confidence interval for
-the mean. The formal limits-note equation and the Case D work order specify the
-absolute difference; a chat-derived Q&A in the same note says squared
-difference, and the binding absolute formula takes precedence.
+the solid curve reports the MAP-conditional posterior expected absolute
+deviation of the latent function,
+`E_{f|y,eta_hat}[abs(f(t) - mu_theta(t))]`; its band spans the pooled 10th and
+90th percentiles across 25 subjects times 100 draws within each truth cohort,
+so it describes dispersion rather than a confidence interval for the mean. A
+dashed overlay reports the mean-based plug-in
+`abs(E[f(t)|y,eta_hat] - mu_theta(t))`, aggregated over the same 25 subjects.
+Jensen's inequality makes the latent-draw deviation no smaller per subject,
+candidate, and trial; unequal inflation changes the candidate gap
+trial-dependently, which motivates reporting both estimands.
+The formal limits-note equation and the Case D work order specify an absolute
+difference; a chat-derived Q&A in the same note says squared difference, and
+the binding absolute form takes precedence.
 
 `run.py` loops through practitioner, moderate, and agnostic configurations. It
 sets the single `gp_hyperparameters` block only while that block remains empty,
@@ -5756,13 +5766,23 @@ immediately after a successful configuration MAP fit and before the HMC branch.
 All 50 source files contain every configuration's diagnostics, so their stored
 lengthscale, outputscale, and noise values come from the first, practitioner MAP
 fit even in `results_hmc/`. The subject JSONs do not retain HMC hyperparameter
-draws. The regret script therefore rebuilds the practitioner RBF GP at that
+draws. The deviation script therefore rebuilds the practitioner RBF GP at that
 stored point and performs exact conditioning with normalized-variance jitter
 `1e-6`; it neither refits hyperparameters nor reconstructs HMC trajectories.
+Because the limits-note target averages posterior mean functions over
+hyperparameter draws, neither MAP-conditional reconstruction equals that
+target. Reporting both the latent-draw expected deviation and the posterior-mean
+plug-in makes the mean-versus-draw substitution explicit next to the MAP-versus-
+HMC limitation.
+
 The stored `bistar_G_diagnostics` values are aggregated without recomputing G.
 Those artifacts predate W1 and contain `pw_nll`, `pw_mse`, and
-`pw_hellinger`, not `pw_kl_vcal`; `pw_nll` receives closest-role framing but no
-renaming. `docs/paper-sie-jmp/06-case-D-mopen-calibration.md` states these
+`pw_hellinger`, not `pw_kl_vcal`. Legacy `pw_nll` weights by candidate fitted
+noise variance, while `pw_kl_vcal` weights by GP variance; `pw_mse` lies closer
+on that axis. The script verifies the candidate-specific affine identity between
+stored `pw_nll` and `pw_mse`, records the full temperature-scale diagnostic, and
+aggregates the tau-free `pw_nll` `raw_draw_wins` statistic for all three
+configurations. `docs/paper-sie-jmp/06-case-D-mopen-calibration.md` states these
 limits, separates F1 scaffold representability from F2 intrinsic mimicry, and
 positions the result against Navarro, Pitt, and Myung (2004), Evans et al.
 (2018), and Averell and Heathcote (2011).
@@ -5772,7 +5792,7 @@ order prefers the HMC-mode artifacts. `results_diag/` and
 `results_hierarchical/` were not consulted because no documented need emerged.
 Rerunning the practice scripts, refitting candidate or GP parameters, and
 starting HMC were rejected by scope and because the required reconstruction
-uses frozen artifacts. A squared regret was rejected because it conflicts with
+uses frozen artifacts. A squared deviation was rejected because it conflicts with
 the binding formula. A normalized 20-point refit was rejected in favor of
 conditioning on every regenerated observation and evaluating only the common
 20-trial grid. The optional transform-space E8b module was deferred by the
@@ -5786,18 +5806,19 @@ mean absolute errors equal `5.684e-14` and `5.116e-15`, below the asserted
 `1e-8` tolerance. The minimum posterior-covariance eigenvalue across subjects
 equals `-2.400e-15`, within the `1e-8` numerical PSD tolerance. Two consecutive
 runs produced identical SHA-1 values for all three outputs. The figure occupies
-159,881 bytes, below 2 MB.
-
-For power-generated curves, mean regret across 20 trials equals 21.383 for
-Power and 20.681 for Exponential. The gap peaks at 33.782 on trial 1; trials 1
-through 5 account for 70.0% of its summed gap and trials 1 through 10 account
-for 82.2%. For exponential-generated curves, the corresponding means equal
-35.587 and 14.855, the trial-1 peak equals 91.452, and the two early shares
-equal 41.7% and 77.7%. The signal therefore concentrates early without
-vanishing after the first few exponential-cohort trials. The power cohort also
-shows the wrong exponential candidate closer at the largest-gap trial, which
-localizes the stored method's asymmetric recovery failure rather than hiding it
-behind a winner count.
+182,245 bytes, below 2 MB.
+
+For power-generated curves, the MAP-conditional posterior expected absolute
+deviation averages 21.383 for Power and 20.681 for Exponential across 20 trials;
+the mean-based plug-in averages 17.638 and 17.325. Their trial-1 peak gaps equal
+33.782 and 34.052. For exponential-generated curves, the corresponding
+MAP-conditional means equal 35.587 and 14.855, and the plug-in means equal
+33.901 and 10.764; their trial-1 peak gaps equal 91.452 and 92.890. The
+MAP-conditional early-gap shares remain 70.0% and 82.2% through trials 5 and 10
+under power truth, versus 41.7% and 77.7% under exponential truth. The plug-in
+shares equal 63.3% and 74.0%, versus 40.0% and 75.0%. Both estimands therefore
+give a consistent descriptive localization under the stored practitioner-MAP
+scaffold.
 
 The aggregated stored practitioner `pw_nll` means equal 4.799 for Power and
 4.775 for Exponential under power truth, versus 5.003 and 4.582 under
@@ -5805,10 +5826,25 @@ exponential truth. Synthetic exponential subject 25 supplies a particularly
 clear mimicry example: 4.881 for Power and 4.852 for Exponential, an absolute
 difference of 0.029. These known-truth levels show what a future absolute
 inadequacy calibration must condition on; Case D sets no rejection threshold.
-The `pw_nll` soft read remains weak despite stable winner labels: median maximum
-candidate probabilities equal 0.522, 0.522, and 0.518 for practitioner,
-moderate, and agnostic. The section confines its warranted-decline claim to
-that legacy closest-role metric because `pw_mse` behaves much more sharply.
+Every one of the 300 stored `mean_G` pairs satisfies
+`pw_nll = 0.5*log(2*pi*sigma_theta^2) + pw_mse/(2*sigma_theta^2)`, with maximum
+absolute error `1.78e-15`; the divisor `2*sigma_theta^2` ranges from 743 to
+7,161. Shared-temperature probability magnitudes therefore do not support a
+cross-metric confidence contrast. No temperature on the stored 15-point grid
+closes the gap: the power-cohort `pw_nll` medians peak around the review's
+`~0.573` summary at `tau=0.1`, while the all-subject practitioner `pw_mse`
+median remains 0.987 at `tau=31.6`. On the tau-free practitioner `pw_nll`
+diagnostic, the true family wins 974/2,500 draws (39.0%) under power truth, with
+9/25 subject majorities, versus 2,467/2,500 (98.7%) and 25/25 under exponential
+truth. Moderate gives 39.9% with 8/25 versus 94.6% with 25/25; agnostic gives
+41.5% with 9/25 versus 92.1% with 25/25.
+
+Exactly one practitioner-MAP RBF reconstruction appears in this branch, and all
+three stored configurations use RBF kernels. The early-trial localization
+cannot identify whether the `pw_nll` asymmetry comes from F1 representability,
+F2 mimicry, metric behavior, or sampling noise. It remains consistent with the
+tau-free asymmetry only within the shared early-trial region.
+
 The bytewise inventory hash for every file under
 `experiments/practice_EvansEtAL/` remained
 `528fea7d955841cf496883df4f96bb85b8357b4a` before and after execution.
diff --git a/docs/paper-sie-jmp/06-case-D-mopen-calibration.md b/docs/paper-sie-jmp/06-case-D-mopen-calibration.md
index f07b4ed..8d9ad38 100644
--- a/docs/paper-sie-jmp/06-case-D-mopen-calibration.md
+++ b/docs/paper-sie-jmp/06-case-D-mopen-calibration.md
@@ -14,12 +14,17 @@ data directory contains no Evans et al. observations. `run.py` instead generated
 50 synthetic series with seed 42, divided equally between power and exponential
 truth. Each subject's generating form appears among the two fitted candidates.
 The source artifacts record between 20 and 79 observations per subject, and the
-regret analysis uses their common first 20 trials. We use these data to study
-distinguishability and mimicry and to establish correct-specification reference
-levels for (G); we do not infer how either candidate fits the real Evans
-corpus.[^case-d-empirical] Evans et al.'s broader candidate discussion motivates
-the context, while every result below concerns only Power and Exponential, the
-pair retained in the stored fits.[^case-d-evans]
+stored practice (G) values were computed on 50 uniformly spaced points spanning
+each subject's full series. The reconstructed deviation curves instead cover
+integer trials 1 through 20. For the longest subjects, that early grid spans
+19/78, or 24.4%, of the full continuous trial range. Any linkage between those
+curves and the stored aggregate comparisons therefore applies only to their
+shared early-trial region. We use these data to study distinguishability and
+mimicry and to establish correct-specification reference levels for (G); we do
+not infer how either candidate fits the real Evans corpus.[^case-d-empirical]
+Evans et al.'s broader candidate discussion motivates the context, while every
+result below concerns only Power and Exponential, the pair retained in the
+stored fits.[^case-d-evans]
 
 ## Two failure geometries
 
@@ -56,20 +61,41 @@ pointwise metric:
 | practitioner | 22 / 28 | 6 / 44 | 10 / 40 |
 | moderate | 32 / 18 | 7 / 43 | 12 / 38 |
 | agnostic | 27 / 23 | 7 / 43 | 12 / 38 |
-| all configurations agree | 39 / 50 | 49 / 50 | 48 / 50 |
+
+Across the 50 subjects, all three configurations select the same winner for 39
+subjects under `pw_hellinger`, 49 under `pw_mse`, and 48 under `pw_nll`.
 
 These practice artifacts predate W1. They contain `pw_nll`, `pw_mse`, and
 `pw_hellinger`, not the manuscript's primary `pw_kl_vcal`; no new metric was
 authorized for Case D, and we do not relabel the stored quantities.
-`pw_nll` comes closest to the W1 primary role because it combines mean mismatch
-with pointwise variance calibration. Under `pw_nll`, known-truth accuracy equals
-35 of 50 for practitioner and 37 of 50 for both moderate and agnostic. More
-importantly for a decline, median winning probabilities equal only 0.522, 0.522,
-and 0.518 across those configurations. Winner stability therefore coexists with
-weak pairwise separation and a systematic preference for Exponential. The
-much sharper `pw_mse` decisions prevent a metric-general claim that BMS*
-declined. The calibrated claim applies to the `pw_nll` read and its associated
-regret geometry.[^case-d-empirical]
+Legacy `pw_nll` weights squared error by the candidate's fitted noise variance,
+whereas `pw_kl_vcal` weights it by the GP variance. On that weighting axis,
+`pw_mse` lies closer to the manuscript primary.
+
+For all 300 stored configuration-by-subject-by-candidate `mean_G` pairs,
+`pw_nll = 0.5 log(2 pi sigma_theta^2) + pw_mse/(2 sigma_theta^2)` to maximum
+absolute error $1.78 \times 10^{-15}$. Thus `pw_nll` and `pw_mse` apply a
+candidate-specific affine map to the same squared-error statistic; the divisor
+`2 sigma_theta^2` ranges from 743 to 7,161, approximately 750 to 7,150. BMS*
+scores `exp(-G/tau)` at a shared $\tau$, so soft-transfer probability magnitudes
+are not comparable across metrics on different scales. No value on the stored
+15-point grid removes the gap: the power-cohort `pw_nll` medians peak around
+0.57 (approximately 0.573 in the review summary) at $\tau=0.1$, while the
+all-subject practitioner `pw_mse` median remains 0.987 at $\tau=31.6$.[^case-d-empirical]
+
+The tau-free, scale-invariant `pw_nll` `raw_draw_wins` diagnostic carries the
+asymmetry instead:
+
+| GP configuration | Power truth: true-family draw wins / subject majorities | Exponential truth: true-family draw wins / subject majorities |
+|---|---:|---:|
+| practitioner | 39.0% / 9 of 25 | 98.7% / 25 of 25 |
+| moderate | 39.9% / 8 of 25 | 94.6% / 25 of 25 |
+| agnostic | 41.5% / 9 of 25 | 92.1% / 25 of 25 |
+
+These `pw_nll` counts describe how often the known-truth candidate attains the
+smaller raw divergence on the 100 stored GP draws per subject. They support a
+metric-specific asymmetric-recovery statement without interpreting a
+temperature-dependent probability magnitude.[^case-d-empirical]
 
 ## Absolute divergence magnitudes
 
@@ -84,69 +110,95 @@ script aggregates them without recomputing (G).
 | moderate | 4.858 | 4.830 | 5.045 | 4.688 |
 | agnostic | 4.834 | 4.811 | 5.045 | 4.715 |
 
-The power-generated rows exhibit the mimicry signature: both magnitudes nearly
-coincide, and the wrong exponential candidate has the slightly smaller cohort
-mean. The exponential-generated rows separate more clearly and favor the known
-truth. At synthetic exponential subject 25, the practitioner `pw_nll` means
+Within these `pw_nll` summaries, the power-generated rows exhibit the mimicry
+signature: both magnitudes nearly coincide, and the wrong exponential candidate
+has the slightly smaller cohort mean. The `pw_nll` exponential-generated rows
+separate more clearly and favor the known truth. At synthetic exponential
+subject 25, the practitioner `pw_nll` means
 equal 4.881 for Power and 4.852 for Exponential, an absolute difference of
 0.029. A ranking reports only Exponential; the paired magnitudes show how
 little separates the candidates for that subject.[^case-d-empirical]
 
-The table also blocks an overstatement about M-open inadequacy. Correctly
-specified candidates can produce mean (G) values from 4.582 to 4.858 in these
-cohort summaries, while a wrong but mimicking candidate can occupy much of the
-same scale. A future inadequacy rule must compare an observed magnitude with a
+The `pw_nll` table also blocks an overstatement about M-open inadequacy.
+Correctly specified candidates can produce `pw_nll` mean (G) values from 4.582
+to 4.858 in these cohort summaries, while a wrong but mimicking candidate can
+occupy much of the same scale. A future inadequacy rule must compare an observed
+magnitude with a
 reference distribution under correct specification, conditional on metric,
 configuration, sample size, and noise. These known-truth `mean_G` distributions
 supply the kind of calibration material such a rule needs, but Case D does not
 set a rejection threshold.
 
-## Regret localizes the comparison
+## MAP-conditional deviation localizes the comparison
 
 The subject JSONs omit GP curves and draws. The new reconstruction regenerates
 the synthetic observations, verifies each stored candidate fit through its BIC
 residual structure, rebuilds an exact GP at the stored hyperparameters, and
-draws 100 seeded latent posterior functions per subject. No refitting and no
-new HMC occur. For candidate θ and trial (t), the reported estimand follows the
-binding absolute-difference formula
+computes its latent posterior mean plus 100 seeded latent posterior functions
+per subject. No refitting and no new HMC occur.
+
+One provenance and estimand limitation matters. `run.py` writes one
+`gp_hyperparameters` block immediately after the first successful configuration
+MAP fit. With the default order, all 50 source files record the practitioner MAP
+point even though `results_hmc/` subsequently uses HMC samples for its stored
+BMS* diagnostics. The JSONs do not retain those HMC hyperparameter draws, so
+neither reconstruction below averages posterior mean functions over
+hyperparameter draws as in the limits-note formula. The solid curves instead
+report the MAP-conditional posterior expected absolute deviation of the latent
+function,
 
 \[
-\operatorname{regret}_{\theta}(t)
-= \mathbb{E}_{\mathrm{draws}}
-  \left[\left|\mu_{\mathrm{GP}}(t)-\mu_{\theta}(t)\right|\right].
+R^{\mathrm{draw}}_{\theta}(t)
+= \mathbb{E}_{f\mid y,\hat{\eta}}
+  \left[\left|f(t)-\mu_{\theta}(t)\right|\right],
 \]
 
-Each line pools 25 subjects and 100 draws within a truth cohort. The shaded band
+and the dashed curves report the mean-based plug-in at the same MAP point,
+
+\[
+R^{\mathrm{mean}}_{\theta}(t)
+= \left|\mathbb{E}\!\left[f(t)\mid y,\hat{\eta}\right]
+  -\mu_{\theta}(t)\right|.
+\]
+
+Jensen's inequality makes $R^{\mathrm{draw}}_{\theta}(t)$ no smaller than
+$R^{\mathrm{mean}}_{\theta}(t)$ for each subject, candidate, and trial. Latent
+posterior spread therefore inflates candidate deviations and generally
+compresses their gap by a trial-dependent amount, so the two estimands should
+not be substituted silently.
+
+Each solid line pools 25 subjects and 100 draws within a truth cohort. Its band
 spans the pooled 10th and 90th percentiles of the resulting 2,500 absolute
 errors at each trial; it describes subject-and-draw dispersion, not uncertainty
-in the cohort mean.
-
-![Regret curves for the two synthetic truth cohorts](../../runs/regret_curves_mopen/regret_curves.png)
-
-| Truth cohort | Mean Power regret | Mean Exponential regret | Peak discrimination gap | Gap in trials 1–5 | Gap in trials 1–10 |
-|---|---:|---:|---:|---:|---:|
-| Power | 21.383 | 20.681 | 33.782 at trial 1 | 70.0% | 82.2% |
-| Exponential | 35.587 | 14.855 | 91.452 at trial 1 | 41.7% | 77.7% |
-
-The discrimination profile concentrates toward the beginning but does not
-collapse to only the first few trials. For power-generated curves, trial 1
-produces regrets of 116.333 for Power and 82.551 for Exponential, so the GP
-reconstruction favors the wrong family precisely where the largest gap occurs.
-The later gap rapidly contracts. For exponential-generated curves, trial 1
-produces regrets of 131.415 for Power and 39.963 for Exponential, and appreciable
-separation continues through the first half of the grid. Regret therefore
-explains both sides of the aggregate result: strong localization can support
-correct recovery, as in the exponential cohort, or expose a scaffold-induced
-preference for the wrong mimicking curve, as in the power cohort.[^case-d-empirical]
-
-One provenance limitation matters. `run.py` writes one
-`gp_hyperparameters` block immediately after the first successful configuration
-MAP fit. With the default order, all 50 source files record the practitioner MAP
-point even though `results_hmc/` subsequently uses HMC samples for its stored
-BMS* diagnostics. The JSONs do not retain those HMC hyperparameter draws. The
-regret curves consequently condition at the stored practitioner MAP point and
-sample functions from that exact conditional GP; they should not be described
-as reconstructed HMC trajectories.
+in the cohort mean. Each dashed line averages the 25 subject-level plug-in
+deviations; corresponding subject quantiles remain in `results.json`.
+
+![MAP-conditional deviation curves for the two synthetic truth cohorts](../../runs/regret_curves_mopen/regret_curves.png)
+
+| Estimand | Truth cohort | Mean Power deviation (RT units) | Mean Exponential deviation (RT units) | Peak gap (RT units) | Gap in trials 1–5 | Gap in trials 1–10 |
+|---|---|---:|---:|---:|---:|---:|
+| MAP-conditional posterior expected absolute deviation | Power | 21.383 | 20.681 | 33.782 at trial 1 | 70.0% | 82.2% |
+| Posterior-mean plug-in | Power | 17.638 | 17.325 | 34.052 at trial 1 | 63.3% | 74.0% |
+| MAP-conditional posterior expected absolute deviation | Exponential | 35.587 | 14.855 | 91.452 at trial 1 | 41.7% | 77.7% |
+| Posterior-mean plug-in | Exponential | 33.901 | 10.764 | 92.890 at trial 1 | 40.0% | 75.0% |
+
+Both profiles concentrate toward the beginning but do not collapse to only the
+first few trials. For the MAP-conditional posterior expected absolute deviation
+under power truth, trial 1 produces 116.333 RT units for Power and 82.551 for
+Exponential, with the wrong family closer where the largest gap occurs. Under
+exponential truth, the corresponding values equal 131.415 and 39.963, and
+appreciable separation continues through the first half of the grid. The two
+estimands therefore show a consistent descriptive localization under the
+stored practitioner-MAP scaffold. Within the shared early-trial region, that
+localization agrees with the asymmetric practitioner `pw_nll` raw-draw result;
+it cannot explain the portion of the stored aggregate comparison evaluated
+later in each subject's full series.[^case-d-empirical]
+
+The branch contains exactly one practitioner-MAP RBF reconstruction, and all
+three stored configurations use the RBF family. These artifacts cannot identify
+whether the localized `pw_nll` recovery asymmetry originates in F1
+representability, F2 mimicry, metric behavior, or sampling noise. That
+non-identifiability matches the F1/F2-agnostic interpretation above.
 
 ## Positioning and optional extension
 
@@ -155,10 +207,11 @@ forgetting can change between individual-level and population-level analyses.
 Their result warns against treating one comparison procedure or aggregation
 level as a resolution of the functional-form debate.[^case-d-averell] Case D
 supports a narrower conclusion. On synthetic practice curves, the legacy
-`pw_nll` comparison expresses weak confidence, its raw divergence magnitudes
-provide correct-specification reference levels, and regret identifies where
-the scaffold helps or misleads. Nothing here adjudicates the real practice data
-or the forgetting literature.
+`pw_nll` raw-draw results show asymmetric recovery, its raw divergence
+magnitudes provide correct-specification reference levels, and both
+MAP-conditional deviation estimands descriptively localize part of that
+asymmetry in the shared early-trial region. Nothing here identifies its cause or
+adjudicates the real practice data or the forgetting literature.
 
 > **[E8B-PLACEHOLDER] UNBUILT OPTIONAL MODULE.** The proposed extension would
 > refit in semi-log and log-log spaces, with an explicit lognormal or
diff --git a/experiments/regret_curves_mopen.py b/experiments/regret_curves_mopen.py
index fa88948..32ab1cd 100644
--- a/experiments/regret_curves_mopen.py
+++ b/experiments/regret_curves_mopen.py
@@ -1,11 +1,11 @@
 #!/usr/bin/env python3
-"""Reconstruct Case D regret curves from the frozen practice artifacts.
+"""Reconstruct Case D deviation curves from the frozen practice artifacts.
 
 The script does not fit candidates, optimize GP hyperparameters, or run HMC.
 It regenerates the seeded synthetic observations, verifies the stored BIC
 values from the stored candidate parameters, conditions an exact GP at the
-stored practitioner MAP hyperparameters, and draws latent functions on the
-common first-20-trial grid.
+stored practitioner MAP hyperparameters, and evaluates two absolute-deviation
+estimands on the common first-20-trial grid.
 """
 
 from __future__ import annotations
@@ -112,13 +112,13 @@ def _stored_bic_from_regenerated_data(
     return float(log_likelihood - 0.5 * k * np.log(n))
 
 
-def _conditioned_function_draws(
+def _conditioned_latent_posterior(
     ncurve,
     hp: dict[str, float],
     trial_grid: np.ndarray,
     subject_seed: int,
-) -> tuple[np.ndarray, dict[str, float]]:
-    """Draw latent GP functions after exact conditioning at stored MAP HPs."""
+) -> tuple[np.ndarray, np.ndarray, dict[str, float]]:
+    """Return latent draws and mean after conditioning at stored MAP HPs."""
     x_train = torch.as_tensor(ncurve.x, dtype=torch.float64)
     y_train = torch.as_tensor(ncurve.y, dtype=torch.float64)
     x_eval_norm = (trial_grid - ncurve.x_min) / (ncurve.x_max - ncurve.x_min)
@@ -165,10 +165,9 @@ def _conditioned_function_draws(
     standard_normal = rng.standard_normal((N_DRAWS, trial_grid.size))
     draws_normalized = mean[None, :] + standard_normal @ factor.T
     draws_raw = draws_normalized * ncurve.y_std + ncurve.y_mean
-    return draws_raw, {
+    posterior_mean_raw = mean * ncurve.y_std + ncurve.y_mean
+    return draws_raw, posterior_mean_raw, {
         "minimum_posterior_covariance_eigenvalue": min_eigenvalue,
-        "posterior_sd_min_raw": float(np.sqrt(eigenvalues.min()) * ncurve.y_std),
-        "posterior_sd_max_raw": float(np.sqrt(eigenvalues.max()) * ncurve.y_std),
     }
 
 
@@ -213,6 +212,148 @@ def _aggregate_stored_g(subjects: list[dict[str, Any]]) -> dict[str, Any]:
     return output
 
 
+def _aggregate_truth_raw_draw_wins(
+    subjects: list[dict[str, Any]], metric: str = "pw_nll"
+) -> dict[str, Any]:
+    """Aggregate tau-free wins by the known-truth candidate."""
+    first = subjects[0]["bistar_G_diagnostics"]
+    output: dict[str, Any] = {
+        "metric": metric,
+        "description": (
+            "Tau-free fraction of stored GP draws on which the known-truth "
+            "candidate has the smaller raw G value"
+        ),
+        "subject_majority_definition": "Strictly more than half of a subject's stored draws",
+        "by_configuration": {},
+    }
+    for config in first:
+        output["by_configuration"][config] = {}
+        for cohort, dataset_id, truth in (
+            ("power_truth", "synth_power", "Power"),
+            ("exponential_truth", "synth_exponential", "Exponential"),
+        ):
+            selected = [s for s in subjects if s["dataset_id"] == dataset_id]
+            wins = []
+            draw_counts = []
+            for subject in selected:
+                diagnostics = subject["bistar_G_diagnostics"][config][metric]
+                wins.append(int(diagnostics["per_model"][truth]["raw_draw_wins"]))
+                draw_counts.append(int(diagnostics["n_draws"]))
+            if len(set(draw_counts)) != 1:
+                raise AssertionError(f"Stored draw counts vary for {config}/{cohort}/{metric}")
+            total_draws = int(sum(draw_counts))
+            truth_wins = int(sum(wins))
+            output["by_configuration"][config][cohort] = {
+                "truth_candidate": truth,
+                "n_subjects": len(selected),
+                "n_draws_per_subject": draw_counts[0],
+                "n_draws_total": total_draws,
+                "truth_raw_draw_wins": truth_wins,
+                "truth_raw_draw_win_fraction": truth_wins / total_draws,
+                "n_subjects_truth_strict_majority": int(
+                    sum(win > draw_count / 2 for win, draw_count in zip(wins, draw_counts))
+                ),
+                "n_subjects_truth_exact_tie": int(
+                    sum(win == draw_count / 2 for win, draw_count in zip(wins, draw_counts))
+                ),
+            }
+    return output
+
+
+def _metric_scale_diagnostics(subjects: list[dict[str, Any]]) -> dict[str, Any]:
+    """Verify the stored pw_nll/pw_mse affine identity and tau-scale behavior."""
+    identity_errors = []
+    divisors = []
+    configurations = tuple(subjects[0]["bistar_G_diagnostics"])
+    for subject in subjects:
+        for config in configurations:
+            for candidate in ("Power", "Exponential"):
+                sigma = float(subject["fitted_params"][candidate]["sigma"])
+                sigma2 = sigma**2
+                pw_mse = float(
+                    subject["bistar_G_diagnostics"][config]["pw_mse"]["per_model"][
+                        candidate
+                    ]["mean_G"]
+                )
+                pw_nll = float(
+                    subject["bistar_G_diagnostics"][config]["pw_nll"]["per_model"][
+                        candidate
+                    ]["mean_G"]
+                )
+                reconstructed = 0.5 * math.log(2.0 * math.pi * sigma2) + pw_mse / (
+                    2.0 * sigma2
+                )
+                identity_errors.append(abs(pw_nll - reconstructed))
+                divisors.append(2.0 * sigma2)
+
+    tau_grid = sorted(float(t) for t in subjects[0]["bistar_probs"][configurations[0]]["pw_nll"])
+    probability_medians: dict[str, Any] = {}
+    for config in configurations:
+        probability_medians[config] = {}
+        for metric in ("pw_nll", "pw_mse"):
+            probability_medians[config][metric] = {}
+            for cohort, dataset_id in (
+                ("power_truth", "synth_power"),
+                ("exponential_truth", "synth_exponential"),
+                ("all_subjects", None),
+            ):
+                selected = (
+                    subjects
+                    if dataset_id is None
+                    else [s for s in subjects if s["dataset_id"] == dataset_id]
+                )
+                probability_medians[config][metric][cohort] = [
+                    {
+                        "tau": tau,
+                        "median_max_candidate_probability": float(
+                            np.median(
+                                [
+                                    max(
+                                        float(p)
+                                        for p in subject["bistar_probs"][config][metric][
+                                            str(tau)
+                                        ].values()
+                                    )
+                                    for subject in selected
+                                ]
+                            )
+                        ),
+                    }
+                    for tau in tau_grid
+                ]
+
+    return {
+        "affine_identity": {
+            "formula": (
+                "pw_nll = 0.5 * log(2 * pi * sigma_theta^2) "
+                "+ pw_mse / (2 * sigma_theta^2)"
+            ),
+            "description": (
+                "Candidate-specific affine identity checked on every stored "
+                "configuration, subject, and candidate mean_G pair"
+            ),
+            "n_stored_mean_G_pairs_checked": len(identity_errors),
+            "max_absolute_error": max(identity_errors),
+            "two_sigma_squared_divisor_min": min(divisors),
+            "two_sigma_squared_divisor_max": max(divisors),
+            "shared_tau_invariance": False,
+            "non_invariance_note": (
+                "BMS* scores exp(-G/tau) at one shared tau, so probability "
+                "magnitudes are not comparable across differently scaled metrics."
+            ),
+        },
+        "stored_tau_grid_probability_medians": {
+            "description": (
+                "Median maximum candidate probabilities from the stored 15-point "
+                "tau grid; retained only to demonstrate metric-scale non-invariance"
+            ),
+            "n_tau_values": len(tau_grid),
+            "tau_grid": tau_grid,
+            "by_configuration_metric_cohort": probability_medians,
+        },
+    }
+
+
 def _selection_summary(
     source_aggregate: dict[str, Any], subjects: list[dict[str, Any]]
 ) -> dict[str, Any]:
@@ -278,8 +419,76 @@ def _selection_summary(
     }
 
 
+def _summarize_deviation_estimand(
+    deviations: dict[str, dict[str, list[np.ndarray]]],
+    *,
+    n_atoms_per_subject: int,
+    atom_description: str,
+    estimand_description: str,
+) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
+    """Pool a per-subject deviation estimand and compute common summaries."""
+    curves: dict[str, Any] = {}
+    gaps: dict[str, Any] = {}
+    headlines: dict[str, Any] = {}
+    for cohort in ("power_truth", "exponential_truth"):
+        curves[cohort] = {}
+        means = {}
+        for candidate in ("Power", "Exponential"):
+            pooled = np.concatenate(deviations[cohort][candidate], axis=0)
+            expected_shape = (25 * n_atoms_per_subject, TRIAL_GRID.size)
+            if pooled.shape != expected_shape:
+                raise AssertionError(
+                    f"Unexpected pooled deviation shape for {cohort}/{candidate}: "
+                    f"{pooled.shape} != {expected_shape}"
+                )
+            mean = pooled.mean(axis=0)
+            means[candidate] = mean
+            curves[cohort][candidate] = {
+                "estimand": estimand_description,
+                "n_subjects": 25,
+                "n_atoms_per_subject": n_atoms_per_subject,
+                "atom_description": atom_description,
+                "n_pooled_atoms_per_trial": int(pooled.shape[0]),
+                "mean": mean,
+                "band_q10": np.quantile(pooled, 0.10, axis=0),
+                "band_q90": np.quantile(pooled, 0.90, axis=0),
+            }
+        gap = np.abs(means["Power"] - means["Exponential"])
+        total_gap = float(gap.sum())
+        first_five = float(gap[:5].sum())
+        peak_index = int(np.argmax(gap))
+        gaps[cohort] = {
+            "estimand": estimand_description,
+            "definition": (
+                "Absolute difference between the two candidates' pooled mean "
+                "absolute deviations at each trial"
+            ),
+            "absolute_mean_deviation_gap": gap,
+        }
+        headlines[cohort] = {
+            "estimand": estimand_description,
+            "peak_trial": int(TRIAL_GRID[peak_index]),
+            "peak_gap": float(gap[peak_index]),
+            "mean_gap_trials_1_to_5": float(gap[:5].mean()),
+            "mean_gap_trials_6_to_20": float(gap[5:].mean()),
+            "first_five_fraction_of_total_gap": first_five / total_gap if total_gap else 0.0,
+            "first_ten_fraction_of_total_gap": (
+                float(gap[:10].sum()) / total_gap if total_gap else 0.0
+            ),
+            "power_regret_mean_over_20_trials": float(means["Power"].mean()),
+            "exponential_regret_mean_over_20_trials": float(
+                means["Exponential"].mean()
+            ),
+        }
+    return curves, gaps, headlines
+
+
 def _plot_regret_curves(
-    regret_curves: dict[str, Any], discrimination_gap: dict[str, Any], path: Path
+    regret_curves: dict[str, Any],
+    discrimination_gap: dict[str, Any],
+    mean_based_regret_curves: dict[str, Any],
+    mean_based_discrimination_gap: dict[str, Any],
+    path: Path,
 ) -> None:
     colors = {"Power": "#315B8A", "Exponential": "#C65A34"}
     labels = {"power_truth": "Power-generated", "exponential_truth": "Exponential-generated"}
@@ -294,19 +503,44 @@ def _plot_regret_curves(
         ax = axes[0, column]
         for candidate in ("Power", "Exponential"):
             record = regret_curves[cohort][candidate]
+            mean_record = mean_based_regret_curves[cohort][candidate]
             mean = np.asarray(record["mean"])
+            mean_based = np.asarray(mean_record["mean"])
             lower = np.asarray(record["band_q10"])
             upper = np.asarray(record["band_q90"])
-            ax.plot(TRIAL_GRID, mean, color=colors[candidate], lw=2.2, label=candidate)
+            ax.plot(
+                TRIAL_GRID,
+                mean,
+                color=colors[candidate],
+                lw=2.2,
+                label=candidate,
+            )
+            ax.plot(
+                TRIAL_GRID,
+                mean_based,
+                color=colors[candidate],
+                lw=1.9,
+                ls="--",
+            )
             ax.fill_between(TRIAL_GRID, lower, upper, color=colors[candidate], alpha=0.14)
         ax.set_title(labels[cohort])
-        ax.set_ylabel("Absolute regret (RT units)")
+        ax.set_ylabel("Absolute deviation (RT units)")
         ax.grid(alpha=0.22, linewidth=0.7)
-        ax.legend(frameon=False)
+        ax.legend(frameon=False, fontsize=8)
 
         gap_ax = axes[1, column]
-        gap = np.asarray(discrimination_gap[cohort]["absolute_mean_regret_gap"])
+        gap = np.asarray(discrimination_gap[cohort]["absolute_mean_deviation_gap"])
+        mean_gap = np.asarray(
+            mean_based_discrimination_gap[cohort]["absolute_mean_deviation_gap"]
+        )
         gap_ax.plot(TRIAL_GRID, gap, color="#5D3A7A", lw=2.0)
+        gap_ax.plot(
+            TRIAL_GRID,
+            mean_gap,
+            color="#5D3A7A",
+            lw=1.8,
+            ls="--",
+        )
         gap_ax.fill_between(TRIAL_GRID, 0.0, gap, color="#5D3A7A", alpha=0.14)
         gap_ax.axvspan(0.5, 5.5, color="#D4A72C", alpha=0.08)
         gap_ax.set_xlabel("Practice trial")
@@ -314,11 +548,14 @@ def _plot_regret_curves(
         gap_ax.set_xticks([1, 5, 10, 15, 20])
         gap_ax.grid(alpha=0.22, linewidth=0.7)
 
-    fig.suptitle("Candidate regret under stored practice-run GP hyperparameters", y=0.995)
+    fig.suptitle("Candidate deviation under stored practitioner-MAP GP", y=0.995)
     fig.text(
         0.5,
         0.01,
-        "Lines show pooled subject-draw means; bands show pooled 10th to 90th percentiles.",
+        (
+            "Solid: MAP-conditional posterior expected absolute deviation of the latent "
+            "function. Dashed: posterior-mean plug-in. Bands show pooled draw dispersion."
+        ),
         ha="center",
         fontsize=9,
     )
@@ -331,7 +568,23 @@ def _write_readme(results: dict[str, Any], path: Path) -> None:
     fidelity = results["reconstruction_fidelity"]
     power = results["headline_regret"]["power_truth"]
     exponential = results["headline_regret"]["exponential_truth"]
-    readme = f"""# Case D regret curves
+    mean_power = results["mean_based_headline_regret"]["power_truth"]
+    mean_exponential = results["mean_based_headline_regret"]["exponential_truth"]
+    raw_wins = results["stored_truth_raw_draw_wins"]["by_configuration"]
+    affine = results["metric_scale_diagnostics"]["affine_identity"]
+    tau_medians = results["metric_scale_diagnostics"][
+        "stored_tau_grid_probability_medians"
+    ]["by_configuration_metric_cohort"]
+    power_pw_nll_at_tau_min = [
+        tau_medians[config]["pw_nll"]["power_truth"][0][
+            "median_max_candidate_probability"
+        ]
+        for config in ("practitioner", "moderate", "agnostic")
+    ]
+    practitioner_pw_mse_at_tau_max = tau_medians["practitioner"]["pw_mse"][
+        "all_subjects"
+    ][-1]["median_max_candidate_probability"]
+    readme = f"""# Case D deviation curves
 
 Run from the repository root:
 
@@ -345,7 +598,12 @@ The script reads the 50 subject JSONs in
 power-generated and 25 exponential-generated curves. The practice data
 directory contains no Evans et al. CSVs, so none of these results concern the
 real Evans corpus. The regenerated training series range from {results['provenance']['training_trial_counts']['min']} to {results['provenance']['training_trial_counts']['max']}
-trials; all contain the common trials 1 through 20 used for the regret figure.
+trials. The stored practice G values use 50 uniformly spaced points over each
+subject's full trial span, whereas both reconstructed estimands use integer
+trials 1 through 20. For a 79-trial series, the latter grid covers
+{100 * results['provenance']['evaluation_domains']['longest_subject_continuous_span_overlap_fraction']:.1f}% of the full continuous trial span. Comparisons between the reconstructed curves
+and stored aggregate G diagnostics therefore concern only their shared early
+region.
 
 ## Reconstruction
 
@@ -363,21 +621,36 @@ subject JSONs do not retain the HMC hyperparameter draws. This script rebuilds
 the practitioner RBF GP at that stored point, conditions on the complete
 regenerated series with normalized-space jitter {CONDITIONING_JITTER:.1e}, and
 draws {N_DRAWS} latent posterior functions per subject. It performs no fitting
-and no HMC. Subject `i` uses NumPy seed `{DRAW_SEED_BASE} + i`.
+and no HMC. Subject `i` uses NumPy seed `{DRAW_SEED_BASE} + i`. The limits-note
+formula averages posterior mean functions over hyperparameter draws. The stored
+files cannot reconstruct that target. The solid curves instead report the
+MAP-conditional posterior expected absolute deviation of the latent function,
+and the dashed curves report the posterior-mean plug-in at the same MAP point.
+
+## Estimands and bands
 
-## Estimand and band
+The MAP-conditional posterior expected absolute deviation computes
+`E_{{f | y, eta_hat}}[abs(f(t) - mu_theta(t))]`. Its mean at each trial pools
+25 subjects times 100 draws within a truth cohort. The shaded band spans the
+10th and 90th percentiles of those same 2,500 subject-draw absolute deviations;
+it describes dispersion, not a confidence interval for the cohort mean. The
+mean-based plug-in computes
+`abs(E[f(t) | y, eta_hat] - mu_theta(t))` per subject and candidate. Its JSON
+band pools the 25 subject values; the figure overlays only its dashed cohort
+mean. Jensen's inequality makes the draw-based deviation no smaller than the
+plug-in for each subject, candidate, and trial. The latent posterior spread
+therefore inflates candidate deviations and generally compresses their gap by a
+trial-dependent amount. Both estimands use raw response-time units (RT units).
 
-The implemented formula equals
-`regret_theta(t) = E_draws[abs(mu_GP(t) - mu_theta(t))]`. A chat-derived Q&A in
-the local limits note mentions a squared difference, but the formal formula and
-the Case D work order specify the absolute difference. The mean at each trial
-pools 25 subjects times 100 draws within a truth cohort. The shaded band spans
-the 10th and 90th percentiles of those same 2,500 subject-draw absolute errors;
-it describes dispersion across subjects and posterior function draws, not a
-confidence interval for the cohort mean.
+| Truth cohort | Estimand | Mean Power deviation (RT units) | Mean Exponential deviation (RT units) | Peak gap (RT units) |
+|---|---|---:|---:|---:|
+| Power | MAP-conditional posterior expected absolute deviation | {power['power_regret_mean_over_20_trials']:.3f} | {power['exponential_regret_mean_over_20_trials']:.3f} | {power['peak_gap']:.3f} at trial {power['peak_trial']} |
+| Power | Posterior-mean plug-in | {mean_power['power_regret_mean_over_20_trials']:.3f} | {mean_power['exponential_regret_mean_over_20_trials']:.3f} | {mean_power['peak_gap']:.3f} at trial {mean_power['peak_trial']} |
+| Exponential | MAP-conditional posterior expected absolute deviation | {exponential['power_regret_mean_over_20_trials']:.3f} | {exponential['exponential_regret_mean_over_20_trials']:.3f} | {exponential['peak_gap']:.3f} at trial {exponential['peak_trial']} |
+| Exponential | Posterior-mean plug-in | {mean_exponential['power_regret_mean_over_20_trials']:.3f} | {mean_exponential['exponential_regret_mean_over_20_trials']:.3f} | {mean_exponential['peak_gap']:.3f} at trial {mean_exponential['peak_trial']} |
 
 For the power-generated cohort, {100 * power['first_five_fraction_of_total_gap']:.1f}% of the summed
-20-trial discrimination gap occurs in trials 1 through 5, and the first 10
+20-trial MAP-conditional gap occurs in trials 1 through 5, and the first 10
 trials account for {100 * power['first_ten_fraction_of_total_gap']:.1f}%. The largest gap equals
 {power['peak_gap']:.3f} RT units at trial {power['peak_trial']}. For the exponential-generated cohort,
 the corresponding shares equal {100 * exponential['first_five_fraction_of_total_gap']:.1f}% and
@@ -390,15 +663,38 @@ the corresponding shares equal {100 * exponential['first_five_fraction_of_total_
 configuration, legacy metric, truth cohort, and candidate. It never recomputes
 G. The practice artifacts predate the W1 metric decision and contain
 `pw_nll`, `pw_mse`, and `pw_hellinger`; they contain no `pw_kl_vcal`.
-`pw_nll` provides the closest available role to the W1 primary, but the script
-does not rename it or introduce a new metric.
+The primary `pw_kl_vcal` weights squared error by GP variance. Legacy `pw_nll`
+instead weights by each candidate's fitted noise variance; on that axis,
+`pw_mse` more closely resembles the primary metric.
+
+Every one of the {affine['n_stored_mean_G_pairs_checked']} stored `mean_G` pairs satisfies
+`pw_nll = 0.5*log(2*pi*sigma_theta^2) + pw_mse/(2*sigma_theta^2)`, with maximum
+absolute error {affine['max_absolute_error']:.2e}. The candidate-specific divisor
+`2*sigma_theta^2` ranges from {affine['two_sigma_squared_divisor_min']:.1f} to
+{affine['two_sigma_squared_divisor_max']:.1f}. BMS* applies `exp(-G/tau)` at a
+shared temperature, so soft-transfer probability magnitudes cannot be compared
+across these differently scaled metrics. No value on the stored 15-point grid
+removes that scale gap: at `tau=0.1`, the power-cohort `pw_nll` medians equal
+{power_pw_nll_at_tau_min[0]:.3f}, {power_pw_nll_at_tau_min[1]:.3f}, and
+{power_pw_nll_at_tau_min[2]:.3f} across practitioner, moderate, and agnostic
+(about 0.57), while the all-subject practitioner `pw_mse` median remains
+{practitioner_pw_mse_at_tau_max:.3f} at `tau=31.6`.
+
+The tau-free `pw_nll` `raw_draw_wins` diagnostic retains the asymmetry:
+
+| Configuration | Power truth: true-family draw wins | Power subjects with true-family majority | Exponential truth: true-family draw wins | Exponential subjects with true-family majority |
+|---|---:|---:|---:|---:|
+| practitioner | {100 * raw_wins['practitioner']['power_truth']['truth_raw_draw_win_fraction']:.1f}% | {raw_wins['practitioner']['power_truth']['n_subjects_truth_strict_majority']} / 25 | {100 * raw_wins['practitioner']['exponential_truth']['truth_raw_draw_win_fraction']:.1f}% | {raw_wins['practitioner']['exponential_truth']['n_subjects_truth_strict_majority']} / 25 |
+| moderate | {100 * raw_wins['moderate']['power_truth']['truth_raw_draw_win_fraction']:.1f}% | {raw_wins['moderate']['power_truth']['n_subjects_truth_strict_majority']} / 25 | {100 * raw_wins['moderate']['exponential_truth']['truth_raw_draw_win_fraction']:.1f}% | {raw_wins['moderate']['exponential_truth']['n_subjects_truth_strict_majority']} / 25 |
+| agnostic | {100 * raw_wins['agnostic']['power_truth']['truth_raw_draw_win_fraction']:.1f}% | {raw_wins['agnostic']['power_truth']['n_subjects_truth_strict_majority']} / 25 | {100 * raw_wins['agnostic']['exponential_truth']['truth_raw_draw_win_fraction']:.1f}% | {raw_wins['agnostic']['exponential_truth']['n_subjects_truth_strict_majority']} / 25 |
 
 Files:
 
-- `results.json`: provenance, fidelity checks, regret curves, discrimination
-  gaps, stored selection summaries, and aggregated stored G magnitudes.
+- `results.json`: provenance, fidelity checks, both deviation estimands,
+  discrimination gaps, scale diagnostics, tau-free draw wins, stored selection
+  summaries, and aggregated stored G magnitudes.
 - `regret_curves.png`: two truth-cohort panels with pooled dispersion bands and
-  per-trial candidate discrimination gaps.
+  dashed posterior-mean overlays plus per-trial candidate discrimination gaps.
 """
     path.write_text(readme)
 
@@ -421,6 +717,10 @@ def main() -> None:
         "power_truth": {"Power": [], "Exponential": []},
         "exponential_truth": {"Power": [], "Exponential": []},
     }
+    mean_based_regrets: dict[str, dict[str, list[np.ndarray]]] = {
+        "power_truth": {"Power": [], "Exponential": []},
+        "exponential_truth": {"Power": [], "Exponential": []},
+    }
     observed_lengths = []
 
     for artifact in subject_artifacts:
@@ -468,7 +768,7 @@ def main() -> None:
                 )
             candidate_means[candidate_name] = candidate.predict(TRIAL_GRID).mean
 
-        function_draws, covariance_check = _conditioned_function_draws(
+        function_draws, posterior_mean, covariance_check = _conditioned_latent_posterior(
             ncurve,
             artifact["gp_hyperparameters"],
             TRIAL_GRID,
@@ -479,6 +779,9 @@ def main() -> None:
             regrets[cohort][candidate_name].append(
                 np.abs(function_draws - candidate_means[candidate_name][None, :])
             )
+            mean_based_regrets[cohort][candidate_name].append(
+                np.abs(posterior_mean - candidate_means[candidate_name])[None, :]
+            )
 
         fidelity_rows.append(
             {
@@ -501,44 +804,26 @@ def main() -> None:
         for row in fidelity_rows
         for candidate in ("Power", "Exponential")
     ]
-    regret_curves: dict[str, Any] = {}
-    discrimination_gap: dict[str, Any] = {}
-    headline_regret: dict[str, Any] = {}
-    for cohort in ("power_truth", "exponential_truth"):
-        regret_curves[cohort] = {}
-        means = {}
-        for candidate in ("Power", "Exponential"):
-            pooled = np.concatenate(regrets[cohort][candidate], axis=0)
-            if pooled.shape != (25 * N_DRAWS, TRIAL_GRID.size):
-                raise AssertionError(f"Unexpected pooled regret shape for {cohort}/{candidate}")
-            mean = pooled.mean(axis=0)
-            means[candidate] = mean
-            regret_curves[cohort][candidate] = {
-                "n_subjects": 25,
-                "n_draws_per_subject": N_DRAWS,
-                "n_subject_draw_atoms_per_trial": int(pooled.shape[0]),
-                "mean": mean,
-                "band_q10": np.quantile(pooled, 0.10, axis=0),
-                "band_q90": np.quantile(pooled, 0.90, axis=0),
-            }
-        gap = np.abs(means["Power"] - means["Exponential"])
-        total_gap = float(gap.sum())
-        first_five = float(gap[:5].sum())
-        peak_index = int(np.argmax(gap))
-        discrimination_gap[cohort] = {
-            "definition": "Absolute difference between pooled candidate mean regrets at each trial",
-            "absolute_mean_regret_gap": gap,
-        }
-        headline_regret[cohort] = {
-            "peak_trial": int(TRIAL_GRID[peak_index]),
-            "peak_gap": float(gap[peak_index]),
-            "mean_gap_trials_1_to_5": float(gap[:5].mean()),
-            "mean_gap_trials_6_to_20": float(gap[5:].mean()),
-            "first_five_fraction_of_total_gap": first_five / total_gap if total_gap else 0.0,
-            "first_ten_fraction_of_total_gap": float(gap[:10].sum()) / total_gap if total_gap else 0.0,
-            "power_regret_mean_over_20_trials": float(means["Power"].mean()),
-            "exponential_regret_mean_over_20_trials": float(means["Exponential"].mean()),
-        }
+    draw_estimand_description = (
+        "MAP-conditional posterior expected absolute deviation of the latent function"
+    )
+    mean_estimand_description = "Posterior-mean plug-in absolute deviation at the MAP point"
+    regret_curves, discrimination_gap, headline_regret = _summarize_deviation_estimand(
+        regrets,
+        n_atoms_per_subject=N_DRAWS,
+        atom_description="Seeded latent function draw conditional on the stored MAP point",
+        estimand_description=draw_estimand_description,
+    )
+    (
+        mean_based_regret_curves,
+        mean_based_discrimination_gap,
+        mean_based_headline_regret,
+    ) = _summarize_deviation_estimand(
+        mean_based_regrets,
+        n_atoms_per_subject=1,
+        atom_description="One latent posterior mean function at the stored MAP point",
+        estimand_description=mean_estimand_description,
+    )
 
     sub25 = next(
         s
@@ -547,7 +832,7 @@ def main() -> None:
     )
     sub25_pw_nll = sub25["bistar_G_diagnostics"]["practitioner"]["pw_nll"]["per_model"]
     results = {
-        "schema_version": 1,
+        "schema_version": 2,
         "provenance": {
             "source_artifact_dir": "experiments/practice_EvansEtAL/results_hmc",
             "source_aggregate": "experiments/practice_EvansEtAL/results_hmc/aggregate.json",
@@ -562,20 +847,75 @@ def main() -> None:
                 "max": int(max(observed_lengths)),
                 "unique": sorted(set(int(n) for n in observed_lengths)),
             },
+            "evaluation_domains": {
+                "stored_practice_G": (
+                    "50-point uniform grid spanning each subject's full observed trial series"
+                ),
+                "stored_practice_G_n_points": 50,
+                "stored_practice_G_subject_trial_count_range": {
+                    "min": int(min(observed_lengths)),
+                    "max": int(max(observed_lengths)),
+                },
+                "reconstructed_deviation_curves": "Integer trials 1 through 20 only",
+                "reconstructed_deviation_n_points": int(TRIAL_GRID.size),
+                "shared_region": "Integer trials 1 through 20",
+                "longest_subject_continuous_span_overlap_fraction": float(
+                    (TRIAL_GRID[-1] - TRIAL_GRID[0])
+                    / (max(observed_lengths) - TRIAL_GRID[0])
+                ),
+                "linkage_limit": (
+                    "Reconstructed deviation curves can localize stored aggregate "
+                    "comparisons only within the shared early-trial region."
+                ),
+            },
             "evaluation_trial_grid": TRIAL_GRID,
             "data_seed": DATA_SEED,
             "posterior_function_draw_seed_base": DRAW_SEED_BASE,
             "posterior_function_draw_seed_rule": "seed = 20260811 + subject_id",
             "n_draws_per_subject": N_DRAWS,
             "stored_n_gp_samples_per_subject": N_DRAWS,
-            "formula": "regret_theta(t) = E_draws[abs(mu_GP(t) - mu_theta(t))]",
+            "formula": (
+                "MAP-conditional posterior expected absolute deviation of the latent "
+                "function: E_{f | y, eta_hat}[abs(f(t) - mu_theta(t))]"
+            ),
+            "mean_based_plugin_formula": (
+                "Posterior-mean plug-in absolute deviation at the MAP point: "
+                "abs(E[f(t) | y, eta_hat] - mu_theta(t))"
+            ),
             "regret_units": "raw response-time units from the synthetic generator",
-            "band_definition": "At each trial, q10 and q90 pool the 25 subjects by 100 posterior function draws within a truth cohort and describe dispersion rather than confidence limits for the mean.",
+            "band_definition": (
+                "For the MAP-conditional posterior expected absolute deviation of the "
+                "latent function, q10 and q90 pool 25 subjects by 100 posterior function "
+                "draws within a truth cohort. For the posterior-mean plug-in, q10 and q90 "
+                "pool 25 subject values. Both describe dispersion rather than confidence "
+                "limits for a cohort mean."
+            ),
             "summary_definition": "Summary fields use the arithmetic mean, sample standard deviation with ddof=1, and NumPy linear-interpolation quantiles.",
             "gp_hyperparameters_provenance": "run.py stores gp_hyperparameters once, immediately after the first successful configuration MAP fit. The default loop order starts with practitioner, so all 50 source files carry practitioner MAP values even though results_hmc subsequently runs HMC for GP samples.",
-            "gp_reconstruction": "Exact zero-mean RBF GP conditioning at stored lengthscale, outputscale, and noise; no refit and no hyperparameter sampling; latent posterior function draws exclude fresh observation noise.",
+            "gp_reconstruction": (
+                "Exact zero-mean RBF GP conditioning at stored lengthscale, outputscale, "
+                "and noise; no refit and no hyperparameter sampling; latent posterior "
+                "function draws exclude fresh observation noise."
+            ),
+            "mean_vs_draw_substitution": (
+                "The limits-note target averages posterior mean functions over "
+                "hyperparameter draws. The stored files do not retain those draws. This "
+                "artifact reports both the MAP-conditional posterior expected absolute "
+                "deviation of the latent function and a posterior-mean plug-in at the "
+                "same stored MAP point."
+            ),
+            "estimand_relation_note": (
+                "By Jensen's inequality, the MAP-conditional posterior expected "
+                "absolute deviation of the latent function is no smaller than the "
+                "posterior-mean plug-in for each subject, candidate, and trial. Unequal "
+                "inflation changes the candidate gap by a trial-dependent amount."
+            ),
             "conditioning_jitter_normalized_variance": CONDITIONING_JITTER,
-            "legacy_metric_note": "Stored diagnostics contain pw_nll, pw_mse, and pw_hellinger. They predate W1 and contain no pw_kl_vcal. pw_nll receives closest-role framing without relabeling or recomputation.",
+            "legacy_metric_note": (
+                "Stored diagnostics contain pw_nll, pw_mse, and pw_hellinger. They "
+                "predate W1 and contain no pw_kl_vcal. pw_nll weights squared error by "
+                "candidate fitted noise variance; pw_kl_vcal weights it by GP variance."
+            ),
             "formula_discrepancy_note": "The formal limits-note equation and Case D work order use absolute difference. A chat-derived Q&A in the same note says squared difference; this artifact follows the binding absolute formula.",
         },
         "reconstruction_fidelity": {
@@ -601,15 +941,34 @@ def main() -> None:
         },
         "trial_grid": TRIAL_GRID,
         "regret_band": {
+            "estimand": draw_estimand_description,
             "lower_quantile": 0.10,
             "upper_quantile": 0.90,
-            "aggregation": "Pooled across subjects and posterior function draws within each truth cohort",
+            "aggregation": (
+                "Pooled across subjects and posterior function draws for the "
+                "MAP-conditional posterior expected absolute deviation of the latent "
+                "function within each truth cohort"
+            ),
         },
         "regret_curves": regret_curves,
         "discrimination_gap": discrimination_gap,
         "headline_regret": headline_regret,
+        "mean_based_regret_band": {
+            "estimand": mean_estimand_description,
+            "lower_quantile": 0.10,
+            "upper_quantile": 0.90,
+            "aggregation": (
+                "Pooled across the 25 subject-level posterior-mean plug-in absolute "
+                "deviations within each truth cohort"
+            ),
+        },
+        "mean_based_regret_curves": mean_based_regret_curves,
+        "mean_based_discrimination_gap": mean_based_discrimination_gap,
+        "mean_based_headline_regret": mean_based_headline_regret,
         "stored_selection_summary": _selection_summary(source_aggregate, subject_artifacts),
         "stored_mean_G_summaries": _aggregate_stored_g(subject_artifacts),
+        "stored_truth_raw_draw_wins": _aggregate_truth_raw_draw_wins(subject_artifacts),
+        "metric_scale_diagnostics": _metric_scale_diagnostics(subject_artifacts),
         "stored_named_examples": {
             "synth_exponential_sub25_practitioner_pw_nll": {
                 "source_file": sub25["_source_file"],
@@ -631,7 +990,11 @@ def main() -> None:
         json.dumps(_json_ready(results), indent=2, sort_keys=True, allow_nan=False) + "\n"
     )
     _plot_regret_curves(
-        _json_ready(regret_curves), _json_ready(discrimination_gap), figure_path
+        _json_ready(regret_curves),
+        _json_ready(discrimination_gap),
+        _json_ready(mean_based_regret_curves),
+        _json_ready(mean_based_discrimination_gap),
+        figure_path,
     )
     if figure_path.stat().st_size >= FIGURE_SIZE_LIMIT:
         raise AssertionError(
@@ -650,11 +1013,19 @@ def main() -> None:
         f"max_abs_error={max(all_bic_errors):.3e}, tolerance={BIC_ABS_TOL:.1e}"
     )
     for cohort, headline in headline_regret.items():
+        mean_headline = mean_based_headline_regret[cohort]
         print(
-            f"{cohort}: peak trial {headline['peak_trial']}, "
+            f"{cohort}, MAP-conditional posterior expected absolute deviation "
+            f"of the latent function: peak trial {headline['peak_trial']}, "
             f"peak gap {headline['peak_gap']:.6f}, "
             f"first-five share {headline['first_five_fraction_of_total_gap']:.3f}"
         )
+        print(
+            f"{cohort}, posterior-mean plug-in absolute deviation at the MAP point: "
+            f"peak trial {mean_headline['peak_trial']}, "
+            f"peak gap {mean_headline['peak_gap']:.6f}, "
+            f"first-five share {mean_headline['first_five_fraction_of_total_gap']:.3f}"
+        )
 
 
 if __name__ == "__main__":
diff --git a/runs/regret_curves_mopen/README.md b/runs/regret_curves_mopen/README.md
index e5ca01f..bba8418 100644
--- a/runs/regret_curves_mopen/README.md
+++ b/runs/regret_curves_mopen/README.md
@@ -1,4 +1,4 @@
-# Case D regret curves
+# Case D deviation curves
 
 Run from the repository root:
 
@@ -12,7 +12,12 @@ The script reads the 50 subject JSONs in
 power-generated and 25 exponential-generated curves. The practice data
 directory contains no Evans et al. CSVs, so none of these results concern the
 real Evans corpus. The regenerated training series range from 20 to 79
-trials; all contain the common trials 1 through 20 used for the regret figure.
+trials. The stored practice G values use 50 uniformly spaced points over each
+subject's full trial span, whereas both reconstructed estimands use integer
+trials 1 through 20. For a 79-trial series, the latter grid covers
+24.4% of the full continuous trial span. Comparisons between the reconstructed curves
+and stored aggregate G diagnostics therefore concern only their shared early
+region.
 
 ## Reconstruction
 
@@ -30,21 +35,36 @@ subject JSONs do not retain the HMC hyperparameter draws. This script rebuilds
 the practitioner RBF GP at that stored point, conditions on the complete
 regenerated series with normalized-space jitter 1.0e-06, and
 draws 100 latent posterior functions per subject. It performs no fitting
-and no HMC. Subject `i` uses NumPy seed `20260811 + i`.
+and no HMC. Subject `i` uses NumPy seed `20260811 + i`. The limits-note
+formula averages posterior mean functions over hyperparameter draws. The stored
+files cannot reconstruct that target. The solid curves instead report the
+MAP-conditional posterior expected absolute deviation of the latent function,
+and the dashed curves report the posterior-mean plug-in at the same MAP point.
 
-## Estimand and band
+## Estimands and bands
 
-The implemented formula equals
-`regret_theta(t) = E_draws[abs(mu_GP(t) - mu_theta(t))]`. A chat-derived Q&A in
-the local limits note mentions a squared difference, but the formal formula and
-the Case D work order specify the absolute difference. The mean at each trial
-pools 25 subjects times 100 draws within a truth cohort. The shaded band spans
-the 10th and 90th percentiles of those same 2,500 subject-draw absolute errors;
-it describes dispersion across subjects and posterior function draws, not a
-confidence interval for the cohort mean.
+The MAP-conditional posterior expected absolute deviation computes
+`E_{f | y, eta_hat}[abs(f(t) - mu_theta(t))]`. Its mean at each trial pools
+25 subjects times 100 draws within a truth cohort. The shaded band spans the
+10th and 90th percentiles of those same 2,500 subject-draw absolute deviations;
+it describes dispersion, not a confidence interval for the cohort mean. The
+mean-based plug-in computes
+`abs(E[f(t) | y, eta_hat] - mu_theta(t))` per subject and candidate. Its JSON
+band pools the 25 subject values; the figure overlays only its dashed cohort
+mean. Jensen's inequality makes the draw-based deviation no smaller than the
+plug-in for each subject, candidate, and trial. The latent posterior spread
+therefore inflates candidate deviations and generally compresses their gap by a
+trial-dependent amount. Both estimands use raw response-time units (RT units).
+
+| Truth cohort | Estimand | Mean Power deviation (RT units) | Mean Exponential deviation (RT units) | Peak gap (RT units) |
+|---|---|---:|---:|---:|
+| Power | MAP-conditional posterior expected absolute deviation | 21.383 | 20.681 | 33.782 at trial 1 |
+| Power | Posterior-mean plug-in | 17.638 | 17.325 | 34.052 at trial 1 |
+| Exponential | MAP-conditional posterior expected absolute deviation | 35.587 | 14.855 | 91.452 at trial 1 |
+| Exponential | Posterior-mean plug-in | 33.901 | 10.764 | 92.890 at trial 1 |
 
 For the power-generated cohort, 70.0% of the summed
-20-trial discrimination gap occurs in trials 1 through 5, and the first 10
+20-trial MAP-conditional gap occurs in trials 1 through 5, and the first 10
 trials account for 82.2%. The largest gap equals
 33.782 RT units at trial 1. For the exponential-generated cohort,
 the corresponding shares equal 41.7% and
@@ -57,12 +77,35 @@ the corresponding shares equal 41.7% and
 configuration, legacy metric, truth cohort, and candidate. It never recomputes
 G. The practice artifacts predate the W1 metric decision and contain
 `pw_nll`, `pw_mse`, and `pw_hellinger`; they contain no `pw_kl_vcal`.
-`pw_nll` provides the closest available role to the W1 primary, but the script
-does not rename it or introduce a new metric.
+The primary `pw_kl_vcal` weights squared error by GP variance. Legacy `pw_nll`
+instead weights by each candidate's fitted noise variance; on that axis,
+`pw_mse` more closely resembles the primary metric.
+
+Every one of the 300 stored `mean_G` pairs satisfies
+`pw_nll = 0.5*log(2*pi*sigma_theta^2) + pw_mse/(2*sigma_theta^2)`, with maximum
+absolute error 1.78e-15. The candidate-specific divisor
+`2*sigma_theta^2` ranges from 743.3 to
+7161.5. BMS* applies `exp(-G/tau)` at a
+shared temperature, so soft-transfer probability magnitudes cannot be compared
+across these differently scaled metrics. No value on the stored 15-point grid
+removes that scale gap: at `tau=0.1`, the power-cohort `pw_nll` medians equal
+0.581, 0.569, and
+0.557 across practitioner, moderate, and agnostic
+(about 0.57), while the all-subject practitioner `pw_mse` median remains
+0.987 at `tau=31.6`.
+
+The tau-free `pw_nll` `raw_draw_wins` diagnostic retains the asymmetry:
+
+| Configuration | Power truth: true-family draw wins | Power subjects with true-family majority | Exponential truth: true-family draw wins | Exponential subjects with true-family majority |
+|---|---:|---:|---:|---:|
+| practitioner | 39.0% | 9 / 25 | 98.7% | 25 / 25 |
+| moderate | 39.9% | 8 / 25 | 94.6% | 25 / 25 |
+| agnostic | 41.5% | 9 / 25 | 92.1% | 25 / 25 |
 
 Files:
 
-- `results.json`: provenance, fidelity checks, regret curves, discrimination
-  gaps, stored selection summaries, and aggregated stored G magnitudes.
+- `results.json`: provenance, fidelity checks, both deviation estimands,
+  discrimination gaps, scale diagnostics, tau-free draw wins, stored selection
+  summaries, and aggregated stored G magnitudes.
 - `regret_curves.png`: two truth-cohort panels with pooled dispersion bands and
-  per-trial candidate discrimination gaps.
+  dashed posterior-mean overlays plus per-trial candidate discrimination gaps.

=== REGENERATED results.json (ABRIDGED) ===
{
 "discrimination_gap": {
  "exponential_truth": {
   "absolute_mean_deviation_gap": {
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
   "definition": "Absolute difference between the two candidates' pooled mean absolute deviations at each trial",
   "estimand": "MAP-conditional posterior expected absolute deviation of the latent function"
  },
  "power_truth": {
   "absolute_mean_deviation_gap": {
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
   "definition": "Absolute difference between the two candidates' pooled mean absolute deviations at each trial",
   "estimand": "MAP-conditional posterior expected absolute deviation of the latent function"
  }
 },
 "headline_regret": {
  "exponential_truth": {
   "estimand": "MAP-conditional posterior expected absolute deviation of the latent function",
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
   "estimand": "MAP-conditional posterior expected absolute deviation of the latent function",
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
 "mean_based_discrimination_gap": {
  "exponential_truth": {
   "absolute_mean_deviation_gap": {
    "__abridged__": "20 floats",
    "first3": [
     92.88999713781251,
     5.694803955967547,
     13.450973977232064
    ],
    "last3": [
     10.036050062323781,
     9.590559411378244,
     9.050064238856802
    ],
    "min": 5.694803955967547,
    "max": 92.88999713781251
   },
   "definition": "Absolute difference between the two candidates' pooled mean absolute deviations at each trial",
   "estimand": "Posterior-mean plug-in absolute deviation at the MAP point"
  },
  "power_truth": {
   "absolute_mean_deviation_gap": {
    "__abridged__": "20 floats",
    "first3": [
     34.05167565471554,
     11.07335573595175,
     4.148307625009332
    ],
    "last3": [
     2.7190588743179394,
     2.2807899067032746,
     2.1058002722942284
    ],
    "min": 0.584498864073435,
    "max": 34.05167565471554
   },
   "definition": "Absolute difference between the two candidates' pooled mean absolute deviations at each trial",
   "estimand": "Posterior-mean plug-in absolute deviation at the MAP point"
  }
 },
 "mean_based_headline_regret": {
  "exponential_truth": {
   "estimand": "Posterior-mean plug-in absolute deviation at the MAP point",
   "exponential_regret_mean_over_20_trials": 10.764172709047234,
   "first_five_fraction_of_total_gap": 0.40034269839889197,
   "first_ten_fraction_of_total_gap": 0.7496200488234263,
   "mean_gap_trials_1_to_5": 37.05066872573897,
   "mean_gap_trials_6_to_20": 18.498904496447196,
   "peak_gap": 92.88999713781251,
   "peak_trial": 1,
   "power_regret_mean_over_20_trials": 33.901018262817374
  },
  "power_truth": {
   "estimand": "Posterior-mean plug-in absolute deviation at the MAP point",
   "exponential_regret_mean_over_20_trials": 17.32462457616572,
   "first_five_fraction_of_total_gap": 0.6329818088541972,
   "first_ten_fraction_of_total_gap": 0.7395714828667208,
   "mean_gap_trials_1_to_5": 12.969109640059282,
   "mean_gap_trials_6_to_20": 2.5066013452963536,
   "peak_gap": 34.05167565471554,
   "peak_trial": 1,
   "power_regret_mean_over_20_trials": 17.63806529002045
  }
 },
 "mean_based_regret_band": {
  "aggregation": "Pooled across the 25 subject-level posterior-mean plug-in absolute deviations within each truth cohort",
  "estimand": "Posterior-mean plug-in absolute deviation at the MAP point",
  "lower_quantile": 0.1,
  "upper_quantile": 0.9
 },
 "mean_based_regret_curves": {
  "exponential_truth": {
   "Exponential": {
    "atom_description": "One latent posterior mean function at the stored MAP point",
    "band_q10": {
     "__abridged__": "20 floats",
     "first3": [
      21.747846158647462,
      7.082412806382718,
      2.7377694687531857
     ],
     "last3": [
      0.11095494770183906,
      0.7630186304521772,
      0.367870108164027
     ],
     "min": 0.11095494770183906,
     "max": 21.747846158647462
    },
    "band_q90": {
     "__abridged__": "20 floats",
     "first3": [
      54.293563041725385,
      35.27754246392763,
      16.13005307450503
     ],
     "last3": [
      13.709253541406408,
      15.947640494525814,
      14.593420342625588
     ],
     "min": 11.114262480953478,
     "max": 54.293563041725385
    },
    "estimand": "Posterior-mean plug-in absolute deviation at the MAP point",
    "mean": {
     "__abridged__": "20 floats",
     "first3": [
      38.68220488060546,
      19.88193972596966,
      9.263164939126693
     ],
     "last3": [
      6.040085885867627,
      6.881255243289295,
      7.261996651009156
     ],
     "min": 5.20636359800775,
     "max": 38.68220488060546
    },
    "n_atoms_per_subject": 1,
    "n_pooled_atoms_per_trial": 25,
    "n_subjects": 25
   },
   "Power": {
    "atom_description": "One latent posterior mean function at the stored MAP point",
    "band_q10": {
     "__abridged__": "20 floats",
     "first3": [
      67.7485117672013,
      2.4762155115983435,
      2.490568461114595
     ],
     "last3": [
      3.8645036579691694,
      2.0106838871903845,
      2.956490201243856
     ],
     "min": 2.0106838871903845,
     "max": 67.7485117672013
    },
    "band_q90": {
     "__abridged__": "20 floats",
     "first3": [
      200.9789833939314,
      51.13993549867656,
      39.81169117162108
     ],
     "last3": [
      30.351728667840646,
      33.335318176988885,
      34.46453090228213
     ],
     "min": 27.24532405172968,
     "max": 200.9789833939314
    },
    "estimand": "Posterior-mean plug-in absolute deviation at the MAP point",
    "mean": {
     "__abridged__": "20 floats",
     "first3": [
      131.57220201841798,
      25.576743681937206,
      22.714138916358756
     ],
     "last3": [
      16.076135948191407,
      16.47181465466754,
      16.312060889865958
     ],
     "min": 15.256879301292411,
     "max": 131.57220201841798
    },
    "n_atoms_per_subject": 1,
    "n_pooled_atoms_per_trial": 25,
    "n_subjects": 25
   }
  },
  "power_truth": {
   "Exponential": {
    "atom_description": "One latent posterior mean function at the stored MAP point",
    "band_q10": {
     "__abridged__": "20 floats",
     "first3": [
      26.12722870055168,
      12.252887894092124,
      5.989314620073606
     ],
     "last3": [
      2.540867006217161,
      0.9265830320570332,
      0.8002568860742031
     ],
     "min": 0.5667886075925255,
     "max": 26.12722870055168
    },
    "band_q90": {
     "__abridged__": "20 floats",
     "first3": [
      155.15281579009218,
      69.30258340936432,
      23.04566298455634
     ],
     "last3": [
      21.211163051055976,
      22.28667562436746,
      20.970484894843867
     ],
     "min": 19.644089021985337,
     "max": 155.15281579009218
    },
    "estimand": "Posterior-mean plug-in absolute deviation at the MAP point",
    "mean": {
     "__abridged__": "20 floats",
     "first3": [
      82.45391238964753,
      33.77764885010754,
      15.219164475824227
     ],
     "last3": [
      10.509417205201075,
      10.12857375192545,
      10.247016469963368
     ],
     "min": 10.078818200771863,
     "max": 82.45391238964753
    },
    "n_atoms_per_subject": 1,
    "n_pooled_atoms_per_trial": 25,
    "n_subjects": 25
   },
   "Power": {
    "atom_description": "One latent posterior mean function at the stored MAP point",
    "band_q10": {
     "__abridged__": "20 floats",
     "first3": [
      47.52091883034876,
      9.904906346495569,
      6.383508131399617
     ],
     "last3": [
      0.5812538838239221,
      0.9312582249735897,
      1.3942139625951655
     ],
     "min": 0.5812538838239221,
     "max": 47.52091883034876
    },
    "band_q90": {
     "__abridged__": "20 floats",
     "first3": [
      214.40544659761045,
      43.5946463460022,
      40.40314756778859
     ],
     "last3": [
      15.374531402863502,
      16.35437256272679,
      17.176779985961456
     ],
     "min": 13.892683582755353,
     "max": 214.40544659761045
    },
    "estimand": "Posterior-mean plug-in absolute deviation at the MAP point",
    "mean": {
     "__abridged__": "20 floats",
     "first3": [
      116.50558804436307,
      22.70429311415579,
      19.36747210083356
     ],
     "last3": [
      7.7903583308831355,
      7.847783845222175,
      8.14121619766914
     ],
     "min": 7.7903583308831355,
     "max": 116.50558804436307
    },
    "n_atoms_per_subject": 1,
    "n_pooled_atoms_per_trial": 25,
    "n_subjects": 25
   }
  }
 },
 "metric_scale_diagnostics": {
  "affine_identity": {
   "description": "Candidate-specific affine identity checked on every stored configuration, subject, and candidate mean_G pair",
   "formula": "pw_nll = 0.5 * log(2 * pi * sigma_theta^2) + pw_mse / (2 * sigma_theta^2)",
   "max_absolute_error": 1.7763568394002505e-15,
   "n_stored_mean_G_pairs_checked": 300,
   "non_invariance_note": "BMS* scores exp(-G/tau) at one shared tau, so probability magnitudes are not comparable across differently scaled metrics.",
   "shared_tau_invariance": false,
   "two_sigma_squared_divisor_max": 7161.481610527603,
   "two_sigma_squared_divisor_min": 743.3198609618871
  },
  "stored_tau_grid_probability_medians": {
   "by_configuration_metric_cohort": {
    "agnostic": {
     "pw_mse": {
      "all_subjects": [
       {
        "median_max_candidate_probability": 0.915,
        "tau": 0.1
       },
       {
        "median_max_candidate_probability": 0.915,
        "tau": 0.15085907086001785
       },
       {
        "median_max_candidate_probability": 0.915,
        "tau": 0.22758459260747887
       },
       {
        "median_max_candidate_probability": 0.915,
        "tau": 0.3433320018281994
       },
       {
        "median_max_candidate_probability": 0.9150000000000177,
        "tau": 0.5179474679231211
       },
       {
        "median_max_candidate_probability": 0.9150000000570124,
        "tau": 0.7813707376518095
       },
       {
        "median_max_candidate_probability": 0.9150000119023511,
        "tau": 1.1787686347935873
       },
       {
        "median_max_candidate_probability": 0.9150003603100036,
        "tau": 1.7782794100389228
       },
       {
        "median_max_candidate_probability": 0.9150009811511262,
        "tau": 2.682695795279726
       },
       {
        "median_max_candidate_probability": 0.9149612604232349,
        "tau": 4.047089950759761
       },
       {
        "median_max_candidate_probability": 0.914590716260785,
        "tau": 6.105402296585329
       },
       {
        "median_max_candidate_probability": 0.9129981463815752,
        "tau": 9.21055317689482
       },
       {
        "median_max_candidate_probability": 0.907597749876616,
        "tau": 13.894954943731374
       },
       {
        "median_max_candidate_probability": 0.8910460767164242,
        "tau": 20.961799924531277
       },
       {
        "median_max_candidate_probability": 0.8760581649681496,
        "tau": 31.622776601683793
       }
      ],
      "exponential_truth": [
       {
        "median_max_candidate_probability": 0.95,
        "tau": 0.1
       },
       {
        "median_max_candidate_probability": 0.95,
        "tau": 0.15085907086001785
       },
       {
        "median_max_candidate_probability": 0.95,
        "tau": 0.22758459260747887
       },
       {
        "median_max_candidate_probability": 0.95,
        "tau": 0.3433320018281994
       },
       {
        "median_max_candidate_probability": 0.95,
        "tau": 0.5179474679231211
       },
       {
        "median_max_candidate_probability": 0.95,
        "tau": 0.7813707376518095
       },
       {
        "median_max_candidate_probability": 0.9500000000000004,
        "tau": 1.1787686347935873
       },
       {
        "median_max_candidate_probability": 0.9500000000047544,
        "tau": 1.7782794100389228
       },
       {
        "median_max_candidate_probability": 0.9500000026519956,
        "tau": 2.682695795279726
       },
       {
        "median_max_candidate_probability": 0.9500001072919255,
        "tau": 4.047089950759761
       },
       {
        "median_max_candidate_probability": 0.9499999513872672,
        "tau": 6.105402296585329
       },
       {
        "median_max_candidate_probability": 0.9499959147337118,
        "tau": 9.21055317689482
       },
       {
        "median_max_candidate_probability": 0.9499256932933022,
        "tau": 13.894954943731374
       },
       {
        "median_max_candidate_probability": 0.9494572228762864,
        "tau": 20.961799924531277
       },
       {
        "median_max_candidate_probability": 0.9476529265374657,
        "tau": 31.622776601683793
       }
      ],
      "power_truth": [
       {
        "median_max_candidate_probability": 0.8100000002044463,
        "tau": 0.1
       },
       {
        "median_max_candidate_probability": 0.8100000456833233,
        "tau": 0.15085907086001785
       },
       {
        "median_max_candidate_probability": 0.8100016479901869,
        "tau": 0.22758459260747887
       },
       {
        "median_max_candidate_probability": 0.8100177475343467,
        "tau": 0.3433320018281994
       },
       {
        "median_max_candidate_probability": 0.8100857071435189,
        "tau": 0.5179474679231211
       },
       {
        "median_max_candidate_probability": 0.8102409154969914,
        "tau": 0.7813707376518095
       },
       {
        "median_max_candidate_probability": 0.8104418754759447,
        "tau": 1.1787686347935873
       },
       {
        "median_max_candidate_probability": 0.8104470254947259,
        "tau": 1.7782794100389228
       },
       {
        "median_max_candidate_probability": 0.8097461005330455,
        "tau": 2.682695795279726
       },
       {
        "median_max_candidate_probability": 0.8076847869494385,
        "tau": 4.047089950759761
       },
       {
        "median_max_candidate_probability": 0.8030364511159224,
        "tau": 6.105402296585329
       },
       {
        "median_max_candidate_probability": 0.7921323437638692,
        "tau": 9.21055317689482
       },
       {
        "median_max_candidate_probability": 0.7780873926090749,
        "tau": 13.894954943731374
       },
       {
        "median_max_candidate_probability": 0.7443954804984806,
        "tau": 20.961799924531277
       },
       {
        "median_max_candidate_probability": 0.6997146784576921,
        "tau": 31.622776601683793
       }
      ]
     },
     "pw_nll": {
      "all_subjects": [
       {
        "median_max_candidate_probability": 0.7291517750166245,
        "tau": 0.1
       },
       {
        "median_max_candidate_probability": 0.6769791900962778,
        "tau": 0.15085907086001785
       },
       {
        "median_max_candidate_probability": 0.6318723722560831,
        "tau": 0.22758459260747887
       },
       {
        "median_max_candidate_probability": 0.5898313928044461,
        "tau": 0.3433320018281994
       },
       {
        "median_max_candidate_probability": 0.5604295265447139,
        "tau": 0.5179474679231211
       },
       {
        "median_max_candidate_probability": 0.5403855820972432,
        "tau": 0.7813707376518095
       },
       {
        "median_max_candidate_probability": 0.5268963071283329,
        "tau": 1.1787686347935873
       },
       {
        "median_max_candidate_probability": 0.5178784875172757,
        "tau": 1.7782794100389228
       },
       {
        "median_max_candidate_probability": 0.5118713003165127,
        "tau": 2.682695795279726
       },
       {
        "median_max_candidate_probability": 0.507877508334843,
        "tau": 4.047089950759761
       },
       {
        "median_max_candidate_probability": 0.5052253022254443,
        "tau": 6.105402296585329
       },
       {
        "median_max_candidate_probability": 0.5034652090473655,
        "tau": 9.21055317689482
       },
       {
        "median_max_candidate_probability": 0.5022976359187309,
        "tau": 13.894954943731374
       },
       {
        "median_max_candidate_probability": 0.5015233173951615,
        "tau": 20.961799924531277
       },
       {
        "median_max_candidate_probability": 0.5010098850691336,
        "tau": 31.622776601683793
       }
      ],
      "exponential_truth": [
       {
        "median_max_candidate_probability": 0.8854941916887752,
        "tau": 0.1
       },
       {
        "median_max_candidate_probability": 0.835991661998517,
        "tau": 0.15085907086001785
       },
       {
        "median_max_candidate_probability": 0.7589096924957632,
        "tau": 0.22758459260747887
       },
       {
        "median_max_candidate_probability": 0.6862789055912326,
        "tau": 0.3433320018281994
       },
       {
        "median_max_candidate_probability": 0.6324201356968516,
        "tau": 0.5179474679231211
       },
       {
        "median_max_candidate_probability": 0.5912387726188197,
        "tau": 0.7813707376518095
       },
       {
        "median_max_candidate_probability": 0.5617842470611764,
        "tau": 1.1787686347935873
       },
       {
        "median_max_candidate_probability": 0.5414501482127541,
        "tau": 1.7782794100389228
       },
       {
        "median_max_candidate_probability": 0.527668122706233,
        "tau": 2.682695795279726
       },
       {
        "median_max_candidate_probability": 0.5184168184776906,
        "tau": 4.047089950759761
       },
       {
        "median_max_candidate_probability": 0.512239144374903,
        "tau": 6.105402296585329
       },
       {
        "median_max_candidate_probability": 0.5081259491559378,
        "tau": 9.21055317689482
       },
       {
        "median_max_candidate_probability": 0.5053919432938695,
        "tau": 13.894954943731374
       },
       {
        "median_max_candidate_probability": 0.5035765102908517,
        "tau": 20.961799924531277
       },
       {
        "median_max_candidate_probability": 0.5023717773055637,
        "tau": 31.622776601683793
       }
      ],
      "power_truth": [
       {
        "median_max_candidate_probability": 0.5569539724953905,
        "tau": 0.1
       },
       {
        "median_max_candidate_probability": 0.5399307466854822,
        "tau": 0.15085907086001785
       },
       {
        "median_max_candidate_probability": 0.5274544799227111,
        "tau": 0.22758459260747887
       },
       {
        "median_max_candidate_probability": 0.5184510869517727,
        "tau": 0.3433320018281994
       },
       {
        "median_max_candidate_probability": 0.5123211541843508,
        "tau": 0.5179474679231211
       },
       {
        "median_max_candidate_probability": 0.5084043594457774,
        "tau": 0.7813707376518095
       },
       {
        "median_max_candidate_probability": 0.5056087749217772,
        "tau": 1.1787686347935873
       },
       {
        "median_max_candidate_probability": 0.5037345056678135,
        "tau": 1.7782794100389228
       },
       {
        "median_max_candidate_probability": 0.5024827978725015,
        "tau": 2.682695795279726
       },
       {
        "median_max_candidate_probability": 0.5016489838431978,
        "tau": 4.047089950759761
       },
       {
        "median_max_candidate_probability": 0.5010944735533458,
        "tau": 6.105402296585329
       },
       {
        "median_max_candidate_probability": 0.5007261141447422,
        "tau": 9.21055317689482
       },
       {
        "median_max_candidate_probability": 0.5004815920101173,
        "tau": 13.894954943731374
       },
       {
        "median_max_candidate_probability": 0.5003193527884595,
        "tau": 20.961799924531277
       },
       {
        "median_max_candidate_probability": 0.5002117420991279,
        "tau": 31.622776601683793
       }
      ]
     }
    },
    "moderate": {
     "pw_mse": {
      "all_subjects": [
       {
        "median_max_candidate_probability": 0.955,
        "tau": 0.1
       },
       {
        "median_max_candidate_probability": 0.955,
        "tau": 0.15085907086001785
       },
       {
        "median_max_candidate_probability": 0.955,
        "tau": 0.22758459260747887
       },
       {
        "median_max_candidate_probability": 0.9549999999999975,
        "tau": 0.3433320018281994
       },
       {
        "median_max_candidate_probability": 0.9549999999657125,
        "tau": 0.5179474679231211
       },
       {
        "median_max_candidate_probability": 0.9549999809232025,
        "tau": 0.7813707376518095
       },
       {
        "median_max_candidate_probability": 0.9549987435941014,
        "tau": 1.1787686347935873
       },
       {
        "median_max_candidate_probability": 0.9549799063756428,
        "tau": 1.7782794100389228
       },
       {
        "median_max_candidate_probability": 0.9533667774796155,
        "tau": 2.682695795279726
       },
       {
        "median_max_candidate_probability": 0.9508699603675239,
        "tau": 4.047089950759761
       },
       {
        "median_max_candidate_probability": 0.949894526214015,
        "tau": 6.105402296585329
       },
       {
        "median_max_candidate_probability": 0.9492979106584034,
        "tau": 9.21055317689482
       },
       {
        "median_max_candidate_probability": 0.9473634173613938,
        "tau": 13.894954943731374
       },
       {
        "median_max_candidate_probability": 0.9402622321910321,
        "tau": 20.961799924531277
       },
       {
        "median_max_candidate_probability": 0.9308761773493088,
        "tau": 31.622776601683793
       }
      ],
      "exponential_truth": [
       {
        "median_max_candidate_probability": 0.97,
        "tau": 0.1
       },
       {
        "median_max_candidate_probability": 0.97,
        "tau": 0.15085907086001785
       },
       {
        "median_max_candidate_probability": 0.9700000000000641,
        "tau": 0.22758459260747887
       },
       {
        "median_max_candidate_probability": 0.9700000001166174,
        "tau": 0.3433320018281994
       },
       {
        "median_max_candidate_probability": 0.9700000168999316,
        "tau": 0.5179474679231211
       },
       {
        "median_max_candidate_probability": 0.9700004575327431,
        "tau": 0.7813707376518095
       },
       {
        "median_max_candidate_probability": 0.9700040734319523,
        "tau": 1.1787686347935873
       },
       {
        "median_max_candidate_probability": 0.9700173469724119,
        "tau": 1.7782794100389228
       },
       {
        "median_max_candidate_probability": 0.9700452966393274,
        "tau": 2.682695795279726
       },
       {
        "median_max_candidate_probability": 0.9700855191348232,
        "tau": 4.047089950759761
       },
       {
        "median_max_candidate_probability": 0.970130241917534,
        "tau": 6.105402296585329
       },
       {
        "median_max_candidate_probability": 0.9701720565485196,
        "tau": 9.21055317689482
       },
       {
        "median_max_candidate_probability": 0.9702068804663365,
        "tau": 13.894954943731374
       },
       {
        "median_max_candidate_probability": 0.9702334517184702,
        "tau": 20.961799924531277
       },
       {
        "median_max_candidate_probability": 0.9702407576415744,
        "tau": 31.622776601683793
       }
      ],
      "power_truth": [
       {
        "median_max_candidate_probability": 0.8182032701872491,
        "tau": 0.1
       },
       {
        "median_max_candidate_probability": 0.8170090622630442,
        "tau": 0.15085907086001785
       },
       {
        "median_max_candidate_probability": 0.8158091241768657,
        "tau": 0.22758459260747887
       },
       {
        "median_max_candidate_probability": 0.8147579484162503,
        "tau": 0.3433320018281994
       },
       {
        "median_max_candidate_probability": 0.8138889947125224,
        "tau": 0.5179474679231211
       },
       {
        "median_max_candidate_probability": 0.8131013907799379,
        "tau": 0.7813707376518095
       },
       {
        "median_max_candidate_probability": 0.8122473099731344,
        "tau": 1.1787686347935873
       },
       {
        "median_max_candidate_probability": 0.8118621272186263,
        "tau": 1.7782794100389228
       },
       {
        "median_max_candidate_probability": 0.8123211803475034,
        "tau": 2.682695795279726
       },
       {
        "median_max_candidate_probability": 0.8127927746440574,
        "tau": 4.047089950759761
       },
       {
        "median_max_candidate_probability": 0.8131534182290407,
        "tau": 6.105402296585329
       },
       {
        "median_max_candidate_probability": 0.8130703746819997,
        "tau": 9.21055317689482
       },
       {
        "median_max_candidate_probability": 0.8115875029157339,
        "tau": 13.894954943731374
       },
       {
        "median_max_candidate_probability": 0.8066830741913835,
        "tau": 20.961799924531277
       },
       {
        "median_max_candidate_probability": 0.777933163467259,
        "tau": 31.622776601683793
       }
      ]
     },
     "pw_nll": {
      "all_subjects": [
       {
        "median_max_candidate_probability": 0.7684416824689437,
        "tau": 0.1
       },
       {
        "median_max_candidate_probability": 0.7050165576140018,
        "tau": 0.15085907086001785
       },
       {
        "median_max_candidate_probability": 0.6510312643728859,
        "tau": 0.22758459260747887
       },
       {
        "median_max_candidate_probability": 0.6064005188015069,
        "tau": 0.3433320018281994
       },
       {
        "median_max_candidate_probability": 0.5728376790370007,
        "tau": 0.5179474679231211
       },
       {
        "median_max_candidate_probability": 0.549062380079238,
        "tau": 0.7813707376518095
       },
       {
        "median_max_candidate_probability": 0.5327732643741806,
        "tau": 1.1787686347935873
       },
       {
        "median_max_candidate_probability": 0.5218032192123964,
        "tau": 1.7782794100389228
       },
       {
        "median_max_candidate_probability": 0.5144771494857767,
        "tau": 2.682695795279726
       },
       {
        "median_max_candidate_probability": 0.5096040594814581,
        "tau": 4.047089950759761
       },
       {
        "median_max_candidate_probability": 0.5063686249781556,
        "tau": 6.105402296585329
       },
       {
        "median_max_candidate_probability": 0.5042223328116183,
        "tau": 9.21055317689482
       },
       {
        "median_max_candidate_probability": 0.5027991088474325,
        "tau": 13.894954943731374
       },
       {
        "median_max_candidate_probability": 0.5018555310904111,
        "tau": 20.961799924531277
       },
       {
        "median_max_candidate_probability": 0.5012300065170814,
        "tau": 31.622776601683793
       }
      ],
      "exponential_truth": [
       {
        "median_max_candidate_probability": 0.9106962858063502,
        "tau": 0.1
       },
       {
        "median_max_candidate_probability": 0.8610975827917601,
        "tau": 0.15085907086001785
       },
       {
        "median_max_candidate_probability": 0.7851703528190683,
        "tau": 0.22758459260747887
       },
       {
        "median_max_candidate_probability": 0.7057973441295453,
        "tau": 0.3433320018281994
       },
       {
        "median_max_candidate_probability": 0.646479574055951,
        "tau": 0.5179474679231211
       },
       {
        "median_max_candidate_probability": 0.6012975630371092,
        "tau": 0.7813707376518095
       },
       {
        "median_max_candidate_probability": 0.5687290257563039,
        "tau": 1.1787686347935873
       },
       {
        "median_max_candidate_probability": 0.5461559137483315,
        "tau": 1.7782794100389228
       },
       {
        "median_max_candidate_probability": 0.5308256889924515,
        "tau": 2.682695795279726
       },
       {
        "median_max_candidate_probability": 0.5205245602220382,
        "tau": 4.047089950759761
       },
       {
        "median_max_candidate_probability": 0.5136421069754696,
        "tau": 6.105402296585329
       },
       {
        "median_max_candidate_probability": 0.5090582867873802,
        "tau": 9.21055317689482
       },
       {
        "median_max_candidate_probability": 0.5060109395455245,
        "tau": 13.894954943731374
       },
       {
        "median_max_candidate_probability": 0.5039872369955071,
        "tau": 20.961799924531277
       },
       {
        "median_max_candidate_probability": 0.5026442121073115,
        "tau": 31.622776601683793
       }
      ],
      "power_truth": [
       {
        "median_max_candidate_probability": 0.5690660110284153,
        "tau": 0.1
       },
       {
        "median_max_candidate_probability": 0.5468277170482767,
        "tau": 0.15085907086001785
       },
       {
        "median_max_candidate_probability": 0.5314748734612056,
        "tau": 0.22758459260747887
       },
       {
        "median_max_candidate_probability": 0.5220576062114068,
        "tau": 0.3433320018281994
       },
       {
        "median_max_candidate_probability": 0.5146681583087076,
        "tau": 0.5179474679231211
       },
       {
        "median_max_candidate_probability": 0.5097414983093281,
        "tau": 0.7813707376518095
       },
       {
        "median_max_candidate_probability": 0.5064647848761865,
        "tau": 1.1787686347935873
       },
       {
        "median_max_candidate_probability": 0.5042883851255595,
        "tau": 1.7782794100389228
       },
       {
        "median_max_candidate_probability": 0.5028439347020137,
        "tau": 2.682695795279726
       },
       {
        "median_max_candidate_probability": 0.5018857103140345,
        "tau": 4.047089950759761
       },
       {
        "median_max_candidate_probability": 0.5012502182396696,
        "tau": 6.105402296585329
       },
       {
        "median_max_candidate_probability": 0.500828835165358,
        "tau": 9.21055317689482
       },
       {
        "median_max_candidate_probability": 0.500549454884783,
        "tau": 13.894954943731374
       },
       {
        "median_max_candidate_probability": 0.500364236830318,
        "tau": 20.961799924531277
       },
       {
        "median_max_candidate_probability": 0.5002414503134274,
        "tau": 31.622776601683793
       }
      ]
     }
    },
    "practitioner": {
     "pw_mse": {
      "all_subjects": [
       {
        "median_max_candidate_probability": 1.0,
        "tau": 0.1
       },
       {
        "median_max_candidate_probability": 1.0,
        "tau": 0.15085907086001785
       },
       {
        "median_max_candidate_probability": 1.0,
        "tau": 0.22758459260747887
       },
       {
        "median_max_candidate_probability": 1.0,
        "tau": 0.3433320018281994
       },
       {
        "median_max_candidate_probability": 0.9999999999999825,
        "tau": 0.5179474679231211
       },
       {
        "median_max_candidate_probability": 0.9999999998577981,
        "tau": 0.7813707376518095
       },
       {
        "median_max_candidate_probability": 0.9999999415304355,
        "tau": 1.1787686347935873
       },
       {
        "median_max_candidate_probability": 0.999996724743484,
        "tau": 1.7782794100389228
       },
       {
        "median_max_candidate_probability": 0.9999518537967576,
        "tau": 2.682695795279726
       },
       {
        "median_max_candidate_probability": 0.9997113732119901,
        "tau": 4.047089950759761
       },
       {
        "median_max_candidate_probability": 0.9990503528609163,
        "tau": 6.105402296585329
       },
       {
        "median_max_candidate_probability": 0.9970354952860109,
        "tau": 9.21055317689482
       },
       {
        "median_max_candidate_probability": 0.9928559552365088,
        "tau": 13.894954943731374
       },
       {
        "median_max_candidate_probability": 0.9917116853822014,
        "tau": 20.961799924531277
       },
       {
        "median_max_candidate_probability": 0.9865572479420387,
        "tau": 31.622776601683793
       }
      ],
      "exponential_truth": [
       {
        "median_max_candidate_probability": 1.0,
        "tau": 0.1
       },
       {
        "median_max_candidate_probability": 1.0,
        "tau": 0.15085907086001785
       },
       {
        "median_max_candidate_probability": 1.0,
        "tau": 0.22758459260747887
       },
       {
        "median_max_candidate_probability": 1.0,
        "tau": 0.3433320018281994
       },
       {
        "median_max_candidate_probability": 1.0,
        "tau": 0.5179474679231211
       },
       {
        "median_max_candidate_probability": 1.0,
        "tau": 0.7813707376518095
       },
       {
        "median_max_candidate_probability": 1.0,
        "tau": 1.1787686347935873
       },
       {
        "median_max_candidate_probability": 1.0,
        "tau": 1.7782794100389228
       },
       {
        "median_max_candidate_probability": 1.0,
        "tau": 2.682695795279726
       },
       {
        "median_max_candidate_probability": 1.0,
        "tau": 4.047089950759761
       },
       {
        "median_max_candidate_probability": 1.0,
        "tau": 6.105402296585329
       },
       {
        "median_max_candidate_probability": 1.0,
        "tau": 9.21055317689482
       },
       {
        "median_max_candidate_probability": 0.9999999999949309,
        "tau": 13.894954943731374
       },
       {
        "median_max_candidate_probability": 0.999999993104361,
        "tau": 20.961799924531277
       },
       {
        "median_max_candidate_probability": 0.9999991757824439,
        "tau": 31.622776601683793
       }
      ],
      "power_truth": [
       {
        "median_max_candidate_probability": 0.950000001338247,
        "tau": 0.1
       },
       {
        "median_max_candidate_probability": 0.9500001011971192,
        "tau": 0.15085907086001785
       },
       {
        "median_max_candidate_probability": 0.9500017799419247,
        "tau": 0.22758459260747887
       },
       {
        "median_max_candidate_probability": 0.9500118422169733,
        "tau": 0.3433320018281994
       },
       {
        "median_max_candidate_probability": 0.9500383630939216,
        "tau": 0.5179474679231211
       },
       {
        "median_max_candidate_probability": 0.9500456429876923,
        "tau": 0.7813707376518095
       },
       {
        "median_max_candidate_probability": 0.9498705149863425,
        "tau": 1.1787686347935873
       },
       {
        "median_max_candidate_probability": 0.9492500201774884,
        "tau": 1.7782794100389228
       },
       {
        "median_max_candidate_probability": 0.9478749474360448,
        "tau": 2.682695795279726
       },
       {
        "median_max_candidate_probability": 0.9451913129439374,
        "tau": 4.047089950759761
       },
       {
        "median_max_candidate_probability": 0.939921937065564,
        "tau": 6.105402296585329
       },
       {
        "median_max_candidate_probability": 0.9287685903090902,
        "tau": 9.21055317689482
       },
       {
        "median_max_candidate_probability": 0.9149910912120246,
        "tau": 13.894954943731374
       },
       {
        "median_max_candidate_probability": 0.8926894442772615,
        "tau": 20.961799924531277
       },
       {
        "median_max_candidate_probability": 0.8223661426878969,
        "tau": 31.622776601683793
       }
      ]
     },
     "pw_nll": {
      "all_subjects": [
       {
        "median_max_candidate_probability": 0.7914527215345899,
        "tau": 0.1
       },
       {
        "median_max_candidate_probability": 0.7149278089831728,
        "tau": 0.15085907086001785
       },
       {
        "median_max_candidate_probability": 0.657048903966694,
        "tau": 0.22758459260747887
       },
       {
        "median_max_candidate_probability": 0.6106999438433625,
        "tau": 0.3433320018281994
       },
       {
        "median_max_candidate_probability": 0.5751993133856355,
        "tau": 0.5179474679231211
       },
       {
        "median_max_candidate_probability": 0.5503338442820387,
        "tau": 0.7813707376518095
       },
       {
        "median_max_candidate_probability": 0.5335481444207733,
        "tau": 1.1787686347935873
       },
       {
        "median_max_candidate_probability": 0.5223093599124856,
        "tau": 1.7782794100389228
       },
       {
        "median_max_candidate_probability": 0.5148167681382014,
        "tau": 2.682695795279726
       },
       {
        "median_max_candidate_probability": 0.5098333239280545,
        "tau": 4.047089950759761
       },
       {
        "median_max_candidate_probability": 0.5065231309981664,
        "tau": 6.105402296585329
       },
       {
        "median_max_candidate_probability": 0.504326077854293,
        "tau": 9.21055317689482
       },
       {
        "median_max_candidate_probability": 0.5028685253994187,
        "tau": 13.894954943731374
       },
       {
        "median_max_candidate_probability": 0.5019018483670812,
        "tau": 20.961799924531277
       },
       {
        "median_max_candidate_probability": 0.5012608475694812,
        "tau": 31.622776601683793
       }
      ],
      "exponential_truth": [
       {
        "median_max_candidate_probability": 0.9631470594707544,
        "tau": 0.1
       },
       {
        "median_max_candidate_probability": 0.9110513932425167,
        "tau": 0.15085907086001785
       },
       {
        "median_max_candidate_probability": 0.8331411932720818,
        "tau": 0.22758459260747887
       },
       {
        "median_max_candidate_probability": 0.7572631148395917,
        "tau": 0.3433320018281994
       },
       {
        "median_max_candidate_probability": 0.6821299711432761,
        "tau": 0.5179474679231211
       },
       {
        "median_max_candidate_probability": 0.6247652199881675,
        "tau": 0.7813707376518095
       },
       {
        "median_max_candidate_probability": 0.5840544639925019,
        "tau": 1.1787686347935873
       },
       {
        "median_max_candidate_probability": 0.5561689408759257,
        "tau": 1.7782794100389228
       },
       {
        "median_max_candidate_probability": 0.5373868781596636,
        "tau": 2.682695795279726
       },
       {
        "median_max_candidate_probability": 0.5248370151785461,
        "tau": 4.047089950759761
       },
       {
        "median_max_candidate_probability": 0.5164836405107585,
        "tau": 6.105402296585329
       },
       {
        "median_max_candidate_probability": 0.5109341019235226,
        "tau": 9.21055317689482
       },
       {
        "median_max_candidate_probability": 0.5072508829563425,
        "tau": 13.894954943731374
       },
       {
        "median_max_candidate_probability": 0.5048076095552504,
        "tau": 20.961799924531277
       },
       {
        "median_max_candidate_probability": 0.5031873261411676,
        "tau": 31.622776601683793
       }
      ],
      "power_truth": [
       {
        "median_max_candidate_probability": 0.5810374753655416,
        "tau": 0.1
       },
       {
        "median_max_candidate_probability": 0.5556587972980823,
        "tau": 0.15085907086001785
       },
       {
        "median_max_candidate_probability": 0.5371151342204393,
        "tau": 0.22758459260747887
       },
       {
        "median_max_candidate_probability": 0.5261296586851232,
        "tau": 0.3433320018281994
       },
       {
        "median_max_candidate_probability": 0.5174877400515677,
        "tau": 0.5179474679231211
       },
       {
        "median_max_candidate_probability": 0.5116646764774314,
        "tau": 0.7813707376518095
       },
       {
        "median_max_candidate_probability": 0.5077637730018814,
        "tau": 1.1787686347935873
       },
       {
        "median_max_candidate_probability": 0.5051601741615739,
        "tau": 1.7782794100389228
       },
       {
        "median_max_candidate_probability": 0.5034265631423782,
        "tau": 2.682695795279726
       },
       {
        "median_max_candidate_probability": 0.5022740116262242,
        "tau": 4.047089950759761
       },
       {
        "median_max_candidate_probability": 0.5015085344953824,
        "tau": 6.105402296585329
       },
       {
        "median_max_candidate_probability": 0.5010004716089225,
        "tau": 9.21055317689482
       },
       {
        "median_max_candidate_probability": 0.5006634063247704,
        "tau": 13.894954943731374
       },
       {
        "median_max_candidate_probability": 0.5004398504589764,
        "tau": 20.961799924531277
       },
       {
        "median_max_candidate_probability": 0.5002916068997112,
        "tau": 31.622776601683793
       }
      ]
     }
    }
   },
   "description": "Median maximum candidate probabilities from the stored 15-point tau grid; retained only to demonstrate metric-scale non-invariance",
   "n_tau_values": 15,
   "tau_grid": {
    "__abridged__": "15 floats",
    "first3": [
     0.1,
     0.15085907086001785,
     0.22758459260747887
    ],
    "last3": [
     13.894954943731374,
     20.961799924531277,
     31.622776601683793
    ],
    "min": 0.1,
    "max": 31.622776601683793
   }
  }
 },
 "provenance": {
  "band_definition": "For the MAP-conditional posterior expected absolute deviation of the latent function, q10 and q90 pool 25 subjects by 100 posterior function draws within a truth cohort. For the posterior-mean plug-in, q10 and q90 pool 25 subject values. Both describe dispersion rather than confidence limits for a cohort mean.",
  "cohort_sizes": {
   "exponential_truth": 25,
   "power_truth": 25
  },
  "conditioning_jitter_normalized_variance": 1e-06,
  "data_seed": 42,
  "estimand_relation_note": "By Jensen's inequality, the MAP-conditional posterior expected absolute deviation of the latent function is no smaller than the posterior-mean plug-in for each subject, candidate, and trial. Unequal inflation changes the candidate gap by a trial-dependent amount.",
  "evaluation_domains": {
   "linkage_limit": "Reconstructed deviation curves can localize stored aggregate comparisons only within the shared early-trial region.",
   "longest_subject_continuous_span_overlap_fraction": 0.24358974358974358,
   "reconstructed_deviation_curves": "Integer trials 1 through 20 only",
   "reconstructed_deviation_n_points": 20,
   "shared_region": "Integer trials 1 through 20",
   "stored_practice_G": "50-point uniform grid spanning each subject's full observed trial series",
   "stored_practice_G_n_points": 50,
   "stored_practice_G_subject_trial_count_range": {
    "max": 79,
    "min": 20
   }
  },
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
  "formula": "MAP-conditional posterior expected absolute deviation of the latent function: E_{f | y, eta_hat}[abs(f(t) - mu_theta(t))]",
  "formula_discrepancy_note": "The formal limits-note equation and Case D work order use absolute difference. A chat-derived Q&A in the same note says squared difference; this artifact follows the binding absolute formula.",
  "gp_hyperparameters_provenance": "run.py stores gp_hyperparameters once, immediately after the first successful configuration MAP fit. The default loop order starts with practitioner, so all 50 source files carry practitioner MAP values even though results_hmc subsequently runs HMC for GP samples.",
  "gp_reconstruction": "Exact zero-mean RBF GP conditioning at stored lengthscale, outputscale, and noise; no refit and no hyperparameter sampling; latent posterior function draws exclude fresh observation noise.",
  "legacy_metric_note": "Stored diagnostics contain pw_nll, pw_mse, and pw_hellinger. They predate W1 and contain no pw_kl_vcal. pw_nll weights squared error by candidate fitted noise variance; pw_kl_vcal weights it by GP variance.",
  "mean_based_plugin_formula": "Posterior-mean plug-in absolute deviation at the MAP point: abs(E[f(t) | y, eta_hat] - mu_theta(t))",
  "mean_vs_draw_substitution": "The limits-note target averages posterior mean functions over hyperparameter draws. The stored files do not retain those draws. This artifact reports both the MAP-conditional posterior expected absolute deviation of the latent function and a posterior-mean plug-in at the same stored MAP point.",
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
  "aggregation": "Pooled across subjects and posterior function draws for the MAP-conditional posterior expected absolute deviation of the latent function within each truth cohort",
  "estimand": "MAP-conditional posterior expected absolute deviation of the latent function",
  "lower_quantile": 0.1,
  "upper_quantile": 0.9
 },
 "regret_curves": {
  "exponential_truth": {
   "Exponential": {
    "atom_description": "Seeded latent function draw conditional on the stored MAP point",
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
    "estimand": "MAP-conditional posterior expected absolute deviation of the latent function",
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
    "n_atoms_per_subject": 100,
    "n_pooled_atoms_per_trial": 2500,
    "n_subjects": 25
   },
   "Power": {
    "atom_description": "Seeded latent function draw conditional on the stored MAP point",
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
    "estimand": "MAP-conditional posterior expected absolute deviation of the latent function",
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
    "n_atoms_per_subject": 100,
    "n_pooled_atoms_per_trial": 2500,
    "n_subjects": 25
   }
  },
  "power_truth": {
   "Exponential": {
    "atom_description": "Seeded latent function draw conditional on the stored MAP point",
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
    "estimand": "MAP-conditional posterior expected absolute deviation of the latent function",
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
    "n_atoms_per_subject": 100,
    "n_pooled_atoms_per_trial": 2500,
    "n_subjects": 25
   },
   "Power": {
    "atom_description": "Seeded latent function draw conditional on the stored MAP point",
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
    "estimand": "MAP-conditional posterior expected absolute deviation of the latent function",
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
    "n_atoms_per_subject": 100,
    "n_pooled_atoms_per_trial": 2500,
    "n_subjects": 25
   }
  }
 },
 "schema_version": 2,
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
 "stored_truth_raw_draw_wins": {
  "by_configuration": {
   "agnostic": {
    "exponential_truth": {
     "n_draws_per_subject": 100,
     "n_draws_total": 2500,
     "n_subjects": 25,
     "n_subjects_truth_exact_tie": 0,
     "n_subjects_truth_strict_majority": 25,
     "truth_candidate": "Exponential",
     "truth_raw_draw_win_fraction": 0.9208,
     "truth_raw_draw_wins": 2302
    },
    "power_truth": {
     "n_draws_per_subject": 100,
     "n_draws_total": 2500,
     "n_subjects": 25,
     "n_subjects_truth_exact_tie": 0,
     "n_subjects_truth_strict_majority": 9,
     "truth_candidate": "Power",
     "truth_raw_draw_win_fraction": 0.4148,
     "truth_raw_draw_wins": 1037
    }
   },
   "moderate": {
    "exponential_truth": {
     "n_draws_per_subject": 100,
     "n_draws_total": 2500,
     "n_subjects": 25,
     "n_subjects_truth_exact_tie": 0,
     "n_subjects_truth_strict_majority": 25,
     "truth_candidate": "Exponential",
     "truth_raw_draw_win_fraction": 0.9456,
     "truth_raw_draw_wins": 2364
    },
    "power_truth": {
     "n_draws_per_subject": 100,
     "n_draws_total": 2500,
     "n_subjects": 25,
     "n_subjects_truth_exact_tie": 1,
     "n_subjects_truth_strict_majority": 8,
     "truth_candidate": "Power",
     "truth_raw_draw_win_fraction": 0.3992,
     "truth_raw_draw_wins": 998
    }
   },
   "practitioner": {
    "exponential_truth": {
     "n_draws_per_subject": 100,
     "n_draws_total": 2500,
     "n_subjects": 25,
     "n_subjects_truth_exact_tie": 0,
     "n_subjects_truth_strict_majority": 25,
     "truth_candidate": "Exponential",
     "truth_raw_draw_win_fraction": 0.9868,
     "truth_raw_draw_wins": 2467
    },
    "power_truth": {
     "n_draws_per_subject": 100,
     "n_draws_total": 2500,
     "n_subjects": 25,
     "n_subjects_truth_exact_tie": 0,
     "n_subjects_truth_strict_majority": 9,
     "truth_candidate": "Power",
     "truth_raw_draw_win_fraction": 0.3896,
     "truth_raw_draw_wins": 974
    }
   }
  },
  "description": "Tau-free fraction of stored GP draws on which the known-truth candidate has the smaller raw G value",
  "metric": "pw_nll",
  "subject_majority_definition": "Strictly more than half of a subject's stored draws"
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