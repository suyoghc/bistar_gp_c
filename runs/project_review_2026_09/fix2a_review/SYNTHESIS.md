# Fix pass 2a review round: synthesis (2026-10-03)

Five independent channels reviewed the uncommitted fix pass 2a (worktree `bistar_gp_c-fix2a`,
branch `fix/pass-2a`, base `69deeda`) against the brief `brief.md` (repository channels also
`brief_repo_addendum.md`). Collation rule as in earlier rounds (HANDOFF-cases section 4):
multi-reporter findings go to the fix queue; single-reporter findings were probe-verified here
with a default of refuted; severity follows reachability (a paper path or a documented call
pattern; injected failures count as latent).

## Channels and verdicts

| Channel | Access | Code verdict | Output |
|---|---|---|---|
| Codex gpt-6-astra, xhigh (`codex exec --yolo`, read-only by instruction) | repository; targeted tests (144 + 9 passed), E7 and Case E replays, mutant probes | REVISE (X01-X09) | `astra_review.md` |
| Fable (Agent subagent; consulted earlier on the D2 tests, disclosed) | repository; targeted tests (283 + 194 passed), E7 and Case E replays, card6 render probe | REVISE (F1-F7) | `fable_review.md` |
| GLM 5.3 (`z-ai/glm-5.3`, OpenRouter, reasoning cap 16000) | package only (`package_only_bundle.md`, about 65k tokens) | APPROVE (G1-G7) | `glm_5_3_review.md`, `glm_raw.json` |
| Kimi K3 (`moonshotai/kimi-k3`, OpenRouter, reasoning cap 16000) | package only | REVISE (K3-1..K3-5) | `kimi_k3_review.md`, `kimi_raw.json` |
| Gemini 3.1 Pro (`gemini-3.1-pro-preview`, Gemini API, thinking HIGH) | package only | APPROVE (GEM-1, GEM-2) | `gemini_review.md`, `gemini_raw.json` |

Adjudicated code verdict: **REVISE**, with targeted folds and no rewrite (every channel answered
the standing question with KEEP or SIMPLIFY IN PLACE; none chose REWRITE). No S1. The paper paths
are unchanged by three independent replays (implementer: E7, Cases A-E; Astra: E7, Case E; Fable:
E7, Case E). Integrity: the three worktrees, every ref, `stash@{0}` and the worktree registrations
were identical before and after the round (`integrity_before.txt` and `integrity_after.txt` in this
directory).

## Findings, collated and verified

Reporters: X = Astra, F = Fable, G = GLM, K = Kimi, M = Gemini. "Verified" names the
implementer's own probe on the 2a tree (package path printed) unless stated.

