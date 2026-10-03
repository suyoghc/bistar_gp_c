"""
FIX-8 (2026-09 review): van Bork, Romeijn and Wagenmakers (2025) Targets A
and B as package closed forms, and a checker that asserts an artifact
against them by recomputing the errors from its rows.

Pins: the closed forms; the committed
runs/vanbork_external_validation/results.json values (its smallest-tau rows,
embedded here from the driver-provided fixture, and the fixture file itself
when present) pass; a copy with the Target B column shifted by 0.1 fails;
a corrupted Target A column, a stored error field that disagrees with the
rows, and an over-tight tolerance fail with the target named.
"""

import copy
import json
import os

import numpy as np
import pytest

from bistar_gp.external_targets import (
    VANBORK_TARGET_A, VANBORK_TARGET_B_PRIORS, check_external_targets,
    external_target_errors, vanbork_target_b, vanbork_target_b_densities,
    vanbork_target_b_weight,
)

# Driver-provided `git show` copy of the case-A artifact; set FIX1_FIXTURE_DIR to
# the directory holding vanbork_results.json to exercise it (skipped otherwise).
SCRATCH_FIXTURE = os.path.join(os.environ.get("FIX1_FIXTURE_DIR", ""), "vanbork_results.json")

# Smallest-tau rows (and the tau = 1 rows) of the committed artifact, copied
# from the driver-provided `git show` fixture of paper/case-a-vanbork.
COMMITTED = {
    "source": "van Bork, Romeijn & Wagenmakers 2025, Synthese, doi:10.1007/s11229-025-05286-y, Section 4",
    "taus": [1.0, 0.1, 0.01, 0.001, 0.0001, 1e-05, 1e-06, 1e-07],
    "target_a": {
        "names": ["M1 (theta=0.15)", "M2 (theta=0.20)"],
        "target": {"M1 (theta=0.15)": 0.4, "M2 (theta=0.20)": 0.6},
        "rows": [
            {"tau": 1.0, "M1 (theta=0.15)": 0.49965650872257117, "M2 (theta=0.20)": 0.5003434912774289},
            {"tau": 1e-07, "M1 (theta=0.15)": 0.4, "M2 (theta=0.20)": 0.6},
        ],
    },
    "target_b": {
        "names": ["M_x beta(50,50)", "M_z beta(2,2)"],
        "published_densities_at_mle": {"M_x beta(50,50)": 7.95892373871788, "M_z beta(2,2)": 1.5000000000000007},
        "published_weight_Mx": 0.8414195904910299,
        "rows": [
            {"tau": 1.0, "M_x beta(50,50)": 0.5296605155174497, "M_z beta(2,2)": 0.47033948448255036},
            {"tau": 1e-07, "M_x beta(50,50)": 0.841418950016495, "M_z beta(2,2)": 0.15858104998350495},
        ],
    },
    "abs_error_at_min_tau": {"A": 0.0, "B": 6.404745348520535e-07},
}


def _write(tmp_path, payload, name="results.json"):
    p = tmp_path / name
    p.write_text(json.dumps(payload))
    return str(p)


def test_closed_forms():
    assert VANBORK_TARGET_A == {"M1 (theta=0.15)": 0.4, "M2 (theta=0.20)": 0.6}
    dens = vanbork_target_b_densities()
    assert dens["M_x beta(50,50)"] == pytest.approx(7.95892373871788, rel=1e-12)
    assert dens["M_z beta(2,2)"] == pytest.approx(1.5, rel=1e-12)
    assert vanbork_target_b_weight() == pytest.approx(0.8414195904910299, abs=1e-12)
    tb = vanbork_target_b()
    assert set(tb) == set(VANBORK_TARGET_B_PRIORS) and sum(tb.values()) == pytest.approx(1.0)


def test_committed_values_pass(tmp_path):
    path = _write(tmp_path, COMMITTED)
    errors = check_external_targets(path)
    assert errors["A"] == 0.0
    assert errors["B"] == pytest.approx(6.404745348520535e-07, abs=1e-12)
    assert external_target_errors(COMMITTED) == errors


@pytest.mark.skipif(not os.environ.get("FIX1_FIXTURE_DIR") or not os.path.exists(SCRATCH_FIXTURE),
                    reason="FIX1_FIXTURE_DIR with vanbork_results.json not provided")
def test_driver_fixture_passes():
    errors = check_external_targets(SCRATCH_FIXTURE)
    with open(SCRATCH_FIXTURE) as f:
        stored = json.load(f)["abs_error_at_min_tau"]
    assert errors["A"] == pytest.approx(stored["A"], abs=1e-12)
    assert errors["B"] == pytest.approx(stored["B"], abs=1e-12)


def test_target_b_column_shift_fails(tmp_path):
    bad = copy.deepcopy(COMMITTED)
    for row in bad["target_b"]["rows"]:
        row["M_x beta(50,50)"] += 0.1
        row["M_z beta(2,2)"] -= 0.1          # masses still sum to one
    with pytest.raises(AssertionError, match="external target B"):
        check_external_targets(_write(tmp_path, bad))
    unbalanced = copy.deepcopy(COMMITTED)
    for row in unbalanced["target_b"]["rows"]:
        row["M_x beta(50,50)"] += 0.1
    with pytest.raises(AssertionError, match="external target B"):
        check_external_targets(_write(tmp_path, unbalanced, "u.json"))


def test_target_a_corruption_and_stored_field_disagreement_fail(tmp_path):
    bad_a = copy.deepcopy(COMMITTED)
    bad_a["target_a"]["rows"][-1]["M1 (theta=0.15)"] = 0.41
    bad_a["target_a"]["rows"][-1]["M2 (theta=0.20)"] = 0.59
    with pytest.raises(AssertionError, match="external target A"):
        check_external_targets(_write(tmp_path, bad_a))
    stale = copy.deepcopy(COMMITTED)
    stale["abs_error_at_min_tau"]["B"] = 0.0
    with pytest.raises(AssertionError, match="disagrees"):
        check_external_targets(_write(tmp_path, stale, "s.json"))
    with pytest.raises(AssertionError, match="external target B"):
        check_external_targets(_write(tmp_path, COMMITTED, "t.json"), tol_b=1e-8)


def test_min_tau_row_is_selected_regardless_of_order(tmp_path):
    shuffled = copy.deepcopy(COMMITTED)
    for key in ("target_a", "target_b"):
        shuffled[key]["rows"] = shuffled[key]["rows"][::-1]
    assert external_target_errors(shuffled) == external_target_errors(COMMITTED)
