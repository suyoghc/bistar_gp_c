"""Fail-closed divergence non-clustering predicate (rev-5 section 5.3).

The governing schema records only per-chain post-warmup draw indices.  It has
no parameter values, so parameter-band clustering is honestly unevaluable
without a schema extension.  This predicate evaluates only the frozen rate,
chain-concentration, and per-chain time-window gates; every report carries the
schema limitation explicitly so a PASS cannot be read more broadly.
"""

import math
from numbers import Integral

from .m2c_freeze_dm import (
    DIVERGENCE_CONC_FACTOR,
    DIVERGENCE_MIN_EVENT_FLOOR,
    DIVERGENCE_RATE_CAP,
    DIVERGENCE_TIME_WINDOW_FRAC,
)


class DivergenceError(RuntimeError):
    """Fail-closed signal for an undefined divergence predicate."""


def _empty_report(error=None):
    report = {
        "verdict": "UNDETERMINED",
        "rate": None,
        "rate_cap": DIVERGENCE_RATE_CAP,
        "d_max": None,
        "L_chain": None,
        "time_max": None,
        "L_time": None,
        "w": None,
        "n_divergences": None,
        "failed_gates": [],
        "divergence_concentration_factor": DIVERGENCE_CONC_FACTOR,
        "divergence_min_event_floor": DIVERGENCE_MIN_EVENT_FLOOR,
        "divergence_time_window_frac": DIVERGENCE_TIME_WINDOW_FRAC,
        "parameter_band_clustering": "unevaluable-schema-limited",
    }
    if error is not None:
        report["error"] = str(error)
    return report


def _positive_int(value, label):
    if isinstance(value, bool) or not isinstance(value, Integral) or value <= 0:
        raise DivergenceError(f"{label} must be a positive integer")
    return int(value)


def _validated_draws(diagnostics, n_chains, n_draws):
    draws = diagnostics.divergence_draws
    if draws is None:
        raise DivergenceError("divergence_draws is unavailable")
    if len(draws) != n_chains:
        raise DivergenceError(
            f"divergence_draws has {len(draws)} chains; expected {n_chains}"
        )

    validated = []
    for chain_index, chain in enumerate(draws):
        try:
            indices = tuple(chain)
        except TypeError as exc:
            raise DivergenceError(
                f"divergence_draws chain {chain_index} is not iterable"
            ) from exc
        if any(
            isinstance(index, bool) or not isinstance(index, Integral)
            for index in indices
        ):
            raise DivergenceError(
                f"divergence_draws chain {chain_index} must contain integers"
            )
        indices = tuple(int(index) for index in indices)
        if any(index < 0 or index >= n_draws for index in indices):
            raise DivergenceError(
                f"divergence_draws chain {chain_index} has an out-of-range index"
            )
        if any(left >= right for left, right in zip(indices, indices[1:])):
            raise DivergenceError(
                f"divergence_draws chain {chain_index} must be unique and sorted"
            )
        validated.append(indices)
    return tuple(validated)


def _maximum_window_count(indices, width, n_draws):
    """Maximum event count in any valid integer-start half-open window."""
    if not indices:
        return 0
    if width > n_draws:
        return len(indices)

    maximum = 0
    left = 0
    for right, event in enumerate(indices):
        while event - indices[left] >= width:
            left += 1
        maximum = max(maximum, right - left + 1)
    return maximum


def divergence_nonclustering(diagnostics) -> dict:
    """Evaluate the frozen divergence gates, returning UNDETERMINED on bad input.

    The result always contains the same core fields.  Missing, duplicate,
    unsorted, inconsistent, or insufficient inputs never become a false zero
    or PASS.
    """
    try:
        n_chains = _positive_int(diagnostics.n_chains, "n_chains")
        n_draws = _positive_int(diagnostics.n_draws, "n_draws")
        draws = _validated_draws(diagnostics, n_chains, n_draws)

        n_divergences = tuple(len(chain) for chain in draws)
        total = sum(n_divergences)
        rate = total / float(n_chains * n_draws)
        try:
            reported_rate = diagnostics.divergence_rate
        except Exception as exc:
            raise DivergenceError("divergence_rate could not be read") from exc
        if (
            reported_rate is None
            or not math.isfinite(float(reported_rate))
            or not math.isclose(
                float(reported_rate), rate, rel_tol=1e-12, abs_tol=1e-15
            )
        ):
            raise DivergenceError(
                "reported divergence_rate does not match the per-chain indices"
            )

        d_max = max(n_divergences)
        L_chain = max(
            DIVERGENCE_MIN_EVENT_FLOOR,
            math.ceil(DIVERGENCE_CONC_FACTOR * total / n_chains),
        )
        width = math.ceil(DIVERGENCE_TIME_WINDOW_FRAC * n_draws)
        time_max = max(
            _maximum_window_count(chain, width, n_draws) for chain in draws
        )
        L_time = max(
            DIVERGENCE_MIN_EVENT_FLOOR,
            math.ceil(
                DIVERGENCE_CONC_FACTOR
                * (total / n_chains)
                * width
                / n_draws
            ),
        )

        failed_gates = []
        if rate > DIVERGENCE_RATE_CAP:
            failed_gates.append("rate")
        if d_max > L_chain:
            failed_gates.append("chain")
        if time_max > L_time:
            failed_gates.append("time")

        return {
            "verdict": "FAIL" if failed_gates else "PASS",
            "rate": rate,
            "rate_cap": DIVERGENCE_RATE_CAP,
            "d_max": d_max,
            "L_chain": L_chain,
            "time_max": time_max,
            "L_time": L_time,
            "w": width,
            "n_divergences": n_divergences,
            "failed_gates": failed_gates,
            "divergence_concentration_factor": DIVERGENCE_CONC_FACTOR,
            "divergence_min_event_floor": DIVERGENCE_MIN_EVENT_FLOOR,
            "divergence_time_window_frac": DIVERGENCE_TIME_WINDOW_FRAC,
            "parameter_band_clustering": "unevaluable-schema-limited",
        }
    except (DivergenceError, AttributeError, TypeError, ValueError, OverflowError) as exc:
        return _empty_report(exc)


__all__ = ["DivergenceError", "divergence_nonclustering"]
