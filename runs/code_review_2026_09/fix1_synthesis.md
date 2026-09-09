# Fix pass 1: review-round synthesis (revision 2, 2026-09-08, Fable)

Revision 1 (2026-09-07) covered the Codex channel. Revision 2 adds the
Fable 5.1 channel, records the adjudication of both, and reports fix pass
1b, which folds the accepted items into the same uncommitted worktree.
Scope: `/Users/sc8918/Documents/GitHub/bistar_gp_c-fix` (branch
`fix/code-review-2026-09`, base `71540836`). Questions: (a) is the recent
code correct; (b) should the fix be deleted and re-implemented more
concisely.

## Channels

| Channel | Status | Output |
|---|---|---|
| Codex gpt-6-astra xhigh (full repo; suite, oracle, probes) | landed 2026-09-07 | `fix1_codex_review.md` (REVISE, R1-R10) |
| Fable 5.1 fresh instance (subagent, no shared context; full repo; suite, oracle, probes) | landed 2026-09-08 | `fix1_fable51_review.md` (APPROVE, F1-F7) |
| Fable (implementer's self-check; not an independent channel) | | SC-1 = R8(i) = F1 |
| Kimi K3, GLM 5.3 (package-only) | pending, author-run | brief `docs/paper-sie-jmp/prompts/code-review-fix1-review.txt`; bundle `fix1_bundle/` |

The user chose Fable 5.1 for the fourth slot instead of Opus. Its
independence is one of context, not of model: it saw none of my reasoning
or the other channel's file (it was told not to open them, and its report
says it did not), so its agreement with Codex on R8(i)/F1 and R4/F5 counts
as two-reporter under HANDOFF-cases §4.

## Verification of the two channels

Codex: all ten probes rerun with the fix worktree forced onto the path;
every line reproduced (revision 1). Fable 5.1: every probe asserted the
package path itself; its seven findings were checked by reading the cited
lines and, for F1, by my own earlier probe; each is now pinned by a test
that discriminates the pass-1 code from pass 1b. Both channels reran the
suite (Codex 1327/3/1 with the fixture variable, Fable 1325/5/1 without)
and the Case E oracle (three sha256 identical).

## (a) Findings, adjudicated, with pass 1b disposition

Severity: S1 manuscript number wrong; S2 wrong under a reachable
configuration; S3 latent, guarded; S4 hygiene. Reachability means a paper
path or a documented call pattern; injected exceptions and offsets of 1e12
do not count. Codex graded six items S2 that I grade S3/S4 on that basis;
Fable 5.1 graded everything S3/S4 independently. The fix list is the same
under either reading.

