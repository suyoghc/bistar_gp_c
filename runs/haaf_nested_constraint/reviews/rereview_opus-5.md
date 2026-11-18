# Re-review — Opus 5 (raiser of OC1-OC10), repo access, changed hunks of 0ce03ba

REREVIEW-OC1-NARROWED: RESOLVED

- All three round-1 false claims are gone from the file: `grep` for "different support", "On its face", "categorical LOO failure" returns nothing in `docs/paper-sie-jmp/05-case-C-nested-constraints.md`, `runs/haaf_nested_constraint/README.md`, or `Notes/DECISIONS.md`. The replacement at section:113-133 is accurate in both directions: it keeps the affirmative core ("The two slope priors coincide up to normalization on $b>0$, so LOO has no structural contrast wherever negative-slope posterior mass is negligible") and explicitly disclaims what the cross-check refuted ("does not prove that the global posteriors or leave-one-out fold posteriors are exactly identical … does not establish that the entire observed gap comes from estimator noise").
- The new diagnostic reproduces independently to float precision: an independent Jacobian at the recorded MLE gives slope SD 0.012950550589627555, boundary distance 19.40280379889375, tail 3.6537543119486e-84, against `results.json` `candidate_definition.local_gaussian_slope_diagnostic` values 0.012950550589627553 / 19.402803798893753 / 3.653754311948442e-84; the section's rounded 0.0129506 / 19.4028 / 3.65e-84 are correct roundings.
- The hedges are individually checkable, not decorative: 0.413/0.256 = 1.613, so "smaller than twice its paired SE" holds under the *new* ddof=0 SE (it was 1.572 before, so the fix tightened rather than helped itself); "the paired SE covers data-level pointwise variability only, without MCMC error" is the correct scope statement for sqrt(n·var(pointwise_differences)).
- The Haaf attribution ("this kind of null-to-inconclusive LOO difference as the failure mode for a satisfied nested constraint") is within what the cited abstract supports ("More constrained models are not favored even when data are compatible with the constraint"), and the closing sentence reproduces the null-to-inconclusive failure mode without supporting a directional claim.

REREVIEW-OC2: RESOLVED
- `requirements.txt:8` now reads `arviz>=0.17`; `pyproject.toml:19` adds `"arviz>=0.17"` to `[project].dependencies`. Both manifests were previously silent on arviz.
- The README's fresh-clone regeneration block can now reach `import arviz as az` from a manifest-driven install, so §0's regenerability rule is met.
- No unrelated dependency churn: `pyro-ppl>=1.8` was already declared and unchanged; the diff is exactly one added line per manifest.

REREVIEW-OC3: RESOLVED
- The misleading sentence is deleted outright — `grep -n "kl_forward\|0.0006"` on the section returns nothing, so the "also remains within 0.0006 of an equal split" corroboration claim no longer exists in the paper text.
- The relocated documentation (README "Appendix-only `kl_forward` stress note", `results.json` `bms_star.appendix_metric_diagnostic`) states all three substantive points raised: pooled degeneracy at exactly [0.5, 0.5] (`pooled_exact_half_at_every_tau: true`, confirmed against the regenerated tables), the expected-posterior sign reversal (`reverses_primary_metric_direction: true`, differing row 984 favouring the restricted candidate by 11.160 nats), and evaluation at `pw_kl_vcal` optima with σ from unweighted RMS residuals so "the primary nesting inequality does not apply".
- The implementer's correction to the round-1 parenthetical is right and accepted: row 984 has 500.142 vs 488.982, while the 5.92e10 maximum is row 733 with `constrained_minus_free_G: 0.0`. The round-1 magnitude was inferred from the column mean (sum 6.27e10) rather than the max. The corrected mechanism also checks out — all five expected-posterior `kl_forward` values reconstruct from the 11.160-nat gap alone and match the JSON to 15 decimals, and `differing_row_weight_underflow_by_tau` {0.1: true, 0.3: true, 1.0/3.0/10.0: false} is what direct exp-underflow arithmetic gives.
- One residual imprecision, non-blocking: the rendered README collapses both regimes into "contributes below float64 aggregate resolution", which is true a fortiori at τ=0.1/0.3 but understates that those two are exact underflow; the per-τ split is preserved exactly in `results.json`.

REREVIEW-OC4: RESOLVED
- Table 5.1 now reports `0.500` in all twenty cells, consistent with the artifact's own `tolerances.cross_machine_rerun.bms_probability_abs: 0.005`.
- The prose replacement is verifiable: recomputing every gap from `results.json` `bms_star.tables.pw_kl_vcal` gives a maximum of 7.7997e-6, so "smaller than 10^-5 at every τ under both conventions" holds, and "comes entirely from the single negative-slope draw" follows from the 999 exactly-equal rows.
- The monotonicity claim is now correctly attributed ("follows deterministically from the Boltzmann aggregation, not from a measured temperature effect"), and full precision is retained in the artifact rather than the paper table, which is the right split.

