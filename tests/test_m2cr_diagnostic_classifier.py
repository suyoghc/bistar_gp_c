"""Hermetic unit tests for the v1.21 sweep and slope classifier."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from bistar_gp.m2cr.diagnostic import (
    SWEEP_H_VALUES,
    classify_slope,
    ols_loglog,
    slope_analysis_record,
    symmetry_error_at_h,
)
from bistar_gp.m2cr.gates_v2 import curvature_gate_v2


@pytest.mark.parametrize(
    ("errors", "classification", "slope"),
    [
        ([3.0 * h**2 for h in SWEEP_H_VALUES], "TRUNCATION_LIKE", 2.0),
        ([3.0 / h for h in SWEEP_H_VALUES], "NOISE_LIKE", -1.0),
        ([3.0 for _ in SWEEP_H_VALUES], "FLAT", 0.0),
    ],
)
def test_characteristic_sweep_slopes(errors, classification, slope) -> None:
    fit = ols_loglog(SWEEP_H_VALUES, errors)
    assert fit["defined"] is True
    assert fit["slope"] == pytest.approx(slope, abs=1e-12)
    assert classify_slope(fit) == classification


@pytest.mark.parametrize(
    ("slope", "expected"),
    [
        (1.5, "TRUNCATION_LIKE"),
        (2.5, "TRUNCATION_LIKE"),
        (-0.5, "NOISE_LIKE"),
        (1.49, "FLAT"),
        (2.51, "FLAT"),
        (-0.49, "FLAT"),
        (np.nextafter(1.5, -np.inf), "FLAT"),
        (np.nextafter(2.5, np.inf), "FLAT"),
        (np.nextafter(-0.5, np.inf), "FLAT"),
        (np.nextafter(1.5, np.inf), "TRUNCATION_LIKE"),
        (np.nextafter(2.5, -np.inf), "TRUNCATION_LIKE"),
        (np.nextafter(-0.5, -np.inf), "NOISE_LIKE"),
    ],
)
def test_exact_boundaries_and_adjacent_values(slope: float, expected: str) -> None:
    """The windows are the frozen real boundaries verbatim (B12(b)).

    Boundary semantics are a property of ``classify_slope`` over a fitted
    slope, so the fit dict is injected directly; the one-ULP-adjacent cases
    pin that no epsilon of any size widens or narrows a window.  OLS-path
    coverage at non-boundary slopes is in
    ``test_characteristic_sweep_slopes``.
    """

    fit = {"defined": True, "slope": float(slope), "intercept": 0.0}
    assert classify_slope(fit) == expected


@pytest.mark.parametrize("bad", [0.0, -1.0])
def test_nonpositive_value_is_undefined(bad: float) -> None:
    errors = [1.0] * 5
    errors[2] = bad
    assert slope_analysis_record(SWEEP_H_VALUES, errors) == {
        "classification": "UNDEFINED",
        "undefined_reason": "nonpositive_sweep_value",
    }


@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf])
def test_nonfinite_value_is_undefined(bad: float) -> None:
    errors = [1.0] * 5
    errors[2] = bad
    assert slope_analysis_record(SWEEP_H_VALUES, errors) == {
        "classification": "UNDEFINED",
        "undefined_reason": "nonfinite_sweep_value",
    }


def test_nonfinite_label_wins_in_a_mixed_invalid_sweep() -> None:
    assert slope_analysis_record(
        SWEEP_H_VALUES, [-1.0, 1.0, np.nan, 1.0, 1.0]
    ) == {
        "classification": "UNDEFINED",
        "undefined_reason": "nonfinite_sweep_value",
    }


@pytest.mark.parametrize("count", [4, 6])
def test_reduced_or_extended_fit_is_rejected(count: int) -> None:
    with pytest.raises(ValueError, match="exactly five"):
        ols_loglog([1.0] * count, [1.0] * count)


def test_nonfinite_required_ols_statistic_is_undefined() -> None:
    # Identical positive h values make the required denominator zero without
    # introducing an invalid sweep error; B12(c) must catch the OLS statistic.
    assert ols_loglog([1.0] * 5, [1.0, 2.0, 3.0, 4.0, 5.0]) == {
        "defined": False,
        "reason": "nonfinite_ols_statistic",
    }


def test_center_symmetry_is_bit_exact_with_frozen_gate() -> None:
    curvature = np.diag(np.asarray([1.0, 4.0, 9.0], dtype=np.float64))

    def g(u):
        return -0.5 * float(u @ curvature @ u)

    def grad(u):
        return -(curvature @ u)

    u = np.zeros(3, dtype=np.float64)
    gate = curvature_gate_v2(
        g, grad, u, ("ls", "os", "lv"), perm=(0, 1, 2)
    )
    assert symmetry_error_at_h(grad, u, 1e-3) == gate["symmetry_error"]


def test_wrong_shape_gradient_is_rejected() -> None:
    with pytest.raises(ValueError, match="wrong shape"):
        symmetry_error_at_h(
            lambda _u: np.zeros(2, dtype=np.float64), np.zeros(3), 1e-3
        )


def test_protocol_artifact_sweep_matches_public_tuple() -> None:
    artifact = json.loads(
        (
            Path(__file__).resolve().parents[1]
            / "docs/m2c_freeze/m2cr_diagnostic_protocol_v1.json"
        ).read_text()
    )
    assert tuple(artifact["sweep"]["h_values"]) == SWEEP_H_VALUES
