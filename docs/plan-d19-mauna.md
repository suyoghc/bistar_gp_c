# D19 — Mauna Loa prior-sensitivity + sampler-options study: frozen plan and pre-registration v1.0

**Status: FROZEN 2026-07-10 (milestone M1), before any pilot, posterior, or BMS\*
result exists.** No scientific result of this study may be read before this document
and its commit are reviewed. Implementation (M2a) follows in a separate PR.

Governing briefs: the PROVISIONAL W6 Mauna brief + its addendum (local writeup log;
precedence fixed by decision A11 below), W1/W2/W5; committed history D6, D8, D11,
D12/D13, D18. Review provenance: the planning-session plan went through four codex
gpt-5.6-sol rounds on 2026-07-10 — round 1 (14 findings, verdict FIX-FIRST, all
accepted at least partially), round 2 (decision addendum A3-A11, milestone split,
holdout seal, concrete elicited-prior proposal), round 3 (A1 ratified, six
corrections, scorecard v1 then v2 with corrected functionals), round 4 (A2-v1
ratified, two wording corrections). Everything below is the post-round-4 state;
superseded planning-session wording is not preserved here. A fifth round reviewed
the freeze commit itself (gpt-5.6-sol, verdict FIX-FIRST, 10 findings, 6 HIGH);
every finding was resolved at documentation level before this commit finalized —
the substantive corrections are marked "round 5" inline, so v1.0 already contains
them and no amendment is owed for that round.

Companion artifacts in this commit:

- `experiments/d19_prior_scorecard.py` — Stage-0 scorecard, deterministic
  (verified: regenerates `runs/d19_planning/scorecard_v2.json` byte-identically).
- `experiments/d19_bench.py` — the planning micro-benchmark script (the Della
  re-benchmark vehicle for A7/R6; timings are machine-dependent, JSONs are the
  frozen record).
- `runs/d19_planning/{bench_sub,bench_full,scorecard_v2}.json` — frozen planning
  evidence (deliberately tracked).
- `Notes/DECISIONS.md` D19 — the decision-log entry for this freeze.

## 0. Facts verified during planning (2026-07-10, read-only session on fcd70e2)

- **Sampled-site inventory: 7 pyro sites**, confirmed via
  `pyro.infer.mcmc.util.initialize_model` on `build_mauna_loa_kernels()`: trend
  ls + os, seasonal ls + os, medium ls + os, noise (`bench_*.json:sampled_sites`).
- **The seasonal period is a trainable plug-in, not a fixed constant** (codex
  round-1 catch, verified live). `period_length` carries no prior, so it is not a
  pyro sample site, but `raw_period_length` remains `requires_grad=True` under
  `Interval(0.99, 1.01)` (`bistar_gp/model.py:132-141` — the Interval constraint
  at line 134, the plug-in assignment `= 1.0` at line 141; the registered raw
  parameter stays trainable by default despite the "keep this one fixed"
  comment), and `fit_map` moves it from 1.0 to 0.99962 in 100 iterations. Every pre-D19 Mauna analysis is therefore
  conditional on a data-fitted plug-in period near 0.9996 — an omitted disclosure
  until now (standing disclosure 4, section 6.14). Decision A10 freezes the period
  at exactly 1.0 from M2a (`requires_grad_(False)` + an assertion that it stays 1.0
  through every MAP/multi-start path), keeping the active-site inventory at 7 for
  M0 and 9 for M1.
- **Data provenance (measured)**: OpenML `data_id=41187`, name
  `mauna-loa-atmospheric-co2`, fetched version 1; raw frame 2225 weekly rows,
  columns `[year, month, day, weight, flag, station, co2]`; the `co2 > 0` filter
  currently drops 0 rows; monthly-mean aggregation gives 521 months; cutoff
  `max(x) - 5.0` years splits 461 train / 60 test; `y_mean = 336.188 ppm`,
  `y_std = 14.583 ppm` (so `y_std^2 = 212.68 ppm^2`); x centered at 1977.711 and
  not scaled (units stay years; one sampling interval = 1/12 y = 0.0833); train
  span 38.75 y. sha256 of the co2 column =
  `7e301efd6dbd2b4007723368aa69ebd2259ea6aa1d431650c209df181f244cb9`. D8's "N~457"
  was approximate; the measured count is 461.
- **Loader defects** (`bistar_gp/data.py::load_mauna_loa`; wording per codex
  round 1): on a fetch failure the documented synthetic fallback is commented out,
  so execution reaches `np.argsort(x_all)` with `x_all` unbound and raises
  `UnboundLocalError` (data.py:127); a second `except` clause (data.py:114) is
  unreachable; the `co2 > 0` filter is currently a no-op. `data_id=41187` does
  identify the dataset record (the earlier "version not pinned" phrasing overstated
  that defect) — the real gaps are runtime checksum verification and a canonical
  local artifact, and the planning hash covers only the co2 column, leaving
  year/month metadata unprotected. M2a items under decision A9.
- **Stale slurm script**: `experiments/job_mauna_loa_hmc.slurm` passes `--mode`,
  `--subsample`, `--n-posterior`, none of which exist in the current
  `bms_star_mauna_loa.py` argparse; it would crash on submission. M2a refresh.
- **Two candidate sets exist** (resolved by A4, section 3): the 4-model ladder in
  `bistar_gp/mauna_loa_candidates.py` and the 3-model inline set in
  `experiments/bms_star_mauna_loa.py`.
- **Metric gap**: the Mauna scripts score `pw_mse / pw_nll / pw_hellinger /
  pw_kl_forward / pw_kl_symmetric`; none runs the W1-ratified default
  `pw_kl_vcal`. Wired in at M2a.
- **Sub-150 screening design adopted**: even-index whole-span subsample
  (`np.round(np.linspace(0, N-1, 150))`), mean stride 3.12 months, all 12 calendar
  months covered (measured), never the first 150 points. Screening only.
- **Measured discovery that reshapes Stage B**: the pyro NUTS potential
  (`_hmc_pyro_model` deep-copies the model per evaluation — the D6-fix pattern)
  costs 1.49 s per log-joint eval and 2.79 s per gradient at N=461, while the
  direct gpytorch parameter path costs 6.3 ms per marginal-likelihood eval and
  15.5 ms per forward+backward — a roughly 200x gap (238x eval, 181x gradient).
  It reproduces the recorded history (127 leapfrogs x 2.8 s = 6 min per saturated
  depth-7 iteration; D8's 28-hour full-N regeneration corresponds to ~90
  leapfrogs/iteration average) and makes a direct-potential prototype (enabler E1)
  the single highest-leverage engineering item.
- **MAP-protocol flag**: the benchmark used the 300-iteration HMC-prep convention,
  not a converged MAP (experiments use 800; D8's chains rested at trend ls 8 and
  32, far from the 300-iter value 4.41). Every Hessian consumer in the study must
  standardize the MAP protocol first (risk R10). The 300-iter values trend ls
  4.41 y vs medium ls 3.34 y already suggest trend/medium proximity worth watching
  under the identifiability gates (risk R5).

## 1. Measured cost table and projections

Platform: macOS arm64 (14 cores), torch 2.10.0, default 10 threads, gpytorch
1.15.1, pyro 1.9.1. All timings warmed up and repeated (median of 5 where marked);
jitter = package default. Raw JSONs: `runs/d19_planning/bench_{sub,full}.json`.

### 1.1 Measured

| Operation (measured) | sub-150 | full N=461 | notes |
|---|---|---|---|
| MAP fit, 300 Adam iters (lr 0.02) | 1.46 s (4.9 ms/iter) | 4.64 s (15.5 ms/iter) | noise var at stop: 0.00172 / 0.00193 normalized |
| log-joint eval, pyro potential, unconstrained | 51.8 ms | 1.486 s | median of 5; full/sub ratio 28.7 vs (461/150)^3 = 29.0 |
| gradient of pyro potential | 84.6 ms | 2.793 s | median of 5 |
| 7-dim Hessian at MAP (`torch.autograd.functional.hessian`) | 0.794 s | 33.8 s | SPD at both scales, 0 eigenvalues below the 1e-6 floor; min eig 0.069 / 0.075; condition number 4.6e4 / 4.2e5 |
| prior-proposal eval (draw applied via `apply_hp_value`, one `ExactMarginalLogLikelihood` eval) | 2.15 ms | 6.25 ms | 0 failures in 1000 |
| 100 prior-proposal evals | 0.21 s | 0.63 s | measured directly |
| 1000 prior-proposal evals | 2.13 s | 6.32 s | measured directly (cap not threatened) |
| profile-Laplace grid point: 150-iter profile opt with noise frozen | 0.53 s | 2.17 s | plus the Laplace-det cost below |
| profile-Laplace grid point composite (opt + 7-dim Hessian) | 1.32 s | 36.0 s | composite at the 300-iter MAP; see the estimate caveat in 1.2 |
| single-thread retiming (full N only) | n/a | log-joint 3.97 s, gradient 5.90 s, prior eval 8.3 ms | 10-thread speedup only ~2.1-2.7x at this N |

MAP hyperparameters at the 300-iteration stop (full N, normalized coords): noise
var 0.00193 (= 0.41 ppm^2, sd 0.64 ppm), trend os 0.99 / ls 4.41 y, seasonal os
0.094 / ls 2.68 (phase units), medium os 0.075 / ls 3.34 y.

