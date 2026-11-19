RE-REVIEW ROUND (HANDOFF §4 rule 4) — Case A fix pass 1, changed hunks only.
Branch paper/case-a-vanbork; fix commit 7b653cf on top of reviewed tip 31a9258.
Task: for EACH of YOUR OWN previously raised findings that entered the fix queue (per the
dispatch note), judge from the changed hunks whether the fix resolves it. Findings REJECTED
in cross-check (AC1, AC3, AC4, AC6, AO4, AO5) were deliberately NOT implemented — do not
re-litigate them; D60/D61 remain deliberately byte-untouched per the endorsed author-record
policy (their items went to the author ledger). Output per finding: 'REREVIEW-<ID>: RESOLVED'
or 'REREVIEW-<ID>: NOT-RESOLVED' plus 2-4 evidence lines. Additionally report any NEW defect
INTRODUCED BY the changed hunks (hunks only; no scope expansion). Round-1 record:
runs/vanbork_external_validation/reviews/VERDICTS.md.

=== IMPLEMENTER FIX REPORT ===
Implemented all nine fixes.

1. **FIX-1:** Reframed the hard-fraction identity as analytic, cited 0.696 to E7 `results.json`, and attributed 696/1000 to D18 and the E7 README.

   Verbatim corrected sentences:

   > Expected-posterior aggregation instead gives 0.696 at \(\tau=0.1\) in the E7 `results.json`. Analytically, expected-posterior aggregation converges by construction to hard best-match fractions as \(\tau\) approaches zero. At the reported precision, the E7 value equals the `toy_elicited` SIR hard fraction 0.696 (696/1000) in the committed D18 record, a correspondence also noted in the E7 README.

2. **FIX-2:** Relabeled the Target A row as shipped per-draw-minimum-shift semantics and explicitly distinguished it from Eq. 4 rowwise posterior normalization, including their shared zero-temperature unique-winner limit.

3. **FIX-3:** Qualified the mapping table with the infinite-data Bayesian-posterior versus zero-temperature Boltzmann-softmax distinction.

4. **FIX-4:** Relabeled 0.841420 as the double-precision evaluation of the authors’ closed form and corrected D65 accordingly.

   Verbatim corrected sentences:

   > The paper prints the prior densities as 7.96 and 1.50 and the model weight as approximately 0.84; the quotient formed from those printed densities equals 0.841438. Thus, the six-decimal comparison uses their closed form evaluated at double precision rather than a printed six-decimal value. At the smallest reported temperature, the absolute error against that evaluated limit equals \(6.4\times10^{-7}\).

5. **FIX-5:** Changed both body and footnote wording to “stays at or above 0.93”; aligned D65 as well.

6. **FIX-6:** Used the data-pattern atom \(\psi^*=1/2\), retained \(\theta\) for candidate parameters, added \(\bar G(\phi)=G(\psi^*,\phi)\), and aligned the Laplace curvature notation.

7. **FIX-7:** Changed “induction” to “induced-prior.”

8. **FIX-8:** Removed the unused `fmc` import. The one permitted E7 rerun exited successfully. Regenerated output differed only in:

   - saved: `"generated": "2026-08-11"`
   - regenerated: `"generated": "2026-08-12"`

   After excluding that line, the byte streams were identical. The saved artifact was restored; its SHA-256 remains `0b3e2924ec857e4662c7242f326e26960d5d7621adb3145552eadc395f8db22c`.

9. **FIX-9:** Added that all variants use the same \(G\) matrix from one \(n_{\mathrm{pred}}=1000\) SIR realization, making movements paired differences.

Final modified files:

- [03-case-A-external-validation.md](/Users/sc8918/Documents/GitHub/bistar_gp_c/docs/paper-sie-jmp/03-case-A-external-validation.md:1)
- [DECISIONS.md](/Users/sc8918/Documents/GitHub/bistar_gp_c/Notes/DECISIONS.md:6153), D65 only
- [e7_convention_sensitivity.py](/Users/sc8918/Documents/GitHub/bistar_gp_c/experiments/e7_convention_sensitivity.py:44)

