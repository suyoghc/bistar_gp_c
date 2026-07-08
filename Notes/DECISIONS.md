# Decision Log

Tracks what was changed, why, what alternatives were considered, and what's still open.
Convention adopted from `antagonistic_collab/Notes/DECISIONS.md`.

## Conventions

- Entries are numbered sequentially (D1, D2, …) regardless of topic.
- Each entry: `**Problem:**`, `**Decision:**`, optional `**Alternatives considered:**`, and
  `**Result:**` / `**Status:**`. Include commit hashes, `file:line`, flags, and numbers — entries
  are self-contained and are the source text for commit messages.
- Mark unresolved forks `(OPEN)`; update the entry when they close rather than adding a duplicate.
- Update DECISIONS.md in the same commit that makes the change, while context is fresh.

---

## D1: Repo hygiene + first test suite (commit 5d15853, PR #1) — 2026-07-01

**Problem:** 740 tracked files / 72 MB. 254 PNGs, 8 `.npz` HMC caches, 6 slurm logs, and `.DS_Store`
were committed before `.gitignore` existed, so the ignore rules never took effect. Four
byte-identical duplicate scripts. No test suite for numerically delicate GP code.
**Decision:** `git rm --cached` the already-ignored artifacts (files kept on disk); commit
`.gitignore` so it sticks; delete the 4 duplicates (canonical copies kept in `bistar_viz/scripts/`
per README); add `tests/` + a root `conftest.py`. Tracked files 740 down to 458, repo 72 MB down to 11 MB.
**Alternatives considered:** Leave artifacts tracked (rejected: bloat, and ignore rules silently
ineffective). `metrics_v2.py` / `aggregation_v3.py` were left untouched — verified they are the
live modules, not superseded versions.

---

## D2: BMS*/BI* correctness fixes (commits 569ee39, f218dea, 84568fc; PR #1) — 2026-07-01

**Problem:** A multi-agent evaluation plus direct verification found five result-invalidating bugs
in the default pipelines.
**Decision (each fix has a regression test):**
- `soft_transfer` (bms_star.py:435): per-row (per-draw) max shift reweighted GP draws; replaced
  with a single global scalar (posterior-preserving).
- `compute_G_matrix` (bms_star.py:390): `10*max_finite` sentinel is the *best* score for
  negative-valued metrics (pw_nll); replaced with a strictly-worse penalty.
- `AdditiveGPModel` (model.py:25): kernels double-registered via a ModuleList **and** covar_module,
  so HMC saw duplicate latent sites (7 vs 4 for the toy model); hold components in a plain list so
  covar_module is the sole registration path.
- `fit_mcmc_simple` (fit.py:89): used gpytorch's per-datum-averaged MLL, tempering the MH target to
  posterior^(1/n); multiply by n to recover the summed log joint.
- `decompose_model` (debias.py:68): `full_std` summed component covariances, dropping cross terms;
  compute the true sum-kernel posterior covariance instead.
Also added a defensive `period_length` branch in `aggregation_v3.py:330` (not result-invalidating:
`period_length` has no prior, so it is never sampled).
**Result:** 33 tests pass. Verified live: HMC latents 7 down to 4; the soft_transfer distortion was
demonstrated numerically ([0.501, 0.289, 0.210] correct vs [0.476, 0.302, 0.222] as-implemented).

---

## D3: Z_Mx / Laplace model-prior definition and posterior assembly (CLOSED 2026-07-08 — plan committed c5562a3) — 2026-07-01

**Problem:** `laplace_evidence.py::compute_laplace_evidence` computes a Laplace approximation to
`∫ p(y|φ)·exp(−Ḡ/τ) dφ` — a likelihood-weighted joint mislabeled as "model evidence." The paper
defines `Z_Mx` as a **data-free** model prior (README:90; `kb/Wiki/GP-Induced Model Priors.md`:25),
matching the viz reference `model_priors_laplace.py:251`. Verified analytically and numerically:
code output = (proper within-model evidence) + log Z_noOccam. It also feeds
`bistar_sample_size_sweep.py:234` and `bistar_induced_prior_v2.py:208`, producing figures
inconsistent with the viz path.
**Decision (proposed; full spec in `docs/plan-zmx-laplace.md`):** Make the package compute the
data-free `Z_Mx` (expand at argmin Ḡ, Hessian of Ḡ, optional `−log V_ref` Occam term); add the
within-model evidence and an ordinary-evidence primitive; expose model selection as an **ablation
ladder** — baseline (no GP) / Construction I (GP as model prior × ordinary evidence) / Construction
II (GP-induced joint prior, posterior ∝ N(M)) — with **Construction II as canonical**. Unify the
package and viz implementations; migrate the two callers above.
**Alternatives considered:**
- Construction I as canonical: kept only as an ablation. The joint-prior derivation (§2.1–2.2 of the
  plan) shows II is Bayes-consistent and not double counting, which is why II is canonical.
- Leave-as-is / relabel only: rejected — disagrees with the viz `Z_Mx` figures and mislabels the object.
- Occam default: no-Occam (faithful original BI*, README default); with-Occam (`−log V_ref`) shown as
  a sensitivity analysis. The `V_ref` (parameter-box) dependence is a real modeling knob to defend.
**Status (updated 2026-07-01):** Construction II **confirmed canonical** (user). PR #1 merged
(`origin/main` 76df156). **Core implemented + tested** on `fix/laplace-zmx`:
`laplace_log_Z_Mx` (data-free prior, Occam toggle), `laplace_log_evidence_ordinary`,
`laplace_log_evidence_induced` (N/Z_prior), `model_posterior(construction=baseline|I|II)`, and a
robust `_laplace_logdet` (clips eigenvalues to fix the boundary curvature-fabrication issue).
`compute_laplace_evidence` / `compute_all_laplace_evidences` / `LaplaceResult` **removed**; callers
`bistar_sample_size_sweep.py` and `bistar_induced_prior_v2.py` migrated to
`model_posterior(construction="II")` with redesigned decomposition/ablation figures; `laplace_evidence`
now self-registers its default metric (imports `metrics_v2`). Parked eval follow-ups also done:
`pyproject.toml`, dedup `build_toy_kernels`, `InducedPriorResult` collision renamed
(`mechanism.py` renamed it to `CandidateInducedSamples`), optional RNG `seed=` on `fit_mcmc_simple`/`fit_hmc`.
`tests/test_laplace_zmx.py` **42 tests pass** (adds default-metric-registration and
II-decomposition-identity). README Occam section updated to the canonical API + ablation ladder.
**All three open items CLOSED:** (1) ~~unify the two self-contained viz
Laplace scripts~~ DONE — D10 dissolved the single-`G` choice, D15/D16 built the machinery, D17 landed
the ports + comparison harness; (2) ~~regenerate all figures + old-vs-new impact
assessment~~ DONE — impact assessment: toy sections on Della (job 10608943), Mauna local
2026-07-04, post-D11 recheck 523825c; figures: all non-viz sets regenerated 2026-07-08 on
the fixed code via `runs/figures_regen/regen.sh` (detached two-wave orchestrator: the five
`bistar_gp/cache/hmc_samples_*_n500_s42.npz` caches rebuilt fresh — pre-D2 originals
quarantined in `bistar_gp/cache/stale_preD2_20260214/` — then toy_example x2, mauna_loa,
bms_star_mauna_loa + debias (debias fed the properly-sampled cache via `--use-cache`; its
own HMC block still has the pre-D8 init/cap bug, flagged separately), and the five
cache-dependent scripts induced_prior, induced_prior_v2, sample_size_sweep,
v2/v3_comparison; 151 figures, zero errors across 11 logs; the full-data Mauna chain
inherits the D8 convergence caveat). The self-contained sandbox viz scripts
(mechanism_unified, pipeline_figure, model_priors_montecarlo, model_prior_both) import
nothing from bistar_gp, so the correctness fixes never invalidated their outputs — left
as-is; (3) ~~update `kb/Wiki/GP-Induced Model Priors.md`~~ DONE 2026-07-07 — rewritten to
Construction II canonical (ablation ladder, analytic-tau Laplace form, D5 occam
semantics, D16 estimator picture, D17 attribution folded into the trajectory Q&A).

