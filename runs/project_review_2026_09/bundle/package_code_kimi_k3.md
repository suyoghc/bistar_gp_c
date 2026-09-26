[CHANNEL OVERRIDE, PACKAGE-ONLY]
You are the Kimi K3 channel. You cannot run code or open the repository;
everything you may use is in this package. Claims needing execution or files
not included here must be tagged NEEDS-REPO-VERIFICATION and marked PLAUSIBLE.
This package covers PART A (code) of the brief, with Part B only as far as the code listings support it; the modules listed are the manuscript-path package; tests are named but not included. Return the complete review as your reply in the
brief's OUTPUT FORMAT (the single-output-file instruction is replaced by
"return the review text"); in section 6 state what you could not run. Sign
only as "Kimi K3 (package-only channel)". Line numbers in the listings are
the file's own line numbers at ddf8c9d; cite them as path:line.

==================== BRIEF ====================
[TASK CONTEXT]
You are one of five independent reviewers of the CURRENT CODE AND PROJECT
STATE of the BI*/BMS*-GP repository (Chandramouli & Shiffrin framework:
Gaussian-process data priors, G divergence, Boltzmann soft transfer,
Laplace/MC/IS model evidence, additive-kernel decomposition; a journal
manuscript in preparation). Review date 2026-09-26.

Code under review: the fix-branch head `ddf8c9d` on `fix/code-review-2026-09`
(PR #42, a fast-forward of `main` 7154083 plus fix passes 1/1b/1c of the
2026-09 implementation review), checked out read-only at
  /Users/sc8918/Documents/GitHub/bistar_gp_c-fix
