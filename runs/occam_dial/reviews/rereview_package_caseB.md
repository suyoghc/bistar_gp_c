RE-REVIEW ROUND (HANDOFF §4 rule 4) — Case B fix pass 1, changed hunks only.
Branch paper/case-b-occam-dial; fix commit c15a65f on top of reviewed tip 9d6d95c.
Your task: for EACH of YOUR OWN previously raised findings (listed per reviewer in the
dispatch note), judge from the changed hunks whether the fix resolves it.
Output per finding: 'REREVIEW-<ID>: RESOLVED' or 'REREVIEW-<ID>: NOT-RESOLVED' plus 2-4
evidence lines. Additionally report any NEW defect INTRODUCED BY the changed hunks
(scope: the hunks only; no re-litigation of unchanged code; no scope expansion).
Finding IDs and the full round-1 record: runs/occam_dial/reviews/VERDICTS.md (also
summarized in the implementer's fix report below).

=== IMPLEMENTER FIX REPORT ===
Implemented all ten fixes exactly within the allowed scope.

Key files: [figure script](/Users/sc8918/Documents/GitHub/bistar_gp_c/experiments/occam_dial_figure.py), [E6 script](/Users/sc8918/Documents/GitHub/bistar_gp_c/experiments/e6_nesting_monotonicity.py), [README](/Users/sc8918/Documents/GitHub/bistar_gp_c/runs/occam_dial/README.md), [figure JSON](/Users/sc8918/Documents/GitHub/bistar_gp_c/runs/occam_dial/figure_results.json), [E6 JSON](/Users/sc8918/Documents/GitHub/bistar_gp_c/runs/occam_dial/e6_results.json), [paper section](/Users/sc8918/Documents/GitHub/bistar_gp_c/docs/paper-sie-jmp/04-case-B-occam-dial.md), [local KB resolution](/Users/sc8918/Documents/GitHub/bistar_gp_c/kb/Wiki/REVIEW_AND_VET.md), and [D62](/Users/sc8918/Documents/GitHub/bistar_gp_c/Notes/DECISIONS.md:5826).

1. **FIX-F2** — E6 script, E6 JSON, README, paper section, KB, D62. Added n_is=100,000 sweeps for seeds 0/1/2, one IS call per model per seed, and grid/seed/ESS uncertainty reporting.

   - `occam=False`: no crossing for either pair on any seed.
   - Linear: seed 0 `0.295 [0.282, 0.299]`; seed 1 `0.295 [0.282, 0.299]`; seed 2 `0.296 [0.282, 0.299]`. Per-seed spread `[0.295, 0.296]`; seed-0 one-SE interval `[0.295, 0.296]`. The 0.354-nat bracket swing exceeds the approximately 0.012-nat SE.
   - Sinusoidal: seed 0 `1.484 [1.413, 1.496]`; seed 1 `1.584 [1.496, 1.585]`; seed 2 `1.382 [1.334, 1.413]`. Reported as `τ ≈ 1.5`; spread `[1.382, 1.584]`; seed-0 shift roots `[1.392, 1.563]`; grid-aware uncertainty about `τ 1.39 to 1.58`.

2. **FIX-O2** — E6 script, E6 JSON, README, paper section, KB, D62. Reframed the min-Ḡ inequality as an analytic consequence of exact box containment and the mean-only divergence. E6 now describes a machinery check and quantifies margins of 2.379 and 2.501 nats.

3. **FIX-F1** — figure script, README, local KB, D62. Mirrored the complete corrected resolution into the committed README, with the clean-checkout explanation. The README and KB resolution paragraphs are byte-identical.

4. **FIX-O3** — paper section. Added the τ=0.3 versus τ≈0.295 cross-reference, 1.6-percent offset, 0.0867-nat p2 gap, Bayes factor about 1.09, and the τ-marginal versus robust-content interpretation.

5. **FIX-O4** — figure script, README, paper section, D62. Prose probabilities now use three decimals; added the requested ESS-implied log-Z and approximately 0.005 probability SE; reframed 0.003 strictly as a same-seed reproduction gate.

6. **FIX-O5** — figure script, figure JSON, README, paper section. Renamed `model_posterior` to `model_prior`; README now uses “Fresh n=50 induced model priors.” No stale induced-prior posterior labels remain.

7. **FIX-O6** — figure script, figure JSON, README. Added direct public `laplace_log_Z_Mx` calls and equality assertions. Recorded p1 diagnostics:

   - Linear: `n_clipped=0`, `converged=true`
   - Sinusoidal: `n_clipped=0`, `converged=true`
   - Sin+Linear: `n_clipped=0`, `converged=true`
   - Quadratic: `n_clipped=0`, `converged=true`

8. **FIX-O7** — figure script, figure JSON, README. Cross-check prose is state-invariant; JSON records `"machine_dependent": true` alongside local availability.

9. **FIX-O8** — E6 script. Added exact-zero crossing guards, tie-aware winner labels, and isolated-zero deduplication. Synthetic edge-case checks passed.

10. **FIX-C3** — D62 only. Corrected the description of local `runs/viz_unification/` contents and the authoritative recomputation plus 0.003 same-seed cross-check behavior.

Reruns:

- `occam_dial_figure.py`: exit 0, **14.89 seconds**; anchors and local cross-check passed.
- `e6_nesting_monotonicity.py`: exit 0, **31.80 seconds**; all three seeds completed.
- Regenerated [PNG](/Users/sc8918/Documents/GitHub/bistar_gp_c/runs/occam_dial/occam_dial.png) is 152 KB and passed visual inspection.
- Ruff and final schema/terminology/artifact checks passed.

Deviations: none. No git commands were executed.
=== FIX DIFF STAT (full) ===
 Notes/DECISIONS.md                         |    81 +-
 docs/paper-sie-jmp/04-case-B-occam-dial.md |    72 +-
 experiments/e6_nesting_monotonicity.py     |   299 +-
 experiments/occam_dial_figure.py           |   218 +-
 runs/occam_dial/README.md                  |    44 +-
 runs/occam_dial/e6_results.json            | 11035 ++++++++++++++++++++-------
 runs/occam_dial/figure_results.json        |    27 +-
 7 files changed, 8868 insertions(+), 2908 deletions(-)

=== FIX DIFF (e6_results.json excluded; its regenerated summary follows) ===
diff --git a/Notes/DECISIONS.md b/Notes/DECISIONS.md
index 21a737a..12e8c14 100644
--- a/Notes/DECISIONS.md
+++ b/Notes/DECISIONS.md
@@ -5722,10 +5722,13 @@ computation, holdout access, BMS*, Ready, or merge.
 **Problem:** Case B needed a regenerable E4 figure that separated the D17
 estimator and `occam` changes, plus an E6 numerical check of the claim that an
 encompassing model cannot have a worse best achievable divergence than either
-of its exact restrictions. The local `runs/viz_unification/` directory contains
-figures and logs only and cannot serve as an input. The canonical visualization
-box also starts the sinusoid amplitude at 0.01, while exact Linear nesting
-requires A=0.
+of its exact restrictions. The local untracked `runs/viz_unification/` directory
+contains figures, logs, `delta_table.md`, `ess_by_stage.md` diagnostics, and
+extracted legacy scripts, so it cannot serve as the authoritative committed data
+source and the figure arms must be recomputed. When `delta_table.md` is present,
+the figure script parses it and enforces a 0.003 same-seed cross-check gate. The
+canonical visualization box also starts the sinusoid amplitude at 0.01, while
+exact Linear nesting requires A=0.
 
 **Decision:** Added `experiments/occam_dial_figure.py` and
 `experiments/e6_nesting_monotonicity.py`, both writing to
@@ -5734,43 +5737,59 @@ MAP-based averaged GP through `bistar_viz/scripts/_viz_spaces.py` at n=50,
 with data seed 42, 80 evaluation points, and primary metric `pw_kl_vcal`.
 The figure runs the p1 pure-Laplace `occam=True`, p2 IS `occam=True`, and p3 IS
 `occam=False` arms at τ=0.3, IS seed 0, `n_is=40000`, and five seeded
-perturbations per start. Its absolute anchor tolerance equals 0.003, allowing
-three-decimal source rounding and small cross-platform optimizer variation
-while remaining below the p2 decision gap. E6 calls
+perturbations per start. Its 0.003 absolute-probability anchor tolerance provides
+a same-seed reproduction gate for three-decimal source anchors, not an accuracy
+claim. The p1 arm calls `laplace_log_Z_Mx` directly to retain each model's
+`n_clipped` and `converged` diagnostics and asserts that those direct log Z_M
+values match the arm values. E6 calls
 `_multistart_G_optima`, `compute_G_at_params`, and `is_log_Z_Mx` from
 `bistar_gp/laplace_evidence.py`; it does not reimplement Ḡ. E6 extends
 only the encompassing amplitude boundary to A=0, seeds its optimizer with
-the exact restricted optima, and uses `n_is=100000` over 161 log-spaced
-temperatures from 0.031623 through 316.227766. One IS call per model supplies
+the exact restricted optima, and uses seeds 0, 1, and 2 with `n_is=100000` per
+seed over 161 log-spaced temperatures. One IS call per model per seed supplies
 the raw sweep, and the package reference-volume helper supplies the
-`occam=True` sweep. The min-Ḡ tolerance equals 10^-8, with a 10^-10
-exact-embedding check.
+`occam=True` sweep. Given the exact embeddings and mean-only divergence, each
+min-Ḡ inequality follows analytically from box containment; the retained check
+confirms the implementation reproduces that consequence and quantifies the
+margins. The min-Ḡ tolerance equals 10^-8, with a 10^-10 exact-embedding check.
 
 **Alternatives considered:** Reading `delta_table.md` or the local logs as the
 figure data source was rejected because those artifacts remain local and
-untracked; the table now provides an optional cross-check only. Comparing p1
-directly with p3 as a pure `occam` ablation was rejected because the arms also
+untracked; the table provides only the machine-dependent 0.003 same-seed
+cross-check when present. Comparing p1 directly with p3 as a pure `occam`
+ablation was rejected because the arms also
 change the Z_M estimator; p2 isolates the estimator step. Retaining the
 0.01 amplitude cutoff for E6 was rejected because it excludes the stated
 A=0 restriction. Reimplementing the divergence or optimizer was rejected
 in favor of the package machinery required by the work order.
 
-**Result:** `runs/occam_dial/figure_results.json` reproduces the n=50 arms:
-p1 Linear 0.534121, Sinusoidal 0.075747, Sin+Linear 0.382052, Quadratic
-0.008080; p2 Linear 0.506877, Sinusoidal 0.020499, Sin+Linear 0.464791,
-Quadratic 0.007834; p3 Linear 0.007040, Sinusoidal 0.001093, Sin+Linear
-0.991758, Quadratic 0.000109. The p1-to-p2 estimator change narrows the Linear
-versus Sin+Linear gap, and the p2-to-p3 convention change decides the verdict.
-D17's legacy 0.934 and 0.693 values remain explicitly labeled as recorded
-legacy findings and are not recomputed by the new scripts.
-
-E6 found min-Ḡ 0.045516783 for Sin+Linear, 2.424774370 for Linear, and
-2.546229649 for Sinusoidal, giving restricted-minus-encompassing margins
-2.379257587 and 2.500712865. Both nesting inequalities hold. Under
-`occam=False`, neither pair crosses on the tested τ grid. Under
-`occam=True`, Linear overtakes Sin+Linear at τ=0.295184 within the bracket
-[0.281838, 0.298538], and Sinusoidal overtakes at τ=1.484355 within
-[1.412538, 1.496236]. Minimum ESS values equal 14903 for Linear, 1373 for
-Sinusoidal, and 831 for Sin+Linear. The figure remains below the 2 MB
-limit. Exact rerun commands: `python experiments/occam_dial_figure.py` and
+**Result:** `runs/occam_dial/figure_results.json` reproduces the n=50 induced
+model priors: p1 Linear 0.534, Sinusoidal 0.076, Sin+Linear 0.382, Quadratic
+0.008; p2 Linear 0.507, Sinusoidal 0.020, Sin+Linear 0.465, Quadratic 0.008;
+p3 Linear 0.007, Sinusoidal 0.001, Sin+Linear 0.992, Quadratic 0.000. At p2,
+ESS implies SE(log Z) of approximately 0.008, 0.017, and 0.038 nats for Linear,
+Sin+Linear, and Sinusoidal, respectively, with probability SE approximately
+0.005. Every p1 model has `n_clipped=0` and `converged=True`. The p1-to-p2
+estimator change narrows the Linear versus Sin+Linear gap, and the p2-to-p3
+convention change provides the robust magnitude change. D17's legacy 0.934 and
+0.693 values remain explicitly labeled as recorded legacy findings and are not
+recomputed by the new scripts.
+
+E6 confirms the analytic box-containment consequence and quantifies
+restricted-minus-encompassing margins of 2.379 nats for Linear and 2.501 nats
+for Sinusoidal. Under `occam=False`, neither pair crosses for seeds 0, 1, or 2.
+Under `occam=True`, the Linear crossing occurs at τ=0.295, 0.295, and 0.296;
+the seed-0 bracket is [0.282, 0.299], the per-seed spread is [0.295, 0.296],
+and the ESS-implied one-SE shift interval is [0.295, 0.296]. Its bracket delta
+swing of 0.354 nats exceeds the approximately 0.012-nat SE, supporting the
+three-decimal crossing. The Sinusoidal crossing occurs at 1.484, 1.584, and
+1.382 and supports only τ ≈ 1.5; the seed-0 bracket is [1.413, 1.496], the
+per-seed spread is [1.382, 1.584], and the ESS shift roots are [1.392, 1.563].
+The enclosing shifted-root grid bracket gives an uncertainty interval of about
+τ 1.39 to 1.58. Crossing resolution is set by the larger of grid spacing and
+Monte Carlo error. The empirical content comprises these margins and finite-τ
+crossings. The REVIEW_AND_VET resolution text is mirrored into the committed
+`runs/occam_dial/README.md` because `kb/` is gitignored. The figure remains
+below the 2 MB limit. Exact rerun commands:
+`python experiments/occam_dial_figure.py` and
 `python experiments/e6_nesting_monotonicity.py`.
diff --git a/docs/paper-sie-jmp/04-case-B-occam-dial.md b/docs/paper-sie-jmp/04-case-B-occam-dial.md
index fd4811e..b5ebe6e 100644
--- a/docs/paper-sie-jmp/04-case-B-occam-dial.md
+++ b/docs/paper-sie-jmp/04-case-B-occam-dial.md
@@ -27,12 +27,20 @@ posterior inference about which model generated the data.[^3]
 panels differ in both the Z_M estimator and the `occam` convention, so the p2
 panel prevents a conflated attribution. Replacing pure Laplace with IS while
 retaining `occam=True` changes the Linear and Sin+Linear probabilities from
-0.534121 and 0.382052 in p1 to 0.506877 and 0.464791 in p2. Changing only the
-convention in the next step gives 0.007040 and 0.991758 in p3. The estimator
+0.534 and 0.382 in p1 to 0.507 and 0.465 in p2. Changing only the convention
+in the next step gives 0.007 and 0.992 in p3. At p2, ESS implies SE(log Z) of
+approximately 0.008, 0.017, and 0.038 nats for Linear, Sin+Linear, and
+Sinusoidal, respectively, with probability SE approximately 0.005. The estimator
 change narrows the gap; removing the V_ref normalization decides the verdict.
 The dial figure argues about the `occam` convention's effect, not about which
 model generated the data.
 
+The figure's τ=0.3 evaluation point falls 1.6 percent above the `occam=True`
+Linear/Sin+Linear crossing at τ≈0.295. The p2 log Z_M gap of 0.0867 nats gives
+a Bayes factor of about 1.09, so the `occam=True` panels report an essentially
+tied comparison. The p1/p2 "Linear preferred" reading therefore remains
+τ-marginal, while the p2-to-p3 magnitude change provides the robust content.
+
 The earlier contradiction supplies useful historical context but not new
 evidence. D17 records 0.934 for Sin+Linear in the legacy trajectory script and
 0.693 for Linear in the legacy priors script, which hard-coded
@@ -50,30 +58,42 @@ min_φ Ḡ(φ). The reachable-set argument therefore requires
 \]
 
 Different parameter dimensions prevent a Lebesgue-monotonicity argument in
