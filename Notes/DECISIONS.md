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
**Status:** OPEN. Gate before implementation: user confirmation of Construction II as canonical.
Implement on a fresh `fix/laplace-zmx` branch after PR #1 lands.
