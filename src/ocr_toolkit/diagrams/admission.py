"""Admit optional diagrams against final native identity, source spans and DLP."""

from __future__ import annotations

import html
import unicodedata
from collections.abc import Callable
from subprocess import TimeoutExpired

from ocr_toolkit.context.contracts import TextBudgets
from ocr_toolkit.context.dlp import HTML_COMMENT_RE, HTML_TAG_RE, ForbiddenMatcher, check_text
from ocr_toolkit.diagrams.collector import CollectorSnapshot
from ocr_toolkit.diagrams.contracts import (
    DiagramMode,
    DiagramReason,
    DiagramResult,
    DiagramState,
    DiagramSubmission,
    diagram_text_units,
)
from ocr_toolkit.review_range import ReviewRange


def admit_diagram(
    mode: DiagramMode,
    snapshot: CollectorSnapshot | None,
    *,
    review_range: ReviewRange | None,
    output_calls: int,
    read_source: Callable[[str], str | None],
    forbidden_matcher: ForbiddenMatcher,
    dlp_enabled: bool,
) -> DiagramResult:
    """Omit a complete diagram on any loss; never alter the finding outcome.

    The caller binds read_source to its already-proven immutable head. Locations
    establish mechanical source validity, never the truth of model semantics.
    """

    def result(
        state: DiagramState,
        reason: DiagramReason = "none",
        submission: DiagramSubmission | None = None,
    ) -> DiagramResult:
        return DiagramResult(mode, state, reason, submission, output_calls)

    if snapshot is None:
        return result("omitted-invalid", "unavailable")
    if snapshot.reason != "none":
        return result("omitted-invalid", snapshot.reason)
    if snapshot.submissions != output_calls:
        return result("omitted-invalid", "unavailable")
    if snapshot.submissions == 0:
        return result("not-generated")
    return admit_candidate(
        mode,
        snapshot.candidate,
        review_range=review_range,
        output_calls=output_calls,
        read_source=read_source,
        forbidden_matcher=forbidden_matcher,
        dlp_enabled=dlp_enabled,
    )


def admit_candidate(
    mode: DiagramMode,
    candidate: DiagramSubmission | None,
    *,
    review_range: ReviewRange | None,
    output_calls: int,
    read_source: Callable[[str], str | None],
    forbidden_matcher: ForbiddenMatcher,
    dlp_enabled: bool,
) -> DiagramResult:
    """Revalidate a typed candidate at production admission or later publication."""

    def result(
        state: DiagramState,
        reason: DiagramReason = "none",
        submission: DiagramSubmission | None = None,
    ) -> DiagramResult:
        return DiagramResult(mode, state, reason, submission, output_calls)

    if candidate is None or review_range is None or candidate.review_range != review_range:
        return result("omitted-invalid", "range")
    if candidate.diagram is None:
        return result("not-applicable")
    rejection = candidate_text_reason(
        candidate, forbidden_matcher=forbidden_matcher, dlp_enabled=dlp_enabled
    )
    if rejection is not None:
        return result("omitted-invalid", rejection)
    source_lines: dict[str, int | None] = {}
    for _text, references in diagram_text_units(candidate.diagram):
        for reference in references:
            if reference.path not in source_lines:
                try:
                    source = read_source(reference.path)
                except (OSError, ValueError, UnicodeError, TimeoutExpired):
                    source = None
                source_lines[reference.path] = (
                    source.count("\n") + (0 if source.endswith("\n") else 1)
                    if source and "\x00" not in source
                    else None
                )
            count = source_lines[reference.path]
            if count is None or reference.end_line > count:
                return result("omitted-invalid", "reference")
    return result("generated", submission=candidate)


def candidate_text_reason(
    candidate: DiagramSubmission, *, forbidden_matcher: ForbiddenMatcher, dlp_enabled: bool
) -> DiagramReason | None:
    """Revalidate complete diagram text without mutation or fabricated source proof."""

    if candidate.diagram is None:
        return None
    for text, references in diagram_text_units(candidate.diagram):
        # Even an explicit DLP bypass does not turn diagram strings into raw
        # HTML, directives or multiple display lines. These are format rules.
        representation = text
        for _layer in range(3):
            if (
                HTML_TAG_RE.search(representation)
                or HTML_COMMENT_RE.search(representation)
                or "%%{" in representation
                or any(
                    unicodedata.category(c) in {"Cc", "Cf", "Cs", "Zl", "Zp"}
                    for c in representation
                )
            ):
                return "invalid"
            decoded = html.unescape(representation)
            if decoded == representation:
                break
            representation = decoded
        checked = check_text(
            text,
            budgets=TextBudgets(80, 320, 1),
            publication=True,
            forbidden_matcher=forbidden_matcher,
            enabled=dlp_enabled,
        )
        if not checked.admitted or checked.text != text:
            return "dlp"
        for reference in references:
            checked_path = check_text(
                reference.path,
                budgets=TextBudgets(512, 2048, 1),
                publication=True,
                forbidden_matcher=forbidden_matcher,
                enabled=dlp_enabled,
            )
            if not checked_path.admitted or checked_path.text != reference.path:
                return "dlp"
    return None
