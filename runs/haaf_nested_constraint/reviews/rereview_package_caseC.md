RE-REVIEW ROUND (HANDOFF §4 rule 4) — Case C fix pass 1, changed hunks only.
Branch paper/case-c-haaf; fix commit 0ce03ba on top of reviewed tip 87da084.
Task: for EACH of YOUR OWN previously raised findings (per the dispatch note), judge from
the changed hunks whether the fix resolves it. Output per finding: 'REREVIEW-<ID>: RESOLVED'
or 'REREVIEW-<ID>: NOT-RESOLVED' plus 2-4 evidence lines. Additionally report any NEW defect
INTRODUCED BY the changed hunks (hunks only; no re-litigation of unchanged code; no scope
expansion). Round-1 record: runs/haaf_nested_constraint/reviews/VERDICTS.md.
NOTE: the implementer corrected one reviewer misattribution during FIX-2 (the ~6.3e10
kl_forward value belongs to a separate equal-candidate row, not the differing row, whose
values are 500.142 vs 488.982; underflow at tau=0.1/0.3, aggregate-resolution loss at
larger tau) — results.json now records both rows and per-tau status; judge the corrected
documentation on its merits.

=== IMPLEMENTER FIX REPORT ===
Implemented all ten fixes within the authorized scope.

1. **FIX-1** — Files: [requirements.txt](/Users/sc8918/Documents/GitHub/bistar_gp_c/requirements.txt:8), [pyproject.toml](/Users/sc8918/Documents/GitHub/bistar_gp_c/pyproject.toml:19). Added exactly `arviz>=0.17` to both manifests.

2. **FIX-2** — Files: [experiment](/Users/sc8918/Documents/GitHub/bistar_gp_c/experiments/haaf_nested_constraint.py:612), [README](/Users/sc8918/Documents/GitHub/bistar_gp_c/runs/haaf_nested_constraint/README.md:59), [results.json](/Users/sc8918/Documents/GitHub/bistar_gp_c/runs/haaf_nested_constraint/results.json:305), [section](/Users/sc8918/Documents/GitHub/bistar_gp_c/docs/paper-sie-jmp/05-case-C-nested-constraints.md:69). Removed `kl_forward` entirely from the main section and documented pooled degeneracy, expected-posterior sign reversal, and evaluation at primary-metric optima in the appendix note.

3. **FIX-3** — Files: experiment, README, section, [D63](/Users/sc8918/Documents/GitHub/bistar_gp_c/Notes/DECISIONS.md:5905), results.json. Documented four shared base starts, asymmetric restricted warm starts, cross-seeded candidate pools, and their optimizer-noise-control purpose.

4. **FIX-4** — Files: section, README, D63, results.json. Replaced the directional LOO reading with the narrowed null-to-inconclusive interpretation and generated the local Gaussian diagnostic.

   Corrected section sentences verbatim:

   > The constrained-minus-free `elpd_loo` difference equals 0.413 with a paired SE of 0.256, computed with `ddof=0` to match the ArviZ convention.[^2] The difference is directionally inconclusive: its magnitude is smaller than twice its paired SE, the constrained estimate carries a Pareto-$k$ warning because one observation exceeds the 0.697 good-$k$ threshold, and the paired SE covers data-level pointwise variability only, without MCMC error. Haaf, Klaassen, and Rouder report this kind of null-to-inconclusive LOO difference as the failure mode for a satisfied nested constraint.[^1]

   > The two slope priors coincide up to normalization on $b>0$, so LOO has no structural contrast wherever negative-slope posterior mass is negligible. The artifact's own full-data local Gaussian diagnostic gives posterior SD 0.0129506 for $b$, places the boundary 19.4028 SDs away, and gives a Gaussian left-tail probability of $3.65\times10^{-84}$. This local approximation supports the reading that the constraint binds only where the locally approximated posterior carries negligible mass. It does not prove that the global posteriors or leave-one-out fold posteriors are exactly identical, and it does not establish that the entire observed gap comes from estimator noise.[^2]

5. **FIX-5** — Files: section, README, D63. Table 5.1 now reports `0.500` throughout; prose reports a gap below \(10^{-5}\), attributes it to one SIR draw, and treats its temperature monotonicity as deterministic.

6. **FIX-6** — Files: experiment, README, section, D63, results.json. Reframed nesting as protocol set inclusion and retained the runtime gates as machinery-regression guards.

7. **FIX-7** — Files: README, section, D63. Stated before Table 5.1 that the restricted probability cannot exceed the free probability; only gap magnitude remains empirical.

8. **FIX-8** — Files: experiment, README, section, D63, results.json. Both sampler blocks now record `init_strategy` with `init_to_value` and all six initial values. The aliases near 4.939 and 6.999 and the within-mode-only interpretation of R-hat/ESS are disclosed.

9. **FIX-9** — Files: experiment, README, section, D63, results.json. Paired SE now uses `ddof=0`: full precision **0.25588686781820247**, printed as **0.256**. `psis_loo.pairwise` records `se_ddof`, formula, and ArviZ convention.

10. **FIX-10** — Files: experiment, results.json, section. `data.x_eval` now records `n: 60` and range `[-11.0, 11.0]`.

Final canonical rerun: exit code **0**, wall time **208.15 seconds**. JSON assertions and stale-phrase/dependency checks passed. Expected GP-jitter and Pareto-\(k\) warnings were emitted.

One evidence-driven deviation: FIX-2 attributed the approximately \(6.3\times10^{10}\) value to the sole differing row and claimed underflow at every temperature. Regeneration shows the differing row has values 500.142 and 488.982; the \(5.92\times10^{10}\) maximum occurs on a separate equal-candidate row. Underflow occurs at \(\tau=0.1,0.3\), while later values fall below aggregate float64 resolution. `results.json` records both rows and the per-temperature underflow status rather than repeating the inaccurate attribution.

Open driver questions: none. `pyro-ppl>=1.8` was already declared in both manifests. No network or git operations were performed.
=== FIX DIFF STAT ===
 Notes/DECISIONS.md                                 |  77 ++++--
 docs/paper-sie-jmp/05-case-C-nested-constraints.md | 104 ++++++---
 experiments/haaf_nested_constraint.py              | 258 +++++++++++++++++++--
 pyproject.toml                                     |   1 +
 requirements.txt                                   |   1 +
 runs/haaf_nested_constraint/README.md              |  68 +++++-
 runs/haaf_nested_constraint/results.json           |  91 +++++++-
 7 files changed, 508 insertions(+), 92 deletions(-)

=== FIX DIFF (full) ===
diff --git a/Notes/DECISIONS.md b/Notes/DECISIONS.md
index 62b6c7d..88b990f 100644
--- a/Notes/DECISIONS.md
+++ b/Notes/DECISIONS.md
@@ -5733,11 +5733,16 @@ directional claim could not determine how the comparison came out.
 `python experiments/haaf_nested_constraint.py` uses
 `generate_toy_data()` defaults ($N=20$, data seed 42, true $b=0.25$, noise
 standard deviation 0.5). Both candidates call
