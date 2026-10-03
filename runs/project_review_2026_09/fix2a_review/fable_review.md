<!-- channel fable, Agent subagent (model fable), repository access, read-only; delivered 2026-10-03 -->

# Fable channel review of fix pass 2a (2026-10-03)

**Disclosure.** I was consulted read-only during this pass on one design point: the adaptation of the two D2 tests in `tests/test_bms_aggregation.py` (option A, my variant adopted). I judged that change below by mutant probes like everything else; nothing in this review relies on the implementer's report or on my earlier advice.

## Verdict

**REVISE** (code): the ten queue items and the optional items are implemented to specification and every paper path I replayed is unchanged, but two holes should close before commit: the Case D producer still substitutes a flat-mean candidate silently under `strict=True` (F2), and the A-5 change alters and mislabels the frozen D58 poster driver's card6 render path (F1). Three cheap items (F3, F4, F5) should go in with them.

**Record:** accurate in substance; two inaccuracies: `WITHDRAWN_CACHES` has 15 entries, not 16 (report 2a-7 and D70), and the A-5 consumer list omits `experiments/poster_d58_mauna.py`, which renders card6 through `viz.plot_mauna_loa_decomposition`.

## Findings

| ID | Item | Sev | Status | file:line | Claim | Concrete failure scenario | Suggested change | Pin |
|---|---|---|---|---|---|---|---|---|
| F1 | A-5 (optional) | S3 | CONFIRMED by probe | `bistar_gp/viz.py:132-136, 158-172, 185-187`; consumer `experiments/poster_d58_mauna.py:541-544, 578-591` (frozen) | Report: A-5 consumers are three unrun scripts | Rebuild the committed `runs/poster_d58/fit_full461_seed0/decomposition.npz` exactly as the frozen driver does (positional contract, `ComponentResult(name, mean, std, cov, samples)` so `samples_kind` defaults to `"function_draws"`, `full=None`) and call `plot_mauna_loa_decomposition`: base package gives panel (a) 16 lines, band "95% CI"; 2a gives panel (a) 1 line (traces gone), band "mean ± 2 sd", and panels (b)-(d) label the 15 traces **"function draws"** although they are the per-draw conditional means of the HMC decomposition. PNG sha256 fbd05dcf... becomes 8c1a3d0f...: card6 no longer regenerates from the committed arrays through the frozen driver, and a presented-figure path gains a wrong legend. | In `plot_component`/`_plot_traces`, label traces only when provenance is known (`comp.n_draws > 0`); a rebuilt summary (n_draws 0) keeps unlabeled traces as before. State in the report and D70 that card6 re-rendered by the frozen driver differs from the pinned asset until the 2c D58 correction. | Rebuild a result through the positional contract and assert no `"function draws"` label on a summary with `n_draws == 0`; assert the card6 legend set. |
| F2 | 2a-10 | S2 | CONFIRMED by source read | `experiments/practice_EvansEtAL/run.py:379-392` | Report deviation 6: strict covers every configuration-dropping site | `run_all(curves, out, seed=0, strict=True)`; one subject's `exponential.fit` raises (optimizer overflow on a short curve). The handler appends a flat-mean `CandidateResult` named "exponential" (`mean = ȳ`, `cov = var(y) I`, `parameters={}`), BMS* scores it under the real candidate's name, BIC silently omits it, `strict` is never consulted, and `run_all` passes `verbose=False`, so nothing is printed; the JSON shows only `fitted_params["exponential"] == {}`. The planned A1 regeneration would carry this silently. | Under `strict` raise naming subject and candidate (reuse `_missing`'s pattern); non-strict records the substitution in a `candidate_failures` field and marks the candidate. | Monkeypatch one candidate's `fit` to raise: strict run raises; non-strict JSON records it; `bistar_probs` excludes or flags the candidate. |
| F3 | 2a-8 | S4 | CONFIRMED by probe | `bistar_gp/bms_star.py:761-768`; `run_bms_star` `:855` (no passthrough) | ESS floor "fires below the floor and not above" | `soft_transfer(np.zeros((20, 2)), 1.0, ["a","b"])`: uniform weights, ESS 20 = n_draws, warning fires. Every `run_bms_star` call with fewer than 100 predictives warns per (metric, tau) (270/270 in the smoke run); inside the frozen `mcse_strategy` (B = 1000 replicates per cell) up to 1000 lines per cell whenever pooled ESS < 100 (kl_forward at tau ≤ 1 has ESS 1.1 to 14.5 of 1000 in E7). Numbers unchanged; the signal is uninformative and cannot be tuned from `run_bms_star`. | Make the floor relative (warn when `min_ess < ess_warn` and `min_ess < frac * n_psi`), or warn from `run_bms_star` with an `ess_warn` passthrough. | Uniform 20-draw matrix produces no warning; the concentrated matrix does. |
| F4 | 2a-7 | S4 | CONFIRMED by probe | `bistar_gp/config.py:34-58` | Registry derived from D33/D34 | `load_hmc_samples("runs/prior_sensitivity/samples_toy_elicited_hmc_td7.npz")` (exists locally, pre-D22 sampler; D33 calls its numbers "withdrawn historical HMC numbers", now superseded) loads without refusal, and `prior_sensitivity_study.py` stage B `--method hmc` for toy_elicited reaches it through `run_one_method`. Two registered informative `runs/prior_sensitivity` HMC entries have no local file (harmless). | Register `samples_toy_elicited_hmc_td{7,10}.npz` with a D33 comment; the direct `np.load` readers at pss:579 and :1156 bypass the loader, so nothing else changes. | Add both names to `test_2a7`'s list. |
| F5 | record | S4 | CONFIRMED by probe | `fix2a_report.md` 2a-7 and Deviations; `Notes/DECISIONS.md` D70 | "16 entries" | `len(WITHDRAWN_CACHES)` is 15. The A-5 consumer list omits the frozen poster driver (F1). | Correct both. | n/a |
| F6 | 2a-3 | S4 | CONFIRMED by source read | `bistar_gp/bms_star.py:279-308` vs `bistar_gp/model.py:63-65` | Aliases match `apply_hp_value` | `model.py` states that every consumer must go through `select_hmc_sites`/`apply_hp_value` rather than parsing names; `missing_sample_sites` re-implements the alias table in a second module. A future alias accepted by `apply_hp_value` but not by `canonical` makes strict extraction raise "missing site" on a dictionary the applier accepts. Latent today (probe: toy, single-kernel, Mauna current and legacy names all resolve). | Move `canonical`/`missing_sample_sites` into `model.py` beside the two helpers and derive the alias table once. | Parametrize the legacy-name check over the alias list shared with `test_hmc_sample_sites`. |
| F7 | 2a-1 | S3 | CONFIRMED by source read | `bistar_gp/bms_star.py:646-668` | Partial failures keep the penalty | A draw on which every candidate fails (joint `kl_forward` on a predictive covariance beyond `_safe_logdet`'s fallbacks) gets a uniform row; under `normalize_per_draw=True` its deltas are zero, so it adds 1/n_theta to every candidate, and `hard_win_statistics` counts it as an all-way tie. Latent (no paper path uses that configuration with a failing metric). Report open item 1. | Treat a dead row like a dead column (raise, or drop the draw and record `n_dead_draws`). | Matrix with one all-failed row raises or reports the count. |

## Verified correct

- **Targeted suite on the 2a tree** (`PYTHONPATH` = worktree, package path printed, `-p no:cacheprovider`): 23 package-side files, 283 passed, 2 skipped (the `FIX1_FIXTURE_DIR` gate and the machine-local artefact gate); 8 frozen-area consumer files (`test_poster_d58_driver`, `test_m2br_drivers`, `test_m2br_v116`, `test_m2c_mcse_strategy`, `test_m2c_umbrella`, `test_m2c_profile_integration`, `test_m2c_m1_nugget_floor`, `test_mauna_candidate_registry`, `test_d19_bench_firewall`), 194 passed.
- **Each new pin fails on the pre-2a code**: `git archive 69deeda` into scratch, the `errors` import redirected to `laplace_evidence`, 12 of 12 fail with substantive reasons (DID NOT RAISE for 2a-1, 2a-2, 2a-3, 2a-4, 2a-5, 2a-10; `noise_var` 0.1 vs 0.05; td7 entry missing; no `ess_warn` kwarg; tuple lacks `converged`; "95% CI"; [0.731, 0.269]).
- **Adapted D2 tests are not weakened**: both fail on a `10 * max_finite` mutant and on a `max_finite` mutant of `compute_G_matrix` (two scratch copies of the package), pass on 2a, and the dead-column raise is pinned where the old construction stood.
- **E7 (headline SIR path) regenerated in scratch** against the 2a package with a copied `runs/prior_sensitivity`: 138 numbers and 5 strings identical to the committed `results.json` at `76135be`, no added keys; anchor 0.183 0.192 0.441 0.184; the ESS floor fired six times exactly as the report lists.
- **Case E oracle** (`toy_debias_demo.py` from `a07e61e`, 4 min under load): `results.json`, `debias_figure.png`, `README.md` byte-identical to the committed hashes 65c9ff5f..., c1153549..., 7096cd6e....
- **D58 poster driver's decomposition call passes the new site check**: Mauna model has 7 named priors, the committed `samples.npz` has the same 7 keys, `select_hmc_sites` keeps all 7, `missing_sample_sites` returns `[]` under current and legacy names; `noise_var` change is metadata only.
- `m2br_run_common.py` passes a config likelihood builder, so the probe inventory matches the sampled sites; `mcse_strategy` reaches only `soft_transfer` (log-only change).
- `TauSweepPosteriors`/`LadderPosteriors` survive `copy.deepcopy` and `pickle`; the ladder JSON-serializes as the plain dict; `plot_tau_effect_on_evidence` unpacking unchanged.
- `is_withdrawn_cache` matches by path suffix, so scratch copies are refused identically; `run_one_method` reads through the loader before any `np.load`.
- 2a-3 draw indices unchanged (same generator calls; E7 and oracle identical); `sample_draw_count` handles torch tensors and 0-d arrays; the equal-length error is order-free by sorted keys.
- `errors.py` import graph acyclic; `laplace_evidence` re-export works (`test_fix1_review_round` passes); `EvaluationFailure` is one class object across modules.
- Report counts: 12 new tests; `test_bms_aggregation.py` 11 tests; `run_weighted_bms_star` exists; 2a-9 has no script callers; `compute_induced_prior` has no case-script callers.

## Answers

**Q5 (deviations 1-9):** all acceptable, none to revert. Deviation 8 should also disclose the rebuilt-result behaviour (F1). Deviation 6's wording is accurate (candidate substitution is not a configuration drop) but leaves F2 open.

**Q6 (open items):** fix inside 2a: item 5 (F2, before any Case D run), item 7 (F4, two lines), item 2 (F3, at least so uniform weights never warn), plus F1 and F5. Can wait: item 1 (F7, three lines, author's call), item 3 (overflow, unreachable), item 4 (`score_averaged_gp` NaN softmax; no paper path), item 6 (outside the editable block; needs a scope line), item 8 (sheet B1).

**Q4 (tests):** every pin discriminates the base; plausible wrong implementations I considered (penalty `10 * max_finite`, dead column penalized, failed-point weight 1, first-key draw count, argmin ties, missing records) all fail. Missing pins: `decompose_model_mcmc`'s ragged check (deviation 4), the strict=False warn path of `_require_sample_sites`, 2a-10 strict failures at the MAP-fit, empty-predictive and BMS* stages, the generator-ladder materialization in 2a-4, and the rebuilt-result (positional-contract) render path, which is exactly where F1 appeared.

**Q7:**

| Item | Answer | Why / how |
|---|---|---|
| 2a-1 | KEEP | Clear three-way contract; add the dead-row clause if F7 is accepted. |
| 2a-2 | KEEP | Correct; the second all-non-finite raise is redundant but harmless. |
| 2a-3 | SIMPLIFY IN PLACE | One `_probe_inventory(kernel_builder, likelihood_builder, x, y)` helper for the two duplicated blocks; move alias canonicalization into `model.py` (F6). |
| 2a-4 | KEEP | Three lines, as specified. |
| 2a-5 | KEEP | `_require_restart` is the right seam. |
| 2a-6 | KEEP | Minimal; MAP path untouched. |
| 2a-7 | KEEP | Add the two toy_elicited HMC entries (F4). |
| 2a-8 | SIMPLIFY IN PLACE | Relative floor or warn from `run_bms_star` with passthrough (F3); serialization block fine. |
| 2a-9 | KEEP | Subclasses keep every caller unchanged; a dataclass would force call-site edits. |
| 2a-10 | KEEP, close F2 | Extend `_missing` to the candidate loop. |
| A-5 | SIMPLIFY IN PLACE | Provenance-guarded labels (F1). |
| A-7 | KEEP | `rankdata` average is the package's tie rule. |
| A-15/A-18 | KEEP | Docstrings only. |

## What I ran or read

Read: brief, repo addendum, `HANDOFF-fix-pass-2.md`, `HANDOFF-code-review.md` §2, SYNTHESIS §3, §9, §10, `fix2a_report.md`, D70 draft, D33/D34, the full `git diff 69deeda` (saved to scratch), `errors.py`, `test_fix2a_contracts.py`, and the surrounding sources (`model.py` site helpers and Mauna builder, `bms_star.py` extraction/ESS/tie helpers, `debias.py` both decompositions, `fit.py`, `config.py`, `laplace_evidence.py` ladder, `mcse_strategy.py` loop, `metrics_v2.py`, `aggregation_v3.score_averaged_gp`, `prior_sensitivity_study.py` `_sir_bms` and cache readers, `poster_d58_mauna.py` rebuild and render, `viz.py`, `run.py`). Caller inventories by grep across `bistar_gp/` and `experiments/`.

Ran (all with `PYTHONPATH` to the 2a worktree unless stated, `PYTHONDONTWRITEBYTECODE=1`, `TMPDIR`/`MPLCONFIGDIR`/`XDG_CACHE_HOME` in scratch, package path printed): the two targeted pytest batches above (283 + 194 passed); the new test file against the `69deeda` archive (12 failed as expected); the two adapted D2 tests against two penalty mutants (4 failures); the Mauna inventory, ESS-floor and pickle probe; the before/after card6 render probe on the local D58 `decomposition.npz` (base vs 2a); E7 regeneration with a JSON walker against the committed reference; the Case E oracle with sha256 against `origin/paper/case-e-debias`; `len(WITHDRAWN_CACHES)` and `is_withdrawn_cache` suffix checks. No repository file was created, edited or deleted; only read-only git commands (`status`, `rev-parse`, `diff`, `show`, `ls-tree`, `archive`) were used; no Mauna inference, no network.
