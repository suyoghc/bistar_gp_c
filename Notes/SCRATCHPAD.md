# Scratchpad

Working notes: current plan, open questions, in-progress state. Clean out completed items.

## In progress

- **Z_Mx / Laplace reconciliation** — plan written (`docs/plan-zmx-laplace.md`), logged as
  DECISIONS D3. Awaiting confirmation of **Construction II** as canonical, then implement on a
  fresh `fix/laplace-zmx` branch after PR #1 lands.

## Open questions

- Confirm Construction II as the canonical posterior assembly (baseline / I as ablations).
- Confirm Occam default = no-Occam (README's "faithful BI*"); with-Occam shown as sensitivity.
- Should the process docs (this plan + `Notes/`) stay on the `fix/bms-correctness` PR, or move to a
  separate branch so PR #1 is purely code?

## Branches / PRs

- **`fix/bms-correctness`** (PR #1: https://github.com/suyoghc/bistar_gp_c/pull/1) — repo hygiene +
  5 correctness fixes + Z_Mx plan + Notes scaffold. Not yet merged.

## Follow-ups from the codebase evaluation (not yet scheduled)

- De-dup `build_toy_kernels` (defined twice, model.py:52 and :117) and the `InducedPriorResult`
  name collision (induced_prior.py:155 vs mechanism.py:270).
- RNG seeding for MAP/HMC; cache key that covers all result-determining config.
- Fix `numerical_hessian` boundary regularization (fabricates curvature at boundary MAPs).
- Add `pyproject.toml` to remove the 13 `sys.path` hacks and the `conftest.py` stopgap.
