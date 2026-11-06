"""Bounded closed-data proof, without executing or qualifying source code."""

from __future__ import annotations

import ast
import json
import re

_MAX_CHARS = 2_000_000
_MAX_TOKENS = 32_768
_MAX_DEPTH = 20
_PUNCTUATION = re.compile(r"[^\w\s]|\d+", re.UNICODE)
_DATA_SCALARS = frozenset({"true", "false", "null", "none"})
_DATA_NODES = (
    ast.Expression,
    ast.Module,
    ast.Expr,
    ast.Assign,
    ast.AnnAssign,
    ast.Constant,
    ast.List,
    ast.Tuple,
    ast.Set,
    ast.Dict,
    ast.Load,
    ast.Store,
    ast.UnaryOp,
    ast.UAdd,
    ast.USub,
)


class LiteralContext:
    """Cache one bounded quote inventory and a complete data-grammar proof.

    Only literal values, containers and named literal fields qualify. Unknown
    calls, references, operators or literal syntaxes never acquire authority
    from the number of recognized strings. This is not a source-language proof.
    """

    def __init__(self, text: str) -> None:
        self.text = text
        self._quotes: dict[tuple[int, int], bool] | None = None
        self._data: bool | None = None
        self._valid = True

    def proves_carrier(self, start: int, end: int) -> bool:
        if self._quotes is None:
            self._inventory()
        assert self._quotes is not None
        if not self._valid or (start, end) not in self._quotes:
            return False
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
        while cursor < len(text):
            quote = text[cursor]
            if quote not in "\"'":
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
            if len(self._quotes) > _MAX_TOKENS:
                self._valid = False
                return

    def _literal_data(self) -> bool:
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
            # No parser-discarded comments or unbounded numeric conversion.
            if match[0] == "#" or len(match[0]) > 4096:
                return False
            if match[0] in "([{":
                depth += 1
                if depth > _MAX_DEPTH:
                    return False
            elif match[0] in ")]}":
                depth -= 1
                if depth < 0:
                    return False
        try:
            json.loads(self.text)
            return True
        except (ValueError, RecursionError):
            pass
        try:
            try:
                tree = ast.parse(self.text.strip(), mode="eval")
            except SyntaxError:
                tree = ast.parse(self.text.strip(), mode="exec")
        except (SyntaxError, ValueError, RecursionError, UnicodeError):
            return False
        targets: set[int] = set()
        if isinstance(tree, ast.Module):
            for statement in tree.body:
                if isinstance(statement, ast.Assign):
                    if len(statement.targets) != 1 or not isinstance(
                        statement.targets[0], ast.Name
                    ):
                        return False
                    targets.add(id(statement.targets[0]))
                elif isinstance(statement, ast.AnnAssign):
                    if statement.value is not None or not isinstance(statement.target, ast.Name):
                        return False
                    targets.add(id(statement.target))
                elif not isinstance(statement, ast.Expr):
                    return False
        strings = 0
        for count, node in enumerate(ast.walk(tree), 1):
            if count > _MAX_TOKENS:
                return False
            if isinstance(node, ast.Name):
                if id(node) not in targets and node.id.casefold() not in _DATA_SCALARS:
                    return False
                continue
            if not isinstance(node, _DATA_NODES):
                return False
            if isinstance(node, ast.UnaryOp) and (
                not isinstance(node.operand, ast.Constant)
                or type(node.operand.value) not in {int, float, complex}
            ):
                return False
            strings += isinstance(node, ast.Constant) and isinstance(node.value, (str, bytes))
        return strings == len(self._quotes or ())
