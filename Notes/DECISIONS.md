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
**Status addendum (2026-07-08):** the queued prior-sensitivity study is DONE — see D18
(bimodality confirmed prior-induced; the mass split and the VI framing above are
superseded by D18 findings 2 and 4).

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

---

## D18: prior-sensitivity / re-elicitation study — the D12 bimodality is prior-induced; `toy_elicited` recommended for final toy numbers — 2026-07-08

**Problem:** W2 (the ratified D12 gate) required a prior-sensitivity study before final paper
numbers: is the D12 bimodality (and the VI/HMC disagreement, and the "true model selected
from the minority-mass basin" caveat) an artifact of the `informative` prior fighting the
toy data's scale (truth-ish log joint -57.2 vs -33.4 MAP), and is the BI*/BMS* thesis-toy
result stable under reasonable re-elicited priors?

**Design** (`experiments/prior_sensitivity_study.py`; raw artifacts `runs/prior_sensitivity/`,
local by convention; generated tables `docs/prior-sensitivity-study.md`): three alternates
defined in-script (deliberately NOT added to `PRIOR_CONFIGS` — package default is out of
scope): `vague` (the pre-registered broad-LogNormal config), `toy_elicited` (LogNormal priors
with medians from observable data statistics only: lengthscale median 4.5 = geometric middle
of x-spacing 1.05 and x-range 20, sigma 0.9; outputscale median 1.5 ~ var(y)/2; linear
variance median 0.04 ~ var(y)/(2*mean(x^2)); noise median 0.3 ~ 10% of var(y)), and
`gamma_relaxed` (attribution arm: kernel priors Gamma(6,0.85) relaxed to Gamma(2,0.5), noise
prior untouched). Staged cheap-to-expensive pipeline: stage A (prior scorecard, MAP,
27-start Nelder-Mead mode hunt with valley checks between verified modes, 3-seed prior-IS
with delta-method SEs and per-basin ESS, VI across seeds 0/1/2/42), stage B (capped-depth
NUTS td7 + VI + MAP through the D12 `run_one_method` machinery, cache fingerprint sidecars),
stage `is` (mass-faithful model selection: SIR from pooled prior-IS draws through the same
BMS* pipeline, ESS>=100 floor). Decision rules PRE-REGISTERED in the script docstring and
report header before any stage-B result was read (roles, coherence criteria i-iii,
winner-blind adoption, outcome patterns A-E). A preflight multi-agent review (5 reviewers,
findings adversarially verified) ran before the expensive stage and forced four fixes: the
`toy_elicited` lengthscale prior violated its own elicitation rule (median 2, suspiciously
near the D12 posterior, vs the honest geometric middle 4.5 — fixed, affected HMC rerun);
the original 4-start mode hunt produced a FALSE unimodal verdict for `vague` (a verifier
located a surviving degenerate mode at ls 0.018, noise 0.44); prior-IS ESS collapses for
the Gamma configs (informative low-basin effective draws ~15 at the 60k default) with no
reported uncertainty; and no mass-faithful model-selection number existed anywhere despite
D12's framing hinging on one.

**Findings:**
1. **Attribution:** prior-only scorecard at truth-ish — `informative` total log prior
   -35.5 nats (per-site: linear variance -19.7, outputscale -9.7, lengthscale -5.0,
   noise -1.2);
   alternates -0.9 to -9.5. `gamma_relaxed` (kernel priors relaxed, noise prior IDENTICAL)
   fully dissolves the bimodality: the Gamma(6, 0.85) kernel priors are the cause, not the
   noise prior. Truth-ish-to-MAP log-joint gap: 23.8 nats informative vs 3.5-4.3 alternates.
2. **Geometry:** `informative` bimodal (2 verified modes, straight-path valley 6.3 nats;
   pooled 600k-draw prior-IS: P(noise<0.15) = 0.277+-0.018, P(noise>0.30) = 0.592+-0.015,
   low-basin ESS 129; nearest-mode mass split 0.40/0.60) — the D13 "~3x the mass" headline
   softens to ~1.5-2x with honest SEs, direction unchanged, and it is the only INCOHERENT
   config under the pre-registered rules. `toy_elicited` and `gamma_relaxed`: 27/27 starts
   to a single verified mode (IS mass 1.000). `vague`: trimodal but coherent — dominant
   near-truth mode holds 95.9% of pooled mass; two degenerate tiny-lengthscale modes
   (ls ~0.018) hold 0.8%/3.4% (<5% rule).
3. **Model selection (stage B, td7, D12 budgets/seed; baseline comparability certified by
   a drift check — fresh informative vi/map reruns match the frozen `results_td7.json` to
   0.00000):** HMC and MAP select Sin+Linear under EVERY config (hmc pw_kl_vcal tau=1:
   0.673 informative / 0.681 gamma_relaxed / 0.685 vague / 0.696 toy_elicited; hard
   assignment 200/200 everywhere). The new mass-faithful SIR arm (final numbers at
   n_pred=1000 with bootstrap SEs over SIR draws and 3 per-IS-seed replicates) selects
   Sin+Linear at tau=1 under ALL FOUR configs — including informative (0.276±0.003,
   near-flat) — so the D12 speculation that "a mass-faithful answer would lean toward
   VI's wrong-model conclusion" is REFUTED by the computed number: the informative prior
   does not flip the mass-faithful conclusion, it dilutes it toward uniform and makes it
   tau-FRAGILE (informative SIR row: Linear top at tau=0.1, Sinusoidal at 0.3, Sin+Linear
   only from tau>=1; every alternate's SIR row is rank-stable at Sin+Linear across all
   tau — gamma_relaxed 0.378±0.004, vague 0.432±0.007, toy_elicited 0.441±0.005 at tau=1,
   per-seed scatter <=0.03; hard fractions 0.908-0.973 vs informative's 0.481).
4. **VI (revises the W3 framing):** fit_vi lands in the wide smooth high-noise region under
   EVERY config (noise 0.37-0.57, stable across 4 seeds x 4 configs) REGARDLESS of that
   region's actual posterior mass (59% informative, 15% gamma_relaxed, 6% vague, 5%
   toy_elicited), so VI/HMC max abs posterior difference is 0.45-0.48 everywhere.
   PRE-REGISTRATION DEVIATION, disclosed: coherence criterion (iii) (VI-HMC agreement
   <= 0.10) fails for every config and is hereby judged MIS-SPECIFIED — it tests fit_vi's
   ADVI approximation quality (an entropy-favored wide basin), not posterior geometry; the
   D12/D13 reading "VI migrates to the DOMINANT basin" was partly coincidental (under
   informative the wide region happens to hold the majority mass). Criteria (i)+(ii) plus
   the SIR arbiter carry the coherence verdict; VI is demoted from "bimodality diagnostic"
   to "wide-basin detector" — its disagreement with HMC no longer implies multimodality.
5. **kl_forward (strengthens W1; stated precisely):** 1.000 Sin+Linear under every tight
   single-basin HMC/MAP arm. Under heterogeneous draw mixtures (all VI and SIR rows) its
   SOFT tau=1 Boltzmann posterior collapses Sin+Linear to 0.000 — the aggregation
   mean_i exp(-G_ij/tau) is dominated by the mixture's high-noise draws, whose kl_forward
   G for Sin+Linear is enormous — while the per-draw HARD best-match rate stays majority
   Sin+Linear on the alternates' mixtures (SIR hard fractions at n_pred=1000: 0.696
   toy_elicited, 0.707 vague, 0.520 gamma_relaxed; the informative mixture degrades it to
   0.241). An aggregation-level outlier sensitivity under draw heterogeneity, not
   per-draw misranking — appendix-only framing confirmed and sharpened.

**Decision (recommendation under a DISCLOSED DEVIATION from the pre-registered pattern
table):** no pre-registered pattern fires cleanly. Pattern A required VI/HMC agreement,
and criterion (iii) fails for EVERY config including the frozen informative baseline
(finding 4); read strictly, the table returns pattern D ("all alternates incoherent"),
which is absurd — a leg that fails identically everywhere cannot distinguish configs, and
the failure is attributable to fit_vi, not to any posterior. Revised rule, adopted openly
post hoc: coherence = criteria (i)+(ii), with the mass-faithful SIR row as the
VI-independent arbiter. Under that rule the substance of pattern A holds: the bimodality
and the VI/HMC disagreement are PRIOR-INDUCED artifacts of the `informative` config;
recommendation for the paper — final toy numbers use the re-elicited `toy_elicited` prior
(coherent geometry, honest data-statistics elicitation, healthiest sampler behavior:
capped-td7 site ESS 41-72 vs the informative baseline's 11-18, uncapped 28-70 vs 4-27,
and the strongest and most tau-stable mass-faithful result), with
`informative` retained as the documented prior-misspecification / bimodality case study
(the D12 story) and `vague` as the robustness appendix. The headline "BI* recovers the true
mechanistic model" is NOT an artifact of the informative prior: it survives every prior and
every mass-faithful measure tested; what the informative prior costs is decisiveness and
tau-stability. **Spot-check (pre-registered rule FIRES; arbitration decided, uncapped arm
recorded below):** for the adopted config the HMC draw occupancy contradicts the prior-IS
mass far beyond 2 SE (P(noise<0.15): 1.000 vs 0.763±0.004). Three-way noise-marginal
arbitration (stage `noise-marginal`, estimators sharing no failure mode) is UNANIMOUS
against the capped chain: prior-IS pooled 0.763±0.004 / 0.191±0.004 / 0.046±0.001
(mid-band ESS 3444, top mid draws on a smooth ridge 1.4-1.6 nats below the best);
Jacobian-corrected RW-MH referee 0.796-0.843 / 0.140-0.175 / 0.016-0.037 across seeds
42/1/2 with 38-44 lo/hi crossings per 30k chain (the ridge is traversable by a plain
random-walk sampler); profile-Laplace quadrature of p(noise|y) (no sampling, 40/40 grid
points PD) 0.763 / 0.138 / 0.023. The capped MAP-init NUTS chain (noise draws
0.0495±0.0076, confined near the mode) under-explores the noise ridge even in this
UNIMODAL geometry — the D8 Mauna disease pattern, now demonstrated on a well-behaved
posterior. CONSEQUENCE for the paper: under toy_elicited the honest full-Bayes headline
is the mass-faithful SIR number (Sin+Linear 0.441±0.005 bootstrap SE at tau=1, per-IS-seed
0.419/0.438/0.431 at n_pred=1000), with the HMC row (0.696) reported as the
density-mode-region answer under the same disclosure discipline W2 already imposes on the
method default. Uncapped td10 arm (COMPLETE, 5.7 h): ALSO fully confined — occupancy
1.000/0.000/0.000, noise draws 0.0516±0.0068 (q95 0.064), pw_kl_vcal tau=1 Sin+Linear
0.683 vs capped 0.696 (cap again result-preserving, <=0.013 shift). So the confinement is
NOT a depth-cap artifact: MAP-init NUTS with pyro-default adaptation under-explores the
noise ridge on this posterior at any tree depth (step size adapted in the stiff
near-mode region cannot diffuse up the ridge within 2000 draws), while a plain RW-MH
crosses it ~40 times per 30k chain. Consequence stands: the SIR row is the honest
full-Bayes number; the HMC row (either cap) is the density-mode-region answer.

**Status (CLOSED 2026-07-10; author ratification 2026-07-09, recorded in the local
writeup log):**

