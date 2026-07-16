"""Versioned profile gates with complete attempt and retry evidence.

The scientific verdict branches reproduce the frozen v1.17 gates.  The v2
surface retains optimizer calls and curvature evaluations that the frozen
return values discard, and can emit the write-ahead gate events of plan
§3.2.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

import numpy as np
from scipy.optimize import minimize

from bistar_gp.m2c_freeze import (
    AGREE_DG_REL,
    AGREE_DU_INF,
    DIRECTIONAL_EPS,
    DIRECTIONAL_TOL,
    DIRECTION_RNG_SEEDS,
    HESS_H_CENTER,
    HESS_H_SWEEP,
    LBFGSB_FTOL,
    LBFGSB_GTOL,
    LBFGSB_MAXFUN,
    LBFGSB_MAXITER,
    LOGDET_STABILITY_TOL,
    RCOND_MIN,
    RESTART_JITTER_SCALE,
    RESTART_RNG_BASE,
    RETRY_FTOL,
    RETRY_GTOL,
    RETRY_MAXITER,
    SYMMETRY_TOL,
    TAU_STAT,
)
from bistar_gp.m2cr.coordinates import (
    CANONICAL_AXIS_ORDER,
    matrix_storage_to_canonical,
    vector_storage_to_canonical,
)

__all__ = ["optimize_conditional_v2", "curvature_gate_v2"]


def _attempt_record(
    neg_g: Callable[[np.ndarray], float],
    neg_grad: Callable[[np.ndarray], np.ndarray],
    result: Any,
    start: np.ndarray,
    expected_shape: tuple[int, ...],
    *,
    is_jittered_restart: bool,
    jitter: dict[str, Any] | None = None,
) -> dict[str, Any]:
    u_opt = np.asarray(result.x, dtype=np.float64)
    reported_success = int(result.status) == 0 and bool(
        getattr(result, "success", True)
    )
    g_value = float(-np.asarray(neg_g(u_opt), dtype=np.float64))
    grad_g = -np.asarray(neg_grad(u_opt), dtype=np.float64)
    finite = bool(
        u_opt.shape == expected_shape
        and np.all(np.isfinite(u_opt))
        and np.isfinite(g_value)
        and grad_g.shape == expected_shape
        and np.all(np.isfinite(grad_g))
    )
    grad_inf = float(np.linalg.norm(grad_g, ord=np.inf)) if finite else np.inf
    stationary = bool(finite and grad_inf <= TAU_STAT)
    accepted = bool(reported_success and finite and stationary)
    record = {
        "is_jittered_restart": is_jittered_restart,
        "start": start.copy(),
        "u": u_opt,
        "g": g_value,
        "gradient": grad_g,
        "grad_inf_norm": grad_inf,
        "status": int(result.status),
        "reported_success": reported_success,
        "finite": finite,
        "stationary": stationary,
        "accepted": accepted,
        "message": str(result.message),
    }
    if jitter is not None:
        record["jitter"] = jitter
    return record


def _emit_attempt_result(
    event_sink: Any,
    record: dict[str, Any],
    *,
    start_label: str,
    attempt_index: int,
    node_index: int | None,
    perm: Sequence[int] | None,
) -> None:
    if event_sink is None:
        return
    event_sink.emit(
        "EVAL_RESULT",
        gate="optimizer",
        start_label=start_label,
        attempt_index=attempt_index,
        node_index=node_index,
        is_jittered_restart=record["is_jittered_restart"],
        persisted_axis_order=_event_axis_order(perm),
        u=_event_vector(record["u"], perm),
        g=record["g"],
        gradient=_event_vector(record["gradient"], perm),
        grad_inf_norm=record["grad_inf_norm"],
        status=record["status"],
        reported_success=record["reported_success"],
        finite=record["finite"],
        stationary=record["stationary"],
        accepted=record["accepted"],
        message=record["message"],
    )


def _event_axis_order(perm: Sequence[int] | None) -> list[str] | None:
    return None if perm is None else list(CANONICAL_AXIS_ORDER)


def _event_vector(values: Any, perm: Sequence[int] | None) -> list[float]:
    vector = np.asarray(values, dtype=np.float64)
    if perm is not None:
        vector = vector_storage_to_canonical(vector, perm)
    return vector.tolist()


def _event_matrix(values: Any, perm: Sequence[int] | None) -> list[list[float]]:
    matrix = np.asarray(values, dtype=np.float64)
    if perm is not None:
        matrix = matrix_storage_to_canonical(matrix, perm)
    return matrix.tolist()


def optimize_conditional_v2(
    neg_g: Callable[[np.ndarray], float],
    neg_grad: Callable[[np.ndarray], np.ndarray],
    u0_warm: np.ndarray | Sequence[float],
    u0_mode: np.ndarray | Sequence[float],
    *,
    event_sink: Any = None,
    node_index: int | None = None,
    perm: Sequence[int] | None = None,
) -> dict[str, Any]:
    """Apply the frozen two-start gate while retaining every minimize call.

    A failed original attempt is not evaluated until the complete frozen
    optimizer/oracle sequence has finished.  Its ``ATTEMPT_END`` therefore
    carries ``telemetry_deferred=True`` and its ``EVAL_RESULT`` is emitted
    later as a point event.  With ``perm``, coordinate-vector event payloads
    are canonical ``(ls, os, lv)``; return values remain in storage order.
    """

    warm = np.asarray(u0_warm, dtype=np.float64)
    mode = np.asarray(u0_mode, dtype=np.float64)
    if warm.ndim != 1 or mode.shape != warm.shape or warm.size == 0:
        raise ValueError("optimizer starts must be nonempty vectors of equal shape")
    if not np.all(np.isfinite(warm)) or not np.all(np.isfinite(mode)):
        raise ValueError("optimizer starts must be finite")

    options = {
        "maxiter": LBFGSB_MAXITER,
        "maxfun": LBFGSB_MAXFUN,
        "ftol": LBFGSB_FTOL,
        "gtol": LBFGSB_GTOL,
    }
    restart_count = 0
    records: list[dict[str, Any]] = []
    attempt_slots: dict[str, list[dict[str, Any] | None]] = {}
    discarded_originals: list[tuple[str, Any, np.ndarray]] = []
    for index, (label, start) in enumerate((("warm", warm), ("mode", mode))):
        if event_sink is not None:
            event_sink.emit(
                "ATTEMPT_BEGIN",
                start_label=label,
                attempt_index=0,
                is_jittered_restart=False,
                node_index=node_index,
                persisted_axis_order=_event_axis_order(perm),
                start=_event_vector(start, perm),
            )
        result = minimize(
            neg_g,
            start.copy(),
            jac=neg_grad,
            method="L-BFGS-B",
            options=options,
        )
        if int(result.status) != 0:
            restart_count += 1
            discarded_originals.append((label, result, start.copy()))
            if event_sink is not None:
                # Closing the attempt here keeps the write-ahead stream
                # balanced without evaluating the discarded result early.
                # Everything SciPy already returned is durable immediately
                # (plan §3.2: the stream is the durability channel); only the
                # oracle-derived telemetry is deferred, to preserve the
                # frozen oracle-call prefix.
                u_flat = np.asarray(result.x, dtype=np.float64).reshape(-1)
                # The event declares canonical axis order, so a well-shaped
                # vector is permuted like every other vector payload; a
                # wrong-shaped rigged result stays raw with a null order.
                well_shaped = perm is not None and u_flat.size == len(perm)
                event_sink.emit(
                    "ATTEMPT_END",
                    start_label=label,
                    attempt_index=0,
                    is_jittered_restart=False,
                    node_index=node_index,
                    persisted_axis_order=(
                        _event_axis_order(perm) if well_shaped or perm is None
                        else None
                    ),
                    status=int(result.status),
                    scipy_success=bool(getattr(result, "success", True)),
                    message=str(result.message),
                    u_raw=(
                        _event_vector(u_flat, perm)
                        if well_shaped
                        else u_flat.tolist()
                    ),
                    telemetry_deferred=True,
                )
            rng_seed = RESTART_RNG_BASE + index
            rng = np.random.default_rng(rng_seed)
            draw = rng.standard_normal(start.size)
            jitter_vector = RESTART_JITTER_SCALE * draw
            jittered = start + RESTART_JITTER_SCALE * draw
            jitter = {
                "rng_seed": rng_seed,
                "jitter_scale": RESTART_JITTER_SCALE,
                "base_start": start.copy(),
                "jitter_vector": jitter_vector,
                "resulting_start": jittered.copy(),
            }
            if event_sink is not None:
                event_sink.emit(
                    "ATTEMPT_BEGIN",
                    start_label=label,
                    attempt_index=1,
                    is_jittered_restart=True,
                    node_index=node_index,
                    persisted_axis_order=_event_axis_order(perm),
                    start=_event_vector(jittered, perm),
                )
            result = minimize(
                neg_g,
                jittered,
                jac=neg_grad,
                method="L-BFGS-B",
                options=options,
            )
            restarted = _attempt_record(
                neg_g,
                neg_grad,
                result,
                jittered,
                start.shape,
                is_jittered_restart=True,
                jitter=jitter,
            )
            _emit_attempt_result(
                event_sink,
                restarted,
                start_label=label,
                attempt_index=1,
                node_index=node_index,
                perm=perm,
            )
            if event_sink is not None:
                event_sink.emit(
                    "ATTEMPT_END",
                    start_label=label,
                    attempt_index=1,
                    is_jittered_restart=True,
                    node_index=node_index,
                    persisted_axis_order=_event_axis_order(perm),
                    status=restarted["status"],
                    accepted=restarted["accepted"],
                )
            final_attempt = restarted
            attempt_slots[label] = [None, restarted]
        else:
            original = _attempt_record(
                neg_g,
                neg_grad,
                result,
                start,
                start.shape,
                is_jittered_restart=False,
            )
            _emit_attempt_result(
                event_sink,
                original,
                start_label=label,
                attempt_index=0,
                node_index=node_index,
                perm=perm,
            )
            if event_sink is not None:
                event_sink.emit(
                    "ATTEMPT_END",
                    start_label=label,
                    attempt_index=0,
                    is_jittered_restart=False,
                    node_index=node_index,
                    persisted_axis_order=_event_axis_order(perm),
                    status=original["status"],
                    accepted=original["accepted"],
                )
            final_attempt = original
            attempt_slots[label] = [original]

        records.append(
            {
                "label": label,
                "u": final_attempt["u"],
                "g": final_attempt["g"],
                "grad_inf_norm": final_attempt["grad_inf_norm"],
                "status": final_attempt["status"],
                "reported_success": final_attempt["reported_success"],
                "finite": final_attempt["finite"],
                "stationary": final_attempt["stationary"],
                "accepted": final_attempt["accepted"],
                "message": final_attempt["message"],
            }
        )

    both_success = bool(all(record["accepted"] for record in records))
    comparable = bool(all(record["finite"] for record in records))
    if comparable:
        g_scale = max(1.0, *(abs(record["g"]) for record in records))
        agree_g = abs(records[0]["g"] - records[1]["g"]) <= AGREE_DG_REL * g_scale
        agree_u = (
            np.linalg.norm(records[0]["u"] - records[1]["u"], ord=np.inf)
            <= AGREE_DU_INF
        )
        agree = bool(agree_g and agree_u)
    else:
        agree_g = False
        agree_u = False
        agree = False

    finite_records = [record for record in records if record["finite"]]
    best = max(finite_records, key=lambda record: record["g"]) if finite_records else None
    stop = not (both_success and agree)
    failures: list[str] = []
    for record in records:
        if not record["reported_success"]:
            failures.append(f"{record['label']} optimizer failed")
        elif not record["finite"]:
            failures.append(f"{record['label']} result is non-finite")
        elif not record["stationary"]:
            failures.append(f"{record['label']} result is non-stationary")
    if both_success and not agree_g:
        failures.append("start objective values disagree")
    if both_success and not agree_u:
        failures.append("start optima disagree")

    # The frozen verdict and every oracle call that can affect it are now
    # complete.  Only v2's extra evidence for discarded originals follows.
    for label, result, start in discarded_originals:
        original = _attempt_record(
            neg_g,
            neg_grad,
            result,
            start,
            start.shape,
            is_jittered_restart=False,
        )
        attempt_slots[label][0] = original
        _emit_attempt_result(
            event_sink,
            original,
            start_label=label,
            attempt_index=0,
            node_index=node_index,
            perm=perm,
        )
    attempts_by_start = {
        label: [attempt for attempt in attempts if attempt is not None]
        for label, attempts in attempt_slots.items()
    }

    return {
        "u_star": None if best is None else best["u"].copy(),
        "g_star": np.nan if best is None else float(best["g"]),
        "grad_inf_norm": np.inf if best is None else float(best["grad_inf_norm"]),
        "both_success": both_success,
        "agree": agree,
        "agree_g": bool(agree_g),
        "agree_u": bool(agree_u),
        "restart_count": restart_count,
        "stop": stop,
        "reason": "; ".join(failures),
        "starts": {record["label"]: record for record in records},
        "attempts_by_start": attempts_by_start,
    }


def _curvature_evaluation_v2(
    g: Callable[[np.ndarray], float],
    grad: Callable[[np.ndarray], np.ndarray],
    u_star: np.ndarray,
    nuisance_order: tuple[str, ...],
) -> tuple[dict[str, Any], dict[str, Any]]:
    dimension = u_star.size
    identity = np.eye(dimension, dtype=np.float64)
    raw_by_h: dict[float, np.ndarray] = {}
    symmetric_by_h: dict[float, np.ndarray] = {}
    logdet_by_h: dict[float, float] = {}
    for h in HESS_H_SWEEP:
        hessian = np.empty((dimension, dimension), dtype=np.float64)
        for column in range(dimension):
            plus = np.asarray(grad(u_star + h * identity[column]), dtype=np.float64)
            minus = np.asarray(grad(u_star - h * identity[column]), dtype=np.float64)
            if plus.shape != u_star.shape or minus.shape != u_star.shape:
                raise ValueError("gradient callable returned the wrong shape")
            hessian[:, column] = (plus - minus) / (2.0 * h)
        raw = -hessian
        curvature = 0.5 * (raw + raw.T)
        raw_by_h[h] = raw
        symmetric_by_h[h] = curvature
        sign, logabsdet = np.linalg.slogdet(curvature)
        logdet_by_h[h] = float(logabsdet) if sign != 0 else -np.inf

    raw_center = raw_by_h[HESS_H_CENTER]
    curvature = symmetric_by_h[HESS_H_CENTER]
    symmetry_error = float(
        np.linalg.norm(raw_center - raw_center.T, ord="fro")
        / max(1.0, np.linalg.norm(raw_center, ord="fro"))
    )
    symmetry_ok = bool(np.isfinite(symmetry_error) and symmetry_error <= SYMMETRY_TOL)

    center_logdet = logdet_by_h[HESS_H_CENTER]
    if np.isfinite(center_logdet):
        logdet_errors = {
            h: abs(value - center_logdet) / max(1.0, abs(center_logdet))
            for h, value in logdet_by_h.items()
            if h != HESS_H_CENTER
        }
        logdet_error = float(max(logdet_errors.values(), default=0.0))
    else:
        logdet_errors = {
            h: np.inf for h in HESS_H_SWEEP if h != HESS_H_CENTER
        }
        logdet_error = np.inf
    logdet_stable = bool(
        np.isfinite(logdet_error) and logdet_error <= LOGDET_STABILITY_TOL
    )

    g_center = float(g(u_star))
    grad_center = np.asarray(grad(u_star), dtype=np.float64)
    grad_inf_norm = (
        float(np.linalg.norm(grad_center, ord=np.inf))
        if grad_center.shape == u_star.shape and np.all(np.isfinite(grad_center))
        else np.inf
    )
    stationary = bool(np.isfinite(grad_inf_norm) and grad_inf_norm <= TAU_STAT)

    directional_errors: dict[int, float] = {}
    directional_second: dict[int, float] = {}
    directional_directions: dict[int, np.ndarray] = {}
    for seed in DIRECTION_RNG_SEEDS:
        rng = np.random.default_rng(seed)
        direction = rng.standard_normal(dimension)
        direction /= np.linalg.norm(direction)
        second = float(
            (
                g(u_star + DIRECTIONAL_EPS * direction)
                - 2.0 * g_center
                + g(u_star - DIRECTIONAL_EPS * direction)
            )
            / DIRECTIONAL_EPS**2
        )
        quadratic = float(direction @ curvature @ direction)
        error = abs(quadratic + second) / max(1.0, abs(second))
        directional_second[seed] = second
        directional_errors[seed] = float(error)
        directional_directions[seed] = direction.copy()
    directional_ok = bool(
        all(
            np.isfinite(error) and error <= DIRECTIONAL_TOL
            for error in directional_errors.values()
        )
    )

    eigenvalues = np.linalg.eigvalsh(curvature)
    lambda_min = float(eigenvalues[0])
    lambda_max = float(eigenvalues[-1])
    spd = bool(
        np.all(np.isfinite(eigenvalues))
        and lambda_min > 0.0
        and lambda_max > 0.0
    )
    rcond = float(lambda_min / lambda_max) if lambda_max != 0.0 else np.nan
    conditioning_ok = bool(spd and np.isfinite(rcond) and rcond >= RCOND_MIN)
    stop = not (
        stationary
        and symmetry_ok
        and logdet_stable
        and directional_ok
        and conditioning_ok
    )

    failures = []
    if not stationary:
        failures.append("u_star is non-stationary")
    if not symmetry_ok:
        failures.append("pre-symmetrization check failed")
    if not logdet_stable:
        failures.append("logdet stability check failed")
    if not directional_ok:
        failures.append("directional curvature check failed")
    if not spd:
        failures.append("curvature is not strictly SPD")
    elif not conditioning_ok:
        failures.append("curvature rcond is below the frozen minimum")

    evaluation = {
        "K": curvature,
        "eigenvalues": eigenvalues,
        "logdet": center_logdet,
        "rcond": rcond,
        "spd": spd,
        "conditioning_ok": conditioning_ok,
        "stationary": stationary,
        "grad_inf_norm": grad_inf_norm,
        "symmetry_ok": symmetry_ok,
        "symmetry_error": symmetry_error,
        "logdet_stable": logdet_stable,
        "logdet_stability_error": logdet_error,
        "logdet_by_h": logdet_by_h,
        "directional_ok": directional_ok,
        "directional_errors": directional_errors,
        "directional_second_differences": directional_second,
        "nuisance_order": nuisance_order,
        "u_star": u_star.copy(),
        "stop": stop,
        "reason": "; ".join(failures),
        "raw_hessian": raw_center,
        "directional_directions": directional_directions,
    }
    evaluated_point = {
        "objective": g_center,
        "gradient": grad_center,
        "stationarity_norm": grad_inf_norm,
    }
    return evaluation, evaluated_point


def _emit_curvature_result(
    event_sink: Any,
    evaluation: dict[str, Any],
    *,
    phase: str,
    node_index: int | None,
    perm: Sequence[int] | None,
) -> None:
    if event_sink is None:
        return
    # The full already-computed evaluation rides in the durable event, so a
    # crash before node-file assembly loses nothing (plan §3.2); no oracle
    # call happens here.
    event_sink.emit(
        "EVAL_RESULT",
        gate="curvature",
        phase=phase,
        node_index=node_index,
        persisted_axis_order=_event_axis_order(perm),
        u_star=_event_vector(evaluation["u_star"], perm),
        raw_hessian=_event_matrix(evaluation["raw_hessian"], perm),
        K=_event_matrix(evaluation["K"], perm),
        # Spectral order is invariant and is never coordinate-permuted.
        eigenvalues=np.asarray(evaluation["eigenvalues"], dtype=np.float64).tolist(),
        logdet=evaluation["logdet"],
        logdet_by_h=[
            {"h": float(h), "logdet": evaluation["logdet_by_h"][h]}
            for h in HESS_H_SWEEP
        ],
        logdet_stability_error=evaluation["logdet_stability_error"],
        symmetry_error=evaluation["symmetry_error"],
        directional=[
            {
                "seed": int(seed),
                "direction": _event_vector(
                    evaluation["directional_directions"][seed], perm
                ),
                "second_difference": evaluation["directional_second_differences"][
                    seed
                ],
                "error": evaluation["directional_errors"][seed],
            }
            for seed in DIRECTION_RNG_SEEDS
        ],
        rcond=evaluation["rcond"],
        spd=evaluation["spd"],
        conditioning_ok=evaluation["conditioning_ok"],
        stationary=evaluation["stationary"],
        grad_inf_norm=evaluation["grad_inf_norm"],
        symmetry_ok=evaluation["symmetry_ok"],
        logdet_stable=evaluation["logdet_stable"],
        directional_ok=evaluation["directional_ok"],
        stop=evaluation["stop"],
        reason=evaluation["reason"],
    )


def curvature_gate_v2(
    g: Callable[[np.ndarray], float],
    grad: Callable[[np.ndarray], np.ndarray],
    u_star: np.ndarray | Sequence[float],
    nuisance_order: Sequence[str],
    *,
    event_sink: Any = None,
    node_index: int | None = None,
    perm: Sequence[int] | None = None,
) -> dict[str, Any]:
    """Apply the frozen curvature gate while retaining retry evidence.

    With ``perm``, coordinate-vector event payloads are canonical
    ``(ls, os, lv)``.  Eigenvalues stay in spectral order and return values
    stay in storage order.
    """

    optimum = np.asarray(u_star, dtype=np.float64)
    order = tuple(nuisance_order)
    if optimum.ndim != 1 or optimum.size == 0 or len(order) != optimum.size:
        raise ValueError("u_star and nuisance_order must describe the same nonempty vector")
    if not np.all(np.isfinite(optimum)):
        raise ValueError("u_star must be finite")

    pre_retry, _pre_point = _curvature_evaluation_v2(g, grad, optimum, order)
    _emit_curvature_result(
        event_sink,
        pre_retry,
        phase="pre_retry",
        node_index=node_index,
        perm=perm,
    )
    evaluation = pre_retry.copy()
    evaluation["retry_count"] = 0
    evaluation["retry_optimizer_success"] = None
    evaluation["retry_optimizer_status"] = None
    evaluation["evaluations"] = {"pre_retry": pre_retry}
    evaluation["retry_evidence"] = {"fired": False}
    if evaluation["conditioning_ok"]:
        return evaluation

    if event_sink is not None:
        event_sink.emit(
            "RETRY_BEGIN",
            gate="curvature",
            node_index=node_index,
            persisted_axis_order=_event_axis_order(perm),
            trigger="spd_or_rcond_conditioning_failure",
        )
    retry = minimize(
        lambda u: -float(g(np.asarray(u, dtype=np.float64))),
        optimum.copy(),
        jac=lambda u: -np.asarray(grad(np.asarray(u, dtype=np.float64)), dtype=np.float64),
        method="L-BFGS-B",
        options={
            "gtol": RETRY_GTOL,
            "ftol": RETRY_FTOL,
            "maxiter": RETRY_MAXITER,
        },
    )
    raw_candidate = np.asarray(retry.x, dtype=np.float64)
    retried_optimum = raw_candidate
    candidate_finite = bool(np.all(np.isfinite(raw_candidate)))
    output_shape_and_finite = bool(
        retried_optimum.shape == optimum.shape and candidate_finite
    )
    fallback_fired = not output_shape_and_finite
    if fallback_fired:
        retried_optimum = optimum.copy()
    post_retry, evaluated_point = _curvature_evaluation_v2(
        g, grad, retried_optimum, order
    )
    _emit_curvature_result(
        event_sink,
        post_retry,
        phase="post_retry",
        node_index=node_index,
        perm=perm,
    )
    retry_success = int(retry.status) == 0 and bool(
        getattr(retry, "success", True)
    )
    if not retry_success:
        post_retry = post_retry.copy()
        post_retry["stop"] = True
        suffix = "curvature retry optimization failed"
        post_retry["reason"] = "; ".join(
            part for part in (post_retry["reason"], suffix) if part
        )
    evaluation = post_retry.copy()
    evaluation["retry_count"] = 1
    evaluation["retry_optimizer_success"] = retry_success
    evaluation["retry_optimizer_status"] = int(retry.status)

    gradient = evaluated_point["gradient"]
    objective_finite = bool(np.isfinite(evaluated_point["objective"]))
    gradient_shape_and_finite = bool(
        gradient.shape == optimum.shape and np.all(np.isfinite(gradient))
    )
    stationarity_within_bound = bool(
        np.isfinite(evaluated_point["stationarity_norm"])
        and evaluated_point["stationarity_norm"] <= TAU_STAT
    )
    conjuncts = {
        "status_zero": int(retry.status) == 0,
        "reported_success": bool(getattr(retry, "success", True)),
        "output_shape_and_finite": output_shape_and_finite,
        "objective_finite": objective_finite,
        "gradient_shape_and_finite": gradient_shape_and_finite,
        "stationarity_within_bound": stationarity_within_bound,
    }
    retry_evidence: dict[str, Any] = {
        "fired": True,
        "trigger": "spd_or_rcond_conditioning_failure",
        "telemetry": {
            "status": int(retry.status),
            "reported_success": bool(getattr(retry, "success", True)),
            "message": str(retry.message),
            "candidate_vector": raw_candidate.reshape(-1).copy(),
            "candidate_finite": candidate_finite,
            "required_shape": list(optimum.shape),
            "observed_shape": list(raw_candidate.shape),
            "objective": evaluated_point["objective"],
            "gradient": gradient,
            "stationarity_norm": evaluated_point["stationarity_norm"],
        },
        "conjuncts": conjuncts,
        "positively_accepted": bool(all(conjuncts.values())),
        "fallback_fired": fallback_fired,
    }
    if fallback_fired:
        retry_evidence["fallback_target"] = "pre_retry_optimum"
    evaluation["evaluations"] = {
        "pre_retry": pre_retry,
        "post_retry": post_retry,
    }
    evaluation["retry_evidence"] = retry_evidence
    return evaluation
