"""Pure R3 diagnostic protocol helpers and Layer-1b manifest tooling.

The numerical rules implement prereg v1.21 sections 3--4 and the Layer-1b
artifact graph implements prereg v1.21 section 6 / plan section 3.1.  This
module performs no scientific computation and imports no scientific stack.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from bistar_gp.m2c_freeze import HESS_H_CENTER
from bistar_gp.m2cr.coordinates import (
    vector_canonical_to_storage,
    vector_storage_to_canonical,
)
from bistar_gp.m2cr.serialization import (
    atomic_write_canonical_json,
    canonical_sha256,
    encode_float,
    sha256_file,
)

__all__ = [
    "SWEEP_H_VALUES",
    "DECISION_TABLE_ROWS",
    "PROTOCOL_MANIFEST_RELPATH",
    "DIAGNOSTIC_SCHEMA_RELPATH",
    "PROTOCOL_PARAMETERS_RELPATH",
    "symmetry_error_at_h",
    "symmetry_error_sweep",
    "ols_loglog",
    "classify_slope",
    "slope_analysis_record",
    "sweep_record",
    "evaluate_decision_table",
    "canonical_bridge",
    "build_protocol_manifest",
    "verify_protocol_manifest",
    "main",
]

# Prereg v1.21 section 3, ballot B12(a): the factor-two five-point sweep.
SWEEP_H_VALUES = (2.5e-4, 5e-4, 1e-3, 2e-3, 4e-3)
if HESS_H_CENTER != SWEEP_H_VALUES[2]:
    raise RuntimeError("the frozen Hessian center is not the R3 sweep center")

PROTOCOL_MANIFEST_RELPATH = "docs/m2c_freeze/m2cr_protocol_manifest_v1.json"
DIAGNOSTIC_SCHEMA_RELPATH = (
    "docs/m2c_freeze/m2c_diagnostic_record.schema_v1.json"
)
PROTOCOL_PARAMETERS_RELPATH = (
    "docs/m2c_freeze/m2cr_diagnostic_protocol_v1.json"
)
_INFRASTRUCTURE_MANIFEST_RELPATH = (
    "docs/m2c_freeze/m2cr_infrastructure_manifest_v1.json"
)
_HEX64_RE = re.compile(r"[0-9a-f]{64}")
_MANIFEST_KEYS = {
    "kind",
    "schema_version",
    "addendum",
    "diagnostic_record_schema",
    "protocol_parameters",
    "infrastructure_manifest_sha256",
}
_PIN_KEYS = {"path", "sha256"}

_MODULE_REPO_ROOT = Path(__file__).resolve().parents[2]
_PARAMETERS_PATH = _MODULE_REPO_ROOT / PROTOCOL_PARAMETERS_RELPATH
_SCHEMA_PATH = _MODULE_REPO_ROOT / DIAGNOSTIC_SCHEMA_RELPATH
_EXECUTION_SCHEMA_PATH = (
    _MODULE_REPO_ROOT
    / "docs/m2c_freeze/m2c_execution_record.schema_v1.json"
)


def _read_json_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON artifact is not an object: {path}")
    return value


_PARAMETERS = _read_json_object(_PARAMETERS_PATH)
DECISION_TABLE_ROWS = [
    dict(row) for row in _PARAMETERS["decision_table"]["rows"]
]

_DIAGNOSTIC_SCHEMA = _read_json_object(_SCHEMA_PATH)
_EXECUTION_SCHEMA = _read_json_object(_EXECUTION_SCHEMA_PATH)
_DIAGNOSTIC_REGISTRY = Registry().with_resources(
    [
        (
            _DIAGNOSTIC_SCHEMA["$id"],
            Resource.from_contents(_DIAGNOSTIC_SCHEMA),
        ),
        (
            _EXECUTION_SCHEMA["$id"],
            Resource.from_contents(_EXECUTION_SCHEMA),
        ),
    ]
)


def symmetry_error_at_h(
    grad: Callable[[np.ndarray], np.ndarray],
    u_star: np.ndarray | Sequence[float],
    h: float,
) -> float:
    """Measure raw-Hessian asymmetry at one step (v1.21 section 3/B12(a))."""

    optimum = np.asarray(u_star, dtype=np.float64)
    step = float(h)
    if optimum.ndim != 1 or optimum.size == 0:
        raise ValueError("u_star must be a nonempty vector")
    if not math.isfinite(step) or step <= 0.0:
        raise ValueError("h must be finite and positive")
    identity = np.eye(optimum.size, dtype=np.float64)
    hessian = np.empty((optimum.size, optimum.size), dtype=np.float64)
    for column in range(optimum.size):
        plus = np.asarray(
            grad(optimum + step * identity[column]), dtype=np.float64
        )
        minus = np.asarray(
            grad(optimum - step * identity[column]), dtype=np.float64
        )
        if plus.shape != optimum.shape or minus.shape != optimum.shape:
            raise ValueError("gradient callable returned the wrong shape")
        hessian[:, column] = (plus - minus) / (2.0 * step)
    raw = -hessian
    return float(
        np.linalg.norm(raw - raw.T, ord="fro")
        / max(1.0, np.linalg.norm(raw, ord="fro"))
    )


def symmetry_error_sweep(
    grad: Callable[[np.ndarray], np.ndarray],
    u_star: np.ndarray | Sequence[float],
) -> list[float]:
    """Return the frozen five-point asymmetry sweep in protocol order."""

    return [symmetry_error_at_h(grad, u_star, h) for h in SWEEP_H_VALUES]


def ols_loglog(
    h_values: Sequence[float], errors: Sequence[float]
) -> dict[str, Any]:
    """Fit the B12(c) five-point natural-log OLS, failing closed."""

    if len(h_values) != 5 or len(errors) != 5:
        raise ValueError("the slope fit requires exactly five h/error pairs")
    error_values = np.asarray(errors, dtype=np.float64)
    if np.any(~np.isfinite(error_values)):
        return {"defined": False, "reason": "nonfinite_sweep_value"}
    if np.any(error_values <= 0.0):
        return {"defined": False, "reason": "nonpositive_sweep_value"}

    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        x = np.asarray(np.log(np.asarray(h_values, dtype=np.float64)), dtype=np.float64)
        y = np.asarray(np.log(error_values), dtype=np.float64)
        xbar = float(np.mean(x))
        ybar = float(np.mean(y))
        numerator = float(np.sum((x - xbar) * (y - ybar)))
        denominator = float(np.sum((x - xbar) ** 2))
        slope = float(np.divide(numerator, denominator))
        intercept = float(ybar - slope * xbar)
    required_statistics = np.concatenate(
        (
            x.reshape(-1),
            y.reshape(-1),
            np.asarray(
                [xbar, ybar, numerator, denominator, slope, intercept],
                dtype=np.float64,
            ),
        )
    )
    if not np.all(np.isfinite(required_statistics)):
        return {"defined": False, "reason": "nonfinite_ols_statistic"}
    return {"defined": True, "slope": slope, "intercept": intercept}


def classify_slope(fit: Mapping[str, Any]) -> str:
    """Apply the exact inclusive v1.21 section 3 slope windows.

    The comparisons are the frozen real boundaries verbatim: B12(b) forbids
    widening the windows, so no epsilon or adjacent-representable slack of
    any size exists here.  A fitted slope that float64 rounding lands one ULP
    outside a window is classified by the window it actually falls in.
    """

    if fit.get("defined") is not True:
        return "UNDEFINED"
    slope = float(fit["slope"])
    if 1.5 <= slope <= 2.5:
        return "TRUNCATION_LIKE"
    if slope <= -0.5:
        return "NOISE_LIKE"
    return "FLAT"


def slope_analysis_record(
    h_values: Sequence[float], errors: Sequence[float]
) -> dict[str, Any]:
    """Build and schema-validate the R3 slope-analysis object."""

    fit = ols_loglog(h_values, errors)
    classification = classify_slope(fit)
    if classification == "UNDEFINED":
        record = {
            "classification": classification,
            "undefined_reason": fit["reason"],
        }
    else:
        record = {
            "classification": classification,
            "slope": float(fit["slope"]),
            "intercept": float(fit["intercept"]),
        }
    Draft202012Validator(
        {"$ref": _DIAGNOSTIC_SCHEMA["$id"] + "#/$defs/slope_analysis"},
        registry=_DIAGNOSTIC_REGISTRY,
    ).validate(record)
    return record


def sweep_record(errors: Sequence[float]) -> list[dict[str, Any]]:
    """Encode the exact five R3 sweep points under plan section 5.4."""

    if len(errors) != len(SWEEP_H_VALUES):
        raise ValueError("the sweep record requires exactly five values")
    return [
        {"h": h, "symmetry_error": encode_float(error)}
        for h, error in zip(SWEEP_H_VALUES, errors, strict=True)
    ]


def _decision_result(row_number: int) -> dict[str, Any]:
    row = DECISION_TABLE_ROWS[row_number - 1]
    # Prereg v1.21 section 4 freezes the evaluator output to row + track only;
    # disposition remains part of the machine-readable table itself.
    return {"row": int(row["row"]), "track": str(row["track"])}


def evaluate_decision_table(
    instance: Mapping[str, Any], *, terminal_status: str, evidence_complete: bool
) -> dict[str, Any]:
    """Apply v1.21 section 4 rows 1--10 by mechanical first match."""

    rows = list(instance["per_node_diagnostics"])
    accepted = [row for row in rows if row["optimizer_accepted"] is True]
    if instance["purity"]["pass"] is not True:
        return _decision_result(1)
    if terminal_status != "COMPLETED" or evidence_complete is not True:
        return _decision_result(2)
    if any(row["optimizer_accepted"] is False for row in rows):
        return _decision_result(3)
    if any(
        (
            row["curvature_summary"]["retry_fired"]
            and row["curvature_summary"]["retry_positively_accepted"] is not True
        )
        or row["curvature_summary"][
            "nonstationarity_observed_any_evaluated_point"
        ]
        for row in accepted
    ):
        return _decision_result(4)
    if (
        instance["g1_battery"]["all_pass"] is not True
        or instance["g2_equivalence"]["all_pass"] is not True
        or instance["d23_sentinel"]["pass"] is not True
    ):
        return _decision_result(5)
    symmetry_failing = [
        row for row in accepted if row["raw_symmetry"]["symmetry_ok"] is False
    ]
    if not symmetry_failing:
        return _decision_result(6)
    if any(
        any(
            summary[key] is not True
            for key in (
                "spd_final",
                "rcond_ok_final",
                "directional_ok_final",
                "logdet_stable_final",
            )
        )
        for summary in (row["curvature_summary"] for row in accepted)
    ):
        return _decision_result(7)
    classifications = [row["slope_analysis"]["classification"] for row in accepted]
    failing_classifications = [
        row["slope_analysis"]["classification"] for row in symmetry_failing
    ]
    if (
        all(value != "UNDEFINED" for value in classifications)
        and all(value == "TRUNCATION_LIKE" for value in failing_classifications)
    ):
        return _decision_result(8)
    if (
        any(
            value in {"NOISE_LIKE", "FLAT", "UNDEFINED"}
            for value in failing_classifications
        )
        or any(value == "UNDEFINED" for value in classifications)
    ):
        return _decision_result(9)
    return _decision_result(10)


def canonical_bridge(
    g_storage: Callable[[np.ndarray], float],
    grad_storage: Callable[[np.ndarray], np.ndarray],
    perm: Sequence[int],
) -> tuple[Callable[[np.ndarray], float], Callable[[np.ndarray], np.ndarray]]:
    """Compose storage callables into canonical axes (v1.21 section 8)."""

    def g_canonical(u_canonical: np.ndarray) -> float:
        storage = vector_canonical_to_storage(
            np.asarray(u_canonical, dtype=np.float64), perm
        )
        return float(np.float64(g_storage(storage)))

    def grad_canonical(u_canonical: np.ndarray) -> np.ndarray:
        storage = vector_canonical_to_storage(
            np.asarray(u_canonical, dtype=np.float64), perm
        )
        gradient = np.asarray(grad_storage(storage), dtype=np.float64)
        return vector_storage_to_canonical(gradient, perm).astype(
            np.float64, copy=False
        )

    return g_canonical, grad_canonical


def _safe_repo_file(repo_root: Path, relpath: str, label: str) -> Path:
    if (
        not isinstance(relpath, str)
        or not relpath
        or Path(relpath).is_absolute()
        or ".." in Path(relpath).parts
    ):
        raise ValueError(f"{label} must be a safe repo-relative path")
    root = repo_root.resolve()
    path = (root / relpath).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{label} resolves outside repo_root") from exc
    if not path.is_file():
        raise ValueError(f"{label} is missing: {path}")
    return path


def _validate_parameters_header(parameters: Mapping[str, Any]) -> None:
    if parameters.get("kind") != "m2cr_diagnostic_protocol":
        raise ValueError("protocol parameters have the wrong kind")
    if parameters.get("schema_version") != 1:
        raise ValueError("protocol parameters have the wrong schema_version")
    if parameters.get("addendum") != "v1.21":
        raise ValueError("protocol parameters have the wrong addendum")


def build_protocol_manifest(repo_root: str | Path) -> dict[str, Any]:
    """Build the literal Layer-1b manifest (v1.21 section 6 / ballot C)."""

    root = Path(repo_root)
    schema_path = _safe_repo_file(
        root, DIAGNOSTIC_SCHEMA_RELPATH, "diagnostic record schema"
    )
    parameters_path = _safe_repo_file(
        root, PROTOCOL_PARAMETERS_RELPATH, "protocol parameters"
    )
    infra_path = _safe_repo_file(
        root, _INFRASTRUCTURE_MANIFEST_RELPATH, "infrastructure manifest"
    )
    parameters = _read_json_object(parameters_path)
    _validate_parameters_header(parameters)
    manifest = {
        "kind": "m2cr_protocol_manifest",
        "schema_version": 1,
        "addendum": "v1.21",
        "diagnostic_record_schema": {
            "path": DIAGNOSTIC_SCHEMA_RELPATH,
            "sha256": sha256_file(schema_path),
        },
        "protocol_parameters": {
            "path": PROTOCOL_PARAMETERS_RELPATH,
            "sha256": sha256_file(parameters_path),
        },
        "infrastructure_manifest_sha256": sha256_file(infra_path),
    }
    own_digest = canonical_sha256(manifest).encode("ascii")
    if own_digest in schema_path.read_bytes():
        raise ValueError("diagnostic schema contains the protocol manifest digest")
    return manifest


def verify_protocol_manifest(
    manifest_path: str | Path, repo_root: str | Path | None = None
) -> dict[str, Any]:
    """Verify Layer-1b pins, acyclicity, and the v1.20 static ceiling."""

    path = Path(manifest_path)
    root = Path(repo_root) if repo_root is not None else path.resolve().parents[2]
    errors: list[str] = []
    checks: dict[str, bool] = {}

    def check(name: str, condition: bool, detail: str) -> None:
        checks[name] = bool(condition)
        if not condition:
            errors.append(detail)

    try:
        manifest = _read_json_object(path)
    except (OSError, ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        return {"ok": False, "errors": [f"cannot read protocol manifest: {exc}"], "checks": checks}

    check(
        "manifest_key_set",
        set(manifest) == _MANIFEST_KEYS,
        f"protocol manifest must carry exactly {sorted(_MANIFEST_KEYS)}",
    )
    check(
        "kind",
        manifest.get("kind") == "m2cr_protocol_manifest",
        "protocol manifest has the wrong kind",
    )
    check(
        "schema_version",
        manifest.get("schema_version") == 1,
        "protocol manifest has the wrong schema_version",
    )
    check(
        "addendum",
        manifest.get("addendum") == "v1.21",
        "protocol manifest has the wrong addendum",
    )

    resolved_pins: dict[str, Path] = {}
    expected_relpaths = {
        "diagnostic_record_schema": DIAGNOSTIC_SCHEMA_RELPATH,
        "protocol_parameters": PROTOCOL_PARAMETERS_RELPATH,
    }
    for name, expected_relpath in expected_relpaths.items():
        pin = manifest.get(name)
        shape_ok = (
            isinstance(pin, Mapping)
            and set(pin) == _PIN_KEYS
            and isinstance(pin.get("path"), str)
            and isinstance(pin.get("sha256"), str)
            and _HEX64_RE.fullmatch(pin["sha256"]) is not None
        )
        check(
            f"{name}_shape",
            shape_ok,
            f"{name} must be exactly a path/lowercase-sha256 pin",
        )
        if not shape_ok:
            continue
        relpath_ok = pin["path"] == expected_relpath
        check(
            f"{name}_path",
            relpath_ok,
            f"{name} path must equal {expected_relpath}",
        )
        try:
            pinned_path = _safe_repo_file(root, pin["path"], name)
        except ValueError as exc:
            errors.append(str(exc))
            checks[f"{name}_digest"] = False
            continue
        resolved_pins[name] = pinned_path
        check(
            f"{name}_digest",
            sha256_file(pinned_path) == pin["sha256"],
            f"{name} digest does not match the pinned file",
        )

    infra_path: Path | None = None
    try:
        infra_path = _safe_repo_file(
            root, _INFRASTRUCTURE_MANIFEST_RELPATH, "infrastructure manifest"
        )
        infra_digest = sha256_file(infra_path)
        supplied_infra = manifest.get("infrastructure_manifest_sha256")
        infra_shape = (
            isinstance(supplied_infra, str)
            and _HEX64_RE.fullmatch(supplied_infra) is not None
        )
        check(
            "infrastructure_digest_shape",
            infra_shape,
            "infrastructure_manifest_sha256 must be lowercase hex-64",
        )
        check(
            "infrastructure_digest",
            infra_shape and supplied_infra == infra_digest,
            "infrastructure_manifest_sha256 does not match the committed manifest",
        )
    except ValueError as exc:
        errors.append(str(exc))
        checks["infrastructure_digest"] = False

    parameters_path = resolved_pins.get("protocol_parameters")
    if parameters_path is not None:
        try:
            parameters = _read_json_object(parameters_path)
            _validate_parameters_header(parameters)
        except (OSError, ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            errors.append(f"invalid protocol parameters: {exc}")
            checks["addendum_agreement"] = False
        else:
            agreement = manifest.get("addendum") == parameters.get("addendum") == "v1.21"
            check(
                "addendum_agreement",
                agreement,
                "manifest and parameters addenda do not agree at v1.21",
            )

    schema_path = resolved_pins.get("diagnostic_record_schema")
    try:
        own_digest = sha256_file(path).encode("ascii")
        acyclic = schema_path is not None and own_digest not in schema_path.read_bytes()
    except OSError as exc:
        errors.append(f"cannot perform protocol-manifest acyclicity check: {exc}")
        acyclic = False
    check(
        "acyclic",
        acyclic,
        "diagnostic schema contains the protocol manifest's own sha256",
    )

    if infra_path is not None:
        try:
            infra = _read_json_object(infra_path)
            artifacts = infra.get("artifacts")
            if not isinstance(artifacts, Mapping):
                raise ValueError("infrastructure manifest lacks artifacts")
            ceiling_pin = artifacts.get("evidence_ceilings")
            if not isinstance(ceiling_pin, Mapping) or set(ceiling_pin) != _PIN_KEYS:
                raise ValueError("infrastructure manifest has a malformed evidence_ceilings pin")
            ceiling_path = _safe_repo_file(
                root, ceiling_pin["path"], "evidence ceilings"
            )
            if sha256_file(ceiling_path) != ceiling_pin["sha256"]:
                raise ValueError("evidence ceilings digest does not match infrastructure pin")
            from bistar_gp.m2cr.environment_freeze import parse_evidence_ceilings

            ceiling = parse_evidence_ceilings(_read_json_object(ceiling_path))[
                "runtime_envelope_static_artifact_per_file_bytes"
            ]
            static_paths = [path]
            if schema_path is not None:
                static_paths.append(schema_path)
            if parameters_path is not None:
                static_paths.append(parameters_path)
            sizes_ok = len(static_paths) == 3 and all(
                item.stat().st_size <= ceiling for item in static_paths
            )
            check(
                "static_file_ceiling",
                sizes_ok,
                "one or more Layer-1b files exceed the authenticated static per-file ceiling",
            )
        except (OSError, ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            errors.append(f"cannot verify the static per-file ceiling: {exc}")
            checks["static_file_ceiling"] = False

    return {"ok": not errors, "errors": errors, "checks": checks}


def main(argv: Sequence[str] | None = None) -> int:
    """Generate the canonical Layer-1b manifest (v1.21 section 6)."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--generate", choices=("protocol-manifest",), required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    manifest = build_protocol_manifest(args.repo_root)
    atomic_write_canonical_json(args.out, manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
