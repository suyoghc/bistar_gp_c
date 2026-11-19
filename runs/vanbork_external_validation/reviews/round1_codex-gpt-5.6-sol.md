# Round-1 review — Codex gpt-5.6-sol xhigh, fresh session, repo access

REVISE

1. [severity S2] [docs/paper-sie-jmp/03-case-A-external-validation.md:104] `kl_forward` results appear in the main Case A section — labeling them “appendix-only” does not satisfy W1 — remove the detailed paragraph and retain only an appendix cross-reference.

2. [severity S2] [Notes/DECISIONS.md:5762] D60 says `normalize_per_draw=True` implements the Eq.-4-correct convention — the shipped flag subtracts row minima but normalizes only after pooling, unlike expected-posterior aggregation’s per-row normalization; they coincide here only in the unique-winner, zero-temperature limit — distinguish the two conventions explicitly.

3. [severity S2] [Notes/DECISIONS.md:5776] D60 includes Mauna material — §0 prohibits Mauna Loa material of any kind on this branch — delete both Mauna references without adding replacement analysis.

4. [severity S3] [Notes/DECISIONS.md:5777] Equal-weight draws are claimed to make the conventions differ “far less” — equal weighting does not ensure this, and E7’s equal-weight `kl_forward` result shows approximately 0.696 maximum movement — remove the inference and describe the movement as untested at D60.

5. [severity S3] [docs/paper-sie-jmp/03-case-A-external-validation.md:107] The 696/1000 hard-win fraction, passed consistency check, and outlier-draw attribution are presented as artifact-backed — the E7 script does not persist hard-win fractions, run an explicit consistency assertion, or emit outlier diagnostics into `results.json` — remove those claims from the section and associated D61/D65/README prose, retaining the JSON-backed 0.696 aggregation result.

6. [severity S4] [Notes/DECISIONS.md:5748] D60 uses prohibited arrow glyphs repeatedly — this violates the explicit prose-style rule — rewrite the limits and implications in words throughout D60.