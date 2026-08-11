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
0.534121 and 0.382052 in p1 to 0.506877 and 0.464791 in p2. Changing only the
convention in the next step gives 0.007040 and 0.991758 in p3. The estimator
change narrows the gap; removing the V_ref normalization decides the verdict.
The dial figure argues about the `occam` convention's effect, not about which
model generated the data.

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
parameter space. E6 instead tests the two exact restrictions in data space.
The visualization box uses A ≥ 0.01 as a numerical cutoff, so E6 alone extends
the encompassing amplitude bound to A ≥ 0. All other bounds match the
visualization arms. The restricted optimum seeds the encompassing multi-start
optimization, and the package divergence calculation reproduces the restricted
value exactly at its embedding, within the declared 10^-10 tolerance.[^4]

For this n=50, `informative`-configuration, MAP-based averaged GP, E6
obtains min_φ Ḡ=0.045516783 for Sin+Linear, 2.424774370 for Linear, and
2.546229649 for Sinusoidal. The encompassing model improves on the restrictions
by 2.379257587 and 2.500712865, respectively. Both numerical inequalities
therefore hold by margins far above the 10^-8 comparison tolerance. This result
supports the reachable-set claim for the tested GP and parameterization; it
does not prove the claim for every data prior or parameterization.[^4]

Finite τ separates the two reference measures. One IS call per model evaluates
161 temperatures from 0.031623 through 316.227766. With `occam=False`,
Sin+Linear retains the larger pairwise Z_M throughout that grid, so neither
nested pair crosses. With `occam=True`, Linear overtakes Sin+Linear at the
log-interpolated location τ=0.295184, bracketed by 0.281838 and 0.298538.
Sinusoidal overtakes at τ=1.484355, bracketed by 1.412538 and 1.496236. Thus
low temperature supports Popper's encompassing constraint in both conventions
for this example, while V_ref normalization permits the finite-temperature
simplicity preference associated with Wrinch and Jeffreys.[^4]

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
