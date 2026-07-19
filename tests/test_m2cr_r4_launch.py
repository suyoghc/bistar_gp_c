"""Hermetic tests for the D51 generic production launch vehicle."""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Callable

import pytest

import bistar_gp.m2cr.capture as capture_module
import bistar_gp.m2cr.r4_launch as r4_launch
from bistar_gp.m2cr.audit import validate_ledger
from bistar_gp.m2cr.capture import (
    V117_CANONICAL_SHA256,
    WALL_CLOCK_CEILING_HOURS,
    TerminalPublicationError,
)
from bistar_gp.m2cr.serialization import (
    canonical_bytes,
    canonical_dumps,
    sha256_bytes,
    sha256_file,
)


ROOT = Path(__file__).resolve().parents[1]
REAL_SCHEMA = ROOT / r4_launch.LEDGER_SCHEMA_RELPATH
REAL_TEMPLATE = (
    ROOT / "docs/m2c_freeze/m2cr_r4_bootstrap_template_v1.json"
)
PACKET_RELPATH = "docs/m2cr_r4_launch_packet.json"
TEMPLATE_RELPATH = "docs/m2c_freeze/m2cr_r4_bootstrap_template_v1.json"
ENVIRONMENT_RELPATH = "docs/m2c_freeze/fake_environment_freeze.json"
AUTHORIZATION_ID = "m2cr-auth-20260719-01"
SECOND_AUTHORIZATION_ID = "m2cr-auth-20260719-02"
LAUNCH_ATTEMPT_ID = "m2cr-launch-20260719-01"
SECOND_LAUNCH_ATTEMPT_ID = "m2cr-launch-20260719-02"
RUN_ID = "diagnostic-m2cr-auth-20260719-01"
DATE = "2026-07-19"


def _git(repo: Path, *arguments: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", "-C", os.fspath(repo), *arguments],
        check=True,
        capture_output=True,
    )


def _commit(repo: Path, message: str) -> str:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)
    return os.fsdecode(_git(repo, "rev-parse", "HEAD").stdout).strip()


def _write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _jsonl(events: list[dict[str, Any]]) -> str:
    return "".join(canonical_dumps(event) + "\n" for event in events)


def _grant(
    chain: dict[str, Any], *, frozen_chain: dict[str, Any] | None = None
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "event": "authorization_granted",
        "event_id": "m2cr-ev-000001",
        "authorization_id": AUTHORIZATION_ID,
        "date": DATE,
        "scope": {
            "milestone": "R4",
            "record_kind": "diagnostic",
            "one_shot": True,
        },
        "frozen_chain": frozen_chain
        if frozen_chain is not None
        else {
            name: value
            for name, value in chain.items()
            if name != "authorization_id"
        },
    }


def _historical() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "event": "historical_authorization_record",
        "event_id": "m2cr-ev-000001",
        "authorization_id": AUTHORIZATION_ID,
        "date": DATE,
        "disposition": "CONSUMED",
        "adjudicated_under_prospective_rule": False,
        "basis": "Hermetic historical fixture in the spirit of D45.",
        "attempt_outcome": "UNVALIDATED_ATTEMPT",
        "scientific_result": False,
        "evidence_location": "runs/historical-fixture/",
        "evidence_carries_certification_weight": False,
        "historical_note": "Not a prospective grant.",
    }


