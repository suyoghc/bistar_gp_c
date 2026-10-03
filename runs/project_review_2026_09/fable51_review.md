# Project review 2026-09-26 — Fable 5.1 (this session; full repo access)

Disclosure: this channel implemented fix passes 1, 1b and 1c and coordinated
their review rounds. Its findings on the fix-pass surface are therefore not
independent of the code; its fresh contributions are the regeneration checks
and the probes in sections 2 and 4. This file was written before any other
channel's output in this directory was opened. Probe scripts and logs:
scratchpad `proj_review/fable/` (ephemeral; named per finding).

## 1. Verdict

**Code: APPROVE** at `ddf8c9d`. No S1, S2 or S3 finding survives probing; the
residue is S4 (a known deferred policy, a documented dual meaning, provenance
prose, and one arithmetic-path change that moves ESS fields by 1e-14).
Every manuscript-path artifact that could be regenerated against this package
regenerates: Case A's E7 and Case D bit-for-bit, Case B to round-off in ESS
fields only, Case E byte-identical (the 2026-09-08 oracle), Case C pending
below.

**Project: NOT READY** for submission. Blocking list, in the order they
should be cleared:

1. Five author decisions on the code-review ledger (`runs/code_review_2026_09/ledger_draft.md`
   Items 1-5) have been open since 2026-09-06. Items 3, 4 and 5 gate
   manuscript text (Case D's stored comparisons; the row definition behind
   the 0.441 sentence; section 2.4's reporting commitment); Items 1 and 2
   gate the D58 poster record.
2. Section 06 carries `[E8B-PLACEHOLDER] UNBUILT OPTIONAL MODULE`
   (06-case-D.tex:309).
3. The headline path's inputs, `runs/prior_sensitivity/` (63 MB, 61 files;
   the `toy_elicited` subset 7.2 MB), are committed on no branch although
   sections 03, 04 and 07 cite them thirteen times and D67 already says the
   stage-a artifact "should be committed".
4. Seven unmerged branches; every pair conflicts on `Notes/DECISIONS.md`;
   no integration branch exists.
5. The D58 poster (presented 2026-08-11) drew bands that FIX-2 showed to be
   understated by 5 to 14 times; the poster record carries no correction.

## 2. Code findings (Part A)

| ID | Target | Sev | Status | Location (ddf8c9d) | Claim |
|---|---|---|---|---|---|
| A1 | T4/T3 arithmetic | S4 | CONFIRMED | `bistar_gp/bms_star.py` `log_weight_ess`; `laplace_evidence.py` `_weight_ess` | Pass 1b's shared ESS routine changes the arithmetic path; Case B's committed ESS fields regenerate with relative differences up to 2e-14 (2815 fields in `e6_results.json`, 8 in `figure_results.json`); every non-ESS field, including every log Z and every crossing, is identical. Hash pins on those two artifacts will not match a byte-for-byte regeneration. |
| A2 | T6 | S4 | CONFIRMED | `bms_star.py` `run_bms_star`, implicit roster | In a fresh process the implicit `metric_names=None` roster omits `pw_kl_vcal` (registry misses only on lookup); a warning names it. No experiment script uses the implicit roster. Design, disclosed in fix1_synthesis rev 3. |
| A3 | FIX-3 seam | S4 | CONFIRMED (disclosed) | `bms_star.py:583` | `metric_name` optional; required in fix pass 2 needs a metric identity on `mcse_strategy_estimate` (M2c contract). Author accepted optional 2026-09-08. |
| A4 | FIX-2 seam | S4 | CONFIRMED (disclosed) | `debias.py` `ComponentResult.samples` | Dual meaning (function draws on the MAP path, conditional means on draw paths, marked by `samples_kind`), retained for the read-only poster driver. |
| A5 | hygiene | S4 | CONFIRMED | package docstrings | Review provenance prose (review IDs, dates) in docstrings; the fix-pass Fable 5.1 review counted 18 "2026-09" and 26 "FIX-n" added lines. Trim at pass 2; `Notes/DECISIONS.md` D68 carries the history. |
| A6 | FIX-7a | S4 | CONFIRMED | `config.py` `ExperimentConfig.metrics`; `experiments/bms_star_toy.py:132` | The legacy toy script now scores eleven metrics instead of ten (the primary metric was appended by FIX-7a, as ordered). Not a paper path. |
| A7 | FIX-1d | S4 | CONFIRMED | `debias.py` `decompose_model_hmc(strict=True)` | Four legacy callers (`toy_example.py:87`, `mauna_loa.py:74`, `bistar_debias_mauna_loa.py:425`, `poster_d58_mauna.py:459`) now raise on a failed draw where they skipped it. D58 decomposed 200/200, so its record is unaffected; a future poster rerun would also produce law-of-total-variance bands, wider than the pinned figures (see B5). |

