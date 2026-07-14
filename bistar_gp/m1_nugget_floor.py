"""Report-only M1 nugget-floor predicate (prereg v1.17, rev-5 §5.5)."""

from collections.abc import Mapping

import numpy as np

from .m1_authority import (
    AuthorityError,
    NormalizedAuthority,
    VALID_VERDICT_AUTHORITIES,
    select_and_normalize_authority,
)
from .m2c_freeze_m1 import NUGGET_FLAG_THRESHOLD, NUGGET_REFERENCE


class NuggetError(ValueError):
    """Fail-closed signal for an undefined nugget-floor calculation."""


def resolve_single_noise_site(sample_keys):
    """Resolve exactly one current-or-legacy constrained noise variance site."""
    from .model import select_hmc_sites

    selected = select_hmc_sites(sample_keys)
    noise_sites = [key for key in selected if "noise_covar.noise" in key]
    if len(noise_sites) != 1:
        raise NuggetError(
            f"expected exactly one selected noise site, found {len(noise_sites)}"
        )
    return noise_sites[0]


def _validated_probability_inputs(noise_variances, authority, label):
    try:
        noises = np.asarray(noise_variances, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise NuggetError(f"{label} noise draws must be float64-compatible") from exc
    if noises.ndim != 1 or noises.size == 0:
        raise NuggetError(f"{label} noise draws must be a non-empty 1D array")
    if not np.all(np.isfinite(noises)):
        raise NuggetError(f"{label} noise draws must all be finite")
    if not isinstance(authority, NormalizedAuthority):
        raise NuggetError(f"{label} normalized authority is missing")
    if authority.label not in VALID_VERDICT_AUTHORITIES:
        raise NuggetError(f"{label} normalized authority is invalid")
    weights = np.asarray(authority.weights, dtype=np.float64)
    if authority.n_draws != noises.size or weights.shape != noises.shape:
        raise NuggetError(f"{label} authority draw count does not match noise draws")
    if not np.all(np.isfinite(weights)) or np.any(weights < 0.0):
        raise NuggetError(f"{label} normalized authority weights are invalid")
    if not np.isclose(weights.sum(), 1.0, rtol=1e-12, atol=1e-12):
        raise NuggetError(f"{label} authority weights are not normalized")
    if not np.isfinite(authority.ess) or authority.ess <= 0.0:
        raise NuggetError(f"{label} authority ESS is invalid")
    return noises, weights


def nugget_floor_predicate(
    m1_noise_variances,
    normalized_m1_authority,
    *,
    m0_noise_variances=None,
    normalized_m0_authority=None,
    predictive_gate_passes=None,
    reference=NUGGET_REFERENCE,
    flag_threshold=NUGGET_FLAG_THRESHOLD,
):
    """Calculate the weighted, strictly-below nugget-floor report.

    This low-level calculation never emits a stop or blocking verdict.
    """
    m1_noises, m1_weights = _validated_probability_inputs(
        m1_noise_variances, normalized_m1_authority, "M1"
    )
    p_below_m1 = float(np.sum(m1_weights * (m1_noises < reference)))

    if (m0_noise_variances is None) != (normalized_m0_authority is None):
        raise NuggetError("M0 noise draws and authority must be provided together")
    p_below_m0 = None
    delta_p = None
    if m0_noise_variances is not None:
        m0_noises, m0_weights = _validated_probability_inputs(
            m0_noise_variances, normalized_m0_authority, "M0"
        )
        p_below_m0 = float(np.sum(m0_weights * (m0_noises < reference)))
        delta_p = p_below_m1 - p_below_m0

    flag = bool(p_below_m1 > flag_threshold)
    predictive = (
        None if predictive_gate_passes is None else bool(predictive_gate_passes)
    )
    coincidence = None if predictive is None else bool(flag and predictive)
    return {
        "p_below_M1": p_below_m1,
        "authority": normalized_m1_authority.label,
        "ess": normalized_m1_authority.ess,
        "p_below_M0": p_below_m0,
        "delta_p": delta_p,
        "flag": flag,
        "coincidence": coincidence,
        "predictive_gate_passes": predictive,
        "reference": reference,
        "flag_threshold": flag_threshold,
    }


def _noise_values(source):
    if isinstance(source, Mapping):
        key = resolve_single_noise_site(source.keys())
        return source[key]
    return source


def _require_positive_noise(noise_variances, label):
    """A constrained noise variance is strictly positive; reject n_i <= 0."""
    values = np.asarray(noise_variances, dtype=np.float64)
    if values.size == 0 or not np.all(np.isfinite(values)) or np.any(values <= 0.0):
        raise NuggetError(f"{label} noise variances must be finite and strictly positive")
    return values


def nugget_floor_report(
    m1_noise_variances,
    m1_authority_candidates,
    m1_authority_weights_by_label,
    *,
    m0_noise_variances=None,
    m0_authority_candidates=None,
    m0_authority_weights_by_label=None,
    predictive_gate_passes=None,
):
    """SCIENTIFIC §5.5 report: complete inputs + internal precedence selection.

    Unlike the flexible primitive :func:`nugget_floor_predicate`, the scientific
    report performs the verdict-authority precedence ITSELF (via
    ``select_and_normalize_authority``) for BOTH the M1 and the same-arm M0
    authority — from caller-attested strict-bool candidate maps + per-label
    weights — so precedence cannot be bypassed with a pre-built authority.  It
    emits the full §5.5(d) coincidence record only when every input is present
    and valid, else it fails closed to ``flag="UNDETERMINED"`` (never a valid M1
    flag with ``None`` companions):
      * M1 AND same-arm M0 candidates + weights are both REQUIRED (a resolvable,
        weighted authority for each).
      * ``m0_noise_variances`` (the same-arm M0 authority's draws) is REQUIRED.
      * ``predictive_gate_passes`` must be an explicit bool (the separate M1
        predictive-improvement gate); ``None`` ⇒ UNDETERMINED.
      * every M1/M0 noise variance must be finite and strictly positive (n_i is a
        constrained variance).
    The frozen ``NUGGET_REFERENCE`` (1.9e-4) and ``NUGGET_FLAG_THRESHOLD`` (0.05)
    are PINNED here (§7 "Frozen, not open") and cannot be overridden — they are
    recorded in every completed report; threshold configurability lives only in
    the ``nugget_floor_predicate`` primitive.  A noise source may be a 1D array or
    a sample mapping (single current/legacy site resolved via
    :func:`resolve_single_noise_site`).  No input failure escapes this wrapper.
    """
    m1_authority = None
    try:
        m1_authority = select_and_normalize_authority(
            m1_authority_candidates, m1_authority_weights_by_label
        )
        if (
            m0_noise_variances is None
            or m0_authority_candidates is None
            or m0_authority_weights_by_label is None
        ):
            raise NuggetError(
                "scientific report requires the same-arm M0 noise draws + authority"
            )
        m0_authority = select_and_normalize_authority(
            m0_authority_candidates, m0_authority_weights_by_label
        )
        if not isinstance(predictive_gate_passes, bool):
            raise NuggetError(
                "scientific report requires an explicit predictive-gate boolean"
            )

        m1_noises = _require_positive_noise(_noise_values(m1_noise_variances), "M1")
        m0_noises = _require_positive_noise(_noise_values(m0_noise_variances), "M0")

        return nugget_floor_predicate(
            m1_noises,
            m1_authority,
            m0_noise_variances=m0_noises,
            normalized_m0_authority=m0_authority,
            predictive_gate_passes=predictive_gate_passes,
            reference=NUGGET_REFERENCE,
            flag_threshold=NUGGET_FLAG_THRESHOLD,
        )
    except (AuthorityError, NuggetError, TypeError, ValueError, OverflowError) as exc:
        predictive = (
            predictive_gate_passes
            if isinstance(predictive_gate_passes, bool)
            else None
        )
        return {
            "p_below_M1": None,
            "authority": getattr(m1_authority, "label", None),
            "ess": None,
            "p_below_M0": None,
            "delta_p": None,
            "flag": "UNDETERMINED",
            "coincidence": None,
            "predictive_gate_passes": predictive,
            "reference": NUGGET_REFERENCE,
            "flag_threshold": NUGGET_FLAG_THRESHOLD,
            "error": str(exc),
        }


__all__ = [
    "NuggetError",
    "resolve_single_noise_site",
    "nugget_floor_predicate",
    "nugget_floor_report",
]
