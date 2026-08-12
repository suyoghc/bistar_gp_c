# Case C (paper/case-c-haaf) — §4 review record

Branch tip reviewed: 87da084 (paper(case-c): Haaf nested slope constraint
under BMS* and PSIS-LOO — D63). Package: `review_package_caseC.md` (identical
for every reviewer; §0 constraints + §2 work order + driver-verified facts +
section + README + FULL results.json + full diff).

## Reviewer channels

| Reviewer | Channel used | Round-1 verdict |
|---|---|---|
| GPT 5.6 sol (xhigh) | Codex CLI fresh session, repo read access | REVISE (3 findings) |
| Opus 5 | Claude Code in-session subagent (model=opus), FRESH agent (no Case B context), repo read access | REVISE (10 findings) |
| Gemini | Direct Generative Language API `gemini-3.1-pro-preview`, Griffiths key, thinkingLevel HIGH, package-only (author-directed substitution; MCP server not connected) | APPROVE (0 findings) |
| Kimi K3 | Paste-ready package `kimi_k3_package.md` — **author-run, PENDING** | pending |

Raw outputs: `round1_codex-gpt-5.6-sol.md`, `round1_opus-5.md`,
`round1_gemini-3.1-pro-preview.md`. Verdict conflict (APPROVE vs 2× REVISE)
resolved by rule 3: fix queue non-empty, so REVISE governs.

## Collation and cross-verification

Two-reporter findings (rule 1, presumed real, no adversarial check):

| ID | Sev | Substance | Reporters |
|---|---|---|---|
| CC1/OC2 | S2 | arviz imported but declared in neither requirements.txt nor pyproject.toml; fresh clone cannot run the script (work order authorized the addition) | Codex + Opus |
| CC2/OC3 | S2/S3 | The main section's kl_forward sentence breaches W1 (appendix-only) AND misreads the appendix metric: pooled column degenerate (single differing row underflows to zero weight), expected-posterior column sign-REVERSED (restricted favored by 11.160 nats on that row), values are evaluations at pw_kl_vcal-optimal instances. Driver independently re-verified all three facts from results.json (expected-posterior τ=1 reconstructs to 13 digits from the single row) | Codex (W1 placement) + Opus (content); driver verification |
| CC3/OC7 | S3 | "use the same starts" is false: restricted fit receives free solutions as clipped extra starts; selection pools cross-seeded; asymmetry deliberate and load-bearing | Codex + Opus |

Single-reporter findings (rule 2, adversarially checked; checker prompted to
refute with default-refuted on ambiguity; never the originator):

| ID | Sev | Substance | Checker | Outcome |
|---|---|---|---|---|
| OC1 | S1 | LOO compares a model against itself (HalfNormal = truncated Normal ⇒ identical posteriors; +0.413 gap purely estimator noise; "does not reproduce a categorical LOO failure" misreads the literature) | Codex | **REFUTED as stated**: exact-identity and all-noise claims unproved (local Gaussian approximation only; ω/φ multimodality; no fold refits/MCSE). Codex AFFIRMED the narrow core: the null-difference reading — a null predictive difference is exactly the reported failure mode — and confirmed the artifact's own recorded local diagnostic (SD 0.0129506, 19.4028 SDs, tail 3.65e-84). **Disposition: OC1 as stated REJECTED (logged); NARROWED OC1′ (two-reviewer-supported intersection) enters the fix queue** |
| OC4 | S2 | Nine-decimal table vs the run's own 0.005 cross-machine tolerance; gap from ONE of 1000 draws (≈100% relative binomial SE); τ-trend read from 7th-9th digit | Gemini | CONFIRMED |
| OC5 | S3 | "Nesting check passed at 2e-7" reports an unreachable guard (cross-seeded pools ⇒ set-inclusion identity; exact-0.0 from same-vector re-evaluation) | Codex | CONFIRMED |
| OC6 | S3 | BMS* arm one-sided by construction (G_r ≥ G_e rowwise); "in this instance" frames a structural bound as data-dependent | Gemini | CONFIRMED |
| OC8 | S3 | Undisclosed deterministic MLE initialization of all NUTS chains; R̂/ESS certify within-mode mixing only (grid aliases at ω≈4.939, 6.999 computed by the checker) | Codex | CONFIRMED |
| OC9 | S4 | Paired SE ddof=1 vs az.loo's ddof=0 per-model convention (0.262534 vs 0.255887); all printed as "SE" | Codex | CONFIRMED |
| OC10 | S4 | "evaluates 60 locations" untraceable to results.json (no x_eval field) | Gemini | CONFIRMED |

