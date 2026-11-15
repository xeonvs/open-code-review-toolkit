"""Canonical JSON construction with a bound on retained UTF-8 bytes."""

from __future__ import annotations

import io
import json

from ocr_toolkit.evidence.store.contracts import EvidenceStoreBudgetError


def encoded_size(value: object) -> int:
    """Measure one already bounded value with the store's canonical encoding."""

    return sum(
        len(part.encode("utf-8"))
        for part in json.JSONEncoder(
            sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).iterencode(value)
    )


def bounded_json(value: object, *, max_bytes: int, reserved_bytes: int) -> str:
    """Stop construction at the byte ceiling, including the final newline."""

    size = 1
    output = io.StringIO()
    encoder = json.JSONEncoder(sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    for chunk in encoder.iterencode(value):
        size += len(chunk.encode("utf-8"))
        if size > max_bytes - reserved_bytes:
            raise EvidenceStoreBudgetError(
                size + reserved_bytes,
                max_bytes,
                "bytes",
                message="serialized evidence store exceeds its byte budget",
            )
        output.write(chunk)
    return output.getvalue() + "\n"
