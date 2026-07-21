# Pre-D22 `d19_bench.py` timing anchors — SUPERSEDED

**Status:** SUPERSEDED (record created under D55, 2026-07-20)
**Authority:** prereg addendum v1.8 item 2(d) and item 5; v1.9 item 1 (author ratification)
**Applies to:** `runs/d19_planning/bench_sub.json`, `runs/d19_planning/bench_full.json`

---

## 1. What this record does

Prereg addendum v1.8 item 2(d) requires that `experiments/d19_bench.py` be
reworked to the v1.2-point-6 timing-only firewall **and** that "its pre-D22
anchors [be] marked superseded". D55 performs the rework. This document is the
supersession record for the two committed artifacts that the pre-rework script
produced.

Both artifacts remain in the repository, byte-unchanged. Nothing here deletes,
edits, or regenerates them. They stay as provenance of what the M1-era script
did, consistent with the v1.9 item 1 ratification that superseded material
"stay[s] as provenance only".

## 2. What is superseded, and why

Two independent defects disqualify these files as anchors for any A7 decision.

**(a) They carry prohibited scientific values.** The generating script persisted
MAP hyperparameters, the MAP noise variance, and the full Hessian eigenvalue
spectrum with its SPD flag and post-floor condition number. v1.2 point 6 permits
only timing fields, potential/gradient evaluation counts and costs, and leapfrog
counts; v1.9 item 1 confirms that "hyperparameters, samples, acceptance,
divergences, model scores, and posterior summaries remain forbidden in benchmark
artifacts". v1.8 item 2(d) names this defect explicitly.

**(b) They were produced through the holdout-bearing loader.** The pre-rework
script called `load_mauna_loa`, which materializes the sealed 60-month holdout
(`bistar_gp/data.py`), rather than the training-only `load_mauna_loa_training`
that v1.2 point 6 mandates. Both artifacts consequently record `n_test_months`,
holdout-derived metadata that a study-facing artifact must not carry (§6.6).

## 3. Artifact inventory

### `runs/d19_planning/bench_sub.json`

- sha256 `ed5c7bf4467c83896dc43d46d17564f052c806808877b031733a16822eb070a2`
- size 3663 bytes
- 19 prohibited keys, plus holdout metadata:

| Key | Class |
|---|---|
| `map_hyperparameters` (7 values) | hyperparameter values |
| `map_noise_variance_normalized` | noise value |
| `hessian.eigenvalues` (7 values) | curvature spectrum |
| `hessian.min_eig`, `hessian.max_eig` | curvature spectrum |
| `hessian.spd` | curvature diagnostic |
| `hessian.n_below_1e-6_floor` | curvature diagnostic |
| `hessian.condition_number_after_floor` | curvature diagnostic |
| `provenance.y_mean_ppm`, `provenance.y_std_ppm` | response-variable statistics |
| `provenance.x_offset_years`, `provenance.x_train_min`, `provenance.x_train_max`, `provenance.span_years` | data-derived statistics |
| `sub_design.stride_months_mean`, `sub_design.unique_calendar_months_covered`, `sub_design.span_years` | data-derived design statistics |
| `sampled_sites` | per-site inventory |
| `period_length_sampled` | per-site structural flag |
| `provenance.n_test_months` | holdout-derived metadata |

### `runs/d19_planning/bench_full.json`

- sha256 `ea47270d599213187d9fbb6bb2e018b0c166fcd4c6ae5c4d6e476bd0b6ff5b34`
- size 3451 bytes
- 17 prohibited keys, plus holdout metadata: the same set as `bench_sub.json`
  minus the three `sub_design.*` entries (no subsample block at full scale), plus
  `single_thread` (a mid-run `torch.set_num_threads(1)` retiming block, removed
  under D55 because it is incompatible with the pre-import thread-pinning
  contract).

## 4. Consequences

- Neither file may price an A7 decision, a Della assignment, a thread-pinning
  choice, or any cost projection.
- No timing or thread-pinning number in either file is carried forward. D55
  invents no replacement values: the reworked script has **not been run**, on
  any machine. The A7 timing run, local and then thread-pinned on Della, is a
  separate later authorization.

### Output namespace: these paths are retired, not reused

The reworked `experiments/d19_bench.py` writes to a **different namespace**:

| | Pre-D22 (superseded) | D55 onward |
|---|---|---|
| Directory | `runs/d19_planning/` | `runs/d19_a7_timing/` |
| Filename | `bench_{scale}.json` | `bench_{scale}_threads_{threads}.json` |

Two reasons. First, the old default addressed exactly the two files catalogued
above, so any A7 run would have destroyed the historical provenance this
document exists to preserve. Second, the thread setting is now part of the
filename, so a thread sweep across `--threads 1..4` cannot overwrite its own
earlier rows.

The script additionally **refuses** any resolved target equal to either
superseded path, and performs that refusal before loading data or constructing
a model, so a future change to the naming rule cannot silently start
overwriting these files. Atomic honest replacement is preserved for repeated
runs at the same scale/thread target; no general no-clobber policy was
introduced.

## 5. Deletion is NOT performed here

Deleting or rewriting these tracked artifacts is **a separate author decision**,
deliberately not folded into D55. D55 neither deletes nor edits any file it did
not create. The banner-style treatment follows the precedent of v1.9 item 1,
which applied superseded banners to four documents rather than removing them.

## 6. Cross-references

- `Notes/DECISIONS.md` — D55
- `docs/prereg-addenda-d19.md` — v1.2 point 6, v1.6 item 6, v1.8 items 2(d)/5, v1.9 item 1, v1.11 item 4
- `docs/plan-d19-mauna.md` — §1.3 (Della guidance), §7 A7
- `experiments/d19_e1_bench.py` — the firewalled-bench reference pattern
