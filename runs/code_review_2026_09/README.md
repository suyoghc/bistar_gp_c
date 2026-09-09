# Implementation-correctness review, 2026-09-05

Four independent channels audit whether the code computes what the manuscript
claims. Governing document: `docs/paper-sie-jmp/HANDOFF-code-review.md`.
Prompts: `docs/paper-sie-jmp/prompts/code-review-{fable,codex}.txt`.

| Channel | Access | Output file | Status |
|---|---|---|---|
| Fable | full repo | `fable_review.md` | author-run, pending |
| Codex (model chosen at run time) | full repo | `codex_review.md` | author-run, pending |
| Kimi K3 (`moonshotai/kimi-k3`) | package-only | `kimi_k3_review.md` | driver-run 2026-09-05 |
| GLM 5.3 (`z-ai/glm-5.3`) | package-only | `glm_5_3_review.md` | driver-run 2026-09-05 |

The two package-only channels received an identical self-contained package
(handoff + manuscript section 02 as the specification + line-numbered source
for bms_star, laplace_evidence, aggregation_v3, metrics_v2, debias, decompose,
config, induced_prior, and experiments/toy_debias_demo; roughly 286 KB). They
cannot execute code or open committed artifacts, so their findings that depend
on either are tagged `NEEDS-REPO-VERIFICATION` and are for the driver to
settle against the repository before collation. The two repo-access channels
run the full protocol including the test suite.

The Codex pass additionally discharges the standing ledger item on PR #40 and
PR #41 ("ratify, or commission a Codex re-review after the lock lifts"); the
lock expired 2026-08-18.

Collation follows `HANDOFF-cases.md` §4: two-reporter findings go straight to
a fix queue, single-reporter findings are adversarially checked by the other
channel with a default of refuted when ambiguous, and S1/S2 statistical
findings go to the author. Nothing is fixed, committed, or merged without the
author.

## Driver baseline, 2026-09-05

`python -m pytest tests/ -q`: 1249 passed, 1 failed, 2 skipped, 539.8 s.
The single failure is `test_m2cr_environment_freeze.py::
test_committed_dependency_lock_reproduces_at_head`, caused by one package
added to the environment since the lock was frozen (`pypdf==6.14.2`; nothing
removed, no version changes). Not a code defect; resolution is the author's
because the lock is committed M2CR evidence.

## Fix pass 1 review round, 2026-09-07/08

Fix pass 1 (work order `docs/paper-sie-jmp/prompts/code-review-fix1.txt`,
implemented by Fable in the sibling worktree, branch `fix/code-review-2026-09`)
was reviewed against the brief `docs/paper-sie-jmp/prompts/code-review-fix1-review.txt`.

| Channel | Access | Output file | Verdict |
|---|---|---|---|
| Codex gpt-6-astra xhigh | full repo | `fix1_codex_review.md` | REVISE (R1-R10) |
| Fable 5.1, fresh instance | full repo | `fix1_fable51_review.md` | APPROVE (F1-F7) |
| Kimi K3 (`moonshotai/kimi-k3`) | package-only | `fix1_kimi_k3_review.md` | pending |
| GLM 5.3 (`z-ai/glm-5.3`) | package-only | `fix1_glm_5_3_review.md` | pending |

Implementer's report: `fix1_report.md` (with dated addenda). Adjudication and
the pass 1b record: `fix1_synthesis.md`. Diffs and snapshots: `fix1_bundle/`
(`fix1_tracked.diff` + `fix1_new_files.txt` = the reviewed pass-1 state;
`fix1b_delta.diff` = what pass 1b changed; `fix1b_cumulative_tracked.diff`).
