"""Bounded Markdown/HTML interpretation; original material is checked separately."""

from __future__ import annotations

import re
import weakref
from collections.abc import Iterable, Iterator
from contextvars import ContextVar
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any, SupportsIndex

from mistune import BlockParser, BlockState, InlineParser, InlineState, Markdown
from mistune.core import token_depth

from ocr_toolkit.common.redaction import masked_credential_spans
from ocr_toolkit.context.dlp.decoding import RepresentationLimit as RepresentationLimit

MAX_TOKENS = 32_768
MAX_DEPTH = 20


@dataclass(slots=True)
class _Budget:
    remaining: int = MAX_TOKENS

    def observe(self, token: dict[str, Any], depth: int) -> None:
        self.remaining -= 1
        if self.remaining < 0 or depth + token_depth([token]) > MAX_DEPTH:
            raise RepresentationLimit("markup construction budget")

    def html_event(self) -> None:
        self.remaining -= 1
        if self.remaining < 0:
            raise RepresentationLimit("HTML event budget")

    def reserve_inline(self, count: int) -> None:
        self.remaining -= count
        if self.remaining < 0:
            raise RepresentationLimit("inline construction budget")


# Only source-free counters/depth live in this scope. Native link handling can
# finalize plain-list slices, so list ownership alone cannot carry the budget.
_INLINE_SCOPE: ContextVar[tuple[_Budget, int] | None] = ContextVar("dlp_inline_scope", default=None)


class _Tokens(list[dict[str, Any]]):
    def __init__(self, owner: Any) -> None:
        super().__init__()
        self.owner = weakref.ref(owner)

    def _observe(self, token: dict[str, Any]) -> None:
        owner = self.owner()
        assert owner is not None
        block = isinstance(owner, BlockState)
        depth = owner.depth() if block else owner.depth + owner.env.get("dlp_depth", 0)
        owner.env["dlp_budget"].observe(token, depth)
        if block:
            token["dlp_depth"] = depth

    def append(self, token: dict[str, Any]) -> None:
        self._observe(token)
        super().append(token)

    def insert(self, index: SupportsIndex, token: dict[str, Any]) -> None:
        self._observe(token)
        super().insert(index, token)

    def extend(self, tokens: Iterable[dict[str, Any]]) -> None:
        for token in tokens:
            self.append(token)


class _BlockState(BlockState):
    def __init__(self, parent: BlockState | None = None) -> None:
        super().__init__(parent)
        self.tokens = _Tokens(self)
        if parent is None:
            self.env["dlp_budget"] = _Budget()


class _InlineState(InlineState):
    def __init__(self, env: Any) -> None:
        super().__init__(env)
        self.tokens = _Tokens(self)


class _BlockParser(BlockParser):
    state_cls = _BlockState


class _InlineParser(InlineParser):
    state_cls = _InlineState

    def render(self, state: InlineState) -> list[dict[str, Any]]:
        token = _INLINE_SCOPE.set((state.env["dlp_budget"], state.env.get("dlp_depth", 0)))
        try:
            return super().render(state)
        finally:
            _INLINE_SCOPE.reset(token)

    def finalize_tokens(self, tokens: list[dict[str, Any]], depth: int) -> list[dict[str, Any]]:
        scope = _INLINE_SCOPE.get()
        if scope is None:
            raise RepresentationLimit("unbound inline construction")
        budget, block_depth = scope
        markers = sum(
            token.get("raw", "").count("*") + token.get("raw", "").count("_")
            for token in tokens
            if token["type"] == "text" and token.get("_emphasis", True)
        )
        # Reserve coalescing/splitting/wrapper work before native finalization,
        # which constructs ordinary lists outside our append/insert hooks.
        budget.reserve_inline(len(tokens) + 4 * markers)
        result = super().finalize_tokens(tokens, depth)
        subtree_depth = token_depth(result)
        if block_depth + depth + subtree_depth > MAX_DEPTH or (
            subtree_depth and subtree_depth >= self.max_nested_level - depth
        ):
            raise RepresentationLimit("combined inline depth budget")
        return result

    def parse_codespan(self, match: re.Match[str], state: InlineState) -> int:
        end = super().parse_codespan(match, state)
        if state.tokens and state.tokens[-1]["type"] == "codespan":
            state.tokens[-1]["dlp_source"] = state.src[match.start() : end]
        return end


