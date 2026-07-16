"""Exact-byte and derived-label tests for B15(ii) R2 measurement."""

from __future__ import annotations

from pathlib import Path

import pytest

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


def test_measure_manifest_counts_v2_header_bytes_but_not_entries(tmp_path: Path):
    header = {
        "kind": "m2cr_importable_artifact_manifest",
        "schema_version": 2,
        "roots": {"stdlib": "/frozen/stdlib"},
    }
    entries = [{"artifact_type": "source", "relpath": "a.py"}]
    data = "".join(
        canonical_dumps(item) + "\n" for item in [header, *entries]
    ).encode()
    path = tmp_path / "v2.jsonl"
    path.write_bytes(data)
    assert measure.measure_manifest(path) == {
        "bytes": len(data),
        "entries": 1,
        "counts_by_type": {"source": 1},
    }


def test_event_and_record_canonical_byte_counts_are_exact():
    # Canonical {"a":1} is seven bytes; JSONL adds exactly one newline.
    assert measure.measure_event_bytes([{"a": 1}]) == 8
    assert measure.measure_event_bytes([{"b": 2}, {"a": 1}]) == 16
    assert measure.measure_record_bytes({"a": 1}) == 7
    assert measure.measure_record_bytes({"z": "x"}) == len(b'{"z":"x"}')


def test_bundle_projection_labels_measured_derived_and_allowances():
    projection = measure.derive_bundle_projection(
        {
            "node_record": {
                "bytes": 11,
                "worst_case": "max over rigged retry-fired per-node records",
            },
            "event_bytes": {
                "bytes": 7,
                "worst_case": "max canonical event line over rigged paths",
            },
        },
        {
            "prelaunch": 100,
            "spawned": 40,
            "payload_marker": 60,
            "attestations": 200,
            "import_inventory": 300,
            "stdout": {"allowance_bytes": 1000},
            "stderr": {"allowance_bytes": 500},
        },
        node_count=3,
    )
    assert projection["node_count"] == {"count": 3, "derived": False}
    assert projection["per_node"]["node_record"] == {
        "bytes": 11,
        "derived": False,
        "scope": "per_node",
        "worst_case": "max over rigged retry-fired per-node records",
    }
    assert projection["fixed"]["prelaunch"] == {
        "bytes": 100,
        "derived": False,
        "scope": "fixed",
    }
    stdout = projection["allowances"]["stdout"]
    assert stdout["bytes"] == 1000
    assert stdout["measured"] is False
    assert stdout["caller_supplied_allowance"] is True
    assert "not a measured claim" in stdout["basis"]
    assert projection["derived"]["node_record_all_nodes"] == {
        "bytes": 33,
        "derived": True,
        "basis": "per_node.node_record.bytes * node_count",
    }
    assert projection["derived"]["complete_bundle"]["bytes"] == (
        (100 + 40 + 60 + 200 + 300) + (1000 + 500) + 3 * (11 + 7)
    )
    for item in projection["derived"].values():
        assert item["derived"] is True
        assert isinstance(item["basis"], str) and item["basis"]


def test_bundle_projection_requires_explicit_worst_case_labels():
    with pytest.raises(ValueError, match="worst_case"):
        measure.derive_bundle_projection({"node_record": 5}, {}, node_count=1)
    with pytest.raises(ValueError, match="worst_case"):
        measure.derive_bundle_projection(
            {"node_record": {"bytes": 5}}, {}, node_count=1
        )
    with pytest.raises(ValueError, match="worst_case"):
        measure.derive_bundle_projection(
            {"node_record": {"bytes": 5, "worst_case": ""}}, {}, node_count=1
        )


def test_bundle_projection_rejects_measured_claims_for_unbounded_streams():
    with pytest.raises(ValueError, match="never a measured claim"):
        measure.derive_bundle_projection({}, {"stdout": 10}, node_count=1)
    with pytest.raises(ValueError, match="never a measured claim"):
        measure.derive_bundle_projection({}, {"stderr": 10}, node_count=1)


def test_bundle_projection_node_count_is_caller_parameterized():
    spec = {
        "event_bytes": {"bytes": 5, "worst_case": "hermetic measured maximum"}
    }
    first = measure.derive_bundle_projection(spec, {}, node_count=2)
    second = measure.derive_bundle_projection(spec, {}, node_count=9)
    assert first["derived"]["complete_bundle"]["bytes"] == 10
    assert second["derived"]["complete_bundle"]["bytes"] == 45
    assert first["node_count"]["count"] == 2
    assert second["node_count"]["count"] == 9


def test_measure_module_exports_no_size_limit_constant():
    assert not [name for name in vars(measure) if "CEILING" in name.upper()]
