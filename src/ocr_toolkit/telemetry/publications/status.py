"""Recognize OCR-only publication headers and pre-model terminal statuses."""

import re
from typing import Any

from ocr_toolkit.posting.markers import MARKER, SUMMARY_RUN_MARKER_RE, WRITE_MARKER_RE

from .grammar import (
    OCR_EVIDENCE_ACTION_MAX_COUNT,
    OCR_FAILURE_STATUS_TYPES,
    OCR_FAILURE_TITLES,
    OCR_GITLINK_EMPTY_HEADING,
    OCR_LIMITED_COMMENT_ONLY,
    OCR_POLICY_FALLBACK_RE,
    OCR_PRE_MODEL_STATUSES,
    OCR_PREVIEW_STATUSES,
    OCR_PROVIDER_FAILURE_REASON_SET,
    OCR_PROVIDER_FAILURE_TITLE,
    OCR_REPOSITORY_COVERAGE_MAX,
    OCR_REPOSITORY_COVERAGE_RE,
    OCR_SETUP_AUTHORITIES,
    OCR_SUMMARY_HEADINGS,
    OCR_TERMINAL_MR_MARKER,
)

_SUMMARY_PREFIX = re.compile(
    r"\A(?:<!-- open-code-review-(?:bot|summary run=[A-Za-z0-9_-]{1,64}|write id=[0-9a-f]{32}) -->\n){0,3}"
)
_HISTORICAL_WRAPPER = re.compile(r"\A<p>[^<>\r\n]{1,256}</p>\n(?=<!-- open-code-review-bot -->\n)")
_TECHNICAL = re.compile(
    r"<details>\n<summary>Technical details</summary>\n((?:\n|- [^\n]+\n)*)</details>"
)
_SIGNAL_SPOILER_TITLES = {
    "<summary>DLP disabled: sensitive-data risk</summary>",
    "<summary>Private result sanitization signal</summary>",
    "<summary>Publication filtering signal</summary>",
}


def publication_body(body: str) -> str:
    """Remove leading producer markers without treating quoted markers as authority."""

    body = _HISTORICAL_WRAPPER.sub("", body, count=1)
    return _SUMMARY_PREFIX.sub("", body, count=1)


def has_summary_marker(body: str) -> bool:
    """Recognize a historical summary marker only in the leading producer block."""

    body = _HISTORICAL_WRAPPER.sub("", body, count=1)
    prefix = _SUMMARY_PREFIX.match(body)
    return bool(prefix and "<!-- open-code-review-summary " in prefix[0])


def has_current_summary_markers(body: str) -> bool:
    """Require the exact ownership and run marker order of a primary GitLab note."""

    marker, _, remainder = body.partition("\n")
    if marker != MARKER:
        return False
    summary, _, remainder = remainder.partition("\n")
    if WRITE_MARKER_RE.fullmatch(summary):
        summary, _, remainder = remainder.partition("\n")
    return SUMMARY_RUN_MARKER_RE.fullmatch(summary) is not None and remainder.startswith(
        "## Open Code Review\n\n"
    )