The MAIN worktree /Users/sc8918/Documents/GitHub/bistar_gp_c (read-only) is on
`paper/case-e-debias` and holds, untracked, the manuscript apparatus:
docs/paper-sie-jmp/{00-notation.md, HANDOFF-cases.md, HANDOFF-code-review.md,
prompts/, build_tex.py, tex/sections/*.tex}. Six unmerged paper branches
(PRs #36-#41) carry the case sections and decision entries D59-D67; read them
with read-only git only (`git show origin/<branch>:<path>`, `git log`,
`git diff`, `git merge-tree`). The project map (branches, PRs, D-entry
inventory, runs/, suite counts) is in runs/project_review_2026_09/project_map.md.
Prior review records (runs/code_review_2026_09/, the case branches' review
records) are CONTEXT, not evidence, and must not bound your review: derive
your own findings, on the whole project, not only the fix-pass surface.

[SCOPE, PART A: CODE]
Does the package at `ddf8c9d` compute what the manuscript claims? Standard:
docs/paper-sie-jmp/HANDOFF-code-review.md section 2; named targets T1-T11 of
its section 3 remain in scope, now against the post-fix code. Specification:
tex/sections/02-machinery.tex (and the case sections where they state what a
number is), 00-notation.md. Hunt for: wrong mathematics, contract breaks,
silent fallbacks that substitute a different estimator, sentinels that can
win, path-dependent results (draw order, start order, dict order), numerical
regimes that matter on the paper paths (N=20 toy, tau in [0.1, 100], KL and
pw_kl_vcal magnitudes), tests that would pass against wrong code, and the
seams the fix passes left (the required `metric_name` deferred to pass 2, the
`samples` dual meaning, the implicit metric roster, provenance prose).

[SCOPE, PART B: PROJECT]
P1 Manuscript-code consistency: for each section 01-08, do the numbers,
   conventions and terms come from code at this head via a named
   experiments/ script into a runs/ artifact, and do the section's claims
   survive the fix passes (in particular FIX-2: every earlier band from
   decompose_model_hmc/mcmc was understated; which manuscript or poster
   statements inherit that, and are they marked)?
P2 Branch topology and merge plan: seven unmerged branches whose
   Notes/DECISIONS.md diverge (D59-D67 on paper branches, D68 on the fix
   branch), the A-before-C script dependency, package API changes on the fix
   branch versus what the case scripts on the paper branches expect
   (strict extraction now raises where scripts once relied on dropped draws;
   `compute_induced_prior` weighting; `soft_transfer_weighted` raising;
   `PredictiveList`; `DecompositionResult.group`). State the merge order you
   would use and the conflicts or breakages you can demonstrate.
P3 The record: HANDOFF-cases.md section 0 constraints (M2bR banner, W1
   primary metric, W4 framing, no Mauna material) honoured in the sections;
   open ledger items; D-entry statuses versus reality; the fix pass 2 list.
P4 Test suite: value of the tests on the paper paths (tautological or
   implementation-coupled tests; missing pins), the known failure, the
   fixture-gated skips, runtime.
P5 Reproducibility and provenance: runs/ artifacts versus the scripts that
   claim to produce them; hashes; the Case E oracle; what a reader of the
   manuscript could not regenerate.
P6 Publication readiness: the blocking list, the risks, and what you would
   do in the next two weeks, in priority order with effort estimates.

[PROTOCOL]
- Repo-access channels: run the suite once in the fix worktree
  (`cd /Users/sc8918/Documents/GitHub/bistar_gp_c-fix && python -m pytest
  tests/ -q -p no:cacheprovider`; expect 1346 passed, 5 skipped, 1 failed =
  the known dependency-lock drift test; report your counts and runtime), then
  probe. Package-resolution trap: `bistar_gp` is an editable install pointing
  at the MAIN worktree; a probe script outside the fix worktree imports the
  UNFIXED package unless you force the path (`PYTHONPATH=/Users/sc8918/
  Documents/GitHub/bistar_gp_c-fix` or `sys.path.insert(0, ...)`). Print
  `bistar_gp.__file__` once per probe.
- Reproduce every claim (path:line at ddf8c9d, or branch:path:line for paper
  branches, plus a command and an output excerpt). Mark each finding
  CONFIRMED (reproduced) or PLAUSIBLE (argued). Package-only channels tag
  execution-dependent claims NEEDS-REPO-VERIFICATION.
- Severity, code: S1 a manuscript-path number is wrong; S2 wrong under a
  reachable configuration; S3 latent, guarded; S4 hygiene. Severity,
  project: BLOCKER (must be resolved before submission), MAJOR (would draw a
  referee's objection or a retraction risk), MINOR.
- Adversarial stance toward every record, report and test in the repository.

[CONSTRAINTS]
- READ-ONLY on both worktrees: create, edit or delete nothing under either,
  except your single output file below; no git add/commit/stash/checkout/
  reset/branch/rebase/worktree anywhere; never touch stash@{0}.
- Scratch: only the directory named in your channel override.
- No network, no new dependencies, no Mauna Loa inference, no change to the
  dependency lock. Do not open the other channels' output files in
  runs/project_review_2026_09/ (some may exist while you work).
- Hard constraints of HANDOFF-cases.md section 0 apply to what you write:
  the informative-config HMC caches are withdrawn (never cite
  runs/fit_method_metric_comparison/samples_hmc.npz or
  runs/toy_tau_metric_comparison/); pw_kl_vcal is the primary metric and
  kl_forward appendix-only; no arrow glyphs; no "X is the Y" role-noun
  constructions; no "lives/sits" for abstracta.

[OUTPUT FORMAT]
Write EXACTLY ONE file (the path is in your channel override) with:
1. Verdict. Code: APPROVE / REVISE / REJECT, one sentence. Project: READY /
   NOT READY for submission, with the blocking list.
2. Code findings: summary table (ID, target or module, severity,
   CONFIRMED/PLAUSIBLE, path:line, one-line claim), then per-finding detail
   (what is wrong, reproduction, suggested change, the test that would pin it).
3. Project findings: summary table (ID, P1-P6, severity, CONFIRMED/PLAUSIBLE,
   location, claim), then detail, including your merge plan for P2.
4. Verified-correct list (what you checked and found right, so the
   synthesizer can see coverage).
5. Recommendations: prioritized, each with an effort estimate and what it
   unblocks.
6. Commands run and their outcomes; what you could not run.
Sign only with your channel label. Do not claim to be another reviewer.

[SUCCESS CRITERIA]
Every T1-T11 target and every P1-P6 item has an explicit judgement; every
finding carries a reproduction or is marked PLAUSIBLE; the suite counts are
reported (repo-access channels); the single output file exists.

==================== REVIEW STANDARD: HANDOFF-code-review.md sections 2-3 ====================
## 2. The standard: what "implemented correctly" means here

A finding is anything where one of these fails.

1. **Claim fidelity.** A quantity the paper names is computed by code that
   computes something else. The known instance of this class, already
   confirmed and still open on #40's ledger, is the Ḡ plug-in surrogate
   (§3, T1); find the rest.
2. **Commitment enforcement.** A decision recorded in `Notes/DECISIONS.md` or
   the writeup banners is not actually enforced by the code that is supposed
   to enforce it, so a caller can silently violate it. The precedent is the A4
   universe firewall, which accepted mixed candidate universes and silently
   normalized across them until it was guarded.
3. **Silent-wrong-answer paths.** A failure that produces a plausible number
   instead of an error. Discarded return values, swallowed exceptions,
   fallbacks that substitute a different estimator, and jitter escalation that
   is not counted all belong here.
4. **Estimator honesty.** An uncertainty summary that understates or
   misdescribes what it measures, or a diagnostic reported next to a quantity
   it is not comparable with.
5. **Reproducibility.** A committed artifact that the named script does not
   regenerate, or regenerates differently, within its stated tolerance.
6. **Test adequacy.** A claim the manuscript rests on that no test would catch
   if it broke.

### Severity

- **S1** — a number, figure, or artifact the manuscript or the D58 poster
  presents is wrong, or is right only by accident.
- **S2** — substantive: the computation diverges from the claim, a commitment
  is unenforced, or an uncertainty is materially misstated, but no published
  number is yet known to be wrong.
- **S3** — scope, robustness, or an unexercised silent-failure path.
- **S4** — hygiene, naming, or documentation that could mislead a future
  maintainer.

Every finding needs a **concrete failure scenario**: inputs or a call sequence
that produce the wrong outcome. A finding with no failure scenario is a
question, and belongs in the questions section instead.

---

## 3. Named targets

These come from the driver's scan of 2026-09-05. They are **starting points, not
conclusions**. Confirm or refute each on the evidence, and say which. Finding
that a named target is a non-issue is a useful result; report it under "what I
verified clean" with the reasoning. Do not stop at this list.

**T1 — the Ḡ plug-in surrogate.** `bistar_gp/laplace_evidence.py:135` passes
`avg_gp.mean, avg_gp.cov` to the metric, so G is evaluated once against a
moment-matched averaged pattern rather than averaged over per-draw
divergences. `docs/paper-sie-jmp/00-notation.md` glosses Ḡ as averaged across
data patterns. The synthesis review confirmed the gap and the section now
calls the quantity a plug-in surrogate; the notation amendment remains open on
#40's ledger. Question for the reviewer: which committed numbers depend on the
difference, and is the surrogate's error bounded or characterized anywhere?
Driver observation to follow up: the averaged-pattern construction at
`bistar_gp/aggregation_v3.py:77` (`mu_bar = w @ means`) emits divide-by-zero,
overflow, and invalid-value RuntimeWarnings during
`tests/test_zmx_estimators.py::test_prior_stage_flows_to_finite_is_log_Z`.
The weight validator just above rejects non-finite weights, so the
non-finite values arrive in `means`. Establish whether that is confined to
deliberate prior-stage stress inputs or can reach a reported number.

**T2 — the decomposition routines discard per-draw conditional covariance.**
*Driver correction, 2026-09-06 (raised by the Codex channel): the two affected
routines are `decompose_model_mcmc` (`bistar_gp/debias.py:131`) and
`decompose_model_hmc` (`:206`). The MAP wrapper `decompose_model` is NOT
affected; it computes the full posterior covariance from summed kernel blocks
at `:70-84` and explicitly retains inter-component cross-covariance. The
original wording of this target named the wrong function.*
`decompose_model_mcmc` and `decompose_model_hmc` iterate
`for (mean_i, _), comp_name in zip(...)` (`bistar_gp/debias.py:131` and
`:206`), dropping each draw's covariance, and both report
`cov=np.diag(std**2)` (`:144`, `:225`) where `std` is the across-draw spread
of means alone. Case E deliberately avoided this routine for that reason.
Live callers of the HMC variant:
`experiments/toy_example.py:87`, `experiments/mauna_loa.py:74`,
`experiments/bistar_debias_mauna_loa.py:410`,
`experiments/poster_d58_mauna.py:459`. A local workaround exists at
`experiments/honest_band_decomposition.py`, and
`experiments/toy_n20_poster_figures.py:80` carries a comment about it.
Question: does any **paper-facing or D58-poster-facing** band understate
uncertainty as a result, and if so by how much? Treat this as potentially S1.

**T3 — aggregation dial enforcement.** D60 fixed pooled aggregation as
canonical with `normalize_per_draw=False` shipped unchanged
(`bistar_gp/bms_star.py:412`, `:513`). The global-shift stabilization at
`:449-455` carries a comment arguing a per-row max would silently behave like
`normalize_per_draw` even when the flag is False. Verify that argument is
correct and that the shift actually cancels in the normalization.

**T4 — MLL weight concentration.** BMS\* averages Boltzmann weights across GP
draws. `bistar_gp/induced_prior.py` computes an effective sample size for its
own importance sampling, but the driver found no Pareto-k or ESS diagnostic on
the weights that drive model scores. Question: can a small number of draws
dominate a reported model probability without any diagnostic firing, and does
that occur in any committed artifact?

**T5 — the evaluation grid.** `bistar_gp/config.py:172` sets `n_eval: int =
60` as a default, and every pointwise divergence averages over exactly those
locations. Question: is any reported conclusion sensitive to the grid's size
or placement, and is the choice documented anywhere as a choice?

**T6 — metric scoping (W1).** `pw_kl_vcal` is the primary metric and
`kl_forward` is appendix-only. Question: is that enforced in code, or is it
convention that a caller can silently violate?

**T7 — the M2bR banner.** The `informative`-config HMC results are WITHDRAWN;
`runs/fit_method_metric_comparison/samples_hmc.npz` and
`runs/toy_tau_metric_comparison/` must never be cited. Question: does any code
path read, regenerate, or surface those artifacts in a way that could reach a
paper-facing number?

**T8 — universe firewall completeness.**
`_assert_candidate_universes_consistent` (`bistar_gp/bms_star.py:480`) closed
the A4 gap, and `run_bms_star` calls it at `:529`. But `soft_transfer`
(`:409`) and `compute_G_matrix` (`:368`) are public and perform the
aggregation without passing through that guard. Question: can a caller reach a
normalized cross-universe probability through the primitives, and does
anything in `experiments/` do so? Also check whether an untagged or
partially-tagged roster still passes the guard itself.

**T9 — Case E's new script.** `experiments/toy_debias_demo.py` (committed at
`8f1326d`, hardened at `a5b9cf8`) has never been seen by Codex. It carries an
AST-based guard asserting the library's sampler constants, a raise on
unmatched hyperparameter sites, and a jitter probe. Audit all three, plus the
mixture-interval construction and the law-of-total-variance inversion added in
the fix pass.

**T10 — test adequacy.** 67 test files. Question: for each of the
manuscript's load-bearing claims, would any test fail if the claim stopped
holding? Name the claims that no test protects.

**T11 — sentinel returns and swallowed exceptions in the evidence path.**
`bistar_gp/laplace_evidence.py:126-127` catches bare `Exception` and returns
`1e6`; `:136-137` catches `LinAlgError`/`ValueError` and returns `1e6`. Under
`exp(-G/tau)` a score of 1e6 becomes indistinguishable from zero weight, so a
parameter region that fails numerically is scored as an extremely poor fit
rather than reported as a failure. `_log_likelihood` returns `-1e10` on any
exception (`:253`), and both Laplace optimizers fall back to the starting
point when `minimize` raises (`:268` sets `converged=False`; `:486` records no
flag at all). Questions: how often does each path fire in the committed runs,
does anything downstream inspect `converged`, and can a Z_M or a model
probability in the manuscript depend on a silently substituted sentinel?

---


==================== NOTATION ====================
# Frozen notation — JMP special-issue manuscript

All sections and case studies use these symbols; do not restate or vary them.
Frozen 2026-08-11 (W7 plan). Changes require editing this file first and
propagating.

| Symbol | Meaning | Source of truth |
|---|---|---|
| ψ (psi) | one data pattern: a probability distribution over outcomes at the evaluation points; one BI* table row. In the GP implementation, a sampled function f with observation variance defines ψ = N(f(x), σ²_ψ I) | JMP 2016 Fig. 1; thesis ch. 5 |
| p₀(ψ) | the data prior: the distribution over data patterns induced by the GP hyperpriors (sample hyperparameters, then a function) | mechanism figure |
| ℓ, σ²_SE, σ²_b, σ²_y | kernel hyperparameters: SE lengthscale, SE variance, linear-kernel variance, observation-noise variance | `bistar_gp/config.py` |
| G(ψ, θ) | divergence between one data pattern and one candidate predictive; per-draw, UNAVERAGED | `bistar_gp/metrics_v2.py` |
| Ḡ(φ) | G averaged across data patterns, as a function of candidate parameters φ; the object inside Z_M | `bistar_gp/laplace_evidence.py` |
| pw_kl_vcal | primary metric (W1): variance-calibrated pointwise KL, equal to GP-uncertainty-weighted MSE | W1; D10 |
| kl_forward | appendix-only stress metric (W1): full joint KL, covariance-sensitive | W1 |
| τ (tau) | Boltzmann temperature of soft transfer; τ→0 recovers hard best-match partitioning; always reported as a sweep | BMS-star Framework |
| soft transfer | p(θ \| y) ∝ Σᵢ exp(−G(ψᵢ, θ)/τ) under the POOLED convention; the aggregation-convention choice is stated explicitly wherever it matters (Case A) | D60; E7 |
| Z_M | induced model prior: ∫ exp(−Ḡ(φ)/τ) dφ (occam=False) or the V_ref-normalized variant (occam=True) | GP-Induced Model Priors |
| occam | the reference-measure flag on Z_M: False = raw Lebesgue (canonical, faithful to original BI*), True = normalize by V_ref | D3, D5, D17 |
| M_r ⊂ M_e | restricted model nested in encompassing model (van Bork et al.'s notation, adopted for Cases A/B/C) | vanBork ingest |
| SIR / prior-IS / NUTS | estimator names; toy_elicited SIR 0.441 and corrected NUTS ≈ 0.42 reported as separate-but-agreeing (M2bR banner) | WRITEUP_DECISIONS banner |

Terminology rules (W5 + global style): the N=20 toy prior is "data-elicited"
(empirical-Bayes-style, elicited from observable statistics only); uncertainty
reported at two layers (conditional bootstrap SE; independent-pool scatter).
No arrow glyphs in prose; no "X is the Y" role-noun constructions.

==================== SPECIFICATION: section 02 (machinery), LaTeX ====================
%% Generated from docs/paper-sie-jmp/02-machinery.md
%% Source branch: paper/synthesis-sections
%% Do not hand-edit; see docs/paper-sie-jmp/build_tex.py
\section{Machinery}

\subsection{From the BI* table to a GP data prior}

The BI* table begins with possible data patterns \(\psi\) as rows and possible
observations as columns. A row carries prior weight \(p_0(\psi)\); observing a
column updates the row weights by Bayes' rule. Candidate models enter only after
that data-space update, through the predictive patterns they can reproduce.
Figure 1 of the foundational JMP account gives the finite construction.\footnote{\evidencetier{peer-reviewed} Chandramouli and Shiffrin (2016), ``Extending Bayesian induction,'' \emph{Journal of Mathematical Psychology}, 72, 38--42; Shiffrin, Chandramouli, and Grünwald (2016), ``Bayes factors, relations to minimum description length, and overlapping model classes,'' \emph{Journal of Mathematical Psychology}, 72, 56--77.}

A Gaussian process replaces enumeration with a generative data prior. Draw the
kernel hyperparameters, draw a function conditional on them, and combine that
function with observation variance to obtain one \(\psi\). Repetition induces
\(p_0(\psi)\). The squared-exponential plus linear construction uses four
positive hyperparameters with direct qualitative interpretations: \(\ell\)
controls the scale over which nonlinear variation remains smooth,
\(\sigma^2_{SE}\) controls the amplitude of that smooth variation,
\(\sigma^2_b\) controls the strength of linear trend, and \(\sigma^2_y\)
controls observation-scale variation. Gamma hyperpriors in the prior-only
mechanism illustration make those beliefs inspectable before data enter.\footnote{\evidencetier{empirical} \texttt{bistar\_gp/config.py}; the prior-only arm of \texttt{experiments/mechanism\_figure\_poster.py}, local methods material that remains uncommitted in this repository, serves construction visualization and supplies no reported number or posterior estimate.}

The mechanism illustration has an \texttt{informative}-configuration,
prior-predictive methods-validation role. It explains the construction rather
than supplying a paper-facing posterior estimate. Each case states its own GP
configuration and inferential path; no \texttt{informative}-configuration HMC result
enters the account here.

\subsection{\texorpdfstring{Projection, induced priors, and \(Z_M\)}{Projection, induced priors, and Z\_M}}

For a candidate family, projection fits the candidate instance that minimizes
\(G(\psi,\theta)\) for each sampled pattern. Under \texttt{pw\_kl\_vcal}, the candidate
variance is calibrated to the GP pattern, so the parameter-dependent part of
the divergence reduces to variance-weighted squared error. When a drawn pattern
carries one scalar noise variance shared across the evaluation locations, that
weight factors out of the minimization, and the variance-calibrated argmin
coincides with the Gaussian maximum-likelihood refit. The correspondence holds
algebraically rather than as a sampled regularity. Where the pattern variance
varies across locations, the weights no longer factor out and the two
projections need no longer coincide. The collection of fitted instances should
be read as samples from the pushforward of \(p_0(\psi)\) through this
projection, not as draws from a separately elicited within-model parameter
prior.\footnote{\evidencetier{empirical} the \texttt{pw\_kl\_vcal} definition in \texttt{bistar\_gp/metrics\_v2.py}, from which the shared-scalar-variance coincidence of the two projections follows algebraically; conceptual account in \texttt{kb/Wiki/GP-Induced\ Model\ Priors.md}.}

Model-level induction averages before integrating. For candidate parameters
\(\phi\), \(\bar G(\phi)\) averages \(G\) across data patterns, and

\[
Z_M = \int \exp\{-\bar G(\phi)/\tau\}\,d\phi.
\]

The implementation reaches that average by moment matching rather than by
averaging per-draw divergences. It first collapses the sampled patterns into a
single averaged pattern \(\bar\psi\), whose mean equals the weighted mean of the
per-draw means and whose covariance adds a between-draw mean-spread term to the
weighted average of the per-draw covariances, and then evaluates \(G\) once
against \(\bar\psi\). The computed object therefore reports the divergence from
\(\bar\psi\) rather than the mean of the per-draw divergences, and the
discrepancy between them varies with \(\phi\), so it does not cancel from a
normalized comparison across candidates. Take the notation's ``averaged across
data patterns'' gloss as the intended reading of \(\bar G(\phi)\) and the
moment-matched evaluation as the plug-in surrogate for it used throughout. The
surrogate is not consistent for the per-draw average, because the gap between
them reflects the construction rather than sampling error that accumulating
draws would remove.\footnote{\evidencetier{empirical} \texttt{bistar\_gp/aggregation\_v3.py}, whose \texttt{average\_gp\_posterior} forms the weighted mean and the covariance carrying the between-draw mean-spread term, and \texttt{bistar\_gp/laplace\_evidence.py}, whose \texttt{compute\_G\_at\_params} evaluates the divergence against that averaged pattern.}

With \texttt{occam=False}, the integral uses raw Lebesgue measure, which follows the
canonical BI* convention. With \texttt{occam=True}, division by \(V_{\mathrm{ref}}\)
changes the reference measure from total compatible volume to average
compatible density. The flag therefore encodes a substantive position on how
parameter-region volume should affect a model prior; it does not merely select
a numerical correction. Case B, section 4, demonstrates that consequence under
the required \texttt{informative}-configuration, MAP-based methods-validation
framing.\footnote{\evidencetier{empirical} assembled-manuscript section 4 on \texttt{paper/case-b-occam-dial}; \texttt{experiments/occam\_dial\_figure.py}; \texttt{experiments/e6\_nesting\_monotonicity.py}; \texttt{runs/occam\_dial/}; Notes/DECISIONS.md D17 and D62.}

\subsection{Soft transfer, temperature, and aggregation}

Soft transfer retains per-pattern variation rather than averaging first. Under
pooled aggregation,

\[
p(\theta\mid y) \propto
\sum_i \exp\{-G(\psi_i,\theta)/\tau\}.
\]

Small \(\tau\) concentrates credit on the best matches, and larger \(\tau\)
spreads it across candidates. The low-temperature limit itself depends on the
aggregation convention set out below rather than on temperature alone. As
\(\tau\) approaches zero under pooled aggregation, the sum concentrates on the
globally smallest divergences across all draws, so draws whose best available
match remains poor contribute negligible support. The per-draw conventions
defined below, row-min and expected-posterior, instead resolve each draw
separately, and where a draw has a unique closest candidate they recover hard
best-match assignment within that draw, so their low-temperature limit reflects
the rate at which candidates attain their draw's smallest divergence.
Temperature must therefore be swept and reported together with the convention,
not fixed silently.

Aggregation supplies a third dial. Pooled aggregation preserves the absolute
support contributed by each pattern and normalizes only after summing. The
row-min convention subtracts each pattern's smallest divergence before the
same pooled normalization. Expected-posterior aggregation first normalizes
candidate support within each pattern and then averages, matching Eq. 4 of van
Bork, Romeijn, and Wagenmakers. Per-pattern normalization spends equal total
credit on a pattern even when every candidate fits poorly, whereas pooled
aggregation retains that absolute inadequacy information.

The D60 Resolution adopts aggregation as an explicit evaluation dial.
Canonical reporting uses pooled aggregation to preserve absolute divergence
magnitudes, the M-open signal, and continuity with the validated results.
Expected-posterior aggregation accompanies it wherever external correspondence
with Eq. 4 matters. Canonical pooled reporting carries an explicit price: pooled
aggregation does not reproduce Case A's Target A, which the per-draw routes
recover, and the dial records that failure rather than absorbing it into a
silent default. Neither convention receives a universal-correctness claim;
Case A, section 3, reports the cost of each choice.\footnote{\evidencetier{empirical} \texttt{experiments/vanbork\_external\_validation.py}; \texttt{runs/vanbork\_external\_validation/}; \texttt{experiments/e7\_convention\_sensitivity.py}; \texttt{runs/e7\_convention\_sensitivity/}; Notes/DECISIONS.md D60 Resolution and Precision addenda, and D61.}

\textbf{Remark 1 (one-sidedness under nested candidate regions).} Score a candidate
family \(M\) on draw \(\psi_i\) by its best available match,

\[
G_i(M)=\min_{\theta\in M}G(\psi_i,\theta)
=\min_{q\in\mathcal{P}(M)}G(\psi_i,q),
\]

where \(\mathcal{P}(M)\) collects the predictive distributions the family can
reach as \(\theta\) ranges over its parameters. Stating the score through the
reachable set, rather than through containment of parameter vectors, admits an
embedded restriction that carries fewer parameters than its encompassing
family: nesting requires only \(\mathcal{P}(M_r)\subseteq\mathcal{P}(M_e)\), and
the two parameter spaces may then have unequal dimension. Whenever that
containment holds, minimizing over the larger set cannot return a larger value,
so for every draw

\[
G_i(M_e)\leq G_i(M_r).
\]

The inequality follows from reachable-set containment, not from a sampled
regularity. Under any of the three conventions above, each of which is monotone
in the per-draw scores, table-path aggregation preserves that ordering and can
never favor the restriction at any \(\tau\); only the gap magnitude is
empirical. Consequently, crediting a satisfied restriction belongs to the
\(Z_M\) side, where the volume or reference-measure term controlled by \texttt{occam}
can reward the restricted region, not to the table path. Cases B and C, sections
4 and 5, provide the complementary worked instances.\footnote{\evidencetier{empirical} assembled-manuscript sections 4 and 5 on the Case B and Case C branches; \texttt{runs/occam\_dial/e6\_results.json}; \texttt{runs/haaf\_nested\_constraint/results.json}; Notes/DECISIONS.md D62 and D63.}

\subsection{Metric roles and scale discipline}

Joint divergences compare the full GP predictive covariance with the
candidate's joint predictive covariance. That comparison can make structural
covariance mismatch dominate the mean-pattern question of interest. Pointwise
metrics instead compare marginal predictions at each evaluation location.
Following W1, \texttt{pw\_kl\_vcal} provides the primary metric: variance calibration
reduces it to GP-uncertainty-weighted squared error. The full joint
\texttt{kl\_forward} remains an appendix-only stress metric.\footnote{\evidencetier{peer-reviewed} Gneiting and Raftery (2007), ``Strictly proper scoring rules, prediction, and estimation,'' \emph{JASA}, 102(477), 359--378; Varin, Reid, and Firth (2011), ``An overview of composite likelihood methods,'' \emph{Statistica Sinica}, 21, 5--42. W1 fixes the manuscript roles of \texttt{pw\_kl\_vcal} and \texttt{kl\_forward}.}

D61 sharpens the appendix attribution. The observed \texttt{kl\_forward} fragility
arises largely from pooled aggregation's sensitivity to outlying predictive
draws rather than from the metric alone. Appendix reporting should therefore
pair its pooled soft-transfer result with the aggregation convention and a
draw-level diagnostic, rather than treating a collapsed pooled weight as an
unqualified metric verdict.\footnote{\evidencetier{empirical} \texttt{experiments/e7\_convention\_sensitivity.py}; \texttt{runs/e7\_convention\_sensitivity/results.json} and \texttt{README.md}; Notes/DECISIONS.md D61.}

\textbf{SCALE-INVARIANCE WARNING.} Soft-transfer probability magnitudes cannot be
compared across metrics at a shared numerical \(\tau\). Even under a common
positive affine rescaling of \(G\), the multiplicative scale changes the
effective temperature and can make the normalized probabilities arbitrarily
sharp or diffuse without changing the underlying within-draw ordering. Case D,
section 6, exhibits an exact candidate-specific affine identity between two
stored metrics and shows why a common temperature does not repair their scale
difference.\footnote{\evidencetier{empirical} assembled-manuscript section 6 on \texttt{paper/case-d-mopen}; \texttt{experiments/regret\_curves\_mopen.py}; \texttt{runs/regret\_curves\_mopen/results.json}; Notes/DECISIONS.md D64.}

Reporting must therefore compare probabilities within a metric, over a stated
\(\tau\) sweep. Every soft-transfer table should also report tau-free draw-win
fractions: the fraction of data-pattern draws on which each candidate attains
the smallest \(G\). That statistic remains invariant under a common positive
affine rescaling and separates ordering from temperature-dependent sharpness.
Case D supplies the worked instance.\footnote{\evidencetier{empirical} assembled-manuscript section 6 on \texttt{paper/case-d-mopen}; \texttt{experiments/regret\_curves\_mopen.py}; \texttt{runs/regret\_curves\_mopen/results.json}; Notes/DECISIONS.md D64.}

==================== TEST FILES AT ddf8c9d (names only) ====================
__pycache__
test_bms_aggregation.py
test_bms_star_metrics.py
test_bms_star_universe_firewall.py
test_candidates.py
test_d19_a7_protocol.py
test_d19_bench_firewall.py
test_decompose.py
test_e1_notpsd_policy.py
test_e1_potential.py
test_experiment_hmc_pattern.py
test_fit_gp_options.py
test_fix1_conventions.py
test_fix1_decomposition.py
test_fix1_diagnostics.py
test_fix1_external_targets.py
test_fix1_metrics_firewall.py
test_fix1_review_round.py
test_fix1_roles.py
test_fix1_sentinels.py
test_fix1_sites.py
test_fix1_weighting.py
test_hmc_sample_sites.py
test_impact_compare.py
test_laplace_zmx.py
test_m2br_drivers.py
test_m2br_v116.py
test_m2c_divergence_clustering.py
test_m2c_freeze_constants.py
test_m2c_freeze_dm_constants.py
test_m2c_freeze_m1_constants.py
test_m2c_freeze_s2s3_constants.py
test_m2c_m1_builder.py
test_m2c_m1_nugget_floor.py
test_m2c_m1_overlap.py
test_m2c_manifest.py
test_m2c_mcse_strategy.py
test_m2c_profile_gradient.py
test_m2c_profile_integration.py
test_m2c_s2_fixed_metric.py
test_m2c_s3_reparam.py
test_m2c_umbrella.py
test_m2cr_audit.py
test_m2cr_bootstrap.py
test_m2cr_capture.py
test_m2cr_coordinate_goldens.py
test_m2cr_coordinates.py
test_m2cr_diagnostic_classifier.py
test_m2cr_diagnostic_protocol.py
test_m2cr_diagnostic_schema.py
test_m2cr_environment_freeze.py
test_m2cr_events.py
test_m2cr_evidence_ceilings.py
test_m2cr_gates_v2.py
test_m2cr_gates_v2_equivalence.py
test_m2cr_historical_anchor.py
test_m2cr_infrastructure_manifest.py
test_m2cr_launch_authority.py
test_m2cr_measure.py
test_m2cr_nonfinite_completeness.py
test_m2cr_payload_boundary.py
test_m2cr_protocol_authentication.py
test_m2cr_protocol_manifest.py
test_m2cr_r4_launch.py
test_m2cr_realroot_integration.py
test_m2cr_records.py
test_m2cr_serialization.py
test_m2cr_terminal_records.py
test_mauna_candidate_registry.py
test_mauna_period_freeze.py
test_mauna_provenance.py
test_model_and_fit.py
test_poster_d58_driver.py
test_prior_predictive.py
test_prior_sensitivity_figures.py
test_sampler_diagnostics.py
test_slurm_argparse.py
test_zmx_estimators.py

==================== SOURCE bistar_gp/bms_star.py (line-numbered) ====================
     1	"""
     2	BMS* (Bayesian Model Selection Star) implementation.
     3	
     4	Extends Bayesian induction (Chandramouli & Shiffrin, 2016) by:
     5	1. Using GP hyperpriors to define prior/posterior over data distributions (ψ)
     6	2. Computing divergence G between GP posterior samples and candidate model predictions
     7	3. Soft transfer: transferring GP-derived posteriors onto candidate model instances
     8	
     9	Supports: KL(ψ||θ), KL(θ||ψ), Symmetric KL, Hellinger distance
    10	"""
    11	
    12	import logging
    13	
    14	import numpy as np
    15	import torch
    16	from typing import List, Dict, Tuple, Optional
    17	from dataclasses import dataclass
    18	
    19	torch.set_default_dtype(torch.float64)
    20	logger = logging.getLogger(__name__)
    21	
    22	
    23	# ═══════════════════════════════════════════════════════════════════
    24	# Divergence Metrics for Multivariate Gaussians
    25	# ═══════════════════════════════════════════════════════════════════
    26	
    27	def _safe_logdet(M):
    28	    """Log determinant via Cholesky with jitter fallback."""
    29	    n = M.shape[0]
    30	    for jitter in [0.0, 1e-10, 1e-8, 1e-6, 1e-4]:
    31	        try:
    32	            L = np.linalg.cholesky(M + jitter * np.eye(n))
    33	            return 2.0 * np.sum(np.log(np.diag(L)))
    34	        except np.linalg.LinAlgError:
    35	            continue
    36	    # Fallback: use eigenvalues
    37	    eigs = np.linalg.eigvalsh(M)
    38	    eigs = np.maximum(eigs, 1e-10)
    39	    return np.sum(np.log(eigs))
    40	
    41	
    42	def _safe_solve(A, B):
    43	    """Solve A x = B with regularization fallback."""
    44	    n = A.shape[0]
    45	    for jitter in [0.0, 1e-10, 1e-8, 1e-6, 1e-4]:
    46	        try:
    47	            return np.linalg.solve(A + jitter * np.eye(n), B)
    48	        except np.linalg.LinAlgError:
    49	            continue
    50	    return np.linalg.lstsq(A, B, rcond=None)[0]
    51	
    52	
    53	def kl_divergence(mu_p, cov_p, mu_q, cov_q):
    54	    """
    55	    KL(p || q) for multivariate Gaussians.
    56	    p = N(mu_p, cov_p), q = N(mu_q, cov_q)
    57	
    58	    KL(p||q) = 0.5 * [tr(Σ_q^{-1} Σ_p) + (μ_q - μ_p)^T Σ_q^{-1} (μ_q - μ_p)
    59	                       - k + ln(|Σ_q| / |Σ_p|)]
    60	    """
    61	    k = len(mu_p)
    62	    diff = mu_q - mu_p
    63	
    64	    cov_q_inv_cov_p = _safe_solve(cov_q, cov_p)
    65	    cov_q_inv_diff = _safe_solve(cov_q, diff)
    66	
    67	    trace_term = np.trace(cov_q_inv_cov_p)
    68	    quad_term = diff @ cov_q_inv_diff
    69	    logdet_term = _safe_logdet(cov_q) - _safe_logdet(cov_p)
    70	
    71	    return 0.5 * (trace_term + quad_term - k + logdet_term)
    72	
    73	
    74	def kl_forward(mu_psi, cov_psi, mu_theta, cov_theta):
    75	    """KL(ψ || θ): 'if ψ is true, how much info is lost using θ?'"""
    76	    return kl_divergence(mu_psi, cov_psi, mu_theta, cov_theta)
    77	
    78	
    79	def kl_backward(mu_psi, cov_psi, mu_theta, cov_theta):
    80	    """KL(θ || ψ): 'if θ is true, how surprised would ψ be?'"""
    81	    return kl_divergence(mu_theta, cov_theta, mu_psi, cov_psi)
    82	
    83	
    84	def kl_symmetric(mu_psi, cov_psi, mu_theta, cov_theta):
    85	    """Jeffreys divergence: (KL(ψ||θ) + KL(θ||ψ)) / 2"""
    86	    return 0.5 * (kl_forward(mu_psi, cov_psi, mu_theta, cov_theta) +
    87	                  kl_backward(mu_psi, cov_psi, mu_theta, cov_theta))
    88	
    89	
    90	def bhattacharyya_distance(mu_p, cov_p, mu_q, cov_q):
    91	    """
    92	    Bhattacharyya distance between two Gaussians.
    93	    D_B = (1/8)(μ_p - μ_q)^T Σ^{-1} (μ_p - μ_q) + (1/2) ln(|Σ| / sqrt(|Σ_p||Σ_q|))
    94	    where Σ = (Σ_p + Σ_q) / 2
    95	    """
    96	    cov_avg = 0.5 * (cov_p + cov_q)
    97	    diff = mu_p - mu_q
    98	
    99	    cov_avg_inv_diff = _safe_solve(cov_avg, diff)
   100	    quad_term = 0.125 * diff @ cov_avg_inv_diff
   101	
   102	    logdet_avg = _safe_logdet(cov_avg)
   103	    logdet_p = _safe_logdet(cov_p)
   104	    logdet_q = _safe_logdet(cov_q)
   105	    logdet_term = 0.5 * (logdet_avg - 0.5 * (logdet_p + logdet_q))
   106	
   107	    return quad_term + logdet_term
   108	
   109	
   110	def hellinger_distance(mu_psi, cov_psi, mu_theta, cov_theta):
   111	    """
   112	    Squared Hellinger distance: H^2 = 1 - exp(-D_B)
   113	    Bounded in [0, 1], symmetric, proper metric.
   114	    """
   115	    db = bhattacharyya_distance(mu_psi, cov_psi, mu_theta, cov_theta)
   116	    return 1.0 - np.exp(-db)
   117	
   118	
   119	# ═══════════════════════════════════════════════════════════════════
   120	# Pointwise Divergence Metrics (univariate, averaged over locations)
   121	# ═══════════════════════════════════════════════════════════════════
   122	#
   123	# Joint metrics on n-dimensional Gaussians are dominated by covariance
   124	# structure in high dimensions. Pointwise metrics strip this out:
   125	# compare marginals N(μ_k, σ²_k) at each location k, then average.
   126	# This isolates *mean accuracy* from covariance structure mismatch.
   127	
   128	def _scalar_kl(mu_p, var_p, mu_q, var_q):
   129	    """KL(p || q) for univariate Gaussians."""
   130	    return 0.5 * (np.log(var_q / var_p) + var_p / var_q + (mu_p - mu_q)**2 / var_q - 1.0)
   131	
   132	
   133	def _scalar_hellinger(mu_p, var_p, mu_q, var_q):
   134	    """Squared Hellinger distance for univariate Gaussians."""
   135	    db = 0.25 * np.log(0.25 * (var_p / var_q + var_q / var_p + 2)) + \
   136	         0.25 * (mu_p - mu_q)**2 / (var_p + var_q)
   137	    return 1.0 - np.exp(-db)
   138	
   139	
   140	def _extract_marginals(mu, cov):
   141	    """Extract pointwise means and variances from (mu, cov)."""
   142	    var = np.diag(cov).copy()
   143	    var = np.maximum(var, 1e-10)  # numerical safety
   144	    return mu, var
   145	
   146	
   147	def pw_kl_forward(mu_psi, cov_psi, mu_theta, cov_theta):
   148	    """Pointwise KL(ψ_k || θ_k), averaged over locations."""
   149	    mu_p, var_p = _extract_marginals(mu_psi, cov_psi)
   150	    mu_q, var_q = _extract_marginals(mu_theta, cov_theta)
   151	    return np.mean(_scalar_kl(mu_p, var_p, mu_q, var_q))
   152	
   153	
   154	def pw_kl_backward(mu_psi, cov_psi, mu_theta, cov_theta):
   155	    """Pointwise KL(θ_k || ψ_k), averaged over locations."""
   156	    mu_p, var_p = _extract_marginals(mu_psi, cov_psi)
   157	    mu_q, var_q = _extract_marginals(mu_theta, cov_theta)
   158	    return np.mean(_scalar_kl(mu_q, var_q, mu_p, var_p))
   159	
   160	
   161	def pw_kl_symmetric(mu_psi, cov_psi, mu_theta, cov_theta):
   162	    """Pointwise symmetric KL, averaged over locations."""
   163	    return 0.5 * (pw_kl_forward(mu_psi, cov_psi, mu_theta, cov_theta) +
   164	                  pw_kl_backward(mu_psi, cov_psi, mu_theta, cov_theta))
   165	
   166	
   167	def pw_hellinger(mu_psi, cov_psi, mu_theta, cov_theta):
   168	    """Pointwise squared Hellinger, averaged over locations."""
   169	    mu_p, var_p = _extract_marginals(mu_psi, cov_psi)
   170	    mu_q, var_q = _extract_marginals(mu_theta, cov_theta)
   171	    return np.mean(_scalar_hellinger(mu_p, var_p, mu_q, var_q))
   172	
   173	
   174	def pw_mse(mu_psi, cov_psi, mu_theta, cov_theta):
   175	    """
   176	    Pointwise mean squared error (ignores variance entirely).
   177	    Pure mean-accuracy baseline — no distributional comparison.
   178	    """
   179	    return np.mean((mu_psi - mu_theta)**2)
   180	
   181	
   182	def pw_nll(mu_psi, cov_psi, mu_theta, cov_theta):
   183	    """
   184	    Pointwise negative log-likelihood of ψ means under θ marginals.
   185	    Equivalent to: how well does θ's predictive distribution cover ψ's mean?
   186	    Sensitive to both mean accuracy and calibration.
   187	    """
   188	    mu_p, _ = _extract_marginals(mu_psi, cov_psi)
   189	    mu_q, var_q = _extract_marginals(mu_theta, cov_theta)
   190	    return np.mean(0.5 * np.log(2 * np.pi * var_q) + 0.5 * (mu_p - mu_q)**2 / var_q)
   191	
   192	
   193	# Registry of available metrics
   194	class _MetricRegistry(dict):
   195	    """METRICS[name] imports the v2 metrics on the first miss (FIX-7), so the
   196	    primary metric pw_kl_vcal, defined in metrics_v2, resolves for a caller
   197	    that never imported that module (ExperimentConfig.metrics names it).
   198	    Registered names resolve exactly as in a plain dict; .keys() on the
   199	    implicit run_bms_star path lists v2 names only after their first import,
   200	    as before."""
   201	
   202	    def __missing__(self, name):
   203	        from . import metrics_v2  # noqa: F401  registers into this dict
   204	        if name in self:
   205	            return dict.__getitem__(self, name)
   206	        raise KeyError(f"unknown metric {name!r}; registered: {sorted(self)}")
   207	
   208	
   209	METRICS = _MetricRegistry({
   210	    # Joint (full n-dimensional Gaussian)
   211	    "kl_forward": kl_forward,       # KL(ψ || θ)
   212	    "kl_backward": kl_backward,     # KL(θ || ψ)
   213	    "kl_symmetric": kl_symmetric,   # Jeffreys divergence
   214	    "hellinger": hellinger_distance, # H^2(ψ, θ)
   215	    # Pointwise (univariate marginals, averaged)
   216	    "pw_kl_forward": pw_kl_forward,
   217	    "pw_kl_backward": pw_kl_backward,
   218	    "pw_kl_symmetric": pw_kl_symmetric,
   219	    "pw_hellinger": pw_hellinger,
   220	    "pw_mse": pw_mse,               # mean-only baseline
   221	    "pw_nll": pw_nll,               # mean + variance calibration
   222	})
   223	
   224	
   225	# ═══════════════════════════════════════════════════════════════════
   226	# GP Predictive Extraction from HMC Samples
   227	# ═══════════════════════════════════════════════════════════════════
   228	
   229	@dataclass
   230	class GPPosteriorSample:
   231	    """One draw from the GP posterior over data distributions (one ψ)."""
   232	    mean: np.ndarray       # (n_eval,)
   233	    cov: np.ndarray        # (n_eval, n_eval)
   234	    hyperparameters: Dict[str, float]
   235	
   236	
   237	class PredictiveList(list):
   238	    """List of GPPosteriorSample with draw-integrity bookkeeping (FIX-1).
   239	
   240	    Behaves exactly like the plain list it replaces (len, iteration, indexing,
   241	    truthiness) and additionally records which draw indices were attempted,
   242	    which were retained, and why any were dropped, so a caller can see when
   243	    the returned ensemble is a numerically selected subset of the draws.
   244	    """
   245	
   246	    def __init__(self, items=(), attempted_indices=None, retained_indices=None,
   247	                 dropped=None):
   248	        super().__init__(items)
   249	        self.attempted_indices = list(attempted_indices or [])
   250	        self.retained_indices = list(retained_indices or [])
   251	        self.dropped = list(dropped or [])   # (draw index, reason) pairs
   252	
   253	    @property
   254	    def n_dropped(self):
   255	        return len(self.dropped)
   256	
   257	
   258	def extract_gp_predictives(model, likelihood, x_train, y_train, x_eval,
   259	                           mcmc_samples, kernel_builder,
   260	                           likelihood_builder=None,
   261	                           n_posterior_samples=200, jitter=1e-4,
   262	                           condition_on_data=True, rng=None, strict=True):
   263	    """
   264	    Extract full GP predictive distributions for each hyperparameter sample.
   265	
   266	    Each sample defines a specific GP with specific hyperparameters,
   267	    which implies a specific multivariate Gaussian over y at x_eval.
   268	    These are the ψ's in BMS*.
   269	
   270	    condition_on_data selects which predictive, so the SAME machinery serves both
   271	    Bayesian-workflow checks:
   272	      True  (default): POSTERIOR predictive p(y* | X, y, θ) — condition on the
   273	             training data. Feed fit_hmc posterior draws → posterior predictive check.
   274	      False: PRIOR predictive p(y* | θ) — the GP prior at x_eval (ZeroMean → mean 0,
   275	             cov K_θθ(x_eval) + σ²I), no conditioning on y. Feed sample_prior draws
   276	             → prior predictive check. x_train/y_train are then unused.
   277	
   278	    Args:
   279	        model: fitted AdditiveGPModel (for component_names)
   280	        likelihood: fitted likelihood
   281	        x_train, y_train: training data (used only when condition_on_data=True)
   282	        x_eval: evaluation points
   283	        mcmc_samples: dict from fit_hmc (posterior) or sample_prior (prior)
   284	        kernel_builder: callable returning (kernels, names)
   285	        likelihood_builder: callable returning a likelihood. If None, uses
   286	                           default with Positive() constraint.
   287	        n_posterior_samples: how many samples to use
   288	        jitter: numerical stability
   289	        condition_on_data: posterior (True) vs prior (False) predictive
   290	        rng: optional numpy.random.Generator for the draw subsampling;
   291	             None preserves the legacy global-np.random behavior
   292	        strict: True (default) raises on any silent-wrong-answer path: a
   293	             sample site apply_hp_value does not recognize, an exception
   294	             while applying a site, a sample dict with no recognized kernel
   295	             site, or a draw whose predictive fails numerically. False keeps
   296	             the pre-2026-09 behavior (warn, skip the site or drop the draw)
   297	             for exploratory use; the dropped draws are then recorded on the
   298	             returned PredictiveList.
   299	
   300	    Returns:
   301	        PredictiveList (a list of GPPosteriorSample carrying
   302	        attempted_indices, retained_indices, dropped, n_dropped)
   303	    """
   304	    from .model import build_model, select_hmc_sites, apply_hp_value
   305	    from .decompose import compute_cholesky
   306	    import gpytorch
   307	    from gpytorch.constraints import Positive
   308	    from gpytorch.priors import GammaPrior
   309	
   310	    def _default_likelihood():
   311	        return gpytorch.likelihoods.GaussianLikelihood(
   312	            noise_constraint=Positive(),
   313	            noise_prior=GammaPrior(1.75, 1.0),
   314	        )
   315	
   316	    if likelihood_builder is None:
   317	        likelihood_builder = _default_likelihood
   318	
   319	    x_train = x_train.double() if isinstance(x_train, torch.Tensor) else torch.tensor(x_train).double()
   320	    y_train = y_train.double() if isinstance(y_train, torch.Tensor) else torch.tensor(y_train).double()
   321	    x_eval = x_eval.double() if isinstance(x_eval, torch.Tensor) else torch.tensor(x_eval).double()
   322	
   323	    first_key = list(mcmc_samples.keys())[0]
   324	    total_mcmc = len(mcmc_samples[first_key])
   325	    n_take = min(n_posterior_samples, total_mcmc)
   326	    if rng is not None:
   327	        indices = rng.choice(total_mcmc, n_take, replace=False)
   328	    else:
   329	        # legacy path: global np.random state (callers that need
   330	        # reproducibility without the rng= parameter seed globally)
   331	        indices = np.random.choice(total_mcmc, n_take, replace=False)
   332	
   333	    relevant_keys = select_hmc_sites(mcmc_samples.keys())
   334	    kernel_keys = [k for k in relevant_keys
   335	                   if not k.endswith("noise_covar.noise_prior")]
   336	    if not kernel_keys:
   337	        msg = ("extract_gp_predictives: no kernel hyperparameter site was "
   338	               f"recognized among {sorted(mcmc_samples.keys())}; every "
   339	               "predictive would be built at the fresh model's initialization "
   340	               "kernel values (only the noise would vary)")
   341	        if strict:
   342	            raise ValueError(msg)
   343	        logger.warning(msg)
   344	
   345	    results = []
   346	    retained = []
   347	    dropped = []
   348	
   349	    for idx in indices:
   350	        kernels, names = kernel_builder()
   351	        fresh_likelihood = likelihood_builder()
   352	        fresh_model, fresh_likelihood = build_model(x_train, y_train, kernels, names, fresh_likelihood)
   353	
   354	        # Set parameters from this MCMC sample. Only values that were
   355	        # actually applied are recorded as the draw's hyperparameters.
   356	        hp_dict = {}
   357	        for pyro_name in relevant_keys:
   358	            val = float(mcmc_samples[pyro_name][idx])
   359	            try:
   360	                applied = apply_hp_value(fresh_model, fresh_likelihood, pyro_name, val)
   361	            except (IndexError, AttributeError, RuntimeError) as exc:
   362	                msg = (f"extract_gp_predictives: applying site {pyro_name!r} "
   363	                       f"for draw {int(idx)} raised {type(exc).__name__}: {exc}")
   364	                if strict:
   365	                    raise ValueError(msg) from exc
   366	                logger.warning(msg)
   367	                continue
   368	            if not applied:
   369	                msg = (f"extract_gp_predictives: apply_hp_value did not recognize "
   370	                       f"site {pyro_name!r} (draw {int(idx)}); the fresh model "
   371	                       "keeps its initialization value for that hyperparameter")
   372	                if strict:
   373	                    raise ValueError(msg)
   374	                logger.warning(msg)
   375	                continue
   376	            hp_dict[pyro_name] = val
   377	
   378	        fresh_model.eval()
   379	        fresh_likelihood.eval()
   380	
   381	        with torch.no_grad():
   382	            try:
   383	                noise_var = fresh_likelihood.noise.item()
   384	                K_XstarXstar = fresh_model.covar_module(x_eval, x_eval).evaluate().detach()
   385	
   386	                if condition_on_data:
   387	                    # Posterior predictive p(y* | X, y, θ)
   388	                    K_XX = fresh_model.covar_module(x_train, x_train).evaluate().detach()
   389	                    K_XstarX = fresh_model.covar_module(x_eval, x_train).evaluate().detach()
   390	                    K_XXstar = fresh_model.covar_module(x_train, x_eval).evaluate().detach()
   391	
   392	                    # Cholesky of K_XX + σ²I
   393	                    L = compute_cholesky(K_XX, noise_var, jitter)
   394	                    # Predictive mean: K_*X (K_XX + σ²I)^{-1} y
   395	                    alpha = torch.cholesky_solve(y_train.unsqueeze(-1), L).squeeze(-1)
   396	                    pred_mean = (K_XstarX @ alpha).numpy()
   397	                    # Predictive covariance: K_** - K_*X (K_XX + σ²I)^{-1} K_X*
   398	                    V = torch.linalg.solve_triangular(L, K_XXstar, upper=False)
   399	                    pred_cov = (K_XstarXstar - V.T @ V).numpy()
   400	                else:
   401	                    # Prior predictive p(y* | θ): the GP prior at x_eval, no
   402	                    # conditioning on data. ZeroMean → mean 0; x_train/y_train unused.
   403	                    pred_mean = fresh_model.mean_module(x_eval).detach().numpy()
   404	                    pred_cov = K_XstarXstar.numpy().copy()
   405	
   406	                # Add observation noise to the predictive covariance
   407	                pred_cov = pred_cov + noise_var * np.eye(len(x_eval))
   408	
   409	                results.append(GPPosteriorSample(
   410	                    mean=pred_mean,
   411	                    cov=pred_cov,
   412	                    hyperparameters=hp_dict,
   413	                ))
   414	                retained.append(int(idx))
   415	            except RuntimeError as exc:
   416	                if strict:
   417	                    raise RuntimeError(
   418	                        f"extract_gp_predictives: the predictive for draw "
   419	                        f"{int(idx)} failed ({exc}); pass strict=False to drop "
   420	                        "failing draws and record them instead") from exc
   421	                dropped.append((int(idx), str(exc)))
   422	                continue
   423	
   424	    print(f"  Extracted {len(results)}/{len(indices)} GP predictives")
   425	    if dropped:
   426	        logger.warning("extract_gp_predictives dropped %d of %d draws: %s",
   427	                       len(dropped), len(indices),
   428	                       [d for d, _ in dropped][:10])
   429	    return PredictiveList(results, attempted_indices=[int(i) for i in indices],
   430	                          retained_indices=retained, dropped=dropped)
   431	
   432	
   433	# ═══════════════════════════════════════════════════════════════════
   434	# BMS* Scoring: Soft Transfer
   435	# ═══════════════════════════════════════════════════════════════════
   436	
   437	@dataclass
   438	class BMSStarResult:
   439	    """Results from BMS* analysis."""
   440	    metric_name: str
   441	    tau: float
   442	    # Instance-level
   443	    instance_names: List[str]
   444	    instance_scores: np.ndarray        # (n_instances,) — unnormalized
   445	    instance_posteriors: np.ndarray     # (n_instances,) — normalized, sum to 1
   446	    # Class-level (same as instance for non-nested models)
   447	    class_names: List[str]
   448	    class_posteriors: np.ndarray        # (n_classes,) — normalized
   449	    # Raw G matrix for diagnostics
   450	    G_matrix: np.ndarray               # (n_psi, n_theta)
   451	    # Draw-level diagnostics (2026-09 review FIX-3). weight_ess is the
   452	    # per-candidate effective number of draws behind the pooled score,
   453	    # (sum_i w_ij)^2 / sum_i w_ij^2 with w_ij = exp(-G_ij/tau) on the weights
   454	    # actually aggregated: a concentration summary, not an MCMC ESS and not an
   455	    # error bar. hard_win_credit splits each draw's unit of credit equally
   456	    # among its exact co-minimizers (sums to one across candidates);
   457	    # attainment is the fraction of draws on which a candidate attains the
   458	    # row minimum (ties counted for every co-minimizer); tie_fraction is the
   459	    # fraction of draws whose minimum is tied.
   460	    weight_ess: Optional[np.ndarray] = None
   461	    hard_win_credit: Optional[np.ndarray] = None
   462	    attainment: Optional[np.ndarray] = None
   463	    tie_fraction: Optional[float] = None
   464	
   465	
   466	def log_weight_ess(log_w, axis: int = 0):
   467	    """Effective sample size (sum w)^2 / sum w^2 from LOG weights.
   468	
   469	    The one ESS routine of the package (fix pass 1b): the per-column maximum
   470	    is subtracted before exponentiation, so a large common offset cancels
   471	    exactly instead of surviving as a difference of two large log-sum-exps
   472	    (review R6), and no weight can overflow. Entries of -inf contribute
   473	    nothing. A column whose weights are all -inf has ESS 0 (absent support);
   474	    a column containing NaN has ESS NaN (an invalid evaluation), which is
   475	    deliberately distinct from absent support (review R8). A 1-D input
   476	    returns a float.
   477	    """
   478	    lw = np.asarray(log_w, dtype=float)
   479	    one_d = lw.ndim == 1
   480	    if one_d:
   481	        lw = lw[:, None]
   482	        axis = 0
   483	    nan_col = np.isnan(lw).any(axis=axis)
   484	    m = np.max(np.where(np.isnan(lw), -np.inf, lw), axis=axis, keepdims=True)
   485	    supported = np.isfinite(m)
   486	    w = np.exp(lw - np.where(supported, m, 0.0))
   487	    with np.errstate(invalid="ignore", divide="ignore"):
   488	        ess = w.sum(axis=axis) ** 2 / (w ** 2).sum(axis=axis)
   489	    ess = np.where(np.squeeze(supported, axis=axis), ess, 0.0)
   490	    ess = np.where(nan_col, np.nan, ess)
   491	    return float(ess[0]) if one_d else ess
   492	
   493	
   494	def boltzmann_weight_ess(G_matrix: np.ndarray, tau: float) -> np.ndarray:
   495	    """Per-candidate effective number of draws behind a pooled Boltzmann score.
   496	
   497	    ESS_j = (sum_i w_ij)^2 / sum_i w_ij^2 with w_ij = exp(-G_ij / tau), computed
   498	    from log weights (log_weight_ess) so that a candidate whose raw weights
   499	    underflow still gets a finite value. Invariant under a per-candidate
   500	    column shift of G, which is the multiplicative factor the cross-candidate
   501	    normalization removes.
   502	    """
   503	    lw = -np.asarray(G_matrix, dtype=float) / float(tau)
   504	    if not np.all(np.isfinite(lw)):
   505	        raise ValueError("boltzmann_weight_ess requires finite G values")
   506	    return log_weight_ess(lw, axis=0)
   507	
   508	
   509	def hard_win_statistics(G_matrix: np.ndarray):
   510	    """Tau-free draw-win statistics with an explicit, order-free tie rule.
   511	
   512	    Exact ties on the validated finite scores: for draw i let T_i be the set
   513	    of candidates attaining the row minimum. Returns
   514	      hard_win_credit_j = mean_i [ 1(j in T_i) / |T_i| ]   (sums to one),
   515	      attainment_j      = mean_i [ 1(j in T_i) ],
   516	      tie_fraction      = mean_i [ |T_i| > 1 ].
   517	    A first-argmin rule would silently award every tie to the first candidate.
   518	    """
   519	    G = np.asarray(G_matrix, dtype=float)
   520	    if G.ndim != 2 or not np.all(np.isfinite(G)):
   521	        raise ValueError("hard_win_statistics requires a finite 2-D G matrix")
   522	    row_min = G.min(axis=1, keepdims=True)
   523	    tied = (G == row_min)
   524	    sizes = tied.sum(axis=1, keepdims=True)
   525	    credit = (tied / sizes).mean(axis=0)
   526	    attainment = tied.mean(axis=0)
   527	    tie_fraction = float(np.mean(sizes[:, 0] > 1))
   528	    return credit, attainment, tie_fraction
   529	
   530	
   531	def compute_G_matrix(gp_samples: List[GPPosteriorSample],
   532	                     candidate_results: list,
   533	                     metric_name: str = "kl_forward") -> np.ndarray:
   534	    """
   535	    Compute divergence matrix G[i, j] = G(ψ_i, θ_j).
   536	
   537	    Args:
   538	        gp_samples: list of GPPosteriorSample (the ψ's)
   539	        candidate_results: list of CandidateResult (the θ's)
   540	        metric_name: one of 'kl_forward', 'kl_backward', 'kl_symmetric', 'hellinger'
   541	
   542	    Returns:
   543	        G matrix of shape (n_psi, n_theta)
   544	    """
   545	    # A4 universe firewall at the boundary that still holds candidate
   546	    # metadata (2026-09 review FIX-4): every path that builds a G matrix
   547	    # through the package passes here, including the aggregation_v3 entry
   548	    # points that never call run_bms_star.
   549	    _assert_candidate_universes_consistent(candidate_results)
   550	
   551	    metric_fn = METRICS[metric_name]          # registers metrics_v2 on a miss
   552	    n_psi = len(gp_samples)
   553	    n_theta = len(candidate_results)
   554	    G = np.zeros((n_psi, n_theta))
   555	
   556	    for i, psi in enumerate(gp_samples):
   557	        for j, theta in enumerate(candidate_results):
   558	            try:
   559	                G[i, j] = metric_fn(psi.mean, psi.cov, theta.mean, theta.cov)
   560	            except (np.linalg.LinAlgError, ValueError):
   561	                G[i, j] = np.inf
   562	
   563	    # Replace any inf/nan with a value guaranteed to be WORSE (larger) than any
   564	    # finite divergence. A plain `10 * max_finite` is wrong when the metric can
   565	    # be negative (e.g. pw_nll, whose 0.5*log(2*pi*sigma^2) term goes negative):
   566	    # 10*max_finite would then be the *smallest* G, so a failed computation would
   567	    # win the comparison. This penalty is always strictly greater than max_finite.
   568	    if np.any(np.isfinite(G)):
   569	        max_finite = np.nanmax(G[np.isfinite(G)])
   570	        penalty = max_finite + 10.0 * (abs(max_finite) + 1.0)
   571	    else:
   572	        penalty = 1e6
   573	    G = np.where(np.isfinite(G), G, penalty)
   574	
   575	    return G
   576	
   577	
   578	def soft_transfer(G_matrix: np.ndarray, tau: float,
   579	                  instance_names: List[str],
   580	                  class_names: Optional[List[str]] = None,
   581	                  normalize_per_draw: bool = False,
   582	                  metric_name: Optional[str] = None) -> BMSStarResult:
   583	    """
   584	    Soft BMS* scoring.
   585	
   586	    score(θ_j) = (1/N) Σ_i exp(-G(ψ_i, θ_j) / τ)
   587	
   588	    Class level: only the one-instance-per-class mapping is supported, in
   589	    which class posteriors equal instance posteriors. Any ``class_names``
   590	    that groups instances raises rather than silently returning instance
   591	    posteriors under a class label (2026-09 review FIX-3).
   592	
   593	    Args:
   594	        G_matrix: (n_psi, n_theta) divergence matrix
   595	        tau: temperature parameter
   596	        instance_names: names for each θ
   597	        class_names: None or a 1:1 relabelling of the instances
   598	        normalize_per_draw: if True, subtract per-row minimum before
   599	            Boltzmann weighting. This removes systematic offset so that
   600	            only *relative* divergence within each GP draw matters.
   601	            Prevents microscopic absolute bias from being amplified
   602	            into false certainty across many draws.
   603	        metric_name: the divergence that produced G_matrix. None is recorded
   604	            as "unspecified" rather than an invented identity.
   605	
   606	    Returns:
   607	        BMSStarResult with normalized posteriors and draw-level diagnostics
   608	    """
   609	    n_psi, n_theta = G_matrix.shape
   610	    if not np.all(np.isfinite(G_matrix)):
   611	        # A NaN or infinite divergence is never a score. compute_G_matrix
   612	        # returns finite penalties, so only a hand-built matrix reaches this;
   613	        # the pre-fix code returned a uniform posterior for it (review F4).
   614	        raise ValueError("soft_transfer: G_matrix contains non-finite entries")
   615	
   616	    if len(instance_names) != n_theta:
   617	        raise ValueError(
   618	            f"soft_transfer: {len(instance_names)} instance_names for "
   619	            f"{n_theta} candidate columns")
   620	    if class_names is None:
   621	        class_names = instance_names
   622	    elif len(class_names) != n_theta or len(set(class_names)) != n_theta:
   623	        # one label per column and no repeats (review R5: a length check
   624	        # alone, or a uniqueness check alone, each admits a malformed list)
   625	        raise ValueError(
   626	            "soft_transfer: class-level averaging over grouped instances is "
   627	            "not implemented; pass class_names=None (or a 1:1 relabelling) "
   628	            "and aggregate classes explicitly")
   629	
   630	    # Optionally normalize: subtract best-model score per draw
   631	    G_effective = G_matrix.copy()
   632	    if normalize_per_draw:
   633	        row_mins = G_effective.min(axis=1, keepdims=True)
   634	        G_effective -= row_mins
   635	
   636	    # Instance scores: average Boltzmann weight across GP samples
   637	    # score(θ_j) = (1/N) Σ_i exp(-G_ij / τ)
   638	    log_weights = -G_effective / tau
   639	    # Numerical stability: subtract a single GLOBAL scalar. This cancels exactly
   640	    # in the cross-candidate normalization below, so the posterior is unchanged.
   641	    # A per-row (axis=1) max does NOT cancel — it is a per-draw constant applied
   642	    # before the over-draw mean, so it reweights GP draws and silently behaves
   643	    # like normalize_per_draw even when that flag is False.
   644	    log_weights_shifted = log_weights - log_weights.max()
   645	    weights = np.exp(log_weights_shifted)
   646	    instance_scores = weights.mean(axis=0)
   647	
   648	    # Normalize to get instance posteriors
   649	    total = instance_scores.sum()
   650	    if total > 0:
   651	        instance_posteriors = instance_scores / total
   652	    else:
   653	        instance_posteriors = np.ones(n_theta) / n_theta
   654	
   655	    # Class posteriors = instance posteriors (1:1 mapping, enforced above)
   656	    class_posteriors = instance_posteriors.copy()
   657	
   658	    # Draw-level diagnostics on the weights actually aggregated (G_effective)
   659	    # and the tau-free win statistics on the raw matrix.
   660	    weight_ess = boltzmann_weight_ess(G_effective, tau)
   661	    credit, attainment, tie_fraction = hard_win_statistics(G_matrix)
   662	
   663	    return BMSStarResult(
   664	        metric_name=metric_name if metric_name is not None else "unspecified",
   665	        tau=tau,
   666	        instance_names=list(instance_names),
   667	        instance_scores=instance_scores,
   668	        instance_posteriors=instance_posteriors,
   669	        class_names=list(class_names),
   670	        class_posteriors=class_posteriors,
   671	        G_matrix=G_matrix,
   672	        weight_ess=weight_ess,
   673	        hard_win_credit=credit,
   674	        attainment=attainment,
   675	        tie_fraction=tie_fraction,
   676	    )
   677	
   678	
   679	def aggregate_convention(G_matrix: np.ndarray, tau: float, variant: str) -> np.ndarray:
   680	    """The three aggregation conventions of section 2.3 over one G matrix
   681	    (n_draws, n_candidates) at temperature tau (2026-09 review FIX-9; moved
   682	    into the package from the Case A script so that Cases A and C share one
   683	    implementation instead of a cross-branch import).
   684	
   685	      "pooled": the shipped default; mean over draws of exp(-G/tau) with one
   686	          global stabilizing shift, normalized once (identical arithmetic to
   687	          soft_transfer with normalize_per_draw=False).
   688	      "rowmin": subtract each draw's minimum first, then as "pooled"
   689	          (identical to soft_transfer with normalize_per_draw=True).
   690	      "expected_posterior": normalize each draw into a posterior over
   691	          candidates, then average (van Bork et al. Eq. 4).
   692	    """
   693	    G = np.asarray(G_matrix, dtype=float)
   694	    if not np.all(np.isfinite(G)):
   695	        # the Case A script's `tot > 0 else uniform` tail would otherwise
   696	        # return a uniform posterior for a NaN matrix (GLM F1); on finite
   697	        # input that tail is dead, so the arithmetic below is unchanged
   698	        raise ValueError("aggregate_convention requires a finite G matrix")
   699	    if variant == "pooled":
   700	        G_eff = G
   701	    elif variant == "rowmin":
   702	        G_eff = G - G.min(axis=1, keepdims=True)
   703	    elif variant == "expected_posterior":
   704	        lw = -(G - G.min(axis=1, keepdims=True)) / tau
   705	        w = np.exp(lw)
   706	        w = w / w.sum(axis=1, keepdims=True)
   707	        s = w.mean(axis=0)
   708	        return s / s.sum()
   709	    else:
   710	        raise ValueError(f"unknown aggregation variant {variant!r}")
   711	    lw = -G_eff / tau
   712	    w = np.exp(lw - lw.max())
   713	    s = w.mean(axis=0)
   714	    tot = s.sum()
   715	    return s / tot if tot > 0 else np.ones(G.shape[1]) / G.shape[1]
   716	
   717	
   718	def _assert_candidate_universes_consistent(candidate_results):
   719	    """Firewall the A4 separate-normalization rule at the shared BMS* boundary.
   720	
   721	    run_bms_star normalizes candidate probabilities over ONE universe; the
   722	    D19 pre-registration (decision A4, plan section 3) forbids merging the
   723	    Mauna 4-ladder and harmonized 3-set into one normalization. Enforcing
   724	    that only in the Mauna script is caller-dependent — any other caller
   725	    could pass a mixed set and receive silently normalized cross-universe
   726	    probabilities — so the check runs here, before any G matrix is computed:
   727	
   728	    - every result untagged (universe is None): allowed (legacy/toy callers
   729	      with plain candidates carry no universe and no A4 obligation);
   730	    - any result tagged: EVERY result must be tagged with the SAME universe;
   731	    - mixed tags, or a mix of tagged and untagged: raise before computing G.
   732	    """
   733	    universes = [getattr(cr, "universe", None) for cr in candidate_results]
   734	    tagged = {u for u in universes if u is not None}
   735	    if not tagged:
   736	        return  # all untagged: legacy/toy, no A4 rule applies
   737	    if None in universes or len(tagged) > 1:
   738	        labels = ", ".join(
   739	            f"{getattr(cr, 'name', '?')}[{getattr(cr, 'universe', None)}]"
   740	            for cr in candidate_results)
   741	        raise ValueError(
   742	            "compute_G_matrix/run_bms_star received candidates spanning "
   743	            "multiple universes or a mix of tagged and untagged results "
   744	            f"({labels}); decision A4 forbids merging Mauna candidate "
   745	            "universes into one normalization")
   746	
   747	
   748	def run_bms_star(gp_samples: List[GPPosteriorSample],
   749	                 candidate_results: list,
   750	                 metric_names: List[str] = None,
   751	                 taus: np.ndarray = None,
   752	                 normalize_per_draw: bool = False) -> Dict[str, Dict[float, BMSStarResult]]:
   753	    """
   754	    Run full BMS* analysis across metrics and temperatures.
   755	
   756	    Args:
   757	        normalize_per_draw: if True, subtract per-draw minimum G before
   758	            Boltzmann. Eliminates systematic absolute-score bias.
   759	
   760	    Returns:
   761	        results[metric_name][tau] = BMSStarResult
   762	    """
   763	    implicit_metrics = metric_names is None
   764	    if metric_names is None:
   765	        metric_names = list(METRICS.keys())
   766	    if taus is None:
   767	        taus = np.logspace(-1, 2, 20)
   768	    if implicit_metrics:
   769	        from .config import APPENDIX_METRICS, PRIMARY_METRIC
   770	        appendix = [m for m in metric_names if m in APPENDIX_METRICS]
   771	        if appendix:
   772	            logger.warning(
   773	                "run_bms_star: scoring appendix-only metric(s) %s because "
   774	                "metric_names was not given; W1 makes %s the primary metric",
   775	                appendix, PRIMARY_METRIC)
   776	        if PRIMARY_METRIC not in metric_names:
   777	            # The implicit roster is whatever is registered at call time; the
   778	            # primary metric registers on first use of metrics_v2 (Kimi K3-1).
   779	            # The roster is left as it is so existing implicit calls keep
   780	            # their outputs; the omission is announced instead.
   781	            logger.warning(
   782	                "run_bms_star: the primary metric %s is not in the implicit "
   783	                "roster (metrics_v2 not imported yet); pass metric_names "
   784	                "explicitly to score it", PRIMARY_METRIC)
   785	
   786	    _assert_candidate_universes_consistent(candidate_results)
   787	
   788	    instance_names = [cr.name for cr in candidate_results]
   789	    results = {}
   790	
   791	    for metric_name in metric_names:
   792	        print(f"\n  Computing G matrix: {metric_name}...")
   793	        G = compute_G_matrix(gp_samples, candidate_results, metric_name)
   794	
   795	        print(f"    G stats — min: {G.min():.2f}, median: {np.median(G):.2f}, max: {G.max():.2f}")
   796	
   797	        # Per-draw diagnostic: how often does each model win raw?
   798	        raw_winners = np.argmin(G, axis=1)
   799	        for m_idx, name in enumerate(instance_names):
   800	            n_wins = np.sum(raw_winners == m_idx)
   801	            print(f"    {name} wins {n_wins}/{len(raw_winners)} draws (raw G)")
   802	
   803	        if normalize_per_draw:
   804	            row_deltas = G - G.min(axis=1, keepdims=True)
   805	            for m_idx, name in enumerate(instance_names):
   806	                mean_delta = row_deltas[:, m_idx].mean()
   807	                print(f"    {name} mean Δ from best: {mean_delta:.4f}")
   808	
   809	        results[metric_name] = {}
   810	        for tau in taus:
   811	            bms_result = soft_transfer(G, tau, instance_names,
   812	                                       normalize_per_draw=normalize_per_draw,
   813	                                       metric_name=metric_name)
   814	            results[metric_name][tau] = bms_result
   815	
   816	    return results
   817	
   818	
   819	# ═══════════════════════════════════════════════════════════════════
   820	# Visualization
   821	# ═══════════════════════════════════════════════════════════════════
   822	
   823	def plot_bms_star_results(results: Dict[str, Dict[float, BMSStarResult]],
   824	                         figsize=None):
   825	    """
   826	    Plot BMS* results: τ sensitivity curves, one panel per metric.
   827	    Automatically sizes grid to fit all metrics.
   828	    """
   829	    import matplotlib.pyplot as plt
   830	
   831	    metric_names = list(results.keys())
   832	    n_metrics = len(metric_names)
   833	    ncols = min(4, n_metrics)
   834	    nrows = (n_metrics + ncols - 1) // ncols
   835	    if figsize is None:
   836	        figsize = (4 * ncols, 3.5 * nrows)
   837	
   838	    fig, axes = plt.subplots(nrows, ncols, figsize=figsize)
   839	    if n_metrics == 1:
   840	        axes = np.array([axes])
   841	    axes = np.atleast_2d(axes).flatten()
   842	
   843	    colors = ['#e74c3c', '#3498db', '#2ecc71', '#9b59b6', '#f39c12']
   844	
   845	    for ax_idx, metric_name in enumerate(metric_names):
   846	        ax = axes[ax_idx]
   847	        taus = sorted(results[metric_name].keys())
   848	        instance_names = results[metric_name][taus[0]].instance_names
   849	        n_models = len(instance_names)
   850	
   851	        posteriors = np.zeros((len(taus), n_models))
   852	        for t_idx, tau in enumerate(taus):
   853	            posteriors[t_idx] = results[metric_name][tau].instance_posteriors
   854	
   855	        for m_idx, name in enumerate(instance_names):
   856	            ax.semilogx(taus, posteriors[:, m_idx],
   857	                       label=name, color=colors[m_idx % len(colors)],
   858	                       linewidth=2)
   859	
   860	        ax.set_xlabel("τ")
   861	        ax.set_ylabel("Posterior")
   862	        ax.set_title(metric_name, fontsize=9)
   863	        ax.set_ylim(-0.05, 1.05)
   864	        ax.legend(fontsize=6)
   865	        ax.grid(True, alpha=0.3)
   866	
   867	    # Hide unused axes
   868	    for ax_idx in range(n_metrics, len(axes)):
   869	        axes[ax_idx].set_visible(False)
   870	
   871	    fig.suptitle("BMS*: Model Posteriors vs Temperature", fontsize=14)
   872	    fig.tight_layout()
   873	    return fig
   874	
   875	
   876	def plot_G_heatmaps(results: Dict[str, Dict[float, BMSStarResult]],
   877	                    figsize=None):
   878	    """Plot G matrix heatmaps for each metric."""
   879	    import matplotlib.pyplot as plt
   880	
   881	    metric_names = list(results.keys())
   882	    n_metrics = len(metric_names)
   883	    ncols = min(5, n_metrics)
   884	    nrows = (n_metrics + ncols - 1) // ncols
   885	    if figsize is None:
   886	        figsize = (3.5 * ncols, 3 * nrows)
   887	
   888	    fig, axes = plt.subplots(nrows, ncols, figsize=figsize)
   889	    if n_metrics == 1:
   890	        axes = np.array([axes])
   891	    axes = np.atleast_2d(axes).flatten()
   892	
   893	    first_tau = sorted(results[metric_names[0]].keys())[0]
   894	
   895	    for ax, metric_name in zip(axes, metric_names):
   896	        bms = results[metric_name][first_tau]
   897	        G = bms.G_matrix
   898	
   899	        im = ax.imshow(G, aspect='auto', cmap='viridis')
   900	        ax.set_xlabel("Candidate (θ)", fontsize=7)
   901	        ax.set_ylabel("GP sample (ψ)", fontsize=7)
   902	        ax.set_title(metric_name, fontsize=8)
   903	        ax.set_xticks(range(len(bms.instance_names)))
   904	        ax.set_xticklabels(bms.instance_names, rotation=45, ha='right', fontsize=6)
   905	        plt.colorbar(im, ax=ax, fraction=0.046)
   906	
   907	    for ax_idx in range(n_metrics, len(axes)):
   908	        axes[ax_idx].set_visible(False)
   909	
   910	    fig.suptitle("Divergence G(ψ, θ) matrices", fontsize=14)
   911	    fig.tight_layout()
   912	    return fig
   913	
   914	
   915	def plot_candidate_predictions(x_eval, gp_samples, candidate_results,
   916	                               x_train=None, y_train=None, figsize=(14, 8)):
   917	    """Overlay candidate model predictions on GP posterior."""
   918	    import matplotlib.pyplot as plt
   919	
   920	    fig, axes = plt.subplots(2, 2, figsize=figsize)
   921	    axes = axes.flatten()
   922	    colors = ['#e74c3c', '#3498db', '#2ecc71', '#9b59b6']
   923	
   924	    # Compute GP posterior mean and std across samples
   925	    gp_means = np.array([s.mean for s in gp_samples])
   926	    gp_mean = gp_means.mean(axis=0)
   927	    gp_std = gp_means.std(axis=0)
   928	
   929	    for ax_idx, (cr, color) in enumerate(zip(candidate_results, colors)):
   930	        ax = axes[ax_idx]
   931	
   932	        # GP posterior
   933	        ax.fill_between(x_eval, gp_mean - 2*gp_std, gp_mean + 2*gp_std,
   934	                        alpha=0.2, color='gray', label='GP ±2σ')
   935	        # Individual GP samples (thin lines)
   936	        for s in gp_samples[::max(1, len(gp_samples)//15)]:
   937	            ax.plot(x_eval, s.mean, color='gray', alpha=0.1, linewidth=0.5)
   938	        ax.plot(x_eval, gp_mean, color='gray', linewidth=1.5, label='GP mean')
   939	
   940	        # Candidate model
   941	        ax.plot(x_eval, cr.mean, color=color, linewidth=2.5, label=cr.name)
   942	        cr_std = np.sqrt(np.diag(cr.cov))
   943	        ax.fill_between(x_eval, cr.mean - 2*cr_std, cr.mean + 2*cr_std,
   944	                        alpha=0.15, color=color)
   945	
   946	        # Data
   947	        if x_train is not None and y_train is not None:
   948	            ax.scatter(x_train, y_train, color='black', marker='x', s=20, zorder=5)
   949	
   950	        ax.set_title(cr.name, fontsize=12, fontweight='bold')
   951	        ax.legend(fontsize=7, loc='upper left')
   952	        ax.grid(True, alpha=0.3)
   953	
   954	    fig.suptitle("Candidate Models vs GP Posterior", fontsize=14)
   955	    fig.tight_layout()
   956	    return fig
   957	
   958	
   959	def print_bms_star_table(results: Dict[str, Dict[float, BMSStarResult]],
   960	                         tau: float):
   961	    """Print a clean table of BMS* posteriors at a given τ."""
   962	    metric_names = list(results.keys())
   963	    first = results[metric_names[0]]
   964	    closest_tau = min(first.keys(), key=lambda t: abs(t - tau))
   965	    instance_names = first[closest_tau].instance_names
   966	
   967	    # Header
   968	    header = f"{'Model':<15}"
   969	    for m in metric_names:
   970	        header += f"  {m:<15}"
   971	    print(f"\n  BMS* Posteriors at τ = {closest_tau:.2f}")
   972	    print(f"  {'─' * len(header)}")
   973	    print(f"  {header}")
   974	    print(f"  {'─' * len(header)}")
   975	
   976	    for i, name in enumerate(instance_names):
   977	        row = f"{name:<15}"
   978	        for m in metric_names:
   979	            p = results[m][closest_tau].instance_posteriors[i]
   980	            row += f"  {p:<15.4f}"
   981	        print(f"  {row}")
   982	    print()

==================== SOURCE bistar_gp/aggregation_v3.py (line-numbered) ====================
     1	"""
     2	aggregation_v3.py — Alternative BMS* aggregation strategies
     3	
     4	The v2 metrics showed that the variance-ratio trap was masking a deeper issue:
     5	GP posterior mean variability across HMC samples. The correct model (Sin+Linear)
     6	matches the *averaged* GP well but has high-variance G across individual samples.
     7	The Boltzmann average rewards consistency over occasional excellence.
     8	
     9	Three fixes, each attacking a different part of the problem:
    10	
    11	  Strategy 1: AVERAGED GP POSTERIOR
    12	    Collapse all GP samples into one averaged ψ̄, then compute G(ψ̄, θ) once.
    13	    Bypasses sample-level averaging entirely.
    14	
    15	  Strategy 2: ROBUST AGGREGATION
    16	    Keep individual G values but replace Boltzmann with robust summaries:
    17	    (a) Median G per candidate (robust to outlier samples)
    18	    (b) Trimmed mean (drop worst 20% of GP samples per candidate)
    19	    (c) Rank-based: for each ψ, rank candidates, then average ranks
    20	
    21	  Strategy 3: MARGINAL LIKELIHOOD WEIGHTING
    22	    Weight each HMC sample by p(y|X,θ_i) before averaging.
    23	    High-likelihood samples (well-fitting hyperparameters) count more;
    24	    outlier samples (very long/short lengthscales) get downweighted.
    25	"""
    26	
    27	import logging
    28	
    29	import numpy as np
    30	import torch
    31	from scipy.special import logsumexp
    32	from typing import List, Dict, Optional, Tuple
    33	from dataclasses import dataclass
    34	
    35	from bistar_gp.bms_star import (
    36	    GPPosteriorSample, METRICS, compute_G_matrix, BMSStarResult,
    37	    _extract_marginals, _assert_candidate_universes_consistent,
    38	    aggregate_convention, hard_win_statistics, log_weight_ess,
    39	)
    40	
    41	logger = logging.getLogger(__name__)
    42	
    43	torch.set_default_dtype(torch.float64)
    44	
    45	
    46	# ═══════════════════════════════════════════════════════════════════
    47	# Strategy 1: Averaged GP Posterior
    48	# ═══════════════════════════════════════════════════════════════════
    49	
    50	def average_gp_posterior(gp_samples: List[GPPosteriorSample],
    51	                         weights=None) -> GPPosteriorSample:
    52	    """
    53	    Collapse GP samples into one averaged predictive distribution.
    54	
    55	    The marginal predictive p(y*|X,y) = ∫ p(y*|X,y,θ) p(θ|X,y) dθ
    56	    is approximated by the mixture of Gaussians from HMC samples.
    57	    For a Gaussian mixture with weights w_i (uniform 1/N by default), the
    58	    mean and covariance of the mixture are:
    59	
    60	      μ̄ = Σ w_i μ_i
    61	      Σ̄ = Σ w_i [Σ_i + (μ_i - μ̄)(μ_i - μ̄)^T]
    62	
    63	    The second term captures the inter-sample mean spread — this is
    64	    the "hyperparameter uncertainty" that inflates the marginal variance.
    65	
    66	    weights: optional per-sample mixture weights (normalized internally).
    67	    Uniform is correct for genuine posterior draws; the weighted form exists
    68	    to reproduce legacy importance-weighted prior-draw figures in the viz
    69	    unification comparison harness (docs/plan-viz-unification.md §1.4).
    70	    """
    71	    N = len(gp_samples)
    72	    if weights is None:
    73	        w = np.full(N, 1.0 / N)
    74	    else:
    75	        w = np.asarray(weights, dtype=float)
    76	        if (w.shape != (N,) or not np.all(np.isfinite(w)) or np.any(w < 0)
    77	                or w.sum() <= 0):
    78	            raise ValueError(
    79	                f"weights must be {N} finite non-negative values with positive sum")
    80	        w = w / w.sum()
    81	
    82	    means = np.array([s.mean for s in gp_samples])   # (N, n_eval)
    83	    if not np.all(np.isfinite(means)):
    84	        bad = [i for i, m in enumerate(means) if not np.all(np.isfinite(m))]
    85	        raise ValueError(
    86	            f"average_gp_posterior: non-finite mean in draw(s) {bad[:10]}")
    87	    for i, s in enumerate(gp_samples):
    88	        if not np.all(np.isfinite(np.diag(s.cov))):
    89	            raise ValueError(
    90	                f"average_gp_posterior: non-finite covariance diagonal in draw {i}")
    91	    mu_bar = w @ means                                 # (n_eval,)
    92	
    93	    # Weighted average covariance + inter-sample mean spread
    94	    n_eval = len(mu_bar)
    95	    cov_bar = np.zeros((n_eval, n_eval))
    96	    for w_i, s in zip(w, gp_samples):
    97	        diff = s.mean - mu_bar
    98	        cov_bar += w_i * (s.cov + np.outer(diff, diff))
    99	
   100	    return GPPosteriorSample(
   101	        mean=mu_bar,
   102	        cov=cov_bar,
   103	        hyperparameters={"averaged": True, "n_samples": N},
   104	    )
   105	
   106	
   107	def score_averaged_gp(gp_samples: List[GPPosteriorSample],
   108	                      candidate_results: list,
   109	                      metric_names: Optional[List[str]] = None,
   110	                      ) -> Dict[str, np.ndarray]:
   111	    """
   112	    Strategy 1: Score candidates against the averaged GP posterior.
   113	
   114	    No τ parameter needed — just one G value per candidate per metric.
   115	    Returns normalized posteriors (lower G → higher posterior).
   116	
   117	    Returns:
   118	        results[metric_name] = {
   119	            "G_values": np.ndarray (n_theta,),
   120	            "posteriors": np.ndarray (n_theta,),  # softmax of -G
   121	            "names": List[str],
   122	        }
   123	    """
   124	    if metric_names is None:
   125	        metric_names = ["pw_kl_vcal", "pw_hellinger_vcal", "pw_nll_gp",
   126	                        "pw_mse", "pw_hellinger_mean"]
   127	
   128	    # This strategy scores the averaged pattern directly and never builds a
   129	    # G matrix, so the A4 firewall must run here explicitly (FIX-4).
   130	    _assert_candidate_universes_consistent(candidate_results)
   131	
   132	    psi_bar = average_gp_posterior(gp_samples)
   133	    instance_names = [cr.name for cr in candidate_results]
   134	    results = {}
   135	
   136	    for metric_name in metric_names:
   137	        metric_fn = METRICS[metric_name]
   138	        G_values = np.array([
   139	            metric_fn(psi_bar.mean, psi_bar.cov, cr.mean, cr.cov)
   140	            for cr in candidate_results
   141	        ])
   142	
   143	        # Convert to posteriors: exp(-G) / Σ exp(-G)
   144	        # Use log-space for stability
   145	        log_scores = -G_values
   146	        log_scores -= log_scores.max()
   147	        scores = np.exp(log_scores)
   148	        posteriors = scores / scores.sum()
   149	
   150	        results[metric_name] = {
   151	            "G_values": G_values,
   152	            "posteriors": posteriors,
   153	            "names": instance_names,
   154	        }
   155	
   156	        print(f"  [Averaged GP] {metric_name}:")
   157	        for name, g, p in zip(instance_names, G_values, posteriors):
   158	            print(f"    {name:<15} G={g:.4f}  posterior={p:.4f}")
   159	
   160	    return results
   161	
   162	
   163	# ═══════════════════════════════════════════════════════════════════
   164	# Strategy 2: Robust Aggregation
   165	# ═══════════════════════════════════════════════════════════════════
   166	
   167	@dataclass
   168	class RobustResult:
   169	    """Results from robust aggregation."""
   170	    metric_name: str
   171	    method: str               # "median", "trimmed_mean", "rank"
   172	    instance_names: List[str]
   173	    summary_values: np.ndarray  # (n_theta,) — the summary statistic per candidate
   174	    posteriors: np.ndarray      # (n_theta,) — normalized
   175	
   176	
   177	def robust_median(G_matrix: np.ndarray,
   178	                  instance_names: List[str],
   179	                  metric_name: str = "") -> RobustResult:
   180	    """
   181	    Median G across GP samples per candidate.
   182	
   183	    Robust to outlier GP samples (very short or very long lengthscale).
   184	    Median minimizes absolute deviation — a single bad GP sample
   185	    can't dominate the score.
   186	    """
   187	    medians = np.median(G_matrix, axis=0)
   188	
   189	    # Lower G → better → higher posterior
   190	    log_scores = -medians
   191	    log_scores -= log_scores.max()
   192	    scores = np.exp(log_scores)
   193	    posteriors = scores / scores.sum()
   194	
   195	    return RobustResult(
   196	        metric_name=metric_name,
   197	        method="median",
   198	        instance_names=list(instance_names),
   199	        summary_values=medians,
   200	        posteriors=posteriors,
   201	    )
   202	
   203	
   204	def robust_trimmed_mean(G_matrix: np.ndarray,
   205	                        instance_names: List[str],
   206	                        trim_fraction: float = 0.2,
   207	                        metric_name: str = "") -> RobustResult:
   208	    """
   209	    Trimmed mean: drop the top and bottom trim_fraction of G values
   210	    per candidate before averaging.
   211	
   212	    With trim_fraction=0.2 and 200 samples, drops the 40 highest and
   213	    40 lowest G values per candidate. Removes both "too easy" and
   214	    "too hard" GP samples.
   215	    """
   216	    n_psi = G_matrix.shape[0]
   217	    n_trim = int(n_psi * trim_fraction)
   218	
   219	    trimmed_means = np.zeros(G_matrix.shape[1])
   220	    for j in range(G_matrix.shape[1]):
   221	        col = np.sort(G_matrix[:, j])
   222	        trimmed = col[n_trim:n_psi - n_trim] if n_trim > 0 else col
   223	        trimmed_means[j] = trimmed.mean()
   224	
   225	    log_scores = -trimmed_means
   226	    log_scores -= log_scores.max()
   227	    scores = np.exp(log_scores)
   228	    posteriors = scores / scores.sum()
   229	
   230	    return RobustResult(
   231	        metric_name=metric_name,
   232	        method=f"trimmed_mean_{trim_fraction:.0%}",
   233	        instance_names=list(instance_names),
   234	        summary_values=trimmed_means,
   235	        posteriors=posteriors,
   236	    )
   237	
   238	
   239	def robust_rank(G_matrix: np.ndarray,
   240	                instance_names: List[str],
   241	                metric_name: str = "") -> RobustResult:
   242	    """
   243	    Rank-based aggregation: for each GP sample, rank candidates 1-K
   244	    (1 = lowest G = best). Then average ranks across samples.
   245	
   246	    Completely nonparametric — immune to scale differences between
   247	    GP samples. A model that consistently ranks #1 or #2 wins,
   248	    regardless of the absolute G values.
   249	    """
   250	    n_psi, n_theta = G_matrix.shape
   251	
   252	    # For each row (GP sample), compute ranks
   253	    ranks = np.zeros_like(G_matrix)
   254	    for i in range(n_psi):
   255	        ranks[i] = np.argsort(np.argsort(G_matrix[i])) + 1  # 1-indexed
   256	
   257	    avg_ranks = ranks.mean(axis=0)
   258	
   259	    # Lower rank → better → higher posterior
   260	    # Convert: use exp(-rank) and normalize
   261	    log_scores = -avg_ranks
   262	    log_scores -= log_scores.max()
   263	    scores = np.exp(log_scores)
   264	    posteriors = scores / scores.sum()
   265	
   266	    return RobustResult(
   267	        metric_name=metric_name,
   268	        method="rank",
   269	        instance_names=list(instance_names),
   270	        summary_values=avg_ranks,
   271	        posteriors=posteriors,
   272	    )
   273	
   274	
   275	def run_robust_aggregation(gp_samples: List[GPPosteriorSample],
   276	                           candidate_results: list,
   277	                           metric_names: Optional[List[str]] = None,
   278	                           ) -> Dict[str, Dict[str, RobustResult]]:
   279	    """
   280	    Run all three robust aggregation methods across metrics.
   281	
   282	    Returns:
   283	        results[metric_name][method] = RobustResult
   284	    """
   285	    if metric_names is None:
   286	        metric_names = ["pw_kl_vcal", "pw_hellinger_vcal", "pw_nll_gp",
   287	                        "pw_mse", "pw_hellinger_mean"]
   288	
   289	    instance_names = [cr.name for cr in candidate_results]
   290	    results = {}
   291	
   292	    for metric_name in metric_names:
   293	        print(f"\n  Computing G matrix: {metric_name}...")
   294	        G = compute_G_matrix(gp_samples, candidate_results, metric_name)
   295	
   296	        results[metric_name] = {
   297	            "median": robust_median(G, instance_names, metric_name),
   298	            "trimmed_mean": robust_trimmed_mean(G, instance_names, 0.2, metric_name),
   299	            "rank": robust_rank(G, instance_names, metric_name),
   300	        }
   301	
   302	        for method_name, rr in results[metric_name].items():
   303	            print(f"  [{method_name}] {metric_name}:")
   304	            for name, sv, p in zip(rr.instance_names, rr.summary_values, rr.posteriors):
   305	                print(f"    {name:<15} summary={sv:.4f}  posterior={p:.4f}")
   306	
   307	    return results
   308	
   309	
   310	# ═══════════════════════════════════════════════════════════════════
   311	# Strategy 3: Marginal Likelihood Weighting
   312	# ═══════════════════════════════════════════════════════════════════
   313	
   314	def compute_log_marginal_likelihoods(
   315	    gp_samples: List[GPPosteriorSample],
   316	    x_train, y_train,
   317	    kernel_builder, likelihood_builder=None,
   318	    jitter: float = 1e-4,
   319	) -> np.ndarray:
   320	    """
   321	    Compute log p(y | X, θ_i) for each HMC sample.
   322	
   323	    log p(y|X,θ) = -0.5 * y^T (K+σ²I)^{-1} y
   324	                   -0.5 * log|K+σ²I|
   325	                   -n/2 * log(2π)
   326	
   327	    Uses the same fresh-model rebuild approach as extract_gp_predictives.
   328	    """
   329	    from bistar_gp.model import build_model, apply_hp_value
   330	    from bistar_gp.decompose import compute_cholesky
   331	
   332	    x_t = x_train.double() if isinstance(x_train, torch.Tensor) else torch.tensor(x_train).double()
   333	    y_t = y_train.double() if isinstance(y_train, torch.Tensor) else torch.tensor(y_train).double()
   334	    n = len(x_t)
   335	
   336	    import gpytorch
   337	    from gpytorch.constraints import Positive
   338	    from gpytorch.priors import GammaPrior
   339	
   340	    if likelihood_builder is None:
   341	        def likelihood_builder():
   342	            return gpytorch.likelihoods.GaussianLikelihood(
   343	                noise_constraint=Positive(),
   344	                noise_prior=GammaPrior(1.75, 1.0),
   345	            )
   346	
   347	    log_mlls = np.zeros(len(gp_samples))
   348	
   349	    for idx, sample in enumerate(gp_samples):
   350	        kernels, names = kernel_builder()
   351	        fresh_lik = likelihood_builder()
   352	        fresh_model, fresh_lik = build_model(x_t, y_t, kernels, names, fresh_lik)
   353	
   354	        # Set hyperparameters OUTSIDE the numerical handler below. A site the
   355	        # model does not recognize is a silent-wrong-answer path (the
   356	        # likelihood would be scored at the fresh model's initialization
   357	        # value), so it raises and the error must escape (FIX-1; review R1
   358	        # found the pass-1 raise sitting inside the handler that converts
   359	        # numerical failures into -inf).
   360	        for pyro_name, val in sample.hyperparameters.items():
   361	            if not apply_hp_value(fresh_model, fresh_lik, pyro_name, val):
   362	                raise ValueError(
   363	                    f"compute_log_marginal_likelihoods: apply_hp_value did "
   364	                    f"not recognize site {pyro_name!r} for draw {idx}")
   365	
   366	        fresh_model.eval()
   367	        fresh_lik.eval()
   368	
   369	        try:
   370	            with torch.no_grad():
   371	                noise_var = fresh_lik.noise.item()
   372	                K_XX = fresh_model.covar_module(x_t, x_t).evaluate().detach()
   373	                L = compute_cholesky(K_XX, noise_var, jitter)
   374	
   375	                # α = (K + σ²I)^{-1} y
   376	                alpha = torch.cholesky_solve(y_t.unsqueeze(-1), L).squeeze(-1)
   377	
   378	                # log|K + σ²I| = 2 * sum(log(diag(L)))
   379	                log_det = 2.0 * torch.sum(torch.log(torch.diag(L)))
   380	
   381	                # log p(y|X,θ)
   382	                data_fit = -0.5 * y_t.dot(alpha)
   383	                complexity = -0.5 * log_det
   384	                constant = -0.5 * n * np.log(2 * np.pi)
   385	
   386	                log_mlls[idx] = (data_fit + complexity + constant).item()
   387	
   388	        except (RuntimeError, ValueError):
   389	            log_mlls[idx] = -np.inf
   390	
   391	    # Report
   392	    valid = np.isfinite(log_mlls)
   393	    print(f"  Computed {valid.sum()}/{len(log_mlls)} valid log marginal likelihoods")
   394	    if valid.any():
   395	        print(f"    Range: [{log_mlls[valid].min():.2f}, {log_mlls[valid].max():.2f}]")
   396	        print(f"    Mean:  {log_mlls[valid].mean():.2f}")
   397	
   398	    return log_mlls
   399	
   400	
   401	def soft_transfer_weighted(G_matrix: np.ndarray, tau: float,
   402	                           instance_names: List[str],
   403	                           log_weights: np.ndarray) -> BMSStarResult:
   404	    """
   405	    Weighted Boltzmann soft transfer.
   406	
   407	    score(θ_j) = Σ_i w_i exp(-G_ij / τ)  /  Σ_i w_i
   408	
   409	    where w_i = exp(log_weight_i - max(log_weight)).
   410	
   411	    High marginal-likelihood samples contribute more.
   412	    """
   413	    G = np.asarray(G_matrix, dtype=float)
   414	    if not np.all(np.isfinite(G)):
   415	        # same rule as soft_transfer (review K3-3 / GLM F4): a non-finite
   416	        # divergence is never a score; NaN used to propagate silently here
   417	        raise ValueError("soft_transfer_weighted: G_matrix contains non-finite entries")
   418	    n_psi, n_theta = G.shape
   419	    lw = np.asarray(log_weights, dtype=float).copy()
   420	    lw[~np.isfinite(lw)] = -np.inf          # a non-finite draw weight is absent support
   421	    if not np.any(np.isfinite(lw)):
   422	        raise ValueError(
   423	            "soft_transfer_weighted: no draw carries a finite log weight; "
   424	            "refusing to substitute a uniform posterior")
   425	
   426	    # Joint log-space aggregation (2026-09 review FIX-6). The previous code
   427	    # stabilized the draw weights and the Boltzmann factors SEPARATELY and
   428	    # multiplied them, so when their maxima fell on different rows every
   429	    # product could underflow and the function silently returned a uniform
   430	    # posterior. Forming log w_i - G_ij/tau first and summing with
   431	    # log-sum-exp makes the result exact up to floating point.
   432	    log_terms = lw[:, None] - G / tau                            # (n_psi, n_theta)
   433	    # One GLOBAL shift before the two log-sum-exps (pass 1b, review R6): the
   434	    # cross-candidate normalization is then a difference of moderate numbers
   435	    # instead of two large nearly equal ones. The shift cancels exactly.
   436	    shift = np.max(log_terms)
   437	    ls = logsumexp(log_terms - shift, axis=0)                    # log-scores up to the shift
   438	    log_post = ls - logsumexp(ls)
   439	    instance_posteriors = np.exp(log_post)
   440	    log_scores = ls + shift - logsumexp(lw)                      # log[ sum_i w_i e^{-G_ij/tau} / sum_i w_i ]
   441	    # Scores on the pre-fix scale: sum_i w_i exp(-(G_ij - G_min)/tau) / sum_i w_i
   442	    instance_scores = np.exp(log_scores + G.min() / tau)
   443	    weight_ess = log_weight_ess(log_terms, axis=0)
   444	    credit, attainment, tie_fraction = hard_win_statistics(G)
   445	
   446	    return BMSStarResult(
   447	        metric_name="weighted",
   448	        tau=tau,
   449	        instance_names=list(instance_names),
   450	        instance_scores=instance_scores,
   451	        instance_posteriors=instance_posteriors,
   452	        class_names=list(instance_names),
   453	        class_posteriors=instance_posteriors.copy(),
   454	        G_matrix=G,
   455	        weight_ess=weight_ess,
   456	        hard_win_credit=credit,
   457	        attainment=attainment,
   458	        tie_fraction=tie_fraction,
   459	    )
   460	
   461	
   462	def run_weighted_bms_star(gp_samples: List[GPPosteriorSample],
   463	                          candidate_results: list,
   464	                          log_mlls: np.ndarray,
   465	                          metric_names: Optional[List[str]] = None,
   466	                          taus: np.ndarray = None,
   467	                          ) -> Dict[str, Dict[float, BMSStarResult]]:
   468	    """
   469	    Run BMS* with marginal likelihood weighting across metrics × τ.
   470	
   471	    Same structure as run_bms_star but with weighted aggregation.
   472	    """
   473	    if metric_names is None:
   474	        metric_names = ["pw_kl_vcal", "pw_hellinger_vcal", "pw_nll_gp",
   475	                        "pw_mse", "pw_hellinger_mean"]
   476	    if taus is None:
   477	        taus = np.logspace(-1, 2, 30)
   478	
   479	    instance_names = [cr.name for cr in candidate_results]
   480	    results = {}
   481	
   482	    for metric_name in metric_names:
   483	        print(f"\n  [Weighted] Computing G matrix: {metric_name}...")
   484	        G = compute_G_matrix(gp_samples, candidate_results, metric_name)
   485	
   486	        results[metric_name] = {}
   487	        for tau in taus:
   488	            bms = soft_transfer_weighted(G, tau, instance_names, log_mlls)
   489	            bms.metric_name = metric_name
   490	            results[metric_name][tau] = bms
   491	
   492	    return results
   493	
   494	
   495	# ═══════════════════════════════════════════════════════════════════
   496	# Visualization
   497	# ═══════════════════════════════════════════════════════════════════
   498	
   499	def plot_strategy_comparison(
   500	    averaged_results: Dict,
   501	    robust_results: Dict,
   502	    weighted_results: Dict,
   503	    original_results: Dict = None,
   504	    metric_name: str = "pw_kl_vcal",
   505	    tau: float = 1.0,
   506	    figsize: tuple = None,
   507	):
   508	    """
   509	    Bar chart comparing all strategies for a single metric.
   510	
   511	    Groups: Original Boltzmann, Averaged GP, Median, Trimmed Mean, Rank, Weighted
   512	    """
   513	    import matplotlib.pyplot as plt
   514	
   515	    groups = []
   516	    posteriors_list = []
   517	
   518	    # Original Boltzmann (if provided)
   519	    if original_results and metric_name in original_results:
   520	        taus = sorted(original_results[metric_name].keys())
   521	        closest = min(taus, key=lambda t: abs(t - tau))
   522	        bms = original_results[metric_name][closest]
   523	        groups.append("Boltzmann\n(original)")
   524	        posteriors_list.append(bms.instance_posteriors)
   525	        instance_names = bms.instance_names
   526	    else:
   527	        instance_names = None
   528	
   529	    # Averaged GP
   530	    if metric_name in averaged_results:
   531	        ar = averaged_results[metric_name]
   532	        groups.append("Averaged\nGP")
   533	        posteriors_list.append(ar["posteriors"])
   534	        if instance_names is None:
   535	            instance_names = ar["names"]
   536	
   537	    # Robust methods
   538	    if metric_name in robust_results:
   539	        for method in ["median", "trimmed_mean", "rank"]:
   540	            rr = robust_results[metric_name][method]
   541	            label = {"median": "Median", "trimmed_mean": "Trimmed\nMean",
   542	                     "rank": "Rank"}[method]
   543	            groups.append(label)
   544	            posteriors_list.append(rr.posteriors)
   545	            if instance_names is None:
   546	                instance_names = rr.instance_names
   547	
   548	    # Weighted Boltzmann
   549	    if weighted_results and metric_name in weighted_results:
   550	        taus_w = sorted(weighted_results[metric_name].keys())
   551	        closest = min(taus_w, key=lambda t: abs(t - tau))
   552	        bms_w = weighted_results[metric_name][closest]
   553	        groups.append("MLL-\nWeighted")
   554	        posteriors_list.append(bms_w.instance_posteriors)
   555	
   556	    if not groups:
   557	        print(f"  No results for metric {metric_name}")
   558	        return None
   559	
   560	    n_groups = len(groups)
   561	    n_models = len(instance_names)
   562	    colors = ['#e74c3c', '#3498db', '#2ecc71', '#9b59b6']
   563	
   564	    if figsize is None:
   565	        figsize = (max(10, 2 * n_groups), 5)
   566	
   567	    fig, ax = plt.subplots(figsize=figsize)
   568	    x = np.arange(n_groups)
   569	    width = 0.8 / n_models
   570	
   571	    for m_idx, model_name in enumerate(instance_names):
   572	        vals = [p[m_idx] for p in posteriors_list]
   573	        offset = (m_idx - n_models / 2 + 0.5) * width
   574	        ax.bar(x + offset, vals, width, label=model_name,
   575	               color=colors[m_idx % len(colors)])
   576	
   577	    ax.set_xticks(x)
   578	    ax.set_xticklabels(groups, fontsize=9)
   579	    ax.set_ylabel("Posterior probability")
   580	    ax.set_title(f"Strategy Comparison — {metric_name} (τ={tau:.1f})", fontsize=13)
   581	    ax.set_ylim(0, 1)
   582	    ax.axhline(0.25, color='gray', linestyle=':', alpha=0.5, label='uniform')
   583	    ax.legend(fontsize=8, loc='upper right')
   584	    ax.grid(True, alpha=0.2, axis='y')
   585	    fig.tight_layout()
   586	    return fig
   587	
   588	
   589	def plot_all_strategies_grid(
   590	    averaged_results: Dict,
   591	    robust_results: Dict,
   592	    weighted_results: Dict,
   593	    original_results: Dict = None,
   594	    metric_names: Optional[List[str]] = None,
   595	    tau: float = 1.0,
   596	    figsize: tuple = None,
   597	):
   598	    """
   599	    Grid of strategy comparisons: one row per metric.
   600	    """
   601	    import matplotlib.pyplot as plt
   602	
   603	    if metric_names is None:
   604	        metric_names = list(averaged_results.keys())
   605	
   606	    n_metrics = len(metric_names)
   607	    if figsize is None:
   608	        figsize = (14, 3.5 * n_metrics)
   609	
   610	    fig, axes = plt.subplots(n_metrics, 1, figsize=figsize)
   611	    if n_metrics == 1:
   612	        axes = [axes]
   613	
   614	    colors = ['#e74c3c', '#3498db', '#2ecc71', '#9b59b6']
   615	
   616	    for ax, metric_name in zip(axes, metric_names):
   617	        groups = []
   618	        posteriors_list = []
   619	        instance_names = None
   620	
   621	        # Gather all strategies
   622	        if original_results and metric_name in original_results:
   623	            taus = sorted(original_results[metric_name].keys())
   624	            closest = min(taus, key=lambda t: abs(t - tau))
   625	            bms = original_results[metric_name][closest]
   626	            groups.append("Boltzmann")
   627	            posteriors_list.append(bms.instance_posteriors)
   628	            instance_names = bms.instance_names
   629	
   630	        if metric_name in averaged_results:
   631	            groups.append("Avg GP")
   632	            posteriors_list.append(averaged_results[metric_name]["posteriors"])
   633	            if instance_names is None:
   634	                instance_names = averaged_results[metric_name]["names"]
   635	
   636	        if metric_name in robust_results:
   637	            for method, label in [("median", "Median"), ("trimmed_mean", "Trimmed"),
   638	                                  ("rank", "Rank")]:
   639	                groups.append(label)
   640	                posteriors_list.append(robust_results[metric_name][method].posteriors)
   641	
   642	        if weighted_results and metric_name in weighted_results:
   643	            taus_w = sorted(weighted_results[metric_name].keys())
   644	            closest = min(taus_w, key=lambda t: abs(t - tau))
   645	            groups.append("MLL-Wt")
   646	            posteriors_list.append(weighted_results[metric_name][closest].instance_posteriors)
   647	
   648	        n_groups = len(groups)
   649	        n_models = len(instance_names) if instance_names else 0
   650	        if n_groups == 0 or n_models == 0:
   651	            continue
   652	
   653	        x = np.arange(n_groups)
   654	        width = 0.8 / n_models
   655	
   656	        for m_idx, model_name in enumerate(instance_names):
   657	            vals = [p[m_idx] for p in posteriors_list]
   658	            offset = (m_idx - n_models / 2 + 0.5) * width
   659	            ax.bar(x + offset, vals, width, label=model_name if ax == axes[0] else "",
   660	                   color=colors[m_idx % len(colors)])
   661	
   662	        ax.set_xticks(x)
   663	        ax.set_xticklabels(groups, fontsize=9)
   664	        ax.set_ylabel("Posterior", fontsize=9)
   665	        ax.set_title(metric_name, fontsize=11, fontweight='bold')
   666	        ax.set_ylim(0, 1)
   667	        ax.axhline(0.25, color='gray', linestyle=':', alpha=0.3)
   668	        ax.grid(True, alpha=0.2, axis='y')
   669	
   670	    axes[0].legend(fontsize=8, loc='upper right')
   671	    fig.suptitle(f"All Aggregation Strategies at τ = {tau:.1f}", fontsize=14)
   672	    fig.tight_layout()
   673	    return fig
   674	
   675	
   676	def plot_weighted_tau_sensitivity(
   677	    weighted_results: Dict[str, Dict[float, BMSStarResult]],
   678	    figsize=None,
   679	):
   680	    """τ sensitivity curves for MLL-weighted Boltzmann."""
   681	    import matplotlib.pyplot as plt
   682	
   683	    metric_names = list(weighted_results.keys())
   684	    n_metrics = len(metric_names)
   685	    ncols = min(4, n_metrics)
   686	    nrows = (n_metrics + ncols - 1) // ncols
   687	    if figsize is None:
   688	        figsize = (4.5 * ncols, 3.5 * nrows)
   689	
   690	    fig, axes = plt.subplots(nrows, ncols, figsize=figsize)
   691	    axes = np.atleast_2d(axes).flatten()
   692	    colors = ['#e74c3c', '#3498db', '#2ecc71', '#9b59b6']
   693	
   694	    for ax_idx, metric_name in enumerate(metric_names):
   695	        ax = axes[ax_idx]
   696	        taus = sorted(weighted_results[metric_name].keys())
   697	        instance_names = weighted_results[metric_name][taus[0]].instance_names
   698	        n_models = len(instance_names)
   699	
   700	        posteriors = np.zeros((len(taus), n_models))
   701	        for t_idx, tau in enumerate(taus):
   702	            posteriors[t_idx] = weighted_results[metric_name][tau].instance_posteriors
   703	
   704	        for m_idx, name in enumerate(instance_names):
   705	            ax.plot(taus, posteriors[:, m_idx], color=colors[m_idx],
   706	                    linewidth=2, label=name)
   707	
   708	        ax.set_xscale('log')
   709	        ax.set_ylim(0, 1)
   710	        ax.set_xlabel('τ', fontsize=9)
   711	        ax.set_ylabel('Posterior', fontsize=9)
   712	        ax.set_title(f"{metric_name} (MLL-weighted)", fontsize=10)
   713	        ax.legend(fontsize=7)
   714	        ax.grid(True, alpha=0.3)
   715	
   716	    for ax_idx in range(n_metrics, len(axes)):
   717	        axes[ax_idx].set_visible(False)
   718	
   719	    fig.suptitle("MLL-Weighted Boltzmann — τ Sensitivity", fontsize=14)
   720	    fig.tight_layout()
   721	    return fig
   722	
   723	
   724	def plot_mll_distribution(log_mlls: np.ndarray, figsize=(8, 4)):
   725	    """Histogram of log marginal likelihoods across HMC samples."""
   726	    import matplotlib.pyplot as plt
   727	
   728	    valid = log_mlls[np.isfinite(log_mlls)]
   729	    fig, ax = plt.subplots(figsize=figsize)
   730	    ax.hist(valid, bins=40, color='steelblue', alpha=0.7, edgecolor='white')
   731	    ax.axvline(np.median(valid), color='red', linestyle='--', label=f'median={np.median(valid):.1f}')
   732	    ax.axvline(np.mean(valid), color='orange', linestyle='--', label=f'mean={np.mean(valid):.1f}')
   733	    ax.set_xlabel("Log Marginal Likelihood")
   734	    ax.set_ylabel("Count")
   735	    ax.set_title("HMC Sample Quality: log p(y|X,θ)")
   736	    ax.legend()
   737	    fig.tight_layout()
   738	    return fig

==================== SOURCE bistar_gp/laplace_evidence.py (line-numbered) ====================
     1	"""
     2	laplace_evidence.py — Laplace Approximation for BI* Model Evidence
     3	
     4	Approximates BI* model evidence with a Laplace expansion around the MAP
     5	estimate under the GP-induced prior. The Laplace path replaced an early
     6	naive prior-importance-sampling estimator whose effective sample size
     7	collapsed beyond a few dimensions, and remains the fast default. Since
     8	D16 the module also provides sampling estimators for Z_Mx: `mc_log_Z_Mx`
     9	(uniform-box MC, accurate at high τ) and `is_log_Z_Mx` (ordinary
    10	defensive-mixture IS). The figure scripts use `is_log_Z_Mx` as their
    11	validated reference for Z_Mx values; it costs more than Laplace and its
    12	reported ESS diagnostics must be checked, but it stays accurate across
    13	the full τ range, where pure Laplace diverges at high τ.
    14	
    15	The model evidence integral:
    16	
    17	  p(y | M_j, ψ) = ∫ p(y | φ, M_j) · p_induced(φ | ψ) dφ
    18	
    19	is approximated as:
    20	
    21	  log p(y | M_j, ψ) ≈ log p(y | φ*) - Ḡ(φ*)/τ + (d/2)log(2π) - (1/2)log|H|
    22	
    23	where:
    24	  φ* = argmax [log p(y|φ) - Ḡ(φ)/τ]   (MAP under induced prior)
    25	  H  = Hessian of -[log p(y|φ) - Ḡ(φ)/τ] at φ*
    26	  d  = number of parameters
    27	  Ḡ(φ) = divergence between GP posterior and candidate prediction at φ
    28	
    29	The three terms have clear interpretations:
    30	  (1) log p(y|φ*) — data fit at MAP
    31	  (2) -Ḡ(φ*)/τ  — GP-induced prior penalty (how well GP "likes" these params)
    32	  (3) (d/2)log(2π) - (1/2)log|H| — Occam factor (complexity penalty)
    33	
    34	This is what makes BI* different from BIC/AIC:
    35	  Term (2) transfers qualitative GP beliefs into model comparison.
    36	  Informative GP → small Ḡ for correct model → correct model wins.
    37	  Vague GP → similar Ḡ for all models → reverts to standard BIC-like behavior.
    38	"""
    39	
    40	import logging
    41	
    42	import numpy as np
    43	from typing import Dict, List, Optional, Tuple
    44	from scipy.optimize import minimize
    45	from scipy.special import softmax, logsumexp
    46	from scipy.linalg import solve_triangular
    47	from dataclasses import dataclass, field
    48	
    49	from bistar_gp.bms_star import GPPosteriorSample, METRICS, log_weight_ess
    50	from bistar_gp.induced_prior import ModelParameterSpace
    51	import bistar_gp.metrics_v2  # noqa: F401 — registers pw_* metrics (incl. the default pw_kl_vcal) into METRICS
    52	
    53	logger = logging.getLogger(__name__)
    54	
    55	# Candidate noise sigma used when noise_param is absent from the param specs —
    56	# a documented contract (tests build sigma-free spaces so integrals run over
    57	# means only), previously copy-pasted as a magic 0.3 across five sites.
    58	DEFAULT_FIXED_SIGMA = 0.3
    59	# Objective value returned for invalid (sigma <= 0) points; large enough that
    60	# L-BFGS-B never accepts them, finite so finite differences stay defined.
    61	_GUARD_PENALTY = 1e10
    62	
    63	
    64	def _noise_sigma(param_space, param_dict) -> float:
    65	    """The candidate's noise sigma at these params (DEFAULT_FIXED_SIGMA when
    66	    the space carries no noise parameter) — the single authority for the
    67	    default previously duplicated across the closures and helpers."""
    68	    return param_dict.get(param_space.noise_param, DEFAULT_FIXED_SIGMA)
    69	
    70	
    71	def _guarded_neg_log(param_space, unpack, neg_log_of_dict):
    72	    """Vectorize a dict-based objective with the shared invalid-noise guard.
    73	    Every Laplace objective in this module (Z_Mx, ordinary evidence, N(M))
    74	    goes through here, so the guard cannot silently desync between them."""
    75	    def neg_log_f(vec):
    76	        pd = unpack(vec)
    77	        if _noise_sigma(param_space, pd) <= 0:
    78	            return _GUARD_PENALTY
    79	        return neg_log_of_dict(pd)
    80	    return neg_log_f
    81	
    82	
    83	def numerical_hessian(f, x, eps=1e-5):
    84	    """
    85	    Compute Hessian of f at x via central finite differences.
    86	    f: R^d → R
    87	    Returns (d, d) matrix.
    88	
    89	    Diagonal entries use the 3-point second-difference through f(x) itself
    90	    (2 evaluations each plus one shared f(x)); the 4-point cross stencil is
    91	    reserved for the off-diagonals, where it is required. Same O(eps^2)
    92	    accuracy, ~2d fewer objective evaluations per Hessian.
    93	    """
    94	    d = len(x)
    95	    H = np.zeros((d, d))
    96	    f0 = f(x)
    97	
    98	    for i in range(d):
    99	        x_p = x.copy(); x_p[i] += eps
   100	        x_m = x.copy(); x_m[i] -= eps
   101	        H[i, i] = (f(x_p) - 2.0 * f0 + f(x_m)) / eps**2
   102	
   103	    for i in range(d):
   104	        for j in range(i + 1, d):
   105	            x_pp = x.copy(); x_pp[i] += eps; x_pp[j] += eps
   106	            x_pm = x.copy(); x_pm[i] += eps; x_pm[j] -= eps
   107	            x_mp = x.copy(); x_mp[i] -= eps; x_mp[j] += eps
   108	            x_mm = x.copy(); x_mm[i] -= eps; x_mm[j] -= eps
   109	
   110	            H[i, j] = (f(x_pp) - f(x_pm) - f(x_mp) + f(x_mm)) / (4 * eps**2)
   111	            H[j, i] = H[i, j]
   112	
   113	    return H
   114	
   115	
   116	def compute_G_at_params(
   117	    param_dict: Dict[str, float],
   118	    param_space: ModelParameterSpace,
   119	    x_eval: np.ndarray,
   120	    avg_gp: GPPosteriorSample,
   121	    metric_fn,
   122	    strict: bool = True,
   123	) -> float:
   124	    """Compute G between candidate prediction at φ and averaged GP.
   125	
   126	    Evaluation failures (a raising predict_fn or metric) are NOT converted
   127	    into a finite energy: before the 2026-09 review fix they returned 1e6,
   128	    which exp(-G/tau) turned into "an extremely poor fit" and which an
   129	    all-failed integral could even win with. Under strict=True (default) the
   130	    failure raises with the parameter point; under strict=False it returns
   131	    NaN, which propagates honestly through every integral and ESS.
   132	    """
   133	    try:
   134	        mu_theta = param_space.predict_fn(x_eval, param_dict)
   135	    except Exception as exc:
   136	        if strict:
   137	            raise EvaluationFailure(
   138	                f"compute_G_at_params: predict_fn of {param_space.model_name!r} "
   139	                f"raised {type(exc).__name__} at {param_dict}: {exc}") from exc
   140	        return np.nan
   141	
   142	    sigma = _noise_sigma(param_space, param_dict)
   143	    sigma2 = max(sigma ** 2, 1e-8)
   144	    n_eval = len(x_eval)
   145	    cov_theta = sigma2 * np.eye(n_eval)
   146	
   147	    try:
   148	        return metric_fn(avg_gp.mean, avg_gp.cov, mu_theta, cov_theta)
   149	    except (np.linalg.LinAlgError, ValueError, RuntimeError, FloatingPointError) as exc:
   150	        if strict:
   151	            raise EvaluationFailure(
   152	                f"compute_G_at_params: metric raised {type(exc).__name__} for "
   153	                f"{param_space.model_name!r} at {param_dict}: {exc}") from exc
   154	        return np.nan
   155	
   156	
   157	# ═══════════════════════════════════════════════════════════════════
   158	# Canonical Z_Mx / evidence / posterior  (docs/plan-zmx-laplace.md, DECISIONS D3)
   159	# ═══════════════════════════════════════════════════════════════════
   160	#
   161	# All log-integrals use the generic Laplace identity
   162	#     log ∫ exp(−f(φ)) dφ  ≈  −f(φ*) + (d/2)log(2π) − ½log|H|,   H = ∇²f(φ*), φ* = argmin f.
   163	# The τ and −log V_ref bookkeeping falls out of the choice of f:
   164	#   Z_Mx:             f = Ḡ (τ enters analytically) → log Z = −Ḡ*/τ + (d/2)log(2πτ) − ½log|H_Ḡ|
   165	#   ordinary evidence f = −log p(y|φ)
   166	#   N(M):             f = −[log p(y|φ) − Ḡ/τ]    (joint MAP)
   167	#   induced evidence  p(y|M,ψ) = N(M)/Z_prior(M),  Z_prior = Z_Mx with Occam (the V cancels)
   168	#
   169	# The occam flag has ONE meaning module-wide: include the −log V_ref term of the
   170	# normalized uniform reference prior p_ref = 1/V_ref. occam=False integrates
   171	# against the raw Lebesgue measure on the box (faithful no-Occam BI*). Every
   172	# construction must apply the SAME reference measure, otherwise cross-construction
   173	# gaps (the ablation ladder's "GP contribution") absorb per-model V_ref
   174	# differences — for the toy spaces a ~3.9-nat cross-model artifact.
   175	
   176	
   177	@dataclass
   178	class ZMxResult:
   179	    """Data-free GP-informed model prior Z_Mx (§1.2 of the plan)."""
   180	    model_name: str
   181	    log_Z: float                 # log Z_Mx, Occam-adjusted
   182	    G_at_min: float              # Ḡ(φ_G*)
   183	    phi_min: Dict[str, float]
   184	    occam: bool
   185	    log_volume: float            # log V_ref
   186	    logdet_H: float
   187	    n_params: int
   188	    tau: float
   189	    converged: bool
   190	    n_clipped: int = 0           # Hessian eigenvalues clipped: >0 means |H| was regularized
   191	    optimizer: Optional[Dict[str, object]] = None   # best start's OptimizerRecord (FIX-5)
   192	    n_starts_failed: int = 0     # starts whose minimize raised or reported failure
   193	
   194	
   195	class EvaluationFailure(RuntimeError):
   196	    """A candidate predictor or divergence metric failed under strict
   197	    evaluation (fix pass 1b). Subclass of RuntimeError for compatibility with
   198	    callers that catch the pass-1 exception; the optimizer fallback handlers
   199	    re-raise it so it can never turn into a start-point expansion."""
   200	
   201	
   202	@dataclass
   203	class OptimizerRecord:
   204	    """What scipy's minimize actually reported for one start (2026-09 FIX-5).
   205	
   206	    Before this record existed, an optimizer that raised fell back to the
   207	    start point with converged=False, and a non-successful result was
   208	    accepted silently; nothing carried either fact to the caller.
   209	    """
   210	    success: bool
   211	    status: Optional[int] = None
   212	    message: str = ""
   213	    nit: Optional[int] = None
   214	    nfev: Optional[int] = None
   215	    exception: Optional[str] = None
   216	
   217	    def as_dict(self) -> Dict[str, object]:
   218	        return {"success": bool(self.success), "status": self.status,
   219	                "message": str(self.message), "nit": self.nit, "nfev": self.nfev,
   220	                "exception": self.exception}
   221	
   222	
   223	@dataclass
   224	class EvidenceResult:
   225	    """Within-model evidence (kind='ordinary' or 'induced')."""
   226	    model_name: str
   227	    log_evidence: float
   228	    kind: str
   229	    log_N: Optional[float] = None          # induced: log ∫ p(y|φ) exp(−Ḡ/τ) p_ref dφ
   230	    log_Z_prior: Optional[float] = None    # induced: log Z_Mx^{Occam}
   231	    log_lik_at_map: Optional[float] = None
   232	    phi_star: Dict[str, float] = field(default_factory=dict)
   233	    n_params: int = 0
   234	    converged: bool = True
   235	    n_clipped: int = 0           # Hessian eigenvalues clipped: >0 means |H| was regularized
   236	    optimizer: Optional[Dict[str, object]] = None   # FIX-5
   237	    n_starts_failed: int = 0
   238	
   239	
   240	@dataclass
   241	class ModelPosteriorResult:
   242	    """Normalized model posterior under a chosen assembly (§2 of the plan).
   243	
   244	    A non-finite kernel for ANY model (a non-strict evaluation failure) makes
   245	    every posterior NaN: the softmax is a joint normalization, so no candidate
   246	    can win a comparison one of them failed (review F7); `all_converged` is
   247	    False in that case.
   248	    """
   249	    construction: str                      # 'baseline' | 'I' | 'II'
   250	    occam: bool
   251	    tau: float
   252	    model_names: List[str]
   253	    posteriors: Dict[str, float]
   254	    log_kernel: Dict[str, float]           # unnormalized log p(M|D) per model
   255	    components: Dict[str, Dict[str, float]]
   256	    # metric used for the GP terms; recorded so reuse paths (precomputed_II)
   257	    # can verify compatibility instead of silently mixing metrics (codex
   258	    # finding: without this the mismatch was unenforceable).
   259	    metric_name: str = ""
   260	    # FIX-5: False when any model's Laplace optimization did not converge;
   261	    # per-model detail in components[name]["converged"], ["n_clipped"],
   262	    # ["n_starts_failed"].
   263	    all_converged: bool = True
   264	
   265	
   266	def _log_reference_volume(param_space) -> float:
   267	    """log V_ref = Σ log(upper − lower) over the uniform reference-prior box."""
   268	    return float(np.sum([np.log(ps.bounds[1] - ps.bounds[0])
   269	                         for ps in param_space.param_specs]))
   270	
   271	
   272	def _laplace_logdet(H: np.ndarray, floor: float = 1e-8, cap: float = 1e12) -> Tuple[float, int]:
   273	    """log|H| from eigenvalues clipped to [floor, cap]; robust to non-PSD/cliff curvature.
   274	
   275	    Clipping prevents both a negative/near-zero eigenvalue (from a saddle or flat
   276	    direction) and a cliff at a bounds-adjacent MAP from fabricating ~1e17 curvature.
   277	    A floored direction contributes −½·log(floor) ≈ +9.2 nats to the log-integral,
   278	    an arbitrary regularization rather than geometry — so n_clipped is propagated
   279	    into every result (ZMxResult/EvidenceResult.n_clipped, the Construction-II
   280	    components detail) and a warning is logged; treat any n_clipped > 0 evidence
   281	    value as floor-dependent.
   282	    """
   283	    H = 0.5 * (H + H.T)
   284	    eig = np.linalg.eigvalsh(H)
   285	    clipped = np.clip(eig, floor, cap)
   286	    n_clipped = int(np.sum((eig < floor) | (eig > cap)))
   287	    return float(np.sum(np.log(clipped))), n_clipped
   288	
   289	
   290	def _unpacker(param_space):
   291	    """vector -> {param name: value} in param_specs order (the inverse packer
   292	    was dead code at every call site and is gone)."""
   293	    specs = param_space.param_specs
   294	    def unpack(vec):
   295	        return {ps.name: float(vec[j]) for j, ps in enumerate(specs)}
   296	    return unpack
   297	
   298	
   299	def _x0_and_bounds(param_space, mle_params):
   300	    specs = param_space.param_specs
   301	    bounds = [(ps.bounds[0], ps.bounds[1]) for ps in specs]
   302	    if mle_params is not None:
   303	        x0 = np.array([mle_params[ps.name] for ps in specs])
   304	    else:
   305	        x0 = np.array([(b[0] + b[1]) / 2 for b in bounds])
   306	    return x0, bounds
   307	
   308	
   309	def _log_likelihood(param_space, x_train, y_train, param_dict,
   310	                    strict: bool = True) -> float:
   311	    try:
   312	        mu = param_space.predict_fn(x_train, param_dict)
   313	    except Exception as exc:
   314	        # The -1e10 sentinel of the pre-2026-09 code made a raising predictor
   315	        # look like an astronomically poor fit; raise, or NaN when not strict.
   316	        if strict:
   317	            raise EvaluationFailure(
   318	                f"_log_likelihood: predict_fn of {param_space.model_name!r} "
   319	                f"raised {type(exc).__name__} at {param_dict}: {exc}") from exc
   320	        return np.nan
   321	    sigma = _noise_sigma(param_space, param_dict)
   322	    sigma2 = max(sigma ** 2, 1e-8)
   323	    n = len(y_train)
   324	    resid = y_train - mu
   325	    return -0.5 * n * np.log(2 * np.pi * sigma2) - 0.5 * np.sum(resid ** 2) / sigma2
   326	
   327	
   328	def _optimizer_record(res) -> "OptimizerRecord":
   329	    return OptimizerRecord(
   330	        success=bool(getattr(res, "success", False)),
   331	        status=(int(res.status) if getattr(res, "status", None) is not None else None),
   332	        message=str(getattr(res, "message", "")),
   333	        nit=(int(res.nit) if getattr(res, "nit", None) is not None else None),
   334	        nfev=(int(res.nfev) if getattr(res, "nfev", None) is not None else None),
   335	    )
   336	
   337	
   338	def _laplace_log_integral(neg_log_f, x0, bounds, d, eps=1e-4):
   339	    """Generic Laplace: returns (log_integral, x_star, f_star, logdet, converged,
   340	    n_clipped, optimizer_record). The record (FIX-5) carries scipy's own
   341	    success flag and message, or the exception text when minimize raised and
   342	    the start point was used instead."""
   343	    try:
   344	        res = minimize(neg_log_f, x0, bounds=bounds, method="L-BFGS-B",
   345	                       options={"maxiter": 500, "ftol": 1e-10})
   346	        x_star, converged = res.x, bool(res.success)
   347	        record = _optimizer_record(res)
   348	    except EvaluationFailure:
   349	        # A strict evaluation failure inside the optimizer's own function
   350	        # evaluations is not an optimizer fault: it must reach the caller
   351	        # (fix pass 1b, review R7), never a start-point expansion.
   352	        raise
   353	    except Exception as exc:
   354	        x_star, converged = np.asarray(x0, dtype=float), False
   355	        record = OptimizerRecord(success=False, message="minimize raised",
   356	                                 exception=f"{type(exc).__name__}: {exc}")
   357	        logger.warning("Laplace optimizer raised (%s); expanding around the start point",
   358	                       record.exception)
   359	    f_star = float(neg_log_f(x_star))
   360	    if not np.isfinite(f_star):
   361	        # Non-strict evaluation failure (NaN objective): no Hessian can be
   362	        # formed; propagate NaN honestly instead of clipping a NaN matrix.
   363	        logger.warning("Laplace objective is non-finite at x*=%s; returning NaN", x_star)
   364	        record.success = False
   365	        record.message = record.message or "non-finite objective at x*"
   366	        return np.nan, x_star, f_star, np.nan, False, 0, record
   367	    # Bounds-aware Hessian point: L-BFGS-B may pin x* on the box boundary,
   368	    # where a centered stencil evaluates the objective OUTSIDE the box (an
   369	    # undefined regime the guards turn into cliffs, which the eigenvalue
   370	    # floor then converts into an arbitrary +9.2-nats-per-direction term).
   371	    # Nudging the evaluation point 2*eps into the interior keeps every
   372	    # stencil point in-box; genuinely flat directions still floor (and are
   373	    # flagged via n_clipped), but boundary-pinning no longer fabricates or
   374	    # destroys curvature. The integral is still expanded around f(x*).
   375	    lo = np.array([b[0] for b in bounds], dtype=float)
   376	    hi = np.array([b[1] for b in bounds], dtype=float)
   377	    # inset capped at half the box width: for a pathological dimension
   378	    # narrower than 4*eps a fixed 2*eps inset would INVERT the clip and
   379	    # push x_h outside the box (codex finding); capping degrades gracefully
   380	    # to the box midpoint instead.
   381	    inset = np.minimum(2 * eps, 0.5 * (hi - lo))
   382	    x_h = np.clip(x_star, lo + inset, hi - inset)
   383	    H = numerical_hessian(neg_log_f, x_h, eps=eps)
   384	    if not np.all(np.isfinite(H)):
   385	        # Non-strict failure on the Hessian stencil (review R8): no expansion
   386	        # exists; keep the optimizer's own record, mark the integral invalid.
   387	        logger.warning("Laplace Hessian is non-finite at x*=%s; returning NaN", x_star)
   388	        record.success = False
   389	        record.message = f"non-finite Hessian at x*; optimizer: {record.message}"
   390	        return np.nan, x_star, f_star, np.nan, False, 0, record
   391	    logdet, n_clipped = _laplace_logdet(H)
   392	    if n_clipped:
   393	        logger.warning(
   394	            "Laplace Hessian regularized: %d of %d eigenvalues clipped at x*=%s; "
   395	            "the log-integral carries a floor/cap-dependent term", n_clipped, d, x_star)
   396	    log_integral = -f_star + 0.5 * d * np.log(2 * np.pi) - 0.5 * logdet
   397	    return log_integral, x_star, f_star, logdet, converged, n_clipped, record
   398	
   399	
   400	def laplace_log_Z_Mx(param_space, x_eval, avg_gp, *, metric_name="pw_kl_vcal",
   401	                     tau=1.0, occam=False, mle_params=None,
   402	                     starts=None, strict=True) -> ZMxResult:
   403	    """Data-free GP-informed model prior Z_Mx = ∫ exp(−Ḡ/τ) [p_ref] dφ (§1.2).
   404	
   405	    Expands at φ_G* = argmin Ḡ with the Hessian of Ḡ. NO data likelihood. With
   406	    occam=True the uniform reference prior p_ref = 1/V_ref contributes −log V_ref.
   407	
   408	    τ enters analytically (argmin Ḡ/τ = argmin Ḡ and H_{Ḡ/τ} = H_Ḡ/τ):
   409	        log Z(τ) = −Ḡ*/τ + (d/2)·log(2πτ) − ½·log|H_Ḡ|
   410	    so the optimization, the Hessian, and the eigenvalue clipping in
   411	    _laplace_logdet are all evaluated once on Ḡ itself — which eigenvalues get
   412	    floored cannot depend on τ, keeping τ-sweeps free of clipping artifacts.
   413	
   414	    starts: optional list of {param: value} dicts for MULTI-START optimization
   415	    (the min-Ḡ* result wins). Ḡ landscapes with sinusoidal candidates are
   416	    multimodal — a single midpoint/MLE start can miss the global basin
   417	    entirely (plan-viz-unification §0 V1); mle_params, if also given, is
   418	    appended as one more start.
   419	    """
   420	    metric_fn = METRICS[metric_name]
   421	    d = param_space.n_params
   422	    unpack = _unpacker(param_space)
   423	
   424	    neg_log_f = _guarded_neg_log(
   425	        param_space, unpack,
   426	        lambda pd: compute_G_at_params(pd, param_space, x_eval, avg_gp, metric_fn,
   427	                                       strict=strict))
   428	
   429	    start_list = list(starts) if starts else []
   430	    if mle_params is not None or not start_list:
   431	        start_list.append(mle_params)
   432	    runs = [_laplace_log_integral(neg_log_f, *_x0_and_bounds(param_space, start), d)
   433	            for start in start_list]
   434	    best, n_failed = _select_start(runs)          # min f_star == min Ḡ* over finite runs
   435	    log_int, x_star, G_star, logdet, conv, n_clip, record = best
   436	    # log_int is the τ=1 integral −Ḡ* + (d/2)log(2π) − ½log|H_Ḡ|; rescale to τ.
   437	    log_int_tau = log_int + G_star - G_star / tau + 0.5 * d * np.log(tau)
   438	    log_V = _log_reference_volume(param_space)
   439	    log_Z = log_int_tau - (log_V if occam else 0.0)
   440	    return ZMxResult(model_name=param_space.model_name, log_Z=log_Z,
   441	                     G_at_min=G_star, phi_min=unpack(x_star), occam=occam,
   442	                     log_volume=log_V, logdet_H=logdet, n_params=d, tau=tau,
   443	                     converged=conv, n_clipped=n_clip,
   444	                     optimizer=record.as_dict(), n_starts_failed=n_failed)
   445	
   446	
   447	@dataclass
   448	class ZMxSweepResult:
   449	    """log Z_Mx across a τ ladder from one sampling estimator (mc or is)."""
   450	    model_name: str
   451	    taus: np.ndarray
   452	    log_Z: np.ndarray
   453	    ess: np.ndarray            # per-τ effective sample size of the weights
   454	    estimator: str             # 'mc' | 'is'
   455	    occam: bool
   456	    n_samples: int
   457	    n_starts_failed: int = 0   # FIX-5: proposal-optimizer starts that failed (is only)
   458	    optimizer_records: Optional[List[Dict[str, object]]] = None
   459	
   460	
   461	def _pack(param_space, pd):
   462	    """{param: value} -> vector in param_specs order."""
   463	    return np.array([pd[ps.name] for ps in param_space.param_specs], dtype=float)
   464	
   465	
   466	def _box(param_space):
   467	    lo = np.array([ps.bounds[0] for ps in param_space.param_specs], dtype=float)
   468	    hi = np.array([ps.bounds[1] for ps in param_space.param_specs], dtype=float)
   469	    return lo, hi
   470	
   471	
   472	def _G_of_matrix(param_space, x_eval, avg_gp, metric_fn, X, strict=True):
   473	    """Ḡ evaluated row-wise on an (n, d) parameter matrix."""
   474	    unpack = _unpacker(param_space)
   475	    neg_log_f = _guarded_neg_log(
   476	        param_space, unpack,
   477	        lambda pd: compute_G_at_params(pd, param_space, x_eval, avg_gp, metric_fn,
   478	                                       strict=strict))
   479	    return np.array([neg_log_f(row) for row in X])
   480	
   481	
   482	def _weight_ess(log_w):
   483	    """ESS = (Σw)² / Σw² from log weights via the package's one ESS routine
   484	    (bms_star.log_weight_ess). All -inf weights (every sample out of box)
   485	    give 0, so the starvation warning fires (codex P3); a NaN weight (a
   486	    non-strict evaluation failure) gives NaN, distinct from absent support
   487	    (fix pass 1b, review R8)."""
   488	    return float(log_weight_ess(np.asarray(log_w, dtype=float)))
   489	
   490	
   491	def _select_start(runs):
   492	    """Pick the multi-start winner among runs with a FINITE objective; when
   493	    every run is non-finite return the first so the NaN propagates. The
   494	    result does not depend on the order of the starts (fix pass 1b, review
   495	    R8: `nan < x` is False, so a NaN first start used to absorb the minimum
   496	    while a NaN later start was ignored). Failed starts are those whose
   497	    optimizer record reports failure, which includes every non-finite run."""
   498	    n_failed = sum(1 for r in runs if not r[6].success)
   499	    finite = [r for r in runs if np.isfinite(r[2])]
   500	    if not finite:
   501	        return runs[0], n_failed
   502	    return min(finite, key=lambda r: r[2]), n_failed
   503	
   504	
   505	def mc_log_Z_Mx(param_space, x_eval, avg_gp, taus, *, n_mc=200_000, seed=0,
   506	                metric_name="pw_kl_vcal", occam=False, strict=True) -> ZMxSweepResult:
   507	    """Uniform-box Monte Carlo Z_Mx across a τ ladder: Ḡ is computed ONCE and
   508	    reweighted per τ (the legacy precompute_G_samples pattern, generalized).
   509	
   510	    The box-uniform mean estimates the OCCAM-NORMALIZED quantity
   511	    (1/V)∫exp(−Ḡ/τ)dφ, so occam=False ADDS +log V — the inverse of the
   512	    Laplace path, where occam=True subtracts it (same reference-measure
   513	    convention module-wide, D5).
   514	
   515	    Cheap and unbiased, but the weights starve at low τ (plan §0 V1: ESS
   516	    < 200 below τ≈0.3 on the viz spaces) — check .ess before trusting the
   517	    low-τ end; is_log_Z_Mx is the reference estimator across all τ.
   518	    """
   519	    metric_fn = METRICS[metric_name]
   520	    lo, hi = _box(param_space)
   521	    rng = np.random.default_rng(seed)
   522	    X = rng.uniform(lo, hi, size=(n_mc, len(lo)))
   523	    G = _G_of_matrix(param_space, x_eval, avg_gp, metric_fn, X, strict=strict)
   524	
   525	    taus = np.asarray(list(taus), dtype=float)
   526	    log_V = _log_reference_volume(param_space)
   527	    log_Z = np.empty(len(taus))
   528	    ess = np.empty(len(taus))
   529	    for t, tau in enumerate(taus):
   530	        log_w = -G / tau
   531	        log_Z[t] = logsumexp(log_w) - np.log(n_mc) + (0.0 if occam else log_V)
   532	        ess[t] = _weight_ess(log_w)
   533	    return ZMxSweepResult(model_name=param_space.model_name, taus=taus,
   534	                          log_Z=log_Z, ess=ess, estimator="mc", occam=occam,
   535	                          n_samples=n_mc)
   536	
   537	
   538	class _DefensiveProposal:
   539	    """Mixture proposal for ordinary-IS Z_Mx: ½·uniform-box + ½·equal-weight
   540	    UNTRUNCATED Gaussians at the multi-start Ḡ-optima with covariances
   541	    τ_k·H⁻¹ over a τ_k ladder.
   542	
   543	    The Gaussians are normalized on R^d and the box constraint is an
   544	    INDICATOR on the integrand (out-of-box draws get zero weight), so the
   545	    mixture density integrates to 1 by construction — no per-component
   546	    truncation-mass bookkeeping (plan §1.2, codex watchpoint). Sampling and
   547	    density evaluation share the same component parameters; their consistency
   548	    is pinned by the ∫_box 1 dφ = V test (plan §6.10).
   549	    """
   550	
   551	    def __init__(self, lo, hi, centers, covs):
   552	        self.lo, self.hi = lo, hi
   553	        self.d = len(lo)
   554	        self.log_V = float(np.sum(np.log(hi - lo)))
   555	        self.chols = [np.linalg.cholesky(C) for C in covs]
   556	        self.centers = [np.asarray(c, dtype=float) for c in centers]
   557	        self.n_gauss = len(self.centers)
   558	
   559	    def sample(self, rng, n):
   560	        comp = rng.integers(0, 2, size=n)          # 0: uniform half, 1: gaussian half
   561	        X = rng.uniform(self.lo, self.hi, size=(n, self.d))
   562	        if self.n_gauss:
   563	            which = rng.integers(0, self.n_gauss, size=n)
   564	            Z = rng.standard_normal(size=(n, self.d))
   565	            for j in range(self.n_gauss):
   566	                m = (comp == 1) & (which == j)
   567	                if m.any():
   568	                    X[m] = self.centers[j] + Z[m] @ self.chols[j].T
   569	        return X
   570	
   571	    def log_q(self, X):
   572	        n = len(X)
   573	        in_box = np.all((X >= self.lo) & (X <= self.hi), axis=1)
   574	        parts = [np.where(in_box, np.log(0.5) - self.log_V, -np.inf)]
   575	        for c, L in zip(self.centers, self.chols):
   576	            y = solve_triangular(L, (X - c).T, lower=True)
   577	            log_det = np.sum(np.log(np.diag(L)))
   578	            lp = (-0.5 * np.sum(y ** 2, axis=0) - log_det
   579	                  - 0.5 * self.d * np.log(2 * np.pi))
   580	            parts.append(np.log(0.5) - np.log(self.n_gauss) + lp)
   581	        return logsumexp(np.vstack(parts), axis=0), in_box
   582	
   583	
   584	def _multistart_G_optima(param_space, x_eval, avg_gp, metric_fn, starts,
   585	                         eps=1e-4, strict=True):
   586	    """[(x*, Ḡ*, eigval_clipped, eigvec, optimizer_record)] per start — the IS
   587	    proposal's Gaussian anchors, with the Hessian eigendecomposition kept
   588	    EXPLICIT so the caller inverts in eigen space (codex P2: reconstructing
   589	    the clipped matrix and calling np.linalg.inv can raise on the
   590	    ~1e20-condition flat+cliff combination the clipping exists to survive).
   591	    The fifth element (FIX-5) records scipy's success flag and message, or
   592	    the exception when minimize raised; earlier code silently used the start
   593	    point in that case and never inspected res.success."""
   594	    unpack = _unpacker(param_space)
   595	    neg_log_f = _guarded_neg_log(
   596	        param_space, unpack,
   597	        lambda pd: compute_G_at_params(pd, param_space, x_eval, avg_gp, metric_fn,
   598	                                       strict=strict))
   599	    lo, hi = _box(param_space)
   600	    bounds = list(zip(lo, hi))
   601	    out = []
   602	    for start in (starts or [None]):
   603	        x0, _ = _x0_and_bounds(param_space, start)
   604	        try:
   605	            res = minimize(neg_log_f, x0, bounds=bounds, method="L-BFGS-B",
   606	                           options={"maxiter": 500, "ftol": 1e-10})
   607	            x_star = res.x
   608	            record = _optimizer_record(res)
   609	        except EvaluationFailure:
   610	            raise                     # strict evaluation failure: never a fallback (review R7)
   611	        except Exception as exc:
   612	            x_star = np.asarray(x0, dtype=float)
   613	            record = OptimizerRecord(success=False, message="minimize raised",
   614	                                     exception=f"{type(exc).__name__}: {exc}")
   615	        if not record.success:
   616	            logger.warning("_multistart_G_optima(%s): start %s did not converge: %s",
   617	                           param_space.model_name, start, record.exception or record.message)
   618	        inset = np.minimum(2 * eps, 0.5 * (hi - lo))
   619	        f_star = float(neg_log_f(x_star))
   620	        if not np.isfinite(f_star):
   621	            record.success = False
   622	            record.message = f"non-finite objective at x*; optimizer: {record.message}"
   623	        H = numerical_hessian(neg_log_f, np.clip(x_star, lo + inset, hi - inset),
   624	                              eps=eps)
   625	        H = 0.5 * (H + H.T)
   626	        if np.all(np.isfinite(H)):
   627	            eigval, eigvec = np.linalg.eigh(H)
   628	        else:
   629	            # NaN objective (non-strict failure): anchor the proposal on an
   630	            # identity Hessian; the integral itself will carry the NaN.
   631	            record.success = False
   632	            record.message = record.message or "non-finite Hessian at x*"
   633	            eigval, eigvec = np.ones(len(x_star)), np.eye(len(x_star))
   634	        out.append((x_star, f_star, np.clip(eigval, 1e-8, 1e12), eigvec, record))
   635	    return out
   636	
   637	
   638	def is_log_Z_Mx(param_space, x_eval, avg_gp, taus, *, n_is=100_000, seed=0,
   639	                starts=None, metric_name="pw_kl_vcal", occam=False,
   640	                tau_ladder=(0.03, 0.3, 3.0), ess_warn=100.0,
   641	                strict=True) -> ZMxSweepResult:
   642	    """ORDINARY defensive-mixture importance sampling for Z_Mx across a τ
   643	    ladder — the REFERENCE estimator for figure Z_Mx values (plan §1.2).
   644	
   645	    NOT self-normalized IS: Z_Mx is itself the normalizer, so the proposal
   646	    density q is evaluated exactly and
   647	
   648	        log I_raw = logmeanexp_i( −Ḡ(φ_i)/τ − log q(φ_i) ),  φ_i ~ q
   649	
   650	    estimates the RAW Lebesgue integral ∫_box exp(−Ḡ/τ) dφ. occam=False
   651	    returns log I_raw; occam=True returns log I_raw − log V (Laplace-path
   652	    convention). Ḡ and log q are computed once; every τ is a reweighting.
   653	
   654	    starts: multi-start dicts anchoring the proposal's Gaussian components
   655	    (covariances τ_k·H⁻¹ over tau_ladder); pass the same starts you would
   656	    give laplace_log_Z_Mx. The uniform half of the mixture defends against
   657	    optima the starts missed. Warns when any per-τ ESS < ess_warn.
   658	    """
   659	    metric_fn = METRICS[metric_name]
   660	    lo, hi = _box(param_space)
   661	    optima = _multistart_G_optima(param_space, x_eval, avg_gp, metric_fn, starts,
   662	                                  strict=strict)
   663	    records = [rec.as_dict() for *_, rec in optima]
   664	    n_failed = sum(1 for *_, rec in optima if not rec.success)
   665	    # Component covariances tau_k * H^-1, inverted in EIGEN space (never
   666	    # reconstruct-then-inv, codex P2) with per-direction variances capped at
   667	    # the box scale: a floored-flat Hessian direction would otherwise give a
   668	    # ~1e8-variance Gaussian that throws nearly all its samples out of the
   669	    # box. The uniform mixture half keeps the estimator correct either way;
   670	    # the cap keeps it efficient.
   671	    var_cap = float(np.max(0.5 * (hi - lo)) ** 2)
   672	    centers, covs = [], []
   673	    for x_star, _, eigval, eigvec, _rec in optima:
   674	        for tk in tau_ladder:
   675	            var = np.minimum(tk / eigval, var_cap)
   676	            centers.append(x_star)
   677	            covs.append(eigvec @ np.diag(var) @ eigvec.T)
   678	    prop = _DefensiveProposal(lo, hi, centers, covs)
   679	
   680	    rng = np.random.default_rng(seed)
   681	    X = prop.sample(rng, n_is)
   682	    log_q, in_box = prop.log_q(X)
   683	    G = np.full(n_is, np.inf)
   684	    G[in_box] = _G_of_matrix(param_space, x_eval, avg_gp, metric_fn, X[in_box],
   685	                             strict=strict)
   686	
   687	    taus = np.asarray(list(taus), dtype=float)
   688	    log_V = _log_reference_volume(param_space)
   689	    log_Z = np.empty(len(taus))
   690	    ess = np.empty(len(taus))
   691	    for t, tau in enumerate(taus):
   692	        log_w = np.where(in_box, -G / tau - log_q, -np.inf)
   693	        log_Z[t] = (logsumexp(log_w) - np.log(n_is)
   694	                    - (log_V if occam else 0.0))
   695	        ess[t] = _weight_ess(log_w)
   696	    if np.any(ess < ess_warn):
   697	        worst = taus[int(np.argmin(ess))]
   698	        logger.warning(
   699	            "is_log_Z_Mx(%s): ESS below %g (min %.1f at tau=%g) — increase "
   700	            "n_is or supply better starts", param_space.model_name, ess_warn,
   701	            float(ess.min()), worst)
   702	    return ZMxSweepResult(model_name=param_space.model_name, taus=taus,
   703	                          log_Z=log_Z, ess=ess, estimator="is", occam=occam,
   704	                          n_samples=n_is, n_starts_failed=n_failed,
   705	                          optimizer_records=records)
   706	
   707	
   708	def laplace_log_evidence_ordinary(param_space, x_train, y_train, *,
   709	                                  mle_params=None, occam=True,
   710	                                  strict=True) -> EvidenceResult:
   711	    """Ordinary marginal likelihood p_ord(D|M) = ∫ p(y|φ) [p_ref] dφ (no GP).
   712	
   713	    The GP-free primitive for the baseline and Construction I. With occam=True
   714	    (default) the normalized reference prior contributes −log V_ref, making
   715	    this a proper marginal likelihood; occam=False integrates the likelihood
   716	    against the raw Lebesgue measure, matching what Z_Mx and N(M) do under the
   717	    same flag so that cross-construction gaps stay volume-free.
   718	    """
   719	    d = param_space.n_params
   720	    unpack = _unpacker(param_space)
   721	    x0, bounds = _x0_and_bounds(param_space, mle_params)
   722	
   723	    neg_log_f = _guarded_neg_log(
   724	        param_space, unpack,
   725	        lambda pd: -_log_likelihood(param_space, x_train, y_train, pd, strict=strict))
   726	
   727	    log_int, x_star, f_star, logdet, conv, n_clip, record = _laplace_log_integral(neg_log_f, x0, bounds, d)
   728	    log_ev = log_int - (_log_reference_volume(param_space) if occam else 0.0)
   729	    return EvidenceResult(model_name=param_space.model_name, log_evidence=log_ev,
   730	                          kind="ordinary", log_lik_at_map=-f_star,
   731	                          phi_star=unpack(x_star), n_params=d, converged=conv,
   732	                          n_clipped=n_clip, optimizer=record.as_dict(),
   733	                          n_starts_failed=int(not record.success))
   734	
   735	
   736	def _laplace_log_N(param_space, x_train, y_train, x_eval, avg_gp, metric_fn,
   737	                   tau, mle_params, occam, strict=True):
   738	    """log N(M) = log ∫ p(y|φ) exp(−Ḡ/τ) [p_ref] dφ via the joint MAP."""
   739	    d = param_space.n_params
   740	    unpack = _unpacker(param_space)
   741	    x0, bounds = _x0_and_bounds(param_space, mle_params)
   742	
   743	    def _neg_log_joint(pd):
   744	        ll = _log_likelihood(param_space, x_train, y_train, pd, strict=strict)
   745	        G = compute_G_at_params(pd, param_space, x_eval, avg_gp, metric_fn, strict=strict)
   746	        return -(ll - G / tau)
   747	
   748	    neg_log_joint = _guarded_neg_log(param_space, unpack, _neg_log_joint)
   749	
   750	    log_int, x_star, f_star, logdet, conv, n_clip, record = _laplace_log_integral(neg_log_joint, x0, bounds, d)
   751	    log_V = _log_reference_volume(param_space)
   752	    log_N = log_int - (log_V if occam else 0.0)
   753	    pd_star = unpack(x_star)
   754	    ll_star = _log_likelihood(param_space, x_train, y_train, pd_star, strict=strict)
   755	    G_star = compute_G_at_params(pd_star, param_space, x_eval, avg_gp, metric_fn, strict=strict)
   756	    # Additive decomposition of log_N at the joint MAP: fit + gp_penalty + occam == log_N.
   757	    detail = {
   758	        "log_N": log_N,
   759	        "log_lik_at_map": ll_star,
   760	        "G_at_map": G_star,
   761	        "gp_penalty": -G_star / tau,
   762	        "occam": 0.5 * d * np.log(2 * np.pi) - 0.5 * logdet - (log_V if occam else 0.0),
   763	        "n_clipped": n_clip,
   764	        "converged": conv,
   765	        "n_starts_failed": int(not record.success),
   766	        "optimizer": record.as_dict(),
   767	    }
   768	    return log_N, pd_star, conv, detail
   769	
   770	
   771	def laplace_log_evidence_induced(param_space, x_train, y_train, x_eval, avg_gp, *,
   772	                                 metric_name="pw_kl_vcal", tau=1.0,
   773	                                 mle_params=None, strict=True) -> EvidenceResult:
   774	    """Within-model evidence under the GP-induced prior: p(y|M,ψ) = N(M)/Z_prior(M) (§1.3).
   775	
   776	    Occam-independent: both N and Z_prior carry −log V_ref, which cancels.
   777	    """
   778	    metric_fn = METRICS[metric_name]
   779	    log_N, phi_star, conv, detail = _laplace_log_N(param_space, x_train, y_train, x_eval, avg_gp,
   780	                                                   metric_fn, tau, mle_params, occam=True,
   781	                                                   strict=strict)
   782	    zprior = laplace_log_Z_Mx(param_space, x_eval, avg_gp, metric_name=metric_name,
   783	                              tau=tau, occam=True, mle_params=mle_params, strict=strict)
   784	    return EvidenceResult(model_name=param_space.model_name,
   785	                          log_evidence=log_N - zprior.log_Z, kind="induced",
   786	                          log_N=log_N, log_Z_prior=zprior.log_Z,
   787	                          log_lik_at_map=detail["log_lik_at_map"],
   788	                          phi_star=phi_star, n_params=param_space.n_params,
   789	                          converged=(conv and zprior.converged),
   790	                          n_clipped=detail["n_clipped"] + zprior.n_clipped,
   791	                          optimizer=detail["optimizer"],
   792	                          n_starts_failed=detail["n_starts_failed"] + zprior.n_starts_failed)
   793	
   794	
   795	def model_posterior(param_spaces, x_train, y_train, x_eval, avg_gp, mle_params, *,
   796	                    construction="II", metric_name="pw_kl_vcal", tau=1.0,
   797	                    occam=False, strict=True) -> ModelPosteriorResult:
   798	    """Normalized model posterior under the chosen assembly (§2). II is canonical.
   799	
   800	      baseline: p(M|D) ∝ p_ord(D|M)                    (no GP)
   801	      I       : p(M|D) ∝ Z_Mx · p_ord(D|M)             (GP at class level)
   802	      II      : p(M|D) ∝ N(M)                          (GP-induced joint prior)
   803	
   804	    The occam flag applies the −log V_ref reference-volume term to EVERY
   805	    integral of the chosen construction (see the module header), so pairwise
   806	    construction gaps isolate GP terms rather than per-model volume bookkeeping.
   807	    """
   808	    metric_fn = METRICS[metric_name]
   809	    names = list(param_spaces.keys())
   810	    log_kernel, components = {}, {}
   811	    all_converged = True
   812	
   813	    for name in names:
   814	        ps = param_spaces[name]
   815	        mp = mle_params.get(name) if mle_params else None
   816	        if construction == "baseline":
   817	            ev = laplace_log_evidence_ordinary(ps, x_train, y_train, mle_params=mp,
   818	                                               occam=occam, strict=strict)
   819	            log_kernel[name] = ev.log_evidence
   820	            components[name] = {"log_ord_evidence": ev.log_evidence,
   821	                                "converged": ev.converged, "n_clipped": ev.n_clipped,
   822	                                "n_starts_failed": ev.n_starts_failed}
   823	        elif construction == "I":
   824	            zmx = laplace_log_Z_Mx(ps, x_eval, avg_gp, metric_name=metric_name,
   825	                                   tau=tau, occam=occam, mle_params=mp, strict=strict)
   826	            ev = laplace_log_evidence_ordinary(ps, x_train, y_train, mle_params=mp,
   827	                                               occam=occam, strict=strict)
   828	            log_kernel[name] = zmx.log_Z + ev.log_evidence
   829	            components[name] = {"log_Z_Mx": zmx.log_Z, "log_ord_evidence": ev.log_evidence,
   830	                                "converged": bool(zmx.converged and ev.converged),
   831	                                "n_clipped": zmx.n_clipped + ev.n_clipped,
   832	                                "n_starts_failed": zmx.n_starts_failed + ev.n_starts_failed}
   833	        elif construction == "II":
   834	            log_N, _, conv, detail = _laplace_log_N(ps, x_train, y_train, x_eval, avg_gp,
   835	                                                    metric_fn, tau, mp, occam=occam,
   836	                                                    strict=strict)
   837	            log_kernel[name] = log_N
   838	            components[name] = detail
   839	        else:
   840	            raise ValueError(f"unknown construction {construction!r}")
   841	        if not components[name]["converged"]:
   842	            all_converged = False
   843	            logger.warning("model_posterior(%s): Laplace optimization for %r did not "
   844	                           "converge; the reported posterior carries a start-point "
   845	                           "expansion", construction, name)
   846	
   847	    logk = np.array([log_kernel[n] for n in names])
   848	    post = softmax(logk)
   849	    return ModelPosteriorResult(
   850	        construction=construction, occam=occam, tau=tau, model_names=names,
   851	        posteriors={n: float(p) for n, p in zip(names, post)},
   852	        log_kernel={n: float(log_kernel[n]) for n in names},
   853	        components=components, metric_name=metric_name,
   854	        all_converged=all_converged,
   855	    )
   856	
   857	
   858	# ═══════════════════════════════════════════════════════════════════
   859	# Visualization
   860	# ═══════════════════════════════════════════════════════════════════
   861	
   862	def _require_construction_II(results_by_prior):
   863	    """The log N(M) decomposition keys (log_lik_at_map, gp_penalty, occam)
   864	    exist only on Construction-II components; fail with a clear message
   865	    instead of a KeyError deep inside the plot loop."""
   866	    non_ii = [p for p, r in results_by_prior.items() if r.construction != "II"]
   867	    if non_ii:
   868	        raise ValueError(
   869	            f"construction='II' ModelPosteriorResult required; got "
   870	            f"{ {p: results_by_prior[p].construction for p in non_ii} } — "
   871	            "baseline/I components carry no log N(M) decomposition")
   872	
   873	
   874	def plot_evidence_decomposition(
   875	    results_by_prior: Dict[str, "ModelPosteriorResult"],
   876	    figsize: tuple = None,
   877	):
   878	    """
   879	    Additive decomposition of the Construction-II log kernel log N(M) per model,
   880	    grouped by GP prior. Each bar stacks the parts that sum to log N(M):
   881	      fit  = log p(y|φ*)          (data fit at the joint MAP)
   882	      gp   = −Ḡ(φ*)/τ            (GP-compatibility, varies across priors)
   883	      occam = (d/2)log2π − ½log|H| [− log V_ref]   (Laplace complexity term)
   884	
   885	    Pass a dict of prior_name → ModelPosteriorResult (construction="II").
   886	    """
   887	    _require_construction_II(results_by_prior)   # before the mpl import: the
   888	    # rejection must not depend on a working matplotlib install/cache dir
   889	    import matplotlib.pyplot as plt
   890	
   891	    prior_names = list(results_by_prior.keys())
   892	    model_names = results_by_prior[prior_names[0]].model_names
   893	    n_priors = len(prior_names)
   894	    n_models = len(model_names)
   895	
   896	    colors = {
   897	        'Linear': '#e74c3c',
   898	        'Sinusoidal': '#3498db',
   899	        'Sin+Linear': '#2ecc71',
   900	        'Quadratic': '#9b59b6',
   901	    }
   902	
   903	    if figsize is None:
   904	        figsize = (5 * n_priors, 6)
   905	
   906	    fig, axes = plt.subplots(1, n_priors, figsize=figsize, sharey=True)
   907	    if n_priors == 1:
   908	        axes = [axes]
   909	
   910	    for ax, prior_name in zip(axes, prior_names):
   911	        comps = results_by_prior[prior_name].components
   912	        x = np.arange(n_models)
   913	
   914	        for m_idx, model_name in enumerate(model_names):
   915	            c = comps[model_name]
   916	            color = colors.get(model_name, 'gray')
   917	            fit, gp, occ = c["log_lik_at_map"], c["gp_penalty"], c["occam"]
   918	
   919	            ax.bar(x[m_idx], fit, color=color, alpha=0.9,
   920	                   label='Data fit' if m_idx == 0 else "")
   921	            ax.bar(x[m_idx], gp, bottom=fit, color=color, alpha=0.5, hatch='///',
   922	                   label='GP prior −Ḡ/τ' if m_idx == 0 else "")
   923	            ax.bar(x[m_idx], occ, bottom=fit + gp, color=color, alpha=0.3, hatch='...',
   924	                   label='Occam' if m_idx == 0 else "")
   925	
   926	            ax.plot(x[m_idx], c["log_N"], 'k_', markersize=15, markeredgewidth=2)
   927	
   928	        ax.set_xticks(x)
   929	        ax.set_xticklabels(model_names, fontsize=9, rotation=20)
   930	        ax.set_title(f"{prior_name}", fontsize=12, fontweight='bold')
   931	        ax.grid(True, alpha=0.2, axis='y')
   932	        if ax == axes[0]:
   933	            ax.set_ylabel("log N(M) components", fontsize=11)
   934	
   935	    axes[0].legend(fontsize=8, loc='lower left')
   936	    fig.suptitle("BI* Construction II: log N(M) = Fit + GP prior + Occam",
   937	                 fontsize=14)
   938	    fig.tight_layout()
   939	    return fig
   940	
   941	
   942	def plot_prior_penalty_comparison(
   943	    results_by_prior: Dict[str, "ModelPosteriorResult"],
   944	    figsize: tuple = None,
   945	):
   946	    """
   947	    Bar chart of the GP prior penalty −Ḡ(φ*)/τ per model per prior.
   948	
   949	    Isolates the BI* contribution: how much the GP prior favors each model.
   950	    Pass a dict of prior_name → ModelPosteriorResult (construction="II").
   951	    """
   952	    _require_construction_II(results_by_prior)
   953	    import matplotlib.pyplot as plt
   954	
   955	    prior_names = list(results_by_prior.keys())
   956	    model_names = results_by_prior[prior_names[0]].model_names
   957	    n_priors = len(prior_names)
   958	    n_models = len(model_names)
   959	
   960	    colors = ['#e74c3c', '#3498db', '#2ecc71', '#9b59b6']
   961	
   962	    if figsize is None:
   963	        figsize = (max(10, 2.5 * n_priors), 5)
   964	
   965	    fig, ax = plt.subplots(figsize=figsize)
   966	    x = np.arange(n_priors)
   967	    width = 0.8 / n_models
   968	
   969	    for m_idx, model_name in enumerate(model_names):
   970	        penalties = [results_by_prior[p].components[model_name]["gp_penalty"]
   971	                     for p in prior_names]
   972	        offset = (m_idx - n_models / 2 + 0.5) * width
   973	        ax.bar(x + offset, penalties, width, label=model_name,
   974	               color=colors[m_idx % len(colors)])
   975	
   976	    ax.set_xticks(x)
   977	    ax.set_xticklabels(prior_names, fontsize=10)
   978	    ax.set_ylabel("GP Prior Penalty  −Ḡ(φ*)/τ", fontsize=11)
   979	    ax.set_title("BI* Prior Transfer: GP's Preference for Each Model\n"
   980	                 "(less negative = GP likes it more)", fontsize=13)
   981	    ax.legend(fontsize=9)
   982	    ax.grid(True, alpha=0.2, axis='y')
   983	    fig.tight_layout()
   984	    return fig
   985	
   986	
   987	def plot_model_posteriors_by_prior(
   988	    results_by_prior: Dict[str, "ModelPosteriorResult"],
   989	    figsize: tuple = None,
   990	):
   991	    """
   992	    Bar chart: model posteriors p(M|D,ψ) (Construction II), grouped by GP prior.
   993	    Pass a dict of prior_name → ModelPosteriorResult.
   994	    """
   995	    import matplotlib.pyplot as plt
   996	
   997	    prior_names = list(results_by_prior.keys())
   998	    model_names = results_by_prior[prior_names[0]].model_names
   999	    n_priors = len(prior_names)
  1000	    n_models = len(model_names)
  1001	
  1002	    colors = ['#e74c3c', '#3498db', '#2ecc71', '#9b59b6']
  1003	
  1004	    if figsize is None:
  1005	        figsize = (max(10, 2.5 * n_priors), 5)
  1006	
  1007	    fig, ax = plt.subplots(figsize=figsize)
  1008	    x = np.arange(n_priors)
  1009	    width = 0.8 / n_models
  1010	
  1011	    for m_idx, model_name in enumerate(model_names):
  1012	        posteriors = [results_by_prior[p].posteriors[model_name] for p in prior_names]
  1013	        offset = (m_idx - n_models / 2 + 0.5) * width
  1014	        ax.bar(x + offset, posteriors, width, label=model_name,
  1015	               color=colors[m_idx % len(colors)])
  1016	
  1017	    ax.set_xticks(x)
  1018	    ax.set_xticklabels(prior_names, fontsize=10)
  1019	    ax.set_ylabel("Model Posterior p(M|D,ψ)", fontsize=11)
  1020	    ax.set_title("BI* Model Selection: How GP Prior Shapes Model Ranking\n"
  1021	                 "(Construction II, Laplace)", fontsize=13)
  1022	    ax.set_ylim(0, 1)
  1023	    ax.axhline(1.0 / n_models, color='gray', linestyle=':', alpha=0.5, label='uniform')
  1024	    ax.legend(fontsize=9)
  1025	    ax.grid(True, alpha=0.2, axis='y')
  1026	    fig.tight_layout()
  1027	    return fig
  1028	
  1029	
  1030	def model_posterior_tau_sweep(
  1031	    param_spaces: Dict[str, ModelParameterSpace],
  1032	    x_train: np.ndarray,
  1033	    y_train: np.ndarray,
  1034	    x_eval: np.ndarray,
  1035	    avg_gp: GPPosteriorSample,
  1036	    mle_params: Dict[str, Dict[str, float]],
  1037	    taus,
  1038	    *,
  1039	    construction: str = "II",
  1040	    metric_name: str = "pw_kl_vcal",
  1041	    occam: bool = False,
  1042	    strict: bool = True,
  1043	) -> Tuple[List[str], np.ndarray]:
  1044	    """Model posteriors across τ values, exploiting per-construction structure
  1045	    instead of re-running the full Laplace machinery at every τ:
  1046	
  1047	      baseline — τ-independent: one computation, replicated.
  1048	      I        — p_ord is τ-independent (once per model) and Z_Mx rescales
  1049	                 ANALYTICALLY from a single τ=1 pass (the same identity
  1050	                 laplace_log_Z_Mx uses internally):
  1051	                     log Z(τ) = log Z(1) + Ḡ*·(1 − 1/τ) + (d/2)·log τ
  1052	      II       — the joint MAP of log p(y|φ) − Ḡ(φ)/τ genuinely moves with τ,
  1053	                 so it is honestly recomputed per τ (no shortcut exists).
  1054	
  1055	    Returns (model_names, posteriors[t_idx, m_idx]).
  1056	    """
  1057	    names = list(param_spaces.keys())
  1058	    taus = np.asarray(list(taus), dtype=float)
  1059	    logk = np.zeros((len(taus), len(names)))
  1060	
  1061	    if construction == "baseline":
  1062	        mpr = model_posterior(param_spaces, x_train, y_train, x_eval, avg_gp,
  1063	                              mle_params, construction="baseline",
  1064	                              metric_name=metric_name, tau=1.0, occam=occam,
  1065	                              strict=strict)
  1066	        logk[:] = [mpr.log_kernel[n] for n in names]
  1067	    elif construction == "I":
  1068	        for j, name in enumerate(names):
  1069	            ps = param_spaces[name]
  1070	            mp = mle_params.get(name) if mle_params else None
  1071	            ev = laplace_log_evidence_ordinary(ps, x_train, y_train,
  1072	                                               mle_params=mp, occam=occam,
  1073	                                               strict=strict)
  1074	            z1 = laplace_log_Z_Mx(ps, x_eval, avg_gp, metric_name=metric_name,
  1075	                                  tau=1.0, occam=occam, mle_params=mp,
  1076	                                  strict=strict)
  1077	            log_Z_tau = (z1.log_Z + z1.G_at_min * (1.0 - 1.0 / taus)
  1078	                         + 0.5 * ps.n_params * np.log(taus))
  1079	            logk[:, j] = log_Z_tau + ev.log_evidence
  1080	    elif construction == "II":
  1081	        for t_idx, tau in enumerate(taus):
  1082	            mpr = model_posterior(param_spaces, x_train, y_train, x_eval,
  1083	                                  avg_gp, mle_params, construction="II",
  1084	                                  metric_name=metric_name, tau=float(tau),
  1085	                                  occam=occam, strict=strict)
  1086	            logk[t_idx] = [mpr.log_kernel[n] for n in names]
  1087	    else:
  1088	        raise ValueError(f"unknown construction {construction!r}")
  1089	
  1090	    return names, softmax(logk, axis=1)
  1091	
  1092	
  1093	def plot_tau_effect_on_evidence(
  1094	    param_spaces: Dict[str, ModelParameterSpace],
  1095	    x_train: np.ndarray,
  1096	    y_train: np.ndarray,
  1097	    x_eval: np.ndarray,
  1098	    avg_gp: GPPosteriorSample,
  1099	    mle_params: Dict[str, Dict[str, float]],
  1100	    metric_name: str = "pw_kl_vcal",
  1101	    taus: np.ndarray = None,
  1102	    prior_name: str = "",
  1103	    construction: str = "II",
  1104	    occam: bool = False,
  1105	    figsize: tuple = (10, 5),
  1106	):
  1107	    """
  1108	    Show how τ controls the balance between GP prior and complexity.
  1109	
  1110	    Low τ: GP prior dominates → correct model wins (if GP is informative)
  1111	    High τ: prior weakens → reverts to BIC-like complexity ranking
  1112	    """
  1113	    import matplotlib.pyplot as plt
  1114	
  1115	    if taus is None:
  1116	        taus = np.logspace(-1, 2, 25)
  1117	
  1118	    model_names, posteriors = model_posterior_tau_sweep(
  1119	        param_spaces, x_train, y_train, x_eval, avg_gp, mle_params, taus,
  1120	        construction=construction, metric_name=metric_name, occam=occam)
  1121	    n_models = len(model_names)
  1122	
  1123	    colors = ['#e74c3c', '#3498db', '#2ecc71', '#9b59b6']
  1124	    fig, ax = plt.subplots(figsize=figsize)
  1125	
  1126	    for m_idx, name in enumerate(model_names):
  1127	        ax.plot(taus, posteriors[:, m_idx], color=colors[m_idx % len(colors)],
  1128	                linewidth=2.5, label=name)
  1129	
  1130	    ax.set_xscale('log')
  1131	    ax.set_ylim(0, 1)
  1132	    ax.set_xlabel('τ (transfer temperature)', fontsize=12)
  1133	    ax.set_ylabel('Model Posterior', fontsize=12)
  1134	    ax.set_title(f"BI* τ Sensitivity (Construction {construction}, {prior_name})\n"
  1135	                 f"Low τ = strong GP influence   High τ = data only",
  1136	                 fontsize=13)
  1137	    ax.axhline(1.0 / n_models, color='gray', linestyle=':', alpha=0.5)
  1138	    ax.legend(fontsize=10)
  1139	    ax.grid(True, alpha=0.3)
  1140	    fig.tight_layout()
  1141	    return fig
  1142	
  1143	
  1144	def ablation_ladder_posteriors(
  1145	    param_spaces: Dict[str, ModelParameterSpace],
  1146	    x_train: np.ndarray,
  1147	    y_train: np.ndarray,
  1148	    x_eval: np.ndarray,
  1149	    avg_gp: GPPosteriorSample,
  1150	    mle_params: Dict[str, Dict[str, float]],
  1151	    *,
  1152	    metric_name: str = "pw_kl_vcal",
  1153	    tau: float = 1.0,
  1154	    occam: bool = False,
  1155	    precomputed_II: Optional[ModelPosteriorResult] = None,
  1156	) -> Dict[str, Dict[str, float]]:
  1157	    """Posteriors for all three constructions, computing each Laplace
  1158	    primitive ONCE per model: p_ord serves both the baseline and Construction
  1159	    I (three separate model_posterior calls used to compute it twice), Z_Mx
  1160	    serves I, and N(M) serves II. Pass an existing construction="II"
  1161	    ModelPosteriorResult (same metric/τ/occam — enforced) to skip the N(M)
  1162	    optimizations too.
  1163	
  1164	    Returns {construction: {model_name: posterior}}.
  1165	    """
  1166	    metric_fn = METRICS[metric_name]
  1167	    names = list(param_spaces.keys())
  1168	
  1169	    if precomputed_II is not None:
  1170	        mismatch = (precomputed_II.construction != "II"
  1171	                    or precomputed_II.tau != tau
  1172	                    or precomputed_II.occam != occam
  1173	                    or precomputed_II.metric_name != metric_name
  1174	                    or list(precomputed_II.model_names) != names)
  1175	        if mismatch:
  1176	            raise ValueError(
  1177	                "precomputed_II must be a construction='II' result with the "
  1178	                "same tau/occam/metric_name/model set as this ladder call")
  1179	
  1180	    logk = {c: [] for c in ("baseline", "I", "II")}
  1181	    for name in names:
  1182	        ps = param_spaces[name]
  1183	        mp = mle_params.get(name) if mle_params else None
  1184	        ev = laplace_log_evidence_ordinary(ps, x_train, y_train, mle_params=mp,
  1185	                                           occam=occam)
  1186	        zmx = laplace_log_Z_Mx(ps, x_eval, avg_gp, metric_name=metric_name,
  1187	                               tau=tau, occam=occam, mle_params=mp)
  1188	        if precomputed_II is not None:
  1189	            log_N = precomputed_II.log_kernel[name]
  1190	        else:
  1191	            log_N, _, _, _ = _laplace_log_N(ps, x_train, y_train, x_eval,
  1192	                                            avg_gp, metric_fn, tau, mp,
  1193	                                            occam=occam)
  1194	        logk["baseline"].append(ev.log_evidence)
  1195	        logk["I"].append(zmx.log_Z + ev.log_evidence)
  1196	        logk["II"].append(log_N)
  1197	
  1198	    return {c: {n: float(p) for n, p in zip(names, softmax(np.array(arr)))}
  1199	            for c, arr in logk.items()}
  1200	
  1201	
  1202	def plot_ablation_ladder(
  1203	    param_spaces: Dict[str, ModelParameterSpace],
  1204	    x_train: np.ndarray,
  1205	    y_train: np.ndarray,
  1206	    x_eval: np.ndarray,
  1207	    avg_gp: GPPosteriorSample,
  1208	    mle_params: Dict[str, Dict[str, float]],
  1209	    metric_name: str = "pw_kl_vcal",
  1210	    tau: float = 1.0,
  1211	    occam: bool = False,
  1212	    prior_name: str = "",
  1213	    figsize: tuple = None,
  1214	    precomputed_II: Optional[ModelPosteriorResult] = None,
  1215	):
  1216	    """
  1217	    Baseline / Construction I / Construction II model posteriors side by side.
  1218	
  1219	    baseline: no GP.  I: GP as model prior × ordinary evidence.
  1220	    II (canonical): GP-induced joint prior. Each pairwise gap isolates one GP
  1221	    contribution (baseline vs I = the GP model prior; I vs II = the induced
  1222	    parameter prior; baseline vs II = the total GP contribution).
  1223	    precomputed_II: reuse an existing construction="II" result (same
  1224	    metric/τ/occam) instead of recomputing N(M) per model.
  1225	    """
  1226	    import matplotlib.pyplot as plt
  1227	
  1228	    model_names = list(param_spaces.keys())
  1229	    constructions = ["baseline", "I", "II"]
  1230	    post = ablation_ladder_posteriors(
  1231	        param_spaces, x_train, y_train, x_eval, avg_gp, mle_params,
  1232	        metric_name=metric_name, tau=tau, occam=occam,
  1233	        precomputed_II=precomputed_II)
  1234	
  1235	    n_c = len(constructions)
  1236	    n_models = len(model_names)
  1237	    colors = ['#e74c3c', '#3498db', '#2ecc71', '#9b59b6']
  1238	    if figsize is None:
  1239	        figsize = (max(9, 2.6 * n_c), 5)
  1240	
  1241	    fig, ax = plt.subplots(figsize=figsize)
  1242	    x = np.arange(n_c)
  1243	    width = 0.8 / n_models
  1244	    for m_idx, model_name in enumerate(model_names):
  1245	        vals = [post[c][model_name] for c in constructions]
  1246	        offset = (m_idx - n_models / 2 + 0.5) * width
  1247	        ax.bar(x + offset, vals, width, label=model_name, color=colors[m_idx % len(colors)])
  1248	
  1249	    ax.set_xticks(x)
  1250	    ax.set_xticklabels(["baseline\n(no GP)", "I\n(GP model prior)", "II\n(GP joint prior)"],
  1251	                       fontsize=10)
  1252	    ax.set_ylabel("Model Posterior p(M|D)", fontsize=11)
  1253	    ax.set_title(f"BI* Ablation Ladder{(' — ' + prior_name) if prior_name else ''}\n"
  1254	                 "baseline vs I: value of GP model prior · I vs II: value of induced parameter prior",
  1255	                 fontsize=12)
  1256	    ax.set_ylim(0, 1)
  1257	    ax.axhline(1.0 / n_models, color='gray', linestyle=':', alpha=0.5)
  1258	    ax.legend(fontsize=9)
  1259	    ax.grid(True, alpha=0.2, axis='y')
  1260	    fig.tight_layout()
  1261	    return fig

==================== SOURCE bistar_gp/debias.py (line-numbered) ====================
     1	"""
     2	Debiasing pipeline: fit additive GP, decompose, extract labeled components.
     3	Works for any number of additive components.
     4	
     5	2026-09 review fix pass (FIX-1 and FIX-2). The hyperparameter-draw routines
     6	`decompose_model_hmc` and `decompose_model_mcmc` used to discard each draw's
     7	conditional covariance and report `std` as the across-draw spread of the
     8	conditional means alone, which understated every band they produced (the
     9	D58 Mauna cards by an order of magnitude). They now retain each draw's
    10	conditional variance and report law-of-total-variance moments,
    11	
    12	    Var[f(x) | y] = E_d[ Var(f(x) | y, eta_d) ] + Var_d[ E(f(x) | y, eta_d) ],
    13	
    14	for every component, for the full posterior of the summed kernel, and for
    15	any requested GROUP of components. Group moments come from conditioning the
    16	summed group blocks with the Cholesky factor of the entire training
    17	covariance plus noise, never from summing component variances, so a group
    18	containing every component reproduces the full posterior exactly.
    19	"""
    20	
    21	import functools
    22	import logging
    23	import operator
    24	
    25	import torch
    26	import numpy as np
    27	from typing import Dict, List, Optional, Sequence, Tuple
    28	from dataclasses import dataclass, field
    29	
    30	from .decompose import (
    31	    decompose_additive_gp, decompose_component, compute_cholesky,
    32	    sample_from_component, mixture_central_interval,
    33	)
    34	
    35	logger = logging.getLogger(__name__)
    36	
    37	
    38	@dataclass
    39	class ComponentResult:
    40	    """Posterior summary of one additive component (or of a component group).
    41	
    42	    ``mean``, ``std`` and ``cov`` are TOTAL posterior moments over the
    43	    retained hyperparameter draws (law of total variance). ``samples`` keeps
    44	    its historical position and meaning for the MAP path (function draws);
    45	    on the draw-based paths it holds the per-draw conditional means, and
    46	    ``samples_kind`` says which. ``conditional_means`` and
    47	    ``conditional_vars`` (n_draws, n_test) are what interval construction
    48	    needs; ``within_var_mean`` and ``between_var`` are the two terms whose
    49	    sum is ``std ** 2``.
    50	    """
    51	    name: str
    52	    mean: np.ndarray       # (n_test,)
    53	    std: np.ndarray        # (n_test,)  total posterior sd
    54	    cov: np.ndarray        # (n_test, n_test)  total posterior covariance
    55	    samples: np.ndarray    # (n_samples, n_test); see samples_kind
    56	    samples_kind: str = "function_draws"        # or "conditional_means"
    57	    conditional_means: Optional[np.ndarray] = None   # (n_draws, n_test)
    58	    conditional_vars: Optional[np.ndarray] = None    # (n_draws, n_test)
    59	    within_var_mean: Optional[np.ndarray] = None     # E_d[var_d]
    60	    between_var: Optional[np.ndarray] = None         # Var_d[mean_d]
    61	    n_draws: int = 0
    62	
    63	    def central_interval(self, mass: float = 0.95):
    64	        """Pointwise central interval of the retained draw mixture."""
    65	        if self.conditional_means is None or self.conditional_vars is None:
    66	            raise ValueError(
    67	                f"component {self.name!r} carries no per-draw conditional "
    68	                "moments; intervals need a decomposition produced by this "
    69	                "package version")
    70	        return mixture_central_interval(self.conditional_means,
    71	                                        self.conditional_vars, mass=mass)
    72	
    73	
    74	@dataclass
    75	class DecompositionResult:
    76	    """Decomposition of one additive GP posterior.
    77	
    78	    The seven fields below are a positional rebuild contract pinned by
    79	    tests/test_poster_d58_driver.py; additional per-draw information is
    80	    attached as non-field attributes in __post_init__ (``full``, ``groups``,
    81	    ``n_draws_attempted``, ``n_draws_retained``) so that contract holds.
    82	    """
    83	    x_test: np.ndarray
    84	    x_train: np.ndarray
    85	    y_train: np.ndarray
    86	    components: Dict[str, ComponentResult]
    87	    full_mean: np.ndarray
    88	    full_std: np.ndarray
    89	    noise_var: float
    90	
    91	    def __post_init__(self):
    92	        # Non-field attributes (not part of dataclasses.fields()).
    93	        self.full: Optional[ComponentResult] = None
    94	        self.groups: Dict[Tuple[str, ...], ComponentResult] = {}
    95	        self.n_draws_attempted: int = 0
    96	        self.n_draws_retained: int = 0
    97	
    98	    @staticmethod
    99	    def group_key(names: Sequence[str]) -> Tuple[str, ...]:
   100	        return tuple(sorted(set(names)))     # a repeated name is one member (review F3)
   101	
   102	    def group(self, names: Sequence[str]) -> ComponentResult:
   103	        """Joint posterior summary of the sum of the named components.
   104	
   105	        Groups must be requested at decomposition time (``groups=`` on
   106	        `decompose_model_hmc` / `decompose_model_mcmc`) because their
   107	        conditional moments are computed per hyperparameter draw from the
   108	        summed kernel blocks. A group of every component is the full
   109	        posterior; a singleton is the component; an empty group is zero.
   110	        """
   111	        key = self.group_key(names)
   112	        if len(key) == 0:
   113	            n = len(self.x_test)
   114	            zeros = np.zeros(n)
   115	            n_draws = max(self.n_draws_retained, 1)
   116	            return ComponentResult(
   117	                name="", mean=zeros, std=zeros, cov=np.zeros((n, n)),
   118	                samples=np.zeros((n_draws, n)), samples_kind="conditional_means",
   119	                conditional_means=np.zeros((n_draws, n)),
   120	                conditional_vars=np.zeros((n_draws, n)),
   121	                within_var_mean=zeros, between_var=zeros, n_draws=n_draws)
   122	        if len(key) == 1:
   123	            if key[0] not in self.components:
   124	                raise KeyError(f"unknown component {key[0]!r}; components are "
   125	                               f"{list(self.components)}")
   126	            return self.components[key[0]]
   127	        if key == self.group_key(self.components.keys()) and self.full is not None:
   128	            return self.full
   129	        if key in self.groups:
   130	            return self.groups[key]
   131	        raise KeyError(
   132	            f"group {list(key)} was not requested at decomposition time; pass "
   133	            f"groups=[{list(key)}] to decompose_model_hmc/decompose_model_mcmc "
   134	            "(joint group moments cannot be derived from component summaries)")
   135	
   136	
   137	# ── shared draw accumulation ────────────────────────────────────────
   138	
   139	def _blocks_sum(km, names, key):
   140	    """Sum of the named components' kernel blocks. A single name returns its
   141	    block itself (no leading ``0 +`` step), so a lone component follows
   142	    exactly the arithmetic of the per-component path."""
   143	    return functools.reduce(operator.add, [km[n][key] for n in names])
   144	
   145	
   146	def _summarize(name, M, V, cov, samples, samples_kind) -> ComponentResult:
   147	    """The one place a ComponentResult is packaged (fix pass 1b).
   148	
   149	    M, V: (n_draws, n_test) conditional means and variances. cov: the total
   150	    posterior covariance the caller assembled (one draw's conditional
   151	    covariance, or mean_d C_d + Cov_d m_d over draws). std is the
   152	    law-of-total-variance sd sqrt(E_d[var_d] + Var_d[mean_d]).
   153	    """
   154	    M = np.asarray(M, dtype=float)
   155	    V = np.asarray(V, dtype=float)
   156	    within = V.mean(axis=0)
   157	    between = M.var(axis=0)
   158	    std = np.sqrt(np.clip(within + between, 0.0, None))
   159	    return ComponentResult(
   160	        name=name, mean=M.mean(axis=0), std=std, cov=cov,
   161	        samples=samples, samples_kind=samples_kind,
   162	        conditional_means=M, conditional_vars=V,
   163	        within_var_mean=within, between_var=between, n_draws=M.shape[0])
   164	
   165	
   166	def _single_draw_summary(name, mean, cov, samples=None) -> ComponentResult:
   167	    """Summary of one conditional Gaussian (the MAP path), variance floored
   168	    at 1e-10 as before; ``samples`` are function draws when given."""
   169	    mean = np.asarray(mean, dtype=float)
   170	    var = np.clip(np.diag(cov), 1e-10, None)
   171	    if samples is None:
   172	        return _summarize(name, mean[None, :], var[None, :], cov, mean[None, :],
   173	                          "conditional_means")
   174	    return _summarize(name, mean[None, :], var[None, :], cov, samples, "function_draws")
   175	
   176	
   177	def _validated_groups(names, groups) -> Dict[Tuple[str, ...], List[str]]:
   178	    """{sorted-name tuple: members} for the requested groups that need their
   179	    own conditioning (more than one component, fewer than all). Empty,
   180	    singleton and all-component requests are derived by
   181	    DecompositionResult.group; repeated names collapse to one member; unknown
   182	    members raise."""
   183	    out = {}
   184	    for g in (groups or []):
   185	        g = list(g)
   186	        key = DecompositionResult.group_key(g)
   187	        unknown = [n for n in key if n not in names]
   188	        if unknown:
   189	            raise KeyError(f"group {g} names unknown components {unknown}")
   190	        if 1 < len(key) < len(names):
   191	            out[key] = list(key)
   192	    return out
   193	
   194	
   195	class _DrawAccumulator:
   196	    """Accumulate per-draw conditional moments for components, the full
   197	    posterior and requested groups, then form total posterior moments.
   198	
   199	    Targets are keyed by typed tuples ``("component", name)``, ``("group",
   200	    sorted names)`` and ``("full",)``, so a component name can never collide
   201	    with a group label or the full posterior (fix pass 1b, review R3)."""
   202	
   203	    def __init__(self, names: List[str], n_test: int,
   204	                 groups: Optional[Sequence[Sequence[str]]]):
   205	        self.names = list(names)
   206	        self.n_test = n_test
   207	        self.group_keys = _validated_groups(self.names, groups)
   208	        self.targets = ([("full",)] + [("component", n) for n in self.names]
   209	                        + [("group", k) for k in self.group_keys])
   210	        self.means = {t: [] for t in self.targets}
   211	        self.vars = {t: [] for t in self.targets}
   212	        self.cov_sum = {t: np.zeros((n_test, n_test)) for t in self.targets}
   213	        self.n = 0
   214	
   215	    def _members(self, target):
   216	        if target[0] == "full":
   217	            return self.names
   218	        if target[0] == "component":
   219	            return [target[1]]
   220	        return self.group_keys[target[1]]
   221	
   222	    def add_draw(self, km, noise_var, y_train, jitter):
   223	        """One hyperparameter draw: a single Cholesky of the summed training
   224	        covariance serves every target. Every target is conditioned into a
   225	        local record first and committed together at the end, so a failure
   226	        part-way leaves no partially recorded draw (fix pass 1b, review R2)."""
   227	        L = compute_cholesky(_blocks_sum(km, self.names, "XX"), noise_var, jitter)
   228	        record = {}
   229	        for target in self.targets:
   230	            members = self._members(target)
   231	            mean_t, cov_t = decompose_component(
   232	                _blocks_sum(km, members, "XstarX"), _blocks_sum(km, members, "XstarXstar"),
   233	                _blocks_sum(km, members, "XXstar"), L, y_train)
   234	            m = np.array(mean_t.numpy() if hasattr(mean_t, "numpy") else mean_t, dtype=float)
   235	            c = np.asarray(cov_t.numpy() if hasattr(cov_t, "numpy") else cov_t, dtype=float)
   236	            c = 0.5 * (c + c.T)
   237	            v = np.clip(np.diag(c), 0.0, None)
   238	            np.fill_diagonal(c, v)      # keep diag(cov) == std**2 when a diagonal is numerically negative (K3-4)
   239	            record[target] = (m, v, c)
   240	        for target, (m, v, c) in record.items():
   241	            self.means[target].append(m)
   242	            self.vars[target].append(v)
   243	            self.cov_sum[target] += c
   244	        self.n += 1
   245	
   246	    def _finalize_target(self, target, name) -> ComponentResult:
   247	        M = np.stack(self.means[target])                 # (n_draws, n_test)
   248	        V = np.stack(self.vars[target])
   249	        within_cov = self.cov_sum[target] / self.n
   250	        if M.shape[0] > 1:
   251	            between_cov = np.atleast_2d(np.cov(M, rowvar=False, bias=True))
   252	        else:
   253	            between_cov = np.zeros((self.n_test, self.n_test))
   254	        return _summarize(name, M, V, within_cov + between_cov, M, "conditional_means")
   255	
   256	    def finalize(self):
   257	        if self.n == 0:
   258	            raise RuntimeError("no hyperparameter draw was decomposed")
   259	        components = {n: self._finalize_target(("component", n), n) for n in self.names}
   260	        full = self._finalize_target(("full",), "__full__")
   261	        groups = {key: self._finalize_target(("group", key), "+".join(key))
   262	                  for key in self.group_keys}
   263	        return components, full, groups
   264	
   265	
   266	def _assemble(x_test, x_train, y_train, components, full, groups, noise_var,
   267	              n_attempted, n_retained) -> DecompositionResult:
   268	    result = DecompositionResult(
   269	        x_test=x_test.numpy(), x_train=x_train.numpy(), y_train=y_train.numpy(),
   270	        components=components, full_mean=full.mean, full_std=full.std,
   271	        noise_var=noise_var)
   272	    result.full = full
   273	    result.groups = groups
   274	    result.n_draws_attempted = n_attempted
   275	    result.n_draws_retained = n_retained
   276	    return result
   277	
   278	
   279	# ── MAP decomposition ───────────────────────────────────────────────
   280	
   281	def decompose_model(model, likelihood, x_train, y_train, x_test, n_samples=25, jitter=1e-4,
   282	                    groups=None):
   283	    """
   284	    Decompose a fitted additive GP into its components.
   285	    Single set of hyperparameters (MAP). For full Bayesian, use decompose_model_hmc.
   286	
   287	    groups: optional list of component-name lists. Each requested group's
   288	    posterior is the posterior of the summed group kernel conditioned with
   289	    the Cholesky factor of the ENTIRE training covariance (never a
   290	    group-only factorization); retrieve it with ``result.group(names)``.
   291	    """
   292	    model.eval()
   293	    likelihood.eval()
   294	    x_train, y_train, x_test = x_train.double(), y_train.double(), x_test.double()
   295	    noise_var = likelihood.noise.item()
   296	
   297	    km = model.get_component_kernel_matrices(x_train, x_test)
   298	    names = model.component_names
   299	
   300	    with torch.no_grad():
   301	        results = decompose_additive_gp(
   302	            [km[n]["XX"] for n in names],
   303	            [km[n]["XstarX"] for n in names],
   304	            [km[n]["XstarXstar"] for n in names],
   305	            [km[n]["XXstar"] for n in names],
   306	            noise_var, y_train, jitter,
   307	        )
   308	
   309	    components = {}
   310	    full_mean = torch.zeros(x_test.shape[0], dtype=torch.float64)
   311	
   312	    for (mean_i, cov_i), name in zip(results, names):
   313	        samples_i = sample_from_component(mean_i, cov_i, n_samples)
   314	        components[name] = _single_draw_summary(name, mean_i.numpy(), cov_i.numpy(),
   315	                                                samples=samples_i.numpy())
   316	        full_mean += mean_i
   317	
   318	    # Full posterior covariance of f = sum_i f_i is NOT the sum of the
   319	    # component covariances: that drops every inter-component cross-covariance
   320	    # term Cov(f_i, f_j). Compute it directly as the posterior of the sum
   321	    # kernel, reusing one Cholesky of (K_sum(X,X) + sigma^2 I).
   322	    with torch.no_grad():
   323	        K_sum_XX = sum(km[n]["XX"] for n in names)
   324	        K_sum_XstarX = sum(km[n]["XstarX"] for n in names)
   325	        K_sum_XstarXstar = sum(km[n]["XstarXstar"] for n in names)
   326	        K_sum_XXstar = sum(km[n]["XXstar"] for n in names)
   327	        L_sum = compute_cholesky(K_sum_XX, noise_var, jitter)
   328	        _, full_cov_t = decompose_component(
   329	            K_sum_XstarX, K_sum_XstarXstar, K_sum_XXstar, L_sum, y_train,
   330	        )
   331	    full = _single_draw_summary("__full__", full_mean.numpy(), full_cov_t.numpy())
   332	
   333	    # Requested groups (FIX-2b/2d): the summed group blocks conditioned with
   334	    # the same full-kernel factor L_sum; a single hyperparameter setting, so
   335	    # the between-draw term is zero.
   336	    group_results = {}
   337	    for key, members in _validated_groups(names, groups).items():
   338	        with torch.no_grad():
   339	            mean_g_t, cov_g_t = decompose_component(
   340	                _blocks_sum(km, members, "XstarX"), _blocks_sum(km, members, "XstarXstar"),
   341	                _blocks_sum(km, members, "XXstar"), L_sum, y_train)
   342	        cov_g = cov_g_t.numpy()
   343	        group_results[key] = _single_draw_summary("+".join(key), mean_g_t.numpy(),
   344	                                                  0.5 * (cov_g + cov_g.T))
   345	
   346	    result = DecompositionResult(
   347	        x_test=x_test.numpy(), x_train=x_train.numpy(), y_train=y_train.numpy(),
   348	        components=components, full_mean=full_mean.numpy(), full_std=full.std, noise_var=noise_var,
   349	    )
   350	    result.full = full
   351	    result.groups = group_results
   352	    result.n_draws_attempted = result.n_draws_retained = 1
   353	    return result
   354	
   355	
   356	# ── draw-based decompositions ───────────────────────────────────────
   357	
   358	def _raw_parameter_map(model, likelihood):
   359	    """{name: parameter} over model + likelihood scalar parameters, deduplicated
   360	    by object identity with the first name kept (the fit_mcmc_simple naming)."""
   361	    seen = set()
   362	    out = {}
   363	    for n, p in list(model.named_parameters()) + list(likelihood.named_parameters()):
   364	        if p.requires_grad and p.numel() == 1 and id(p) not in seen:
   365	            seen.add(id(p))
   366	            out[n] = p
   367	    return out
   368	
   369	
   370	def decompose_model_mcmc(model, likelihood, x_train, y_train, x_test,
   371	                         mcmc_samples, n_posterior_samples=100, jitter=1e-4,
   372	                         groups=None, rng=None):
   373	    """
   374	    Full Bayesian decomposition over RAW-parameter draws (fit_mcmc_simple
   375	    output: dict keyed by named_parameters names, raw unconstrained values).
   376	
   377	    Draws are matched to parameters BY NAME (the previous positional pairing
   378	    silently mis-assigned any differently ordered dict); every parameter must
   379	    have a key and every key must name a parameter, or the call raises.
   380	    Bands are law-of-total-variance moments (see the module docstring).
   381	    """
   382	    model.eval()
   383	    likelihood.eval()
   384	    x_train, y_train, x_test = x_train.double(), y_train.double(), x_test.double()
   385	    n_test = x_test.shape[0]
   386	
   387	    param_map = _raw_parameter_map(model, likelihood)
   388	    keys = list(mcmc_samples.keys())
   389	    unknown = [k for k in keys if k not in param_map]
   390	    missing = [n for n in param_map if n not in mcmc_samples]
   391	    if unknown or missing:
   392	        raise KeyError(
   393	            "decompose_model_mcmc: sample keys and model parameters do not "
   394	            f"match by name (unknown keys {unknown}, parameters without a key "
   395	            f"{missing}); positional pairing is no longer performed")
   396	
   397	    total_mcmc = len(mcmc_samples[keys[0]])
   398	    n_take = min(n_posterior_samples, total_mcmc)
   399	    if rng is not None:
   400	        indices = rng.choice(total_mcmc, n_take, replace=False)
   401	    else:
   402	        indices = np.random.choice(total_mcmc, n_take, replace=False)
   403	
   404	    names = list(model.component_names)
   405	    acc = _DrawAccumulator(names, n_test, groups)
   406	    noise_var = float(likelihood.noise.item())
   407	    for idx in indices:
   408	        for name, p in param_map.items():
   409	            p.data.fill_(float(mcmc_samples[name][idx]))
   410	        noise_var = likelihood.noise.item()
   411	        km = model.get_component_kernel_matrices(x_train, x_test)
   412	        with torch.no_grad():
   413	            acc.add_draw(km, noise_var, y_train, jitter)
   414	
   415	    components, full, group_results = acc.finalize()
   416	    return _assemble(x_test, x_train, y_train, components, full, group_results,
   417	                     noise_var, len(indices), acc.n)
   418	
   419	
   420	def decompose_model_hmc(model, likelihood, x_train, y_train, x_test,
   421	                        mcmc_samples, kernel_builder, n_posterior_samples=200,
   422	                        jitter=1e-4, groups=None, strict=True, rng=None):
   423	    """
   424	    Decomposition over Pyro/E1 hyperparameter draws (fit_hmc dict schema:
   425	    constrained values keyed by pyro sample-site name).
   426	
   427	    kernel_builder: callable that returns (kernel_components, names), e.g.
   428	                    build_toy_kernels or build_mauna_loa_kernels.
   429	    groups: optional list of component-name lists; each requested group's
   430	            joint posterior (sum of the components) is computed per draw and
   431	            available through DecompositionResult.group(names).
   432	    strict: True (default) raises on an unrecognized or failing sample site
   433	            and on a draw whose decomposition fails; False keeps the previous
   434	            skip-and-continue behavior and records the dropped draws.
   435	    """
   436	    from .model import build_model, build_likelihood, select_hmc_sites, apply_hp_value
   437	
   438	    x_train, y_train, x_test = x_train.double(), y_train.double(), x_test.double()
   439	    n_test = x_test.shape[0]
   440	
   441	    first_key = list(mcmc_samples.keys())[0]
   442	    total_mcmc = len(mcmc_samples[first_key])
   443	    n_take = min(n_posterior_samples, total_mcmc)
   444	    if rng is not None:
   445	        indices = rng.choice(total_mcmc, n_take, replace=False)
   446	    else:
   447	        indices = np.random.choice(total_mcmc, n_take, replace=False)
   448	
   449	    relevant_keys = select_hmc_sites(mcmc_samples.keys())
   450	    kernel_keys = [k for k in relevant_keys if not k.endswith("noise_covar.noise_prior")]
   451	    if not kernel_keys:
   452	        msg = ("decompose_model_hmc: no kernel hyperparameter site recognized "
   453	               f"among {sorted(mcmc_samples.keys())}")
   454	        if strict:
   455	            raise ValueError(msg)
   456	        logger.warning(msg)
   457	
   458	    names = list(model.component_names)
   459	    acc = _DrawAccumulator(names, n_test, groups)
   460	    dropped = []
   461	    last_noise = float(likelihood.noise.item())
   462	
   463	    for idx in indices:
   464	        kernels, fresh_names = kernel_builder()
   465	        if list(fresh_names) != names:
   466	            raise ValueError(
   467	                f"kernel_builder names {list(fresh_names)} differ from the "
   468	                f"model's component names {names}")
   469	        fresh_likelihood = build_likelihood()
   470	        fresh_model, fresh_likelihood = build_model(x_train, y_train, kernels, fresh_names, fresh_likelihood)
   471	
   472	        for pyro_name in relevant_keys:
   473	            val = float(mcmc_samples[pyro_name][idx])
   474	            try:
   475	                applied = apply_hp_value(fresh_model, fresh_likelihood, pyro_name, val)
   476	            except (IndexError, AttributeError, RuntimeError) as exc:
   477	                msg = (f"decompose_model_hmc: applying site {pyro_name!r} for "
   478	                       f"draw {int(idx)} raised {type(exc).__name__}: {exc}")
   479	                if strict:
   480	                    raise ValueError(msg) from exc
   481	                logger.warning(msg)
   482	                continue
   483	            if not applied:
   484	                msg = (f"decompose_model_hmc: apply_hp_value did not recognize "
   485	                       f"site {pyro_name!r} (draw {int(idx)})")
   486	                if strict:
   487	                    raise ValueError(msg)
   488	                logger.warning(msg)
   489	
   490	        fresh_model.eval()
   491	        fresh_likelihood.eval()
   492	        noise_var = fresh_likelihood.noise.item()
   493	        km = fresh_model.get_component_kernel_matrices(x_train, x_test)
   494	
   495	        with torch.no_grad():
   496	            try:
   497	                acc.add_draw(km, noise_var, y_train, jitter)
   498	                last_noise = noise_var
   499	            except RuntimeError as exc:
   500	                if strict:
   501	                    raise RuntimeError(
   502	                        f"decompose_model_hmc: decomposition failed for draw "
   503	                        f"{int(idx)} ({exc}); pass strict=False to drop failing "
   504	                        "draws and record them") from exc
   505	                dropped.append((int(idx), str(exc)))
   506	                continue
   507	
   508	    if acc.n == 0:
   509	        raise RuntimeError("All MCMC samples failed decomposition")
   510	
   511	    print(f"  Decomposed {acc.n}/{len(indices)} MCMC samples successfully")
   512	    if dropped:
   513	        logger.warning("decompose_model_hmc dropped %d of %d draws: %s",
   514	                       len(dropped), len(indices), [d for d, _ in dropped][:10])
   515	
   516	    components, full, group_results = acc.finalize()
   517	    result = _assemble(x_test, x_train, y_train, components, full, group_results,
   518	                       last_noise, len(indices), acc.n)
   519	    result.dropped = dropped
   520	    return result

==================== SOURCE bistar_gp/decompose.py (line-numbered) ====================
     1	"""
     2	Additive kernel decomposition for Gaussian Processes.
     3	
     4	Implements Eq. 5 from Chandramouli & Shiffrin:
     5	Given a GP with sum kernel k_sum = k_1 + k_2 + ... + k_n,
     6	decompose posterior predictions into individual component GPs.
     7	
     8	Pure PyTorch — no GPyTorch dependency. This is the mathematical core.
     9	"""
    10	
    11	import numpy as np
    12	import torch
    13	from typing import List, Tuple, Optional
    14	
    15	
    16	def compute_cholesky(
    17	    K_sum_XX: torch.Tensor,
    18	    noise_var: float,
    19	    jitter: float = 1e-6,
    20	) -> torch.Tensor:
    21	    """
    22	    Compute Cholesky factor of (K_sum(X,X) + sigma_y^2 I).
    23	    Shared across all component decompositions.
    24	    Progressive jitter fallback on failure.
    25	    """
    26	    n = K_sum_XX.shape[0]
    27	    A = K_sum_XX + (noise_var + jitter) * torch.eye(n, dtype=K_sum_XX.dtype, device=K_sum_XX.device)
    28	    try:
    29	        return torch.linalg.cholesky(A)
    30	    except RuntimeError:
    31	        for extra in [1e-5, 1e-4, 1e-3, 1e-2]:
    32	            try:
    33	                return torch.linalg.cholesky(
    34	                    A + extra * torch.eye(n, dtype=A.dtype, device=A.device)
    35	                )
    36	            except RuntimeError:
    37	                continue
    38	        raise RuntimeError("Cholesky failed even with large jitter. Check hyperparameters.")
    39	
    40	
    41	def decompose_component(
    42	    K_i_XstarX: torch.Tensor,
    43	    K_i_XstarXstar: torch.Tensor,
    44	    K_i_XXstar: torch.Tensor,
    45	    L: torch.Tensor,
    46	    y: torch.Tensor,
    47	    mean: Optional[torch.Tensor] = None,
    48	) -> Tuple[torch.Tensor, torch.Tensor]:
    49	    """
    50	    Posterior for component i of an additive kernel (Eq. 5).
    51	
    52	    f_i(x*) | X, Y ~ GP(
    53	        k_i(x*, X) (K_sum + sigma_y^2 I)^{-1} y,
    54	        k_i(x*, x*) - k_i(x*, X) (K_sum + sigma_y^2 I)^{-1} k_i(X, x*)
    55	    )
    56	
    57	    Args:
    58	        K_i_XstarX:     k_i(X*, X), shape (n_test, n_train)
    59	        K_i_XstarXstar: k_i(X*, X*), shape (n_test, n_test)
    60	        K_i_XXstar:     k_i(X, X*), shape (n_train, n_test)
    61	        L:              Cholesky of (K_sum(X,X) + sigma_y^2 I)
    62	        y:              observed data, shape (n_train,)
    63	        mean:           optional mean at training points
    64	
    65	    Returns:
    66	        (mean_i, cov_i)
    67	    """
    68	    y_centered = (y - mean) if mean is not None else y
    69	
    70	    alpha = torch.cholesky_solve(y_centered.unsqueeze(-1), L).squeeze(-1)
    71	    V = torch.linalg.solve_triangular(L, K_i_XXstar, upper=False)
    72	
    73	    mean_i = K_i_XstarX @ alpha
    74	    cov_i = K_i_XstarXstar - V.T @ V
    75	
    76	    return mean_i, cov_i
    77	
    78	
    79	def decompose_additive_gp(
    80	    component_kernels_XX: List[torch.Tensor],
    81	    component_kernels_XstarX: List[torch.Tensor],
    82	    component_kernels_XstarXstar: List[torch.Tensor],
    83	    component_kernels_XXstar: List[torch.Tensor],
    84	    noise_var: float,
    85	    y: torch.Tensor,
    86	    jitter: float = 1e-6,
    87	    mean: Optional[torch.Tensor] = None,
    88	) -> List[Tuple[torch.Tensor, torch.Tensor]]:
    89	    """
    90	    Full additive decomposition: return posterior (mean, cov) for each component.
    91	    Single Cholesky, shared across all components.
    92	    """
    93	    K_sum_XX = sum(component_kernels_XX)
    94	    L = compute_cholesky(K_sum_XX, noise_var, jitter)
    95	
    96	    return [
    97	        decompose_component(KxsX, KxsXs, KXxs, L, y, mean)
    98	        for KxsX, KxsXs, KXxs in zip(
    99	            component_kernels_XstarX,
   100	            component_kernels_XstarXstar,
   101	            component_kernels_XXstar,
   102	        )
   103	    ]
   104	
   105	
   106	def sample_from_component(
   107	    mean_i: torch.Tensor,
   108	    cov_i: torch.Tensor,
   109	    n_samples: int = 25,
   110	    jitter: float = 1e-6,
   111	) -> torch.Tensor:
   112	    """Draw function samples from a component posterior. Shape: (n_samples, n_test)."""
   113	    n = cov_i.shape[0]
   114	    cov_j = cov_i + jitter * torch.eye(n, dtype=cov_i.dtype, device=cov_i.device)
   115	    try:
   116	        L = torch.linalg.cholesky(cov_j)
   117	    except RuntimeError:
   118	        diag = torch.clamp(torch.diag(cov_i), min=1e-8)
   119	        L = torch.diag(torch.sqrt(diag))
   120	
   121	    z = torch.randn(n_samples, n, dtype=mean_i.dtype, device=mean_i.device)
   122	    return mean_i.unsqueeze(0) + z @ L.T
   123	
   124	
   125	def mixture_central_interval(mean_draws, var_draws, mass=0.95, n_iter=100):
   126	    """Exact central interval of an equally weighted Gaussian mixture.
   127	
   128	    ``mean_draws`` and ``var_draws`` have shape (n_draws, n_points); the
   129	    return is (lo, hi), each of shape (n_points,). Quantiles are obtained by
   130	    bisecting the mixture CDF, so the interval is the mixture's own central
   131	    ``mass`` interval rather than a Gaussian approximation to it (ported from
   132	    experiments/toy_debias_demo.py in the 2026-09 review fix pass; the
   133	    reference implementation there is unchanged).
   134	    """
   135	    from scipy.special import ndtr
   136	
   137	    mean_draws = np.asarray(mean_draws, dtype=float)
   138	    var_draws = np.asarray(var_draws, dtype=float)
   139	    if mean_draws.ndim == 1:
   140	        mean_draws = mean_draws[None, :]
   141	        var_draws = var_draws[None, :]
   142	    if mean_draws.shape != var_draws.shape:
   143	        raise ValueError("mean_draws and var_draws must have the same shape")
   144	    if not (0.0 < mass < 1.0):
   145	        raise ValueError("mass must lie strictly between 0 and 1")
   146	    sd = np.sqrt(np.clip(var_draws, 1e-24, None))
   147	    tail = (1.0 - mass) / 2.0
   148	
   149	    def quantile(p):
   150	        lo = (mean_draws - 12.0 * sd).min(axis=0)
   151	        hi = (mean_draws + 12.0 * sd).max(axis=0)
   152	        for _ in range(n_iter):
   153	            mid = 0.5 * (lo + hi)
   154	            cdf = ndtr((mid[None, :] - mean_draws) / sd).mean(axis=0)
   155	            below = cdf < p
   156	            lo = np.where(below, mid, lo)
   157	            hi = np.where(below, hi, mid)
   158	        return 0.5 * (lo + hi)
   159	
   160	    return quantile(tail), quantile(1.0 - tail)

==================== SOURCE bistar_gp/metrics_v2.py (line-numbered) ====================
     1	"""
     2	metrics_v2.py — Calibrated divergence metrics for BMS*
     3	
     4	Addresses the variance-ratio trap: standard KL penalizes correct-but-confident
     5	models (small σ²_θ) when comparing against GP predictives (large σ²_ψ that
     6	includes hyperparameter uncertainty). Wrong models with inflated noise
     7	accidentally "match" the GP's width and get lower divergence.
     8	
     9	Three families of fixes, each isolating a different aspect of the comparison:
    10	
    11	  Group A: Variance-Calibrated — replace θ's variance with ψ's before
    12	           computing the divergence. Forces comparison onto mean accuracy,
    13	           with GP uncertainty as natural weighting.
    14	
    15	  Group B: Mean-Only — set all variances to 1. Pure mean comparison
    16	           inheriting the geometric properties of the parent divergence
    17	           (bounded for Hellinger, information-theoretic for KL).
    18	
    19	  Group C: GP-Anchored — evaluate θ's mean under ψ's distribution.
    20	           "How probable is θ's prediction under the GP posterior?"
    21	           Naturally weights by GP uncertainty.
    22	
    23	All metrics follow the standard signature:
    24	    f(mu_psi, cov_psi, mu_theta, cov_theta) -> float
    25	
    26	Import this module to register the new metrics into bms_star.METRICS.
    27	"""
    28	
    29	import numpy as np
    30	from typing import Dict, List, Optional, Tuple
    31	
    32	# We'll register into the existing METRICS dict
    33	from bistar_gp.bms_star import METRICS, _extract_marginals, GPPosteriorSample
    34	
    35	
    36	# ═══════════════════════════════════════════════════════════════════
    37	# Group A: Variance-Calibrated Metrics
    38	#
    39	# Idea: Replace σ²_θ with σ²_ψ at each point before computing divergence.
    40	# This removes the "width matching" incentive entirely.
    41	# ═══════════════════════════════════════════════════════════════════
    42	
    43	def pw_kl_vcal(mu_psi, cov_psi, mu_theta, cov_theta):
    44	    """
    45	    Variance-calibrated pointwise KL(ψ || θ_cal).
    46	
    47	    Replace θ's variance with ψ's variance at each location.
    48	    KL(N(μ_ψ, σ²_ψ) || N(μ_θ, σ²_ψ)) = (μ_θ - μ_ψ)² / (2σ²_ψ)
    49	
    50	    Reduces to GP-uncertainty-weighted MSE. Uncertain GP regions
    51	    contribute less — exactly the right behavior.
    52	    """
    53	    mu_p, var_p = _extract_marginals(mu_psi, cov_psi)
    54	    mu_q, _     = _extract_marginals(mu_theta, cov_theta)
    55	    return np.mean(0.5 * (mu_q - mu_p)**2 / var_p)
    56	
    57	
    58	def pw_hellinger_vcal(mu_psi, cov_psi, mu_theta, cov_theta):
    59	    """
    60	    Variance-calibrated pointwise Hellinger.
    61	
    62	    With σ²_θ = σ²_ψ at each point the Bhattacharyya distance of two
    63	    equal-variance Gaussians is
    64	      D_B = (μ_ψ - μ_θ)² / (8σ²_ψ)
    65	      H²  = 1 - exp(-D_B)
    66	    (the pre-2026-09 code and docstring used 4σ², twice the exponent; the
    67	    base pw_hellinger and the joint hellinger_distance were always correct).
    68	
    69	    Bounded in [0, 1], GP-uncertainty-weighted, saturates for large errors.
    70	    """
    71	    mu_p, var_p = _extract_marginals(mu_psi, cov_psi)
    72	    mu_q, _     = _extract_marginals(mu_theta, cov_theta)
    73	    db = (mu_p - mu_q)**2 / (8.0 * var_p)
    74	    return np.mean(1.0 - np.exp(-db))
    75	
    76	
    77	def pw_kl_sym_vcal(mu_psi, cov_psi, mu_theta, cov_theta):
    78	    """
    79	    Variance-calibrated symmetric KL.
    80	
    81	    With matched variances, forward and backward KL are identical:
    82	      KL(ψ||θ_cal) = KL(θ_cal||ψ) = (μ_θ - μ_ψ)² / (2σ²_ψ)
    83	
    84	    So symmetric = forward = backward. Included for completeness
    85	    and to verify this symmetry in practice.
    86	    """
    87	    # Identical to pw_kl_vcal when variances match
    88	    return pw_kl_vcal(mu_psi, cov_psi, mu_theta, cov_theta)
    89	
    90	
    91	# ═══════════════════════════════════════════════════════════════════
    92	# Group B: Mean-Only Metrics
    93	#
    94	# Idea: Set all variances to 1 (or any constant). Pure mean comparison
    95	# with the divergence's geometric properties preserved.
    96	# ═══════════════════════════════════════════════════════════════════
    97	
    98	def pw_hellinger_mean(mu_psi, cov_psi, mu_theta, cov_theta):
    99	    """
   100	    Mean-only pointwise Hellinger.
   101	
   102	    Set σ²_ψ = σ²_θ = 1 at every point:
   103	      D_B = (μ_ψ - μ_θ)² / 8
   104	      H²  = 1 - exp(-(μ_ψ - μ_θ)² / 8)
   105	    (the pre-2026-09 code and docstring used 4, twice the exponent).
   106	
   107	    Bounded [0, 1], symmetric. Large mean errors saturate at 1,
   108	    so outlier GP samples can't dominate. No variance information used.
   109	    """
   110	    mu_p = mu_psi if isinstance(mu_psi, np.ndarray) else np.array(mu_psi)
   111	    mu_q = mu_theta if isinstance(mu_theta, np.ndarray) else np.array(mu_theta)
   112	    db = (mu_p - mu_q)**2 / 8.0
   113	    return np.mean(1.0 - np.exp(-db))
   114	
   115	
   116	def pw_kl_mean(mu_psi, cov_psi, mu_theta, cov_theta):
   117	    """
   118	    Mean-only pointwise KL.
   119	
   120	    Set σ²_ψ = σ²_θ = 1:
   121	      KL = (μ_θ - μ_ψ)² / 2
   122	
   123	    Equivalent to MSE/2. Included to show that MSE *is* KL
   124	    when variance is removed from the picture.
   125	    """
   126	    mu_p = mu_psi if isinstance(mu_psi, np.ndarray) else np.array(mu_psi)
   127	    mu_q = mu_theta if isinstance(mu_theta, np.ndarray) else np.array(mu_theta)
   128	    return np.mean(0.5 * (mu_q - mu_p)**2)
   129	
   130	
   131	# ═══════════════════════════════════════════════════════════════════
   132	# Group C: GP-Anchored Metrics
   133	#
   134	# Idea: Score θ's prediction under ψ's distribution.
   135	# "How likely is θ's mean under the GP posterior at each point?"
   136	# ═══════════════════════════════════════════════════════════════════
   137	
   138	def pw_nll_gp(mu_psi, cov_psi, mu_theta, cov_theta):
   139	    """
   140	    GP-anchored NLL: negative log-likelihood of θ's mean under ψ's marginals.
   141	
   142	    -log N(μ_θ | μ_ψ, σ²_ψ) = 0.5*ln(2π*σ²_ψ) + 0.5*(μ_θ - μ_ψ)²/σ²_ψ
   143	
   144	    The constant 0.5*ln(2πσ²_ψ) is the same for all candidates (it depends
   145	    only on the GP sample), so for ranking it's equivalent to pw_kl_vcal.
   146	    But for absolute G values and τ sensitivity the constant matters.
   147	
   148	    Contrast with pw_nll which evaluates ψ's mean under θ's distribution —
   149	    that penalizes θ for being narrow.
   150	    """
   151	    mu_p, var_p = _extract_marginals(mu_psi, cov_psi)
   152	    mu_q, _     = _extract_marginals(mu_theta, cov_theta)
   153	    return np.mean(0.5 * np.log(2 * np.pi * var_p) + 0.5 * (mu_q - mu_p)**2 / var_p)
   154	
   155	
   156	def pw_nmse(mu_psi, cov_psi, mu_theta, cov_theta):
   157	    """
   158	    Normalized MSE: mean squared error weighted by GP uncertainty.
   159	
   160	    avg (μ_θ - μ_ψ)² / σ²_ψ
   161	
   162	    = 2 * pw_kl_vcal (exactly).
   163	
   164	    Included as a named metric because "normalized MSE" is a more
   165	    intuitive description than "variance-calibrated KL" for some audiences.
   166	    The factor of 2 doesn't affect ranking but affects τ sensitivity.
   167	    """
   168	    mu_p, var_p = _extract_marginals(mu_psi, cov_psi)
   169	    mu_q, _     = _extract_marginals(mu_theta, cov_theta)
   170	    return np.mean((mu_q - mu_p)**2 / var_p)
   171	
   172	
   173	# ═══════════════════════════════════════════════════════════════════
   174	# Registration
   175	# ═══════════════════════════════════════════════════════════════════
   176	
   177	METRICS_V2 = {
   178	    # Group A: Variance-Calibrated
   179	    "pw_kl_vcal":         pw_kl_vcal,
   180	    "pw_hellinger_vcal":  pw_hellinger_vcal,
   181	    "pw_kl_sym_vcal":     pw_kl_sym_vcal,
   182	
   183	    # Group B: Mean-Only
   184	    "pw_hellinger_mean":  pw_hellinger_mean,
   185	    "pw_kl_mean":         pw_kl_mean,
   186	
   187	    # Group C: GP-Anchored
   188	    "pw_nll_gp":          pw_nll_gp,
   189	    "pw_nmse":            pw_nmse,
   190	}
   191	
   192	# Register into the main METRICS dict
   193	METRICS.update(METRICS_V2)
   194	
   195	
   196	# ═══════════════════════════════════════════════════════════════════
   197	# Diagnostics
   198	# ═══════════════════════════════════════════════════════════════════
   199	
   200	def diagnose_G_matrix(G_matrix: np.ndarray,
   201	                      instance_names: List[str],
   202	                      metric_name: str = "") -> Dict:
   203	    """
   204	    Diagnostic summary of a G matrix.
   205	
   206	    Reports mean, median, std, min, max per candidate, plus the
   207	    inter-candidate spread (how much the metric differentiates models).
   208	
   209	    Returns a dict for programmatic use; also prints a readable table.
   210	    """
   211	    n_psi, n_theta = G_matrix.shape
   212	
   213	    stats = {}
   214	    print(f"\n  G-matrix diagnostics: {metric_name}")
   215	    print(f"  {'─' * 70}")
   216	    print(f"  {'Model':<15} {'Mean':>10} {'Median':>10} {'Std':>10} {'Min':>10} {'Max':>10}")
   217	    print(f"  {'─' * 70}")
   218	
   219	    means = []
   220	    for j, name in enumerate(instance_names):
   221	        col = G_matrix[:, j]
   222	        s = {
   223	            "mean": np.mean(col),
   224	            "median": np.median(col),
   225	            "std": np.std(col),
   226	            "min": np.min(col),
   227	            "max": np.max(col),
   228	        }
   229	        stats[name] = s
   230	        means.append(s["mean"])
   231	        print(f"  {name:<15} {s['mean']:>10.4f} {s['median']:>10.4f} "
   232	              f"{s['std']:>10.4f} {s['min']:>10.4f} {s['max']:>10.4f}")
   233	
   234	    # Inter-candidate spread: how distinguishable are the models?
   235	    means = np.array(means)
   236	    spread = means.max() - means.min()
   237	    cv = np.std(means) / np.mean(means) if np.mean(means) > 0 else 0.0
   238	
   239	    print(f"  {'─' * 70}")
   240	    print(f"  Spread (max-min of means): {spread:.4f}")
   241	    print(f"  CV of means:               {cv:.4f}")
   242	    print(f"  Best candidate (lowest G): {instance_names[np.argmin(means)]}")
   243	    print()
   244	
   245	    stats["_spread"] = spread
   246	    stats["_cv"] = cv
   247	    stats["_best"] = instance_names[np.argmin(means)]
   248	
   249	    return stats
   250	
   251	
   252	def diagnose_all_metrics(gp_samples: list,
   253	                         candidate_results: list,
   254	                         metric_names: Optional[List[str]] = None) -> Dict[str, Dict]:
   255	    """
   256	    Run diagnostics across all specified metrics.
   257	
   258	    Computes G matrix for each metric, prints per-candidate stats,
   259	    and returns a summary dict.
   260	
   261	    Args:
   262	        gp_samples: list of GPPosteriorSample
   263	        candidate_results: list of CandidateResult
   264	        metric_names: which metrics to diagnose (default: all registered)
   265	
   266	    Returns:
   267	        diagnostics[metric_name] = stats dict from diagnose_G_matrix
   268	    """
   269	    from bistar_gp.bms_star import compute_G_matrix
   270	
   271	    if metric_names is None:
   272	        metric_names = list(METRICS.keys())
   273	
   274	    instance_names = [cr.name for cr in candidate_results]
   275	    all_stats = {}
   276	
   277	    for metric_name in metric_names:
   278	        G = compute_G_matrix(gp_samples, candidate_results, metric_name)
   279	        stats = diagnose_G_matrix(G, instance_names, metric_name)
   280	        all_stats[metric_name] = stats
   281	
   282	    # Summary comparison table
   283	    print(f"\n  {'═' * 75}")
   284	    print(f"  SUMMARY: Which candidate wins (lowest mean G) per metric?")
   285	    print(f"  {'─' * 75}")
   286	    print(f"  {'Metric':<22} {'Best':<15} {'Spread':>10} {'CV':>10}")
   287	    print(f"  {'─' * 75}")
   288	
   289	    for m in metric_names:
   290	        s = all_stats[m]
   291	        print(f"  {m:<22} {s['_best']:<15} {s['_spread']:>10.4f} {s['_cv']:>10.4f}")
   292	    print()
   293	
   294	    return all_stats
   295	
   296	
   297	def plot_G_diagnostic_comparison(all_stats: Dict[str, Dict],
   298	                                 instance_names: List[str],
   299	                                 metric_groups: Optional[Dict[str, List[str]]] = None):
   300	    """
   301	    Bar chart comparing mean G per candidate, grouped by metric family.
   302	
   303	    Args:
   304	        all_stats: output from diagnose_all_metrics
   305	        instance_names: candidate model names
   306	        metric_groups: optional grouping, e.g.
   307	            {"Original PW": ["pw_kl_forward", ...], "Calibrated": ["pw_kl_vcal", ...]}
   308	            If None, auto-groups by prefix.
   309	    """
   310	    import matplotlib.pyplot as plt
   311	
   312	    if metric_groups is None:
   313	        # Auto-group: original vs v2
   314	        original = [m for m in all_stats if m in [
   315	            "pw_kl_forward", "pw_kl_backward", "pw_kl_symmetric",
   316	            "pw_hellinger", "pw_mse", "pw_nll",
   317	            "kl_forward", "kl_backward", "kl_symmetric", "hellinger",
   318	        ]]
   319	        v2 = [m for m in all_stats if m in METRICS_V2]
   320	        metric_groups = {}
   321	        if original:
   322	            metric_groups["Original"] = original
   323	        if v2:
   324	            metric_groups["Calibrated (v2)"] = v2
   325	
   326	    n_groups = len(metric_groups)
   327	    fig, axes = plt.subplots(1, n_groups, figsize=(7 * n_groups, 5))
   328	    if n_groups == 1:
   329	        axes = [axes]
   330	
   331	    model_colors = ['#e74c3c', '#3498db', '#2ecc71', '#9b59b6']
   332	
   333	    for ax, (group_name, metrics) in zip(axes, metric_groups.items()):
   334	        n_metrics = len(metrics)
   335	        n_models = len(instance_names)
   336	        x = np.arange(n_metrics)
   337	        width = 0.8 / n_models
   338	
   339	        for m_idx, model_name in enumerate(instance_names):
   340	            vals = []
   341	            for metric_name in metrics:
   342	                if metric_name in all_stats and model_name in all_stats[metric_name]:
   343	                    vals.append(all_stats[metric_name][model_name]["mean"])
   344	                else:
   345	                    vals.append(0)
   346	            offset = (m_idx - n_models / 2 + 0.5) * width
   347	            ax.bar(x + offset, vals, width, label=model_name,
   348	                   color=model_colors[m_idx % len(model_colors)])
   349	
   350	        ax.set_xticks(x)
   351	        ax.set_xticklabels(metrics, rotation=45, ha='right', fontsize=8)
   352	        ax.set_ylabel("Mean G(ψ, θ)")
   353	        ax.set_title(group_name, fontsize=12, fontweight='bold')
   354	        ax.legend(fontsize=8)
   355	        ax.grid(True, alpha=0.2, axis='y')
   356	
   357	    fig.suptitle("Mean Divergence per Candidate — Original vs Calibrated", fontsize=14)
   358	    fig.tight_layout()
   359	    return fig
   360	
   361	
   362	def plot_v2_tau_sensitivity(gp_samples: list,
   363	                            candidate_results: list,
   364	                            taus: np.ndarray = None,
   365	                            figsize=None):
   366	    """
   367	    τ sensitivity curves for the v2 metrics only.
   368	
   369	    Mirrors plot_bms_star_results but restricted to the new metrics,
   370	    so you can see them side-by-side with the originals.
   371	    """
   372	    import matplotlib.pyplot as plt
   373	    from bistar_gp.bms_star import compute_G_matrix, soft_transfer
   374	
   375	    if taus is None:
   376	        taus = np.logspace(-1, 2, 30)
   377	
   378	    v2_names = list(METRICS_V2.keys())
   379	    instance_names = [cr.name for cr in candidate_results]
   380	    n_metrics = len(v2_names)
   381	    ncols = min(4, n_metrics)
   382	    nrows = (n_metrics + ncols - 1) // ncols
   383	    if figsize is None:
   384	        figsize = (4.5 * ncols, 3.5 * nrows)
   385	
   386	    fig, axes = plt.subplots(nrows, ncols, figsize=figsize)
   387	    axes = np.atleast_2d(axes).flatten()
   388	
   389	    colors = ['#e74c3c', '#3498db', '#2ecc71', '#9b59b6']
   390	
   391	    for ax_idx, metric_name in enumerate(v2_names):
   392	        ax = axes[ax_idx]
   393	        print(f"  Computing G matrix: {metric_name}...")
   394	        G = compute_G_matrix(gp_samples, candidate_results, metric_name)
   395	
   396	        posteriors = np.zeros((len(taus), len(instance_names)))
   397	        for t_idx, tau in enumerate(taus):
   398	            bms = soft_transfer(G, tau, instance_names)
   399	            posteriors[t_idx] = bms.instance_posteriors
   400	
   401	        for m_idx, name in enumerate(instance_names):
   402	            ax.plot(taus, posteriors[:, m_idx], color=colors[m_idx],
   403	                    linewidth=2, label=name)
   404	
   405	        ax.set_xscale('log')
   406	        ax.set_xlabel('τ', fontsize=9)
   407	        ax.set_ylabel('Posterior', fontsize=9)
   408	        ax.set_title(metric_name, fontsize=10)
   409	        ax.set_ylim(0, 1)
   410	        ax.legend(fontsize=7)
   411	        ax.grid(True, alpha=0.3)
   412	
   413	    for ax_idx in range(n_metrics, len(axes)):
   414	        axes[ax_idx].set_visible(False)
   415	
   416	    fig.suptitle("V2 Calibrated Metrics — τ Sensitivity", fontsize=14)
   417	    fig.tight_layout()
   418	    return fig

==================== SOURCE bistar_gp/config.py (line-numbered) ====================
     1	"""
     2	Configuration for BMS* experiments.
     3	
     4	Defines:
     5	- Named GP hyperprior configurations for sensitivity analysis
     6	- Sample caching paths and behavior
     7	- Experiment parameters (n_points, n_samples, τ range, etc.)
     8	"""
     9	
    10	import math
    11	import os
    12	from dataclasses import dataclass, field
    13	from typing import Dict, List, Optional, Tuple
    14	
    15	# ── Paths ─────────────────────────────────────────────────────────
    16	
    17	CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
    18	RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
    19	
    20	# ── Metric roles (W1) and withdrawn caches (M2bR banner) ───────────
    21	# 2026-09 review FIX-7. The manuscript's primary metric and the appendix-only
    22	# stress metric; generic APIs keep their defaults, manuscript-facing code
    23	# and run_bms_star's implicit path refer to these names.
    24	PRIMARY_METRIC = "pw_kl_vcal"
    25	APPENDIX_METRICS = ("kl_forward",)
    26	
    27	# Caches the M2bR banner withdrew: `informative`-config HMC draws produced by
    28	# the pre-D6/D22 sampler. load_hmc_samples refuses them unless the caller
    29	# passes allow_withdrawn=True (and then warns). Entries ending in "/" are
    30	# directory prefixes; the rest are file paths relative to the repository.
    31	WITHDRAWN_CACHES = (
    32	    "runs/fit_method_metric_comparison/samples_hmc.npz",
    33	    "runs/toy_tau_metric_comparison/",
    34	)
    35	
    36	
    37	def is_withdrawn_cache(path) -> bool:
    38	    """True when `path` names, or lies under, a withdrawn cache entry."""
    39	    norm = os.path.normpath(os.path.abspath(str(path))).replace(os.sep, "/")
    40	    for entry in WITHDRAWN_CACHES:
    41	        if entry.endswith("/"):
    42	            if "/" + entry.rstrip("/") + "/" in norm + "/":
    43	                return True
    44	        elif norm.endswith("/" + entry) or norm == entry:
    45	            return True
    46	    return False
    47	
    48	
    49	# ── Prior Configurations ──────────────────────────────────────────
    50	
    51	@dataclass
    52	class PriorConfig:
    53	    """
    54	    Named hyperprior configuration for the GP.
    55	
    56	    Each config specifies the prior family and parameters for:
    57	    - SE kernel: lengthscale, outputscale
    58	    - Linear kernel: variance
    59	    - Noise variance
    60	    """
    61	    name: str
    62	    description: str
    63	
    64	    # SE lengthscale prior: (family, param1, param2)
    65	    se_lengthscale_prior: Tuple[str, float, float]
    66	    se_lengthscale_bounds: Tuple[float, float]
    67	
    68	    # SE outputscale prior
    69	    se_outputscale_prior: Tuple[str, float, float]
    70	    se_outputscale_bounds: Tuple[float, float]
    71	
    72	    # Linear kernel variance prior
    73	    linear_variance_prior: Tuple[str, float, float]
    74	    linear_variance_bounds: Tuple[float, float]
    75	
    76	    # Noise prior
    77	    noise_prior: Tuple[str, float, float]
    78	    noise_bounds: Tuple[float, float]
    79	
    80	
    81	# Named prior configurations for sensitivity analysis
    82	PRIOR_CONFIGS: Dict[str, PriorConfig] = {
    83	
    84	    "informative": PriorConfig(
    85	        name="informative",
    86	        description="Moderate Gamma priors — current default. Concentrates mass around reasonable values.",
    87	        se_lengthscale_prior=("gamma", 6.0, 0.85),
    88	        se_lengthscale_bounds=(0.5, 30.0),
    89	        se_outputscale_prior=("gamma", 6.0, 0.85),
    90	        se_outputscale_bounds=(0.1, 20.0),
    91	        linear_variance_prior=("gamma", 6.0, 0.85),
    92	        linear_variance_bounds=(0.01, 20.0),
    93	        noise_prior=("gamma", 1.75, 1.0),
    94	        noise_bounds=(1e-4, 10.0),
    95	    ),
    96	
    97	    "vague": PriorConfig(
    98	        name="vague",
    99	        description="Broad LogNormal priors — lets data dominate. Tests BMS* under minimal prior info.",
   100	        se_lengthscale_prior=("lognormal", 0.0, 2.0),
   101	        se_lengthscale_bounds=(0.1, 100.0),
   102	        se_outputscale_prior=("lognormal", 0.0, 2.0),
   103	        se_outputscale_bounds=(0.01, 100.0),
   104	        linear_variance_prior=("lognormal", 0.0, 2.0),
   105	        linear_variance_bounds=(0.001, 100.0),
   106	        noise_prior=("lognormal", -1.0, 2.0),
   107	        noise_bounds=(1e-5, 50.0),
   108	    ),
   109	
   110	    "misspecified_tight": PriorConfig(
   111	        name="misspecified_tight",
   112	        description="Tight Gamma concentrated away from truth. Prior actively fights the data.",
   113	        se_lengthscale_prior=("gamma", 20.0, 4.0),   # concentrates near 5, true is ~1-2
   114	        se_lengthscale_bounds=(1.0, 50.0),
   115	        se_outputscale_prior=("gamma", 20.0, 4.0),
   116	        se_outputscale_bounds=(0.5, 50.0),
   117	        linear_variance_prior=("gamma", 20.0, 4.0),
   118	        linear_variance_bounds=(0.1, 50.0),
   119	        noise_prior=("gamma", 5.0, 5.0),              # concentrates near 1, true is ~0.09
   120	        noise_bounds=(1e-3, 20.0),
   121	    ),
   122	
   123	    "low_noise": PriorConfig(
   124	        name="low_noise",
   125	        description="Informative kernel priors but very small noise prior — overconfident GP.",
   126	        se_lengthscale_prior=("gamma", 6.0, 0.85),
   127	        se_lengthscale_bounds=(0.5, 30.0),
   128	        se_outputscale_prior=("gamma", 6.0, 0.85),
   129	        se_outputscale_bounds=(0.1, 20.0),
   130	        linear_variance_prior=("gamma", 6.0, 0.85),
   131	        linear_variance_bounds=(0.01, 20.0),
   132	        noise_prior=("gamma", 2.0, 20.0),             # concentrates near 0.1
   133	        noise_bounds=(1e-5, 1.0),
   134	    ),
   135	
   136	    "high_noise": PriorConfig(
   137	        name="high_noise",
   138	        description="Informative kernel priors but large noise prior — underconfident GP.",
   139	        se_lengthscale_prior=("gamma", 6.0, 0.85),
   140	        se_lengthscale_bounds=(0.5, 30.0),
   141	        se_outputscale_prior=("gamma", 6.0, 0.85),
   142	        se_outputscale_bounds=(0.1, 20.0),
   143	        linear_variance_prior=("gamma", 6.0, 0.85),
   144	        linear_variance_bounds=(0.01, 20.0),
   145	        noise_prior=("gamma", 2.0, 0.5),              # concentrates near 4
   146	        noise_bounds=(0.1, 50.0),
   147	    ),
   148	
   149	    # Registry-only entry: NOT the package default and deliberately absent
   150	    # from ExperimentConfig.prior_configs (no default-sweep change, no
   151	    # cached-run invalidation). Parameters are byte-identical to the
   152	    # prior-sensitivity study's in-script `toy_elicited` config
   153	    # (experiments/prior_sensitivity_study.py, D18); the study's cache
   154	    # fingerprint covers exactly these four parameter tuples.
   155	    "toy_elicited_n20": PriorConfig(
   156	        name="toy_elicited_n20",
   157	        description=(
   158	            "Re-elicited from the N=20 thesis-toy observable statistics; "
   159	            "D18. LogNormal medians from data statistics only, no truth "
   160	            "values: lengthscale 4.5 (geometric middle of x-spacing 1.05 "
   161	            "and x-range 20, sigma 0.9), outputscale 1.5 (~var(y)/2), "
   162	            "linear variance 0.04 (~var(y)/(2*mean(x^2))), noise 0.3 "
   163	            "(~10% of var(y)). Scope: the N=20 thesis-toy instance "
   164	            "(generate_toy_data() defaults: N=20, noise 0.5, seed 42) "
   165	            "ONLY, per the 2026-07-09 scope-tightened ratification; not a "
   166	            "global prior replacement (bms_star_toy.py's N=50 sweep and "
   167	            "the bistar_viz data convention keep their own priors). "
   168	            "Data-elicited, empirical-Bayes-style: the medians use the "
   169	            "realized sample's summaries, so results under this prior are "
   170	            "posterior-mass-faithful conditional on the fixed prior, not "
   171	            "unqualified full-Bayes (D18 terminology correction, "
   172	            "2026-07-10)."
   173	        ),
   174	        se_lengthscale_prior=("lognormal", math.log(4.5), 0.9),
   175	        se_lengthscale_bounds=(0.1, 100.0),
   176	        se_outputscale_prior=("lognormal", math.log(1.5), 1.0),
   177	        se_outputscale_bounds=(0.01, 100.0),
   178	        linear_variance_prior=("lognormal", math.log(0.04), 1.5),
   179	        linear_variance_bounds=(1e-4, 10.0),
   180	        noise_prior=("lognormal", math.log(0.3), 1.0),
   181	        noise_bounds=(1e-4, 10.0),
   182	    ),
   183	}
   184	
   185	
   186	# ── Experiment Configuration ──────────────────────────────────────
   187	
   188	@dataclass
   189	class ExperimentConfig:
   190	    """Full experiment configuration."""
   191	
   192	    # Data
   193	    n_points: int = 50
   194	    noise_std: float = 0.3
   195	    bias_slope: float = 0.25
   196	    seed: int = 42
   197	    x_range: Tuple[float, float] = (-10.0, 10.0)
   198	
   199	    # Evaluation grid
   200	    n_eval: int = 60
   201	
   202	    # HMC
   203	    n_hmc_samples: int = 500
   204	    n_warmup: int = 200
   205	    n_posterior_samples: int = 200     # subsample from HMC for BMS*
   206	
   207	    # BMS*
   208	    tau_range: Tuple[float, float] = (-1, 2)  # log10 scale
   209	    n_taus: int = 30
   210	    # The primary metric is APPENDED (FIX-7) so positional uses of the legacy
   211	    # list (experiments/bms_star_toy.py slices metrics[:4]) keep their meaning.
   212	    metrics: List[str] = field(default_factory=lambda: [
   213	        "kl_forward", "kl_backward", "kl_symmetric", "hellinger",
   214	        "pw_kl_forward", "pw_kl_backward", "pw_kl_symmetric", "pw_hellinger",
   215	        "pw_mse", "pw_nll",
   216	        PRIMARY_METRIC,
   217	    ])
   218	
   219	    # Prior sensitivity
   220	    prior_configs: List[str] = field(default_factory=lambda: [
   221	        "informative", "vague", "misspecified_tight", "low_noise", "high_noise"
   222	    ])
   223	
   224	    # Caching
   225	    use_cache: bool = True            # load cached samples if available
   226	    save_cache: bool = True           # save new samples to cache
   227	    cache_dir: str = CACHE_DIR
   228	    force_rerun: bool = False         # ignore cache, rerun everything
   229	
   230	    def get_cache_path(self, prior_name: str) -> str:
   231	        """Path to cached HMC samples for a given prior config."""
   232	        os.makedirs(self.cache_dir, exist_ok=True)
   233	        return os.path.join(
   234	            self.cache_dir,
   235	            f"hmc_samples_{prior_name}_n{self.n_hmc_samples}_s{self.seed}.npz"
   236	        )
   237	
   238	    def cache_exists(self, prior_name: str) -> bool:
   239	        return os.path.exists(self.get_cache_path(prior_name))
   240	
   241	
   242	# ── Cache I/O ─────────────────────────────────────────────────────
   243	
   244	def save_hmc_samples(samples: Dict, path: str):
   245	    """Save HMC samples dict to .npz file."""
   246	    os.makedirs(os.path.dirname(path), exist_ok=True)
   247	    # numpy savez expects arrays
   248	    import numpy as np
   249	    np.savez(path, **{k: np.array(v) for k, v in samples.items()})
   250	    print(f"  Cached HMC samples → {path}")
   251	
   252	
   253	def load_hmc_samples(path: str, allow_withdrawn: bool = False) -> Dict:
   254	    """Load HMC samples from .npz file.
   255	
   256	    Refuses the caches the M2bR banner withdrew (WITHDRAWN_CACHES) unless
   257	    allow_withdrawn=True is passed explicitly, in which case it warns; a
   258	    figure or number built from them must be labelled as withdrawn material.
   259	    """
   260	    import warnings
   261	    import numpy as np
   262	    if is_withdrawn_cache(path):
   263	        msg = (f"{path} is a WITHDRAWN cache (M2bR banner: informative-config "
   264	               "HMC draws from the pre-D6/D22 sampler must never be cited); "
   265	               "pass allow_withdrawn=True only for explicitly labelled archival "
   266	               "reproduction")
   267	        if not allow_withdrawn:
   268	            raise RuntimeError(msg)
   269	        warnings.warn(msg, UserWarning, stacklevel=2)
   270	    data = np.load(path)
   271	    samples = {k: data[k] for k in data.files}
   272	    print(f"  Loaded cached HMC samples ← {path}")
   273	    return samples
   274	
   275	
   276	# ── Kernel Builder from Config ────────────────────────────────────
   277	
   278	def build_kernels_from_config(prior_config: PriorConfig):
   279	    """
   280	    Build GP kernel components with priors from a PriorConfig.
   281	    Returns (kernels, names) matching the interface of build_toy_kernels().
   282	    Uses Positive() constraints (not Interval) — Pyro HMC needs open bounds.
   283	    """
   284	    import gpytorch
   285	    from gpytorch.kernels import ScaleKernel, RBFKernel, LinearKernel
   286	    from gpytorch.constraints import Positive
   287	    from gpytorch.priors import GammaPrior, LogNormalPrior
   288	
   289	    def make_prior(family, p1, p2):
   290	        if family == "gamma":
   291	            return GammaPrior(p1, p2)
   292	        elif family == "lognormal":
   293	            return LogNormalPrior(p1, p2)
   294	        else:
   295	            raise ValueError(f"Unknown prior family: {family}")
   296	
   297	    se = ScaleKernel(
   298	        RBFKernel(
   299	            lengthscale_constraint=Positive(),
   300	            lengthscale_prior=make_prior(*prior_config.se_lengthscale_prior),
   301	        ),
   302	        outputscale_constraint=Positive(),
   303	        outputscale_prior=make_prior(*prior_config.se_outputscale_prior),
   304	    )
   305	    linear = LinearKernel(
   306	        variance_constraint=Positive(),
   307	        variance_prior=make_prior(*prior_config.linear_variance_prior),
   308	    )
   309	    return [se, linear], ["unbiased_se", "bias_linear"]
   310	
   311	
   312	def build_likelihood_from_config(prior_config: PriorConfig):
   313	    """Build likelihood with noise prior from config. Uses Positive() constraint."""
   314	    import gpytorch
   315	    from gpytorch.constraints import Positive
   316	    from gpytorch.priors import GammaPrior, LogNormalPrior
   317	
   318	    def make_prior(family, p1, p2):
   319	        if family == "gamma":
   320	            return GammaPrior(p1, p2)
   321	        elif family == "lognormal":
   322	            return LogNormalPrior(p1, p2)
   323	        else:
   324	            raise ValueError(f"Unknown prior family: {family}")
   325	
   326	    return gpytorch.likelihoods.GaussianLikelihood(
   327	        noise_constraint=Positive(),
   328	        noise_prior=make_prior(*prior_config.noise_prior),
   329	    )
   330	
   331	
   332	# ── Default config ────────────────────────────────────────────────
   333	
   334	DEFAULT_CONFIG = ExperimentConfig()

==================== SOURCE bistar_gp/induced_prior.py (line-numbered) ====================
     1	"""
     2	induced_prior.py — GP-Induced Priors on Parametric Model Parameters
     3	
     4	This is the core BI* mechanism:
     5	
     6	  GP kernel priors (qualitative beliefs about data patterns)
     7	    → GP posterior ψ (updated beliefs about data)
     8	      → Induced prior on model parameters φ
     9	        → Bayesian model selection with informed priors
    10	
    11	The key equation from Extending Bayesian Induction:
    12	
    13	  p(φ_j | ψ, M_j) ∝ exp(-G(ψ, θ_j(φ)) / τ) · p₀(φ_j)
    14	
    15	where:
    16	  - ψ = GP posterior (data distribution belief)
    17	  - θ_j(φ) = candidate model M_j's prediction given parameters φ
    18	  - G = divergence between GP and candidate
    19	  - τ = temperature (controls sharpness of transfer)
    20	  - p₀(φ) = reference prior on parameters (broad/uninformative)
    21	
    22	The GP prior choice (kernel structure + hyperpriors) determines ψ,
    23	which in turn determines p(φ | ψ). This is how qualitative beliefs
    24	about data patterns (periodicity, trends, smoothness) get transferred
    25	into quantitative priors on model parameters (amplitude, frequency, slope).
    26	
    27	Expected qualitative behavior:
    28	  - Informative GP prior → tight ψ → sharp induced prior near truth
    29	  - Vague GP prior → wide ψ → diffuse induced prior, less informative
    30	  - Misspecified GP prior → biased ψ → shifted induced prior, may mislead
    31	"""
    32	
    33	import logging
    34	
    35	import numpy as np
    36	from typing import List, Dict, Optional, Tuple, Callable
    37	from dataclasses import dataclass
    38	
    39	logger = logging.getLogger(__name__)
    40	
    41	from bistar_gp.bms_star import GPPosteriorSample, METRICS
    42	from bistar_gp.candidates import CandidateResult
    43	
    44	
    45	# ═══════════════════════════════════════════════════════════════════
    46	# Parameter Space Definitions
    47	# ═══════════════════════════════════════════════════════════════════
    48	
    49	@dataclass
    50	class ParameterSpec:
    51	    """Specification for one model parameter."""
    52	    name: str
    53	    bounds: Tuple[float, float]    # sampling range
    54	    true_value: Optional[float]     # ground truth (if known)
    55	    mle_value: Optional[float] = None
    56	
    57	
    58	@dataclass
    59	class ModelParameterSpace:
    60	    """Parameter space for a candidate model."""
    61	    model_name: str
    62	    param_specs: List[ParameterSpec]
    63	    predict_fn: Callable  # (x_eval, param_dict) → mean array
    64	    noise_param: str = "sigma"  # name of the noise parameter
    65	
    66	    @property
    67	    def param_names(self):
    68	        return [ps.name for ps in self.param_specs]
    69	
    70	    @property
    71	    def n_params(self):
    72	        return len(self.param_specs)
    73	
    74	    def sample_reference_prior(self, n_samples: int, seed: int = None) -> np.ndarray:
    75	        """
    76	        Sample from broad reference prior p₀(φ).
    77	        Uniform over bounds for each parameter.
    78	        Returns (n_samples, n_params).
    79	        """
    80	        rng = np.random.RandomState(seed)
    81	        samples = np.zeros((n_samples, self.n_params))
    82	        for j, ps in enumerate(self.param_specs):
    83	            samples[:, j] = rng.uniform(ps.bounds[0], ps.bounds[1], n_samples)
    84	        return samples
    85	
    86	
    87	def build_toy_parameter_spaces(true_params: Dict = None) -> Dict[str, ModelParameterSpace]:
    88	    """
    89	    Build parameter spaces for the four toy candidate models.
    90	
    91	    True data: y = sin(x) + 0.25x + noise(0.3)
    92	    """
    93	    if true_params is None:
    94	        true_params = {
    95	            "A": 1.0, "omega": 1.0, "phi": 0.0,
    96	            "slope": 0.25, "intercept": 0.0, "sigma": 0.3,
    97	        }
    98	
    99	    spaces = {}
   100	
   101	    # Linear: y = a*x + b + eps
   102	    spaces["Linear"] = ModelParameterSpace(
   103	        model_name="Linear",
   104	        param_specs=[
   105	            ParameterSpec("a", (-1.0, 1.0), true_value=0.25),
   106	            ParameterSpec("b", (-3.0, 3.0), true_value=0.0),
   107	            ParameterSpec("sigma", (0.05, 3.0), true_value=None),  # no "true" for wrong model
   108	        ],
   109	        predict_fn=lambda x, p: p["a"] * x + p["b"],
   110	    )
   111	
   112	    # Sinusoidal: y = A*sin(omega*x + phi) + eps
   113	    spaces["Sinusoidal"] = ModelParameterSpace(
   114	        model_name="Sinusoidal",
   115	        param_specs=[
   116	            ParameterSpec("A", (0.1, 3.0), true_value=1.0),
   117	            ParameterSpec("omega", (0.3, 3.0), true_value=1.0),
   118	            ParameterSpec("phi", (-np.pi, np.pi), true_value=0.0),
   119	            ParameterSpec("sigma", (0.05, 3.0), true_value=None),
   120	        ],
   121	        predict_fn=lambda x, p: p["A"] * np.sin(p["omega"] * x + p["phi"]),
   122	    )
   123	
   124	    # Sin+Linear: y = A*sin(omega*x + phi) + b*x + c + eps
   125	    spaces["Sin+Linear"] = ModelParameterSpace(
   126	        model_name="Sin+Linear",
   127	        param_specs=[
   128	            ParameterSpec("A", (0.1, 3.0), true_value=1.0),
   129	            ParameterSpec("omega", (0.3, 3.0), true_value=1.0),
   130	            ParameterSpec("phi", (-np.pi, np.pi), true_value=0.0),
   131	            ParameterSpec("b", (-1.0, 1.0), true_value=0.25),
   132	            ParameterSpec("c", (-3.0, 3.0), true_value=0.0),
   133	            ParameterSpec("sigma", (0.05, 3.0), true_value=None),
   134	        ],
   135	        predict_fn=lambda x, p: (p["A"] * np.sin(p["omega"] * x + p["phi"])
   136	                                  + p["b"] * x + p["c"]),
   137	    )
   138	
   139	    # Quadratic: y = a*x^2 + b*x + c + eps
   140	    spaces["Quadratic"] = ModelParameterSpace(
   141	        model_name="Quadratic",
   142	        param_specs=[
   143	            ParameterSpec("a", (-0.2, 0.2), true_value=None),
   144	            ParameterSpec("b", (-1.0, 1.0), true_value=None),
   145	            ParameterSpec("c", (-3.0, 3.0), true_value=None),
   146	            ParameterSpec("sigma", (0.05, 3.0), true_value=None),
   147	        ],
   148	        predict_fn=lambda x, p: p["a"] * x**2 + p["b"] * x + p["c"],
   149	    )
   150	
   151	    return spaces
   152	
   153	
   154	# ═══════════════════════════════════════════════════════════════════
   155	# GP-Induced Prior Computation
   156	# ═══════════════════════════════════════════════════════════════════
   157	
   158	@dataclass
   159	class InducedPriorResult:
   160	    """Result of computing the GP-induced prior over model parameters."""
   161	    model_name: str
   162	    prior_name: str          # which GP prior config
   163	    param_names: List[str]
   164	    param_samples: np.ndarray   # (n_samples, n_params) — reference prior draws
   165	    log_weights: np.ndarray     # (n_samples,) — log induced prior weight per sample
   166	    weights: np.ndarray         # (n_samples,) — normalized weights
   167	    G_per_sample: np.ndarray    # (n_samples,) — average G across GP samples
   168	    tau: float
   169	    effective_sample_size: float
   170	    mle_values: Optional[Dict[str, float]] = None
   171	    true_values: Optional[Dict[str, float]] = None
   172	
   173	
   174	def compute_induced_prior(
   175	    param_space: ModelParameterSpace,
   176	    gp_samples: List[GPPosteriorSample],
   177	    x_eval: np.ndarray,
   178	    log_mlls: Optional[np.ndarray] = None,
   179	    metric_name: str = "pw_kl_vcal",
   180	    tau: float = 1.0,
   181	    n_param_samples: int = 10000,
   182	    seed: int = 42,
   183	    weighting: str = "uniform",
   184	) -> InducedPriorResult:
   185	    """
   186	    Compute the GP-induced prior over model parameters.
   187	
   188	    For each parameter sample φ:
   189	      1. Generate candidate prediction θ(φ) at x_eval
   190	      2. Compute MLL-weighted average G across GP samples:
   191	         Ḡ(φ) = Σ_i w_i G(ψ_i, θ(φ)) / Σ_i w_i
   192	      3. Induced prior weight: exp(-Ḡ(φ) / τ)
   193	
   194	    weighting (2026-09 review FIX-6):
   195	      "uniform" (default): w_i = 1/N. This is the correct average for
   196	          POSTERIOR draws (fit_hmc output); the draws already carry the
   197	          likelihood, and multiplying by p(y|η_i) again would average under a
   198	          density proportional to p(η) p(y|η)^2.
   199	      "likelihood_tilted": w_i ∝ exp(log_mlls[i]); the self-normalized
   200	          importance weights that turn PRIOR draws into a posterior average.
   201	          Requires log_mlls. Never use with posterior draws.
   202	    The pre-fix code made the likelihood weighting mandatory and its legacy
   203	    callers fed it posterior draws.
   204	    """
   205	    metric_fn = METRICS[metric_name]
   206	    n_draws = len(gp_samples)
   207	
   208	    if weighting == "uniform":
   209	        if log_mlls is not None:
   210	            # A legacy positional call would otherwise run a different
   211	            # estimator with only a log line to say so (review F2).
   212	            raise ValueError(
   213	                "compute_induced_prior: log_mlls supplied under weighting='uniform'; "
   214	                "pass weighting='likelihood_tilted' for PRIOR draws or drop log_mlls "
   215	                "for posterior draws")
   216	        mll_weights = np.full(n_draws, 1.0 / n_draws)
   217	    elif weighting == "likelihood_tilted":
   218	        if log_mlls is None:
   219	            raise ValueError("weighting='likelihood_tilted' requires log_mlls")
   220	        log_mlls = np.asarray(log_mlls, dtype=float)
   221	        valid = np.isfinite(log_mlls)
   222	        if not valid.any():
   223	            raise ValueError("compute_induced_prior: no finite log marginal likelihood")
   224	        lw = log_mlls.copy()
   225	        lw[~valid] = -np.inf
   226	        lw -= lw[valid].max()
   227	        mll_weights = np.exp(lw)
   228	        mll_weights /= mll_weights.sum()
   229	    else:
   230	        raise ValueError(f"unknown weighting {weighting!r}; use 'uniform' or "
   231	                         "'likelihood_tilted'")
   232	
   233	    # Sample parameters from reference prior
   234	    param_samples = param_space.sample_reference_prior(n_param_samples, seed=seed)
   235	
   236	    # For each parameter sample, compute MLL-weighted G
   237	    G_per_sample = np.zeros(n_param_samples)
   238	
   239	    for s_idx in range(n_param_samples):
   240	        # Build parameter dict
   241	        param_dict = {ps.name: param_samples[s_idx, j]
   242	                      for j, ps in enumerate(param_space.param_specs)}
   243	
   244	        # Generate prediction
   245	        try:
   246	            mu_theta = param_space.predict_fn(x_eval, param_dict)
   247	        except Exception:
   248	            G_per_sample[s_idx] = np.inf
   249	            continue
   250	
   251	        sigma = param_dict.get(param_space.noise_param, 0.3)
   252	        sigma2 = sigma ** 2
   253	        n_eval = len(x_eval)
   254	        cov_theta = sigma2 * np.eye(n_eval)
   255	
   256	        # MLL-weighted average G across GP samples
   257	        g_vals = np.zeros(len(gp_samples))
   258	        for i, psi in enumerate(gp_samples):
   259	            try:
   260	                g_vals[i] = metric_fn(psi.mean, psi.cov, mu_theta, cov_theta)
   261	            except (np.linalg.LinAlgError, ValueError):
   262	                g_vals[i] = np.inf
   263	
   264	        # Replace a failed draw with a value strictly WORSE than every finite
   265	        # one. The old `10 * max(finite)` is the smallest value (the best
   266	        # score) whenever the metric is negative-valued (pw_nll_gp), the bug
   267	        # class compute_G_matrix already documents (2026-09 review FIX-5).
   268	        finite_mask = np.isfinite(g_vals)
   269	        if finite_mask.any():
   270	            max_finite = np.max(g_vals[finite_mask])
   271	            g_vals[~finite_mask] = max_finite + 10.0 * (abs(max_finite) + 1.0)
   272	        else:
   273	            g_vals[:] = 1e6
   274	
   275	        G_per_sample[s_idx] = np.sum(mll_weights * g_vals)
   276	
   277	    # Compute induced prior weights
   278	    log_weights = -G_per_sample / tau
   279	
   280	    # Numerical stability
   281	    finite = np.isfinite(log_weights)
   282	    if finite.any():
   283	        log_weights[~finite] = -np.inf
   284	        log_weights -= np.max(log_weights[finite])
   285	    else:
   286	        log_weights[:] = 0.0
   287	
   288	    weights = np.exp(log_weights)
   289	    total = weights.sum()
   290	    if total > 0:
   291	        weights /= total
   292	    else:
   293	        weights[:] = 1.0 / n_param_samples
   294	
   295	    # Effective sample size
   296	    ess = 1.0 / np.sum(weights ** 2) if np.sum(weights ** 2) > 0 else 0
   297	
   298	    # Collect true and MLE values
   299	    true_vals = {ps.name: ps.true_value for ps in param_space.param_specs
   300	                 if ps.true_value is not None}
   301	    mle_vals = {ps.name: ps.mle_value for ps in param_space.param_specs
   302	                if ps.mle_value is not None}
   303	
   304	    # Weighted statistics
   305	    print(f"\n  [{param_space.model_name}] Induced prior (τ={tau}, metric={metric_name}):")
   306	    print(f"    ESS: {ess:.0f} / {n_param_samples}")
   307	    for j, ps in enumerate(param_space.param_specs):
   308	        w_mean = np.sum(weights * param_samples[:, j])
   309	        w_std = np.sqrt(np.sum(weights * (param_samples[:, j] - w_mean)**2))
   310	        true_str = f"  true={ps.true_value}" if ps.true_value is not None else ""
   311	        print(f"    {ps.name:<8}: mean={w_mean:.4f} ± {w_std:.4f}{true_str}")
   312	
   313	    return InducedPriorResult(
   314	        model_name=param_space.model_name,
   315	        prior_name="",  # set by caller
   316	        param_names=[ps.name for ps in param_space.param_specs],
   317	        param_samples=param_samples,
   318	        log_weights=log_weights + np.log(total) if total > 0 else log_weights,
   319	        weights=weights,
   320	        G_per_sample=G_per_sample,
   321	        tau=tau,
   322	        effective_sample_size=ess,
   323	        mle_values=mle_vals if mle_vals else None,
   324	        true_values=true_vals if true_vals else None,
   325	    )
   326	
   327	
   328	def compute_model_evidence_induced(
   329	    induced_prior: InducedPriorResult,
   330	    x_train: np.ndarray,
   331	    y_train: np.ndarray,
   332	    param_space: ModelParameterSpace,
   333	) -> float:
   334	    """
   335	    Compute marginal likelihood under the GP-induced prior:
   336	
   337	      p(y | M_j, ψ) = ∫ p(y | φ, M_j) p(φ | ψ) dφ
   338	                     ≈ Σ_s w_s · p(y | φ_s, M_j)
   339	
   340	    where w_s are the induced prior weights and φ_s are parameter samples.
   341	    This is importance sampling with the induced prior as the weight.
   342	    """
   343	    n_samples = len(induced_prior.weights)
   344	    log_liks = np.zeros(n_samples)
   345	
   346	    for s_idx in range(n_samples):
   347	        param_dict = {name: induced_prior.param_samples[s_idx, j]
   348	                      for j, name in enumerate(induced_prior.param_names)}
   349	
   350	        try:
   351	            mu = param_space.predict_fn(x_train, param_dict)
   352	            sigma = param_dict.get(param_space.noise_param, 0.3)
   353	            sigma2 = sigma ** 2
   354	            residuals = y_train - mu
   355	            n = len(y_train)
   356	            log_liks[s_idx] = -0.5 * n * np.log(2 * np.pi * sigma2) - 0.5 * np.sum(residuals**2) / sigma2
   357	        except Exception:
   358	            log_liks[s_idx] = -np.inf
   359	
   360	    # Weighted average: Σ w_s * p(y|φ_s)
   361	    # In log space: log(Σ w_s exp(log_lik_s))
   362	    log_evidence = _log_sum_exp(np.log(induced_prior.weights + 1e-300) + log_liks)
   363	
   364	    return log_evidence
   365	
   366	
   367	def _log_sum_exp(x):
   368	    """Numerically stable log-sum-exp."""
   369	    x = x[np.isfinite(x)]
   370	    if len(x) == 0:
   371	        return -np.inf
   372	    c = x.max()
   373	    return c + np.log(np.sum(np.exp(x - c)))
   374	
   375	
   376	def compute_all_model_evidences(
   377	    induced_priors: Dict[str, InducedPriorResult],
   378	    x_train: np.ndarray,
   379	    y_train: np.ndarray,
   380	    param_spaces: Dict[str, ModelParameterSpace],
   381	) -> Dict[str, float]:
   382	    """
   383	    Compute model evidence for all candidates under their induced priors.
   384	    Returns dict of model_name → log evidence.
   385	    """
   386	    evidences = {}
   387	    for model_name, ip in induced_priors.items():
   388	        evidences[model_name] = compute_model_evidence_induced(
   389	            ip, x_train, y_train, param_spaces[model_name]
   390	        )
   391	        print(f"    {model_name}: log evidence = {evidences[model_name]:.2f}")
   392	
   393	    # Compute posteriors (with equal model priors)
   394	    log_evs = np.array(list(evidences.values()))
   395	    names = list(evidences.keys())
   396	    log_evs_shifted = log_evs - log_evs.max()
   397	    posteriors = np.exp(log_evs_shifted)
   398	    posteriors /= posteriors.sum()
   399	
   400	    print(f"\n  Model posteriors (induced prior):")
   401	    for name, p in zip(names, posteriors):
   402	        print(f"    {name:<15} p = {p:.4f}")
   403	
   404	    return evidences
   405	
   406	
   407	# ═══════════════════════════════════════════════════════════════════
   408	# Visualization
   409	# ═══════════════════════════════════════════════════════════════════
   410	
   411	def plot_induced_prior_marginals(
   412	    induced_prior: InducedPriorResult,
   413	    figsize: tuple = None,
   414	):
   415	    """
   416	    Plot weighted marginal distributions for each parameter.
   417	    Shows how the GP sculpts the parameter prior.
   418	    """
   419	    import matplotlib.pyplot as plt
   420	
   421	    n_params = len(induced_prior.param_names)
   422	    ncols = min(3, n_params)
   423	    nrows = (n_params + ncols - 1) // ncols
   424	    if figsize is None:
   425	        figsize = (4.5 * ncols, 3.5 * nrows)
   426	
   427	    fig, axes = plt.subplots(nrows, ncols, figsize=figsize)
   428	    axes = np.atleast_2d(axes).flatten()
   429	
   430	    for j, name in enumerate(induced_prior.param_names):
   431	        ax = axes[j]
   432	        vals = induced_prior.param_samples[:, j]
   433	        w = induced_prior.weights
   434	
   435	        # Reference prior (unweighted histogram)
   436	        ax.hist(vals, bins=50, density=True, alpha=0.3, color='gray',
   437	                label='Reference prior p₀(φ)')
   438	
   439	        # Induced prior (weighted histogram)
   440	        ax.hist(vals, bins=50, weights=w, density=True, alpha=0.6,
   441	                color='steelblue', label='Induced prior p(φ|ψ)')
   442	
   443	        # True value
   444	        if (induced_prior.true_values and
   445	                name in induced_prior.true_values and
   446	                induced_prior.true_values[name] is not None):
   447	            ax.axvline(induced_prior.true_values[name], color='red',
   448	                       linestyle='--', linewidth=2, label=f'True = {induced_prior.true_values[name]}')
   449	
   450	        # MLE value
   451	        if (induced_prior.mle_values and
   452	                name in induced_prior.mle_values and
   453	                induced_prior.mle_values[name] is not None):
   454	            ax.axvline(induced_prior.mle_values[name], color='orange',
   455	                       linestyle=':', linewidth=2, label=f'MLE = {induced_prior.mle_values[name]:.3f}')
   456	
   457	        # Weighted mean
   458	        w_mean = np.sum(w * vals)
   459	        ax.axvline(w_mean, color='steelblue', linestyle='-', linewidth=1.5,
   460	                   alpha=0.7, label=f'Induced mean = {w_mean:.3f}')
   461	
   462	        ax.set_xlabel(name, fontsize=11)
   463	        ax.set_ylabel('Density', fontsize=9)
   464	        ax.legend(fontsize=7)
   465	        ax.grid(True, alpha=0.2)
   466	
   467	    for j in range(n_params, len(axes)):
   468	        axes[j].set_visible(False)
   469	
   470	    fig.suptitle(f"GP-Induced Prior — {induced_prior.model_name} "
   471	                 f"(prior: {induced_prior.prior_name}, τ={induced_prior.tau})",
   472	                 fontsize=13)
   473	    fig.tight_layout()
   474	    return fig
   475	
   476	
   477	def plot_induced_prior_2d(
   478	    induced_prior: InducedPriorResult,
   479	    param_x: str,
   480	    param_y: str,
   481	    figsize: tuple = (6, 5),
   482	):
   483	    """
   484	    2D scatter of induced prior over two parameters.
   485	    Point size/color shows weight.
   486	    """
   487	    import matplotlib.pyplot as plt
   488	
   489	    idx_x = induced_prior.param_names.index(param_x)
   490	    idx_y = induced_prior.param_names.index(param_y)
   491	    x = induced_prior.param_samples[:, idx_x]
   492	    y = induced_prior.param_samples[:, idx_y]
   493	    w = induced_prior.weights
   494	
   495	    # Only plot top-weighted samples for clarity
   496	    threshold = np.percentile(w, 90)
   497	    mask = w > threshold
   498	
   499	    fig, ax = plt.subplots(figsize=figsize)
   500	
   501	    # Background: all samples (faint)
   502	    ax.scatter(x, y, s=1, alpha=0.1, color='gray')
   503	
   504	    # Foreground: high-weight samples
   505	    sc = ax.scatter(x[mask], y[mask], s=20, c=w[mask],
   506	                    cmap='viridis', alpha=0.7, edgecolors='none')
   507	    plt.colorbar(sc, ax=ax, label='Induced prior weight')
   508	
   509	    # True values
   510	    true_x = (induced_prior.true_values or {}).get(param_x)
   511	    true_y = (induced_prior.true_values or {}).get(param_y)
   512	    if true_x is not None and true_y is not None:
   513	        ax.scatter([true_x], [true_y], marker='*', s=200, color='red',
   514	                   edgecolors='black', linewidth=1, zorder=10, label='True')
   515	
   516	    ax.set_xlabel(param_x, fontsize=12)
   517	    ax.set_ylabel(param_y, fontsize=12)
   518	    ax.set_title(f"Induced Prior — {induced_prior.model_name} "
   519	                 f"({induced_prior.prior_name})", fontsize=12)
   520	    ax.legend()
   521	    ax.grid(True, alpha=0.2)
   522	    fig.tight_layout()
   523	    return fig
   524	
   525	
   526	def plot_prior_comparison_marginals(
   527	    induced_priors_by_prior: Dict[str, InducedPriorResult],
   528	    param_name: str,
   529	    figsize: tuple = (8, 5),
   530	):
   531	    """
   532	    Compare induced prior marginals across GP prior configs for one parameter.
   533	
   534	    This is the key BI* demonstration: same model, same data, but different
   535	    GP priors → different induced priors on model parameters.
   536	    """
   537	    import matplotlib.pyplot as plt
   538	
   539	    colors = {
   540	        'informative': '#2ecc71',
   541	        'vague': '#3498db',
   542	        'misspecified_tight': '#e74c3c',
   543	        'low_noise': '#9b59b6',
   544	        'high_noise': '#f39c12',
   545	    }
   546	
   547	    fig, ax = plt.subplots(figsize=figsize)
   548	
   549	    for prior_name, ip in induced_priors_by_prior.items():
   550	        j = ip.param_names.index(param_name)
   551	        vals = ip.param_samples[:, j]
   552	        w = ip.weights
   553	
   554	        # Weighted KDE approximation via histogram
   555	        color = colors.get(prior_name, 'gray')
   556	        ax.hist(vals, bins=60, weights=w, density=True, alpha=0.4,
   557	                color=color, label=f'{prior_name}')
   558	
   559	        # Weighted mean line
   560	        w_mean = np.sum(w * vals)
   561	        ax.axvline(w_mean, color=color, linestyle='--', linewidth=1.5, alpha=0.8)
   562	
   563	    # True value
   564	    first_ip = list(induced_priors_by_prior.values())[0]
   565	    true_val = (first_ip.true_values or {}).get(param_name)
   566	    if true_val is not None:
   567	        ax.axvline(true_val, color='black', linestyle='-', linewidth=2,
   568	                   label=f'True = {true_val}')
   569	
   570	    model_name = first_ip.model_name
   571	    ax.set_xlabel(param_name, fontsize=12)
   572	    ax.set_ylabel('Induced Prior Density', fontsize=11)
   573	    ax.set_title(f"Prior Transfer: How GP Prior Shapes {model_name}'s '{param_name}' Prior",
   574	                 fontsize=13)
   575	    ax.legend(fontsize=9)
   576	    ax.grid(True, alpha=0.2)
   577	    fig.tight_layout()
   578	    return fig
   579	
   580	
   581	def plot_evidence_comparison(
   582	    evidences_by_prior: Dict[str, Dict[str, float]],
   583	    figsize: tuple = None,
   584	):
   585	    """
   586	    Bar chart: model posteriors under induced priors, grouped by GP prior.
   587	
   588	    Shows how GP prior choice affects model selection outcome.
   589	    """
   590	    import matplotlib.pyplot as plt
   591	
   592	    prior_names = list(evidences_by_prior.keys())
   593	    model_names = list(evidences_by_prior[prior_names[0]].keys())
   594	    n_priors = len(prior_names)
   595	    n_models = len(model_names)
   596	
   597	    colors = ['#e74c3c', '#3498db', '#2ecc71', '#9b59b6']
   598	
   599	    if figsize is None:
   600	        figsize = (max(10, 2.5 * n_priors), 5)
   601	
   602	    fig, ax = plt.subplots(figsize=figsize)
   603	    x = np.arange(n_priors)
   604	    width = 0.8 / n_models
   605	
   606	    for m_idx, model_name in enumerate(model_names):
   607	        posteriors = []
   608	        for prior_name in prior_names:
   609	            evs = evidences_by_prior[prior_name]
   610	            log_evs = np.array(list(evs.values()))
   611	            log_evs -= log_evs.max()
   612	            ps = np.exp(log_evs) / np.exp(log_evs).sum()
   613	            posteriors.append(ps[m_idx])
   614	
   615	        offset = (m_idx - n_models / 2 + 0.5) * width
   616	        ax.bar(x + offset, posteriors, width, label=model_name,
   617	               color=colors[m_idx % len(colors)])
   618	
   619	    ax.set_xticks(x)
   620	    ax.set_xticklabels(prior_names, fontsize=10)
   621	    ax.set_ylabel("Model Posterior (induced prior)", fontsize=11)
   622	    ax.set_title("BI* Model Selection: How GP Prior Affects Model Ranking", fontsize=13)
   623	    ax.set_ylim(0, 1)
   624	    ax.axhline(0.25, color='gray', linestyle=':', alpha=0.5, label='uniform')
   625	    ax.legend(fontsize=9)
   626	    ax.grid(True, alpha=0.2, axis='y')
   627	    fig.tight_layout()
   628	    return fig
   629	
   630	
   631	def plot_prior_sharpness_summary(
   632	    induced_priors_all: Dict[str, Dict[str, InducedPriorResult]],
   633	    figsize: tuple = None,
   634	):
   635	    """
   636	    Summary plot: ESS (effective sample size) as measure of how much
   637	    the GP prior concentrates each model's parameter prior.
   638	
   639	    Higher ESS = more diffuse induced prior = less information transfer.
   640	    Lower ESS = sharper induced prior = more information transfer.
   641	    """
   642	    import matplotlib.pyplot as plt
   643	
   644	    prior_names = list(induced_priors_all.keys())
   645	    model_names = list(induced_priors_all[prior_names[0]].keys())
   646	    n_priors = len(prior_names)
   647	    n_models = len(model_names)
   648	
   649	    colors = ['#e74c3c', '#3498db', '#2ecc71', '#9b59b6']
   650	
   651	    if figsize is None:
   652	        figsize = (max(10, 2.5 * n_priors), 5)
   653	
   654	    fig, ax = plt.subplots(figsize=figsize)
   655	    x = np.arange(n_priors)
   656	    width = 0.8 / n_models
   657	
   658	    for m_idx, model_name in enumerate(model_names):
   659	        ess_vals = []
   660	        for prior_name in prior_names:
   661	            ip = induced_priors_all[prior_name][model_name]
   662	            ess_vals.append(ip.effective_sample_size)
   663	
   664	        offset = (m_idx - n_models / 2 + 0.5) * width
   665	        ax.bar(x + offset, ess_vals, width, label=model_name,
   666	               color=colors[m_idx % len(colors)])
   667	
   668	    ax.set_xticks(x)
   669	    ax.set_xticklabels(prior_names, fontsize=10)
   670	    ax.set_ylabel("Effective Sample Size (ESS)", fontsize=11)
   671	    ax.set_title("Prior Information Transfer: Lower ESS = Sharper Induced Prior",
   672	                 fontsize=13)
   673	    ax.legend(fontsize=9)
   674	    ax.grid(True, alpha=0.2, axis='y')
   675	    fig.tight_layout()
   676	    return fig

==================== SOURCE bistar_gp/external_targets.py (line-numbered) ====================
     1	"""
     2	External validation targets of van Bork, Romeijn and Wagenmakers (2025),
     3	Synthese, doi:10.1007/s11229-025-05286-y, section 4, and a checker for the
     4	artifact runs/vanbork_external_validation/results.json that
     5	experiments/vanbork_external_validation.py writes on paper/case-a-vanbork.
     6	
     7	2026-09 review FIX-8: the case script prints its errors against these targets
     8	and never asserts them, so a regression in its own divergence or quadrature
     9	could regenerate the artifact with wrong error fields and exit 0. This module
    10	holds the closed forms and the assertion the script (fix pass 2) and the
    11	tests call. The checker recomputes the errors from the stored rows instead of
    12	trusting the stored abs_error_at_min_tau field.
    13	"""
    14	
    15	import json
    16	from typing import Dict
    17	
    18	import numpy as np
    19	
    20	# Target A (non-overlapping point models): data prior 0.4 on s/n = 0.16 and
    21	# 0.6 on s/n = 0.19; models theta = 0.15 and theta = 0.20; their answer is the
    22	# data-prior mass on the nearest model.
    23	VANBORK_TARGET_A: Dict[str, float] = {"M1 (theta=0.15)": 0.4, "M2 (theta=0.20)": 0.6}
    24	
    25	# Target B (completely overlapping models): point data prior at theta = 1/2;
    26	# M_x with theta ~ Beta(50, 50) against M_z with theta ~ Beta(2, 2); their
    27	# answer is the normalized ratio of the two prior densities at that point.
    28	VANBORK_TARGET_B_PRIORS: Dict[str, tuple] = {"M_x beta(50,50)": (50.0, 50.0),
    29	                                             "M_z beta(2,2)": (2.0, 2.0)}
    30	VANBORK_TARGET_B_PSI = 0.5
    31	
    32	
    33	def vanbork_target_b_densities(psi: float = VANBORK_TARGET_B_PSI) -> Dict[str, float]:
    34	    """The two prior densities at the data-prior point."""
    35	    from scipy.stats import beta as beta_dist
    36	
    37	    return {name: float(beta_dist.pdf(psi, a, b))
    38	            for name, (a, b) in VANBORK_TARGET_B_PRIORS.items()}
    39	
    40	
    41	def vanbork_target_b_weight(psi: float = VANBORK_TARGET_B_PSI) -> float:
    42	    """Their closed form for p(M_x): d_x / (d_x + d_z) at double precision."""
    43	    dens = vanbork_target_b_densities(psi)
    44	    names = list(VANBORK_TARGET_B_PRIORS)
    45	    return dens[names[0]] / (dens[names[0]] + dens[names[1]])
    46	
    47	
    48	def vanbork_target_b() -> Dict[str, float]:
    49	    w = vanbork_target_b_weight()
    50	    names = list(VANBORK_TARGET_B_PRIORS)
    51	    return {names[0]: w, names[1]: 1.0 - w}
    52	
    53	
    54	def _min_tau_row(rows, names, key):
    55	    """The smallest-tau row with every named posterior validated finite.
    56	
    57	    Validation comes first (fix pass 1b, review R9): Python's max() keeps a
    58	    finite first argument over a NaN and abs(nan - 1) > tol is False, so an
    59	    unvalidated NaN column would pass both the mass check and the tolerance.
    60	    """
    61	    finite = [r for r in rows if np.isfinite(float(r["tau"]))]
    62	    if not finite:
    63	        raise AssertionError(f"external target {key}: no row carries a finite tau")
    64	    row = min(finite, key=lambda r: float(r["tau"]))
    65	    for n in names:
    66	        value = float(row[n])
    67	        if not np.isfinite(value):
    68	            raise AssertionError(
    69	                f"external target {key}: non-finite posterior {value!r} for {n!r} "
    70	                f"at tau={row['tau']}")
    71	    return row
    72	
    73	
    74	def external_target_errors(results: dict) -> Dict[str, float]:
    75	    """Recompute max |ours - target| at the smallest-tau row of a results.json
    76	    payload (the per-draw route rows for Target A, the Z_M route rows for
    77	    Target B). Raises AssertionError on a non-finite posterior."""
    78	    a = results["target_a"]
    79	    a_row = _min_tau_row(a["rows"], a["names"], "A")
    80	    err_a = max(abs(float(a_row[n]) - VANBORK_TARGET_A[n]) for n in a["names"])
    81	    b = results["target_b"]
    82	    b_row = _min_tau_row(b["rows"], b["names"], "B")
    83	    target_b = vanbork_target_b()
    84	    err_b = max(abs(float(b_row[n]) - target_b[n]) for n in b["names"])
    85	    return {"A": float(err_a), "B": float(err_b)}
    86	
    87	
    88	def check_external_targets(results_json_path, tol_a: float = 1e-6, tol_b: float = 1e-5,
    89	                           stored_field_tol: float = 1e-9) -> Dict[str, float]:
    90	    """Assert that the artifact reproduces both published targets.
    91	
    92	    Raises AssertionError naming the offending target when a recomputed error
    93	    exceeds its tolerance, when a row's masses do not sum to one, or when the
    94	    stored abs_error_at_min_tau field disagrees with the recomputation.
    95	    Returns the recomputed errors.
    96	    """
    97	    with open(results_json_path) as f:
    98	        results = json.load(f)
    99	    for key, block, target in (("A", results["target_a"], VANBORK_TARGET_A),
   100	                               ("B", results["target_b"], vanbork_target_b())):
   101	        if set(block["names"]) != set(target):
   102	            raise AssertionError(
   103	                f"external target {key}: model names {block['names']} do not match "
   104	                f"the published targets {list(target)}")
   105	        row = _min_tau_row(block["rows"], block["names"], key)
   106	        mass = sum(float(row[n]) for n in block["names"])
   107	        if abs(mass - 1.0) > 1e-9:
   108	            raise AssertionError(
   109	                f"external target {key}: posterior masses sum to {mass!r} at tau={row['tau']}")
   110	    errors = external_target_errors(results)
   111	    stored = results.get("abs_error_at_min_tau", {})
   112	    for key, tol in (("A", tol_a), ("B", tol_b)):
   113	        if key in stored and not np.isfinite(float(stored[key])):
   114	            raise AssertionError(
   115	                f"external target {key}: stored abs_error_at_min_tau is {stored[key]!r}")
   116	        if not np.isfinite(errors[key]) or errors[key] > tol:
   117	            raise AssertionError(
   118	                f"external target {key}: |ours - target| = {errors[key]:.3e} exceeds "
   119	                f"tolerance {tol:.1e} at the smallest-tau row")
   120	        if key in stored and abs(float(stored[key]) - errors[key]) > stored_field_tol:
   121	            raise AssertionError(
   122	                f"external target {key}: stored abs_error_at_min_tau {stored[key]!r} "
   123	                f"disagrees with the recomputed {errors[key]!r}")
   124	    return errors

==================== SOURCE bistar_gp/candidates.py (line-numbered) ====================
     1	"""
     2	Parametric candidate models for BMS* comparison.
     3	
     4	Each model has:
     5	    fit(x, y)       → learn parameters via MLE
     6	    predict(x_eval) → (mean, cov) predictive distribution
     7	    name            → string identifier
     8	    params()        → dict of fitted parameters
     9	"""
    10	
    11	import logging
    12	
    13	import numpy as np
    14	from scipy.optimize import minimize
    15	from dataclasses import dataclass
    16	from typing import Tuple, Dict, Optional
    17	
    18	logger = logging.getLogger(__name__)
    19	
    20	
    21	@dataclass
    22	class CandidateResult:
    23	    """Predictive distribution from a candidate model."""
    24	    name: str
    25	    mean: np.ndarray          # (n_eval,)
    26	    cov: np.ndarray           # (n_eval, n_eval)
    27	    noise_var: float
    28	    parameters: Dict[str, float]
    29	    # Universe identity for the Mauna A4 separate-normalization rule: stamped
    30	    # by _make_result from the producing model's tag, so the guard can
    31	    # validate the exact list handed to run_bms_star rather than the model
    32	    # list it was derived from. None for non-registry candidates (the toy
    33	    # universe has no A4 rule).
    34	    universe: Optional[str] = None
    35	
    36	
    37	class CandidateModel:
    38	    """Base class for parametric candidate models."""
    39	
    40	    name: str = "base"
    41	
    42	    def fit(self, x: np.ndarray, y: np.ndarray) -> None:
    43	        raise NotImplementedError
    44	
    45	    def predict(self, x_eval: np.ndarray) -> CandidateResult:
    46	        raise NotImplementedError
    47	
    48	    def _fit_mle(self, x, y, f_predict, p0, bounds=None, return_status=False):
    49	        """
    50	        Generic MLE fitting. f_predict(x, params) -> mean vector.
    51	        Assumes Gaussian noise: y ~ N(f(x; params), sigma^2 I).
    52	        Last element of params is log(sigma).
    53	
    54	        Returns (params, nll), or (params, nll, status) when
    55	        return_status=True, where status is scipy's report
    56	        {success, status, message, nit} (2026-09 review FIX-5: a
    57	        non-successful L-BFGS-B result used to be accepted silently).
    58	        Multi-start callers must compare restarts by this nll — the FULL
    59	        negative log likelihood including the 0.5*n*log(2*pi*sigma^2) term.
    60	        The residual term alone is useless for that comparison: at any
    61	        converged MLE sigma^2 = mean(residuals^2), so 0.5*sum(r^2)/sigma^2 =
    62	        n/2 for EVERY restart, and selection degrades to optimizer-noise
    63	        tie-breaking (which picked a degenerate near-linear "sinusoid" on the
    64	        thesis toy data).
    65	        """
    66	        def neg_log_lik(params):
    67	            log_sigma = params[-1]
    68	            sigma2 = np.exp(2 * log_sigma)
    69	            mu = f_predict(x, params[:-1])
    70	            residuals = y - mu
    71	            n = len(y)
    72	            return 0.5 * n * np.log(2 * np.pi * sigma2) + 0.5 * np.sum(residuals**2) / sigma2
    73	
    74	        result = minimize(neg_log_lik, p0, bounds=bounds, method="L-BFGS-B")
    75	        if not return_status:
    76	            return result.x, result.fun
    77	        status = {"success": bool(result.success), "status": int(result.status),
    78	                  "message": str(result.message), "nit": int(result.nit)}
    79	        return result.x, result.fun, status
    80	
    81	    @staticmethod
    82	    def _select_restart(candidates, model_name):
    83	        """Pick the best restart, preferring successful optimizer reports;
    84	        fall back to the best overall with a warning when none succeeded.
    85	        candidates: list of (params, nll, status)."""
    86	        if not candidates:
    87	            return None
    88	        ok = [c for c in candidates if c[2]["success"]]
    89	        pool = ok if ok else candidates
    90	        if not ok:
    91	            logger.warning("%s: no restart reported convergence (%s); using the "
    92	                           "best non-converged result", model_name,
    93	                           candidates[0][2]["message"])
    94	        return min(pool, key=lambda c: c[1])
    95	
    96	    def _make_result(self, x_eval, mean, noise_var, params_dict):
    97	        """Build CandidateResult with isotropic noise covariance."""
    98	        n = len(x_eval)
    99	        cov = noise_var * np.eye(n)
   100	        return CandidateResult(
   101	            name=self.name,
   102	            mean=mean,
   103	            cov=cov,
   104	            noise_var=noise_var,
   105	            parameters=params_dict,
   106	            universe=getattr(self, "universe", None),
   107	        )
   108	
   109	
   110	class LinearModel(CandidateModel):
   111	    """y = ax + b + eps"""
   112	
   113	    name = "Linear"
   114	
   115	    def __init__(self):
   116	        self.a = 0.0
   117	        self.b = 0.0
   118	        self.sigma = 1.0
   119	
   120	    def fit(self, x, y):
   121	        def f(x, params):
   122	            return params[0] * x + params[1]
   123	
   124	        p0 = [0.0, 0.0, np.log(0.5)]
   125	        result, _, status = self._fit_mle(x, y, f, p0, return_status=True)
   126	        if not status["success"]:
   127	            logger.warning("Linear fit did not converge: %s", status["message"])
   128	        self.a, self.b = result[0], result[1]
   129	        self.sigma = np.exp(result[2])
   130	
   131	    def predict(self, x_eval):
   132	        mean = self.a * x_eval + self.b
   133	        return self._make_result(
   134	            x_eval, mean, self.sigma**2,
   135	            {"a": self.a, "b": self.b, "sigma": self.sigma},
   136	        )
   137	
   138	
   139	class SinusoidalModel(CandidateModel):
   140	    """y = A * sin(omega * x + phi) + eps"""
   141	
   142	    name = "Sinusoidal"
   143	
   144	    def __init__(self):
   145	        self.A = 1.0
   146	        self.omega = 1.0
   147	        self.phi = 0.0
   148	        self.sigma = 1.0
   149	
   150	    def fit(self, x, y):
   151	        def f(x, params):
   152	            return params[0] * np.sin(params[1] * x + params[2])
   153	
   154	        # Try multiple initializations (omega is tricky); prefer restarts
   155	        # whose optimizer reported success (FIX-5).
   156	        restarts = []
   157	        for omega_init in [0.5, 1.0, 1.5, 2.0]:
   158	            for A_init in [0.5, 1.0, 2.0]:
   159	                p0 = [A_init, omega_init, 0.0, np.log(0.5)]
   160	                try:
   161	                    restarts.append(self._fit_mle(x, y, f, p0, return_status=True))
   162	                except Exception:
   163	                    continue
   164	        best = self._select_restart(restarts, self.name)
   165	        best_params = best[0] if best is not None else None
   166	
   167	        if best_params is not None:
   168	            self.A, self.omega, self.phi = best_params[0], best_params[1], best_params[2]
   169	            self.sigma = np.exp(best_params[3])
   170	        else:
   171	            # Fallback: just use initial
   172	            self.A, self.omega, self.phi = 1.0, 1.0, 0.0
   173	            self.sigma = np.std(y)
   174	
   175	    def predict(self, x_eval):
   176	        mean = self.A * np.sin(self.omega * x_eval + self.phi)
   177	        return self._make_result(
   178	            x_eval, mean, self.sigma**2,
   179	            {"A": self.A, "omega": self.omega, "phi": self.phi, "sigma": self.sigma},
   180	        )
   181	
   182	
   183	class SinLinearModel(CandidateModel):
   184	    """y = A * sin(omega * x + phi) + b * x + c + eps"""
   185	
   186	    name = "Sin+Linear"
   187	
   188	    def __init__(self):
   189	        self.A = 1.0
   190	        self.omega = 1.0
   191	        self.phi = 0.0
   192	        self.b = 0.0
   193	        self.c = 0.0
   194	        self.sigma = 1.0
   195	
   196	    def fit(self, x, y):
   197	        def f(x, params):
   198	            return params[0] * np.sin(params[1] * x + params[2]) + params[3] * x + params[4]
   199	
   200	        restarts = []
   201	        for omega_init in [0.5, 1.0, 1.5, 2.0]:
   202	            p0 = [1.0, omega_init, 0.0, 0.25, 0.0, np.log(0.3)]
   203	            try:
   204	                restarts.append(self._fit_mle(x, y, f, p0, return_status=True))
   205	            except Exception:
   206	                continue
   207	        best = self._select_restart(restarts, self.name)
   208	        best_params = best[0] if best is not None else None
   209	
   210	        if best_params is not None:
   211	            self.A = best_params[0]
   212	            self.omega = best_params[1]
   213	            self.phi = best_params[2]
   214	            self.b = best_params[3]
   215	            self.c = best_params[4]
   216	            self.sigma = np.exp(best_params[5])
   217	        else:
   218	            self.A, self.omega, self.phi = 1.0, 1.0, 0.0
   219	            self.b, self.c = 0.25, 0.0
   220	            self.sigma = np.std(y)
   221	
   222	    def predict(self, x_eval):
   223	        mean = self.A * np.sin(self.omega * x_eval + self.phi) + self.b * x_eval + self.c
   224	        return self._make_result(
   225	            x_eval, mean, self.sigma**2,
   226	            {"A": self.A, "omega": self.omega, "phi": self.phi,
   227	             "b": self.b, "c": self.c, "sigma": self.sigma},
   228	        )
   229	
   230	
   231	class QuadraticModel(CandidateModel):
   232	    """y = a * x^2 + b * x + c + eps"""
   233	
   234	    name = "Quadratic"
   235	
   236	    def __init__(self):
   237	        self.a = 0.0
   238	        self.b = 0.0
   239	        self.c = 0.0
   240	        self.sigma = 1.0
   241	
   242	    def fit(self, x, y):
   243	        def f(x, params):
   244	            return params[0] * x**2 + params[1] * x + params[2]
   245	
   246	        p0 = [0.0, 0.0, 0.0, np.log(0.5)]
   247	        result, _, status = self._fit_mle(x, y, f, p0, return_status=True)
   248	        if not status["success"]:
   249	            logger.warning("Quadratic fit did not converge: %s", status["message"])
   250	        self.a, self.b, self.c = result[0], result[1], result[2]
   251	        self.sigma = np.exp(result[3])
   252	
   253	    def predict(self, x_eval):
   254	        mean = self.a * x_eval**2 + self.b * x_eval + self.c
   255	        return self._make_result(
   256	            x_eval, mean, self.sigma**2,
   257	            {"a": self.a, "b": self.b, "c": self.c, "sigma": self.sigma},
   258	        )
   259	
   260	
   261	def build_toy_candidates():
   262	    """Return all 4 candidate models for the toy example."""
   263	    return [LinearModel(), SinusoidalModel(), SinLinearModel(), QuadraticModel()]

==================== SOURCE bistar_gp/model.py (line-numbered) ====================
     1	"""
     2	GPyTorch model wrapper with robustness built in:
     3	- Double precision
     4	- Hyperparameter constraints (away from zero!)
     5	- Clean interface for additive kernel decomposition
     6	"""
     7	
     8	import torch
     9	import gpytorch
    10	from gpytorch.kernels import ScaleKernel, RBFKernel, LinearKernel, PeriodicKernel
    11	from gpytorch.constraints import Interval, Positive
    12	from gpytorch.priors import GammaPrior, LogNormalPrior
    13	from typing import List, Optional, Dict, Any
    14	
    15	torch.set_default_dtype(torch.float64)
    16	
    17	
    18	class AdditiveGPModel(gpytorch.models.ExactGP):
    19	    """Exact GP with named additive kernel components for decomposition."""
    20	
    21	    def __init__(self, train_x, train_y, likelihood, kernel_components, component_names=None):
    22	        super().__init__(train_x, train_y, likelihood)
    23	        self.mean_module = gpytorch.means.ZeroMean()
    24	        self.component_names = component_names or [f"comp_{i}" for i in range(len(kernel_components))]
    25	
    26	        # Build sum kernel. The component kernels are registered ONLY through
    27	        # covar_module (a plain list here, not an nn.ModuleList) so each kernel
    28	        # prior is registered exactly once. Registering them a second time via a
    29	        # ModuleList made pyro_sample_from_prior create a duplicate HMC latent
    30	        # site per hyperparameter and add the kernel priors to the NUTS target
    31	        # twice, biasing every HMC posterior.
    32	        self.kernel_components = list(kernel_components)
    33	        self.covar_module = self.kernel_components[0]
    34	        for k in self.kernel_components[1:]:
    35	            self.covar_module = self.covar_module + k
    36	
    37	    def forward(self, x):
    38	        mean = self.mean_module(x)
    39	        covar = self.covar_module(x)
    40	        return gpytorch.distributions.MultivariateNormal(mean, covar)
    41	
    42	    def get_component_kernel_matrices(self, X_train, X_test):
    43	        """Evaluate each component kernel at train/test points."""
    44	        matrices = {}
    45	        for name, kernel in zip(self.component_names, self.kernel_components):
    46	            matrices[name] = {
    47	                "XX": kernel(X_train, X_train).evaluate().detach(),
    48	                "XstarX": kernel(X_test, X_train).evaluate().detach(),
    49	                "XstarXstar": kernel(X_test, X_test).evaluate().detach(),
    50	                "XXstar": kernel(X_train, X_test).evaluate().detach(),
    51	            }
    52	        return matrices
    53	
    54	
    55	# ── HMC sample-site naming ───────────────────────────────────────
    56	#
    57	# fit_hmc/fit_mcmc_simple return dicts keyed by pyro sample-site name. The
    58	# names follow the module tree above: each kernel hyperparameter appears once,
    59	# at "covar_module.kernels.{i}.<hp>_prior", and the noise at
    60	# "likelihood.noise_covar.noise_prior". Archives saved by older code carry
    61	# extra sites: "kernel_components.{i}.*" duplicates (disconnected prior draws
    62	# from the double-registration bug) and a bare "noise_covar.noise_prior" from
    63	# the era when fit_hmc sampled the likelihood separately (in those archives
    64	# the bare site is the one that was wired to the likelihood). Every consumer
    65	# must go through the two helpers below rather than parsing names itself.
    66	
    67	def select_hmc_sites(sample_keys):
    68	    """Pick the sample sites actually wired to the likelihood, across eras.
    69	
    70	    Returns the kernel hyperparameter keys plus the noise key, preferring the
    71	    current naming and falling back to legacy names only when the current ones
    72	    are absent, so both fresh runs and old cached archives resolve to the
    73	    connected (posterior) latents.
    74	    """
    75	    keys = list(sample_keys)
    76	    kernel_keys = [k for k in keys if k.startswith("covar_module.kernels.")]
    77	    if not kernel_keys:
    78	        # Single-kernel models register their one kernel directly as
    79	        # covar_module (no AdditiveKernel wrapper), so its sites carry no
    80	        # ".kernels.{i}." segment: "covar_module.outputscale_prior" and
    81	        # "covar_module.base_kernel.lengthscale_prior". Before the 2026-09
    82	        # review fix (FIX-1) these names were dropped here and rejected by
    83	        # apply_hp_value, so every predictive of a single-kernel model was
    84	        # built at the fresh model's initialization kernel values.
    85	        kernel_keys = [k for k in keys if k.startswith("covar_module.")]
    86	    if not kernel_keys:  # archives predating the covar_module naming
    87	        kernel_keys = [k for k in keys if k.startswith("kernel_components.")]
    88	    if "noise_covar.noise_prior" in keys:
    89	        # Legacy archives: the bare site was sampled last and overwrote the
    90	        # likelihood.* one, so it holds the connected draws.
    91	        noise_keys = ["noise_covar.noise_prior"]
    92	    else:
    93	        noise_keys = [k for k in keys if k.endswith("noise_covar.noise_prior")]
    94	    return kernel_keys + noise_keys
    95	
    96	
    97	def apply_hp_value(model, likelihood, pyro_name, value):
    98	    """Set one hyperparameter on model/likelihood from a sample-site name.
    99	
   100	    Accepts both current ("covar_module.kernels.{i}.*") and legacy
   101	    ("kernel_components.{i}.*", "noise_covar.noise*") site names. Returns True
   102	    if the name was recognized and applied, False otherwise.
   103	    """
   104	    if "noise_covar.noise" in pyro_name:
   105	        likelihood.noise = value
   106	        return True
   107	    parts = pyro_name.split(".")
   108	    if len(parts) < 2:
   109	        return False
   110	    if parts[0] == "covar_module" and parts[1] == "kernels":
   111	        comp_idx = int(parts[2])
   112	    elif parts[0] == "covar_module":
   113	        # Single-kernel site name (FIX-1): the kernel IS covar_module, so the
   114	        # name maps to component 0 exactly when the model has one component
   115	        # registered directly as covar_module; any other model returns False.
   116	        components = getattr(model, "kernel_components", None)
   117	        if not components or len(components) != 1 \
   118	                or model.covar_module is not components[0]:
   119	            return False
   120	        comp_idx = 0
   121	    elif parts[0] == "kernel_components":
   122	        comp_idx = int(parts[1])
   123	    else:
   124	        return False
   125	    kernel = model.kernel_components[comp_idx]
   126	    if "base_kernel.lengthscale" in pyro_name:
   127	        kernel.base_kernel.lengthscale = value
   128	    elif "base_kernel.period_length" in pyro_name:
   129	        kernel.base_kernel.period_length = value
   130	    elif "outputscale" in pyro_name:
   131	        kernel.outputscale = value
   132	    elif "variance" in pyro_name:
   133	        kernel.variance = value
   134	    else:
   135	        return False
   136	    return True
   137	
   138	
   139	# ── Kernel builders ──────────────────────────────────────────────
   140	
   141	MAUNA_FROZEN_PERIOD = 1.0  # A10: seasonal period frozen at exactly 1.0
   142	
   143	
   144	def assert_mauna_period_frozen(model):
   145	    """A10 invariant check: every periodic component stays at exactly 1.0.
   146	
   147	    Call after any MAP / multi-start / sampling path that touches a Mauna
   148	    model. Verifies, for each PeriodicKernel among the model's components,
   149	    that the constrained period equals MAUNA_FROZEN_PERIOD bit-exactly and
   150	    that its raw parameter remains gradient-frozen. Raises AssertionError with
   151	    the offending value otherwise.
   152	    """
   153	    checked = 0
   154	    for kernel in model.kernel_components:
   155	        base = getattr(kernel, "base_kernel", kernel)
   156	        if isinstance(base, PeriodicKernel):
   157	            period = base.period_length.item()
   158	            assert period == MAUNA_FROZEN_PERIOD, (
   159	                f"A10 violation: period_length = {period!r}, expected exactly "
   160	                f"{MAUNA_FROZEN_PERIOD} (docs/plan-d19-mauna.md A10)")
   161	            assert not base.raw_period_length.requires_grad, (
   162	                "A10 violation: raw_period_length is trainable again")
   163	            checked += 1
   164	    assert checked > 0, "no PeriodicKernel found; nothing to check"
   165	
   166	
   167	def build_mauna_loa_kernels():
   168	    """Trend + Seasonal + Medium-term for CO2 decomposition."""
   169	    trend = ScaleKernel(
   170	        RBFKernel(
   171	            lengthscale_constraint=Positive(),
   172	            lengthscale_prior=LogNormalPrior(4.0, 1.0),
   173	        ),
   174	        outputscale_constraint=Positive(),
   175	        outputscale_prior=GammaPrior(4.0, 0.5),
   176	    )
   177	
   178	    seasonal = ScaleKernel(
   179	        PeriodicKernel(
   180	            period_length_constraint=Interval(0.99, 1.01),
   181	            lengthscale_constraint=Positive(),
   182	            lengthscale_prior=GammaPrior(3.0, 2.0),
   183	        ),
   184	        outputscale_constraint=Positive(),
   185	        outputscale_prior=GammaPrior(3.0, 1.0),
   186	    )
   187	    # A10 period freeze (D19/D20): the old "keep this one fixed" comment was
   188	    # aspirational — raw_period_length stayed requires_grad=True, so fit_map
   189	    # drifted the plug-in period to ~0.9996 (standing disclosure 4 in
   190	    # docs/plan-d19-mauna.md §6.14). Freeze it at EXACTLY 1.0: raw = 0 under
   191	    # Interval(0.99, 1.01) maps to lower + (upper-lower)*sigmoid(0) = 1.0
   192	    # exactly in float64 (verified), and with requires_grad off the period has
   193	    # no gradient, no optimizer state, and no fit_mcmc_simple proposal
   194	    # dimension. It carries no prior, so the pyro sample-site inventory stays
   195	    # at 7 (asserted in tests).
   196	    with torch.no_grad():
   197	        seasonal.base_kernel.raw_period_length.fill_(0.0)
   198	    seasonal.base_kernel.raw_period_length.requires_grad_(False)
   199	    # Freeze-target stamp: fit_map verifies, at entry, that every stamped
   200	    # module still holds its frozen value, so a period mutated BEFORE a fit
   201	    # (frozen-but-moved, which the unchanged-at-exit guard alone would let
   202	    # through) fails at the next MAP/multi-start call (M2a review round,
   203	    # finding 4).
   204	    seasonal.base_kernel._a10_frozen_period = MAUNA_FROZEN_PERIOD
   205	    assert seasonal.base_kernel.period_length.item() == MAUNA_FROZEN_PERIOD
   206	
   207	    medium = ScaleKernel(
   208	        RBFKernel(
   209	            lengthscale_constraint=Positive(),
   210	            lengthscale_prior=GammaPrior(3.0, 1.0),
   211	        ),
   212	        outputscale_constraint=Positive(),
   213	        outputscale_prior=GammaPrior(2.0, 1.0),
   214	    )
   215	
   216	    return [trend, seasonal, medium], ["trend", "seasonal", "medium_term"]
   217	
   218	
   219	def build_likelihood(noise_constraint=None, noise_prior=None):
   220	    return gpytorch.likelihoods.GaussianLikelihood(
   221	        noise_constraint=noise_constraint or Positive(),
   222	        noise_prior=noise_prior or GammaPrior(1.75, 1.0),
   223	    )
   224	
   225	def build_model(train_x, train_y, kernel_components, component_names, likelihood=None):
   226	    """Build full model. Enforces float64. Returns (model, likelihood)."""
   227	    train_x, train_y = train_x.double(), train_y.double()
   228	    if likelihood is None:
   229	        likelihood = build_likelihood()
   230	    model = AdditiveGPModel(train_x, train_y, likelihood, kernel_components, component_names)
   231	    return model.double(), likelihood.double()
   232	
   233	def build_toy_kernels():
   234	    """SE (truth) + Linear (bias) — thesis toy example."""
   235	    se = ScaleKernel(
   236	        RBFKernel(
   237	            lengthscale_constraint=Positive(),
   238	            #lengthscale_prior=GammaPrior(6.0, 0.85),
   239	            lengthscale_prior=GammaPrior(2.0, 2.0),  # mean ~1, favors short lengthscales
   240	        ),
   241	        outputscale_constraint=Positive(),
   242	        outputscale_prior=GammaPrior(6.0, 0.85),
   243	    )
   244	    linear = LinearKernel(
   245	        variance_constraint=Positive(),
   246	        variance_prior=GammaPrior(6.0, 0.85),
   247	    )
   248	    return [se, linear], ["unbiased_se", "bias_linear"]