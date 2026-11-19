# Round-1 review — Kimi K3 (moonshotai/kimi-k3 via OpenRouter), package-only

## Review: SYNTHESIS package (sections 1, 2, 8 + D66)

### Dimension 1 — Constraint compliance (§0 list)
- **M2bR banner:** No citation of `samples_hmc.npz` or `runs/toy_tau_metric_comparison/`; §2.1 explicitly disclaims any `informative`-config HMC result. PASS.
- **W1:** §2.4 names `pw_kl_vcal` primary and `kl_forward` appendix-only. PASS.
- **W4:** `viz_unification`-type material is framed as `informative`-config, MAP-based, methods-validation in §1.3, §2.1, and §2.2. PASS.
- **Mauna Loa:** absent. PASS. **API/defaults:** writing-only; D66 states no computation ran. PASS.
- **Style:** no arrow glyphs; no "lives/sits"; no "X is the Y" role-noun constructions found; em-dashes appear only in the 🟢/🟠 footnote separator convention shared with the case sections. PASS.
- **Regenerability/D-entry:** no new numbers; D66 appended; scope limited to the three sections + DECISIONS. PASS.

### Dimension 2 — Numeral audit (zero-re-quote policy)
Scanned every numeral in §§1, 2, 8: all are bibliographic metadata (years, volumes, pages), identifiers (D17, D60–D66, W1, F1/F2, Eq. 4, Target B, Kimi K3), or notation (τ, \(Z_M\), \(V_{\mathrm{ref}}\), section numbers). No empirical estimate (0.441, 0.696, 0.295, 4.799, etc.) is re-quoted. PASS.

### Dimension 3 — Statistical/methodological correctness
- **Remark 1:** containment inequality is correct and correctly attributed to feasible-set inclusion; pooled, row-min, and expected-posterior aggregation are all monotone within-draw, so the pairwise ordering claim holds at every τ. One wording overreach (Finding 2).
- **Scale-invariance warning:** correct — the additive affine component cancels in softmax normalization; the multiplicative component rescales effective temperature; draw-win fractions are invariant under common positive affine rescaling. The "even under common rescaling" phrasing correctly sets up Case D's stronger candidate-specific identity. PASS.
- **B-to-C bridge:** correctly locates the restriction reward on the \(Z_M\)/`occam` side and accurately summarizes Case C's LOO local diagnostic as a local, not global, identity claim. PASS.
- **§2.2** (variance calibration reduces `pw_kl_vcal` to weighted SSE; Gaussian MLE agreement), **§8.3** (PSIS-LOO mechanics), **§8.5** (F1/F2 non-identifiability): all accurate and appropriately hedged. PASS.

### Dimension 4 — Prose style
Clean; hedges ("can permit", "largely", "methods-validation role") are consistent. PASS.

### Dimension 5 — Consistency with case sections
Case A (Target B special case, aggregation trade, D61 attribution), Case B (finite-τ crossing under `occam=True`; methods-validation framing), Case C (effective tie, containment-fixed direction, inconclusive LOO), Case D (synthetic-only, no threshold, partial early-trial coverage, F1/F2 agnosticism) are all represented without overreach. One cross-record tension (Finding 1).

## Verdict: **APPROVE**

## Findings

1. **[S3] [08-discussion.md, §8.6 vs. Notes/DECISIONS.md D66]** §8.6 states "D17 records the provenance exception for the local methods-validation reach check," while the same commit's D66 entry states "D65 records the D17 local methods-validation provenance exception, which Section 8 states explicitly." The two records attribute the exception to different decision numbers, and Case A's [^4] cites D17 only for the findings' citation provenance — why it is wrong: within one commit the provenance chain for the same exception points at two different D-numbers, so a reader cannot tell which entry is authoritative — concrete fix: align §8.6 with D66 (e.g., "D65 records the provenance exception for the D17 local methods-validation reach check") or amend D66 if D17 is intended.

2. **[S4] [02-machinery.md, Remark 1]** "Every aggregation convention above preserves the per-draw ordering, so table-path aggregation can never favor the restriction at any τ under any convention" — why it is wrong: the proof covers only the three listed conventions (all monotone within draw); "under any convention" is a universal claim that a non-monotone or draw-reweighting convention could violate, claiming more than the remark establishes — concrete fix: replace "under any convention" with "under any of these conventions" (the preceding sentence already scopes correctly).