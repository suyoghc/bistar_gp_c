"""Exact byte measurement and explicitly labeled R2 bundle projections.

This module reports representation sizes only.  It intentionally defines no
limits: B15(ii) defers every evidence-size policy value to a later, separately
ratified pre-execution addendum.
"""

from __future__ import annotations

import json
import os
from collections import Counter
from collections.abc import Iterable, Mapping
from typing import Any

from bistar_gp.m2cr.serialization import canonical_dumps

__all__ = [
    "measure_file",
    "measure_manifest",
    "measure_event_bytes",
    "measure_record_bytes",
    "derive_bundle_projection",
]


def measure_file(path: str | os.PathLike[str]) -> int:
    """Return the exact number of bytes in one filesystem file."""

    return os.path.getsize(path)


def measure_manifest(path: str | os.PathLike[str]) -> dict[str, Any]:
    """Stream a JSONL artifact manifest and report exact bytes and classes."""

    total_bytes = 0
    entries = 0
    counts: Counter[str] = Counter()
    with open(path, "rb") as handle:
        for line_number, raw in enumerate(handle, start=1):
            total_bytes += len(raw)
            if not raw.strip():
                raise ValueError(f"manifest line {line_number} is blank")
            try:
                entry = json.loads(raw)
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise ValueError(
                    f"manifest line {line_number} is not valid UTF-8 JSON"
                ) from exc
            if not isinstance(entry, dict) or not isinstance(
                entry.get("artifact_type"), str
            ):
                raise ValueError(
                    f"manifest line {line_number} lacks string artifact_type"
                )
            entries += 1
            counts[entry["artifact_type"]] += 1
    return {
        "bytes": total_bytes,
        "entries": entries,
        "counts_by_type": dict(sorted(counts.items())),
    }


def measure_event_bytes(event_dicts: Iterable[Mapping[str, Any]]) -> int:
    """Measure canonical JSONL bytes, including one newline per event."""

    return sum(
        len((canonical_dumps(dict(event)) + "\n").encode("utf-8"))
        for event in event_dicts
    )


def measure_record_bytes(record_dict: Mapping[str, Any]) -> int:
    """Measure one canonical record exactly, with no trailing newline."""

    return len(canonical_dumps(dict(record_dict)).encode("utf-8"))


def _component_spec(name: str, value: Any) -> tuple[int, bool]:
    if isinstance(value, Mapping):
        if "bytes" not in value:
            raise ValueError(f"component {name!r} lacks bytes")
        byte_count = value["bytes"]
        per_node = bool(value.get("per_node", False))
    else:
        byte_count = value
        # This convenience convention remains labeling, not policy: callers
        # can use an explicit {bytes, per_node} mapping to avoid name inference.
        per_node = name.startswith("per_node_") or name.endswith("_per_node")
    if isinstance(byte_count, bool) or not isinstance(byte_count, int):
        raise TypeError(f"component {name!r} bytes must be an integer")
    if byte_count < 0:
        raise ValueError(f"component {name!r} bytes cannot be negative")
    return byte_count, per_node


def derive_bundle_projection(
    components: dict[str, Any], node_count: int = 1481
) -> dict[str, Any]:
    """Project a complete bundle from measured component byte figures.

    B7 supplies 1481 only as the default caller input; it is not hard-coded as
    scientific truth and may be replaced through ``node_count``.  A component
    may be an integer (fixed-size measured bytes) or
    ``{"bytes": N, "per_node": true}``.  Names beginning ``per_node_`` or
    ending ``_per_node`` are also treated as per-node for convenience.

    Every measured figure is labeled ``derived: false``.  Every multiplication
    or sum is labeled ``derived: true`` and carries its formula in ``basis``.
    """

    if isinstance(node_count, bool) or not isinstance(node_count, int):
        raise TypeError("node_count must be an integer")
    if node_count < 0:
        raise ValueError("node_count cannot be negative")
    measured: dict[str, dict[str, Any]] = {}
    derived: dict[str, dict[str, Any]] = {}
    fixed_total = 0
    scaled_total = 0
    for name in sorted(components):
        byte_count, per_node = _component_spec(name, components[name])
        measured[name] = {
            "bytes": byte_count,
            "derived": False,
            "scope": "per_node" if per_node else "fixed",
        }
        if per_node:
            projection_name = f"{name}_all_nodes"
            projected = byte_count * node_count
            derived[projection_name] = {
                "bytes": projected,
                "derived": True,
                "basis": f"measured.{name}.bytes * node_count",
            }
            scaled_total += projected
        else:
            fixed_total += byte_count
    derived["complete_bundle"] = {
        "bytes": fixed_total + scaled_total,
        "derived": True,
        "basis": (
            "sum(measured fixed-component bytes) + "
            "sum(measured per-node bytes * node_count)"
        ),
    }
    return {
        "node_count": {"count": node_count, "derived": False},
        "measured": measured,
        "derived": derived,
    }
