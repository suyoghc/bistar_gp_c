# E7 — aggregation-convention sensitivity (validated toy path)

Generated 2026-08-11 by `experiments/e7_convention_sensitivity.py` (D61).
Basis: `toy_elicited`, SIR n_pred=1000 from pooled 3-seed prior-IS — the
ratified W4 path; anchor row reproduces the SIR headline exactly
(pw_kl_vcal tau=1 pooled: 0.183 / 0.192 / 0.441 / 0.184).

## Findings

1. **Primary metric (pw_kl_vcal): winner convention-robust everywhere.**
   Sin+Linear tops all three variants at every tau. Movement pooled vs
   expected-posterior: 0.31 at tau=0.1, 0.072 at tau=1 (0.441 -> 0.513),
   0.001 at tau=10. Qualitative claims unaffected; headline number moves
   modestly under Eq.-4 semantics.

2. **NEW: the kl_forward "fragility" (W1/D18) is largely an aggregation
   artifact of the pooled convention.** Pooled at tau<=1 collapses Sin+Linear
   to ~0.000 (Linear/Quadratic split the mass — outlier draws with globally
   minimal G dominate the unnormalized pool). Under per-draw conventions
   kl_forward becomes sane: expected-posterior gives Sin+Linear 0.696 at
   tau=0.1, exactly matching the raw hard-win fraction 696/1000 (as it must:
   expected-posterior at tau->0 IS the hard best-match rate). W1's framing
   ("soft tau=1 collapse under heterogeneous draw mixtures") is thereby
   attributed: it is pooled-aggregation outlier sensitivity, not a property of
   the metric alone.

3. Consistency check passed: expected_posterior(tau->0) = hard-win fractions.

## Fork input (D60, author decision pending)

- Pooled keeps absolute divergence magnitudes (M-open signal) and continuity
  with every ratified number; fails van Bork Target A.
- Expected-posterior matches van Bork Eq. 4 semantics and rescues kl_forward,
  but discards magnitudes (every draw spends one unit of credit).
- Candidate paper position: present the aggregation convention as an explicit
  evaluation dial alongside tau and occam; canonical numbers pooled, Case A
  reports the Eq.-4 variant, appendix carries the kl_forward attribution.
