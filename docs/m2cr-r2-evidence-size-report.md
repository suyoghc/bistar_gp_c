# M2cR R2 — evidence-size measurement report (B15(ii))

**Status: measurement report, 2026-07-16. Nothing here is frozen.** Plan §4.4 defers every exact
numeric ceiling to a versioned pre-execution addendum before R4 (milestone R2a, a separate author
act); this report supplies the measurements and derivations that addendum will draw on, and the
proposals at the end carry no force. Completeness is never weakened to fit a ceiling, and overflow
handling stays `INFRA_FAILURE`, never truncation (B15(iii)).

Every figure below is labeled either **measured** (an exact byte count of a real artifact or a
hermetic serialization) or **derived** (a formula over measured components; plan §4.4 requires the
derivation to be named where it derives). The measurement tooling is
`bistar_gp/m2cr/measure.py`; per-record and per-event figures come from hermetic rigged-oracle runs
of the v2 gates under the canonical serializer with the frozen nonfinite sentinels.

## Measured — committed freeze artifacts

| Artifact | Bytes | Notes |
|---|---|---|
| `m2cr_importable_artifact_manifest_v1.jsonl` | 7,625,848 | 39,967 entries: 39,389 source, 564 extension, 12 orphan-bytecode, 2 importable-archive |
| `m2cr_dependency_lock_v1.json` | 57,417 | supplementary only |
| `m2cr_infrastructure_manifest_v1.json` | 3,046 | Layer 1a |
| `m2cr_preboundary_attestation_set_v1.json` | 3,032 | includes the dyld main cache plus its twelve declared subcaches |
| `m2cr_environment_freeze_manifest_v1.json` | 903 | the aggregating manifest; its file sha256 is the chain member |
| `m2cr_child_env_mapping_v1.json` | 602 | |
| `m2cr_interpreter_pin_v1.json` | 383 | |

The plan §4.5.12 ratification-time estimates (roughly 78,890 entries and about 12 MB under the
B15(ii) scope) were explicitly "not the R2 measurement". The measured inventory is smaller for
three reasons: the walker attributes each artifact to exactly one root (`lib-dynload` and
`site-packages` are subdirectories of the stdlib root, so a naive four-root walk double-counts
them), the worktree portion is generated from a fresh detached worktree containing only committed
content, and the B15(ii) scope excludes normal source-backed `__pycache__` entries while retaining
the twelve orphan-bytecode candidates that exist in the shared Miniconda base. Deterministic
chunking is permitted by §4.4 but unnecessary at these sizes; every artifact is committed as one
file.

## Measured — per-node records and event stream (hermetic)

Canonical serialization of schema-valid Layer-2 per-node records built from rigged three-coordinate
oracles, worst-known-case variants included:

| Item | Bytes | Basis |
|---|---|---|
| Accepted node, no restart, no retry | 3,179 | measured |
| Failed node (optimizer gate failure) | 1,613 | measured |
| Accepted node with a fired retry (pre- and post-retry evaluations) | 4,857 | measured |
| Write-ahead events per clean node (9 events) | 2,280 | measured |
| Smallest single event line | 44 | measured |
| Largest single event line (optimizer EVAL_RESULT) | 540 | measured |

A restarted start adds one attempt object with jitter provenance to its optimizer record and three
event lines; a fired retry adds the post-retry evaluation and the retry union to the curvature
record (the 4,857-byte variant above) plus two event lines.

## Derived — full-closure projections

The B7 probe closure has at most about 1,481 unique nodes (plan §6.1); the node count enters every
projection as a parameter, not a constant.

| Quantity | Bytes | Derivation (labeled derived) |
|---|---|---|
| Per-node records, all nodes | 7,193,217 | derived: 4,857 (worst-case measured per-node record) × 1,481 |
| Event stream, all nodes | 3,376,680 | derived: 2,280 (measured clean-node events) × 1,481 |
| Complete bundle | 18,261,128 | derived: fixed measured artifact bytes (7,691,231) + both per-node products |

These derivations deliberately price every node at the worst measured per-node variant, so they sit
above any realistic clean run. They exclude stdout/stderr, which have no hermetic measurement basis:
the frozen orchestrator emits no per-node stdout, so realized stdout/stderr content is expected to
be dominated by interpreter and library banners plus attestation summaries, and the R2a addendum
should treat that class on structural grounds rather than on a measured figure.

## Proposed per-class ceilings — NOT FROZEN, no force

Plan §4.4 asks R2 to propose separate ceilings; freezing them is the R2a author act. Proposals,
each holding at least fourfold headroom over the corresponding measured or derived figure so that a
legitimate complete run can never collide with a ceiling: attestation manifests 32 MiB; event
streams 32 MiB; stdout 16 MiB and stderr 16 MiB; complete bundle 128 MiB. If any future measurement
exceeds a proposal, the resolution is a larger ceiling in the R2a addendum, never reduced
completeness.
