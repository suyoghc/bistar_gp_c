# Round-1 review — Opus 5 (fresh in-session subagent, repo read access)

**VERDICT: REVISE** — two S2 findings (a factual misattribution repeated in four
artifacts, and one-sided reporting of a comparative diagnostic), one S2 framing
overreach, plus eight S3 and four S4 items. No S1: the additive-kernel
mathematics, the marginalization argument, the mixture-interval construction and
the slope read are all correct, and I reproduced every reported number
independently, bit-for-bit at the printed precision.

Verification basis: I re-executed the committed pipeline through the committed
script's own entry points (`run_chains`, `decompose_draws`,
`mixture_central_interval`, `total_variance_sd`, `rmse`) from a scratchpad
driver, writing nothing into the repository, and additionally computed four
quantities the artifact does not record. Every reproduced value matched
`results.json` exactly. New numbers cited below are from that run and are
reproducible by the same seeds.

---

## Findings

### F1 — S2 — The `toy_elicited` posterior is not multi-basin; D12's bimodality belongs to the `informative` configuration

**Where (four artifacts, same sentence):**
- `docs/paper-sie-jmp/07-debias-bridge.md:26-28`
- `runs/toy_debias_demo/results.json:17` (`config.init_strategy`)
- `runs/toy_debias_demo/README.md:38`
- `Notes/DECISIONS.md:6346` (D67, INIT DISCLOSURE)
- generated from `experiments/toy_debias_demo.py:158`, `:522`, `:757`

**Defective text** (section 07): "Both chains initialize at the same MAP point,
so the rank-normalized R-hat reported here measures mixing within the mode the
optimizer selected and not agreement between dispersed starts; **the toy
hyperparameter posterior is multi-basin, which makes the distinction worth
stating explicitly.**"

**Why it is wrong.** D12's bimodality result is explicitly scoped to a different
prior configuration: `Notes/DECISIONS.md:485` reads "**The hyperparameter
posterior is bimodal** under the `informative` priors", with the two modes at
noise 0.0736 / ls 2.18 and noise 0.5917 / ls 8.43 and a valley near −43. The run
under review does not use that configuration; it uses `toy_elicited_n20`, and
the repository's own prior-sensitivity artifact certifies the opposite geometry
for it. `runs/prior_sensitivity/stage_a_toy_elicited.json` records
`"coherent_geometry": true`, `"valleys": []`, and a single entry in `modes` with
`"verified_local_max": true` and `"pooled_is_mass": 1.0`. That mode's converged
values (ls 1.4629303978786417, os 0.713868711215515, lv 0.018307933126650966,
noise 0.06186741902432317) agree with this run's `config.map_point` to about
1e-9, so it is demonstrably the same basin, found by an independent wide-start
Nelder-Mead hunt. The `informative` configuration is the one recorded as
`"coherent_geometry": false`.

The disclosure itself is good practice and should stay. Its stated *justification*
is false, and as written it gratuitously casts doubt on the run's own posterior
summaries: a reader who believes the posterior is multi-basin must discount the
slope interval, the coverage number, and both band widths, since all four depend
on the full hyperparameter spread and not just on R-hat.

**Fix.** Replace the clause in all four places with the correct provenance, e.g.
in section 07: "Both chains initialize at the same MAP point, so the
rank-normalized R-hat reported here measures mixing within the mode the
optimizer selected and not agreement between dispersed starts. The multi-basin
hyperparameter geometry recorded for the `informative` configuration (D12) does
not carry over: the wide-start mode hunt for this configuration verified a single
local maximum holding the whole pooled prior-importance-sampling mass, with no
separating valley, and its converged point matches the MAP used here. The shared
init is therefore a cost-control choice, and the disclosure is retained because a
common start still leaves R-hat silent about exploration." Adjust
`config.init_strategy`, the README bullet, and D67 to match, and add
`runs/prior_sensitivity/stage_a_toy_elicited.json` to footnote 2.

---

### F2 — S2 — The debiased arm's coverage is reported; the composite arm's is not, and the omitted number reverses the natural reading

**Where:** `docs/paper-sie-jmp/07-debias-bridge.md:68-72`;
`runs/toy_debias_demo/results.json` `recovery` block;
`experiments/toy_debias_demo.py:674-694` (only `covered` is computed).

