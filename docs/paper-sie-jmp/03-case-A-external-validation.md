# 3. Case A: external validation against van Bork, Romeijn, and Wagenmakers

van Bork, Romeijn, and Wagenmakers derive model probabilities from expected
predictive support under an independently specified data prior. Their proposal
cites the BI*/BMS* line as related prior work, but their closed-form examples
were developed without reference to the present implementation. They therefore
provide external checks on the induction and soft-transfer machinery. Because
their examples supply the data prior directly, these checks bypass its GP
construction.[^1]

## 3.1 Correspondence of the constructions

The correspondence below remains deliberately qualified. Both approaches
evaluate models against a distribution over possible data, but they need not
assign the same semantics to every intermediate quantity.

| van Bork et al. | Present notation and computation | Qualification |
|---|---|---|
| Data prior, a probability over outputs specified independently of the candidate models | \(p_0(\psi)\), a distribution over data patterns | In the general framework, GP hyperpriors induce \(p_0(\psi)\). The validation examples instead insert the authors' supplied data prior, so they do not test the GP scaffold. |
| Expected support against the data prior, expressed through Rosenkrantz-style verisimilitude | A divergence-based score \(G(\psi,\theta)\), followed by \(\bar G(\phi)\) when averaged over data patterns | Their support increases with predictive agreement; our divergence decreases with it. Additive and scale conventions therefore prevent a literal identification. |
| Prior model probability from expected posterior probability under their Eq. 4 | Normalize model support within each draw \(\psi\), then average under \(p_0(\psi)\) | This order matches expected-posterior aggregation. It does not match pooled aggregation, which sums unnormalized support across draws before model normalization. |
| Completely overlapping models with distinct within-model parameter priors | Hybrid \(Z_M=\int p_M(\phi)\exp\{-\bar G_M(\phi)/\tau\}\,d\phi\) | The within-model density \(p_M(\phi)\) replaces the usual Lebesgue or \(V_{\mathrm{ref}}\)-normalized reference measure, so the check concerns an extension of the standard \(Z_M\). |
| A restricted model nested in an encompassing model | \(M_r\subset M_e\) | We adopt their nesting notation. Normalized predictive weights over a candidate roster do not thereby become set-additive probabilities over hypotheses. |

## 3.2 Target B: completely overlapping models

Their coin example compares \(M_x\), with
\(\theta\sim\operatorname{Beta}(50,50)\), against \(M_z\), with
\(\theta\sim\operatorname{Beta}(2,2)\), under a point data prior at
\(\theta^*=1/2\). The hybrid computation approaches the published probability
for \(M_x\) monotonically over the reported low-temperature rows:

| \(\tau\) | Computed \(p(M_x)\) |
|---:|---:|
| \(10^{-2}\) | 0.792607 |
| \(10^{-4}\) | 0.840781 |
| \(10^{-6}\) | 0.841413 |
| \(10^{-7}\) | 0.841419 |
| Published target | 0.841420 |

At the smallest reported temperature, the absolute error equals
\(6.4\times10^{-7}\). The computed prior densities at the maximum-likelihood
point, 7.9589 for \(M_x\) and 1.5000 for \(M_z\), also reproduce the quoted
7.96 and 1.50 values.[^2]

The agreement follows from a Laplace special case. Around the common optimum,

\[
Z_M \approx p_M(\theta^*)
\sqrt{\frac{2\pi\tau}{G''(\theta^*)}}.
\]

Both models use the same Bernoulli family, so they share the local curvature
\(G''(\theta^*)\). That factor and the remaining common terms cancel after
normalization across models. As \(\tau\) approaches zero, the normalized
hybrid scores consequently converge to the ratio of the within-model prior
densities at \(\theta^*\). The authors' published formula thus coincides with
the shared-family, point-data-prior, zero-temperature limit of the hybrid
\(Z_M\). Target B supplies the first passing test of this within-model-prior
extension, which had previously remained an open implementation question.[^2]

## 3.3 Target A: aggregation changes the limiting answer

The non-overlapping example assigns data-prior mass 0.4 at a Bernoulli
proportion of 0.16 and mass 0.6 at 0.19, then compares point models at 0.15 and
0.20. van Bork et al.'s answer assigns model probabilities 0.4 and 0.6. The
three implemented aggregation routes behave differently:

| Aggregation route | Low-temperature result | Target A verdict |
|---|---:|---|
| Pooled, `normalize_per_draw=False` | 0.000 / 1.000 | Fails |
| Normalize each data-prior atom, then average | 0.400 / 0.600 | Exact |
| `soft_transfer(..., normalize_per_draw=True)` | 0.400 / 0.600 | Exact |

