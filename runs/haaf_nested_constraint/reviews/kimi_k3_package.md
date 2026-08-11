PASTE-READY PACKAGE FOR KIMI K3 (author-run; no CLI configured in this repo).
You are an independent reviewer (one of four; you will not see the others' outputs).
You have NO repository access; review strictly from the package below, and flag any
claim you cannot verify from it as exactly that. Produce the verdict (APPROVE or
REVISE) and the numbered findings list in the package's specified format.

Review the attached branch diff for the BI*/BMS*-GP paper case C (Haaf nested
constraint). Verdict: APPROVE or REVISE. Findings as a numbered list:
[severity S1-S4] [file:line] claim — why it is wrong — concrete fix.
Check specifically: (1) constraint compliance [the §0 list below]; (2) numerical
claims vs the runs/ JSONs; (3) statistical correctness of the method logic;
(4) prose style rules; (5) anything the section claims that the artifacts do
not support. Do not propose scope expansions.

§0 CONSTRAINT LIST (from docs/paper-sie-jmp/HANDOFF-cases.md, verbatim):
- M2bR banner: `informative`-config HMC is WITHDRAWN. Usable numbers:
  `toy_elicited` SIR (headline 0.441), prior-IS, MAP, SIR hard-best-match
  rates, corrected NUTS ≈ 0.42. Never cite the withdrawn cache
  (`runs/fit_method_metric_comparison/samples_hmc.npz`) or
  `runs/toy_tau_metric_comparison/` (poster-only per W7).
- W1: primary metric `pw_kl_vcal`; `kl_forward` appendix-only.
- W4: `runs/viz_unification/*` numbers are `informative`-config, MAP-based,
  methods-validation role — prose must frame them so.
- No Mauna Loa material of any kind (D58 prereg boundary not to be tested).
- No changes to `bistar_gp/` package defaults or public APIs.
- Style: no arrow glyphs in prose; no "X is the Y" role-noun constructions;
  no "lives/sits" for abstracta; minimal em-dashes.
- Every reported number must be regenerable from a named `experiments/`
  script into a `runs/` artifact; each case commits a same-commit
  `Notes/DECISIONS.md` entry (next free D number).
- Commit scope per branch: `experiments/` script(s), `docs/paper-sie-jmp/`
  section, `Notes/DECISIONS.md` entry, and (deliberately, if evidence-worthy)
  the `runs/` JSON — never figures over 2 MB, never gitignored Notes files.

CASE C WORK ORDER (§2 of the HANDOFF, verbatim):
Scope: the one real build. `experiments/haaf_nested_constraint.py`:
1. Candidate pair differing ONLY by a parameter-region constraint within one
   functional form (mirror Haaf & Klaassen's ordinal-constraint setting):
   free Sin+Linear vs slope-constrained (b ≥ 0) Sin+Linear, both via
   `bistar_gp/candidates.py` `_fit_mle` with bounds.
2. Constraint-consistent synthetic data (true b > 0), N=20 convention,
   seeded.
3. BMS* scoring on the validated path: reuse
   `experiments/prior_sensitivity_study.py` stage-IS machinery exactly as
   `experiments/e7_convention_sensitivity.py` does (imports, not copies);
   report pooled AND expected-posterior variants (fork-agnostic table).
4. PSIS-LOO head-to-head on the identical data via `arviz` (add to
   requirements only if absent), for the same two candidates fitted as
   Bayesian models with weakly-informative priors — document those priors;
   they exist only on the LOO side of the comparison.
5. Section `05-case-C-nested-constraints.md` from the stub. Output
   `runs/haaf_nested_constraint/`.
Acceptance: the comparison table shows, on identical data, what LOO awards
the constrained candidate vs what BMS* awards it; whichever way it comes out
is reported (a null result is reportable); DECISIONS entry present.

DRIVER-VERIFIED FACTS (state of the world; do not report these as findings):
- kb/ is entirely gitignored in this repo (.gitignore:36; zero kb/ files have
  ever been tracked). Case C's work order commissions NO kb edit, and none
  appears in the diff. Local kb material cannot appear in any diff by design.
- The BMS* arm depends on LOCAL untracked prior-IS caches
  runs/prior_sensitivity/is_draws_toy_elicited_s{0,1,2}.npz. Driver verified
  their provenance matches the documented regeneration command exactly
  (60000 draws per seed; prior_sensitivity_study.py --stage a default
  --is-n 60000). The README documents the cache dependency and regeneration.
- The Haaf, Klaassen & Rouder (2025) DOI 10.1007/s42113-025-00240-0 cited in
  the section matches the kb ingest stub
  kb/Raw/papers/doi/bayes_factor_vs_posterior_predictive_model_assessm.md
  (OpenAlex citing-papers sweep). Kellen & Klauer (2020) remains unread in
  kb/Raw/WANTED.md:131, so the section's provisional-framing marker is
  required and present.
- Driver rerun of experiments/haaf_nested_constraint.py from the branch tip
  reproduced runs/haaf_nested_constraint/results.json BYTE-IDENTICAL
  (deterministic, including both pyro NUTS chains).
- The uncommitted working-tree Notes/DECISIONS.md additionally carries
  D60/D61/D62 above the committed D63; they belong to other branches and are
  correctly absent from this branch's committed diff.

=== SECTION FILE (docs/paper-sie-jmp/05-case-C-nested-constraints.md) ===
# 5. Case C: a satisfied nested constraint under BMS* and LOO

Haaf, Klaassen, and Rouder examine theories represented by restrictions on a
common parameter space. In their ordinal examples, WAIC and leave-one-out
cross-validation do not favor the restricted model even when the data comply
with its constraint. They argue that a forced partition into disjoint regions
can replace scientifically meaningful overlapping models with regions that
carry no theoretical interpretation.[^1] [Provisional framing: Kellen and
Klauer (2020) has not yet been read, so the phrase “sharpest published
criticism” remains provisional.]

Our experiment mirrors the parameter-region issue directly. It does not rely
on the toy example's cross-family nesting. The encompassing candidate
$M_e$ uses

$$
y(x)=A\sin(\omega x+\phi)+bx+c+\epsilon,
$$

with unrestricted $b$. The restricted candidate $M_r \subset M_e$ uses the
same expression and imposes $b\geq 0$. Both candidates call the same bounded
MLE routine, use the same starts, and share every bound except the lower bound
on $b$. The frozen $N=20$ data use seed 42 and the true slope $b=0.25$, so the
restriction holds in truth.[^2]

## 5.1 BMS* comparison

The BMS* calculation follows the validated `toy_elicited` stage-IS path. It
pools prior-IS caches from seeds 0, 1, and 2, draws 1,000 SIR predictives with
seed 42, and evaluates 60 locations. For every predictive data pattern
$\psi$, the free and restricted fits minimize the primary
`pw_kl_vcal` value $G(\psi,\theta)$ over their respective parameter regions.
Thus the calculation supplies candidate instances from a shared $\psi$ rather
than introducing candidate-parameter priors. Such priors contribute only to
the separate LOO comparison below.[^2]

The nesting check passed at a $2\times10^{-7}$ absolute tolerance. On 999
predictives, the free optimum had $b\geq0$, and both candidates produced
identical primary $G$ values. One predictive had a negative free optimum, for
a fraction of 0.001. On that row, restricted minus free $G$ equaled
0.000360, so the required one-sided ordering also held.[^2]

Table 5.1 reports both aggregation conventions across the preregistered
temperature grid. Each pair normalizes over only the free and restricted
candidates.[^2]

| $\tau$ | pooled free | pooled restricted | expected-posterior free | expected-posterior restricted |
|---:|---:|---:|---:|---:|
| 0.1 | 0.500003900 | 0.499996100 | 0.500000900 | 0.499999100 |
| 0.3 | 0.500000570 | 0.499999430 | 0.500000300 | 0.499999700 |
| 1.0 | 0.500000112 | 0.499999888 | 0.500000090 | 0.499999910 |
| 3.0 | 0.500000032 | 0.499999968 | 0.500000030 | 0.499999970 |
| 10.0 | 0.500000009 | 0.499999991 | 0.500000009 | 0.499999991 |

At the headline value $\tau=1$, both conventions therefore give an effective
tie. The free candidate's advantage decreases monotonically as $\tau$
increases, and neither aggregation choice changes the conclusion. The
appendix-only `kl_forward` calculation also remains within 0.0006 of an equal
split across the grid.[^2]

The result does not support a claim that BMS* preferentially rewards a
satisfied restriction in this instance. BMS* assigns the restricted candidate
essentially half the probability without partitioning the parameter space,
but the encompassing candidate can reproduce every restricted optimum. The
single predictive with a negative slope creates the entire primary-metric gap.
Without an explicit parameter-volume or complexity term, the satisfied
restriction supplies equality on shared optima rather than an automatic
advantage. Soft transfer makes that null result visible across $\tau$; a hard
best-match treatment would retain only the limiting row assignments.

## 5.2 PSIS-LOO comparison

Both Bayesian candidates use the identical 20 observations and likelihood.
Their weakly informative priors apply only to this LOO arm: $A\sim$
HalfNormal(5), $\omega\sim$ LogNormal(0, 0.7), $\phi\sim$
Uniform($-\pi,\pi$), $c\sim$ Normal(0, 5), and $\sigma\sim$
HalfNormal(2). The free model uses $b\sim$ Normal(0, 5); the restricted model
uses the corresponding zero-truncated distribution, $b\sim$ HalfNormal(5).
No prior from this list enters the BMS* calculation.[^2]

Pyro NUTS ran two sequential chains with seeds 20260811 and 20260812. Each
chain used 1,000 warmup iterations and retained 1,000 draws, with target
acceptance probability 0.90 and maximum tree depth 8. Both fits recorded zero
divergences. Rank-normalized $\widehat R$ reached at most 1.003 for the free
fit and 1.002 for the restricted fit; minimum bulk effective sample sizes were
1,004 and 1,638, respectively.[^2]

| candidate | `elpd_loo` | SE | `p_loo` | max Pareto $k$ | warning |
|---|---:|---:|---:|---:|---|
| free Sin+Linear | -13.074 | 3.458 | 5.343 | 0.564 | no |
| slope-constrained Sin+Linear | -12.661 | 3.594 | 5.169 | 0.718 | yes, one observation |

The constrained-minus-free `elpd_loo` difference equals 0.413 with a paired SE
of 0.263.[^2] On its face, PSIS-LOO assigns the higher predictive score to the
restricted candidate, while BMS* produces an effective tie. ArviZ nevertheless
flags the restricted estimate because one observation exceeds the
sample-size-specific good-$k$ threshold of 0.697. Pareto shape values above
about 0.7 can make the importance-sampling approximation unreliable, so the
direction should not support a decisive claim without exact refits or a more
robust cross-validation calculation.[^3]

This head-to-head does not reproduce a categorical LOO failure, and it does
not show preferential BMS* credit for the satisfied constraint. It instead
separates two mechanisms on identical data. LOO changes because the two
Bayesian fits use different support for $b$; BMS* changes only when a shared
$\psi$ has a negative free optimum. Here that event occurs once in 1,000 SIR
predictives, leaving the BMS* result numerically indistinguishable from a tie.

[^1]: 🟢 peer-reviewed — Haaf, Klaassen, and Rouder (2025). Bayes factor vs. posterior predictive model assessment: Insights from ordinal constraints. *Computational Brain & Behavior*. https://doi.org/10.1007/s42113-025-00240-0
[^2]: 🟠 empirical — `experiments/haaf_nested_constraint.py`; `runs/haaf_nested_constraint/results.json` and `README.md` (data seed 42; prior-IS seeds 0, 1, 2; SIR seed 42; NUTS seeds 20260811 and 20260812).
[^3]: 🟢 peer-reviewed — Vehtari, Gelman, and Gabry (2017). Practical Bayesian model evaluation using leave-one-out cross-validation and WAIC. *Statistics and Computing*, 27(5), 1413–1432.

---
*Provenance: `runs/haaf_nested_constraint/` · `experiments/haaf_nested_constraint.py` · Notes/DECISIONS.md D63.*


=== RUN README (runs/haaf_nested_constraint/README.md) ===
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


=== RUN JSON (runs/haaf_nested_constraint/results.json, FULL) ===
{
  "case": "Case C, nested slope constraint",
  "protocol_date": "2026-08-11",
  "quick": false,
  "data": {
    "generator": "bistar_gp.generate_toy_data defaults",
    "n": 20,
    "seed": 42,
    "x_range": [
      -10.0,
      10.0
    ],
    "true_bias_slope": 0.25,
    "noise_std": 0.5,
    "xy_sha256_float64_le": "f54c873f48f6d049778d12989b3209d78605002f747a2805551cedfd9d4eedb5"
  },
  "candidate_definition": {
    "functional_form": "A sin(omega x + phi) + b x + c",
    "model_names": [
      "Free Sin+Linear",
      "Slope-constrained Sin+Linear"
    ],
    "free_bounds": [
      [
        null,
        null
      ],
      [
        null,
        null
      ],
      [
        null,
        null
      ],
      [
        null,
        null
      ],
      [
        null,
        null
      ],
      [
        -10.0,
        5.0
      ]
    ],
    "constrained_bounds": [
      [
        null,
        null
      ],
      [
        null,
        null
      ],
      [
        null,
        null
      ],
      [
        0.0,
        null
      ],
      [
        null,
        null
      ],
      [
        -10.0,
        5.0
      ]
    ],
    "only_bound_difference_index": 3,
    "only_bound_difference_parameter": "b",
    "observed_data_mle": {
      "Free Sin+Linear": {
        "A": 0.8863515558683248,
        "omega": 1.030239891010187,
        "phi": -0.02988145356722502,
        "b": 0.2512769921781912,
        "c": 0.02872270880462028,
        "sigma": 0.32123190979141125
      },
      "Slope-constrained Sin+Linear": {
        "A": 0.8863515558683248,
        "omega": 1.030239891010187,
        "phi": -0.02988145356722502,
        "b": 0.2512769921781912,
        "c": 0.02872270880462028,
        "sigma": 0.32123190979141125
      }
    }
  },
  "bms_star": {
    "config": "toy_elicited",
    "is_seeds": [
      0,
      1,
      2
    ],
    "sir_seed": 42,
    "n_sir_draws": 1000,
    "n_unique_sir_draws": 883,
    "pooled_is_ess": 4464.532791988796,
    "cache_dependencies": [
      {
        "seed": 0,
        "path": "runs/prior_sensitivity/is_draws_toy_elicited_s0.npz",
        "n_draws": 60000,
        "sha256": "a07c4c8e2dc95e37d00334d4555c569fa36d47dae2bb083bbc94e2d32220a552"
      },
      {
        "seed": 1,
        "path": "runs/prior_sensitivity/is_draws_toy_elicited_s1.npz",
        "n_draws": 60000,
        "sha256": "60d2bdf48235f8baca5f1f2cf15121ea6a518c227927b6cfab890fd8cc37350b"
      },
      {
        "seed": 2,
        "path": "runs/prior_sensitivity/is_draws_toy_elicited_s2.npz",
        "n_draws": 60000,
        "sha256": "5efb94beec2040cf3eecdb862d4d657d05e6fad385f8a275e79961ceaf3d0a8f"
      }
    ],
    "primary_metric": "pw_kl_vcal",
    "appendix_metric": "kl_forward",
    "taus": [
      0.1,
      0.3,
      1.0,
      3.0,
      10.0
    ],
    "aggregation_variants": [
      "pooled",
      "expected_posterior"
    ],
    "tables": {
      "pw_kl_vcal": {
        "0.1": {
          "pooled": [
            0.5000038998478196,
            0.49999610015218043
          ],
          "expected_posterior": [
            0.5000009002844767,
            0.49999909971552325
          ]
        },
        "0.3": {
          "pooled": [
            0.5000005696716678,
            0.4999994303283322
          ],
          "expected_posterior": [
            0.5000003000951139,
            0.49999969990488613
          ]
        },
        "1.0": {
          "pooled": [
            0.5000001121319367,
            0.49999988786806315
          ],
          "expected_posterior": [
            0.500000090028544,
            0.49999990997145605
          ]
        },
        "3.0": {
          "pooled": [
            0.5000000324017109,
            0.499999967598289
          ],
          "expected_posterior": [
            0.500000030009515,
            0.49999996999048507
          ]
        },
        "10.0": {
          "pooled": [
            0.5000000092162471,
            0.4999999907837529
          ],
          "expected_posterior": [
            0.5000000090028545,
            0.49999999099714554
          ]
        }
      },
      "kl_forward": {
        "0.1": {
          "pooled": [
            0.5,
            0.5
          ],
          "expected_posterior": [
            0.4995,
            0.5005
          ]
        },
        "0.3": {
          "pooled": [
            0.5,
            0.5
          ],
          "expected_posterior": [
            0.4995,
            0.5005
          ]
        },
        "1.0": {
          "pooled": [
            0.5,
            0.5
          ],
          "expected_posterior": [
            0.4995000142279742,
            0.5004999857720258
          ]
        },
        "3.0": {
          "pooled": [
            0.5,
            0.5
          ],
          "expected_posterior": [
            0.4995236583737479,
            0.5004763416262521
          ]
        },
        "10.0": {
          "pooled": [
            0.5,
            0.5
          ],
          "expected_posterior": [
            0.4997467486749119,
            0.500253251325088
          ]
        }
      }
    },
    "slope_sign": {
      "negative_count": 1,
      "nonnegative_count": 999,
      "negative_fraction": 0.001,
      "free_slope_min": -2.740556026196546,
      "free_slope_median": 0.24992808854452286,
      "free_slope_max": 0.2561836749400731
    },
    "sanity_identity_primary_G": {
      "metric": "pw_kl_vcal",
      "equality_atol": 2e-07,
      "order_atol": 2e-07,
      "max_abs_gap_on_nonnegative_free_slope": 0.0,
      "min_constrained_minus_free_G_on_negative_free_slope": 0.00036011417986084315,
      "violations": 0
    },
    "G_summary": {
      "pw_kl_vcal": {
        "Free Sin+Linear": {
          "mean": 0.2624501953762448,
          "median": 0.21240332889150088
        },
        "Slope-constrained Sin+Linear": {
          "mean": 0.2624505554904247,
          "median": 0.21240332889150088
        },
        "mean_constrained_minus_free": 3.6011417986084316e-07
      },
      "kl_forward": {
        "Free Sin+Linear": {
          "mean": 62711373.94763098,
          "median": 55.77955486646584
        },
        "Slope-constrained Sin+Linear": {
          "mean": 62711373.936470695,
          "median": 55.77955486646584
        }
      }
    },
    "validated_pss_observed_fit_anchor": {
      "metric": "pw_kl_vcal",
      "tau": 1.0,
      "pooled_probabilities": [
        0.5,
        0.5
      ],
      "observed_candidate_predictions_identical": true
    }
  },
  "psis_loo": {
    "priors_apply_only_to_loo": true,
    "priors": {
      "A": "HalfNormal(scale=5)",
      "omega": "LogNormal(loc=0, scale=0.7)",
      "phi": "Uniform(-pi, pi)",
      "b_free": "Normal(loc=0, scale=5)",
      "b_constrained": "HalfNormal(scale=5), the zero-truncated counterpart",
      "c": "Normal(loc=0, scale=5)",
      "sigma": "HalfNormal(scale=2)"
    },
    "candidates": {
      "free": {
        "elpd_loo": -13.074035199760031,
        "se": 3.457658432262354,
        "p_loo": 5.3425180223319035,
        "pointwise_elpd": [
          -0.21155629476330606,
          -0.43926962300042316,
          -0.20719821594875842,
          -0.2361651234683606,
          -0.4226011004547363,
          -2.0652754755042784,
          -0.12736686775851602,
          -0.18822889368121043,
          -0.21485785502532995,
          -0.18244473313072174,
          -3.1356277558931103,
          -0.17212033900921142,
          -0.42340045460782605,
          -1.1776824907532264,
          -0.3857673072787069,
          -0.4901979252335966,
          -0.28427848341864603,
          -0.5362899197571522,
          -1.8088032429869152,
          -0.36490309808599797
        ],
        "pareto_k": {
          "max": 0.56433444203386,
          "good_k_threshold": 0.6970642492453765,
          "warning": false,
          "n_over_good_k_threshold": 0,
          "n_over_0_5": 4,
          "n_over_0_7": 0,
          "n_over_1_0": 0,
          "values": [
            0.3375728534467342,
            0.2012959331566071,
            0.3841381306806338,
            0.20993827363907794,
            0.5478633098143861,
            0.5260322750894596,
            0.10269805482506851,
            0.3732058250621627,
            0.2312628196351459,
            0.28545804852125023,
            0.56433444203386,
            0.18117722566553335,
            0.40889762466289403,
            0.44866077852480507,
            0.43193724825145835,
            0.3735030007370231,
            0.37745979566745264,
            0.47510620894643435,
            0.5020553621914025,
            0.48371240471020577
          ]
        },
        "sampler": {
          "chains": 2,
          "warmup_per_chain": 1000,
          "draws_per_chain": 1000,
          "chain_seeds": [
            20260811,
            20260812
          ],
          "target_accept_prob": 0.9,
          "max_tree_depth": 8,
          "divergences_by_chain": [
            0,
            0
          ],
          "divergences_total": 0,
          "acceptance_rate_by_chain": [
            1.0,
            0.997
          ],
          "r_hat": {
            "A": 1.0021779256815142,
            "omega": 1.000345794126434,
            "phi": 1.0004711765829615,
            "b": 1.0003334427482566,
            "c": 1.0026623905081171,
            "sigma": 1.0017171836801422
          },
          "r_hat_max": 1.0026623905081171,
          "ess_bulk": {
            "A": 1578.5422136990771,
            "omega": 1682.8810514518743,
            "phi": 1622.7358100655185,
            "b": 1734.6441569567678,
            "c": 1504.9794243136823,
            "sigma": 1004.1756676042146
          },
          "ess_bulk_min": 1004.1756676042146,
          "ess_tail": {
            "A": 1048.5480175608104,
            "omega": 1395.318973231408,
            "phi": 1215.2131371265382,
            "b": 1529.632189759994,
            "c": 976.4286801081233,
            "sigma": 1198.1492536746052
          },
          "ess_tail_min": 976.4286801081233
        }
      },
      "constrained": {
        "elpd_loo": -12.661376138005416,
        "se": 3.593844557536322,
        "p_loo": 5.169193999240674,
        "pointwise_elpd": [
          -0.1800941287574247,
          -0.42016992466978476,
          -0.15434077798912327,
          -0.20929934443788767,
          -0.4073675395332659,
          -2.0935369019362025,
          -0.1078674215861195,
          -0.15857842457300642,
          -0.17731310309399628,
          -0.15574465766583412,
          -3.3043938783522897,
          -0.15303684255469907,
          -0.3805443681813099,
          -1.185193076132145,
          -0.39494352321351034,
          -0.4929921892755429,
          -0.2754431413619107,
          -0.461345161954239,
          -1.657964283014448,
          -0.291207449722676
        ],
        "pareto_k": {
          "max": 0.7182546199391353,
          "good_k_threshold": 0.6970642492453765,
          "warning": true,
          "n_over_good_k_threshold": 1,
          "n_over_0_5": 4,
          "n_over_0_7": 1,
          "n_over_1_0": 0,
          "values": [
            0.15441142640734165,
            0.29633185258099387,
            0.27270946441404176,
            0.29566889483930986,
            0.32138749989195053,
            0.7182546199391353,
            0.09818048865950656,
            0.029063955554477914,
            0.08319147392416558,
            0.04775309292109709,
            0.4745683259763115,
            0.2549629577876692,
            0.35251782241265806,
            0.4106324853246572,
            0.25526691818542246,
            0.606530857456,
            0.6033338832223576,
            0.17594206418835584,
            0.5643109072287471,
            0.4385118962465545
          ]
        },
        "sampler": {
          "chains": 2,
          "warmup_per_chain": 1000,
          "draws_per_chain": 1000,
          "chain_seeds": [
            20260811,
            20260812
          ],
          "target_accept_prob": 0.9,
          "max_tree_depth": 8,
          "divergences_by_chain": [
            0,
            0
          ],
          "divergences_total": 0,
          "acceptance_rate_by_chain": [
            1.0,
            0.999
          ],
          "r_hat": {
            "A": 0.9996110580196691,
            "omega": 1.0018726549522892,
            "phi": 1.0003446815445542,
            "b": 1.0019608793754489,
            "c": 0.9994023363149376,
            "sigma": 1.0011641982754624
          },
          "r_hat_max": 1.0019608793754489,
          "ess_bulk": {
            "A": 2129.102192398176,
            "omega": 1721.2813249175815,
            "phi": 2071.0224454556114,
            "b": 1804.4172698799557,
            "c": 2116.2916155268513,
            "sigma": 1638.0890639710935
          },
          "ess_bulk_min": 1638.0890639710935,
          "ess_tail": {
            "A": 1203.637068515664,
            "omega": 1192.2911786469801,
            "phi": 1382.6965173555689,
            "b": 1497.3311200217663,
            "c": 1582.8357646041945,
            "sigma": 1269.7691958043156
          },
          "ess_tail_min": 1192.2911786469801
        }
      }
    },
    "pairwise": {
      "direction": "constrained_minus_free",
      "elpd_difference": 0.4126590617546153,
      "se": 0.262534386964351,
      "pointwise_differences": [
        0.031462166005881365,
        0.019099698330638404,
        0.052857437959635156,
        0.026865779030472936,
        0.015233560921470435,
        -0.028261426431924086,
        0.019499446172396517,
        0.029650469108204014,
        0.037544751931333664,
        0.026700075464887618,
        -0.16876612245917944,
        0.01908349645451235,
        0.04285608642651617,
        -0.007510585378918577,
        -0.009176215934803444,
        -0.0027942640419462705,
        0.008835342056735307,
        0.07494475780291321,
        0.1508389599724671,
        0.07369564836332199
      ]
    }
  },
  "tolerances": {
    "structural": {
      "G_equality_atol": 2e-07,
      "G_order_atol": 2e-07,
      "slope_bound_atol": 1e-10
    },
    "cross_machine_rerun": {
      "bms_probability_abs": 0.005,
      "loo_elpd_abs": 0.25,
      "loo_pairwise_difference_abs": 0.25,
      "negative_slope_fraction_abs": 0.005
    }
  },
  "versions": {
    "numpy": "1.26.4",
    "torch": "2.10.0",
    "pyro": "1.9.1",
    "arviz": "0.23.4"
  }
}


=== BRANCH DIFF vs main (full) ===
Stat:
 Notes/DECISIONS.md                                 |  80 ++
 docs/paper-sie-jmp/05-case-C-nested-constraints.md | 114 +++
 experiments/haaf_nested_constraint.py              | 871 +++++++++++++++++++++
 runs/haaf_nested_constraint/README.md              |  90 +++
 runs/haaf_nested_constraint/results.json           | 565 +++++++++++++
 5 files changed, 1720 insertions(+)

(results.json excluded from textual diff; full content above)

diff --git a/Notes/DECISIONS.md b/Notes/DECISIONS.md
index 033fee3..62b6c7d 100644
--- a/Notes/DECISIONS.md
+++ b/Notes/DECISIONS.md
@@ -5716,3 +5716,83 @@ to be amended later merely to insert them. STOP before Ready or merge. NOT autho
 second correction pass, restoring/applying/dropping stash `5280d1e1…`, D59 work, evidence
 or figure changes, poster-repository work, the captions themselves, Della contact, new
 computation, holdout access, BMS*, Ready, or merge.
+
+## D63: Case C nested slope constraint under BMS* and PSIS-LOO — 2026-08-11
+
+**Problem:** Case C needed a direct mirror of Haaf, Klaassen, and Rouder's
+parameter-region comparison, not the toy example's cross-family nesting. The
+comparison had to use the constraint-consistent, data-elicited $N=20$ toy
+instance and place a free Sin+Linear candidate beside an otherwise identical
+$b\geq0$ candidate. BMS* had to follow the validated `toy_elicited` SIR path
+under both pooled and expected-posterior aggregation, while PSIS-LOO had to fit
+Bayesian versions of the same pair on identical observations. The original
+directional claim could not determine how the comparison came out.
+
+**Decision:** Added `experiments/haaf_nested_constraint.py`, which writes
+`runs/haaf_nested_constraint/{results.json,README.md}`. The canonical command
+`python experiments/haaf_nested_constraint.py` uses
+`generate_toy_data()` defaults ($N=20$, data seed 42, true $b=0.25$, noise
+standard deviation 0.5). Both candidates call
+`bistar_gp.candidates.CandidateModel._fit_mle`; they share all starts and
+bounds except the lower slope bound, unrestricted for the free candidate and
+zero for the restricted candidate. A common log-sigma bound of [-10, 5]
+prevents exploratory underflow. Each shared $\psi$ receives a fresh fit, so the
+per-draw free-slope sign can account for the BMS* gap.
+
+The BMS* arm imports `prior_sensitivity_study.py`, loads the local
+`toy_elicited` prior-IS caches for seeds 0, 1, and 2, and calls the validated
+stage-IS machinery with SIR seed 42 and `n_pred=1000`. It imports the pooled
+and expected-posterior aggregations from
+`e7_convention_sensitivity.py`, reports $\tau\in\{0.1,0.3,1,3,10\}$, uses
+`pw_kl_vcal` as the primary metric, and confines `kl_forward` to an appendix
+stress table. Candidate-parameter priors do not enter BMS*.
+
+The LOO arm alone uses weakly informative priors: $A\sim$ HalfNormal(5),
+$\omega\sim$ LogNormal(0, 0.7), $\phi\sim$ Uniform($-\pi,\pi$),
+$c\sim$ Normal(0, 5), and $\sigma\sim$ HalfNormal(2); the free candidate uses
+$b\sim$ Normal(0, 5), while the restricted candidate uses $b\sim$
+HalfNormal(5). Pyro NUTS runs sequential chains with seeds 20260811 and
+20260812, each with 1,000 warmup iterations and 1,000 retained draws, target
+acceptance probability 0.90, and maximum tree depth 8. ArviZ computes
+pointwise PSIS-LOO. Structural G tolerances equal $2\times10^{-7}$ for both
+interior equality and one-sided nesting; cross-machine artifact tolerances
+equal 0.005 for probabilities and the slope fraction, 0.25 elpd for each LOO
+estimate, and 0.25 elpd for the paired difference.
+
+**Alternatives considered:** Drawing new data was rejected because it would
+break the binding between the $N=20$ observations, their data-elicited GP
+prior, and the validated M2bR basis. Changing `bistar_gp/` was rejected because
+the existing protected `_fit_mle(..., bounds=...)` hook supplies the needed
+constraint. Fitting each candidate only once to the observations was rejected
+because the positive observed-data slope would make the two predictions
+identical and could not produce the required per-$\psi$ slope diagnostic.
+Reimplementing the SIR or aggregation formulas was rejected in favor of the
+required imports. One NUTS chain was allowed by the work order, but two seeded
+chains provide rank-normalized $\widehat R$ diagnostics. A figure was omitted
+because the table and slope-sign count contain the full comparison.
+
+**Result:** The pooled prior-IS ESS equals 4,464.53, and the 1,000 SIR rows
+contain 883 unique cached draws. The free best-fit slope falls below zero on
+1/1,000 rows, a fraction of 0.001. The remaining 999 rows have identical
+primary G values for both candidates to the recorded tolerance. On the one
+negative-slope row, restricted minus free G equals 0.000360, so the one-sided
+nesting check passes with zero violations.
+
+At $\tau=1$, pooled BMS* assigns 0.500000112 to the free candidate and
+0.499999888 to the restricted candidate; expected-posterior aggregation
+assigns 0.500000090 and 0.499999910. The restricted pooled probability ranges
+from 0.499996100 at $\tau=0.1$ to 0.499999991 at $\tau=10$; its
+expected-posterior probability ranges from 0.499999100 to 0.499999991. Thus
+BMS* reports an effective tie throughout the sweep.
+
+PSIS-LOO reports `elpd_loo=-13.074` (SE 3.458, `p_loo=5.343`) for the free
+candidate and `elpd_loo=-12.661` (SE 3.594, `p_loo=5.169`) for the restricted
+candidate. The restricted-minus-free difference equals 0.413 with paired SE
+0.263. Both NUTS fits have zero divergences; maximum rank-normalized
+$\widehat R$ equals 1.003 free and 1.002 restricted, and minimum bulk ESS
+equals 1,004 and 1,638. The free maximum Pareto $k$ equals 0.564 with no
+warning. The restricted maximum equals 0.718, and ArviZ flags one observation
+above its 0.697 good-$k$ threshold. The direction favors the restriction under
+LOO but requires that qualification. Case C therefore records a split null:
+LOO gives a small, diagnostically qualified advantage to the restricted
+candidate, while BMS* gives neither candidate a meaningful advantage.
diff --git a/docs/paper-sie-jmp/05-case-C-nested-constraints.md b/docs/paper-sie-jmp/05-case-C-nested-constraints.md
new file mode 100644
index 0000000..7cb9001
--- /dev/null
+++ b/docs/paper-sie-jmp/05-case-C-nested-constraints.md
@@ -0,0 +1,114 @@
+# 5. Case C: a satisfied nested constraint under BMS* and LOO
+
+Haaf, Klaassen, and Rouder examine theories represented by restrictions on a
+common parameter space. In their ordinal examples, WAIC and leave-one-out
+cross-validation do not favor the restricted model even when the data comply
+with its constraint. They argue that a forced partition into disjoint regions
+can replace scientifically meaningful overlapping models with regions that
+carry no theoretical interpretation.[^1] [Provisional framing: Kellen and
+Klauer (2020) has not yet been read, so the phrase “sharpest published
+criticism” remains provisional.]
+
+Our experiment mirrors the parameter-region issue directly. It does not rely
+on the toy example's cross-family nesting. The encompassing candidate
+$M_e$ uses
+
+$$
+y(x)=A\sin(\omega x+\phi)+bx+c+\epsilon,
+$$
+
+with unrestricted $b$. The restricted candidate $M_r \subset M_e$ uses the
+same expression and imposes $b\geq 0$. Both candidates call the same bounded
+MLE routine, use the same starts, and share every bound except the lower bound
+on $b$. The frozen $N=20$ data use seed 42 and the true slope $b=0.25$, so the
+restriction holds in truth.[^2]
+
+## 5.1 BMS* comparison
+
+The BMS* calculation follows the validated `toy_elicited` stage-IS path. It
+pools prior-IS caches from seeds 0, 1, and 2, draws 1,000 SIR predictives with
+seed 42, and evaluates 60 locations. For every predictive data pattern
+$\psi$, the free and restricted fits minimize the primary
+`pw_kl_vcal` value $G(\psi,\theta)$ over their respective parameter regions.
+Thus the calculation supplies candidate instances from a shared $\psi$ rather
+than introducing candidate-parameter priors. Such priors contribute only to
+the separate LOO comparison below.[^2]
+
+The nesting check passed at a $2\times10^{-7}$ absolute tolerance. On 999
+predictives, the free optimum had $b\geq0$, and both candidates produced
+identical primary $G$ values. One predictive had a negative free optimum, for
+a fraction of 0.001. On that row, restricted minus free $G$ equaled
+0.000360, so the required one-sided ordering also held.[^2]
+
+Table 5.1 reports both aggregation conventions across the preregistered
+temperature grid. Each pair normalizes over only the free and restricted
+candidates.[^2]
+
+| $\tau$ | pooled free | pooled restricted | expected-posterior free | expected-posterior restricted |
+|---:|---:|---:|---:|---:|
+| 0.1 | 0.500003900 | 0.499996100 | 0.500000900 | 0.499999100 |
+| 0.3 | 0.500000570 | 0.499999430 | 0.500000300 | 0.499999700 |
+| 1.0 | 0.500000112 | 0.499999888 | 0.500000090 | 0.499999910 |
+| 3.0 | 0.500000032 | 0.499999968 | 0.500000030 | 0.499999970 |
+| 10.0 | 0.500000009 | 0.499999991 | 0.500000009 | 0.499999991 |
+
+At the headline value $\tau=1$, both conventions therefore give an effective
+tie. The free candidate's advantage decreases monotonically as $\tau$
+increases, and neither aggregation choice changes the conclusion. The
+appendix-only `kl_forward` calculation also remains within 0.0006 of an equal
+split across the grid.[^2]
+
+The result does not support a claim that BMS* preferentially rewards a
+satisfied restriction in this instance. BMS* assigns the restricted candidate
+essentially half the probability without partitioning the parameter space,
+but the encompassing candidate can reproduce every restricted optimum. The
+single predictive with a negative slope creates the entire primary-metric gap.
+Without an explicit parameter-volume or complexity term, the satisfied
+restriction supplies equality on shared optima rather than an automatic
+advantage. Soft transfer makes that null result visible across $\tau$; a hard
+best-match treatment would retain only the limiting row assignments.
+
+## 5.2 PSIS-LOO comparison
+
+Both Bayesian candidates use the identical 20 observations and likelihood.
+Their weakly informative priors apply only to this LOO arm: $A\sim$
+HalfNormal(5), $\omega\sim$ LogNormal(0, 0.7), $\phi\sim$
+Uniform($-\pi,\pi$), $c\sim$ Normal(0, 5), and $\sigma\sim$
+HalfNormal(2). The free model uses $b\sim$ Normal(0, 5); the restricted model
+uses the corresponding zero-truncated distribution, $b\sim$ HalfNormal(5).
+No prior from this list enters the BMS* calculation.[^2]
+
+Pyro NUTS ran two sequential chains with seeds 20260811 and 20260812. Each
+chain used 1,000 warmup iterations and retained 1,000 draws, with target
+acceptance probability 0.90 and maximum tree depth 8. Both fits recorded zero
+divergences. Rank-normalized $\widehat R$ reached at most 1.003 for the free
+fit and 1.002 for the restricted fit; minimum bulk effective sample sizes were
+1,004 and 1,638, respectively.[^2]
+
+| candidate | `elpd_loo` | SE | `p_loo` | max Pareto $k$ | warning |
+|---|---:|---:|---:|---:|---|
+| free Sin+Linear | -13.074 | 3.458 | 5.343 | 0.564 | no |
+| slope-constrained Sin+Linear | -12.661 | 3.594 | 5.169 | 0.718 | yes, one observation |
+
+The constrained-minus-free `elpd_loo` difference equals 0.413 with a paired SE
+of 0.263.[^2] On its face, PSIS-LOO assigns the higher predictive score to the
+restricted candidate, while BMS* produces an effective tie. ArviZ nevertheless
+flags the restricted estimate because one observation exceeds the
+sample-size-specific good-$k$ threshold of 0.697. Pareto shape values above
+about 0.7 can make the importance-sampling approximation unreliable, so the
+direction should not support a decisive claim without exact refits or a more
+robust cross-validation calculation.[^3]
+
+This head-to-head does not reproduce a categorical LOO failure, and it does
+not show preferential BMS* credit for the satisfied constraint. It instead
+separates two mechanisms on identical data. LOO changes because the two
+Bayesian fits use different support for $b$; BMS* changes only when a shared
+$\psi$ has a negative free optimum. Here that event occurs once in 1,000 SIR
+predictives, leaving the BMS* result numerically indistinguishable from a tie.
+
+[^1]: 🟢 peer-reviewed — Haaf, Klaassen, and Rouder (2025). Bayes factor vs. posterior predictive model assessment: Insights from ordinal constraints. *Computational Brain & Behavior*. https://doi.org/10.1007/s42113-025-00240-0
+[^2]: 🟠 empirical — `experiments/haaf_nested_constraint.py`; `runs/haaf_nested_constraint/results.json` and `README.md` (data seed 42; prior-IS seeds 0, 1, 2; SIR seed 42; NUTS seeds 20260811 and 20260812).
+[^3]: 🟢 peer-reviewed — Vehtari, Gelman, and Gabry (2017). Practical Bayesian model evaluation using leave-one-out cross-validation and WAIC. *Statistics and Computing*, 27(5), 1413–1432.
+
+---
+*Provenance: `runs/haaf_nested_constraint/` · `experiments/haaf_nested_constraint.py` · Notes/DECISIONS.md D63.*
diff --git a/experiments/haaf_nested_constraint.py b/experiments/haaf_nested_constraint.py
new file mode 100644
index 0000000..0637746
--- /dev/null
+++ b/experiments/haaf_nested_constraint.py
@@ -0,0 +1,871 @@
+"""
+Case C: a nested slope constraint under BMS* and PSIS-LOO.
+
+The experiment uses the frozen N=20 thesis toy data and the validated
+``toy_elicited`` stage-IS path.  Each SIR predictive pattern is fit by the
+same Sin+Linear functional form twice.  The restricted fit changes only the
+slope bound from unbounded to nonnegative.  BMS* uses no candidate-parameter
+prior.  Separate Pyro models provide the weakly informative priors needed for
+the PSIS-LOO comparison.
+
+Canonical run from the repository root:
+
+    python experiments/haaf_nested_constraint.py
+
+The canonical artifacts are written under ``runs/haaf_nested_constraint/``.
+``--quick`` provides a development check with smaller Monte Carlo budgets and
+writes ``results_quick.json`` without replacing the canonical artifacts.
+"""
+
+from __future__ import annotations
+
+# ruff: noqa: E402
+
+import argparse
+import hashlib
+import json
+import math
+import os
+import sys
+from dataclasses import dataclass
+from typing import Dict, Iterable, List, Optional, Sequence, Tuple
+
+SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
+REPO = os.path.dirname(SCRIPT_DIR)
+sys.path.insert(0, REPO)
+sys.path.insert(0, SCRIPT_DIR)
+
+import arviz as az
+import numpy as np
+import pyro
+import pyro.distributions as dist
+import torch
+from pyro.infer import MCMC, NUTS
+from pyro.infer.autoguide.initialization import init_to_value
+
+import e7_convention_sensitivity as e7
+import prior_sensitivity_study as pss
+from bistar_gp import generate_toy_data
+from bistar_gp.bms_star import METRICS
+from bistar_gp.candidates import CandidateModel, CandidateResult
+
+
+torch.set_default_dtype(torch.float64)
+
+OUT_DIR = os.path.join(REPO, "runs", "haaf_nested_constraint")
+RESULTS_PATH = os.path.join(OUT_DIR, "results.json")
+README_PATH = os.path.join(OUT_DIR, "README.md")
+
+DATA_SEED = 42
+CONFIG = "toy_elicited"
+IS_SEEDS = [0, 1, 2]
+SIR_SEED = 42
+N_PRED = 1000
+TAUS = [0.1, 0.3, 1.0, 3.0, 10.0]
+PRIMARY_METRIC = "pw_kl_vcal"
+APPENDIX_METRIC = "kl_forward"
+VARIANTS = ["pooled", "expected_posterior"]
+
+LOO_CHAIN_SEEDS = [20260811, 20260812]
+LOO_WARMUP = 1000
+LOO_DRAWS = 1000
+LOO_TARGET_ACCEPT = 0.90
+LOO_MAX_TREE_DEPTH = 8
+
+# Numerical gates test the nesting identity, not statistical significance.
+G_EQUAL_ATOL = 2e-7
+G_ORDER_ATOL = 2e-7
+BOUND_ATOL = 1e-10
+
+# Cross-machine rerun tolerances recorded in the README and results artifact.
+# The structural gates above remain much tighter.
+RERUN_TOLERANCES = {
+    "bms_probability_abs": 0.005,
+    "loo_elpd_abs": 0.25,
+    "loo_pairwise_difference_abs": 0.25,
+    "negative_slope_fraction_abs": 0.005,
+}
+
+MODEL_NAMES = ["Free Sin+Linear", "Slope-constrained Sin+Linear"]
+PARAMETER_NAMES = ["A", "omega", "phi", "b", "c", "sigma"]
+
+PRIOR_DESCRIPTIONS = {
+    "A": "HalfNormal(scale=5)",
+    "omega": "LogNormal(loc=0, scale=0.7)",
+    "phi": "Uniform(-pi, pi)",
+    "b_free": "Normal(loc=0, scale=5)",
+    "b_constrained": "HalfNormal(scale=5), the zero-truncated counterpart",
+    "c": "Normal(loc=0, scale=5)",
+    "sigma": "HalfNormal(scale=2)",
+}
+
+
+def _float(value) -> float:
+    """Convert numpy, torch, and xarray scalars to a JSON-safe float."""
+    if hasattr(value, "values"):
+        value = value.values
+    if isinstance(value, torch.Tensor):
+        value = value.detach().cpu().numpy()
+    return float(np.asarray(value))
+
+
+def _sha256_arrays(*arrays: np.ndarray) -> str:
+    digest = hashlib.sha256()
+    for array in arrays:
+        digest.update(np.ascontiguousarray(array, dtype="<f8").tobytes())
+    return digest.hexdigest()
+
+
+def _sha256_file(path: str) -> str:
+    digest = hashlib.sha256()
+    with open(path, "rb") as handle:
+        for block in iter(lambda: handle.read(1024 * 1024), b""):
+            digest.update(block)
+    return digest.hexdigest()
+
+
+class NestedSinLinearModel(CandidateModel):
+    """Sin+Linear fitted through CandidateModel._fit_mle with one bound fork."""
+
+    def __init__(self, constrained: bool):
+        self.constrained = constrained
+        self.name = MODEL_NAMES[int(constrained)]
+        self.vector = np.array([1.0, 1.0, 0.0, 0.25, 0.0, np.log(0.3)])
+        self.sigma = 0.3
+
+    @staticmethod
+    def _mean(x: np.ndarray, params: Sequence[float]) -> np.ndarray:
+        A, omega, phi, b, c = params
+        return A * np.sin(omega * x + phi) + b * x + c
+
+    @property
+    def bounds(self) -> List[Tuple[Optional[float], Optional[float]]]:
+        bounds: List[Tuple[Optional[float], Optional[float]]] = [
+            (None, None),
+            (None, None),
+            (None, None),
+            (None, None),
+            (None, None),
+            (-10.0, 5.0),
+        ]
+        if self.constrained:
+            bounds[3] = (0.0, None)
+        return bounds
+
+    @staticmethod
+    def base_starts() -> List[np.ndarray]:
+        return [
+            np.array([1.0, omega, 0.0, 0.25, 0.0, np.log(0.3)])
+            for omega in (0.5, 1.0, 1.5, 2.0)
+        ]
+
+    def fit_all(
+        self,
+        x: np.ndarray,
+        y: np.ndarray,
+        weights: Optional[np.ndarray] = None,
+        extra_starts: Iterable[np.ndarray] = (),
+    ) -> List[np.ndarray]:
+        """Return finite multistart fits while preserving the bound fork."""
+        x = np.asarray(x, dtype=float)
+        y = np.asarray(y, dtype=float)
+        if weights is None:
+            scale = np.ones_like(y)
+        else:
+            weights = np.asarray(weights, dtype=float)
+            if np.any(~np.isfinite(weights)) or np.any(weights <= 0):
+                raise ValueError("candidate weights must remain finite and positive")
+            scale = np.sqrt(weights)
+        y_scaled = y * scale
+
+        def f_scaled(x_values, params):
+            return self._mean(x_values, params) * scale
+
+        starts = self.base_starts() + [np.asarray(v, dtype=float).copy()
+                                       for v in extra_starts]
+        fitted = []
+        for start in starts:
+            if self.constrained:
+                start[3] = max(0.0, start[3])
+            try:
+                vector, nll = self._fit_mle(
+                    x, y_scaled, f_scaled, start, bounds=self.bounds)
+            except Exception:
+                continue
+            if np.isfinite(nll) and np.all(np.isfinite(vector)):
+                if self.constrained and vector[3] < -BOUND_ATOL:
+                    raise RuntimeError("bounded fit returned a negative slope")
+                fitted.append(np.asarray(vector, dtype=float))
+        if not fitted:
+            raise RuntimeError(f"all multistart fits failed for {self.name}")
+        return fitted
+
+    def set_vector(self, vector: np.ndarray, y: np.ndarray, x: np.ndarray) -> None:
+        self.vector = np.asarray(vector, dtype=float).copy()
+        residual = np.asarray(y) - self._mean(np.asarray(x), self.vector[:-1])
+        self.sigma = max(float(np.sqrt(np.mean(residual ** 2))), 1e-8)
+
+    @property
+    def slope(self) -> float:
+        return float(self.vector[3])
+
+    def predict(self, x_eval: np.ndarray) -> CandidateResult:
+        mean = self._mean(np.asarray(x_eval, dtype=float), self.vector[:-1])
+        return self._make_result(
+            x_eval,
+            mean,
+            self.sigma ** 2,
+            {
+                "A": float(self.vector[0]),
+                "omega": float(self.vector[1]),
+                "phi": float(self.vector[2]),
+                "b": float(self.vector[3]),
+                "c": float(self.vector[4]),
+                "sigma": float(self.sigma),
+            },
+        )
+
+
+@dataclass
+class PairFit:
+    free: CandidateResult
+    constrained: CandidateResult
+    free_slope: float
+    primary_G: np.ndarray
+    appendix_G: np.ndarray
+
+
+def _candidate_G(psi, candidate: CandidateResult, metric_name: str) -> float:
+    return float(METRICS[metric_name](
+        psi.mean, psi.cov, candidate.mean, candidate.cov))
+
+
+def fit_nested_pair(x_eval: np.ndarray, psi) -> PairFit:
+    """Minimize primary G over encompassing and restricted parameter regions."""
+    variance = np.maximum(np.diag(psi.cov), 1e-10)
+    weights = 1.0 / variance
+
+    free_model = NestedSinLinearModel(constrained=False)
+    free_vectors = free_model.fit_all(x_eval, psi.mean, weights=weights)
+
+    constrained_model = NestedSinLinearModel(constrained=True)
+    constrained_vectors = constrained_model.fit_all(
+        x_eval, psi.mean, weights=weights,
+        extra_starts=[v.copy() for v in free_vectors],
+    )
+
+    # Every constrained solution also belongs to the free region.  Retaining
+    # those feasible vectors in the free search makes the numerical nesting
+    # check independent of local optimizer tie-breaking.
+    free_candidates = free_vectors + [v.copy() for v in constrained_vectors]
+    constrained_candidates = constrained_vectors + [
+        v.copy() for v in free_vectors if v[3] >= -BOUND_ATOL
+    ]
+
+    def select(model: NestedSinLinearModel,
+               vectors: Sequence[np.ndarray]) -> Tuple[np.ndarray, CandidateResult, float]:
+        best = None
+        for vector in vectors:
+            model.set_vector(vector, psi.mean, x_eval)
+            result = model.predict(x_eval)
+            value = _candidate_G(psi, result, PRIMARY_METRIC)
+            if best is None or value < best[2]:
+                best = (vector.copy(), result, value)
+        if best is None:
+            raise RuntimeError(f"no finite candidate result for {model.name}")
+        return best
+
+    free_vector, free_result, free_G = select(free_model, free_candidates)
+    _constrained_vector, constrained_result, constrained_G = select(
+        constrained_model, constrained_candidates)
+
+    # An interior free optimum belongs to both regions.  Reuse its exact
+    # representation when float-level optimizer noise separates equal optima.
+    if free_vector[3] >= -BOUND_ATOL:
+        constrained_model.set_vector(free_vector, psi.mean, x_eval)
+        shared_result = constrained_model.predict(x_eval)
+        shared_G = _candidate_G(psi, shared_result, PRIMARY_METRIC)
+        if shared_G <= constrained_G + G_EQUAL_ATOL:
+            constrained_result = shared_result
+            constrained_G = shared_G
+
+    if free_G > constrained_G + G_ORDER_ATOL:
+        raise RuntimeError(
+            f"nesting order failed: free G={free_G}, constrained G={constrained_G}")
+
+    appendix = np.array([
+        _candidate_G(psi, free_result, APPENDIX_METRIC),
+        _candidate_G(psi, constrained_result, APPENDIX_METRIC),
+    ])
+    return PairFit(
+        free=free_result,
+        constrained=constrained_result,
+        free_slope=float(free_vector[3]),
+        primary_G=np.array([free_G, constrained_G]),
+        appendix_G=appendix,
+    )
+
+
+def observed_pair(x: np.ndarray, y: np.ndarray,
+                  x_eval: np.ndarray) -> Tuple[List[CandidateResult], Dict]:
+    """Fit the observed data pair through the same bound-only model classes."""
+    free_model = NestedSinLinearModel(constrained=False)
+    free_vectors = free_model.fit_all(x, y)
+    free_model.set_vector(free_vectors[0], y, x)
+    free_best = min(
+        free_vectors,
+        key=lambda v: np.mean((y - free_model._mean(x, v[:-1])) ** 2),
+    )
+    free_model.set_vector(free_best, y, x)
+
+    constrained_model = NestedSinLinearModel(constrained=True)
+    constrained_vectors = constrained_model.fit_all(
+        x, y, extra_starts=[free_best])
+    constrained_best = min(
+        constrained_vectors,
+        key=lambda v: np.mean((y - constrained_model._mean(x, v[:-1])) ** 2),
+    )
+    if free_best[3] >= -BOUND_ATOL:
+        constrained_best = free_best.copy()
+    constrained_model.set_vector(constrained_best, y, x)
+
+    results = [free_model.predict(x_eval), constrained_model.predict(x_eval)]
+    parameters = {result.name: result.parameters for result in results}
+    return results, parameters
+
+
+def validated_sir_predictives(
+    x: torch.Tensor,
+    y: torch.Tensor,
+    x_eval: torch.Tensor,
+    observed_results: List[CandidateResult],
+    n_pred: int,
+) -> Tuple[List, Dict, np.ndarray, float]:
+    """Call pss._sir_bms and retain the exact predictive rows it scores."""
+    ths, lml = pss.load_pooled_is(CONFIG, IS_SEEDS)
+    weights = np.exp(lml - lml.max())
+    pooled_ess = float(weights.sum() ** 2 / np.sum(weights ** 2))
+
+    captured: Dict[str, List] = {}
+    original_extract = pss.extract_gp_predictives
+
+    def capture_extract(*args, **kwargs):
+        predictives = original_extract(*args, **kwargs)
+        captured["predictives"] = predictives
+        return predictives
+
+    # _sir_bms does not return its predictive objects.  Intercepting the
+    # imported extractor keeps one authoritative SIR call and no copied
+    # resampling or GP-predictive formula.
+    pss.extract_gp_predictives = capture_extract
+    try:
+        per_metric, _, _, indices = pss._sir_bms(
+            pss.STUDY_CONFIGS[CONFIG], x, y, x_eval, observed_results,
+            ths, lml, n_pred, sir_seed=SIR_SEED)
+    finally:
+        pss.extract_gp_predictives = original_extract
+
+    predictives = captured.get("predictives", [])
+    if len(predictives) != n_pred:
+        raise RuntimeError(
+            f"validated path returned {len(predictives)} predictives, expected {n_pred}")
+    return predictives, per_metric, indices, pooled_ess
+
+
+def aggregate_tables(G_by_metric: Dict[str, np.ndarray]) -> Dict:
+    """Use E7's imported aggregation variants over the case-specific G rows."""
+    output = {}
+    for metric_name, G in G_by_metric.items():
+        metric_rows = {}
+        for tau in TAUS:
+            tau_rows = {}
+            for variant in VARIANTS:
+                tau_rows[variant] = [
+                    float(value) for value in e7.aggregate(G, tau, variant)
+                ]
+            metric_rows[str(tau)] = tau_rows
+        output[metric_name] = metric_rows
+    return output
+
+
+def pyro_sin_linear(x: torch.Tensor, y: Optional[torch.Tensor],
+                    constrained: bool) -> None:
+    """Bayesian Sin+Linear likelihood used only for the PSIS-LOO arm."""
+    A = pyro.sample("A", dist.HalfNormal(torch.tensor(5.0)))
+    omega = pyro.sample(
+        "omega", dist.LogNormal(torch.tensor(0.0), torch.tensor(0.7)))
+    phi = pyro.sample(
+        "phi", dist.Uniform(torch.tensor(-math.pi), torch.tensor(math.pi)))
+    if constrained:
+        b = pyro.sample("b", dist.HalfNormal(torch.tensor(5.0)))
+    else:
+        b = pyro.sample(
+            "b", dist.Normal(torch.tensor(0.0), torch.tensor(5.0)))
+    c = pyro.sample("c", dist.Normal(torch.tensor(0.0), torch.tensor(5.0)))
+    sigma = pyro.sample("sigma", dist.HalfNormal(torch.tensor(2.0)))
+    mu = A * torch.sin(omega * x + phi) + b * x + c
+    with pyro.plate("data", len(x)):
+        pyro.sample("obs", dist.Normal(mu, sigma), obs=y)
+
+
+def _initial_values(parameters: Dict[str, float], constrained: bool) -> Dict:
+    values = {
+        "A": torch.tensor(max(abs(parameters["A"]), 1e-3)),
+        "omega": torch.tensor(max(abs(parameters["omega"]), 1e-3)),
+        "phi": torch.tensor(float(np.clip(parameters["phi"],
+                                            -math.pi + 1e-6,
+                                            math.pi - 1e-6))),
+        "b": torch.tensor(max(parameters["b"], 1e-6)
+                          if constrained else parameters["b"]),
+        "c": torch.tensor(parameters["c"]),
+        "sigma": torch.tensor(max(parameters["sigma"], 1e-3)),
+    }
+    return values
+
+
+def run_loo_candidate(
+    x: torch.Tensor,
+    y: torch.Tensor,
+    constrained: bool,
+    mle_parameters: Dict[str, float],
+    warmup: int,
+    draws: int,
+    chain_seeds: Sequence[int],
+) -> Dict:
+    """Run explicit seeded Pyro chains and compute PSIS-LOO with ArviZ."""
+    per_chain = []
+    diverging = []
+    acceptance_rates = []
+    for seed in chain_seeds:
+        pyro.clear_param_store()
+        pyro.set_rng_seed(seed)
+        np.random.seed(seed)
+        torch.manual_seed(seed)
+        kernel = NUTS(
+            lambda x_data, y_data: pyro_sin_linear(
+                x_data, y_data, constrained),
+            init_strategy=init_to_value(
+                values=_initial_values(mle_parameters, constrained)),
+            target_accept_prob=LOO_TARGET_ACCEPT,
+            max_tree_depth=LOO_MAX_TREE_DEPTH,
+        )
+        mcmc = MCMC(
+            kernel,
+            num_samples=draws,
+            warmup_steps=warmup,
+            num_chains=1,
+            disable_progbar=True,
+        )
+        mcmc.run(x, y)
+        samples = {
+            key: value.detach().cpu().numpy()
+            for key, value in mcmc.get_samples().items()
+        }
+        per_chain.append(samples)
+        diagnostics = mcmc.diagnostics()
+        divergent_indices = diagnostics["divergences"].get("chain 0", [])
+        mask = np.zeros(draws, dtype=bool)
+        mask[np.asarray(divergent_indices, dtype=int)] = True
+        diverging.append(mask)
+        acceptance_rates.append(float(
+            diagnostics["acceptance rate"].get("chain 0", float("nan"))))
+
+    posterior = {
+        key: np.stack([chain[key] for chain in per_chain], axis=0)
+        for key in PARAMETER_NAMES
+    }
+    x_np = x.detach().cpu().numpy()
+    y_np = y.detach().cpu().numpy()
+    mu = (
+        posterior["A"][..., None]
+        * np.sin(posterior["omega"][..., None] * x_np
+                 + posterior["phi"][..., None])
+        + posterior["b"][..., None] * x_np
+        + posterior["c"][..., None]
+    )
+    sigma = posterior["sigma"][..., None]
+    log_likelihood = (
+        -0.5 * np.log(2.0 * np.pi * sigma ** 2)
+        -0.5 * ((y_np - mu) / sigma) ** 2
+    )
+    idata = az.from_dict(
+        posterior=posterior,
+        sample_stats={"diverging": np.stack(diverging, axis=0)},
+        log_likelihood={"obs": log_likelihood},
+        observed_data={"obs": y_np},
+        constant_data={"x": x_np},
+    )
+    loo = az.loo(idata, pointwise=True)
+    rhat_data = az.rhat(idata, var_names=PARAMETER_NAMES, method="rank")
+    ess_bulk_data = az.ess(idata, var_names=PARAMETER_NAMES, method="bulk")
+    ess_tail_data = az.ess(idata, var_names=PARAMETER_NAMES, method="tail")
+    rhat = {name: _float(rhat_data[name]) for name in PARAMETER_NAMES}
+    ess_bulk = {name: _float(ess_bulk_data[name]) for name in PARAMETER_NAMES}
+    ess_tail = {name: _float(ess_tail_data[name]) for name in PARAMETER_NAMES}
+    pareto_k = np.asarray(loo.pareto_k, dtype=float)
+    record = {
+        "elpd_loo": _float(loo.elpd_loo),
+        "se": _float(loo.se),
+        "p_loo": _float(loo.p_loo),
+        "pointwise_elpd": [float(value) for value in np.asarray(loo.loo_i)],
+        "pareto_k": {
+            "max": float(np.max(pareto_k)),
+            "good_k_threshold": _float(loo.good_k),
+            "warning": bool(loo.warning),
+            "n_over_good_k_threshold": int(np.sum(pareto_k > _float(loo.good_k))),
+            "n_over_0_5": int(np.sum(pareto_k > 0.5)),
+            "n_over_0_7": int(np.sum(pareto_k > 0.7)),
+            "n_over_1_0": int(np.sum(pareto_k > 1.0)),
+            "values": [float(value) for value in pareto_k],
+        },
+        "sampler": {
+            "chains": len(chain_seeds),
+            "warmup_per_chain": warmup,
+            "draws_per_chain": draws,
+            "chain_seeds": list(chain_seeds),
+            "target_accept_prob": LOO_TARGET_ACCEPT,
+            "max_tree_depth": LOO_MAX_TREE_DEPTH,
+            "divergences_by_chain": [int(mask.sum()) for mask in diverging],
+            "divergences_total": int(sum(mask.sum() for mask in diverging)),
+            "acceptance_rate_by_chain": acceptance_rates,
+            "r_hat": rhat,
+            "r_hat_max": float(max(rhat.values())),
+            "ess_bulk": ess_bulk,
+            "ess_bulk_min": float(min(ess_bulk.values())),
+            "ess_tail": ess_tail,
+            "ess_tail_min": float(min(ess_tail.values())),
+        },
+    }
+    return record
+
+
+def loo_comparison(free: Dict, constrained: Dict) -> Dict:
+    """Return paired pointwise ELPD difference for constrained minus free."""
+    pointwise = (np.asarray(constrained["pointwise_elpd"], dtype=float)
+                 - np.asarray(free["pointwise_elpd"], dtype=float))
+    difference = constrained["elpd_loo"] - free["elpd_loo"]
+    se = float(np.sqrt(len(pointwise) * np.var(pointwise, ddof=1)))
+    return {
+        "direction": "constrained_minus_free",
+        "elpd_difference": float(difference),
+        "se": se,
+        "pointwise_differences": [float(value) for value in pointwise],
+    }
+
+
+def render_readme(results: Dict) -> str:
+    bms = results["bms_star"]
+    loo = results["psis_loo"]
+    headline = bms["tables"][PRIMARY_METRIC]["1.0"]
+    lines = [
+        "# Haaf-style nested constraint: BMS* and PSIS-LOO",
+        "",
+        "Run from the repository root:",
+        "",
+        "```bash",
+        "python experiments/haaf_nested_constraint.py",
+        "```",
+        "",
+        "The command regenerates `results.json` and this README. It uses the ",
+        "frozen `generate_toy_data()` defaults: N=20, data seed 42, true ",
+        "slope b=0.25, and observation standard deviation 0.5. The free and ",
+        "restricted candidates share the Sin+Linear form. Their only region ",
+        "difference concerns the slope bound: the free fit accepts every real ",
+        "b, while the restricted fit requires b greater than or equal to zero.",
+        "",
+        "## BMS* path and cache dependency",
+        "",
+        "The run imports `prior_sensitivity_study.py`, loads the pooled ",
+        "`toy_elicited` prior-IS caches for seeds 0, 1, and 2, and calls its ",
+        "stage-IS SIR machinery with seed 42 and 1,000 predictives. It imports ",
+        "the pooled and expected-posterior aggregation implementations from ",
+        "`e7_convention_sensitivity.py`. The primary metric uses ",
+        "`pw_kl_vcal`; `kl_forward` appears only as an appendix stress metric.",
+        "",
+        "A fresh clone must first regenerate the local caches:",
+        "",
+        "```bash",
+        "python experiments/prior_sensitivity_study.py --stage a --configs toy_elicited --is-n 60000 --is-seeds 0 1 2",
+        "python experiments/haaf_nested_constraint.py",
+        "```",
+        "",
+        "Expected cache paths:",
+        "",
+        "- `runs/prior_sensitivity/is_draws_toy_elicited_s0.npz`",
+        "- `runs/prior_sensitivity/is_draws_toy_elicited_s1.npz`",
+        "- `runs/prior_sensitivity/is_draws_toy_elicited_s2.npz`",
+        "",
+        "For each shared predictive pattern, both candidates minimize the ",
+        "primary G over their parameter regions through ",
+        "`CandidateModel._fit_mle`. No candidate-parameter prior contributes ",
+        "to the BMS* calculation.",
+        "",
+        "At τ = 1, pooled BMS* assigns "
+        f"{headline['pooled'][0]:.6f} to the free candidate and "
+        f"{headline['pooled'][1]:.6f} to the restricted candidate. "
+        "Expected-posterior aggregation assigns "
+        f"{headline['expected_posterior'][0]:.6f} and "
+        f"{headline['expected_posterior'][1]:.6f}, respectively. The free-fit "
+        f"slope falls below zero for {bms['slope_sign']['negative_fraction']:.6f} "
+        "of SIR predictives.",
+        "",
+        "## PSIS-LOO priors and sampler",
+        "",
+        "The LOO comparison uses the identical x and y values. These priors ",
+        "apply only to the LOO arm:",
+        "",
+    ]
+    for name, description in PRIOR_DESCRIPTIONS.items():
+        lines.append(f"- `{name}`: {description}")
+    lines += [
+        "",
+        "Pyro NUTS runs two sequential chains with seeds 20260811 and ",
+        "20260812, 1,000 warmup iterations and 1,000 retained draws per chain, ",
+        "target acceptance probability 0.90, and maximum tree depth 8. ArviZ ",
+        "receives the pointwise Normal log likelihoods and computes PSIS-LOO.",
+        "",
+        "## Headline PSIS-LOO",
+        "",
+        "| candidate | elpd_loo | SE | p_loo | max Pareto k | warning | divergences | max r_hat |",
+        "|---|---:|---:|---:|---:|---|---:|---:|",
+    ]
+    for key, label in (("free", MODEL_NAMES[0]),
+                       ("constrained", MODEL_NAMES[1])):
+        row = loo["candidates"][key]
+        sampler = row["sampler"]
+        lines.append(
+            f"| {label} | {row['elpd_loo']:.3f} | {row['se']:.3f} | "
+            f"{row['p_loo']:.3f} | {row['pareto_k']['max']:.3f} | "
+            f"{'yes' if row['pareto_k']['warning'] else 'no'} | "
+            f"{sampler['divergences_total']} | {sampler['r_hat_max']:.3f} |")
+    pair = loo["pairwise"]
+    lines += [
+        "",
+        "The paired constrained-minus-free elpd difference equals "
+        f"{pair['elpd_difference']:.3f} with SE {pair['se']:.3f}.",
+        "ArviZ flags the constrained estimate because "
+        f"{loo['candidates']['constrained']['pareto_k']['n_over_good_k_threshold']} "
+        "observation exceeds its sample-size-specific good-k threshold. Interpret "
+        "the direction with that qualification.",
+        "",
+        "## Determinism and tolerances",
+        "",
+        "All random-number seeds appear in `results.json`. On the pinned ",
+        "environment, repeated CPU runs should reproduce the artifact. Across ",
+        "compatible machines and library builds, use these absolute comparison ",
+        "tolerances:",
+        "",
+    ]
+    for key, value in RERUN_TOLERANCES.items():
+        lines.append(f"- `{key}`: {value}")
+    lines += [
+        "",
+        f"The primary nesting gates use {G_EQUAL_ATOL:g} absolute tolerance "
+        "for equality on nonnegative free-slope rows and "
+        f"{G_ORDER_ATOL:g} for the one-sided G ordering on negative-slope rows. ",
+        "A failure stops the run before artifact replacement.",
+        "",
+        "No figure accompanies the case because the comparison table and the ",
+        "slope-sign diagnostic convey the full result without an additional ",
+        "visual encoding.",
+        "",
+    ]
+    return "\n".join(line.rstrip() for line in lines)
+
+
+def main() -> None:
+    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
+    parser.add_argument(
+        "--quick", action="store_true",
+        help="run a small development check and write results_quick.json")
+    args = parser.parse_args()
+
+    n_pred = 40 if args.quick else N_PRED
+    warmup = 75 if args.quick else LOO_WARMUP
+    draws = 75 if args.quick else LOO_DRAWS
+
+    x, y, info = generate_toy_data()
+    x_np = x.detach().cpu().numpy()
+    y_np = y.detach().cpu().numpy()
+    x_eval_np = np.linspace(x_np.min() - 1.0, x_np.max() + 1.0, 60)
+    x_eval = torch.tensor(x_eval_np).double()
+    if len(x_np) != 20 or info["bias_slope"] != 0.25:
+        raise RuntimeError("the frozen N=20, b=0.25 data convention changed")
+
+    observed_results, observed_parameters = observed_pair(
+        x_np, y_np, x_eval_np)
+    print("Loading validated SIR predictives")
+    predictives, pss_anchor, sir_indices, pooled_ess = validated_sir_predictives(
+        x, y, x_eval, observed_results, n_pred)
+
+    print(f"Fitting the nested candidate pair to {len(predictives)} predictives")
+    pair_fits = []
+    for index, psi in enumerate(predictives):
+        pair_fits.append(fit_nested_pair(x_eval_np, psi))
+        if (index + 1) % 100 == 0 or index + 1 == len(predictives):
+            print(f"  fitted {index + 1}/{len(predictives)}")
+
+    primary_G = np.vstack([fit.primary_G for fit in pair_fits])
+    appendix_G = np.vstack([fit.appendix_G for fit in pair_fits])
+    slopes = np.array([fit.free_slope for fit in pair_fits])
+    negative = slopes < -BOUND_ATOL
+    nonnegative = ~negative
+    gap = primary_G[:, 1] - primary_G[:, 0]
+    max_equal_difference = (
+        float(np.max(np.abs(gap[nonnegative]))) if np.any(nonnegative) else 0.0)
+    min_negative_gap = (
+        float(np.min(gap[negative])) if np.any(negative) else None)
+    if max_equal_difference > G_EQUAL_ATOL:
+        raise RuntimeError(
+            f"nonnegative-slope identity failed at {max_equal_difference}")
+    if np.any(negative) and min_negative_gap is not None \
+            and min_negative_gap < -G_ORDER_ATOL:
+        raise RuntimeError(f"negative-slope nesting order failed at {min_negative_gap}")
+
+    G_by_metric = {
+        PRIMARY_METRIC: primary_G,
+        APPENDIX_METRIC: appendix_G,
+    }
+    tables = aggregate_tables(G_by_metric)
+
+    print("Running PSIS-LOO models")
+    free_loo = run_loo_candidate(
+        x, y, False, observed_parameters[MODEL_NAMES[0]], warmup, draws,
+        LOO_CHAIN_SEEDS)
+    constrained_loo = run_loo_candidate(
+        x, y, True, observed_parameters[MODEL_NAMES[1]], warmup, draws,
+        LOO_CHAIN_SEEDS)
+    pairwise = loo_comparison(free_loo, constrained_loo)
+
+    cache_records = []
+    for seed in IS_SEEDS:
+        path = pss._is_draw_path(CONFIG, seed)
+        with np.load(path) as cache:
+            cache_records.append({
+                "seed": seed,
+                "path": os.path.relpath(path, REPO),
+                "n_draws": int(len(cache["lml"])),
+                "sha256": _sha256_file(path),
+            })
+
+    results = {
+        "case": "Case C, nested slope constraint",
+        "protocol_date": "2026-08-11",
+        "quick": bool(args.quick),
+        "data": {
+            "generator": "bistar_gp.generate_toy_data defaults",
+            "n": int(len(x_np)),
+            "seed": DATA_SEED,
+            "x_range": [float(x_np.min()), float(x_np.max())],
+            "true_bias_slope": float(info["bias_slope"]),
+            "noise_std": float(info["noise_std"]),
+            "xy_sha256_float64_le": _sha256_arrays(x_np, y_np),
+        },
+        "candidate_definition": {
+            "functional_form": "A sin(omega x + phi) + b x + c",
+            "model_names": MODEL_NAMES,
+            "free_bounds": NestedSinLinearModel(False).bounds,
+            "constrained_bounds": NestedSinLinearModel(True).bounds,
+            "only_bound_difference_index": 3,
+            "only_bound_difference_parameter": "b",
+            "observed_data_mle": observed_parameters,
+        },
+        "bms_star": {
+            "config": CONFIG,
+            "is_seeds": IS_SEEDS,
+            "sir_seed": SIR_SEED,
+            "n_sir_draws": int(n_pred),
+            "n_unique_sir_draws": int(len(np.unique(sir_indices))),
+            "pooled_is_ess": pooled_ess,
+            "cache_dependencies": cache_records,
+            "primary_metric": PRIMARY_METRIC,
+            "appendix_metric": APPENDIX_METRIC,
+            "taus": TAUS,
+            "aggregation_variants": VARIANTS,
+            "tables": tables,
+            "slope_sign": {
+                "negative_count": int(np.sum(negative)),
+                "nonnegative_count": int(np.sum(nonnegative)),
+                "negative_fraction": float(np.mean(negative)),
+                "free_slope_min": float(np.min(slopes)),
+                "free_slope_median": float(np.median(slopes)),
+                "free_slope_max": float(np.max(slopes)),
+            },
+            "sanity_identity_primary_G": {
+                "metric": PRIMARY_METRIC,
+                "equality_atol": G_EQUAL_ATOL,
+                "order_atol": G_ORDER_ATOL,
+                "max_abs_gap_on_nonnegative_free_slope": max_equal_difference,
+                "min_constrained_minus_free_G_on_negative_free_slope": min_negative_gap,
+                "violations": 0,
+            },
+            "G_summary": {
+                PRIMARY_METRIC: {
+                    MODEL_NAMES[0]: {
+                        "mean": float(np.mean(primary_G[:, 0])),
+                        "median": float(np.median(primary_G[:, 0])),
+                    },
+                    MODEL_NAMES[1]: {
+                        "mean": float(np.mean(primary_G[:, 1])),
+                        "median": float(np.median(primary_G[:, 1])),
+                    },
+                    "mean_constrained_minus_free": float(np.mean(gap)),
+                },
+                APPENDIX_METRIC: {
+                    MODEL_NAMES[0]: {
+                        "mean": float(np.mean(appendix_G[:, 0])),
+                        "median": float(np.median(appendix_G[:, 0])),
+                    },
+                    MODEL_NAMES[1]: {
+                        "mean": float(np.mean(appendix_G[:, 1])),
+                        "median": float(np.median(appendix_G[:, 1])),
+                    },
+                },
+            },
+            "validated_pss_observed_fit_anchor": {
+                "metric": PRIMARY_METRIC,
+                "tau": 1.0,
+                "pooled_probabilities": pss_anchor[PRIMARY_METRIC]
+                    ["posteriors"]["1.0"],
+                "observed_candidate_predictions_identical": True,
+            },
+        },
+        "psis_loo": {
+            "priors_apply_only_to_loo": True,
+            "priors": PRIOR_DESCRIPTIONS,
+            "candidates": {
+                "free": free_loo,
+                "constrained": constrained_loo,
+            },
+            "pairwise": pairwise,
+        },
+        "tolerances": {
+            "structural": {
+                "G_equality_atol": G_EQUAL_ATOL,
+                "G_order_atol": G_ORDER_ATOL,
+                "slope_bound_atol": BOUND_ATOL,
+            },
+            "cross_machine_rerun": RERUN_TOLERANCES,
+        },
+        "versions": {
+            "numpy": np.__version__,
+            "torch": torch.__version__,
+            "pyro": pyro.__version__,
+            "arviz": az.__version__,
+        },
+    }
+
+    os.makedirs(OUT_DIR, exist_ok=True)
+    output_path = (os.path.join(OUT_DIR, "results_quick.json")
+                   if args.quick else RESULTS_PATH)
+    with open(output_path, "w", encoding="utf-8") as handle:
+        json.dump(results, handle, indent=2, allow_nan=False)
+        handle.write("\n")
+    if not args.quick:
+        with open(README_PATH, "w", encoding="utf-8") as handle:
+            handle.write(render_readme(results))
+    print(f"Saved {output_path}")
+
+
+if __name__ == "__main__":
+    main()
diff --git a/runs/haaf_nested_constraint/README.md b/runs/haaf_nested_constraint/README.md
new file mode 100644
index 0000000..bc62abe
--- /dev/null
+++ b/runs/haaf_nested_constraint/README.md
@@ -0,0 +1,90 @@
+# Haaf-style nested constraint: BMS* and PSIS-LOO
+
+Run from the repository root:
+
+```bash
+python experiments/haaf_nested_constraint.py
+```
+
+The command regenerates `results.json` and this README. It uses the
+frozen `generate_toy_data()` defaults: N=20, data seed 42, true
+slope b=0.25, and observation standard deviation 0.5. The free and
+restricted candidates share the Sin+Linear form. Their only region
+difference concerns the slope bound: the free fit accepts every real
+b, while the restricted fit requires b greater than or equal to zero.
+
+## BMS* path and cache dependency
+
+The run imports `prior_sensitivity_study.py`, loads the pooled
+`toy_elicited` prior-IS caches for seeds 0, 1, and 2, and calls its
+stage-IS SIR machinery with seed 42 and 1,000 predictives. It imports
+the pooled and expected-posterior aggregation implementations from
+`e7_convention_sensitivity.py`. The primary metric uses
+`pw_kl_vcal`; `kl_forward` appears only as an appendix stress metric.
+
+A fresh clone must first regenerate the local caches:
+
+```bash
+python experiments/prior_sensitivity_study.py --stage a --configs toy_elicited --is-n 60000 --is-seeds 0 1 2
+python experiments/haaf_nested_constraint.py
+```
+
+Expected cache paths:
+
+- `runs/prior_sensitivity/is_draws_toy_elicited_s0.npz`
+- `runs/prior_sensitivity/is_draws_toy_elicited_s1.npz`
+- `runs/prior_sensitivity/is_draws_toy_elicited_s2.npz`
+
+For each shared predictive pattern, both candidates minimize the
+primary G over their parameter regions through
+`CandidateModel._fit_mle`. No candidate-parameter prior contributes
+to the BMS* calculation.
+
+At τ = 1, pooled BMS* assigns 0.500000 to the free candidate and 0.500000 to the restricted candidate. Expected-posterior aggregation assigns 0.500000 and 0.500000, respectively. The free-fit slope falls below zero for 0.001000 of SIR predictives.
+
+## PSIS-LOO priors and sampler
+
+The LOO comparison uses the identical x and y values. These priors
+apply only to the LOO arm:
+
+- `A`: HalfNormal(scale=5)
+- `omega`: LogNormal(loc=0, scale=0.7)
+- `phi`: Uniform(-pi, pi)
+- `b_free`: Normal(loc=0, scale=5)
+- `b_constrained`: HalfNormal(scale=5), the zero-truncated counterpart
+- `c`: Normal(loc=0, scale=5)
+- `sigma`: HalfNormal(scale=2)
+
+Pyro NUTS runs two sequential chains with seeds 20260811 and
+20260812, 1,000 warmup iterations and 1,000 retained draws per chain,
+target acceptance probability 0.90, and maximum tree depth 8. ArviZ
+receives the pointwise Normal log likelihoods and computes PSIS-LOO.
+
+## Headline PSIS-LOO
+
+| candidate | elpd_loo | SE | p_loo | max Pareto k | warning | divergences | max r_hat |
+|---|---:|---:|---:|---:|---|---:|---:|
+| Free Sin+Linear | -13.074 | 3.458 | 5.343 | 0.564 | no | 0 | 1.003 |
+| Slope-constrained Sin+Linear | -12.661 | 3.594 | 5.169 | 0.718 | yes | 0 | 1.002 |
+
+The paired constrained-minus-free elpd difference equals 0.413 with SE 0.263.
+ArviZ flags the constrained estimate because 1 observation exceeds its sample-size-specific good-k threshold. Interpret the direction with that qualification.
+
+## Determinism and tolerances
+
+All random-number seeds appear in `results.json`. On the pinned
+environment, repeated CPU runs should reproduce the artifact. Across
+compatible machines and library builds, use these absolute comparison
+tolerances:
+
+- `bms_probability_abs`: 0.005
+- `loo_elpd_abs`: 0.25
+- `loo_pairwise_difference_abs`: 0.25
+- `negative_slope_fraction_abs`: 0.005
+
+The primary nesting gates use 2e-07 absolute tolerance for equality on nonnegative free-slope rows and 2e-07 for the one-sided G ordering on negative-slope rows.
+A failure stops the run before artifact replacement.
+
+No figure accompanies the case because the comparison table and the
+slope-sign diagnostic convey the full result without an additional
+visual encoding.

