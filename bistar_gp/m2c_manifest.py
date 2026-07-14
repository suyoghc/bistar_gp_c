"""Builders for the append-only M2c v1.17 algorithm manifest.

The committed v1.17 document is immutable: any revision is a new addendum,
never an edit.  This module reconstructs its machine-independent algorithm
portion from the already-frozen code constants and separately captures benign,
descriptive freeze-environment provenance.  It performs no scientific
computation and reads no sampler, chain, Mauna, holdout, or run artifact.
"""

import hashlib
import importlib.metadata
import json
import os
import platform
from pathlib import Path

import numpy as np
import torch

from . import m2c_freeze as profile
from . import m2c_freeze_dm as dm
from . import m2c_freeze_m1 as m1
from . import m2c_freeze_s2s3 as s2s3


# The exact PR-D IMPLEMENTATION snapshot: the commit that CONTAINS the §5.3
# divergence / §3 MCSE / manifest-builder algorithm code (COMMIT A of the
# two-stage construction).  A committed manifest cannot embed its own commit sha,
# so the immutable manifest artifact is added in the FOLLOWING commit (COMMIT B),
# which references this snapshot.  Checking out this sha reproduces the frozen
# algorithm; the manifest==code CI additionally pins the manifest to that live
# code (every frozen constant + the live ``profile_integration.py`` sha256).
FROZEN_AT_GIT_SHA = "6d39d38ad000583fcbb4e5311efe57ff5e0c1503"

FROZEN_AT_GIT_SHA_MEANING = (
    "Exact PR-D implementation snapshot; the immutable manifest artifact was "
    "added in the following commit."
)


def _profile_integration_sha256():
    path = Path(__file__).with_name("profile_integration.py")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tolerance(name, value, rationale, tag, test):
    return {
        "name": name,
        "value": value,
        "rationale": rationale,
        "tag": tag,
        "test": test,
    }


