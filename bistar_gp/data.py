"""
Synthetic data generators and real dataset loaders.

Mauna Loa loading is gated by the D19 data-provenance rules (decision A9,
docs/plan-d19-mauna.md sections 0 and 6.2; DECISIONS.md D20): the raw record is
a vendored, checksummed copy of OpenML data_id=41187 (licence CC0), verified at
every load against pinned hashes and row counts, with a hard failure on any
mismatch. The pre-A9 loader had a dead synthetic fallback (a fetch failure
reached `np.argsort(x_all)` with `x_all` unbound), an unreachable second
`except` clause, and no runtime identity check; all three are fixed here.
"""

import hashlib
from pathlib import Path

import torch
import numpy as np

torch.set_default_dtype(torch.float64)


# ── Mauna Loa provenance pins (A9; prereg §6.2 + addendum v1.1) ──────────────
#
# Canonical raw-record identity: sha256 over the concatenated float64 bytes of
# the year, month, and co2 columns (in that column order, fetched row order,
# full 2225-row raw record). Recorded as pre-registration addendum v1.1 in
# docs/prereg-addenda-d19.md. Reading the full record here — including
# test-era rows — is the PROVENANCE LAYER acting under the §6.6 seal
# semantics: identity verification only, no analysis value is derived from it.
MAUNA_OPENML_DATA_ID = 41187
MAUNA_VENDORED_CSV = Path(__file__).resolve().parent / "datasets" / "mauna_loa_co2_openml41187.csv"
MAUNA_CANONICAL_SHA256 = "5bcdc813b4c3b570c9947acfaa0d3ff8cb5f89094b3e4e5121f72535a0cc0910"
# M1 continuity pin (plan §6.2): sha256 over the co2 column alone.
MAUNA_CO2_SHA256 = "7e301efd6dbd2b4007723368aa69ebd2259ea6aa1d431650c209df181f244cb9"
MAUNA_RAW_ROWS = 2225
MAUNA_MONTHLY_ROWS = 521
MAUNA_TRAIN_ROWS = 461  # at the prereg cutoff rule max(x) - 5.0 years
MAUNA_TEST_ROWS = 60


def generate_toy_data(n_points=20, x_range=(-10.0, 10.0), noise_std=0.5,
                      bias_slope=0.25, seed=42):
    """
    Thesis toy data: sin(x) + slope*x + noise.
    Returns (x, y, info_dict_with_ground_truth).
    """
    if seed is not None:
        torch.manual_seed(seed)
        np.random.seed(seed)

    x = torch.linspace(x_range[0], x_range[1], n_points).double()
    true_signal = torch.sin(x)
    bias = bias_slope * x
    noise = noise_std * torch.randn_like(x)
    y = true_signal + bias + noise

    info = {
        "true_signal": true_signal.numpy(),
        "bias": bias.numpy(),
        "combined": (true_signal + bias).numpy(),
        "noise_std": noise_std,
        "bias_slope": bias_slope,
    }
    return x, y.double(), info


def _mauna_raw_frame(source="vendored"):
    """Return the full raw OpenML 41187 record as a DataFrame.

    source="vendored" reads the checksummed repo copy (CC0; no network).
    source="openml" retrieves the same record deterministically by data_id via
    sklearn and verifies it against the same pins — there is deliberately no
    synthetic fallback (A9): a failure raises instead of silently substituting
    data of a different provenance.
    """
    import pandas as pd

    if source == "vendored":
        if not MAUNA_VENDORED_CSV.exists():
            raise RuntimeError(
                f"vendored Mauna Loa dataset missing at {MAUNA_VENDORED_CSV}; "
                "restore it from the repo or use source='openml'")
        return pd.read_csv(MAUNA_VENDORED_CSV)
    if source == "openml":
        try:
            from sklearn.datasets import fetch_openml
            bunch = fetch_openml(data_id=MAUNA_OPENML_DATA_ID, as_frame=True)
        except Exception as e:
            raise RuntimeError(
                f"OpenML fetch of data_id={MAUNA_OPENML_DATA_ID} failed; no "
                "fallback exists (A9). Use source='vendored'.") from e
        return bunch.frame
    raise ValueError(f"unknown source {source!r}; expected 'vendored' or 'openml'")


