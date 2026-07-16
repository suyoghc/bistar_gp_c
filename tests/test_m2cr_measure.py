"""Exact-byte and derived-label tests for B15(ii) R2 measurement."""

from __future__ import annotations

from pathlib import Path

import bistar_gp.m2cr.measure as measure
from bistar_gp.m2cr.serialization import canonical_dumps


def test_measure_file_returns_exact_bytes_for_known_content(tmp_path: Path):
    path = tmp_path / "bytes.bin"
    path.write_bytes(b"a\n\xff")
    assert measure.measure_file(path) == 3


def test_measure_manifest_streams_exact_bytes_entries_and_types(tmp_path: Path):
    entries = [
        {"artifact_type": "source", "relpath": "a.py"},
        {"artifact_type": "source", "relpath": "b.py"},
        {"artifact_type": "extension", "relpath": "c.so"},
    ]
    data = "".join(canonical_dumps(entry) + "\n" for entry in entries).encode()
    path = tmp_path / "manifest.jsonl"
    path.write_bytes(data)
    assert measure.measure_manifest(path) == {
        "bytes": len(data),
        "entries": 3,
        "counts_by_type": {"extension": 1, "source": 2},
    }


def test_event_and_record_canonical_byte_counts_are_exact():
    # Canonical {"a":1} is seven bytes; JSONL adds exactly one newline.
    assert measure.measure_event_bytes([{"a": 1}]) == 8
    assert measure.measure_event_bytes([{"b": 2}, {"a": 1}]) == 16
    assert measure.measure_record_bytes({"a": 1}) == 7
    assert measure.measure_record_bytes({"z": "x"}) == len(b'{"z":"x"}')


def test_bundle_projection_labels_measured_and_derived_figures():
    projection = measure.derive_bundle_projection(
        {
            "attestation_manifest": 100,
            "event_bytes": {"bytes": 7, "per_node": True},
            "per_node_record_per_node": 11,
            "stdout": 13,
        },
        node_count=3,
    )
    assert projection["node_count"] == {"count": 3, "derived": False}
    assert all(
        item["derived"] is False for item in projection["measured"].values()
    )
    assert projection["derived"]["event_bytes_all_nodes"] == {
        "bytes": 21,
        "derived": True,
        "basis": "measured.event_bytes.bytes * node_count",
    }
    assert projection["derived"]["per_node_record_per_node_all_nodes"][
        "bytes"
    ] == 33
    assert projection["derived"]["complete_bundle"]["bytes"] == 167
    for item in projection["derived"].values():
        assert item["derived"] is True
        assert isinstance(item["basis"], str) and item["basis"]


def test_bundle_projection_node_count_is_caller_parameterized():
    first = measure.derive_bundle_projection(
        {"event_per_node": {"bytes": 5, "per_node": True}}, node_count=2
    )
    second = measure.derive_bundle_projection(
        {"event_per_node": {"bytes": 5, "per_node": True}}, node_count=9
    )
    assert first["derived"]["complete_bundle"]["bytes"] == 10
    assert second["derived"]["complete_bundle"]["bytes"] == 45
    assert first["node_count"]["count"] == 2
    assert second["node_count"]["count"] == 9


def test_measure_module_exports_no_size_limit_constant():
    assert not [name for name in vars(measure) if "CEILING" in name.upper()]
