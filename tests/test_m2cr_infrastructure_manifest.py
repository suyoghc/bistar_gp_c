"""Standing manifest==tree CI for the acyclic M2cR Layer-1a manifest."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pytest

from bistar_gp.m2cr.audit import verify_infrastructure_manifest
from bistar_gp.m2cr.environment_freeze import (
    R1_SCHEMA_RELPATHS,
    R2_CODE_RELPATHS,
    build_infrastructure_manifest,
)
from bistar_gp.m2cr.serialization import atomic_write_canonical_json


ROOT = Path(__file__).resolve().parents[1]
COMMITTED_MANIFEST = ROOT / "docs/m2c_freeze/m2cr_infrastructure_manifest_v1.json"


def _inputs(tmp_path: Path):
    code = {
        relpath: ROOT / relpath
        for relpath in R2_CODE_RELPATHS
        if (ROOT / relpath).is_file()
    }
    artifact_names = (
        "child_env_mapping",
        "importable_artifact_manifest",
        "interpreter_pin",
        "preboundary_attestation_set",
        "environment_freeze_manifest",
        "dependency_lock",
    )
    artifacts = {}
    for name in artifact_names:
        path = tmp_path / "artifacts" / f"{name}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((name + "\n").encode("utf-8"))
        artifacts[name] = path
    r1_schemas = {
        "execution_record": ROOT / R1_SCHEMA_RELPATHS[0],
        "authorization_ledger": ROOT / R1_SCHEMA_RELPATHS[1],
    }
    return {"code": code, "artifacts": artifacts, "r1_schemas": r1_schemas}


def test_generated_manifest_matches_tree_and_detects_copied_tree_tamper(
    tmp_path: Path,
):
    inputs = _inputs(tmp_path)
    manifest = build_infrastructure_manifest(inputs, repo_root=ROOT)
    manifest_path = tmp_path / "manifest.json"
    atomic_write_canonical_json(manifest_path, manifest)
    assert verify_infrastructure_manifest(manifest_path, repo_root=ROOT)["ok"]

    # Repo-contained pins are stored repo-relative (fix A9), so a detached
    # copy of the pinned tree audits its own copy, never this checkout.
    copy_root = tmp_path / "copy"
    relative_pins = list(manifest["code"]) + [
        pin["path"]
        for pin in manifest["r1_schemas"].values()
        if not Path(pin["path"]).is_absolute()
    ]
    for relpath in relative_pins:
        destination = copy_root / relpath
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relpath, destination)
    copied_manifest = copy_root / "manifest.json"
    shutil.copyfile(manifest_path, copied_manifest)
    first_code_path = next(iter(sorted(manifest["code"])))
    tampered = copy_root / first_code_path
    tampered.write_bytes(tampered.read_bytes() + b"\n# tampered copy\n")
    report = verify_infrastructure_manifest(copied_manifest)
    assert not report["ok"]
    assert any("sha256 mismatch" in error for error in report["errors"])


def test_manifest_has_both_r1_schema_pins_and_no_r3_diagnostic_schema(
    tmp_path: Path,
):
    manifest = build_infrastructure_manifest(_inputs(tmp_path))
    assert set(manifest["r1_schemas"]) == {
        "execution_record",
        "authorization_ledger",
    }
    assert manifest["r1_schemas"]["execution_record"]["path"].endswith(
        "m2c_execution_record.schema_v1.json"
    )
    assert manifest["r1_schemas"]["authorization_ledger"]["path"].endswith(
        "m2c_authorization_ledger.schema_v1.json"
    )
    assert "m2c_diagnostic_record" not in json.dumps(manifest, sort_keys=True)


@pytest.mark.parametrize("category", ["code", "artifacts", "r1_schemas"])
@pytest.mark.parametrize("mutation", ["missing", "extra"])
def test_builder_rejects_nonexact_required_key_sets(
    tmp_path: Path,
    category: str,
    mutation: str,
):
    inputs = _inputs(tmp_path)
    values = dict(inputs[category])
    if mutation == "missing":
        values.pop(next(iter(values)))
    else:
        extra = tmp_path / f"extra-{category}.json"
        extra.write_text("extra", encoding="utf-8")
        values["unexpected_alias"] = extra
    inputs[category] = values
    with pytest.raises(ValueError, match="must contain exactly"):
        build_infrastructure_manifest(inputs)


def test_builder_rejects_r3_schema_as_an_expected_pin_path(tmp_path: Path):
    inputs = _inputs(tmp_path)
    r3 = tmp_path / "m2c_diagnostic_record.schema_v1.json"
    r3.write_text("{}", encoding="utf-8")
    inputs["artifacts"]["dependency_lock"] = r3
    with pytest.raises(ValueError, match="R3 diagnostic schema"):
        build_infrastructure_manifest(inputs)


def test_verifier_rejects_nonexact_key_sets_and_malformed_pins(tmp_path: Path):
    manifest = build_infrastructure_manifest(_inputs(tmp_path), repo_root=ROOT)
    manifest["artifacts"]["unexpected_alias"] = manifest["artifacts"][
        "dependency_lock"
    ]
    manifest["code"][R2_CODE_RELPATHS[0]]["path"] = R2_CODE_RELPATHS[0]
    manifest_path = tmp_path / "malformed.json"
    atomic_write_canonical_json(manifest_path, manifest)
    report = verify_infrastructure_manifest(manifest_path, repo_root=ROOT)
    assert not report["ok"]
    assert any("exact required key set" in error for error in report["errors"])
    assert any("malformed pin" in error for error in report["errors"])


def test_no_pinned_digest_occurs_inside_the_file_it_pins(tmp_path: Path):
    inputs = _inputs(tmp_path)
    manifest = build_infrastructure_manifest(inputs, repo_root=ROOT)
    for relpath, pin in manifest["code"].items():
        assert pin["sha256"].encode("ascii") not in (ROOT / relpath).read_bytes()
    for category in ("artifacts", "r1_schemas"):
        for pin in manifest[category].values():
            pin_path = Path(pin["path"])
            if not pin_path.is_absolute():
                pin_path = ROOT / pin_path
            assert pin["sha256"].encode("ascii") not in pin_path.read_bytes()


def test_committed_infrastructure_manifest_matches_tree():
    if os.environ.get("M2CR_ALLOW_MISSING_COMMITTED_MANIFEST") == "1":
        pytest.skip(
            "orchestrator regeneration window: the committed manifest is being "
            "regenerated and its content check is deferred to the orchestrator"
        )
    if not COMMITTED_MANIFEST.exists():
        pytest.fail(
            "committed R2 infrastructure manifest is missing; only the generation "
            "orchestrator may set M2CR_ALLOW_MISSING_COMMITTED_MANIFEST=1"
        )
    report = verify_infrastructure_manifest(COMMITTED_MANIFEST)
    assert report["ok"], report["errors"]
