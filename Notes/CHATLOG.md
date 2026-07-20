# Chat Log

Session summaries: date, what was done, what was committed, key discussion points.

## 2026-07-01

**Done:**
- Evaluated the codebase — first a single-pass review, then an exhaustive multi-agent workflow
  (172 agents across map / review / verify / completeness / synthesize). The verify phase was hit
  by transient rate-limiting, so critical findings were re-verified by hand against source.
- Landed repo hygiene + the first test suite (DECISIONS D1) and five BMS*/BI* correctness fixes with
  regression tests (D2); 33 tests pass. Opened PR #1.
- Deep-dived the Laplace model-prior definition: established that `laplace_evidence.py` computes a
  mislabeled likelihood-weighted joint, not the data-free `Z_Mx` the paper defines. Wrote
  `docs/plan-zmx-laplace.md` and logged D3.
- Adopted the `antagonistic_collab` `Notes/` decision-log workflow (this file, `DECISIONS.md`,
  `SCRATCHPAD.md`) and documented the convention in `CLAUDE.md`.

**Committed:** 5d15853 (hygiene + tests), 569ee39 / f218dea / 84568fc (correctness fixes),
c5562a3 (Z_Mx plan). PR #1: https://github.com/suyoghc/bistar_gp_c/pull/1

**Key discussion — Construction I vs II for the GP-informed model posterior:**
Starting from a single GP-induced joint prior over (M, φ) shows the model-prior integral `Z_M` and
the parameter-prior normalizer `Z_prior` are the same integral, so they cancel and the consistent
posterior is `∝ N(M)` (Construction II). This corrected an earlier off-hand framing of II as
"double counting" — it is not. Recommended II as canonical, with a no-GP baseline and Construction I
(GP as a separate model-prior factor) as an ablation ladder.

**Open:** confirm Construction II canonical + Occam default; implement the plan on `fix/laplace-zmx`
after PR #1 merges. See `Notes/SCRATCHPAD.md`.

---

## 2026-07-01 → 2026-07-04 — Review campaign D4–D8, real-data impact, thesis-anchored options D9/D10

