"""High-level OCR result posting workflow."""

from __future__ import annotations

import json
import os
import re
import secrets
import subprocess
import sys
from collections import Counter
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from ocr_toolkit.common.git import isolated_git_environment, read_only_git_prefix
from ocr_toolkit.common.markdown import markdown_code_block, neutralize_quick_actions
from ocr_toolkit.common.redaction import redact_sensitive
from ocr_toolkit.evidence.artifacts import repository_artifacts
from ocr_toolkit.ocr_result import (
    TOOLKIT_RESULT_KEY,
    OcrResultMalformed,
    OcrResultMissing,
    OcrResultTooLarge,
    load_ocr_result,
)
from ocr_toolkit.posting import gitlab as gitlab_api
from ocr_toolkit.posting.approval import (
    ApprovalEligibility,
    ApprovalResult,
    ApprovalStatus,
    evaluate_approval_policy,
    provisional_approval_result,
    publication_dlp_state,
)
from ocr_toolkit.posting.comments import (
    clean_text,
    code_text,
    comment_line,
    compact_escaped_text,
)
from ocr_toolkit.posting.formatting import (
    format_fallback_comment_chunks,
    format_inline_comment,
    format_mcp_usage_summary,
    format_omitted_comments_summary,
    format_publication_dlp_details,
    format_reviewer_guide,
    format_token_usage_summary,
    format_tool_calls_summary,
    inline_code,
    publication_dlp_signal,
    summarize_result,
)
from ocr_toolkit.posting.gitlab import (
    GitLabConfig,
    get_diff_refs,
    load_gitlab_config,
    post_review_discussion,
    post_review_note_bounded,
    publish_created_draft_notes,
    resolve_discussion,
    update_plain_note,
)
from ocr_toolkit.posting.gitlab_approval import ApprovalExecution, execute_approval
from ocr_toolkit.posting.markers import (
    SETUP_PENDING_MARKER,
    annotate_comment_fingerprints,
    build_summary_run_marker,
    is_own_bot_note,
)
from ocr_toolkit.posting.payloads import build_marked_note_body
from ocr_toolkit.posting.result import (
    llm_billing_failure_warnings,
    normalize_coverage_diagnostics,
)
from ocr_toolkit.posting.snapshot import (
    BotCommentRefs,
    cleanup_drafts_created_by_this_run,
    collect_previous_bot_comment_refs,
    delete_previous_bot_comments_if_collected,
    delete_previous_setup_notes,
    delete_previous_summary_notes,
    filter_previously_published_comments,
    filter_suppressed_comments,
    posting_failure_exit,
    print_posting_failure_banner,
    publish_failure_exit,
    rollback_current_run_comments,
)
from ocr_toolkit.posting.suggestions import (
    SuggestionDecision,
    evaluate_suggestion,
    safe_repository_path,
)
from ocr_toolkit.posting.transaction import PostingTransaction
from ocr_toolkit.pre_execution import (
    BACKGROUND_REASONS,
    PROTECTED_TARGET_RULE_PATH_PENDING,
    PreExecutionStatus,
    PreExecutionStatusError,
    read_pre_execution_status,
)
from ocr_toolkit.result_contract import OcrResultContractError, ReviewOutcome, parse_result_outcome

# Kept as a module-level compatibility seam for tests and external monkey-patching.
post_review_note = gitlab_api.post_review_note
from ocr_toolkit.posting.settings import (
    auto_approve,
    max_post_comments,
    ocr_exit_code,
    post_badges,
    post_emoji,
    post_mode,
    strict_posting,
)
from ocr_toolkit.review_runner import read_stderr_excerpt


def finalize_posting(config: GitLabConfig, transaction: PostingTransaction) -> bool:
    """Publish draft notes created by this script run."""

    return publish_created_draft_notes(config, transaction)


def inline_skip_reason(refs: dict[str, str] | None, path: str, line: int) -> str:
    """Return why an OCR comment cannot be posted inline before API posting."""

    if refs is None:
        return "missing_diff_refs"
    if not path:
        return "missing_path"
    if line <= 0:
        return "missing_line"
    return "unknown"


def reviewed_sha() -> str:
    """Return the commit SHA OCR was expected to review in CI."""

    source_sha = clean_text(os.environ.get("CI_MERGE_REQUEST_SOURCE_BRANCH_SHA", ""))
    if source_sha and not re.fullmatch(r"0+", source_sha):
        return source_sha
    return clean_text(os.environ.get("CI_COMMIT_SHA", ""))


def mr_head_sha() -> str:
    """Return the MR source-branch head SHA when GitLab provides it."""

    return clean_text(os.environ.get("CI_MERGE_REQUEST_SOURCE_BRANCH_SHA", ""))


def approval_receipt_identity(toolkit_metadata: Any) -> tuple[str, int | None]:
    """Return only validated-by-policy receipt identities for provider readback."""

    if not isinstance(toolkit_metadata, dict) or toolkit_metadata.get("schema_version") != 5:
        return "", None
    review = toolkit_metadata.get("review")
    if not isinstance(review, dict):
        return "", None
    source_sha = review.get("source_sha")
    author_id = review.get("mr_author_id")
    if not (
        isinstance(source_sha, str)
        and re.fullmatch(r"[0-9a-f]{40}", source_sha)
        and isinstance(author_id, int)
        and not isinstance(author_id, bool)
        and author_id > 0
    ):
        return "", None
    return source_sha, author_id


