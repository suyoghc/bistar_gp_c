# D22-D24 impact audit — artifact classification and author ratification checklist

Status: RATIFIED with corrections (author, 2026-07-11, via the forwarded
codex recommendation set and the instruction to implement it; D27 and prereg
addendum v1.9 record the ratifications, the A5 trigger correction, and the
API disposition). Date: 2026-07-11.

**Scope-of-claim rule (ratified):** these defects invalidate THIS
repository's attempted HMC/VI replication — a pyro/gpytorch integration.
They establish nothing about the thesis's original implementation (VI there
was gpflow/ADVI, a different stack) or its conclusions. Every superseded
banner and decision entry carries this framing. Scope: every artifact
produced through the pre-correction inference paths, classified per the codex
meta-review recommendation: UNAFFECTED (dependency-verified), INVALID PENDING
RERUN, or NEEDS DEPENDENCY TRACING. Historical text stays for provenance;
affected conclusions are marked superseded/unvalidated, never silently
edited.

The three defects (full records: DECISIONS D22-D24; prereg v1.3/v1.6):

- **D22 (fixed)**: `_hmc_pyro_model` targeted p(theta) L(theta)^N — every
  fit_hmc / fit_vi / fit_hmc_laplace result sampled or approximated a
  likelihood-to-the-N tempered posterior.
- **D23 (open, upstream)**: pyro/gpytorch autograd loses kernel-site
  likelihood gradients in the traced target — post-D22-fix, fit_hmc proposes
  with misguided dynamics (valid target, broken guidance), fit_vi's ELBO
  lacks kernel-site likelihood gradients entirely (kernel posteriors are
  effectively prior-guided), and fit_hmc_laplace inherits both.
- **D24 (open, upstream)**: create_graph double-backward through the
  marginal log-prob is silently wrong — fit_hmc_laplace's whitening Hessian
  and ANY Laplace/profile-Laplace consumer of a second-order autograd
  Hessian over GP hyperparameters is affected. First-order FD Hessians
  (e.g. `laplace_evidence.numerical_hessian`, candidate-parameter space) are
  immune.

## 1. UNAFFECTED (dependency-verified this session)

| Artifact / machinery | Why unaffected | Verification |
|---|---|---|
| MAP fits, `fit_map_samples`, candidate MLEs (D11 protocol) | no pyro target, no NUTS gradients | code path |
| `fit_mcmc_simple` (post-D13) | scores `_mh_log_joint` (mll x n) + raw Jacobian; never touches `_hmc_pyro_model` | fit.py:158-163 |
| Prior-IS / SIR arms of D18 (headline 0.441; pools 0.419/0.438/0.431) | weights score through `_mh_log_joint` directly | prior_sensitivity_study.py:233 |
| D12 prior-IS mass numbers (0.19/0.67) | same direct-likelihood scoring | same mechanism |
| `sample_prior`, prior-predictive checks, Stage-0 scorecards (§9) | prior draws only; no obs term, no gradients | code path |
| `laplace_evidence.py` / Z_Mx machinery (D3/D15/D16) | candidate-parameter space, own likelihood, FD `numerical_hessian` | code path |
| Viz-unification canonical figures (D17; Sin+Linear 0.86-0.99) | `--gp-method map` default; IS estimator scores directly | model_priors_laplace.py:13 |
| Metrics (`pw_kl_vcal` etc.), aggregation, decomposition CODE | consume sample dicts; sampler-agnostic | code path |
| M2a infrastructure (A9 provenance, A10 freeze, A4 registry, seal API) | no sampler dependence | D20 record |
| Planning benchmark TIMING observations (D8 engineering: deep-copy cost, thread scaling) | wall-clock facts about the code that ran; superseded as planning anchors by v1.5/v1.6, not invalidated as observations | v1.6 |

## 2. INVALID PENDING RERUN (conclusions superseded/unvalidated)

| Artifact | Defect(s) | Standing |
|---|---|---|
| D18 HMC headline 0.696 (td7) / 0.683 (td10) and every HMC-arm number | D22+D23 | UNVALIDATED; the "density-mode-region answer" interpretation rests on a tempered target |
| D18 VI arm | D22 (ELBO x N) + D23 (no kernel-site likelihood gradients) | UNVALIDATED |
| D12 method x metric: hmc / hmc_laplace / vi columns, "hard assignment 200/200", "VI migrates to the mass basin" reading, td7-vs-td10 appendix | D22+D23 (+D24 for hmc_laplace) | UNVALIDATED; the VI-migration story may be a D23 artifact (prior-guided kernel sites), not a mass phenomenon |
| W2 gate reasoning (keep hmc default "density-mode answer, disclosed") and W3 VI framing | built on the above | RE-DECIDE after corrected reruns (author) |
| D8 Mauna impact-assessment HMC sections (noise ~0.001 posterior, reversal mechanism attribution to "new = posterior") | D22+D23 | UNVALIDATED as posterior claims; the D4/D6 fix DIRECTION story stands (old = prior draws, structurally proven), but "new = the posterior" is now "new = a tempered posterior with broken guidance" |
| Every `fit_hmc_laplace` result anywhere | D22+D23+D24 | UNVALIDATED |
| HMC sample caches: `runs/figures_regen/*` wave-1 HMC caches + dependent figures, `runs/fit_method_metric_comparison/samples_*.npz` (hmc/hmc_laplace/vi entries), any `hmc_samples.pt` | D22+D23 | never reuse for science; retain on disk as provenance |
| G-toy golden candidates derived from old HMC/VI (§6.9 references to the confined 0.696) | D22+D23 | RETIRED as goldens by v1.8; prior-IS/SIR/RW-MH references survive |

