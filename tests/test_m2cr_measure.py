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


def test_evidence_size_report_figures_reproduce():
    """External audit F8: the report's measured-exemplar byte figures are
    reproducible from committed code, not free-floating numbers."""

    import io
    import numpy as np
    from scipy.optimize import OptimizeResult
    import bistar_gp.m2cr.gates_v2 as gates
    from bistar_gp.m2cr.events import EventSink
    from bistar_gp.m2cr.records import (
        build_two_start_optimizer_record,
        build_curvature_record,
        build_battery_record,
        build_warm_start_ref,
        build_per_node_record,
    )
    from bistar_gp.m2cr.coordinates import storage_to_canonical_permutation
    from bistar_gp.m2cr.serialization import canonical_bytes
    from bistar_gp.m2c_freeze import TOL_GRAD_ABS, TOL_GRAD_REL

    storage = ("S.outputscale", "S.base_kernel.lengthscale", "S.kernels.1.variance")
    perm = storage_to_canonical_permutation(storage)

    def quad(diag):
        A = np.diag(np.asarray(diag, dtype=np.float64))
        return (
            lambda u: -0.5 * float(np.asarray(u) @ A @ np.asarray(u)),
            lambda u: -(A @ np.asarray(u, dtype=np.float64)),
        )

    g, gr = quad([1.0, 4.0, 9.0])
    battery = build_battery_record(
        [
            {"role": r, "fd_step": 1e-5, "reference_value": v,
             "functional_value": v, "absolute_error": 0.0,
             "threshold": TOL_GRAD_ABS + TOL_GRAD_REL * 1.0, "pass": True}
            for r, v in zip(("ls", "os", "lv"), (0.1, -0.2, 0.05))
        ]
    )
    ref_in = build_warm_start_ref({"kind": "mode_u"}, [0.0, 0.0, 0.0], "initial_mode_u")
    ref_out = build_warm_start_ref(
        {"kind": "accepted_node", "stage_id": "level0", "node_index": 0},
        [0.0, 0.0, 0.0],
        "accepted_current_node",
    )

    # Clean accepted node (no restart, no retry).
    opt = gates.optimize_conditional_v2(
        lambda u: -g(u), lambda u: -gr(u), np.ones(3), -np.ones(3), perm=perm
    )
    cur = gates.curvature_gate_v2(g, gr, np.zeros(3), storage, perm=perm)
    clean = build_per_node_record(
        0, 0.1, storage, ref_in, ref_out,
        build_two_start_optimizer_record(opt, perm), True, [0.0, 0.0, 0.0],
        battery, build_curvature_record(cur, perm), stage_id="level0",
    )
    assert len(canonical_bytes(clean)) == 3179  # report figure

    failed_opt = build_two_start_optimizer_record(opt, perm)
    failed = build_per_node_record(
        1, 0.2, storage, ref_in, ref_in, failed_opt, False, None,
        stage_id="level0",
    )
    assert len(canonical_bytes(failed)) == 1613  # report figure


def test_evidence_size_report_fixed_total_matches_committed_artifacts():
    """External audit round-2 F8: the report's fixed-artifact total must equal
    the sum of the committed artifacts' actual byte sizes, so a regenerated
    artifact cannot leave the report stale."""

    import os
    import re
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    artifacts = [
        "m2cr_importable_artifact_manifest_v1.jsonl",
        "m2cr_dependency_lock_v1.json",
        "m2cr_preboundary_attestation_set_v1.json",
        "m2cr_infrastructure_manifest_v1.json",
        "m2cr_environment_freeze_manifest_v1.json",
        "m2cr_child_env_mapping_v1.json",
        "m2cr_interpreter_pin_v1.json",
        "m2cr_native_stack_expectations_v1.json",
    ]
    freeze = root / "docs/m2c_freeze"
    if not all((freeze / name).exists() for name in artifacts):
        import pytest

        pytest.skip("committed freeze artifacts absent (regeneration window)")
    total = sum(os.path.getsize(freeze / name) for name in artifacts)
    report = (root / "docs/m2cr-r2-evidence-size-report.md").read_text()
    stated = int(
        re.search(r"Fixed-artifact total:\s*\*\*([\d,]+) bytes", report)
        .group(1)
        .replace(",", "")
    )
    assert stated == total, f"report says {stated}, artifacts sum to {total}"
