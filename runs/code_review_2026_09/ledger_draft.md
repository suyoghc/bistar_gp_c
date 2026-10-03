# Author-adjudication ledger — DRAFT revision 3, 2026-09-06 (Fable)

Revision 3 folds in the Codex channel's independent recommendations
(`codex_recommendations.md`, gpt-6-astra at xhigh, written from an
options-only copy of revision 2). Both repo-access channels now recommend
the same option on every item. Changes from revision 2: Item 3 gains the
suspension option and adopts it; Items 1 and 2 carry the D58 record
mechanics and interval semantics; Item 5 carries an explicit tie rule and
Case C's derivable values; a verified reproducibility finding that neither
review reported is added for the collation; the dependency-lock drift and
the pull-request statuses are recorded as decisions.

Scope: the S1/S2 statistical items that survived the four-channel collation
and both adversarial cross-checks (`COLLATION.md`, `fable_review.md`,
`codex_review.md`, `fable_crosscheck.md`, `codex_crosscheck.md`). Items are
ordered by what they block: 3, 4 and 5 touch READY pull requests and the
frozen notation; 1 and 2 touch the frozen D58 poster record. Nothing here is
fixed, committed, or merged without the author.

---

## Item 3 — Case D's stored comparisons were produced by a sampler that targeted the prior

**Severity / reporters:** S1 recommended (Codex F3 at S2, escalated in the
Fable cross-check); Codex F4 (S2) is the regeneration-path corollary and is
folded in. Cross-verified against history, the D6 record, and current code.

**Established.**
- `experiments/practice_EvansEtAL/results_hmc/` was added in one commit,
  `7026ad6` (2026-02-16), never touched since; `run.py` is unchanged since
  `9015ee4` the same day and calls the package `fit_hmc` (`run.py:45`, `:413`).
- `fit_hmc` at `7026ad6` (`fit.py:149-154`) discards the return values of
  `pyro_sample_from_prior()` and scores the likelihood on the original,
  MAP-fitted modules. `Notes/DECISIONS.md` D6 (2026-07-02) records the
  consequence: "every `fit_hmc` 'posterior' draw was a prior draw", and calls
  the defect pre-existing. No other `fit_hmc` existed before 2026-06-30.
- D6's withdrawal list names `bistar_gp/cache/*.npz` and
  `runs/mauna_loa_sub150_hmc_*` only. The practice artifacts escaped it, and
  D64 (2026-08-11) imported them as "the HMC-mode practice run".
- The historical extractor applied the sampled kernel values by name, so each
  stored "GP draw" is a data-conditioned predictive under hyperparameters
  drawn from the configuration's hyperprior, not from the posterior.
- On current code the single-kernel practice model's sites
  (`covar_module.outputscale_prior`, `covar_module.base_kernel.lengthscale_prior`)
  are dropped by `select_hmc_sites` (`model.py:76-78`) and rejected by
  `apply_hp_value` (`model.py:99-104`); two draws with lengthscales 0.05/2.0
  give byte-identical predictives. The corrected sampler emits exactly those
  names, so regenerating the artifacts today would silently score
  default-kernel predictives (Codex F4).

**Reach.** Section 6 material computed from `bistar_probs` and
`bistar_G_diagnostics`: the winner-count table at τ=1.778 and the 39/49/48
agreement counts; the cohort `mean_G` table and the subject-25 example; the
`raw_draw_wins` table (39.0/39.9/41.5 versus 98.7/94.6/92.1 percent), which
is the carrier the F-D1 rewrite adopted for the asymmetry thesis; the τ-grid
medians (0.581/0.569/0.557 and 0.987); the "known-truth reference levels"
argument. D64's scope decision not to rerun the practice scripts was taken
under the HMC premise. PR #38 was marked READY on these numbers.
**Unaffected:** the BIC counts (18/32, 41 of 50), the MAP-conditional
deviation reconstruction and its early-trial localization (the stored
`gp_hyperparameters` come from `fit_map`, which worked), the affine identity
(algebraic on the stored values), and the F1/F2 geometry framing.