### 1.2 Projections (each row carries its anchor and label; none is budget-grade for E1 until M2b)

| Projected operation | sub-150 | full N=461 | anchor and label |
|---|---|---|---|
| NUTS leapfrog, pyro path | 85 ms | 2.79 s | = measured gradient |
| depth-7 iteration, saturated (127 leapfrogs) | 10.7 s | 355 s | leapfrog-count bound x measured gradient; bounds leapfrog work, not wall-clock overheads |
| 400-iteration chain (200w+200d), pyro path | ~1.2-1.5 h | ~28-39 h | upper end = saturated bound; lower end anchored to D8 history (~90 leapfrogs/iter average full-N; ~90 min/400 iters at sub-150) — no unanchored "typical" endpoint |
| NUTS leapfrog, direct-potential path (E1) | ~5 ms | ~16 ms | KERNEL-COST PROXY: equals measured fit_map fwd+bwd per iteration; excludes transforms, prior terms, and pyro NUTS overhead. PENDING the M2b E1 NUTS microbenchmark |
| 400-iteration chain, E1 path, saturated | ~4 min | ~14 min | same proxy x 127-leapfrog count; PENDING M2b — not a measured bound |
| 27-start Nelder-Mead mode hunt (~500 evals/start) | ~29 s | ~85 s | prior-eval unit cost |
| multi-start MAP (8 x 800 iters) | ~31 s | ~99 s | per-iter cost |
| 40-point profile-Laplace noise grid | ~53 s | ~24 min | ESTIMATE, not a bound: off-MAP Hessians can run slower, be non-SPD, or need retries; the composite was measured at the MAP |
| prior-IS pilot 60k draws | ~2.2 min | ~6.3 min | per-eval cost |
| prior-IS pool 600k draws | ~21 min | ~63 min | 3 pools = 3.2 h sequential, embarrassingly parallel |
| RW-MH referee, 30k chain (direct path) | ~1.1 min | ~3.2 min | per-eval cost |

Full budgeting of any full-scale run additionally requires the observed
leapfrog-count distribution from that strategy's own sub-150 pilot (codex round 1,
finding 9): the cubic (461/150)^3 reference applies only to operations dominated by
a fixed number of dense GP solves, not to end-to-end samplers whose leapfrog counts
change with geometry.

### 1.3 Della guidance

The della-h16 history (D3/D8: ~5x slower per op single-thread, 8-thread thrash
inflating funnel iterations to ~35 min, two 4-8 h timeouts) plus the measured weak
thread scaling (2.1-2.7x from 10 threads) fixes the policy: pin threads (start at
OMP/MKL 1-4), re-run `experiments/d19_bench.py` on Della before assigning any job
(decision A7, risk R6), and use Della only for embarrassingly parallel work
(independent chains, seeds, IS pools, prior arms, surviving strategies), never for
single-chain latency. Per stage: Stage 0 local; Stage A local for single-arm
latency, Della for arm x pool fan-out after its benchmark; Stage B pilots local
first (sub-150); full-N E1-path chains either place; full-N pyro-path chains
nowhere without explicit author exception; Stage C scoring local, SIR pools
Della-parallel.

## 2. Staged design

### Stage 0 — elicitation record + prior scorecards per arm (low-cost, not free; mostly complete at this freeze)

1. **Data-provenance gate** (measured values in section 0): pin OpenML id 41187 +
   fetched version 1 + checksums; record filter, aggregation, cutoff, and counts
   (2225 raw, 521 monthly, 461/60 split) in the study config and report; harden
   the loader per decision A9 (M2a).
2. **Nugget observation-model memo** — RESOLVED as decision A1: the nugget
   represents measurement error plus uncorrelated monthly-aggregation/residual
   variance; correlated short-term discrepancy belongs to M1's Matern-3/2
   component, not the nugget. Arithmetic context (recorded, not a conclusion): an
   instrument-only nugget near 0.2 ppm sd maps to (0.2/14.583)^2 = 1.9e-4
   normalized, below the likelihood-favored 7e-4 to 1.9e-3 range, so the semantics
   choice materially moves the anchor. Instrument precision is not equated with
   total residual variance, and M1 must not be advantaged by forcing the nugget
   below its stated observation model (diagnostic in G-A; reference value 1.9e-4).
   Era caveat: the 0.2 ppm figure describes NOAA's modern system; the OpenML
   record's source/instrument eras (station column, 2225 weekly rows, 1958-2001)
   still need the Stage-0 transcription (section 8), which must separate analyzer
   accuracy from weather/aggregation variability. The elicited nugget band absorbs
   era heterogeneity; era-dependent noise stays a disclosed limitation out of
   scope.
3. **Per-site physical-units elicitation** — RESOLVED as decision A2 (arm tables
   in section 7; scorecard in section 9). Unit note: the gpytorch periodic
   lengthscale is in phase units relative to the fixed 1-year period, not years
   (risk R11). Baseline moments recorded for contrast, in physical units: trend-ls
   prior median e^4 = 54.6 y (exceeds the 38.75-y observed span); noise prior mean
   1.75 normalized = 372 ppm^2; trend-os mean 8.0 normalized = 1701 ppm^2.
4. **Transformation documentation** (W5 discipline from day one): x centered by
   the realized train mean (1977.711), unscaled, so elicited times in years pass
   through; y standardized by realized train stats, so elicited amplitudes divide
   by y_std = 14.583 ppm and elicited variances divide by y_std^2 = 212.68 ppm^2.
   Because y_mean/y_std/x_offset are realized-data summaries, every arm's
   transformed prior is data-scaled in that specific sense; the disclosure list
   opens with these three plus any further summary an arm uses.
5. **Attribution arms** — RESOLVED as decision A2 (roles and frozen order in
   section 6.4).
6. **Prior-predictive scorecards per arm** — DONE, v2 frozen in section 9 with
   verdicts written before any posterior work.
7. **M1 bounds** — RESOLVED as decision A3 (bounded logit-normal lengthscale
   prior on the hard Interval [0.1, 1.0] y; lower bound just above one sampling
   interval 0.083 y so the component cannot imitate the nugget; upper bound below
   the medium-RBF regime, whose 300-iter MAP lengthscale measured 3.34 y).

**Gate G0 (author, at M2d):** nugget semantics stated (done, A1); arm parameters
ratified (done, A2); M1 bounds ratified (done, A3); era/source transcription
closed or its amendment recorded (section 8); W5 disclosure list complete. No
Stage A compute before G0.

### Stage A — sampler-independent geometry per arm

Order: sub-150 screening first; full N for arms still in play. Arms run in the
frozen order of section 6.4. Per arm:

- **Standardized MAP**: multi-start (8 starts: current values, prior medians, and
  perturbations), 800 iterations, convergence check; ~99 s full-N per start set.
  Upstream of every Hessian consumer (risk R10).
- **SPD Hessian + condition number** in the unconstrained coordinates (~34 s
  full-N); report eigenspectrum, floor clips, and condition (measured baseline:
  SPD, 4.2e5).
- **Reduced mode hunt** (D18 pattern): 27-start Nelder-Mead on the direct
  marginal-likelihood path with valley checks between verified modes (~85 s
  full-N).
- **Trend-lengthscale ridge probe**: profile the log joint along trend ls over the
  D8 stuck-chain range (8 to 32) at 20 points; characterizes the 418-nat structure
  per arm and directly measures whether prior revision moves it (the open question
  W6 keeps open; the probe measures, it does not presume). A profile curve has no
  occupancy or SE semantics and never issues a coverage verdict alone
  (section 6.8).
- **Profile-Laplace noise marginal**: 40-point grid (~24 min full-N, estimate),
  the D18 arbitration tool; per-point SPD status recorded.
- **Prior-IS behind gate G-IS** (candidate, not promised): 60k pilot per arm
  (~6.3 min full-N); proceed to 3 x 600k independent pools (~63 min each,
  Della-parallel) only if the pilot passes G-IS (section 6.7). Fallback ladder,
  each behind its own pilot and the same gate: defensive mixture (1/2 prior + 1/2
  Laplace at the Stage-A MAP/Hessian, reusing D16 machinery), Laplace-guided IS,
  SMC with tempering. Bridge sampling only ever an evidence diagnostic (it
  produces no posterior predictive particles).
- **RW-MH referee behind gate G-referee** (candidate): Jacobian-corrected (D13
  `_raw_log_jacobian`), 30k chain ~3.2 min full-N on the direct path; role =
  ridge-crossing evidence.
- **M1 identifiability pre-check** (only for P-comb+M1-v1): the quantitative gates
  of section 6.7 (bound occupancy, duplication, geometry non-worsening,
  nugget-floor diagnostic). Failure blocks M1's promotion to any full run.

**Gate G-A (per arm):** geometry dossier complete (MAP table, Hessian status, mode
inventory with valleys, noise marginal, ridge probe, IS/referee outcomes where
gated in), written and hashed per section 6.5 before any BMS\* output under that
arm. Arms may be dropped here only for documented elicitation defects or
computational infeasibility, never for how any downstream model ranking looks.

### Stage B — sampler strategies as experiment-local configuration

