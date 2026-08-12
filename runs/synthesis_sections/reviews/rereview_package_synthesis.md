RE-REVIEW ROUND (rule 4) — synthesis fix pass 1, changed hunks only.
Branch paper/synthesis-sections; fix commit d6ee868 on top of reviewed tip 95d1259.
For EACH of YOUR OWN findings that entered the fix queue, judge from the changed hunks whether
the fix resolves it. Findings REJECTED in cross-check were deliberately NOT implemented — do
not re-litigate. Output per finding: 'REREVIEW-<ID>: RESOLVED' or 'REREVIEW-<ID>:
NOT-RESOLVED' plus 2-4 evidence lines; then any NEW defect introduced by the changed hunks
(hunks only; no scope expansion).

=== FIX DIFF (full) ===
diff --git a/Notes/DECISIONS.md b/Notes/DECISIONS.md
index 02aadc2..7c47b58 100644
--- a/Notes/DECISIONS.md
+++ b/Notes/DECISIONS.md
@@ -5754,8 +5754,9 @@ The verification paragraph reflects the completed case review archives. All
 four reviewer rounds are recorded for every case, with the fourth, Kimi K3, run
 at the author's direction on the same round-1 packages; the findings,
 refutations, fixes, and author sign-off records are committed under
-`runs/<case>/reviews/` in this repository. D65 records the D17 local
-methods-validation provenance exception, which Section 8 states explicitly.
+`runs/<case>/reviews/` in this repository. D65 records the provenance exception
+for the D17-recorded local methods-validation reach check, which Section 8
+states explicitly in the same terms.
 
 The case sections remain on their source branches and are cited at their
 assembled-manuscript paths: Case A from `paper/case-a-vanbork` at
diff --git a/docs/paper-sie-jmp/01-intro.md b/docs/paper-sie-jmp/01-intro.md
index 80a1d10..14255b9 100644
--- a/docs/paper-sie-jmp/01-intro.md
+++ b/docs/paper-sie-jmp/01-intro.md
@@ -58,9 +58,12 @@ inspectable distribution over data patterns.
 candidate predictions and integrating compatibility, without requiring a
 separate hand-specified parameter prior for every model.
 
-(iii) It subjects the machinery to four cases covering external validation,
-nested-model reference measures, a satisfied parameter constraint against
-PSIS-LOO, and calibration under known synthetic truth.[^intro-cases]
+(iii) It subjects the machinery to four cases. The first provides external
+validation of the induced-prior and soft-transfer computations against data
+priors supplied by other authors, which leaves the GP scaffold itself untested;
+the remaining three cover nested-model reference measures, a satisfied parameter
+constraint against PSIS-LOO, and calibration under known synthetic
+truth.[^intro-cases]
 
 (iv) It makes the evaluative choices explicit as dials rather than burying them
 in an implementation. Case B, section 4, jointly prices \(\tau\) and `occam`;
@@ -71,14 +74,18 @@ numerical \(\tau\) cannot support probability comparisons across differently
 scaled metrics.
 
 The cases produce deliberately mixed outcomes. Case A reproduces independent
-closed-form targets, validates a hybrid \(Z_M\) special case, and exposes the
-aggregation trade. Case B uses an `informative`-configuration, MAP-based
-methods-validation example to show that reference-volume normalization can
-change a nested-model comparison at finite temperature. Case C returns the
-important null: the table path gives an effective tie with a direction fixed by
-containment, while PSIS-LOO remains directionally inconclusive for the satisfied
-constraint. Case D remains synthetic-only; it contributes known-truth reference
-material and a metric-scale warning without claiming a real-data result or
+closed-form targets and validates a hybrid \(Z_M\) special case, though its
+examples insert the published data priors directly and therefore exercise the
+induced-prior and soft-transfer machinery without testing the GP scaffold. It
+also exposes the aggregation trade, because the canonical pooled convention does
+not reproduce the non-overlapping target that the per-draw routes recover. Case
+B uses an `informative`-configuration, MAP-based methods-validation example to
+show that reference-volume normalization can change a nested-model comparison at
+finite temperature. Case C returns the important null: the table path gives an
+effective tie with a direction fixed by containment, while PSIS-LOO remains
+directionally inconclusive for the satisfied constraint. Case D remains
+synthetic-only; it contributes known-truth reference material and a
+metric-scale warning without claiming a real-data result or
 setting an inadequacy threshold.[^intro-cases]
 
 [^intro-special]: 🟢 peer-reviewed — Myung, Forster, and Browne (2000) and Wagenmakers and Waldorp (2006), earlier *Journal of Mathematical Psychology* special-issue contributions on model selection and evaluation.
