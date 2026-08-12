# Case A (paper/case-a-vanbork) — §4 review record

Branch tip reviewed: 31a9258 (paper(case-a): external validation section with
the fork placeholder — D65, plus the D60/D61 compute provenance). Package:
`review_package_caseA.md` (identical for every reviewer; §0 constraints + §2
work order + driver-verified facts + section + both READMEs + both FULL
results.json + full diff). Writing-only case; the [FORK-DECISION-PLACEHOLDER]
is required by §1 and reviewers were told not to flag it.

## Reviewer channels

| Reviewer | Channel used | Round-1 verdict |
|---|---|---|
| GPT 5.6 sol (xhigh) | Codex CLI fresh session, repo read access | REVISE (6 findings) |
| Opus 5 | Claude Code in-session subagent (model=opus), FRESH agent, repo read access | REVISE (11 findings) |
| Gemini | Direct Generative Language API `gemini-3.1-pro-preview`, Griffiths key, thinkingLevel HIGH, package-only. The gemini MCP server had reconnected this session; the API channel was retained for cross-case comparability (all four Gemini round-1 reviews identical channel/model/config) | REVISE (1 finding) |
| Kimi K3 | Paste-ready package `kimi_k3_package.md` — **author-run, PENDING** | pending |

Raw outputs: `round1_codex-gpt-5.6-sol.md`, `round1_opus-5.md`,
`round1_gemini-3.1-pro-preview.md`.

## Collation and cross-verification

Multi-reporter findings (rule 1, presumed real):

| ID | Sev | Substance | Reporters |
|---|---|---|---|
| F-A1 | S2 | The section credits the E7 artifact with a consistency check it does not contain and presents 696/1000 as artifact-backed: results.json has no hard-win field, the script computes no check (driver grep independently confirmed). Opus located the legitimate committed provenance: the D18 record "SIR hard fractions at n_pred=1000: 0.696 toy_elicited" (Notes/DECISIONS.md ~:923, on main) | Gemini (AG1) + Codex (AC5) + Opus (AO1) |
| F-A2 | S2/S4 | Shipped `normalize_per_draw=True` over-identified with Eq.-4 expected-posterior aggregation: distinct computations (per-row min shift + post-pool normalization vs per-row normalization then average) coinciding only at the τ→0 unique-winner limit; the Target A row label also implies the shipped call ran while the script reimplements the semantics inline (verified faithful) | Codex (AC2, D60 side) + Opus (AO9, section side); clustered |

Single-reporter findings (rule 2, adversarially checked; default-refuted;
never the originator):

