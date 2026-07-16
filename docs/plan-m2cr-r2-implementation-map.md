# M2cR milestone R2 — implementation map (requirement, artifact, test)

**Status: R2 working document, 2026-07-16.** The authoritative specification is
`docs/plan-post-d45-m2cr.md` (sha256 `51b8ec602bc955a619432fd1097012efbfa795e4bccb0a2cc7830d07e1aefbf7`),
which governs over this map on every detail, together with the R1 contracts (prereg addendum v1.19 and the
committed schemas). This map records how each R2 obligation is discharged and which files are protected.
It freezes nothing and authorizes nothing.

## Scope rule

R2 implements exactly the plan §8 R2 enumeration, hermetically: no `--execute`, no scientific or
diagnostic run, no real-model evaluation, no Mauna or holdout access, no new MAP/optimizer/gradient/
Hessian/HMC/VI/sampler execution on scientific models. The full executable suite runs (plan §8); its
pre-existing hermetic tiny-E1 regressions run unchanged as part of that suite. The orchestrator-v2
composition with the §6.2 gradient battery is not in the §8 R2 enumeration and is deferred with the
protocol work it depends on (§6 is frozen in R3); R2 ships the battery **record** builder and its
schema-conformance tests because prereg v1.19 §9 assigns those invariants to R2.

## Requirement matrix