D60–D64 retain their pre-edit hash exactly. Both committed run artifacts and their READMEs retain their pre-edit hashes. `[FORK-DECISION-PLACEHOLDER]` remains intact exactly once. Rejected fixes were not implemented. No git commands, network access, dependencies, or additional experiment runs were used. No deviations.
=== FIX DIFF STAT ===
 Notes/DECISIONS.md                                 | 13 ++--
 .../paper-sie-jmp/03-case-A-external-validation.md | 72 +++++++++++++---------
 experiments/e7_convention_sensitivity.py           |  1 -
 3 files changed, 51 insertions(+), 35 deletions(-)

=== FIX DIFF (full) ===
diff --git a/Notes/DECISIONS.md b/Notes/DECISIONS.md
index fab50ce..557ea59 100644
--- a/Notes/DECISIONS.md
+++ b/Notes/DECISIONS.md
@@ -5850,9 +5850,9 @@ The multi-parameter paragraph follows W4: it labels
 `runs/viz_unification/p3_priors_canonical/` as an
 `informative`-configuration, MAP-based methods-validation check. Because that
 directory remains local and untracked, its 0.992 Sin+Linear value at \(n=50\)
-and 0.93–0.99 range across evaluated \(n\) use the committed D17-recorded
-citation pattern and name the regenerating `bistar_viz` scripts explicitly.
-They do not enter the validated `toy_elicited` SIR headline.
+and values at or above 0.93 across evaluated \(n\) use the committed
+D17-recorded citation pattern and name the regenerating `bistar_viz` scripts
+explicitly. They do not enter the validated `toy_elicited` SIR headline.
 
 **Alternatives considered:** Selecting pooled aggregation was rejected because
 it would preempt the author and would leave Target A unresolved. Selecting
@@ -5865,7 +5865,8 @@ and modifying scripts or run artifacts were all rejected by the Case A work
 order.
 
 **Result:** The section reports Target B's progression from 0.792607 to
-0.841419 against the published 0.841420, with absolute error
+0.841419 against their closed form evaluated at double precision (0.841420 to
+six decimals), with absolute error against that evaluated limit
 \(6.4\times10^{-7}\), and connects the agreement to cancellation of shared
 Bernoulli curvature in the hybrid Laplace approximation. It reports Target A
 as 0.000/1.000 under pooled aggregation versus the exact 0.400/0.600 under both
@@ -5876,4 +5877,6 @@ the 0.31, 0.072, and 0.001 maximum movements, and the appendix-only
 under expected-posterior aggregation, equal to 696/1000 hard wins at the
 reported precision. This branch commits D60 and D61, which record the finalized
 compute provenance, together with D65. No experiment or artifact-generation
-command ran, and neither finalized run directory was modified.
+command ran during the original section-drafting pass. The review fix pass ran
+the single authorized E7 verification; its regenerated JSON differed only in
+the generated-date field, and the saved artifact was restored afterward.
diff --git a/docs/paper-sie-jmp/03-case-A-external-validation.md b/docs/paper-sie-jmp/03-case-A-external-validation.md
index 23caa3a..27c9808 100644
--- a/docs/paper-sie-jmp/03-case-A-external-validation.md
+++ b/docs/paper-sie-jmp/03-case-A-external-validation.md
@@ -4,9 +4,9 @@ van Bork, Romeijn, and Wagenmakers derive model probabilities from expected
 predictive support under an independently specified data prior. Their proposal
 cites the BI*/BMS* line as related prior work, but their closed-form examples
 were developed without reference to the present implementation. They therefore
-provide external checks on the induction and soft-transfer machinery. Because
-their examples supply the data prior directly, these checks bypass its GP
-construction.[^1]
+provide external checks on the induced-prior and soft-transfer machinery.
+Because their examples supply the data prior directly, these checks bypass its
+GP construction.[^1]
 
 ## 3.1 Correspondence of the constructions
 
