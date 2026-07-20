"""D54 — historical-anchor verifier tests for the RETIRED M2cR v1 cascade.

The verifier is exercised ONLY through its isolated interface — standalone
file-path loading via ``importlib.util.spec_from_file_location`` (and subprocess
probes) — never a package-qualified ``from bistar_gp.m2cr.historical_anchor
import ...`` that would first execute the pre-existing eager
``bistar_gp/__init__.py``. See D54 and the module docstring for the honest
isolation scope.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
VERIFIER_PATH = ROOT / "bistar_gp/m2cr/historical_anchor.py"
ANCHOR_RECORD = ROOT / "docs/m2c_freeze/m2cr_current_tree_anchor_v1.json"
SCHEMA_PATH = ROOT / "docs/m2c_freeze/m2cr_current_tree_anchor.schema_v1.json"

ANCHOR_COMMIT = "76f3c39631d8724c45db5f0e679608bffde39bbe"
E3_COMMIT = "367667f77881469b47c901345015c72b70e2fc02"
BASE_MERGE = "5e0bbddc60042a096833f4b0bd437c1ffcc5c98e"

# Real anchor-blob sha256 + size of the direct A7 target and the full E3 chain members.
D19_BENCH_SHA_AT_ANCHOR = "d8a606fc885c91b8db20d64ee46de1b72a83ef183b89d620d52390d55c58f478"
D19_BENCH_SIZE_AT_ANCHOR = 12824
E3_ENV = "8b6795e58ce07c08be94ba9136edcf3f97431188eb57ac91e0a62b5aa76113bc"
E3_INFRA = "d8a3f302fc39b59a4210d65fefd10b67fce5a435245cd387bed952d120f7259d"
E3_PROTOCOL = "ace374a6d0b02eaf6321ac6b81d542ec532114235e166fac0190f499a0c179d2"
E3_V117 = "65381bc774e894dd9aaf2207cadd9cfa2f2735dafceff4bb39492086a9e522e2"


def _load_verifier():
    """Load the verifier STANDALONE (isolated interface): no ``bistar_gp``
    package import, so ``bistar_gp/__init__.py`` never runs."""

    spec = importlib.util.spec_from_file_location(
        "m2cr_historical_anchor_isolated", VERIFIER_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ha = _load_verifier()


def _record():
    record, errors = ha.load_anchor_record(ROOT)
    assert errors == [], errors
    return record


# ============================ POSITIVE ============================


def test_full_audit_passes_on_committed_cascade():
    report = ha.verify_all(ROOT)
    assert report["ok"], report
    assert report["record_errors"] == []

    e3 = report["e3_execution_freeze"]
    assert e3["ok"], e3["errors"]
    assert e3["v117_recomputed"] is False

    l2 = report["l2_cascade_anchor"]
    assert l2["ok"], l2["errors"]
    assert l2["manifests"]["ok"]
    ip = l2["infrastructure_internal_pins"]
    assert (ip["ok"], ip["code"], ip["artifacts"], ip["r1_schemas"]) == (True, 12, 8, 2)
    we = l2["importable_worktree_entries"]
    assert we["git_verified"] == 156
    assert we["environment_interpreter_attested"] == 39812
    assert we["environment_git_verified"] == 0

    assert report["v1_immutability"]["ok"]
    r4 = report["committed_r4_ledger_evidence"]
    assert r4["ok"], r4["errors"]
    assert r4["authorization_id"] == "m2cr-auth-20260719-03"
    assert r4["grant_event_id"] == "m2cr-ev-000006"
    assert report["future_live_tree_manifests"]["in_scope"] is False


def test_anchor_record_validates_against_committed_schema():
    schema = json.loads(SCHEMA_PATH.read_text())
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(json.loads(ANCHOR_RECORD.read_text()))


def test_record_hashes_equal_live_committed_manifests():
    for role, pin in _record()["retired_cascade"].items():
        disk = hashlib.sha256((ROOT / pin["path"]).read_bytes()).hexdigest()
        assert disk == pin["sha256"], role


def test_v1_files_byte_identical_to_anchor_blob():
    for role, pin in _record()["retired_cascade"].items():
        blob = subprocess.run(
            ["git", "cat-file", "blob", f"{ANCHOR_COMMIT}:{pin['path']}"],
            cwd=ROOT, capture_output=True, check=True,
        ).stdout
        assert hashlib.sha256(blob).hexdigest() == pin["sha256"], role


def test_e3_chain_reproduces_from_367667f_and_distinct_from_l2():
    report = ha.verify_e3_execution_freeze(_record(), ROOT)
    assert report["ok"], report["errors"]
    assert report["v117_recomputed"] is False
    assert report["v117_canonical_attested"] == E3_V117


def test_infrastructure_internal_pin_counts():
    report = ha.verify_l2_cascade_content_at_anchor(_record(), ROOT)
    ip = report["infrastructure_internal_pins"]
    assert ip["ok"]
    assert (ip["code"], ip["artifacts"], ip["r1_schemas"]) == (12, 8, 2)


# ==================== ROBUSTNESS (the direct A7 unblock) ====================


def test_dirtied_worktree_file_does_not_break_content_verification(tmp_path):
    """A dirtied on-disk copy of a tracked worktree entry (d19_bench.py) in a
    scratch checkout at the anchor does NOT change the anchored result, because
    worktree entries verify against 76f3c39 blobs, never the live tree. This is
    exactly the future-A7 edit the retirement must survive."""

    worktree = tmp_path / "wt"
    add = subprocess.run(
        ["git", "worktree", "add", "--detach", str(worktree), ANCHOR_COMMIT],
        cwd=ROOT, capture_output=True, text=True,
    )
    if add.returncode != 0:
        pytest.skip("git worktree unavailable: " + add.stderr)
    try:
        target = worktree / "experiments/d19_bench.py"
        target.write_text(target.read_text() + "\n# A7-style on-disk edit\n")
        report = ha.verify_l2_cascade_content_at_anchor(_record(), worktree)
        assert report["importable_worktree_entries"]["ok"], report["importable_worktree_entries"]["errors"]
        assert report["ok"], report["errors"]
    finally:
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(worktree)],
            cwd=ROOT, capture_output=True,
        )


# ============================ NEGATIVE ============================


def _manifest_bytes(*entries):
    header = '{"kind":"m2cr_importable_artifact_manifest","schema_version":2}'
    return ("\n".join([header, *[json.dumps(e) for e in entries]]) + "\n").encode("utf-8")


def test_n1_worktree_entry_hash_mismatch_fails():
    manifest = _manifest_bytes(
        {"root": "worktree", "relpath": "experiments/d19_bench.py", "sha256": "00" * 32, "size": 1}
    )
    verified, env, errors = ha._verify_importable_worktree_entries(ROOT, ANCHOR_COMMIT, manifest)
    assert verified == 0 and env == 0
    assert any("blob != manifest sha256" in e for e in errors)


def test_n2_worktree_entry_absent_at_anchor_fails():
    manifest = _manifest_bytes(
        {"root": "worktree", "relpath": "does/not/exist_at_anchor.py", "sha256": "00" * 32, "size": 1}
    )
    verified, env, errors = ha._verify_importable_worktree_entries(ROOT, ANCHOR_COMMIT, manifest)
    assert verified == 0
    assert any("absent at anchor" in e for e in errors)


def test_n3_manifest_tamper_fails_immutability(tmp_path):
    record = _record()
    for pin in record["retired_cascade"].values():
        dst = tmp_path / pin["path"]
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes((ROOT / pin["path"]).read_bytes())
    tampered = tmp_path / record["retired_cascade"]["protocol_manifest"]["path"]
    tampered.write_bytes(tampered.read_bytes() + b"\n")
    report = ha.verify_v1_immutability(record, tmp_path)
    assert not report["ok"]
    assert any("immutability:protocol_manifest" in e for e in report["errors"])


def test_n4_environment_entry_never_git_verified():
    manifest = _manifest_bytes(
        {"root": "worktree", "relpath": "experiments/d19_bench.py",
         "sha256": D19_BENCH_SHA_AT_ANCHOR, "size": D19_BENCH_SIZE_AT_ANCHOR},
        {"root": "site-packages", "relpath": "numpy/bogus_never_checked.py", "sha256": "ff" * 32, "size": 1},
    )
    verified, env, errors = ha._verify_importable_worktree_entries(ROOT, ANCHOR_COMMIT, manifest)
    assert verified == 1  # the worktree entry verified against its anchor blob (sha + size)
    assert env == 1  # the env entry counted, interpreter-attested
    assert errors == []  # the bogus env sha256 caused NO error (never git-verified)


def test_n4b_worktree_entry_size_mismatch_fails():
    manifest = _manifest_bytes(
        {"root": "worktree", "relpath": "experiments/d19_bench.py",
         "sha256": D19_BENCH_SHA_AT_ANCHOR, "size": D19_BENCH_SIZE_AT_ANCHOR + 1},
    )
    verified, env, errors = ha._verify_importable_worktree_entries(ROOT, ANCHOR_COMMIT, manifest)
    assert verified == 0
    assert any("blob size" in e for e in errors)


def test_n4c_unrecognised_root_is_an_error():
    manifest = _manifest_bytes(
        {"root": "not_a_real_root", "relpath": "whatever.py", "sha256": "00" * 32, "size": 1},
    )
    verified, env, errors = ha._verify_importable_worktree_entries(ROOT, ANCHOR_COMMIT, manifest)
    assert verified == 0 and env == 0
    assert any("unrecognised root" in e for e in errors)


def test_n5_wrong_anchor_commit_is_rejected():
    record = copy.deepcopy(_record())
    record["anchor_commit"] = E3_COMMIT  # the cascade values differ at E3 (specificity)
    report = ha.verify_l2_cascade_content_at_anchor(record, ROOT)
    assert not report["ok"]


def test_n6_e3_not_distinct_from_l2_is_flagged():
    record = copy.deepcopy(_record())
    record["e3_execution_chain"]["environment_freeze_manifest_sha256"] = (
        record["retired_cascade"]["environment_freeze_manifest"]["sha256"]
    )
    report = ha.verify_e3_execution_freeze(record, ROOT)
    assert not report["ok"]
    assert any("not distinct" in e for e in report["errors"])


def test_n7_schema_rejects_closed_world_violations():
    validator = Draft202012Validator(json.loads(SCHEMA_PATH.read_text()))
    base = json.loads(ANCHOR_RECORD.read_text())
    assert validator.is_valid(base)

    unknown = copy.deepcopy(base)
    unknown["surprise"] = 1
    assert not validator.is_valid(unknown)

    missing = copy.deepcopy(base)
    del missing["lifecycle"]
    assert not validator.is_valid(missing)

    wrong_kind = copy.deepcopy(base)
    wrong_kind["kind"] = "other"
    assert not validator.is_valid(wrong_kind)

    wrong_version = copy.deepcopy(base)
    wrong_version["schema_version"] = 2
    assert not validator.is_valid(wrong_version)

    nested_unknown = copy.deepcopy(base)
    nested_unknown["retired_cascade"]["surprise"] = {"path": "x", "sha256": "0" * 64}
    assert not validator.is_valid(nested_unknown)


def test_n7b_schema_rejects_well_formed_but_wrong_commit_path_hash():
    """Const-binding: a canonical record with a well-formed but WRONG anchor
    commit, retired path, manifest sha256, or E3 member does not validate."""
    validator = Draft202012Validator(json.loads(SCHEMA_PATH.read_text()))
    base = json.loads(ANCHOR_RECORD.read_text())

    wrong_anchor = copy.deepcopy(base)
    wrong_anchor["anchor_commit"] = "0" * 40  # well-formed 40-hex, wrong commit
    assert not validator.is_valid(wrong_anchor)

    wrong_e3 = copy.deepcopy(base)
    wrong_e3["e3_execution_commit"] = "1" * 40
    assert not validator.is_valid(wrong_e3)

    wrong_path = copy.deepcopy(base)
    wrong_path["retired_cascade"]["protocol_manifest"]["path"] = "docs/m2c_freeze/other.json"
    assert not validator.is_valid(wrong_path)

    wrong_manifest_hash = copy.deepcopy(base)
    wrong_manifest_hash["retired_cascade"]["importable_artifact_manifest"]["sha256"] = "0" * 64
    assert not validator.is_valid(wrong_manifest_hash)

    wrong_e3_member = copy.deepcopy(base)
    wrong_e3_member["e3_execution_chain"]["infrastructure_manifest_sha256"] = "0" * 64
    assert not validator.is_valid(wrong_e3_member)


def test_n7_loader_structural_rejection(tmp_path):
    (tmp_path / "docs/m2c_freeze").mkdir(parents=True)
    base = json.loads(ANCHOR_RECORD.read_text())
    base["kind"] = "wrong"
    # indented (non-canonical) write also trips the canonical-serialization check
    (tmp_path / ha.ANCHOR_RECORD_RELPATH).write_text(json.dumps(base, indent=2))
    record, errors = ha.load_anchor_record(tmp_path)
    assert any("wrong kind" in e for e in errors)
    assert any("canonical" in e for e in errors)


def test_n8_future_or_other_manifest_out_of_scope():
    with pytest.raises(ha.AnchorScopeError):
        ha.assert_retired_scope(["docs/m2c_freeze/some_future_manifest_v2.json"])
    with pytest.raises(ha.AnchorScopeError):
        ha.verify_all(ROOT, manifest_scope=["docs/m2c_freeze/some_future_manifest_v2.json"])


def _write_ledger(tmp_path, grant):
    (tmp_path / "docs/m2c_freeze").mkdir(parents=True, exist_ok=True)
    (tmp_path / ha.LEDGER_RELPATH).write_text(json.dumps(grant) + "\n")


def test_n9_right_identity_wrong_frozen_chain_is_flagged(tmp_path):
    # The real R4 grant identity but a tampered frozen_chain (wrong env member).
    grant = {
        "event": "authorization_granted",
        "event_id": ha.R4_GRANT_EVENT_ID,
        "authorization_id": ha.R4_AUTHORIZATION_ID,
        "frozen_chain": {
            "execution_commit": E3_COMMIT,
            "environment_freeze_manifest_sha256": "00" * 32,  # WRONG
            "infrastructure_manifest_sha256": E3_INFRA,
            "protocol_manifest_sha256": E3_PROTOCOL,
            "v117_canonical_sha256": E3_V117,
        },
    }
    _write_ledger(tmp_path, grant)
    report = ha.verify_r4_ledger_e3_binding(_record(), tmp_path)
    assert not report["ok"]
    assert any("does not exactly equal" in e for e in report["errors"])


def test_n9b_wrong_grant_identity_with_correct_chain_is_not_accepted(tmp_path):
    # A DIFFERENT grant carrying the exact correct frozen_chain must not stand in
    # for the pinned R4 grant m2cr-ev-000006 / m2cr-auth-20260719-03.
    grant = {
        "event": "authorization_granted",
        "event_id": "m2cr-ev-999999",
        "authorization_id": "m2cr-auth-impostor",
        "frozen_chain": {
            "execution_commit": E3_COMMIT,
            "environment_freeze_manifest_sha256": E3_ENV,
            "infrastructure_manifest_sha256": E3_INFRA,
            "protocol_manifest_sha256": E3_PROTOCOL,
            "v117_canonical_sha256": E3_V117,
        },
    }
    _write_ledger(tmp_path, grant)
    report = ha.verify_r4_ledger_e3_binding(_record(), tmp_path)
    assert not report["ok"]
    assert any("not found" in e for e in report["errors"])


def test_n9c_extra_frozen_chain_member_is_flagged(tmp_path):
    # Full equality: a reshaped frozen_chain with an EXTRA member is rejected.
    grant = {
        "event": "authorization_granted",
        "event_id": ha.R4_GRANT_EVENT_ID,
        "authorization_id": ha.R4_AUTHORIZATION_ID,
        "frozen_chain": {
            "execution_commit": E3_COMMIT,
            "environment_freeze_manifest_sha256": E3_ENV,
            "infrastructure_manifest_sha256": E3_INFRA,
            "protocol_manifest_sha256": E3_PROTOCOL,
            "v117_canonical_sha256": E3_V117,
            "surprise_member": "deadbeef",
        },
    }
    _write_ledger(tmp_path, grant)
    report = ha.verify_r4_ledger_e3_binding(_record(), tmp_path)
    assert not report["ok"]
    assert any("does not exactly equal" in e for e in report["errors"])


def test_n10_standalone_load_pulls_no_scientific_stack():
    code = "\n".join([
        "import importlib.util, sys",
        f"spec = importlib.util.spec_from_file_location('_ha', {str(VERIFIER_PATH)!r})",
        "m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)",
        "roots = {x.split('.')[0] for x in sys.modules}",
        "forbidden = {'bistar_gp', 'torch', 'gpytorch', 'pyro'}",
        "m2cr = [x for x in sys.modules if x.startswith('bistar_gp.m2cr')]",
        "print(repr({'leaked': sorted(forbidden & roots), 'm2cr': m2cr}))",
    ])
    result = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    parsed = ast.literal_eval(result.stdout.strip().splitlines()[-1])
    assert parsed["leaked"] == [], parsed
    assert parsed["m2cr"] == [], parsed


def test_n10_direct_script_execution_pulls_no_scientific_stack():
    code = "\n".join([
        "import runpy, sys, io, contextlib",
        f"sys.argv = ['historical_anchor', '--repo-root', {str(ROOT)!r}]",
        "buf = io.StringIO()",
        "with contextlib.redirect_stdout(buf):",
        "    try:",
        f"        runpy.run_path({str(VERIFIER_PATH)!r}, run_name='__main__')",
        "    except SystemExit:",
        "        pass",
        "roots = {x.split('.')[0] for x in sys.modules}",
        "print(repr(sorted({'bistar_gp', 'torch', 'gpytorch', 'pyro'} & roots)))",
    ])
    result = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert ast.literal_eval(result.stdout.strip().splitlines()[-1]) == []


def test_n10_source_imports_are_stdlib_only():
    modules: set[str] = set()
    for node in ast.walk(ast.parse(VERIFIER_PATH.read_text())):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            modules.add(node.module.split(".")[0])
    forbidden = {"bistar_gp", "torch", "gpytorch", "pyro"}
    assert not (modules & forbidden), modules
    for name in modules:
        assert name in sys.stdlib_module_names, name


def test_n10_no_reverse_import_from_launch_bootstrap_capture_audit():
    for path in (ROOT / "bistar_gp/m2cr").glob("*.py"):
        if path.name == "historical_anchor.py":
            continue
        assert "historical_anchor" not in path.read_text(), path.name


def test_n11_runtime_verification_defaults_byte_unchanged():
    """No pre-existing R2 infrastructure module (audit / capture / bootstrap /
    environment_freeze / …) changed vs the PR #20 base merge; only the new
    historical_anchor.py is added. The fresh-builder live-tree tests in
    test_m2cr_infrastructure_manifest.py remain unchanged and continue to
    exercise verify_infrastructure_manifest's live-tree resolution."""

    diff = subprocess.run(
        ["git", "diff", "--name-only", BASE_MERGE, "--", "bistar_gp/m2cr/"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert diff.returncode == 0, diff.stderr
    changed = [
        line for line in diff.stdout.splitlines()
        if line.strip() and line != "bistar_gp/m2cr/historical_anchor.py"
    ]
    assert changed == [], f"pre-existing R2 modules changed: {changed}"
