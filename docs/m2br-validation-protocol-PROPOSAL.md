# M2bR scientific-validation layer — PROPOSAL (multi-chain; pending author ratification)

Status: PROPOSAL, REVISED PER THE AUTHOR'S ITEM-8 VOTE (D29, 2026-07-11:
same-MAP chain starts rejected — four same-start chains can miss the same
basin and still pass R-hat/ESS/internal occupancy agreement), plus the D30
start-state preflight + deterministic next-eligible fallback. STILL PENDING
EXPLICIT AUTHOR RATIFICATION of rows 8-9 in the author's own words (the D28
rule bars treating forwarded advice as a vote). Nothing here runs until the
author ratifies this revised protocol and the M2b PR merges. Companion to
`docs/m2br-corrected-impact-protocol.md`, whose six single-chain runs are a
controlled HISTORICAL-IMPACT AUDIT only — this layer is what can support
replacement scientific conclusions and the W2/W3 re-openings, and only if
its acceptance criteria pass.

## Purpose split (D28)

- AUDIT layer (already drafted, single-chain, seed 42): isolates the D22/D23
  correction's effect on the historical numbers by mirroring the original
  one-chain design exactly. Output label: "corrected single-chain
  comparison". Cannot validate basin exploration or convergence; cannot
  close W2/W3.
- VALIDATION layer (this proposal, multi-chain): establishes whether the
  corrected E1 sampler's characterization of the two PIVOTAL toy posteriors
  is reproducible across independent chains, with preregistered convergence
  criteria. Only results passing acceptance may be cited as replacements or
  used to re-decide W2/W3.

## Runs (proposed)

Configurations: `informative` and `toy_elicited` (the two pivotal D18/W2
configurations). Same frozen toy data, candidates, MAP-init procedure,
metrics, and predictive scoring as the audit protocol (its §1, by
reference).

| Layer cell | Config | Depth | Chains (independent seeds) | Iterations per chain |
|---|---|---|---|---|
| V1 | informative | td7 | 4 (seeds 0/1/2/3) | 1000 warmup + 2000 draws |
| V2 | informative | td10 | 4 (seeds 0/1/2/3) | 1000 warmup + 2000 draws |
| V3 | toy_elicited | td7 | 4 (seeds 0/1/2/3) | 1000 warmup + 2000 draws |
| V4 | toy_elicited | td10 | 4 (seeds 0/1/2/3) | 1000 warmup + 2000 draws |

Chain seeds are disjoint from the audit layer's seed 42; the audit chain is
never pooled into validation statistics.

### Overdispersed initialization (D29 revision; replaces same-MAP starts)

Per cell, the four chains start from FROZEN, distinct constrained states:

- Chain seed 0: the MAP init (the S1f default; doubles as the
  near-reference NotPSD sentinel).
- Chains seeds 1/2/3: overdispersed starts drawn from the config's existing
  UNAFFECTED authority references (the D18 prior-IS pools; audit table 1) by
  a deterministic rule: for every reportable noise band of that config
  (authority mass >= 5%, the §6.15 reportable-band convention, computed from
  the pooled prior-IS bands), one start = the band's weighted-median draw
  (the pool draw whose noise value equals the weighted median within the
  band; ties resolve to the lowest pool index). If a config has fewer than
  three reportable bands, the remaining chains fill with the weighted q25
  and q75 draws of the largest-mass band. Every noise band with material
  authority mass therefore contributes a chain start.
- DETERMINISTIC PREFLIGHT (D30): before a selected state is pinned, it must
  pass `bistar_gp.e1_potential.preflight_start_state` — exact site set,
  successful constrained/unconstrained round-trip (within
  PREFLIGHT_ROUNDTRIP_TOL = 1e-10 relative), finite E1 potential AND first
  gradient, and no terminal NotPSD at initialization. A selected draw that
  fails preflight is replaced by the NEXT-ELIGIBLE authority draw under the
  same deterministic rule (for a band start: the pool draw with the next
  noise value away from the weighted median, ties to the lowest index),
  never a manually chosen replacement. `select_start_state` applies the
  preflight down the preregistered priority-ordered candidate list and
  returns the first pass; if a cell exhausts its eligible candidates the
  cell is reported un-startable rather than hand-patched.
