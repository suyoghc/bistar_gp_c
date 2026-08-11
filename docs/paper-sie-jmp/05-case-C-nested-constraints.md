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
MLE routine, receive four shared base starts, and share every bound except the
lower bound on $b$. The restricted fit additionally receives the free
solutions, clipped at $b=0$ when necessary, and each candidate's selection
pool includes the other candidate's feasible vectors. This deliberate
asymmetry forces exact equality at shared optima instead of turning optimizer
noise into a gap. The frozen $N=20$ data use seed 42 and the true slope
$b=0.25$, so the restriction holds in truth.[^2]

## 5.1 BMS* comparison

The BMS* calculation follows the validated `toy_elicited` stage-IS path. It
pools prior-IS caches from seeds 0, 1, and 2, draws 1,000 SIR predictives with
seed 42, and evaluates 60 locations. For every predictive data pattern
$\psi$, the free and restricted fits minimize the primary
`pw_kl_vcal` value $G(\psi,\theta)$ over their respective parameter regions.
Thus the calculation supplies candidate instances from a shared $\psi$ rather
than introducing candidate-parameter priors. Such priors contribute only to
the separate LOO comparison below.[^2]

The nesting relation fixes the primary-metric ordering as an identity of the
protocol: $M_r\subset M_e$ implies
$\min_{\theta\in M_r}G\geq\min_{\theta\in M_e}G$ for every predictive. The
cross-seeded candidate pools enforce this set inclusion numerically, while
re-evaluation of the same feasible vector gives exact equality at a shared
optimum. The $2\times10^{-7}$ runtime gates guard against machinery
regressions; they do not provide an empirical nesting test. On 999
predictives, the free optimum had $b\geq0$ and the primary $G$ gap equaled
exactly zero. One predictive had a negative free optimum, for a fraction of
0.001, and restricted minus free $G$ equaled 0.000360 on that row.[^2]

This same set inclusion fixes the probability direction before Table 5.1.
The restricted candidate can never exceed the free candidate under either
aggregation at any $\tau$; only the gap's magnitude depends on the sampled
predictives.[^2]

Table 5.1 reports both aggregation conventions across the preregistered
temperature grid. Each pair normalizes over only the free and restricted
candidates.[^2]

| $\tau$ | pooled free | pooled restricted | expected-posterior free | expected-posterior restricted |
|---:|---:|---:|---:|---:|
| 0.1 | 0.500 | 0.500 | 0.500 | 0.500 |
| 0.3 | 0.500 | 0.500 | 0.500 | 0.500 |
| 1.0 | 0.500 | 0.500 | 0.500 | 0.500 |
| 3.0 | 0.500 | 0.500 | 0.500 | 0.500 |
| 10.0 | 0.500 | 0.500 | 0.500 | 0.500 |

At the headline value $\tau=1$, both conventions therefore give an effective
tie. The free-minus-restricted probability gap remains smaller than
$10^{-5}$ at every $\tau$ under both conventions and comes entirely from the
single negative-slope draw. Its monotone contraction with $\tau$ follows
deterministically from the Boltzmann aggregation, not from a measured
temperature effect.[^2]

The result does not support a claim that BMS* preferentially rewards a
satisfied restriction. BMS* assigns the restricted candidate
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
acceptance probability 0.90 and maximum tree depth 8. Both chains for both
candidates initialized deterministically at the same observed-data MLE through
`init_to_value`: $A=0.886352$, $\omega=1.030240$, $\phi=-0.029881$,
$b=0.251277$, $c=0.028723$, and $\sigma=0.321232$. Sampled-grid aliases near
$\omega=4.939$ and $6.999$ make the $\omega$/$\phi$ likelihood multimodal.
Both fits recorded zero divergences. Rank-normalized $\widehat R$ reached at
most 1.003 for the free fit and 1.002 for the restricted fit; minimum bulk
effective sample sizes were 1,004 and 1,638, respectively. These diagnostics
support within-mode convergence only, not exploration across modes.[^2]

| candidate | `elpd_loo` | SE | `p_loo` | max Pareto $k$ | warning |
|---|---:|---:|---:|---:|---|
| free Sin+Linear | -13.074 | 3.458 | 5.343 | 0.564 | no |
| slope-constrained Sin+Linear | -12.661 | 3.594 | 5.169 | 0.718 | yes, one observation |

The constrained-minus-free `elpd_loo` difference equals 0.413 with a paired SE
of 0.256, computed with `ddof=0` to match the ArviZ convention.[^2] The
difference is directionally inconclusive: its magnitude is smaller than twice
its paired SE, the constrained estimate carries a Pareto-$k$ warning because
one observation exceeds the 0.697 good-$k$ threshold, and the paired SE covers
data-level pointwise variability only, without MCMC error. Haaf, Klaassen, and
Rouder report this kind of null-to-inconclusive LOO difference as the failure
mode for a satisfied nested constraint.[^1] Pareto shape values above about
0.7 can make the importance-sampling approximation unreliable, so a decisive
direction would require exact refits or a more robust cross-validation
calculation.[^3]

The two slope priors coincide up to normalization on $b>0$, so LOO has no
structural contrast wherever negative-slope posterior mass is negligible. The
artifact's own full-data local Gaussian diagnostic gives posterior SD
0.0129506 for $b$, places the boundary 19.4028 SDs away, and gives a Gaussian
left-tail probability of $3.65\times10^{-84}$. This local approximation
supports the reading that the constraint binds only where the locally
approximated posterior carries negligible mass. It does not prove that the
global posteriors or leave-one-out fold posteriors are exactly identical, and
it does not establish that the entire observed gap comes from estimator
noise.[^2]

The LOO arm therefore reproduces the null-to-inconclusive failure mode without
supporting a directional claim. BMS* also gives a numerical tie, with a
one-sided direction fixed by nesting and a magnitude determined by the single
negative-slope SIR draw.

[^1]: 🟢 peer-reviewed — Haaf, Klaassen, and Rouder (2025). Bayes factor vs. posterior predictive model assessment: Insights from ordinal constraints. *Computational Brain & Behavior*. https://doi.org/10.1007/s42113-025-00240-0
[^2]: 🟠 empirical — `experiments/haaf_nested_constraint.py`; `runs/haaf_nested_constraint/results.json` and `README.md` (data seed 42; prior-IS seeds 0, 1, 2; SIR seed 42; NUTS seeds 20260811 and 20260812).
[^3]: 🟢 peer-reviewed — Vehtari, Gelman, and Gabry (2017). Practical Bayesian model evaluation using leave-one-out cross-validation and WAIC. *Statistics and Computing*, 27(5), 1413–1432.

---
*Provenance: `runs/haaf_nested_constraint/` · `experiments/haaf_nested_constraint.py` · Notes/DECISIONS.md D63.*
