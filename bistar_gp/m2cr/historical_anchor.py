"""Historical-anchor verifier for the RETIRED M2cR current-tree cascade (D54).

The four-manifest M2cR "current-tree" cascade (importable / environment-freeze /
infrastructure / protocol manifests) is reclassified as immutable historical
artifacts frozen at anchor commit ``76f3c39`` (= L2, the post-execution
certification freeze). This module verifies them by retrieving the pinned blobs
from that commit, never from the live working tree, so future working-tree edits
(for example the deferred A7 ``experiments/d19_bench.py`` rework) can never
desync the retired cascade.

Isolation (D54 ballot B, honestly scoped). This module's SOURCE imports only the
standard library and ``subprocess`` (for read-only ``git cat-file``); it imports
none of the capture, bootstrap, launch, audit, or scientific (torch / gpytorch /
pyro) modules, and none of those import it. Direct script execution and standalone
file-path loading in a fresh interpreter (the interface the D54 tests use, via
``importlib.util.spec_from_file_location`` / subprocess) load none of
``bistar_gp``, ``torch``, ``gpytorch``, ``pyro``, or the M2cR launch / bootstrap /
capture / audit modules.

An ORDINARY package-qualified import (``from bistar_gp.m2cr.historical_anchor
import ...``) first executes the pre-existing eager ``bistar_gp/__init__.py``,
which may load the scientific stack. That is existing package behaviour, not a
dependency introduced by this verifier, and changing it is outside D54. No claim
is made that every import spelling avoids the scientific stack — only the tested
standalone interface and the absence of dependency edges in either direction.

Adding this module changes no runtime verification default for any future fresh
arc: ``bistar_gp.m2cr.audit.verify_infrastructure_manifest`` and the capture /
bootstrap importable-drift walk keep their live-tree behaviour.

Four provenance classes are distinguished, each with the correct method:

  (i)   E3 execution freeze at ``367667f`` — the E3 env / infra / protocol
        members reproduce from that commit (plain file digests, verified) and
        are DISTINCT from the L2 cascade values. The v1.17 canonical hash is an
        algorithm hash, carried as attested and NOT recomputed here.
  (ii)  L2 cascade anchor at ``76f3c39`` — the four manifests, the infrastructure
        manifest's internal pins (12 R2 code modules + 8 artifact pins + 2 R1
        schema pins), and all 156 worktree-root importable entries verify against
        ``76f3c39`` blobs. Content verification reads NO live-tree bytes. The
        39,812 environment-root importable entries are labelled interpreter /
        external-pin attested and are NEVER git-verified (they are not
        reproducible from Git alone). A separate immutability guard reads the
        four retired manifest FILES from disk to catch any regeneration /
        overwrite of the immutable v1 artifacts.
  (iii) committed R4 ledger / evidence — the ledger is read read-only to confirm
        the R4 grant ``frozen_chain`` equals the E3 members (E3-bound), thereby
        distinguishing this provenance from the L2 cascade. Evidence integrity is
        deferred to the existing audit stack; nothing here re-hashes evidence or
        interprets ``payload.json``.
  (iv)  future live-tree manifests — out of scope. Any request to anchor a
        manifest other than the retired v1 cascade raises ``AnchorScopeError``;
        fresh arcs mint new versioned manifests with their own live-tree
        verification.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

__all__ = [
    "AnchorScopeError",
    "REPO_ROOT",
    "ANCHOR_RECORD_RELPATH",
    "LEDGER_RELPATH",
    "RETIRED_CASCADE_ROLES",
    "R4_GRANT_EVENT_ID",
    "R4_AUTHORIZATION_ID",
    "load_anchor_record",
    "assert_retired_scope",
    "verify_e3_execution_freeze",
    "verify_l2_cascade_content_at_anchor",
    "verify_v1_immutability",
    "verify_r4_ledger_e3_binding",
    "verify_all",
    "main",
]

REPO_ROOT = Path(__file__).resolve().parents[2]
ANCHOR_RECORD_RELPATH = "docs/m2c_freeze/m2cr_current_tree_anchor_v1.json"
LEDGER_RELPATH = "docs/m2c_freeze/m2c_authorization_ledger.jsonl"

RETIRED_CASCADE_ROLES = (
    "importable_artifact_manifest",
    "environment_freeze_manifest",
    "infrastructure_manifest",
    "protocol_manifest",
)

# The only importable-manifest roots that are attested against the frozen
# interpreter / external environment pins (NEVER git). Any other root is an error.
_KNOWN_ENVIRONMENT_ROOTS = frozenset({"stdlib", "site-packages", "lib-dynload"})

# The exact R4 diagnostic grant identity (class iii): the E3-bound one-shot grant
# consumed by the R4 execution. Pinned so a reshaped or different grant carrying
# the same fields cannot be accepted.
R4_GRANT_EVENT_ID = "m2cr-ev-000006"
R4_AUTHORIZATION_ID = "m2cr-auth-20260719-03"

_ANCHOR_RECORD_TOP_KEYS = {
    "kind",
    "schema_version",
    "anchor_commit",
    "e3_execution_commit",
    "retired_cascade",
    "e3_execution_chain",
    "importable_entry_classes",
    "provenance_classes",
    "lifecycle",
    "references",
}


class AnchorScopeError(ValueError):
    """Raised when the historical verifier is asked to anchor a manifest other
    than the retired v1 cascade (provenance class iv: future / live-tree
    manifests are out of scope for this module)."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_bytes(obj: Any) -> bytes:
    # Mirrors bistar_gp.m2cr.serialization.canonical_bytes WITHOUT importing it
    # (isolation): sorted keys, compact separators, allow_nan=False, UTF-8.
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _git_blob(repo_root: Path, commit: str, relpath: str) -> bytes | None:
    """Read-only blob retrieval at ``<commit>:<relpath>``.

    Returns ``None`` when the path does not exist at that commit (or git errors).
    Never reads the live working tree.
    """

    proc = subprocess.run(
        ["git", "cat-file", "blob", f"{commit}:{relpath}"],
        cwd=str(repo_root),
        capture_output=True,
    )
    if proc.returncode != 0:
        return None
    return proc.stdout


