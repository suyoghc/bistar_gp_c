"""Frozen M2c profile-core constants from prereg v1.17.

The governing rev-5 freeze package has sha256
``c3e9db66e189b2a8cad19bf11b5c4acc6518d4b6d2597ae93b0f700587d1ce3f``.
Every value here is a protocol input quoted from that package, not a tuning
parameter, with one disclosed exception: ``D23_SENTINEL_MIN_REL`` is the
test-side discrimination floor reused from the frozen v1.4 E1 D23 sentinel
(``tests/test_e1_potential.py`` ``per_site[s] > 1e-2``), which rev-5 §2a L94-95
directs the profile sentinel to mirror ("the v1.4 pattern"); rev-5 gives the
sentinel qualitatively and pins no numeric floor of its own.
"""

# P3 grid / domain (rev-5 section 1).
PROFILE_GRID_BASE_LO = 0.005
PROFILE_GRID_BASE_HI = 1.2
PROFILE_GRID_BASE_N = 40
PROFILE_GRID_RATIO = (1.2 / 0.005) ** (1.0 / 39.0)
FULL_DOMAIN_LO = 1e-7
FULL_DOMAIN_HI = 1e4
FULL_DOMAIN_N_NODES = 182
FULL_DOMAIN_N_WITH_EDGES = 184
CAP_LADDER_UPPER_DIAGNOSTIC = (10.0, 100.0, 1000.0)
CAP_LADDER_LOWER_DIAGNOSTIC = (1e-4, 1e-5, 1e-6)
EPS_DOMAIN = 1e-4
EPS_GRID = 1e-4
REFINE_L_MAX = 3
TOY_BAND_EDGES = (0.15, 0.30)

# Profile gradient battery, P1 (rev-5 section 2a).
FD_STEP_GRAD = 1e-5
TOL_GRAD_ABS = 1e-4
TOL_GRAD_REL = 1e-4
PRIOR_DRAW_SEEDS = tuple(range(100, 110))
# Test-side D23 discrimination floor, mirrored from the frozen v1.4 E1 sentinel
# (tests/test_e1_potential.py `per_site[s] > 1e-2`) per rev-5 §2a "v1.4 pattern".
D23_SENTINEL_MIN_REL = 1e-2

# Optimizer gate (rev-5 section 2b).
LBFGSB_MAXITER = 500
LBFGSB_MAXFUN = 5000
LBFGSB_FTOL = 1e-12
LBFGSB_GTOL = 1e-8
TAU_STAT = 1e-4
AGREE_DG_REL = 1e-6
AGREE_DU_INF = 1e-4
RESTART_JITTER_SCALE = 1e-3
RESTART_RNG_BASE = 300

# Curvature gate (rev-5 section 2c).
HESS_H_SWEEP = (5e-4, 1e-3, 2e-3)
HESS_H_CENTER = 1e-3
LOGDET_STABILITY_TOL = 1e-3
SYMMETRY_TOL = 1e-6
DIRECTIONAL_TOL = 1e-3
DIRECTIONAL_EPS = 1e-3
DIRECTION_RNG_SEEDS = (200, 201, 202)
RCOND_MIN = 1e-8
RETRY_GTOL = 1e-10
RETRY_FTOL = 1e-14
RETRY_MAXITER = 1000

# Frozen elsewhere (later PRs; references only): divergence rate 0.001;
# M1 correlation cap 0.95; M1-gate eigenvalue floor 1e-3; nugget reference
# 1.9e-4; SIR 0.441.
