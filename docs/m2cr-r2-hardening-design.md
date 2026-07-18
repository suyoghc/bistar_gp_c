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

> **Status:** this section describes the TARGET redesign for findings 1–3. As of the previous cycle
> only WI3 (the sentinel, a static fact already flowing through the existing derive/bind path) was
> implemented; the `AuthenticatedLaunchSpec` mechanism below was NOT yet built (finding 2 remained
> open, finding 1 deferred — see "Landed this cycle" and the cost finding). The 2026-07-18
> launch-authority cycle implements WI1+WI2 against the derived matrix in "R2 launch-authority
> cycle (2026-07-18)" below; neither finding is claimed closed until its discriminating tests,
> real-root integration launches, regenerated artifacts, and the three-reviewer gate are complete.

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
committed bytes. Layering note: the spec factory enforces worktree/chain AGREEMENT;
whether a given chain was ever legitimately granted is the authorization-ledger and
audit-CI layer's determination (§5.2 verifies every chain member against the committed
artifacts at the authorized commit), and a caller who fabricates a complete bundle
plus a matching chain is performing a deliberate act outside the §4.5.13 threat model.

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

## R2 launch-authority cycle (2026-07-18) — derived requirement/implementation/test matrix

Working matrix for the WI1+WI2 implementation cycle authorized against findings 1 and 2 (the two
remaining external-audit BLOCKERs). Nothing here claims either finding closed; closure requires the
matrix's tests green, the bounded real-root integration launches green, regenerated artifacts, and a
clean three-reviewer gate at the reviewed production-code head. (Outcome: the panel's round-4
confirmatory delta was clean at code head `b673367`; the later `366b004…3071046` tail is
behavior-neutral — two test corrections, the artifacts they forced, and D48/SCRATCHPAD docs, with no
`bistar_gp/` change — and was verified by a separate one-shot Codex closure audit. See the round-4
and closure records below.)

### Refined cost measurement (2026-07-18, supersedes the walk-cost reading above where they differ)

The ~11.7 s four-root walk is site-packages-dominated. Measured at HEAD `46519af` with the frozen
walker semantics: real stdlib excluding the site-packages and lib-dynload subtrees, plus lib-dynload,
is **1,624 entries in 0.24 s**; the same walk with site-packages inside the stdlib root is **39,812
entries in 14.19 s**. Because the walker's nested-root exclusion is derived from the declared root
list, ANY child whose four roots include the real stdlib pays the site-packages walk (declared, it is
walked as its own root; undeclared, it is walked inside the stdlib root). Consequence: the fast
synthetic battery keeps fully synthetic four roots (walks in milliseconds), and the real-root cost is
confined to the dedicated integration launches.

### Origin/loader authority for modules outside the four roots (new derived rule)

Plan §4.5.7 binds every executed module's resolved origin and loader class to a frozen manifest
entry. A child of the pinned interpreter unavoidably loads ~66 real-stdlib file-backed modules before
`sys.path` replacement, so the strict all-under-roots form holds exactly when the four roots include
the real stdlib, which is the production configuration and the real-root integration configuration.
The enforcement rule is therefore split by scope, with no skip and no test-only branch:

- a file-backed loaded module whose resolved origin is under one of the four roots must match a
  manifest entry by `(root, relpath, sha256)` and loader class, else the child fails closed;
- a file-backed loaded module outside all four roots must match an entry of the authenticated
  pre-boundary bootstrap closure by exact path and sha256, with its loader class required to equal
  the frozen loader for its artifact type, else the child fails closed.

In production both clauses are backed by committed chain-bound artifacts and the second clause is
structurally redundant (the closure members are under the real stdlib root, so they also match the
manifest); in the synthetic battery the second clause is what authenticates the interpreter-forced
real-stdlib preloads without weakening either authority. The production manifest remains complete
over every importable artifact under all allowed roots; nothing narrows to "modules observed as
loaded".

### WI2 — authenticated launch spec

