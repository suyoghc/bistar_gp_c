# Case E review package — paper/case-e-debias tip 8f1326d

You are one of the independent reviewers in the HANDOFF §4 four-model protocol,
applied to Case E (the toy debias demonstration, section 07). Review the package
below. Return a verdict line (APPROVE or REVISE) followed by numbered findings,
each with a severity (S1 fatal statistical / S2 substantive statistical or
factual / S3 scope-or-framing / S4 style-or-mechanics), the file and line, the
defective text or number, and the concrete fix. Statistical claims deserve
adversarial scrutiny: check the mathematics, the estimator conventions, the
diagnostics interpretation, and every number against the artifact JSON included
here. Do not raise style findings that contradict the [STYLE] rules below.

## Hard constraints the implementation was bound by (HANDOFF §0, verbatim)
```
## 0. Global protocol (applies to every case)

**Branching.** One branch per case off `main`:
`paper/case-a-vanbork`, `paper/case-b-occam-dial`, `paper/case-c-haaf`,
`paper/case-d-mopen`. Work in this clone (local-only files such as
`Notes/WRITEUP_DECISIONS.md` are gitignored but present in the working tree —
Codex may READ them, must never `git add` them).

**Hard constraints (repeat verbatim in every Codex prompt):**
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
  no "lives/sits" for abstracta; minimal em-dashes (see repo CLAUDE.md +
  user's global rules quoted in `docs/paper-sie-jmp/00-notation.md`).
- Every reported number must be regenerable from a named `experiments/`
  script into a `runs/` artifact; each case commits a same-commit
  `Notes/DECISIONS.md` entry (next free D number).
- Commit scope per branch: `experiments/` script(s), `docs/paper-sie-jmp/`
  section, `Notes/DECISIONS.md` entry, and (deliberately, if evidence-worthy)
  the `runs/` JSON — never figures over 2 MB, never gitignored Notes files.

**Canonical implementation invocation** (pipe the case prompt via stdin):

```bash
git checkout main && git checkout -b paper/case-X-<slug>
cat docs/paper-sie-jmp/prompts/case-X-impl.txt | codex exec --yolo \
  --skip-git-repo-check -m gpt-5.6-sol \
  -c 'model_reasoning_effort="xhigh"' -o /tmp/case-X-impl.txt -
```

The driver session composes `case-X-impl.txt` from §2's work order + §0's
constraints, reads `/tmp/case-X-impl.txt`, verifies (§3), then runs §4.

## 1. Sequencing and blockers
```

## Driver facts
- Branch tip reviewed: 8f1326d (single commit over main: section 07, the
  experiment script, runs/toy_debias_demo/ artifacts, DECISIONS D67).
- The driver independently reran python experiments/toy_debias_demo.py once:
  results.json and debias_figure.png reproduced byte-identically
  (sha256 e73f0672…, 6ebd195f…), exit 0, ~60 s.
- Imports verified: bistar_gp.decompose.decompose_additive_gp,
  decompose_component, bistar_gp.fit.fit_hmc, fit_map all exist.
- Evidence tiers 🟡 thesis and 🟣 framework are legitimate vocabulary from the
  repo's evidence-tiers skill file; section 07 is the first section using them.
- The implementer chose NOT to use bistar_gp.debias.decompose_model_hmc,
  reporting that it discards each draw's conditional covariance
  (bistar_gp/debias.py:206) and would understate debiased uncertainty; the
  demo instead aggregates per-draw component moments with exact mixture
  intervals by CDF bisection over all 1000 draws. Scrutinize this choice.
- Known open item, NOT a finding to re-raise as new: the committed synthesis
  section 08 footnote (excerpt below) predates Case E and now needs its
  'supplies no reported number' wording updated at assembly; flag ONLY if you
  see a sharper inconsistency than the known one.
- Codex (gpt-5.6-sol) is usage-locked until 2026-08-18 and absent this round;
  disclosed per the established substitution pattern.

## Committed synthesis 08-discussion excerpt (context for the 8.5 connection)
```

## 8.5 Costs and scope conditions

The method moves judgment into the data prior, kernel, metric, temperature,
reference measure, and aggregation rule. These choices become visible and
testable, but they still require substantive knowledge. When beliefs about a
bias process come largely from outside the observed data, additional sample
size need not remove the associated uncertainty, and honest inference can retain
an uncertainty floor. That expectation belongs to the program rather than to
any of the four cases reported here, and section 7 of the assembled manuscript
carries the debiasing development that would make it
concrete.[^discussion-floor]

Two scope conditions follow from Case D. Under F1, the GP scaffold may fail to
represent the feature that distinguishes the candidates, so comparison reflects
[^discussion-floor]: 🟠 empirical — forward reference to assembled-manuscript section 7, drafted at `docs/paper-sie-jmp/07-debias-bridge.md`, local material that remains uncommitted in this repository and supplies no reported number; none of the four cases reported here estimates an uncertainty floor.
```

## Section 07 as committed (docs/paper-sie-jmp/07-debias-bridge.md)
```markdown
# 7. From evaluation to debiasing

The accepted proposal and thesis chapter 5 set two goals for this program:
evaluating candidate models through data priors, and mitigating bias. Sections
1 through 6 and 8 develop the first. The second follows from the same
construction rather than from new machinery. Candidates are graded against the
posterior over data patterns ψ, and that posterior supports more than grading.
Under an additive kernel the function underlying each ψ decomposes into
components, each component admits a substantive label, and labeling one
component as bias turns its removal into marginalization. Evaluation and
mitigation therefore draw on one object.[^1]

## 7.1 The demonstration

The data come from `generate_toy_data()` at its defaults: N=20 points on
[-10, 10], seed 42, observation noise 0.5, and y = sin(x) + 0.25x + noise. The
generator itself names the linear term the bias, so the demonstration inherits
a known true process and a known bias process instead of asserting either.[^2]

The GP uses the SE plus linear additive kernel under the `toy_elicited`
data-elicited prior, the configuration validated for this N=20 instance.
Hyperparameters come from the corrected NUTS path in two seeded chains,
20260813 and 20260814, with 500 warmup and 500 retained draws each, target
acceptance 0.8 and maximum tree depth 8. Both chains initialize at the same MAP
point, so the rank-normalized R-hat reported here measures mixing within the
mode the optimizer selected and not agreement between dispersed starts; the toy
hyperparameter posterior is multi-basin, which makes the distinction worth
stating explicitly. Across the four hyperparameters the run gives no
divergences, rank-normalized R-hat at most 1.0025, bulk ESS at least 602.4, and
tail ESS at least 502.6.[^2]

Every one of the 1,000 retained draws is decomposed by the package
additive-kernel machinery into an SE component, treated as the truth candidate,
and a linear component, treated as the bias candidate; all 1,000 decompositions
succeed.[^3] The debiased predictive of the true process consists of the
SE-component posterior with the linear component marginalized out. That
marginalization happens analytically within a draw, because the component
posterior the decomposition returns already forms the marginal of the joint
conditional Gaussian, and by Monte Carlo across draws for the hyperparameters.
Reported intervals are exact central intervals of the resulting draw mixture
rather than Gaussian approximations to it, and all bands are latent-function
bands with no observation noise added.[^2]

![Composite fit, labeled components, and the debiased predictive against the known truth](../../runs/toy_debias_demo/debias_figure.png)

**Figure 7.** Three readings of one posterior on the N=20 toy. Panel (a) shows
the composite posterior predictive against the observed data, which the
composite describes well. Panel (b) shows the two labeled components with their
95 percent central intervals against the generating sin(x) and 0.25x curves.
Panel (c) shows the debiased predictive against the known true process. The
annotated slope and RMSE readouts are computed from the artifact values.

Turning to recovery, the bias-slope posterior has mean 0.197 with standard
deviation 0.072 and a 95 percent central interval of [0.033, 0.323], which
contains the generating value 0.250. On a grid of 201 equally spaced points
inside the training span, the composite posterior mean differs from sin(x) by
an RMSE of 1.430 and the debiased posterior mean by 0.403, a reduction of 1.028
or 71.9 percent. Between-chain scatter in those two quantities is small: 1.431
and 1.430 for the composite arm, 0.403 and 0.402 for the debiased arm.[^2]

The composite value of 1.430 has a plain reading that should be stated rather
than left to the reader. On the same grid the drift 0.25x has RMS 1.451, so the
composite arm's discrepancy with sin(x) essentially reproduces the displacement
it was fitted to include. The debias claim concerns how much of that known
displacement marginalization removes, and it removes most of it. What remains,
0.403, is not negligible against the true process's own RMS of 0.690.[^2]

The debiased band covers sin(x) at 174 of the 201 grid points, 0.866 against a
nominal 0.95. Neighboring grid points share nearly the same posterior, so the
figure summarizes pointwise coverage rather than testing calibration over
independent trials; read that way it records mild undercoverage and not a
validated interval procedure.[^2]

## 7.2 What the demonstration does and does not establish

Two limits deserve statement.

First, identifying the linear component as bias is a modeling choice rather
than an inference. Construction licenses the choice here, because the generator
produced the drift. No generator supplies that warrant in an application, and
the analyst must justify the kernel labeling on substantive grounds before a
marginalization result means what its name suggests. The decomposition
machinery will split an additive posterior whichever way the labels are
assigned, and the split acquires interpretation only from the labeling
argument.

Second, the data determine the split far less sharply than they determine the
fit. The debiased band has mean width 1.836 on the grid while the composite
band has mean width 1.032, so the observations constrain the sum of the two
components more tightly than they constrain either component alone. That
difference gives concrete form to the expectation recorded in section 8.5: when
the grounds for treating one component as bias come from outside the observed
data, additional observations sharpen the composite while leaving the
attribution comparatively uncertain, and honest inference retains an
uncertainty floor that sample size does not remove.[^2]

The full development belongs to the companion line. The program originates in
thesis chapter 5, and the real-data study proceeds under its own
preregistration; no real-data result is reported or forecast here.[^1]

[^1]: 🟡 thesis — Chandramouli (2020), doctoral dissertation, Indiana University; Chapter 5 instantiates BI* with Gaussian Processes and states the debiasing program. 🟣 framework — Chandramouli and Shiffrin (2016), "Extending Bayesian induction," *Journal of Mathematical Psychology*, 72, 38–42.
[^2]: 🟠 empirical — `experiments/toy_debias_demo.py`; `runs/toy_debias_demo/results.json` and `README.md` (data seed 42; MAP-init torch seed 42; NUTS chain seeds 20260813 and 20260814).
[^3]: 🟠 empirical — decomposition through `bistar_gp.decompose.decompose_additive_gp`, the package implementation of the thesis Eq. 5 additive-kernel decomposition, with the joint posterior from `decompose_component` on the summed kernel blocks so the inter-component cross-covariance is retained; success counts and the linear-component structure checks in `runs/toy_debias_demo/results.json`.

---
*Provenance: `runs/toy_debias_demo/` · `experiments/toy_debias_demo.py` ·
`Notes/DECISIONS.md` D67.*
```

