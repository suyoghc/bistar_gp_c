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
    "RUN_DIR_EVIDENCE_CLASSES",
    "classify_run_dir_layout",
    "measure_run_dir_fixed_evidence",
]


def measure_file(path: str | os.PathLike[str]) -> int:
    """Return the exact number of bytes in one filesystem file."""

    return os.path.getsize(path)


def measure_manifest(path: str | os.PathLike[str]) -> dict[str, Any]:
    """Stream a JSONL artifact manifest and report exact bytes and classes.

    A first-line v2 header (``kind == "m2cr_importable_artifact_manifest"``)
    is counted in ``bytes`` but is not an entry.
    """

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
            if (
                line_number == 1
                and isinstance(entry, dict)
                and entry.get("kind") == "m2cr_importable_artifact_manifest"
            ):
                continue
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


_UNBOUNDED_STREAM_CLASSES = frozenset({"stdout", "stderr"})
_ALLOWANCE_BASIS = (
    "caller-supplied allowance for an unbounded stream; not a measured claim"
)


def _require_byte_count(name: str, value: Any, member: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"component {name!r} {member} must be an integer")
    if value < 0:
        raise ValueError(f"component {name!r} {member} cannot be negative")
    return value


def _per_node_spec(name: str, value: Any) -> tuple[int, str]:
    """Require an explicit measured worst-case: ``{"bytes", "worst_case"}``."""

    if not isinstance(value, Mapping) or set(value) != {"bytes", "worst_case"}:
        raise ValueError(
            f"per-node class {name!r} must be a mapping with exactly "
            "'bytes' and an explicit 'worst_case' label"
        )
    label = value["worst_case"]
    if not isinstance(label, str) or not label:
        raise ValueError(
            f"per-node class {name!r} worst_case label must be a non-empty string"
        )
    return _require_byte_count(name, value["bytes"], "bytes"), label


def derive_bundle_projection(
    per_node_classes: Mapping[str, Any],
    fixed_classes: Mapping[str, Any],
    node_count: int = 1481,
) -> dict[str, Any]:
    """Project a complete bundle from explicitly labeled component figures.

    Plan section 4.4 (B15(ii)) requires the complete-bundle figure to be
    *derived from measured components*, saying derived where it derives, and
    defines NO ceilings here.

    ``per_node_classes`` maps each per-node evidence class to
    ``{"bytes": N, "worst_case": label}``: the measured worst-case bytes of
    one node's record with an EXPLICIT label stating which worst case was
    measured.  ``fixed_classes`` maps run-scoped runtime files (prelaunch,
    spawned, marker, attestations, inventory, ...) to measured integer
    bytes -- except unbounded streams (``stdout``, ``stderr``), which must be
    declared as ``{"allowance_bytes": N}``: a caller-supplied allowance
    labeled as such, never a measured claim.  B7 supplies 1481 only as the
    default ``node_count`` input.

    Every measured figure is labeled ``derived: false``; every allowance is
    additionally labeled ``measured: false``; every projection or sum is
    labeled ``derived: true`` and carries its formula in ``basis``.
    """

    if isinstance(node_count, bool) or not isinstance(node_count, int):
        raise TypeError("node_count must be an integer")
    if node_count < 0:
        raise ValueError("node_count cannot be negative")
    per_node: dict[str, dict[str, Any]] = {}
    fixed: dict[str, dict[str, Any]] = {}
    allowances: dict[str, dict[str, Any]] = {}
    derived: dict[str, dict[str, Any]] = {}
    fixed_total = 0
    allowance_total = 0
    scaled_total = 0
    overlap = set(per_node_classes) & set(fixed_classes)
    if overlap:
        raise ValueError(
            "component classes appear in both per-node and fixed inputs: "
            + ", ".join(sorted(overlap))
        )
    for name in sorted(per_node_classes):
        byte_count, worst_case = _per_node_spec(name, per_node_classes[name])
        per_node[name] = {
            "bytes": byte_count,
            "derived": False,
            "scope": "per_node",
            "worst_case": worst_case,
        }
        projected = byte_count * node_count
        derived[f"{name}_all_nodes"] = {
            "bytes": projected,
            "derived": True,
            "basis": f"per_node.{name}.bytes * node_count",
        }
        scaled_total += projected
    for name in sorted(fixed_classes):
        value = fixed_classes[name]
        if isinstance(value, Mapping):
            if set(value) != {"allowance_bytes"}:
                raise ValueError(
                    f"fixed class {name!r} mapping must carry exactly "
                    "'allowance_bytes'"
                )
            byte_count = _require_byte_count(
                name, value["allowance_bytes"], "allowance_bytes"
            )
            allowances[name] = {
                "bytes": byte_count,
                "derived": False,
                "measured": False,
                "scope": "fixed",
                "caller_supplied_allowance": True,
                "basis": _ALLOWANCE_BASIS,
            }
            allowance_total += byte_count
            continue
        if name in _UNBOUNDED_STREAM_CLASSES:
            raise ValueError(
                f"fixed class {name!r} is an unbounded stream and must be "
                "declared as {'allowance_bytes': N}, never a measured claim"
            )
        byte_count = _require_byte_count(name, value, "bytes")
        fixed[name] = {"bytes": byte_count, "derived": False, "scope": "fixed"}
        fixed_total += byte_count
    derived["complete_bundle"] = {
        "bytes": fixed_total + allowance_total + scaled_total,
        "derived": True,
        "basis": (
            "sum(fixed measured bytes) + sum(caller-supplied allowance bytes) "
            "+ sum(per-node worst-case bytes * node_count)"
        ),
    }
    return {
        "node_count": {"count": node_count, "derived": False},
        "per_node": per_node,
        "fixed": fixed,
        "allowances": allowances,
        "derived": derived,
    }


