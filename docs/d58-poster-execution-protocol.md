# D58 — poster-grade Mauna fit: execution and provenance protocol

Status: frozen at the D58-PREP review head. Governs the single poster-grade
Mauna Loa fit (D58-RUN), its evidence handling, and the poster hand-off
(D58-POST). Companion code: `experiments/poster_d58_mauna.py` (driver),
`experiments/submit_d58_poster_fit.slurm` (Slurm), guarded by
`tests/test_poster_d58_driver.py`.

## 1. Scope and firewall

Everything produced under D58 is a poster-grade presentation artifact for the
CogSci poster. It is explicitly non-paper-grade. No D58 output may feed any
D19 gate, dossier, arm, strategy, BMS\* computation, or selection; the
preregistered study (docs/plan-d19-mauna.md, prereg v1.0 plus addenda through
v1.23) reads only its own namespaces and never `runs/poster_d58/`. The fit is
not a Stage-B pilot; its diagnostics serve display acceptance only (§5). A
disclosure line for the eventual paper is queued in the D58 DECISIONS entry:
one poster-grade fit under the baseline prior was produced before the study's
pilots and fed no gate, dossier, or selection.

The pre-freeze legacy Mauna PNGs regenerated 2026-07-07/08 under
`runs/figures_regen/` display the sealed holdout window and holdout scores
exist in their logs; they are historical artifacts and are NOT poster-usable.
D58 supersedes them for poster purposes.

## 2. Authority lineage

- D57 ballot B4 renumbered the poster milestone to D58 (2026-07-23).
- Author dispositions (2026-07-23): **B1** fresh seeded E1-backed NUTS poster
  fit executed on Della, poster-grade and non-paper-grade; **B2** crop
  strictly at the training boundary; **B3** the optional BMS\* poster card is
  dropped, with no legacy BMS\* reuse and no fresh BMS\* before the study's
  ordering gates; **B4** a main-repo D58 preparation branch carries reviewed
  code, protocol, tests, and Notes, with run evidence a separate post-run
  act; **B5** the driver is under `experiments/`.
- Author ballot (2026-07-23): **P1(a)** fit specification (§3); **P2(a)**
  data-only on Della, figures rendered locally in D58-POST; **P3(a)** ONE
  fresh Codex gpt-5.6-sol xHigh exact-head read-only review for PREP.
- D58-PREP authorization CAST 2026-07-23 (recorded in the D58 DECISIONS
  entry). D58-RUN and each D58-POST act require their own authorizations; the
  RUN template is §7.3.

## 3. Frozen fit specification (P1a) and cost anchors

One fit, full training scale, executed once on Della:

| item | frozen value |
|---|---|
| data | `load_mauna_loa_training(normalize=True, test_years=5.0)`; N = 461 training months only |
| model | `build_mauna_loa_kernels` + `build_likelihood` + `build_model`; A10 period frozen at exactly 1.0 (asserted after build and after the fit) |
| sampler | committed `fit_hmc` (E1-backed NUTS, D27), `return_diagnostics=True` |
| seed | 0 |
| warmup / retained draws | 200 / 200 (single chain, the committed default) |
| max tree depth | 7 (the td7 efficiency control; disclosed, never convergence evidence) |
| target accept | 0.8 (committed default, echoed into provenance) |
| init | `init_to_map=True` (committed default, echoed) |
| prediction grid | 500 points, `linspace(min(x_train), max(x_train))` — training span only |
| decomposition | `decompose_model_hmc` with `n_posterior_samples = 200` = ALL retained draws |
| threads | v1.23 §6 pin: the driver sets the four environment variables and torch intra-op to 3 pre-import; `cpus-per-task=3`; torch inter-op observed and recorded, never set |
| resources | one node in the frozen `intel,cascade,rh9` pool, `--mem=8G`, `--time=02:00:00` (operational ceilings, not predictions) |
| output | `runs/poster_d58/fit_full461_seed0/` (deterministic name; no-clobber) |

Cost anchor (DERIVED from the v1.23 recorded pin-3 units; planning arithmetic,
not a gate): the full-scale gradient median is `0.0282818500418216 s`, so the
td7-saturated bound is `(200 + 200) x 127 x 0.0282818500418216 = 1437 s = 23.9
min` raw and `35.9 min` under the frozen x1.5 engineering-overhead convention,
leaving `7200 / 2155 = 3.3x` ceiling headroom on the anchored portion. The
decomposition stage has NO frozen anchor (v1.23 measures no such operation);
its expectation is minutes-class and the 2 h ceiling is the operational bound.
Memory anchor: the A7 batch step recorded `MaxRSS=828880K` at full scale; 8G
is the ceiling.

