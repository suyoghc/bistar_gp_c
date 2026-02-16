# Practice Law of Practice — BI* Sandbox

**Question:** Does BI* resolve the 25-year power-vs-exponential debate?

**Data:** Evans et al. (2018) / Heathcote et al. (2000) — 475 subjects, 24 experiments.  
**Download:** https://osf.io/7yx6b/ → put files in `./data/`

## Quick start

```bash
# Synthetic smoke test (no data needed)
cd experiments/practice
python run.py --demo

# Real data
python run.py --data_dir ./data --mode map

# Full Bayesian (cluster)
python run.py --data_dir ./data --mode hmc --n_hmc_samples 200
```

## Files

| File | What |
|------|------|
| `candidates.py` | Power, Exponential, DelayedExp, APEX models |
| `kernels.py` | GP kernel + 3 hyperprior configs (practitioner/moderate/agnostic) |
| `run.py` | Main pipeline — fits all subjects, compares BI* vs BIC |
| `data/` | Put Evans et al. CSVs here |
| `results/` | JSON output per subject + aggregate |

## The argument

Standard Bayes factors for power-vs-exponential are **prior-sensitive** — the
winner flips depending on parameter priors (Evans et al. 2018 showed this).

BI* replaces parameter priors with GP hyperprior on data patterns: "smooth
monotone decrease." Both sides agree on that. If BI* gives the same answer
across 3 different GP hyperprior configs, that's the robustness story.

## Key output

`results/aggregate.json` contains:
- BIC winner counts (standard Bayes factor baseline)
- BI* winner counts per (config × metric × τ)
- Robustness: % of subjects where all 3 GP configs agree
- BIC vs BI* disagreement rate

## Dependencies

Imports from `bistar_gp/` (parent package). Requires:
- gpytorch, torch, pyro (for HMC mode)
- scipy (differential_evolution for candidate fitting)
- numpy, matplotlib
