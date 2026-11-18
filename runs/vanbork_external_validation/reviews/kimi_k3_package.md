PASTE-READY PACKAGE FOR KIMI K3 (author-run; no CLI configured in this repo).
You are an independent reviewer (one of four; you will not see the others' outputs).
You have NO repository access; review strictly from the package below, and flag any
claim you cannot verify from it as exactly that. Produce the verdict (APPROVE or
REVISE) and the numbered findings list in the package's specified format.

Review the attached branch diff for the BI*/BMS*-GP paper case A (external
validation against van Bork, Romeijn & Wagenmakers). Verdict: APPROVE or
REVISE. Findings as a numbered list:
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

CASE A WORK ORDER (§2 of the HANDOFF, verbatim):
Scope: writing-heavy; compute exists (`runs/vanbork_external_validation/`,
`runs/e7_convention_sensitivity/`, both with READMEs; D60, D61).
1. Flesh out `03-case-A-external-validation.md`: mapping table, Target B
   six-decimal reproduction + the Laplace special-case argument, Target A
   convention dependence, E7 movement numbers, the kl_forward attribution
   (D61 finding 2) — leaving `[FORK-DECISION-PLACEHOLDER]` where the
   canonical-convention statement goes.
2. Add the multi-parameter reach demo paragraph citing
   `runs/viz_unification/p3_priors_canonical/` under W4 framing.
Acceptance: every number in the section traces to the two run dirs;
placeholder intact; no new compute.

DRIVER-VERIFIED FACTS (state of the world; do not report these as findings):
- WRITING-ONLY case. The compute is FINAL and predates the branch (D60/D61,
  2026-08-11). The [FORK-DECISION-PLACEHOLDER] at the canonical-convention
  slot is REQUIRED by the work order (§1 marks Case A blocked on the D60
  fork, an author call): its presence is correct; do not flag it and do not
  propose resolving the fork.
- Driver reran both scripts from the branch tip: exit 0; the regenerated
  JSONs are byte-identical to the committed artifacts EXCEPT the
  "generated" date-stamp field (2026-08-12 vs 2026-08-11); the committed
  originals were restored (their dates match the D60/D61 records).
- This branch deliberately commits the previously working-tree-only compute
  provenance: both experiments scripts, both run dirs, and the D60/D61
  DECISIONS entries together with the new D65. The committed DECISIONS diff
  therefore contains three entries (D60, D61, D65) by design.
- kb/ is entirely gitignored (zero kb/ files ever tracked); kb paths may
  ground ARGUMENTS but never numbers. runs/viz_unification/ is local and
  untracked, so the reach paragraph uses the D17-RECORDED citation pattern
  (values quoted from the committed Notes/DECISIONS.md D17 entry,
  regenerable via the named bistar_viz scripts) — the same pattern the Case
  B review accepted for legacy values.
- The e7 script's SIR path depends on local untracked prior-IS caches
  (runs/prior_sensitivity/is_draws_toy_elicited_s{0,1,2}.npz, 60000 draws
  per seed); their regeneration route is prior_sensitivity_study.py stage
  A (documented in D18/D61). The van Bork script has no such dependency
  (analytic, seconds).
- The cited reference title was verified against the kb ingest frontmatter
  verbatim: van Bork, R., Romeijn, J.-W., & Wagenmakers, E.-J. (2025),
  "Simplicity in Bayesian nested-model comparisons: Popper's disagreement
  with Wrinch and Jeffreys revisited", Synthese,
  doi:10.1007/s11229-025-05286-y.
- The uncommitted working-tree Notes/DECISIONS.md additionally carries
  D62/D63/D64 (other branches) above the committed content; they are
  correctly absent from this branch's diff.

=== SECTION FILE (docs/paper-sie-jmp/03-case-A-external-validation.md) ===
# 3. Case A: external validation against van Bork, Romeijn, and Wagenmakers

van Bork, Romeijn, and Wagenmakers derive model probabilities from expected
predictive support under an independently specified data prior. Their proposal
cites the BI*/BMS* line as related prior work, but their closed-form examples
were developed without reference to the present implementation. They therefore
provide external checks on the induction and soft-transfer machinery. Because
their examples supply the data prior directly, these checks bypass its GP
construction.[^1]

## 3.1 Correspondence of the constructions

The correspondence below remains deliberately qualified. Both approaches
evaluate models against a distribution over possible data, but they need not
assign the same semantics to every intermediate quantity.

| van Bork et al. | Present notation and computation | Qualification |
|---|---|---|
| Data prior, a probability over outputs specified independently of the candidate models | \(p_0(\psi)\), a distribution over data patterns | In the general framework, GP hyperpriors induce \(p_0(\psi)\). The validation examples instead insert the authors' supplied data prior, so they do not test the GP scaffold. |
| Expected support against the data prior, expressed through Rosenkrantz-style verisimilitude | A divergence-based score \(G(\psi,\theta)\), followed by \(\bar G(\phi)\) when averaged over data patterns | Their support increases with predictive agreement; our divergence decreases with it. Additive and scale conventions therefore prevent a literal identification. |
| Prior model probability from expected posterior probability under their Eq. 4 | Normalize model support within each draw \(\psi\), then average under \(p_0(\psi)\) | This order matches expected-posterior aggregation. It does not match pooled aggregation, which sums unnormalized support across draws before model normalization. |
| Completely overlapping models with distinct within-model parameter priors | Hybrid \(Z_M=\int p_M(\phi)\exp\{-\bar G_M(\phi)/\tau\}\,d\phi\) | The within-model density \(p_M(\phi)\) replaces the usual Lebesgue or \(V_{\mathrm{ref}}\)-normalized reference measure, so the check concerns an extension of the standard \(Z_M\). |
| A restricted model nested in an encompassing model | \(M_r\subset M_e\) | We adopt their nesting notation. Normalized predictive weights over a candidate roster do not thereby become set-additive probabilities over hypotheses. |

## 3.2 Target B: completely overlapping models

Their coin example compares \(M_x\), with
\(\theta\sim\operatorname{Beta}(50,50)\), against \(M_z\), with
\(\theta\sim\operatorname{Beta}(2,2)\), under a point data prior at
\(\theta^*=1/2\). The hybrid computation approaches the published probability
for \(M_x\) monotonically over the reported low-temperature rows:

| \(\tau\) | Computed \(p(M_x)\) |
|---:|---:|
| \(10^{-2}\) | 0.792607 |
| \(10^{-4}\) | 0.840781 |
| \(10^{-6}\) | 0.841413 |
| \(10^{-7}\) | 0.841419 |
| Published target | 0.841420 |

At the smallest reported temperature, the absolute error equals
\(6.4\times10^{-7}\). The computed prior densities at the maximum-likelihood
point, 7.9589 for \(M_x\) and 1.5000 for \(M_z\), also reproduce the quoted
7.96 and 1.50 values.[^2]

The agreement follows from a Laplace special case. Around the common optimum,

\[
Z_M \approx p_M(\theta^*)
\sqrt{\frac{2\pi\tau}{G''(\theta^*)}}.
\]

Both models use the same Bernoulli family, so they share the local curvature
\(G''(\theta^*)\). That factor and the remaining common terms cancel after
normalization across models. As \(\tau\) approaches zero, the normalized
hybrid scores consequently converge to the ratio of the within-model prior
densities at \(\theta^*\). The authors' published formula thus coincides with
the shared-family, point-data-prior, zero-temperature limit of the hybrid
\(Z_M\). Target B supplies the first passing test of this within-model-prior
extension, which had previously remained an open implementation question.[^2]

## 3.3 Target A: aggregation changes the limiting answer

The non-overlapping example assigns data-prior mass 0.4 at a Bernoulli
proportion of 0.16 and mass 0.6 at 0.19, then compares point models at 0.15 and
0.20. van Bork et al.'s answer assigns model probabilities 0.4 and 0.6. The
three implemented aggregation routes behave differently:

| Aggregation route | Low-temperature result | Target A verdict |
|---|---:|---|
| Pooled, `normalize_per_draw=False` | 0.000 / 1.000 | Fails |
| Normalize each data-prior atom, then average | 0.400 / 0.600 | Exact |
| `soft_transfer(..., normalize_per_draw=True)` | 0.400 / 0.600 | Exact |

Both per-draw routes have converged to the exact target by
\(\tau=10^{-4}\).[^2] The result exposes a modeling choice rather than a
numerical defect. Pooled aggregation preserves absolute divergence magnitudes:
a draw that every candidate fits poorly contributes less total support. That
property carries the M-open inadequacy signal, but pooled aggregation fails
Target A. Expected-posterior aggregation matches Eq. 4 and avoids that failure,
but each draw must spend one full unit of credit even when every candidate fits
poorly. The latter choice therefore discards the absolute-magnitude signal.

[FORK-DECISION-PLACEHOLDER]

Pending the author's decision, the E7 artifact records only a candidate
presentation: treat aggregation as an explicit evaluation dial alongside
\(\tau\) and `occam`, retain pooled results for continuity, report the Eq. 4
variant in Case A, and reserve the `kl_forward` attribution for the appendix.
That candidate does not settle the canonical convention.[^3]

## 3.4 Measured sensitivity on the validated toy path

E7 evaluates the fork on the validated `toy_elicited` SIR path. Under the
primary `pw_kl_vcal` metric at \(\tau=1\), pooled aggregation gives model
probabilities 0.183, 0.192, 0.441, and 0.184 for Linear, Sinusoidal,
Sin+Linear, and Quadratic, respectively. This row reproduces the ratified SIR
headline. Sin+Linear remains the highest-weight candidate under every tested
aggregation variant and temperature. The maximum absolute movement between
pooled and expected-posterior aggregation equals 0.31 at \(\tau=0.1\), 0.072
at \(\tau=1\), and 0.001 at \(\tau=10\); at \(\tau=1\), the Sin+Linear
weight changes from 0.441 to 0.513.[^3]

The appendix-only `kl_forward` stress metric reveals a sharper attribution.
With pooled aggregation, the Sin+Linear weight collapses to approximately
0.000 for \(\tau\leq1\). Expected-posterior aggregation instead gives 0.696
at \(\tau=0.1\), equal at the reported precision to the raw hard-best-match
fraction of 696/1000. Expected-posterior aggregation converges to hard-win
fractions as \(\tau\) approaches zero by construction, and the artifact's
consistency check confirms that identity. The earlier `kl_forward` fragility
therefore reflects pooled-aggregation sensitivity to outlying draws, not a
property of the metric alone.[^3]

## 3.5 Multi-parameter reach under methods-validation framing

An earlier informative-configuration, MAP-based visualization arm provides a
methods-validation reach check rather than a paper-facing inferential
headline. In `runs/viz_unification/p3_priors_canonical/`, the multi-parameter
Sin+Linear candidate receives 0.992 at \(n=50\) and remains between 0.93 and
0.99 across all evaluated \(n\). This result shows that the same induced-prior
machinery extends beyond the closed-form coin targets to a richer candidate
family. It does not replace the validated `toy_elicited` SIR result above.[^4]

[^1]: 🟢 peer-reviewed — van Bork, R., Romeijn, J.-W., & Wagenmakers, E.-J. (2025). Simplicity in Bayesian nested-model comparisons: Popper's disagreement with Wrinch and Jeffreys revisited. *Synthese*. https://doi.org/10.1007/s11229-025-05286-y.
[^2]: 🟠 empirical — `experiments/vanbork_external_validation.py`; `runs/vanbork_external_validation/results.json` and `README.md`; Notes/DECISIONS.md D60.
[^3]: 🟠 empirical — `experiments/e7_convention_sensitivity.py`; `runs/e7_convention_sensitivity/results.json` and `README.md`; Notes/DECISIONS.md D61.
[^4]: 🟠 empirical — D17-recorded findings for the local, untracked `runs/viz_unification/p3_priors_canonical/` arm, generated by `bistar_viz/scripts/viz_unification_compare.py` through `bistar_viz/scripts/model_priors_laplace.py`. The informative-configuration, MAP-based values are 0.992 at \(n=50\) and 0.93–0.99 across all evaluated \(n\); the committed Notes/DECISIONS.md D17 record supplies their citation provenance and the `bistar_viz` scripts regenerate them.

---
*Provenance: `runs/vanbork_external_validation/` ·
`experiments/vanbork_external_validation.py` · Notes/DECISIONS.md D60;
`runs/e7_convention_sensitivity/` ·
`experiments/e7_convention_sensitivity.py` · Notes/DECISIONS.md D61.
The W4 reach check follows the D17-recorded citation path stated in [^4].
Argument provenance: `kb/Raw/papers/important/vanBork_Romeijn_Wagenmakers_2025_subset_problem.md`
and `kb/Wiki/Subset Problem and the Data Prior.md`.*


=== RUN README (runs/vanbork_external_validation/README.md) ===
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


=== RUN JSON (runs/vanbork_external_validation/results.json, FULL) ===
{
  "source": "van Bork, Romeijn & Wagenmakers 2025, Synthese, doi:10.1007/s11229-025-05286-y, Section 4",
  "generated": "2026-08-11",
  "taus": [
    1.0,
    0.1,
    0.01,
    0.001,
    0.0001,
    1e-05,
    1e-06,
    1e-07
  ],
  "target_a": {
    "names": [
      "M1 (theta=0.15)",
      "M2 (theta=0.20)"
    ],
    "target": {
      "M1 (theta=0.15)": 0.4,
      "M2 (theta=0.20)": 0.6
    },
    "G": [
      [
        0.0003852189585290388,
        0.005280769692049159
      ],
      [
        0.005870165359722922,
        0.0003165152651966492
      ]
    ],
    "rows": [
      {
        "tau": 1.0,
        "M1 (theta=0.15)": 0.49965650872257117,
        "M2 (theta=0.20)": 0.5003434912774289
      },
      {
        "tau": 0.1,
        "M1 (theta=0.15)": 0.49656623856814297,
        "M2 (theta=0.20)": 0.503433761431857
      },
      {
        "tau": 0.01,
        "M1 (theta=0.15)": 0.4667729956851523,
        "M2 (theta=0.20)": 0.5332270043148476
      },
      {
        "tau": 0.001,
        "M1 (theta=0.15)": 0.3993453066638815,
        "M2 (theta=0.20)": 0.6006546933361185
      },
      {
        "tau": 0.0001,
        "M1 (theta=0.15)": 0.4,
        "M2 (theta=0.20)": 0.6
      },
      {
        "tau": 1e-05,
        "M1 (theta=0.15)": 0.4,
        "M2 (theta=0.20)": 0.6
      },
      {
        "tau": 1e-06,
        "M1 (theta=0.15)": 0.4,
        "M2 (theta=0.20)": 0.6
      },
      {
        "tau": 1e-07,
        "M1 (theta=0.15)": 0.4,
        "M2 (theta=0.20)": 0.6
      }
    ],
    "rows_pooled": [
      {
        "tau": 1.0,
        "M1 (theta=0.15)": 0.4996566714119555,
        "M2 (theta=0.20)": 0.5003433285880444
      },
      {
        "tau": 0.1,
        "M1 (theta=0.15)": 0.49658202255622896,
        "M2 (theta=0.20)": 0.503417977443771
      },
      {
        "tau": 0.01,
        "M1 (theta=0.15)": 0.467855436624073,
        "M2 (theta=0.20)": 0.532144563375927
      },
      {
        "tau": 0.001,
        "M1 (theta=0.15)": 0.3839987766269134,
        "M2 (theta=0.20)": 0.6160012233730866
      },
      {
        "tau": 0.0001,
        "M1 (theta=0.15)": 0.25114742054263756,
        "M2 (theta=0.20)": 0.7488525794573624
      },
      {
        "tau": 1e-05,
        "M1 (theta=0.15)": 0.0006915837751011594,
        "M2 (theta=0.20)": 0.9993084162248989
      },
      {
        "tau": 1e-06,
        "M1 (theta=0.15)": 9.688885873115595e-31,
        "M2 (theta=0.20)": 1.0
      },
      {
        "tau": 1e-07,
        "M1 (theta=0.15)": 2.8025910750271484e-299,
        "M2 (theta=0.20)": 1.0
      }
    ],
    "rows_perdraw": [
      {
        "tau": 1.0,
        "M1 (theta=0.15)": 0.49965650872257117,
        "M2 (theta=0.20)": 0.5003434912774289
      },
      {
        "tau": 0.1,
        "M1 (theta=0.15)": 0.49656623856814297,
        "M2 (theta=0.20)": 0.503433761431857
      },
      {
        "tau": 0.01,
        "M1 (theta=0.15)": 0.4667729956851523,
        "M2 (theta=0.20)": 0.5332270043148476
      },
      {
        "tau": 0.001,
        "M1 (theta=0.15)": 0.3993453066638815,
        "M2 (theta=0.20)": 0.6006546933361185
      },
      {
        "tau": 0.0001,
        "M1 (theta=0.15)": 0.4,
        "M2 (theta=0.20)": 0.6
      },
      {
        "tau": 1e-05,
        "M1 (theta=0.15)": 0.4,
        "M2 (theta=0.20)": 0.6
      },
      {
        "tau": 1e-06,
        "M1 (theta=0.15)": 0.4,
        "M2 (theta=0.20)": 0.6
      },
      {
        "tau": 1e-07,
        "M1 (theta=0.15)": 0.4,
        "M2 (theta=0.20)": 0.6
      }
    ],
    "rows_shipped_npd_true": [
      {
        "tau": 1.0,
        "M1 (theta=0.15)": 0.4996567144883083,
        "M2 (theta=0.20)": 0.5003432855116917
      },
      {
        "tau": 0.1,
        "M1 (theta=0.15)": 0.49658633141353736,
        "M2 (theta=0.20)": 0.5034136685864626
      },
      {
        "tau": 0.01,
        "M1 (theta=0.15)": 0.46827826385721033,
        "M2 (theta=0.20)": 0.5317217361427897
      },
      {
        "tau": 0.001,
        "M1 (theta=0.15)": 0.4001965745042194,
        "M2 (theta=0.20)": 0.5998034254957806
      },
      {
        "tau": 0.0001,
        "M1 (theta=0.15)": 0.4,
        "M2 (theta=0.20)": 0.6
      },
      {
        "tau": 1e-05,
        "M1 (theta=0.15)": 0.4,
        "M2 (theta=0.20)": 0.6
      },
      {
        "tau": 1e-06,
        "M1 (theta=0.15)": 0.4,
        "M2 (theta=0.20)": 0.6
      },
      {
        "tau": 1e-07,
        "M1 (theta=0.15)": 0.4,
        "M2 (theta=0.20)": 0.6
      }
    ]
  },
  "target_b": {
    "names": [
      "M_x beta(50,50)",
      "M_z beta(2,2)"
    ],
    "published_densities_at_mle": {
      "M_x beta(50,50)": 7.95892373871788,
      "M_z beta(2,2)": 1.5000000000000007
    },
    "published_weight_Mx": 0.8414195904910299,
    "target": {
      "M_x beta(50,50)": 0.8414195904910299,
      "M_z beta(2,2)": 0.15858040950897012
    },
    "rows": [
      {
        "tau": 1.0,
        "M_x beta(50,50)": 0.5296605155174497,
        "M_z beta(2,2)": 0.47033948448255036
      },
      {
        "tau": 0.1,
        "M_x beta(50,50)": 0.6507977844205177,
        "M_z beta(2,2)": 0.34920221557948233
      },
      {
        "tau": 0.01,
        "M_x beta(50,50)": 0.792606943759565,
        "M_z beta(2,2)": 0.20739305624043508
      },
      {
        "tau": 0.001,
        "M_x beta(50,50)": 0.8352288012734923,
        "M_z beta(2,2)": 0.16477119872650767
      },
      {
        "tau": 0.0001,
        "M_x beta(50,50)": 0.8407813510283959,
        "M_z beta(2,2)": 0.1592186489716041
      },
      {
        "tau": 1e-05,
        "M_x beta(50,50)": 0.8413555652894344,
        "M_z beta(2,2)": 0.15864443471056563
      },
      {
        "tau": 1e-06,
        "M_x beta(50,50)": 0.8414131859480664,
        "M_z beta(2,2)": 0.1585868140519335
      },
      {
        "tau": 1e-07,
        "M_x beta(50,50)": 0.841418950016495,
        "M_z beta(2,2)": 0.15858104998350495
      }
    ]
  },
  "abs_error_at_min_tau": {
    "A": 0.0,
    "B": 6.404745348520535e-07
  }
}

=== RUN README (runs/e7_convention_sensitivity/README.md) ===
# E7 — aggregation-convention sensitivity (validated toy path)

Generated 2026-08-11 by `experiments/e7_convention_sensitivity.py` (D61).
Basis: `toy_elicited`, SIR n_pred=1000 from pooled 3-seed prior-IS — the
ratified W4 path; anchor row reproduces the SIR headline exactly
(pw_kl_vcal tau=1 pooled: 0.183 / 0.192 / 0.441 / 0.184).

## Findings

1. **Primary metric (pw_kl_vcal): winner convention-robust everywhere.**
   Sin+Linear tops all three variants at every tau. Movement pooled vs
   expected-posterior: 0.31 at tau=0.1, 0.072 at tau=1 (0.441 -> 0.513),
   0.001 at tau=10. Qualitative claims unaffected; headline number moves
   modestly under Eq.-4 semantics.

2. **NEW: the kl_forward "fragility" (W1/D18) is largely an aggregation
   artifact of the pooled convention.** Pooled at tau<=1 collapses Sin+Linear
   to ~0.000 (Linear/Quadratic split the mass — outlier draws with globally
   minimal G dominate the unnormalized pool). Under per-draw conventions
   kl_forward becomes sane: expected-posterior gives Sin+Linear 0.696 at
   tau=0.1, exactly matching the raw hard-win fraction 696/1000 (as it must:
   expected-posterior at tau->0 IS the hard best-match rate). W1's framing
   ("soft tau=1 collapse under heterogeneous draw mixtures") is thereby
   attributed: it is pooled-aggregation outlier sensitivity, not a property of
   the metric alone.

3. Consistency check passed: expected_posterior(tau->0) = hard-win fractions.

## Fork input (D60, author decision pending)

- Pooled keeps absolute divergence magnitudes (M-open signal) and continuity
  with every ratified number; fails van Bork Target A.
- Expected-posterior matches van Bork Eq. 4 semantics and rescues kl_forward,
  but discards magnitudes (every draw spends one unit of credit).
- Candidate paper position: present the aggregation convention as an explicit
  evaluation dial alongside tau and occam; canonical numbers pooled, Case A
  reports the Eq.-4 variant, appendix carries the kl_forward attribution.


=== RUN JSON (runs/e7_convention_sensitivity/results.json, FULL) ===
{
  "config": "toy_elicited",
  "n_pred": 1000,
  "is_seeds": [
    0,
    1,
    2
  ],
  "model_names": [
    "Linear",
    "Sinusoidal",
    "Sin+Linear",
    "Quadratic"
  ],
  "generated": "2026-08-11",
  "anchor_pooled_pw_kl_vcal_tau1": [
    0.18339001724428333,
    0.1923955140897971,
    0.44067371117415843,
    0.18354075749176121
  ],
  "results": {
    "pw_kl_vcal": {
      "0.1": {
        "pooled": [
          0.12080661834058654,
          0.12471402532260904,
          0.6336791776415797,
          0.12080017869522483
        ],
        "rowmin": [
          0.036608193974719476,
          0.04039862076492636,
          0.8863096479406375,
          0.03668353731971672
        ],
        "expected_posterior": [
          0.016793524033472673,
          0.019339336315471037,
          0.9470252688520636,
          0.016841870798992648
        ]
      },
      "0.3": {
        "pooled": [
          0.11428321467711881,
          0.1242309937092506,
          0.6470214904679347,
          0.11446430114569593
        ],
        "rowmin": [
          0.08472526994796022,
          0.09336922240727344,
          0.7370211247440785,
          0.08488438290068771
        ],
        "expected_posterior": [
          0.05649952408332812,
          0.06392983591776222,
          0.8229420988378155,
          0.05662854116109408
        ]
      },
      "1.0": {
        "pooled": [
          0.18339001724428333,
          0.1923955140897971,
          0.44067371117415843,
          0.18354075749176121
        ],
        "rowmin": [
          0.17679800844924867,
          0.18590062817480882,
          0.4603525996442708,
          0.17694876373167165
        ],
        "expected_posterior": [
          0.1592544835663714,
          0.16865859101921857,
          0.5126837179683223,
          0.1594032074460877
        ]
      },
      "3.0": {
        "pooled": [
          0.22466292426479983,
          0.2291661941022073,
          0.3214361828057378,
          0.22473469882725494
        ],
        "rowmin": [
          0.223679851002957,
          0.2282528534574733,
          0.3243148631542618,
          0.22375243238530784
        ],
        "expected_posterior": [
          0.22012156001360225,
          0.2249540579236698,
          0.33472772918676164,
          0.2201966528759663
        ]
      },
      "10.0": {
        "pooled": [
          0.24206050570700036,
          0.2436430426456574,
          0.2722110986283088,
          0.24208535301903347
        ],
        "rowmin": [
          0.24196129918819867,
          0.2435540460424947,
          0.27249836119534765,
          0.24198629357395895
        ],
        "expected_posterior": [
          0.24159819550556036,
          0.2432301246180665,
          0.273547997142369,
          0.24162368273400409
        ]
      },
      "max_abs_movement_pooled_vs_eqp": {
        "0.1": 0.31334609121048396,
        "0.3": 0.17592060836988088,
        "1.0": 0.07201000679416392,
        "3.0": 0.013291546381023811,
        "10.0": 0.001336898514060214
      }
    },
    "kl_forward": {
      "0.1": {
        "pooled": [
          0.5776623966370532,
          2.915632233698937e-06,
          4.312633288701694e-101,
          0.42233468773071303
        ],
        "rowmin": [
          0.01439400675523952,
          0.2872901571339631,
          0.6859092744401684,
          0.012406561670628861
        ],
        "expected_posterior": [
          0.008099422410931643,
          0.2889308182704174,
          0.6960704748508468,
          0.006899284467804077
        ]
      },
      "0.3": {
        "pooled": [
          0.5191372314135831,
          0.013594945996038006,
          5.145248690431794e-34,
          0.46726782259037886
        ],
        "rowmin": [
          0.018804322391081214,
          0.2859500801722907,
          0.6770171355419088,
          0.01822846189471931
        ],
        "expected_posterior": [
          0.010514572043285058,
          0.2824434850546835,
          0.6967986861002223,
          0.01024325680180917
        ]
      },
      "1.0": {
        "pooled": [
          0.41454279103637137,
          0.1816352488790708,
          3.391697830764308e-10,
          0.403821959745388
        ],
        "rowmin": [
          0.05613999280169587,
          0.26871532967525064,
          0.6186339072273698,
          0.05651077029568366
        ],
        "expected_posterior": [
          0.03854307696623614,
          0.22782396233905908,
          0.6947452997025414,
          0.03888766099216331
        ]
      },
      "3.0": {
        "pooled": [
          0.3502729957070257,
          0.29861960140505983,
          0.0027748100079786546,
          0.34833259287993573
        ],
        "rowmin": [
          0.1268244045782355,
          0.23878125017598395,
          0.507089989583158,
          0.12730435566262266
        ],
        "expected_posterior": [
          0.08537429083335694,
          0.16775604051781498,
          0.6611515526948006,
          0.08571811595402741
        ]
      },
      "10.0": {
        "pooled": [
          0.2414258863653513,
          0.272444972404087,
          0.24452950876131005,
          0.24159963246925173
        ],
        "rowmin": [
          0.18895381861395374,
          0.2341777497911735,
          0.38774661032240326,
          0.1891218212724695
        ],
        "expected_posterior": [
          0.15253818986293188,
          0.1906959698555062,
          0.5041259804928205,
          0.15263985978874128
        ]
      },
      "max_abs_movement_pooled_vs_eqp": {
        "0.1": 0.6960704748508468,
        "0.3": 0.6967986861002223,
        "1.0": 0.6947452993633716,
        "3.0": 0.658376742686822,
        "10.0": 0.25959647173151046
      }
    }
  }
}

=== BRANCH DIFF vs main (full; run JSONs/READMEs excluded — content above) ===
Stat:
 Notes/DECISIONS.md                                 | 161 +++++++++++++
 .../paper-sie-jmp/03-case-A-external-validation.md | 136 +++++++++++
 experiments/e7_convention_sensitivity.py           | 137 +++++++++++
 experiments/vanbork_external_validation.py         | 204 ++++++++++++++++
 runs/e7_convention_sensitivity/README.md           |  37 +++
 runs/e7_convention_sensitivity/results.json        | 242 +++++++++++++++++++
 runs/vanbork_external_validation/README.md         |  51 ++++
 runs/vanbork_external_validation/results.json      | 263 +++++++++++++++++++++
 8 files changed, 1231 insertions(+)

diff --git a/Notes/DECISIONS.md b/Notes/DECISIONS.md
index 033fee3..fab50ce 100644
--- a/Notes/DECISIONS.md
+++ b/Notes/DECISIONS.md
@@ -5716,3 +5716,164 @@ to be amended later merely to insert them. STOP before Ready or merge. NOT autho
 second correction pass, restoring/applying/dropping stash `5280d1e1…`, D59 work, evidence
 or figure changes, poster-repository work, the captions themselves, Della contact, new
 computation, holdout access, BMS*, Ready, or merge.
+
+## D60: External validation against van Bork, Romeijn & Wagenmakers (2025) — two published closed-form targets reproduced; the aggregation convention is adjudicated, and the M-open signal is in tension with it — 2026-08-11
+
+**Problem:** Every demonstration of the induced-prior / soft-transfer machinery
+to date is self-validating: we generate data from a known process and check that
+the framework recovers it. That establishes internal consistency, not external
+correctness. The full-text ingest of van Bork, Romeijn & Wagenmakers (2025,
+*Synthese*, doi:10.1007/s11229-025-05286-y) surfaced two model probabilities the
+authors derive in closed form from Rosenkrantz-style expected support against a
+"data prior" — independent ground truth, computed with no reference to this
+implementation.
+
+**Decision:** New driver `experiments/vanbork_external_validation.py`
+(local, seconds, no HMC and no GP: the paper supplies the data prior directly,
+so only the scoring half is under test). Outputs to
+`runs/vanbork_external_validation/{results.json, README.md}`.
+
+**Result — both targets reproduced.**
+
+*Target B (completely overlapping models, their beta example):* data prior a
+point mass at s/n = 1/2; M_x: theta ~ beta(50,50) vs M_z: theta ~ beta(2,2).
+Paper's answer 7.96/(7.96+1.50) = 0.841420. Ours converges to **0.841419** by
+tau = 1e-7 (abs err 6.4e-7); our densities at the MLE (7.9589, 1.5000) match
+their quoted 7.96/1.50. This required the HYBRID form
+Z_M = ∫ p_M(theta) exp(-G(theta)/tau) d theta, i.e. a within-model parameter
+prior in place of the Lebesgue/V_ref reference measure — the hybrid listed as an
+OPEN question. Analytic account: Laplace gives Z_M ≈ p_M(theta*)·sqrt(2 pi tau /
+G''(theta*)); both models share the Bernoulli family, so G'' cancels and the
+normalized ratio converges to the ratio of prior densities at theta*. **Their
+published formula is therefore the tau→0, shared-family, point-data-prior
+special case of Z_M.** The hybrid open question now has a passing test.
+
+*Target A (non-overlapping point models):* data prior 0.4 on s/n→0.16, 0.6 on
+s/n→0.19; models theta=0.15 vs theta=0.20; paper's answer 0.4/0.6. Three
+aggregation variants at tau→0:
+- pooled (**shipped default, `normalize_per_draw=False`**): → **0.000/1.000, FAILS**
+- per-atom renormalization then average (paper Eq. 4): → 0.400/0.600, exact
+- shipped `soft_transfer(..., normalize_per_draw=True)`: → 0.400/0.600, exact
+
+**Adjudication and the tension it exposes (OPEN — author call required):** the
+paper defines the prior model probability as the *expected posterior* across the
+data prior (their Eq. 4), which mandates normalizing each data-prior atom into a
+posterior over models before averaging. Under that reading the canonical default
+is wrong and `normalize_per_draw=True` is correct. But the two conventions serve
+different goals and the choice is not free:
+- **Per-draw** matches the expected-posterior derivation, but destroys absolute
+  divergence magnitudes — every draw must spend one full unit of credit, so a
+  draw that no candidate fits votes exactly as forcefully as one that all
+  candidates fit.
+- **Pooled** preserves absolute magnitudes, which is precisely what carries the
+  **M-open inadequacy signal** (uniformly high divergence ⇒ no candidate is
+  adequate) that D-series work and the poster both claim as a distinguishing
+  feature.
+So the framework cannot simultaneously have the paper's expected-posterior
+semantics and the M-open magnitude signal from a single aggregation. This is a
+substantive modeling fork, not a bug, and it is recorded here unresolved.
+
+**Scope note:** no poster figure is invalidated by this entry. All toy and Mauna
+runs use equal-weight GP draws, where the two conventions differ far less than
+in Target A's unequal-mass two-atom construction, and no claim on the poster
+depends on the unequal-mass case. Whether the toy/Mauna posteriors move
+materially under `normalize_per_draw=True` is UNTESTED — that check (E7) should
+precede any published claim that the framework reproduces the paper's targets.
+
+**Alternatives considered:** (a) validate against the paper's coin example using
+the GP scaffold — rejected, the example is binomial with a given data prior, so
+the scaffold has nothing to construct; (b) declare the default convention wrong
+and switch it — rejected, the M-open tension above makes this an author-level
+modeling decision, not a fix.
+
+## D61: E7 aggregation-convention sensitivity on the validated toy path — winner robust; kl_forward fragility attributed to pooled aggregation — 2026-08-11
+
+**Problem:** D60's external validation showed the shipped pooled soft-transfer
+convention fails van Bork et al.'s Target A while per-draw conventions
+reproduce it, exposing a fork (expected-posterior semantics vs M-open
+magnitudes). Before the JMP special-issue paper can cite either, the movement
+of the paper-facing toy numbers under the conventions had to be measured on the
+VALIDATED estimator path (M2bR banner: `toy_elicited` SIR; no withdrawn HMC).
+
+**Decision:** New driver `experiments/e7_convention_sensitivity.py`: reuses
+`prior_sensitivity_study.py`'s stage-IS machinery verbatim (pooled 3-seed
+prior-IS, SIR n_pred=1000, same seeds/subsample conventions), computes G for
+pw_kl_vcal (W1 primary) and kl_forward (W1 appendix), aggregates under (a)
+pooled/shipped default, (b) shipped normalize_per_draw=True (row-min), (c)
+expected-posterior (van Bork Eq. 4). Output
+`runs/e7_convention_sensitivity/{results.json, README.md}`. Anchor check: the
+pooled pw_kl_vcal tau=1 row reproduces the ratified SIR headline exactly
+(0.183/0.192/0.441/0.184).
+
+**Result:** (1) pw_kl_vcal: Sin+Linear wins under every variant at every tau;
+max movement 0.313 at tau=0.1, 0.072 at tau=1 (0.441 to 0.513), 0.001 at
+tau=10 — qualitative claims convention-robust. (2) NEW ATTRIBUTION: the
+kl_forward fragility recorded in W1/D18 is largely pooled-aggregation outlier
+sensitivity, not intrinsic to the metric: pooled collapses Sin+Linear to
+~0.000 at tau<=1 while expected-posterior yields 0.696 at tau=0.1, exactly the
+raw hard-best-match fraction (696/1000) — the tau->0 identity between
+expected-posterior aggregation and hard-win rates holds by construction and
+passed numerically. (3) Fork (OPEN, author): pooled keeps M-open magnitudes
+and continuity with all ratified numbers but fails van Bork Target A;
+expected-posterior matches their Eq.-4 semantics and rescues kl_forward but
+spends exactly one unit of credit per draw. Candidate paper stance recorded in
+the run README: treat the aggregation convention as an explicit evaluation
+dial alongside tau and occam.
+
+**Status:** E7 CLOSED as an experiment; D60 fork remains OPEN pending author
+call. Paper Case A blocked only on that call.
+
+## D65: Case A external-validation section with the aggregation fork preserved — 2026-08-12
+
+**Problem:** The Case A manuscript stub needed a self-contained external
+validation argument from the finalized D60 and D61 artifacts: an honest mapping
+to van Bork, Romeijn, and Wagenmakers; the six-decimal completely-overlapping
+target and its Laplace explanation; the non-overlapping target's dependence on
+aggregation; the validated toy-path sensitivity; the appendix-only
+`kl_forward` attribution; and a multi-parameter reach paragraph. The author has
+not yet selected a canonical aggregation convention, and the writing task did
+not authorize new compute or artifact regeneration.
+
+**Decision:** Replaced the stub in
+`docs/paper-sie-jmp/03-case-A-external-validation.md` with a mapping table and
+the full Case A account. Numerical claims use
+`runs/vanbork_external_validation/{results.json,README.md}` and
+`runs/e7_convention_sensitivity/{results.json,README.md}`, generated by
+`experiments/vanbork_external_validation.py` and
+`experiments/e7_convention_sensitivity.py`. The section keeps the author-decision
+placeholder on a standalone line at the canonical-convention slot. Surrounding
+prose states both sides of the fork and labels the E7
+evaluation-dial framing as a candidate rather than a decision. It treats
+`pw_kl_vcal` as primary and confines `kl_forward` to an appendix attribution.
+
+The multi-parameter paragraph follows W4: it labels
+`runs/viz_unification/p3_priors_canonical/` as an
+`informative`-configuration, MAP-based methods-validation check. Because that
+directory remains local and untracked, its 0.992 Sin+Linear value at \(n=50\)
+and 0.93–0.99 range across evaluated \(n\) use the committed D17-recorded
+citation pattern and name the regenerating `bistar_viz` scripts explicitly.
+They do not enter the validated `toy_elicited` SIR headline.
+
+**Alternatives considered:** Selecting pooled aggregation was rejected because
+it would preempt the author and would leave Target A unresolved. Selecting
+expected-posterior aggregation was rejected because it would also preempt the
+author and would discard the absolute divergence magnitudes used for the
+M-open signal. Treating the untracked viz-unification directory as committed
+numerical authority was rejected in favor of the authorized D17-recorded
+provenance exception. New computation, rerunning either finalized experiment,
+and modifying scripts or run artifacts were all rejected by the Case A work
+order.
+
+**Result:** The section reports Target B's progression from 0.792607 to
+0.841419 against the published 0.841420, with absolute error
+\(6.4\times10^{-7}\), and connects the agreement to cancellation of shared
+Bernoulli curvature in the hybrid Laplace approximation. It reports Target A
+as 0.000/1.000 under pooled aggregation versus the exact 0.400/0.600 under both
+per-draw routes, with convergence by \(\tau=10^{-4}\). On the validated
+`toy_elicited` SIR path, it records the 0.183/0.192/0.441/0.184 pooled anchor,
+the 0.31, 0.072, and 0.001 maximum movements, and the appendix-only
+`kl_forward` change from approximately 0.000 under pooled aggregation to 0.696
+under expected-posterior aggregation, equal to 696/1000 hard wins at the
+reported precision. This branch commits D60 and D61, which record the finalized
+compute provenance, together with D65. No experiment or artifact-generation
+command ran, and neither finalized run directory was modified.
diff --git a/docs/paper-sie-jmp/03-case-A-external-validation.md b/docs/paper-sie-jmp/03-case-A-external-validation.md
new file mode 100644
index 0000000..23caa3a
--- /dev/null
+++ b/docs/paper-sie-jmp/03-case-A-external-validation.md
@@ -0,0 +1,136 @@
+# 3. Case A: external validation against van Bork, Romeijn, and Wagenmakers
+
+van Bork, Romeijn, and Wagenmakers derive model probabilities from expected
+predictive support under an independently specified data prior. Their proposal
+cites the BI*/BMS* line as related prior work, but their closed-form examples
+were developed without reference to the present implementation. They therefore
+provide external checks on the induction and soft-transfer machinery. Because
+their examples supply the data prior directly, these checks bypass its GP
+construction.[^1]
+
+## 3.1 Correspondence of the constructions
+
+The correspondence below remains deliberately qualified. Both approaches
+evaluate models against a distribution over possible data, but they need not
+assign the same semantics to every intermediate quantity.
+
+| van Bork et al. | Present notation and computation | Qualification |
+|---|---|---|
+| Data prior, a probability over outputs specified independently of the candidate models | \(p_0(\psi)\), a distribution over data patterns | In the general framework, GP hyperpriors induce \(p_0(\psi)\). The validation examples instead insert the authors' supplied data prior, so they do not test the GP scaffold. |
+| Expected support against the data prior, expressed through Rosenkrantz-style verisimilitude | A divergence-based score \(G(\psi,\theta)\), followed by \(\bar G(\phi)\) when averaged over data patterns | Their support increases with predictive agreement; our divergence decreases with it. Additive and scale conventions therefore prevent a literal identification. |
+| Prior model probability from expected posterior probability under their Eq. 4 | Normalize model support within each draw \(\psi\), then average under \(p_0(\psi)\) | This order matches expected-posterior aggregation. It does not match pooled aggregation, which sums unnormalized support across draws before model normalization. |
+| Completely overlapping models with distinct within-model parameter priors | Hybrid \(Z_M=\int p_M(\phi)\exp\{-\bar G_M(\phi)/\tau\}\,d\phi\) | The within-model density \(p_M(\phi)\) replaces the usual Lebesgue or \(V_{\mathrm{ref}}\)-normalized reference measure, so the check concerns an extension of the standard \(Z_M\). |
+| A restricted model nested in an encompassing model | \(M_r\subset M_e\) | We adopt their nesting notation. Normalized predictive weights over a candidate roster do not thereby become set-additive probabilities over hypotheses. |
+
+## 3.2 Target B: completely overlapping models
+
+Their coin example compares \(M_x\), with
+\(\theta\sim\operatorname{Beta}(50,50)\), against \(M_z\), with
+\(\theta\sim\operatorname{Beta}(2,2)\), under a point data prior at
+\(\theta^*=1/2\). The hybrid computation approaches the published probability
+for \(M_x\) monotonically over the reported low-temperature rows:
+
+| \(\tau\) | Computed \(p(M_x)\) |
+|---:|---:|
+| \(10^{-2}\) | 0.792607 |
+| \(10^{-4}\) | 0.840781 |
+| \(10^{-6}\) | 0.841413 |
+| \(10^{-7}\) | 0.841419 |
+| Published target | 0.841420 |
+
+At the smallest reported temperature, the absolute error equals
+\(6.4\times10^{-7}\). The computed prior densities at the maximum-likelihood
+point, 7.9589 for \(M_x\) and 1.5000 for \(M_z\), also reproduce the quoted
+7.96 and 1.50 values.[^2]
+
+The agreement follows from a Laplace special case. Around the common optimum,
+
+\[
+Z_M \approx p_M(\theta^*)
+\sqrt{\frac{2\pi\tau}{G''(\theta^*)}}.
+\]
+
+Both models use the same Bernoulli family, so they share the local curvature
+\(G''(\theta^*)\). That factor and the remaining common terms cancel after
+normalization across models. As \(\tau\) approaches zero, the normalized
+hybrid scores consequently converge to the ratio of the within-model prior
+densities at \(\theta^*\). The authors' published formula thus coincides with
+the shared-family, point-data-prior, zero-temperature limit of the hybrid
+\(Z_M\). Target B supplies the first passing test of this within-model-prior
+extension, which had previously remained an open implementation question.[^2]
+
+## 3.3 Target A: aggregation changes the limiting answer
+
+The non-overlapping example assigns data-prior mass 0.4 at a Bernoulli
+proportion of 0.16 and mass 0.6 at 0.19, then compares point models at 0.15 and
+0.20. van Bork et al.'s answer assigns model probabilities 0.4 and 0.6. The
+three implemented aggregation routes behave differently:
+
+| Aggregation route | Low-temperature result | Target A verdict |
+|---|---:|---|
+| Pooled, `normalize_per_draw=False` | 0.000 / 1.000 | Fails |
+| Normalize each data-prior atom, then average | 0.400 / 0.600 | Exact |
+| `soft_transfer(..., normalize_per_draw=True)` | 0.400 / 0.600 | Exact |
+
+Both per-draw routes have converged to the exact target by
+\(\tau=10^{-4}\).[^2] The result exposes a modeling choice rather than a
+numerical defect. Pooled aggregation preserves absolute divergence magnitudes:
+a draw that every candidate fits poorly contributes less total support. That
+property carries the M-open inadequacy signal, but pooled aggregation fails
+Target A. Expected-posterior aggregation matches Eq. 4 and avoids that failure,
+but each draw must spend one full unit of credit even when every candidate fits
+poorly. The latter choice therefore discards the absolute-magnitude signal.
+
+[FORK-DECISION-PLACEHOLDER]
+
+Pending the author's decision, the E7 artifact records only a candidate
+presentation: treat aggregation as an explicit evaluation dial alongside
+\(\tau\) and `occam`, retain pooled results for continuity, report the Eq. 4
+variant in Case A, and reserve the `kl_forward` attribution for the appendix.
+That candidate does not settle the canonical convention.[^3]
+
+## 3.4 Measured sensitivity on the validated toy path
+
+E7 evaluates the fork on the validated `toy_elicited` SIR path. Under the
+primary `pw_kl_vcal` metric at \(\tau=1\), pooled aggregation gives model
+probabilities 0.183, 0.192, 0.441, and 0.184 for Linear, Sinusoidal,
+Sin+Linear, and Quadratic, respectively. This row reproduces the ratified SIR
+headline. Sin+Linear remains the highest-weight candidate under every tested
+aggregation variant and temperature. The maximum absolute movement between
+pooled and expected-posterior aggregation equals 0.31 at \(\tau=0.1\), 0.072
+at \(\tau=1\), and 0.001 at \(\tau=10\); at \(\tau=1\), the Sin+Linear
+weight changes from 0.441 to 0.513.[^3]
+
+The appendix-only `kl_forward` stress metric reveals a sharper attribution.
+With pooled aggregation, the Sin+Linear weight collapses to approximately
+0.000 for \(\tau\leq1\). Expected-posterior aggregation instead gives 0.696
+at \(\tau=0.1\), equal at the reported precision to the raw hard-best-match
+fraction of 696/1000. Expected-posterior aggregation converges to hard-win
+fractions as \(\tau\) approaches zero by construction, and the artifact's
+consistency check confirms that identity. The earlier `kl_forward` fragility
+therefore reflects pooled-aggregation sensitivity to outlying draws, not a
+property of the metric alone.[^3]
+
+## 3.5 Multi-parameter reach under methods-validation framing
+
+An earlier informative-configuration, MAP-based visualization arm provides a
+methods-validation reach check rather than a paper-facing inferential
+headline. In `runs/viz_unification/p3_priors_canonical/`, the multi-parameter
+Sin+Linear candidate receives 0.992 at \(n=50\) and remains between 0.93 and
+0.99 across all evaluated \(n\). This result shows that the same induced-prior
+machinery extends beyond the closed-form coin targets to a richer candidate
+family. It does not replace the validated `toy_elicited` SIR result above.[^4]
+
+[^1]: 🟢 peer-reviewed — van Bork, R., Romeijn, J.-W., & Wagenmakers, E.-J. (2025). Simplicity in Bayesian nested-model comparisons: Popper's disagreement with Wrinch and Jeffreys revisited. *Synthese*. https://doi.org/10.1007/s11229-025-05286-y.
+[^2]: 🟠 empirical — `experiments/vanbork_external_validation.py`; `runs/vanbork_external_validation/results.json` and `README.md`; Notes/DECISIONS.md D60.
+[^3]: 🟠 empirical — `experiments/e7_convention_sensitivity.py`; `runs/e7_convention_sensitivity/results.json` and `README.md`; Notes/DECISIONS.md D61.
+[^4]: 🟠 empirical — D17-recorded findings for the local, untracked `runs/viz_unification/p3_priors_canonical/` arm, generated by `bistar_viz/scripts/viz_unification_compare.py` through `bistar_viz/scripts/model_priors_laplace.py`. The informative-configuration, MAP-based values are 0.992 at \(n=50\) and 0.93–0.99 across all evaluated \(n\); the committed Notes/DECISIONS.md D17 record supplies their citation provenance and the `bistar_viz` scripts regenerate them.
+
+---
+*Provenance: `runs/vanbork_external_validation/` ·
+`experiments/vanbork_external_validation.py` · Notes/DECISIONS.md D60;
+`runs/e7_convention_sensitivity/` ·
+`experiments/e7_convention_sensitivity.py` · Notes/DECISIONS.md D61.
+The W4 reach check follows the D17-recorded citation path stated in [^4].
+Argument provenance: `kb/Raw/papers/important/vanBork_Romeijn_Wagenmakers_2025_subset_problem.md`
+and `kb/Wiki/Subset Problem and the Data Prior.md`.*
diff --git a/experiments/e7_convention_sensitivity.py b/experiments/e7_convention_sensitivity.py
new file mode 100644
index 0000000..6e33e61
--- /dev/null
+++ b/experiments/e7_convention_sensitivity.py
@@ -0,0 +1,137 @@
+"""
+E7 — aggregation-convention sensitivity on the VALIDATED toy path (WP0b).
+
+Question (D60 fork): the shipped soft-transfer default pools unnormalized
+Boltzmann contributions across GP draws (`normalize_per_draw=False`); van Bork,
+Romeijn & Wagenmakers' Eq. 4 semantics (prior model probability = expected
+posterior across the data prior) instead demand normalizing each draw into a
+posterior over models BEFORE averaging. D60 showed the default fails their
+Target A while the per-draw variants reproduce it. This experiment measures how
+much the PAPER-FACING toy numbers move across three aggregation variants, so
+the author can decide the fork with the cost in view.
+
+Validated basis (M2bR banner + W4/W7): `toy_elicited` config, SIR-resampled
+predictives from the pooled 3-seed prior-IS draws — the exact machinery of
+`experiments/prior_sensitivity_study.py` stage IS (functions imported from it,
+same seeds, same subsample conventions; SIR headline at tau=1 is 0.441). No
+withdrawn HMC anywhere.
+
+Variants, applied to the SAME G matrices:
+  (a) pooled      — shipped default (`_boltzmann_posterior`): mean of
+                    exp(-G/tau) over draws, normalize once.
+  (b) rowmin      — shipped `soft_transfer(..., normalize_per_draw=True)`:
+                    subtract per-draw min G, then as (a).
+  (c) expected-posterior — van Bork Eq. 4: normalize each draw's Boltzmann
+                    weights into a posterior over models, then average.
+
+Metrics: pw_kl_vcal (W1 primary) + kl_forward (W1 appendix). Taus: the study's
+grid. Outputs: runs/e7_convention_sensitivity/{results.json, README.md}.
+
+Run from the repo root:
+    python experiments/e7_convention_sensitivity.py
+"""
+
+import os, sys, json, datetime
+
+sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
+sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
+
+import numpy as np
+import torch
+
+torch.set_default_dtype(torch.float64)
+
+import prior_sensitivity_study as pss
+import fit_method_metric_comparison as fmc
+from bistar_gp import generate_toy_data
+from bistar_gp.candidates import build_toy_candidates
+
+REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
+OUT_DIR = os.path.join(REPO, "runs", "e7_convention_sensitivity")
+
+CONFIG = "toy_elicited"
+IS_SEEDS = [0, 1, 2]
+N_PRED = 1000                      # matches the ratified SIR headline run
+METRICS = ["pw_kl_vcal", "kl_forward"]
+REPORT_TAUS = ["0.1", "0.3", "1.0", "3.0", "10.0"]
+
+
+def aggregate(G, tau, variant):
+    """Three aggregation conventions over the same (n_draws x n_models) G."""
+    if variant == "pooled":                       # shipped default
+        return pss._boltzmann_posterior(G, tau)
+    if variant == "rowmin":                       # shipped npd=True semantics
+        Ge = G - G.min(axis=1, keepdims=True)
+        return pss._boltzmann_posterior(Ge, tau)
+    if variant == "expected_posterior":           # van Bork Eq. 4
+        lw = -(G - G.min(axis=1, keepdims=True)) / tau
+        w = np.exp(lw)
+        w = w / w.sum(axis=1, keepdims=True)      # per-draw posterior
+        s = w.mean(axis=0)                        # equal-weight data prior
+        return s / s.sum()
+    raise ValueError(variant)
+
+
+def main():
+    os.makedirs(OUT_DIR, exist_ok=True)
+
+    # ── Data + candidates: the study's exact conventions ───────────
+    x, y, _ = generate_toy_data()                 # thesis toy: N=20 defaults
+    x_np, y_np = x.numpy(), y.numpy()
+    x_eval = torch.tensor(
+        np.linspace(x_np.min() - 1, x_np.max() + 1, 60)).double()
+    candidate_results = []
+    for cand in build_toy_candidates():
+        cand.fit(x_np, y_np)
+        candidate_results.append(cand.predict(x_eval.numpy()))
+    names = [cr.name for cr in candidate_results]
+
+    # ── SIR predictives from pooled prior-IS (validated path) ──────
+    pc = pss.STUDY_CONFIGS[CONFIG]
+    ths, lml = pss.load_pooled_is(CONFIG, IS_SEEDS)
+    per_metric, G_by_metric, _, idx = pss._sir_bms(
+        pc, x, y, x_eval, candidate_results, ths, lml, N_PRED)
+    print(f"SIR draws: {len(np.unique(idx))}/{N_PRED} unique")
+
+    # sanity anchor: the pooled pw_kl_vcal tau=1 row must reproduce the
+    # ratified SIR headline (0.441 for Sin+Linear) within MC tolerance
+    anchor = per_metric["pw_kl_vcal"]["posteriors"]["1.0"]
+    print("anchor (pooled, pw_kl_vcal, tau=1):",
+          " ".join(f"{v:.3f}" for v in anchor))
+
+    out = {"config": CONFIG, "n_pred": N_PRED, "is_seeds": IS_SEEDS,
+           "model_names": names,
+           "generated": datetime.date.today().isoformat(),
+           "anchor_pooled_pw_kl_vcal_tau1": anchor,
+           "results": {}}
+
+    print(f"\n{'metric':<12} {'tau':<6} {'variant':<20} " +
+          " ".join(f"{n:<14}" for n in names))
+    for metric in METRICS:
+        G = G_by_metric[metric]
+        out["results"][metric] = {}
+        for tau_s in REPORT_TAUS:
+            tau = float(tau_s)
+            out["results"][metric][tau_s] = {}
+            for variant in ("pooled", "rowmin", "expected_posterior"):
+                post = aggregate(G, tau, variant)
+                out["results"][metric][tau_s][variant] = [float(v)
+                                                          for v in post]
+                print(f"{metric:<12} {tau_s:<6} {variant:<20} " +
+                      " ".join(f"{v:<14.4f}" for v in post))
+        # max movement across variants, per tau
+        mv = {t: float(np.max(np.abs(
+                np.array(out["results"][metric][t]["pooled"]) -
+                np.array(out["results"][metric][t]["expected_posterior"]))))
+              for t in REPORT_TAUS}
+        out["results"][metric]["max_abs_movement_pooled_vs_eqp"] = mv
+        print(f"{metric}: max |pooled - expected_posterior| by tau: " +
+              ", ".join(f"{t}: {v:.4f}" for t, v in mv.items()))
+
+    with open(os.path.join(OUT_DIR, "results.json"), "w") as f:
+        json.dump(out, f, indent=2)
+    print("\nSaved:", os.path.join(OUT_DIR, "results.json"))
+
+
+if __name__ == "__main__":
+    main()
diff --git a/experiments/vanbork_external_validation.py b/experiments/vanbork_external_validation.py
new file mode 100644
index 0000000..429306c
--- /dev/null
+++ b/experiments/vanbork_external_validation.py
@@ -0,0 +1,204 @@
+"""
+External validation of the BI*/BMS* scoring machinery against two closed-form
+model probabilities published by van Bork, Romeijn & Wagenmakers (2025,
+Synthese, doi:10.1007/s11229-025-05286-y), Section 4.
+
+Both targets are derived there from Rosenkrantz-style expected support against
+a "data prior", with no reference to this implementation. They therefore serve
+as independent ground truth for the induced-prior / soft-transfer half of the
+framework (the GP scaffold is not exercised: in both cases the paper GIVES the
+data prior, so we supply it directly and test the scoring).
+
+TARGET A — non-overlapping point models (their two-point example).
+  Data prior: mass 4/10 on s/n -> 0.16, mass 6/10 on s/n -> 0.19.
+  Models:     M1: theta = 0.15,  M2: theta = 0.20.
+  Their answer: p(M1) = 0.4, p(M2) = 0.6, argued via asymptotic posterior
+  model probabilities that go to 0/1 under each data-prior atom.
+  Our route: Boltzmann soft transfer p(M) ∝ sum_i w_i exp(-G(psi_i, M)/tau)
+  with G the Bernoulli KL. Tests the tau -> 0 (hard-partition) limit.
+
+TARGET B — completely overlapping models (their beta example, Fig. 1).
+  Data prior: point mass on s/n -> 1/2.
+  Models:     M_x: theta ~ beta(50,50),  M_z: theta ~ beta(2,2).
+  Their answer: the normalized ratio of prior densities at the MLE,
+  7.96 / (7.96 + 1.50) ~= 0.84 for M_x.
+  Our route: the HYBRID form of the induced model prior,
+      Z_M = integral p_M(theta) exp(-Gbar(theta)/tau) d theta,
+  i.e. Z_M with a within-model parameter prior in place of the Lebesgue /
+  V_ref reference measure. This is the "data prior + parameter hyperprior
+  hybrid" listed as an open question in CogSci Poster/OPEN_QUESTIONS.md; the
+  paper supplies a target number for it.
+
+  Analytic expectation: as tau -> 0, Laplace gives
+      Z_M ~= p_M(theta*) sqrt(2 pi tau / G''(theta*)),
+  and since both models share the Bernoulli family, G and G'' are identical
+  across them, so the Hessian factor cancels and the normalized Z ratio
+  converges to the ratio of prior densities at theta* = 1/2 -- exactly their
+  formula. Their result is thus the tau -> 0, shared-family, point-data-prior
+  special case of Z_M.
+
+Run from the repo root:
+    python experiments/vanbork_external_validation.py
+"""
+
+import os, json, datetime
+
+import numpy as np
+from scipy.stats import beta as beta_dist
+
+REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
+OUT_DIR = os.path.join(REPO, "runs", "vanbork_external_validation")
+
+TAUS = [1.0, 0.1, 0.01, 1e-3, 1e-4, 1e-5, 1e-6, 1e-7]
+
+
+def kl_bernoulli(p, q, eps=1e-300):
+    """KL( Bern(p) || Bern(q) ) in nats."""
+    p = np.clip(p, eps, 1 - eps)
+    q = np.clip(q, eps, 1 - eps)
+    return p * np.log(p / q) + (1 - p) * np.log((1 - p) / (1 - q))
+
+
+def softmax_weights(neg_energies):
+    m = np.max(neg_energies)
+    w = np.exp(neg_energies - m)
+    return w / w.sum()
+
+
+# ── TARGET A ──────────────────────────────────────────────────────────
+def target_a():
+    psi_atoms = np.array([0.16, 0.19])      # limiting relative frequencies
+    psi_mass = np.array([0.4, 0.6])         # the paper's data prior
+    models = {"M1 (theta=0.15)": 0.15, "M2 (theta=0.20)": 0.20}
+    names = list(models)
+    thetas = np.array([models[n] for n in names])
+
+    # G[i, j] = divergence from data-prior atom i to model j
+    G = np.array([[kl_bernoulli(p, t) for t in thetas] for p in psi_atoms])
+
+    rows_pooled, rows_perdraw, rows_shipped = [], [], []
+    for tau in TAUS:
+        # (a) pooled: sum unnormalized Boltzmann contributions, normalize once
+        contrib = psi_mass[:, None] * np.exp(-(G - G.min()) / tau)
+        pooled = contrib.sum(axis=0)
+        pooled = pooled / pooled.sum()
+        rows_pooled.append({"tau": tau,
+                            **{n: float(v) for n, v in zip(names, pooled)}})
+
+        # (b) per-draw: normalize each atom's Boltzmann weights into a posterior
+        #     over models FIRST, then average with the data-prior mass. This is
+        #     the paper's Eq. 4, prior model probability = expected posterior.
+        per_atom = np.exp(-(G - G.min(axis=1, keepdims=True)) / tau)
+        per_atom = per_atom / per_atom.sum(axis=1, keepdims=True)
+        perdraw = (psi_mass[:, None] * per_atom).sum(axis=0)
+        rows_perdraw.append({"tau": tau,
+                             **{n: float(v) for n, v in zip(names, perdraw)}})
+
+        # (c) exact shipped semantics of bms_star.soft_transfer with
+        #     normalize_per_draw=True: subtract the per-row MINIMUM (no row
+        #     renormalization), weight by atom mass, then normalize once.
+        shipped = (psi_mass[:, None] *
+                   np.exp(-(G - G.min(axis=1, keepdims=True)) / tau)).sum(axis=0)
+        shipped = shipped / shipped.sum()
+        rows_shipped.append({"tau": tau,
+                             **{n: float(v) for n, v in zip(names, shipped)}})
+    return {"names": names, "target": {"M1 (theta=0.15)": 0.4,
+                                       "M2 (theta=0.20)": 0.6},
+            "G": G.tolist(), "rows": rows_perdraw,
+            "rows_pooled": rows_pooled, "rows_perdraw": rows_perdraw,
+            "rows_shipped_npd_true": rows_shipped}
+
+
+# ── TARGET B ──────────────────────────────────────────────────────────
+def target_b():
+    psi_star = 0.5                          # data prior: spike at s/n -> 1/2
+    priors = {"M_x beta(50,50)": (50.0, 50.0), "M_z beta(2,2)": (2.0, 2.0)}
+    names = list(priors)
+
+    # their published densities at the MLE and the resulting weight
+    dens = {n: float(beta_dist.pdf(psi_star, a, b))
+            for n, (a, b) in priors.items()}
+    dens_ratio_weight = dens[names[0]] / (dens[names[0]] + dens[names[1]])
+
+    # hybrid Z_M = ∫ p_M(theta) exp(-G(theta)/tau) d theta, on a fine grid
+    # union of a coarse global grid and a dense grid around theta*,
+    # so the exp(-G/tau) peak (width ~ sqrt(tau)/2) stays resolved
+    theta = np.unique(np.concatenate([
+        np.linspace(1e-6, 1 - 1e-6, 200001),
+        psi_star + np.linspace(-0.02, 0.02, 400001),
+    ]))
+    theta = theta[(theta > 0) & (theta < 1)]
+    G = kl_bernoulli(psi_star, theta)       # same G for both models
+    rows = []
+    for tau in TAUS:
+        integrand_core = np.exp(-(G - G.min()) / tau)
+        Z = {}
+        for n, (a, b) in priors.items():
+            trapz = getattr(np, "trapezoid", np.trapz)
+            Z[n] = float(trapz(beta_dist.pdf(theta, a, b) * integrand_core,
+                               theta))
+        tot = sum(Z.values())
+        rows.append({"tau": tau, **{n: Z[n] / tot for n in names}})
+    return {"names": names,
+            "published_densities_at_mle": dens,
+            "published_weight_Mx": dens_ratio_weight,
+            "target": {names[0]: dens_ratio_weight,
+                       names[1]: 1 - dens_ratio_weight},
+            "rows": rows}
+
+
+def main():
+    os.makedirs(OUT_DIR, exist_ok=True)
+    a, b = target_a(), target_b()
+
+    print("=" * 74)
+    print("TARGET A — non-overlapping point models (paper: 0.4 / 0.6)")
+    print("=" * 74)
+    print(f"  divergences G[atom, model]:\n{np.array(a['G'])}")
+    for label, key in [("(a) POOLED  (sum, then normalize once)", "rows_pooled"),
+                       ("(b) PER-DRAW (normalize per atom, then average) "
+                        "= paper Eq. 4", "rows_perdraw"),
+                       ("(c) SHIPPED soft_transfer, normalize_per_draw=True",
+                        "rows_shipped_npd_true")]:
+        print(f"\n  {label}")
+        print("    tau".ljust(14) + "".join(n.ljust(22) for n in a["names"]))
+        for r in a[key]:
+            print(f"    {r['tau']:<10.3g}" +
+                  "".join(f"{r[n]:<22.6f}" for n in a["names"]))
+        print("    paper target:".ljust(14) +
+              "".join(f"{a['target'][n]:<22.6f}" for n in a["names"]))
+
+    print()
+    print("=" * 74)
+    print("TARGET B — completely overlapping beta models (paper: ~0.84 / 0.16)")
+    print("=" * 74)
+    print("  prior densities at MLE 0.5:",
+          {k: round(v, 4) for k, v in b["published_densities_at_mle"].items()},
+          "(paper quotes 7.96 and 1.50)")
+    print(f"  paper weight for M_x: {b['published_weight_Mx']:.6f}")
+    hdr = "  tau".ljust(12) + "".join(n.ljust(22) for n in b["names"])
+    print(hdr)
+    for r in b["rows"]:
+        print(f"  {r['tau']:<10.3g}" +
+              "".join(f"{r[n]:<22.6f}" for n in b["names"]))
+    print("  paper target:".ljust(12) +
+          "".join(f"{b['target'][n]:<22.6f}" for n in b["names"]))
+
+    # convergence report
+    a_err = abs(a["rows"][-1][a["names"][0]] - a["target"][a["names"][0]])
+    b_err = abs(b["rows"][-1][b["names"][0]] - b["target"][b["names"][0]])
+    print()
+    print(f"  |ours - paper| at tau={TAUS[-1]}:  A = {a_err:.2e}   B = {b_err:.2e}")
+
+    out = {"source": "van Bork, Romeijn & Wagenmakers 2025, Synthese, "
+                     "doi:10.1007/s11229-025-05286-y, Section 4",
+           "generated": datetime.date.today().isoformat(),
+           "taus": TAUS, "target_a": a, "target_b": b,
+           "abs_error_at_min_tau": {"A": a_err, "B": b_err}}
+    with open(os.path.join(OUT_DIR, "results.json"), "w") as f:
+        json.dump(out, f, indent=2)
+    print("\nSaved:", os.path.join(OUT_DIR, "results.json"))
+
+
+if __name__ == "__main__":
+    main()

