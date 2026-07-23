# A7 job-11517022 — timing evidence recovery record

Provenance record for the **validated A7 timing evidence** of job 11517022. It documents a disclosed,
post-run metadata recovery and interprets **no** benchmark timing magnitude. Planning evidence, not a
scientific-paper result.

## 1. Status and anchors
- Execution / expected anchor **M56c** = `725e5f194de7bda12475f0d2a64893aa5cf5315f`.
- Validator anchor **M56d** = `5fcc2d316f6894ed793418d9ab16274e6c8a1ad2`.
- Canonical validated evidence: `runs/d19_a7_timing/` (12 files).
- Preserved original incomplete capture: `runs/d19_a7_timing_original_incomplete_11517022/` (11 files).

## 2. Job outcome (scheduler accounting)
From the recovered `job_metadata.txt` (`sacct`), verbatim:
```
JobID|State|ExitCode|Elapsed|Timelimit|TotalCPU|MaxRSS|NodeList|Submit|Start|End
11517022|COMPLETED|0:0|00:05:31|02:00:00|07:57.822||della-i13n2|2026-07-22T22:24:36|2026-07-22T22:24:51|2026-07-22T22:30:22
11517022.batch|COMPLETED|0:0|00:05:31||07:57.822|828880K|della-i13n2|2026-07-22T22:24:51|2026-07-22T22:24:51|2026-07-22T22:30:22
11517022.extern|COMPLETED|0:0|00:05:31||00:00:00||della-i13n2|2026-07-22T22:24:51|2026-07-22T22:24:51|2026-07-22T22:30:22
```
`della-i13n2` is inside the frozen `intel,cascade,rh9` 90-node pool. The stdout log records `ENV-OK` on
the five frozen pins (python 3.11.14 / torch 2.10.0+cu128 / gpytorch 1.15.1 / pyro 1.9.1 / numpy 2.4.2),
eight `CELL` cells (sub 1–4, full 1–4) each exiting `0`, and `MATRIX-COMPLETE`. These are
scheduler/structural facts only; no benchmark timing magnitude is interpreted.

## 3. Original P6 omission
The contemporaneous P6/P6b capture wrote only **10** files. Protocol P6 records scheduler metadata via
`sacct … > runs/d19_a7_timing/job_metadata.txt`; that redirect target is CWD-relative and did not resolve
from the capture CWD, so `job_metadata.txt` was never written in the original sequence. The original
manifest therefore froze at **902 B / 10 lines** (`a3aadf32…`), covering the eight JSON artifacts,
`slurm-11517022.err`, and `slurm-11517022.out`.

## 4. Delayed exact P6 recovery
The **exact** P6 `sacct` command was re-run **post-run** — disclosed, and NOT contemporaneous with the
original P6/P6b sequence — producing `job_metadata.txt` (456 B, `6d24b28d…`) and the recovered manifest
(**985 B / 11 lines**, `8c27e40b…`). The recovery is a delayed scheduler-accounting capture; it altered
no benchmark artifact.

## 5. Byte identity (original and recovered tree/file hashes)
The ten shared payload files are byte-identical across the two bundles (identical SHA-256). The recovered
bundle = the original bundle plus `job_metadata.txt`; the recovered 11-line manifest = the original
10-line manifest plus the single sorted `job_metadata.txt` line (985 − 902 = 83 B = one manifest line).

### Original incomplete bundle — `runs/d19_a7_timing_original_incomplete_11517022/` (11 files)
```
a3aadf32650fdf7d853b4ecd3a3671298a6a80236b1403ef71ce2e8eca75b55f     902  PROVENANCE.sha256
f7df3be2326b7427a32758ac3c20e65b24bf34897a9d556608a1b9ff4fb8410b    4358  bench_full_threads_1.json
d09dfb25ab33db144af4f0f6f133de5ba86f0c687a54c1cf3fc8e121f53b7af4    4359  bench_full_threads_2.json
3bcf1322781db9b7ce1c2f903956c9ab0ed22db9e8ec1de2a89f4ba2c8528c14    4359  bench_full_threads_3.json
2ca418389a3b583357e27f7629a2097ab8a8b31d9a488f87fcd05dd6d209c285    4358  bench_full_threads_4.json
d690d29ad09264d7cb4db83a42bd9e96b4bcf95281b4c65ad7af7cf4f2a6c2a5    4360  bench_sub_threads_1.json
e0bccf3083472006bbb36afd6577ba58df3f2780257f49ecb76a1c5c4b9ff5a4    4364  bench_sub_threads_2.json
3abde383a9b2bb5e69d2b4a773ef379ed03063b69e5df8a9bbc2b8697c797b89    4364  bench_sub_threads_3.json
a037413ebbca0be64cf15d26e8f67a4dccad3be4f927846edcf6d4bf45786510    4362  bench_sub_threads_4.json
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855       0  slurm-11517022.err
f8f76037994d0106d9e7f50495bd3cf12b4bd6e215806ec84b1c0cc2e8a7e960    6626  slurm-11517022.out
```

