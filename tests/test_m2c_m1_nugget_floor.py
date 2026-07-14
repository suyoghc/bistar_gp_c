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


def _auth(label, weights):
    """(candidates, weights_by_label) for one attested authority."""
    return {label: True}, {label: list(weights)}


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


def _report(m1_noises, m1_weights, **kwargs):
    """Complete scientific report: internal precedence selection + explicit gate."""
    m1_c, m1_w = _auth("G-IS", m1_weights)
    m0_c, m0_w = _auth("RW-MH", [1.0, 1.0])
    defaults = dict(
        m0_noise_variances=[2.0 * NUGGET_REFERENCE, 2.0 * NUGGET_REFERENCE],
        m0_authority_candidates=m0_c,
        m0_authority_weights_by_label=m0_w,
        predictive_gate_passes=True,
    )
    defaults.update(kwargs)
    return nugget_floor_report(m1_noises, m1_c, m1_w, **defaults)


def test_unusable_or_bad_authority_reports_undetermined():
    m1 = [0.5 * NUGGET_REFERENCE, 2.0 * NUGGET_REFERENCE]
    # No usable M1 candidate (nothing attested) => UNDETERMINED.
    r_unusable = nugget_floor_report(
        m1, {"G-IS": False}, {"G-IS": [0.5, 0.5]},
        m0_noise_variances=m1,
        m0_authority_candidates={"RW-MH": True},
        m0_authority_weights_by_label={"RW-MH": [0.5, 0.5]},
        predictive_gate_passes=True,
    )
    assert r_unusable["flag"] == "UNDETERMINED"
    assert r_unusable["p_below_M1"] is None and r_unusable["coincidence"] is None
    assert "verdict" not in r_unusable
    # profile-Laplace can never be selected => UNDETERMINED.
    r_pl = nugget_floor_report(
        m1, {"profile-Laplace": True}, {"profile-Laplace": [0.5, 0.5]},
        m0_noise_variances=m1,
        m0_authority_candidates={"RW-MH": True},
        m0_authority_weights_by_label={"RW-MH": [0.5, 0.5]},
        predictive_gate_passes=True,
    )
    assert r_pl["flag"] == "UNDETERMINED"
    # Bad M1 weights => UNDETERMINED (selection fails closed inside the wrapper).
    for weights in ([], [0.0, 0.0], [1.0, -1.0], [1.0, np.nan], [10 ** 400]):
        assert _report(m1, weights)["flag"] == "UNDETERMINED"


def test_missing_m0_or_predictive_gate_reports_undetermined():
    m1 = [0.5 * NUGGET_REFERENCE, 2.0 * NUGGET_REFERENCE]
    missing_m0 = _report(m1, [0.5, 0.5], m0_noise_variances=None)
    missing_m0_auth = _report(m1, [0.5, 0.5], m0_authority_candidates=None)
    missing_gate = _report(m1, [0.5, 0.5], predictive_gate_passes=None)
    assert missing_m0["flag"] == "UNDETERMINED"
    assert missing_m0_auth["flag"] == "UNDETERMINED"
    assert missing_gate["flag"] == "UNDETERMINED"


def test_nonpositive_noise_reports_undetermined():
    m1 = [0.5 * NUGGET_REFERENCE, 2.0 * NUGGET_REFERENCE]
    zero_m1 = _report([0.0, 2.0 * NUGGET_REFERENCE], [0.5, 0.5])
    neg_m0 = _report(m1, [0.5, 0.5], m0_noise_variances=[-1e-5, NUGGET_REFERENCE])
    assert zero_m1["flag"] == "UNDETERMINED"
    assert neg_m0["flag"] == "UNDETERMINED"


def test_bad_noise_site_mapping_reports_undetermined_without_escaping():
    missing = _report(
        {"covar_module.kernels.0.outputscale_prior": np.array([1.0])}, [1.0]
    )
    multiple = _report(
        {
            "likelihood.noise_covar.noise_prior": np.array([NUGGET_REFERENCE]),
            "alternate.noise_covar.noise_prior": np.array([NUGGET_REFERENCE]),
        },
        [1.0],
    )
    assert missing["flag"] == "UNDETERMINED"
    assert multiple["flag"] == "UNDETERMINED"


def test_complete_report_returns_the_full_coincidence_record():
    report = _report(
        [0.5 * NUGGET_REFERENCE, 2.0 * NUGGET_REFERENCE], [2.0, 18.0]
    )
    assert report["p_below_M1"] == pytest.approx(0.10)
    assert report["ess"] == pytest.approx(1.0 / (0.1 ** 2 + 0.9 ** 2))
    assert report["p_below_M0"] == pytest.approx(0.0)
    assert report["delta_p"] == pytest.approx(0.10)
    assert report["flag"] is True
    assert report["coincidence"] is True
    assert report["predictive_gate_passes"] is True
    assert "verdict" not in report


def test_nugget_report_pins_frozen_thresholds_and_rejects_overrides():
    import inspect

    from bistar_gp import m1_nugget_floor

    params = inspect.signature(m1_nugget_floor.nugget_floor_report).parameters
    assert "reference" not in params and "flag_threshold" not in params
    # The frozen 1.9e-4/0.05 appear in every completed report (valid + UNDETERMINED).
    ok = _report([0.5 * NUGGET_REFERENCE, 2.0 * NUGGET_REFERENCE], [2.0, 18.0])
    assert ok["reference"] == NUGGET_REFERENCE == 1.9e-4
    assert ok["flag_threshold"] == NUGGET_FLAG_THRESHOLD == 0.05
    und = _report([0.5 * NUGGET_REFERENCE], [1.0], m0_noise_variances=None)
    assert und["flag"] == "UNDETERMINED"
    assert und["reference"] == 1.9e-4 and und["flag_threshold"] == 0.05
    # A caller cannot flip the flag by overriding the frozen threshold (§7 frozen).
    with pytest.raises(TypeError):
        _report([0.5 * NUGGET_REFERENCE], [1.0], flag_threshold=1.0)
