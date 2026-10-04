# Consultation brief: how would you cast the author decision sheet? (2026-10-03)

## Task context

You are advising the author of the BI*/BMS*-GP journal paper (repository `suyoghc/bistar_gp_c`,
local clone `/Users/sc8918/Documents/GitHub/bistar_gp_c`) on how to fill in ("cast") the author
decision sheet written after the 2026-09-26 five-channel project review. The sheet is
`/Users/sc8918/Documents/GitHub/bistar_gp_c/runs/project_review_2026_09/DECISION_SHEET.md`, an
untracked live copy in the main worktree. Each line lists options already on record and a
default that every checking channel recommended in September. Nothing on it has been cast.

### What happened after the sheet was written (the sheet does not reflect it)

- PR #42 (fix passes 1, 1b, 1c: D68; plus the D69 project-review record) was merged into `main`
  on 2026-10-03 as the true merge `8c6e6b2`, by direct author instruction, ahead of line B9
  (whose A1-A3 gate is still uncast).
- Fix pass 2a (D70: the decision-free package contracts A-1 to A-4, A-6, A-10, A-11 with A-24,
  A-13's code half, A-23's package half, and the hardened Case D producer
  `experiments/practice_EvansEtAL/run.py` with seed, strict mode and sampler diagnostics;
  optional A-5, A-7, A-15, A-18; a five-channel review and its fold pass) was merged as PR #43
  (true merge `622c566`); the D70 closeout PR #44 was merged as `84e9881`, the current `main`.
  So `main` now contains fix pass 1 and 2a, and B9's "integration branch from PR #42 ... fix
  pass 2a on it" was partly overtaken: 2a went straight to `main`.
- The six paper PRs, #36 (Case B, `paper/case-b-occam-dial`), #37 (Case C,
  `paper/case-c-haaf`), #38 (Case D, `paper/case-d-mopen`), #39 (Case A,
  `paper/case-a-vanbork`), #40 (synthesis sections, `paper/synthesis-sections`) and #41
  (Case E, `paper/case-e-debias`), are open; each conflicts with `main` on
  `Notes/DECISIONS.md` only (their D60-D67 blocks against D68-D70).
- B2 (`metric_name`) was out of 2a's scope and is still open.
- Test suite on the 2a code: 1354 passed, 5 skipped, and the four realroot launch tests pass
  once `bistar_gp/errors.py` is tracked (it now is). The only known failure is the
  dependency-lock test; the drift is now `pypdf==6.14.2` in the user site AND
  `imageio-ffmpeg==0.6.0` in the base site-packages (B1 names only `pypdf`).
- D58 poster: card6 still re-renders from the committed arrays to its pin `0fe67b15`; cards 7
  and 8 raise `KeyError` through the frozen driver since fix pass 1 (relevant to C1).
- Open items recorded by 2a for the author (D70, report "Not done"): the penalty overflow near
  the float maximum; the `score_averaged_gp` NaN path; direct `np.load` reads in
  `prior_sensitivity_study`; the site alias table belongs in `model.py` (R16); cards 7-8; the
  legacy `bistar_gp/cache` archives are unregistered.

### Where to read (all read-only)

- The sheet (path above).
- The committed record on local branch `main` (`84e9881`); read with
  `git -C /Users/sc8918/Documents/GitHub/bistar_gp_c show main:<path>`:
  - `runs/project_review_2026_09/SYNTHESIS.md` (revision 1.3; section 10 is the adopted plan;
    findings are cited as A-n for code and B-n for the project);
  - `runs/project_review_2026_09/fix2a_report.md` and
    `runs/project_review_2026_09/fix2a_review/SYNTHESIS.md`;
  - `runs/code_review_2026_09/ledger_draft.md` (ledger revision 3) and
    `runs/code_review_2026_09/fix1_synthesis.md`;
  - `Notes/DECISIONS.md` (D68, D69, D70 at the end).
- D60-D67 and the D66/D67 closing ledgers are on the paper branches:
  `git -C /Users/sc8918/Documents/GitHub/bistar_gp_c show origin/paper/<branch>:Notes/DECISIONS.md`
  (and other files on those branches the same way).
- The manuscript apparatus is untracked in the main worktree:
  `/Users/sc8918/Documents/GitHub/bistar_gp_c/docs/paper-sie-jmp/` (`00-notation.md`, the
  section files, the HANDOFF files).
- Do not rely on the main worktree's tracked files: it is checked out on
  `paper/case-e-debias` with uncommitted edits to `Notes/DECISIONS.md` and
  `Notes/SCRATCHPAD.md`.

## Objectives

1. For every line (A1, A1a, A1b, A1c, A2, A2a, A3 to A9, B1 to B10, C1, C2), give the option you
   would cast and why, in one or two sentences grounded in the record (cite file:line, a
   D-entry or a finding id).
2. Say where your cast differs from the sheet's default and why, and where the events of
   2026-10-03 make a line moot, change its best option, or require rewording (in particular
   B1, B2, B8, B9 and the closing paragraph "What happens the moment the sheet is cast").
3. List any decision the current state requires that the sheet lacks (for example: how the
   paper PRs now integrate given that #42 and 2a are on `main`; whether an integration branch
   is still needed; from which commit the canonical Case D run starts).
4. Give the order in which you would cast, naming the first three lines and what each
   unblocks.

## Constraints

- Strictly read-only. No file writes anywhere in the repository or its worktrees. No git
  command that changes refs, the index or worktrees (no fetch, pull, checkout, switch,
  commit, stash, worktree add or remove, merge, reset). Never touch `stash@{0}`. No network
  and no package installs. Do not run the test suite or any experiment.
- Do not edit the sheet; your answer goes in your final message only.
- Be decisive: one cast per line. Mark a line "author-only" when the choice rests on the
  author's taste or schedule rather than on evidence, and still state your lean.
- Keep the answer under about 1,500 words.

## Output format

1. A markdown table with columns: Line | Your cast | Sheet default | Same? | Rationale and
   evidence.
2. "Changes since 2026-09-26" (bullets).
3. "Missing decisions" (bullets).
4. "Cast order" (numbered).

## Success criteria

Every line has a cast; every disagreement with a default has a reason tied to evidence; the
answer accounts for the 2026-10-03 merges.
