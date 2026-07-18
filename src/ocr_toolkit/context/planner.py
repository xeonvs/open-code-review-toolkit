"""Budget and render generic review-context sections."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ocr_toolkit.common.markdown import markdown_fence_transition, open_markdown_fence


@dataclass(frozen=True)
class ContextSection:
    """One independently budgeted top-level Markdown section."""

    title: str
    body: str
    priority: int = 50
    minimum_bytes: int = 160

    def render(self) -> str:
        """Render the complete section without applying a budget."""

        return f"## {self.title}\n{self.body.strip()}\n"


def split_markdown_sections(markdown: str) -> tuple[str, list[ContextSection]]:
    """Split top-level Markdown sections without treating fenced headings as structure."""

    preamble: list[str] = []
    sections: list[ContextSection] = []
    title: str | None = None
    body: list[str] = []
    fence: str | None = None
    for line in markdown.splitlines():
        if fence is None and line.startswith("## "):
            if title is None:
                preamble = body
            else:
                sections.append(ContextSection(title=title, body="\n".join(body)))
            title = line[3:].strip()
            body = []
        else:
            body.append(line)
        fence, _ = markdown_fence_transition(line, fence)

    if title is None:
        preamble = body
    else:
        sections.append(ContextSection(title=title, body="\n".join(body)))
    return "\n".join(preamble).rstrip(), sections


def _truncate_section(section: ContextSection, max_bytes: int) -> str:
    """Render one section inside a byte budget while preserving Markdown fences."""

    heading = f"## {section.title}\n"
    marker = "\n- ... section truncated\n"
    heading_bytes = len(heading.encode("utf-8"))
    marker_bytes = len(marker.encode("utf-8"))
    body = section.body.strip()
    complete = heading + body + "\n"
    if len(complete.encode("utf-8")) <= max_bytes:
        return complete
    if max_bytes < heading_bytes + marker_bytes:
        return ""

    body_bytes = body.encode("utf-8")
    content_budget = max(0, max_bytes - heading_bytes - marker_bytes)
    reserved_closing_bytes = 0
    while True:
        body_budget = max(0, content_budget - reserved_closing_bytes)
        clipped = body_bytes[:body_budget].decode("utf-8", errors="ignore").rstrip()
        fence = open_markdown_fence(clipped)
        closing = f"\n{fence}" if fence else ""
        required = len(closing.encode("utf-8"))
        if required <= reserved_closing_bytes:
            break
        reserved_closing_bytes = required

    return heading + clipped + closing + marker


def _render_context_bytes(preamble: str, sections: Sequence[ContextSection], max_bytes: int) -> str:
    """Render context densely inside one strict UTF-8 byte budget."""

    if max_bytes <= 0:
        return ""

    clean_preamble = preamble.rstrip()
    preamble_bytes = len(clean_preamble.encode("utf-8"))
    if preamble_bytes >= max_bytes:
        return (clean_preamble + "\n").encode("utf-8")[:max_bytes].decode("utf-8", errors="ignore")
    if not sections:
        return clean_preamble + "\n"

    separator_bytes = 2 * (len(sections) - 1 + bool(clean_preamble))
    available = max_bytes - preamble_bytes - separator_bytes - 1
    rendered_sizes = [len(section.render().encode("utf-8")) for section in sections]
    minimums = [
        min(
            rendered_sizes[index],
            max(
                section.minimum_bytes,
                len(f"## {section.title}\n".encode()),
            ),
        )
        for index, section in enumerate(sections)
    ]
    minimum_total = sum(minimums)
    if minimum_total > available:
        minimums = [max(0, available * minimum // minimum_total) for minimum in minimums]

    allocations = list(minimums)
    remaining = max(0, available - sum(allocations))
    pending = {
        index
        for index, rendered_size in enumerate(rendered_sizes)
        if allocations[index] < rendered_size
    }
    while remaining > 0 and pending:
        total_weight = sum(max(1, sections[index].priority) for index in pending)
        progressed = False
        for index in sorted(pending):
            share = max(
                1,
                remaining * max(1, sections[index].priority) // total_weight,
            )
            addition = min(share, rendered_sizes[index] - allocations[index], remaining)
            if addition:
                allocations[index] += addition
                remaining -= addition
                progressed = True
            if allocations[index] >= rendered_sizes[index]:
                pending.discard(index)
            if not remaining:
                break
        if not progressed:
            break

    rendered = [clean_preamble] if clean_preamble else []
    rendered.extend(
        _truncate_section(section, allocation).rstrip()
        for section, allocation in zip(sections, allocations)
        if allocation > 0
    )
    result = "\n\n".join(rendered).rstrip() + "\n"
    if len(result.encode("utf-8")) > max_bytes:
        raise ValueError("context planner exceeded its byte allocation")
    return result


def render_context(
    preamble: str,
    sections: Sequence[ContextSection],
    max_bytes: int,
    *,
    max_chars: int | None = None,
) -> str:
    """Render context inside independent OCR character and file byte limits."""

    if max_chars is None:
        return _render_context_bytes(preamble, sections, max_bytes)
    if max_chars <= 0 or max_bytes <= 0:
        return ""

    selected = list(sections)
    clean_preamble = preamble.rstrip()
    minimum_char_cost = len(clean_preamble) + 1
    minimum_char_cost += 2 * (len(selected) - 1 + bool(clean_preamble))
    minimum_char_cost += sum(
        len(f"## {section.title}\n- ... section truncated\n") for section in selected
    )
    if minimum_char_cost > max_chars:
        ranked = sorted(
            enumerate(selected),
            key=lambda item: (-item[1].priority, item[0]),
        )
        kept_indexes: list[int] = []
        cost = len(preamble.rstrip())
        for index, section in ranked:
            section_cost = len(f"\n\n## {section.title}\n- ... section truncated\n")
            if cost + section_cost <= max_chars:
                kept_indexes.append(index)
                cost += section_cost
        omitted = len(selected) - len(kept_indexes)
        selected = [selected[index] for index in sorted(kept_indexes)]
        if omitted:
            coverage = ContextSection(
                title="Context coverage",
                body=f"- {omitted} lower-priority section(s) omitted by the character budget.",
                priority=200,
                minimum_bytes=100,
            )
            coverage_cost = len(f"\n\n{coverage.render()}")
            while selected and cost + coverage_cost > max_chars:
                lowest = min(
                    range(len(selected)),
                    key=lambda index: (selected[index].priority, -index),
                )
                removed = selected.pop(lowest)
                cost -= len(f"\n\n## {removed.title}\n- ... section truncated\n")
                omitted += 1
                coverage = ContextSection(
                    title="Context coverage",
                    body=f"- {omitted} lower-priority section(s) omitted by the character budget.",
                    priority=200,
                    minimum_bytes=100,
                )
                coverage_cost = len(f"\n\n{coverage.render()}")
            if cost + coverage_cost <= max_chars:
                selected.append(coverage)

    byte_budget = min(max_bytes, max_chars * 4)
    result = _render_context_bytes(preamble, selected, byte_budget)
    for _ in range(8):
        if len(result) <= max_chars:
            return result
        next_budget = len(result[:max_chars].encode("utf-8"))
        if next_budget >= byte_budget:
            next_budget = byte_budget - 1
        byte_budget = max(1, next_budget)
        result = _render_context_bytes(preamble, selected, byte_budget)

    result = _render_context_bytes(preamble, selected, min(max_bytes, max_chars))
    if len(result) > max_chars:
        raise ValueError("context planner could not satisfy the character budget")
    return result