---

## D4: HMC sample-site naming fallout + MH target fixes (fix/laplace-zmx) — 2026-07-01

**Problem:** The D2 single-registration fix renamed every kernel latent from
`kernel_components.{i}.*_prior` to `covar_module.kernels.{i}.*_prior`, but three consumers still
parsed the old names: `extract_gp_predictives` (bms_star.py:269), `decompose_model_hmc`
(debias.py:175), and the seven `hp_pattern` strings in mechanism.py. On any fresh HMC run, every
kernel hyperparameter draw was silently dropped, so GP predictives were built at default-initialized
kernel hyperparameters (only noise varied), invalidating BMS* scoring, decompositions, and mechanism
figures with no error raised. Two related fit.py bugs: (1) `fit_hmc`'s pyro target called both
`model.pyro_sample_from_prior()` and `likelihood.pyro_sample_from_prior()`; the likelihood is an
ExactGP submodule, so the noise prior registered twice (5 latents for 4 toy hyperparameters) and the
phantom `likelihood.noise_covar.noise_prior` column held pure prior draws. (2) `fit_mcmc_simple`
evaluated its MH target in eval mode, scoring `train_y` against the posterior predictive conditioned
on `train_y` itself (data used twice; the D2 `*n` factor amplified the bias); its proposal also
double-counted the noise parameter (same tensor reached via both model and likelihood
`named_parameters()`).

**Decision:** One naming authority in model.py, next to `AdditiveGPModel`: `select_hmc_sites()`
picks the connected latents across archive eras (current runs; legacy duplicate-site archives in
`bistar_gp/cache/*.npz` and `runs/*/samples/`, where `covar_module.kernels.*` and the bare
`noise_covar.noise_prior` were the wired sites; post-fix noise naming
`likelihood.noise_covar.noise_prior`), and `apply_hp_value()` parses and sets one hyperparameter,
accepting current and legacy names. All three consumers migrated onto the helpers; mechanism.py
patterns updated to `covar_module.kernels.*` with `find_hp_key` canonicalizing legacy keys before
matching. fit.py: module-level `_hmc_pyro_model` samples priors exactly once; `_mh_log_joint`
forces train mode on every call; MH parameter list deduped by object identity.

**Alternatives considered:** Patching the three string filters in place (rejected: leaves the naming
logic in three copies, the exact drift that caused this bug). Keeping the separate likelihood
sampling call and filtering the phantom site downstream (rejected: NUTS still wastes work on a
disconnected latent and the samples dict still carries a prior-only column).

**Result:** 56 tests pass (14 new: era selection, value application, a trace of the actual fit_hmc
target, train-mode MH target, `extract_gp_predictives` kernel-draw propagation). End-to-end NUTS
smoke run: 4 sample sites, one noise latent, varying lengthscale draws in the predictives.
**CORRECTION (see D6):** this entry's implication that the HMC path was fully correct was WRONG.
D4 fixed the duplicate noise latent but not the deeper disconnection (`_hmc_pyro_model` scored the
un-sampled model, so NUTS still targeted the prior); the "varying lengthscale draws" smoke did not
distinguish prior from posterior since prior draws also vary. Fixed in D6.
**Consequence:** every committed HMC archive (`bistar_gp/cache/*.npz`,
`runs/mauna_loa_sub150_hmc_*`) predates the D2 fix (biased target, duplicate sites) — regenerate
before quoting paper numbers; the Della impact assessment must rerun on the fixed code.

---

## D5: Reference-volume consistency, τ-invariant Z_Mx clipping, weighted-transfer max shift — 2026-07-02

**Problem:** Three review findings. (1) `laplace_log_evidence_ordinary` always subtracted
`log V_ref` while `Z_Mx` and `N(M)` only did so with `occam=True`, so with `occam=False` (the
default) cross-construction gaps in the ablation ladder absorbed per-model volume differences
(log V_ref: 3.57 Linear vs 7.46 Sin+Linear — a ~49x odds artifact inside what the figure labels
"the GP contribution"). (2) `laplace_log_Z_Mx` minimized f = Ḡ/τ, so the absolute eigenvalue floor
in `_laplace_logdet` fired τ-dependently (τ-sweeps bent for numerical, not statistical, reasons),
and `_laplace_log_integral` discarded `n_clipped` — a floored flat direction silently adds
−½·log(1e-8) ≈ +9.2 nats of evidence. (3) `aggregation_v3.soft_transfer_weighted:402` kept the
per-candidate (axis=0) max shift that D2 removed from `bms_star.soft_transfer`; two candidates with
equal weighted Boltzmann mass got 0.434/0.566 instead of 0.50/0.50 (pre-existing on `main`, reached
via `run_weighted_bms_star` from `experiments/bms_star_v3_comparison.py`).

**Decision:** (1) `laplace_log_evidence_ordinary` gains `occam=True` (standalone default keeps the
proper marginal-likelihood semantics); `model_posterior` threads its `occam` flag into every
construction. The flag now has one module-wide meaning: include the −log V_ref term of the
normalized uniform reference prior; `occam=False` integrates against the raw Lebesgue measure
everywhere (faithful no-Occam BI*). (2) `Z_Mx` optimizes and differentiates Ḡ itself and applies τ
analytically — log Z = −Ḡ*/τ + (d/2)log(2πτ) − ½log|H_Ḡ|, the identity the module header already
documented — so clipping decisions are τ-invariant by construction; `n_clipped` now propagates into
`ZMxResult`/`EvidenceResult`/the Construction-II components with a logger warning. Floor/cap values
unchanged (pinned by tests; intentional mitigation per D3). (3) Global scalar max shift in
`soft_transfer_weighted`, mirroring the D2 fix and comment.

**Alternatives considered:** A floor relative to the largest eigenvalue (τ-invariant and
scale-aware) was rejected: with the 1e12 cap in place a fabricated cliff eigenvalue would drag the
floor up to ~1e3 and corrupt genuine O(1) curvature. Making `numerical_hessian` bounds-aware was
deferred — the review's verifier showed the sentinel-cliff path is unreachable with the shipped
parameter spaces, so surfacing the diagnostic is the honest fix.

**Result:** 63 tests pass (7 new: volume-free construction gaps under a constant metric, occam
toggle on the ordinary evidence, exact analytic τ-scaling checked at τ=1e12, flat-direction
`n_clipped` flag, weighted-transfer direct formula / equal-mass 0.5-0.5 / global-offset invariance).
Live demo on the toy spaces: II−baseline gaps no longer track log V, and the new warning immediately
surfaced a real flat direction at Sin+Linear's joint MAP (1 of 6 eigenvalues floored) that was
previously invisible.

---

## D6: fit_hmc sampled the prior, not the posterior (multi-model review catch) — 2026-07-02

**Problem:** Before the Della re-validation, a 5-model review panel (Gemini 3.1 Pro, Kimi K2-thinking,
GLM-5.2 via OpenRouter; codex/gpt-5.5 on the real repo; Fable adjudicating) reviewed the D3–D5 diff.
codex — alone among the panel — caught that `_hmc_pyro_model` discarded the return value of
`model.pyro_sample_from_prior()`. In gpytorch 1.15.1 that method deep-copies the model, applies the
sampled hyperparameters to the COPY, and returns it; the original `model`/`likelihood` are unchanged.
The target scored `likelihood(model(x))` on the ORIGINAL module, so the obs likelihood was independent
of the sampled latents and NUTS targeted the **prior**: every `fit_hmc` "posterior" draw was a prior
draw. **Pre-existing** — main's inline `pyro_model` had the same discard pattern (plus the duplicate
noise latent D4 removed); the D4 change fixed the duplicate latent but not the disconnection, and the
D4 regression test passed because it checked latent-site COUNT, not whether obs depends on the latents.

