"""Bounded literal-data proof, without executing or importing source code."""

from __future__ import annotations

import ast
import json
import re

_MAX_CHARS = 2_000_000
_MAX_TOKENS = 32_768
_MAX_DEPTH = 20
_PUNCTUATION = re.compile(r"[^\w\s]|\d+", re.UNICODE)
_DATA_SCALARS = frozenset({"true", "false", "null", "none"})
_SCALAR = re.compile(r"(?<!\w)(?:\d|(?:" + "|".join(sorted(_DATA_SCALARS)) + r")\b)", re.IGNORECASE)
_INDEX = re.compile(r"\[\s*[+-]?\d+\s*\]")
_DATA_NODES = (
    ast.Expression,
    ast.Constant,
    ast.List,
    ast.Tuple,
    ast.Set,
    ast.Dict,
    ast.Load,
    ast.UnaryOp,
    ast.UAdd,
    ast.USub,
)


class LiteralContext:
    """Keep one local quote inventory and lazily prove a closed data container.

    A comma in executable/unknown syntax does not establish independence of
    neighboring literals. A closed literal-data expression does: calls,
    subscripts, operators and interpolation cannot acquire that authority.
    This is a data grammar, not a qualification of a source language.
    """

    def __init__(self, text: str) -> None:
        self.text = text
        self._quotes: dict[tuple[int, int], bool] | None = None
        self._data: bool | None = None
        self._valid = True
        self._materials = 0
        self._quote_records: dict[tuple[int, int], int] = {}
        self._scalar_records: set[int] = set()

    def proves_carrier(self, start: int, end: int) -> bool:
        if self._quotes is None:
            self._inventory()
        assert self._quotes is not None
        if not self._valid or (start, end) not in self._quotes:
            return False
        if (
            self._materials == int(self._quotes[start, end])
            and self._quote_records[start, end] not in self._scalar_records
        ):
            return True
        if self._data is None:
            self._data = self._literal_data()
        return self._data

    def _inventory(self) -> None:
        self._quotes = {}
        text = self.text
        if len(text) > _MAX_CHARS:
            self._valid = False
            return
        cursor = 0
        record = 0
        depth = 0
        pending_break = False
        while cursor < len(text):
            quote = text[cursor]
            if pending_break and not quote.isspace():
                if quote not in ",+-*/%|&^.":
                    record += 1
                pending_break = False
            if quote not in "\"'":
                # A closed postfix ordinal selects a reference without
                # resolving its value or contributing literal credential bits.
                if (
                    quote == "["
                    and cursor
                    and (text[cursor - 1].isalnum() or text[cursor - 1] in "_)]")
                ):
                    index = _INDEX.match(text, cursor)
                    if index is not None:
                        cursor = index.end()
                        continue
                if quote in "([{":
                    depth += 1
                elif quote in ")]}":
                    depth = max(0, depth - 1)
                if (quote.isdecimal() or quote in "tTfFnN") and (
                    _SCALAR.match(text, cursor) is not None
                ):
                    self._scalar_records.add(record)
                    if len(self._scalar_records) > _MAX_TOKENS:
                        self._valid = False
                        return
                if quote == "\n" and depth == 0:
                    previous = cursor - 1
                    while previous >= 0 and text[previous] in " \t\r":
                        previous -= 1
                    if previous < 0 or text[previous] not in "\\,+-*/%|&^.":
                        pending_break = True
                elif quote == ";" and depth == 0:
                    record += 1
                cursor += 1
                continue
            start = cursor
            cursor += 1
            while cursor < len(text) and text[cursor] != quote:
                cursor += 2 if text[cursor] == "\\" else 1
            if cursor >= len(text) or text.startswith(quote * 3, start):
                self._valid = False
                return
            cursor += 1
            self._quotes[start, cursor] = text[start + 1 : cursor - 1] not in {"", "***"}
            self._quote_records[start, cursor] = record
            self._materials += self._quotes[start, cursor]
            if len(self._quotes) > _MAX_TOKENS:
                self._valid = False
                return

    def _literal_data(self) -> bool:
        # Bound parser allocation before calling the stdlib parser, including
        # punctuation inside interpolation-shaped strings that could expand ASTs.
        depth = 0
        quotes = iter(self._quotes or ())
        quoted = next(quotes, None)
        for count, match in enumerate(_PUNCTUATION.finditer(self.text), 1):
            if count > _MAX_TOKENS:
                return False
            while quoted is not None and match.start() >= quoted[1]:
                quoted = next(quotes, None)
            if quoted is not None and quoted[0] <= match.start() < quoted[1]:
                continue
            # Bound numeric conversion even when a host disables Python's
            # process-wide decimal digit guard. Quoted data stays literal.
            if len(match[0]) > 4096:
                return False
            if match[0] in "([{":
                depth += 1
                if depth > _MAX_DEPTH:
                    return False
            elif match[0] in ")]}":
                depth -= 1
        try:
            # A complete JSON value is also closed literal data. It cannot
            # discard comments or contain calls/expressions. The same lexical
            # allocation bounds above apply before either standard parser.
            json.loads(self.text)
            return True
        except (ValueError, RecursionError):
            pass
        try:
            tree = ast.parse(self.text.strip(), mode="eval")
        except (SyntaxError, ValueError, RecursionError, UnicodeError):
            return False
        strings = 0
        for count, node in enumerate(ast.walk(tree), 1):
            if count > _MAX_TOKENS:
                return False
            # Data scalars stay scalars under the independent case-folded
            # material view. This permits no calls, operators or other names.
            if isinstance(node, ast.Name) and node.id.casefold() in _DATA_SCALARS:
                continue
            if not isinstance(node, _DATA_NODES):
                return False
            strings += isinstance(node, ast.Constant) and isinstance(node.value, (str, bytes))
        # Each inventoried carrier must belong to the closed data expression.
        # Comments are discarded by AST parsing; adjacent literals are merged.
        # Neither can grant independence to an unrepresented quoted fragment.
        return strings == len(self._quotes or ())
