# M2bR corrected-impact rerun — FROZEN protocol (prereg addendum v1.9)

Status: PROPOSED, PENDING EXPLICIT AUTHOR RATIFICATION (D28 provenance
correction; the v1.9 "author-authorized" label was wrong — forwarded
recommendations are not a vote). Purpose, corrected per D28: a CONTROLLED
HISTORICAL-IMPACT AUDIT — six single-chain runs mirroring the original
one-chain D12/D18 design so old and new numbers differ only in the sampler
correction. Single chains cannot validate basin exploration or convergence:
these results are labeled "corrected single-chain comparisons", are NEVER
paper-grade replacements, and CANNOT close W2/W3. Scientific validation
runs separately under docs/m2br-validation-protocol-PROPOSAL.md (multi-chain,
own budget). Executed only in the M2bR PR after the M2b merge and after
explicit ratification. Drafted by codex gpt-5.6-sol (xhigh) from the
committed study code with file:line citations; run list below unchanged
from the v1.9-pinned draft. The v1.10 addendum re-pins this file by sha256;
any change to the run list is a new addendum, never an edit.


## 1. Recovered original protocol

### Data and shared pipeline

- One fixed thesis-toy dataset for every run: `generate_toy_data()` defaults to `n_points=20`, `x_range=(-10,10)`, `noise_std=0.5`, `bias_slope=0.25`, `seed=42`; \(x\) is evenly spaced and \(y=\sin(x)+0.25x+0.5\epsilon\), \(\epsilon\sim N(0,1)\). `bistar_gp/data.py:41-64`
- Both D12 and D18 call the generator with no overrides. `experiments/fit_method_metric_comparison.py:378-384`; `experiments/prior_sensitivity_study.py:1911`
- Four MLE-fitted candidates: Linear, Sinusoidal, Sin+Linear, Quadratic. `docs/fit-method-metric-comparison.md:7-10`; `experiments/fit_method_metric_comparison.py:387-394`
- Evaluation grid: 60 points from `min(x)-1` to `max(x)+1`. `experiments/fit_method_metric_comparison.py:378-381`
- Each HMC run produces 2,000 posterior draws; 200 deterministically subsampled GP predictives are scored. `experiments/fit_method_metric_comparison.py:107-112,166-177,333-334`
- Metrics: `pw_kl_vcal`, `pw_nll_gp`, `pw_kl_mean`, `pw_hellinger_vcal`, `kl_forward`; \(\tau=\{0.1,0.3,1,3,10\}\), headline \(\tau=1\). `experiments/fit_method_metric_comparison.py:51-56`

### D18 configurations: exactly four

| Study key | Priors `(family, parameters)` | Bounds `(ls, os, lv, noise)` |
|---|---|---|
| `informative` | Gamma(6,0.85), Gamma(6,0.85), Gamma(6,0.85), Gamma(1.75,1) | `(0.5,30)`, `(0.1,20)`, `(0.01,20)`, `(1e-4,10)` |
| `vague` | LogNormal(0,2), LogNormal(0,2), LogNormal(0,2), LogNormal(-1,2) | `(0.1,100)`, `(0.01,100)`, `(0.001,100)`, `(1e-5,50)` |
| `toy_elicited` | LogNormal(log 4.5,0.9), LogNormal(log 1.5,1), LogNormal(log 0.04,1.5), LogNormal(log 0.3,1) | `(0.1,100)`, `(0.01,100)`, `(1e-4,10)`, `(1e-4,10)` |
| `gamma_relaxed` | Gamma(2,0.5), Gamma(2,0.5), Gamma(2,0.5), Gamma(1.75,1) | `(0.5,30)`, `(0.1,20)`, `(0.01,20)`, `(1e-4,10)` |

Sources: `experiments/prior_sensitivity_study.py:147-178`; `bistar_gp/config.py:56-80,121-154`.

### HMC settings

