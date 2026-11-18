# Adversarial cross-check results — Codex gpt-5.6-sol xhigh checking Opus singles OC1/OC5/OC8/OC9

CHECK-1: REFUTED  
Evidence:

- `experiments/haaf_nested_constraint.py:399-404` gives the free model positive density for \(b<0\), while the constrained model gives none; they are therefore not exactly the same posterior or population `elpd_loo`.
- `results.json:77-93` reproduces the local calculation: SD \(=0.0129506\), boundary \(=19.4028\) SD, Gaussian tail \(=3.65\times10^{-84}\). This is a local full-data approximation, not evidence about global posterior mass or all LOO folds.
- `experiments/haaf_nested_constraint.py:391-408,447-448` defines a nonlinear frequency model sampled from one initialization; no posterior-\(b\) summaries, fold refits, or Monte Carlo SE establish that the entire \(0.412659\) gap is estimator noise.
- The narrower literature point is correct: `05-case-C-nested-constraints.md:3-7` and the [primary article](https://link.springer.com/article/10.1007/s42113-025-00240-0) identify a null predictive difference as the reported failure mode; nevertheless, the finding’s exact-identity conclusion is unproved.

CHECK-2: CONFIRMED  
Evidence:

- `experiments/haaf_nested_constraint.py:260-263` puts every constrained candidate vector into `free_candidates`; hence `constrained_candidates` is a subset of `free_candidates`.
- `experiments/haaf_nested_constraint.py:265-280` evaluates the same \(G\) objective on those vectors, making `free_G <= constrained_G` structural rather than empirically tested.
- `experiments/haaf_nested_constraint.py:282-290` reuses the feasible free vector and overwrites `constrained_G`; `results.json:254-260` consequently records an exact nonnegative-row gap of `0.0`.
- Thus the order gates at `experiments/haaf_nested_constraint.py:292-294,718-723` cannot fail for finite deterministic evaluations under the implemented candidate construction.

CHECK-3: CONFIRMED  
Evidence:

- `results.json:77-93` records identical MLE vectors for both candidates, including \(b=0.2512769922\), \(\omega=1.0302398910\), and \(\sigma=0.3212319098\).
- `experiments/haaf_nested_constraint.py:439-448` initializes every seeded chain through `init_to_value(_initial_values(mle_parameters,...))`, so both chains begin at that same MLE.
- `results.json:364-400,469-505` and `README.md:58-61` disclose seeds and diagnostics but not the initialization strategy or values.
- From `bistar_gp/data.py:41-55`, spacing is \(20/19\); the sinusoidal likelihood at \(\omega=1.03024\) has sampled-grid aliases at \(4.93879\) and \(6.99927\). Therefore the reported \(\widehat R\le1.003\) in `05-case-C-nested-constraints.md:81-86` cannot certify exploration of unvisited modes.

CHECK-4: CONFIRMED  
Evidence:

- `experiments/haaf_nested_constraint.py:543-547` explicitly computes paired SE as \(\sqrt{20\,\mathrm{var}(d,\mathrm{ddof}=1)}\).
- From the 20 differences in `results.json:522-543`, this equals `0.262534387`; `ddof=0` gives `0.255886868`, 2.598% smaller.
- The per-model pointwise values at `results.json:311-332,416-436` reproduce the stored SEs `3.457658432` and `3.593844558` only with `ddof=0`.
- `05-case-C-nested-constraints.md:88-94` labels all three quantities “SE” without disclosing the mixed variance conventions.
# Gemini 3.1 Pro checking Opus singles OC4/OC6/OC10

CHECK-1: CONFIRMED
Evidence: Table 5.1 reports probabilities to nine decimal places (e.g., 0.500003900) and the text claims a monotonic trend based on these microscopic differences. However, `results.json` explicitly declares a cross-machine tolerance of `bms_probability_abs=0.005`, and `slope_sign.negative_count` is exactly 1, meaning the entire gap is driven by a single Monte Carlo draw out of 1000, making the 9-decimal precision statistically meaningless.

CHECK-2: CONFIRMED
Evidence: The restricted model is defined as sharing all bounds with the free model except for `b >= 0`. Because the restricted parameter space is a strict subset of the free space, the minimized primary metric `G` for the free model is mathematically guaranteed to be $\le$ the restricted model's `G` for every predictive draw. Therefore, the free model's BMS* probability is structurally bounded to be $\ge 0.5$, making the one-sided result a mathematical certainty rather than an empirical outcome "in this instance."

CHECK-3: CONFIRMED
Evidence: The section text explicitly claims the calculation "evaluates 60 locations." However, scanning the provided `results.json` reveals no `x_eval` field or any value of 60. While the number 60 appears in the `experiments/haaf_nested_constraint.py` script (`np.linspace(..., 60)`), it is not recorded in the output artifact, violating the strict traceability constraint that every reported number must be regenerable into a `runs/` artifact.