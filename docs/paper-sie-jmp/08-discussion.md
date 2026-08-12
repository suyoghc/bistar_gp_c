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