Named targets, re-examined on the post-fix code:

- **T1 (Ḡ plug-in surrogate), characterized.** On the headline SIR draws
  (`toy_elicited`, n_pred = 1000, seeded exactly as `_sir_bms`), the metric
  evaluated on the averaged GP is 0.60 times the per-draw mean divergence for
  `pw_kl_vcal` (ratios 0.596 / 0.588 / 0.622 / 0.597 across Linear /
  Sinusoidal / Sin+Linear / Quadratic) and 0.85 times for `kl_forward`. At
  tau = 1 the Sin+Linear posterior is 0.403 from the plug-in Ḡ, 0.526 from
  the per-draw mean Ḡ, and 0.441 from the shipped pooled aggregation. The
  ratio is nearly uniform across candidates, so orderings survive; absolute
  Z_M values on the Laplace path (Case B) carry the factor. Section 02
  already names the quantity a plug-in surrogate; the number is not in the
  manuscript (see B10). Probe: `probe_T1_surrogate.py`.
- **T4 (weight concentration), characterized.** `pw_kl_vcal`: ESS behind
  the Sin+Linear posterior 551 (tau 0.1), 864 (0.3), 978 (1.0), 997 (3.0),
  1000 (10) of 1000 draws; exact-tie split credit 0.973. `kl_forward`:
  ESS 2.5 (tau 0.1), 9.4 (0.3), 104 (1.0), 370 (3.0), 727 (10). The
  appendix metric's pooled posterior at tau <= 1 rests on a handful of
  draws, which is the E7 README's "aggregation artifact" in numbers. The
  diagnostic now exists in the package (`BMSStarResult.weight_ess`) but no
  committed artifact or section reports it. Probe: `probe_headline_T1_T4_T5.py`.
- **T5 (evaluation grid), verified clean.** Headline pooled `pw_kl_vcal`
  posterior at tau = 1 for n_eval 30 / 60 / 120 / 240: Sin+Linear 0.440 /
  0.441 / 0.441 / 0.441. The choice is not documented as a choice (B10).
- **T2, T3, T6, T7, T8, T9, T11:** closed by the fix passes with pins, and
  re-verified here only through the regenerations of section 4 and the Case
  E oracle; the four fix-pass channels' probes (runs/code_review_2026_09/)
  remain the independent evidence.
- **T10:** see B6.

## 3. Project findings (Part B)