| # | Obligation (authority) | Artifact | Test |
|---|---|---|---|
| 1 | v2 gates as reimplementations with full attempt capture: `optimize_conditional_v2`, `curvature_gate_v2`, importing frozen constants from `m2c_freeze.py`; `profile_integration.py` byte-identical (plan §3.2, B13) | `bistar_gp/m2cr/gates_v2.py` | `tests/test_m2cr_gates_v2.py` |
| 2 | Frozen-behavior equivalence: differential frozen-vs-v2 on existing synthetic oracles plus rigged oracles forcing each restart/retry/failure path, including status-0/success-False retry via fake minimizer, malformed-output fallback, nonstationary retries; verdict fields identical, bit-identical where deterministic; v2 additionally exposes discarded attempts (plan §3.2) | same | `tests/test_m2cr_gates_v2_equivalence.py` |
| 3 | Positive retry-acceptance predicate with per-conjunct outcomes (plan §3.2, §6.3 row 4) | `gates_v2.py` retry telemetry | equivalence + record tests |
| 4 | Write-ahead event stream: `STAGE_BEGIN/END`, `NODE_BEGIN/END`, `ATTEMPT_BEGIN`, `EVAL_RESULT`, `RETRY_BEGIN`, `ATTEMPT_END`; line-delimited, per-line flush, parent-owned unbuffered pipe; balanced stream required for COMPLETED, partial admitted for ABORTED_BUDGET / INFRA_FAILURE (plan §3.2) | `bistar_gp/m2cr/events.py` | `tests/test_m2cr_events.py` |
| 5 | Record emission per the R1 Layer-2 contract: per-node record, two-start optimizer record with per-start `attempts`, curvature record with pre/post-retry evaluations and tagged retry union, warm-start identities, battery record builder, canonical `(ls, os, lv)` persistence (v1.19 §9; schema `$defs`) | `bistar_gp/m2cr/records.py` | `tests/test_m2cr_records.py` validating through JSON Pointer `#/$defs/per_node_record` et al. |
| 6 | R2-assigned invariants: battery aggregate pass equals the conjunction of the three coordinate passes; jitter `resulting_start == base_start + jitter_vector`; `restart_count` equals the number of starts carrying a restart attempt; permutation and matrix conjugation tested in both directions (v1.19 §9) | `records.py`, `coordinates.py` | `tests/test_m2cr_records.py`, `tests/test_m2cr_coordinates.py` |
| 7 | Coordinate semantics: role map with exactly one site per role or STOP (`base_kernel.lengthscale` as `ls`, `outputscale` as `os`, `kernels.1.variance` as `lv`); computation in E1 storage order, persistence canonical (plan §3.3, B1) | `bistar_gp/m2cr/coordinates.py` | `tests/test_m2cr_coordinates.py` |
| 8 | Nonfinite serialization: frozen sentinels, element-level rule, canonical serialization (sorted keys, compact separators, UTF-8, `allow_nan=False`) (plan §5.4) | `bistar_gp/m2cr/serialization.py` | `tests/test_m2cr_serialization.py` |
| 9 | Hermetic §5.4 completeness test, non-self-certifying: dual inventory (schema walk vs emitted fields) matching exactly in both directions; every nonfinite kind forced through rigged oracles; hand-written golden serializations; negative cases (unknown field, malformed sentinel, sentinel in finite-only position, raw nonfinite literal) (plan §5.4) | test-only | `tests/test_m2cr_nonfinite_completeness.py` |
| 10 | Capture driver and spawn boundary: `prelaunch.json`, child hello as first act, atomic `spawned.json`, terminal-state precedence rules 1–5, grace policy SIGTERM then 30 s then SIGKILL, parent record assembly from flushed evidence, reconciliation mode flagged `reconstructed: true`, frozen write order Layer 2 then 3 then 4 via write-temp, fsync, atomic rename, `RAW_MANIFEST.sha256` excluding itself and the terminal record (plan §3.1, §4.3, B2, B10) | `bistar_gp/m2cr/capture.py` | `tests/test_m2cr_capture.py` |
| 11 | Terminal records: five-status assembly, per-kind standing, stage records and aggregates, evidence blocks; schema-valid against `m2c_execution_record.schema_v1.json` (plan §4.3, §5.3; R1 schema) | `capture.py` + `records.py` | `tests/test_m2cr_terminal_records.py` |
| 12 | Payload-boundary enforceability, fail-closed and hermetically proven with spies/fakes: attestations complete before the marker; marker atomic, durable, hash-bound to authorization id, launch-attempt id, execution commit, and frozen chain; no data generation, MAP construction, model evaluation, diagnostic evaluation, or result payload before the marker; first scientific operation follows without another unrecorded phase; missing, malformed, late, or mismatched markers fail closed (plan §4.3 hard R2 obligation; v1.19 §7) | `bistar_gp/m2cr/payload_boundary.py` | `tests/test_m2cr_payload_boundary.py` |
| 13 | B14-stack v5 child bootstrap machinery, hermetically tested with fakes and tmp manifests (the real four-root wiring and native-stack attestation run at a future authorized launch from its regenerated freeze): launch flags `-S -s -P -B -X pycache_prefix`, `-I`/`-E` prohibited, absolute resolved interpreter, `shell=False`, pinned CWD; effect proofs via explicit `SystemExit` (never `assert`, never `exit(...)`); bound sentinel `__hash__` check; complete `sys.path` replacement with the four roots; staged dual-view environment attestation (Stage A exact, Stage B two frozen deltas only, Stage C own-baseline) via `os.environ` and raw C `environ` (`_NSGetEnviron`, duplicate keys rejected); orphan/legacy `.pyc` rejection; `SourcelessFileLoader` rejection; audit hook plus canary; import inventory with resolved origin and loader class; thread controls set to 10 intra-op and inter-op, failing closed; post-execution re-attestation with parent-side rehashing preferred (plan §4.5, B14) | `bistar_gp/m2cr/bootstrap.py` + `capture.py` | `tests/test_m2cr_bootstrap.py` (real hermetic subprocess launches with fake payloads; no scientific computation) |
| 14 | Environment-freeze artifacts (Layer 0): exact frozen child-environment mapping; complete importable-artifact manifest over the four roots under the B15(ii) scope (normal `__pycache__` entries excluded; orphan, legacy, sourceless, importable-archive candidates included; catches an added `numpy/_distributor_init_local.py`); interpreter pin (version string plus resolved-target sha256, re-attested now, not inherited); pre-boundary attestation set; aggregating environment-freeze manifest carrying the single chain digest (plan §3.1, §4.5.7, §4.5.12; v1.19 §2, §5) | `bistar_gp/m2cr/environment_freeze.py` generators; committed artifacts under `docs/m2c_freeze/` | `tests/test_m2cr_environment_freeze.py` |
| 15 | Dependency lock, supplementary only: pip-freeze text, dist-info RECORD digests, binary-extension sha256, with the caveat recorded that RECORD is not a completeness manifest and does not cover `.pyc` (plan §4.5.7) | committed lock artifact + generator | freeze tests |
| 16 | INFRASTRUCTURE manifest (Layer 1a): pins sha256 of every R2 Layer-0 artifact, including the aggregating environment-freeze manifest, and additionally pins the two R1-authored schemas; never the R3 diagnostic schema; acyclic (plan §3.1) | `docs/m2c_freeze/m2cr_infrastructure_manifest_v1.json` | `tests/test_m2cr_infrastructure_manifest.py` |
| 17 | Audit tooling: ledger validation (event ordering, unique ids, legal transitions, consumption derived only from a payload-start event, D45 historical entry excluded from prospective derivation), chain-member verification against committed artifacts, terminal-record schema validation, bit-exact `sum` identity for band masses (plan §4.3, §5.2, §5.5) | `bistar_gp/m2cr/audit.py` | `tests/test_m2cr_audit.py` |
| 18 | Crash and interruption preservation: child SIGKILL mid-stream preserves `events.jsonl` up to the last flushed line and yields INFRA_FAILURE; parent budget kill yields ABORTED_BUDGET even when capture faults follow; parent death leaves `prelaunch.json`/`spawned.json` plus raw files and reconciliation assembles a flagged record; no confirmed spawn yields NOT_STARTED (plan §3.2, §4.3, §8) | `capture.py` + `events.py` | `tests/test_m2cr_capture.py` crash/interruption cases |
| 19 | Evidence-size measurement feeding B15(ii): exact importable-manifest measurement, exact per-event and per-record byte sizes from hermetic runs, complete-bundle components derived at the B7 node count with derivations labeled derived; no ceiling frozen here (plan §4.4, §4.5.12, §8; R2a is a separate author act) | `bistar_gp/m2cr/measure.py`; report `docs/m2cr-r2-evidence-size-report.md` | `tests/test_m2cr_measure.py` |
| 20 | Full executable suite (plan §8) | — | `python -m pytest -q`; baseline 442 passed, 1 skipped recorded pre-edit; final integrated tree 701 passed, 2 skipped (both remaining skips are the opt-in real-root walk and the pre-existing baseline skip) |