**Done (all on `fix/laplace-zmx`, PR #2; 8f09af9 → f4a4d1f; 42 → 88 tests):**
- 8-angle code review → D4 (sample-site rename fallout: kernel draws silently dropped in three
  consumers; double noise latent; eval-mode MH target) and D5 (V_ref consistency across
  constructions; τ-invariant Z_Mx clipping with n_clipped surfaced; soft_transfer_weighted global
  shift). Two severity-3 leftovers fixed (compare() key-union; sweep-script sys.path).
- Multi-model panel (Gemini 3.1 Pro / Kimi K2-thinking / GLM-5.2 via OpenRouter / codex gpt-5.5 /
  Fable adjudicating): codex alone caught that fit_hmc sampled the PRIOR (discarded
  pyro_sample_from_prior return) → D6 fix + connection regression test. Kimi's ×n CRITICAL refuted
  empirically (gpytorch MLL is per-datum).
- D7 prior/posterior predictive sampling (sample_prior + condition_on_data flag).
- D8 Mauna NUTS taming (init_to_map + max_tree_depth; tree cap is the operative fix); mixing
  qualifier added separately (capped chain fast but NOT converged: ESS≈1, Rhat 4–81).
- Impact assessment old(9016a55)-vs-new: toy sections on Della (job 10608943); --mauna section run
  LOCALLY after two Della timeouts (della-h16 slow per-op + thread thrash). HEADLINE: BMS* model
  selection on Mauna Loa REVERSES — old picks Linear 0.99, new picks Quad+2Harm 0.42 (direction
  robust, exact numbers carry the non-convergence caveat). docs/impact-assessment-results.md.
- Thesis chapter read end-to-end → D9 fit_gp(method=hmc|vi|map|hmc_laplace), one shared samples
  schema, defaults thesis-anchored (full-Bayes sampling; VI was the thesis PRIMARY, HMC cross-check,
  MAP the contrast); D10 the "single-G decision" DISSOLVED (viz variance-weighted MSE ≡ pw_kl_vcal,
  verified 1e-12; identity scoped to var ≥ 1e-6 — floors differ below). Writeup-ready doc:
  docs/inference-and-metric-options.md. codex review of D9/D10 → 4 CONFIRMED findings fixed
  (shared init guard, (n,) schema at n=1, floor-scoped identity, VI learn-vs-init test).

**Key discussion:** thesis anchors extracted with page numbers (App. II p. 221: VI primary /
10k+1k; pp. 174–5: KL-variant metric, investigator's choice; hard best-match aggregation, soft-τ is
the relaxation). Della abandoned for small sequential NUTS (Mac ~faster per-op). API keys sit in
plaintext ~/.zshrc — consider rotating/moving.

**Next session:** (1) comparative results run — fit_gp methods × metric family on the thesis toy
(+ optionally Mauna) so the user can "choose based on results"; (2) severity-2 cleanups (fold into
viz unification); (3) viz unification (UNBLOCKED by D10); (4) figure regeneration; (5) open forks:
converged Mauna full-Bayes (nonlinear reparam), Occam default, kb/Wiki update.

## 2026-07-04 → 2026-07-07 — Task 1 (method × metric comparison) + Task 2 (cleanup backlog + viz unification)

**Task 1 (D11–D13):** fit_gp methods × 5 metrics on the thesis toy. Found + fixed the
candidates.py restart-selection no-op (D11: criterion constant n/2 at any MLE; Sin+Linear
had collapsed to a fake near-linear sinusoid — invalidated the first 12 h run; raw draws
now cached so sampler hours are never re-paid). Corrected results (D12): toy posterior
BIMODAL under `informative` priors; hmc/map/hmc_laplace select Sin+Linear under every
metric, VI migrates to the dominant-mass basin and selects Sinusoidal — thesis App. II
"VI ≈ HMC" does not replicate; reads as prior misspecification. Post-commit codex
verification refuted the initial mass story — root cause fit_mcmc_simple's missing
raw-space Jacobian (D13, fixed); D12 corrected in place. Capped-NUTS appendix
(docs/appendix-tree-depth-cap.md): depth-7 ≈9× cheaper, posteriors shift ≤0.011.

**Task 2 (D14–D17):** backlog recovered via the user's second session (20bd7c8). D14
hygiene (S1s, prose, .pyc, conftest retired for pip install -e). D15 laplace_evidence
refactor (bit-identical golden; ladder/τ-sweep helpers; bounds-aware Hessian). D16 Z_Mx
sampling estimators (mc + ordinary defensive-mixture IS as reference; starts=, weights=,
rng=). D17 viz unification: both scripts ported (legacy pinned a87356a), shared
_viz_spaces, rerunnable attribution harness. KEY FINDING: the two legacy reference
scripts CONTRADICTED each other at n=50 (Linear 0.693 vs Sin+Linear 0.934) — attributed
dominantly to the priors script's hard-wired occam-ON convention; canonical figures
select the true model 0.93–0.99. Post-run codex review → proposal-coverage hardening
(--n-perturb 5 default, ess_by_stage.md diagnostic) + pristine single-run artifact
directory (zero ESS warnings, worst per-stage ESS 166).

**Committed:** 0d49a1e, 6573ff0 (Task 1); 980d253, 641444a, plan R0–R2 docs, a87356a,
7be2f40, 5b4c889, 5b7210f (Task 2). 111 tests pass. Five codex review rounds, all
findings verified empirically; two of my own claims corrected by review (D12 mass story,
SCRATCHPAD ESS claim) — logged as corrections, not rewrites.

**Open for the user:** push + flip PR #2 to Ready; ratify pw_kl_vcal / method-default /
VI-framing (D12/D13 questions in SCRATCHPAD); Mauna candidate recheck post-D11 before
paper numbers; non-viz figure sets; kb/Wiki update. Tooling lesson recorded: backgrounded
`codex exec` needs stdin from /dev/null.

## 2026-07-07/08 — Work-queue session: recheck, gates, PR flip, figure regeneration

**Orientation:** verified d9efaaa + 111 tests before touching anything, per the handoff
prompt.

**Mauna candidate recheck post-D11 (523825c):** the reversal headline SURVIVES. Re-ran
`impact_assessment --mauna` at the 2026-07-04 settings on the current tree: HMC side
bit-identical (clean isolation), every BMS* posterior entry within 0.00002 (Quad+2Harm
stays 0.42218 vs Linear 0.11368 at pw_kl_forward@tau1). Mechanism diagnostic: all 12
restarts of each Mauna candidate converge to one basin (frequencies fixed a priori), so
the pre-D11 first-restart pick was already optimal — the toy's multi-basin omega
pathology does not transfer. Recheck subsection added to the impact doc.

**D12/D13 gates resolved (user; f6db15d):** new local-only paper log
Notes/WRITEUP_DECISIONS.md (gitignored via 0280b77). W1: pw_kl_vcal ratified as main
metric, kl_forward demoted to appendix stress-test. W2: method default stays hmc for the
draft with the mass split disclosed and basin-occupancy required; prior-sensitivity study
QUEUED before final paper numbers (the one remaining open fork). W3: VI framed as the
bimodality/prior-sensitivity story, paper phrasing recorded verbatim. D12 got a Ratified
block.

**PR #2 flipped to Ready** (user-authorized): 16 commits pushed, draft flag cleared.

**Figure regeneration (D3 item 2) DONE — D3 fully CLOSED:** detached two-wave
orchestrator runs/figures_regen/regen.sh (survived one Claude session restart that had
killed the first attempt). Five bistar_gp/cache HMC caches rebuilt fresh on fixed code
(pre-D2 originals quarantined in cache/stale_preD2_20260214/); toy_example x2, mauna_loa,
bms_star_mauna_loa + debias (fed the sampled cache via --use-cache — the debias script's
own HMC block still has the pre-D8 init/cap bug, flagged as a spawn-task), then the five
cache-dependent scripts. 151 figures, zero errors in 11 logs. Full-data Mauna BMS* chain
is slow even at depth 7 (~8 min/step, 28 h) and carries the D8 convergence caveat.
Sandbox-era viz scripts import nothing from bistar_gp — unaffected, not regenerated.
kb/Wiki/GP-Induced Model Priors.md rewritten to Construction II canonical (D3 item 3).

**Committed:** 523825c, 0280b77, f6db15d, plus this close-out docs commit. Stale module
docstring noted (laplace_evidence.py header still says IS "fails in >3D" — pre-D16
wording), left for the next code-touching pass.

**Open for the user:** prior-sensitivity / re-elicitation study on the informative config
before final paper numbers (W2); debias-script HMC fix chip; PR #2 review itself.

## 2026-07-08 — debias-script HMC fix chip (CLOSED)

Scope-limited cleanup chip after PR #2 / D3 closure; the prior-sensitivity /
re-elicitation study was explicitly NOT started and remains open.

- `experiments/bistar_debias_mauna_loa.py` fresh-HMC branch brought onto the D8
  pattern: MAP-fit the model actually passed to `fit_hmc` (n_iter=300), then
  `fit_hmc(..., max_tree_depth=7)`; the throwaway `model_map` fit removed.
  `--use-cache` untouched (the regenerated figures had used cached draws and
  were never affected).
- `bistar_gp/laplace_evidence.py` header reworded post-D16: IS no longer
  described as failing >3D; `is_log_Z_Mx` documented as the figure scripts'
  validated reference, heavier and ESS-checked.
- New `tests/test_experiment_hmc_pattern.py`: source-level (AST) guard that all
  three Mauna scripts cap tree depth at 7 and MAP-fit the exact model/data
  passed to `fit_hmc`; verified to fail on the pre-fix source.
- D8 and D16 got status addenda. Full suite: 114 passed.

## 2026-07-08 — prior-sensitivity / re-elicitation study (W2 gate, D18)

The remaining paper-facing research task from W2, run end to end in one session.

- **New:** `experiments/prior_sensitivity_study.py` (staged pipeline: prior scorecard,
  27-start mode hunt with valley checks, 3-seed prior-IS with SEs/per-basin ESS, capped
  NUTS + VI + MAP via the D12 machinery with cache-fingerprint sidecars, mass-faithful
  SIR arm, generated report). Tables: `docs/prior-sensitivity-study.md`; raw artifacts
  `runs/prior_sensitivity/` (local). Decision rules pre-registered before stage-B reads.
- **Preflight multi-agent review** (5 reviewers + adversarial verification) before the
  expensive stage caught 4 substantive design/method flaws, including a truth-peeking
  lengthscale prior in the re-elicited config (fixed, HMC arm rerun) and a false
  unimodal verdict for `vague` from the original 4-start hunt.
- **Headline (D18):** the D12 bimodality is PRIOR-INDUCED (kernel Gamma(6,0.85) priors;
  noise prior innocent per the attribution arm). All re-elicited configs are unimodal /
  coherent and select Sin+Linear under HMC, MAP, AND the mass-faithful SIR measure; even
  informative's mass-faithful number selects Sin+Linear at tau>=1 (near-flat,
  tau-fragile) — D12's "mass-faithful would lean wrong" speculation refuted. VI lands in
  the wide high-noise region under every config regardless of mass (revises W3's
  framing); kl_forward flips under any heterogeneous mixture (sharpens W1).
- **Recommendation (user to ratify):** final toy numbers under `toy_elicited`;
  informative becomes the prior-misspecification case study; vague the robustness
  appendix. D12/D13 history preserved; D12 got a status addendum pointing to D18.
- 114 tests pass; no package code touched (alternate configs defined in-script only).

## 2026-07-09 — prior study review response: spot-check resolved, SIR hardened (D18 final)

User review of the D18 study surfaced four issues; all addressed.

- **"Pattern A" mislabel fixed:** the pre-registered VI/HMC-agreement leg failed for
  every config including the baseline, so D18's Decision is rewritten as a DISCLOSED
  DEVIATION (coherence = geometry + basin-agreement criteria, mass-faithful SIR row as
  the VI-independent arbiter); W2's status note matches.