**Enabler E1, built first (M2b), gated before use**: a direct-parameter potential
— the unconstrained log joint assembled from gpytorch raw parameters, analytic
prior log-probs, and constraint Jacobians (D13's `_raw_log_jacobian` pattern),
exposed as a pyro `potential_fn` exactly as `fit_hmc_laplace` already does.
Motivation: the measured ~200x per-leapfrog advantage over the deep-copy path.
Equivalence gates before any science use (battery enumerated in section 6.15;
tolerances and point-generation distributions frozen at M2b): agreement with the
pyro potential to an additive constant and gradient agreement over frozen point
sets that include MAP neighborhoods, prior draws, tail/boundary stress points
(near-zero noise, Interval boundaries, near-singular kernels), and invalid-SPD
cases; likelihood and prior/Jacobian contributions tested separately; directional
Hessians; transformed draw round-trips; site ordering; posterior-predictive
equality; plus the estimator-specific toy goldens (G-toy). E1 failing its budget
is documented and the pyro path stays the vehicle at sub-150 (risk R2).

Strategies (every one gets a bounded pilot with a pre-registered budget; none —
including MAP+Laplace — is primary beforehand; A11):

- **S1 adapted baseline**: current `fit_hmc` (MAP-init, td7, pyro path).
- **S1f adapted baseline on E1**: statistically identical target, cheap leapfrogs.
- **S2 fixed MAP-Hessian inverse mass, adaptation off** (D8 option a): implemented
  on E1 via whitened coordinates or a fixed mass matrix. `fit_hmc_laplace` only
  approximates this (it still adapts within z-space), so S2 proper disables mass
  adaptation; the mass convention gets its own M2c tests.
- **S3 reparameterized prototype (concrete, no contingency status)**: coordinates
  = 3 log-lengthscales; s = log total signal variance log(os_tr + os_se + os_me);
  2 additive-log-ratio coordinates for the variance shares; r = log
  noise-to-signal ratio log(noise/exp(s)). 7 coordinates, bijective to the current
  7. Rationale from recorded geometry: the D8 ridge couples trend amplitude and
  lengthscale, so shares + total decouple amplitude trade-offs, and r targets the
  near-zero-noise funnel — a hypothesis the pilot tests, not a claim. The
  transformation is only complete with its Jacobian log-determinant (codex round
  1; exactly the D13 class of error): the forward/inverse map and the analytic or
  autodiff log-det term are part of the S3 definition, and S3 is gated on density
  and gradient equivalence to E1 over interior and near-boundary points (M2c).
  Pilot success criterion beyond validity, numbers frozen (round 5): over the
  pooled validity-passing sub-150 pilot draws on the same arm, |corr(trend ls,
  trend os)| under S3 must be at least 0.1 (absolute) below the S1f value, OR
  the condition number of the pooled pilot-draw covariance (each sampler in its
  own working coordinates) must improve by at least 2x — shares/total do not
  automatically remove the cited ridge, so the improvement is measured, not
  assumed. Vehicle: E1. Budget: A6. A build failure within budget is the
  documented pilot outcome (W6 addendum).
- **S4 MAP+Laplace**: a strategy like the others (A11). Requires a genuine
  GP-hyperparameter Laplace approximation built at M2c — `fit_hmc_laplace` is
  whitened NUTS, not a Laplace approximation, and `laplace_evidence.py` concerns
  candidate-model evidence, not GP-hyperparameter draws (codex round 1). Validity
  analog: the standardized MAP plus Laplace adequacy against the Stage-A
  sampler-independent geometry (profile-marginal and mode-inventory agreement).

Pilot design per strategy: 4 chains x (200 warmup + 200 draws), seeds 0/1/2/3,
td7 unless the strategy specifies otherwise, sub-150 first. Pilot order: ascending
cost (S4, then S1f/S2/S3 on E1, S1 pyro-path last).

**Toy smoke-validation (G-toy) before any Mauna hours**: estimator-specific
goldens per section 6.9 — a coverage-repairing sampler is NOT required to
reproduce the confined 0.696.

**Gate G-B (per strategy x scale):** the validity criteria of section 6.7
(convergence, ESS, divergences, depth saturation, coverage per the two-reference
arbitration, seed reproducibility, interpretability, feasibility). Survivors earn
runs at the paper-target scale (A5: full N=461 unless the pre-registered fallback
fires). Sequential stop rules per section 6.10 — keyed only on geometry, adequacy,
and budget, never on BMS\* output.

### Stage C — BMS\* + mass-faithful arm; report; the D19 author decision

- BMS\* on the surviving arm x strategy combinations over the ratified candidate
  sets (A4, section 3), primary metric `pw_kl_vcal` (W1) at the tau grid
  0.1/0.3/1/3/10 (headline tau = 1, matching the toy convention), with the
  existing Mauna metrics plus `kl_forward` as appendix sensitivity.
- BMS\* seed-stability (agreement of probabilities across seed-disjoint chain
  halves) is computed and reported HERE, as a reporting-only diagnostic (round
  5): it never gates a run or a scale and never feeds any selection — the G-B
  reproducibility gate is target-level only (6.7).
- Mass-faithful arm (A8: required to attempt): SIR through the BMS\* pipeline from
  whichever particle-producing estimator passed G-IS; two-layer uncertainty
  reporting per W5 (conditional bootstrap SE beside independent-pool variability,
  never combined into one bar).
- Predictive adequacy: within-span interpolation checks separated from the
  60-month holdout, which stays SEALED until after the D19 decision (section 6.6)
  and is then scored once as the labeled extrapolation/forecast check (W6).
- The scalability artifact (template in section 11) ships with the results
  milestone.
- The D19 author decision is taken under the selection firewall (section 6.11)
  with the default-selection rules (section 6.12), then recorded in
  `Notes/DECISIONS.md` with the disclosure set.

Candidate figure forms (predefined only; no headline chosen): F1 component
decomposition (trend/seasonal/medium with bands) per surviving path; F2 data-level
prior beliefs transferring into model-level probabilities — per-arm BMS\*
posterior bars under the surviving inference path (the brief's
main-applied-result form); F3 sensitivity small multiples, BMS\* posterior vs tau
across arms and strategies; F4 geometry appendix, noise marginal (profile-Laplace
vs IS vs chain occupancy) and ridge slice per arm (D18 Figure-B pattern); F5 the
scaling table rendered. Sampler and prior tradeoffs go to sensitivity panels, an
appendix, and the discussion; the evidence picks the final presentation.

## 3. Candidate-set matrix and harmonization rule (A4)

|  | Main universe: 4-ladder | Appendix universe: harmonized 3-set |
|---|---|---|
| Source | `bistar_gp/mauna_loa_candidates.py::build_mauna_loa_candidates` | `experiments/bms_star_mauna_loa.py::build_mauna_loa_candidates`, harmonized at M2a |
| Members | Linear; Quadratic; Quad+Sin (annual harmonic); Quad+2Harm (annual + semi-annual) | Linear+2Harm; Quadratic+2Harm (shared member); Exponential+2Harm |
| Role | primary BMS\* universe (continuity with the impact-assessment headline, Quad+2Harm 0.42218 vs Linear 0.11368 at pw_kl_forward tau=1, D11-rechecked) | trend-law contrast only (Linear vs Quadratic vs Exponential growth) |
| Optimizer | D11 multi-start full-NLL protocol | the same shared protocol (replaces `differential_evolution`) |
| Seasonal period | fixed at 1.0 by construction | FROZEN at 1.0 (currently a trainable P in (0.9, 1.1)) |
| Normalization | over its own universe | over its own universe — ALWAYS separate; the two universes are never merged into one normalization |
| Cross-universe check | — | code-level identity test on the shared member: harmonized Quadratic+2Harm must reproduce the ladder's Quad+2Harm fitted parameters and NLL |

Harmonization rule (codex round 3): with the period frozen at 1.0 and the shared
D11 multi-start protocol, the 3-set's Quadratic+Seasonal coincides exactly with
the ladder's Quad+2Harm, so the cross-universe consistency check reduces to a
code-level identity test and the appendix carries purely the trend-law contrast.

## 4. Milestone map

- **M1 (this commit)** — documentation-first freeze: this plan, pre-registration
  v1.0, decision record A1-A11, scorecard + benchmark artifacts, D19 entry.
  Reviewed before any M2a work.
- **M2a — infrastructure PR (arm-independent)**: data-provenance gate + loader
  hardening (A9: canonical year/month/co2 hash, runtime verification or vendored
  checksummed dataset, fallback/filter defects fixed); period freeze + assertion
  (A10); candidate-set registry with the harmonized 3-set and the shared-member
  identity test (A4); `pw_kl_vcal` wiring + tau grid; diagnostic-retaining sampler
  result schema (divergences, tree-depth, acceptance — `fit_hmc` currently
  discards the MCMC object); a training-only loader path so the 6.6 holdout seal
  is mechanical rather than conventional (round 5); slurm refresh.
- **M2b — E1 (arm-independent)**: direct-parameter potential + the frozen
  equivalence battery (tolerances and point sets fixed here, before any pilot
  result is read); the real E1 NUTS microbenchmark; the Della re-benchmark (A7);
  A6 budgets finalized as a pre-registration addendum, and the A5
  subsample-fallback design + infeasibility predicate frozen in the same
  addendum (round 5).
- **M2c — strategies + M1 (arm-independent)**: S2 (mass convention + tests), S3
  (map + Jacobian log-det + equivalence tests), S4 (genuine GP-hyperparameter
  Laplace sampler), M1 model construction + its prior tests (normalization
  quadrature, sampling check, target equivalence), estimator-specific toy goldens
  with frozen tolerances (G-toy), and the corrected normalized profile band-mass
  computation with the recomputed D18 reference values (6.9 caution; round 5).
- **M2d — arms + orchestration (needs G0)**: attribution arms as experiment-local
  configuration; orchestration + dossier/hashing mechanics (section 6.5);
  consolidation of every numeric addendum into the pre-registration record; G0
  sign-off including the era-transcription outcome (section 8).
- **M3 — pilot evidence**: toy smoke (G-toy) + sub-150 Stage-A screening +
  Stage-B pilots; committed JSONs/tables, D18 style.
- **M4 — expensive runs**: full-N Stage A for surviving arms; paper-target-scale
  runs for G-B survivors; Della only after its benchmark.
- **M5 — results + decision**: Stage C, scalability artifact, report, the D19
  author decision + DECISIONS.md Status closure + writeup entries.

## 5. Risk register (severity-ranked)

Likelihood labels below are engineering-feasibility assessments, permitted under
the outcome-prediction ban as narrowed in section 6.13 (the ban covers scientific
results: which arm, strategy, or candidate model wins).

1. **R1 — no sampling strategy converges at the paper-target scale** (high
   impact; moderate likelihood given the D8/D18 confinement history). Mitigation:
   pre-registered outcome O4 — MAP+Laplace (S4) carries the decomposition figures
   with the W6 disclosure language; joint-posterior claims rescoped. Named in
   advance, not a surprise ending.
2. **R2 — E1 direct potential is subtly wrong** (high impact: silently wrong
   target; low-moderate likelihood: prior-convention and Jacobian mismatches are
   exactly the D6/D13 class). Mitigation: the M2b equivalence battery + G-toy
   before any use; E1 failure documented, pyro path retained at sub-150.
3. **R3 — selection leakage** (high impact, insidious). Mitigation: the firewall
   (6.11), the ordering/blinding rule (6.5), stop rules keyed only on
   geometry/adequacy/budget (6.10), and the frozen arm order (6.4).
4. **R4 — prior-IS ESS collapse in 7 dimensions on real data** (moderate-high
   likelihood; cost is measured cheap, so the gate is statistical, not
   computational). Mitigation: G-IS with per-band floors (6.7), the fallback
   ladder, bridge sampling as evidence diagnostic only; if nothing passes, outcome
   O5 reports the mass-faithful arm infeasible rather than substituting a
   confined chain.
5. **R5 — additive-component identifiability** (moderate). Measured hint: trend
   ls 4.41 y vs medium ls 3.34 y at the 300-iter MAP. M1 adds imitation risk by
   design. Mitigation: G-A proximity assessment, the quantitative M1 pre-check
   gates (6.7), decomposition-stability check in Stage C.
6. **R6 — Della thread-thrash/timeout repeats** (moderate). Mitigation: re-run
   `experiments/d19_bench.py` on Della first (A7); pin threads; wall-clock caps
   with checkpointing; assign only embarrassingly parallel work.
7. **R7 — sub-150 conclusions fail to transfer to full N** (moderate; the noise
   MAP already shifts 0.00172 to 0.00193 across scales). Mitigation: sub-150
   labeled screening-only everywhere; every survivor re-validated at the
   paper-target scale.
8. **R8 — data-provenance drift** (low-moderate): no runtime checksum, dead
   fallback, no-op filter, co2-only hash. Mitigation: A9 at M2a; the prereg data
   pin (6.2) re-pins on any deviation.
9. **R9 — repo inconsistencies bite at M2** (low): stale slurm flags, two
   candidate sets, missing `pw_kl_vcal`, `fit_hmc` discarding diagnostics,
   `fit_hmc_laplace` not being a Laplace approximation. Mitigation: named M2a-M2c
   items with tests.
10. **R10 — Hessian consumers read an under-converged MAP** (low-moderate; the
    benchmark itself used the 300-iter convention). Mitigation: standardized MAP
    protocol (multi-start, 800 iters, convergence check) upstream of every Hessian
    use (E1 whitening, S2 mass, S4, profile-Laplace).
11. **R11 — seasonal-lengthscale unit slip** (low): periodic ls is in phase
    units. Mitigation: explicit unit note wherever those values appear.
12. **R12 — depth-cap misread as stationarity evidence** (low): td7 stays
    disclosed as an efficiency control (D8), never as convergence evidence.
13. **R13 — era transcription contradicts the 0.2 ppm interpretation**
    (low-moderate; codex round 4). Mitigation: the amendment rule of section 8 —
    a documented pre-registration amendment or a new named arm BEFORE Stage A.

## 6. Pre-registration v1.0 (FROZEN at this commit)

### 6.1 Scope and standard

Mauna Loa serves the paper as an applied scalability demonstration, not a
definitive domain model of atmospheric CO2 (W6). Elicitation uses basic, legible
domain information with sourced quantitative claims; transparent and reasonable is
the standard. Near-zero fitted noise under the corrected code is described as
"likelihood-favored under the current GP specification," never simply
"data-driven." Whether the prior influences the lengthscale geometry is an open
question this study measures; the D6-corrected causal history stands.

### 6.2 Data

OpenML 41187 (fetched version 1), sha256 of the co2 column
`7e301efd6dbd2b4007723368aa69ebd2259ea6aa1d431650c209df181f244cb9` (extended to a
canonical year/month/co2 hash at M2a per A9); filter co2 > 0; monthly-mean
aggregation; train/test cutoff max(x) - 5.0 y; counts 2225 raw / 521 monthly /
461 train / 60 test. Any deviation re-pins before use.

### 6.3 Model space

M0: trend RBF + fixed-period periodic + medium RBF + Gaussian nugget; 7 active
sites once A10's period freeze lands (the pre-freeze plug-in history is standing
disclosure 4). M1: M0 + constrained short-scale Matern-3/2 (A3), a pilot option
only, with the nugget anchored per A1 and 9 active sites. Diagnostics always run
over the active-site inventory of the model in use (7 vs 9).