- `n_samples=2000`, `n_warmup=1000`, sampler seed `42`, one chain. `experiments/fit_method_metric_comparison.py:85-116`; `bistar_gp/e1_potential.py:290-297`
- Before every sampler call: fresh model, `torch.manual_seed(42)`, MAP fit for 300 iterations at `lr=0.05`; sampler initializes from that MAP. `experiments/fit_method_metric_comparison.py:128-149`
- Corrected rerun calls `bistar_gp.e1_potential.fit_hmc_e1` directly with `init_to_map=True`, `verbose=False`, `return_diagnostics=True`. E1 uses step size 0.1 with adaptation and target acceptance 0.8. `bistar_gp/e1_potential.py:249-263,270-299`
- Capped arms: `max_tree_depth=7`; uncapped/original-default arms: `max_tree_depth=10`. `experiments/fit_method_metric_comparison.py:91-116`; `experiments/prior_sensitivity_study.py:624-644,1883-1886`
- Only seed 42 was used for HMC. Seeds 0/1/2 belong to prior-IS, not HMC. `experiments/prior_sensitivity_study.py:122,1891-1896`

### Basin occupancy

Using the noise-variance sample site `likelihood.noise_covar.noise_prior`:

- low: noise `< 0.15`;
- middle: `0.15 <= noise <= 0.30`;
- high: noise `> 0.30`;
- report each fraction and total draw count.

`experiments/prior_sensitivity_study.py:122-125,576-585`

## 2. Frozen run list

Execution order is fixed to preserve the highest-priority D12 and adopted-prior comparisons if the deadline intervenes.

| # | Run ID | Config | Samples/warmup | Depth | Seed | Original cache represented | New corrected outputs |
|---:|---|---|---|---:|---:|---|---|
| 1 | `d12_informative_td7` | `informative` | 2000/1000 | 7 | 42 | `runs/fit_method_metric_comparison/samples_hmc_td7.npz` | `runs/m2br_corrected_impact/samples_d12_informative_td7_e1.npz`; matching `diagnostics_*.json`, `results_*.json` |
| 2 | `d12_informative_td10` | `informative` | 2000/1000 | 10 | 42 | `runs/fit_method_metric_comparison/samples_hmc.npz` | `samples_d12_informative_td10_e1.npz`; matching diagnostics/results |
| 3 | `d18_toy_elicited_td7` | `toy_elicited` | 2000/1000 | 7 | 42 | `runs/prior_sensitivity/samples_toy_elicited_hmc_td7.npz` | `samples_d18_toy_elicited_td7_e1.npz`; matching diagnostics/results |
| 4 | `d18_toy_elicited_td10` | `toy_elicited` | 2000/1000 | 10 | 42 | `runs/prior_sensitivity/samples_toy_elicited_hmc_td10.npz` | `samples_d18_toy_elicited_td10_e1.npz`; matching diagnostics/results |
| 5 | `d18_vague_td7` | `vague` | 2000/1000 | 7 | 42 | `runs/prior_sensitivity/samples_vague_hmc_td7.npz` | `samples_d18_vague_td7_e1.npz`; matching diagnostics/results |
| 6 | `d18_gamma_relaxed_td7` | `gamma_relaxed` | 2000/1000 | 7 | 42 | `runs/prior_sensitivity/samples_gamma_relaxed_hmc_td7.npz` | `samples_d18_gamma_relaxed_td7_e1.npz`; matching diagnostics/results |

The D12 td7 run is also D18’s frozen `informative` baseline; it is executed once and reused. `experiments/prior_sensitivity_study.py:117-120,1447-1460`

No VI, `hmc_laplace`, profile-Laplace, Mauna posterior, additional seed, shortened chain, or substitute configuration is permitted.

### Artifact preservation