class _Markdown(Markdown):
    def _iter_render(
        self, tokens: Iterable[dict[str, Any]], state: BlockState
    ) -> Iterator[dict[str, Any]]:
        for token in tokens:
            if "children" in token:
                token["children"] = list(self._iter_render(token["children"], state))
            elif "text" in token:
                env = dict(state.env, dlp_depth=token.pop("dlp_depth", 0) + 1)
                token["children"] = self.inline(token.pop("text").strip(" \r\n\t\f"), env)
            yield token


class _VisibleHTML(HTMLParser):
    def __init__(self, budget: _Budget) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.budget = budget

    def handle_data(self, data: str) -> None:
        self.budget.html_event()
        self.parts.append(data)

    def handle_starttag(self, tag: str, attrs: Any) -> None:
        self.budget.html_event()

    def handle_endtag(self, tag: str) -> None:
        self.budget.html_event()

    def handle_comment(self, data: str) -> None:
        self.budget.html_event()


@dataclass(frozen=True, slots=True)
class MarkupText:
    visible: str
    code_sources: tuple[tuple[str, str], ...]
    contacts: str


_PARSER = _Markdown(
    renderer=None,
    block=_BlockParser(max_nested_level=MAX_DEPTH),
    inline=_InlineParser(max_nested_level=MAX_DEPTH),
)


def interpret_markdown(value: str) -> MarkupText:
    """Return visible material and exact native code-span lexemes, without HTML output."""

    if not any(c in value for c in "<>&`*_~[]\\"):
        return MarkupText(value, (), value)
    # Parser rules/compiled patterns are shared, but every parse creates fresh
    # state, references and budgets. The parser retains no document/cache text.
    tokens, state = _PARSER.parse(value)
    assert isinstance(tokens, list)
    pieces: list[str] = []
    contacts: list[str] = []
    code: list[tuple[str, str]] = []
    used = 0
    maximum = 4 * len(value) + 4096

    def add(text: str) -> None:
        nonlocal used
        used += len(text)
        if used > maximum:
            raise RepresentationLimit("markup view expansion budget")
        pieces.append(text)
        contacts.append(text)

    def boundary() -> None:
        nonlocal used
        used += 1
        if used > maximum:
            raise RepresentationLimit("markup contact expansion budget")
        contacts.append(" ")

    def walk(items: list[dict[str, Any]]) -> None:
        for token in items:
            kind = token["type"]
            formatted = kind in {"emphasis", "strong", "codespan"}
            if formatted:
                boundary()
            if "children" in token:
                walk(token["children"])
            elif kind in {"inline_html", "block_html"}:
                fragment = token.get("raw", "")
                if len(fragment) > 65_536:
                    raise RepresentationLimit("HTML token budget")
                html = _VisibleHTML(state.env["dlp_budget"])
                html.feed(fragment)
                html.close()
                add("".join(html.parts) + html.rawdata)
            else:
                add(token.get("raw", "\n" if kind in {"softbreak", "linebreak"} else ""))
            if kind == "codespan":
                code.append((token["dlp_source"], token["raw"]))
            if formatted:
                boundary()
            if kind in {"paragraph", "block_code", "heading", "block_html"}:
                add("\n")

    walk(tokens)
    return MarkupText("".join(pieces), tuple(code), "".join(contacts))


def strip_format_markers(value: str) -> str:
    """Conservative deobfuscation that cannot erase a complete canonical mask."""

    protected_spans = masked_credential_spans(value)
    if not protected_spans:
        return re.sub(r"[`*_~]", "", value)
    spans = iter(protected_spans)
    protected = next(spans, None)
    parts = []
    for index, character in enumerate(value):
        while protected is not None and index >= protected[1]:
            protected = next(spans, None)
        if character not in "`*_~" or (protected is not None and protected[0] <= index):
            parts.append(character)
    return "".join(parts)