def _verify_mauna_provenance(df):
    """A9 runtime gate: hard failure unless the raw record matches the pins.

    Verifies the raw row count, the canonical year/month/co2 sha256, and the
    M1-era co2-only sha256 (continuity with the value frozen in plan §6.2).
    Returns the resolved (year_col, month_col, co2_col) names.
    """
    cols = {c.lower(): c for c in df.columns}
    year_col = cols.get("year")
    month_col = cols.get("month")
    co2_col = cols.get("average") or cols.get("co2")
    if year_col is None or month_col is None or co2_col is None:
        raise RuntimeError(
            f"Mauna Loa raw record misses expected columns; got {list(df.columns)}")
    if len(df) != MAUNA_RAW_ROWS:
        raise RuntimeError(
            f"Mauna Loa raw record has {len(df)} rows; pinned {MAUNA_RAW_ROWS} "
            "(prereg §6.2 requires re-pinning before any use of deviating data)")

    def col_bytes(col):
        return np.ascontiguousarray(df[col].astype(float).values).tobytes()

    canonical = hashlib.sha256(
        col_bytes(year_col) + col_bytes(month_col) + col_bytes(co2_col)).hexdigest()
    if canonical != MAUNA_CANONICAL_SHA256:
        raise RuntimeError(
            "Mauna Loa canonical year/month/co2 sha256 mismatch: "
            f"{canonical} != pinned {MAUNA_CANONICAL_SHA256} (addendum v1.1)")
    co2_hash = hashlib.sha256(col_bytes(co2_col)).hexdigest()
    if co2_hash != MAUNA_CO2_SHA256:
        raise RuntimeError(
            "Mauna Loa co2-column sha256 mismatch: "
            f"{co2_hash} != pinned {MAUNA_CO2_SHA256} (plan §6.2)")
    return year_col, month_col, co2_col


def _mauna_monthly_arrays(source="vendored"):
    """Provenance-verified raw record aggregated to sorted monthly means.

    Returns (x_all, y_all) with x in calendar years (year + (month-1)/12) and
    y the monthly-mean co2 in ppm, sorted by x. The aggregation is the same
    operation sequence the pre-A9 loader used, so downstream values are
    byte-identical (the D19 scorecard regenerates its frozen JSON exactly).
    """
    df = _mauna_raw_frame(source)
    year_col, month_col, co2_col = _verify_mauna_provenance(df)

    df = df.copy()
    df[co2_col] = df[co2_col].astype(float)
    df[year_col] = df[year_col].astype(float)
    df[month_col] = df[month_col].astype(float)

    # Prereg §6.2 filter "co2 > 0": part of the frozen data definition, and a
    # no-op on the pinned record (drops 0 of 2225 rows; enforced below so a
    # future record that made it bite would fail loudly instead of silently
    # changing the sample).
    df = df[df[co2_col] > 0]
    if len(df) != MAUNA_RAW_ROWS:
        raise RuntimeError(
            f"co2 > 0 filter dropped rows ({len(df)} left of {MAUNA_RAW_ROWS}); "
            "the pinned record makes this filter a no-op — re-pin before use")

    # Aggregate to monthly means (handles the weekly raw cadence).
    df["year_month"] = (df[year_col].astype(int).astype(str) + "-"
                        + df[month_col].astype(int).astype(str).str.zfill(2))
    monthly = df.groupby("year_month").agg({
        year_col: "first",
        month_col: "first",
        co2_col: "mean",
    }).reset_index()

    x_all = monthly[year_col].values + (monthly[month_col].values - 1) / 12.0
    y_all = monthly[co2_col].values
    if len(x_all) != MAUNA_MONTHLY_ROWS:
        raise RuntimeError(
            f"monthly aggregation gave {len(x_all)} months; pinned {MAUNA_MONTHLY_ROWS}")

    idx = np.argsort(x_all)
    return x_all[idx], y_all[idx]


