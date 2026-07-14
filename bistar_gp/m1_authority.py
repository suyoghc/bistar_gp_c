"""Shared M1 verdict-authority and weight contract (rev-5 §§5.4-5.5)."""

from dataclasses import dataclass

import numpy as np


VALID_VERDICT_AUTHORITIES = ("G-IS", "RW-MH")
PROFILE_LAPLACE_LABEL = "profile-Laplace"


class AuthorityError(ValueError):
    """Fail-closed signal for an unusable M1 verdict authority."""


@dataclass(frozen=True)
class NormalizedAuthority:
    """A selected authority with weights normalized exactly once."""

    label: str
    weights: np.ndarray
    ess: float
    n_draws: int


def normalize_authority_weights(label, weights):
    """Validate and normalize one verdict authority's draw weights once."""
    if label == PROFILE_LAPLACE_LABEL:
        raise AuthorityError("profile-Laplace cannot issue this verdict")
    if label not in VALID_VERDICT_AUTHORITIES:
        raise AuthorityError(f"invalid verdict authority: {label!r}")

    try:
        values = np.asarray(weights, dtype=np.float64)
    except (TypeError, ValueError, OverflowError) as exc:
        # OverflowError: a Python int too large for float64 is a "bad weight",
        # which the authority contract requires to fail closed (UNDETERMINED),
        # never to escape as an unstructured exception.
        raise AuthorityError("authority weights must be float64-compatible") from exc
    if values.ndim != 1 or values.size == 0:
        raise AuthorityError("authority weights must be a non-empty 1D array")
    if not np.all(np.isfinite(values)):
        raise AuthorityError("authority weights must all be finite")
    if np.any(values < 0.0):
        raise AuthorityError("authority weights must all be nonnegative")
    total = values.sum()
    if not np.isfinite(total) or total <= 0.0:
        raise AuthorityError("authority weights must have positive finite total")

    normalized = values / total
    ess = 1.0 / np.sum(normalized ** 2)
    return NormalizedAuthority(label, normalized, float(ess), len(values))


def resolve_verdict_authority(candidates):
    """Select G-IS first, then a crossing-verified RW-MH referee."""
    for label in VALID_VERDICT_AUTHORITIES:
        if bool(candidates.get(label, False)):
            return label
    raise AuthorityError("no usable G-IS or RW-MH verdict authority")


__all__ = [
    "VALID_VERDICT_AUTHORITIES",
    "PROFILE_LAPLACE_LABEL",
    "AuthorityError",
    "NormalizedAuthority",
    "normalize_authority_weights",
    "resolve_verdict_authority",
]
