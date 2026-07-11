"""
Diagnostic-retaining sampler result schema (D20, M2a item 6).

fit_hmc used to discard the pyro MCMC object, losing divergences, tree-depth
saturation, and acceptance — the exact quantities the D19 G-B gate reads
(plan-d19-mauna.md §6.7) and the base the M2c divergence-clustering predicate
is defined against (§6.15). These tests pin the contract:

- the DEFAULT fit_hmc return is the untouched D9 dict (site name to (n,)
  constrained array);
- return_diagnostics=True returns (samples, SamplerDiagnostics), a frozen,
  plain-data, JSON-round-trippable record;
- diagnostics a path cannot observe are None AND named in `unavailable` —
  never fabricated zeros.

Runs use the TOY model on synthetic data only (tiny chains; no Mauna data,
no scientific result).
"""

import json

import numpy as np
import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("pyro")

from bistar_gp.fit import fit_hmc, fit_map
from bistar_gp.model import build_model, build_toy_kernels
from bistar_gp.sampler_diagnostics import (
    SCHEMA_VERSION,
    SamplerDiagnostics,
    diagnostics_from_pyro_mcmc,
    leapfrog_counts_from_records,
)

torch.set_default_dtype(torch.float64)

N_DRAWS, N_WARMUP, TREE_DEPTH = 6, 6, 3


@pytest.fixture(scope="module")
def hmc_run():
    """One tiny seeded NUTS run shared by the structured-path tests."""
    x = torch.linspace(0, 6, 15)
    y = torch.sin(x) + 0.25 * x
    kernels, names = build_toy_kernels()
    model, lik = build_model(x, y, kernels, names)
    fit_map(model, lik, x, y, n_iter=30, lr=0.05, verbose=False)
    samples, diag = fit_hmc(model, lik, x, y, n_samples=N_DRAWS,
                            n_warmup=N_WARMUP, verbose=False, seed=0,
                            max_tree_depth=TREE_DEPTH, return_diagnostics=True)
    return samples, diag


def test_diagnostics_path_does_not_perturb_the_trajectory():
    """The core promise of return_diagnostics: it OBSERVES the run without
    changing its target or RNG trajectory (D20 review round 3). Two identical
    toy models from the same MAP state and seed — one with diagnostics, one
    without — must produce bit-identical sample keys and draws. The tracker
    wraps the model callable transparently and the MCMC hook consumes no
    model RNG, so any divergence would be a real perturbation bug."""
    def fresh():
        x = torch.linspace(0, 6, 15)
        y = torch.sin(x) + 0.25 * x
        kernels, names = build_toy_kernels()
        model, lik = build_model(x, y, kernels, names)
        fit_map(model, lik, x, y, n_iter=40, lr=0.05, verbose=False)
        return model, lik, x, y

    mA, likA, xA, yA = fresh()
    plain = fit_hmc(mA, likA, xA, yA, n_samples=8, n_warmup=8, verbose=False,
                    seed=123, max_tree_depth=4, return_diagnostics=False)

    mB, likB, xB, yB = fresh()
    observed, diag = fit_hmc(mB, likB, xB, yB, n_samples=8, n_warmup=8,
                             verbose=False, seed=123, max_tree_depth=4,
                             return_diagnostics=True)

    assert list(plain.keys()) == list(observed.keys())
    for site in plain:
        assert np.array_equal(plain[site], observed[site]), (
            f"diagnostics path perturbed site {site}")
    # and the observation actually captured something (no silent all-unavailable)
    assert diag.leapfrog_counts is not None


def test_default_return_is_the_unchanged_d9_dict():
    x = torch.linspace(0, 6, 12)
    y = torch.sin(x)
    kernels, names = build_toy_kernels()
    model, lik = build_model(x, y, kernels, names)
    fit_map(model, lik, x, y, n_iter=20, lr=0.05, verbose=False)
    out = fit_hmc(model, lik, x, y, n_samples=3, n_warmup=3,
                  verbose=False, seed=0, max_tree_depth=2)
    assert isinstance(out, dict) and not isinstance(out, tuple)
    for name, arr in out.items():
        assert isinstance(arr, np.ndarray) and arr.shape == (3,), name


