"""Centered covariance-overlap diagnostic (prereg v1.17, rev-5 §5.4).

The statistic is the specified Frobenius alignment of centered covariance
matrices.  It deliberately performs no eigenvalue flooring or SPD projection.
"""

from collections.abc import Mapping

import numpy as np

from .m1_authority import (
    AuthorityError,
    NormalizedAuthority,
    VALID_VERDICT_AUTHORITIES,
    select_and_normalize_authority,
)
from .m2c_freeze_m1 import (
    M1_OVERLAP_REQUIRED_COMPONENTS,
    M1_SHORT_SCALE_NAME,
    OVERLAP_ALIGNMENT_THRESHOLD,
    Q_OVERLAP_CAP,
)


class OverlapError(RuntimeError):
    """Fail-closed signal for an undefined covariance-overlap diagnostic."""


def _as_float64_matrix(value, label):
    if hasattr(value, "detach"):
        value = value.detach().cpu().numpy()
    try:
        matrix = np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise OverlapError(f"{label} is not a float64 matrix") from exc
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise OverlapError(f"{label} must be square")
    if matrix.shape[0] == 0:
        raise OverlapError(f"{label} must be non-empty")
    if not np.all(np.isfinite(matrix)):
        raise OverlapError(f"{label} contains a non-finite entry")
    return matrix


def centered_frobenius_alignment(A, B):
    """Return the Frobenius cosine of two already-centered matrices."""
    left = _as_float64_matrix(A, "A")
    right = _as_float64_matrix(B, "B")
    if left.shape != right.shape:
        raise OverlapError(
            f"A and B shapes differ: {left.shape} != {right.shape}"
        )

    norm_left = np.sqrt(np.sum(left * left))
    norm_right = np.sqrt(np.sum(right * right))
    if not np.isfinite(norm_left) or norm_left == 0.0:
        raise OverlapError("A has zero or non-finite Frobenius norm")
    if not np.isfinite(norm_right) or norm_right == 0.0:
        raise OverlapError("B has zero or non-finite Frobenius norm")

    alignment = float(np.sum(left * right) / (norm_left * norm_right))
    if not np.isfinite(alignment):
        raise OverlapError("Frobenius alignment is non-finite")
    if 1.0 < alignment <= 1.0 + 1e-12:
        return 1.0
    if -1.0 - 1e-12 <= alignment < -1.0:
        return -1.0
    if alignment < -1.0 or alignment > 1.0:
        raise OverlapError(f"Frobenius alignment is outside [-1, 1]: {alignment}")
    return alignment


def _center(matrix, projector, label):
    # Some BLAS builds emit spurious floating-point warnings during otherwise
    # finite matmul.  Validate the result explicitly so real overflow/nonfinite
    # failures still fail closed without leaking backend warnings.
    with np.errstate(all="ignore"):
        centered = projector @ matrix @ projector
    return _as_float64_matrix(centered, label)