def summary_with_run_marker(body: str, run_id: str) -> str:
    """Attach one bounded hidden transaction identity to the summary."""

    return "\n".join((build_summary_run_marker(run_id), body))


def find_current_summary_note(config: GitLabConfig, run_id: str) -> int | None:
    """Find exactly one owned published summary for this posting transaction."""

    marker = build_summary_run_marker(run_id)
    notes = gitlab_api.api_get_paginated(
        config,
        "/notes?sort=desc&order_by=created_at",
        max_pages=50,
    )
    if notes is None:
        return None
    matches: list[int] = []
    for note in notes:
        if not isinstance(note, dict) or not is_own_bot_note(config, note, "body"):
            continue
        body = note.get("body")
        note_id = note.get("id")
        if (
            isinstance(body, str)
            and marker in body
            and isinstance(note_id, int)
            and not isinstance(note_id, bool)
            and note_id > 0
        ):
            matches.append(note_id)
    return matches[0] if len(matches) == 1 else None


def replace_current_summary(
    config: GitLabConfig,
    run_id: str,
    body: str,
) -> bool:
    """Update and read back one current summary without retrying the write."""

    note_id = find_current_summary_note(config, run_id)
    if note_id is None:
        print(
            "Cannot identify exactly one current OCR summary; "
            "leaving the published advisory review unchanged.",
            file=sys.stderr,
        )
        return False
    write = update_plain_note(config, note_id, body)
    if not write.posted:
        return False
    readback = gitlab_api.api_request(config, f"/notes/{note_id}", method="GET")
    return bool(
        isinstance(readback, dict)
        and is_own_bot_note(config, readback, "body")
        and readback.get("body") == build_marked_note_body(body)
    )


def finalize_review_approval(
    config: GitLabConfig,
    previous_refs: BotCommentRefs,
    outcome: ReviewOutcome,
    transaction: PostingTransaction,
    eligibility: ApprovalEligibility,
    reviewed_commit: str,
    reviewed_author_id: int | None,
    run_id: str,
    render_summary: Callable[[ApprovalResult], str],
) -> int:
    """Publish notes, manage exact-SHA approval, update summary, then clean old state."""

    if not finalize_posting(config, transaction):
        return publish_failure_exit(config, transaction)

    execution = execute_approval(
        config,
        eligibility,
        reviewed_commit,
        reviewed_author_id,
    )
    final_body = summary_with_run_marker(
        render_summary(execution.result),
        run_id,
    )
    provisional_body = summary_with_run_marker(
        render_summary(provisional_approval_result(eligibility)),
        run_id,
    )
    summary_updated = final_body == provisional_body or replace_current_summary(
        config,
        run_id,
        final_body,
    )
    if not summary_updated:
        execution = ApprovalExecution(
            ApprovalResult(
                ApprovalStatus.FAILED,
                "the published approval status could not be safely confirmed",
            ),
        )
        print(
            "Automatic approval summary update failed after review publication.",
            file=sys.stderr,
        )

    finalize_previous_review_state(config, previous_refs, outcome)
    if execution.result.status is ApprovalStatus.FAILED and strict_posting():
        return 1
    return 0


DiffLineCache = dict[tuple[str, str, str], set[int]]
FileLineCache = dict[tuple[str, str], list[tuple[int, str]]]
ChangedPathCache = dict[tuple[str, str], list[str]]
FileTextCache = dict[tuple[str, str], str | None]
MAX_CROSS_FILE_REMAP_PATHS = 200
MAX_REMAP_FILE_BYTES = 2_000_000
MAX_REMAP_DIFF_BYTES = 8_000_000


def _git_read_environment() -> dict[str, str]:
    """Return an isolated environment for untrusted-repository Git reads."""

    return isolated_git_environment()


def _git_read_prefix() -> list[str]:
    """Return Git arguments that disable repository-controlled hooks."""

    return read_only_git_prefix()


