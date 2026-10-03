"""
External validation targets of van Bork, Romeijn and Wagenmakers (2025),
Synthese, doi:10.1007/s11229-025-05286-y, section 4, and a checker for the
artifact runs/vanbork_external_validation/results.json that
experiments/vanbork_external_validation.py writes on paper/case-a-vanbork.

2026-09 review FIX-8: the case script prints its errors against these targets
and never asserts them, so a regression in its own divergence or quadrature
could regenerate the artifact with wrong error fields and exit 0. This module
holds the closed forms and the assertion the script (fix pass 2) and the
tests call. The checker recomputes the errors from the stored rows instead of
trusting the stored abs_error_at_min_tau field.
"""

import json
from typing import Dict

import numpy as np

# Target A (non-overlapping point models): data prior 0.4 on s/n = 0.16 and
# 0.6 on s/n = 0.19; models theta = 0.15 and theta = 0.20; their answer is the
# data-prior mass on the nearest model.
VANBORK_TARGET_A: Dict[str, float] = {"M1 (theta=0.15)": 0.4, "M2 (theta=0.20)": 0.6}

# Target B (completely overlapping models): point data prior at theta = 1/2;
# M_x with theta ~ Beta(50, 50) against M_z with theta ~ Beta(2, 2); their
# answer is the normalized ratio of the two prior densities at that point.
VANBORK_TARGET_B_PRIORS: Dict[str, tuple] = {"M_x beta(50,50)": (50.0, 50.0),
                                             "M_z beta(2,2)": (2.0, 2.0)}
VANBORK_TARGET_B_PSI = 0.5


def vanbork_target_b_densities(psi: float = VANBORK_TARGET_B_PSI) -> Dict[str, float]:
    """The two prior densities at the data-prior point."""
    from scipy.stats import beta as beta_dist

    return {name: float(beta_dist.pdf(psi, a, b))
            for name, (a, b) in VANBORK_TARGET_B_PRIORS.items()}


def vanbork_target_b_weight(psi: float = VANBORK_TARGET_B_PSI) -> float:
    """Their closed form for p(M_x): d_x / (d_x + d_z) at double precision."""
    dens = vanbork_target_b_densities(psi)
    names = list(VANBORK_TARGET_B_PRIORS)
    return dens[names[0]] / (dens[names[0]] + dens[names[1]])


def vanbork_target_b() -> Dict[str, float]:
    w = vanbork_target_b_weight()
    names = list(VANBORK_TARGET_B_PRIORS)
    return {names[0]: w, names[1]: 1.0 - w}


def _min_tau_row(rows, names, key):
    """The smallest-tau row with every named posterior validated finite.

    Validation comes first (fix pass 1b, review R9): Python's max() keeps a
    finite first argument over a NaN and abs(nan - 1) > tol is False, so an
    unvalidated NaN column would pass both the mass check and the tolerance.
    """
    finite = [r for r in rows if np.isfinite(float(r["tau"]))]
    if not finite:
        raise AssertionError(f"external target {key}: no row carries a finite tau")
    row = min(finite, key=lambda r: float(r["tau"]))
    for n in names:
        value = float(row[n])
        if not np.isfinite(value):
            raise AssertionError(
                f"external target {key}: non-finite posterior {value!r} for {n!r} "
                f"at tau={row['tau']}")
    return row


def external_target_errors(results: dict) -> Dict[str, float]:
    """Recompute max |ours - target| at the smallest-tau row of a results.json
    payload (the per-draw route rows for Target A, the Z_M route rows for
    Target B). Raises AssertionError on a non-finite posterior."""
    a = results["target_a"]
    a_row = _min_tau_row(a["rows"], a["names"], "A")
    err_a = max(abs(float(a_row[n]) - VANBORK_TARGET_A[n]) for n in a["names"])
    b = results["target_b"]
    b_row = _min_tau_row(b["rows"], b["names"], "B")
    target_b = vanbork_target_b()
    err_b = max(abs(float(b_row[n]) - target_b[n]) for n in b["names"])
    return {"A": float(err_a), "B": float(err_b)}


def check_external_targets(results_json_path, tol_a: float = 1e-6, tol_b: float = 1e-5,
                           stored_field_tol: float = 1e-9) -> Dict[str, float]:
    """Assert that the artifact reproduces both published targets.

    Raises AssertionError naming the offending target when a recomputed error
    exceeds its tolerance, when a row's masses do not sum to one, or when the
    stored abs_error_at_min_tau field disagrees with the recomputation.
    Returns the recomputed errors.
    """
    with open(results_json_path) as f:
        results = json.load(f)
    for key, block, target in (("A", results["target_a"], VANBORK_TARGET_A),
                               ("B", results["target_b"], vanbork_target_b())):
        if set(block["names"]) != set(target):
            raise AssertionError(
                f"external target {key}: model names {block['names']} do not match "
                f"the published targets {list(target)}")
        row = _min_tau_row(block["rows"], block["names"], key)
        mass = sum(float(row[n]) for n in block["names"])
        if abs(mass - 1.0) > 1e-9:
            raise AssertionError(
                f"external target {key}: posterior masses sum to {mass!r} at tau={row['tau']}")
    errors = external_target_errors(results)
    stored = results.get("abs_error_at_min_tau", {})
    for key, tol in (("A", tol_a), ("B", tol_b)):
        if key in stored and not np.isfinite(float(stored[key])):
            raise AssertionError(
                f"external target {key}: stored abs_error_at_min_tau is {stored[key]!r}")
        if not np.isfinite(errors[key]) or errors[key] > tol:
            raise AssertionError(
                f"external target {key}: |ours - target| = {errors[key]:.3e} exceeds "
                f"tolerance {tol:.1e} at the smallest-tau row")
        if key in stored and abs(float(stored[key]) - errors[key]) > stored_field_tol:
            raise AssertionError(
                f"external target {key}: stored abs_error_at_min_tau {stored[key]!r} "
                f"disagrees with the recomputed {errors[key]!r}")
    return errors
