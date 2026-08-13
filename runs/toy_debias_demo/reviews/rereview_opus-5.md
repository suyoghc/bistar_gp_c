# Re-review — Opus 5 (raiser channel, changed hunks)

Scope: rule 4, fix pass `8f1326d..a5b9cf8`, changed hunks only. Ten round-1
Opus findings entered the queue (F1, F3, F4, F7, F10, F11, F12, F13, F14, F15);
F2/F5/F6 were refuted by adversarial check and are not re-raised; F9 and the
§8.5 footnote are assembly-ledger items on the synthesis branch and are out of
scope here.

**Verdict: all ten RESOLVED. Seven new defects, one S3 and six S4, none
blocking; all are one- or two-sentence edits.**

Verification basis (repository, read-only, nothing written outside this file):
re-read `runs/prior_sensitivity/stage_a_toy_elicited.json`, `Notes/DECISIONS.md`
D12, `bistar_gp/decompose.py`, `bistar_gp/model.py`, `bistar_gp/e1_potential.py`,
`bistar_gp/fit.py`, `bistar_gp/candidates.py`, the Case A section and E7 artifact
on `paper/case-a-vanbork`; recomputed the MAP-vs-mode discrepancy and the FIX-2
moment identity from the committed JSON; executed
`assert_library_sampler_settings()` against the installed library plus three
negative controls; inspected the regenerated PNG; re-derived the `results.json`
field delta against `8f1326d`. The three artifact hashes and the 271,642-byte
figure size asserted in the D67 addendum all reproduce exactly.

---

## Per-finding

**F1 (S2, init provenance) — RESOLVED.** The misattribution is corrected in all
four artifacts (section 07 lines 35-42, `config.init_strategy`,
`runs/toy_debias_demo/README.md:38`, the D67 addendum) with the stage_a
artifact cited in footnote 2 under the disclosed local-material pattern, and the
repository backs every clause: `coherent_geometry` true, `valleys` `[]`,
`bimodal` false, one mode with `verified_local_max` true and `pooled_is_mass`
1.0, all 27 wide starts converging to log joint −18.913602, and D12's bimodality
scoped to `informative` with valley ≈ −43 and a ~3:1 mass split.

**F1 deviation report — CONFIRMED, and my round-1 number was the wrong one.** The
per-hyperparameter differences between `config.map_point` and `modes[0]` are
+1.690283e-08 (SE lengthscale), +5.600267e-09 (outputscale), −7.996414e-10
(linear variance), +1.187900e-09 (noise); max absolute 1.6902834687e-08. My
round-1 "~1e-9" was too tight by an order of magnitude, and "within 2e-8" as
committed is correct and conservative.

**F3 (S2, uncertainty floor) — RESOLVED.** The N-asymptotic sentence is gone;
§7.2 now reports only the measured N=20 quantities and states explicitly that
the demonstration does not test behaviour in N. The moment numbers are exact:
0.5·(0.06668550257966654 − 0.2368453522059466 − 0.17521904311580203) =
−0.17268944637104106 reproduces the stored cross-covariance bit-for-bit, the
stored correlation −0.8477010316953286 follows to the last digit, and all four
match the values I computed independently in round 1 from my own re-execution.
The identity is legitimate: component means add exactly, the law of total
variance is linear, and `component_covariance_note` says the two numbers are
read off the three variances rather than separately estimated.

**F4 (S3, "either component alone") — RESOLVED.** `recovery.bias_band_mean_width`
= 1.4584026383414934 is in the artifact, the README carries the row, and the
section quotes 1.458 alongside 1.032 and 1.836.

**F7 (S3, invisible width contrast) — RESOLVED.** `sharey=True` at
`experiments/toy_debias_demo.py:504`, plus mean-band-width annotations on panels
(a) and (c). In the regenerated PNG the contrast is now readable at a glance and
nothing is clipped by the shared limits — I checked the worst case, the linear
component's lower band vertex at x = −10 (≈ −3.43), and it renders well inside
the axes. The residual noted in round 1, that panel (c) replots panel (b)'s SE
arrays, was optional in my own fix text and remains by design.

