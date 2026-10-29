"""Deterministic Mermaid and range details from admitted models; no acquisition."""

from __future__ import annotations

import re
from dataclasses import replace

from ocr_toolkit.common.markdown import inline_code, markdown_code_block
from ocr_toolkit.diagrams.contracts import (
    Diagram,
    DiagramResult,
    Flowchart,
    SequenceMessage,
    SequenceStep,
)
from ocr_toolkit.review_range import ReviewRange

BOUNDED_SUMMARY = (
    "Model-proposed summary; may omit routes and error handling. "
    "Source locations are checked mechanically and do not prove behavior."
)


def _label(text: str) -> str:
    """Escape Mermaid syntax as decimal entities, including reserved end tokens.

    See Mermaid's flowchart/sequence entity-code grammar. IDs and syntax below
    are toolkit-owned; model identifiers never become Mermaid identifiers.
    """

    escaped = "".join(c if c.isalnum() or c in " ._-" else f"#{ord(c)};" for c in text)
    return re.sub(
        r"\bend\b",
        lambda match: f"#{ord(match[0][0])};{match[0][1:]}",
        escaped,
        flags=re.IGNORECASE,
    )


def diagram_mermaid(diagram: Diagram) -> str:
    """Render only the supported fixed grammar, preserving message/branch order."""

    if isinstance(diagram, Flowchart):
        identifiers = {node.identifier: f"n{index}" for index, node in enumerate(diagram.nodes)}
        lines = ["flowchart LR"]
        for node in diagram.nodes:
            opener, closer = ('{"', '"}') if node.kind == "decision" else ('["', '"]')
            lines.append(f"    {identifiers[node.identifier]}{opener}{_label(node.label)}{closer}")
        for edge in diagram.edges:
            condition = f'|"{_label(edge.condition)}"|' if edge.condition else ""
            lines.append(
                f"    {identifiers[edge.source]} -->{condition} {identifiers[edge.target]}"
            )
        return "\n".join(lines)
    identifiers = {
        participant.identifier: f"p{index}"
        for index, participant in enumerate(diagram.participants)
    }
    lines = ["sequenceDiagram"]
    for participant in diagram.participants:
        lines.append(
            f"    participant {identifiers[participant.identifier]} as {_label(participant.label)}"
        )

    def steps(items: tuple[SequenceStep, ...], depth: int) -> None:
        indent = "    " * depth
        for item in items:
            if isinstance(item, SequenceMessage):
                arrow = "->>" if item.message_type == "call" else "-->>"
                lines.append(
                    f"{indent}{identifiers[item.source]}{arrow}{identifiers[item.target]}: {_label(item.label)}"
                )
            else:
                for index, branch in enumerate(item.branches):
                    lines.append(
                        f"{indent}{'alt' if index == 0 else 'else'} {_label(branch.condition)}"
                    )
                    steps(branch.steps, depth + 1)
                lines.append(f"{indent}end")

    steps(diagram.steps, 1)
    return "\n".join(lines)


def diagram_section(result: DiagramResult, *, collapsed: bool = False) -> str:
    """Apply presentation only after the adapter admits/suppresses a diagram."""

    if (
        result.state != "generated"
        or result.submission is None
        or result.submission.diagram is None
    ):
        return ""
    diagram = result.submission.diagram
    content = f"{BOUNDED_SUMMARY}\n\n{markdown_code_block('mermaid', diagram_mermaid(diagram))}"
    if collapsed:
        return "<details><summary>Change flow</summary>\n\n" + content + "\n\n</details>"
    return "### Change flow\n\n" + content


def range_details(review_range: ReviewRange | None, *, reviewed_sha: str = "") -> tuple[str, ...]:
    """Do not turn requested endpoints or legacy output into a confirmed range."""

    lines = [
        f"- Effective Git range: {inline_code(review_range.exact_range)}"
        if review_range is not None
        else "- Effective Git range: unverified"
    ]
    if reviewed_sha and (review_range is None or reviewed_sha != review_range.head):
        lines.append(f"- Reviewed commit: {inline_code(reviewed_sha, escape_controls=True)}")
    return tuple(lines)


def prepare_diagram_section(
    result: DiagramResult | None, *, collapsed: bool = False
) -> tuple[DiagramResult | None, str, bool]:
    """Keep optional rendering failures out of provider delivery and finding health."""

    if result is None or result.state != "generated":
        return result, "", False
    try:
        section = diagram_section(result, collapsed=collapsed)
        if not section:
            raise ValueError("generated diagram has no presentation")
    except Exception:
        return (
            replace(result, state="omitted-invalid", reason="unavailable", submission=None),
            "",
            True,
        )
    return result, section, False