-`bistar_gp.candidates.CandidateModel._fit_mle`; they share all starts and
-bounds except the lower slope bound, unrestricted for the free candidate and
-zero for the restricted candidate. A common log-sigma bound of [-10, 5]
-prevents exploratory underflow. Each shared $\psi$ receives a fresh fit, so the
-per-draw free-slope sign can account for the BMS* gap.
+`bistar_gp.candidates.CandidateModel._fit_mle`; they receive four shared base
+starts and share all bounds except the lower slope bound, unrestricted for the
+free candidate and zero for the restricted candidate. The restricted fit also
+receives the free solutions, clipped at $b=0$ when necessary, and each
+candidate's selection pool includes the other candidate's feasible vectors.
+This deliberate asymmetric warm start and candidate pooling forces exact
+equality at shared optima instead of turning optimizer noise into a gap. A
+common log-sigma bound of [-10, 5] prevents exploratory underflow. Each shared
+$\psi$ receives a fresh fit, so the per-draw free-slope sign can account for
+the BMS* gap.
 
 The BMS* arm imports `prior_sensitivity_study.py`, loads the local
 `toy_elicited` prior-IS caches for seeds 0, 1, and 2, and calls the validated
@@ -5753,11 +5758,13 @@ $c\sim$ Normal(0, 5), and $\sigma\sim$ HalfNormal(2); the free candidate uses
 $b\sim$ Normal(0, 5), while the restricted candidate uses $b\sim$
 HalfNormal(5). Pyro NUTS runs sequential chains with seeds 20260811 and
 20260812, each with 1,000 warmup iterations and 1,000 retained draws, target
-acceptance probability 0.90, and maximum tree depth 8. ArviZ computes
-pointwise PSIS-LOO. Structural G tolerances equal $2\times10^{-7}$ for both
-interior equality and one-sided nesting; cross-machine artifact tolerances
-equal 0.005 for probabilities and the slope fraction, 0.25 elpd for each LOO
-estimate, and 0.25 elpd for the paired difference.
+acceptance probability 0.90, and maximum tree depth 8. Every chain initializes
+deterministically at the common observed-data MLE through `init_to_value`.
+ArviZ computes pointwise PSIS-LOO. The $2\times10^{-7}$ structural G gates
+guard machinery regressions rather than empirically testing nesting;
+cross-machine artifact tolerances equal 0.005 for probabilities and the slope
+fraction, 0.25 elpd for each LOO estimate, and 0.25 elpd for the paired
+difference.
 
 **Alternatives considered:** Drawing new data was rejected because it would
 break the binding between the $N=20$ observations, their data-elicited GP
@@ -5774,25 +5781,45 @@ because the table and slope-sign count contain the full comparison.
 **Result:** The pooled prior-IS ESS equals 4,464.53, and the 1,000 SIR rows
 contain 883 unique cached draws. The free best-fit slope falls below zero on
 1/1,000 rows, a fraction of 0.001. The remaining 999 rows have identical
-primary G values for both candidates to the recorded tolerance. On the one
-negative-slope row, restricted minus free G equals 0.000360, so the one-sided
-nesting check passes with zero violations.
-
-At $\tau=1$, pooled BMS* assigns 0.500000112 to the free candidate and
-0.499999888 to the restricted candidate; expected-posterior aggregation
-assigns 0.500000090 and 0.499999910. The restricted pooled probability ranges
-from 0.499996100 at $\tau=0.1$ to 0.499999991 at $\tau=10$; its
-expected-posterior probability ranges from 0.499999100 to 0.499999991. Thus
-BMS* reports an effective tie throughout the sweep.
+primary G values for both candidates because the same feasible vector is
+re-evaluated. On the one negative-slope row, restricted minus free G equals
+0.000360. The one-sided ordering follows by set inclusion; the runtime gates
+record zero machinery-regression violations.
+
+At $\tau=1$, both aggregation conventions assign 0.500 to each candidate.
+The free-minus-restricted probability gap remains smaller than $10^{-5}$ at
+every $\tau$ under both conventions and comes entirely from the single
+negative-slope draw. Its monotone contraction with $\tau$ follows
+deterministically from Boltzmann aggregation, not from a measured temperature
+effect. The restricted candidate cannot exceed the free candidate because the
+restricted region is a subset; only the gap magnitude is empirical.
 
 PSIS-LOO reports `elpd_loo=-13.074` (SE 3.458, `p_loo=5.343`) for the free
 candidate and `elpd_loo=-12.661` (SE 3.594, `p_loo=5.169`) for the restricted
 candidate. The restricted-minus-free difference equals 0.413 with paired SE
-0.263. Both NUTS fits have zero divergences; maximum rank-normalized
+0.256, computed with `ddof=0` to match the ArviZ convention. Both NUTS fits
+have zero divergences; maximum rank-normalized
 $\widehat R$ equals 1.003 free and 1.002 restricted, and minimum bulk ESS
 equals 1,004 and 1,638. The free maximum Pareto $k$ equals 0.564 with no
 warning. The restricted maximum equals 0.718, and ArviZ flags one observation
-above its 0.697 good-$k$ threshold. The direction favors the restriction under
-LOO but requires that qualification. Case C therefore records a split null:
-LOO gives a small, diagnostically qualified advantage to the restricted
-candidate, while BMS* gives neither candidate a meaningful advantage.
+above its 0.697 good-$k$ threshold. Because both candidates' chains initialize
+at the same MLE and sampled-grid aliases occur near $\omega=4.939$ and 6.999,
+the $\widehat R$ and ESS values support within-mode convergence only.
+
+The difference is directionally inconclusive: its magnitude is smaller than
+twice its paired SE, the constrained estimate carries a Pareto-$k$ warning,
+and the paired SE covers data-level pointwise variability only, without MCMC
+error. Haaf, Klaassen, and Rouder report this kind of null-to-inconclusive LOO
+difference as the failure mode for a satisfied nested constraint.
+
+The two slope priors coincide up to normalization on $b>0$, so LOO has no
+structural contrast wherever negative-slope posterior mass is negligible. The
+artifact's own full-data local Gaussian diagnostic gives posterior SD
+0.0129506 for $b$, places the boundary 19.4028 SDs away, and gives a Gaussian
+left-tail probability of $3.65\times10^{-84}$. This local approximation
+supports the reading that the constraint binds only where the locally
+approximated posterior carries negligible mass. It does not prove that the
+global posteriors or leave-one-out fold posteriors are exactly identical, and
+it does not establish that the entire observed gap comes from estimator
+noise. Case C therefore records a null-to-inconclusive LOO comparison and an
+effective BMS* tie without a directional claim.
diff --git a/docs/paper-sie-jmp/05-case-C-nested-constraints.md b/docs/paper-sie-jmp/05-case-C-nested-constraints.md
index 7cb9001..14ab0e6 100644
--- a/docs/paper-sie-jmp/05-case-C-nested-constraints.md
+++ b/docs/paper-sie-jmp/05-case-C-nested-constraints.md
@@ -19,9 +19,13 @@ $$
 
 with unrestricted $b$. The restricted candidate $M_r \subset M_e$ uses the
 same expression and imposes $b\geq 0$. Both candidates call the same bounded
