"""Frozen M2c M1 constants from prereg v1.17, rev-5 §§5.4-5.5.

The governing freeze package has sha256
``c3e9db66e189b2a8cad19bf11b5c4acc6518d4b6d2597ae93b0f700587d1ce3f``.
Every value below is a protocol input quoted from that package.  The two
reference-only values are pinned for provenance but never applied in PR C;
in particular, the overlap statistic uses no eigenvalue flooring or SPD
projection.
"""

import math


# §5.4 overlap thresholds (rev-5 §5.4, §7 table).
OVERLAP_ALIGNMENT_THRESHOLD = 0.90
Q_OVERLAP_CAP = 0.05

# M1 Matern-3/2 frozen prior (experiments/d19_prior_scorecard.py:120;
# docs/plan-d19-mauna.md:892; Notes/DECISIONS.md A3 ~L1112).
M1_OUTPUTSCALE_MEDIAN = 2.4e-4
M1_OUTPUTSCALE_SIGMA = 1.2
M1_LENGTHSCALE_Z_LOC = -1.2528
M1_LENGTHSCALE_Z_SCALE = 1.082
M1_LENGTHSCALE_LOWER = 0.1
M1_LENGTHSCALE_UPPER = 1.0
M1_MATERN_NU = 1.5
M1_LENGTHSCALE_QREF = (0.16, 0.30, 0.58)
M1_LENGTHSCALE_MEDIAN = 0.30
M1_SHORT_SCALE_NAME = "short_scale"
# Frozen non-M1 named component set the §5.4 overlap gate must see for the
# Mauna P-comb+M1-v1 promotion arm (rev-5 §5.4(a) j ∈ {trend, seasonal, medium,
# ...}; build_mauna_loa_kernels() names them "trend"/"seasonal"/"medium_term",
# shared across all Mauna arms).  The top-level overlap_diagnostic requires
# these present by default so a partial input fails closed per §5.4(d).
M1_OVERLAP_REQUIRED_COMPONENTS = ("trend", "seasonal", "medium_term")

# §5.5 nugget-floor (rev-5 §5.5, §7 table).
NUGGET_REFERENCE = 1.9e-4
NUGGET_FLAG_THRESHOLD = 0.05

# Reference-only frozen values.  Neither is applied by PR C.
M1_CORRELATION_CAP_REFERENCE_ONLY = 0.95
M1_GATE_EIGENVALUE_FLOOR_REFERENCE_ONLY = 1e-3


__all__ = [
    "OVERLAP_ALIGNMENT_THRESHOLD",
    "Q_OVERLAP_CAP",
    "M1_OUTPUTSCALE_MEDIAN",
    "M1_OUTPUTSCALE_SIGMA",
    "M1_LENGTHSCALE_Z_LOC",
    "M1_LENGTHSCALE_Z_SCALE",
    "M1_LENGTHSCALE_LOWER",
    "M1_LENGTHSCALE_UPPER",
    "M1_MATERN_NU",
    "M1_LENGTHSCALE_QREF",
    "M1_LENGTHSCALE_MEDIAN",
    "M1_SHORT_SCALE_NAME",
    "M1_OVERLAP_REQUIRED_COMPONENTS",
    "NUGGET_REFERENCE",
    "NUGGET_FLAG_THRESHOLD",
    "M1_CORRELATION_CAP_REFERENCE_ONLY",
    "M1_GATE_EIGENVALUE_FLOOR_REFERENCE_ONLY",
]
