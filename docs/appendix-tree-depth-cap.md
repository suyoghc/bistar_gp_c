# Appendix: the NUTS tree-depth cap (max_tree_depth=7) on the thesis toy

> **WITHDRAWN/UNVALIDATED PENDING CORRECTED RERUN (D26/D28, 2026-07-11).** Every HMC, VI, and
> `hmc_laplace` number in this document was produced by this repository's
> pre-correction samplers: the D22 wrong-measure defect (target
> p(theta)L(theta)^N) and the D23 broken kernel-site gradients (VI's ELBO
> included), plus D24 for `hmc_laplace` (see `docs/d22-d24-impact-audit.md`).
> Those numbers are WITHDRAWN and UNVALIDATED pending the M2bR corrected
> reruns; they remain below strictly as provenance. They may be marked
> superseded only after validated replacements exist (D28 terminology rule). Unaffected here (audit
> table 1): MAP/MLE, prior-IS, SIR, corrected RW-MH, and prior-predictive
> quantities. This statement concerns THIS repository's pyro/gpytorch
> implementation only — it establishes nothing about the thesis's original
> gpflow/ADVI implementation or its conclusions.

Companion to `docs/fit-method-metric-comparison.md` (D12). The main comparison
ran the two NUTS methods uncapped (pyro default `max_tree_depth=10`); this
appendix reruns them capped at 7 and quantifies what the cap buys and costs.
Capped outputs are tagged `_td7` under `runs/fit_method_metric_comparison/`
(`results_td7.json`, `tables_td7.md`, `samples_{method}_td7.npz`); the
uncapped canonical files are untouched.

## Why a cap, and why 7

NUTS builds a binary leapfrog tree, so depth `d` bounds the trajectory at
`2^d − 1` leapfrog steps per iteration, each one a Cholesky factorization plus
a backward pass. When the posterior geometry is stiff — here, the bimodal
hyperparameter posterior of D12; on Mauna Loa, the near-zero-noise ridge of
D8 — the step size collapses and trees saturate, so the default `d=10`
(≤1023 steps) pays its full worst case on every iteration. Capping at `d=7`
(≤127 steps) cuts that worst case ~8×. The specific value 7 is the knee D8
validated head-to-head on the real-data Mauna Loa problem (1.04 s/it capped
vs 4.9–8.2 s/it uncapped, identical posteriors); reusing it here keeps the
toy and real-data samplers one consistent choice. The cap shortens
trajectories, not the target: the stationary distribution is unchanged in
principle, and what is traded away is within-iteration exploration.

## Setup

Identical to the main comparison in every respect (same data, seeds, budgets:
2000 draws / 1000 warmup, MAP init) except `max_tree_depth`. vi and map have
no tree depth; their capped-run draws are seed-identical to the uncapped ones.

Reproduce with:

    python experiments/fit_method_metric_comparison.py                     # uncapped
    python experiments/fit_method_metric_comparison.py --max-tree-depth 7  # capped

## Results

Wall-clock (2000 draws + 1000 warmup, N=20, Apple Silicon, single process):

| method | uncapped (d=10) | capped (d=7) | speedup |
|---|---|---|---|
| hmc | 20,295 s (5.6 h) | 2,326 s (39 min) | 8.7× |
| hmc_laplace | 20,803 s (5.8 h) | 2,337 s (39 min) | 8.9× |

Hyperparameter posteriors (constrained space; ESS = crude single-chain Geyer):

| method | hyperparameter | uncapped mean±sd (ESS) | capped mean±sd (ESS) |
|---|---|---|---|
| hmc | SE lengthscale | 1.4556±0.0640 (6) | 1.4567±0.0837 (11) |
| hmc | SE outputscale | 0.8493±0.1010 (4) | 0.8130±0.1218 (11) |
| hmc | Linear variance | 0.1722±0.0738 (27) | 0.1831±0.1371 (17) |
| hmc | Noise variance | 0.0527±0.0065 (10) | 0.0523±0.0080 (18) |
| hmc_laplace | SE lengthscale | 1.4139±0.0657 (30) | 1.4806±0.0719 (51) |
| hmc_laplace | SE outputscale | 0.7477±0.0908 (37) | 0.8165±0.1032 (59) |
| hmc_laplace | Linear variance | 0.1590±0.0801 (21) | 0.4096±0.5790 (5) |
| hmc_laplace | Noise variance | 0.0518±0.0051 (14) | 0.0545±0.0054 (21) |

BMS* model posteriors: max absolute shift across all five metrics at τ=1 is
**0.0015** (hmc) and **0.0108** (hmc_laplace); e.g. `pw_kl_vcal` at τ=1 moves
from [0.105, 0.115, 0.675, 0.105] to [0.106, 0.115, 0.673, 0.106] (hmc). The
hard best-match assignment (the thesis aggregation) is 200/200 Sin+Linear in
every capped cell, unchanged from uncapped. Both capped chains remain entirely
inside the likelihood mode (P(noise < 0.15) = 1.000), like their uncapped
twins — the cap neither causes nor cures the mode-blindness documented in D12;
that property belongs to the bimodal geometry.

## Reading

- **The cap is result-preserving at model-selection precision here** (shifts
  ≤0.011 in posterior probability, no rank changes) while cutting cost ~9×.
  This reproduces D8's Mauna finding on the toy, with the full BMS* pipeline
  downstream rather than only the hyperparameter posterior.
- **Per-second exploration improves**: within-mode ESS per 2000 draws is
  comparable or better capped (most rows up ~2×), so ESS per hour is roughly
  an order of magnitude better.
- **Caveat, honestly held**: these are single chains with a crude ESS
  estimator, and the capped hmc_laplace linear-variance row (0.41±0.58,
  ESS 5) shows a heavy-tail excursion the uncapped chain didn't take — at
  ESS this low, within-mode tail quantities are not stable in either arm.
  What is stable across all four chains is the mode location, the noise/
  lengthscale posteriors, and every model-selection output. Neither arm
  explores the second (prior-favored) mode; converged full-Bayes on this
  posterior needs a mode-aware strategy regardless of the cap (D12).