def load_anchor_record(
    repo_root: Path | str = REPO_ROOT,
) -> tuple[dict, list[str]]:
    """Load and structurally validate the committed anchor record.

    Stdlib-only structural checks (closed top-level key set, ``kind`` /
    ``schema_version``, canonical serialization). Full Draft-2020-12 schema
    validation is a test-side concern.
    """

    repo_root = Path(repo_root)
    raw = (repo_root / ANCHOR_RECORD_RELPATH).read_bytes()
    errors: list[str] = []
    record = json.loads(raw)
    if not isinstance(record, dict):
        raise AnchorScopeError("anchor record is not a JSON object")
    if set(record) != _ANCHOR_RECORD_TOP_KEYS:
        missing = sorted(_ANCHOR_RECORD_TOP_KEYS - set(record))
        extra = sorted(set(record) - _ANCHOR_RECORD_TOP_KEYS)
        errors.append(
            f"anchor record non-canonical key set (missing={missing}, extra={extra})"
        )
    if record.get("kind") != "m2cr_current_tree_anchor":
        errors.append("anchor record wrong kind")
    if record.get("schema_version") != 1:
        errors.append("anchor record wrong schema_version")
    if raw != _canonical_bytes(record):
        errors.append("anchor record is not in canonical serialization")
    return record, errors


def assert_retired_scope(manifest_paths: Any) -> None:
    """Class (iv) guard: refuse any manifest set other than the retired v1
    cascade. ``manifest_paths`` is the exact set of the four retired relpaths."""

    expected = {
        "docs/m2c_freeze/m2cr_importable_artifact_manifest_v1.jsonl",
        "docs/m2c_freeze/m2cr_environment_freeze_manifest_v1.json",
        "docs/m2c_freeze/m2cr_infrastructure_manifest_v1.json",
        "docs/m2c_freeze/m2cr_protocol_manifest_v1.json",
    }
    try:
        given = set(manifest_paths)
    except TypeError as exc:  # pragma: no cover - defensive
        raise AnchorScopeError("manifest scope is not iterable") from exc
    if given != expected:
        raise AnchorScopeError(
            "historical-anchor verifier only serves the retired v1 cascade; "
            "future / live-tree manifests are out of scope (provenance class iv)"
        )


