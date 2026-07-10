# Plan: Reconcile and correct the GP-induced model prior `Z_Mx` and model selection

Status: **proposed** (no code changed yet). Implement after the current branch
(`fix/bms-correctness`, PR #1) is committed/merged.

Decisions locked by the user:
- **1b** — package computes the data-free `Z_Mx` (the model prior) **and** a separate,
  correctly normalized model-selection stage.
- **Occam: expose both** conventions via a toggle.
- **Unify** — one canonical implementation in the package; viz/experiment callers updated.

One theory fork remains open and must be confirmed before implementation: see §2.

---

## 0. Problem

`bistar_gp/laplace_evidence.py::compute_laplace_evidence` computes a Laplace
approximation to `log ∫ p(y|φ)·exp(−Ḡ(φ)/τ) dφ`. Verified numerically and analytically:

```
code output  =  log p(y|M,ψ)            +  log Z_Mx^{noOccam}
             =  (within-model evidence)    (GP model prior, no Occam)
```

So the function silently computes the BI* **joint** (evidence × no-Occam model prior),
but its docstring labels it the "model evidence," and it includes the data likelihood
`p(y|φ)`. Your own framework (README:90, `kb/Wiki/GP-Induced Model Priors.md`:25, the
Laplace-normalization decision log) defines `Z_Mx` as **data-free**:

```
Z_Mx = ∫ exp(−Ḡ/τ) dφ            (no Occam)
Z_Mx = ∫ p_ref(φ)·exp(−Ḡ/τ) dφ   (with Occam),   p_ref uniform = 1/V_ref
```

with the data likelihood multiplied in a *separate* stage. The reference viz script
`model_priors_laplace.py:251` already implements the data-free formula; the package
module is the outlier, and it feeds `bistar_sample_size_sweep.py:234` and
`bistar_induced_prior_v2.py:208`, producing figures inconsistent with the viz path.

---

## 1. Definitions (the exact math to implement)

Notation: `φ` = candidate parameters (dim `d`); `Ḡ(φ)` = MLL-weighted average divergence
between GP posterior samples and the candidate prediction `θ(φ)`; `τ` = transfer
temperature; `p_ref(φ)` = uniform reference prior on the parameter box, density `1/V_ref`,
`V_ref = Π (upper_k − lower_k)`.

### 1.1 Induced parameter prior (already correct in `induced_prior.py`)
```
p(φ | ψ, M) = exp(−Ḡ(φ)/τ) · p_ref(φ) / Z_prior(M),   Z_prior(M) = ∫ exp(−Ḡ/τ) p_ref dφ
```
Note `Z_prior(M)` is exactly `Z_Mx` with Occam.

### 1.2 Model prior `Z_Mx` (the data-free object; core of 1b)
Laplace around `φ_G* = argmin_φ Ḡ(φ)`, with `H_G = ∇²Ḡ(φ_G*)` (Hessian of `Ḡ`, **not** `Ḡ/τ`):
```
log Z_Mx^{noOccam} ≈ −Ḡ(φ_G*)/τ + (d/2)·log(2π·τ) − (1/2)·log|H_G|
log Z_Mx^{Occam}   ≈ log Z_Mx^{noOccam} − log V_ref
```
The `+(d/2)log τ` arises because the curvature of `Ḡ/τ` is `H_G/τ`. This matches
`model_priors_laplace.py:251-254` (with-Occam) and `model_prior_trajectory_laplace.py:278`
(no-Occam, drops `−log V_ref`).

### 1.3 Within-model evidence under the induced prior
```
p(y | M, ψ) = ∫ p(y|φ) p(φ|ψ,M) dφ = N(M) / Z_prior(M),   N(M) = ∫ p(y|φ) exp(−Ḡ/τ) p_ref dφ
```
Laplace: `log N(M)` around the **joint** MAP `φ_J* = argmax[log p(y|φ) − Ḡ/τ]`,
`H_J = ∇²(−[log p(y|φ) − Ḡ/τ])(φ_J*)`:
```
log N(M)        ≈ log p(y|φ_J*) − Ḡ(φ_J*)/τ − log V_ref + (d/2)log(2π) − (1/2)log|H_J|
log p(y|M,ψ)    = log N(M) − log Z_prior(M)        (the −log V_ref cancels here)
```
This evidence is Occam-independent (the `V_ref` cancels), consistent with the kb note
"induced parameter priors carry no complexity penalty; Occam enters only at model-prior
aggregation."

### 1.4 Full model posterior
The assembly is the central modeling decision; see §2. It combines the data-free `Z_Mx`
(§1.2), the within-model evidence (§1.3), and the joint-prior foundation (§2.1).

---

## 2. The central modeling decision — how the GP enters the model posterior

### 2.1 Foundation: one GP belief, one joint prior over (M, φ)
The GP supplies a single belief ψ. The principled way to use it is to let it induce a
**joint** prior over (model, parameters):
```
p(M, φ | ψ)  ∝  p₀(M) · exp(−Ḡ(ψ, θ_M(φ))/τ) · p_ref(φ | M)
```
where `p₀(M)` is a base model prior (usually uniform). Define `w(M,φ) = exp(−Ḡ/τ) p_ref` and
`Z_M = ∫ w(M,φ) dφ`. Marginalizing this one joint prior gives **both** lower-level objects, and
fixes their relationship:
```
model prior        p(M|ψ)   = p₀(M) Z_M / Σ_M' p₀(M') Z_M'          (this is Z_Mx, normalized)
parameter prior    p(φ|M,ψ) = w(M,φ) / Z_M                           (the induced prior)
```
Crucially `Z_M` (the model-prior integral) **is the same integral** as `Z_prior(M)` (the
parameter-prior normalizer, §1.3). They are not two independent quantities; consistency forces
`Z_M = Z_prior`. This single fact is what makes the constructions below differ.

### 2.2 Construction II — GP induces the joint prior (Bayes-consistent)
Apply Bayes with the joint prior of §2.1 and the data likelihood `p(D|φ,M)`:
```
p(M|D,ψ) ∝ p(M|ψ) · ∫ p(D|φ,M) p(φ|M,ψ) dφ
         = [p₀(M) Z_M] · [N(M) / Z_M]
         = p₀(M) · N(M),      N(M) = ∫ p(D|φ,M) exp(−Ḡ/τ) p_ref dφ
```
`Z_M` and `Z_prior` **cancel** (they are the same integral). So with uniform `p₀`, the model
posterior is simply `∝ N(M)`. Numerically verified: `Z_M · p(y|M,ψ) = N(M)` exactly.

- The GP is used **once** — as a single joint prior. There is no double counting; the apparent
  "two uses" (tilting φ, and weighting M) are two marginals of one object that cancel on combination.
- This is the faithful GP analogue of the original discrete BI*, where one prior over
  data-distributions both selects plausible instances and aggregates to model classes.
- The induced **parameter** prior is load-bearing: it is exactly what the likelihood integrates
  against. The θ-transfer figures then *drive* selection, not merely illustrate it.
- **What the current code computes is essentially N(M)** (its bug is the label "evidence", the
  missing `p_ref`/`−log V_ref`, and the wrong Laplace expansion — not the use of the data).
- Complexity control: the `p_ref = 1/V_ref` factor does **not** cancel in `N(M)`, so the posterior
  carries a `−log V_ref` penalty automatically (bigger parameter boxes are penalized). The Occam
  toggle here = whether `p_ref` includes the `1/V_ref` normalization, and it acts directly on the
  posterior.

### 2.3 Construction I — GP supplies only the model prior
Use the GP to rank classes via `Z_Mx`, but let the data speak through an **ordinary** marginal
likelihood that uses a GP-free parameter prior `p₀(φ|M)` (typically `p_ref`):
```
p(M|D,ψ) ∝ Z_Mx(ψ) · p_ord(D|M),     p_ord(D|M) = ∫ p(D|φ,M) p₀(φ|M) dφ
```
- The GP is used **once** — only at the class level. Within a model, inference is standard.
- Clean separation of concerns: `Z_Mx` (GP belief about which family is right) and `p_ord(D|M)`
  (how well the family fits) are independently interpretable factors.
- The induced **parameter** prior is *not* used in selection; it is a descriptive side-product.
- Complexity control: `p_ord(D|M)` has its own Bayesian Occam factor (the Laplace `½log|H|`),
  independent of `G`. The GP-side Occam (`−log V_ref` in `Z_Mx`) is then an *additional*, optional
  knob.
- Matches the literal kb phrasing "p(M|D) ∝ Z_Mx [prior] × p(D|M) [likelihood]" if `p(D|M)` is read
  as the ordinary evidence.

### 2.4 The combination to AVOID
`Z_Mx · p(y|M,ψ)` where `p(y|M,ψ)` is the *induced-prior* evidence `N(M)/Z_prior` is genuine
double counting: it telescopes to `Z_Mx · N(M)/Z_M = N(M)` only because `Z_M=Z_prior`, i.e. it
silently collapses to Construction II while *looking* like an extra model-prior boost. Multiplying
a GP-derived model prior by a GP-induced-prior evidence is only legitimate if the two came from
**independent** information sources, which here they do not. Do not expose this as an option.

### 2.5 Reconciling with the kb notes
The decision-log formula `p(M|D) ∝ Z_Mx × p(D|M)` is **consistent with both** constructions and
does not by itself disambiguate them: Construction I takes `p(D|M)` = ordinary evidence;
Construction II takes `p(D|M)` = induced-prior evidence and the `Z`s cancel. The kb design goals
("the prior should be gentle; selection power must come from the data likelihood") are satisfiable
under either. So this is a real choice the framework's author must make explicitly; it is not
already settled by the notes.

### 2.6 Decision criteria and recommendation

| Aspect | Construction I | Construction II |
|---|---|---|
| GP used | once, at class level | once, as joint (M,φ) prior |
| Drives selection | ordinary data fit, tilted by `Z_Mx` prior | likelihood mass ∩ GP-plausible region |
| Induced parameter prior | descriptive only | **load-bearing** (it is the prior in the evidence) |
| `Z_Mx` role | an explicit, separately-multiplied factor | a diagnostic marginal (not re-multiplied) |
| Complexity control | evidence's own `½log\|H\|` + optional `−log V_ref` | automatic `−log V_ref` in `N(M)` (Occam toggle) |
| `V_ref` (box) sensitivity | only if with-Occam | always present in the posterior |
| Extra modeling choice | needs an ordinary within-model prior `p₀(φ\|M)` | none beyond `p_ref` |
| Relation to current code | new object | current code already ≈ `N(M)` (relabel + fix) |
| Fidelity to original BI* | "prior × likelihood" reading | joint-prior-over-distributions reading |
| Paper narrative | "GP picks the family, data fits it" | "GP-induced parameter priors select the model" |

**Recommendation: implement all three assemblies as an ablation ladder, with Construction II as the
canonical method.** They share primitives, so the marginal cost is one small function (the ordinary
evidence `p_ord(D|M)`), and the contrast is a genuine results section rather than a hedge:

- **Baseline (no GP):** `p(M|D) ∝ p_ord(D|M)` with uniform model prior. The standard-Bayes null.
- **Construction I:** `p(M|D) ∝ Z_Mx · p_ord(D|M)`. GP acts only at the class level.
- **Construction II (canonical):** `p(M|D) ∝ N(M)`. GP acts at the parameter level; the induced
  parameter prior drives selection.

Each pairwise comparison isolates one contribution: baseline-vs-I = value of a GP model prior;
I-vs-II = value of the induced parameter prior on top of that; baseline-vs-II = total GP contribution.

Mark **II as canonical** on the grounds that (a) it is the Bayes-consistent posterior from a single
GP-induced joint prior, with no separable-information assumption; (b) it makes the framework's
headline mechanism — GP-induced *parameter* priors — drive selection rather than decorate it; (c) it
is the faithful GP analogue of original discrete BI*; and (d) it is closest to the existing
computation, so the fix is "relabel + correct the Laplace + add the Occam term" rather than a new
object. Present I and the baseline as **ablations/comparisons**, not co-equal alternatives, so the
paper reads as a resolved method with a robustness analysis, not an undecided one.

(This revises the earlier off-hand recommendation of I: the joint-prior derivation in §2.1–2.2 shows
II is not double counting but the consistent choice, which changes the balance.)

**Action: confirm II-as-canonical + ablation ladder before coding §3/§4.**

---

## 3. Target API (`bistar_gp/laplace_evidence.py`, canonical)

```python
def laplace_log_Z_Mx(param_space, x_eval, avg_gp, *, metric_name, tau,
                     occam: bool = False, mle_params=None) -> ZMxResult
    # data-free model prior. occam=False -> §1.2 noOccam; occam=True -> subtract log V_ref.
    # expansion point argmin Ḡ; Hessian of Ḡ. NO p(y|φ).

def laplace_log_evidence_induced(param_space, x_train, y_train, x_eval, avg_gp, *,
                                 metric_name, tau, mle_params=None) -> EvidenceResult
    # §1.3 within-model evidence p(y|M,ψ) = log N(M) − log Z_prior(M). Two Laplace solves.
    # Also exposes log N(M) directly (the Construction-II posterior kernel).

def laplace_log_evidence_ordinary(param_space, x_train, y_train, *,
                                  mle_params=None) -> EvidenceResult
    # ordinary marginal likelihood p_ord(D|M): Laplace/BIC on the likelihood with reference
    # prior p_ref, NO G. The GP-free primitive used by the baseline and Construction I.

def model_posterior(param_spaces, ..., *, construction: str, occam: bool) -> dict
    # assembles per §2. construction in {"baseline","I","II"}; II is canonical.
    #   baseline: softmax(log p_ord(D|M))
    #   I       : softmax(log Z_Mx + log p_ord(D|M))
    #   II      : softmax(log N(M))
    # Returns normalized p(M|D) + per-model components for the ablation table/figure.
```
- Keep dataclasses but split: `ZMxResult` (prior + its 3 terms), `EvidenceResult`
  (log N, log Z_prior, log evidence), `ModelPosteriorResult` (per-model components + posterior).
- Deprecate `compute_laplace_evidence` / `compute_all_laplace_evidences` (keep thin shims that
  call the new functions and emit a `DeprecationWarning`, or delete after callers migrate).
- Reuse a shared `numerical_hessian`; fix its boundary/regularization behavior (see §6, the
  curvature-fabrication issue flagged in the eval).

## 4. Concrete fixes vs current code
1. Drop `p(y|φ)` from the model-prior path (§1.2). Expansion point `argmin Ḡ`, Hessian of `Ḡ`.
2. Add the `+(d/2)log τ` and the optional `−log V_ref` (Occam toggle).
3. Implement the evidence as `log N − log Z_prior` (§1.3), not the unnormalized `log N`.
4. Assemble the posterior per the chosen Construction (§2); never multiply `Z_Mx` by the
   induced-prior evidence.

## 5. Unification / migration
- Make the package functions canonical. Update callers:
  - `bistar_viz/scripts/bistar_sample_size_sweep.py:234`
  - `experiments/bistar_induced_prior_v2.py:208`
- Refactor `model_priors_laplace.py` and `model_prior_trajectory_laplace.py` to call
  `laplace_log_Z_Mx(..., occam=True/False)` instead of their private copies, removing the
  duplicated formula (and the existing inconsistency: one includes `−log V_ref`, the other omits it).
- Resolve the `InducedPriorResult` name collision (induced_prior.py vs mechanism.py) while here.

## 6. Regression tests (`tests/test_laplace_zmx.py`)
- **Laplace vs brute force (low-d):** for `Linear` (d=3), `laplace_log_Z_Mx` within tolerance of
  a dense-grid `log ∫ exp(−Ḡ/τ) dφ` on the box. Same for `log_evidence_induced` vs grid `log N − log Z_prior`.
- **No likelihood in the prior:** `laplace_log_Z_Mx` output is invariant to permuting/scaling `y`
  (it must not depend on the data except through `avg_gp`).
- **Occam = −log V_ref:** `log Z_Mx^{Occam} − log Z_Mx^{noOccam} == −log V_ref` exactly.
- **Evidence is Occam-independent:** `log_evidence_induced` unchanged under box rescaling that
  changes `V_ref` (the `V_ref` cancels).
- **No double-use guard:** assert `Construction II` posterior `== softmax(log_evidence_induced)`
  and `Construction I` posterior `== softmax(log Z_Mx + log p(D|M))`; assert these differ, and
  that neither equals `softmax(log Z_Mx + log_evidence_induced)` (the bug).
- **Cross-check vs MC:** `laplace_log_evidence_induced` ≈ `induced_prior.compute_model_evidence_induced`
  on a 3-param model within MC tolerance.
- **Hessian sanity:** on a known quadratic `Ḡ`, recovered `½log|H_G|` matches the analytic value;
  boundary-MAP case does not fabricate ~1e17 curvature (fix the eigenvalue flooring).

## 7. Paper-figure mapping
- **Mechanism / prior transfer figure** ← `laplace_log_Z_Mx` (data-free), per GP prior config.
- **Occam-sensitivity figure** ← `laplace_log_Z_Mx` with `occam=False` vs `True` (new, defensible analysis).
- **Model-selection figure** ← `model_posterior(construction="II")` (canonical); show the
  `log Z_Mx` (GP prior) + `log p_ord(D|M)` (data fit) decomposition alongside.
- **Ablation-ladder figure/table** ← `model_posterior` for `baseline` / `I` / `II` side by side, so each
  pairwise gap isolates one GP contribution (class-level prior, parameter-level prior, total).
- **Sample-size sweep** ← rerun `bistar_sample_size_sweep.py` after it calls the canonical functions.
- Add a short methods paragraph stating that II is the canonical assembly (with the §2.1–2.2 joint-prior
  justification), that I and the baseline are ablations, the Occam default, and the `V_ref` arbitrariness
  (why no-Occam is the default; with-Occam shown as sensitivity).

## 8. Validation before regenerating figures
- Reproduce one toy case end-to-end; confirm Laplace `Z_Mx` matches the viz `model_priors_laplace`
  output (they should now be identical, modulo the Occam flag).
- Confirm `compute_model_evidence_induced` (MC) and `laplace_log_evidence_induced` agree on a 3-param model.
- Diff old vs new model rankings on the toy + Mauna Loa; document any flips (expected, since the old
  number conflated prior and likelihood).

## 9. Sequencing
1. Land PR #1 (current correctness fixes).
2. Confirm §2 (Construction I vs II).
3. Implement §3/§4 with §6 tests (new branch `fix/laplace-zmx`).
4. Migrate callers (§5), regenerate figures (§7/§8), update README + `kb/Wiki/GP-Induced Model Priors.md`
   to state the final definitions and the chosen Construction.