| ID | Sev | Substance | Checker | Outcome |
|---|---|---|---|---|
| AC1 | S2 | kl_forward paragraph in the main section violates W1 | Opus | REFUTED: the paragraph carries the frozen "appendix-only stress metric" label, no headline rests on it, W1 assigns roles rather than banning mention, and removal would breach the work order that commissions the attribution. REJECTED (logged) |
| AC3 | S2 | D60 mentions Mauna; §0 forbids Mauna material | Gemini | REFUTED: D60 is a dated historical record predating the work order; its UNTESTED statement complies with the prereg-boundary intent. REJECTED (logged) |
| AC4 | S3 | D60's "differ far less" equal-weight claim contradicted by E7's kl_forward movement | Opus | REFUTED: dated, self-flagged conjecture whose mandated check (E7) is committed in the same diff; operative claim survives under the primary metric (movements 0.313 to 0.001, below Target A's 0.4 discrepancy). REJECTED (logged) |
| AC6 | S4 | D60 uses arrow glyphs | Gemini | REFUTED: the style rule governs manuscript prose; D60 is a historical log entry; rewriting it would alter the record. REJECTED (logged) |
| AO2 | S2 | Mapping row 3 omits the load-bearing qualification (their infinite-data posterior idealization vs our τ→0 Boltzmann limit; agreement because both collapse to nearest-model assignment) | Codex | CONFIRMED |
| AO3 | S3 | "Published target 0.841420" is self-computed (paper prints 7.96, 1.50, ≈0.84; printed-density quotient 0.841438; the 6.4e-7 error is against the repo-evaluated limit) | Codex | CONFIRMED (with sharpened decomposition) |
| AO4 | S3 | Laplace display omits exp{−G(θ*)/τ} | Codex | REFUTED: the display is explicitly scoped to the point-prior special case where G(ψ*)=0 and the conclusion is expressly confined to that limit. REJECTED (logged) |
| AO5 | S3 | "highest-weight under every variant and temperature" false across metrics | Codex | REFUTED: the sentence opens under an explicit primary-metric scope and the artifact confirms it within that scope. REJECTED (logged) |
| AO6 | S3 | 0.992 contradicts "between 0.93 and 0.99" | Gemini | CONFIRMED |
| AO7 | S3 | Frozen-notation deviations (θ* for the data-prior atom; Ḡ vs G'' unanchored) | Codex | CONFIRMED |
| AO8 | S4 | "induction" vs the repo term "induced-prior" | Gemini | CONFIRMED |
| AO10 | S4 | Dead `import fit_method_metric_comparison as fmc` in the e7 script | Codex | CONFIRMED (transitive dependency remains via prior_sensitivity_study; no banner violation either way) |
| AO11 | S4 | E7 movements lack an uncertainty statement | Codex | CONFIRMED as a paired-difference disclosure (checker cautioned against the unquantified "largely cancels" phrasing) |

Findings REJECTED with logged refutations: AC1, AC3, AC4, AC6, AO4, AO5.
Driver policy endorsed by the cross-checks: committed D-entries are historical
records — factual-accuracy concerns go to the author as proposed addenda,
never silent rewrites; manuscript style rules do not retroactively apply to
log entries.

## Fix queue (dispatched as `docs/paper-sie-jmp/prompts/case-A-fix1.txt`)

FIX-1 consistency-check re-attribution (F-A1, with the D18-record citation) ·
FIX-2 rowmin/Eq.-4 distinction + row relabel (F-A2 section side) · FIX-3
mapping row-3 qualification (AO2) · FIX-4 published-target relabel + D65
wording (AO3; D60 untouched) · FIX-5 0.992/0.93 band fix (AO6) · FIX-6
notation alignment ψ*/Ḡ (AO7) · FIX-7 induced-prior term (AO8) · FIX-8 dead
import removal + byte-identity rerun verification (AO10) · FIX-9
paired-difference sentence (AO11).

## Author-adjudication ledger (open at merge proposal)

1. F-A2 D60 side (S2, statistical): proposed ADDENDUM to D60 (not a rewrite)
   distinguishing shipped rowmin semantics from Eq.-4 expected-posterior at
   finite τ; the entry's Target A table is correct at the τ→0 limit it
   reports. Also covers D60's "0.841420" phrasing (AO3's D60-side instance).
2. FORK: the [FORK-DECISION-PLACEHOLDER] stands until the D60 aggregation-
   convention call; the section presents both sides and the E7 dial framing
   as a candidate only.
3. Author-record policy ratification: cross-checks endorsed treating D60/D61
   as immutable records with author-approved addenda only.
4. Kimi K3 round-1 review: run `kimi_k3_package.md`; findings enter a fresh
   cross-verification cycle.

(Continued below after the fix pass and re-review round.)

## Fix pass 1 (rule 4) — commit 7b653cf

All nine queue fixes implemented by Codex gpt-5.6-sol xhigh
(`docs/paper-sie-jmp/prompts/case-A-fix1.txt`); the six rejected findings
were NOT implemented and D60/D61 stayed byte-untouched per the endorsed
author-record policy. FIX-8's one authorized verification rerun reproduced
the committed e7 results.json byte-identically except the generated-date
field; the committed artifact was restored (SHA-256 0b3e2924…).

## Re-review round (changed hunks only, by the raisers)

| Reviewer | Findings re-reviewed | Outcome |
|---|---|---|
| Codex gpt-5.6-sol | F-A1 (AC5), F-A2 (AC2 section side) | both RESOLVED; no new defects |
| Gemini 3.1 Pro | F-A1 (AG1) | RESOLVED; no new defects |
| Opus 5 | AO1 (F-A1), AO9 (F-A2), AO2, AO3, AO6, AO7, AO8, AO10, AO11 | all RESOLVED (independent verification incl. the metric-correctness of the D18 attribution, the τ=1e-3 rowmin/per-draw divergence point, and the artifact hash); THREE new S4 cosmetics in the fix hunks: the added M subscript undercutting the model-independence step (N1), the θ*=ψ* shorthand equating a parameter with a data pattern (N2), the paired-differences sentence forward-referencing its numbers (N3) |

