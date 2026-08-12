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

(iii) It subjects the machinery to four cases. The first provides external
validation of the induced-prior and soft-transfer computations against data
priors supplied by other authors, which leaves the GP scaffold itself untested;
the remaining three cover nested-model reference measures, a satisfied parameter
constraint against PSIS-LOO, and calibration under known synthetic
truth.[^intro-cases]

(iv) It makes the evaluative choices explicit as dials rather than burying them
in an implementation. Case B, section 4, jointly prices \(\tau\) and `occam`;
Case A, section 3, prices aggregation against external correspondence and the
retention of absolute divergence; Case C, section 5, shows what follows when the
table path has no volume term; and Case D, section 6, establishes why a shared
numerical \(\tau\) cannot support probability comparisons across differently
scaled metrics.

The cases produce deliberately mixed outcomes. Case A reproduces independent
closed-form targets and validates a hybrid \(Z_M\) special case, though its
examples insert the published data priors directly and therefore exercise the
induced-prior and soft-transfer machinery without testing the GP scaffold. It
also exposes the aggregation trade, because the canonical pooled convention does
not reproduce the non-overlapping target that the per-draw routes recover. Case
B uses an `informative`-configuration, MAP-based methods-validation example to
show that reference-volume normalization can change a nested-model comparison at
finite temperature. Case C returns the important null: the table path gives an
effective tie with a direction fixed by containment, while PSIS-LOO remains
directionally inconclusive for the satisfied constraint. Case D remains
synthetic-only; it contributes known-truth reference material and a
metric-scale warning without claiming a real-data result or
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