**F10 (S3, unexercised "one object" claim) — RESOLVED.** §7.1 now opens with the
section 3.4 cross-link. The cited facts check out: `03-case-A-external-validation.md:146-149`
gives 0.183 / 0.192 / 0.441 / 0.184 for Linear, Sinusoidal, Sin+Linear,
Quadratic under `pw_kl_vcal` at τ=1, and `experiments/e7_convention_sensitivity.py`
uses `generate_toy_data()` at its defaults with `CONFIG = "toy_elicited"`, so
"same N=20 seed-42 instance, same data-elicited configuration" is exact. The
sentence that carries the link has three defects of its own (N1-N3).

**F11 (S3, empirical-Bayes conditioning) — RESOLVED.** Lines 27-30 record that
the lognormal medians are set from this sample's observable summaries and that
posterior statements are conditional on the fixed prior, matching the stage_a
`description` field (x-spacing 1.05, x-range 20, var(y) ≈ 3); the coverage
paragraph inherits the conditioning at lines 87-89, though its causal clause is
misstated (N4).

**F12 (S4, silent-wrong-answer path) — RESOLVED.** `apply_hp_value` now raises on
a False return (lines 367-377). I re-read `bistar_gp/model.py:88-116` to confirm
the fix cannot false-alarm: every success path returns literal `True`, and the
only falsy returns are the two unmatched-name branches. The jitter probe is a
faithful mirror of `compute_cholesky`'s base attempt — same
`K_sum + (noise_var + jitter)·I`, same `torch.linalg.cholesky`, same
`RuntimeError` catch (`LinAlgError` subclasses it) — so
`n_draws_needing_extra_jitter` = 0 of 1000 means what it says, and `n_ok` no
longer conflates clean with rescued solves.

**F13 (S4, hardcoded sampler mirrors) — RESOLVED, and the guard works.** I
executed `assert_library_sampler_settings()` against the installed package: it
passes. Three negative controls each raised with a correct message —
`TARGET_ACCEPT` 0.9, `SAMPLER_NAME` `nuts_bogus`, `STEP_SIZE_ADAPTED` False. The
guard reads the right surface: `fit_hmc_e1` passes `step_size=0.1`,
`adapt_step_size=True`, `target_accept_prob=0.8`, `sampler_name="nuts_e1"` as
literals to `_run_e1_nuts_route` (`bistar_gp/e1_potential.py:510-526`), whose
signature defaults agree (`:374-379`), and `bistar_gp.fit.fit_hmc` is what the
demo imports and calls. `sampler_name` has no signature default and the
`Parameter.empty` case is handled rather than mis-flagged.

**F14 (S4, acceptance rate) — RESOLVED.** Renamed to `move_fraction_by_chain`
with a `move_fraction_note` sibling and a README line stating the
non-comparability. A repository-wide grep finds no remaining consumer of
`acceptance_rate_by_chain` outside the D67 prose that describes the rename.

**F15 (S4, divergences) — RESOLVED.** Lines 42-45 carry the proposed
restructure verbatim in substance, and `results.json` supports both halves:
`divergences_total` 0, `depth_saturated_draws` 0, `depth_saturation_rate` 0.0.

---

## New findings

### N1 — S3 — `docs/paper-sie-jmp/07-debias-bridge.md:18-19`

**Defect.** "The demonstration below decomposes the posterior of that same
additive structure" makes the winning Case A candidate and the decomposed GP the
same object. They are different objects with different roles.
`bistar_gp/candidates.py:154-158` defines Sin+Linear as a parametric candidate
y = A·sin(ωx+φ) + b·x + c + ε fitted by MLE; section 7 decomposes the GP's
SE-plus-Linear *kernel* posterior. In BI* the GP posterior over ψ is the grader
and the candidate is the graded, so as written the sentence inverts the
framework's own roles in the one paragraph whose job is to substantiate
"evaluation and mitigation draw on one object." The true link is stronger than
the one claimed: both sections use the same ψ posterior, under the same prior,
on the same data, estimated by SIR in 3.4 and by NUTS here.

