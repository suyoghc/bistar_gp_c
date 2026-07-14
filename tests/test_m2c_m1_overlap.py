"""Hermetic algebraic and one plumbing-only M1 overlap fixture."""

import numpy as np
import pytest


torch = pytest.importorskip("torch")
pytest.importorskip("gpytorch")

from bistar_gp.m1_authority import (
    AuthorityError,
    normalize_authority_weights,
    resolve_verdict_authority,
    select_and_normalize_authority,
)
from bistar_gp.m1_builder import build_mauna_loa_m1_kernels
from bistar_gp.m1_overlap import (
    OverlapError,
    centered_frobenius_alignment,
    draw_overlap_omax,
    overlap_diagnostic,
    q_overlap,
)
from bistar_gp.m2c_freeze_m1 import (
    M1_LENGTHSCALE_MEDIAN,
    M1_OUTPUTSCALE_MEDIAN,
    M1_OVERLAP_REQUIRED_COMPONENTS,
    M1_SHORT_SCALE_NAME,
    NUGGET_REFERENCE,
    OVERLAP_ALIGNMENT_THRESHOLD,
    Q_OVERLAP_CAP,
)
from bistar_gp.model import build_model


torch.set_default_dtype(torch.float64)


def _auth(label="G-IS", weights=(1.0,)):
    """(candidates, weights_by_label) for one attested authority; spread with *."""
    return {label: True}, {label: list(weights)}


def _exact_draw(projector):
    """A complete frozen-set component dict (M1 + trend/seasonal/medium_term)."""
    return {
        M1_SHORT_SCALE_NAME: projector,
        **{name: projector for name in M1_OVERLAP_REQUIRED_COMPONENTS},
    }


def _centered_rank_one(vector):
    vector = np.asarray(vector, dtype=np.float64)
    assert vector.sum() == pytest.approx(0.0)
    return np.outer(vector, vector)


def test_identical_centered_matrices_have_exact_unit_alignment():
    matrix = _centered_rank_one([1.0, -1.0, 0.0])
    assert centered_frobenius_alignment(matrix, matrix) == 1.0


def test_orthogonal_centered_rank_one_matrices_have_zero_alignment():
    left = _centered_rank_one([1.0, -1.0, 0.0])
    right = _centered_rank_one([1.0, 1.0, -2.0])
    assert centered_frobenius_alignment(left, right) == 0.0


def test_frobenius_alignment_is_invariant_to_positive_scale():
    left = _centered_rank_one([1.0, -1.0, 0.0])
    right = _centered_rank_one([1.0, 1.0, -2.0]) + left
    baseline = centered_frobenius_alignment(left, right)
    assert centered_frobenius_alignment(7.25 * left, right) == pytest.approx(
        baseline, abs=1e-15
    )
    assert centered_frobenius_alignment(left, 0.03125 * right) == pytest.approx(
        baseline, abs=1e-15
    )


@pytest.mark.parametrize(
    ("weights", "expected_q", "verdict"),
    [
        ([0.049, 0.951], 0.049, "PASS"),
        ([0.050, 0.950], 0.050, "PASS"),
        ([0.051, 0.949], 0.051, "STOP"),
    ],
)
def test_weighted_duplicate_mass_straddles_strict_five_percent_cap(
    weights, expected_q, verdict
):
    authority = normalize_authority_weights("G-IS", weights)
    report = q_overlap([0.95, 0.20], authority)
    assert report["q_overlap"] == pytest.approx(expected_q)
    assert report["verdict"] == verdict
    assert report["threshold"] == OVERLAP_ALIGNMENT_THRESHOLD
    assert report["cap"] == Q_OVERLAP_CAP


def test_rest_can_cross_threshold_when_no_single_component_does():
    # The centered subspace has orthonormal u/v/w directions. M1 is U+V;
    # each U or V aligns by 1/sqrt(2), and nugget P by sqrt(2/3), while their
    # rest sum is almost collinear with M1.
    u = np.array([1.0, -1.0, 0.0, 0.0]) / np.sqrt(2.0)
    v = np.array([1.0, 1.0, -2.0, 0.0]) / np.sqrt(6.0)
    U = np.outer(u, u)
    V = np.outer(v, v)
    report = draw_overlap_omax(
        {M1_SHORT_SCALE_NAME: U + V, "first": U, "second": V},
        0.01,
    )
    alignments = report["o_by_component"]
    assert alignments["first"] < OVERLAP_ALIGNMENT_THRESHOLD
    assert alignments["second"] < OVERLAP_ALIGNMENT_THRESHOLD
    assert alignments["nugget"] < OVERLAP_ALIGNMENT_THRESHOLD
    assert alignments["rest"] >= OVERLAP_ALIGNMENT_THRESHOLD
    assert report["o_max"] == alignments["rest"]