- (a) RATIFIED, scope-TIGHTENED: `toy_elicited` adopted for the paper's final toy
  figures on the N=20 thesis-toy instance ONLY (`generate_toy_data()` defaults: N=20,
  noise 0.5, seed 42, the D12/D18 instance), not as a global prior replacement:
  `bms_star_toy.py`'s N=50 sweep and the `bistar_viz` data convention keep their
  current priors (viz gate below). Reporting convention: the SIR estimate carries
  the headline as the posterior-mass-faithful answer under the fixed data-elicited
  prior (Sin+Linear 0.441, conditional SIR bootstrap SE 0.005, at tau=1;
  independent-pool estimates 0.419/0.438/0.431 as the second uncertainty
  component; terminology correction below), with the NUTS value beside it as the
  answer conditional on the density-mode region (0.696 capped td7 / 0.683
  uncapped td10). Figures A
  (`toy_model_posterior_elicited`) and B (`prior_misspec_geometry`) implemented as
  `--stage figures` in `experiments/prior_sensitivity_study.py` (this commit): built
  only from the existing `runs/prior_sensitivity/` artifacts (zero new sampling),
  every plotted headline value asserted equal to its pinned expectation
  (rtol=0, atol=1e-12) before plotting, outputs under
  `runs/prior_sensitivity/figures/`, captions carrying per-estimator predictive
  counts rendered from validated artifact fields (SIR 1000 resampled predictives,
  883 unique, with every metric's hard-fraction denominator proving all 1000
  contributed; NUTS 200 predictives from 2000 draws) and the density-mode
  disclosure; the rank-stability annotation is validated against the full
  posterior vectors at every tau.
- (b) GRADUATED registry-only: `PRIOR_CONFIGS["toy_elicited_n20"]`
  (`bistar_gp/config.py`, this commit), parameters identical to the study's
  in-script config; the `_n20` suffix encodes the dataset instance whose observable
  statistics defined the elicitation. NOT the package default and NOT added to
  `ExperimentConfig.prior_configs`, so the default sweep and every cached run stay
  untouched. `STUDY_CONFIGS["toy_elicited"]` now points at the registry entry; the
  cache fingerprint covers only the four prior parameter tuples and is verified
  unchanged against the on-disk sidecars, and artifact filenames key off the
  STUDY_CONFIGS dict key, which stays `toy_elicited`. Regression tests:
  `tests/test_prior_sensitivity_figures.py` (registry params exact and out of the
  default sweep; fingerprint pinned; figures preflight fails fast with all 15
  required artifact names pinned; figures stage builds with every
  fitting/sampling/predictive-extraction entry point monkeypatched to raise, the
  validation gate's console line asserted, the output stems pinned, and a
  completeness invariant tying every loaded headline value to a pinned
  expectation; a hermetic synthetic-artifact test covers the loader schema and
  both renderers on machines without runs/; negative tests prove the gate fails
  on a drifted value and on SIR rank instability). The same commit retitles
  `docs/fit-method-metric-comparison.md` as the informative
  prior-misspecification case study via its generator (`render_markdown`),
  regenerates it with `--render-only` (no sampling), and regenerates
  `docs/prior-sensitivity-study.md` via `--stage report` so its toy_elicited
  description bullet matches the registry entry.
- (c) W3's verbatim VI sentence REVISED in the local writeup log (2026-07-09): VI
  reads as a wide-basin detector, not a mass-faithful reporter (finding 4); the
  paper phrasing now assesses posterior mass with sampler-independent estimators
  (pooled prior-IS for basin mass, SIR through the BMS* pipeline for model
  posteriors).

**Terminology correction (2026-07-10, author decision; W5 in the local writeup
log):** the "full-Bayes headline" wording used above and in the 2026-07-08/09
narrative of this entry is superseded; the original text stays as written for
provenance. `toy_elicited`'s medians were set from the realized N=20 sample's
summaries (x-spacing, x-range, mean(x^2), var(y)), so the prior is DATA-ELICITED
(empirical-Bayes-style, data-adaptive). The philosophy is continuous with thesis
Chapter 5 pp. 184-186, which explicitly permits using some or all of the present
data to choose plausible generating processes and priors and cites empirical
Bayes; the thesis does not document this exact var(y)-based numerical
elicitation rule. Consequently the SIR estimate is POSTERIOR-MASS-FAITHFUL
CONDITIONAL ON THAT FIXED PRIOR, not an unqualified full-Bayes result: the
end-to-end procedure does not propagate uncertainty in the data-driven
prior-setting step. Uncertainty reporting is two-layered and the components are
never combined into one error bar: the ±0.005 whisker is the conditional SIR
bootstrap SE given the realized pooled IS draws and their estimated weights,
while the independent-pool estimates 0.419/0.438/0.431 display the separate
importance-pool variability. Figure A's legend and caption carry this wording.
No change to the prior, the adoption scope, any numerical result, or any
ranking conclusion.

**Viz canonical-figure gate (ratification condition): PASSED BUT NOT EXERCISED
(2026-07-10, read-only recheck).** Re-applying the D18 elicitation rule to the
canonical viz data convention (`_viz_spaces.generate_data`: n=50, seed 42,
uniform-random x, noise 0.3) put all four re-derived medians within one log-SD of
the `toy_elicited_n20` medians:

| site | viz-convention median | log-ratio vs toy_elicited_n20 | prior sigma | worst seed \|log-ratio\| (seeds 0,1,2,7,123) |
|---|---|---|---|---|
| ls | 2.712 | -0.506 | 0.9 | 0.531 |
| os | 1.557 | +0.037 | 1.0 | 0.386 |
| lv | 0.0460 | +0.139 | 1.5 | 0.293 |
| noise | 0.3114 | +0.037 | 1.0 | 0.386 |

Provenance caveat, to be repeated wherever this gate is cited: the quantitative
one-log-SD-per-site threshold was declared in-session on 2026-07-10 immediately
BEFORE the read-only calculation, blind to its output; it does not appear in the
original ratification text and must never be described as original
preregistration. Author decision: the gate stays unexercised;
`p3_priors_canonical` / `t2_traj_canonical` stay under `informative` in the
methods-validation / legacy-comparison role, and `assert_prior_parity` stays as
is. Rationale: the switch would buy presentational consistency only, while the
n=0 panel would become implicitly empirical-Bayes (a prior re-derived from the
same data convention it then predicts), extra parity machinery would be needed,
and the legacy comparison would lose continuity. Reconsideration condition:
promoting the viz trajectory to a main-text scientific result requires a separate
scoped sensitivity figure plus an explicit data-dependent-prior disclosure first.

**Result:** stage-A/B/is JSONs + sampler caches under `runs/prior_sensitivity/` (HMC arms
~2.3-2.4 h wall each under parallel load); generated tables `docs/prior-sensitivity-study.md`;
114 tests at the study commit ec127a9, which touched no package code (the Status closure
above later added the registry entry and the figure tests, bringing the suite to 121).
D12/D13 history preserved unmodified (this
entry supersedes their mass-ratio and VI-framing numbers where noted).

---

## D19: Mauna Loa paper-grade study — plan + pre-registration v1.0 FROZEN before results (M1) — 2026-07-10

**Problem:** D8 left paper-grade full-Bayes Mauna inference as an open fork (stuck chains at
trend lengthscale 8 vs 32 with a 418-nat log-joint gap, kernel-site ESS ≈ 1), the W6
provisional brief scoped the study (applied scalability demonstration; nothing pre-selected),
and a planning-only session (2026-07-10) produced a staged design that went through four codex
gpt-5.6-sol review rounds (round 1: 14 findings, FIX-FIRST, all accepted at least partially;
rounds 2-4: decision addenda, scorecard corrections, ratifications). The plan, the author
decisions, and the pre-registration had to land in one tracked, reviewed commit of planning
artifacts only (docs, Notes, frozen planning scripts and JSONs; no package code) BEFORE any
pilot, posterior, or BMS* result exists — otherwise arm or sampler selection
could leak results into the design (the R3 class) and the study would lose its
pre-registration standing.

**Decision:** freeze everything currently definable in `docs/plan-d19-mauna.md` (staged plan +
pre-registration v1.0 + decision record + committed evidence) in this single commit on
`docs/d19-mauna-freeze`; M2a implementation follows as a separate infrastructure PR.

- Staged design: Stage 0 elicitation (closed here except the era transcription) / Stage A
  sampler-independent geometry per arm / Stage B strategies S1, S1f, S2, S3, S4 behind bounded
  pilots on enabler E1 (direct-parameter potential; measured ~200x per-leapfrog advantage over
  the deep-copy pyro path: 2.79 s vs 15.5 ms per gradient at N=461) / Stage C BMS* +
  mass-faithful arm. Gates G0 / G-IS / G-referee / G-A / G-toy / G-B / G-C; milestones
  M2a (provenance + loader + registry + metric + diagnostic schema), M2b (E1 + equivalence +
  the real E1 NUTS microbenchmark + Della re-benchmark), M2c (S2/S3/S4 + M1 + estimator-
  specific toy goldens), M2d (arms + orchestration + G0), M3 pilots, M4 full runs, M5 results
  + the D19 author decision.
- Author decisions recorded: **A1** nugget = measurement error + uncorrelated
  monthly-aggregation/residual variance; M1's Matern-3/2 carries correlated short-term
  discrepancy. **A2** arm priors v1 RATIFIED (P0 baseline; elicited kernel/noise blocks;
  tables in the doc §7, identical to the committed scorecard script); v1b
  examined-and-rejected, kept with its scorecard. **A3** M1 piloted, with the bounded
  logit-normal lengthscale prior ls = 0.1 + 0.9·sigmoid(z), z ~ N(-1.2528, 1.082), hard
  support [0.1, 1.0] y (q10/50/90 = 0.16/0.30/0.58), normalization/sampling/equivalence tests
  at M2c. **A4** 4-ladder main universe + harmonized 3-set appendix: period frozen at 1.0,
  shared D11 multi-start protocol replaces differential_evolution, code-level identity test on
  the shared member (Quad+2Harm), separate normalizations always; pw_kl_vcal primary at tau
  grid 0.1/0.3/1/3/10 (headline tau 1), kl_forward appendix. **A5** paper target = full N=461,
  frozen before any pilot is read; blind pre-registered subsample fallback only if infeasible,
  with the fallback design, exact N, and the infeasibility predicate (engineering/budget
  evidence only, never adequacy or BMS* outcomes) frozen at M2b per the freeze-commit review.
  **A6** pilot budgets PROVISIONAL until the M2b E1 NUTS microbenchmark (the E1 cost rows are
  kernel-cost proxies). **A7** Della use gated on re-running `experiments/d19_bench.py` there,
  threads pinned; embarrassingly parallel work only. **A8** mass-faithful arm REQUIRED TO
  ATTEMPT, optional to deliver (O5 reports infeasibility; a confined chain is never
  substituted). **A9** vendored checksummed dataset + runtime verification if licensing
  permits, else deterministic retrieval + checksum; canonical year/month/co2 hash; the
  document-only option REMOVED. **A10** seasonal period FROZEN at exactly 1.0 with
  requires_grad(False) + assertion at M2a — the planning session verified live (codex catch)
  that `raw_period_length` is a TRAINABLE plug-in today (fit_map moves 1.0 to 0.99962 in 100
  iters under Interval(0.99, 1.01)), so every pre-D19 Mauna analysis is disclosed as
  conditional on a data-fitted plug-in period ~0.9996. **A11** the PROVISIONAL W6 brief takes
  precedence over the second W6 entry's computation-tree step 1: no method — including
  MAP+Laplace — is primary before pilots; S4 competes like every strategy; MAP+Laplace
  survives only as the O4 fallback carrier.
