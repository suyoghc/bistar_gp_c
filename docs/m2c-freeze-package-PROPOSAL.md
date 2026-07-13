# M2c — complete numerical freeze package — PROPOSAL (for the SECOND author vote)

Status: **PROPOSED, PENDING THE AUTHOR'S SECOND EXPLICIT VOTE.** Numerical companion to the
architecturally-ratified [m2c-gtoy-profile-PROPOSAL.md](m2c-gtoy-profile-PROPOSAL.md) (D39 directional
ratification of P1–P8). **Every number is PROPOSED and needs ratification; nothing here is frozen; no
compute/recompute, sampler run, Mauna access, or holdout access is performed or authorized.** On
ratification this becomes prereg addendum **v1.17** (algorithm + protocols + tolerances + references);
then the gated deterministic recompute; then a **separate append-only v1.18** result addendum. Per
**P7** this is **one umbrella package**: §§1–6 land together; none may be frozen piecemeal.

Tags: **CONFIRMED** = quoted from a frozen source (file:line); **PROPOSED** = a value this freeze
introduces, with rationale. Fixtures are synthetic only (§6.5); the toy reference is `toy_elicited`
(N=20). This draft is **rev-5**, applying the author's 2026-07-13 directional J-decisions, five freeze
fixes, and three final freeze-precision corrections (see §9). **Nothing is frozen until the P7 umbrella
vote — the J-decisions are author-selected/directional, not yet frozen.**

---

## 1. P3 — nested-grid + domain-extension protocol (numerical convergence/sensitivity, NOT a proven bound)

Governs the profile-Laplace noise-marginal quadrature (§4 of the architecture doc). It is a
**numerical convergence/sensitivity** procedure — **not** a proven tail bound. It amends the frozen
"profile grid 40 points" (§6.15 L811) via the §6.16 append-only route.

**Base grid (CONFIRMED, frozen):** `np.geomspace(0.005, 1.2, 40)`. Freeze the generator as the **exact
expression r = (1.2/0.005)^(1/39)** (float64 1.150882688488405; 1.150883 is display-only).

**Band-edge nodes (CONFIRMED authorized, §6.9 L661):** insert exact band edges as integration nodes —
toy 0.15, 0.30; Mauna per-arm q25/q75 (exact-quadratic inversion, §4.2 Step 7). Not an amendment.

**Domain extension (PROPOSED; the P3 amendment). Support is UNBOUNDED** (`Positive()` likelihood,
config.py:282 — `noise_bounds=(1e-4,10.0)` is **inert config metadata, NOT a model constraint**).
- **Staged wider-cap SENSITIVITY protocol (PROPOSED; author fix 1). This is CAP SENSITIVITY, NOT a
  proven tail bound** — a single cap at 10.0 with an outermost-shell check only asks "does the mass
  change between the last lattice node and 10.0?", which says nothing about mass beyond 10.0. Instead,
  **stage progressively wider caps** and measure whether widening changes the masses:
  - **Order-independent: always evaluate the FULL maximum domain [1e-7, 1e4]** (author correction).
    Extend the geometric lattice (ratio r) across the full [1e-7, 1e4], insert the exact cap nodes at
    both ends, and use this **full-domain grid as the reported cap result** (band masses P_b^{full}).
    The maximum domain is fixed at [1e-7, 1e4]: beyond these the LogNormal(log 0.3, 1) prior density is
    astronomically small (at η = 1e4, ~exp(−½·(log(1e4/0.3))²) ≈ e^{−54}; symmetric at 1e-7) times a
    vanishing likelihood.
  - **Final one-sided sensitivities (computed at the full domain, order-free):**
    **δ_tail^{upper}(b) = |P_b([1e-7, 1e4]) − P_b([1e-7, 1e3])|** (upper cap pulled back one decade) and
    **δ_tail^{lower}(b) = |P_b([1e-7, 1e4]) − P_b([1e-6, 1e4])|** (lower cap pulled back one decade). The
    reported **δ_tail(b) = max(δ_tail^{upper}(b), δ_tail^{lower}(b))**. **STOP if either final one-sided
    delta ≥ ε_domain = 1e-4 for any band** (the masses still shift at the full domain; needs the
    tail-envelope below or P3(iii)). At ~16.4 nodes/decade the full [1e-7, 1e4] grid is
    **40 base + 76 lower + 64 upper + 2 cap = 182 nodes** (184 with the two band edges).
  - **Earlier decade stages** (upper caps 10/100/1000; lower caps 1e-4/1e-5/1e-6) are recorded
    **DIAGNOSTICALLY only** (a convergence trace), never used for the pass/fail verdict.
  - **Honest label (fix 5):** δ_tail is a **numerical cap-sensitivity estimate**, NOT a proof that no
    mass exists beyond the last cap. Rationale for ε_domain = 1e-4: it is far below the smallest
    **REPORTABLE**-band SE (mid 0.003838 — ~38× below; the hi band's 8.66e-4 is non-reportable at mass
    0.046) and below the 0.10 S4 tolerance, so a cap shift this small cannot move a gated comparison.
- **Optional certified tail-ENVELOPE (a genuine bound, if the author wants rigor beyond sensitivity):**
  for η beyond a cap C, the omitted mass ≤ **L_max · ∫_C^∞ p_η(η) dη** (L_max = global max likelihood;
  p_η = LogNormal prior), a closed-form upper bound (architecture doc §4.2 option B). Only this route
  yields a *proven* tail bound; the staged-cap protocol above yields sensitivity, and P3 is described
  as sensitivity unless this envelope is adopted.

**Nested-grid refinement (PROPOSED; the quadrature-sensitivity ESTIMATE — NOT a certified bound and
NOT Richardson):**
- **Exact nested construction:** at refinement level ℓ, insert **one node at the geometric mean**
  √(g_k·g_{k+1}) between every consecutive pair of the level-(ℓ−1) grid, **retaining all previous
  nodes** (including edges and caps). Level ℓ has 2·N_{ℓ−1} − 1 nodes; the construction is strictly
  nested (every coarse node persists), so successive levels are directly comparable.