REREVIEW-OC5: RESOLVED
- Section:41-48 now states the ordering as protocol identity (M_r ⊂ M_e implies min over M_r ≥ min over M_e), names the cross-seeded pools as what enforces it numerically, and says the gates "guard against machinery regressions; they do not provide an empirical nesting test".
- "The nesting check passed at a 2×10^-7 absolute tolerance" is gone (grep: no hits); the 999-row result is now stated as "the primary G gap equaled exactly zero", which is what re-evaluating the same feasible vector produces.
- The same reframing propagates to README and D63.

REREVIEW-OC6: RESOLVED
- A dedicated paragraph now precedes Table 5.1: "The restricted candidate can never exceed the free candidate under either aggregation at any τ; only the gap's magnitude depends on the sampled predictives."
- The instance-framing is removed ("in this instance" and "Here that event occurs once in 1,000 SIR predictives" both return no grep hits); the closing now reads "a one-sided direction fixed by nesting and a magnitude determined by the single negative-slope SIR draw".
- Verified empirically: all ten table entries have free minus restricted ≥ 0, matching the asserted bound.

REREVIEW-OC7: RESOLVED
- Section:21-26 now says the candidates "receive four shared base starts", that "the restricted fit additionally receives the free solutions, clipped at b=0 when necessary", and that "each candidate's selection pool includes the other candidate's feasible vectors" — each clause maps to `base_starts()` (four ω seeds 0.5/1.0/1.5/2.0), `start[3] = max(0.0, start[3])`, and the cross-seeded pools.
- The purpose clause ("forces exact equality at shared optima instead of turning optimizer noise into a gap") is the correct reason and is mirrored in `results.json` `candidate_definition.fit_protocol`.
- "use the same starts" no longer appears anywhere in section, README, or D63.

REREVIEW-OC8: RESOLVED
- Both sampler blocks in `results.json` now carry `init_strategy` with `name: "init_to_value"`, all six initial values, and `same_values_for_every_chain: true`; the two blocks are identical, confirming the section's disclosure.
- The six values printed in the section round correctly from the recorded MLE, and none of `_initial_values`' clamps bind at these values.
- The interpretive limit is stated: "These diagnostics support within-mode convergence only, not exploration across modes." The alias arithmetic is sound — Δ = 20/19 = 1.05263, sampling frequency 2π/Δ = 5.96903, aliases 4.93879 / 6.99927, ω̂ = 1.0302 below the Nyquist 2.98451.
- The `value.clone()` refactor is behaviour-preserving: every LOO number except the intentionally changed pairwise SE is byte-identical to the pre-fix artifact.

REREVIEW-OC9: RESOLVED
- `loo_comparison` now sets `se_ddof = 0`; the recorded `se` is 0.25588686781820247, reproducing exactly from `np.sqrt(20*np.var(c-f))` on the stored pointwise vectors.
- All three SEs in the section's LOO table and paragraph are now one convention, and the section states "computed with `ddof=0` to match the ArviZ convention".
- The convention is recorded (`se_ddof`, `se_formula`, `se_convention` in `psis_loo.pairwise`), and the stale 0.263 is gone from section, README, and D63.

REREVIEW-OC10: RESOLVED
- `results.json` `data.x_eval` now records `{"n": 60, "range": [-11.0, 11.0]}`, matching `np.linspace(x.min()-1, x.max()+1, 60)` on x spanning [−10, 10].
- Section "evaluates 60 locations" is therefore checkable against the runs/ artifact, closing the §0 traceability gap.

NEW DEFECTS INTRODUCED BY THE CHANGED HUNKS

1. **[S4] [experiments/haaf_nested_constraint.py:826; runs/haaf_nested_constraint/results.json:360]** `alias_period = 2.0 * math.pi / abs(x_spacing)` is stored as `sampled_grid_alias_diagnostic.alias_period = 5.969026041820609`, but that quantity is the sampling *angular frequency* 2π/Δ (rad per x-unit), not a period; the period of the sampling grid is Δ = 1.0526. No number or prose claim is affected — the derived `alias_omega` values are correct, and neither the section nor the README uses the word "period" — so this is a field/variable naming defect only. **Fix:** rename to `sampling_angular_frequency` (or `alias_spacing_omega`) in both the script and the JSON key.

No other defect found in the changed hunks. Every number the fix newly introduced or altered was re-verified against the regenerated `results.json` (local Gaussian diagnostic, alias frequencies, init values, paired SE, x_eval, appendix diagnostic, all five expected-posterior `kl_forward` entries reconstructed from the differing-row gap) with no discrepancy; a style scan of all 178 added prose lines found no arrow glyphs, no "lives/sits", no "X is the Y" role-noun constructions, and no new em-dashes outside the mandated footnote format.