| Requirement | Implementation | Discriminating tests |
|---|---|---|
| One trusted-parent factory authenticates the complete committed Layer-0 graph under `worktree_root` and `chain` | `_authenticate_launch_spec(worktree_root, chain)` in capture.py, extending `_derive_authenticated_bundle`: infra manifest digest must equal `chain.infrastructure_manifest_sha256`; env-freeze manifest authenticated via its infra pin AND required to equal `chain.environment_freeze_manifest_sha256`; child-env mapping, importable manifest, interpreter pin, pre-boundary set authenticated via env-freeze pins; expectations + dependency lock via infra pins; returns one frozen `AuthenticatedLaunchSpec` | wrong worktree (no bundle), wrong chain digest, each artifact pin corrupted one at a time (7 artifacts), env-freeze vs chain disagreement; every failure is a pre-spawn INFRA_FAILURE with no marker |
| Spec carries every static fact | Spec fields: frozen env mapping; interpreter path + resolved-target digest + frozen flags; canonical four roots; importable-manifest path; pre-boundary set path + closure entries; all 8 attestation directives incl. sentinel; dependency lock + site-packages authority; bootstrap path; `spec_sha256` = canonical digest of the spec document | positive fake-bundle derivation asserts each field equals the committed artifact's value |
| Interpreter authenticated, not asserted | factory hashes `realpath(pin.path)` and requires equality with `pin.sha256` before any spawn | interpreter pin sha mismatch fails pre-spawn; missing interpreter fails pre-spawn (INFRA_FAILURE, not NOT_STARTED) |
| Caller cannot author expected security values | `LaunchConfig` loses `interpreter_path`, `interpreter_flags`, `frozen_env`, `bootstrap_path`, `preboundary_attestation_set`, `preboundary_skip`, `dependency_lock_path`, `site_packages`; remaining fields are identity/routing (`run_dir`, `run_id`, `launch_attempt_id`, `authorization_id`, `record_kind`, `chain`, `worktree_root`, ceiling, test-only `waiter`) | constructing `LaunchConfig` with any removed field raises `TypeError`; non-consumption is structural (the fields do not exist on the config, so no code path — direct, `asdict`, or `getattr` — can read them), proven by the field-set equality test |
| Caller substitutions rejected, not silently preferred | spec-authored template keys (`frozen_env`/`expected_frozen_env`, `four_roots`, `importable_artifact_manifest`, `authenticated_spec_sha256`, pre-boundary closure directive, all 8 directives) are compared against the template before injection; a conflicting value raises, a missing value is injected | one test per substitutable key: conflicting template value refuses the launch pre-spawn |
| Skip tokens and absent pre-boundary set unrepresentable | `verify_preboundary_attestation_set` loses its `skip` parameter; capture verifies the spec's set unconditionally pre-spawn and post-exit | signature test (no skip parameter); fixture-authored stand-in sets make every launch verify genuinely; absent/malformed set fails closed |
| Wall-clock ceiling bounded by the ratified constant | `wall_clock_ceiling_hours` stays caller-visible for tests but is validated: finite, positive, and at most `WALL_CLOCK_CEILING_HOURS` | ceiling above 8.0 h refused |
| Parent and child cannot consume different static authorities | template gains mandatory `authenticated_spec_sha256`; the parent writes it from the spec, records it in `prelaunch.json`, and the child records it in `effect_proofs.json` (an attestation whose digest the marker already binds); post-exit the parent re-reads `effect_proofs.json`, requires the recorded digest to equal the derived spec digest, and re-hashes every marker-listed attestation evidence file against the marker's digest list | doctored template spec digest refused pre-spawn; child launched with a mismatching argv config digest refuses; payload that rewrites a marker-bound attestation file is caught by the parent's post-exit evidence re-hash |

### WI1 — mandatory child manifest