Findings REFUTED: OC1 as stated (see disposition). All others confirmed.

## Fix queue (dispatched as `docs/paper-sie-jmp/prompts/case-C-fix1.txt`)

FIX-1 arviz manifests (CC1/OC2) · FIX-2 kl_forward removal from main +
degeneracy/sign-reversal documentation (CC2/OC3) · FIX-3 asymmetric-starts
description (CC3/OC7) · FIX-4 NARROWED LOO interpretation rewrite (OC1′) ·
FIX-5 table precision to declared tolerance (OC4) · FIX-6 nesting check as
protocol identity (OC5) · FIX-7 one-sided bound stated before the table
(OC6) · FIX-8 init-strategy disclosure + within-mode framing (OC8) · FIX-9
ddof alignment (OC9) · FIX-10 x_eval traceability (OC10).

## Author-adjudication ledger (open at merge proposal)

1. OC1/OC1′ (S1, statistical): the strong claim was refuted, the narrowed
   rewrite implemented; sign off the final LOO interpretation (rule 5).
2. CC2/OC3 and OC4 (S2, statistical): sign off the kl_forward documentation
   and the precision policy.
3. FIX-1 scope note: requirements.txt/pyproject.toml edited beyond §0's
   literal commit-scope list, per the work order's explicit "add to
   requirements only if absent" authorization.
4. Kimi K3 round-1 review: run `kimi_k3_package.md`; findings enter a fresh
   cross-verification cycle.

(Continued below after the fix pass and re-review round.)

## Fix pass 1 (rule 4) — commit 0ce03ba

All ten queue fixes implemented by Codex gpt-5.6-sol xhigh
(`docs/paper-sie-jmp/prompts/case-C-fix1.txt`). One evidence-driven deviation
disclosed by the implementer and verified in re-review: the round-1 OC3
parenthetical misattributed the ~6.3e10 kl_forward value to the differing row
(row 984 actually reads 500.142 vs 488.982, preserving the verified
11.160-nat reversal; the 5.92e10 maximum belongs to equal-candidate row 733);
results.json records both rows and per-τ underflow status. Driver reran the
script clean; regenerated results.json byte-identical on a second run.

## Re-review round (changed hunks only, by the raisers)

| Reviewer | Findings re-reviewed | Outcome |
|---|---|---|
| Codex gpt-5.6-sol | CC1, CC2, CC3 | all RESOLVED; no new defects |
| Opus 5 | OC1-NARROWED, OC2-OC10 | all RESOLVED (independently re-derived every newly introduced number, incl. the local Gaussian diagnostic to float precision and all five reconstructed expected-posterior kl_forward values to 15 decimals; accepted the implementer's correction to its own OC3 parenthetical); ONE new S4 defect: `alias_period` field misnames the sampling angular frequency 2π/Δ; plus one non-blocking README phrasing residual (underflow regimes collapsed) |

Raw outputs: `rereview_codex-gpt-5.6-sol.md`, `rereview_opus-5.md`; package
`rereview_package_caseC.md`. Gemini raised no round-1 findings (APPROVE) and
so held no re-review role under rule 4.

## Post-re-review handling of the S4 naming defect + residual

Bounded Codex micro-fix (rule-4-consistent channel): `alias_period` renamed
`sampling_angular_frequency` in script and JSON (value unchanged); README
underflow note split into the two per-τ regimes exactly matching
`differing_row_weight_underflow_by_tau`. Driver verified mechanically: old
key absent from script and live artifacts (remaining mentions are historical
quotes inside review records), new key present, rerun exit 0 at 208 s,
results.json byte-identical after reverse-normalizing the renamed key.
Reviewer sign-off structurally unavailable (no third round per rule 4);
disclosed here.

## Final §4 verdict for the branch

Round-1 REVISE discharged: 13 distinct findings collated (3 two-reporter, 10
Opus singles of which 6 confirmed, OC1 REFUTED as stated with its narrowed
core implemented as FIX-4); all queue fixes RESOLVED in re-review; the one
hunk-introduced S4 naming defect fixed and driver-verified. **Protocol
outcome: REVISE resolved — branch proposed to the author for merge, subject
to the ledger:**
1. OC1/OC1′ (S1, statistical): sign off the final LOO interpretation (the
   strong claim was refuted; the implemented narrowed reading was
   re-reviewed by its originator as accurate in both directions).
2. CC2/OC3 + OC4 (S2, statistical): sign off the kl_forward degeneracy
   documentation and the precision policy (0.500 table, gap < 1e-5).
3. FIX-1 manifests: requirements.txt/pyproject.toml gained exactly
   `arviz>=0.17` under the work order's explicit authorization (beyond §0's
   literal scope list; flagged for awareness).