diff --git a/docs/paper-sie-jmp/02-machinery.md b/docs/paper-sie-jmp/02-machinery.md
index e6521db..4e0eb9a 100644
--- a/docs/paper-sie-jmp/02-machinery.md
+++ b/docs/paper-sie-jmp/02-machinery.md
@@ -30,11 +30,16 @@ enters the account here.
 For a candidate family, projection fits the candidate instance that minimizes
 \(G(\psi,\theta)\) for each sampled pattern. Under `pw_kl_vcal`, the candidate
 variance is calibrated to the GP pattern, so the parameter-dependent part of
-the divergence reduces to variance-weighted squared error. Gaussian MLE refits
-and direct minimization of `pw_kl_vcal` therefore agree in the prior-only
-mechanism check. The collection of fitted instances should be read as samples
-from the pushforward of \(p_0(\psi)\) through this projection, not as draws from
-a separately elicited within-model parameter prior.[^machinery-projection]
+the divergence reduces to variance-weighted squared error. When a drawn pattern
+carries one scalar noise variance shared across the evaluation locations, that
+weight factors out of the minimization, and the variance-calibrated argmin
+coincides with the Gaussian maximum-likelihood refit. The correspondence holds
+algebraically rather than as a sampled regularity. Where the pattern variance
+varies across locations, the weights no longer factor out and the two
+projections separate. The collection of fitted instances should be read as
+samples from the pushforward of \(p_0(\psi)\) through this projection, not as
+draws from a separately elicited within-model parameter
+prior.[^machinery-projection]
 
 Model-level induction averages before integrating. For candidate parameters
 \(\phi\), \(\bar G(\phi)\) averages \(G\) across data patterns, and
@@ -43,6 +48,19 @@ Model-level induction averages before integrating. For candidate parameters
 Z_M = \int \exp\{-\bar G(\phi)/\tau\}\,d\phi.
 \]
 
+The implementation reaches that average by moment matching rather than by
+averaging per-draw divergences. It first collapses the sampled patterns into a
+single averaged pattern \(\bar\psi\), whose mean equals the weighted mean of the
+per-draw means and whose covariance adds a between-draw mean-spread term to the
+weighted average of the per-draw covariances, and then evaluates \(G\) once
+against \(\bar\psi\). The computed object therefore reports the divergence from
+\(\bar\psi\) rather than the mean of the per-draw divergences, and the
+discrepancy between them varies with \(\phi\), so it does not cancel from a
+normalized comparison across candidates. Take the notation's "averaged across
+data patterns" gloss as the intended reading of \(\bar G(\phi)\) and the
+moment-matched evaluation as the estimator of it used
+throughout.[^machinery-gbar]
+
 With `occam=False`, the integral uses raw Lebesgue measure, which follows the
 canonical BI* convention. With `occam=True`, division by \(V_{\mathrm{ref}}\)
 changes the reference measure from total compatible volume to average
@@ -62,10 +80,18 @@ p(\theta\mid y) \propto
 \sum_i \exp\{-G(\psi_i,\theta)/\tau\}.
 \]
 
