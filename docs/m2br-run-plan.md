# M2bR run plan — audit + validation layers (drivers implemented; NOT yet run)

Status: pre-launch. The two-stage start freeze gate PASSED (D32; prereg v1.14/v1.15;
Commits A `10edc2d` + B `72949c0`). The audit and validation drivers are implemented,
hermetically tested, and independently codex-reviewed. **No HMC chain has run.** Real sampling
is gated behind an explicit `--execute` flag; the callable driver APIs additionally require
`authorized=True`. This document + the machine-readable `docs/m2br_freeze/run_plan.json` are the
committed provenance. Heavy samples and the local prior-IS pools stay untracked.

Provenance pin: freeze manifest `docs/m2br_freeze/start_freeze_v1.14.json`
sha256 `b1abfa3c244a03f3ce3b5a69782157aad087e01de8b15a9a332de6ab2643d891`
(the validation driver refuses to load any other manifest bytes). arviz 0.23.4, torch 2.10.0,
gpytorch 1.15.1, pyro 1.9.1, numpy 1.26.4.

## Drivers

- `experiments/m2br_run_common.py` — shared infra: model/candidate/scoring context, schema-v3
  diagnostics payload, `Deadline` (monotonic clock, 10-min reserve, per-run projection gate,
  process isolation with strictly-absolute cutoff + grace-kill), `transactional_persist`
  (samples cache committed strictly last so no orphan consumable cache can appear),
  `require_absent` (no-overwrite), `persist_failure` (failure records with attached diagnostics).
- `experiments/m2br_audit_run.py` — 6 single-chain seed-42 runs (frozen §2 list), `init_to_map`
  after `fit_map(300, lr 0.05)`, 2 h ceiling. Runs the §3 unchanged-arm re-verification first
  (deterministic, no sampler). Every output labelled "corrected single-chain comparison";
  cannot close W2/W3.
- `experiments/m2br_validation_run.py` — cells V1, V3, V2, V4 (priority order), 4 chains each
  from the FROZEN manifest starts injected via `fit_hmc_e1(init_values=..., init_to_map=False)`
  (never recomputes MAP/authority starts; each start semantic-sha256-verified before injection),
  arviz acceptance criteria + authority coverage, R-B pooled-800 primary estimator, 6 h ceiling.
- `tests/test_m2br_drivers.py` — 21 hermetic tests (mock sampler), incl. the R-B proof that
  pooling 800 rows differs from averaging four normalized posteriors and that the driver uses the
  pooled formula.

## Audit layer — frozen run list (2 h ceiling, 600 s reserve)

| # | run_id | config | td | seed | projection |
|---|---|---|---|---|---|
| 1 | d12_informative_td7 | informative | 7 | 42 | 865 s |
| 2 | d12_informative_td10 | informative | 10 | 42 | 1362 s |
| 3 | d18_toy_elicited_td7 | toy_elicited | 7 | 42 | 865 s |
| 4 | d18_toy_elicited_td10 | toy_elicited | 10 | 42 | 1362 s |
| 5 | d18_vague_td7 | vague | 7 | 42 | 865 s |
| 6 | d18_gamma_relaxed_td7 | gamma_relaxed | 7 | 42 | 865 s |

Outputs → `runs/m2br_corrected_impact/` (untracked): `samples_<run_id>_e1.npz`,
`diagnostics_<run_id>.json`, `results_<run_id>.json`, plus `unchanged_arms_verification.json`.
Projected sampling+scoring ≈ 103 min; within the 2 h ceiling.

## Validation layer — cells (6 h ceiling, 600 s reserve; priority V1, V3, V2, V4)

| cell | config | td | chains (seeds) | frozen start sha256 (chain 0..3, truncated) |
|---|---|---|---|---|
| V1 | informative | 7 | 0/1/2/3 | 72a7e891 / c9f37584 / 2db18020 / 5cf298a7 |
| V3 | toy_elicited | 7 | 0/1/2/3 | e666fbca / 50209065 / a806fa8a / c965203c |
| V2 | informative | 10 | 0/1/2/3 | 72a7e891 / c9f37584 / 2db18020 / 5cf298a7 |
| V4 | toy_elicited | 10 | 0/1/2/3 | e666fbca / 50209065 / a806fa8a / c965203c |

(V2 reuses V1's starts; V4 reuses V3's — starts depend only on config.) Per-chain projection
865 s (td7) / 1362 s (td10). Outputs → `runs/m2br_validation/<cell>/` (untracked): per-chain
`chain<k>_{samples,predictives,diagnostics,results}.*` + `cell_results.json`. A cell passing ALL
acceptance criteria yields R-B replacement numbers that MAY supersede the withdrawn historical
numbers; a failing cell leaves its historical counterparts WITHDRAWN/UNVALIDATED.

## Exact launch commands (run only when authorized)

```bash
# from repo root, branch feat/d19-m2br

# 0. (optional) re-emit the machine-readable plan without running anything
python experiments/m2br_audit_run.py --emit-plan

# 0b. (optional) deterministic §3 unchanged-arm re-verification only (no sampler)
python experiments/m2br_audit_run.py --verify-arms

# 1. AUDIT layer — 6 single-chain runs, ~2 h ceiling, stop-and-report
python experiments/m2br_audit_run.py --execute

# 2. VALIDATION layer — cells V1,V3,V2,V4, 4 chains each, ~6 h ceiling, stop-and-report
python experiments/m2br_validation_run.py --execute
```

`--dry-run` swaps in a deterministic mock sampler (no real HMC) and writes to a `_dryrun/`
subdirectory — for plumbing checks only, never a scientific result. Without `--execute` (or
`--dry-run`) the drivers print the plan and exit.

## Projected schedule

- Audit: ~103 min sampling+scoring, ceiling 120 min. Stop-and-report; the first
  unexecuted/timed-out run is recorded.
- Validation: ~312 min projected, ceiling 360 min. Priority order V1, V3, V2, V4 so the td7
  cells of both pivotal configurations survive a truncated session.
- The author authorizes both layers together in a fresh session (they are up to ~8 h combined,
  local HMC). Escalation (more/longer chains) is a new prereg addendum, never an in-run extension.

## After the runs

A separate outcomes D-entry will record which withdrawn numbers are superseded (cells that passed
ALL acceptance criteria) versus still withdrawn, followed by a proposed (pending author
ratification) W2/W3 writeup update. M2c stays blocked; the A7 Della vehicle stays on hold (v1.8).
