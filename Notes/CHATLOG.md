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
