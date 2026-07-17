# M2cR R2 continuous-hardening design note (external-audit findings 1–6)

Working design note for the improvement cycle that follows the external exact-head
audit at `bd1d0f9`. Starting HEAD `0b7c596`. **Not** a freeze, R2a, R3, or execution
grant. This note records root causes, the shared redesign, the files expected to
change, the protected files that stay byte-identical, and any contract question —
before coding, per the cycle instructions.

## Root causes

- **Findings 1–3 share one root cause:** `capture_run` consumes a *mixture* of
  authenticated committed values and **caller-authored static values**. Today it
  derives the native-stack expectations and the dependency lock from the committed
  infrastructure manifest under the launch worktree (chain-bound), but it still
  trusts the caller `LaunchConfig` for the frozen environment mapping
  (`frozen_env`), the interpreter path and flags, and the pre-boundary attestation
  set — the latter defaulting to `None` (skippable) with production-reachable skip
  tokens. The importable-artifact manifest and the four roots ride on the mutable
  bootstrap template as an *optional* child directive. So a directly-constructed
  `LaunchConfig` can (F2) add an unrelated environment variable to both the child
  and its expected mapping, supply `preboundary_attestation_set=None`, or use skip
  tokens; (F1) omit the importable manifest so the completeness re-walks and
  origin/loader authentication never run; and (F3) supply the bound sentinel hash
  its own environment observes rather than a committed expectation.
- **Finding 4** is a wording question, not a code defect: the protected R1 schema
  freezes `candidate_vector` as the retry optimizer's RAW output "at whatever shape
  it came back," which is exactly the current unpermuted behavior.
- **Finding 5** is an internal inconsistency in the evidence-size report: the
  "complete bundle" line is labelled *measured* but omits the runtime-envelope
  evidence classes the report itself lists as excluded.
- **Finding 6** is an API-truthfulness gap: `capture_run` can swallow an `OSError`
  from terminal publication and return an in-memory record as though it were
  durably committed.

## Shared redesign — one authenticated launch authority (PROPOSED; only partly built this cycle)

> **Status:** this section describes the TARGET redesign for findings 1–3. As of this cycle only
> WI3 (the sentinel, a static fact already flowing through the existing derive/bind path) is
> implemented; the `AuthenticatedLaunchSpec` mechanism below is NOT yet built (finding 2 remains
> open, finding 1 deferred — see "Landed this cycle" and the cost finding). Read this as the plan
> for the next cycle, not a description of the current code.

Findings 1–3 are fixed together by a single target invariant:

> Every static fact capable of affecting pre-boundary execution or certification is
> derived from one authenticated committed artifact graph inside the trusted parent
> boundary. The caller supplies run-specific identity and routing inputs, not
> expected security values.

Proposed mechanism (not yet built): a new frozen `AuthenticatedLaunchSpec` produced by
`_authenticate_launch_spec(worktree_root, chain)`, which extends the existing
`_derive_authenticated_bundle` scaffolding. From the chain-bound infrastructure
manifest under the launch worktree it authenticates **every** Layer-0 pin
(`child_env_mapping`, `interpreter_pin`, `importable_artifact_manifest`,
`preboundary_attestation_set`, `native_stack_expectations`, `dependency_lock`, and
the aggregating `environment_freeze_manifest`) and derives from them: the frozen
environment mapping, the interpreter path + resolved-target digest + the frozen
flag set, the canonical four roots (from the importable-manifest v2 header), the
importable-manifest path, the pre-boundary attestation-set path, the seven
mandatory attestation directives, the build-pinned sentinel hash, and the
dependency lock + site-packages root.

