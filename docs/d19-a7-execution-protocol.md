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

STOP if `/scratch/gpfs/SUYOGHC/bistar_gp_a7_exec_03` exists or is registered in `git worktree list --porcelain`. The attempt-1 worktree `/scratch/gpfs/SUYOGHC/bistar_gp_a7_exec` and the attempt-2 worktree `/scratch/gpfs/SUYOGHC/bistar_gp_a7_exec_02` are both expected to remain present and registered from the spent attempts 1 and 2; neither is a collision for attempt 3. Never remove, reset, clean, or reuse any of the three worktrees. Only after both attempt-3 checks are negative:

```text
git -C /scratch/gpfs/SUYOGHC/bistar_gp_c worktree add --detach /scratch/gpfs/SUYOGHC/bistar_gp_a7_exec_03 <M56>
```

**P3 — Detached-head and cleanliness precondition.**

Change to the execution worktree `/scratch/gpfs/SUYOGHC/bistar_gp_a7_exec_03`. Require HEAD exactly `<M56>` and `git status --porcelain` completely empty, including untracked paths, before P4.

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
scp -r sc8918@della.princeton.edu:/scratch/gpfs/SUYOGHC/bistar_gp_a7_exec_03/runs/d19_a7_timing <staging-parent>/d19_a7_timing_incoming
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

### §7 amendment (D56a, 2026-07-21): launch-closure rule repaired

The original launch-closure rule quoted below is **SUPERSEDED**:

```text
git diff H'..M56 -- experiments/ bistar_gp/ tests/ docs/d19-a7-execution-protocol.md
```

It became permanently non-empty when the separately authorized test-only commit `b50350e` landed after `H'`. That commit changed only `tests/test_slurm_argparse.py`: the standing guard learned POSIX backslash-continued logical shell lines after the D56 submit script's continuations crashed its collection. The execution-relevant surface stayed byte-identical to `H'`. A launch gate that can never pass protects nothing; the gate is repaired here in the committed record, not overridden in chat.

**Definitions.** `H'` = `4c9b79ae8fbe42ceeacbeac1f99a2cc1599ece7a`, the reviewed D56 code head. `b50350e` = `b50350e16f5a9356c383e09c357df258f99cd432`, the authorized guard correction. `A` is the exact reviewed D56a protocol-amendment head: this amendment's reviewed commit. `M56a` is the merge commit of the D56a PR and is the launch anchor. D56a deliberately does not name its own future merge SHA.

**Two-anchor launch-closure rule.** This rule replaces the superseded diff above. Launch authorization requires **ALL** of the following:

1. **Execution-byte closure.** The following diff is empty:

   ```text
   git diff H'..M56a -- experiments/submit_d19_a7_bench.slurm experiments/d19_a7_validate.py experiments/d19_bench.py bistar_gp/
   ```

2. **Known test-only delta.** The complete `tests/` diff from `H'` through `M56a` names exactly `tests/test_slurm_argparse.py`, and that file's blob at `M56a` equals its blob at `b50350e`. No other `tests/` delta is permitted.

3. **Amendment closure.** `docs/d19-a7-execution-protocol.md` at `M56a` is byte-identical to `A`; equivalently, `git diff A..M56a -- docs/d19-a7-execution-protocol.md` is empty. Any commit after `A` on the D56a branch before merge must be Notes-only and explicitly identified in the launch authorization.

4. **Topology.** `origin/main` HEAD equals `M56a`. `M56a` is a true merge commit whose second parent is the D56a PR head.

5. **Unchanged enforcement bindings.** The Della worktree HEAD must equal `M56a`, enforced by the script, and every artifact `git_sha` must equal `M56a`, enforced by the validator. V0 binds the validator and frozen vehicle bytes at `M56a`; execution-byte closure makes those bytes identical to the bytes reviewed at `H'`.

