# Inference and Metric Options — justification and thesis anchoring

Design principle (D9/D10): every methodological choice is an **explicit, selectable
option with a recorded justification**, and the **default is whatever is closest to
the thesis chapter** (Chandramouli 2020, Ch. 5 — `kb/Raw/papers/important/
SHChandramouli_Thesis Chapter 5 2020-04-01.pdf`). Deviations forced by practical
issues are documented where they occur. This section is written to be adapted
directly into the paper's methods discussion.

## 1. GP hyperparameter inference (`bistar_gp.fit.fit_gp(method=...)`)

### What the thesis chapter does

- **Full-Bayes joint posterior over kernel + noise hyperparameters, by sampling.**
  Ch. 5 p. 172: since the full Bayesian implementation "does not have a closed form
  solution, we instead use sampling methods to approximate the joint posterior on
  the kernel parameters"; p. 173 names HMC and VI as the two admissible
  implementations, "outlined in Appendix I."
- **Appendix II (p. 221): VI was the primary implementation** ("the results shown in
  our examples were based on variational inference", gpflow/TensorFlow), with HMC
  (GPy) as the cross-check and the two reported to give "similar" results.
  10,000 samples, first 1,000 discarded as burn-in.
- **MAP/MMLE is the thesis's explicit contrast**, not its method: Fig. 6 ("best
  fitting") vs Fig. 7a (full Bayes), with the text stressing the wider, honest
  uncertainty of the full posterior.

### The options

All methods return the same dict schema (pyro site name → array of constrained
draws), so any choice flows through `extract_gp_predictives` → BMS* →
decomposition unchanged, and results are directly comparable across methods.

| method | What it is | Thesis anchoring | When to prefer it |
|---|---|---|---|
| `"hmc"` **(default)** | NUTS on the joint hyperparameter posterior (with D8's `init_to_map` + `max_tree_depth`) | The chapter's validated cross-check implementation (App. II); same estimand as its primary VI | Default. Asymptotically exact; matches the repo's tested production path |
| `"vi"` | ADVI-style SVI with a full-covariance Gaussian guide in unconstrained space, MAP-initialized | **The chapter's primary implementation** (App. II) | Stiff posteriors where NUTS mixes poorly (the D8 funnel): VI has no step-size/trajectory pathology (optimization, not simulation) and is fast — at the price of a Gaussian approximation whose fidelity in the funnel is itself an assumption to check |
| `"map"` | MAP/MMLE point estimate, returned as a length-1 "posterior" | The chapter's explicit simpler contrast (Fig. 6) | Clean, deterministic, funnel-free demonstrations; sensitivity analyses; anywhere hyperparameter uncertainty is not the point |
| `"hmc_laplace"` | NUTS on the Laplace-whitened posterior: z = A⁻¹(u − u_MAP), A = chol(H⁻¹), H the MAP Hessian in unconstrained space | Implementation-level aid to the same thesis estimand | Ill-conditioned posteriors where geometry, not multimodality, is the obstacle |

Note on the option set: a *linear* reparameterization of the posterior is
mathematically identical to mass-matrix preconditioning, so `"hmc_laplace"`
delivers both "Laplace-preconditioned NUTS" and "reparameterized HMC" as one
option. A *nonlinear* reparameterization (e.g. sampling a signal-to-noise ratio
instead of the raw noise) would change the geometry more aggressively but is a
larger intervention; it remains the open fork noted in D8 for the
non-converged Mauna Loa chain.

### Default and known practical deviations

Default `"hmc"`: full-Bayes sampling is the thesis's method; between the two
thesis implementations we default to the one this codebase has validated
end-to-end (D6 connection test, D8 sampler work). `"vi"` is one flag away and is
the literal thesis-primary — for the stiff Mauna Loa posterior it is also the
pragmatic recommendation until the D8 mixing fork is resolved.

Deviations to disclose in the paper: thesis scale was 10,000/1,000
samples/burn-in on a 3–4-parameter toy; the Mauna Loa 7-parameter posterior at
that scale is compute-bound under NUTS (D8), so real-data runs use fewer draws
with a convergence caveat, or VI/MAP.

## 2. The divergence G (`metric_name=...` in the METRICS registry)

### What the thesis chapter says

Ch. 5 pp. 174–175: model instances are scored by "best matching," which "is
defined by a metric that is used to compare distributions, a metric that is
chosen by the investigator to have desirable properties (**one or another
variant of KL divergence is often a metric used**)." Two anchors follow:

1. The metric is explicitly an **investigator's choice** — the options-with-
   justifications design *is* the thesis position, not a departure from it.
2. The named default family is **KL variants**.

### The identity that dissolves the old fork (D10)

The viz scripts' G ("pointwise variance-weighted MSE",
`model_priors_laplace.py::compute_G`) and the package default `pw_kl_vcal` are
**the same function**:

    viz:        mean( (μ_GP − μ_θ)² / (2 σ²_GP) )
    pw_kl_vcal: mean( 0.5 (μ_θ − μ_ψ)² / σ²_ψ )  =  KL(N(μ_ψ,σ²_ψ) ‖ N(μ_θ,σ²_ψ))

i.e. the pointwise KL between the GP marginal and a candidate assigned the GP's
own variance — a *variance-calibrated* KL variant. Verified numerically to
1e-12 (`tests/test_fit_gp_options.py::test_viz_variance_weighted_mse_is_pw_kl_vcal`).
Scope of the identity: it holds wherever the GP pointwise variance is at or
above 1e-6, because the two implementations clip variance at different floors
(viz at 1e-6, package `_extract_marginals` at 1e-10) — below 1e-6 they diverge
by the floor ratio (pinned in `test_viz_and_package_floors_diverge_below_1e6_variance`).
That regime is degenerate near-interpolation; for the unification, adopt the
package floor (closer to the un-floored mathematics) and disclose the change if
any legacy figure probed sub-1e-6 variances. So the package default is
simultaneously (a) a KL variant per the thesis and (b) identical to the metric
the viz-reference figures used on any non-degenerate input. The
"single-G decision" required no choice — only the recognition.

(The remaining viz/package difference is upstream and estimator-level, not
metric-level: the viz scripts importance-weight *prior* hyperparameter draws by
marginal likelihood, while the package uses genuine posterior draws with uniform
weights — same mixture-of-Gaussians target, better Monte Carlo estimator, and
the same mixture-moment formulas on both sides.)

### The option family and when each member is right

All registered in `bms_star.METRICS` (extended by `metrics_v2`); selectable
everywhere a `metric_name` is accepted (BMS*, `laplace_log_Z_Mx`,
`model_posterior`, ...).

| Metric | Formula (pointwise) | Justification / use |
|---|---|---|
| `pw_kl_vcal` **(default)** | (μ_θ−μ_ψ)²/(2σ²_ψ) | KL variant (thesis family); GP-uncertainty-weighted mean accuracy; identical to the viz "variance-weighted MSE"; immune to the variance-ratio trap (below) |
| `pw_nll_gp` | ½log(2πσ²_ψ) + (μ_θ−μ_ψ)²/(2σ²_ψ) | Same ranking as `pw_kl_vcal`; the additive log-variance constant matters for absolute G and τ-sensitivity |
| `pw_kl_mean` | (μ_θ−μ_ψ)²/2 | Mean-only KL = MSE/2: drops GP weighting entirely; the "pure fit" baseline |
| `pw_hellinger_vcal` / `pw_hellinger_mean` | bounded transforms of the above | Bounded [0,1]: outlier GP draws cannot dominate the aggregation |
| `kl_forward` / `kl_backward` / `kl_symmetric` | joint n-dim Gaussian KL | Full-covariance comparison, including the candidate's own variance |
| `pw_nll`, `pw_mse` | see bms_star.py | Legacy/simple baselines |

Why the default is the *variance-calibrated* KL rather than the plain KL: the
variance-ratio trap (`metrics_v2.py` header). A plain KL against GP predictives
rewards wrong models with inflated noise for accidentally matching the GP's
width; calibrating the candidate to the GP's variance scores mean adequacy
under GP uncertainty — the quantity BI* transfers. This is the 6-part argument
of `kb/Wiki/Metric Choice Justification.md` (KL → pw_nll → aggregation), which
this section summarizes.

One further thesis nuance for the paper: the chapter's aggregation is a hard
best-match assignment (p. 174: sum the posteriors of the GP instances each
model instance best matches); the package's soft Boltzmann transfer with
temperature τ is the practical relaxation, recovering hard assignment as τ→0.
τ-sensitivity panels therefore double as a thesis-fidelity axis.

## 3. Choosing based on results

Both option sets are exposed precisely so choices can be made empirically:
run the same pipeline across `fit_gp` methods and across metrics, compare model
posteriors, and record the choice in `Notes/DECISIONS.md` with the observed
justification. The defaults above are the thesis-anchored starting point, not
a commitment.

**The comparison has since been run** (D12, corrected by D13 after an
adjudicated independent verification; tables in
`docs/fit-method-metric-comparison.md`, evidence chain in
`experiments/toy_posterior_mode_analysis.py`). Headlines: the toy
hyperparameter posterior is bimodal under the `informative` priors — a
low-noise mode containing the global density maximum (the MAP) and a
high-noise, prior-scale mode holding roughly 3× the posterior mass (prior
importance sampling; the two modes verified as genuine local maxima of the
exact log joint). HMC and Laplace-whitened HMC sample only the density-mode
basin and select the true model under every metric; VI migrates (stably) to
the dominant-mass basin, whose smooth predictives select a wrong model.
Thesis Appendix II's "VI ≈ HMC" agreement does not replicate here, and no
single offered method reports the full bimodal posterior — the practical
diagnostic is the basin-occupancy check (`toy_posterior_mode_analysis.py`),
and §1's pragmatic recommendation of VI for stiff posteriors carries that
mode-check caveat. Because the mass-dominant basin contradicts the
data-generating hyperparameters, this reads as a prior-misspecification
finding as much as a method comparison. Among metrics, `pw_kl_vcal` and
`pw_nll_gp` are empirically equivalent, mean-only and bounded variants lose
discrimination, and joint `kl_forward` is sharpest but most brittle under a
bad hyperparameter posterior — the `pw_kl_vcal` default is confirmed by
results. The METHOD default remains `hmc` as the thesis-anchored choice, now
with the honest qualifier that on this toy it reports the density mode, not
the posterior mass.