Determinism rule: `decompose_model_hmc` subsamples draws with an unseeded RNG;
with `n_posterior_samples` equal to the retained draw count the selection is
the full set and therefore RNG-independent. The equality is frozen here and
wired into the driver (`n_posterior_samples = n_samples`).

## 4. Artifact census and provenance

The fit writes exactly six artifacts into the run directory, in recovery
order (a wall-clock kill preserves everything already written). Every writer
— JSON, manifest, and both NPZ archives — uses the same atomic discipline
(same-directory temporary, flush + fsync, `os.replace`), so no partial file
can ever occupy a final name:

1. `fit_config.json` — pre-fit echo: design label, git SHA (must equal the
   RUN anchor), host, Slurm ids, seed/warmup/draws/depth/target-accept/init,
   grid size, thread contract (four variables, intra-op, observed inter-op),
   the five environment version pins, and the loader's split METADATA
   (counts, `cutoff_rule`, `test_years`, source, canonical sha256, and the
   training-span normalization scalars `y_mean`/`y_std`/`x_offset`).
2. `samples.npz` — the sampled sites, site name to `(n,)` array.
3. `diagnostics.json` — the `SamplerDiagnostics` record verbatim
   (`dataclasses.asdict`), plus DERIVED convenience scalars
   (`divergence_count_total`, `tree_depth_saturation_threshold = 2^7 - 1 =
   127`, `tree_depth_saturated_draws`) and per-site finiteness flags.
4. `decomposition.npz` — `x_pred` (the training-span grid), `x_train`,
   `y_train`, `full_mean`, `full_std`, `noise_var`, `component_names`, and
   per-component mean/std/samples.
5. `provenance.json` — the consolidated record: everything in
   `fit_config.json` plus finish time, fit and decomposition elapsed seconds,
   `decomposition_n_success` versus requested, global finiteness flags,
   diagnostic summary scalars, and the artifact list.
6. `PROVENANCE.sha256` — `shasum -c` compatible manifest over artifacts 1-5,
   written last.

No test-valued field exists anywhere in the census: the process obtains data
exclusively through the training-only loader, so holdout values are
mechanically unreachable (plan §6.6). Split counts and the cutoff rule
(`max(x) - test_years`) appear as permitted metadata only. Naming note: the
package dataclass's first field carries a legacy name for prediction
locations; in every D58 artifact those locations are the driver-supplied
training-span grid, persisted as `x_pred`. The driver and Slurm sources are
guard-tested to contain no holdout-array token and no full-loader call.

Figures are NOT part of the fit census. Render mode (local, D58-POST)
verifies the census against `PROVENANCE.sha256` under a closed-world rule
(exactly the six artifacts; a prior render's `figures/` directory is the one
permitted extra; duplicate or miscounted manifest lines fail closed),
validates the saved grid semantically (finite, nondecreasing, endpoints
exactly equal to the training span — `validate_saved_grid`), rebuilds the
decomposition result from arrays, renders the four poster panels into
`figures/` (`card6_mauna_decomposition.png`,
`card7_three_interpretations.png`, `card8_debiased_ppm.png`,
`card8_removed_bias.png`), and writes `figures/FIGURES.sha256` over them —
the figure-provenance manifest is created only once figures exist. Render
performs no data load and no inference; it loads the tracked plotting module
`experiments/bistar_debias_mauna_loa.py` for its figure functions, which
binds (but render never calls) the full loader. Boundary rendering is
ENFORCED, not assumed: `enforce_training_boundary` sets every axes' x-limits
to exactly the training span in that figure's own units (normalized time for
cards 6-7; calendar years via `x_offset` for the card-8 strips), eliminating
matplotlib's default margins, and strips the tracked plot functions'
boundary annotations ("forecast" and "train" markers), so no axis range,
band, or label extends past or points beyond the final training coordinate.

## 5. Acceptance checks A1-A7 (frozen, non-adaptive, display gate only)

Applied read-only at D58-RUN step P7, after transport. They decide whether
the figures may be displayed on the poster; they never trigger tuning,
re-running, or resubmission (the single submission is spent regardless).
Any failure, and any diagnostic situation these checks cannot classify, is
returned to the author as an unresolved judgment with the evidence preserved.

