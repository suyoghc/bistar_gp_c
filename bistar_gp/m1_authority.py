"""Shared M1 verdict-authority and weight contract (rev-5 §§5.4-5.5).

Authority provenance boundary (honest statement of what PR C does and does NOT
enforce).  The frozen contract is: the verdict authority is a G-IS-passing IS
first, else a crossing-verified RW-MH referee; profile-Laplace may NOT issue a
promotion verdict.  The top-level scientific gates never accept a pre-built
authority object; they take a caller-supplied ``candidates`` map (label ->
attested-qualified strict bool) plus per-label weights and perform the precedence
selection THEMSELVES via :func:`select_and_normalize_authority`, so
:func:`resolve_verdict_authority` is always on the required path and a bare label
or hand-built authority cannot drive a verdict.

PR C is HERMETIC: it runs no chains, so it CANNOT itself prove that a "G-IS"
candidate passed its G-IS check or that an "RW-MH" candidate was crossing-
verified.  Those qualification booleans are therefore CALLER-ATTESTED here and
are validated only by PR D's real chains.  PR C enforces the precedence
STRUCTURE (order, profile-Laplace exclusion) and the weight/ESS/label contract,
NOT the underlying G-IS/RW-MH facts.  The arithmetic primitives
(:func:`normalize_authority_weights`, ``q_overlap``, ``nugget_floor_predicate``)
remain usable with a bare authority; only the scientific wrappers require
precedence selection.
"""

from collections.abc import Mapping
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
    """Validate and normalize one verdict authority's draw weights once.

    This is the arithmetic weight contract, NOT proof that the authority
    satisfies the frozen precedence (that is :func:`select_and_normalize_authority`).
    """
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
    """Select G-IS first, then a crossing-verified RW-MH referee.

    ``candidates`` maps a label to its (CALLER-ATTESTED) qualification bool.  Each
    value must be a STRICT ``bool`` (a truthy non-bool such as the string
    ``"False"`` is rejected, not silently treated as qualified).  profile-Laplace
    is never selected (it is not a verdict authority).  Raises ``AuthorityError``
    (=> UNDETERMINED) when neither G-IS nor RW-MH is usable.
    """
    if not isinstance(candidates, Mapping):
        raise AuthorityError("authority candidates must be a label->qualified mapping")
    for key, value in candidates.items():
        if not isinstance(value, bool):
            raise AuthorityError(
                f"authority candidate {key!r} must be a strict bool, got {type(value).__name__}"
            )
    for label in VALID_VERDICT_AUTHORITIES:
        if candidates.get(label, False):
            return label
    raise AuthorityError("no usable G-IS or RW-MH verdict authority")


def select_and_normalize_authority(candidates, weights_by_label):
    """Apply the frozen precedence, THEN the weight contract.

    ``candidates``: label -> attested-qualified strict bool (G-IS passed its G-IS
    check; RW-MH crossing-verified).  These booleans are CALLER-ATTESTED in
    hermetic PR C and validated only by PR D's chains — see the module docstring.
    ``weights_by_label``: label -> per-draw weights for that authority.
    Returns the ``NormalizedAuthority`` for the precedence-selected label, or
    raises ``AuthorityError`` (=> UNDETERMINED) if none is usable or its weights
    are missing.  The scientific gates call this internally, so precedence
    selection cannot be bypassed by handing them a pre-built authority.
    """
    label = resolve_verdict_authority(candidates)
    if not isinstance(weights_by_label, Mapping) or label not in weights_by_label:
        raise AuthorityError(
            f"no weights supplied for the resolved verdict authority {label!r}"
        )
    return normalize_authority_weights(label, weights_by_label[label])


__all__ = [
    "VALID_VERDICT_AUTHORITIES",
    "PROFILE_LAPLACE_LABEL",
    "AuthorityError",
    "NormalizedAuthority",
    "normalize_authority_weights",
    "resolve_verdict_authority",
    "select_and_normalize_authority",
]