6. **Total-surface closure (audit hardening).** The complete
   `git diff --name-only H'..M56a` may contain only paths under `Notes/` or `docs/`,
   plus exactly `tests/test_slurm_argparse.py`; equivalently, the following command
   must print nothing:

   ```text
   git diff --name-only H'..M56a -- . ':(exclude)Notes' ':(exclude)docs' ':(exclude)tests/test_slurm_argparse.py'
   ```

   Rationale: the benchmark process imports through `PYTHONPATH=$EXEC_ROOT` and its
   script directory `experiments/`, so any new or changed top-level `*.py`, top-level
   package directory, or `experiments/` file could shadow a standard-library or
   scientific module and execute unreviewed code that the item-1 closure and V0 cannot
   see. Items 1 and 2 remain as the named anchors; this item closes the remainder of
   the tree. `Notes/` and `docs/` paths cannot enter the interpreter's import path,
   and `docs/d19-a7-execution-protocol.md` stays pinned to `A` by item 3, while
   `tests/test_slurm_argparse.py` stays blob-pinned to `b50350e` by item 2.

**Scope and amendment-time proof.** This amendment does not reinterpret the earlier two-reviewer review or its focused re-confirmation; alters no execution or validator byte; and authorizes no benchmark and no Della access. It only repairs the launch precondition so the authorized parser-test correction does not make D56 permanently unlaunchable. At amendment time, the following mechanical facts were verified at current `origin/main`, D56 merge `M56` = `66ca91cd8a5e0a2bbb7d984b2e5298707160d6c0`, which was merged without launch: `git diff 4c9b79a..origin/main -- experiments/submit_d19_a7_bench.slurm experiments/d19_a7_validate.py experiments/d19_bench.py bistar_gp/` is empty; the complete `tests/` diff from `4c9b79ae8fbe42ceeacbeac1f99a2cc1599ece7a` through current `origin/main` is exactly `tests/test_slurm_argparse.py`; and that file's blob at current `origin/main` is `5ef26ec2464aeb9e788a6e14b443e5801ed8b5c8`, equal to its blob at `b50350e16f5a9356c383e09c357df258f99cd432`. At amendment time the total-surface check also holds at current `origin/main`: the complete name-diff from `H'` contains only `Notes/`, `docs/`, and `tests/test_slurm_argparse.py` paths.

### §7 amendment (D56b, 2026-07-22): PS1 correction, attempt-2 worktree, and launch anchor M56b

Attempt 1, Slurm job `11485635`, is SPENT and immutable. Its four-file failure evidence is committed at `runs/d19_a7_failed_11485635/`, and the AC5 one-submission authorization was consumed. Nothing is retried.

The separately authorized, strictly read-only Della diagnostic established the failure mechanism. With `PS1` unset and nounset enabled, `module purge` passes, while `module load anaconda3/2024.6` reproduces the byte-identical `environment: line 49: PS1: unbound variable` failure. The modulefile emits 51 shell lines; emitted line 50 contains the first unguarded read, `export _LOCAL_OLD_PS1="${PS1}"`. It executes through the environment-imported `_module_raw` wrapper, which explains both the `environment` source label and the reported-line-49 versus emitted-line-50 offset. In a disposable child, defining and exporting an empty `PS1` before `set -u` makes module purge, module load, conda-hook generation and evaluation, and activation of `/home/sc8918/.conda/envs/bistar_gp` all pass. D56b itself performs no Della operation and no benchmark; the diagnostic ran under its own separate read-only authorization.

The frozen correction is exactly `export PS1="${PS1-}"`, placed after `set -euo pipefail` and before the first module operation. Nounset is never disabled, and no `set +u` bracketing is introduced.

Attempt 2 executes in `/scratch/gpfs/SUYOGHC/bistar_gp_a7_exec_02`. The attempt-1 worktree `/scratch/gpfs/SUYOGHC/bistar_gp_a7_exec` is preserved untouched forever. The in-worktree evidence path `runs/d19_a7_timing/` and the local staging path `runs/d19_a7_timing_incoming`, currently absent, are unchanged.

**Definitions.** `B` = the reviewed D56b code head: the last commit of the D56b PR that touches any non-Notes path. An optional Notes-only tail may follow `B` before merge and must be explicitly identified in the launch authorization. `B` names a Git commit anchor here; it is unrelated to §8's "evidence commit allowlist B", which names a file list. `M56b` = the merge commit of the D56b PR and the NEW launch anchor. D56b deliberately does not name its own future merge SHA. Every `<M56>` placeholder in the §4 procedure and the §5 validator invocation is read as `<M56b>` for attempt 2; it was read as `<M56a>` for attempt 1.

**Attempt-2 launch-closure rule.** Launch authorization requires **ALL** of the following:

1. **Reviewed-surface closure.** The submit script, this protocol document, and the protocol test file at `M56b` must be byte-identical to `B`; the following diff must be empty:

   ```text
   git diff B..M56b -- experiments/submit_d19_a7_bench.slurm tests/test_d19_a7_protocol.py docs/d19-a7-execution-protocol.md
   ```

   This closes the reviewed launch rule itself: no post-review commit or merge resolution can weaken the correction, these tests, or this amendment while the check passes. Any commit after `B` on the D56b branch before merge must be Notes-only and explicitly identified in the launch authorization.

2. **Reviewed execution-byte closure.** The validator, vehicle, and library execution bytes must stay byte-identical to the D56-reviewed bytes; the following diff must be empty:

   ```text
   git diff H'..M56b -- experiments/d19_a7_validate.py experiments/d19_bench.py bistar_gp/
   ```

   Here `H'` remains `4c9b79ae8fbe42ceeacbeac1f99a2cc1599ece7a`, unchanged from the D56a rule.