| Requirement | Implementation | Discriminating tests |
|---|---|---|
| Manifest path + four roots derived only from the authenticated graph and injected unconditionally | capture injects `four_roots` (worktree slot = the launch worktree, host slots = manifest header) and `importable_artifact_manifest` from the spec into every template; conflicts rejected | template substitution of either key refused; roots reordered or duplicated fail (`_canonical_four_roots`, header comparison) |
| Bootstrap requires them before the payload marker | `main()` fails closed when `importable_artifact_manifest` or `four_roots` is missing, non-absolute, or (for the manifest) headerless v1; the optional `manifest_path is not None` branch is removed | config without the manifest directive exits `attestation_fault` before any native import and emits no marker |
| Complete pre-import re-walk gates the marker | existing `_verify_importable_artifact_manifest(..., phase="pre_audit")` becomes unconditional; its attestation joins the marker's required set | added, removed, and byte-changed artifact each fail before the marker (synthetic roots); marker file proven absent |
| Origin/loader authentication before payload start | new pre-marker check over current `sys.modules`: under-roots modules bind to manifest entries (sha + loader), outside-roots modules bind to the authenticated closure (path + sha + type-derived loader); recorded as a marker-required attestation | closure entry sha mismatch, module with no authority, loader-class mismatch each fail with no marker |
| Complete post-execution re-walk + origin/loader validation gate COMPLETED | existing post-walk + `_inventory` binding become unconditional, extended with the outside-roots closure clause; the child returns a protocol exit only after both | payload that mutates a root, loads an unlisted file-backed module, or strips the postcheck ends INFRA_FAILURE, never COMPLETED |
| Manifest omission/substitution/incomplete postcheck fail closed parent-side too | parent post-exit requires: the marker's attestation names to include the manifest pre-walk and origin-binding attestations, `manifest_post.json` present with its digest recorded in `stage_c.json`, and every marker-listed evidence file re-hashed | stripped `manifest_post.json`, doctored `stage_c.json` reference, and marker missing the mandatory names each yield INFRA_FAILURE |
| `numpy/_distributor_init_local.py`-style additions caught before execution | covered by the pre-walk completeness clause | synthetic site-packages plant of `numpy/_distributor_init_local.py` fails the pre-walk before any import of the planted file; real-root worktree plant covered by integration launch 2 |

### Test architecture (bounded real-root integration + fast synthetic battery)

| Requirement | Implementation |
|---|---|
| Session-scoped authenticated host-manifest fixture, generated independently before any test child starts | a pytest session fixture materializes a detached copy of the candidate tree (`git archive` of the current tracked tree), generates the full production-shaped bundle over the real four roots with the real generators, and caches it outside the repository |
| Cache keyed at least by candidate HEAD, interpreter digest, four roots, generator digest | cache directory keyed by sha256 over: the git tree id of the archived tree (equals the HEAD tree when the working tree is clean, so candidate HEAD is captured content-exactly), `sha256(realpath(interpreter))`, the canonical four-root list, and the sha256 of `environment_freeze.py` + `serialization.py`; any key mismatch regenerates |
| Child only consumes and verifies; it never generates its own expectation | manifests/expectations are generated by the fixture process (parent side, before any child starts); children re-walk and compare; loaded-image expectations keep the established two-probe unauthenticated measurement with test-side re-hashing |
| Positive and negative invocations are separate processes | each integration case is its own `capture_run` child launch in its own run directory |
| At most FOUR real-root integration launches | (1) complete positive production path over the real four roots ending COMPLETED; (2) pre-walk added-artifact failure before the marker (worktree plant); (3) post-execution mutation failure after the marker (COMPLETED impossible); (4) exercised as the real-root origin/loader negative: a manifest loader pin doctored to a conflicting concrete class over a consistently re-pinned bundle copy, surviving the parent's verification and the completeness re-walk (whose drift core excludes the loader annotation) and caught only by the child's pre-marker origin binding |
| Fast synthetic battery carries the mutation matrix without claiming the production path | `_make_launch` / `_launch_bootstrap` bundles gain the full eight-artifact fake authority (fake child-env mapping, interpreter pin naming the real interpreter with its genuine digest, fixture-sized pre-boundary set with genuine hashes and the genuine closure, entry-complete synthetic manifests); all mutation-matrix negatives run over synthetic roots in milliseconds |

### First real-native production-path launch — Stage-B KMP finding (2026-07-18)

The real-root integration battery's positive launch is the first time the complete production
path has ever executed with the real native stack (every prior child ran the fake torch/numpy
stack, whose fake torch SIMULATES the libomp registration). It immediately surfaced an empirical
over-read in the Stage-B classifier: on the frozen host, importing numpy+torch and running the
thread controls adds ONLY `__CF_USER_TEXT_ENCODING` to the raw C environment — libomp performs
its `__KMP_REGISTERED_LIB_<pid>` registration lazily, at its first parallel region, which a
hermetic no-computation child never reaches. The classifier required exactly one KMP entry and
therefore classified every genuine production-path launch as `environment_fault`.