- **Successive-level sensitivity (corrected per rev-2 review — the gate must advance across levels):**
  at each level ℓ define **δ_quad^(ℓ)(b) = |P_b(level ℓ) − P_b(level ℓ−1)|** (level 0 = the converged
  base+edge+extension grid). Refine while **max_b δ_quad^(ℓ)(b) ≥ ε_grid = 1e-4**, up to **L_max = 3**
  (≈8× density); the reported **δ_quad(b) = δ_quad^(ℓ_final)(b)**. If still ≥ 1e-4 at level 3 ⇒ **STOP**.
  This is a **successive-grid sensitivity estimate**, explicitly **not** a proven discretization bound
  (a true bound needs an analytic max|m″|, unavailable on sampled nodes — codex round-4).
- **Measure:** integration stays in **linear noise space** (the verified measure). Log-noise
  re-parameterization is optional **P3(iii)**, not the default.

All extension/refinement lattices are deterministic; the realized grids, per-stage cap masses, and
the convergence trace go in the v1.18 result manifest (§6).

---

## 2. Profile-Laplace gradient battery, optimizer gate, and curvature gate (exact)

### 2a. Profile-gradient validation battery (the P1 spec — not just a reference)

P1 ratified a functional (`functional_call`, no-`.data`) gradient of the profile potential
g(u) = log_joint(exp(u), noise) + Σu. Freeze its validation, mirroring the v1.4 E1 battery:
- **FD reference:** central finite differences of g at step 1e-5 scaled per coordinate
  (h_j = 1e-5·max(1,|u_j|)).
- **Gate:** ‖∇g_func − FD(g)‖ per coordinate ≤ **1e-4 abs + 1e-4·scale** (scale = max(1, max-coord FD);
  reuse of the frozen v1.4 gradient envelope).
- **Point set:** at each of the profile grid's conditional optima u\*(η) (a state per grid node) plus
  the toy/Mauna-structure MAP and 10 prior draws (seeds 100–109) — the E1 point-generation style.
- **D23 sentinel:** the naive `.data`-injection gradient of g must remain **disconnected** on kernel
  sites (a sentinel test asserts the defect persists, so an env upgrade forces review — v1.4 pattern).
- **Test:** `tests/test_m2c_profile_gradient.py` (new); failure ⇒ **STOP** (no profile recompute).

### 2b. Per-grid-point optimizer gate (ALL mandatory; stationarity never replaced by agreement)

The per-point optimization finds u\* = argmax g(u; η). **Upgrade the optimizer to gradient-based
(L-BFGS-B on the 2a-validated gradient)** — the existing Nelder-Mead converges on function value, not
gradient, and cannot reliably reach the stationarity tolerance below. Run **two starts** (warm-start
along η and the mode-start); **both must be finite AND report success.**
- **Frozen L-BFGS-B controls (fix 2):** `scipy.optimize.minimize(method="L-BFGS-B")` on −g (minimize
  the negative log-marginal), with `options = {maxiter: 500, maxfun: 5000, ftol: 1e-12, gtol: 1e-8}`
  (gtol 1e-8 is tighter than the τ_stat = 1e-4 gate below, so a converged run comfortably passes
  stationarity). **Abnormal termination** (SciPy `status ≠ 0`, e.g. `ABNORMAL_TERMINATION_IN_LNSRCH`)
  ⇒ **one restart** of that start from a seed-derived jitter u_0 + 1e-3·N(0,I) (frozen generator
  `numpy.random.default_rng(300 + start_index)`, float64); if the restart also terminates abnormally,
  **that start has failed**. If EITHER start fails after its one restart ⇒ **STOP** for that grid point
  (no single-start acceptance — both starts are required for the agreement check). No further restarts.
- **Finite objective:** g(u\*) finite. — PROPOSED.
- **Gradient-stationarity (mandatory, per start):** ‖∇g(u\*)‖_∞ ≤ **τ_stat = 1e-4** (2a gradient).
  Rationale: u is O(1) log-space; matches the v1.4 absolute gradient scale; achievable with L-BFGS-B.
  PROPOSED.
- **Multi-start agreement (ADDITIONAL, never a substitute for stationarity):** |g_warm − g_mode| ≤
  **1e-6·max(1,|g|)** AND ‖u\*_warm − u\*_mode‖_∞ ≤ **1e-4**; take the higher-g optimum. PROPOSED.

### 2c. Curvature gate (K = −H must be SPD AND well-conditioned; NO flooring — author J1)

- **H by central differences of the 2a validated gradient** (never `create_graph`; D24/v1.8 §3):
  H^{(h)}_{·j} = [∇g(u\*+h e_j) − ∇g(u\*−h e_j)]/(2h); symmetrize K = −(H+Hᵀ)/2.
- **Step-size stability:** over h ∈ {5e-4, 1e-3, 2e-3}, require
  **max_{h≠1e-3} |log|K^{(h)}| − log|K^{(1e-3)}|| / max(1, |log|K^{(1e-3)}||) ≤ 1e-3**; the **reported
  Hessian is K^{(1e-3)}**. PROPOSED.
- **Symmetry:** pre-symmetrization **‖K_raw − K_rawᵀ‖_F / max(1, ‖K_raw‖_F) ≤ 1e-6**. PROPOSED.
- **Directional-curvature verification (REQUIRED by v1.8 §3; sign-corrected per rev-2 review).**
  **Direction RNG (frozen, fix 3):** `numpy.random.default_rng(seed)` (PCG64), **float64**, seeds
  **{200, 201, 202}** (reuse of the v1.4 convention); draw `rng.standard_normal(d)` over the d=3
  profile coordinates in the fixed order **(ls, os, lv)**, then **unit-L2-normalize** v ← v/‖v‖_2. For
  each such v at u\*, let
  D²_g(v) = [g(u\*+εv) − 2g(u\*) + g(u\*−εv)]/ε² (ε = 1e-3) be the second central difference of the
  potential. Since **K = −H_g** and g is maximized at u\* (so H_g is negative-definite and D²_g(v) < 0),
  the correct comparison is **vᵀK v ≈ −D²_g(v)**: require
  **|vᵀK v − (−D²_g(v))| / max(1, |D²_g(v)|) = |vᵀK v + D²_g(v)| / max(1, |D²_g(v)|) ≤ 1e-3**. Failure
  ⇒ **STOP**. PROPOSED (reuse of the v1.4 directional-Hessian 1e-3 tolerance).
