# HANDOFF — remaining paper cases, one branch each

2026-08-11. Governs execution of the four case-study work packages for the JMP
special-issue manuscript (plan: `~/.claude/plans/should-we-split-these-
synchronous-wand.md`; skeletons in `docs/paper-sie-jmp/`). Implementation by
**Codex `gpt-5.6-sol`, reasoning `xhigh`** (the A7/D56b review-protocol model).
Reviews by four independent models with cross-verification (§4).

## 0. Global protocol (applies to every case)

**Branching.** One branch per case off `main`:
`paper/case-a-vanbork`, `paper/case-b-occam-dial`, `paper/case-c-haaf`,
`paper/case-d-mopen`. Work in this clone (local-only files such as
`Notes/WRITEUP_DECISIONS.md` are gitignored but present in the working tree —
Codex may READ them, must never `git add` them).

**Hard constraints (repeat verbatim in every Codex prompt):**
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
  no "lives/sits" for abstracta; minimal em-dashes (see repo CLAUDE.md +
  user's global rules quoted in `docs/paper-sie-jmp/00-notation.md`).
- Every reported number must be regenerable from a named `experiments/`
  script into a `runs/` artifact; each case commits a same-commit
  `Notes/DECISIONS.md` entry (next free D number).
- Commit scope per branch: `experiments/` script(s), `docs/paper-sie-jmp/`
  section, `Notes/DECISIONS.md` entry, and (deliberately, if evidence-worthy)
  the `runs/` JSON — never figures over 2 MB, never gitignored Notes files.

**Canonical implementation invocation** (pipe the case prompt via stdin):

```bash
git checkout main && git checkout -b paper/case-X-<slug>
cat docs/paper-sie-jmp/prompts/case-X-impl.txt | codex exec --yolo \
  --skip-git-repo-check -m gpt-5.6-sol \
  -c 'model_reasoning_effort="xhigh"' -o /tmp/case-X-impl.txt -
```

The driver session composes `case-X-impl.txt` from §2's work order + §0's
constraints, reads `/tmp/case-X-impl.txt`, verifies (§3), then runs §4.

## 1. Sequencing and blockers

| Case | Status | Blocker |
|---|---|---|
| B (occam dial) | UNBLOCKED | — |
| C (Haaf) | UNBLOCKED for build | "sharpest criticism" framing stays provisional until Kellen & Klauer 2020 PDF is read (WANTED.md) |
| D (M-open) | UNBLOCKED | verify what `experiments/practice_EvansEtAL/run.py` already outputs before writing new regret code |
| A (van Bork) | **BLOCKED on the D60/D61 fork** (author call: canonical aggregation convention) | draft everything except the fork paragraph; leave `[FORK-DECISION-PLACEHOLDER]` |

Recommended order: B and C in parallel, then D, then A.

## 2. Work orders

### Case B — `paper/case-b-occam-dial`
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

### Case C — `paper/case-c-haaf`
Scope: the one real build. `experiments/haaf_nested_constraint.py`:
1. Candidate pair differing ONLY by a parameter-region constraint within one
   functional form (mirror Haaf & Klaassen's ordinal-constraint setting):
   free Sin+Linear vs slope-constrained (b ≥ 0) Sin+Linear, both via
   `bistar_gp/candidates.py` `_fit_mle` with bounds.
2. Constraint-consistent synthetic data (true b > 0), N=20 convention,
   seeded.
3. BMS* scoring on the validated path: reuse
   `experiments/prior_sensitivity_study.py` stage-IS machinery exactly as
   `experiments/e7_convention_sensitivity.py` does (imports, not copies);
   report pooled AND expected-posterior variants (fork-agnostic table).
4. PSIS-LOO head-to-head on the identical data via `arviz` (add to
   requirements only if absent), for the same two candidates fitted as
   Bayesian models with weakly-informative priors — document those priors;
   they exist only on the LOO side of the comparison.
5. Section `05-case-C-nested-constraints.md` from the stub. Output
   `runs/haaf_nested_constraint/`.
Acceptance: the comparison table shows, on identical data, what LOO awards
the constrained candidate vs what BMS* awards it; whichever way it comes out
is reported (a null result is reportable); DECISIONS entry present.

### Case D — `paper/case-d-mopen`
Scope: regret curves + section; E8b optional module.
1. FIRST inventory `experiments/practice_EvansEtAL/` (`run.py`, diag scripts,
   `data/`): if regret-per-trial is already computed, reuse; else add
   `experiments/regret_curves_mopen.py` implementing
   regret_θ(t) = E_draws|μ_GP(t) − μ_θ(t)| per the formula in
   `kb/Wiki/Limits Diagnostics and Open Questions.md`, on that experiment's
   existing fitted artifacts (no new HMC).
2. Section `06-case-D-mopen-calibration.md`: the decline-is-correct argument
   (Navarro, Pitt & Myung 2004 digest in
   `kb/Digests/Clippings/data_prior_regimes/`), divergence magnitudes as the
   absolute inadequacy read, regret curves showing WHERE candidates fail.
3. OPTIONAL `experiments/e8b_transform_space.py` (semi-log + log-log refit,
   lognormal noise correction) — implement behind `[E8B-PLACEHOLDER]` blocks
   in the section so the author can excise cleanly.
Acceptance: regret figure regenerates from existing artifacts; section
drafted; DECISIONS entry present.

### Case A — `paper/case-a-vanbork`
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

## 3. Driver-session verification (before any review)

Per branch: `python experiments/<new script>.py` reruns clean from the branch
tip; figures/JSON regenerate (numbers within pinned tolerances where the
script pins them); `git diff main --stat` contains only the §0 commit scope;
DECISIONS entry number does not collide (check `grep -c '^## D' Notes/DECISIONS.md`).

## 4. Review protocol — four models, independently, then cross-verify

For each branch, after §3 passes, obtain FOUR independent reviews. Each
reviewer receives the same package: `git diff main` for the branch, the case's
section file, the run README(s), and §0's constraints. Reviewers must NOT see
each other's outputs in round 1.

| Reviewer | Channel | Invocation sketch |
|---|---|---|
| GPT 5.6 sol (xhigh) | Codex CLI, fresh session, review-only prompt | same canonical command, prompt = review template below, `-o /tmp/caseX-rev-codex.txt` |
| Opus 5 | Claude in-session subagent (Agent tool, model=opus) or `claude -p --model opus` once CLI OAuth is restored | review template |
| Gemini | `gemini` MCP server (`gemini-analyze-code` / `gemini-analyze-text` on the diff) when connected | review template |
| Kimi K3 | author's Kimi channel (no CLI configured in this repo — **author supplies the command or runs it by hand**; template below is paste-ready) | review template |

Review template (all four):

```
Review the attached branch diff for the BI*/BMS*-GP paper case <X>.
Verdict: APPROVE or REVISE. Findings as a numbered list:
[severity S1-S4] [file:line] claim — why it is wrong — concrete fix.
Check specifically: (1) constraint compliance [paste §0 list]; (2) numerical
claims vs the runs/ JSONs; (3) statistical correctness of the method logic;
(4) prose style rules; (5) anything the section claims that the artifacts do
not support. Do not propose scope expansions.
```

**Cross-verification rules:**
1. Collate findings across the four reviews. A finding reported by ≥2
   reviewers is presumed real → fix queue.
2. A finding reported by exactly ONE reviewer is adversarially checked: send
   it to one OTHER reviewer (rotate; never the originator) with "attempt to
   refute this specific finding against the artifacts; default to refuted if
   the evidence is ambiguous." Survivors → fix queue; refuted → logged as
   rejected with the refutation.
3. Verdict conflicts (some APPROVE, some REVISE) are decided by the fix
   queue, not by vote: empty queue → APPROVE stands; non-empty → REVISE.
4. Fixes implemented by Codex (same canonical invocation, prompt = fix queue
   + diff); then ONE re-review round of the changed hunks only, by the two
   reviewers who raised the surviving findings. No third round — residuals
   escalate to the author.
5. Author adjudicates anything the protocol cannot settle, and always
   adjudicates S1/S2 findings touching statistical claims.

**Record-keeping per branch:** review outputs under
`runs/<case run dir>/reviews/` (raw reviewer outputs + a `VERDICTS.md`
summarizing findings, refutations, fixes, final verdict). The branch's
DECISIONS entry gets a one-line review-outcome addendum before merge is
proposed. Merges are proposed to the author; nothing merges autonomously.

## 5. Out of scope for all branches

The D60 fork decision (author). Kellen & Klauer PDF acquisition. Overleaf
conversion. Any Mauna computation. Poster files. `bistar_gp/` API changes.
