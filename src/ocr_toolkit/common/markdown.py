"""Markdown formatting helpers for OCR CI output."""

from __future__ import annotations

import re
import unicodedata

SAFE_CODE_BLOCK_LANGUAGE_RE = re.compile(r"^[A-Za-z0-9_+.#-]{1,40}$")
FENCE_LINE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})([^\n]*)$")


def markdown_fence_transition(line: str, open_fence: str | None) -> tuple[str | None, bool]:
    """Return updated fenced-code marker and whether this line is a fence."""

    match = FENCE_LINE_RE.match(line)
    if not match:
        return open_fence, False

    fence = match.group(1)
    suffix = match.group(2)
    marker = fence[0]
    if open_fence is None:
        if marker == "`" and "`" in suffix:
            return open_fence, False
        return marker * len(fence), True

    if marker != open_fence[0] or len(fence) < len(open_fence):
        return open_fence, False
    if suffix.strip():
        return open_fence, False
    return None, True


def open_markdown_fence(markdown: str) -> str | None:
    """Return the currently open CommonMark fenced-code marker, if any."""

    open_fence: str | None = None
    for line in markdown.splitlines():
        open_fence, _ = markdown_fence_transition(line, open_fence)
    return open_fence


def neutralize_suggestion_fences(text: str) -> str:
    """Prevent OCR-controlled prose from creating GitLab suggestion blocks."""

    neutralized: list[str] = []
    for raw_line in text.splitlines(keepends=True):
        line = raw_line.rstrip("\r\n")
        line_ending = raw_line[len(line) :]
        stripped = line.lstrip(" ")
        indent = line[: len(line) - len(stripped)]
        match = FENCE_LINE_RE.match(line)
        if (
            len(indent) <= 3
            and match
            and match.group(1).startswith("`")
            and "`" not in match.group(2)
            and match.group(2).lstrip().lower().startswith("suggestion")
        ):
            neutralized.append(f"{indent}{match.group(1)}text{line_ending}")
        else:
            neutralized.append(raw_line)
    return "".join(neutralized)


def max_backtick_run(text: str) -> int:
    """Return the longest consecutive backtick run in text."""

    longest = 0
    current = 0

    for char in text:
        if char == "`":
            current += 1
            longest = max(longest, current)
        else:
            current = 0

    return longest


def escape_code_block_control_chars(value: str) -> str:
    """Escape invisible controls while preserving code-block layout."""

    escaped: list[str] = []
    for char in value:
        codepoint = ord(char)
        if char in {"\n", "\t"}:
            escaped.append(char)
            continue
        category = unicodedata.category(char)
        if category == "Cc":
            escaped.append(f"\\x{codepoint:02x}")
        elif category in {"Cf", "Zl", "Zp"}:
            if codepoint <= 0xFFFF:
                escaped.append(f"\\u{codepoint:04x}")
            else:
                escaped.append(f"\\U{codepoint:08x}")
        else:
            escaped.append(char)

    return "".join(escaped)


def markdown_code_block(language: str, content: str, escape_controls: bool = True) -> str:
    """Return a Markdown code block safe for embedded fences."""

    if escape_controls:
        content = escape_code_block_control_chars(content)

    fence_len = max(3, max_backtick_run(content) + 1)
    fence = "`" * fence_len
    lang = language.strip()
    if not SAFE_CODE_BLOCK_LANGUAGE_RE.fullmatch(lang):
        lang = ""

    closing_separator = "" if content.endswith("\n") else "\n"
    if lang:
        return f"{fence}{lang}\n{content}{closing_separator}{fence}"

    return f"{fence}\n{content}{closing_separator}{fence}"


def escape_control_chars(value: str) -> str:
    """Return text with control/format characters escaped for Markdown output.

    Unicode control characters (category ``Cc``), format controls
    (category ``Cf``), and Unicode line/paragraph separators (``Zl``/``Zp``)
    can make rendered Markdown differ from the underlying value. Keep ordinary
    printable Unicode unchanged.
    """

    escaped: list[str] = []
    for char in value:
        codepoint = ord(char)
        if char == "\n":
            escaped.append("\\n")
            continue
        elif char == "\r":
            escaped.append("\\r")
            continue
        elif char == "\t":
            escaped.append("\\t")
            continue
        category = unicodedata.category(char)
        if category == "Cc":
            escaped.append(f"\\x{codepoint:02x}")
        elif category in {"Cf", "Zl", "Zp"}:
            if codepoint <= 0xFFFF:
                escaped.append(f"\\u{codepoint:04x}")
            else:
                escaped.append(f"\\U{codepoint:08x}")
        else:
            escaped.append(char)

    return "".join(escaped)


def inline_code(value: str, escape_controls: bool = True) -> str:
    """Return a Markdown inline-code representation safe for backticks.

    Control/format escaping is the default because most callers render
    MR-controlled paths, CI values, manifest strings, or OCR output. Callers
    that render compile-time literal identifiers may opt out explicitly.

    An empty input is rendered as an italic ``_(unset)_`` so a missing
    branch name or commit SHA is visually obvious instead of collapsing
    into two adjacent backticks that GitLab renders ambiguously.
    """

    if not value:
        return "_(unset)_"

    if escape_controls:
        value = escape_control_chars(value)

    padded_span = bool(value.strip()) and value.startswith(" ") and value.endswith(" ")
    if "`" not in value and not padded_span:
        return f"`{value}`"

    fence = "`" * (max_backtick_run(value) + 1)
    return f"{fence} {value} {fence}"


def neutralize_quick_actions(text: str) -> str:
    """Prevent GitLab quick actions from executing in bot-created notes.

    GitLab treats lines starting with '/' as quick actions in comments.
    Prefix such lines with a backslash so the text remains readable but
    is not executed. This is a raw GitLab-note safety boundary, so it
    intentionally escapes slash-prefixed lines even inside Markdown code
    blocks rather than relying on GitLab quick-action parsing to honor
    the same Markdown boundaries as this local parser.
    """

    neutralized_lines: list[str] = []
    open_fence: str | None = None  # currently open fence marker, or None
    for raw_line in text.splitlines(keepends=True):
        line = raw_line.rstrip("\r\n")
        line_ending = raw_line[len(line) :]
        next_open_fence, is_fence = markdown_fence_transition(line, open_fence)
        if is_fence:
            open_fence = next_open_fence
            neutralized_lines.append(line + line_ending)
            continue

        stripped = line.lstrip()
        if stripped.startswith("/"):
            leading = line[: len(line) - len(stripped)]
            neutralized_lines.append(f"{leading}\\{stripped}{line_ending}")
        else:
            neutralized_lines.append(line + line_ending)

    return "".join(neutralized_lines)