def metadata_sections(body: str) -> tuple[str, str | None, str]:
    """Separate visible legacy lines, top-level technical details and DLP markers."""

    visible: list[str] = []
    signals: list[str] = []
    technical: list[str] = []
    detail_lines: list[str] = []
    fence = ""
    details_depth = 0
    for line in body.splitlines():
        if delimiter := re.match(r"^ {0,3}(`{3,}|~{3,})", line):
            run = delimiter[1]
            if not fence:
                fence = run
            elif (
                run[0] == fence[0]
                and len(run) >= len(fence)
                and not line[delimiter.end() :].strip(" \t")
            ):
                fence = ""
            continue
        if fence or line.startswith((">", "    ", "\t")):
            continue
        if line in {"<details>", "<details open>"}:
            if details_depth == 0:
                detail_lines = []
            details_depth += 1
            detail_lines.append(line)
            continue
        if details_depth:
            detail_lines.append(line)
            if line == "</details>":
                details_depth -= 1
                if details_depth == 0:
                    if match := _TECHNICAL.fullmatch("\n".join(detail_lines)):
                        technical.append(match[1])
                    elif (
                        len(detail_lines) >= 3
                        and detail_lines[1] in _SIGNAL_SPOILER_TITLES
                        and not any(item.startswith("<details") for item in detail_lines[1:])
                    ):
                        signals.extend(
                            item
                            for item in detail_lines[2:]
                            if item.startswith("<!-- ocr-toolkit-signal ")
                        )
            continue
        if line.startswith("<!-- ocr-toolkit-signal "):
            signals.append(line)
        visible.append(line)
    technical_text = None if not technical else technical[0] if len(technical) == 1 else ""
    return "\n".join(visible), technical_text, "\n".join(signals)


def preview_status_body(body: str) -> str:
    """Read only a protected leading marker, with an optional producer write ID."""

    return re.sub(
        r"\A<!-- open-code-review-bot -->\n(?:<!-- open-code-review-write id=[0-9a-f]{32} -->\n)?",
        "",
        body,
    )


def is_ocr_summary(body: str) -> bool:
    """Recognize summary notes emitted by every released toolkit layout."""

    stripped = publication_body(body)
    if stripped.startswith(OCR_TERMINAL_MR_MARKER):
        return True
    if any(stripped.startswith(title) for title in OCR_FAILURE_TITLES):
        return True
    plain_heading = re.sub(r"^\*\*(?:[^A-Za-z\n]*)(Open Code Review[^*]+)\*\*.*", r"\1", stripped)
    if any(plain_heading.startswith(title) for title in OCR_PRE_MODEL_STATUSES):
        return True
    if any(preview_status_body(body).startswith(f"**{title}**") for title in OCR_PREVIEW_STATUSES):
        return True
    if preview_status_body(body).startswith(OCR_GITLINK_EMPTY_HEADING.removesuffix("**")):
        return True
    return (
        stripped.startswith(OCR_SUMMARY_HEADINGS[0])
        or stripped.split("\n", 1)[0] in OCR_SUMMARY_HEADINGS[1:]
        or stripped.startswith("**Open Code Review**\n\n")
        or has_summary_marker(body)
    )


def empty_ocr_result(outcome: str, layout: str, *, result_kind: str = "model") -> dict[str, Any]:
    """Return one normalized OCR result without structured review details."""

    return {
        "outcome": outcome,
        "recognized": True,
        "layout": layout,
        "result_kind": result_kind,
        "findings": None,
        "findings_reported": False,
        "model_started": False if result_kind in {"pre_model", "terminal_lifecycle"} else None,
        "severity": {},
        "categories": {},
        "posting": {},
        "coverage": {},
        "tool_calls": None,
        "tool_calls_by_name": {},
        "mcp": None,
        "federation": None,
        "legacy_context_policy": False,
        "completed_evidence_actions": None,
        "tokens": {},
        "publication_filter": None,
        "ocr_core_advisory": None,
        "reviewer_suppressed_findings": 0,
        "limited_comment_only": False,
        "review_mode": "unavailable",
        "review_mode_invalid": False,
        "repository_coverage": None,
        "repository_coverage_invalid": False,
        "terminal_lifecycle": None,
        "review_rejection": None,
    }


def ocr_canonical_header(body: str) -> re.Match[str] | None:
    """Require the producer header at the start, not in quoted report content."""
    header = re.match(
        r"\A(?:<!-- open-code-review-(?:bot|summary [^\r\n]*|write id=[0-9a-f]{32}) -->\n)*"
        r"## Open Code Review\n\n(?:✅ |🔎 |⚠️ |\N{INFORMATION SOURCE}\N{VARIATION SELECTOR-16} |❌ |⏭️ )?"
        r"\*\*(?:Review |Analysis complete; output incomplete — )[^\n]*\*\*(?:\n|$)",
        body.strip(),
    )
    return header


