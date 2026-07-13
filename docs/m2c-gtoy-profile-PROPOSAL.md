# M2c — G-toy golden derivation + normalized profile band-mass recomputation — PROPOSAL

Status: **ARCHITECTURE REVIEWED AND DIRECTIONALLY RATIFIED** (author own-words vote, P1–P8,
2026-07-12); **NUMERICAL FREEZE INCOMPLETE.** The architectural direction is settled; the exact
numbers (P3 grid/domain protocol, optimizer/curvature gates, chain-aware MCSE, the five remaining
§6.15 predicates, a manifest schema) are owed as a **complete freeze package for a second explicit
vote** before any v1.17 freeze (see §10). This is **not** a freeze-grade document. Planning-only
artifact of the first
M2c session. It reconciles base plan §6.9 against the D22–D24 correctness findings and the M2bR
outcomes (v1.8 + D33–D38), then proposes — for author ratification, before anything is built or
run — (1) the normalized profile-integration algorithm, (2) the HMC-independent references and
their exact formulas, (3) the estimator-specific G-toy goldens and tolerances, and (4) the
structure of the versioned freeze addendum that must be committed **before** any toy or Mauna
pilot. **No implementation, no compute, no freeze, no Mauna access, no holdout touch has occurred
or is proposed in this session.** Nothing in this file changes a frozen M2bR artifact, driver,
manifest, protocol doc, or committed D-entry.

Precedence rule applied throughout (author instruction + prereg header): where base
`docs/plan-d19-mauna.md` §6.9 (pre-D22) conflicts with the prereg addenda
(`docs/prereg-addenda-d19.md` v1.3/v1.4/v1.6/v1.8 onward) or `Notes/DECISIONS.md` D22–D24 /
D33–D38, **the addenda and D-entries win.** No pre-D22 HMC/VI number, cached chain, or
pyro-autograd gradient is treated as a valid reference anywhere below.

---

## 0. Governing vocabulary — four quantity types (kept distinct everywhere)

Every G-toy comparison names which of these four it is; the do-not-conflate rules are frozen.

| # | Quantity type | Toy examples (this study) | Natural measure |
|---|---|---|---|
| Q1 | **Noise-band masses** (occupancy of the constrained-noise marginal in low/mid/high bands) | prior-IS 0.7627/0.1911/0.0463; RW-MH 0.796–0.843 / 0.140–0.175 / 0.016–0.037; corrected NUTS occ 0.7605/0.1856/0.0539; profile band masses (to be recomputed) | fraction of marginal mass |
| Q2 | **Model probabilities** (BMS\* instance posterior at τ=1) | SIR Sin+Linear **0.441**; corrected-NUTS Sin+Linear **0.4205 (td7) / 0.4220 (td10)** | probability over the candidate set |
| Q3 | **Hard-best-match rates** (fraction of predictive draws whose argmin metric is model j) | SIR Sin+Linear hard-win **0.696–0.707** at n\_pred=1000; corrected-NUTS hard-win 0.968/0.970 | fraction of draws |
| Q4 | **Diagnostic-only outputs** (never reportable as a result) | pooled BMS\* of a validation-FAILED cell; cross-chain SDs; leapfrog counts | — |

**Do-not-conflate (frozen):**
- Never compare a **Q2** number with a **Q1** number. In particular **never compare 0.42 (Q2,
  model probability) with 0.763 (Q1, low-noise band mass)** — the recurring category error.
- The numeral **0.696** is BOTH the *withdrawn* HMC model posterior (Q2, retired D22/D33) AND an
  *unaffected* SIR hard-best-match rate at n\_pred=1000 (Q3, 0.696–0.707). **Never conflate them.**
- The numeral **0.441** appears as a SIR **Q2** (model probability, τ=1). Its Q1 companion is the
  SIR noise occupancy ≈0.80/0.16/0.04. Keep them separate.

---

## 1. Reconciliation — base §6.9 vs v1.8 + D22–D24 + D33–D38

§6.9 predates D22. Each of its bullets is reconciled below; the governing authority is named.

| §6.9 bullet (base, pre-D22) | Disposition | Governing authority |
|---|---|---|
| **Reference** = "the D18 `toy_elicited` cached artifacts at pinned seeds" | **KEPT as the reference CONFIGURATION** (`toy_elicited`, N=20 data-elicited prior). The pre-D22 **HMC/VI** cached numbers within it are **RETIRED as validity targets**; the **prior-IS / SIR / RW-MH / MAP / profile** artifacts of that config survive (D22 affected HMC/VI/hmc\_laplace only). | v1.8 §1; D22; D38 §4 |
| **E1/S1f**: density/gradient/transform equivalence to the S1 pyro target (M2b battery) + "one S1f toy run whose draws pass the same diagnostics as **S1's cached run**" | Battery **KEPT** (frozen v1.4/v1.6). "Same diagnostics as S1's cached run" is **REPLACED**: an S1f toy run's draws are judged against the **independently preregistered** diagnostic thresholds (v1.4 / Gate G-B), never against a pre-D22 cached chain (retired). Cached scientific results may not define tolerances. | v1.4; v1.6; v1.8 §1; §6.7 G-B |
| **S1**: "reproduce its own cached 0.696-family (td7) … regression characterization ONLY — not a validity pass" | **The base §6.9 L648–650 obligation is a pinned-seed reproduction of the cached 0.696-family AS A REGRESSION CHARACTERIZATION** (never a validity pass). v1.8 §1 retires the 0.696-family as a *golden/validity target*; it does **not**, by itself, delete the historical regression role. **PROPOSED disposition (routes to ratification P5):** satisfy that historical role with the **existing** D18 cached artifact + the documented D22/D23/D33/D36 history — i.e. **no new legacy S1 run** (the task instruction bars making one mandatory). Any *new* legacy execution needs separate justification, quarantine (labelled non-golden), and explicit author authorization. Presented here as the proposed reading, not as already-settled. | v1.8 §1; D38 §4; §6.9 L648–650 |
| **S2/S3**: agreement with prior-IS 0.763/0.191/0.046 (±0.004/0.004/0.001) AND RW-MH 0.796–0.843 / 0.140–0.175 / 0.016–0.037 within pre-declared MC error, AND mass-faithful BMS\* Sin+Linear 0.441 at τ=1; "a coverage-repairing sampler must reproduce the mass-faithful answer, not the confined 0.696" | **KEPT and SHARPENED.** References survive (all HMC-independent). Two sharpenings: (a) update prior-IS to the **frozen v1.14 values** (0.762660±0.004283 / 0.191078±0.003838 / 0.046262±0.000866, verified @1e-12); (b) arbitration is the **frozen §6.8 combined-SE / MC-error** test, **not raw range inclusion**, and **prior-IS + SIR are ONE IS-family reference (not double-counted)**; RW-MH is the independent referee. | §6.9; v1.14; §6.8; D33; D34 §1 |
| **CAUTION**: profile triplet 0.763/0.138/0.023 sums to 0.924, historical-only, NOT a golden; M2c recomputes normalized profile band masses | **This proposal's item 2.** See §4. | §6.9 L657–666; D38 §4 |
| **S4**: Laplace marginal/moments vs profile quadrature + IS references on the toy | **KEPT**, with the profile quadrature replaced by the **corrected** normalized integration (§4). S4's adequacy analog (§6.7 G-B) uses the corrected-normalization profile masses. | §6.9; §6.7 G-B; v1.8 §3 |
| **SIR/IS**: reproduce SIR 0.441-family at pinned seeds within bootstrap MC error | **KEPT as-is** (UNAFFECTED); a reproducibility golden at pinned seeds. | §6.9; D22; audit §1 |
| **"Numeric tolerances: frozen at M2c"** | **This proposal's item 3 + §5**, frozen against **independent references' own MC error**, never against newly observed E1/S1f outcomes. | §6.9 L673–674; §6.15; v1.8 §1 |