Plan §4.5.5 Stage B is an ACCEPT-ONLY allowlist ("Accept **only** explicitly frozen
native-runtime deltas … **Any other delta is `INFRA_FAILURE`**"): it admits the PID-bound entry;
it does not mandate its occurrence, and the fail-closed direction is extra or malformed deltas,
not the non-occurrence of a lazy registration. `classify_stage_b_deltas` now accepts zero or one
PID-bound format-valid entry; two entries, a wrong-PID name, a malformed value, and any other
addition still fail closed, and the frozen `__CF_USER_TEXT_ENCODING` value rule is unchanged.
The plan's rationale sentence ("torch's libomp registers a PID-scoped …") recorded the 2026-07-15
probe's observation — that probe evidently reached a parallel region; the hermetic child does
not. No plan text changes; the classifier now implements the frozen acceptance rule exactly.

The same launches also fixed the loader-binding semantics against runtime reality. Two legitimate
CPython/library behaviors present a runtime loader of "none" on file-backed modules: C-extension
init code REGISTERS submodules that share the parent `.so`'s origin with no loader object
(`torch._C._autograd`), and libraries perform module-object surgery that replaces their own
`sys.modules` entries with custom module instances (`torch.backends`). The pinned loader class
exists to defeat a CONFLICTING loader (zipimport or sourceless smuggling always presents its
concrete class), so the rule is now: a concrete mismatch fails closed; a runtime "none" is
accepted AND recorded (`loader_binding: "unclaimed"`), upgraded to `"parent:<name>"` when a loaded
ancestor with the same resolved origin carries the pinned loader; the bytes remain
sha-authenticated either way and sourceless execution stays excluded by its dedicated scan. The
Stage-C image allowlist is now MEASURED rather than empty: the frozen payload class imports
`bistar_gp.profile_integration`, whose closure loads additional extension images after the Stage-B
baseline; the expectations generator enumerates exactly that delta with the same probe.

A second empirical finding from the same launch: `numpy.show_config()` — called by the child's
build-marker attestation BEFORE the Stage-B image measurement — lazily imports pyyaml, loading
`yaml/_yaml.cpython-313-darwin.so`; the freeze-time measurement probe enumerated its image set
BEFORE its own config-show calls, so the committed 66-image expectation was measured at the wrong
point in the sequence and every real child (67 images) failed authentication. The measurement now
replicates the child's exact pre-Stage-B sequence (build-configuration calls, then image
enumeration); the regenerated expectations artifact carries 67 images. Additionally, the child's
native import used `__import__(name, fromlist=["*"])`, whose `__all__` expansion imported extra
submodules the plain-importing measurement never loads; it now uses `importlib.import_module`, so
the child and the measurement load the same closure and the pre-marker import surface is strictly
smaller.

### Kimi K3 architecture challenge (2026-07-18) — adjudication record

One bounded fresh OpenRouter request (`moonshotai/kimi-k3`, maximum reasoning effort) challenged
the complete WI1/WI2 design plus the controlling plan sections; the first attempt returned an
empty keep-alive body (transport failure) and was retried exactly once. The retry returned 14
findings, each independently verified against the plan and source before any change. Kimi has no
vote; nothing below expands scope.

**Confirmed or partially confirmed, acted on:**

- **K2/K3 (split origin rule vs §4.5.7):** the outside-roots closure clause could admit the
  interpreter-forced preloads under an erroneously rooted freeze, and the production redundancy of
  the clause was asserted in prose only. Standing CI now ASSERTS the redundancy over the committed
  bundle: the committed manifest header's stdlib/lib-dynload/site-packages roots must equal the
  pinned interpreter's own `sysconfig` paths, and every committed closure member must resolve
  under the committed roots — so in the committed configuration the strict all-under-roots §4.5.7
  form is structural, the closure clause is unreachable, and an erroneously rooted freeze fails CI
  before any launch. The positive real-root launch additionally asserts `closure_bound == 0`.
