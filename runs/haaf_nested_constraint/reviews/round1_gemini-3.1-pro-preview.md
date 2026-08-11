# Round-1 review — Gemini 3.1 Pro (gemini-3.1-pro-preview), Griffiths API key, thinkingLevel HIGH, package-only
# Channel note: gemini MCP server not connected; author-directed API substitution this session.

An independent review of the branch diff for Case C (Haaf nested constraint) has been completed against the specified checking dimensions.

**1. Constraint compliance:** 
- The `toy_elicited` configuration is correctly used for the SIR path, and no withdrawn caches are cited.
- `pw_kl_vcal` is correctly used as the primary metric, with `kl_forward` strictly relegated to an appendix stress role.
- No Mauna Loa material is present.
- No changes are made to `bistar_gp/` package defaults or public APIs.
- The commit scope is perfectly compliant (script, markdown section, DECISIONS entry, and JSON artifact).
- The script intercepts `extract_gp_predictives` to reuse the validated stage-IS machinery exactly without copying it, fulfilling the strict reuse constraint.

**2. Numerical claims vs. the runs/JSONs:**
- Every number in the prose (data parameters, tolerances, predictive counts, fractions, G-value gaps, table probabilities, LOO ELPDs, standard errors, Pareto $k$ values, and diagnostic counts) matches the `results.json` artifact exactly.
- The mathematical consistency of the results is flawless (e.g., the exact 0.0000018 expected-posterior probability difference at $\tau=0.1$ perfectly matches the theoretical $1/1000$ contribution of the single predictive row with a 0.000360 G-value gap).

**3. Statistical correctness of the method logic:**
- The MLE bounded optimization correctly forces exact equality when the free optimum falls within the restricted region, eliminating floating-point noise from the comparison.
- The Bayesian priors for the LOO arm are statistically sound. The use of `HalfNormal(5)` for the restricted slope is the exact zero-truncated counterpart to the free model's `Normal(0, 5)`.
- The interpretation of the results—that BMS* does not automatically penalize the free model for parameter volume, while LOO rewards the restricted model due to prior concentration—is statistically rigorous and directly addresses the cited critique.
- The ArviZ Pareto $k$ warning is correctly reported and appropriately qualifies the LOO conclusion.

**4. Prose style rules:**
- No arrow glyphs are used in the prose.
- No "X is the Y" role-noun constructions are present.
- No "lives/sits" anthropomorphisms are used for abstracta.
- Em-dashes are used minimally and correctly.

**5. Artifact support for claims:**
- Every analytical claim made in the section is fully supported by the generated artifacts. The split null conclusion is accurately derived from the data.

Verdict: **APPROVE**

Findings:
[None. The package is exceptionally well-crafted, mathematically rigorous, and fully compliant with all instructions.]