### 6.4 Arms: roles and frozen order

| Arm | Definition (section 7 tables) | Role |
|---|---|---|
| P0 | baseline kernel + baseline noise | control/continuity baseline; fallback if no revised arm passes |
| P-noise | baseline kernel + elicited noise | attribution arm (noise block) |
| P-kernel-v1 | elicited kernel + baseline noise | attribution arm (kernel block) |
| P-comb-v1 | elicited kernel + elicited noise | FIRST REVISED ARM; adoption candidate |
| P-comb+M1-v1 | P-comb-v1 prior on the M1 model space | adoption candidate, conditional on the M1 gates |
| \*-v1b | trend-os variant LN(log 2.5, 1.0) | examined-and-rejected (section 9.6); never run downstream |

Frozen order for all staged compute: P0, P-comb-v1, P-comb+M1-v1, P-kernel-v1,
P-noise. The first revised arm is P-comb-v1, fixed here before any BMS\* output
exists. Adoption candidates (P-comb-v1, P-comb+M1-v1, with P0 as fallback) that
pass G-A MUST all run at the paper-target scale before any prior selection.
Attribution arms are not selection-eligible; they run Stage A always, and Stage
B/C only as budget permits (in the frozen order), labeled sensitivity evidence.
Budget reservation (round 5): before any attribution arm consumes Stage-B/C
budget, the remaining approved budget must cover P0 and every G-A-passing
adoption candidate at the paper-target scale (enforcement in 6.10).

### 6.5 Ordering/blinding rule (leakage control)

Per arm: the Stage-0 scorecard verdict and the Stage-A adequacy verdict are
computed and written into that arm's dossier BEFORE any BMS\* model probability
under that arm is computed. At the moment an arm's Stage-A dossier is complete,
its sha256 is recorded in the study log, and the dossier is committed no later
than the next milestone commit — both before Stage-C unblinding for that arm.
BMS\* outputs never feed back into arm definitions; a revision made after seeing
any BMS\* output starts a new, labeled arm (P-comb-v2, ...) with its own dossier.

### 6.6 Holdout seal

The 60 test months stay SEALED until the D19 author decision is recorded in
`Notes/DECISIONS.md`. Seal semantics, stated precisely (round 5): no Stage
0/A/B/C analysis, plot, score, persisted artifact, or selection input may use
test VALUES. Predefined split METADATA (the cutoff rule, the counts 461/60) and
the legacy loader's mechanical materialization of the split are permitted — the
current `load_mauna_loa` constructs and returns `x_test/y_test` unconditionally,
so "never loaded" would be false as a literal claim; the planning scripts bound
`_xte/_yte` unused (scorecard) and recorded only the test count (benchmark
provenance). M2a adds a training-only loader path so the seal becomes mechanical
rather than conventional. Every predictive-adequacy check used for prior or
sampler selection runs on the 461 training months only — training-span
interpolation splits or rolling-origin splits within the training span, with
refits at MAP or S4 level only (never a full sampler rerun per fold). After the
D19 decision the holdout is scored once and labeled an extrapolation/forecast
check (W6 separation).

