# Adversarial cross-check raw outputs — synthesis round

## Gemini batch 1 (SC4, SC5, SO7, SO8)
CHECK-1: REFUTED
Evidence: Section 8.1 accurately reflects Case C's findings without overstatement. It explicitly notes that for LOO "the comparison remains inconclusive" and correctly identifies the diagnostic as "the artifact's local diagnostic." This perfectly aligns with Case C's conclusion that LOO "reproduces the null-to-inconclusive failure mode without supporting a directional claim."

CHECK-2: CONFIRMED
Evidence: Section 8.5 states that BMS*-GP should report "the possibility of unresolved F1/F2 non-identifiability," omitting the other two sources. Case D explicitly states: "These artifacts cannot identify whether the localized `pw_nll` recovery asymmetry originates in F1 representability, F2 mimicry, metric behavior, or sampling noise."

CHECK-3: CONFIRMED
Evidence: Sections 2.3 and 8.1 frame the trade-off symmetrically (e.g., "Expected-posterior aggregation obtains external correspondence... while pooled aggregation retains absolute divergence magnitudes") and state "Neither convention receives a universal-correctness claim." They omit the qualitative fact established in Case A (Section 3.3) that pooled aggregation outright "Fails" Target A.

CHECK-4: CONFIRMED
Evidence: Section 1.3 lists contribution (iii) as subjecting "the machinery to four cases covering external validation," which implies the full GP construction from (i). However, Case A explicitly states that "these checks bypass its GP construction" and only validate the "induced-prior and soft-transfer machinery."
## Kimi batch 1 (SO10, SO11, SO12)
CHECK-1: REFUTED
Evidence: The sentence "Following W1, `pw_kl_vcal` provides the primary metric: variance calibration reduces it to GP-uncertainty-weighted squared error" is grammatical and coherent: "provides" means the implementation supplies the working metric, with the colon clause immediately defining it. "Provide" is not restricted to non-metric subjects (cf. "the package provides the estimator"). The same footnote correctly attributes the role assignment to W1 ("W1 fixes the manuscript roles"). The proposed fix changes wording, not sense; the alleged incoherence is a stylistic preference, not a defect.

CHECK-2: CONFIRMED
Evidence: Section 08 states "its importance ratios approximate leave-one-out posteriors, with Pareto smoothing diagnosing unstable ratios." In PSIS-LOO (Vehtari, Gelman, Gabry 2017, cited in [^discussion-loo]), the raw importance ratios target LOO-posterior/posterior density ratios and serve to reweight posterior draws for LOO predictive estimates; Pareto smoothing *stabilizes/replaces* the largest ratios, and the fitted shape estimate k-hat is the *diagnostic* of reliability. The sentence conflates smoothing (a fix) with diagnosis (k-hat's role). Case C itself uses the correct mechanics ("max Pareto k… warning", "Pareto shape values above about 0.7 can make the importance-sampling approximation unreliable"), so the discussion sentence is also inconsistent with the case it summarizes.

CHECK-3: REFUTED
Evidence: The footnote already cites Varin, Reid, and Firth (2011) alongside Gneiting and Raftery (2007) and states the operative scope clause itself: "W1 fixes the manuscript roles of `pw_kl_vcal` and `kl_forward`." The paragraph's anchor is W1's role assignment, not a propriety claim; nothing in §2.4 or elsewhere asserts that variance-calibrated `pw_kl_vcal` is a proper scoring rule — the prose describes it only as reducing to "GP-uncertainty-weighted squared error." A citation to proper-scoring-rule background in a metrics footnote does not make a propriety claim on the section's behalf, so the demanded disclaimer addresses a claim the text never makes.
## Gemini batch 2 — rerouted after Codex usage-lock (SO1 with source excerpts, SO9, KS1)
CHECK-1: REFUTED
Evidence: The text in Section 2.2 explicitly scopes the agreement, stating that the two methods "therefore agree in the prior-only mechanism check." The finding's claim that the section states the agreement "without that scoping" is factually incorrect.

CHECK-2: CONFIRMED
Evidence: Section 8.5 introduces claims about a "bias process" and an "uncertainty floor" without any citation. None of the four provided cases (A-D) address bias processes or uncertainty floors, and the Section 7 stub (which mentions bias) is not referenced, leaving the claim unsupported in the current package.

CHECK-3: CONFIRMED
Evidence: There is a direct contradiction between the section text and the commit message. Section 8.6 states that "D17 records the provenance exception," whereas the D66 diff claims that "D65 records the D17 local methods-validation provenance exception." An authoritative attribution is needed to resolve this discrepancy.
## Kimi batch 2 — rerouted (SC2 second check, SO2, SO3, SO4, SO6)
CHECK-1: REFUTED
Evidence: The sentence claims only that small τ "concentrates credit on the best matches and recovers hard best-match assignment" — a generic property of the Boltzmann softmax that is true of pooled aggregation: as τ→0 the pooled sum is dominated by the single smallest G(ψ_i, θ) pair, i.e., a hard (global) best-match assignment. The text nowhere claims pooled recovers *per-draw* hard best-match rates; that reading is imported by the reviewer. Case A's Target A (pooled → 0.000/1.000) is exactly the global-winner limit the sentence describes, not a contradiction of it. No reassignment is required.

CHECK-2: REFUTED
Evidence: The synthesis sentence describes the *order of operations* ("normalizes candidate support within each pattern and then averages"), and Case A's own mapping row 3 states "This order matches expected-posterior aggregation" — the match claim is about computation order, which is exact, not about the semantics of the per-atom quantity. Case A itself uses the unqualified phrases "Expected-posterior aggregation matches Eq. 4" and "the Eq. 4 variant purchases external correspondence," so 08's "obtains external correspondence" mirrors the case sections rather than exceeding them. The synthesis claims nothing the cases did not establish.

CHECK-3: REFUTED
Evidence: The 08 sentence states a reporting mandate ("require tau-free draw-win fractions alongside soft probabilities"), not a claim that draw-win fractions are invariant across metrics. Section 02 scopes the invariance claim precisely to "a common positive affine rescaling" and opens the reporting paragraph with "Reporting must therefore compare probabilities within a metric" — the within-metric restriction the reviewer says is missing. Case D itself calls the pw_nll raw_draw_wins diagnostic "tau-free, scale-invariant" while scoping it to a metric-specific statement; 08 does not contradict that scoping and asserts no cross-metric comparability for the fractions.

CHECK-4: REFUTED
Evidence: 08 claims only that Case D "contributes the first correct-specification reference material for this program: known-truth distributions of mean G" — true, and it does not attribute that material to `pw_kl_vcal`. The same paragraph states that a reference distribution must be "conditional on the metric, data-prior configuration, design, and noise regime," which preserves exactly the metric-dependence the reviewer says is omitted. Claiming the material exists (in legacy `pw_nll`) while requiring metric-conditional calibration is not an overclaim; the absence of a primary-metric reference is nowhere denied.

CHECK-5: REFUTED
Evidence: The reporting rule's invariance claim is explicitly and correctly scoped: "remains invariant under a common positive affine rescaling" — it never asserts invariance under candidate-specific rescaling, so no false justification is given. Moreover the metric-specificity clause the reviewer demands is present one sentence earlier: "Reporting must therefore compare probabilities within a metric, over a stated τ sweep." The preceding warning paragraph already names Case D's identity as "candidate-specific," so the candidate-specific failure mode is disclosed in the same subsection the reviewer cites.
## Opus batch (SC1, SC2, SC3) — see rereview agent transcript record
