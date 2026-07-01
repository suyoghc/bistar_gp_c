# Scratchpad

Working notes: current plan, open questions, in-progress state. Clean out completed items.

## In progress

- **Z_Mx / Laplace reconciliation** (DECISIONS D3) — PR #1 merged; Construction II confirmed
  canonical. **Core done** on `fix/laplace-zmx`: new canonical API in `laplace_evidence.py` +
  `tests/test_laplace_zmx.py` (40 tests pass). **Next:** migrate the two callers off
  `compute_laplace_evidence` (`bistar_sample_size_sweep.py:234`, `bistar_induced_prior_v2.py:208`),
  unify the viz Laplace scripts, regenerate figures, update README + kb/Wiki definitions.

## Open questions

- Confirm Occam default = no-Occam (README's "faithful BI*"); with-Occam shown as sensitivity.
  (Currently `model_posterior`/`laplace_log_Z_Mx` default `occam=False`.)
- When to regenerate paper figures + run the old-vs-new impact assessment (needs a torch env).

## Branches / PRs

- **`fix/bms-correctness`** (PR #1: https://github.com/suyoghc/bistar_gp_c/pull/1) — repo hygiene +
  5 correctness fixes + Z_Mx plan + Notes scaffold. Not yet merged.

## Follow-ups from the codebase evaluation (not yet scheduled)

- De-dup `build_toy_kernels` (defined twice, model.py:52 and :117) and the `InducedPriorResult`
  name collision (induced_prior.py:155 vs mechanism.py:270).
- RNG seeding for MAP/HMC; cache key that covers all result-determining config.
- Fix `numerical_hessian` boundary regularization (fabricates curvature at boundary MAPs).
- Add `pyproject.toml` to remove the 13 `sys.path` hacks and the `conftest.py` stopgap.
