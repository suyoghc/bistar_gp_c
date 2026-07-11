# D19 pre-registration addenda (append-only)

Amendment record for the D19 Mauna Loa pre-registration, governed by
`docs/plan-d19-mauna.md` §6.16: the frozen plan (commit a077c6e) is never
edited in place; every prereg-referenced value produced after the M1 freeze
lands here as a numbered, dated, reasoned addendum, in a tracked commit
BEFORE the stage it affects. Later addenda never modify earlier ones.

---

## v1.1 — A9 canonical data hash + vendored artifact (M2a) — 2026-07-11

**Prereg anchor:** §6.2 ("extended to a canonical year/month/co2 hash at M2a
per A9"), §6.15 addendum protocol, decision A9 (§7). Landed with the M2a
infrastructure PR, before any pilot result exists (§6.16 ordering satisfied).

**Licence check (A9 fork):** OpenML dataset 41187 (`mauna-loa-atmospheric-co2`,
version 1) is licensed **CC0** (OpenML API record, checked 2026-07-11;
upstream md5 `fe3355c5e4f3cafc49adc4487806b9a1`). Licensing therefore permits
the vendored-artifact branch of A9, which is the one implemented.

**Vendored artifact:** `bistar_gp/datasets/mauna_loa_co2_openml41187.csv` —
the full 2225-row raw record, all seven columns
(`year, month, day, weight, flag, station, co2`), written from a fresh
`fetch_openml(data_id=41187)` frame with exact float round-trip (verified:
identical hashes and byte-identical monthly aggregation from the CSV and from
a live fetch). The non-analysis columns (`day, weight, flag, station`) are
retained because the Stage-0 era/source transcription (§8) reads the station
column; no analysis touches them.
File sha256: `6e50ccd10d6132da6df272f5e2b30d2f02c5134cda6bbd3a1b2b69fbe48d30eb`.

**Canonical hash (the prereg-referenced value):** sha256 over the
concatenated float64 little-endian bytes of the `year`, `month`, and `co2`
columns, in that column order, in fetched row order, over the FULL 2225-row
raw record:

```
MAUNA_CANONICAL_SHA256 =
5bcdc813b4c3b570c9947acfaa0d3ff8cb5f89094b3e4e5121f72535a0cc0910
```

The byte-serialization convention (`np.ascontiguousarray(col.astype(float)
.values).tobytes()`) is the same one the M1 benchmark used for the co2-only
hash, so the two pins are directly comparable. The M1 pin
`7e301efd6dbd2b4007723368aa69ebd2259ea6aa1d431650c209df181f244cb9`
(§6.2) stays recorded and is re-verified at every load for continuity.

**Runtime enforcement:** `bistar_gp/data.py` verifies, at every Mauna load
and for both sources (vendored CSV and OpenML retrieval): the canonical hash,
the co2-only continuity hash, the raw row count 2225, the post-filter count
2225 (the §6.2 `co2 > 0` filter is asserted to remain a no-op), the monthly
count 521, and — at the prereg cutoff rule (`test_years = 5.0`) — the split
counts 461/60. Any mismatch is a hard `RuntimeError`; no fallback data path
exists (the pre-A9 synthetic fallback is removed).

**Holdout-seal note (§6.6):** computing the canonical hash necessarily
streams test-era rows; that is the PROVENANCE LAYER verifying artifact
identity, which the seal permits. Study-facing code uses the new
training-only entry point (`load_mauna_loa_training`), which never returns,
logs, or persists test y values; split metadata (461/60, cutoff rule) remains
available, as §6.6 explicitly permits.

**What this addendum does NOT change:** no threshold of §6.15, no gate of
§6.7, no arm definition, no candidate set. The remaining
implementation-coupled §6.15 values stay owed at M2b (E1 tolerances, A6
budgets, A5 fallback) and M2c (S2/S3/G-toy tolerances, divergence-clustering
predicate, M1 overlap diagnostic, corrected profile band masses).
