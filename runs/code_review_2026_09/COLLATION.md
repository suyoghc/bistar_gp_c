# Interim collation — implementation-correctness review, 2026-09-05

**Status: ALL FOUR channels reported (updated 2026-09-06).** The two package-only channels (Kimi K3,
GLM 5.3) were driver-run and are complete. The two repo-access channels (Fable, and Codex running `gpt-6-astra` at xhigh
effort) were author-run and landed 2026-09-06. The clusters below were written
when only the package-only pair had reported; the four-channel supersession is
recorded in the section at the end. This is still NOT the final §4 collation:
single-reporter findings have not been adversarially cross-checked, and the
author-adjudication ledger is not yet drawn up.

| Channel | Access | Verdict | Findings |
|---|---|---|---|
| Kimi K3 (`moonshotai/kimi-k3`) | package-only | FINDINGS | 6 (2 S2, 3 S3, 1 S4) |
| GLM 5.3 (`z-ai/glm-5.3`) | package-only | FINDINGS | 7 (1 S2, 5 S3, 1 S4) |
| Fable | full repo | FINDINGS | 10 (1 S1, 3 S2, 4 S3, 3 S4) |
| Codex (`gpt-6-astra`, xhigh) | full repo | FINDINGS | 10 (2 S1, 6 S2, 2 S3) |

Both package-only models opened their reports by copying the output-format
placeholder rather than naming themselves (Kimi wrote "Claude (Codex
channel)", GLM wrote "Fable"). The driver removed each stray line and replaced
it with a dated note recording the actual model and token counts; review
bodies were not altered. The handoff's output format has been hardened so the
remaining two channels name themselves explicitly.

## Two-reporter convergence (rule 1: straight to the fix queue)

**C1 — decomposition routines discard per-draw conditional covariance.**
Kimi F1 (S2) + GLM F1 (S2), and the driver's own T2. Both `decompose_model_mcmc`
and `decompose_model_hmc` iterate `for (mean_i, _), ...`
(`bistar_gp/debias.py:131`, `:206`), then report `cov=np.diag(std**2)`
(`:144`, `:225`) with `std` the across-draw spread of means alone; `full_std`
(`:149`, `:230`) has the same defect. The law-of-total-variance term
`mean_d[within-draw var]` is omitted entirely, so every band these routines
produce is too narrow. Kimi adds decisive evidence that the correct
construction was known: the MAP variant `decompose_model` computes the full
covariance including cross-component terms at `:70-84`. Live callers include
`experiments/poster_d58_mauna.py:459`. **Escalates to S1 if any committed
D58-poster band flows through this path.** Driver verification outstanding.

**C2 — the A4 universe firewall is bypassable through the public primitives.**
Kimi F3 (S3) + GLM F2 (S3), and the driver's own T8.
`_assert_candidate_universes_consistent` (`bistar_gp/bms_star.py:480`) is
called only from `run_bms_star` (`:529`), while `compute_G_matrix` (`:368`)
and `soft_transfer` (`:409`) are public and perform the normalization
unguarded. GLM adds that `aggregation_v3.run_robust_aggregation` (`:276`) and
`run_weighted_bms_star` (`:455`) also call `compute_G_matrix` directly. Kimi
adds that the guard passes an all-untagged roster by design (`:497-498`), so
forgetting to tag yields no protection. Both propose moving the assertion into
`compute_G_matrix`, the enforceable boundary.

**C3 — sentinel substitution in the evidence path, with the convergence flag
discarded.** Kimi F2 (S2) + GLM F3 (S3), and the driver's own T11.
`compute_G_at_params` returns `1e6` under a bare `except Exception`
(`laplace_evidence.py:126-127`) and under `LinAlgError/ValueError` (`:136-137`);
`_log_likelihood` returns `-1e10` (`:253`); `_laplace_log_integral` falls back
to the start point with `converged=False` when `minimize` raises (`:268-269`).
Kimi supplies the sharpest evidence, **verified by the driver**: `model_posterior`
discards the flag it is handed, `log_N, _, _, detail = _laplace_log_N(...)`
(`:673`), while `laplace_log_evidence_induced` does propagate it
(`converged=conv`, `:636`). The asymmetry establishes this as a gap rather than
a uniform policy. Kimi further notes a constant sentinel objective makes
L-BFGS-B report success, so the flag alone would not catch every case.

