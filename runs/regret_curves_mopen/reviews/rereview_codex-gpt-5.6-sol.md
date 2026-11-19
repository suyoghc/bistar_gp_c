# Re-review — Codex gpt-5.6-sol xhigh (raiser of DC1-DC4), changed hunks of c57a70e

### REREVIEW-F-D1: RESOLVED

- The paper now distinguishes candidate-variance `pw_nll` from GP-variance `pw_kl_vcal`, identifying `pw_mse` as closer on that axis. The W1-analogue and weak/sharp confidence claims are removed. [Paper section](/Users/sc8918/Documents/GitHub/bistar_gp_c/docs/paper-sie-jmp/06-case-D-mopen-calibration.md:68)
- The affine identity is recorded for all 300 pairs with maximum error \(1.78\times10^{-15}\), alongside the complete tau-grid diagnostic. [results.json](/Users/sc8918/Documents/GitHub/bistar_gp_c/runs/regret_curves_mopen/results.json:463)
- The replacement tau-free `raw_draw_wins` counts match an independent read-only aggregation of the 50 source artifacts: 974/2467, 998/2364, and 1037/2302. [results.json](/Users/sc8918/Documents/GitHub/bistar_gp_c/runs/regret_curves_mopen/results.json:3888)

### REREVIEW-F-D2: RESOLVED

- The paper explicitly states that the limits-note hyperparameter-draw target is unreconstructable and correctly labels the solid estimand as \(E_{f\mid y,\hat\eta}|f-\mu_\theta|\). [Paper section](/Users/sc8918/Documents/GitHub/bistar_gp_c/docs/paper-sie-jmp/06-case-D-mopen-calibration.md:141)
- The posterior-mean plug-in \(|E[f\mid y,\hat\eta]-\mu_\theta|\) is separately computed, stored, tabulated, and plotted with dashed overlays. [results.json](/Users/sc8918/Documents/GitHub/bistar_gp_c/runs/regret_curves_mopen/results.json:134)
- The prose and figure now describe both quantities as MAP-conditional deviations rather than silently substituting either for the HMC target.

### REREVIEW-F-D3: RESOLVED

- “Scaffold-induced preference,” “helps or misleads,” and explanatory causal language have been removed.
- The revised interpretation is explicitly descriptive and limited to the stored practitioner-MAP scaffold and shared early-trial region. [Paper section](/Users/sc8918/Documents/GitHub/bistar_gp_c/docs/paper-sie-jmp/06-case-D-mopen-calibration.md:185)
- It now states that one RBF reconstruction cannot distinguish F1 representability, F2 mimicry, metric behavior, or sampling noise. [Paper section](/Users/sc8918/Documents/GitHub/bistar_gp_c/docs/paper-sie-jmp/06-case-D-mopen-calibration.md:197)

### NEW-DEFECT-1 [S3]

- The new Jensen text says the draw-based deviation is no smaller than the plug-in for every subject/candidate/trial, without distinguishing the exact expectation from its finite 100-draw Monte Carlo estimate. [Paper section](/Users/sc8918/Documents/GitHub/bistar_gp_c/docs/paper-sie-jmp/06-case-D-mopen-calibration.md:164)
- The reported trial-1 estimates violate that categorical relationship: 116.333 < 116.506 under Power truth and 131.415 < 131.572 under Exponential truth for the Power candidate. [draw estimates](/Users/sc8918/Documents/GitHub/bistar_gp_c/runs/regret_curves_mopen/results.json:2780), [plug-in estimates](/Users/sc8918/Documents/GitHub/bistar_gp_c/runs/regret_curves_mopen/results.json:287)
- Qualify Jensen as applying to the exact estimands while finite-draw estimates may differ, or compute the Gaussian expected absolute deviation analytically.