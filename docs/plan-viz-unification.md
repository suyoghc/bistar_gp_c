# Plan: viz-script unification onto laplace_evidence (Task 2 batch 2b) — 2026-07-06, R2

Port `bistar_viz/scripts/model_priors_laplace.py` (515 ln) and
`model_prior_trajectory_laplace.py` (542 ln) onto the canonical
`bistar_gp.laplace_evidence` machinery (D3 open item 1, unblocked by D10,
foundation refactored in D15).

**Revision 2 (same day): R1 incorporated the codex review of R0 (22a3e5e);
R2 patches four blockers from the codex re-review of R1 (15051aa) — see the
§7 review log. Notably R2 corrects an R1 factual error (Quadratic bounds DO
differ between the legacy scripts) and respecifies the IS estimator as
ordinary/balance-heuristic MIS (SNIS was mathematically wrong for a
normalizing constant).** The R1 summary below stands otherwise: Dispositions are logged in §7; the material changes:
the reference Z_Mx estimator for figures is now defensive-mixture IS rather
than a fixed-window Laplace/MC blend (codex S2: the R0 blend was pure Laplace
at exactly the fixed-τ=0.3 panels it claimed to improve); the two legacy
scripts' space/occam/multi-start DIFFERENCES are now stated from in-repo
verification and resolved by unify-with-disclosure; prior parity is pinned to
`PRIOR_CONFIGS["informative"]` (`build_toy_kernels()` uses `Gamma(2,2)`
lengthscale — the legacy-matching `Gamma(6,0.85)` is commented out in
`model.py`); the comparison harness extracts legacy scripts from a pinned
commit so it stays rerunnable after replace-in-place; `rng=` is added to
`extract_gp_predictives` instead of caller-side global seeding.

## 0. Evidence base

Two adversarial verification runs (2026-07-06) ground this plan. Their raw
scripts are session-scratch (not committed); accordingly, treat the specific
constants below as *measured once, to be re-derived in-repo* — §6 commits a
re-derivation script as part of implementation. The STRUCTURAL claims are
closed-form consequences of the Laplace expression and were independently
confirmed by the codex review.

**V1 — pure Laplace is NOT adequate for the τ-sweep figure; plain MC is not
adequate at low τ (verdict: two regimes, no single cheap estimator).** On
sigma-free spaces mirroring the trajectory script's bounds, against 200k-
sample uniform-box MC cross-checked by a 400k defensive-mixture IS estimator:

- Laplace's `(d/2)log τ` term grows without bound while the true
  occam-normalized `Z_Mx = E_box[exp(−Ḡ/τ)] ≤ 1` (so `log Z ≤ 0` — a hard
  bound Laplace crosses at finite τ: measured ≈31/47/187 for d=3/5/2). The
  cross-model ranking FLIPS (measured τ≈88) because at large τ Laplace orders
  models by d while the truth orders them by mean box divergence; at the
  legacy figure's τ_max≈316 the Laplace posterior gap vs truth was 0.45 with
  the wrong winner. The flip-τ is closed-form derivable from the Laplace
  expression — it becomes a committed regression check (§6).
- Mid-range (τ~0.3–3) pure Laplace carries 1–2.5-nat model-specific errors
  from non-Gaussianity (Sinusoidal's Ḡ-minimum pinned at the ω=0.1 boundary;
  Sin+Linear's bimodal Ḡ landscape), i.e. posterior gaps 0.10–0.25.
  Laplace/MC agreement near τ≈1 and τ≈20–30 is coincidental cancellation.
- Plain uniform-box MC fails at LOW τ: ESS < 200 below τ≈0.3, and misses
  Sin+Linear's narrow Ḡ=0 basin entirely at τ=0.1 (−2.4 nats).
- The package's single midpoint start found Ḡ*=4.94 for Sinusoidal (true
  0.796) and missed Sin+Linear's Ḡ*=0 — multi-start is mandatory (the D11
  lesson recurring).
- The legacy G-clamp at 500 is immaterial (<0.001 nats).