**Decision required.** Whether the stored-comparison material stays in Case
D, and in what form; the status of PR #38 while that is decided; and a dated
D6 addendum extending the withdrawal to `results_hmc/`.

**Options.**
- (i) *Withdraw* the stored-comparison material outright. Section 6 keeps
  the BIC counts, the reconstruction, and the geometry prose; loses the three
  tables, the example, the medians, and the reference-levels argument. No
  compute; a substantial rewrite; the asymmetry thesis has no carrier.
- (ii) *Relabel.* Keep every number, describe the draws as data-conditioned
  predictives under hyperprior-drawn hyperparameters (sampler of record D6),
  and reinterpret the tables as hyperprior-sensitivity reference material.
  Cheapest; but it changes the question the tables answer, the F-D1/F-D2
  sign-offs were given under the HMC reading, and a reinterpreted comparison
  left in the live argument can survive into submission.
- (iii) *Regenerate* on the corrected sampler. Prerequisites: fix the
  single-kernel site handling with a sensitivity test (fix pass 1); harden
  the practice producer (explicit `--demo --mode hmc --output_dir <new>`
  with a reviewed seed and settings contract, retained draws, sampler
  identity recorded, the broad exception handlers removed); split the
  reconstruction and comparison input paths in `regret_curves_mopen.py`; run
  the 50 subjects × 3 configurations on `nuts_e1` (new local compute, order
  of an hour as a planning estimate); re-derive every section-6 stored
  number; a fresh §4 review round for Case D; dated addenda to D64 (scope
  premise) and D6 (withdrawal list). Keep the comparison design and the
  legacy metric identities fixed; a new primary-metric analysis is a
  separate scope choice.
- (iv) *(ii) now, (iii) before submission.*
- (v) *Suspend now, regenerate the comparison layer as the endpoint*
  (Codex): withdraw the posterior interpretation immediately, preserve the
  BIC and MAP baselines as explicitly identified inputs, keep the old
  comparisons as historical evidence, and replace only the comparison layer
  with the regenerated results. Unlike (iv), no reinterpreted comparison
  stays in the live argument while the run is pending. A failed or
  inconclusive replacement yields a narrower section, not a rescued one.

**Recommended default:** (v), with (iii) as the endpoint (both channels).
Return PR #38 to Draft now; write the D6 addendum now regardless of the
choice; decide Item 4 before the run; check whether `results_diag/` and
`results_hierarchical/` are pre-2026-07-02 HMC products that belong on the
same withdrawal list. If the schedule cannot hold a defensible run, take
(i) rather than (ii).

---

## Item 4 — The computed table row is not the row the frozen notation defines

**Severity / reporters:** S2 (Codex F5; cross-check confirmed and quantified;
revision-1 wording corrected by Codex).

**Established.** `extract_gp_predictives` (`bms_star.py:323-337`) forms, per
hyperparameter draw η, the predictive N(m_η, S_η + σ²_η I) with the latent
function integrated out; it never draws f. `docs/paper-sie-jmp/00-notation.md`
("a sampled function f with observation variance defines ψ = N(f(x), σ²_ψ I)")
and §2.1 ("draw a function conditional on them, and combine that function
with observation variance to obtain one ψ") define a sampled-function row.
On E7's exact path (same caches, seeds, grid, candidates; implemented G
reproduced to 0.0), with the notation's construction implemented literally
as one function draw per hyperparameter draw, Linear / Sinusoidal /
Sin+Linear / Quadratic:

| Row | pooled τ=1 | pooled τ=0.1 | Eq.-4 τ=1 | hard-win | mean G |
|---|---|---|---|---|---|
| implemented (the artifacts) | 0.183 / 0.192 / **0.441** / 0.184 | 0.121 / 0.125 / **0.634** / 0.121 | 0.159 / 0.169 / 0.513 / 0.159 | 0.012 / 0.014 / 0.973 / 0.001 | 1.51 / 1.45 / 0.29 / 1.51 |
| notation row, one sampled f per draw (seed 0; 10 seeds in brackets) | 0.158 / 0.176 / **0.509** [0.501–0.509] / 0.158 | 0.249 / 0.233 / **0.272** [0.23–0.29; first in 2 of 10 seeds] / 0.246 | 0.109 / 0.128 / 0.654 / 0.109 | 0.012 / 0.018 / 0.963 / 0.007 | 3.15 / 2.87 / 0.88 / 3.15 |

Under the notation's own definition the Case A headline moves from 0.441 to
0.50–0.51; the pooled τ=0.1 preference for Sin+Linear (0.634) disappears
into a four-way near-tie whose winner depends on the function-draw seed;
the absolute G scale carrying the M-open signal roughly doubles; hard-win
fractions and Eq.-4 orderings are stable. The sampled function adds a
candidate-independent per-draw term that pooled aggregation retains and
Eq.-4 aggregation cancels, so the row choice interacts with the D60 dial at
low τ. The exp(−E_f[G]/τ) variant tabulated in revision 1 is a different
estimator from the notation's construction and is excluded from the claim.

**Reach.** Every soft-transfer number in Case A (E7) and Case C; the stored
Case D G values (same predictive rows, Item 3); Case B's Ḡ, which is the MAP
predictive row; the M2bR banner's SIR 0.441 anchor and its continuity with
D18/D60/D61; §2.2's projection paragraph, whose "one scalar noise variance
shared across locations" case is exactly the notation row and never holds
on the implemented row (posterior variance varies across locations). Not
Case E, whose latent-function decomposition estimand is defined separately.

**Decision required.** Which row definition governs the manuscript.

**Options.**
- (A) *Keep the implemented row and amend the definition.* Notation ψ row
  and §2.1 rewritten as "each hyperparameter draw defines one pattern,
  ψ(η; D) = N(m_η(D), S_η(D) + σ²_η I), the hyperparameter-conditional
  predictive with the latent function integrated out"; the prior-only
  construction described separately; §2.2's scalar-variance clause
  re-scoped as the special case. All committed numbers stand; no compute.
- (B) *Adopt the notation's sampled-function row.* Implement f-draws in the
  extractor; regenerate E7 and Case C; redesign Case B's Ḡ path; Case D
  cannot follow except through Item 3. Headline 0.441 becomes about 0.50,
  the pooled τ=0.1 row becomes a seed-dependent near-tie, absolute G
  doubles, continuity with every ratified number is lost; fresh rounds for
  A, B, C, and the synthesis; function-draw Monte Carlo noise enters every
  comparison.
- (C) *(A) plus a disclosed, reproducible sensitivity*: a committed script
  and artifact with the exact E7 inputs, hashes, and function seeds, cited
  once with the statement that the row definition is a convention whose
  low-τ pooled consequences are visible there.

**Recommended default:** (C) (both channels), under these conditions from
the Codex channel, which I adopt: give the substantive predictive-pattern
rationale before the continuity argument, so the choice does not read as
post-hoc definition selection; amend the Ḡ entry in the same change,
stating that Case B retains one MAP predictive so the additional averaging
gap is zero there; align the notation's unconditional τ-limit gloss with the
synthesis's convention-dependent, unique-winner qualification; commit a
baseline for `00-notation.md` first (it is untracked on every branch); and
budget a narrow Case A methods review in addition to the synthesis review,
not "synthesis text only".

---

## Item 5 — Section 2.4's reporting commitment is unmet by Case A's own table and artifact

**Severity / reporters:** S2 (statistical). Fable F3, promoted after Codex's
independent confirmation that §2.4 calls for tau-free draw-win fractions in
every soft-transfer table and a draw-level diagnostic beside appendix
`kl_forward` results, while E7's script and saved artifact carry neither.
Codex's T4 independently measured the same concentration.

