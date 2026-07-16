"""Canonical serialization, nonfinite sentinels, digests, atomic writes.

Plan §5.4 freezes the sentinel objects and the canonical form: sorted keys,
compact separators, UTF-8, ``allow_nan=False``. The v1.17 canonical hash is
reproduced by exactly this form (D47 verified it with stdlib only), so this
module is the single serialization authority for every R2 artifact and
record. Plan §3.1 freezes the write order discipline: write-temp, fsync,
atomic rename.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

__all__ = [
    "NONFINITE_NEG_INF",
    "NONFINITE_POS_INF",
    "NONFINITE_NAN",
    "encode_float",
    "encode_vector",
    "encode_matrix",
    "decode_number",
    "is_nonfinite_sentinel",
    "canonical_dumps",
    "canonical_bytes",
    "canonical_sha256",
    "sha256_bytes",
    "sha256_file",
    "atomic_write_bytes",
    "atomic_write_canonical_json",
    "append_jsonl_line",
]

# Frozen sentinel objects (plan §5.4): closed objects whose single property
# takes one of exactly these three enum values.
NONFINITE_NEG_INF = {"_nonfinite": "-inf"}
NONFINITE_POS_INF = {"_nonfinite": "+inf"}
NONFINITE_NAN = {"_nonfinite": "nan"}

_SENTINEL_VALUES = ("-inf", "+inf", "nan")


def encode_float(value: float) -> float | dict[str, str]:
    """Encode one scalar under the element-level rule of plan §5.4."""

    value = float(value)
    if math.isnan(value):
        return dict(NONFINITE_NAN)
    if math.isinf(value):
        return dict(NONFINITE_POS_INF) if value > 0 else dict(NONFINITE_NEG_INF)
    return value


def encode_vector(values: Iterable[float]) -> list[float | dict[str, str]]:
    """Encode a one-dimensional numeric sequence element-wise."""

    return [encode_float(value) for value in values]


def encode_matrix(
    rows: Iterable[Iterable[float]],
) -> list[list[float | dict[str, str]]]:
    """Encode a two-dimensional numeric sequence element-wise."""

    return [encode_vector(row) for row in rows]


def is_nonfinite_sentinel(obj: Any) -> bool:
    """True iff ``obj`` is exactly one frozen sentinel object."""

    return (
        isinstance(obj, Mapping)
        and set(obj.keys()) == {"_nonfinite"}
        and obj["_nonfinite"] in _SENTINEL_VALUES
    )


def decode_number(obj: Any) -> float:
    """Invert :func:`encode_float` for round-trip tests."""

    if is_nonfinite_sentinel(obj):
        kind = obj["_nonfinite"]
        if kind == "nan":
            return math.nan
        return math.inf if kind == "+inf" else -math.inf
    if isinstance(obj, bool) or not isinstance(obj, (int, float)):
        raise ValueError(f"not a serialized number: {obj!r}")
    return float(obj)


def canonical_dumps(obj: Any) -> str:
    """Serialize to the frozen canonical JSON form.

    ``allow_nan=False`` rejects raw nonfinite literals everywhere; nonfinite
    values must arrive pre-encoded as the frozen sentinel objects.
    """

    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False)


def canonical_bytes(obj: Any) -> bytes:
    return canonical_dumps(obj).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_sha256(obj: Any) -> str:
    """sha256 of the canonical serialization (the v1.17 canonical-hash form)."""

    return sha256_bytes(canonical_bytes(obj))


def sha256_file(path: str | os.PathLike[str], chunk_size: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write_bytes(path: str | os.PathLike[str], data: bytes) -> None:
    """Write via temp file, fsync, atomic rename, directory fsync.

    Plan §3.1 frozen write order requires each layer file to become durable
    through exactly this discipline.
    """

    path = os.fspath(path)
    directory = os.path.dirname(path) or "."
    fd, temp_path = tempfile.mkstemp(dir=directory, prefix=".m2cr-tmp-")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.rename(temp_path, path)
    except BaseException:
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise
    directory_fd = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def atomic_write_canonical_json(path: str | os.PathLike[str], obj: Any) -> str:
    """Atomically write canonical JSON; return the written content's sha256."""

    data = canonical_bytes(obj)
    atomic_write_bytes(path, data)
    return sha256_bytes(data)


def append_jsonl_line(handle: Any, obj: Any, *, fsync: bool = True) -> str:
    """Append one canonical JSON line with per-line flush (write-ahead rule).

    Plan §3.2: the event stream is the durability channel; each line is
    flushed (and fsynced when the handle is a real file) so a crash preserves
    evidence up to the last flushed line. Returns the serialized line without
    its newline.
    """

    line = canonical_dumps(obj)
    handle.write(line + "\n")
    handle.flush()
    if fsync:
        fileno = getattr(handle, "fileno", None)
        if fileno is not None:
            try:
                os.fsync(fileno())
            except (OSError, ValueError):
                # Pipes and pseudo-files reject fsync; per-line flush already
                # pushed the bytes to the parent-owned descriptor.
                pass
    return line


def encode_tree(obj: Any) -> Any:
    """Recursively encode every float in a JSON-like tree under §5.4.

    Mappings keep their keys; sequences become lists; ints and bools pass
    through unchanged (they are not numeric gate outputs); floats go through
    :func:`encode_float`.
    """

    if isinstance(obj, Mapping):
        return {key: encode_tree(value) for key, value in obj.items()}
    if isinstance(obj, (list, tuple)) or (
        isinstance(obj, Sequence) and not isinstance(obj, (str, bytes))
    ):
        return [encode_tree(value) for value in obj]
    if isinstance(obj, bool) or isinstance(obj, int) or obj is None:
        return obj
    if isinstance(obj, float):
        return encode_float(obj)
    return obj