-parameter space. E6 instead tests the two exact restrictions in data space.
-The visualization box uses A ≥ 0.01 as a numerical cutoff, so E6 alone extends
-the encompassing amplitude bound to A ≥ 0. All other bounds match the
-visualization arms. The restricted optimum seeds the encompassing multi-start
-optimization, and the package divergence calculation reproduces the restricted
-value exactly at its embedding, within the declared 10^-10 tolerance.[^4]
-
-For this n=50, `informative`-configuration, MAP-based averaged GP, E6
-obtains min_φ Ḡ=0.045516783 for Sin+Linear, 2.424774370 for Linear, and
-2.546229649 for Sinusoidal. The encompassing model improves on the restrictions
-by 2.379257587 and 2.500712865, respectively. Both numerical inequalities
-therefore hold by margins far above the 10^-8 comparison tolerance. This result
-supports the reachable-set claim for the tested GP and parameterization; it
-does not prove the claim for every data prior or parameterization.[^4]
-
-Finite τ separates the two reference measures. One IS call per model evaluates
-161 temperatures from 0.031623 through 316.227766. With `occam=False`,
-Sin+Linear retains the larger pairwise Z_M throughout that grid, so neither
-nested pair crosses. With `occam=True`, Linear overtakes Sin+Linear at the
-log-interpolated location τ=0.295184, bracketed by 0.281838 and 0.298538.
-Sinusoidal overtakes at τ=1.484355, bracketed by 1.412538 and 1.496236. Thus
-low temperature supports Popper's encompassing constraint in both conventions
-for this example, while V_ref normalization permits the finite-temperature
-simplicity preference associated with Wrinch and Jeffreys.[^4]
+parameter space. Given the two exact embeddings and the mean-only divergence,
+however, the inequality follows analytically from reachable-set containment in
+data space. The visualization box uses A ≥ 0.01 as a numerical cutoff, so E6
+alone extends the encompassing amplitude bound to A ≥ 0. All other bounds
+match the visualization arms. The restricted optima seed the encompassing
+multi-start optimization, and the package divergence calculation reproduces
+each restricted value at its embedding within the declared 10^-10 tolerance.
+E6 thereby confirms that the implementation reproduces the analytic
+consequence, providing a machinery check rather than empirical support for the
+containment claim.[^4]
+
+For this n=50, `informative`-configuration, MAP-based averaged GP, the machinery
+check obtains min_φ Ḡ=0.046 for Sin+Linear, 2.425 for Linear, and 2.546 for
+Sinusoidal. It quantifies restricted-minus-encompassing margins of 2.379 and
+2.501 nats, respectively, far above the 10^-8 comparison tolerance. The
+empirical content of E6 consists of these margins and the finite-τ Z_M
+crossings.[^4]
+
+Finite τ separates the two reference measures. One IS call per model per seed
+evaluates 161 temperatures for seeds 0, 1, and 2. With `occam=False`,
+Sin+Linear retains the larger pairwise Z_M throughout the grid for all three
+seeds, so neither nested pair crosses. With `occam=True`, the Linear crossing
+occurs at τ=0.295, 0.295, and 0.296 across seeds 0, 1, and 2. Seed 0 has grid
+bracket [0.282, 0.299], the per-seed spread is [0.295, 0.296], and its
+ESS-implied one-SE shift interval is [0.295, 0.296]. The seed-0 bracket delta
+swing of 0.354 nats exceeds the ESS-implied SE of approximately 0.012 nats, so
+the three-decimal Linear crossing is sign-supported. The Sinusoidal crossing
+occurs at 1.484, 1.584, and 1.382 across those seeds; it should be summarized
+only as τ ≈ 1.5. Its seed-0 bracket is [1.413, 1.496], the per-seed spread is
+[1.382, 1.584], and the seed-0 ESS shift roots are [1.392, 1.563]. The enclosing
+shifted-root grid bracket gives an uncertainty interval of about τ 1.39 to 1.58.
+Crossing resolution is set by the larger of grid spacing and Monte Carlo error.
+Thus low temperature supports Popper's encompassing constraint in both
+conventions for this example, while V_ref normalization permits the
+finite-temperature simplicity preference associated with Wrinch and
+Jeffreys.[^4]
 
 The two controls should therefore remain explicit. Temperature governs how
 strongly best achievable divergence dominates integrated compatibility, while
diff --git a/experiments/e6_nesting_monotonicity.py b/experiments/e6_nesting_monotonicity.py
index b9cc490..cca2f08 100644
--- a/experiments/e6_nesting_monotonicity.py
+++ b/experiments/e6_nesting_monotonicity.py
@@ -2,9 +2,10 @@
 """Run the Case B E6 nesting and finite-τ ordering check.
 
 The script uses the existing multi-start Ḡ optimizer and defensive-mixture IS
-implementation. It tests exact Linear and Sinusoidal restrictions inside an
-encompassing Sin+Linear parameter space, then computes both reference-measure
-conventions over one shared τ grid.
+implementation. Exact embeddings and a mean-only divergence make the min-Ḡ
+inequality an analytic consequence of box containment; E6 checks that the
+implementation reproduces it, quantifies the margins, and computes both
+reference-measure conventions over one shared τ grid.
 """
 
 from __future__ import annotations
