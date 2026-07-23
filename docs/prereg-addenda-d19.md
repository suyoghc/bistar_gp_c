# D19 pre-registration addenda (append-only)

Amendment record for the D19 Mauna Loa pre-registration, governed by
`docs/plan-d19-mauna.md` §6.16: the frozen plan (commit a077c6e) is never
edited in place; every prereg-referenced value produced after the M1 freeze
lands here as a numbered, dated, reasoned addendum, in a tracked commit
BEFORE the stage it affects. Later addenda never modify earlier ones.

---

## v1.1 — A9 canonical data hash + vendored artifact (M2a) — 2026-07-11

**Prereg anchor:** §6.2 ("extended to a canonical year/month/co2 hash at M2a
per A9"), §6.15 addendum protocol, decision A9 (§7). Landed with the M2a
infrastructure PR, before any pilot result exists (§6.16 ordering satisfied).

**Licence check (A9 fork):** OpenML dataset 41187 (`mauna-loa-atmospheric-co2`,
version 1) is licensed **CC0** (OpenML API record, checked 2026-07-11;
upstream md5 `fe3355c5e4f3cafc49adc4487806b9a1`). Licensing therefore permits
the vendored-artifact branch of A9, which is the one implemented.

**Vendored artifact:** `bistar_gp/datasets/mauna_loa_co2_openml41187.csv` —
the full 2225-row raw record, all seven columns
(`year, month, day, weight, flag, station, co2`), written from a fresh
`fetch_openml(data_id=41187)` frame with exact float round-trip (verified:
identical hashes and byte-identical monthly aggregation from the CSV and from
a live fetch). The non-analysis columns (`day, weight, flag, station`) are
retained because the Stage-0 era/source transcription (§8) reads the station
column; no analysis touches them.
File sha256: `6e50ccd10d6132da6df272f5e2b30d2f02c5134cda6bbd3a1b2b69fbe48d30eb`.

**Canonical hash (the prereg-referenced value):** sha256 over the
concatenated float64 little-endian bytes of the `year`, `month`, and `co2`
columns, in that column order, in fetched row order, over the FULL 2225-row
raw record:

```
MAUNA_CANONICAL_SHA256 =
5bcdc813b4c3b570c9947acfaa0d3ff8cb5f89094b3e4e5121f72535a0cc0910
```

The byte-serialization convention (`np.ascontiguousarray(col.astype(float)
.values).tobytes()`) is the same one the M1 benchmark used for the co2-only
hash, so the two pins are directly comparable. The M1 pin
`7e301efd6dbd2b4007723368aa69ebd2259ea6aa1d431650c209df181f244cb9`
(§6.2) stays recorded and is re-verified at every load for continuity.

**Runtime enforcement:** `bistar_gp/data.py` verifies, at every Mauna load
and for both sources (vendored CSV and OpenML retrieval): the canonical hash,
the co2-only continuity hash, the raw row count 2225, the post-filter count
2225 (the §6.2 `co2 > 0` filter is asserted to remain a no-op), the monthly
count 521, and — at the prereg cutoff rule (`test_years = 5.0`) — the split
counts 461/60. Any mismatch is a hard `RuntimeError`; no fallback data path
exists (the pre-A9 synthetic fallback is removed).

**Holdout-seal note (§6.6):** computing the canonical hash necessarily
streams test-era rows; that is the PROVENANCE LAYER verifying artifact
identity, which the seal permits. Study-facing code uses the new
training-only entry point (`load_mauna_loa_training`), which never returns,
logs, or persists test y values; split metadata (461/60, cutoff rule) remains
available, as §6.6 explicitly permits.

**What this addendum does NOT change:** no threshold of §6.15, no gate of
§6.7, no arm definition, no candidate set. The remaining
implementation-coupled §6.15 values stay owed at M2b (E1 tolerances, A6
budgets, A5 fallback) and M2c (S2/S3/G-toy tolerances, divergence-clustering
predicate, M1 overlap diagnostic, corrected profile band masses).

---

## v1.2 — E1 coordinate convention (first M2b addendum, pre-implementation) — 2026-07-11

**Prereg anchor:** §2 Stage B (Enabler E1 paragraph), §6.15 (row "E1
equivalence tolerances + frozen point-generation distributions"), §6.16
addendum protocol, decisions A5/A6/A10/A11 (§7). Author-directed
clarification, recorded BEFORE any E1 code, benchmark number, or pilot
result exists (§6.16 ordering satisfied). The frozen plan's Stage-B sentence
defines E1 as "the unconstrained log joint assembled from gpytorch raw
parameters, analytic prior log-probs, and constraint Jacobians"; per §6.16
that text stays untouched, and this addendum GOVERNS the coordinate
convention it left ambiguous. Rationale: as written, the sentence permits an
E1 whose NUTS coordinates are gpytorch raw (softplus) parameters — a
DIFFERENT unconstrained parameterization from the S1 pyro path, which
samples in pyro's `biject_to(support)` coordinates (log-space for the
Gamma/LogNormal sites). Sampling in a different coordinate system is a
reparameterization, and reparameterization is the S3 strategy under test;
letting it into E1 silently would both contaminate the S1-vs-S1f comparison
(no longer "statistically identical target, cheap leapfrogs") and pre-judge
S3.

**(1) Public coordinates are pyro's; gpytorch raw is internal-only.** E1's
PUBLIC NUTS coordinates are the exact pyro unconstrained sample-site
coordinates returned by `pyro.infer.mcmc.util.initialize_model` on the S1
target (`_hmc_pyro_model`), with the same site set, site order, and support
transforms as S1 (`fit_hmc`) — the same objects `fit_hmc_laplace` already
consumes (`init_params, potential_fn, transforms, _ = initialize_model(...)`).
GPyTorch raw parameters may serve as an internal evaluation representation
only; they never define the sampling coordinates. For each pyro-coordinate
state u, E1 evaluates as follows:

- constrained value: theta_s = `transforms[s].inv(u_s)`, where `transforms`
  is the site-transform dict returned by `initialize_model` (the oracle's own
  transform; `transforms[s]` maps constrained to unconstrained, its `.inv`
  recovers theta);
- theta is mapped into the corresponding gpytorch parameter WITHOUT breaking
  autograd (functional parameter substitution in the differentiable graph; no
  `.data` writes on the gradient path);
- the GP marginal is evaluated directly on the same module — no
  per-evaluation deep copy (`pyro_sample_from_prior()`'s copy is exactly the
  ~200x cost E1 exists to remove);
- the same support-transform log-Jacobian terms pyro applies are added, one
  per site.

Consequence: S1f is S1 in BOTH target and coordinates; only the evaluation
path differs. Any change of sampling coordinates remains reserved for S3 and
arrives with its own Jacobian log-determinant and M2c equivalence gates; E1
must not become S3 by accident.

**(2) No cross-parameterization comparison without the explicit map.** A
softplus gpytorch-raw potential is never compared directly against pyro's
log-coordinate potential — the two differ by a genuine change-of-variables
term, so a "match" or "mismatch" between them is meaningless as stated. If an
internal raw-coordinate formulation is tested at all, the comparison goes
through the explicit coordinate map u to raw and its change-of-variables
Jacobian (D13's `_raw_log_jacobian` pattern applies to that internal check
only, not to E1's public target).

**(3) Single-evaluation composition rule (the D6/D13 error classes).** Each
E1 potential evaluation computes the full observation marginal log p(y |
theta) exactly once, as the summed `log_prob(y)` of the noise-added marginal
MVN. `gpytorch.mlls.ExactMarginalLogLikelihood` is NOT used as a pure
likelihood with priors added on top: it already incorporates registered prior
log-probs and divides by N, so composing it with an explicit prior sum
double-counts every prior and mis-scales the likelihood. Every canonical
prior enters exactly once; every pyro support Jacobian enters exactly once.
The M2b battery includes duplicate-prior and duplicate-site inventory tests
targeting exactly the D6 error class (a site or prior term entering twice, or
a latent silently dropped).

**(4) Frozen period exclusion.** The A10-frozen annual period is absent from
the seven-site E1 coordinate vector (site inventory: trend ls+os, seasonal
ls+os, medium ls+os, noise — the M2a `test_pyro_sampled_site_inventory_stays_seven`
inventory). The battery tests that E1 excludes it and that it remains exactly
1.0 through E1 evaluations. The period's old Interval boundaries are REMOVED
from the E1 boundary stress-point sets: with the period frozen, no
Interval-constrained coordinate remains among the seven sites, so those
stress points would probe a coordinate that no longer exists. Boundary stress
points are therefore near-zero noise, near-singular kernels, and extreme
lengthscale/outputscale magnitudes.

**(5) Posterior-predictive equality gate: paired states, not chains.** The
battery's posterior-predictive equality item is DEFINED on paired identical
constrained hyperparameter states: one frozen set of theta states is pushed
through both evaluation paths' predictive machinery and compared pointwise.
Pointwise equality is NOT demanded of independent NUTS chains — two correct
samplers of the same target do not produce equal draws. If a chain-level
comparison is retained at all, it must use a preregistered
distributional/MC-error criterion, frozen in the M2b tolerance addendum
before any chain used in the comparison is run.

**(6) Microbenchmark persistence firewall.** The real-data E1 NUTS
microbenchmark runs on the training-only loader (`load_mauna_loa_training`;
the v1.1 seal note continues to govern) and may persist ONLY timing fields,
potential-evaluation counts/costs, and leapfrog counts. Samples and
scientific diagnostics (posterior summaries, R-hat/ESS, divergence
locations, acceptance statistics, any per-site value) are discarded without
printing or serialization — the benchmark exists to price a leapfrog, not to
preview a posterior (§6.5 ordering/blinding).

**(7) Cost-projection labeling.** M2b finalizes measured cost projections
ONLY for E1/S1f and machinery they directly share. S3 and S4 numbers are
frozen as AUTHOR-APPROVED CEILINGS (the A6 provisional values) until their
M2c implementations can be benchmarked; they are never labeled measured
projections.

**What this addendum does NOT change:** the battery's enumerated content
(§6.15 row) except as clarified in (4) and (5); no gate of §6.7; no arm,
candidate set, or v1.0-frozen threshold. The E1 numeric tolerances +
point-generation distributions, the A6 final budgets, and the A5 fallback
design still land as their own M2b addenda per §6.15, after this convention
is in force.

---

## v1.3 — S1 target correction: the pyro path counted the marginal likelihood N times (M2b, pre-battery) — 2026-07-11

**Prereg anchor:** §2 Stage B (strategy S1 "current `fit_hmc` (MAP-init, td7,
pyro path)"; the E1 battery's reference "agreement with the pyro potential"),
§6.15, §6.16, addendum v1.2 point 3. Recorded BEFORE any E1 battery number,
benchmark, or pilot result exists; discovered while implementing E1 under the
v1.2 single-count composition rule, whose first equivalence probe against the
S1 oracle exposed the defect.

**Finding 1 (D22, FIXED).** `_hmc_pyro_model` — the traced target shared by
`fit_hmc` (S1), `fit_hmc_laplace`, and `fit_vi` — emitted the observation
site inside `pyro.plate("data", N)`. The observation marginal is a single
MultivariateNormal whose EVENT dimension already covers all N data points;
the plate expanded it to a batch of N identical MVNs, each scored against
the full y. The sampled target was therefore

    p(theta) * p(y | theta)^N     (likelihood raised to the N),

not the posterior. Evidence, all exact: the traced obs log-prob equals
N x the independently computed marginal (toy N=40: -864.851 = 40 x -21.621);
the initialize_model potential equals the N-fold composition to 1e-12; a
minimal pyro-only model (no gpytorch) reproduces the factor exactly, and
removing the plate restores the single count. Fix: the obs site is emitted
bare (`bistar_gp/fit.py::_hmc_pyro_model`); regression tests pin the traced
obs log-prob to the independent marginal and the full potential to the
single-count composition -(log p(y|theta) + sum log p(theta_s) +
sum log|dtheta_s/du_s|) at paired states
(`tests/test_model_and_fit.py::test_hmc_target_counts_marginal_likelihood_once`,
`::test_hmc_potential_is_single_count_composition`).

**Meaning of "S1" from this addendum on:** the corrected target. The E1
battery gates against the corrected pyro potential; v1.2's requirement that
E1 compute the marginal exactly once and the battery's "agreement with the
pyro potential" are now consistent rather than contradictory.

**Finding 2 (D23, DOCUMENTED — not fixable inside S1).** Pyro's autograd
through the traced target is BROKEN for every kernel hyperparameter site:
gpytorch's prior-value injection (`setting_closure` -> `initialize` ->
`.data.copy_`) severs the graph from the conditioned sample value into the
kernel parameters, so the NUTS gradient for those coordinates omits the
likelihood contribution entirely (finite-difference arbitration on the toy:
autograd -0.0499 vs true -1.0820 for the SE lengthscale, with E1's autograd
matching finite differences on every coordinate to 1e-9-scale). The noise
site alone keeps a connected graph (gpytorch's non-strict attribute-replace
fallback happens to preserve it). Consequences, recorded now:

- S1's NUTS proposes with a partially wrong gradient field. The invariant
  target is still defined by the potential (acceptance uses exact
  potential values), so this is an efficiency/guidance defect layered on
  top of Finding 1's wrong-measure defect — a candidate mechanical
  explanation for the recorded S1 pathologies (step-size collapse,
  tree-depth saturation, ESS ~ 1), which remains a HYPOTHESIS until the
  microbenchmark and pilots read on the corrected code.
- The E1 GRADIENT gate cannot reference the oracle's autograd. The battery's
  gradient reference is CENTRAL FINITE DIFFERENCES of the corrected oracle
  potential (the function defines the target; its autograd is an
  implementation artifact of the deep-copy path). E1's autograd is
  additionally required to match its own finite differences.
- Any S1-vs-S1f comparison (microbenchmark included) carries a disclosed
  asymmetry: identical target, different per-leapfrog cost AND different
  gradient-field correctness. Cost-per-leapfrog remains well-defined for
  both; cost-per-effective-draw comparisons must cite this addendum.

**Standing caveat on pre-existing results (disclosure, no relabeling here):**
every result produced through `fit_hmc`, `fit_hmc_laplace`, or `fit_vi`
before this correction sampled (or variationally approximated) the
likelihood-to-the-N target with the Finding-2 gradient field: the D8 Mauna
impact-assessment HMC runs, the D12 method x metric HMC/VI numbers, the D18
prior-sensitivity HMC headline (0.696 td7 / 0.683 td10) and its VI arm, and
the regenerated figure caches. Unaffected: MAP (no pyro), `fit_mcmc_simple`
(D13-corrected measure, single-count mll x n), all prior-IS / SIR /
profile-quadrature numbers (no pyro NUTS), and the A9/A10/A4 M2a
infrastructure. Re-interpretation or re-labeling of already-ratified records
(D12/D18 and the W-series writeup decisions) is a pending author decision,
queued explicitly — nothing in those records is edited by this addendum. The
D19 study itself is unaffected going forward: no pilot, posterior, or Mauna
BMS* number exists yet (§6.16 ordering satisfied), and G-toy goldens (M2c)
were always defined as estimator-specific rather than
reproduce-the-old-number (§6.9).

**What this addendum does NOT change:** no gate of §6.7, no arm, no
candidate set, no v1.0 threshold. The E1 tolerances + point sets (with the
finite-difference gradient reference above), A6 budgets, and A5 fallback
still land as their own M2b addenda.

---

## v1.4 — E1 equivalence battery: frozen tolerances, point-generation distributions, and references (M2b) — 2026-07-11

**Prereg anchor:** §6.15 row "E1 equivalence tolerances + frozen
point-generation distributions", §2 Stage B battery enumeration, addenda
v1.2/v1.3. Frozen NOW, before any pilot result is read and before the E1
microbenchmark runs. Implementation: `tests/test_e1_potential.py` — the
constants below are its module-level frozen values; a tolerance revision is
a new addendum, never an edit.

**Fixtures (code-level gate; synthetic data only, §6.5):** toy structure
(4 sites; x = linspace(0,5,40), y = sin(2x) + 0.3 N(0,1), torch seed 0) and
the Mauna MODEL STRUCTURE on a synthetic monthly series (7 sites; n=120,
numpy seed 0 — never real Mauna values). Both MAP-fitted (fit_map, 150
iterations, lr 0.05) before the battery point sets are generated.

**Frozen point-generation distributions:**
- MAP neighborhoods: u_map plus sigma * N(0, I) per coordinate, sigma in
  {0.1, 1.0}, torch.Generator seeds {0,1,2,3,4} per sigma, plus u_map itself
  (11 states).
- Prior draws: theta_s ~ prior_s under torch.manual_seed(s), s in
  {100..109}, mapped to u by the oracle transforms (10 states).
- Tail/boundary offsets on u_map by site-name substring (7 states):
  near-zero noise (noise -15), large noise (+8), long/short lengthscales
  (+-8), large/small outputscales-and-variance (+-8), and the near-singular
  combination (lengthscale +8, outputscale/variance +8, noise -15). Per
  v1.2 point 4 no period coordinate exists and no Interval boundary appears
  among the sites; the pre-v1.2 "Interval boundaries" stress family is
  formally EMPTY at M2b.
- Invalid-SPD states (behavior-parity only): noise -40; and
  outputscale/variance +30 with noise -40.
- Directions (curvature gate): unit-normalized N(0, I) with generator seeds
  {200, 201, 202}, at u_map, the sigma=0.1/seed-0 neighbor, and the
  seed-100 prior draw.

**Frozen tolerances (worst measured deviation on both structures, then the
frozen bound; margins are the point of the gap):**

| Gate | Measured worst | Frozen |
|---|---|---|
| potential vs oracle, relative to max(1, oracle) | 6.0e-16 | 1e-9 |
| E1 autograd vs central FD of the ORACLE (per coordinate, step 1e-5 scaled; scale = max(1, max FD coordinate)) | 2.3e-7 | 1e-4 abs + 1e-4 * scale |
| directional Hessian: FD of E1 gradient (step 1e-5) vs oracle second difference (step 1e-3), relative | 7.5e-6 | 1e-3 |
| likelihood / prior / Jacobian components vs independent oracles | 1.7e-16 | 1e-9 relative |
| transform round-trips (u and theta) | 1.1e-16 | 1e-10 |
| paired-state posterior-predictive mean/variance | (exact-path identity) | 1e-9 relative |

**References and defect routing:** the potential-value reference is the
CORRECTED S1 oracle (v1.3). The gradient reference is central finite
differences of that oracle — its autograd stays broken for kernel sites
(D23) and a SENTINEL test asserts the defect is still present, so an
environment upgrade that silently fixes it forces a review of this addendum
rather than passing unnoticed. The curvature gate uses first-order machinery
only: double-backward (create_graph) through the gpytorch marginal log-prob
graph returns silently wrong directional Hessians (D24; measured 3.3026
against a triple-agreeing true value 3.9444 on the toy at MAP, ~16% off,
persisting with fast_computations disabled — so the defect is in the custom
linear-operator autograd Functions, not the fast paths). A second sentinel
pins D24. Consequences recorded now: any M2c S2 mass-matrix construction
must assemble the MAP Hessian from first-order differences of the E1
gradient (never create_graph through the marginal), and `fit_hmc_laplace`'s
whitening Hessian — torch.autograd.functional.hessian on the oracle
potential — is affected by BOTH D23 and D24, which the v1.3 standing caveat
already covers at the results level.

**Posterior-predictive equality (v1.2 point 5):** implemented as the
paired-state gate — one frozen set of constrained states through both
parameter-injection paths, pointwise-equal predictive mean and variance at a
frozen 25-point grid. NO chain-level comparison is preregistered and none
will run; the alternative left open by v1.2 ("if retained, a
distributional/MC-error criterion") is hereby NOT retained.

**Battery inventory (items in `tests/test_e1_potential.py`):** (a) site
inventory/order + duplicate-prior/site guards (D6/D4 classes, v1.2 point 3);
(b) potential agreement over all regular states; (c) gradient gates (oracle
FD + self FD) + the D23 sentinel; (d) directional Hessians + the D24
sentinel; (e) separate components against independent oracles; (f)
round-trips; (g) paired-state predictive equality; (h) invalid-SPD behavior
parity; (i) A10 period exclusion and immobility; (j) S1f sampler schema +
diagnostics honesty contract. 29 tests; battery passes at this freeze (28
passed, 1 structure-conditional skip).

**What this addendum does NOT change:** no gate of §6.7, no arm, no
candidate set. A6 final budgets and the A5 fallback design remain owed as
the next M2b addendum, after the microbenchmark.

---

## v1.5 — E1 NUTS microbenchmark results; final A6 budgets; frozen A5 subsample-fallback design (M2b, round 5) — 2026-07-11

**Prereg anchor:** §1.2 (E1 rows "PENDING the M2b E1 NUTS microbenchmark"),
§6.15 rows "A6 pilot budgets finalized" and "A5 subsample-fallback", §7
A5/A6/A7, addenda v1.2 (points 6-7) and v1.3. No pilot, posterior, or Mauna
BMS* number exists; the microbenchmark persisted timing, potential-
evaluation, and leapfrog-count fields only (`experiments/d19_e1_bench.py`,
artifact `runs/d19_planning/e1_nuts_microbench.json`, firewall note embedded
in the artifact; samples and scientific diagnostics discarded unread).

### Microbenchmark (local, macOS arm64 14 cores, 10 torch threads; td7,
50 warmup + 50 draws, seed 0, single chain; medians over 20 reps for
per-eval rows)

| Quantity | sub-150 | full N=461 |
|---|---|---|
| S1 potential value (corrected target) | 6.01 ms | 10.52 ms |
| E1 potential value | 1.90 ms | 5.37 ms |
| S1 value+gradient (one leapfrog's work) | 7.39 ms | 14.44 ms |
| E1 value+gradient | 3.33 ms | 12.19 ms |
| per-evaluation advantage, S1/E1 | 3.2x value / 2.2x grad | 2.0x / 1.2x |
| S1f NUTS: wall, sampling leapfrogs | 5.53 s, 334 (6.7/draw) | 32.97 s, 1378 (27.6/draw) |
| S1f wall ms/leapfrog (warmup overhead inside) | 16.6 | 23.9 |
| S1 NUTS: wall, sampling leapfrogs | 94.26 s, 6350 (127/draw — saturated) | not run (§1.3: pyro path sub-150 only) |
| S1 wall ms/leapfrog | 14.8 | — |

**Cost-story revision (supersedes the §1.1/§1.2 anchors for planning):** the
plan's measured pyro-potential rows (51.8 ms sub / 1.486 s full per value,
84.6 ms / 2.793 s per gradient) were measurements of the PLATED (D22) target,
whose obs term evaluated a batch of N identical MVNs; on the corrected
target those costs are 6.0/10.5 ms and 7.4/14.4 ms. The Stage-B motivation
sentence "the measured ~200x per-leapfrog advantage over the deep-copy path"
therefore no longer describes evaluation cost: post-correction, E1's
per-evaluation advantage is 1.2-3.2x. E1's operative advantages are (a)
D23 immunity — correct gradients on every coordinate, where S1's broken
kernel-site gradients saturated td7 in the microbenchmark (127
leapfrogs/draw vs S1f's 6.7 at sub-150: ~17x fewer leapfrogs per draw and
~17x less wall per draw, from guidance quality rather than evaluation
cost) — and (b) no per-evaluation deep copy. Single-seed, single-chain,
50w+50d caveat: leapfrog counts are geometry- and adaptation-dependent;
budgets below therefore freeze on the SATURATED bound (127 leapfrogs per
iteration at td7), which is count-independent.

### Final A6 budgets (frozen; pilot shape everywhere: 4 chains x
(200 warmup + 200 draws), seeds 0/1/2/3, td7 — §6.15)

