"""Trusted project guidance handling for OCR review context."""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

from ocr_toolkit.common.redaction import redact_sensitive, redact_url_userinfo
from ocr_toolkit.context.repo import read_text, trusted_guidance_file
from ocr_toolkit.context.settings import MAX_INSTRUCTION_BYTES

GUIDANCE_KEYWORDS = (
    "ocr",
    "open code review",
    "review",
    "ci",
    "gitlab",
    "python",
    "secret",
    "redact",
    "security",
    "token",
    "markdown",
    "ansible",
)


def _sanitize_guidance_text(text: str) -> str:
    return redact_sensitive(redact_url_userinfo(text)).strip()


def read_project_instructions(
    limit_bytes: int = MAX_INSTRUCTION_BYTES,
    changed_paths: Sequence[str] | None = None,
) -> list[tuple[str, str]]:
    """Read bounded excerpts from stable project AI instruction files.

    Instruction files changed by the same MR are intentionally ignored. This
    prevents a merge request from changing reviewer guidance and using that new
    guidance to influence the review of itself.
    """

    instruction_files = [
        "PR_REVIEW.md",
        "AGENTS.md",
        "AGENTS.MD",
        "CLAUDE.md",
        "CLAUDE.MD",
        ".cursorrules",
        ".github/copilot-instructions.md",
    ]

    changed_set = {path.casefold() for path in changed_paths or []}
    excerpts: list[tuple[str, str]] = []
    seen_instruction_files: set[tuple[int, int] | Path] = set()
    remaining = limit_bytes

    for rel_path in instruction_files:
        if rel_path.casefold() in changed_set:
            continue

        safe_path = trusted_guidance_file(rel_path)
        if safe_path is None or remaining <= 0:
            continue
        try:
            stat_result = safe_path.stat()
            instruction_key: tuple[int, int] | Path = (
                stat_result.st_dev,
                stat_result.st_ino,
            )
        except OSError:
            instruction_key = safe_path
        if instruction_key in seen_instruction_files:
            continue
        seen_instruction_files.add(instruction_key)

        scan_budget = max(MAX_INSTRUCTION_BYTES, min(128_000, limit_bytes * 4))
        raw_text = _sanitize_guidance_text(read_text(safe_path, max_bytes=scan_budget))
        if not raw_text:
            continue

        text = selected_instruction_excerpt(
            rel_path,
            raw_text,
            max_bytes=min(remaining, 8_000),
        )
        if not text:
            continue

        excerpts.append((rel_path, text))
        remaining -= len(text.encode("utf-8", errors="ignore"))

    return excerpts