def _consumed_events(chain: dict[str, Any]) -> list[dict[str, Any]]:
    payload_digest = "d" * 64
    return [
        {
            "schema_version": 1,
            "event": "launch_attempt_started",
            "event_id": "m2cr-ev-000002",
            "authorization_id": AUTHORIZATION_ID,
            "launch_attempt_id": LAUNCH_ATTEMPT_ID,
            "date": DATE,
        },
        {
            "schema_version": 1,
            "event": "payload_started",
            "event_id": "m2cr-ev-000003",
            "authorization_id": AUTHORIZATION_ID,
            "launch_attempt_id": LAUNCH_ATTEMPT_ID,
            "date": DATE,
            "payload_started_sha256": payload_digest,
            "bound_to": {
                "authorization_id": AUTHORIZATION_ID,
                "launch_attempt_id": LAUNCH_ATTEMPT_ID,
                "execution_commit": chain["execution_commit"],
                "environment_freeze_manifest_sha256": chain[
                    "environment_freeze_manifest_sha256"
                ],
            },
        },
        {
            "schema_version": 1,
            "event": "terminal_outcome",
            "event_id": "m2cr-ev-000004",
            "authorization_id": AUTHORIZATION_ID,
            "launch_attempt_id": LAUNCH_ATTEMPT_ID,
            "date": DATE,
            "record_kind": "diagnostic",
            "status": "COMPLETED",
            "terminal_record_sha256": "e" * 64,
            "raw_manifest_sha256": "f" * 64,
        },
        {
            "schema_version": 1,
            "event": "authorization_consumed",
            "event_id": "m2cr-ev-000005",
            "authorization_id": AUTHORIZATION_ID,
            "launch_attempt_id": LAUNCH_ATTEMPT_ID,
            "date": DATE,
            "derived_from": {
                "event": "payload_started",
                "event_id": "m2cr-ev-000003",
                "payload_started_sha256": payload_digest,
            },
        },
    ]


def build_launch_repo(
    tmp_path: Path,
    *,
    consumed: bool = False,
    historical_only: bool = False,
    grant_digest_mismatch: bool = False,
    grant_execution_commit_mismatch: bool = False,
) -> dict[str, Any]:
    """Build one closed hermetic authority repository and launch worktree."""

    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", os.fspath(repo)], check=True)
    _git(repo, "config", "user.email", "m2cr-tests@example.invalid")
    _git(repo, "config", "user.name", "M2cR Tests")

    schema_path = repo / r4_launch.LEDGER_SCHEMA_RELPATH
    _write(schema_path, REAL_SCHEMA.read_bytes())
    manifest_paths = {
        "infrastructure": repo / r4_launch.COMMITTED_INFRA_RELPATH,
        "environment_freeze": repo / ENVIRONMENT_RELPATH,
        "protocol": repo / r4_launch.COMMITTED_PROTOCOL_RELPATH,
    }
    manifest_bytes = {
        "infrastructure": b"fake infrastructure manifest bytes\n",
        "environment_freeze": b"fake environment freeze manifest bytes\n",
        "protocol": b"fake protocol manifest bytes\n",
    }
    for name, path in manifest_paths.items():
        _write(path, manifest_bytes[name])
    template_path = repo / TEMPLATE_RELPATH
    _write(template_path, canonical_bytes(r4_launch.DIAGNOSTIC_TEMPLATE_DOCUMENT))
    sha1 = _commit(repo, "freeze")

    mismatched_commit = None
    if grant_execution_commit_mismatch:
        anchor = repo / "docs/m2c_freeze/grant_commit_anchor.txt"
        _write(anchor, b"grant commit anchor\n")
        mismatched_commit = _commit(repo, "grant commit anchor")

    manifest_pins = {
        "infrastructure": {
            "path": r4_launch.COMMITTED_INFRA_RELPATH,
            "sha256": sha256_file(manifest_paths["infrastructure"]),
        },
        "environment_freeze": {
            "path": ENVIRONMENT_RELPATH,
            "sha256": sha256_file(manifest_paths["environment_freeze"]),
        },
        "protocol": {
            "path": r4_launch.COMMITTED_PROTOCOL_RELPATH,
            "sha256": sha256_file(manifest_paths["protocol"]),
        },
    }
    chain = {
        "v117_canonical_sha256": V117_CANONICAL_SHA256,
        "infrastructure_manifest_sha256": manifest_pins["infrastructure"][
            "sha256"
        ],
        "environment_freeze_manifest_sha256": manifest_pins[
            "environment_freeze"
        ]["sha256"],
        "protocol_manifest_sha256": manifest_pins["protocol"]["sha256"],
        "execution_commit": sha1,
        "authorization_id": AUTHORIZATION_ID,
    }

    frozen_chain = {
        name: value for name, value in chain.items() if name != "authorization_id"
    }
    if grant_digest_mismatch:
        frozen_chain["protocol_manifest_sha256"] = "9" * 64
    if mismatched_commit is not None:
        frozen_chain["execution_commit"] = mismatched_commit

    if historical_only:
        events = [_historical()]
    else:
        events = [_grant(chain, frozen_chain=frozen_chain)]
        if consumed:
            events.extend(_consumed_events(chain))
    ledger_text = _jsonl(events)
    ledger_report = validate_ledger(ledger_text)
    assert ledger_report["ok"], ledger_report["errors"]
    ledger_path = repo / r4_launch.LEDGER_RELPATH
    _write(ledger_path, ledger_text.encode("utf-8"))

    worktree = tmp_path / "wt"
    launch_attempt_id = SECOND_LAUNCH_ATTEMPT_ID if consumed else LAUNCH_ATTEMPT_ID
    packet = {
        "kind": r4_launch.PACKET_KIND,
        "schema_version": r4_launch.PACKET_SCHEMA_VERSION,
        "milestone": "R4",
        "record_kind": "diagnostic",
        "authorization_id": AUTHORIZATION_ID,
        "launch_attempt_id": launch_attempt_id,
        "run_id": RUN_ID,
        "execution_commit": sha1,
        "chain": chain,
        "bootstrap_template": {
            "path": TEMPLATE_RELPATH,
            "sha256": sha256_file(template_path),
        },
        "manifests": manifest_pins,
        "worktree_root": os.fspath(worktree.resolve()),
        "evidence_dir": f"docs/m2c_evidence/{RUN_ID}/",
        "wall_clock_ceiling_hours": 8.0,
    }
    packet_path = repo / PACKET_RELPATH
    _write(packet_path, canonical_bytes(packet))
    authority_commit = _commit(repo, "authority")
    _git(repo, "worktree", "add", "--detach", os.fspath(worktree), sha1)
    return {
        "repo": repo,
        "worktree": worktree,
        "packet": packet,
        "packet_path": packet_path,
        "ledger_path": ledger_path,
        "ledger_text": ledger_text,
        "template_path": template_path,
        "manifest_paths": manifest_paths,
        "manifest_bytes": manifest_bytes,
        "chain": chain,
        "sha1": sha1,
        "authority_commit": authority_commit,
        "mismatched_commit": mismatched_commit,
        "authorization_id": AUTHORIZATION_ID,
        "launch_attempt_id": launch_attempt_id,
        "run_id": RUN_ID,
    }


