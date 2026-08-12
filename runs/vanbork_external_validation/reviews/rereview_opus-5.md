# Re-review — Opus 5 (raiser of AO1/AO9/AO2/AO3/AO6/AO7/AO8/AO10/AO11), repo access, changed hunks of 7b653cf

REREVIEW-AO1: RESOLVED
- "the artifact's consistency check confirms that identity" is deleted; §3.4:113-119 now states the identity analytically ("converges by construction"), cites 0.696 at τ=0.1 to the E7 `results.json` (verified: 0.6960704748508468), and attributes 696/1000 to the committed D18 record.
- The D18 attribution is metric-correct: committed `Notes/DECISIONS.md:923` carries "SIR hard fractions at n_pred=1000: 0.696 toy_elicited" inside D18 finding 5, which is the `kl_forward` finding, so the section is not borrowing a `pw_kl_vcal` fraction.
- [^3] now names the D18 record and describes the README as merely "noting" the correspondence, which is exactly what `runs/e7_convention_sensitivity/README.md:20-27` does. Every number in the paragraph now has a committed source.

REREVIEW-AO9: RESOLVED
- The Target A row reads "Shipped `normalize_per_draw=True` semantics (per-draw minimum shift)", so it no longer implies a `soft_transfer(...)` call the artifact never makes.
- The added prose is accurate against `bistar_gp/bms_star.py:439-454` (row-min subtraction, single global shift, one normalization) versus the Eq. 4 rowwise posterior route.
- "They coincide in the τ-to-zero unique-winner limit" checks out in `results.json`: `rows_shipped_npd_true` and `rows_perdraw` differ at τ=1e-3 (0.40020 versus 0.39935) and agree at 0.4/0.6 from τ=1e-4 down.

REREVIEW-AO2: RESOLVED
- Mapping row 3's qualification now states that their Eq. 4 per-atom quantity is a Bayesian posterior under an infinite-data idealization while ours is a Boltzmann softmax as τ approaches zero, and that Target A agreement follows because both collapse to the same hard nearest-model assignment.
- That matches the source: the kb ingest records their infinite-size-experiment requirement and that posterior model probability goes to 0/1 per atom, which is the load-bearing step the table previously omitted.

REREVIEW-AO3: RESOLVED
- The table row is now "Their closed form, evaluated at double precision", and the body states the paper prints 7.96, 1.50 and approximately 0.84, with the printed-density quotient 0.841438 (arithmetic confirmed: 7.96/9.46 = 0.8414376), so the six-decimal target is no longer presented as published.
- The error claim is rescoped to "against that evaluated limit", and D65 is aligned ("their closed form evaluated at double precision (0.841420 to six decimals)").
- D60's looser wording stays byte-untouched by design; the D60/D61 block (committed lines 5720-5825) hashes identically across 31a9258..7b653cf.

REREVIEW-AO6: RESOLVED
- Body and [^4] now read "stays at or above 0.93 across all evaluated n", so 0.992 at n=50 no longer falls outside the stated band, and D65 carries the same wording.
- The weakened bound is what D17 supports (0.992 at the p3/canonical n=50 arm; "0.93–0.99 across all n").

REREVIEW-AO7: RESOLVED
- The data-prior atom is now ψ* ("a data prior that places a point mass at ψ*=1/2"), matching `00-notation.md:9` and the script's `psi_star`.
- The point-prior identity Ḡ(φ)=G(ψ*,φ) was added and the display switched to Ḡ_M'', removing the G-versus-Ḡ clash with mapping row 4. One residual wording issue introduced by this hunk is reported below.

REREVIEW-AO8: RESOLVED
- §3:7 now reads "the induced-prior and soft-transfer machinery", consistent with §3.5, the run README and D60. The reflow introduced no new style problems.

REREVIEW-AO10: RESOLVED
- `import fit_method_metric_comparison as fmc` is gone from `experiments/e7_convention_sensitivity.py`; it was the file's only `fmc` reference.
- The removal is provably behavior-neutral: `experiments/prior_sensitivity_study.py:110` imports the same module and uses `fmc.METRICS` at :687 and :690, and e7 imports `pss` first, so the module (and the `bistar_gp.metrics_v2` registration it triggers) still loads. That is why the rerun reproduced the artifact.
- Byte identity verified independently: no `runs/` path appears in `git diff --name-only 31a9258..7b653cf`, and `runs/e7_convention_sensitivity/results.json` hashes to 0b3e2924ec857e4662c7242f326e26960d5d7621adb3145552eadc395f8db22c, exactly the fix report's value. Note the fix is cosmetic only; the withdrawn-arm module remains a live transitive dependency through `pss`, and the fix report correctly does not claim otherwise.

REREVIEW-AO11: RESOLVED
- §3.4 now states that all three variants use the same G matrix from one SIR realization at n_pred=1000, so the movements are paired differences rather than differences of independent estimates.
- Accurate to the script (`G = G_by_metric[metric]` from a single `pss._sir_bms` call, all variants applied to that matrix) and it introduces no number outside `results.json` ("n_pred": 1000).

NEW defects introduced by the changed hunks

N1. [S4] [docs/paper-sie-jmp/03-case-A-external-validation.md:58-63] The FIX-6 hunk writes "Both models use the same Bernoulli family, so they share the local curvature Ḡ_M''(θ*)" — the newly added M subscript indexes by model the very quantity the sentence asserts is model-independent, which is the step the cancellation argument depends on. The pre-fix unsubscripted form did not have this tension. Fix: keep Ḡ_M'' in the display for consistency with mapping row 4 and write the cancellation sentence as "so Ḡ_x''(θ*)=Ḡ_z''(θ*)", or drop the subscript in both places.

N2. [S4] [docs/paper-sie-jmp/03-case-A-external-validation.md:57-58] Same hunk: "the common candidate optimum θ*=ψ*=1/2" equates a candidate parameter with a data pattern, though `00-notation.md:9` defines ψ as a distribution over outcomes, not a scalar. The shorthand is used consistently elsewhere in the example, so this is cosmetic. Fix: "the candidate optimum θ*=1/2, which coincides with the data-prior atom".

N3. [S4] [docs/paper-sie-jmp/03-case-A-external-validation.md:108-112] The FIX-9 sentence is placed between the anchor claim and the winner claim, so "the reported movements" forward-references numbers that appear two sentences later. Fix: move the paired-differences sentence to just after "the Sin+Linear weight changes from 0.441 to 0.513".
