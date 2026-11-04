"""Bounded Git acquisition for a batch of already located posting suggestions."""

from pathlib import Path
from typing import Any

from ocr_toolkit.evidence.source_reader import SourceReadSession
from ocr_toolkit.evidence.text_contracts import TextSpan
from ocr_toolkit.posting.comments import clean_text
from ocr_toolkit.posting.suggestions import (
    SuggestionDecision,
    evaluate_suggestion,
    suggestion_source_request,
)


class SuggestionSourceReader:
    """Share immutable reads after remapping, without retaining full syntax."""

    def __init__(self, root: Path, head: str, comments: list[dict[str, Any]]) -> None:
        requests: dict[str, set[TextSpan]] = {}
        for comment in comments:
            path = clean_text(comment.get("path"))
            span = suggestion_source_request(comment, path)
            if span is not None:
                requests.setdefault(path, set()).add(span)
        try:
            self._session: SourceReadSession | None = SourceReadSession(
                root,
                head,
                {path: tuple(sorted(spans)) for path, spans in requests.items()},
                retain_syntax=False,
            )
        except (ValueError, OSError):
            self._session = None

    def evaluate(self, comment: dict[str, Any], path: str) -> SuggestionDecision:
        """Unavailable acquisition omits only the replacement, preserving its finding."""

        span = suggestion_source_request(comment, path)
        if self._session is not None and span is not None:
            result = self._session.read_excerpt(path, *span)
            if result.metadata is not None and result.metadata.excerpts:
                return evaluate_suggestion(
                    comment,
                    path,
                    excerpt=result.metadata.excerpts[0],
                    source_line_count=result.metadata.line_count,
                )
        return evaluate_suggestion(comment, path)
