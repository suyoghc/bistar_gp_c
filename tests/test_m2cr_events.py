"""Write-ahead event stream and balance semantics (plan §3.2)."""

import io
import json
import os
import subprocess
import sys

import pytest

from bistar_gp.m2cr import events as ev


def _emit_balanced(sink):
    sink.emit("STAGE_BEGIN", stage_id="level0")
    sink.emit("NODE_BEGIN", node_index=0)
    sink.emit("ATTEMPT_BEGIN", start_label="warm", attempt_index=0)
    sink.emit("EVAL_RESULT", g=1.5, grad_inf_norm=float("+inf"))
    sink.emit("ATTEMPT_END", start_label="warm", attempt_index=0)
    sink.emit("RETRY_BEGIN", node_index=0)
    sink.emit("NODE_END", node_index=0)
    sink.emit("STAGE_END", stage_id="level0")


def test_sink_emits_canonical_lines_with_increasing_seq():
    buffer = io.StringIO()
    sink = ev.EventSink(buffer)
    _emit_balanced(sink)
    lines = buffer.getvalue().splitlines()
    assert [json.loads(line)["seq"] for line in lines] == list(range(8))
    # Numeric fields pass through the frozen sentinel encoding.
    eval_line = json.loads(lines[3])
    assert eval_line["grad_inf_norm"] == {"_nonfinite": "+inf"}
    assert eval_line["g"] == 1.5


def test_sink_rejects_unknown_event_types():
    sink = ev.EventSink(io.StringIO())
    with pytest.raises(ValueError):
        sink.emit("RETRY_END")
    with pytest.raises(ValueError):
        sink.emit("NODE_ABORT")


def test_balanced_stream_verdict():
    buffer = io.StringIO()
    _emit_balanced(ev.EventSink(buffer))
    verdict = ev.check_stream_balance(buffer.getvalue().splitlines())
    assert verdict == {"balanced": True, "reason": ""}


def test_point_events_do_not_require_closers():
    buffer = io.StringIO()
    sink = ev.EventSink(buffer)
    sink.emit("ATTEMPT_BEGIN", start_label="warm", attempt_index=0)
    sink.emit("EVAL_RESULT")
    sink.emit("RETRY_BEGIN")
    sink.emit("ATTEMPT_END", start_label="warm", attempt_index=0)
    assert ev.check_stream_balance(buffer.getvalue().splitlines())["balanced"]


def test_truncated_stream_is_unbalanced_with_reason():
    buffer = io.StringIO()
    _emit_balanced(ev.EventSink(buffer))
    lines = buffer.getvalue().splitlines()
    verdict = ev.check_stream_balance(lines[:-2])
    assert not verdict["balanced"]
    assert "unclosed" in verdict["reason"]


def test_mismatched_and_orphan_closers_are_unbalanced():
    good = [
        '{"seq":0,"event":"STAGE_BEGIN"}',
        '{"seq":1,"event":"NODE_BEGIN"}',
        '{"seq":2,"event":"STAGE_END"}',
    ]
    assert not ev.check_stream_balance(good)["balanced"]
    orphan = ['{"seq":0,"event":"ATTEMPT_END"}']
    assert not ev.check_stream_balance(orphan)["balanced"]


def test_seq_gaps_and_malformed_lines_are_unbalanced():
    assert not ev.check_stream_balance(['{"seq":1,"event":"EVAL_RESULT"}'])["balanced"]
    assert not ev.check_stream_balance(["not json"])["balanced"]
    assert not ev.check_stream_balance(['{"event":"EVAL_RESULT"}'])["balanced"]
    assert not ev.check_stream_balance([])["balanced"]
    two = ['{"seq":0,"event":"EVAL_RESULT"}', '{"seq":2,"event":"EVAL_RESULT"}']
    assert not ev.check_stream_balance(two)["balanced"]


def test_control_lines_join_seq_but_not_bracketing():
    lines = [
        '{"seq":0,"event":"HELLO","pid":1}',
        '{"seq":1,"event":"STAGE_BEGIN","stage_id":"level0"}',
        '{"seq":2,"event":"PAYLOAD_STARTED"}',
        '{"seq":3,"event":"STAGE_END","stage_id":"level0"}',
    ]
    assert ev.check_stream_balance(lines)["balanced"]


