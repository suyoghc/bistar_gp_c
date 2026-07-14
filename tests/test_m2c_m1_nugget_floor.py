"""Seedless weighted tests for the report-only M1 nugget predicate."""

import numpy as np
import pytest

from bistar_gp.m1_authority import normalize_authority_weights
from bistar_gp.m1_nugget_floor import (
    NuggetError,
    nugget_floor_predicate,
    nugget_floor_report,
    resolve_single_noise_site,
)
from bistar_gp.m2c_freeze_m1 import NUGGET_FLAG_THRESHOLD, NUGGET_REFERENCE


def _predicate(noises, weights, **kwargs):
    authority = normalize_authority_weights("G-IS", weights)
    return nugget_floor_predicate(noises, authority, **kwargs)


@pytest.mark.parametrize(
    ("noises", "weights", "expected"),
    [
        ([NUGGET_REFERENCE, 2.0 * NUGGET_REFERENCE], [0.5, 0.5], 0.0),
        ([0.5 * NUGGET_REFERENCE, 2.0 * NUGGET_REFERENCE], [0.05, 0.95], 0.05),
        ([0.5 * NUGGET_REFERENCE, 2.0 * NUGGET_REFERENCE], [0.10, 0.90], 0.10),
        ([0.5 * NUGGET_REFERENCE, 0.75 * NUGGET_REFERENCE], [0.25, 0.75], 1.0),
    ],
)
def test_seedless_weighted_p_below_values(noises, weights, expected):
    report = _predicate(noises, weights)
    assert report["p_below_M1"] == pytest.approx(expected)
    assert report["authority"] == "G-IS"


def test_noise_exactly_at_reference_is_not_strictly_below():
    report = _predicate(
        [NUGGET_REFERENCE, np.nextafter(NUGGET_REFERENCE, 0.0)], [0.8, 0.2]
    )
    assert report["p_below_M1"] == pytest.approx(0.2)


def test_flag_uses_strict_five_percent_boundary():
    at_boundary = _predicate(
        [0.5 * NUGGET_REFERENCE, 2.0 * NUGGET_REFERENCE],
        [NUGGET_FLAG_THRESHOLD, 1.0 - NUGGET_FLAG_THRESHOLD],
    )
    above_boundary = _predicate(
        [0.5 * NUGGET_REFERENCE, 2.0 * NUGGET_REFERENCE], [0.051, 0.949]
    )
    assert at_boundary["p_below_M1"] == pytest.approx(NUGGET_FLAG_THRESHOLD)
    assert at_boundary["flag"] is False
    assert above_boundary["flag"] is True


@pytest.mark.parametrize(
    ("m1_weights", "m0_weights", "expected_delta"),
    [([0.75, 0.25], [0.25, 0.75], 0.50), ([0.25, 0.75], [0.75, 0.25], -0.50)],
)
def test_m0_companion_and_signed_delta(m1_weights, m0_weights, expected_delta):
    m1_authority = normalize_authority_weights("G-IS", m1_weights)
    m0_authority = normalize_authority_weights("RW-MH", m0_weights)
    report = nugget_floor_predicate(
        [0.5 * NUGGET_REFERENCE, 2.0 * NUGGET_REFERENCE],
        m1_authority,
        m0_noise_variances=[0.5 * NUGGET_REFERENCE, 2.0 * NUGGET_REFERENCE],
        normalized_m0_authority=m0_authority,
    )
    assert report["p_below_M0"] == pytest.approx(m0_weights[0])
    assert report["delta_p"] == pytest.approx(expected_delta)


def test_true_flag_is_report_only_and_never_a_blocking_verdict():
    report = _predicate([0.5 * NUGGET_REFERENCE], [1.0])
    assert report["flag"] is True
    assert not ({"stop", "blocking", "verdict"} & set(report))


@pytest.mark.parametrize(
    ("below_weight", "predictive_gate", "expected"),
    [(1.0, True, True), (1.0, False, False), (0.0, True, False)],
)
def test_coincidence_requires_both_flag_and_predictive_gate(
    below_weight, predictive_gate, expected
):
    report = _predicate(
        [0.5 * NUGGET_REFERENCE, 2.0 * NUGGET_REFERENCE],
        [below_weight, 1.0 - below_weight],
        predictive_gate_passes=predictive_gate,
    )
    assert report["coincidence"] is expected
    assert report["predictive_gate_passes"] is predictive_gate


def test_current_and_legacy_noise_sites_resolve_with_legacy_precedence():
    current = "likelihood.noise_covar.noise_prior"
    legacy = "noise_covar.noise_prior"
    assert resolve_single_noise_site(
        ["covar_module.kernels.0.outputscale_prior", current]
    ) == current
    assert resolve_single_noise_site(
        ["kernel_components.0.outputscale_prior", legacy]
    ) == legacy
    assert resolve_single_noise_site([current, legacy]) == legacy


def test_zero_or_multiple_selected_noise_sites_fail_closed():
    with pytest.raises(NuggetError):
        resolve_single_noise_site(["covar_module.kernels.0.outputscale_prior"])
    with pytest.raises(NuggetError):
        resolve_single_noise_site(
            [
                "likelihood.noise_covar.noise_prior",
                "alternate.noise_covar.noise_prior",
            ]
        )


@pytest.mark.parametrize(
    ("label", "weights"),
    [
        ("profile-Laplace", [1.0]),
        ("G-IS", []),
        ("G-IS", [0.0, 0.0]),
        ("G-IS", [1.0, -1.0]),
        ("G-IS", [1.0, np.nan]),
        ("G-IS", [10 ** 400]),  # Python int too large for float64 -> UNDETERMINED
    ],
)
def test_bad_or_profile_authority_reports_undetermined(label, weights):
    report = nugget_floor_report(
        [NUGGET_REFERENCE], label, weights, predictive_gate_passes=True
    )
    assert report["flag"] == "UNDETERMINED"
    assert report["coincidence"] is None
    assert report["p_below_M1"] is None
    assert "verdict" not in report


def test_bad_noise_site_mapping_reports_undetermined_without_escaping():
    missing = nugget_floor_report(
        {"covar_module.kernels.0.outputscale_prior": np.array([1.0])},
        "G-IS",
        [1.0],
    )
    multiple = nugget_floor_report(
        {
            "likelihood.noise_covar.noise_prior": np.array([NUGGET_REFERENCE]),
            "alternate.noise_covar.noise_prior": np.array([NUGGET_REFERENCE]),
        },
        "G-IS",
        [1.0],
    )
    assert missing["flag"] == "UNDETERMINED"
    assert multiple["flag"] == "UNDETERMINED"


def test_top_level_report_normalizes_once_and_returns_normally():
    report = nugget_floor_report(
        [0.5 * NUGGET_REFERENCE, 2.0 * NUGGET_REFERENCE],
        "RW-MH",
        [2.0, 18.0],
        predictive_gate_passes=True,
    )
    assert report["p_below_M1"] == pytest.approx(0.10)
    assert report["ess"] == pytest.approx(1.0 / (0.1 ** 2 + 0.9 ** 2))
    assert report["flag"] is True
    assert report["coincidence"] is True
