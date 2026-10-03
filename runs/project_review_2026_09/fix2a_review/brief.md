# Review brief: fix pass 2a of the BI*/BMS*-GP package (2026-10-03)

You are one of five independent reviewers (Codex gpt-6-astra, Fable, GLM 5.3, Gemini, Kimi K3) of
an uncommitted fix pass. Review it on its merits; do not defer to the implementer's report.

## What is under review

Repository suyoghc/bistar_gp_c (Bayesian model selection by GP-induced data priors, "BMS*").
Fix pass 2a implements the decision-free package contracts adopted by the 2026-09-26 five-channel
project review (SYNTHESIS section 10). The work order is `docs/paper-sie-jmp/HANDOFF-fix-pass-2.md`
(sections 3 to 6 define the queue items 2a-1 to 2a-10, the optional items, the style and editable-set
rules, the verification and the report). The defect specifications are the SYNTHESIS A-n rows and the
Codex C01-C11 / Opus C4-C10 findings they collate. The implementer's claims are in
`runs/project_review_2026_09/fix2a_report.md` and the draft decision entry D70 in
`Notes/DECISIONS.md`.

- Base: commit `69deeda` (branch `fix/code-review-2026-09`, PR #42).
- Under review: the uncommitted working tree of `/Users/sc8918/Documents/GitHub/bistar_gp_c-fix2a`
  (branch `fix/pass-2a`): edits to `bistar_gp/{__init__,aggregation_v3,bms_star,candidates,config,
  debias,decompose,induced_prior,laplace_evidence,viz}.py`, the new `bistar_gp/errors.py`, edits to
  `experiments/fit_method_metric_comparison.py`, `experiments/practice_EvansEtAL/run.py`,
  `experiments/prior_sensitivity_study.py` (the `_sir_bms` serialization block), the new
  `tests/test_fix2a_contracts.py`, two adapted tests in `tests/test_bms_aggregation.py` (an
  author-approved exception to the editable set, after a consultation recorded in the report), the
  report, and the D70 draft.
- Implementer's verification (verify, do not assume): full suite 1353 passed, 6 failed, 5 skipped,
  with the failures attributed to the known dependency-lock drift, four realroot tests that archive
  only tracked files (the new `errors.py` is untracked), and one timing flake; Case E oracle
  byte-identical; Cases A, C, D regenerated identically; Case B identical except ESS fields at
  2e-14 relative.

## Standard and severity (from `docs/paper-sie-jmp/HANDOFF-code-review.md` section 2)

A finding is anything where claim fidelity, commitment enforcement, silent-wrong-answer paths,
estimator honesty, reproducibility or test adequacy fails. Severity: **S1** a number, figure or
artifact the manuscript or the D58 poster presents is wrong; **S2** the computation diverges from
the claim, a commitment is unenforced, or an uncertainty is materially misstated, under a reachable
configuration; **S3** scope, robustness or an unexercised silent-failure path; **S4** hygiene,
naming, documentation. Every finding needs a concrete failure scenario (inputs or a call sequence
that produce the wrong outcome); without one it is a question. Grade by reachability: a paper path
or a documented call pattern; injected exceptions and never-used argument values count as latent.

## Questions

1. Item by item (2a-1 to 2a-10 and the optional A-5, A-7, A-15, A-18): does the change implement
   the work-order specification and the SYNTHESIS disposition correctly and completely? Name any
   gap, wrong exception type, wrong message, or behaviour the spec did not ask for.
2. Regressions: can any change alter a number on a paper path (the E7/headline SIR path in
   `experiments/prior_sensitivity_study.py::_sir_bms`, Cases A-E), or break a caller (including
   the frozen M2bR/M2c modules and drivers, which must not be edited, and the D58 poster driver)?
3. New holes: does any change introduce a new silent-wrong-answer path, an order dependence, an
   unhandled exception class, a log-only signal where a raise or recorded field is needed, or a
   reproducibility gap?
4. Tests: does each pin discriminate the pre-2a code and the defect class (would a plausible wrong
   implementation pass)? Are the two adapted D2 tests in `tests/test_bms_aggregation.py` weakened in
   any respect? What is missing?
5. The report's deviations (its section "Deviations", items 1-9): acceptable, or should any be
   reverted?
6. The report's open items (its section "Not done", items 1-8): which, if any, should be fixed
   inside 2a before it is committed, and which can wait?
7. The author's standing question for every fix: knowing what you now know, should this pass be
   deleted and re-implemented in a better, more concise, more elegant form? Answer per item with
   KEEP, SIMPLIFY IN PLACE (say how), or REWRITE (say why).
8. Record accuracy: is any claim in the report or the D70 draft false or overstated?

## Output format (markdown, at most about 2500 words)

- **Verdict**: APPROVE or REVISE for the code; one line on the record's accuracy.
- **Findings** table: ID (your channel prefix plus number), item, severity S1-S4, status
  (CONFIRMED by probe, CONFIRMED by source read, PLAUSIBLE, or NEEDS-REPO-VERIFICATION),
  file:line, claim, concrete failure scenario, suggested change, pin that would catch it.
- **Verified correct**: what you checked and found right (with the check).
- **Answers** to questions 5, 6 and 7 (a short table for 7).
- **What you ran or read** (repository channels: commands and outcomes).