def _rewrite_packet(data: dict[str, Any], *, commit: bool = True) -> None:
    _write(data["packet_path"], canonical_bytes(data["packet"]))
    if commit:
        _commit(data["repo"], "packet variant")


def _run(
    data: dict[str, Any], capsys: pytest.CaptureFixture[str], *, execute: bool = False
) -> tuple[int, dict[str, Any]]:
    arguments = ["--packet", os.fspath(data["packet_path"])]
    if execute:
        arguments.append("--execute")
    rc = r4_launch.main(arguments)
    captured = capsys.readouterr()
    assert captured.err == ""
    lines = captured.out.splitlines()
    assert len(lines) == 1, captured.out
    return rc, json.loads(lines[0])


def _checks(report: dict[str, Any], name: str) -> list[dict[str, str]]:
    return [item for item in report["checks"] if item["check"] == name]


def _assert_failed(report: dict[str, Any], name: str) -> None:
    matching = _checks(report, name)
    assert matching, report["checks"]
    assert any(item["status"] == "FAIL" for item in matching), matching


def _assert_passed(report: dict[str, Any], name: str) -> None:
    matching = _checks(report, name)
    assert matching, report["checks"]
    assert all(item["status"] == "PASS" for item in matching), matching


def _never_called(*args: Any, **kwargs: Any) -> Any:
    raise AssertionError("reviewed execution machinery must not be called")


