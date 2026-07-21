# D19 A7 execution protocol — D56 preparation freeze

**Status:** D56, 2026-07-21. Frozen **before any A7 execution**. This is a docs-first, hermetic preparation milestone; it authorizes no launch and records no benchmark result.

**Authority:** `docs/plan-d19-mauna.md` §1.3 and §7 A7; preregistration v1.2 point 6, v1.5 owed-numbers, v1.6 item 6, v1.8 items 2(d) and 5, v1.9 item 1, and v1.11 items 4 and 6; D25's “user-executed” boundary; D55's vehicle rework; and the author ballot cast 2026-07-21. The A7 run is **USER-EXECUTED on Della**. This document is the frozen mechanical protocol.

## 1. Author ballot, cast 2026-07-21

- AC1 NONE (no local run; (sub,1) is the Della smoke cell).
- AC2 all eight cells.
- AC3 --budget-s 600 uniform; skipped_for_budget / extrapolated_from_stage1 are truthful cell-valid statuses, surfaced explicitly, never described as measured. The budget is an operational ceiling.
- AC4 Model B (one job, one node, cpus-per-task=4, strictly serial).
- AC5 STOP-only (no automatic retry or completion; further invocations need a new explicit author authorization).
- AC6 docs-first D56 with committed submit script + validator.
- AC7 v1.8-item-5 key-inventory audit discharged by D55.
- AC8 scp into an ABSENT local staging dir, dual-source hash cross-check, then local commit.
- AC9 option (ii): --constraint=cascade + the exclude list above + in-job exact ActiveFeatures check "intel,cascade,rh9" before cell 1 + all claims scoped to the frozen 90-node pool.
- AC10 environment frozen (incl. numpy 2.4.2), no modification, drift fails before cell 1.
- AC11 no SLURM mail directives.

The AC9 exclude list is exactly `della-h12n[1-13],della-h12n[17-18],della-h17n1,della-i13n25`.

## 2. Read-only Della reconnaissance

Reconnaissance was performed 2026-07-21 through an author-opened SSH master socket, read-only. The login host was `della9`, with RHEL 9.8 and slurm 25.11.6. The frozen scheduler selection is account `suyoghc`, partition `cpu`, QOS as exposed for that account and partition, and the `cascade` constraint token.

Live `man sbatch` on slurm 25.11.6 established the export rule: variables cannot be combined with `--export=NONE`. The execution SHA therefore travels as the script's single positional argument. `NONE` invokes get-user-env and implicitly loads the user's login environment on the node, making `module` available; `NIL` would not.

The existing clone `/scratch/gpfs/SUYOGHC/bistar_gp_c` was STALE+DIRTY: HEAD `865182a5`, dated 2026-07-03, branch `fix/laplace-zmx`, with four dirty paths. It is preserved untouched. Execution instead uses the collision-guarded detached worktree `/scratch/gpfs/SUYOGHC/bistar_gp_a7_exec`.

The `bistar_gp` conda environment at `/home/sc8918/.conda/envs/bistar_gp` contains python 3.11.14, torch 2.10.0+cu128, gpytorch 1.15.1, pyro 1.9.1, and numpy 2.4.2 under module `anaconda3/2024.6`. The numpy version differs from local 1.26.4. AC10 freezes the Della environment without modification; the local suite has never run under numpy 2.4.2, and any failure aborts through the sanitized path before cell 1. No site-packages installation of `bistar_gp` exists, so `PYTHONPATH` is required and the script verifies that the imported package resides inside the execution worktree.

The cluster uses `ProctrackType=proctrack/cgroup`, `TaskPlugin=task/cgroup,task/affinity`, and `SelectTypeParameters=CR_CORE_MEMORY`. The `cascade` token alone is heterogeneous across 107 nodes: 13 bigmem nodes `della-h12n[1-13]`, optane `della-h17n1`, mixed `della-h12n17`, and Sapphire Rapids `della-h12n18` plus `della-i13n25` are excluded. The frozen homogeneous pool has exactly 90 nodes with exact `ActiveFeatures=intel,cascade,rh9`:

- `della-h17n[2-3]`
- `della-i13n[1-24]`
- `della-r3c1n[1-16]`
- `della-r3c2n[1-16]`
- `della-r3c3n[1-16]`
- `della-r3c4n[1-16]`

The `della-h16n*` nodes are now `amd,genoa,rh9,nvme`; the D3/D8 `della-h16` history attaches to retired hardware. Its margins-only status is unchanged.

## 3. Committed submit script

The launch vehicle is [`experiments/submit_d19_a7_bench.slurm`](../experiments/submit_d19_a7_bench.slurm). Its scheduler memory and time requests are operational ceilings: `16G` ceiling and `02:00:00` ceiling, not predictions.