- Pre-registration v1.0 (doc §6), frozen at this commit: arm roles + frozen order (P0,
  P-comb-v1 = the first revised arm, P-comb+M1-v1, P-kernel-v1, P-noise; adoption candidates
  must all reach the paper-target scale before selection); per-arm dossier hashed BEFORE any
  BMS* probability under that arm is computed (sha256 in the study log, committed by the next
  milestone); selection firewall + default-selection tie-breakers; outcome patterns O1-O5 with
  no scientific-outcome predictions (risk-register likelihoods narrowed to engineering
  feasibility); sequential stop rules keyed ONLY on geometry/adequacy/budget — the draft's
  BMS-shift expansion trigger DELETED, and (freeze-review catch) the G-B seed-reproducibility
  leg re-keyed from BMS* outputs to target-level agreement (per-site posterior means within 2
  combined MCSEs; band occupancy within 0.05), with BMS* seed-stability demoted to Stage-C
  reporting-only, so no gate reads BMS* output; budget reservation guaranteeing P0 + every
  G-A-passing adoption candidate reach the paper-target scale before attribution arms spend,
  else no prior selection occurs (P0 default, disclosed); the 60-month holdout SEALED until
  the D19 decision is recorded (no inspection/scoring/persistence/selection use of test
  VALUES; split metadata and the legacy loader's mechanical materialization permitted and
  disclosed; training-only loader path queued at M2a; selection-relevant predictive checks =
  training-span or rolling-origin with MAP/S4-level refits only); estimator-specific toy
  goldens (S2/S3 must reproduce the D18 sampler-based noise-marginal references — prior-IS +
  RW-MH referee — and the mass-faithful 0.441 family within pre-declared MC error, NOT the
  confined 0.696, which stays an S1 regression characterization only; the freeze review
  exposed the D18 profile-quadrature triplet 0.763/0.138/0.023 as non-normalized grid
  integrals summing to 0.924, so it is historical-only with the corrected recompute queued at
  M2c); coverage verdicts need a mass-bearing authority (gated IS, else the crossing-verified
  referee) plus a corroborating reference within 3 authority-SEs (profile quadrature
  corroborating-only; a profile curve alone is never a coverage authority; no available
  authority = coverage undetermined and the strategy fails that scale); G-IS = pooled ESS >=
  100 pilot floor, per-band ESS >= 100 in every band holding >= 5% authority mass, 3
  independent 600k pools agreeing within 2 combined SEs, functional MCSE <= 0.02 for any
  paper-quoted BMS* probability; 10 standing disclosures (td7 efficiency control;
  "likelihood-favored under the current GP specification"; W5 data-elicited terminology incl.
  y_std^2 = 212.68 ppm^2 scaling and x centering at 1977.711; the plug-in period history;
  sub-150 screening-only; corrected D6 causal history; "the stationary zero-mean trend prior
  assigns equal probability to rising and falling trajectories — the scorecard evaluates
  magnitude only"). Every currently definable threshold carries its number (doc §6.15);
  implementation-coupled predicates (E1 equivalence tolerances, S2/S3 test tolerances, G-toy
  tolerances, divergence-clustering, M1 overlap diagnostic, final A6 budgets) are enumerated
  with "numeric value fixed in M2a-M2c, before any pilot result is read"; amendments are
  append-only v1.x, landing before the stage they affect (§6.16).
- Source status (doc §8): OpenML 41187 v1, sha256(co2) 7e301efd...44cb9, counts
  2225/521/461/60 verified; Thoning et al. 1989 + Komhyr et al. 1989 + NOAA GML pages
  identified for the nugget memo; era/source transcription OPEN with the round-4 amendment
  rule — material contradiction of the 0.2 ppm lower-reference interpretation triggers a
  documented prereg amendment or a new named arm BEFORE Stage A.
- Evidence committed: `experiments/d19_prior_scorecard.py` (port of the planning scorecard,
  seeds [arm, 20260710] / [arm, 77] unchanged; VERIFIED this session to regenerate
  `runs/d19_planning/scorecard_v2.json` byte-identically), `experiments/d19_bench.py` (the
  A7/R6 re-benchmark vehicle), and `runs/d19_planning/{bench_sub,bench_full,scorecard_v2}.json`
  (deliberately tracked: timing evidence is not regenerable and the scorecard JSON is the
  determinism reference). Scorecard v2 (2000 draws/arm, B=1000 bootstrap, corrected
  functionals): realized training references trend 46.59 / decadal 8.56 / seasonal 4.62 /
  range 51.93 / diff-sd 1.19 ppm; adoption candidates P-comb-v1 and P-comb+M1-v1 pass ALL rows
  with bootstrap confidence (trend pctile 0.938, CI [0.927, 0.949]); stability counts all zero
  (v1's warnings were spurious arm64 BLAS flags, fixed in v2 by correlation-space Cholesky +
  relative jitter ladder).
- Housekeeping in the same commit: `.gitignore` gains `Notes/WRITEUP_DRAFT.md` (recorded as
  pending on 2026-07-10 in the memory note; local prose stays untracked).

**Alternatives considered:** freezing after M2a with the implementation-coupled numbers in
hand (rejected: pilot results could be read before the freeze, which defeats pre-registration);
leaving the plan as the chat deliverable without a tracked commit (rejected: unreviewable,
mutable, and the seeds/artifacts would rot in a session scratchpad); one shared toy golden for
every strategy (rejected as statistically backwards — codex round 1: a coverage-repairing
sampler must not be required to reproduce the mode-confined number); v1b trend-os arm
(examined-and-rejected under A2: chases the realized trend magnitude and inflates the prior
range, q97.5 120 vs 93 ppm); giving the seasonal period a prior as an 8th site (rejected under
A10: inventory churn everywhere downstream with no identified scientific need; revisit only on
Stage-A seasonal misfit, as an amendment).

**Freeze-commit review (same session, codex gpt-5.6-sol xhigh on the diff): FIX-FIRST, 10
findings (6 HIGH, 2 MEDIUM, 2 LOW), every one resolved at documentation level BEFORE the
freeze finalized** (the commit was amended; "round 5" markers in the doc flag each change):
G-B seed reproducibility re-keyed off BMS* outputs to target-level agreement; M1/S3/S4 and
selection predicates numerically frozen or §6.15-enumerated (frozen rolling-origin protocol,
occupancy/correlation authority precedence, coverage SE formulas incl. chain occupancy SE,
5x speed factor, ordinal coverage score, operational prior-pass rules); the D18
profile-quadrature band triplet exposed as non-normalized (sum 0.924, boundary-straddling
intervals dropped) and demoted to historical with the corrected recompute queued at M2c;
budget reservation for adoption candidates with a no-selection rule if any ends unmeasured;
holdout-seal semantics made literally true (the legacy loader materializes the split; a
training-only loader path is an M2a item); the A5 fallback freeze pinned to M2b; the model.py
citation corrected to lines 132-141; the scope label corrected to planning-artifacts-only.
The reviewer independently verified the committed scorecard values/CIs, realized references,
stability counts, benchmark timings, MAP/provenance values, arm tuples, and both seed
formulas, and confirmed no package-code change and no new pilot/posterior/BMS* artifact in
the diff. Thirteen §9.4 table cells were also corrected to the script's own %.3f rendering
(x.xxx5 boundary values; the pinned P-comb-v1 trend 0.938 [0.927, 0.949] was unaffected).

**Status: FROZEN-BEFORE-RESULTS (M1 complete).** No pilot, posterior, or BMS* number exists or
was read; the only computation this session was the deterministic reproduction check of the
already-ratified Stage-0 scorecard (whose acceptance rule was declared before any scorecard
computation, in the planning session). OPEN items, all carried inside the doc: era/source
transcription (§8, amendment rule armed); final A6 budgets + A5 fallback freeze at M2b;
implementation-coupled predicate numbers at M2a-M2c (§6.15); G0 sign-off at M2d. Next: the
M2a infrastructure PR.

## D20: D19 M2a infrastructure — provenance gate, holdout-seal API, period freeze, candidate registry, metric wiring, diagnostics schema, slurm guard — 2026-07-11

**Problem:** the frozen D19 pre-registration (docs/plan-d19-mauna.md, a077c6e, merged e86e90a)
promises seven arm-independent infrastructure pieces at M2a, before any pilot result may be
read (§4 milestone map, §6.15/§6.16 ordering): the A9 data-provenance gate with the canonical
year/month/co2 hash; a training-only loader making the §6.6 holdout seal mechanical; the A10
seasonal-period freeze (the plug-in period was still trainable and drifted to ~0.9996 under
fit_map — standing disclosure 4); the A4 candidate-set registry with the harmonized 3-set
appendix universe (historically: trainable P in (0.9, 1.1), cos second harmonic,
differential_evolution — all divergent from the ladder); pw_kl_vcal + the frozen tau grid
wired to the Mauna scripts; a diagnostic-retaining sampler result schema (fit_hmc discarded
the pyro MCMC object, losing the divergences/depth-saturation/acceptance that gate G-B reads);
and the stale-slurm refresh. The recorded loader defects (dead synthetic fallback reaching
`np.argsort(x_all)` with `x_all` unbound on fetch failure; unreachable second `except`;
undocumented no-op co2>0 filter) rode along.

**Decision:** one infrastructure PR (branch `feat/d19-m2a-infra`), no pilots, no Mauna BMS*
output, no candidate fit to real Mauna data anywhere (all harmonization/registry/metric tests
run on synthetic fixtures):

- **A9 provenance gate** (`bistar_gp/data.py`, rewritten): OpenML 41187 is licensed CC0
  (checked 2026-07-11 via the OpenML API), so the vendored branch of A9 applies — the full
  2225-row raw record is vendored at `bistar_gp/datasets/mauna_loa_co2_openml41187.csv`
  (all 7 columns; station/day/weight/flag kept because the §8 era transcription reads them;
  file sha256 6e50ccd10d6132da6df272f5e2b30d2f02c5134cda6bbd3a1b2b69fbe48d30eb). Every load
  verifies: the canonical year/month/co2 sha256
  5bcdc813b4c3b570c9947acfaa0d3ff8cb5f89094b3e4e5121f72535a0cc0910 (float64 tobytes, column
  order year/month/co2, fetched row order — the same serialization the M1 benchmark used;
  recorded as PREREG ADDENDUM v1.1 in the new docs/prereg-addenda-d19.md), the M1 co2-only
  pin 7e301efd...44cb9 (continuity, plan §6.2), and counts 2225 raw (pre AND post the §6.2
  co2>0 filter, asserted to stay a no-op) / 521 monthly / 461 train / 60 test at the prereg
  cutoff. Hard RuntimeError on any mismatch (`_verify_mauna_provenance`, data.py:96).
  Sources: `source="vendored"` default (offline, deterministic), `source="openml"`
  retrieval verified against the same pins (data.py:67; verified to yield byte-identical
  tensors). The dead fallback and unreachable except are gone; `_synthetic_mauna_loa` is
  deleted (a silent synthetic substitute is exactly what A9 forbids).
- **Training-only API** (`load_mauna_loa_training`, data.py:244): returns (x_train, y_train,
  info) — test y values never returned, logged, or persisted by this entry point; split
  METADATA (461/60, cutoff rule) rides in info as §6.6 explicitly permits. The provenance
  layer still reads the full artifact for checksum verification (seal semantics are
  application-layer; full-artifact verification necessarily streams test-era rows and is
  permitted). Study-facing D19 code uses this entry point from now on; the default
  `load_mauna_loa` keeps its exact 5-tuple contract and values.
- **A10 period freeze** (`bistar_gp/model.py:121-190` + `bistar_gp/fit.py:42`):
  raw_period_length filled to exactly 0.0 — which maps to exactly 1.0 under
  Interval(0.99, 1.01) in float64 (verified numerically) — plus requires_grad_(False) in
  build_mauna_loa_kernels; `assert_mauna_period_frozen(model)` checker (model.py:124);
  fit_map snapshots every requires_grad=False parameter at entry and asserts it unchanged at
  exit, so every MAP/multi-start path enforces the freeze structurally. Disclosed side
  effect: fit_mcmc_simple no longer proposes the period (its param_list filters on
  requires_grad; pre-A10 the period WAS a proposal dimension). The pyro sampled-site
  inventory stays 7 (the period carries no prior). Tests:
  tests/test_mauna_period_freeze.py (7 — exact 1.0 at build, fit_map 100-iter hold,
  3-restart multi-start hold, guard trip on violation, 7-site inventory via
  initialize_model, no period site, MH exclusion).
- **A4 candidate registry** (`bistar_gp/mauna_loa_candidates.py`): one module now hosts BOTH
  universes — MAIN_LADDER (the unchanged 4-ladder) and APPENDIX_TREND3 (harmonized 3-set) in
  an immutable MappingProxyType registry (line 476) with per-universe roles and the A4
  separate-normalization rule; `build_universe(key)` tags every fresh instance with
  `.universe` (line 497); `assert_single_universe` raises on empty/untagged/mixed
  collections (line 511) and the study script calls it before run_bms_star, so merging the
  two universes into one normalization is loudly erroneous. Harmonized appendix members
  LinearHarmonic2Model (line 215) and ExponentialHarmonic2Model (line 316) use the ladder
  convention: period frozen at 1.0 (fixed 2π/4π frequencies; the historical trainable
  P in (0.9, 1.1) is gone), sine second harmonic (replacing the historical cos — the two
  conventions are prediction-equivalent, tested on canonicalized predictions rather than
  raw phase parameters), and the shared D11 multi-start full-NLL protocol through
  CandidateModel._fit_mle (differential_evolution removed from
  experiments/bms_star_mauna_loa.py entirely). The shared member is the SAME class object
  in both universes (`AppendixQuadHarmonic2Model = QuadHarmonic2Model`, line 464), so the
  §3 cross-universe identity holds by construction. Tests:
  tests/test_mauna_candidate_registry.py (7, synthetic fixtures only): composition/tags,
  class-and-fit identity of the shared member, historical-cos ground truth reproduced by
  the harmonized sine model, restarts routed through _fit_mle (spy) + no
  differential_evolution import remains, merge-guard accept/reject, metric/tau contracts,
  synthetic end-to-end BMS* normalization.
- **Metric wiring (A4-metric)** (registry module lines 37-52):
  MAUNA_PRIMARY_METRIC="pw_kl_vcal"; MAUNA_METRICS = pw_kl_vcal first + the five legacy
  Mauna metrics + the DISTRIBUTION-LEVEL kl_forward as the A4 appendix-sensitivity
  addition (plan §2/§7 "existing Mauna metrics plus kl_forward" — the pointwise
  pw_kl_forward is one of the legacy five and does not satisfy that clause;
  verification-workflow catch); MAUNA_TAU_GRID =
  (0.1, 0.3, 1.0, 3.0, 10.0); MAUNA_HEADLINE_TAU = 1.0. bms_star_mauna_loa.py imports
  bistar_gp.metrics_v2 for METRICS registration, scores MAUNA_METRICS over the frozen grid
  (replacing np.logspace(-1, 2, 25)), prints tables at every prereg tau, and keys the
  summary JSON on the headline tau instead of the mid-grid heuristic. No Mauna BMS* value
  was computed anywhere in M2a.
- **Diagnostics schema** (`bistar_gp/sampler_diagnostics.py`, new): frozen dataclass
  SamplerDiagnostics (schema_version 1, line 65) — chain-major divergence_draws
  (post-warmup indices, pyro's own convention at hmc.py:414), acceptance_rate,
  leapfrog_counts, site_names in samples-dict order; JSON to_dict/from_dict rejecting
  unknown keys and foreign versions; an honesty contract enforced at construction (a
  diagnostic is None exactly when named in `unavailable` — never fabricated zeros); derived
  n_divergences/divergence_rate/tree_depths/depth_saturation_rate (saturation predicate:
  leapfrogs >= 2^max_tree_depth - 1; 127 at td7, matching the D8 record). Pyro 1.9.1 does
  not expose per-iteration tree depth, so it is recovered observationally:
  PotentialEvalTracker (line 40) wraps the model callable — one traced call per leapfrog,
  verified by probe — and an MCMC hook_fn snapshots cumulative counts per iteration;
  sampling-stage deltas are per-draw leapfrog counts (leapfrog_counts_from_records,
  line 203). `fit_hmc(..., return_diagnostics=True)` returns (samples, SamplerDiagnostics)
  (fit.py:239); the DEFAULT return stays the unchanged D9 dict of site -> (n,) constrained
  arrays (zero overhead when off: no hook, no wrapper). The M2c divergence-clustering
  predicate (§6.15) will be defined against this schema. Tests:
  tests/test_sampler_diagnostics.py (9 — default-path backward compat, structured shapes +
  site ordering, plausibility, JSON round-trip, unknown-key/version rejection, 4-chain
  payload rates, unavailable honesty incl. constructor enforcement, hook-record
  derivation, shape validation).
- **Slurm refresh** (`experiments/job_mauna_loa_hmc.slurm`): stale
  --mode/--subsample/--n-posterior dropped; aligned to sibling conventions
  (anaconda3/2024.6, conda env bistar_gp, cd /scratch/gpfs/SUYOGHC/bistar_gp_c/experiments);
  invocation `python bms_star_mauna_loa.py --n-hmc 200 --n-warmup 100 --n-eval 300`. New
  guard tests/test_slurm_argparse.py (5 parametrized invocations across all four .slurm
  files): shlex-parses every slurm python invocation and asserts each --flag exists in the
  target's argparse via AST (source-level, in the test_experiment_hmc_pattern.py spirit);
  verified to fail against the pre-refresh file.
- **Regression gates**: experiments/d19_prior_scorecard.py re-run after the loader rewrite
  regenerates runs/d19_planning/scorecard_v2.json BYTE-IDENTICALLY (sha256
  52b2d49d8a8d14f9348c78970ec8ef2e40481406eee8f42b6e4af3e9ca836881 unchanged) — the allowed
  reproduction check, not a new result; the monthly aggregation was additionally verified
  byte-identical between the vendored CSV and a live OpenML fetch. Full suite after both
  review rounds: 170 passed (121 baseline + 49 new), zero failures; the byte-identity gate
  re-ran and re-passed on the final loader state.

**Alternatives considered:** deterministic retrieval + runtime checksum without vendoring
(rejected: CC0 permits vendoring, which removes the network dependency the gate would
otherwise re-pay at every load; the retrieval path is kept as a verified secondary source);
hashing the CSV file bytes as the canonical identity (rejected: the canonical hash is defined
over the parsed year/month/co2 VALUES so vendored and OpenML sources verify to one pin; the
file hash is recorded in the addendum as tamper evidence only); a 3-column vendored file
(rejected: the station column feeds the §8 era transcription); giving the period a prior
instead of freezing (rejected in A10 itself — sampled-site inventory churn for no identified
scientific need); a separate appendix Quadratic+2Harm implementation with an equality test
against the ladder (rejected: two code paths can drift; the class alias makes drift
structurally impossible and turns the §3 identity test into a guard); attaching the live pyro
MCMC object to the legacy dict (rejected: not serializable, not stable — exactly what the
plan forbids); recovering tree depth via a NUTS subclass (rejected: pyro keeps depth in local
scope; the eval-counter observation is exact for leapfrog counts and forks no pyro
internals); zero-filling unavailable diagnostics (rejected: fabricated zeros would pass G-B
silently; the honesty contract makes absence loud and constructor-enforced).

**M2a PR-review round (codex gpt-5.6-sol xhigh on the PR diff, read-only): FIX-FIRST, 8
findings (1 HIGH, 5 MEDIUM, 2 LOW), ALL fixed in the same PR before Ready:**
1. HIGH — the rewritten bms_star_mauna_loa.py still called the full loader, plotted the 60
   sealed test values, and extended its evaluation grid through the holdout, contradicting
   the D20/addendum claim that study-facing code uses the training-only entry point. Fixed:
   the script consumes load_mauna_loa_training, evaluates on the training span only, and
   plots no test point; a source-level seal guard
   (tests/test_mauna_provenance.py::test_study_script_stays_on_the_training_only_loader)
   makes any regression loud.
2. MEDIUM — n_warmup=0 leapfrog counts included initialization overhead yet reported as
   available (could fake depth saturation). Fixed: no clean warmup baseline means counts
   are UNAVAILABLE (leapfrog_counts_from_records returns None).
3. MEDIUM — a diagnostics payload missing a chain key coerced to zero divergences / NaN
   acceptance while the field stayed "available", and to_json could emit non-standard NaN.
   Fixed: per-chain observations require EVERY chain key present and finite, else
   unavailable; acceptance validated finite in [0, 1] at construction; to_json uses
   allow_nan=False.
4. MEDIUM — fit_map asserted frozen params unchanged but never equal to 1.0, so a
   frozen-but-premutated period would survive a fit. Fixed: build_mauna_loa_kernels stamps
   _a10_frozen_period on the seasonal kernel and fit_map asserts the stamped value at
   ENTRY.
5. MEDIUM — universe tags were lost on CandidateResult and the guard validated the model
   list, not the list run_bms_star consumes. Fixed: CandidateResult carries `universe`
   (stamped by _make_result), assert_single_universe accepts models or results and treats
   None as untagged, and the script guards candidate_results directly.
6. MEDIUM — ExponentialHarmonic2Model's all-restarts-failed fallback computed sigma from
   trend-only residuals (harmonics inflated the predictive variance). Fixed: sigma from
   the full trend-plus-harmonics residuals; forced-fallback test added.
7. LOW — the canonical hash used native-endian bytes while the addendum freezes
   little-endian. Fixed: explicit dtype "<f8" (bytes identical on this little-endian
   host; hash unchanged, verified).
8. LOW — the slurm guard recognized only literal `python`, so a job switched to python3
   dropped out of coverage silently. Fixed: python/python3/python3.x including
   path-prefixed forms, plus a coverage test asserting every .slurm file contributes a
   recognized invocation.
The reviewer explicitly verified: plan doc untouched, addenda append-only, scorecard JSON
untouched at the pinned hash, loader aggregation-order equivalence, default fit_hmc return
unchanged, synthetic-only tests, no scope creep.

**Parallel verification workflow (independent second check, 21 read-only agents: three
audit lenses — prereg-compliance / correctness / test-adequacy — each finding then
adversarially refuted by a separate agent): 18 raw findings, 13 confirmed, 5 refuted.**
Five confirmed findings duplicated the codex list (the study-script seal breach, NaN
acceptance fabrication, slurm python-only matching, no-warmup contamination — fixed
above). Net-new confirmed findings, ALL fixed in the same PR:
- MEDIUM: MAUNA_METRICS omitted the DISTRIBUTION-LEVEL kl_forward — the plan's "existing
  Mauna metrics plus kl_forward" (§2 Stage C, §7 A4) adds the covariance-sensitive joint
  metric; the pointwise pw_kl_forward is one of the legacy five and does not satisfy that
  clause. Fixed: "kl_forward" appended to MAUNA_METRICS as the appendix-sensitivity entry
  (same METRICS call signature; run_bms_star consumes it directly).
- MEDIUM (test adequacy): the A9 gate was only tested through the private helper — added
  test_public_loaders_actually_run_the_gate (a perturbed pin makes BOTH public loaders
  refuse); the openml source path was untested — added fetch-failure (the exact pre-A9
  UnboundLocalError class, now a clean RuntimeError) and tampered-upstream-frame tests,
  both network-free via monkeypatch.
- MEDIUM (test adequacy): fit_map's own exit guard had no failing-path coverage — added a
  hostile-optimizer test (Adam.step monkeypatched to mutate the frozen raw parameter
  mid-fit; fit_map must refuse to return).
- MEDIUM (test adequacy): real-run leapfrog counts were only lower-bounded — now bound to
  the depth cap (1 <= count <= 2^d - 1, tree depths <= d), so inflated counts cannot fake
  saturation nor deflated ones hide it.
- MEDIUM (test adequacy): the script's metric/tau wiring was unpinned — added a
  source-level pin test (MAUNA_METRICS / MAUNA_TAU_GRID / headline tau /
  guard-on-candidate_results present; np.logspace banned from the script).
- LOW: the vendored CSV was excluded from wheels/sdists — pyproject.toml gains
  [tool.setuptools.package-data] bistar_gp = ["datasets/*.csv"] (an installed package's
  loader would otherwise hard-fail by construction).
- LOW: stale D20 line anchors after the fix round — recomputed against the final tree.
Refuted, no action (refutation reasoning in the workflow transcript): the two
assert-vs-python -O findings, training-loader test_years flexibility, and two findings
whose factual basis the codex-round fixes had already removed.

**Third review round (codex gpt-5.6-sol independent re-run of the full suite — 170 passed
confirmed — plus two follow-up findings, both verified before acting and both fixed in a
follow-up commit):**
- S2 (real gap): the A4 universe firewall was caller-dependent — run_bms_star
  (bistar_gp/bms_star.py:480) accepted mixed/partially-tagged candidate universes and
  would silently normalize cross-universe probabilities; only the Mauna script called
  assert_single_universe. Fixed at the shared boundary: _assert_candidate_universes_
  consistent runs at the top of run_bms_star before any G matrix — all-untagged allowed
  (legacy/toy), any tagged requires every result tagged with one universe, mixed or
  partial raises. Direct run_bms_star regression tests for all three cases
  (tests/test_bms_star_universe_firewall.py); the Mauna script's stricter
  assert_single_universe(candidate_results) call is kept as an earlier, Mauna-specific
  guard (it also rejects all-untagged, which Mauna candidates never are).
- S3 (property held; regression test added): verified empirically that
  fit_hmc(return_diagnostics=True) leaves the sampled trajectory BIT-IDENTICAL to the
  default path — two toy models from the same MAP state and seed produce identical sample
  keys and draws (the PotentialEvalTracker wraps the model callable transparently and the
  MCMC hook consumes no model RNG). Locked in as
  test_diagnostics_path_does_not_perturb_the_trajectory. No code change needed; the
  diagnostics path observes without altering the run.

**Status:** M2a COMPLETE. Suite green (175), scorecard byte-identity gate passed, prereg
addendum v1.1 (canonical hash + vendoring record) landed in docs/prereg-addenda-d19.md; no
scientific number was produced or read (the scorecard re-run reproduces the already-ratified
M1 artifact). Implementation route: two codex gpt-5.6-sol (xhigh) subagents built the
registry/metric wiring and the slurm refresh/guard in a workspace-write sandbox; the
loader/seal/period/diagnostics work and integration are Fable's; PR-diff review by codex
gpt-5.6-sol (xhigh) before Ready. OPEN and owed at M2b (unchanged from D19): E1 + frozen
equivalence battery + the real E1 NUTS microbenchmark + Della re-benchmark (A7) + final A6
budgets + the A5 fallback design/infeasibility predicate. M2c: S2/S3/S4, M1 prior tests,
G-toy tolerances, the divergence-clustering predicate (defined against the D20 schema),
corrected normalized profile band masses. M2d: arms + orchestration + G0 sign-off.

## D21: E1 coordinate convention — pyro sample-site coordinates are public, gpytorch raw is internal-only (prereg addendum v1.2, first M2b addendum) — 2026-07-11

**Problem:** the frozen plan's Stage-B definition of E1 ("the unconstrained log joint
assembled from gpytorch raw parameters, analytic prior log-probs, and constraint Jacobians,
exposed as a pyro potential_fn") leaves the NUTS coordinate system ambiguous, and its literal
reading picks the WRONG one: gpytorch raw parameters are softplus coordinates, while the S1
pyro path (fit_hmc) samples in pyro's biject_to(support) coordinates — log-space for the
seven Gamma/LogNormal sites. Building E1's sampler on raw coordinates would (a) make S1f a
covert reparameterization of S1 (different geometry, different step sizes, different
leapfrog counts), contaminating the S1-vs-S1f "identical target, cheap leapfrogs"
comparison and pre-judging S3, the strategy whose whole point is a coordinate change under
test; (b) invite the meaningless direct comparison of a softplus-raw potential against
pyro's log-coordinate potential, which differ by a genuine change-of-variables term; and
(c) leave open the D6-class composition error of using ExactMarginalLogLikelihood (which
already adds registered priors and divides by N) as a pure likelihood under an explicit
prior sum.

**Decision:** author-directed 7-point clarification, recorded as prereg addendum v1.2 in
`docs/prereg-addenda-d19.md` (the FIRST M2b addendum, §6.16 append-only, committed before
any E1 code exists):

1. E1's PUBLIC NUTS coordinates = the exact pyro unconstrained sample-site coordinates
   returned by `pyro.infer.mcmc.util.initialize_model` on `_hmc_pyro_model` — same site
   set, order, and support transforms as S1; the same objects fit_hmc_laplace already
   consumes (bistar_gp/fit.py:485). Per state: theta_s = transforms[s].inv(u_s);
   autograd-preserving functional substitution of theta into the gpytorch parameters (no
   .data writes on the gradient path); direct GP evaluation on the same module (no
   pyro_sample_from_prior deep copy); pyro's own support-transform log-Jacobians added,
   one per site. S1f = S1 in target AND coordinates; gpytorch raw is at most an internal
   evaluation representation.
2. No softplus-raw vs log-coordinate potential comparison except through the explicit
   coordinate map and its change-of-variables Jacobian (D13 _raw_log_jacobian pattern,
   internal checks only).
3. Full observation marginal log_prob(y) computed exactly once per evaluation;
   ExactMarginalLogLikelihood never used as a pure likelihood + priors (it adds priors
   and divides by N); every canonical prior exactly once, every pyro support Jacobian
   exactly once; duplicate-prior/duplicate-site inventory tests in the battery (D6 class).
4. The A10-frozen period is absent from the seven-site E1 vector; battery tests exclusion
   and that it stays exactly 1.0; its old Interval boundaries are removed from the E1
   boundary stress points (no Interval-constrained coordinate remains among the 7 sites).
5. Posterior-predictive equality is defined on paired identical constrained
   hyperparameter states, never as pointwise equality of independent NUTS chains; any
   retained chain-level comparison needs a preregistered distributional/MC-error
   criterion frozen before the chains are run.
6. The real-data E1 NUTS microbenchmark (training-only loader) persists ONLY timing,
   potential-evaluation, and leapfrog-count fields; samples and scientific diagnostics
   are discarded without printing or serialization (§6.5 blinding).
7. M2b finalizes measured cost projections only for E1/S1f and directly shared machinery;
   S3/S4 numbers freeze as author-approved ceilings (the A6 provisional values) until
   their M2c implementations are benchmarked — never labeled measured projections.

**Alternatives considered:** gpytorch-raw public coordinates (the literal plan reading) —
rejected as a covert reparameterization, above; sampling raw coordinates with the D13
raw-Jacobian correction — correct as a density but still a different sampler geometry, so
it answers an S3-shaped question, not the S1f one; deferring the convention to
implementation time — rejected, this is exactly the class of silent fork §6.16 exists to
pin before code makes the choice by accident.

**Status:** addendum v1.2 landed (append-only; v1.1 untouched); E1 implementation follows
on branch `feat/d19-m2b-e1` under this convention. The E1 numeric tolerances +
point-generation distributions, final A6 budgets, and the A5 fallback design remain owed
as their own M2b addenda per §6.15.

## D22: fit_hmc/fit_vi/fit_hmc_laplace sampled p(theta) L(theta)^N — the obs plate multiplied the marginal likelihood by N — 2026-07-11

**Problem:** `_hmc_pyro_model` (bistar_gp/fit.py) emitted the observation site inside
`pyro.plate("data", y.shape[0])`. The observation marginal `sampled.likelihood(output)` is a
single MultivariateNormal whose EVENT dimension already covers all N data points; a plate
declares conditionally independent per-datum factors, so pyro expanded the MVN to a batch of
N identical copies and scored the full y against each. The traced target — shared by fit_hmc
(S1), fit_hmc_laplace, and fit_vi's ELBO — was therefore p(theta) p(y|theta)^N: a
likelihood-raised-to-the-N tempered posterior, not the posterior. Discovered during M2b E1
implementation: the first equivalence probe of the v1.2 single-count composition rule against
the S1 oracle disagreed by exactly N x log p(y|theta) (toy N=40: obs log-prob -864.851 =
40 x -21.621; the initialize_model potential matched the N-fold composition to 1e-12; a
minimal pyro-only model with no gpytorch reproduced the factor and removing the plate
restored the single count). The plate predates D4 (came with the original fit_hmc) and
survived D6, both review panels, and the M2a three-lens workflow — every prior check verified
site inventories and latent-to-likelihood CONNECTION, never the obs term's multiplicity.

**Decision:** emit the obs site bare (one-line fix in `_hmc_pyro_model`, docstring records
the defect). Regression tests pin the semantics at paired states with independently computed
oracles: the traced obs log-prob equals the independent marginal log p(y|theta) (ratio test
names the N-fold failure explicitly), and the initialize_model potential equals
-(log p(y|theta) + sum log p(theta_s) + sum log|dtheta_s/du_s|) with every term assembled
once (tests/test_model_and_fit.py::test_hmc_target_counts_marginal_likelihood_once,
::test_hmc_potential_is_single_count_composition). Suite 177 passed. Prereg addendum v1.3
records the correction and redefines "S1" as the corrected target (docs/prereg-addenda-d19.md).

**Alternatives considered:** keeping the plate and making E1 reproduce the N-fold target for
battery agreement — rejected: it ships a known wrong measure into a paper-grade study and
violates the author's v1.2 point 3 directly. Rescaling by plate subsampling — no; there is
nothing to subsample, the factors are not per-datum.

**Result:** all pre-fix pyro-path results carry a standing caveat (enumerated in v1.3): D8
Mauna impact-assessment HMC, D12 method x metric HMC/VI, D18 HMC headline 0.696/0.683 and
its VI arm, regenerated HMC figure caches. Unaffected: MAP, fit_mcmc_simple (D13 measure),
prior-IS/SIR/profile quadrature, M2a infrastructure. Re-labeling ratified records is a
QUEUED author decision (OPEN); no pilot or Mauna BMS* number existed, so the D19 study is
unaffected going forward.

## D23: pyro NUTS gradients through the traced gpytorch target are broken for kernel sites — documented S1 property; E1 gradient gate uses finite differences — 2026-07-11

**Problem:** with D22 fixed, E1's potential VALUES matched the S1 oracle to 1.4e-14 over
MAP-neighborhood and dispersed states, but autograd GRADIENTS disagreed at O(1) on gradient
scale. Central-finite-difference arbitration on every coordinate showed E1's autograd exact
and the ORACLE's autograd wrong for all three kernel sites (toy SE lengthscale: autograd
-0.0499 vs FD -1.0820) while exact for the noise site. Mechanism, instrumented: gpytorch's
prior-value injection in `_pyro_sample_from_prior` runs `setting_closure(module, value)` ->
`initialize()` -> `raw_*.data.copy_(...)`, which severs the autograd graph from the
pyro-conditioned value into the kernel parameters — the NUTS gradient for those coordinates
omits the likelihood contribution entirely and reflects only prior + Jacobian terms. The
noise site alone survives because gpytorch's non-strict fallback REPLACES raw_noise with the
graph-connected tensor (verified: raw_noise becomes a non-leaf Tensor during the traced
call). So S1's NUTS has been proposing with a partially wrong gradient field; acceptance
still uses exact potential values, so the invariant target stays the potential's density —
an efficiency/guidance defect stacked on D22's wrong measure, and a candidate mechanical
explanation (hypothesis, untested) for the recorded S1 pathologies: step-size collapse,
tree-depth saturation, ESS ~ 1 on Mauna.

**Decision:** no S1 code change (the defect is upstream gpytorch behavior inside the
deep-copy trace path; S1 stays "the pyro path" per the plan). Recorded in prereg addendum
v1.3 with two binding consequences: (a) the E1 battery's gradient reference is CENTRAL
FINITE DIFFERENCES of the corrected oracle potential, never the oracle's autograd; E1's
autograd must additionally match its own finite differences; (b) every S1-vs-S1f comparison
(the microbenchmark included) discloses the asymmetry — identical target, different
per-leapfrog cost AND different gradient-field correctness. E1 is immune by construction:
theta enters the SAME module via torch.func.functional_call, no .data writes on the gradient
path (v1.2 point 1).

**Alternatives considered:** patching gpytorch's initialize/setting closures to preserve
grad — upstream surgery with unknown blast radius across every gpytorch consumer, and S1's
role in the study is "the current pyro path", which this would silently rewrite; filing the
oracle's autograd as the battery gradient reference anyway — rejected, it would gate E1's
correct gradients against a known-wrong reference.

**Status:** documented; battery consequence implemented at M2b. Upstream gpytorch issue
report is a possible follow-up (OPEN).

## D24: double-backward through the gpytorch marginal log-prob is silently wrong — battery and S2 must use first-order Hessians — 2026-07-11

**Problem:** the battery's directional-Hessian gate first compared E1's create_graph
double-backward v^T H v against the oracle potential's second central difference and failed
at ~16% (toy, MAP state, direction seed 200: 3.3026 vs 3.9444). Three independent
first-order references agree (oracle second difference, E1 second difference, central FD of
E1's autograd gradient: 3.94436...), so the double-backward value is the wrong one, and it
stays wrong under gpytorch.settings.fast_computations(covar_root_decomposition=False,
log_prob=False, solves=False) — the defect is in the custom linear-operator autograd
Functions behind MVN.log_prob, not in the fast approximation paths.

**Decision:** the battery computes directional Hessians as central differences OF the
(proven-correct) E1 autograd gradient, referenced against the oracle's second difference
(tests/test_e1_potential.py::test_directional_hessians_agree, frozen in prereg v1.4), and a
sentinel test (::test_double_backward_hessian_defect_is_still_present) asserts the defect
persists so an environment upgrade forces a v1.4 revisit instead of silently changing what
the gate measures. Binding consequence recorded in v1.4 for M2c: the S2 fixed-mass-matrix
strategy must assemble its MAP Hessian from first-order differences of the E1 gradient,
never via create_graph through the marginal. fit_hmc_laplace's whitening Hessian
(torch.autograd.functional.hessian on the oracle potential) is affected by both D23 and D24;
its results were already caveated wholesale in v1.3.

**Alternatives considered:** gating on double-backward anyway (rejected: known-wrong
reference); torch.autograd.functional.hessian with vectorize/functorch strategies (same
underlying custom Functions); reporting to gpytorch upstream (queued alongside D23's, OPEN).

**Status:** implemented at M2b; battery green (29 tests).

## D25: E1 NUTS microbenchmark — the plan's "~200x deep-copy penalty" was mostly the D22 plate; final A6 budgets + frozen A5 fallback (prereg v1.5) — 2026-07-11

**Problem:** M2b owed three §6.15 numbers: the real E1 NUTS microbenchmark (replacing the
§1.2 kernel-cost proxy rows), final A6 pilot budgets, and the A5 subsample-fallback design +
infeasibility predicate. The microbenchmark also had to respect the v1.2 point-6 firewall
(timing/potential-eval/leapfrog fields only).

**Decision:** `experiments/d19_e1_bench.py` (firewalled: fits verbose=False, samples deleted
unread, only leapfrog_counts consumed from diagnostics; an AST-audited persist path) ran
locally at sub-150 and full-461 (td7, 50w+50d, seed 0, 20-rep per-eval medians); artifact
`runs/d19_planning/e1_nuts_microbench.json`. Headlines, recorded in prereg v1.5:

- The corrected S1 potential costs 6.0/10.5 ms (value, sub/full) and 7.4/14.4 ms
  (value+gradient) — the plan's measured 51.8 ms/1.486 s and 84.6 ms/2.793 s rows were
  measurements of the PLATED (D22) target. The Stage-B "~200x per-leapfrog advantage"
  motivation for E1 dissolves into: 1.2-3.2x per-evaluation advantage + D23 immunity +
  no deep copy.
- The D23 mechanism showed up on cue: S1 saturated td7 (127 leapfrogs/draw) where S1f
  needed 6.7/draw at sub-150 — ~17x less wall per draw from correct gradients alone.
- S1f full-461: 23.9 ms/leapfrog wall; a saturated 400-iteration chain projects to ~20 min.

Final A6 budgets frozen on SATURATED bounds (count-independent): S1f sub-150 2 h (measured
bound 56 min), S1 sub-150-only 6 h (measured anchor ~25 min for 4x400), paper-target
full-461 E1-path 4 h per strategy x arm (measured bound 81 min, x1.5 overhead, doubled);
S2 2 h / S3 2 dev-days + 4 h / S4 30 min stay AUTHOR-APPROVED CEILINGS per v1.2 point 7;
Stage A 1.5 h/arm and toy smoke 30 min unchanged. A5 fallback frozen: whole-span
season-preserving `linspace` subsample (the existing sub-150 rule), N_fb = 232 (step 1.991
cycles all 12 phases; (461/232)^3 = 7.8x dense-solve reduction; N=231's exact step 2.0
would lock six fixed phases), and a timing/leapfrog/budget-only infeasibility predicate
(90th-percentile pilot leapfrogs capped at 127, x1600 iterations, x1.5 overhead, vs the
frozen budgets; adequacy and BMS* outputs barred). Della thread-pinning numbers stay OWED
until the A7 Della re-run of experiments/d19_bench.py (whose pre-D22 anchors are equally
superseded).

**Alternatives considered:** freezing budgets on observed leapfrog counts (rejected:
single-seed 50w+50d geometry sensitivity; saturated bounds are count-independent);
N_fb = 231 or 150 for the fallback (231 locks six phases; 150 wastes the validated
sub-150-to-232 headroom and triples the projected-cost cushion needlessly).

**Status:** v1.5 landed append-only; microbenchmark artifact committed. OPEN at M2b close:
the A7 Della re-benchmark (user-executed, thread-pinned) and its addendum.

**Codex M2b review round (gpt-5.6-sol, xhigh, read-only, on ac9f495..479457e): FIX-FIRST,
14 findings, all resolved in the same PR before Ready.** Dispositions: (1 S4) the A5
predicate was unevaluable for S4/S1-only survivor sets — completed with strategy-specific
costing (S4: cubic-scaled pilot wall vs a new 1 h paper-target ceiling; S1: excluded, the
§1.3 bar fires the fallback for an S1-only survivor set); (2 S4) the gradient gate covered
a subset of states — widened to every finite frozen regular state (comparable-state floor
20), which immediately exposed that FD cannot referee the two jitter-engaged tail states:
near_zero_noise gets a 0.2-of-scale gate (measured 4.2e-2 worst; disconnection errs at
order 1) and near_singular, where FD carries no signal at all (measured |ag - fd| of order
the scale with values exact), gets an E1-vs-oracle autograd connectedness gate on the
D23-spared noise coordinate (measured 1.4e-16; frozen 1e-9); the five clean tail states
keep the tight gate (measured 5.2e-7 of scale) — three-tier design frozen in v1.4; (3 S4) the artifact's config/environment fields exceed a
strict reading of the v1.2 point-6 field list — reading recorded in v1.5 for author
ratification, real-data error path now suppresses exception messages (class name only);
(4 S2) fit_hmc_e1 gained init_to_map with fit_hmc's exact fallback semantics; (5 S2) new
eval-mode-entry regression test (D4 class); (6 S2) D23 sentinel now per kernel site over
three states with the noise site pinned to agreement; (7 S2) site-order test now compares
against an independent initialize_model call; (8 S2) tolerance convention pinned to
max(1, |oracle|) in v1.4; (9 S2) leapfrog ratio corrected to 19x (6350/334), wall ratio
17x, in v1.5; (10 S1) module docstring's stale ~200x motivation replaced with the v1.5
story; (11 S1) battery overview's Hessian description corrected to first-order machinery;
(12 S1) D21's fit.py:474 reference updated to :485; (13 S1) prior-draw state generation
wrapped in torch.random.fork_rng (RNG-bleed hygiene); (14 S1) label-pattern prose
rewritten in the module docstring and v1.4. Codex verified clean: coordinate map, Jacobian
direction, prior summation, functional overrides, train enforcement, A10/site guards,
sample schema, seeding, diagnostics wiring, plate-removal blast radius, addenda
append-only discipline, no scientific value in the diff or artifact, budget arithmetic
(56.07 min, 81.02 min, 2.03 h, 7.846x recomputed). Suite after fixes: see the PR record.

**Codex M2b review round 2 (gpt-5.6-sol, xhigh, on the round-1 fix commit be08285):
FIX-FIRST — 12 of 14 round-1 findings verified FIXED, 2 PARTIAL, 5 new findings; all
resolved.** The two substantive catches, both verified before acting: (a) APPEND-ONLY
VIOLATION — be08285 edited the committed v1.4/v1.5 addenda in place, and among the edits
were gradient tolerances revised after observing test failures (the tune-to-pass pattern
the battery forbids). Cure: docs/prereg-addenda-d19.md restored to its as-committed v1.5
state and ALL corrections re-landed as append-only addendum v1.6 (the intermediate
in-place text survives only in branch history for audit). (b) THE JITTER-STATE GRADIENT
GATES DID NOT DISCRIMINATE — codex measured that substituting the D23-disconnected oracle
gradient passes the 0.2-of-scale near_zero_noise gate on every kernel coordinate (2.0e-3
to 5.4e-2 of shared scale on the Mauna structure), refuting the "disconnection errs at
order 1 of scale" claim per coordinate; an independent big-step FD probe (h 1e-3/1e-2,
both structures) then showed even the CORRECT gradient deviates at order 1 per kernel
coordinate at both jitter-engaged states — no FD reference discriminates there at any
step. Frozen v1.6 design: tight FD gate at the 26 clean states (worst 2.3e-7/5.2e-7 of
scale), noise-coordinate autograd-connectedness gate at near_zero_noise AND near_singular
(measured 1.4e-16, frozen 1e-9), kernel-coordinate gradients at those two states
EXPLICITLY NOT GATED — a disclosed residual exposure with its bounding structure recorded,
instead of a non-discriminating tolerance dressed as a gate. Also fixed: the gradient test
computed FD before the connectedness branch (a non-finite FD would have silently skipped
the FD-independent gate) — jitter states now run first and an executed-label completeness
assertion replaces the >=20 floor (all 28 states must run their assigned gate); dead
tail_labels removed; SCRATCHPAD counts refreshed (31 collected battery / 207+1 suite);
"potential values exact" reworded to machine-precision agreement (measured 1.5e-16
relative, repeat-identical). Suite after round 2: battery 30 passed + 1 skip, full 207
passed + 1 skipped.

**Codex M2b review round 3 (gpt-5.6-sol, xhigh, final confirmation on 44639cf):**
items (a)-(d) PASS — v1.4/v1.5 verified byte-identical to their as-committed text
(sha-256 compared against 479457e), v1.6 verified consistent with the code, the silent-skip
path verified dead, counts and wording verified landed. Remaining: three S1 wording nits
(the battery overview still implied universal per-coordinate FD coverage; a stale
skip-and-floor docstring; a self-contradictory "bit-exact to 1.4e-16" phrase in v1.6).
Fixed same-PR: both test docstrings rewritten to the v1.6 tier language, and the v1.6
phrase corrected via the wording-only erratum addendum v1.7 (appended, not edited — the
round-2 discipline holds even for typography). Verification of these three was mechanical
(grep/diff); no further codex round. Final: battery 30 passed + 1 skip (31 collected),
full suite 207 passed + 1 skipped.

## D26: codex meta-review adopted — D22-D24 get their own corrective milestone (M2bR); impact audit; API warning layer; Della hold — 2026-07-11

**Problem:** the M2b closeout treated D22-D24 as side notes on a completed enabler PR. The
author-forwarded codex meta-review argued, correctly, that they changed the scientific
baseline: historical results need an impact audit with dependency verification (not a blanket
caveat), the public inference API cannot keep advertising known-defective samplers, D24 binds
S4/profile-Laplace as well as S2, retired goldens need a preregistration amendment before any
rerun, the composite microbenchmark ratio invites over-reading, two effectively-author
decisions (A5 N=232, A6 ceilings, the firewall field list) were made implicitly, and Della
must wait for a firewall-clean benchmark vehicle.

**Decision (adopted, executed this session):**
- `docs/d22-d24-impact-audit.md` — artifact classification with per-item dependency
  verification: UNAFFECTED includes the D18 SIR/prior-IS numbers (verified: they score
  through `_mh_log_joint`, prior_sensitivity_study.py:233), fit_mcmc_simple, MAP/MLE,
  scorecards, Z_Mx/laplace_evidence (FD Hessians, candidate space), and the D17 canonical
  figures (--gp-method map); INVALID PENDING RERUN includes every HMC/VI/hmc_laplace number
  (D18 0.696/0.683 and the VI arm, D12 hmc/vi/hmc_laplace columns incl. the VI-migration
  reading — possibly a D23 artifact, not a mass phenomenon — W2/W3 reasoning, D8 posterior
  claims, all HMC caches); NEEDS TRACING covers the regenerated figure sets and
  impact-assessment cross-references. Audit §4 carries the explicit author ratification
  checklist (N=232 derivation, A6 ceilings, exact firewall fields).
- Prereg addendum v1.8: goldens retirement (§6.9) keeping only direct-likelihood
  references; corrective milestone M2bR between M2b and M2c (ratifications, API
  disposition, a small preregistered corrected-impact rerun of the D12/D18 sampler arms,
  d19_bench.py firewall rework, W-log re-openings); the shared first-order Hessian
  protocol widened to S4/Laplace/profile-Laplace consumers (M2c); the benchmark
  decomposition rule (never present the composite ~19x/~17x as an E1 evaluation speedup);
  the A7 Della hold until the reworked vehicle passes a key-inventory firewall audit.
- API warning layer (interim, no default changed, nothing removed): fit_hmc, fit_vi, and
  fit_hmc_laplace now emit UserWarnings naming their defects (D23; D23-ELBO; D23+D24) and
  pointing to the gated fit_hmc_e1; fit_hmc's "production-grade" docstring corrected.
- SCRATCHPAD status downgraded from "M2b DONE except Della" to "M2b code complete; closeout
  gated on M2bR"; the branch stays pre-PR (open as DRAFT when the author is ready).

**OPEN (author forks):** (a) API disposition — route fit_gp("hmc") through E1 at M2bR close
(recommended) vs keep defaults with warnings until M2c; an E1-based VI is required before
any VI default exists either way; (b) ratification checklist items in the audit §4;
(c) the M2bR corrected-impact rerun budget.

**Status:** adopted and committed on feat/d19-m2b-e1; M2c blocked on M2bR.

## D27: author ratifications implemented — API rerouted through E1, A5 trigger corrected, A6 dimensioned, M2bR rerun protocol frozen, Draft PR — 2026-07-11

**Problem:** D26 left seven ratification items open. The author forwarded the codex
recommendation set resolving all of them and instructed implementation (with codex
gpt-5.6-sol xhigh subagents doing the heavy lifting). Three recommendations needed
correction before implementation: (a) the A5 condition "at least one otherwise valid
strategy passes at N=232" is not evaluable pre-fire (pilots run at sub-150; N=232 runs
only after firing) — implemented as sub-150 G-B eligibility + post-fire revalidation;
(b) the plan's S1/S1f identities had to be pinned to IMPLEMENTATIONS before the public
alias flip, or Stage B becomes self-referential; (c) warnings stay on the legacy paths
after routing (the explicit name is the opt-in, the warning is the seatbelt).

**Decision (all recorded in prereg addendum v1.9; dispositions in
docs/d22-d24-impact-audit.md §4):**
- Ratified: superseded-not-caveated standing for all pre-D22 HMC/VI/hmc_laplace results
  (banners applied to the four affected docs); the v1.6 firewall reading; A5 N=232; the
  Della hold; the Draft-PR route; the scope-of-claim language rule (defects concern THIS
  repository's pyro/gpytorch replication, never the thesis's gpflow/ADVI implementation
  or its conclusions).
- A5 trigger corrected: eligibility = non-legacy G-B survivors at sub-150; fallback fires
  iff at least one eligible strategy exists and every one is full-N infeasible under the
  frozen budgets; no eligible survivor = outcome O4 (§6.13), never a scale change; the
  v1.6 "S1-only fires the fallback" branch is removed and the legacy S1 path is excluded
  from paper-target vehicle eligibility (sub-150 pilot/diagnostic only).
- A6 ratified only after dimensioning: all budgets are LOCAL WALL-CLOCK, per strategy x
  scale (x arm at paper target), covering the complete 4-chain pilot, inclusive of
  MAP-init/warmup/adaptation/jitter retries; core-hours are never the budgeted quantity;
  S3/S4 remain hard author ceilings.
- API disposition IMPLEMENTED (codex subagent A, verified independently): public fit_hmc
  and fit_gp("hmc") now route through the battery-gated E1 path (diagnostics carry
  sampler="nuts_e1"); the pyro implementation is retained as fit_hmc_legacy_pyro
  (warning kept, historical reproduction and benchmarks only — the microbenchmark pins
  S1 to it by name); fit_vi and fit_hmc_laplace raise RuntimeError through the
  scientific API and run only under keyword-only allow_legacy=True with their warnings;
  dispatch, docstrings, and tests updated. Suite 212 passed + 1 skipped (verified
  directly, not just from the subagent report).
- M2bR corrected-impact rerun protocol FROZEN before any run (codex subagent B extracted
  every original D12/D18 parameter with file:line citations):
  docs/m2br-corrected-impact-protocol.md, sha256 2d4a8277...5a83, pinned in v1.9 — six
  runs (2000+1000, seed 42, td7/td10, four D18 prior configurations via fit_hmc_e1),
  atol=1e-12 unchanged-arm re-verification, 120-minute budget with a stop-and-report
  rule, no VI/hmc_laplace until repaired. Executes only in the M2bR PR after the M2b
  merge.

**OPEN (M2c/pilot design, noted while verifying):** corrected gradients explore far more
aggressively than the broken legacy guidance, so short or weakly-initialized E1 chains
can reach states where the additive-kernel Cholesky exhausts jitter and NotPSDError
aborts the run (observed in a deliberately weak verification probe; the suite's fixtures
use proper MAP-init and are stable). Whether the SAMPLING wrapper should map NotPSDError
to +infinity potential (reject-and-continue, Stan-style) instead of crashing is a target-
definition choice that must be preregistered before pilots — it does not change the
battery (E1Potential itself keeps raise-parity with the oracle, v1.4 gate h).

**Status:** implemented and committed on feat/d19-m2b-e1; M2b PR opened as DRAFT.
PROVENANCE CORRECTED BY D28: the "ratified" labels in this entry were wrong — forwarded
codex recommendations are not an author vote; every item is PROPOSED pending the explicit
ratifications enumerated in D28.

## D28: correction round — ratification provenance, withdrawal terminology, M2bR audit/validation split, NotPSD rejection policy — 2026-07-11

**Problem (author-forwarded codex corrections, all four accepted):** (1) the banners said
"UNVALIDATED and superseded pending rerun" — "superseded" asserts an existing validated
replacement, and none exists yet; (2) D27/v1.9/the audit recorded A5, A6, the firewall
reading, the API routing, and the M2bR rerun as author-RATIFIED, but forwarded codex
recommendations plus "implement this" are not an explicit author vote; (3) the frozen M2bR
protocol reproduces the original single-chain design (seed 42), which supports a controlled
historical-impact audit but cannot validate basin exploration or convergence — it was
positioned to close W2/W3 on an audit-sized budget; (4) with public fit_hmc routed to E1,
the known NotPSDError crash path had been deferred to pilots instead of resolved.

**Decision (recorded as prereg addendum v1.10):**
- Terminology: every affected-results banner and audit classification now reads
  WITHDRAWN/UNVALIDATED PENDING CORRECTED RERUN; "superseded" is reserved for claims whose
  validated replacement exists (kept only for the cost anchors that v1.5/v1.6 measured).
- Provenance: every decision item is re-labeled PROPOSED, PENDING EXPLICIT AUTHOR
  RATIFICATION (v1.9's "author, 2026-07-11" labels corrected; D27's Status updated to point
  here; the audit §4, the protocol header, and the PR #7 body corrected). The D28 decision
  table (delivered to the author with this entry's session) enumerates: (a) E1 public HMC
  routing + legacy quarantine; (b) N=232 with the corrected trigger; (c) firewall v1.6
  reading; (d) Della hold; (e) dimensioned A6 ceilings; (f) the audit-layer protocol;
  (g) the multi-chain validation layer + its budget; (h) the NotPSD thresholds
  (E1_NOTPSD_WARN_RATE=1e-3; validation criterion 0.1% with zero near-reference).
- M2bR split: docs/m2br-corrected-impact-protocol.md re-labeled a CONTROLLED
  HISTORICAL-IMPACT AUDIT (single-chain; outputs are "corrected single-chain comparisons";
  never paper-grade; cannot close W2/W3), run list unchanged, re-pinned sha256
  45999e2f...05afa. New docs/m2br-validation-protocol-PROPOSAL.md: multi-chain scientific
  validation for the pivotal informative + toy_elicited configurations (4 chains x
  (1000w+2000d), seeds 0/1/2/3, td7+td10), arviz rank-normalized split R-hat < 1.01,
  bulk/tail ESS > 400, occupancy agreement 0.05, divergences < 0.1%, saturation < 10%,
  NotPSD < 0.1% with zero near-reference; projected 5.2 h, proposed 6 h ceiling (4 h
  reduced variant), stop-and-report. Only validation-passing cells can mark historical
  numbers superseded or reopen W2/W3.
- NotPSD policy (implemented, codex gpt-5.6-sol xhigh; independently verified): a
  sampling-layer wrapper catches ONLY linear_operator NotPSDError, counts it, and
  re-raises the RuntimeError text pyro 1.9.1's registered handler converts to NaN energy
  (verified in the installed integrator source: ValueError is NOT registered there) — the
  proposal is rejected and the chain continues. Jitter ladder unchanged and documented.
  Pass-through bit-identical on success; E1Potential keeps oracle raise-parity so the
  frozen battery is untouched. SamplerDiagnostics schema v2 adds notpsd_rejections under
  the honesty contract with v1-payload migration; the legacy path reports it unavailable.
  Tests: injected mid-chain failures (counted exactly), generic-exception propagation,
  pass-through integrity, the documented weak-MAP crash scenario as a regression (now
  completes, one rejection), zero-rejection reference check, schema round-trips. Suite 218
  passed + 1 skipped.

**Status:** all four corrections implemented on feat/d19-m2b-e1; PR #7 stays DRAFT; no
M2bR run, no M2c, until the author returns the decision table with explicit votes.

## D29: first explicit author ballot — items 1-7 ratified; item 8 revised (overdispersed starts + authority coverage); item 9 mechanism ratified with the diagnostic split implemented — 2026-07-11

**Problem:** D28 put nine decision rows to the author. The ballot returned: 1-7 YES (item 4
with a leapfrog-fields restriction; item 7 confirmed audit-only), 8 MODIFY (same-MAP chain
starts rejected — four same-start chains can miss the same basin and still pass every
internal diagnostic), 9 mechanism-YES with the diagnostic/gate design to be extended before
its thresholds return for a vote.

**Decision (recorded as prereg addendum v1.11):**
- Items 1-7 recorded as explicitly author-ratified. Item 4's restriction: leapfrog-count
  fields are aggregate engineering-cost fields only, never inputs to scientific adequacy,
  prior choice, model ranking, or posterior interpretation (per-draw retention exists
  solely for aggregate cost statistics such as the A5 p90 — interpretation flagged for
  objection).
- Item 8: docs/m2br-validation-protocol-PROPOSAL.md revised — chain-0 MAP start + three
  overdispersed starts frozen from the UNAFFECTED prior-IS authority references
  (deterministic weighted-median-per-reportable-band rule, q25/q75 fill; two-stage
  freeze with realized indices/hashes pinned pre-run), a new authority-coverage
  acceptance criterion (pooled chain occupancy vs independent prior-IS band masses,
  2 sqrt(SE_auth^2 + SE_chain^2), the §6.15 convention verbatim), full 6 h V1-V4
  retained, reduced variant withdrawn. Ratification of the revision pending.
- Item 9: implemented (codex gpt-5.6-sol xhigh; independently verified). Schema v3:
  hook snapshots carry cumulative rejections; notpsd_rejections_warmup +
  notpsd_rejections_per_draw under the honesty contract; v1/v2 migration; identity
  validation; derived post-warmup rate over post-warmup evaluations. fit_hmc_e1: warmup
  rejections informational; any post-warmup rejection warns with draw indices; rate >=
  E1_NOTPSD_FAIL_RATE (proposed 1e-3) raises with diagnostics attached, enforced with or
  without return_diagnostics. init_values constrained-state injection added for the
  item-8 starts (site-set validation + boundary guard; round-trips at 9e-16). Suite 224
  passed + 1 skipped.

**OPEN (awaiting the author):** the revised item-8 protocol; item 9's numeric pair
(1e-3 post-warmup fail rate; 50-draw early window). PR #7 stays DRAFT; no M2bR layer
runs; M2c blocked.

## D30: start-state preflight + deterministic next-eligible fallback for the pending item-8 validation protocol — 2026-07-11

**Problem:** the forwarded codex message (a recommendation, NOT an author vote — the D28
rule holds) proposed a safeguard for the item-8 multi-chain validation protocol: each frozen
overdispersed chain start should pass a deterministic preflight before pinning, with a
preregistered next-eligible fallback rather than a manual replacement chosen after seeing
failures. The safeguard improves the item-8 proposal regardless of whether rows 8-9 are
eventually ratified, so it was implemented as a capability; item 8 stays PENDING.

**Decision (capability only; no ratification):** implemented via codex gpt-5.6-sol (xhigh),
independently verified.
- `bistar_gp.e1_potential.preflight_start_state(model, likelihood, x, y, init_values, jitter)`
  -> (ok, reason, report): deterministic checks in protocol order, stopping at the first
  failure — exact site set (build_e1_potential/_guard_init_values), constrained/
  unconstrained round-trip within PREFLIGHT_ROUNDTRIP_TOL=1e-10 relative, finite E1
  potential, finite first gradient, no terminal NotPSD at initialization. A degenerate state
  that defeats pyro's initialize_model validation classifies as potential_finite=False, not a
  site-set failure (verified). Catches ONLY ValueError and NotPSDError/RuntimeError at the
  specified points, never bare Exception.
- `select_start_state(..., candidates)` -> (index, values, reports): the deterministic
  next-eligible fallback — runs the preflight down the preregistered priority-ordered
  candidate list, returns the first pass with its index, raises with every per-candidate
  failure reason if all fail (so a cell is reported un-startable, never hand-patched).
- Protocol doc updated: the D30 preflight + fallback bullet added to the two-stage freeze;
  the realized fallback-advance count per cell joins the pre-run start-freeze pins; status
  line reasserts rows 8-9 PENDING the author's own-words vote. Recorded as prereg addendum
  v1.12 (a refinement of a still-unratified proposal; the protocol doc re-pins to sha256
  bdbabb86...03e8, which is a proposal-state fingerprint, not a freeze).

**Verification:** suite 230 passed + 1 skipped; the frozen v1.4/v1.6 battery untouched;
independently confirmed the fallback skips a leading degenerate candidate to a stable index
across reruns and raises when all fail.

**Status:** capability on feat/d19-m2b-e1; PR #7 stays DRAFT; rows 8-9 still awaiting the
author's explicit ratification in their own words; M2c blocked; nothing runs.

## D31: explicit author ratification of decision-table rows 8 and 9 — all nine items ratified; PR #7 to Ready — 2026-07-11

**Problem:** rows 8 (multi-chain validation protocol) and 9 (NotPSD numeric thresholds)
were the last two decision-table items still pending. The D28 rule bars treating a
forwarded codex recommendation as an author vote, so they stayed PROPOSED through v1.11/v1.12
even though the machinery was implemented.

**Decision:** the author ratified both in their own words ("I ratify row 8 and row 9. you
may proceed"). Recorded as prereg addendum v1.13.
- Row 8: the revised M2bR scientific-validation layer is ratified as written (overdispersed
  prior-IS starts, D30 preflight + next-eligible fallback, §6.15 authority-coverage
  criterion, full 6 h V1-V4). The proposal doc is retitled RATIFIED.
- Row 9: the NotPSD mechanism AND thresholds are ratified (fail >= 1e-3 post-warmup with
  diagnostics attached, warn on any post-warmup, warmup separate, zero in first 50
  post-warmup draws, zero-at-reference). The E1_NOTPSD_FAIL_RATE constant and its raise
  message are relabeled from "proposed" to ratified (D31).
- Audit §4 now records every item 1-9 author-ratified.

**Scope of "you may proceed" (deliberately bounded):** the ratification unblocks recording
the votes and flipping PR #7 Draft -> Ready (the codex code-review rounds + the AST
firewall key-inventory audit satisfy the ratified Ready preconditions). It does NOT
authorize the M2b merge or any M2bR run on its own: per the ratified PR structure (D27),
M2b merges as its own step, then M2bR runs as a SEPARATE corrective-impact PR opening with
the two-stage start-freeze. Merge and M2bR execution remain the author's next explicit
calls. No code logic changed (only the "proposed"->ratified relabel); suite green.

**Status:** all nine decision-table items ratified; PR #7 set Ready; M2b merge + M2bR run
await the author; M2c blocked on M2bR; nothing scientific has run.

## D32: M2bR two-stage start freeze — realized validation starts pinned + independently verified (the pre-run gate) — 2026-07-11

**Problem:** The M2bR corrective milestone opens on branch `feat/d19-m2br` (off `origin/main`
bd0b399, the merged M2b PR #7). Its hard ordering gate: the two-stage validation start freeze
is the FIRST substantive action, and NO chain of ANY layer (audit or validation) may launch
until the realized freeze is committed AND independently reproduced byte-for-byte. The
selection RULE was frozen at prereg v1.11-v1.13; the realized pool indices, fallback-advance
counts, and per-state hashes could not be pinned earlier because the prior-IS pools are local
artifacts. This entry records the author-ratified filler/aggregation refinements, the realized
freeze, and its independent verification — the gate itself.

**Decision (author-ratified refinements baked into the freeze):**
- **R-A (filler selection).** 3 authority slots (chains 1-3). B = number of reportable noise
  bands (pooled prior-IS mass >= 5%; bands lo `noise<0.15`, mid `0.15<=noise<=0.30`, hi
  `noise>0.30`). Band-medians fill B slots; the remaining `3-B` slots are fillers from the
  LARGEST-MASS reportable band: B=3 no filler; B=2 the largest-mass band's weighted-q75 draw;
  B=1 the largest-mass band's weighted-q25 AND q75 draws.
- **R-B (replacement-number aggregation; applies at the validation RUN, not the freeze).** 200
  predictives/chain via the frozen D12/D18 extraction rule; the PRIMARY per-cell validated BMS
  posterior = the concatenated 800 predictive-level G rows, equal per-chain contribution, ONE
  final normalization. Per-chain separately-normalized posteriors and the cross-chain SD are
  DIAGNOSTICS only, never the primary estimator.
- Deterministic details 1-5 (lexicographic `(seed,row)` pooling; softmax-weighted band
  quantiles, first cumulative weight `>= q`, noise-ascending with `(seed,row)` tie-break;
  same-band `|Δnoise|` fallback ordering; chain 0 = frozen MAP via `init_values` not
  `init_to_map`, cell-unstartable-if-MAP-fails; `atol=1e-12` pool verification as a STOP
  condition) are applied throughout. Full text in prereg v1.14.

**Realized freeze (prereg v1.14; `experiments/m2br_start_freeze.py`; manifest
`docs/m2br_freeze/start_freeze_v1.14.json`, sha256 `b1abfa3c…2643d891`).** Start states depend
only on config, so V1/V2 share the `informative` set and V3/V4 share `toy_elicited` (2 sets x 4
chains = 8 starts). Reportability from pooled masses: `informative` lo/mid/hi = 0.2768/0.1310/
0.5922 -> B=3, no filler; `toy_elicited` lo/mid/hi = 0.7627/0.1911/0.0463 -> hi<5%, B=2, one
filler = q75(lo). All targets passed D30 preflight (fallback=0 everywhere); both MAP starts
passed; no cell unstartable.

| Cell(s) | Chain(seed) | Role | Realized `(seed,row)` | Semantic sha256 |
|---|---|---|---|---|
| V1,V2 informative | 0(0) | MAP | — | `72a7e891…4a8b215a` |
| V1,V2 informative | 1(1) | median(lo) | (2,39347) | `c9f37584…d0d7fd4ad` |
| V1,V2 informative | 2(2) | median(mid) | (2,152981) | `2db18020…da309cda` |
| V1,V2 informative | 3(3) | median(hi) | (0,166451) | `5cf298a7…1de45649` |
| V3,V4 toy_elicited | 0(0) | MAP | — | `e666fbca…d8bf747b` |
| V3,V4 toy_elicited | 1(1) | median(lo) | (0,43612) | `50209065…812f4978` |
| V3,V4 toy_elicited | 2(2) | median(mid) | (1,1491) | `a806fa8a…e5fcd752` |
| V3,V4 toy_elicited | 3(3) | q75(lo) filler | (0,53543) | `c965203c…085776c48` |

**Independent verification (the gate — PASSED).** Three independent implementations of the
frozen rule agree byte-for-byte on all 8 starts (realized `(seed,row)`, fallback counts, and
semantic sha256, chain 0 included):
1. codex gpt-5.6-sol (xhigh) — the committed freeze script; two runs -> identical manifest hash.
2. Fable — an independent from-scratch recomputation (separate implementation of R-A + details
   1-4 and the hashing convention, not importing the freeze script); also confirmed the
   `atol=1e-12` pool verification (per-seed + pooled vs `stage_a_{config}.json`), the four-site
   topology, and MAP determinism.
3. codex gpt-5.6-sol (xhigh) — a CLEAN-ROOM recomputation, verifiably barred from reading the
   freeze script / manifest / prereg (its script references none of them), writing its own
   result; byte-compared to the committed manifest = all 8 starts identical.

**Alternatives considered / reconciliations recorded in v1.14:** (a) the validation-proposal
doc-hash drifted (v1.12 pinned `bdbabb86…`; retitled RATIFIED at D31 -> current governing
`1045c11c…`) — recorded as a fingerprint update, no criterion change; (b) the audit protocol's
stale "PROPOSED, PENDING" header is SUPERSEDED by D31 without editing the frozen file (its run
list and sha `45999e2f…` stay frozen); (c) the proposal's "7-site constrained draws" is a
Mauna-model carryover — the toy E1 model has EXACTLY 4 sites, and the criteria ("every site")
are unchanged. No ratified value, criterion, budget, run list, or cell design was altered.

**Result:** Commit A `10edc2d` (v1.14 + `experiments/m2br_start_freeze.py` + manifest) and this
Commit B (D32) both exist; the clean-room recomputation matches byte-for-byte. The hard
ordering gate is satisfied. Nothing scientific has run: no HMC/VI/`hmc_laplace`, no Mauna
access, no pool regeneration; the local pools and original invalid caches are untouched.

**Status:** GATE PASSED. The audit layer (`docs/m2br-corrected-impact-protocol.md`: 6
single-chain seed-42 runs, 2 h ceiling, "corrected single-chain comparison" label, cannot close
W2/W3) and the validation layer (`docs/m2br-validation-protocol-PROPOSAL.md`: cells V1,V3,V2,V4
from the frozen starts, 4 chains, 6 h ceiling) MAY now execute per their frozen protocols with
stop-and-report. Outcomes (which withdrawn numbers are superseded vs still withdrawn) will be a
SEPARATE later D-entry. M2c stays blocked; the A7 Della vehicle stays on hold (v1.8).