| ID | Item | Sev | Status | Location | Claim |
|---|---|---|---|---|---|
| B1 | P3 | BLOCKER | CONFIRMED | `runs/code_review_2026_09/ledger_draft.md` Items 1-5 | Five "Decision required" items open since 2026-09-06; no disposition recorded except `metric_name` (2026-09-08). Items 3-5 gate manuscript statements. |
| B2 | P1 | MAJOR | CONFIRMED | `tex/sections/06-case-D.tex:309` (source `docs/paper-sie-jmp/06-case-D-mopen-calibration.md` on `paper/case-d-mopen`) | `[E8B-PLACEHOLDER] UNBUILT OPTIONAL MODULE` in the section body. Build or cut. |
| B3 | P5 | MAJOR | CONFIRMED | `runs/prior_sensitivity/` (untracked on every branch; 0 commits in `git log --all`) | Cited thirteen times (07: 8, 04: 3, 03: 2); the headline 0.441, E7 and Case C read the `toy_elicited` prior-IS caches (`is_draws_toy_elicited_s{0,1,2}.npz`, 2.3 MB each) and `stage_a_toy_elicited.json`; D67 records that the stage-a file "should be committed". Regenerable only by re-running stage a; cross-machine determinism unverified. |
| B4 | P2 | MAJOR | CONFIRMED | `git merge-tree` fix head x each paper branch, and every paper-branch pair | 21 of 21 branch pairs conflict, all and only on `Notes/DECISIONS.md` (each branch appends after D58 at the same location). No other file conflicts. |
| B5 | P1/P3 | MAJOR | CONFIRMED | `runs/poster_d58/` (no markdown record); `Notes/DECISIONS.md` D58 (main); D68 (fix branch) | The poster's decomposition bands came from the pre-fix `decompose_model_hmc` (spread of conditional means only); the fix-pass ledger quantified the understatement at 14x / 9x / 5x. The D58 record and the pinned figure manifest carry no correction; `poster_d58_mauna.py` now regenerates different (wider) bands than the pinned PNGs. |
| B6 | P4 | MAJOR | CONFIRMED | `tests/` (1352 collected) | 604 m2cr + 165 m2c + 145 d19 + 53 poster + 47 m2br + 46 e1 = 1060 tests (78%) protect infrastructure and freezes; about 230 protect package arithmetic; none regenerates a manuscript number. The READMEs' hash pins are the only guard on the case artifacts, and Case B's pins already no longer match (A1). E7 regenerates in 8 s, Case D in 4 s, Case B in 41 s. |
| B7 | P2 | MINOR | CONFIRMED | `paper/case-c-haaf:experiments/haaf_nested_constraint.py:46` | Imports `e7_convention_sensitivity` from Case A's branch (A before C); works once both are integrated; fix pass 2 switches it to `aggregate_convention`. |
| B8 | P2/P4 | MINOR | CONFIRMED | `paper/case-c-haaf:pyproject.toml`, `requirements.txt` (+ `arviz>=0.17`) | The M2CR dependency lock (`docs/m2c_freeze/m2cr_dependency_lock_v1.json`) and its test will need one refresh at integration, together with the known pypdf drift. |
| B9 | P3 | MINOR | CONFIRMED | PR titles; `Notes/CHATLOG.md`, `Notes/SCRATCHPAD.md` | PR #39's title says "fork awaits author" while D61's status update records the D60 fork RESOLVED 2026-08-12; #40 and #41 are still Draft; CHATLOG ends 2026-07-26 and SCRATCHPAD still opens with D58, so the August paper phase and the September review phase are recorded only in D-entries and runs/ records. |
| B10 | P1 | MINOR | CONFIRMED | sections 02, 03, appendix | Three measured facts the manuscript could state and does not: the surrogate ratio (T1), the ESS behind the headline and behind the appendix metric (T4), and the evaluation-grid insensitivity (T5). |
| B11 | P5 | MINOR | CONFIRMED | `runs/viz_unification/` (untracked) | Cited in section 04 as a cross-check only; the W4 numbers are pinned to `bistar_viz/scripts/viz_unification_compare.py` at commit `a87356a`, so regenerable. Acceptable; say so in the README. |
| B12 | P5 | MINOR | CONFIRMED | `paper/case-b-occam-dial:runs/occam_dial/README.md` | Regeneration against this package matches to 2e-14 relative in ESS fields (A1); the README's byte pins need a tolerance statement or a regeneration at integration. |
| B13 | P4 | MINOR | CONFIRMED | `tests/test_m2cr_environment_freeze.py::test_committed_dependency_lock_reproduces_at_head` | Known failure (pypdf added to the environment since the lock). Lock refresh is the author's, because the lock is M2CR evidence. |

### B4 detail: merge plan

Order and mechanics I would use, all on one integration branch cut from
`main` after PR #42 merges (the fix branch fast-forwards onto `main` with no
conflict):

1. `paper/case-b-occam-dial` (D62), `paper/case-c-haaf` (D63),
   `paper/case-d-mopen` (D64), `paper/case-a-vanbork` (D60, D61, D65),
   `paper/synthesis-sections` (D66), `paper/case-e-debias` (D67): merge in
   that order. Each merge conflicts only in `Notes/DECISIONS.md`; resolve by
   keeping both sides and appending the incoming entries after the last
   existing one. The D numbers are already unique across branches, so the
   resolution is deterministic and reviewable by `grep '^## D'`.
2. After each case merge, run that case's script in place and compare its
   `results.json` to the committed one (the comparison used here:
   `proj_review/fable/cases/compare.py`); expected: A, D, E identical; B to
   2e-14 in ESS fields; C per section 4.
3. Run the full suite once at the end; refresh the M2CR dependency lock
   (B8, B13) in a separate, recorded commit.
4. One PR to `main`; then fix pass 2 on `main`.

The A-before-C dependency (B7) is satisfied by the order above. No paper
script calls an API the fix passes changed in a breaking way: the static scan
over the six branches' scripts found only `laplace_log_Z_Mx` / `is_log_Z_Mx`
(Case B; trailing `strict` keyword added, defaults unchanged) and the Case A
script import (Case C); the regenerations confirm it dynamically.

## 4. Verified-correct list

- **Regeneration against `ddf8c9d`, from a scratch environment whose
  `bistar_gp` resolves to the fix worktree (path printed in every log) and
  whose only inputs are the committed scripts, the tracked practice
  artifacts and the local prior-IS caches:**
  - Case A E7 (`e7_convention_sensitivity.py`): every number identical to
    `paper/case-a-vanbork:runs/e7_convention_sensitivity/results.json`
    (anchor 0.183 / 0.192 / 0.441 / 0.184), 8.3 s.
  - Case D (`regret_curves_mopen.py`): every number identical, 4 s.
  - Case B (`occam_dial_figure.py`, `e6_nesting_monotonicity.py`): all
    non-ESS fields identical; ESS fields within 2e-14 relative (A1); 13 s
    and 28 s.
  - Case C (`haaf_nested_constraint.py`): every number identical to `paper/case-c-haaf:runs/haaf_nested_constraint/results.json`, 212 s (Pyro chains for PSIS-LOO included).
  - Case E: byte-identical oracle recorded 2026-09-08 (sha256 65c9ff5f /
    c1153549 / 7096cd6e); the package has not changed since except the
    record commit.