`capture_run` then uses the **spec** for all static facts and ignores/rejects the
caller `LaunchConfig`'s static fields. The caller keeps only run-specific identity
and routing: `run_dir`, `run_id`, `launch_attempt_id`, `authorization_id`,
`record_kind`, the already-governed `chain`, `worktree_root` (which worktree to
launch from — the chain's infra digest fails closed on the wrong one), the
test-only `waiter`, and payload selection via the template. The spec is **not** a
freely constructible trust token: it is only ever produced by deriving and checking
committed bytes.

- **Work item 1 (mandatory manifest):** the importable-artifact manifest path and
  the four roots are derived from the authenticated graph and injected into the
  child directive unconditionally; the child requires the manifest, performs the
  complete pre-import and post-execution re-walks, and authenticates every executed
  file-backed module's origin and loader. A caller/template substitution of the
  manifest path or the roots is rejected. `payload_started` is impossible before the
  pre-walk; `COMPLETED` is impossible without the post-walk and origin/loader checks.
- **Work item 2 (environment/interpreter/pre-boundary):** the frozen environment
  mapping, interpreter path/flags, and pre-boundary set are all derived; production
  skip tokens are removed; the pre-boundary set is required before spawn and repeated
  parent-side after exit.
- **Work item 3 (sentinel hash):** the build-pinned bound `sentinel.__hash__()` value
  is stored in the committed native-stack expectations artifact (keeping launch
  expectations coherent in one artifact — no ninth artifact), derived parent-side,
  bound into the consumed bootstrap config as a mandatory directive, required
  child-side, and re-checked where the post-execution effect proofs repeat.

## Test-harness consequence

The `_make_launch` fake bundle must now provide a *complete authenticated synthetic
four-root inventory* that exercises the real enforcement path — not a caller
`LaunchConfig` with hand-supplied static fields. The synthetic worktree gains a fake
`child_env_mapping`, `interpreter_pin` (naming the real hermetic interpreter, whose
digest is genuine), a v2 importable manifest over the synthetic four roots, and a
pre-boundary attestation set with fixture-sized authenticated interpreter/dyld
stand-ins plus the genuine worktree closure. No test reaches the marker via
`preboundary_attestation_set=None` or production skip tokens. A separate, slower
integration test may walk real roots; the fast synthetic battery still proves the
manifest is mandatory and consumed.

## Work items 4–6 (independent of the launch-authority redesign)

- **4 (retry candidate):** Option A (minimal clarification). Keep `candidate_vector`
  as exact raw flattened optimizer output; document it explicitly as a
  field-specific exception to canonical-axis persistence; add a discriminating
  asymmetric test (raw candidate vs canonical gradient under a non-identity storage
  permutation); ensure nothing calls it canonical. No schema change — Option B
  (a versioned record-contract successor) is not warranted for an explainable
  field-specific exception.
- **5 (evidence bundle):** measure every bounded fixed runtime evidence class from
  hermetic capture output; keep per-node/per-event worst-case exemplars; represent
  stdout/stderr only as explicit caller-supplied unmeasured allowances; include all
  components in the projection; distinguish static freeze-artifact storage from
  per-run evidence-bundle storage; relabel the "complete bundle"; keep every ceiling
  non-binding (R2a is the only future freezing act). Add a test that fails if a
  `RUN_DIR_LAYOUT` evidence class is absent from the measurement inventory without an
  explicit classification+reason.
- **6 (terminal publication):** make `capture_run`'s return contract truthful. A
  normal record is returned only when it is the authoritative no-clobber record and
  its required durability was confirmed. Distinguish publication-failed-before-final
  (raise a typed `TerminalPublicationError` carrying the attempted record + cause),
  another-valid-winner (return that record), directory-fsync-uncertain (explicit
  publication-uncertain surface), confirmed-durable, and malformed-occupant.
  Hardening-round-2 refinement (Codex): the shared `_race_winner_or_raise` returns an
  EEXIST occupant ONLY when it is a schema-valid terminal record bound to THIS run
  (`validate_terminal_record` + matching `run_id`/`launch_attempt_id`/`chain`); a
  canonical-but-schema-invalid or wrong-run occupant is a §4.5.13 squatter surfaced as
  a `TerminalWriteError`, so `capture_run` always returns a schema-valid record or
  raises, never a non-record. The winner path fsyncs the run directory before
  returning (a racing publisher may have linked the name but not yet fsync'd), raising
  `TerminalDurabilityUncertain` if that cannot be confirmed. `reconcile_run` keeps its
  distinct refuse-on-any-existing-terminal contract (it raises `TerminalAlreadyExists`,
  a `RecordAssemblyError`, rather than reconstructing over an occupied name).

## Files expected to change

- `bistar_gp/m2cr/capture.py` — launch authority (spec), mandatory manifest wiring,
  publication truthfulness.
- `bistar_gp/m2cr/bootstrap.py` — mandatory manifest directive; sentinel directive;
  child-side requirement.
- `bistar_gp/m2cr/environment_freeze.py` — add the build-pinned sentinel hash to the
  native-stack expectations generator.
- `bistar_gp/m2cr/records.py` — retry candidate documentation only (no behavior
  change).
- `bistar_gp/m2cr/measure.py` + `docs/m2cr-r2-evidence-size-report.md` — bundle
  measurement completeness.
- `tests/test_m2cr_*.py` — harness rebuild + discriminating/equivalence tests.
- Regenerated freeze artifacts (native-stack expectations gains the sentinel field;
  infra/env/importable/preboundary re-pin as usual) — once, after code is stable.
- `Notes/DECISIONS.md`, `Notes/SCRATCHPAD.md`, `docs/plan-m2cr-r2-implementation-map.md`
  — truthful state.

## Protected files that stay byte-identical

`docs/plan-post-d45-m2cr.md`, `docs/m2c-freeze-package-PROPOSAL.md`,
`docs/prereg-addenda-d19.md`, `docs/m2c_freeze/gtoy_profile_freeze_v1.17.json`,
`docs/m2c_freeze/gtoy_profile_result_v1.18.schema.json` (and the absent
`…result_v1.18.json`), both R1 schemas + the ledger JSONL, every pre-existing
`bistar_gp/*.py` top-level source (esp. `profile_integration.py`, `m2c_freeze.py`),
every pre-R2 test, `experiments/` in full, nothing under `runs/`.

## Cost finding that shapes the cycle sequencing (measured at HEAD)

A hermetic child loads exactly **66 file-backed real-stdlib modules** (51 stdlib
`.py`, 15 `lib-dynload` `.so`, 0 site-packages — it uses the fake worktree stack).
Their `sys.modules` origins are fixed to the real stdlib (loaded before the child's
`sys.path` replacement), so the child's origin/loader binding (§4.5.7) genuinely
requires the four roots to include the **real** stdlib/lib-dynload. A real-root
importable walk is ~11.7 s, so a mandatory-manifest child launch (pre- + post-walk)
costs ~12–23 s. That is prohibitive for the fast synthetic battery (~30 child
launches), and it is the exact tension the author flagged ("keep real-root walking
separate from the fast synthetic battery").

Consequence for sequencing: the importable-manifest **child re-walk/origin binding**
(work item 1's child side) needs a dedicated test-infrastructure investment
(session-cached host manifest + a small number of isolated real-root integration
launches), so it is the natural next cycle. Every OTHER static-authority fact —
frozen environment, interpreter, four roots (header only, cheap), pre-boundary set
(fixture-sized dyld stand-ins, cheap), sentinel hash, expectations, dependency lock —
is derivable and enforceable WITHOUT the real-root walk, but the full env/interpreter/
pre-boundary derivation (WI2) is a bounded harness rebuild that shares the launch-spec
machinery with WI1, so this cycle lands the self-contained items and schedules WI1+WI2
together for the next cycle.

**Landed this cycle (accurate — corrected after the hardening-review round):**
- **WI4 / finding 4** — retry-candidate clarification (records.py comment + asymmetric test).
- **WI6 / finding 6** — truthful terminal-publication states (typed publication hierarchy).
- **WI3 / finding 3** — build-pinned sentinel hash derived from the committed expectations.
- **WI5 / finding 5** — complete per-run evidence-bundle measurement + RUN_DIR_LAYOUT coverage.

**ADVANCED but NOT landed — finding 2 (BLOCKER) is still OPEN:** the parent already derives the
native-stack expectations, dependency lock, importable-manifest header roots, and (this cycle)
the sentinel from the chain-bound committed infrastructure manifest. But `capture_run` STILL
trusts the caller `LaunchConfig` for `frozen_env`, `interpreter_path`/`interpreter_flags`, and
`preboundary_attestation_set` (which still defaults to `None`/skippable with the
`{"interpreter","dyld"}` skip tokens present). So WI2's authenticated environment/interpreter/
pre-boundary derivation is NOT implemented, the skip tokens are NOT removed, and the
`AuthenticatedLaunchSpec` / `_authenticate_launch_spec` described in the "Shared redesign" section
above is a **PROPOSED mechanism for the next cycle, not yet built**. Finding 2 is not closed.

**Deferred (documented next cycle) — finding 1 (BLOCKER):** WI1's child-side mandatory
importable-manifest re-walk + origin/loader binding on the production launch path, and its
isolated real-root integration tests; landed together with the full WI2 harness rebuild.

## Contract questions

- **No protected-schema change is required.** Work item 4 resolves to Option A (a
  documentation clarification of an already-frozen field), so the R1 execution-record
  schema is untouched.
- The native-stack expectations artifact is **R2 Layer-0 content**, not a protected
  historical schema; adding the sentinel-hash field to it is an ordinary R2 artifact
  evolution (it already gained its current shape in D48 Update 8), regenerated and
  re-pinned, not a protected-contract amendment.