## D67 as committed (Notes/DECISIONS.md tail)
```markdown
## D67: Case E toy debias demonstration — evaluation and mitigation from one posterior — 2026-08-13

**Problem:** The thesis (ch. 5) and the accepted proposal set two goals for the
BI*/BMS*-GP program: model evaluation via data priors, and bias mitigation.
Manuscript sections 1-6 and 8 deliver the first; section 7
(`docs/paper-sie-jmp/07-debias-bridge.md`) was still a stub, so the second goal
appeared in the paper only as a promise. The demonstration had to be small,
in-paper, and honest, and it had to be built without touching the D58 Mauna Loa
preregistration boundary, which reserves the real-data development for the
companion line.

**Decision:** Added `experiments/toy_debias_demo.py` and the run directory
`runs/toy_debias_demo/` (`results.json`, `README.md`, `debias_figure.png`), and
replaced the section 7 stub with the full section carrying that one figure.

Data: `bistar_gp.generate_toy_data()` at its defaults (N=20 on [-10, 10], seed
42, observation noise 0.5, `bias_slope=0.25`, y = sin(x) + 0.25x + noise), so
the true process and the bias process are both known by construction.

Fit: SE + linear additive kernel under `PRIOR_CONFIGS["toy_elicited_n20"]`, the
registry entry byte-identical to `experiments/prior_sensitivity_study.py`
STUDY_CONFIGS `toy_elicited`. Hyperparameters from the CORRECTED sampler path
`bistar_gp.fit.fit_hmc` (`nuts_e1`); the pre-correction Pyro NUTS setup is not
used. Two chains, seeds 20260813 and 20260814, 500 warmup + 500 retained draws
each (1,000 pooled), `target_accept_prob` 0.8, `max_tree_depth` 8, initial step
size 0.1 with adaptation. INIT DISCLOSURE: both chains start at the SAME MAP
point (`fit_map`, torch seed 42, 500 iterations, lr 0.05), so the reported
rank-normalized R-hat is WITHIN-MODE evidence about mixing around the
optimizer's mode, not between-mode agreement from dispersed starts; the toy
hyperparameter posterior is multi-basin (D12). The disclosure is carried in
`results.json` (`config.init_strategy`), in the run README, and in the section
prose, per the standing requirement from the Case C review.

Decomposition: the package machinery only. `bistar_gp.decompose
.decompose_additive_gp` for the SE (truth-candidate) and linear
(bias-candidate) components, and `decompose_component` on the summed kernel
blocks for the joint posterior, so the inter-component cross-covariance is
retained rather than dropped by summing component covariances. Debiasing by
marginalization: analytic within a draw (the returned component posterior
already forms the marginal of the joint conditional Gaussian) and Monte Carlo
across draws for the hyperparameters. Bands are latent-function bands with no
observation noise, matching the convention documented in
`experiments/honest_band_decomposition.py`; summary sds use the law of total
variance, and reported intervals are EXACT central intervals of the draw
mixture obtained by CDF bisection rather than mean ± 2 sd approximations.

Slope read: gpytorch's `LinearKernel` gives k(x, x') = v x x', so the linear
component's posterior mean is exactly linear and its posterior covariance
exactly Var(b|θ) x xᵀ. Both properties are verified per draw and the worst
deviations recorded (4.456e-13 for linearity, 1.896e-15 for rank-one variance),
which licenses reading the slope moments off the decomposition output instead
of introducing a separate formula.

**Alternatives considered:** Importing `bistar_gp.debias.decompose_model_hmc`
was rejected because it discards each draw's conditional covariance
(`bistar_gp/debias.py:206`), so its bands show across-draw mean spread alone
and would have understated the debiased uncertainty and wrecked the coverage
number. Importing `total_variance_decomposition` from
`experiments/honest_band_decomposition.py` was rejected because it returns
summary bands only, whereas the recovery numbers need per-draw component
moments for the mixture quantiles; that helper's total-variance and
latent-band conventions are followed and cited, not copied, and this script
makes a single consistent pass over the package decomposition. A mean ± 2 sd
band was rejected in favour of exact mixture quantiles. Random subsampling of
draws (the `np.random.choice` convention in the older helpers) was rejected in
favour of using all 1,000 draws, which removes an RNG dependence from the
reported numbers. Any Mauna Loa material was excluded by scope.

**Result:** First run kept; no iteration toward better numbers. Diagnostics
clean: 0 divergences, rank-normalized R-hat at most 1.0025, bulk ESS at least
602.4, tail ESS at least 502.6, tree-depth saturation rate 0.0, and 1,000 of
1,000 decompositions successful.

Recovery, with uncertainty layers, all in
`runs/toy_debias_demo/results.json`:
- bias-slope posterior mean 0.197, sd 0.072, 95% central interval
  [0.033, 0.323], which CONTAINS the generating 0.250 (posterior layer);
- RMSE against sin(x) on a 201-point grid inside the training span: composite
  posterior mean 1.430, debiased posterior mean 0.403, a reduction of 1.028 or
  71.9% (between-chain scatter 1.431/1.430 and 0.403/0.402);
- coverage of sin(x) by the debiased 95% band 0.866 (174 of 201 grid points),
  i.e. mild UNDERCOVERAGE, reported as it came out;
- scale references on the same grid: the drift 0.25x has RMS 1.451 and sin(x)
  has RMS 0.690, so the composite arm's discrepancy essentially reproduces the
  drift it was fitted to include, and the residual 0.403 is not negligible;
- mean band width 1.836 debiased versus 1.032 composite, i.e. the data
  constrain the SUM of the components far more tightly than either component
  alone. That number is what makes the section 8.5 uncertainty-floor sentence
  concrete, and section 7 now states the connection.

Determinism: byte-stable. Two consecutive runs reproduced BOTH `results.json`
and `debias_figure.png` byte for byte (results.json sha256
`e73f067276e7bd61026dbcde835d9e1461d5dd604a448cd5176e3b0687eaaa3c`, figure
sha256 `6ebd195f8bf9c224361853ba16b36af1f2e4010ffec912fb6bb44766b5e58907`) on
python 3.13.11 / torch 2.10.0 / numpy 1.26.4 / arviz 0.23.4. Byte-stability is
asserted within one environment only; across environments the README pins
numeric tolerances (recovery 1e-6 absolute, R-hat 1e-3, ESS 1 effective draw).
Rerun: `python experiments/toy_debias_demo.py` from the repository root, about
one minute on a laptop CPU, no network and no new dependencies. Figure size
264 KiB, well under the 2 MB limit.

Scope, stated in the section, the run README, and `results.json`
(`scope.mauna_loa_contact = "none"`): synthetic toy only; no Mauna Loa script
or artifact is imported, executed, or cited, so the D58 preregistration
boundary is untouched, and no real-data number is reported or forecast.
KERNEL-LABELING CAVEAT: identifying the linear component as bias is a modeling
CHOICE, licensed here only because the generator produced the drift. The
decomposition will split an additive posterior whichever way the labels are
assigned, so in an application the analyst must justify the labeling on
substantive grounds before a marginalization result means what its name
suggests.

**Status:** Section 7 fleshed out at `docs/paper-sie-jmp/07-debias-bridge.md`
with the one figure and evidence-tier footnotes; the derived
`docs/paper-sie-jmp/tex/sections/07-debias.tex` still holds the old stub text
and needs regeneration through `docs/paper-sie-jmp/build_tex.py` at assembly
time. No review round has been run on this case yet (HANDOFF §4 protocol not
yet applied to Case E). No git mutation was performed by the implementing
session.
```

