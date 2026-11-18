# Re-review — Codex gpt-5.6-sol xhigh (raiser of F1, F2, C3), changed hunks of c15a65f

REREVIEW-F1: RESOLVED

- The committed [README](/Users/sc8918/Documents/GitHub/bistar_gp_c/runs/occam_dial/README.md:49) now preserves the complete resolution for clean checkouts.
- Its resolution paragraph is byte-identical to the local `kb/Wiki/REVIEW_AND_VET.md` paragraph.
- D62 explicitly records the mirror because `kb/` remains gitignored.

REREVIEW-F2: RESOLVED

- The E6 script performs one 100,000-sample IS sweep per model for seeds 0, 1, and 2; the regenerated JSON records all three.
- Sinusoidal crossings span 1.382–1.584, with seed-0 ESS-shift roots 1.392–1.563; these values reconcile with the recorded ESS and log-Z brackets.
- The [paper](/Users/sc8918/Documents/GitHub/bistar_gp_c/docs/paper-sie-jmp/04-case-B-occam-dial.md:79) now reports the supported summary as `τ ≈ 1.5`, exposes the seed/grid/ESS uncertainty, and removes the unsupported six-decimal claim.

REREVIEW-C3: RESOLVED

- [D62](/Users/sc8918/Documents/GitHub/bistar_gp_c/Notes/DECISIONS.md:5831) now accurately lists the local tables, diagnostics, and extracted scripts.
- It correctly says those untracked artifacts are not the authoritative committed data source.
- It also accurately describes `delta_table.md` as an optional parsed input enforcing the 0.003 same-seed assertion gate.

NEW-DEFECTS: NONE.