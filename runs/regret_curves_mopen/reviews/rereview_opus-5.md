# Re-review — Opus 5 (raiser of DO1/DO4/DO5/DO8/DO9/DO11 in the fix queue), repo access, changed hunks of c57a70e

REREVIEW-DO1: RESOLVED
- `docs/paper-sie-jmp/06-case-D-mopen-calibration.md:64-66` now states the correct weighting axis ("Legacy `pw_nll` weights squared error by the candidate's fitted noise variance, whereas `pw_kl_vcal` weights it by the GP variance… `pw_mse` lies closer to the manuscript primary"), and the old "comes closest to the W1 primary role" and "median winning probabilities equal only 0.522" sentences are gone (grep returns nothing).
- The affine identity is now machine-gated in `experiments/regret_curves_mopen.py:_metric_scale_diagnostics` and stored at `results.json` `metric_scale_diagnostics.affine_identity`: 300 pairs, max abs error 1.7763568394002505e-15, divisor min/max 743.3198609618871 / 7161.481610527603 — matching the section's "1.78e-15" and "743 to 7,161".
- The replacement `raw_draw_wins` table (section:78-84) reproduces exactly from the stored `bistar_G_diagnostics`: practitioner 39.0% / 9 of 25 and 98.7% / 25 of 25; moderate 39.9% / 8 and 94.6% / 25; agnostic 41.5% / 9 and 92.1% / 25. All six recomputed independently.
- `practitioner pw_mse` all-subject median at tau=31.6 is 0.9865572479420387 in the artifact, matching the section's 0.987.

REREVIEW-DO4: RESOLVED
- The estimand is relabelled honestly: section:129-146 defines `R^draw` as `E_{f|y,eta_hat}[|f(t)-mu_theta(t)|]`, states that the JSONs cannot reconstruct the limits-note hyperparameter average, and adds `R^mean` as the posterior-mean plug-in at the same MAP point.
- The plug-in is genuinely computed, not asserted: `_conditioned_latent_posterior` now returns `posterior_mean_raw`, and `main` accumulates `np.abs(posterior_mean - candidate_means[...])`. Every plug-in number in the section table verifies against `results.json.mean_based_headline_regret` (17.638 / 17.325 / 34.052 / 63.3% / 74.0%; 33.901 / 10.764 / 92.890 / 40.0% / 75.0%).
- The Jensen statement holds in every reported aggregate: draw-based means exceed plug-in means in all four cells, and the gap is compressed in all reported cells (peak 33.782 vs 34.052; 91.452 vs 92.890; trials 1-5 means 11.960 vs 12.969 and 34.561 vs 37.051).
- "explains both sides of the aggregate result" is gone, replaced by "descriptively localize" plus the explicit limit "it cannot explain the portion of the stored aggregate comparison evaluated later in each subject's full series" (section:161-163).

REREVIEW-DO5: RESOLVED
- Section:17-22 now states both domains: stored G on "50 uniformly spaced points spanning each subject's full series" versus "integer trials 1 through 20", with the worst-case overlap "19/78, or 24.4%".
- Backed by a new artifact field, `results.json` `provenance.evaluation_domains` (`stored_practice_G_n_points` 50, `reconstructed_deviation_n_points` 20, `longest_subject_continuous_span_overlap_fraction` 0.24358974358974358 = 19/78), and the README renders the same figure at line 18.
- The linkage claim is correspondingly scoped ("applies only to their shared early-trial region"), and the 79-trial maximum is confirmed against the source JSONs.

REREVIEW-DO8: RESOLVED
- The "all configurations agree" row is removed from the Power/Exponential table (section:59-66) and restated as prose: "all three configurations select the same winner for 39 subjects under `pw_hellinger`, 49 under `pw_mse`, and 48 under `pw_nll`."
- Matches `results.json` `stored_selection_summary.robustness_across_configs` (39/49/48 agree). No header/semantics mismatch remains.

REREVIEW-DO9: RESOLVED
- `posterior_sd_min_raw` and `posterior_sd_max_raw` are deleted from the return dict of the renamed `_conditioned_latent_posterior`; grep for `posterior_sd` over `experiments/regret_curves_mopen.py` and `runs/regret_curves_mopen/results.json` returns nothing.
- Only `minimum_posterior_covariance_eigenvalue` is now collected and consumed, so the mislabelled-and-discarded eigenvalue roots are gone rather than merely renamed.

REREVIEW-DO11: RESOLVED
- Section table headers now read "Mean Power deviation (RT units)", "Mean Exponential deviation (RT units)", "Peak gap (RT units)" (section:148-153); the figure y-label reads "Absolute deviation (RT units)".
- The README carries the same units in its table header and adds "Both estimands use raw response-time units (RT units)."

F-D3 (causal scaffold language) — no conflict with anything raised
- Section:165-169 now states "The branch contains exactly one practitioner-MAP RBF reconstruction, and all three stored configurations use the RBF family. These artifacts cannot identify whether the localized `pw_nll` recovery asymmetry originates in F1 representability, F2 mimicry, metric behavior, or sampling noise."
- Both premises verify: `experiments/regret_curves_mopen.py:127-128` hardcodes the practitioner config with no alternative, and `experiments/practice_EvansEtAL/kernels.py:69-80` returns `[ScaleKernel(RBFKernel)]` for every config. "scaffold-induced" is gone from the branch.
- Consistent with the DO4/DO5 scoping and the CHECK-DC4 evidence; it neither weakens nor contradicts any finding raised.

NEW DEFECT introduced by a changed hunk

1. **[S3] [docs/paper-sie-jmp/06-case-D-mopen-calibration.md:82-84]** — the F-D1 hunk writes "the power-cohort `pw_nll` medians peak around 0.57 (approximately 0.573 in the review summary) at $\tau=0.1$". Three problems, all inside the new hunk. The artifact's power-cohort `pw_nll` medians at tau=0.1 are 0.581037 (practitioner), 0.569066 (moderate), 0.556954 (agnostic) — 0.573 is not among them and appears nowhere in `runs/regret_curves_mopen/results.json`. It cites "the review summary", an internal review document rather than a `runs/` artifact, which breaches the §0 rule that every reported number be regenerable from a named `experiments/` script into a `runs/` artifact, and it puts a reference to the review process into manuscript prose. The value is also mislabelled: 0.573 originated as a single-subject illustrative calculation, not a cohort median. The README got this right on the same fix pass — `_write_readme` interpolates the three artifact values and summarises them as "(about 0.57)". **Fix:** delete the parenthetical, or mirror the README and give the three artifact medians (0.581, 0.569, 0.557) with the "about 0.57" summary.
