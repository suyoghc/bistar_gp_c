<!-- channel kimi, model moonshotai/kimi-k3 via openrouter, attempt 1, 2026-10-03 07:50:20, 169s -->

# Fix pass 2a review — Kimi K3

**Verdict: REVISE.** The main contracts are implemented carefully and the paper-path evidence is strong, but five items should be corrected or explicitly dispositioned before commit: near-ties in `robust_rank`, the toy-elicited HMC cache omission, the remaining Case D candidate-fit fallback, false-positive ESS warnings, and all-failed rows. **Record accuracy:** substantially accurate; the A-7 disposition is overstated as complete because SYNTHESIS asked for ties under a tolerance, while the implementation handles only exact ties.

## Findings

| ID | Item | Severity | Status | File:line | Claim | Concrete failure scenario | Suggested change | Pin |
|---|---|---:|---|---|---|---|---|---|
| K3-1 | A-7 | S4 | CONFIRMED by source read | `bistar_gp/aggregation_v3.py:250-270` | `robust_rank` averages only exactly equal ranks. SYNTHESIS A-7 says “average ranks under a tolerance.” | With row values `[0.0, 1e-16]`, swapping candidate columns still swaps the ranks and resulting probabilities, although the values are numerically tied under any reasonable tolerance. | Cluster sorted row values under a stated tolerance, assign each cluster the average rank, then restore column order. | A near-tied two-candidate matrix must return `[0.5, 0.5]` and be permutation symmetric; exact-tie tests remain. |
| K3-2 | 2a-7 / A-24 | S4 | CONFIRMED by source read | `bistar_gp/config.py:31-58`; report “Not done” 7 | The D33/D34-derived registry omits the historical toy-elicited HMC caches named in the report: `runs/prior_sensitivity/samples_toy_elicited_hmc_td{7,10}.npz`. | `load_hmc_samples("runs/prior_sensitivity/samples_toy_elicited_hmc_td7.npz")` is accepted even though D33 classifies toy-elicited historical sampler output as superseded/withdrawn. | Either register both paths with a D33 citation, or record an explicit author-approved exclusion and the reason the D33 classification does not apply. | Both names are refused by the loader and by the experiment route; IS pools and MAP caches remain admitted. |
| K3-3 | 2a-10, Case D producer | S2 | CONFIRMED by report; source path NEEDS-REPO-VERIFICATION | `experiments/practice_EvansEtAL/run.py`, candidate-fit block preceding the diff at approximately line 370 | A raising practice-candidate fit is still replaced by a flat-mean candidate without stopping or recording the substitution. | During the future canonical Case D run, one candidate optimizer raises; the subject still scores a synthetic flat candidate as though it were fitted. A BMS* winner, probability and downstream regret table can therefore be based on an unfitted model. | Before the canonical run, raise `EvaluationFailure` under `strict=True`; under non-strict omit the candidate only with a recorded field, or abort that subject/configuration. Do not score a preset substitute. | Monkeypatch one candidate fit to raise: strict fails naming subject and candidate; non-strict records the failure and no flat candidate enters `candidate_results`. |
| K3-4 | 2a-8 | S4 | CONFIRMED by source read and implementer’s open item | `bistar_gp/bms_star.py:610`, `:765-777` | The absolute default floor `ess_warn=100.0` fires even when fewer than 100 draws are perfectly uniform. | `soft_transfer(np.zeros((4, 2)), 1.0, names)` has ESS 4 for each candidate, the maximum possible concentration-independent value, but logs “weight ESS below 100”. The frozen MCSE path can emit this on every replicate. | Use a floor such as `min(ess_warn, n_psi)` or warn only when ESS is below both an absolute floor and a stated fraction of `n_psi`. Preserve E7/Case C warnings. | Uniform weights with four draws produce no warning; one dominant draw among 1,000 still does. |
| K3-5 | 2a-1 residue | S3 | CONFIRMED by source read and implementer’s open item | `bistar_gp/bms_star.py:630-665` | A row in which every candidate fails keeps the same penalty in every column. Under `normalize_per_draw=True`, subtracting the row minimum turns that failed draw into equal support for every candidate. | Three candidates and four draws: one draw raises for every candidate, the others are finite. `compute_G_matrix(...); soft_transfer(..., normalize_per_draw=True)` silently adds one uniform draw to the pooled evidence. | Treat a row with no finite entry symmetrically with a dead candidate column: raise `EvaluationFailure` naming the draw, or add an explicit permissive mode carrying a row-validity mask. | A metric failing for every candidate on one draw raises; partial row failures retain the warned penalty. |