| Item | Frozen budget | Anchor and label |
|---|---|---|
| E1 build + battery + microbenchmark | DONE: ~1 dev-day; compute ~3 min | under the provisional 2 dev-days + 30 min |
| Toy smoke (G-toy), per strategy | 30 min | unchanged from provisional |
| S1f pilot, sub-150 | 2 h | MEASURED saturated bound: 4 x 400 x 127 x 16.6 ms = 56 min; 2 h keeps a 2.1x cushion |
| S2 pilot, sub-150 (E1 vehicle) | 2 h | AUTHOR-APPROVED CEILING (v1.2 point 7): mass-convention overhead unmeasured until M2c |
| S3 pilot | 2 dev-days + 4 h sub-150 | AUTHOR-APPROVED CEILING (v1.2 point 7) until M2c |
| S4 pilot | 30 min | AUTHOR-APPROVED CEILING (v1.2 point 7) until M2c |
| S1 pilot, sub-150 ONLY | 6 h | measured anchor: the saturated 100-iteration microbench chain cost 94 s, so 4 x 400 iterations projects to ~25 min; the 6 h ceiling absorbs pathological adaptation |
| Stage A per arm | 1.5 h core + gated IS pools | unchanged from provisional |
| Paper-target run (full N=461), per G-B-surviving strategy x arm, E1 path | 4 h | MEASURED saturated bound: 4 x 400 x 127 x 23.9 ms = 81 min; x1.5 engineering overhead = 2.0 h; 4 h doubles that |
| S1 pyro path at full N | none | barred without explicit author exception (§1.3, unchanged) |

Della thread-pinning numbers remain OWED: they land as their own addendum
after `experiments/d19_bench.py` runs on Della (A7), before any Della job
assignment. Note for that re-run: the pre-D22 Della anchors also measured
the plated target and are superseded the same way.

### Frozen A5 subsample fallback (design rule, exact N, infeasibility predicate)

- **Design rule:** whole-span, season-preserving index subsample of the 461
  training months: `indices = np.round(np.linspace(0, 460, N_fb)).astype(int)`
  — the same frozen rule the sub-150 design already uses (§1.1,
  `experiments/d19_bench.py`, the microbenchmark above), so every pilot
  validates the same subsampling geometry the fallback would ship.
- **Exact N:** N_fb = 232. The step 460/231 = 1.991 months keeps the full
  38.4-year span (trend identifiability), cycles through all twelve
  month-of-year phases across consecutive years (N_fb = 231 gives step
  exactly 2.0 and would lock sampling to six fixed phases forever), and cuts
  the dominant dense-solve cost by (461/232)^3 = 7.8x.
- **Infeasibility predicate (engineering/budget evidence only, per A5):**
  the fallback fires iff, for EVERY strategy that passed G-B validity at
  sub-150, the projected paper-target cost at full N=461 exceeds that
  strategy's frozen paper-target budget above, with
  projected cost = (median per-leapfrog wall cost at full N on the executing
  platform: this microbenchmark locally, or the A7 Della re-measurement for
  Della jobs) x (the 90th percentile of the strategy's own sub-150 pilot
  per-draw leapfrog counts, capped at 127) x 1600 iterations (4 chains x
  400) x 1.5 engineering overhead. Admissible inputs: timing,
  potential-evaluation, leapfrog-count, and budget fields ONLY; adequacy
  diagnostics and BMS* outputs are barred from the trigger. Evaluated once,
  before any M3 full-scale assignment; the arithmetic and outcome are
  committed with the run log. If the predicate fires, the N=232 fallback is
  validated through ALL gates at that scale and disclosed as the paper
  target (A5).

**What this addendum does NOT change:** no gate of §6.7, no arm, no
candidate set, no battery value of v1.4. S3/S4 numbers above remain
ceilings, never measured projections, until M2c (v1.2 point 7).

---

## v1.6 — codex M2b review corrections: append-only discipline restored; A5 predicate completed; gradient-gate redesign with measured discrimination limits (M2b) — 2026-07-11

**Prereg anchor:** §6.16, addenda v1.2-v1.5, §6.15 rows "E1 equivalence
tolerances" / "A6 pilot budgets" / "A5 subsample-fallback". Two codex
gpt-5.6-sol (xhigh) review rounds ran on the M2b branch before this PR
finalizes (round 1: 14 findings on the base diff; round 2: verification plus
5 findings on the fixes). No pilot, posterior, or Mauna BMS* number exists.

**Process correction (round 2, finding: append-only violation).** The
round-1 fix commit edited the already-committed v1.4/v1.5 texts in place
(with inline round markers), contrary to this file's header rule that later
addenda never modify earlier ones — and among those edits were gradient
tolerances revised after observing test failures, which is the exact
tune-to-pass pattern the battery header forbids. Cure: v1.4 and v1.5 are
RESTORED to their as-committed text (the in-place-edited intermediate exists
only in branch history, commit be08285, for audit); every correction lands
here, append-only, with its reasoning. Where this addendum contradicts
v1.4/v1.5, this addendum governs.

### Corrections to v1.4 (battery)

1. **Tolerance convention:** the potential gate reads relative to
   max(1, |oracle|) — absolute value, matching the code
   (`tests/test_e1_potential.py::TOL_POTENTIAL_REL` usage).
2. **Gradient-gate coverage and redesign (round 1 finding 2 + round 2
   finding on discrimination).** v1.4 froze the FD gradient gate on a
   subset of states (6 MAP + 4 prior). Widening it to every frozen regular
   state exposed two facts, both measured on both structures:
   - At the five non-jitter tail states (large_noise, long/short
     lengthscales, large/small outputscales) FD stays clean: worst deviation
     5.2e-7 of the state gradient scale. The tight gate (1e-4 abs + 1e-4 x
     scale) applies there, alongside the MAP and prior states (worst
     2.3e-7).
   - At the two jitter-engaged states (near_zero_noise, near_singular) NO
     central-difference reference discriminates kernel-coordinate gradient
     disconnection at ANY step size: adaptive-jitter branch flips between
     the FD probes inject evaluation noise of order the potential's
     magnitude, so even the CORRECT E1 gradient shows per-coordinate FD
     deviations up to 5.4x the coordinate scale at steps 1e-3 to 1e-2
     (measured), indistinguishable from a disconnected candidate (deviation
     ~1.0; the substituted D23-broken oracle gradient — the natural
     disconnected mutant — passes any scale-relative band that the correct
     gradient passes). An intermediate 0.2-of-scale gate at near_zero_noise
     claimed disconnection discrimination it does not have (round 2
     measurement: the disconnected mutant scores 2.0e-3 to 5.4e-2 of shared
     scale on the Mauna structure, all passing) and is WITHDRAWN.
   Frozen design, replacing the v1.4 gradient row:
   - MAP neighborhoods (11 states), prior draws (10), and the five clean
     tail states: per-coordinate tight gate, 1e-4 abs + 1e-4 x state scale,
     E1 autograd vs central FD of the oracle (step 1e-5 scaled).
   - near_zero_noise and near_singular: a CONNECTEDNESS gate only — E1
     autograd must equal the ORACLE autograd on the noise coordinate (the
     one site whose oracle graph the D23 defect spares) within 1e-9
     relative (measured: bit-exact to 1.4e-16). Kernel-coordinate gradients
     at these two states are EXPLICITLY NOT GATED — no implementable
     reference discriminates there — and this residual exposure is
     disclosed rather than papered over. Bounding structure, stated for the
     record: E1's graph topology is state-independent (one code path, one
     override dict for all sites); the only state-dependent branch is
     gpytorch's shared cholesky/jitter machinery, whose backward carries
     noise and kernel coordinates through the same matrix operations, and
     the noise coordinate is verified connected at exactly these states;
     potential VALUES agree at machine precision there (round 2 wording
     correction: path difference 6e-8 absolute on a 4.4e8 potential,
     1.5e-16 relative — "machine-precision agreement, each path
     repeat-identical", not literally "exact"); and every kernel coordinate
     is FD-gated at the 26 other states, including jitter-free
     extreme-parameter states.
   - Execution completeness: the battery asserts that every one of the 28
     frozen regular states executes its assigned gate (an executed-label
     set check; a state silently going non-finite fails the battery rather
     than shrinking coverage — round 2 finding on silent skips), and the
     near-singular/near-zero connectedness gates run before and
     independently of any FD computation.
3. **D23 sentinel:** per kernel site over three frozen states with the
   noise site pinned to FD agreement (a partial upstream fix cannot hide
   behind a max-over-sites check). The sentinel doubles as the gradient
   gate's TEETH: the disconnected oracle gradient measurably violates the
   tight gate at the states where discrimination is claimed.
4. **Battery inventory:** an eval-mode-entry regression (D4 class) joins
   the battery; fit_hmc_e1 exposes init_to_map with fit_hmc's exact
   boundary-guarded fallback (S1f initialization-surface parity). Counts at
   this freeze: 31 collected, 30 passed, 1 structure-conditional skip; full
   suite 207 passed + 1 skipped.

### Corrections to v1.5 (microbenchmark, budgets, fallback)

5. **Ratio pair:** S1 vs S1f at sub-150: ~19x fewer sampling leapfrogs per
   draw (6350/334) and ~17x less wall per draw (94.26 s / 5.53 s); v1.5's
   "~17x fewer leapfrogs" was arithmetic slippage.
6. **Firewall reading (awaits author ratification with this PR):** beyond
   timing / potential-evaluation / leapfrog-count fields, the benchmark
   artifact carries run configuration (seed, iteration counts, tree depth)
   and environment provenance (versions, threads, platform, host,
   timestamp, git sha) plus fixed caveat strings. The v1.2 point-6
   exclusion is read as targeting samples and scientific diagnostics;
   configuration and provenance are science-free and necessary to interpret
   timings (AST-audited key inventory; no hyperparameter, MAP, sample,
   acceptance, divergence, or step-size field exists in the artifact). The
   script's real-data error path suppresses exception MESSAGES (class name
   only) so a raising library call cannot leak a value; full tracebacks
   stay available on the synthetic path.
7. **A5 infeasibility predicate, completed** (round 1 finding 1: the v1.5
   predicate was unevaluable for survivor sets containing S4 or only S1).
   The fallback fires iff the projected full-N=461 paper-target cost
   exceeds the frozen paper-target budget for EVERY G-B-surviving strategy,
   with strategy-specific costing:
   - NUTS strategies on the E1 vehicle (S1f, S2, S3): projected cost =
     (median per-leapfrog wall cost at full N on the executing platform:
     the M2b microbenchmark locally, or the A7 Della re-measurement for
     Della jobs) x (the 90th percentile of the strategy's own sub-150 pilot
     per-draw leapfrog counts, capped at 127) x 1600 iterations (4 chains x
     400) x 1.5 engineering overhead, against the 4 h budget of v1.5.
   - S4 (MAP+Laplace, no leapfrogs): projected cost = measured sub-150 S4
     pilot wall time x (461/150)^3 = 29.0 x 1.5 overhead, against a new S4
     full-N paper-target budget of 1 h — an AUTHOR-APPROVED CEILING
     consistent with v1.2 point 7 (M2c may refine by addendum; the
     corrected first-order full-N machinery prices a MAP fit at 4.6 s and a
     7-site FD Hessian at ~0.2 s, so 1 h is generous).
   - S1 (pyro path): never enters the projection — full-N pyro-path chains
     stay barred by §1.3 regardless of pilot outcomes. A survivor set
     containing ONLY S1 leaves full N without an admissible vehicle and
     fires the fallback by the standing bar; an explicit author exception
     under §1.3 would arrive as its own addendum with its own budget.
   Admissible inputs, evaluation timing, and post-fire validation are
   unchanged from v1.5 (timing/potential-evaluation/leapfrog/budget fields
   only; adequacy and BMS* outputs barred; evaluated once before any M3
   full-scale assignment; N=232 fallback re-passes all gates and is
   disclosed as the paper target).

**What this addendum does NOT change:** no gate of §6.7, no arm, no
candidate set, no v1.0 threshold, no data pin of v1.1, no convention of
v1.2, no finding of v1.3. S3/S4 numbers remain ceilings until M2c.

---

## v1.7 — erratum to v1.6 correction 2 (wording only) — 2026-07-11

Codex round 3 (final confirmation) flagged one self-contradictory phrase in
v1.6 correction 2: "within 1e-9 relative (measured: bit-exact to 1.4e-16)".
Bit-exact means a difference of zero; the measurement was a worst RELATIVE
difference of 1.4e-16 (toy structure; 0.0 on the Mauna structure). The
phrase reads: "within 1e-9 relative (measured worst: 1.4e-16 relative)".
No tolerance, gate, state set, or claim of substance changes.

---

## v1.8 — D22-D24 impact amendment: goldens retirement, corrective milestone M2bR, shared Hessian protocol, Della hold (M2b close) — 2026-07-11

**Prereg anchor:** §4 (milestone map), §6.5, §6.9 (G-toy goldens), §6.15,
§7 A7/A11, addenda v1.3/v1.6. Adopted from the codex meta-review of the M2b
closeout (author-forwarded): D22-D24 changed the scientific baseline, not
merely the benchmark implementation, so they receive their own corrective
treatment BEFORE M2c. Companion artifact: `docs/d22-d24-impact-audit.md`
(artifact classification with dependency verification + the author
ratification checklist). No pilot, posterior, or Mauna BMS* number exists.

