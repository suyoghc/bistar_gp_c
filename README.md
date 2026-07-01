# bistar_gp

**BI\* and BMS\* with Gaussian Processes** — Bayesian bias mitigation and model comparison using additive GP decomposition.

Implements the frameworks from Chandramouli & Shiffrin ([2016](https://doi.org/10.1016/j.jmp.2015.10.002), [2020](https://github.com/suyoghc/bistar_gp_c/blob/main/docs/)). The GP with hyperpriors serves as the nonparametric backbone: BI\* exploits additive kernel structure to separate signal components, BMS\* exploits the posterior over hyperparameters to evaluate external parametric models.

## Overview

The core idea: a Gaussian Process with hyperpriors defines a prior (and posterior) over data-generating functions. This serves as the "left side of the BI\* table" — the space of data distributions. Parametric models on the "right side" are then scored by how well they approximate these GP-defined distributions.

**BI\* (Bayesian Inference Star):** Additive GP decomposition for bias mitigation. A GP with kernel `k = k_truth + k_bias` is fitted to data, then decomposed into component posteriors (Eq. 5 from thesis), recovering the "true" signal from a biased observation.

**BMS\* (Bayesian Model Selection Star):** Model comparison via GP-informed priors. For each GP hyperparameter sample ψ, candidate parametric models are scored by divergence G from the GP predictive. This induces:
- **Parameter priors:** GP beliefs transfer into parametric parameter distributions (e.g., GP lengthscale ℓ → frequency ω, GP linear variance σ²\_lin → slope b)
- **Model priors:** Aggregating scores across ψ gives GP-informed prior probability for each model class

## Quick Start

```bash
pip install -r requirements.txt

# BI* — decompose sin(x) + 0.25x into components
python experiments/toy_example.py

# BI* — decompose Mauna Loa CO2 into trend + seasonal + medium-term
python experiments/mauna_loa.py

# BMS* — compare candidate models against GP posterior
python experiments/bms_star_toy.py --priors informative
```

## Project Layout

```
bistar_gp/                       Core package
├── decompose.py ·············· Eq. 5 — additive GP decomposition (pure PyTorch)
├── model.py ·················· GP model class + kernel builders (GPyTorch)
├── fit.py ···················· MAP optimization + HMC via Pyro NUTS
├── debias.py ················· BI* pipeline: fit → decompose → package results
├── viz.py ···················· Decomposition plots
├── data.py ··················· Toy data generator + Mauna Loa loader
├── bms_star.py ··············· BMS* engine: divergence metrics, GP extraction, scoring
├── candidates.py ············· Parametric candidate models with MLE fitting
├── config.py ················· Named prior configs, experiment settings, caching
└── __init__.py ··············· Public API

bistar_viz/                      Standalone visualization scripts
├── mechanism_unified.py ······ BI* mechanism figure: dual-channel GP→parametric transfer
├── model_prior_both.py ······· Model prior trajectories: Occam vs no-Occam comparison
├── model_prior_trajectory_laplace.py · Laplace Z with V_ref Occam toggle
├── model_priors_laplace.py ··· Laplace approximation for Z_Mx
├── model_priors_montecarlo.py · Monte Carlo Z estimation (has dimensionality bias)
├── bistar_sample_size_sweep.py · Model probabilities vs sample size (3 scenarios)
├── bistar_mechanism_plots.py ·· Earlier mechanism figure (ω only)
├── bistar_pipeline_figure.py ·· Full BMS* pipeline visualization
└── narrative_figure.py ······· Compact overview figure

experiments/                     Runnable experiments (use bistar_gp package)
├── toy_example.py ············ BI* on sin(x) + 0.25x + noise
├── mauna_loa.py ·············· BI* on Mauna Loa CO2 data
└── bms_star_toy.py ··········· BMS* model comparison experiment
```

## Key Concepts

### BI\* — Additive GP Decomposition

Model the data with a GP whose kernel is a sum of components:

```
k(x, x') = k_truth(x, x') + k_bias(x, x')
```

After fitting, the posterior decomposes cleanly (Eq. 5). Each component gets its own posterior mean and covariance, sharing a single Cholesky factorization of the summed kernel.

### BMS\* — GP-Informed Model Comparison

For each GP hyperparameter sample ψ:
1. Compute GP predictive distribution (μ\_ψ, σ²\_ψ)
2. For each candidate model M\_x with parameters φ, compute divergence G(ψ, θ\_Mx(φ))
3. Soft transfer: weight each instance by exp(-G/τ)

This produces **induced parameter priors** — GP beliefs transferred into the parametric model's parameter space. The normalizing constant Z\_Mx gives the **model prior**.

### Model Priors: Occam vs No-Occam

The framework supports two interpretations of the model prior Z\_Mx:

**No Occam** (faithful to original BI\*):
```
Z_Mx = ∫ exp(-G(ψ, θ(φ)) / τ) dφ
```
Total GP-compatible volume in parameter space. Complex models naturally score higher because they have more parameter configurations that can match the GP. The original BI\* paper has no implicit complexity penalty — "the sum of posteriors for the larger class has to be larger than the sum for the smaller class, and there is no penalty for class complexity."

**With Occam** (optional complexity penalty):
```
Z_Mx = ∫ p_ref(φ) · exp(-G(ψ, θ(φ)) / τ) dφ
```
Average GP-compatible density. Penalizes models with vast parameter wastelands.

Both are computed via Laplace approximation to avoid Monte Carlo dimensionality bias.

`Z_Mx` is the **data-free** GP model prior: `laplace_evidence.laplace_log_Z_Mx(..., occam=False|True)`, expanded at `argmin Ḡ` with the Hessian of `Ḡ` (no data likelihood). Model *selection* combines it with the data through `model_posterior(construction=...)`, an ablation ladder:

- **baseline** — ordinary marginal likelihood, no GP.
- **Construction I** — `Z_Mx · p_ord(D|M)` (GP acts as a class-level prior).
- **Construction II** *(canonical)* — `∝ N(M) = ∫ p(y|φ)·exp(-Ḡ/τ)·p_ref(φ) dφ`, the Bayes-consistent posterior from a single GP-induced joint prior over (model, parameters).

See `docs/plan-zmx-laplace.md` for the derivation and `Notes/DECISIONS.md` (D3) for the rationale.

### Temperature Parameter τ

Controls the sharpness of the GP's influence:
- **Low τ** → only parameters producing near-perfect GP matches get weight
- **High τ** → broad, diffuse weights approaching uniform
- **τ → ∞** → GP has no influence, recover reference priors

## Prior Configurations

Five named configurations in `config.py`:

| Config | Description | Use case |
|--------|-------------|----------|
| `informative` | Gamma(6, 0.85) | Moderate concentration around reasonable values |
| `vague` | LogNormal(0, 2) | Broad, data-dominated |
| `misspecified_tight` | Gamma(20, 4) | Concentrates away from truth (stress test) |
| `low_noise` | Small noise prior | Overconfident GP |
| `high_noise` | Large noise prior | Underconfident GP |

## References

- Chandramouli, S.H. & Shiffrin, R.M. (2016). Extending Bayesian induction. *Journal of Mathematical Psychology*, 72, 38-42.
- Chandramouli, S.H. (2020). *Bayesian Inference Star: A Framework for Bias Mitigation and Model Selection* (Doctoral thesis, Chapter 5). Indiana University.
- Shiffrin, R.M., Chandramouli, S.H., & Grünwald, P.D. (2016). Bayes factors, relations to minimum description length, and overlapping model classes. *Journal of Mathematical Psychology*, 72, 56-77.
