# Frozen notation — JMP special-issue manuscript

All sections and case studies use these symbols; do not restate or vary them.
Frozen 2026-08-11 (W7 plan). Changes require editing this file first and
propagating.

| Symbol | Meaning | Source of truth |
|---|---|---|
| ψ (psi) | one data pattern: a probability distribution over outcomes at the evaluation points; one BI* table row. In the GP implementation, a sampled function f with observation variance defines ψ = N(f(x), σ²_ψ I) | JMP 2016 Fig. 1; thesis ch. 5 |
| p₀(ψ) | the data prior: the distribution over data patterns induced by the GP hyperpriors (sample hyperparameters, then a function) | mechanism figure |
| ℓ, σ²_SE, σ²_b, σ²_y | kernel hyperparameters: SE lengthscale, SE variance, linear-kernel variance, observation-noise variance | `bistar_gp/config.py` |
| G(ψ, θ) | divergence between one data pattern and one candidate predictive; per-draw, UNAVERAGED | `bistar_gp/metrics_v2.py` |
| Ḡ(φ) | G averaged across data patterns, as a function of candidate parameters φ; the object inside Z_M | `bistar_gp/laplace_evidence.py` |
| pw_kl_vcal | primary metric (W1): variance-calibrated pointwise KL, equal to GP-uncertainty-weighted MSE | W1; D10 |
| kl_forward | appendix-only stress metric (W1): full joint KL, covariance-sensitive | W1 |
| τ (tau) | Boltzmann temperature of soft transfer; τ→0 recovers hard best-match partitioning; always reported as a sweep | BMS-star Framework |
| soft transfer | p(θ \| y) ∝ Σᵢ exp(−G(ψᵢ, θ)/τ) under the POOLED convention; the aggregation-convention choice is stated explicitly wherever it matters (Case A) | D60; E7 |
| Z_M | induced model prior: ∫ exp(−Ḡ(φ)/τ) dφ (occam=False) or the V_ref-normalized variant (occam=True) | GP-Induced Model Priors |
| occam | the reference-measure flag on Z_M: False = raw Lebesgue (canonical, faithful to original BI*), True = normalize by V_ref | D3, D5, D17 |
| M_r ⊂ M_e | restricted model nested in encompassing model (van Bork et al.'s notation, adopted for Cases A/B/C) | vanBork ingest |
| SIR / prior-IS / NUTS | estimator names; toy_elicited SIR 0.441 and corrected NUTS ≈ 0.42 reported as separate-but-agreeing (M2bR banner) | WRITEUP_DECISIONS banner |

Terminology rules (W5 + global style): the N=20 toy prior is "data-elicited"
(empirical-Bayes-style, elicited from observable statistics only); uncertainty
reported at two layers (conditional bootstrap SE; independent-pool scatter).
No arrow glyphs in prose; no "X is the Y" role-noun constructions.
