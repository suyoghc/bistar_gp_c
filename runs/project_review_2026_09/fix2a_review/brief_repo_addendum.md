
## Repository channel rules (you have read access to the repository)

- Review target: `/Users/sc8918/Documents/GitHub/bistar_gp_c-fix2a` (uncommitted working tree, branch
  `fix/pass-2a`, base `69deeda`). See the full change with
  `git -C /Users/sc8918/Documents/GitHub/bistar_gp_c-fix2a diff 69deeda` plus the two untracked files
  `bistar_gp/errors.py` and `tests/test_fix2a_contracts.py`. The work order is in the MAIN worktree:
  `/Users/sc8918/Documents/GitHub/bistar_gp_c/docs/paper-sie-jmp/HANDOFF-fix-pass-2.md`; the record
  (SYNTHESIS, channel reviews, the 2a report) is under `runs/project_review_2026_09/` in the 2a
  worktree. Case scripts live only on the paper branches: read them with
  `git -C <worktree> show origin/paper/case-<x>:<path>`.
- READ-ONLY everywhere. Do not create, edit or delete any file inside
  `/Users/sc8918/Documents/GitHub/bistar_gp_c-fix2a`, `/Users/sc8918/Documents/GitHub/bistar_gp_c` or
  `/Users/sc8918/Documents/GitHub/bistar_gp_c-fix`. Do not run any git command that writes (add,
  commit, stash, stash create, checkout, switch, reset, restore, branch, tag, worktree, merge, rebase,
  push, fetch, gc). Never touch `stash@{0}`.
- Do NOT run the full test suite: it contains Git-mutating tests
  (`tests/test_m2cr_historical_anchor.py`, `tests/test_m2cr_r4_launch.py`,
  `tests/test_m2cr_realroot_integration.py`). Run targeted test files or test ids instead, with
  `-p no:cacheprovider`.
- Every Python run: `PYTHONPATH=/Users/sc8918/Documents/GitHub/bistar_gp_c-fix2a`,
  `PYTHONDONTWRITEBYTECODE=1`, and print `bistar_gp.__file__` once (the editable install otherwise
  imports the MAIN worktree's unfixed package). Put every probe script, temporary file and output
  under your scratch directory (given in your dispatch), and point `TMPDIR`, `MPLCONFIGDIR` and
  `XDG_CACHE_HOME` there. To exercise the pre-2a code, extract it read-only, for example
  `git -C /Users/sc8918/Documents/GitHub/bistar_gp_c-fix2a archive 69deeda bistar_gp experiments tests | tar -x -C <scratch>/base`.
- No Mauna Loa inference of any kind, no network calls, no package installs.
- Case regenerations are optional; if you run one, build it in your scratch directory (copy inputs
  such as `/Users/sc8918/Documents/GitHub/bistar_gp_c/runs/prior_sensitivity` instead of
  symlinking them, so nothing can write into the main worktree).
- Return the review in the brief's output format as your final message.
