"""Hermetic Layer-1b protocol-manifest generation and verification tests."""

from __future__ import annotations

import copy
import json
import os
import shutil
from pathlib import Path

import pytest

from bistar_gp.m2cr.diagnostic import (
    DIAGNOSTIC_SCHEMA_RELPATH,
    PROTOCOL_MANIFEST_RELPATH,
    PROTOCOL_PARAMETERS_RELPATH,
    build_protocol_manifest,
    verify_protocol_manifest,
)
from bistar_gp.m2cr.serialization import (
    atomic_write_canonical_json,
    sha256_file,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
INFRA_RELPATH = "docs/m2c_freeze/m2cr_infrastructure_manifest_v1.json"
CEILINGS_RELPATH = "docs/m2c_freeze/m2cr_evidence_ceilings_v1.json"


@pytest.fixture
def protocol_tree(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "repo"
    for relpath in (
        DIAGNOSTIC_SCHEMA_RELPATH,
        PROTOCOL_PARAMETERS_RELPATH,
        INFRA_RELPATH,
        CEILINGS_RELPATH,
    ):
        destination = root / relpath
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO_ROOT / relpath, destination)
    manifest_path = root / PROTOCOL_MANIFEST_RELPATH
    atomic_write_canonical_json(manifest_path, build_protocol_manifest(root))
    return root, manifest_path


def _rewrite(path: Path, document: dict) -> None:
    atomic_write_canonical_json(path, document)


def test_build_verify_round_trip(protocol_tree) -> None:
    root, path = protocol_tree
    manifest = json.loads(path.read_text())
    assert set(manifest) == {
        "kind",
        "schema_version",
        "addendum",
        "diagnostic_record_schema",
        "protocol_parameters",
        "infrastructure_manifest_sha256",
    }
    result = verify_protocol_manifest(path, root)
    assert result["ok"] is True, result["errors"]


def test_committed_protocol_manifest_matches_tree_or_regeneration_window() -> None:
    path = REPO_ROOT / PROTOCOL_MANIFEST_RELPATH
    if not path.is_file():
        if os.environ.get("M2CR_ALLOW_MISSING_COMMITTED_MANIFEST") == "1":
            pytest.skip("R3 integration regeneration window")
        pytest.fail(f"committed protocol manifest is missing: {path}")
    result = verify_protocol_manifest(path, REPO_ROOT)
    assert result["ok"] is True, result["errors"]
    assert json.loads(path.read_text()) == build_protocol_manifest(REPO_ROOT)


@pytest.mark.parametrize(
    "mutator",
    [
        lambda manifest: manifest.update(extra=True),
        lambda manifest: manifest.pop("addendum"),
        lambda manifest: manifest.update(kind="wrong"),
        lambda manifest: manifest.update(schema_version=2),
        lambda manifest: manifest.update(addendum="v1.20"),
    ],
)
def test_closed_world_header_negatives(protocol_tree, mutator) -> None:
    root, path = protocol_tree
    manifest = json.loads(path.read_text())
    mutator(manifest)
    _rewrite(path, manifest)
    assert verify_protocol_manifest(path, root)["ok"] is False


def test_tampered_schema_pin_digest_fails(protocol_tree) -> None:
    root, path = protocol_tree
    (root / DIAGNOSTIC_SCHEMA_RELPATH).write_bytes(b"{}")
    result = verify_protocol_manifest(path, root)
    assert result["ok"] is False
    assert result["checks"]["diagnostic_record_schema_digest"] is False


def test_pin_path_must_be_frozen_relpath(protocol_tree) -> None:
    root, path = protocol_tree
    alternate = root / "docs/m2c_freeze/alternate-schema.json"
    shutil.copy2(root / DIAGNOSTIC_SCHEMA_RELPATH, alternate)
    manifest = json.loads(path.read_text())
    manifest["diagnostic_record_schema"] = {
        "path": "docs/m2c_freeze/alternate-schema.json",
        "sha256": sha256_file(alternate),
    }
    _rewrite(path, manifest)
    result = verify_protocol_manifest(path, root)
    assert result["checks"]["diagnostic_record_schema_path"] is False


def test_infrastructure_digest_mismatch_fails(protocol_tree) -> None:
    root, path = protocol_tree
    manifest = json.loads(path.read_text())
    manifest["infrastructure_manifest_sha256"] = "0" * 64
    _rewrite(path, manifest)
    result = verify_protocol_manifest(path, root)
    assert result["checks"]["infrastructure_digest"] is False


def test_static_ceiling_is_parsed_from_authenticated_artifact(protocol_tree) -> None:
    root, path = protocol_tree
    ceilings_path = root / CEILINGS_RELPATH
    ceilings = json.loads(ceilings_path.read_text())
    ceilings["ceilings"][
        "runtime_envelope_static_artifact_per_file_bytes"
    ] = 1
    _rewrite(ceilings_path, ceilings)
    infra_path = root / INFRA_RELPATH
    infra = json.loads(infra_path.read_text())
    infra["artifacts"]["evidence_ceilings"]["sha256"] = sha256_file(
        ceilings_path
    )
    _rewrite(infra_path, infra)
    _rewrite(path, build_protocol_manifest(root))
    result = verify_protocol_manifest(path, root)
    assert result["checks"]["static_file_ceiling"] is False


def test_self_hash_acyclicity_guard_detects_schema_reference(protocol_tree) -> None:
    root, path = protocol_tree
    own_digest = sha256_file(path)
    schema_path = root / DIAGNOSTIC_SCHEMA_RELPATH
    schema_path.write_bytes(schema_path.read_bytes() + own_digest.encode("ascii"))
    result = verify_protocol_manifest(path, root)
    assert result["checks"]["acyclic"] is False


def test_build_rejects_wrong_parameters_header(protocol_tree) -> None:
    root, _path = protocol_tree
    parameters_path = root / PROTOCOL_PARAMETERS_RELPATH
    parameters = json.loads(parameters_path.read_text())
    parameters["addendum"] = "v1.20"
    _rewrite(parameters_path, parameters)
    with pytest.raises(ValueError, match="wrong addendum"):
        build_protocol_manifest(root)