No S1 finding is confirmed from the supplied material.

## Verified correct

Checks below are source/diff reads unless explicitly marked otherwise.

- **2a-1:** `compute_G_matrix` now rejects an empty table, raises on an all-failed table, raises on a candidate with no finite entry, and preserves a strictly-worse penalty for partial failures. The penalty remains safe for negative-valued metrics. The two adapted D2 tests preserve the original “failure must not win” property and add a stronger comparison against treating the failed cell as ordinary.
- **2a-2:** moving `EvaluationFailure` to `errors.py` avoids the circular import while retaining the `laplace_evidence` re-export. Strict and non-strict induced-prior semantics match the order: failed points carry `-inf`/zero mass and `n_failed_points`; all-failed input raises under both modes; ESS is computed after failed points have zero mass.
- **2a-3:** length validation occurs before subsampling/indexing and produces an order-independent message. The sampled-site inventory accounts for the legacy kernel prefix, bare noise site and single-kernel aliasing. Complete dictionaries retain the previous RNG call order, so the reported E7/Case E bit identity is plausible.
- **2a-4:** materializing `tau_ladder` before validation correctly handles generators; empty, non-finite and non-positive ladders raise before proposal construction.
- **2a-5:** both sinusoid fits now raise when every restart raises, while a successful restart follows the same assignments as before. The E7 fits should therefore remain bit-identical when all restarts succeed.
- **2a-6:** `noise_var` is now the retained-draw mean, `noise_var_draws` is attached outside the seven-field positional contract, and failed HMC draws do not contribute noise values. The MAP path stores its single value. This intentionally changes the scalar stored by a future D58 rerun but does not break its positional contract.
- **2a-7:** `run_one_method` now passes through `load_hmc_samples` before reading, and `_fit_seconds` is popped rather than leaking into sample hyperparameters. The registry groups match the handoff’s explicit informative, Laplace, vague/gamma-relaxed and VI classes, apart from K3-2.
- **2a-8:** old `hard_win_fractions` remains, while `hard_win_credit`, `attainment`, `tie_fraction` and per-tau `weight_ess` are added. E7 should gain no keys if it consumes only posteriors and G matrices. Console wins are tie-split.
- **2a-9:** tuple/dict subclasses preserve unpacking, indexing and equality while carrying convergence records. `__getnewargs__` addresses pickle/deepcopy for the tuple subclass. `compute_cholesky` has no signature or return change.
- **2a-10:** the seed reaches both NUTS and predictive subsampling; strict mode covers MAP fit, HMC/extraction, empty predictives and BMS* scoring; JSON records counts, diagnostics, seed and strict status; samples go to a sibling `.npz`.
- **Frozen modules:** the diff does not edit M2bR/M2c files, `mcse_strategy.py`, or `poster_d58_mauna.py`.
- **Serialization regression risk:** E7/headline numeric paths are not altered by the added dictionary fields; the reported exact regeneration is consistent with the source changes. I could not execute it.

## Answers to questions 5 and 6

### Deviations

| Deviation | Decision |
|---|---|
| 1. Adapt `test_bms_aggregation.py` | **Accept.** Author-approved, necessary to resolve the direct conflict with A-1, and not weakened. |
| 2. Empty-table raise and repeated-name counts | **Accept.** Natural hardening inside 2a-1. |
| 3. `n_penalized_evaluations` | **Accept.** Records partial substitutions rather than merely logging them. |
| 4. `decompose_model_mcmc` length check; unconditional marginal-likelihood site raise | **Accept.** Same defect class; the latter function has no strict mode and already raises for unknown sites. |
| 5. `--allow-withdrawn` | **Accept.** Mirrors the loader and is needed for labelled archival reproduction. |
| 6. Strict coverage of every configuration-dropping site and seeded subsampling | **Accept.** Both are required for a reproducible, fail-loud producer. |
| 7. Exact ties rather than tolerance ties | **Revise.** See K3-1; SYNTHESIS explicitly says “under a tolerance.” |
| 8. A-5 MAP traces become fixed-seed joint draws; rebuild without `full` gets no traces | **Accept.** It removes the incorrect sum of independently drawn components. Run the three consumer scripts as smoke tests before release. |
| 9. Copy rather than symlink regeneration inputs | **Accept.** Safer for the read-only main worktree; hashes were checked. |