**Defective text:** "The debiased band covers sin(x) at 174 of the 201 grid
points, 0.866 against a nominal 0.95. … read that way it records mild
undercoverage and not a validated interval procedure."

**Why it matters.** The section computes coverage for exactly one of the two
bands it discusses, and it is the band it is arguing *for*. Using the identical
grid, mixture-interval construction and draws, I measured the composite band
against its own known truth, sin(x) + 0.25x: **0.8209 (165 of 201 points)** —
worse than the debiased arm's 0.8657. The bias band covers 0.25x at **201 of
201** points. So marginalization does not cost calibration here; if anything the
debiased arm is the better-calibrated of the two. As committed, "mild
undercoverage" attaches only to the debiased band and reads as a debit against
the method, which the full picture does not support. One-sided reporting of a
comparative diagnostic is a substantive reporting defect, not a stylistic one,
and the missing number costs nothing to produce.

**Fix.** Add `coverage_composite`, `coverage_composite_points_covered`, and
`coverage_bias` to `recovery` in `results.json` (three lines in
`experiments/toy_debias_demo.py` alongside the existing `covered` computation),
put them in the README table, and rewrite the section sentence as: "The debiased
band covers sin(x) at 174 of the 201 grid points, 0.866 against a nominal 0.95;
on the same grid the composite band covers sin(x) + 0.25x at 165 points, 0.821,
and the bias band covers 0.25x at all 201. Neighboring grid points share nearly
the same posterior, so these are pointwise summaries rather than calibration
tests over independent trials; read that way both arms record mild
undercoverage of a comparable size, and marginalization does not pay for its
wider band with calibration."

---

### F3 — S2 — The uncertainty-floor sentence makes an asymptotic claim from a single fixed sample size

**Where:** `docs/paper-sie-jmp/07-debias-bridge.md:90-95`.

**Defective text:** "That difference gives concrete form to the expectation
recorded in section 8.5: when the grounds for treating one component as bias
come from outside the observed data, **additional observations sharpen the
composite while leaving the attribution comparatively uncertain**, and honest
inference retains **an uncertainty floor that sample size does not remove**."

**Why it is unsupported.** The experiment fixes N=20 (`generate_toy_data()` at
defaults) and varies nothing. Two width numbers at one sample size are evidence
about the posterior correlation between components at that sample size — and the
correlation is real and strong: from the same draws, the mean total variances are
0.2368 (SE component), 0.1752 (linear component) and 0.0667 (composite), which
forces a posterior cross-covariance near −0.173 and a component correlation near
−0.85. That is a genuine and interesting finding. It says nothing whatever about
the N-asymptotics, and for this particular model the asymptotics plausibly run
the other way: the bias component is a one-parameter family (`LinearKernel` gives
f_lin(x) = b·x with b scalar), the SE lengthscale is bounded by a proper prior,
and sd(b | y) is already about a third of its prior scale at N=20 (0.0721 against
roughly 0.213, the prior sd implied by the posterior median σ²_b = 0.0453).
Nothing in the artifact indicates that this shrinks to a positive floor rather
than to zero. Section 8.5's own footnote states that none of the
committed cases estimates an uncertainty floor; section 7 should not be the place
where the claim is quietly upgraded from expectation to demonstration.

**Fix.** Either (a) restrict the sentence to what was measured — "At this sample
size the data pin the sum far better than the split: the two components carry a
posterior correlation near −0.85, so the composite band is narrower than either
component's. Whether that gap persists as N grows is the substantive form of the
expectation recorded in section 8.5, and this demonstration does not test it." —
or (b) add the test, which is cheap: rerun the identical pipeline at
n_points ∈ {20, 50, 200} (`generate_toy_data(n_points=…)`, ~1 min each) and
record debiased band mean width and Var(b | y) per N in `results.json`. If the
widths plateau, the section earns the floor claim outright; if they do not, (a)
is the honest wording and the finding is still worth reporting.

---

### F4 — S3 — "either component alone" is true but not evidenced by any committed number