It fails closed with explicit exit codes:

- 64: execution-directory mismatch; 65: missing or malformed positional execution SHA.
- 66–69: `module` unavailable, module load failure, conda hook failure, or environment activation failure.
- 70–72: HEAD mismatch, unstaged tracked changes, or staged/index changes.
- 73–75: closed-world untracked-state, pristine-evidence-directory, or evidence-entry failure.
- 77–78: pre-existing cell target or exit-zero-without-a-nonempty artifact.
- 80–82: conda-prefix mismatch, Python-resolution mismatch, or version/import-containment drift.
- 83: exact `ActiveFeatures` mismatch.

The script uses one node and one task with four CPUs available to the task. It runs `(sub,1)` first, then `sub` threads 2–4, then `full` threads 1–4. Cells are strictly serial. Every cell receives the uniform operational `--budget-s 600` ceiling. The first nonzero cell exit stops the matrix with no retry or continuation. The script does not set the four thread environment variables; the frozen D55 vehicle owns that pre-import contract.

Gitignored files are invisible to git-based cleanliness checks; the four `sitecustomize.py`, `sitecustomize.pyc`, `usercustomize.py`, and `usercustomize.pyc` hijack names are shell-checked and both Python invocations run with `-B`, while host-level write access to the worktree remains a stated trust assumption.

## 4. Launch procedure

These steps may be executed **only under a later byte-exact launch authorization** naming `<M56>`.

**P0 — GitHub authentication precondition.**

`git -C /scratch/gpfs/SUYOGHC/bistar_gp_c ls-remote origin` must exit zero. If it does not, the authorized fallback is a local `git bundle create`, `scp` of that bundle to Della, and fetch from the bundle file.

**P1 — Retrieve the authorized object.**

Run `git -C /scratch/gpfs/SUYOGHC/bistar_gp_c fetch origin`, or the authorized bundle fetch.

**P2 — Worktree collision guard.**

STOP if `/scratch/gpfs/SUYOGHC/bistar_gp_a7_exec` exists or is registered in `git worktree list --porcelain`. Never remove, reset, clean, or reuse it. Only after both checks are negative:

```text
git -C /scratch/gpfs/SUYOGHC/bistar_gp_c worktree add --detach /scratch/gpfs/SUYOGHC/bistar_gp_a7_exec <M56>
```

**P3 — Detached-head and cleanliness precondition.**

Change to the execution worktree. Require HEAD exactly `<M56>` and `git status --porcelain` completely empty, including untracked paths, before P4.

**P4 — Create the evidence directory.**

Run `mkdir runs/d19_a7_timing` without `-p`; fail closed if it is present.

**P5 — Submit once.**

```text
sbatch --export=NONE experiments/submit_d19_a7_bench.slurm <M56>
```

**P6 — Capture scheduler metadata after termination.**

```text
[ ! -e runs/d19_a7_timing/job_metadata.txt ] || { echo "job_metadata.txt exists; STOP"; exit 1; }
sacct -j <jobid> -P --format=JobID,State,ExitCode,Elapsed,Timelimit,TotalCPU,MaxRSS,NodeList,Submit,Start,End > runs/d19_a7_timing/job_metadata.txt
```

**P6b — Generate the complete Della manifest, excluding itself.**

```text
[ ! -e runs/d19_a7_timing/PROVENANCE.sha256 ] || { echo "PROVENANCE.sha256 exists; STOP"; exit 1; }
(cd runs/d19_a7_timing && ls -A | grep -vx PROVENANCE.sha256 | LC_ALL=C sort \
  | xargs -d '\n' sha256sum > PROVENANCE.sha256)
```

This covers every present entry, including dotfiles. The success set is exactly the eleven files comprising eight JSON artifacts, stdout, stderr, and `job_metadata.txt`. A rerun of either P6 or P6b capture is an author decision: refuse and STOP when its target is present; nothing is ever truncated or overwritten.

**P7 — Transport without clobbering or dropping dotfiles.**

The local staging destination must not exist; refuse otherwise and never merge or overwrite. Use the directory form:

```text
scp -r sc8918@della.princeton.edu:/scratch/gpfs/SUYOGHC/bistar_gp_a7_exec/runs/d19_a7_timing <staging-parent>/d19_a7_timing_incoming
```

Never use a `/*` wildcard because it omits dotfiles. Verify the received file set exactly, then require three-way hash agreement — in-job `sha256sum` lines, `PROVENANCE.sha256`, and an independent local recomputation — before the validator runs or anything is moved or committed. Failure evidence, including stranded temporary files and partial sets, is transported and preserved verbatim, never omitted or deleted.

