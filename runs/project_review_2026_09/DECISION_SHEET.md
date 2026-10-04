# Author decision sheet (2026-09-26)

One tick per line. Options are the ones already recorded (ledger revision 3
`runs/code_review_2026_09/ledger_draft.md`, D66/D67 closing ledgers, SYNTHESIS
section 10); the default is the one every checking channel recommended.
Evidence pointers are to the committed record on `fix/code-review-2026-09`.
Cast by writing the option letter in the last column; nothing below moves
until the line it gates is cast.

**Cast 2026-10-03.** The author confirmed the implementer's recommended cast for every line
below, after read-only consultations of Codex gpt-6-astra (xhigh) and Fable on one brief
(`sheet_consult/`). Since this sheet was written, PR #42 (`8c6e6b2`) and fix pass 2a (PR #43,
`622c566`) were merged into `main`, so the evidence pointers below now resolve on `main`;
where B9 and the closing paragraph assume the pre-merge state, the cast column and D69's
2026-10-03 update govern.

## A. Manuscript-gating (cast first)

| # | Decision | Options on record | Default | Evidence | Your call |
|---|---|---|---|---|---|
| A1 | Case D: what happens to the stored-comparison tables of section 06 (winner labels, pw_nll draw wins, cohort mean G), which rest on the pre-D6 archive and change under the corrected sampler | (i) withdraw them; (ii) relabel as prior-conditioned; (iii) regenerate on the corrected sampler; (iv) relabel now, regenerate before submission; (v) suspend now, regenerate the comparison layer as the endpoint | **(v)**, endpoint (iii); if the schedule cannot hold, (i) rather than (ii) | SYNTHESIS A-20/B-0; `opus_review.md` C1; two matching regenerations (22/28 became 5/45 under pw_hellinger) | **(v)**, endpoint (iii); (i) if the schedule cannot hold |
| A1a | Case D regeneration scope: add `pw_kl_vcal` (the W1 primary metric) to the regenerated run, or reproduce only the legacy metrics | add / legacy only | **add**, decided before the run, reported either way | ledger Item 3(iii): "a separate scope choice"; Astra amendment 4 | **add** |
| A1b | Case D regeneration protocol: seeds and diagnostics | one seed (as the probes) / two seeds with sampler diagnostics per subject and configuration | **two seeds with diagnostics** | Opus plan check 1: `run.py` passes no seed, one chain | **two seeds with diagnostics** (strict) |
| A1c | D6 addendum scope: the other two February archives `results_diag/` and `results_hierarchical/` | withdraw alongside `results_hmc` / rule them out of scope | **withdraw alongside** unless a use is found (none cited by section 06) | both committed 2026-02-16, pre-D6; ledger Item 3 asked for this ruling | **withdraw alongside** |
| A2 | psi row and the G-bar symbol: which definition governs (the notation's sampled function versus the implemented hyperparameter-conditional predictive; one symbol currently names both the per-pattern mean G and the plug-in on the moment-matched pattern) | (A) keep the implemented row, amend the notation; (B) implement the notation's row; (C) (A) plus a committed sensitivity artifact | **(C)**, with `00-notation.md` committed unchanged first, two symbols for the two G-bar estimands, and each case's candidate-fitting protocol stated | ledger Item 4; SYNTHESIS B-1, A-21, A-26; D66 SC1 (same decision) | **(C)**, with `00-notation.md` committed unchanged first |
| A2a | D66 SC2: sign off the pooled-limit separation (the tau-to-zero hard-best-match limit belongs to per-draw conventions, not to the pooled display) | sign off / reopen | **sign off** | `runs/synthesis_sections/reviews/VERDICTS.md` SC2; E7 artifact | **sign off** |
| A3 | Section 2.4's reporting commitment: every soft-transfer table reports tau-free draw-win credit, attainment and weight ESS | (a) meet it (extend the E7 artifact and the Case C line, amend sections 3.4 and 5); (b) state a limitation instead | **(a)** with the exact-tie rule (equal split, never candidate order) | ledger Item 5; SYNTHESIS A-13, B-8 (ESS 978 of 1000 at tau = 1; appendix metric 2.5 to 104) | **(a)**, exact ties split equally |
| A4 | Remark 1's scope: the headline path scores instances fitted once to the observed data, and a committed row favors the restriction | restrict Remark 1, intro (ii) and section 8 to per-draw protocols and state the fixed-instance protocol / recompute the headline with per-draw projection | **restrict and state**; a per-draw headline is a separate scientific choice | SYNTHESIS A-21; `codex_astra_review.md` P01 | **restrict and state** |
| A5 | Evaluation grid: state the choice (60 points on [x_min - 1, x_max + 1]) and report placement sensitivity (0.412 to 0.445; the appendix attribution flips) | state and report / change the grid | **state and report**; do not change the grid to preserve a result | SYNTHESIS A-22 | **state and report** |
| A6 | The absolute-inadequacy argument (pooled "retains absolute divergence magnitudes"): normalized pooled probabilities are offset-invariant | rewrite to "preserves between-draw differences in total support; absolute inadequacy is read from raw divergences" / keep | **rewrite** (sections 03, 02, 08) | SYNTHESIS B-6 (a) | **rewrite** |
| A7 | Appendix-only material: the manuscript has no results appendix | create a results appendix and move the `kl_forward` paragraph out of section 3.4 / drop the material | **create and move** | SYNTHESIS B-6 (b) and (f) | **create and move** |
| A8 | E8B placeholder in section 06 | cut / build | **cut** (an hour; the section already states the limitation) | SYNTHESIS B-4 | **cut** |
| A9 | Case C's provisional "sharpest published criticism" framing (Kellen and Klauer 2020 unread) | read and confirm / reword to a non-superlative | **reword** unless the paper is read before integration | `05-case-C.md:8-10`; `kb/Raw/WANTED.md:131` | **reword** |

## B. Record and process

| # | Decision | Options on record | Default | Evidence | Your call |
|---|---|---|---|---|---|
| B1 | `pypdf`: it is installed in your user site (`~/.local/lib/python3.13/site-packages`, its only package) and fails the M2CR lock test | uninstall it there and keep the historical lock (move PDF tooling to a venv) / re-lock under a recorded policy change | **uninstall, keep the lock**; your act, before any suite is used as a gate | ledger "Other decisions recorded"; Opus plan check 5 | **uninstall both** drifted packages (`pypdf`, `imageio-ffmpeg`) and **keep the lock**; PDF tooling (`graphifyy`'s `pdf` extra) moves to its own environment; the author's act |
| B2 | `soft_transfer(metric_name=)`: the work order said required; `mcse_strategy_estimate` (M2c contract) has no metric identity | (i) keep optional, pass the name at the one caller that has it; (ii) thread an optional recorded keyword through `mcse_strategy_estimate` | **(ii)** (GLM); (i) is the cheaper record-only choice | `fix1_synthesis.md` pass-2 note; SYNTHESIS A-9 | **(i)**, not the default: (ii) would edit the frozen `bistar_gp/mcse_strategy.py`; pass the name at the one caller in 2b |
| B3 | D67 F1: commit `runs/prior_sensitivity/stage_a_toy_elicited.json` (and the three `toy_elicited` prior-IS pools, 7.2 MB, or their hashes plus the regeneration recipe) | commit the JSON and the pools / commit the JSON and a hash manifest with the recipe | **JSON plus manifest and recipe** (all three pools regenerate bit-identically, 71 to 74 s each) | SYNTHESIS B-3; D67 closing ledger | **JSON plus manifest and recipe** |
| B4 | D67 F3: the floor sentence restricted to the measured N = 20 statement; optional N-sweep (20/50/200) | sign off the restriction / commission the sweep | **sign off**; sweep not required | D67 closing ledger | **sign off** |
| B5 | D67 F2: the enrichment option (coverages 0.821 and 1.000, driver-verified) | include / leave out | **leave out** (cut line) | D67 closing ledger | **leave out** |
| B6 | Ratify the substitute-implementer and driver-verification deviations of the synthesis and Case E rounds (Codex was usage-locked) | ratify / commission a Codex re-review | **ratify**; this round's Codex review of the same material stands as the later independent check | D66, D67 closing ledgers | **ratify** |
| B7 | Uncommitted-local-material policy: `runs/viz_unification/`, `experiments/mechanism_figure_poster.py`, `kb/Wiki` citations | commit the cited items / cite only committed material (recompute the 0.992 arm from the Case B script; commit the mechanism script; drop kb/Wiki as provenance) | **cite only committed material** | SYNTHESIS B-3; D66 open item | **cite only committed material** |
| B8 | PR statuses now | #38 to Draft; #40 and #41 stay Draft until A2/B3-B6 close; retitle #39 | **as listed** | ledger "Pull-request statuses"; SYNTHESIS B-9 | **as listed**; the six paper PRs retarget to the integration branch once it exists |
| B9 | Integration authorization: one integration branch from PR #42 (true merge), the D60-D68 union with per-block hash reconciliation, fix pass 2a on it, then A, C, 2b, B, D (after A1), E, synthesis, true merges only, final suite in a clone | authorize / hold | **authorize** once A1-A3 are cast | SYNTHESIS section 10 | **authorize**, cutting the integration branch from `main` at `84e9881` (PR #42 and 2a are merged) |
| B10 | Two-week cut line: E8B, enrichment, broad refactoring (A-18), unsupported reach and mode claims go first | accept / amend the list | **accept** | Astra 10, Opus 10 | **accept**; of D70's leftovers, R16, the `score_averaged_gp` NaN check and the unguarded cache reads go to 2b, the rest behind the line |

## C. Poster record (separate from the manuscript)

| # | Decision | Options on record | Default | Evidence | Your call |
|---|---|---|---|---|---|
| C1 | D58 poster bands (cards 6 to 8) understated 5 to 14 times; which image set was presented, and what correction | (A) addendum only; (B) corrected pinned set plus addendum, recomputed from the committed `samples.npz` with mixture quantiles, as a separately authorized act; (C) (B) plus a modeling change | **(B)**; start the presented-asset inventory now | ledger Items 1-2; SYNTHESIS B-5; `CogSci Poster/QA_PREP.md` Q24 | **(B)**; the inventory starts now |
| C2 | Public erratum for the presented poster | yes / no / after the inventory | **after the inventory** | Opus plan check 8 | **after the inventory** |

## What each cast unlocks

- A1 to A1c: the D64 suspension addendum and the D6 addendum on
  `paper/case-d-mopen`; PR #38 to Draft; the hardened producer and the
  canonical run; the rewrite of section 06 and the section 08 sentence.
- A2 to A7: the notation amendment, the E7 extension, the manuscript
  amendments of SYNTHESIS B-6 and B-8; PR #39 and #37 reopen for their
  bounded amendments.
- B1: a green suite baseline (expected 1347 passed, 5 skipped).
- B2: fix pass 2a's last package item.
- B3 to B7: PR #40 and #41 leave Draft.
- B9: everything downstream of the union.

## What happens the moment the sheet is cast

Within the day: the two addenda committed on the case D branch; the
checksummed archive of the untracked apparatus and local inputs;
`00-notation.md` committed unchanged; PR statuses set; the integration branch
cut from PR #42 with the union; fix pass 2a started. The canonical Case D run
follows the hardened producer, from a commit containing #42 and 2a.