def test_draw_overlap_fails_closed_on_missing_required_m0_component():
    # rev-5 §5.4(a) fixes the component set {trend, seasonal, medium, ...}; a
    # partial input must fail closed (§5.4(d) "missing matrix"), never silently
    # compute O_max on the incomplete set and pass.
    projector = np.eye(4) - np.ones((4, 4)) / 4.0
    required = ("trend", "seasonal", "medium_term")
    complete = {
        M1_SHORT_SCALE_NAME: projector,
        "trend": projector,
        "seasonal": projector,
        "medium_term": projector,
    }
    # Complete set computes without error.
    draw_overlap_omax(complete, 0.01, required_components=required)
    incomplete = {k: v for k, v in complete.items() if k != "medium_term"}
    with pytest.raises(OverlapError, match="missing required"):
        draw_overlap_omax(incomplete, 0.01, required_components=required)
    with pytest.raises(OverlapError, match="only non-M1"):
        draw_overlap_omax(
            complete, 0.01, required_components=(M1_SHORT_SCALE_NAME, "trend")
        )


def test_draw_overlap_fails_closed_on_missing_zero_and_nonfinite_matrices():
    projector = np.eye(3) - np.ones((3, 3)) / 3.0
    with pytest.raises(OverlapError, match="missing M1"):
        draw_overlap_omax({"other": projector}, 0.01)
    with pytest.raises(OverlapError, match="zero"):
        draw_overlap_omax(
            {M1_SHORT_SCALE_NAME: np.zeros((3, 3)), "other": projector},
            0.01,
        )
    with pytest.raises(OverlapError, match="zero"):
        draw_overlap_omax(
            {M1_SHORT_SCALE_NAME: projector, "other": np.zeros((3, 3))},
            0.01,
        )
    nonfinite = projector.copy()
    nonfinite[0, 0] = np.nan
    with pytest.raises(OverlapError, match="non-finite"):
        draw_overlap_omax(
            {M1_SHORT_SCALE_NAME: nonfinite, "other": projector}, 0.01
        )


def test_authority_weights_normalize_once_and_report_uniform_ess():
    raw = np.array([2.0, 2.0, 2.0, 2.0])
    authority = normalize_authority_weights("G-IS", raw)
    assert np.array_equal(authority.weights, raw / raw.sum())
    assert authority.weights.sum() == 1.0
    assert authority.ess == 4.0
    assert authority.n_draws == 4


@pytest.mark.parametrize(
    "weights",
    [[], [0.0, 0.0], [1.0, -0.1], [1.0, np.nan], [1.0, np.inf]],
)
def test_invalid_authority_weights_fail_closed(weights):
    with pytest.raises(AuthorityError):
        normalize_authority_weights("G-IS", weights)


def test_authority_precedence_and_profile_laplace_exclusion():
    assert resolve_verdict_authority({"G-IS": True, "RW-MH": True}) == "G-IS"
    assert resolve_verdict_authority({"G-IS": False, "RW-MH": True}) == "RW-MH"
    with pytest.raises(AuthorityError):
        resolve_verdict_authority(
            {"G-IS": False, "RW-MH": False, "profile-Laplace": True}
        )
    with pytest.raises(AuthorityError, match="profile-Laplace"):
        normalize_authority_weights("profile-Laplace", [1.0])


def test_select_and_normalize_authority_qualifies_via_precedence():
    # G-IS attested wins over RW-MH.
    a = select_and_normalize_authority(
        {"G-IS": True, "RW-MH": True}, {"G-IS": [1.0, 3.0], "RW-MH": [1.0]}
    )
    assert a.label == "G-IS" and a.n_draws == 2
    # RW-MH referee when G-IS is not attested.
    b = select_and_normalize_authority({"G-IS": False, "RW-MH": True}, {"RW-MH": [2.0, 2.0]})
    assert b.label == "RW-MH"
    # Strict-bool candidates: a truthy non-bool (e.g. the string "False") is rejected.
    with pytest.raises(AuthorityError, match="strict bool"):
        resolve_verdict_authority({"G-IS": "False"})
    # No usable candidate / only profile-Laplace / bad or missing weights fail closed.
    for candidates, weights in [
        ({"G-IS": False, "RW-MH": False}, {"G-IS": [1.0]}),
        ({"profile-Laplace": True}, {"profile-Laplace": [1.0]}),
        ({"G-IS": True}, {"RW-MH": [1.0]}),          # weights missing for resolved label
        ({"G-IS": True}, {"G-IS": [10 ** 400]}),      # overflow weight
        ({"G-IS": True}, {"G-IS": [0.0, 0.0]}),       # zero total
    ]:
        with pytest.raises(AuthorityError):
            select_and_normalize_authority(candidates, weights)


