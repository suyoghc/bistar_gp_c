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