**Established.** `run_bms_star` computes draw wins and only prints them
(`bms_star.py:545-549`); `_sir_bms` returns `hard_win_fractions` and E7
discards them; `BMSStarResult` carries no weight ESS. On E7's exact path,
the per-candidate effective number of draws behind the pooled weights (of
1000): pw_kl_vcal τ=1 669/685/978/669 (the headline is not concentrated);
τ=0.1 34/38/551/34; appendix `kl_forward` τ=1 6.1/8.4/104/6.1 and τ=0.1
1.15/2.25/2.47/1.14. Hard-win fractions under pw_kl_vcal are
0.012/0.014/0.973/0.001, with `argmin` silently awarding ties to the first
candidate.

**Reach.** Case A §3.4 (PR #39, READY): the pooled tables, and the appendix
sentence that the Sin+Linear `kl_forward` weight "collapses to approximately
0.000", which is a one-to-eight-draw statement;
`runs/e7_convention_sensitivity/results.json`. Case C's Table 5.1 (PR #37,
READY) is also a soft-transfer table and falls under the same rule; its
values are derivable from the saved counts without rerunning the LOO
sampler: attainment 1.000 / 0.999, strict unique wins 0.001 / 0, tie
fraction 0.999, equal-split credit 0.5005 / 0.4995.

**Decision required.** Whether the commitment is met by extending the E7
artifact, §3.4, and Case C's table, or stated as a limitation; and the tie
rule.

**Options.**
- (a) *Meet it.* `BMSStarResult` carries per-candidate weight ESS, tie-aware
  hard-win credit, attainment fractions, and tie frequency; E7 persists
  them (rerun seconds; every existing number bit-exact); §3.4 quotes the
  fractions and puts the ESS beside the appendix sentence; Case C gains one
  diagnostic line derived from its saved counts, with no LOO rerun.
- (b) *State a limitation* in §2.4 or §3.4 without changing the artifact.

**Tie rule (Codex, adopted):** exact ties on validated finite scores; report
equal-split credit h_j = mean_i[1(j ∈ T_i)/|T_i|] (sums to one), attainment
a_j = mean_i[1(j ∈ T_i)], and the tied-row fraction; never let candidate
order break a tie; introduce new field names rather than redefining the
archived `raw_draw_wins`. Pin with G = [[0, 0], [10, 11]]: attainment
[1, 0.5], split credit [0.75, 0.25], limiting row-min [2/3, 1/3], limiting
pooled [0.5, 0.5].

**Recommended default:** (a) with the tie rule (both channels). Label the
ESS as a concentration summary, not an MCMC ESS or an error bar.

---

## Item 1 — D58 Mauna cards draw bands that are not posterior bands (S1-a)

**Severity / reporters:** S1. All four channels (Kimi F1, GLM F1, Fable F1,
Codex F1); driver T2. Both repo channels opened the committed artifact.

**Established.** `decompose_model_hmc` discards each draw's conditional
covariance (`debias.py:206`) and reports `std` as the across-draw spread of
conditional means (`:222-225`; same in `decompose_model_mcmc`, `:131-144`).
Recomputing from the committed `samples.npz` (200 draws, training-only
loader, no new inference, 12 s) reproduces the committed `comp__*__std` and
`full_std` to 7.1e-13, and the law-of-total-variance sd is, in ppm at the
grid median: trend 9.34 against 0.650 committed (14.4×), seasonal 9.34
against 0.648 (14.4×), medium_term 0.177 against 0.036 (4.9×), full GP
0.132 against 0.014 (9.3×, the band card 6a labels "95% CI"; component bands
are labelled "±2 SE"). The cause of the large trend/seasonal within-draw
spread is structural: the period-1 periodic kernel with lengthscale ≈1.5
carries a near-constant direction that trades against the RBF trend's level,
so the split is unidentified within a draw (each ≈9.3 ppm) while the sum is
tight (0.13 ppm). Mean curves are unaffected.

