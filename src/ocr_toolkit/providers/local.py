"""Standalone local Markdown output; no forge acquisition, actions or posting policy."""

from __future__ import annotations

import os
import secrets
from collections.abc import Iterator
from pathlib import Path
from typing import TextIO

from ocr_toolkit.common.filesystem import (
    fsync_directory,
    open_private_parent_directory,
    same_file_identity,
)
from ocr_toolkit.common.markdown import inline_code, markdown_code_block
from ocr_toolkit.reporting.dlp import admission_dlp_state, format_dlp_admission
from ocr_toolkit.reporting.metadata import finding_metadata, format_ocr_core_advisory
from ocr_toolkit.reporting.model import ReviewReport
from ocr_toolkit.reporting.outcome import FindingVisibility, review_outcome_line
from ocr_toolkit.reporting.sections import report_sections
from ocr_toolkit.reporting.text import clean_text, code_text, comment_line


def local_summary(report: ReviewReport) -> str:
    """Render common facts, with neither forge publication claims nor remote badges."""

    lines = [
        "## Open Code Review",
        "",
        review_outcome_line(
            findings=FindingVisibility(count=len(report.comments)),
            warning_count=len(report.warnings),
            outcome_status=(
                "admission-filtered"
                if admission_dlp_state(report.publication) == "publication-filtered"
                and report.outcome.kind in {"clean", "warning"}
                else report.outcome.status
            ),
            outcome_message=report.outcome_message,
            unreviewed_file_count=report.diagnostics.file_count,
        ),
    ]
    if report.failure_stage is not None:
        lines.extend(
            [
                "",
                f"Stopped at: {inline_code(report.failure_stage, escape_controls=True)}.",
                "Findings, coverage and execution usage are unavailable or untrusted. "
                "See the diagnostic output for the blocking check.",
            ]
        )
    lines.extend(report_sections(report.comments, report.diagnostics, report.warnings))
    lines.extend(["", "### Technical details", "", "- Output: local Markdown"])
    if report.reviewed_sha:
        lines.append(f"- Reviewed commit: {inline_code(report.reviewed_sha, escape_controls=True)}")
    if report.outcome.coverage_summary:
        lines.append(f"- {report.outcome.coverage_summary}")
    for detail in (
        report.mcp_usage_summary,
        report.tool_calls_summary,
        report.token_usage_summary,
        format_ocr_core_advisory(report.advisory),
        format_dlp_admission(report.publication),
    ):
        if detail:
            lines.append(detail)
    return "\n".join(lines)


def local_report_parts(report: ReviewReport) -> Iterator[str]:
    """Yield every admitted finding without posting limits or executable markup."""

    yield local_summary(report)
    for ordinal, comment in enumerate(report.comments, 1):
        location = clean_text(comment.get("path")) or "unknown"
        line = comment_line(comment)
        if line:
            location += f":L{line}"
        tags = ", ".join(part for part in finding_metadata(comment) if part)
        header = f"### Finding {ordinal}: {inline_code(location, escape_controls=True)}"
        if tags:
            header += f" — {inline_code(tags)}"
        yield (
            "\n\n"
            + header
            + "\n\n"
            + markdown_code_block(
                "", clean_text(comment.get("content")) or "Open Code Review reported an issue here."
            )
        )
        for field, label in (
            ("existing_code", "Existing code"),
            ("suggestion_code", "Suggested code"),
        ):
            content = code_text(comment.get(field))
            if content:
                yield f"\n\n#### {label}\n\n" + markdown_code_block("", content)
    yield "\n"


def write_local_report(report: ReviewReport, stream: TextIO) -> None:
    """Write admitted output incrementally; the runner owns output failure handling."""

    for part in local_report_parts(report):
        stream.write(part)
    stream.flush()


def prepare_local_report_path(path: Path, *, other_outputs: tuple[Path, ...]) -> None:
    """Validate a fresh report destination without overwriting caller-owned data."""

    if path.resolve() in {output.resolve() for output in other_outputs}:
        raise ValueError("local report path must differ from result and stderr")
    if path.is_symlink() or path.exists():
        raise ValueError("local report path must be fresh")


def publish_local_report(report: ReviewReport, path: Path) -> None:
    """Publish complete private Markdown atomically without replacing another file."""

    prepare_local_report_path(path, other_outputs=())
    parent_descriptor, destination = open_private_parent_directory(path)
    temporary = ".ocr-report-" + secrets.token_hex(12)
    descriptor = -1
    temporary_identity: os.stat_result | None = None
    try:
        descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=parent_descriptor,
        )
        os.fchmod(descriptor, 0o600)
        temporary_identity = os.fstat(descriptor)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            descriptor = -1
            write_local_report(report, stream)
            os.fsync(stream.fileno())
        # Unlike replace(), link() rejects a destination created since preflight.
        current = os.stat(temporary, dir_fd=parent_descriptor, follow_symlinks=False)
        if not same_file_identity(temporary_identity, current) or current.st_nlink != 1:
            raise OSError("private report temporary artifact changed")
        os.link(
            temporary,
            destination,
            src_dir_fd=parent_descriptor,
            dst_dir_fd=parent_descriptor,
            follow_symlinks=False,
        )
        os.unlink(temporary, dir_fd=parent_descriptor)
        temporary_identity = None
        fsync_directory(parent_descriptor)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if temporary_identity is not None:
            try:
                current = os.stat(temporary, dir_fd=parent_descriptor, follow_symlinks=False)
                if same_file_identity(temporary_identity, current):
                    os.unlink(temporary, dir_fd=parent_descriptor)
            except FileNotFoundError:
                pass
        os.close(parent_descriptor)
