"""Bounded incremental retention of requested LF-addressed text spans only."""

from __future__ import annotations

from dataclasses import dataclass, field

from ocr_toolkit.evidence.text_contracts import (
    MAX_EXCERPT_BYTES,
    MAX_EXCERPT_CHARS,
    MAX_EXCERPT_SPAN_LINES,
    MAX_SYNTAX_CHARS,
    RepositoryTextExcerpt,
    TextSpan,
)

MAX_TEXT_SPANS = 10_000
MAX_CAPTURE_BYTES = 32_000_000


def validate_spans(spans: tuple[TextSpan, ...]) -> None:
    """Reject malformed/unbounded requests before any source peer is launched."""

    if not isinstance(spans, tuple) or len(spans) > MAX_TEXT_SPANS:
        raise ValueError("invalid text excerpt requests")
    for span in spans:
        if (
            not isinstance(span, tuple)
            or len(span) != 2
            or any(type(line) is not int for line in span)
            or not 1 <= span[0] <= span[1] <= 1_000_000_000
            or span[1] - span[0] > MAX_EXCERPT_SPAN_LINES
        ):
            raise ValueError("invalid text excerpt range")


@dataclass(slots=True)
class _Capture:
    parts: list[str] = field(default_factory=list, repr=False)
    chars: int = 0
    bytes: int = 0
    limited: bool = False


def validate_capture_limits(max_bytes: int, max_source_chars: int) -> None:
    if type(max_bytes) is not int or not 0 <= max_bytes <= MAX_CAPTURE_BYTES:
        raise ValueError("invalid aggregate excerpt budget")
    if type(max_source_chars) is not int or not 0 <= max_source_chars <= MAX_SYNTAX_CHARS:
        raise ValueError("invalid full-source syntax budget")


class TextExcerptCapture:
    """No line buffer grows with source size; each chunk has bounded peer size."""

    def __init__(
        self, spans: tuple[TextSpan, ...], *, max_bytes: int, max_source_chars: int
    ) -> None:
        validate_spans(spans)
        validate_capture_limits(max_bytes, max_source_chars)
        self._spans = {span: _Capture() for span in sorted(set(spans))}
        self._max_bytes = max_bytes
        self.used_bytes = 0
        self._source_limit = max_source_chars
        self._source_chars = 0
        self._source: list[str] | None = [] if max_source_chars else None

    def feed(self, text: str, first_line: int) -> None:
        """Consume one strictly decoded chunk at its current absolute LF line."""

        if self._source is not None:
            self._source_chars += len(text)
            if self._source_chars > self._source_limit:
                self._source = None
            else:
                self._source.append(text)
        if not self._spans:
            return
        parts = text.split("\n")
        last_line = first_line + len(parts) - 1
        for (start, end), capture in self._spans.items():
            if capture.limited or end < first_line or start > last_line:
                continue
            piece = "\n".join(
                parts[max(0, start - first_line) : min(len(parts), end - first_line + 1)]
            )
            size = len(piece.encode("utf-8"))
            if (
                len(piece) > MAX_EXCERPT_CHARS - capture.chars
                or size > MAX_EXCERPT_BYTES - capture.bytes
                or size > self._max_bytes - self.used_bytes
            ):
                self.used_bytes -= capture.bytes
                capture.parts.clear()
                capture.limited = True
                continue
            capture.parts.append(piece)
            capture.chars += len(piece)
            capture.bytes += size
            self.used_bytes += size

    def finish(self, line_count: int) -> tuple[RepositoryTextExcerpt, ...]:
        return tuple(
            RepositoryTextExcerpt(
                start,
                end,
                None if capture.limited or end > line_count else "".join(capture.parts),
                "range" if end > line_count else "limit" if capture.limited else "none",
            )
            for (start, end), capture in self._spans.items()
        )

    @property
    def source(self) -> str | None:
        return "".join(self._source) if self._source is not None else None