-Small \(\tau\) concentrates credit on the best matches and recovers hard
-best-match assignment in the limiting case; larger \(\tau\) spreads credit
-across candidates. Temperature must therefore be swept and reported, not fixed
-silently.
+Small \(\tau\) concentrates credit on the best matches, and larger \(\tau\)
+spreads it across candidates. The low-temperature limit itself depends on the
+aggregation convention set out below rather than on temperature alone. As
+\(\tau\) approaches zero under pooled aggregation, the sum concentrates on the
+globally smallest divergences across all draws, so draws whose best available
+match remains poor contribute negligible support. The per-draw conventions
+defined below, row-min and expected-posterior, instead resolve each draw
+separately, and where a draw has a unique closest candidate they recover hard
+best-match assignment within that draw, so their low-temperature limit reflects
+the rate at which candidates attain their draw's smallest divergence.
+Temperature must therefore be swept and reported together with the convention,
+not fixed silently.
 
 Aggregation supplies a third dial. Pooled aggregation preserves the absolute
 support contributed by each pattern and normalizes only after summing. The
@@ -80,27 +106,41 @@ The D60 Resolution adopts aggregation as an explicit evaluation dial.
 Canonical reporting uses pooled aggregation to preserve absolute divergence
 magnitudes, the M-open signal, and continuity with the validated results.
 Expected-posterior aggregation accompanies it wherever external correspondence
-with Eq. 4 matters. Neither convention receives a universal-correctness claim;
+with Eq. 4 matters. Canonical pooled reporting carries an explicit price: pooled
+aggregation does not reproduce Case A's Target A, which the per-draw routes
+recover, and the dial records that failure rather than absorbing it into a
+silent default. Neither convention receives a universal-correctness claim;
 Case A, section 3, reports the cost of each choice.[^machinery-aggregation]
 
-**Remark 1 (one-sidedness under nested candidate regions).** Let
-\(M_r\subset M_e\) and evaluate both candidates by their best-instance
-divergence from each shared data pattern. For every draw \(\psi\),
+**Remark 1 (one-sidedness under nested candidate regions).** Score a candidate
+family \(M\) on draw \(\psi_i\) by its best available match,
+
+\[
+G_i(M)=\min_{\theta\in M}G(\psi_i,\theta)
+=\min_{q\in\mathcal{P}(M)}G(\psi_i,q),
+\]
+
+where \(\mathcal{P}(M)\) collects the predictive distributions the family can
+reach as \(\theta\) ranges over its parameters. Stating the score through the
+reachable set, rather than through containment of parameter vectors, admits an
+embedded restriction that carries fewer parameters than its encompassing
+family: nesting requires only \(\mathcal{P}(M_r)\subseteq\mathcal{P}(M_e)\), and
+the two parameter spaces may then have unequal dimension. Whenever that
+containment holds, minimizing over the larger set cannot return a larger value,
+so for every draw
 
 \[
-\min_{\theta\in M_e}G(\psi,\theta)
-\leq
-\min_{\theta\in M_r}G(\psi,\theta).
+G_i(M_e)\leq G_i(M_r).
 \]
 
-The inequality follows from feasible-set containment, not from a sampled
-regularity. Every aggregation convention above preserves the per-draw ordering,
-so table-path aggregation can never favor the restriction at any \(\tau\) under
-any convention; only the gap magnitude is empirical. Consequently, crediting a
-satisfied restriction belongs to the \(Z_M\) side, where the volume or
-reference-measure term controlled by `occam` can reward the restricted region,
-not to the table path. Cases B and C, sections 4 and 5, provide the complementary
-worked instances.[^machinery-nesting]
+The inequality follows from reachable-set containment, not from a sampled
+regularity. Under any of the three conventions above, each of which is monotone
+in the per-draw scores, table-path aggregation preserves that ordering and can
+never favor the restriction at any \(\tau\); only the gap magnitude is
+empirical. Consequently, crediting a satisfied restriction belongs to the
+\(Z_M\) side, where the volume or reference-measure term controlled by `occam`
+can reward the restricted region, not to the table path. Cases B and C, sections
+4 and 5, provide the complementary worked instances.[^machinery-nesting]
 
 ## 2.4 Metric roles and scale discipline
 