def selected_instruction_excerpt(rel_path: str, text: str, max_bytes: int) -> str:
    """Return a useful bounded excerpt from arbitrary trusted guidance text."""

    if max_bytes <= 0 or not text.strip():
        return ""
    if Path(rel_path).name.lower() not in {"agents.md", "claude.md"}:
        return read_text_slice(text, max_bytes=max_bytes)
    if len(text.encode("utf-8")) <= max_bytes:
        return text.strip()

    pieces: list[str] = []
    used: set[str] = set()
    added_relevant_candidate = False
    first_slice = read_text_slice(text, max_bytes=max(1, min(1_000, max_bytes // 4)))
    if first_slice:
        pieces.append(first_slice)
        used.add(first_slice)

    for candidate in _rank_guidance_candidates(text):
        if not candidate or candidate in used:
            continue
        current = _join_instruction_pieces(pieces)
        separator = "\n\n---\n\n" if current else ""
        remaining = max_bytes - len((current + separator).encode("utf-8"))
        if remaining <= 0:
            break
        clipped = read_text_slice(candidate, max_bytes=remaining)
        if not clipped:
            continue
        pieces.append(clipped)
        used.add(candidate)
        added_relevant_candidate = True
        if len(_join_instruction_pieces(pieces).encode("utf-8")) >= max_bytes:
            break

    if not added_relevant_candidate:
        return read_text_slice(text, max_bytes=max_bytes)
    return read_text_slice(
        _join_instruction_pieces(pieces) if pieces else text, max_bytes=max_bytes
    )


def _join_instruction_pieces(pieces: Sequence[str]) -> str:
    return "\n\n---\n\n".join(piece.strip() for piece in pieces if piece.strip())


def _rank_guidance_candidates(text: str) -> list[str]:
    sections = _heading_sections(text)
    if sections:
        preamble = text[: text.find(sections[0][1])].strip()
        scored_sections = [
            (_guidance_score(title, body), index, body)
            for index, (title, body) in enumerate(sections)
        ]
        if preamble:
            scored_sections.append((_guidance_score("", preamble), -1, preamble))
        return [
            _heading_guidance_candidate(body)
            for score, _index, body in sorted(scored_sections, key=lambda item: (-item[0], item[1]))
            if score > 0
        ]

    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    scored_paragraphs = [
        (_guidance_score("", paragraph), index, _keyword_window(paragraph))
        for index, paragraph in enumerate(paragraphs)
    ]
    return [
        paragraph
        for score, _index, paragraph in sorted(
            scored_paragraphs, key=lambda item: (-item[0], item[1])
        )
        if score > 0
    ]


def _heading_guidance_candidate(text: str) -> str:
    """Keep heading-section context while preserving deep keyword rules."""

    window = _keyword_window(text)
    prefix = read_text_slice(text, max_bytes=40).strip()
    if not prefix or window == text or text.startswith(window):
        return text
    return _join_instruction_pieces([prefix, window])


def _keyword_window(text: str, radius: int = 500) -> str:
    """Return a bounded window around the first guidance keyword."""

    positions: list[int] = []
    for keyword in GUIDANCE_KEYWORDS:
        if " " in keyword:
            match = re.search(re.escape(keyword), text, flags=re.IGNORECASE)
            if match:
                positions.append(match.start())
            continue
        match = re.search(
            rf"(?<![a-z0-9]){re.escape(keyword)}(?![a-z0-9])",
            text,
            flags=re.IGNORECASE,
        )
        if match:
            positions.append(match.start())
    if not positions:
        return text
    position = min(positions)
    newline_position = text.rfind("\n", 0, position)
    start = newline_position + 1 if newline_position >= 0 else max(0, position - radius)
    end = min(len(text), position + radius)
    return text[start:end].strip()


def _heading_sections(text: str) -> list[tuple[str, str]]:
    """Split Markdown-ish guidance by any heading level."""

    matches = list(re.finditer(r"(?m)^(#{1,6})\s+(.+?)\s*$", text))
    sections: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        title = match.group(2).strip()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections.append((title, text[match.start() : end].strip()))
    return sections


def _guidance_score(title: str, body: str) -> int:
    haystack = f"{title}\n{body}".casefold()
    score = 0
    for keyword in GUIDANCE_KEYWORDS:
        keyword_text = keyword.casefold()
        if " " in keyword_text:
            score += haystack.count(keyword_text)
            continue
        score += len(
            re.findall(
                rf"(?<![a-z0-9]){re.escape(keyword_text)}(?![a-z0-9])",
                haystack,
            )
        )
    return score


def read_text_slice(text: str, max_bytes: int) -> str:
    """Return a UTF-8 byte-bounded text slice without adding notices."""

    if max_bytes <= 0:
        return ""
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text
    return encoded[:max_bytes].decode("utf-8", errors="ignore").rstrip()


def read_accepted_decisions(
    changed_paths: Sequence[str] | None = None,
    max_bytes: int = MAX_INSTRUCTION_BYTES,
) -> str:
    """Return the contents of `.opencodereview/accepted-decisions.md`.

    This file lists project decisions the reviewer should not raise as
    new issues (e.g. a known but accepted security tradeoff). If the
    file is part of the current merge request's changed paths, it is
    ignored — otherwise an MR could whitelist its own findings.
    """

    rel_path = ".opencodereview/accepted-decisions.md"
    if rel_path.casefold() in {path.casefold() for path in changed_paths or []}:
        return ""

    path = trusted_guidance_file(rel_path)
    if path is None:
        return ""

    return _sanitize_guidance_text(read_text(path, max_bytes=max_bytes))
