# Plan: viz-script unification onto laplace_evidence (Task 2 batch 2b) — 2026-07-06

Port `bistar_viz/scripts/model_priors_laplace.py` (515 ln) and
`model_prior_trajectory_laplace.py` (542 ln) onto the canonical
`bistar_gp.laplace_evidence` machinery (D3 open item 1, unblocked by D10,
foundation refactored in D15). Every design choice below is grounded in two
adversarial verification runs (2026-07-06, ~200k tokens, scripts preserved in
the session scratchpad and summarized here); the numbers cited are measured,
not assumed.

## 0. What the verification runs established

**V1 — pure Laplace is NOT adequate for the τ-sweep figure (verdict:
hybrid needed).** On sigma-free spaces mirroring the legacy MODELS bounds
(Linear d=2, Sinusoidal d=3, Sin+Linear d=5), against a 200k-sample uniform-box
MC ground truth (cross-checked by a 400k defensive-mixture IS estimator):

- The Laplace `(d/2)log τ` term grows without bound while the true
  occam-normalized `Z_Mx = E_box[exp(−Ḡ/τ)] ≤ 1`. Laplace crosses the
  impossible `log Z > 0` line at τ ≈ 31 (Sin), 47 (Sin+Lin), 187 (Lin); the
  cross-model ranking FLIPS at τ ≈ 88 purely because d=5 > d=3 — at the
  legacy figure's τ_max ≈ 316, Laplace gives Sin+Linear 0.77 vs true 0.32
  (wrong winner, posterior gap 0.45).
