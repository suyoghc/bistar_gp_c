# HANDOFF — implementation-correctness review of the manuscript's compute

Written 2026-09-05 by the driver session. Companion to `HANDOFF-cases.md`,
which governs the *prose* review of the paper sections. This document governs
a different question: **does the code actually compute what the manuscript
says it computes.**

Two independent reviewers receive identical packages: **Fable** and **Codex** (model chosen by the author
at run time, and recorded by the reviewer in its own report). Neither sees the other's findings until both have
reported.

---

## 0. Repository state as of 2026-09-05

Nothing has been merged or committed since 2026-08-13. The scan below is the
factual baseline every reviewer starts from.

| Item | State |
|---|---|
| `main` | `7154083` (2026-07-26, merge of PR #35). Untouched by the paper work. |
| `origin/main` | identical to `main`. |
| Open PRs | six: #36 case-B `32c0a58`, #37 case-C `0adde90`, #38 case-D `ff4c353`, #39 case-A `76135be` (all four READY), #40 synthesis `096dd01` (draft), #41 case-E `a07e61e` (draft). |
| Checked-out branch | `paper/case-e-debias` at `a07e61e`. |
| `Notes/DECISIONS.md` | worktree carries 66 entries ending at **D67**. D59 is absent by design (preserved in stash `stash@{0}`, blob `025cd1a5`; never restore it as part of this review). Committed branch tails carry only each branch's own entry, by plumbing-staging. |
| Uncommitted tracked files | `Notes/DECISIONS.md` (+597 lines over HEAD), `Notes/SCRATCHPAD.md` (+18). Both are author working state. |
| Package | 34 modules, 13,001 lines under `bistar_gp/`. |
| Tests | 67 files, 1252 collected. Driver baseline 2026-09-05: **1249 passed, 1 failed, 2 skipped** in 539.8 s. |
| Known failure | `tests/test_m2cr_environment_freeze.py::test_committed_dependency_lock_reproduces_at_head`. Diagnosed by the driver as environment drift, not a code defect: the committed lock `docs/m2c_freeze/m2cr_dependency_lock_v1.json` holds 324 filtered `pip_freeze` entries, the current environment holds 325, and the sole difference is an added `pypdf==6.14.2` (nothing removed, no version changes). `pypdf` was installed during a 2026-08-13 session to read a thesis PDF. The freeze test is behaving correctly by catching the drift. Resolution belongs to the author, since the lock is committed M2CR evidence: uninstall the package, or update the lock under its own authorization. Reviewers should confirm this diagnosis rather than re-derive it, and must not modify the lock. |
| Environment | python 3.13.11, torch 2.10.0, numpy 1.26.4, gpytorch 1.15.1, pyro 1.9.1, arviz 0.23.4. |
| Codex availability | the usage lock expired **2026-08-18**. The Codex channel is available again; the author selects the model for this round. |

### Why this review exists now

Two open PRs carry an author-ledger item that reads, in both cases,
"Substitute-implementer and driver-verification deviations (Codex locked to
2026-08-18): ratify, or commission a Codex re-review after the lock lifts."
The lock has lifted. A Codex pass over the implementation discharges that item
for #40 and #41, and the Fable pass supplies the second independent channel.

Separately, four case sections have been signed off and marked READY on the
strength of numbers this code produced. No reviewer has yet audited the
*implementation* end to end against the manuscript's claims; every review so
far scrutinized sections, artifacts, and diffs.

---

## 1. Scope

**In scope.** The code that produces any number, figure, or artifact the
manuscript relies on:

- `bistar_gp/` (the package; all 34 modules, with weight on the modules named
  in §3).
- `experiments/` scripts that regenerate committed `runs/` artifacts cited by
  the paper sections, including the five written for this manuscript:
  `occam_dial_figure.py`, `e6_nesting_monotonicity.py`,
  `haaf_nested_constraint.py`, `regret_curves_mopen.py`, `vanbork_figure.py`,
  and Case E's `toy_debias_demo.py`.
- `tests/` — specifically, whether the suite pins the *claims* or merely pins
  the implementation against itself.
- Agreement between committed `runs/*/results.json` values and the section
  prose that quotes them.

**Out of scope.** Do not spend effort on:

- Paper prose, style, framing, or citations. Five §4 rounds have covered that.
- The Mauna Loa preregistration boundary (D58). Read Mauna code where it
  shares machinery with paper-facing paths, but propose no Mauna experiment,
  and treat `runs/d19_*`, `runs/m2c*`, `runs/m2br*` evidence trees as frozen
  historical records.
- Anything requiring new compute beyond running the existing test suite and
  rerunning the named regeneration scripts.
- `Notes/DECISIONS.md` entry bodies. Committed D-entries are immutable
  historical records under the author-record policy; factual corrections
  become dated addenda, never edits. Flag a defect, do not rewrite the log.
- Reformatting, renaming, dependency upgrades, or refactors for their own
  sake.

**No mutations.** Reviewers write exactly one file each (§4) and perform zero
git operations. Read-only git commands are expected and necessary.

---

## 2. The standard: what "implemented correctly" means here

