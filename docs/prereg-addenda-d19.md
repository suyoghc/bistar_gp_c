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
