"""Frozen M2c divergence/MCSE constants from prereg v1.17, rev-5.

The governing freeze package sections 3, 5.3, and 7 have sha256
``c3e9db66e189b2a8cad19bf11b5c4acc6518d4b6d2597ae93b0f700587d1ce3f``.
Every value below is a protocol input, never a value inferred from a chain.

``DIVERGENCE_RATE_CAP`` is the same 0.001 value that appears only in a
reference comment in :mod:`bistar_gp.m2c_freeze` (line 62 at the freeze).
This module is its first real definition, avoiding a second inconsistent
definition.
"""

# Divergence non-clustering (rev-5 section 5.3 and section 7).
DIVERGENCE_RATE_CAP = 0.001
DIVERGENCE_CONC_FACTOR = 3
DIVERGENCE_MIN_EVENT_FLOOR = 2
DIVERGENCE_TIME_WINDOW_FRAC = 0.10

# Chain-aware MCSE_strategy (rev-5 section 3 and section 7).
MCSE_MBB_B = 1000
MCSE_MBB_SEED = 20260712
MCSE_BLOCK_LEN_FACTOR = 2
MCSE_PRECISION_GATE = 0.02

# Reference-only frozen numbers.  They are reported separately and are never
# recomputed or combined by the MCSE_strategy estimator.
MCSE_SIR_REFERENCE = 0.441
MCSE_SIR_REFERENCE_SE = 0.005
W5_INDEPENDENT_POOL_SCATTER = (0.419, 0.438, 0.431)


__all__ = [
    "DIVERGENCE_RATE_CAP",
    "DIVERGENCE_CONC_FACTOR",
    "DIVERGENCE_MIN_EVENT_FLOOR",
    "DIVERGENCE_TIME_WINDOW_FRAC",
    "MCSE_MBB_B",
    "MCSE_MBB_SEED",
    "MCSE_BLOCK_LEN_FACTOR",
    "MCSE_PRECISION_GATE",
    "MCSE_SIR_REFERENCE",
    "MCSE_SIR_REFERENCE_SE",
    "W5_INDEPENDENT_POOL_SCATTER",
]