-MLE routine, use the same starts, and share every bound except the lower bound
-on $b$. The frozen $N=20$ data use seed 42 and the true slope $b=0.25$, so the
-restriction holds in truth.[^2]
+MLE routine, receive four shared base starts, and share every bound except the
+lower bound on $b$. The restricted fit additionally receives the free
+solutions, clipped at $b=0$ when necessary, and each candidate's selection
+pool includes the other candidate's feasible vectors. This deliberate
+asymmetry forces exact equality at shared optima instead of turning optimizer
+noise into a gap. The frozen $N=20$ data use seed 42 and the true slope
+$b=0.25$, so the restriction holds in truth.[^2]
 
 ## 5.1 BMS* comparison
 
@@ -34,11 +38,21 @@ Thus the calculation supplies candidate instances from a shared $\psi$ rather
 than introducing candidate-parameter priors. Such priors contribute only to
 the separate LOO comparison below.[^2]
 
-The nesting check passed at a $2\times10^{-7}$ absolute tolerance. On 999
-predictives, the free optimum had $b\geq0$, and both candidates produced
-identical primary $G$ values. One predictive had a negative free optimum, for
-a fraction of 0.001. On that row, restricted minus free $G$ equaled
-0.000360, so the required one-sided ordering also held.[^2]
+The nesting relation fixes the primary-metric ordering as an identity of the
+protocol: $M_r\subset M_e$ implies
+$\min_{\theta\in M_r}G\geq\min_{\theta\in M_e}G$ for every predictive. The
+cross-seeded candidate pools enforce this set inclusion numerically, while
+re-evaluation of the same feasible vector gives exact equality at a shared
+optimum. The $2\times10^{-7}$ runtime gates guard against machinery
+regressions; they do not provide an empirical nesting test. On 999
+predictives, the free optimum had $b\geq0$ and the primary $G$ gap equaled
+exactly zero. One predictive had a negative free optimum, for a fraction of
+0.001, and restricted minus free $G$ equaled 0.000360 on that row.[^2]
+
+This same set inclusion fixes the probability direction before Table 5.1.
+The restricted candidate can never exceed the free candidate under either
+aggregation at any $\tau$; only the gap's magnitude depends on the sampled
+predictives.[^2]
 
 Table 5.1 reports both aggregation conventions across the preregistered
 temperature grid. Each pair normalizes over only the free and restricted
@@ -46,20 +60,21 @@ candidates.[^2]
 
 | $\tau$ | pooled free | pooled restricted | expected-posterior free | expected-posterior restricted |
 |---:|---:|---:|---:|---:|
-| 0.1 | 0.500003900 | 0.499996100 | 0.500000900 | 0.499999100 |
-| 0.3 | 0.500000570 | 0.499999430 | 0.500000300 | 0.499999700 |
-| 1.0 | 0.500000112 | 0.499999888 | 0.500000090 | 0.499999910 |
-| 3.0 | 0.500000032 | 0.499999968 | 0.500000030 | 0.499999970 |
-| 10.0 | 0.500000009 | 0.499999991 | 0.500000009 | 0.499999991 |
+| 0.1 | 0.500 | 0.500 | 0.500 | 0.500 |
+| 0.3 | 0.500 | 0.500 | 0.500 | 0.500 |
+| 1.0 | 0.500 | 0.500 | 0.500 | 0.500 |
+| 3.0 | 0.500 | 0.500 | 0.500 | 0.500 |
+| 10.0 | 0.500 | 0.500 | 0.500 | 0.500 |
 
 At the headline value $\tau=1$, both conventions therefore give an effective
-tie. The free candidate's advantage decreases monotonically as $\tau$
-increases, and neither aggregation choice changes the conclusion. The
-appendix-only `kl_forward` calculation also remains within 0.0006 of an equal
-split across the grid.[^2]
+tie. The free-minus-restricted probability gap remains smaller than
+$10^{-5}$ at every $\tau$ under both conventions and comes entirely from the
+single negative-slope draw. Its monotone contraction with $\tau$ follows
+deterministically from the Boltzmann aggregation, not from a measured
+temperature effect.[^2]
 
 The result does not support a claim that BMS* preferentially rewards a
-satisfied restriction in this instance. BMS* assigns the restricted candidate
+satisfied restriction. BMS* assigns the restricted candidate
 essentially half the probability without partitioning the parameter space,
 but the encompassing candidate can reproduce every restricted optimum. The
 single predictive with a negative slope creates the entire primary-metric gap.
@@ -80,10 +95,15 @@ No prior from this list enters the BMS* calculation.[^2]
 
 Pyro NUTS ran two sequential chains with seeds 20260811 and 20260812. Each
 chain used 1,000 warmup iterations and retained 1,000 draws, with target
-acceptance probability 0.90 and maximum tree depth 8. Both fits recorded zero
-divergences. Rank-normalized $\widehat R$ reached at most 1.003 for the free
-fit and 1.002 for the restricted fit; minimum bulk effective sample sizes were
-1,004 and 1,638, respectively.[^2]
+acceptance probability 0.90 and maximum tree depth 8. Both chains for both
+candidates initialized deterministically at the same observed-data MLE through
+`init_to_value`: $A=0.886352$, $\omega=1.030240$, $\phi=-0.029881$,
+$b=0.251277$, $c=0.028723$, and $\sigma=0.321232$. Sampled-grid aliases near
+$\omega=4.939$ and $6.999$ make the $\omega$/$\phi$ likelihood multimodal.
+Both fits recorded zero divergences. Rank-normalized $\widehat R$ reached at
+most 1.003 for the free fit and 1.002 for the restricted fit; minimum bulk
+effective sample sizes were 1,004 and 1,638, respectively. These diagnostics
+support within-mode convergence only, not exploration across modes.[^2]
 
 | candidate | `elpd_loo` | SE | `p_loo` | max Pareto $k$ | warning |
 |---|---:|---:|---:|---:|---|
@@ -91,20 +111,32 @@ fit and 1.002 for the restricted fit; minimum bulk effective sample sizes were
 | slope-constrained Sin+Linear | -12.661 | 3.594 | 5.169 | 0.718 | yes, one observation |
 
 The constrained-minus-free `elpd_loo` difference equals 0.413 with a paired SE
