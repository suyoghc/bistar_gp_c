"""Differential obligation between the frozen and v2 profile gates."""

import struct

import numpy as np
import pytest
from scipy.optimize import OptimizeResult, minimize as scipy_minimize

import bistar_gp.m2cr.gates_v2 as v2
import bistar_gp.profile_integration as frozen


def _quadratic_oracle(A, center=None):
    A = np.asarray(A, dtype=np.float64)
    if center is None:
        center = np.zeros(A.shape[0], dtype=np.float64)
    center = np.asarray(center, dtype=np.float64)

    def g(u):
        delta = np.asarray(u, dtype=np.float64) - center
        return -0.5 * float(delta @ A @ delta)

    def grad(u):
        return -A @ (np.asarray(u, dtype=np.float64) - center)

    return g, grad


def _assert_frozen_value_identical(expected, actual, path="return"):
    if isinstance(expected, dict):
        for key, value in expected.items():
            assert key in actual, f"missing frozen key {path}.{key}"
            _assert_frozen_value_identical(value, actual[key], f"{path}.{key}")
    elif isinstance(expected, np.ndarray):
        assert expected.shape == actual.shape, path
        np.testing.assert_array_equal(
            expected.view(np.uint64), np.asarray(actual).view(np.uint64), err_msg=path
        )
    elif isinstance(expected, (float, np.floating)):
        assert struct.pack(">d", float(expected)) == struct.pack(">d", float(actual)), path
    else:
        assert expected == actual, path


def _optimizer_pair(monkeypatch, g, grad, warm, mode, fake=None):
    if fake is not None:
        monkeypatch.setattr(frozen, "minimize", fake)
        monkeypatch.setattr(v2, "minimize", fake)
    expected = frozen.optimize_conditional(
        lambda u: -g(u), lambda u: -grad(u), warm, mode
    )
    if fake is not None and hasattr(fake, "reset"):
        fake.reset()
    actual = v2.optimize_conditional_v2(
        lambda u: -g(u), lambda u: -grad(u), warm, mode
    )
    _assert_frozen_value_identical(expected, actual)
    assert "attempts_by_start" in actual
    return actual


def _curvature_pair(monkeypatch, g, grad, optimum, fake=None):
    if fake is not None:
        monkeypatch.setattr(frozen, "minimize", fake)
        monkeypatch.setattr(v2, "minimize", fake)
    expected = frozen.curvature_gate(g, grad, optimum, ("a", "b", "c"))
    if fake is not None and hasattr(fake, "reset"):
        fake.reset()
    actual = v2.curvature_gate_v2(g, grad, optimum, ("a", "b", "c"))
    _assert_frozen_value_identical(expected, actual)
    assert "evaluations" in actual
    assert "raw_hessian" in actual["evaluations"]["pre_retry"]
    return actual


class _SequencedMinimize:
    def __init__(self, behavior):
        self.behavior = behavior
        self.calls = 0

    def __call__(self, fun, x0, **kwargs):
        self.calls += 1
        return self.behavior(self.calls, fun, np.asarray(x0, dtype=np.float64), kwargs)

    def reset(self):
        self.calls = 0


class _StatefulSequenceOracle:
    def __init__(self):
        self.call_count = 0
        self.calls = []

    def g(self, u):
        self.call_count += 1
        value = float(self.call_count)
        self.calls.append(("g", tuple(np.asarray(u, dtype=np.float64)), value))
        return value

    def grad(self, u):
        self.call_count += 1
        value = np.full(3, self.call_count * 1.0e-6, dtype=np.float64)
        self.calls.append(
            (
                "grad",
                tuple(np.asarray(u, dtype=np.float64)),
                tuple(value),
            )
        )
        return value

    def reset(self):
        self.call_count = 0
        self.calls = []


def test_clean_two_start_accept_matches_existing_oracle(monkeypatch):
    g, grad = _quadratic_oracle(np.diag([1.0, 4.0, 9.0]), [0.4, -0.7, 1.1])
    result = _optimizer_pair(monkeypatch, g, grad, np.array([3.0, -2.0, 0.0]), np.array([-4.0, 2.0, 5.0]))
    assert result["stop"] is False
    assert all(len(value) == 1 for value in result["attempts_by_start"].values())


