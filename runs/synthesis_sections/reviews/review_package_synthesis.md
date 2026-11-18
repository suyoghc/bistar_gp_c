Review the attached branch diff for the BI*/BMS*-GP paper SYNTHESIS package
(sections 1, 2, 8 — intro, machinery, discussion). Verdict: APPROVE or REVISE.
Findings as a numbered list:
[severity S1-S4] [file:line] claim — why it is wrong — concrete fix.
Check specifically: (1) constraint compliance [the §0 list below]; (2) every
numeral in the sections (the package's stated policy: NO re-quoted empirical
estimates — identifiers, notation, and bibliography only; flag any violation);
(3) statistical correctness of Remark 1, the scale-invariance warning, the
B-to-C bridge, and every methodological claim; (4) prose style rules; (5)
consistency with the four case sections (provided below) — the synthesis must
not claim more than the cases established. Do not propose scope expansions.

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

DRIVER-VERIFIED FACTS (do not report as findings):
- Writing-only package; commit = the three sections + D66; the four case
  sections are committed on their own branches (A 76135be, B 32c0a58,
  C 0adde90, D ff4c353) and appear IN FULL below for consistency checking;
  cross-references to sections 3-6 anticipate the merged manuscript.
- All four Kimi K3 reviewer rounds are COMPLETE (2026-08-12, author-directed,
  committed in each case's reviews dir); the D62-D65 addenda that say
  "pending" are dated records predating those commits; the synthesis prose
  states the completed status correctly.
- The D60 fork is RESOLVED (aggregation as an explicit evaluation dial;
  pooled canonical; D60 Resolution addendum on the case-a branch).
- kb/ is gitignored; kb citations ground arguments, never numbers.

=== SECTION 01 (this branch) ===
# 1. Introduction

## 1.1 Data priors and the model-evaluation problem

This contribution enters the third *Journal of Mathematical Psychology*
special issue devoted to statistical model evaluation, following the
collections associated with Myung, Forster, and Browne and with Wagenmakers and
Waldorp.[^intro-special] Across those collections, the recurring problem has
not been a shortage of scoring rules. The harder question concerns what a score
should evaluate when scientific models overlap, approximate rather than contain
the data-generating process, or earn good fit through flexibility. The present
paper answers by taking possible data patterns, rather than separately chosen
parameter priors, as the common reference for evaluation.

That choice continues the data-prior program introduced in the JMP contributions
by Chandramouli and Shiffrin and by Shiffrin, Chandramouli, and Grünwald.[^intro-foundations]
Their BI* table assigns prior probability to data patterns \(\psi\), updates
those patterns after observing data, and derives model evaluation from their
relation to candidate predictions. A data prior therefore provides the
through-line from the original finite table to the present Gaussian-process
implementation. GP hyperpriors construct \(p_0(\psi)\) over a continuous family
of plausible patterns; projection transfers that belief to candidate instances;
and integration or soft transfer produces model-level quantities without a
hand-specified parameter prior for every candidate.

This reallocation of judgment does not remove prior choice. It asks the analyst
to state beliefs about observable regularity, variation, trend, and noise in a
shared scaffold. Those choices can be inspected through prior predictive
patterns and applied consistently to every candidate. The resulting comparison
addresses how well each candidate approximates a common posterior over data
patterns, rather than how well separately equipped Bayesian models predict
under different within-model priors.

## 1.2 Fit propensity over a weighted data space

Bonifay and Cai's fit-propensity program supplies a particularly close point of
contact. Fit propensity evaluates how readily a model attains good fit over
possible data, so observed fit cannot be interpreted apart from the range of
patterns a model can accommodate.[^intro-fit] The present construction shares
that data-space orientation but replaces an undifferentiated set of possible
data with \(p_0(\psi)\), a scientifically weighted distribution. It also makes
the evaluative consequences explicit: \(G\) defines relevant predictive
similarity, \(\tau\) controls the softness of credit, `occam` selects the
reference measure for \(Z_M\), and aggregation determines whether absolute
inadequacy remains visible. Fit propensity and data priors thus ask compatible
questions about model behavior before a single observed-data fit receives an
evidential interpretation.

## 1.3 Contributions and case-study plan

The paper makes four contributions.

(i) It constructs a stand-alone data prior \(p_0(\psi)\) from GP kernel
hyperpriors, replacing enumeration of the BI* table with a continuous and
inspectable distribution over data patterns.

(ii) It induces parameter and model priors by projecting those patterns onto
candidate predictions and integrating compatibility, without requiring a
separate hand-specified parameter prior for every model.

(iii) It subjects the machinery to four cases covering external validation,
nested-model reference measures, a satisfied parameter constraint against
PSIS-LOO, and calibration under known synthetic truth.[^intro-cases]

(iv) It makes the evaluative choices explicit as dials rather than burying them
in an implementation. Case B, section 4, jointly prices \(\tau\) and `occam`;
Case A, section 3, prices aggregation against external correspondence and the
retention of absolute divergence; Case C, section 5, shows what follows when the
table path has no volume term; and Case D, section 6, establishes why a shared
numerical \(\tau\) cannot support probability comparisons across differently
scaled metrics.

The cases produce deliberately mixed outcomes. Case A reproduces independent
closed-form targets, validates a hybrid \(Z_M\) special case, and exposes the
aggregation trade. Case B uses an `informative`-configuration, MAP-based
methods-validation example to show that reference-volume normalization can
change a nested-model comparison at finite temperature. Case C returns the
important null: the table path gives an effective tie with a direction fixed by
containment, while PSIS-LOO remains directionally inconclusive for the satisfied
constraint. Case D remains synthetic-only; it contributes known-truth reference
material and a metric-scale warning without claiming a real-data result or
setting an inadequacy threshold.[^intro-cases]

[^intro-special]: 🟢 peer-reviewed — Myung, Forster, and Browne (2000) and Wagenmakers and Waldorp (2006), earlier *Journal of Mathematical Psychology* special-issue contributions on model selection and evaluation.
[^intro-foundations]: 🟢 peer-reviewed — Chandramouli and Shiffrin (2016), “Extending Bayesian induction,” *Journal of Mathematical Psychology*, 72, 38–42; Shiffrin, Chandramouli, and Grünwald (2016), “Bayes factors, relations to minimum description length, and overlapping model classes,” *Journal of Mathematical Psychology*, 72, 56–77.
[^intro-fit]: 🟢 peer-reviewed — Bonifay and Cai (2017), “On the complexity of item response theory models,” *Multivariate Behavioral Research*, 52(4), 465–484.
[^intro-cases]: 🟠 empirical — assembled-manuscript sections 3–6, read from the case branches at `docs/paper-sie-jmp/03-case-A-external-validation.md`, `docs/paper-sie-jmp/04-case-B-occam-dial.md`, `docs/paper-sie-jmp/05-case-C-nested-constraints.md`, and `docs/paper-sie-jmp/06-case-D-mopen-calibration.md`; supporting artifacts and decisions are listed in the provenance footer below.

---
*Provenance: no empirical estimate is re-quoted in this section. Case-result
summaries draw on `runs/vanbork_external_validation/` and
`runs/e7_convention_sensitivity/` · `experiments/vanbork_external_validation.py`
and `experiments/e7_convention_sensitivity.py` · Notes/DECISIONS.md D60, D61;
`runs/occam_dial/` · `experiments/occam_dial_figure.py` and
`experiments/e6_nesting_monotonicity.py` · D62;
`runs/haaf_nested_constraint/` · `experiments/haaf_nested_constraint.py` · D63;
`runs/regret_curves_mopen/` · `experiments/regret_curves_mopen.py` · D64.
Argument provenance: `kb/Wiki/BI-star Framework.md`,
`kb/Wiki/Data Priors Citation Landscape.md`, and
`kb/Wiki/Paper Writing Guide.md`.*


=== SECTION 02 (this branch) ===
# 2. Machinery

## 2.1 From the BI* table to a GP data prior

The BI* table begins with possible data patterns \(\psi\) as rows and possible
observations as columns. A row carries prior weight \(p_0(\psi)\); observing a
column updates the row weights by Bayes' rule. Candidate models enter only after
that data-space update, through the predictive patterns they can reproduce.
Figure 1 of the foundational JMP account gives the finite construction.[^machinery-foundations]

A Gaussian process replaces enumeration with a generative data prior. Draw the
kernel hyperparameters, draw a function conditional on them, and combine that
function with observation variance to obtain one \(\psi\). Repetition induces
\(p_0(\psi)\). The squared-exponential plus linear construction uses four
positive hyperparameters with direct qualitative interpretations: \(\ell\)
controls the scale over which nonlinear variation remains smooth,
\(\sigma^2_{SE}\) controls the amplitude of that smooth variation,
\(\sigma^2_b\) controls the strength of linear trend, and \(\sigma^2_y\)
controls observation-scale variation. Gamma hyperpriors in the prior-only
mechanism illustration make those beliefs inspectable before data enter.[^machinery-construction]

The mechanism illustration has an `informative`-configuration,
prior-predictive methods-validation role. It explains the construction rather
than supplying a paper-facing posterior estimate. Each case states its own GP
configuration and inferential path; no `informative`-configuration HMC result
enters the account here.

## 2.2 Projection, induced priors, and \(Z_M\)

For a candidate family, projection fits the candidate instance that minimizes
\(G(\psi,\theta)\) for each sampled pattern. Under `pw_kl_vcal`, the candidate
variance is calibrated to the GP pattern, so the parameter-dependent part of
the divergence reduces to variance-weighted squared error. Gaussian MLE refits
and direct minimization of `pw_kl_vcal` therefore agree in the prior-only
mechanism check. The collection of fitted instances should be read as samples
from the pushforward of \(p_0(\psi)\) through this projection, not as draws from
a separately elicited within-model parameter prior.[^machinery-projection]

Model-level induction averages before integrating. For candidate parameters
\(\phi\), \(\bar G(\phi)\) averages \(G\) across data patterns, and

\[
Z_M = \int \exp\{-\bar G(\phi)/\tau\}\,d\phi.
\]

With `occam=False`, the integral uses raw Lebesgue measure, which follows the
canonical BI* convention. With `occam=True`, division by \(V_{\mathrm{ref}}\)
changes the reference measure from total compatible volume to average
compatible density. The flag therefore encodes a substantive position on how
parameter-region volume should affect a model prior; it does not merely select
a numerical correction. Case B, section 4, demonstrates that consequence under
the required `informative`-configuration, MAP-based methods-validation
framing.[^machinery-occam]

## 2.3 Soft transfer, temperature, and aggregation

Soft transfer retains per-pattern variation rather than averaging first. Under
pooled aggregation,

\[
p(\theta\mid y) \propto
\sum_i \exp\{-G(\psi_i,\theta)/\tau\}.
\]

Small \(\tau\) concentrates credit on the best matches and recovers hard
best-match assignment in the limiting case; larger \(\tau\) spreads credit
across candidates. Temperature must therefore be swept and reported, not fixed
silently.

Aggregation supplies a third dial. Pooled aggregation preserves the absolute
support contributed by each pattern and normalizes only after summing. The
row-min convention subtracts each pattern's smallest divergence before the
same pooled normalization. Expected-posterior aggregation first normalizes
candidate support within each pattern and then averages, matching Eq. 4 of van
Bork, Romeijn, and Wagenmakers. Per-pattern normalization spends equal total
credit on a pattern even when every candidate fits poorly, whereas pooled
aggregation retains that absolute inadequacy information.

The D60 Resolution adopts aggregation as an explicit evaluation dial.
Canonical reporting uses pooled aggregation to preserve absolute divergence
magnitudes, the M-open signal, and continuity with the validated results.
Expected-posterior aggregation accompanies it wherever external correspondence
with Eq. 4 matters. Neither convention receives a universal-correctness claim;
Case A, section 3, reports the cost of each choice.[^machinery-aggregation]

**Remark 1 (one-sidedness under nested candidate regions).** Let
\(M_r\subset M_e\) and evaluate both candidates by their best-instance
divergence from each shared data pattern. For every draw \(\psi\),

\[
\min_{\theta\in M_e}G(\psi,\theta)
\leq
\min_{\theta\in M_r}G(\psi,\theta).
\]

The inequality follows from feasible-set containment, not from a sampled
regularity. Every aggregation convention above preserves the per-draw ordering,
so table-path aggregation can never favor the restriction at any \(\tau\) under
any convention; only the gap magnitude is empirical. Consequently, crediting a
satisfied restriction belongs to the \(Z_M\) side, where the volume or
reference-measure term controlled by `occam` can reward the restricted region,
not to the table path. Cases B and C, sections 4 and 5, provide the complementary
worked instances.[^machinery-nesting]

## 2.4 Metric roles and scale discipline

Joint divergences compare the full GP predictive covariance with the
candidate's joint predictive covariance. That comparison can make structural
covariance mismatch dominate the mean-pattern question of interest. Pointwise
metrics instead compare marginal predictions at each evaluation location.
Following W1, `pw_kl_vcal` provides the primary metric: variance calibration
reduces it to GP-uncertainty-weighted squared error. The full joint
`kl_forward` remains an appendix-only stress metric.[^machinery-metrics]

D61 sharpens the appendix attribution. The observed `kl_forward` fragility
arises largely from pooled aggregation's sensitivity to outlying predictive
draws rather than from the metric alone. Appendix reporting should therefore
pair its pooled soft-transfer result with the aggregation convention and a
draw-level diagnostic, rather than treating a collapsed pooled weight as an
unqualified metric verdict.[^machinery-attribution]

**SCALE-INVARIANCE WARNING.** Soft-transfer probability magnitudes cannot be
compared across metrics at a shared numerical \(\tau\). Even under a common
positive affine rescaling of \(G\), the multiplicative scale changes the
effective temperature and can make the normalized probabilities arbitrarily
sharp or diffuse without changing the underlying within-draw ordering. Case D,
section 6, exhibits an exact candidate-specific affine identity between two
stored metrics and shows why a common temperature does not repair their scale
difference.[^machinery-scale]

Reporting must therefore compare probabilities within a metric, over a stated
\(\tau\) sweep. Every soft-transfer table should also report tau-free draw-win
fractions: the fraction of data-pattern draws on which each candidate attains
the smallest \(G\). That statistic remains invariant under a common positive
affine rescaling and separates ordering from temperature-dependent sharpness.
Case D supplies the worked instance.[^machinery-scale]

[^machinery-foundations]: 🟢 peer-reviewed — Chandramouli and Shiffrin (2016), “Extending Bayesian induction,” *Journal of Mathematical Psychology*, 72, 38–42; Shiffrin, Chandramouli, and Grünwald (2016), “Bayes factors, relations to minimum description length, and overlapping model classes,” *Journal of Mathematical Psychology*, 72, 56–77.
[^machinery-construction]: 🟠 empirical — `bistar_gp/config.py` and the prior-only arm of `experiments/mechanism_figure_poster.py`; the latter serves construction visualization and methods validation, not posterior inference.
[^machinery-projection]: 🟠 empirical — the draw-for-draw projection check implemented in `experiments/mechanism_figure_poster.py`; conceptual account in `kb/Wiki/GP-Induced Model Priors.md`.
[^machinery-occam]: 🟠 empirical — assembled-manuscript section 4 on `paper/case-b-occam-dial`; `experiments/occam_dial_figure.py`; `experiments/e6_nesting_monotonicity.py`; `runs/occam_dial/`; Notes/DECISIONS.md D17 and D62.
[^machinery-aggregation]: 🟠 empirical — `experiments/vanbork_external_validation.py`; `runs/vanbork_external_validation/`; `experiments/e7_convention_sensitivity.py`; `runs/e7_convention_sensitivity/`; Notes/DECISIONS.md D60 Resolution and Precision addenda, and D61.
[^machinery-nesting]: 🟠 empirical — assembled-manuscript sections 4 and 5 on the Case B and Case C branches; `runs/occam_dial/e6_results.json`; `runs/haaf_nested_constraint/results.json`; Notes/DECISIONS.md D62 and D63.
[^machinery-metrics]: 🟢 peer-reviewed — Gneiting and Raftery (2007), “Strictly proper scoring rules, prediction, and estimation,” *JASA*, 102(477), 359–378; Varin, Reid, and Firth (2011), “An overview of composite likelihood methods,” *Statistica Sinica*, 21, 5–42. W1 fixes the manuscript roles of `pw_kl_vcal` and `kl_forward`.
[^machinery-attribution]: 🟠 empirical — `experiments/e7_convention_sensitivity.py`; `runs/e7_convention_sensitivity/results.json` and `README.md`; Notes/DECISIONS.md D61.
[^machinery-scale]: 🟠 empirical — assembled-manuscript section 6 on `paper/case-d-mopen`; `experiments/regret_curves_mopen.py`; `runs/regret_curves_mopen/results.json`; Notes/DECISIONS.md D64.

---
*Provenance: no empirical estimate is re-quoted in this section.
Construction and projection: `bistar_gp/config.py` · the prior-only mechanism
and projection-check arms of `experiments/mechanism_figure_poster.py`.
Aggregation: `runs/vanbork_external_validation/` and
`runs/e7_convention_sensitivity/` ·
`experiments/vanbork_external_validation.py` and
`experiments/e7_convention_sensitivity.py` · D60, D61.
Nesting and metric scale: `runs/occam_dial/`,
`runs/haaf_nested_constraint/`, and `runs/regret_curves_mopen/` ·
`experiments/e6_nesting_monotonicity.py`,
`experiments/haaf_nested_constraint.py`, and
`experiments/regret_curves_mopen.py` · D62, D63, D64.*


=== SECTION 08 (this branch) ===
# 8. Discussion

## 8.1 The three evaluation dials, revisited

The cases replace a single model-probability answer with an auditable set of
evaluative choices. Temperature controls how strongly small divergences
dominate. The `occam` flag controls whether \(Z_M\) integrates total compatible
volume or normalizes by \(V_{\mathrm{ref}}\). Aggregation controls whether
data-pattern draws contribute according to their absolute support or spend
equal total credit after within-draw normalization. Each choice changes the
question being answered, so sensitivity analysis cannot substitute for naming
the convention.[^discussion-dials]

Case A prices aggregation most directly. Expected-posterior aggregation obtains
external correspondence with van Bork, Romeijn, and Wagenmakers, while pooled
aggregation retains absolute divergence magnitudes needed for an M-open
reading. The same case gives the hybrid \(Z_M\) construction a passing
shared-family special-case test. Case B then shows how \(\tau\) and `occam`
interact in nested comparisons: low temperature emphasizes best achievable
divergence, while reference-volume normalization can permit a finite-temperature
simplicity preference. Case C shows that changing \(\tau\) or the table-path
aggregation cannot reverse containment. Case D adds the scale qualification:
temperature has meaning only relative to the scale of \(G\), so comparisons
across metrics require tau-free draw-win fractions alongside soft probabilities.[^discussion-dials]

The bridge from Case B to Case C resolves an apparent tension. Case C shows
that neither the table path nor LOO credits a satisfied constraint in its
head-to-head example. For the table path, candidate-region containment fixes
the direction per draw; for LOO, the artifact's local diagnostic places
negligible mass in the excluded region and the comparison remains
inconclusive. Case B identifies the machinery that can credit the restriction:
the volume or reference-measure term on the \(Z_M\) side. A Bayes-factor-style
prior-mass reward corresponds to the \(V_{\mathrm{ref}}\)-normalization choice,
not to best-instance table-path aggregation. Making `occam` explicit keeps that
reward available without quietly attributing it to predictive fit.[^discussion-bridge]

## 8.2 Calibrating the M-open signal

Absolute divergence offers information that a relative ranking discards, but
its interpretation needs calibration. A high best-candidate \(G\) can reflect
misspecification, ordinary sampling variation, the GP scaffold, or the metric's
scale. A defensible inadequacy claim therefore requires a reference distribution
under known correct specification, conditional on the metric, data-prior
configuration, design, and noise regime.

Formal M-open calibration remains open. Case D contributes the first
correct-specification reference material for this program: known-truth
distributions of mean \(G\) under a synthetic design in which the generating
family appears among the candidates. Those distributions reveal overlap and
asymmetric distinguishability that a winner label would hide. They do not set
a rejection threshold, validate a universal scale, or establish an M-open
finding for observed data.[^discussion-mopen]

## 8.3 Relation to elpd and PSIS-LOO

The relation to elpd and PSIS-LOO concerns shared operations rather than an
identity of inferential targets. Both traditions use pointwise predictive
evaluation and can use importance weighting over posterior draws. PSIS-LOO
fits each candidate with its own parameter prior and estimates held-out
predictive accuracy; its importance ratios approximate leave-one-out
posteriors, with Pareto smoothing diagnosing unstable ratios. BMS*-GP instead
evaluates all candidates against shared data patterns \(\psi\), uses
`pw_kl_vcal` as the primary divergence, and reserves within-model priors for an
explicit hybrid extension. Its target concerns proximity to a common
data-space posterior, not leave-one-out prediction.[^discussion-loo]

Case C sharpens the distinction through a head-to-head comparison on identical
data. PSIS-LOO returns a null-to-inconclusive difference for the satisfied
constraint, consistent with the failure mode identified by Haaf, Klaassen, and
Rouder. The BMS* table path also returns an effective tie, but for a different
structural reason: the encompassing region contains every restricted optimum
and can never have larger best-instance divergence. The shared outcome does not
make the methods interchangeable. It locates the missing restriction reward in
both comparisons and directs any such reward to an explicit prior-volume
choice.[^discussion-loo-case]

## 8.4 Open questions

Several extensions now have sharper starting points.

- **Hybrid \(Z_M\).** Case A, section 3, upgrades the hybrid from a proposal to
  a construction with a passing Target B special-case test. Work remains on
  general candidate families, on prior knowledge independent of the analyzed
  data, and on the relation between within-model density and the `occam`
  reference measure.[^discussion-hybrid]

- **Learning \(\tau\).** The present work treats temperature as a sweep.
  Calibration across tasks with known truth could replace a conventional value
  with a design- and metric-specific learning rule.

- **Decision-theoretic \(G\).** Scientific losses differ across applications.
  A utility-weighted divergence could state which predictive discrepancies
  matter, while preserving the shared data-prior scaffold.

- **Non-stationary kernels.** Case D leaves scaffold representability and
  intrinsic mimicry unidentified. Kernels with location-dependent smoothness
  could address the first mechanism, but they cannot manufacture information
  when candidate families genuinely mimic one another.

- **Aggregation semantics.** D60 resolves the reporting convention, not the
  substantive choice for every application. Pooled aggregation remains
  canonical; expected-posterior aggregation remains necessary when Eq. 4
  correspondence matters. A future decision rule should connect that choice to
  whether absolute inadequacy or equal per-pattern credit answers the scientific
  question.

## 8.5 Costs and scope conditions

The method moves judgment into the data prior, kernel, metric, temperature,
reference measure, and aggregation rule. These choices become visible and
testable, but they still require substantive knowledge. When beliefs about a
bias process come largely from outside the observed data, additional sample
size need not remove the associated uncertainty; honest inference can retain an
uncertainty floor.

Two scope conditions follow from Case D. Under F1, the GP scaffold may fail to
represent the feature that distinguishes the candidates, so comparison reflects
the scaffold's resolution as well as the candidate theories. Under F2, the
candidate families may mimic one another over the informative design region,
so no scoring rule can recover information that the data do not contain. The
synthetic case could not identify which mechanism produced its asymmetry, and
its deviation curves covered only part of the region used by the stored
aggregate scores. BMS*-GP should therefore report scaffold checks, local
deviation diagnostics, and the possibility of unresolved F1/F2
non-identifiability rather than treating every weak separation as a demand for
a sharper posterior.[^discussion-limits]

## 8.6 Verification and reproducibility

Every reported number has a named regenerating `experiments/` script and a
corresponding `runs/` artifact; D17 records the provenance exception for the
local methods-validation reach check. Each case section underwent independent
review within a four-model adversarial cross-verification protocol. All four
reviewer rounds are recorded for every case, with the fourth, Kimi K3, run at
the author's direction on the same round-1 packages. The findings, refutations,
fixes, and author sign-off records are committed under `runs/<case>/reviews/`
in this repository, and the corresponding `Notes/DECISIONS.md` entry records
the review outcome.[^discussion-repro]

[^discussion-dials]: 🟠 empirical — assembled-manuscript sections 3–6 and their case artifacts: `runs/vanbork_external_validation/`, `runs/e7_convention_sensitivity/`, `runs/occam_dial/`, `runs/haaf_nested_constraint/`, and `runs/regret_curves_mopen/`; Notes/DECISIONS.md D60–D64.
[^discussion-bridge]: 🟠 empirical — assembled-manuscript sections 4 and 5 on `paper/case-b-occam-dial` and `paper/case-c-haaf`; `runs/occam_dial/e6_results.json`; `runs/haaf_nested_constraint/results.json`; Notes/DECISIONS.md D62 and D63.
[^discussion-mopen]: 🟠 empirical — assembled-manuscript section 6 on `paper/case-d-mopen`; `experiments/regret_curves_mopen.py`; `runs/regret_curves_mopen/results.json`; Notes/DECISIONS.md D64.
[^discussion-loo]: 🟢 peer-reviewed — Vehtari, Gelman, and Gabry (2017), “Practical Bayesian model evaluation using leave-one-out cross-validation and WAIC,” *Statistics and Computing*, 27(5), 1413–1432. Argument provenance: `kb/Wiki/Vehtari-Gelman-Gabry Connection.md`.
[^discussion-loo-case]: 🟠 empirical — `experiments/haaf_nested_constraint.py`; `runs/haaf_nested_constraint/results.json` and `README.md`; Notes/DECISIONS.md D63. 🟢 peer-reviewed — Haaf, Klaassen, and Rouder (2025), “Bayes factor vs. posterior predictive model assessment: Insights from ordinal constraints,” *Computational Brain & Behavior*.
[^discussion-hybrid]: 🟠 empirical — assembled-manuscript section 3 on `paper/case-a-vanbork`; `experiments/vanbork_external_validation.py`; `runs/vanbork_external_validation/results.json`; Notes/DECISIONS.md D60 Resolution and Precision addenda.
[^discussion-limits]: 🟠 empirical — assembled-manuscript section 6; `experiments/regret_curves_mopen.py`; `runs/regret_curves_mopen/`; Notes/DECISIONS.md D64.
[^discussion-repro]: 🟠 empirical — case review archives under `runs/vanbork_external_validation/reviews/`, `runs/occam_dial/reviews/`, `runs/haaf_nested_constraint/reviews/`, and `runs/regret_curves_mopen/reviews/`; corresponding review outcomes in Notes/DECISIONS.md D62–D65.

---
*Provenance: no empirical estimate is re-quoted in this section.
Cases A–D: `runs/vanbork_external_validation/`,
`runs/e7_convention_sensitivity/`, `runs/occam_dial/`,
`runs/haaf_nested_constraint/`, and `runs/regret_curves_mopen/` ·
`experiments/vanbork_external_validation.py`,
`experiments/e7_convention_sensitivity.py`,
`experiments/occam_dial_figure.py`,
`experiments/e6_nesting_monotonicity.py`,
`experiments/haaf_nested_constraint.py`, and
`experiments/regret_curves_mopen.py` · Notes/DECISIONS.md D60–D65.
Argument provenance: `kb/Wiki/Vehtari-Gelman-Gabry Connection.md`,
`kb/Wiki/Limits Diagnostics and Open Questions.md`, and
`CogSci Poster/OPEN_QUESTIONS.md`.*


=== CASE SECTIONS FOR CONSISTENCY (their own branches, read-only) ===
--- 03 Case A ---
# 3. Case A: external validation against van Bork, Romeijn, and Wagenmakers

van Bork, Romeijn, and Wagenmakers derive model probabilities from expected
predictive support under an independently specified data prior. Their proposal
cites the BI*/BMS* line as related prior work, but their closed-form examples
were developed without reference to the present implementation. They therefore
provide external checks on the induced-prior and soft-transfer machinery.
Because their examples supply the data prior directly, these checks bypass its
GP construction.[^1] The section reproduces both of their closed-form targets,
locates their construction inside the induced-prior machinery, and returns one
counterclaim about what their aggregation semantics costs.

## 3.1 Correspondence of the constructions

The correspondence below remains deliberately qualified. Both approaches
evaluate models against a distribution over possible data, but they need not
assign the same semantics to every intermediate quantity.

| van Bork et al. | Present notation and computation | Qualification |
|---|---|---|
| Data prior, a probability over outputs specified independently of the candidate models | \(p_0(\psi)\), a distribution over data patterns | In the general framework, GP hyperpriors induce \(p_0(\psi)\). The validation examples instead insert the authors' supplied data prior, so they do not test the GP scaffold. |
| Expected support against the data prior, expressed through Rosenkrantz-style verisimilitude | A divergence-based score \(G(\psi,\theta)\), followed by \(\bar G(\phi)\) when averaged over data patterns | Their support increases with predictive agreement; our divergence decreases with it. Additive and scale conventions therefore prevent a literal identification. |
| Prior model probability from expected posterior probability under their Eq. 4 | Normalize model support within each draw \(\psi\), then average under \(p_0(\psi)\) | This order matches expected-posterior aggregation. It does not match pooled aggregation, which sums unnormalized support across draws before model normalization. Their Eq. 4 treats each per-atom quantity as a Bayesian posterior model probability under an infinite-data idealization, whereas ours applies a Boltzmann softmax as \(\tau\) approaches zero. Target A agreement follows because both collapse to the same hard nearest-model assignment. |
| Completely overlapping models with distinct within-model parameter priors | Hybrid \(Z_M=\int p_M(\phi)\exp\{-\bar G_M(\phi)/\tau\}\,d\phi\) | The within-model density \(p_M(\phi)\) replaces the usual Lebesgue or \(V_{\mathrm{ref}}\)-normalized reference measure, so the check concerns an extension of the standard \(Z_M\). |
| A restricted model nested in an encompassing model | \(M_r\subset M_e\) | We adopt their nesting notation. Normalized predictive weights over a candidate roster do not thereby become set-additive probabilities over hypotheses. |

## 3.2 Target B: completely overlapping models

Their coin example compares \(M_x\), with
\(\theta\sim\operatorname{Beta}(50,50)\), against \(M_z\), with
\(\theta\sim\operatorname{Beta}(2,2)\), under a data prior that places a point
mass at \(\psi^*=1/2\). The hybrid computation approaches the published
probability for \(M_x\) monotonically over the reported low-temperature rows:

| \(\tau\) | Computed \(p(M_x)\) |
|---:|---:|
| \(10^{-2}\) | 0.792607 |
| \(10^{-4}\) | 0.840781 |
| \(10^{-6}\) | 0.841413 |
| \(10^{-7}\) | 0.841419 |
| Their closed form, evaluated at double precision | 0.841420 |

The paper prints the prior densities as 7.96 and 1.50 and the model weight as
approximately 0.84; the quotient formed from those printed densities equals
0.841438. Thus, the six-decimal comparison uses their closed form evaluated at
double precision rather than a printed six-decimal value. At the smallest
reported temperature, the absolute error against that evaluated limit equals
\(6.4\times10^{-7}\). The computed prior densities at the maximum-likelihood
point, 7.9589 for \(M_x\) and 1.5000 for \(M_z\), also reproduce the quoted
7.96 and 1.50 values.[^2]

The agreement follows from a Laplace special case. With a point data prior,
\(\bar G(\phi)=G(\psi^*,\phi)\). Around the candidate optimum
\(\theta^*=1/2\), which coincides with the data-prior atom,

\[
Z_M \approx p_M(\theta^*)
\sqrt{\frac{2\pi\tau}{\bar G_M''(\theta^*)}}.
\]

Both models use the same Bernoulli family, so they share the local curvature:
\(\bar G_x''(\theta^*)=\bar G_z''(\theta^*)\). That factor and the remaining
common terms cancel after normalization across models. As \(\tau\) approaches
zero, the normalized hybrid scores consequently converge to the ratio of the
within-model prior densities at \(\theta^*\). The authors' published formula
thus coincides with the shared-family, point-data-prior, zero-temperature limit
of the hybrid \(Z_M\). Target B supplies the first passing test of this
within-model-prior extension, which had previously remained an open
implementation question.[^2]

## 3.3 Target A: aggregation changes the limiting answer

The non-overlapping example assigns data-prior mass 0.4 at a Bernoulli
proportion of 0.16 and mass 0.6 at 0.19, then compares point models at 0.15 and
0.20. van Bork et al.'s answer assigns model probabilities 0.4 and 0.6. The
three implemented aggregation routes behave differently:

| Aggregation route | Low-temperature result | Target A verdict |
|---|---:|---|
| Pooled, `normalize_per_draw=False` | 0.000 / 1.000 | Fails |
| Normalize each data-prior atom, then average | 0.400 / 0.600 | Exact |
| Shipped `normalize_per_draw=True` semantics (per-draw minimum shift) | 0.400 / 0.600 | Exact |

![Target A aggregation and Target B temperature validation](../../runs/vanbork_external_validation/target_figure.png)

*Figure. Panel (a) compares the three Target A aggregation routes at the
smallest artifact temperature with the published targets. Panel (b) plots our
Target B \(p(M_x)\) across the artifact temperatures with their closed form
evaluated at double precision. Source: `runs/vanbork_external_validation/results.json`.
The figure re-plots committed artifact values without recomputation.*

Both per-draw routes have converged to the exact target by
\(\tau=10^{-4}\).[^2] The shipped semantics and Eq. 4 aggregation remain
distinct computations: the former subtracts per-row minima and normalizes once
after pooling, whereas the latter normalizes each row into a model posterior
before averaging. They coincide in the \(\tau\)-to-zero unique-winner limit
exercised by Target A. The result exposes a modeling choice rather than a
numerical defect. Pooled aggregation preserves absolute divergence magnitudes:
a draw that every candidate fits poorly contributes less total support. That
property carries the M-open inadequacy signal, but pooled aggregation fails
Target A. Expected-posterior aggregation matches Eq. 4 and avoids that failure,
but each draw must spend one full unit of credit even when every candidate fits
poorly. The latter choice therefore discards the absolute-magnitude signal.

The author adopted the aggregation convention as an explicit evaluation dial
alongside \(\tau\) and `occam`. Canonical reporting keeps pooled aggregation to
preserve absolute divergence magnitudes, the M-open signal, and continuity with
every ratified number; the shipped `normalize_per_draw=False` default remains
unchanged. In Case A, the expected-posterior variant from Eq. 4 accompanies
pooled results wherever correspondence with van Bork et al.'s semantics matters,
while the `kl_forward` aggregation attribution remains confined to the appendix.
Neither convention is declared universally correct.[^2]

The E7 README recorded this stance as a candidate, which the author adopted on
2026-08-12.[^3]

**Claim:** van Bork, Romeijn, and Wagenmakers advance the expected-support
construction as a principled source of prior model probability: candidates
earn probability through expected predictive alignment with the data prior,
and even completely overlapping models become distinguishable, grounding a
Wrinch-Jeffreys-style simplicity preference in prediction rather than
fiat.[^1] Section 3.2 locates that construction inside the present framework:
their formula arises from the hybrid \(Z_M\) in the zero-temperature,
shared-family, point-data-prior limit, and the case reproduces both published
targets. Containment rather than rivalry describes the relation: the framework
exposes through explicit controls what their construction fixes implicitly,
namely \(\tau\), `occam`, and the aggregation dial.

**Counterclaim:** the framework identifies a cost. Their Eq. 4 semantics
forces per-draw normalization, so every data-prior draw spends one full unit of
credit even when no candidate fits it, and absolute divergence magnitudes
disappear. Those magnitudes carry the framework's misspecification signal:
uniformly high divergence indicates that no candidate is adequate, as
exercised by the M-open reading in Case D, section 6. Adopted as canonical,
their construction would therefore silently foreclose misspecification
diagnosis, a cost the published account does not price. The evaluation dial
prices it explicitly: pooled aggregation retains the magnitudes, the Eq. 4
variant purchases external correspondence, and the trade remains visible at
the point of use.[^3] Neither reading restores set-additive probabilities over
a hypothesis space (mapping row 5), so Popper's nesting constraint is dissolved
rather than answered by this family of constructions; section 4 prices the
residual disagreement empirically through the `occam` dial.

## 3.4 Measured sensitivity on the validated toy path

E7 evaluates the fork on the validated `toy_elicited` SIR path. Under the
primary `pw_kl_vcal` metric at \(\tau=1\), pooled aggregation gives model
probabilities 0.183, 0.192, 0.441, and 0.184 for Linear, Sinusoidal,
Sin+Linear, and Quadratic, respectively. This row reproduces the ratified SIR
headline. Under this metric, Sin+Linear remains the highest-weight candidate at
every tested aggregation variant and temperature. The maximum absolute movement
between pooled and expected-posterior aggregation equals 0.31 at \(\tau=0.1\),
0.072 at \(\tau=1\), and 0.001 at \(\tau=10\); at \(\tau=1\), the Sin+Linear
weight changes from 0.441 to 0.513.[^3] Within each metric, all three
aggregation variants use the same \(G\) matrix from one SIR realization
(\(n_{\mathrm{pred}}=1000\)), so the reported movements are paired differences
rather than differences of independent estimates.

The appendix-only `kl_forward` stress metric reveals a sharper attribution.
With pooled aggregation, the Sin+Linear weight collapses to approximately
0.000 for \(\tau\leq1\). Expected-posterior aggregation instead gives 0.696 at
\(\tau=0.1\) in the E7 `results.json`. Analytically, expected-posterior
aggregation converges by construction to hard best-match fractions as \(\tau\)
approaches zero. At the reported precision, the E7 value equals the
`toy_elicited` SIR hard fraction 0.696 (696/1000) in the committed D18 record,
a correspondence also noted in the E7 README. The earlier `kl_forward`
fragility therefore reflects pooled-aggregation sensitivity to outlying draws,
not a property of the metric alone.[^3]

## 3.5 Multi-parameter reach under methods-validation framing

An earlier informative-configuration, MAP-based visualization arm provides a
methods-validation reach check rather than a paper-facing inferential
headline. In `runs/viz_unification/p3_priors_canonical/`, the multi-parameter
Sin+Linear candidate receives 0.992 at \(n=50\) and stays at or above 0.93
across all evaluated \(n\). This result shows that the same induced-prior
machinery extends beyond the closed-form coin targets to a richer candidate
family. It does not replace the validated `toy_elicited` SIR result above.[^4]

[^1]: 🟢 peer-reviewed — van Bork, R., Romeijn, J.-W., & Wagenmakers, E.-J. (2025). Simplicity in Bayesian nested-model comparisons: Popper's disagreement with Wrinch and Jeffreys revisited. *Synthese*. https://doi.org/10.1007/s11229-025-05286-y.
[^2]: 🟠 empirical — `experiments/vanbork_external_validation.py`; `runs/vanbork_external_validation/results.json` and `README.md`; Notes/DECISIONS.md D60; Notes/DECISIONS.md D60 Resolution (2026-08-12).
    Figure: `experiments/vanbork_figure.py` re-plots the committed artifact values without recomputation.
[^3]: 🟠 empirical — `experiments/e7_convention_sensitivity.py`; `runs/e7_convention_sensitivity/results.json` and `README.md`; Notes/DECISIONS.md D61. The committed Notes/DECISIONS.md D18 record supplies the `toy_elicited` SIR hard fraction 0.696 (696/1000), whose correspondence with E7 is also noted in the E7 README.
[^4]: 🟠 empirical — D17-recorded findings for the local, untracked `runs/viz_unification/p3_priors_canonical/` arm, generated by `bistar_viz/scripts/viz_unification_compare.py` through `bistar_viz/scripts/model_priors_laplace.py`. The informative-configuration, MAP-based Sin+Linear candidate receives 0.992 at \(n=50\) and stays at or above 0.93 across all evaluated \(n\); the committed Notes/DECISIONS.md D17 record supplies their citation provenance and the `bistar_viz` scripts regenerate them.

---
*Provenance: `runs/vanbork_external_validation/` ·
`experiments/vanbork_external_validation.py` · Notes/DECISIONS.md D60;
`runs/e7_convention_sensitivity/` ·
`experiments/e7_convention_sensitivity.py` · Notes/DECISIONS.md D61.
The W4 reach check follows the D17-recorded citation path stated in [^4].
Argument provenance: `kb/Raw/papers/important/vanBork_Romeijn_Wagenmakers_2025_subset_problem.md`
and `kb/Wiki/Subset Problem and the Data Prior.md`.*

--- 04 Case B ---
# 4. Case B: the occam flag as the Popper/Wrinch-Jeffreys dial

van Bork, Romeijn, and Wagenmakers restate Popper's objection to the
Wrinch-Jeffreys treatment of nested models: if M_r ⊂ M_e, assigning more prior
probability to the restricted model M_r violates the encompassing-model
constraint. Wrinch and Jeffreys instead permit a simplicity preference for
M_r. Their analysis motivates a direct question for the induced model prior
Z_M: which position does its reference measure encode?[^1]

The toy roster contains two relevant restrictions. Linear follows from
Sin+Linear at A=0, and Sinusoidal follows at b=c=0. Quadratic does not form a
restriction of Sin+Linear. The `occam` flag changes the measure used in Z_M:
`occam=False` integrates against raw Lebesgue measure, following the canonical
BI* convention, whereas `occam=True` divides by the reference volume
V_ref.[^2]

## 4.1 An attribution ladder, not a two-arm ablation

Figure 4 recomputes the three D17 attribution arms at n=50 and τ=0.3, with the
`informative` GP configuration and a MAP predictive. These values serve
methods validation and legacy comparison. They do not provide paper-facing
posterior inference about which model generated the data.[^3]

![Three-arm Occam-dial comparison at n=50](../../runs/occam_dial/occam_dial.png)

**Figure 4.** Induced model priors for the nested toy roster. The p1 and p3
panels differ in both the Z_M estimator and the `occam` convention, so the p2
panel prevents a conflated attribution. Replacing pure Laplace with IS while
retaining `occam=True` changes the Linear and Sin+Linear probabilities from
0.534 and 0.382 in p1 to 0.507 and 0.465 in p2. Changing only the convention
in the next step gives 0.007 and 0.992 in p3. At p2, ESS implies SE(log Z) of
approximately 0.008, 0.017, and 0.038 nats for Linear, Sin+Linear, and
Sinusoidal, respectively, with probability SE approximately 0.005. The estimator
change narrows the gap; removing the V_ref normalization decides the verdict.
The dial figure argues about the `occam` convention's effect, not about which
model generated the data.

The figure's τ=0.3 evaluation point falls 1.6 percent above the `occam=True`
Linear/Sin+Linear crossing at τ≈0.295. The p2 log Z_M gap of 0.0867 nats gives
a Bayes factor of about 1.09, so the `occam=True` panels report an essentially
tied comparison. The p1/p2 "Linear preferred" reading therefore remains
τ-marginal, while the p2-to-p3 magnitude change provides the robust content.

The earlier contradiction supplies useful historical context but not new
evidence. D17 records 0.934 for Sin+Linear in the legacy trajectory script and
0.693 for Linear in the legacy priors script, which hard-coded
`occam=True`. The pinned-commit extraction in
`viz_unification_compare.py` regenerates those legacy arms. The new figure
does not invoke or parse that extraction.[^2]

## 4.2 E6: best achievable divergence under exact nesting

As τ approaches zero, the leading contribution to Z_M comes from
min_φ Ḡ(φ). The reachable-set argument therefore requires

\[
\min_{\phi}\bar G(M_e) \leq \min_{\phi}\bar G(M_r).
\]

Different parameter dimensions prevent a Lebesgue-monotonicity argument in
parameter space. Given the two exact embeddings and the mean-only divergence,
however, the inequality follows analytically from reachable-set containment in
data space. The visualization box uses A ≥ 0.01 as a numerical cutoff, so E6
alone extends the encompassing amplitude bound to A ≥ 0. All other bounds
match the visualization arms. The restricted optima seed the encompassing
multi-start optimization, and the package divergence calculation reproduces
each restricted value at its embedding within the declared 10^-10 tolerance.
E6 thereby confirms that the implementation reproduces the analytic
consequence, providing a machinery check rather than empirical support for the
containment claim.[^4]

For this n=50, `informative`-configuration, MAP-based averaged GP, the machinery
check obtains min_φ Ḡ=0.046 for Sin+Linear, 2.425 for Linear, and 2.546 for
Sinusoidal. It quantifies restricted-minus-encompassing margins of 2.379 and
2.501 nats, respectively, far above the 10^-8 comparison tolerance. The
empirical content of E6 consists of these margins and the finite-τ Z_M
crossings.[^4]

Finite τ separates the two reference measures. One IS call per model per seed
evaluates 161 temperatures for seeds 0, 1, and 2. With `occam=False`,
Sin+Linear retains the larger pairwise Z_M throughout the grid for all three
seeds, so neither nested pair crosses. With `occam=True`, the Linear crossing
occurs at τ=0.295, 0.295, and 0.296 across seeds 0, 1, and 2. Seed 0 has grid
bracket [0.282, 0.299], the per-seed spread is [0.295, 0.296], and its
ESS-implied one-SE shift interval is [0.295, 0.296]. The seed-0 bracket delta
swing of 0.354 nats exceeds the ESS-implied SE of approximately 0.012 nats, so
the three-decimal Linear crossing is sign-supported. The Sinusoidal crossing
occurs at 1.484, 1.584, and 1.382 across those seeds; it should be summarized
only as τ ≈ 1.5. Its seed-0 bracket is [1.413, 1.496], the per-seed spread is
[1.382, 1.584], and the seed-0 ESS shift roots are [1.392, 1.563]. The enclosing
grid-and-seed uncertainty interval is about τ 1.33 to 1.59.
Crossing resolution is set by the larger of grid spacing and Monte Carlo error.
Thus low temperature supports Popper's encompassing constraint in both
conventions for this example, while V_ref normalization permits the
finite-temperature simplicity preference associated with Wrinch and
Jeffreys.[^4]

The two controls should therefore remain explicit. Temperature governs how
strongly best achievable divergence dominates integrated compatibility, while
`occam` selects raw or volume-normalized reference measure. Their joint
sensitivity describes the Popper/Wrinch-Jeffreys disagreement without turning
a methods-validation example into a claim about model truth.

[^1]: 🟢 peer-reviewed — van Bork, Romeijn, and Wagenmakers (2025), *Synthese*, doi:10.1007/s11229-025-05286-y.
[^2]: 🟠 empirical — `Notes/DECISIONS.md` D3, D5, and D17; legacy regeneration through `bistar_viz/scripts/viz_unification_compare.py` at pinned commit `a87356a`.
[^3]: 🟠 empirical — `experiments/occam_dial_figure.py`; `runs/occam_dial/figure_results.json`.
[^4]: 🟠 empirical — `experiments/e6_nesting_monotonicity.py`; `runs/occam_dial/e6_results.json`.

---
*Provenance: `runs/occam_dial/` · `experiments/occam_dial_figure.py` ·
`experiments/e6_nesting_monotonicity.py` · `Notes/DECISIONS.md` D17, D62.*

--- 05 Case C ---
# 5. Case C: a satisfied nested constraint under BMS* and LOO

Haaf, Klaassen, and Rouder examine theories represented by restrictions on a
common parameter space. In their ordinal examples, WAIC and leave-one-out
cross-validation do not favor the restricted model even when the data comply
with its constraint. They argue that a forced partition into disjoint regions
can replace scientifically meaningful overlapping models with regions that
carry no theoretical interpretation.[^1] [Provisional framing: Kellen and
Klauer (2020) has not yet been read, so the phrase “sharpest published
criticism” remains provisional.]

Our experiment mirrors the parameter-region issue directly. It does not rely
on the toy example's cross-family nesting. The encompassing candidate
$M_e$ uses

$$
y(x)=A\sin(\omega x+\phi)+bx+c+\epsilon,
$$

with unrestricted $b$. The restricted candidate $M_r \subset M_e$ uses the
same expression and imposes $b\geq 0$. Both candidates call the same bounded
MLE routine, receive four shared base starts, and share every bound except the
lower bound on $b$. The restricted fit additionally receives the free
solutions, clipped at $b=0$ when necessary, and each candidate's selection
pool includes the other candidate's feasible vectors. This deliberate
asymmetry forces exact equality at shared optima instead of turning optimizer
noise into a gap. The frozen $N=20$ data use seed 42 and the true slope
$b=0.25$, so the restriction holds in truth.[^2]

## 5.1 BMS* comparison

The BMS* calculation follows the validated `toy_elicited` stage-IS path. It
pools prior-IS caches from seeds 0, 1, and 2, draws 1,000 SIR predictives with
seed 42, and evaluates 60 locations. For every predictive data pattern
$\psi$, the fits are obtained by variance-weighted maximum likelihood toward
each $\psi$; the primary `pw_kl_vcal` value $G(\psi,\theta)$ is then minimized
by selection over the shared candidate pool, within each candidate's parameter
region.
Thus the calculation supplies candidate instances from a shared $\psi$ rather
than introducing candidate-parameter priors. Such priors contribute only to
the separate LOO comparison below.[^2]

The nesting relation fixes the primary-metric ordering as an identity of the
protocol: $M_r\subset M_e$ implies
$\min_{\theta\in M_r}G\geq\min_{\theta\in M_e}G$ for every predictive. The
cross-seeded candidate pools enforce this set inclusion numerically, while
re-evaluation of the same feasible vector gives exact equality at a shared
optimum. The $2\times10^{-7}$ runtime gates guard against machinery
regressions; they do not provide an empirical nesting test. On 999
predictives, the free optimum had $b\geq0$ and the primary $G$ gap equaled
exactly zero. One predictive had a negative free optimum, for a fraction of
0.001, and restricted minus free $G$ equaled 0.000360 on that row.[^2]

This same set inclusion fixes the probability direction before Table 5.1.
The restricted candidate can never exceed the free candidate under either
aggregation at any $\tau$; only the gap's magnitude depends on the sampled
predictives.[^2]

Table 5.1 reports both aggregation conventions across the preregistered
temperature grid. Each pair normalizes over only the free and restricted
candidates.[^2]

| $\tau$ | pooled free | pooled restricted | expected-posterior free | expected-posterior restricted |
|---:|---:|---:|---:|---:|
| 0.1 | 0.500 | 0.500 | 0.500 | 0.500 |
| 0.3 | 0.500 | 0.500 | 0.500 | 0.500 |
| 1.0 | 0.500 | 0.500 | 0.500 | 0.500 |
| 3.0 | 0.500 | 0.500 | 0.500 | 0.500 |
| 10.0 | 0.500 | 0.500 | 0.500 | 0.500 |

At the headline value $\tau=1$, both conventions therefore give an effective
tie. The free-minus-restricted probability gap remains smaller than
$10^{-5}$ at every $\tau$ under both conventions and comes entirely from the
single negative-slope draw. Its monotone contraction with $\tau$ follows
deterministically from the Boltzmann aggregation, not from a measured
temperature effect.[^2]

The result does not support a claim that BMS* preferentially rewards a
satisfied restriction. BMS* assigns the restricted candidate
essentially half the probability without partitioning the parameter space,
but the encompassing candidate can reproduce every restricted optimum. The
single predictive with a negative slope creates the entire primary-metric gap.
Without an explicit parameter-volume or complexity term, the satisfied
restriction supplies equality on shared optima rather than an automatic
advantage. Soft transfer makes that null result visible across $\tau$; a hard
best-match treatment would retain only the limiting row assignments.

## 5.2 PSIS-LOO comparison

Both Bayesian candidates use the identical 20 observations and likelihood.
Their weakly informative priors apply only to this LOO arm: $A\sim$
HalfNormal(5), $\omega\sim$ LogNormal(0, 0.7), $\phi\sim$
Uniform($-\pi,\pi$), $c\sim$ Normal(0, 5), and $\sigma\sim$
HalfNormal(2). The free model uses $b\sim$ Normal(0, 5); the restricted model
uses the corresponding zero-truncated distribution, $b\sim$ HalfNormal(5).
No prior from this list enters the BMS* calculation.[^2]

Pyro NUTS ran two sequential chains with seeds 20260811 and 20260812. Each
chain used 1,000 warmup iterations and retained 1,000 draws, with target
acceptance probability 0.90 and maximum tree depth 8. Both chains for both
candidates initialized deterministically at the same observed-data MLE through
`init_to_value`: $A=0.886352$, $\omega=1.030240$, $\phi=-0.029881$,
$b=0.251277$, $c=0.028723$, and $\sigma=0.321232$. Sampled-grid aliases near
$\omega=4.939$ and $6.999$ make the $\omega$/$\phi$ likelihood multimodal.
Both fits recorded zero divergences. Rank-normalized $\widehat R$ reached at
most 1.003 for the free fit and 1.002 for the restricted fit; minimum bulk
effective sample sizes were 1,004 and 1,638, respectively. These diagnostics
support within-mode convergence only, not exploration across modes.[^2]

| candidate | `elpd_loo` | SE | `p_loo` | max Pareto $k$ | warning |
|---|---:|---:|---:|---:|---|
| free Sin+Linear | -13.074 | 3.458 | 5.343 | 0.564 | no |
| slope-constrained Sin+Linear | -12.661 | 3.594 | 5.169 | 0.718 | yes, one observation |

The constrained-minus-free `elpd_loo` difference equals 0.413 with a paired SE
of 0.256, computed with `ddof=0` to match the ArviZ convention.[^2] The
difference is directionally inconclusive: its magnitude is smaller than twice
its paired SE, the constrained estimate carries a Pareto-$k$ warning because
one observation exceeds the 0.697 good-$k$ threshold, and the paired SE covers
data-level pointwise variability only, without MCMC error. Haaf, Klaassen, and
Rouder report this kind of null-to-inconclusive LOO difference as the failure
mode for a satisfied nested constraint.[^1] Pareto shape values above about
0.7 can make the importance-sampling approximation unreliable, so a decisive
direction would require exact refits or a more robust cross-validation
calculation.[^3]

The two slope priors coincide up to normalization on $b>0$, so LOO has no
structural contrast wherever negative-slope posterior mass is negligible. The
artifact's own full-data local Gaussian diagnostic gives posterior SD
0.0129506 for $b$, places the boundary 19.4028 SDs away, and gives a Gaussian
left-tail probability of $3.65\times10^{-84}$. This local approximation
supports the reading that the constraint binds only where the locally
approximated posterior carries negligible mass. It does not prove that the
global posteriors or leave-one-out fold posteriors are exactly identical, and
it does not establish that the entire observed gap comes from estimator
noise.[^2]

The LOO arm therefore reproduces the null-to-inconclusive failure mode without
supporting a directional claim. BMS* also gives a numerical tie, with a
one-sided direction fixed by nesting and a magnitude determined by the single
negative-slope SIR draw.

[^1]: 🟢 peer-reviewed — Haaf, Klaassen, and Rouder (2025). Bayes factor vs. posterior predictive model assessment: Insights from ordinal constraints. *Computational Brain & Behavior*. https://doi.org/10.1007/s42113-025-00240-0
[^2]: 🟠 empirical — `experiments/haaf_nested_constraint.py`; `runs/haaf_nested_constraint/results.json` and `README.md` (data seed 42; prior-IS seeds 0, 1, 2; SIR seed 42; NUTS seeds 20260811 and 20260812).
[^3]: 🟢 peer-reviewed — Vehtari, Gelman, and Gabry (2017). Practical Bayesian model evaluation using leave-one-out cross-validation and WAIC. *Statistics and Computing*, 27(5), 1413–1432.

---
*Provenance: `runs/haaf_nested_constraint/` · `experiments/haaf_nested_constraint.py` · Notes/DECISIONS.md D63.*

--- 06 Case D ---
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
stored practice (G) values were computed on 50 uniformly spaced points spanning
each subject's full series. The reconstructed deviation curves instead cover
integer trials 1 through 20. For the longest subjects, that early grid spans
19/78, or 24.4%, of the full continuous trial range. Any linkage between those
curves and the stored aggregate comparisons therefore applies only to their
shared early-trial region. We use these data to study distinguishability and
mimicry and to establish correct-specification reference levels for (G); we do
not infer how either candidate fits the real Evans corpus.[^case-d-empirical]
Evans et al.'s broader candidate discussion motivates the context, while every
result below concerns only Power and Exponential, the pair retained in the
stored fits.[^case-d-evans]

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

Across the 50 subjects, all three configurations select the same winner for 39
subjects under `pw_hellinger`, 49 under `pw_mse`, and 48 under `pw_nll`.

These practice artifacts predate W1. They contain `pw_nll`, `pw_mse`, and
`pw_hellinger`, not the manuscript's primary `pw_kl_vcal`; no new metric was
authorized for Case D, and we do not relabel the stored quantities.
Legacy `pw_nll` weights squared error by the candidate's fitted noise variance,
whereas `pw_kl_vcal` weights it by the GP variance. On that weighting axis,
`pw_mse` lies closer to the manuscript primary.

For all 300 stored configuration-by-subject-by-candidate `mean_G` pairs,
`pw_nll = 0.5 log(2 pi sigma_theta^2) + pw_mse/(2 sigma_theta^2)` to maximum
absolute error $1.78 \times 10^{-15}$. Thus `pw_nll` and `pw_mse` apply a
candidate-specific affine map to the same squared-error statistic; the divisor
`2 sigma_theta^2` ranges from 743 to 7,161, approximately 750 to 7,150. BMS*
scores `exp(-G/tau)` at a shared $\tau$, so soft-transfer probability magnitudes
are not comparable across metrics on different scales. No value on the stored
15-point grid removes the gap: at $\tau=0.1$, the power-cohort `pw_nll` medians
are 0.581, 0.569, and 0.557 for practitioner, moderate, and agnostic,
respectively, while the all-subject practitioner `pw_mse` median remains 0.987
at $\tau=31.6$.[^case-d-empirical]

The tau-free, scale-invariant `pw_nll` `raw_draw_wins` diagnostic carries the
asymmetry instead:

| GP configuration | Power truth: true-family draw wins / subject majorities | Exponential truth: true-family draw wins / subject majorities |
|---|---:|---:|
| practitioner | 39.0% / 9 of 25 | 98.7% / 25 of 25 |
| moderate | 39.9% / 8 of 25 | 94.6% / 25 of 25 |
| agnostic | 41.5% / 9 of 25 | 92.1% / 25 of 25 |

These `pw_nll` counts describe how often the known-truth candidate attains the
smaller raw divergence on the 100 stored GP draws per subject. They support a
metric-specific asymmetric-recovery statement without interpreting a
temperature-dependent probability magnitude.[^case-d-empirical]

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

Within these `pw_nll` summaries, the power-generated rows exhibit the mimicry
signature: both magnitudes nearly coincide, and the wrong exponential candidate
has the slightly smaller cohort mean. The `pw_nll` exponential-generated rows
separate more clearly and favor the known truth. At synthetic exponential
subject 25, the practitioner `pw_nll` means
equal 4.881 for Power and 4.852 for Exponential, an absolute difference of
0.029. A ranking reports only Exponential; the paired magnitudes show how
little separates the candidates for that subject.[^case-d-empirical]

The `pw_nll` table also blocks an overstatement about M-open inadequacy.
Correctly specified candidates can produce `pw_nll` mean (G) values from 4.582
to 4.858 in these cohort summaries, while a wrong but mimicking candidate can
occupy much of the same scale. A future inadequacy rule must compare an observed
magnitude with a
reference distribution under correct specification, conditional on metric,
configuration, sample size, and noise. These known-truth `mean_G` distributions
supply the kind of calibration material such a rule needs, but Case D does not
set a rejection threshold.

## MAP-conditional deviation localizes the comparison

The subject JSONs omit GP curves and draws. The new reconstruction regenerates
the synthetic observations, verifies each stored candidate fit through its BIC
residual structure, rebuilds an exact GP at the stored hyperparameters, and
computes its latent posterior mean plus 100 seeded latent posterior functions
per subject. No refitting and no new HMC occur.

One provenance and estimand limitation matters. `run.py` writes one
`gp_hyperparameters` block immediately after the first successful configuration
MAP fit. With the default order, all 50 source files record the practitioner MAP
point even though `results_hmc/` subsequently uses HMC samples for its stored
BMS* diagnostics. The JSONs do not retain those HMC hyperparameter draws, so
neither reconstruction below averages posterior mean functions over
hyperparameter draws as in the limits-note formula. The solid curves instead
report the MAP-conditional posterior expected absolute deviation of the latent
function,

\[
R^{\mathrm{draw}}_{\theta}(t)
= \mathbb{E}_{f\mid y,\hat{\eta}}
  \left[\left|f(t)-\mu_{\theta}(t)\right|\right],
\]

and the dashed curves report the mean-based plug-in at the same MAP point,

\[
R^{\mathrm{mean}}_{\theta}(t)
= \left|\mathbb{E}\!\left[f(t)\mid y,\hat{\eta}\right]
  -\mu_{\theta}(t)\right|.
\]

Jensen's inequality orders the exact estimands: the exact
$R^{\mathrm{draw}}_{\theta}(t)$ is no smaller than
$R^{\mathrm{mean}}_{\theta}(t)$ for each subject, candidate, and trial. The
finite 100-draw Monte Carlo estimates carry Monte Carlo error and may invert
locally, as at trial 1 for the Power candidate under Power truth (116.333 versus
116.506) and Exponential truth (131.415 versus 131.572). Latent posterior spread
therefore inflates candidate deviations and generally compresses their gap by a
trial-dependent amount, so the two estimands should not be substituted silently.

Each solid line pools 25 subjects and 100 draws within a truth cohort. Its band
spans the pooled 10th and 90th percentiles of the resulting 2,500 absolute
errors at each trial; it describes subject-and-draw dispersion, not uncertainty
in the cohort mean. Each dashed line averages the 25 subject-level plug-in
deviations; corresponding subject quantiles remain in `results.json`.

![MAP-conditional deviation curves for the two synthetic truth cohorts](../../runs/regret_curves_mopen/regret_curves.png)

| Estimand | Truth cohort | Mean Power deviation (RT units) | Mean Exponential deviation (RT units) | Peak gap (RT units) | Gap in trials 1–5 | Gap in trials 1–10 |
|---|---|---:|---:|---:|---:|---:|
| MAP-conditional posterior expected absolute deviation | Power | 21.383 | 20.681 | 33.782 at trial 1 | 70.0% | 82.2% |
| Posterior-mean plug-in | Power | 17.638 | 17.325 | 34.052 at trial 1 | 63.3% | 74.0% |
| MAP-conditional posterior expected absolute deviation | Exponential | 35.587 | 14.855 | 91.452 at trial 1 | 41.7% | 77.7% |
| Posterior-mean plug-in | Exponential | 33.901 | 10.764 | 92.890 at trial 1 | 40.0% | 75.0% |

Both profiles concentrate toward the beginning but do not collapse to only the
first few trials. For the MAP-conditional posterior expected absolute deviation
under power truth, trial 1 produces 116.333 RT units for Power and 82.551 for
Exponential, with the wrong family closer where the largest gap occurs. Under
exponential truth, the corresponding values equal 131.415 and 39.963, and
appreciable separation continues through the first half of the grid. The two
estimands therefore show a consistent descriptive localization under the
stored practitioner-MAP scaffold. Within the shared early-trial region, that
localization agrees with the asymmetric practitioner `pw_nll` raw-draw result;
it cannot explain the portion of the stored aggregate comparison evaluated
later in each subject's full series.[^case-d-empirical]

The branch contains exactly one practitioner-MAP RBF reconstruction, and all
three stored configurations use the RBF family. These artifacts cannot identify
whether the localized `pw_nll` recovery asymmetry originates in F1
representability, F2 mimicry, metric behavior, or sampling noise. That
non-identifiability matches the F1/F2-agnostic interpretation above.

## Positioning and optional extension

Averell and Heathcote showed that power-versus-exponential conclusions about
forgetting can change between individual-level and population-level analyses.
Their result warns against treating one comparison procedure or aggregation
level as a resolution of the functional-form debate.[^case-d-averell] Case D
supports a narrower conclusion. On synthetic practice curves, the legacy
`pw_nll` raw-draw results show asymmetric recovery, its raw divergence
magnitudes provide correct-specification reference levels, and both
MAP-conditional deviation estimands descriptively localize part of that
asymmetry in the shared early-trial region. Nothing here identifies its cause or
adjudicates the real practice data or the forgetting literature.

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


=== BRANCH DIFF vs main (DECISIONS D66 entry) ===
diff --git a/Notes/DECISIONS.md b/Notes/DECISIONS.md
index 033fee3..02aadc2 100644
--- a/Notes/DECISIONS.md
+++ b/Notes/DECISIONS.md
@@ -5716,3 +5716,72 @@ to be amended later merely to insert them. STOP before Ready or merge. NOT autho
 second correction pass, restoring/applying/dropping stash `5280d1e1…`, D59 work, evidence
 or figure changes, poster-repository work, the captions themselves, Della contact, new
 computation, holdout access, BMS*, Ready, or merge.
+
+## D66: Synthesis sections integrate the four case studies — 2026-08-12
+
+**Problem:** The synthesis branch still contained stubs for the Introduction,
+Machinery, and Discussion after the four case sections were completed on their
+separate branches. The assembled manuscript needed those sections to adopt the
+case prose conventions, expose the author-resolved evaluation dials, carry the
+Case B-to-C nesting logic into the general account, and state the Case D scale
+and calibration limits without copying case results or treating knowledge-base
+files as numerical authority.
+
+**Decision:** Replaced the stubs in `docs/paper-sie-jmp/01-intro.md`,
+`docs/paper-sie-jmp/02-machinery.md`, and
+`docs/paper-sie-jmp/08-discussion.md` with final manuscript prose under the
+frozen notation in `docs/paper-sie-jmp/00-notation.md`.
+
+Section 1 frames the contribution for the third JMP model-evaluation special
+issue, treats data priors as the through-line from the foundational JMP papers,
+connects the construction to Bonifay and Cai's fit-propensity program, makes the
+three evaluation dials the unifying contribution, and previews the four cases
+with Case C's null and Case D's synthetic-only scope stated directly. Section 2
+develops the data prior, projection and induced priors, \(Z_M\), soft transfer,
+aggregation, and metric roles. It adds a numbered containment remark: for
+\(M_r\subset M_e\), best-instance divergence orders the encompassing candidate
+no worse on every shared pattern, so no listed table-path aggregation can favor
+the restriction at any \(\tau\); restriction credit belongs to the
+reference-measure side controlled by `occam`. It also records the D60
+Resolution, retains W1 and the D61 `kl_forward` attribution, and adds the Case D
+scale-invariance reporting rule. Section 8 revisits the dials, states the Case
+B-to-C bridge, preserves M-open calibration as open while recognizing Case D's
+known-truth reference material, upgrades hybrid \(Z_M\) with the Case A Target B
+test, distinguishes BMS*-GP from elpd and PSIS-LOO using Case C, records the
+verification protocol, and treats F1 and F2 as scope conditions.
+
+The verification paragraph reflects the completed case review archives. All
+four reviewer rounds are recorded for every case, with the fourth, Kimi K3, run
+at the author's direction on the same round-1 packages; the findings,
+refutations, fixes, and author sign-off records are committed under
+`runs/<case>/reviews/` in this repository. D65 records the D17 local
+methods-validation provenance exception, which Section 8 states explicitly.
+
+The case sections remain on their source branches and are cited at their
+assembled-manuscript paths: Case A from `paper/case-a-vanbork` at
+`docs/paper-sie-jmp/03-case-A-external-validation.md`; Case B from
+`paper/case-b-occam-dial` at
+`docs/paper-sie-jmp/04-case-B-occam-dial.md`; Case C from
+`paper/case-c-haaf` at
+`docs/paper-sie-jmp/05-case-C-nested-constraints.md`; and Case D from
+`paper/case-d-mopen` at
+`docs/paper-sie-jmp/06-case-D-mopen-calibration.md`. Synthesis footnotes name
+the case-generating `experiments/` scripts, `runs/` artifacts, and decision
+entries. Knowledge-base paths support arguments only.
+
+**Alternatives considered:** Re-quoting case headline values was rejected in
+favor of a zero-new-empirical-numbers policy. Copying the absent case files onto
+the synthesis branch was rejected because final assembly supplies sections 3
+through 6 from their case branches. Choosing a new canonical aggregation or
+`occam` convention was rejected in favor of the D60 Resolution and the frozen
+defaults. Treating the local `kb/` vault or an uncommitted visualization path as
+numerical authority was rejected; cross-branch case artifacts and decision
+records provide the empirical provenance.
+
+**Result:** The three synthesis sections contain no re-quoted empirical
+estimate. Their only numerals belong to section and equation references,
+notation, decision identifiers, and bibliographic metadata. All requested
+case-derived additions appear in the designated sections, provenance footers
+name the supporting scripts, artifacts, and decisions, and D66 was appended at
+the end of the decision log. No experiment, artifact-generation command,
+network request, or state-mutating git operation ran during the synthesis pass.