A finding is anything where one of these fails.

1. **Claim fidelity.** A quantity the paper names is computed by code that
   computes something else. The known instance of this class, already
   confirmed and still open on #40's ledger, is the Ḡ plug-in surrogate
   (§3, T1); find the rest.
2. **Commitment enforcement.** A decision recorded in `Notes/DECISIONS.md` or
   the writeup banners is not actually enforced by the code that is supposed
   to enforce it, so a caller can silently violate it. The precedent is the A4
   universe firewall, which accepted mixed candidate universes and silently
   normalized across them until it was guarded.
3. **Silent-wrong-answer paths.** A failure that produces a plausible number
   instead of an error. Discarded return values, swallowed exceptions,
   fallbacks that substitute a different estimator, and jitter escalation that
   is not counted all belong here.
4. **Estimator honesty.** An uncertainty summary that understates or
   misdescribes what it measures, or a diagnostic reported next to a quantity
   it is not comparable with.
5. **Reproducibility.** A committed artifact that the named script does not
   regenerate, or regenerates differently, within its stated tolerance.
6. **Test adequacy.** A claim the manuscript rests on that no test would catch
   if it broke.

### Severity

- **S1** — a number, figure, or artifact the manuscript or the D58 poster
  presents is wrong, or is right only by accident.
- **S2** — substantive: the computation diverges from the claim, a commitment
  is unenforced, or an uncertainty is materially misstated, but no published
  number is yet known to be wrong.
- **S3** — scope, robustness, or an unexercised silent-failure path.
- **S4** — hygiene, naming, or documentation that could mislead a future
  maintainer.

Every finding needs a **concrete failure scenario**: inputs or a call sequence
that produce the wrong outcome. A finding with no failure scenario is a
question, and belongs in the questions section instead.

---

## 3. Named targets

These come from the driver's scan of 2026-09-05. They are **starting points, not
conclusions**. Confirm or refute each on the evidence, and say which. Finding
that a named target is a non-issue is a useful result; report it under "what I
verified clean" with the reasoning. Do not stop at this list.

**T1 — the Ḡ plug-in surrogate.** `bistar_gp/laplace_evidence.py:135` passes
`avg_gp.mean, avg_gp.cov` to the metric, so G is evaluated once against a
moment-matched averaged pattern rather than averaged over per-draw
divergences. `docs/paper-sie-jmp/00-notation.md` glosses Ḡ as averaged across
data patterns. The synthesis review confirmed the gap and the section now
calls the quantity a plug-in surrogate; the notation amendment remains open on
#40's ledger. Question for the reviewer: which committed numbers depend on the
difference, and is the surrogate's error bounded or characterized anywhere?
Driver observation to follow up: the averaged-pattern construction at
`bistar_gp/aggregation_v3.py:77` (`mu_bar = w @ means`) emits divide-by-zero,
overflow, and invalid-value RuntimeWarnings during
`tests/test_zmx_estimators.py::test_prior_stage_flows_to_finite_is_log_Z`.
The weight validator just above rejects non-finite weights, so the
non-finite values arrive in `means`. Establish whether that is confined to
deliberate prior-stage stress inputs or can reach a reported number.

**T2 — the decomposition routines discard per-draw conditional covariance.**
*Driver correction, 2026-09-06 (raised by the Codex channel): the two affected
routines are `decompose_model_mcmc` (`bistar_gp/debias.py:131`) and
`decompose_model_hmc` (`:206`). The MAP wrapper `decompose_model` is NOT
affected; it computes the full posterior covariance from summed kernel blocks
at `:70-84` and explicitly retains inter-component cross-covariance. The
original wording of this target named the wrong function.*
`decompose_model_mcmc` and `decompose_model_hmc` iterate
`for (mean_i, _), comp_name in zip(...)` (`bistar_gp/debias.py:131` and
`:206`), dropping each draw's covariance, and both report
`cov=np.diag(std**2)` (`:144`, `:225`) where `std` is the across-draw spread
of means alone. Case E deliberately avoided this routine for that reason.
Live callers of the HMC variant:
`experiments/toy_example.py:87`, `experiments/mauna_loa.py:74`,
`experiments/bistar_debias_mauna_loa.py:410`,
`experiments/poster_d58_mauna.py:459`. A local workaround exists at
`experiments/honest_band_decomposition.py`, and
`experiments/toy_n20_poster_figures.py:80` carries a comment about it.
Question: does any **paper-facing or D58-poster-facing** band understate
uncertainty as a result, and if so by how much? Treat this as potentially S1.

**T3 — aggregation dial enforcement.** D60 fixed pooled aggregation as
canonical with `normalize_per_draw=False` shipped unchanged
(`bistar_gp/bms_star.py:412`, `:513`). The global-shift stabilization at
`:449-455` carries a comment arguing a per-row max would silently behave like
`normalize_per_draw` even when the flag is False. Verify that argument is
correct and that the shift actually cancels in the normalization.