@@ -136,8 +176,9 @@ affine rescaling and separates ordering from temperature-dependent sharpness.
 Case D supplies the worked instance.[^machinery-scale]
 
 [^machinery-foundations]: 🟢 peer-reviewed — Chandramouli and Shiffrin (2016), “Extending Bayesian induction,” *Journal of Mathematical Psychology*, 72, 38–42; Shiffrin, Chandramouli, and Grünwald (2016), “Bayes factors, relations to minimum description length, and overlapping model classes,” *Journal of Mathematical Psychology*, 72, 56–77.
-[^machinery-construction]: 🟠 empirical — `bistar_gp/config.py` and the prior-only arm of `experiments/mechanism_figure_poster.py`; the latter serves construction visualization and methods validation, not posterior inference.
-[^machinery-projection]: 🟠 empirical — the draw-for-draw projection check implemented in `experiments/mechanism_figure_poster.py`; conceptual account in `kb/Wiki/GP-Induced Model Priors.md`.
+[^machinery-construction]: 🟠 empirical — `bistar_gp/config.py`; the prior-only arm of `experiments/mechanism_figure_poster.py`, local methods material that remains uncommitted in this repository, serves construction visualization and supplies no reported number or posterior estimate.
+[^machinery-projection]: 🟠 empirical — the `pw_kl_vcal` definition in `bistar_gp/metrics_v2.py`, from which the shared-scalar-variance coincidence of the two projections follows algebraically; conceptual account in `kb/Wiki/GP-Induced Model Priors.md`.
+[^machinery-gbar]: 🟠 empirical — `bistar_gp/aggregation_v3.py`, whose `average_gp_posterior` forms the weighted mean and the covariance carrying the between-draw mean-spread term, and `bistar_gp/laplace_evidence.py`, whose `compute_G_at_params` evaluates the divergence against that averaged pattern.
 [^machinery-occam]: 🟠 empirical — assembled-manuscript section 4 on `paper/case-b-occam-dial`; `experiments/occam_dial_figure.py`; `experiments/e6_nesting_monotonicity.py`; `runs/occam_dial/`; Notes/DECISIONS.md D17 and D62.
 [^machinery-aggregation]: 🟠 empirical — `experiments/vanbork_external_validation.py`; `runs/vanbork_external_validation/`; `experiments/e7_convention_sensitivity.py`; `runs/e7_convention_sensitivity/`; Notes/DECISIONS.md D60 Resolution and Precision addenda, and D61.
 [^machinery-nesting]: 🟠 empirical — assembled-manuscript sections 4 and 5 on the Case B and Case C branches; `runs/occam_dial/e6_results.json`; `runs/haaf_nested_constraint/results.json`; Notes/DECISIONS.md D62 and D63.
@@ -147,8 +188,11 @@ Case D supplies the worked instance.[^machinery-scale]
 
 ---
 *Provenance: no empirical estimate is re-quoted in this section.
-Construction and projection: `bistar_gp/config.py` · the prior-only mechanism
-and projection-check arms of `experiments/mechanism_figure_poster.py`.
+Construction, projection, and the averaged-pattern evaluation of \(\bar G\):
+`bistar_gp/config.py`, `bistar_gp/metrics_v2.py`, `bistar_gp/aggregation_v3.py`,
+and `bistar_gp/laplace_evidence.py` · the prior-only mechanism arm of
+`experiments/mechanism_figure_poster.py`, cited as uncommitted local methods
+material for construction visualization only.
 Aggregation: `runs/vanbork_external_validation/` and
 `runs/e7_convention_sensitivity/` ·
 `experiments/vanbork_external_validation.py` and