def ocr_summary_preamble(body: str) -> list[str]:
    """Read signal lines only before report content in a canonical summary."""
    header = ocr_canonical_header(body)
    if not header:
        return []
    lines = []
    for line in body.strip()[header.end() :].splitlines():
        if not line.strip():
            continue
        # Bound the preamble before findings, fences, technical details or prose.
        if not line.startswith(
            ("Repository coverage:", "*The target branch was not protected in GitLab.")
        ):
            break
        lines.append(line)
    return lines


def parse_ocr_repository_coverage(body: str) -> tuple[dict[str, Any] | None, bool]:
    """Parse only path-free published coverage; absence never proves full scope."""

    lines = ocr_summary_preamble(body)
    signals = [line for line in lines if line.startswith("Repository coverage:")]
    header = ocr_canonical_header(body)
    top_level = []
    if header:
        for line in body.strip()[header.end() :].splitlines():
            if line.startswith(("#", "<", "```", "~~~")):
                break
            if line.startswith("Repository coverage:"):
                top_level.append(line)
    if top_level != signals:
        return None, True
    if not signals:
        return None, False
    match = OCR_REPOSITORY_COVERAGE_RE.fullmatch(signals[0])
    if len(signals) != 1 or lines[0] != signals[0] or not match:
        return None, True
    completed, changed, gitlinks = map(int, match.groups())
    if (
        not 1 <= completed <= changed <= OCR_REPOSITORY_COVERAGE_MAX
        or gitlinks > OCR_REPOSITORY_COVERAGE_MAX
    ):
        return None, True
    return {
        "state": "partial",
        "ordinary_completed": completed,
        "ordinary_changed": changed,
        "gitlink_changes": gitlinks,
    }, False


def parse_ocr_review_mode(body: str) -> tuple[str, bool]:
    """Classify canonical policy lines independently of repository coverage."""

    signals = [
        line
        for line in ocr_summary_preamble(body)
        if line.startswith("*The target branch was not protected in GitLab.")
    ]
    if not signals:
        return "unavailable", False
    if len(signals) == 1:
        if OCR_POLICY_FALLBACK_RE.fullmatch(signals[0]):
            return "protected_default_fallback", False
        if signals[0] == OCR_LIMITED_COMMENT_ONLY:
            return "limited_comment_only", False
    return "unavailable", True


def parse_setup_authority(body: str) -> str:
    """Recognize exact public setup text pairs, leaving old normalized notes unknown."""

    for authority, (commit, destination) in OCR_SETUP_AUTHORITIES.items():
        text = (
            "This merge request adds the repository rules file configured for Open Code Review. "
            f"Open Code Review did not run because this file was not present in the {commit} "
            "captured for this pipeline. This is expected while the rules path is being "
            f"introduced. Once valid rules are available at this path in the {destination}, "
            "subsequent merge requests can run a full review.\n\n"
            "No review findings were produced. Previous Open Code Review comments were preserved."
        )
        if re.fullmatch(
            r"\*\*(?:⏳ )?Open Code Review setup is pending\*\*\n\n"
            r"<!-- open-code-review-setup-pending -->\n" + re.escape(text),
            preview_status_body(body).strip(),
        ):
            return authority
    return "unavailable"