@@ -18,7 +18,7 @@ assign the same semantics to every intermediate quantity.
 |---|---|---|
 | Data prior, a probability over outputs specified independently of the candidate models | \(p_0(\psi)\), a distribution over data patterns | In the general framework, GP hyperpriors induce \(p_0(\psi)\). The validation examples instead insert the authors' supplied data prior, so they do not test the GP scaffold. |
 | Expected support against the data prior, expressed through Rosenkrantz-style verisimilitude | A divergence-based score \(G(\psi,\theta)\), followed by \(\bar G(\phi)\) when averaged over data patterns | Their support increases with predictive agreement; our divergence decreases with it. Additive and scale conventions therefore prevent a literal identification. |
-| Prior model probability from expected posterior probability under their Eq. 4 | Normalize model support within each draw \(\psi\), then average under \(p_0(\psi)\) | This order matches expected-posterior aggregation. It does not match pooled aggregation, which sums unnormalized support across draws before model normalization. |
+| Prior model probability from expected posterior probability under their Eq. 4 | Normalize model support within each draw \(\psi\), then average under \(p_0(\psi)\) | This order matches expected-posterior aggregation. It does not match pooled aggregation, which sums unnormalized support across draws before model normalization. Their Eq. 4 treats each per-atom quantity as a Bayesian posterior model probability under an infinite-data idealization, whereas ours applies a Boltzmann softmax as \(\tau\) approaches zero. Target A agreement follows because both collapse to the same hard nearest-model assignment. |
 | Completely overlapping models with distinct within-model parameter priors | Hybrid \(Z_M=\int p_M(\phi)\exp\{-\bar G_M(\phi)/\tau\}\,d\phi\) | The within-model density \(p_M(\phi)\) replaces the usual Lebesgue or \(V_{\mathrm{ref}}\)-normalized reference measure, so the check concerns an extension of the standard \(Z_M\). |
 | A restricted model nested in an encompassing model | \(M_r\subset M_e\) | We adopt their nesting notation. Normalized predictive weights over a candidate roster do not thereby become set-additive probabilities over hypotheses. |
 
@@ -26,9 +26,9 @@ assign the same semantics to every intermediate quantity.
 
 Their coin example compares \(M_x\), with
 \(\theta\sim\operatorname{Beta}(50,50)\), against \(M_z\), with
-\(\theta\sim\operatorname{Beta}(2,2)\), under a point data prior at
-\(\theta^*=1/2\). The hybrid computation approaches the published probability
-for \(M_x\) monotonically over the reported low-temperature rows:
+\(\theta\sim\operatorname{Beta}(2,2)\), under a data prior that places a point
+mass at \(\psi^*=1/2\). The hybrid computation approaches the published
+probability for \(M_x\) monotonically over the reported low-temperature rows:
 
 | \(\tau\) | Computed \(p(M_x)\) |
 |---:|---:|
@@ -36,22 +36,28 @@ for \(M_x\) monotonically over the reported low-temperature rows:
 | \(10^{-4}\) | 0.840781 |
 | \(10^{-6}\) | 0.841413 |
 | \(10^{-7}\) | 0.841419 |
-| Published target | 0.841420 |
+| Their closed form, evaluated at double precision | 0.841420 |
 
-At the smallest reported temperature, the absolute error equals
+The paper prints the prior densities as 7.96 and 1.50 and the model weight as
+approximately 0.84; the quotient formed from those printed densities equals
+0.841438. Thus, the six-decimal comparison uses their closed form evaluated at
+double precision rather than a printed six-decimal value. At the smallest
+reported temperature, the absolute error against that evaluated limit equals
 \(6.4\times10^{-7}\). The computed prior densities at the maximum-likelihood
 point, 7.9589 for \(M_x\) and 1.5000 for \(M_z\), also reproduce the quoted
 7.96 and 1.50 values.[^2]
 