-of 0.263.[^2] On its face, PSIS-LOO assigns the higher predictive score to the
-restricted candidate, while BMS* produces an effective tie. ArviZ nevertheless
-flags the restricted estimate because one observation exceeds the
-sample-size-specific good-$k$ threshold of 0.697. Pareto shape values above
-about 0.7 can make the importance-sampling approximation unreliable, so the
-direction should not support a decisive claim without exact refits or a more
-robust cross-validation calculation.[^3]
-
-This head-to-head does not reproduce a categorical LOO failure, and it does
-not show preferential BMS* credit for the satisfied constraint. It instead
-separates two mechanisms on identical data. LOO changes because the two
-Bayesian fits use different support for $b$; BMS* changes only when a shared
-$\psi$ has a negative free optimum. Here that event occurs once in 1,000 SIR
-predictives, leaving the BMS* result numerically indistinguishable from a tie.
+of 0.256, computed with `ddof=0` to match the ArviZ convention.[^2] The
+difference is directionally inconclusive: its magnitude is smaller than twice
+its paired SE, the constrained estimate carries a Pareto-$k$ warning because
+one observation exceeds the 0.697 good-$k$ threshold, and the paired SE covers
+data-level pointwise variability only, without MCMC error. Haaf, Klaassen, and
+Rouder report this kind of null-to-inconclusive LOO difference as the failure
+mode for a satisfied nested constraint.[^1] Pareto shape values above about
+0.7 can make the importance-sampling approximation unreliable, so a decisive
+direction would require exact refits or a more robust cross-validation
+calculation.[^3]
+
+The two slope priors coincide up to normalization on $b>0$, so LOO has no
+structural contrast wherever negative-slope posterior mass is negligible. The
+artifact's own full-data local Gaussian diagnostic gives posterior SD
+0.0129506 for $b$, places the boundary 19.4028 SDs away, and gives a Gaussian
+left-tail probability of $3.65\times10^{-84}$. This local approximation
+supports the reading that the constraint binds only where the locally
+approximated posterior carries negligible mass. It does not prove that the
+global posteriors or leave-one-out fold posteriors are exactly identical, and
+it does not establish that the entire observed gap comes from estimator
+noise.[^2]
+
+The LOO arm therefore reproduces the null-to-inconclusive failure mode without
+supporting a directional claim. BMS* also gives a numerical tie, with a
+one-sided direction fixed by nesting and a magnitude determined by the single
+negative-slope SIR draw.
 
 [^1]: 🟢 peer-reviewed — Haaf, Klaassen, and Rouder (2025). Bayes factor vs. posterior predictive model assessment: Insights from ordinal constraints. *Computational Brain & Behavior*. https://doi.org/10.1007/s42113-025-00240-0
 [^2]: 🟠 empirical — `experiments/haaf_nested_constraint.py`; `runs/haaf_nested_constraint/results.json` and `README.md` (data seed 42; prior-IS seeds 0, 1, 2; SIR seed 42; NUTS seeds 20260811 and 20260812).