## 3. NEEDS DEPENDENCY TRACING (corrective milestone M2bR)

| Artifact | Question |
|---|---|
| `bistar_gp/results/` figure sets regenerated 2026-07-08 | which panels consumed HMC/VI draws vs MAP/prior/IS paths — per-figure provenance sweep |
| `docs/impact-assessment-results.md` toy sections (mcmc_simple comparisons cite HMC anchors) | which comparisons survive with mcmc_simple/MAP/IS-only anchors |
| kb/Wiki articles citing HMC-vs-VI behavior (local, gitignored) | re-word after corrected reruns |
| `experiments/d19_bench.py` (A7 vehicle) | measures the CORRECTED potential post-D22, but persists `map_noise_variance_normalized` (a scientific value; M1-era convention) and its committed anchors are pre-D22 — REWORK to the v1.2-point-6 firewall before any Della run (v1.8) |

## 4. Author ratification checklist — DISPOSITIONS (2026-07-11)

Item 1 (classifications + superseded-not-caveated rule): RATIFIED; banners
applied to the four affected docs. Item 2 (API): DECIDED as D27 — public
fit_hmc routes to E1; legacy pyro path explicit (fit_hmc_legacy_pyro,
warning retained); fit_vi and fit_hmc_laplace unavailable through the
scientific API pending repair, legacy behind allow_legacy=True opt-in.
Item 3 (N=232): RATIFIED, with the trigger CORRECTED in v1.9 — the
"S1-only survivor set fires the fallback" branch is removed (the legacy S1
path is not a valid paper-target vehicle post-D23; no valid survivor means
O4, not a scale change). Item 4 (A6): NOT ratified as-was — v1.9 adds the
dimensional clarification (wall-clock, per strategy x arm x scale,
warmup/retry-inclusive) first. Item 5 (firewall fields): RATIFIED as
enumerated. Item 6 (M2bR + frozen rerun): AUTHORIZED — toy-only, corrected
E1 HMC over the D18 prior configurations + affected D12 HMC rows, no
VI/hmc_laplace until repaired, at most 2 h local wall with stop-and-report;
protocol frozen in v1.9 before any run. Item 7 (Della hold): RATIFIED.

Original checklist (for the record):

1. **This audit's classifications** (tables above), and the standing rule:
   affected conclusions are marked superseded/unvalidated in place, never
   silently edited.
2. **Public API disposition (D26 fork, OPEN)** — interim state shipped now:
   `fit_hmc`, `fit_vi`, `fit_hmc_laplace` emit a UserWarning citing
   D22-D24 and pointing to the gated `fit_hmc_e1`; docstrings corrected; NO
   default changed, nothing removed. Choose: (a) route `fit_gp("hmc")`
   through E1 once the author accepts the battery, demoting the pyro path
   to an explicitly named historical diagnostic; or (b) keep defaults,
   warnings stay until an E1-based VI and S1f replacement land at M2c.
   Recommendation: (a) for HMC at M2bR close; VI needs its own E1-based
   implementation before any default exists.
3. **A5 fallback N=232** — derivation: the frozen whole-span rule
   `np.round(np.linspace(0, 460, N)).astype(int)`; N=232 keeps the full
   38.4-year span, gives step 460/231 = 1.991 months so sampling cycles all
   twelve month-of-year phases (N=231 gives step exactly 2.0 = six fixed
   phases forever), and cuts dense-solve cost (461/232)^3 = 7.8x. Trigger
   sets that fire it: every G-B survivor's projected full-N cost exceeds
   its ceiling (S1f/S2/S3 by the leapfrog projection; S4 by the cubic law),
   or the survivor set contains only S1 (barred at full N by §1.3).
4. **Final A6 ceilings** (v1.5 + v1.6): S1f sub-150 2 h; S2 2 h; S3 2
   dev-days + 4 h; S4 pilot 30 min; S1 sub-150-only 6 h; Stage A 1.5
   h/arm; toy smoke 30 min; paper-target full-461 4 h per strategy x arm
   (E1 path) and 1 h for S4; S1 full-N: none (barred).
5. **Microbenchmark firewall reading (v1.6 item 6)** — exact persisted
   fields: meta (timestamp, git sha, torch/gpytorch/pyro/python versions,
   platform, thread count, cpu count, hostname), firewall note, per scale:
   n_points; per-eval median/mean ms for S1-value, E1-value, S1-grad,
   E1-grad + the two ratios; per sampler: wall_s, n_draws, n_warmup,
   max_tree_depth, seed, leapfrog caveat string, per-draw and total
   sampling leapfrogs, wall-ms-per-leapfrog. Nothing else exists in the
   artifact (AST-audited).
6. **M2bR corrective milestone** (v1.8): scope and its small preregistered
   corrected-impact rerun, BEFORE any M2c work.
7. **Della hold** (v1.8): no A7 run until d19_bench.py is reworked to the
   timing-only firewall and its pre-D22 anchors are marked superseded.