3. **Six-file total-surface closure.** The complete name-diff from failed-attempt merge `7d234e9ffad6b154e7523507658a6999e7bb6c53` to `M56b` must be limited to exactly this D56b allowlist: `experiments/submit_d19_a7_bench.slurm`, `tests/test_d19_a7_protocol.py`, `docs/d19-a7-execution-protocol.md`, `Notes/DECISIONS.md`, `Notes/SCRATCHPAD.md`, and `Notes/CHATLOG.md`. This pins the attempt-1 evidence blobs and every other tree byte, closing the total surface in the same way as D56a item 6.

4. **Topology.** Before any future launch, `origin/main` HEAD must equal `M56b`. `M56b` must be a true merge commit whose second parent is the D56b PR head.

5. **Fresh authorization.** Attempt 2 still requires a fresh byte-exact author authorization naming `M56b`; the spent attempt-1 authorization does not carry over.

6. **Enforcement bindings.** The Della attempt-2 worktree HEAD must equal `M56b`, enforced by the script. Every artifact `git_sha` must equal `M56b`, enforced by the validator. V0 binds the validator and frozen vehicle bytes at `M56b`, which item 2 makes byte-identical to the `H'`-reviewed bytes.

This amendment does not reinterpret the D56 review lineage, alters no validator or vehicle byte, and authorizes no benchmark and no Della access.

### §7 amendment (D56c, 2026-07-22): environment re-freeze, attempt-3 worktree, and launch anchor M56c

Attempt 2, Slurm job `11497561`, is SPENT and immutable. It failed at the preflight `import bistar_gp` (exit 82) because the frozen Della environment lacked `arviz` (and its transitive `jsonschema` and `referencing`), which `bistar_gp/__init__.py` imports through `mcse_strategy`. The submit-script preflight caught this and failed closed before any benchmark cell, so no scientific computation occurred. The attempt-2 failure is recorded in the Notes decision log rather than a committed evidence directory.

**Environment re-freeze (prerequisite).** The frozen `bistar_gp` conda environment was extended, without perturbing the five pinned scientific versions, by installing `arviz` and `jsonschema`: a pure addition of eleven packages, with zero removals and zero version changes. The complete post-change 69-package manifest is committed at `docs/d19_a7_freeze/bistar_env_after.txt` and is the authoritative environment for attempt 3; prereg addendum **v1.22** records the re-freeze, the eleven-package delta, the install commands, and the observed verification. This supersedes, for future attempts, the original five-version freeze recorded in §2 and §3, without rewriting that history. Prospective versioning amendment: §8's post-run success addendum (allowlist C) moves from **v1.22** to **v1.23**, because v1.22 now denotes this environment re-freeze; §8's "latest addendum is v1.21" is likewise superseded, not rewritten.

**Preparation-time environment enforcement.** Immediately before a future launch authorization for attempt 3 is cast, the read-only preparation preflight on Della must require **BOTH**: (a) exact byte-for-byte equality between the live `/home/sc8918/.conda/envs/bistar_gp/bin/python -m pip list --format=freeze` and the committed `docs/d19_a7_freeze/bistar_env_after.txt` (the complete 69-package inventory); and (b) a successful `import bistar_gp` under the five pinned versions (python 3.11.14, torch 2.10.0+cu128, gpytorch 1.15.1, pyro 1.9.1, numpy 2.4.2). Both are read-only and run no benchmark. **Honest scope.** The complete 69-package inventory is enforced only here, at preparation time, immediately before the authorization is cast. The submit job itself continues to enforce the five version pins plus `import bistar_gp` (script exit 82), **not** the complete 69-package manifest. The interval between this preparation check and the single submission is a disclosed, user-controlled trust interval, accepted under the D56c lightweight disposition; the operator mutates no package across it.