**T4 — MLL weight concentration.** BMS\* averages Boltzmann weights across GP
draws. `bistar_gp/induced_prior.py` computes an effective sample size for its
own importance sampling, but the driver found no Pareto-k or ESS diagnostic on
the weights that drive model scores. Question: can a small number of draws
dominate a reported model probability without any diagnostic firing, and does
that occur in any committed artifact?

**T5 — the evaluation grid.** `bistar_gp/config.py:172` sets `n_eval: int =
60` as a default, and every pointwise divergence averages over exactly those
locations. Question: is any reported conclusion sensitive to the grid's size
or placement, and is the choice documented anywhere as a choice?

**T6 — metric scoping (W1).** `pw_kl_vcal` is the primary metric and
`kl_forward` is appendix-only. Question: is that enforced in code, or is it
convention that a caller can silently violate?

**T7 — the M2bR banner.** The `informative`-config HMC results are WITHDRAWN;
`runs/fit_method_metric_comparison/samples_hmc.npz` and
`runs/toy_tau_metric_comparison/` must never be cited. Question: does any code
path read, regenerate, or surface those artifacts in a way that could reach a
paper-facing number?

**T8 — universe firewall completeness.**
`_assert_candidate_universes_consistent` (`bistar_gp/bms_star.py:480`) closed
the A4 gap, and `run_bms_star` calls it at `:529`. But `soft_transfer`
(`:409`) and `compute_G_matrix` (`:368`) are public and perform the
aggregation without passing through that guard. Question: can a caller reach a
normalized cross-universe probability through the primitives, and does
anything in `experiments/` do so? Also check whether an untagged or
partially-tagged roster still passes the guard itself.

**T9 — Case E's new script.** `experiments/toy_debias_demo.py` (committed at
`8f1326d`, hardened at `a5b9cf8`) has never been seen by Codex. It carries an
AST-based guard asserting the library's sampler constants, a raise on
unmatched hyperparameter sites, and a jitter probe. Audit all three, plus the
mixture-interval construction and the law-of-total-variance inversion added in
the fix pass.

**T10 — test adequacy.** 67 test files. Question: for each of the
manuscript's load-bearing claims, would any test fail if the claim stopped
holding? Name the claims that no test protects.

**T11 — sentinel returns and swallowed exceptions in the evidence path.**
`bistar_gp/laplace_evidence.py:126-127` catches bare `Exception` and returns
`1e6`; `:136-137` catches `LinAlgError`/`ValueError` and returns `1e6`. Under
`exp(-G/tau)` a score of 1e6 becomes indistinguishable from zero weight, so a
parameter region that fails numerically is scored as an extremely poor fit
rather than reported as a failure. `_log_likelihood` returns `-1e10` on any
exception (`:253`), and both Laplace optimizers fall back to the starting
point when `minimize` raises (`:268` sets `converged=False`; `:486` records no
flag at all). Questions: how often does each path fire in the committed runs,
does anything downstream inspect `converged`, and can a Z_M or a model
probability in the manuscript depend on a silently substituted sentinel?

---

## 4. Output

Write exactly one file, then report the same text as your final message.

- Fable writes `runs/code_review_2026_09/fable_review.md`.
- Codex writes `runs/code_review_2026_09/codex_review.md`.

Create the directory if it does not exist. Write nothing else, anywhere.

Structure:

```
# Implementation review — <name yourself: the model you are actually running as,
and its reasoning-effort setting. Do not copy a placeholder>, 2026-09-05
VERDICT: PASS | FINDINGS

## Findings
### F<n> — S<severity> — <file>:<line>
Defect: ...
Failure scenario: <inputs or call sequence producing the wrong outcome>
Evidence: <what you ran or read that establishes it>
Fix: <concrete>

## Named targets T1-T11
<one line each: CONFIRMED / REFUTED / PARTIAL, with the reason>

## What I verified clean
<paths and claims you checked that hold, with how you checked>

## Open questions for the author
<things you could not settle without a decision>
```

Rank findings most severe first. Report the count of tests you ran and their
result. If you could not run something, say so rather than assuming.

---

## 5. Ground rules

1. Verify before asserting. Every numeric claim in a finding must come from
   something you ran or read, quoted with its location. The prose review
   rounds refuted roughly a quarter of all single-reporter findings on
   evidence; expect the same scrutiny.
2. Distinguish what the code does from what you would prefer it did. Style
   preferences are not findings.
3. When a finding rests on a claim about a committed artifact, check the
   artifact.
4. Reruns are allowed for the manuscript's own scripts; note runtime and
   whether output reproduced. Do not launch anything long-running without
   saying so in your report.
5. Never restore, drop, or inspect-then-modify `stash@{0}`.
6. `kb/` is gitignored local material; read it freely, never treat its
   contents as committed evidence.
7. No git mutations. No commits, no branches, no staging, no stash operations.

---

## 6. After both reports

The driver collates under the `HANDOFF-cases.md` §4 rules: findings reported
by both channels go straight to a fix queue; single-reporter findings are
adversarially checked by the other channel with a default of refuted when the
case is ambiguous. Statistical findings at S1 or S2 go to the author for
adjudication. Nothing is fixed, committed, or merged without the author.
