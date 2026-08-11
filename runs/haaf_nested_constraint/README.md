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

For each shared predictive pattern, both candidates minimize the
primary G over their parameter regions through
`CandidateModel._fit_mle`. No candidate-parameter prior contributes
to the BMS* calculation.

At τ = 1, pooled BMS* assigns 0.500000 to the free candidate and 0.500000 to the restricted candidate. Expected-posterior aggregation assigns 0.500000 and 0.500000, respectively. The free-fit slope falls below zero for 0.001000 of SIR predictives.

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

## Headline PSIS-LOO

| candidate | elpd_loo | SE | p_loo | max Pareto k | warning | divergences | max r_hat |
|---|---:|---:|---:|---:|---|---:|---:|
| Free Sin+Linear | -13.074 | 3.458 | 5.343 | 0.564 | no | 0 | 1.003 |
| Slope-constrained Sin+Linear | -12.661 | 3.594 | 5.169 | 0.718 | yes | 0 | 1.002 |

The paired constrained-minus-free elpd difference equals 0.413 with SE 0.263.
ArviZ flags the constrained estimate because 1 observation exceeds its sample-size-specific good-k threshold. Interpret the direction with that qualification.

## Determinism and tolerances

All random-number seeds appear in `results.json`. On the pinned
environment, repeated CPU runs should reproduce the artifact. Across
compatible machines and library builds, use these absolute comparison
tolerances:

- `bms_probability_abs`: 0.005
- `loo_elpd_abs`: 0.25
- `loo_pairwise_difference_abs`: 0.25
- `negative_slope_fraction_abs`: 0.005

The primary nesting gates use 2e-07 absolute tolerance for equality on nonnegative free-slope rows and 2e-07 for the one-sided G ordering on negative-slope rows.
A failure stops the run before artifact replacement.

No figure accompanies the case because the comparison table and the
slope-sign diagnostic convey the full result without an additional
visual encoding.