def test_constants_match_frozen_authorities() -> None:
    schema = json.loads(REAL_SCHEMA.read_text(encoding="utf-8"))
    assert r4_launch.COMMITTED_INFRA_RELPATH == (
        capture_module._COMMITTED_INFRA_RELPATH
    )
    assert r4_launch.COMMITTED_PROTOCOL_RELPATH == (
        capture_module._COMMITTED_PROTOCOL_RELPATH
    )
    patterns = {
        "authorization_id": r4_launch.AUTHORIZATION_ID_RE.pattern,
        "launch_attempt_id": r4_launch.LAUNCH_ATTEMPT_ID_RE.pattern,
        "sha256": r4_launch.SHA256_RE.pattern,
        "git_commit": r4_launch.GIT_COMMIT_RE.pattern,
        "event_id": r4_launch.EVENT_ID_RE.pattern,
    }
    assert patterns == {
        name: schema["$defs"][name]["pattern"] for name in patterns
    }
    assert r4_launch.RUN_ID_RE.pattern == r"^[a-z0-9][a-z0-9_-]{2,63}$"
    assert REAL_TEMPLATE.read_bytes() == canonical_bytes(
        r4_launch.DIAGNOSTIC_TEMPLATE_DOCUMENT
    )
    assert sha256_file(REAL_TEMPLATE) == (
        "d62fee603088979111ff6f63c66c29093a4b3f413ee1d52c2f4869f17493b299"
    )
    assert WALL_CLOCK_CEILING_HOURS == 8.0


def test_validate_mode_is_read_only_and_never_calls_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    data = build_launch_repo(tmp_path)
    before = data["ledger_path"].read_bytes()
    monkeypatch.setattr(r4_launch, "launch_config_from_freeze", _never_called)
    monkeypatch.setattr(r4_launch, "capture_run", _never_called)

    rc, report = _run(data, capsys)

    assert rc == 0
    assert report["ok"] is True
    assert report["mode"] == "validate"
    assert data["ledger_path"].read_bytes() == before
    assert not (data["repo"] / data["packet"]["evidence_dir"]).exists()


def test_execute_appends_one_attempt_then_calls_factory_and_capture_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    data = build_launch_repo(tmp_path)
    before = data["ledger_path"].read_bytes()
    sentinel = object()
    factory_calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
    capture_calls: list[Any] = []

    def factory(*args: Any, **kwargs: Any) -> object:
        factory_calls.append((args, kwargs))
        return sentinel

    def capture(config: Any) -> dict[str, Any]:
        capture_calls.append(config)
        assert config is sentinel
        lines = data["ledger_path"].read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2
        assert json.loads(lines[-1])["event"] == "launch_attempt_started"
        return {
            "status": "COMPLETED",
            "not_a_result": True,
            "evidence": {"raw_manifest_sha256": "0" * 64},
        }

    monkeypatch.setattr(r4_launch, "launch_config_from_freeze", factory)
    monkeypatch.setattr(r4_launch, "capture_run", capture)

    rc, report = _run(data, capsys, execute=True)

    assert rc == 0
    assert report["ok"] is True
    assert len(factory_calls) == 1
    assert capture_calls == [sentinel]
    after = data["ledger_path"].read_bytes()
    assert after.startswith(before)
    appended = after[len(before) :]
    assert appended.count(b"\n") == 1
    expected_event = {
        "schema_version": 1,
        "event": "launch_attempt_started",
        "event_id": "m2cr-ev-000002",
        "authorization_id": AUTHORIZATION_ID,
        "launch_attempt_id": LAUNCH_ATTEMPT_ID,
        "date": time.strftime("%Y-%m-%d"),
    }
    assert appended == canonical_bytes(expected_event) + b"\n"
    assert json.loads(appended) == expected_event
    arguments, keywords = factory_calls[0]
    worktree = data["worktree"].resolve()
    assert arguments == (
        worktree / ENVIRONMENT_RELPATH,
        worktree / r4_launch.COMMITTED_INFRA_RELPATH,
    )
    assert keywords == {
        "run_dir": data["repo"] / f"docs/m2c_evidence/{RUN_ID}",
        "run_id": RUN_ID,
        "authorization_id": AUTHORIZATION_ID,
        "launch_attempt_id": LAUNCH_ATTEMPT_ID,
        "record_kind": "diagnostic",
        "chain": data["chain"],
        "bootstrap_template_path": worktree / TEMPLATE_RELPATH,
        "worktree_root": worktree,
    }
    assert report["run_dir"] == os.fspath(
        data["repo"] / f"docs/m2c_evidence/{RUN_ID}"
    )
    assert report["payload_started_exists"] is False
    assert report["authorization_consumed"] is False
    assert report["terminal_status"] == "COMPLETED"
    assert report["not_a_result"] is True
    assert report["payload_json_exists"] is False
    assert report["terminal_record_sha256"] is None
    assert report["raw_manifest_sha256"] == "0" * 64
    assert report["launch_attempt_event_id"] == "m2cr-ev-000002"