## runs/toy_debias_demo/results.json as committed
```json
{
  "case": "E",
  "config": {
    "band_convention": "latent function, no observation noise added",
    "components": {
      "bias_candidate": "bias_linear",
      "truth_candidate": "unbiased_se"
    },
    "credible_mass": 0.95,
    "decomposition_jitter": 0.0001,
    "grid": {
      "hi": 10.0,
      "lo": -10.0,
      "n": 201,
      "spacing": "equally spaced, inside the training span"
    },
    "init_strategy": "init_to_map: both chains start at the same MAP point, so R-hat is within-mode evidence about mixing around the optimizer's mode, not between-mode agreement from dispersed starts (the toy hyperparameter posterior is multi-basin, D12)",
    "interval_method": "exact central interval of the equally weighted Gaussian mixture over retained draws, by CDF bisection",
    "map_iters": 500,
    "map_lr": 0.05,
    "map_point": {
      "linear_variance": 0.018307932327009557,
      "noise_variance": 0.06186742021222304,
      "se_lengthscale": 1.4629304147814763,
      "se_outputscale": 0.7138687168157818
    },
    "map_seed": 42,
    "prior_equivalent_to": "experiments/prior_sensitivity_study.py STUDY_CONFIGS['toy_elicited']",
    "prior_key": "toy_elicited_n20",
    "prior_parameters": {
      "linear_variance_prior": [
        "lognormal",
        -3.2188758248682006,
        1.5
      ],
      "noise_prior": [
        "lognormal",
        -1.2039728043259361,
        1.0
      ],
      "se_lengthscale_prior": [
        "lognormal",
        1.5040773967762742,
        0.9
      ],
      "se_outputscale_prior": [
        "lognormal",
        0.4054651081081644,
        1.0
      ]
    }
  },
  "data": {
    "bias_process": "0.25 * x",
    "bias_slope": 0.25,
    "generator": "bistar_gp.generate_toy_data() at defaults",
    "n_points": 20,
    "noise_std": 0.5,
    "seed": 42,
    "true_process": "sin(x)",
    "x_range": [
      -10.0,
      10.0
    ]
  },
  "decomposition": {
    "linear_component_structure_check": {
      "max_abs_deviation_from_exact_linearity": 4.4564352208453784e-13,
      "max_abs_deviation_from_rank_one_variance": 1.89605275924265e-15,
      "note": "gpytorch LinearKernel gives k(x,x') = v x x', so the component posterior mean must be exactly linear and its covariance exactly Var(b|theta) x x^T; these are the worst observed deviations across retained draws, and they license reading the slope moments off the decomposition output"
    },
    "machinery": "bistar_gp.decompose.decompose_additive_gp for components; bistar_gp.decompose.decompose_component on the summed kernel blocks for the joint posterior",
    "n_attempted": 1000,
    "n_failed": 0,
    "n_ok": 1000
  },
  "environment": {
    "arviz": "0.23.4",
    "numpy": "1.26.4",
    "python": "3.13.11",
    "torch": "2.10.0"
  },
  "recovery": {
    "bias_process_grid_rms": 1.4505745987941008,
    "composite_band_mean_width": 1.0319893656930352,
    "coverage": 0.8656716417910447,
    "coverage_caveat": "a pointwise summary over a correlated grid, not a calibration test with independent trials: neighboring grid points share nearly the same posterior, so the effective number of checks is far below 201",
    "coverage_nominal": 0.95,
    "coverage_points_covered": 174,
    "coverage_points_total": 201,
    "debias_improves_rmse": true,
    "debiased_band_mean_width": 1.8355730651608624,
    "generating_slope": 0.25,
    "rmse_composite": 1.430390061349473,
    "rmse_composite_by_chain": [
      1.430902946911567,
      1.429886916216616
    ],
    "rmse_debiased": 0.4025181154080362,
    "rmse_debiased_by_chain": [
      0.4034854430683031,
      0.4015943687218727
    ],
    "rmse_reduction": 1.027871945941437,
    "rmse_reduction_pct": 71.85955591523836,
    "slope": {
      "hi": 0.3229918220752096,
      "lo": 0.03275525741517342,
      "mean": 0.19749504453874142,
      "sd": 0.07214240107691616
    },
    "slope_interval_contains_generating": true,
    "slope_minus_generating": -0.05250495546125858,
    "true_process_grid_rms": 0.6901815271460361
  },
  "sampler": {
    "acceptance_rate_by_chain": [
      0.992,
      0.998
    ],
    "arviz_version": "0.23.4",
    "chain_seeds": [
      20260813,
      20260814
    ],
    "chains": 2,
    "depth_saturated_draws": 0,
    "depth_saturation_rate": 0.0,
    "divergences_by_chain": [
      0,
      0
    ],
    "divergences_total": 0,
    "draws_per_chain": 500,
    "draws_total": 1000,
    "ess_bulk": {
      "covar_module.kernels.0.base_kernel.lengthscale_prior": 602.405863421313,
      "covar_module.kernels.0.outputscale_prior": 649.0183288902416,
      "covar_module.kernels.1.variance_prior": 849.6635487695786,
      "likelihood.noise_covar.noise_prior": 776.7104612764434
    },
    "ess_bulk_min": 602.405863421313,
    "ess_tail": {
      "covar_module.kernels.0.base_kernel.lengthscale_prior": 502.6181016635812,
      "covar_module.kernels.0.outputscale_prior": 662.5058914752248,
      "covar_module.kernels.1.variance_prior": 627.841729671124,
      "likelihood.noise_covar.noise_prior": 578.2567932948699
    },
    "ess_tail_min": 502.6181016635812,
    "final_step_size_by_chain": [
      0.47063635349887833,
      0.42284941431499096
    ],
    "initial_step_size": 0.1,
    "max_tree_depth": 8,
    "r_hat_max": 1.002489522142068,
    "r_hat_rank_normalized": {
      "covar_module.kernels.0.base_kernel.lengthscale_prior": 1.0011566039709776,
      "covar_module.kernels.0.outputscale_prior": 1.0012317832909678,
      "covar_module.kernels.1.variance_prior": 1.002489522142068,
      "likelihood.noise_covar.noise_prior": 1.0012107890929356
    },
    "sampler": "nuts_e1",
    "step_size_adapted": true,
    "target_accept_prob": 0.8,
    "warmup_per_chain": 500
  },
  "scope": {
    "kernel_labeling": "the linear component is labeled bias and the SE component truth; licensed here because generate_toy_data constructed the data that way, and a modeling choice the analyst must justify elsewhere",
    "mauna_loa_contact": "none",
    "synthetic_only": true
  },
  "title": "Toy debias demonstration: evaluation and mitigation from one posterior"
}
```

