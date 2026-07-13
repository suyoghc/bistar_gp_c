"""Frozen M2c S2/S3 constants from prereg v1.17, rev-5 §§5.1-5.2.

The governing freeze package has sha256
``c3e9db66e189b2a8cad19bf11b5c4acc6518d4b6d2597ae93b0f700587d1ce3f``.
Every value below is a protocol input quoted from that package.  PR-A's
profile constants remain in :mod:`bistar_gp.m2c_freeze`; the distinct S2
curvature rule is deliberately defined here rather than cross-applied there.
"""

# S2 fixed MAP-Hessian metric (rev-5 §5.1).
S2_FD_STEP = 1e-5
S2_STABILITY_MULTIPLIERS = (0.5, 1.0, 2.0)
S2_SKEW_TOL = 1e-5
S2_STEP_STABILITY_TOL = 1e-3
S2_DIRECTIONAL_TOL = 1e-3
S2_WHITENING_TOL = 1e-8
S2_EIG_FLOOR = 1e-6
S2_ORACLE_TOL = 1e-10

# S3 M0 seven-coordinate reparameterization (rev-5 §5.2).
S3_SLOGDET_TOL = 1e-10
S3_ROUNDTRIP_TOL = 1e-10
S3_DENSITY_TOL = 1e-9
S3_GRAD_ABS = 1e-4
S3_GRAD_REL = 1e-4
S3_N_STATES = 33
S3_PRIOR_DRAW_SEEDS = tuple(range(100, 110))
S3_NEIGHBORHOOD_SEEDS = (0, 1, 2, 3, 4)
S3_NEIGHBORHOOD_SIGMAS = (0.1, 1.0)