**Fix.** "Section 3.4 grades candidate models against the posterior this same GP
configuration induces on the same N=20 seed-42 instance, and puts most weight on
the Sin+Linear candidate, 0.441 under `pw_kl_vcal` at τ=1 with pooled
aggregation on the SIR path. The demonstration below decomposes that same GP
posterior, estimated here by NUTS rather than by SIR, into an SE and a linear
component; the winning candidate's sinusoid-plus-drift shape mirrors that
additive split without being the object decomposed."

### N2 — S4 — `docs/paper-sie-jmp/07-debias-bridge.md:15`

**Defect.** "this same N=20 seed-42 instance" is a forward reference: the
instance is not introduced until line 21. My round-1 fix offered two placements
and the head of §7.1 was chosen, which puts the demonstrative ahead of its
antecedent.

**Fix.** Move the cross-link paragraph to follow the data paragraph (after line
24), or write "the N=20 seed-42 instance described below".

### N3 — S4 — `docs/paper-sie-jmp/07-debias-bridge.md:16-17`

**Defect.** 0.441 is quoted with no aggregation convention named, and section 3.4
exists precisely to show that this number moves with the convention: the same
metric at the same τ gives 0.513 under expected-posterior aggregation
(`03-case-A-external-validation.md:154`). Quoting the pooled value bare invites
a cross-section inconsistency in the assembled manuscript. My round-1 fix text
carried the same omission, so this is my error propagated, not the
implementer's.

**Fix.** Insert the qualifier: "0.441 under `pw_kl_vcal` at τ=1 with pooled
aggregation on the SIR path".

### N4 — S4 — `docs/paper-sie-jmp/07-debias-bridge.md:87-89`

**Defect.** "the prior was elicited from the same sample the band is scored
against" misstates what is scored. The band is scored against sin(x) at the 201
grid points; the sample is what the posterior behind the band conditions on. As
written a reader can take the coverage number to be measured against the
observed data.

**Fix.** "…because the prior was elicited from the same sample the band
conditions on."

### N5 — S4 — `docs/paper-sie-jmp/07-debias-bridge.md:61-66` (Figure 7 caption)

**Defect.** FIX-4 changed the figure but not its caption. The caption still says
"The annotated slope and RMSE readouts are computed from the artifact values",
which now omits the coverage and the two new mean-band-width readouts, and it
never tells the reader that the panels share a y axis — the property that makes
the width comparison legitimate and that was the whole point of the fix.

**Fix.** "The three panels share a common y axis, so band widths are directly
comparable across them. The annotated slope, RMSE, coverage and band-width
readouts are computed from the artifact values."

### N6 — S4 — `docs/paper-sie-jmp/07-debias-bridge.md:109-111`

**Defect.** "a correlation near −0.85" reads as a correlation between the two
component functions, but the quantity is a ratio of grid-averaged total
variances, as the artifact key `component_correlation_from_mean_total_variances`
states and the prose does not. The pointwise correlation is not constant over
the grid and is undefined at x = 0, where the linear component has zero
variance. Round-1 F3 used the unqualified word first, so this is inherited
wording.

**Fix.** "…and a grid-averaged correlation near −0.85", matching the artifact key.

### N7 — S4 — `Notes/DECISIONS.md`, D67 review-fix addendum (results.json diff paragraph)

**Defect.** The addendum presents an exhaustive field-by-field account — "nine
added keys, the `acceptance_rate_by_chain` to `move_fraction_by_chain` rename
carrying the same 0.992/0.998 values, and the rewritten `config.init_strategy`
prose". The actual delta against `8f1326d` is eleven added fields, one removed,
one changed; nine of the additions are the recovery and decomposition keys, and
`sampler.move_fraction_note` is a tenth addition that the rename clause does not
cover. D67 entries are the source text for commit messages, so the count should
match the diff it claims to reproduce.

**Fix.** "…ten added keys (nine in `recovery` and `decomposition`, plus
`sampler.move_fraction_note`), the `acceptance_rate_by_chain` to
`move_fraction_by_chain` rename carrying the same 0.992/0.998 values, and the
rewritten `config.init_strategy` prose."