def test_structured_return_shapes_and_site_ordering(hmc_run):
    samples, diag = hmc_run
    assert isinstance(diag, SamplerDiagnostics)
    assert diag.sampler == "nuts_pyro"
    assert diag.site_names == tuple(samples.keys())  # order preserved
    assert diag.n_chains == 1
    assert diag.n_draws == N_DRAWS and diag.n_warmup == N_WARMUP
    assert diag.max_tree_depth == TREE_DEPTH
    for name, arr in samples.items():
        assert arr.shape == (N_DRAWS,), name  # legacy schema intact


def test_observed_diagnostics_are_plausible(hmc_run):
    _, diag = hmc_run
    assert diag.unavailable == ()
    # leapfrog counts: one chain, one entry per post-warmup draw, each at
    # least 1 AND bounded by the depth cap (a NUTS tree at cap d takes at
    # most 2**d - 1 leapfrogs; the probe verified the counter delta equals
    # the leapfrog count exactly). The upper bound BINDS the observation to
    # the cap: fabricated or overhead-inflated counts would exceed it and
    # fake saturation (workflow finding C9).
    (counts,) = diag.leapfrog_counts
    assert len(counts) == N_DRAWS
    assert all(1 <= c <= 2 ** TREE_DEPTH - 1 for c in counts)
    assert 0.0 <= diag.depth_saturation_rate <= 1.0
    (depths,) = diag.tree_depths
    assert all(0 <= d <= TREE_DEPTH for d in depths)
    (acc,) = diag.acceptance_rate
    assert 0.0 <= acc <= 1.0
    (div_idx,) = diag.divergence_draws
    assert all(0 <= t < N_DRAWS for t in div_idx)
    assert diag.divergence_rate == len(div_idx) / N_DRAWS
    assert diag.step_size is None or diag.step_size > 0


def test_json_round_trip_is_lossless(hmc_run):
    _, diag = hmc_run
    payload = json.loads(json.dumps(diag.to_dict()))
    restored = SamplerDiagnostics.from_dict(payload)
    assert restored == diag  # frozen dataclass equality, field by field
    assert restored.schema_version == SCHEMA_VERSION


def test_from_dict_rejects_unknown_keys_and_foreign_versions(hmc_run):
    _, diag = hmc_run
    payload = diag.to_dict()
    with_extra = dict(payload, surprise_field=1)
    with pytest.raises(ValueError, match="unknown"):
        SamplerDiagnostics.from_dict(with_extra)
    with pytest.raises(ValueError, match="schema_version"):
        SamplerDiagnostics.from_dict(dict(payload, schema_version=99))


def test_multi_chain_payload_shapes_and_rates():
    """The schema is chain-major; a synthetic 4-chain payload (pyro
    multi-chain runs come later) must round-trip with correct derived rates."""
    diag = SamplerDiagnostics(
        sampler="nuts_pyro", n_chains=4, n_draws=10, n_warmup=5,
        site_names=("a", "b"), max_tree_depth=7,
        divergence_draws=((0, 3), (), (9,), ()),
        acceptance_rate=(0.9, 0.8, 0.95, 0.85),
        leapfrog_counts=tuple(tuple([127] * 10) for _ in range(4)),
    )
    assert diag.n_divergences == (2, 0, 1, 0)
    assert diag.divergence_rate == 3 / 40
    assert diag.depth_saturation_rate == 1.0  # 127 = 2**7 - 1 every draw
    assert SamplerDiagnostics.from_dict(
        json.loads(json.dumps(diag.to_dict()))) == diag


