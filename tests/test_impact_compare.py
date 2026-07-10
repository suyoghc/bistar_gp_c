"""
Regression test for experiments/impact_assessment.py compare().

compare() used to build its key set only from the NEW json, so a metric present
in old.json but absent from new.json (e.g. a section that raised on the new
tree and left only an 'error' leaf) vanished from both the diff listing and the
changed/unchanged counts — a broken new run could read as a clean diff.
"""

import importlib.util
import json
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def impact():
    path = Path(__file__).resolve().parents[1] / "experiments" / "impact_assessment.py"
    spec = importlib.util.spec_from_file_location("impact_assessment", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _write(tmp_path, name, payload):
    p = tmp_path / name
    p.write_text(json.dumps(payload))
    return str(p)


def test_compare_reports_keys_missing_from_either_side(impact, tmp_path, capsys):
    old = {"git_sha": "aaa", "sec": {"metric": 1.0, "gone_in_new": 2.0}}
    new = {"git_sha": "bbb", "sec": {"metric": 1.0, "error": "boom"}}
    impact.compare(_write(tmp_path, "old.json", old), _write(tmp_path, "new.json", new))
    out = capsys.readouterr().out
    assert "sec.gone_in_new" in out          # old-only leaf must be listed...
    assert "sec.error" in out                # ...and so must the new-only one
    assert "2 changed, 1 unchanged." in out  # both missing-side leaves counted


def test_compare_identical_runs_report_no_changes(impact, tmp_path, capsys):
    payload = {"git_sha": "aaa", "sec": {"a": 1.5, "b": "ok"}}
    impact.compare(_write(tmp_path, "old.json", payload),
                   _write(tmp_path, "new.json", payload))
    out = capsys.readouterr().out
    assert "0 changed, 2 unchanged." in out