## Protected files (byte-identical throughout R2)

- `docs/plan-post-d45-m2cr.md` (authoritative plan)
- `docs/m2c-freeze-package-PROPOSAL.md` (rev-5; sha256 `c3e9db66e189b2a8cad19bf11b5c4acc6518d4b6d2597ae93b0f700587d1ce3f`)
- `docs/prereg-addenda-d19.md` (R2 appends no addendum; the B15(ii) ceilings addendum is R2a, a later author act)
- `docs/m2c_freeze/gtoy_profile_freeze_v1.17.json` (canonical hash `65381bc774e894dd9aaf2207cadd9cfa2f2735dafceff4bb39492086a9e522e2`)
- `docs/m2c_freeze/gtoy_profile_result_v1.18.schema.json`; the result-instance path `docs/m2c_freeze/gtoy_profile_result_v1.18.json` stays absent
- `docs/m2c_freeze/m2c_execution_record.schema_v1.json`, `docs/m2c_freeze/m2c_authorization_ledger.schema_v1.json`, `docs/m2c_freeze/m2c_authorization_ledger.jsonl` (R1 artifacts; immutable; R2 appends no ledger event because no grant is issued and no launch occurs)
- every existing `bistar_gp/*.py` source, in particular `bistar_gp/profile_integration.py` and `bistar_gp/m2c_freeze.py`
- every existing test, in particular `tests/test_m2c_manifest.py` (the v1.17 manifest CI)
- `experiments/` in full; `runs/` never staged

## Known provenance note

The R2 authorization prompt instructed verification of a rev-5 sha256 ending `…0957308a2ff7df`. The
committed rev-5 file and the plan agree at both citation sites (§1 line 33 and §12 line 904) on the
true digest `c3e9db66e189b2a8cad19bf11b5c4acc6518d4b6d2597ae93b0f700587d1ce3f`, which the file
matches byte-exactly and every prior record (prereg v1.17, D40-D47, R1's precondition check)
confirms; the prompt's value appears nowhere in the repository, and its suffix coincides with the
D46 historical plan hash `d9e85a41…0957308a2ff7df`, so the authorization prompt inherited a splice.
An earlier revision of this note wrongly located that splice inside the plan's §12; round-2 review
caught the misstatement, and the plan needs no correction anywhere. The startup gate's intent
(rev-5 unchanged since D40 ratification) holds and was verified against the true digest.
