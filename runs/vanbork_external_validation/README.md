# External validation against van Bork, Romeijn & Wagenmakers (2025)

Generated 2026-08-11 by `experiments/vanbork_external_validation.py` (local,
seconds, no HMC, no GP). Source: Synthese, doi:10.1007/s11229-025-05286-y, §4.

Two model probabilities that the paper derives in closed form from
Rosenkrantz-style expected support against a "data prior", with no reference to
this implementation. They are therefore independent ground truth for the
induced-prior / soft-transfer machinery. The GP scaffold is NOT exercised: the
paper supplies the data prior, so we supply it directly and test the scoring.

## Target A — non-overlapping point models (paper: 0.4 / 0.6)

Data prior: 0.4 on s/n -> 0.16, 0.6 on s/n -> 0.19. Models: theta = 0.15 vs
theta = 0.20. Three aggregation variants, tau -> 0:

| variant | limit | matches paper |
|---|---|---|
| (a) pooled — shipped default, `normalize_per_draw=False` | 0.000 / 1.000 | NO |
| (b) per-atom renormalization, then average (paper Eq. 4) | 0.400 / 0.600 | YES, exact |
| (c) shipped `soft_transfer(..., normalize_per_draw=True)` | 0.400 / 0.600 | YES, exact |

Converged by tau = 1e-4 for (b) and (c).

## Target B — completely overlapping models (paper: ~0.84 / 0.16)

Data prior: point mass on s/n -> 1/2. Models: theta ~ beta(50,50) vs
beta(2,2) — both put nonzero mass everywhere, so Popper would call them equally
probable and no finite data can separate them (both symmetric about 1/2).

Requires the HYBRID form Z_M = integral p_M(theta) exp(-G(theta)/tau) d theta,
i.e. a within-model parameter prior in place of the Lebesgue/V_ref reference
measure — the "data prior + parameter hyperprior hybrid" listed as an open
question in `CogSci Poster/OPEN_QUESTIONS.md`.

| tau | our p(M_x) |
|---|---|
| 1e-2 | 0.792607 |
| 1e-4 | 0.840781 |
| 1e-6 | 0.841413 |
| 1e-7 | 0.841419 |
| paper | 0.841420 |

Absolute error 6.4e-7. Our prior densities at the MLE (7.9589, 1.5000) match
the paper's quoted 7.96 and 1.50.

Analytic reason for the match: Laplace gives Z_M ~ p_M(theta*) sqrt(2 pi tau /
G''(theta*)); both models share the Bernoulli family so G and G'' are identical
and the Hessian factor cancels, leaving the ratio of prior densities at
theta* = 1/2 — exactly the paper's formula. Their result is the tau -> 0,
shared-family, point-data-prior special case of Z_M.