- **Curvature conditioning — NO flooring of the profile determinant (author J1 DIRECTION,
  2026-07-13: no flooring).** Compute the eigenvalues λ_max = λ_1 ≥ … ≥ λ_d = λ_min of K. Require BOTH:
  - **strict SPD:** λ_min > 0;
  - **relative conditioning:** **rcond = λ_min / λ_max ≥ κ_min = 1e-8** — **PROPOSED (Claude's number,
    NOT author-directed; frozen only at the P7 umbrella vote):** the reciprocal spectral condition
    number, ≥ 1e-8 means κ₂ ≤ 1e8, a conservative binary64 numerical-PD safety threshold (heuristic,
    not a determinant-error guarantee); a genuine profile maximum is far better conditioned, so this
    rarely binds.

  **No eigenvalue is ever floored** — flooring a near-singular direction would fabricate the
  determinant (hence spurious mass). If λ_min ≤ 0 **or** rcond < κ_min, the direction is
  near-singular/unresolved ⇒ **RETRY ONCE:** re-optimize u\* with **tighter L-BFGS-B tolerances
  (gtol 1e-10, ftol 1e-14, maxiter 1000)** and re-run the **full curvature gate** (the same h-sweep
  {5e-4, 1e-3, 2e-3}, symmetry, directional, SPD/rcond checks). The **reported Hessian stays K^{(1e-3)}
  at the re-optimized u\*** (the frozen center step is unchanged; the retry sharpens the *optimum*, not
  which h is reported). If the retry still fails the SPD/rcond check ⇒ **STOP** (the point is
  unresolvable; never accepted, never floored). This replaces the rev-3 flooring rule entirely, per the
  author's J1 vote.

STOP/retry counts per grid point go in the v1.18 result manifest.

---

## 3. Chain-aware `MCSE_strategy` for the Q2 model probability

The Q2 agreement test (§5 of the architecture doc) is |p_strategy − p_SIR| ≤ 2·√(MCSE_strategy² +
MCSE_SIR²). A strategy's MCMC predictive rows are **autocorrelated**, so an ordinary row bootstrap
(the deterministic-SIR machinery, `prior_sensitivity_study.py:725`) underestimates MCSE_strategy.

- **Dependence measured on the Q2 SOFT contribution series (corrected from rev-1 — NOT the Q3 hard
  winner).** Q2 = the normalized soft-transfer functional s_j = mean_draws exp(−G/τ − max)_j
  (`prior_sensitivity_study.py:654`). Its per-draw influence series for the reported model (Sin+Linear,
  column j\*) is **c_t = exp(−G_{t,j\*}/τ − M_global)**, where **M_global = max over ALL (t,j) of
  (−G_{t,j}/τ)** — the **same single global shift** `soft_transfer` uses
  (`prior_sensitivity_study.py:658`), a constant that leaves the autocorrelation unchanged. **NOT a
  per-draw max_j shift** (rev-2 review: a per-draw shift rescales each draw by a different constant and
  distorts the autocorrelation — the very bug the global shift avoids). The hard-winner indicator (Q3)
  can be constant while c_t is highly autocorrelated, so IACT is estimated from **c_t**, per chain, with
  **τ_int = max over chains and over each competing model's contribution series** (conservative).
  Estimator: arviz initial-monotone-sequence (`az.ess`-style autocov). If a series is constant (τ_int
  undefined) ⇒ the cell is **UNDETERMINED** (a constant contribution cannot yield a meaningful MCSE).
- **Estimator: moving-block bootstrap (MBB), fully specified:**
  - **Block length** ℓ = **ceil(2·τ_int)**; the cell is **UNDETERMINED** (chain too short to resolve
    dependence, not a silent fallback) whenever the number of distinct non-circular blocks
    **T − ℓ + 1 < 2** (i.e. ℓ ≥ T, which yields a single block and zero bootstrap variation).
  - **Blocks:** overlapping blocks of ℓ consecutive draws **within each chain** (non-circular: starts
    0..T−ℓ); draw **⌈T/ℓ⌉ blocks per chain**, concatenate, and **truncate back to exactly T draws per
    chain** (preserving the equal-per-chain, R-B pooled-800 one-normalization aggregation).
  - Re-run the exact `soft_transfer` aggregation per replicate; **MCSE_strategy = SD over B = 1000
    replicates**; **frozen seed = 20260712**. Expect ~2% MC relative noise in the bootstrap SD.
- **Kept SEPARATE from** (i) the **G-C precision gate** MCSE ≤ 0.02 on any reported probability (§6.7),
  and (ii) the **W5 independent-pool scatter** (0.419/0.438/0.431). The three are reported separately,
  never combined. **MCSE_SIR** stays the deterministic conditional bootstrap (0.441 ± 0.005), unchanged.

---

## 4. Numerical-error reporting for the deterministic profile masses (sensitivity ESTIMATES, never an SE, never a proven bound)

