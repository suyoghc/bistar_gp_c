# Scratchpad

Working notes: current plan, open questions, in-progress state. Clean out completed items.

## M2cR R3 — COMPLETE: diagnostic protocol + decision-rule freeze; Draft PR open (NOT Ready, NOT merged) (D50 + Update 1, 2026-07-18) — branch `feat/d19-m2cr-r3-diagnostic-protocol` off `35ccc3d`, HARD STOP

- **Shipped (v1.21 scope exactly; D50 Update 1 is the full record):** docs-first freeze
  (`0bbc69d`), implementation (`365d7b3`: diagnostic.py + diagnostic_payload.py + capture/audit
  A1 + six test files), regen (`0071fd4`), report currency (`c855d5f`), the single
  panel-correction pass (`9c4452f`: Kimi F1-F2 + GLM F1-F4), regen + Layer-1b re-pin
  (`c038f47`). Full suite at the final code head: **957 passed / 2 skipped / 0 failed**.
- **Panel (one bounded parallel pass at `c855d5f`):** Opus 4.8 APPROVE; GLM 5.2 APPROVE;
  Kimi K3 REVISE (two MINORs, both fixed); no BLOCKER/MAJOR anywhere; every finding
  independently verified by Fable; three dismissals recorded with evidence.
- **NEXT (each a separate author act; none authorized):** author decides the R3 Draft PR
  (Ready/merge). **R4 needs a fresh grant in the v1.19 ledger** — its `frozen_chain` now
  necessarily cites the committed protocol manifest — plus freeze regeneration at its own
  worktree/commit and the `--execute` boundary. v1.18 instance stays absent; D45 stays
  UNVALIDATED_ATTEMPT.

- **Ballot ratified (D50):** A1 (Layer-1b enforcement closed inside R3 — capture authenticates the
  committed protocol manifest chain-bound at launch; parent validates the exact persisted
  diagnostic `payload.json` against the R3 schema before accepting a protocol exit; audit
  declarable-absent shrinks to `{diagnostic_record_sha256, amendment_manifest}`); B (§6.3 rows 1–10
  as a pure hermetic evaluator returning first-match row + frozen track only); C (protocol-manifest
  key set literal to plan §3.1, no R3 code pins).
- **Docs-first freeze committed:** prereg **v1.21** (§6 verbatim: coverage/continuation, frozen
  formulas, total table; instance residence = the diagnostic run's `payload.json`; canonical-space
  B1 composition; stage-grouped `node_index` + recorded `probe_position`; sweep at the FINAL
  curvature evaluation point; purity at `mode_u`, repeats 2) + D50 +
  `m2c_diagnostic_record.schema_v1.json` (`b6b60dd1…`) + `m2cr_diagnostic_protocol_v1.json`
  (`bdfac013…`).
- **Boundaries held throughout:** hermetic only — no `--execute`, no diagnostic/scientific
  computation, no real-model evaluation, no Mauna/holdout, no ledger event, no `runs/`, no
  `docs/m2c_evidence/`; the v1.18 instance stays absent.

## M2cR R2a — v1.20 ceilings FROZEN + enforcement OPERATIONAL; PR #17 MERGED at `35ccc3d3e871a864b081d10e6ca7db53b0cbd5fe` (D49 + Updates 1–2, 2026-07-18) — R2a frozen

- **Ballot ratified (D49):** five exact byte ceilings — runtime-envelope/static-artifact per-file
  33,554,432; events.jsonl 33,554,432; stdout.txt 16,777,216; stderr.txt 16,777,216; complete
  per-run bundle 134,217,728 — frozen in prereg **v1.20** with exact scopes, counting rules, and
  the candidate-record overflow decision. R2a amended ONCE (explicit author act) into a bounded
  freeze+operationalization milestone; no separate R2b; R2 otherwise frozen; B2 precedence and the
  R1 schema untouched.
- **Enforcement shipped:** `m2cr_evidence_ceilings_v1.json` (ninth static artifact, infra-pinned,
  spec-carried); the v1.20 §4 decision at Layer-3/terminal time in capture + last-resort +
  reconciliation; `evidence_overflow` INFRA_FAILURE with full retention, never truncation; audit CI
  static per-file checks (exact manifest key set required). 25 new ceiling tests + the committed
  corroborating measurement rig (5,960 / 2,939 / 6,184); report provenance corrected per v1.20 §7.
- **Gate:** full suite **868 passed / 2 skipped**; one Codex gpt-5.6-sol xHigh read-only exact-head
  review (REVISE: 2 MAJOR / 2 MINOR) — one consolidated correction pass (audit shape/key-set
  requirement; exact addendum provenance; report total), TOCTOU MAJOR dismissed with recorded
  rationale (v1.19 §5 out-of-scope residual, digest-bound content). Regens at bfc4d0e and 3995d5c:
  environment-derived artifacts byte-identical throughout; fixed-artifact total 8,868,576 B.
- **CLOSED (D49 Update 2):** PR #17 merged at `35ccc3d3e871a864b081d10e6ca7db53b0cbd5fe`
  (2026-07-18); final-head full suite 869 passed / 2 skipped. R2a frozen. R3 is now in progress
  under D50 (section above); R4 still needs a fresh grant in the v1.19 ledger + freeze
  regeneration at its own worktree/commit.

## M2cR R2 — CLOSED; external-audit BLOCKERs 1 AND 2 CLOSED (launch-authority cycle; findings 3/4/5/6 already closed); three-reviewer gate CLEAN at reviewed code head b673367 (four converging delta rounds; Codex + Opus APPROVE, GLM disproven); behavior-neutral tail through 3071046 verified by a one-shot Codex closure audit; PR #16 MERGED at `9bb246714f6c64f0a5e65e9afbc50fef627dbc54` (D48 Update 12; merge recorded in v1.20 provenance, 2026-07-18) — R2 frozen

- **Launch-authority cycle (D48 Update 12; reviewed code head b673367, final head 3071046):** finding 2
  (one authenticated launch authority) and finding 1 (mandatory importable-manifest child binding +
  origin/loader authentication) are now CLOSED. `_authenticate_launch_spec` derives EVERY static launch
  fact from the committed Layer-0 graph under the launch worktree (chain-bound); `LaunchConfig` is
  reduced to run identity/routing (the former static fields are unrepresentable); skip tokens and the
  preboundary=None bypass removed; parent/child bound to one `authenticated_spec_sha256`. The child
  requires the manifest + four roots + closure + spec digest (closed-world config), performs the
  complete pre-import re-walk (marker-gated), pre-marker origin/loader authentication of every
  file-backed loaded module, and the post-execution re-walk + inventory validation (gating COMPLETED).
  Bounded real-root integration: a session-cached authenticated host bundle + FOUR child launches
  (positive COMPLETED ~62 s; pre-walk added ~37 s; post-exec mutation ~54 s; manifest
  authority-substitution rejected at parse ~19–41 s). Full suite **840 passed / 2 skipped**; boundaries
  clean (10/10 protected byte-identical, ledger 1 line, v1.18 absent, no runs/experiments, v1.17
  canonical 65381bc7…). Kimi K3 bounded challenge adjudicated (non-gating). First real-native
  production-path launches surfaced + fixed five empirical items (lazy KMP; image-measurement ordering;
  fromlist import expansion; loader-"none" for source/extension; synthetic-`__file__`). The panel
  reviewed the code heads through **b673367** (round-4 Codex + Opus APPROVE, GLM disproven); the
  `366b004…3071046` tail (two test corrections, the artifacts they forced, docs) is behavior-neutral
  (`git diff b673367 3071046 -- bistar_gp/` empty) and was verified by a one-shot Codex closure audit.
  **PR #16 flipped Draft → Ready, then merged by the author at `9bb2467` (2026-07-18; recorded in
  v1.20 provenance).** R2 frozen — no further hardening round absent an observed production failure
  or explicit author amendment; R2a/R3/execute remain separate author acts. Full record: D48
  Update 12 + `docs/m2cr-r2-hardening-design.md`.


- **Shipped (hermetic, plan §8 R2 exactly), at HEAD 3071046:** `bistar_gp/m2cr/` (12 modules) + **17**
  `tests/test_m2cr_*` files; v2 gates byte-equivalent with full attempt/retry evidence; write-ahead
  events; capture driver + B14-stack v5 bootstrap; fail-closed `payload_started.json` boundary + the
  WI1/WI2 launch authority (AuthenticatedLaunchSpec + mandatory child manifest/origin binding); **8**
  committed freeze artifacts under `docs/m2c_freeze/m2cr_*` (importable manifest v2: 39,957 entries /
  **8,744,319 B** / 0 orphans; the 8th = the native-stack expectations artifact, which carries the
  build-pinned sentinel hash and the byte-authenticated 173-entry payload-image allowlist); audit
  tooling; B15(ii) measurement report (NO ceilings; proposals non-binding). Suite at HEAD: **840
  passed / 2 skipped**, exit 0; real-root integration battery 4/4.
- **Review-gate history (compressed):** original three-reviewer gate + external Codex round-3 F1–F6 +
  CP-1..CP-5 + author-directed F1/F2/F4 strengthening = D48 main entry + Updates 7–8 (heads eeefeef,
  8c24b1f, dcefefd). Then the fresh Codex delta review at dcefefd returned **C1–C4 (REVISE)**; the
  author-directed round-4 remediation (unconditional two-layer attestation enforcement, Stage-C
  hermetic fake-bundle tests, argv config-digest transport binding, durable no-clobber publication,
  cached failure route) ran as twelve commits (seven code + five regenerations) through **five
  adjudicated Codex/Opus/GLM delta-review rounds**, ending R5 at **00c3a92**: Codex APPROVE, Opus
  APPROVE, GLM clean-on-adjudication. **Internal gate CLOSED** (D48 Update 9, head bd1d0f9 = Update-9
  docs commit). Every regeneration used the established fresh-detached-worktree process; the four
  environment-derived artifacts stayed byte-identical across all five regenerations.
- **External exact-head audit at bd1d0f9 (2026-07-17) → REVISE (2 BLOCKER / 4 MAJOR / 2 MINOR).**
  The two MINOR documentation findings (7/8) were fixed by 0b7c596. A continuous-hardening cycle
  (D48 Update 10, heads through f51a98e) then addressed the rest:
  - **Finding 4 (retry candidate_vector) — DISMISSED-as-defect / clarified.** It is the protected R1
    schema's RAW-output field; canonicalizing would contradict the closed schema. Documented as an
    explicit field-specific exception + discriminating asymmetric test (27e7e8d).
  - **Finding 6 (terminal-publication truthfulness) — CLOSED.** Typed publication states
    (TerminalWriteError / TerminalAlreadyExists / TerminalDurabilityUncertain); capture returns a
    record only when durably published (ceb9793).
  - **Finding 3 (sentinel hash) — CLOSED.** Now the 8th mandatory attestation directive, measured
    under PYTHONHASHSEED=0 and frozen in the native-stack expectations artifact, derived + bound +
    required (8a319b5).
  - **Finding 5 (evidence bundle) — CLOSED.** RUN_DIR_LAYOUT fully classified with a fail-closed
    coverage guard; report separates static freeze storage from the per-run evidence bundle
    (runtime envelopes measured + per-node/per-event scaled + labeled stdout/stderr allowances);
    ceilings non-binding (f1e15a8).
  - **Finding 2 (BLOCKER, env/interpreter authentication) — ADVANCED.** Parent already derives
    expectations/lock/roots/sentinel from the chain-bound committed infra manifest; the env-mapping /
    interpreter-pin / pre-boundary-set derivation (capture_run ignoring caller static fields) is a
    bounded harness rebuild scheduled with finding 1's cycle (no real-root walk needed).
  - **Finding 1 (BLOCKER, mandatory importable-manifest child binding) — DEFERRED with a measured
    plan.** A hermetic child loads 66 real-stdlib file-backed modules whose origins force real-root
    binding; a real-root walk is ~11.7 s, so a mandatory-manifest child launch is ~12–23 s —
    prohibitive for the ~30-launch fast battery. Parent-side derivation is authenticated; the child's
    unconditional consumption + isolated real-root integration launches (incl.
    numpy/_distributor_init_local.py) need a session-cached host manifest and a small launch count —
    a dedicated next cycle. Full record: D48 Update 10 + docs/m2cr-r2-hardening-design.md.