def build_v117_algorithm_manifest() -> dict:
    """Return the deterministic, machine-independent v1.17 manifest portion."""
    refs_test = (
        "tests/test_m2c_manifest.py::test_reference_constants_match_frozen_values"
    )
    s2_test = (
        "tests/test_m2c_s2_fixed_metric.py::"
        "test_seedless_quadratic_oracle_recovers_position_mass_not_inverse"
    )
    s3_test = (
        "tests/test_m2c_s3_reparam.py::"
        "test_m0_roles_and_33_state_equivalence_battery"
    )
    profile_test = (
        "tests/test_m2c_profile_integration.py::"
        "test_corrected_profile_band_masses_matches_gaussian_oracle"
    )

    references = [
        {
            "name": "prior_is_toy_elicited_band_masses",
            "value": [0.762660, 0.191078, 0.046262],
            "se": [0.004283, 0.003838, 0.000866],
            "source": "docs/prereg-addenda-d19.md:1279-1281",
            "test": refs_test,
        },
        {
            "name": "rw_mh_toy_elicited_pooled_band_masses",
            "value": [0.815644, 0.161078, 0.023278],
            "se": [0.023483, 0.017650, 0.010167],
            "source": "docs/prereg-addenda-d19.md:1281-1282",
            "test": refs_test,
        },
        {
            "name": "sir_sin_linear_tau1_probability",
            "value": dm.MCSE_SIR_REFERENCE,
            "se": dm.MCSE_SIR_REFERENCE_SE,
            "source": "docs/prereg-addenda-d19.md:1282-1283",
            "test": refs_test,
        },
        {
            "name": "w5_independent_pool_scatter",
            "value": list(dm.W5_INDEPENDENT_POOL_SCATTER),
            "source": "docs/m2c-gtoy-profile-PROPOSAL.md:123-125",
            "test": refs_test,
        },
    ]

    algorithm = {
        "profile_integration_sha256": _profile_integration_sha256(),
        "grid": {
            "base": {
                "lo": profile.PROFILE_GRID_BASE_LO,
                "hi": profile.PROFILE_GRID_BASE_HI,
                "n": profile.PROFILE_GRID_BASE_N,
            },
            "ratio_expr": "(1.2/0.005)^(1/39)",
            "ratio_f64": profile.PROFILE_GRID_RATIO,
            "full_domain": {
                "lo": profile.FULL_DOMAIN_LO,
                "hi": profile.FULL_DOMAIN_HI,
                "n_nodes": profile.FULL_DOMAIN_N_NODES,
                "n_with_toy_edges": profile.FULL_DOMAIN_N_WITH_EDGES,
            },
            "cap_ladders_diagnostic": {
                "upper": list(profile.CAP_LADDER_UPPER_DIAGNOSTIC),
                "lower": list(profile.CAP_LADDER_LOWER_DIAGNOSTIC),
            },
            "max_nodes": profile.FULL_DOMAIN_N_WITH_EDGES,
            "test": (
                "tests/test_m2c_profile_integration.py::"
                "test_p3_grid_geometry_and_nested_refinement"
            ),
        },
        "p3": {
            "eps_domain": profile.EPS_DOMAIN,
            "eps_grid": profile.EPS_GRID,
            "l_max": profile.REFINE_L_MAX,
            "nested_construction": "retain prior nodes; insert geometric midpoints",
            "test": profile_test,
        },
        "gradient_battery": {
            "fd_step": profile.FD_STEP_GRAD,
            "tol_abs": profile.TOL_GRAD_ABS,
            "tol_rel": profile.TOL_GRAD_REL,
            "point_set": {
                "conditional_optima": "every profile-grid node",
                "structures": ["synthetic-toy", "synthetic-mauna-structure"],
                "prior_draw_seeds": list(profile.PRIOR_DRAW_SEEDS),
            },
            "d23_sentinel": {
                "behavior": "naive data-injection remains disconnected",
                "min_relative_difference": profile.D23_SENTINEL_MIN_REL,
            },
            "test": (
                "tests/test_m2c_profile_gradient.py::"
                "test_functional_gradient_matches_independent_finite_difference"
            ),
        },
        "optimizer_gate": {
            "method": "L-BFGS-B",
            "lbfgsb_controls": {
                "maxiter": profile.LBFGSB_MAXITER,
                "maxfun": profile.LBFGSB_MAXFUN,
                "ftol": profile.LBFGSB_FTOL,
                "gtol": profile.LBFGSB_GTOL,
            },
            "restart_policy": {
                "count": 1,
                "jitter_scale": profile.RESTART_JITTER_SCALE,
                "rng_base": profile.RESTART_RNG_BASE,
                "on": "abnormal termination",
            },
            "tau_stat": profile.TAU_STAT,
            "dg_agree": profile.AGREE_DG_REL,
            "du_agree": profile.AGREE_DU_INF,
            "two_start": True,
            "test": (
                "tests/test_m2c_profile_integration.py::"
                "test_optimizer_gate_converges_and_requires_both_starts"
            ),
        },
        "curvature_gate": {
            "h_sweep": list(profile.HESS_H_SWEEP),
            "center_h": profile.HESS_H_CENTER,
            "logdet_stability": profile.LOGDET_STABILITY_TOL,
            "symmetry": profile.SYMMETRY_TOL,
            "directional_tol": profile.DIRECTIONAL_TOL,
            "direction_rng": {
                "generator": "numpy.random.default_rng",
                "seeds": list(profile.DIRECTION_RNG_SEEDS),
                "epsilon": profile.DIRECTIONAL_EPS,
                "dtype": "float64",
                "normalization": "unit-L2",
                "coordinate_order": ["ls", "os", "lv"],
            },
            "spd_required": True,
            "rcond_min": profile.RCOND_MIN,
            "retry_policy": {
                "count": 1,
                "gtol": profile.RETRY_GTOL,
                "ftol": profile.RETRY_FTOL,
                "maxiter": profile.RETRY_MAXITER,
                "rerun_full_gate": True,
            },
            "stop_on_fail": True,
            "test": (
                "tests/test_m2c_profile_integration.py::"
                "test_curvature_gate_recovers_quadratic_oracle_without_flooring"
            ),
        },
    }

    mcse_strategy = {
        "estimator": "per-chain non-circular moving-block bootstrap",
        "iact_series": (
            "each model contribution exp(-G[c,t,j]/tau-M_global), with one "
            "M_global=max over all c,t,j; max IACT over chains and models"
        ),
        "block_len_rule": f"ceil({dm.MCSE_BLOCK_LEN_FACTOR}*tau_int)",
        "block_cap_behavior": (
            "UNDETERMINED when T-block_len+1<2; no IID-row fallback"
        ),
        "B": dm.MCSE_MBB_B,
        "seed": dm.MCSE_MBB_SEED,
        "test": (
            "tests/test_m2c_mcse_strategy.py::"
            "test_known_iact_and_frozen_seed_determinism"
        ),
    }

    tolerances = [
        _tolerance("profile_eps_domain", profile.EPS_DOMAIN,
                   "final one-sided cap-sensitivity gate", "PROPOSED-v1.17",
                   profile_test),
        _tolerance("profile_eps_grid", profile.EPS_GRID,
                   "successive nested-grid sensitivity gate", "PROPOSED-v1.17",
                   profile_test),
        _tolerance("profile_gradient_abs", profile.TOL_GRAD_ABS,
                   "frozen v1.4-style gradient envelope", "CONFIRMED",
                   "tests/test_m2c_profile_gradient.py::test_functional_gradient_matches_independent_finite_difference"),
        _tolerance("profile_gradient_rel", profile.TOL_GRAD_REL,
                   "frozen v1.4-style gradient envelope", "CONFIRMED",
                   "tests/test_m2c_profile_gradient.py::test_functional_gradient_matches_independent_finite_difference"),
        _tolerance("profile_stationarity", profile.TAU_STAT,
                   "mandatory per-start optimizer stationarity", "PROPOSED-v1.17",
                   "tests/test_m2c_profile_integration.py::test_optimizer_gate_converges_and_requires_both_starts"),
        _tolerance("profile_logdet_stability", profile.LOGDET_STABILITY_TOL,
                   "curvature h-sweep stability", "PROPOSED-v1.17",
                   "tests/test_m2c_profile_integration.py::test_curvature_gate_recovers_quadratic_oracle_without_flooring"),
        _tolerance("profile_symmetry", profile.SYMMETRY_TOL,
                   "pre-symmetrization curvature skew", "PROPOSED-v1.17",
                   "tests/test_m2c_profile_integration.py::test_curvature_gate_recovers_quadratic_oracle_without_flooring"),
        _tolerance("profile_directional", profile.DIRECTIONAL_TOL,
                   "directional curvature verification", "PROPOSED-v1.17",
                   "tests/test_m2c_profile_integration.py::test_curvature_gate_recovers_quadratic_oracle_without_flooring"),
        _tolerance("profile_rcond_min", profile.RCOND_MIN,
                   "relative numerical positive-definiteness floor", "PROPOSED-v1.17",
                   "tests/test_m2c_profile_integration.py::test_curvature_gate_stops_after_retry_for_near_singular_spd_oracle"),
        _tolerance("s2_fd_step", s2s3.S2_FD_STEP,
                   "scaled central finite-difference base step", "PROPOSED-v1.17", s2_test),
        _tolerance("s2_skew", s2s3.S2_SKEW_TOL,
                   "raw differenced-Hessian skew", "PROPOSED-v1.17", s2_test),
        _tolerance("s2_step_stability", s2s3.S2_STEP_STABILITY_TOL,
                   "author-selected J2 step stability", "PROPOSED-v1.17", s2_test),
        _tolerance("s2_directional", s2s3.S2_DIRECTIONAL_TOL,
                   "directional curvature agreement", "PROPOSED-v1.17", s2_test),
        _tolerance("s2_whitening", s2s3.S2_WHITENING_TOL,
                   "both whitening identities", "PROPOSED-v1.17", s2_test),
        _tolerance("s2_eigenvalue_floor", s2s3.S2_EIG_FLOOR,
                   "raw Hessian must already clear the SPD floor", "PROPOSED-v1.17", s2_test),
        _tolerance("s2_oracle", s2s3.S2_ORACLE_TOL,
                   "diag(1,4,9) mass-convention oracle", "PROPOSED-v1.17", s2_test),
        _tolerance("s3_slogdet", s2s3.S3_SLOGDET_TOL,
                   "analytic/autodiff log-determinant", "PROPOSED-v1.17", s3_test),
        _tolerance("s3_roundtrip", s2s3.S3_ROUNDTRIP_TOL,
                   "u/theta coordinate round trips", "PROPOSED-v1.17", s3_test),
        _tolerance("s3_density", s2s3.S3_DENSITY_TOL,
                   "S3/E1 density equivalence", "PROPOSED-v1.17", s3_test),
        _tolerance("s3_gradient_abs", s2s3.S3_GRAD_ABS,
                   "gradient chain-rule absolute envelope", "PROPOSED-v1.17", s3_test),
        _tolerance("s3_gradient_rel", s2s3.S3_GRAD_REL,
                   "gradient chain-rule relative envelope", "PROPOSED-v1.17", s3_test),
        _tolerance("s3_constrained_bridge", s2s3.S3_CONSTRAINED_BRIDGE_TOL,
                   "manual constrained map must match E1 transforms", "PROPOSED-v1.17", s3_test),
    ]

    predicates = [
        {
            "name": "s2_mass_convention",
            "formula": "M=H_reg; u=u_MAP+Q diag(lambda^-1/2) z",
            "threshold": {
                "skew": s2s3.S2_SKEW_TOL,
                "step_stability": s2s3.S2_STEP_STABILITY_TOL,
                "directional": s2s3.S2_DIRECTIONAL_TOL,
                "whitening": s2s3.S2_WHITENING_TOL,
                "lambda_min": s2s3.S2_EIG_FLOOR,
                "n_clipped": 0,
            },
            "fixture": "synthetic E1 structures plus seedless quadratic oracle",
            "failure": "STOP; no identity fallback",
            "field": "S2 fixed metric",
            "test": s2_test,
            "tag": "PROPOSED-v1.17",
        },
        {
            "name": "s3_jacobian_equivalence",
            "formula": "log|det du/dz|=0 and V3(z)=V_E1(u(z))",
            "threshold": {
                "slogdet": s2s3.S3_SLOGDET_TOL,
                "roundtrip": s2s3.S3_ROUNDTRIP_TOL,
                "density": s2s3.S3_DENSITY_TOL,
                "gradient_abs": s2s3.S3_GRAD_ABS,
                "gradient_rel": s2s3.S3_GRAD_REL,
                "n_states": s2s3.S3_N_STATES,
            },
            "fixture": "synthetic M0 Mauna-structure 33-state battery",
            "failure": "STOP for S3; non-seven-site inventories are outside definition",
            "field": "S3 reparameterization",
            "test": s3_test,
            "tag": "PROPOSED-v1.17",
        },
        {
            "name": "divergence_nonclustering",
            "formula": "rate plus chain and per-chain time-window concentration",
            "threshold": {
                "rate_cap": dm.DIVERGENCE_RATE_CAP,
                "concentration_factor": dm.DIVERGENCE_CONC_FACTOR,
                "min_event_floor": dm.DIVERGENCE_MIN_EVENT_FLOOR,
                "time_window_fraction": dm.DIVERGENCE_TIME_WINDOW_FRAC,
            },
            "fixture": "hand-built C=4,T=2000 SamplerDiagnostics",
            "failure": "FAIL; missing or invalid indices are UNDETERMINED",
            "field": "SamplerDiagnostics.divergence_draws; parameter-band clustering unevaluable",
            "test": "tests/test_m2c_divergence_clustering.py::test_frozen_enumerated_cases",
            "tag": "CONFIRMED+PROPOSED-v1.17",
        },
        {
            "name": "m1_covariance_overlap",
            "formula": "q_overlap=sum_i w_i 1{max_j alignment(PK_m1P,PK_jP)>=threshold}",
            "threshold": {
                "alignment": m1.OVERLAP_ALIGNMENT_THRESHOLD,
                "q_overlap_cap": m1.Q_OVERLAP_CAP,
            },
            "fixture": "seedless algebraic matrices and synthetic structure plumbing",
            "failure": "STOP for M1 promotion; uncomputable inputs are UNDETERMINED",
            "field": "M1 covariance duplication",
            "test": "tests/test_m2c_m1_overlap.py::test_overlap_wrapper_pins_frozen_thresholds_and_rejects_overrides",
            "tag": "PROPOSED-v1.17",
        },
        {
            "name": "m1_nugget_floor",
            "formula": "p_below=sum_i w_i 1{noise_i<reference}; flag iff p_below>0.05",
            "threshold": {
                "noise_reference": m1.NUGGET_REFERENCE,
                "flag_probability": m1.NUGGET_FLAG_THRESHOLD,
                "strict": True,
            },
            "fixture": "seedless weighted noise-variance draws",
            "failure": "REPORT-ONLY; missing inputs are UNDETERMINED",
            "field": "M1 nugget-floor coincidence report",
            "test": "tests/test_m2c_m1_nugget_floor.py::test_complete_report_returns_the_full_coincidence_record",
            "tag": "CONFIRMED+PROPOSED-v1.17",
        },
        {
            "name": "profile_core",
            "formula": "edge-exact normalized band partition after optimizer/curvature/P3 gates",
            "threshold": {
                "eps_domain": profile.EPS_DOMAIN,
                "eps_grid": profile.EPS_GRID,
                "stationarity": profile.TAU_STAT,
                "rcond_min": profile.RCOND_MIN,
            },
            "fixture": "analytic synthetic Gaussian/quadratic profile oracles",
            "failure": "STOP on any optimizer, curvature, tail, or refinement failure",
            "field": "corrected profile-Laplace integration",
            "test": profile_test,
            "tag": "PROPOSED-v1.17",
        },
    ]

    return {
        "freeze_version": "v1.17",
        "kind": "m2c-gtoy-profile-algorithm-freeze",
        "references": references,
        "algorithm": algorithm,
        "mcse_strategy": mcse_strategy,
        "tolerances": tolerances,
        "predicates": predicates,
        "historical_provenance": {
            "buggy_triplet": [0.76262, 0.13752, 0.02311],
            "sum": 0.9232,
            "note": (
                "Historical buggy profile triplet only; not a result, target, "
                "or corrected profile value."
            ),
        },
    }