# External-audit finding 5: every RUN_DIR_LAYOUT evidence class is classified
# EXPLICITLY here, with a reason, so a "complete bundle" figure cannot silently
# omit a component.  A class is exactly one of:
#   fixed_runtime    — a bounded one-shot runtime envelope file measured per run
#   per_event_stream — the event stream, scaled by node/event count (not fixed)
#   per_node_subtree — the nodes/ subtree, scaled per node (not fixed)
#   stream_allowance — an unbounded stream represented only as a labeled allowance
#   run_local_scratch — a writable run-local directory (HOME/TMPDIR/XDG) whose
#                       payload-written contents ARE Layer-3 raw-manifested, so
#                       represented as a caller-supplied allowance (unbounded, no
#                       hermetic basis), NEVER assumed to carry zero bytes
#   run_local_dir    — a run-local directory asserted empty (pycache prefix),
#                       genuinely zero certification bytes
#   conditional      — emitted only on a specific outcome (payload vs failure),
#                      measured as a fixed_runtime class when present
# The classification is validated to cover RUN_DIR_LAYOUT exactly (see
# classify_run_dir_layout), and the per-run evidence-bundle projection consumes
# the fixed_runtime + stream_allowance + per-event/per-node components — never
# only the static committed freeze artifacts, which are separate one-time storage.
RUN_DIR_EVIDENCE_CLASSES: dict[str, tuple[str, str]] = {
    "bootstrap_config.json": ("fixed_runtime", "consumed bootstrap config"),
    "prelaunch.json": ("fixed_runtime", "pre-fork launch provenance"),
    "spawned.json": ("fixed_runtime", "child hello confirmation"),
    "payload_started.json": ("fixed_runtime", "hash-bound payload marker"),
    "effect_proofs.json": ("fixed_runtime", "§4.5.8 effect proofs"),
    "stage_a.json": ("fixed_runtime", "Stage A path/env attestation"),
    "bytecode.json": ("fixed_runtime", "bytecode scan attestation"),
    "audit_canary.json": ("fixed_runtime", "audit-hook canary"),
    "stage_b_os.json": ("fixed_runtime", "Stage B os.environ baseline"),
    "stage_b_raw.json": ("fixed_runtime", "Stage B raw environ baseline"),
    "native_stack.json": ("fixed_runtime", "native-stack attestation"),
    "manifest_pre.json": ("fixed_runtime", "pre-import manifest re-walk"),
    "manifest_post.json": ("fixed_runtime", "post-execution manifest re-walk"),
    "sourceless.json": ("fixed_runtime", "sourceless-loader attestation"),
    "import_inventory.json": ("fixed_runtime", "import inventory + worktree hashes"),
    "stage_c.json": ("fixed_runtime", "Stage C re-attestation"),
    "payload.json": ("fixed_runtime", "protocol payload (present on a protocol exit)"),
    "bootstrap_failure.json": (
        "conditional",
        "child failure evidence; mutually exclusive with a clean payload exit",
    ),
    "RAW_MANIFEST.sha256": ("fixed_runtime", "Layer-3 raw manifest"),
    "terminal_record.json": ("fixed_runtime", "Layer-4 terminal record"),
    "events.jsonl": (
        "per_event_stream",
        "write-ahead event stream; scales with node/event count, not fixed",
    ),
    "stdout.txt": (
        "stream_allowance",
        "unbounded child stdout; represented only as a caller-supplied allowance",
    ),
    "stderr.txt": (
        "stream_allowance",
        "unbounded child stderr; represented only as a caller-supplied allowance",
    ),
    "nodes/": (
        "per_node_subtree",
        "per-node record subtree; scales per node, projected not fixed",
    ),
    "home/": (
        "run_local_scratch",
        "run-local HOME; any payload-written contents are Layer-3 raw-manifested "
        "and represented as a caller-supplied allowance, not zero bytes",
    ),
    "tmp/": (
        "run_local_scratch",
        "run-local TMPDIR (torch OpenMP may write here, §4.5.14); contents are "
        "Layer-3 raw-manifested and represented as a caller-supplied allowance",
    ),
    "xdg/": (
        "run_local_scratch",
        "run-local XDG base; any payload-written contents are Layer-3 "
        "raw-manifested and represented as a caller-supplied allowance",
    ),
    "pycache/": (
        "run_local_dir",
        "run-local pycache prefix; asserted empty at Stage C, zero certification "
        "bytes",
    ),
}