4. Kimi K3 round: run `kimi_k3_package.md`; findings enter a fresh
   cross-verification cycle.
Nothing merges autonomously (§4).

## Kimi K3 round (author-directed, 2026-08-12)

Channel: `moonshotai/kimi-k3` via OpenRouter (author's key), package-only, on
the ORIGINAL round-1 package (pre-fix state). **Verdict: REVISE (minor)** —
5 findings, raw output `round1_kimi-k3.md`. Collation:

- KC1 [S3] ("use the same starts" asymmetry): fourth-reporter convergence
  with CC3/OC7, already resolved in 0ce03ba (FIX-3). No action.
- KC2 [S3] (D63 attributes the one-chain allowance to the work order):
  NEW; survived driver verification at the current tip and Codex adversarial
  check (CONFIRMED: the work order fixes no chain count; the allowance came
  from the driver implementation prompt). FIXED post-round: D63 reattributed
  in place ("The work order does not fix a chain count; the driver prompt
  allowed a single chain at this scale; two seeded chains were used
  instead").
- KC3 [S4] (optimizer-objective compression): NEW; Codex CONFIRMED (the
  MLE stage minimizes variance-weighted Gaussian NLL; G enters at pool
  selection). FIXED post-round with the clarifying clause in 5.1.
- KC4 [S4] ("preregistered temperature grid" unverifiable): Codex REFUTED
  with the record — the τ grid {0.1, 0.3, 1, 3, 10} appears verbatim in
  docs/m2br-corrected-impact-protocol.md and is incorporated into
  preregistration v1.9 by hash (docs/prereg-addenda-d19.md), later
  ratified. "Preregistered" stands. REJECTED (logged).
- KC5 [S4] (arviz manifests unverifiable from package): convergence with
  CC1/OC2, already resolved in 0ce03ba (FIX-1). No action.
- Note: Kimi verified the round-1 kl_forward "0.0006" sentence against the
  round-1 package; that sentence was later removed per W1 (CC2/OC3), so no
  conflict with the current tip.

Net: two new prose fixes (KC2, KC3), one refuted with the prereg record,
two convergences with resolved findings. Independent reconfirmation of all
LOO and BMS* numbers.

## Author sign-off and Ready (2026-08-12)

The author signed off the statistical items by direct instruction: item 1
(the OC1′ narrowed LOO interpretation: directionally inconclusive, the
null-to-inconclusive difference identified as the Haaf/Klaassen/Rouder
failure mode, the local Gaussian diagnostic cited without exact-identity
claims) and item 2 (the kl_forward degeneracy documentation and the
0.500-precision policy). Item 3 (the arviz manifest scope note) is
acknowledged as work-order-authorized. The Kimi K3 round is complete (two
prose fixes landed at cd2aac3; the prereg-grid finding refuted with the
record). At the author's direction, PR #37 leaves Draft: **READY**.