**Reach.** `runs/poster_d58/fit_full461_seed0/figures/card6..card8` (render
evidence `783e434`; closeout D58 Update 4 at `71540836`); the byte-identical
pins in `poster/assets/d58/` (poster-repo branch
`handoff/d58-figures-11572645`, commit `7401281`, local-only); the older
`CogSci Poster/Fig X` images from the same routine. **Not the manuscript:**
Case E used the correct construction and the toy poster figures used
`honest_band_decomposition.py`.

**Decision required.** (1) Which of the two image sets the presented poster
carried, which fixes the dissemination correction but not the defect in
the pinned set. (2) The correction path under the D58 record process
(`docs/d58-poster-execution-protocol.md`). (3) The interval semantics of any
corrected band. (4) Whether the corrected figures disclose the level-split
non-identifiability or the modeling change to remove it.

**Options.**
- (A) *Addendum only.* D58 Update 5 records the band semantics; the pinned
  figures stay. No compute; the record's only render stays wrong.
- (B) *Corrected pinned set plus addendum, as a separately authorized
  correction act.* Recompute from the committed `samples.npz`, the hashed
  training arrays, grid, and normalization metadata with per-draw
  conditional moments retained; a new correction driver, since the old
  renderer only rebuilds the incomplete saved arrays and writes into the
  original `figures/`; a new output namespace outside the original fit
  directory, whose closed-world census permits only the existing `figures/`;
  input hashes, code head, moment schema, tolerances, and new figure hashes
  recorded; originals byte-pinned. Interval semantics: pointwise central 95
  percent posterior credible intervals of the retained draw mixture for the
  latent process, conditional on the recorded fit (the Case E CDF-bisection
  construction), which makes the "95%" label true; if only total variance is
  implemented, the truthful label is "±2 posterior SD" without "95%" or
  "SE". The trend and seasonal panels will show bands of roughly ±19 ppm
  around a cycle of a few ppm; that is what the posterior says under this
  kernel and must not be suppressed by centering or refitting.
- (C) *(B) plus a modeling change* (a seasonal component with a fixed level)
  to make the split identifiable. Requires a new Mauna fit under its own
  preregistration; companion-line work, not D58.
- Interim option (Codex): a means-only replacement that omits uncertainty
  explicitly, if a faithful correction cannot be produced under an
  authorized act in time.

**Recommended default:** (B) with the mixture-quantile construction and the
level-split disclosure in Update 5 (both channels); (C) noted as
companion-line work; D58's spent PREP/POST rounds do not authorize this act,
so commission a new bounded correction, evidence commit, and poster hand-off
on a new branch in that repository; identify the presented poster's actual
assets before specifying the public-facing correction, without letting that
question block the corrected evidence.

---

## Item 2 — Grouped "truth"/"bias" bands assume independent components (S1-b)

**Severity / reporters:** S1. Codex F2; the grouping half of Fable F1; Kimi
and GLM supplied the contrast with the MAP variant that retains
cross-covariance.

**Established.** `compute_debiased` (`bistar_debias_mauna_loa.py:97`, `:106`)
forms grouped uncertainty as `sqrt(Σ comp.std²)` under an "independent
components" comment. Assigning every component to truth (the Believer
interpretation) must reproduce the full posterior band. Two magnitudes,
both in ppm at the grid median:
- *The pinned cards as rendered* (committed mean-spread marginals, summed
  independently) against the corrected joint SD: Believer 0.919 against
  0.132 (7× too wide); Moderate 0.918 against 0.132 (7× too wide); Skeptic
  0.648 against 9.34 (14× too narrow; a single component, so Item 1 alone).
  Codex's 2294× is the same comparison in variance units on the committed
  rows.
