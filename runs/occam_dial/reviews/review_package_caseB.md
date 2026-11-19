Review the attached branch diff for the BI*/BMS*-GP paper case B (occam dial).
Verdict: APPROVE or REVISE. Findings as a numbered list:
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

CASE B WORK ORDER (what was commissioned; §2 of the HANDOFF, verbatim):
Scope: E4 figure + E6 check + section `04-case-B-occam-dial.md`.
1. `experiments/occam_dial_figure.py`: side-by-side model posteriors under
   occam=False vs occam=True from the MAP-based viz_unification artifacts
   (`runs/viz_unification/p3_priors_canonical/`, `p1_priors_lap_occam/`;
   D17 numbers 0.934 vs 0.693 at n=50), nesting relations annotated
   (Linear ⊂ Sin+Linear via A=0; Sinusoidal ⊂ Sin+Linear via b=c=0;
   Quadratic not nested). Output `runs/occam_dial/`.
2. `experiments/e6_nesting_monotonicity.py`: verify min_φ Ḡ(encompassing) ≤
   min_φ Ḡ(restricted) for both nested pairs across a τ-relevant grid, using
   the existing Ḡ/multi-start machinery in `bistar_gp/laplace_evidence.py`
   (do NOT reimplement). Output JSON + a one-paragraph resolution of the
   `kb/Wiki/REVIEW_AND_VET.md` "Nesting monotonicity" entry (edit that file:
   mark resolved with the numbers).
3. Flesh out `docs/paper-sie-jmp/04-case-B-occam-dial.md` from the stub +
   `kb/Wiki/Subset Problem and the Data Prior.md` (W4 framing discipline).
Acceptance: figure regenerates; E6 verdict stated either way (a violation is
a REPORTABLE finding, not a failure); DECISIONS entry present.

NOTE for reviewers: the kb/Wiki/REVIEW_AND_VET.md edit is part of the
commissioned work order (item 2), so its presence in the diff is in scope.
The driver-verified anchor context: runs/viz_unification/ is a LOCAL untracked
directory (PNGs + delta_table.md + logs only), so the diff's scripts recompute
arm numbers through bistar_viz/bistar_gp machinery rather than reading
committed JSONs; delta_table anchors at n=50: p3 Sin+Linear 0.992, p1 Linear
0.534 / Sin+Linear 0.382, p2 Linear 0.507 / Sin+Linear 0.465. The D17 legacy
contradiction pair (trajectory Sin+Linear 0.934, occam hard-OFF; priors script
Linear 0.693, occam hard-ON) comes from Notes/DECISIONS.md D17 and may be
quoted with that provenance without recomputation.

=== SECTION FILE (docs/paper-sie-jmp/04-case-B-occam-dial.md) ===
# 4. Case B: the occam flag as the Popper/Wrinch-Jeffreys dial

van Bork, Romeijn, and Wagenmakers restate Popper's objection to the
Wrinch-Jeffreys treatment of nested models: if M_r ⊂ M_e, assigning more prior
probability to the restricted model M_r violates the encompassing-model
constraint. Wrinch and Jeffreys instead permit a simplicity preference for
M_r. Their analysis motivates a direct question for the induced model prior
Z_M: which position does its reference measure encode?[^1]

The toy roster contains two relevant restrictions. Linear follows from
Sin+Linear at A=0, and Sinusoidal follows at b=c=0. Quadratic does not form a
restriction of Sin+Linear. The `occam` flag changes the measure used in Z_M:
`occam=False` integrates against raw Lebesgue measure, following the canonical
BI* convention, whereas `occam=True` divides by the reference volume
V_ref.[^2]

## 4.1 An attribution ladder, not a two-arm ablation

Figure 4 recomputes the three D17 attribution arms at n=50 and τ=0.3, with the
`informative` GP configuration and a MAP predictive. These values serve
methods validation and legacy comparison. They do not provide paper-facing
posterior inference about which model generated the data.[^3]

![Three-arm Occam-dial comparison at n=50](../../runs/occam_dial/occam_dial.png)

**Figure 4.** Induced model priors for the nested toy roster. The p1 and p3
panels differ in both the Z_M estimator and the `occam` convention, so the p2
panel prevents a conflated attribution. Replacing pure Laplace with IS while
retaining `occam=True` changes the Linear and Sin+Linear probabilities from
0.534121 and 0.382052 in p1 to 0.506877 and 0.464791 in p2. Changing only the
convention in the next step gives 0.007040 and 0.991758 in p3. The estimator
change narrows the gap; removing the V_ref normalization decides the verdict.
The dial figure argues about the `occam` convention's effect, not about which
model generated the data.

The earlier contradiction supplies useful historical context but not new
evidence. D17 records 0.934 for Sin+Linear in the legacy trajectory script and
0.693 for Linear in the legacy priors script, which hard-coded
`occam=True`. The pinned-commit extraction in
`viz_unification_compare.py` regenerates those legacy arms. The new figure
does not invoke or parse that extraction.[^2]

## 4.2 E6: best achievable divergence under exact nesting

As τ approaches zero, the leading contribution to Z_M comes from
min_φ Ḡ(φ). The reachable-set argument therefore requires

\[
\min_{\phi}\bar G(M_e) \leq \min_{\phi}\bar G(M_r).
\]

Different parameter dimensions prevent a Lebesgue-monotonicity argument in
parameter space. E6 instead tests the two exact restrictions in data space.
The visualization box uses A ≥ 0.01 as a numerical cutoff, so E6 alone extends
the encompassing amplitude bound to A ≥ 0. All other bounds match the
visualization arms. The restricted optimum seeds the encompassing multi-start
optimization, and the package divergence calculation reproduces the restricted
value exactly at its embedding, within the declared 10^-10 tolerance.[^4]

For this n=50, `informative`-configuration, MAP-based averaged GP, E6
obtains min_φ Ḡ=0.045516783 for Sin+Linear, 2.424774370 for Linear, and
2.546229649 for Sinusoidal. The encompassing model improves on the restrictions
by 2.379257587 and 2.500712865, respectively. Both numerical inequalities
therefore hold by margins far above the 10^-8 comparison tolerance. This result
supports the reachable-set claim for the tested GP and parameterization; it
does not prove the claim for every data prior or parameterization.[^4]

Finite τ separates the two reference measures. One IS call per model evaluates
161 temperatures from 0.031623 through 316.227766. With `occam=False`,
Sin+Linear retains the larger pairwise Z_M throughout that grid, so neither
nested pair crosses. With `occam=True`, Linear overtakes Sin+Linear at the
log-interpolated location τ=0.295184, bracketed by 0.281838 and 0.298538.
Sinusoidal overtakes at τ=1.484355, bracketed by 1.412538 and 1.496236. Thus
low temperature supports Popper's encompassing constraint in both conventions
for this example, while V_ref normalization permits the finite-temperature
simplicity preference associated with Wrinch and Jeffreys.[^4]

The two controls should therefore remain explicit. Temperature governs how
strongly best achievable divergence dominates integrated compatibility, while
`occam` selects raw or volume-normalized reference measure. Their joint
sensitivity describes the Popper/Wrinch-Jeffreys disagreement without turning
a methods-validation example into a claim about model truth.

[^1]: 🟢 peer-reviewed — van Bork, Romeijn, and Wagenmakers (2025), *Synthese*, doi:10.1007/s11229-025-05286-y.
[^2]: 🟠 empirical — `Notes/DECISIONS.md` D3, D5, and D17; legacy regeneration through `bistar_viz/scripts/viz_unification_compare.py` at pinned commit `a87356a`.
[^3]: 🟠 empirical — `experiments/occam_dial_figure.py`; `runs/occam_dial/figure_results.json`.
[^4]: 🟠 empirical — `experiments/e6_nesting_monotonicity.py`; `runs/occam_dial/e6_results.json`.

---
*Provenance: `runs/occam_dial/` · `experiments/occam_dial_figure.py` ·
`experiments/e6_nesting_monotonicity.py` · `Notes/DECISIONS.md` D17, D62.*


=== RUN README(s) (runs/occam_dial/) ===
# Case B: Occam dial and nesting monotonicity

Regenerate from the repository root:

```bash
python experiments/occam_dial_figure.py
python experiments/e6_nesting_monotonicity.py
```

Both scripts use local CPU computation only. They construct the n=50 averaged GP with `PRIOR_CONFIGS["informative"]`, `gp_method="map"`, data seed 42, 80 evaluation points over [-10, 10], and the primary `pw_kl_vcal` metric. MAP retains one GP predictive. The scripts import the shared construction from `bistar_viz/scripts/_viz_spaces.py` and the existing evidence machinery from `bistar_gp/laplace_evidence.py`.

## Figure computation

`occam_dial.png` and `figure_results.json` use τ=0.3, IS seed 0, n_is=40,000, five seeded perturbations per legacy start, and the canonical visualization parameter boxes. The optional `runs/viz_unification/delta_table.md` only supplies a cross-check when present.

The anchor tolerance equals 0.003 in absolute model probability. The published anchors were rounded to three decimals, and the remaining allowance covers small cross-platform optimizer differences. The tolerance remains well below the 0.042 p2 Linear versus Sin+Linear gap.

Fresh n=50 posteriors:

- `p1_priors_lap_occam`: Linear 0.534121, Sinusoidal 0.075747, Sin+Linear 0.382052, Quadratic 0.008080
- `p2_priors_is_occam`: Linear 0.506877, Sinusoidal 0.020499, Sin+Linear 0.464791, Quadratic 0.007834
- `p3_priors_canonical`: Linear 0.007040, Sinusoidal 0.001093, Sin+Linear 0.991758, Quadratic 0.000109

The optional D17 table cross-check was available.

The D17-recorded legacy 0.934 and 0.693 values provide historical context only. `bistar_viz/scripts/viz_unification_compare.py`, with pinned legacy commit `a87356a`, regenerates those legacy arms. Neither new script invokes that git-based extraction path.

## E6 computation

E6 uses 161 log-spaced τ values from 10^-1.5 through 10^2.5, IS seed 0, n_is=100,000, and the same five perturbations per start. One `is_log_Z_Mx` call per model computes the full raw sweep; the package's `_log_reference_volume` helper supplies the occam-normalized sweep. The visualization box uses A >= 0.01 for numerical plotting. E6 alone extends the encompassing Sin+Linear box to A >= 0 so Linear at A=0 forms an exact restriction. All other bounds match the canonical visualization boxes. The embedded restricted optima seed the encompassing multi-start optimization. IS uses interior perturbed starts plus the best encompassing optimum, which avoids flat boundary-Hessian components without changing the integral.

The min-Ḡ comparison tolerance equals 1e-8 in Ḡ units. It only classifies floating-point near-ties and remains many orders of magnitude below the observed margins. τ crossings use linear interpolation in log10(τ) inside the reported adjacent grid bracket; the bracket, rather than extra decimal places in the interpolant, provides the resolution statement.