- The cycle's fixes were put through the standing three-reviewer delta gate (Codex/Opus/GLM),
  four converging rounds (heads 8650661 → c1c6442 → 9c3549d → 0a1a7f2), ending in **unanimous
  APPROVE at 0a1a7f2** with zero unresolved confirmed defects (round 1 fixed the design-note
  WI2/finding-2 overclaim + the squatter-return contract; round 2 the schema-valid-winner + durability
  -fsync contract; round 3 the discriminating durability/valid-raced-reconcile tests; round 4
  confirmatory). Full record: D48 Update 11.
- Full suite at HEAD (0a1a7f2): **798 passed / 2 skipped / 0 failed**. Boundaries clean (protected
  byte-identical, ledger 1 line, v1.18 absent, no runs/ or experiments/). This is an iterative cycle,
  NOT a freeze; findings 1/2 remain the next launch-authority cycle. PR #16 stays Draft.
- **Prompt-hash note:** the R2 authorization prompt's rev-5 hash was a splice (suffix = D46 historical
  plan hash); the plan is consistent at §1 and §12 with the true `c3e9db66…d1ce3f`, which the file
  matches. Gate intent held. See D48.
- **NEXT (each a separate author act; none authorized):** with findings 1 and 2 now CLOSED (D48
  Update 12), the next gate is R2a — a versioned pre-execution addendum freezing per-class evidence
  ceilings from R2's measurement; then R3 (diagnostic protocol freeze, §6 verbatim, diagnostic-record
  schema, PROTOCOL manifest, classifier goldens); R4 execution needs a fresh grant in the v1.19 ledger
  + freeze regeneration at its own worktree/commit.

## M2c — v1.17 ALGORITHM FREEZE RATIFIED (branch `feat/d19-m2c` off main fcc3ce4; D40, 2026-07-13). STOPPED before compute.

- **Two ratified deliverables (committed):** `docs/m2c-gtoy-profile-PROPOSAL.md` (D39 architecture,
  directionally ratified P1-P8) + `docs/m2c-freeze-package-PROPOSAL.md` (**rev-5, umbrella-ratified**;
  the complete numerical freeze). Prereg **v1.17** appended, pinning the rev-5 package byte-exact at
  **sha256 `c3e9db66…d1ce3f`**. D40 records the umbrella vote.
- **Adversarial review DONE:** 5 codex gpt-5.6-sol (xhigh) rounds on the architecture doc + 5 more on
  the freeze package + 1 independent subagent; every finding cross-verified against source. Caught +
  fixed pre-freeze: an invalid MAP-likelihood tail bound, the directional-curvature SIGN, and the Q2
  IACT global-shift. codex outputs in session scratchpad (not committed).
- **Umbrella vote (2026-07-13, own-words):** J1 no-flooring (SPD + rcond≥1e-8, Claude-PROPOSED, retry-
  then-STOP); J2=1e-3; J3=0.90 (a priori); J4=report-only; staged FULL-domain [1e-7,1e4] cap-SENSITIVITY
  (NOT a bound); + the P1-P8 directions. Frozen via §6.16.
- **FROZEN (v1.17):** HMC-independent references (prior-IS/RW-MH pooled/SIR); the profile-integration
  algorithm (exact-edge partition + staged cap-sensitivity + nested refinement + P1 gradient battery +
  L-BFGS-B + SPD/rcond curvature); chain-aware MCSE (MBB on Q2 soft-contribution); numerical-error =
  sensitivity (never SE); estimator goldens+tolerances; the 5 §6.15 predicates (S2/S3/divergence/
  overlap/nugget); two-manifest schema. Historical buggy triplet 0.76262/0.13752/0.02311 (sum 0.9232)
  = HISTORICAL-only.
- **The entire hermetic M2c package is now implemented (PRs A–D, no compute):** the profile functional-
  gradient path (PR A / D41), the S2 fixed-metric + S3 reparam paths (PR B / D42), the **M1 Matérn builder
  + §5.4 overlap + §5.5 nugget (PR C / D43)**, and the **§5.3 divergence + §3 chain-aware MCSE + the v1.17
  algorithm manifest + the v1.18 result SCHEMA + the umbrella suite (PR D / D44)**. **NEXT:** with a
  SEPARATE explicit author `--execute`, the gated deterministic profile recompute → the FILLED **v1.18**
  result manifest (values). **UPDATE (D45, 2026-07-14): one recompute was ATTEMPTED under the now-CONSUMED
  one-shot `--execute` and STOPPED at node 0 (pre-symmetrization symmetry); UNVALIDATED / not independently
  auditable, no v1.18 result, no rerun authorized; see the v1.18 subsection below.** Still owed (no executor,
  pinned reference-only): the ≤0.95
  correlation-duplication gate + the 1e-3 M1-gate eigenvalue-floor gate (PR C); the v1.18 result VALUES.
- **HARD GATES:** no compute/recompute/sampler/Mauna/holdout without `--execute` + clean tree + byte-
  exact hashes + passing tests, then stop-and-report; HMC only via `fit_hmc_e1`; VI+hmc_laplace
  withdrawn; A7 Della on hold (v1.8); holdout SEALED (§6.6).

### v1.18 recompute ATTEMPTED — STOPPED at node 0; UNVALIDATED, no result; v1.17 one-shot CONSUMED; no rerun (D45, 2026-07-14)

- **What:** under a one-shot in-session `--execute`, the reviewed `corrected_profile_band_masses` was called
  EXACTLY ONCE on the real thesis-toy profile over the frozen `[1e-7, 1e4]` domain. It **STOPPED** at node 0
  (noise = `1e-7`). The authorized run's own stdout emitted only `RESULT: STOP` + reason
  `curvature: pre-symmetrization check failed` + `stop_index 0` (`outputs/04`); the magnitudes
  (`sym_err ≈ 3.08e-6` vs `SYMMETRY_TOL 1e-6`; SPD True; `rcond ≈ 6.7e-3`) are from the POST-STOP EXPLORATORY
  diagnostic (`outputs/05`), NOT the authorized run. No band-mass triplet; nothing written under
  `docs/m2c_freeze/`.
- **Evidence:** LOCAL, UNTRACKED bundle `runs/m2c_v118_stop_20260714/` (manifest fixity sha256 `ab73576a…` =
  self-digest of `MANIFEST.sha256`, which lists the 13 OTHER bundle files; never staged; left byte-unchanged).
- **Two independent audits (read-only, author-commissioned; NOT GitHub reviews; author-recorded — the bundle
  holds only the Fable adjudication REQUEST, no returned verdicts):** Fable Max = `VALID_STOP` (faithful
  frozen-algorithm behavior); Codex GPT-5.6-sol = `EXECUTION_NOT_AUDITABLE`.
- **Conservative author disposition (adopted, D45):** UNVALIDATED execution attempt; reported STOP technically
  plausible but not independently auditable, so **no result**. v1.17 one-shot authorization **CONSUMED**; **no
  rerun authorized**; post-STOP node probes exploratory only.
- **Limitations (verified):** post-hoc capture; unreviewed runtime wrappers replaced the frozen module
  bindings; runner used E1 order (os, ls, lv) vs rev-5 (ls, os, lv); gate events discarded by the orchestrator;
  schema has no strictly-typed STOP; post-STOP probes hand-picked, not the frozen grid. The order defect does
  NOT explain the symmetry STOP (the Frobenius symmetry metric is permutation-invariant) but means the complete
  frozen algorithm was not executed exactly.
- **Reserved `docs/m2c_freeze/gtoy_profile_result_v1.18.json` stays ABSENT.** Any future recompute is blocked
  pending a separately-authorized, preregistered, read-only diagnostic protocol plus a fresh `--execute`
  (HANDOFF Q6). Full record: **D45**.

### M2cR remediation — BALLOT CLOSED; durable plan MATERIALIZED; R1 EXECUTED (taxonomy freeze); R2 + all execution UNAUTHORIZED (branch `docs/d46-m2cr-ballot-close` off `origin/main` 9b786f8; D46 + D47, 2026-07-15)

- **BALLOT CLOSED.** Every item of the post-D45 remediation ballot (B1–B18, incl. all B10/B12/B14/B15/B18
  sub-items) is resolved in the author's own words. **Nothing pending.** B11 struck by the plan; the D23
  sentinel needed no vote. Full dispositions: **D46** + plan §9.
- **DURABLE PLAN MATERIALIZED:** `docs/plan-post-d45-m2cr.md`, **authoritative sha256
  `51b8ec602bc955a619432fd1097012efbfa795e4bccb0a2cc7830d07e1aefbf7`** (historical
  `d9e85a41…8a2ff7df` = the plan as committed in `1241aca`, before the §12 precondition-(2) status edit).
  Previously the plan
  existed **only in conversation**, so every ballot disposition and handoff instruction cited section numbers
  with no durable referent — the same not-independently-auditable defect D45 records. The file is now the
  citable artifact: architecture, artifact graph, contracts, diagnostic protocol, total decision table,
  milestones R0–R6, all dispositions, B14-stack v5 in full, corrections C-a…C-j, deferred gates, and the blocked
  R1 handoff, under stable anchors. Conformed only: where the ballot changed REVISION 4's wording, only the
  final rule appears, with provenance noting what it supersedes.
- **BOTH R1 PRECONDITIONS NOW SATISFIED (author determination, 2026-07-15; D46 Update).** (1) D46 records the
  ballot. (2) **SATISFIED on the layered review record:** REVISION 4's scientific/architectural `APPROVE_PLAN`;
  B14-stack v5's bounded technical closure `PASS`; and the exact conformed plan + D46 + §12 handoff reviewed by
  **Codex (gpt-5.6-sol, xHigh)** and **Fable**, both read-only, both **APPROVE** after conforming fixes (both
  opened at REVISE; the shared material finding was REVISION 4's own §3.1-vs-§7 schema-authorship
  contradiction).
- **R1 EXECUTED (D47, 2026-07-15)** — documentation and schema only, on explicit author authorization; its
  artifacts are frozen in the commit that carries D47, and the **Draft PR follows that commit**. Artifacts:
  prereg addendum **`v1.19`** (not v1.18: that label is permanently burned by the D45
  invariant, so the gap is mandated, not created; v1.16 was always the M2bR run label, never an addendum —
  sequence v1.15 → v1.17 → **v1.19**); `docs/m2c_freeze/m2c_execution_record.schema_v1.json`;
  `docs/m2c_freeze/m2c_authorization_ledger.schema_v1.json` + `…_ledger.jsonl` (JSONL authoritative; no
  Markdown rendering added). The addendum contains **no numeric evidence ceiling** — all deferred to R2 plus a
  versioned pre-execution addendum before R4.