**C4 — `decompose_model_mcmc` maps MCMC draws to parameters by list position.**
Kimi F4 (S3) + GLM F6 (S3). New; not among the driver's named targets.
`bistar_gp/debias.py:103-118` builds `param_list` from `named_parameters()`,
then fills `p.data` from `mcmc_samples[mcmc_keys[i]]` positionally, guarded
only by `if i < len(mcmc_keys)`, silently skipping extras. It computes
`param_names_ordered` (`:106`) and never uses it for matching. The sibling
`decompose_model_hmc` uses name-based `select_hmc_sites`/`apply_hp_value`
precisely to avoid this, and Case E's FIX-7 hardened the same defect class.

**C5 — `soft_transfer` returns a result object that misdescribes itself.**
GLM F7 (S4) + Kimi F6 (S4); different lines, same function and defect class.
The docstring promises class-level averaging, "not sum, to avoid size bias"
(`bms_star.py:418`), while the implementation is
`class_posteriors = instance_posteriors.copy()` with "(1:1 mapping for now)"
(`:465`); `metric_name` is stamped `"unknown"` for the caller to overwrite
(`:467`), which only `run_bms_star` does.

## Single-reporter findings (not yet adversarially checked)

**S-GLM-F4 (S3) — negative-metric penalty in `induced_prior`.** Driver-verified
against source and unusually strong for a single report: `induced_prior.py:235`
sets `g_vals[~finite_mask] = 10 * np.max(g_vals[finite_mask])`, the exact
pattern `bms_star.py:394-404` documents as wrong for negative-capable metrics,
naming `pw_nll` and implementing `penalty = max_finite + 10*(|max_finite|+1)`
instead. `pw_nll_gp` is negative-capable (`metrics_v2.py:149`) and is a
registered, selectable metric. A failed evaluation would become the *best*
score and take the largest induced-prior weight. Mitigation: `compute_induced_prior`
defaults to `pw_kl_vcal` (`:175`); reachability in committed runs is the open
check.

**S-Kimi-F5 (S3) — silent draw loss and partial initialization in
`extract_gp_predictives`.** Driver-verified, and the code is worse than the
finding states. Per-draw failures are dropped by `except RuntimeError: continue`
(`bms_star.py:341-342`) with print-only accounting (`:344`). Per-site failures
are swallowed by `except (IndexError, AttributeError, RuntimeError): continue`
(`:300-303`) — and because `hp_dict[pyro_name] = val` is executed at `:299`
*before* the apply attempt, a draw whose `apply_hp_value` fails still records
the value in the hyperparameters it reports while the model retains its
prior-initialized default. The returned provenance therefore claims a value
that was never applied.

**S-GLM-F5 (S3) — `average_gp_posterior` validates weights but not samples.**
`aggregation_v3.py:70-77` checks caller-supplied weights for finiteness and
never checks `means`/`covs`; a non-finite draw mean propagates into `mu_bar`
and `cov_bar` silently. Offered as the explanation for the driver-observed
RuntimeWarnings at `:77`. Confinement to the prior-stage stress test is
plausible but unenforced.

## Driver verifications performed

Confirmed from source: the `debias.py` covariance discard at all four cited
lines; the firewall call graph; `model_posterior:673` discarding the flag that
`laplace_log_evidence_induced:636` propagates; the positional key mapping and
its unused `param_names_ordered`; the `soft_transfer` docstring/implementation
mismatch and `metric_name="unknown"`; the `induced_prior` penalty against
`bms_star`'s own corrective comment; `pw_nll_gp` negativity; and the
partial-initialization ordering at `bms_star.py:299-303`.

## Outstanding

1. Fable and Codex reports.
2. Repo verification of the `NEEDS-REPO-VERIFICATION` items, chiefly whether
   any committed D58-poster band flows through `decompose_model_hmc` (C1, the
   only candidate S1 so far) and whether any committed artifact reached the
   unguarded primitives (C2) or a negative-capable metric via `induced_prior`
   (S-GLM-F4).
3. Adversarial cross-check of the single-reporter findings, then the final §4
   collation and the author-adjudication ledger.

Nothing is fixed, committed, or merged without the author.


---

# Four-channel supersession (2026-09-06)

## C1 ESCALATED TO S1 BY BOTH REPO-ACCESS CHANNELS, AND SPLIT IN TWO

