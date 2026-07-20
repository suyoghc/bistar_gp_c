"""Standing manifest==tree CI for the acyclic M2cR Layer-1a manifest."""

from __future__ import annotations

import importlib.util
import json
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

# D54: the committed v1 cascade is RETIRED — its two former live-tree standing
# checks now verify against the historical Git anchor 76f3c39, never the live
# working tree. The historical-anchor verifier is loaded through its ISOLATED
# interface (standalone file path), never a package-qualified import that would
# execute the pre-existing eager bistar_gp/__init__.py.
_VERIFIER_PATH = ROOT / "bistar_gp/m2cr/historical_anchor.py"


def _load_historical_anchor():
    spec = importlib.util.spec_from_file_location(
        "m2cr_historical_anchor_isolated_infra", _VERIFIER_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_HA = _load_historical_anchor()


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
        "native_stack_expectations",
        "evidence_ceilings",
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


def test_retired_infrastructure_manifest_verifies_at_historical_anchor():
    """RETIRED (D54): the committed infrastructure manifest's internal pins (12
    R2 code modules + 8 artifact pins + 2 R1 schema pins) verify against the
    historical anchor 76f3c39, NOT the live working tree, so future edits to the
    retired tree never desync it. Replaces the former live-tree
    ``verify_infrastructure_manifest(COMMITTED_MANIFEST)`` check; the
    ``M2CR_ALLOW_MISSING_COMMITTED_MANIFEST`` regeneration-window bypass is gone
    because an immutable historical artifact is never regenerated. The fresh-arc
    ``verify_infrastructure_manifest`` live-tree default is preserved and still
    exercised by the fresh-builder tests above."""

    record, record_errors = _HA.load_anchor_record(ROOT)
    assert record_errors == [], record_errors
    report = _HA.verify_l2_cascade_content_at_anchor(record, ROOT)
    assert report["manifests"]["ok"], report["manifests"]["errors"]
    pins = report["infrastructure_internal_pins"]
    assert pins["ok"], pins["errors"]
    assert (pins["code"], pins["artifacts"], pins["r1_schemas"]) == (12, 8, 2)


def test_retired_importable_manifest_worktree_entries_verify_at_historical_anchor():
    """RETIRED (D54): the committed importable manifest's 156 WORKTREE entries
    verify against their 76f3c39 blobs, NOT the live on-disk source.

    This is the direct blocker for the future A7 ``experiments/d19_bench.py``
    rework: after retirement a live-tree edit to any worktree entry cannot break
    this check (demonstrated by the robustness test in
    tests/test_m2cr_historical_anchor.py). The 39,812 environment-root entries
    stay interpreter-attested and are never git-verified. Replaces the former
    live-tree cross-walk (which read every worktree entry off disk); the
    ``M2CR_ALLOW_MISSING_COMMITTED_MANIFEST`` regeneration-window bypass is gone
    because an immutable historical artifact is never regenerated."""

    record, record_errors = _HA.load_anchor_record(ROOT)
    assert record_errors == [], record_errors
    report = _HA.verify_l2_cascade_content_at_anchor(record, ROOT)
    entries = report["importable_worktree_entries"]
    assert entries["ok"], entries["errors"]
    assert entries["git_verified"] == 156
    assert entries["environment_interpreter_attested"] == 39812
    assert entries["environment_git_verified"] == 0


def test_child_and_generator_loader_maps_stay_in_sync():
    """The child's restated loader map (bootstrap._LOADER_BY_ARTIFACT_TYPE, a
    deliberate verbatim copy so the child can validate before its sys.path is
    replaced) must never drift from the generator's authority
    (environment_freeze.LOADER_BY_ARTIFACT_TYPE), and must cover every artifact
    type the child accepts (three-reviewer gate round-4 NOTE)."""

    from bistar_gp.m2cr.bootstrap import (
        _ARTIFACT_TYPES,
        _LOADER_BY_ARTIFACT_TYPE,
    )
    from bistar_gp.m2cr.environment_freeze import LOADER_BY_ARTIFACT_TYPE

    assert _LOADER_BY_ARTIFACT_TYPE == dict(LOADER_BY_ARTIFACT_TYPE)
    # Every accepted artifact type has a frozen loader, so the parse-time
    # consistency check never falls through to a None comparison.
    assert set(_ARTIFACT_TYPES) == set(_LOADER_BY_ARTIFACT_TYPE)
