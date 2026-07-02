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
per README); add `tests/` + a root `conftest.py`. Tracked files 740 → 458, repo 72 MB → 11 MB.
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
**Result:** 33 tests pass. Verified live: HMC latents 7 → 4; the soft_transfer distortion was
demonstrated numerically ([0.501, 0.289, 0.210] correct vs [0.476, 0.302, 0.222] as-implemented).

---

## D3: Z_Mx / Laplace model-prior definition and posterior assembly (OPEN — plan committed c5562a3) — 2026-07-01

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
(`mechanism.py` → `CandidateInducedSamples`), optional RNG `seed=` on `fit_mcmc_simple`/`fit_hmc`.
`tests/test_laplace_zmx.py` **42 tests pass** (adds default-metric-registration and
II-decomposition-identity). README Occam section updated to the canonical API + ablation ladder.
**Still OPEN (held deliberately — needs a decision or compute):** (1) unify the two self-contained viz
Laplace scripts (`model_priors_laplace.py`, `model_prior_trajectory_laplace.py`) onto
`laplace_log_Z_Mx` — blocked on the single-`G` choice (they use a variance-weighted MSE, not a package
METRIC; this is the paper's metric-choice decision); (2) regenerate all figures + old-vs-new impact
assessment (needs a torch runtime); (3) update `kb/Wiki/GP-Induced Model Priors.md` (gitignored).

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
**Consequence:** every committed HMC archive (`bistar_gp/cache/*.npz`,
`runs/mauna_loa_sub150_hmc_*`) predates the D2 fix (biased target, duplicate sites) — regenerate
before quoting paper numbers; the Della impact assessment must rerun on the fixed code.
