<!-- channel glm, model z-ai/glm-5.3 via openrouter, attempt 1, 2026-10-03 07:49:22, 111s -->

# Review: fix pass 2a (package-only channel, GLM 5.3)

**Verdict: APPROVE** for the code, with two record corrections required (the withdrawn-cache entry count and the unpinned pickle claim) and one recommended in-place change (ESS floor scaling) that can be committed with 2a or immediately after. The report and D70 draft are accurate in substance; the two overstatements are listed below.

## Findings

| ID | Item | Sev | Status | Location | Claim / scenario | Suggested change | Pin |
|---|---|---|---|---|---|---|---|
| G1 | 2a-7 / record | S4 | CONFIRMED by source read | `bistar_gp/config.py` WITHDRAWN_CACHES | The diff's tuple has **15** entries (14 added + `runs/toy_tau_metric_comparison/`), but the report ("16 entries") and D70 ("16 entries") both say 16. One of the two is wrong: either the diff shown truncates an entry (e.g. an `samples_hmc_td10.npz` or an informative `hmc_laplace` prior-sensitivity cache) or the record overcounts. | Run `python -c "from bistar_gp.config import WITHDRAWN_CACHES; print(len(WITHDRAWN_CACHES))"`; correct whichever side is wrong. If a D33/D34 cache is genuinely missing, add it. | `assert len(WITHDRAWN_CACHES) == <n>` in `test_2a7` (a count pin is cheap and would have caught this). |
| G2 | 2a-8 | S3 | CONFIRMED by source read (behaviour), fire counts NEEDS-REPO-VERIFICATION | `bms_star.py` `soft_transfer(..., ess_warn=100.0)` | The absolute floor fires on *every* call with fewer than 100 draws — including uniform weights (ESS = n_draws) — and per-replicate inside the frozen `mcse_strategy` loop (report's own smoke run: 270/270 calls). Log-only, no number changes, but the warning spam on frozen-module paths destroys the diagnostic's signal: a genuine concentration in E7 (6 fires) is buried by hundreds of vacuous ones in other workflows. | Scale the floor: `floor = min(ess_warn, n_psi)` inside `soft_transfer`, or emit once per `run_bms_star` call. One line; the report already records the two options. | Extend `test_2a8`: `soft_transfer(np.zeros((4,2)), ..., ess_warn=100.0)` (default) must *not* warn. |
| G3 | 2a-9 / record | S4 | PLAUSIBLE (needs run) | `laplace_evidence.py` `LadderPosteriors` | The report claims both subclasses "survive copy.deepcopy and pickle"; no test pins it. `LadderPosteriors` has a custom `__init__` and no `__getnewargs__`/`__reduce__`; default pickling of a dict subclass should reconstruct via `__new__` + state, but this is exactly the kind of claim that silently breaks on a protocol bump. | Add two lines to `test_2a9`: `pickle.loads(pickle.dumps(ladder)) == ladder` and `copy.deepcopy(sweep).converged is not None`. | Same two lines. |
| G4 | 2a-10 | S3 | NEEDS-REPO-VERIFICATION | `run.py` `fit_hmc(..., return_diagnostics=True)` | The work order guarantees `seed=` exists on the sampler but says nothing about `return_diagnostics`. The two-subject smoke run evidently succeeded, so the kwarg exists — but confirm the signature, since a `TypeError` here would be masked as an "HMC fit" failure under the new strict wrapper. | `inspect.signature(fit_hmc)` once; note the provenance in the report. | `test_2a10` already covers it via the stub; a signature assertion would make it explicit. |
| G5 | 2a-7 side effect | S3 | NEEDS-REPO-VERIFICATION | `prior_sensitivity_study.run_method_fingerprinted` | Stage B of the study now *refuses* the withdrawn caches it previously read, because `run_one_method` defaults to `allow_withdrawn=False` and the study was not edited (editable-set limit). Disclosed as intended. If any committed study workflow re-reads `samples_*_vi_td7.npz` etc. as part of a paper number, that stage now raises. | Grep which prior-sensitivity stages call `run_one_method` with cache paths; if one is on a paper path, route it with an explicit decision rather than the implicit default. | — |
| G6 | A-5 | S4 | CONFIRMED by source read (latent) | `viz.py` `plot_full_prediction` | The MAP branch is selected by `full.n_draws == 1`. A draw-based decomposition that retained exactly one draw also takes it, drawing "function draws" from `N(mean, cov)` where `cov` is the single draw's within-draw covariance — the label is then correct in spirit but the hyperparameter spread is absent either way, so no wrong answer; noted for the record only. | Optionally branch on `samples_kind` instead of `n_draws`. | — |
| G7 | 2a-3 | S4 | CONFIRMED by source read (latent) | `bms_star.py` `sample_draw_count` | Only `relevant_keys` (post-`select_hmc_sites`) are length-checked; a ragged *non-site* key is neither checked nor indexed, so it cannot produce a wrong answer — but a caller passing a dict whose site keys are aliases the selector drops would fall back to `list(mcmc_samples)` and raise on the ragged alias. No failure scenario found; question only. | None needed. | — |

No S1 or S2 findings. I looked specifically for: order-dependence introduced by the moved index selection (none — same RNG calls, and the Case E oracle and Cases A–D regenerations confirm bit-identity); circular imports from the new `errors.py` (none — `errors` imports nothing, `debias→bms_star` is one-directional); signature breaks for the frozen M2bR/M2c modules (only trailing defaulted keywords and log-only changes on their paths); and the `--allow-withdrawn` flag becoming a silent substitute (it warns through the loader, and is CLI-only).

## Verified correct

- **2a-1**: all-failed raise, dead-column raise naming candidates, partial penalty `max_finite + 10(|max_finite|+1)` preserved with a counted warning, repeated names kept separate. Matches the A-1 disposition exactly; the penalty formula is unchanged so no paper-path number moves.
- **2a-2**: strict/non-strict split, `n_failed_points`, zero-weight failed points, ESS over valid points only (failed weights are exactly 0, so they drop out of `1/Σw²`), all-points-failed raises under both settings, `EvaluationFailure` moved to `errors.py` with the `laplace_evidence` re-export intact (the import direction argument in the work order is honored). The `log_weights + log(total)` shift is safe because the preceding raise guarantees a finite weight exists.
- **2a-3**: `sample_draw_count` checks before any indexing with a key-sorted (order-invariant) message; `missing_sample_sites` canonicalizes under the same aliases `select_hmc_sites`/`apply_hp_value` accept, including the single-kernel `covar_module` case and the bare noise site; the Mauna frozen period (no prior) is correctly never required. Probe model construction draws no random numbers, so the RNG consumption sequence is unchanged.
- **2a-4**: tuple-materialization before validation means a generator ladder is not consumed by the check; empty/non-finite/non-positive all rejected; the constant-integrand identity is pinned.
- **2a-5**: both sinusoid classes raise `EvaluationFailure` with restart count and last error; the success path executes the identical assignment statements.
- **2a-6**: `noise_var` is the retained-draw mean on both draw routes, `noise_var_draws` attached as a non-field attribute (the seven-field positional contract survives), MAP path unchanged. Permutation test checks summaries, not just the scalar.
- **2a-8**: warning fires below the floor and not above (test covers both directions); `hard_win_fractions` kept byte-comparable, new keys additive; the frozen M2bR drivers untouched. E7 verified unchanged by the regeneration.
- **2a-9**: `TauSweepPosteriors` unpacks as before; `LadderPosteriors` compares equal to the plain dict; `compute_cholesky` signature and return unchanged (Case E oracle byte-identity is the strongest possible pin here).
- **2a-10**: strict covers every configuration-dropping site including `run_all`'s per-subject handler; seed threads to `fit_hmc` and the predictive subsample (without the latter a seeded run would not reproduce — the smoke run's exact reproduction supports this); the old JSONs stay readable (`regret_curves_mopen.py` replay identical).
- **Tests**: each pin discriminates the pre-2a code (the reported per-test pre-2a failures are the right mutants: DID-NOT-RAISE, 0.1-vs-0.05, missing registry entry, absent attribute, old label, old tie split). The two adapted D2 tests are **not weakened**: the negative-metric penalty property is retained on the partial-failure configuration where the penalty still applies, the dead column now pins the raise, and the added "failure costs mass" comparison fails against a `max_finite`-only penalty. This is the correct resolution of the A-1/D2 conflict; the consultation and author exception are properly recorded.
- **Style**: provenance lines are one per function, no arrow glyphs in the new prose, no role-noun constructions spotted; the editable set is respected apart from the approved `test_bms_aggregation.py` exception.

