# Adversarial cross-check — Gemini 3.1 Pro (checks A/B/C on Opus singles F9/F10/F11)

VERDICT: REVISE

1. S3 scope-or-framing (CHECK-A). `paper/synthesis-sections/08-discussion.md` (assembly target).
Finding: CONFIRMED. The inclusion of Case E (section 7) makes the universal claim in the previously committed section 8.6 factually false. Because Codex (gpt-5.6-sol) was usage-locked and absent for this round, Case E's review package contains three models, not four. Scoping the sentence at assembly is a necessary factual correction distinct from the already-known 8.5 footnote staleness.
Defective text: "All four reviewer rounds are recorded for every case, with the fourth, Kimi K3, run at the author's direction..."
Concrete fix: Scope the sentence for assembly to accurately reflect the protocol substitutions: "All four reviewer rounds are recorded for Cases A–D (the section 7 demonstration round ran three models, with the fourth disclosed absent), with Kimi K3 run at the author's direction..."

2. S3 scope-or-framing (CHECK-B). `docs/paper-sie-jmp/07-debias-bridge.md`, line 16.
Finding: CONFIRMED. Section 7's opening architectural claim promises that the *same* object handles evaluation and mitigation, but the text never explicitly connects the MAP-initialized HMC posterior decomposed here back to the evaluation of that same configuration in section 3.4. Adding a cross-reference closes this gap seamlessly without conflating the `pw_kl_vcal` (evaluation) estimator with the exact marginalization (mitigation) estimator.
Defective text: "## 7.1 The demonstration\n\nThe data come from `generate_toy_data()` at its defaults"
Concrete fix: Insert an explicit link establishing the continuity: "## 7.1 The demonstration\n\nSection 3.4 previously evaluated candidate models on this instance, finding that the composite SE-plus-linear structure outperformed the SE-only structure under the `pw_kl_vcal` metric. Here we proceed to mitigation on that same composite posterior.\n\nThe data come from `generate_toy_data()` at its defaults"

3. S3 scope-or-framing (CHECK-C). `docs/paper-sie-jmp/07-debias-bridge.md`, line 21.
Finding: CONFIRMED. The `toy_elicited` prior, as defined in `bistar_gp/config.py`, sets its lognormal medians using empirical summaries of this exact N=20 sample. Section 7 is the only section reporting a mathematical coverage probability (0.866). Failing to disclose that this interval relies on a prior informed by the same training data risks overstating the out-of-sample validity of the coverage metric.
Defective text: "The GP uses the SE plus linear additive kernel under the `toy_elicited` data-elicited prior, the configuration validated for this N=20 instance."
Concrete fix: Extend the sentence to transparently scope the conditioning: "The GP uses the SE plus linear additive kernel under the `toy_elicited` data-elicited prior (whose empirical-Bayes construction sets medians from this same sample's summaries, a conditioning the coverage number below inherits), the configuration validated for this N=20 instance."

4. S4 style-or-mechanics (Statistical Checklist - Prose vs JSON). `docs/paper-sie-jmp/07-debias-bridge.md`.
Finding: Verified clean. Every prose number in section 7 (RMSEs 1.430, 0.403; reductions 1.028, 71.9%; chains 1.431/1.430 and 0.403/0.402; coverage 0.866 / 174 points; widths 1.836, 1.032; R-hat 1.0025; slope CI bounds) traces perfectly to `results.json` byte-for-byte with correct statistical rounding. No fix required.

5. S4 style-or-mechanics (Statistical Checklist - Exact Mixture & Total Variance Math). `experiments/toy_debias_demo.py`.
Finding: Verified clean. The script impeccably implements the Law of Total Variance in `total_variance_sd` (`var_draws.mean() + mean_draws.var()`). The bisection approach for `mixture_central_interval` correctly integrates the exact CDF of the Gaussian mixture. The decision in D67 to reject `decompose_model_hmc` (which drops within-draw conditional variance) in favor of this exact bisection over all 1000 draws was computationally rigorous and mathematically mandatory for honest coverage bands. No fix required.

6. S4 style-or-mechanics (Statistical Checklist - Framing Hygiene). `docs/paper-sie-jmp/07-debias-bridge.md`.
Finding: Verified clean. The statistical presentation exhibits exceptional hygiene across the board: (1) It safely and correctly discloses that the identical MAP initialization restricts R-hat to within-mode mixing on a known multi-basin topology. (2) It juxtaposes the composite RMSE (1.430) against the true bias process RMS (1.451), correctly anchoring the magnitude. (3) It rightly disclaims the coverage rate on the highly correlated 201-point grid as a pointwise summary rather than an independent-trial calibration. (4) It leverages the width difference (1.836 debiased vs 1.032 composite) to concretely illustrate the "uncertainty floor" dictated by negative posterior cross-covariance between non-orthogonal components. No fix required.

7. S4 style-or-mechanics (Statistical Checklist - Style Rules). `docs/paper-sie-jmp/07-debias-bridge.md`.
Finding: Verified clean. The prose complies perfectly with the negative constraints: no arrow glyphs, no "lives/sits", minimal em-dashes, and no "X is the Y" role-noun violations (employing active, compliant phrasings like "names the linear term the bias" and "identifying the linear component as bias"). No fix required.