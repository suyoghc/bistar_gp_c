# Re-review — Codex gpt-5.6-sol xhigh (raiser of AC5-in-F-A1, AC2-in-F-A2), changed hunks of 7b653cf

REREVIEW-F-A1: RESOLVED

- The section now attributes 0.696 at \(\tau=0.1\) to E7 `results.json`, which records 0.696070… for Sin+Linear.
- The independent 696/1000 hard fraction is explicitly attributed to committed D18.
- The limiting identity is presented as analytic; the section no longer claims E7 contains an artifact-backed consistency check.

REREVIEW-F-A2: RESOLVED

- The Target A row now describes shipped `normalize_per_draw=True` semantics without implying the shipped function was directly called.
- The added prose correctly distinguishes per-row minimum shifting followed by pooled normalization from Eq.-4 rowwise posterior normalization followed by averaging.
- Agreement is correctly limited to Target A’s zero-temperature, unique-winner limit. The D60-side addendum remains in the author ledger under the endorsed immutable-record policy.

NEW-DEFECTS: NONE introduced by the changed hunks.