Both per-draw routes have converged to the exact target by
\(\tau=10^{-4}\).[^2] The result exposes a modeling choice rather than a
numerical defect. Pooled aggregation preserves absolute divergence magnitudes:
a draw that every candidate fits poorly contributes less total support. That
property carries the M-open inadequacy signal, but pooled aggregation fails
Target A. Expected-posterior aggregation matches Eq. 4 and avoids that failure,
but each draw must spend one full unit of credit even when every candidate fits
poorly. The latter choice therefore discards the absolute-magnitude signal.

[FORK-DECISION-PLACEHOLDER]

Pending the author's decision, the E7 artifact records only a candidate
presentation: treat aggregation as an explicit evaluation dial alongside
\(\tau\) and `occam`, retain pooled results for continuity, report the Eq. 4
variant in Case A, and reserve the `kl_forward` attribution for the appendix.
That candidate does not settle the canonical convention.[^3]

## 3.4 Measured sensitivity on the validated toy path

E7 evaluates the fork on the validated `toy_elicited` SIR path. Under the
primary `pw_kl_vcal` metric at \(\tau=1\), pooled aggregation gives model
probabilities 0.183, 0.192, 0.441, and 0.184 for Linear, Sinusoidal,
Sin+Linear, and Quadratic, respectively. This row reproduces the ratified SIR
headline. Sin+Linear remains the highest-weight candidate under every tested
aggregation variant and temperature. The maximum absolute movement between
pooled and expected-posterior aggregation equals 0.31 at \(\tau=0.1\), 0.072
at \(\tau=1\), and 0.001 at \(\tau=10\); at \(\tau=1\), the Sin+Linear
weight changes from 0.441 to 0.513.[^3]

The appendix-only `kl_forward` stress metric reveals a sharper attribution.
With pooled aggregation, the Sin+Linear weight collapses to approximately
0.000 for \(\tau\leq1\). Expected-posterior aggregation instead gives 0.696
at \(\tau=0.1\), equal at the reported precision to the raw hard-best-match
fraction of 696/1000. Expected-posterior aggregation converges to hard-win
fractions as \(\tau\) approaches zero by construction, and the artifact's
consistency check confirms that identity. The earlier `kl_forward` fragility
therefore reflects pooled-aggregation sensitivity to outlying draws, not a
property of the metric alone.[^3]

## 3.5 Multi-parameter reach under methods-validation framing

An earlier informative-configuration, MAP-based visualization arm provides a
methods-validation reach check rather than a paper-facing inferential
headline. In `runs/viz_unification/p3_priors_canonical/`, the multi-parameter
Sin+Linear candidate receives 0.992 at \(n=50\) and remains between 0.93 and
0.99 across all evaluated \(n\). This result shows that the same induced-prior
machinery extends beyond the closed-form coin targets to a richer candidate
family. It does not replace the validated `toy_elicited` SIR result above.[^4]

[^1]: 🟢 peer-reviewed — van Bork, R., Romeijn, J.-W., & Wagenmakers, E.-J. (2025). Simplicity in Bayesian nested-model comparisons: Popper's disagreement with Wrinch and Jeffreys revisited. *Synthese*. https://doi.org/10.1007/s11229-025-05286-y.
[^2]: 🟠 empirical — `experiments/vanbork_external_validation.py`; `runs/vanbork_external_validation/results.json` and `README.md`; Notes/DECISIONS.md D60.
[^3]: 🟠 empirical — `experiments/e7_convention_sensitivity.py`; `runs/e7_convention_sensitivity/results.json` and `README.md`; Notes/DECISIONS.md D61.
[^4]: 🟠 empirical — D17-recorded findings for the local, untracked `runs/viz_unification/p3_priors_canonical/` arm, generated by `bistar_viz/scripts/viz_unification_compare.py` through `bistar_viz/scripts/model_priors_laplace.py`. The informative-configuration, MAP-based values are 0.992 at \(n=50\) and 0.93–0.99 across all evaluated \(n\); the committed Notes/DECISIONS.md D17 record supplies their citation provenance and the `bistar_viz` scripts regenerate them.

---
*Provenance: `runs/vanbork_external_validation/` ·
`experiments/vanbork_external_validation.py` · Notes/DECISIONS.md D60;
`runs/e7_convention_sensitivity/` ·
`experiments/e7_convention_sensitivity.py` · Notes/DECISIONS.md D61.
The W4 reach check follows the D17-recorded citation path stated in [^4].
Argument provenance: `kb/Raw/papers/important/vanBork_Romeijn_Wagenmakers_2025_subset_problem.md`
and `kb/Wiki/Subset Problem and the Data Prior.md`.*
