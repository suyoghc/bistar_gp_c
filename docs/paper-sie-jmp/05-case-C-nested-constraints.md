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