**V2 — the averaged-GP port recipe is exact where it must be.** The viz
`compute_averaged_gp` moment-match and the package `average_gp_posterior`
agree at machine precision on identical draws with uniform weights (2.2e-16
mean, 8.9e-16 var); a weighted generalization is exact to 1.8e-15. The port
differences to handle or disclose: (i) ESTIMATOR — viz importance-weights
PRIOR draws by LML, package uses uniform-weighted draws from the chosen
`fit_gp` method (on identical draws, LML-vs-uniform weighting shifts moments
by up to 2.37 mean / 3.21 var — the deliberate D10 estimator change,
disclosed, not a bug); (ii) variance floor 1e-6 (viz) vs 1e-10 (package
`_extract_marginals`) — adopt the package floor per D10; (iii) diag-only vs
full mixture covariance — harmless under pw_* metrics, which consume
marginals; (iv) training-Gram jitter 1e-6 vs 1e-4; (v) viz clips extreme
hyperparameter draws, the package drops them on Cholesky failure — the port
counts and reports retained draws per stage; (vi) `extract_gp_predictives`
subsampling uses global np.random and needs placeholder x/y tensors for the
n=0 prior stage; (vii) prior parity is the script's responsibility.

**V3 — the two legacy scripts are NOT mutually consistent (verified in-repo;
bounds re-verified in R2 after a truncated-grep error in R1).**
`model_priors_laplace.py` vs `model_prior_trajectory_laplace.py`: (a) Linear
bounds (-2,2) vs (-3,3) AND Quadratic bounds [(-0.5,0.5),(-2,2),(-5,5)] vs
[(-1,1),(-3,3),(-5,5)] (Sinusoidal and Sin+Linear match); (b) the priors
script's
Laplace Z always subtracts `log V` (occam ON) while the trajectory script's
`compute_laplace_Z` has NO `−log V` term (occam OFF) — since `log V_j`
differs per model, the two legacy figure sets used different normalized
posteriors, an inconsistency the unification must resolve, not preserve;
(c) multi-start styles differ (fixed inits lists vs p0 + 20 seeded random
perturbations clipped to 0.99·bounds). Resolution: **unify with
disclosure** (§3), reproducing each legacy convention only inside the
comparison harness.

## 1. Package additions (laplace_evidence.py)

1. **`mc_log_Z_Mx(param_space, x_eval, avg_gp, taus, *, n_mc=200_000,
   seed=0, metric_name="pw_kl_vcal", occam=False)`** — uniform-box sampling;
   Ḡ computed ONCE, reweighted per τ (`logsumexp(−Ḡ/τ) − log n_mc`); returns
   per-τ log Z + per-τ ESS. Occam bookkeeping (codex-CONFIRMED): the
   box-uniform mean estimates the OCCAM-normalized `(1/V)∫exp(−Ḡ/τ)dφ`, so
   `occam=False` ADDS `+log V` — the inverse of the Laplace path where
   `occam=True` subtracts it. A cross-estimator volume-invariance test (§6)
   pins the D5 same-reference-measure invariant so a mixed Laplace/MC ladder
   can never silently disagree on volume bookkeeping.