Raw outputs: `rereview_codex-gpt-5.6-sol.md`, `rereview_gemini-3.1-pro-preview.md`,
`rereview_opus-5.md`; package `rereview_package_caseA.md`.

## Post-re-review handling of the three S4 cosmetics

Bounded Codex micro-fix (prose-only, section file only): the cancellation
sentence now states Ḡ_x''(θ*)=Ḡ_z''(θ*) explicitly; "the candidate optimum
θ*=1/2, which coincides with the data-prior atom" replaces the θ*=ψ*
shorthand; the paired-differences sentence follows the movement numbers it
describes. Driver verified mechanically: shorthand absent, new phrasings
present at their lines, placeholder intact exactly once, both committed run
artifacts byte-unchanged, D60-D65 untouched by the micro-fix. Reviewer
sign-off structurally unavailable (no third round per rule 4); disclosed
here.

## Final §4 verdict for the branch

Round-1 REVISE discharged: 15 distinct findings collated (1 three-reporter
cluster, 1 two-reporter cluster, 13 singles of which 7 confirmed and 6
REFUTED with logged refutations); all queue fixes RESOLVED in re-review;
three hunk-introduced S4 cosmetics fixed and driver-verified. **Protocol
outcome: REVISE resolved — branch proposed to the author for merge, subject
to the ledger:**
1. THE FORK (standing): [FORK-DECISION-PLACEHOLDER] awaits the D60
   aggregation-convention call; the section presents both sides and labels
   the E7 dial framing a candidate.
2. F-A2 D60 side + AO3 D60 side (S2/S3, statistical): approve or decline
   the proposed D60 ADDENDUM (distinguishing shipped rowmin semantics from
   Eq.-4 aggregation at finite τ; noting 0.841420 as the evaluated closed
   form) — the entry body stays untouched either way.
3. Author-record policy: ratify the cross-check-endorsed policy (D-entries
   immutable; author-approved addenda only; manuscript style rules do not
   retroactively bind log entries).
4. Kimi K3 round: run `kimi_k3_package.md`; findings enter a fresh
   cross-verification cycle.
Nothing merges autonomously (§4).

## Kimi K3 round (author-directed, 2026-08-12)

Channel: `moonshotai/kimi-k3` via OpenRouter (author's key), package-only, on
the ORIGINAL round-1 package. **Verdict: APPROVE** (3 findings, all S4). Raw
output: `round1_kimi-k3.md`.

- KA1 (metric scope of the highest-weight sentence): re-raises AO5, which a
  single-reporter cross-check had REFUTED on paragraph-scope grounds. With
  two independent reviewers (Opus + Kimi) reading the same sentence as
  misparse-prone, rule 1's two-reporter presumption supersedes the
  refutation: FIXED post-round ("Under this metric, …" inline scope; commit
  on this branch). AO5's rejection entry stands as history; this supersession
  is the protocol working as designed.
- KA2 (D60 Mauna mention): converges with the REFUTED AC3 and with ledger
  item 3 — Kimi itself proposes only author confirmation, matching the
  author-record policy disposition. No action beyond the standing ledger.
- KA3 (footnote em-dash tags): the established house citation convention
  across all four case sections; reviewers in every case accepted it. No
  action.
- Every number Kimi checked reproduced exactly (its verification list
  includes a hand-recomputed KL cell and the monotone Target B rows).

## Fork resolution (author, 2026-08-12) — ledger item resolved

The author decided the D60 fork: **aggregation as an explicit evaluation
dial** alongside τ and occam (the E7 candidate stance, ratified). Canonical
reporting stays pooled (M-open magnitudes, ratified-number continuity,
shipped default unchanged); the Eq.-4 expected-posterior variant is reported
alongside where external correspondence matters; the kl_forward attribution
stays appendix-only. Implemented on this branch under author authority (rule
5): the section's [FORK-DECISION-PLACEHOLDER] replaced with the decision
paragraph, the D60 entry gains a dated Resolution addendum (body immutable),
and D61 a dated status line. Ledger items now open: the proposed D60
precision addendum (item 1 of the original ledger), author-record policy
ratification, and the per-case statistical sign-offs.
