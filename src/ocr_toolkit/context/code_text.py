"""In-memory source interpretation bound to exact text, never a publication grant."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum


class TextSink(Enum):
    PROSE = "prose"
    LITERAL_CODE = "literal-code"
    DIAGRAM_LABEL = "diagram-label"


@dataclass(frozen=True, slots=True)
class CodeTextContext:
    """Only proven non-value key spans; original values remain independently checked."""

    text_digest: str
    key_spans: tuple[tuple[int, int], ...]

    def credential_view(self, value: str) -> str:
        if hashlib.sha256(value.encode()).hexdigest() != self.text_digest:
            return value
        previous = 0
        pieces = []
        if not isinstance(self.key_spans, tuple) or len(self.key_spans) > 4096:
            return value
        for span in self.key_spans:
            if not isinstance(span, tuple) or len(span) != 2:
                return value
            start, end = span
            if (
                type(start) is not int
                or type(end) is not int
                or not previous <= start < end <= len(value)
            ):
                return value
            pieces.extend((value[previous:start], "x" * (end - start)))
            previous = end
        pieces.append(value[previous:])
        return "".join(pieces)