### 6.7 Gates, with every currently definable number

- **G0 (author, M2d):** section Stage 0. Includes the era-transcription outcome
  (section 8).
- **G-IS (per estimator x arm):** a 60k-draw pilot proceeds to full pools only if
  pooled ESS >= 100 (D18 floor). Full evidence = 3 independent pools of 600k
  (distinct seeds); requirements: per-band ESS >= 100 in every reportable band
  (bands defined in 6.8; reportable = holding >= 5% of the reference marginal's
  mass, the D18 rule); pool-to-pool agreement on band masses and on each BMS\*
  probability within 2 pooled SEs; proposal-tail diagnostics reported (max
  normalized weight, tail index). Fallback ladder on failure: defensive mixture,
  Laplace-guided IS, SMC — each behind the same gate. Bridge sampling never
  produces particles; evidence diagnostic only.
- **G-referee:** the RW-MH referee reports only if its pilot shows >= 10 lo/hi
  crossings of the reference band boundaries per 30k chain (D18 measured 38-44)
  and acceptance within [0.1, 0.6]; otherwise "referee infeasible" is recorded.
- **G-A (per arm):** geometry dossier complete + hashed (6.5). Drop reasons
  limited to documented elicitation defects or computational infeasibility. M1
  pre-check (P-comb+M1-v1 only), all failures blocking:
  - bound occupancy: <= 5% of M1-lengthscale mass within 5% relative distance of
    either bound of [0.1, 1.0] y, measured on the mass-bearing authority of 6.8
    (a G-IS-passing IS estimator first, else the crossing-verified referee, else
    the normalized profile marginal; the authority used is recorded in the
    dossier before the verdict — round 5);
  - duplication: |posterior correlation| <= 0.95 between the M1 outputscale and
    every other component outputscale, and between the M1 lengthscale and the
    medium lengthscale, computed over the same authority's (weighted) draws;
    no new Hessian eigenvalue below 1e-3 at the standardized MAP (measured M0
    floor: 0.069-0.075);
  - geometry non-worsening: M1 Hessian condition number <= 10x the same-arm M0
    value at the standardized MAP;
  - nugget-floor diagnostic: report whether M1's advantage coincides with nugget
    posterior mass pushed below the instrument-only reference 1.9e-4 normalized
    (A1); the formal predicate is implementation-coupled (6.15, M2c);
  - predictive improvement: M1 must improve rolling-origin training-span pw_nll
    over same-arm M0 by more than 2 fold-SEs. Protocol frozen (round 5): 9
    origins at training months 240, 264, ..., 432 (24-month spacing), horizon 12
    months, refit at MAP/S4 level per fold (6.6); per-fold statistic = mean
    pw_nll over the 12 predicted months; comparison statistic = mean of the 9
    per-fold differences; fold-SE = sd of those 9 differences / 3. The numeric
    content of "clear benefit";
  - spectral/covariance overlap diagnostic: enumerated, form fixed at M2c (6.15).
- **G-toy (per strategy):** estimator-specific goldens per 6.9, at pinned seeds,
  within tolerances frozen at M2c.
- **G-B (per strategy x scale):** rank-normalized split-Rhat <= 1.05 on all
  active sites across 4 chains; pooled bulk ESS >= 100 AND tail ESS >= 100 per
  site; divergences <= 0.1% and non-clustering (rate frozen now; the clustering
  predicate is implementation-coupled, 6.15); tree-depth saturation < 10%;
  coverage per the two-reference arbitration (6.8); seed reproducibility,
  target-level only (round 5 — no BMS\* output appears in this or any gate): the
  two seed-disjoint chain pairs agree on every active site's posterior mean
  within 2 combined MCSEs (per-half MCSE = sd/sqrt(bulk ESS); combined =
  sqrt(MCSE_1^2 + MCSE_2^2)) AND on band occupancy within 0.05 in every
  reportable band (6.8) — BMS\* seed-stability moves to Stage C as
  reporting-only; draws interpretable: finite and in-support for 100% of scored
  draws, and the decomposition's reconstructed full-model predictive variance
  matches the directly computed one within 1e-8 relative on 10 seeded
  spot-check draws (the D2 cross-term identity); feasibility: measured pilot
  cost extrapolates to the paper-target scale within the approved A6 budget.
  S4's analog, numbers frozen (round 5): standardized MAP, plus Laplace
  adequacy = (i) S4's noise-marginal band masses within 0.10 absolute of the
  corrected-normalization profile quadrature (6.9 caution) in every reportable
  band, and (ii) no non-MAP mode from the Stage-A inventory holding more than
  5% of the mass-bearing authority's mass. If S4 fails its analog, the O4
  fallback is unavailable and O4's degraded sub-case applies (6.13).
- **G-C (mass-faithful arm):** SIR only from an estimator that passed G-IS;
  every reported BMS\* probability carries a functional MCSE (conditional
  bootstrap; weighted for IS/SIR) with floor MCSE <= 0.02 for any
  paper-quoted probability; two-layer uncertainty per W5 (conditional bootstrap
  SE beside independent-pool variability, never combined).

### 6.8 Coverage: two-reference arbitration (codex round 1; D18 pattern)

Band definitions, frozen: for the noise site, three bands split at the 25th and
75th percentiles of that arm's Stage-A profile-Laplace noise marginal (band EDGES
come from the profile marginal, recorded in the dossier before any Stage-B run);
for the trend lengthscale, three bands split at ls = 8 and ls = 32 (the D8
stuck-chain values). Reportable band: holds >= 5% of the MASS-BEARING AUTHORITY's
marginal mass (authority defined next; round 5 — edges are pre-registered
geometry, the authority decides reportability).

Reference roles, frozen (round 5). The mass-bearing authority is the first
available of: (1) an IS-family estimator that passed G-IS (band masses with
delta-method SEs; fails by proposal starvation), then (2) the RW-MH referee that
passed G-referee (pooled over >= 3 seeds; per-band SE proxy = half the
across-seed range; fails by non-crossing). Profile-Laplace quadrature is always
corroborating-only — deterministic and mode-based, biased where the Laplace form
is wrong, computed with the corrected normalized band integration (6.9 caution) —
and never issues a verdict alone. If NO mass-bearing authority exists for an
arm x scale (no IS estimator and no referee passed its gate), coverage is
UNDETERMINED and the strategy cannot pass G-B at that scale; that routes honestly
toward O4 rather than substituting a weaker authority.

Pass criterion, per reportable band: |chain occupancy - authority band mass|
<= 2 sqrt(SE_auth^2 + SE_chain^2), with SE_chain = sqrt(p(1-p)/bulk ESS of the
banded coordinate's site). Corroboration predicate (replaces "agreeing
directionally"; round 5): the corroborating reference (profile quadrature, or
the sampler-based reference not serving as authority) must lie within 3 SE_auth
of the authority in every reportable band; if it does not, run the full D18
three-way arbitration (IS + referee + profile quadrature) and record the
adjudication before any strategy verdict. Any two-estimator comparison
(pool-to-pool in G-IS included) uses combined SEs:
|m_a - m_b| <= 2 sqrt(SE_a^2 + SE_b^2). A profile curve or ridge probe alone
never issues a coverage verdict; mutually agreeing confined chains still fail
(agreement among chains is not coverage evidence).

### 6.9 Estimator-specific toy goldens (G-toy; codex round 1)

Reference: the D18 `toy_elicited` cached artifacts at pinned seeds. Requiring
every strategy to reproduce the confined NUTS number would be statistically
backwards, so the golden depends on what the estimator claims to do:

- **E1/S1f**: no cached-number target — density, gradient, and transform
  equivalence to the S1 pyro target (the M2b battery), plus one S1f toy run whose
  draws pass the same diagnostics as S1's cached run.
- **S1**: reproduce its own cached 0.696-family result (td7) at pinned seeds
  within tolerance, as a regression characterization ONLY — explicitly not a
  validity pass (the chain is known mode-confined; D18).
- **S2/S3**: agreement with the D18 sampler-based noise-marginal references —
  prior-IS pooled band masses 0.763/0.191/0.046 (SEs ±0.004/±0.004/±0.001) and
  the RW-MH referee 0.796-0.843 / 0.140-0.175 / 0.016-0.037 — within
  pre-declared MC error, AND the mass-faithful BMS\* result (Sin+Linear 0.441 at
  tau=1) within pre-declared MC error. A coverage-repairing sampler must
  reproduce the mass-faithful answer, not the confined 0.696. CAUTION (round 5
  review catch): the D18 profile-Laplace quadrature triplet 0.763/0.138/0.023
  sums to 0.924, not 1 — the D18 script's band integrals masked a fixed grid at
  off-grid thresholds and dropped the boundary-straddling intervals, so those
  three numbers are non-exhaustive partial-grid integrals, HISTORICAL ONLY, and
  are NOT a golden. M2c recomputes normalized profile band masses (boundary
  points inserted or straddling intervals split) and freezes the corrected
  values and tolerances as a v1.x addendum before any toy or Mauna pilot; the
  same corrected integration applies to every profile band-mass computation in
  this study (Stage A dossiers, the 6.8 corroborator, S4 adequacy). The
  numerical fix itself is M2 work, not part of this documentation commit.
