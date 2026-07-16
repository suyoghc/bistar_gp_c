# Post-D45 M2cR remediation plan — author-ratified, conformed

**Status: AUTHOR-RATIFIED PLAN. No implementation, execution, or scientific computation is authorized by this document.**

Ratified 2026-07-15 by author ballot (see [§9](#9-author-ballot--final-dispositions) and `Notes/DECISIONS.md` D46).
This file is the durable, citable artifact. D46 and the R1 handoff cite the section anchors here rather than
conversation-only section numbers. Nothing in this document has been implemented; every milestone ends in a
hard STOP and every execution requires its own fresh explicit author authorization.

Provenance: this plan derives from REVISION 4, which received Codex `APPROVE_PLAN`. The author ballot then
resolved every item in REVISION 4's section 8. Where the ballot changed REVISION 4's proposed text, **only the
final conformed rule appears below**, with a concise note recording what it supersedes. The conforming
corrections are enumerated in [§10](#10-conforming-corrections).

---

## 1. Standing context and invariants

D45 recorded the one attempted M2c v1.18 recompute as an **UNVALIDATED / NOT INDEPENDENTLY AUDITABLE**
execution attempt: a technically plausible node-0 pre-symmetrization symmetry STOP, no scientific result, the
v1.17 one-shot `--execute` authorization CONSUMED, no rerun authorized.

The following are standing invariants, not ballot items:

- **D45 remains an UNVALIDATED_ATTEMPT forever.** It is never retroactively validated or reclassified by any
  later diagnostic, amendment, or rule. In particular the consumption rule of [§4.3](#43-terminal-state-taxonomy-precedence-and-spawn-boundary)
  is **prospective**; D45 stays a historical CONSUMED entry and is not re-adjudicated under it.
- The reserved instance path `docs/m2c_freeze/gtoy_profile_result_v1.18.json` and the **v1.18 label** stay
  permanently unused.
- The evidence bundle `runs/m2c_v118_stop_20260714/` is immutable.
- `bistar_gp/profile_integration.py`, the committed v1.17 manifest and its manifest==code CI, the v1.18 schema
  artifact, the rev-5 freeze package (`docs/m2c-freeze-package-PROPOSAL.md`, sha256
  `c3e9db66e189b2a8cad19bf11b5c4acc6518d4b6d2597ae93b0f700587d1ce3f`), the historical buggy triplet, and
  `experiments/prior_sensitivity_study.py` are untouched throughout.
- The 60-month holdout stays sealed. No Mauna access.
- `runs/` carries no certification weight.
- Every milestone ends in a hard STOP. Every execution requires its own fresh explicit author authorization.

Milestone branding is **M2cR** (ballot B8; editorial only, changing no scientific or execution rule).

---

## 2. Diagnosis

**CRITICAL.**
(C-a) No native gate-event propagation: the frozen orchestrator discards `restart_count` / `retry_count` /
`rcond` on the accept path (`bistar_gp/profile_integration.py:963-969`) and returns no `gate_events`.
(C-b) No execution-capture infrastructure: the attempt relied on post-hoc transcription and unreviewed runtime
monkeypatching.
(C-c) The v1.18 result schema cannot represent a STOP (no status discriminator; untyped interiors).

**HIGH.**
(H-a) Coordinate-order conflict: rev-5 §2c and the committed v1.17 manifest freeze directional order
`(ls, os, lv)` while the review-hardened scientific bridge enforces the E1 storage order `(os, ls, lv)` for the
toy, and directions are applied positionally, so the two frozen constraints are jointly unsatisfiable as
implemented.
(H-b) The rev-5 §2a battery at real conditional optima has no executor.
(H-c) No preregistered diagnostic protocol or decision rule existed post-STOP.
(H-d) The frozen gates discard first attempts: the optimizer overwrites a failed start with its restart
(`profile_integration.py:446-456`) and the curvature gate overwrites the pre-retry evaluation
(`profile_integration.py:702-723`), so no wrapper-free sibling orchestrator can recover per-attempt evidence.

**MEDIUM.**
(M-a) The raw-symmetry tolerance `1e-6` at the frozen `h = 1e-3` is in tension with FD truncation theory: raw
asymmetry of a gradient-differenced Hessian scales as `h²` times a fourth-derivative anisotropy. The theory,
not the exploratory numbers, motivates the diagnostic.
(M-b) `gate_events` under-specified (no restarts, no per-stage split, undefined `undetermined`).
(M-c) No in-run purity/determinism verification.

**LOW.** Runner-level contract drift; untyped provenance in the v1.18 schema.

---

## 3. Architecture

### 3.1 Topological artifact graph and write order

Hash edges point strictly from higher-numbered to lower-numbered layers. No artifact contains or implies its
own digest. **No schema embeds a hash of any manifest that references it.** That rule exists to prevent cycles,
not to forbid every manifest digest: schemas may embed the **v1.17 canonical hash** as a `const`, which creates
no cycle because v1.17 references none of them. This is the pattern the already-committed
`docs/m2c_freeze/gtoy_profile_result_v1.18.schema.json` uses today.

- **Layer 0 (frozen content).** **R1 authors** the execution-record schema and the authorization-ledger schema
  plus its JSONL instance ([§12](#12-blocked-r1-handoff)). **R2 authors** the v2-gate module(s), the capture
  driver and bootstrap, the dependency lock, and **the v5 environment-freeze artifacts**: the exact frozen
  child-environment mapping, the complete importable-artifact manifest, the interpreter pin, and the
  pre-boundary attestation set. R2 also authors the **aggregating environment-freeze manifest** that pins those
  artifacts by sha256 and itself carries the single digest referenced by the effective chain
  ([§5.2](#52-effective-chain-provenance)). **R3 authors** the diagnostic-record schema and the protocol
  parameter document.

  *Provenance: this enumeration supersedes REVISION 4 §3.1's "the frozen child-environment dict", a phrase the
  ratified v5 package outgrew (correction C-i). It also corrects REVISION 4 §3.1's attribution of the
  execution-record schema to R2, which contradicted REVISION 4 §7's R1 scope; R1 authorship is the ratified
  position ([§8](#8-milestones), [§12](#12-blocked-r1-handoff)). The acyclicity rule is stated as the
  cycle-prevention rule it always was, so that REVISION 4's own v1.17-`const` carve-out is no longer a literal
  self-contradiction. Neither change alters any scientific decision or execution policy.*

- **Layer 1a (R2).** The INFRASTRUCTURE manifest pins sha256 of every R2 Layer-0 artifact, including the
  aggregating environment-freeze manifest, **and additionally pins the R1-authored execution-record and
  authorization-ledger schemas**. That is a downward edge and preserves acyclicity: R1 precedes R2, and neither
  schema references the manifest. It does not and cannot pin the R3 diagnostic schema.
- **Layer 1b (R3).** The PROTOCOL manifest (the artifact pinned by the protocol addendum) pins the
  diagnostic-record schema hash and the frozen protocol parameter set, and references the Layer-1a manifest
  hash (a downward edge).
- **Layer 2 (runtime).** Raw evidence files: stdout, stderr, `events.jsonl`, per-node records, payload JSON,
  import inventory, `prelaunch.json`, `spawned.json`, `payload_started.json`, per-launch realized environment
  attestations, pytest output where applicable.
- **Layer 3 (runtime).** `RAW_MANIFEST.sha256` over all Layer-2 files, excluding itself and the terminal record.
- **Layer 4 (runtime).** The terminal record, referencing the Layer-1a/1b hashes (pattern-checked at runtime by
  the driver and post hoc by audit CI against the committed manifests), the Layer-2 per-file digests, and the
  Layer-3 digest.
- **Layer 5.** The git commit and the D-entry quote the Layer-4 record's sha256.

**Acyclicity of the authorization ledger.** The ledger ([§4.3](#43-terminal-state-taxonomy-precedence-and-spawn-boundary))
records terminal-record **digests**, while a terminal record's chain records the authorization by **id string**,
never by ledger digest. Record names the grant; ledger hashes the record. No cycle.

**Frozen write order.** Layer 2 closed, then Layer 3, then Layer 4, each via write-temp, fsync, atomic rename;
commit afterward.

### 3.2 Versioned v2 gates with full attempt capture and write-ahead events

New module(s) provide `optimize_conditional_v2` and `curvature_gate_v2` as **reimplementations, not wrappers**,
importing the same frozen constants from `m2c_freeze.py`. `profile_integration.py` stays byte-identical; the
v1.17 manifest CI is untouched. (Ballot B13.)

- The v2 optimizer returns `attempts` per start: for each attempt, the start vector, whether it was the
  jittered restart (with the jitter draw's provenance), SciPy status and message, `u`, `g`, the per-coordinate
  gradient, grad-inf norm, stationarity, and acceptance. Verdict logic byte-equivalent to the frozen gate.
- The v2 curvature gate returns `evaluations`: the pre-retry evaluation in full (raw matrix, symmetrized `K`,
  eigenvalues, symmetry error, logdet by `h`, per-seed directional values with the canonical direction vectors
  used, rcond, SPD, stationarity, reason) and, when a retry fires, the retry-optimizer telemetry plus the
  post-retry evaluation in full. Verdict logic byte-equivalent, including the frozen malformed-output fallback:
  when the retry optimizer returns a wrong-shaped or non-finite vector, the frozen gate re-evaluates at the
  pre-retry optimum (`profile_integration.py:720-722`); v2 reproduces that behavior and records both the
  malformed output and the fallback evaluation.

**Positive retry-acceptance predicate** (shared definition; used by [§6.3](#63-total-decision-table) row 4). A
curvature retry is POSITIVELY ACCEPTED if and only if ALL hold: (i) SciPy `status == 0`; (ii) reported
`success == True`; (iii) the output vector has the required shape and every element is finite; (iv) the
objective at the retried point is finite; (v) the gradient at the retried point has the required shape and every
element is finite; (vi) the stationarity norm at the retried point satisfies the frozen bound (max-norm of the
gradient at most `tau_stat`). Any retry that is not positively accepted is a **RETRY FAILURE**. This matches
frozen semantics: the frozen gate rejects `status != 0` and `success == False` alike
(`retry_success = int(retry.status) == 0 and bool(getattr(retry, "success", True))`,
`profile_integration.py:724`); a malformed output falls back to re-evaluating the already-failing pre-retry
point, which then necessarily fails the gate; and non-finite objective/gradient or nonstationarity at the
evaluated point force the frozen evaluation's stop conjunction (`profile_integration.py:586-599, 616-624`).

**Write-ahead event stream.** The v2 gates accept an event sink; during execution the child emits
line-delimited write-ahead events (`STAGE_BEGIN/END`, `NODE_BEGIN/END`, `ATTEMPT_BEGIN`, `EVAL_RESULT`,
`RETRY_BEGIN`, `ATTEMPT_END`) over an unbuffered pipe owned by the parent, which appends each line to
`events.jsonl` with per-line flush. Return values remain the structured record for completed calls; the event
stream is the durability channel. A COMPLETED payload requires a balanced event stream; the ABORTED_BUDGET and
INFRA_FAILURE branches explicitly admit an unbalanced partial stream, schema-valid there and carried by digest,
so a crash preserves in-flight attempt evidence up to the last flushed line.

**Equivalence obligation (hermetic).** Differential tests run frozen and v2 gates on the existing synthetic
oracles plus rigged oracles forcing each restart/retry/failure path (including a status-0/success-False retry
via a fake minimizer, the malformed-output fallback, and nonstationary retries); final verdict fields must be
identical (bit-identical where deterministic), with v2 additionally exposing the attempts the frozen gates
discard.

Orchestrator v2 composes the v2 gates, the unchanged frozen grid/band/delta primitives, the per-node gradient
battery ([§6.2](#62-frozen-formulas)), and the B1-reconciled directions, and emits the per-stage records of
[§5.3](#53-gate-event-and-stage-record-structure).

### 3.3 Coordinate semantics (ballot B1)

Directions are **named-canonical** `(ls, os, lv)` permuted into storage order. The role map is separately
ratified: the site containing `base_kernel.lengthscale` is `ls`; `outputscale` is `os`; `kernels.1.variance` is
`lv`; **exactly one site per role or STOP**. Persistence contract: all persisted vectors, matrices, Hessian
axes, optimizer traces, and comparison points are written in **canonical named axes** (matrices conjugated by
the role permutation); **computation stays in E1 storage order**; the bridge is untouched.

---

## 4. Terminal state, retention, and execution snapshot

### 4.3 Terminal-state taxonomy, precedence, and spawn boundary

*(Section number retained from REVISION 4 §3.3 for citation stability.)*

**Status enum:** `{COMPLETED, ALGORITHM_STOP, ABORTED_BUDGET, INFRA_FAILURE, NOT_STARTED}`; one record schema
with a closed `oneOf` branch per status. Scientific standing is a function of (record kind, status): a
result-kind COMPLETED record is a scientific result; a diagnostic-kind COMPLETED record is protocol completion
only, with `not_a_result: true` as a `const` in the diagnostic schema; ALGORITHM_STOP is reachable only by
result-kind runs (the diagnostic probe loop has no verdict gates); ABORTED_BUDGET is an interruption, never a
scientific STOP; INFRA_FAILURE and NOT_STARTED are non-scientific. (Ballot B2.)

**Frozen precedence (first match wins).**
1. No confirmed spawn yields NOT_STARTED.
2. A parent-initiated budget kill yields ABORTED_BUDGET, even if capture faults follow the kill.
3. Any capture, attestation, or environment fault during the run yields INFRA_FAILURE, even if the child also
   exited with a protocol code (a capture fault voids certification).
4. A child protocol exit with a schema-valid payload yields COMPLETED or ALGORITHM_STOP per exit code plus
   payload validation.
5. Anything else yields INFRA_FAILURE.

**Spawn boundary and crash preservation.** The parent writes `prelaunch.json` before fork; the child
bootstrap's first act is a hello message on the pipe; on receipt the parent atomically writes `spawned.json`.
On child death the parent still assembles an INFRA_FAILURE terminal record over whatever raw evidence exists.
If the parent itself dies, `prelaunch.json` / `spawned.json` plus the raw files remain, and a reconciliation
mode later assembles an INFRA_FAILURE record explicitly flagged `reconstructed: true` (raw content was
runtime-captured; only envelope assembly is late). Nothing vanishes and no state is silently reclassified. The
ALGORITHM_STOP branch's `stop.stage` enum is limited to `{optimizer, gradient_battery, curvature, refinement,
upper_pullback, lower_pullback, tail, edge_interiority}`; budget and infrastructure never appear in it.

**Authorization consumption (ballot B10).** `spawned.json` is **process-launch provenance only and does not
consume**. A distinct, **hash-bound** `payload_started.json` is emitted only after all pre-scientific
attestations pass and immediately before the first scientific/model evaluation. **The scientific authorization
is consumed if and only if `payload_started.json` exists.** Once payload starts, **every** terminal outcome
consumes the authorization, including ALGORITHM_STOP, ABORTED_BUDGET, INFRA_FAILURE, crash, or missing
postcheck. A pre-payload infrastructure or attestation failure must still produce and commit an INFRA_FAILURE
record and launch-attempt evidence, but **does not consume** the scientific authorization, because no
scientific evaluation occurred. Any relaunch requires explicit author confirmation and a **new launch-attempt
id**; it is never automatic. Any code, protocol, environment-freeze, or payload change requires the
corresponding new frozen provenance before relaunch.

*Provenance: this supersedes REVISION 4 §3.3's "An authorization is consumed if and only if `spawned.json`
exists (ballot B10)". That sentence's own parenthetical deferred the consumption **decision** to B10; B2
ratified the spawn-boundary **mechanism** and stands unamended. Correction C-a.*

**Payload-boundary enforceability is a HARD R2 OBLIGATION.** R2 must provide a fail-closed, hermetically tested
definition proving that: all pre-scientific attestations complete before the marker; the marker is atomically
and durably emitted and hash-bound to the authorization id, launch-attempt id, exact execution commit, and
frozen artifact chain; no data generation, MAP construction, model evaluation, diagnostic evaluation, or result
payload can occur before the marker; the first scientific operation follows the marker without another
unrecorded phase; missing, malformed, late, or mismatched markers fail closed; and the ordering tests use
spies/fakes and remain hermetic, with no scientific computation. (Spies are what let R2 prove the ordering
while remaining forbidden to perform real model evaluation.)

**Grace policy (ballot B10).** At the wall-clock ceiling the parent issues SIGTERM, waits a 30-second grace
period, then SIGKILL if the child has not exited. A parent budget termination remains ABORTED_BUDGET under
precedence rule 2. The parent assembles the terminal record from already-flushed evidence.

**Authorization ledger (ballot B10).** A committed, append-only ledger records every grant **and every launch
attempt**. Its canonical form is **schema-validated, machine-readable JSONL**; a human-readable
`authorizations.md` rendering may exist but is **not authoritative**. The ledger uses **append-only events**
rather than a mutable grant row:

- `authorization_granted`: authorization id, scope, exact frozen commit / artifact chain, date.
- `launch_attempt_started`: launch-attempt id, authorization id.
- `pre_payload_terminal_outcome`: when applicable.
- `payload_started`: reference/digest of `payload_started.json`.
- `terminal_outcome`: evidence / terminal-record digest.
- `authorization_consumed`: **derived only from a valid payload-start event**, never asserted as a field.

Corrections append **superseding events** rather than rewriting history. Audit CI validates event ordering,
unique ids, legal state transitions, agreement with committed attempt evidence and terminal records, and the
consumption rule. **D45 is recorded as a historical consumed authorization and is not reinterpreted under the
new prospective rule.**

*Provenance: supersedes REVISION 4's Markdown `docs/m2c_freeze/authorizations.md` ledger. Correction C-c.*

### 4.4 Durable evidence retention

All certification evidence becomes **committed repository content** at `docs/m2c_evidence/<run_id>/`: raw
stdout, raw stderr, `events.jsonl`, per-node/per-attempt records, payload JSON, pytest baseline output where
applicable, import inventory, `prelaunch.json`, `spawned.json`, `payload_started.json`, per-launch realized
environment attestations, `RAW_MANIFEST.sha256`, and the terminal record. Local-untracked retention is
**ineligible**; no external store is selected. (Ballot B15(i).)

The **authoritative terminal record is committed in the same directory** as that run's evidence and raw
manifest. Each run is a self-contained committed directory. (Ballot B9.)

**Overflow is `INFRA_FAILURE`, never truncation.** (Ballot B15(iii).) Truncated evidence is indistinguishable
from complete evidence after the fact.

**Exact numeric ceilings are DEFERRED.** R2 measures the canonical evidence representation, may use
**deterministic chunking**, and proposes **separate** ceilings for attestation manifests, event streams,
stdout/stderr, and the complete bundle. Those exact ceilings must be frozen in a **versioned pre-execution
addendum before R4**. **Completeness must never be weakened to fit a ceiling.** Precision note: R2 can measure
the importable-artifact manifest exactly (a filesystem walk) and per-event byte size exactly (hermetic runs),
and the node count is known from B7; the complete-bundle ceiling is therefore **derived** from measured
components rather than observed from a real run, and the addendum must say derived where it derives. (Ballot
B15(ii).)

*Provenance: supersedes REVISION 4 §3.4's ceilings of 20 MB per file and 50 MB per bundle. Corrections C-f,
C-h.*

`runs/` remains scratch and carries no certification weight. The D45 bundle stays where it is, immutable, as
historical evidence of the unvalidated attempt.

### 4.5 Execution snapshot and environment — B14-stack v5

*(Supersedes REVISION 4 §3.5 in full. The original proposed `python -I`, a venv-based lock with byte equality
as completeness, and "threads = 10 across OMP/MKL/VecLib/OpenBLAS". Every one of those is superseded. Ballot
B14-host and B14-stack; correction C-d.)*

**Host scoping (B14-host).** The host is recorded and bit-reproducibility claims are scoped to **identical host
plus lock**. No hostname hard-pinning.

**4.5.1 Launch.** The interpreter is the **Miniconda base installation** at
`/opt/homebrew/Caskroom/miniconda/base/bin/python3.13`, invoked by **absolute resolved path** — never via
`PATH` lookup, never via `.venv/bin/python`. `.venv` is excluded entirely (it contains only `pip`; the
scientific stack is the Miniconda base). The resolved target's sha256 is pinned and **re-attested at freeze
time**, not inherited from any review measurement.

Flags: `-S -s -P -B -X pycache_prefix=<verified-empty run-local dir>`.

**`-I` and `-E` are prohibited.** `-I` implies `-E`, which makes CPython ignore all `PYTHON*` environment
variables including `PYTHONHASHSEED`; the seed then never takes effect while `os.environ` still reads `"0"`, a
false-pass. Verified empirically on CPython 3.13.11: `PYTHONHASHSEED=0 python -I` yields
`hash_randomization == 1` and three differing string hashes across processes, while `python -s -P` yields
`hash_randomization == 0` and identical hashes.

Spawn is direct with `shell=False`. The CWD is pinned to the detached worktree root and asserted.

**4.5.2 Pre-boundary integrity attestation.** Actual sha256 of **every source and native artifact executed
before the audit boundary**: the final bootstrap's full closure, any pre-boundary `lib-dynload` extensions, and
the native runtimes. Frozen and built-in code is carried by the interpreter and covered by its resolved sha256.
`/usr/lib/dyld` is hashed, as is the active arm64e dyld shared cache — the main file **plus all 12 declared
subcaches**.

The empty `pycache_prefix` **alone is insufficient**: compiling from source only helps if the source is
integrity-bound; otherwise unverified bytecode is merely swapped for unverified `.py`.

Residual, stated honestly: trust in **pre-verification execution and kernel/dyld mapping**. This is *not* a
claim that on-disk bytes are unhashable — `/usr/lib/dyld` hashes fine and is hashed.

**4.5.3 Bytecode enforcement (bounded).** The empty `pycache_prefix` forces ordinary source-backed imports away
from existing caches. **Fail if any imported module uses `SourcelessFileLoader`.** Reject orphan/legacy `.pyc`
candidates across the four roots and import containers, asserted at **every launch**. Do **not** require
deleting every normal `.pyc` in Miniconda.

Honest wording: `-B` prevents standard import-cache **writes**; it does not disable `SourcelessFileLoader`, and
`.pyc` remains a registered import suffix. The empty-prefix-remains-empty postcondition is a **consistency
check only** — it proves no surviving file in that directory, not that `-B` held, not that no `.pyc` was read,
not that no transient write occurred.

**4.5.4 Path.** Permitted paths come from frozen manifest metadata, **not** `sys.prefix` (`-S` suppresses site
setup, and on 3.13 leaves a venv's `sys.prefix` at the base interpreter). `sys.path[:]` is **replaced
entirely**, not inserted into, with exactly four entries:

1. the detached worktree root
2. `/opt/homebrew/Caskroom/miniconda/base/lib/python3.13`
3. `/opt/homebrew/Caskroom/miniconda/base/lib/python3.13/lib-dynload`
4. `/opt/homebrew/Caskroom/miniconda/base/lib/python3.13/site-packages`

Replacement rather than insertion because `-S` startup leaves a **nonexistent `python313.zip` entry** that would
otherwise survive and break exact equality. `.pth`-derived finder paths are excluded; none is load-bearing for
the stack, and the editable `bistar_gp` finder's role is replaced by the explicit worktree-root entry.

Assert complete canonical `sys.path` equality against the frozen allowlist. **Permit the canonical worktree
root at index 0** (it is the pinned CWD); reject only `""`, relative or CWD-derived spellings, and additional
aliases or duplicates.

**4.5.5 Environment — staged, exact, dual-view.**

*Stage A, before native imports.* Exact equality against the frozen parent-supplied mapping in **both**
`os.environ` **and raw C `environ`** (via `_NSGetEnviron`, duplicate keys rejected). Frozen mapping:

| Variable | Value | Note |
|---|---|---|
| `PYTHONHASHSEED` | `0` | honored because `-E` is absent |
| `OMP_NUM_THREADS` | `10` | operative: torch's `libomp` |
| `OMP_DYNAMIC` | `FALSE` | verified effective (`omp_get_dynamic() == 0`) |
| `MKL_NUM_THREADS` | `10` | **operative via ATen precedence even with no MKL runtime** |
| `VECLIB_MAXIMUM_THREADS` | `10` | operative: Accelerate |
| `LC_ALL` | `C` | |
| `TZ` | `UTC` | |
| `HOME`, `TMPDIR`, XDG | run-local | realized values recorded, integrity-bound per launch |
| `PATH` | minimal | interpreter still invoked by absolute resolved path |

`OPENBLAS_NUM_THREADS` is **dropped as empirically inert** (setting it changed nothing). `MKL_NUM_THREADS` is
**retained** because it is empirically operative: `MKL_NUM_THREADS=2` drove torch intra-op to 2. An exact
environment contains operative controls, not settings known to do nothing. Recorded as a separate true fact: no
MKL or OpenBLAS runtime image is loaded; `USE_MKL=OFF`; `torch.backends.mkl.is_available()` is false.

Excluded: `PYTHONPATH`, `PYTHONHOME`, `PYTHONUSERBASE`, any other `PYTHON*`, stray `DYLD_*`, and every
unrelated inherited variable.

Locale: with `LC_ALL=C`, `LC_CTYPE` is **not** injected — expect its **absence**. Record
`sys.flags.utf8_mode == 1`, which `LC_ALL=C` induces. (The `LC_CTYPE=C.UTF-8` injection occurs only when no
locale variable is set; the frozen mapping is observed under the **complete final** environment, not a
locale-less probe.)

Run-local `HOME`/`TMPDIR`/XDG directories are created and canonicalized **before spawn**, verified to be inside
the run root and usable; `TMPDIR` must exist and be writable **before torch imports**.

*Stage B, after importing the frozen native stack and initializing thread controls, before payload execution.*
Accept **only** explicitly frozen native-runtime deltas: (i) the validated `__CF_USER_TEXT_ENCODING` value, and
(ii) exactly **one** PID-bound `__KMP_REGISTERED_LIB_*` entry satisfying a frozen name/value rule. **Any other
delta is `INFRA_FAILURE`.** Persist and **authenticate separate post-initialization baselines** for `os.environ`
and raw C `environ`. The two views are **not** required to equal each other.

Rationale, verified: importing torch pulls in CoreFoundation, which sets `__CF_USER_TEXT_ENCODING` in the raw C
environment only, and torch's `libomp` registers a PID-scoped `__KMP_REGISTERED_LIB_<pid>`. A single-stage exact
equality at exit would therefore misclassify **every normal run** as `INFRA_FAILURE`. Probe confirmed exactly
those two deltas appear, with no `os.environ` delta and no other change.

*Stage C, immediately before normal exit.* Compare each view to **its own** authenticated post-initialization
baseline. Any drift is `INFRA_FAILURE`. A **missing** postcheck is `INFRA_FAILURE`.

**4.5.6 Threads.** **Requested/configured value 10 for each controlled facility.** No process-wide ceiling is
claimed and **no exact physical-worker count is claimed**. Torch intra-op **and inter-op** are explicitly set to
10 before any parallel work, **failing closed** if that cannot be done (`set_num_interop_threads` is one-shot
and pre-parallel-work; a second call raises). Dynamic threading is disabled where supported. Backend identity is
**attested as Accelerate** via the conjunction of frozen binary hashes, torch/NumPy build configuration
(`BLAS_INFO=accelerate`, `LAPACK_INFO=accelerate`, `USE_MKL=OFF`, `USE_MKLDNN=OFF`, `USE_OPENMP=ON`; NumPy BLAS
`accelerate`), linkage, and the loaded-image inventory; a build or runtime **backend change fails closed and
requires a new environment freeze**. Effective settings are recorded.

**Empirical repeatability ([§6.2](#62-frozen-formulas), ballot B12(g)) remains the bit-reproducibility gate**,
scoped to what it establishes: repeatability at four frozen points, not global determinism.

*Provenance: supersedes "threads = 10 across OMP/MKL/VecLib/OpenBLAS" and any "exactly 10 threads" claim.
`OMP_DYNAMIC=FALSE` disables dynamic adjustment but the OpenMP specification still permits fewer threads;
`VECLIB_MAXIMUM_THREADS` is a maximum, not a guarantee; intra-op and inter-op are separate pools coexisting with
Accelerate, helper, and native-runtime threads.*

**4.5.7 Completeness — importable-artifact manifest.** A **complete frozen manifest** of importable artifacts
across all four allowed roots, containing path, artifact type, and sha256 for source modules, extension
modules, legacy/sourceless bytecode candidates, and importable archives. **Reject any added, removed, or
changed importable artifact both before imports and after execution.** Every executed module's **resolved origin
and loader class** must match a frozen manifest entry; recording import names is **insufficient**. Built-in,
frozen, and namespace-package modules are classified explicitly. Native-image enumeration and hashing are
retained for libraries loaded outside normal module imports.

Scope (ballot B15(ii) clarification): normal source-backed `__pycache__` entries that cannot be selected under
the frozen empty `pycache_prefix` need not be included merely because they exist; **orphan, legacy, sourceless,
or otherwise importable bytecode candidates must be included**.

This must catch an added `numpy/_distributor_init_local.py` **before NumPy can execute it**:
`numpy/_distributor_init.py:12` performs `try: from . import _distributor_init_local / except ImportError: pass`,
and `numpy/__init__.py:127` imports `_distributor_init` unconditionally. The file is absent and **unlisted in
NumPy's RECORD**, so an ordinary distributor customization or leftover install file could appear and execute
inside `import numpy` without changing `pip freeze`, any RECORD digest, binary-extension hashes, `sys.path`, or
the orphan-`.pyc` scan.

The dependency lock (pip-freeze text plus dist-info RECORD digests plus binary-extension sha256) is retained
**only as a supplementary check**, with the explicit caveat that RECORD proves listed files' bytes, is **not a
completeness manifest**, and **does not cover `.pyc`** (torch's RECORD lists `.pyc` entries with blank hashes).
The prior claim "drift fails closed at the lock check" is **withdrawn**; completeness now rests on this manifest.

**4.5.8 Effect proofs (pre-import, fail-closed).** Explicit `if not cond: raise SystemExit(...)`. **Never**
Python `assert` (stripped by `-O`). **Never** `exit(...)` (installed by `site`, and therefore absent under
`-S`).

- `sys.flags.optimize == 0`
- `sys.flags.hash_randomization == 0` **and** the build-pinned frozen **bound** `sentinel.__hash__()` value.
  The bound call bypasses both a shadowable `builtins.hash` and the shadowable global name `str`; verified to
  return the frozen value after shadowing both.
- `sys.flags.safe_path`; `no_user_site == 1`; `dont_write_bytecode == 1`; `no_site == 1`
- expected `sys.flags.isolated == 0` and `ignore_environment == 0`; record `utf8_mode == 1`
- canonical `sys.pycache_prefix` equality against the verified-empty run-local prefix
- complete canonical `sys.path` equality; staged environment attestation per §4.5.5; CWD asserted equal to the
  worktree root; no orphan/legacy `.pyc`; no `SourcelessFileLoader` import
- an **audit canary** emitted and verified immediately after `sys.addaudithook`, because a pre-existing hook can
  interfere with installing another

The parent treats every uncaught exception or missing authenticated success record as failure.

**4.5.9 Audit-boundary scoping.** The boundary is the point **immediately after successful hook installation**.
Unobserved by the hook: interpreter initialization, bootstrap source reading and compilation, and the statements
that install the hook. Those are **not merely trusted** — every pre-boundary source and native artifact is
hashed per §4.5.2. The residual is trust in pre-verification execution and kernel/dyld mapping.

**4.5.10 Retained.** Import inventory via read-only `sys.addaudithook` from the boundary onward. The parent
hashes the bootstrap and payload entry from disk **before spawn**. Every worktree file loaded is hashed at exit.
In-process check that the imported `profile_integration.py` hash equals the frozen v1.17 manifest constant, as
an **explicit comparison, not a Python `assert`**.

**4.5.11 Post-execution re-attestation.** Repeat **every** pre-run class: interpreter, bootstrap, stdlib
sources, dependency sources, extensions, native libraries, active dyld-cache files, manifest and lock metadata,
worktree. Environment: staged comparison per §4.5.5 Stage C, comparing raw macOS `environ` via `_NSGetEnviron`
(rejecting duplicate keys) **and** `os.environ` — because `os.environ` **desynchronizes** from libc, verified: a
`setenv()` drove `OMP_NUM_THREADS` from 10 to 99 while `os.environ` still read 10. Re-enumerate loaded native
images at exit. Recheck `sys.path` at exit. Any drift is `INFRA_FAILURE`. A **missing** post-attestation
(crash, signal, `os._exit`, `execve`) is `INFRA_FAILURE`. **Parent-side post-exit rehashing is preferred**, so
payload code cannot replace child-side hashing helpers.

**4.5.12 Implementation cost.** The enlarged import/native-image manifest is **accepted as implementation
cost**; its **measured size is reported during R2**; **completeness must not be weakened to meet an assumed
size**. Independent count at ratification: 157,032 importable artifacts under the frozen roots (77,762 `.py`,
1,128 `.so`, 78,140 `.pyc`), roughly 23.6 MB as a single manifest file; under the B15(ii) scope clarification
excluding normal `__pycache__` entries, roughly 78,890 entries and about 12 MB. These are ratification-time
estimates, not the R2 measurement.

**4.5.13 Frozen threat model.**

- **In scope** (a finding blocks only if it is a concrete failure here): accidental source or environment drift;
  stale bytecode; ordinary native/Python environment mutation; crashes; incomplete capture.
- **Out of scope, disclosed as residuals, never blockers**: malicious same-user mutation-and-restore; kernel
  compromise; hostile dyld/loader behavior; payload code deliberately defeating attestation.

**4.5.14 Residual limitations, recorded rather than claimed away.** The mutation-and-restore race and TOCTOU on
hashing (out of scope; disclosed). In-memory-only native state or code mutation undetected by file, environment,
or path re-attestation (out of scope; disclosed). Native runtimes may not honor run-local temp variables
universally: torch's OpenMP attempted a fixed `/tmp` operation despite the controlled TMPDIR. The Miniconda base
is a **shared, mutable** environment carrying other projects' editable installs
(`__editable__.antagonistic_collab-0.1.0.pth`), so drift fails closed at the completeness check rather than
corrupting a result. R4/R6 require a **fresh detached worktree**: the ratification-time checkout held 133
`__pycache__`/`.pyc` paths and correctly fails closed. The numerical effect of `VECLIB_MAXIMUM_THREADS` is
unexercised (exercising it would require prohibited computation).

---

## 5. Contracts

### 5.1 Schema and label naming

Schema files carry their own content-kind name and integer schema version
(`m2c_execution_record.schema_v1.json`, `m2c_diagnostic_record.schema_v1.json`,
`m2c_authorization_ledger.schema_v1.json`), referenced everywhere by sha256. Prereg addendum numbers are
assigned **strictly sequentially at ratification time, never reserved in advance**, so a conditional amendment
that never happens leaves no gap. Run records are named by **kind plus authorization id** and remain **outside
the P4 numeric sequence**. The v1.18 label stays permanently unused. (Ballot B3.)

### 5.2 Effective-chain provenance

Every terminal record carries a `chain` object:

- the v1.17 canonical hash
- the infrastructure-manifest hash
- the protocol-manifest hash (diagnostic and result runs)
- **`environment_freeze_manifest_sha256`** (every diagnostic and result run), binding the record to the
  **static** environment freeze of §4.5 rather than relying only on transitive coverage through the
  infrastructure manifest. Per-launch **realized** environment attestations remain evidence files covered by
  `RAW_MANIFEST.sha256` and are **not** this static member: a per-launch value differs every run and could never
  identify which freeze was used.
- the diagnostic-record sha256 (result runs)
- the amendment-manifest hash or an explicit `"none"` (result runs)
- the exact execution commit
- the authorization **id string** (never a ledger digest; see §3.1 acyclicity)

The audit CI verifies each member against the committed artifacts. (Ballot B18 and B18-sub; correction C-e.)

### 5.3 Gate-event and stage-record structure

- **Per-node record:** node index, noise, warm-start provenance, full v2 optimizer attempts, battery
  per-coordinate results (reference values, functional values, per-coordinate error, pass), full v2 curvature
  evaluations (pre- and post-retry, including the retry-acceptance predicate's per-conjunct outcomes),
  acceptance. Per ballot B12(i), the record must additionally preserve, for every node, the **incoming
  warm-start identity**, both optimizer attempts, the acceptance/failure outcome, the selected optimum if any,
  and the **outgoing warm-start identity**, so the continuation trajectory is **independently reconstructable**.
- **Per-stage record:** stage id (`level0`, `refine_1..3`, `upper_pullback`, `lower_pullback`, and the six
  diagnostic cap stages), class (verdict or diagnostic), status in `{COMPLETED, STOPPED_AT_NODE k,
  NOT_REACHED}`, `nodes_evaluated`, and `nodes_total` where the grid was materialized (absent otherwise). No
  fabricated aggregate: the old `undetermined` count is replaced by these statuses.
- **Aggregates (well-defined sums only):** `restart_count`, `retry_count`, `retry_failure_count`,
  `rcond_fail_count` (pre- plus post-retry evaluations failing SPD or rcond), `symmetry_fail_count`,
  `battery_fail_count`, split by verdict class versus diagnostic class.
- The rev-5 section-6 `gate_events`/result field contract is **superseded for future records** (ballot B2). The
  committed v1.18 schema artifact is **not edited**.
- `available_diagnostics` / `unavailable_fields` do not exist; each `oneOf` branch closes its property set, so
  what can exist in a given terminal state is defined by schema, not self-description.

### 5.4 Nonfinite serialization contract and completeness tests

**Frozen sentinel objects:** `{"_nonfinite": "-inf"}`, `{"_nonfinite": "+inf"}`, `{"_nonfinite": "nan"}` — each
a closed object whose single property takes one of exactly those three enum values.

**Universal element-level rule.** **Every** numeric field emitted in v2 optimizer/curvature records — scalar,
vector, matrix, or per-seed map — serializes with each scalar element as `oneOf [JSON number, sentinel]` under
Draft 2020-12, with closed properties everywhere. This covers, explicitly and without exception: failed-attempt
`u` vectors (`profile_integration.py:458`, `:476-487`); per-coordinate gradients of any attempt; raw and
symmetrized Hessian matrices; eigenvalues; `directional_second_differences` and `directional_errors`
(`:607-617`; all three sentinel kinds permitted); objectives `g` and `g_star` (`:520-523`); `grad_inf_norm`
(`:471`); logdet and `logdet_by_h` (`:559`); `logdet_stability_error` (`:577-581`); `rcond` (`:634`);
`symmetry_error`; battery reference/actual/error values; and every other numeric field the v2 records emit.
Because the rule is universal over the v2 record schemas, its validity does not depend on this inventory being
exhaustive; the inventory documents where nonfinite values are expected from the frozen code.

**Scientific summary fields** in a result-kind COMPLETED payload (band masses, sensitivities, realized-grid
scalars) remain plain finite JSON numbers: a COMPLETED result cannot carry nonfinite summary values by
construction, and canonical serialization (sorted keys, compact separators, UTF-8, `allow_nan=False`) rejects
raw nonfinite literals everywhere.

**Hermetic completeness test (R2 obligation, non-self-certifying by construction).** (i) Walk the complete
emitted-record schema and enumerate every numeric field. (ii) Independently enumerate every field actually
emitted by the v2 gates on rigged oracles, and assert the two inventories match exactly in both directions.
(iii) Force every nonfinite kind through rigged oracles (objectives and gradients returning `-inf`/`+inf`/`nan`,
vectors with nonfinite elements, Hessians with slogdet sign 0, a zero maximum eigenvalue for `rcond = NaN`,
malformed retry outputs, a fake minimizer returning status 0 with success False) and assert each emitted record
validates against the schema **and** round-trips to **hand-written golden serializations** fixed in the test
file (goldens written by hand, not generated by the serializer under test). (iv) Assert that an unknown field, a
malformed sentinel (for example `{"_nonfinite": "infinity"}`), a sentinel in a plain-number-only position, and a
raw nonfinite literal each **fail** validation. The golden fixtures and the dual-inventory cross-check are what
make the test non-self-certifying: neither the serializer nor the schema is checked against itself.

### 5.5 Result payload (result-kind COMPLETED branch)

Required: typed `profile_band_masses` (`lo`, `mid`, `hi`, `sum` as plain numbers; the audit tool checks
**bit-exactly** that `sum` equals the float64 sum of the three — an identity, not a tolerance), typed per-band
`numerical_sensitivity`, `realized_grids`, per-stage records, aggregates, and per-node evidence digests.

**Quantiles are excluded** (ballot B17). The replacement result restores the v1.17-class band-mass result
without adding unsupported probability levels or new unreachable-quantile semantics. Quantiles may be added only
through a future schema version, protocol, and authorization if a scientific need is established. *Rationale of
record: a quantile is not finite by construction — an unreachable level would be undefined and could not
serialize under `allow_nan=False` — and closing that would require a new ALGORITHM_STOP condition and therefore
a new decision-table row, which §6.3's ratified row-8 exclusivity and row-10 totality do not admit.*

---

## 6. Diagnostic protocol

Frozen in R3, before any diagnostic computation.

### 6.1 Probe coverage and continuation

**Coverage (ballot B7): full deterministic verdict closure.** The sorted union of the level-0 grid with toy
edges, its nested refinements to `L_max = 3`, and both one-decade pullback grids refined to `L_max = 3`. The
level-3 refined full grid has `8 × (184 − 1) + 1 = 1,465` nodes, and each refined pullback adds at most about 8
further nodes adjacent to its inserted cap node (pullback grids are otherwise subsets of the full grid,
`profile_integration.py:133-160`), so the closure has **at most about 1,481 unique nodes**. Full closure is
**necessary but not sufficient** for the amendment branch: one non-truncation-like failing node still yields
PRESERVE_STOP. Permitted inference is bound to coverage: a globally scoped row-8 amendment is permissible only
under this full-closure coverage.

**Continuation (ballot B12(i)), all five components.** Nodes are probed in **ascending noise order**. Per node:
run the v2 two-start optimizer and record all attempts. If the two-start gate **accepts**, the warm start for
the next node is this accepted optimum, **regardless of this node's battery or curvature outcomes**. If it
**fails**, the warm start carries forward unchanged (last accepted optimum, else `mode_u`). **Battery and
curvature results never affect continuation or warm-start selection**; the probe path is a function of the
optimizer gate alone. At accepted optima only: run the battery (record), then the v2 curvature evaluation in
**record-only mode executing the frozen retry policy exactly** (a retry fires only on SPD/rcond conditioning
failure; both evaluations recorded in full, with the retry-acceptance predicate's per-conjunct outcomes). **No
scientific gate outcome halts the probe loop**; a diagnostic run's terminal status is COMPLETED unless budget or
infrastructure intervenes; **ALGORITHM_STOP is unreachable for diagnostic-kind runs**.

Node-level conclusions are warm-start-robust by construction because the frozen agreement gate requires both
starts to coincide within the frozen `1e-4`. The accept/fail *outcome* can depend on the warm start, but §6.3
row 3 routes any optimizer gate failure at any probed node to PRESERVE_STOP, and row 8 requires rows 1–7 clear;
so the only path to an amendment is one where every probed node accepted, and on that path every node is
warm-start-robust.

### 6.2 Frozen formulas

**Battery at each accepted optimum (ballot B6, B12(e)).** Inclusion at every accepted real conditional optimum
is a **v1.17 §2a conformance requirement**, not superseded. Reference gradient = central FD of the independent
**fresh-model** scalar `G_hist(u, noise) = _mh_log_joint(mll, model, likelihood, x, y)` plus the sum of `u` over
nuisance coordinates, constructed exactly as the committed hermetic fixture does it
(`tests/test_m2c_profile_gradient.py:188-199`): **fresh model per evaluation**, values applied via
`apply_hp_value`, `ExactMarginalLogLikelihood`, noise fixed. Steps `h_j = FD_STEP_GRAD × max(1, |u_j|)` per
coordinate (`FD_STEP_GRAD = 1e-5`); gate per site `|Δ| ≤ TOL_GRAD_ABS + TOL_GRAD_REL × scale` with
`scale = max(1, max over sites of |FD| max)` (`TOL_GRAD_ABS = TOL_GRAD_REL = 1e-4`). All constants are the
existing frozen ones. **Ratified scope: this is a gross-defect detector at accepted optima, not a
precision-gradient claim** — at an optimum the gradient is near zero by stationarity, so the envelope sits near
`2e-4` while the FD reference's own noise is orders of magnitude smaller.

**Historical equivalence (ballot B12(d)).** `|g_value(u, noise) − G_hist(u, noise)| ≤ 1e-9 × max(1, |G_hist|)`,
the **reused v1.4/S3 density-equivalence class**, at prespecified points only: the MAP state, the ten
prior-draw states, and every accepted conditional optimum. The `+ sum(u)` term is the change-of-variables
Jacobian: the profile works in `u = log θ` while the historical density is in `θ`, and `dθ/du = e^u` contributes
`+u` per transformed coordinate. That correction is what makes the two densities comparable rather than merely
similar.

**Prior-draw construction (ballot B12(f)).** The ten states are generated exactly as the committed fixture
generates them (`tests/test_m2c_profile_gradient.py:167-181`): `torch.random.fork_rng()`,
`torch.manual_seed(seed)` for seeds 100–109, theta sampled per site in **`profile.sites` storage order**,
`u = log theta`, noise taken from the draw. The `fork_rng()` isolates the RNG state so that generating the draws
does not advance the global stream and perturb what is being checked. **Additionally: persist the exact
storage-site order and the realized states in canonical named coordinates**, so any future ordering change is
visible. The draws are **reproducible, not permutation-invariant**: if storage order changed, the ten states
would change, and the persisted order makes that fact evident rather than silent.

**D23 sentinel — committed form verbatim, no vote taken or needed; any change would require a new ballot item.**
Point set `_map_neighborhood_states(case)[1:6]` (the five non-MAP neighborhood states from the frozen generator
seeds and sigmas); per-site worst relative error, max over states of `|naive − FD| max / max(1, |FD| max)`; a
`None` naive gradient counts as infinity (defect visible); **strict** greater-than `D23_SENTINEL_MIN_REL`
required for **every** nuisance site (`tests/test_m2c_profile_gradient.py:365-393`; `m2c_freeze.py:1-11`).

**MAP construction pinned verbatim.** `generate_toy_data()` defaults, `PRIOR_CONFIGS["toy_elicited_n20"]`,
`torch.manual_seed(42)`, `fit_map(n_iter=300, lr=0.05)`. The MAP-noise comparison against
`FIGURE_EXPECTATIONS["toy_elicited_map_noise"]` is **REPORT-ONLY** (ballot B12(h)): the exact float64 delta is
recorded; **no gate, no new tolerance, and no new decision-table row**. This preserves the no-new-thresholds
invariant below and keeps §6.3 ratifiable without a new row.

**FD-step sensitivity (ballot B12(a)).** `symmetry_error(h)` at
`h ∈ {2.5e-4, 5e-4, 1e-3, 2e-3, 4e-3}` — the frozen sweep extended one factor-2 step each way **by the same
generative rule**, introducing no new constant. Per node, an OLS slope of `log symmetry_error` against `log h`.

**Slope classification (ballot B12(b)).** A priori windows: **TRUNCATION-LIKE** `[1.5, 2.5]` (theory predicts 2
for `h²` truncation); **NOISE-LIKE** `≤ −0.5` (roundoff predicts −1 for a gradient-differenced Hessian);
**FLAT** otherwise. Ratified instruction: **do not widen these windows merely to make the amendment branch more
reachable. Row 8 remains deliberately conservative.**

**UNDEFINED (ballot B12(c), extended).** The slope is **UNDEFINED** if **any sweep value is nonpositive or
nonfinite**, or if **the fitted slope or any required OLS statistic is nonfinite**. **Invalid points are never
silently omitted and no reduced subset is fitted.** UNDEFINED routes to PRESERVE_STOP through the frozen
decision table.

*Provenance: supersedes REVISION 4's "the slope is UNDEFINED if any sweep value is zero or nonfinite".
Correction C-b.*

**Purity (ballot B12(g)).** Repeated `g` and `grad` evaluations bit-identical at the mode and at three frozen
node indices (0, mid, last). **Kept at four points, not enlarged.** Ratified scope: this **establishes
repeatability at those frozen points, not global proof of deterministic behavior at every state.** The node
indices are relative to the probed grid, which §6.1 coverage determines.

**No threshold anywhere in this protocol is new.** Every numeric gate reuses a pre-STOP frozen constant, the
MAP-noise comparison is report-only, and the slope windows are theory-derived. The exploratory bundle motivated
which quantities to measure and sets none of their values.

### 6.3 Total decision table

**Definitions.** `G1` = battery outcome over all accepted optima. `G2` = historical-equivalence outcome. Slope
classes per node with the a priori windows of §6.2, with **UNDEFINED as defined there (B12(c) form)**. **POSITIVE
RETRY ACCEPTANCE** is the §3.2 predicate. A **FINAL** curvature evaluation means the single evaluation at the
two-start-accepted optimum when no retry fired, or the post-retry evaluation at the positively accepted retry
point when one did. **First matching row wins; the table is total via row 10; every mixed, missing, nonfinite, or
unresolved case lands on PRESERVE_STOP.** (Ballot B16, conformed to B12(c) per correction C-b; otherwise
unchanged.)

| # | Condition | Disposition |
|---|---|---|
| 1 | The purity check fails anywhere | PRESERVE_STOP; infrastructure-defect track; no amendment permitted |
| 2 | Any probed node lacks a complete record for any reason other than a recorded optimizer-gate failure, or the diagnostic run's terminal status is not COMPLETED | PRESERVE_STOP; evidence incomplete; no amendment |
| 3 | The two-start optimizer gate fails at any probed node (start failure after restart, non-stationarity, or agreement failure) | PRESERVE_STOP; optimizer/step-policy track (not a Hessian-estimator diagnosis) |
| 4 | Any curvature retry is not POSITIVELY ACCEPTED (the negation of any conjunct, including `status == 0` with `success == False` and the malformed-output fallback), OR nonstationarity is observed at any evaluated point, pre- or post-retry | PRESERVE_STOP; optimizer/stationarity track; this row precedes every Hessian or amendment diagnosis |
| 5 | `G1` fails at any accepted optimum, or `G2` fails at any prespecified point, or the D23 sentinel fails | PRESERVE_STOP; gradient/potential code-defect track; no gate or tolerance amendment permitted |
| 6 | Zero probed nodes fail the frozen raw-symmetry check | PRESERVE_STOP; reproducibility investigation; no amendment supported; D45 remains unvalidated either way |
| 7 | Any symmetrized-curvature gate (SPD, rcond, directional, logdet-stability) fails at a FINAL curvature evaluation (which by rows 3–4 exists only at positively accepted points) | PRESERVE_STOP; Hessian-estimator amendment track, gated on a separate future ballot (B5) |
| 8 | Rows 1–7 clear; at least one node fails raw symmetry; every probed node has a defined finite slope; every symmetry-failing node is TRUNCATION-LIKE | AMEND per the pre-committed B4 branch, scoped per B7: global only under full-closure coverage |
| 9 | Any symmetry-failing node is NOISE-LIKE, FLAT, or UNDEFINED, or any probed node's slope is UNDEFINED | PRESERVE_STOP; mixed or ambiguous evidence; follow-up requires a new frozen protocol version |
| 10 | Anything else | PRESERVE_STOP |

**Only row 8 can ever authorize an amendment.** Rows 3 and 4 route every optimizer-class and retry-class failure
ahead of the Hessian row; row 7 is defined solely over final evaluations at positively accepted points; row 8's
precondition "rows 1–7 clear" therefore excludes every retry-failure path. R5's mechanical application means
evaluating rows 1–10 in order against the committed record; the author confirms the application.

**Row-8 pre-committed branch (ballot B4).** If and only if the complete frozen decision table reaches row 8, raw
pre-symmetrization asymmetry is **demoted from a blocking gate to a reported diagnostic**. **It must continue to
be measured and retained.** The independent gradient battery and **all** gates on the symmetrized matrix (SPD,
rcond, directional agreement, logdet stability) **remain blocking**. The branch is pre-committed **before any
evidence exists**, which is the point: choosing a remedy after seeing the diagnostic would be selecting it to fit
the data. **Any row-8 amendment still requires its own implementation, review, manifest, and separate author
ratification at R5 before a result run.**

The `tol(h) = C·h²` alternative **remains not ballot-ready and is not authorized**: it needs an independent
a priori derivation of `C` and its own future ballot. Deriving `C` from the exploratory numbers would fit the
tolerance to the data it exists to gate.

**Row-7 estimator policy (ballot B5).** Any estimator amendment arising from row 7 is **deferred to a separate
future ballot after the specific failing gate is known**. Richardson-extrapolated finite differences are **not
precommitted** as a universal remedy: row 7 fires on four distinct gates, and Richardson addresses truncation,
which is irrelevant to SPD (a structural property) and rcond (conditioning). **Row 7 preserves the STOP.** Exact
forward-mode Hessians would additionally require re-examining the D24 ban before candidacy.

---

## 7. Costs

Estimates, explicitly **not budget-grade**. The only measured anchors are Mauna sub-150 figures
(`docs/plan-d19-mauna.md`, measured-timings table): 0.53 s per 150-iteration profile optimization, and 0.794 s
per 7-dimensional Hessian via `torch.autograd.functional.hessian` (an **autodiff** Hessian, not finite
differences). The toy (N=20, 3 nuisance coordinates) should cost well under those per node, but **no toy
benchmark exists and none may be run now**; every runtime projection is unvalidated until a permitted benchmark
exists. R2 forbids real-model evaluation, so no milestone before R4 is currently permitted to validate it.

**Ceilings (ballot B10): 8 h wall-clock for the full-closure diagnostic; 8 h for a future result run. These are
safety ceilings, not validated runtime predictions and not scientific thresholds.** ABORTED_BUDGET remains an
interruption that preserves partial evidence and **yields no scientific conclusion** (§6.3 row 2 sends any
non-COMPLETED diagnostic to PRESERVE_STOP).

*Provenance: correction C-g — REVISION 4's figures are recorded here as safety ceilings, not predictions.*

Implementation effort: R1 one session plus review; R2 roughly 1,200–1,800 new lines (v2 gates, driver, schemas,
tests) over 2–3 sessions with 2–3 dual-review rounds, **plus the enlarged manifest and attestation surface of
§4.5**; R3 1–2 sessions; R5 audit plus conditional amendment 1–2 sessions; R4/R6 execution-only.

---

## 8. Milestones

Each ends in a hard STOP.

- **R0** — This plan plus the ballot. Ballot closed 2026-07-15. No new authorization recorded. **Complete.**
- **R1** — Taxonomy freeze (documentation and schema design only). See [§12](#12-blocked-r1-handoff). **HARD
  STOP. Not authorized.**
- **R2** — Infrastructure implementation (hermetic). v2 gates with full attempt capture and the write-ahead
  event stream, the capture driver and bootstrap, the dependency lock, the **environment-freeze artifacts and
  aggregating manifest**, the INFRASTRUCTURE manifest plus audit CI, the differential gate-equivalence suite,
  interruption and crash-preservation tests, the §5.4 nonfinite completeness test, the **payload-boundary
  enforceability proof** (§4.3), and the **evidence-size measurement** feeding B15(ii). The full executable
  suite runs here. **No real-model evaluation.** HARD STOP.
- **R2a (new gate, ballot B15(ii))** — A **versioned pre-execution addendum** freezing the exact per-class
  evidence ceilings from R2's measurement, before R4. HARD STOP.
- **R3** — Diagnostic protocol and decision-rule freeze. §6 verbatim, the diagnostic-record schema, the PROTOCOL
  manifest, coordinate goldens (hard-coded per-seed canonical vectors, an asymmetric named-coordinate oracle,
  storage-permutation invariance), and hermetic classifier tests (injected `h²` asymmetry classified
  TRUNCATION-LIKE, injected `1/h` noise NOISE-LIKE, flat injection FLAT, zero/nonfinite/nonpositive UNDEFINED).
  HARD STOP before any `--execute`.
- **R4** — Diagnostic execution. Fresh explicit authorization at one exact commit; captured execution; complete
  evidence committed per §4.4. STOP immediately after.
- **R5** — Independent record audit and mechanical rule application. If row 8 fired: implement, review,
  manifest, and **separately ratify** the amendment. If any other row fired: the arc ends with the STOP
  preserved. HARD STOP.
- **R6** — Result execution (reachable only through R5). Fresh one-shot authorization at one exact
  effective-algorithm commit; terminal record committed (label per B3). The v1.18 path remains absent.

---

## 9. Author ballot — final dispositions

Closed 2026-07-15. Every item resolved; none pending.

| Item | Disposition |
|---|---|
| **B1** | **RATIFIED** — canonical named axes (ls, os, lv); explicit role map, exactly one site per role or STOP; computation in E1 storage order; persistence in canonical order with required permutation/conjugation; bridge unchanged. See §3.3. |
| **B2** | **RATIFIED** — five-status taxonomy, per-kind standing, precedence table, spawn-boundary mechanism; rev-5 §6 field contract superseded for **future records only**; v1.18 artifact untouched and permanently uninstantiated. See §4.3, §5.3. |
| **B3** | **RATIFIED (a)** — addendum numbers sequential at ratification, never pre-reserved; schemas carry own `schema_version`; run records named by kind + authorization id, outside the P4 sequence. See §5.1. |
| **B4** | **RATIFIED** — the pre-committed row-8 branch; `tol(h)=C·h²` not ballot-ready and not authorized; separate R5 ratification required. See §6.3. |
| **B5** | **RATIFIED (a)** — defer row-7 estimator amendments to a future ballot; Richardson not precommitted; row 7 preserves the STOP. See §6.3. |
| **B6** | **RATIFIED** — battery at every accepted real conditional optimum per v1.17 §2a; that requirement **not superseded**. See §6.2. |
| **B7** | **RATIFIED (a)** — full deterministic verdict closure, at most ~1,481 nodes; necessary but **not sufficient** for the amendment branch. See §6.1. |
| **B8** | **RATIFIED** — adopt the `M2cR` milestone branding as the plan's editorial default. Naming only; changes no scientific or execution rule. See §1. |
| **B9** | **RATIFIED** — authoritative terminal record committed under `docs/m2c_evidence/<run_id>/` with that run's evidence and raw manifest; each run a self-contained committed directory. See §4.4. |
| **B10 ceilings** | **RATIFIED** — 8 h diagnostic, 8 h result; **safety ceilings**, not validated predictions and not scientific thresholds. See §7. |
| **B10 consumption** | **RATIFIED** — the spawn-consumption rule **rejected**; consumption iff `payload_started.json`. See §4.3. |
| **B10 boundary** | **RATIFIED** — payload-boundary enforceability is a **hard R2 obligation**, hermetically tested with spies/fakes. See §4.3. |
| **B10 grace** | **RATIFIED** — SIGTERM, 30 s, SIGKILL; remains ABORTED_BUDGET; parent assembles the record. See §4.3. |
| **B10 ledger** | **RATIFIED** — canonical schema-validated **JSONL** event ledger; Markdown non-authoritative; consumption **derived** from a payload-start event. See §4.3. |
| **B11** | **Struck by the plan**; dissolved into B3 and the D45 invariant. |
| **B12(a)** | **RATIFIED** — h set `{2.5e-4, 5e-4, 1e-3, 2e-3, 4e-3}`. See §6.2. |
| **B12(b)** | **RATIFIED** — OLS log-log; `[1.5, 2.5]` / `≤ −0.5` / FLAT; **windows not to be widened for reachability**. See §6.2. |
| **B12(c)** | **RATIFIED, extended** — nonpositive or nonfinite sweep value, or nonfinite fitted slope or required OLS statistic, yields UNDEFINED; **no silent omission, no reduced-subset fitting**. See §6.2. |
| **B12(d)** | **RATIFIED** — `G_hist = _mh_log_joint + sum(u)`; reused `1e-9 × max(1,|G_hist|)`. See §6.2. |
| **B12(e)** | **RATIFIED** — fresh-model central-FD battery per the fixture; **gross-defect detector, not a precision-gradient claim**. See §6.2. |
| **B12(f)** | **RATIFIED** — ten prior draws per the fixture; **plus** persistence of storage-site order and realized states in canonical coordinates. See §6.2. |
| **B12(g)** | **RATIFIED** — four-point purity smoke test; **claim scoped to those points, not global determinism**. See §6.2. |
| **B12(h)** | **RATIFIED** — MAP-noise **report-only**; no new tolerance, no new row. See §6.2. |
| **B12(i)** | **RATIFIED** — all five continuation components; **plus** per-node warm-start trajectory reconstructability. See §6.1, §5.3. |
| **D23** | No vote taken or needed; committed form unchanged. See §6.2. |
| **B13** | **RATIFIED (a)** — v2 gates as independent reimplementations with byte-equivalent verdicts; frozen code, v1.17 manifest, and CI untouched. See §3.2. |
| **B14-host** | **RATIFIED** — identical-host-plus-lock scoping; no hostname pinning. See §4.5. |
| **B14-stack** | **RATIFIED as v5 in full**, explicitly superseding the original B14 ballot wording. Execution and attestation requirements only; authorizes no implementation, file edits, R1, or scientific computation. See §4.5. |
| **B15(i)** | **RATIFIED** — committed content-addressed evidence directory; local-untracked ineligible; external store not selected. See §4.4. |
| **B15(ii)** | **DEFERRED** — exact numeric ceilings to R2; separate per-class ceilings; **versioned pre-execution addendum before R4**; completeness never weakened to fit. See §4.4, §8 (R2a). |
| **B15(iii)** | **RATIFIED** — overflow is `INFRA_FAILURE`, **never truncation**. See §4.4. |
| **B16** | **RATIFIED** — the complete precedence-ordered decision table **as conformed to B12(c)**; otherwise unchanged, including the positive retry-acceptance predicate, row-8 exclusivity, fail-closed mixed cases, row-10 totality. See §6.3. |
| **B17** | **RATIFIED** — quantiles **excluded**; future schema version, protocol, and authorization only. See §5.5. |
| **B18** | **RATIFIED** — per-record-kind effective chain, every member CI-verified. **Sub: RATIFIED** — explicit `environment_freeze_manifest_sha256` bound to the **static** freeze; per-launch realized attestations remain `RAW_MANIFEST.sha256` evidence. See §5.2. |

---

## 10. Conforming corrections

Text changes forced by ratified votes. **No scientific decision is changed by any of them.**

| Id | Correction | Applied at |
|---|---|---|
| **C-a** | Consumption keys on `payload_started.json`, not `spawned.json`. REVISION 4 §3.3's sentence carried the plan's *recommendation* and its own parenthetical deferred the **decision** to B10; B2 ratified the spawn-boundary **mechanism** and **stands unamended**. | §4.3 |
| **C-b** | UNDEFINED conformed to B12(c) (nonpositive or nonfinite sweep value; nonfinite fitted slope or required OLS statistic; no silent omission; no reduced-subset fitting). | §6.2, §6.3 |
| **C-c** | Canonical **JSONL** ledger plus its schema; Markdown rendering non-authoritative. | §4.3, §5.1, §12 |
| **C-d** | REVISION 4 §3.5 superseded by B14-stack v5 (`-I` to `-S -s -P -B -X pycache_prefix`; venv to Miniconda base; env dict to staged dual-view mapping; `OPENBLAS_NUM_THREADS` dropped, `MKL_NUM_THREADS` retained; lock demoted to supplementary). | §4.5 |
| **C-e** | Effective chain gains `environment_freeze_manifest_sha256`. | §5.2 |
| **C-f** | REVISION 4 §3.4's 20 MB / 50 MB ceilings deferred to R2 per B15(ii). | §4.4 |
| **C-g** | REVISION 4 §6's 8 h figures are safety ceilings, not predictions. | §7 |
| **C-h** | R1 freezes retention policy and overflow semantics only; exact numeric ceilings expressly deferred to the B15(ii) pre-execution addendum. **The R1 addendum contains no numeric size ceilings.** | §4.4, §12 |
| **C-i** | §3.1's Layer-0 enumeration expanded past "the frozen child-environment dict" to name v5's freeze artifacts, and the **aggregating environment-freeze manifest defined** so C-e's chain member has a referent. | §3.1 |
| **C-j** | "No quantiles unless B17 ratified inclusion" resolves to **no quantiles** (B17 ratified exclusion). | §5.5, §12 |

---

## 11. Deferred values and future author gates

Nothing in this list is decided. Each requires its own future author act.

1. **B15(ii) — evidence ceilings.** R2 measures/derives; a **versioned pre-execution addendum before R4**
   freezes the exact per-class ceilings. Completeness is never weakened to fit. (§4.4, §8 R2a.)
2. **B4 — row-8 amendment.** Even if row 8 fires, the amendment requires its own implementation, review,
   manifest, and **separate author ratification at R5** before a result run. (§6.3.)
3. **B5 — row-7 estimator amendment.** A separate future ballot, after the specific failing gate is known.
   (§6.3.)
4. **§4.5.12 — manifest measured size.** Reported during R2; completeness not weakened to meet an assumed size.
5. **§4.3 — payload-boundary enforceability.** A hard R2 obligation, hermetically tested with spies/fakes.
6. **§4.5.1 — interpreter re-attestation.** The resolved-target sha256 is re-attested at freeze time, not
   inherited from any review measurement.
7. **Every future `--execute`** requires fresh explicit author authorization, recorded in the §4.3 ledger.
8. **B17 — quantiles.** Only via a future schema version, protocol, and authorization, if a scientific need is
   established.

---

## 12. Blocked R1 handoff

**STATUS: R1 is not authorized by this document.** Both handoff preconditions are now **SATISFIED** (author
determination, 2026-07-15); satisfying them removes the handoff's own gate and **does not** authorize R1.
Beginning R1 remains a separate, explicit author act.

1. **SATISFIED.** `Notes/DECISIONS.md` contains the author's confirmed ballot-resolution entry (D46, the closed
   M2cR ballot of 2026-07-15, recorded in the author's own words), committed in `1241aca`.
2. **SATISFIED** by author determination of 2026-07-15, on the **layered review record**: (i) REVISION 4's
   scientific/architectural `APPROVE_PLAN`; (ii) B14-stack v5's bounded technical closure `PASS`; and (iii) the
   exact conformed durable plan, D46, and this handoff reviewed by **Codex (gpt-5.6-sol, xHigh, read-only)** and
   **Fable (read-only)**, both returning **APPROVE** after conforming fixes. See the D46 Update of 2026-07-15.

```
Execute milestone R1 (taxonomy freeze; documentation and schema design ONLY) of
the author-ratified post-D45 M2cR remediation plan at docs/plan-post-d45-m2cr.md
in /Users/sc8918/Documents/GitHub/bistar_gp_c. Cite that file's section anchors.

PRECONDITIONS (verify; refuse to proceed on any failure):
- Notes/DECISIONS.md contains the confirmed D46 ballot-resolution entry.
- origin/main contains merge 9b786f8ab52a7c71a32026a37484ee0ce056717c.
- docs/m2c_freeze/gtoy_profile_result_v1.18.json is ABSENT.
- rev-5 sha256 c3e9db66e189b2a8cad19bf11b5c4acc6518d4b6d2597ae93b0f700587d1ce3f
  (docs/m2c-freeze-package-PROPOSAL.md) and the v1.17 canonical hash
  65381bc774e894dd9aaf2207cadd9cfa2f2735dafceff4bb39492086a9e522e2 verify
  unchanged. The v1.17 value is a CANONICAL hash, not the plain file digest;
  verify it with the project's canonical serializer.

HARD PROHIBITIONS (entire session): no scientific or diagnostic computation of
any kind; no profile/optimizer/gradient/Hessian/MAP/sampler execution — the
executable test suite is NOT run in R1; rely on the recorded 442 passed /
1 skipped baseline. No Mauna or holdout access; no --execute; no edits to any
existing bistar_gp/ source file or test, to gtoy_profile_freeze_v1.17.json, to
gtoy_profile_result_v1.18.schema.json, to the rev-5 package, or to experiments/;
runs/ (including runs/m2c_v118_stop_20260714/) is read-only and never staged.
D45 remains an UNVALIDATED_ATTEMPT and must not be recharacterized.

SCOPE (new documentation and schema artifacts only; own branch off updated main;
Draft PR):

1. ONE prereg addendum appended to docs/prereg-addenda-d19.md (number assigned
   sequentially at ratification per B3; never pre-reserved) freezing:
   a. The acyclic artifact graph and write order (plan §3.1), INCLUDING the
      expanded Layer-0 enumeration and the aggregating ENVIRONMENT-FREEZE
      MANIFEST that gives B18-sub's chain member a referent. [C-i]
   b. The five-status terminal taxonomy with per-kind standing, the precedence
      table, and the spawn-boundary MECHANISM (plan §4.3, per B2).
   c. The evidence-retention policy (plan §4.4, per B15(i)/B15(iii)/B9) and
      OVERFLOW SEMANTICS (INFRA_FAILURE, never truncation). EXACT NUMERIC
      CEILINGS ARE DEFERRED: the R1 addendum MUST NOT contain any numeric size
      ceiling. Record that per-class ceilings are measured/derived at R2 and
      frozen in a SEPARATE VERSIONED PRE-EXECUTION ADDENDUM BEFORE R4, and that
      completeness is never weakened to fit. [C-f, C-h]
   d. The execution-snapshot and environment rules per plan §4.5 (B14-host and
      B14-stack v5). REVISION 4 §3.5 is superseded and must not be reintroduced.
      [C-d]
   e. The authorization ledger and consumption semantics per B10 (plan §4.3):
      consumption keyed to payload_started.json, NOT spawned.json; and the
      payload-boundary requirements whose enforcement R2 must prove. [C-a]
   f. The labeling rule (plan §5.1, per B3).
   This append is the ONLY permitted edit to an existing tracked file besides
   Notes/DECISIONS.md and Notes/SCRATCHPAD.md.

2. NEW SCHEMA docs/m2c_freeze/m2c_execution_record.schema_v1.json — closed oneOf
   branches for COMPLETED / ALGORITHM_STOP / ABORTED_BUDGET / INFRA_FAILURE /
   NOT_STARTED; per-kind standing (diagnostic kind carries const
   not_a_result: true); the chain object per plan §5.2 INCLUDING
   environment_freeze_manifest_sha256 [C-e]; the plan §5.4 nonfinite sentinel
   definitions applied element-wise to every numeric field of the v2 record
   sections; no placeholders; NO QUANTILES [B17, C-j]. The diagnostic-record
   schema is authored in R3, NOT stubbed here.

3. NEW canonical authorization ledger: schema-validated JSONL plus its schema
   (named per B3, e.g. m2c_authorization_ledger.schema_v1.json), with the
   append-only event types of plan §4.3 and superseding-event corrections. A
   human-readable authorizations.md rendering MAY exist but is NOT
   authoritative. D45 is recorded as a historical CONSUMED entry, not
   reinterpreted under the prospective rule. [C-c]

4. Notes/DECISIONS.md D-entry + SCRATCHPAD update in the same commits.

NOT IN R1: plan §§6.2/6.3 and the decision table belong to R3. Plan §7's
safety-ceiling wording is plan text, not an R1 artifact.

VERIFICATION PERMITTED IN R1: JSON well-formedness and Draft-2020-12 schema
validation of the new schema files against hand-written valid and invalid
instances (non-scientific tooling); git hygiene; hash verification. Nothing else.

CONSTRAINTS: schemas internally acyclic per plan §3.1 (no schema embeds a hash of
any manifest that REFERENCES it; the v1.17 const is permitted precisely because
v1.17 references none of these schemas; the chain references the
environment-freeze manifest by hash, and the ledger references records by digest
while records reference authorizations by ID STRING — no cycle); every nested
object closed (additionalProperties: false); strict finite JSON with the frozen
nonfinite sentinels.

REVIEW GATE: adversarial review by codex (xHigh) plus a Claude cross-model pass;
loop until both approve; every finding cross-verified against source.

STOP after the Draft PR and review verdicts. Merge, R2, and any --execute are
separate author decisions this session must not take.
```