def draw_overlap_omax(
    component_matrices,
    noise_variance,
    *,
    m1_name=M1_SHORT_SCALE_NAME,
    required_components=None,
):
    """Compute all centered alignments and O_max for one authority draw.

    ``required_components`` names the non-M1 covariance components that MUST be
    present for a valid diagnostic (for the frozen Mauna P-comb+M1 arm:
    ``trend``, ``seasonal``, ``medium_term``).  Per rev-5 §5.4(a) the overlap is
    defined against that specific set, and §5.4(d) requires a missing matrix to
    fail closed; when supplied, any absent required component raises
    ``OverlapError`` rather than silently computing on a partial set.  The
    algebraic fixtures leave it ``None`` to exercise the primitive directly.
    """
    if not isinstance(component_matrices, Mapping):
        raise OverlapError("component_matrices must be a name-to-matrix mapping")
    if m1_name not in component_matrices:
        raise OverlapError(f"missing M1 component {m1_name!r}")
    if required_components is not None:
        if m1_name in required_components:
            raise OverlapError(
                "required_components must list only non-M1 components"
            )
        missing = [
            name for name in required_components if name not in component_matrices
        ]
        if missing:
            raise OverlapError(
                f"missing required non-M1 component matrices: {sorted(missing)}"
            )

    matrices = {
        name: _as_float64_matrix(matrix, f"component {name!r}")
        for name, matrix in component_matrices.items()
    }
    m1_matrix = matrices[m1_name]
    shape = m1_matrix.shape
    for name, matrix in matrices.items():
        if matrix.shape != shape:
            raise OverlapError(
                f"component {name!r} shape {matrix.shape} does not match {shape}"
            )

    try:
        noise = float(noise_variance)
    except (TypeError, ValueError) as exc:
        raise OverlapError("noise variance must be a finite positive scalar") from exc
    if not np.isfinite(noise) or noise <= 0.0:
        raise OverlapError("noise variance must be a finite positive scalar")

    n = shape[0]
    projector = np.eye(n, dtype=np.float64) - (
        np.ones((n, n), dtype=np.float64) / n
    )
    centered_m1 = _center(m1_matrix, projector, "centered M1 component")

    non_m1 = {name: matrix for name, matrix in matrices.items() if name != m1_name}
    rest = noise * np.eye(n, dtype=np.float64)
    centered_others = {}
    for name, matrix in non_m1.items():
        centered_others[name] = _center(
            matrix, projector, f"centered component {name!r}"
        )
        rest = rest + matrix
    centered_others["nugget"] = _center(
        noise * np.eye(n, dtype=np.float64), projector, "centered nugget"
    )
    centered_others["rest"] = _center(rest, projector, "centered rest")

    alignments = {
        name: centered_frobenius_alignment(centered_m1, matrix)
        for name, matrix in centered_others.items()
    }
    return {
        "o_max": max(alignments.values()),
        "o_by_component": alignments,
        "n": n,
    }


def _validated_authority_weights(normalized_authority, n_draws):
    if not isinstance(normalized_authority, NormalizedAuthority):
        raise OverlapError("missing normalized verdict authority")
    if normalized_authority.label not in VALID_VERDICT_AUTHORITIES:
        raise OverlapError("invalid normalized verdict authority")
    weights = np.asarray(normalized_authority.weights, dtype=np.float64)
    if weights.ndim != 1 or normalized_authority.n_draws != n_draws:
        raise OverlapError("authority draw count does not match overlap draws")
    if weights.size != n_draws or not np.all(np.isfinite(weights)):
        raise OverlapError("normalized authority weights are invalid")
    if np.any(weights < 0.0) or not np.isclose(
        weights.sum(), 1.0, rtol=1e-12, atol=1e-12
    ):
        raise OverlapError("authority weights are not normalized")
    if not np.isfinite(normalized_authority.ess) or normalized_authority.ess <= 0.0:
        raise OverlapError("authority ESS is invalid")
    return weights


def q_overlap(
    per_draw_omax,
    normalized_authority,
    *,
    alignment_threshold=OVERLAP_ALIGNMENT_THRESHOLD,
    cap=Q_OVERLAP_CAP,
):
    """Return the authority-weighted duplicate mass and its blocking verdict."""
    values = np.asarray(per_draw_omax, dtype=np.float64)
    if values.ndim != 1 or values.size == 0 or not np.all(np.isfinite(values)):
        raise OverlapError("per-draw O_max must be a non-empty finite 1D array")
    if np.any(values < -1.0) or np.any(values > 1.0):
        raise OverlapError("per-draw O_max values must lie in [-1, 1]")
    weights = _validated_authority_weights(normalized_authority, values.size)

    duplicate_mass = float(np.sum(weights * (values >= alignment_threshold)))
    return {
        "q_overlap": duplicate_mass,
        "verdict": "STOP" if duplicate_mass > cap else "PASS",
        "threshold": alignment_threshold,
        "cap": cap,
        "authority": normalized_authority.label,
        "ess": normalized_authority.ess,
    }