### Canonical recovered bundle — `runs/d19_a7_timing/` (12 files)
```
8c27e40b71fa3e01b11625c256e480d99340a507b407a3e0a1ea8453973cf2d2     985  PROVENANCE.sha256
f7df3be2326b7427a32758ac3c20e65b24bf34897a9d556608a1b9ff4fb8410b    4358  bench_full_threads_1.json
d09dfb25ab33db144af4f0f6f133de5ba86f0c687a54c1cf3fc8e121f53b7af4    4359  bench_full_threads_2.json
3bcf1322781db9b7ce1c2f903956c9ab0ed22db9e8ec1de2a89f4ba2c8528c14    4359  bench_full_threads_3.json
2ca418389a3b583357e27f7629a2097ab8a8b31d9a488f87fcd05dd6d209c285    4358  bench_full_threads_4.json
d690d29ad09264d7cb4db83a42bd9e96b4bcf95281b4c65ad7af7cf4f2a6c2a5    4360  bench_sub_threads_1.json
e0bccf3083472006bbb36afd6577ba58df3f2780257f49ecb76a1c5c4b9ff5a4    4364  bench_sub_threads_2.json
3abde383a9b2bb5e69d2b4a773ef379ed03063b69e5df8a9bbc2b8697c797b89    4364  bench_sub_threads_3.json
a037413ebbca0be64cf15d26e8f67a4dccad3be4f927846edcf6d4bf45786510    4362  bench_sub_threads_4.json
6d24b28d8c3fbfa4890858c84554e7b733d1a1bd510670f18c0a2b146e8749e9     456  job_metadata.txt
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855       0  slurm-11517022.err
f8f76037994d0106d9e7f50495bd3cf12b4bd6e215806ec84b1c0cc2e8a7e960    6626  slurm-11517022.out
```

## 6. Manifests
- Original: `a3aadf32650fdf7d853b4ecd3a3671298a6a80236b1403ef71ce2e8eca75b55f` (902 B / 10 lines).
- Recovered / canonical: `8c27e40b71fa3e01b11625c256e480d99340a507b407a3e0a1ea8453973cf2d2` (985 B / 11 lines).

## 7. Validation
The amended validator returned **16/16 PASS, exit 0** against `--expected-sha M56c --validator-sha M56d`
on the canonical directory `runs/d19_a7_timing/` (V0–V15 PASS; V5/V11 pass because `condition(?!al)` no
longer matches `conditional`; V0 binds the validator to M56d and the vehicle to M56c; V9 confirms artifact
`git_sha == M56c`). Only on this clean pass is the run validated.

## 8. D56d amendment (post-run, outcome-informed)
The validator's free-text `condition` matcher was corrected post-run (D56d, merged as M56d). The ORIGINAL
validator returned **14/16 PASS**: V5 and V11 alone failed because the raw substring `condition` matched
`conditional` in the `lscpu` Spectre-v2 host line (`IBPB conditional`). This correction is explicitly
post-run and outcome-informed; it is **NOT preregistered** and **NOT an original clean validation**. No
timing magnitude has been interpreted.

## 9. Paths and preservation
- Canonical validated evidence: `runs/d19_a7_timing/` (12 files; §5 recovered table).
- Preserved original incomplete capture: `runs/d19_a7_timing_original_incomplete_11517022/` (11 files; §5 original table).
- Della worktrees `/scratch/gpfs/SUYOGHC/bistar_gp_a7_exec`, `…_exec_02`, and `…_exec_03`, and the
  Della-side `runs/d19_a7_timing`, remain untouched (no Della action in this closure).