def _package_version(distribution):
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def _blas_descriptor():
    try:
        config = getattr(np.__config__, "CONFIG", {})
        dependencies = config.get("Build Dependencies", {})
        blas = dependencies.get("blas", {})
        parts = [blas.get(key) for key in ("name", "version", "openblas configuration")]
        descriptor = "; ".join(str(part) for part in parts if part)
        if descriptor:
            return descriptor
        get_info = getattr(np.__config__, "get_info", None)
        if get_info is not None:
            info = get_info("blas_opt_info") or get_info("blas_info")
            libraries = info.get("libraries", ())
            if libraries:
                return ",".join(str(item) for item in libraries)
    except Exception:
        pass
    return "unknown"


def _provenance():
    versions = {
        "python": platform.python_version(),
        "numpy": _package_version("numpy"),
        "scipy": _package_version("scipy"),
        "torch": _package_version("torch"),
        "gpytorch": _package_version("gpytorch"),
        "pyro": _package_version("pyro-ppl"),
        "arviz": _package_version("arviz"),
    }
    return {
        "versions": versions,
        "scipy": versions["scipy"],
        "blas": _blas_descriptor(),
        "host": platform.node(),
        "cpu_count": int(os.cpu_count() or 1),
        "threads": int(torch.get_num_threads()),
        "frozen_at_git_sha_meaning": FROZEN_AT_GIT_SHA_MEANING,
    }


def build_v117_manifest() -> dict:
    """Return a complete v1.17 snapshot with descriptive provenance."""
    manifest = build_v117_algorithm_manifest()
    manifest["provenance"] = _provenance()
    manifest["frozen_at_git_sha"] = FROZEN_AT_GIT_SHA
    return manifest


def manifest_sha256(manifest_dict) -> str:
    """Hash canonical JSON (sorted keys and compact separators)."""
    encoded = json.dumps(
        manifest_dict, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


__all__ = [
    "FROZEN_AT_GIT_SHA",
    "build_v117_algorithm_manifest",
    "build_v117_manifest",
    "manifest_sha256",
]