def _verify_blob_pin(
    repo_root: Path,
    commit: str,
    label: str,
    relpath: Any,
    expected: Any,
    checks: list[dict],
    errors: list[str],
) -> None:
    """Verify ``sha256(<commit>:<relpath>) == expected`` (blob-only)."""

    if not isinstance(relpath, str) or not isinstance(expected, str):
        errors.append(f"{label}: malformed pin (path/sha256)")
        return
    blob = _git_blob(repo_root, commit, relpath)
    if blob is None:
        checks.append({"label": label, "relpath": relpath, "ok": False, "reason": "absent-at-commit"})
        errors.append(f"{label}: {relpath} absent at {commit[:12]}")
        return
    got = _sha256(blob)
    ok = got == expected
    checks.append({"label": label, "relpath": relpath, "ok": ok})
    if not ok:
        errors.append(f"{label}: {relpath} blob {got[:12]} != expected {expected[:12]}")


def verify_e3_execution_freeze(
    record: dict, repo_root: Path | str = REPO_ROOT
) -> dict:
    """Class (i): the E3 env / infra / protocol members reproduce from the E3
    execution commit and are DISTINCT from the L2 cascade values. The v1.17
    canonical hash is attested, NOT recomputed here."""

    repo_root = Path(repo_root)
    errors: list[str] = []
    checks: list[dict] = []
    e3 = record["e3_execution_commit"]
    chain = record["e3_execution_chain"]
    cascade = record["retired_cascade"]
    members = {
        "environment_freeze_manifest": (
            "docs/m2c_freeze/m2cr_environment_freeze_manifest_v1.json",
            chain.get("environment_freeze_manifest_sha256"),
        ),
        "infrastructure_manifest": (
            "docs/m2c_freeze/m2cr_infrastructure_manifest_v1.json",
            chain.get("infrastructure_manifest_sha256"),
        ),
        "protocol_manifest": (
            "docs/m2c_freeze/m2cr_protocol_manifest_v1.json",
            chain.get("protocol_manifest_sha256"),
        ),
    }
    for role, (relpath, expected) in members.items():
        _verify_blob_pin(repo_root, e3, f"e3:{role}", relpath, expected, checks, errors)
        l2_val = cascade.get(role, {}).get("sha256") if isinstance(cascade, dict) else None
        if isinstance(expected, str) and expected == l2_val:
            errors.append(f"e3:{role}: E3 value not distinct from the L2 cascade value")
    return {
        "ok": not errors,
        "errors": errors,
        "checks": checks,
        "v117_canonical_attested": chain.get("v117_canonical_sha256"),
        "v117_recomputed": False,
    }


def _verify_importable_worktree_entries(
    repo_root: Path, commit: str, manifest_bytes: bytes
) -> tuple[int, int, list[str]]:
    """Verify each worktree-root entry in an importable manifest against its blob
    at ``commit`` (blob-only): both sha256 AND size must match. Environment-root
    entries (``stdlib`` / ``site-packages`` / ``lib-dynload``) are COUNTED
    (interpreter-attested) but NEVER git-verified; any other root is an error.
    Returns ``(worktree_verified, environment_attested, errors)``."""

    errors: list[str] = []
    worktree_verified = 0
    env_attested = 0
    for line in manifest_bytes.decode("utf-8").splitlines()[1:]:  # skip v2 header
        if not line.strip():
            continue
        entry = json.loads(line)
        root = entry.get("root")
        if root == "worktree":
            relpath = entry.get("relpath")
            want = entry.get("sha256")
            size = entry.get("size")
            blob = _git_blob(repo_root, commit, relpath)
            if blob is None:
                errors.append(f"importable:worktree:{relpath}: absent at anchor")
            elif _sha256(blob) != want:
                errors.append(f"importable:worktree:{relpath}: blob != manifest sha256")
            elif len(blob) != size:
                errors.append(
                    f"importable:worktree:{relpath}: blob size {len(blob)} != manifest size {size}"
                )
            else:
                worktree_verified += 1
        elif root in _KNOWN_ENVIRONMENT_ROOTS:
            env_attested += 1  # interpreter / external-pin attested; NEVER git-verified
        else:
            errors.append(f"importable: entry with unrecognised root {root!r}")
    return worktree_verified, env_attested, errors