**Attempt 3.** Attempt 3 executes in `/scratch/gpfs/SUYOGHC/bistar_gp_a7_exec_03`. The attempt-1 worktree `/scratch/gpfs/SUYOGHC/bistar_gp_a7_exec` and the attempt-2 worktree `/scratch/gpfs/SUYOGHC/bistar_gp_a7_exec_02` are both preserved untouched forever, and neither is reused. The in-worktree evidence path `runs/d19_a7_timing/` and the local staging path `runs/d19_a7_timing_incoming`, currently absent, are unchanged.

**Definitions.** `R56c` = the reviewed D56c code head: the last commit of the D56c PR that touches any non-Notes path. This is a new, unambiguous anchor name for D56c, unrelated both to the D56b commit anchor `B` and to §8's "evidence commit allowlist B". `M56c` = the merge commit of the D56c PR and the NEW launch anchor; D56c deliberately does not name its own future merge SHA. Every `<M56>` placeholder in the §4 procedure and the §5 validator invocation is read as `<M56c>` for attempt 3.

**Attempt-3 launch-closure rule.** Launch authorization requires **ALL** of the following:

1. **Reviewed-surface closure (five files).** These five files at `M56c` must be byte-identical to `R56c`; the following diff must be empty:

   ```text
   git diff R56c..M56c -- experiments/submit_d19_a7_bench.slurm tests/test_d19_a7_protocol.py docs/d19-a7-execution-protocol.md docs/prereg-addenda-d19.md docs/d19_a7_freeze/bistar_env_after.txt
   ```

   No post-review commit or merge resolution can weaken the correction, these tests, this amendment, the environment addendum, or the committed manifest while the check passes. Every commit after `R56c` on the D56c branch before merge must be Notes-only and explicitly identified in the launch authorization.

2. **Reviewed execution-byte closure.** The validator, vehicle, and library bytes stay byte-identical to the D56-reviewed bytes; the following diff must be empty, with `H'` = `4c9b79ae8fbe42ceeacbeac1f99a2cc1599ece7a`:

   ```text
   git diff H'..M56c -- experiments/d19_a7_validate.py experiments/d19_bench.py bistar_gp/
   ```

3. **Eight-file total-surface closure.** The complete name-diff from this D56c branch's base `M56b` = `d9c924fc35cc771775732cb431014a25de8a6400` to `M56c` is limited to exactly the eight-file D56c allowlist: the five reviewed-surface files above plus `Notes/DECISIONS.md`, `Notes/SCRATCHPAD.md`, and `Notes/CHATLOG.md`.

4. **Topology.** `origin/main` HEAD must equal `M56c`, a true merge commit whose second parent is the D56c PR head.

5. **Preparation-time environment enforcement.** The read-only Della check above — exact 69-package inventory equality against `docs/d19_a7_freeze/bistar_env_after.txt` **and** a successful `import bistar_gp` — must pass immediately before this authorization is cast.

6. **Fresh authorization and enforcement bindings.** Attempt 3 requires a fresh byte-exact author authorization naming `M56c`; no prior authorization carries over. The Della attempt-3 worktree HEAD must equal `M56c` (script-enforced) and every artifact `git_sha` must equal `M56c` (validator-enforced).

This amendment alters no validator or vehicle byte, and authorizes no benchmark and no Della access.

### §7 amendment (D56d, 2026-07-23): post-run correction to the validator `condition` token semantics

**Post-run motivation and status.** A7 job `11517022` completed successfully. Recovery checks R1–R10 passed, and the recovered twelve-entry bundle `runs/d19_a7_timing_recovery_11517022_incoming` is preserved unchanged. That bundle validated V0–V4, V6–V10, and V12–V15, but the ORIGINAL validator returned **14/16 PASS**: V5 and V11 alone failed because the raw free-text `condition` substring matched `conditional` in the original `lscpu` Spectre-v2 host-metadata line (`IBPB conditional`). This is explicitly a **post-run, outcome-informed correction**. It is NOT preregistered and MUST NOT be described as an original clean validation. No timing magnitude has been interpreted, and the run remains UNVALIDATED until the amended, merged validator passes.