def parse_ocr_review_rejection(body: str) -> dict[str, Any] | None:
    """Project one canonical published rejection; discard all stderr and coverage."""

    wrapper = re.fullmatch(
        r"(?:<!-- open-code-review-bot -->\n)?"
        r"\*\*Open Code Review failure\*\*\n\n"
        r"\*\*Open Code Review did not complete successfully\.\*\*\n\n"
        r"- OCR exit code: `[0-9]{1,10}`\n"
        r"- Normal review comments were not published because the result may be partial or misleading\.\n"
        r"- Previous OCR review comments were preserved\.\n\n"
        r"(?P<fence>`{3,})text\n(?P<details>.*?)\n(?P=fence)",
        body.strip(),
        re.DOTALL,
    )
    if not wrapper or body.count("Review rejected:") != 1:
        return None
    details = wrapper.group("details")
    if any(len(run) >= len(wrapper.group("fence")) for run in re.findall(r"`+", details)):
        return None
    lines = []
    nested_fence = None
    for line in details.split("\n"):
        fence = re.fullmatch(r"\s*(`{3,}|~{3,})[^\r\n]*", line)
        if fence:
            run = fence.group(1)
            if nested_fence is None:
                nested_fence = run
            elif run[0] == nested_fence[0] and len(run) >= len(nested_fence):
                nested_fence = None
        if line.startswith("Review rejected:"):
            if nested_fence is not None:
                return None
            lines.append(line)
    if len(lines) != 1:
        return None
    diagnostic = re.fullmatch(
        r"Review rejected: (?P<detail>required evidence use was not confirmed by OCR result telemetry"
        r"|mandatory evidence summary action attribution was not confirmed"
        r"|evidence action attribution was not confirmed) "
        r"\(reported calls: (?P<calls>unavailable|0|[1-9][0-9]{0,9}); "
        r"reason=(?P<reason>evidence-use-unconfirmed|evidence-action-attribution-invalid)\)\. "
        r"Result not accepted for publication or automatic approval\. "
        r"outcome=(?P<outcome>clean|warning|partial|failed|skipped)"
        r"(?:; Coverage: selected (?P<selected>0|[1-9][0-9]{0,4}); "
        r"completed (?P<completed>0|[1-9][0-9]{0,4}); "
        r"reused (?P<reused>0|[1-9][0-9]{0,4}); "
        r"failed (?P<failed>0|[1-9][0-9]{0,4}); "
        r"waived (?P<waived>0|[1-9][0-9]{0,4})\.)?",
        lines[0],
    )
    if not diagnostic:
        return None
    reason = diagnostic.group("reason")
    calls = None if diagnostic.group("calls") == "unavailable" else int(diagnostic.group("calls"))
    mandatory = diagnostic.group("outcome") in {"clean", "warning", "partial"}
    expected_detail = (
        "required evidence use was not confirmed by OCR result telemetry"
        if reason == "evidence-use-unconfirmed"
        else "mandatory evidence summary action attribution was not confirmed"
        if mandatory
        else "evidence action attribution was not confirmed"
    )
    if diagnostic.group("detail") != expected_detail:
        return None
    if calls is not None and calls > OCR_EVIDENCE_ACTION_MAX_COUNT:
        return None
    if reason == "evidence-use-unconfirmed" and (not mandatory or calls not in {None, 0}):
        return None
    if reason == "evidence-action-attribution-invalid" and (
        calls is None
        or (mandatory and calls == 0)
        or (diagnostic.group("outcome") == "skipped" and calls != 0)
    ):
        return None
    if diagnostic.group("selected") is not None:
        coverage = {
            key: int(diagnostic.group(key))
            for key in ("selected", "completed", "reused", "failed", "waived")
        }
        if max(coverage.values()) > 10_000 or coverage["selected"] != sum(
            coverage[key] for key in ("completed", "reused", "failed", "waived")
        ):
            return None
        outcome = diagnostic.group("outcome")
        if (
            outcome == "warning"
            or (outcome == "clean" and (not coverage["selected"] or coverage["failed"]))
            or (outcome == "partial" and not 0 < coverage["failed"] < coverage["selected"])
            or (outcome == "skipped" and coverage["selected"])
        ):
            return None
    return {"reason": reason, "reported_calls": calls}