diff --git a/docs/paper-sie-jmp/08-discussion.md b/docs/paper-sie-jmp/08-discussion.md
index 56f461e..35f3ad6 100644
--- a/docs/paper-sie-jmp/08-discussion.md
+++ b/docs/paper-sie-jmp/08-discussion.md
@@ -13,15 +13,17 @@ the convention.[^discussion-dials]
 
 Case A prices aggregation most directly. Expected-posterior aggregation obtains
 external correspondence with van Bork, Romeijn, and Wagenmakers, while pooled
-aggregation retains absolute divergence magnitudes needed for an M-open
-reading. The same case gives the hybrid \(Z_M\) construction a passing
-shared-family special-case test. Case B then shows how \(\tau\) and `occam`
-interact in nested comparisons: low temperature emphasizes best achievable
-divergence, while reference-volume normalization can permit a finite-temperature
-simplicity preference. Case C shows that changing \(\tau\) or the table-path
-aggregation cannot reverse containment. Case D adds the scale qualification:
-temperature has meaning only relative to the scale of \(G\), so comparisons
-across metrics require tau-free draw-win fractions alongside soft probabilities.[^discussion-dials]
+aggregation retains absolute divergence magnitudes needed for an M-open reading
+yet does not reproduce their non-overlapping target, and naming aggregation as a
+dial states that price instead of concealing it. The same case gives the hybrid
+\(Z_M\) construction a passing shared-family special-case test. Case B then
+shows how \(\tau\) and `occam` interact in nested comparisons: low temperature
+emphasizes best achievable divergence, while reference-volume normalization can
+permit a finite-temperature simplicity preference. Case C shows that changing
+\(\tau\) or the table-path aggregation cannot reverse containment. Case D adds
+the scale qualification: temperature has meaning only relative to the scale of
+\(G\), so comparisons across metrics require tau-free draw-win fractions
+alongside soft probabilities.[^discussion-dials]
 
 The bridge from Case B to Case C resolves an apparent tension. Case C shows
 that neither the table path nor LOO credits a satisfied constraint in its
@@ -57,8 +59,10 @@ The relation to elpd and PSIS-LOO concerns shared operations rather than an
 identity of inferential targets. Both traditions use pointwise predictive
 evaluation and can use importance weighting over posterior draws. PSIS-LOO
 fits each candidate with its own parameter prior and estimates held-out
-predictive accuracy; its importance ratios approximate leave-one-out
-posteriors, with Pareto smoothing diagnosing unstable ratios. BMS*-GP instead
+predictive accuracy: reweighting its posterior draws by the importance ratios
+approximates each leave-one-out predictive quantity, a generalized Pareto fit to
+the largest of those ratios stabilizes them, and the fitted shape estimate flags
+cases where the approximation becomes unreliable. BMS*-GP instead
 evaluates all candidates against shared data patterns \(\psi\), uses
 `pw_kl_vcal` as the primary divergence, and reserves within-model priors for an
 explicit hybrid extension. Its target concerns proximity to a common
@@ -110,8 +114,10 @@ The method moves judgment into the data prior, kernel, metric, temperature,
 reference measure, and aggregation rule. These choices become visible and
 testable, but they still require substantive knowledge. When beliefs about a
 bias process come largely from outside the observed data, additional sample
-size need not remove the associated uncertainty; honest inference can retain an
-uncertainty floor.
+size need not remove the associated uncertainty, and honest inference can retain
+an uncertainty floor. That expectation belongs to the program rather than to
+any of the four cases reported here; section 7 develops the debiasing
+construction that makes it concrete.[^discussion-floor]
 
 Two scope conditions follow from Case D. Under F1, the GP scaffold may fail to
 represent the feature that distinguishes the candidates, so comparison reflects
@@ -121,21 +127,23 @@ so no scoring rule can recover information that the data do not contain. The
 synthetic case could not identify which mechanism produced its asymmetry, and
 its deviation curves covered only part of the region used by the stored
 aggregate scores. BMS*-GP should therefore report scaffold checks, local