### Open items

**Fix inside 2a before commit:**

1. Dead rows under `normalize_per_draw=True` (K3-5): small, directly adjacent to 2a-1, and prevents a new permissive path from being codified.
2. ESS-floor false positives (K3-4): small and otherwise floods ordinary calls and the frozen MCSE path.
3. Practice candidate-fit fallback (K3-3): must not survive into the canonical Case D producer.
4. Toy-elicited HMC registry gap (K3-2): either add the two names or record an explicit exclusion.
5. A-7 tolerance ties (K3-1): complete the adopted disposition.

**Can wait:**

- The theoretical penalty overflow near the float maximum.
- `score_averaged_gp` NaN validation, provided it is tracked as an A-23/A-1 adjacent hardening item.
- Direct `np.load` reads in `prior_sensitivity_study` outside the serialization block, because that file is deliberately restricted in 2a; handle in 2b or by author exception.
- The enlarged lock drift, pending the author’s B1 environment decision.

## Question 7: keep, simplify, or rewrite

| Item | Decision | Reason |
|---|---|---|
| 2a-1 | **SIMPLIFY IN PLACE** | Add the dead-row rule/mask; otherwise concise and well pinned. |
| 2a-2 | **KEEP** | Strict/permissive semantics and records match the contract. |
| 2a-3 | **KEEP** | Shared validation and alias handling address the defect without changing successful paths. |
| 2a-4 | **KEEP** | Minimal and correct. |
| 2a-5 | **KEEP** | Directly removes the silent preset candidate. |
| 2a-6 | **KEEP** | Summary is order-invariant and positional compatibility is retained. |
| 2a-7 | **SIMPLIFY IN PLACE** | Resolve the toy-elicited HMC omission/exclusion. |
| 2a-8 | **SIMPLIFY IN PLACE** | Scale or qualify the ESS floor; serialization itself is right. |
| 2a-9 | **KEEP** | Compatibility-preserving record carriers are appropriate. |
| 2a-10 | **SIMPLIFY IN PLACE** | Remove/record the candidate-fit fallback before Case D is regenerated. |
| A-5 | **KEEP** | Correct conceptual repair; add consumer smoke coverage. |
| A-7 | **SIMPLIFY IN PLACE** | Extend exact ties to documented tolerance clusters. |
| A-15 | **KEEP** | Docstring accurately exposes the internal scale. |
| A-18 | **KEEP** | The in-place behavior is now explicit. |

No item warrants a full rewrite.

## Test adequacy

The new tests generally discriminate the pre-2a code: they use always-failing metrics/predictors, missing and ragged site dictionaries, invalid ladders, all-failed restarts, draw permutations, guarded cache fixtures, tied candidates, forced optimizer failure and a raising sampler. The two adapted D2 tests are **not weakened**; the always-failing candidate now pins the stricter adjudicated behavior, while the negative-metric penalty property remains tested on a partial failure.

Missing or desirable pins:

- Near-tied ranks under the stated tolerance.
- A dead row under `normalize_per_draw=True`.
- Uniform small-draw ESS should not warn.
- Toy-elicited HMC cache refusal, or its explicit exemption.
- Practice candidate-fit failure must not become a flat candidate.
- `strict=False` missing-site extraction warning behavior.
- `allow_withdrawn=True` warns but loads.
- Smoke execution of `toy_example.py`, `mauna_loa.py` and `toy_example_noMCMC.py` against the revised `viz.py`.

## What I ran or read

No repository execution was available on this channel. I read the work order, SYNTHESIS A-n dispositions, Codex C01-C11, Opus C4-C14, the implementer’s report, the D70 draft, the complete supplied diff and both new files. All execution claims—including suite counts, Case A-E regeneration identity, oracle hashes, smoke-run reproducibility and the attribution of the six suite failures—are therefore **NEEDS-REPO-VERIFICATION** from this channel. The minimum verification is the handoff’s full suite plus Case E hash check, followed by regeneration of Cases A-D with `bistar_gp.__file__` printed and comparison against the committed references.