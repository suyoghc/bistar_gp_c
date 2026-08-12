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
the divergence reduces to variance-weighted squared error. When a drawn pattern
carries one scalar noise variance shared across the evaluation locations, that
weight factors out of the minimization, and the variance-calibrated argmin
coincides with the Gaussian maximum-likelihood refit. The correspondence holds
algebraically rather than as a sampled regularity. Where the pattern variance
varies across locations, the weights no longer factor out and the two
projections need no longer coincide. The collection of fitted instances should
be read as samples from the pushforward of \(p_0(\psi)\) through this
projection, not as draws from a separately elicited within-model parameter
prior.[^machinery-projection]

Model-level induction averages before integrating. For candidate parameters
\(\phi\), \(\bar G(\phi)\) averages \(G\) across data patterns, and

\[
Z_M = \int \exp\{-\bar G(\phi)/\tau\}\,d\phi.
\]

The implementation reaches that average by moment matching rather than by
averaging per-draw divergences. It first collapses the sampled patterns into a
single averaged pattern \(\bar\psi\), whose mean equals the weighted mean of the
per-draw means and whose covariance adds a between-draw mean-spread term to the
weighted average of the per-draw covariances, and then evaluates \(G\) once
against \(\bar\psi\). The computed object therefore reports the divergence from
\(\bar\psi\) rather than the mean of the per-draw divergences, and the
discrepancy between them varies with \(\phi\), so it does not cancel from a
normalized comparison across candidates. Take the notation's "averaged across
data patterns" gloss as the intended reading of \(\bar G(\phi)\) and the
moment-matched evaluation as the plug-in surrogate for it used throughout. The
surrogate is not consistent for the per-draw average, because the gap between
them reflects the construction rather than sampling error that accumulating
draws would remove.[^machinery-gbar]

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

Small \(\tau\) concentrates credit on the best matches, and larger \(\tau\)
spreads it across candidates. The low-temperature limit itself depends on the
aggregation convention set out below rather than on temperature alone. As
\(\tau\) approaches zero under pooled aggregation, the sum concentrates on the
globally smallest divergences across all draws, so draws whose best available
match remains poor contribute negligible support. The per-draw conventions
defined below, row-min and expected-posterior, instead resolve each draw
separately, and where a draw has a unique closest candidate they recover hard
best-match assignment within that draw, so their low-temperature limit reflects
the rate at which candidates attain their draw's smallest divergence.
Temperature must therefore be swept and reported together with the convention,
not fixed silently.

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
with Eq. 4 matters. Canonical pooled reporting carries an explicit price: pooled
aggregation does not reproduce Case A's Target A, which the per-draw routes
recover, and the dial records that failure rather than absorbing it into a
silent default. Neither convention receives a universal-correctness claim;
Case A, section 3, reports the cost of each choice.[^machinery-aggregation]

**Remark 1 (one-sidedness under nested candidate regions).** Score a candidate
family \(M\) on draw \(\psi_i\) by its best available match,

\[
G_i(M)=\min_{\theta\in M}G(\psi_i,\theta)
=\min_{q\in\mathcal{P}(M)}G(\psi_i,q),
\]

where \(\mathcal{P}(M)\) collects the predictive distributions the family can
reach as \(\theta\) ranges over its parameters. Stating the score through the
reachable set, rather than through containment of parameter vectors, admits an
embedded restriction that carries fewer parameters than its encompassing
family: nesting requires only \(\mathcal{P}(M_r)\subseteq\mathcal{P}(M_e)\), and
the two parameter spaces may then have unequal dimension. Whenever that
containment holds, minimizing over the larger set cannot return a larger value,
so for every draw

\[
G_i(M_e)\leq G_i(M_r).
\]

