# Round-1 review — Kimi K3 (moonshotai/kimi-k3 via OpenRouter, author-directed; package-only, no repo access)
# Channel note: run 2026-08-12 on the ORIGINAL round-1 package (same input as the other three reviewers); temperature 0.3, reasoning budget 24576, completion 49152. First attempt exhausted a 16384 budget on reasoning (finish=length) and was retried.

VERDICT: APPROVE

Findings:

1. [S4] [docs/paper-sie-jmp/03-case-A-external-validation.md, §3.4, sentence "Sin+Linear remains the highest-weight candidate under every tested aggregation variant and temperature"] — The sentence is scoped to the `pw_kl_vcal` paragraph and is true for that metric (verified against `runs/e7_convention_sensitivity/results.json`: Sin+Linear tops pooled/rowmin/expected_posterior at all five taus). However, E7 tested two metrics, and under `kl_forward` pooled the same artifact shows Sin+Linear collapsing to ~0 (4.3e-101 at τ=0.1), so an unqualified "every tested aggregation variant and temperature" is one reader-misparsing away from an artifact-contradicted claim — insert "under the primary metric" or "under `pw_kl_vcal`" into the sentence.

2. [S4] [Notes/DECISIONS.md, D60 "Scope note"] — The committed D60 entry contains the phrases "All toy and Mauna runs use equal-weight GP draws" and "Whether the toy/Mauna posteriors move materially under `normalize_per_draw=True` is UNTESTED". The §0 constraint "No Mauna Loa material of any kind" is most naturally read as governing paper-facing content (`docs/paper-sie-jmp/`), which is clean; the mention sits in an internal decision log whose pre-dating the branch is driver-verified. Flagging only for author confirmation that the constraint does not extend to committed Notes content — no fix proposed beyond that confirmation.

3. [S4] [docs/paper-sie-jmp/03-case-A-external-validation.md, footnotes [^1]–[^4]] — Each footnote citation tag contains an em-dash ("🟢 peer-reviewed —", "🟠 empirical —"). The style rule is "minimal em-dashes"; these appear to be the house citation-tag pattern rather than prose, so likely compliant, but if the rule is applied to the file mechanically these are the only instances.

Verified as correct (no findings):

- All Target B numbers (0.792607 / 0.840781 / 0.841413 / 0.841419 vs published 0.841420, abs err 6.4e-7, densities 7.9589/1.5000) match `results.json` exactly, including the unreported intermediate rows; "monotonically over the reported low-temperature rows" is accurate.
- Target A: pooled → 0.000/1.000 (2.8e-299 at τ=1e-7), both per-draw routes exactly 0.400/0.600 by τ=1e-4 — matches `rows_pooled`, `rows_perdraw`, `rows_shipped_npd_true`. Hand-check of G[0,0] = KL(Bern(0.16)||Bern(0.15)) ≈ 0.000385 reproduces the JSON value.
- E7 anchor 0.183/0.192/0.441/0.184, movements 0.31/0.072/0.001 (JSON: 0.31335/0.07201/0.00134), 0.441→0.513 (0.51268), `kl_forward` pooled collapse for τ≤1, expected-posterior 0.696 at τ=0.1 vs 696/1000 — all match the JSON.
- Constraint compliance: `pw_kl_vcal` primary with `kl_forward` explicitly appendix-only (W1); §3.5 carries full W4 framing (informative-config, MAP-based, methods-validation, subordinated to the validated SIR result); no withdrawn HMC cache or `toy_tau_metric_comparison` cited; no `bistar_gp/` default or API changes in the diff; no arrow glyphs, role-noun constructions, or lives/sits abstracta in section prose; `[FORK-DECISION-PLACEHOLDER]` intact on its own line per the work order; commit scope matches the permitted set (experiments scripts, section, DECISIONS, run JSONs/READMEs; no figures).
- The Laplace cancellation argument in §3.2 is statistically correct: shared Bernoulli family implies identical G and G'' at θ*, so the Hessian factor and common terms cancel under normalization, leaving the prior-density ratio — consistent with the script's analytic comment and the numerical convergence.
- The D17-recorded citation pattern in [^4] for the untracked viz_unification values matches the driver-verified accepted pattern; no kb path grounds any number.
- Reference title in [^1] matches the driver-verified frontmatter verbatim.