_RUN_DIR_EVIDENCE_CLASS_NAMES = frozenset(
    {
        "fixed_runtime",
        "per_event_stream",
        "per_node_subtree",
        "stream_allowance",
        "run_local_scratch",
        "run_local_dir",
        "conditional",
    }
)


def classify_run_dir_layout(run_dir_layout: Iterable[str]) -> dict[str, tuple[str, str]]:
    """Return the explicit (class, reason) for every RUN_DIR_LAYOUT member,
    failing closed if any member is unclassified or any classification is for a
    path not in the layout (external-audit finding 5).

    This is the completeness guard: a new run-directory evidence file cannot be
    added to RUN_DIR_LAYOUT without an explicit measurement classification and a
    reason, so the per-run evidence-bundle projection can never silently omit it.
    """

    layout = list(run_dir_layout)
    layout_set = set(layout)
    missing = sorted(name for name in layout_set if name not in RUN_DIR_EVIDENCE_CLASSES)
    if missing:
        raise ValueError(
            "RUN_DIR_LAYOUT members lack an explicit evidence classification: "
            + ", ".join(missing)
        )
    stray = sorted(name for name in RUN_DIR_EVIDENCE_CLASSES if name not in layout_set)
    if stray:
        raise ValueError(
            "evidence classification names paths absent from RUN_DIR_LAYOUT: "
            + ", ".join(stray)
        )
    for name, (klass, reason) in RUN_DIR_EVIDENCE_CLASSES.items():
        if klass not in _RUN_DIR_EVIDENCE_CLASS_NAMES:
            raise ValueError(f"unknown evidence class {klass!r} for {name!r}")
        if not isinstance(reason, str) or not reason:
            raise ValueError(f"evidence class for {name!r} lacks a reason")
    return {name: RUN_DIR_EVIDENCE_CLASSES[name] for name in layout}


def measure_run_dir_fixed_evidence(
    run_dir: str | os.PathLike[str],
) -> dict[str, int]:
    """Measure, from a real (hermetic) run directory, the exact bytes of every
    ``fixed_runtime``/``conditional`` evidence file that is present.

    Returns ``{relpath: bytes}`` for the bounded one-shot runtime envelope
    classes only; the event stream, node subtree, unbounded streams, and
    run-local scratch directories are excluded by class (they are projected or
    allowance-declared, not fixed).  Feeds :func:`derive_bundle_projection` as
    the ``fixed_classes`` runtime evidence, so the per-run bundle projection is
    derived from measured runtime components rather than the static freeze
    artifacts alone (external-audit finding 5).
    """

    root = os.fspath(run_dir)
    measured: dict[str, int] = {}
    for name, (klass, _reason) in RUN_DIR_EVIDENCE_CLASSES.items():
        if klass not in {"fixed_runtime", "conditional"}:
            continue
        path = os.path.join(root, name)
        if os.path.isfile(path):
            measured[name] = measure_file(path)
    return measured
