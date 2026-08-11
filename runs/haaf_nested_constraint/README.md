# Haaf-style nested constraint: BMS* and PSIS-LOO

Run from the repository root:

```bash
python experiments/haaf_nested_constraint.py
```

The command regenerates `results.json` and this README. It uses the
frozen `generate_toy_data()` defaults: N=20, data seed 42, true
slope b=0.25, and observation standard deviation 0.5. The free and
restricted candidates share the Sin+Linear form. Their only region
difference concerns the slope bound: the free fit accepts every real
b, while the restricted fit requires b greater than or equal to zero.

## BMS* path and cache dependency

The run imports `prior_sensitivity_study.py`, loads the pooled
`toy_elicited` prior-IS caches for seeds 0, 1, and 2, and calls its
stage-IS SIR machinery with seed 42 and 1,000 predictives. It imports
the pooled and expected-posterior aggregation implementations from
`e7_convention_sensitivity.py`. The primary metric uses
`pw_kl_vcal`; `kl_forward` appears only as an appendix stress metric.

A fresh clone must first regenerate the local caches:

```bash
python experiments/prior_sensitivity_study.py --stage a --configs toy_elicited --is-n 60000 --is-seeds 0 1 2
python experiments/haaf_nested_constraint.py
```

Expected cache paths:

- `runs/prior_sensitivity/is_draws_toy_elicited_s0.npz`
- `runs/prior_sensitivity/is_draws_toy_elicited_s1.npz`
- `runs/prior_sensitivity/is_draws_toy_elicited_s2.npz`

For each shared predictive pattern, both candidates receive four shared
base starts. The restricted fit additionally receives every free
solution, clipped at b = 0 when necessary, and each candidate's
selection pool retains the other candidate's feasible vectors. This
deliberate asymmetry forces exact equality at shared optima instead of
turning optimizer noise into a model gap.

Because the restricted region forms a subset of the free region, the
protocol has min G over the restricted region greater than or equal to
min G over the free region for every predictive. The restricted BMS*
probability therefore cannot exceed the free probability under either
aggregation at any τ. Only the gap magnitude comes from the sampled
predictives. The runtime tolerance gates guard against machinery
regressions; they do not empirically test nesting.

At τ = 1, pooled BMS* assigns 0.500 to the free candidate and 0.500 to the restricted candidate. Expected-posterior aggregation also assigns 0.500 and 0.500. The free-minus-restricted
gap remains smaller than 1e-5 at every τ under both conventions and
comes from the 1 negative-slope draw among 1,000 SIR predictives. Its monotone contraction with τ
follows deterministically from Boltzmann aggregation, not from a
measured temperature effect.

## Appendix-only `kl_forward` stress note

The pooled `kl_forward` column is degenerate at exactly [0.5, 0.5]
for every τ. The single differing row has a `kl_forward` value of
500.142 for the free candidate and 488.982 for the restricted candidate, compared with a grid median of 55.8. The approximately 5.92e+10 global maximum occurs on a separate row where both candidate values are equal. Under the global
max-shift, the differing row contributes below float64 aggregate
resolution, so the pooled result carries no directional information.
The expected-posterior calculation reverses the primary-metric sign:
the differing row favors the restricted candidate by 11.160 nats, and at τ = 1 it assigns 0.499500014228 to the free candidate and 0.500499985772 to the restricted candidate.

These `kl_forward` values evaluate the candidate instances selected at
the `pw_kl_vcal` optima, with sigma reset from unweighted RMS residuals
after the primary-metric fit. They do not minimize `kl_forward` over
either parameter region, so the primary nesting inequality does not
apply to this appendix stress calculation.

## PSIS-LOO priors and sampler

The LOO comparison uses the identical x and y values. These priors
apply only to the LOO arm:

- `A`: HalfNormal(scale=5)
- `omega`: LogNormal(loc=0, scale=0.7)
- `phi`: Uniform(-pi, pi)
- `b_free`: Normal(loc=0, scale=5)
- `b_constrained`: HalfNormal(scale=5), the zero-truncated counterpart
- `c`: Normal(loc=0, scale=5)
- `sigma`: HalfNormal(scale=2)

Pyro NUTS runs two sequential chains with seeds 20260811 and
20260812, 1,000 warmup iterations and 1,000 retained draws per chain,
target acceptance probability 0.90, and maximum tree depth 8. ArviZ
receives the pointwise Normal log likelihoods and computes PSIS-LOO.

Every chain for both candidates initializes deterministically at the
common observed-data MLE through `init_to_value`: A = 0.886352, omega = 1.030240, phi = -0.029881, b = 0.251277, c = 0.028723, and sigma = 0.321232. The sampled x grid admits likelihood aliases near omega = 4.939 and 6.999 around the initialized mode at 1.0302. The likelihood is therefore multimodal,
so the reported R-hat and ESS values support within-mode convergence
only; they do not establish exploration across modes.

## Headline PSIS-LOO

| candidate | elpd_loo | SE | p_loo | max Pareto k | warning | divergences | max r_hat |
|---|---:|---:|---:|---:|---|---:|---:|
| Free Sin+Linear | -13.074 | 3.458 | 5.343 | 0.564 | no | 0 | 1.003 |
| Slope-constrained Sin+Linear | -12.661 | 3.594 | 5.169 | 0.718 | yes | 0 | 1.002 |

The paired constrained-minus-free elpd difference equals 0.413 with SE 0.256, computed with ddof=0 to match the ArviZ convention. The difference
is directionally inconclusive because it is smaller than twice its
paired SE, and ArviZ flags the constrained estimate because 1 observation exceeds its sample-size-specific good-k threshold. The
paired SE covers data-level pointwise variability only and does not
include MCMC error. A null-to-inconclusive LOO difference matches the
failure mode reported for satisfied nested constraints.

The two slope priors coincide up to normalization on b > 0. The
artifact's full-data local Gaussian approximation gives posterior SD
0.0129506 for b, places the boundary 19.4028 SDs away, and gives a Gaussian
left-tail probability of 3.65e-84. This local approximation supports the reading that the constraint
binds only where the locally approximated posterior carries negligible
mass. It does not prove exact posterior identity or show that the entire
observed gap comes from estimator noise.

## Determinism and tolerances

All random-number seeds appear in `results.json`. On the pinned
environment, repeated CPU runs should reproduce the artifact. Across
compatible machines and library builds, use these absolute comparison
tolerances:

- `bms_probability_abs`: 0.005
- `loo_elpd_abs`: 0.25
- `loo_pairwise_difference_abs`: 0.25
- `negative_slope_fraction_abs`: 0.005

The primary machinery-regression gates use 2e-07 absolute tolerance for equality on nonnegative free-slope rows and 2e-07 for the one-sided G ordering on negative-slope rows.
A failure stops the run before artifact replacement; passing the gates
does not supply an empirical nesting test.

No figure accompanies the case because the comparison table and the
slope-sign diagnostic convey the full result without an additional
visual encoding.