def test_overlap_selects_authority_internally_and_fails_closed_on_unusable():
    projector = np.eye(4) - np.ones((4, 4)) / 4.0
    draws = [_exact_draw(projector)]
    # No usable candidate (neither G-IS nor RW-MH attested) => UNDETERMINED.
    r = overlap_diagnostic(draws, [0.01], {"G-IS": False}, {"G-IS": [1.0]})
    assert r["verdict"] == "UNDETERMINED" and r["q_overlap"] is None
    # profile-Laplace can never be selected => UNDETERMINED.
    r_pl = overlap_diagnostic(draws, [0.01], {"profile-Laplace": True}, {"profile-Laplace": [1.0]})
    assert r_pl["verdict"] == "UNDETERMINED"
    # A usable, attested authority on the exact set yields a computed verdict.
    ok = overlap_diagnostic(draws, [0.01], *_auth("G-IS", [1.0]))
    assert ok["verdict"] in ("PASS", "STOP") and ok["q_overlap"] is not None


def test_overlap_pins_the_frozen_m1_name_no_relabel():
    # codex #1: the scientific wrapper must not let a caller relabel M1.  A dict
    # keyed by an alias (not the frozen short_scale) is the wrong component set
    # => UNDETERMINED, never a computed verdict.
    projector = np.eye(4) - np.ones((4, 4)) / 4.0
    aliased = {
        "alias": projector,
        **{name: projector for name in M1_OVERLAP_REQUIRED_COMPONENTS},
    }
    r = overlap_diagnostic([aliased], [0.01], *_auth("G-IS", [1.0]))
    assert r["verdict"] == "UNDETERMINED" and r["q_overlap"] is None


def test_top_level_overlap_enforces_exact_frozen_component_set():
    # rev-5 §5.4(a) fixes the set exactly; missing OR extra components fail closed
    # (§5.4(d)).  Use ORTHONORMAL centered rank-1 directions so the partial set
    # genuinely PASSes in the primitive (O_max from nugget = 1/sqrt(3) < 0.90) yet
    # is UNDETERMINED in the exact-set wrapper — the real regression codex flagged.
    u = np.array([1.0, -1.0, 0.0, 0.0]) / np.sqrt(2.0)
    v = np.array([1.0, 1.0, -2.0, 0.0]) / np.sqrt(6.0)
    w = np.array([1.0, 1.0, 1.0, -3.0]) / np.sqrt(12.0)
    U, V, W = np.outer(u, u), np.outer(v, v), np.outer(w, w)

    # Primitive on the partial (missing medium_term) set: PASS.
    partial_matrices = {M1_SHORT_SCALE_NAME: U, "trend": V, "seasonal": W}
    prim = draw_overlap_omax(partial_matrices, 1e-8)
    assert prim["o_max"] < OVERLAP_ALIGNMENT_THRESHOLD  # would PASS on its own
    assert q_overlap([prim["o_max"]], normalize_authority_weights("G-IS", [1.0]))[
        "verdict"
    ] == "PASS"
    # Scientific wrapper on the same partial set: UNDETERMINED (missing member).
    r_missing = overlap_diagnostic([partial_matrices], [1e-8], *_auth("G-IS", [1.0]))
    assert r_missing["verdict"] == "UNDETERMINED" and r_missing["q_overlap"] is None

    # Extra component beyond the frozen set: UNDETERMINED.
    projector = np.eye(4) - np.ones((4, 4)) / 4.0
    extra = dict(_exact_draw(projector), spurious=projector)
    r_extra = overlap_diagnostic([extra], [0.01], *_auth("G-IS", [1.0]))
    assert r_extra["verdict"] == "UNDETERMINED" and r_extra["q_overlap"] is None

    # The exact frozen set computes a verdict.
    ok = overlap_diagnostic([_exact_draw(projector)], [0.01], *_auth("G-IS", [1.0]))
    assert ok["verdict"] in ("PASS", "STOP") and ok["q_overlap"] is not None


def test_one_synthetic_mauna_draw_is_finite_plumbing_only():
    """Wiring/finiteness fixture only; this is not a scientific M1 verdict."""
    x = torch.arange(36, dtype=torch.float64) / 12.0
    y = 0.05 * x + 0.3 * torch.sin(2.0 * torch.pi * x)
    kernels, names = build_mauna_loa_m1_kernels()
    model, likelihood = build_model(x, y, kernels, names)

    fixed = ((4.0, 0.002), (0.8, 0.001), (1.2, 0.0015))
    for kernel, (lengthscale, outputscale) in zip(
        model.kernel_components[:-1], fixed
    ):
        kernel.base_kernel.lengthscale = lengthscale
        kernel.outputscale = outputscale
    m1 = model.kernel_components[-1]
    m1.base_kernel.lengthscale = M1_LENGTHSCALE_MEDIAN
    m1.outputscale = M1_OUTPUTSCALE_MEDIAN
    likelihood.noise = NUGGET_REFERENCE

    evaluated = model.get_component_kernel_matrices(x, x)
    matrices = {name: values["XX"] for name, values in evaluated.items()}
    report = draw_overlap_omax(
        matrices,
        likelihood.noise.item(),
        required_components=("trend", "seasonal", "medium_term"),
    )
    assert np.isfinite(report["o_max"])
    assert 0.0 <= report["o_max"] <= 1.0
    for alignment in report["o_by_component"].values():
        assert np.isfinite(alignment)
        assert 0.0 <= alignment <= 1.0