def parse_status_note(body: str) -> dict[str, Any] | None:
    """Return the closed non-summary status when a dedicated note layout matches."""

    preview_body = preview_status_body(body)
    if preview_body.startswith(OCR_GITLINK_EMPTY_HEADING.removesuffix("**")):
        match = re.fullmatch(
            re.escape(OCR_GITLINK_EMPTY_HEADING)
            + r"\n\nReview not started: no ordinary files were selected; ([1-9][0-9]{0,4}) "
            r"changed gitlink pointer\(s\) remain unreviewed\. Ordinary files were not reviewed "
            r"in this run\. Previous review comments were preserved\.",
            preview_body.rstrip(),
        )
        if match and int(match[1]) <= OCR_REPOSITORY_COVERAGE_MAX:
            result = empty_ocr_result(
                "gitlink_no_reviewable_files",
                "gitlink_no_reviewable_files",
                result_kind="pre_model",
            )
            result["repository_coverage"] = {
                "state": "not_started",
                "gitlink_changes": int(match[1]),
            }
            return result
        result = empty_ocr_result("unknown", "unknown", result_kind="status")
        result["recognized"] = False
        return result
    for heading, (outcome, text) in OCR_PREVIEW_STATUSES.items():
        if preview_body.startswith(f"**{heading}**"):
            if preview_body.rstrip() == f"**{heading}**\n\n{text}":
                return empty_ocr_result(outcome, outcome, result_kind="pre_model")
            result = empty_ocr_result("unknown", "unknown")
            result["recognized"] = False
            return result
    stripped = publication_body(body)
    if stripped.startswith(OCR_TERMINAL_MR_MARKER):
        terminal_heading = re.search(
            r"\A<!-- open-code-review-terminal-merge-request -->\n\n?"
            r"\*\*(?:⏭️ )?Open Code Review skipped — merge request is already "
            r"(merged|closed)\*\*(?=\n|$)",
            stripped,
        )
        if terminal_heading:
            state = terminal_heading.group(1)
            result = empty_ocr_result(
                f"terminal_{state}", "terminal_merge_request", result_kind="terminal_lifecycle"
            )
            result["terminal_lifecycle"] = state
            return result
        result = empty_ocr_result(
            "unknown", "terminal_merge_request", result_kind="terminal_lifecycle"
        )
        result["recognized"] = False
        return result
    normalized_heading = re.sub(r"^\*\*[^A-Za-z\n]*(Open Code Review[^*]+)\*\*.*", r"\1", stripped)
    for heading, outcome in OCR_PRE_MODEL_STATUSES.items():
        if normalized_heading.split("\n", 1)[0] == heading:
            result = empty_ocr_result(outcome, outcome, result_kind="pre_model")
            if outcome == "setup_pending":
                result["setup_authority"] = parse_setup_authority(body)
            elif limits := re.search(
                r"`([0-9]{1,12})` (characters|bytes|tokens|files|records|entries)"
                r"(?:; the hard limit is| exceeded its current hard limit of)"
                r" `([0-9]{1,12})` \2\.",
                stripped,
            ):
                actual, limit = int(limits[1]), int(limits[3])
                if actual > limit:
                    result["pre_model_limit"] = {
                        "actual": actual,
                        "limit": limit,
                        "unit": limits[2],
                    }
            return result
    if stripped.startswith(OCR_PROVIDER_FAILURE_TITLE):
        result = empty_ocr_result("failed", "provider_failure", result_kind="provider_failure")
        reason_match = re.search(
            r"(?m)^- Safe classification: `([^`\r\n]+)`\.\s*$",
            stripped,
        )
        reason = reason_match.group(1) if reason_match else "unavailable"
        result["provider_failure_reason"] = (
            reason if reason in OCR_PROVIDER_FAILURE_REASON_SET else "unavailable"
        )
        return result
    for title, status_type in OCR_FAILURE_STATUS_TYPES.items():
        if stripped.startswith(title):
            result = empty_ocr_result("failed", "failure_note", result_kind="status")
            result["status_type"] = status_type
            if status_type == "failure":
                result["review_rejection"] = parse_ocr_review_rejection(body)
            return result
    return None