def verify_l2_cascade_content_at_anchor(
    record: dict, repo_root: Path | str = REPO_ROOT
) -> dict:
    """Class (ii) content verification, BLOB-ONLY (reads no live-tree bytes):
    the four manifests, the infrastructure manifest's internal pins, and all 156
    worktree-root importable entries verify against anchor-commit blobs. The
    environment-root importable entries are counted as interpreter-attested and
    are never git-verified."""

    repo_root = Path(repo_root)
    anchor = record["anchor_commit"]
    cascade = record["retired_cascade"]

    man_errors: list[str] = []
    man_checks: list[dict] = []
    relpaths: dict[str, str] = {}
    for role in RETIRED_CASCADE_ROLES:
        pin = cascade.get(role)
        if not isinstance(pin, dict) or set(pin) != {"path", "sha256"}:
            man_errors.append(f"retired_cascade:{role}: malformed pin")
            continue
        relpaths[role] = pin["path"]
        _verify_blob_pin(
            repo_root, anchor, f"manifest:{role}", pin["path"], pin["sha256"], man_checks, man_errors
        )

    infra_errors: list[str] = []
    infra_checks: list[dict] = []
    counts = {"code": 0, "artifacts": 0, "r1_schemas": 0}
    infra_relpath = relpaths.get("infrastructure_manifest")
    if infra_relpath:
        infra_blob = _git_blob(repo_root, anchor, infra_relpath)
        if infra_blob is None:
            infra_errors.append("infrastructure manifest absent at anchor")
        else:
            infra = json.loads(infra_blob)
            for stored_path, pin in sorted((infra.get("code") or {}).items()):
                counts["code"] += 1
                _verify_blob_pin(
                    repo_root, anchor, f"infra:code:{stored_path}", stored_path,
                    (pin or {}).get("sha256"), infra_checks, infra_errors,
                )
            for section in ("artifacts", "r1_schemas"):
                for name, pin in sorted((infra.get(section) or {}).items()):
                    counts[section] += 1
                    _verify_blob_pin(
                        repo_root, anchor, f"infra:{section}:{name}", (pin or {}).get("path"),
                        (pin or {}).get("sha256"), infra_checks, infra_errors,
                    )

    imp_errors: list[str] = []
    worktree_verified = 0
    env_attested = 0
    imp_relpath = relpaths.get("importable_artifact_manifest")
    if imp_relpath:
        imp_blob = _git_blob(repo_root, anchor, imp_relpath)
        if imp_blob is None:
            imp_errors.append("importable manifest absent at anchor")
        else:
            worktree_verified, env_attested, entry_errors = (
                _verify_importable_worktree_entries(repo_root, anchor, imp_blob)
            )
            imp_errors.extend(entry_errors)

    classes = record["importable_entry_classes"]
    if worktree_verified != classes.get("worktree_git_reproducible"):
        imp_errors.append(
            f"worktree entries git-verified {worktree_verified} != declared "
            f"{classes.get('worktree_git_reproducible')}"
        )
    if env_attested != classes.get("environment_interpreter_attested"):
        imp_errors.append(
            f"environment entries {env_attested} != declared "
            f"{classes.get('environment_interpreter_attested')}"
        )

    all_errors = man_errors + infra_errors + imp_errors
    return {
        "ok": not all_errors,
        "anchor_commit": anchor,
        "errors": all_errors,
        "manifests": {"ok": not man_errors, "errors": man_errors, "checks": man_checks, "checked": len(relpaths)},
        "infrastructure_internal_pins": {"ok": not infra_errors, "errors": infra_errors, "checks": infra_checks, **counts},
        "importable_worktree_entries": {
            "ok": not imp_errors,
            "errors": imp_errors,
            "git_verified": worktree_verified,
            "environment_interpreter_attested": env_attested,
            "environment_git_verified": 0,
        },
    }


def verify_v1_immutability(record: dict, repo_root: Path | str = REPO_ROOT) -> dict:
    """The four retired v1 manifest FILES on disk must equal their recorded (=
    anchor-blob) sha256. Detects any regeneration / overwrite of the immutable v1
    artifacts. This is the only routine that reads the retired v1 MANIFEST files
    from the live tree, and only those four files that must never change (never
    the 156 mutable worktree entries — those are verified against anchor blobs).
    ``load_anchor_record`` and ``verify_r4_ledger_e3_binding`` also read the live
    tree, but for their own distinct inputs (the anchor record and the ledger),
    not the retired manifests."""

    repo_root = Path(repo_root)
    cascade = record["retired_cascade"]
    errors: list[str] = []
    checked: dict[str, dict] = {}
    for role in RETIRED_CASCADE_ROLES:
        pin = cascade.get(role)
        if not isinstance(pin, dict) or set(pin) != {"path", "sha256"}:
            errors.append(f"retired_cascade:{role}: malformed pin")
            continue
        disk = repo_root / pin["path"]
        disk_h = _sha256(disk.read_bytes()) if disk.is_file() else None
        ok = disk_h == pin["sha256"]
        checked[role] = {"disk_sha256": disk_h, "matches": ok}
        if not ok:
            errors.append(
                f"immutability:{role}: on-disk {disk_h} != recorded {pin['sha256'][:12]} "
                "(retired v1 file must never be regenerated or overwritten)"
            )
    return {"ok": not errors, "errors": errors, "checked": checked}