## Answers

**5. Deviations 1–9**: all acceptable; none should be reverted. Deviation 6 (widening 2a-10's strict contract) and 9 (copies over symlinks) are improvements, not scope creep — each dropped configuration site was a silent-loss path of exactly the class the pass exists to close, and the copies remove the only way the pass could have written into the read-only main worktree. Deviation 4's unconditional raise in `compute_log_marginal_likelihoods` is consistent with that function's existing unconditional raise on unknown sites.

**6. Open items**: fix **item 2 (ESS floor)** in 2a before commit (G2 — one line, and the spam reaches into frozen code's log output). Item 1 (dead row) and item 3 (overflow) can wait for a recorded follow-up — item 1 is outside 2a-1's wording and the SYNTHESIS disposition does not ask for it. Items 4, 5, 6 are outside the editable set and must wait (item 6 is blocked by the serialization-block-only restriction on `prior_sensitivity_study.py`; do not widen the exception). Item 7 (toy_elicited HMC) is an author decision under D33's SUPERSEDED classification; wait. Item 8 (lock drift) is sheet B1, the author's.

**7. Per item**:

| Item | Verdict | Note |
|---|---|---|
| 2a-1 | KEEP | Direct, minimal diff, right exception types |
| 2a-2 | KEEP | Dual raise paths are redundant but harmless |
| 2a-3 | KEEP | Alias table is the unavoidable complexity; probe model is cheap |
| 2a-4 | KEEP | Three lines |
| 2a-5 | KEEP | `_require_restart` helper is the right factoring |
| 2a-6 | KEEP | |
| 2a-7 | KEEP | Verify entry count (G1) |
| 2a-8 | SIMPLIFY IN PLACE | Scale the floor to the draw count (G2) |
| 2a-9 | KEEP | Subclass approach preserves both callers without edits |
| 2a-10 | KEEP | The `_missing` closure is concise; verify `return_diagnostics` (G4) |
| A-5 | KEEP | Joint draws on the MAP path are what C05 asked for |
| A-7 | KEEP | Exact ties match the package's existing tie rule |

**8. Record accuracy**: two overstatements — the "16 entries" count (G1, confirmed against the diff: 15) and the unpinned deepcopy/pickle claim (G3). Everything else I could check against the diff holds: the file list, the signature changes, the caller inventory, the test descriptions, the deviation rationales, and the D70 text are consistent with the code shown. The suite counts, oracle hashes, and regeneration comparisons are internally coherent but NEEDS-REPO-VERIFICATION by execution (as the handoff's verification protocol already requires for the release run).

## What I read

Package-only channel: the work order (section A), the SYNTHESIS A-n table and section 10, the Codex C01–C11 and Opus C4–C14 specifications, the implementer's report and D70 draft, and the complete diff including both new files. All findings above are from source reading of the diff; the execution-dependent claims (suite counts, hashes, regenerations, smoke-run reproducibility, pickle survival) are marked NEEDS-REPO-VERIFICATION with the command to run.