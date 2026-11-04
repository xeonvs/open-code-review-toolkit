"""Bounded incremental retention of requested LF-addressed text spans only."""

from __future__ import annotations

from dataclasses import dataclass, field

from ocr_toolkit.evidence.text_contracts import (
    MAX_EXCERPT_BYTES,
    MAX_EXCERPT_CHARS,
    MAX_EXCERPT_SOURCE_CHARS,
    MAX_EXCERPT_SPAN_LINES,
    MAX_SYNTAX_CHARS,
    RepositoryTextExcerpt,
    TextSpan,
    normalize_fragment,
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
        offsets = [0]
        for part in parts[:-1]:
            offsets.append(offsets[-1] + len(part) + 1)
        events: dict[int, list[tuple[int, _Capture, bool]]] = {}
        for rank, ((start, end), capture) in enumerate(self._spans.items()):
            if capture.limited or end < first_line or start > last_line:
                continue
            left = offsets[max(0, start - first_line)]
            right = offsets[end - first_line + 1] - 1 if end < last_line else len(text)
            if left < right:
                events.setdefault(left, []).append((rank, capture, True))
                events.setdefault(right, []).append((rank, capture, False))
        active: dict[int, _Capture] = {}
        previous = 0
        for position in sorted(events):
            if active and position > previous:
                self._append(text[previous:position], active)
            for rank, capture, opening in events[position]:
                if opening and not capture.limited:
                    active[rank] = capture
                else:
                    active.pop(rank, None)
            previous = position

    def _discard(self, capture: _Capture) -> None:
        self.used_bytes -= capture.bytes
        capture.parts.clear()
        capture.chars = capture.bytes = 0
        capture.limited = True

    def _retain(self, capture: _Capture, text: str, size: int) -> None:
        capture.parts.append(text)
        capture.chars += len(text)
        capture.bytes += size
        self.used_bytes += size

    def _append(self, text: str, active: dict[int, _Capture]) -> None:
        """Allocate at source positions, batching prefixes that cannot hit a limit."""

        offset = 0
        while active and offset < len(text):
            captures = tuple(active.values())
            chars = min(MAX_EXCERPT_SOURCE_CHARS - item.chars for item in captures)
            room = min(
                (self._max_bytes - self.used_bytes) // len(captures),
                *(MAX_EXCERPT_BYTES - item.bytes for item in captures),
            )
            prefix = text[offset : offset + chars]
            encoded = prefix.encode("utf-8")
            if len(encoded) > room:
                prefix = encoded[:room].decode("utf-8", errors="ignore")
                encoded = prefix.encode("utf-8")
            if prefix:
                for capture in captures:
                    self._retain(capture, prefix, len(encoded))
                offset += len(prefix)
            if offset == len(text):
                break
            # Completed spans keep their reservation. At a limit, process one
            # source character and evict lower-priority active spans first;
            # allocation cannot depend on OS pipe boundaries. Usual reads batch.
            character = text[offset]
            size = len(character.encode("utf-8"))
            ranks = sorted(active)
            victims = ranks.copy()
            for rank in ranks:
                capture = active.get(rank)
                if capture is None:
                    continue
                if (
                    capture.chars == MAX_EXCERPT_SOURCE_CHARS
                    or size > MAX_EXCERPT_BYTES - capture.bytes
                ):
                    self._discard(active.pop(rank))
                    continue
                while rank in active and size > self._max_bytes - self.used_bytes:
                    while victims[-1] not in active:
                        victims.pop()
                    self._discard(active.pop(victims.pop()))
                if rank in active:
                    self._retain(capture, character, size)
            offset += 1

    def finish(self, line_count: int) -> tuple[RepositoryTextExcerpt, ...]:
        result = []
        for (start, end), capture in self._spans.items():
            text = None if capture.limited or end > line_count else "".join(capture.parts)
            if text is not None and len(normalize_fragment(text)) > MAX_EXCERPT_CHARS:
                text = None
                self._discard(capture)
            result.append(
                RepositoryTextExcerpt(
                    start,
                    end,
                    text,
                    "range" if end > line_count else "limit" if capture.limited else "none",
                )
            )
        return tuple(result)

    @property
    def source(self) -> str | None:
        return "".join(self._source) if self._source is not None else None