-deviation diagnostics, and the possibility of unresolved F1/F2
-non-identifiability rather than treating every weak separation as a demand for
-a sharper posterior.[^discussion-limits]
+deviation diagnostics, and the possibility that a weak separation remains
+unresolved across all four sources Case D leaves open, namely F1
+representability, F2 mimicry, metric behavior, and sampling noise, rather than
+treating every weak separation as a demand for a sharper
+posterior.[^discussion-limits]
 
 ## 8.6 Verification and reproducibility
 
 Every reported number has a named regenerating `experiments/` script and a
-corresponding `runs/` artifact; D17 records the provenance exception for the
-local methods-validation reach check. Each case section underwent independent
-review within a four-model adversarial cross-verification protocol. All four
-reviewer rounds are recorded for every case, with the fourth, Kimi K3, run at
-the author's direction on the same round-1 packages. The findings, refutations,
-fixes, and author sign-off records are committed under `runs/<case>/reviews/`
-in this repository, and the corresponding `Notes/DECISIONS.md` entry records
-the review outcome.[^discussion-repro]
+corresponding `runs/` artifact; D65 records the provenance exception for the
+D17-recorded local methods-validation reach check. Each case section underwent
+independent review within a four-model adversarial cross-verification protocol.
+All four reviewer rounds are recorded for every case, with the fourth, Kimi K3,
+run at the author's direction on the same round-1 packages. The findings,
+refutations, fixes, and author sign-off records are committed under
+`runs/<case>/reviews/` in this repository, and the corresponding
+`Notes/DECISIONS.md` entry records the review outcome.[^discussion-repro]
 
 [^discussion-dials]: 🟠 empirical — assembled-manuscript sections 3–6 and their case artifacts: `runs/vanbork_external_validation/`, `runs/e7_convention_sensitivity/`, `runs/occam_dial/`, `runs/haaf_nested_constraint/`, and `runs/regret_curves_mopen/`; Notes/DECISIONS.md D60–D64.
 [^discussion-bridge]: 🟠 empirical — assembled-manuscript sections 4 and 5 on `paper/case-b-occam-dial` and `paper/case-c-haaf`; `runs/occam_dial/e6_results.json`; `runs/haaf_nested_constraint/results.json`; Notes/DECISIONS.md D62 and D63.
@@ -144,6 +152,7 @@ the review outcome.[^discussion-repro]
 [^discussion-loo-case]: 🟠 empirical — `experiments/haaf_nested_constraint.py`; `runs/haaf_nested_constraint/results.json` and `README.md`; Notes/DECISIONS.md D63. 🟢 peer-reviewed — Haaf, Klaassen, and Rouder (2025), “Bayes factor vs. posterior predictive model assessment: Insights from ordinal constraints,” *Computational Brain & Behavior*.
 [^discussion-hybrid]: 🟠 empirical — assembled-manuscript section 3 on `paper/case-a-vanbork`; `experiments/vanbork_external_validation.py`; `runs/vanbork_external_validation/results.json`; Notes/DECISIONS.md D60 Resolution and Precision addenda.
 [^discussion-limits]: 🟠 empirical — assembled-manuscript section 6; `experiments/regret_curves_mopen.py`; `runs/regret_curves_mopen/`; Notes/DECISIONS.md D64.
+[^discussion-floor]: 🟠 empirical — assembled-manuscript section 7, `docs/paper-sie-jmp/07-debias-bridge.md`, which develops the debiasing bridge and refers the full treatment to the companion paper and thesis chapter 5; none of the four cases reported here estimates an uncertainty floor.
 [^discussion-repro]: 🟠 empirical — case review archives under `runs/vanbork_external_validation/reviews/`, `runs/occam_dial/reviews/`, `runs/haaf_nested_constraint/reviews/`, and `runs/regret_curves_mopen/reviews/`; corresponding review outcomes in Notes/DECISIONS.md D62–D65.
 
 ---