**Bounded correction.** For validator free-text scans only, the `condition` matcher changes from a raw substring to `condition(?!al)`: raw rejection remains in force except for the unrelated `conditional` family. The vehicle's forbidden-token table, its forbidden-KEY checks, the closed-world artifact schema, `_artifact_scan_text`, and every other token's matching semantics are unchanged. V0 gains an optional `--validator-sha` split: `experiments/d19_bench.py` remains bound to `--expected-sha`, while `experiments/d19_a7_validate.py` is bound to `--validator-sha`; omitting `--validator-sha` defaults it to `--expected-sha`, preserving every existing invocation.

**Definitions and D56d closure.** `R56d` is the reviewed D56d code head, defined as the last non-Notes commit off M56c. `M56d` is the D56d merge anchor: a true merge whose second parent is the D56d PR head. D56d deliberately does not name its own future merge SHA. Post-merge revalidation requires ALL of the following:

1. **Reviewed-surface closure.** `experiments/d19_a7_validate.py`, `tests/test_d19_a7_protocol.py`, and `docs/d19-a7-execution-protocol.md` must be byte-identical from `R56d` through `M56d`; the following diff must be empty:

   ```text
   git diff R56d..M56d -- experiments/d19_a7_validate.py tests/test_d19_a7_protocol.py docs/d19-a7-execution-protocol.md
   ```

   Every commit after `R56d` on the D56d branch before merge must be Notes-only and explicitly identified.

2. **Execution-byte closure for the unchanged surface.** With `H'` = `4c9b79ae8fbe42ceeacbeac1f99a2cc1599ece7a`, the following diff must be empty:

   ```text
   git diff H'..M56d -- experiments/d19_bench.py bistar_gp/
   ```

   The validator is intentionally NOT in this diff because D56d amends it. Its reviewed identity is pinned at `M56d` and checked by V0 through `--validator-sha`.

3. **Six-file total-surface closure.** The complete `git diff --name-only M56c..M56d` is limited to `experiments/d19_a7_validate.py`, `tests/test_d19_a7_protocol.py`, `docs/d19-a7-execution-protocol.md`, `Notes/DECISIONS.md`, `Notes/SCRATCHPAD.md`, and `Notes/CHATLOG.md`.

4. **Topology and authorization.** `origin/main` must equal `M56d`; `M56d` must satisfy the true-merge and second-parent rule above; and post-merge revalidation requires a fresh explicit author authorization. The required reviews are AI reviews, not GitHub reviews or CI.

**Post-merge revalidation.** After the closure and authorization pass, run exactly:

```text
python experiments/d19_a7_validate.py --evidence-dir runs/d19_a7_timing_recovery_11517022_incoming --expected-sha 725e5f194de7bda12475f0d2a64893aa5cf5315f --validator-sha <M56d>
```

The expected result is all V0–V15 PASS. V0 then binds the unchanged vehicle to M56c and the reviewed amended validator to M56d; V5 and V11 accept the `conditional` host-metadata line; V9 continues to bind every recovered artifact to M56c. Only that clean post-merge result validates the run.

## 8. Later allowlists and remaining open decision

Evidence commit allowlist B is `runs/d19_a7_timing/{8 JSONs, slurm-<id>.out, slurm-<id>.err, job_metadata.txt, PROVENANCE.sha256}` plus Notes updates. `.gitignore:29` (`slurm-*.out`) ignores the stdout evidence file, so the evidence commit MUST use `git add -f runs/d19_a7_timing/slurm-<id>.out` and MUST verify that `git ls-files runs/d19_a7_timing/` lists exactly the twelve evidence files before committing; this makes a silent stdout drop impossible. Post-run addendum allowlist C is `docs/prereg-addenda-d19.md` v1.22 plus Notes. Numbering is fixed: v1.16 was burned as the M2bR run label, v1.18 is permanently burned, and the latest addendum is v1.21. **Superseded for D56c onward by the §7 D56c amendment above:** v1.22 now denotes the environment re-freeze, and the post-run success addendum (allowlist C) is `docs/prereg-addenda-d19.md` **v1.23** plus Notes. The historical numbering in this sentence is left unrewritten.

All claims are scoped to the frozen `intel,cascade,rh9` 90-node pool. Deletion of the superseded pre-D22 anchors remains a separate OPEN author decision.
