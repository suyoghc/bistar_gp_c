"""Chain-aware Q2 moving-block-bootstrap MCSE (rev-5 section 3).

The dependence series uses one global Boltzmann shift and ArviZ's
initial-monotone-sequence ESS implementation.  Bootstrap aggregation reuses
the canonical :func:`bistar_gp.bms_star.soft_transfer`; the ordinary SIR row
bootstrap is intentionally not reused because it is not chain-aware.

This module estimates only ``MCSE_strategy``.  It reports, but never combines
or applies, the separate G-C precision gate, deterministic SIR reference, and
W5 independent-pool scatter.  Hermetic tests use synthetic deterministic
contribution series only, never a real MCMC chain.
"""

import math

import arviz as az
import numpy as np

from .bms_star import soft_transfer
from .m2c_freeze_dm import (
    MCSE_BLOCK_LEN_FACTOR,
    MCSE_MBB_B,
    MCSE_MBB_SEED,
    MCSE_PRECISION_GATE,
    MCSE_SIR_REFERENCE,
    MCSE_SIR_REFERENCE_SE,
    W5_INDEPENDENT_POOL_SCATTER,
)


class MCSEError(RuntimeError):
    """Fail-closed signal for an undefined chain-aware MCSE."""


_SEPARATE_NOTE = (
    "MCSE_strategy is reported separately from the G-C precision gate and "
    "the W5 independent-pool scatter; MCSE_SIR is a distinct deterministic "
    "conditional-bootstrap quantity and is not recomputed here."
)


def _base_report(error=None):
    report = {
        "mcse": None,
        "verdict": "UNDETERMINED",
        "tau_int": None,
        "block_len": None,
        "B": MCSE_MBB_B,
        "seed": MCSE_MBB_SEED,
        "reported_col": None,
        "precision_gate": MCSE_PRECISION_GATE,
        "mcse_sir_reference": MCSE_SIR_REFERENCE,
        "mcse_sir_reference_se": MCSE_SIR_REFERENCE_SE,
        "w5_independent_pool_scatter": W5_INDEPENDENT_POOL_SCATTER,
        "reporting_note": _SEPARATE_NOTE,
    }
    if error is not None:
        report["error"] = str(error)
    return report


def _validated_inputs(G_chains, tau, instance_names, reported_col):
    try:
        G = np.asarray(G_chains, dtype=np.float64)
    except (TypeError, ValueError, OverflowError) as exc:
        raise MCSEError("G_chains must be float64-compatible") from exc
    if G.ndim != 3:
        raise MCSEError("G_chains must have shape (C, T, M)")
    n_chains, n_draws, n_models = G.shape
    if n_chains < 1 or n_draws < 2 or n_models < 1:
        raise MCSEError("G_chains has insufficient chains, draws, or models")
    if not np.all(np.isfinite(G)):
        raise MCSEError("G_chains contains a non-finite value")

    try:
        tau = float(tau)
    except (TypeError, ValueError, OverflowError) as exc:
        raise MCSEError("tau must be a positive finite float") from exc
    if not np.isfinite(tau) or tau <= 0.0:
        raise MCSEError("tau must be a positive finite float")

    try:
        names = tuple(instance_names)
    except TypeError as exc:
        raise MCSEError("instance_names must be an iterable of model names") from exc
    if len(names) != n_models:
        raise MCSEError(
            f"instance_names has length {len(names)}; expected {n_models}"
        )
    if any(not isinstance(name, str) or not name for name in names):
        raise MCSEError("instance_names must contain non-empty strings")
    if len(set(names)) != len(names):
        raise MCSEError("instance_names must be unique")
    if isinstance(reported_col, (bool, np.bool_)) or not isinstance(
        reported_col, (int, np.integer)
    ):
        raise MCSEError("reported_col must be an integer model-column index")
    reported_col = int(reported_col)
    if reported_col < 0 or reported_col >= n_models:
        raise MCSEError("reported_col is outside the model-column range")
    return G, tau, names, reported_col