-The agreement follows from a Laplace special case. Around the common optimum,
+The agreement follows from a Laplace special case. With a point data prior,
+\(\bar G(\phi)=G(\psi^*,\phi)\). Around the common candidate optimum
+\(\theta^*=\psi^*=1/2\),
 
 \[
 Z_M \approx p_M(\theta^*)
-\sqrt{\frac{2\pi\tau}{G''(\theta^*)}}.
+\sqrt{\frac{2\pi\tau}{\bar G_M''(\theta^*)}}.
 \]
 
 Both models use the same Bernoulli family, so they share the local curvature
-\(G''(\theta^*)\). That factor and the remaining common terms cancel after
+\(\bar G_M''(\theta^*)\). That factor and the remaining common terms cancel after
 normalization across models. As \(\tau\) approaches zero, the normalized
 hybrid scores consequently converge to the ratio of the within-model prior
 densities at \(\theta^*\). The authors' published formula thus coincides with
@@ -70,10 +76,14 @@ three implemented aggregation routes behave differently:
 |---|---:|---|
 | Pooled, `normalize_per_draw=False` | 0.000 / 1.000 | Fails |
 | Normalize each data-prior atom, then average | 0.400 / 0.600 | Exact |
-| `soft_transfer(..., normalize_per_draw=True)` | 0.400 / 0.600 | Exact |
+| Shipped `normalize_per_draw=True` semantics (per-draw minimum shift) | 0.400 / 0.600 | Exact |
 
 Both per-draw routes have converged to the exact target by
-\(\tau=10^{-4}\).[^2] The result exposes a modeling choice rather than a
+\(\tau=10^{-4}\).[^2] The shipped semantics and Eq. 4 aggregation remain
+distinct computations: the former subtracts per-row minima and normalizes once
+after pooling, whereas the latter normalizes each row into a model posterior
+before averaging. They coincide in the \(\tau\)-to-zero unique-winner limit
+exercised by Target A. The result exposes a modeling choice rather than a
 numerical defect. Pooled aggregation preserves absolute divergence magnitudes:
 a draw that every candidate fits poorly contributes less total support. That
 property carries the M-open inadequacy signal, but pooled aggregation fails
@@ -95,36 +105,40 @@ E7 evaluates the fork on the validated `toy_elicited` SIR path. Under the
 primary `pw_kl_vcal` metric at \(\tau=1\), pooled aggregation gives model
 probabilities 0.183, 0.192, 0.441, and 0.184 for Linear, Sinusoidal,
 Sin+Linear, and Quadratic, respectively. This row reproduces the ratified SIR
-headline. Sin+Linear remains the highest-weight candidate under every tested
-aggregation variant and temperature. The maximum absolute movement between
-pooled and expected-posterior aggregation equals 0.31 at \(\tau=0.1\), 0.072
-at \(\tau=1\), and 0.001 at \(\tau=10\); at \(\tau=1\), the Sin+Linear
+headline. Within each metric, all three aggregation variants use the same
+\(G\) matrix from one SIR realization (\(n_{\mathrm{pred}}=1000\)), so the
+reported movements are paired differences rather than differences of
+independent estimates. Sin+Linear remains the highest-weight candidate under
+every tested aggregation variant and temperature. The maximum absolute movement
+between pooled and expected-posterior aggregation equals 0.31 at \(\tau=0.1\),
+0.072 at \(\tau=1\), and 0.001 at \(\tau=10\); at \(\tau=1\), the Sin+Linear
 weight changes from 0.441 to 0.513.[^3]
 
 The appendix-only `kl_forward` stress metric reveals a sharper attribution.
 With pooled aggregation, the Sin+Linear weight collapses to approximately
