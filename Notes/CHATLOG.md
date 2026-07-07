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