def _maximum_iact(G, tau):
    log_weights = -G / tau
    global_shift = np.max(log_weights)
    contributions = np.exp(log_weights - global_shift)
    n_chains, n_draws, n_models = contributions.shape

    tau_values = []
    for chain in range(n_chains):
        for model in range(n_models):
            series = contributions[chain, :, model]
            variance = float(np.var(series, dtype=np.float64))
            if not np.isfinite(variance) or variance == 0.0:
                raise MCSEError(
                    f"contribution series ({chain}, {model}) has zero variance"
                )
            # Public ArviZ API: method="identity" applies the raw autocovariance
            # ESS (Geyer initial-positive then initial-monotone) to the series
            # WITHOUT rank-normalization (that is the "bulk" method); relative=
            # False returns the absolute ESS so tau_int = T/ESS.  One row here is
            # exactly one chain.
            ess = float(
                az.ess(series[np.newaxis, :], method="identity", relative=False)
            )
            if not np.isfinite(ess) or ess <= 0.0:
                raise MCSEError(
                    f"contribution series ({chain}, {model}) has undefined IACT"
                )
            tau_cell = n_draws / ess
            if not np.isfinite(tau_cell) or tau_cell <= 0.0:
                raise MCSEError(
                    f"contribution series ({chain}, {model}) has invalid IACT"
                )
            tau_values.append(tau_cell)
    return float(max(tau_values))


def mcse_strategy_estimate(G_chains, tau, instance_names, reported_col) -> dict:
    """Estimate the frozen chain-aware ``MCSE_strategy`` on a (C,T,M) array."""
    report = _base_report()
    try:
        G, tau, names, reported_col = _validated_inputs(
            G_chains, tau, instance_names, reported_col
        )
        report["reported_col"] = reported_col
        tau_int = _maximum_iact(G, tau)
        report["tau_int"] = tau_int
        block_len = int(math.ceil(MCSE_BLOCK_LEN_FACTOR * tau_int))
        report["block_len"] = block_len

        n_chains, n_draws, n_models = G.shape
        n_starts = n_draws - block_len + 1
        if n_starts < 2:
            raise MCSEError(
                "chain too short to resolve dependence: fewer than two "
                "distinct non-circular blocks"
            )

        rng = np.random.default_rng(MCSE_MBB_SEED)
        blocks_per_chain = math.ceil(n_draws / block_len)
        probabilities = np.empty(MCSE_MBB_B, dtype=np.float64)
        offsets = np.arange(block_len, dtype=np.int64)
        for replicate in range(MCSE_MBB_B):
            pooled = np.empty(
                (n_chains * n_draws, n_models), dtype=np.float64
            )
            for chain in range(n_chains):
                starts = rng.integers(
                    0, n_starts, size=blocks_per_chain, endpoint=False
                )
                indices = (starts[:, None] + offsets[None, :]).reshape(-1)
                resampled = G[chain, indices[:n_draws], :]
                first = chain * n_draws
                pooled[first : first + n_draws, :] = resampled
            result = soft_transfer(
                pooled,
                tau,
                list(names),
                normalize_per_draw=False,
            )
            probability = float(result.instance_posteriors[reported_col])
            if not np.isfinite(probability):
                raise MCSEError("soft_transfer produced a non-finite probability")
            probabilities[replicate] = probability

        mcse = float(np.std(probabilities, ddof=0))
        if not np.isfinite(mcse):
            raise MCSEError("moving-block bootstrap produced a non-finite MCSE")
        report.update({"mcse": mcse, "verdict": "DETERMINED"})
        return report
    except (MCSEError, TypeError, ValueError, OverflowError, FloatingPointError) as exc:
        report["mcse"] = None
        report["verdict"] = "UNDETERMINED"
        report["error"] = str(exc)
        return report


__all__ = ["MCSEError", "mcse_strategy_estimate"]
