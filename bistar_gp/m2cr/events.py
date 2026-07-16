"""Write-ahead event stream (plan §3.2).

During execution the child emits line-delimited write-ahead events over an
unbuffered pipe owned by the parent, which appends each line to
``events.jsonl`` with per-line flush. Return values remain the structured
record for completed calls; the event stream is the durability channel. A
COMPLETED payload requires a balanced event stream; the ABORTED_BUDGET and
INFRA_FAILURE branches explicitly admit an unbalanced partial stream, so a
crash preserves in-flight attempt evidence up to the last flushed line.

Gate event types are frozen by plan §3.2. Control lines (the bootstrap hello
and payload-boundary notices) share the transport but are not gate events;
balance is defined over the gate bracket pairs only, while every line must
be well-formed canonical JSON with a strictly increasing ``seq``.
"""

from __future__ import annotations

import json
import os
import threading
from collections.abc import Iterable
from typing import Any, IO

from bistar_gp.m2cr.serialization import append_jsonl_line, encode_tree

__all__ = [
    "GATE_EVENT_TYPES",
    "BRACKET_PAIRS",
    "POINT_EVENT_TYPES",
    "CONTROL_EVENT_TYPES",
    "EventSink",
    "check_stream_balance",
    "parent_event_pipe",
]

GATE_EVENT_TYPES = (
    "STAGE_BEGIN",
    "STAGE_END",
    "NODE_BEGIN",
    "NODE_END",
    "ATTEMPT_BEGIN",
    "EVAL_RESULT",
    "RETRY_BEGIN",
    "ATTEMPT_END",
)

# Bracket pairs participating in balance; EVAL_RESULT and RETRY_BEGIN are
# interior point events (plan §3.2 enumerates no RETRY_END).
BRACKET_PAIRS = (
    ("STAGE_BEGIN", "STAGE_END"),
    ("NODE_BEGIN", "NODE_END"),
    ("ATTEMPT_BEGIN", "ATTEMPT_END"),
)
POINT_EVENT_TYPES = ("EVAL_RESULT", "RETRY_BEGIN")

# Non-gate control lines sharing the transport.
CONTROL_EVENT_TYPES = ("HELLO", "PAYLOAD_STARTED", "ATTESTATION")

_OPEN_FOR = {begin: end for begin, end in BRACKET_PAIRS}
_CLOSE_FOR = {end: begin for begin, end in BRACKET_PAIRS}


class EventSink:
    """Serialize events as canonical JSON lines with per-line flush.

    Thread-safe; ``seq`` is strictly increasing from 0. Numeric payload
    fields are encoded under the §5.4 element-level sentinel rule before
    serialization.
    """

    def __init__(self, handle: IO[str], *, fsync: bool = False) -> None:
        self._handle = handle
        self._fsync = fsync
        self._lock = threading.Lock()
        self._seq = 0

    def emit(self, event: str, /, **fields: Any) -> dict[str, Any]:
        if event not in GATE_EVENT_TYPES and event not in CONTROL_EVENT_TYPES:
            raise ValueError(f"unknown event type: {event!r}")
        with self._lock:
            payload: dict[str, Any] = {"seq": self._seq, "event": event}
            payload.update(encode_tree(fields))
            append_jsonl_line(self._handle, payload, fsync=self._fsync)
            self._seq += 1
        return payload


# Identity fields a closer must repeat exactly from its opener; a bracket
# closed under a different identity is a capture defect, not a balanced
# stream (plan §5.3: node/stage evidence must support independent
# reconstruction).
_IDENTITY_FIELDS = ("stage_id", "node_index", "start_label", "attempt_index")

# The identity every bracket OPENER must carry, so an anonymous bracket from
# a truncated or buggy emitter cannot balance and certify a COMPLETED stream
# (plan §3.2/§5.3). A closer then has to repeat exactly these.
_REQUIRED_OPENER_IDENTITY = {
    "STAGE_BEGIN": ("stage_id",),
    "NODE_BEGIN": ("node_index",),
    "ATTEMPT_BEGIN": ("start_label", "attempt_index"),
}


