# Re-review — Opus 5 (raiser of F2, O2-O8), repo access, changed hunks of c15a65f

REREVIEW-F2: RESOLVED
- `docs/paper-sie-jmp/04-case-B-occam-dial.md:87-91` now reports the Sinusoidal crossing as "τ ≈ 1.5" and prints all three per-seed interpolants (1.484, 1.584, 1.382) plus the spread [1.382, 1.584]; the old "τ=1.484355, bracketed by 1.412538 and 1.496236" is gone.
- The false resolution rule is deleted: `runs/occam_dial/README.md` E6 section now reads "Crossing resolution is set by the larger of grid spacing and Monte Carlo error" instead of "the bracket ... provides the resolution statement".
- The fix exceeds what I asked by adding seeds 1 and 2 (`experiments/e6_nesting_monotonicity.py:48 IS_SEEDS=(0,1,2)`; `e6_results.json provenance.is_seeds [0,1,2]`), giving direct scatter rather than ESS inference alone; the Linear pair is correctly kept at three decimals (spread [0.295184, 0.295974], SE 0.0121 vs bracket swing 0.3537).
- Residual on the derived summary interval is raised below as NEW-1, not as an unresolved F2.

REREVIEW-O2: RESOLVED
- `04-case-B-occam-dial.md:60-66`: "the inequality follows analytically from reachable-set containment in data space ... E6 thereby confirms that the implementation reproduces the analytic consequence, providing a machinery check rather than empirical support for the containment claim." The "This result supports the reachable-set claim" sentence is deleted.
- Both verdict branches were rewritten in `e6_nesting_monotonicity.py:598-614` of the diff: the failure branch now reads "a machinery regression, not a counterexample to the containment argument", which is the logically correct reading of a seeded, containment-guaranteed check.
- Minor surviving residual (hunk context, not re-litigated): line 46's "The reachable-set argument therefore requires" is now immediately corrected by the following sentence rather than rewritten.

REREVIEW-O3: RESOLVED
- `04-case-B-occam-dial.md:38-42` adds the cross-reference: τ=0.3 falls "1.6 percent above" the occam=True crossing at τ≈0.295, p2 gap 0.0867 nats, Bayes factor ≈1.09, "τ-marginal, while the p2-to-p3 magnitude change provides the robust content."
- Numbers verified against `figure_results.json`: −15.174751675 − (−15.261431576) = 0.0866799 nats, exp = 1.0906; (0.3 − 0.295184)/0.295184 = 1.63%.

REREVIEW-O4: RESOLVED
- `04-case-B-occam-dial.md:30-33` and README now use three decimals throughout and state "SE(log Z) of approximately 0.008, 0.017, and 0.038 nats for Linear, Sin+Linear, and Sinusoidal ... probability SE approximately 0.005".
- Those values use the exact ordinary-IS form sqrt(1/ESS − 1/n_is) — 0.00794/0.01701/0.03800 from ESS 11363/3180/681 at n_is=40000 — which is tighter and more correct than the 1/sqrt(ESS) I proposed; the probability SE recomputes to 0.0045.
- The tolerance is reframed in README and D62 as "a same-seed reproduction gate for three-decimal source anchors, not an accuracy claim."

REREVIEW-O5: RESOLVED
- Key renamed `model_posterior` to `model_prior` at `occam_dial_figure.py:104,121,168,246` and in all three arms of `figure_results.json`; `_fmt_posteriors` renamed `_fmt_priors`; stdout header now "n=50 induced model priors"; README heading "### Fresh n=50 induced model priors".
- grep for `model_posterior` / `_fmt_posteriors` / "n=50 posteriors" across the five changed files returns 0 hits.
- Both JSONs bump `schema_version` 1 to 2 and `write_combined_readme` now ignores non-2 artifacts, so a stale schema-1 file cannot repopulate the old labels.

REREVIEW-O6: RESOLVED
- New `_p1_laplace_diagnostics` (`occam_dial_figure.py:196-222`) calls the public `laplace_log_Z_Mx` with the same starts/τ/occam and asserts each direct log Z matches the arm value to atol 1e-12 — no `bistar_gp/` change, so the API constraint holds.
- `figure_results.json arms.p1_priors_lap_occam.laplace_diagnostics` records `n_clipped=0, converged=true` for all four models, answering the floor-dependence question I raised.
- README prints the diagnostics and adds a conditional warning line that fires only if some future run has `n_clipped > 0`.

REREVIEW-O7: RESOLVED
- `_crosscheck_local_table` now returns `"machine_dependent": true` on both the present and absent branches (`occam_dial_figure.py:144-148, 185`), and the flag is in the committed `figure_results.json`.
- The state-dependent README sentence "The optional D17 table cross-check was available." is deleted and replaced with prose that is identical on a clean checkout, pointing to the JSON for availability.

REREVIEW-O8: RESOLVED
- `e6_nesting_monotonicity.py:111-121` adds the both-zero `continue`, an isolated-zero dedup keyed on a new `exact_grid_index`, and an explicit `right == 0.0` branch; winner labels are now three-valued with "tie" in both `_crossings` and `_ordering_summary`.
- Traced [+1, 0, −1]: index 0 records one crossing at taus[1] with `exact_grid_index=1`; index 1 hits the dedup guard — the double-count reported is gone.
- No reported number changes (no exact zeros occur in this run), as expected for the S4 scope.

NEW DEFECTS INTRODUCED BY THE CHANGED HUNKS

NEW-1 [S3] [docs/paper-sie-jmp/04-case-B-occam-dial.md:90-91; runs/occam_dial/README.md:53; Notes/DECISIONS.md:5894; experiments/occam_dial_figure.py:349-351,377] "The enclosing shifted-root grid bracket gives an uncertainty interval of about τ 1.39 to 1.58" is neither enclosing nor consistent with the values printed one sentence earlier. It mixes two different quantities: the lower end is the interpolated lower shift root (1.392431) while the upper end is the grid-bracket upper *edge* of the upper shift root (`shifted_crossing_grid_brackets[1][1]` = 1.584893), then formats at `.2f` so it rounds down to 1.58. The genuinely enclosing shifted-root grid bracket is [1.333521, 1.584893] and the interpolated-root interval is [1.392, 1.563]; as printed, the stated interval excludes seed 2 (1.381999) and seed 1 (1.584500), i.e. two of the three per-seed crossings the same paragraph lists. Fix: derive one interval consistently — the enclosing shifted-root grid bracket [1.33, 1.59], or its union with the per-seed spread — and round outward rather than to nearest.

NEW-2 [S4] [experiments/occam_dial_figure.py:343-351] `_resolution_paragraph` dereferences `crossing_uncertainty["occam_true"]` and then `["tau_interval_log_interpolated"]` unconditionally, while the sibling `_crossing_uncertainty` deliberately returns `None` when a convention has no crossings (`e6_nesting_monotonicity.py:181,203`) and sets `tau_interval_log_interpolated: None` when the shifted curves yield no root (`e6:218-219`) — the null case already present as `crossing_uncertainty.occam_false: null` in the committed JSON. A future run whose occam=True sweep has no crossing would raise TypeError inside `write_combined_readme` after `e6_results.json` is written, and would also break `occam_dial_figure.py`, which calls the same writer. Fix: guard both lookups and emit a "no crossing on the grid" sentence, mirroring the empty-case fallback `_seed_crossing_text` already implements.