**1. Goldens retirement (§6.9).** Every golden or reference value derived
from pre-correction fit_hmc / fit_vi / fit_hmc_laplace output is RETIRED as
a characterization of any sampler's correct behavior — including the D18
HMC 0.696/0.683 pair wherever §6.9 references it. References that survive
(dependency-verified in the audit): prior-IS, SIR, and the D13-corrected
RW-MH, all of which score through the direct likelihood
(`_mh_log_joint`), plus MAP and prior-predictive quantities. The M2c G-toy
tolerances will be defined against corrected-sampler behavior WITHOUT using
newly observed E1 scientific outcomes to set them (the v1.4/v1.6 discipline:
references are independent oracles or held-out estimator families, never
the gated object's own output).

**2. Corrective milestone M2bR (inserted between M2b and M2c).** Scope:
(a) author ratification of the impact audit's classifications and of the
checklist items (audit doc §4); (b) the public-API disposition decision
(D26 fork; interim warning layer ships with M2b); (c) a SMALL preregistered
corrected-impact rerun — the D12 toy method x metric comparison and the D18
HMC/VI arms re-executed on corrected samplers (S1f for HMC; VI only if an
E1-based VI exists by then, else VI is reported unavailable-pending-repair)
with its budget and comparison plan frozen as an addendum BEFORE it runs;
(d) `experiments/d19_bench.py` reworked to the v1.2-point-6 timing-only
firewall (it currently persists a MAP hyperparameter value under the
M1-era convention) and its pre-D22 anchors marked superseded; (e) the
W2/W3 writeup-decision re-openings recorded in the W-log. M2c does not
begin until M2bR closes with author sign-off.

**3. Shared Hessian protocol (M2c obligation, widened from v1.6).** The
v1.6 first-order rule binds not only the S2 mass matrix but EVERY consumer
of a GP-hyperparameter Hessian: S4's Laplace construction, Laplace
determinants, and any profile-Laplace machinery. One shared protocol is
frozen at M2c before use: central differences of validated first
gradients, a step-size stability check, symmetrization, directional-
curvature verification against second differences of the potential, and
disclosed eigenvalue regularization. (`laplace_evidence.numerical_hessian`
already differentiates a candidate-space objective by finite differences
and is out of this protocol's scope.)

**4. Benchmark interpretation decomposition rule.** Any use of the v1.5
microbenchmark reports the three factors SEPARATELY — cost per
potential/gradient evaluation; leapfrogs per iteration; wall per
iteration/draw — and never presents the composite sub-150 ratio (~19x
leapfrogs, ~17x wall) as a pure E1 evaluation speedup: the composite mixes
the 1.2-3.2x per-evaluation advantage with the D23 guidance difference.
The saturated S1 measurement stands as a historical engineering
observation about the pre-correction path.

**5. Della hold (A7 precondition added).** The A7 Della re-benchmark does
not run until item 2(d) completes and the reworked script's firewall is
verified the way the M2b microbenchmark's was (key-inventory audit). The
Della thread-pinning numbers then land as their own addendum, as before.

**What this addendum does NOT change:** no gate of §6.7, no arm, no
candidate set, no battery value of v1.4/v1.6, no budget of v1.5/v1.6. The
API warning layer changes no default and removes nothing; the default
disposition is the recorded OPEN author fork (D26).

---

## v1.9 — author ratifications; A5 trigger correction; A6 dimensional clarification; API disposition D27; frozen M2bR rerun protocol — 2026-07-11

**Prereg anchor:** §6.13 (O4), §6.15, §6.16, §2 Stage B (strategy
identities), addenda v1.5/v1.6/v1.8, decision D27,
`docs/d22-d24-impact-audit.md` §4 (dispositions). Provenance: the author
forwarded the codex gpt-5.6-sol recommendation set with the instruction to
implement it; three orchestrator corrections were applied and are marked
below. No pilot, posterior, or Mauna BMS* number exists.

**1. Ratifications (author, 2026-07-11).**
- Historical results: every pre-D22 HMC, VI, and hmc_laplace result is
  UNVALIDATED AND SUPERSEDED pending corrected reruns — not merely caveated.
  Old numbers stay as provenance only; superseded banners applied to
  `docs/impact-assessment-results.md`, `docs/fit-method-metric-comparison.md`,
  `docs/prior-sensitivity-study.md`, `docs/appendix-tree-depth-cap.md`.
- The v1.6 firewall reading: RATIFIED. Environment, timing, configuration,
  and leapfrog-count fields are legitimate engineering fields;
  hyperparameters, samples, acceptance, divergences, model scores, and
  posterior summaries remain forbidden in benchmark artifacts.
- A5 exact N = 232: RATIFIED (whole-span phase-coverage rationale), with the
  trigger corrected in item 2.
- The Della hold (v1.8 item 5): RATIFIED.
- The M2b PR opens as DRAFT.
- Scope-of-claim language rule: D22-D24 invalidate THIS repository's
  attempted HMC/VI replication (a pyro/gpytorch integration); they establish
  nothing about the thesis's original implementation (gpflow/ADVI) or its
  conclusions. Every superseded banner, decision entry, and future report
  sentence carries this framing.

**2. A5 trigger correction (supersedes the v1.6 item-7 S1 branch).** The
legacy S1 gradient path is not a validated scientific vehicle (D23), so its
survival can neither establish nor rescue full-N feasibility, and the v1.6
branch "a survivor set containing only S1 fires the fallback" is REMOVED.
Corrected trigger:
- Paper-target ELIGIBILITY: a strategy is eligible iff it passes G-B
  validity at sub-150 AND is not the legacy S1 gradient path (S1 remains a
  sub-150 pilot/diagnostic strategy only; orchestrator correction (a): its
  exclusion is stated at eligibility, and "valid at N=232" is not a
  pre-fire condition — pilots run at sub-150, and the post-fire N=232 run
  still re-passes ALL gates at that scale per A5).
- The fallback FIRES iff at least one eligible strategy exists and EVERY
  eligible strategy's projected full-N=461 cost exceeds its frozen budget
  (costing per v1.6 item 7: leapfrog projection for S1f/S2/S3, cubic law
  for S4).
- If NO eligible strategy passes G-B at sub-150, the study reports outcome
  pattern O4 (§6.13: MAP+Laplace carries the figures, joint-posterior
  claims rescoped per W6, with O4's degraded sub-case if S4 also fails) —
  a smaller dataset is never a cure for absent validity.

**3. A6 dimensional clarification (pre-ratification; codex correctly
declined the ceilings as stated).** Every A6 budget is LOCAL WALL-CLOCK
time on the executing machine — never aggregate core-hours; parallelism
does not stretch a wall budget. Pilot budgets bind per strategy x scale and
cover the complete 4-chain pilot (aggregate wall over all four chains,
sequential or parallel), INCLUSIVE of MAP initialization, warmup,
adaptation, and jitter retries. Paper-target budgets bind per strategy x
arm at the stated scale with the same inclusions. The Stage-A budget binds
per arm for the core geometry work; gated IS pools carry their own §6.15
budgets. Dev-day figures are calendar effort, not compute. With these
dimensions attached, the v1.5/v1.6 ceilings are RATIFIED: S1f and S2
anchored by E1 measurements; S3 and S4 remain HARD AUTHOR CEILINGS, never
measured projections (v1.2 point 7).

**4. Strategy identities pinned across the API change (orchestrator
correction (b)).** D27 routes the public `fit_hmc` (and
`fit_gp(method="hmc")`) through the battery-gated E1 path and retains the
legacy pyro implementation as `fit_hmc_legacy_pyro`; `fit_vi` and
`fit_hmc_laplace` are unavailable through the scientific API pending repair
(explicit `allow_legacy=True` opt-in only, warnings retained on every
legacy path — orchestrator correction (c): the explicit name is the
opt-in, the warning stays as the seatbelt). Plan §2 Stage B strategy
identities bind to IMPLEMENTATIONS, not public aliases: S1 = the legacy
pyro path (now `fit_hmc_legacy_pyro`); S1f = the E1 path (now the public
`fit_hmc`). Every plan reference resolves accordingly; the microbenchmark
already measures S1 through the legacy path by name.

**5. M2bR corrected-impact rerun protocol: FROZEN.** The complete protocol
— recovered original D12/D18 parameters with file:line citations, the
six-run frozen list (2000 draws + 1000 warmup, seed 42, td7/td10 pairs,
four D18 prior configurations through `fit_hmc_e1`), diagnostics and
comparison plan, the unchanged-arm re-verification at atol=1e-12, the
120-minute budget arithmetic, and the stop-and-report rule (reserve the
final 10 minutes for persistence; never extend after inspecting results) —
resides in `docs/m2br-corrected-impact-protocol.md`, frozen at

```
sha256 2d4a827777d9f6eafdc189f2f962d63b539e04a744cf5f4d58ba4683eaaf5a83
```

It executes ONLY in the M2bR PR after the M2b merge; no VI or hmc_laplace
run occurs before those methods are repaired; any protocol change is a new
addendum. Budget authorization: at most 2 hours local wall (author,
2026-07-11).

**What this addendum does NOT change:** no gate of §6.7, no arm, no
candidate set, no battery value of v1.4/v1.6, no microbenchmark number of
v1.5. The plan's §6.15 M2c obligations are unchanged.

---

## v1.10 — D28 corrections: ratification provenance, withdrawal terminology, M2bR purpose split, NotPSD rejection policy — 2026-07-11

**Prereg anchor:** §6.16, addenda v1.8/v1.9, `docs/d22-d24-impact-audit.md`,
D26-D28. Adopted from the author-forwarded codex correction round. No pilot,
posterior, or Mauna BMS* number exists; no M2bR run has occurred.

**1. Ratification provenance corrected.** v1.9 recorded A5 (N=232 +
corrected trigger), the dimensioned A6 ceilings, the v1.6 firewall reading,
the API disposition, the Della hold, and the M2bR rerun as author-ratified.
That provenance was WRONG: the author forwarded codex recommendations with
an instruction to implement, which is not an explicit author vote. Every
such item is re-labeled PROPOSED, PENDING EXPLICIT AUTHOR RATIFICATION, and
the pending set is enumerated in the D28 decision table
(`Notes/DECISIONS.md` D28; dispositions mirrored in the audit §4). The v1.9
line "Budget authorization: ... (author, 2026-07-11)" is corrected the same
way. Implementations already on the branch (API routing, warnings, gates,
banners) stand as REVERSIBLE proposals awaiting the vote; nothing has run.

**2. Withdrawal terminology.** "Superseded" asserts that a validated
replacement exists; none does yet. Every affected-results banner and audit
classification now reads WITHDRAWN/UNVALIDATED PENDING CORRECTED RERUN.
"Superseded" is reserved for claims whose validated replacement exists
(correctly retained for the §1.1/§1.2 cost anchors, whose corrected
measurements are in v1.5/v1.6).

**3. M2bR purpose split.** The six single-chain seed-42 runs of
`docs/m2br-corrected-impact-protocol.md` are a CONTROLLED HISTORICAL-IMPACT
AUDIT: they isolate the sampler correction's effect on the historical
numbers and are labeled "corrected single-chain comparisons"; one chain
cannot validate basin exploration or convergence, so they are never
paper-grade replacements and cannot close W2/W3. The protocol file's header
was corrected accordingly (run list unchanged) and is re-pinned at

```
sha256 45999e2f232a963b04496a5fa3cff557f2370327b216d8600eddfd23be805afa
```

Scientific validation is a separate PROPOSED layer
(`docs/m2br-validation-protocol-PROPOSAL.md`): multi-chain E1 runs for the
pivotal `informative` and `toy_elicited` configurations (4 chains x
(1000 warmup + 2000 draws), seeds 0/1/2/3, td7 and td10), with proposed
acceptance criteria (rank-normalized split R-hat < 1.01 every site;
bulk and tail ESS > 400 pooled; per-chain basin occupancy within 0.05 of
pooled per band; divergence rate < 0.1%; depth saturation < 10%; NotPSD
rejection rate < 0.1% with zero near-reference occurrences), arviz-computed
with the version pinned in artifacts, and its own budget: projected 5.2 h,
proposed ceiling 6 h local wall with audit-style stop-and-report (reduced
4 h td7-weighted variant enumerated). Only validation-passing cells may
mark historical numbers superseded or support the W2/W3 re-openings; audit
results alone may not. Both layers remain PENDING ratification and execute
only after the M2b merge.

**4. NotPSD rejection policy (implemented and tested; threshold values
proposed).** Corrected gradients explore aggressively enough that E1 chains
can reach states where the additive-kernel Cholesky exhausts its jitter
retries; the terminal `NotPSDError` previously crashed the run. Policy, now
on the branch with regression tests (`tests/test_e1_notpsd_policy.py`):
- the jitter ladder is UNCHANGED and documented (cholesky_jitter 1e-4 on
  the marginal; linear_operator psd_safe_cholesky retry defaults
  internally) — the policy converts only the terminal failure;
- a sampling-layer wrapper catches `NotPSDError` and NOTHING else, counts
  the event, and re-raises the RuntimeError text that pyro 1.9.1's
  registered handler converts to NaN energy and zero gradients — the
  proposal is REJECTED and the chain continues (mechanism verified in the
  installed pyro source and empirically: the documented crash scenario now
  completes with one counted rejection; an injected double failure counts
  exactly two; a generic RuntimeError still propagates);
- successful evaluations pass through bit-identically; `E1Potential`
  itself keeps raise-parity with the oracle, so no v1.4/v1.6 battery gate
  changes (the battery passed unchanged);
- `SamplerDiagnostics` schema version 2 adds `notpsd_rejections` under the
  None-iff-unavailable honesty contract (version-1 payloads load with the
  field marked unavailable; the legacy pyro path reports it unavailable —
  that path crashes rather than rejects);
- PROPOSED, pending ratification: the warning threshold
  `E1_NOTPSD_WARN_RATE = 1e-3` of potential evaluations (logger warning,
  never a silent hard-fail), and the validation-layer acceptance criterion
  above (rate < 0.1%, zero near-reference).

**What this addendum does NOT change:** no battery value of v1.4/v1.6, no
microbenchmark number of v1.5, no audit-protocol run list, no gate of §6.7.
Suite at this commit: 218 passed + 1 skipped.

---

## v1.11 — explicit author ballot on the D28 decision table; item-8 protocol revision; item-9 diagnostic split (D29) — 2026-07-11

**Prereg anchor:** §6.15, §6.16, §6.8 (authority conventions), addenda
v1.9/v1.10, `docs/d22-d24-impact-audit.md` §4, D28/D29. The author returned
an EXPLICIT ballot on the nine-row D28 decision table — the first item-level
author vote of the M2b sequence; the v1.10 pending labels resolve as
follows. No run of either M2bR layer has occurred; PR #7 stays Draft; M2c
stays blocked.

**RATIFIED (author, 2026-07-11):**
1. Withdrawal terminology and the audit classifications.
2. The D27 API disposition: public fit_hmc/fit_gp("hmc") on the E1 path;
   fit_hmc_legacy_pyro explicit; fit_vi/fit_hmc_laplace behind
   allow_legacy=True.
3. A5: N=232 with the corrected eligibility trigger (v1.9 item 2).
4. The v1.6 firewall field list, WITH THE RESTRICTION that leapfrog-count
   fields serve aggregate engineering-cost purposes only — they can never
   influence scientific adequacy, prior choice, model ranking, or posterior
   interpretation. Recorded interpretation (flagged for objection if wrong):
   per-draw leapfrog retention in benchmark artifacts exists solely to
   compute aggregate cost statistics such as the A5 predicate's 90th
   percentile, and is barred from any scientific reading.
5. The dimensioned A6 ceilings (v1.9 item 3).
6. The Della hold (v1.8 item 5).
7. The single-chain audit layer (`docs/m2br-corrected-impact-protocol.md`,
   sha unchanged from v1.10) — CONFIRMED as a historical-impact audit only;
   its outputs can never close W2/W3.

**Item 8 — PENDING, revised per the author's modification.** Same-MAP chain
starts are rejected: four same-start chains can miss the same basin and
still pass R-hat, ESS, and internal occupancy agreement. The revised
proposal (`docs/m2br-validation-protocol-PROPOSAL.md`, revised sha pinned
below) now specifies: chain-0 MAP start plus three OVERDISPERSED starts
frozen from the unaffected prior-IS authority references by a deterministic
rule (one start per reportable noise band with authority mass >= 5% —
weighted-median draw per band, q25/q75 fill when fewer than three bands);
a TWO-STAGE FREEZE (rule frozen now; realized pool indices + per-state
sha256 pinned in a pre-run M2bR addendum before any chain launches); a new
AUTHORITY-COVERAGE acceptance criterion — pooled chain occupancy vs the
independent prior-IS band masses within 2 sqrt(SE_auth^2 + SE_chain^2) per
reportable band, the §6.15 convention reused verbatim; and the FULL 6 h
V1-V4 design retained (the reduced variant is withdrawn). The
fit_hmc_e1 init_values capability this requires (constrained-state
injection with exact site-set validation and the _map_init_values boundary
guard) is implemented and tested. Revised file pin:

```
sha256 3ee7967d2a176f97c26fa00f18c76cc45b28bdf9753c5e5c395ab9b5beb59dd0
docs/m2br-validation-protocol-PROPOSAL.md (post-revision; supersedes no
frozen artifact — the proposal was never frozen)
```

Ratification of the REVISED protocol remains with the author.

**Item 9 — MECHANISM RATIFIED; thresholds pending behind the D29
diagnostic split, now implemented.** SamplerDiagnostics schema VERSION 3:
the hook snapshot stream now records cumulative NotPSD rejections alongside
potential evaluations, yielding notpsd_rejections_warmup and per-draw
notpsd_rejections_per_draw (leapfrog_counts layout) under the
None-iff-unavailable honesty contract, with v1/v2 payload migration and the
identity total = warmup + sum(per-draw) validated when all observed.
Derived notpsd_post_warmup_rate uses post-warmup potential evaluations as
the denominator (rejected attempts count as evaluations). fit_hmc_e1
behavior, mechanics implemented with PROPOSED numeric values: warmup
rejections reported separately (informational, no gate); ANY post-warmup
rejection emits a warning naming the draw indices; a post-warmup rate at or
above E1_NOTPSD_FAIL_RATE = 1e-3 raises with the completed diagnostics
attached (a failing run's draws are never silently consumable), enforced
whether or not diagnostics were requested. Zero-at-reference stays enforced
by regression test. The numeric pair awaiting the author: the 1e-3 fail
rate and the validation layer's early-draw window (zero rejections within
the first 50 post-warmup draws of any chain).

**Suite at this commit:** 224 passed + 1 skipped (independently verified:
init_values round-trips at 9e-16; schema v3 round-trips; migrations
covered).

**What this addendum does NOT change:** no battery value, no microbenchmark
number, no audit-protocol run list, no gate of §6.7.

---

## v1.12 — D30 start-state preflight added to the pending item-8 protocol (capability; item 8 still PENDING ratification) — 2026-07-11

**Prereg anchor:** the pending item-8 validation proposal
(`docs/m2br-validation-protocol-PROPOSAL.md`), addenda v1.9/v1.11, §6.16,
D30. This addendum records a REFINEMENT of a proposal that is itself not yet
ratified; it changes no ratified value, no battery gate, no budget, and does
not run anything. Items 8 and 9 remain PENDING the author's explicit
own-words vote (the D28 rule bars treating a forwarded codex recommendation
as a ballot).

**What D30 adds (codex-recommended, implemented, tested):** each frozen
overdispersed chain start of the item-8 protocol must pass a DETERMINISTIC
preflight before the two-stage freeze pins it —
`bistar_gp.e1_potential.preflight_start_state` checks, in protocol order and
stopping at the first failure: exact site set, constrained/unconstrained
round-trip within PREFLIGHT_ROUNDTRIP_TOL = 1e-10 relative, finite E1
potential, finite first gradient, and no terminal NotPSD at initialization
(a degenerate state that defeats pyro's initialize_model validation is
classified as a potential failure, not a site-set failure). A selected draw
that fails is replaced by the NEXT-ELIGIBLE authority draw under the frozen
rule via `select_start_state`, a deterministic first-pass selector down the
preregistered priority-ordered candidate list that raises (naming every
per-candidate failure reason) if a cell exhausts its eligible candidates,
so a cell is reported un-startable rather than hand-patched after seeing
failures. The realized number of fallback advances used per cell is pinned
in the pre-run start-freeze addendum alongside the indices and hashes.

**Verification:** the preflight classifies healthy / site-set-mismatch /
degenerate states correctly; `select_start_state` skips a leading degenerate
candidate and returns the first healthy one at a stable index across reruns,
and raises with reasons when all candidates fail (independently reproduced).
Full suite 230 passed + 1 skipped; the frozen v1.4/v1.6 battery
(`tests/test_e1_potential.py`) untouched.

**Protocol-doc pin (un-frozen; the proposal is still a proposal):** the
revised `docs/m2br-validation-protocol-PROPOSAL.md` now hashes to

```
sha256 bdbabb867680371922196b25fb55a8ac9509913fc64047b99b8da6470b7a03e8
```

This supersedes the v1.11 pin of the same file as the current
proposal-state fingerprint; it is not a freeze and confers no ratification.

**What this addendum does NOT change:** no ratified item, no gate of §6.7,
no battery value, no budget, no run authorization. Rows 8-9 await the
author's explicit vote; PR #7 stays Draft; M2c stays blocked.

---

## v1.13 — explicit author ratification of decision-table rows 8 and 9 (D31) — 2026-07-11

**Prereg anchor:** the D28 decision table, addenda v1.9/v1.11/v1.12,
`docs/d22-d24-impact-audit.md` §4, D31. The author ratified rows 8 and 9 in
their own words in the chat interface ("I ratify row 8 and row 9. you may
proceed"), which the D28 rule accepts as a valid author vote (unlike a
forwarded codex recommendation). With this, ALL nine decision-table items
are author-ratified.

**Row 8 — RATIFIED.** The M2bR multi-chain scientific-validation layer
(`docs/m2br-validation-protocol-PROPOSAL.md`, now titled RATIFIED) as
revised: two pivotal configurations (`informative`, `toy_elicited`) x
td7/td10, four chains each (seeds 0/1/2/3, 1000 warmup + 2000 draws);
chain 0 at MAP, chains 1-3 from overdispersed frozen starts drawn
deterministically from the unaffected prior-IS authority references; the
D30 preflight + next-eligible fallback; the §6.15-verbatim authority-
coverage acceptance criterion alongside rank-normalized R-hat < 1.01,
bulk/tail ESS > 400, occupancy agreement 0.05, divergence < 0.1%,
saturation < 10%; the full 6 h V1-V4 budget with stop-and-report. Only
cells passing ALL criteria yield validated replacement numbers, may mark
withdrawn historical numbers superseded, or feed the W2/W3 re-decisions.

**Row 9 — RATIFIED (mechanism and thresholds).** The NotPSD policy as
implemented: warmup rejections reported separately (informational, no
gate); any post-warmup rejection warns with draw indices; a post-warmup
rate at or above E1_NOTPSD_FAIL_RATE = 1e-3 raises with the completed
diagnostics attached (a failing run's draws are never silently consumable),
enforced with or without return_diagnostics; the validation layer
additionally requires zero rejections in each chain's first 50 post-warmup
draws; zero-at-reference stays enforced by regression test. The code
constant and message are updated from "proposed" to ratified (D31).

**What this ratification unblocks and what it does NOT.** It unblocks
recording the ratifications and moving PR #7 from Draft to Ready (code
review via the codex rounds and the benchmark-firewall key-inventory audit
are complete). It does NOT by itself authorize the M2b merge or any M2bR
run: per the ratified PR structure (D27), M2b merges as its own step, then
M2bR executes as a SEPARATE corrective-impact PR that opens with the
two-stage start-freeze (pinning realized start indices, fallback-advance
counts, and per-state hashes in a pre-run addendum) before any chain
launches. No pilot, posterior, or Mauna BMS* number exists; §6.5/§6.6
ordering and blinding continue to govern.

**What this addendum does NOT change:** no battery value, no budget number,
no gate of §6.7, no plan §6.15 M2c obligation. Suite unchanged (green).

---

## v1.14 — M2bR two-stage start freeze: realized validation-layer start states pinned (pre-run) — 2026-07-11

**Prereg anchor:** the ratified validation proposal
(`docs/m2br-validation-protocol-PROPOSAL.md`, "Overdispersed initialization"
+ "Authority-coverage criterion"), addenda v1.11/v1.12/v1.13, §6.8 (band
conventions), §6.15 (threshold inventory, coverage convention), §6.16
(append-only), D31. This is the pre-run start-freeze addendum the two-stage
freeze requires: the SELECTION RULE was frozen at v1.11-v1.13; this addendum
pins the REALIZED pool indices, fallback-advance counts, and per-state
sha256 (chain 0 included), which could not be committed earlier because the
authority pools are local artifacts. It authorizes NO chain launch by
itself: per the gate, chains launch only after this addendum is committed
(Commit A) AND an independent clean-room recomputation reproduces it
byte-identically (recorded in the pre-run D-entry, Commit B).

**Governing document fingerprints (current sha256, this checkout).**

```
docs/m2br-corrected-impact-protocol.md   45999e2f232a963b04496a5fa3cff557f2370327b216d8600eddfd23be805afa
docs/m2br-validation-protocol-PROPOSAL.md 1045c11cf14ca83e56d7cc450fbeae9bb3bcf81bc678a413b792e0a004e6302c
```

**Doc-drift reconciliation.** v1.12 pinned the validation proposal at
`bdbabb86…7a03e8` as its then-current proposal-state fingerprint. The
proposal was subsequently retitled "RATIFIED (multi-chain)" when the author
ratified row 8 (D31/v1.13), so its bytes — and therefore its hash — changed.
The CURRENT GOVERNING fingerprint of that document is
`1045c11cf14ca83e56d7cc450fbeae9bb3bcf81bc678a413b792e0a004e6302c` (above);
it supersedes the v1.11 (`3ee7967d…`) and v1.12 (`bdbabb86…`) proposal-state
pins. This is a fingerprint update only; no ratified value, criterion,
budget, or run/cell design changes.

**Stale-header note (no edit to the frozen protocol).** The header of
`docs/m2br-corrected-impact-protocol.md` still reads "PROPOSED, PENDING
EXPLICIT AUTHOR RATIFICATION". D31 (v1.13, item-6 split / decision-table row
7) ratified that six-run single-chain layer as a historical-impact audit
whose outputs can never close W2/W3. This addendum records that D31
SUPERSEDES the stale header WITHOUT altering the protocol's frozen run list
or any other byte of that file (its fingerprint stays `45999e2f…`); the
append-only discipline forbids editing a frozen artifact, including its
header.

**Topology clarification (empirically verified, changes no criterion).** The
toy E1 model built for BOTH pivotal configs (`informative`,
`toy_elicited` = `PRIOR_CONFIGS["toy_elicited_n20"]`, via
`STUDY_CONFIGS[...]`) has EXACTLY FOUR pyro sample sites:

```
likelihood.noise_covar.noise_prior                     shape (1,)
covar_module.kernels.0.outputscale_prior               shape ()
covar_module.kernels.0.base_kernel.lengthscale_prior   shape (1,1)
covar_module.kernels.1.variance_prior                  shape (1,1)
```

The validation proposal's phrase "the 7-site constrained draws" is a
carryover from the 7-site Mauna model and does not describe the toy. The
governing acceptance criteria are stated over "every site", which for these
cells is exactly these four sites; the R-hat/ESS/occupancy/coverage gates are
unchanged. The prior-IS pools carry the four constrained hyperparameters
`ths[:, ORDER]` with `ORDER = ['ls','os','lv','noise']`
(`prior_sensitivity_study.SHORT`/`ORDER`), which map one-to-one to these four
sites; a pool draw seeds a chain by reshaping each scalar into its site's
constrained shape and passing it through `fit_hmc_e1(init_values=...)`.

**Ratified refinements baked into this freeze (R-A, R-B; author-ratified,
D31 own-words vote; recorded verbatim).**

- **R-A (filler selection).** Three authority slots (chains 1-3). B = the
  number of reportable noise bands (pooled prior-IS mass >= 5%; bands
  low `noise<0.15`, mid `0.15<=noise<=0.30`, high `noise>0.30`). Band-medians
  fill B slots; the remaining `3-B` slots are fillers from the LARGEST-MASS
  reportable band: B=3 -> no filler; B=2 (one filler slot) -> the largest-mass
  band's weighted-q75 draw; B=1 (two filler slots) -> the largest-mass band's
  weighted-q25 AND weighted-q75 draws.
- **R-B (replacement-number aggregation, applies at the validation run, not
  the freeze).** 200 predictives per chain via the frozen D12/D18 extraction
  rule. The PRIMARY per-cell validated BMS posterior is computed from the
  concatenated 800 predictive-level G rows with equal per-chain contribution
  and ONE final normalization. Each chain's separately-normalized posterior
  and the cross-chain SD are reported as DIAGNOSTICS, never as the primary
  estimator.

**Deterministic details baked in (author-ratified; applied throughout).**

1. All pool operations use lexicographic `(seed, row)` ordering (pooled pool
   = seed 0 rows, then seed 1, then seed 2; `row` is the 0-based index within
   that seed's own pool file).
2. Weighted quantiles (q25/q50-median/q75): within the band, softmax weights
   `w = exp(lml - max(lml))` normalized over that band's draws; sort the
   band's draws by noise ascending (ties by `(seed,row)` ascending); the
   weighted q-quantile draw is the FIRST whose cumulative normalized weight is
   `>= q`.
3. Fallback: if an authority start fails preflight, order the fallback
   candidates WITHIN THE SAME BAND by absolute noise distance from that
   start's target-quantile draw, then by `(seed,row)`; take the first that
   passes preflight (`select_start_state` returns its position = the
   fallback-advance count).
4. Chain 0 = the MAP constrained state (fresh model, `torch.manual_seed(42)`,
   `fit_map(n_iter=300, lr=0.05)`, then `_map_init_values`), frozen /
   preflighted / serialized / hashed like the others and launched via
   `fit_hmc_e1(init_values=...)` (NOT `init_to_map`). If the MAP start fails
   preflight the CELL is unstartable; an authority draw is NEVER substituted
   for chain 0.
5. Each pool's recomputed band masses AND SEs (`_is_summary`) were verified
   against the D18 record (`runs/prior_sensitivity/stage_a_{config}.json`,
   `prior_is.per_seed.{0,1,2}` and `prior_is.pooled`) at `atol=1e-12`; a
   mismatch or a missing pool is a STOP condition requiring a new addendum,
   never a source switch or auto-regeneration.

**Start-state hashing.** Canonical SEMANTIC serialization (not `.npz`/pickle
file bytes): for the constrained start dict, in sorted-site order, emit
`utf8(site) + 0x00 + uint32_LE(ndim) + int64_LE(dim...)  + float64_LE(values,
C-order)`; `sha256` over the concatenation.

**Authority pools (per config; verified at `atol=1e-12`).** Pinned per pool:
file sha256, semantic array sha256 (`sha256(ths<f8 C || lml<f8 C ||
int64_LE(seed))`), array shapes. Pooled prior-IS band masses ± delta-method
SE (the coverage authority):

| Config | pool shapes | pooled lo | pooled mid | pooled hi | reportable | B |
|---|---|---|---|---|---|---|
| `informative` | `ths (200000,4)` x3 seeds | 0.276812 ± 0.017734 | 0.131009 ± 0.007024 | 0.592178 ± 0.015063 | lo, mid, hi | 3 |
| `toy_elicited` | `ths (60000,4)` x3 seeds | 0.762660 ± 0.004283 | 0.191078 ± 0.003838 | 0.046262 ± 0.000866 | lo, mid | 2 |

`toy_elicited` high band (0.0463 < 0.05) is NOT reportable, so B=2 and the
one filler slot is the largest-mass band's (lo) weighted-q75 draw (R-A). Pool
file/array hashes are pinned in the committed manifest below.

**Realized freeze — per config x chain (shared across td7/td10 of a config).**
Full-precision constrained values, per-site shapes, per-site float64 hex, the
per-pool provenance hashes, and these same hashes are pinned in the committed
artifact `docs/m2br_freeze/start_freeze_v1.14.json`
(sha256 `b1abfa3c244a03f3ce3b5a69782157aad087e01de8b15a9a332de6ab2643d891`),
produced by the deterministic `experiments/m2br_start_freeze.py` (no sampler,
no network).

| Cell(s) | Chain (seed) | Role | Band | q | Realized `(seed,row)` | Fallback | Semantic sha256 |
|---|---|---|---|---|---|---|---|
| V1,V2 `informative` | 0 (0) | MAP | — | — | — | — | `72a7e8916501b8e344383ab547f0889022136e95856ef89f29a22df34a8b215a` |
| V1,V2 `informative` | 1 (1) | band-median | lo | 0.50 | `(2, 39347)` | 0 | `c9f3758458671a26f0c351f6a597d74cead392796f4ff9fe6259331d0d7fd4ad` |
| V1,V2 `informative` | 2 (2) | band-median | mid | 0.50 | `(2, 152981)` | 0 | `2db18020dfc123d8ed0e6b0c2dffc27fc8ae01c58e1e0c0f9eee10b2da309cda` |
| V1,V2 `informative` | 3 (3) | band-median | hi | 0.50 | `(0, 166451)` | 0 | `5cf298a7ad0ac3317442e4e5cb998976dbfd5808025728c2cbb82f5f1de45649` |
| V3,V4 `toy_elicited` | 0 (0) | MAP | — | — | — | — | `e666fbca520969ff8c0a66c33b4cada458d173c46917188f21e75d9ad8bf747b` |
| V3,V4 `toy_elicited` | 1 (1) | band-median | lo | 0.50 | `(0, 43612)` | 0 | `502090658b4ab1ab5832872cc90a36e51c246b1a8effeadb37723a26812f4978` |
| V3,V4 `toy_elicited` | 2 (2) | band-median | mid | 0.50 | `(1, 1491)` | 0 | `a806fa8a18d78f8e595994cdc550facf1abcbfd0310e7cf21bb6fa53e5fcd752` |
| V3,V4 `toy_elicited` | 3 (3) | filler | lo | 0.75 | `(0, 53543)` | 0 | `c965203c21997abdd593735bd4cfec75884574c65320be2de2247a4085776c48` |

Start states depend only on config (not tree depth), so V1 and V2 share the
`informative` set and V3 and V4 share the `toy_elicited` set; the identical
per-chain sha256 across the shared cells is the invariant. Every authority
start's target-quantile draw passed the D30 preflight (finite E1 potential and
first gradient, round-trip `<= 1e-10`, no terminal NotPSD), so every
fallback-advance count is 0 and every realized index equals its target index.
Both MAP starts passed preflight; no cell is unstartable.

**Verification standing at this addendum (Commit A).** The freeze was built by
codex gpt-5.6-sol (xhigh) and independently recomputed from scratch by Fable
(a separate implementation of R-A + details 1-4 and the hashing convention,
not importing the freeze script): both reproduce every realized `(seed,row)`
index, every fallback-advance count, and every semantic sha256 byte-for-byte,
including chain 0, and both confirm the `atol=1e-12` pool verification and the
four-site topology. The THIRD, formally independent clean-room codex
recomputation is the gate; its byte-identical result is recorded in the
pre-run D-entry (Commit B). No chain of any layer launches until Commit A and
Commit B both exist and the clean-room recomputation matches.

**What this addendum does NOT change or authorize.** No battery value, no
budget, no acceptance criterion, no audit run list, no cell design; no gate of
§6.7; no §6.5/§6.6 relaxation. It authorizes no HMC run, no VI, no
`hmc_laplace`, and no Mauna access. It pins realized start states only.

---

## v1.15 — provenance erratum: R-A/R-B ratification is D32 (a later explicit author message), not D31 — 2026-07-12

**Prereg anchor:** v1.14 (this file), Notes/DECISIONS.md D31/D32, §6.16. This is
a PROVENANCE-ONLY erratum. It changes NO value, start state, hash, criterion,
budget, run list, or cell design; it corrects an attribution in v1.14.

**Correction.** v1.14 labelled the filler-selection rule R-A and the
replacement-number aggregation rule R-B as "author-ratified, D31 own-words
vote". That attribution is wrong. D31 (v1.13) ratified decision-table rows 8
and 9 — the multi-chain validation layer's overdispersed-start design and the
NotPSD policy. It did NOT contain R-A or R-B, which specify (a) the exact
slotting of the `3-B` filler slots to the largest-mass band's weighted-q75
(B=2) or weighted-q25+q75 (B=1) draws, and (b) the 800-row pooled-with-one-
final-normalization primary estimator. R-A and R-B were stated and explicitly
ratified in the author's SUBSEQUENT message (the M2bR execution instruction)
and are formally recorded in **D32**, the pre-run gate entry.

**Layering, stated correctly.**
- v1.11-v1.13 froze the BASE RULE: chain-0 MAP plus overdispersed
  authority starts, one weighted-median draw per reportable noise band
  (mass >= 5%), q25/q75 fill "when fewer than three bands", the D30 preflight,
  and the deterministic next-eligible fallback (D29/D30; rows 8-9 ratified at
  D31).
- v1.14 froze the EXPLICITLY-RATIFIED REFINEMENTS on top of that base: R-A's
  exact filler slotting, R-B's pooled aggregation, and deterministic details
  1-5 — all ratified in the author's later message and recorded in D32. The
  realized pool indices, fallback-advance counts, and per-state hashes in
  v1.14 are unchanged and remain the governing freeze.

**Effect.** Read every "D31 own-words vote" attached to R-A/R-B in v1.14 (and
any similar phrasing) as "explicitly ratified in the author's later M2bR
message; formally recorded in D32". Nothing else in v1.14 is amended; the
manifest `docs/m2br_freeze/start_freeze_v1.14.json`
(sha256 `b1abfa3c244a03f3ce3b5a69782157aad087e01de8b15a9a332de6ab2643d891`)
and all eight pinned starts stand.

**What this addendum does NOT change or authorize.** No value, start, hash,
criterion, or budget. No run of any layer. Toy-only; §6.5/§6.6 continue to
govern.

---

## v1.17 — M2c G-toy/profile algorithm freeze: normalized profile-integration algorithm, HMC-independent references, estimator-specific goldens + tolerances, and the five §6.15 M2c predicates (author umbrella vote) — 2026-07-13

**Prereg anchor:** §6.9 (G-toy goldens; profile band-mass caution L657-666), §6.15 (the seven M2c
predicates L819-828, incl. "G-toy per-estimator numeric tolerances" and "Corrected normalized
profile-Laplace band masses"), §6.8 (two-reference arbitration), §6.7 (G-A M1 pre-check, G-B
divergence), §7 A1, D38/D39, and the D22-D24 correctness chain. Provenance: the author cast an
explicit own-words **umbrella vote (2026-07-13)** ratifying the complete P7 package as revised in
rev-5, after directional ratification of P1-P8 (D39) and the J1-J4 decisions + three
freeze-precision corrections. No pilot, posterior, Mauna, or holdout access exists or is authorized.

**Numbering.** This is the M2c ALGORITHM freeze. It is **v1.17**, not v1.16: v1.16 is the M2bR
run/protocol label (manifests `docs/m2br_freeze/v116_*.json`; D34/D36 titles), never an addendum, so
the addenda sequence goes v1.15 → v1.17 (P4). The post-compute RESULT freeze is **v1.18**.

**Frozen complete specification (byte-exact).** The full algorithm, protocols, tolerances, references,
predicate specs, and manifest schemas are frozen as `docs/m2c-freeze-package-PROPOSAL.md` (rev-5),
pinned at

```
sha256 c3e9db66e189b2a8cad19bf11b5c4acc6518d4b6d2597ae93b0f700587d1ce3f
```

The key frozen values are inlined below; the pinned document governs on any detail. Adversarial
review before this freeze: 5 codex gpt-5.6-sol (xhigh) rounds + 1 independent repo-reading subagent,
every finding cross-verified against source (two math errors — directional-curvature sign, Q2 IACT
global shift — caught and fixed pre-freeze).

**1. HMC-independent references (all D22-unaffected; §2 of the package).** prior-IS pooled toy_elicited
band masses **0.762660±0.004283 / 0.191078±0.003838 / 0.046262±0.000866** (primary authority; hi
0.0463<5% → B=2); RW-MH pooled **0.815644 / 0.161078 / 0.023278**, half-range SE **0.023483 /
0.017650 / 0.010167** (fallback authority / referee); SIR Sin+Linear **0.441±0.005** (Q2) + hard-win
**0.696-0.707** (Q3). prior-IS + SIR = ONE IS family (not double-counted). Corrected-NUTS D33 V3/V4
(Sin+Linear 0.4205/0.4220; occ ~0.76/0.19/0.05) = cross-check ONLY, never a tolerance-setter.

**2. Normalized profile-integration algorithm (§4 of the package).** Corrected `_profile_band_masses`
= exact band-edge nodes (0.15/0.30 toy; Mauna q25/q75 via exact-quadratic CDF inversion) + float-safe
exact partition (total := Σ band_int) + normalization (Σ P_b ≡ 1). Grid r = (1.2/0.005)^(1/39).
**Staged full-domain cap-SENSITIVITY (NOT a proven bound):** always evaluate the full [1e-7, 1e4]
domain (182 nodes) as the reported result; final one-sided δ_tail^upper = |P([1e-7,1e4]) −
P([1e-7,1e3])|, δ_tail^lower = |P([1e-7,1e4]) − P([1e-6,1e4])|; **STOP if either ≥ ε_domain = 1e-4**;
earlier decade stages diagnostic-only. Nested geometric-midpoint refinement, δ_quad^(ℓ) < ε_grid =
1e-4, L_max=3. **Profile-gradient battery (P1):** functional (`functional_call`) gradient validated vs
central FD (1e-4 abs + 1e-4·scale) + D23 sentinel. **Optimizer:** L-BFGS-B (maxiter 500, maxfun 5000,
ftol 1e-12, gtol 1e-8), mandatory stationarity τ_stat=1e-4, 1 jittered restart then STOP.
**Curvature (v1.8 §3 shared protocol):** K = −H by central differences of the validated gradient
(never create_graph); h-sweep {5e-4,1e-3,2e-3}, center 1e-3, logdet-stability 1e-3, symmetry 1e-6,
directional check 1e-3 (RNG numpy default_rng seeds {200,201,202}, float64, unit-L2, order ls/os/lv);
**SPD + rcond = λ_min/λ_max ≥ 1e-8, NO eigenvalue flooring, retry-once-then-STOP (J1).** Measure =
linear noise space. δ_tail is cap-sensitivity, not a bound; the certified tail-envelope
(L_max · ∫ LogNormal tail) is the documented rigor-if-wanted alternative, not adopted.

**3. Chain-aware MCSE_strategy (§3).** Moving-block bootstrap on the **Q2 soft-contribution series**
c_t = exp(−G_{t,j*}/τ − M_global) (single global shift), NOT the Q3 hard winner; ℓ = ⌈2·τ_int⌉
(UNDETERMINED if <2 distinct blocks), B=1000, seed 20260712; kept separate from the MCSE≤0.02 G-C
precision gate and the W5 pool scatter.

**4. Numerical-error reporting (§4).** The deterministic profile masses carry **numerical
sensitivity estimates** δ_quad/δ_hess/δ_tail reported separately — **never an SE, never a proven
bound** (an optional max is a heuristic envelope).

**5. Estimator-specific G-toy goldens + tolerances (§5 of the package + architecture doc §5).** Tied
to independent-reference MC error (prior-IS delta-SE / RW-MH half-range / SIR bootstrap MCSE) and the
frozen §6.8/§6.15 conventions; never to E1/S1f/S2/S3 own output. Q2 agreement = |p_strat − p_SIR| ≤
2√(MCSE_strat² + MCSE_SIR²) (MCSE_strat chain-aware, §3), separate from the MCSE≤0.02 precision floor.
S1 0.696-family = HISTORICAL-only (no new legacy run). S4 Q2 vs SIR 0.441 = diagnostic-only (base §6.9
L668).

**6. The five §6.15 M2c predicates (§5.1-5.5 of the package).** S2 mass-convention (first-order FD
Hessian, whitening M=H, λ_min≥1e-6/n_clipped=0, skew 1e-5, step-stability **1e-3 (J2)**, oracle
diag(1,4,9) 1e-10); S3 Jacobian/equivalence (7-coord, volume-preserving log|det ∂u/∂z|=0, M0-only, 33
states, v1.4 envelopes); divergence non-clustering (rate 0.001 + chain-concentration factor 3 +
per-chain 10% time-window; parameter-band clustering UNEVALUABLE without a schema extension);
spectral/covariance overlap (centered alignment tr(AB)/√(tr A² tr B²), K_rest EXCLUDES M1, cap
q_overlap≤0.05, **alignment 0.90 (J3)**; M1 Matern builder is NEW implementation, UNVERIFIED); M1
nugget-floor (p_below^{M1} > 0.05 flag vs 1.9e-4 variance, **REPORT-ONLY (J4)**, not blocking).

**7. Manifests (§6).** Two append-only manifests: immutable **v1.17** algorithm manifest (JSON-Schema,
every reference/tolerance/predicate + each algorithm sub-object carries a named test) and a separate
**v1.18** result manifest referencing the v1.17 manifest sha256. Neither is produced by this freeze;
v1.18 follows the gated deterministic recompute.

**Two-stage sequencing (P4).** v1.17 (this addendum, algorithm) → the gated deterministic profile
recompute (a SEPARATE explicit author `--execute`, then stop-and-report) → v1.18 (result addendum,
corrected band-mass values + numerical sensitivities). The corrected profile triplet is NOT quoted
here; the historical buggy triplet (persisted 0.76262/0.13752/0.02311, sum 0.9232; §6.9 rounds to
0.763/0.138/0.023) is retained as HISTORICAL-only provenance.

**Implementation owed before the recompute (disclosed, not authorized here):** the S2 fixed-metric
path, the M1 Matern builder, and the profile functional-gradient path are NEW code; the P3 grid
amendment (full [1e-7,1e4] domain + nested refinement) amends the frozen "profile grid 40 points"
(§6.15 L811) and is ratified by this umbrella vote via §6.16.

**What this addendum does NOT change or authorize.** No §6.7 gate value, no arm, no candidate set, no
M2bR frozen artifact (drivers, manifests, protocol docs, committed D-entries), no §6.5/§6.6
relaxation. It authorizes **NO** compute, recompute, sampler run, VI, `hmc_laplace`, or Mauna access;
the 60-month **holdout stays SEALED (§6.6)**. HMC remains available only via `fit_hmc_e1`. The A7
Della vehicle stays on hold (v1.8). Any v1.18 computation requires a separate explicit author
`--execute` authorization.

## v1.19 — M2cR taxonomy freeze: acyclic artifact graph, five-status terminal taxonomy + precedence, environment-freeze manifest, evidence-retention policy (ceilings DEFERRED), B14-stack v5 execution snapshot, authorization ledger + payload-start consumption, and the labeling rule (author ballot, milestone R1) — 2026-07-15

**Prereg anchor:** v1.17 (the M2c algorithm freeze, unchanged and untouched by this addendum), §6.15
M2c predicates, §7 A1, and the D45/D46 chain. Provenance: the author closed the post-D45 **M2cR**
remediation ballot on 2026-07-15, resolving every item B1-B18 in their own words (**D46**), and
separately determined both R1 preconditions SATISFIED on the layered review record (**D46 Update**).
The complete conformed plan governing this addendum is `docs/plan-post-d45-m2cr.md`, pinned at

```
sha256 51b8ec602bc955a619432fd1097012efbfa795e4bccb0a2cc7830d07e1aefbf7
```

The pinned plan governs on any detail. This addendum is milestone **R1** (taxonomy freeze;
documentation and schema design only). No pilot, posterior, Mauna, or holdout access exists or is
authorized. **D45 remains permanently an UNVALIDATED_ATTEMPT** and is never retroactively validated
or reclassified.

**Numbering (B3).** This is **v1.19**, not v1.18. Two facts fix it. (i) **v1.18 is permanently
unused**: it was pre-reserved by v1.17 for the post-compute RESULT freeze, and the D45 disposition
makes both the label and the reserved instance path `docs/m2c_freeze/gtoy_profile_result_v1.18.json`
permanently unused, so the number is burned and the gap at v1.18 is mandated rather than created
here. (ii) v1.16 remains what v1.17 recorded: the M2bR run/protocol label, never an addendum. So the
addenda sequence is v1.15 → v1.17 → **v1.19**. Ballot **B3** ratifies the general rule prospectively:
addendum numbers are assigned **strictly sequentially at ratification time and never reserved in
advance** — precisely so that a conditional amendment which never happens leaves no gap, the defect
v1.18 now exhibits. Schema files carry their own content-kind name and integer `schema_version`. Run
records are named by **kind plus authorization id** and stay **outside** the P4 numeric sequence; the
v1.16 precedent of a run occupying a sequence number is **not** repeated.

**1. Acyclic artifact graph and write order (plan §3.1).** Hash edges point strictly from
higher-numbered to lower-numbered layers. **No artifact contains or implies its own digest. No schema
embeds a hash of any manifest that references it** — the rule prevents cycles, and does not forbid
every manifest digest: schemas may embed the **v1.17 canonical hash** as a `const`, which creates no
cycle because v1.17 references none of them (the pattern the committed
`gtoy_profile_result_v1.18.schema.json` already uses).

- **Layer 0 (frozen content).** **R1 authors** the execution-record schema and the authorization-ledger
  schema plus its JSONL instance. **R2 authors** the v2-gate module(s), the capture driver and
  bootstrap, the dependency lock, and the **v5 environment-freeze artifacts** (§5 below). **R3 authors**
  the diagnostic-record schema and the protocol parameter document.
- **Layer 1a (R2).** The INFRASTRUCTURE manifest pins sha256 of every R2 Layer-0 artifact, including
  the aggregating environment-freeze manifest, **and additionally pins the R1-authored schemas** (a
  downward edge: R1 precedes R2 and neither schema references the manifest). It does not and cannot
  pin the R3 diagnostic schema.
- **Layer 1b (R3).** The PROTOCOL manifest pins the diagnostic-record schema hash and the frozen
  protocol parameter set, and references the Layer-1a hash.
- **Layer 2 (runtime).** Raw evidence: stdout, stderr, `events.jsonl`, per-node records, payload JSON,
  import inventory, `prelaunch.json`, `spawned.json`, `payload_started.json`, per-launch realized
  environment attestations, pytest output where applicable.
- **Layer 3 (runtime).** `RAW_MANIFEST.sha256` over all Layer-2 files, **excluding itself and the
  terminal record**.
- **Layer 4 (runtime).** The terminal record, referencing the Layer-1a/1b hashes, the Layer-2 per-file
  digests, and the Layer-3 digest.
- **Layer 5.** The git commit and the D-entry quote the Layer-4 record's sha256.

**Ledger acyclicity.** The ledger records terminal-record **digests**, while a terminal record's chain
records the authorization by **id string**, never by ledger digest. Record names the grant; ledger
hashes the record. No cycle.

**Frozen write order.** Layer 2 closed, then Layer 3, then Layer 4, each via write-temp, fsync, atomic
rename; commit afterward.

**2. Aggregating environment-freeze manifest (gives `environment_freeze_manifest_sha256` a referent).**
R2 authors a single **environment-freeze manifest** that pins by sha256 the complete v5 freeze set: the
exact frozen child-environment mapping; the complete importable-artifact manifest; the interpreter pin
(version string plus resolved-target sha256); and the pre-boundary attestation set. It carries the one
digest that every diagnostic and result terminal record cites as `environment_freeze_manifest_sha256`
(§7 below). Per-launch **realized** environment attestations are Layer-2 evidence covered by
`RAW_MANIFEST.sha256` and are **not** this static member: a per-launch value differs every run and
could never identify which freeze was used.

**3. Terminal-state taxonomy, per-kind standing, precedence, spawn boundary (plan §4.3; ballot B2).**
Status enum **{COMPLETED, ALGORITHM_STOP, ABORTED_BUDGET, INFRA_FAILURE, NOT_STARTED}**; one record
schema with a closed `oneOf` branch per status. **Scientific standing is a function of (record kind,
status):** a result-kind COMPLETED record is a scientific result; a diagnostic-kind COMPLETED record is
protocol completion only, carrying `not_a_result: true` as a `const`; **ALGORITHM_STOP is reachable
only by result-kind runs**; ABORTED_BUDGET is an interruption, **never a scientific STOP**;
INFRA_FAILURE and NOT_STARTED are non-scientific.

**Frozen precedence (first match wins).** (1) No confirmed spawn yields NOT_STARTED. (2) A
parent-initiated budget kill yields ABORTED_BUDGET, even if capture faults follow the kill. (3) Any
capture, attestation, or environment fault during the run yields INFRA_FAILURE, even if the child also
exited with a protocol code (a capture fault voids certification). (4) A child protocol exit with a
schema-valid payload yields COMPLETED or ALGORITHM_STOP per exit code plus payload validation. (5)
Anything else yields INFRA_FAILURE.

**Spawn-boundary mechanism.** The parent writes `prelaunch.json` before fork; the child bootstrap's
first act is a hello message on the pipe; on receipt the parent atomically writes `spawned.json`. On
child death the parent still assembles an INFRA_FAILURE terminal record over whatever raw evidence
exists. If the parent dies, a reconciliation mode later assembles an INFRA_FAILURE record explicitly
flagged `reconstructed: true`. Nothing vanishes and no state is silently reclassified. The
ALGORITHM_STOP branch's `stop.stage` enum is limited to **{optimizer, gradient_battery, curvature,
refinement, upper_pullback, lower_pullback, tail, edge_interiority}**; budget and infrastructure never
appear in it.

**4. Evidence retention and overflow; ALL numeric ceilings DEFERRED (plan §4.4; ballots B9, B15).**
All certification evidence becomes **committed repository content** at `docs/m2c_evidence/<run_id>/`.
The **authoritative terminal record is committed in the same directory** as that run's evidence and
raw manifest; each run is a **self-contained committed directory**. Local-untracked retention is
**ineligible**; no external store is selected. **Overflow is `INFRA_FAILURE`, never truncation** —
truncated evidence is indistinguishable from complete evidence after the fact. `runs/` remains scratch
and carries **no certification weight**; the D45 bundle stays immutable where it is.

**Deferral (B15(ii)), frozen here as a deferral.** **This addendum sets no numeric evidence-size
ceiling of any kind.** R2 measures the canonical evidence representation, may use **deterministic
chunking**, and proposes **separate** ceilings for attestation manifests, event streams, stdout/stderr,
and the complete bundle. R2 can measure the importable-artifact manifest exactly (a filesystem walk)
and per-event byte size exactly (hermetic runs), and the node count is known; the complete-bundle
ceiling is therefore **derived** from measured components rather than observed from a real run, and
the later addendum must say derived where it derives. Those exact ceilings are frozen in a **separate
versioned pre-execution addendum, before R4**. **Completeness is never weakened to fit a ceiling.**

**5. Execution snapshot and environment — B14-host and B14-stack v5, exactly as ratified (plan §4.5).**
This supersedes nothing in v1.17 and creates no new scientific rule; it governs how a future
authorized execution is snapshotted and attested.

- **Host (B14-host).** The host is recorded and bit-reproducibility claims are scoped to **identical
  host plus lock**. No hostname hard-pinning.
- **Launch.** The **Miniconda base** interpreter at
  `/opt/homebrew/Caskroom/miniconda/base/bin/python3.13`, invoked by **absolute resolved path**, never
  via `PATH` lookup, never via `.venv/bin/python`; `.venv` excluded entirely (it holds only `pip`). The
  resolved target's sha256 is pinned and **re-attested at freeze time**. Flags
  **`-S -s -P -B -X pycache_prefix=<verified-empty run-local dir>`**. **`-I` and `-E` are prohibited**:
  `-I` implies `-E`, which makes CPython ignore `PYTHONHASHSEED`, so the seed never takes effect while
  `os.environ` still reads `"0"` — a false-pass. Spawn is direct with `shell=False`; CWD is pinned to
  the detached worktree root and asserted.
- **Pre-boundary attestation.** Actual sha256 of **every source and native artifact executed before the
  audit boundary**, including the bootstrap closure, pre-boundary `lib-dynload` extensions, the native
  runtimes, `/usr/lib/dyld`, and the active arm64e dyld shared cache (main file plus all declared
  subcaches). The empty `pycache_prefix` **alone is insufficient**: compiling from source only helps if
  the source is integrity-bound. Residual, stated honestly: trust in pre-verification execution and
  kernel/dyld mapping — **not** a claim that on-disk bytes are unhashable.
- **Bytecode.** Fail if any imported module uses `SourcelessFileLoader`; reject orphan/legacy `.pyc`
  candidates at every launch; do **not** require deleting normal `.pyc`. `-B` prevents standard
  import-cache **writes** only; the empty-prefix postcondition is a **consistency check**, not proof
  that `-B` held or that no `.pyc` was read.
- **Path.** `sys.path[:]` **replaced entirely** with exactly four roots (worktree root; base
  `lib/python3.13`; base `lib-dynload`; base `site-packages`), because `-S` startup leaves a
  nonexistent `python313.zip` entry. `.pth`-derived finder paths excluded. Complete canonical equality
  asserted; the canonical worktree root is **permitted at index 0** (it is the pinned CWD); only `""`,
  relative/CWD-derived spellings, and extra aliases are rejected.
- **Environment — staged, exact, dual-view.** *Stage A* (before native imports): exact equality against
  the frozen parent-supplied mapping in **both** `os.environ` **and raw C `environ`** (via
  `_NSGetEnviron`, duplicate keys rejected). Frozen mapping: `PYTHONHASHSEED=0`; `OMP_NUM_THREADS=10`;
  `OMP_DYNAMIC=FALSE`; **`MKL_NUM_THREADS=10`** (operative via ATen precedence even with no MKL
  runtime); `VECLIB_MAXIMUM_THREADS=10`; `LC_ALL=C`; `TZ=UTC`; run-local `HOME`/`TMPDIR`/XDG (realized
  values recorded, integrity-bound per launch); minimal `PATH`. **`OPENBLAS_NUM_THREADS` is dropped as
  empirically inert.** Under `LC_ALL=C`, `LC_CTYPE` is **not** injected — expect its absence; record
  `sys.flags.utf8_mode == 1`. *Stage B* (after the frozen native stack imports and thread controls
  initialize, before payload): accept **only** two explicitly frozen native-runtime deltas — the
  validated `__CF_USER_TEXT_ENCODING` value and exactly one PID-bound `__KMP_REGISTERED_LIB_*` entry
  satisfying a frozen name/value rule; **any other delta is INFRA_FAILURE**. Persist and authenticate
  **separate** post-initialization baselines per view; the two views are **not** required to equal each
  other. *Stage C* (immediately before normal exit): compare each view to **its own** baseline; drift
  or a **missing** postcheck is INFRA_FAILURE.
- **Threads.** **Requested/configured value 10 for each controlled facility.** **No process-wide
  ceiling and no exact physical-worker count are claimed.** Torch intra-op **and inter-op** explicitly
  set to 10 before any parallel work, **failing closed** otherwise. Dynamic threading disabled where
  supported. Backend identity **attested as Accelerate**; a backend change fails closed and requires a
  new environment freeze. **Empirical repeatability is the bit-reproducibility gate**, scoped to what
  it establishes.
- **Completeness.** A **complete frozen importable-artifact manifest** across the four roots (path,
  type, sha256 for source modules, extension modules, legacy/sourceless bytecode candidates, importable
  archives). Reject any **added, removed, or changed** importable artifact **before imports and after
  execution**. Every executed module's **resolved origin and loader class** must match a frozen entry;
  recording import names is **insufficient**. Built-in, frozen, and namespace-package modules are
  classified explicitly. The dependency lock is retained **only as a supplementary check**: dist-info
  RECORD proves listed files' bytes, is **not a completeness manifest**, and does **not cover `.pyc`**.
- **Effect proofs.** Explicit `if not cond: raise SystemExit(...)`; **never** Python `assert` (stripped
  by `-O`); **never** `exit(...)` (site-installed, absent under `-S`). Assert `optimize == 0`;
  `hash_randomization == 0` **plus** a build-pinned **bound** `sentinel.__hash__()` value; `safe_path`;
  `no_user_site == 1`; `dont_write_bytecode == 1`; `no_site == 1`; expected `isolated == 0` and
  `ignore_environment == 0`; canonical `sys.pycache_prefix` equality; and an **audit canary** verified
  immediately after `sys.addaudithook`.
- **Post-execution re-attestation.** Repeat **every** pre-run class; compare raw C `environ` **and**
  `os.environ` (they desynchronize); re-enumerate loaded native images; recheck `sys.path`. Drift or a
  missing postcheck is INFRA_FAILURE. **Parent-side rehashing preferred.**
- **Frozen threat model.** **In scope:** accidental source or environment drift; stale bytecode;
  ordinary native/Python environment mutation; crashes; incomplete capture. **Out of scope, disclosed
  as residuals, never blockers:** malicious same-user mutation-and-restore; kernel compromise; hostile
  dyld/loader behavior; payload code deliberately defeating attestation.

**6. Authorization ledger and consumption semantics (plan §4.3; ballot B10).** A committed,
**append-only** ledger records every grant **and every launch attempt**. Its **canonical form is
schema-validated JSONL**; any `authorizations.md` rendering is **not authoritative**. Append-only
**events**, never a mutable grant row: `authorization_granted`; `launch_attempt_started`;
`pre_payload_terminal_outcome`; `payload_started` (carrying the `payload_started.json` digest);
`terminal_outcome` (carrying evidence and terminal-record digests); `authorization_consumed`, **derived
only from a valid payload-start event** and never a freely typed mutable status. Corrections append
**superseding events** rather than rewriting history. Audit CI validates event ordering, unique ids,
legal state transitions, agreement with committed attempt evidence and terminal records, and the
consumption rule.

**Consumption rule (B10).** `spawned.json` is **process-launch provenance only and does not consume**.
A distinct, **hash-bound** `payload_started.json` is emitted only after all pre-scientific attestations
pass and immediately before the first scientific/model evaluation. **The scientific authorization is
consumed if and only if `payload_started.json` exists.** Once payload starts, **every** terminal
outcome consumes — ALGORITHM_STOP, ABORTED_BUDGET, INFRA_FAILURE, crash, or missing postcheck. A
**pre-payload** infrastructure or attestation failure must still produce and commit an INFRA_FAILURE
record and launch-attempt evidence, but **does not consume**, because no scientific evaluation
occurred. Any relaunch requires **explicit author confirmation and a new launch-attempt id**; never
automatic. Any code, protocol, environment-freeze, or payload change requires the corresponding new
frozen provenance before relaunch. **D45 is recorded as a historical consumed authorization and is not
reinterpreted under this prospective rule.**

**Grace policy.** At the wall-clock ceiling the parent issues SIGTERM, waits 30 seconds, then SIGKILL
if the child has not exited. A parent budget termination remains ABORTED_BUDGET under precedence rule
(2). The parent assembles the terminal record from already-flushed evidence.

**7. Payload-start boundary — a hard R2 obligation (plan §4.3).** R2 must provide a **fail-closed,
hermetically tested** definition proving that: all pre-scientific attestations complete before the
marker; the marker is **atomically and durably** emitted and **hash-bound to the authorization id,
launch-attempt id, exact execution commit, and frozen artifact chain**; **no data generation, MAP
construction, model evaluation, diagnostic evaluation, or result payload can occur before the marker**;
the first scientific operation follows the marker **without another unrecorded phase**; **missing,
malformed, late, or mismatched markers fail closed**; and the ordering tests use **spies/fakes and
remain hermetic, with no scientific computation**. R1 freezes the requirement; R2 owes the proof.

**8. Effective-chain provenance (plan §5.2; ballot B18 + sub).** Every terminal record carries a
`chain` object whose members are **exactly** B18's ratified enumeration, extended by nothing: the v1.17
canonical hash; the infrastructure-manifest hash; the protocol-manifest hash (diagnostic and result
runs); **`environment_freeze_manifest_sha256`** (every diagnostic and result run), binding the record to
the **static** environment freeze of §2/§5 rather than relying only on transitive coverage; the
diagnostic-record sha256 (result runs); the amendment-manifest hash or an explicit `"none"` (result
runs); the exact execution commit; and the authorization **id string**. The audit CI verifies each member
against the committed artifacts.

**`diagnostic_record_sha256` referent, pinned (author determination, 2026-07-15).** It is the sha256 of
the **R3 diagnostic-record INSTANCE** governed by `m2c_diagnostic_record.schema_v1.json` (§5.1; authored
in R3), **not** the diagnostic-kind terminal record. This follows the plan's literal terminology and
preserves the R3-to-R5/R6 dependency. **No separate terminal-record hash is added**, because no ratified
requirement demands one; whether a result record should additionally cite the diagnostic-kind terminal
record is **flagged for a later author decision** and is not decided here.

**Launch-attempt binding, outside the chain (author determination, 2026-07-15).** `launch_attempt_id` is
a **required top-level field of every terminal record**, deliberately **not** a chain member: B18's chain
enumeration is ratified and is **not silently extended**. Binding is preserved regardless, because the
record is hashed as a whole and the ledger cites terminal records by digest, so the digest covers the
top-level field. Under §6 a single grant may carry several launch attempts, so recording which attempt
produced a record is necessary; doing it outside the chain keeps B18 intact.

The chain's members are **exactly** that enumeration. `launch_attempt_id` is deliberately **not**
among them (author decision, 2026-07-15, resolving the R1 stop question, option (c)): every terminal
record instead carries `launch_attempt_id` as a **required top-level field** on every branch, where it
remains hash-bound to the record because the ledger cites terminal records by digest and that digest
covers every top-level field. The binding therefore holds **without silently extending the ratified
chain**. The diagnostic-record member is the SHA-256 of the **diagnostic-record instance governed by
`m2c_diagnostic_record.schema_v1.json`**, the R3-authored artifact §5.1 names (author decision,
2026-07-15, following the plan's literal terminology and preserving the R3-to-R5/R6 dependency); it is
never the digest of a terminal record. The diagnostic-kind terminal record is a distinct artifact,
cited by digest in the ledger's `terminal_outcome` event, and admitting it as a chain member would
require a separate author decision; no ratified requirement presently demands one.

**9. The Layer-2 v2 per-node record contract (author determinations, 2026-07-15).** **R1 owns and freezes the
complete contract; R2 owns the v2-gate implementation that emits those records and the non-self-certifying
completeness tests comparing emitted fields against this contract.** Reconciled with §1: **Layer 2 continues to
store the full raw per-node records; Layer 4 continues to carry only their digests** and never embeds a per-node
record. The contract is a set of closed reusable `$defs` inside the single execution-record schema, **directly
addressable by JSON Pointer** (`#/$defs/per_node_record`, `#/$defs/two_start_optimizer_record`,
`#/$defs/battery_record`, `#/$defs/curvature_record`, `#/$defs/curvature_evaluation`, `#/$defs/retry`) so R2 can
validate Layer-2 files against them. **No additional schema file is created.** The frozen nonfinite sentinel rule
applies recursively to every numeric scalar in these definitions; scientific summary fields (§8's result payload)
remain finite-only. R1 freezes the contract only: **no emitters, gates, serializers, or completeness walkers**.

- **Serialization, not science.** These determinations fix representation. They alter **no** scientific formula,
  frozen gate, continuation rule, retry behavior, or verdict logic.
- **Optimizer starts versus attempts (diagnosis H-d).** The frozen gate iterates **two starts** in frozen order
  `(warm, mode)` (`profile_integration.py:438`), and each start issues an original `minimize()` call plus, if
  that call returns a non-zero status, a **jittered restart that overwrites the original result**
  (`:446-456`) — discarding exactly the failed first call's telemetry. Accordingly the contract records
  `starts` as a fixed-order two-element array, and **each start carries every call it issued**: element 0 is
  always the original, element 1 is the jittered restart and is present if and only if the original failed,
  never more than two (the frozen gate restarts at most once). This is what §3.2 requires — "`attempts` **per
  start**", with the equivalence obligation demanding "v2 **additionally exposing the attempts the frozen gates
  discard**" — and it is what recovers the H-d evidence. Ballot **B12(i)**'s "preserve … both optimizer
  attempts" is a floor, satisfied a fortiori. The restart attempt's **jitter provenance is structurally
  required**, and the frozen RNG seed is `RESTART_RNG_BASE + START index`, so exactly `{300, 301}` are
  realizable.
- **`logdet_by_h`** is a fixed-order **array** of closed `{h, logdet}` records ordered exactly by frozen
  `HESS_H_SWEEP = (5e-4, 1e-3, 2e-3)` — never an object with float-string keys. `h` is a finite plain number
  fixed to its sweep value; `logdet` takes the numeric-or-sentinel form. Missing, duplicate, extra, off-sweep, or
  reordered entries are rejected.
- **Directional evidence** is a fixed-order **array** of closed `{seed, direction, second_difference, error}`
  records ordered exactly by frozen `DIRECTION_RNG_SEEDS = (200, 201, 202)` — never integer-string map keys.
  `direction` is the realized canonical-axis vector actually used. Missing, duplicate, extra, or reordered seeds
  are rejected.
- **Warm-start identity** is a **closed tagged object**, never an opaque string or hash: exactly
  `{"kind":"mode_u"}` or `{"kind":"accepted_node","stage_id":…,"node_index":…}`. Every per-node record carries
  both `incoming_warm_start` and `outgoing_warm_start`, each with the tagged identity, the realized warm-start
  vector in canonical axes, and a `selection_reason` distinguishing initial `mode_u`, accepted current node,
  carried last accepted node, and carried `mode_u`. An accepted node's outgoing identity points at that node; on
  optimizer failure the outgoing identity and vector equal the incoming ones. **This makes the complete
  continuation trajectory reconstructable without self-hashes or external inference** (ballot B12(i)).
- **Retry telemetry** is a **closed tagged union**: `{"fired": false}`, or a `fired: true` branch carrying the
  frozen trigger (SPD/rcond conditioning failure only), the complete retry-optimizer telemetry (status, reported
  success, message, candidate vector, objective, gradient, stationarity), **every positive-acceptance conjunct as
  an explicit boolean**, required and observed shapes, candidate finiteness, whether the fallback fired, and the
  fallback target (`pre_retry_optimum`). Wrong-shaped and nonfinite candidates stay representable via explicit
  observed-shape metadata and the frozen sentinels; **no arbitrary Python repr is serialized**. The post-retry
  evaluation is recorded in full, including when it evaluates the fallback point, and **cannot appear without a
  fired retry**.
- **Battery record** carries the aggregate frozen `scale`, the aggregate `pass`, and a fixed canonical-order
  array for `ls`, `os`, `lv`; per coordinate: role, the realized FD step from the frozen rule, reference value,
  functional value, absolute error, the frozen threshold, and pass. The aggregate pass equals the conjunction of
  the three coordinate passes; **R2 must test that invariant**.
- **Jitter provenance** records the frozen RNG seed (`RESTART_RNG_BASE + index`), the frozen jitter scale, the
  base start vector, the realized jitter vector (the applied offset), and the resulting start vector, all in
  canonical axes. **R2 must test the invariant** that the resulting vector equals base plus jitter. This is
  provenance, **not a new optimizer decision**.
- **Axis order.** All persisted numerical vectors, gradients, directions, Hessians, eigenvector-indexed material,
  starts, optima, and comparison points use **canonical `(ls, os, lv)`** axes, with matrices conjugated
  accordingly (ballot B1). The ambiguous persisted field name `nuisance_order` is **not used**. Records instead
  carry `persisted_axis_order`, a `const` of `["ls","os","lv"]`, and `computation_storage_order`, the three E1
  site names in their computation order — preserving the frozen source/storage provenance **without** changing
  persisted array order. **R2 must test the permutation and matrix conjugation in both directions.**

**Artifacts frozen by this addendum.** `docs/m2c_freeze/m2c_execution_record.schema_v1.json` (Draft
2020-12; closed `oneOf` per status; per-kind standing; the §8 chain; the §9 Layer-2 v2 per-node record contract;
element-level nonfinite sentinels; strict finite JSON; `additionalProperties: false` throughout; **no
quantiles**),
`docs/m2c_freeze/m2c_authorization_ledger.schema_v1.json`, and
`docs/m2c_freeze/m2c_authorization_ledger.jsonl` (initialized with the D45 historical consumed entry).
The **R3 diagnostic-record schema is not authored or stubbed here.**

**What this addendum does NOT change or authorize.** It changes **no v1.17 value, tolerance, gate,
reference, predicate, or algorithm**; no §6.7 gate value, arm, or candidate set; no M2bR or M2c frozen
artifact (`gtoy_profile_freeze_v1.17.json`, `gtoy_profile_result_v1.18.schema.json`, the rev-5 package,
drivers, committed D-entries); no §6.5/§6.6 relaxation. It sets **no numeric evidence ceiling** (§4).
It authorizes **NO** compute, recompute, diagnostic, profile, optimizer, gradient, Hessian, curvature,
MAP, sampler, VI, `hmc_laplace`, or Mauna access, and **no `--execute`**; the 60-month **holdout stays
SEALED (§6.6)**. **R2 is not begun and is not authorized.** The reserved v1.18 result-instance path
stays **ABSENT** and the **v1.18 label stays permanently unused**. Every future execution requires its
own fresh explicit author authorization, recorded in the §6 ledger.

## v1.20 — M2cR R2a: exact per-class evidence-size ceilings FROZEN (B15(ii)); R2a scope amendment to one bounded operationalization milestone; enforcement semantics; measurement-provenance correction mandate (author ballot, milestone R2a) — 2026-07-18

**Prereg anchor:** v1.19 (the R1 taxonomy freeze, unchanged), v1.17 (untouched), and the D45/D46/D48
chain. Provenance: PR #16 merged R2 at `9bb246714f6c64f0a5e65e9afbc50fef627dbc54` (D48 Update 12 and
its closure update); an independent preflight verified every figure in
`docs/m2cr-r2-evidence-size-report.md` (arithmetic, on-disk artifact sizes, entry counts, hermetic
measurement suite 13/13) and audited enforcement ownership; the author then cast the ballot recorded
in **D49**, which this addendum freezes. The governing plan remains `docs/plan-post-d45-m2cr.md`,
pinned at

```
sha256 51b8ec602bc955a619432fd1097012efbfa795e4bccb0a2cc7830d07e1aefbf7
```

**Numbering (B3).** This is **v1.20**, the next sequential number after v1.19, assigned at
ratification per the B3 rule. The addenda sequence is v1.15, v1.17, v1.19, **v1.20**; v1.16 remains a
run/protocol label, v1.18 remains permanently unused.

**1. Frozen per-class ceilings (B15(ii) resolved; exact byte values, ratified).** Every value is an
exact byte count; mebibyte figures appear only as parenthetical gloss.

| Class | Ceiling (bytes) | Gloss |
|---|---|---|
| runtime-envelope/static-artifact **per-file** | **33,554,432** | 32 MiB |
| event stream (`events.jsonl`), per run | **33,554,432** | 32 MiB |
| `stdout.txt`, per run | **16,777,216** | 16 MiB |
| `stderr.txt`, per run | **16,777,216** | 16 MiB |
| complete per-run evidence bundle | **134,217,728** | 128 MiB |

Basis, labeled per plan §4.4 ("say derived where it derives"): the per-file ceiling holds ×3.84 over
the largest measured static artifact (the 8,744,319-byte importable manifest, measured); the event
ceiling holds ×3.72 over the derived structural worst-case stream (9,016,328 = 6,088 × 1,481,
derived from a measured exemplar); the bundle ceiling holds ×7.53 over the derived measured-basis
subtotal (17,830,263, derived); stdout/stderr have **no measured basis by design** (caller
allowances, set here on structural grounds). A 256 MiB bundle alternative was **rejected** (D49):
128 MiB already provides substantial headroom while retaining useful fault detection and limiting
committed repository growth. None of these figures is a proven maximum over all runs (the
optimizer/retry `message` string is schema-unbounded); if a legitimate complete run ever exceeds a
ceiling, the remedy is a **larger ceiling in a later versioned addendum**, never truncation and
never reduced completeness.

**2. Exact scope of each ceiling (the precise operational interpretation of plan §4.4's class
list).** Plan §4.4's "attestation manifests" class is operationalized as the
**runtime-envelope/static-artifact per-file** class, a per-file ceiling covering:

1. **each committed static freeze artifact** — the artifacts pinned by the infrastructure manifest's
   artifact table (including the evidence-ceilings artifact of §5), plus the infrastructure manifest
   file itself — checked at **regeneration/audit time**, never counted toward any per-run bundle; and
2. **every per-run `RUN_DIR_EVIDENCE_CLASSES` member classified `fixed_runtime` or `conditional`**,
   including `RAW_MANIFEST.sha256` and the **candidate terminal record** (its exact serialized
   bytes; see §3), checked at the per-run decision point.

`events.jsonl`, `stdout.txt`, and `stderr.txt` use their dedicated per-run ceilings above. The
`nodes/` subtree and the run-local `home/`, `tmp/`, and `xdg/` scratch directories carry **no
separate class ceiling or allowance** and count toward the complete-bundle ceiling only. `pycache/`
remains required empty (Stage C; unchanged). The complete per-run bundle is governed as one
aggregate per run directory under `docs/m2c_evidence/<run_id>/`; static freeze artifacts are
governed separately and are **not** part of any per-run bundle. **No chunking exists and none is
introduced; truncation is never permitted.** Per-file and per-class-instance therefore coincide.

**3. Counting and canonicalization rules.** A file's size is its exact on-disk byte count
(`st_size`, the measurement `bistar_gp/m2cr/measure.py::measure_file` reports). The **candidate
terminal record** is priced at the exact byte length of its canonical JSON serialization (the same
bytes the atomic publisher writes). The **complete per-run bundle** is the sum over **every retained
regular file beneath the run directory** (recursive; directories themselves excluded; the root
terminal-record path excluded from the on-disk sum) **plus** the candidate terminal record's
serialized bytes — so the count includes `RAW_MANIFEST.sha256`, the terminal record, every nested
`nodes/` and scratch file, and any unclassified stray file (strays carry no per-file ceiling but can
never escape the aggregate). The per-file class map is derived at decision time from
`classify_run_dir_layout(RUN_DIR_LAYOUT)`, which **fails closed** if any layout member lacks a
classification, so a newly introduced run-directory evidence file cannot escape classification or
size accounting.

**4. Overflow decision protocol (B15(iii) operationalized; ratified).** For every launch the parent:

1. closes Layer-2 evidence (frozen write order unchanged);
2. constructs and writes `RAW_MANIFEST.sha256` (Layer 3, unchanged);
3. assembles the **candidate terminal record** for the outcome the ratified §4.3/B2 precedence
   selects;
4. computes the candidate sizes: every per-file class check of §2, the dedicated `events.jsonl` /
   `stdout.txt` / `stderr.txt` checks, and the complete-bundle sum of §3, **including** the candidate
   terminal record;
5. if any class or total ceiling is exceeded, **replaces the candidate outcome with an
   `INFRA_FAILURE` record carrying `fault_class: "evidence_overflow"`** and publishes it over the
   complete retained evidence — **nothing is truncated, deleted, or omitted**; the oversized bundle
   is retained and committed in full. Overflow voids certification, not retention.

**Candidate rule.** The decision consumes the candidate's sizes exactly once. The
scientific/protocol outcome is **never reconsidered** because the smaller replacement
`evidence_overflow` record would bring the final retained directory below a ceiling: the attempted
candidate exceeded the ceiling and remains failed. The replacement record is not itself re-priced
(no recursive or self-referential size semantics).

**Precedence interaction (B2 unchanged; first match wins).** Candidates selected by precedence rule
(4) — a protocol exit yielding COMPLETED or ALGORITHM_STOP — are replaced outright on breach, the
displaced candidate status recorded in the fault detail. Candidates already `INFRA_FAILURE` (rules
(3)/(5), assembly fallback, reconciliation) keep that status with `fault_class` elevated to
`evidence_overflow` and the displaced fault class and detail preserved in the detail text. Rule-(1)
`NOT_STARTED` and rule-(2) `ABORTED_BUDGET` candidates keep their ratified statuses: B2's
first-match precedence is not amended here (rule (2) explicitly survives capture faults that follow
the kill, and the untouched closed R1 schema gives those branches no fault object); neither status
is scientific or certifiable, and the oversized evidence remains committed and visible. Authorization
consumption is unchanged and continues to depend **solely** on `payload_started.json` (v1.19 §6).

**Fault detail contract.** The `evidence_overflow` detail identifies, for every breach, the
applicable class, the offending path (or `complete_bundle`), the observed candidate bytes, and the
ceiling bytes, plus the displaced candidate outcome; the breach enumeration is structurally bounded
by the fixed class set and cannot recurse.

**Coverage.** The protocol applies to the normal capture terminal path, to the post-authentication
last-resort envelope (fault-class elevation, within the last-resort detail limit), and to
**reconciliation** (`reconcile_run`), which authenticates the ceilings from the captured
`prelaunch.json` provenance (worktree root plus chain-bound infrastructure-manifest digest). If
reconciliation cannot authenticate the pinned ceilings artifact (for example the freeze-time
worktree no longer exists), the reconstructed `INFRA_FAILURE` record is still published with that
unavailability disclosed in its detail: recovery is never blocked, and the record is non-certifiable
either way. Failures **before** launch-spec authentication succeed carry no authenticated ceiling
values and publish as today; every such outcome is already a non-consuming `INFRA_FAILURE`.
Enforcement is operative from successful launch-spec authentication onward. **Static-artifact
overflow fails regeneration/audit CI** (the committed-tree audit checks every §2-scope static file
against the per-file ceiling).

**5. One authenticated machine-readable source of truth.** The five ceilings are frozen in a new
committed Layer-0 artifact, `docs/m2c_freeze/m2cr_evidence_ceilings_v1.json`
(`kind: "m2cr_evidence_ceilings"`, `schema_version: 1`, `addendum: "v1.20"`, and a closed `ceilings`
object with exactly five integer members). The infrastructure manifest pins it as the
`evidence_ceilings` artifact; `_authenticate_launch_spec` resolves and digest-verifies it under the
launch worktree, validates it closed-world, and carries the values on the spec (spec-digest-bound),
so parent-side enforcement and the audit tooling consume **only** this artifact — no independently
editable duplicate constants exist in code. This addendum records the ratified values; the committed
artifact is the machine authority; the audit CI asserts the two agree.

**6. R2a scope amendment (explicit author act, D49).** Plan §8 defined R2a as a versioned
pre-execution addendum only. The author **explicitly amends R2a once** so the milestone owns, as one
bounded unit: (1) this docs-first v1.20 numerical freeze, and (2) the **narrowly scoped enforcement
required to make these values operational** — the ceilings artifact, its infrastructure-manifest
pin, the §4 decision protocol in the capture/reconciliation paths, the static audit checks, their
hermetic tests, and the resulting artifact regeneration. This is an explicit amendment to the prior
addendum-only wording, **not** a silent reinterpretation of R2 or R3; R2 remains otherwise frozen,
and R3's charter is untouched. Within one branch and PR, **freeze-before-implementation** holds:
v1.20 and D49 are committed first; enforcement follows in subsequent commits; **R4 remains blocked
until the complete R2a PR merges.** No further hardening round of R2 is opened beyond this bounded
scope.

**7. Measurement-provenance correction (truthfulness).** The R2 report's claim that
`tests/test_m2cr_measure.py::test_evidence_size_report_figures_reproduce` deterministically
reproduces its measured exemplars presently holds only for 3,179 and 1,613. R2a must either extend
the hermetic tests to **reproduce 5,894 / 3,029 / 6,088 / 84,921 from the fixture/serializer path**
(compared against separately written expected integers, never by copying report constants into a
tautology) or, for any figure that cannot be reproduced independently, **correct the current report**
instead of freezing the unsupported value, recording the correction in D49. Historical D48 text
remains historical.

**What this addendum does NOT change or authorize.** It changes **no v1.17 value, tolerance, gate,
reference, predicate, or algorithm**; no frozen M2bR/M2c artifact; **no R1 schema** (the
`evidence_overflow` enum member and every closed branch stand exactly as frozen in v1.19; the
unbounded optimizer/retry `message` field remains unbounded); **no B2 precedence row**; no gate,
serializer, event, or record contract. It authorizes **NO** compute, recompute, diagnostic, profile,
optimizer, gradient, Hessian, curvature, MAP, sampler, VI, or Mauna access, and **no `--execute`**;
the 60-month **holdout stays SEALED**. **R3 is not begun and is not authorized; R4 requires its own
fresh grant and is blocked until the R2a PR merges.** The v1.18 label stays permanently unused.

## v1.21 — M2cR R3: diagnostic protocol and decision-rule freeze — §6 verbatim (coverage, continuation, frozen formulas, total decision table), diagnostic-record schema + instance residence, protocol parameters + Layer-1b PROTOCOL manifest, Layer-1b launch/audit enforcement, rows 1–10 evaluator, coordinate goldens (author ballot, milestone R3) — 2026-07-18

**Prereg anchor:** v1.19 (the R1 taxonomy freeze, unchanged), v1.20 (the R2a ceilings freeze,
unchanged), v1.17 (untouched), and the D45/D46/D48/D49 chain. Provenance: PR #16 merged R2 at
`9bb246714f6c64f0a5e65e9afbc50fef627dbc54`; PR #17 merged R2a at
`35ccc3d3e871a864b081d10e6ca7db53b0cbd5fe`; a fresh read-only R3 preflight at that head verified the
startup gate (tracked tree clean; reserved v1.18 instance absent; fixture authorities byte-faithful
to the plan's §6 citations) and produced a requirement-to-artifact map; the author then cast the R3
ballot recorded in **D50** (items A1, B, C, 2026-07-18), which this addendum freezes. The governing
plan remains `docs/plan-post-d45-m2cr.md`, pinned at

```
sha256 51b8ec602bc955a619432fd1097012efbfa795e4bccb0a2cc7830d07e1aefbf7
```

The pinned plan governs on any detail. **D45 remains permanently an UNVALIDATED_ATTEMPT.**

**Numbering (B3).** This is **v1.21**, the next sequential number after v1.20, assigned at
ratification. The addenda sequence is v1.15, v1.17, v1.19, v1.20, **v1.21**; v1.16 remains a
run/protocol label, v1.18 remains permanently unused.

**1. Milestone scope.** R3 is the diagnostic protocol and decision-rule freeze of plan §8, PLUS the
orchestrator-v2 composition that the R2 implementation map's scope rule explicitly deferred "with
the protocol work it depends on (§6 is frozen in R3)" — plan §7 makes R4 execution-only, so the
executable diagnostic payload must exist, hermetically tested, before any R4 grant. R3 is hermetic:
**no `--execute`, no diagnostic or scientific computation, no real-model evaluation, no
profile/optimizer/gradient/Hessian/MAP/sampler execution outside the pre-existing hermetic suite,
no Mauna or holdout access, no ledger event, no run directory, no v1.18 instance.** Every R3 test
drives the new code with fakes, rigged oracles, and injected data only.

**2. Probe coverage and continuation (plan §6.1; ballots B7, B12(i)).** **Coverage is full
deterministic verdict closure:** the sorted union of the level-0 grid with toy edges, its nested
refinements to `L_max = 3`, and **both one-decade pullback grids** — upper cap `1e3`, lower cap
`1e-6`, exactly the caps of the frozen `δ_tail` definition — refined to `L_max = 3`. The level-3
refined full grid has `8 × (184 − 1) + 1 = 1,465` nodes and each refined pullback adds at most about
8 further nodes adjacent to its inserted cap node, so the closure has **at most about 1,481 unique
nodes**. Full closure is **necessary but not sufficient** for the amendment branch; a globally
scoped row-8 amendment is permissible only under this full-closure coverage. The six decade-cap
stages (`cap_1e-6` … `cap_1e3`) are result-run diagnostic traces and are **not** probed here.

**Continuation, all five components (B12(i)).** Nodes are probed in **ascending noise order**. Per
node: run the v2 two-start optimizer and record all attempts. On **accept**, the warm start for the
next node is this accepted optimum, regardless of this node's battery or curvature outcomes. On
**failure**, the warm start carries forward unchanged (last accepted optimum, else `mode_u`).
**Battery and curvature results never affect continuation or warm-start selection.** At accepted
optima only: run the battery (record), then the v2 curvature evaluation in **record-only mode
executing the frozen retry policy exactly** (a retry fires only on SPD/rcond conditioning failure;
both evaluations recorded in full with the per-conjunct retry-acceptance outcomes). **No scientific
gate outcome halts the probe loop**; a diagnostic run's terminal status is COMPLETED unless budget
or infrastructure intervenes; **ALGORITHM_STOP is unreachable for diagnostic-kind runs.**

**R3 determinations (conforming, recorded here so they are frozen rather than silent):**
(i) `node_index` is assigned **stage-grouped** — grouped by the frozen stage order `level0`,
`refine_1..3`, `upper_pullback`, `lower_pullback`, ascending noise within each stage — because the
frozen capture stage bookkeeping requires contiguous node blocks per stage, while probing remains
globally ascending in noise; every per-node record and diagnostic row additionally carries
`probe_position`, the realized position in probe order, so the trajectory is explicit.
(ii) Purity's three node points `0`, `mid = floor((N−1)/2)`, `last = N−1` are positions in **probe
order** over the closure §6.1 determines.

**3. Frozen formulas (plan §6.2). No threshold anywhere in this protocol is new.** Every numeric
gate reuses a pre-STOP frozen constant; the MAP-noise comparison is report-only; the slope windows
are theory-derived.

- **Battery (B6, B12(e)).** At every accepted real conditional optimum — a v1.17 §2a conformance
  requirement, not superseded. Reference gradient = central FD of the independent fresh-model scalar
  `G_hist(u, noise) = _mh_log_joint(...) + Σ_nuisance u`, constructed exactly as the committed
  fixture does it (`tests/test_m2c_profile_gradient.py:188-199`): fresh model per evaluation,
  `apply_hp_value`, `ExactMarginalLogLikelihood`, noise fixed. Steps
  `h_j = FD_STEP_GRAD × max(1, |u_j|)` (`FD_STEP_GRAD = 1e-5`); gate per site
  `|Δ| ≤ TOL_GRAD_ABS + TOL_GRAD_REL × scale`, `scale = max(1, max |FD|)` (both `1e-4`). **Ratified
  scope: a gross-defect detector at accepted optima, not a precision-gradient claim.**
- **Historical equivalence (B12(d)).** `|g_value − G_hist| ≤ 1e-9 × max(1, |G_hist|)` — the reused
  v1.4/S3 density-equivalence class — at prespecified points only: the MAP state, the ten prior-draw
  states, and every accepted conditional optimum. The `+ Σ u` term is the change-of-variables
  Jacobian.
- **Prior draws (B12(f)).** Exactly as the committed fixture generates them
  (`tests/test_m2c_profile_gradient.py:167-181`): `torch.random.fork_rng()`,
  `torch.manual_seed(seed)` for seeds 100–109, theta sampled per site in `profile.sites` storage
  order, `u = log theta`, noise from the draw. **Additionally persisted: the exact storage-site
  order and the realized states in canonical named coordinates** — reproducible, not
  permutation-invariant, and any ordering change becomes visible rather than silent.
- **D23 sentinel — committed form verbatim; no vote taken or needed.** Point set
  `_map_neighborhood_states(case)[1:6]`; per-site worst relative error, max over states of
  `|naive − FD| max / max(1, |FD| max)`; a `None` naive gradient counts as infinity; **strict**
  greater-than `D23_SENTINEL_MIN_REL` for **every** nuisance site
  (`tests/test_m2c_profile_gradient.py:365-393`; `m2c_freeze.py:36`).
- **MAP construction pinned verbatim; comparison REPORT-ONLY (B12(h)).** `generate_toy_data()`
  defaults (internally seeded), `PRIOR_CONFIGS["toy_elicited_n20"]`, fresh build, then
  `torch.manual_seed(42)` immediately before `fit_map(n_iter=300, lr=0.05)` — the exact
  `map_fitted` sequence of `experiments/prior_sensitivity_study.py`. The exact float64 delta
  against `FIGURE_EXPECTATIONS["toy_elicited_map_noise"]` (`0.061867347763041584`, the study's
  full-precision frozen constant; a rounded `0.06` appearing in a figure-test fixture dict is
  not this constant) is recorded; **no gate, no new tolerance, no new decision-table row.**
- **FD-step sensitivity (B12(a)).** `symmetry_error(h)` at
  `h ∈ {2.5e-4, 5e-4, 1e-3, 2e-3, 4e-3}` — the frozen sweep extended one factor-2 step each way by
  the same generative rule, introducing no new constant. Per node, an OLS slope of log
  `symmetry_error` against log `h`. **R3 determinations:** the per-`h` statistic is the frozen
  gate's own formula applied per sweep value — `‖raw_h − raw_hᵀ‖_F / max(1, ‖raw_h‖_F)` with
  `raw_h` the central-difference Hessian of the validated gradient at step `h`; the sweep is
  measured at the **FINAL curvature evaluation point** (§6.3's FINAL definition); the OLS uses
  **natural logs** (the slope is base-invariant; fixing the base pins the recorded intercept). The
  measurement is implemented **outside the frozen v2 gates**, which stay byte-identical.
- **Slope classification (B12(b)).** A priori windows: **TRUNCATION-LIKE** `[1.5, 2.5]`;
  **NOISE-LIKE** `≤ −0.5`; **FLAT** otherwise. **The windows are not to be widened to make the
  amendment branch more reachable; row 8 remains deliberately conservative.**
- **UNDEFINED (B12(c), extended form).** The slope is UNDEFINED if **any sweep value is nonpositive
  or nonfinite**, or if **the fitted slope or any required OLS statistic is nonfinite**. **Invalid
  points are never silently omitted and no reduced subset is fitted.** UNDEFINED routes to
  PRESERVE_STOP through the frozen decision table.
- **Purity (B12(g)).** Repeated `g` and `grad` evaluations bit-identical at the mode and at the
  three frozen probe positions (first, mid, last). **Kept at four points, not enlarged**; the claim
  is repeatability at those points, not global determinism. **R3 determinations:** every purity
  evaluation is at the fixed nuisance vector `mode_u` (deterministic, independent of optimizer
  outcomes); `repeats = 2` — the minimal conforming reading of "repeated"; bit-identity of the
  objective and every gradient component.

**4. Total decision table (plan §6.3; ballot B16 as conformed to B12(c)).** Definitions: `G1` =
battery outcome over all accepted optima; `G2` = historical-equivalence outcome; slope classes per
§3 above with the B12(c) UNDEFINED; POSITIVE RETRY ACCEPTANCE is the plan §3.2 six-conjunct
predicate; a **FINAL** curvature evaluation is the single evaluation at the two-start-accepted
optimum when no retry fired, or the post-retry evaluation at the positively accepted retry point
when one did. **First matching row wins; the table is total via row 10; every mixed, missing,
nonfinite, or unresolved case lands on PRESERVE_STOP.**

| # | Condition | Disposition |
|---|---|---|
| 1 | The purity check fails anywhere | PRESERVE_STOP; infrastructure-defect track; no amendment permitted |
| 2 | Any probed node lacks a complete record for any reason other than a recorded optimizer-gate failure, or the diagnostic run's terminal status is not COMPLETED | PRESERVE_STOP; evidence incomplete; no amendment |
| 3 | The two-start optimizer gate fails at any probed node (start failure after restart, non-stationarity, or agreement failure) | PRESERVE_STOP; optimizer/step-policy track (not a Hessian-estimator diagnosis) |
| 4 | Any curvature retry is not POSITIVELY ACCEPTED (the negation of any conjunct, including `status == 0` with `success == False` and the malformed-output fallback), OR nonstationarity is observed at any evaluated point, pre- or post-retry | PRESERVE_STOP; optimizer/stationarity track; this row precedes every Hessian or amendment diagnosis |
| 5 | `G1` fails at any accepted optimum, or `G2` fails at any prespecified point, or the D23 sentinel fails | PRESERVE_STOP; gradient/potential code-defect track; no gate or tolerance amendment permitted |
| 6 | Zero probed nodes fail the frozen raw-symmetry check | PRESERVE_STOP; reproducibility investigation; no amendment supported; D45 remains unvalidated either way |
| 7 | Any symmetrized-curvature gate (SPD, rcond, directional, logdet-stability) fails at a FINAL curvature evaluation (which by rows 3–4 exists only at positively accepted points) | PRESERVE_STOP; Hessian-estimator amendment track, gated on a separate future ballot (B5) |
| 8 | Rows 1–7 clear; at least one node fails raw symmetry; every probed node has a defined finite slope; every symmetry-failing node is TRUNCATION-LIKE | AMEND per the pre-committed B4 branch, scoped per B7: global only under full-closure coverage |
| 9 | Any symmetry-failing node is NOISE-LIKE, FLAT, or UNDEFINED, or any probed node's slope is UNDEFINED | PRESERVE_STOP; mixed or ambiguous evidence; follow-up requires a new frozen protocol version |
| 10 | Anything else | PRESERVE_STOP |

**Only row 8 can ever authorize an amendment**, and even then the amendment requires its own
implementation, review, manifest, and separate author ratification at R5 before a result run (B4).
The `tol(h) = C·h²` alternative remains not ballot-ready and not authorized. Row-7 estimator
amendments stay deferred to a separate future ballot (B5); row 7 preserves the STOP.

**Rows evaluator (author ballot item B, ratified).** R3 implements the table as a **pure,
hermetically tested function** over the diagnostic-record instance: input the committed record's
distilled fields, output **only the first matching row number and its frozen track label**. It
mechanizes frozen precedence for R5's mechanical application, which the author confirms; it
authorizes no execution and makes no new scientific decision. The diagnostic record itself carries
measurements and frozen-check outcomes only, **never a disposition**.

**5. Diagnostic-record schema and instance residence.**
`docs/m2c_freeze/m2c_diagnostic_record.schema_v1.json` (Draft 2020-12; closed properties
everywhere; frozen nonfinite sentinels element-wise on every measurement field; finite-only summary
constants; `not_a_result: true` as a const) governs the **R3 diagnostic-record INSTANCE**, whose
sha256 is the `diagnostic_record_sha256` member of every result-run chain and every R6 grant
(v1.19 §8; never a terminal-record digest). **Residence, determined:** the instance is the
diagnostic run's **exact persisted `payload.json`** — the document the child bootstrap writes after
externalizing `node_records` to `nodes/` and injecting `node_evidence_digests` — committed at
`docs/m2c_evidence/<run_id>/payload.json`. Consequences, each verified against merged source: the
`RUN_DIR_LAYOUT` entry is the existing `"payload.json"`; its `RUN_DIR_EVIDENCE_CLASSES` class is
the existing `fixed_runtime`; the applicable v1.20 ceilings are the 33,554,432-byte
runtime-envelope per-file class and membership in the 134,217,728-byte bundle; it is Layer-2
evidence under `RAW_MANIFEST.sha256` with its digest in the terminal record's evidence block. **No
new run-directory path, class, or ceiling is introduced; the R2a fail-closed layout is not
amended.** The schema references the frozen R1 execution-record schema by `$id` and JSON Pointer
(a downward reference embedding no digest) and embeds no hash of the protocol manifest that pins
it (acyclicity, plan §3.1).

**6. Protocol parameters and the Layer-1b PROTOCOL manifest (author ballot item C, ratified).**
`docs/m2c_freeze/m2cr_diagnostic_protocol_v1.json` (`kind: "m2cr_diagnostic_protocol"`,
`schema_version: 1`, `addendum: "v1.21"`) restates this addendum's protocol machine-readably;
**every numeric value quotes an existing frozen constant** from `bistar_gp/m2c_freeze.py` or this
addendum's ratified windows; the audit CI asserts artifact/addendum agreement.
`docs/m2c_freeze/m2cr_protocol_manifest_v1.json` is the Layer-1b PROTOCOL manifest with the
**literal plan §3.1 key set and nothing more**: `kind`, `schema_version`, `addendum`,
`diagnostic_record_schema {path, sha256}`, `protocol_parameters {path, sha256}`, and
`infrastructure_manifest_sha256` (the Layer-1a downward edge). **No R3 code pins are added**: code
bytes remain bound by the exact `execution_commit` and the complete importable-artifact manifest
with origin/loader authentication. The manifest is produced by a committed R3 generator and
**re-pinned mechanically whenever Layer 1a regenerates** (an R4 launch-prep regeneration at its own
worktree/commit regenerates Layer 1b alongside, under the R4 grant); the committed-matches-tree
audit fails closed on any drift, self-hash, or R3-schema pin appearing in Layer 1a. The three new
Layer-0/1b static artifacts are additionally checked against the v1.20 static per-file ceiling.

**7. Layer-1b launch and audit enforcement (author ballot item A1, ratified).** Bounded amendments
to two infrastructure-pinned R2/R2a modules, with the full regeneration cascade and discriminating
tests:

- **Launch (capture).** `_authenticate_launch_spec` additionally resolves the committed protocol
  manifest under the launch worktree at its committed relpath, requires its file sha256 to equal
  the authorized chain's `protocol_manifest_sha256`, parses it **closed-world** against the §6 key
  set, requires its `infrastructure_manifest_sha256` to equal the spec's own authenticated
  Layer-1a digest, resolves and digest-verifies the diagnostic-record schema and protocol-parameter
  pins on disk, and carries the authenticated facts on the launch spec (spec-digest-bound). Any
  missing, unbindable, or mismatched artifact remains a pre-payload `INFRA_FAILURE` that does not
  consume.
- **Protocol-exit validation (capture).** For diagnostic-kind runs the parent validates the **exact
  persisted `payload.json`** — after node externalization and digest injection — against the
  **authenticated** diagnostic-record schema before accepting the protocol exit; a violation is
  `schema_invalid_payload` and the record falls to `INFRA_FAILURE` under the unamended B2
  precedence (rule 4 unsatisfied, rule 5 applies).
- **Audit.** `protocol_manifest_sha256` is removed from the declarable-absent set, which shrinks to
  exactly `{diagnostic_record_sha256, amendment_manifest}` — the members produced only by R4 and
  R5. **Historical semantics are preserved:** D45 remains a historical consumed ledger entry and is
  never re-adjudicated; no committed R2-era report is rewritten; the change binds every **future**
  chain verification, and every future R4 diagnostic launch requires the committed protocol
  manifest.
- Both amended modules are re-pinned in the regenerated infrastructure manifest `code` section; the
  importable-artifact manifest and aggregating environment-freeze manifest regenerate by the
  established fresh-detached-worktree recipe.

**8. Coordinate semantics and goldens (plan §3.3/B1; plan §8 R3).** **Composition, determined:**
the orchestrator supplies the v2 gates with callables and vectors in **canonical `(ls, os, lv)`
axes**; the canonical-to-storage role permutation is applied **inside the bridge wrapper** at each
evaluation, so computation inside the scientific bridge stays in E1 storage order and the bridge is
untouched, while the gates — which are axis-space-agnostic and stay byte-identical — realize
directions positionally on canonical axes. This is the only composition that simultaneously
satisfies B1's named-canonical semantics, §3.2's "B1-reconciled directions", and storage-permutation
invariance. Consequences frozen as goldens: **hard-coded per-seed canonical direction vectors** —
the exact float64 triples `normalize(default_rng(seed).standard_normal(3))` for seeds
`{200, 201, 202}` — pinned as literals; an **asymmetric named-coordinate oracle** tracing
distinguishable per-axis values through optimizer, battery, curvature, and persistence; and
**storage-permutation invariance** — permuting the storage-site order changes no persisted
canonical evidence and no realized direction.

**9. What this addendum does NOT change or authorize.** It changes **no v1.17 value, tolerance,
gate, reference, predicate, or algorithm**; no B2 precedence row; no R1 schema byte; no v1.20
ceiling; no frozen M2bR/M2c artifact; no §6.5/§6.6 relaxation. The frozen v2 gates,
`profile_integration.py`, and the v1.17 manifest CI stay byte-identical. It authorizes **NO**
compute, recompute, diagnostic, profile, optimizer, gradient, Hessian, curvature, MAP, sampler, VI,
or Mauna access, and **no `--execute`**; the 60-month **holdout stays SEALED**. **R4 is not begun
and is not authorized**: it requires its own fresh explicit author grant, recorded in the v1.19
ledger with the complete frozen chain — which after this addendum necessarily includes the
committed protocol manifest — at its own regenerated freeze and exact execution commit. The
reserved instance path stays **ABSENT** and the **v1.18 label stays permanently unused**.

## v1.22 — A7 attempt-3 prerequisite: Della `bistar_gp` environment re-freeze (arviz + jsonschema added), caused by attempt-2's fail-closed dependency discovery — 2026-07-22

**Prospective amendment, not a rewrite.** A7 attempt 2 (Slurm job `11497561`, SPENT) failed at the
submit-script preflight `import bistar_gp` (exit 82) because the frozen Della `bistar_gp` conda
environment lacked `arviz` — imported unconditionally by `bistar_gp/__init__.py` through
`mcse_strategy` — together with its transitive `jsonschema` and `referencing`. The preflight caught
this and failed closed before any benchmark cell; no scientific computation, Mauna access, or
benchmark JSON artifact resulted. This addendum records the environment re-freeze that removes the blocker for
attempt 3. Earlier freeze history (the five-version freeze in the D19 A7 execution protocol §2/§3
and this file's prior addenda) is superseded on the environment inventory for future attempts, not
rewritten.

**Versioning reassignment.** This number, **v1.22**, previously reserved for the successful A7
measured-results / thread-pinning addendum, is reassigned to this environment re-freeze. The
successful measured-results addendum becomes **v1.23**. The reassignment is prospective and caused
by attempt 2's discovery.

**The re-freeze (pure addition, five scientific pins unchanged).** In the frozen environment
`/home/sc8918/.conda/envs/bistar_gp` (python 3.11.14, torch 2.10.0+cu128, gpytorch 1.15.1, pyro
1.9.1, numpy 2.4.2), `arviz` and `jsonschema` were installed with the five scientific packages held
by constraint so none could move. The exact commands, author-executed on della9 (2026-07-22):

```
cat > ~/bistar_pin_constraints.txt <<'EOF'
numpy==2.4.2
scipy==1.17.0
pandas==3.0.0
matplotlib==3.10.8
torch==2.10.0
gpytorch==1.15.1
pyro-ppl==1.9.1
EOF
/home/sc8918/.conda/envs/bistar_gp/bin/python -m pip install --dry-run -c ~/bistar_pin_constraints.txt arviz jsonschema
/home/sc8918/.conda/envs/bistar_gp/bin/python -m pip install -c ~/bistar_pin_constraints.txt arviz jsonschema
```

The result was a pure addition of eleven packages, zero removals and zero version changes
(mechanically proven by `comm` on the sorted before/after `pip list --format=freeze` manifests:
`comm -23` empty, `comm -13` = 11): `arviz==0.23.4`, `attrs==26.1.0`, `h5netcdf==1.8.1`,
`h5py==3.16.0`, `jsonschema==4.26.0`, `jsonschema-specifications==2025.9.1`, `platformdirs==4.11.0`,
`referencing==0.37.0`, `rpds-py==2026.6.3`, `xarray==2026.7.0`, `xarray-einstats==0.9.1`.

**Authoritative manifest.** The complete post-change 69-package environment is committed at
`docs/d19_a7_freeze/bistar_env_after.txt` (1386 bytes, 69 lines, sha256
`d832d426ec5a83e3f1da3275c289323c8732f2644038efb15b2eb1567b085aa1`); it is the frozen environment
for attempt 3. The pre-change 58-package baseline (`~/bistar_env_before.txt`, 1175 bytes, sha256
`18eef23fc80c5faea2fe1e346564f0a51c7e76e15930ee617654444f92eb084d`) is retained uncommitted in
Della home (`~/bistar_env_before.txt`) as provenance and is not committed to the repository.

**Verification.** After the install, the submit-script preflight environment check — run read-only
from the attempt-2 worktree — printed `ENV-OK /home/sc8918/.conda/envs/bistar_gp/bin/python 3.11.14
2.10.0+cu128 1.15.1 1.9.1 2.4.2`, confirming `import bistar_gp` now succeeds and the five pinned
versions are unchanged; a live `pip list --format=freeze` equalled the committed manifest.

**Attempt-3 preconditions.** Attempt 3 requires the D56c amendment (D19 A7 execution protocol §7):
the `_03` worktree, both prior worktrees preserved, and a fresh byte-exact authorization naming the
D56c merge anchor `M56c`. Immediately before that authorization is cast, the read-only Della
preparation check must require **BOTH** exact byte-for-byte equality between the live
`pip list --format=freeze` and this committed 69-package manifest **and** a successful
`import bistar_gp` under the five pins. Honest scope: that complete-inventory equality is a
preparation-time gate only; the submit job enforces the five version pins plus `import bistar_gp`
(exit 82), **not** the 69-package manifest, and the interval between the preparation check and the
single submission is a disclosed, user-controlled trust interval. This addendum authorizes **NO**
benchmark, submission, Mauna access, or scientific computation; the 60-month holdout stays SEALED
and the **v1.18 label stays permanently unused**.