- All six original caches above remain untouched as invalid historical provenance.
- Leave all `samples_vi*.npz`, `samples_map*.npz`, `samples_hmc_laplace*.npz`, their result JSONs, fingerprints, and existing reports untouched.
- New files are written first to temporary names and atomically renamed only after samples, diagnostics, scoring, and hashes complete.
- The original cache retention requirement follows `docs/d22-d24-impact-audit.md:43-54`; original cache naming follows `experiments/fit_method_metric_comparison.py:364-413` and `experiments/prior_sensitivity_study.py:632-645`.

## 3. Diagnostics and comparisons

### Per-run diagnostics

Persist the complete D20 `SamplerDiagnostics.to_dict()` payload:

`sampler`, `n_chains`, `n_draws`, `n_warmup`, `site_names`, `max_tree_depth`, `step_size`, `divergence_draws`, `acceptance_rate`, `leapfrog_counts`, `unavailable`, `schema_version`.

Also persist derived:

`n_divergences`, `divergence_rate`, `tree_depths`, `depth_saturation_rate`, where saturation is `leapfrog_count >= 2^depth-1`.

`bistar_gp/sampler_diagnostics.py:64-85,120-156`; observation extraction: `bistar_gp/sampler_diagnostics.py:227-288`.

Additionally record:

- basin occupancy low/mid/high and `n`;
- constrained-site mean, SD, q05/q50/q95, crude ESS;
- fit wall time, scoring wall time, predictive count;
- sample/diagnostic SHA-256, git SHA, package versions, hostname/thread count.

### Numbers replaced

- **D12 td10:** replace every `hmc` value in:
  - five \(\tau=1\) metric rows: `docs/fit-method-metric-comparison.md:17-21`;
  - five hard-win rows: lines 44-48;
  - five tau-sensitivity rows: lines 69-73;
  - four hyperparameter-summary rows and fit time: lines 96-99;
  - the HMC halves and recomputed deltas of the VI-vs-HMC tables: lines 113-130.
- The VI values remain unrerun and unvalidated; therefore VI-vs-HMC rows cannot be relabeled “corrected,” only “corrected HMC versus historical invalid VI.”
- **D12 td7 / D18 informative baseline:** replace the informative HMC stage-B, hard-win, `kl_forward`, tau, occupancy, and hyperparameter-derived values, including the reported 0.673 headline. `docs/prior-sensitivity-study.md:104,126,148,170,209`
- **D18 alternate td7 runs:** replace the corresponding HMC rows for `vague`, `toy_elicited`, and `gamma_relaxed` across model posteriors, hard wins, `kl_forward`, tau sensitivity, occupancy, hyperparameter summaries, and HMC-dependent figures. `docs/prior-sensitivity-study.md:92,96,100,114-125,136-147,158-169`
- **D18 toy td10:** replace the uncapped occupancy and 0.683 model-posterior row. `docs/prior-sensitivity-study.md:210,212-216`
- Recompute all five metrics at every frozen tau from exactly 200 seeded predictive draws; no metric-specific resampling. `experiments/fit_method_metric_comparison.py:166-199`

### Unchanged-arm re-verification

No new prior-IS, SIR, or RW-MH draws:

1. Dependency check:
   - prior-IS weights use the direct likelihood;
   - SIR consumes those pools;
   - post-D13 RW-MH uses the direct constrained likelihood plus change-of-variable Jacobian.
   These paths are classified unaffected. `docs/d22-d24-impact-audit.md:28-39`
2. Load the existing prior-IS pools for all four configs and seeds 0/1/2; recompute `_is_summary`, including pooled/per-band ESS and low/mid/high masses, and compare with existing Stage-A JSON at `atol=1e-12`. Pool paths are defined at `experiments/prior_sensitivity_study.py:337-397`.
3. Re-run only the deterministic SIR transformation from those unchanged pools: seed 42, 1,000 resamples, bootstrap seed 1 with 1,000 replicates; compare every metric/tau posterior, hard fraction, occupancy, ESS, and bootstrap field at `atol=1e-12`. `experiments/prior_sensitivity_study.py:664-702,705-764`; reported 1,000-draw rows: `docs/prior-sensitivity-study.md:187-196`.
4. Do not rerun RW-MH. Verify the stored three rows have seeds `42/1/2`, 30,000 retained samples after 5,000 burn-in, proposal scale 0.1, and unchanged occupancies/crossing counts. `experiments/prior_sensitivity_study.py:849-872`; `docs/prior-sensitivity-study.md:200-207`.
5. Profile-Laplace is not an “unchanged” reference because D24 invalidates second-order autograd Hessians. `docs/d22-d24-impact-audit.md:21-26`

