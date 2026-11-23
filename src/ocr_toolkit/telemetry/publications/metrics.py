"""Path-free finding, posting, coverage and presentation counters."""

import re
from collections import Counter
from typing import Any

from .grammar import (
    OCR_CATEGORIES,
    OCR_CORE_ADVISORY_MAX_COUNT,
    OCR_PUBLICATION_DLP_MAX_COUNT,
    SEVERITIES,
)
from .usage import named_counts


def finding_counts(
    status_text: str, visible: str, metrics_text: str
) -> tuple[int | None, dict[str, int]]:
    """Read published finding totals and the closed finding taxonomy."""

    findings_match = re.search(
        r"(?:Review[^\n]*?—\s+|Analysis complete; output incomplete — |\*\*)([0-9]{1,12}) findings? published",
        status_text,
        re.IGNORECASE,
    )
    if findings_match:
        findings = int(findings_match.group(1))
    else:
        legacy_findings = re.search(
            r"\*\*Open Code Review\*\* found \*\*([0-9]{1,12})\*\* issue(?:\(s\)|s)?",
            status_text,
            re.IGNORECASE,
        ) or re.search(r"\bFound\s+([0-9]{1,12})\s+issue(?:\(s\)|s)?", status_text, re.IGNORECASE)
        findings = int(legacy_findings.group(1)) if legacy_findings else None
    if findings is None and re.search(
        r"(?:—\s+no (?:new )?findings(?: published)?\b"
        r"|\bNo (?:review )?comments generated\b"
        r"|\bNo issues found\b)",
        status_text,
        re.IGNORECASE,
    ):
        findings = 0
    counts: Counter[str] = Counter()
    findings_section = visible.split("\n### Findings\n", 1)
    if len(findings_section) == 2:
        section = re.split(r"\n(?:#{2,}\s|<details>)", findings_section[1], maxsplit=1)[0]
        for label, count in re.findall(r"-\s+[^`\n]*`([^`]+)`: ([0-9]{1,12})", section):
            key = label.lower()
            if key in SEVERITIES | OCR_CATEGORIES:
                counts[key] += int(count)
    else:
        for kind in ("severity", "category"):
            match = re.search(rf"(?m)^- {kind} tags: ([^\n]+)$", metrics_text, re.IGNORECASE)
            if match:
                for label, count in re.findall(r"`([^`]+)`: ([0-9]{1,12})", match.group(1)):
                    key = label.lower()
                    if key in SEVERITIES | OCR_CATEGORIES:
                        counts[key] += int(count)

    return findings, dict(counts)


def posting_counts(
    metrics_text: str, *, canonical_status: bool
) -> tuple[dict[str, int], dict[str, int]]:
    """Read delivery counters and the terminal review-work partition."""

    def groups(pattern: str, names: tuple[str, ...]) -> dict[str, int]:
        matches = re.findall(pattern, metrics_text, re.M)
        if len(matches) != 1:
            return {}
        match = matches[0]
        return {name: int(value) for name, value in zip(names, match)}

    posting = groups(
        r"^- Posting: ([0-9]{1,12}) inline, ([0-9]{1,12}) fallback, ([0-9]{1,12}) (?:posting-stage )?omitted$",
        ("inline", "fallback", "omitted"),
    )
    if not posting and not canonical_status:
        inline_match = re.search(r"(?m)^- ([0-9]{1,12}) posted as inline discussion", metrics_text)
        fallback_match = re.search(
            r"(?m)^- ([0-9]{1,12}) posted as fallback summary item", metrics_text
        )
        omitted_match = re.search(
            r"(?m)^- ([0-9]{1,12}) omitted by `OCR_MAX_POST_COMMENTS`", metrics_text
        )
        posting = {
            key: int(match[1])
            for key, match in (
                ("inline", inline_match),
                ("fallback", fallback_match),
                ("omitted", omitted_match),
            )
            if match is not None
        }
    coverage = groups(
        r"^(?:- )?Coverage: selected ([0-9]{1,12}); completed ([0-9]{1,12}); reused ([0-9]{1,12}); failed ([0-9]{1,12}); waived ([0-9]{1,12})\.?$",
        ("selected", "completed", "reused", "failed", "waived"),
    )
    if coverage and coverage["selected"] != sum(
        coverage[name] for name in ("completed", "reused", "failed", "waived")
    ):
        coverage = {}
    return posting, coverage


