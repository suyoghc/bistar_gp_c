"""A1 launch authentication and diagnostic protocol-exit validation tests."""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

from bistar_gp.m2cr.capture import capture_run
from bistar_gp.m2cr.serialization import (
    atomic_write_canonical_json,
    sha256_file,
)
from tests.test_m2cr_capture import _make_launch


PROTOCOL_RELPATH = "docs/m2c_freeze/m2cr_protocol_manifest_v1.json"
SCHEMA_RELPATH = "docs/m2c_freeze/m2c_diagnostic_record.schema_v1.json"
PARAMETERS_RELPATH = "docs/m2c_freeze/m2cr_diagnostic_protocol_v1.json"


def _assert_pre_payload_failure(config) -> dict:
    record = capture_run(config)
    assert record["status"] == "INFRA_FAILURE"
    assert not (Path(config.run_dir) / "payload_started.json").exists()
    assert record["fault"]["payload_started"] is False
    return record


def _rewrite_protocol(config, mutator):
    path = Path(config.worktree_root) / PROTOCOL_RELPATH
    manifest = json.loads(path.read_text())
    mutator(manifest)
    atomic_write_canonical_json(path, manifest)
    return dataclasses.replace(
        config,
        chain={
            **config.chain,
            "protocol_manifest_sha256": sha256_file(path),
        },
    )


def test_correct_protocol_manifest_authenticates_and_launches(tmp_path: Path) -> None:
    config = _make_launch(tmp_path)
    record = capture_run(config)
    assert record["status"] == "COMPLETED", record.get("fault")
    assert record["not_a_result"] is True


def test_missing_protocol_manifest_fails_before_payload(tmp_path: Path) -> None:
    config = _make_launch(tmp_path)
    (Path(config.worktree_root) / PROTOCOL_RELPATH).unlink()
    record = _assert_pre_payload_failure(config)
    assert "protocol manifest not found" in record["fault"]["detail"]


def test_protocol_bytes_must_match_chain_digest(tmp_path: Path) -> None:
    config = _make_launch(tmp_path)
    path = Path(config.worktree_root) / PROTOCOL_RELPATH
    path.write_bytes(path.read_bytes() + b" ")
    record = _assert_pre_payload_failure(config)
    assert "authorized chain binding" in record["fault"]["detail"]


def test_protocol_must_reference_authenticated_infrastructure(tmp_path: Path) -> None:
    config = _make_launch(tmp_path)
    config = _rewrite_protocol(
        config,
        lambda manifest: manifest.update(
            infrastructure_manifest_sha256="0" * 64
        ),
    )
    record = _assert_pre_payload_failure(config)
    assert "authenticated infrastructure manifest" in record["fault"]["detail"]


@pytest.mark.parametrize("relpath", [SCHEMA_RELPATH, PARAMETERS_RELPATH])
def test_tampered_layer0_protocol_pin_fails_closed(
    tmp_path: Path, relpath: str
) -> None:
    config = _make_launch(tmp_path)
    path = Path(config.worktree_root) / relpath
    path.write_bytes(path.read_bytes() + b" ")
    record = _assert_pre_payload_failure(config)
    assert "sha256 does not match" in record["fault"]["detail"]


def test_protocol_manifest_wrong_addendum_value_fails_closed(
    tmp_path: Path,
) -> None:
    config = _make_launch(tmp_path)
    config = _rewrite_protocol(
        config, lambda manifest: manifest.update(addendum="v1.20")
    )
    record = _assert_pre_payload_failure(config)
    assert "wrong addendum" in record["fault"]["detail"]


@pytest.mark.parametrize("mutation", ["extra", "missing"])
def test_protocol_manifest_key_set_is_closed_world(
    tmp_path: Path, mutation: str
) -> None:
    config = _make_launch(tmp_path)

    def mutate(manifest):
        if mutation == "extra":
            manifest["extra"] = True
        else:
            manifest.pop("addendum")

    config = _rewrite_protocol(config, mutate)
    record = _assert_pre_payload_failure(config)
    assert "exactly the frozen Layer-1b key set" in record["fault"]["detail"]


def test_invalid_persisted_diagnostic_payload_maps_to_schema_fault(
    tmp_path: Path,
) -> None:
    config = _make_launch(tmp_path, mode="invalid_diagnostic_schema")
    record = capture_run(config)
    assert (Path(config.run_dir) / "payload_started.json").is_file()
    assert record["status"] == "INFRA_FAILURE"
    assert record["fault"]["fault_class"] == "schema_invalid_payload"
    assert "violates the R3 diagnostic-record schema" in record["fault"]["detail"]


def test_valid_persisted_diagnostic_payload_is_protocol_completion(
    tmp_path: Path,
) -> None:
    config = _make_launch(tmp_path)
    record = capture_run(config)
    assert record["status"] == "COMPLETED", record.get("fault")
    assert record["record_kind"] == "diagnostic"
    assert record["not_a_result"] is True


def test_result_kind_remains_governed_by_r1_result_payload(tmp_path: Path) -> None:
    diagnostic = _make_launch(tmp_path, mode="result")
    result_chain = {
        **diagnostic.chain,
        "diagnostic_record_sha256": "4" * 64,
        "amendment_manifest": "none",
    }
    config = dataclasses.replace(
        diagnostic, record_kind="result", chain=result_chain
    )
    record = capture_run(config)
    assert record["status"] == "COMPLETED", record.get("fault")
    assert record["record_kind"] == "result"
    assert "not_a_result" not in record
    assert record["result_payload"]["profile_band_masses"]["sum"] == 1.0