-0.000 for \(\tau\leq1\). Expected-posterior aggregation instead gives 0.696
-at \(\tau=0.1\), equal at the reported precision to the raw hard-best-match
-fraction of 696/1000. Expected-posterior aggregation converges to hard-win
-fractions as \(\tau\) approaches zero by construction, and the artifact's
-consistency check confirms that identity. The earlier `kl_forward` fragility
-therefore reflects pooled-aggregation sensitivity to outlying draws, not a
-property of the metric alone.[^3]
+0.000 for \(\tau\leq1\). Expected-posterior aggregation instead gives 0.696 at
+\(\tau=0.1\) in the E7 `results.json`. Analytically, expected-posterior
+aggregation converges by construction to hard best-match fractions as \(\tau\)
+approaches zero. At the reported precision, the E7 value equals the
+`toy_elicited` SIR hard fraction 0.696 (696/1000) in the committed D18 record,
+a correspondence also noted in the E7 README. The earlier `kl_forward`
+fragility therefore reflects pooled-aggregation sensitivity to outlying draws,
+not a property of the metric alone.[^3]
 
 ## 3.5 Multi-parameter reach under methods-validation framing
 
 An earlier informative-configuration, MAP-based visualization arm provides a
 methods-validation reach check rather than a paper-facing inferential
 headline. In `runs/viz_unification/p3_priors_canonical/`, the multi-parameter
-Sin+Linear candidate receives 0.992 at \(n=50\) and remains between 0.93 and
-0.99 across all evaluated \(n\). This result shows that the same induced-prior
+Sin+Linear candidate receives 0.992 at \(n=50\) and stays at or above 0.93
+across all evaluated \(n\). This result shows that the same induced-prior
 machinery extends beyond the closed-form coin targets to a richer candidate
 family. It does not replace the validated `toy_elicited` SIR result above.[^4]
 
 [^1]: 🟢 peer-reviewed — van Bork, R., Romeijn, J.-W., & Wagenmakers, E.-J. (2025). Simplicity in Bayesian nested-model comparisons: Popper's disagreement with Wrinch and Jeffreys revisited. *Synthese*. https://doi.org/10.1007/s11229-025-05286-y.
 [^2]: 🟠 empirical — `experiments/vanbork_external_validation.py`; `runs/vanbork_external_validation/results.json` and `README.md`; Notes/DECISIONS.md D60.
-[^3]: 🟠 empirical — `experiments/e7_convention_sensitivity.py`; `runs/e7_convention_sensitivity/results.json` and `README.md`; Notes/DECISIONS.md D61.
-[^4]: 🟠 empirical — D17-recorded findings for the local, untracked `runs/viz_unification/p3_priors_canonical/` arm, generated by `bistar_viz/scripts/viz_unification_compare.py` through `bistar_viz/scripts/model_priors_laplace.py`. The informative-configuration, MAP-based values are 0.992 at \(n=50\) and 0.93–0.99 across all evaluated \(n\); the committed Notes/DECISIONS.md D17 record supplies their citation provenance and the `bistar_viz` scripts regenerate them.
+[^3]: 🟠 empirical — `experiments/e7_convention_sensitivity.py`; `runs/e7_convention_sensitivity/results.json` and `README.md`; Notes/DECISIONS.md D61. The committed Notes/DECISIONS.md D18 record supplies the `toy_elicited` SIR hard fraction 0.696 (696/1000), whose correspondence with E7 is also noted in the E7 README.
+[^4]: 🟠 empirical — D17-recorded findings for the local, untracked `runs/viz_unification/p3_priors_canonical/` arm, generated by `bistar_viz/scripts/viz_unification_compare.py` through `bistar_viz/scripts/model_priors_laplace.py`. The informative-configuration, MAP-based Sin+Linear candidate receives 0.992 at \(n=50\) and stays at or above 0.93 across all evaluated \(n\); the committed Notes/DECISIONS.md D17 record supplies their citation provenance and the `bistar_viz` scripts regenerate them.
 
 ---
 *Provenance: `runs/vanbork_external_validation/` ·
diff --git a/experiments/e7_convention_sensitivity.py b/experiments/e7_convention_sensitivity.py
index 6e33e61..52fd2f8 100644
--- a/experiments/e7_convention_sensitivity.py
+++ b/experiments/e7_convention_sensitivity.py
@@ -42,7 +42,6 @@ import torch
 torch.set_default_dtype(torch.float64)
 
 import prior_sensitivity_study as pss
-import fit_method_metric_comparison as fmc
 from bistar_gp import generate_toy_data
 from bistar_gp.candidates import build_toy_candidates
 