- The LaTeX build in the main worktree equals a fresh `build_tex.py` run
  from the branch sources (ten section files byte-identical).
- HANDOFF-cases section 0 constraints in the sections: no withdrawn-cache
  path, `kl_forward` framed appendix-only in every mention, no arrow glyph
  (the one match is `\tau`), no role-noun "X is the Y" hit, no
  "lives/sits" for abstracta, no Mauna material.
- `PredictiveList`, `DecompositionResult.group`, `EvaluationFailure`,
  `log_weight_ess`, `_MetricRegistry`: pinned by `tests/test_fix1_*.py` and
  `tests/test_fix1_review_round.py` (100 tests), all passing at the last
  full run.
- Suite: 1346 passed, 5 skipped, 1 failed (B13) at `9b59d89` on
  2026-09-08, 493 s; `ddf8c9d` differs from it only under `runs/`, so the
  count stands (not rerun today; CPU shared with four other channels).
- T5 grid insensitivity; T1 and T4 characterized (numbers above).

## 5. Recommendations, in priority order

1. **Cast the five ledger decisions** (B1). Author time, hours. Unblocks
   the Case D text, the row-definition sentence, section 2.4's commitment,
   and the poster record.
2. **Integrate** per the B4 plan after merging PR #42: half a day of
   mechanical work plus one suite run; unblocks fix pass 2 and every later
   manuscript edit on `main`.
3. **Commit the headline provenance** (B3): the `toy_elicited` subset of
   `runs/prior_sensitivity/` (7.2 MB) or, if size matters, the stage-a JSON
   plus a sha256 manifest of the three npz caches and the exact stage-a
   command and seeds; then add slow regeneration tests for E7, Case D and
   Case B that compare to the committed JSON with a 1e-12 relative
   tolerance (B6, B12). One day.
4. **Resolve E8B** (B2): cut the placeholder paragraph or build the module;
   cutting is an hour and the section already states the limitation.
5. **D58 addendum** (B5): a dated D58 update naming the band defect, the
   fix commit and the quantified understatement, plus the author's decision
   on a poster erratum; two hours of record work.
6. **Fix pass 2** (A3, A4, A5, B7, plus the case-A checker wiring): one
   day, after integration.
7. **Lock refresh** (B8, B13) with an M2CR record entry: two hours.
8. **Manuscript additions** (B10): one sentence each for the ESS behind the
   headline (978 of 1000 at tau = 1) and behind the appendix metric (2.5 to
   104 at tau <= 1), the surrogate ratio 0.60, and the grid statement; two
   hours including artifact regeneration so the numbers trace to runs/.
9. **Record hygiene** (B9): retitle PR #39, decide Draft status of #40/#41,
   append CHATLOG entries for the August and September sessions; an hour.

## 6. Commands run and their outcomes

- `git merge-tree --write-tree --no-messages` for the fix head against each
  paper branch and for all fifteen paper-branch pairs: conflicts in
  `Notes/DECISIONS.md` only (B4).
- `git show origin/<branch>:<path>` scans of the six branches' scripts for
  calls into changed APIs; `git diff --name-only origin/main origin/<branch>`
  for the file sets; `git log --all -- runs/prior_sensitivity
  runs/viz_unification` (0 commits each).
- `python docs/paper-sie-jmp/build_tex.py --out <scratch>` and `cmp` against
  the untracked build: identical.
- `python -m pytest tests/ --collect-only -q`: 1352 tests, grouped by file
  family (B6).
- Regenerations in `<scratch>/proj_review/fable/{e7,cases}/` with
  `bistar_gp`, `bistar_viz` and `experiments/practice_EvansEtAL` symlinked
  read-only to the fix worktree and `runs/prior_sensitivity`,
  `runs/viz_unification` symlinked read-only to the main worktree; outputs
  under the scratch `runs/`; comparison by `compare.py` (exact numeric
  equality, timestamps ignored).
- Probes `probe_headline_T1_T4_T5.py`, `probe_T1_surrogate.py` (fix package
  path asserted in the log).
- Not run today: the full suite (last run 2026-09-08 at `9b59d89`, cited),
  and any Mauna Loa inference.

Signed: Fable 5.1 (this session).
