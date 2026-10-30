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
    """Proven syntax roles; original values remain independently checked."""

    text_digest: str
    key_spans: tuple[tuple[int, int], ...]
    operator_spans: tuple[tuple[int, int], ...] = ()

    def credential_view(self, value: str) -> str:
        return self._view(value, self.key_spans, operators=False)

    def phone_view(self, value: str) -> str:
        return self._view(value, self.operator_spans, operators=True)

    def _view(self, value: str, spans: tuple[tuple[int, int], ...], *, operators: bool) -> str:
        if hashlib.sha256(value.encode()).hexdigest() != self.text_digest:
            return value
        previous = 0
        pieces = []
        if not isinstance(spans, tuple) or len(spans) > 4096:
            return value
        for span in spans:
            if not isinstance(span, tuple) or len(span) != 2:
                return value
            start, end = span
            if (
                type(start) is not int
                or type(end) is not int
                or not previous <= start < end <= len(value)
            ):
                return value
            if operators and value[start:end] not in {"*", "**"}:
                return value
            replacement = "×" if operators else "x"  # noqa: RUF001 - internal math marker
            pieces.extend((value[previous:start], replacement * (end - start)))
            previous = end
        pieces.append(value[previous:])
        return "".join(pieces)
