"""
A4 universe firewall enforced at the shared BMS* boundary (D20 review round 3).

run_bms_star normalizes candidate probabilities over ONE universe; decision A4
(docs/plan-d19-mauna.md section 3) forbids merging the Mauna 4-ladder and the
harmonized 3-set into one normalization. Guarding only in the Mauna script is
caller-dependent, so run_bms_star itself rejects cross-universe and
partially-tagged candidate lists before computing any G matrix. Legacy/toy
callers whose candidates carry no universe tag are unaffected.

Synthetic inputs only — no Mauna data, no real BMS* result.
"""

import numpy as np
import pytest

from bistar_gp.bms_star import GPPosteriorSample, run_bms_star
from bistar_gp.candidates import CandidateResult


def _gp_samples(n_eval=4, k=3, seed=0):
    rng = np.random.default_rng(seed)
    return [
        GPPosteriorSample(
            mean=rng.normal(size=n_eval),
            cov=np.diag(np.full(n_eval, 0.1)),
            hyperparameters={"draw": float(i)},
        )
        for i in range(k)
    ]


def _result(name, universe, n_eval=4):
    return CandidateResult(
        name=name,
        mean=np.zeros(n_eval),
        cov=np.eye(n_eval) * 0.1,
        noise_var=0.1,
        parameters={},
        universe=universe,
    )


TAUS = np.array([1.0])
METRICS = ["pw_mse"]


def test_untagged_candidates_are_allowed():
    """Legacy/toy callers carry no universe tag and must still work."""
    results = run_bms_star(
        _gp_samples(),
        [_result("Linear", None), _result("Quadratic", None)],
        METRICS, TAUS)
    probs = results["pw_mse"][1.0].instance_posteriors
    assert probs.sum() == pytest.approx(1.0)


def test_single_tagged_universe_is_allowed():
    results = run_bms_star(
        _gp_samples(),
        [_result("Linear+2Harm", "appendix_trend3"),
         _result("Quad+2Harm", "appendix_trend3")],
        METRICS, TAUS)
    assert results["pw_mse"][1.0].instance_posteriors.sum() == pytest.approx(1.0)


def test_mixed_universes_are_rejected_before_computing_g():
    with pytest.raises(ValueError, match="multiple universes|A4"):
        run_bms_star(
            _gp_samples(),
            [_result("Quad+2Harm", "main_ladder"),
             _result("Quad+2Harm", "appendix_trend3")],
            METRICS, TAUS)


def test_partially_tagged_input_is_rejected():
    """A tagged result mixed with an untagged one is the silent-merge risk
    the firewall exists to stop."""
    with pytest.raises(ValueError, match="mix of tagged and untagged|A4"):
        run_bms_star(
            _gp_samples(),
            [_result("Quad+2Harm", "appendix_trend3"),
             _result("Linear", None)],
            METRICS, TAUS)
