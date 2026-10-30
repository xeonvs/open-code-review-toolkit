"""Deterministic flowchart width estimates; no renderer, model or acquisition."""

from __future__ import annotations

import unicodedata
from typing import Literal

from ocr_toolkit.diagrams.contracts import Flowchart

READABLE_COLUMNS = 100
RANK_GAP = 8


def _columns(value: str) -> int:
    """Approximate displayed glyph width, independent of Mermaid entity syntax."""

    return sum(
        0 if unicodedata.combining(c) else 2 if unicodedata.east_asian_width(c) in {"W", "F"} else 1
        for c in value
    )


def flowchart_direction(diagram: Flowchart) -> Literal["LR", "TB"]:
    """Prefer LR when it fits; otherwise choose the narrower estimated layout.

    Condense cycles before ranking, retaining their member/feedback-edge cost.
    Width is a bounded heuristic for an ordinary report viewport, not a promise
    about a provider's font or Mermaid version. Node/edge order stays untouched.
    """

    if not diagram.nodes:
        return "LR"
    nodes = {node.identifier: node for node in diagram.nodes}
    reach = {name: {name} for name in nodes}
    for edge in diagram.edges:
        reach[edge.source].add(edge.target)
    for _ in nodes:
        for name in nodes:
            reach[name].update(*(reach[target] for target in tuple(reach[name])))
    components = []
    remaining = set(nodes)
    for name in sorted(nodes):
        if name in remaining:
            group = {target for target in reach[name] if name in reach[target]}
            components.append(group)
            remaining.difference_update(group)
    owners = {name: index for index, group in enumerate(components) for name in group}
    ranks = [0] * len(components)
    links = {(owners[edge.source], owners[edge.target]) for edge in diagram.edges}
    for _ in components:
        for source, target in sorted(links):
            if source != target:
                ranks[target] = max(ranks[target], ranks[source] + 1)
    widths = {
        name: max(8, _columns(node.label) + (10 if node.kind == "decision" else 6))
        for name, node in nodes.items()
    }
    lr_ranks: dict[int, list[int]] = {}
    tb_ranks: dict[int, list[int]] = {}
    for index, group in enumerate(components):
        rank = ranks[index]
        # An SCC can contain a chain and feedback edges; do not mistake a large
        # cycle for a single small box when predicting horizontal overflow.
        lr = sum(widths[name] for name in group) + RANK_GAP * (len(group) - 1)
        tb = max(widths[name] for name in group) + (4 if len(group) > 1 else 0)
        lr_ranks.setdefault(rank, []).append(lr)
        tb_ranks.setdefault(rank, []).append(tb)
    gaps = [RANK_GAP] * max(ranks)
    condition_width = 0
    for edge in diagram.edges:
        width = _columns(edge.condition)
        condition_width = max(condition_width, width)
        start, end = ranks[owners[edge.source]], ranks[owners[edge.target]]
        if end > start:
            part = (width + 4 + end - start - 1) // (end - start)
            for rank in range(start, end):
                gaps[rank] = max(gaps[rank], part)
    lr_width = sum(max(layer) for layer in lr_ranks.values()) + sum(gaps)
    tb_width = max(
        condition_width + RANK_GAP,
        *(sum(layer) + RANK_GAP * (len(layer) - 1) for layer in tb_ranks.values()),
    )
    return "TB" if lr_width > READABLE_COLUMNS and tb_width < lr_width else "LR"