def _require_exact_component_set(component_matrices):
    """Enforce rev-5 §5.4(a)'s EXACT frozen scientific component set.

    §5.4 fixes j to {trend, seasonal, medium, nugget, rest}; nugget and rest are
    derived, so each draw's supplied matrices must be EXACTLY the frozen M1
    component ``M1_SHORT_SCALE_NAME`` plus ``M1_OVERLAP_REQUIRED_COMPONENTS`` — no
    missing member and no extra component (an unexpected extra would silently
    change K_rest), and the M1 key cannot be relabelled.  Any deviation fails
    closed (§5.4(d)).
    """
    if not isinstance(component_matrices, Mapping):
        raise OverlapError("component_matrices must be a name-to-matrix mapping")
    expected = frozenset(M1_OVERLAP_REQUIRED_COMPONENTS) | {M1_SHORT_SCALE_NAME}
    actual = frozenset(component_matrices)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise OverlapError(
            "overlap scientific component set must be exactly "
            f"{sorted(expected)}; missing={missing}, unexpected={extra}"
        )


def overlap_diagnostic(
    per_draw_component_matrices,
    noise_variances,
    authority_candidates,
    authority_weights_by_label,
    *,
    alignment_threshold=OVERLAP_ALIGNMENT_THRESHOLD,
    cap=Q_OVERLAP_CAP,
):
    """Scientific M1-overlap gate: exact frozen set + internal precedence selection.

    This is the SCIENTIFIC wrapper (not the algebraic primitive
    :func:`draw_overlap_omax`).  It performs the verdict-authority precedence
    ITSELF: ``authority_candidates`` (label -> attested-qualified strict bool) and
    ``authority_weights_by_label`` (label -> weights) are resolved via
    ``select_and_normalize_authority`` (G-IS-first, else RW-MH; profile-Laplace
    never; rev-5 §5.4(e)/§6.8) — a caller cannot bypass precedence by handing in a
    pre-built authority.  The M1 component key is PINNED to the frozen
    ``M1_SHORT_SCALE_NAME`` (not caller-relabelable), and each draw's
    ``component_matrices`` must be EXACTLY that plus ``M1_OVERLAP_REQUIRED_COMPONENTS``
    — missing OR extra components fail closed (§5.4(a)/(d)).

    Verdict encoding of rev-5 §5.4(d) — every failure blocks P-comb+M1-v1
    promotion (M0/other arms continue):
      * ``STOP``          — a computed ``q_overlap`` that exceeds the 0.05 cap.
      * ``UNDETERMINED``  — any un-computable input: a zero/missing/non-finite
        matrix, a wrong component set, or a missing/unusable/invalid authority.
        §5.4(d) lists these under "STOP for promotion"; the task's restatement
        writes "UNDETERMINED/STOP", so the un-computable branch is UNDETERMINED
        and never PASS.
    """
    authority = None
    try:
        authority = select_and_normalize_authority(
            authority_candidates, authority_weights_by_label
        )
        draws = list(per_draw_component_matrices)
        noises = np.asarray(noise_variances, dtype=np.float64)
        if noises.ndim != 1 or noises.size != len(draws):
            raise OverlapError("noise draw count does not match covariance draws")
        draw_reports = []
        for matrices, noise in zip(draws, noises):
            _require_exact_component_set(matrices)
            draw_reports.append(
                draw_overlap_omax(
                    matrices,
                    noise,
                    m1_name=M1_SHORT_SCALE_NAME,
                    required_components=M1_OVERLAP_REQUIRED_COMPONENTS,
                )
            )
        report = q_overlap(
            [draw["o_max"] for draw in draw_reports],
            authority,
            alignment_threshold=alignment_threshold,
            cap=cap,
        )
        report["draws"] = draw_reports
        return report
    except (AuthorityError, OverlapError, TypeError, ValueError, OverflowError) as exc:
        return {
            "q_overlap": None,
            "verdict": "UNDETERMINED",
            "threshold": alignment_threshold,
            "cap": cap,
            "authority": getattr(authority, "label", None),
            "ess": None,
            "draws": None,
            "error": str(exc),
        }


__all__ = [
    "OverlapError",
    "centered_frobenius_alignment",
    "draw_overlap_omax",
    "q_overlap",
    "overlap_diagnostic",
]