def changed_new_lines(
    refs: dict[str, str], path: str, cache: DiffLineCache | None = None
) -> set[int]:
    """Return changed new-file lines for a path from the reviewed Git diff."""

    cache_key = (refs["base_sha"], refs["head_sha"], path)
    if cache is not None and cache_key in cache:
        return cache[cache_key]

    try:
        result = subprocess.run(
            [
                *_git_read_prefix(),
                "diff",
                "--unified=0",
                refs["base_sha"],
                refs["head_sha"],
                "--",
                path,
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=_git_read_environment(),
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        lines: set[int] = set()
        if cache is not None:
            cache[cache_key] = lines
        return lines

    if result.returncode != 0:
        lines = set()
        if cache is not None:
            cache[cache_key] = lines
        return lines
    if len(result.stdout.encode("utf-8")) > MAX_REMAP_DIFF_BYTES:
        lines = set()
        if cache is not None:
            cache[cache_key] = lines
        return lines

    lines = set()
    for match in re.finditer(r"(?m)^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", result.stdout):
        start = int(match.group(1))
        length = int(match.group(2) or "1")
        if start <= 0 or length <= 0:
            continue
        lines.update(range(start, start + length))
    if cache is not None:
        cache[cache_key] = lines
    return lines


def changed_new_paths(refs: dict[str, str], cache: ChangedPathCache | None = None) -> list[str]:
    """Return changed new-file paths for the reviewed Git diff."""

    cache_key = (refs["base_sha"], refs["head_sha"])
    if cache is not None and cache_key in cache:
        return cache[cache_key]

    try:
        result = subprocess.run(
            [
                *_git_read_prefix(),
                "diff",
                "--name-only",
                "--diff-filter=ACMR",
                "-z",
                refs["base_sha"],
                refs["head_sha"],
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=_git_read_environment(),
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        paths: list[str] = []
        if cache is not None:
            cache[cache_key] = paths
        return paths
    if result.returncode != 0:
        paths = []
        if cache is not None:
            cache[cache_key] = paths
        return paths

    if len(result.stdout) > MAX_REMAP_DIFF_BYTES:
        paths = []
        if cache is not None:
            cache[cache_key] = paths
        return paths
    try:
        paths = sorted(path.decode("utf-8") for path in result.stdout.split(b"\0") if path)
    except UnicodeDecodeError:
        paths = []
    if cache is not None:
        cache[cache_key] = paths
    return paths


def head_file_lines(
    refs: dict[str, str], path: str, cache: FileLineCache | None = None
) -> list[tuple[int, str]]:
    """Return non-blank head file lines with original 1-based line numbers."""

    cache_key = (refs["head_sha"], path)
    if cache is not None and cache_key in cache:
        return cache[cache_key]

    try:
        size_result = subprocess.run(
            [*_git_read_prefix(), "cat-file", "-s", f"{refs['head_sha']}:{path}"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=_git_read_environment(),
            text=True,
            timeout=15,
        )
        if (
            size_result.returncode != 0
            or int(size_result.stdout.strip() or "0") > MAX_REMAP_FILE_BYTES
        ):
            lines: list[tuple[int, str]] = []
            if cache is not None:
                cache[cache_key] = lines
            return lines
        file_text = subprocess.run(
            [*_git_read_prefix(), "show", f"{refs['head_sha']}:{path}"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=_git_read_environment(),
            timeout=15,
        )
    except (OSError, ValueError, subprocess.SubprocessError):
        lines = []
        if cache is not None:
            cache[cache_key] = lines
        return lines
    if file_text.returncode != 0:
        lines = []
        if cache is not None:
            cache[cache_key] = lines
        return lines

    lines = [
        (line_number, line.rstrip())
        for line_number, line in enumerate(
            file_text.stdout.decode("utf-8", errors="replace").splitlines(), start=1
        )
        if line.strip()
    ]
    if cache is not None:
        cache[cache_key] = lines
    return lines


def head_file_text(
    refs: dict[str, str], path: str, cache: FileTextCache | None = None
) -> str | None:
    """Return one bounded UTF-8 head blob without consulting the worktree."""

    cache_key = (refs["head_sha"], path)
    if cache is not None and cache_key in cache:
        return cache[cache_key]
    if not safe_repository_path(path):
        if cache is not None:
            cache[cache_key] = None
        return None
    text: str | None = None
    try:
        size_result = subprocess.run(
            [*_git_read_prefix(), "cat-file", "-s", f"{refs['head_sha']}:{path}"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=_git_read_environment(),
            text=True,
            timeout=15,
        )
        size = int(size_result.stdout.strip() or "0")
        if size_result.returncode == 0 and 0 <= size <= MAX_REMAP_FILE_BYTES:
            result = subprocess.run(
                [*_git_read_prefix(), "show", f"{refs['head_sha']}:{path}"],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                env=_git_read_environment(),
                timeout=15,
            )
            if result.returncode == 0:
                text = result.stdout.decode("utf-8")
    except (OSError, UnicodeDecodeError, ValueError, subprocess.SubprocessError):
        text = None
    if cache is not None:
        cache[cache_key] = text
    return text


def unique_existing_code_line(
    refs: dict[str, str],
    path: str,
    comment: dict[str, Any],
    *,
    diff_line_cache: DiffLineCache | None = None,
    file_line_cache: FileLineCache | None = None,
) -> int:
    """Map existing_code to one changed line when the match is unambiguous."""

    existing = code_text(comment.get("existing_code")).strip("\n")
    if not existing:
        return 0
    needle = [line.rstrip() for line in existing.splitlines() if line.strip()]
    if not needle:
        return 0

    changed_lines = changed_new_lines(refs, path, diff_line_cache)
    if not changed_lines:
        return 0

    haystack = head_file_lines(refs, path, file_line_cache)
    if not haystack:
        return 0
    matches: list[int] = []
    width = len(needle)
    for index in range(0, max(0, len(haystack) - width + 1)):
        window = haystack[index : index + width]
        if [line_text for _, line_text in window] != needle:
            continue
        changed_anchor = next(
            (line_number for line_number, _ in window if line_number in changed_lines),
            0,
        )
        if changed_anchor > 0:
            matches.append(changed_anchor)
    return matches[0] if len(matches) == 1 else 0


def remap_existing_code_location(
    refs: dict[str, str],
    path: str,
    comment: dict[str, Any],
    *,
    diff_line_cache: DiffLineCache,
    file_line_cache: FileLineCache,
    changed_path_cache: ChangedPathCache,
) -> tuple[str, int]:
    """Map an anchorless OCR finding to one changed path and line when unambiguous."""

    if path:
        line = unique_existing_code_line(
            refs,
            path,
            comment,
            diff_line_cache=diff_line_cache,
            file_line_cache=file_line_cache,
        )
        if line > 0:
            return path, line
        return path, 0

    candidate_paths = changed_new_paths(refs, changed_path_cache)
    if len(candidate_paths) > MAX_CROSS_FILE_REMAP_PATHS:
        return path, 0

    matches: list[tuple[str, int]] = []
    for candidate_path in candidate_paths:
        if candidate_path == path:
            continue
        line = unique_existing_code_line(
            refs,
            candidate_path,
            comment,
            diff_line_cache=diff_line_cache,
            file_line_cache=file_line_cache,
        )
        if line > 0:
            matches.append((candidate_path, line))
            if len(matches) > 1:
                break

    return matches[0] if len(matches) == 1 else (path, 0)


def post_results(config: GitLabConfig, result: dict[str, Any]) -> int:
    """Post OCR result comments to GitLab and return a process exit code."""

    if config.current_user_id is None:
        print(
            "Cannot resolve current GitLab user; refusing to publish OCR review notes.",
            file=sys.stderr,
        )
        print_posting_failure_banner()
        return 1

    toolkit_metadata = result.get(TOOLKIT_RESULT_KEY)
    publication = (
        toolkit_metadata.get("publication") if isinstance(toolkit_metadata, dict) else None
    )
    if toolkit_metadata is None:
        publication_state = "direct"
    elif isinstance(toolkit_metadata, dict) and toolkit_metadata.get("schema_version") == 5:
        publication_state = publication_dlp_state(publication)
    else:
        publication_state = None
    if publication_state is None:
        return invalid_ocr_schema_exit(
            config,
            "receipt v5 publication state is invalid",
            intro="OCR result publication policy state could not be validated.",
            title="**Open Code Review publication policy error**",
        )

    comments_value = result.get("comments", [])
    warnings_value = result.get("warnings", [])
    tool_calls_summary = format_tool_calls_summary(result.get("tool_calls"))
    mcp_usage_summary = format_mcp_usage_summary(result.get(TOOLKIT_RESULT_KEY))
    token_usage_summary = format_token_usage_summary(result)
    try:
        outcome = parse_result_outcome(result)
    except OcrResultContractError as exc:
        return invalid_ocr_schema_exit(config, str(exc))
    outcome_message = clean_text(result.get("message"))

    if not isinstance(comments_value, list):
        return invalid_ocr_schema_exit(config, "field 'comments' must be a list")
    if not isinstance(warnings_value, list):
        return invalid_ocr_schema_exit(config, "field 'warnings' must be a list")
    comments: list[dict[str, Any]] = []
    for index, comment in enumerate(comments_value):
        if not isinstance(comment, dict):
            return invalid_ocr_schema_exit(config, f"field 'comments[{index}]' must be an object")
        comments.append(comment)

    # Approval policy consumes the complete authoritative OCR finding set,
    # before reviewer suppression or the publication cap can hide a blocker.
    approval_comments = list(comments)

    warnings = warnings_value
    coverage_diagnostics = normalize_coverage_diagnostics(outcome, warnings)
    if outcome.kind == "failed":
        return post_manifest_failure(
            config,
            outcome,
            outcome_message,
            warnings,
            tool_calls_summary=tool_calls_summary,
            mcp_usage_summary=mcp_usage_summary,
            token_usage_summary=token_usage_summary,
        )

    billing_warnings = llm_billing_failure_warnings(warnings)
    if billing_warnings:
        print(
            "OCR reported an LLM provider billing/quota failure; refusing to publish normal review notes.",
            file=sys.stderr,
        )
        return post_llm_provider_failure(
            config,
            billing_warnings,
            tool_calls_summary=tool_calls_summary,
            mcp_usage_summary=mcp_usage_summary,
            token_usage_summary=token_usage_summary,
        )

    previous_bot_comment_refs = collect_previous_bot_comment_refs(config)
    transaction = PostingTransaction()
    if previous_bot_comment_refs is None:
        print(
            "Cannot collect previous OCR bot comments reliably; refusing to publish "
            "new OCR review notes so resolved, /ocr suppress, and /ocr resolve state is preserved.",
            file=sys.stderr,
        )
        print_posting_failure_banner()
        return 1 if strict_posting() else 0

    annotate_comment_fingerprints(comments)

    comments, suppressed_count = filter_suppressed_comments(comments, previous_bot_comment_refs)
    if suppressed_count:
        print(
            f"Suppressed {suppressed_count} OCR comment(s) at locations resolved or "
            "suppressed by the reviewer."
        )
    carried_forward_count = 0
    if publication_state == "publication-filtered":
        comments, carried_forward_count = filter_previously_published_comments(
            comments, previous_bot_comment_refs
        )
        if carried_forward_count:
            print(
                f"Preserved {carried_forward_count} matching finding(s) from the previous "
                "OCR review instead of publishing duplicates."
            )
    dlp_signal = publication_dlp_signal(publication, carried_forward_comments=carried_forward_count)
    dlp_details = format_publication_dlp_details(dlp_signal)
    if dlp_signal is not None:
        print(
            "OCR toolkit telemetry event: "
            + json.dumps(dlp_signal, sort_keys=True, separators=(",", ":"))
        )

    publishable_comment_count = len(comments)
    publish_limit = max_post_comments()
    omitted_count = max(0, publishable_comment_count - publish_limit)
    if omitted_count:
        print(
            f"Omitting {omitted_count} OCR comment(s) because OCR_MAX_POST_COMMENTS="
            f"{publish_limit}.",
            file=sys.stderr,
        )
        comments = comments[:publish_limit]

    emoji = post_emoji()
    badge_mode = post_badges()
    approval_setting = auto_approve()
    approval_eligibility = evaluate_approval_policy(
        approval_setting,
        outcome,
        approval_comments,
        warnings,
        omitted_count,
        result.get(TOOLKIT_RESULT_KEY),
    )
    summary_run_id = secrets.token_hex(16)
    receipt_sha, reviewed_author_id = approval_receipt_identity(result.get(TOOLKIT_RESULT_KEY))
    reviewed_commit = receipt_sha or reviewed_sha()
    reviewer_guide = format_reviewer_guide(
        comments,
        omitted_count,
        outcome_status="budget_exceeded" if outcome.budget_exceeded else outcome.kind,
        coverage_summary=outcome.coverage_summary,
    )

    if publishable_comment_count == 0:

        def render_no_comments_summary(approval_result: ApprovalResult) -> str:
            """Render the no-findings summary with one approval state."""

            return summarize_result(
                total=0,
                inline_count=0,
                fallback_count=0,
                warning_count=len(warnings),
                comments=(),
                tool_calls_summary=tool_calls_summary,
                mcp_usage_summary=mcp_usage_summary,
                token_usage_summary=token_usage_summary,
                publication_dlp_details=dlp_details,
                reviewer_guide=reviewer_guide,
                reviewed_sha=reviewed_commit,
                mr_head_sha=mr_head_sha(),
                outcome_status=("budget_exceeded" if outcome.budget_exceeded else outcome.kind),
                outcome_message=outcome_message,
                coverage_summary=outcome.coverage_summary,
                coverage_diagnostics=coverage_diagnostics,
                warnings=warnings,
                suppressed_count=suppressed_count,
                approval_result=approval_result,
                emoji=emoji,
            )

        body = summary_with_run_marker(
            render_no_comments_summary(provisional_approval_result(approval_eligibility)),
            summary_run_id,
        )
        response = post_review_note_bounded(
            config,
            "",
            body,
            transaction,
        )
        if response is None:
            print("Failed to create OCR no-comments note.", file=sys.stderr)
            return posting_failure_exit(config, previous_bot_comment_refs, transaction)
        return finalize_review_approval(
            config,
            previous_bot_comment_refs,
            outcome,
            transaction,
            approval_eligibility,
            reviewed_commit,
            reviewed_author_id,
            summary_run_id,
            render_no_comments_summary,
        )

    refs = get_diff_refs(config)
    inline_count = 0
    failed_comments: list[tuple[dict[str, Any], SuggestionDecision]] = []
    fallback_reasons: Counter[str] = Counter()
    diff_line_cache: DiffLineCache = {}
    file_line_cache: FileLineCache = {}
    changed_path_cache: ChangedPathCache = {}
    file_text_cache: FileTextCache = {}

    for raw_comment in comments:
        if not isinstance(raw_comment, dict):
            continue

        path = clean_text(raw_comment.get("path"))
        old_path = clean_text(raw_comment.get("old_path")) or None
        line = comment_line(raw_comment)
        if refs and line <= 0:
            remapped_path, remapped_line = remap_existing_code_location(
                refs,
                path,
                raw_comment,
                diff_line_cache=diff_line_cache,
                file_line_cache=file_line_cache,
                changed_path_cache=changed_path_cache,
            )
            if remapped_line > 0:
                path = remapped_path
                line = remapped_line
                raw_comment["path"] = remapped_path
                raw_comment["line"] = remapped_line
                old_path = None
                print(
                    "Inline posting remapped missing line from existing_code, "
                    f"path={path!r}, line={line!r}.",
                    file=sys.stderr,
                )

        suggestion_decision = evaluate_suggestion(
            raw_comment,
            path,
            lambda candidate_path: (
                head_file_text(refs, candidate_path, file_text_cache) if refs else None
            ),
        )
        if not refs or not path or line <= 0:
            reason = inline_skip_reason(refs, path, line)
            print(
                f"Inline posting skipped reason={reason}, path={path!r}, line={line!r}; "
                "will publish as fallback.",
                file=sys.stderr,
            )
            fallback_reasons[reason] += 1
            failed_comments.append((raw_comment, suggestion_decision))
            continue

        inline_result = post_review_discussion(
            config=config,
            path=path,
            line=line,
            body=format_inline_comment(
                raw_comment,
                suggestion_decision=suggestion_decision,
                emoji=emoji,
                badge_mode=badge_mode,
            ),
            refs=refs,
            transaction=transaction,
            fingerprint=clean_text(raw_comment.get("_ocr_fingerprint")) or None,
            old_path=old_path,
        )

        if inline_result.posted:
            inline_count += 1
        elif inline_result.invalid_position:
            print(
                f"Inline posting skipped reason=invalid_position, path={path!r}, line={line!r}; "
                "will publish as fallback.",
                file=sys.stderr,
            )
            fallback_reasons["invalid_position"] += 1
            failed_comments.append((raw_comment, suggestion_decision))
        else:
            print(
                f"Inline posting failed reason={inline_result.status}, "
                f"path={path!r}, line={line!r}; refusing fallback because only "
                "a definite invalid-position rejection permits fallback.",
                file=sys.stderr,
            )
            rollback_current_run_comments(config, previous_bot_comment_refs, transaction)
            print_posting_failure_banner()
            return 1

    if failed_comments:
        fallback_chunks = format_fallback_comment_chunks(
            failed_comments,
            emoji=emoji,
            badge_mode=badge_mode,
        )

        for index, fallback_chunk in enumerate(fallback_chunks, start=1):
            fallback_title = (
                f"**Open Code Review fallback comments ({index}/{len(fallback_chunks)})**"
            )
            fallback_body = (
                "Open Code Review found issues that could not be posted inline.\n\n"
                f"{fallback_chunk}"
            )

            fallback_response = post_review_note_bounded(
                config,
                fallback_title,
                fallback_body,
                transaction,
            )

            if fallback_response is None:
                print("Failed to create OCR fallback note.", file=sys.stderr)
                return posting_failure_exit(config, previous_bot_comment_refs, transaction)

    if omitted_count:
        omitted_response = post_review_note_bounded(
            config,
            "**Open Code Review omitted comments**",
            format_omitted_comments_summary(
                publishable_total=publishable_comment_count,
                publish_limit=publish_limit,
                omitted=omitted_count,
            ),
            transaction,
        )
        if omitted_response is None:
            print("Failed to create OCR omitted-comments note.", file=sys.stderr)
            return posting_failure_exit(config, previous_bot_comment_refs, transaction)

    def render_findings_summary(approval_result: ApprovalResult) -> str:
        """Render the findings summary with one approval state."""

        return summarize_result(
            total=len(comments),
            inline_count=inline_count,
            fallback_count=len(failed_comments),
            warning_count=len(warnings),
            comments=comments,
            omitted_count=omitted_count,
            tool_calls_summary=tool_calls_summary,
            mcp_usage_summary=mcp_usage_summary,
            token_usage_summary=token_usage_summary,
            publication_dlp_details=dlp_details,
            reviewer_guide=reviewer_guide,
            fallback_reasons=fallback_reasons,
            reviewed_sha=reviewed_commit,
            mr_head_sha=mr_head_sha(),
            outcome_status="budget_exceeded" if outcome.budget_exceeded else outcome.kind,
            outcome_message=outcome_message,
            coverage_summary=outcome.coverage_summary,
            coverage_diagnostics=coverage_diagnostics,
            warnings=warnings,
            suppressed_count=suppressed_count,
            approval_result=approval_result,
            emoji=emoji,
        )

    summary_response = post_review_note_bounded(
        config,
        "",
        summary_with_run_marker(
            render_findings_summary(provisional_approval_result(approval_eligibility)),
            summary_run_id,
        ),
        transaction,
    )

    if summary_response is None:
        print("Failed to create OCR summary note.", file=sys.stderr)
        return posting_failure_exit(config, previous_bot_comment_refs, transaction)

    approval_exit = finalize_review_approval(
        config,
        previous_bot_comment_refs,
        outcome,
        transaction,
        approval_eligibility,
        reviewed_commit,
        reviewed_author_id,
        summary_run_id,
        render_findings_summary,
    )

    print(
        f"Posted OCR comments: mode={post_mode()}, inline={inline_count}, "
        f"fallback={len(failed_comments)}, omitted={omitted_count}, "
        f"total={publishable_comment_count}"
    )
    return approval_exit


def finalize_previous_review_state(
    config: GitLabConfig,
    previous_refs: BotCommentRefs,
    outcome: ReviewOutcome,
) -> None:
    """Replace prior notes only after a complete outcome; preserve them for partial coverage."""

    if outcome.kind == "partial":
        print("OCR coverage is partial; preserving previous review comments until a complete run.")
        delete_previous_summary_notes(config, previous_refs)
    else:
        delete_previous_bot_comments_if_collected(config, previous_refs)
    resolve_requested_discussions(config, previous_refs)


def resolve_requested_discussions(
    config: GitLabConfig, previous_refs: BotCommentRefs | None
) -> None:
    """Resolve discussions marked with `/ocr resolve` after successful posting."""

    if previous_refs is None or not previous_refs.discussions_to_resolve:
        return

    resolved = 0
    for discussion_id in previous_refs.discussions_to_resolve:
        if resolve_discussion(config, discussion_id):
            resolved += 1

    if resolved:
        print(f"Resolved {resolved} OCR discussion(s) per /ocr resolve reply.")


def invalid_ocr_schema_exit(
    config: GitLabConfig,
    message: str,
    intro: str = "OCR produced valid JSON that does not match the expected review schema.",
    title: str = "**Open Code Review result schema error**",
) -> int:
    """Post a visible OCR result artifact error without replacing old review notes."""

    print(f"OCR result schema error: {message}", file=sys.stderr)
    transaction = PostingTransaction()
    safe_message = neutralize_quick_actions(clean_text(message))
    response = post_review_note_bounded(
        config,
        title,
        f"{neutralize_quick_actions(clean_text(intro))}\n\n"
        "- Normal review comments were not published.\n"
        "- Previous OCR review comments were preserved.\n"
        f"- Schema error: {inline_code(safe_message)}",
        transaction,
    )
    if response is None:
        print("Failed to create OCR schema-error note.", file=sys.stderr)
        return posting_failure_exit(config, None, transaction)

    if not finalize_posting(config, transaction):
        return publish_failure_exit(config, transaction)

    return 1 if strict_posting() else 0


def post_manifest_failure(
    config: GitLabConfig,
    outcome: ReviewOutcome,
    message: str,
    warnings: Sequence[Any],
    *,
    tool_calls_summary: str = "",
    mcp_usage_summary: str = "",
    token_usage_summary: str = "",
) -> int:
    """Post a manifest-declared run failure while preserving prior review notes."""

    transaction = PostingTransaction()
    body = summarize_result(
        total=0,
        inline_count=0,
        fallback_count=0,
        warning_count=len(warnings),
        tool_calls_summary=tool_calls_summary,
        mcp_usage_summary=mcp_usage_summary,
        token_usage_summary=token_usage_summary,
        outcome_status="failed",
        outcome_message=message,
        coverage_summary=outcome.coverage_summary,
        coverage_diagnostics=normalize_coverage_diagnostics(outcome, warnings),
        warnings=warnings,
        emoji=post_emoji(),
    )

    response = post_review_note_bounded(
        config,
        "",
        body,
        transaction,
    )
    if response is None:
        print("Failed to create OCR manifest-failure note.", file=sys.stderr)
        return posting_failure_exit(config, None, transaction)
    if not finalize_posting(config, transaction):
        return publish_failure_exit(config, transaction)
    return 1 if strict_posting() else 0


def post_llm_provider_failure(
    config: GitLabConfig,
    warnings: Sequence[str],
    tool_calls_summary: str = "",
    mcp_usage_summary: str = "",
    token_usage_summary: str = "",
) -> int:
    """Post a visible OCR provider failure and preserve previous review notes."""

    transaction = PostingTransaction()
    warning_items: list[str] = []
    for warning in warnings[:10]:
        safe_warning = compact_escaped_text(
            neutralize_quick_actions(redact_sensitive(warning)),
            1200,
        )
        if safe_warning:
            warning_items.append(f"- {safe_warning}")

    body_parts = [
        "OCR could not complete the review because the LLM provider reported a billing, quota, or balance failure.",
        "",
        "- Normal review comments were not published.",
        "- Previous OCR review comments were preserved.",
        "- Refill or rotate the LLM token, then rerun the pipeline.",
    ]
    if warning_items:
        body_parts.extend(["", "**Provider warnings:**", *warning_items])
    if tool_calls_summary:
        body_parts.extend(["", tool_calls_summary])
    if mcp_usage_summary:
        body_parts.append(mcp_usage_summary)
    if token_usage_summary:
        body_parts.append(token_usage_summary)

    response = post_review_note_bounded(
        config,
        "**Open Code Review provider failure**",
        "\n".join(body_parts),
        transaction,
    )
    if response is None:
        print("Failed to create OCR provider-failure note.", file=sys.stderr)
        cleanup_drafts_created_by_this_run(config, transaction)
        print_posting_failure_banner()
        return 1

    if not finalize_posting(config, transaction):
        return publish_failure_exit(config, transaction)

    print(
        "Open Code Review did not complete because the LLM provider reported a billing/quota failure.",
        file=sys.stderr,
    )
    return 1


def post_parse_error(config: GitLabConfig, stderr_path: Path) -> int:
    """Post a safe error note when OCR output is not valid JSON.

    Previous OCR bot notes are intentionally NOT cleaned up here: a parse
    error means the new review may be partial or misleading, so the last
    valid review must remain visible until a successful run replaces it.
    """

    transaction = PostingTransaction()
    details_enabled = os.environ.get("OCR_POST_ERROR_DETAILS") == "1"
    details = read_stderr_excerpt(stderr_path) if details_enabled else ""

    if details:
        parse_error_response = post_review_note_bounded(
            config,
            "**Open Code Review parse error**",
            "**Open Code Review failed to produce valid JSON.**\n\n"
            + neutralize_quick_actions(markdown_code_block("text", details)),
            transaction,
        )
    else:
        parse_error_response = post_review_note_bounded(
            config,
            "**Open Code Review parse error**",
            "**Open Code Review failed to produce valid JSON.** Check the CI job log.",
            transaction,
        )

    if parse_error_response is None:
        print("Failed to create OCR parse-error note.", file=sys.stderr)
        return posting_failure_exit(config, None, transaction)

    if not finalize_posting(config, transaction):
        return publish_failure_exit(config, transaction)

    return 1 if strict_posting() else 0


def post_ocr_failure(config: GitLabConfig, stderr_path: Path, exit_code: int) -> int:
    """Post a safe failure note when OCR exits with a non-zero status.

    A non-zero OCR exit code means the JSON output may be partial or misleading,
    so this script intentionally does not publish normal review comments.
    Previous OCR bot notes are intentionally NOT cleaned up here: the last
    valid review must remain visible until a successful run replaces it.

    A negative `exit_code` is the convention used by `main()` to flag a
    successful OCR run that produced no result artifact at all (so there
    is no real exit code to report); render that as "missing artifact"
    instead of a confusing negative number.
    """

    try:
        status_path = repository_artifacts().pre_execution_status
        source_sha = clean_text(os.environ.get("CI_MERGE_REQUEST_SOURCE_BRANCH_SHA", ""))
        diff_base_sha = clean_text(os.environ.get("CI_MERGE_REQUEST_DIFF_BASE_SHA", ""))
        status = read_pre_execution_status(
            status_path,
            expected_diff_base_sha=diff_base_sha,
            expected_source_sha=source_sha,
        )
    except (OSError, PreExecutionStatusError, RuntimeError):
        status = None
    if status is not None:
        return post_pre_execution_status(config, status)

    transaction = PostingTransaction()
    details_enabled = os.environ.get("OCR_POST_ERROR_DETAILS") == "1"
    details = read_stderr_excerpt(stderr_path) if details_enabled else ""

    if exit_code < 0:
        exit_code_line = "- OCR result file was missing on disk."
    else:
        exit_code_line = f"- OCR exit code: `{exit_code}`"

    body = (
        f"**Open Code Review did not complete successfully.**\n\n"
        f"{exit_code_line}\n"
        "- Normal review comments were not published because the result may be partial or misleading.\n"
        "- Previous OCR review comments were preserved."
    )

    if details:
        body += "\n\n" + neutralize_quick_actions(markdown_code_block("text", details))

    response = post_review_note_bounded(
        config,
        "**Open Code Review failure**",
        body,
        transaction,
    )
    if response is None:
        print("Failed to create OCR failure note.", file=sys.stderr)
        return posting_failure_exit(config, None, transaction)

    if not finalize_posting(config, transaction):
        return publish_failure_exit(config, transaction)

    return 1 if strict_posting() else 0


def post_pre_execution_status(config: GitLabConfig, status: PreExecutionStatus) -> int:
    """Render static toolkit text for one already hostile-validated closed outcome."""

    if status.reason in BACKGROUND_REASONS:
        transaction = PostingTransaction()
        heading = (
            "**⛔ Open Code Review background was rejected**"
            if post_emoji()
            else "**Open Code Review background was rejected**"
        )
        unit = status.unit
        body = (
            "The installed, preflight-qualified OCR executable rejected the generated review "
            f"background before model execution: `{status.actual}` {unit} exceeded its current "
            f"hard limit of `{status.limit}` {unit}.\n\n"
            "No model review or review findings were produced. Previous Open Code Review "
            "comments were preserved."
        )
        response = post_review_note_bounded(config, heading, body, transaction)
        if response is None:
            print("Failed to create OCR background-rejection note.", file=sys.stderr)
            return posting_failure_exit(config, None, transaction)
        if not finalize_posting(config, transaction):
            return publish_failure_exit(config, transaction)
        return 1 if strict_posting() else 0
    if status.reason != PROTECTED_TARGET_RULE_PATH_PENDING:
        raise ValueError("unsupported pre-execution status")
    previous_refs = collect_previous_bot_comment_refs(config)
    if previous_refs is None:
        print("Cannot collect previous OCR setup notes reliably.", file=sys.stderr)
        return 1 if strict_posting() else 0
    transaction = PostingTransaction()
    heading = (
        "**⏳ Open Code Review setup is pending**"
        if post_emoji()
        else "**Open Code Review setup is pending**"
    )
    body = (
        "This merge request adds the repository rules file configured for Open Code Review. "
        "Open Code Review did not run because this file was not present in the protected-target "
        "commit captured for this pipeline. This is expected while the rules path is being "
        "introduced. Once valid rules are available at this path in the protected target branch, "
        "subsequent merge requests can run a full review.\n\n"
        "No review findings were produced. Previous Open Code Review comments were preserved."
    )
    response = post_review_note_bounded(
        config,
        heading,
        f"{SETUP_PENDING_MARKER}\n{body}",
        transaction,
    )
    if response is None:
        print("Failed to create OCR setup-pending note.", file=sys.stderr)
        return posting_failure_exit(config, None, transaction)
    if not finalize_posting(config, transaction):
        return publish_failure_exit(config, transaction)
    delete_previous_setup_notes(config, previous_refs)
    return 1 if strict_posting() else 0


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""

    args = argv if argv is not None else sys.argv[1:]
    # Defaults are per-job files in the isolated CI container; callers can override both.
    result_path = Path(args[0]) if len(args) >= 1 else Path("/tmp/ocr-result.json")  # nosec B108
    stderr_path = Path(args[1]) if len(args) >= 2 else Path("/tmp/ocr-stderr.log")  # nosec B108

    config = load_gitlab_config()
    if config is None:
        print(
            "GitLab posting configuration is missing or invalid; refusing to report success.",
            file=sys.stderr,
        )
        return 1
    if config.current_user_id is None:
        print(
            "Cannot resolve current GitLab user; refusing to publish any OCR notes.",
            file=sys.stderr,
        )
        print_posting_failure_banner()
        return 1

    exit_code = ocr_exit_code()
    if exit_code != 0:
        return post_ocr_failure(config, stderr_path, exit_code)

    try:
        result = load_ocr_result(result_path)
    except OcrResultMissing as exc:
        # OCR exited 0 but did not produce the result file at all —
        # treat as a failed run, not a parse error. The note text
        # comes from post_ocr_failure with a synthetic exit code so
        # the reviewer sees "did not complete successfully".
        print(f"OCR result file missing or unreadable: {exc}", file=sys.stderr)
        return post_ocr_failure(config, stderr_path, exit_code=-1)
    except OcrResultTooLarge as exc:
        print(f"OCR result file is too large: {exc}", file=sys.stderr)
        return invalid_ocr_schema_exit(
            config,
            str(exc),
            intro="OCR result artifact exceeded the configured safety limit before it could be parsed.",
            title="**Open Code Review result artifact error**",
        )
    except OcrResultMalformed as exc:
        print(f"Cannot parse OCR result JSON: {exc}", file=sys.stderr)
        return post_parse_error(config, stderr_path)

    if not isinstance(result, dict):
        print("OCR result JSON must be an object.", file=sys.stderr)
        return invalid_ocr_schema_exit(config, "top-level JSON value must be an object")

    return post_results(config, result)