**Where:** `docs/paper-sie-jmp/07-debias-bridge.md:88-90`;
`runs/toy_debias_demo/results.json` `recovery` (has
`debiased_band_mean_width` and `composite_band_mean_width`, not the bias band's).

**Defective text:** "The debiased band has mean width 1.836 on the grid while the
composite band has mean width 1.032, so the observations constrain the sum of the
two components more tightly than they constrain **either component alone**."

**Assessment.** The claim is correct — I measured the bias-component band mean
width at **1.4584** on the same grid, also above 1.032 — but a reader cannot
check "either" from the artifact, which reports only two of the three widths. A
claim whose scope exceeds the committed numbers should not stand in a section
whose provenance rule is that every reported number is regenerable from a named
artifact.

**Fix.** Add `bias_band_mean_width` (1.4584026383414934) to `recovery` in
`results.json` and the README table — one line in
`experiments/toy_debias_demo.py` next to the existing two widths — and quote it
in the section: "…while the composite band has mean width 1.032 and the linear
component's 1.458, so the observations constrain the sum more tightly than either
component alone."

---

### F5 — S3 — "It removes most of it" is supported by the wrong statistic

**Where:** `docs/paper-sie-jmp/07-debias-bridge.md:61-66`.

**Defective text:** "The debias claim concerns how much of that known
displacement marginalization removes, and it removes most of it. What remains,
0.403, is not negligible against the true process's own RMS of 0.690."

**Why.** The preceding sentence's "71.9 percent" is a reduction in RMSE-against-
sin(x), not the fraction of the drift removed, and the section then uses it to
support a statement about displacement removal. The direct quantity is available
in closed form from numbers already committed: the un-removed drift is
(0.25 − 0.19749504453874142)·x, whose grid RMS is 0.05250495546 × 5.802298 =
**0.3046**, so marginalization removes **79.0%** of the drift, not 71.9%.
Separately, the composition of the 0.403 residual is currently left opaque, and
it is informative: removing the *known* drift 0.25x from the composite mean
leaves RMSE **0.3210**, so of the debiased squared error, 0.3046²/0.4025² =
**57%** is attributable to the 21% slope shortfall and the remainder to SE
misfit. That decomposition strengthens the section's own honesty point instead of
weakening it.

**Fix.** Rewrite as: "The debias claim concerns how much of that known
displacement marginalization removes. The posterior slope falls 0.053 short of
0.250, so the drift left in place has RMS 0.305 and marginalization removes 79.0
percent of it. What remains in the debiased arm, 0.403, is not negligible against
the true process's own RMS of 0.690, and about 57 percent of that residual
squared error is the unremoved drift rather than misfit of the smooth component:
subtracting the known 0.25x from the composite mean instead of the estimated
component would leave 0.321." Add `rmse_composite_oracle_debiased` (0.3210435)
and `bias_fraction_removed` (0.78998) to `recovery` so the numbers are
regenerable.

---

### F6 — S3 — Latent-function bands are labelled "posterior predictive", and panel (a)'s fit claim is unquantified

**Where:** `docs/paper-sie-jmp/07-debias-bridge.md:35` ("The debiased predictive
of the true process"), `:46-48` (caption), `experiments/toy_debias_demo.py:404`
("(a) Composite posterior predictive"), `:440` ("(c) Debiased predictive"),
`:33-35` (module docstring, "The debiased predictive is therefore the finite
mixture…").

**Defective text:** "Panel (a) shows the composite posterior predictive against
the observed data, which the composite describes well."

**Why.** The section states two lines earlier that "all bands are latent-function
bands with no observation noise added", which is exactly right and is what the
code does (`bistar_gp/decompose.py:73` returns
K\*\* − Vᵀ V with no σ²_y added to the test covariance). A posterior predictive
for y includes observation noise; calling a noise-free latent band a posterior
predictive is a terminology error a methods-journal reviewer will flag, and it is
not harmless here: panel (a) invites the reader to judge fit by whether the
crosses sit in the blue band, and in the rendered figure several observations
(near x ≈ −4.6, 0.5, 9.0) fall visibly outside it, exactly as a latent band
should behave with noise sd ≈ 0.34. No goodness-of-fit statistic for the
composite arm is reported anywhere, so "describes well" rests on nothing.

**Fix.** Retitle the panels "(a) Composite latent posterior" and "(c) Debiased
latent posterior against the known truth"; change "The debiased predictive of the
true process consists of" to "The debiased posterior for the true process is";
and either add a σ²_y-inflated predictive band to panel (a) alone (clearly
labelled, since it is the only panel where data are plotted) or replace "which
the composite describes well" with the composite coverage number from F2.

---

### F7 — S3 — The figure cannot show the width contrast the section's main argument rests on

**Where:** `experiments/toy_debias_demo.py:392`
(`plt.subplots(1, 3, figsize=(15.0, 4.6), sharex=True)`).

**Why.** `sharey` is not set, so panel (a) renders on roughly [−3.3, 3.3] and
panel (c) on roughly [−2.7, 2.3]. The reader therefore cannot see that the
debiased band (1.836) is nearly twice the composite band (1.032) — the single
comparison that carries section 7.2. Separately, panel (c) replots exactly the
same `truth_mean`/`truth_lo`/`truth_hi` arrays as panel (b), so the "three
readings" are two distinct posteriors plus a crop.

**Fix.** Pass `sharey=True`, or annotate each of panels (a) and (c) with its mean
band width. Optionally repurpose panel (c) to plot the pointwise band widths of
the three objects (composite, SE component, linear component) on one axis, which
would make the section's argument visible instead of asserted.

---

### F8 — S3 — `build_tex.py` was not updated, so the documented regeneration path will silently emit the stub and a broken figure reference

**Where:** `docs/paper-sie-jmp/build_tex.py:38`, `:43-47`, `:50-54`;
`Notes/DECISIONS.md` D67 **Status**.

**Defective text (D67 Status):** "the derived
`docs/paper-sie-jmp/tex/sections/07-debias.tex` still holds the old stub text and
needs regeneration through `docs/paper-sie-jmp/build_tex.py` at assembly time."

**Why that is not sufficient.** Three registry entries are missing, and
`docs/paper-sie-jmp/` is inside the branch's declared commit scope, so this
belongs in this commit:
1. `SECTIONS` line 38 is
   `("docs/paper-sie-jmp/07-debias-bridge.md", None, "07-debias")`. `None` means
   "read the working tree"; every other case entry names its branch. Run from any
   other branch, the build will pick up whatever 07 file the working tree holds —
   on `main` that is nothing, and the previously generated stub in
   `tex/sections/07-debias.tex` survives with no error.
2. `FIGURES` has no entry for the new figure, so
   `runs/toy_debias_demo/debias_figure.png` is never copied into the LaTeX tree.
3. `FIGURE_PATHS` has no entry for
   `"../../runs/toy_debias_demo/debias_figure.png"`, so `preprocess` leaves the
   Markdown path untouched and pandoc emits
   `\includegraphics{../../runs/toy_debias_demo/debias_figure.png}`, which will
   not resolve.

**Fix.** In the same commit: set the `SECTIONS` branch to
`"paper/case-e-debias"`; append
`("runs/toy_debias_demo/debias_figure.png", "paper/case-e-debias", "debias_figure.png")`
to `FIGURES`; and append
`"../../runs/toy_debias_demo/debias_figure.png": "debias_figure.png"` to
`FIGURE_PATHS`. Then amend D67 Status to say the registries are updated and only
regeneration remains.

---

### F9 — S3 — Section 8.6's universal quantifier over cases becomes false once Case E is section 7

**Where:** `docs/paper-sie-jmp/08-discussion.md:142-145` (on
`paper/synthesis-sections`).

**Defective text:** "Each case section underwent independent review within a
four-model adversarial cross-verification protocol. **All four reviewer rounds
are recorded for every case**, with the fourth, Kimi K3, run at the author's
direction on the same round-1 packages. The findings, refutations, fixes, and
author sign-off records are committed under `runs/<case>/reviews/`…"

**Why this is sharper than the known §8.5 footnote item.** The known item is a
wording fix ("supplies no reported number"). This one is a factual universal
claim that Case E cannot satisfy as the round is currently constituted: the
driver record states Codex (gpt-5.6-sol) is usage-locked until 2026-08-18 and
absent, so Case E's round has three models, not four. The clause also promises
`runs/<case>/reviews/` archives "for every case".

**Fix.** At assembly, change to "Every case section underwent independent
adversarial review. Cases A through D were reviewed by four models; the section 7
demonstration was reviewed by three, with the fourth reviewer unavailable in the
review window, and the substitution is disclosed in its review record." Keep the
`runs/<case>/reviews/` sentence and ensure `runs/toy_debias_demo/reviews/` is
committed. This should be logged as an open assembly item in D67 Status alongside
the §8.5 footnote item, so both are closed together.

---

### F10 — S3 — The section's opening claim has a free, already-committed instantiation that it does not use

**Where:** `docs/paper-sie-jmp/07-debias-bridge.md:5-11`.

**Defective text:** "Candidates are graded against the posterior over data
patterns ψ, and that posterior supports more than grading. … Evaluation and
mitigation therefore draw on one object."

**Why.** As committed, "one object" is asserted architecturally and never
exhibited: Case E computes no evaluation-side quantity, and none of Cases A–D
decomposes anything. But the link already exists in the manuscript. Section 3.4
(`paper/case-a-vanbork`, lines 146-152) reports, on the *same* frozen N=20 seed-42
toy under the *same* `toy_elicited` configuration, pooled `pw_kl_vcal` model
probabilities 0.183 / 0.192 / **0.441** / 0.184 for Linear, Sinusoidal,
**Sin+Linear**, and Quadratic at τ=1. The winning candidate there is precisely the
SE-plus-linear additive structure that section 7 then splits into a truth
component and a bias component. Naming that costs one sentence, requires no new
computation, and converts the section's central claim from assertion to
demonstration.

**Fix.** After line 11 or at the head of 7.1, add: "Section 3.4 grades candidates
on this same N=20 instance under the same data-elicited configuration and puts
most weight on Sin+Linear (0.441 under `pw_kl_vcal` at τ=1 on the SIR path). The
demonstration below decomposes the posterior of that same additive structure,
sampled here on the corrected NUTS path; the two estimators are reported as
separate but agreeing (00-notation)." Cite footnote 2 plus section 3.4.

---

### F11 — S3 — The empirical-Bayes character of the prior is dropped where it matters most

**Where:** `docs/paper-sie-jmp/07-debias-bridge.md:20-22`.

**Defective text:** "The GP uses the SE plus linear additive kernel under the
`toy_elicited` data-elicited prior, the configuration validated for this N=20
instance."

**Why.** "Data-elicited" is the correct bound term (W5,
`docs/paper-sie-jmp/00-notation.md`), and "validated" is warranted
(`runs/prior_sensitivity/stage_a_toy_elicited.json` → `coherent_geometry: true`).
But the registry description (`bistar_gp/config.py:129-145`) is explicit that the
lognormal medians are set from *this realized sample's* summaries — lengthscale
4.5 from x-spacing and x-range, outputscale ≈ var(y)/2, linear variance ≈
var(y)/(2·mean(x²)), noise ≈ 10% of var(y) — and that "results under this prior
are posterior-mass-faithful conditional on the fixed prior, not unqualified
full-Bayes". Section 7 is the one section that reports a *coverage* number, which
is precisely the quantity whose interpretation the double use of the data
conditions. Cases A–D do not report coverage, so the omission has more bite here
than elsewhere.

**Fix.** Extend the sentence: "…under the `toy_elicited` data-elicited prior
(empirical-Bayes-style: the lognormal medians are set from this sample's own
observable summaries, so every posterior statement below is conditional on that
fixed prior rather than unqualified full-Bayes), the configuration validated for
this N=20 instance." Then add to the coverage paragraph that the coverage figure
inherits that conditioning.

---

### F12 — S4 — A silent-wrong-answer path in the decomposition loop

**Where:** `experiments/toy_debias_demo.py:279`
(`apply_hp_value(model_i, likelihood_i, site, float(pooled_samples[site][i]))`).

**Why.** `apply_hp_value` returns `True`/`False`
(`bistar_gp/model.py:88-116`) and the return value is discarded. If a site name
ever failed to match — a legitimate risk given the function is explicitly built
to straddle current and legacy naming eras — the freshly built model would keep
its gpytorch *default* hyperparameter, the decomposition would succeed, and the
draw would be counted in "1000 of 1000 decompositions succeed" while carrying the
wrong hyperparameters. All four sites currently resolve (I confirmed the run
reproduces exactly and that its MAP matches the independent mode hunt), so this
is latent, not active. A related gap: `compute_cholesky`
(`bistar_gp/decompose.py:29-37`) escalates jitter up to 1e-2 and returns
successfully, so `n_ok` does not distinguish a clean solve from a jitter-rescued
one.

**Fix.** `if not apply_hp_value(...): raise RuntimeError(f"unmatched HMC site {site}")`,
and record a `n_draws_needing_extra_jitter` count in
`decomposition` (by attempting `torch.linalg.cholesky` at `DECOMP_JITTER`
directly before falling back).

---

### F13 — S4 — Sampler settings in `results.json` are hardcoded mirrors, not observations

**Where:** `experiments/toy_debias_demo.py:124-125`
(`TARGET_ACCEPT = 0.8  # fixed inside fit_hmc_e1`,
`INIT_STEP_SIZE = 0.1  # fixed inside fit_hmc_e1, then adapted`) and the
`"step_size_adapted": True` literal at `:227`.

**Why.** These three values are asserted by the script and written into
`results.json` as if measured. They are currently correct — I confirmed
`bistar_gp/e1_potential.py:520-523` passes `step_size=0.1`,
`adapt_step_size=True`, `target_accept_prob=0.8` — but nothing ties the artifact
to the library, so a future change inside `fit_hmc_e1` would produce a
silently false provenance record in a paper-facing artifact.

**Fix.** Read them back from the diagnostics object where available, or add an
explicit guard, e.g. assert against
`inspect.signature`/module constants of `fit_hmc_e1` and fail loudly on drift.

---

### F14 — S4 — `acceptance_rate_by_chain` and `target_accept_prob` are different quantities sitting side by side

**Where:** `runs/toy_debias_demo/results.json` `sampler.acceptance_rate_by_chain`
= [0.992, 0.998] next to `sampler.target_accept_prob` = 0.8.

**Why.** Pyro's reported "acceptance rate" is `_accept_cnt / n_post_warmup`, the
fraction of post-warmup iterations whose proposal was accepted at all, whereas
`target_accept_prob` is the mean Metropolis accept *probability* that dual
averaging targets. Placing 0.992 next to 0.8 invites a reader to conclude
adaptation missed its target by a wide margin; it did not (the adapted step sizes
0.471 and 0.423 are sane for a 4-dimensional unconstrained target, and the values
reproduce exactly).

**Fix.** Rename to `move_fraction_by_chain`, or add a sibling note key: "fraction
of post-warmup iterations that moved, as reported by pyro; not comparable to
`target_accept_prob`, which is the targeted mean Metropolis accept probability."

---

### F15 — S4 — Divergences and depth saturation are per-draw quantities, not per-hyperparameter

**Where:** `docs/paper-sie-jmp/07-debias-bridge.md:28-30`.

**Defective text:** "**Across the four hyperparameters** the run gives no
divergences, rank-normalized R-hat at most 1.0025, bulk ESS at least 602.4, and
tail ESS at least 502.6."

**Why.** R-hat and ESS are per-site, so "across the four hyperparameters" is
right for them; divergence count is a property of the trajectory, not of a site.

**Fix.** "The run gives no divergences and no tree-depth saturation, and across
the four hyperparameters the rank-normalized R-hat is at most 1.0025, bulk ESS at
least 602.4, and tail ESS at least 502.6."

---

## What I verified clean

**Reproduction.** Re-running the committed code paths on the committed seeds
reproduced, exactly at printed precision: `rmse_composite` 1.430390061349473,
`rmse_debiased` 0.4025181154080362, `coverage` 0.8656716417910447 (174/201),
`debiased_band_mean_width` 1.8355730651608624, `composite_band_mean_width`
1.0319893656930352, slope mean 0.19749504453874142, sd 0.07214240107691616,
interval [0.03275525741517342, 0.3229918220752096], `r_hat_max`
1.002489522142068, `ess_bulk_min` 602.405863421313, `ess_tail_min`
502.6181016635812, 0 divergences, acceptance [0.992, 0.998], final step sizes
[0.4706, 0.4228], and the full `map_point`. Determinism holds as claimed.

**Additive-kernel mathematics.** `decompose_component`
(`bistar_gp/decompose.py:40-75`) returns
mᵢ = Kᵢ(X\*,X)(K_sum + σ²I)⁻¹y and Cᵢ = Kᵢ(X\*,X\*) − Kᵢ(X\*,X)(K_sum + σ²I)⁻¹Kᵢ(X,X\*),
which is exactly the marginal of the joint conditional Gaussian for component i
under a zero-mean additive GP. The section's claim that "the component posterior
the decomposition returns already forms the marginal of the joint conditional
Gaussian" is therefore correct, and "labeling one component as bias turns its
removal into marginalization" is a fair description of the estimand change from
f to f_SE. The composite arm is obtained by calling the same routine on summed
blocks, which correctly retains the inter-component cross-covariance rather than
summing component covariances; footnote 3 and D67 describe this accurately. I
confirmed the arithmetic is internally coherent: mean total variances 0.2368
(SE), 0.1752 (linear), 0.0667 (composite) imply a posterior cross-covariance of
about −0.173 and a component correlation near −0.85, which is what makes the
composite band narrower than either component's.

**Rejection of `decompose_model_hmc`.** Correct and correctly cited.
`bistar_gp/debias.py:206` is `for (mean_i, _), comp_name in zip(results, names)`
— each draw's conditional covariance is discarded and the reported std is the
across-draw spread of means alone (`:224`). Using it would have understated the
debiased band, and the demo's per-draw-moments approach is the right call. The
parallel rejection of `total_variance_decomposition` is also sound: that helper
returns summary bands only and subsamples draws via `np.random.choice`, and the
demo's use of all 1,000 draws removes an RNG dependence.

**Interval construction.** `mixture_central_interval` bisects the exact mixture
CDF (1/D)·Σ Φ((q − m_d)/s_d) over a ±12 sd bracket for 100 iterations, so "exact"
is justified to machine precision and the intervals are genuinely not
mean ± 2 sd. `total_variance_sd` implements the law of total variance correctly.
The degenerate point x = 0 for the linear component (zero variance) is handled by
the 1e-24 variance floor and does not enter any reported number.

**Slope read.** `LinearKernel` in the installed gpytorch is k(x,x′) = v·x·x′ with
no offset (`bistar_gp/config.py:260-263`), and the model uses `ZeroMean`
(`bistar_gp/model.py:23`), so f_lin(x) = b·x with b scalar and the posterior mean
is exactly linear with exactly rank-one covariance. b̂ = (m_lin[−1] − m_lin[0])/20
recovers b exactly, and Var(b) = c_lin[−1,−1]/100. The numerical structure checks
(4.456e-13 linearity, 1.896e-15 rank-one) confirm this at machine precision, so
reading slope moments off the decomposition rather than introducing a separate
formula is sound.

**Constraint compliance.** The M2bR banner is respected: the run uses
`toy_elicited` on the corrected `nuts_e1` path, never touches
`runs/fit_method_metric_comparison/samples_hmc.npz` or
`runs/toy_tau_metric_comparison/`, and cites no withdrawn `informative` HMC
number. W1 is not engaged (no metric is computed). W4 is not engaged (no
`runs/viz_unification/` number appears). No Mauna Loa material of any kind is
imported, executed, or cited — I checked the script, README, section and D67. No
`bistar_gp/` default or public API is changed. Commit scope is exactly the
permitted set, and the figure is 264 KiB, well under 2 MB.

**Style rules.** No arrow glyphs anywhere in section 07; no `lives`/`sits` for
abstracta; no "X is the Y" role-noun constructions; the only em-dashes are inside
the evidence-tier footnote markers, which are the mandated format. Section
heading and figure-caption conventions match Case B. Unicode ψ is handled by
`build_tex.py`'s `UNICODE_MATH` map, so the plain-Unicode style in 07 versus
`\(\psi\)` in 02/08 is not a build hazard.

**Bookkeeping.** D67 is the next free number: main ends at D58, Cases A–D take
D60–D65, synthesis takes D66. The chain/draw bookkeeping is correct
(`i // N_DRAWS` on a concatenation of two 500-draw chains, appended in lockstep
with the success path). The two grid scale references are exact:
RMS(0.25x) = 1.4505745987941008 and RMS(sin x) = 0.6901815271460361 on the
201-point grid, both of which I verified analytically. Every prose number in
section 07 rounds correctly from `results.json`: 0.197 / 0.072 / [0.033, 0.323]
/ 0.250 / 1.430 / 0.403 / 1.028 / 71.9% / 1.431 / 1.430 / 0.403 / 0.402 / 1.451
/ 0.690 / 174 / 201 / 0.866 / 0.95 / 1.836 / 1.032 / 1.0025 / 602.4 / 502.6 /
1,000. The evaluation grid is strictly inside the training span (training x is
`linspace(-10, 10, 20)`, grid endpoints coincide), so the "no extrapolation"
claim holds. The "byte-identical to `prior_sensitivity_study` `toy_elicited`"
claim understates the truth: `STUDY_CONFIGS["toy_elicited"]` *is*
`PRIOR_CONFIGS["toy_elicited_n20"]`, the same object
(`experiments/prior_sensitivity_study.py:156`).