2. **`is_log_Z_Mx(param_space, x_eval, avg_gp, taus, *, n_is=100_000,
   seed=0, starts=None, metric_name=..., occam=False)`** — ORDINARY
   defensive-mixture importance sampling (balance-heuristic MIS), NOT
   self-normalized IS: SNIS estimates expectations whose normalizer cancels,
   but Z_Mx IS the normalizer, so the proposal density must be evaluated
   exactly. Proposal q = ½·uniform-box + ½·mixture of BOX-TRUNCATED Gaussians
   at the multi-start optima with covariances `τ_k·H⁻¹` over a small τ_k
   ladder. Implementation choice (codex watchpoint, resolved): the Gaussian
   components are UNTRUNCATED (normalized on ℝᵈ) and the box constraint is an
   INDICATOR on the integrand — q integrates to 1 by construction, out-of-box
   draws contribute zero weight, and no per-component truncation-mass
   computation is needed; the cost is a small sampling-efficiency loss. A
   standalone consistency test estimates `∫_box 1 dφ = V` through the full
   sample-and-evaluate path (§6.10). Estimate:
   `log I_raw = logmeanexp_i( −Ḡ(φ_i)/τ − log q(φ_i) )`, φ_i ~ q — the RAW
   Lebesgue integral over the box. `occam=False` returns `log I_raw`;
   `occam=True` returns `log I_raw − log V` (same convention as the Laplace
   path). Valid at ALL τ from one sample set; returns per-τ log Z + ESS,
   warns when ESS < threshold.
   **This is the reference/default estimator for all figure Z_Mx values**
   (codex recommendation adopted): one estimator, no seam, no
   blended-bias window — and it fixes the R0 inconsistency that the blend
   was pure Laplace at exactly the fixed-τ=0.3 panels V1 showed Laplace
   distorting by 0.10–0.25. Laplace (analytic, low-τ) and `mc_log_Z_Mx`
   (high-τ) remain as cheap CROSS-CHECKS: the harness plots all three, and
   an ESS-adaptive hybrid is NOT built unless the IS estimator proves too
   expensive in practice (it did not in V1: 400k evaluations covered a
   7-point τ ladder for three models in minutes).
3. **`laplace_log_Z_Mx(..., starts=None)`** — optional list of start dicts;
   runs the existing single-start path per start, keeps the min-Ḡ* result.
   Mandatory per V1's midpoint-start failures; also feeds the IS proposal's
   Gaussian components.
4. **`average_gp_posterior(..., weights=None)`** — verified-exact weighted
   moments (None = uniform, current behavior). Needed to reproduce legacy
   LML-weighted figures inside the comparison harness only.
5. **`extract_gp_predictives(..., rng=None)`** — optional
   `numpy.random.Generator` for the draw subsampling (codex: API parameter,
   not caller-side `np.random.seed`); `None` preserves the current
   global-state behavior for existing callers.

## 2. Port `model_priors_laplace.py`

- **Spaces**: sigma-free `ModelParameterSpace`s built in a shared
  `bistar_viz/scripts/_viz_spaces.py`, on the UNIFIED canonical bounds (§3);
  legacy positional `predict_fn`s converted to dict-based; legacy `inits`
  become `starts`.
- **Priors** (codex fix): kernels/likelihood built via
  `build_kernels_from_config(PRIOR_CONFIGS["informative"])` and
  `build_likelihood_from_config(...)` — NOT `build_toy_kernels()`, whose
  SE-lengthscale prior is `Gamma(2,2)` (the legacy-matching `Gamma(6,0.85)`
  is present only as a comment in `model.py`). The harness asserts the
  registered prior parameters equal the config values at runtime.
- **Averaged GP** (V2 recipe): n>0 stages: `fit_map` →
  `fit_gp(method=args.gp_method)` → `extract_gp_predictives(rng=rng)` →
  `average_gp_posterior`. n=0 stage: placeholder tensors + `sample_prior` +
  `condition_on_data=False`. `--gp-method` **default `map`**, `vi`/`hmc`
  selectable. Language discipline (codex clarification): MAP output is a
  **point-estimate predictive** (a degenerate length-1 "posterior");
  "posterior draws" is reserved for `hmc`/`vi`. The default is defensible
  ONLY as a disclosed mechanism-figure choice: per D12 these figures
  illustrate the BI* mechanism, not full-Bayes inference claims, and under
  the `informative` priors MAP/HMC report the density-mode basin (minority
  mass) — the figure captions and the disclosure paragraph say so.
- **Z per model**: `is_log_Z_Mx(..., starts=legacy inits)` at the figure's
  τ (fixed panels AND normalization), `occam` per §3. `--estimator
  {is,laplace,mc}` exposed; `--estimator laplace` reproduces the legacy
  method for the harness.
- Report retained-draw counts per stage (V2 diff v).

## 3. Unification decisions (from V3)