- **K4 (import-then-evict):** a module imported and evicted from `sys.modules` between checkpoints
  cannot be origin-authenticated after the fact (the CPython import audit event does not carry the
  resolved origin). Recorded as a disclosed residual of the same §4.5.13 class as in-memory
  mutation; the inventory now records `import_events_without_module` so an eviction is visible in
  evidence rather than silently absorbed, and worktree reads remain covered by load-time
  open-hashing.
- **K5 (open-world config):** the child's consumed configuration is now CLOSED-WORLD
  (`KNOWN_CONFIG_KEYS`): any key outside the enumerated set — a legacy alias such as
  `preboundary_skip`, or a future directive the parent's substitution comparison does not yet
  cover — fails closed child-side before any consumption.
- **K6/K11 (fixture cache):** the session bundle cache is populated atomically (staging directory,
  `key.json` written last, atomic rename), and a cache hit is revalidated against live-host drift
  (dependency-lock semantics recomputed against the live site-packages plus a deterministic
  manifest-entry re-hash sample); every real-root negative asserts its SPECIFIC planted artifact
  so unrelated host drift cannot masquerade as a pass.
- **K7 (candidate provenance):** the fixture archives the `git stash create` tree, so uncommitted
  TRACKED changes are part of both the cache key and the launched code; the key document records
  head/dirty state explicitly.
- **K8 (nested-root coverage):** the production nesting geometry (site-packages physically inside
  the stdlib root) now has launch-level synthetic coverage: a positive nested-root launch and a
  boundary plant caught by the pre-walk under the inner root id, plus the existing walker unit
  test.
- **K9 (post-marker self-consistency):** the parent's exit checks now bind the postcheck CONTENT
  to the authenticated authority: `manifest_post.json` must attest exactly the spec's manifest
  digest with `entry_sets_identical` true, beyond the stage-C digest linkage. A payload
  consistently rewriting the whole post-marker pair remains the disclosed §4.5.13
  hostile-payload residual; parent-side full re-walking was rejected as duplicating the child
  walk at real-root cost.
- **K12 (grep-test weakness):** the matrix wording was replaced — non-consumption of caller
  static fields is structural (the fields no longer exist), not grep-asserted.
- **K14 (reserved launch):** the fourth real-root launch is now exercised as a loader-class
  corruption that survives the parent's verification and the completeness re-walk (whose drift
  core deliberately excludes the loader annotation) and is caught ONLY by the child's pre-marker
  origin/loader binding.

**Dismissed with rationale (no change):**

- **K1 (fabricated bundle+chain pair):** a caller who authors a complete self-consistent worktree
  bundle AND its matching chain is performing a deliberate §4.5.13 out-of-scope act, and the
  grant-validity of a chain is the authorization-ledger/audit layer's job (§5.2: audit CI
  verifies every chain member against the committed artifacts at the authorized commit); the
  capture layer's obligation — refusing any worktree/chain DISAGREEMENT — is implemented and
  tested. A clarifying sentence was added here instead of a code change.
- **K10 (child spec-digest self-reference):** the pre-consumption binding is the argv transport
  digest — the child refuses, before consuming any field, a config whose bytes differ from what
  the parent derived from the spec; the `authenticated_spec_sha256` echo in the marker-bound
  effect proofs is the post-hoc audit trail, not the enforcement point. The discriminating tests
  cover both: argv digest mismatch refusal (pre-consumption) and parent-side echo comparison.
- **K13 (`waiter` seam):** the waiter is consulted only between SIGTERM and SIGKILL of a run
  already classified ABORTED_BUDGET; it cannot influence any static fact, attestation, or
  certification content, and a hanging waiter harms only the caller's own process. It is not a
  static-authority seam.

### Three-reviewer gate — round 1 adjudication (2026-07-18, head b97c802)

The WI1/WI2 candidate at `b97c802` was put through the standing three-reviewer gate — Codex
gpt-5.6-sol xHigh (read-only sandbox, full repo), Opus 4.8 (read-only agent, full repo), GLM 5.2 via
OpenRouter. GLM first hit its documented reasoning-channel-consumption failure (21,916 reasoning
tokens, empty content) and was re-run in the established working configuration (reasoning disabled,
two subsystem-scoped diff chunks). Every finding was cross-verified against the plan and source
before any change; reviewer votes are not evidence.

