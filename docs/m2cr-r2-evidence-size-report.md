# M2cR R2 — evidence-size measurement report (B15(ii))

**Status: measurement report, 2026-07-16 (regenerated after the final-gate fix round), corrected and
updated 2026-07-18 under R2a (v1.20 §7, D49): the static table reflects the R2a regeneration at the
enforcement code commit plus the ninth (evidence-ceilings) artifact, and the measured-exemplar
provenance below now states exactly which figures are test-reproduced.** Plan §4.4 deferred every
exact numeric ceiling to a versioned pre-execution addendum before R4 (milestone R2a); **v1.20 has
since frozen the ceilings at exactly the values proposed at the end of this report.** Completeness is
never weakened to fit a ceiling, and overflow handling stays `INFRA_FAILURE`, never truncation
(B15(iii)).

Every figure is labeled either **measured** (an exact byte count of a committed artifact or a
hermetic serialization) or **derived** (a formula over measured components; plan §4.4 requires the
derivation to be named where it derives). Tooling: `bistar_gp/m2cr/measure.py`; per-record and
per-event figures come from hermetic rigged-oracle runs of the v2 gates under the canonical
serializer with the frozen nonfinite sentinels.

## Measured — committed freeze artifacts

| Artifact | Bytes | Notes |
|---|---|---|
| `m2cr_importable_artifact_manifest_v1.jsonl` | 8,746,622 | format v2 (roots header, per-entry loader); 39,968 entries: 39,402 source, 564 extension, 2 importable-archive, 0 orphan-bytecode (the +2 sources vs the R3 figure are the R3a launch vehicle `bistar_gp/m2cr/r4_launch.py` and `tests/test_m2cr_r4_launch.py`; R3 had added its two modules plus six test files; R2a itself had added `tests/test_m2cr_evidence_ceilings.py`) |
| `m2cr_dependency_lock_v1.json` | 57,451 | supplementary only; editable installs excluded from `pip_freeze` (external audit round-3 F4), reproducible at HEAD |
| `m2cr_preboundary_attestation_set_v1.json` | 14,560 | dyld main cache plus its twelve declared subcaches, interpreter, and the 74-entry pre-boundary bootstrap closure; smaller than the prior 76 because the fabricated `bistar_gp`/`bistar_gp.m2cr` namespace packages no longer claim a never-executed `__init__.py` origin (WI1); the three worktree-origin closure pins are stored worktree-relative (F3) |
| `m2cr_infrastructure_manifest_v1.json` | 3,026 | Layer 1a; repo-relative pins (8 artifacts incl. native-stack expectations and, since R2a, the evidence-ceilings artifact) |
| `m2cr_native_stack_expectations_v1.json` | 47,047 | WI1/WI2 launch-authority cycle: frozen native stack, profile hash, build-pinned bound sentinel `__hash__` (§4.5.8), backend build markers, Stage-B delta, the **67**-entry expected on-disk loaded-image set (path+sha256; +1 vs the prior 66 because the measurement now enumerates images after the config-show calls, matching the child sequence — `numpy.show_config()` lazily loads pyyaml's extension), and the **173-entry Stage-C `loaded_image_allowlist`, each pinned `(path, sha256)`** so the child authenticates every payload-phase native image's bytes (§4.5.7 "enumeration AND hashing"; three-reviewer gate) rather than allowlisting by path alone |
| `m2cr_environment_freeze_manifest_v1.json` | 731 | the aggregating manifest; its file sha256 is the chain member |
| `m2cr_child_env_mapping_v1.json` | 602 | includes the concrete frozen `PATH` |
| `m2cr_interpreter_pin_v1.json` | 383 | version string plus resolved-target sha256 |
| `m2cr_evidence_ceilings_v1.json` | 255 | added by R2a (v1.20): the five ratified evidence-size ceilings, the one machine-readable authority enforcement consumes; hand-authored, never regenerated |

Fixed-artifact total: **8,870,677 bytes** (measured; regenerated at the R4 audit-hardening commit
`b1ee5ec` — the D52 Update 5 amendment commit J — via the established fresh-detached-worktree
process. The J regeneration is a pure authorized cascade over the two hardened source files:
the importable manifest changes ONLY in its informational header worktree path and in the two
entries `bistar_gp/m2cr/audit.py` (F1/F2/F3 hardening + the deterministic closure API; sha256
`2adae520…`, size 89,677 B) and `tests/test_m2cr_audit.py` (+8 discriminating tests; sha256
`ad0d1af5…`, size 46,611 B); all other 39,966 entries are byte-identical and the manifest file is
unchanged at 8,746,622 B because both grown entries kept 5-digit sizes and fixed-width digests. The
aggregating and infrastructure manifests re-derive at unchanged sizes (digest-only changes; the
infrastructure code section changes ONLY the `audit.py` pin), the Layer-1b protocol manifest
re-pins the new Layer-1a digest, and the interpreter pin (re-attested per v1.19 §4.5.1), child-env
mapping, dependency lock, native-stack expectations, AND the preboundary attestation set stay
byte-identical. The stale `_02` launch packet was removed from the tree in commit J and is not a
freeze artifact. The E2 regen at `473a3f8` (commit H) measured the same 8,870,677-byte total; the
first R4 preparation regen at `f745bcd` measured 8,870,676 bytes (header-path-only manifest delta,
8,746,621 B). The R3a total at the `c11db47` regen was 8,870,677 bytes — the importable manifest had gained the two R3a
sources `bistar_gp/m2cr/r4_launch.py` and `tests/test_m2cr_r4_launch.py`, with no infrastructure
code pin for the launcher per the D50 ballot-C precedent. The R3 total at the `c038f47`
regen was 8,870,266 bytes; the R2a total at PR #17 merge was 8,868,576 bytes; the
R2-close total at PR #16 merge was 8,867,965 bytes over the then-eight artifacts. The three R3
Layer-1b statics — the diagnostic-record schema, the protocol parameters, and the protocol
manifest — are deliberately OUTSIDE this nine-artifact infra-pinned set; they are pinned by the
Layer-1b protocol manifest and checked against the same v1.20 static per-file ceiling by
`verify_protocol_manifest`.)

Two truthfulness notes. First, the plan §4.5.12 ratification-time estimates (roughly 78,890 entries,
about 12 MB) were explicitly "not the R2 measurement"; the measured inventory is smaller because the
walker attributes each artifact to exactly one root (`lib-dynload` and `site-packages` are inside
the stdlib root), the worktree portion comes from a fresh detached worktree holding only committed
content, and the B15(ii) scope excludes source-backed `__pycache__` entries. An earlier draft of
this report counted 12 orphan-bytecode entries; review of the classifier showed all twelve were
dotted-stem source-backed caches, and the corrected walker reports zero true orphan candidates in
the frozen base. Second, the manifest header records the absolute path of the freeze-time detached
worktree, which is temporary by construction: any future authorized launch runs from its own fresh
detached worktree at its own frozen commit and therefore regenerates the freeze (new provenance per
plan §4.3). The freeze-time worktree path in the header is **informational and exempt** from the
launch-time physical-path check (plan §4.5.1 pins the CWD to the run's own worktree); the worktree
root's identity and hashes are re-walked against the launch worktree by `(root_id, relpath, sha256)`,
so a content-matching per-launch worktree is accepted and a content mismatch fails closed. The
three host-global roots keep exact physical-path equality. External audit round-3 F3 extended this
same worktree-relative discipline to the **pre-boundary attestation set**: its five worktree-origin
bootstrap-closure pins are now stored `{root: worktree, relpath, sha256}` (no freeze-time absolute
path) and verified against each launch's own worktree, with the resolved target required to stay
beneath the worktree root (checkpoint CP-3) so a symlink cannot escape it; the interpreter, dyld
family, and stdlib closure members keep absolute paths.

## Measured exemplars — per-node records and event stream (hermetic)

These are **measured exemplars**, not proven upper bounds. Each byte figure is the canonical
serialization of a specific rigged-oracle run. **Measurement-provenance correction (2026-07-18,
R2a/v1.20 §7, D49):** an earlier revision of this paragraph claimed all five figures were
"reproduced deterministically by `tests/test_m2cr_measure.py::test_evidence_size_report_figures_reproduce`";
that test reproduces exactly **3,179** and **1,613**. The **5,894 / 3,029 / 6,088** figures were
measured by a freeze-time rig that was never committed (its rigged message strings and marker
serialization are not recoverable), so they are recorded exemplars, not test-reproduced values. A
**committed corroborating rig**
(`tests/test_m2cr_measure.py::test_structural_worst_case_and_event_figures_reproduce_from_committed_rig`)
walks the same fixture/serializer path — the frozen v2 gates over the same rigged quadratic oracle,
both starts restarted and the retry fired — and pins its own independently derived exemplars:
worst-case record **5,960** bytes, clean-node gate-event stream **2,939** bytes over 7 gate events
(the 9-event figure additionally counted the two payload-emitted node markers), and worst-case
gate-event stream **6,184** bytes over 15 events. The committed rig corroborates the recorded
figures' structure and magnitude; the derived projections and the v1.20-ratified ceilings stand on
the recorded figures, whose ×3.7+ headroom absorbs the small rig-string differences. The same
correction covers the **84,921**-byte runtime-envelope figure below: it is a one-run hermetic
exemplar whose exact value embeds run-directory path lengths (the prelaunch/attestation provenance
records absolute paths), so it is not a reproducible constant and no test pins it; the projection
already treats the envelope class as measured per run, never frozen. They are
exemplars, not maxima, because one field is not length-bounded: the optimizer/retry `message` is
schema-typed `{"type": "string"}` (a SciPy termination message), so a pathological minimizer could
enlarge a record without changing its structural path. R2a froze ceilings with headroom precisely so
the unbounded `message` cannot collide with a limit; the derivations below therefore price a
**structural worst case** (both starts restarted, retry fired), not a proven maximum over all string
content.

| Item | Bytes | Basis |
|---|---|---|
| Accepted node, no restart, no retry | 3,179 | measured exemplar |
| Failed node (optimizer gate failure) | 1,613 | measured exemplar |
| Structural worst case: both starts restarted AND retry fired | 5,894 | measured exemplar |
| Write-ahead events, clean node (9 events, full curvature payloads) | 3,029 | measured exemplar |
| Write-ahead events, worst-case node (17 events) | 6,088 | measured exemplar |

## Derived — full-closure projections

The B7 probe closure has at most about 1,481 unique nodes (plan §6.1); the node count enters every
projection as a parameter with that default, not a constant.

**Two distinct storage classes (external-audit finding 5).** The committed freeze artifacts above are
**static, one-time** repository storage. The **per-run evidence bundle** is what each launch emits
under `docs/m2c_evidence/<run_id>/` (§4.4), and it is a *separate* quantity: the earlier revision of
this report labelled a figure "complete bundle" that summed the static freeze total with the per-node
and per-event products while **omitting** the runtime envelope classes and the stdout/stderr
allowances — a mislabel corrected here. Every RUN_DIR_LAYOUT evidence class is now explicitly
classified in `bistar_gp/m2cr/measure.py` (`RUN_DIR_EVIDENCE_CLASSES`), and a CI check fails closed if
any layout member lacks a measurement classification, so the per-run projection cannot silently omit a
component.

**Static freeze-artifact storage (one-time, committed):** Fixed-artifact total **8,870,677 bytes**
(the table above); it is NOT part of the per-run evidence bundle.

**Per-run evidence bundle (per launch) — components:**

| Component | Bytes | Basis (labeled) |
|---|---|---|
| Runtime envelope classes (`RUN_DIR_EVIDENCE_CLASSES` marks 20 `fixed_runtime` + the `conditional` `bootstrap_failure.json`; all 20 present in this hermetic run now that the WI1 fake bundle carries the mandatory importable-manifest directive — `manifest_pre.json` 329, `manifest_post.json` 334, and the new `origin_binding_pre.json` 82 are included) | 84,921 | measured (hermetic capture via `measure_run_dir_fixed_evidence`; `import_inventory.json` dominates at 41,543 and scales with the real import closure) |
| Run-local scratch (`home/`, `tmp/`, `xdg/`) | (allowance) | any payload-written contents are Layer-3 raw-manifested, so represented as a caller-supplied allowance (unbounded, no hermetic basis), NOT assumed zero; `pycache/` alone is asserted empty (zero) |
| Per-node records, all nodes at the structural worst case | 8,729,014 | derived: 5,894 × 1,481 |
| Event stream, all nodes at the structural worst case | 9,016,328 | derived: 6,088 × 1,481 |
| stdout / stderr | (allowance) | caller-supplied allowance, labeled `measured: false`; no hermetic basis, never a measured claim |
| **Per-run evidence bundle, measured-basis subtotal** | **17,830,263** | derived: runtime envelopes (84,921) + per-node product + per-event product |
| Per-run evidence bundle, complete | 17,830,263 + allowances | derived: measured-basis subtotal + caller-supplied stdout/stderr + run-local-scratch allowances |

The complete per-run bundle is exactly `derive_bundle_projection`'s `complete_bundle` = sum(measured
fixed runtime bytes) + sum(caller-supplied allowance bytes) + sum(per-node worst-case bytes ×
node_count); the runtime envelope classes and the allowances are genuine components of it, not
omitted. The projection prices every node at the structural worst-case exemplar (both starts
restarted, retry fired). It is **not** a proven upper bound over all runs, because the `message`
string is unbounded (external audit F8); R2a sets each ceiling with headroom over these figures so an
enlarged `message` cannot collide with a limit, and if any future measurement exceeds a figure the
resolution is a larger ceiling, never reduced completeness. stdout/stderr have no hermetic measurement
basis; the measurement API represents them only as a caller-supplied allowance labeled as such, and
the R2a addendum should set that allowance on structural grounds. The runtime envelope total is
measured per run (the hermetic figure here uses a fake payload; the inventory class grows with the
real import closure), never frozen as a single constant.

## Proposed per-class ceilings — RATIFIED by v1.20 (2026-07-18) at exactly these values

Plan §4.4 asked R2 to propose separate ceilings; freezing them was the R2a author act, completed in
prereg addendum **v1.20** (D49), which ratified exactly the values proposed here as exact bytes —
runtime-envelope/static-artifact per-file 33,554,432; event stream 33,554,432; stdout 16,777,216;
stderr 16,777,216; complete per-run bundle 134,217,728 — and fixed each ceiling's scope, the
counting rules, and the candidate-record overflow decision. The original proposal text, preserved:
each holds at least threefold headroom over the corresponding measured or derived figure so a
legitimate complete run can never collide with a ceiling: attestation manifests 32 MiB; event
streams 32 MiB; stdout 16 MiB and stderr 16 MiB; complete bundle 128 MiB. If any future measurement
exceeds a ceiling, the resolution is a larger ceiling in a later versioned addendum, never reduced
completeness.