The escalation condition stated in C1 was met. Both channels opened the
committed D58 artifact and confirmed the defect reaches displayed uncertainty.

**S1-a — the band construction (Fable F1, Codex F1; supersedes C1).** Fable
recomputed the decomposition from the committed `samples.npz` (200 draws,
training-only loader, no new inference) and reproduced the committed
`comp__*__std` and `full_std` fields to within 7.1e-13, establishing a
like-for-like comparison, then applied the law of total variance. In ppm, over
the 500-point grid: the trend and seasonal component bands are roughly 14x too
NARROW (0.650 and 0.648 committed against 9.34 honest), medium_term about 5x
too narrow, and the full-GP band labelled "95% CI" about 9x too narrow at the
median. The Moderate and Believer "truth" bands run the other way, about 7x
too WIDE. Mean curves are unaffected. Codex independently opened
`runs/poster_d58/fit_full461_seed0/decomposition.npz` and confirmed that all
three stored component standard deviations equal exactly the population
standard deviation of their 200 conditional-mean rows, and that the artifact
does not retain conditional covariances, so the missing variance cannot be
recovered from the saved decomposition alone.

**S1-b — the grouping construction (Codex F2, also raised inside Fable F1).**
`experiments/bistar_debias_mauna_loa.py:97` forms grouped "truth" uncertainty
as the sum of component variances under an explicit "independent components"
comment, dropping every inter-component cross-covariance. Codex quantified the
internal contradiction on the committed artifact: the grid mean of the summed
variances is 0.003969823126724952 against 0.0000017302240418020973 for the
variance of the summed stored rows, a factor of 2294.4 (normalized
coordinates; the latter agrees exactly with stored `full_std` squared). Codex
supplies the decisive invariant: assigning every component to truth, as the
Believer interpretation does, must reproduce the full posterior band, and this
implementation cannot. Adding S1-a's missing marginal variances does not fix
S1-b.

**Blast radius, per Fable and consistent with Codex.** The MANUSCRIPT IS NOT
AFFECTED: Case E deliberately bypassed these routines
(`experiments/toy_debias_demo.py:396-435` retains per-draw variances and takes
the joint posterior from summed blocks), no paper number derives from
`debias.py`, and the toy poster figures used
`experiments/honest_band_decomposition.py`. The affected artifacts are the
four committed D58 Mauna cards (`runs/poster_d58/fit_full461_seed0/figures/
card6..card8`, pinned byte-identically into `poster/assets/d58/` under
`FIGURES.sha256`). Re-rendering requires no new inference.

## Correction to the driver's own handoff

Codex found target T2 misnamed the affected functions. The defect is in
`decompose_model_mcmc` (`debias.py:131`) and `decompose_model_hmc` (`:206`);
the MAP wrapper `decompose_model` is clean and computes the full covariance
from summed kernel blocks at `:70-84`, explicitly retaining inter-component
cross-covariance. The handoff has been corrected with a dated note. Kimi had
already used the MAP variant's correctness as evidence that the right
construction was known; Codex established that the handoff's wording was the
error.

## Codex substitution ratification (discharges the PR #40 and #41 ledger item)

Codex ratified the substituted work of the lock period, with two refinements
it declined to ratify as stated:
- Synthesis SC1, SC2, SC3, SC5: ratified, including the driver's mechanical
  verification. It declines to ratify any implication that use of `avg_gp`
  alone establishes a nonzero gap in the reported Case B/E6 numbers, since
  their retained predictive count is one. The frozen-notation amendment
  remains an author decision.
- Case E: ratified in full, including the three rejected single-reporter
  findings F2, F5, F6, which it would also reject as mandatory fixes. It
  refines the driver's jitter-probe refutation (the script performs another
  composite factorization, but on the same matrix, so no different solve is
  left unprobed) and cautions that "grid-averaged correlation" should be read
  as a correlation formed from mean total variances rather than the arithmetic
  average of pointwise correlations, which is about -0.712.

## Still outstanding

1. Full §4 collation across all four channels: convergence counting for the
   remaining ~20 findings, adversarial cross-check of every single-reporter
   item under the default-refuted rule, and the author-adjudication ledger.
2. Author decisions: the D58 poster-card correction path (the poster is a
   frozen, pinned artifact under the author's record process), and whether the
   presented poster used the affected cards.
