"""Fail-closed payload-start boundary (plan section 4.3).

The marker is the authorization-consumption boundary.  A callable guarded by
this module cannot run until every registered pre-scientific attestation has
passed and the exact canonical marker written by this process still exists.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from copy import deepcopy
from pathlib import Path
from typing import Any, ParamSpec, TypeVar

from bistar_gp.m2cr.serialization import (
    atomic_write_canonical_json,
    canonical_bytes,
    sha256_file,
)

__all__ = [
    "BoundaryViolation",
    "PayloadBoundary",
    "verify_marker",
]

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_MARKER_FIELDS = {
    "authorization_id",
    "launch_attempt_id",
    "execution_commit",
    "chain",
    "attestation_evidence_digests",
    "prelaunch_sha256",
}

P = ParamSpec("P")
R = TypeVar("R")


class BoundaryViolation(RuntimeError):
    """The payload boundary was missing, incomplete, or no longer authentic."""


def _require_sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise BoundaryViolation(f"{label} is not a lowercase sha256")
    return value


def _read_canonical_marker(path: Path) -> tuple[dict[str, Any], bytes]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise BoundaryViolation(
            f"payload marker is missing or unreadable: {exc}"
        ) from exc
    try:
        text = raw.decode("utf-8", errors="strict")
        marker = json.loads(text)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BoundaryViolation(f"payload marker is malformed: {exc}") from exc
    if not isinstance(marker, dict):
        raise BoundaryViolation("payload marker must be an object")
    try:
        canonical = canonical_bytes(marker)
    except (TypeError, ValueError) as exc:
        raise BoundaryViolation(f"payload marker is not serializable: {exc}") from exc
    if raw != canonical:
        raise BoundaryViolation("payload marker is not in canonical serialization")
    return marker, raw


def verify_marker(
    path: str | Path,
    *,
    authorization_id: str,
    launch_attempt_id: str,
    execution_commit: str,
    chain: Mapping[str, Any],
    prelaunch_sha256: str | None = None,
    attestation_evidence_digests: list[dict[str, str]] | None = None,
    expected_sha256: str | None = None,
) -> str:
    """Verify exact marker identity, canonical bytes, and optional content hash.

    The optional digest and attestation list are supplied by the boundary's
    in-process guard, making same-identity byte substitution fail closed too.
    """

    marker, _ = _read_canonical_marker(Path(path))
    if set(marker) != _MARKER_FIELDS:
        raise BoundaryViolation("payload marker has missing or unknown fields")
    expected_scalars = {
        "authorization_id": authorization_id,
        "launch_attempt_id": launch_attempt_id,
        "execution_commit": execution_commit,
    }
    for name, expected in expected_scalars.items():
        if marker.get(name) != expected:
            raise BoundaryViolation(f"payload marker {name} mismatch")
    if marker.get("chain") != dict(chain):
        raise BoundaryViolation("payload marker chain mismatch")
    _require_sha256(marker.get("prelaunch_sha256"), "prelaunch_sha256")
    if prelaunch_sha256 is not None and marker["prelaunch_sha256"] != prelaunch_sha256:
        raise BoundaryViolation("payload marker prelaunch digest mismatch")

    attestations = marker.get("attestation_evidence_digests")
    if not isinstance(attestations, list):
        raise BoundaryViolation("attestation evidence must be a list")
    names: list[str] = []
    for item in attestations:
        if not isinstance(item, dict) or set(item) != {"name", "evidence_sha256"}:
            raise BoundaryViolation("malformed attestation evidence entry")
        name = item["name"]
        if not isinstance(name, str) or not name:
            raise BoundaryViolation("attestation evidence name is empty")
        names.append(name)
        _require_sha256(item["evidence_sha256"], f"attestation {name}")
    if names != sorted(names) or len(names) != len(set(names)):
        raise BoundaryViolation("attestation evidence is not uniquely name-sorted")
    if (
        attestation_evidence_digests is not None
        and attestations != attestation_evidence_digests
    ):
        raise BoundaryViolation("attestation evidence digest set mismatch")

    actual_sha256 = sha256_file(path)
    if expected_sha256 is not None and actual_sha256 != expected_sha256:
        raise BoundaryViolation("payload marker byte digest mismatch")
    return actual_sha256


class PayloadBoundary:
    """Register attestations, durably mark payload start, and guard payloads."""

    def __init__(
        self,
        run_dir: str | Path,
        authorization_id: str,
        launch_attempt_id: str,
        execution_commit: str,
        chain: Mapping[str, Any],
    ) -> None:
        self.run_dir = Path(run_dir).resolve()
        self.marker_path = self.run_dir / "payload_started.json"
        self.authorization_id = authorization_id
        self.launch_attempt_id = launch_attempt_id
        self.execution_commit = execution_commit
        self.chain = deepcopy(dict(chain))
        self.phase_log: list[str] = []
        self._required: set[str] = set()
        self._attestations: dict[str, tuple[bool, str]] = {}
        self._marked_sha256: str | None = None
        self._marked_attestations: list[dict[str, str]] | None = None
        self._payload_entered = False

    def register_required_attestation(self, name: str) -> None:
        if self._marked_sha256 is not None:
            raise BoundaryViolation("cannot register an attestation after marking")
        if not isinstance(name, str) or not name:
            raise BoundaryViolation("attestation name must be non-empty")
        if name in self._required:
            raise BoundaryViolation(f"attestation already registered: {name}")
        self._required.add(name)

    def register_required_attestations(self, *names: str) -> None:
        for name in names:
            self.register_required_attestation(name)

    def record_attestation(self, name: str, passed: bool, evidence_sha256: str) -> None:
        if self._marked_sha256 is not None:
            raise BoundaryViolation("cannot alter an attestation after marking")
        if name not in self._required:
            raise BoundaryViolation(f"attestation was not registered: {name}")
        if name in self._attestations:
            raise BoundaryViolation(f"attestation was already recorded: {name}")
        if not isinstance(passed, bool):
            raise BoundaryViolation("attestation outcome must be boolean")
        self._attestations[name] = (
            passed,
            _require_sha256(evidence_sha256, f"attestation {name}"),
        )

    def mark(self) -> str:
        """Write the marker iff every registered attestation positively passed."""

        if self._marked_sha256 is not None:
            return verify_marker(
                self.marker_path,
                authorization_id=self.authorization_id,
                launch_attempt_id=self.launch_attempt_id,
                execution_commit=self.execution_commit,
                chain=self.chain,
                prelaunch_sha256=sha256_file(self.run_dir / "prelaunch.json"),
                attestation_evidence_digests=self._marked_attestations,
                expected_sha256=self._marked_sha256,
            )
        missing = sorted(self._required - self._attestations.keys())
        failed = sorted(
            name for name, (passed, _) in self._attestations.items() if not passed
        )
        if not self._required:
            raise BoundaryViolation("no pre-scientific attestations were registered")
        if missing or failed:
            raise BoundaryViolation(
                f"pre-scientific attestations incomplete; missing={missing}, failed={failed}"
            )
        try:
            prelaunch_sha256 = sha256_file(self.run_dir / "prelaunch.json")
        except OSError as exc:
            raise BoundaryViolation(f"prelaunch evidence is missing: {exc}") from exc
        evidence = [
            {"name": name, "evidence_sha256": self._attestations[name][1]}
            for name in sorted(self._required)
        ]
        marker = {
            "authorization_id": self.authorization_id,
            "launch_attempt_id": self.launch_attempt_id,
            "execution_commit": self.execution_commit,
            "chain": deepcopy(self.chain),
            "attestation_evidence_digests": evidence,
            "prelaunch_sha256": prelaunch_sha256,
        }
        self.phase_log.append("attestations_complete")
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self._marked_sha256 = atomic_write_canonical_json(self.marker_path, marker)
        self._marked_attestations = evidence
        self.phase_log.append("marker_written")
        return self._marked_sha256

    def guard(self, payload_callable: Callable[P, R]) -> Callable[P, R]:
        """Return a direct-call wrapper that re-attests the marker at entry."""

        def guarded(*args: P.args, **kwargs: P.kwargs) -> R:
            if self._marked_sha256 is None or self._marked_attestations is None:
                raise BoundaryViolation(
                    "payload marker was not completed in this process"
                )
            verify_marker(
                self.marker_path,
                authorization_id=self.authorization_id,
                launch_attempt_id=self.launch_attempt_id,
                execution_commit=self.execution_commit,
                chain=self.chain,
                prelaunch_sha256=sha256_file(self.run_dir / "prelaunch.json"),
                attestation_evidence_digests=self._marked_attestations,
                expected_sha256=self._marked_sha256,
            )
            if not self._payload_entered:
                self.phase_log.append("payload_entered")
                self._payload_entered = True
            return payload_callable(*args, **kwargs)

        return guarded