- **Two design points worth remembering.** (1) Consumption has **no boolean to type**:
  `authorization_consumed` requires a `derived_from` reference to a `payload_started` event, and
  `pre_payload_terminal_outcome.consumes` is frozen `false`. **Scope limit, stated honestly:** the line schema
  constrains the reference **shape** only — it cannot resolve cross-line references, so the mandatory **R2 stream
  audit** must resolve `derived_from` against the real event stream. Shape validity is necessary, not
  sufficient. (2) D45 could not be expressed through the prospective predicate at all (it predates
  `payload_started.json`), so it is fenced as a `historical_authorization_record` with
  `adjudicated_under_prospective_rule` frozen **false** — recorded, never reinterpreted.
- **Two author decisions (2026-07-15) resolved the R1 stop questions.** (1) `launch_attempt_id` is NOT a B18
  chain member (option (c)): both chain `$defs` are B18-exact, and every record branch requires it **top-level**
  instead, where the ledger's record digests bind it without extending the ratified chain. (2)
  `diagnostic_record_sha256` names the SHA-256 of the **diagnostic-record instance governed by
  `m2c_diagnostic_record.schema_v1.json`** (R3-authored; plan §5.1's literal terminology), never a
  terminal-record digest; no additional terminal-record hash member added — flagged as a future author decision
  if ever wanted. Addendum §8, both schemas, and all validation fixtures aligned.
- **Verification (permitted set only, re-run after the author decisions):** v1.17 canonical hash verified
  `65381bc7…` **exact**, by replicating the frozen canonicalization stdlib-only **without importing
  `bistar_gp`**; rev-5 `c3e9db66…` exact; plan byte-frozen at `51b8ec60…` exact; v1.18 instance ABSENT;
  `origin/main` 9b786f8 an ancestor of HEAD. Hand-written instances: original suite 6 valid / 12 rejected
  (execution record), 9 valid (incl. the committed D45 line) / 8 rejected (ledger); consolidated adversarial
  battery **78/78 probes as expected** (incl. the option-(c) cases, rev-5 cap conformance both directions,
  ALGORITHM_STOP-unbalanced rejected, terminal_outcome-NOT_STARTED rejected); regression suite for the six
  Codex findings passes; `allow_nan=False` rejects raw `NaN`; every `const` digest is v1.17 only. **The test
  suite was NOT run** — prohibited in R1; the recorded 442 passed / 1 skipped baseline stands.
- **R2 AND ALL EXECUTION REMAIN UNAUTHORIZED.** A Draft PR **follows the R1 commit** and must **not** be marked
  Ready or merged; R1 stops there. No `--execute` exists.
  **NEXT (author's call, none granted):** review + merge the R1 PR; then R2 (hermetic infrastructure; full suite
  runs there; still no real-model evaluation), which owes the payload-boundary proof, the evidence-size
  measurement feeding the pre-R4 ceilings addendum, and the environment-freeze manifest.
- **Headline reversals worth remembering:** the proposed `python -I` snapshot is **disqualified** (`-I` implies
  `-E`, so `PYTHONHASHSEED` is ignored and the seed never takes effect while `os.environ` still reads `"0"`);
  the `.venv` is **not** the scientific environment (it holds only `pip`; the stack is the Miniconda base);
  `MKL_NUM_THREADS` is **operative** via ATen precedence with no MKL runtime while `OPENBLAS_NUM_THREADS` is
  inert; `os.environ` **desynchronizes** from libc; dist-info RECORD is **not** a completeness manifest and lists
  `.pyc` with blank hashes; consumption is keyed to a hash-bound `payload_started.json`, **not** `spawned.json`.
- **Deferred/gated downstream (none granted):** the B15(ii) pre-execution ceilings addendum before R4; separate
  R5 ratification of any row-8 amendment; a future ballot for any row-7 estimator amendment; fresh `--execute`
  for every execution.
- **D45 is untouched and permanently UNVALIDATED_ATTEMPT.** The new consumption rule is prospective; D45 stays a
  historical CONSUMED entry. The v1.18 label and result-instance path stay permanently unused.

### PR D — divergence + chain-aware MCSE + v1.17 manifest + v1.18 schema + umbrella DRAFT (branch `feat/d19-m2c-pr-d` off merged main `b3d35b6`; D44, 2026-07-14)

- **Scope = the final hermetic M2c pieces:** (1) §5.3 divergence non-clustering predicate, (2) §3 chain-
  aware `MCSE_strategy` estimator, (3) the IMMUTABLE v1.17 algorithm manifest + manifest==code CI, (4) the
  SEPARATE v1.18 result-manifest SCHEMA (field contract only, NO values), (5) a hermetic umbrella suite.
  4 NEW modules (`bistar_gp/{m2c_freeze_dm,divergence_clustering,mcse_strategy,m2c_manifest}.py`) +
  `docs/m2c_freeze/{gtoy_profile_freeze_v1.17.json, gtoy_profile_result_v1.18.schema.json}` + 5 test files;
  the only tracked non-new-file SOURCE edit is a symbol-export append to `bistar_gp/__init__.py` (plus the
  standard decision-log updates to `Notes/DECISIONS.md` + `Notes/SCRATCHPAD.md`). `python -m pytest -q` →
  **442 passed / 1 skipped**.
- **Divergence** (`divergence_clustering.py`): rate ≤0.001; d_max ≤ L_chain=max(2,⌈3D/C⌉); per-chain time
  window w=⌈0.10T⌉, time_max ≤ L_time=max(2,⌈3·(D/C)·w/T⌉) (sliding window = max_a W_c(a)); unique+sorted
  pre-check (dup/missing ⇒ UNDETERMINED); §5.3(c) fixtures exact (L_chain=6/L_time=2/w=200). HONEST SCOPE:
  parameter-band clustering UNEVALUABLE (schema stores indices only) — flagged, not overclaimed.
- **MCSE** (`mcse_strategy.py`): c_t=exp(-G/τ − M_global), SINGLE global shift over all (c,t,j); IACT via
  the PUBLIC `az.ess(method="identity", relative=False)` raw-autocov ESS (τ=N/ESS), τ_int=max over
  chains+columns; block ℓ=⌈2τ_int⌉; T−ℓ+1<2 ⇒
  UNDETERMINED (no row-bootstrap fallback); overlapping non-circular MBB within each chain → re-run
  `soft_transfer`; SD over B=1000 seed 20260712. Does NOT reuse the SIR row bootstrap. Kept separate from
  the 0.02 precision gate / W5 scatter / MCSE_SIR 0.441±0.005.
- **v1.17 manifest** (`m2c_manifest.py` + JSON): machine-independent algorithm/references/tolerances/
  predicates from the merged frozen constants; NO profile result; manifest==code CI (deep-equality +
  live `profile_integration.py` sha256 drift-catch + exact-key-set). Two-stage construction:
  `frozen_at_git_sha=6d39d38` is the PR-D IMPLEMENTATION snapshot (COMMIT A — actually contains the algorithm
  code); the immutable manifest artifact is recorded/finalized against that snapshot in the following commit
  (a committed manifest can't embed its own sha). **v1.18** = SCHEMA only (at `…v1.18.schema.json`, reserving
  the bare `…v1.18.json` INSTANCE path per §6), NO values, `v117_manifest_sha256` a `const` pinning the actual
  v1.17 hash (`65381bc7…`) + `additionalProperties:false`.
- **Adversarial review (codex xHigh + Sonnet-5) → BOTH APPROVE, then a second focused codex round.** Round 1:
  algorithm/constants/umbrella/invariants CLEAN in both (Sonnet fuzz-checked the divergence window 20k× + read
  arviz source confirming `_ess` is raw not bulk); codex found 3 manifest-CI findings, fixed → both APPROVE.
  Round 2 (author-relayed): codex flagged the manifest didn't follow the amended two-stage sequencing —
  `frozen_at_git_sha` still on the PR-C base, the schema on the reserved result-instance path, `v117_manifest_
  sha256` a bare pattern, no `additionalProperties:false`, and private `az._ess`. All corrected in follow-up
  commits A (public `az.ess(method="identity", relative=False)`) + B (frozen_at_git_sha→impl snapshot; schema
  renamed; const v117 hash + additionalProperties:false + result-instance rejection tests).
- **Provenance (precise):** no scientific sampler route or chain executed; the divergence + MCSE estimators
  ran on hand-built/synthetic deterministic fixtures only, never a real MCMC chain; no Mauna/holdout ran.
  The full suite did execute its pre-existing hermetic tiny-E1 sampler regression tests.
- **DRAFT PR to `main`.** rev-5 sha256 unchanged; all merged frozen source byte-identical to `b3d35b6`; no
  `runs/` staged. STOP before the gated recompute, any v1.18 result VALUES, `--execute`, and merge.

### PR C — M1 builder + §5.4 overlap + §5.5 nugget-floor DRAFT (branch `feat/d19-m2c-pr-c` off merged main `f1bf977`; D43, 2026-07-13)

- **Scope = the three §6.15 M2c predicates PRs A/B did not cover:** (1) the NEW **M1 constrained
  short-scale Matérn-3/2 builder** (M0's 7 sites + ls/os ⇒ 9 sites), (2) the **§5.4 covariance-overlap**
  M1-duplication diagnostic, (3) the **§5.5 report-only nugget-floor** predicate. HERMETIC — synthetic
  fixtures + algebraic seedless cases only; no sampler, no Mauna/holdout, no `--execute`. 5 NEW modules
  (`bistar_gp/{m2c_freeze_m1,m1_builder,m1_authority,m1_overlap,m1_nugget_floor}.py`) + 4 test files; the
  ONLY tracked edit is a 4-symbol export append to `bistar_gp/__init__.py`. `python -m pytest -q` →
  **402 passed / 1 skipped** (baseline 350/1 + PR-C tests).
- **M1 prior (frozen, byte-exact):** outputscale LogNormal(log 2.4e-4, 1.2); lengthscale logit-normal
  0.1+0.9·sigmoid(z), z~Normal(-1.2528, 1.082), hard support [0.1,1.0] (q10/q50/q90 = 0.16/0.30/0.58),
  Matérn ν=1.5. `LogitNormalPrior(Prior, LogitNormal)` mirrors gpytorch `LogNormalPrior`; `Interval(0.1,
  1.0).transform` = 0.1+0.9·sigmoid(raw) bit-exact so constraint↔prior compose (no truncation constant).
  Composable non-mutating `augment_with_m1_short_scale` appends `short_scale` to ANY Mauna arm; 9-site E1
  inventory exact; seasonal A10 stamp UNCHANGED.
- **Distinct-gate discipline:** overlap is the plain centered Frobenius alignment — NO eigen-floor / SPD /
  curvature rule on A or B_j (distinct from PR-A profile SPD, PR-B S2 λ_min≥1e-6, and the M1-gate 1e-3
  floor). The 0.95 correlation cap and 1e-3 M1-gate floor are pinned REFERENCE-ONLY, not applied; their
  gates (≤0.95 duplication, 1e-3 eigen-floor) remain OWED (no executor in PR C).
- **Adversarial review (codex xHigh primary + Sonnet-5), two fix rounds → BOTH APPROVE:** codex
  CHANGES-REQUIRED with 1 MAJOR (overlap silently accepted a partial component set → could PASS) + 2 MINOR
  (OverflowError on huge int weights escaped the wrappers; logit-normal endpoints). Cross-verified vs the
  freeze: MAJOR + the overflow MINOR fixed (overlap now fails closed on a partial set via a FROZEN
  fail-safe default `M1_OVERLAP_REQUIRED_COMPONENTS`; wrappers catch OverflowError → UNDETERMINED); the
  endpoint MINOR does NOT survive cross-verification — the freeze pins "hard support [0.1,1.0]" CLOSED, so
  endpoints-in-support is freeze-faithful (documented, code unchanged). Sonnet APPROVE both rounds; codex
  re-reviewed twice (held the line that the fail-closed must be the DEFAULT, not an optional arg) → APPROVE.
- **Production-contract hardening (2026-07-13/14, author-relayed codex pushback; D43 Update):** five issues,
  all fixed in PR-C modules only. (1) `overlap_diagnostic` enforces the EXACT frozen component set + PINS
  the M1 key to `M1_SHORT_SCALE_NAME` (no `m1_name`/`None` bypass). (2) `nugget_floor_report` requires
  complete M1+M0 authorities + explicit predictive-gate bool + strictly-positive noise. (3) authority
  provenance: the scientific wrappers take candidate maps (label→STRICT bool) + weights and call
  `select_and_normalize_authority`→`resolve_verdict_authority` INTERNALLY, removing the pre-built-authority
  OBJECT bypass (`"False"`-string/`numpy.bool_` rejected). Honest boundary — NOT "non-forgeable": the
  qualification booleans stay CALLER-ATTESTED (a caller can assert `{"G-IS": True}` without proof); PR C
  runs no chains and does not derive/verify G-IS passage or RW-MH crossing — PR D does. (4)
  `augment_with_m1_short_scale` fails closed on a malformed M0 inventory (arm-generic, no hardcoded Mauna
  names). (5) frozen decision thresholds PINNED in the scientific wrappers (`overlap_diagnostic` no longer
  takes `alignment_threshold`/`cap`; `nugget_floor_report` no longer takes `reference`/`flag_threshold`;
  §7 "Frozen, not open" 0.90/0.05 + 1.9e-4/0.05), recorded in every report; configurability stays on the
  `q_overlap`/`nugget_floor_predicate` primitives. Three focused review rounds → codex + Sonnet-5 APPROVE.
- **Provenance (precise):** no M1/scientific sampler route or chain executed; no Mauna/holdout computation
  ran. The full suite did execute its pre-existing hermetic tiny-E1 sampler regression tests.
- **PR #12 flipped Draft → Ready 2026-07-14** after the author (relaying codex) accepted the final
  threshold-pinning correction and directed the mechanical Ready preflight: HEAD contains current
  origin/main (`f1bf977`), GitHub MERGEABLE/CLEAN, PR diff = only the intended PR-C code/tests/Notes (no
  `runs/`), `python -m pytest -q` → 404 passed / 1 skipped, PR body updated. rev-5 sha256 unchanged;
  `m2c_freeze.py`, `m2c_freeze_s2s3.py`, PR-A/PR-B source, the `e1_potential.py` refactor, the freeze
  package, and historical `prior_sensitivity_study.py` all byte-identical to `f1bf977`. The TRACKED tree is
  clean; unrelated local untracked artifacts (pre-existing `runs/` outputs, `.obsidian/`, etc.) remain and
  were NOT staged. Public default strategy unchanged; S3 stays M0-only. STOP before merge, PR D (divergence
  + chain-aware MCSE + two JSON manifests + umbrella suite), any scientific sampler execution, Mauna/holdout,
  and the v1.18 recompute (still blocked on the PR-D v1.17 manifest). Merge is the author's call.

### PR B — S2 fixed-metric + S3 reparam READY (PR #11, branch `feat/d19-m2c-pr-b` off merged main `70e3eb3`; D42, 2026-07-13)

- **Scope:** S2 (§5.1) fixed MAP-Hessian whitened metric + S3 (§5.2) M0 7-coord reparam, BOTH as complete
  sampler-capable NUTS-pilot routes. HERMETIC — synthetic fixtures + quadratic oracle; S2/S3 routes tested
  with MOCKED NUTS/MCMC (no real chain). New: `bistar_gp/m2c_freeze_s2s3.py` (sibling constants, NOT
  `m2c_freeze.py`), `bistar_gp/s2_fixed_metric.py`, `bistar_gp/s3_reparam.py` + 3 test files. Refactor:
  extracted shared `_run_e1_nuts_route` core in `e1_potential.py`; `fit_hmc_e1` behavior IDENTICAL
  (regression guards unedited). `python -m pytest -q` → **350 passed / 1 skipped**.
- **Adversarial review (codex xHigh + Sonnet-5):** codex found 2 BLOCKERS — the S3 33-state battery was
  self-referential (a coord relabeling passed all gates) and the 12 §5.2(c) boundary offsets were unpinned;
  BOTH FIXED with independent golden/role/boundary anchor tests. Sonnet APPROVE + 2 doc nits (site_names
  label, S2 directional sign vs PR-A) addressed as comments. Honesty note: the Mauna-structure fixture's
  MAP Hessian is non-SPD (λ_min≈−9.13) → S2 correctly STOPs; the passing S2 path is exercised by the toy
  fixture + oracle (analogous to the M1 9-site caveat).
- **Follow-up fix (commit `6911a80`):** author caught the S3 target-to-output bridge — target runs in E1's
  u-coords but returned draws used the manual `exp(z_to_u)` map, gated only against its own inverse. Added
  `S3_CONSTRAINED_BRIDGE_TOL=1e-10` gating `max|z_to_e1_theta(z) − e1.constrain(z_to_e1_u(z))| ≤ 1e-10` over
  all 33 states; `coords_to_theta` now reports through `e1.constrain`; discriminating test + M0 comparison
  EXACTLY 0.0. codex xHigh APPROVE.
- **Provenance (precise):** no S2/S3 sampler route or scientific chain executed; no Mauna/holdout
  computation ran. The full suite did execute its pre-existing hermetic tiny-E1 sampler regression tests.
- **PR #11 flipped Draft → Ready 2026-07-13.** STOP before merge, PR C, PR D, any scientific sampler
  execution, or v1.18. rev-5 sha256 unchanged; PR-A source + historical path + `m2c_freeze.py`
  byte-identical to `70e3eb3`; no `runs/` staged.

### PR A — profile core MERGED (PR #10 → main `70e3eb3`, branch `feat/d19-m2c-pr-a` off main a7e108d7; D41, 2026-07-13)

- **PR #10 flipped Draft → Ready 2026-07-13** after S2 authority path closed (9 review rounds, codex +
  Sonnet BOTH APPROVE). MERGEABLE / CLEAN, current with `main`, no `runs/` in the diff. Exact full-suite
  command: `python -m pytest -q` → 331 passed / 1 skipped (bare `pytest -q` has a pre-existing
  `experiments` collection issue — out of scope, do NOT broaden PR A to fix it). STOPPED before merge per
  author instruction; merge is the author's call. No v1.18/recompute/sampler/Mauna.

- **Scope = profile core only** (P1 functional gradient + battery + D23 sentinel; L-BFGS-B optimizer
  gate; curvature gate; P3 grid/quadrature; band-mass partition; quantile inversion; δ_quad/hess/tail;
  **the top-level orchestrator** `profile_logm_on_grid` + `corrected_profile_band_masses` +
  `profile_potential_callables` that COMPOSE the primitives so v1.18 is execution-only).
  6 NEW files: `bistar_gp/{m2c_freeze,profile_potential,profile_integration}.py` +
  `tests/test_m2c_{freeze_constants,profile_gradient,profile_integration}.py`. The historical buggy
  triplet + `experiments/prior_sensitivity_study.py` untouched.
- **Hermetic only** — synthetic fixtures / quadratic + Gaussian-profile oracles; NO real compute,
  sampler, Mauna, or u*(η). The orchestrator is tested on analytic oracles only; the adapter at a
  single MAP point.
- **Verified:** full suite **328 passed / 1 skipped**; rev-5 sha256 unchanged; measured gradient dev
  ≤7.67e-6, D23 mismatch 2.14/2.72, band-mass ΣP_b−1=0, curvature vs diag(1,4,9)=0, oracle logm error
  5.4e-14, discriminating-refinement level-0-vs-final mass shift 0.191 (ℓ*=2).
- **Author interpretation of v1.17 (pre-compute, D41):** once nested refinement converges, the FINAL
  converged grid is authoritative for every reported output (band masses/logm/quantiles); sensitivities
  at matched resolution; all six diagnostic decade-cap stages evaluated as a non-fail-closing trace.
- **Adversarial review (5 rounds):** codex gpt-5.6-sol xHigh (primary) + Sonnet-5 cross-model. R1: 2
  codex blockers + 2 Sonnet minors. R2 (codex on the actual diff): S1 missing orchestrator + S2/S3.
  R3: 4 orchestrator defects (curvature-retry Laplace bookkeeping High — BOTH models; fail-closed logm
  leak; refine=False bypass; non-one-to-one site order). R4: reported coarse level-0 instead of the
  final converged level + confounded sensitivities + unevaluated diagnostic stages + optional bridge
  order → refinement-authority refactor. R5: out-of-domain band edge crashed the diagnostic trace
  (codex) + fail-closed docstring over-claim (Sonnet). All fixed; codex + Sonnet APPROVE each round.
  Gemini/Fable unavailable (quota/outage/credits).
- **Deferred to the gated v1.18 recompute:** real u*(η) optimization; curvature gate on the real
  profile; corrected band-mass triplet / real golden PASS-FAIL; v1.18 result manifest; S2 HMC smoke.
- **NEXT PRs (roadmap):** B (S2 fixed-metric + S3 reparam), C (M1 Matern builder + overlap + nugget),
  D (divergence + MCSE + manifests + umbrella suite; lands last, pins the manifest).

## M2bR corrective milestone — COMPUTE LAYERS EXECUTED (D33, branch feat/d19-m2br, 2026-07-12); start-freeze gate PASSED (D32)

Branch `feat/d19-m2br` off `origin/main` (bd0b399 = merged M2b PR #7). The two-stage
validation start freeze is DONE and independently verified; the hard ordering gate was
satisfied. As of D32 no chain had run; **both compute layers have SINCE been executed
(D33, 2026-07-12) — 6 audit + 16 validation chains completed** (see the D33 block below).

- **Commit A `10edc2d`** — prereg v1.14 + `experiments/m2br_start_freeze.py` (deterministic,
  no sampler) + `docs/m2br_freeze/start_freeze_v1.14.json` (manifest sha `b1abfa3c…`). Pins
  the 8 realized starts (2 configs x 4 chains, shared across td7/td10): `informative` B=3
  (median lo/mid/hi), `toy_elicited` B=2 (median lo/mid + q75(lo) filler; hi 0.046<5%). All
  fallback=0; both MAP starts preflight-OK. R-A/R-B + details 1-5 recorded verbatim.
- **Commit B `72949c0`** — D32 pre-run gate entry. Three independent implementations (codex
  freeze script, Fable from-scratch recompute, barred clean-room codex) agree byte-for-byte on
  all 8 starts (realized (seed,row), fallback, semantic sha256, chain 0 incl.); atol=1e-12 pool
  verify + 4-site topology + MAP determinism confirmed.
- Reconciliations in v1.14: validation-proposal doc-hash drift (`bdbabb86`->`1045c11c`); D31
  supersedes the audit protocol's stale "PENDING" header without editing the frozen file
  (`45999e2f`); the proposal's "7-site" is a Mauna carryover (toy model has 4 sites).

**Implementation-only checkpoint DONE (author's call, 2026-07-12): drivers built + verified,
NO chain launched.** prereg **v1.15** provenance erratum (R-A/R-B ratified in the author's later
message + recorded in D32, not by the D31 rows-8/9 vote). Drivers:
`experiments/m2br_run_common.py` (Deadline w/ absolute cutoff, transactional_persist samples-last,
failure records, schema-v3), `experiments/m2br_audit_run.py` (6 runs + §3 unchanged-arm
re-verification: prior-IS + SIR PASS @1e-12 on real data; RW-MH broadened — toy_elicited
thorough PASS (occupancy sum, 30000-integral, P_lo + crossings [44,40,38] unchanged @1e-12,
code params 30000/5000/0.1), other 3 configs NOT_APPLICABLE (RW-MH referee is toy_elicited-only)), and
`experiments/m2br_validation_run.py` (V1/V3/V2/V4, frozen-start injection w/ manifest-hash anchor
`b1abfa3c` + per-start sha verify, arviz criteria, authority coverage, R-B pooled-800 primary).
`tests/test_m2br_drivers.py` 21 hermetic tests (incl. R-B pooled≠averaged proof). Real HMC gated
behind `--execute` AND `authorized=True`. codex-reviewed (two rounds);
all confirmed findings fixed (accidental-run guard, manifest-hash anchor+TOCTOU, §3 re-verify,
cardinality/draw contracts, samples-last persistence, absolute cutoff+clock-first).
Committed run plan `docs/m2br_freeze/run_plan.json` + report `docs/m2br-run-plan.md` (exact launch
commands + schedule). Heavy samples & pools stay untracked.

**PREFLIGHT-HARDENING fix pass (2026-07-12, before launch):** `--verify-arms` writes a separate
`runs/m2br_preflight/` namespace (idempotent; no collision with `--execute`'s no-overwrite
artifacts); unchanged-arm verification is STRICT (missing required pool/SIR/toy-RWMH artifact =
FAIL not SKIP; `--verify-arms` exits 0 only on PASS; `run_audit` samples only on PASS); RW-MH pins
the FULL (lo,mid,hi) occupancy triplet per seed @1e-12 + crossings + integer-exactness + caller
frozen-defaults provenance; process isolation uses `spawn` (not fork) + bounded
`queue.get(timeout)` (not `empty()`) + terminate→kill + start() cleanup; thread/BLAS env pinned
INSIDE each spawned sampler child (`M2BR_TORCH_THREADS`, default 10) — directly tested under spawn.
Full suite **262 passed + 1 skipped**.

**COMPUTE EXECUTED (D33, 2026-07-12, this session).** Both layers ran under `caffeinate -i`, threads
pinned to 10, stop-and-report. Pre-launch gates ALL PASSED (freeze sha `b1abfa3c` byte-exact; §3
`--verify-arms` overall PASS; `pytest` 262+1; both `--dry-run` plumbing OK). Nothing frozen edited;
heavy samples + pools stay UNTRACKED.
- **AUDIT** (`runs/m2br_corrected_impact/`): all 6 single-chain runs completed (~14 min), clean
  (`nuts_e1`, 0 div, acc ≥0.99, 0 saturation, 0 NotPSD). td7≡td10 bit-identical (cap never binds).
  Corrected occupancy now tracks the prior-IS authority; posteriors de-concentrate from Sin+Linear
  ~0.67–0.70 to ~0.24–0.43. Single-chain → CANNOT close W2/W3.
- **VALIDATION** (`runs/m2br_validation/`): 16 chains, all start-shas match manifest v1.14 byte-exact.
  **V3, V4 (toy_elicited td7/td10) PASS all criteria → SUPERSEDE** (validated R-B pooled-800
  Sin+Linear 0.4205/0.4220, occ ≈0.76/0.19/0.05, agreeing with SIR 0.441 — mode-vs-mass dichotomy
  collapses). **V1, V2 (informative td7/td10) FAIL** 4 marginal criteria (R-hat 1.0114, bulk-ESS
  378/382<400, per-chain occ hi-spread 0.104>0.05, div 0.001) → stay **WITHDRAWN/UNVALIDATED**
  (authority coverage passes; reproducibility does not). Escalation = new addendum v1.16+, never in-run.
- **Provenance (small tracked manifests):** `docs/m2br_freeze/{audit,validation}_result_manifest.json`
  (hashes + verdicts + provenance + pooled occupancy); D33 in `Notes/DECISIONS.md`; proposed (pending
  author ratification) `docs/m2br-w2w3-writeup-PROPOSAL.md`. Draft PR #8 updated, kept DRAFT pending
  author sign-off.
- **W2/W3 proposal REVISED (rev-2, 2026-07-12)** after codex review + author direction: corrected NUTS
  (Sin+Linear 0.4205 td7 SD 0.0063 / 0.4220 td10 SD 0.0077) and SIR (0.441±0.005; pools 0.419/0.438/0.431)
  reported SEPARATELY (not merged into 0.42–0.44); prior-IS/SIR = ONE IS-family reference (shared pools),
  independent check = NUTS vs IS/SIR family; ALL VI claims WITHDRAWN pending corrected-VI rerun (VI hit by
  same D22 defect); mass-faithful language qualified as conditional on the fixed data-elicited prior,
  N=20 toy-only. See `docs/m2br-w2w3-writeup-PROPOSAL.md`.
- **RATIFIED (D34, 2026-07-12):** author explicitly ratified revised W2 + interim-withdrawn W3 + the
  v1.16 numerical protocol. A codex round-2 caught a FAILURE-DIAGNOSIS error (now corrected): the `382`
  noise ESS is POOLED, not per-chain — the "~6-SE gap" is WITHDRAWN (Fable recomputed: per-chain hi-band
  indicator ESS ≈96/66 → chain0 vs chain2 ≈ **2.0 combined MCSE**); mechanisms are distinct (chain 2 =
  divergences 6/8; chain 0 = max occupancy deviation +0.104); "all four marginal" → occupancy missed
  MATERIALLY (0.104>0.05) + 3 near-threshold; rationale reframed HYPOTHESIS-testing; cross-chain SDs are
  DIAGNOSTICS not SEs; informative audit = nearly uniform, nominal argmax. W2/W3 doc → RATIFIED (rev-3).
- **v1.16 PINNED + DRIVER BUILT/TESTED/REVIEWED (not run):** pin `docs/m2br_freeze/v116_run_plan.json`
  (sha `db177b8b`); driver `experiments/m2br_v116_run.py` (imports, does NOT modify, the frozen
  `m2br_validation_run.py`; sole change warmup 3000 + draws 8000; dual-gated --execute+authorized=True;
  --emit-plan verifies the 4 start shas; --dry-run mock-only). Tests `tests/test_m2br_v116.py` (10
  hermetic → **12** after cross-model findings). Two independent reviews, both **APPROVE, no P0/P1**:
  (i) Claude subagent (codex was rate-limited); (ii) **GLM-5.2 via OpenRouter** cross-model pass —
  its 5 P2 findings cross-verified against source: #1 --execute routing test + #2 no-overwrite test
  ADDED, #4 --emit-plan made explicit, #3 already covered, **#5 (pickle-identity gate bypass) was a
  FALSE ALARM**. NO chain launched.
- **D35 fail-closed sampler gate — v1.16 ONLY; frozen drivers kept as-executed (2026-07-12):** a 4th
  review (GPT-5.6-sol xhigh via OpenRouter) flagged the historical `sampler_fn is fit_hmc_e1` gate as
  fail-OPEN (a `partial(fit_hmc_e1)` ran ungated). Author ratified adopting the fail-closed pattern, THEN
  (provenance call) chose to apply it to **v1.16 ONLY** and REVERT `m2br_audit_run.py` +
  `m2br_validation_run.py` + `tests/test_m2br_drivers.py` to their exact as-executed bytes (`b56a5a2`).
  Rationale: only v1.16 ever launches again, so the gate has full value there + zero on the done drivers;
  keeping the frozen files byte-identical to what produced D33 preserves the freeze discipline
  (footnote-free). Fail-closed primitive lives in `m2br_run_common` (ADDITIVE: `register_mock_sampler`/
  `is_ungated_sampler`/`require_sampler_authorization`; per-object-attribute marker, dual-import-safe,
  import-registered mock survives spawn). v1.16 gates at orchestrator+worker and rejects real+isolate=False.
  D33 results provably unaffected (frozen drivers == as-executed). Full suite **277 passed + 1 skipped**.
  NO chain launched.
- **v1.16 EXECUTED once (D36, 2026-07-12, author-authorized) → FAIL.** HEAD `d0f4b02`, preflight PASSED,
  exit 0, ~27 min. `failed_criteria: occupancy (0.0604>0.05) + divergence_rate (0.00716>0.001)`. R-hat and
  ESS were FIXED by the longer chains (378→1158 bulk-ESS; 1.0114→1.0081 R-hat); occupancy improved
  (0.104→0.060) but still fails; divergence rate increased (0.001→0.00716). **CORRECTION (D36-c1):** NOT a
  high-noise-basin effect — divergences concentrate in the larger-step chains 0/2/3 (steps 0.37/0.33/0.40 vs
  chain1's 0.16; chain1 has 0 div despite 65.4% high-band) and endpoint-localize to LOW/MID noise (pooled
  137/53/39 of 229; conditional 1.69%/1.25%/0.20%) — an unresolved target-geometry/adaptation/
  parameterization interaction; the longer same-strategy run did not resolve it.
  Authority coverage PASS (pooled 0.253/0.133/0.614 ≈ prior-IS authority).
  → **informative stays WITHDRAWN/UNVALIDATED; no replacement number.** Same-strategy lane exhausted
  (D33 4×2000 + v1.16 4×8000); any further attempt = STRATEGY change via new addendum, never a budget bump.
  No corrected-VI claim. toy_elicited (D33) UNAFFECTED — still superseded. Provenance:
  `docs/m2br_freeze/v116_result_manifest.json`; heavy samples `runs/m2br_v116_informative/` UNTRACKED.
- **D36-c1 (correction):** divergences are NOT a high-noise-basin effect — they concentrate in the
  larger-adapted-step chains 0/2/3 and endpoint-localize to LOW/MID noise (pooled 137/53/39 of 229;
  1.69/1.25/0.20%); chain1 is 65.4% high-band with 0 div. All docs corrected; result manifest carries
  SHA256 for all 17 artifacts. Deterministic archive: 26.04 MiB, sha256 c0aea0b9…e2a3a7b9 (untracked).
- **M2bR CLOSED (D37, 2026-07-12).** Outcomes propagated (banners): tracked
  `docs/{prior-sensitivity-study,fit-method-metric-comparison,appendix-tree-depth-cap}.md`; local
  `WRITEUP_DRAFT/DECISIONS` + 2 kb/Wiki articles (SIR 0.696-0.707 hard-win left UNAFFECTED). G-toy gate:
  validated toy_elicited is an INPUT to M2c, does NOT close G-toy (an M2c §6.9 derivation referenced to the
  D18 toy_elicited artifacts; M2c must still revise the withdrawn 0.696, recompute normalized profile masses,
  freeze tolerances). informative withdrawal is NON-BLOCKING because §6.9 defines G-toy against toy_elicited
  and informative is NOT the reference config (NOT a general coverage-failure waiver — the L305-307 sentence
  only says a coverage-repairing sampler targets the mass-faithful answer, not 0.696). **PR #8 → Ready** (not merged).
- **AUTHOR DECISIONS MADE (D38, 2026-07-12):** (1) M2bR formally CLOSED; (2) M2c OPENED as next milestone
  (own branch/PR off updated main; NOT started this session); (3) `informative` ACCEPTED as
  WITHDRAWN/UNVALIDATED for the paper — no strategy-change now, retained as a documented future/
  reviewer-contingent option; (4) G-toy golden revision scoped to M2c (remove withdrawn 0.696 as a
  validity target; keep only as S1 historical regression; recompute normalized profile masses; freeze
  corrected tolerances before any pilot). **PR #8 merged to `main`** (merge-commit method); local `main`
  fast-forwarded.
- **NEXT session = M2c** (own branch off updated main; handoff prompt provided). Prohibited until then:
  Mauna hours, VI repair, informative strategy-change. Fold banners into final paper prose is an author
  writeup action. Untracked run artifacts + archive preserved (unmoved/uncommitted); durable relocation
  is a separate author choice. A7 Della on hold (v1.8).


## D19 Mauna study — M2a DONE (D20); M2b code complete, ALL 9 decision items ratified (D21-D31); PR #7 Ready; merge + M2bR = author's next call

- `docs/plan-d19-mauna.md` = the frozen record (a077c6e, immutable; merged to main
  as e86e90a): staged plan, gates, cost table (E1 rows are kernel-cost proxies
  pending the M2b NUTS microbenchmark), candidate matrix + harmonization rule, risk
  register, milestones, pre-registration v1.0, A1-A11, scorecard v2 + benchmark
  evidence. Amendments are append-only in `docs/prereg-addenda-d19.md` (§6.16);
  v1.1 (A9 canonical hash 5bcdc813...0910 + CC0 vendoring record) landed with M2a.
- **M2a DONE (D20)**: A9 vendored+checksummed loader with hard-fail provenance gate;
  `load_mauna_loa_training` (mechanical §6.6 seal); A10 period frozen at exactly 1.0
  (7 pyro sites, tested); A4 registry with both universes + shared Quad+2Harm alias +
  merge guard (harmonized 3-set: period 1.0, sine convention, D11 multi-start
  full-NLL, no differential_evolution); pw_kl_vcal + tau grid 0.1/0.3/1/3/10 wired;
  SamplerDiagnostics schema (fit_hmc return_diagnostics option; D9 default return
  unchanged); slurm refresh + AST argparse guard. Gates: scorecard_v2.json
  regenerated byte-identically on every review round; suite 175 passed. No pilot, posterior,
  or Mauna BMS* number exists; registry tests are synthetic-fixture-only.
- **HOLDOUT SEALED**: no selection analysis loads/plots/scores the 60 test months
  until the D19 author decision is recorded (prereg §6.6). Study-facing code uses
  `load_mauna_loa_training` from now on.
- **No BMS*/pilot/posterior result exists yet**; the ordering/blinding rule (§6.5)
  governs from here on.
- **M2b code COMPLETE; closeout gated on the M2bR corrective milestone (D21-D26,
  branch `feat/d19-m2b-e1`, 2026-07-11; PR to open as DRAFT)**: the codex
  meta-review (author-forwarded) reframed D22-D24 as a baseline change needing
  its own milestone — adopted as prereg v1.8 + docs/d22-d24-impact-audit.md
  (classification with dependency verification + author ratification checklist)
  + an interim UserWarning layer on fit_hmc/fit_vi/fit_hmc_laplace (no default
  changed; fork OPEN in D26). M2bR before M2c: ratifications, API disposition,
  small preregistered corrected-impact rerun (D12/D18 sampler arms),
  d19_bench.py firewall rework, W2/W3 re-openings.
- **M2b contents**: prereg addenda v1.2-v1.8 (append-only): v1.2 author
  coordinate convention (E1 public coordinates = pyro initialize_model sites;
  gpytorch raw internal-only); v1.3 the D22/D23 S1-target findings; v1.4
  frozen battery tolerances + point sets; v1.5 microbenchmark + final A6
  budgets + frozen A5 fallback (N_fb=232, linspace rule,
  timing/leapfrog/budget-only predicate); v1.6 codex-round corrections
  (append-only after be08285's in-place edits were reverted); v1.7 wording
  erratum; v1.8 the D22-D24 impact amendment (M2bR). Code:
  `bistar_gp/e1_potential.py` (E1Potential + fit_hmc_e1), the battery
  `tests/test_e1_potential.py` (31 collected), firewalled
  `experiments/d19_e1_bench.py` + artifact
  `runs/d19_planning/e1_nuts_microbench.json`, UserWarning layer on the three
  affected samplers. Suite 207 passed + 1 skip. Review: three codex
  gpt-5.6-sol (xhigh) rounds (14 + 5 + 3 findings, all resolved) + the
  adopted meta-review (D26).
- **TWO CORRECTNESS FINDINGS while building E1 (author attention required)**:
  (D22) the obs pyro.plate made fit_hmc/fit_vi/fit_hmc_laplace target
  p(theta)L(theta)^N — FIXED, but every pre-fix HMC/VI result carries the
  v1.3 standing caveat (D8 Mauna impact HMC, D12 hmc/vi numbers, D18 HMC
  headline 0.696/0.683, HMC figure caches); re-labeling ratified records =
  QUEUED author decision. (D23) pyro autograd through the traced gpytorch
  target loses kernel-site likelihood gradients (noise survives by accident);
  S1 stays as-is (upstream), E1 immune; battery gradient reference = central
  FD of the oracle. Also (D24) create_graph double-backward through the
  marginal log-prob is silently wrong (~16%): S2's M2c mass matrix must be
  built from first-order FD of the E1 gradient. The planning cost table's
  "~200x deep-copy penalty" was mostly the plate: corrected S1 potential is
  6.0/10.5 ms (sub/full); E1's real advantages = correct gradients (S1
  saturates td7: 127 lf/draw vs S1f 6.7 at sub-150) + no deep copy.
- **BALLOT RETURNED (D29, v1.11): items 1-7 RATIFIED** (item 4 restricted:
  leapfrog fields = aggregate engineering cost only); **item 8 pending its
  D29 revision** (overdispersed prior-IS starts, authority-coverage
  criterion, 6 h full design) **+ D30 preflight** (preflight_start_state +
  select_start_state deterministic fallback, v1.12; codex-implemented, suite
  230+1); **item 9 mechanism ratified**, split diagnostics implemented
  (schema v3), numeric pair (1e-3 fail rate, 50-draw window) pending.
  ROWS 8-9 RATIFIED by the author in their own words (D31, v1.13) — ALL 9
  items now ratified; PR #7 set READY. NEXT (author's explicit calls, not
  done autonomously): merge M2b, then run M2bR as a separate PR opening with
  the two-stage start-freeze. Originally proposed as D27/D28 (v1.9/v1.10)**:
  superseded standing, firewall
  reading, A5 N=232 (trigger corrected: non-legacy sub-150 G-B eligibility;
  no eligible survivor = O4; S1-only branch removed), dimensioned A6
  ceilings, Draft-PR route, scope-of-claim rule. API rerouted (public
  fit_hmc = E1; fit_hmc_legacy_pyro explicit; vi/hmc_laplace behind
  allow_legacy=True). M2bR rerun protocol FROZEN
  (docs/m2br-corrected-impact-protocol.md — D28: AUDIT layer only,
  single-chain, cannot close W2/W3; re-pinned in v1.10; multi-chain
  validation layer proposed in docs/m2br-validation-protocol-PROPOSAL.md).
  D28 NotPSD rejection policy implemented (schema v2 notpsd_rejections).
  Suite 218+1.
- **Della (A7) ON HOLD (v1.8)**: no Della run until d19_bench.py is reworked
  to the timing-only firewall (it persists a MAP hyperparameter value under
  the M1-era convention) and key-inventory audited; pre-D22 Della anchors are
  superseded the same way as §1.1; the thread-pinning addendum lands after.
- OPEN, tracked in the doc: era/source transcription (§8; amendment rule armed —
  before Stage A); M2c predicate numbers (S2/S3/G-toy tolerances,
  divergence-clustering against the D20 schema, M1 overlap diagnostic, corrected
  normalized profile band masses); G0 sign-off at M2d.

## Prior-sensitivity study (W2 gate) — DONE 2026-07-08, CLOSED 2026-07-10 (D18)

`experiments/prior_sensitivity_study.py` + `docs/prior-sensitivity-study.md` +
`runs/prior_sensitivity/` (local). Bimodality is prior-induced (kernel Gamma(6,0.85)
priors; noise prior innocent). Sin+Linear survives every prior under HMC/MAP and under
the new mass-faithful SIR arm. Headline = SIR Sin+Linear 0.441 at tau=1,
posterior-mass-faithful under the fixed data-elicited prior (W5/D18 terminology
correction: ±0.005 is the conditional SIR bootstrap SE given the realized pooled IS
draws and weights; independent-pool estimates 0.419/0.438/0.431 are the separate
second uncertainty component, never combined); HMC 0.696 (td7) / 0.683 (td10) =
density-mode-region answer. D18 Status forks a/b/c all CLOSED 2026-07-10
(ratification 2026-07-09, scope-tightened to the N=20 thesis toy); the viz gate
resolved "passed but not exercised" — full record in D18.

## PR #4 — MERGED to main 2026-07-10 (merge commit fcd70e2)

Implementation of the D18 ratification: `PRIOR_CONFIGS["toy_elicited_n20"]`
(registry-only), STUDY_CONFIGS swap (fingerprint verified unchanged against the
on-disk sidecars), `--stage figures` (Figures A/B from existing artifacts only,
assert-equal validation at rtol=0/atol=1e-12), 7 regression tests
(`tests/test_prior_sensitivity_figures.py`, incl. a hermetic synthetic-artifact
test and negative validation gates, hardened after the codex 5.6 sol + Fable
review round), D18 Status closure, `docs/fit-method-metric-comparison.md` and
`docs/prior-sensitivity-study.md` regenerated via their generators. Local-only
companions (gitignored, same session): W4 gate paragraph updated in
Notes/WRITEUP_DECISIONS.md; kb/Wiki touch-ups (Paper Writing Guide 7.2, HMC vs MAP
for GP Posteriors, Metric Choice Justification kl_forward paragraph).

## Done this session (D11/D12/D13, comparison campaign)

- **Method × metric comparison (D12, corrected by D13)** —
  `experiments/fit_method_metric_comparison.py`, tables in
  `docs/fit-method-metric-comparison.md` (+ capped-NUTS appendix
  `docs/appendix-tree-depth-cap.md`, `_td7` outputs). Corrected headlines: toy posterior
  BIMODAL under `informative` priors — low-noise mode = global DENSITY max (MAP, −33.4);
  high-noise prior-scale mode holds ~3× the MASS (prior-IS 0.19/0.67). hmc/map/hmc_laplace
  report the density-mode basin and pick Sin+Linear under every metric (hard assignment
  200/200); VI migrates to the dominant-mass basin and picks Sinusoidal — thesis App. II
  "VI ≈ HMC" does not replicate; reads as PRIOR MISSPECIFICATION expressed through method
  choice. pw_kl_vcal ≡ pw_nll_gp empirically; kl_forward sharpest but brittle; pw_kl_vcal
  default results-confirmed; METHOD default is now a real user fork (density mode vs mass —
  see D12 Decision). depth-7 cap: ~9× cheaper, model posteriors shift ≤0.011. Raw draws
  cached (`runs/fit_method_metric_comparison/samples_*.npz`) — sampler hours never re-paid.
- **candidates.py restart-selection bug (D11)** — multi-start MLE selection was a no-op
  (criterion constant n/2 at any MLE); Sin+Linear had collapsed to a degenerate near-linear
  fit (same no-op + a tuple-unpack breakage in the two Mauna candidates, codex catch).
  Fixed via full-NLL comparison at all six `_fit_mle` call sites + `tests/test_candidates.py`.
  First-run outputs preserved as `results_degenerate_candidates.json`.
- **fit_mcmc_simple sampled the wrong measure (D13)** — raw-space MH without the softplus
  Jacobian; inflated small-hyperparameter mass ~3× and briefly inverted the D12 mass story
  (caught by a post-commit codex verification, upheld by independent prior-IS + exact-mode
  optimization; D12 corrected in place). Fixed via `_raw_log_jacobian` in the MH target +
  analytic regression test. **92 tests pass.**

## Task 2 batch 2b — LANDED (D16 estimators + D17 ports/harness); remaining below

D17: both viz scripts ported onto the package (legacy pinned at a87356a), shared
`_viz_spaces.py`, rerunnable comparison harness with an attribution ladder + τ-overlay.
Headline: the legacy scripts CONTRADICTED each other at n=50 (priors: Linear 0.693;
trajectory: Sin+Linear 0.934) — attributed dominantly to the priors script's hard-wired
occam-ON convention (volume penalty against the d=5 true model), secondarily to pure
Laplace; canonical figures (occam=False, IS estimator) select the true model 0.93–0.99.

**Full-quality figures DONE (2026-07-06, corrected + hardened after codex post-run
review):** canonical arms give Sin+Linear 0.86–0.99 at every n, both scripts exactly
consistent at shared stages; codex's independent 200k-n_is rerun confirms the headline
(n=50 canonical still 0.992). CORRECTION (codex): ESS warnings fired at the PRIMARY
τ=0.3 for Sinusoidal at intermediate stages — a proposal-coverage gap (fixed starts miss
data-dependent basins), not a sample-count problem (the n=50 τ-sweep is healthy at 200k,
min ESS 955). Hardened: both ported scripts now default to seeded perturbed starts
(--n-perturb 5) anchoring the IS proposal, and the trajectory port emits a per-stage
per-model `ess_by_stage.md` diagnostic; stale first-layout legacy figures removed from
`runs/viz_unification/`. **PR #2 is ready to flip from draft** (since merged as
a9253fb). **Paper-grade artifact directory DONE (codex caveat resolved):**
`runs/viz_unification/` regenerated from empty in ONE clean harness run with the hardened
scripts — zero ESS warnings in every log, same-run `ess_by_stage.md` (worst 166), 26
figures, all artifacts in a single 10-min timestamp window; headline reproduced exactly
(canonical n=50 Sin+Linear 0.992 vs legacy priors Linear 0.693). codex's independent
200k set kept at `runs/viz_unification_highis/` as the cross-check.
The three deferred items are now ALL DONE (2026-07-07/08): Mauna candidate recheck
post-D11 (523825c), non-viz figure regeneration (D3 item 2, see below), kb/Wiki update
(D3 item 3). D3 is fully CLOSED.

### superseded planning note (plan now at R2 + implementation addenda)

Two adversarial verification runs (2026-07-06) resolved the open forks with measurements:
pure Laplace FAILS the τ-sweep (ranking flip at τ≈88, gap 0.45 at τ=316, and 0.1–0.25
mid-range distortion) AND plain MC fails low-τ (ESS<200 below τ≈0.3) — hybrid needed both
ways; averaged-GP moment formulas match to 2e-16 with all port differences enumerated.
R1 changes after codex review (all 9 outcomes dispositioned, plan §7): defensive-mixture
IS (`is_log_Z_Mx`) replaces the fixed-window hybrid as the reference estimator (the R0
blend was pure Laplace at exactly the τ=0.3 panels it claimed to fix); legacy scripts'
verified inconsistencies (Linear bounds, occam ON vs OFF, multi-start styles) resolved by
unify-with-disclosure; prior parity pinned to PRIOR_CONFIGS['informative'] (build_toy_kernels
uses Gamma(2,2) — mismatch); rng= param on extract_gp_predictives; rerunnable harness via
git-show of the pinned commit; 9-item test checklist in plan §6.

### superseded design sketch (kept for the record)

Port `bistar_viz/scripts/model_priors_laplace.py` (515 ln) and
`model_prior_trajectory_laplace.py` (542 ln) onto `laplace_log_Z_Mx` (D10 unblocked; D15
machinery committed at 641444a). Design decisions already made:
- **Spaces**: build sigma-free `ModelParameterSpace`s IN the scripts mirroring their own
  bounds/parameterizations (NOT `build_toy_parameter_spaces` — different bounds, plus a
  sigma param that adds a flat direction; legacy-figure comparability wins).
- **Multi-start**: external — loop each model's legacy `inits`, call
  `laplace_log_Z_Mx(mle_params=init)` per start, keep min `G_at_min` (D11 lesson: Ḡ has
  local minima in ω; package API stays single-start).
- **Averaged GP**: replace prior-IS `compute_averaged_gp` with `extract_gp_predictives`
  plus `aggregation_v3.average_gp_posterior`; draw source via `--gp-method` flag (map
  default for the n-sweep figures per D9's "clean deterministic demonstrations" case;
  vi/hmc selectable; the n=0 stage via `sample_prior` + `condition_on_data=False`).
  Disclose the estimator change vs legacy prior-IS figures.
- **Trajectory-script fork (surface with evidence, don't silently resolve)**: it uses a
  Laplace/MC HYBRID (`compute_Z_hybrid`: Laplace low-τ, uniform-box MC log Z high-τ,
  sigmoid blend) because pure Laplace degrades as τ flattens exp(−Ḡ/τ). Option (a) pure
  Laplace + verify the high-τ tail vs the legacy hybrid; (b) add an optional MC Z_Mx
  estimator to the package. Lean (a); check the tail first. The analytic τ-rescale makes
  Laplace trajectories nearly free either way.
- Then: figure regeneration + legacy comparison, codex review (stdin: `< /dev/null`!),
  D16, flip D3 open item (1), PR #2 to Ready (since merged).

## Mauna candidate recheck post-D11 — DONE (2026-07-07)

- Reversal headline VERIFIED on the fixed restart selection: HMC reproduces
  bit-identically, BMS* posteriors shift at most 0.00002 (Quad+2Harm 0.42218 vs Linear
  0.11368 at pw_kl_forward@tau1). All 12 restarts of each Mauna candidate share one
  basin (fixed frequencies) — the toy omega pathology has no analog here. Recheck
  subsection in docs/impact-assessment-results.md; raw runs/mauna_recheck_postD11.json;
  D11 Result updated.

## D12/D13 gates RESOLVED (user, 2026-07-07) — logged in Notes/WRITEUP_DECISIONS.md

- `metric_name="pw_kl_vcal"` RATIFIED as main/default; `kl_forward` to the appendix as a
  covariance-sensitive stress-test metric (W1; no code change).
- METHOD default: keep `hmc` for package/paper draft with the mass split disclosed loudly;
  basin-occupancy check is a required diagnostic; prior-sensitivity / re-elicitation study
  QUEUED before final paper numbers (W2). NOT switching the default to VI.
- VI framing: bimodality/prior-sensitivity story, with recorded paper phrasing (W3).
- `Notes/WRITEUP_DECISIONS.md` is the new paper/writeup decision log (gitignored,
  local-only; entries W1–W3 so far).

## Done this session (on `fix/laplace-zmx`, PR #2)

- **Z_Mx / Laplace reconciliation** (DECISIONS D3) — Construction II canonical. Canonical API in
  `laplace_evidence.py` (`laplace_log_Z_Mx`, `laplace_log_evidence_ordinary`/`_induced`,
  `model_posterior(baseline|I|II)`, `_laplace_logdet`); callers migrated; figures redesigned
  (decomposition + ablation ladder); deprecated `compute_(all_)laplace_evidence`/`LaplaceResult`
  removed; module self-registers its default metric. **42 tests pass.**
- **Eval follow-ups:** `pyproject.toml`; dedup `build_toy_kernels`; `InducedPriorResult` collision
  renamed; optional RNG `seed=` on `fit_mcmc_simple`/`fit_hmc`; `numerical_hessian` boundary issue
  fixed in the new module via `_laplace_logdet` (old copy removed).

- **Code review (Fable, 8-angle) + D4 fixes** — review of the branch diff surfaced 33 findings
  (10 severe). Fixed the top cluster (DECISIONS D4): stale `kernel_components` sample-key parsing
  in `bms_star`/`debias`/`aggregation_v3`/`mechanism` (kernel posterior draws silently dropped),
  double noise latent in `fit_hmc`, eval-mode MH target + duplicate proposal dim in
  `fit_mcmc_simple`. New naming helpers `select_hmc_sites`/`apply_hp_value` in `model.py`.
  **56 tests pass** (14 new).

- **Review findings round 2 fixed (DECISIONS D5)** — occam flag now applies the −log V_ref
  reference term consistently across constructions (ablation-ladder gaps volume-free); `Z_Mx`
  computes τ analytically on H_Ḡ (clipping τ-invariant) and `n_clipped` propagates with a warning;
  `soft_transfer_weighted` global-scalar max shift. **63 tests pass** (7 new).
- **Last two severity-3 findings fixed** — `impact_assessment.compare()` diffs the union of old
  and new keys (a section erroring on one side reports as CHANGED instead of vanishing; report is
  now trustworthy for the Della rerun); `bistar_viz/scripts/bistar_sample_size_sweep.py` sys.path
  bootstrap points at the repo root after the file move (runs directly again). **65 tests pass.**
- **Multi-model review + D6 fix** — 5-model panel (Gemini 3.1 Pro / Kimi K2-thinking / GLM-5.2 via
  OpenRouter; codex/gpt-5.5; Fable adjudicating). codex alone caught that `fit_hmc` sampled the
  PRIOR not the posterior (`_hmc_pyro_model` discarded the return of `pyro_sample_from_prior()`).
  Fixed in D6: score through the returned sampled module + new connection regression test. **66
  tests pass.** Kimi's `×n` CRITICAL was a false positive (verified); `fit_mcmc_simple` Jacobian is
  a pre-existing non-blocking follow-up. Panel verdict: NO-GO pre-fix, GO after D6.
- **Prior/posterior predictive sampling (D7)** — `fit.sample_prior` (i.i.d., no NUTS) +
  `extract_gp_predictives(condition_on_data=)`: one pipeline for both prior and posterior predictive
  checks. **72 tests pass** (6 new). Adversarially reviewed: SHIP, no defects.

- **Inference + G options, thesis-anchored (D9/D10)** — `fit_gp(method=hmc|vi|map|hmc_laplace)`,
  one shared samples schema, defaults per thesis Ch.5 (full-Bayes sampling; VI was its primary
  implementation, HMC the cross-check, MAP the contrast). D10: the "single-G decision" DISSOLVED —
  viz variance-weighted MSE ≡ `pw_kl_vcal` (verified to 1e-12), so the default already matches both
  thesis (KL variant) and viz figures; **viz unification UNBLOCKED**. Writeup-ready justifications in
  `docs/inference-and-metric-options.md`. **84 tests pass** (9 new).

## Still open (held deliberately)

- **Remaining review findings** — ~20 severity-2 cleanups (duplication in laplace_evidence
  closures, redundant recomputation in plot_ablation_ladder/tau sweeps, committed .pyc/.DS_Store
  artifacts, walrus-in-ternary in impact_assessment, CLAUDE.md prose nits; full list in the
  review output).
- ~~**HMC archives invalid**~~ RESOLVED (2026-07-08): the five `bistar_gp/cache/*.npz`
  caches regenerated fresh on the fixed code (pre-D2 originals quarantined in
  `bistar_gp/cache/stale_preD2_20260214/`); the stale `runs/mauna_loa_sub150_hmc_*`
  archive is superseded by the regenerated Mauna figure sets under `runs/figures_regen/`
  (left on disk — never reuse). Impact assessment reran long ago (toy: Della; Mauna:
  local 2026-07-04; recheck 523825c).

- **Viz-script unification (UNBLOCKED by D10)** — port `model_priors_laplace.py` /
  `model_prior_trajectory_laplace.py` onto `laplace_log_Z_Mx` with `metric_name="pw_kl_vcal"`
  (proven identical to their G) and posterior draws (better estimator than their prior-IS).
- **Old-vs-new impact assessment: toy sections DONE on Della** (job 10608943, 2026-07-03) —
  `docs/impact-assessment-results.md`. Quantifies the D2 fixes: latent sites 7 down to 4, decompose
  full_std order-of-magnitude correction, mcmc_simple ~8x tighter, soft_transfer shifts.
  **`--mauna` section UNBLOCKED (D8)**: fit_hmc gained init_to_map + max_tree_depth; the
  tree cap (7) is the operative fix — head-to-head 1.04 s/it vs 4.9–8.2 s/it, identical
  posteriors. impact_assessment passes it via signature dispatch; both Mauna experiment
  scripts fixed (were MAP-fitting one model, HMC-ing a fresh default one). codex review
  FIX-FIRST findings verified + fixed (boundary-underflow init guard). **75 tests pass.**
  **`--mauna` real-data results DONE (local, 2026-07-04)** — docs/impact-assessment-results.md
  real-data section. Headline: BMS* model selection REVERSES on Mauna Loa CO2 (old picks
  Linear 0.99; new picks Quad+2Harm 0.42) — the D4+D6 fixes change the scientific conclusion.
  Mechanism: old HMC = prior (noise 1.58±1.09 ≈ GammaPrior), new = posterior (noise ≈0.001);
  latent sites 13 down to 7; decompose 0.92 down to 0.03. NEW chain NOT converged (ESS≈1, Rhat 4–81) so exact
  probs soft but DIRECTION robust (mechanistically forced by near-zero noise). Ran locally
  (Della abandoned: della-h16 ~5× slower/op + thread-thrash + jitter-retry ballooning). Noise-
  prior change remains a deliberately-untaken MODELING decision; converged full-Bayes = open fork.
- ~~**Figure regeneration**~~ DONE (2026-07-08) — all non-viz figure sets regenerated on
  the fixed code via the detached two-wave orchestrator `runs/figures_regen/regen.sh`
  (system python3, miniconda base, torch 2.10): wave 1 rebuilt the five HMC caches
  (`bms_star_toy --force-rerun`, uncapped as shipped, ~18 h) plus toy_example x2,
  mauna_loa, and the bms_star_mauna_loa + debias chain (debias fed
  `--use-cache runs/figures_regen/bms_mauna_loa/hmc_samples.pt` to bypass its own
  un-capped default-init HMC block — that bug is flagged as a separate task); wave 2 ran
  the five cache-dependent scripts (induced_prior, induced_prior_v2, sample_size_sweep,
  v2/v3_comparison). 151 figures (18 under `runs/figures_regen/`, 133 in
  `bistar_gp/results/`), zero errors across 11 logs (`runs/figures_regen/logs/`). The
  full-data Mauna BMS* chain mixes slowly even at depth 7 (~8 min/step) — figures carry
  the D8 convergence caveat. Sandbox-era viz scripts (mechanism_unified, pipeline_figure,
  model_priors_montecarlo, model_prior_both) import nothing from bistar_gp — unaffected
  by the fixes, not regenerated.
  ADDENDUM (2026-07-08, post-codex closeout check): codex noted 76 February PNGs still
  mixed into `bistar_gp/results/` alongside the fresh set. Resolved: 68 were prior-config
  gaps the wave-2 defaults skipped — regenerated from the fresh caches
  (`--priors low_noise high_noise` for induced_prior x2; `--priors vague
  misspecified_tight low_noise high_noise` for v3_comparison; `*gapfill.log`); the 8 true
  orphans (renamed `bms_tau_informative`, six `mauna_loa_map_*` from a February
  CWD-in-results run — regenerated equivalents in `runs/figures_regen/mauna_loa/` — and
  the v2 tau=10 grid point) are quarantined in `bistar_gp/results/stale_preD2_20260214/`.
  `bistar_gp/results/` now contains ONLY post-fix figures (203) outside the quarantine.
- ~~**kb/Wiki/GP-Induced Model Priors.md**~~ DONE (2026-07-07) — rewritten to
  Construction II canonical (gitignored, local).
- **Occam default** — currently `occam=False` (faithful BI*); with-Occam intended as sensitivity.
- Minor: remove the 13 `sys.path` hacks now that `pyproject.toml` exists (`pip install -e .`);
  add a cache key covering all result-determining config.

## Cleanup backlog — 8-angle review findings (2026-07-01), annotated vs D4–D13

Reconstructed from the original review; every FIXED/OPEN status re-verified against the
tree at HEAD 6573ff0. 33 kept findings + 1 refuted. Anchored by symbol (lines have moved).
Fold the `laplace_evidence.py` efficiency items into the viz unification (D10 unblocked it) —
you'll be editing those plot functions anyway.

### OPEN — execute these

Correctness-adjacent / deferred:
- [x] laplace_evidence.py :: numerical_hessian + _laplace_logdet :: not bounds-aware; the
  [1e-8,1e12] clip CONSTANTS set the Occam term at a bound-pinned MAP (~+9.2 nats/flat dir).
  D5 surfaced n_clipped but deferred the bounds-aware refactor :: S3-PLAU
- [x] laplace_evidence.py :: plot_evidence_decomposition / plot_prior_penalty_comparison ::
  read Construction-II-only component keys (log_lik_at_map, gp_penalty) with no
  `result.construction` guard → KeyError on a construction="I"/"baseline" result :: S2

Efficiency (redundant recompute — also speeds figure regeneration):
- [x] laplace_evidence.py :: plot_tau_effect_on_evidence :: re-runs full Laplace at every τ
  though baseline is τ-independent and Construction-I rescales analytically :: S2
- [x] laplace_evidence.py :: plot_ablation_ladder :: recomputes laplace_log_evidence_ordinary
  for both "baseline" and "I" per model (identical inputs) :: S2
- [x] laplace_evidence.py :: laplace_log_evidence_induced :: recomputes ll_at via
  _log_likelihood though _laplace_log_N's detail already holds log_lik_at_map :: S2
- [x] experiments/bistar_induced_prior_v2.py :: main → plot_ablation_ladder :: re-runs
  model_posterior(construction="II") already computed earlier in the same loop :: S2
- [x] laplace_evidence.py :: numerical_hessian :: computes f0=f(x) but never uses it, and the
  diagonal (i==j) uses the 4-point cross stencil (~2d+1 redundant objective evals) :: S2

Duplication / reuse:
- [x] laplace_evidence.py :: neg_log_f/neg_log_joint closures + _log_likelihood +
  compute_G_at_params :: the `noise_param, 0.3 <= 0` guard and magic 0.3 default are
  copy-pasted across 5 sites (drift silently desyncs Z_Mx / ordinary / N(M)) :: S2
- [x] laplace_evidence.py :: _log_likelihood :: re-implements the iid Gaussian log-likelihood
  (incl. the 0.3 default) rather than reusing a shared primitive :: S2
- [x] laplace_evidence.py :: model_posterior :: hand-rolls shift-by-max softmax
  (np.exp(logk - logk.max())) — another copy of a normalization snippet :: S2
- [x] experiments/impact_assessment.py :: mauna() :: duplicates the pyro latent-site
  trace/count block verbatim from collect() :: S2
- [~] tests/test_laplace_zmx.py :: lin_space()/quad_space() :: re-implement Linear/Quadratic
  ModelParameterSpace that bistar_gp.induced_prior already builds :: S2-PLAU

Dead code / artifacts:
- [x] laplace_evidence.py :: _packers :: returns (pack, unpack) but `pack` is dead at all 3
  call sites (`_, unpack = _packers(...)`) :: S2
- [x] bistar_viz/scripts/bistar_sample_size_sweep.py :: per-n_sub loop :: dead mutation
  `spec.mle_value = ...` (nothing reads it; leftover from removed compute_all_laplace_evidences) :: S2
- [x] conftest.py :: root sys.path shim :: now redundant — pyproject.toml exists and its own
  comment says "Remove once the project ships a pyproject.toml" (ties into the 13 sys.path hacks) :: S2
- [x] experiments/practice_EvansEtAL/__pycache__/*.pyc :: 6 committed .pyc artifacts the D1
  hygiene sweep missed :: S2

Prose (CLAUDE.md writing-style rules):
- [x] README.md :: "Z_Mx is the **data-free** GP model prior" :: "X is the Y" label ban :: S2
- [x] docs/plan-zmx-laplace.md :: "...are the ingredients." :: "ingredient" metaphor ban :: S2

### OPEN — severity-1 (never addressed — FLAGGED)
- [x] **laplace_evidence.py :: module imports :: `build_toy_parameter_spaces` and
  `average_gp_posterior` imported but unused (1 occurrence each) :: S1**
- [x] **Notes/DECISIONS.md :: prose :: right-arrow (→) chars — CLAUDE.md ban; 16 occurrences and
  GROWING (D4–D13 entries added more) :: S1**

### FIXED
- [x] bms_star.py :: extract_gp_predictives :: stale 'kernel_components' filter dropped kernel draws :: S5 → D4
- [x] fit.py :: fit_hmc/_hmc_pyro_model :: noise prior registered twice → phantom prior-only latent :: S4 → D4 (+D6)
- [x] mechanism.py :: *_mechanism_config hp_patterns :: 'kernel_components.*' no longer matched :: S4 → D4
- [x] fit.py :: fit_mcmc_simple :: MH target scored in eval mode (data twice) :: S4 → D4 (D13 added Jacobian)
- [x] debias.py :: decompose_model_hmc :: same stale 'kernel_components' filter :: S4 → D4
- [x] aggregation_v3.py :: soft_transfer_weighted :: per-candidate (axis=0) max shift distorted posteriors :: S4 → D5
- [x] laplace_evidence.py :: ordinary vs model_posterior :: occam=False V_ref inconsistent across constructions :: S4 → D5
- [x] laplace_evidence.py :: _laplace_logdet/_laplace_log_integral :: n_clipped discarded :: S3 → D5 (floor magnitude still OPEN)
- [x] impact_assessment.py :: compare() :: key set only from NEW json (old-only vanished) :: S3 → severity-3 pair
- [x] bistar_viz/scripts/bistar_sample_size_sweep.py :: sys.path bootstrap :: '..' = bistar_viz/ not root :: S3 → severity-3 pair
- [x] bistar_viz/scripts/bistar_sample_size_sweep.py :: docstring :: stale 'python experiments/...' path :: S2 → severity-3 pair
- [x] impact_assessment.py :: compare() :: walrus-in-ternary counter :: S2 → fixed w/ compare() union commit

### SUPERSEDED (not actionable)
- [~] Notes/DECISIONS.md :: D3 status in a later commit than the change (same-commit rule) :: S2 —
  past-commit process observation; D4–D13 all comply going forward
- [~] Notes/SCRATCHPAD.md :: "This is the *" openers :: S1 — flagged content gone (rewritten); watch style

### REFUTED by the review's own verifier (do NOT action)
- impact_assessment.py :: _git_sha :: claimed to dup run_manager._git_hash — REFUTED (both exist)

## Branches / PRs

- **PR #1** — MERGED to `main` (hygiene, 5 correctness fixes, plan, Notes workflow).
- **PR #2** (`fix/laplace-zmx`) — MERGED to `main` 2026-07-10 (merge commit a9253fb;
  original commits preserved, pinned hashes like a87356a stay valid).
- **PR #3** (`study/prior-sensitivity`) — MERGED to `main` 2026-07-10 (merge commit
  7069ea6).
- **PR #4** (`feat/toy-elicited-n20-figures`) — MERGED to `main` 2026-07-10
  (merge commit fcd70e2; commits 8141703 + 5b77619 W5 terminology correction +
  7dcb9cb Figure A caption layout; see the PR #4 section above).