Fresh E6 results:

- `Linear_within_Sin+Linear`: min Ḡ(restricted)=2.424774370, min Ḡ(encompassing)=0.045516783, margin=2.379257587, holds=True.
  - `occam_false`: no crossing on the grid.
  - `occam_true`: 0.295184 within [0.281838, 0.298538].
- `Sinusoidal_within_Sin+Linear`: min Ḡ(restricted)=2.546229649, min Ḡ(encompassing)=0.045516783, margin=2.500712865, holds=True.
  - `occam_false`: no crossing on the grid.
  - `occam_true`: 1.484355 within [1.412538, 1.496236].

E6 verdict: Both numerical min-Ḡ inequalities hold on the n=50 informative-config, MAP-based toy GP. E6 supports the reachable-set claim for these two exact restrictions, while the finite-τ Z_M ordering still depends on the reference-measure convention.

## Files

- `occam_dial.png`: E4 attribution-ladder figure, kept below 2 MB.
- `figure_results.json`: all freshly computed E4 arm values and anchor checks.
- `e6_results.json`: min-Ḡ optima, exact-embedding checks, both Z_M conventions, ESS diagnostics, the full τ grid, and crossing brackets.


=== RUN JSON summary ===
runs/occam_dial/figure_results.json (FULL):
{
  "anchor_checks": {
    "p1_priors_lap_occam": {
      "Linear": {
        "absolute_error": 0.00012117610177397875,
        "actual": 0.534121176101774,
        "expected": 0.534,
        "passed": true
      },
      "Sin+Linear": {
        "absolute_error": 5.16271444940819e-05,
        "actual": 0.3820516271444941,
        "expected": 0.382,
        "passed": true
      }
    },
    "p2_priors_is_occam": {
      "Linear": {
        "absolute_error": 0.0001234753523423615,
        "actual": 0.5068765246476576,
        "expected": 0.507,
        "passed": true
      },
      "Sin+Linear": {
        "absolute_error": 0.00020914428525986573,
        "actual": 0.46479085571474016,
        "expected": 0.465,
        "passed": true
      }
    },
    "p3_priors_canonical": {
      "Sin+Linear": {
        "absolute_error": 0.00024230569270233815,
        "actual": 0.9917576943072977,
        "expected": 0.992,
        "passed": true
      }
    }
  },
  "anchor_tolerance_absolute_probability": 0.003,
  "arms": {
    "p1_priors_lap_occam": {
      "ess": {
        "Linear": null,
        "Quadratic": null,
        "Sin+Linear": null,
        "Sinusoidal": null
      },
      "estimator": "laplace",
      "log_Z_M": {
        "Linear": -15.165401538600314,
        "Quadratic": -19.3566141369075,
        "Sin+Linear": -15.500468524289005,
        "Sinusoidal": -17.118624784446126
      },
      "model_posterior": {
        "Linear": 0.534121176101774,
        "Quadratic": 0.008080147573789803,
        "Sin+Linear": 0.3820516271444941,
        "Sinusoidal": 0.07574704917994204
      },
      "occam": true
    },
    "p2_priors_is_occam": {
      "ess": {
        "Linear": 11363.35016462474,
        "Quadratic": 9409.970831256755,
        "Sin+Linear": 3180.462456067874,
        "Sinusoidal": 680.849114003975
      },
      "estimator": "is",
      "log_Z_M": {
        "Linear": -15.174751675190652,
        "Quadratic": -19.344539317824736,
        "Sin+Linear": -15.261431576239175,
        "Sinusoidal": -18.382664063985942
      },
      "model_posterior": {
        "Linear": 0.5068765246476576,
        "Quadratic": 0.00783405135143996,
        "Sin+Linear": 0.46479085571474016,
        "Sinusoidal": 0.020498568286162287
      },
      "occam": true
    },
    "p3_priors_canonical": {
      "ess": {
        "Linear": 11363.35016462474,
        "Quadratic": 9409.970831256755,
        "Sin+Linear": 3180.462456067874,
        "Sinusoidal": 680.849114003975
      },
      "estimator": "is",
      "log_Z_M": {
        "Linear": -11.485872221076717,
        "Quadratic": -15.655659863710799,
        "Sin+Linear": -6.538003940835886,
        "Sinusoidal": -13.348115882696586
      },
      "model_posterior": {
        "Linear": 0.007040016665579024,
        "Quadratic": 0.00010880727236574364,
        "Sin+Linear": 0.9917576943072977,
        "Sinusoidal": 0.001093481754757355
      },
      "occam": false
    }
  },
  "artifact": "occam_dial_figure",
  "case": "B",
  "interpretation_scope": "informative-config, MAP-based methods-validation and legacy-comparison material; the comparison evaluates the occam convention, not which model generated the data",
  "legacy_context_not_recomputed": {
    "legacy_priors_Linear_n50": 0.693,
    "legacy_trajectory_Sin+Linear_n50": 0.934,
    "pinned_legacy_commit": "a87356a",
    "regeneration_script": "bistar_viz/scripts/viz_unification_compare.py",
    "source": "Notes/DECISIONS.md D17"
  },
  "optional_local_crosscheck": {
    "available": true,
    "checks": {
      "p1_priors_lap_occam": {
        "absolute_errors": {
          "Linear": 0.00012117610177397875,
          "Quadratic": 8.014757378980303e-05,
          "Sin+Linear": 5.16271444940819e-05,
          "Sinusoidal": 0.0002529508200579539
        },
        "found": true,
        "passed": true,
        "table_values": {
          "Linear": 0.534,
          "Quadratic": 0.008,
          "Sin+Linear": 0.382,
          "Sinusoidal": 0.076
        }
      },
      "p2_priors_is_occam": {
        "absolute_errors": {
          "Linear": 0.0001234753523423615,
          "Quadratic": 0.00016594864856003984,
          "Sin+Linear": 0.00020914428525986573,
          "Sinusoidal": 0.0004985682861622862
        },
        "found": true,
        "passed": true,
        "table_values": {
          "Linear": 0.507,
          "Quadratic": 0.008,
          "Sin+Linear": 0.465,
          "Sinusoidal": 0.02
        }
      },
      "p3_priors_canonical": {
        "absolute_errors": {
          "Linear": 4.0016665579023676e-05,
          "Quadratic": 0.00010880727236574364,
          "Sin+Linear": 0.00024230569270233815,
          "Sinusoidal": 9.3481754757355e-05
        },
        "found": true,
        "passed": true,
        "table_values": {
          "Linear": 0.007,
          "Quadratic": 0.0,
          "Sin+Linear": 0.992,
          "Sinusoidal": 0.001
        }
      }
    },
    "path": "runs/viz_unification/delta_table.md"
  },
  "provenance": {
    "data_seed": 42,
    "evidence": "bistar_gp/laplace_evidence.py",
    "gp_config": "informative",
    "gp_method": "map",
    "gp_predictives_retained": 1,
    "is_seed": 0,
    "metric": "pw_kl_vcal",
    "n": 50,
    "n_draws_requested": 150,
    "n_is": 40000,
    "n_perturb": 5,
    "spaces": "bistar_viz/scripts/_viz_spaces.py:canonical_spaces",
    "tau": 0.3,
    "x_eval_count": 80,
    "x_eval_range": [
      -10.0,
      10.0
    ]
  },
  "schema_version": 1
}


