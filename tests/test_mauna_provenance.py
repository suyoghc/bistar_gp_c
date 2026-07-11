"""
A9 data-provenance gate + training-only loader (D20; plan-d19-mauna.md §6.2/§6.6).

The Mauna Loa loader now reads a vendored, checksummed copy of OpenML 41187
(licence CC0) and hard-fails on any identity mismatch: canonical
year/month/co2 sha256, the M1-era co2-only sha256, and the pinned counts
2225 raw / 521 monthly / 461 train / 60 test. These tests exercise the gate
against the real vendored artifact (reading the full raw record here is the
PROVENANCE LAYER acting under the §6.6 seal semantics — identity checks only;
no model is fit and no test value feeds any analysis) plus tampered in-memory
copies for the failure paths. Everything runs offline; the OpenML network
source is deliberately not tested in CI.
"""

import numpy as np
import pytest

torch = pytest.importorskip("torch")
pd = pytest.importorskip("pandas")

from bistar_gp.data import (
    MAUNA_CANONICAL_SHA256,
    MAUNA_CO2_SHA256,
    MAUNA_MONTHLY_ROWS,
    MAUNA_RAW_ROWS,
    MAUNA_TEST_ROWS,
    MAUNA_TRAIN_ROWS,
    MAUNA_VENDORED_CSV,
    _verify_mauna_provenance,
    load_mauna_loa,
    load_mauna_loa_training,
)

# Pinned realized normalization stats (plan §0; the D19 scorecard asserts the
# same y_std, so drift here would also break the byte-identity gate).
PINNED_Y_STD = 14.58342466738224
PINNED_X_OFFSET = 1977.7109544468547


@pytest.fixture(scope="module")
def raw_frame():
    return pd.read_csv(MAUNA_VENDORED_CSV)


@pytest.fixture(scope="module")
def default_load():
    return load_mauna_loa(normalize=True, test_years=5.0)


def test_vendored_artifact_exists_and_verifies(raw_frame):
    assert MAUNA_VENDORED_CSV.exists()
    year_col, month_col, co2_col = _verify_mauna_provenance(raw_frame)
    assert (year_col, month_col, co2_col) == ("year", "month", "co2")
    assert len(raw_frame) == MAUNA_RAW_ROWS == 2225


def test_pinned_hash_constants_are_the_frozen_values():
    """The prereg-referenced values: canonical hash = addendum v1.1; co2-only
    hash = the M1 pin carried forward from plan §6.2."""
    assert MAUNA_CANONICAL_SHA256 == (
        "5bcdc813b4c3b570c9947acfaa0d3ff8cb5f89094b3e4e5121f72535a0cc0910")
    assert MAUNA_CO2_SHA256 == (
        "7e301efd6dbd2b4007723368aa69ebd2259ea6aa1d431650c209df181f244cb9")


def test_counts_and_normalization_pins(default_load):
    x_train, y_train, x_test, y_test, info = default_load
    assert len(x_train) == MAUNA_TRAIN_ROWS == 461
    assert len(x_test) == MAUNA_TEST_ROWS == 60
    assert info["n_monthly"] == MAUNA_MONTHLY_ROWS == 521
    assert info["n_raw"] == 2225
    assert float(info["y_std"]) == pytest.approx(PINNED_Y_STD, abs=1e-12)
    assert float(info["x_offset"]) == pytest.approx(PINNED_X_OFFSET, abs=1e-9)
    assert x_train.dtype == torch.float64 and y_train.dtype == torch.float64


def test_tampered_co2_value_hard_fails(raw_frame):
    tampered = raw_frame.copy()
    tampered.loc[100, "co2"] = tampered.loc[100, "co2"] + 0.01
    with pytest.raises(RuntimeError, match="sha256 mismatch"):
        _verify_mauna_provenance(tampered)


def test_tampered_metadata_column_hard_fails(raw_frame):
    """The canonical hash covers year/month too — metadata edits that leave
    the co2 column intact (the M1-era blind spot) now fail loudly."""
    tampered = raw_frame.copy()
    tampered.loc[0, "month"] = 2
    with pytest.raises(RuntimeError, match="canonical year/month/co2"):
        _verify_mauna_provenance(tampered)


def test_truncated_record_hard_fails(raw_frame):
    with pytest.raises(RuntimeError, match="rows"):
        _verify_mauna_provenance(raw_frame.iloc[:-1])