- TWO-STAGE FREEZE: this selection RULE (including the preflight and the
  next-eligible fallback ordering) is frozen now; the realized pool indices,
  the number of fallback advances used, and the sha256 of each serialized
  start state are pinned in a pre-run M2bR addendum BEFORE any chain launches
  (the pools are local artifacts, so realized pins cannot be committed
  earlier than that).
- Mechanics: chains 1-3 pass their frozen constrained states through
  fit_hmc_e1's init_values parameter (D29 capability; validated site set +
  boundary guard, then pyro init_to_value).

### Authority-coverage criterion (D29 addition)

Internal cross-chain agreement cannot detect four chains missing the same
basin, so the pooled chain occupancy is additionally compared against the
INDEPENDENT authority (the config's prior-IS pooled band masses — an
unaffected reference): per reportable band,

    |pooled_chain_band - authority_band| <= 2 * sqrt(SE_auth^2 + SE_chain^2),

with SE_chain = sqrt(p(1-p)/bulk ESS) — the §6.15 coverage convention
reused verbatim rather than a new tolerance. A cell failing authority
coverage fails validation regardless of its internal diagnostics. Every chain runs
`fit_hmc_e1(..., return_diagnostics=True)` with the D28 NotPSD rejection
policy active; per-chain artifacts persist samples, the full
SamplerDiagnostics payload (schema v3, including the warmup/post-warmup NotPSD rejection split), and
hashes, with the audit protocol's atomic-rename convention.

## Diagnostics and acceptance criteria (proposed prereg values)

Computed per cell over its 4 chains, via arviz (version pinned in the
artifact metadata; installed reference 0.23.4) on the 7-site constrained
draws:

| Criterion | Proposed threshold | Anchor |
|---|---|---|
| rank-normalized split R-hat, every site | < 1.01 | Vehtari et al. 2021 convention |
| bulk ESS and tail ESS, every site, pooled | > 400 (= 100 per chain) | §6.15 ESS floor scaled to 4 chains |
| per-chain basin occupancy (noise bands low/mid/high per the audit protocol §1) vs pooled | max abs deviation <= 0.05 per band | §6.15 seed-reproducibility band convention |
| divergence rate, pooled | < 0.1% | §6.15 |
| depth saturation rate, pooled | < 10% | §6.15 |
| NotPSD rejections (D29 split design) | zero within the first 50 post-warmup draws of any chain; post-warmup rate < 0.1% of post-warmup potential evaluations (the fit_hmc_e1 fail threshold); warmup rejections reported separately and do not gate | D28/D29 policy; near-reference failures are disqualifying |

A cell passing ALL criteria yields validated replacement numbers (reported
with cross-chain SDs); its historical counterparts may then be marked
superseded (D28 terminology rule). A cell failing any criterion reports the
failure and the affected historical numbers stay WITHDRAWN/UNVALIDATED —
escalation (more chains, longer chains, or a strategy change) is a new
addendum, never an in-run extension.

## Budget (separate from the audit's 2 h)

Anchors (deliberately conservative, from the M2b microbenchmark at N=150;
every run here is the N=20 toy): 16.5556 ms per sampling leapfrog including
warmup overhead; projected 15 leapfrogs/iteration at td7, 25 at td10; 120 s
per chain for MAP, scoring, diagnostics, serialization.

- td7 chain: 3000 x 15 x 0.0165556 + 120 = 865 s = 14.4 min; 8 chains
  (V1 + V3) = 115.4 min.
- td10 chain: 3000 x 25 x 0.0165556 + 120 = 1362 s = 22.7 min; 8 chains
  (V2 + V4) = 181.6 min.
- Cross-chain diagnostics + report: 15 min.
- Projected total: 312 min = 5.2 h. CEILING: 6 h local wall,
  stop-and-report mechanics identical to the audit protocol §4 (priority
  order V1, V3, V2, V4 so the td7 cells of both pivotal configurations
  survive a truncated session). The author retained the FULL V1-V4 design
  (D29 vote); the previously offered reduced variant is withdrawn. The
  start-state selection and authority-coverage computations reuse existing
  pool artifacts and add negligible wall time.

## What this proposal does NOT cover

VI and hmc_laplace (no rerun before repair, per v1.8/v1.9); Mauna data in
any form; the gamma_relaxed and vague configurations (audit layer only —
promoting either to validation is an author option at +2 cells per config);
any G-toy golden derivation (M2c, after this layer's outcome is known).