runs/occam_dial/e6_results.json (ABRIDGED: long numeric arrays elided with first3/last3/min/max; full file in repo):
{
 "artifact": "e6_nesting_monotonicity",
 "case": "B",
 "model_sweeps": {
  "Linear": {
   "is_calls": 1,
   "log_reference_volume": 3.6888794541139367,
   "occam_false": {
    "ess": {
     "__abridged_array__": "161 floats",
     "first3": [
      22358.460489324258,
      22877.203247248406,
      23366.738899135617
     ],
     "last3": [
      41787.646449387765,
      42461.61424369554,
      43112.12888745887
     ],
     "min": 14903.232260820918,
     "max": 43112.12888745887
    },
    "log_Z_M": {
     "__abridged_array__": "161 floats",
     "first3": [
      -82.32245983423631,
      -77.97555999123718,
      -73.86859013935329
     ],
     "last3": [
      2.974025922025577,
      3.004527577780113,
      3.0341005701083095
     ],
     "min": -82.32245983423631,
     "max": 3.0341005701083095
    },
    "min_ess": 14903.232260820918
   },
   "occam_true": {
    "derived_from_raw_with": "bistar_gp.laplace_evidence._log_reference_volume",
    "ess": {
     "__abridged_array__": "161 floats",
     "first3": [
      22358.460489324258,
      22877.203247248406,
      23366.738899135617
     ],
     "last3": [
      41787.646449387765,
      42461.61424369554,
      43112.12888745887
     ],
     "min": 14903.232260820918,
     "max": 43112.12888745887
    },
    "log_Z_M": {
     "__abridged_array__": "161 floats",
     "first3": [
      -86.01133928835024,
      -81.6644394453511,
      -77.55746959346722
     ],
     "last3": [
      -0.7148535320883598,
      -0.6843518763338237,
      -0.6547788840056272
     ],
     "min": -86.01133928835024,
     "max": -0.6547788840056272
    },
    "min_ess": 14903.232260820918
   }
  },
  "Sin+Linear": {
   "is_calls": 1,
   "log_reference_volume": 8.725429638073964,
   "occam_false": {
    "ess": {
     "__abridged_array__": "161 floats",
     "first3": [
      9784.141295821242,
      9854.426660436255,
      9838.264221064028
     ],
     "last3": [
      38938.01855407652,
      39680.895364414806,
      40398.81858414094
     ],
     "min": 830.8870807818723,
     "max": 40398.81858414094
    },
    "log_Z_M": {
     "__abridged_array__": "161 floats",
     "first3": [
      -13.67298197519908,
      -13.447511767413268,
      -13.226383133220434
     ],
     "last3": [
      7.9407587544467635,
      7.97508221701081,
      8.00827630767664
     ],
     "min": -13.67298197519908,
     "max": 8.00827630767664
    },
    "min_ess": 830.8870807818723
   },
   "occam_true": {
    "derived_from_raw_with": "bistar_gp.laplace_evidence._log_reference_volume",
    "ess": {
     "__abridged_array__": "161 floats",
     "first3": [
      9784.141295821242,
      9854.426660436255,
      9838.264221064028
     ],
     "last3": [
      38938.01855407652,
      39680.895364414806,
      40398.81858414094
     ],
     "min": 830.8870807818723,
     "max": 40398.81858414094
    },
    "log_Z_M": {
     "__abridged_array__": "161 floats",
     "first3": [
      -22.398411613273044,
      -22.17294140548723,
      -21.9518127712944
     ],
     "last3": [
      -0.7846708836272,
      -0.7503474210631538,
      -0.7171533303973234
     ],
     "min": -22.398411613273044,
     "max": -0.7171533303973234
    },
    "min_ess": 830.8870807818723
   }
  },
  "Sinusoidal": {
   "is_calls": 1,
   "log_reference_volume": 5.034548181289354,
   "occam_false": {
    "ess": {
     "__abridged_array__": "161 floats",
     "first3": [
      1734.0482913807937,
      1817.3570432452789,
      1895.0850090273177
     ],
     "last3": [
      53296.69622494243,
      53296.897753581645,
      53295.86858528673
     ],
     "min": 1372.8868832793878,
     "max": 53296.897753581645
    },
    "log_Z_M": {
     "__abridged_array__": "161 floats",
     "first3": [
      -89.45840667787704,
      -84.84502360523015,
      -80.48381496312514
     ],
     "last3": [
      4.914919470087712,
      4.921671168389681,
      4.9280581057723385
     ],
     "min": -89.45840667787704,
     "max": 4.9280581057723385
    },
    "min_ess": 1372.8868832793878
   },
   "occam_true": {
    "derived_from_raw_with": "bistar_gp.laplace_evidence._log_reference_volume",
    "ess": {
     "__abridged_array__": "161 floats",
     "first3": [
      1734.0482913807937,
      1817.3570432452789,
      1895.0850090273177
     ],
     "last3": [
      53296.69622494243,
      53296.897753581645,
      53295.86858528673
     ],
     "min": 1372.8868832793878,
     "max": 53296.897753581645
    },
    "log_Z_M": {
     "__abridged_array__": "161 floats",
     "first3": [
      -94.49295485916639,
      -89.8795717865195,
      -85.5183631444145
     ],
     "last3": [
      -0.11962871120164209,
      -0.11287701289967345,
      -0.10649007551701573
     ],
     "min": -94.49295485916639,
     "max": -0.10649007551701573
    },
    "min_ess": 1372.8868832793878
   }
  }
 },
 "nested_pairs": {
  "Linear_within_Sin+Linear": {
   "Z_M_ordering": {
    "occam_false": {
     "crossings": [],
     "delta_at_tau_max": 4.974175737568331,
     "delta_at_tau_min": 68.64947785903723,
     "delta_definition": "log Z_M(encompassing) - log Z_M(restricted)",
     "delta_log_Z": {
      "__abridged_array__": "161 floats",
      "first3": [
       68.64947785903723,
       64.5280482238239,
       60.64220700613285
      ],
      "last3": [
       4.966732832421187,
       4.970554639230697,
       4.974175737568331
      ],
      "min": 2.970459017312912,
      "max": 68.64947785903723
     },
     "minimum_absolute_delta_grid_point": {
      "delta_log_Z": 2.970459017312912,
      "tau": 0.7498942093324559
     },
     "winner_at_tau_max": "encompassing",
     "winner_at_tau_min": "encompassing"
    },
    "occam_true": {
     "crossings": [
      {
       "delta_log_Z_bracket": [
        0.2842881798814876,
        -0.06941931223643749
       ],
       "lower_grid_index": 38,
       "tau_bracket": [
        0.2818382931264454,
        0.298538261891796
       ],
       "tau_log_interpolated": 0.29518443393426885,
       "winner_above": "restricted",
       "winner_below": "encompassing"
      }
     ],
     "delta_at_tau_max": -0.0623744463916962,
     "delta_at_tau_min": 63.6129276750772,
     "delta_definition": "log Z_M(encompassing) - log Z_M(restricted)",
     "delta_log_Z": {
      "__abridged_array__": "161 floats",
      "first3": [
       63.6129276750772,
       59.49149803986388,
       55.60565682217282
      ],
      "last3": [
       -0.06981735153884028,
       -0.06599554472933011,
       -0.0623744463916962
      ],
      "min": -2.066091166647116,
      "max": 63.6129276750772
     },
     "minimum_absolute_delta_grid_point": {
      "delta_log_Z": -0.0623744463916962,
      "tau": 316.22776601683796
     },
     "winner_at_tau_max": "restricted",
     "winner_at_tau_min": "encompassing"
    }
   },
   "embedded_restricted_optimum": {
    "Gbar": 2.4247743701716202,
    "absolute_Gbar_error": 0.0,
    "passed": true,
    "phi": {
     "A": 0.0,
     "b": 0.27577151111106163,
     "c": 0.004158945541476323,
     "omega": 1.0,
     "phi": 0.0
    },
    "tolerance": 1e-10
   },
   "encompassing": {
    "min_Gbar": 0.04551678343894516,
    "n_multistarts": 38,
    "phi_min": {
     "A": 1.0224846975427644,
     "b": 0.25015173054273654,
     "c": -0.0034811798627464555,
     "omega": 0.9986522565255535,
     "phi": 0.07582150264521711
    }
   },
   "encompassing_model": "Sin+Linear",
   "inequality": "min_\u03c6 \u1e20(encompassing) \u2264 min_\u03c6 \u1e20(restricted)",
   "inequality_holds": true,
   "margin_restricted_minus_encompassing": 2.379257586732675,
   "minimum_is_tau_independent": true,
   "restricted": {
    "min_Gbar": 2.4247743701716202,
    "n_multistarts": 18,
    "phi_min": {
     "a": 0.27577151111106163,
     "b": 0.004158945541476323
    }
   },
   "restricted_model": "Linear",
   "restriction": "A=0; encompassing b and c equal restricted a and b",
   "tolerance": 1e-08,
   "verified_for_tau_count": 161
  },
  "Sinusoidal_within_Sin+Linear": {
   "Z_M_ordering": {
    "occam_false": {
     "crossings": [],
     "delta_at_tau_max": 3.0802182019043016,
     "delta_at_tau_min": 75.78542470267796,
     "delta_definition": "log Z_M(encompassing) - log Z_M(restricted)",
     "delta_log_Z": {
      "__abridged_array__": "161 floats",
      "first3": [
       75.78542470267796,
       71.3975118378169,
       67.2574318299047
      ],
      "last3": [
       3.0258392843590514,
       3.053411048621129,
       3.0802182019043016
      ],
      "min": 1.2938117958184012,
      "max": 75.78542470267796
     },
     "minimum_absolute_delta_grid_point": {
      "delta_log_Z": 1.2938117958184012,
      "tau": 11.88502227437019
     },
     "winner_at_tau_max": "encompassing",
     "winner_at_tau_min": "encompassing"
    },
    "occam_true": {
     "crossings": [
      {
       "delta_log_Z_bracket": [
        0.03435390158246321,
        -0.005522325686383667
       ],
       "lower_grid_index": 66,
       "tau_bracket": [
        1.4125375446227548,
        1.4962356560944337
       ],
       "tau_log_interpolated": 1.4843551834764874,
       "winner_above": "restricted",
       "winner_below": "encompassing"
      }
     ],
     "delta_at_tau_max": -0.6106632548803077,
     "delta_at_tau_min": 72.09454324589335,
     "delta_definition": "log Z_M(encompassing) - log Z_M(restricted)",
     "delta_log_Z": {
      "__abridged_array__": "161 floats",
      "first3": [
       72.09454324589335,
       67.70663038103228,
       63.566550373120094
      ],
      "last3": [
       -0.665042172425558,
       -0.6374704081634803,
       -0.6106632548803077
      ],
      "min": -2.397069660966208,
      "max": 72.09454324589335
     },
     "minimum_absolute_delta_grid_point": {
      "delta_log_Z": -0.005522325686383667,
      "tau": 1.4962356560944337
     },
     "winner_at_tau_max": "restricted",
     "winner_at_tau_min": "encompassing"
    }
   },
   "embedded_restricted_optimum": {
    "Gbar": 2.546229648543252,
    "absolute_Gbar_error": 0.0,
    "passed": true,
    "phi": {
     "A": 3.0262248187297827,
     "b": 0.0,
     "c": 0.0,
     "omega": 0.1,
     "phi": 0.003147503569407698
    },
    "tolerance": 1e-10
   },
   "encompassing": {
    "min_Gbar": 0.04551678343894516,
    "n_multistarts": 38,
    "phi_min": {
     "A": 1.0224846975427644,
     "b": 0.25015173054273654,
     "c": -0.0034811798627464555,
     "omega": 0.9986522565255535,
     "phi": 0.07582150264521711
    }
   },
   "encompassing_model": "Sin+Linear",
   "inequality": "min_\u03c6 \u1e20(encompassing) \u2264 min_\u03c6 \u1e20(restricted)",
   "inequality_holds": true,
   "margin_restricted_minus_encompassing": 2.5007128651043065,
   "minimum_is_tau_independent": true,
   "restricted": {
    "min_Gbar": 2.546229648543252,
    "n_multistarts": 30,
    "phi_min": {
     "A": 3.0262248187297827,
     "omega": 0.1,
     "phi": 0.003147503569407698
    }
   },
   "restricted_model": "Sinusoidal",
   "restriction": "b=c=0",
   "tolerance": 1e-08,
   "verified_for_tau_count": 161
  }
 },
 "provenance": {
  "Z_M_estimator": "bistar_gp.laplace_evidence.is_log_Z_Mx",
  "data_seed": 42,
  "gp_config": "informative",
  "gp_method": "map",
  "gp_predictives_retained": 1,
  "is_seed": 0,
  "metric": "pw_kl_vcal",
  "n": 50,
  "n_draws_requested": 150,
  "n_is": 100000,
  "n_perturb": 5,
  "occam_normalization": "bistar_gp.laplace_evidence._log_reference_volume",
  "optimizer": "bistar_gp.laplace_evidence._multistart_G_optima",
  "spaces": {
   "encompassing": "canonical Sin+Linear bounds with the amplitude lower bound extended from 0.01 to 0 for exact nesting",
   "restricted": "bistar_viz/scripts/_viz_spaces.py:canonical_spaces"
  },
  "start_sets": "restricted optima embedded at the exact boundaries for the min-\u1e20 optimization; interior perturbed starts plus the best encompassing optimum for IS",
  "tau_grid": {
   "definition": "numpy.logspace(-1.5, 2.5, 161)",
   "values": {
    "__abridged_array__": "161 floats",
    "first3": [
     0.03162277660168379,
     0.03349654391578276,
     0.03548133892335755
    ],
    "last3": [
     281.8382931264455,
     298.538261891796,
     316.22776601683796
    ],
    "min": 0.03162277660168379,
    "max": 316.22776601683796
   }
  },
  "x_eval_count": 80,
  "x_eval_range": [
   -10.0,
   10.0
  ]
 },
 "schema_version": 1,
 "tolerances": {
  "exact_embedding_Gbar": 1e-10,
  "min_Gbar_inequality": 1e-08
 },
 "verdict": {
  "all_min_Gbar_inequalities_hold": true,
  "scope": "numerical check on one n=50 informative-config, MAP-based averaged GP; not a proof over all data priors or parameterizations",
  "statement": "Both numerical min-\u1e20 inequalities hold on the n=50 informative-config, MAP-based toy GP. E6 supports the reachable-set claim for these two exact restrictions, while the finite-\u03c4 Z_M ordering still depends on the reference-measure convention."
 }
}