- **A1 scheduler truth**: decided from the frozen P4 capture
  `runs/poster_d58/job_metadata.txt` (plus the Slurm log): parent row
  `State=COMPLETED`, `ExitCode 0:0`, node inside the frozen pool.
- **A2 closed-world census**: exactly the six §4 artifacts present in the
  transported fit directory; `shasum -c PROVENANCE.sha256` passes; nothing
  extra inside the fit directory (figures do not exist at P7).
- **A3 provenance completeness**: every §4 field present;
  `git_sha` equals the RUN anchor; thread contract echoed at 3/3/3 with
  inter-op recorded; the five version pins match the frozen environment.
- **A4 finiteness**: all sampled-site and decomposition arrays finite, both
  as driver-recorded flags and as a local recomputation on the transported
  arrays.
- **A5 sampler completion**: retained draws and warmup equal the P1a
  specification (200/200), single chain.
- **A6 seal integrity**: `n_train = 461` and the `cutoff_rule` string
  present; no test-valued field anywhere; the source-level guards hold at
  the RUN anchor.
- **A7 truthful diagnostics** (RUN-time half): the verbatim
  `SamplerDiagnostics` payload is present with the DERIVED divergence and
  tree-depth-saturation counts, and `decomposition_n_success` is reported
  with any shortfall returned to the author. The caption obligation — any
  displayed figure reports those numbers honestly, with td7 labeled an
  efficiency control per the standing disclosure — attaches to D58-POST,
  when figures exist; it is not decidable at P7 and is recorded there as an
  obligation, not a check.

## 6. D58-RUN steps and STOP conditions

Available only after the PREP PR is merged (true merge; anchor **M58**) with
`origin/main == M58`, under a fresh byte-exact authorization naming M58
(template §7.3). Author-executed, one command at a time:

- **P0** — topology: fetch; require `origin/main == M58`; clean tracked tree.
- **P1** — fresh detached worktree `/scratch/gpfs/SUYOGHC/bistar_gp_d58` at
  M58; `mkdir -p runs/poster_d58` inside it. The stale
  `/scratch/gpfs/SUYOGHC/bistar_gp_c` checkout and the spent A7 worktrees
  stay untouched.
- **P2** — read-only environment preflight from the worktree:
  `PYTHONPATH=$PWD python -B -c "import bistar_gp"`.
- **P3** — **ONE** `sbatch --export=NONE
  experiments/submit_d58_poster_fit.slurm <M58-sha40>`, where `<M58-sha40>`
  is the LITERAL 40-hex merge-anchor SHA written out in the cast
  authorization (the script rejects anything else at exit 65 AFTER the
  submission is accepted, which would spend it — never pass a symbolic
  name). The submission is SPENT on execution; no automatic retry, no
  post-hoc tuning, on any outcome.
- **P4** — single-shot scheduler capture, frozen verbatim (the A7 recovery
  lesson: the original P6 redirect was CWD-relative and missed; run this
  from the worktree root and check the target first):
  `[ ! -e runs/poster_d58/job_metadata.txt ] && sacct -j <jobid> -P
  --format=JobID,State,ExitCode,Elapsed,Timelimit,TotalCPU,MaxRSS,NodeList,Submit,Start,End
  > runs/poster_d58/job_metadata.txt` (parent and batch rows arrive
  together; no-clobber; one shot).
- **P5** — dotfile-safe transport of `runs/poster_d58/` (the fit directory,
  `slurm-<jobid>.out/.err`, and `job_metadata.txt`) to the Mac at
  `runs/poster_d58_incoming/`, with sha256 recorded on Della at capture
  time.
- **P6** — hash gate: `shasum -c PROVENANCE.sha256` inside the transported
  fit directory plus comparison of the Della-side capture hashes; any
  disagreement is a STOP.
- **P7** — the frozen A1-A7 checks, read-only. Then **STOP**.

STOP conditions (each preserves all evidence and returns to the author, with
no resubmission): sbatch rejection; job failure at any preflight code (64-83)
or in the fit (`FIT-STOP`); wall-clock kill (partial census is evidence — the
recovery write order preserves whatever completed); transport or hash-gate
disagreement; any A-check failure. Prohibited throughout: BMS\*, holdout
access, paper gates, arm or strategy selection, a second submission, edits to
any frozen surface, and any `poster/` change.