- **Pre-registered spot-check ran and mattered:** toy_elicited HMC occupancy (1.000
  low-band) contradicts prior-IS mass (0.763±0.004) by far over 2 SE. Three-way
  arbitration (new stage `noise-marginal`: prior-IS per-band ESS, Jacobian-corrected
  RW-MH referee with ~40 lo/hi crossings per chain, profile-Laplace quadrature) is
  UNANIMOUS against the chain, and the uncapped td10 arm (5.7 h) is EQUALLY confined
  (1.000/0.000/0.000, tau=1 0.683 vs capped 0.696). Conclusion: MAP-init NUTS
  under-explores the noise ridge at any tree depth even in this unimodal geometry (the
  D8 disease on a well-behaved posterior). Paper consequence: the full-Bayes headline
  under toy_elicited is the mass-faithful SIR number 0.441±0.005; the HMC 0.696 is the
  density-mode-region answer, disclosed.
- **kl_forward claim made precise:** the tau=1 collapse (Sin+Linear 0.000) is the SOFT
  aggregation only; hard best-match on the same mixtures stays 0.696/0.707/0.520
  (alternates) and 0.241 (informative).
- **SIR hardened to paper-grade:** n_pred=1000 with bootstrap SEs (<=0.007) and
  per-IS-seed replicates (scatter <=0.03); all stale n=200 numbers reconciled across
  D18/W2/SCRATCHPAD.
- Committed on `study/prior-sensitivity` (stacked on fix/laplace-zmx); PR #2 untouched.

## 2026-07-10 — PR #4: toy_elicited_n20 graduation + D18 figures stage (Fable session)

Implementation branch for the D18 ratification, built off main after the PR #2/#3
merges (a9253fb, 7069ea6).

- **Code:** `PRIOR_CONFIGS["toy_elicited_n20"]` (registry-only; params byte-identical
  to the study config, N=20 provenance in the description); STUDY_CONFIGS swap with
  the cache fingerprint verified unchanged against all four on-disk sidecars;
  `--stage figures` building Figure A (toy_model_posterior_elicited) and Figure B
  (prior_misspec_geometry) from existing artifacts only, with 34 pinned headline
  values asserted equal at rtol=0/atol=1e-12 before plotting.
- **Docs:** D18 Status forks a/b/c closed; viz gate recorded "passed but not
  exercised" with the recheck table and the threshold-provenance caveat;
  fit-method doc retitled via its generator; prior-sensitivity report regenerated
  (description bullet now matches the registry entry); SCRATCHPAD cleaned. Local:
  W4 gate paragraph updated; kb/Wiki touch-ups (Paper Writing Guide 7.2 data-priors
  anchor, HMC vs MAP mode-confinement caveat, Metric Choice Justification kl_forward
  paragraph).
- **Review round (milestone):** codex GPT 5.6 sol (xhigh, read-only; verified 70
  pinned scalars independently) + 21-agent Fable workflow (5 dimensions, adversarial
  verification; 16 raw findings, 12 confirmed). All 15 confirmed findings fixed
  before push: stale generated study doc, caption counts now loaded from validated
  artifact fields (SIR hard-fraction denominators prove all 1000 predictives
  contributed), histogram density normalized against all draws with the display clip
  disclosed, rank-stability validated against full posterior vectors, test suite
  hardened to 7 tests (negative gates + hermetic synthetic-artifact coverage).
- **Shipped:** 121 tests pass; commit 8141703 pushed; PR #4 opened against main
  (https://github.com/suyoghc/bistar_gp_c/pull/4).
- **W5 follow-up (same day, codex review of the framing):** the earlier "full-Bayes
  headline" wording is superseded by "posterior-mass-faithful under the fixed
  data-elicited prior" (W5 in the local writeup log; committed correction in D18
  Status). The prior medians use realized data summaries, continuous with thesis
  Ch. 5 pp. 184-186 (which permits data-informed prior choice and cites empirical
  Bayes) though the thesis does not document this exact var(y)-based rule.
  Figure A now states the two-layer uncertainty explicitly: ±0.005 = conditional SIR
  bootstrap SE given the realized pooled IS draws and weights; open points
  0.419/0.438/0.431 = independent importance-pool variability; never combined.
  Registry description gains the data-elicited disclosure; Figure B mode-label
  crowding fixed. Terminology and disclosure only; no prior, scope, number, or
  ranking change.
- **MERGED:** PR #4 merged to main 2026-07-10 as fcd70e2 (after the W5
  terminology commit 5b77619 and the Figure A caption-layout commit 7dcb9cb);
  121 tests pass on merged main.

## 2026-07-10 — D19 M1 freeze commit: plan + pre-registration v1.0 (planning artifacts only)

Session scope held exactly to the handoff: one reviewed commit on
`docs/d19-mauna-freeze` containing planning artifacts only (documentation, Notes,
reproduction/benchmark scripts, frozen planning JSONs) — no package code, no
pilots, no expensive runs, no scientific result read before the commit.

- **Recovered** the planning-session artifacts intact from the prior session's
  scratchpad (d19_plan.md, bench_sub/full.json, d19_scorecard_v2.py,
  scorecard_v2.json, the codex round-1 review) and backed them up into this
  session's scratchpad.
- **Synthesized** `docs/plan-d19-mauna.md`: the post-round-4 plan (all four codex
  gpt-5.6-sol rounds folded in) — staged design with gates, measured cost table
  (E1 rows labeled kernel-cost proxies pending the M2b NUTS microbenchmark),
  candidate-set matrix with the harmonization rule, risk register (+R13 era
  amendment), milestone map M2a-M2d/M3/M4/M5, pre-registration v1.0 (frozen arm
  order, dossier-hash blinding, selection firewall, O1-O5, geometry/adequacy/
  budget-only stop rules, SEALED 60-month holdout, estimator-specific toy goldens,
  two-reference coverage arbitration, per-band IS ESS + independent pools +
  functional MCSE floors, 10 standing disclosures, threshold inventory §6.15,
  amendment protocol §6.16), decision record A1-A11, source status + era
  amendment rule, scorecard v2 frozen record, benchmark artifacts, scalability
  template.
- **Ported + verified**: `experiments/d19_prior_scorecard.py` (seeds unchanged)
  regenerates `runs/d19_planning/scorecard_v2.json` byte-identically — the only
  computation this session (reproduction of the already-ratified Stage-0
  scorecard). `experiments/d19_bench.py` committed as the A7 Della re-benchmark
  vehicle; the three planning JSONs deliberately tracked under
  `runs/d19_planning/`.