**Decision:** `_hmc_pyro_model(model, x, y)` now scores through the returned module:
`sampled = model.pyro_sample_from_prior(); pyro.sample("obs", sampled.likelihood(sampled(x)), obs=y)`.
Dropped the now-unused `likelihood` parameter (caller `partial(_hmc_pyro_model, model)`). Added
`test_hmc_target_connects_latents_to_likelihood`: conditions the latents at two values and asserts the
obs log-prob MOVES (the check a site-count test cannot do). Site names are unchanged, so
`select_hmc_sites`/`apply_hp_value` and archive compatibility are unaffected.

**Verification:** Direct experiment (orchestrator + Fable, independently): conditioning obs on
latents 0.5 vs 2.5 gave an identical obs log-prob under the old target (disconnected) and a moving
one under the fix (connected). gpytorch source confirms the copy semantics; the original
`likelihood.noise` is unmutated after the call. **66 tests pass** (1 new connection test; D4 trace
test updated to the new signature).

**Panel notes (recorded, not fixes):**
- Kimi's sole CRITICAL — "MLL is summed, so ×n over-inflates by n" — is a FALSE POSITIVE for
  gpytorch 1.15.1: `ExactMarginalLogLikelihood.forward` ends `res.div_(num_data)`, so it is per-datum;
  measured `mll=−1.61686`, `mll×n=−48.50574=` the independently summed log joint. The D5 (D2) `×n` fix
  is correct. Gemini and GLM agreed.
- `fit_mcmc_simple` proposes in raw unconstrained space while scoring constrained-space priors without
  the constraint Jacobian (codex MEDIUM, GLM): **pre-existing**, and `fit_mcmc_simple` is documented as
  a non-production starting point (fit_hmc/NUTS is production). Non-blocking follow-up.

**Consequence:** independently reconfirms that **all committed HMC archives** (`bistar_gp/cache/*.npz`,
`runs/mauna_loa_sub150_hmc_*`) are prior-only and MUST be regenerated on the fixed code before any
paper number is quoted. Panel verdict was NO-GO on the pre-fix branch; GO after this fix.

---

## D7: prior/posterior predictive sampling (one pipeline, two checks) — 2026-07-02

**Problem:** The core package could only sample the posterior (`fit_hmc`); prior sampling existed
only as scattered numpy reimplementations in `bistar_viz/scripts/`. A prior predictive check (are the
GP's prior beliefs — the ones BI* transfers into `Z_Mx` — reasonable before seeing data?) and a
posterior predictive check (does the fitted GP reproduce the data?) had no shared, first-class path.
Motivated by the D6 finding: the bug was accidentally producing prior draws via NUTS, i.e. prior
sampling done the expensive/wrong way.

**Decision:** Two minimal additions that share the existing predictive pipeline and the `fit_hmc`
dict schema.
- `fit.py::sample_prior(model, n_samples, seed)` — i.i.d. draws from the registered priors by
  tracing `model.pyro_sample_from_prior()`; **no NUTS** (the priors are known distributions, so draws
  are exact and ~instant), values in the same constrained space `fit_hmc`/`apply_hp_value` use.
- `bms_star.py::extract_gp_predictives(..., condition_on_data=True)` — `True` (default) keeps the
  posterior predictive p(y*|X,y,θ); `False` gives the prior predictive p(y*|θ) = GP prior at x_eval
  (ZeroMean gives mean 0, cov K_θθ(x_eval)+σ²I), no conditioning on data.
So: the prior predictive check feeds `sample_prior` into
`extract_gp_predictives(condition_on_data=False)`; the posterior predictive check feeds
`fit_hmc` draws into `extract_gp_predictives(...)`.

**Alternatives considered:** Sampling the prior via NUTS (rejected — wasteful and can mix poorly;
i.i.d. is exact). Unifying the scattered `bistar_viz/scripts/` prior-predictive reimplementations
into this path (deferred — tangled with the still-open single-`G` metric decision that blocks the
other viz-unification work). A `.rsample()`-style helper drawing actual y* realizations (deferred —
callers can draw from the returned Gaussians; keep the addition minimal).

**Result:** 72 tests pass (6 new: prior-sample schema/i.i.d./data-freeness, prior-predictive exact
analytic covariance + zero mean + data-independence, posterior-predictive data-dependence,
posterior≤prior variance invariant). Adversarially reviewed (independent agent, ran its own checks:
constrained-space match vs a real HMC run, NaN-train leakage test, exact-covariance sensitivity) —
verdict SHIP, no defects.

---

## D8: taming the Mauna Loa NUTS funnel (init_to_map + max_tree_depth) — 2026-07-03

**Problem:** Post-D6, fit_hmc targets the real posterior, and the Mauna Loa run became
intractable: Della job 10584302 timed out at 14/400 warmup iterations, step size collapsing
from 7.2e-01 to 3.3e-07 with tree depth saturating (~72 min/iteration). Diagnosis: the noise
posterior genuinely concentrates near zero (monthly-averaged CO2 is nearly noiseless;
posterior noise ≈ 7e-4 ± 1e-4 normalized), so the stiff region IS the typical set — the
sampler cannot avoid it, and uncapped depth-10 NUTS trees (up to 1023 leapfrog steps, each a
Cholesky + backward) explode per-iteration cost. Head-to-head at SUB=30 (28 iterations):
tree-cap=7 + MAP-init 29.2s (1.04 s/it) vs MAP-init alone 230.7s vs old behavior 138.2s —
the CAP is the operative fix (MAP-init alone starts in the stiff region and is slower);
all three configs agree on the posterior (noise 0.0006–0.0007 ± 0.0001), consistent with
max_tree_depth being bias-free (it shortens trajectories, not the stationary distribution).

**Decision:** `fit_hmc` gains `init_to_map=True` (init each latent at the model's current
constrained value via pyro `init_to_value`; named_priors name == sample-site name, proven by
a transforms round-trip test) and `max_tree_depth=10` (pyro default, now exposed).
`impact_assessment.mauna()` passes `max_tree_depth=7` via `inspect.signature` dispatch (NOT
try/except TypeError, which would swallow an internal TypeError and silently rerun uncapped);
the old worktree arm keeps its signature — and is fast anyway since pre-D6 it samples the
prior. `experiments/bms_star_mauna_loa.py` and `experiments/mauna_loa.py` now MAP-fit the
model actually passed to fit_hmc (they used to fit one model and pass a fresh default one)
and set `max_tree_depth=7`.

**codex review (FIX-FIRST, then fixed):** (1) CONFIRMED: a constrained value that underflows to
exactly 0 sits INSIDE the closed support GreaterThanEq(0) yet maps to -inf under
biject_to(support).inv, so pyro retries the same fixed init until "cannot find valid initial
params" — reproduced, then fixed by checking finiteness of the unconstrained image (support
membership is the WRONG predicate), clamping into the interior, and falling back to
init_to_sample with a warning if still invalid. (2) The two stale experiment call sites above.

**Result:** 75 tests pass (3 new: kwargs smoke, init_to_value transforms round-trip,
boundary-underflow survival). Projection for Della: ~0.1 s/leapfrog at SUB=150 × ≤127 steps
≈ ≤13 s/it, so 400 iterations ≈ 90 min (was: >8 h timeout). Note for the paper: any change to
the NOISE PRIOR itself (e.g. bounding it away from zero) is a modeling decision, deliberately
not taken here — these are pure sampler-efficiency knobs.

