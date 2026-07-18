"""Direct hermetic tests for the versioned profile gates."""

import io
import json

import numpy as np
import pytest
from scipy.optimize import OptimizeResult

import bistar_gp.m2cr.gates_v2 as gates
from bistar_gp.m2c_freeze import RESTART_JITTER_SCALE, RESTART_RNG_BASE
from bistar_gp.m2cr.events import EventSink, check_stream_balance


def _quadratic(dimension=3, diagonal=None, center=None):
    if diagonal is None:
        diagonal = np.arange(1, dimension + 1, dtype=np.float64)
    A = np.diag(np.asarray(diagonal, dtype=np.float64))
    if center is None:
        center = np.zeros(dimension, dtype=np.float64)
    center = np.asarray(center, dtype=np.float64)

    def g(u):
        delta = np.asarray(u, dtype=np.float64) - center
        return -0.5 * float(delta @ A @ delta)

    def grad(u):
        return -A @ (np.asarray(u, dtype=np.float64) - center)

    return g, grad


@pytest.mark.parametrize("dimension", [2, 3])
def test_gates_work_at_two_and_three_dimensions(dimension):
    g, grad = _quadratic(dimension)
    optimum = np.zeros(dimension)
    optimized = gates.optimize_conditional_v2(
        lambda u: -g(u), lambda u: -grad(u), np.ones(dimension), -np.ones(dimension)
    )
    assert optimized["stop"] is False
    curved = gates.curvature_gate_v2(
        g, grad, optimum, tuple(f"u{index}" for index in range(dimension))
    )
    assert curved["stop"] is False
    assert curved["evaluations"]["pre_retry"]["raw_hessian"].shape == (
        dimension,
        dimension,
    )