def test_abnormal_then_real_restart_matches_and_retains_discard(monkeypatch):
    g, grad = _quadratic_oracle(np.diag([1.0, 4.0, 9.0]), [0.2, -0.1, 0.3])

    def behavior(call, fun, x0, kwargs):
        if call == 1:
            return OptimizeResult(x=x0, status=2, success=False, message="abnormal")
        return scipy_minimize(fun, x0, **kwargs)

    result = _optimizer_pair(
        monkeypatch, g, grad, np.ones(3), -np.ones(3), _SequencedMinimize(behavior)
    )
    assert result["restart_count"] == 1
    assert result["attempts_by_start"]["warm"][0]["status"] == 2
    assert result["attempts_by_start"]["warm"][0]["g"] < 0.0


def test_discarded_original_telemetry_follows_complete_frozen_call_prefix(
    monkeypatch,
):
    oracle = _StatefulSequenceOracle()

    def behavior(call, fun, x0, kwargs):
        fun(x0)
        kwargs["jac"](x0)
        if call == 1:
            return OptimizeResult(
                x=np.full(3, 9.0),
                status=2,
                success=False,
                message="discarded original",
            )
        return OptimizeResult(
            x=np.zeros(3), status=0, success=True, message=f"final {call}"
        )

    fake = _SequencedMinimize(behavior)
    monkeypatch.setattr(frozen, "minimize", fake)
    monkeypatch.setattr(v2, "minimize", fake)
    warm = np.ones(3)
    mode = -np.ones(3)
    expected = frozen.optimize_conditional(
        lambda u: -oracle.g(u), lambda u: -oracle.grad(u), warm, mode
    )
    frozen_calls = list(oracle.calls)

    fake.reset()
    oracle.reset()
    actual = v2.optimize_conditional_v2(
        lambda u: -oracle.g(u), lambda u: -oracle.grad(u), warm, mode
    )

    _assert_frozen_value_identical(expected, actual)
    assert oracle.calls[: len(frozen_calls)] == frozen_calls
    assert [call[0] for call in oracle.calls[len(frozen_calls) :]] == ["g", "grad"]
    assert len(oracle.calls) == len(frozen_calls) + 2
    assert actual["attempts_by_start"]["warm"][0]["status"] == 2


def test_restart_that_also_fails_matches(monkeypatch):
    g, grad = _quadratic_oracle(np.eye(3))

    def behavior(call, fun, x0, kwargs):
        return OptimizeResult(x=x0, status=2, success=False, message=f"failed {call}")

    result = _optimizer_pair(
        monkeypatch, g, grad, np.ones(3), -np.ones(3), _SequencedMinimize(behavior)
    )
    assert result["restart_count"] == 2
    assert all(len(value) == 2 for value in result["attempts_by_start"].values())
    assert result["stop"] is True


def test_status_zero_nonstationary_matches(monkeypatch):
    fake = _SequencedMinimize(
        lambda call, fun, x0, kwargs: OptimizeResult(
            x=np.zeros(3), status=0, success=True, message="synthetic success"
        )
    )
    result = _optimizer_pair(
        monkeypatch,
        lambda u: 0.0,
        lambda u: -np.ones(3),
        np.zeros(3),
        np.zeros(3),
        fake,
    )
    assert result["both_success"] is False
    assert result["agree"] is True
    assert result["reason"] == "warm result is non-stationary; mode result is non-stationary"


def test_optimizer_status_zero_success_false_matches(monkeypatch):
    fake = _SequencedMinimize(
        lambda call, fun, x0, kwargs: OptimizeResult(
            x=np.zeros(3),
            status=0,
            success=False,
            message="status zero but reported false",
        )
    )
    result = _optimizer_pair(
        monkeypatch,
        lambda u: 0.0,
        lambda u: np.zeros(3),
        np.ones(3),
        -np.ones(3),
        fake,
    )
    assert result["restart_count"] == 0
    assert result["both_success"] is False
    assert result["reason"] == "warm optimizer failed; mode optimizer failed"