**Status (updated 2026-07-03, mixing validation — IMPORTANT QUALIFIER):** Two independent
2-chain validations (sub=60; capped depth-6, warmup 100; and capped depth-8 + DENSE adapted
mass, warmup 200) show the capped sampler is fast and divergence-free but does NOT mix within
hundreds of iterations: ESS ≈ 1 and split-R̂ 4–81 on every kernel hyperparameter (chains rest
at trend lengthscale 8 vs 32 with a 418-nat log-joint gap between their mean points — a stuck
chain, not a benign flat ridge or genuine multimodality). The one healthy direction is the
NOISE (R̂ 1.06, ESS 12), which is what this entry's "configs agree" check measured — so the
depth cap is bias-free in principle but the practical chains are far from stationarity in the
lengthscale/outputscale directions. Dense mass adaptation does not rescue it (5× cost, same
ESS=1): the curvature is position-dependent, so no constant mass matrix conditions it.
**Implication:** a capped Della `--mauna` run is valid for the D6 old-vs-new IMPACT story
(old arm = prior draws, new arm = data-informed draws near the MAP — a large, honest,
qualitative shift) but its kernel-hyperparameter "posteriors" must carry a non-convergence
caveat and are not paper-grade. Paper-grade full-Bayes on Mauna Loa needs one of: (a)
Laplace-preconditioned NUTS (FIXED inverse mass from the MAP Hessian, adaptation off — the
one cheap sampler idea not yet tried; adapted-mass failure does not rule it out), (b)
reparameterization (significant work), or (c) rescoping full-Bayes mauna out of the paper's
figures (MAP + Laplace machinery, the paper's primary path, is unaffected). (OPEN — fork
belongs to the user.) Diagnostics: scratchpad nuts_diag_out/{validate,round2_dense}.json.

**Status addendum (2026-07-08, debias-script chip):** a third stale call site surfaced during
the D3 figure regeneration: `experiments/bistar_debias_mauna_loa.py` MAP-fitted a throwaway
`model_map`, then passed a fresh default-init `model2` to `fit_hmc` with no depth cap.
Since `init_to_map` reads the current values of the model actually passed, standalone fresh
debias runs started from default hyperparameters under uncapped depth-10 NUTS. Fixed to the
D8 pattern (MAP-fit `model2` itself, n_iter=300, then `fit_hmc(..., max_tree_depth=7)`);
`--use-cache` behavior unchanged. The regenerated figures were unaffected because the debias
run consumed cached bms_star draws via `--use-cache`. New source-level guard
`tests/test_experiment_hmc_pattern.py` (AST) checks both knobs in all three Mauna scripts and
fails on the pre-fix source; after an adversarial review found name-only matching escapable
(cross-branch match after a model2 rename; rebinding between fit_map and fit_hmc), the guard
requires the matching fit_map to be a sibling statement in fit_hmc's block with none of the
four tracked names rebound in between — all escape mutants verified caught. The mixing qualifier above still applies; the prior-sensitivity
study stays open.

---

## D9: GP inference as selectable options, thesis-anchored default (fit_gp) — 2026-07-04

**Problem:** The user wants every methodological choice explicit and selectable, with defaults
matching the thesis chapter (Chandramouli 2020 Ch. 5). For GP hyperparameter inference the chapter
prescribes full-Bayes sampling of the joint posterior (p. 172–173) — Appendix II (p. 221): VI
(gpflow) was the PRIMARY implementation, HMC (GPy) the cross-check, "similar" results, 10k samples /
1k burn-in — with MAP/MMLE as the explicitly-contrasted simpler alternative (Fig. 6 vs 7a). The repo
only exposed fit_hmc (+ fit_map separately, different output shape).

**Decision:** `fit.py::fit_gp(model, lik, x, y, method=...)` — every method returns the SAME dict
schema as fit_hmc (site name mapped to a (n,) constrained array), so options flow through
extract_gp_predictives/BMS*/decompose unchanged and are directly comparable:
- `"hmc"` (DEFAULT): existing NUTS path with D8 knobs. Thesis-equivalent (validated cross-check);
  chosen over literal-primary VI because it is the path this codebase has verified end-to-end
  (D6 connection test, D8).
- `"vi"` (fit_vi): ADVI-style pyro SVI, AutoMultivariateNormal guide in unconstrained space,
  MAP-initialized via the shared init_to_value machinery. The thesis's literal primary method;
  funnel-immune (pragmatic recommendation for Mauna until the D8 mixing fork closes).
- `"map"` (fit_map_samples): MAP/MMLE as length-1 arrays — the thesis's contrast case, now
  pipeline-compatible (degenerate posterior).
- `"hmc_laplace"` (fit_hmc_laplace): NUTS on the Laplace-whitened posterior z = A⁻¹(u−u_MAP),
  A = chol(H⁻¹), H = MAP Hessian of the potential in unconstrained space via initialize_model +
  autograd; eigenvalue floor 1e-6; falls back to identity whitening with a warning. NOTE: a linear
  reparameterization ≡ mass-matrix preconditioning, so this single option delivers both the
  "Laplace-preconditioned NUTS" and "reparameterized HMC" items; a NONLINEAR reparameterization
  (e.g. signal-to-noise) remains the open D8 fork.

**Result:** 84 tests pass (9 new: per-method schema/finite/positive, MAP point-estimate equality,
VI concentrates vs prior (noise sd ≪ prior sd), pipeline flow-through for map/vi, unknown-method
error, plus the D10 identity below). Justification writeup for the paper:
`docs/inference-and-metric-options.md`.
**codex review (FIX-FIRST, then fixed the same day):** (1) the D8 boundary guard existed only in fit_hmc's
inline init loop, so an underflowed-to-zero hyperparameter crashed the NEW vi/hmc_laplace init paths
— `_map_init_values` is now the single guarded authority (biject_to-finiteness clamp, ValueError if
irreparable; fit_hmc falls back to init_to_sample), with boundary regression tests for both paths.
(2) fit_hmc's `.squeeze()` returned 0-d arrays at n_samples=1, breaking the (n,) schema promise and
crashing extract_gp_predictives — now `.reshape(-1)`, pinned by a test. (3) the VI concentration test
could pass with n_steps=0 (MAP init alone) — replaced with a fresh-model learn-vs-no-learn contrast
(n_steps=0 stays at init 0.69; 400 steps drops below 0.2), so a future detached-gradient regression
fails the test. codex independently verified the ELBO gradient path through gpytorch's
setting_closure is alive, and hmc_laplace's flatten/whiten/transform round-trip is correct.
88 tests pass.

---

## D10: the "single-G decision" dissolved — viz metric ≡ pw_kl_vcal — 2026-07-04

**Problem:** The viz-script unification (D3 open item) was blocked on choosing a single canonical G:
the viz scripts use a "pointwise variance-weighted MSE" while the package default METRIC is
pw_kl_vcal — believed to be different quantities requiring a paper-level decision.

**Decision/Finding:** They are the SAME function. viz `compute_G` = mean((μ_GP−μ_θ)²/(2σ²_GP));
`pw_kl_vcal` = mean(0.5(μ_θ−μ_ψ)²/σ²_ψ) = KL(N(μ_ψ,σ²_ψ)‖N(μ_θ,σ²_ψ)) — identical formulas
(viz adds only a 1e-6 variance floor). Verified numerically to 1e-12
(tests/test_fit_gp_options.py::test_viz_variance_weighted_mse_is_pw_kl_vcal). Consequences:
(1) the package default is simultaneously a KL variant — the thesis's named family (Ch.5 p.174–175:
metric "chosen by the investigator… one or another variant of KL divergence") — AND numerically
identical to what the viz-reference figures used; the default needs NO change and satisfies both
anchors at once. (2) The metric option family already exists (METRICS + metrics_v2 with
justification-grade docstrings: variance-calibrated / mean-only / GP-anchored); documented per-option
in docs/inference-and-metric-options.md. (3) The residual viz/package difference is upstream and
estimator-level only: viz importance-weights PRIOR hyperparameter draws by marginal likelihood, the
package uses genuine posterior draws with uniform weights — same mixture-of-Gaussians target, same
mixture-moment formulas (compute_averaged_gp vs aggregation_v3.average_gp_posterior), better
estimator in the package. Viz unification is therefore UNBLOCKED: port the scripts onto
laplace_log_Z_Mx with metric_name="pw_kl_vcal" and posterior draws.
**Thesis nuance recorded for the paper:** the chapter's aggregation is hard best-match assignment
(p. 174); the package's soft-τ Boltzmann transfer is the practical relaxation (recovering it in the small-τ limit).
**Scope qualifier (codex review):** the identity holds for GP pointwise variance ≥ 1e-6; below that
the implementations' variance FLOORS differ (viz clips at 1e-6, package `_extract_marginals` at
1e-10) and they diverge by the floor ratio — pinned in
`test_viz_and_package_floors_diverge_below_1e6_variance` and qualified in the docs. For the viz
unification, adopt the package floor (closer to the un-floored mathematics).