@@ -37,7 +38,6 @@ from bistar_gp.laplace_evidence import (  # noqa: E402
 from occam_dial_figure import (  # noqa: E402
     DATA_SEED,
     DEFAULT_OUT_DIR,
-    IS_SEED,
     MODEL_NAMES,
     N_DRAWS,
     N_PERTURB,
@@ -47,6 +47,7 @@ from occam_dial_figure import (  # noqa: E402
 
 
 N_IS = 100_000
+IS_SEEDS = (0, 1, 2)
 TAUS = np.logspace(-1.5, 2.5, 161)
 MIN_G_TOLERANCE = 1e-8
 EMBEDDING_TOLERANCE = 1e-10
@@ -107,8 +108,21 @@ def _crossings(taus: np.ndarray, delta: np.ndarray) -> list[dict[str, Any]]:
     found = []
     for index in range(len(taus) - 1):
         left, right = float(delta[index]), float(delta[index + 1])
+        if left == 0.0 and right == 0.0:
+            continue
+        if (
+            left == 0.0
+            and found
+            and found[-1].get("exact_grid_index") == index
+        ):
+            continue
+        exact_grid_index = None
         if left == 0.0:
             estimate = float(taus[index])
+            exact_grid_index = index
+        elif right == 0.0:
+            estimate = float(taus[index + 1])
+            exact_grid_index = index + 1
         elif left * right > 0.0:
             continue
         else:
@@ -116,16 +130,21 @@ def _crossings(taus: np.ndarray, delta: np.ndarray) -> list[dict[str, Any]]:
             estimate = float(
                 10.0 ** (log_left - left * (log_right - log_left) / (right - left))
             )
-        found.append(
-            {
-                "lower_grid_index": index,
-                "tau_bracket": [float(taus[index]), float(taus[index + 1])],
-                "delta_log_Z_bracket": [left, right],
-                "tau_log_interpolated": estimate,
-                "winner_below": "encompassing" if left > 0.0 else "restricted",
-                "winner_above": "encompassing" if right > 0.0 else "restricted",
-            }
-        )
+        crossing = {
+            "lower_grid_index": index,
+            "tau_bracket": [float(taus[index]), float(taus[index + 1])],
+            "delta_log_Z_bracket": [left, right],
+            "tau_log_interpolated": estimate,
+            "winner_below": (
+                "encompassing" if left > 0.0 else "restricted" if left < 0.0 else "tie"
+            ),
+            "winner_above": (
+                "encompassing" if right > 0.0 else "restricted" if right < 0.0 else "tie"
+            ),
+        }
+        if exact_grid_index is not None:
+            crossing["exact_grid_index"] = exact_grid_index
+        found.append(crossing)
     return found
 
 
@@ -140,8 +159,12 @@ def _ordering_summary(
         "delta_definition": "log Z_M(encompassing) - log Z_M(restricted)",
         "delta_log_Z": delta,
         "crossings": crossings,
-        "winner_at_tau_min": "encompassing" if delta[0] > 0.0 else "restricted",
-        "winner_at_tau_max": "encompassing" if delta[-1] > 0.0 else "restricted",
+        "winner_at_tau_min": (
+            "encompassing" if delta[0] > 0.0 else "restricted" if delta[0] < 0.0 else "tie"
+        ),
+        "winner_at_tau_max": (
+            "encompassing" if delta[-1] > 0.0 else "restricted" if delta[-1] < 0.0 else "tie"
+        ),
         "delta_at_tau_min": float(delta[0]),
         "delta_at_tau_max": float(delta[-1]),
         "minimum_absolute_delta_grid_point": {
@@ -151,6 +174,91 @@ def _ordering_summary(
     }
 
 
+def _nearest_crossing(
+    crossings: list[dict[str, Any]], target: float
+) -> dict[str, Any] | None:
+    if not crossings:
+        return None
+    return min(crossings, key=lambda item: abs(item["tau_log_interpolated"] - target))
+
+
+def _crossing_uncertainty(
+    orderings_by_seed: dict[str, dict[str, Any]],
+    sweeps_by_seed: dict[str, dict[str, Any]],
+    restricted_name: str,
+    convention: str,
+) -> dict[str, Any] | None:
+    """Combine grid, seed, and ESS information for a single crossing."""
+    per_seed = {
+        seed: ordering[convention]["crossings"]
+        for seed, ordering in orderings_by_seed.items()
+    }
+    estimates = [
+        crossing["tau_log_interpolated"]
+        for crossings in per_seed.values()
+        for crossing in crossings
+    ]
+    seed_zero_crossings = per_seed.get("0", [])
+    if not estimates or not seed_zero_crossings:
+        return None
+
+    seed_zero = seed_zero_crossings[0]
+    nominal = float(seed_zero["tau_log_interpolated"])
+    seed_zero_ordering = orderings_by_seed["0"][convention]
+    delta = np.asarray(seed_zero_ordering["delta_log_Z"], dtype=float)
+    restricted_ess = np.asarray(
+        sweeps_by_seed["0"][restricted_name][convention]["ess"], dtype=float
+    )
+    encompassing_ess = np.asarray(
+        sweeps_by_seed["0"]["Sin+Linear"][convention]["ess"], dtype=float
+    )
+    delta_se = np.sqrt(1.0 / restricted_ess + 1.0 / encompassing_ess)
+    lower = _nearest_crossing(_crossings(TAUS, delta - delta_se), nominal)
+    upper = _nearest_crossing(_crossings(TAUS, delta + delta_se), nominal)
+    if lower is None or upper is None:
+        one_se_interval = None
+        shifted_brackets = None
+    else:
+        shifted = sorted(
+            [lower, upper], key=lambda item: item["tau_log_interpolated"]
+        )
+        one_se_interval = [
+            float(shifted[0]["tau_log_interpolated"]),
+            float(shifted[1]["tau_log_interpolated"]),
+        ]
+        shifted_brackets = [
+            shifted[0]["tau_bracket"],
+            shifted[1]["tau_bracket"],
+        ]
+
+    bracket_index = int(seed_zero["lower_grid_index"])
+    bracket_delta = np.asarray(seed_zero["delta_log_Z_bracket"], dtype=float)
+    return {
+        "grid_bracket_seed_0": seed_zero["tau_bracket"],
+        "per_seed_crossings": per_seed,
+        "per_seed_interpolant_spread": [float(min(estimates)), float(max(estimates))],
+        "ess_implied_one_se_common_mode_shift_seed_0": {
+            "method": (
+                "shift the seed-0 delta-log-Z curve by plus or minus "
+                "sqrt(1/ESS_encompassing + 1/ESS_restricted) at each grid point"
+            ),
+            "tau_interval_log_interpolated": one_se_interval,
+            "shifted_crossing_grid_brackets": shifted_brackets,
+            "delta_log_Z_se_at_nominal_bracket": [
+                float(delta_se[bracket_index]),
+                float(delta_se[bracket_index + 1]),
+            ],
+            "delta_log_Z_swing_across_nominal_bracket": float(
+                abs(bracket_delta[1] - bracket_delta[0])
+            ),
+        },
+        "resolution_rule": (
+            "crossing resolution is set by the larger of grid spacing and "
+            "Monte Carlo error"
+        ),
+    }
+
+
 def run(out_dir: Path, *, n_is: int) -> dict[str, Any]:
     out_dir.mkdir(parents=True, exist_ok=True)
     x_eval, _x_50, _y_50, avg_gp, retained = build_map_gp()
@@ -232,48 +340,52 @@ def run(out_dir: Path, *, n_is: int) -> dict[str, Any]:
         # instead uses interior starts plus the best encompassing optimum.
         "Sin+Linear": starts["Sin+Linear"] + [encompassing_phi],
     }
-    sweeps: dict[str, dict[str, Any]] = {}
-    for name, param_space in spaces.items():
-        # One package IS call computes the full τ sweep. The package's
-        # reference-volume helper then applies the documented occam variant.
-        # NumPy 2 on Accelerate can emit spurious matmul floating warnings for
-        # the large proposal draw even when every returned diagnostic remains
-        # finite, so the scoped errstate accompanies explicit finiteness checks.
-        with np.errstate(divide="ignore", over="ignore", invalid="ignore"):
-            result = is_log_Z_Mx(
-                param_space,
-                x_eval,
-                avg_gp,
-                TAUS,
-                n_is=n_is,
-                seed=IS_SEED,
-                starts=starts_by_model[name],
-                metric_name="pw_kl_vcal",
-                occam=False,
-            )
-        if not np.all(np.isfinite(result.log_Z)) or not np.all(
-            np.isfinite(result.ess)
-        ):
-            raise AssertionError(f"non-finite IS result for {name}")
-        log_volume = float(_log_reference_volume(param_space))
-        normalized_log_z = result.log_Z - log_volume
-        sweeps[name] = {
-            "occam_false": {
-                "log_Z_M": result.log_Z,
-                "ess": result.ess,
-                "min_ess": float(np.min(result.ess)),
-            },
-            "occam_true": {
-                "log_Z_M": normalized_log_z,
-                "ess": result.ess,
-                "min_ess": float(np.min(result.ess)),
-                "derived_from_raw_with": (
-                    "bistar_gp.laplace_evidence._log_reference_volume"
-                ),
-            },
-            "log_reference_volume": log_volume,
-            "is_calls": 1,
-        }
+    sweeps_by_seed: dict[str, dict[str, Any]] = {}
+    for seed in IS_SEEDS:
+        sweeps: dict[str, dict[str, Any]] = {}
+        for name, param_space in spaces.items():
+            # One package IS call per model and seed computes the full τ sweep.
+            # The reference-volume helper then applies the occam variant.
+            # NumPy 2 on Accelerate can emit spurious matmul floating warnings
+            # for the large proposal draw even when every returned diagnostic
+            # remains finite, so the scoped errstate accompanies explicit
+            # finiteness checks.
+            with np.errstate(divide="ignore", over="ignore", invalid="ignore"):
+                result = is_log_Z_Mx(
+                    param_space,
+                    x_eval,
+                    avg_gp,
+                    TAUS,
+                    n_is=n_is,
+                    seed=seed,
+                    starts=starts_by_model[name],
+                    metric_name="pw_kl_vcal",
+                    occam=False,
+                )
+            if not np.all(np.isfinite(result.log_Z)) or not np.all(
+                np.isfinite(result.ess)
+            ):
+                raise AssertionError(f"non-finite IS result for {name}, seed {seed}")
+            log_volume = float(_log_reference_volume(param_space))
+            normalized_log_z = result.log_Z - log_volume
+            sweeps[name] = {
+                "occam_false": {
+                    "log_Z_M": result.log_Z,
+                    "ess": result.ess,
+                    "min_ess": float(np.min(result.ess)),
+                },
+                "occam_true": {
+                    "log_Z_M": normalized_log_z,
+                    "ess": result.ess,
+                    "min_ess": float(np.min(result.ess)),
+                    "derived_from_raw_with": (
+                        "bistar_gp.laplace_evidence._log_reference_volume"
+                    ),
+                },
+                "log_reference_volume": log_volume,
+                "is_calls": 1,
+            }
+        sweeps_by_seed[str(seed)] = sweeps
 
     pair_inputs = {
         "Linear_within_Sin+Linear": {
@@ -306,13 +418,25 @@ def run(out_dir: Path, *, n_is: int) -> dict[str, Any]:
         margin = restricted_min - encompassing_min
         holds = margin >= -MIN_G_TOLERANCE
         all_hold = all_hold and holds
-        orderings = {}
-        for convention in ("occam_false", "occam_true"):
-            orderings[convention] = _ordering_summary(
-                TAUS,
-                np.asarray(sweeps["Sin+Linear"][convention]["log_Z_M"]),
-                np.asarray(sweeps[restricted_name][convention]["log_Z_M"]),
+        orderings_by_seed = {}
+        for seed, sweeps in sweeps_by_seed.items():
+            orderings = {}
+            for convention in ("occam_false", "occam_true"):
+                orderings[convention] = _ordering_summary(
+                    TAUS,
+                    np.asarray(sweeps["Sin+Linear"][convention]["log_Z_M"]),
+                    np.asarray(sweeps[restricted_name][convention]["log_Z_M"]),
+                )
+            orderings_by_seed[seed] = orderings
+        crossing_uncertainty = {
+            convention: _crossing_uncertainty(
+                orderings_by_seed,
+                sweeps_by_seed,
+                restricted_name,
+                convention,
             )
+            for convention in ("occam_false", "occam_true")
+        }
         nested_pairs[pair_name] = {
             "restricted_model": restricted_name,
             "encompassing_model": "Sin+Linear",
@@ -340,21 +464,23 @@ def run(out_dir: Path, *, n_is: int) -> dict[str, Any]:
             "inequality_holds": holds,
             "verified_for_tau_count": len(TAUS),
             "minimum_is_tau_independent": True,
-            "Z_M_ordering": orderings,
+            "Z_M_ordering_by_seed": orderings_by_seed,
+            "crossing_uncertainty": crossing_uncertainty,
         }
 
     verdict_text = (
-        "Both numerical min-Ḡ inequalities hold on the n=50 informative-config, "
-        "MAP-based toy GP. E6 supports the reachable-set claim for these two "
-        "exact restrictions, while the finite-τ Z_M ordering still depends on "
-        "the reference-measure convention."
+        "Exact embeddings and the mean-only divergence make both min-Ḡ "
+        "inequalities analytic consequences of box containment. E6 confirms "
+        "that the implementation reproduces those consequences and quantifies "
+        "the margins; the finite-τ Z_M crossings provide the remaining empirical content."
         if all_hold
         else
-        "At least one numerical min-Ḡ inequality fails on the n=50 informative-config, "
-        "MAP-based toy GP, so E6 reports a counterexample to the reachable-set claim."
+        "The implementation failed to reproduce a min-Ḡ inequality that follows "
+        "analytically from exact embedding and box containment. E6 therefore "
+        "reports a machinery regression, not a counterexample to the containment argument."
     )
     results = {
-        "schema_version": 1,
+        "schema_version": 2,
         "case": "B",
         "artifact": "e6_nesting_monotonicity",
         "provenance": {
@@ -363,12 +489,13 @@ def run(out_dir: Path, *, n_is: int) -> dict[str, Any]:
             "metric": "pw_kl_vcal",
             "n": 50,
             "data_seed": DATA_SEED,
-            "is_seed": IS_SEED,
+            "is_seeds": list(IS_SEEDS),
             "x_eval_count": len(x_eval),
             "x_eval_range": [float(x_eval[0]), float(x_eval[-1])],
             "n_draws_requested": N_DRAWS,
             "gp_predictives_retained": retained,
             "n_is": n_is,
+            "is_calls_per_model_per_seed": 1,
             "n_perturb": N_PERTURB,
             "tau_grid": {
                 "definition": "numpy.logspace(-1.5, 2.5, 161)",
@@ -397,13 +524,13 @@ def run(out_dir: Path, *, n_is: int) -> dict[str, Any]:
             "exact_embedding_Gbar": EMBEDDING_TOLERANCE,
         },
         "nested_pairs": nested_pairs,
-        "model_sweeps": sweeps,
+        "model_sweeps_by_seed": sweeps_by_seed,
         "verdict": {
             "all_min_Gbar_inequalities_hold": all_hold,
             "statement": verdict_text,
             "scope": (
-                "numerical check on one n=50 informative-config, MAP-based averaged GP; "
-                "not a proof over all data priors or parameterizations"
+                "machinery check and margin/crossing quantification on one n=50 "
+                "informative-config, MAP-based averaged GP"
             ),
         },
     }
@@ -429,15 +556,19 @@ def main() -> None:
             f"margin={pair['margin_restricted_minus_encompassing']:.9f}; "
             f"holds={pair['inequality_holds']}"
         )
-        for convention in ("occam_false", "occam_true"):
-            crossings = pair["Z_M_ordering"][convention]["crossings"]
-            if crossings:
-                locations = ", ".join(
-                    f"{item['tau_log_interpolated']:.6f}" for item in crossings
+        for seed, orderings in pair["Z_M_ordering_by_seed"].items():
+            for convention in ("occam_false", "occam_true"):
+                crossings = orderings[convention]["crossings"]
+                if crossings:
+                    locations = ", ".join(
+                        f"{item['tau_log_interpolated']:.3f}"
+                        for item in crossings
+                    )
+                else:
+                    locations = "none on grid"
+                print(
+                    f"  seed {seed}, {convention} Z_M τ crossings: {locations}"
                 )
-            else:
-                locations = "none on grid"
-            print(f"  {convention} Z_M τ crossings: {locations}")
     print(results["verdict"]["statement"])
     print(f"wrote {args.out_dir.resolve() / 'e6_results.json'}")
 
diff --git a/experiments/occam_dial_figure.py b/experiments/occam_dial_figure.py
index 883d8c9..862fe94 100644
--- a/experiments/occam_dial_figure.py
+++ b/experiments/occam_dial_figure.py
@@ -29,6 +29,7 @@ if str(VIZ_SCRIPTS) not in sys.path:
     sys.path.insert(0, str(VIZ_SCRIPTS))
 
 import _viz_spaces as V  # noqa: E402
+from bistar_gp.laplace_evidence import laplace_log_Z_Mx  # noqa: E402
 
 
 MODEL_NAMES = ["Linear", "Sinusoidal", "Sin+Linear", "Quadratic"]
@@ -85,7 +86,7 @@ def _arm(
     occam: bool,
     n_is: int,
 ) -> dict[str, Any]:
-    names, log_z, posterior, diagnostics = V.model_prior_curves(
+    names, log_z, priors, diagnostics = V.model_prior_curves(
         spaces,
         x_eval,
         avg_gp,
@@ -100,8 +101,8 @@ def _arm(
         "estimator": estimator,
         "occam": occam,
         "log_Z_M": {name: float(log_z[0, j]) for j, name in enumerate(names)},
-        "model_posterior": {
-            name: float(posterior[0, j]) for j, name in enumerate(names)
+        "model_prior": {
+            name: float(priors[0, j]) for j, name in enumerate(names)
         },
         "ess": {
             name: None
@@ -117,7 +118,7 @@ def _assert_anchors(arms: dict[str, dict[str, Any]], tolerance: float) -> dict:
     for arm_name, expected_by_model in ANCHORS.items():
         checks[arm_name] = {}
         for model_name, expected in expected_by_model.items():
-            actual = arms[arm_name]["model_posterior"][model_name]
+            actual = arms[arm_name]["model_prior"][model_name]
             error = abs(actual - expected)
             passed = error <= tolerance
             checks[arm_name][model_name] = {
@@ -140,7 +141,11 @@ def _crosscheck_local_table(
     """Compare against the optional local D17 table without sourcing data."""
     path = REPO_ROOT / "runs" / "viz_unification" / "delta_table.md"
     if not path.exists():
-        return {"available": False, "path": str(path.relative_to(REPO_ROOT))}
+        return {
+            "available": False,
+            "machine_dependent": True,
+            "path": str(path.relative_to(REPO_ROOT)),
+        }
 
     rows: dict[str, list[float]] = {}
     wanted = {f"{arm_name}/n=50" for arm_name in arms}
@@ -160,7 +165,7 @@ def _crosscheck_local_table(
             checks[arm_name] = {"found": False}
             continue
         errors = {
-            model: abs(arms[arm_name]["model_posterior"][model] - rows[key][j])
+            model: abs(arms[arm_name]["model_prior"][model] - rows[key][j])
             for j, model in enumerate(MODEL_NAMES)
         }
         passed = max(errors.values()) <= tolerance
@@ -177,11 +182,44 @@ def _crosscheck_local_table(
             )
     return {
         "available": True,
+        "machine_dependent": True,
         "path": str(path.relative_to(REPO_ROOT)),
         "checks": checks,
     }
 
 
+def _p1_laplace_diagnostics(
+    spaces,
+    x_eval,
+    avg_gp,
+    starts_map,
+    arm: dict[str, Any],
+) -> dict[str, dict[str, Any]]:
+    """Obtain public-API diagnostics and verify the existing p1 values."""
+    diagnostics = {}
+    for name, param_space in spaces.items():
+        result = laplace_log_Z_Mx(
+            param_space,
+            x_eval,
+            avg_gp,
+            metric_name="pw_kl_vcal",
+            tau=TAU,
+            occam=True,
+            starts=starts_map[name],
+        )
+        expected = arm["log_Z_M"][name]
+        if not np.isclose(result.log_Z, expected, rtol=0.0, atol=1e-12):
+            raise AssertionError(
+                f"direct p1 Laplace log Z for {name} ({result.log_Z}) does not "
+                f"match the arm value ({expected})"
+            )
+        diagnostics[name] = {
+            "converged": bool(result.converged),
+            "n_clipped": int(result.n_clipped),
+        }
+    return diagnostics
+
+
 def _plot(arms: dict[str, dict[str, Any]], out_path: Path) -> None:
     colors = [V.COLORS[name] for name in MODEL_NAMES]
     panels = [
@@ -205,7 +243,7 @@ def _plot(arms: dict[str, dict[str, Any]], out_path: Path) -> None:
     for panel_index, (ax, (arm_name, title, alpha)) in enumerate(
         zip(axes, panels)
     ):
-        values = [arms[arm_name]["model_posterior"][name] for name in MODEL_NAMES]
+        values = [arms[arm_name]["model_prior"][name] for name in MODEL_NAMES]
         bars = ax.bar(
             np.arange(len(MODEL_NAMES)),
             values,
@@ -277,9 +315,69 @@ def _plot(arms: dict[str, dict[str, Any]], out_path: Path) -> None:
     plt.close(fig)
 
 
-def _fmt_posteriors(arm: dict[str, Any]) -> str:
+def _fmt_priors(arm: dict[str, Any]) -> str:
     return ", ".join(
-        f"{name} {arm['model_posterior'][name]:.6f}" for name in MODEL_NAMES
+        f"{name} {arm['model_prior'][name]:.3f}" for name in MODEL_NAMES
+    )
+
+
+def _seed_crossing_text(pair: dict[str, Any], convention: str) -> str:
+    pieces = []
+    for seed, orderings in pair["Z_M_ordering_by_seed"].items():
+        crossings = orderings[convention]["crossings"]
+        if not crossings:
+            pieces.append(f"seed {seed}: none on the grid")
+            continue
+        formatted = ", ".join(
+            f"{item['tau_log_interpolated']:.3f} within "
+            f"[{item['tau_bracket'][0]:.3f}, {item['tau_bracket'][1]:.3f}]"
+            for item in crossings
+        )
+        pieces.append(f"seed {seed}: {formatted}")
+    return "; ".join(pieces)
+
+
+def _resolution_paragraph(e6: dict[str, Any]) -> str:
+    linear = e6["nested_pairs"]["Linear_within_Sin+Linear"]
+    sinusoidal = e6["nested_pairs"]["Sinusoidal_within_Sin+Linear"]
+    linear_u = linear["crossing_uncertainty"]["occam_true"]
+    sinusoidal_u = sinusoidal["crossing_uncertainty"]["occam_true"]
+    linear_se = linear_u["ess_implied_one_se_common_mode_shift_seed_0"]
+    sinusoidal_se = sinusoidal_u["ess_implied_one_se_common_mode_shift_seed_0"]
+    linear_se_interval = linear_se["tau_interval_log_interpolated"]
+    sinusoidal_se_interval = sinusoidal_se["tau_interval_log_interpolated"]
+    sinusoidal_shift_upper_grid = sinusoidal_se[
+        "shifted_crossing_grid_brackets"
+    ][1][1]
+    return (
+        "**Resolution (RESOLVED, E6):** Given exact embeddings and the mean-only "
+        "`pw_kl_vcal` divergence, each min-Ḡ inequality follows analytically from "
+        "box containment. E6 confirms that the implementation reproduces this "
+        "consequence and quantifies restricted-minus-encompassing margins of "
+        f"{linear['margin_restricted_minus_encompassing']:.3f} nats for Linear and "
+        f"{sinusoidal['margin_restricted_minus_encompassing']:.3f} nats for "
+        "Sinusoidal. Across 161 τ values and IS seeds 0, 1, and 2, raw Lebesgue "
+        "`occam=False` yields no pairwise crossing. With `occam=True`, Linear "
+        f"crosses at {_seed_crossing_text(linear, 'occam_true')}; the per-seed "
+        f"interpolant spread is [{linear_u['per_seed_interpolant_spread'][0]:.3f}, "
+        f"{linear_u['per_seed_interpolant_spread'][1]:.3f}], and the seed-0 "
+        f"ESS-implied one-SE shift interval is [{linear_se_interval[0]:.3f}, "
+        f"{linear_se_interval[1]:.3f}]. Its seed-0 bracket delta swing "
+        f"({linear_se['delta_log_Z_swing_across_nominal_bracket']:.3f} nats) "
+        "exceeds the ESS-implied SE "
+        f"({max(linear_se['delta_log_Z_se_at_nominal_bracket']):.3f} nats), "
+        "which supports reporting τ=0.295. Sinusoidal crosses at "
+        f"{_seed_crossing_text(sinusoidal, 'occam_true')}; the supported summary "
+        "is τ ≈ 1.5, with per-seed interpolant spread "
+        f"[{sinusoidal_u['per_seed_interpolant_spread'][0]:.3f}, "
+        f"{sinusoidal_u['per_seed_interpolant_spread'][1]:.3f}] and seed-0 "
+        f"ESS-implied shift roots [{sinusoidal_se_interval[0]:.3f}, "
+        f"{sinusoidal_se_interval[1]:.3f}]. The enclosing shifted-root grid "
+        f"bracket gives the uncertainty statement τ about "
+        f"{sinusoidal_se_interval[0]:.2f} to {sinusoidal_shift_upper_grid:.2f}. "
+        "Crossing resolution is set by the larger of grid spacing and Monte "
+        "Carlo error. The empirical content comprises the margins and finite-τ "
+        "Z_M crossings."
     )
 
 
@@ -289,6 +387,10 @@ def write_combined_readme(out_dir: Path) -> None:
     e6_path = out_dir / "e6_results.json"
     figure = json.loads(figure_path.read_text(encoding="utf-8")) if figure_path.exists() else None
     e6 = json.loads(e6_path.read_text(encoding="utf-8")) if e6_path.exists() else None
+    if figure is not None and figure.get("schema_version") != 2:
+        figure = None
+    if e6 is not None and e6.get("schema_version") != 2:
+        e6 = None
 
     lines = [
         "# Case B: Occam dial and nesting monotonicity",
@@ -311,29 +413,41 @@ def write_combined_readme(out_dir: Path) -> None:
         "",
         "`occam_dial.png` and `figure_results.json` use τ=0.3, IS seed 0, "
         "n_is=40,000, five seeded perturbations per legacy start, and the canonical "
-        "visualization parameter boxes. The optional `runs/viz_unification/delta_table.md` "
-        "only supplies a cross-check when present.",
+        "visualization parameter boxes.",
         "",
-        "The anchor tolerance equals 0.003 in absolute model probability. The published "
-        "anchors were rounded to three decimals, and the remaining allowance covers small "
-        "cross-platform optimizer differences. The tolerance remains well below the 0.042 "
-        "p2 Linear versus Sin+Linear gap.",
+        "The 0.003 absolute-probability anchor tolerance provides a same-seed "
+        "reproduction gate for three-decimal source anchors, not an accuracy claim.",
+        "",
+        "At p2, ESS implies SE(log Z) of approximately 0.008, 0.017, and 0.038 "
+        "nats for Linear, Sin+Linear, and Sinusoidal, respectively; the induced "
+        "model-probability SE is approximately 0.005.",
+        "",
+        "The script cross-checks against `runs/viz_unification/delta_table.md` when "
+        "that local untracked file exists; availability is machine-dependent and "
+        "recorded in `figure_results.json`.",
     ]
     if figure is not None:
-        lines.extend(["", "Fresh n=50 posteriors:", ""])
+        lines.extend(["", "### Fresh n=50 induced model priors", ""])
         for arm_name in (
             "p1_priors_lap_occam",
             "p2_priors_is_occam",
             "p3_priors_canonical",
         ):
-            lines.append(f"- `{arm_name}`: {_fmt_posteriors(figure['arms'][arm_name])}")
-        cross = figure["optional_local_crosscheck"]
-        lines.extend(
-            [
-                "",
-                f"The optional D17 table cross-check was {'available' if cross['available'] else 'not available'}.",
-            ]
+            lines.append(f"- `{arm_name}`: {_fmt_priors(figure['arms'][arm_name])}")
+        diagnostics = figure["arms"]["p1_priors_lap_occam"][
+            "laplace_diagnostics"
+        ]
+        diagnostics_text = "; ".join(
+            f"{name} n_clipped={diagnostics[name]['n_clipped']}, "
+            f"converged={diagnostics[name]['converged']}"
+            for name in MODEL_NAMES
         )
+        lines.extend(["", f"Direct p1 Laplace diagnostics: {diagnostics_text}."])
+        if any(item["n_clipped"] > 0 for item in diagnostics.values()):
+            lines.append(
+                "At least one p1 Hessian eigenvalue was clipped, so the affected "
+                "log integral contains a floor- or cap-dependent regularization term."
+            )
 
     lines.extend(
         [
@@ -345,10 +459,11 @@ def write_combined_readme(out_dir: Path) -> None:
             "",
             "## E6 computation",
             "",
-            "E6 uses 161 log-spaced τ values from 10^-1.5 through 10^2.5, IS seed 0, "
-            "n_is=100,000, and the same five perturbations per start. One "
-            "`is_log_Z_Mx` call per model computes the full raw sweep; the package's "
-            "`_log_reference_volume` helper supplies the occam-normalized sweep. The visualization "
+            "E6 uses 161 log-spaced τ values from 10^-1.5 through 10^2.5, IS seeds "
+            "0, 1, and 2, n_is=100,000 per seed, and the same five perturbations "
+            "per start. One `is_log_Z_Mx` call per model per seed computes the full "
+            "raw sweep; the package's `_log_reference_volume` helper supplies the "
+            "occam-normalized sweep. The visualization "
             "box uses A >= 0.01 for numerical plotting. E6 alone extends the encompassing "
             "Sin+Linear box to A >= 0 so Linear at A=0 forms an exact restriction. All "
             "other bounds match the canonical visualization boxes. The embedded restricted "
@@ -356,33 +471,37 @@ def write_combined_readme(out_dir: Path) -> None:
             "starts plus the best encompassing optimum, which avoids flat boundary-Hessian "
             "components without changing the integral.",
             "",
-            "The min-Ḡ comparison tolerance equals 1e-8 in Ḡ units. It only classifies "
-            "floating-point near-ties and remains many orders of magnitude below the observed "
-            "margins. τ crossings use linear interpolation in log10(τ) inside the reported "
-            "adjacent grid bracket; the bracket, rather than extra decimal places in the "
-            "interpolant, provides the resolution statement.",
+            "Given the exact embeddings and mean-only divergence, the min-Ḡ inequality "
+            "follows analytically from box containment. The retained check confirms that "
+            "the implementation reproduces that consequence and quantifies the margins. "
+            "The 1e-8 comparison tolerance only classifies floating-point near-ties. "
+            "Crossing resolution is set by the larger of grid spacing and Monte Carlo error.",
         ]
     )
     if e6 is not None:
         lines.extend(["", "Fresh E6 results:", ""])
         for pair_name, pair in e6["nested_pairs"].items():
             lines.append(
-                f"- `{pair_name}`: min Ḡ(restricted)={pair['restricted']['min_Gbar']:.9f}, "
-                f"min Ḡ(encompassing)={pair['encompassing']['min_Gbar']:.9f}, "
-                f"margin={pair['margin_restricted_minus_encompassing']:.9f}, "
+                f"- `{pair_name}`: min Ḡ(restricted)={pair['restricted']['min_Gbar']:.3f}, "
+                f"min Ḡ(encompassing)={pair['encompassing']['min_Gbar']:.3f}, "
+                f"margin={pair['margin_restricted_minus_encompassing']:.3f}, "
                 f"holds={pair['inequality_holds']}."
             )
             for convention in ("occam_false", "occam_true"):
-                crossing_text = ", ".join(
-                    f"{item['tau_log_interpolated']:.6f} within "
-                    f"[{item['tau_bracket'][0]:.6f}, {item['tau_bracket'][1]:.6f}]"
-                    for item in pair["Z_M_ordering"][convention]["crossings"]
-                ) or "no crossing on the grid"
-                lines.append(f"  - `{convention}`: {crossing_text}.")
+                lines.append(
+                    f"  - `{convention}`: {_seed_crossing_text(pair, convention)}."
+                )
         lines.extend(
             [
                 "",
                 f"E6 verdict: {e6['verdict']['statement']}",
+                "",
+                "## REVIEW_AND_VET resolution (mirrored)",
+                "",
+                "The `kb/` tree is local by design and gitignored; this committed mirror "
+                "preserves the resolution for clean checkouts.",
+                "",
+                _resolution_paragraph(e6),
             ]
         )
 
@@ -394,7 +513,7 @@ def write_combined_readme(out_dir: Path) -> None:
             "- `occam_dial.png`: E4 attribution-ladder figure, kept below 2 MB.",
             "- `figure_results.json`: all freshly computed E4 arm values and anchor checks.",
             "- `e6_results.json`: min-Ḡ optima, exact-embedding checks, both Z_M conventions, "
-            "ESS diagnostics, the full τ grid, and crossing brackets.",
+            "three-seed ESS diagnostics, the full τ grid, and crossing uncertainty.",
         ]
     )
     (out_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
@@ -438,11 +557,20 @@ def run(out_dir: Path, *, n_is: int, anchor_tolerance: float) -> dict[str, Any]:
             n_is=n_is,
         ),
     }
+    arms["p1_priors_lap_occam"]["laplace_diagnostics"] = (
+        _p1_laplace_diagnostics(
+            spaces,
+            x_eval,
+            avg_gp,
+            starts_map,
+            arms["p1_priors_lap_occam"],
+        )
+    )
     anchor_checks = _assert_anchors(arms, anchor_tolerance)
     local_crosscheck = _crosscheck_local_table(arms, anchor_tolerance)
 
     results = {
-        "schema_version": 1,
+        "schema_version": 2,
         "case": "B",
         "artifact": "occam_dial_figure",
         "provenance": {
@@ -505,9 +633,9 @@ def main() -> None:
         n_is=args.n_is,
         anchor_tolerance=args.anchor_tolerance,
     )
-    print("n=50 model posteriors")
+    print("n=50 induced model priors")
     for arm_name, arm in results["arms"].items():
-        print(f"  {arm_name}: {_fmt_posteriors(arm)}")
+        print(f"  {arm_name}: {_fmt_priors(arm)}")
     print(f"wrote {args.out_dir.resolve() / 'figure_results.json'}")
     print(f"wrote {args.out_dir.resolve() / 'occam_dial.png'}")
 
diff --git a/runs/occam_dial/README.md b/runs/occam_dial/README.md
index 1a14cd1..fc99520 100644
--- a/runs/occam_dial/README.md
+++ b/runs/occam_dial/README.md
@@ -11,39 +11,49 @@ Both scripts use local CPU computation only. They construct the n=50 averaged GP
 
 ## Figure computation
 
-`occam_dial.png` and `figure_results.json` use τ=0.3, IS seed 0, n_is=40,000, five seeded perturbations per legacy start, and the canonical visualization parameter boxes. The optional `runs/viz_unification/delta_table.md` only supplies a cross-check when present.
+`occam_dial.png` and `figure_results.json` use τ=0.3, IS seed 0, n_is=40,000, five seeded perturbations per legacy start, and the canonical visualization parameter boxes.
 
-The anchor tolerance equals 0.003 in absolute model probability. The published anchors were rounded to three decimals, and the remaining allowance covers small cross-platform optimizer differences. The tolerance remains well below the 0.042 p2 Linear versus Sin+Linear gap.
+The 0.003 absolute-probability anchor tolerance provides a same-seed reproduction gate for three-decimal source anchors, not an accuracy claim.
 
-Fresh n=50 posteriors:
+At p2, ESS implies SE(log Z) of approximately 0.008, 0.017, and 0.038 nats for Linear, Sin+Linear, and Sinusoidal, respectively; the induced model-probability SE is approximately 0.005.
 
-- `p1_priors_lap_occam`: Linear 0.534121, Sinusoidal 0.075747, Sin+Linear 0.382052, Quadratic 0.008080
-- `p2_priors_is_occam`: Linear 0.506877, Sinusoidal 0.020499, Sin+Linear 0.464791, Quadratic 0.007834
-- `p3_priors_canonical`: Linear 0.007040, Sinusoidal 0.001093, Sin+Linear 0.991758, Quadratic 0.000109
+The script cross-checks against `runs/viz_unification/delta_table.md` when that local untracked file exists; availability is machine-dependent and recorded in `figure_results.json`.
 
-The optional D17 table cross-check was available.
+### Fresh n=50 induced model priors
+
+- `p1_priors_lap_occam`: Linear 0.534, Sinusoidal 0.076, Sin+Linear 0.382, Quadratic 0.008
+- `p2_priors_is_occam`: Linear 0.507, Sinusoidal 0.020, Sin+Linear 0.465, Quadratic 0.008
+- `p3_priors_canonical`: Linear 0.007, Sinusoidal 0.001, Sin+Linear 0.992, Quadratic 0.000
+
+Direct p1 Laplace diagnostics: Linear n_clipped=0, converged=True; Sinusoidal n_clipped=0, converged=True; Sin+Linear n_clipped=0, converged=True; Quadratic n_clipped=0, converged=True.
 
 The D17-recorded legacy 0.934 and 0.693 values provide historical context only. `bistar_viz/scripts/viz_unification_compare.py`, with pinned legacy commit `a87356a`, regenerates those legacy arms. Neither new script invokes that git-based extraction path.
 
 ## E6 computation
 
-E6 uses 161 log-spaced τ values from 10^-1.5 through 10^2.5, IS seed 0, n_is=100,000, and the same five perturbations per start. One `is_log_Z_Mx` call per model computes the full raw sweep; the package's `_log_reference_volume` helper supplies the occam-normalized sweep. The visualization box uses A >= 0.01 for numerical plotting. E6 alone extends the encompassing Sin+Linear box to A >= 0 so Linear at A=0 forms an exact restriction. All other bounds match the canonical visualization boxes. The embedded restricted optima seed the encompassing multi-start optimization. IS uses interior perturbed starts plus the best encompassing optimum, which avoids flat boundary-Hessian components without changing the integral.
+E6 uses 161 log-spaced τ values from 10^-1.5 through 10^2.5, IS seeds 0, 1, and 2, n_is=100,000 per seed, and the same five perturbations per start. One `is_log_Z_Mx` call per model per seed computes the full raw sweep; the package's `_log_reference_volume` helper supplies the occam-normalized sweep. The visualization box uses A >= 0.01 for numerical plotting. E6 alone extends the encompassing Sin+Linear box to A >= 0 so Linear at A=0 forms an exact restriction. All other bounds match the canonical visualization boxes. The embedded restricted optima seed the encompassing multi-start optimization. IS uses interior perturbed starts plus the best encompassing optimum, which avoids flat boundary-Hessian components without changing the integral.
 
-The min-Ḡ comparison tolerance equals 1e-8 in Ḡ units. It only classifies floating-point near-ties and remains many orders of magnitude below the observed margins. τ crossings use linear interpolation in log10(τ) inside the reported adjacent grid bracket; the bracket, rather than extra decimal places in the interpolant, provides the resolution statement.
+Given the exact embeddings and mean-only divergence, the min-Ḡ inequality follows analytically from box containment. The retained check confirms that the implementation reproduces that consequence and quantifies the margins. The 1e-8 comparison tolerance only classifies floating-point near-ties. Crossing resolution is set by the larger of grid spacing and Monte Carlo error.
 
 Fresh E6 results:
 
-- `Linear_within_Sin+Linear`: min Ḡ(restricted)=2.424774370, min Ḡ(encompassing)=0.045516783, margin=2.379257587, holds=True.
-  - `occam_false`: no crossing on the grid.
-  - `occam_true`: 0.295184 within [0.281838, 0.298538].
-- `Sinusoidal_within_Sin+Linear`: min Ḡ(restricted)=2.546229649, min Ḡ(encompassing)=0.045516783, margin=2.500712865, holds=True.
-  - `occam_false`: no crossing on the grid.
-  - `occam_true`: 1.484355 within [1.412538, 1.496236].
+- `Linear_within_Sin+Linear`: min Ḡ(restricted)=2.425, min Ḡ(encompassing)=0.046, margin=2.379, holds=True.
+  - `occam_false`: seed 0: none on the grid; seed 1: none on the grid; seed 2: none on the grid.
+  - `occam_true`: seed 0: 0.295 within [0.282, 0.299]; seed 1: 0.295 within [0.282, 0.299]; seed 2: 0.296 within [0.282, 0.299].
+- `Sinusoidal_within_Sin+Linear`: min Ḡ(restricted)=2.546, min Ḡ(encompassing)=0.046, margin=2.501, holds=True.
+  - `occam_false`: seed 0: none on the grid; seed 1: none on the grid; seed 2: none on the grid.
+  - `occam_true`: seed 0: 1.484 within [1.413, 1.496]; seed 1: 1.584 within [1.496, 1.585]; seed 2: 1.382 within [1.334, 1.413].
+
+E6 verdict: Exact embeddings and the mean-only divergence make both min-Ḡ inequalities analytic consequences of box containment. E6 confirms that the implementation reproduces those consequences and quantifies the margins; the finite-τ Z_M crossings provide the remaining empirical content.
+
+## REVIEW_AND_VET resolution (mirrored)
+
+The `kb/` tree is local by design and gitignored; this committed mirror preserves the resolution for clean checkouts.
 
-E6 verdict: Both numerical min-Ḡ inequalities hold on the n=50 informative-config, MAP-based toy GP. E6 supports the reachable-set claim for these two exact restrictions, while the finite-τ Z_M ordering still depends on the reference-measure convention.
+**Resolution (RESOLVED, E6):** Given exact embeddings and the mean-only `pw_kl_vcal` divergence, each min-Ḡ inequality follows analytically from box containment. E6 confirms that the implementation reproduces this consequence and quantifies restricted-minus-encompassing margins of 2.379 nats for Linear and 2.501 nats for Sinusoidal. Across 161 τ values and IS seeds 0, 1, and 2, raw Lebesgue `occam=False` yields no pairwise crossing. With `occam=True`, Linear crosses at seed 0: 0.295 within [0.282, 0.299]; seed 1: 0.295 within [0.282, 0.299]; seed 2: 0.296 within [0.282, 0.299]; the per-seed interpolant spread is [0.295, 0.296], and the seed-0 ESS-implied one-SE shift interval is [0.295, 0.296]. Its seed-0 bracket delta swing (0.354 nats) exceeds the ESS-implied SE (0.012 nats), which supports reporting τ=0.295. Sinusoidal crosses at seed 0: 1.484 within [1.413, 1.496]; seed 1: 1.584 within [1.496, 1.585]; seed 2: 1.382 within [1.334, 1.413]; the supported summary is τ ≈ 1.5, with per-seed interpolant spread [1.382, 1.584] and seed-0 ESS-implied shift roots [1.392, 1.563]. The enclosing shifted-root grid bracket gives the uncertainty statement τ about 1.39 to 1.58. Crossing resolution is set by the larger of grid spacing and Monte Carlo error. The empirical content comprises the margins and finite-τ Z_M crossings.
 
 ## Files
 
 - `occam_dial.png`: E4 attribution-ladder figure, kept below 2 MB.
 - `figure_results.json`: all freshly computed E4 arm values and anchor checks.
-- `e6_results.json`: min-Ḡ optima, exact-embedding checks, both Z_M conventions, ESS diagnostics, the full τ grid, and crossing brackets.
+- `e6_results.json`: min-Ḡ optima, exact-embedding checks, both Z_M conventions, three-seed ESS diagnostics, the full τ grid, and crossing uncertainty.
diff --git a/runs/occam_dial/figure_results.json b/runs/occam_dial/figure_results.json
index 02d555c..89127ab 100644
--- a/runs/occam_dial/figure_results.json
+++ b/runs/occam_dial/figure_results.json
@@ -47,13 +47,31 @@
         "Sinusoidal": null
       },
       "estimator": "laplace",
+      "laplace_diagnostics": {
+        "Linear": {
+          "converged": true,
+          "n_clipped": 0
+        },
+        "Quadratic": {
+          "converged": true,
+          "n_clipped": 0
+        },
+        "Sin+Linear": {
+          "converged": true,
+          "n_clipped": 0
+        },
+        "Sinusoidal": {
+          "converged": true,
+          "n_clipped": 0
+        }
+      },
       "log_Z_M": {
         "Linear": -15.165401538600314,
         "Quadratic": -19.3566141369075,
         "Sin+Linear": -15.500468524289005,
         "Sinusoidal": -17.118624784446126
       },
-      "model_posterior": {
+      "model_prior": {
         "Linear": 0.534121176101774,
         "Quadratic": 0.008080147573789803,
         "Sin+Linear": 0.3820516271444941,
@@ -75,7 +93,7 @@
         "Sin+Linear": -15.261431576239175,
         "Sinusoidal": -18.382664063985942
       },
-      "model_posterior": {
+      "model_prior": {
         "Linear": 0.5068765246476576,
         "Quadratic": 0.00783405135143996,
         "Sin+Linear": 0.46479085571474016,
@@ -97,7 +115,7 @@
         "Sin+Linear": -6.538003940835886,
         "Sinusoidal": -13.348115882696586
       },
-      "model_posterior": {
+      "model_prior": {
         "Linear": 0.007040016665579024,
         "Quadratic": 0.00010880727236574364,
         "Sin+Linear": 0.9917576943072977,
@@ -168,6 +186,7 @@
         }
       }
     },
+    "machine_dependent": true,
     "path": "runs/viz_unification/delta_table.md"
   },
   "provenance": {
@@ -190,5 +209,5 @@
       10.0
     ]
   },
-  "schema_version": 1
+  "schema_version": 2
 }

=== REGENERATED e6_results.json (ABRIDGED: long arrays elided) ===
{
 "artifact": "e6_nesting_monotonicity",
 "case": "B",
 "model_sweeps_by_seed": {
  "0": {
   "Linear": {
    "is_calls": 1,
    "log_reference_volume": 3.6888794541139367,
    "occam_false": {
     "ess": {
      "__abridged__": "161 floats",
      "first3": [
       22358.460489324258,
       22877.203247248406,
       23366.738899135617
      ],
      "last3": [
       41787.646449387765,
       42461.61424369554,
       43112.12888745887
      ],
      "min": 14903.232260820918,
      "max": 43112.12888745887
     },
     "log_Z_M": {
      "__abridged__": "161 floats",
      "first3": [
       -82.32245983423631,
       -77.97555999123718,
       -73.86859013935329
      ],
      "last3": [
       2.974025922025577,
       3.004527577780113,
       3.0341005701083095
      ],
      "min": -82.32245983423631,
      "max": 3.0341005701083095
     },
     "min_ess": 14903.232260820918
    },
    "occam_true": {
     "derived_from_raw_with": "bistar_gp.laplace_evidence._log_reference_volume",
     "ess": {
      "__abridged__": "161 floats",
      "first3": [
       22358.460489324258,
       22877.203247248406,
       23366.738899135617
      ],
      "last3": [
       41787.646449387765,
       42461.61424369554,
       43112.12888745887
      ],
      "min": 14903.232260820918,
      "max": 43112.12888745887
     },
     "log_Z_M": {
      "__abridged__": "161 floats",
      "first3": [
       -86.01133928835024,
       -81.6644394453511,
       -77.55746959346722
      ],
      "last3": [
       -0.7148535320883598,
       -0.6843518763338237,
       -0.6547788840056272
      ],
      "min": -86.01133928835024,
      "max": -0.6547788840056272
     },
     "min_ess": 14903.232260820918
    }
   },
   "Sin+Linear": {
    "is_calls": 1,
    "log_reference_volume": 8.725429638073964,
    "occam_false": {
     "ess": {
      "__abridged__": "161 floats",
      "first3": [
       9784.141295821242,
       9854.426660436255,
       9838.264221064028
      ],
      "last3": [
       38938.01855407652,
       39680.895364414806,
       40398.81858414094
      ],
      "min": 830.8870807818723,
      "max": 40398.81858414094
     },
     "log_Z_M": {
      "__abridged__": "161 floats",
      "first3": [
       -13.67298197519908,
       -13.447511767413268,
       -13.226383133220434
      ],
      "last3": [
       7.9407587544467635,
       7.97508221701081,
       8.00827630767664
      ],
      "min": -13.67298197519908,
      "max": 8.00827630767664
     },
     "min_ess": 830.8870807818723
    },
    "occam_true": {
     "derived_from_raw_with": "bistar_gp.laplace_evidence._log_reference_volume",
     "ess": {
      "__abridged__": "161 floats",
      "first3": [
       9784.141295821242,
       9854.426660436255,
       9838.264221064028
      ],
      "last3": [
       38938.01855407652,
       39680.895364414806,
       40398.81858414094
      ],
      "min": 830.8870807818723,
      "max": 40398.81858414094
     },
     "log_Z_M": {
      "__abridged__": "161 floats",
      "first3": [
       -22.398411613273044,
       -22.17294140548723,
       -21.9518127712944
      ],
      "last3": [
       -0.7846708836272,
       -0.7503474210631538,
       -0.7171533303973234
      ],
      "min": -22.398411613273044,
      "max": -0.7171533303973234
     },
     "min_ess": 830.8870807818723
    }
   },
   "Sinusoidal": {
    "is_calls": 1,
    "log_reference_volume": 5.034548181289354,
    "occam_false": {
     "ess": {
      "__abridged__": "161 floats",
      "first3": [
       1734.0482913807937,
       1817.3570432452789,
       1895.0850090273177
      ],
      "last3": [
       53296.69622494243,
       53296.897753581645,
       53295.86858528673
      ],
      "min": 1372.8868832793878,
      "max": 53296.897753581645
     },
     "log_Z_M": {
      "__abridged__": "161 floats",
      "first3": [
       -89.45840667787704,
       -84.84502360523015,
       -80.48381496312514
      ],
      "last3": [
       4.914919470087712,
       4.921671168389681,
       4.9280581057723385
      ],
      "min": -89.45840667787704,
      "max": 4.9280581057723385
     },
     "min_ess": 1372.8868832793878
    },
    "occam_true": {
     "derived_from_raw_with": "bistar_gp.laplace_evidence._log_reference_volume",
     "ess": {
      "__abridged__": "161 floats",
      "first3": [
       1734.0482913807937,
       1817.3570432452789,
       1895.0850090273177
      ],
      "last3": [
       53296.69622494243,
       53296.897753581645,
       53295.86858528673
      ],
      "min": 1372.8868832793878,
      "max": 53296.897753581645
     },
     "log_Z_M": {
      "__abridged__": "161 floats",
      "first3": [
       -94.49295485916639,
       -89.8795717865195,
       -85.5183631444145
      ],
      "last3": [
       -0.11962871120164209,
       -0.11287701289967345,
       -0.10649007551701573
      ],
      "min": -94.49295485916639,
      "max": -0.10649007551701573
     },
     "min_ess": 1372.8868832793878
    }
   }
  },
  "1": {
   "Linear": {
    "is_calls": 1,
    "log_reference_volume": 3.6888794541139367,
    "occam_false": {
     "ess": {
      "__abridged__": "161 floats",
      "first3": [
       22330.75214480198,
       22850.709923224073,
       23341.65179908466
      ],
      "last3": [
       41731.2672856774,
       42409.190835926514,
       43063.32270473773
      ],
      "min": 14790.150193150868,
      "max": 43063.32270473773
     },
     "log_Z_M": {
      "__abridged__": "161 floats",
      "first3": [
       -82.32317520214156,
       -77.97651100519197,
       -73.86975049446981
      ],
      "last3": [
       2.9690895873275345,
       2.999796545496155,
       3.0295682537254596
      ],
      "min": -82.32317520214156,
      "max": 3.0295682537254596
     },
     "min_ess": 14790.150193150868
    },
    "occam_true": {
     "derived_from_raw_with": "bistar_gp.laplace_evidence._log_reference_volume",
     "ess": {
      "__abridged__": "161 floats",
      "first3": [
       22330.75214480198,
       22850.709923224073,
       23341.65179908466
      ],
      "last3": [
       41731.2672856774,
       42409.190835926514,
       43063.32270473773
      ],
      "min": 14790.150193150868,
      "max": 43063.32270473773
     },
     "log_Z_M": {
      "__abridged__": "161 floats",
      "first3": [
       -86.01205465625549,
       -81.6653904593059,
       -77.55862994858374
      ],
      "last3": [
       -0.7197898667864022,
       -0.6890829086177819,
       -0.6593112003884771
      ],
      "min": -86.01205465625549,
      "max": -0.6593112003884771
     },
     "min_ess": 14790.150193150868
    }
   },
   "Sin+Linear": {
    "is_calls": 1,
    "log_reference_volume": 8.725429638073964,
    "occam_false": {
     "ess": {
      "__abridged__": "161 floats",
      "first3": [
       9724.045699115868,
       9795.102862489992,
       9783.004221758983
      ],
      "last3": [
       38930.06191051065,
       39672.80445274916,
       40390.30358448224
      ],
      "min": 565.5509141920479,
      "max": 40390.30358448224
     },
     "log_Z_M": {
      "__abridged__": "161 floats",
      "first3": [
       -13.677224887244542,
       -13.452453463554582,
       -13.23200666609805
      ],
      "last3": [
       7.9419948876796855,
       7.97624283456121,
       8.00936335325021
      ],
      "min": -13.677224887244542,
      "max": 8.00936335325021
     },
     "min_ess": 565.5509141920479
    },
    "occam_true": {
     "derived_from_raw_with": "bistar_gp.laplace_evidence._log_reference_volume",
     "ess": {
      "__abridged__": "161 floats",
      "first3": [
       9724.045699115868,
       9795.102862489992,
       9783.004221758983
      ],
      "last3": [
       38930.06191051065,
       39672.80445274916,
       40390.30358448224
      ],
      "min": 565.5509141920479,
      "max": 40390.30358448224
     },
     "log_Z_M": {
      "__abridged__": "161 floats",
      "first3": [
       -22.402654525318503,
       -22.177883101628545,
       -21.957436304172013
      ],
      "last3": [
       -0.783434750394278,
       -0.7491868035127531,
       -0.7160662848237536
      ],
      "min": -22.402654525318503,
      "max": -0.7160662848237536
     },
     "min_ess": 565.5509141920479
    }
   },
   "Sinusoidal": {
    "is_calls": 1,
    "log_reference_volume": 5.034548181289354,
    "occam_false": {
     "ess": {
      "__abridged__": "161 floats",
      "first3": [
       1813.4460587436142,
       1900.4003151254608,
       1980.8820742488622
      ],
      "last3": [
       53159.01624884227,
       53159.48420744627,
       53158.71437334382
      ],
      "min": 1414.9436096219306,
      "max": 53159.48420744627
     },
     "log_Z_M": {
      "__abridged__": "161 floats",
      "first3": [
       -89.41367189345402,
       -84.79924209193017,
       -80.43715520108024
      ],
      "last3": [
       4.913250475506148,
       4.919998801753005,
       4.926382510927732
      ],
      "min": -89.41367189345402,
      "max": 4.926382510927732
     },
     "min_ess": 1414.9436096219306
    },
    "occam_true": {
     "derived_from_raw_with": "bistar_gp.laplace_evidence._log_reference_volume",
     "ess": {
      "__abridged__": "161 floats",
      "first3": [
       1813.4460587436142,
       1900.4003151254608,
       1980.8820742488622
      ],
      "last3": [
       53159.01624884227,
       53159.48420744627,
       53158.71437334382
      ],
      "min": 1414.9436096219306,
      "max": 53159.48420744627
     },
     "log_Z_M": {
      "__abridged__": "161 floats",
      "first3": [
       -94.44822007474338,
       -89.83379027321952,
       -85.4717033823696
      ],
      "last3": [
       -0.12129770578320631,
       -0.11454937953634925,
       -0.10816567036162184
      ],
      "min": -94.44822007474338,
      "max": -0.10816567036162184
     },
     "min_ess": 1414.9436096219306
    }
   }
  },
  "2": {
   "Linear": {
    "is_calls": 1,
    "log_reference_volume": 3.6888794541139367,
    "occam_false": {
     "ess": {
      "__abridged__": "161 floats",
      "first3": [
       22333.649695515956,
       22845.730855757134,
       23328.17763847564
      ],
      "last3": [
       41854.63180970728,
       42528.66844815673,
       43178.824735366186
      ],
      "min": 14814.100950525637,
      "max": 43178.824735366186
     },
     "log_Z_M": {
      "__abridged__": "161 floats",
      "first3": [
       -82.32330190485037,
       -77.97641322529252,
       -73.86948402083746
      ],
      "last3": [
       2.972363503560958,
       3.00298117845211,
       3.032662878848585
      ],
      "min": -82.32330190485037,
      "max": 3.032662878848585
     },
     "min_ess": 14814.100950525637
    },
    "occam_true": {
     "derived_from_raw_with": "bistar_gp.laplace_evidence._log_reference_volume",
     "ess": {
      "__abridged__": "161 floats",
      "first3": [
       22333.649695515956,
       22845.730855757134,
       23328.17763847564
      ],
      "last3": [
       41854.63180970728,
       42528.66844815673,
       43178.824735366186
      ],
      "min": 14814.100950525637,
      "max": 43178.824735366186
     },
     "log_Z_M": {
      "__abridged__": "161 floats",
      "first3": [
       -86.0121813589643,
       -81.66529267940645,
       -77.55836347495139
      ],
      "last3": [
       -0.7165159505529788,
       -0.6858982756618266,
       -0.6562165752653515
      ],
      "min": -86.0121813589643,
      "max": -0.6562165752653515
     },
     "min_ess": 14814.100950525637
    }
   },
   "Sin+Linear": {
    "is_calls": 1,
    "log_reference_volume": 8.725429638073964,
    "occam_false": {
     "ess": {
      "__abridged__": "161 floats",
      "first3": [
       9718.306029084217,
       9780.247159132734,
       9759.394365577873
      ],
      "last3": [
       38954.20163768611,
       39699.36546732579,
       40418.73833421095
      ],
      "min": 457.30151391594956,
      "max": 40418.73833421095
     },
     "log_Z_M": {
      "__abridged__": "161 floats",
      "first3": [
       -13.675931482198632,
       -13.45208917158748,
       -13.232663254438355
      ],
      "last3": [
       7.94088897878642,
       7.975234142904307,
       8.008445498190143
      ],
      "min": -13.675931482198632,
      "max": 8.008445498190143
     },
     "min_ess": 457.30151391594956
    },
    "occam_true": {
     "derived_from_raw_with": "bistar_gp.laplace_evidence._log_reference_volume",
     "ess": {
      "__abridged__": "161 floats",
      "first3": [
       9718.306029084217,
       9780.247159132734,
       9759.394365577873
      ],
      "last3": [
       38954.20163768611,
       39699.36546732579,
       40418.73833421095
      ],
      "min": 457.30151391594956,
      "max": 40418.73833421095
     },
     "log_Z_M": {
      "__abridged__": "161 floats",
      "first3": [
       -22.401361120272597,
       -22.177518809661443,
       -21.95809289251232
      ],
      "last3": [
       -0.7845406592875435,
       -0.7501954951696561,
       -0.7169841398838201
      ],
      "min": -22.401361120272597,
      "max": -0.7169841398838201
     },
     "min_ess": 457.30151391594956
    }
   },
   "Sinusoidal": {
    "is_calls": 1,
    "log_reference_volume": 5.034548181289354,
    "occam_false": {
     "ess": {
      "__abridged__": "161 floats",
      "first3": [
       1824.7564335069862,
       1910.4691969903647,
       1990.8046438407628
      ],
      "last3": [
       53127.74192361312,
       53127.79652410768,
       53126.62929112615
      ],
      "min": 1415.59121819522,
      "max": 53127.79652410768
     },
     "log_Z_M": {
      "__abridged__": "161 floats",
      "first3": [
       -89.39141111179806,
       -84.77861596619148,
       -80.41805077613644
      ],
      "last3": [
       4.91122279251759,
       4.917949203254258,
       4.924312327078054
      ],
      "min": -89.39141111179806,
      "max": 4.924312327078054
     },
     "min_ess": 1415.59121819522
    },
    "occam_true": {
     "derived_from_raw_with": "bistar_gp.laplace_evidence._log_reference_volume",
     "ess": {
      "__abridged__": "161 floats",
      "first3": [
       1824.7564335069862,
       1910.4691969903647,
       1990.8046438407628
      ],
      "last3": [
       53127.74192361312,
       53127.79652410768,
       53126.62929112615
      ],
      "min": 1415.59121819522,
      "max": 53127.79652410768
     },
     "log_Z_M": {
      "__abridged__": "161 floats",
      "first3": [
       -94.42595929308742,
       -89.81316414748083,
       -85.45259895742579
      ],
      "last3": [
       -0.12332538877176447,
       -0.11659897803509622,
       -0.11023585421130022
      ],
      "min": -94.42595929308742,
      "max": -0.11023585421130022
     },
     "min_ess": 1415.59121819522
    }
   }
  }
 },
 "nested_pairs": {
  "Linear_within_Sin+Linear": {
   "Z_M_ordering_by_seed": {
    "0": {
     "occam_false": {
      "crossings": [],
      "delta_at_tau_max": 4.974175737568331,
      "delta_at_tau_min": 68.64947785903723,
      "delta_definition": "log Z_M(encompassing) - log Z_M(restricted)",
      "delta_log_Z": {
       "__abridged__": "161 floats",
       "first3": [
        68.64947785903723,
        64.5280482238239,
        60.64220700613285
       ],
       "last3": [
        4.966732832421187,
        4.970554639230697,
        4.974175737568331
       ],
       "min": 2.970459017312912,
       "max": 68.64947785903723
      },
      "minimum_absolute_delta_grid_point": {
       "delta_log_Z": 2.970459017312912,
       "tau": 0.7498942093324559
      },
      "winner_at_tau_max": "encompassing",
      "winner_at_tau_min": "encompassing"
     },
     "occam_true": {
      "crossings": [
       {
        "delta_log_Z_bracket": [
         0.2842881798814876,
         -0.06941931223643749
        ],
        "lower_grid_index": 38,
        "tau_bracket": [
         0.2818382931264454,
         0.298538261891796
        ],
        "tau_log_interpolated": 0.29518443393426885,
        "winner_above": "restricted",
        "winner_below": "encompassing"
       }
      ],
      "delta_at_tau_max": -0.0623744463916962,
      "delta_at_tau_min": 63.6129276750772,
      "delta_definition": "log Z_M(encompassing) - log Z_M(restricted)",
      "delta_log_Z": {
       "__abridged__": "161 floats",
       "first3": [
        63.6129276750772,
        59.49149803986388,
        55.60565682217282
       ],
       "last3": [
        -0.06981735153884028,
        -0.06599554472933011,
        -0.0623744463916962
       ],
       "min": -2.066091166647116,
       "max": 63.6129276750772
      },
      "minimum_absolute_delta_grid_point": {
       "delta_log_Z": -0.0623744463916962,
       "tau": 316.22776601683796
      },
      "winner_at_tau_max": "restricted",
      "winner_at_tau_min": "encompassing"
     }
    },
    "1": {
     "occam_false": {
      "crossings": [],
      "delta_at_tau_max": 4.97979509952475,
      "delta_at_tau_min": 68.64595031489702,
      "delta_definition": "log Z_M(encompassing) - log Z_M(restricted)",
      "delta_log_Z": {
       "__abridged__": "161 floats",
       "first3": [
        68.64595031489702,
        64.52405754163739,
        60.63774382837176
       ],
       "last3": [
        4.972905300352151,
        4.976446289065056,
        4.97979509952475
       ],
       "min": 3.054344169287255,
       "max": 68.64595031489702
      },
      "minimum_absolute_delta_grid_point": {
       "delta_log_Z": 3.054344169287255,
       "tau": 0.7943282347242817
      },
      "winner_at_tau_max": "encompassing",
      "winner_at_tau_min": "encompassing"
     },
     "occam_true": {
      "crossings": [
       {
        "delta_log_Z_bracket": [
         0.28251751298838457,
         -0.06815880433467925
        ],
        "lower_grid_index": 38,
        "tau_bracket": [
         0.2818382931264454,
         0.298538261891796
        ],
        "tau_log_interpolated": 0.2952166878296174,
        "winner_above": "restricted",
        "winner_below": "encompassing"
       }
      ],
      "delta_at_tau_max": -0.05675508443527644,
      "delta_at_tau_min": 63.60940013093698,
      "delta_definition": "log Z_M(encompassing) - log Z_M(restricted)",
      "delta_log_Z": {
       "__abridged__": "161 floats",
       "first3": [
        63.60940013093698,
        59.48750735767735,
        55.60119364441173
       ],
       "last3": [
        -0.06364488360787579,
        -0.060103894894971255,
        -0.05675508443527644
       ],
       "min": -1.982206014672773,
       "max": 63.60940013093698
      },
      "minimum_absolute_delta_grid_point": {
       "delta_log_Z": -0.05675508443527644,
       "tau": 316.22776601683796
      },
      "winner_at_tau_max": "restricted",
      "winner_at_tau_min": "encompassing"
     }
    },
    "2": {
     "occam_false": {
      "crossings": [],
      "delta_at_tau_max": 4.975782619341558,
      "delta_at_tau_min": 68.64737042265173,
      "delta_definition": "log Z_M(encompassing) - log Z_M(restricted)",
      "delta_log_Z": {
       "__abridged__": "161 floats",
       "first3": [
        68.64737042265173,
        64.52432405370504,
        60.636820766399104
       ],
       "last3": [
        4.968525475225462,
        4.972252964452197,
        4.975782619341558
       ],
       "min": 2.98451886945689,
       "max": 68.64737042265173
      },
      "minimum_absolute_delta_grid_point": {
       "delta_log_Z": 2.98451886945689,
       "tau": 0.7943282347242817
      },
      "winner_at_tau_max": "encompassing",
      "winner_at_tau_min": "encompassing"
     },
     "occam_true": {
      "crossings": [
       {
        "delta_log_Z_bracket": [
         0.29978377333145545,
         -0.05285509528852472
        ],
        "lower_grid_index": 38,
        "tau_bracket": [
         0.2818382931264454,
         0.298538261891796
        ],
        "tau_log_interpolated": 0.2959735406484291,
        "winner_above": "restricted",
        "winner_below": "encompassing"
       }
      ],
      "delta_at_tau_max": -0.06076756461846866,
      "delta_at_tau_min": 63.6108202386917,
      "delta_definition": "log Z_M(encompassing) - log Z_M(restricted)",
      "delta_log_Z": {
       "__abridged__": "161 floats",
       "first3": [
        63.6108202386917,
        59.487773869745006,
        55.60027058243907
       ],
       "last3": [
        -0.06802470873456468,
        -0.06429721950782952,
        -0.06076756461846866
       ],
       "min": -2.0520313145031377,
       "max": 63.6108202386917
      },
      "minimum_absolute_delta_grid_point": {
       "delta_log_Z": -0.05285509528852472,
       "tau": 0.298538261891796
      },
      "winner_at_tau_max": "restricted",
      "winner_at_tau_min": "encompassing"
     }
    }
   },
   "crossing_uncertainty": {
    "occam_false": null,
    "occam_true": {
     "ess_implied_one_se_common_mode_shift_seed_0": {
      "delta_log_Z_se_at_nominal_bracket": [
       0.012119399787001713,
       0.012410065425652003
      ],
      "delta_log_Z_swing_across_nominal_bracket": 0.35370749211792507,
      "method": "shift the seed-0 delta-log-Z curve by plus or minus sqrt(1/ESS_encompassing + 1/ESS_restricted) at each grid point",
      "shifted_crossing_grid_brackets": [
       [
        0.2818382931264454,
        0.298538261891796
       ],
       [
        0.2818382931264454,
        0.298538261891796
       ]
      ],
      "tau_interval_log_interpolated": [
       0.2945920747486698,
       0.2957789615291232
      ]
     },
     "grid_bracket_seed_0": [
      0.2818382931264454,
      0.298538261891796
     ],
     "per_seed_crossings": {
      "0": [
       {
        "delta_log_Z_bracket": [
         0.2842881798814876,
         -0.06941931223643749
        ],
        "lower_grid_index": 38,
        "tau_bracket": [
         0.2818382931264454,
         0.298538261891796
        ],
        "tau_log_interpolated": 0.29518443393426885,
        "winner_above": "restricted",
        "winner_below": "encompassing"
       }
      ],
      "1": [
       {
        "delta_log_Z_bracket": [
         0.28251751298838457,
         -0.06815880433467925
        ],
        "lower_grid_index": 38,
        "tau_bracket": [
         0.2818382931264454,
         0.298538261891796
        ],
        "tau_log_interpolated": 0.2952166878296174,
        "winner_above": "restricted",
        "winner_below": "encompassing"
       }
      ],
      "2": [
       {
        "delta_log_Z_bracket": [
         0.29978377333145545,
         -0.05285509528852472
        ],
        "lower_grid_index": 38,
        "tau_bracket": [
         0.2818382931264454,
         0.298538261891796
        ],
        "tau_log_interpolated": 0.2959735406484291,
        "winner_above": "restricted",
        "winner_below": "encompassing"
       }
      ]
     },
     "per_seed_interpolant_spread": [
      0.29518443393426885,
      0.2959735406484291
     ],
     "resolution_rule": "crossing resolution is set by the larger of grid spacing and Monte Carlo error"
    }
   },
   "embedded_restricted_optimum": {
    "Gbar": 2.4247743701716202,
    "absolute_Gbar_error": 0.0,
    "passed": true,
    "phi": {
     "A": 0.0,
     "b": 0.27577151111106163,
     "c": 0.004158945541476323,
     "omega": 1.0,
     "phi": 0.0
    },
    "tolerance": 1e-10
   },
   "encompassing": {
    "min_Gbar": 0.04551678343894516,
    "n_multistarts": 38,
    "phi_min": {
     "A": 1.0224846975427644,
     "b": 0.25015173054273654,
     "c": -0.0034811798627464555,
     "omega": 0.9986522565255535,
     "phi": 0.07582150264521711
    }
   },
   "encompassing_model": "Sin+Linear",
   "inequality": "min_\u03c6 \u1e20(encompassing) \u2264 min_\u03c6 \u1e20(restricted)",
   "inequality_holds": true,
   "margin_restricted_minus_encompassing": 2.379257586732675,
   "minimum_is_tau_independent": true,
   "restricted": {
    "min_Gbar": 2.4247743701716202,
    "n_multistarts": 18,
    "phi_min": {
     "a": 0.27577151111106163,
     "b": 0.004158945541476323
    }
   },
   "restricted_model": "Linear",
   "restriction": "A=0; encompassing b and c equal restricted a and b",
   "tolerance": 1e-08,
   "verified_for_tau_count": 161
  },
  "Sinusoidal_within_Sin+Linear": {
   "Z_M_ordering_by_seed": {
    "0": {
     "occam_false": {
      "crossings": [],
      "delta_at_tau_max": 3.0802182019043016,
      "delta_at_tau_min": 75.78542470267796,
      "delta_definition": "log Z_M(encompassing) - log Z_M(restricted)",
      "delta_log_Z": {
       "__abridged__": "161 floats",
       "first3": [
        75.78542470267796,
        71.3975118378169,
        67.2574318299047
       ],
       "last3": [
        3.0258392843590514,
        3.053411048621129,
        3.0802182019043016
       ],
       "min": 1.2938117958184012,
       "max": 75.78542470267796
      },
      "minimum_absolute_delta_grid_point": {
       "delta_log_Z": 1.2938117958184012,
       "tau": 11.88502227437019
      },
      "winner_at_tau_max": "encompassing",
      "winner_at_tau_min": "encompassing"
     },
     "occam_true": {
      "crossings": [
       {
        "delta_log_Z_bracket": [
         0.03435390158246321,
         -0.005522325686383667
        ],
        "lower_grid_index": 66,
        "tau_bracket": [
         1.4125375446227548,
         1.4962356560944337
        ],
        "tau_log_interpolated": 1.4843551834764874,
        "winner_above": "restricted",
        "winner_below": "encompassing"
       }
      ],
      "delta_at_tau_max": -0.6106632548803077,
      "delta_at_tau_min": 72.09454324589335,
      "delta_definition": "log Z_M(encompassing) - log Z_M(restricted)",
      "delta_log_Z": {
       "__abridged__": "161 floats",
       "first3": [
        72.09454324589335,
        67.70663038103228,
        63.566550373120094
       ],
       "last3": [
        -0.665042172425558,
        -0.6374704081634803,
        -0.6106632548803077
       ],
       "min": -2.397069660966208,
       "max": 72.09454324589335
      },
      "minimum_absolute_delta_grid_point": {
       "delta_log_Z": -0.005522325686383667,
       "tau": 1.4962356560944337
      },
      "winner_at_tau_max": "restricted",
      "winner_at_tau_min": "encompassing"
     }
    },
    "1": {
     "occam_false": {
      "crossings": [],
      "delta_at_tau_max": 3.0829808423224776,
      "delta_at_tau_min": 75.73644700620949,
      "delta_definition": "log Z_M(encompassing) - log Z_M(restricted)",
      "delta_log_Z": {
       "__abridged__": "161 floats",
       "first3": [
        75.73644700620949,
        71.34678862837559,
        67.2051485349822
       ],
       "last3": [
        3.0287444121735376,
        3.0562440328082054,
        3.0829808423224776
       ],
       "min": 1.320623853647307,
       "max": 75.73644700620949
      },
      "minimum_absolute_delta_grid_point": {
       "delta_log_Z": 1.320623853647307,
       "tau": 11.88502227437019
      },
      "winner_at_tau_max": "encompassing",
      "winner_at_tau_min": "encompassing"
     },
     "occam_true": {
      "crossings": [
       {
        "delta_log_Z_bracket": [
         0.05111190075568217,
         -0.00022134678070528935
        ],
        "lower_grid_index": 67,
        "tau_bracket": [
         1.4962356560944337,
         1.584893192461114
        ],
        "tau_log_interpolated": 1.584499845074845,
        "winner_above": "restricted",
        "winner_below": "encompassing"
       }
      ],
      "delta_at_tau_max": -0.6079006144621317,
      "delta_at_tau_min": 72.04556554942488,
      "delta_definition": "log Z_M(encompassing) - log Z_M(restricted)",
      "delta_log_Z": {
       "__abridged__": "161 floats",
       "first3": [
        72.04556554942488,
        67.65590717159097,
        63.514267078197584
       ],
       "last3": [
        -0.6621370446110717,
        -0.6346374239764039,
        -0.6079006144621317
       ],
       "min": -2.3702576031373024,
       "max": 72.04556554942488
      },
      "minimum_absolute_delta_grid_point": {
       "delta_log_Z": -0.00022134678070528935,
       "tau": 1.584893192461114
      },
      "winner_at_tau_max": "restricted",
      "winner_at_tau_min": "encompassing"
     }
    },
    "2": {
     "occam_false": {
      "crossings": [],
      "delta_at_tau_max": 3.0841331711120894,
      "delta_at_tau_min": 75.71547962959943,
      "delta_definition": "log Z_M(encompassing) - log Z_M(restricted)",
      "delta_log_Z": {
       "__abridged__": "161 floats",
       "first3": [
        75.71547962959943,
        71.326526794604,
        67.18538752169809
       ],
       "last3": [
        3.0296661862688303,
        3.0572849396500494,
        3.0841331711120894
       ],
       "min": 1.3158048996919511,
       "max": 75.71547962959943
      },
      "minimum_absolute_delta_grid_point": {
       "delta_log_Z": 1.3158048996919511,
       "tau": 11.88502227437019
      },
      "winner_at_tau_max": "encompassing",
      "winner_at_tau_min": "encompassing"
     },
     "occam_true": {
      "crossings": [
       {
        "delta_log_Z_bracket": [
         0.020446543072374368,
         -0.012515315520140291
        ],
        "lower_grid_index": 65,
        "tau_bracket": [
         1.333521432163324,
         1.4125375446227548
        ],
        "tau_log_interpolated": 1.3819990012964956,
        "winner_above": "restricted",
        "winner_below": "encompassing"
       }
      ],
      "delta_at_tau_max": -0.6067482856725199,
      "delta_at_tau_min": 72.02459817281482,
      "delta_definition": "log Z_M(encompassing) - log Z_M(restricted)",
      "delta_log_Z": {
       "__abridged__": "161 floats",
       "first3": [
        72.02459817281482,
        67.6356453378194,
        63.49450606491347
       ],
       "last3": [
        -0.661215270515779,
        -0.6335965171345599,
        -0.6067482856725199
       ],
       "min": -2.375076557092658,
       "max": 72.02459817281482
      },
      "minimum_absolute_delta_grid_point": {
       "delta_log_Z": -0.012515315520140291,
       "tau": 1.4125375446227548
      },
      "winner_at_tau_max": "restricted",
      "winner_at_tau_min": "encompassing"
     }
    }
   },
   "crossing_uncertainty": {
    "occam_false": null,
    "occam_true": {
     "ess_implied_one_se_common_mode_shift_seed_0": {
      "delta_log_Z_se_at_nominal_bracket": [
       0.042671021625809956,
       0.04204726702648715
      ],
      "delta_log_Z_swing_across_nominal_bracket": 0.039876227268846876,
      "method": "shift the seed-0 delta-log-Z curve by plus or minus sqrt(1/ESS_encompassing + 1/ESS_restricted) at each grid point",
      "shifted_crossing_grid_brackets": [
       [
        1.333521432163324,
        1.4125375446227548
       ],
       [
        1.4962356560944337,
        1.584893192461114
       ]
      ],
      "tau_interval_log_interpolated": [
       1.3924309147649392,
       1.5629209897331997
      ]
     },
     "grid_bracket_seed_0": [
      1.4125375446227548,
      1.4962356560944337
     ],
     "per_seed_crossings": {
      "0": [
       {
        "delta_log_Z_bracket": [
         0.03435390158246321,
         -0.005522325686383667
        ],
        "lower_grid_index": 66,
        "tau_bracket": [
         1.4125375446227548,
         1.4962356560944337
        ],
        "tau_log_interpolated": 1.4843551834764874,
        "winner_above": "restricted",
        "winner_below": "encompassing"
       }
      ],
      "1": [
       {
        "delta_log_Z_bracket": [
         0.05111190075568217,
         -0.00022134678070528935
        ],
        "lower_grid_index": 67,
        "tau_bracket": [
         1.4962356560944337,
         1.584893192461114
        ],
        "tau_log_interpolated": 1.584499845074845,
        "winner_above": "restricted",
        "winner_below": "encompassing"
       }
      ],
      "2": [
       {
        "delta_log_Z_bracket": [
         0.020446543072374368,
         -0.012515315520140291
        ],
        "lower_grid_index": 65,
        "tau_bracket": [
         1.333521432163324,
         1.4125375446227548
        ],
        "tau_log_interpolated": 1.3819990012964956,
        "winner_above": "restricted",
        "winner_below": "encompassing"
       }
      ]
     },
     "per_seed_interpolant_spread": [
      1.3819990012964956,
      1.584499845074845
     ],
     "resolution_rule": "crossing resolution is set by the larger of grid spacing and Monte Carlo error"
    }
   },
   "embedded_restricted_optimum": {
    "Gbar": 2.546229648543252,
    "absolute_Gbar_error": 0.0,
    "passed": true,
    "phi": {
     "A": 3.0262248187297827,
     "b": 0.0,
     "c": 0.0,
     "omega": 0.1,
     "phi": 0.003147503569407698
    },
    "tolerance": 1e-10
   },
   "encompassing": {
    "min_Gbar": 0.04551678343894516,
    "n_multistarts": 38,
    "phi_min": {
     "A": 1.0224846975427644,
     "b": 0.25015173054273654,
     "c": -0.0034811798627464555,
     "omega": 0.9986522565255535,
     "phi": 0.07582150264521711
    }
   },
   "encompassing_model": "Sin+Linear",
   "inequality": "min_\u03c6 \u1e20(encompassing) \u2264 min_\u03c6 \u1e20(restricted)",
   "inequality_holds": true,
   "margin_restricted_minus_encompassing": 2.5007128651043065,
   "minimum_is_tau_independent": true,
   "restricted": {
    "min_Gbar": 2.546229648543252,
    "n_multistarts": 30,
    "phi_min": {
     "A": 3.0262248187297827,
     "omega": 0.1,
     "phi": 0.003147503569407698
    }
   },
   "restricted_model": "Sinusoidal",
   "restriction": "b=c=0",
   "tolerance": 1e-08,
   "verified_for_tau_count": 161
  }
 },
 "provenance": {
  "Z_M_estimator": "bistar_gp.laplace_evidence.is_log_Z_Mx",
  "data_seed": 42,
  "gp_config": "informative",
  "gp_method": "map",
  "gp_predictives_retained": 1,
  "is_calls_per_model_per_seed": 1,
  "is_seeds": [
   0,
   1,
   2
  ],
  "metric": "pw_kl_vcal",
  "n": 50,
  "n_draws_requested": 150,
  "n_is": 100000,
  "n_perturb": 5,
  "occam_normalization": "bistar_gp.laplace_evidence._log_reference_volume",
  "optimizer": "bistar_gp.laplace_evidence._multistart_G_optima",
  "spaces": {
   "encompassing": "canonical Sin+Linear bounds with the amplitude lower bound extended from 0.01 to 0 for exact nesting",
   "restricted": "bistar_viz/scripts/_viz_spaces.py:canonical_spaces"
  },
  "start_sets": "restricted optima embedded at the exact boundaries for the min-\u1e20 optimization; interior perturbed starts plus the best encompassing optimum for IS",
  "tau_grid": {
   "definition": "numpy.logspace(-1.5, 2.5, 161)",
   "values": {
    "__abridged__": "161 floats",
    "first3": [
     0.03162277660168379,
     0.03349654391578276,
     0.03548133892335755
    ],
    "last3": [
     281.8382931264455,
     298.538261891796,
     316.22776601683796
    ],
    "min": 0.03162277660168379,
    "max": 316.22776601683796
   }
  },
  "x_eval_count": 80,
  "x_eval_range": [
   -10.0,
   10.0
  ]
 },
 "schema_version": 2,
 "tolerances": {
  "exact_embedding_Gbar": 1e-10,
  "min_Gbar_inequality": 1e-08
 },
 "verdict": {
  "all_min_Gbar_inequalities_hold": true,
  "scope": "machinery check and margin/crossing quantification on one n=50 informative-config, MAP-based averaged GP",
  "statement": "Exact embeddings and the mean-only divergence make both min-\u1e20 inequalities analytic consequences of box containment. E6 confirms that the implementation reproduces those consequences and quantifies the margins; the finite-\u03c4 Z_M crossings provide the remaining empirical content."
 }
}