The profile band masses are **deterministic**; their uncertainty is **numerical** and reported as
**sensitivity estimates** (corrected from rev-1's "bound"), **never** an SE and **never** a proven
error bound.
- Per band b, report the **three components separately** (no `max`/`sum` claimed as a bound —
  `max` cannot bound simultaneous same-direction errors):
  - **δ_quad(b)** = δ_quad^(ℓ_final)(b) = |P_b(final refinement level) − P_b(final−1)| (§1, the
    successive-level definition — not level-1-vs-level-0);
  - **δ_hess(b)** = max_{h∈{5e-4,2e-3}} |P_b(h) − P_b(1e-3)| (band mass recomputed with the Hessian at
    each sweep step, §2c);
  - **δ_tail(b)** = **max(δ_tail^{upper}(b), δ_tail^{lower}(b))** from §1 (the two final one-sided cap
    sensitivities at the full [1e-7, 1e4] domain; a cap-sensitivity estimate, **not** a bound — a proven
    bound requires the §1 tail-envelope option).
- An optional aggregate **δ_b^{env} = max(δ_quad, δ_hess, δ_tail)** may accompany them **labelled a
  heuristic envelope, NOT a proven bound.** All are used only to confirm the profile masses are
  numerically stable to well within the gated tolerances (e.g. the S4 0.10 adequacy tolerance); the
  profile is a **corroborating** reference (§6.8), never a lone verdict.

---

## 5. The five remaining §6.15 M2c predicates

Researched by codex (xhigh) reading the plan + code; every CONFIRMED fact was **independently
re-verified against source** (S2 def plan L271; S3 7-coord def plan L275–285 + volume-preserving
log|det ∂u/∂z| = 0, checked by hand; M0=7/M1=9 sites plan L478; `SamplerDiagnostics.divergence_draws`
= per-chain draw indices only, `sampler_diagnostics.py:93`; `get_component_kernel_matrices` /
`apply_hp_value` / `likelihood.noise`=variance, `model.py:42/88/95`).

### 5.1 S2 mass-convention test tolerances

**CONFIRMED:** S2 = "fixed MAP-Hessian inverse mass, adaptation off" on E1 (plan L271); mass Hessian
from central differences of validated first gradients, never `create_graph` (D24; v1.8 §3).
- **(a) Formula:** in `e1.sites` order, C_{·j} = [∇U(u_MAP + h_j e_j) − ∇U(u_MAP − h_j e_j)]/(2h_j),
  h_j = η·max(1,|u_MAP,j|), U = `e1.potential_fn`; H = (C+Cᵀ)/2. Freeze **mass M = H_reg** (position
  space), implemented as whitening A = Q·diag(λ_reg^{−1/2}), u = u_MAP + A z, identity metric in z,
  `adapt_mass_matrix=False`, `adapt_step_size=True`.
- **(b) Thresholds (PROPOSED):** FD base η₀ = 1e-5; stability multipliers {0.5,1,2}; raw skew
  **‖C−Cᵀ‖_F/max(1,‖H‖_F) ≤ 1e-5** (loosened from rev-1's 1e-6 — a differenced noisy Hessian; codex);
  step stability **max_{η∈{0.5,2}η₀} ‖H^{(η)}−H^{(η₀)}‖_F/max(1,‖H^{(η₀)}‖_F) ≤ 1e-3** (**J2
  author-selected at 1e-3** — not frozen until the umbrella vote — matching the directional gate);
  directional curvature ≤ 1e-3
  (as §2c); whitening **‖AᵀH_reg A − I‖_F, ‖H_reg AAᵀ − I‖_F ≤ 1e-8**; quadratic oracle
  U\*=½uᵀdiag(1,4,9)u must recover **mass diag(1,4,9)** (not its inverse) to ≤ 1e-10 relative.
  **SPD requirement: λ_min(H) ≥ 1e-6 with `n_clipped == 0`** (S2 valid ONLY if the raw Hessian is
  already SPD at ≥1e-6 — the 1e-6 floor makes ops safe but cannot conceal a non-SPD Hessian).
- **(c) Fixtures:** the frozen E1 synthetic fixtures (toy seed 0; **Mauna-structure n=120 seed 0 for
  the 7/9-site coverage**; MAP 150 iters, lr 0.05) + the seedless quadratic oracle. **M1 9-site
  coverage is UNVERIFIED until the M1 builder exists (§5.4);** flagged, not claimed.
- **(d) Failure:** any check fails ⇒ **STOP** (S2 unavailable; **no identity fallback**).
- **(e) Consumes:** `E1Potential.sites/init_params/potential_fn`; a new S2 result object
  (`raw_hessian, hessian, eigenvalues, n_clipped, mass_matrix, inverse_mass_matrix, whitener`).
  New implementation (`fit_hmc_e1` has no fixed-metric path).
- **(f)** First-order/no-`create_graph`: CONFIRMED; M=H convention + tolerances + fail-closed: PROPOSED.

### 5.2 S3 Jacobian log-det + equivalence tolerances

**CONFIRMED:** S3 = the 7-coordinate reparameterization z = (ℓ_t,ℓ_s,ℓ_m, s, a_t, a_s, r), bijective to
M0's 7 sites, gated on density + gradient equivalence to E1 (plan L275–285). **M0-only** (M1 has 9
sites; the 4-site toy is rejected, not scored).
- **(a) Formula:** q_j = e^{a_j}/D, D = 1+e^{a_t}+e^{a_s}; ls_j=e^{ℓ_j}, os_j=e^s q_j, noise=e^{s+r};
  u_ls_j=ℓ_j, u_os_t=s+a_t−logD, u_os_s=s+a_s−logD, u_os_m=s−logD, u_noise=s+r (resolve by semantic
  site role, then emit in `e1.sites` order). **log|det ∂u/∂z| = 0** (volume-preserving, verified). Also
  test the constrained log-det log|det ∂θ/∂z| = ℓ_t+ℓ_s+ℓ_m+4s+r+a_t+a_s−3logD so "zero in E1 coords"
  is not misread as omitting support Jacobians. V₃(z) = V_E1(u(z)) − log|det ∂u/∂z| (= V_E1(u(z))).
- **(b) Thresholds (PROPOSED reuse of frozen v1.4 envelopes):** analytic vs autodiff `slogdet` (both
  forms) ≤ 1e-10 abs; z↔θ, z↔u round-trips ≤ 1e-10 (‖·‖_∞); density |V₃−V_E1| ≤ 1e-9·max(1,|V_E1|);
  gradient chain-rule ‖g₃ − J_uzᵀ g_E1‖_∞ ≤ 1e-4 + 1e-4·max(1,‖·‖_∞). All log-share math via `logsumexp`.
- **(c) Fixtures (Mauna-structure ONLY, n=120 seed 0, 150 MAP iters):** 21 interior states (z_map;
  z_map + σ·N(0,I), σ∈{0.1,1.0}, torch seeds {0,1,2,3,4}; prior draws torch seeds {100..109} mapped to
  z). **12 enumerated near-boundary states** (from z_map): [1] r−15; [2] r+8; [3] ℓ_{t,s,m}+8;
  [4] ℓ_{t,s,m}−8; [5] s+8; [6] s−8; [7] ℓ_{t,s,m}+8 & s+8 & r−15; and 5 simplex-boundary ALR pairs
  (a_t,a_s) ∈ {(−15,0),(0,−15),(15,15),(15,−15),(−15,15)}. Total 33 states.
- **(d) Failure:** any check fails, or non-7-site inventory, or site-role ambiguity ⇒ **STOP for S3**
  (others continue). S3-on-M1 reported "outside the frozen S3 definition".
- **(e) Consumes:** E1 ordered sites/transforms/`constrain`/`unconstrain`/`components`/`potential_fn`.
- **(f)** 7-coord definition + E1-equivalence: CONFIRMED; maps, both log-det identities, point sets,
  tolerances, M0-only: PROPOSED.

### 5.3 Divergence non-clustering predicate

**CONFIRMED:** G-B requires "divergences ≤ 0.1% and non-clustering" (plan L580). **The schema stores
only per-chain post-warmup divergence DRAW INDICES, no parameter values** (`sampler_diagnostics.py:93`)
— so **parameter-band clustering is UNEVALUABLE without a schema extension**; only chain- and
(per-chain) time-concentration are honestly computable.
- **Pre-check (PROPOSED):** `divergence_draws` must be **unique sorted integers in [0,T)** per chain
  (the schema range-checks but does not enforce uniqueness, `sampler_diagnostics.py:136`); a duplicate
  ⇒ **UNDETERMINED**.
- **(a) Formula:** rate D/(C·T) ≤ 0.001 (CONFIRMED). **Chain concentration:** d_max = max_c|D_c| ≤
  L_chain = max(2, ⌈3D/C⌉). **Per-chain time-window concentration (corrected from rev-1 —
  per-chain, not synchronized across independent chains):** window w = ⌈0.10 T⌉; for each chain c and
  each start a∈[0,T−w], W_c(a) = #{t∈D_c : a≤t<a+w}; require **max_c max_a W_c(a) ≤ L_time =
  max(2, ⌈3·(D/C)·w/T⌉)** (share per chain, not pooled).
- **(b) Thresholds:** rate 0.1% CONFIRMED; concentration factor 3, min-event floor 2, window 10%,
  inclusive caps — PROPOSED. (At the 4×200 pilot, one divergence is 0.125% > 0.1%, so the rate gate
  forces zero pilot divergences; clustering bites at larger cells.)
- **(c) Fixtures (deterministic hand-built `SamplerDiagnostics`, C=4, T=2000, FULLY enumerated
  per-chain indices; L_chain=6, L_time=2, w=200 at D=8):**
  - **pass** — chain0=[100,1100], chain1=[500,1500], chain2=[300,1300], chain3=[700,1700] (D=8; rate
    0.001; d_max=2≤6; each chain's two events >200 apart ⇒ time passes).
  - **fail-rate** — the pass set with chain0=[100,1100,1900] (D=9 ⇒ 0.001125>0.001).
  - **fail-chain** — chain0=[100,300,500,700,900,1100,1300,1500], chains 1–3 empty (D=8 rate passes;
    d_max=8>6 fails chain; events 200 apart ⇒ each window ≤1 ⇒ time passes).
  - **fail-time ONLY (isolating)** — chain0=[100,150,199], chain1=[500], chain2=[1000,1500],
    chain3=[1800,1900] (D=8 rate passes; d_max=3≤6 chain passes; chain0's [0,200) window holds 3>2 ⇒
    time fails).
  - **{0,1,2}-event** — all empty / chain0=[100] / chain0=[100],chain1=[500] = pass.
  - **duplicate** — chain0=[100,100] = UNDETERMINED; **missing** `divergence_draws`=None = UNDETERMINED.
  Seedless.
- **(d) Failure:** any of rate/chain/time fails ⇒ strategy fails G-B at that scale (sub-150 fail ⇒
  STOP at larger scales, §6.10); missing/duplicate locations ⇒ **UNDETERMINED** (not zero). Does not
  stop unrelated strategies.
- **(e) Consumes:** `n_chains`, `n_draws`, `divergence_draws` (+ `divergence_rate` cross-check).
- **(f)** Rate + post-warmup interpretation + stop routing + schema limitation: CONFIRMED; the
  factor-3 per-chain tests, 2-event floor, 10% window, uniqueness check: PROPOSED.

### 5.4 Spectral/covariance overlap diagnostic (M1 duplication gate)

**CONFIRMED:** M1 adds a constrained short-scale Matern-3/2; the existing duplication gate checks
posterior correlations ≤ 0.95; the ADDITIONAL covariance-overlap form is deferred to M2c (plan L574).
`get_component_kernel_matrices` exposes each component's train covariance (`model.py:42`). **UNVERIFIED:
no production M1 Matern builder exists in the cited code — 5.4's integration fixture depends on that
NEW implementation and is not currently runnable.**
- **(a) Formula:** for each mass-bearing-authority draw θ_i, on training inputs, P = I − (1/n)11ᵀ,
  A = P K_x P (M1 Matern), B_j = P K_j P for **j ∈ {trend, seasonal, medium, nugget K_ε=noise·I,
  rest}** where **K_rest = K_trend + K_seasonal + K_medium + K_ε, EXCLUDING M1** (so the overlap is not
  tautological). Alignment O_j = tr(A B_j)/√(tr(A²)tr(B_j²)); O_max(θ_i) = max_j O_j; duplicate mass
  q_overlap = Σ_i w̃_i·1{O_max ≥ threshold}.
- **(b) Thresholds:** posterior duplicate-mass cap **q_overlap ≤ 0.05** (mirrors the 5%-pathological-
  mass style) — PROPOSED. **Per-draw alignment threshold = 0.90, author-selected a priori (J3,
  2026-07-13; not frozen until the umbrella vote)** — chosen for discrimination over the more
  permissive 0.95, and fixed a priori. The synthetic algebraic fixtures (c) **validate the
  implementation only; they must NOT select the threshold post hoc.**
- **(c) Fixtures:** algebraic seedless (A=B⇒O=1; orthogonal rank-1⇒O=0; positive-scale invariance;
  weighted draws either side of 5%; a "no single component ≥thr but K_rest does" case) + a plumbing
  integration fixture (synthetic Mauna + the NEW M1 builder at prior medians M1 ls 0.30 y, os 2.4e-4;
  checks finite [0,1], not the scientific verdict — contingent on the M1 builder).
- **(d) Failure:** q_overlap > 0.05 (or zero/missing matrix, missing M1/authority) ⇒ **STOP for
  P-comb+M1-v1 promotion**; M0/other arms continue.
- **(e) Consumes:** `get_component_kernel_matrices(...)["XX"]`, `apply_hp_value`, `likelihood.noise`,
  the existing correlation gate's authority weights. **Authority = G-IS IS first, then RW-MH referee;
  profile-Laplace CANNOT issue this verdict** (§6.8).
- **(f)** M1 role + correlation gate + authority + blocking scope: CONFIRMED; centered alignment,
  K_rest-excludes-M1, 5% mass cap: PROPOSED; **alignment 0.90: author-selected a priori (J3; frozen at
  the umbrella vote)**; M1 builder: UNVERIFIED (new).

### 5.5 M1 nugget-floor formal predicate

**CONFIRMED:** instrument-only reference **1.9e-4 normalized variance** (A1; plan L843/§6.7); A1 says
the nugget also absorbs aggregation/residual variance, so it is a diagnostic floor, not a model
truncation. `likelihood.noise` is already **variance** (do not square/sqrt).
- **(a) Formula:** on the M1 authority, n_i = constrained noise variance, w̃_i normalized weights;
  **p_below^{M1} = Σ_i w̃_i·1{n_i < 1.9e-4}** (strict). Report-only companions: p_below^{M0} and
  Δp = p_below^{M1} − p_below^{M0} (same-arm M0 authority). Coincidence boolean = flag ∧ {the separate
  M1 predictive-improvement gate passes}.
- **(b) Threshold — corrected from rev-1 (codex: 0.50 was far too loose):** flag when
  **p_below^{M1} > 0.05** (strict), matching the frozen 5%-pathological-mass style of the other M1
  pre-checks (bound occupancy ≤5%, duplicate mass ≤5%). Reference 1.9e-4 CONFIRMED. **REPORT-ONLY
  (author J4 DIRECTION, 2026-07-13; frozen at the umbrella vote)** — resolving the §6.7 ambiguity ("all failures blocking" vs the
  nugget item's "diagnostic: report whether") in favor of the item's own "report whether" wording: the
  nugget-floor is a **reported coincidence flag**, not a blocking gate. It emits a boolean at
  p_below^{M1} > 0.05 and never stops M1 promotion.
- **(c) Fixtures:** seedless weighted (p_below ∈ {0, 0.05, 0.10, 1.0}; a draw exactly at 1.9e-4
  asserted not-below; M1/M0 arrays with ±Δp; current + legacy noise-site names via `select_hmc_sites`).
- **(d) Behavior (REPORT-ONLY):** always report p_below^{M1}, the authority + ESS, p_below^{M0}, Δp,
  the coincidence flag (p_below^{M1} > 0.05 ∧ predictive-gate passes), and the predictive-gate boolean;
  **no stop**. Missing authority/noise site/bad weights ⇒ the flag is **UNDETERMINED**.
- **(e) Consumes:** the noise site via `select_hmc_sites` (current + legacy) + authority weights.
  Profile-Laplace cannot evaluate it (not a verdict authority).
- **(f)** Reference + variance units + authority: CONFIRMED; the 5% flag threshold, strict boundary,
  M0 comparison: PROPOSED; **report-only disposition: author-selected (J4; frozen at the umbrella vote)**.

---

## 6. Manifests — an immutable v1.17 algorithm manifest + a SEPARATE v1.18 result manifest

Two manifests (corrected from rev-1's single "filled" manifest, which violated §6.16 append-only):

- **`docs/m2c_freeze/gtoy_profile_freeze_v1.17.json`** — the **immutable** algorithm freeze. Contains
  NO profile result. Every entry carries `name`, `value` (or `formula`), `source` (file:line or
  `"PROPOSED-v1.17"`), `test` (exact node id, e.g. `tests/test_m2c_refs.py::test_prior_is_pooled`), and
  a `sha256` where the value is a document/artifact.
- **`docs/m2c_freeze/gtoy_profile_result_v1.18.json`** — the **separate** result freeze, produced AFTER
  the gated deterministic recompute. It **references the immutable v1.17 manifest by its sha256** and
  adds the corrected band-mass VALUES + the three numerical sensitivity estimates (§4) + the realized
  extension/refinement grids + the per-point STOP/retry counts. It never edits v1.17.

**v1.17 field contract (JSON-Schema, no placeholders; the full instance is produced at freeze):**
```
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["freeze_version","kind","frozen_at_git_sha","provenance","references",
               "algorithm","mcse_strategy","tolerances","predicates","historical_provenance"],
  "properties": {
    "freeze_version": {"const": "v1.17"},
    "kind": {"const": "m2c-gtoy-profile-algorithm-freeze"},
    "frozen_at_git_sha": {"type": "string", "pattern": "^[0-9a-f]{40}$"},
    "provenance": {"type": "object", "required":
      ["versions","host","cpu_count","threads","blas","scipy"],
      "properties": {"versions": {"type":"object"}, "scipy": {"type":"string"},
                     "blas": {"type":"string"}, "host": {"type":"string"},
                     "cpu_count": {"type":"integer"}, "threads": {"type":"integer"}}},
    "references": {"type":"array","items": {"type":"object","required":
      ["name","value","source","test"],
      "properties": {"name":{"type":"string"},"value":{},"se":{},"source":{"type":"string"},
                     "test":{"type":"string"},"sha256":{"type":"string"}}}},
    "algorithm": {"type":"object","required":
      ["profile_integration_sha256","grid","p3","gradient_battery","optimizer_gate","curvature_gate"],
      "properties": {
        "profile_integration_sha256": {"type":"string","pattern":"^[0-9a-f]{64}$"},
        "grid": {"type":"object","required":
          ["base","ratio_expr","ratio_f64","full_domain","cap_ladders_diagnostic","max_nodes","test"]},
        "p3": {"type":"object","required":["eps_domain","eps_grid","l_max","nested_construction","test"]},
        "gradient_battery": {"type":"object","required":["fd_step","tol_abs","tol_rel","point_set","d23_sentinel","test"]},
        "optimizer_gate": {"type":"object","required":
          ["method","lbfgsb_controls","restart_policy","tau_stat","dg_agree","du_agree","two_start","test"]},
        "curvature_gate": {"type":"object","required":
          ["h_sweep","center_h","logdet_stability","symmetry","directional_tol","direction_rng",
           "spd_required","rcond_min","retry_policy","stop_on_fail","test"]}}},
    "mcse_strategy": {"type":"object","required":
      ["estimator","iact_series","block_len_rule","block_cap_behavior","B","seed","test"]},
    "tolerances": {"type":"array","items": {"type":"object","required":
      ["name","value","rationale","tag","test"]}},
    "predicates": {"type":"array","items": {"type":"object","required":
      ["name","formula","threshold","fixture","failure","field","test","tag"]}},
    "historical_provenance": {"type":"object","required":["buggy_triplet","sum","note"]}
  }
}
```
**v1.18 result-manifest field contract (separate, append-only; references the immutable v1.17):**
```
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["freeze_version","kind","v117_manifest_sha256","frozen_at_git_sha","provenance",
               "profile_band_masses","numerical_sensitivity","realized_grids","gate_events"],
  "properties": {
    "freeze_version": {"const": "v1.18"},
    "kind": {"const": "m2c-gtoy-profile-result-freeze"},
    "v117_manifest_sha256": {"type":"string","pattern":"^[0-9a-f]{64}$"},
    "profile_band_masses": {"type":"object","required":["lo","mid","hi","sum"]},
    "numerical_sensitivity": {"type":"object","required":["delta_quad","delta_hess","delta_tail"]},
    "realized_grids": {"type":"object","required":["extended","refined_levels","band_edges"]},
    "gate_events": {"type":"object","required":["stop_count","retry_count","rcond_fail_count","undetermined"]}
  }
}
```
**Field-contract note (reconciling the value/formula question):** in v1.17, `references` and
`tolerances` entries carry a numeric `value`; `predicates` entries carry a `formula` + `threshold`;
`algorithm` sub-objects carry named numeric fields — each entry type has its appropriate field (there
is no single "value-or-formula" ambiguity). Every `references`/`tolerances`/`predicates` entry carries
its own `test`; and **each `algorithm` sub-object (grid, p3, gradient_battery, optimizer_gate,
curvature_gate, mcse_strategy) is covered by ONE named `test`** (a `test` field on the sub-object, not
one per numeric leaf — corrected per the rev-4 traceability note). CI asserts the manifest matches the
code constants (the v1.4 pattern). A revision is a **new addendum**, never an edit.

---

## 7. Consolidated PROPOSED numbers (for the vote)

| Area | PROPOSED numbers | Judgment-flag |
|---|---|---|
| P3 grid/domain | r = (1.2/0.005)^(1/39); **staged wider caps** (upper 10→1e4, lower 1e-4→1e-7; ×10/stage; support unbounded, caps are metadata-derived); δ_tail = cap-sensitivity (**NOT a bound**), STOP if ≥1e-4 at max cap; ε_grid=1e-4 (successive δ_quad^(ℓ)); L_max=3; nested = geometric-midpoint | — |
| Gradient battery (P1) | FD step 1e-5·scale; tol 1e-4 abs + 1e-4·scale; D23 sentinel | — |
| Optimizer gate | L-BFGS-B on the validated gradient; **maxiter 500, maxfun 5000, ftol 1e-12, gtol 1e-8**; 1 jittered restart on abnormal termination then fail; τ_stat=1e-4; agreement \|Δg\|≤1e-6·max(1,\|g\|), ‖Δu‖_∞≤1e-4; both starts valid | — |
| Curvature gate | h∈{5e-4,1e-3,2e-3}, center 1e-3; logdet-stability 1e-3; symmetry 1e-6; directional 1e-3 (RNG: numpy default_rng seeds {200,201,202}, float64, unit-L2, order ls/os/lv); **SPD + rcond=λ_min/λ_max ≥ 1e-8, NO flooring, retry-then-STOP** | J1 no-floor **DIRECTED**; rcond≥1e-8 **PROPOSED** (umbrella vote) |
| MCSE_strategy | MBB on the Q2 soft-contribution IACT (global shift); ℓ=⌈2τ_int⌉ (UNDETERMINED if T−ℓ+1<2); B=1000; seed 20260712 | — |
| Numerical error | δ_quad, δ_hess, δ_tail reported separately; optional max = heuristic envelope (not a bound) | — |
| S2 | η₀=1e-5; skew 1e-5; step-stability **1e-3**; whitening 1e-8; oracle 1e-10; λ_min≥1e-6, n_clipped=0 | J2 **selected** 1e-3 (umbrella vote) |
| S3 | slogdet/round-trip 1e-10; density 1e-9; gradient 1e-4+1e-4·scale; 33 states (21 interior + 12 enumerated boundary); M0-only | — |
| Divergence | rate 0.001 (frozen); factor 3; floor 2; window 10% per-chain; unique-index check | — |
| Overlap | q_overlap ≤ 0.05; **alignment 0.90** (a priori) | J3 **selected** 0.90 (umbrella vote) |
| Nugget floor | flag p_below^{M1} > 0.05; ref 1.9e-4 (frozen); strict `<`; **REPORT-ONLY** | J4 **selected** report-only (umbrella vote) |

**Frozen, not open (preserve exactly):** divergence rate 0.001; M1 correlation cap 0.95; eigenvalue
floor 1e-3 (M1 gate); nugget reference 1.9e-4; SIR 0.441; prior-IS/RW-MH reference numbers.

---

## 8. What this package does NOT do

No number here is frozen; no v1.17/v1.18 appended; no compute/recompute/sampler run; no Mauna access;
holdout SEALED (§6.6); HMC only via `fit_hmc_e1`; VI + hmc_laplace withdrawn; A7 Della on hold (v1.8).
On ratification the two-stage freeze (v1.17 algorithm → gated deterministic recompute → v1.18 values)
proceeds under the standard gates (clean tracked tree, byte-exact hashes, passing tests, explicit
author `--execute`, stop-and-report).

---

## 9. Adversarial review provenance

- **rev-1 → rev-2:** codex gpt-5.6-sol (xhigh) adversarially reviewed rev-1 → **CHANGES-REQUIRED**; all
  CONFIRMED source tags re-verified correct. Fixes applied in rev-2 (each cross-verified against
  source): relabelled [1e-4,10] as an inert-metadata search cap, NOT model support (config.py:282
  `Positive()`); **curvature gate SPD-only** — λ≤0 ⇒ STOP, never floored (τ_neg retry-only); added the
  **directional-curvature check** and the full **profile-gradient battery + D23 sentinel** (the P1
  spec); **exact nested-grid** construction (geometric-midpoint, retains nodes) + exact cap nodes +
  r as the exact expression; **cumulative-to-cap** tail criterion (not 3 local passes); **MCSE IACT on
  the Q2 soft-contribution series, not the Q3 hard winner** + complete MBB algorithm; numerical
  components are **sensitivity estimates, not a bound**; **two manifests** (immutable v1.17 + separate
  v1.18) with a real JSON-Schema (no placeholders); per-chain divergence window + unique-index check;
  **K_rest excludes M1**; **nugget flag 0.05** (not 0.50); S2 skew 1e-5, step-stability 1e-3, λ_min≥1e-6;
  enumerated S3's 12 boundary states. Four judgment flags (**J1** profile eigenvalue floor, **J2** S2
  step-stability, **J3** overlap 0.90-vs-0.95, **J4** nugget blocking-vs-report) are surfaced for the
  author, not silently resolved.
- **rev-2 → rev-3:** codex verified rev-2 → 8/15 items RESOLVED, the rest PARTIAL, catching **two
  math errors** (both fixed in rev-3, cross-verified): the **directional-curvature sign** (K = −H_g and
  g is maximized, so vᵀKv ≈ **−**D²_g(v), not +D²_g(v) — the old form would reject valid positive
  curvature) and the **Q2 IACT global shift** (a per-draw `max_j` shift distorts autocorrelation; use
  `soft_transfer`'s single global shift). Plus precision fixes: successive-level δ_quad^(ℓ) so the
  refinement gate advances; the tail criterion rewritten to always extend to the cap with δ_tail =
  outermost-shell mass (removing the cap self-contradiction); MBB UNDETERMINED when < 2 distinct blocks;
  grid arithmetic (last upper node 1.2·r^15 ≈ 9.88, max 86 nodes with edges); the "smallest reportable
  SE" label corrected to the mid band 0.003838 (hi is non-reportable); executable + time-isolating
  divergence fixtures; and a v1.18 result schema + value/formula reconciliation. Frozen values
  (divergence 0.001, correlation 0.95, eig floor 1e-3, nugget 1.9e-4, SIR 0.441) untouched; over-reach
  check PASS across both rounds.
- **rev-3 confirmation: APPROVE-WITH-CHANGES.** codex confirmed **both math fixes** (directional-
  curvature sign; Q2 global-shift IACT) and the tail/refinement/grid/SE-label/manifest fixes, with
  three cosmetic residuals — all now applied: §4's δ_quad synced to the successive-level definition;
  the §7 table's MBB block-length synced to §3 (ℓ=⌈2τ_int⌉, UNDETERMINED if <2 blocks); and the
  divergence fixtures fully enumerated with explicit per-chain indices. Frozen values (0.001, 0.95,
  1e-3, 1.9e-4, 0.441) verified untouched; over-reach PASS across all three rounds. The package is
  internally consistent and executable; the open items are the four **author judgment flags J1–J4**,
  surfaced deliberately.
- **rev-4 (author decisions 2026-07-13 + five freeze fixes).** The author **selected (directional, not
  yet frozen)** J2=1e-3, J3=0.90 (fixed a priori, not post-hoc), J4=report-only, and directed
  **J1 = NO flooring**: SPD + a relative
  conditioning threshold. Applied: **J1** → §2c now requires λ_min>0 AND **rcond = λ_min/λ_max ≥ 1e-8**
  (PROPOSED), no flooring, retry-once-then-STOP (all prior flooring language removed). **Fix 1** → the
  single-cap outermost-shell check is replaced by a **staged wider-cap sensitivity protocol** (upper
  10→1e4, lower 1e-4→1e-7, ×10/stage; STOP at max cap; explicitly cap-SENSITIVITY, not a bound) plus
  the certified tail-envelope as the rigor-if-wanted alternative. **Fix 2** → frozen L-BFGS-B controls
  (maxiter 500, maxfun 5000, ftol 1e-12, gtol 1e-8; one jittered restart then fail). **Fix 3** → frozen
  direction RNG (numpy `default_rng` seeds {200,201,202}, float64, standard-normal, unit-L2, order
  ls/os/lv). **Fix 4** → J1's vague "smaller floor" replaced by the exact no-floor conditioning rule.
  **Fix 5** → P3 is described as numerical cap-sensitivity throughout unless the tail-envelope is
  adopted.
- **rev-4 consistency review: all SUBSTANTIVE rules CONFIRMED correct** (rcond=λ_min/λ_max is exactly
  the reciprocal spectral condition number, 1e-8 a defensible binary64 threshold; L-BFGS-B controls,
  direction RNG, J2/J3/J4, and all frozen values verified). It flagged **prose↔manifest sync gaps only**,
  now fixed: the v1.17 `curvature_gate` schema dropped `eig_floor`/`tau_neg_retry_only` and added
  `direction_rng`/`spd_required`/`rcond_min`/`retry_policy`; `grid` now requires the staged cap ladders
  (not a singular cap); `optimizer_gate` requires the frozen L-BFGS-B controls + restart policy; v1.18
  `gate_events` dropped `floor_count`; the retry now specifies its tolerances (gtol 1e-10, ftol 1e-14)
  and that the reported Hessian stays K^(1e-3) at the re-optimized u\*; the staged-cap uses one-sided
  per-end deltas; and the stale "J2 flag if 1% is preferred" and "per-shell/floor count" wordings are
  removed. No substantive rule changed; no compute/freeze/Mauna/holdout.
- **rev-5 (author's three final freeze-precision corrections, 2026-07-13).** (1) **P3 order dependence
  removed:** always evaluate the FULL maximum domain [1e-7, 1e4] (182 nodes) as the reported cap
  result; the final upper sensitivity compares [1e-7,1e4] vs [1e-7,1e3] and the lower compares
  [1e-7,1e4] vs [1e-6,1e4]; earlier decade stages are diagnostic-only; STOP if either final one-sided
  delta ≥ 1e-4 (still cap sensitivity, not a bound). (2) **Provenance corrected:** J1's no-flooring is
  author-DIRECTED but **rcond ≥ 1e-8 is Claude-PROPOSED**; J2/J3/J4 are author-**selected**, and
  **nothing is frozen until the P7 umbrella vote** — all "RATIFIED" labels relabeled accordingly.
  (3) **Manifest traceability made truthful:** each `algorithm` sub-object carries ONE named `test`
  field (not one per numeric leaf), and the prose is corrected to match. Author scientific note
  recorded: the staged cap-sensitivity route is preferred over requiring a certified envelope because
  profile-Laplace is corroborating, not the verdict authority. No new choices introduced; no compute.