## 7. Allowlists and the RUN authorization template

### 7.1 D58-PREP changed-file allowlist (exactly seven)

1. `experiments/poster_d58_mauna.py` (NEW)
2. `experiments/submit_d58_poster_fit.slurm` (NEW)
3. `tests/test_poster_d58_driver.py` (NEW)
4. `docs/d58-poster-execution-protocol.md` (NEW, this file)
5. `Notes/DECISIONS.md` (APPEND: D58)
6. `Notes/SCRATCHPAD.md` (UPDATE: D58 section)
7. `Notes/CHATLOG.md` (APPEND)

No figure or figure-hash manifest exists at PREP; no `poster/` or
`CogSci Poster/` change; no edit to any existing tracked code, prereg or
freeze document, or `runs/` content.

### 7.2 D58-POST allowlists (each act separately authorized)

- **Evidence commit**: `runs/poster_d58/**` (the six-artifact census, the
  Slurm out/err, the `sacct` capture, and, after render, `figures/*.png`
  plus `figures/FIGURES.sha256`; PNG and Slurm-log paths are gitignored and
  enter by explicit force-add) plus Notes updates. Nothing else.
- **Poster hand-off**: copying approved PNGs into the separate user-owned
  `poster/` repository happens on a NEW branch inside that repository, under
  its own authorization, after the evidence commit. `poster/` and every
  currently untracked poster material stay untouched until then.

### 7.3 D58-RUN authorization template (castable only once M58 exists)

> **D58-RUN AUTHORIZATION.** Preconditions: PREP PR #\<N\> merged as a true
> merge producing **M58 = `<sha40>`** (the cast MUST write out the literal
> 40-hex SHA here; every later reference below means that literal);
> `origin/main == M58` verified at cast time;
> `docs/d58-poster-execution-protocol.md` at M58 governs. Authorize, as one
> author-executed sequence: P0 topology verification; P1 fresh detached
> worktree `/scratch/gpfs/SUYOGHC/bistar_gp_d58` at M58 with
> `mkdir -p runs/poster_d58` (existing Della checkouts and spent A7 worktrees
> untouched); P2 read-only environment preflight; P3 **ONE**
> `sbatch --export=NONE experiments/submit_d58_poster_fit.slurm <sha40>`
> with the literal 40-hex M58 as the argument (a symbolic name fails the
> in-job guard at exit 65 and spends the submission), the single submission
> SPENT on execution with no automatic retry and no post-hoc tuning on any
> outcome; P4 the frozen single-shot `sacct` capture to
> `runs/poster_d58/job_metadata.txt` (protocol §6 P4, verbatim); P5
> dotfile-safe transport (fit directory + Slurm logs + `job_metadata.txt`)
> to `runs/poster_d58_incoming/` with Della-side hashes; P6 the hash gate;
> P7 the frozen A1-A7 acceptance checks, read-only; then STOP. Evidence
> preserved on every outcome. Not authorized: BMS\*, holdout access, paper
> gates, arm or strategy selection, a second submission, the evidence
> commit, or any `poster/` change — the last two are separate D58-POST
> authorizations.

## 8. Disclosures and notes

- td7 is an efficiency control (D8), never convergence evidence; every
  displayed caption honors this and reports divergences and saturation
  truthfully (A7).
- Single chain, one seed: no replicate variance exists; poster captions do
  not claim otherwise.
- The A10 period freeze makes this fit's seasonal period exactly 1.0; the
  pre-D19 plug-in-period disclosure applies to the superseded legacy figures,
  not to this fit.
- Thread-contract division of responsibility: the driver owns the
  four-variable pre-import contract and the torch intra-op pin; the Slurm
  script owns `cpus-per-task=3` and exports no thread variable (the committed
  D55/A7 pattern). This refines the D58 plan message's wording, disclosed
  here before review.
- The poster quotes split metadata (461/60, the cutoff rule) as text only; no
  holdout value, coordinate, score, or forecast band appears anywhere on the
  poster, and the legacy log line holding a pre-freeze holdout score is not
  quotable.
- Render input path: the fit directory is validated in place wherever the
  transport landed it (the D58-POST flow uses
  `runs/poster_d58_incoming/...`); the driver's namespace guard applies to
  fit-mode OUTPUT directories only.
- Local hermetic tests are the only PREP execution; the driver's fit mode
  runs exactly once, on Della, under the RUN authorization.