| ID | Channels | Grade (Codex / Fable 5.1 / adjudicated) | Pass 1b disposition |
|---|---|---|---|
| R1 unknown site swallowed to -inf in `compute_log_marginal_likelihoods` | Codex | S2 / - / S3 (all draws share keys, so the all-absent guard raises; `extract_gp_predictives` cannot emit an unknown key) | FIXED: sites applied outside the numeric handler; pin R1 |
| R2 non-atomic `add_draw` under `strict=False` | Codex | S2 / - / S3 (needs an injected failure) | FIXED: every target conditioned into a per-draw record, committed together; pin R2 |
| R3 accumulator key collision (`"a,b"`, `"__full__"`) | Codex | S2 / - / S4 | FIXED: typed tuple keys; pin R3 |
| F3 duplicate names in a group double-count | Fable 5.1 | - / S4 / S4 | FIXED: `group_key` deduplicates (Fable's one-line form); pin in R3 test |
| R4 = F5 `metric_name` optional versus "required" | Codex + Fable 5.1 (two-reporter) | S4 / S4 / S4, author decision | NOT CHANGED. Both channels recommend: accept the optional keyword now, make it required in fix pass 2 together with the two callers outside the editable set (`metrics_v2.py:398`, `mcse_strategy.py:177`). Proposed disposition below. |
| R5 class-label cardinality unchecked | Codex | S2 / - / S4 (no caller passes `class_names`) | FIXED: one label per column, no repeats, plus an `instance_names` length check; pin R5 |
| R6 large common offsets cancel imprecisely in weighted posterior and ESS | Codex | S2 / - / S3 (8e-13 at offset 1e4, 2e-11 at 1e6, visible only at 1e12) | FIXED: one global shift before the log-sum-exps; one ESS routine with per-column max; pins R6 (exact at 1e16) |
| R7 strict evaluation failure inside the optimizer becomes a flagged start-point expansion | Codex | S2 / - / S2 | FIXED: `EvaluationFailure(RuntimeError)` raised by the evaluators and re-raised by both optimizer handlers; genuine optimizer faults keep their fallback; pin R7 |
| R8(i) = F1 = SC-1 start-order dependence under NaN | Codex + Fable 5.1 (two-reporter) | S2 / S3 / S3 | FIXED: `_select_start` picks the minimum over finite objectives, NaN only when all are non-finite; pin R8 |
| R8(ii) NaN evidence reported with `converged=True` | Codex | S2 / - / S3 | FIXED: Hessian finiteness checked before the log-determinant; record kept, `converged` cleared; pin R8 |
| R8(iii) `_weight_ess` returns 0 for NaN and for absent support alike | Codex | S2 / - / S4 | FIXED: `log_weight_ess` returns NaN for NaN, 0 for all -inf; pin |
| R9 target checker accepts a NaN column | Codex | S2 / - / S3 | FIXED: finite validation of the selected row and the stored field before any reduction; pins R9 (each column, both blocks, stored field) |
| R10 covariance pin checks the diagonal only | Codex | S4 / - / S4 | FIXED: full-matrix pin against direct conditioning plus the between-draw covariance; the fixture has off-diagonal between-draw terms |
| F2 `log_mlls` under the default uniform weighting is discarded with a warning (legacy positional calls run a different estimator) | Fable 5.1 | - / S3 / S3 | FIXED: the combination raises; the warning branch is gone; pin in `test_fix1_weighting.py` |
| F4 `soft_transfer` now raises on non-finite G (undisclosed, unpinned, helper-named message) | Fable 5.1 | - / S4 / S4 | FIXED: validated at `soft_transfer` entry with its own message; pin; disclosed here (pre-fix returned a uniform posterior; `compute_G_matrix` never emits non-finite values) |
| F6 two fixture-gated pins skip in the plain suite (1325/5 versus the report's 1327/3) | Fable 5.1 | - / S4 / S4 | DOCUMENTED: both counts stated in the report; the embedded values and inline arithmetic keep the substance exercised without the variable |
| F7 sentinel test does not assert the all-NaN posterior semantics | Fable 5.1 | - / S4 / S4 | FIXED: assertion and `ModelPosteriorResult` docstring |
| Codex firewall suggestion (prove "before any metric call") | Codex | S4 | FIXED: counting-metric pin |
| Codex non-findings: `instance_scores` scale, report's `rng` misattribution, `samples` rationale | Codex | S4 | scores restored to the pre-fix scale (pin); report addendum carries the other two |

No S1 at any point. Verdict on (a): the pass computes what the work order
and the manuscript require; the one S2 (R7) and every S3/S4 above are
closed by pass 1b except R4/F5, which is the author's call.

## (b) A better, more concise, more elegant fix?

Both channels: do not delete and re-implement. Codex: SIMPLIFY IN PLACE for
FIX-1, 2, 3, 5, 6, 8, KEEP for 4, 7, 9. Fable 5.1: KEEP overall, SIMPLIFY
IN PLACE for FIX-2, 5, 6, and two optional micro-simplifications (a
single-draw helper; a metric registry with `__missing__`). Convergence is
complete on the verdict and near-complete on the means:

- Both name the duplicated `ComponentResult` packaging in `debias.py` as
  the accretion. Pass 1b routes the MAP path, the accumulator, the full
  posterior and the groups through one `_summarize` factory (Codex's
  "summary constructor", Fable's `_single_draw` helper), with zero
  numerical change (the MAP path stays bit-identical: sqrt of the same
  floored variances). Fable 5.1 explicitly rejected routing MAP through the
  accumulator because the accumulator symmetrizes and floors at 0; pass 1b
  does not do that.
- Both want the `strict` flag kept explicit rather than moved onto
  `ModelParameterSpace` or a policy object; both want a distinct evaluation
  exception that the optimizer handlers cannot swallow. Done.
- Codex wants one ESS helper shared by the weighted path and
  `boltzmann_weight_ess`; the package had three copies (laplace, bms_star,
  inline). Pass 1b has one, `log_weight_ess`, used by all three.
- Fable 5.1's `_MetricRegistry.__missing__` replaces `_resolve_metric`
  (18 lines) with 8 and covers every `METRICS[name]` site in the package,
  not only `compute_G_matrix`. Adopted.
- Both keep FIX-9's six duplicated pooled lines under the bit-identity
  test rather than couple `soft_transfer` to `aggregate_convention`. Kept.
- Divergence, minor: Codex would reject repeated group members; Fable 5.1
  would deduplicate. Pass 1b deduplicates (shorter, no error surface).
- Fable 5.1 also asks for less provenance prose in docstrings (18 "2026-09"
  and 26 "FIX-n" mentions). Not done in 1b; a trim is safe to do at commit
  time or in pass 2, and Notes/DECISIONS.md is the right home for the
  review history.

Recommendation on the author's question ("delete this fix and implement a
better, more concise, more elegant version?"): no. Keep the pass; pass 1b
is the concise version of it.

## Fix pass 1b (applied 2026-09-08, same worktree, uncommitted)

Files: `bistar_gp/{aggregation_v3,bms_star,debias,external_targets,induced_prior,laplace_evidence}.py`;
`tests/{test_fix1_conventions,test_fix1_sentinels,test_fix1_weighting}.py` edited;
`tests/test_fix1_review_round.py` new (17 tests, R1-R10 + F2-F4 + firewall).
Delta against the reviewed pass-1 state: `fix1_bundle/fix1b_delta.diff`;
cumulative base-to-now: `fix1_bundle/fix1b_cumulative_tracked.diff`,
`fix1_bundle/fix1b_status.txt`.

Verification: full suite in the fix worktree, plain run (no fixture variable): 1342 passed, 5 skipped, 1 failed, 466.06 s (7 min 46 s); the failure is the known `test_m2cr_environment_freeze.py::test_committed_dependency_lock_reproduces_at_head`; the skips are the two fixture-gated pins plus the three pre-existing environmental skips; collected 1348 = 1331 + 17 new. The two fixture-gated files pass with `FIX1_FIXTURE_DIR=<scratch>/fixpass1/fixtures` (run separately). Log: scratchpad `fixpass1/full_suite_1b_worktree.log`. Case E oracle against the synced
worktree package: three sha256 identical (60.3 s). Pass 1b was developed on
a scratch copy while the Fable 5.1 reviewer read the worktree, then copied
back file-for-file (post-sync `diff -rq` empty).

## Author decisions

1. R4/F5: proposed disposition, from both channels: accept `metric_name`
   optional in this commit; fix pass 2 makes it required and migrates
   `bistar_gp/metrics_v2.py:398` and `bistar_gp/mcse_strategy.py:177`.
2. Severity record: Codex's S2 grades versus the adjudicated S3/S4 (table
   above); the fix list is unaffected.
3. Commit shape: one commit (pass 1 + 1b, as the worktree now stands) with
   this synthesis and the two channel reviews cited, or two commits from
   the bundle's two diffs. The reviewed pass-1 state is reconstructible
   from `fix1_bundle/fix1_tracked.diff` + `fix1_new_files.txt`.
4. Kimi K3 and GLM 5.3: still pending; revision 3 when they land.

## Dispositions (2026-09-08, author)

1. R4/F5: `metric_name` accepted optional in this commit; fix pass 2 makes it
   required together with `bistar_gp/metrics_v2.py:398` and
   `bistar_gp/mcse_strategy.py:177`.
2. Severity record: the adjudicated grades in the table stand; each channel's
   own grades remain in its file.
3. Commit shape: two code commits on `fix/code-review-2026-09` (pass 1 exactly
   as reviewed, then pass 1b) followed by this record; D68 in
   `Notes/DECISIONS.md` with Update 1 for pass 1b.
4. Kimi K3 and GLM 5.3 outputs on the fix pass: to be obtained through
   OpenRouter with the package-only brief and folded into revision 3.