| # | Finding | Reporters | Adj. | Verified | Disposition |
|---|---|---|---|---|---|
| R1 | The absolute ESS floor (100) warns on every call with fewer than 100 draws, including uniform weights (ESS = draw count): 270 of 270 calls in the 20-predictive smoke run; also per replicate inside the frozen `mcse_strategy` loop when pooled ESS is low | G2, K3-4, M (GEM-2), F3, X (Q6) | S4 (log-only) | smoke-run counts; uniform 20-draw matrix warns | fold: effective floor `min(ess_warn, 0.1 * n_draws)` (keeps E7's six and Case C's two warnings at 1000 draws; uniform weights never warn) |
| R2 | The historical toy_elicited HMC caches (`runs/prior_sensitivity/samples_toy_elicited_hmc_td{7,10}.npz`, pre-D22 sampler; D33: "original invalid caches", superseded numbers) load without refusal | K3-2, X05, F4 | S4 | loader accepts them | fold: register both with a D33 comment |
| R3 | The Case D producer still replaces a raising candidate fit with a flat-mean candidate scored under the real name, without consulting `strict` | K3-3 (S2), F2 (S2), X (Q6) | S3 (reachable by construction; 0 substitutions in the 50-subject archive; must close before the canonical Case D run) | archive scan: 0/50 subjects substituted; source read | fold: strict raises naming subject and candidate; non-strict records `candidate_failures` |
| R4 | A dead row (every candidate fails on one draw) keeps the uniform penalty; under `normalize_per_draw=True` it adds equal support to every candidate and counts as an all-way tie | K3-5, M (GEM-1), F7; X: wait, needs an estimator policy | S3 (latent) | source read | **author decision**: raise (symmetric with a dead column; recommended) or keep and record |
| R5 | Record: `WITHDRAWN_CACHES` has 15 entries, not 16 (report and D70) | G1, X09, F5 | S4 | `len(WITHDRAWN_CACHES) == 15` | fold (record) |
| R6 | Record: "these pass once the new file is committed" overstates the evidence for the four realroot launch tests (only the import failure was reproduced and repaired) | X09 | S4 | the reproduction shows the import only | fold (record wording) |
| R7 | A-5 changes the frozen D58 driver's card6 render: rebuilt results (positional contract, `full=None`, `n_draws=0`) lose the panel (a) traces, gain the band label "mean ± 2 sd", and label conditional-mean traces "function draws"; card6 re-rendered from the committed arrays no longer matches its pin | F1 | S2 (a reachable regression on a presented-figure path) | card6 via the frozen driver's own rebuild and render: base `69deeda` reproduces the pinned `0fe67b15…` byte for byte, 2a gives `ada7e7ae…` (panel (a) 1 line against 16; three "function draws" labels). Cards 7-8 raise `KeyError` (group posteriors) at base and at 2a alike, a fix-pass-1 effect owned by the 2c D58 correction | fold: results without per-draw provenance (`full is None`, `n_draws == 0`) render exactly as before; verify card6 = pin |
| R8 | The A-5 pin checks marginal variances only; a diagonal-only sampler passes | X07 | S3 (test adequacy) | source read of the test | fold: compare the empirical correlation matrix with the full posterior |
| R9 | The MAP-path joint draws use a fixed 1e-10 jitter and raise `LinAlgError` on a numerically semidefinite posterior | X08 | S3 (latent) | high-scale toy MAP posterior: minimum eigenvalue -4.9e-8, plot raises | fold: eigen-decomposition, clip roundoff-sized negative eigenvalues, raise when materially indefinite |
| R10 | `robust_rank` stores average ranks in an integer array for integer input, truncating 1.5 to 1 | X01 | S3 (latent; package G matrices are float) | `[[0,0,1]]` ranks [1, 1, 3] against [1.5, 1.5, 3] for floats | fold: float rank storage |
| R11 | `compute_induced_prior` treats only `LinAlgError`/`ValueError` as metric failures; a metric raising `FloatingPointError` (or `RuntimeError`) escapes both modes, so the non-strict contract does not hold | X02 | S3 (latent) | `FloatingPointError` escapes with strict True and False | fold: the exception set of `compute_G_at_params` |
| R12 | Non-strict Case D producer: an extraction failure after a successful sampler run discards the draws and diagnostics | X03 | S3 | record keys `['failed']`, no saved draws | fold: record sampling output before extraction |
| R13 | Non-strict Case D producer: a raising `extract_map_predictives` bypasses the recorder; the subject disappears | X04 | S3 | 0 subjects returned | fold: route MAP extraction through the recorder |
| R14 | The no-kernel-site message (noise-only dictionary) does not name the missing kernel sites | X06 | S4 | message lacks every kernel site | fold: append the missing sites (keep the pinned wording) |
| R15 | The deepcopy/pickle claim for the two result subclasses is unpinned | G3 | S4 | both survive protocols 2 and highest | fold: pin it |
| R16 | `missing_sample_sites` re-implements the alias table of `model.py` | F6 | S4 (latent) | source read | defer: `model.py` is outside the editable set; record for 2b or an exception |
| R17 | A-7 ranks exact ties, while SYNTHESIS A-7 said "under a tolerance" | K3-1 | S4 | — | not adopted: exact ties are the package rule (`hard_win_statistics`); four channels accept the disclosed deviation 7 |
| R18 | Missing pins: `decompose_model_mcmc` ragged check; the strict=False missing-site warning; a generator ladder; 2a-10 strict failure at the BMS* stage; the rebuilt-result render path; noise averaging over retained draws only after a dropped draw | F (Q4), X, K | S4 | — | fold: add to the existing per-item tests |
| R19 | `fit_hmc` may lack `return_diagnostics` | G4 | — | REFUTED: the parameter exists (signature) and the smoke run used it | none |
| R20 | Stage B of `prior_sensitivity_study` now refuses withdrawn caches | G5 | — | intended and disclosed | none |
| R21 | `plot_full_prediction` treats a one-draw draw-path result like the MAP path | G6 | — | correct behaviour (joint draws from that draw's conditional posterior) | none |
| R22 | Smoke-run the A-5 consumers (`toy_example.py`, `toy_example_noMCMC.py`, `mauna_loa.py`) | K | — | `mauna_loa.py` is Mauna inference (excluded) | optional for the toy scripts |

## Recommended fold pass (2a-b)

R1, R2, R3, R5, R6, R7, R8, R9, R10, R11, R12, R13, R14, R15, R18, and R4 if the author chooses
the raise. Then: the new and affected tests, the full suite, the Case E oracle, the Case A-D
regenerations, and the card6 render probe (must equal the pin `0fe67b15…`), with the report and
D70 updated. Deferred: R16 (needs an editable-set line for `model.py`). Not adopted: R17.

## Fold pass 2a-b, applied (2026-10-03)

The author answered "check with fable" on the fold list and on R4. Fable (continuing its review
context, read-only) endorsed every fold with one change, R3 non-strict drops a failing candidate
and records it instead of scoring the flat substitute, and recommended the raise for R4 (a dead
row is a complete failure of one draw; keeping it would change the draw population silently,
SYNTHESIS section 9 amendment 3; no paper path or frozen caller can reach it). Applied as
endorsed, plus Fable's simplification of 2a-3 (one shared preflight for the two draw routes).
Verification after the folds (details in `../fix2a_report.md`): the 12 contract tests pass and
8 of them fail on the pre-fold tree, one per fold (the other four protect behaviour the pre-fold
code already met); a diagonal-only sampler mutant fails R8; full suite 1354 passed, 5 failed
(lock drift; the four realroot tests that need `errors.py` tracked), 5 skipped, 372 s; Case E
oracle byte-identical; Cases A-D regenerate exactly as before the folds (B differs from its
committed artifact only in the known ESS fields); card6 re-renders to its pin `0fe67b15…`; the
Case D smoke run is unchanged apart from the new empty `candidate_failures` field, and its ESS
warnings fall from 270 to 67, all at single-draw concentrations.