- **Notes**: DECISIONS.md D19 entry (the commit-message source); SCRATCHPAD
  D19-state section; `.gitignore` gains `Notes/WRITEUP_DRAFT.md` (the pending
  entry from the PR #4 session).
- **Review**: codex gpt-5.6-sol (xhigh) reviewed the freeze-commit diff:
  FIX-FIRST, 10 findings (6 HIGH, 2 MEDIUM, 2 LOW), all resolved at
  documentation level by amend BEFORE the freeze finalized ("round 5" markers in
  the doc). Highest-value catches: the G-B seed-reproducibility leg was still
  keyed on BMS* outputs (re-keyed to target-level agreement; BMS* seed-stability
  demoted to Stage-C reporting-only); the D18 profile-quadrature band triplet
  0.763/0.138/0.023 sums to 0.924 (non-normalized grid integrals — demoted to
  historical, corrected recompute queued at M2c); coverage arbitration lacked an
  authority-precedence and SE definition (frozen); budget truncation could
  strand an adoption candidate (reservation rule added); "holdout never loaded"
  was literally false (seal semantics restated; training-only loader queued at
  M2a); the A5 fallback design freeze pinned to M2b. The reviewer independently
  verified all committed numbers, seeds, and repo ground-truth claims. In the
  same amend, 13 §9.4 table cells were aligned to the script's own %.3f
  rendering (x.xxx5 boundary values; the pinned 0.938 [0.927, 0.949] headline
  cell unaffected).
- **Next**: M2a infrastructure PR (provenance/loader/A10 period freeze/candidate
  registry/pw_kl_vcal/diagnostic schema/slurm refresh). The holdout stays sealed;
  the ordering/blinding rule governs all subsequent compute.

## 2026-07-11 — PR #5 merge bookkeeping (ride-along from the freeze session)

- **PR #5 opened** (2026-07-10, after author acceptance in chat): branch
  `docs/d19-mauna-freeze` at a077c6e, base main, Ready, planning/documentation-only
  pre-registration PR. Body: no implementation or pilot results; a077c6e = the
  frozen-before-results baseline; tracked planning JSONs = deliberate evidentiary
  artifacts; A6 + §6.15 implementation-coupled thresholds explicitly deferred; M2a
  must not begin until the merge. Standing author rule: a077c6e is immutable —
  corrections are follow-up commits or append-only prereg amendments (§6.16).
- **PR #5 MERGED** 2026-07-11 (~00:37 EDT) as normal merge commit e86e90a (parents
  ec290a8 + a077c6e); a077c6e verified an intact ancestor of main. No CI checks on
  the repo. These lines ride with the M2a Notes commit per the PR #4 pattern
  (author said stop after opening; no bookkeeping-only commit was made then).

## 2026-07-11 — D19 M2a infrastructure PR (D20; branch feat/d19-m2a-infra)

- **Scope discipline held**: infrastructure only — no pilots, no Stage-A/B runs, no
  Mauna BMS* probability computed anywhere, no candidate fit to real Mauna data
  (registry/harmonization tests are synthetic-fixture-only), no arm configs, no era
  transcription. The one Mauna computation was the ALLOWED reproduction check:
  experiments/d19_prior_scorecard.py regenerated runs/d19_planning/scorecard_v2.json
  byte-identically (sha256 52b2d49d...6881) after the loader rewrite.
- **Item summary (full record in DECISIONS.md D20)**: A9 vendored CC0 dataset +
  canonical year/month/co2 sha256 5bcdc813...0910 (prereg addendum v1.1 in the new
  docs/prereg-addenda-d19.md) + hard runtime verification + loader-defect fixes
  (unbound-x_all fallback, unreachable except, no-op filter documented+asserted);
  training-only loader (load_mauna_loa_training) making the §6.6 seal mechanical;
  A10 period frozen at exactly 1.0 with requires_grad off + fit_map frozen-param
  guard + 7-site inventory tests; A4 registry with both universes, the shared
  Quad+2Harm aliased by construction, harmonized 3-set (period 1.0, sine
  convention, D11 multi-start full-NLL, differential_evolution removed), loud
  merge guard; pw_kl_vcal + tau grid 0.1/0.3/1/3/10 wired (kl_forward stays
  appendix); SamplerDiagnostics schema (divergences/acceptance/leapfrog counts,
  JSON round-trip, None-iff-unavailable honesty contract) behind
  fit_hmc(return_diagnostics=True) with the D9 default return unchanged; slurm
  refresh + AST argparse guard over all four .slurm files.
- **Implementation route**: two codex gpt-5.6-sol (xhigh) subagents implemented the
  registry/metric wiring and the slurm/guard items in a workspace-write sandbox;
  Fable implemented loader/seal/period/diagnostics and integrated.
- **Tests**: 175 passed after three review rounds (121 baseline + 54 new). Scorecard
  byte-identity gate passed on every round; vendored-CSV vs live-fetch monthly
  aggregation verified byte-identical.
- **Review**: codex gpt-5.6-sol (xhigh, read-only) on the PR diff: FIX-FIRST, 8
  findings (1 HIGH, 5 MEDIUM, 2 LOW), all fixed in the same PR before Ready —
  highest-value catch: the rewritten study script still called the full loader and
  plotted the sealed holdout (now on load_mauna_loa_training with a source-level
  seal-guard test). Full list + fixes in DECISIONS.md D20 ("M2a PR-review round").
  A parallel three-lens verification workflow (21 read-only agents; prereg-compliance /
  correctness / test-adequacy with per-finding adversarial refutation) ran as an
  independent second check: 18 raw findings, 13 confirmed (5 overlapping codex), all
  net-new ones fixed in the same PR — notably the DISTRIBUTION-LEVEL kl_forward missing
  from MAUNA_METRICS, five test-adequacy gaps, and the vendored CSV missing from wheel
  package-data. Refutations recorded in the workflow transcript.
- **Third round** (codex re-run, 170 confirmed): two follow-up findings, both
  verified before acting. S2 (real) — the A4 universe firewall was caller-dependent;
  run_bms_star now rejects mixed/partially-tagged universes at the shared boundary
  (all-untagged legacy/toy still allowed), with direct regression tests. S3 (property
  held) — proved fit_hmc(return_diagnostics=True) leaves the trajectory bit-identical
  to the default path (two toy runs, same seed/MAP), locked in as a non-perturbation
  test; no code change needed. Follow-up commit; suite 175.
- **Next**: M2b (E1 direct potential + frozen equivalence battery + real E1 NUTS
  microbenchmark + Della re-benchmark (A7) + A6 budgets + A5 fallback addendum).
  Holdout stays sealed; §6.5 ordering/blinding governs.

## 2026-07-11 — D19 M2b: E1 coordinate convention, two S1 correctness findings, battery, microbenchmark (branch feat/d19-m2b-e1)