diff --git a/experiments/haaf_nested_constraint.py b/experiments/haaf_nested_constraint.py
index 0637746..8ba218c 100644
--- a/experiments/haaf_nested_constraint.py
+++ b/experiments/haaf_nested_constraint.py
@@ -334,6 +334,43 @@ def observed_pair(x: np.ndarray, y: np.ndarray,
     return results, parameters
 
 
+def local_gaussian_slope_diagnostic(
+    x: np.ndarray,
+    parameters: Dict[str, float],
+) -> Dict:
+    """Approximate the full-data slope margin from local observed information."""
+    A = parameters["A"]
+    omega = parameters["omega"]
+    phi = parameters["phi"]
+    sigma = parameters["sigma"]
+    angle = omega * x + phi
+    jacobian = np.column_stack([
+        np.sin(angle),
+        A * np.cos(angle) * x,
+        A * np.cos(angle),
+        x,
+        np.ones_like(x),
+    ])
+    covariance = sigma ** 2 * np.linalg.inv(jacobian.T @ jacobian)
+    slope_sd = float(np.sqrt(covariance[3, 3]))
+    boundary_distance = float(parameters["b"] / slope_sd)
+    gaussian_tail = float(
+        0.5 * math.erfc(boundary_distance / math.sqrt(2.0)))
+    return {
+        "approximation": (
+            "full-data local Gaussian approximation at the observed-data MLE "
+            "from the mean-function Jacobian"
+        ),
+        "posterior_sd_b": slope_sd,
+        "boundary_distance_sd": boundary_distance,
+        "gaussian_left_tail_probability": gaussian_tail,
+        "scope_caveat": (
+            "local full-data approximation only; it does not establish global "
+            "posterior mass or any leave-one-out fold posterior"
+        ),
+    }
+
+
 def validated_sir_predictives(
     x: torch.Tensor,
     y: torch.Tensor,
@@ -433,6 +470,11 @@ def run_loo_candidate(
     chain_seeds: Sequence[int],
 ) -> Dict:
     """Run explicit seeded Pyro chains and compute PSIS-LOO with ArviZ."""
+    initial_values = _initial_values(mle_parameters, constrained)
+    initial_values_record = {
+        name: float(value.detach().cpu().item())
+        for name, value in initial_values.items()
+    }
     per_chain = []
     diverging = []
     acceptance_rates = []
@@ -445,7 +487,8 @@ def run_loo_candidate(
             lambda x_data, y_data: pyro_sin_linear(
                 x_data, y_data, constrained),
             init_strategy=init_to_value(
-                values=_initial_values(mle_parameters, constrained)),
+                values={name: value.clone()
+                        for name, value in initial_values.items()}),
             target_accept_prob=LOO_TARGET_ACCEPT,
             max_tree_depth=LOO_MAX_TREE_DEPTH,
         )
@@ -525,6 +568,11 @@ def run_loo_candidate(
             "chain_seeds": list(chain_seeds),
             "target_accept_prob": LOO_TARGET_ACCEPT,
             "max_tree_depth": LOO_MAX_TREE_DEPTH,
+            "init_strategy": {
+                "name": "init_to_value",
+                "initial_values": initial_values_record,
+                "same_values_for_every_chain": True,
+            },
             "divergences_by_chain": [int(mask.sum()) for mask in diverging],
             "divergences_total": int(sum(mask.sum() for mask in diverging)),
             "acceptance_rate_by_chain": acceptance_rates,
@@ -544,11 +592,15 @@ def loo_comparison(free: Dict, constrained: Dict) -> Dict:
     pointwise = (np.asarray(constrained["pointwise_elpd"], dtype=float)
                  - np.asarray(free["pointwise_elpd"], dtype=float))
     difference = constrained["elpd_loo"] - free["elpd_loo"]
-    se = float(np.sqrt(len(pointwise) * np.var(pointwise, ddof=1)))
+    se_ddof = 0
+    se = float(np.sqrt(len(pointwise) * np.var(pointwise, ddof=se_ddof)))
     return {
         "direction": "constrained_minus_free",
         "elpd_difference": float(difference),
         "se": se,
+        "se_ddof": se_ddof,
+        "se_formula": "sqrt(n * var(pointwise_differences, ddof=0))",
+        "se_convention": "matches the ArviZ az.loo and az.compare convention",
         "pointwise_differences": [float(value) for value in pointwise],
     }
 
@@ -557,6 +609,11 @@ def render_readme(results: Dict) -> str:
     bms = results["bms_star"]
     loo = results["psis_loo"]
     headline = bms["tables"][PRIMARY_METRIC]["1.0"]
+    appendix = bms["appendix_metric_diagnostic"]
+    local = results["candidate_definition"]["local_gaussian_slope_diagnostic"]
+    aliases = loo["sampled_grid_alias_diagnostic"]
+    initial = loo["candidates"]["free"]["sampler"]["init_strategy"]
+    initial_values = initial["initial_values"]
     lines = [
         "# Haaf-style nested constraint: BMS* and PSIS-LOO",
         "",
@@ -595,19 +652,59 @@ def render_readme(results: Dict) -> str:
         "- `runs/prior_sensitivity/is_draws_toy_elicited_s1.npz`",
         "- `runs/prior_sensitivity/is_draws_toy_elicited_s2.npz`",
         "",
-        "For each shared predictive pattern, both candidates minimize the ",
-        "primary G over their parameter regions through ",
-        "`CandidateModel._fit_mle`. No candidate-parameter prior contributes ",
-        "to the BMS* calculation.",
+        "For each shared predictive pattern, both candidates receive four shared ",
+        "base starts. The restricted fit additionally receives every free ",
+        "solution, clipped at b = 0 when necessary, and each candidate's ",
+        "selection pool retains the other candidate's feasible vectors. This ",
+        "deliberate asymmetry forces exact equality at shared optima instead of ",
+        "turning optimizer noise into a model gap.",
+        "",
+        "Because the restricted region forms a subset of the free region, the ",
+        "protocol has min G over the restricted region greater than or equal to ",
+        "min G over the free region for every predictive. The restricted BMS* ",
+        "probability therefore cannot exceed the free probability under either ",
+        "aggregation at any τ. Only the gap magnitude comes from the sampled ",
+        "predictives. The runtime tolerance gates guard against machinery ",
+        "regressions; they do not empirically test nesting.",
         "",
         "At τ = 1, pooled BMS* assigns "
-        f"{headline['pooled'][0]:.6f} to the free candidate and "
-        f"{headline['pooled'][1]:.6f} to the restricted candidate. "
-        "Expected-posterior aggregation assigns "
-        f"{headline['expected_posterior'][0]:.6f} and "
-        f"{headline['expected_posterior'][1]:.6f}, respectively. The free-fit "
-        f"slope falls below zero for {bms['slope_sign']['negative_fraction']:.6f} "
-        "of SIR predictives.",
+        f"{headline['pooled'][0]:.3f} to the free candidate and "
+        f"{headline['pooled'][1]:.3f} to the restricted candidate. "
+        "Expected-posterior aggregation also assigns "
+        f"{headline['expected_posterior'][0]:.3f} and "
+        f"{headline['expected_posterior'][1]:.3f}. The free-minus-restricted ",
+        "gap remains smaller than 1e-5 at every τ under both conventions and ",
+        f"comes from the {bms['slope_sign']['negative_count']} negative-slope "
+        "draw among 1,000 SIR predictives. Its monotone contraction with τ ",
+        "follows deterministically from Boltzmann aggregation, not from a ",
+        "measured temperature effect.",
+        "",
+        "## Appendix-only `kl_forward` stress note",
+        "",
+        "The pooled `kl_forward` column is degenerate at exactly [0.5, 0.5] ",
+        "for every τ. The single differing row has a `kl_forward` value of ",
+        f"{appendix['differing_row']['free_G']:.3f} for the free candidate and "
+        f"{appendix['differing_row']['constrained_G']:.3f} for the restricted "
+        f"candidate, compared with a grid median of "
+        f"{appendix['grid_median']['free']:.1f}. The approximately "
+        f"{appendix['global_max_row']['free_G']:.2e} global maximum occurs on "
+        "a separate row where both candidate values are equal. Under the global ",
+        "max-shift, the differing row contributes below float64 aggregate ",
+        "resolution, so the pooled result carries no directional information. ",
+        "The expected-posterior calculation reverses the primary-metric sign: ",
+        "the differing row favors the restricted candidate by "
+        f"{abs(appendix['differing_row']['constrained_minus_free_G']):.3f} nats, "
+        "and at τ = 1 it assigns "
+        f"{bms['tables'][APPENDIX_METRIC]['1.0']['expected_posterior'][0]:.12f} "
+        "to the free candidate and "
+        f"{bms['tables'][APPENDIX_METRIC]['1.0']['expected_posterior'][1]:.12f} "
+        "to the restricted candidate.",
+        "",
+        "These `kl_forward` values evaluate the candidate instances selected at ",
+        "the `pw_kl_vcal` optima, with sigma reset from unweighted RMS residuals ",
+        "after the primary-metric fit. They do not minimize `kl_forward` over ",
+        "either parameter region, so the primary nesting inequality does not ",
+        "apply to this appendix stress calculation.",
         "",
         "## PSIS-LOO priors and sampler",
         "",
@@ -624,6 +721,18 @@ def render_readme(results: Dict) -> str:
         "target acceptance probability 0.90, and maximum tree depth 8. ArviZ ",
         "receives the pointwise Normal log likelihoods and computes PSIS-LOO.",
         "",
+        "Every chain for both candidates initializes deterministically at the ",
+        f"common observed-data MLE through `{initial['name']}`: A = "
+        f"{initial_values['A']:.6f}, omega = {initial_values['omega']:.6f}, "
+        f"phi = {initial_values['phi']:.6f}, b = {initial_values['b']:.6f}, "
+        f"c = {initial_values['c']:.6f}, and sigma = "
+        f"{initial_values['sigma']:.6f}. The sampled x grid admits likelihood "
+        f"aliases near omega = {aliases['alias_omega'][0]:.3f} and "
+        f"{aliases['alias_omega'][1]:.3f} around the initialized mode at "
+        f"{aliases['mle_omega']:.4f}. The likelihood is therefore multimodal, ",
+        "so the reported R-hat and ESS values support within-mode convergence ",
+        "only; they do not establish exploration across modes.",
+        "",
         "## Headline PSIS-LOO",
         "",
         "| candidate | elpd_loo | SE | p_loo | max Pareto k | warning | divergences | max r_hat |",
@@ -642,11 +751,25 @@ def render_readme(results: Dict) -> str:
     lines += [
         "",
         "The paired constrained-minus-free elpd difference equals "
-        f"{pair['elpd_difference']:.3f} with SE {pair['se']:.3f}.",
-        "ArviZ flags the constrained estimate because "
+        f"{pair['elpd_difference']:.3f} with SE {pair['se']:.3f}, computed with "
+        f"ddof={pair['se_ddof']} to match the ArviZ convention. The difference ",
+        "is directionally inconclusive because it is smaller than twice its ",
+        "paired SE, and ArviZ flags the constrained estimate because "
         f"{loo['candidates']['constrained']['pareto_k']['n_over_good_k_threshold']} "
-        "observation exceeds its sample-size-specific good-k threshold. Interpret "
-        "the direction with that qualification.",
+        "observation exceeds its sample-size-specific good-k threshold. The ",
+        "paired SE covers data-level pointwise variability only and does not ",
+        "include MCMC error. A null-to-inconclusive LOO difference matches the ",
+        "failure mode reported for satisfied nested constraints.",
+        "",
+        "The two slope priors coincide up to normalization on b > 0. The ",
+        "artifact's full-data local Gaussian approximation gives posterior SD ",
+        f"{local['posterior_sd_b']:.7f} for b, places the boundary "
+        f"{local['boundary_distance_sd']:.4f} SDs away, and gives a Gaussian ",
+        f"left-tail probability of {local['gaussian_left_tail_probability']:.2e}. "
+        "This local approximation supports the reading that the constraint ",
+        "binds only where the locally approximated posterior carries negligible ",
+        "mass. It does not prove exact posterior identity or show that the entire ",
+        "observed gap comes from estimator noise.",
         "",
         "## Determinism and tolerances",
         "",
@@ -660,10 +783,11 @@ def render_readme(results: Dict) -> str:
         lines.append(f"- `{key}`: {value}")
     lines += [
         "",
-        f"The primary nesting gates use {G_EQUAL_ATOL:g} absolute tolerance "
-        "for equality on nonnegative free-slope rows and "
+        f"The primary machinery-regression gates use {G_EQUAL_ATOL:g} absolute "
+        "tolerance for equality on nonnegative free-slope rows and "
         f"{G_ORDER_ATOL:g} for the one-sided G ordering on negative-slope rows. ",
-        "A failure stops the run before artifact replacement.",
+        "A failure stops the run before artifact replacement; passing the gates ",
+        "does not supply an empirical nesting test.",
         "",
         "No figure accompanies the case because the comparison table and the ",
         "slope-sign diagnostic convey the full result without an additional ",
@@ -694,6 +818,17 @@ def main() -> None:
 
     observed_results, observed_parameters = observed_pair(
         x_np, y_np, x_eval_np)
+    local_slope = local_gaussian_slope_diagnostic(
+        x_np, observed_parameters[MODEL_NAMES[0]])
+    x_spacing = float(np.diff(x_np)[0])
+    if not np.allclose(np.diff(x_np), x_spacing):
+        raise RuntimeError("sampled-grid alias diagnostic requires equal x spacing")
+    alias_period = 2.0 * math.pi / abs(x_spacing)
+    mle_omega = observed_parameters[MODEL_NAMES[0]]["omega"]
+    alias_omega = sorted([
+        abs(alias_period - mle_omega),
+        alias_period + mle_omega,
+    ])
     print("Loading validated SIR predictives")
     predictives, pss_anchor, sir_indices, pooled_ess = validated_sir_predictives(
         x, y, x_eval, observed_results, n_pred)
@@ -727,6 +862,62 @@ def main() -> None:
         APPENDIX_METRIC: appendix_G,
     }
     tables = aggregate_tables(G_by_metric)
+    appendix_gap = appendix_G[:, 1] - appendix_G[:, 0]
+    appendix_differing_indices = np.flatnonzero(appendix_gap != 0.0)
+    appendix_differing_row = None
+    if len(appendix_differing_indices):
+        appendix_index = int(appendix_differing_indices[0])
+        appendix_differing_row = {
+            "index": appendix_index,
+            "free_G": float(appendix_G[appendix_index, 0]),
+            "constrained_G": float(appendix_G[appendix_index, 1]),
+            "constrained_minus_free_G": float(appendix_gap[appendix_index]),
+            "reverses_primary_metric_direction": bool(
+                np.sign(appendix_gap[appendix_index])
+                == -np.sign(gap[appendix_index])),
+        }
+    pooled_exact_half = all(
+        tables[APPENDIX_METRIC][str(tau)]["pooled"] == [0.5, 0.5]
+        for tau in TAUS
+    )
+    differing_row_underflow_by_tau = {
+        str(tau): bool(len(appendix_differing_indices)) and bool(np.all(
+            np.exp(-appendix_G / tau - np.max(-appendix_G / tau))[
+                appendix_differing_indices] == 0.0
+        ))
+        for tau in TAUS
+    }
+    appendix_max_index = int(np.argmax(np.max(appendix_G, axis=1)))
+    appendix_global_max_row = {
+        "index": appendix_max_index,
+        "free_G": float(appendix_G[appendix_max_index, 0]),
+        "constrained_G": float(appendix_G[appendix_max_index, 1]),
+        "constrained_minus_free_G": float(appendix_gap[appendix_max_index]),
+    }
+    appendix_diagnostic = {
+        "evaluation_point": (
+            "pw_kl_vcal-optimal candidate instances with sigma reset from "
+            "unweighted RMS residuals after the primary-metric fit"
+        ),
+        "minimized_over_region_for_kl_forward": False,
+        "primary_nesting_inequality_applies": False,
+        "differing_row_count": int(len(appendix_differing_indices)),
+        "differing_row": appendix_differing_row,
+        "grid_median": {
+            "free": float(np.median(appendix_G[:, 0])),
+            "constrained": float(np.median(appendix_G[:, 1])),
+        },
+        "pooled_exact_half_at_every_tau": pooled_exact_half,
+        "differing_row_weight_underflow_by_tau": (
+            differing_row_underflow_by_tau
+        ),
+        "global_max_row": appendix_global_max_row,
+        "pooled_degeneracy_cause": (
+            "the global max-shift suppresses the differing row below float64 "
+            "aggregate resolution; the much larger global-maximum row has "
+            "equal candidate values"
+        ),
+    }
 
     print("Running PSIS-LOO models")
     free_loo = run_loo_candidate(
@@ -757,6 +948,10 @@ def main() -> None:
             "n": int(len(x_np)),
             "seed": DATA_SEED,
             "x_range": [float(x_np.min()), float(x_np.max())],
+            "x_eval": {
+                "n": int(len(x_eval_np)),
+                "range": [float(x_eval_np.min()), float(x_eval_np.max())],
+            },
             "true_bias_slope": float(info["bias_slope"]),
             "noise_std": float(info["noise_std"]),
             "xy_sha256_float64_le": _sha256_arrays(x_np, y_np),
@@ -768,7 +963,19 @@ def main() -> None:
             "constrained_bounds": NestedSinLinearModel(True).bounds,
             "only_bound_difference_index": 3,
             "only_bound_difference_parameter": "b",
+            "fit_protocol": {
+                "shared_base_starts": len(NestedSinLinearModel.base_starts()),
+                "restricted_extra_starts": (
+                    "all free solutions, clipped at b=0 when necessary"
+                ),
+                "cross_seeded_selection_pools": True,
+                "purpose": (
+                    "force exact equality on shared optima instead of optimizer "
+                    "noise"
+                ),
+            },
             "observed_data_mle": observed_parameters,
+            "local_gaussian_slope_diagnostic": local_slope,
         },
         "bms_star": {
             "config": CONFIG,
@@ -822,6 +1029,7 @@ def main() -> None:
                     },
                 },
             },
+            "appendix_metric_diagnostic": appendix_diagnostic,
             "validated_pss_observed_fit_anchor": {
                 "metric": PRIMARY_METRIC,
                 "tau": 1.0,
@@ -833,6 +1041,16 @@ def main() -> None:
         "psis_loo": {
             "priors_apply_only_to_loo": True,
             "priors": PRIOR_DESCRIPTIONS,
+            "sampled_grid_alias_diagnostic": {
+                "x_spacing": x_spacing,
+                "alias_period": alias_period,
+                "mle_omega": float(mle_omega),
+                "alias_omega": [float(value) for value in alias_omega],
+                "diagnostic_scope": (
+                    "the likelihood is multimodal; R-hat and ESS from common-MLE "
+                    "initializations support within-mode convergence only"
+                ),
+            },
             "candidates": {
                 "free": free_loo,
                 "constrained": constrained_loo,
diff --git a/pyproject.toml b/pyproject.toml
index 291dbbb..424e46b 100644
--- a/pyproject.toml
+++ b/pyproject.toml
@@ -16,6 +16,7 @@ dependencies = [
     "scipy>=1.10",
     "matplotlib>=3.7",
     "scikit-learn>=1.3",
+    "arviz>=0.17",
 ]
 
 [project.optional-dependencies]
diff --git a/requirements.txt b/requirements.txt
index 83708f7..b47ff6e 100644
--- a/requirements.txt
+++ b/requirements.txt
@@ -5,3 +5,4 @@ numpy>=1.24
 scipy>=1.10
 matplotlib>=3.7
 scikit-learn>=1.3
+arviz>=0.17
diff --git a/runs/haaf_nested_constraint/README.md b/runs/haaf_nested_constraint/README.md
index bc62abe..b7e55d8 100644
--- a/runs/haaf_nested_constraint/README.md
+++ b/runs/haaf_nested_constraint/README.md
@@ -35,12 +35,42 @@ Expected cache paths:
 - `runs/prior_sensitivity/is_draws_toy_elicited_s1.npz`
 - `runs/prior_sensitivity/is_draws_toy_elicited_s2.npz`
 
-For each shared predictive pattern, both candidates minimize the
-primary G over their parameter regions through
-`CandidateModel._fit_mle`. No candidate-parameter prior contributes
-to the BMS* calculation.
-
-At τ = 1, pooled BMS* assigns 0.500000 to the free candidate and 0.500000 to the restricted candidate. Expected-posterior aggregation assigns 0.500000 and 0.500000, respectively. The free-fit slope falls below zero for 0.001000 of SIR predictives.
+For each shared predictive pattern, both candidates receive four shared
+base starts. The restricted fit additionally receives every free
+solution, clipped at b = 0 when necessary, and each candidate's
+selection pool retains the other candidate's feasible vectors. This
+deliberate asymmetry forces exact equality at shared optima instead of
+turning optimizer noise into a model gap.
+
+Because the restricted region forms a subset of the free region, the
+protocol has min G over the restricted region greater than or equal to
+min G over the free region for every predictive. The restricted BMS*
+probability therefore cannot exceed the free probability under either
+aggregation at any τ. Only the gap magnitude comes from the sampled
+predictives. The runtime tolerance gates guard against machinery
+regressions; they do not empirically test nesting.
+
+At τ = 1, pooled BMS* assigns 0.500 to the free candidate and 0.500 to the restricted candidate. Expected-posterior aggregation also assigns 0.500 and 0.500. The free-minus-restricted
+gap remains smaller than 1e-5 at every τ under both conventions and
+comes from the 1 negative-slope draw among 1,000 SIR predictives. Its monotone contraction with τ
+follows deterministically from Boltzmann aggregation, not from a
+measured temperature effect.
+
+## Appendix-only `kl_forward` stress note
+
+The pooled `kl_forward` column is degenerate at exactly [0.5, 0.5]
+for every τ. The single differing row has a `kl_forward` value of
+500.142 for the free candidate and 488.982 for the restricted candidate, compared with a grid median of 55.8. The approximately 5.92e+10 global maximum occurs on a separate row where both candidate values are equal. Under the global
+max-shift, the differing row contributes below float64 aggregate
+resolution, so the pooled result carries no directional information.
+The expected-posterior calculation reverses the primary-metric sign:
+the differing row favors the restricted candidate by 11.160 nats, and at τ = 1 it assigns 0.499500014228 to the free candidate and 0.500499985772 to the restricted candidate.
+
+These `kl_forward` values evaluate the candidate instances selected at
+the `pw_kl_vcal` optima, with sigma reset from unweighted RMS residuals
+after the primary-metric fit. They do not minimize `kl_forward` over
+either parameter region, so the primary nesting inequality does not
+apply to this appendix stress calculation.
 
 ## PSIS-LOO priors and sampler
 
@@ -60,6 +90,11 @@ Pyro NUTS runs two sequential chains with seeds 20260811 and
 target acceptance probability 0.90, and maximum tree depth 8. ArviZ
 receives the pointwise Normal log likelihoods and computes PSIS-LOO.
 
+Every chain for both candidates initializes deterministically at the
+common observed-data MLE through `init_to_value`: A = 0.886352, omega = 1.030240, phi = -0.029881, b = 0.251277, c = 0.028723, and sigma = 0.321232. The sampled x grid admits likelihood aliases near omega = 4.939 and 6.999 around the initialized mode at 1.0302. The likelihood is therefore multimodal,
+so the reported R-hat and ESS values support within-mode convergence
+only; they do not establish exploration across modes.
+
 ## Headline PSIS-LOO
 
 | candidate | elpd_loo | SE | p_loo | max Pareto k | warning | divergences | max r_hat |
@@ -67,8 +102,20 @@ receives the pointwise Normal log likelihoods and computes PSIS-LOO.
 | Free Sin+Linear | -13.074 | 3.458 | 5.343 | 0.564 | no | 0 | 1.003 |
 | Slope-constrained Sin+Linear | -12.661 | 3.594 | 5.169 | 0.718 | yes | 0 | 1.002 |
 
-The paired constrained-minus-free elpd difference equals 0.413 with SE 0.263.
-ArviZ flags the constrained estimate because 1 observation exceeds its sample-size-specific good-k threshold. Interpret the direction with that qualification.
+The paired constrained-minus-free elpd difference equals 0.413 with SE 0.256, computed with ddof=0 to match the ArviZ convention. The difference
+is directionally inconclusive because it is smaller than twice its
+paired SE, and ArviZ flags the constrained estimate because 1 observation exceeds its sample-size-specific good-k threshold. The
+paired SE covers data-level pointwise variability only and does not
+include MCMC error. A null-to-inconclusive LOO difference matches the
+failure mode reported for satisfied nested constraints.
+
+The two slope priors coincide up to normalization on b > 0. The
+artifact's full-data local Gaussian approximation gives posterior SD
+0.0129506 for b, places the boundary 19.4028 SDs away, and gives a Gaussian
+left-tail probability of 3.65e-84. This local approximation supports the reading that the constraint
+binds only where the locally approximated posterior carries negligible
+mass. It does not prove exact posterior identity or show that the entire
+observed gap comes from estimator noise.
 
 ## Determinism and tolerances
 
@@ -82,8 +129,9 @@ tolerances:
 - `loo_pairwise_difference_abs`: 0.25
 - `negative_slope_fraction_abs`: 0.005
 
-The primary nesting gates use 2e-07 absolute tolerance for equality on nonnegative free-slope rows and 2e-07 for the one-sided G ordering on negative-slope rows.
-A failure stops the run before artifact replacement.
+The primary machinery-regression gates use 2e-07 absolute tolerance for equality on nonnegative free-slope rows and 2e-07 for the one-sided G ordering on negative-slope rows.
+A failure stops the run before artifact replacement; passing the gates
+does not supply an empirical nesting test.
 
 No figure accompanies the case because the comparison table and the
 slope-sign diagnostic convey the full result without an additional
diff --git a/runs/haaf_nested_constraint/results.json b/runs/haaf_nested_constraint/results.json
index 36fd9fe..0c07d9e 100644
--- a/runs/haaf_nested_constraint/results.json
+++ b/runs/haaf_nested_constraint/results.json
@@ -10,6 +10,13 @@
       -10.0,
       10.0
     ],
+    "x_eval": {
+      "n": 60,
+      "range": [
+        -11.0,
+        11.0
+      ]
+    },
     "true_bias_slope": 0.25,
     "noise_std": 0.5,
     "xy_sha256_float64_le": "f54c873f48f6d049778d12989b3209d78605002f747a2805551cedfd9d4eedb5"
@@ -74,6 +81,12 @@
     ],
     "only_bound_difference_index": 3,
     "only_bound_difference_parameter": "b",
+    "fit_protocol": {
+      "shared_base_starts": 4,
+      "restricted_extra_starts": "all free solutions, clipped at b=0 when necessary",
+      "cross_seeded_selection_pools": true,
+      "purpose": "force exact equality on shared optima instead of optimizer noise"
+    },
     "observed_data_mle": {
       "Free Sin+Linear": {
         "A": 0.8863515558683248,
@@ -91,6 +104,13 @@
         "c": 0.02872270880462028,
         "sigma": 0.32123190979141125
       }
+    },
+    "local_gaussian_slope_diagnostic": {
+      "approximation": "full-data local Gaussian approximation at the observed-data MLE from the mean-function Jacobian",
+      "posterior_sd_b": 0.012950550589627553,
+      "boundary_distance_sd": 19.402803798893753,
+      "gaussian_left_tail_probability": 3.653754311948442e-84,
+      "scope_caveat": "local full-data approximation only; it does not establish global posterior mass or any leave-one-out fold posterior"
     }
   },
   "bms_star": {
@@ -282,6 +302,38 @@
         }
       }
     },
