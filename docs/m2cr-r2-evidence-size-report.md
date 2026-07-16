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
| `m2cr_importable_artifact_manifest_v1.jsonl` | 8,743,897 | format v2 (roots header, per-entry loader); 39,955 entries: 39,389 source, 564 extension, 2 importable-archive, 0 orphan-bytecode |
| `m2cr_dependency_lock_v1.json` | 57,417 | supplementary only |
| `m2cr_preboundary_attestation_set_v1.json` | 3,032 | dyld main cache plus its twelve declared subcaches, interpreter, bootstrap closure |
| `m2cr_infrastructure_manifest_v1.json` | 2,702 | Layer 1a; repo-relative pins |
| `m2cr_environment_freeze_manifest_v1.json` | 731 | the aggregating manifest; its file sha256 is the chain member |
| `m2cr_child_env_mapping_v1.json` | 602 | includes the concrete frozen `PATH` |
| `m2cr_interpreter_pin_v1.json` | 383 | version string plus resolved-target sha256 |

Fixed-artifact total: **8,808,764 bytes** (measured).

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
plan §4.3); a launch against a stale header fails closed on the missing path, never open.

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

| Quantity | Bytes | Derivation (labeled derived) |
|---|---|---|
| Per-node records, all nodes at the structural worst case | 8,729,014 | derived: 5,894 × 1,481 |
| Event stream, all nodes at the structural worst case | 9,016,328 | derived: 6,088 × 1,481 |
| Fixed freeze artifacts | 8,808,764 | measured (sum above) |
| Complete bundle, evidence classes with measured bases | 26,554,106 | derived: fixed total + both per-node products |

The projection prices every node at the structural worst-case exemplar (both starts restarted, retry
fired). It is **not** a proven upper bound over all runs, because the `message` string is unbounded
(external audit F8); R2a sets each ceiling with headroom over these figures so an enlarged `message`
cannot collide with a limit, and if any future measurement exceeds a figure the resolution is a
larger ceiling, never reduced completeness. Runtime envelope files (prelaunch, spawned, marker,
attestations, inventory, `RAW_MANIFEST.sha256`, terminal record) measure a few kilobytes each in
hermetic capture runs and enter `derive_bundle_projection` as explicit fixed classes. stdout/stderr
have no hermetic measurement basis; the measurement API represents them only as a caller-supplied
allowance labeled as such, never as a measured claim, and the R2a addendum should set that allowance
on structural grounds.

## Proposed per-class ceilings — NOT FROZEN, no force

Plan §4.4 asks R2 to propose separate ceilings; freezing them is the R2a author act. Proposals, each
holding at least threefold headroom over the corresponding measured or derived figure so a
legitimate complete run can never collide with a ceiling: attestation manifests 32 MiB; event
streams 32 MiB; stdout 16 MiB and stderr 16 MiB; complete bundle 128 MiB. If any future measurement
exceeds a proposal, the resolution is a larger ceiling in the R2a addendum, never reduced
completeness.