- **Session opened with the author's 7-point revision** of the E1 coordinate
  convention (recorded verbatim in prereg addendum v1.2 + D21, committed BEFORE
  any E1 code per §6.16): E1's public NUTS coordinates are the exact pyro
  initialize_model sample-site coordinates (S1's sites/order/transforms);
  gpytorch raw parameters demoted to an internal evaluation representation;
  single-count composition rule; frozen-period exclusion; paired-state
  posterior-predictive gate; microbenchmark persistence firewall; S3/S4 numbers
  frozen as ceilings until M2c.
- **D22 (found by the first E1 equivalence probe)**: the obs plate in
  _hmc_pyro_model multiplied the marginal likelihood by N — fit_hmc, fit_vi,
  fit_hmc_laplace all targeted p(theta)L(theta)^N. One-line fix, paired-state
  regression tests, prereg v1.3, standing caveat on every pre-fix HMC/VI
  result. Survived D4/D6, two panels, and the M2a three-lens workflow because
  every prior check tested site inventory/connection, never obs multiplicity.
- **D23**: FD arbitration showed pyro autograd through the traced gpytorch
  target loses the likelihood gradient on all kernel sites (gpytorch
  .data.copy_ in prior injection; noise survives via a non-strict fallback,
  instrumented). S1 keeps proposing with the broken field (upstream); E1 is
  immune by construction; battery gradient reference switched to central FD.
- **D24**: double-backward through the marginal log-prob silently wrong (~16%),
  persists with fast_computations off; battery Hessian gate rebuilt on
  first-order machinery; sentinels pin both D23 and D24; S2 mass-matrix
  consequence recorded for M2c.
- **E1 + battery**: bistar_gp/e1_potential.py (functional_call substitution, no
  deep copy, no .data writes; fit_hmc_e1 = S1f vehicle) and the 29-test battery
  with v1.4-frozen tolerances (worst measured: potential 6e-16, gradient
  2.3e-7, curvature 7.5e-6; margins 2-6 orders). Suite 205 passed + 1 skip.
- **Microbenchmark (firewalled, v1.2 point 6)**: the plan's "~200x deep-copy
  penalty" was mostly the plate — corrected S1 potential 6.0/10.5 ms vs plated
  51.8 ms/1.486 s; E1 per-eval advantage 1.2-3.2x; S1 saturated td7 (127
  lf/draw) where S1f needed 6.7. Final A6 budgets frozen on saturated bounds;
  A5 fallback frozen (N=232, linspace rule, engineering-only predicate) in
  v1.5 + D25.
- **Process**: author halted the Claude multi-agent review mid-flight (token
  budget); review re-run via codex gpt-5.6-sol (xhigh) per author instruction;
  codex findings and dispositions recorded below in this entry once resolved.
- **Della re-benchmark (A7) remains user-executed and owed** before any Della
  assignment.
- **Codex round 1 dispositions (all 14 fixed same-PR)**: A5 predicate completed
  for S4/S1-only survivor sets (S4 cubic costing vs a new 1 h ceiling; S1-only
  fires the fallback via the §1.3 bar); gradient gate widened to every finite
  frozen state, which surfaced that FD cannot referee the jitter-engaged tail
  states — three-tier gate frozen (0.2-of-scale at near_zero_noise;
  autograd-connectedness on the noise coordinate at near_singular, where FD
  carries zero signal; tight gate elsewhere); bench firewall reading recorded
  for author ratification + sanitized real-path errors (exception class only);
  fit_hmc_e1 gained init_to_map parity; eval-mode-entry regression added;
  per-site D23 sentinel; independent site-order oracle; max(1,|oracle|)
  convention pinned; 19x/17x leapfrog-wall ratio pair corrected; docstring/
  prose/stale-line fixes; fork_rng hygiene. Battery 30 passed + 1 skip; suite
  207 passed + 1 skipped.
- **Codex round 2 (on the fix commit)**: 12/14 FIXED verified, 2 PARTIAL, 5 new
  findings — the big ones: the round-1 fixes had edited committed addenda in
  place (restored; everything re-landed as append-only v1.6) and the
  jitter-state gradient gates did not actually discriminate disconnection
  (codex mutation-tested it; an independent big-step FD probe confirmed no FD
  reference works there at any step). v1.6 freezes the honest design:
  connectedness gates on the D23-spared noise coordinate at both jitter
  states, kernel coordinates there explicitly not gated with the residual
  exposure disclosed, execution-completeness assertion over all 28 states.
- **Codex round 3**: (a)-(d) PASS (byte-identical restore verified by hash;
  v1.6-code consistency; silent-skip dead; counts/wording landed); three S1
  wording nits remained, fixed same-PR (test docstrings; v1.7 wording-only
  erratum for one self-contradictory v1.6 phrase). M2b review record closed:
  three codex gpt-5.6-sol (xhigh) rounds, 14 + 5 + 3 findings, all resolved.
- **Suite at close**: battery 30 passed + 1 skip; full 207 passed + 1 skipped.
  PR opening awaits the author (branch feat/d19-m2b-e1, 7 commits).
- **Codex meta-review (author-forwarded) adopted (D26)**: M2b downgraded from
  "done except Della" to "code complete, closeout gated on M2bR". New:
  docs/d22-d24-impact-audit.md (dependency-verified classification — D18
  SIR/prior-IS confirmed unaffected via _mh_log_joint; all HMC/VI/hmc_laplace
  numbers unvalidated pending rerun), prereg v1.8 (goldens retirement, M2bR
  milestone, shared Hessian protocol for S2/S4/profile-Laplace, benchmark
  decomposition rule, Della hold), UserWarning layer on the three affected
  samplers (defaults untouched; disposition fork OPEN). Suite 207+1 with the
  new warnings firing.
- **Ratifications + D27 (author-forwarded codex decision set, implemented)**:
  v1.9 records all seven dispositions + three orchestrator corrections (A5
  pre-fire evaluability, S1/S1f implementation pinning, warnings kept on
  legacy paths). API rerouted: fit_hmc/fit_gp("hmc") = E1-backed;
  fit_hmc_legacy_pyro explicit; vi/hmc_laplace gated behind allow_legacy=True.
  M2bR rerun protocol frozen (docs/m2br-corrected-impact-protocol.md, hash in
  v1.9; six runs, 120-min budget, stop-and-report). Superseded banners on the
  four affected docs; scope-of-claim rule (repo replication, not the thesis).
  Implementation: two codex gpt-5.6-sol (xhigh) subagents (API refactor;
  protocol extraction), Fable verification + prereg/decision prose. Suite 212
  passed + 1 skipped, verified directly. Branch ready for a DRAFT PR.
- **D28 correction round (author-forwarded codex, all four accepted)**:
  banners re-termed WITHDRAWN/UNVALIDATED (superseded reserved for existing
  validated replacements); every "ratified" label corrected to
  proposed-pending-explicit-ratification (v1.10; D27 status amended; PR #7
  body fixed); M2bR split into the single-chain historical-impact AUDIT
  (re-pinned) + a multi-chain validation PROPOSAL (informative/toy_elicited,
  4 chains x td7/td10, arviz R-hat/ESS/occupancy criteria, 6 h ceiling);
  NotPSD rejection policy implemented via codex (catch NotPSDError only,
  pyro-handler rejection, schema v2 notpsd_rejections, regression tests incl.
  the documented crash scenario). Suite 218 passed + 1 skipped. PR stays
  Draft; no runs; decision table returned to the author.
- **D29 (explicit author ballot)**: items 1-7 RATIFIED (item 4 with the
  aggregate-engineering-fields restriction on leapfrog counts; item 7
  audit-only confirmed); item 8 revised per vote — overdispersed frozen
  starts from prior-IS authority references + authority-coverage criterion
  (§6.15 convention), full 6 h design, two-stage freeze; item 9 mechanism
  ratified, diagnostic split implemented (schema v3: warmup/per-draw
  rejection counts, warn-on-any-post-warmup, fail at proposed 1e-3 with
  diagnostics attached, init_values injection). v1.11 records the ballot.
  Suite 224+1. Still pending: revised item-8 protocol + item-9 numeric pair.
- **D30 (codex-implemented preflight)**: user switched to opus-4-8 and asked to
  redo using codex for implementations; reverted my partial inline preflight and
  delegated it to codex gpt-5.6-sol xhigh. preflight_start_state +
  select_start_state (deterministic next-eligible fallback) added to the pending
  item-8 protocol; prereg v1.12, protocol re-pinned. Suite 230+1. Governance held:
  the forwarded codex ratification text is NOT the author's vote (D28 rule), so
  rows 8-9 stay pending and PR #7 stays Draft. Gave the user a pros/cons of item 8
  vs item 9 for the vote.
- **D31 (explicit author ratification of rows 8+9)**: author voted in their
  own words ("I ratify row 8 and row 9. you may proceed") — the valid-vote
  form the D28 rule requires. All 9 decision-table items now ratified;
  prereg v1.13; audit §4 updated; validation-protocol doc retitled RATIFIED;
  E1_NOTPSD_FAIL_RATE relabeled proposed->ratified. PR #7 flipped Draft->Ready
  (codex review rounds + AST firewall audit satisfy the preconditions).
  Bounded "proceed": did NOT merge or run M2bR autonomously — per the ratified
  D27 structure those are the author's next explicit calls (merge, then M2bR
  as a separate PR opening with the two-stage start-freeze). Also gave the
  user a Mauna-critical-path vs paper-cleanup analysis (E1/fixes/NotPSD are on
  the Mauna path; the audit layer + W2/W3 rewrite are independent cleanup; the
  item-8 validation doubles as the plan's G-toy gate that de-risks Mauna).
  Suite 230+1.

## 2026-07-12 — M2bR compute executed: audit + validation (D33), W2/W3 + v1.16 ratified (D34), fail-closed gate v1.16-only (D35), v1.16 escalation FAIL (D36) (Fable session, branch feat/d19-m2br)

Executed both M2bR compute layers and the ratified v1.16 escalation, each stop-and-report, each
preceded by frozen preflight; nothing scientific ran before its gates passed.

- **AUDIT + VALIDATION (D33).** 6 single-chain audit runs (clean) + 16 validation chains from the
  frozen manifest starts. toy_elicited (V3/V4) PASS all criteria → SUPERSEDED (validated R-B pooled-800
  Sin+Linear 0.4205 td7 / 0.4220 td10, occ ≈0.76/0.19/0.05, agreeing with SIR 0.441 and prior-IS
  authority). informative (V1/V2) FAIL 4 marginal criteria → WITHDRAWN. Manifests committed; heavy
  samples untracked. Codex-reviewed; findings fixed.
- **W2/W3 + v1.16 (D34).** After codex (GLM-5.2, GPT-5.6-sol) cross-model review + author direction,
  revised W2 (report corrected NUTS and SIR separately; prior-IS/SIR = one IS-family; mass-faithful
  qualified to the fixed data-elicited N=20 prior), interim-withdrew W3 (VI still on the defective
  target), and ratified the v1.16 informative-only escalation numerical protocol. Corrected the
  "~6-SE" failure diagnosis to ~2.0 combined MCSE (pooled vs per-chain ESS). Built + hermetically
  tested + independently reviewed the v1.16 driver (no chain run).
- **Fail-closed gate (D35, then scoped to v1.16 only).** A 4th review (GPT-5.6-sol) flagged the
  `sampler_fn is fit_hmc_e1` gate as fail-open (partial(fit_hmc_e1) ran ungated). Adopted a fail-closed
  primitive, then — on the author's provenance call — scoped it to the live v1.16 driver ONLY and
  reverted the two frozen, already-executed drivers to their exact as-executed bytes (b56a5a2), so
  the freeze story stays footnote-free. run_common addition is additive; D33 results provably unaffected.
- **v1.16 escalation (D36) — FAIL.** Author-authorized one-shot run at HEAD d0f4b02 (preflight PASSED,
  ~27 min, 90-min ceiling). informative td7, 4 chains, 3000 warmup + 8000 draws. Result: FAIL on
  occupancy (per-chain dev 0.0604 > 0.05) and divergence rate (0.00716 > 0.001). The longer chains FIXED
  ESS (378→1158) and R-hat (1.0114→1.0081) and improved occupancy (0.104→0.060), but the divergence rate
  increased (0.001→0.00716). CORRECTION (D36-c1, codex recheck + Fable reproduction): NOT a high-noise-basin
  effect — divergences concentrate in the larger-step chains 0/2/3 (steps ~0.33–0.40 vs chain1's 0.16;
  chain1 has 0 div despite 65.4% high-band) and endpoint-localize to LOW/MID noise (pooled 137/53/39 of 229;
  1.69%/1.25%/0.20%); an unresolved target-geometry/adaptation/parameterization interaction the longer
  same-strategy run did not resolve. informative stays WITHDRAWN/UNVALIDATED; the same-strategy lane is
  exhausted (next step = strategy change via new addendum, not a budget bump). No corrected-VI claim.
  toy_elicited unaffected.

Commits: audit/validation outcomes 6f96c9e; W2/W3 rev ed89517; D34 build 24113a4; GLM hardening 8fc9edc;
D35 fail-closed 12b7aaf; D35 split d0f4b02; D36 v1.16 outcome (this commit). PR #8 kept Draft throughout;
no Mauna / M2c / VI-repair started; A7 Della on hold (v1.8). Heavy run artifacts never tracked.

## 2026-07-13 — M2c PR A: profile-core implementation (hermetic, no compute)

Implemented the v1.17 M2c **profile core** (rev-5 sha256 `c3e9db66…` verified byte-exact first) on a
fresh branch `feat/d19-m2c-pr-a` off updated `main` (a7e108d7). Scope = P1 functional gradient + battery
+ D23 sentinel, the L-BFGS-B optimizer gate, the curvature gate (SPD+rcond, NO flooring), and the P3
grid/quadrature — **code + hermetic tests only; no compute/recompute/sampler/Mauna/u*(η)/--execute**.

Approach: Claude read the full frozen spec (freeze rev-5 §1/§2/§4, prereg v1.17/v1.4/v1.8§3, architecture
§4) + the governing source files, empirically verified the grid arithmetic (182/184, 76/64, straddle
indices) and the D23 mechanism (`apply_hp_value` severs the graph → grad None), then authored a
byte-exact-derived implementation spec. codex gpt-5.6-sol xHigh implemented against it in two calls
(constants+P1; integration). Claude reviewed every file line-by-line.

Adversarial cross-model review: codex gpt-5.6-sol xHigh (primary) + a Claude Sonnet-5 cross-model pass
(Gemini quota-exhausted / flash 503, Fable out of credits — not worked around). Found + fixed: **2 codex
blockers** (curvature-retry never re-checked stationarity — Sonnet missed this; and the frozen §1
refinement convergence/STOP gate was absent) + **2 Sonnet minors** (D23 floor provenance; inert prior
double-count). codex re-review of the fixes = APPROVE. Every finding cross-verified against source.

Result: 6 new files (`bistar_gp/{m2c_freeze,profile_potential,profile_integration}.py` +
`tests/test_m2c_{freeze_constants,profile_gradient,profile_integration}.py`); full suite **311 passed /
1 skipped** (+34); rev-5 sha256 unchanged; historical buggy triplet + `prior_sensitivity_study.py`
untouched; nothing under `runs/` staged. Commit **ef31571**; **Draft PR #10** → `main`; **D41** logged.
Deferred to the gated v1.18 recompute (disclosed in PR/D41): real u*(η) optimization, curvature gate on
the real profile, corrected band-mass triplet, v1.18 result manifest, S2 HMC smoke. Next: PR B (S2/S3),
C (M1/overlap/nugget), D (diagnostics/manifests/umbrella). No compute begun; holdout SEALED.

**Second/third review rounds (same day):** codex reviewed PR #10's actual diff and correctly flagged
that PR-A shipped the numerical PRIMITIVES without a top-level corrected-profile ORCHESTRATOR (so the
v1.18 recompute would have had to WRITE orchestration, not just run it), plus two conformance gaps
(cap-ladder dropped Mauna edges; E1 site order was test-only). Added the hermetic orchestrator
(`profile_logm_on_grid`, `corrected_profile_band_masses`, `profile_potential_callables`) + S2/S3 fixes.
A scoped re-review (codex + Sonnet-5) then found 4 orchestrator defects — the High-severity one (both
models): the curvature §2c retry can re-optimize u*, but the driver kept g_star/warm-start from the
pre-retry point, silently mis-combining g and K (~7% mass error); plus a fail-closed logm leak, a
`refine=False` bypass of the mandatory §1 gate, and a set-only (dup-accepting) site check. All fixed;
codex + Sonnet re-review APPROVE. Commit **45556e5**; full suite **324 passed / 1 skipped**; PR #10 kept
Draft. Still hermetic — no compute/sampler/Mauna/u*(η)/--execute; historical path unchanged.

**Rounds 4-6 (same day):** R4 — codex found `corrected_profile_band_masses` ran the mandatory nested
refinement but published the coarse level-0 answer; author interpretation recorded (final converged grid
authoritative for all reported outputs; matched-resolution δ_hess/δ_tail; all six diagnostic decade
stages evaluated as a non-fail-closing trace; fail-closed bridge order). Discriminating narrow-profile
test (0.191 level-0-vs-final shift). R5 — out-of-domain band edge crashed the diagnostic trace (codex) +
fail-closed docstring over-claim (Sonnet); guarded to recorded/structured STOP; confirmation pass then
found a residual boundary-exact (edge == decade-cap) crash, fixed by requiring strictly-interior edge
nodes. R6 — codex found the E1-order contract was still self-certifiable (fallback profile + bridge
accepted any permutation); hardened: `ProfilePotential.sites_are_authoritative` provenance +
`profile_potential_callables` fail-closes unless authoritative and `sites_order` equals the E1 order
exactly; adapter test rebuilt on `E1Potential.sites` + negative tests. R7-R9 (E1-order provenance,
progressively deeper, each codex-found + fixed): the provenance flag was forgeable (restate named_priors
order / permutation-as-sites) → the bridge now INDEPENDENTLY re-derives `e1.sites` from the profile's own
model and requires an exact match; then it trusted the mutable `profile.nuisance_sites` for the operative
order → derive the nuisance order from `e1.sites` too; then `g_value`/`g_grad` re-read mutable public
fields per call → made `sites`/`nuisance_sites`/`noise_site`/authority-flag READ-ONLY properties. **S2
authority path CLOSED after 9 rounds — codex + Sonnet BOTH APPROVE**; only private `_`-state mutation
remains, agreed out of scope. Commits **966be5d, 45556e5, bd56786, b7f3bed, 8adaaa5, b11166e, 8adaaa5,
91d7671, b02c4cd, 6eefb9f**; full suite **331 passed / 1 skipped**; rev-5 sha256 unchanged; historical
path untouched; PR #10 kept Draft throughout. No compute begun; holdout SEALED.

## 2026-07-14 — M2c v1.18 recompute STOP: documentation-only record (D45)

Documentation-only session. A single gated v1.18 deterministic profile recompute had been ATTEMPTED
(one-shot in-session `--execute`) and STOPPED at node 0 (noise = `1e-7`). The authorized run's own stdout
emitted only `RESULT: STOP` + reason `curvature: pre-symmetrization check failed` + `stop_index 0`
(`outputs/04`); the numeric characterization (`sym_err ≈ 3.08e-6` vs `SYMMETRY_TOL 1e-6`; SPD True;
`rcond ≈ 6.7e-3`) comes from the POST-STOP EXPLORATORY diagnostic (`outputs/05`), not the authorized run.
No band-mass triplet; nothing written under `docs/m2c_freeze/`. Evidence is a LOCAL, UNTRACKED bundle
`runs/m2c_v118_stop_20260714/` (manifest fixity sha256 `ab73576a…`), left byte-unchanged.

Verified every claim against the bundle and the frozen source (read-only), then recorded the author
disposition. Two independent, author-commissioned read-only audits (NOT GitHub PR reviews; author-recorded — the bundle
preserves only the Fable adjudication REQUEST, no returned verdicts, and GitHub carries no reviews/CI):
**Fable Max = VALID_STOP** (the STOP is faithful frozen-algorithm behavior); **Codex GPT-5.6-sol =
EXECUTION_NOT_AUDITABLE**. Adopted the **conservative disposition**: an UNVALIDATED execution attempt
whose reported STOP is technically plausible but not independently auditable, so **no v1.18 result**
stands. The v1.17 one-shot authorization is **CONSUMED**; **no rerun authorized**; post-STOP node probes
are exploratory only.

Recorded limitations (all verified): post-hoc output/environment capture; unreviewed runtime wrappers
replaced the frozen module bindings; the runner used E1 order (os, ls, lv) while rev-5 specifies
(ls, os, lv); the orchestrator discards gate events; the v1.18 schema has no strictly-typed STOP; post-STOP
probes are hand-picked, not the frozen grid. The directional-order defect does NOT explain the symmetry
STOP (the Frobenius symmetry metric is permutation-invariant) but means the complete frozen algorithm was
not executed exactly.

Changes: **Notes-only** — D45 in `Notes/DECISIONS.md`, this log entry, and the `Notes/SCRATCHPAD.md` M2c
subsection. No source/freeze/schema/manifest/evidence-bundle/`runs/` edit; no scientific or diagnostic
computation (no model/profile/optimizer/gradient/Hessian/sampler run); no v1.18 result or success manifest;
reserved `…gtoy_profile_result_v1.18.json` stays ABSENT; rev-5 `c3e9db66…` and v1.17 `65381bc7…` unchanged;
no new preregistration version; no tolerance/algorithm decision; no rerun authorization; nothing called
superseded or validated. Committed on a docs branch; Draft documentation PR opened, held before Ready/merge.

## 2026-07-18 — M2cR R3: diagnostic protocol + decision-rule freeze (D50, prereg v1.21) (Fable session, branch feat/d19-m2cr-r3-diagnostic-protocol)

**Done:**
- Read-only R3 preflight at `origin/main` = `35ccc3d` (PR #17/R2a merge): startup gate, a
  requirement-to-artifact map over plan §6/§8, v1.17–v1.20, D47–D49, and the merged R2/R2a
  source; surfaced the Layer-1b enforcement gap and the instance-residence determination; one
  compact author ballot. Author ratified A1 (close Layer-1b enforcement inside R3), B (rows
  evaluator), C (literal §3.1 protocol-manifest key set), and corrected the PR #17 merge SHA
  used in all durable records.
- Docs-first freeze, then bounded implementation delegated to Codex gpt-5.6-sol xHigh; Fable
  read every change and applied four pre-commit corrections (exact B12(b) windows with no ULP
  slack; `expected_noise` provenance to the true frozen constant `0.061867347763041584` after
  Codex flagged the rounded fixture value; `map_fitted` seed placement; launch-side addendum
  check). Two fresh-detached-worktree regenerations (environment-derived artifacts and the
  preboundary set byte-identical both cycles); the R2a F8 report cross-check failed closed on
  the stale fixed total and the report was updated truthfully (8,870,266 B).
- One bounded advisory panel at `c855d5f`: Opus 4.8 APPROVE, GLM 5.2 APPROVE, Kimi K3 REVISE
  (no BLOCKER/MAJOR anywhere). Six findings confirmed against source and fixed in the single
  authorized pass (`9c4452f`), three dismissed with evidence — all recorded in D50 Update 1.

**Committed:** `0bbc69d` (v1.21 + D50 + schema + parameters) · `365d7b3` (implementation +
interim Layer-1b manifest) · `0071fd4` (regen) · `c855d5f` (report currency) · `9c4452f`
(panel corrections) · `c038f47` (regen + Layer-1b re-pin) · final docs commit. Full suite at
`c038f47`: **957 passed / 2 skipped / 0 failed**. Draft PR opened and left NOT Ready.

**Key points:** the diagnostic-record instance is the diagnostic run's persisted
`payload.json` (no R2a layout amendment needed); every R4 diagnostic launch now requires the
committed, chain-bound protocol manifest and schema-valid persisted payload; R4 stays blocked
on a fresh author grant; the v1.18 label/instance stay permanently unused/absent; D45 stays
UNVALIDATED_ATTEMPT.

## 2026-07-19 — M2cR R4 preflight (BLOCKED) + R3a production launch vehicle (D51); Draft PR opened

**What was done:** The author-directed read-only R4 preflight at `origin/main` `b19cce2` (the PR #18
merge) passed the startup gate and every authority verification — all infrastructure/environment/
protocol pins byte-verified, v1.17 canonical recomputed `65381bc7…`, all 154 worktree-root
importable-manifest entries matched with zero extras, ledger exactly the one D45 line — and returned
**BLOCKED** on one gap: no committed argv-level production launch vehicle. The author's ballot
adopted T-B regeneration, one_shot, Draft evidence PR, and capture-at-source evidence, REJECTED an
R4-created launcher, and authorized the narrow hermetic **R3a** amendment (D51). This session then
delivered R3a on `feat/d19-m2cr-r3a-launch-vehicle`: the fixed diagnostic bootstrap template
(`d62fee60…`), `bistar_gp/m2cr/r4_launch.py` (`python -m bistar_gp.m2cr.r4_launch`; closed-world
canonical launch packet; read-only validate mode; `--execute` gate appending one schema-valid
`launch_attempt_started` line between factory success and capture; only `launch_config_from_freeze`
then `capture_run`; no wrappers), a 48-test hermetic battery, and the four-artifact regeneration at
the exact code commit with report currency (fixed total 8,870,677 B).

**Committed:** `d0a317d` (docs-first) · `c11db47` (implementation) · `601f599` (regen) · the final
docs commit (D51 Update 1 + SCRATCHPAD + this entry). Full suite at `601f599`:
**1005 passed / 2 skipped / 0 failed**.

**Key points:** Codex gpt-5.6-sol xHigh implemented under the bounded brief with every line
Fable-verified (one recorded deviation, packet-derived repo root, verified sound); ONE read-only
Opus 4.8 exact-head review returned **APPROVE** with zero defects and two advisory NOTEs, both
independently verified; the launcher takes no infrastructure code pin (ballot-C precedent) and the
R2 code-pin set is untouched; R4 remains BLOCKED and NOT begun — it needs its own author-authorized
preparation and one-shot launch grant after this PR merges; D45 stays UNVALIDATED_ATTEMPT; the
v1.18 instance stays absent. Draft PR opened and held before Ready/merge. HARD STOP.

## 2026-07-19 — M2cR R4 executed (INFRA_FAILURE) + closure certified + R5 audit APPROVE_RECORD (D52 Updates 8–12, D53); PR #20 flipped Ready, STOP before merge

R4 was prepared, executed, closed, and independently audited across this arc. R4 preparation went
through three superseded freezes (E `71ade35` / E2 `baf5dd7` / **E3 `367667f`**) with an Option-B
audit-hardening amendment (J `b1ee5ec`) before the author returned the one-shot `--execute`
authorization. The launcher was invoked once on packet-03 at E3; the diagnostic probed all 1,481
closure nodes and wrote `payload.json`, but a post-execution parent-side origin-binding attestation
faulted on a torch-internal `_remote_module_non_scriptable` module pointing at a nonexistent
`torch-git` path — terminal **INFRA_FAILURE / attestation_fault / not_a_result: true**; the one-shot
grant `m2cr-auth-20260719-03` was **CONSUMED** (marker present). Machine closure was first BLOCKED by
a pre-existing `verify_ledger_against_evidence` defect (marker-name→file resolution ignored the four
aliased attestation stems); the author authorized a narrow post-execution closure-auditor amendment
(K `2797cef` → L `7a6871d` → K2 `6636929` → **L2 `76f3c39`**) promoting capture's mapping to a public
immutable contract the auditor consumes. The fixed auditor certified the closure over the preserved
E3 evidence — ledger events 000008/9/10 machine-derived, all 1503 evidence files byte-identical to
the pre-amendment baseline — committed at **`f78d16a`** with a Draft evidence PR (#20).

**R5 (this session):** Fable Max performed the independent read-only record audit at exact head
`f78d16a` and returned **APPROVE_RECORD**. Every hash, schema, chain member, and the machine-derived
closure were recomputed from committed bytes / git objects (not adopted from D52): auditability
ok/0-errors, `EVIDENCE_TREE_DIGEST 7154212a…` = baseline, the E3 chain retrieved byte-exact from E3
(distinct from the regenerated current-tree manifests), `payload.json` schema-valid. The frozen §6.3
`evaluate_decision_table` was applied mechanically with `terminal_status=INFRA_FAILURE`: row 1 does
not match (`purity.pass:true`), **row 2 is the first match** →
`{"row":2,"track":"evidence_incomplete_no_amendment"}` = **PRESERVE_STOP; no amendment**. Row 8 did
not fire, so R6 is unreachable and no origin-binding repair / rerun / interpretation is authorized.
Two NOTE-level wording observations recorded (commit-message event range; underspecified digest
recipe), no action.

**Committed:** the Notes-only R5 closeout (D53 + SCRATCHPAD + this entry) — no code, schema, manifest,
ledger event, evidence file, freeze artifact, payload, or v1.18 path touched. PR #20 body updated
with the Fable audit provenance (AI audit, not a GitHub review/CI; first-match row 2; the D53 head
itself not re-audited by Fable; no amendment/R6/repair/rerun authorized), then flipped to **Ready**
after a mechanical preflight. The previously certified unflagged suite (1018 passed / 2 skipped) was
NOT rerun for a Notes-only tail. **STOP before merge.** The M2cR remediation arc ends with the STOP
preserved; D45 remains permanently UNVALIDATED_ATTEMPT; the v1.18 instance stays absent. No
replacement protocol, Della, M2d, or broader D19 planning begun.
