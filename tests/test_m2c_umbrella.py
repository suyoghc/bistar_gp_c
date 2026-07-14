"""Hermetic M2c wiring/consistency umbrella, never a scientific verdict.

No real chain, sampler, Mauna/holdout data, or scientific computation runs.
The divergence and MCSE inputs are hand-built/synthetic deterministic
fixtures; model-bearing checks use synthetic toy/monthly structure only.
"""

import json
import math

import numpy as np
import pytest
from jsonschema import Draft202012Validator

torch = pytest.importorskip("torch")
pytest.importorskip("gpytorch")
pytest.importorskip("pyro")

from tests.test_e1_potential import _built
from tests.test_m2c_manifest import ROOT, V117_SCHEMA

from bistar_gp.divergence_clustering import divergence_nonclustering
from bistar_gp.e1_potential import build_e1_potential
from bistar_gp.m1_builder import build_mauna_loa_m1_kernels
from bistar_gp.m1_nugget_floor import nugget_floor_report
from bistar_gp.m1_overlap import overlap_diagnostic
from bistar_gp.mcse_strategy import mcse_strategy_estimate
from bistar_gp.m2c_freeze_m1 import (
    M1_LENGTHSCALE_MEDIAN,
    M1_OUTPUTSCALE_MEDIAN,
    NUGGET_REFERENCE,
)
from bistar_gp.m2c_manifest import (
    build_v117_algorithm_manifest,
    build_v117_manifest,
)
from bistar_gp.model import build_model
from bistar_gp.profile_integration import band_masses, full_domain_grid
from bistar_gp.profile_potential import ProfilePotential
from bistar_gp.sampler_diagnostics import SamplerDiagnostics
from bistar_gp.s2_fixed_metric import (
    central_fd_hessian,
    flatten_e1_state,
    unflatten_e1_state,
)
from bistar_gp.s3_reparam import (
    frozen_s3_states,
    resolve_m0_site_roles,
    s3_potential,
    z_to_e1_u,
)


torch.set_default_dtype(torch.float64)


@pytest.fixture(scope="module")
def synthetic_m0():
    model, likelihood, x, y = _built("mauna_structure")
    e1 = build_e1_potential(model, likelihood, x, y)
    return model, likelihood, x, y, e1


def _hand_diagnostics(draws):
    return SamplerDiagnostics(
        sampler="hand",
        n_chains=4,
        n_draws=2000,
        n_warmup=1000,
        site_names=("z",),
        divergence_draws=draws,
        acceptance_rate=None,
        leapfrog_counts=None,
        notpsd_rejections=None,
        notpsd_rejections_warmup=None,
        notpsd_rejections_per_draw=None,
        unavailable=(
            "acceptance_rate", "leapfrog_counts", "notpsd_rejections",
            "notpsd_rejections_warmup", "notpsd_rejections_per_draw",
        ) if draws is not None else (
            "divergence_draws", "acceptance_rate", "leapfrog_counts",
            "notpsd_rejections", "notpsd_rejections_warmup",
            "notpsd_rejections_per_draw",
        ),
    )


def _synthetic_g(n_draws=96):
    t = np.arange(n_draws, dtype=np.float64)
    phase = 2.0 * np.pi * t / n_draws
    return np.asarray([
        np.column_stack((
            np.sin(phase + offset) + 0.001 * t,
            -0.6 * np.sin(phase + offset) + 0.1 * np.cos(3 * phase),
            0.4 * np.cos(phase - offset) + 0.002 * t,
        ))
        for offset in (0.0, 0.41)
    ], dtype=np.float64)


def test_profile_core_wiring_is_finite_on_synthetic_structure(synthetic_m0):
    model, likelihood, x, y, e1 = synthetic_m0
    profile = ProfilePotential(
        model, likelihood, x, y, sites=e1.sites
    )
    theta = e1.constrain(e1.init_params)
    value = profile.g_value(
        {site: e1.init_params[site] for site in profile.nuisance_sites},
        theta[profile.noise_site],
    )
    assert torch.isfinite(value)

    grid = full_domain_grid()
    logm = -0.5 * ((grid - 0.25) / 0.08) ** 2
    masses = band_masses(logm, grid, (0.15, 0.30))
    assert all(math.isfinite(masses[key]) for key in (
        "P_noise_lo", "P_noise_mid", "P_noise_hi"
    ))
    assert sum(masses[key] for key in (
        "P_noise_lo", "P_noise_mid", "P_noise_hi"
    )) == pytest.approx(1.0)