- *The grouping defect in isolation* (independence sum on the corrected
  marginals 9.34/9.34/0.18): Believer and Moderate both 13.2 against a joint
  0.132, 100× too wide in SD.
Repairing Item 1's marginals alone therefore makes the grouped bands worse,
not better; the grouped band needs the joint posterior of the summed group
blocks per draw, which `decomposition.npz` does not retain and `samples.npz`
allows.

**Reach.** Cards 7 and 8 (row 0 of card 7, both card-8 strips) and the
older `bistar_three_interpretations_hmc.png` / `bistar_debiased_ppm_hmc.png`.
Not the manuscript.

**Decision required.** Whether the grouped bands are corrected in the same
act as Item 1 or only disclosed.

**Options.** Fold into Item 1 (B), or into (A) with grouped uncertainty
omitted until joint moments exist (Codex's interim).

**Recommended default:** fold into Item 1 (B) (both channels), with the
group conditioning done per draw on the summed group blocks using the
Cholesky factor of the entire fitted training covariance plus noise (never a
group-only factorization), symmetric for truth and removed-bias groups, and
the all-components-truth identity holding for means, total variance, and
mixture quantiles as the acceptance condition before any grouped card is
published. Add that identity, the singleton and empty-group identities, and
an anticorrelated two-component fixture to the test suite.

---

## New finding for the collation (reproducibility, S3; not an adjudication item)

`paper/case-c-haaf:experiments/haaf_nested_constraint.py:46` imports
`e7_convention_sensitivity`, which exists only on `paper/case-a-vanbork`
(absent from `main`, `paper/case-b-occam-dial`, and Case C's own branch;
verified with `git ls-tree`). Case C's committed artifact therefore does
not regenerate from its own branch; the Fable rerun succeeded only because
both scripts were copied into one scratch directory. Found by the Codex
recommendations pass, verified by Fable. Fix: move the aggregation
conventions into the package (fix pass 1, FIX-9) and have both scripts
import them; merge order A before C.

## Other decisions recorded

- **Dependency-lock drift.** Remove `pypdf` from the designated interpreter
  (`/opt/homebrew/Caskroom/miniconda/base/bin/python3.13`, which the freeze
  test targets) and keep PDF tooling elsewhere; do not refresh the lock or
  weaken the test (both channels).
- **Pull-request statuses.** #38 to Draft now; #39 and #37 reopen for the
  bounded reporting amendments of Item 5 and the Item 4 sensitivity; #36
  needs a refreshed dependency and wording verification after the package
  fixes merge, without treating its numbers as withdrawn; #40 and #41 stay
  Draft until their own ledger items close.

## Items considered and deliberately not placed on this ledger

- **Codex F6 / Fable F4 (Ḡ surrogate and notation).** Folded into Item 4's
  notation change.
- **Codex F7 (Hellinger variants, S2).** Fix pass 1; no adjudication.
- **Codex F4.** Folded into Item 3 as the regeneration prerequisite.
- **Fable F8 (metric defaults, S4).** Fix pass 1. The two channels differ
  only on scope: Codex enforces roles at manuscript-facing entry points and
  leaves generic defaults; Fable additionally adds the primary metric to
  `ExperimentConfig.metrics`. Both go to the fix pass; no author decision.

## Suggested record actions once the items are decided

D6 addendum (withdrawal list), D64 addendum (scope premise and chosen
option), D58 Update 5 (both defects, the interval construction, original and
corrected hashes, presented-poster provenance, each act in the past tense
after it happens), the notation baseline commit followed by the ψ, Ḡ, and
τ-limit amendments, the PR status changes above, and the fix-pass lineage:
fix pass 1 (package, decision-independent; dispatch
`docs/paper-sie-jmp/prompts/code-review-fix1.txt`) before any regeneration,
then fix pass 2 (decision-gated script and artifact work: E7 extension and
Case C diagnostic line, the Item 4 sensitivity artifact, the practice
producer and Case D regeneration, the D58 correction act).