## runs/toy_debias_demo/README.md as committed
```markdown
# Case E — toy debias demonstration

Bias mitigation by marginalization on the synthetic toy whose bias
process is known by construction. Generated by
`experiments/toy_debias_demo.py`; consumed by manuscript section 7
(`docs/paper-sie-jmp/07-debias-bridge.md`) and logged as
`Notes/DECISIONS.md` D67.

## Rerun

```bash
python experiments/toy_debias_demo.py
```

From the repository root. No network access and no new dependencies;
local CPU, single process, about one minute.

## Scope note — no Mauna Loa

Synthetic toy only. This script imports, executes, and cites no Mauna
Loa script or artifact, so the D58 preregistration boundary is not
touched. The real-data development of the debiasing program, including
the preregistered study, belongs to the companion line; thesis ch. 5 is
the source of the program. Nothing here forecasts those numbers.

Identifying the linear component as bias is a modeling CHOICE. It is
licensed here because `generate_toy_data` built the data that way
(`bias_slope=0.25`); in an application the analyst must justify the
kernel labeling on substantive grounds.

## Configuration

- Data: `generate_toy_data()` defaults, N=20, seed 42, noise sd 0.5, bias slope 0.25.
- Prior: `PRIOR_CONFIGS["toy_elicited_n20"]`, identical to the `toy_elicited` entry of `experiments/prior_sensitivity_study.py`.
- Sampler: `nuts_e1` via `bistar_gp.fit.fit_hmc` (the corrected NUTS path; the pre-correction Pyro setup is not used).
- 2 chains, seeds [20260813, 20260814], 500 warmup and 500 retained draws each (1000 pooled).
- `target_accept_prob` 0.8, `max_tree_depth` 8, initial step size 0.1 with adaptation.
- Init: BOTH chains start at the SAME MAP point (`fit_map`, torch seed 42, 500 iterations, lr 0.05). R-hat below is therefore WITHIN-MODE evidence: it reports mixing around the mode the optimizer selected, not agreement between dispersed starts. The toy hyperparameter posterior is known to be multi-basin (D12).
- Evaluation grid: 201 equally spaced points on [-10.0, 10.0], inside the training span, so no extrapolation enters the numbers.
- Bands: latent-function, no observation noise; intervals are exact 95% central intervals of the draw mixture, obtained by CDF bisection.

## Diagnostics

- Divergences: 0 (by chain [0, 0]).
- Rank-normalized R-hat, maximum over sites: 1.0025.
- Bulk ESS minimum 602.4; tail ESS minimum 502.6.
- Tree-depth saturation rate: 0.0000.
- Decomposition: 1000 of 1000 draws succeeded, 0 failed.

## Recovery

| quantity | value | uncertainty layer |
|---|---:|---|
| bias slope posterior mean | 0.197 | posterior sd 0.072; 95% CI [0.033, 0.323] |
| generating bias slope | 0.250 | known by construction |
| RMSE, composite mean vs sin x | 1.430 | per-chain 1.431 and 1.430 |
| RMSE, debiased mean vs sin x | 0.403 | per-chain 0.403 and 0.402 |
| RMSE reduction | 1.028 | 71.9% of the composite RMSE |
| coverage of sin x by the debiased band | 0.866 | 174 of 201 grid points, nominal 0.95 |
| mean width, debiased band | 1.836 | composite band 1.032 on the same grid |

Scale references on the same grid, both known by construction: the bias
process 0.25x has RMS 1.451 and the true
process sin x has RMS 0.690. The composite
RMSE therefore reproduces the drift's own magnitude, as it must, since
the composite describes the observed data and the observed data carry
the drift.

Coverage caveat: a pointwise summary over a correlated grid, not a calibration test with independent trials: neighboring grid points share nearly the same posterior, so the effective number of checks is far below 201.

## Reproducibility

- Determinism: every random source is seeded (data 42, MAP 42, chains [20260813, 20260814]); the decomposition pass and the interval bisection draw no random numbers at
  all, so nothing downstream of the sampler can drift.
- Verified: on the environment stamped in `results.json` (`environment`),
  two consecutive runs reproduced BOTH `results.json` and
  `debias_figure.png` byte for byte. Byte-stability is asserted only
  within one environment.
- Across environments compare numerically instead, at these tolerances:
  recovery values to 1e-6 absolute, R-hat to 1e-3, ESS to 1 effective
  draw. A torch or pyro version change moves the draws and voids the
  byte comparison without voiding the substantive numbers.

## Files

- `results.json` — configuration, seeds, sampler settings and init,
  diagnostics, decomposition counts, recovery numbers, grid definition.
- `debias_figure.png` — the three-panel figure carried by section 7.
- `README.md` — this file.
```

