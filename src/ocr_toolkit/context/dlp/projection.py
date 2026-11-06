"""Bounded inert Markdown presentation, after independent material admission."""

from __future__ import annotations

import re
import string
from collections.abc import Iterable
from typing import Any
from urllib.parse import unquote, urlsplit

from mistune import BlockState
from mistune.renderers.markdown import MarkdownRenderer

from ocr_toolkit.context.contracts import TextBudgets
from ocr_toolkit.context.dlp.decoding import RepresentationLimit, _html_decode
from ocr_toolkit.context.dlp.markup import _PARSER, interpret_markdown
from ocr_toolkit.context.dlp.presentation import has_unsafe_controls


class UnsafeDestination(ValueError):
    """A link cannot be delivered as an active destination."""


_HTML_LITERAL = {ord(c): f"&#{ord(c)};" for c in string.punctuation}
_HTML_LITERAL.update({ord("<"): "&lt;", ord(">"): "&gt;", ord("&"): "&amp;"})
_TEXT_LITERAL = {ord(c): f"&#{ord(c)};" for c in "\\[]!`"}


def decoded_markup_material(value: str) -> tuple[str, ...]:
    """Inspect bounded hidden/link material independently of active-URL admission."""

    if "[" not in value and "<" not in value:
        return ()
    views: dict[str, None] = {}
    maximum = 4 * len(value) + 4096
    used = 0
    markup = interpret_markdown(value)
    for url in dict.fromkeys((*markup.links, *markup.hidden)):
        for _ in range(3):
            # Replacement retains surrounding material even for malformed byte
            # escapes. Active URLs separately require strict valid Unicode.
            decoded = _html_decode(unquote(url))
            if decoded == url:
                break
            if decoded not in views:
                used += len(decoded)
                if used > maximum:
                    raise RepresentationLimit("destination material budget")
                views[decoded] = None
            url = decoded
    return tuple(views)


def validate_destination(value: str) -> None:
    """Validate both wire and decoded destinations without resolving a host."""

    if re.search(r"%(?![0-9A-Fa-f]{2})", value):
        raise UnsafeDestination("malformed URL encoding")
    candidate = value
    for _ in range(3):
        if (
            has_unsafe_controls(candidate, display=True)
            or any(c.isspace() and c != " " for c in candidate)
            or any(c in candidate for c in '\\<>"`')
            or candidate.startswith("//")
            or candidate != candidate.lstrip()
        ):
            raise UnsafeDestination("unsafe URL characters")
        try:
            parsed = urlsplit(candidate)
            if parsed.scheme.lower() not in {"", "http", "https"}:
                raise UnsafeDestination("unsafe URL scheme")
            if parsed.netloc and not parsed.scheme:
                raise UnsafeDestination("URL authority requires an allowed scheme")
            if parsed.username is not None or parsed.password is not None:
                raise UnsafeDestination("URL user information")
            if parsed.scheme and (not parsed.hostname or not parsed.netloc):
                raise UnsafeDestination("missing URL authority")
            if parsed.netloc and (
                " " in parsed.netloc or (parsed.port is not None and not 0 <= parsed.port <= 65535)
            ):
                raise UnsafeDestination("invalid URL authority")
        except ValueError as exc:
            raise UnsafeDestination("malformed URL") from exc
        try:
            decoded = _html_decode(unquote(candidate, errors="strict"))
        except UnicodeError as exc:
            raise UnsafeDestination("invalid URL Unicode") from exc
        if decoded == candidate:
            return
        candidate = decoded
    raise UnsafeDestination("URL decoding depth")


def _join(parts: Iterable[str], budgets: TextBudgets) -> str:
    chunks: list[str] = []
    chars = size = lines = 0
    for part in parts:
        chars += len(part)
        size += len(part.encode("utf-8"))
        lines += part.count("\n")
        if chars > budgets.max_chars or size > budgets.max_bytes or lines + 1 > budgets.max_lines:
            raise RepresentationLimit("safe presentation expansion")
        chunks.append(part)
    return "".join(chunks)


