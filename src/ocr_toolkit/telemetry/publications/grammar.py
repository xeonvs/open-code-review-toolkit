"""Bounded grammar for historical and current OCR publication signals."""

import re
from typing import Any

from ocr_toolkit.posting.markers import TERMINAL_MR_MARKER
from ocr_toolkit.result_contract import FORBIDDEN_SOURCE_CLASSES

OCR_TERMINAL_MR_MARKER = TERMINAL_MR_MARKER
OCR_PUBLICATION_DLP_SIGNAL_MARKER = "<!-- ocr-toolkit-signal "
OCR_PUBLICATION_DLP_SIGNAL_RE = re.compile(r"(?m)^<!-- ocr-toolkit-signal ([^\r\n]{1,16384}) -->$")
OCR_PUBLICATION_DLP_REASON_KEYS = {
    "forbidden",
    "invalid_text",
    "laundering",
    "limit",
    "pii",
    "secret",
}
OCR_PUBLICATION_DLP_SOURCE_KEYS = FORBIDDEN_SOURCE_CLASSES
OCR_PUBLICATION_DLP_MAX_COUNT = 1_000_000_000
OCR_FEDERATION_COUNTERS = (
    "attempted",
    "cache_hits",
    "completed",
    "denied",
    "dlp_rejected",
    "failed",
    "oversized",
    "single_flight",
    "timed_out",
)
OCR_FEDERATION_MAX_COUNT = 64
OCR_FEDERATION_MAX_OCR_ATTEMPTS = 1_000_000
OCR_PROVIDER_FAILURE_TITLE = "**Open Code Review provider failure**"
OCR_FAILURE_TITLES = (
    "**Open Code Review failure**",
    "**Open Code Review failed result**",
    OCR_PROVIDER_FAILURE_TITLE,
    "**Open Code Review parse error**",
    "**Open Code Review result artifact error**",
    "**Open Code Review result schema error**",
    "**Open Code Review publication policy error**",
)
OCR_FAILURE_STATUS_TYPES = {
    "**Open Code Review failure**": "failure",
    "**Open Code Review failed result**": "failed_result",
    "**Open Code Review parse error**": "parse_error",
    "**Open Code Review result artifact error**": "result_artifact_error",
    "**Open Code Review result schema error**": "result_schema_error",
    "**Open Code Review publication policy error**": "publication_policy_error",
}
OCR_PROVIDER_FAILURE_REASONS = (
    "authentication",
    "authorization",
    "rate-or-spending-limit",
    "overloaded",
    "timeout",
    "network",
    "endpoint-or-model-not-found",
    "request-rejected",
    "provider-unavailable",
    "invalid-response",
    "cancelled",
    "mixed",
    "unknown",
)
OCR_PROVIDER_FAILURE_REASON_SET = frozenset(OCR_PROVIDER_FAILURE_REASONS)
OCR_PRE_MODEL_STATUSES = {
    "Open Code Review background was rejected": "background_rejected",
    "Open Code Review evidence budget was exceeded": "evidence_budget_exceeded",
    "Open Code Review setup is pending": "setup_pending",
}
OCR_PREVIEW_STATUSES = {
    "Open Code Review preview could not cover a changed gitlink": (
        "gitlink_preview_unsupported",
        "Review not started: a changed Git submodule pointer cannot be safely covered "
        "by the installed OCR preview. Ordinary files were not reviewed in this run. "
        "Previous review comments were preserved.",
    ),
    "Open Code Review preview diagnostics could not be qualified": (
        "unclassified_preview_diagnostics",
        "Review not started: OCR preview diagnostics were unclassified. "
        "No model review was started. Check the job's closed preview status "
        "and installed OCR compatibility. Previous review comments were preserved.",
    ),
}
OCR_GITLINK_EMPTY_HEADING = "**Open Code Review: changed gitlinks remain unreviewed**"
OCR_REPOSITORY_COVERAGE_MAX = 20_000
OCR_REPOSITORY_COVERAGE_RE = re.compile(
    r"Repository coverage: partial; ([1-9][0-9]{0,4}) of ([1-9][0-9]{0,4}) "
    r"ordinary diff record\(s\) completed; ([1-9][0-9]{0,4}) "
    r"changed gitlink pointer\(s\) were not reviewed\."
)
OCR_FEDERATION_GATES = ("arguments", "result")
OCR_FEDERATION_REASONS = ("forbidden", "invalid_text", "limit", "pii", "secret")
OCR_SUMMARY_HEADINGS = (
    "**Open Code Review summary**",
    "# Open Code Review summary",
    "## Open Code Review",
)
OCR_EVIDENCE_ACTIONS = ("summary", "list", "get", "search", "coverage")
OCR_EVIDENCE_ACTION_MAX_COUNT = 1_000_000_000
OCR_MCP_KINDS = {
    "MCP used": "historical_usage",
    "verified MCP calls": "verified_calls",
    "reconciled MCP attempts": "reconciled_attempts",
}
OCR_LIMITED_COMMENT_ONLY = (
    "*The target branch was not protected in GitLab. "
    "This review ran in limited, comment-only mode.*"
)
OCR_POLICY_FALLBACK_RE = re.compile(
    r"\*The target branch was not protected in GitLab\. This review used a protected "
    r"policy anchor at `(?!0{40}`)[0-9a-f]{40}`; automatic approval was unavailable \(comment-only\)\.\*"
)
OCR_SETUP_AUTHORITIES = {
    "protected_target": ("protected-target commit", "protected target branch"),
    "protected_default_branch": (
        "protected default-branch policy commit",
        "protected default branch",
    ),
}
SEVERITIES = {"critical", "high", "medium", "low"}
OCR_CATEGORIES = {
    "bug",
    "security",
    "performance",
    "maintainability",
    "test",
    "documentation",
    "style",
    "other",
}
OCR_CORE_ADVISORY_MAX_COUNT = 999_999_999_999


def model_publication(row: dict[str, Any]) -> bool:
    """Identify recognized results from a review that ran the model."""

    return (
        row.get("recognized", True) is True
        and row.get("result_kind", "model") == "model"
        and row.get("model_started") is not False
        and row.get("outcome") not in ("skipped", "no_supported_files")
    )