- **S4**: its Laplace marginal/moment approximation compared against the profile
  quadrature and IS references on the toy — no single cached headline is its
  target.
- **SIR/IS estimators**: reproduce the D18 SIR 0.441-family numbers at pinned
  seeds within bootstrap MC error.

Numeric tolerances: implementation-coupled, frozen at M2c before any Mauna pilot
result is read (6.15).

### 6.10 Sequential stop rules (keyed only on geometry, adequacy, and budget)

- Pilots run in ascending cost order (S4, S1f, S2, S3, S1); a strategy failing
  validity at sub-150 does not proceed to any larger scale.
- Arms run in the frozen order (6.4). An arm stops only at G-A (elicitation
  defect / computational infeasibility) or on pre-approved budget exhaustion.
  Budget reservation (round 5): before any attribution arm consumes Stage-B/C
  budget, the remaining approved budget must cover P0 and every G-A-passing
  adoption candidate at the paper-target scale, so a budget truncation may cut
  only attribution arms (reported as not-run; budget-driven and
  firewall-clean). If, despite the reservation, any G-A-passing adoption
  candidate ends unmeasured at the paper-target scale, NO final prior selection
  occurs: the baseline P0 remains by default and the report discloses the
  unmeasured candidate.
- No stop, expansion, or ordering decision reads any BMS\* output (the earlier
  draft's "top-model shift > 0.05 triggers more arms" rule is DELETED — codex
  round 1). If the author ever requests a BMS-motivated extra run, it is labeled
  exploratory and its results are barred from selecting the final prior.
- Adoption candidates passing G-A always run to the paper-target scale (6.4);
  there is no early stop that would leave a selection-eligible arm unmeasured
  while selection proceeds.

### 6.11 Selection firewall

- The final prior cannot be selected because it produces a preferred
  candidate-model ranking. Its criteria: elicitation defensibility, prior and
  posterior predictive adequacy, robustness (stability of predictive adequacy and
  geometry across arms — not ranking agreement), and thesis alignment (W5
  terminology where data-elicited).
- The sampler cannot be selected on the attractiveness of its BMS\* result. Its
  criteria: target accuracy against the sampler-independent references,
  convergence, coverage (6.8), reproducibility, and cost — performance first,
  runtime second. Numeric content of "major speed advantage" (round 5): among
  strategies that pass every validity and coverage gate, a faster method may
  displace the nominally best one only when its cost per effective draw is at
  least 5x lower; a fast chain confined against the Stage-A marginals never
  qualifies.

### 6.12 Default-selection rules (tie-breakers, in order)

Sampler: (1) best coverage evidence among validity-passing strategies at the
paper-target scale — ordinal score frozen (round 5): more reportable bands
within 1 combined SE of the authority wins; ties broken by the smaller maximum
band deviation measured in combined-SE units; (2) lowest cost per effective
draw; (3) smallest implementation surface. If none passes at the paper-target
scale, MAP+Laplace (S4) carries the decomposition figures with the W6
disclosure (outcome O4) — provided S4 passes its own adequacy analog (6.7);
otherwise O4's degraded sub-case applies (6.13).

Prior: "passing all prior criteria" is operational (round 5): (i) Stage-0
scorecard — every row inside the central 95% interval (9.2); (ii) training-span
posterior predictive adequacy — the arm's rolling-origin mean pw_nll (protocol
per 6.7) not worse than P0's by more than 2 fold-SEs; (iii) robustness — the
arm's Stage-A dossier shows no new pathology absent under P0 (no new mode
holding more than 5% of authority mass, no new Hessian eigenvalue below 1e-3,
condition number no more than 10x P0's); (iv) the W5 disclosure checklist
complete. Among passing arms, prefer the one with the fewest data-elicited
inputs; if no revised arm passes, the baseline remains and the report states
why revision failed (outcome O3).

### 6.13 Outcome patterns O1-O5

Recorded so surprise is detectable; none is predicted or preferred; they may
co-occur. The no-outcome-predictions rule covers scientific results (which arm,
strategy, or candidate model wins); engineering-feasibility likelihoods in the
risk register are permitted and labeled as such (codex round 1).

- **O1**: revised arms pass adequacy and the geometry differs materially from P0.
  Sensitivity panels quantify the prior influence; F2 uses the ratified arm.
- **O2**: revised arms pass and the geometry is materially unchanged; robustness
  reported.
- **O3**: no revised arm passes; the baseline stays with the scale-tension
  disclosure and the report documents why revision failed.
- **O4**: no sampling strategy passes at the paper-target scale; MAP+Laplace
  carries the figures; joint-posterior claims rescoped per W6. Degraded
  sub-case (round 5): if S4 also fails its adequacy analog (6.7), no adequate
  posterior approximation exists either — the paper then reports MAP point
  estimates only, with the W6 disclosure extended to say exactly that.
- **O5**: no particle-producing estimator passes G-IS; the mass-faithful arm is
  reported infeasible; evidence diagnostics only. (A8: the attempt is required,
  the delivery is not.)

### 6.14 Standing disclosures

1. td7 is an efficiency control (D8), never convergence evidence.
2. Near-zero fitted noise: "likelihood-favored under the current GP
   specification," never "data-driven."
3. W5 data-elicited terminology end-to-end for every arm built from realized-data
   summaries — including the y_std^2 = 212.68 ppm^2 variance scaling, the
   y_std = 14.583 ppm amplitude scaling, the x centering at 1977.711, and any
   further realized summary an arm uses; "posterior-mass-faithful under the fixed
   data-elicited prior" where applicable.
4. Plug-in period history: pre-D19 analyses were conditional on a data-fitted
   plug-in period near 0.9996 (trainable under Interval(0.99, 1.01)); frozen at
   exactly 1.0 from M2a (A10).
5. sub-150 evidence is screening-only.
6. Corrected D6 causal history: the old Mauna chain tracked the Gamma prior
   because of the disconnected-prior sampling bug, not because the prior sculpted
   the posterior; prior influence on the lengthscale geometry is an open question
   this study measures.
7. The stationary zero-mean trend prior assigns equal probability to rising and
   falling trajectories; the scorecard evaluates magnitude only (its statistics
   are absolute changes). A direction-informed mean function is a disclosed
   non-goal for M0/M1.
8. Textbook Mauna Loa facts are data-adjacent (statistics of the same record) and
   join the disclosure list wherever used.
9. No outcome predictions about scientific results anywhere in study documents
   (scope per 6.13).
10. Era-dependent noise is a disclosed limitation, out of scope: one nugget band
    absorbs era heterogeneity (A1).

### 6.15 Threshold inventory

Frozen now (this document): every number in 6.7-6.12 — Rhat 1.05; bulk and tail
ESS 100; divergence rate 0.1%; depth saturation 10%; seed reproducibility
(target-level): per-site posterior means within 2 combined MCSEs AND band
occupancy within 0.05 per reportable band; per-band ESS 100; reportable-band
mass 5% on the mass-bearing authority; authority precedence (G-IS-passing IS,
then G-referee-passing RW-MH; profile corroborating-only); pools 3 x 600k; any
two-estimator agreement 2 combined SEs, sqrt(SE_a^2 + SE_b^2); IS pilot 60k at
pooled ESS 100; referee crossings >= 10 and acceptance [0.1, 0.6]; coverage
2 sqrt(SE_auth^2 + SE_chain^2) per reportable band with SE_chain =
sqrt(p(1-p)/bulk ESS); corroboration 3 SE_auth; coverage ordinal score (bands
within 1 combined SE, then smallest maximum deviation); band splits (noise:
25th/75th percentiles of the Stage-A profile marginal; trend ls: 8 and 32);
MCSE floor 0.02; M1 bound occupancy 5% at 5% relative distance; duplication
|corr| 0.95; Hessian eigenvalue floor 1e-3; condition-number factor 10;
predictive improvement 2 fold-SEs under the frozen rolling-origin protocol
(9 origins at months 240, 264, ..., 432; horizon 12; MAP/S4 refits; fold-SE =
sd/3); S3 improvement (|corr(trend ls, trend os)| lower by >= 0.1, or pilot-draw
covariance condition number >= 2x better); S4 adequacy (band masses within 0.10
of the corrected profile quadrature; non-MAP-mode cap 5%); speed-advantage
factor 5x on cost per effective draw; decomposition identity 1e-8 relative on
10 seeded spot-check draws; pilot shape 4 chains x (200+200), seeds 0/1/2/3;
tau grid 0.1/0.3/1/3/10 with headline tau 1; ridge probe 20 points over
[8, 32]; profile grid 40 points; scorecard seeds and rule (section 9).

Enumerated now, numeric value fixed in M2a-M2c BEFORE any pilot result is read
(each lands as a tracked pre-registration addendum):