- **Bounds**: one canonical set = the `model_priors_laplace.py` bounds
  (Linear (-2,2), Quadratic (-0.5,0.5)/(-2,2)/(-5,5)); D3 designates that
  script the viz reference for Z_Mx. The trajectory legacy deltas (Linear
  (-3,3) AND Quadratic (-1,1)/(-3,3)/(-5,5)) are reproduced only inside the
  harness for its own legacy comparison. Volumes enter through occam, so the
  bounds choice is disclosed alongside it.
- **Occam**: canonical default `occam=False` (D3's faithful no-Occam BI*
  default), with `occam=True` regenerated as the sensitivity variant —
  replacing the legacy scripts' contradictory hard-wired conventions
  (priors: always ON; trajectory: always OFF). Each legacy comparison runs
  under that script's own convention.
- **Multi-start**: canonical = the legacy inits lists via `starts=`, plus an
  optional `--n-perturb` (seeded rng) reproducing the trajectory script's
  20-perturbation robustness trick where its figures are compared.

## 4. Port `model_prior_trajectory_laplace.py`

Same shared spaces/averaged-GP; its `compute_avg_gp` / `compute_laplace_Z` /
`compute_Z_hybrid` / `precompute_G_samples` copies all collapse onto the
package. The τ-sweep figure comes from ONE `is_log_Z_Mx` call per model per
stage (per-τ reweighting of one sample set); the legacy sigmoid-blend hybrid
is not ported (superseded by IS — §1.2), but the harness overlays legacy
hybrid vs IS vs Laplace vs MC on the τ-sweep to document the change.

## 5. Comparison harness + close-out

- Harness is RERUNNABLE after replace-in-place (codex fix): it extracts the
  legacy scripts from the pinned pre-port commit at runtime
  (`git show <pinned>:bistar_viz/scripts/model_priors_laplace.py`, etc.)
  into `runs/viz_unification/legacy_scripts/`, runs them headless on the
  same data/seeds, and emits side-by-side figures + per-figure delta tables
  attributing gaps to (metric: none, D10 identity) / (estimator: prior-IS →
  fit_gp draws) / (Z method: pure Laplace or legacy hybrid → IS) /
  (occam/bounds convention: §3).
- Legacy scripts then REPLACED in place; old behavior preserved by the
  pinned commit + harness artifacts.
- Disclosure paragraph in `docs/inference-and-metric-options.md` (estimator
  + Z-method + convention changes, and why the new figures are more
  accurate).
- codex review of the full diff (`< /dev/null` on stdin); D16 entry; flip D3
  open item (1); PR #2 → Ready.

## 6. Test checklist (updated per review)

1. `mc_log_Z_Mx` vs brute-force grid on a 2-D space at τ ∈ {0.1, 1, 10}.
2. Occam/volume invariance ACROSS estimators (the D5 invariant), under a
   CONTROLLED setup where widening bounds changes only `log V` and not the
   sampled integrand — a constant-Ḡ metric (the existing `const_metric`
   fixture pattern) or an added dead parameter the predict_fn ignores:
   doubling that box must change `log Z` identically under Laplace, MC, and
   IS for both occam settings. (With a real metric, wider bounds change the
   integration region itself, so the naive version of this test would be
   comparing different integrals.)
3. `is_log_Z_Mx`: matches the 2-D grid truth across τ ∈ [0.1, 100]; matches
   Laplace at low τ on a unimodal interior-MAP case; ESS reported;
   deterministic under fixed seed; ESS warning fires on a starved case.
4. `starts=`: recovers the Sinusoidal ω-boundary optimum the midpoint start
   misses, and Sin+Linear's Ḡ*=0 basin (re-derives the V1 finding in-repo).
5. Laplace large-τ structure (re-derives V1 in-repo, codex outcome 9), with
   BOTH estimators at `occam=True` — the `log Z ≤ 0` bound holds only for
   the box-mean-normalized quantity (`Z = E_box[exp(−Ḡ/τ)] ≤ 1`); the raw
   `occam=False` Lebesgue integral can legitimately exceed 1. Assert
   `laplace_log_Z_Mx(occam=True) > 0` beyond a computed τ while
   `is_log_Z_Mx(occam=True) ≤ 0`, and assert the d-driven ranking-flip τ
   against its closed-form value.