**Convergent, confirmed (all three): payload-image byte authentication.** The change that made the
Stage-C `loaded_image_allowlist` MEASURED (to pass the first real production path) admitted the 19
transitive `.dylib` libraries the payload closure loads (libgfortran, libarrow, PIL/scipy/pyarrow
dylibs) by PATH only — disjoint from the hash-pinned Stage-B set and absent from the importable
manifest (`.dylib` is not an importable artifact type). §4.5.7 keeps "enumeration AND hashing" for
libraries loaded outside normal module imports and §4.5.11 re-attests at exit, so a mutation of a
payload-time numerical library would have certified COMPLETED over unauthenticated native bytes.
**Fixed:** the allowlist carries `(path, sha256)`, the generator measures both, and
`authenticate_new_loaded_images` hashes every new Stage-C image against its frozen digest.

**Confirmed, fixed (concrete fail-open or defect):**

- **synthetic_no_file bypass (Codex C5 / GLM child-2):** a module carrying a real file loader whose
  origin is now missing was exempted as synthetic. Fixed: synthetic classification requires loader
  `"none"`; a file-loader module with a missing origin fails closed (unreadable origin). torch.classes
  (loader none, bogus relative `__file__`) still classifies synthetic.
- **Import-then-evict (GLM child-5):** the origin binding checked only resident `sys.modules`. Fixed:
  `_inventory` authenticates every evicted module's absolute file origin against the manifest/closure
  and fails closed on a now-absent one; synthetic (resident, relative `__file__`) modules are excluded
  by residence and the absolute-path gate.
- **Attestation-path aliasing the marker (Codex C3):** a caller attestation path routed to
  `payload_started.json` could forge consumption. Fixed: reject any attestation path aliasing the
  reserved marker or colliding with another, pre-spawn.
- **payload_entry_path coherence (Codex C7):** the attested payload entry is now derived from the
  EXECUTED `payload.entry`; a disagreeing explicit override is rejected (§4.5.10).
- **authorization_id vs chain (Codex C2):** capture now requires
  `config.authorization_id == chain.authorization_id` before any run artifact.

**Kept with recorded rationale (defensible; Opus confirmed sound):**

- **loader-"none" acceptance (Codex C6 / GLM child-1/4):** a runtime loader of `"none"` is accepted
  (recorded `loader_binding`), because the bytes are sha-authenticated against the manifest and the
  ONLY loader that changes bytes-to-execution semantics for the same file — `SourcelessFileLoader`
  (executing bytecode instead of compiling source) — always presents its concrete class, so it is
  caught here as a mismatch (`return None`) and by the dedicated global sourceless scan. C-extension-
  registered submodules (`torch._C._autograd`) and library module-object surgery (`torch.backends`)
  legitimately drop loader metadata after a genuine load. The comment now states this precisely; no
  dead code.

**Dismissed with recorded rationale (no change):**

- **KMP 0-or-1 vs §4.5.5 "exactly one" (Codex C4 / GLM child-3; Opus rated MINOR):** correct for the
  hermetic R2 milestone (libomp registers lazily; the no-compute child observes zero) and admits no
  unauthenticated mutation — 2+, wrong-PID, malformed, or any other delta still fail closed. The
  real-compute Stage-C KMP-appearance concern is an R4 scientific-execution matter, out of this
  hermetic milestone's scope and gated behind a fresh authorization + freeze regeneration.
- **GLM-capture TOCTOU on spec fields / marker-read-then-hash race / stage_c_doc NameError:** the
  post-exit authority checks run after the child has TERMINATED (no concurrent payload); the
  interpreter and pre-boundary set are re-hashed post-exit via `verify_preboundary_attestation_set`;
  `stage_c_doc` is assigned in the same try whose `else` calls the check (no unbound path, verified);
  and the child cannot forge `stage_c.json`/`manifest_post.json`/`import_inventory.json` because the
  bootstrap OVERWRITES them with the real post-walk after the payload returns.
