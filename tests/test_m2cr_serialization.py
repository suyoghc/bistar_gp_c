"""Canonical serialization and frozen nonfinite sentinels (plan §5.4)."""

import json
import math
import os

import numpy as np
import pytest

from bistar_gp.m2cr import serialization as ser


def test_sentinels_are_the_three_frozen_objects():
    assert ser.encode_float(float("-inf")) == {"_nonfinite": "-inf"}
    assert ser.encode_float(float("+inf")) == {"_nonfinite": "+inf"}
    assert math.isnan(float("nan"))
    assert ser.encode_float(float("nan")) == {"_nonfinite": "nan"}
    assert ser.encode_float(0.0) == 0.0
    assert ser.encode_float(-1.25) == -1.25


def test_numpy_scalars_encode_like_python_floats():
    assert ser.encode_float(np.float64("inf")) == {"_nonfinite": "+inf"}
    assert ser.encode_float(np.float64(2.5)) == 2.5
    assert ser.encode_vector(np.asarray([1.0, np.nan])) == [
        1.0,
        {"_nonfinite": "nan"},
    ]
    assert ser.encode_matrix(np.asarray([[np.inf, 1.0], [2.0, -np.inf]])) == [
        [{"_nonfinite": "+inf"}, 1.0],
        [2.0, {"_nonfinite": "-inf"}],
    ]


def test_decode_round_trips_every_sentinel_kind():
    assert ser.decode_number({"_nonfinite": "+inf"}) == math.inf
    assert ser.decode_number({"_nonfinite": "-inf"}) == -math.inf
    assert math.isnan(ser.decode_number({"_nonfinite": "nan"}))
    assert ser.decode_number(1.5) == 1.5
    with pytest.raises(ValueError):
        ser.decode_number({"_nonfinite": "infinity"})
    with pytest.raises(ValueError):
        ser.decode_number("1.5")
    with pytest.raises(ValueError):
        ser.decode_number(True)


def test_sentinel_recognizer_is_closed():
    assert ser.is_nonfinite_sentinel({"_nonfinite": "nan"})
    assert not ser.is_nonfinite_sentinel({"_nonfinite": "infinity"})
    assert not ser.is_nonfinite_sentinel({"_nonfinite": "nan", "extra": 1})
    assert not ser.is_nonfinite_sentinel({})
    assert not ser.is_nonfinite_sentinel("nan")


def test_canonical_dumps_rejects_raw_nonfinite_literals():
    with pytest.raises(ValueError):
        ser.canonical_dumps(float("nan"))
    with pytest.raises(ValueError):
        ser.canonical_dumps({"x": float("inf")})


def test_canonical_form_reproduces_the_v117_canonical_hash():
    # D47 verified the frozen canonicalization (sort_keys, compact separators,
    # sha256 over the whole file) with stdlib only; this module must agree.
    with open("docs/m2c_freeze/gtoy_profile_freeze_v1.17.json", encoding="utf-8") as f:
        obj = json.load(f)
    assert (
        ser.canonical_sha256(obj)
        == "65381bc774e894dd9aaf2207cadd9cfa2f2735dafceff4bb39492086a9e522e2"
    )


def test_canonical_dumps_sorts_keys_and_uses_compact_separators():
    assert ser.canonical_dumps({"b": 1, "a": [1, 2]}) == '{"a":[1,2],"b":1}'


def test_atomic_write_and_file_hash(tmp_path):
    target = tmp_path / "artifact.json"
    digest = ser.atomic_write_canonical_json(target, {"k": [1.5, {"a": 2}]})
    data = target.read_bytes()
    assert ser.sha256_bytes(data) == digest == ser.sha256_file(target)
    # No temp files left behind.
    assert [p.name for p in tmp_path.iterdir()] == ["artifact.json"]


def test_atomic_write_replaces_existing_content_atomically(tmp_path):
    target = tmp_path / "artifact.json"
    ser.atomic_write_canonical_json(target, {"v": 1})
    ser.atomic_write_canonical_json(target, {"v": 2})
    assert json.loads(target.read_text()) == {"v": 2}


def test_append_jsonl_line_flushes_per_line(tmp_path):
    target = tmp_path / "events.jsonl"
    with open(target, "a", encoding="utf-8") as handle:
        ser.append_jsonl_line(handle, {"seq": 0, "event": "HELLO"})
        # Visible on disk before the handle closes: the write-ahead property.
        on_disk = target.read_text()
        assert on_disk == '{"event":"HELLO","seq":0}\n'
        ser.append_jsonl_line(handle, {"seq": 1, "event": "STAGE_BEGIN"})
    assert target.read_text().count("\n") == 2


def test_encode_tree_encodes_only_floats():
    tree = {
        "f": float("inf"),
        "i": 3,
        "b": True,
        "n": None,
        "s": "x",
        "v": [1.0, float("-inf")],
        "m": {"inner": float("nan")},
    }
    encoded = ser.encode_tree(tree)
    assert encoded["f"] == {"_nonfinite": "+inf"}
    assert encoded["i"] == 3 and encoded["b"] is True and encoded["n"] is None
    assert encoded["v"] == [1.0, {"_nonfinite": "-inf"}]
    assert encoded["m"]["inner"] == {"_nonfinite": "nan"}