6. `weights=` on `average_gp_posterior` vs the viz formula at machine
   precision (uniform and Dirichlet-random weights).
7. `extract_gp_predictives(rng=...)`: identical subsample under the same
   Generator; `rng=None` preserves legacy global-state behavior.
8. Prior-parity assertion: harness fails loudly if the built kernels' prior
   parameters differ from `PRIOR_CONFIGS["informative"]`.
9. n=0 prior stage smoke test: `sample_prior` → `condition_on_data=False` →
   `average_gp_posterior` → finite `is_log_Z_Mx` for all four models.
10. Proposal-consistency standalone test (codex watchpoint): estimate
    `∫_box 1 dφ = V` through the full IS sample-and-evaluate path (f = the
    in-box indicator) — validates that q's density evaluation matches its
    sampler, the sharp part of the estimator; also assert q's mixture mass
    (uniform component normalized on the box, untruncated Gaussians on ℝᵈ)
    integrates to 1 on a 2-D quadrature grid.

## 7. Review log

**R1 (2026-07-06) — codex review of R0 (22a3e5e), all outcomes dispositioned:**
(1) MC occam sign CONFIRMED — kept, plus the cross-estimator invariance test
(§6.2). (2) FIX accepted: R0's blend was pure Laplace at the fixed-τ=0.3
panels; resolved by adopting IS as the reference estimator everywhere (§1.2).
(3) FIX accepted with in-repo verification: legacy space/occam/multi-start
differences documented (§0 V3) and resolved by unify-with-disclosure (§3).
(R1's parenthetical here wrongly claimed the Quadratic bounds were identical —
corrected in R2.)
(4) RECOMMENDATION adopted: defensive-mixture IS is the default/reference;
the fixed-window hybrid is dropped rather than made adaptive (§1.2).
(5) CLARIFY accepted: MAP wording corrected to point-estimate predictive;
"posterior draws" reserved for hmc/vi; map default framed as a disclosed
mechanism-figure choice (§2). (6) API accepted: `starts=`, `weights=`, and
`rng=` on `extract_gp_predictives` (§1.3–1.5). (7) PRIOR PARITY accepted:
`PRIOR_CONFIGS["informative"]` + runtime assertion; `build_toy_kernels()`
`Gamma(2,2)` mismatch verified in `model.py` (§2). (8) HARNESS fix accepted:
legacy scripts extracted from the pinned commit at runtime (§5).
(9) NUMERIC-CLAIMS hedge accepted: §0 constants marked measured-once;
structural claims become committed regression tests (§6.5).

**R2 (2026-07-06) — codex re-review of R1 (15051aa), four outcomes, all
accepted:**
(1) S1 factual: R1's own "Quadratic bounds identical" claim was WRONG — the
trajectory script's bounds line sits beyond the grep window R1 used; verified
with full blocks: priors [(-0.5,0.5),(-2,2),(-5,5)] vs trajectory
[(-1,1),(-3,3),(-5,5)]. §0 V3, §3, and the R1 log entry corrected — the
trajectory legacy deltas are Linear AND Quadratic.
(2) S1 estimator spec: "self-normalized" was mathematically wrong for a
normalizing constant (SNIS cancels the very normalizer being estimated);
§1.2 respecified as ordinary defensive-mixture IS / balance-heuristic MIS
with an exactly evaluated, box-truncated-and-renormalized proposal density
and explicit occam bookkeeping (`log I_raw` raw; `−log V` under occam=True).
(3) S2: §6.5 test now pins `occam=True` explicitly — the `log Z ≤ 0` bound
holds only for the box-mean-normalized quantity.
(4) S2: §6.2 volume-invariance test restricted to a controlled setup
(constant-Ḡ metric or dead parameter) where widening bounds changes only
`log V`, not the integrand's region.

**R2 sign-off (2026-07-06): codex confirms implementation-ready.** One
engineering watchpoint (not a blocker): the proposal density is the sharp
part. Resolved by adopting the simpler untruncated-Gaussian + in-box
indicator construction (§1.2) with the standalone consistency test (§6.10).
