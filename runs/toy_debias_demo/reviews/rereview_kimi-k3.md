# Re-review — Kimi K3 (K1, K2 + changed hunks)

# Rule-4 re-review — Case E fix pass 8f1326d..a5b9cf8

## Per-finding verdicts

**K1 (README role-noun "thesis ch. 5 is the source of the program") — RESOLVED.** The fix is made in the `write_readme()` `lines` list in `experiments/toy_debias_demo.py` ("the program originates in thesis ch. 5"), exactly where I flagged it must be made, and the regenerated committed README carries the reworded line (sha256 7096cd6e…), so the fix is regeneration-safe; the docstring "X is the truth candidate" instance was likewise reworded to "serves as … as", and the implementer swept for further instances including the new FIX-8 docstring.

**K2 (acceptance rate 0.992/0.998 unreported against target 0.8) — RESOLVED.** Rather than my suggested clause, FIX-9 relabels the field to `move_fraction_by_chain` (values unchanged), adds a `move_fraction_note` in JSON explaining that pyro's counter is a post-warmup move fraction and is *not* comparable to the targeted mean Metropolis acceptance that `target_accept_prob` 0.8 sets, and adds a README Diagnostics line stating both numbers and the distinction — this fully addresses the underlying defect (an unreported number superficially contradicting the stated target), and is arguably more accurate than my proposed wording.

## Changed-hunk scan

Spot-checks that passed: the variance identity arithmetic is exact (0.0666855 − 0.2368454 − 0.1752190 = −0.3453789; halved = −0.1726894, matching `component_mean_cross_covariance`; correlation −0.17269/√(0.23685×0.17522) = −0.8477 ✓); grid-mean averaging is linear so the law-of-total-variance inversion is valid and uses ddof-0 `np.var` consistently across all three terms; the "2e-8" deviation is carried consistently through prose, README, JSON `init_strategy`, and the DECISIONS addendum; the §7.2 claim "constrain the sum more tightly than either component alone" is now backed (1.032 < 1.458 < 1.836); the sampler-settings guard fails closed in every drift direction I can construct (attribute-style calls or non-literal kwargs both land in `missing` → RuntimeError); the FIX-7 raise is a proper f-string and sits before any decomposition work; the 24 pre-existing numbers are confirmed bit-identical per the driver rerun.

## New findings

**N1 — S4 (low) — `experiments/toy_debias_demo.py`, `decompose_draws` jitter probe (FIX-7 hunk).** The probe Cholesky-tests only the summed train matrix `k_sum_xx + (noise_var + DECOMP_JITTER)·I`, but `decompose_additive_gp` performs its own internal Cholesky factorizations (the summed XX matrix and, depending on the library implementation, per-component or cross-block factorizations); if any of those internally escalate jitter via `compute_cholesky`, the escalation is not counted, so `n_draws_needing_extra_jitter` (and the README line "0 of 1000 needed jitter above the base 0.0001") potentially undercounts and overstates what was probed. Fix: narrow the claim to match the probe — e.g. "0 of 1000 draws needed escalation for the summed training-kernel Cholesky" — or extend the probe to every factorization the decomposition performs.

No other new defects found in the changed hunks; no third round required.