---

## D11: candidate MLE restart selection was a no-op — Sin+Linear never found the sinusoid — 2026-07-05

**Problem:** The D12 comparison run produced near-uniform BMS* posteriors across
Linear/Sin+Linear/Quadratic for every pointwise metric, which traced back to
`bistar_gp/candidates.py`: the multi-start restart pickers in `SinusoidalModel.fit` and
`SinLinearModel.fit` compared restarts by the residual term `0.5*sum(r^2)/sigma^2` alone.
At any converged MLE `sigma^2 = mean(r^2)`, so that quantity equals `n/2` for EVERY restart
(measured: 9.9923–10.0001 across the four omega inits at N=20) — selection degenerated to
optimizer-noise tie-breaking and always kept the FIRST restart (`omega_init=0.5`). On the
thesis toy data that basin is degenerate: Sin+Linear "fit" A=116.8, omega=0.0336 (a giant
near-zero-frequency sinusoid, locally a straight line), sigma=0.6877 vs Linear's 0.6995 —
the true-model candidate was effectively a second Linear model. The omega_init=1.0 restart
finds the truth (omega=1.0302, sigma=0.3212, full NLL 5.67 vs 20.88) but could never win.

**Decision:** `_fit_mle` now returns `(params, nll)` where nll is scipy's `result.fun` — the
FULL Gaussian negative log likelihood including the `0.5*n*log(2*pi*sigma^2)` term — and all
restart pickers compare that. Six call sites updated: four in `candidates.py` plus
`mauna_loa_candidates.py::QuadSinModel.fit`/`QuadHarmonic2Model.fit` (codex pre-commit
review caught the latter two, which had BOTH the same restart no-op AND a tuple-unpack
breakage from the signature change that the broad `except Exception` would have silently
converted into fallback fits — pinned by
`tests/test_candidates.py::test_mauna_candidates_use_tuple_return_and_recover_params`).
Post-fix on the thesis toy:
Sin+Linear recovers A=0.886, omega=1.030, b=0.251, sigma=0.321 (true-parameter residual sd
0.354); Sinusoidal legitimately uses a long-period sine (A=2.45, omega=0.122) to mimic the
linear trend it cannot otherwise represent.

**Alternatives considered:** comparing restarts by sigma alone (equivalent at the MLE but
less explicit); scipy multi-start via `basinhopping` (heavier dependency for the same fix).

**Result:** regression tests in `tests/test_candidates.py` (parameter recovery on the thesis
toy + a test pinning that `_fit_mle`'s returned nll includes the log-variance term and that
the residual-only criterion equals n/2 at the MLE; Mauna tuple-return + parameter recovery).
91 tests pass. Every previous result that
consumed `build_toy_candidates()` output on the toy problem inherited the degenerate
Sin+Linear (and Sinusoidal) fits; the D12 comparison was rerun on the fixed candidates
(GP-side draws unaffected — fit_gp is independent of candidates).
**Mauna recheck (2026-07-07, `d9efaaa`):** the real-data reversal headline
(docs/impact-assessment-results.md) SURVIVES the fix. Re-run of
`impact_assessment --mauna` at identical seed/settings reproduces the HMC side
bit-identically and shifts every BMS* posterior entry by at most 0.00002
(Quad+2Harm stays 0.42218 vs Linear 0.11368 at pw_kl_forward@tau1). All 12 restarts
of each Mauna candidate converge to one basin (frequencies fixed a priori; full NLLs
within ~1e-4), so the pre-fix first-restart selection was already optimal there —
the toy's multi-basin omega pathology does not transfer. Raw:
`runs/mauna_recheck_postD11.json`; recheck subsection added to the impact doc.

---

## D12: method × metric comparison on the thesis toy — bimodal posterior; VI fails model selection; defaults confirmed for hmc + pw_kl_vcal — 2026-07-05