+    "appendix_metric_diagnostic": {
+      "evaluation_point": "pw_kl_vcal-optimal candidate instances with sigma reset from unweighted RMS residuals after the primary-metric fit",
+      "minimized_over_region_for_kl_forward": false,
+      "primary_nesting_inequality_applies": false,
+      "differing_row_count": 1,
+      "differing_row": {
+        "index": 984,
+        "free_G": 500.1419747964646,
+        "constrained_G": 488.98168850611455,
+        "constrained_minus_free_G": -11.16028629035003,
+        "reverses_primary_metric_direction": true
+      },
+      "grid_median": {
+        "free": 55.77955486646584,
+        "constrained": 55.77955486646584
+      },
+      "pooled_exact_half_at_every_tau": true,
+      "differing_row_weight_underflow_by_tau": {
+        "0.1": true,
+        "0.3": true,
+        "1.0": false,
+        "3.0": false,
+        "10.0": false
+      },
+      "global_max_row": {
+        "index": 733,
+        "free_G": 59227845231.42128,
+        "constrained_G": 59227845231.42128,
+        "constrained_minus_free_G": 0.0
+      },
+      "pooled_degeneracy_cause": "the global max-shift suppresses the differing row below float64 aggregate resolution; the much larger global-maximum row has equal candidate values"
+    },
     "validated_pss_observed_fit_anchor": {
       "metric": "pw_kl_vcal",
       "tau": 1.0,
@@ -303,6 +355,16 @@
       "c": "Normal(loc=0, scale=5)",
       "sigma": "HalfNormal(scale=2)"
     },