def test_execute_validation_failure_has_no_side_effect(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    data = build_launch_repo(tmp_path)
    data["packet"]["bootstrap_template"]["sha256"] = "7" * 64
    _rewrite_packet(data)
    before = data["ledger_path"].read_bytes()
    monkeypatch.setattr(r4_launch, "launch_config_from_freeze", _never_called)
    monkeypatch.setattr(r4_launch, "capture_run", _never_called)

    rc, report = _run(data, capsys, execute=True)

    assert rc == 1
    assert report["ok"] is False
    _assert_failed(report, "template_disk")
    assert data["ledger_path"].read_bytes() == before


def test_execute_factory_refusal_does_not_start_attempt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    data = build_launch_repo(tmp_path)
    before = data["ledger_path"].read_bytes()
    factory_calls = 0

    def refusing_factory(*args: Any, **kwargs: Any) -> Any:
        nonlocal factory_calls
        factory_calls += 1
        raise ValueError("refused")

    monkeypatch.setattr(r4_launch, "launch_config_from_freeze", refusing_factory)
    monkeypatch.setattr(r4_launch, "capture_run", _never_called)

    rc, report = _run(data, capsys, execute=True)

    assert rc == 2
    assert factory_calls == 1
    _assert_failed(report, "factory")
    assert _checks(report, "factory")[0]["detail"] == "refused"
    assert data["ledger_path"].read_bytes() == before


PacketMutation = Callable[[dict[str, Any]], None]


def _set_nested(*keys: str, value: Any) -> PacketMutation:
    def mutate(packet: dict[str, Any]) -> None:
        target = packet
        for key in keys[:-1]:
            target = target[key]
        target[keys[-1]] = value

    return mutate


PACKET_REJECTIONS: list[tuple[str, PacketMutation, str]] = [
    ("unknown key", lambda packet: packet.__setitem__("unknown", 1), "packet_keys"),
    ("missing manifests", lambda packet: packet.pop("manifests"), "packet_keys"),
    ("missing chain", lambda packet: packet.pop("chain"), "packet_keys"),
    ("wrong kind", _set_nested("kind", value="other"), "packet_kind"),
    (
        "wrong schema version",
        _set_nested("schema_version", value=2),
        "packet_schema_version",
    ),
    ("wrong milestone", _set_nested("milestone", value="R5"), "milestone"),
    (
        "wrong record kind",
        _set_nested("record_kind", value="result"),
        "record_kind",
    ),
    (
        "malformed authorization id",
        _set_nested("authorization_id", value="bad"),
        "authorization_id",
    ),
    (
        "malformed launch id",
        _set_nested("launch_attempt_id", value="bad"),
        "launch_attempt_id",
    ),
    ("malformed run id", _set_nested("run_id", value="NO"), "run_id"),
    (
        "malformed commit",
        _set_nested("execution_commit", value="abc"),
        "execution_commit",
    ),
    (
        "shortened ceiling",
        _set_nested("wall_clock_ceiling_hours", value=7.5),
        "wall_clock_ceiling_hours",
    ),
    (
        "boolean ceiling",
        _set_nested("wall_clock_ceiling_hours", value=True),
        "wall_clock_ceiling_hours",
    ),
    (
        "wrong evidence dir",
        _set_nested("evidence_dir", value="docs/m2c_evidence/other/"),
        "evidence_dir",
    ),
    (
        "chain missing member",
        lambda packet: packet["chain"].pop("protocol_manifest_sha256"),
        "chain",
    ),
    (
        "chain extra member",
        lambda packet: packet["chain"].__setitem__("extra", "0" * 64),
        "chain",
    ),
    (
        "chain authorization mismatch",
        _set_nested("chain", "authorization_id", value=SECOND_AUTHORIZATION_ID),
        "chain_authorization_id",
    ),
    (
        "chain commit mismatch",
        _set_nested("chain", "execution_commit", value="a" * 40),
        "chain_execution_commit",
    ),
    (
        "manifest digest chain mismatch",
        _set_nested("manifests", "protocol", "sha256", value="8" * 64),
        "manifest_protocol_chain",
    ),
    (
        "infrastructure relpath substitution",
        _set_nested(
            "manifests",
            "infrastructure",
            "path",
            value="docs/m2c_freeze/substitute.json",
        ),
        "manifest_infrastructure_path",
    ),
]


@pytest.mark.parametrize(
    ("label", "mutate", "failed_check"),
    PACKET_REJECTIONS,
    ids=[case[0] for case in PACKET_REJECTIONS],
)
def test_packet_document_rejections(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    label: str,
    mutate: PacketMutation,
    failed_check: str,
) -> None:
    data = build_launch_repo(tmp_path)
    mutate(data["packet"])
    _rewrite_packet(data)
    monkeypatch.setattr(r4_launch, "launch_config_from_freeze", _never_called)
    monkeypatch.setattr(r4_launch, "capture_run", _never_called)

    rc, report = _run(data, capsys)

    assert rc == 1, label
    assert report["ok"] is False
    _assert_failed(report, failed_check)


def test_noncanonical_packet_is_rejected_even_when_committed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    data = build_launch_repo(tmp_path)
    data["packet_path"].write_bytes(data["packet_path"].read_bytes() + b"\n")
    _commit(data["repo"], "noncanonical packet")
    monkeypatch.setattr(r4_launch, "launch_config_from_freeze", _never_called)
    monkeypatch.setattr(r4_launch, "capture_run", _never_called)

    rc, report = _run(data, capsys)

    assert rc == 1
    _assert_failed(report, "packet_canonical")
    assert [
        item["check"] for item in report["checks"] if item["status"] == "FAIL"
    ] == ["packet_canonical"]


def test_uncommitted_packet_is_rejected(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = build_launch_repo(tmp_path)
    data["packet"]["launch_attempt_id"] = SECOND_LAUNCH_ATTEMPT_ID
    _rewrite_packet(data, commit=False)

    rc, report = _run(data, capsys)

    assert rc == 1
    _assert_failed(report, "packet_committed")


def test_template_digest_mismatch_is_rejected(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = build_launch_repo(tmp_path)
    data["template_path"].write_bytes(canonical_bytes({"payload": {}}))

    rc, report = _run(data, capsys)

    assert rc == 1
    _assert_failed(report, "template_disk")


def test_template_content_substitution_fails_fixed_document_check(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = build_launch_repo(tmp_path)
    substitute = {
        "payload": {"entry": "example.invalid:entry", "pass_context": True}
    }
    substitute_bytes = canonical_bytes(substitute)
    data["template_path"].write_bytes(substitute_bytes)
    data["packet"]["bootstrap_template"]["sha256"] = sha256_bytes(
        substitute_bytes
    )
    _rewrite_packet(data, commit=False)
    _commit(data["repo"], "committed template substitution")

    rc, report = _run(data, capsys)

    assert rc == 1
    _assert_passed(report, "template_disk")
    _assert_failed(report, "template_canonical_fixed")
    _assert_passed(report, "template_committed")


def test_template_committed_check_discriminates_head_from_disk(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = build_launch_repo(tmp_path)
    original = data["template_path"].read_bytes()
    data["template_path"].write_bytes(canonical_bytes({"payload": {}}))
    _commit(data["repo"], "different committed template")
    data["template_path"].write_bytes(original)

    rc, report = _run(data, capsys)

    assert rc == 1
    _assert_passed(report, "template_disk")
    _assert_passed(report, "template_canonical_fixed")
    _assert_failed(report, "template_committed")


def test_manifest_digest_mismatch_is_rejected(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = build_launch_repo(tmp_path)
    data["manifest_paths"]["protocol"].write_bytes(b"edited manifest bytes\n")

    rc, report = _run(data, capsys)

    assert rc == 1
    _assert_failed(report, "manifest_disk_protocol")


def test_uncommitted_ledger_append_is_rejected(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = build_launch_repo(tmp_path)
    second_grant = _grant(data["chain"])
    second_grant["event_id"] = "m2cr-ev-000002"
    second_grant["authorization_id"] = SECOND_AUTHORIZATION_ID
    with data["ledger_path"].open("a", encoding="utf-8") as handle:
        handle.write(canonical_dumps(second_grant) + "\n")
    assert validate_ledger(data["ledger_path"].read_text(encoding="utf-8"))["ok"]

    rc, report = _run(data, capsys)

    assert rc == 1
    _assert_failed(report, "ledger_committed")


def test_historical_authorization_never_satisfies_chain(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = build_launch_repo(tmp_path, historical_only=True)

    rc, report = _run(data, capsys)

    assert rc == 1
    _assert_failed(report, "chain_and_grant")
    assert any(
        "historical_authorization_record" in item["detail"]
        for item in _checks(report, "chain_and_grant")
    )


def test_grant_digest_mismatch_needs_stronger_frozen_chain_check(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = build_launch_repo(tmp_path, grant_digest_mismatch=True)

    rc, report = _run(data, capsys)

    assert rc == 1
    _assert_passed(report, "chain_and_grant")
    _assert_failed(report, "grant_frozen_chain_equality")


def test_grant_execution_commit_mismatch_is_rejected_by_chain_audit(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = build_launch_repo(tmp_path, grant_execution_commit_mismatch=True)

    rc, report = _run(data, capsys)

    assert rc == 1
    _assert_failed(report, "chain_and_grant")
    assert any(
        "commit frozen by the grant" in item["detail"]
        for item in _checks(report, "chain_and_grant")
    )


def test_consumed_grant_is_rejected(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = build_launch_repo(tmp_path, consumed=True)

    rc, report = _run(data, capsys)

    assert rc == 1
    _assert_failed(report, "chain_and_grant")
    assert any(
        "already consumed" in item["detail"]
        for item in _checks(report, "chain_and_grant")
    )
    _assert_passed(report, "launch_attempt_fresh")


def test_stale_attempt_id_is_rejected_independently(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = build_launch_repo(tmp_path, consumed=True)
    data["packet"]["launch_attempt_id"] = LAUNCH_ATTEMPT_ID
    _rewrite_packet(data)

    rc, report = _run(data, capsys)

    assert rc == 1
    _assert_failed(report, "launch_attempt_fresh")


def test_existing_evidence_dir_names_fresh_run_blocker(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = build_launch_repo(tmp_path)
    evidence = data["repo"] / data["packet"]["evidence_dir"]
    evidence.mkdir(parents=True)
    (evidence / "prelaunch.json").write_bytes(b"fixture")

    rc, report = _run(data, capsys)

    assert rc == 1
    _assert_failed(report, "evidence_dir_absent")
    assert "prelaunch.json" in _checks(report, "evidence_dir_absent")[0]["detail"]


def _point_packet_at_worktree(data: dict[str, Any], worktree: Path) -> None:
    data["packet"]["worktree_root"] = os.fspath(worktree.resolve())
    _rewrite_packet(data)


def test_worktree_at_wrong_commit_is_rejected(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = build_launch_repo(tmp_path)
    wrong = tmp_path / "wrong-wt"
    _git(
        data["repo"],
        "worktree",
        "add",
        "--detach",
        os.fspath(wrong),
        data["authority_commit"],
    )
    _point_packet_at_worktree(data, wrong)

    rc, report = _run(data, capsys)

    assert rc == 1
    _assert_failed(report, "worktree_head")


def test_attached_worktree_is_rejected(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = build_launch_repo(tmp_path)
    attached = tmp_path / "attached-wt"
    _git(
        data["repo"],
        "worktree",
        "add",
        "-b",
        "r4-launch-test-branch",
        os.fspath(attached),
        data["sha1"],
    )
    _point_packet_at_worktree(data, attached)

    rc, report = _run(data, capsys)

    assert rc == 1
    _assert_failed(report, "worktree_detached")


def test_dirty_worktree_is_rejected(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = build_launch_repo(tmp_path)
    target = data["worktree"] / r4_launch.COMMITTED_PROTOCOL_RELPATH
    target.write_bytes(target.read_bytes() + b"dirty")

    rc, report = _run(data, capsys)

    assert rc == 1
    _assert_failed(report, "worktree_clean")


def test_missing_worktree_is_rejected(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = build_launch_repo(tmp_path)
    missing = tmp_path / "missing-worktree"
    data["packet"]["worktree_root"] = os.fspath(missing.resolve())
    _rewrite_packet(data)

    rc, report = _run(data, capsys)

    assert rc == 1
    _assert_failed(report, "worktree_exists")


def test_worktree_must_be_distinct_from_authority_repo(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = build_launch_repo(tmp_path)
    _point_packet_at_worktree(data, data["repo"])

    rc, report = _run(data, capsys)

    assert rc == 1
    _assert_failed(report, "worktree_distinct")


def test_worktree_template_byte_drift_is_rejected(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = build_launch_repo(tmp_path)
    target = data["worktree"] / TEMPLATE_RELPATH
    target.write_bytes(canonical_bytes({"payload": {}}))

    rc, report = _run(data, capsys)

    assert rc == 1
    _assert_failed(report, "worktree_template")


def test_next_event_id_uses_maximum_and_zero_pads() -> None:
    ledger = _jsonl(
        [
            {"event_id": "m2cr-ev-000009"},
            {"event_id": "m2cr-ev-000002"},
            {"event_id": "not-an-event-id"},
        ]
    )
    assert r4_launch.next_event_id(ledger) == "m2cr-ev-000010"


def test_attempt_event_schema_rejects_malformed_date() -> None:
    event = {
        "schema_version": 1,
        "event": "launch_attempt_started",
        "event_id": "m2cr-ev-000002",
        "authorization_id": AUTHORIZATION_ID,
        "launch_attempt_id": LAUNCH_ATTEMPT_ID,
        "date": "19 July 2026",
    }
    with pytest.raises(ValueError, match="schema error"):
        r4_launch.validate_attempt_event(event, REAL_SCHEMA)


def test_validate_mode_never_calls_execution_on_broken_worktree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    data = build_launch_repo(tmp_path)
    data["packet"]["worktree_root"] = os.fspath(
        (tmp_path / "does-not-exist").resolve()
    )
    _rewrite_packet(data)
    monkeypatch.setattr(r4_launch, "launch_config_from_freeze", _never_called)
    monkeypatch.setattr(r4_launch, "capture_run", _never_called)

    rc, report = _run(data, capsys)

    assert rc == 1
    _assert_failed(report, "worktree_exists")


def test_capture_publication_exception_is_reported_then_propagated(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    data = build_launch_repo(tmp_path)
    sentinel = object()
    monkeypatch.setattr(
        r4_launch, "launch_config_from_freeze", lambda *args, **kwargs: sentinel
    )

    def fail_capture(config: Any) -> Any:
        assert config is sentinel
        raise TerminalPublicationError("publication uncertain")

    monkeypatch.setattr(r4_launch, "capture_run", fail_capture)

    with pytest.raises(TerminalPublicationError, match="publication uncertain"):
        r4_launch.main(
            ["--packet", os.fspath(data["packet_path"]), "--execute"]
        )
    captured = capsys.readouterr()
    report = json.loads(captured.out)
    assert report["ok"] is False
    assert "publication uncertain" in report["capture_exception"]
    _assert_failed(report, "capture_run")
    assert len(data["ledger_path"].read_text(encoding="utf-8").splitlines()) == 2