def check_stream_balance(lines: Iterable[str]) -> dict[str, Any]:
    """Classify an event stream as balanced or not, with the exact reason.

    Balanced means: every line parses as a JSON object carrying ``seq`` and
    ``event``; ``seq`` values are 0, 1, 2, ... in order; every bracket BEGIN
    is closed by its matching END with proper nesting AND matching identity
    fields (stage_id, node_index, start_label, attempt_index, where the
    opener carries them); the bracket stack is empty at the end; every event
    type is known. Control lines participate in the ``seq`` discipline but
    not in bracketing. An empty stream is unbalanced (nothing was captured,
    so nothing is certified complete).
    """

    stack: list[tuple[str, dict[str, Any]]] = []
    expected_seq = 0
    saw_any = False
    for line_number, raw in enumerate(lines, start=1):
        raw = raw.rstrip("\n")
        if not raw:
            return _unbalanced(f"line {line_number}: blank line")
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError as exc:
            return _unbalanced(f"line {line_number}: not JSON ({exc.msg})")
        if not isinstance(obj, dict) or "event" not in obj or "seq" not in obj:
            return _unbalanced(f"line {line_number}: missing event/seq")
        saw_any = True
        if obj["seq"] != expected_seq:
            return _unbalanced(
                f"line {line_number}: seq {obj['seq']} != expected {expected_seq}"
            )
        expected_seq += 1
        event = obj["event"]
        if event in CONTROL_EVENT_TYPES:
            continue
        if event not in GATE_EVENT_TYPES:
            return _unbalanced(f"line {line_number}: unknown event {event!r}")
        if event in _OPEN_FOR:
            required = _REQUIRED_OPENER_IDENTITY.get(event, ())
            missing = [field for field in required if field not in obj]
            if missing:
                return _unbalanced(
                    f"line {line_number}: {event} omits required identity "
                    f"field(s) {missing}"
                )
            identity = {
                field: obj[field] for field in _IDENTITY_FIELDS if field in obj
            }
            stack.append((event, identity))
        elif event in _CLOSE_FOR:
            if not stack or stack[-1][0] != _CLOSE_FOR[event]:
                return _unbalanced(
                    f"line {line_number}: {event} closes "
                    f"{stack[-1][0] if stack else 'nothing'}"
                )
            _, opener_identity = stack.pop()
            for field, opener_value in opener_identity.items():
                if field not in obj:
                    # A closer must repeat every identity field its opener
                    # carried; silence here would let a malformed closer
                    # certify a COMPLETED stream (plan §3.2).
                    return _unbalanced(
                        f"line {line_number}: {event} omits identity field "
                        f"{field} carried by its opener"
                    )
                if obj[field] != opener_value:
                    return _unbalanced(
                        f"line {line_number}: {event} identity mismatch on "
                        f"{field}: opener {opener_value!r} vs closer "
                        f"{obj[field]!r}"
                    )
        # Point events need no bracket handling.
    if not saw_any:
        return _unbalanced("empty stream")
    if stack:
        return _unbalanced(
            f"unclosed brackets at end of stream: {[item[0] for item in stack]}"
        )
    return {"balanced": True, "reason": ""}


def _unbalanced(reason: str) -> dict[str, Any]:
    return {"balanced": False, "reason": reason}


class parent_event_pipe:
    """Parent-owned unbuffered pipe whose reader appends to ``events.jsonl``.

    The parent creates the pipe before spawn and passes the write end to the
    child; a reader thread appends every received line to the target file
    with per-line flush and fsync, so the on-disk stream always holds every
    line the child managed to flush before any crash. The first HELLO control
    line is surfaced through ``hello_event`` for the spawn boundary
    (plan §4.3: on receipt the parent atomically writes ``spawned.json``).
    """

    def __init__(self, events_path: str | os.PathLike[str]) -> None:
        self._events_path = os.fspath(events_path)
        self.read_fd, self.write_fd = os.pipe()
        os.set_inheritable(self.write_fd, True)
        self.hello_event = threading.Event()
        self.hello_payload: dict[str, Any] | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._pump, daemon=True)
        self._thread.start()

    def close_write_end_in_parent(self) -> None:
        try:
            os.close(self.write_fd)
        except OSError:
            pass

    def join(self, timeout: float | None = None) -> None:
        if self._thread is not None:
            self._thread.join(timeout)

    def _pump(self) -> None:
        with open(self._events_path, "a", encoding="utf-8") as sink:
            with os.fdopen(self.read_fd, "r", encoding="utf-8", errors="replace") as source:
                for line in source:
                    line = line.rstrip("\n")
                    if not line:
                        continue
                    sink.write(line + "\n")
                    sink.flush()
                    os.fsync(sink.fileno())
                    if self.hello_payload is None:
                        try:
                            obj = json.loads(line)
                        except json.JSONDecodeError:
                            obj = None
                        if isinstance(obj, dict) and obj.get("event") == "HELLO":
                            self.hello_payload = obj
                            self.hello_event.set()