+    "sampled_grid_alias_diagnostic": {
+      "x_spacing": 1.0526315789473681,
+      "alias_period": 5.969026041820609,
+      "mle_omega": 1.030239891010187,
+      "alias_omega": [
+        4.938786150810421,
+        6.999265932830796
+      ],
+      "diagnostic_scope": "the likelihood is multimodal; R-hat and ESS from common-MLE initializations support within-mode convergence only"
+    },
     "candidates": {
       "free": {
         "elpd_loo": -13.074035199760031,
@@ -371,6 +433,18 @@
           ],
           "target_accept_prob": 0.9,
           "max_tree_depth": 8,
+          "init_strategy": {
+            "name": "init_to_value",
+            "initial_values": {
+              "A": 0.8863515558683248,
+              "omega": 1.030239891010187,
+              "phi": -0.02988145356722502,
+              "b": 0.2512769921781912,
+              "c": 0.02872270880462028,
+              "sigma": 0.32123190979141125
+            },
+            "same_values_for_every_chain": true
+          },
           "divergences_by_chain": [
             0,
             0
@@ -476,6 +550,18 @@
           ],
           "target_accept_prob": 0.9,
           "max_tree_depth": 8,
+          "init_strategy": {
+            "name": "init_to_value",
+            "initial_values": {
+              "A": 0.8863515558683248,
+              "omega": 1.030239891010187,
+              "phi": -0.02988145356722502,
+              "b": 0.2512769921781912,
+              "c": 0.02872270880462028,
+              "sigma": 0.32123190979141125
+            },
+            "same_values_for_every_chain": true
+          },
           "divergences_by_chain": [
             0,
             0
@@ -518,7 +604,10 @@
     "pairwise": {
       "direction": "constrained_minus_free",
       "elpd_difference": 0.4126590617546153,
-      "se": 0.262534386964351,
+      "se": 0.25588686781820247,
+      "se_ddof": 0,
+      "se_formula": "sqrt(n * var(pointwise_differences, ddof=0))",
+      "se_convention": "matches the ArviZ az.loo and az.compare convention",
       "pointwise_differences": [
         0.031462166005881365,
         0.019099698330638404,