class _SafeRenderer(MarkdownRenderer):
    def __init__(self, budgets: TextBudgets) -> None:
        super().__init__()
        self.budgets = budgets

    def render_tokens(self, tokens: Iterable[dict[str, Any]], state: BlockState) -> str:
        return _join(self.iter_tokens(tokens, state), self.budgets)

    def text(self, token: dict[str, Any], state: BlockState) -> str:
        # Entity spelling preserves literal punctuation without introducing a
        # backslash into an otherwise valid numeric or credential boundary.
        return re.sub(
            r"\\([\\`<!&*_\[\]~])",
            lambda m: f"&#{ord(m[1])};",
            super().text(token, state),
        ).translate(_TEXT_LITERAL)

    def __call__(self, tokens: Iterable[dict[str, Any]], state: BlockState) -> str:
        def parts() -> Iterable[str]:
            yield self.render_tokens(tokens, state).rstrip()
            for reference in self.render_referrences(state):
                yield "\n\n"
                yield reference

        return _join(parts(), self.budgets).strip()

    def inline_html(self, token: dict[str, Any], state: BlockState) -> str:
        raw: str = token["raw"]
        # HTML escaping alone could activate Markdown hidden in comments or
        # attributes. Encode punctuation as literal text too, preserving every
        # character without creating images, links or code delimiters.
        count = sum(len(_HTML_LITERAL.get(ord(c), c)) for c in raw)
        if (
            count > self.budgets.max_chars
            or count + len(raw.encode()) - len(raw) > self.budgets.max_bytes
        ):
            raise RepresentationLimit("HTML escaping expansion")
        return raw.translate(_HTML_LITERAL)

    def block_html(self, token: dict[str, Any], state: BlockState) -> str:
        return self.inline_html(token, state) + "\n\n"

    def image(self, token: dict[str, Any], state: BlockState) -> str:
        # An ordinary link retains the alt text, URL and title without fetching.
        token = dict(token, type="link")
        return self.link(token, state)

    def block_code(self, token: dict[str, Any], state: BlockState) -> str:
        # Model prose cannot activate a host's executable/diagram fence handler.
        # Literal source bytes are kept; the typed diagram has its own renderer.
        return super().block_code(dict(token, attrs={"info": "text"}), state)


def _project_once(value: str, budgets: TextBudgets) -> str:
    """Project admitted prose; parser and output construction are independently bounded."""

    if not any(c in value for c in "<>&`*_~[]\\!"):
        return value
    tokens, state = _PARSER.parse(value)
    assert isinstance(tokens, list)
    stack = list(tokens)
    rewrite = False
    validated: set[str] = set()

    def validate(url: str) -> None:
        if url not in validated:
            validate_destination(url)
            validated.add(url)

    while stack:
        token = stack.pop()
        if token["type"] in {"link", "image"}:
            validate(token["attrs"]["url"])
        rewrite = (
            rewrite
            or token["type"] in {"inline_html", "block_html", "image"}
            or token["type"] == "block_code"
            or (
                token["type"] == "text"
                and (
                    any(c in token.get("raw", "") for c in "!`")
                    or re.search(r"<[!/?A-Za-z]", token.get("raw", "")) is not None
                )
            )
        )
        stack.extend(token.get("children", ()))
    # Unused definitions are still supplied material, not invisible exceptions.
    for attrs in state.env["ref_links"].values():
        validate(attrs["url"])
    if not rewrite:
        # Keep existing harmless syntax and literal carriers exactly. Rewriting
        # them merely to canonicalize Markdown can invent credential material.
        return value
    return _SafeRenderer(budgets)(tokens, state)


def project_prose(value: str, budgets: TextBudgets) -> str:
    """Deliver only a stable projection; at most three bounded parser passes."""

    for _ in range(3):
        projected = _project_once(value, budgets)
        if projected == value:
            return projected
        value = projected
    raise RepresentationLimit("noncanonical Markdown presentation")