- **GLM-capture spec-digest hashes the interpreter sha-string not raw bytes:** the raw interpreter
  bytes are authenticated in the factory (`sha256_file(realpath) == pin`); embedding that digest in
  the spec document is correct, and a sha256 preimage is out of the threat model.
- **GLM-child closure loader-by-extension:** a `.py` cannot be loaded by `SourcelessFileLoader`
  (that is `.pyc`), the closure bytes are sha-pinned, and the global sourceless scan fails closed on
  any sourceless module.

### Three-reviewer gate — round 2 (focused delta) adjudication (2026-07-18, head 5282b79)

The fix-pass head `5282b79` went through the focused delta gate. GLM 5.2 (reasoning disabled)
returned **APPROVE** (five NIT confirmations). Codex and Opus converged on the same load-bearing
finding and Codex added three more, all on the fixes themselves; every one was cross-verified
against the plan and an empirical probe of the child interpreter before adjudication.

**Convergent, confirmed (Codex CD2 + Opus MAJOR): the round-1 import-then-evict block was vacuous
for pure-Python modules.** Empirically verified on CPython 3.13.11: the audit `import` event
supplies `filename=None` for `.py`/`.pyc` loads (an absolute path only for `.so` C-extensions), so
the block's `os.path.isabs(filename)` gate skipped every ordinary source import, and its
discriminating test hand-fed an absolute filename CPython never produces. **Resolved by removing the
block and DISCLOSING the residual honestly:** a payload that imports a file, runs it, then deletes it
from `sys.modules` before the inventory is a payload DELIBERATELY defeating attestation — explicitly
OUT OF SCOPE per §4.5.13. The IN-SCOPE cases need no audit-event filename: a new under-root import is
caught by the post-execution manifest re-walk (`added`), a deleted under-root file as `removed`, and
an outside-root import is impossible through normal machinery because `sys.path` is the frozen four
roots and Stage C fails closed on any `sys.path` drift. The over-reaching round-1 mechanism and its
vacuous test are gone; the evicted-name evidence field is relabelled to say disclosed, not
authenticated.

**Confirmed, fixed:**

- **CD1 (case-insensitive marker alias):** the marker-alias check used case-sensitive `Path`
  equality, but macOS/APFS is case-insensitive (and `os.path.normcase` is a no-op on darwin), so
  `PAYLOAD_STARTED.json` aliased `payload_started.json` undetected. Fixed: the containment check
  case-folds the path keys.
- **CD3 (package-vs-module precedence; also Opus NOTE-4):** `_payload_entry_path` checked `foo.py`
  before `foo/__init__.py`, but CPython's FileFinder selects the package first, so with both present
  the parent would attest a different file than the child executes. Fixed: the package is checked
  first, mirroring the real precedence.
- **CD4 (loader-"none" conformance):** the round-1 "unclaimed" acceptance was broad. Strengthened so
  a "none" runtime loader is satisfied ONLY when the frozen manifest loader is the UNIQUE compulsory
  loader for its artifact type — `SourceFileLoader` for source or `ExtensionFileLoader` for an
  extension (a `.py` cannot load sourcelessly; an extension loads only through ExtensionFileLoader).
  A frozen `SourcelessFileLoader` (bytecode) pin is NOT satisfied by "none", so clearing loader
  fields cannot launder a sourceless load. This makes the acceptance provably §4.5.7-conformant while
  keeping the legitimate `torch.backends` (source) and `torch._C._autograd` (extension) cases.

**Recorded residuals (disclosed, no code change):** the deliberate import-then-evict-then-delete of
an out-of-tree file (§4.5.13 out of scope, above); a `zipimporter`-origin module now fails the
stricter `synthetic_no_file` gate (Opus NOTE-3 — the real torch/numpy/scipy stack does not trip it,
verified by the passing battery).

### Three-reviewer gate — round 3 (focused delta) adjudication (2026-07-18, head f4eb9e0)