## 5. Post-run validation

Run only against the absent-before-transport local staging directory:

```text
experiments/d19_a7_validate.py --evidence-dir <staging> --expected-sha <M56>
```

The validator is stdlib-only, read-only, and fail-closed:

- **V0:** require the validator and frozen vehicle bytes to equal their `<M56>` Git blobs, so validation cannot run on unreviewed code.
- **V1:** require the exact twelve-entry set, including the manifest; reject every extra entry and dotfile.
- **V2:** parse all eight UTF-8 JSON artifacts strictly.
- **V3:** pass every artifact through the frozen vehicle's `validate_record` firewall.
- **V4:** compare both directions against the independently transcribed exact key-path inventory.
- **V5:** scan artifacts and logs against both frozen forbidden-token tables, with only the two frozen note values removed from artifact scan text.
- **V6:** require every present seconds/count value to be finite and nonnegative; compare no magnitude.
- **V7:** bind filename scale/thread tokens to the frozen run configuration and operational budget ceiling.
- **V8:** require the successful thread check, all four configured thread fields, and effective torch intra-op threads to agree with the filename; observed, never-set inter-op threads remain schema-checked by V3 only.
- **V9:** bind every artifact to `<M56>`, exact versions, and a common environment fingerprint.
- **V10:** require the short hostname in the frozen 90-node pool, matching `sacct` NodeList, plus `ENV-OK` and no preflight/matrix-stop marker in either log stream.
- **V11:** require eight closed-world report lines whose kind, scale sequence, point counts, and finite nonnegative elapsed values match the order-paired artifacts; also require eight successful cell exits in frozen order, one completion marker, the in-job hash block, and forbidden-clean logs; surface nonempty stderr for author reading.
- **V12:** require the parent scheduler row `COMPLETED`, `0:0`, and within the `02:00:00` scheduler ceiling.
- **V13:** interpret offset-free `sacct` times as `America/New_York`, compare artifact UTC timestamps with ±300 seconds tolerance, and require each artifact elapsed total within scheduler Elapsed; zoneinfo failure is fatal.
- **V14:** require the exact eleven-file `PROVENANCE.sha256`, no self-entry or duplicate, local rehash equality, and three-way JSON-hash agreement.
- **V15:** independently rehash and size-check the two superseded pre-D22 anchors under the repository root.

The final census prints each cell's Hessian and stage-2 status. Truthful `skipped_for_budget` and `extrapolated_from_stage1` statuses are valid and surfaced; neither is described as measured. No timing magnitude is compared, ranked, or projected.

## 6. Failure semantics

AC5 applies uniformly. Submission failure, preflight abort, firewall rejection, timeout, interruption, worktree collision, partial matrix, malformed artifact, and exit-zero-but-failed-validation are all **STOP-and-report** outcomes. There is no retry, completion invocation, or continuation without a new explicit author authorization. Nothing is ever deleted.

## 7. Commit topology and launch identity

The topology is D56 branch → reviewed head `H` (or `H'` after the single bounded correction pass) → optional Notes-only tail → merge `M56`. D56 deliberately does not name its own future merge SHA.

`H'` becomes the reviewed head only after the corrected findings receive focused re-confirmation; the `H..H'` delta is bounded to the confirmed findings and their tests.

Launch authorization requires all of the following: `origin/main` HEAD equals `M56`; `M56`'s second parent is the PR head; the following diff is empty:

```text
git diff H'..M56 -- experiments/ bistar_gp/ tests/ docs/d19-a7-execution-protocol.md
```

The Della worktree HEAD must equal `M56`, enforced by the script, and every artifact `git_sha` must equal `M56`, enforced by the validator.

## 8. Later allowlists and remaining open decision

Evidence commit allowlist B is `runs/d19_a7_timing/{8 JSONs, slurm-<id>.out, slurm-<id>.err, job_metadata.txt, PROVENANCE.sha256}` plus Notes updates. `.gitignore:29` (`slurm-*.out`) ignores the stdout evidence file, so the evidence commit MUST use `git add -f runs/d19_a7_timing/slurm-<id>.out` and MUST verify that `git ls-files runs/d19_a7_timing/` lists exactly the twelve evidence files before committing; this makes a silent stdout drop impossible. Post-run addendum allowlist C is `docs/prereg-addenda-d19.md` v1.22 plus Notes. Numbering is fixed: v1.16 was burned as the M2bR run label, v1.18 is permanently burned, and the latest addendum is v1.21.

All claims are scoped to the frozen `intel,cascade,rh9` 90-node pool. Deletion of the superseded pre-D22 anchors remains a separate OPEN author decision.
