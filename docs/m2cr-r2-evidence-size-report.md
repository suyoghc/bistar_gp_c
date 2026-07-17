# M2cR R2 — evidence-size measurement report (B15(ii))

**Status: measurement report, 2026-07-16 (regenerated after the final-gate fix round). Nothing here
is frozen.** Plan §4.4 defers every exact numeric ceiling to a versioned pre-execution addendum
before R4 (milestone R2a, a separate author act); this report supplies the measurements and
derivations that addendum will draw on, and the proposals at the end carry no force. Completeness is
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
| `m2cr_importable_artifact_manifest_v1.jsonl` | 8,743,895 | format v2 (roots header, per-entry loader); 39,955 entries: 39,389 source, 564 extension, 2 importable-archive, 0 orphan-bytecode |
| `m2cr_dependency_lock_v1.json` | 57,451 | supplementary only; editable installs excluded from `pip_freeze` (external audit round-3 F4), reproducible at HEAD |
| `m2cr_preboundary_attestation_set_v1.json` | 14,825 | dyld main cache plus its twelve declared subcaches, interpreter, and the complete 76-entry pre-boundary bootstrap closure; the five worktree-origin closure pins are stored worktree-relative (F3), which is why the set is smaller than before |
| `m2cr_infrastructure_manifest_v1.json` | 2,872 | Layer 1a; repo-relative pins (now 7 artifacts incl. native-stack expectations) |
| `m2cr_native_stack_expectations_v1.json` | 12,314 | F1/F2 round-3 + finding 3: frozen native stack, profile hash, build-pinned bound sentinel `__hash__` (§4.5.8), backend build markers, Stage-B delta, and the 66-entry expected on-disk loaded-image set (path+sha256) |
| `m2cr_environment_freeze_manifest_v1.json` | 731 | the aggregating manifest; its file sha256 is the chain member |
| `m2cr_child_env_mapping_v1.json` | 602 | includes the concrete frozen `PATH` |
| `m2cr_interpreter_pin_v1.json` | 383 | version string plus resolved-target sha256 |

Fixed-artifact total: **8,833,073 bytes** (measured; regenerated after the external-audit
hardening cycle — WI3 adds the build-pinned sentinel hash to the native-stack expectations,
and the importable/preboundary/aggregating pins re-derive for the changed code; the F3
worktree-relative closure pins and the F4
editable-filtered lock carry over unchanged).

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
serialization of a specific rigged-oracle run, reproduced deterministically by
`tests/test_m2cr_measure.py::test_evidence_size_report_figures_reproduce` under the hermetic
harness; they are exemplars because one field is not length-bounded: the optimizer/retry `message`
is schema-typed `{"type": "string"}`
(a SciPy termination message), so a pathological minimizer could enlarge a record without changing
its structural path. R2a freezes ceilings with headroom precisely so the unbounded `message` cannot
collide with a limit; the derivations below therefore price a **structural worst case** (both starts
restarted, retry fired), not a proven maximum over all string content.

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

**Static freeze-artifact storage (one-time, committed):** Fixed-artifact total **8,833,073 bytes**
(the table above); it is NOT part of the per-run evidence bundle.

**Per-run evidence bundle (per launch) — components:**

| Component | Bytes | Basis (labeled) |
|---|---|---|
| Runtime envelope classes (`RUN_DIR_EVIDENCE_CLASSES` marks 19 `fixed_runtime` + the `conditional` `bootstrap_failure.json`; 17 were present in this hermetic run — `manifest_pre.json`/`manifest_post.json` are absent here because the fake bundle omits the importable-manifest directive, the deferred finding 1) | 61,340 | measured (hermetic capture via `measure_run_dir_fixed_evidence`; `import_inventory.json` dominates at 31,927 and scales with the real import closure) |
| Run-local scratch (`home/`, `tmp/`, `xdg/`) | (allowance) | any payload-written contents are Layer-3 raw-manifested, so represented as a caller-supplied allowance (unbounded, no hermetic basis), NOT assumed zero; `pycache/` alone is asserted empty (zero) |
| Per-node records, all nodes at the structural worst case | 8,729,014 | derived: 5,894 × 1,481 |
| Event stream, all nodes at the structural worst case | 9,016,328 | derived: 6,088 × 1,481 |
| stdout / stderr | (allowance) | caller-supplied allowance, labeled `measured: false`; no hermetic basis, never a measured claim |
| **Per-run evidence bundle, measured-basis subtotal** | **17,806,682** | derived: runtime envelopes + per-node product + per-event product |
| Per-run evidence bundle, complete | 17,806,682 + allowances | derived: measured-basis subtotal + caller-supplied stdout/stderr + run-local-scratch allowances |

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

## Proposed per-class ceilings — NOT FROZEN, no force

Plan §4.4 asks R2 to propose separate ceilings; freezing them is the R2a author act. Proposals, each
holding at least threefold headroom over the corresponding measured or derived figure so a
legitimate complete run can never collide with a ceiling: attestation manifests 32 MiB; event
streams 32 MiB; stdout 16 MiB and stderr 16 MiB; complete bundle 128 MiB. If any future measurement
exceeds a proposal, the resolution is a larger ceiling in the R2a addendum, never reduced
completeness.