| Predicate | Fixed at |
|---|---|
| E1 equivalence tolerances + frozen point-generation distributions (MAP neighborhoods, prior draws, tail/boundary, invalid-SPD; separate likelihood vs prior/Jacobian; directional Hessians; round-trips; site ordering; posterior-predictive equality) | M2b |
| S2 mass-convention test tolerances | M2c |
| S3 Jacobian log-det + equivalence tolerances, interior and near-boundary point sets | M2c |
| G-toy per-estimator numeric tolerances | M2c |
| Divergence non-clustering predicate (needs the M2a diagnostic schema) | M2c |
| Spectral/covariance overlap diagnostic (exact form) for the M1 duplication gate | M2c |
| M1 nugget-floor formal predicate (reference value 1.9e-4 fixed now) | M2c |
| A6 pilot budgets finalized (provisional numbers in section 7) | M2b |
| Della thread-pinning numbers | M2b (after its benchmark) |
| A5 subsample-fallback: design rule, exact N, and the infeasibility predicate (trigger may cite only engineering feasibility/budget evidence — never adequacy or BMS\* outcomes; frozen before M3 or any fallback-scale result; round 5) | M2b |
| Corrected normalized profile-Laplace band masses for the D18 toy reference, plus the corrected integration applied to every profile band-mass computation (6.9 caution; round 5) | M2c |

### 6.16 Amendment protocol

This pre-registration is v1.0, frozen at this commit. Amendments are append-only,
numbered v1.1, v1.2, ..., each dated and reasoned, landing in tracked commits
BEFORE the stage they affect. The era-transcription amendment, if fired, lands
before Stage A (section 8). The implementation-coupled numeric addenda (6.15)
land at M2a-M2c, before any pilot result is read. Nothing in this document is
edited in place after this commit; corrections happen as amendments. (The round-5
freeze-commit review ran before this commit finalized, so its fixes are part of
v1.0 itself, not amendments.)

## 7. Decision record A1-A11 (author, 2026-07-10)

- **A1 — nugget semantics: RATIFIED.** The nugget represents measurement error
  plus uncorrelated monthly-aggregation/residual variance; correlated short-term
  discrepancy belongs to M1's Matern-3/2 component. The elicited nugget prior's
  10-90% sd band (0.16-0.57 ppm) deliberately brackets the 0.2 ppm modern-system
  reference and absorbs era heterogeneity (era-dependent noise: disclosed
  limitation, out of scope). M1 must not win by forcing the nugget below its
  stated observation model (G-A diagnostic; instrument-only reference 1.9e-4
  normalized).
- **A2 — arm prior parameters: v1 RATIFIED** (codex round 4). Tables below are
  the frozen definitions (identical to `experiments/d19_prior_scorecard.py`).
  Rationale: intentionally weakly informative — direction and magnitude of the
  trend are left to the data; the training trajectory is plausible without
  inflating the prior range. v1b (trend os LN(log 2.5, 1.0)) was examined and
  REJECTED: introduced solely to chase the realized trend change, it buys only a
  marginal trend-headroom gain (realized-trend percentile 0.896 vs v1's 0.938)
  while inflating the prior total range (q97.5 120 vs 93 ppm); it stays recorded
  with its scorecard (section 9) and is never run downstream.

  Baseline blocks (P0; gpytorch parameterizations — Gamma(shape, rate), LogNormal
  on the log scale; normalized y units, x in years):

  | Site | Prior | Physical translation |
  |---|---|---|
  | trend ls | LogNormal(4.0, 1.0) | median e^4 = 54.6 y (exceeds the 38.75-y span) |
  | trend os | Gamma(4.0, 0.5) | mean 8.0 norm = 1701 ppm^2 |
  | seasonal ls | Gamma(3.0, 2.0) | phase units; q10/50/90 = 0.55/1.34/2.66, i.e. rho(3 mo) 0.04/0.57/0.87, rho(6 mo) 0.001/0.33/0.75 — harmonic-rich to near-sinusoidal (codex round 3: retained WITH this translation; the earlier "not physically legible" claim is withdrawn) |
  | seasonal os | Gamma(3.0, 1.0) | mean 3.0 norm = 638 ppm^2 |
  | medium ls | Gamma(3.0, 1.0) | mean 3.0 y |
  | medium os | Gamma(2.0, 1.0) | mean 2.0 norm = 425 ppm^2 |
  | noise | Gamma(1.75, 1.0) | mean 1.75 norm = 372 ppm^2 |

  Elicited blocks (v1; used by P-kernel-v1 / P-comb-v1 / P-comb+M1-v1 per the arm
  matrix in 6.4):

  | Site | Prior | Physical translation |
  |---|---|---|
  | trend ls | LogNormal(log 30, 1.0) | median 30 y |
  | trend os | LogNormal(log 1.5, 1.0) | median 1.5 norm = 319 ppm^2 (sd 17.9 ppm) |
  | seasonal ls | Gamma(3.0, 2.0) | kept at baseline (translation above) |
  | seasonal os | LogNormal(log 0.025, 1.0) | median amplitude sqrt(2 os) = 3.26 ppm; peak-to-trough 2 sqrt(2 os) = 6.52 ppm (formula per codex round 3) |
  | medium ls | LogNormal(log 4.0, 0.6) | median 4 y |
  | medium os | LogNormal(log 1.2e-3, 1.0) | median sd 0.51 ppm |
  | noise (elicited) | LogNormal(log 4.2e-4, 1.0) | median sd 0.30 ppm; 10-90% band 0.16-0.57 ppm (A1 anchor) |

  M1 additional sites:

  | Site | Prior | Physical translation |
  |---|---|---|
  | M1 os | LogNormal(log 2.4e-4, 1.2) | median sd 0.23 ppm |
  | M1 ls | 0.1 + 0.9 sigmoid(z), z ~ Normal(-1.2528, 1.082) | hard support [0.1, 1.0] y; q10/50/90 = 0.16/0.30/0.58 y |

- **A3 — M1: PILOT IT, with the bounded prior above RATIFIED** (codex round 3).
  The logit-normal construction is proper by definition on the hard Interval
  [0.1, 1.0] y (no truncation constant, no IS bookkeeping, composes with
  transforms — chosen over a truncated LogNormal). Quantiles verified
  0.16/0.299/0.579 y. M2c tests: normalization quadrature, sampling check, target
  equivalence. Promotion gated by the G-A M1 pre-check (6.7).
- **A4 — candidate sets: 4-ladder main + harmonized 3-set appendix** (section 3),
  under separate normalizations always. Metric reaffirmed: `pw_kl_vcal` primary
  (W1), tau grid 0.1/0.3/1/3/10 (headline tau 1), existing Mauna metrics +
  `kl_forward` as appendix sensitivity.
- **A5 — paper-target scale: full N=461 default**, frozen before any pilot is
  read (codex round 1 killed the choose-at-G-B option as adaptive-target). If
  full N proves infeasible under every surviving strategy, the fallback is a
  pre-registered subsample, still blind: its design rule, exact N, and the
  infeasibility predicate are frozen at M2b (after the E1 benchmark, before M3
  or any fallback-scale result — 6.15, round 5); the trigger may cite only
  engineering feasibility and budget evidence, never adequacy or BMS\*
  outcomes; the fallback is validated through all gates at that scale and
  disclosed as the paper target.
- **A6 — pilot budgets: PROVISIONAL until the M2b E1 NUTS microbenchmark**
  (the E1 rows of section 1.2 are kernel-cost proxies). Provisional numbers: E1
  2 dev-days + <= 30 min compute; S4 <= 30 min; S1f/S2 <= 2 h each; S3 2
  dev-days + <= 4 h sub-150; S1 pyro-path sub-150 only, <= 6 h; Stage A per arm
  <= 1.5 h core + gated IS pools; toy smoke <= 30 min per strategy. Final numbers
  land as the M2b addendum (6.15).
- **A7 — Della: APPROVED, gated on the mandatory re-benchmark**
  (`experiments/d19_bench.py` on Della, threads pinned, before any assignment);
  embarrassingly parallel work only (section 1.3).
- **A8 — mass-faithful arm: REQUIRED TO ATTEMPT, optional to deliver.** The
  particle-estimator ladder must be piloted through G-IS; if every estimator
  fails, O5 reports infeasibility. A confined chain is never substituted.
- **A9 — loader/provenance: vendor a checksummed dataset + runtime verification
  if licensing permits, else deterministic retrieval + checksum verification at
  load.** Canonical hash covers year/month/co2. The document-only option is
  REMOVED (codex round 1: the pre-registration promises hard data identity).
  Loader defects (section 0) fixed at M2a.
- **A10 — seasonal period: FROZEN at exactly 1.0.** `requires_grad_(False)` +
  an assertion that it remains 1.0 through every MAP/multi-start path (M2a), with
  the standing disclosure that pre-D19 runs used a drifting plug-in (~0.9996).
  Giving it a prior (an 8th site) was rejected: it changes the sampled-site
  inventory everywhere downstream for no identified scientific need; revisit only
  if Stage A shows seasonal-component misfit (that revisit would be a prereg
  amendment).
- **A11 — W6 precedence: the PROVISIONAL W6 brief governs.** No inference
  method — including MAP+Laplace — is primary before pilots; S4 competes as a
  strategy like the others. The second W6 entry's computation-tree step 1
  ("MAP+Laplace for the first paper draft") is superseded for this study; its
  substance survives only as the O4 fallback. Frozen before M2.

## 8. Source status and the era-transcription amendment rule

- **Data pin**: OpenML 41187 v1, sha256 (co2 column) `7e301efd...44cb9`, counts
  2225/521/461/60 — verified this session (section 0; full hash in 6.2).
- **Sources identified for the nugget memo**: Thoning et al. 1989 (JGR 94:8549,
  monthly-mean scatter), Komhyr et al. 1989 (instrument/calibration), NOAA GML
  measurement-system pages (modern 0.2 ppm description). Confirmed to exist;
  quantitative claims will cite them.
- **OPEN — era/source transcription** (the one remaining Stage-0 item): pin which
  instrument/program eras the OpenML record's 2225 weekly rows (station column,
  1958-2001) actually cover, and separate analyzer accuracy from
  weather/aggregation variability in the cited numbers.
