# Fable's casts for the 2026-09-26 author decision sheet (read-only consult, 2026-10-03)

(Saved verbatim from the Fable subagent's final report; Astra's answer is in astra.md beside it.)

Read: the sheet; `main` (`84e9881`) copies of SYNTHESIS rev 1.3, fix2a_report, fix2a_review/SYNTHESIS, ledger rev 3, fix1_synthesis, D68-D70; D60-D67 on the branch tails; the untracked apparatus; read-only `merge-tree` and per-block hashes. Nothing written, no refs touched.

## 1. Casts

| Line | Your cast | Sheet default | Same? | Rationale and evidence |
|---|---|---|---|---|
| A1 | (v), endpoint (iii); fall back to (i) only if the two-seed run plus re-review misses the cut line | (v)/(iii) | Yes | A-20/B-0: two independent seed-0 regenerations (Opus 647 s, Fable 608 s) give identical changed tables. The (iii) prerequisite is now on `main` (D70, 2a-10 hardened producer), and `paper/case-d-mopen` has an empty diff under `experiments/practice_EvansEtAL/` against `71540836`, so no conflict. Addenda go on the case D branch (SYNTHESIS §10, Opus 1). |
| A1a | add | add | Yes | Same run, no extra compute; the stored artifacts predate W1 (`pw_nll/pw_mse/pw_hellinger` only, D64), so section 06 cannot otherwise speak in the primary metric. Fix it before the run (ledger Item 3(iii); Astra 4). |
| A1b | two seeds, `strict=True`, diagnostics recorded | two seeds + diagnostics | Yes | Both matching regenerations used seed 0 (determinism, not Monte Carlo robustness; §10 Opus 1). `run.py` now threads `--seed`, `strict` and `sampler_records` (fix2a_report 2a-10), so the protocol is free. |
| A1c | withdraw alongside | withdraw alongside | Yes | `be54c7f` (`results_diag`) and `f6c1d40` (`results_hierarchical`) are 2026-02-16, before the D6 fix `9f75fb0`; `git grep` on the case D branch finds no reference in docs or `regret_curves_mopen.py`; D64 says "not consulted". D6 on `main` still names only `bistar_gp/cache/*.npz` and the Mauna runs. |
| A2 | (C) | (C) | Yes | `00-notation.md:9` (ψ as a sampled f) and `:13` (Ḡ "averaged across data patterns") are committed nowhere (`git log --all` empty), so "commit unchanged first" is a real first act. Ledger Item 4 table (0.441 vs 0.50-0.51; τ=0.1 four-way near-tie); D66 SC1 is the same decision; two Ḡ symbols per Codex P01. |
| A2a | sign off | sign off | Yes | VERDICTS.md SC2: checker split, driver adjudicated FIX, FIX-3 already in the text; D60's pooled Target A row (0.000/1.000) shows the pooled τ→0 limit is global-minimum domination. Signing off ratifies text already present. |
| A3 | (a), exact ties split equally | (a) | Yes | The code half is done: 2a serializes `hard_win_credit`, `attainment`, `tie_fraction`, `weight_ess` in `_sir_bms` and warns on low ESS (D70). Left: the E7 script and README, Case C's derivable line (attainment 1.000/0.999, split 0.5005/0.4995, ledger Item 5), §3.4 and §5 text. ESS 978/1000 behind the headline, 2.5-104 behind the appendix metric (B-8). |
| A4 | restrict and state | same | Yes | A-21: E7 fits once (`cand.fit(x_np, y_np)`), and the committed `kl_forward` pooled row favors the restriction (0.415 vs 3.4e-10). Astra 4: a specification repair, not new science; a per-draw headline breaks continuity with 0.441. |
| A5 | state and report | same | Yes | A-22: 0.441/0.412/0.445/0.439 by placement, size stable, appendix attribution flips. One sentence in §02 plus an E7 README line. |
| A6 | rewrite | rewrite | Yes | B-6(a); Codex probe `shift_invariant True`; §03:129-138, §02, §08. |
| A7 | create and move | same | Yes | B-6(b)(f): `main.tex`'s `\appendix` holds only notation and provenance (Opus PF11). Dropping would lose the D61 attribution the synthesis keeps (D66). |
| A8 | cut | cut | Yes | `06-case-D-mopen-calibration.md:220` placeholder; D64 allows "clean excision"; first item on the B10 cut line. |
| A9 | reword (author-only: confirm instead if the paper is read before the integrated review round) | reword | Yes | `05-case-C-nested-constraints.md:8-10` bracket; `kb/Raw/WANTED.md:131` "abstract unrecoverable". |
| B1 | uninstall both, keep the lock | uninstall `pypdf`, keep the lock | Yes, reworded | The drift is two packages: `pypdf==6.14.2` (user site, its only package) and `imageio-ffmpeg==0.6.0` in the designated interpreter's own site-packages (D70 Result; `imageio_ffmpeg-0.6.0.dist-info` present). The lock has `arviz==0.23.4` and neither of the two. Two uninstalls, then the lock test alone; expected suite at `84e9881`: 1359 passed, 5 skipped, 0 failed (1364 collected). Tooling that needs them goes to a venv. |
| B2 | (i) | (ii) | **No** | `mcse_strategy.py` is in the frozen group (HANDOFF-fix-pass-2 §0: its contract "is why `metric_name` (B2) is not in 2a"; `tests/test_m2c_mcse_strategy.py` pins it). That path aggregates prebuilt matrices and never reaches `compute_G_matrix` (D70); A-9 is S4 with no default-relying caller. (ii) buys one record field at the price of an M2c freeze amendment. (i): pass the in-scope name at `metrics_v2.py:398` (loop variable at `:391`), document the rule in `soft_transfer`, fold into 2b. |
| B3 | JSON plus manifest and recipe | same | Yes | All three pools regenerate bit-identically (71-74 s; §9 bullet 4). `stage_a_toy_elicited.json` (17,181 B) is cited by section 07 (D67 FIX-1) and committed nowhere. |
| B4 | sign off | sign off | Yes | D67 FIX-2 already restricted the sentence to N=20 and states the N-dependence is untested; a sweep is new science behind the cut line. |
| B5 | leave out | leave out | Yes | D67: "available but not required"; B10 names enrichment. |
| B6 | ratify | ratify | Yes | Codex was usage-locked to 2026-08-18 (D66/D67). The 2026-09-26 Codex Astra round regenerated Cases A-E (Case E byte-identical) and reviewed the synthesis text (P01-P08): the later independent check. A fresh re-review would cover text A2-A7 will amend anyway. |
| B7 | cite only committed material | same | Yes | `experiments/mechanism_figure_poster.py` (22 KB) and `runs/viz_unification/` are untracked, kb/Wiki is gitignored (B-3); VERDICTS SC3: the script's entry point never runs the cited check. |
| B8 | as listed, plus one sentence per PR body | as listed | Yes, extended | #38 Draft follows A1 (v); #39 retitle (D61 fork RESOLVED 2026-08-12); #40/#41 Draft until A2 and B3-B6 close. New: all six conflict with `main` on `Notes/DECISIONS.md` only (verified read-only by `merge-tree`), so no paper PR merges to `main` directly; each body should say it lands through the integration branch. |
| B9 | authorize | authorize once A1-A3 are cast | Yes, reworded | Cut from `main` at `84e9881` (contains #42 and 2a), not from PR #42; "2a on it" is done; the union inserts D60-D67 from the branch tails before D68 (both sides append at line 5720, which is the whole conflict). Order: A, C, 2b (Case A checker, Case C import, B2(i)), B, D after its run and re-review, E, synthesis; true merges; suite in a clone. The gate is met once A1-A3 are cast in the same sitting. |
| B10 | accept, with D70's deferred items appended | accept | Yes, list extended | Astra 10, Opus 10. Also behind the line: penalty overflow near the float maximum, the `score_averaged_gp` NaN path, direct `np.load` reads in `prior_sensitivity_study`, R16 alias table, unregistered legacy cache archives (D70 "Not done"); no paper path reaches them. |
| C1 | (B); start the inventory now | (B) | Yes | Ledger Items 1-2. At `main`, card6 re-renders to its pin `0fe67b15` through the frozen driver (D70), but cards 7-8 raise `KeyError` since fix pass 1 (joint group posteriors required), so (A) would leave two cards that cannot even be re-rendered and (B)'s correction driver is needed regardless. Does not gate submission (Opus 8). |
| C2 | after the inventory (author-only; lean yes once the presented set is identified) | after the inventory | Yes | Opus plan check 8; the erratum's content depends on ledger Item 1 question (1), which image set was presented (poster-repo `handoff/d58-figures-11572645`, `7401281`, local only). |

## 2. Changes since 2026-09-26

- `main` = `origin/main` = `84e9881` (D70 closeout) after the true merges `8c6e6b2` (#42, 13:59) and `622c566` (2a, 14:05). The sheet's evidence pointers "on `fix/code-review-2026-09`" now resolve on `main`. D69 still says OPEN until the sheet is cast.
- B9 is partly overtaken: no cut from PR #42, no 2a step, union is D60-D67 onto `main`'s D68-D70. The main worktree's uncommitted D60-D67 block is byte-identical per block to each branch tail apart from trailing separator lines (per-block md5, checked here), so it is a valid union seed; the per-block hash rule still applies at each merge.
- B1's drift widened to two packages; the sheet's "1347 passed" baseline becomes 1359/5 at `84e9881` (the four realroot launch tests pass now that `errors.py` is tracked).
- A1's compute prerequisite exists on `main`; A3's code half is done; B2 moves from "2a's last item" to a 2b item.
- C1 gains the cards 7-8 `KeyError` fact.
- Closing paragraph, rewritten: within the day, the D64 and D6 addenda on `paper/case-d-mopen`; the checksummed archive of the untracked apparatus and local inputs; `00-notation.md` and the apparatus committed unchanged (docs-only PR to `main`: no branch tracks them, so no new conflicts); PR statuses; the two uninstalls and the lock test; the integration branch cut from `84e9881` with the union; 2b. The canonical Case D run follows the hardened producer from a commit descending from `84e9881`, two seeds, strict, `pw_kl_vcal` added.

## 3. Missing decisions

- Integration topology: one integration branch from `84e9881` versus serial merges into `main`. Lean: one branch, so the consolidated review round (Opus 10) happens before `main` moves; one true-merge PR at the end.
- Canonical Case D run: start commit and artifact home. Lean: true-merge `main` into `paper/case-d-mopen` first (Notes union; `run.py` untouched there), run from that merge commit into a new directory (keep `results_hmc/` as historical evidence per (v)), commit the archive, the rerun `regret_curves_mopen.py` outputs and the section rewrite there, so the package commit is an ancestor of the artifact commit (§10 order point).
- Where the apparatus baseline lands (`00-notation.md`, HANDOFFs, `build_tex.py`, tex): lean `main`, as-is, amendments later on the integration branch.
- Recording the cast: commit the cast sheet under `runs/project_review_2026_09/` with a D69 Update (Notes-only PR) the day it is cast.
- The main worktree's uncommitted Notes edits (597 + 18 lines): adopt as the union seed; the author, never an agent, clears the checkout once the integration branch carries the union; the SCRATCHPAD lines ride with the CHATLOG hygiene.
- Assignment of D70's "Not done" items: R16 and `score_averaged_gp` validation to 2b (small package edits off the paper paths); the rest recorded behind the cut line.

## 4. Cast order

1. A1 with A1a-c in one sitting: unblocks the D64 suspension and D6 addenda, #38 to Draft, the longest pole (two-seed run plus re-review, about 1.5 days) and the section 06/08 rewrite.
2. A2 with A2a: unblocks the notation baseline commit, the ψ/Ḡ amendment, the 2c sensitivity artifact, and #40 leaving Draft (with B3-B6).
3. B1: unblocks a green gate for every later check (1359/0/5 expected at `84e9881`).
4. Then A3; B9 (cut the branch the same day: A, C, 2b with B2(i)); B8; B3-B7 (#40/#41 leave Draft); A4-A9 as amendments on the integration branch; B10; C1 (inventory starts, correction act runs in parallel, gates nothing); C2 last.