**Problem:** D9/D10 exposed inference methods and G metrics as selectable options with
thesis-anchored defaults, deliberately deferring the empirical choice ("choose based on
results", docs/inference-and-metric-options.md §3). This entry records that comparison:
all four `fit_gp` methods × five metrics (pw_kl_vcal, pw_nll_gp, pw_kl_mean,
pw_hellinger_vcal, kl_forward) on the thesis toy (sin(x)+0.25x, N=20, `informative` priors),
full BMS* pipeline, 2000 draws/method (thesis App. II scale deviation disclosed).
Tables: `docs/fit-method-metric-comparison.md` (generated by
`experiments/fit_method_metric_comparison.py`; raw draws cached under
`runs/fit_method_metric_comparison/samples_*.npz` so candidate/metric/τ changes never
re-pay sampler hours). First attempt (12 h) was invalidated by the D11 candidates bug;
rerun on fixed candidates from the same cached draws (seeds deterministic — rerun
reproduced run-1 hyperparameter summaries to 4 decimals).

**Findings:**
1. **The hyperparameter posterior is bimodal** under the `informative` priors
   (evidence chain: `experiments/toy_posterior_mode_analysis.py`). Both modes verified as
   genuine local maxima of the exact log joint (D13 adjudication): low-noise mode = the MAP
   (noise 0.0736, ls 2.18, log joint −33.4, the global DENSITY mode; the HMC mean noise≈0.053
   is a typical-set point in its basin, not the mode itself) with the best data fit
   (log ML −23.4) but prior-penalized; high-noise mode (noise 0.5917, ls 8.43, log joint
   −36.8) prior-favored, worst fit; valley ≈ −43 between them. **Mass: the high-noise basin
   holds ~3× the posterior mass** (prior-IS P(noise>0.30)=0.67 vs P(noise<0.15)=0.19;
   codex Sobol integral 0.63/0.24 — CORRECTED in D13; the original "65–81% in the likelihood
   mode" figure came from the Jacobian-less fit_mcmc_simple measure and was wrong). The
   truth-ish hyperparameters score worst of all probed points (log joint −57.2): the
   `informative` config actively fights this data's scale — a prior sensitivity point for
   the paper.
2. **HMC and hmc_laplace sample ONLY the low-noise/density-mode basin**
   (P(noise<0.15)=1.000, both — a MINORITY of posterior mass); **VI converges stably to
   ONLY the dominant high-noise basin** (P=0.000; identical across seeds 0/1/2 and 5k/20k
   steps — a converged ELBO optimum that MIGRATES from its MAP init, noise 0.074 to 0.57,
   toward the larger-mass basin). Thesis App. II's "VI ≈ HMC" does NOT replicate here:
   hyperparameter means 2.4–14.8 pooled-SDs apart, and NO single method reports the full
   bimodal posterior.
3. **Model selection:** hmc/map/hmc_laplace select Sin+Linear (true) under EVERY metric —
   hard best-match (the thesis's own aggregation) is unanimous 200/200 draws. **VI selects
   Sinusoidal** (78.5% of draws, pointwise metrics; kl_forward flips to Linear and is
   τ-unstable): its smooth high-noise-basin GPs are best matched by the long-period sine.
   Honest framing (D13): the true-model selection comes from the MINORITY-mass basin; a
   mass-faithful full-Bayes answer under these priors would weight the smooth basin ~3:1
   and lean toward VI's (wrong-model) conclusion. The failure is PRIOR MISSPECIFICATION
   expressed through method choice, not "VI is broken" — each single-basin method reports
   a different half of a posterior whose dominant mass contradicts the truth.
4. **Metrics (within hmc):** pw_kl_vcal ≡ pw_nll_gp in practice (0.675 vs 0.677 at τ=1 —
   the log-variance term is ≈constant across draws); pw_kl_mean much flatter (0.284:
   dropping GP-variance weighting costs discrimination); pw_hellinger_vcal intermediate
   (0.326, bounded); kl_forward sharpest (1.000) but most brittle under the bad posterior
   (VI row). τ matters more than the pointwise-metric choice: at τ=0.1 pw_kl_vcal reaches 1.000;
   hard assignment is scale-free and unanimous.
5. **Cost:** hmc 5.6 h / hmc_laplace 5.8 h (uncapped depth-10 NUTS, trees saturating —
   the bimodal geometry is stiff; within-mode ESS only 4–37, single-chain Geyer) vs
   vi 38 s vs map 2 s. MAP+pw_kl_vcal reproduces the full-Bayes conclusion at ~1/10,000th
   the cost (0.589 vs 0.675, same winner). Laplace whitening did NOT fix mixing (ESS 14–37
   vs 4–27): the obstacle is global bimodality, not local conditioning — which also predicts
   the D8 fork's option (a) (Laplace-preconditioned NUTS) won't rescue Mauna.

**Decision (defaults, user to ratify — sharpened by the D13 correction):** keep
`metric_name="pw_kl_vcal"` (thesis KL family; empirically equivalent to pw_nll_gp, more
discriminating than mean-only/bounded variants, far more stable than joint kl_forward) —
this choice is unaffected by the correction. The METHOD default is now a genuine judgment
call the user must make: `hmc` (MAP-init) reproduces the thesis-style answer and selects
the true model, but it reports the MINORITY-mass basin (the global density mode); VI
reports the DOMINANT-mass basin, which under these misspecified priors selects the wrong
model; no offered method reports the full bimodal posterior. Framing options: (a) keep
`hmc` as default on the grounds that the density-mode basin is the scientifically useful
answer here and disclose the mass split; (b) treat the toy as evidence the `informative`
priors need revision (truth-ish log joint −57 vs −33 MAP), after which the bimodality may
dissolve and the method choice may stop mattering. Either way both methods need the
basin-occupancy check (`toy_posterior_mode_analysis.py` §5) as a standard diagnostic, and
the earlier "VI pragmatic for Mauna" suggestion inherits the mode-check caveat. MAP is the
honest fast path when hyperparameter uncertainty is not the point.

**Ratified (2026-07-07, user):** `metric_name="pw_kl_vcal"` confirmed as the default;
`kl_forward` moves to the paper appendix as a covariance-sensitive stress-test metric.
Method fork resolved as "both": `hmc` stays the package/paper-draft default with the
mass split disclosed and the basin-occupancy check required as a standard diagnostic;
a prior-sensitivity / re-elicitation study on the `informative` config is queued before
final paper numbers. VI framed as the bimodality/prior-sensitivity diagnostic, not a
failed method. Full writeup-facing rationale and paper phrasing in
`Notes/WRITEUP_DECISIONS.md` W1–W3 (local, gitignored).

**Status (closed same day):** capped-NUTS arm (`--max-tree-depth 7`, the D8-validated knee)
done — `docs/appendix-tree-depth-cap.md`. The cap is result-preserving at model-selection
precision on the toy (max posterior shift 0.0015 hmc / 0.0108 hmc_laplace, hard assignment
unchanged 200/200) at ~9× lower cost (5.6 h down to 39 min); within-mode ESS per draw comparable
or better; both capped chains stay in the likelihood mode (P(noise<0.15)=1.000) — the cap
neither causes nor cures mode-blindness. Caches/outputs tagged `_td7`; uncapped canonical
files untouched.

**Correction (2026-07-05, same day — post-commit codex verification, adjudicated):** the
findings above were EDITED IN PLACE after an independent codex verification pass (prompt
targeted the five scientific claims; commit 0d49a1e carries the original wording) refuted
the mass story: the original "majority of mass 65–81% in the likelihood mode" was an
artifact of the fit_mcmc_simple raw-space measure (missing softplus Jacobian — D13), and
the true constrained posterior puts ~3× the mass in the HIGH-noise basin. Fable
adjudication upheld the refutation with independent methods (Nelder-Mead high-mode search
matching codex's mode to 4 decimals; prior importance sampling 0.19/0.67 vs codex Sobol
0.24/0.63). Consequently the causal framing flipped: VI migrates to the dominant basin,
HMC/MAP report the minority density-mode basin; "VI selects the wrong model" became a
prior-misspecification story. codex's remaining verdicts: bimodality CONFIRMED (with the
MAP-vs-HMC-mean coordinate correction), decompose() CONFIRMED to 1e-12 (constrained-space
priors, no Jacobian in gpytorch's MLL prior term), model-selection scoring CONFIRMED clean
(no inf-sentinel involvement; VI's Sinusoidal pick traced to real predictive shapes:
GP-mean MSE Sinusoidal 0.0095 vs Sin+Linear 0.3487 under the high-noise basin).

---

## D13: fit_mcmc_simple sampled the wrong measure — raw-space MH without the change-of-variables Jacobian — 2026-07-05

**Problem:** `fit_mcmc_simple` proposes on RAW (unconstrained) hyperparameters but accepted
on `_mh_log_joint` alone, which evaluates the posterior density in CONSTRAINED space
(gpytorch adds `prior.log_prob` at the constrained value; no Jacobian anywhere). The
missing factor is Π|d constrained/d raw| = Π sigmoid(raw_i) for Positive()/softplus — for
small θ this ≈ θ, so omitting it INFLATES small-hyperparameter regions. Known since the D6
multi-model review as a "pre-existing non-blocking follow-up"; it became result-relevant
when D12 used fit_mcmc_simple as the mass referee on the bimodal toy posterior: the
uncorrected measure reported 65–81% of mass at noise<0.15 when the true split is ~0.19/0.67
the other way (codex caught it by reproducing the uncorrected numbers from the
Jacobian-less measure via Sobol integration; verified independently by prior importance
sampling, which needs no chain at all).

**Decision:** `fit.py::_raw_log_jacobian(model, param_list)` — sums log|d transform/d raw|
over constrained scalar params, resolving each constraint by gpytorch naming convention
(`raw_X` resolves to the owning module's `raw_X_constraint`) and differentiating `constraint.transform`
by autograd (handles any elementwise constraint; unconstrained params contribute 0).
`fit_mcmc_simple.log_posterior` now adds this term. Pinned by
`tests/test_candidates.py::test_raw_log_jacobian_is_log_sigmoid_for_positive`
(softplus′ = sigmoid analytic identity on the toy model's four sites). NOTE: even
corrected, a single RW-MH chain remains a POOR mass estimator here (valley crossings are
rare; corrected per-chain splits scatter 0.06–0.56 across seeds) —
`toy_posterior_mode_analysis.py` therefore uses prior importance sampling as the mass
authority and keeps MH only as basin-crossing evidence. Pyro-side samplers (fit_hmc,
fit_vi, fit_hmc_laplace) are unaffected: pyro's biject_to machinery applies Jacobians
correctly.

**Alternatives considered:** closed-form logsigmoid for softplus only (rejected: silently
wrong for any future Interval constraint); fixing only the analysis script and leaving the
package sampler biased (rejected: the D12 episode shows a mislabeled measure WILL be
reused).

**Result:** 92 tests pass. D12 findings corrected in place (see its Correction block);
`experiments/toy_posterior_mode_analysis.py` restructured (exact-mode optimization as the
bimodality proof, prior-IS as the mass authority, corrected-MH demoted to mixing evidence);
`docs/inference-and-metric-options.md` §3 reworded. Downstream caveat: any past result that
used fit_mcmc_simple draws quantitatively (old impact-assessment sections compare old-code
vs new-code chains, both now superseded) should be treated as raw-measure numbers.

---

## D14: cleanup-backlog batch 1 — hygiene + test-invocation workflow change — 2026-07-06

**Problem:** The 2026-07-01 8-angle review's severity-2 backlog (reconstructed and
annotated against the tree in commit 20bd7c8; live checklist in Notes/SCRATCHPAD.md) held
a batch of mechanical items independent of the viz-unification work, including two flagged
severity-1s never previously addressed.

**Decision (batch 1, no numerics touched):**
- `bistar_gp/laplace_evidence.py`: removed unused imports `build_toy_parameter_spaces`,
  `average_gp_posterior` (S1); `metrics_v2` self-registration import untouched.
- Right-arrow characters purged from prose per the global style rule (S1): all 16 in
  `Notes/DECISIONS.md`, 4 in `docs/inference-and-metric-options.md`, and the prose lines
  of `Notes/SCRATCHPAD.md` (the backlog checklist's own tag notation left as-is — it is
  ephemeral by design).
- Prose nits: README `Z_Mx` label-pattern sentence rewritten with an active verb;
  `docs/plan-zmx-laplace.md` "ingredients" metaphor replaced.
- 6 committed `.pyc` artifacts under `experiments/practice_EvansEtAL/__pycache__/`
  untracked (`git rm --cached`; `.gitignore` already covers `__pycache__/`).
- `experiments/impact_assessment.py`: the pyro latent-site trace block duplicated between
  `collect()` and `mauna()` extracted into `_latent_sites(model)` (lazy pyro import
  preserved; verified count 4 on the toy model).
- `bistar_viz/scripts/bistar_sample_size_sweep.py`: dead per-n_sub `spec.mle_value`
  mutation removed (verified: `laplace_evidence` reads only the explicit `mle_params`
  dict; `spec.mle_value` matters only for `induced_prior` plotting the sweep never calls).
- **Workflow change:** root `conftest.py` sys.path shim REMOVED per its own removal note —
  the package is now installed editable (`pip install -e . --no-deps`, miniconda base).
  Anyone running tests in a fresh environment needs that install once; both
  `python3 -m pytest` and bare `pytest` verified green after removal.

**Result:** 92 tests pass. Remaining backlog (laplace_evidence efficiency/duplication
cluster, construction guard, bounds-aware hessian S3-PLAU, induced_prior_v2 re-run item,
test_laplace_zmx param-space duplication) is batch 2, folded into the viz unification.

---

## D15: cleanup-backlog batch 2a — laplace_evidence efficiency/duplication cluster — 2026-07-06

**Problem:** The backlog's laplace_evidence.py cluster (11 items): five copy-pasted
noise-guard/0.3-default sites that could silently desync the three Laplace objectives;
plot_ablation_ladder computing p_ord twice and plot_tau_effect_on_evidence re-running the
full machinery at every τ; a KeyError trap when the II-only decomposition plots receive
baseline/I results; dead code (`_packers`' pack, unused f0); a hand-rolled softmax; the
induced evidence recomputing a value its own detail dict already held; and the D5-deferred
S3 item — finite-difference stencils evaluating the objective OUTSIDE the bounds box at a
bound-pinned MAP, which the guards turn into cliffs and the eigenvalue floor converts into
an arbitrary +9.2-nats-per-direction term.

**Decision (pure refactors, verified bit-identical on a 38-entry golden snapshot):**
- Single guard authority: `DEFAULT_FIXED_SIGMA`/`_noise_sigma`/`_guarded_neg_log`; all three
  Laplace objectives (Z_Mx, ordinary, N(M)) and both helpers now share it.
- `_packers` replaced by `_unpacker` (pack was dead at all 3 call sites); scipy
  `softmax` replaces the hand-rolled shift-by-max; `laplace_log_evidence_induced` reuses
  `detail["log_lik_at_map"]`.
- `_require_construction_II` guard on both decomposition plots (clear ValueError).
- New `ablation_ladder_posteriors(...)`: each primitive computed ONCE per model (p_ord
  serves baseline+I), optional `precomputed_II=` reuses an existing model_posterior result
  (consistency-checked); `plot_ablation_ladder` delegates;
  `bistar_induced_prior_v2.py` passes its Part-2 result (one N(M) pass saved per prior).
- New `model_posterior_tau_sweep(...)`: baseline computed once (τ-independent);
  Construction I rescales Z_Mx ANALYTICALLY from one τ=1 pass
  (log Z(τ) = log Z(1) + Ḡ*(1−1/τ) + (d/2)log τ); II honestly recomputed per τ (its joint
  MAP moves with τ — no shortcut exists). `plot_tau_effect_on_evidence` delegates.
**Decision (numerics, shifts ≤ 0.005 nats on the golden fixture):**
- `numerical_hessian` diagonal uses the 3-point second difference through f(x) (uses the
  previously dead f0; ~2d fewer evaluations, same O(eps²) accuracy).
- `_laplace_log_integral` evaluates the Hessian at `clip(x*, lo+2eps, hi−2eps)` so every
  stencil point stays in-box: boundary pinning no longer fabricates curvature, genuinely
  flat directions still floor and are flagged via n_clipped (unchanged on the fixture —
  the sigma-flat directions of mean-only metrics are real and stay flagged).

**Rejected from the backlog (S2-PLAU):** test_laplace_zmx's lin_space/quad_space are NOT
duplicates of `build_toy_parameter_spaces` — they are deliberately minimal (sigma excluded
so integrals run over means with an interior MAP; adjustable bounds for the volume tests);
replacing them would weaken the tests.

**Result:** 96 tests pass (4 new: analytic-Hessian recovery, non-II rejection, ladder ≡
three model_posterior calls + precomputed_II identity + mismatch guard, τ-sweep fast paths
≡ naive loop). Golden equivalences: pure refactors 0.0 delta across all 38 entries;
ladder/precomputed/τ-sweep paths exact to 1e-21. Remaining batch-2 work: port the two viz
Laplace scripts onto this machinery (D3 open item 1).

**codex review (empirical; all three findings verified and fixed same day):** codex loaded
the HEAD module in-memory and diffed old-vs-new numerically, independently confirming the
refactor claims (fixed-sigma deltas ~1e-10; sigma-boundary case 0.0040 nats — within the
claimed 0.005; Construction-I analytic rescale exact to 4.4e-16 with no V_ref
double-count). Findings fixed: (1) MEDIUM — precomputed_II metric mismatch was
unenforceable because ModelPosteriorResult carried no metric_name; field added, guard
extended, mismatch test added. (2) LOW — the non-II rejection fired only after the
matplotlib import (fails in mpl-less/sandboxed envs before the intended ValueError);
guard moved before the import in both plots. (3) LOW — the fixed 2*eps Hessian-point
inset INVERTS the clip for a parameter box narrower than 4*eps; inset now capped at half
the box width (degrades to the box midpoint), pinned by
test_laplace_survives_degenerate_narrow_bounds. 97 tests pass; golden fixture
bit-identical through the fixes. Tooling note: backgrounded `codex exec` requires
stdin redirected from /dev/null, else it blocks forever on "Reading additional input
from stdin..." — the cause of two apparent review hangs this session.

---

## D16: batch 2b step 1 — sampling estimators for Z_Mx (mc/is), starts=, weights=, rng= — 2026-07-06

**Problem:** The viz unification (docs/plan-viz-unification.md, reviewed to R2 by codex)
needs Z_Mx estimators that stay valid across the full τ range: pure Laplace crosses the
impossible log Z > 0 bound at finite τ and flips cross-model rankings via its (d/2)log τ
term, while plain uniform-box MC starves below τ≈0.3 (plan §0 V1, re-derived in-repo by
the §6.5 test). The ports also need multi-start optimization, weighted mixture averaging
for the legacy comparison, and reproducible draw subsampling.

**Decision (laplace_evidence.py unless noted):**
- `mc_log_Z_Mx`: uniform-box MC, Ḡ computed once and reweighted per τ; per-τ ESS
  reported. Occam: the box mean is already occam-normalized, so occam=False ADDS +log V
  (inverse of the Laplace convention; D5 single-reference-measure invariant pinned by a
  cross-estimator test).
- `is_log_Z_Mx`: ORDINARY defensive-mixture IS (not SNIS — Z_Mx is the normalizer), the
  REFERENCE estimator for figure Z_Mx values. Proposal = ½ uniform-box + ½ equal-weight
  UNTRUNCATED Gaussians at multi-start Ḡ-optima (cov τ_k·H⁻¹ over a τ_k ladder), box
  constraint as an indicator on the integrand — q integrates to 1 by construction
  (codex watchpoint; consistency pinned by estimating ∫_box 1 dφ = V through the full
  sample-and-evaluate path, and by cell-centered quadrature of q).
- `laplace_log_Z_Mx(starts=)`: multi-start, min-Ḡ* wins (midpoint start missed the
  Sinusoidal basin by >4 nats and Sin+Linear's Ḡ*=0 entirely — §6.4 regression).
- `average_gp_posterior(weights=)` (aggregation_v3): verified-exact weighted mixture
  moments for reproducing legacy LML-weighted figures; None = uniform (unchanged).
- `extract_gp_predictives(rng=)` (bms_star): optional Generator for subsampling;
  None preserves the legacy global-state path.

**codex implementation review (4 findings, all CONFIRMED by execution, all fixed):**
(P2) clipped Hessians were reconstructed then inverted — LinAlgError risk at ~1e20
condition; now inverted in eigen space with proposal variances capped at the box scale
(a floored-flat direction would otherwise throw ~all samples out of the box).
(P2) weights validation accepted nan/inf → NaN moments; finiteness check added.
(P3) _weight_ess returned NaN on all-(-inf) weights, silencing the starvation warning;
returns 0.0. (P3) the §6.2 test's "exactly unchanged" claim was an overclaim — codex
derived the analytic tail leakage (0.0009 nats at τ=0.1, 0.036 at τ=0.3); docstring
corrected. Implementation findings of our own, recorded in the plan (§6.2 addendum +
review log): the dead-parameter volume test both plan reviews had accepted is INVALID
for Laplace (floored-flat width does not scale with the box — n_clipped flags it;
asserted as flagged), and a naive a·x+b peaked setup leaks 0.19 nats through the a–b
correlation ridge (fixed with orthonormalized features).

**Result:** 109 tests pass (17 new in tests/test_zmx_estimators.py — plan §6.1–6.7,
§6.10, plus the four review regressions). Verified against 2-D grid truth: IS within
0.1 nats across τ ∈ [0.1, 100] with ESS > 1000 throughout; Laplace exact at low τ and
diverging at high τ; MC exact at high τ and starving at low τ — the three-regime
picture the plan predicted. Next: the shared viz spaces module, the two script ports,
and the comparison harness (plan §2–§5).

**Status addendum (2026-07-08):** the module header still carried the pre-D16 claim that
importance sampling "fails in >3D parameter spaces"; reworded to the current picture
(Laplace as the fast default; `is_log_Z_Mx` as the figure scripts' validated reference,
heavier and requiring its ESS diagnostics be checked).

---

## D17: viz unification landed — ports, harness, and the legacy-figure contradiction attributed — 2026-07-06

**Problem:** D3 open item (1): the two self-contained viz Laplace scripts duplicated GP/
Laplace machinery, used mutually contradictory conventions (V3: occam hard-ON vs hard-OFF,
different Linear/Quadratic boxes, different multi-start styles), and predated the D15/D16
package machinery. Plan: docs/plan-viz-unification.md (R2 + codex sign-off).

**Decision:**
- `bistar_viz/scripts/_viz_spaces.py` (new shared module): canonical sigma-free spaces
  (unified on the priors-script bounds), trajectory-legacy space variants, legacy inits as
  `starts` (+ `perturbed_starts` reproducing the trajectory's 20-perturbation convention),
  `averaged_gp` (the V2-verified recipe: PRIOR_CONFIGS["informative"] with a runtime
  parity assertion — build_toy_kernels() has a Gamma(2,2) lengthscale and would silently
  break parity — fit_map, fit_gp(--gp-method), extract_gp_predictives(rng=),
  average_gp_posterior; n=0 via sample_prior + condition_on_data=False), and
  `model_prior_curves` (is/mc/laplace dispatch).
- Both scripts REPLACED in place (legacy pinned at a87356a): IS reference estimator,
  `--estimator/--occam/--gp-method/--legacy-spaces/--n-perturb` flags, canonical
  occam=False default (D3); the decomposition figure stays Laplace-structured
  (multi-start) by design. τ-sweep = one is_log_Z_Mx call per model.
- `viz_unification_compare.py` (new harness): git-show extraction from the pinned commit
  (rerunnable forever), per-script legacy figure dirs, both legacy print formats parsed
  (stage blocks at n_hyper=200 AND sweep rows at 150), an ATTRIBUTION LADDER of ported
  arms isolating one change per adjacent gap, and the plan-§4 τ-overlay figure (legacy
  hybrid vs IS vs Laplace vs MC on the legacy averaged GP).
- D10 identity tests rewired to an inline legacy-formula reimplementation (the loader
  targeted the replaced script).

**Finding (harness, quick arms):** the legacy scripts' contradiction is now QUANTIFIED and
ATTRIBUTED. At n=50 the legacy priors figures picked the WRONG model (Linear 0.693,
Sin+Linear 0.008 at stage resolution) while the legacy trajectory gave Sin+Linear 0.934.
Ladder: the averaged-GP estimator change preserves the legacy behavior (p1: Linear 0.534);
the IS-for-Laplace swap narrows it (p2: 0.499 vs 0.473); dropping the hard-wired −log V
occam term flips it (p3/canonical: Sin+Linear 0.992) — the occam-ON volume penalty against
the d=5 true model was the dominant cause, with pure-Laplace error secondary. The
trajectory ladder is convention-stable (t1 ≈ t2 ≈ legacy). The legacy priors script also
disagreed with ITSELF by 0.14 across its two internal resolutions (n_hyper 200 vs 150) —
its prior-IS estimator noise, now visible. Canonical figures select the true model at
0.93–0.99 across all n.

**codex review (1 HIGH, 4 MEDIUM, 1 LOW — all fixed):** HIGH: the delta table's
attribution claim conflated the Z-estimator and occam changes (fixed with the p2
intermediate arm + corrected wording). MEDIUM: trajectory multi-start convention not
reproduced (perturbed_starts + --n-perturb); the log parser missed the priors stage
blocks and silently compared mixed resolutions (both formats parsed, suffixed); both
legacy scripts overwrote each other's flow figure (per-script dirs); the plan-§4
τ-overlay was missing (added). LOW: assert_prior_parity would AttributeError on a
non-Gamma prior (now reports it as a parity violation).

**Result:** 111 tests pass. Harness validated end-to-end (--quick); canonical/legacyconv
arms internally consistent across both ported scripts. Remaining for PR #2 "Ready":
full-quality figure regeneration (non-quick harness + canonical runs) and the D3 status
flip below.

**Status addendum (2026-07-06, codex post-run review — accepted and hardened):** codex
independently re-ran the suite (111 pass) and a 200k-n_is canonical figure set (headline
unchanged: n=50 Sin+Linear 0.992), and corrected two claims: ESS warnings fired at the
PRIMARY τ=0.3 (Sinusoidal/Sin+Linear, intermediate stages) — a proposal-coverage gap, not
a sample-count problem — and stale first-layout legacy figures padded the artifact count.
Fixes: both ported scripts now default to seeded perturbed starts (--n-perturb 5)
anchoring the IS proposal; the trajectory port writes a per-stage per-model
`ess_by_stage.md` diagnostic; stale figures removed; SCRATCHPAD corrected. Validation
rerun at the standard n_is=40k: zero ESS warnings, worst per-stage ESS 166 (Sin+Linear,
n≈20; was <100), τ-sweep min 221, priors unchanged (Sin+Linear 0.93–0.99). Paper-grade
figure certification = check `ess_by_stage.md` in the shipping run.
