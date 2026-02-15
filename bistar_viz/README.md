# BI* Visualization Scripts & Plots — Feb 14–15, 2026

All scripts are standalone (no dependency on bistar_gp package).
They implement GP primitives inline for portability.

## Scripts

### Mechanism & Induced Priors
- **mechanism_unified.py** — 3×5 grid showing dual-channel BI* transfer:
  ℓ → ω (wiggliness→frequency) and σ²_lin → b (trend→slope).
  Rows: n=0, 10, 50. Cols: GP hyperpriors, GP predictive, p(ω|ψ), p(b|ψ), Sin+Linear predictive.

- **bistar_mechanism_plots.py** — Earlier version of mechanism figure (3×4, ω only).

### Model Priors (Z_Mx)
- **model_priors_montecarlo.py** — Monte Carlo estimation of Z_Mx.
  ⚠ Has dimensionality bias: underestimates Z for high-d models.

- **model_priors_laplace.py** — Laplace approximation for Z_Mx.
  Fixes MC bias. Does NOT include V_ref.

- **model_prior_trajectory_laplace.py** — Laplace Z with V_ref (Occam penalty).
  Sweeps n=0..50, includes τ sensitivity.

- **model_prior_both.py** — Side-by-side comparison: no-Occam vs with-Occam.
  Uses differential_evolution for robust G* optimization.
  Key output: model_prior_both_versions.png

### Sample Size Sweep
- **bistar_sample_size_sweep.py** — BMS* model probabilities vs n for 3 scenarios
  (default, high_noise, narrow_x). Shows crossover dynamics and convergence.

### Pipeline & Narrative
- **bistar_pipeline_figure.py** — Full BMS* pipeline visualization per prior config.
  GP hyperpriors → GP predictive → candidates → divergence → model weights.

- **narrative_figure.py** — Compact narrative overview figure.

## Plots

### plots/mechanism/
- mechanism_unified.png — 5-column dual-channel transfer (latest)
- mechanism_figure.png — 4-column single-channel (earlier)

### plots/model_priors/
- model_prior_both_versions.png — ★ Key comparison: Occam vs no-Occam
- model_prior_trajectory_laplace.png — No-Occam trajectory
- model_prior_tau_laplace.png — τ sensitivity
- model_prior_flow_laplace.png — Stacked area probability flow
- model_prior_decomposed.png — 4-panel term decomposition (with Occam)
- model_prior_robust.png — With-Occam using diff. evolution
- model_prior_bars.png — Bar chart at n=0,10,50 (MC version)
- model_prior_sweep.png — MC version sweep

### plots/sweep/
- transition_informative.png — Model probability vs n (informative prior)
- transition_all_priors.png — All 5 prior configs comparison
- ess_vs_n.png — Effective sample size vs n
- multimodel_predictive_informative.png — Model predictions overlay
- predictive_function_space.png — GP function-space view
- side_by_side_priors.png — Prior config comparison

### plots/pipeline/
- pipeline_informative.png — Full pipeline (informative prior)
- pipeline_vague.png — Full pipeline (vague prior)
- pipeline_misspecified_tight.png — Full pipeline (misspecified)
- pipeline_comparison.png — Cross-prior comparison

## Key Findings

1. **Induced parameter priors work cleanly.** GP ℓ → ω shows multimodal harmonics
   (real identifiability issue). GP σ²_lin → b converges unimodally.

2. **Model priors depend on Occam choice:**
   - No V_ref: Sin+Linear dominates (~93%) — more compatible parameter volume
   - With V_ref: genuine competition — Linear briefly leads at n≈20
   - Original BI* has no implicit Occam; penalty is a design choice

3. **Laplace Z fixes Monte Carlo dimensionality bias** that systematically
   underestimates Z for high-d models.

4. **τ controls sharpness** of GP influence on model prior.
   High τ → uniform. Low τ → GP dominates.