- **Amendment rule (codex round 4)**: the source pin CAN move things. If the era
  verification materially contradicts the 0.2 ppm lower-reference interpretation
  used by A1/A2, the response is a documented pre-registration amendment (v1.x)
  or a new named arm, BEFORE Stage A compute begins. Silent reinterpretation is
  not an option.

## 9. Stage-0 prior-predictive scorecard v2 (frozen record)

### 9.1 Script, seeds, determinism

`experiments/d19_prior_scorecard.py`; training months only — the legacy loader
materializes the test split mechanically, but the script binds `_xte/_yte`
unused and no test value is ever read (the 6.6 seal semantics apply). Per arm k
(insertion order 0-7):
sampling stream `default_rng([k, 20260710])`, bootstrap stream
`default_rng([k, 77])`; 2000 draws/arm, B=1000 bootstrap. Output
`runs/d19_planning/scorecard_v2.json`. Verified this session: the ported script
regenerates the planning-session JSON byte-identically.

### 9.2 Acceptance rule (declared in v1, before any scorecard computation)

Adoption candidates must place every realized reference inside the central 95%
interval; attribution arms are judged on the rows their revised block governs. A
row passes WITH CONFIDENCE if the bootstrap 95% CI of the realized percentile
stays inside (0.025, 0.975).

### 9.3 Functionals and realized references (corrected, v2; codex round 3)

Each functional applies IDENTICALLY to the realized training series and to every
simulated draw: trend change = |difference of full-calendar-year annual means,
last vs first full year| (1996 vs 1959); decadal change = same at 1969 vs 1959;
seasonal peak-to-trough after within-year linear detrending (shared 12x12
projection); total range; monthly first-difference sd. Realized (ppm): trend
46.59 (1.26 ppm/y over 1959-1996), decadal 8.56, seasonal 4.62, range 51.93,
diff-sd 1.19.

### 9.4 Results (pctile of the realized value in the arm's prior-predictive; bootstrap 95% CI; verdict)

| Arm | trend | decadal | seasonal | range | diff-sd | verdict |
|---|---|---|---|---|---|---|
| P0 | 0.755 [0.737, 0.775] ✓ | 0.242 [0.225, 0.259] ✓ | 0.000 [0.000, 0.000] ✗ | 0.001 [0.000, 0.002] ✗ | 0.000 [0.000, 0.000] ✗ | fails 3 of 5 |
| P-noise | 0.755 [0.736, 0.774] ✓ | 0.246 [0.228, 0.263] ✓ | 0.007 [0.004, 0.012] ✗ | 0.036 [0.028, 0.045] ✓ | 0.002 [0.001, 0.004] ✗ | attribution arm |
| P-kernel-v1 | 0.930 [0.918, 0.942] ✓ | 0.579 [0.556, 0.601] ✓ | 0.000 [0.000, 0.000] ✗ | 0.045 [0.036, 0.055] ✓ | 0.000 [0.000, 0.000] ✗ | attribution arm |
| **P-comb-v1** | 0.938 [0.927, 0.949] ✓ | 0.741 [0.722, 0.760] ✓ | 0.649 [0.628, 0.670] ✓ | 0.875 [0.860, 0.889] ✓ | 0.607 [0.587, 0.629] ✓ | **PASS, all rows confident** |
| **P-comb+M1-v1** | 0.936 [0.926, 0.947] ✓ | 0.743 [0.723, 0.761] ✓ | 0.652 [0.630, 0.674] ✓ | 0.874 [0.859, 0.889] ✓ | 0.605 [0.585, 0.628] ✓ | **PASS, all rows confident** |
| P-kernel-v1b | 0.898 [0.886, 0.911] ✓ | 0.551 [0.528, 0.573] ✓ | 0.001 [0.000, 0.002] ✗ | 0.040 [0.032, 0.049] ✓ | 0.000 [0.000, 0.000] ✗ | rejected variant |
| P-comb-v1b | 0.896 [0.883, 0.910] ✓ | 0.672 [0.651, 0.692] ✓ | 0.663 [0.642, 0.685] ✓ | 0.802 [0.784, 0.820] ✓ | 0.610 [0.587, 0.630] ✓ | passes; rejected per A2 |
| P-comb+M1-v1b | 0.901 [0.887, 0.914] ✓ | 0.680 [0.659, 0.702] ✓ | 0.631 [0.610, 0.652] ✓ | 0.807 [0.790, 0.825] ✓ | 0.578 [0.556, 0.600] ✓ | passes; rejected per A2 |

Stability counts: 2000/2000 finite draws for every arm; zero jitter escalations,
zero Cholesky failures, zero nonfinite components (reported per arm in the JSON;
nothing silently discarded).

Attribution reading: both adoption candidates pass every row with bootstrap
confidence. The baseline's failures quantify the prior-data scale tension (e.g.
P0 prior diff-sd central 95% = 12.1-51.6 ppm against the realized 1.19 ppm), and
no failure is attributable to any revised block — the attribution arms fail only
on rows still governed by a baseline block (P-noise keeps the baseline kernel and
fails seasonal/diff-sd; P-kernel-v1 keeps the baseline noise and fails
seasonal-adjacent rows the huge nugget dominates). The M1 arm's
nugget-vs-short-scale variance share spans 0.06-0.97 (q2.5-q97.5, median 0.62),
so the prior does not pre-decide the nugget/M1 split. Under the corrected v2
functionals P0's trend row passes (0.755; annual-mean deseasonalization isolates
the trend), which sharpens rather than weakens the attribution structure: the
baseline's failures are concentrated where its seasonal/noise scales are
implausible by orders of magnitude.

### 9.5 v1-to-v2 corrections (codex round 3)

v1's statistics mixed trend and seasonal signal (its seasonal peak-to-trough 5.69
carried ~1.1 ppm of trend inflation; v2's within-year-detrended value is 4.62)
and its "stability warnings" were SPURIOUS: BLAS floating-point flags raised by
`matmul` on benign near-singular long-lengthscale draws on arm64, while the
Cholesky itself succeeded. v2 uses correlation-space Cholesky with a relative
jitter ladder [1e-8, 1e-6, 1e-4] and explicit per-component finiteness checks,
and reports every count. The v1 artifacts stay in the planning-session scratchpad
record only; v2 is the frozen reference.

### 9.6 v1b: examined and rejected (kept with its scorecard)

v1b raises the trend outputscale to LogNormal(log 2.5, 1.0) for more endpoint
headroom. It passes all rows (trend 0.896) but was introduced solely to chase the
realized trend change and pays for it by inflating the prior total range (q97.5
120 ppm vs v1's 93 ppm against a realized 51.9 ppm). Under the round-4 wording
correction, note the trend statistic is an absolute change: the prior assigns
equal probability to rising and falling trajectories, and the scorecard evaluates
magnitude only — chasing the signed realized trajectory with a symmetric prior
has no elicitation justification. REJECTED per A2; recorded here per the
examined-and-rejected discipline.

## 10. Benchmark artifacts

`runs/d19_planning/bench_sub.json` and `bench_full.json` hold the raw measured
records behind section 1 (provenance block, sub-150 design check, MAP fits,
potential/gradient/Hessian timings with eigenspectra, prior-eval timings, profile
grid point, single-thread retiming). Timings are machine- and load-dependent —
these JSONs are the frozen planning evidence, not regeneration targets; the
committed `experiments/d19_bench.py` re-runs the same protocol wherever needed
(Della per A7).

## 11. Scalability-artifact template (results milestone; codex round 1 additions)

Header block: hardware (machine, cores, threads pinned, BLAS), software versions
(torch/gpytorch/pyro), dtype and jitter settings, code commit, data pin (OpenML
41187 v1, canonical hash, 461/60), arm and model-space identity (which prior,
M0/M1, candidate universe), sampler knobs (tree depth, step size, mass
convention), seeds.

| Stage / operation | N | Arm | Strategy or estimator | Chains x (warmup+draws) or pool size | Wall-clock | Breakdown (warmup / sampling / post) | Divergences | Depth saturation | Acceptance | Failures/retries | Peak memory | Bulk ESS min-site | Tail ESS min-site | Effective draws or estimator ESS (with uncertainty) | Cost per effective draw | Seeds |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

Required rows: the planning benchmark ops (the measured anchor); Stage-A per-arm
ops; every pilot; every full run; SIR pools. Companion sub-table: sub-N vs full-N
measured cost for every op run at both scales, with the observed ratio beside the
(461/150)^3 = 29.0 cubic reference — the cubic column applies only to operations
dominated by a fixed number of dense GP solves, and is omitted for end-to-end
samplers. One rendered figure or table of this artifact ships in the paper's
appendix (F5).