## 4. Two-hour budget

Measured anchor: at \(N=150\), E1 td7 took 5.5296 s for 50+50 iterations and reported 334 sampling leapfrogs, i.e. **16.5556 ms per reported sampling leapfrog including warmup overhead**. `runs/d19_planning/e1_nuts_microbench.json:46-107`

Frozen planning assumptions:

- use the full 16.5556 ms anchor without an \(N=20\) speed discount;
- projected mean leapfrogs/iteration: 15 for td7, 25 for td10;
- add 120 s/run for MAP, predictive extraction, scoring, diagnostics, and serialization.

Arithmetic:

- td7: \(3000\times15\times0.0165556+120=865.0\) s = **14.4 min/run**;
- td10: \(3000\times25\times0.0165556+120=1361.7\) s = **22.7 min/run**;
- four td7 runs: \(4\times14.4=57.7\) min;
- two td10 runs: \(2\times22.7=45.4\) min;
- projected sampling/scoring total: **103.1 min**;
- remaining for unchanged-arm checks and final report: **16.9 min**;
- budget check: **103.1 + 16.9 = 120.0 min**.

This is an estimate, not a guarantee: corrected toy geometry determines realized tree lengths. The per-leapfrog projection is conservative in \(N\), because every run is \(N=20\), far below the measured \(N=150\).

### Stop-and-report rule

- Start one monotonic 120-minute clock before any fit or verification.
- Reserve the final 10 minutes for persistence and report generation; sampler execution cutoff is \(T_0+110\) minutes.
- Before starting a run, require `remaining_to_110min >= its frozen projection`; otherwise skip it and stop.
- Each run executes in a separate process with the common absolute cutoff. At cutoff, terminate the active run; an incomplete temporary cache is not a scientific result.
- Persist all completed atomic artifacts, hashes, logs, failures, and the exact first unexecuted/timed-out run.
- Do not reduce samples, warmup, depth, configurations, diagnostics, or predictive count.
- Do not resume or extend after inspecting results. Any continuation requires a new preregistered addendum.

## 5. Non-1:1 and unrecoverable items

- No requested HMC seed, configuration, data definition, depth, sample count, warmup count, or MAP-init rule is unrecoverable.
- A bit-identical rerun is impossible and undesirable: the old HMC rows used the defective D22/D23 path; this rerun deliberately uses the corrected E1 target and gradients. `docs/d22-d24-impact-audit.md:11-20,43-54`
- Original divergence indices, acceptance rates, leapfrog counts, adapted step sizes, and depth-saturation rates are unrecoverable: the old cache schema stored samples plus `_fit_seconds`, not the Pyro MCMC diagnostics object. `experiments/fit_method_metric_comparison.py:132-152`
- The exact floating-point MAP initialization vectors from the historical processes were not persisted. The deterministic initialization procedure is recoverable and frozen, but bitwise equality across historical/current package builds is not guaranteed.
- `runs/fit_method_metric_comparison/` and `runs/prior_sensitivity/` are local, untracked artifacts in this checkout; their contents are not portable committed evidence. D18 explicitly records them as “local by convention.” `Notes/DECISIONS.md:853-865`
- The corrected output namespace, execution order, diagnostic sidecars, and deadline mechanics are new M2bR protocol decisions above; they are not represented as recovered D12/D18 parameters.

Research was read-only; no files were modified.