def test_parent_pipe_preserves_lines_from_a_killed_child(tmp_path):
    """A SIGKILLed child's flushed lines survive on disk (write-ahead)."""

    events_path = tmp_path / "events.jsonl"
    pipe = ev.parent_event_pipe(events_path)
    pipe.start()
    child_code = (
        "import json, os, signal, sys\n"
        "fd = int(sys.argv[1])\n"
        "w = os.fdopen(fd, 'w')\n"
        "for seq, event in enumerate(['HELLO', 'STAGE_BEGIN', 'NODE_BEGIN']):\n"
        "    w.write(json.dumps({'seq': seq, 'event': event}) + '\\n')\n"
        "    w.flush()\n"
        "os.kill(os.getpid(), signal.SIGKILL)\n"
    )
    process = subprocess.Popen(
        [sys.executable, "-c", child_code, str(pipe.write_fd)],
        pass_fds=(pipe.write_fd,),
        close_fds=True,
    )
    pipe.close_write_end_in_parent()
    process.wait()
    pipe.join(timeout=10)
    assert process.returncode == -9
    # HELLO surfaced for the spawn boundary; all flushed lines preserved.
    assert pipe.hello_event.is_set()
    lines = events_path.read_text().splitlines()
    assert [json.loads(line)["event"] for line in lines] == [
        "HELLO",
        "STAGE_BEGIN",
        "NODE_BEGIN",
    ]
    verdict = ev.check_stream_balance(lines)
    assert not verdict["balanced"]  # admitted only under INFRA/ABORTED branches


def test_closer_identity_must_match_opener():
    """Plan §5.3 reconstruction: a bracket closed under a different identity
    is a capture defect, not a balanced stream."""

    mismatched_stage = [
        '{"seq":0,"event":"STAGE_BEGIN","stage_id":"level0"}',
        '{"seq":1,"event":"STAGE_END","stage_id":"refine_1"}',
    ]
    verdict = ev.check_stream_balance(mismatched_stage)
    assert not verdict["balanced"]
    assert "identity mismatch" in verdict["reason"]

    mismatched_attempt = [
        '{"seq":0,"event":"ATTEMPT_BEGIN","start_label":"warm","attempt_index":0}',
        '{"seq":1,"event":"ATTEMPT_END","start_label":"warm","attempt_index":1}',
    ]
    assert not ev.check_stream_balance(mismatched_attempt)["balanced"]

    matched = [
        '{"seq":0,"event":"NODE_BEGIN","node_index":3}',
        '{"seq":1,"event":"NODE_END","node_index":3}',
    ]
    assert ev.check_stream_balance(matched)["balanced"]

    closer_without_identity = [
        '{"seq":0,"event":"NODE_BEGIN","node_index":3}',
        '{"seq":1,"event":"NODE_END"}',
    ]
    # A closer must repeat every identity field its opener carried; a silent
    # omission would let a malformed closer certify a COMPLETED stream.
    verdict_missing = ev.check_stream_balance(closer_without_identity)
    assert not verdict_missing["balanced"]
    assert "omits identity field" in verdict_missing["reason"]


def test_bracket_opener_must_carry_its_identity(monkeypatch):
    """External audit F5(a): an anonymous bracket opener cannot balance."""

    for lines in (
        ['{"seq":0,"event":"STAGE_BEGIN"}', '{"seq":1,"event":"STAGE_END"}'],
        ['{"seq":0,"event":"NODE_BEGIN"}', '{"seq":1,"event":"NODE_END"}'],
        [
            '{"seq":0,"event":"ATTEMPT_BEGIN","start_label":"warm"}',
            '{"seq":1,"event":"ATTEMPT_END","start_label":"warm"}',
        ],
    ):
        verdict = ev.check_stream_balance(lines)
        assert not verdict["balanced"]
        assert "omits required identity" in verdict["reason"]


def test_pump_error_surfaces_after_join(tmp_path):
    """External audit round-2 F4a: a durability failure in the pump thread is
    recorded and readable by the parent, never silently swallowed."""

    # An events path inside a non-existent directory makes the pump's open()
    # fail; the error must surface via pump_error (and hello_event is set so a
    # waiter is not left hanging).
    bad_path = tmp_path / "does_not_exist" / "events.jsonl"
    pipe = ev.parent_event_pipe(bad_path)
    pipe.start()
    pipe.close_write_end_in_parent()
    pipe.hello_event.wait(timeout=5)
    pipe.join(timeout=5)
    assert pipe.pump_error is not None
    assert isinstance(pipe.pump_error, OSError)