## experiments/toy_debias_demo.py as committed
```python
"""Case E — toy debias demonstration: evaluation and mitigation from one posterior.

The thesis (ch. 5) and the accepted proposal set two goals for the BI*/BMS*-GP
program: model evaluation through data priors, and bias mitigation. Manuscript
sections 1-6 and 8 deliver the first. This script supplies the second as a
small, self-contained demonstration on the synthetic toy whose bias process is
known by construction.

Data
----
`bistar_gp.generate_toy_data()` at its defaults: N=20, x on [-10, 10], seed 42,
observation noise 0.5, and y = sin(x) + 0.25 x + noise. The generator itself
names the linear term the bias (``bias_slope=0.25``; the returned info dict
carries ``true_signal``, ``bias``, and ``combined``). The demonstration treats
the sinusoid as the true process and the linear drift as the bias process.

Method
------
1. Fit the SE + linear additive GP under the `toy_elicited` prior
   (``PRIOR_CONFIGS["toy_elicited_n20"]``, byte-identical to the in-script
   `toy_elicited` entry of ``experiments/prior_sensitivity_study.py``).
   Hyperparameters are sampled on the CORRECTED NUTS path, ``bistar_gp.fit
   .fit_hmc`` (the ``nuts_e1`` sampler), in two seeded chains.
2. Decompose every retained draw's GP posterior additively with the package
   machinery ``bistar_gp.decompose.decompose_additive_gp``: the SE component is
   the truth candidate, the linear component the bias candidate. The joint
   posterior of f = f_SE + f_lin comes from ``decompose_component`` applied to
   the summed kernel blocks, so it retains the inter-component cross-covariance
   that a sum of component covariances would drop.
3. Debias by marginalization. Within a draw, the SE-component posterior that
   ``decompose_additive_gp`` returns is already marginal over the linear
   component (it is the marginal of the joint conditional Gaussian). Across
   draws, hyperparameters are marginalized by Monte Carlo. The debiased
   predictive is therefore the finite mixture over retained draws d of
   N(m_SE^d(x), v_SE^d(x)).

Band and interval conventions
-----------------------------
Bands are latent-function intervals with no observation noise added, matching
the convention documented in ``experiments/honest_band_decomposition.py`` and
used by the existing decomposition figures. Summary standard deviations use the
law of total variance,

    total_var(x) = mean_d[ within-draw var(x) ] + var_d[ within-draw mean(x) ],

and reported intervals are EXACT central intervals of the Gaussian mixture,
obtained by bisecting its CDF rather than by a mean +/- 2 sd approximation.
(That helper is read here for its convention only; it returns summary bands
alone, whereas the recovery numbers below need per-draw component moments, so
this script runs its own single pass over the package decomposition.)

Recovered bias slope
--------------------
gpytorch's ``LinearKernel`` has k(x, x') = v x x', so the linear component is
f_lin(x) = b x with b ~ N(0, v) a priori. Consequently the component posterior
mean is exactly linear in x and the component posterior covariance is exactly
the rank-one matrix Var(b | theta) x x^T. Both properties are verified
numerically for every draw and the worst deviations are reported in
``results.json``. The per-draw slope moments are read off the decomposition
output as

    E[b | y, theta] = (m_lin(x_max) - m_lin(x_min)) / (x_max - x_min),
    Var(b | y, theta) = cov_lin(x_ref, x_ref) / x_ref^2,

so no separate formula is introduced: the slope posterior is a functional of
the same component decomposition the figure plots.

Scope
-----
Synthetic toy only. NO Mauna Loa material of any kind is imported, executed, or
cited: the D58 preregistration boundary stands and the real-data development
belongs to the companion line. Identifying "bias" with the linear component is
a modeling CHOICE, licensed here because the generator built the data that way.

Rerun (from the repository root):

    python experiments/toy_debias_demo.py

Outputs land in ``runs/toy_debias_demo/``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import warnings
from pathlib import Path

import numpy as np
import torch
from scipy.special import ndtr

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from bistar_gp import build_model, generate_toy_data                # noqa: E402
from bistar_gp.config import (                                      # noqa: E402
    PRIOR_CONFIGS,
    build_kernels_from_config,
    build_likelihood_from_config,
)
from bistar_gp.decompose import (                                   # noqa: E402
    compute_cholesky,
    decompose_additive_gp,
    decompose_component,
)
from bistar_gp.fit import fit_hmc, fit_map                          # noqa: E402
from bistar_gp.model import apply_hp_value, select_hmc_sites        # noqa: E402

# ── Frozen configuration ─────────────────────────────────────────────────────

PRIOR_KEY = "toy_elicited_n20"          # == prior_sensitivity_study `toy_elicited`
MAP_SEED = 42                           # torch seed for the shared MAP init
MAP_ITERS = 500
MAP_LR = 0.05
CHAIN_SEEDS = (20260813, 20260814)      # one pyro seed per chain
N_WARMUP = 500                          # per chain
N_DRAWS = 500                           # retained per chain
MAX_TREE_DEPTH = 8
TARGET_ACCEPT = 0.8                     # fixed inside fit_hmc_e1
INIT_STEP_SIZE = 0.1                    # fixed inside fit_hmc_e1, then adapted
DECOMP_JITTER = 1e-4                    # matches the existing figure scripts

GRID_LO, GRID_HI, GRID_N = -10.0, 10.0, 201
CREDIBLE_MASS = 0.95
SLOPE_VAR_MIN_ABS_X = 1.0               # |x| floor for the rank-one variance read
BISECT_ITERS = 100

TRUTH_COMPONENT = "unbiased_se"         # truth candidate
BIAS_COMPONENT = "bias_linear"          # bias candidate

COLOR_PRIMARY = "#2E6FB8"               # posterior means and bands
COLOR_REFERENCE = "#C4356B"             # known generating curves
COLOR_BIAS = "#E08214"                  # bias-candidate component
COLOR_DATA = "#222222"


# ── Fitting ──────────────────────────────────────────────────────────────────


def _fresh_model(prior_config, x, y):
    kernels, names = build_kernels_from_config(prior_config)
    likelihood = build_likelihood_from_config(prior_config)
    model, likelihood = build_model(x, y, kernels, names, likelihood)
    return model, likelihood, names


def _map_fitted_model(prior_config, x, y):
    """A freshly built model driven to the same MAP point every time.

    Both chains start from this point, so R-hat below is WITHIN-MODE evidence:
    it reports mixing around the mode the MAP optimizer selected, not
    between-mode agreement from dispersed starts. The toy hyperparameter
    posterior is known to be multi-basin (D12), which is exactly why the
    disclosure matters.
    """
    model, likelihood, names = _fresh_model(prior_config, x, y)
    torch.manual_seed(MAP_SEED)
    fit_map(model, likelihood, x, y, n_iter=MAP_ITERS, lr=MAP_LR, verbose=False)
    return model, likelihood, names


def _map_point(model, likelihood):
    return {
        "se_lengthscale": float(model.kernel_components[0].base_kernel.lengthscale.item()),
        "se_outputscale": float(model.kernel_components[0].outputscale.item()),
        "linear_variance": float(model.kernel_components[1].variance.item()),
        "noise_variance": float(likelihood.noise.item()),
    }


def run_chains(prior_config, x, y, *, verbose):
    """One MAP-initialized nuts_e1 chain per seed; returns samples + diagnostics."""
    chain_samples, chain_diagnostics, map_points = [], [], []
    for seed in CHAIN_SEEDS:
        model, likelihood, _ = _map_fitted_model(prior_config, x, y)
        map_points.append(_map_point(model, likelihood))
        samples, diagnostics = fit_hmc(
            model, likelihood, x, y,
            n_samples=N_DRAWS, n_warmup=N_WARMUP, verbose=False, seed=seed,
            init_to_map=True, max_tree_depth=MAX_TREE_DEPTH,
            return_diagnostics=True,
        )
        chain_samples.append({k: np.asarray(v, dtype=float).reshape(-1)
                              for k, v in samples.items()})
        chain_diagnostics.append(diagnostics)
        if verbose:
            print(f"  chain seed {seed}: {N_DRAWS} draws, "
                  f"{len(diagnostics.divergence_draws[0])} divergences")
    if len({tuple(sorted(p.items())) for p in map_points}) != 1:
        raise RuntimeError("MAP init differed between chains; determinism broken")
    return chain_samples, chain_diagnostics, map_points[0]


def sampler_diagnostics_block(chain_samples, chain_diagnostics):
    """Rank-normalized R-hat and bulk/tail ESS across the seeded chains."""
    import arviz as az

    sites = list(chain_samples[0].keys())
    posterior = {site: np.stack([chain[site] for chain in chain_samples])
                 for site in sites}
    idata = az.from_dict(posterior=posterior)
    rhat = {s: float(np.asarray(az.rhat(idata, method="rank")[s])) for s in sites}
    ess_bulk = {s: float(np.asarray(az.ess(idata, method="bulk")[s])) for s in sites}
    ess_tail = {s: float(np.asarray(az.ess(idata, method="tail")[s])) for s in sites}

    cap = 2 ** MAX_TREE_DEPTH - 1
    saturated = sum(int(n >= cap)
                    for d in chain_diagnostics for chain in d.leapfrog_counts
                    for n in chain)
    n_leapfrog_draws = sum(len(chain)
                           for d in chain_diagnostics for chain in d.leapfrog_counts)
    return {
        "sampler": chain_diagnostics[0].sampler,
        "chains": len(chain_samples),
        "chain_seeds": list(CHAIN_SEEDS),
        "warmup_per_chain": N_WARMUP,
        "draws_per_chain": N_DRAWS,
        "draws_total": N_DRAWS * len(chain_samples),
        "target_accept_prob": TARGET_ACCEPT,
        "max_tree_depth": MAX_TREE_DEPTH,
        "initial_step_size": INIT_STEP_SIZE,
        "step_size_adapted": True,
        "final_step_size_by_chain": [
            None if d.step_size is None else float(d.step_size)
            for d in chain_diagnostics],
        "divergences_by_chain": [int(sum(len(c) for c in d.divergence_draws))
                                 for d in chain_diagnostics],
        "divergences_total": int(sum(len(c) for d in chain_diagnostics
                                     for c in d.divergence_draws)),
        "acceptance_rate_by_chain": [float(d.acceptance_rate[0])
                                     for d in chain_diagnostics],
        "depth_saturated_draws": saturated,
        "depth_saturation_rate": (saturated / n_leapfrog_draws
                                  if n_leapfrog_draws else None),
        "r_hat_rank_normalized": rhat,
        "r_hat_max": float(max(rhat.values())),
        "ess_bulk": ess_bulk,
        "ess_bulk_min": float(min(ess_bulk.values())),
        "ess_tail": ess_tail,
        "ess_tail_min": float(min(ess_tail.values())),
        "arviz_version": az.__version__,
    }


# ── Decomposition over draws ─────────────────────────────────────────────────


def decompose_draws(prior_config, x, y, x_grid, pooled_samples):
    """Per-draw component and joint posterior moments from the package machinery.

    Returns arrays of shape (n_ok, n_grid) for each component mean/variance and
    for the joint posterior, plus the per-draw bias-slope moments and the
    structure checks that license the slope read.
    """
    sites = select_hmc_sites(pooled_samples.keys())
    n_total = len(next(iter(pooled_samples.values())))
    xg = x_grid.numpy()
    span = xg[-1] - xg[0]
    var_idx = np.flatnonzero(np.abs(xg) >= SLOPE_VAR_MIN_ABS_X)

    comp_mean = {TRUTH_COMPONENT: [], BIAS_COMPONENT: []}
    comp_var = {TRUTH_COMPONENT: [], BIAS_COMPONENT: []}
    joint_mean, joint_var = [], []
    slope_mean, slope_var, chain_of_draw = [], [], []
    max_linearity_dev = 0.0
    max_rank_one_dev = 0.0
    n_fail = 0

    for i in range(n_total):
        kernels_i, names_i = build_kernels_from_config(prior_config)
        likelihood_i = build_likelihood_from_config(prior_config)
        model_i, likelihood_i = build_model(x, y, kernels_i, names_i, likelihood_i)
        for site in sites:
            apply_hp_value(model_i, likelihood_i, site, float(pooled_samples[site][i]))
        model_i.eval()
        likelihood_i.eval()
        noise_var = likelihood_i.noise.item()
        blocks = model_i.get_component_kernel_matrices(x, x_grid)

        with torch.no_grad():
            try:
                per_component = decompose_additive_gp(
                    [blocks[n]["XX"] for n in names_i],
                    [blocks[n]["XstarX"] for n in names_i],
                    [blocks[n]["XstarXstar"] for n in names_i],
                    [blocks[n]["XXstar"] for n in names_i],
                    noise_var, y, DECOMP_JITTER,
                )
                chol = compute_cholesky(
                    sum(blocks[n]["XX"] for n in names_i), noise_var, DECOMP_JITTER)
                f_mean, f_cov = decompose_component(
                    sum(blocks[n]["XstarX"] for n in names_i),
                    sum(blocks[n]["XstarXstar"] for n in names_i),
                    sum(blocks[n]["XXstar"] for n in names_i),
                    chol, y,
                )
            except RuntimeError:
                n_fail += 1
                continue

        moments = dict(zip(names_i, per_component))
        for name in (TRUTH_COMPONENT, BIAS_COMPONENT):
            m_i, c_i = moments[name]
            comp_mean[name].append(m_i.numpy())
            comp_var[name].append(np.clip(np.diag(c_i.numpy()), 0.0, None))

        m_lin = moments[BIAS_COMPONENT][0].numpy()
        c_lin = moments[BIAS_COMPONENT][1].numpy()
        b_hat = (m_lin[-1] - m_lin[0]) / span
        var_candidates = np.diag(c_lin)[var_idx] / xg[var_idx] ** 2
        b_var = float(var_candidates[-1])
        max_linearity_dev = max(max_linearity_dev,
                                float(np.max(np.abs(m_lin - b_hat * xg))))
        max_rank_one_dev = max(max_rank_one_dev,
                               float(np.max(np.abs(var_candidates - b_var))))
        slope_mean.append(float(b_hat))
        slope_var.append(max(b_var, 0.0))
        chain_of_draw.append(i // N_DRAWS)

        joint_mean.append(f_mean.numpy())
        joint_var.append(np.clip(np.diag(f_cov.numpy()), 0.0, None))

    n_ok = len(joint_mean)
    if n_ok == 0:
        raise RuntimeError("every draw failed the additive decomposition")

    return {
        "comp_mean": {k: np.stack(v) for k, v in comp_mean.items()},
        "comp_var": {k: np.stack(v) for k, v in comp_var.items()},
        "joint_mean": np.stack(joint_mean),
        "joint_var": np.stack(joint_var),
        "slope_mean": np.asarray(slope_mean),
        "slope_var": np.asarray(slope_var),
        "chain_of_draw": np.asarray(chain_of_draw),
        "n_attempted": n_total,
        "n_ok": n_ok,
        "n_failed": n_fail,
        "max_linearity_deviation": max_linearity_dev,
        "max_rank_one_variance_deviation": max_rank_one_dev,
    }


# ── Mixture summaries ────────────────────────────────────────────────────────


def total_variance_sd(mean_draws, var_draws):
    """Law-of-total-variance standard deviation across draws."""
    return np.sqrt(var_draws.mean(axis=0) + mean_draws.var(axis=0))


def mixture_central_interval(mean_draws, var_draws, mass=CREDIBLE_MASS):
    """Exact central interval of an equally weighted Gaussian mixture.

    ``mean_draws`` and ``var_draws`` have shape (n_draws, n_points); the return
    is (lo, hi), each of shape (n_points,). Quantiles come from bisecting the
    mixture CDF, so the interval is not a Gaussian approximation to the mixture.
    """
    sd = np.sqrt(np.clip(var_draws, 1e-24, None))
    tail = (1.0 - mass) / 2.0

    def quantile(p):
        lo = (mean_draws - 12.0 * sd).min(axis=0)
        hi = (mean_draws + 12.0 * sd).max(axis=0)
        for _ in range(BISECT_ITERS):
            mid = 0.5 * (lo + hi)
            cdf = ndtr((mid[None, :] - mean_draws) / sd).mean(axis=0)
            below = cdf < p
            lo = np.where(below, mid, lo)
            hi = np.where(below, hi, mid)
        return 0.5 * (lo + hi)

    return quantile(tail), quantile(1.0 - tail)


def rmse(values, target):
    return float(np.sqrt(np.mean((values - target) ** 2)))


# ── Figure ───────────────────────────────────────────────────────────────────


def make_figure(path, xg, x_np, y_np, truth, summary):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 3, figsize=(15.0, 4.6), sharex=True)

    ax = axes[0]
    ax.fill_between(xg, summary["joint_lo"], summary["joint_hi"],
                    color=COLOR_PRIMARY, alpha=0.20, linewidth=0,
                    label="95% central interval")
    ax.plot(xg, summary["joint_mean"], color=COLOR_PRIMARY, lw=2.0,
            label="composite posterior mean")
    ax.plot(xg, truth["combined"], color=COLOR_REFERENCE, lw=1.6, ls="--",
            label=r"generating $\sin x + 0.25x$")
    ax.scatter(x_np, y_np, marker="x", s=42, color=COLOR_DATA, lw=1.4,
               label="observed data (N=20)")
    ax.set_title("(a) Composite posterior predictive", fontsize=11)
    ax.set_ylabel("y", fontsize=10)

    ax = axes[1]
    ax.fill_between(xg, summary["truth_lo"], summary["truth_hi"],
                    color=COLOR_PRIMARY, alpha=0.20, linewidth=0)
    ax.plot(xg, summary["truth_mean"], color=COLOR_PRIMARY, lw=2.0,
            label="SE component (truth candidate)")
    ax.fill_between(xg, summary["bias_lo"], summary["bias_hi"],
                    color=COLOR_BIAS, alpha=0.22, linewidth=0)
    ax.plot(xg, summary["bias_mean"], color=COLOR_BIAS, lw=2.0,
            label="linear component (bias candidate)")
    ax.plot(xg, truth["true_signal"], color=COLOR_REFERENCE, lw=1.5, ls="--",
            label=r"generating $\sin x$")
    ax.plot(xg, truth["bias"], color=COLOR_REFERENCE, lw=1.5, ls=":",
            label=r"generating $0.25x$")
    ax.set_title("(b) Labeled components, 95% central intervals", fontsize=11)
    slope = summary["slope"]
    ax.annotate(
        "recovered slope {:.3f} (sd {:.3f})\n95% CI [{:.3f}, {:.3f}]"
        "\ngenerating value {:.3f}".format(
            slope["mean"], slope["sd"], slope["lo"], slope["hi"],
            summary["generating_slope"]),
        xy=(0.03, 0.97), xycoords="axes fraction", va="top", ha="left",
        fontsize=8.5,
        bbox=dict(boxstyle="round,pad=0.35", facecolor="white",
                  edgecolor=COLOR_BIAS, alpha=0.9))

    ax = axes[2]
    ax.fill_between(xg, summary["truth_lo"], summary["truth_hi"],
                    color=COLOR_PRIMARY, alpha=0.20, linewidth=0,
                    label="95% central interval")
    ax.plot(xg, summary["truth_mean"], color=COLOR_PRIMARY, lw=2.0,
            label="debiased posterior mean")
    ax.plot(xg, truth["true_signal"], color=COLOR_REFERENCE, lw=1.6, ls="--",
            label=r"known true process $\sin x$")
    ax.set_title("(c) Debiased predictive against the known truth", fontsize=11)
    ax.annotate(
        "RMSE vs sin x\ncomposite mean {:.3f}\ndebiased mean {:.3f}"
        "\ncoverage of sin x {:.3f}".format(
            summary["rmse_composite"], summary["rmse_debiased"],
            summary["coverage"]),
        xy=(0.03, 0.97), xycoords="axes fraction", va="top", ha="left",
        fontsize=8.5,
        bbox=dict(boxstyle="round,pad=0.35", facecolor="white",
                  edgecolor=COLOR_PRIMARY, alpha=0.9))

    for ax in axes:
        ax.set_xlabel("x", fontsize=10)
        ax.legend(fontsize=7.6, loc="lower right", framealpha=0.9)
        ax.grid(alpha=0.18, lw=0.6)

    fig.suptitle(
        "Debiasing by marginalization on the N=20 toy: one posterior, "
        "three readings", fontsize=12.5)
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


# ── Artifacts ────────────────────────────────────────────────────────────────


def write_readme(path, results):
    rec = results["recovery"]
    diag = results["sampler"]
    dec = results["decomposition"]
    lines = [
        "# Case E — toy debias demonstration",
        "",
        "Bias mitigation by marginalization on the synthetic toy whose bias",
        "process is known by construction. Generated by",
        "`experiments/toy_debias_demo.py`; consumed by manuscript section 7",
        "(`docs/paper-sie-jmp/07-debias-bridge.md`) and logged as",
        "`Notes/DECISIONS.md` D67.",
        "",
        "## Rerun",
        "",
        "```bash",
        "python experiments/toy_debias_demo.py",
        "```",
        "",
        "From the repository root. No network access and no new dependencies;",
        "local CPU, single process, about one minute.",
        "",
        "## Scope note — no Mauna Loa",
        "",
        "Synthetic toy only. This script imports, executes, and cites no Mauna",
        "Loa script or artifact, so the D58 preregistration boundary is not",
        "touched. The real-data development of the debiasing program, including",
        "the preregistered study, belongs to the companion line; thesis ch. 5 is",
        "the source of the program. Nothing here forecasts those numbers.",
        "",
        "Identifying the linear component as bias is a modeling CHOICE. It is",
        "licensed here because `generate_toy_data` built the data that way",
        "(`bias_slope=0.25`); in an application the analyst must justify the",
        "kernel labeling on substantive grounds.",
        "",
        "## Configuration",
        "",
        f"- Data: `generate_toy_data()` defaults, N={results['data']['n_points']}, "
        f"seed {results['data']['seed']}, noise sd {results['data']['noise_std']}, "
        f"bias slope {results['data']['bias_slope']}.",
        f"- Prior: `PRIOR_CONFIGS[\"{results['config']['prior_key']}\"]`, identical to "
        "the `toy_elicited` entry of `experiments/prior_sensitivity_study.py`.",
        f"- Sampler: `{diag['sampler']}` via `bistar_gp.fit.fit_hmc` (the corrected "
        "NUTS path; the pre-correction Pyro setup is not used).",
        f"- {diag['chains']} chains, seeds {diag['chain_seeds']}, "
        f"{diag['warmup_per_chain']} warmup and {diag['draws_per_chain']} retained "
        f"draws each ({diag['draws_total']} pooled).",
        f"- `target_accept_prob` {diag['target_accept_prob']}, `max_tree_depth` "
        f"{diag['max_tree_depth']}, initial step size {diag['initial_step_size']} "
        "with adaptation.",
        f"- Init: BOTH chains start at the SAME MAP point "
        f"(`fit_map`, torch seed {results['config']['map_seed']}, "
        f"{results['config']['map_iters']} iterations, lr {results['config']['map_lr']}). "
        "R-hat below is therefore WITHIN-MODE evidence: it reports mixing around "
        "the mode the optimizer selected, not agreement between dispersed starts. "
        "The toy hyperparameter posterior is known to be multi-basin (D12).",
        f"- Evaluation grid: {results['config']['grid']['n']} equally spaced points "
        f"on [{results['config']['grid']['lo']}, {results['config']['grid']['hi']}], "
        "inside the training span, so no extrapolation enters the numbers.",
        f"- Bands: latent-function, no observation noise; intervals are exact "
        f"{int(100 * results['config']['credible_mass'])}% central intervals of the "
        "draw mixture, obtained by CDF bisection.",
        "",
        "## Diagnostics",
        "",
        f"- Divergences: {diag['divergences_total']} "
        f"(by chain {diag['divergences_by_chain']}).",
        f"- Rank-normalized R-hat, maximum over sites: {diag['r_hat_max']:.4f}.",
        f"- Bulk ESS minimum {diag['ess_bulk_min']:.1f}; "
        f"tail ESS minimum {diag['ess_tail_min']:.1f}.",
        f"- Tree-depth saturation rate: {diag['depth_saturation_rate']:.4f}.",
        f"- Decomposition: {dec['n_ok']} of {dec['n_attempted']} draws succeeded, "
        f"{dec['n_failed']} failed.",
        "",
        "## Recovery",
        "",
        "| quantity | value | uncertainty layer |",
        "|---|---:|---|",
        f"| bias slope posterior mean | {rec['slope']['mean']:.3f} | "
        f"posterior sd {rec['slope']['sd']:.3f}; 95% CI "
        f"[{rec['slope']['lo']:.3f}, {rec['slope']['hi']:.3f}] |",
        f"| generating bias slope | {rec['generating_slope']:.3f} | known by "
        "construction |",
        f"| RMSE, composite mean vs sin x | {rec['rmse_composite']:.3f} | "
        f"per-chain {rec['rmse_composite_by_chain'][0]:.3f} and "
        f"{rec['rmse_composite_by_chain'][1]:.3f} |",
        f"| RMSE, debiased mean vs sin x | {rec['rmse_debiased']:.3f} | "
        f"per-chain {rec['rmse_debiased_by_chain'][0]:.3f} and "
        f"{rec['rmse_debiased_by_chain'][1]:.3f} |",
        f"| RMSE reduction | {rec['rmse_reduction']:.3f} | "
        f"{rec['rmse_reduction_pct']:.1f}% of the composite RMSE |",
        f"| coverage of sin x by the debiased band | {rec['coverage']:.3f} | "
        f"{rec['coverage_points_covered']} of {rec['coverage_points_total']} grid "
        f"points, nominal {rec['coverage_nominal']:.2f} |",
        f"| mean width, debiased band | {rec['debiased_band_mean_width']:.3f} | "
        f"composite band {rec['composite_band_mean_width']:.3f} on the same grid |",
        "",
        "Scale references on the same grid, both known by construction: the bias",
        f"process 0.25x has RMS {rec['bias_process_grid_rms']:.3f} and the true",
        f"process sin x has RMS {rec['true_process_grid_rms']:.3f}. The composite",
        "RMSE therefore reproduces the drift's own magnitude, as it must, since",
        "the composite describes the observed data and the observed data carry",
        "the drift.",
        "",
        f"Coverage caveat: {rec['coverage_caveat']}.",
        "",
        "## Reproducibility",
        "",
        f"- Determinism: every random source is seeded (data {results['data']['seed']}, "
        f"MAP {results['config']['map_seed']}, chains {diag['chain_seeds']}); the "
        "decomposition pass and the interval bisection draw no random numbers at",
        "  all, so nothing downstream of the sampler can drift.",
        "- Verified: on the environment stamped in `results.json` (`environment`),",
        "  two consecutive runs reproduced BOTH `results.json` and",
        "  `debias_figure.png` byte for byte. Byte-stability is asserted only",
        "  within one environment.",
        "- Across environments compare numerically instead, at these tolerances:",
        "  recovery values to 1e-6 absolute, R-hat to 1e-3, ESS to 1 effective",
        "  draw. A torch or pyro version change moves the draws and voids the",
        "  byte comparison without voiding the substantive numbers.",
        "",
        "## Files",
        "",
        "- `results.json` — configuration, seeds, sampler settings and init,",
        "  diagnostics, decomposition counts, recovery numbers, grid definition.",
        "- `debias_figure.png` — the three-panel figure carried by section 7.",
        "- `README.md` — this file.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