The round-2 fix head `f4eb9e0` went through the focused delta gate. **GLM 5.2 APPROVE** (five NIT
confirmations). **Opus 4.8 APPROVE** — it independently re-probed the CPython audit-event behaviour
and confirmed all four round-2 fixes closed with no new defect and no plan contradiction (five
non-blocking NOTEs, all disclosed §4.5.13 residuals or one-line doc suggestions). **Codex** returned
1 MAJOR + 1 MINOR, both adjudicated below.

- **r3-1 (MAJOR, adjudicated: comment imprecision, no security gap):** Codex noted that an ORDINARY
  optional import that executes and raises is auto-evicted by CPython, so my round-2 comment calling
  the evicted case "deliberate" was too narrow. Opus independently verified — and the source
  confirms — that an evicted module imported through normal machinery loaded from the frozen four
  roots, so its file is UNDER a root and its bytes are authenticated by the pre- and post-execution
  manifest completeness re-walk (which hashes every under-root file and requires the full set to
  equal the frozen manifest), with its loader fixed by the artifact type. §4.5.7's origin and
  loader-class obligations are therefore met at the FILE level for an auto-evicted under-root module
  even without a resident per-module record; the only uncovered case is a deliberate out-of-tree
  `spec_from_file_location` (the §4.5.13 residual). The comment was refined to state this precisely;
  no code fail-open exists.
- **r3-2 (MINOR, confirmed, fixed):** the CD4 loader-"none" exception was gated on the loader
  spelling, so a manifest entry with a bytecode `artifact_type` mislabeled with a source `loader`
  would be accepted — reachable only through a TAMPERED manifest (which fails chain authentication
  before consumption), but a real self-consistency gap. Fixed: `_load_importable_artifact_manifest`
  now rejects any entry whose loader disagrees with the frozen loader for its artifact type, so the
  manifest is self-consistent at parse and the CD4 exception cannot be reached by a mislabeled
  bytecode entry. Discriminating test added.

### Three-reviewer gate — round 4 (confirmatory) + closure (2026-07-18, code head b673367)

The round-3 fix head `b673367` went through the confirmatory delta gate. **Codex APPROVE** (4 NOTEs)
and **Opus APPROVE** — both independently re-verified the round-3 refinements (the loader maps match
exactly, the committed 39,957-entry manifest parses, the regenerated artifacts are faithful, no new
defect). **GLM** returned one MAJOR that is **disproven**: it claimed the parse-time loader check
"silently passes" on an unmapped artifact type, but the check compares against `.get(...)` and a
non-empty loader string, so an unmapped type fails CLOSED (rejected), the opposite of a silent pass;
and the two loader maps are currently identical (a cross-check test now asserts they stay in sync).
`b673367` is therefore the reviewed, gate-clean production-code head; findings 1 and 2 are closed at
it.

**Behavior-neutral tail and closure (head 3071046).** After `b673367` the branch added only:
`366b004` (the realroot launch-4 test's assertion aligned to the round-3 parse-level catch — the
launch still fails closed with no marker, a stronger, earlier catch), `b4c3a00` (the loader-map-sync
test), `cf59b4c` (the authenticated artifacts those two test files forced — `git diff b673367
3071046 -- bistar_gp/` is empty), and `3071046` (the initial D48/SCRATCHPAD docs). A separate one-shot **Codex
closure audit** of the head at audit time (`3071046`) verified: the tail contains only those items; no
production source changed after `b673367`; the regenerated manifests authenticate the final tracked
tree (committed-manifest CI green ungated) with the changed worktree entries being exactly the two
test files; and every protected boundary holds. It raised two documentation-accuracy findings
(head/tail attribution and stale pre-cycle counts), both corrected in the following docs-only commit
(which extends the behavior-neutral tail — `git diff b673367 HEAD -- bistar_gp/` stays empty). The
panel did NOT re-review the literal final head — it does not need to, the tail being behavior-neutral
— and this note does not claim it did.

## Contract questions

- **No protected-schema change is required.** Work item 4 resolves to Option A (a
  documentation clarification of an already-frozen field), so the R1 execution-record
  schema is untouched.
- The native-stack expectations artifact is **R2 Layer-0 content**, not a protected
  historical schema; adding the sentinel-hash field to it is an ordinary R2 artifact
  evolution (it already gained its current shape in D48 Update 8), regenerated and
  re-pinned, not a protected-contract amendment.