def test_nonfinite_result_vectors_match(monkeypatch):
    fake = _SequencedMinimize(
        lambda call, fun, x0, kwargs: OptimizeResult(
            x=np.array([np.nan, 0.0, 0.0]),
            status=0,
            success=True,
            message="nan vector",
        )
    )
    result = _optimizer_pair(
        monkeypatch,
        lambda u: np.nan,
        lambda u: np.zeros(3),
        np.ones(3),
        -np.ones(3),
        fake,
    )
    assert result["u_star"] is None
    assert np.isnan(result["g_star"])
    assert result["agree"] is False


def test_start_objectives_disagree_without_optima_disagreement(monkeypatch):
    fake = _SequencedMinimize(
        lambda call, fun, x0, kwargs: OptimizeResult(
            x=x0, status=0, success=True, message="identity"
        )
    )
    result = _optimizer_pair(
        monkeypatch,
        lambda u: 1.0e6 * float(np.asarray(u)[0]),
        lambda u: np.zeros(3),
        np.zeros(3),
        np.array([5.0e-5, 0.0, 0.0]),
        fake,
    )
    assert result["agree_g"] is False
    assert result["agree_u"] is True
    assert result["reason"] == "start objective values disagree"


def test_start_optima_disagree_without_objective_disagreement(monkeypatch):
    fake = _SequencedMinimize(
        lambda call, fun, x0, kwargs: OptimizeResult(
            x=x0, status=0, success=True, message="identity"
        )
    )
    result = _optimizer_pair(
        monkeypatch,
        lambda u: 0.0,
        lambda u: np.zeros(3),
        np.zeros(3),
        np.ones(3),
        fake,
    )
    assert result["agree_g"] is True
    assert result["agree_u"] is False
    assert result["reason"] == "start optima disagree"


def test_clean_curvature_matches_existing_oracle(monkeypatch):
    g, grad = _quadratic_oracle(np.diag([1.0, 4.0, 9.0]))
    result = _curvature_pair(monkeypatch, g, grad, np.zeros(3))
    assert result["retry_count"] == 0
    assert result["retry_evidence"] == {"fired": False}


@pytest.mark.parametrize("diagonal", [[1.0, 4.0, -2.0], [1.0e-9, 4.0, 9.0]])
def test_indefinite_and_near_singular_retry_then_stop_match(monkeypatch, diagonal):
    g, grad = _quadratic_oracle(np.diag(diagonal))
    result = _curvature_pair(monkeypatch, g, grad, np.zeros(3))
    assert result["retry_count"] == 1
    assert result["stop"] is True
    assert "post_retry" in result["evaluations"]


@pytest.mark.parametrize(
    ("candidate", "success", "expected_false"),
    [
        (np.zeros(3), False, "reported_success"),
        (np.zeros(2), True, "output_shape_and_finite"),
        (np.array([np.nan, 0.0, 0.0]), True, "output_shape_and_finite"),
        (np.ones(3), True, "stationarity_within_bound"),
    ],
)
def test_rigged_retry_failures_match_frozen(
    monkeypatch, candidate, success, expected_false
):
    g, grad = _quadratic_oracle(np.diag([1.0, 4.0, -2.0]))
    fake = _SequencedMinimize(
        lambda call, fun, x0, kwargs: OptimizeResult(
            x=candidate.copy(),
            status=0,
            success=success,
            message="rigged retry",
        )
    )
    result = _curvature_pair(monkeypatch, g, grad, np.zeros(3), fake)
    evidence = result["retry_evidence"]
    assert evidence["conjuncts"][expected_false] is False
    assert evidence["positively_accepted"] is False
    if candidate.shape != (3,) or not np.all(np.isfinite(candidate)):
        assert evidence["fallback_fired"] is True
        np.testing.assert_array_equal(
            result["evaluations"]["post_retry"]["u_star"], np.zeros(3)
        )