**Two facts from M2bR that are INPUTS to (not completions of) M2c** (D37):
- **`toy_elicited` is SUPERSEDED** — the corrected, multi-chain-validated D33 V3/V4 result (Q2
  Sin+Linear ≈0.42; Q1 occ ≈0.76/0.19/0.05) replaces the withdrawn HMC 0.696-family. This is an
  E1/S1f-family output; it is a **feasibility input and cross-check**, **not** a tolerance-setter
  (using E1's own output to gate E1 is forbidden — v1.8 §1, v1.4/v1.6 discipline).
- **`informative` is ACCEPTED as WITHDRAWN/UNVALIDATED** (D38 §3). It is **non-blocking for G-toy
  solely because it is not the G-toy reference configuration** (§6.9 L641; D37 correction). It sets
  no golden and carries no replacement model-probability number.

---

## 2. HMC-independent references and formulas (exact, code-cited)

All references below score through the **unaffected** direct-likelihood path (`_mh_log_joint`) or
prior draws; none touches `_hmc_pyro_model` (D22), pyro autograd (D23), or `create_graph` Hessians
(D24). Source: `experiments/prior_sensitivity_study.py`.

### 2.1 Evidence-source independence map (frozen)

- **IS family (ONE source):** prior-IS **and** SIR. SIR resamples the prior-IS pools, so they share
  failure modes and are **not two independent confirmations**. Do not double-count them in any
  two-reference arbitration (D34 §1; W2 rev-3).
- **Independent referee:** RW-MH (`fit_mcmc_simple`, D13 measure) — a distinct code path (no pyro,
  no NUTS, no IS weights), crossing-verified.
- **Corroborator (deterministic, mode-based):** profile-Laplace quadrature — **corroborating-only,
  never a verdict alone** (§6.8).

### 2.2 Prior-IS band masses + delta-method SE — **Q1 authority** (L365–386)

For pooled draws θ with log-marginal-likelihood weights, w_i = exp(lml_i − max lml), tot = Σ w_i.
Bands on **constrained** noise: lo = {noise < 0.15}, mid = {0.15 ≤ noise ≤ 0.30}, hi = {noise > 0.30}
(`NOISE_SPLIT_LO=0.15`, `NOISE_SPLIT_HI=0.30`; the D12 basin boundary, L123–124).

- P(A) = Σ_{i∈A} w_i / tot = E\_prior[ML·1\_A] / E\_prior[ML]
- SE(A) = sqrt( Σ_i (w_i/tot)² (1\_A(i) − P(A))² )   (self-normalized-ratio delta method)
- per-band ESS(A) = (Σ_{i∈A} w_i)² / Σ_{i∈A} w_i²

Frozen toy_elicited pooled values (v1.14, verified vs the D18 record @atol=1e-12; pools
`ths (60000,4)` ×3 seeds {0,1,2}):

| band | mass | delta-method SE | reportable (≥5%) |
|---|---|---|---|
| lo | **0.762660** | ±0.004283 | yes |
| mid | **0.191078** | ±0.003838 | yes |
| hi | **0.046262** | ±0.000866 | **no** (0.0463 < 0.05) → B=2 |

Because the bands partition the draws at the exact constants 0.15/0.30, **prior-IS band masses sum
to 1 by construction** — this reference has **no** boundary-straddling defect (only the profile
quadrature does; §4).

### 2.3 SIR / Boltzmann BMS\* — **Q2 model probability** + **Q3 hard-best-match** (L654–702)

Resample idx ~ Multinomial(p = w / Σw), n\_pred = 1000, `sir_seed = SEED`, pooled `is_seeds`;
push the resampled hyperparameters through the D12 predictive extraction + `run_bms_star`.

- BMS\* aggregation (`_boltzmann_posterior`, matches `bms_star.soft_transfer`,
  `normalize_per_draw=False`, global-shift): for the G-matrix at τ, s\_j = mean over draws of
  exp(−G/τ − max)\_j ; return s / Σs. **Q2** = the τ=1 instance posterior.
- Hard-win fraction (**Q3**) = mean over draws of 1[argmin_j G\_ij = j].

Frozen toy_elicited SIR references (τ=1, pw\_kl\_vcal, n\_pred=1000):
- **Q2:** Sin+Linear **0.441 ± 0.005** (conditional bootstrap SE); independent-pool scatter
  **0.419 / 0.438 / 0.431** (three prior-IS pools; D34 §1, W2 rev-3) — the two W5 uncertainty
  layers, reported **separately, never combined**.
- **Q1 companion (DIAGNOSTIC-ONLY):** SIR noise occupancy ≈ **0.799 / 0.156 / 0.045** (W2 rev-3;
  D33 rounds it to 0.80/0.16/0.04). The code records this as **three point fractions with NO
  bootstrap SE** (L754), so it is **diagnostic-only unless a resampling-uncertainty formula is
  preregistered** (codex round-2 items 8–9); the IS-family Q1 authority SE is the prior-IS
  delta-method SE (§2.2), not a SIR-occupancy SE.
- **Q3:** Sin+Linear hard-win **0.696–0.707** at n\_pred=1000. **This 0.696 is Q3, unaffected — not
  the withdrawn HMC 0.696 (Q2).**

### 2.4 RW-MH referee — **Q1 independent referee** (L849–872)

`fit_mcmc_simple` (D13 `_mh_log_joint`), 3 seeds {42,1,2} × 30 000 samples, 5 000 burn-in,
proposal\_scale 0.1; softplus(raw\_noise) → constrained noise; band occupancy on the same 0.15/0.30
edges; `lo_hi_crossings` = number of lo↔hi label flips.

- Frozen toy_elicited across-seed ranges: lo **0.796–0.843**, mid **0.140–0.175**, hi
  **0.016–0.037**; crossings **[44, 40, 38]** (G-referee floor ≥10/30k, easily met).
- **Authority precedence (frozen §6.8 L614–615): prior-IS (G-IS-passing) is the PRIMARY
  mass-bearing authority; RW-MH is the FALLBACK authority / independent referee** ("first available
  of: (1) an IS-family estimator that passed G-IS … then (2) the RW-MH referee"). RW-MH is not
  unconditionally "the authority" (codex round-2). When it *does* serve as authority, its point
  estimate is **pooled over ≥3 seeds** with **per-band SE proxy = half the across-seed range**;
  per-seed rows (code output, L849–872) are diagnostics.
- **Exact pooled RW-MH centers + half-range SE proxies (independently recomputed from the persisted
  per-seed rows, `runs/prior_sensitivity/results_noise_marginal_toy_elicited.json`; arithmetic only,
  no sampling):** pooled **lo 0.815644 / mid 0.161078 / hi 0.023278**; half-range SE proxies **lo
  0.023483 / mid 0.017650 / hi 0.010167**. These are the executable RW-MH reference numbers (codex
  round-2 supplied them; reproduced here byte-for-byte).
- NUTS is **not** required to lie inside every raw RW-MH range; the arbitration is combined-SE
  (§6.8), not raw inclusion.

### 2.5 Corrected-NUTS D33 V3/V4 — **cross-check INPUT, not a tolerance-setter**

Validated E1/S1f toy result (4 chains, overdispersed frozen starts, R-B pooled-800): **Q2**
Sin+Linear 0.4205 (td7) / 0.4220 (td10); **Q1** occ 0.7605/0.1856/0.0539 (V3) and
0.7602/0.1894/0.0504 (V4); **Q3** hard-win 0.968/0.970. Used only to demonstrate feasibility and as
a consistency cross-check; **never** to set an E1/S1f/S2/S3 tolerance (self-gating is barred).

### 2.6 Retired (never a reference)

Withdrawn HMC: Sin+Linear 0.696 (td7) / 0.683 (td10), occ 1.00/0.00/0.00 (D22 artifact). VI:
interim-withdrawn pending a corrected E1-based rerun (separate later milestone). `hmc_laplace`:
withdrawn (D22+D23+D24). No pre-D22 cache, pyro-path gradient, or `create_graph` Hessian is a
reference anywhere in M2c.

---

## 3. All corrections concern this repo, not the thesis

Every correction below concerns **this repository's pyro/gpytorch replication**, not the thesis's
original gpflow/ADVI implementation or its conclusions (v1.9 §1; audit scope rule). Every G-toy
golden statement carries this framing.

---

## 4. Normalized profile-integration algorithm (item 2)

### 4.1 The exact defect (characterized, not re-run)

`profile_laplace_noise_marginal` (L779–829) is D22/D23/D24-**immune**: it optimizes g(u) with
derivative-free Nelder-Mead over u = log(ls, os, lv), scores through the unaffected `log_joint` →
`_mh_log_joint` (L227–235), and forms the Laplace determinant from **finite-difference second
differences** of g (h=1e-3), not `create_graph` double-backward. Its **core** defect is the band
integration and normalization (`_profile_band_masses`, L832–846); three further gaps the corrected
protocol must close, none of which is the barred autograd family: (i) the v1.8 §3 obligation to
rebuild its Hessian on the shared **first-gradient** protocol (§4.3 — now mandatory, not optional);
(ii) the per-grid-point Nelder-Mead optimizer accepts `best.x` with **no success / stationarity
gate** (L796–804), so a non-converged u\* would corrupt g0 and H (§4.3a); (iii) the [0.005, 1.2]
grid truncates an **unbounded** LogNormal noise tail (`noise_prior=("lognormal", log 0.3, 1.0)`,
`Positive()`; config.py:152), so the truncation needs a real bound, not just a low endpoint density
(§4.2 step 6).

The buggy band step, on grid `np.geomspace(0.005, 1.2, 40)` with edges 0.15/0.30:

```
mask = (grid >= lo) & (grid <= hi);  band = trapz(m[mask], grid[mask]) / trapz(m, grid)
```

Because 0.15 and 0.30 are **off-grid**, the two grid intervals that straddle them are integrated by
**neither** adjacent band, yet are counted in `total`. Grid geometry (pure arithmetic on the known
grid; no model evaluated):

- edge 0.15 straddled by **[0.14579, 0.16778]** (grid[24], grid[25]);
- edge 0.30 straddled by **[0.29435, 0.33877]** (grid[29], grid[30]).

Both trapezoids drop out of every band → the triplet sums to **0.924**, missing ≈0.076 of the mass
(the two straddling slivers), exactly as §6.9 records. Two further leaks: the `mask.sum() < 2 → 0.0`
guard silently zeroes a thin band, and the support truncates at [0.005, 1.2] (tails beyond dropped).

### 4.2 Corrected algorithm (PROPOSED — one algorithm, all consumers)

Inputs: profile log-marginals {ℓ_k = log m(g_k)} on an ascending grid G (constrained/linear noise);
band edges e_1 < … < e_{B−1} partitioning the support into B bands (for the **toy** the FIXED
0.15/0.30; for **Mauna** the per-arm profile q25/q75, §6.8, obtained from Step 7).

1. **Common scale.** m_k = exp(ℓ_k − max_k ℓ_k). (Overflow-safe; the shift cancels in all ratios.)
2. **Insert every band edge as an integration NODE (exact re-evaluation primary).** Add a node at
   each off-grid edge e. **Primary (codex round-2 item 5):** evaluate the profile-Laplace marginal
   **exactly at e** (the full §4.3/§4.3a machinery — optimize u, SPD Hessian, Laplace determinant),
   giving the true log m(e) rather than a linear guess. **Regression check:** the linear-interpolant
   split m(e) = m_k + (m_{k+1} − m_k)(e − g_k)/(g_{k+1} − g_k) is retained as a **total-preservation
   test** (it splits the straddling trapezoid without changing `total`). *The exact partition
   Σ_b band_int_b = total holds for EITHER value* — exactness comes from e being a **shared node**,
   not from its value — so exact re-evaluation is strictly more accurate at no normalization cost.
   Inserting the two band-edge nodes (0.15, 0.30) is **§6.9-authorized** ("boundary points inserted
   or straddling intervals split", L661), **not** a frozen-grid amendment. Call the augmented grid
   G′.
3. **Trapezoid with an exact partition (float-safe).** band_int_b = trapz over [e_{b−1}, e_b]
   (e_0 = min G′, e_B = max G′), and **define total := Σ_b band_int_b** rather than a separate
   `trapz(m′, G′)` call. Because every edge is a shared node, the composite trapezoid rule is
   additive over the subintervals, so this Σ **equals** the whole-grid trapezoid **algebraically**;
   defining `total` as the sum makes **Σ_b P_b = 1 to machine precision** and removes any
   independent-`trapz` roundoff (the subagent measured the two `trapz` routes agreeing to 5.6×10⁻¹⁷,
   but defining total as the sum makes the invariant exact by construction — codex unverified-concern
   4).
4. **Normalize.** P_b = band_int_b / total; **Σ_b P_b ≡ 1** by Step 3. This removes the 0.924 defect
   by construction.
5. **Non-PD handling: SPD required, materially-indefinite ⇒ STOP (no fabricated mass; codex round-2
   curvature item).** Regularization must **not** invent profile mass: a materially indefinite −H means the
   conditional optimum is **not a valid Laplace mode**, and flooring its eigenvalues to positive
   would fabricate a finite determinant (hence spurious m). Rule: let **K = −H**; K must be **SPD**
   (all eigenvalues positive) at the gated stationary optimum (§4.3a) before the Laplace value is
   accepted. **Flooring is permitted ONLY for already-positive eigenvalues below the frozen 1e-3
   floor** (§6.15 eigenvalue floor), after the step-size stability check; **any materially
   non-positive eigenvalue is a STOP**, not a value. Every floor event and every STOP is reported.
   This replaces both the buggy `<2 → 0.0`/silent-`−∞` behaviour **and** the earlier draft's
   over-permissive "regularize every point finite": the circular "classify a `None` point by its
   undefined mass" is resolved not by inventing a value but by **STOP-on-indefinite**.
6. **Support / tail rule — convergence, not a hand-wave (codex round-3, critical fix).** The noise
   support is **unbounded** (LogNormal prior, `Positive()`; config.py:152), and the reported marginal
   is a **Laplace approximation** (L779). So neither a low endpoint density nor a naive
   "MAP-likelihood × prior-tail" product bounds the omitted tail: **the MAP maximizes L·p, not L**, so
   its likelihood is not an envelope, and a bound on the *exact* marginal need not bound its Laplace
   approximation. Two rigorous options; **recommend (A):**
   - **(A) Preregistered domain-extension convergence (recommended; amends the frozen grid → P3).**
     Extend the upper endpoint geometrically (same ratio) by additional nodes until **every
     normalized band mass changes by < a frozen tolerance ε_domain between successive extensions** — a
     convergence criterion, needing no analytic envelope — with a frozen maximum domain and
     **fail = STOP**. The lower end (η→0) is treated symmetrically. Because it adds nodes beyond
     [0.005, 1.2] it **amends the frozen 40-point grid** (§6.15 L811), so it is ratified up front as
     part of **P3**.
   - **(B) Certified tail bound on the frozen grid (alternative; more delicate).** Valid only with a
     **proven likelihood envelope U(η) ≥ max_φ L(y|φ,η)** — the **global** max likelihood, **not** the
     MAP — AND a separate bound closing the Laplace-vs-exact gap; then ∫ U(η)·p_η(η) dη (converted to
     the grid's shifted `exp(logm − max logm)` scale) is a genuine residual bound. Kept as a documented
     fallback, not the default.
   **Comparability:** prior-IS / RW-MH hi-band masses capture the full (0.30, ∞) tail, so the profile
   hi-band must reach convergence (A) or carry a certified residual (B); the outcome and endpoints are
   recorded in the dossier. **Likely consequence:** rigorous tail handling probably requires the P3
   domain-extension amendment — the frozen 40-point grid alone cannot bound an unbounded tail without
   the delicate envelope (B).
7. **Quantiles for Mauna edges (§6.8) — exact quadratic inversion.** For a piecewise-**linear**
   density (the trapezoid model), the CDF is piecewise-**quadratic**: on [g_k, g_{k+1}],
   ΔF(x) = m_k·x + ½·(m_{k+1}−m_k)/(g_{k+1}−g_k)·x² (x measured from g_k). The q-quantile therefore
   **solves that quadratic exactly** within the containing interval (codex defect 7); inverse-*linear*
   interpolation of F is only an approximation. Use exact-quadratic inversion; the q25/q75 edges feed
   back into Steps 2–4. (Toy edges are the FIXED 0.15/0.30 — this step is Mauna-only.)
8. **Quadrature grid — what is authorized vs what is an amendment.** §6.15 L811 freezes **"profile
   grid 40 points"** in the *non-adjustable* list. **§6.9 authorizes ONLY band-edge insertion /
   straddling-interval splitting** (Step 2) — nothing else. The **minimal no-amendment path** is: the
   frozen `geomspace(0.005, 1.2, 40)` grid **+ the two band-edge nodes (Step 2)**, with the tail
   handled by the **certified within-grid bound (Step 6 option B)** *if it suffices*. **All three of**
   grid **densification** (≥200 pts), **log-noise re-parameterization**, and **domain extension
   (Step 6 option A)** **amend the frozen 40-point grid** and require explicit ratification — bundled
   as Decision **P3**. Because rigorous tail handling on an unbounded support likely needs option A
   (Step 6), **the P3 domain-extension amendment is the probable path**, not the minimal one. If any
   P3 change is ratified, its convergence check (expansion factor, stopping tolerance, max domain,
   grid-doubling tolerance, fail=STOP) **is itself frozen before compute**, never decided after seeing
   whether the 40-point result "looks material".

### 4.3 Profile-Laplace Hessian — MANDATORY first-gradient shared protocol (v1.8 §3)

**Correction (codex defect 1): this is not an optional author decision.** v1.8 §3 binds "EVERY
consumer of a GP-hyperparameter Hessian … any profile-Laplace machinery" to "**central differences
of validated first gradients**" (prereg v1.8 L640; echoed by D24 L1625). The profile-Laplace Hessian
is exactly such a consumer, so it **must** move off its current second-differences-of-values
construction onto validated-first-gradient differencing. (Its D24-immunity — FD of *values*, not
`create_graph` — spares it the *silently-wrong-Hessian* failure, but v1.8 deliberately widened the
protocol beyond D24-immunity; overriding it would itself require an explicit amendment.)

Compliant construction to freeze:
1. **Establish a validated first gradient of the profile potential g** = log_joint(exp(u), noise) +
   Σu over u = log(ls, os, lv). The profile potential uses the **direct** `_mh_log_joint` path
   (unaffected), *not* the E1 `E1Potential`. So M2c must expose g's gradient through a **functional,
   no-`.data`-write path** (the E1 pattern — `torch.func.functional_call` — so the D23 deep-copy
   graph-severing does **not** apply), and **validate it against central finite differences of g**
   (an E1-style gradient gate for the profile potential), with a **D23-style sentinel** asserting the
   naive `.data`-injection gradient stays disconnected. **Open sub-question P1:** whether to build
   this functional gradient path or, if that proves disproportionate for a corroborating-only
   reference, to seek an explicit v1.8 amendment permitting validated **second differences of g**
   for the profile-Laplace specifically. *Recommend building the functional gradient path* (keeps the
   profile inside the frozen protocol; small surface).
2. **Assemble H by central differences of that validated gradient**, with a **step-size stability
   sweep** (h ∈ {5e-4, 1e-3, 2e-3}; log|−H| stable to a frozen tolerance), **symmetrization**,
   **directional-curvature verification** against second differences of g along seeded unit
   directions, and the **SPD requirement of §4.2 Step 5** — K = −H must be SPD; floor **only**
   already-positive eigenvalues below the frozen 1e-3 floor; **any materially non-positive eigenvalue
   is a STOP, never regularized into mass**. Floor events and STOPs are reported per point.

Because the profile-Laplace feeds only the **corroborating** reference (§6.8, never a verdict alone)
the scientific risk is bounded, but the protocol changes the profile VALUES and so **must be frozen
before** the recompute.

### 4.3a Profile-Laplace conditional-optimizer gate (codex defect 10)

The current code accepts the Nelder-Mead result `best.x` with **no convergence check** (L796–804).
Freeze a per-grid-point **fail-closed** gate, ALL mandatory (codex round-2 optimizer item — no "or"):
`best.success`, a **finite objective**, **gradient-stationarity** (‖∇g(u\*)‖ below a frozen tolerance
using the validated gradient of §4.3), and **positive curvature** (K = −H SPD per §4.2 Step 5).
**Multi-start agreement** (warm-start vs mode-start optima within a frozen tolerance) is an
**additional** check, **never a substitute for stationarity** — two optimizers can agree at the same
non-stationary point. Any failure is a **STOP** (never a silently accepted u\*). This supplies the
verification the recomputation currently lacks; it does not assert the historical optimization
failed.

### 4.4 Scope — where the corrected integration applies (frozen)

The single corrected algorithm (§4.2) replaces `_profile_band_masses` **everywhere a profile
band-mass is computed** (§6.9 L664–665): (a) Stage-A dossiers; (b) the §6.8 two-reference-arbitration
corroborator (including the Mauna per-arm q25/q75 edge derivation, Step 7); (c) S4 adequacy (§6.7
G-B analog); (d) the toy S4 / profile G-toy reference (§5).

### 4.5 Two-stage freeze + validation plan (no numbers frozen in this session)

The corrected profile triplet is a derived value produced **under** a ratified freeze, in **two
append-only stages** (codex unverified-concern 3; §6.16 append-only):

- **Stage 1 — algorithm freeze (pre-compute):** the addendum (§6) pins, by sha256, the corrected
  integration algorithm (§4.2), the Hessian + gradient protocol (§4.3), the optimizer gate (§4.3a),
  the tolerances (§5), and the reference numbers (§2). **No profile value is computed yet.**
- **Deterministic recompute (gated):** run the frozen profile-Laplace recompute on the toy. This is
  a **deterministic** computation (no sampler, no Mauna, no holdout) but still executes study code,
  so it is gated the same way: clean tracked tree, byte-exact algorithm/plan hashes, passing tests,
  and an explicit author `--execute`, then stop-and-report. Independent byte-for-byte reproduction of
  the derived triplet by a second implementation; the **Σ_b P_b = 1** invariant asserted; the
  regularization / optimizer / tail disclosures recorded.
- **Stage 2 — result freeze (post-compute):** a second append-only addendum pins the corrected
  band-mass VALUES with **numerical error/sensitivity bounds** — **not statistical SEs** (the profile
  is deterministic; codex round-2/3), unless a resampling procedure is separately defined. The three
  error/sensitivity components: (i) **quadrature discretization** — the composite-trapezoid bound
  |E| ≤ (b−a)/12 · h_max² · max|m″| requires a bound on max|m″| over the *continuous* interval, which
  **finite differences at the 40 nodes cannot certify** (round-4); a defensible error figure
  therefore needs **grid-refinement / Richardson** (the P3 amendment) or an analytic curvature bound,
  so this component is a **grid-sensitivity estimate contingent on P3**, not a frozen-grid
  certificate; (ii) **step-size stability** from the §4.3 Hessian h-sweep (obtainable on the frozen
  grid); (iii) the **tail residual** from §4.2 Step 6 (domain-extension convergence (A), a P3
  amendment, or the certified envelope (B)). The historical buggy triplet (persisted **0.76262 /
  0.13752 / 0.02311**, sum 0.9232; §6.9 rounds to 0.763/0.138/0.023) is retained verbatim beside them
  as HISTORICAL-only provenance. Both stages precede any Mauna pilot.

---

## 5. Estimator-specific G-toy goldens + tolerances (item 1 + item 3)

Reference configuration: **`toy_elicited`** (N=20 data-elicited prior), pinned seeds. Tolerances
are set from the **independent references' own MC error** via the frozen §6.8 / §6.15 conventions —
never from newly observed E1/S1f/S2/S3 outcomes (v1.8 §1). "Q1/Q2/Q3" tag the quantity type (§0).

| Strategy | Golden reference(s) | Tolerance FORM (frozen conventions; numbers instantiated at freeze) | Not a target |
|---|---|---|---|
| **E1 / S1f** | (a) M2b equivalence battery (frozen v1.4/v1.6: potential vs corrected oracle; gradient vs **central FD of the oracle** + E1's own FD, D23 sentinel; directional Hessian via **first-order FD of the E1 gradient**, D24 sentinel). (b) One S1f toy run judged against **independently preregistered** G-B diagnostics. | (a) the frozen v1.4/v1.6 battery bounds (potential 1e-9 rel; gradient 1e-4 abs+1e-4·scale; Hessian 1e-3 rel; etc.). (b) G-B (§6.7): split-R̂ ≤1.05, bulk & tail ESS ≥100/site, div ≤0.1%, depth-sat <10%, coverage via the two-reference arbitration (§6.8), seed reproducibility, interpretability, feasibility. | any pre-D22 cached chain; D33 V3/V4's specific numbers (feasibility input only). |
| **S1 (legacy pyro)** | HISTORICAL provenance only: the existing D18 cached 0.696-family (Q2) + the D22/D23/D33/D36 documented history. | **None — not a gate.** No new run mandatory. A new legacy run needs separate justification + quarantine (non-golden) + author authz. | never correct behaviour; never a validity target. |
| **S2 / S3** | **Q1:** IS-family band masses (**primary authority** prior-IS 0.762660±0.004283 / 0.191078±0.003838 / 0.046262±0.000866; SIR same family) + **fallback authority / independent referee** RW-MH (pooled **0.815644 / 0.161078 / 0.023278**, half-range SE **0.023483 / 0.017650 / 0.010167**). **Q2:** mass-faithful SIR Sin+Linear **0.441** at τ=1. Corroborator: corrected profile masses (§4). | **Q1:** §6.8 combined-SE pass — \|chain occ − authority mass\| ≤ 2·√(SE\_auth² + SE\_chain²) per reportable band, SE\_chain = √(p(1−p)/bulk-ESS); corroboration within 3·SE\_auth; **authority precedence = prior-IS (G-IS-passing) first, RW-MH fallback** (§6.8 L614–615); **prior-IS + SIR not double-counted**. **Q2 — TWO SEPARATE conditions (codex round-2 item 7): (i) G-C PRECISION** — the reported probability's functional MCSE ≤ 0.02 (§6.7 G-C floor); **(ii) AGREEMENT with SIR** — \|p\_strategy − p\_SIR\| ≤ 2·√(MCSE\_strategy² + MCSE\_SIR²) (§6.15 L795 two-estimator convention). **`MCSE_strategy` MUST be a CHAIN-AWARE estimator** (stratified batch-means or moving-block bootstrap) because the strategy's MCMC predictive rows are **autocorrelated** — an ordinary row bootstrap underestimates it (codex; exact estimator + block structure frozen in the freeze package §10). The two W5 layers (conditional-bootstrap MCSE vs independent-pool scatter 0.419/0.438/0.431) are reported **separately, never combined**. **NOT raw range inclusion.** The §6.15-M2c **S2 mass-convention** + **S3 Jacobian-log-det/equivalence** tolerances are frozen in the same umbrella package (§6, P7). | the confined 0.696 (Q2, retired); a coverage-repairing sampler must hit the **mass-faithful** answer. |
| **S4 (MAP+Laplace)** | **VALIDITY (Q1 approximation-adequacy only):** S4's noise-marginal band masses vs the **corrected** profile quadrature (§4) and the IS-family references. **Q2 DIAGNOSTIC-ONLY:** S4's BMS\* Sin+Linear at τ=1 reported beside SIR 0.441 (not a validity target — base §6.9 L668 "no single cached headline is its target"; elevating it is fork **P8**). | **VALIDITY:** §6.7/§6.15 G-B S4 analog — S4 band masses within **0.10 absolute** of the corrected-normalization profile quadrature per reportable band (plan §6.15 L806); no non-MAP mode >5% of the mass-bearing authority. **Q2** carries no gate unless P8 ratifies one. Every *gated* S4 quantity has an executable numeric tolerance. | no single cached headline is S4's target (§6.9 L668). |
| **SIR / IS** | **GOLDEN = Q2 only:** reproduce the SIR 0.441 model probability at pinned seeds. **Q1 SIR occupancy (0.799/0.156/0.045) is DIAGNOSTIC-ONLY** — not part of the golden. | **Q2 (the golden):** within **conditional-bootstrap MC error** — the code's `n_boot=1000` machinery bootstraps **G-matrix rows for BMS probabilities only** (L725), so this tolerance is Q2-only; pinned `sir_seed`/`is_seeds`, n\_pred=1000. **Q1 carries NO pass/fail tolerance** (the code records three point fractions with no bootstrap SE, L754); it is reported as a diagnostic unless a resampling-uncertainty formula is separately preregistered (codex round-2/3). | — (Q2 UNAFFECTED; a pure **Q2** reproducibility golden — Q1 excluded). |

**Tolerance-setting discipline (frozen):** every number above is either a frozen §6.8/§6.15
convention or an **independent-reference** MC-error quantity (prior-IS delta-method SE; RW-MH
across-seed range; SIR bootstrap MCSE). No tolerance is read off an E1/S1f/S2/S3 output. The
corrected-NUTS D33 V3/V4 numbers appear only as consistency cross-checks (§2.5).

---

## 6. Structure of the versioned freeze addendum (item 3)

**Scope note (codex defect 2).** §6.15 assigns **seven** predicates to M2c: (a) "G-toy per-estimator
numeric tolerances" (L821) and (b) "Corrected normalized profile-Laplace band masses …" (L828) —
**both covered by this proposal** — plus five others: (c) **S2 mass-convention test tolerances**
(L819), (d) **S3 Jacobian log-det + equivalence tolerances** (L820), (e) **divergence non-clustering
predicate** (L822), (f) **spectral/covariance overlap diagnostic** for the M1 duplication gate
(L823), and (g) **M1 nugget-floor formal predicate** (L824). This proposal is the **G-toy + profile
slice** of M2c. Per codex round-2 item 11, M2c freezes as **ONE umbrella package**: **all seven**
predicates must carry **exact formulas, thresholds, tests, and sha256 hashes and land together
before ANY compute or pilot** (companion specification documents are acceptable, but committed
together — no staggered partial freezes). Items (c)–(g) are therefore owed as companion specs within
that umbrella; (c)/(d) touch the S2/S3 goldens (§5) directly. Fully specifying (e)–(g) — the
divergence non-clustering predicate, the spectral/covariance overlap exact form, and the M1
nugget-floor predicate — is substantial work beyond this profile/G-toy slice and is flagged, not
drafted here. See Decision **P7**.

To be appended to `docs/prereg-addenda-d19.md` **after author ratification and before any toy or
Mauna pilot** (append-only; never edits an earlier addendum), as the **two-stage freeze** of §4.5.
Version number: the addenda file ends at **v1.15**; **v1.16 is the M2bR run/protocol label**
(manifests `docs/m2br_freeze/v116_*.json`; D34/D36 titles) — never an addendum — so the M2c
algorithm freeze should be **v1.17** to avoid the semantic collision, with the post-compute result
freeze as v1.18 (author to confirm numbering — Decision P4). The v1.17 (algorithm) addendum freezes,
byte-exact:

1. **The four-quantity vocabulary + do-not-conflate list** (§0).
2. **The reconciliation dispositions** (§1) — what §6.9 bullets survive/change and the governing
   authority for each.
3. **The HMC-independent references** with exact formulas + the frozen toy_elicited numbers (§2),
   and the evidence-source-independence map (no double-counting prior-IS with SIR).
4. **The normalized profile-integration algorithm** (§4.2) + the Hessian protocol (§4.3) + the
   support/tail + quadrature-space + convergence decisions (P1/P2/P3) + the scope list (§4.4).
5. **The estimator-specific goldens + tolerances** (§5), each tagged to a frozen §6.8/§6.15
   convention or an independent-reference MC-error quantity.
6. **Freeze-before-run gates:** the algorithm/params/reference-numbers pinned by sha256; independent
   byte-for-byte reproduction of any derived freeze (the corrected profile triplet); the
   Σ\_b P\_b = 1 invariant; retention of the historical 0.924 triplet as provenance-only.
7. **What it does NOT change / authorize:** no §6.7 gate value, no arm, no candidate set, no M2bR
   frozen artifact; **no HMC via anything but `fit_hmc_e1`**; no VI/`hmc_laplace`; **no Mauna
   access; holdout SEALED (§6.6)**; A7 Della on hold (v1.8).

---

## 7. Open decisions flagged for the author (ratification questions)

- **P1 — Profile-Laplace Hessian: how to source the validated first gradient (§4.3).** The shared
  v1.8 §3 protocol ("central differences of validated first gradients") is **mandatory**, not
  optional — so the only genuine fork is *how* to obtain g's validated gradient: **(a) build a
  functional (`functional_call`, no-`.data`) gradient path for the direct log-joint and validate it
  against central FD of g** (keeps the profile inside the frozen protocol), or **(b) seek an explicit
  v1.8 amendment permitting validated second-differences of g** for this corroborating-only
  reference. *Recommend (a).*
- **P2 — Boundary node value (aligned with §4.2 Step 2).** **Exact re-evaluation** of the
  profile-Laplace marginal at the band edges 0.15/0.30 is **primary** (more accurate; the partition
  stays exact because the edge is a shared node regardless of its value); the linear-interpolant
  split is retained **only as a total-preservation regression test**. *Recommend exact re-evaluation
  primary* — this now agrees with Step 2 (the earlier draft's "interpolate primary" is withdrawn).
- **P3 — Frozen-grid amendments (domain-extension + grid-refinement), PROBABLY REQUIRED.** A minimal
  no-amendment path exists (frozen 40-point grid + §6.9-authorized band-edge nodes), but it **likely
  cannot produce a freeze-grade result**: a defensible **quadrature-error estimate genuinely needs
  grid-refinement / Richardson** — a certified bound is **not** obtainable from finite differences on
  the 40 nodes alone (round-4) — and the **unbounded tail** is cleanest via domain extension (§4.2
  Step 6 option A), the within-grid envelope (option B) being the only no-amendment tail alternative
  and a delicate one. Both refinements **amend the frozen "40 points"** (§6.15 L811; §6.16 append-only
  permits this).
  Optional third: **log-noise re-parameterization**. *Recommend ratifying the P3 domain-extension +
  grid-refinement protocol up front*, with every convergence check (expansion factor, stopping
  tolerance, maximum domain, grid-doubling tolerance, **fail = STOP**) **frozen before compute**,
  never decided after seeing the 40-point result.
- **P4 — Addendum version number.** v1.17 (v1.16 is the M2bR run version)? Confirm.
- **P5 — S1 legacy provenance.** Accept that the existing D18 artifact + documented history satisfy
  the S1 historical-regression role, with **no new legacy S1 run**? *Recommend yes.*
- **P6 — E1/S1f toy-run gate vs D33 V3/V4.** Does the M2c E1/S1f G-toy toy-run requirement get
  satisfied by re-using D33 V3/V4 as the demonstrating run (with thresholds still frozen
  independently), or is a fresh pinned-seed S1f toy smoke required at G-toy? *Recommend a fresh
  pinned-seed toy smoke under the M2c freeze* (D33 was M2bR-scoped; keep the gate self-contained),
  with V3/V4 as the feasibility cross-check.
- **P7 — One umbrella M2c freeze package (codex round-2 item 11).** M2c freezes as a **single
  package** — all **seven** §6.15 predicates with exact formulas, thresholds, tests, and sha256
  hashes, **committed together before ANY compute or pilot** (companion specification docs
  acceptable; no staggered partial freezes). *Recommend*: fold (c) S2 mass-convention + (d) S3
  Jacobian-log-det into the S2/S3 golden freeze (they belong beside §5); (e)–(g) (divergence
  non-clustering, spectral/covariance overlap exact form, M1 nugget-floor) as companion specs — all
  landing together. **None may be skipped.** *(Note: (e)–(g) are substantial and not drafted in this
  slice.)*
- **P8 — S4 Q2 status (codex round-2 item 10).** Keep S4's BMS\* Q2 (vs SIR 0.441)
  **diagnostic-only**, with S4 validity resting on approximation-adequacy (§5), OR elevate Q2 to a
  validity target — which **changes base §6.9 L668** ("no single cached headline is its target") and
  needs explicit ratification. *Recommend diagnostic-only* (keep base §6.9).

---

## 8. What this proposal does NOT do

No implementation, no compute, no sampler run, no profile recompute, no number frozen. No append to
the frozen `docs/prereg-addenda-d19.md`. No change to any M2bR frozen artifact, driver, manifest,
protocol doc, or committed D-entry. No `git add runs/`. No Mauna access; the 60-month **holdout
stays SEALED** (§6.6). HMC remains available only via `fit_hmc_e1`; VI and `hmc_laplace` stay
withdrawn. The A7 Della vehicle stays on hold (v1.8). Real compute remains gated on a clean tracked
tree, byte-exact freeze/plan hashes, passing tests, and an explicit author `--execute`
authorization, followed by stop-and-report. **The five other §6.15-M2c predicates (§6 scope note)
are NOT frozen by this proposal and remain owed before any pilot.**

---

## 9. Adversarial cross-model review provenance (this milestone)

Two independent reviews ran against the repo source; every finding was cross-verified against
file:line before being acted on (both models are known to mix real defects with confident false
alarms).

- **codex gpt-5.6-sol (xhigh): CHANGES-REQUIRED.** All frozen numbers and the core algorithm math
  **PASSED** its independent re-derivation (prior-IS masses/SEs, SIR 0.441 / hard-win 0.696–0.707,
  RW-MH ranges, Boltzmann + occupancy formulas, the 0.924 defect, the edge-node correction, the
  linear-noise measure, D24-immunity — each with a source citation). It raised **10 executability /
  completeness defects**, all verified against source and **all folded into this revision**: (1)
  Hessian must be mandatory first-gradient per v1.8 L640 → §4.3; (2) five other §6.15-M2c predicates
  missing → §6 scope note + P7; (3) RW-MH pooled authority center per §6.8 L614 → §2.4, §5; (4) S1
  framing → §1; (5) circular non-PD predicate → §4.2 Step 5; (6) tail bound over unbounded LogNormal
  support → §4.2 Step 6; (7) quadratic CDF inversion → §4.2 Step 7; (8) SIR-occupancy bootstrap not
  implemented → §2.3, §5; (9) S4 moment tolerance → §5; (10) optimizer-success gate → §4.3a. Plus
  the float-exact invariant (`total := Σ band_int`) → §4.2 Step 3, and two-stage sequencing → §4.5.
- **Independent repo-reading subagent: SOUND.** Verified the profile-integration math **numerically**
  (Σ band_int − total = 5.6×10⁻¹⁷; normalized sum = 1.000000000000000; interpolation-split
  total-change = 0.000×10⁰), reproduced the grid arithmetic (dropped intervals exactly (24,25) and
  (29,30)), and confirmed every precedence disposition, no self-gating, and all four spot-checked
  numbers exact. No math/logic/precedence error.
- **Self-verified additionally:** §6.15 L811 freezes the **40-point profile grid** → flipped
  Decision P3 (densification is an amendment, not the default); and the toy noise prior is
  `("lognormal", log 0.3, 1.0)` with `Positive()` (config.py:152), confirming the unbounded-tail
  concern.

- **codex gpt-5.6-sol (xhigh) round 2: CHANGES-REQUIRED (all 11 items verified, all folded in).**
  On the revised draft it accepted the core partition correction but caught: (1) the tail "bound"
  was still an unproved extrapolation → §4.2 Step 6a now a genuine LogNormal-tail **domination**
  bound; (2) eigenvalue clipping could **fabricate mass** → §4.2 Step 5 / §4.3 now require **K = −H
  SPD, STOP on materially-indefinite**; (3) the optimizer gate's "stationarity **or** agreement" was
  unsafe → §4.3a makes **stationarity mandatory**; (4) domain extension is an **amendment**, not
  §6.9-authorized → §4.2 Step 6b/8, P3; (5) exact boundary re-evaluation should be **primary** →
  §4.2 Step 2, P2; (6) supplied the **executable RW-MH pooled centers/half-ranges** (independently
  reproduced by me from the persisted artifact — see below) + fixed authority precedence
  (prior-IS primary, RW-MH fallback); (7) **MCSE ≤ 0.02 is a G-C precision floor, not the agreement
  tolerance** → §5 now states both plus the exact agreement equation; (8) deterministic profile
  values carry **numerical error bounds, not SEs** → §4.5; (9) SIR Q1 occupancy **diagnostic-only**
  → §2.3, §5; (10) S4 Q2 vs SIR 0.441 must stay **diagnostic-only** unless ratified → §5, new P8;
  (11) M2c must freeze as **one umbrella package** → §6, P7.
- **Independent artifact verification (me, this session):** the RW-MH pooled centers **0.815644 /
  0.161078 / 0.023278** and half-range proxies **0.023483 / 0.017650 / 0.010167** reproduce
  byte-for-byte from `runs/prior_sensitivity/results_noise_marginal_toy_elicited.json` (arithmetic
  only, no sampling); the persisted buggy triplet is **0.76262 / 0.13752 / 0.02311** (sum 0.9232);
  §6.8 L615 authority precedence and §6.9 L668 S4 "no single headline" confirmed. codex round-2 had
  **no false alarms** this pass.

- **codex gpt-5.6-sol (xhigh) round 3: verified the revision — 8/11 resolved, then 4 items fixed
  here.** It confirmed items 2,3,4,6,7,8,10,11 resolved with line cites and confirmed the
  exact-quadratic quantile inversion (3b) SOUND. It caught, and this revision fixes: **(critical)**
  my §4.2 Step 6 tail "bound" still used the **MAP likelihood** (which maximizes L·p, not L, so is
  not an envelope) and ignored the **Laplace-approximation** gap → Step 6 is now **convergence-based
  (recommended domain-extension, P3)** with a correctly-stated global-max-likelihood envelope as the
  fallback; **(high)** P2 still said "interpolate primary", contradicting Step 2 → P2 now agrees
  (exact re-evaluation primary); **(medium)** §5 still listed SIR Q1 among goldens → now
  diagnostic-only with no tolerance; **(medium)** Stage 2's grid-error bound relied on unratified
  densification → now a **certified composite-trapezoid bound on the frozen grid**. Its "item 2/3
  label swap" (low) was a **verified false alarm** (my labels matched the authoritative round-2
  list); the refs were de-numbered anyway.

- **codex round 4 (focused): 4/5 fixes confirmed; 2 coupled items fixed here.** It caught that the
  "certified trapezoid bound via FD on the 40 nodes" is **not** certifiable (node samples don't bound
  curvature between nodes) and that P3 had gone stale against the rewritten Step 6/8. Both fixed: a
  defensible quadrature-error **estimate needs grid-refinement (P3)**, and P3 now says the frozen
  40-point grid likely can't be freeze-grade — the tail (domain-extension, option A) and the
  error estimate (grid-refinement) both drive the **P3 amendments**, which §6.16 permits.
- **codex round 5 (consistency): APPROVE-WITH-CHANGES.** Confirmed Step 6 / Step 8 / P3 / Stage 2
  now tell one consistent story with no dangling refs or plan conflicts; two cosmetic wording fixes
  ("bound components"→"error/sensitivity components"; P3 "bound"→"estimate") applied.

Net: the proposal's **references, numbers, and core corrected-integration math are independently
confirmed correct** across both models; **five review rounds** hardened its **architecture**
(SPD/STOP curvature safety, convergence-based tail handling, mandatory stationarity, the exact Q2
agreement equation, honest grid-error accounting, and the umbrella-freeze discipline), converging to
APPROVE-WITH-CHANGES. **Status (author, 2026-07-12): architecture reviewed and directionally ratified
(P1–P8); the NUMERICAL FREEZE is INCOMPLETE.** The exact P3/optimizer/curvature/MCSE numbers and the
five remaining §6.15 predicates are owed as the **complete freeze package** (§10) for a second
explicit vote before any v1.17 freeze. This document is **not** freeze-grade.

---

## 10. Author ratification (2026-07-12) + the owed complete freeze package

**Directional ratification (author own-words vote, 2026-07-12):** the architectural direction is
ratified as P1–P8 below; the **numerical freeze is explicitly NOT ratified**.

| Fork | Ratified direction |
|---|---|
| P1 | Functional `functional_call` gradient for the profile potential, validated against central FD. |
| P2 | Exact evaluation at 0.15/0.30 **primary**; interpolation only as the partition regression test. |
| P3 | A **prospective amendment** for domain extension + nested grid refinement is authorized **in principle** — **the numerical protocol is NOT yet ratified**. |
| P4 | **v1.17** = algorithm freeze; **v1.18** = derived results. |
| P5 | **No** new legacy S1 run. |
| P6 | Fresh pinned-seed S1f smoke **after** the complete freeze; D33 V3/V4 remain cross-checks. |
| P7 | **One umbrella** M2c freeze package — all seven predicates + any companion specs land together. |
| P8 | S4 Q2 stays **diagnostic-only**. |

**Owed next — the complete freeze package (a separate document, for a SECOND explicit vote):**
1. **P3 numerics:** nested grids + domain-extension protocol — expansion rule, lower/upper limits,
   stopping tolerance, required consecutive passes, maximum domain, grid-refinement/Richardson rule,
   `STOP` outcome. Described as **numerical convergence/sensitivity, not a proven tail bound**.
2. **Optimizer + curvature gates (exact numbers):** gradient-norm scaling, multi-start
   objective/state agreement, symmetry tolerance, Hessian-step stability, numerical-zero vs invalid
   curvature, permitted eigenvalue flooring.
3. **Chain-aware `MCSE_strategy`** for Q2 (exact batch/block structure + seeds), kept separate from
   the `MCSE ≤ 0.02` precision gate.
4. **Exact numerical-error reporting** for the deterministic profile masses — **never** labelled an SE.
5. **Full specs (formulas, thresholds, fixtures, failure behaviour) for the five remaining §6.15
   predicates:** S2 mass-convention, S3 Jacobian/equivalence, divergence clustering,
   spectral/covariance overlap, M1 nugget-floor.
6. **One manifest schema** listing every frozen value, its source, its test, and a sha256.

That package will be adversarially reviewed and returned for the author's second explicit vote.
**No v1.17 is appended, and no compute/recompute/sampler/Mauna/holdout is run, until then.**
