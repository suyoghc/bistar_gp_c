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
    sink.emit("ATTEMPT_BEGIN", start_label="warm")
    sink.emit("EVAL_RESULT")
    sink.emit("RETRY_BEGIN")
    sink.emit("ATTEMPT_END", start_label="warm")
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
        '{"seq":1,"event":"STAGE_BEGIN"}',
        '{"seq":2,"event":"PAYLOAD_STARTED"}',
        '{"seq":3,"event":"STAGE_END"}',
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