The inequality follows from reachable-set containment, not from a sampled
regularity. Under any of the three conventions above, each of which is monotone
in the per-draw scores, table-path aggregation preserves that ordering and can
never favor the restriction at any \(\tau\); only the gap magnitude is
empirical. Consequently, crediting a satisfied restriction belongs to the
\(Z_M\) side, where the volume or reference-measure term controlled by `occam`
can reward the restricted region, not to the table path. Cases B and C, sections
4 and 5, provide the complementary worked instances.[^machinery-nesting]

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
[^machinery-construction]: 🟠 empirical — `bistar_gp/config.py`; the prior-only arm of `experiments/mechanism_figure_poster.py`, local methods material that remains uncommitted in this repository, serves construction visualization and supplies no reported number or posterior estimate.
[^machinery-projection]: 🟠 empirical — the `pw_kl_vcal` definition in `bistar_gp/metrics_v2.py`, from which the shared-scalar-variance coincidence of the two projections follows algebraically; conceptual account in `kb/Wiki/GP-Induced Model Priors.md`.
[^machinery-gbar]: 🟠 empirical — `bistar_gp/aggregation_v3.py`, whose `average_gp_posterior` forms the weighted mean and the covariance carrying the between-draw mean-spread term, and `bistar_gp/laplace_evidence.py`, whose `compute_G_at_params` evaluates the divergence against that averaged pattern.
[^machinery-occam]: 🟠 empirical — assembled-manuscript section 4 on `paper/case-b-occam-dial`; `experiments/occam_dial_figure.py`; `experiments/e6_nesting_monotonicity.py`; `runs/occam_dial/`; Notes/DECISIONS.md D17 and D62.
[^machinery-aggregation]: 🟠 empirical — `experiments/vanbork_external_validation.py`; `runs/vanbork_external_validation/`; `experiments/e7_convention_sensitivity.py`; `runs/e7_convention_sensitivity/`; Notes/DECISIONS.md D60 Resolution and Precision addenda, and D61.
[^machinery-nesting]: 🟠 empirical — assembled-manuscript sections 4 and 5 on the Case B and Case C branches; `runs/occam_dial/e6_results.json`; `runs/haaf_nested_constraint/results.json`; Notes/DECISIONS.md D62 and D63.
[^machinery-metrics]: 🟢 peer-reviewed — Gneiting and Raftery (2007), “Strictly proper scoring rules, prediction, and estimation,” *JASA*, 102(477), 359–378; Varin, Reid, and Firth (2011), “An overview of composite likelihood methods,” *Statistica Sinica*, 21, 5–42. W1 fixes the manuscript roles of `pw_kl_vcal` and `kl_forward`.
[^machinery-attribution]: 🟠 empirical — `experiments/e7_convention_sensitivity.py`; `runs/e7_convention_sensitivity/results.json` and `README.md`; Notes/DECISIONS.md D61.
[^machinery-scale]: 🟠 empirical — assembled-manuscript section 6 on `paper/case-d-mopen`; `experiments/regret_curves_mopen.py`; `runs/regret_curves_mopen/results.json`; Notes/DECISIONS.md D64.

---
*Provenance: no empirical estimate is re-quoted in this section.
Construction, projection, and the averaged-pattern evaluation of \(\bar G\):
`bistar_gp/config.py`, `bistar_gp/metrics_v2.py`, `bistar_gp/aggregation_v3.py`,
and `bistar_gp/laplace_evidence.py` · the prior-only mechanism arm of
`experiments/mechanism_figure_poster.py`, cited as uncommitted local methods
material for construction visualization only.
Aggregation: `runs/vanbork_external_validation/` and
`runs/e7_convention_sensitivity/` ·
`experiments/vanbork_external_validation.py` and
`experiments/e7_convention_sensitivity.py` · D60, D61.
Nesting and metric scale: `runs/occam_dial/`,
`runs/haaf_nested_constraint/`, and `runs/regret_curves_mopen/` ·
`experiments/e6_nesting_monotonicity.py`,
`experiments/haaf_nested_constraint.py`, and
`experiments/regret_curves_mopen.py` · D62, D63, D64.*
