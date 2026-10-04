# Project review, 2026-09-26

Five independent channels review the current code (fix-branch head `ddf8c9d`,
PR #42) and the project state (seven unmerged branches, manuscript apparatus,
records). Governing brief: `docs/paper-sie-jmp/prompts/project-review-2026-09-26.txt` (untracked manuscript apparatus; a verbatim copy is committed here as `brief_project-review-2026-09-26.txt`)
(all channels receive it verbatim plus a channel override naming their output
file and scratch directory). Map: `project_map.md`.

| Channel | Access | Output file | Status |
|---|---|---|---|
| Fable 5.1 (this session; also the author of fix passes 1/1b/1c, disclosed) | full repo | `fable51_review.md` | landed: code APPROVE, project NOT READY |
| Codex gpt-6-astra xhigh | full repo | `codex_astra_review.md` | landed: code REVISE, project NOT READY |
| Opus (Claude Code subagent, model `opus`; the user requested Opus 5.5) | full repo | `opus_review.md` | landed: code REVISE (one S1), project NOT READY |
| Kimi K3 (`moonshotai/kimi-k3`, OpenRouter) | package-only, two packages (code, project) | `kimi_k3_review_code.md`, `kimi_k3_review_project.md` | landed: code REVISE, project NOT READY |
| GLM 5.3 (`z-ai/glm-5.3`, OpenRouter) | package-only, same two packages | `glm_5_3_review_code.md`, `glm_5_3_review_project.md` | landed: code REVISE, project NOT READY |

Package-only inputs are in `bundle/` (`package_code.md`, `package_project.md`,
identical for both models apart from the channel label). Collation follows
HANDOFF-cases.md section 4 after all channels land: two-reporter findings go
to a fix queue, single-reporter findings get an adversarial cross-check with
a default of refuted, and S1/S2 or BLOCKER items go to the author.

Synthesis: `SYNTHESIS.md` revision 1.2 (all five channels; Opus's single-reporter claims verified by independent regeneration; section 9 = Codex Astra's plan check, verified; section 10 = Opus 5.5's check of Astra's amendments, verified, and the final adopted plan). Plan checks: `codex_astra_plan_check.md`, `opus_plan_check.md`.

Committed on `fix/code-review-2026-09` on 2026-09-26 as the round's record; the raw OpenRouter
response JSONs (`*.raw.json`, driver-side provenance of the package-only calls) stay local.
Probe scripts and logs named in the reviews were in the session scratchpad and are ephemeral;
every finding they supported is restated with its evidence in the channel files and `SYNTHESIS.md`.

Decision sheet: `DECISION_SHEET.md`, written 2026-09-26 and cast by the author on 2026-10-03
(D69's cast update). The cast followed read-only consultations of Codex gpt-6-astra (xhigh) and
Fable on one brief, recorded in `sheet_consult/` (`brief.md`, `astra.md`, `fable.md`, and
integrity snapshots taken before and after, unchanged). Fix pass 2a's record is
`fix2a_report.md` with `fix2a_review/` (D70).