=== BRANCH DIFF vs main ===
Full --stat (three runs/ artifacts excluded from the textual diff below because their content appears above; the PNG is binary):
 Notes/DECISIONS.md                         |   58 +
 docs/paper-sie-jmp/04-case-B-occam-dial.md |   91 +
 experiments/e6_nesting_monotonicity.py     |  446 ++++
 experiments/occam_dial_figure.py           |  516 +++++
 runs/occam_dial/README.md                  |   49 +
 runs/occam_dial/e6_results.json            | 3019 ++++++++++++++++++++++++++++
 runs/occam_dial/figure_results.json        |  194 ++
 runs/occam_dial/occam_dial.png             |  Bin 0 -> 155658 bytes
 8 files changed, 4373 insertions(+)

diff --git a/Notes/DECISIONS.md b/Notes/DECISIONS.md
index 033fee3..21a737a 100644
--- a/Notes/DECISIONS.md
+++ b/Notes/DECISIONS.md
@@ -5716,3 +5716,61 @@ to be amended later merely to insert them. STOP before Ready or merge. NOT autho
 second correction pass, restoring/applying/dropping stash `5280d1e1…`, D59 work, evidence
 or figure changes, poster-repository work, the captions themselves, Della contact, new
 computation, holdout access, BMS*, Ready, or merge.