- Mid-range (τ ~ 0.3–3) pure Laplace also carries 1–2.5-nat model-specific
  errors from non-Gaussianity (Sinusoidal's Ḡ-minimum pinned at the ω=0.1
  boundary, +1.1 nats; Sin+Linear's bimodal Ḡ landscape, −1.9 to −2.5 nats),
  giving posterior gaps 0.10–0.25. Laplace/MC agreement near τ≈1 and τ≈20–30
  is coincidental cancellation.
- Plain uniform MC fails at the LOW end: ESS < 200 below τ ≈ 0.3, and it
  misses Sin+Linear's narrow Ḡ=0 basin entirely at τ=0.1 (−2.4 nats). So the
  legacy hybrid architecture (Laplace low-τ, MC high-τ) is justified in BOTH
  directions, not a convenience.
- The package's single midpoint start is insufficient: it found Ḡ* = 4.94 for
  Sinusoidal (true 0.796) and missed Sin+Linear's Ḡ* = 0 entirely.
  Multi-start is mandatory (the D11 lesson recurring).
- The legacy G-clamp at 500 is immaterial (< 0.001 nats). At the fixed τ=0.3
  used by the bar-chart/trajectory panels, pure Laplace preserves the top
  model but distorts probabilities by up to 0.22 and swaps 2nd/3rd.

**V2 — the averaged-GP port recipe is exact where it must be.** The viz
`compute_averaged_gp` moment-match and the package `average_gp_posterior` use
the same mixture-moment formulas: machine-precision agreement (2.2e-16 mean,
8.9e-16 var) on identical draws with uniform weights; a weighted
generalization is exact to 1.8e-15. The differences a port must handle or
disclose: (i) ESTIMATOR — viz importance-weights PRIOR draws by LML, package
uses uniform-weighted POSTERIOR draws (on the same draws, LML-vs-uniform
weighting shifts moments by up to 2.37 mean / 3.21 var — this is the
deliberate D10 estimator upgrade, disclosed, not a bug); (ii) variance floor
1e-6 (viz) vs 1e-10 (package `_extract_marginals`) — adopt the package floor
per D10; (iii) diag-only (viz) vs full mixture covariance (package) —
harmless under pw_* metrics, which consume marginals; (iv) training-Gram
jitter 1e-6 vs 1e-4; (v) viz clips extreme hyperparameter draws, the package
drops them on Cholesky failure (mixture N can shrink silently — count and
report); (vi) `extract_gp_predictives` has no seed argument (subsampling uses
global np.random) and requires placeholder x/y tensors for the n=0 prior
stage; (vii) prior parity (Gamma(6,0.85)³ + Gamma(1.75,1)) is the script's
responsibility — nothing in the package enforces it.

## 1. Package additions (laplace_evidence.py) — forced by V1

1. **`mc_log_Z_Mx(param_space, x_eval, avg_gp, taus, *, n_mc=200_000,
   seed=0, metric_name="pw_kl_vcal", occam=False)`** — uniform-box sampling;
   Ḡ computed ONCE and reweighted per τ (the legacy `precompute_G_samples`
   pattern, generalized): `log Z_occam(τ) = logsumexp(−Ḡ/τ) − log n_mc`.
   Occam bookkeeping: the box-uniform MC mean estimates `(1/V)∫exp(−Ḡ/τ)dφ`,
   i.e. the OCCAM-normalized quantity — `occam=False` must ADD `+log V`
   (inverse of the Laplace path, where occam=True subtracts it). Returns
   per-τ log Z plus per-τ ESS diagnostics.
2. **`hybrid_log_Z_Mx(...)`** — Laplace below τ_lo, MC above τ_hi, log-space
   linear blend inside [τ_lo, τ_hi]; defaults **τ_lo=0.3, τ_hi=1.0** from the
   measured ESS profile (MC ESS ≈ 200 at τ=0.3, ≥ 960 at τ≥1) rather than the
   legacy sigmoid centered at 0.5. Warn if MC ESS < 100 anywhere it carries
   weight. (Alternative considered: a defensive-mixture IS estimator valid at
   ALL τ — one method, no seam — deferred as heavier machinery unless review
   prefers it; the V1 run validated such an estimator as its ground truth.)
3. **`laplace_log_Z_Mx(..., starts=None)`** — optional list of start dicts;
   runs the existing single-start path per start, keeps the min-Ḡ* result.
   Small addition, mandatory per V1's midpoint-start failures, benefits all
   callers.
4. **`average_gp_posterior(..., weights=None)`** — verified-exact weighted
   moments (default None = uniform, current behavior). Enables reproducing
   legacy LML-weighted figures exactly for the comparison harness; the
   ported scripts' default remains uniform posterior draws.

Each addition gets a regression test: MC vs brute-force grid on a 2-D case
(+ occam sign-convention test); hybrid continuity across the blend window;
`starts` recovers the Sinusoidal optimum the midpoint start misses (pinned
from V1); `weights` vs the viz formula at machine precision; the ESS warning
fires on a starved case.

## 2. Port `model_priors_laplace.py`

- **Spaces**: sigma-free `ModelParameterSpace`s built in-script, mirroring
  the legacy MODELS bounds/parameterizations exactly (NOT
  `build_toy_parameter_spaces`: different bounds, and its sigma param adds a
  flat direction — legacy-figure comparability wins). Legacy positional
  `predict_fn`s converted to dict-based; legacy `inits` become `starts`.
- **Averaged GP** (V2 recipe): `build_model` with matching priors; n>0
  stages: `fit_map` → `fit_gp(method=args.gp_method)` →
  `np.random.seed(seed)` → `extract_gp_predictives` →
  `average_gp_posterior`. n=0 stage: placeholder tensors + `sample_prior` +
  `condition_on_data=False`. `--gp-method` flag: **default `map`** (the
  D9 "clean deterministic demonstrations" case — these are mechanism
  figures; hmc would cost hours per stage post-D12), `vi`/`hmc` selectable.
  Report the retained-draw count per stage (V2 diff v).
- **Z per model**: `hybrid_log_Z_Mx(..., occam=True, starts=legacy inits)`.
  Default is the hybrid even for the fixed-τ=0.3 panels — V1 measured
  0.10–0.25 posterior distortion from pure Laplace there, so matching the
  legacy figures' method would mean matching their known error. A
  `--pure-laplace` flag reproduces legacy behavior for the comparison.
- **Comparison harness**: run the UNTOUCHED legacy script and the port on
  identical data/seeds; emit side-by-side figures + a per-figure delta table
  under `runs/viz_unification/`; deltas attributed to (metric: none —
  identity proven D10) / (estimator: prior-IS→posterior draws) /
  (Z method: pure Laplace→hybrid).

## 3. Port `model_prior_trajectory_laplace.py`

Same spaces/averaged-GP; its `compute_avg_gp`/`compute_laplace_Z`/
`compute_Z_hybrid`/`precompute_G_samples` copies all collapse onto the
package. The τ-sweep figure uses `mc_log_Z_Mx`'s reweighting (Ḡ computed
once per stage) + the Laplace analytic rescale below the window — the
whole sweep costs one Ḡ-precompute per model per stage.

## 4. Close-out

Figure regeneration (system python3 has torch); legacy scripts REPLACED in
place (git history + comparison artifacts preserve the old behavior — they
are the last two self-contained Laplace copies, and keeping them defeats the
unification); disclosure paragraph added to
`docs/inference-and-metric-options.md` (estimator + Z-method changes and why
the new figures are more accurate); codex review of the full diff
(`< /dev/null` on stdin); D16 entry; flip D3 open item (1); check the last
backlog leftovers; PR #2 → Ready.

## Open questions for review

1. Hybrid blend vs single defensive-mixture IS estimator (seam vs machinery).
2. Hybrid-by-default for the fixed-τ=0.3 panels (more accurate, diverges from
   legacy figures) vs pure-Laplace default (matches legacy, known 0.1–0.25
   error) — plan says hybrid-by-default + `--pure-laplace` escape hatch.
3. `--gp-method map` default for figure speed vs `hmc` for thesis fidelity
   (D12's bimodality caveat applies to BOTH: map reports the density mode;
   the figures' role is mechanism illustration, not inference claims).
4. API surface: `starts=`, `weights=`, and a possible `seed=` on
   `extract_gp_predictives` (V2 blocker vi) vs external `np.random.seed`.