def test_restart_only_on_nonzero_status_and_preserves_jitter(monkeypatch):
    real_minimize = gates.minimize
    calls = 0

    def abnormal_then_real(fun, x0, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            return OptimizeResult(
                x=np.asarray(x0), status=2, success=False, message="abnormal"
            )
        return real_minimize(fun, x0, **kwargs)

    monkeypatch.setattr(gates, "minimize", abnormal_then_real)
    g, grad = _quadratic(3, center=[0.2, -0.1, 0.3])
    result = gates.optimize_conditional_v2(
        lambda u: -g(u), lambda u: -grad(u), np.ones(3), -np.ones(3)
    )
    assert result["restart_count"] == sum(
        len(attempts) == 2 for attempts in result["attempts_by_start"].values()
    )
    assert len(result["attempts_by_start"]["warm"]) == 2
    assert len(result["attempts_by_start"]["mode"]) == 1
    restart = result["attempts_by_start"]["warm"][1]
    jitter = restart["jitter"]
    expected = np.ones(3) + RESTART_JITTER_SCALE * np.random.default_rng(
        RESTART_RNG_BASE
    ).standard_normal(3)
    np.testing.assert_array_equal(
        jitter["resulting_start"], jitter["base_start"] + jitter["jitter_vector"]
    )
    np.testing.assert_array_equal(jitter["resulting_start"], expected)
    np.testing.assert_array_equal(restart["start"], expected)
    assert result["attempts_by_start"]["warm"][0]["status"] == 2


def test_status_zero_success_false_does_not_restart(monkeypatch):
    def false_success(fun, x0, **kwargs):
        return OptimizeResult(
            x=np.zeros_like(x0), status=0, success=False, message="reported false"
        )

    monkeypatch.setattr(gates, "minimize", false_success)
    result = gates.optimize_conditional_v2(
        lambda u: 0.0,
        lambda u: np.zeros_like(u),
        np.ones(3),
        -np.ones(3),
    )
    assert result["restart_count"] == 0
    assert all(len(value) == 1 for value in result["attempts_by_start"].values())
    assert result["stop"] is True


@pytest.mark.parametrize(
    ("candidate", "fallback"),
    [(np.array([1.0, 2.0]), True), (np.array([np.nan, 0.0, 0.0]), True)],
)
def test_retry_evidence_fallback_tagged_union(monkeypatch, candidate, fallback):
    def fake_retry(fun, x0, **kwargs):
        return OptimizeResult(
            x=candidate, status=0, success=True, message="synthetic retry"
        )

    monkeypatch.setattr(gates, "minimize", fake_retry)
    g, grad = _quadratic(3, diagonal=[1.0, 4.0, -2.0])
    result = gates.curvature_gate_v2(g, grad, np.zeros(3), ("a", "b", "c"))
    evidence = result["retry_evidence"]
    assert evidence["fired"] is True
    assert evidence["fallback_fired"] is fallback
    assert evidence["fallback_target"] == "pre_retry_optimum"
    assert evidence["conjuncts"]["output_shape_and_finite"] is False
    assert evidence["positively_accepted"] is False
    np.testing.assert_array_equal(
        result["evaluations"]["post_retry"]["u_star"], np.zeros(3)
    )


def test_retry_positive_acceptance_is_classification_only(monkeypatch):
    center = np.ones(3)
    indefinite = np.diag([1.0, 4.0, -2.0])
    positive = np.diag([1.0, 4.0, 9.0])

    def local_matrix(u):
        return indefinite if np.linalg.norm(np.asarray(u)) < 0.25 else positive

    def g(u):
        u = np.asarray(u, dtype=np.float64)
        matrix = local_matrix(u)
        target = np.zeros(3) if matrix is indefinite else center
        delta = u - target
        return -0.5 * float(delta @ matrix @ delta)

    def grad(u):
        u = np.asarray(u, dtype=np.float64)
        matrix = local_matrix(u)
        target = np.zeros(3) if matrix is indefinite else center
        return -matrix @ (u - target)

    def accepted_retry(fun, x0, **kwargs):
        return OptimizeResult(x=center.copy(), status=0, success=True, message="ok")

    monkeypatch.setattr(gates, "minimize", accepted_retry)
    result = gates.curvature_gate_v2(g, grad, np.zeros(3), ("a", "b", "c"))
    assert result["retry_evidence"]["positively_accepted"] is True
    assert all(result["retry_evidence"]["conjuncts"].values())
    assert result["stop"] is False


def test_event_stream_has_only_gate_events_and_is_balanced(monkeypatch):
    buffer = io.StringIO()
    sink = EventSink(buffer)
    calls = 0

    def one_restart(fun, x0, **kwargs):
        nonlocal calls
        calls += 1
        status = 2 if calls == 1 else 0
        return OptimizeResult(
            x=np.zeros_like(x0),
            status=status,
            success=status == 0,
            message="event fake",
        )

    monkeypatch.setattr(gates, "minimize", one_restart)
    gates.optimize_conditional_v2(
        lambda u: 0.0,
        lambda u: np.zeros_like(u),
        np.ones(3),
        -np.ones(3),
        event_sink=sink,
        node_index=7,
    )
    lines = buffer.getvalue().splitlines()
    assert check_stream_balance(lines)["balanced"] is True
    events = [json.loads(line) for line in lines]
    assert [event["event"] for event in events].count("ATTEMPT_BEGIN") == 3
    assert [event["event"] for event in events].count("ATTEMPT_END") == 3
    assert all(event.get("node_index") == 7 for event in events)
    assert all(event["persisted_axis_order"] is None for event in events)
    assert events[-1]["event"] == "EVAL_RESULT"
    assert events[-1]["start_label"] == "warm"
    assert events[-1]["attempt_index"] == 0
    assert not ({"STAGE_BEGIN", "STAGE_END", "NODE_BEGIN", "NODE_END"} & {
        event["event"] for event in events
    })


def test_curvature_event_retry_shape(monkeypatch):
    buffer = io.StringIO()
    sink = EventSink(buffer)

    def fake_retry(fun, x0, **kwargs):
        return OptimizeResult(x=x0, status=0, success=False, message="false")

    monkeypatch.setattr(gates, "minimize", fake_retry)
    g, grad = _quadratic(3, diagonal=[1.0, 4.0, -2.0])
    result = gates.curvature_gate_v2(
        g, grad, np.zeros(3), ("a", "b", "c"), event_sink=sink, node_index=4
    )
    lines = [json.loads(line) for line in buffer.getvalue().splitlines()]
    assert check_stream_balance(buffer.getvalue().splitlines())["balanced"] is True
    assert [line["event"] for line in lines] == [
        "EVAL_RESULT",
        "RETRY_BEGIN",
        "EVAL_RESULT",
    ]
    # External audit F4: the post-retry durable event carries the FINALIZED
    # verdict (post the retry-optimizer stop override) and the retry summary,
    # so the durability channel can never contradict the returned record.
    post = lines[2]
    assert post["phase"] == "post_retry"
    assert post["stop"] == result["stop"]
    assert post["retry_verdict"] == {
        "retry_optimizer_status": 0,
        "retry_optimizer_success": False,
        "positively_accepted": False,
        "fallback_fired": False,
    }


def test_event_vectors_are_canonical_but_gate_returns_stay_storage_order(
    monkeypatch,
):
    perm = (1, 2, 0)
    optimizer_buffer = io.StringIO()

    def fixed_optimizer(fun, x0, **kwargs):
        return OptimizeResult(
            x=np.array([1.0, 2.0, 3.0]),
            status=0,
            success=True,
            message="fixed storage result",
        )

    monkeypatch.setattr(gates, "minimize", fixed_optimizer)
    optimized = gates.optimize_conditional_v2(
        lambda u: 0.0,
        lambda u: np.array([-4.0, -5.0, -6.0]),
        np.array([10.0, 20.0, 30.0]),
        np.array([-10.0, -20.0, -30.0]),
        event_sink=EventSink(optimizer_buffer),
        perm=perm,
    )
    optimizer_events = [
        json.loads(line) for line in optimizer_buffer.getvalue().splitlines()
    ]
    assert all(
        event["persisted_axis_order"] == ["ls", "os", "lv"]
        for event in optimizer_events
    )
    warm_begin = optimizer_events[0]
    warm_result = next(
        event
        for event in optimizer_events
        if event["event"] == "EVAL_RESULT" and event["start_label"] == "warm"
    )
    assert warm_begin["start"] == [20.0, 30.0, 10.0]
    assert warm_result["u"] == [2.0, 3.0, 1.0]
    assert warm_result["gradient"] == [5.0, 6.0, 4.0]
    np.testing.assert_array_equal(
        optimized["attempts_by_start"]["warm"][0]["start"],
        [10.0, 20.0, 30.0],
    )
    np.testing.assert_array_equal(
        optimized["attempts_by_start"]["warm"][0]["u"], [1.0, 2.0, 3.0]
    )
    np.testing.assert_array_equal(
        optimized["attempts_by_start"]["warm"][0]["gradient"],
        [4.0, 5.0, 6.0],
    )

    curvature_buffer = io.StringIO()
    g, grad = _quadratic(3, diagonal=[1.0, 4.0, 9.0], center=[10.0, 20.0, 30.0])
    curved = gates.curvature_gate_v2(
        g,
        grad,
        np.array([10.0, 20.0, 30.0]),
        ("storage-0", "storage-1", "storage-2"),
        event_sink=EventSink(curvature_buffer),
        perm=perm,
    )
    curvature_event = json.loads(curvature_buffer.getvalue())
    assert curvature_event["persisted_axis_order"] == ["ls", "os", "lv"]
    assert curvature_event["u_star"] == [20.0, 30.0, 10.0]
    np.testing.assert_array_equal(
        curvature_event["eigenvalues"],
        curved["evaluations"]["pre_retry"]["eigenvalues"],
    )
    np.testing.assert_array_equal(
        curved["evaluations"]["pre_retry"]["u_star"], [10.0, 20.0, 30.0]
    )
