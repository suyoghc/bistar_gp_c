"""Seedless hand-built rev-5 divergence-clustering fixtures."""

import pytest

from bistar_gp.divergence_clustering import divergence_nonclustering
from bistar_gp.sampler_diagnostics import SamplerDiagnostics


_OTHER_UNAVAILABLE = (
    "acceptance_rate",
    "leapfrog_counts",
    "notpsd_rejections",
    "notpsd_rejections_warmup",
    "notpsd_rejections_per_draw",
)


def _diagnostics(*chains, missing=False, n_draws=2000):
    if missing:
        divergence_draws = None
        unavailable = ("divergence_draws",) + _OTHER_UNAVAILABLE
    else:
        divergence_draws = tuple(tuple(chain) for chain in chains)
        unavailable = _OTHER_UNAVAILABLE
    return SamplerDiagnostics(
        sampler="hand",
        n_chains=4,
        n_draws=n_draws,
        n_warmup=1000,
        site_names=("z",),
        divergence_draws=divergence_draws,
        acceptance_rate=None,
        leapfrog_counts=None,
        notpsd_rejections=None,
        notpsd_rejections_warmup=None,
        notpsd_rejections_per_draw=None,
        unavailable=unavailable,
    )


PASS_CHAINS = (
    (100, 1100),
    (500, 1500),
    (300, 1300),
    (700, 1700),
)


@pytest.mark.parametrize(
    ("chains", "verdict", "failed_gates"),
    [
        (PASS_CHAINS, "PASS", []),
        (((100, 1100, 1900),) + PASS_CHAINS[1:], "FAIL", ["rate"]),
        (((100, 300, 500, 700, 900, 1100, 1300, 1500), (), (), ()),
         "FAIL", ["chain"]),
        (((100, 150, 199), (500,), (1000, 1500), (1800, 1900)),
         "FAIL", ["time"]),
        (((), (), (), ()), "PASS", []),
        (((100,), (), (), ()), "PASS", []),
        (((100,), (500,), (), ()), "PASS", []),
    ],
)
def test_frozen_enumerated_cases(chains, verdict, failed_gates):
    report = divergence_nonclustering(_diagnostics(*chains))
    assert report["verdict"] == verdict
    assert report["failed_gates"] == failed_gates
    assert report["parameter_band_clustering"] == "unevaluable-schema-limited"


def test_pass_fixture_hits_every_inclusive_boundary_exactly():
    report = divergence_nonclustering(_diagnostics(*PASS_CHAINS))
    assert report["rate"] == report["rate_cap"] == 0.001
    assert report["n_divergences"] == (2, 2, 2, 2)
    assert report["d_max"] == 2
    assert report["L_chain"] == 6
    assert report["time_max"] == 1
    assert report["L_time"] == 2
    assert report["w"] == 200


def test_duplicate_and_missing_indices_are_undetermined():
    duplicate = divergence_nonclustering(
        _diagnostics((100, 100), (), (), ())
    )
    missing = divergence_nonclustering(_diagnostics(missing=True))
    for report in (duplicate, missing):
        assert report["verdict"] == "UNDETERMINED"
        assert report["rate"] is None
        assert report["n_divergences"] is None
        assert report["failed_gates"] == []
        assert "error" in report
        assert report["parameter_band_clustering"] == "unevaluable-schema-limited"


def test_unsorted_and_noninteger_indices_fail_closed():
    unsorted = divergence_nonclustering(_diagnostics((200, 100), (), (), ()))
    noninteger = divergence_nonclustering(_diagnostics((100.0,), (), (), ()))
    assert unsorted["verdict"] == "UNDETERMINED"
    assert noninteger["verdict"] == "UNDETERMINED"


def test_parameter_band_limitation_is_present_in_every_report():
    reports = [
        divergence_nonclustering(_diagnostics(*PASS_CHAINS)),
        divergence_nonclustering(_diagnostics((100, 100), (), (), ())),
        divergence_nonclustering(_diagnostics(missing=True)),
    ]
    assert {
        report["parameter_band_clustering"] for report in reports
    } == {"unevaluable-schema-limited"}