def _load_mauna_loa_split(normalize=True, test_years=5.0, source="vendored"):
    """Shared split + normalization behind both public Mauna loaders.

    Materializes the train/test split mechanically (permitted and disclosed
    under the §6.6 seal semantics); which arrays a caller may receive is
    decided by the public entry points. Normalization statistics come from the
    training span only, exactly as before A9.
    """
    x_all, y_all = _mauna_monthly_arrays(source)

    cutoff = x_all.max() - test_years
    train_mask = x_all <= cutoff

    x_train, y_train = x_all[train_mask], y_all[train_mask]
    x_test, y_test = x_all[~train_mask], y_all[~train_mask]

    if test_years == 5.0 and (len(x_train) != MAUNA_TRAIN_ROWS
                              or len(x_test) != MAUNA_TEST_ROWS):
        raise RuntimeError(
            f"prereg split counts violated: {len(x_train)} train / {len(x_test)} "
            f"test, pinned {MAUNA_TRAIN_ROWS}/{MAUNA_TEST_ROWS} (§6.2)")

    info = {"y_mean": 0.0, "y_std": 1.0, "x_offset": 0.0}

    if normalize:
        info["y_mean"], info["y_std"] = y_train.mean(), y_train.std()
        y_train = (y_train - info["y_mean"]) / info["y_std"]
        y_test = (y_test - info["y_mean"]) / info["y_std"]
        info["x_offset"] = x_train.mean()
        x_train -= info["x_offset"]
        x_test -= info["x_offset"]

    # Split METADATA (always permitted under §6.6) and provenance record.
    info.update({
        "n_raw": MAUNA_RAW_ROWS,
        "n_monthly": len(x_all),
        "n_train": len(x_train),
        "n_test": len(x_test),
        "cutoff_rule": "max(x) - test_years",
        "test_years": test_years,
        "source": source,
        "canonical_sha256": MAUNA_CANONICAL_SHA256,
    })
    return x_train, y_train, x_test, y_test, info


def load_mauna_loa(normalize=True, test_years=5.0, source="vendored"):
    """Load Mauna Loa CO2 (OpenML 41187) with the A9 provenance gate.

    Returns (x_train, y_train, x_test, y_test, info). Returned training values
    are byte-identical to the pre-A9 loader's (regression-gated by the frozen
    D19 scorecard). This entry point materializes the sealed 60-month holdout;
    study-facing D19 code must use load_mauna_loa_training instead (§6.6).
    """
    x_train, y_train, x_test, y_test, info = _load_mauna_loa_split(
        normalize=normalize, test_years=test_years, source=source)
    return (
        torch.tensor(x_train).double(), torch.tensor(y_train).double(),
        torch.tensor(x_test).double(), torch.tensor(y_test).double(),
        info,
    )


def load_mauna_loa_training(normalize=True, test_years=5.0, source="vendored"):
    """TRAINING-ONLY Mauna loader: the §6.6 holdout seal, made mechanical.

    Returns (x_train, y_train, info) and nothing else: test y values are never
    returned, logged, or persisted by this entry point, so a study-facing
    caller cannot touch the sealed holdout through it. Split metadata (counts,
    cutoff rule) is included in info — §6.6 permits that explicitly. The
    normalization statistics are training-span statistics, identical to the
    default loader's. All D19 study-facing code uses this entry point.
    """
    x_train, y_train, _x_test, _y_test, info = _load_mauna_loa_split(
        normalize=normalize, test_years=test_years, source=source)
    return torch.tensor(x_train).double(), torch.tensor(y_train).double(), info