def operational_signals(metrics_text: str, status_text: str) -> tuple[dict[str, Any], bool]:
    """Read closed lifecycle, suppression, migration and advisory facts."""

    context_policy_lines = re.findall(r"(?m)^- Context policy migration v1:[^\r\n]*$", metrics_text)
    legacy_context_policy = context_policy_lines == [
        "- Context policy migration v1: legacy policy; references not executed"
    ]
    invalid_context_policy = bool(context_policy_lines) and not legacy_context_policy
    advisory_prefixes = re.findall(r"(?m)^- OCR core advisory:[^\r\n]*$", metrics_text)
    advisory_matches = re.findall(
        r"(?m)^- OCR core advisory: background ([0-9]{1,12}) characters; recommended "
        r"([0-9]{1,12}) characters; accepted by OCR core\s*$",
        metrics_text,
    )
    ocr_core_advisory: dict[str, int] | None = None
    invalid_advisory = bool(advisory_prefixes) and not (
        len(advisory_prefixes) == len(advisory_matches) == 1
    )
    if advisory_matches:
        actual, recommended = (int(value) for value in advisory_matches[0])
        invalid_advisory = invalid_advisory or not (
            0 < recommended < actual <= OCR_CORE_ADVISORY_MAX_COUNT
        )
        if not invalid_advisory:
            ocr_core_advisory = {"actual": actual, "recommended": recommended}
    suppression_status_matches = re.findall(
        r"\b([0-9]{1,12}) findings? matched prior reviewer decisions\b",
        status_text,
        re.IGNORECASE,
    )
    suppression_detail_matches = re.findall(
        r"(?m)^- Reviewer suppression: ([0-9]{1,12})\s*$",
        metrics_text,
    )
    suppression_values = {
        int(value) for value in (*suppression_status_matches, *suppression_detail_matches)
    }
    invalid_reviewer_suppression = (
        len(suppression_status_matches) > 1
        or len(suppression_detail_matches) > 1
        or len(suppression_values) > 1
        or any(not 0 < value <= OCR_PUBLICATION_DLP_MAX_COUNT for value in suppression_values)
    )
    reviewer_suppressed_findings = (
        next(iter(suppression_values), 0) if not invalid_reviewer_suppression else 0
    )
    lifecycle_prefixes = re.findall(
        r"(?m)^- Merge request lifecycle at publication:[^\r\n]*$", metrics_text
    )
    lifecycle_matches = re.findall(
        r"(?m)^- Merge request lifecycle at publication: `(merged|closed)`; "
        r"result remains bound to (?:its reviewed revision|reviewed commit `[^`\r\n]+`)\s*$",
        metrics_text,
    )
    invalid_terminal_lifecycle = bool(lifecycle_prefixes) and not (
        len(lifecycle_prefixes) == len(lifecycle_matches) == 1
    )
    terminal_lifecycle = lifecycle_matches[0] if lifecycle_matches else None
    return {
        "legacy_context_policy": legacy_context_policy,
        "ocr_core_advisory": ocr_core_advisory,
        "reviewer_suppressed_findings": reviewer_suppressed_findings,
        "terminal_lifecycle": terminal_lifecycle,
    }, any(
        (
            invalid_context_policy,
            invalid_advisory,
            invalid_reviewer_suppression,
            invalid_terminal_lifecycle,
        )
    )


def presentation_signals(metrics_text: str, visible: str) -> dict[str, Any]:
    """Read renderer-owned status labels, without retaining explanatory text."""

    warning_section = re.search(r"(?m)^### Review warnings\n((?:\n|- [^\n]+\n?)*)", visible)
    warning_count = None
    if warning_section:
        warning_lines = [line for line in warning_section[1].splitlines() if line.startswith("- ")]
        more = (
            re.fullmatch(r"- \.\.\. and ([0-9]{1,12}) more warning\(s\)", warning_lines[-1])
            if warning_lines
            else None
        )
        warning_count = len(warning_lines) - int(bool(more)) + (int(more[1]) if more else 0)
    approval = re.findall(
        r"(?m)^- Automatic approval: `(approved|not eligible|disabled|skipped|failed)` — [^\n]+\.$",
        metrics_text,
    )
    posting_mode = re.findall(r"(?m)^- Review mode: `(draft|direct)`$", metrics_text)
    diagram_state = re.findall(
        r"(?m)^- Change diagram: `(disabled|unsupported|not-generated|not-applicable|generated|omitted-invalid)`(?: \([^\n]+\))?$",
        metrics_text,
    )
    fallback_matches = re.findall(r"(?m)^- Fallback reasons: ([^\n]+)$", metrics_text)
    _, fallback_reasons = named_counts(
        fallback_matches[0] if len(fallback_matches) == 1 else None,
        {"missing_diff_refs", "missing_path", "missing_line", "unknown", "invalid_position"},
    )
    return {
        "fallback_reasons": fallback_reasons,
        "posting_mode": posting_mode[0] if len(posting_mode) == 1 else None,
        "approval_state": approval[0] if len(approval) == 1 else None,
        "diagram_state": diagram_state[0] if len(diagram_state) == 1 else None,
        "warning_count": warning_count,
    }
