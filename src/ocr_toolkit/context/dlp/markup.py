"""Bounded Markdown/HTML interpretation; original material is checked separately."""

from __future__ import annotations

import re
import weakref
from bisect import bisect_right
from collections.abc import Iterable, Iterator
from contextvars import ContextVar
from dataclasses import dataclass
from functools import cached_property
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

    def add_paragraph(self, text: str) -> None:
        previous = self.last_token()
        contiguous = (
            previous is not None
            and previous.get("dlp_start", -1) + len(previous.get("text", "")) == self.cursor
        )
        super().add_paragraph(text)
        token = self.last_token()
        if self.parent is None and self.src[self.cursor : self.cursor + len(text)] == text:
            if previous is not token:
                token["dlp_start"] = self.cursor
            elif not contiguous:
                token.pop("dlp_start", None)

    def append_paragraph(self) -> int | None:
        token = self.last_token()
        contiguous = (
            token is not None
            and token.get("dlp_start", -1) + len(token.get("text", "")) == self.cursor
        )
        end = super().append_paragraph()
        if token is not None and not contiguous:
            token.pop("dlp_start", None)
        return end


class _InlineState(InlineState):
    def __init__(self, env: Any) -> None:
        super().__init__(env)
        self.tokens = _Tokens(self)

    def copy(self) -> _InlineState:
        # Native nested parsers can rewrite their source. Without an exact
        # mapping they must not inherit their parent's delimiter authority.
        state = super().copy()
        assert isinstance(state, _InlineState)
        state.env = {k: v for k, v in state.env.items() if k != "dlp_start"}
        return state

    @cached_property
    def credential_masks(self) -> tuple[tuple[int, int], ...]:
        """Cache exact mask positions only for this short-lived source state."""

        return masked_credential_spans(self.src)


class _BlockParser(BlockParser):
    state_cls = _BlockState

    def parse_atx_heading(self, match: re.Match[str], state: BlockState) -> int:
        end = super().parse_atx_heading(match, state)
        token = state.last_token()
        if state.parent is None and token is not None:
            text = token["text"]
            start = match.start("atx_2") + len(match["atx_2"]) - len(match["atx_2"].lstrip())
            if state.src[start : start + len(text)] == text:
                token["dlp_start"] = start
        return end


class _InlineParser(InlineParser):
    state_cls = _InlineState

    def parse_emphasis(self, match: re.Match[str], state: InlineState) -> int:
        assert isinstance(state, _InlineState)
        masks = state.credential_masks
        index = bisect_right(masks, (match.start(), len(state.src) + 1)) - 1
        if index >= 0 and masks[index][0] <= match.start() < match.end() <= masks[index][1]:
            # A canonical mask contains no credential material. Interpreting
            # masks in separate fields as one emphasis pair invents a value.
            state.append_token({"type": "text", "raw": match[0], "_emphasis": False})
            return match.end()
        return super().parse_emphasis(match, state)

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
        if state.tokens and state.tokens[-1]["type"] == "codespan" and "dlp_start" in state.env:
            state.tokens[-1]["dlp_opening"] = (
                state.env["dlp_start"] + match.start(),
                len(match[0]),
            )
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
                text = token.pop("text")
                if "dlp_start" in token:
                    env["dlp_start"] = (
                        token.pop("dlp_start") + len(text) - len(text.lstrip(" \r\n\t\f"))
                    )
                token["children"] = self.inline(text.strip(" \r\n\t\f"), env)
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
    contacts: str
    code_openings: tuple[tuple[int, int], ...] = ()
    hidden: tuple[str, ...] = ()
    links: tuple[str, ...] = ()


_PARSER = _Markdown(
    renderer=None,
    block=_BlockParser(max_nested_level=MAX_DEPTH),
    inline=_InlineParser(max_nested_level=MAX_DEPTH),
)


def interpret_markdown(value: str) -> MarkupText:
    """Return bounded material views and original delimiter positions, without HTML output."""

    if not any(c in value for c in "<>&`*_~[]\\"):
        return MarkupText(value, value)
    # Parser rules/compiled patterns are shared, but every parse creates fresh
    # state, references and budgets. The parser retains no document/cache text.
    tokens, state = _PARSER.parse(value)
    assert isinstance(tokens, list)
    pieces: list[str] = []
    contacts: list[str] = []
    openings: list[tuple[int, int]] = []
    hidden: dict[str, None] = {}
    links: dict[str, None] = {}
    used = 0
    hidden_used = 0
    maximum = 4 * len(value) + 4096
    hidden_maximum = 4 * len(value.encode("utf-8")) + 4096

    def hide(text: str) -> None:
        nonlocal hidden_used
        if text and text not in hidden:
            hidden_used += len(text)
            if hidden_used > hidden_maximum:
                raise RepresentationLimit("hidden material expansion budget")
            hidden[text] = None

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
            if kind in {"link", "image"}:
                attrs = token["attrs"]
                links[attrs["url"]] = None
                hide(attrs["url"])
                hide(attrs.get("title", ""))
            formatted = kind in {"emphasis", "strong", "codespan"}
            if formatted:
                boundary()
            if "children" in token:
                walk(token["children"])
            elif kind in {"inline_html", "block_html"}:
                fragment = token.get("raw", "")
                if len(fragment) > 65_536:
                    raise RepresentationLimit("HTML token budget")
                hide(fragment)
                html = _VisibleHTML(state.env["dlp_budget"])
                try:
                    html.feed(fragment)
                    html.close()
                except AssertionError as exc:
                    # Some supported stdlib parsers assert on malformed marked
                    # sections. An unavailable security view must fail closed.
                    raise RepresentationLimit("HTML interpretation unavailable") from exc
                add("".join(html.parts) + html.rawdata)
            else:
                add(token.get("raw", "\n" if kind in {"softbreak", "linebreak"} else ""))
            if kind == "codespan" and "dlp_opening" in token:
                openings.append(token["dlp_opening"])
            if formatted:
                boundary()
            if kind in {"paragraph", "block_code", "heading", "block_html"}:
                add("\n")

    walk(tokens)
    for attrs in state.env["ref_links"].values():
        links[attrs["url"]] = None
        hide(attrs["url"])
        hide(attrs.get("title", ""))
    return MarkupText(
        "".join(pieces),
        "".join(contacts),
        tuple(openings),
        tuple(hidden),
        tuple(links),
    )


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