def verify_r4_ledger_e3_binding(
    record: dict, repo_root: Path | str = REPO_ROOT
) -> dict:
    """Class (iii): confirm the committed ledger's R4 grant is E3-bound — its
    ``frozen_chain`` equals the E3 members — distinguishing the R4 ledger /
    evidence provenance from the L2 cascade. Evidence integrity is deferred to
    the existing audit stack; nothing here re-hashes evidence or interprets
    ``payload.json``."""

    repo_root = Path(repo_root)
    errors: list[str] = []
    e3 = record["e3_execution_commit"]
    chain = record["e3_execution_chain"]
    expected = {
        "execution_commit": e3,
        "environment_freeze_manifest_sha256": chain.get("environment_freeze_manifest_sha256"),
        "infrastructure_manifest_sha256": chain.get("infrastructure_manifest_sha256"),
        "protocol_manifest_sha256": chain.get("protocol_manifest_sha256"),
        "v117_canonical_sha256": chain.get("v117_canonical_sha256"),
    }
    ledger_path = repo_root / LEDGER_RELPATH
    grant = None
    for line in ledger_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        event = json.loads(line)
        # Pin the grant IDENTITY, so a reshaped or different grant carrying the
        # same fields cannot stand in for the real R4 one-shot grant.
        if (
            event.get("event") == "authorization_granted"
            and event.get("event_id") == R4_GRANT_EVENT_ID
        ):
            grant = event
            break
    if grant is None:
        errors.append(f"R4 grant {R4_GRANT_EVENT_ID} (authorization_granted) not found in ledger")
        return {"ok": False, "errors": errors, "grant_event_id": None, "authorization_id": None}
    if grant.get("authorization_id") != R4_AUTHORIZATION_ID:
        errors.append(
            f"R4 grant authorization_id {grant.get('authorization_id')} != {R4_AUTHORIZATION_ID}"
        )
    # EXACT frozen_chain equality (no extra or missing members), which also
    # enforces execution_commit == E3 and every E3 member.
    if grant.get("frozen_chain") != expected:
        errors.append(
            "R4 grant frozen_chain does not exactly equal the E3 members "
            "(environment / infrastructure / protocol / v117 / execution_commit)"
        )
    return {
        "ok": not errors,
        "errors": errors,
        "grant_event_id": grant.get("event_id"),
        "authorization_id": grant.get("authorization_id"),
    }


def verify_all(
    repo_root: Path | str = REPO_ROOT, manifest_scope: Any = None
) -> dict:
    """Run the full historical-anchor audit over the retired v1 cascade.

    ``manifest_scope`` must be ``None`` (the retired v1 cascade) or exactly the
    four retired relpaths; any other value is a provenance-class-(iv) future /
    live-tree request and raises ``AnchorScopeError``.
    """

    if manifest_scope is not None:
        assert_retired_scope(manifest_scope)
    record, record_errors = load_anchor_record(repo_root)
    e3 = verify_e3_execution_freeze(record, repo_root)
    l2_content = verify_l2_cascade_content_at_anchor(record, repo_root)
    immutability = verify_v1_immutability(record, repo_root)
    r4 = verify_r4_ledger_e3_binding(record, repo_root)
    ok = (
        not record_errors
        and e3["ok"]
        and l2_content["ok"]
        and immutability["ok"]
        and r4["ok"]
    )
    return {
        "ok": ok,
        "anchor_commit": record["anchor_commit"],
        "e3_execution_commit": record["e3_execution_commit"],
        "record_errors": record_errors,
        "e3_execution_freeze": e3,
        "l2_cascade_anchor": l2_content,
        "v1_immutability": immutability,
        "committed_r4_ledger_evidence": r4,
        "future_live_tree_manifests": {
            "in_scope": False,
            "note": (
                "out of scope; fresh arcs mint new versioned manifests with "
                "their own live-tree verification"
            ),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Verify the retired M2cR current-tree cascade against its historical "
            "Git anchor (read-only)."
        )
    )
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    args = parser.parse_args(argv)
    report = verify_all(Path(args.repo_root))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