def test_unknown_source_rejected():
    with pytest.raises(ValueError, match="unknown source"):
        load_mauna_loa(source="ftp")


def test_public_loaders_actually_run_the_gate(monkeypatch):
    """The gate must be wired into the PUBLIC entry points, not just exist as
    a helper: with the pinned canonical hash perturbed, both loaders must
    refuse the (now 'mismatching') vendored artifact (workflow finding C6)."""
    import bistar_gp.data as data_mod

    monkeypatch.setattr(
        data_mod, "MAUNA_CANONICAL_SHA256", "0" * 64)
    with pytest.raises(RuntimeError, match="canonical year/month/co2"):
        load_mauna_loa(normalize=True, test_years=5.0)
    with pytest.raises(RuntimeError, match="canonical year/month/co2"):
        load_mauna_loa_training(normalize=True, test_years=5.0)


def test_openml_source_fetch_failure_is_a_hard_error(monkeypatch):
    """The pre-A9 loader fell through a failed fetch into UnboundLocalError
    at np.argsort(x_all); the A9 path must raise a clear RuntimeError with no
    silent fallback (workflow finding C10). No network involved."""
    import sklearn.datasets

    def failing_fetch(*args, **kwargs):
        raise ConnectionError("no route to openml")

    monkeypatch.setattr(sklearn.datasets, "fetch_openml", failing_fetch)
    with pytest.raises(RuntimeError, match="no\\s+fallback"):
        load_mauna_loa(source="openml")


def test_openml_source_verifies_the_fetched_frame(monkeypatch, raw_frame):
    """A tampered upstream record must fail the same gate as a tampered
    vendored file — the openml path is not exempt (workflow finding C10)."""
    import sklearn.datasets

    tampered = raw_frame.copy()
    tampered.loc[7, "co2"] = tampered.loc[7, "co2"] + 0.5

    class FakeBunch:
        frame = tampered

    monkeypatch.setattr(
        sklearn.datasets, "fetch_openml", lambda *a, **k: FakeBunch())
    with pytest.raises(RuntimeError, match="sha256 mismatch|canonical"):
        load_mauna_loa(source="openml")


def test_training_only_loader_matches_default_and_seals_holdout(default_load):
    x_train, y_train, _x_test, _y_test, info = default_load
    xt, yt, info_t = load_mauna_loa_training(normalize=True, test_years=5.0)
    assert torch.equal(xt, x_train) and torch.equal(yt, y_train)
    # Split METADATA is present (permitted by §6.6) ...
    assert info_t["n_train"] == 461 and info_t["n_test"] == 60
    assert info_t["cutoff_rule"] == "max(x) - test_years"
    # ... but no test values ride along: info carries only scalars/strings,
    # never arrays, so the 60 sealed y values cannot leak through this API.
    assert all(np.ndim(v) == 0 for v in info_t.values())
    assert float(info_t["y_std"]) == float(info["y_std"])


def test_study_script_stays_on_the_training_only_loader():
    """Source-level seal guard (review finding 1): the Mauna study script
    must consume load_mauna_loa_training and never touch test values. A
    reintroduced full-loader call or test-tensor reference reopens the
    sealed holdout silently, so the guard is textual and loud."""
    script = (MAUNA_VENDORED_CSV.parents[2] / "experiments"
              / "bms_star_mauna_loa.py").read_text()
    assert "load_mauna_loa_training" in script
    assert "load_mauna_loa(" not in script, (
        "bms_star_mauna_loa.py calls the full loader; the §6.6 holdout seal "
        "requires the training-only entry point until the D19 decision")
    for forbidden in ("x_test", "y_test"):
        assert forbidden not in script, (
            f"bms_star_mauna_loa.py references {forbidden}; sealed holdout "
            "values must not appear in study-facing code (§6.6)")


def test_unnormalized_values_are_ppm(default_load):
    x_train, y_train, *_ = load_mauna_loa(normalize=False, test_years=5.0)
    assert 300 < float(y_train.mean()) < 400  # ppm scale, not normalized
    assert float(x_train.min()) > 1900  # calendar years, not centered
    # and the normalized default is consistent with these raw values
    _, y_norm, _, _, info = default_load
    back = y_norm.numpy() * float(info["y_std"]) + float(info["y_mean"])
    assert np.allclose(back, y_train.numpy(), rtol=0, atol=1e-9)