# ── Driver ───────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default=str(REPO_ROOT / "runs" / "toy_debias_demo"),
                        help="output directory (default runs/toy_debias_demo)")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    verbose = not args.quiet

    warnings.filterwarnings("ignore", module="linear_operator")
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    prior_config = PRIOR_CONFIGS[PRIOR_KEY]
    x, y, info = generate_toy_data()
    x_grid = torch.linspace(GRID_LO, GRID_HI, GRID_N).double()
    xg = x_grid.numpy()
    truth = {
        "true_signal": np.sin(xg),
        "bias": float(info["bias_slope"]) * xg,
        "combined": np.sin(xg) + float(info["bias_slope"]) * xg,
    }

    if verbose:
        print(f"Case E toy debias demo — N={len(x)}, prior {PRIOR_KEY}")
        print("Sampling hyperparameters on the corrected NUTS path (nuts_e1)...")
    chain_samples, chain_diagnostics, map_point = run_chains(
        prior_config, x, y, verbose=verbose)
    diag = sampler_diagnostics_block(chain_samples, chain_diagnostics)

    pooled = {site: np.concatenate([chain[site] for chain in chain_samples])
              for site in chain_samples[0]}

    if verbose:
        print(f"Decomposing {diag['draws_total']} draws with the package "
              "additive-kernel machinery...")
    dec = decompose_draws(prior_config, x, y, x_grid, pooled)

    truth_mean_draws = dec["comp_mean"][TRUTH_COMPONENT]
    truth_var_draws = dec["comp_var"][TRUTH_COMPONENT]
    bias_mean_draws = dec["comp_mean"][BIAS_COMPONENT]
    bias_var_draws = dec["comp_var"][BIAS_COMPONENT]

    truth_mean = truth_mean_draws.mean(axis=0)
    bias_mean = bias_mean_draws.mean(axis=0)
    joint_mean = dec["joint_mean"].mean(axis=0)

    truth_lo, truth_hi = mixture_central_interval(truth_mean_draws, truth_var_draws)
    bias_lo, bias_hi = mixture_central_interval(bias_mean_draws, bias_var_draws)
    joint_lo, joint_hi = mixture_central_interval(dec["joint_mean"], dec["joint_var"])

    slope_lo, slope_hi = mixture_central_interval(
        dec["slope_mean"][:, None], dec["slope_var"][:, None])
    slope = {
        "mean": float(dec["slope_mean"].mean()),
        "sd": float(total_variance_sd(dec["slope_mean"][:, None],
                                      dec["slope_var"][:, None])[0]),
        "lo": float(slope_lo[0]),
        "hi": float(slope_hi[0]),
    }

    sin_grid = truth["true_signal"]
    rmse_debiased = rmse(truth_mean, sin_grid)
    rmse_composite = rmse(joint_mean, sin_grid)
    chain_ids = dec["chain_of_draw"]
    rmse_debiased_by_chain, rmse_composite_by_chain = [], []
    for c in range(diag["chains"]):
        mask = chain_ids == c
        rmse_debiased_by_chain.append(
            rmse(truth_mean_draws[mask].mean(axis=0), sin_grid))
        rmse_composite_by_chain.append(
            rmse(dec["joint_mean"][mask].mean(axis=0), sin_grid))

    covered = (sin_grid >= truth_lo) & (sin_grid <= truth_hi)
    coverage = float(covered.mean())

    recovery = {
        "generating_slope": float(info["bias_slope"]),
        "slope": slope,
        "slope_minus_generating": float(slope["mean"] - float(info["bias_slope"])),
        "slope_interval_contains_generating": bool(
            slope["lo"] <= float(info["bias_slope"]) <= slope["hi"]),
        "rmse_composite": rmse_composite,
        "rmse_debiased": rmse_debiased,
        "rmse_reduction": float(rmse_composite - rmse_debiased),
        "rmse_reduction_pct": float(
            100.0 * (rmse_composite - rmse_debiased) / rmse_composite),
        "rmse_composite_by_chain": rmse_composite_by_chain,
        "rmse_debiased_by_chain": rmse_debiased_by_chain,
        "debias_improves_rmse": bool(rmse_debiased < rmse_composite),
        "coverage": coverage,
        "coverage_nominal": CREDIBLE_MASS,
        "coverage_points_covered": int(covered.sum()),
        "coverage_points_total": int(covered.size),
        "coverage_caveat": (
            "a pointwise summary over a correlated grid, not a calibration test "
            "with independent trials: neighboring grid points share nearly the "
            "same posterior, so the effective number of checks is far below "
            f"{int(covered.size)}"),
        "debiased_band_mean_width": float(np.mean(truth_hi - truth_lo)),
        "composite_band_mean_width": float(np.mean(joint_hi - joint_lo)),
        "bias_process_grid_rms": rmse(truth["bias"], 0.0),
        "true_process_grid_rms": rmse(sin_grid, 0.0),
    }

    summary = {
        "joint_mean": joint_mean, "joint_lo": joint_lo, "joint_hi": joint_hi,
        "truth_mean": truth_mean, "truth_lo": truth_lo, "truth_hi": truth_hi,
        "bias_mean": bias_mean, "bias_lo": bias_lo, "bias_hi": bias_hi,
        "slope": slope, "generating_slope": float(info["bias_slope"]),
        "rmse_composite": rmse_composite, "rmse_debiased": rmse_debiased,
        "coverage": coverage,
    }
    figure_path = out_dir / "debias_figure.png"
    make_figure(figure_path, xg, x.numpy(), y.numpy(), truth, summary)

    results = {
        "case": "E",
        "title": "Toy debias demonstration: evaluation and mitigation from one posterior",
        "scope": {
            "synthetic_only": True,
            "mauna_loa_contact": "none",
            "kernel_labeling": (
                "the linear component is labeled bias and the SE component truth; "
                "licensed here because generate_toy_data constructed the data that "
                "way, and a modeling choice the analyst must justify elsewhere"),
        },
        "data": {
            "generator": "bistar_gp.generate_toy_data() at defaults",
            "n_points": int(len(x)),
            "seed": 42,
            "x_range": [-10.0, 10.0],
            "noise_std": float(info["noise_std"]),
            "bias_slope": float(info["bias_slope"]),
            "true_process": "sin(x)",
            "bias_process": "0.25 * x",
        },
        "config": {
            "prior_key": PRIOR_KEY,
            "prior_equivalent_to": (
                "experiments/prior_sensitivity_study.py STUDY_CONFIGS['toy_elicited']"),
            "prior_parameters": {
                "se_lengthscale_prior": list(prior_config.se_lengthscale_prior),
                "se_outputscale_prior": list(prior_config.se_outputscale_prior),
                "linear_variance_prior": list(prior_config.linear_variance_prior),
                "noise_prior": list(prior_config.noise_prior),
            },
            "components": {"truth_candidate": TRUTH_COMPONENT,
                           "bias_candidate": BIAS_COMPONENT},
            "map_seed": MAP_SEED,
            "map_iters": MAP_ITERS,
            "map_lr": MAP_LR,
            "init_strategy": (
                "init_to_map: both chains start at the same MAP point, so R-hat is "
                "within-mode evidence about mixing around the optimizer's mode, not "
                "between-mode agreement from dispersed starts (the toy "
                "hyperparameter posterior is multi-basin, D12)"),
            "map_point": map_point,
            "grid": {"lo": GRID_LO, "hi": GRID_HI, "n": GRID_N,
                     "spacing": "equally spaced, inside the training span"},
            "credible_mass": CREDIBLE_MASS,
            "interval_method": (
                "exact central interval of the equally weighted Gaussian mixture "
                "over retained draws, by CDF bisection"),
            "band_convention": "latent function, no observation noise added",
            "decomposition_jitter": DECOMP_JITTER,
        },
        "sampler": diag,
        "decomposition": {
            "machinery": (
                "bistar_gp.decompose.decompose_additive_gp for components; "
                "bistar_gp.decompose.decompose_component on the summed kernel "
                "blocks for the joint posterior"),
            "n_attempted": dec["n_attempted"],
            "n_ok": dec["n_ok"],
            "n_failed": dec["n_failed"],
            "linear_component_structure_check": {
                "max_abs_deviation_from_exact_linearity":
                    dec["max_linearity_deviation"],
                "max_abs_deviation_from_rank_one_variance":
                    dec["max_rank_one_variance_deviation"],
                "note": (
                    "gpytorch LinearKernel gives k(x,x') = v x x', so the component "
                    "posterior mean must be exactly linear and its covariance "
                    "exactly Var(b|theta) x x^T; these are the worst observed "
                    "deviations across retained draws, and they license reading the "
                    "slope moments off the decomposition output"),
            },
        },
        "recovery": recovery,
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "torch": torch.__version__,
            "arviz": diag["arviz_version"],
        },
    }

    results_path = out_dir / "results.json"
    payload = json.dumps(results, indent=2, sort_keys=True) + "\n"
    results_path.write_text(payload, encoding="utf-8")
    write_readme(out_dir / "README.md", results)

    if verbose:
        print(f"\nR-hat max {diag['r_hat_max']:.4f}, bulk ESS min "
              f"{diag['ess_bulk_min']:.1f}, divergences {diag['divergences_total']}")
        print(f"Decomposed {dec['n_ok']}/{dec['n_attempted']} draws "
              f"({dec['n_failed']} failed)")
        print(f"Bias slope {slope['mean']:.3f} (sd {slope['sd']:.3f}, 95% CI "
              f"[{slope['lo']:.3f}, {slope['hi']:.3f}]) vs generating "
              f"{info['bias_slope']:.3f}")
        print(f"RMSE vs sin x: composite {rmse_composite:.3f}, debiased "
              f"{rmse_debiased:.3f} ({recovery['rmse_reduction_pct']:.1f}% lower)")
        print(f"Coverage of sin x by the debiased 95% band: {coverage:.3f}")
        print(f"results.json sha256 "
              f"{hashlib.sha256(payload.encode('utf-8')).hexdigest()}")
        print(f"Figure {figure_path} "
              f"({figure_path.stat().st_size / 1024:.0f} KiB)")


if __name__ == "__main__":
    main()
```