def test_s2_s3_wiring_uses_first_order_hermetic_paths(synthetic_m0):
    e1 = synthetic_m0[-1]
    center = flatten_e1_state(e1.init_params, e1.sites)

    def potential(vector):
        return e1.potential_fn(
            unflatten_e1_state(vector, e1.init_params, e1.sites)
        )

    columns, hessian = central_fd_hessian(potential, center)
    assert columns.shape == hessian.shape == (7, 7)
    assert torch.isfinite(hessian).all()

    roles = resolve_m0_site_roles(e1)
    states = frozen_s3_states(e1, roles)
    assert len(states) == 33
    for _label, z in states[:2]:
        transformed = s3_potential(e1, z, roles)
        direct = e1.potential_fn(z_to_e1_u(z, e1, roles))
        assert torch.isfinite(transformed)
        torch.testing.assert_close(transformed, direct, rtol=0.0, atol=1e-12)


def test_m1_builder_overlap_and_nugget_wiring_is_complete():
    x = torch.arange(36, dtype=torch.float64) / 12.0
    y = 0.05 * x + 0.3 * torch.sin(2.0 * torch.pi * x)
    kernels, names = build_mauna_loa_m1_kernels()
    model, likelihood = build_model(x, y, kernels, names)
    e1 = build_e1_potential(model, likelihood, x, y)
    assert len(e1.sites) == 9

    fixed = ((4.0, 0.002), (0.8, 0.001), (1.2, 0.0015))
    for kernel, (lengthscale, outputscale) in zip(
        model.kernel_components[:-1], fixed
    ):
        kernel.base_kernel.lengthscale = lengthscale
        kernel.outputscale = outputscale
    short = model.kernel_components[-1]
    short.base_kernel.lengthscale = M1_LENGTHSCALE_MEDIAN
    short.outputscale = M1_OUTPUTSCALE_MEDIAN
    likelihood.noise = NUGGET_REFERENCE
    matrices = {
        name: values["XX"]
        for name, values in model.get_component_kernel_matrices(x, x).items()
    }
    overlap = overlap_diagnostic(
        [matrices], [likelihood.noise.item()],
        {"G-IS": True}, {"G-IS": [1.0]},
    )
    assert overlap["verdict"] in {"PASS", "STOP"}
    assert np.isfinite(overlap["q_overlap"])

    nugget = nugget_floor_report(
        [0.5 * NUGGET_REFERENCE, 2.0 * NUGGET_REFERENCE],
        {"G-IS": True}, {"G-IS": [0.1, 0.9]},
        m0_noise_variances=[2.0 * NUGGET_REFERENCE] * 2,
        m0_authority_candidates={"RW-MH": True},
        m0_authority_weights_by_label={"RW-MH": [0.5, 0.5]},
        predictive_gate_passes=True,
    )
    assert nugget["flag"] is True
    assert nugget["p_below_M0"] == 0.0
    assert nugget["coincidence"] is True


def test_pr_d_predicates_are_determined_or_fail_closed_as_wired():
    passed = divergence_nonclustering(_hand_diagnostics((
        (100, 1100), (500, 1500), (300, 1300), (700, 1700)
    )))
    missing = divergence_nonclustering(_hand_diagnostics(None))
    assert passed["verdict"] == "PASS"
    assert missing["verdict"] == "UNDETERMINED"

    determined = mcse_strategy_estimate(
        _synthetic_g(), 1.0, ("a", "b", "c"), 1
    )
    constant = mcse_strategy_estimate(
        np.zeros((2, 32, 2), dtype=np.float64), 1.0, ("a", "b"), 0
    )
    assert determined["verdict"] == "DETERMINED"
    assert np.isfinite(determined["mcse"])
    assert constant["verdict"] == "UNDETERMINED"
    assert constant["mcse"] is None


def test_manifest_and_result_schema_are_consistent_end_to_end():
    committed = json.loads(
        (ROOT / "docs/m2c_freeze/gtoy_profile_freeze_v1.17.json").read_text()
    )
    Draft202012Validator(V117_SCHEMA).validate(committed)
    rebuilt = build_v117_algorithm_manifest()
    for key in (
        "algorithm", "mcse_strategy", "tolerances", "predicates", "references"
    ):
        assert committed[key] == rebuilt[key]
    Draft202012Validator(V117_SCHEMA).validate(build_v117_manifest())

    result_schema = json.loads(
        (ROOT / "docs/m2c_freeze/gtoy_profile_result_v1.18.schema.json").read_text()
    )
    Draft202012Validator.check_schema(result_schema)