+
+## D62: Case B Occam dial and E6 nesting check — 2026-08-11
+
+**Problem:** Case B needed a regenerable E4 figure that separated the D17
+estimator and `occam` changes, plus an E6 numerical check of the claim that an
+encompassing model cannot have a worse best achievable divergence than either
+of its exact restrictions. The local `runs/viz_unification/` directory contains
+figures and logs only and cannot serve as an input. The canonical visualization
+box also starts the sinusoid amplitude at 0.01, while exact Linear nesting
+requires A=0.
+
+**Decision:** Added `experiments/occam_dial_figure.py` and
+`experiments/e6_nesting_monotonicity.py`, both writing to
+`runs/occam_dial/`. Both scripts build the `informative`-configuration,
+MAP-based averaged GP through `bistar_viz/scripts/_viz_spaces.py` at n=50,
+with data seed 42, 80 evaluation points, and primary metric `pw_kl_vcal`.
+The figure runs the p1 pure-Laplace `occam=True`, p2 IS `occam=True`, and p3 IS
+`occam=False` arms at τ=0.3, IS seed 0, `n_is=40000`, and five seeded
+perturbations per start. Its absolute anchor tolerance equals 0.003, allowing
+three-decimal source rounding and small cross-platform optimizer variation
+while remaining below the p2 decision gap. E6 calls
+`_multistart_G_optima`, `compute_G_at_params`, and `is_log_Z_Mx` from
+`bistar_gp/laplace_evidence.py`; it does not reimplement Ḡ. E6 extends
+only the encompassing amplitude boundary to A=0, seeds its optimizer with
+the exact restricted optima, and uses `n_is=100000` over 161 log-spaced
+temperatures from 0.031623 through 316.227766. One IS call per model supplies
+the raw sweep, and the package reference-volume helper supplies the
+`occam=True` sweep. The min-Ḡ tolerance equals 10^-8, with a 10^-10
+exact-embedding check.
+
+**Alternatives considered:** Reading `delta_table.md` or the local logs as the
+figure data source was rejected because those artifacts remain local and
+untracked; the table now provides an optional cross-check only. Comparing p1
+directly with p3 as a pure `occam` ablation was rejected because the arms also
+change the Z_M estimator; p2 isolates the estimator step. Retaining the
+0.01 amplitude cutoff for E6 was rejected because it excludes the stated
+A=0 restriction. Reimplementing the divergence or optimizer was rejected
+in favor of the package machinery required by the work order.
+
+**Result:** `runs/occam_dial/figure_results.json` reproduces the n=50 arms:
+p1 Linear 0.534121, Sinusoidal 0.075747, Sin+Linear 0.382052, Quadratic
+0.008080; p2 Linear 0.506877, Sinusoidal 0.020499, Sin+Linear 0.464791,
+Quadratic 0.007834; p3 Linear 0.007040, Sinusoidal 0.001093, Sin+Linear
+0.991758, Quadratic 0.000109. The p1-to-p2 estimator change narrows the Linear
+versus Sin+Linear gap, and the p2-to-p3 convention change decides the verdict.
+D17's legacy 0.934 and 0.693 values remain explicitly labeled as recorded
+legacy findings and are not recomputed by the new scripts.
+
+E6 found min-Ḡ 0.045516783 for Sin+Linear, 2.424774370 for Linear, and
+2.546229649 for Sinusoidal, giving restricted-minus-encompassing margins
+2.379257587 and 2.500712865. Both nesting inequalities hold. Under
+`occam=False`, neither pair crosses on the tested τ grid. Under
+`occam=True`, Linear overtakes Sin+Linear at τ=0.295184 within the bracket
+[0.281838, 0.298538], and Sinusoidal overtakes at τ=1.484355 within
+[1.412538, 1.496236]. Minimum ESS values equal 14903 for Linear, 1373 for
+Sinusoidal, and 831 for Sin+Linear. The figure remains below the 2 MB
+limit. Exact rerun commands: `python experiments/occam_dial_figure.py` and
+`python experiments/e6_nesting_monotonicity.py`.
diff --git a/docs/paper-sie-jmp/04-case-B-occam-dial.md b/docs/paper-sie-jmp/04-case-B-occam-dial.md
new file mode 100644
index 0000000..fd4811e
--- /dev/null
+++ b/docs/paper-sie-jmp/04-case-B-occam-dial.md
@@ -0,0 +1,91 @@
+# 4. Case B: the occam flag as the Popper/Wrinch-Jeffreys dial
+
+van Bork, Romeijn, and Wagenmakers restate Popper's objection to the
+Wrinch-Jeffreys treatment of nested models: if M_r ⊂ M_e, assigning more prior
+probability to the restricted model M_r violates the encompassing-model
+constraint. Wrinch and Jeffreys instead permit a simplicity preference for
+M_r. Their analysis motivates a direct question for the induced model prior
+Z_M: which position does its reference measure encode?[^1]
+
+The toy roster contains two relevant restrictions. Linear follows from
+Sin+Linear at A=0, and Sinusoidal follows at b=c=0. Quadratic does not form a
+restriction of Sin+Linear. The `occam` flag changes the measure used in Z_M:
+`occam=False` integrates against raw Lebesgue measure, following the canonical
+BI* convention, whereas `occam=True` divides by the reference volume
+V_ref.[^2]
+
+## 4.1 An attribution ladder, not a two-arm ablation
+
+Figure 4 recomputes the three D17 attribution arms at n=50 and τ=0.3, with the
+`informative` GP configuration and a MAP predictive. These values serve
+methods validation and legacy comparison. They do not provide paper-facing
+posterior inference about which model generated the data.[^3]
+
+![Three-arm Occam-dial comparison at n=50](../../runs/occam_dial/occam_dial.png)
+
+**Figure 4.** Induced model priors for the nested toy roster. The p1 and p3
+panels differ in both the Z_M estimator and the `occam` convention, so the p2
+panel prevents a conflated attribution. Replacing pure Laplace with IS while
+retaining `occam=True` changes the Linear and Sin+Linear probabilities from
+0.534121 and 0.382052 in p1 to 0.506877 and 0.464791 in p2. Changing only the
+convention in the next step gives 0.007040 and 0.991758 in p3. The estimator
+change narrows the gap; removing the V_ref normalization decides the verdict.
+The dial figure argues about the `occam` convention's effect, not about which
+model generated the data.
+
+The earlier contradiction supplies useful historical context but not new
+evidence. D17 records 0.934 for Sin+Linear in the legacy trajectory script and
+0.693 for Linear in the legacy priors script, which hard-coded
+`occam=True`. The pinned-commit extraction in
+`viz_unification_compare.py` regenerates those legacy arms. The new figure
+does not invoke or parse that extraction.[^2]
+
+## 4.2 E6: best achievable divergence under exact nesting
+
+As τ approaches zero, the leading contribution to Z_M comes from
+min_φ Ḡ(φ). The reachable-set argument therefore requires
+
+\[
+\min_{\phi}\bar G(M_e) \leq \min_{\phi}\bar G(M_r).
+\]
+
+Different parameter dimensions prevent a Lebesgue-monotonicity argument in
+parameter space. E6 instead tests the two exact restrictions in data space.
+The visualization box uses A ≥ 0.01 as a numerical cutoff, so E6 alone extends
+the encompassing amplitude bound to A ≥ 0. All other bounds match the
+visualization arms. The restricted optimum seeds the encompassing multi-start
+optimization, and the package divergence calculation reproduces the restricted
+value exactly at its embedding, within the declared 10^-10 tolerance.[^4]
+
+For this n=50, `informative`-configuration, MAP-based averaged GP, E6
+obtains min_φ Ḡ=0.045516783 for Sin+Linear, 2.424774370 for Linear, and
+2.546229649 for Sinusoidal. The encompassing model improves on the restrictions
+by 2.379257587 and 2.500712865, respectively. Both numerical inequalities
+therefore hold by margins far above the 10^-8 comparison tolerance. This result
+supports the reachable-set claim for the tested GP and parameterization; it
+does not prove the claim for every data prior or parameterization.[^4]
+
+Finite τ separates the two reference measures. One IS call per model evaluates
+161 temperatures from 0.031623 through 316.227766. With `occam=False`,
+Sin+Linear retains the larger pairwise Z_M throughout that grid, so neither
+nested pair crosses. With `occam=True`, Linear overtakes Sin+Linear at the
+log-interpolated location τ=0.295184, bracketed by 0.281838 and 0.298538.
+Sinusoidal overtakes at τ=1.484355, bracketed by 1.412538 and 1.496236. Thus
+low temperature supports Popper's encompassing constraint in both conventions
+for this example, while V_ref normalization permits the finite-temperature
+simplicity preference associated with Wrinch and Jeffreys.[^4]
+
+The two controls should therefore remain explicit. Temperature governs how
+strongly best achievable divergence dominates integrated compatibility, while
+`occam` selects raw or volume-normalized reference measure. Their joint
+sensitivity describes the Popper/Wrinch-Jeffreys disagreement without turning
+a methods-validation example into a claim about model truth.
+
+[^1]: 🟢 peer-reviewed — van Bork, Romeijn, and Wagenmakers (2025), *Synthese*, doi:10.1007/s11229-025-05286-y.
+[^2]: 🟠 empirical — `Notes/DECISIONS.md` D3, D5, and D17; legacy regeneration through `bistar_viz/scripts/viz_unification_compare.py` at pinned commit `a87356a`.
+[^3]: 🟠 empirical — `experiments/occam_dial_figure.py`; `runs/occam_dial/figure_results.json`.
+[^4]: 🟠 empirical — `experiments/e6_nesting_monotonicity.py`; `runs/occam_dial/e6_results.json`.
+
+---
+*Provenance: `runs/occam_dial/` · `experiments/occam_dial_figure.py` ·
+`experiments/e6_nesting_monotonicity.py` · `Notes/DECISIONS.md` D17, D62.*
diff --git a/experiments/e6_nesting_monotonicity.py b/experiments/e6_nesting_monotonicity.py
new file mode 100644
index 0000000..b9cc490
--- /dev/null
+++ b/experiments/e6_nesting_monotonicity.py
@@ -0,0 +1,446 @@
+#!/usr/bin/env python3
+"""Run the Case B E6 nesting and finite-τ ordering check.
+
+The script uses the existing multi-start Ḡ optimizer and defensive-mixture IS
+implementation. It tests exact Linear and Sinusoidal restrictions inside an
+encompassing Sin+Linear parameter space, then computes both reference-measure
+conventions over one shared τ grid.
+"""
+
+from __future__ import annotations
+
+import argparse
+import json
+from pathlib import Path
+import sys
+from typing import Any
+
+import numpy as np
+
+
+REPO_ROOT = Path(__file__).resolve().parents[1]
+VIZ_SCRIPTS = REPO_ROOT / "bistar_viz" / "scripts"
+EXPERIMENTS = REPO_ROOT / "experiments"
+for import_path in (VIZ_SCRIPTS, EXPERIMENTS):
+    if str(import_path) not in sys.path:
+        sys.path.insert(0, str(import_path))
+
+import _viz_spaces as V  # noqa: E402
+from bistar_gp.bms_star import METRICS  # noqa: E402
+from bistar_gp.induced_prior import ModelParameterSpace, ParameterSpec  # noqa: E402
+from bistar_gp.laplace_evidence import (  # noqa: E402
+    _log_reference_volume,
+    _multistart_G_optima,
+    compute_G_at_params,
+    is_log_Z_Mx,
+)
+from occam_dial_figure import (  # noqa: E402
+    DATA_SEED,
+    DEFAULT_OUT_DIR,
+    IS_SEED,
+    MODEL_NAMES,
+    N_DRAWS,
+    N_PERTURB,
+    build_map_gp,
+    write_combined_readme,
+)
+
+
+N_IS = 100_000
+TAUS = np.logspace(-1.5, 2.5, 161)
+MIN_G_TOLERANCE = 1e-8
+EMBEDDING_TOLERANCE = 1e-10
+
+
+def _native(value: Any) -> Any:
+    if isinstance(value, dict):
+        return {str(k): _native(v) for k, v in value.items()}
+    if isinstance(value, (list, tuple)):
+        return [_native(v) for v in value]
+    if isinstance(value, np.ndarray):
+        return value.tolist()
+    if isinstance(value, (np.floating, np.integer, np.bool_)):
+        return value.item()
+    return value
+
+
+def _exact_encompassing_space() -> ModelParameterSpace:
+    """Match canonical bounds while including the exact A=0 boundary."""
+    return ModelParameterSpace(
+        model_name="Sin+Linear",
+        param_specs=[
+            ParameterSpec("A", (0.0, 5.0), None),
+            ParameterSpec("omega", (0.1, 5.0), None),
+            ParameterSpec("phi", (-np.pi, np.pi), None),
+            ParameterSpec("b", (-2.0, 2.0), None),
+            ParameterSpec("c", (-5.0, 5.0), None),
+        ],
+        predict_fn=lambda x, p: (
+            p["A"] * np.sin(p["omega"] * x + p["phi"])
+            + p["b"] * x
+            + p["c"]
+        ),
+        noise_param="sigma",
+    )
+
+
+def _best_optimum(param_space, x_eval, avg_gp, starts):
+    optima = _multistart_G_optima(
+        param_space,
+        x_eval,
+        avg_gp,
+        METRICS["pw_kl_vcal"],
+        starts,
+    )
+    best = min(optima, key=lambda item: item[1])
+    return optima, best
+
+
+def _parameter_dict(param_space, vector) -> dict[str, float]:
+    return {
+        spec.name: float(value)
+        for spec, value in zip(param_space.param_specs, vector)
+    }
+
+
+def _crossings(taus: np.ndarray, delta: np.ndarray) -> list[dict[str, Any]]:
+    found = []
+    for index in range(len(taus) - 1):
+        left, right = float(delta[index]), float(delta[index + 1])
+        if left == 0.0:
+            estimate = float(taus[index])
+        elif left * right > 0.0:
+            continue
+        else:
+            log_left, log_right = np.log10(taus[index : index + 2])
+            estimate = float(
+                10.0 ** (log_left - left * (log_right - log_left) / (right - left))
+            )
+        found.append(
+            {
+                "lower_grid_index": index,
+                "tau_bracket": [float(taus[index]), float(taus[index + 1])],
+                "delta_log_Z_bracket": [left, right],
+                "tau_log_interpolated": estimate,
+                "winner_below": "encompassing" if left > 0.0 else "restricted",
+                "winner_above": "encompassing" if right > 0.0 else "restricted",
+            }
+        )
+    return found
+
+
+def _ordering_summary(
+    taus: np.ndarray,
+    encompassing_log_z: np.ndarray,
+    restricted_log_z: np.ndarray,
+) -> dict[str, Any]:
+    delta = encompassing_log_z - restricted_log_z
+    crossings = _crossings(taus, delta)
+    return {
+        "delta_definition": "log Z_M(encompassing) - log Z_M(restricted)",
+        "delta_log_Z": delta,
+        "crossings": crossings,
+        "winner_at_tau_min": "encompassing" if delta[0] > 0.0 else "restricted",
+        "winner_at_tau_max": "encompassing" if delta[-1] > 0.0 else "restricted",
+        "delta_at_tau_min": float(delta[0]),
+        "delta_at_tau_max": float(delta[-1]),
+        "minimum_absolute_delta_grid_point": {
+            "tau": float(taus[int(np.argmin(np.abs(delta)))]),
+            "delta_log_Z": float(delta[int(np.argmin(np.abs(delta)))]),
+        },
+    }
+
+
+def run(out_dir: Path, *, n_is: int) -> dict[str, Any]:
+    out_dir.mkdir(parents=True, exist_ok=True)
+    x_eval, _x_50, _y_50, avg_gp, retained = build_map_gp()
+    canonical = V.canonical_spaces()
+    encompassing = _exact_encompassing_space()
+
+    starts = {
+        name: V.perturbed_starts(
+            name, canonical, N_PERTURB, seed=DATA_SEED
+        )
+        for name in MODEL_NAMES
+    }
+    linear_optima, linear_best = _best_optimum(
+        canonical["Linear"], x_eval, avg_gp, starts["Linear"]
+    )
+    sinusoidal_optima, sinusoidal_best = _best_optimum(
+        canonical["Sinusoidal"], x_eval, avg_gp, starts["Sinusoidal"]
+    )
+
+    linear_phi = _parameter_dict(canonical["Linear"], linear_best[0])
+    sinusoidal_phi = _parameter_dict(
+        canonical["Sinusoidal"], sinusoidal_best[0]
+    )
+    linear_embedding = {
+        "A": 0.0,
+        "omega": 1.0,
+        "phi": 0.0,
+        "b": linear_phi["a"],
+        "c": linear_phi["b"],
+    }
+    sinusoidal_embedding = {
+        "A": sinusoidal_phi["A"],
+        "omega": sinusoidal_phi["omega"],
+        "phi": sinusoidal_phi["phi"],
+        "b": 0.0,
+        "c": 0.0,
+    }
+    encompassing_starts = [dict(start) for start in starts["Sin+Linear"]]
+    encompassing_starts.extend([linear_embedding, sinusoidal_embedding])
+    encompassing_optima, encompassing_best = _best_optimum(
+        encompassing, x_eval, avg_gp, encompassing_starts
+    )
+    encompassing_phi = _parameter_dict(encompassing, encompassing_best[0])
+
+    metric = METRICS["pw_kl_vcal"]
+    linear_g_embedded = float(
+        compute_G_at_params(
+            linear_embedding, encompassing, x_eval, avg_gp, metric
+        )
+    )
+    sinusoidal_g_embedded = float(
+        compute_G_at_params(
+            sinusoidal_embedding, encompassing, x_eval, avg_gp, metric
+        )
+    )
+    linear_embedding_error = abs(linear_g_embedded - float(linear_best[1]))
+    sinusoidal_embedding_error = abs(
+        sinusoidal_g_embedded - float(sinusoidal_best[1])
+    )
+    if linear_embedding_error > EMBEDDING_TOLERANCE:
+        raise AssertionError(
+            f"Linear embedding changes Ḡ by {linear_embedding_error}"
+        )
+    if sinusoidal_embedding_error > EMBEDDING_TOLERANCE:
+        raise AssertionError(
+            f"Sinusoidal embedding changes Ḡ by {sinusoidal_embedding_error}"
+        )
+
+    spaces = {
+        "Linear": canonical["Linear"],
+        "Sinusoidal": canonical["Sinusoidal"],
+        "Sin+Linear": encompassing,
+    }
+    starts_by_model = {
+        "Linear": starts["Linear"],
+        "Sinusoidal": starts["Sinusoidal"],
+        # Exact boundary embeddings guarantee the optimization inequality but
+        # create flat omega/phi Hessian directions at A=0. The IS proposal
+        # instead uses interior starts plus the best encompassing optimum.
+        "Sin+Linear": starts["Sin+Linear"] + [encompassing_phi],
+    }
+    sweeps: dict[str, dict[str, Any]] = {}
+    for name, param_space in spaces.items():
+        # One package IS call computes the full τ sweep. The package's
+        # reference-volume helper then applies the documented occam variant.
+        # NumPy 2 on Accelerate can emit spurious matmul floating warnings for
+        # the large proposal draw even when every returned diagnostic remains
+        # finite, so the scoped errstate accompanies explicit finiteness checks.
+        with np.errstate(divide="ignore", over="ignore", invalid="ignore"):
+            result = is_log_Z_Mx(
+                param_space,
+                x_eval,
+                avg_gp,
+                TAUS,
+                n_is=n_is,
+                seed=IS_SEED,
+                starts=starts_by_model[name],
+                metric_name="pw_kl_vcal",
+                occam=False,
+            )
+        if not np.all(np.isfinite(result.log_Z)) or not np.all(
+            np.isfinite(result.ess)
+        ):
+            raise AssertionError(f"non-finite IS result for {name}")
+        log_volume = float(_log_reference_volume(param_space))
+        normalized_log_z = result.log_Z - log_volume
+        sweeps[name] = {
+            "occam_false": {
+                "log_Z_M": result.log_Z,
+                "ess": result.ess,
+                "min_ess": float(np.min(result.ess)),
+            },
+            "occam_true": {
+                "log_Z_M": normalized_log_z,
+                "ess": result.ess,
+                "min_ess": float(np.min(result.ess)),
+                "derived_from_raw_with": (
+                    "bistar_gp.laplace_evidence._log_reference_volume"
+                ),
+            },
+            "log_reference_volume": log_volume,
+            "is_calls": 1,
+        }
+
+    pair_inputs = {
+        "Linear_within_Sin+Linear": {
+            "restricted_name": "Linear",
+            "restriction": "A=0; encompassing b and c equal restricted a and b",
+            "restricted_best": linear_best,
+            "restricted_phi": linear_phi,
+            "embedded_phi": linear_embedding,
+            "embedded_Gbar": linear_g_embedded,
+            "embedding_error": linear_embedding_error,
+            "n_restricted_starts": len(linear_optima),
+        },
+        "Sinusoidal_within_Sin+Linear": {
+            "restricted_name": "Sinusoidal",
+            "restriction": "b=c=0",
+            "restricted_best": sinusoidal_best,
+            "restricted_phi": sinusoidal_phi,
+            "embedded_phi": sinusoidal_embedding,
+            "embedded_Gbar": sinusoidal_g_embedded,
+            "embedding_error": sinusoidal_embedding_error,
+            "n_restricted_starts": len(sinusoidal_optima),
+        },
+    }
+    nested_pairs = {}
+    all_hold = True
+    for pair_name, pair_input in pair_inputs.items():
+        restricted_name = pair_input["restricted_name"]
+        restricted_min = float(pair_input["restricted_best"][1])
+        encompassing_min = float(encompassing_best[1])
+        margin = restricted_min - encompassing_min
+        holds = margin >= -MIN_G_TOLERANCE
+        all_hold = all_hold and holds
+        orderings = {}
+        for convention in ("occam_false", "occam_true"):
+            orderings[convention] = _ordering_summary(
+                TAUS,
+                np.asarray(sweeps["Sin+Linear"][convention]["log_Z_M"]),
+                np.asarray(sweeps[restricted_name][convention]["log_Z_M"]),
+            )
+        nested_pairs[pair_name] = {
+            "restricted_model": restricted_name,
+            "encompassing_model": "Sin+Linear",
+            "restriction": pair_input["restriction"],
+            "restricted": {
+                "min_Gbar": restricted_min,
+                "phi_min": pair_input["restricted_phi"],
+                "n_multistarts": pair_input["n_restricted_starts"],
+            },
+            "encompassing": {
+                "min_Gbar": encompassing_min,
+                "phi_min": encompassing_phi,
+                "n_multistarts": len(encompassing_optima),
+            },
+            "embedded_restricted_optimum": {
+                "phi": pair_input["embedded_phi"],
+                "Gbar": pair_input["embedded_Gbar"],
+                "absolute_Gbar_error": pair_input["embedding_error"],
+                "tolerance": EMBEDDING_TOLERANCE,
+                "passed": pair_input["embedding_error"] <= EMBEDDING_TOLERANCE,
+            },
+            "inequality": "min_φ Ḡ(encompassing) ≤ min_φ Ḡ(restricted)",
+            "margin_restricted_minus_encompassing": margin,
+            "tolerance": MIN_G_TOLERANCE,
+            "inequality_holds": holds,
+            "verified_for_tau_count": len(TAUS),
+            "minimum_is_tau_independent": True,
+            "Z_M_ordering": orderings,
+        }
+
+    verdict_text = (
+        "Both numerical min-Ḡ inequalities hold on the n=50 informative-config, "
+        "MAP-based toy GP. E6 supports the reachable-set claim for these two "
+        "exact restrictions, while the finite-τ Z_M ordering still depends on "
+        "the reference-measure convention."
+        if all_hold
+        else
+        "At least one numerical min-Ḡ inequality fails on the n=50 informative-config, "
+        "MAP-based toy GP, so E6 reports a counterexample to the reachable-set claim."
+    )
+    results = {
+        "schema_version": 1,
+        "case": "B",
+        "artifact": "e6_nesting_monotonicity",
+        "provenance": {
+            "gp_config": "informative",
+            "gp_method": "map",
+            "metric": "pw_kl_vcal",
+            "n": 50,
+            "data_seed": DATA_SEED,
+            "is_seed": IS_SEED,
+            "x_eval_count": len(x_eval),
+            "x_eval_range": [float(x_eval[0]), float(x_eval[-1])],
+            "n_draws_requested": N_DRAWS,
+            "gp_predictives_retained": retained,
+            "n_is": n_is,
+            "n_perturb": N_PERTURB,
+            "tau_grid": {
+                "definition": "numpy.logspace(-1.5, 2.5, 161)",
+                "values": TAUS,
+            },
+            "spaces": {
+                "restricted": "bistar_viz/scripts/_viz_spaces.py:canonical_spaces",
+                "encompassing": (
+                    "canonical Sin+Linear bounds with the amplitude lower bound "
+                    "extended from 0.01 to 0 for exact nesting"
+                ),
+            },
+            "optimizer": "bistar_gp.laplace_evidence._multistart_G_optima",
+            "Z_M_estimator": "bistar_gp.laplace_evidence.is_log_Z_Mx",
+            "occam_normalization": (
+                "bistar_gp.laplace_evidence._log_reference_volume"
+            ),
+            "start_sets": (
+                "restricted optima embedded at the exact boundaries for the "
+                "min-Ḡ optimization; interior perturbed starts plus the best "
+                "encompassing optimum for IS"
+            ),
+        },
+        "tolerances": {
+            "min_Gbar_inequality": MIN_G_TOLERANCE,
+            "exact_embedding_Gbar": EMBEDDING_TOLERANCE,
+        },
+        "nested_pairs": nested_pairs,
+        "model_sweeps": sweeps,
+        "verdict": {
+            "all_min_Gbar_inequalities_hold": all_hold,
+            "statement": verdict_text,
+            "scope": (
+                "numerical check on one n=50 informative-config, MAP-based averaged GP; "
+                "not a proof over all data priors or parameterizations"
+            ),
+        },
+    }
+    path = out_dir / "e6_results.json"
+    path.write_text(
+        json.dumps(_native(results), indent=2, sort_keys=True, ensure_ascii=False) + "\n",
+        encoding="utf-8",
+    )
+    write_combined_readme(out_dir)
+    return results
+
+
+def main() -> None:
+    parser = argparse.ArgumentParser(description=__doc__)
+    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
+    parser.add_argument("--n-is", type=int, default=N_IS)
+    args = parser.parse_args()
+    results = run(args.out_dir.resolve(), n_is=args.n_is)
+    for pair_name, pair in results["nested_pairs"].items():
+        print(
+            f"{pair_name}: restricted min Ḡ={pair['restricted']['min_Gbar']:.9f}; "
+            f"encompassing min Ḡ={pair['encompassing']['min_Gbar']:.9f}; "
+            f"margin={pair['margin_restricted_minus_encompassing']:.9f}; "
+            f"holds={pair['inequality_holds']}"
+        )
+        for convention in ("occam_false", "occam_true"):
+            crossings = pair["Z_M_ordering"][convention]["crossings"]
+            if crossings:
+                locations = ", ".join(
+                    f"{item['tau_log_interpolated']:.6f}" for item in crossings
+                )
+            else:
+                locations = "none on grid"
+            print(f"  {convention} Z_M τ crossings: {locations}")
+    print(results["verdict"]["statement"])
+    print(f"wrote {args.out_dir.resolve() / 'e6_results.json'}")
+
+
+if __name__ == "__main__":
+    main()
diff --git a/experiments/occam_dial_figure.py b/experiments/occam_dial_figure.py
new file mode 100644
index 0000000..883d8c9
--- /dev/null
+++ b/experiments/occam_dial_figure.py
@@ -0,0 +1,516 @@
+#!/usr/bin/env python3
+"""Regenerate the Case B Occam-dial figure and its numeric artifact.
+
+The three arms reproduce the D17 attribution ladder at n=50 on the shared
+informative-config, MAP-based averaged GP. The local viz_unification table,
+when available, provides only a cross-check; all plotted values come from
+fresh calls to the repository's scoring machinery.
+"""
+
+from __future__ import annotations
+
+import argparse
+import json
+from pathlib import Path
+import re
+import sys
+from typing import Any
+
+import matplotlib
+
+matplotlib.use("Agg")
+import matplotlib.pyplot as plt
+import numpy as np
+
+
+REPO_ROOT = Path(__file__).resolve().parents[1]
+VIZ_SCRIPTS = REPO_ROOT / "bistar_viz" / "scripts"
+if str(VIZ_SCRIPTS) not in sys.path:
+    sys.path.insert(0, str(VIZ_SCRIPTS))
+
+import _viz_spaces as V  # noqa: E402
+
+
+MODEL_NAMES = ["Linear", "Sinusoidal", "Sin+Linear", "Quadratic"]
+DEFAULT_OUT_DIR = REPO_ROOT / "runs" / "occam_dial"
+TAU = 0.3
+DATA_SEED = 42
+IS_SEED = 0
+N_IS = 40_000
+N_DRAWS = 150
+N_PERTURB = 5
+ANCHOR_TOLERANCE = 0.003
+ANCHORS = {
+    "p1_priors_lap_occam": {"Linear": 0.534, "Sin+Linear": 0.382},
+    "p2_priors_is_occam": {"Linear": 0.507, "Sin+Linear": 0.465},
+    "p3_priors_canonical": {"Sin+Linear": 0.992},
+}
+
+
+def _native(value: Any) -> Any:
+    """Convert NumPy containers and scalars into JSON-native values."""
+    if isinstance(value, dict):
+        return {str(k): _native(v) for k, v in value.items()}
+    if isinstance(value, (list, tuple)):
+        return [_native(v) for v in value]
+    if isinstance(value, np.ndarray):
+        return value.tolist()
+    if isinstance(value, (np.floating, np.integer, np.bool_)):
+        return value.item()
+    return value
+
+
+def build_map_gp():
+    """Build the n=50 averaged GP with the D17 visualization recipe."""
+    x_eval = np.linspace(-10.0, 10.0, 80)
+    x_50, y_50 = V.generate_data(50, seed=DATA_SEED)
+    avg_gp, retained = V.averaged_gp(
+        x_eval,
+        x_50,
+        y_50,
+        gp_method="map",
+        n_draws=N_DRAWS,
+        seed=DATA_SEED,
+    )
+    return x_eval, x_50, y_50, avg_gp, retained
+
+
+def _arm(
+    spaces,
+    x_eval,
+    avg_gp,
+    starts_map,
+    *,
+    estimator: str,
+    occam: bool,
+    n_is: int,
+) -> dict[str, Any]:
+    names, log_z, posterior, diagnostics = V.model_prior_curves(
+        spaces,
+        x_eval,
+        avg_gp,
+        [TAU],
+        estimator=estimator,
+        occam=occam,
+        seed=IS_SEED,
+        n_is=n_is,
+        starts_map=starts_map,
+    )
+    return {
+        "estimator": estimator,
+        "occam": occam,
+        "log_Z_M": {name: float(log_z[0, j]) for j, name in enumerate(names)},
+        "model_posterior": {
+            name: float(posterior[0, j]) for j, name in enumerate(names)
+        },
+        "ess": {
+            name: None
+            if diagnostics[name] is None
+            else float(diagnostics[name][0])
+            for name in names
+        },
+    }
+
+
+def _assert_anchors(arms: dict[str, dict[str, Any]], tolerance: float) -> dict:
+    checks = {}
+    for arm_name, expected_by_model in ANCHORS.items():
+        checks[arm_name] = {}
+        for model_name, expected in expected_by_model.items():
+            actual = arms[arm_name]["model_posterior"][model_name]
+            error = abs(actual - expected)
+            passed = error <= tolerance
+            checks[arm_name][model_name] = {
+                "expected": expected,
+                "actual": actual,
+                "absolute_error": error,
+                "passed": passed,
+            }
+            if not passed:
+                raise AssertionError(
+                    f"{arm_name} {model_name}: {actual:.6f} differs from "
+                    f"anchor {expected:.3f} by {error:.6f}, above {tolerance}"
+                )
+    return checks
+
+
+def _crosscheck_local_table(
+    arms: dict[str, dict[str, Any]], tolerance: float
+) -> dict[str, Any]:
+    """Compare against the optional local D17 table without sourcing data."""
+    path = REPO_ROOT / "runs" / "viz_unification" / "delta_table.md"
+    if not path.exists():
+        return {"available": False, "path": str(path.relative_to(REPO_ROOT))}
+
+    rows: dict[str, list[float]] = {}
+    wanted = {f"{arm_name}/n=50" for arm_name in arms}
+    for line in path.read_text(encoding="utf-8").splitlines():
+        match = re.match(r"\|\s*([^|]+?)\s*\|\s*(.+)\|$", line)
+        if not match or match.group(1).strip() not in wanted:
+            continue
+        key = match.group(1).strip()
+        values = [float(v.strip()) for v in match.group(2).split("|")]
+        if len(values) == len(MODEL_NAMES):
+            rows[key] = values
+
+    checks = {}
+    for arm_name in arms:
+        key = f"{arm_name}/n=50"
+        if key not in rows:
+            checks[arm_name] = {"found": False}
+            continue
+        errors = {
+            model: abs(arms[arm_name]["model_posterior"][model] - rows[key][j])
+            for j, model in enumerate(MODEL_NAMES)
+        }
+        passed = max(errors.values()) <= tolerance
+        checks[arm_name] = {
+            "found": True,
+            "table_values": dict(zip(MODEL_NAMES, rows[key])),
+            "absolute_errors": errors,
+            "passed": passed,
+        }
+        if not passed:
+            raise AssertionError(
+                f"fresh {arm_name} values do not match the optional local "
+                f"D17 table within {tolerance}"
+            )
+    return {
+        "available": True,
+        "path": str(path.relative_to(REPO_ROOT)),
+        "checks": checks,
+    }
+
+
+def _plot(arms: dict[str, dict[str, Any]], out_path: Path) -> None:
+    colors = [V.COLORS[name] for name in MODEL_NAMES]
+    panels = [
+        (
+            "p1_priors_lap_occam",
+            "p1: pure Laplace\noccam=True",
+            0.82,
+        ),
+        (
+            "p2_priors_is_occam",
+            "p2: IS\noccam=True",
+            0.52,
+        ),
+        (
+            "p3_priors_canonical",
+            "p3: IS\noccam=False",
+            0.88,
+        ),
+    ]
+    fig, axes = plt.subplots(1, 3, figsize=(15.8, 7.4), sharey=True)
+    for panel_index, (ax, (arm_name, title, alpha)) in enumerate(
+        zip(axes, panels)
+    ):
+        values = [arms[arm_name]["model_posterior"][name] for name in MODEL_NAMES]
+        bars = ax.bar(
+            np.arange(len(MODEL_NAMES)),
+            values,
+            color=colors,
+            alpha=alpha,
+            edgecolor="white",
+            linewidth=1.3,
+        )
+        for bar, value in zip(bars, values):
+            ax.text(
+                bar.get_x() + bar.get_width() / 2,
+                value + 0.018,
+                f"{value:.3f}",
+                ha="center",
+                va="bottom",
+                fontsize=10,
+                fontweight="bold",
+            )
+        ax.axhline(0.25, color="#6b7280", ls="--", lw=1, alpha=0.55)
+        ax.set_xticks(np.arange(len(MODEL_NAMES)))
+        ax.set_xticklabels(MODEL_NAMES, rotation=22, ha="right")
+        ax.set_ylim(0.0, 1.08)
+        ax.set_title(title, fontsize=13, fontweight="bold")
+        ax.grid(axis="y", alpha=0.16)
+        if panel_index == 0:
+            ax.set_ylabel("Induced model prior", fontsize=12)
+
+    fig.suptitle(
+        "Occam convention changes the informative-config, MAP-based model prior at n = 50",
+        fontsize=15,
+        fontweight="bold",
+        y=0.965,
+    )
+    fig.text(
+        0.5,
+        0.875,
+        "p1 to p2 changes the Z_M estimator; p2 to p3 changes the occam convention",
+        ha="center",
+        fontsize=11.5,
+        color="#374151",
+    )
+    fig.text(
+        0.5,
+        0.105,
+        "Nesting: Linear ⊂ Sin+Linear at A=0; Sinusoidal ⊂ Sin+Linear at b=c=0; "
+        "Quadratic not nested.",
+        ha="center",
+        fontsize=10.5,
+    )
+    fig.text(
+        0.5,
+        0.062,
+        "The comparison evaluates the occam convention, not which model generated the data.",
+        ha="center",
+        fontsize=10.5,
+        fontweight="bold",
+    )
+    fig.text(
+        0.5,
+        0.022,
+        "D17 legacy context, not recomputed here: trajectory Sin+Linear 0.934; "
+        "priors Linear 0.693.",
+        ha="center",
+        fontsize=9,
+        color="#4b5563",
+    )
+    fig.subplots_adjust(left=0.075, right=0.985, bottom=0.22, top=0.79, wspace=0.1)
+    fig.savefig(out_path, dpi=180, bbox_inches="tight", facecolor="white")
+    plt.close(fig)
+
+
+def _fmt_posteriors(arm: dict[str, Any]) -> str:
+    return ", ".join(
+        f"{name} {arm['model_posterior'][name]:.6f}" for name in MODEL_NAMES
+    )
+
+
+def write_combined_readme(out_dir: Path) -> None:
+    """Write one run-directory README from whichever Case B artifacts exist."""
+    figure_path = out_dir / "figure_results.json"
+    e6_path = out_dir / "e6_results.json"
+    figure = json.loads(figure_path.read_text(encoding="utf-8")) if figure_path.exists() else None
+    e6 = json.loads(e6_path.read_text(encoding="utf-8")) if e6_path.exists() else None
+
+    lines = [
+        "# Case B: Occam dial and nesting monotonicity",
+        "",
+        "Regenerate from the repository root:",
+        "",
+        "```bash",
+        "python experiments/occam_dial_figure.py",
+        "python experiments/e6_nesting_monotonicity.py",
+        "```",
+        "",
+        "Both scripts use local CPU computation only. They construct the n=50 averaged GP with "
+        "`PRIOR_CONFIGS[\"informative\"]`, `gp_method=\"map\"`, data seed 42, 80 "
+        "evaluation points over [-10, 10], and the primary `pw_kl_vcal` metric. MAP retains "
+        "one GP predictive. The scripts import the shared construction from "
+        "`bistar_viz/scripts/_viz_spaces.py` and the existing evidence machinery from "
+        "`bistar_gp/laplace_evidence.py`.",
+        "",
+        "## Figure computation",
+        "",
+        "`occam_dial.png` and `figure_results.json` use τ=0.3, IS seed 0, "
+        "n_is=40,000, five seeded perturbations per legacy start, and the canonical "
+        "visualization parameter boxes. The optional `runs/viz_unification/delta_table.md` "
+        "only supplies a cross-check when present.",
+        "",
+        "The anchor tolerance equals 0.003 in absolute model probability. The published "
+        "anchors were rounded to three decimals, and the remaining allowance covers small "
+        "cross-platform optimizer differences. The tolerance remains well below the 0.042 "
+        "p2 Linear versus Sin+Linear gap.",
+    ]
+    if figure is not None:
+        lines.extend(["", "Fresh n=50 posteriors:", ""])
+        for arm_name in (
+            "p1_priors_lap_occam",
+            "p2_priors_is_occam",
+            "p3_priors_canonical",
+        ):
+            lines.append(f"- `{arm_name}`: {_fmt_posteriors(figure['arms'][arm_name])}")
+        cross = figure["optional_local_crosscheck"]
+        lines.extend(
+            [
+                "",
+                f"The optional D17 table cross-check was {'available' if cross['available'] else 'not available'}.",
+            ]
+        )
+
+    lines.extend(
+        [
+            "",
+            "The D17-recorded legacy 0.934 and 0.693 values provide historical context only. "
+            "`bistar_viz/scripts/viz_unification_compare.py`, with pinned legacy commit "
+            "`a87356a`, regenerates those legacy arms. Neither new script invokes that "
+            "git-based extraction path.",
+            "",
+            "## E6 computation",
+            "",
+            "E6 uses 161 log-spaced τ values from 10^-1.5 through 10^2.5, IS seed 0, "
+            "n_is=100,000, and the same five perturbations per start. One "
+            "`is_log_Z_Mx` call per model computes the full raw sweep; the package's "
+            "`_log_reference_volume` helper supplies the occam-normalized sweep. The visualization "
+            "box uses A >= 0.01 for numerical plotting. E6 alone extends the encompassing "
+            "Sin+Linear box to A >= 0 so Linear at A=0 forms an exact restriction. All "
+            "other bounds match the canonical visualization boxes. The embedded restricted "
+            "optima seed the encompassing multi-start optimization. IS uses interior perturbed "
+            "starts plus the best encompassing optimum, which avoids flat boundary-Hessian "
+            "components without changing the integral.",
+            "",
+            "The min-Ḡ comparison tolerance equals 1e-8 in Ḡ units. It only classifies "
+            "floating-point near-ties and remains many orders of magnitude below the observed "
+            "margins. τ crossings use linear interpolation in log10(τ) inside the reported "
+            "adjacent grid bracket; the bracket, rather than extra decimal places in the "
+            "interpolant, provides the resolution statement.",
+        ]
+    )
+    if e6 is not None:
+        lines.extend(["", "Fresh E6 results:", ""])
+        for pair_name, pair in e6["nested_pairs"].items():
+            lines.append(
+                f"- `{pair_name}`: min Ḡ(restricted)={pair['restricted']['min_Gbar']:.9f}, "
+                f"min Ḡ(encompassing)={pair['encompassing']['min_Gbar']:.9f}, "
+                f"margin={pair['margin_restricted_minus_encompassing']:.9f}, "
+                f"holds={pair['inequality_holds']}."
+            )
+            for convention in ("occam_false", "occam_true"):
+                crossing_text = ", ".join(
+                    f"{item['tau_log_interpolated']:.6f} within "
+                    f"[{item['tau_bracket'][0]:.6f}, {item['tau_bracket'][1]:.6f}]"
+                    for item in pair["Z_M_ordering"][convention]["crossings"]
+                ) or "no crossing on the grid"
+                lines.append(f"  - `{convention}`: {crossing_text}.")
+        lines.extend(
+            [
+                "",
+                f"E6 verdict: {e6['verdict']['statement']}",
+            ]
+        )
+
+    lines.extend(
+        [
+            "",
+            "## Files",
+            "",
+            "- `occam_dial.png`: E4 attribution-ladder figure, kept below 2 MB.",
+            "- `figure_results.json`: all freshly computed E4 arm values and anchor checks.",
+            "- `e6_results.json`: min-Ḡ optima, exact-embedding checks, both Z_M conventions, "
+            "ESS diagnostics, the full τ grid, and crossing brackets.",
+        ]
+    )
+    (out_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
+
+
+def run(out_dir: Path, *, n_is: int, anchor_tolerance: float) -> dict[str, Any]:
+    out_dir.mkdir(parents=True, exist_ok=True)
+    x_eval, _x_50, _y_50, avg_gp, retained = build_map_gp()
+    spaces = V.canonical_spaces()
+    starts_map = {
+        name: V.perturbed_starts(name, spaces, N_PERTURB, seed=DATA_SEED)
+        for name in MODEL_NAMES
+    }
+
+    arms = {
+        "p1_priors_lap_occam": _arm(
+            spaces,
+            x_eval,
+            avg_gp,
+            starts_map,
+            estimator="laplace",
+            occam=True,
+            n_is=n_is,
+        ),
+        "p2_priors_is_occam": _arm(
+            spaces,
+            x_eval,
+            avg_gp,
+            starts_map,
+            estimator="is",
+            occam=True,
+            n_is=n_is,
+        ),
+        "p3_priors_canonical": _arm(
+            spaces,
+            x_eval,
+            avg_gp,
+            starts_map,
+            estimator="is",
+            occam=False,
+            n_is=n_is,
+        ),
+    }
+    anchor_checks = _assert_anchors(arms, anchor_tolerance)
+    local_crosscheck = _crosscheck_local_table(arms, anchor_tolerance)
+
+    results = {
+        "schema_version": 1,
+        "case": "B",
+        "artifact": "occam_dial_figure",
+        "provenance": {
+            "gp_config": "informative",
+            "gp_method": "map",
+            "metric": "pw_kl_vcal",
+            "n": 50,
+            "data_seed": DATA_SEED,
+            "is_seed": IS_SEED,
+            "x_eval_count": len(x_eval),
+            "x_eval_range": [float(x_eval[0]), float(x_eval[-1])],
+            "tau": TAU,
+            "n_draws_requested": N_DRAWS,
+            "gp_predictives_retained": retained,
+            "n_is": n_is,
+            "n_perturb": N_PERTURB,
+            "spaces": "bistar_viz/scripts/_viz_spaces.py:canonical_spaces",
+            "evidence": "bistar_gp/laplace_evidence.py",
+        },
+        "arms": arms,
+        "anchor_tolerance_absolute_probability": anchor_tolerance,
+        "anchor_checks": anchor_checks,
+        "optional_local_crosscheck": local_crosscheck,
+        "legacy_context_not_recomputed": {
+            "source": "Notes/DECISIONS.md D17",
+            "legacy_trajectory_Sin+Linear_n50": 0.934,
+            "legacy_priors_Linear_n50": 0.693,
+            "regeneration_script": "bistar_viz/scripts/viz_unification_compare.py",
+            "pinned_legacy_commit": "a87356a",
+        },
+        "interpretation_scope": (
+            "informative-config, MAP-based methods-validation and legacy-comparison "
+            "material; the comparison evaluates the occam convention, not which "
+            "model generated the data"
+        ),
+    }
+    json_path = out_dir / "figure_results.json"
+    json_path.write_text(
+        json.dumps(_native(results), indent=2, sort_keys=True, ensure_ascii=False) + "\n",
+        encoding="utf-8",
+    )
+    figure_path = out_dir / "occam_dial.png"
+    _plot(arms, figure_path)
+    if figure_path.stat().st_size >= 2_000_000:
+        raise AssertionError(f"{figure_path} exceeds the 2 MB figure limit")
+    write_combined_readme(out_dir)
+    return results
+
+
+def main() -> None:
+    parser = argparse.ArgumentParser(description=__doc__)
+    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
+    parser.add_argument("--n-is", type=int, default=N_IS)
+    parser.add_argument(
+        "--anchor-tolerance", type=float, default=ANCHOR_TOLERANCE
+    )
+    args = parser.parse_args()
+    results = run(
+        args.out_dir.resolve(),
+        n_is=args.n_is,
+        anchor_tolerance=args.anchor_tolerance,
+    )
+    print("n=50 model posteriors")
+    for arm_name, arm in results["arms"].items():
+        print(f"  {arm_name}: {_fmt_posteriors(arm)}")
+    print(f"wrote {args.out_dir.resolve() / 'figure_results.json'}")
+    print(f"wrote {args.out_dir.resolve() / 'occam_dial.png'}")
+
+
+if __name__ == "__main__":
+    main()
diff --git a/runs/occam_dial/README.md b/runs/occam_dial/README.md
new file mode 100644
index 0000000..1a14cd1
--- /dev/null
+++ b/runs/occam_dial/README.md
@@ -0,0 +1,49 @@
+# Case B: Occam dial and nesting monotonicity
+
+Regenerate from the repository root:
+
+```bash
+python experiments/occam_dial_figure.py
+python experiments/e6_nesting_monotonicity.py
+```
+
+Both scripts use local CPU computation only. They construct the n=50 averaged GP with `PRIOR_CONFIGS["informative"]`, `gp_method="map"`, data seed 42, 80 evaluation points over [-10, 10], and the primary `pw_kl_vcal` metric. MAP retains one GP predictive. The scripts import the shared construction from `bistar_viz/scripts/_viz_spaces.py` and the existing evidence machinery from `bistar_gp/laplace_evidence.py`.
+
+## Figure computation
+
+`occam_dial.png` and `figure_results.json` use τ=0.3, IS seed 0, n_is=40,000, five seeded perturbations per legacy start, and the canonical visualization parameter boxes. The optional `runs/viz_unification/delta_table.md` only supplies a cross-check when present.
+
+The anchor tolerance equals 0.003 in absolute model probability. The published anchors were rounded to three decimals, and the remaining allowance covers small cross-platform optimizer differences. The tolerance remains well below the 0.042 p2 Linear versus Sin+Linear gap.
+
+Fresh n=50 posteriors:
+
+- `p1_priors_lap_occam`: Linear 0.534121, Sinusoidal 0.075747, Sin+Linear 0.382052, Quadratic 0.008080
+- `p2_priors_is_occam`: Linear 0.506877, Sinusoidal 0.020499, Sin+Linear 0.464791, Quadratic 0.007834
+- `p3_priors_canonical`: Linear 0.007040, Sinusoidal 0.001093, Sin+Linear 0.991758, Quadratic 0.000109
+
+The optional D17 table cross-check was available.
+
+The D17-recorded legacy 0.934 and 0.693 values provide historical context only. `bistar_viz/scripts/viz_unification_compare.py`, with pinned legacy commit `a87356a`, regenerates those legacy arms. Neither new script invokes that git-based extraction path.
+
+## E6 computation
+
+E6 uses 161 log-spaced τ values from 10^-1.5 through 10^2.5, IS seed 0, n_is=100,000, and the same five perturbations per start. One `is_log_Z_Mx` call per model computes the full raw sweep; the package's `_log_reference_volume` helper supplies the occam-normalized sweep. The visualization box uses A >= 0.01 for numerical plotting. E6 alone extends the encompassing Sin+Linear box to A >= 0 so Linear at A=0 forms an exact restriction. All other bounds match the canonical visualization boxes. The embedded restricted optima seed the encompassing multi-start optimization. IS uses interior perturbed starts plus the best encompassing optimum, which avoids flat boundary-Hessian components without changing the integral.
+
+The min-Ḡ comparison tolerance equals 1e-8 in Ḡ units. It only classifies floating-point near-ties and remains many orders of magnitude below the observed margins. τ crossings use linear interpolation in log10(τ) inside the reported adjacent grid bracket; the bracket, rather than extra decimal places in the interpolant, provides the resolution statement.
+
+Fresh E6 results:
+
+- `Linear_within_Sin+Linear`: min Ḡ(restricted)=2.424774370, min Ḡ(encompassing)=0.045516783, margin=2.379257587, holds=True.
+  - `occam_false`: no crossing on the grid.
+  - `occam_true`: 0.295184 within [0.281838, 0.298538].
+- `Sinusoidal_within_Sin+Linear`: min Ḡ(restricted)=2.546229649, min Ḡ(encompassing)=0.045516783, margin=2.500712865, holds=True.
+  - `occam_false`: no crossing on the grid.
+  - `occam_true`: 1.484355 within [1.412538, 1.496236].
+
+E6 verdict: Both numerical min-Ḡ inequalities hold on the n=50 informative-config, MAP-based toy GP. E6 supports the reachable-set claim for these two exact restrictions, while the finite-τ Z_M ordering still depends on the reference-measure convention.
+
+## Files
+
+- `occam_dial.png`: E4 attribution-ladder figure, kept below 2 MB.
+- `figure_results.json`: all freshly computed E4 arm values and anchor checks.
+- `e6_results.json`: min-Ḡ optima, exact-embedding checks, both Z_M conventions, ESS diagnostics, the full τ grid, and crossing brackets.