def test_unavailable_diagnostics_reported_not_fabricated():
    """A source exposing no divergence/acceptance info (e.g. a kernel whose
    diagnostics() lacks those keys) must yield None + `unavailable`, and the
    derived rates must be None rather than zero."""

    class BareMCMC:
        num_chains = 1

        def diagnostics(self):
            return {}  # nothing observable

    diag = diagnostics_from_pyro_mcmc(
        BareMCMC(), sampler="bare", n_draws=5, n_warmup=2,
        site_names=("a",))
    assert diag.divergence_draws is None and diag.acceptance_rate is None
    assert diag.leapfrog_counts is None
    assert set(diag.unavailable) == {
        "divergence_draws", "acceptance_rate", "leapfrog_counts"}
    assert diag.divergence_rate is None
    assert diag.depth_saturation_rate is None
    assert diag.n_divergences is None and diag.tree_depths is None
    # and the honesty invariant is enforced at construction:
    with pytest.raises(ValueError, match="honesty"):
        SamplerDiagnostics(sampler="x", n_chains=1, n_draws=1, n_warmup=0,
                           site_names=("a",), divergence_draws=None,
                           acceptance_rate=(1.0,), leapfrog_counts=((3,),))


def test_leapfrog_counts_derivation_from_hook_records():
    """Sampling-stage deltas against the last warmup snapshot (the probe
    verified each NUTS leapfrog is one traced model call)."""
    records = [("Warmup", 0, 26), ("Warmup", 1, 29),
               ("Sample", 0, 44), ("Sample", 1, 59), ("Sample", 2, 62)]
    assert leapfrog_counts_from_records(records) == (15, 15, 3)
    assert leapfrog_counts_from_records([("Warmup", 0, 9)]) is None
    # No-warmup runs have no clean baseline: the first delta would absorb
    # initialization overhead and could fake depth saturation, so counts are
    # UNAVAILABLE rather than contaminated (review finding 2).
    assert leapfrog_counts_from_records([("Sample", 0, 12)]) is None


def test_partial_chain_diagnostics_are_unavailable_not_fabricated():
    """A diagnostics payload missing a chain key must not coerce into
    'chain had zero divergences' or a NaN acceptance (review finding 3)."""

    class PartialMCMC:
        num_chains = 2

        def diagnostics(self):
            return {"divergences": {"chain 0": [1]},        # chain 1 missing
                    "acceptance rate": {"chain 0": 0.9}}    # chain 1 missing

    diag = diagnostics_from_pyro_mcmc(
        PartialMCMC(), sampler="partial", n_draws=5, n_warmup=2,
        site_names=("a",))
    assert diag.divergence_draws is None
    assert diag.acceptance_rate is None
    assert "divergence_draws" in diag.unavailable
    assert "acceptance_rate" in diag.unavailable


def test_acceptance_rate_validated_and_json_rejects_nonfinite():
    with pytest.raises(ValueError, match="acceptance_rate"):
        SamplerDiagnostics(sampler="x", n_chains=1, n_draws=2, n_warmup=1,
                           site_names=("a",),
                           divergence_draws=((),),
                           acceptance_rate=(float("nan"),),
                           leapfrog_counts=((1, 1),))
    with pytest.raises(ValueError, match="acceptance_rate"):
        SamplerDiagnostics(sampler="x", n_chains=1, n_draws=2, n_warmup=1,
                           site_names=("a",),
                           divergence_draws=((),),
                           acceptance_rate=(1.5,),
                           leapfrog_counts=((1, 1),))


def test_shape_validation_is_loud():
    with pytest.raises(ValueError, match="chains"):
        SamplerDiagnostics(sampler="x", n_chains=2, n_draws=3, n_warmup=0,
                           site_names=("a",),
                           divergence_draws=((0,),),  # 1 chain given, 2 declared
                           acceptance_rate=(0.5, 0.5),
                           leapfrog_counts=((1, 1, 1), (1, 1, 1)))
    with pytest.raises(ValueError, match="out of range"):
        SamplerDiagnostics(sampler="x", n_chains=1, n_draws=3, n_warmup=0,
                           site_names=("a",),
                           divergence_draws=((7,),),
                           acceptance_rate=(0.5,),
                           leapfrog_counts=((1, 1, 1),))
