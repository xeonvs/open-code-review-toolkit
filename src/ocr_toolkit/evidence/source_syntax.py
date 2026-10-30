"""Bounded full-source Python syntax, separate from Git and DLP orchestration."""

from __future__ import annotations

import ast
import builtins
import hashlib
import io
import re
import tokenize
import unicodedata
from dataclasses import dataclass, field

from ocr_toolkit.context.code_text import CodeTextContext

MAX_SYNTAX_CHARS = 256_000
MAX_SYNTAX_NODES = 30_000
MAX_KEY_SPANS = 4096


def _reference_value(node: ast.AST | None, known_names: set[str]) -> bool:
    """Require no literal credential material, regardless of names or callees."""

    if node is None:
        return True
    elements = tuple(ast.walk(node))
    callee_names = set()
    for call in elements:
        if isinstance(call, ast.Call):
            target = call.func
            while isinstance(target, ast.Attribute):
                target = target.value
            if isinstance(target, ast.Name):
                callee_names.add(id(target))
    return all(
        not isinstance(item, ast.Name)
        or not isinstance(item.ctx, ast.Load)
        or item.id in known_names
        or id(item) in callee_names
        for item in elements
    ) and all(
        not isinstance(item, ast.Constant)
        or item.value is None
        or item.value is Ellipsis
        or (isinstance(item.value, (str, bytes)) and not item.value)
        for item in elements
    )


def _python_declaration(source: str) -> bool | None:
    """A contradictory interpreter closes refinement, irrespective of filename."""

    if not source.startswith("#!"):
        return None
    words = source.split("\n", 1)[0][2:].strip().split()
    if not words:
        return False
    command = words[0].rsplit("/", 1)[-1]
    if command == "env":
        words = words[1:]
        if words[:1] == ["-S"]:
            words = words[1:]
        if not words:
            return False
        command = words[0].rsplit("/", 1)[-1]
    return re.fullmatch(r"python(?:[0-9]+(?:\.[0-9]+)*)?", command) is not None


@dataclass(frozen=True, slots=True)
class PythonSourceSyntax:
    source: str = field(repr=False)
    line_starts: tuple[int, ...]
    key_spans: tuple[tuple[int, int], ...]
    material_spans: tuple[tuple[int, int], ...]

    def context(self, start: int, end: int, value: str) -> CodeTextContext | None:
        if not 1 <= start <= end <= len(self.line_starts):
            return None
        left = self.line_starts[start - 1]
        right = self.line_starts[end] - 1 if end < len(self.line_starts) else len(self.source)
        selected = self.source[left:right]
        normalized = unicodedata.normalize(
            "NFC", value.replace("\r\n", "\n").replace("\r", "\n")
        ).strip()
        if selected.strip() != normalized:
            return None
        # We do not infer dataflow through aliases, defaults or local factories.
        # If the excerpt also contains literal material, retain strict generic
        # checks instead of waiving a key whose value might refer to that material.
        if any(a < right and b > left for a, b in self.material_spans):
            return None
        left += len(selected) - len(selected.lstrip())
        spans = tuple(
            (a - left, b - left)
            for a, b in self.key_spans
            if left <= a < b <= left + len(normalized)
        )
        return CodeTextContext(hashlib.sha256(normalized.encode()).hexdigest(), spans)


def analyze_python_source(source: str) -> PythonSourceSyntax | None:
    """Never treat an excerpt parsed out of a docstring/comment as executable code."""

    if len(source) > MAX_SYNTAX_CHARS or any(char in source for char in "\v\f\x85\u2028\u2029"):
        return None
    source = unicodedata.normalize("NFC", source.replace("\r\n", "\n").replace("\r", "\n"))
    try:
        tree = ast.parse(source)
        declared = _python_declaration(source)
        if declared is False:
            return None
        # A standalone annotation/assignment can also be YAML, dotenv or shell.
        # Do not infer executable Python merely because a fragment parses.
        if declared is not True and not any(
            isinstance(
                node,
                (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef),
            )
            for node in tree.body
        ):
            return None
        nodes = []
        for node in ast.walk(tree):
            nodes.append(node)
            if len(nodes) > MAX_SYNTAX_NODES:
                return None
        known_names = set(vars(builtins))
        known_names.update(
            node.id
            for node in nodes
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)
        )
        known_names.update(node.arg for node in nodes if isinstance(node, ast.arg))
        known_names.update(
            node.name
            for node in nodes
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        )
        known_names.update(
            node.asname or node.name.split(".")[0] for node in nodes if isinstance(node, ast.alias)
        )
        lines = source.split("\n")
        starts = [0]
        for line in lines[:-1]:
            starts.append(starts[-1] + len(line) + 1)
        by_start: dict[tuple[int, int], tuple[int, int]] = {}
        by_end: dict[tuple[int, int], tuple[int, int]] = {}
        # Tokenizer columns count characters, AST columns count UTF-8 bytes.
        # Translate ordered token boundaries in one pass, without quadratic slices.
        positions: dict[int, tuple[int, int]] = {}

        def byte_column(line: int, column: int) -> int:
            old_char, old_byte = positions.get(line, (0, 0))
            new_byte = old_byte + len(lines[line - 1][old_char:column].encode())
            positions[line] = column, new_byte
            return new_byte

        for count, token in enumerate(tokenize.generate_tokens(io.StringIO(source).readline)):
            if count > 3 * MAX_SYNTAX_NODES:
                return None
            if token.type not in {tokenize.NAME, tokenize.STRING}:
                continue
            a, b = token.start, token.end
            span = (starts[a[0] - 1] + a[1], starts[b[0] - 1] + b[1])
            by_start[a[0], byte_column(*a)] = span
            by_end[b[0], byte_column(*b)] = span
        spans: set[tuple[int, int]] = set()

        def key(node: ast.AST) -> None:
            if isinstance(node, (ast.Name, ast.arg, ast.keyword)):
                span = by_start.get((node.lineno, node.col_offset))
            elif isinstance(node, ast.Attribute):
                span = by_end.get((node.end_lineno, node.end_col_offset))
            else:
                if isinstance(node, (ast.Tuple, ast.List)):
                    for element in node.elts:
                        key(element)
                return
            if span is not None:
                spans.add(span)

        defaults: dict[int, ast.AST | None] = {}
        # String keys are values too: iterating a mapping can return them as a
        # credential. No name-based exception removes them from the material guard.
        material = [
            node
            for node in nodes
            if isinstance(node, ast.Constant) and not _reference_value(node, known_names)
        ]
        needed: dict[int, set[int]] = {}
        for node in material:
            if node.end_lineno is None or node.end_col_offset is None:
                return None
            needed.setdefault(node.lineno, set()).add(node.col_offset)
            needed.setdefault(node.end_lineno, set()).add(node.end_col_offset)
        offsets = {}
        for number, columns in needed.items():
            raw = lines[number - 1].encode()
            previous_byte = previous_char = 0
            for column in sorted(columns):
                previous_char += len(raw[previous_byte:column].decode())
                offsets[number, column] = starts[number - 1] + previous_char
                previous_byte = column
        material_spans = tuple(
            (offsets[node.lineno, node.col_offset], offsets[node.end_lineno, node.end_col_offset])
            for node in material
        )
        for node in nodes:
            if isinstance(node, ast.arguments):
                positional = node.posonlyargs + node.args
                defaults.update(
                    (id(arg), default)
                    for arg, default in zip(
                        positional[-len(node.defaults) :] if node.defaults else [],
                        node.defaults,
                        strict=True,
                    )
                )
                defaults.update(
                    (id(arg), default)
                    for arg, default in zip(node.kwonlyargs, node.kw_defaults, strict=True)
                )
        for node in nodes:
            if isinstance(node, ast.Assign) and _reference_value(node.value, known_names):
                for target in node.targets:
                    key(target)
            elif (
                isinstance(node, ast.AnnAssign)
                and _reference_value(node.value, known_names)
                and _reference_value(node.annotation, known_names)
            ) or (isinstance(node, ast.NamedExpr) and _reference_value(node.value, known_names)):
                key(node.target)
            elif (
                isinstance(node, ast.keyword)
                and node.arg is not None
                and _reference_value(node.value, known_names)
            ) or (
                isinstance(node, ast.arg)
                and _reference_value(node.annotation, known_names)
                and _reference_value(defaults.get(id(node)), known_names)
            ):
                key(node)
            if len(spans) > MAX_KEY_SPANS:
                return None
        return PythonSourceSyntax(source, tuple(starts), tuple(sorted(spans)), material_spans)
    except (SyntaxError, ValueError, TypeError, RecursionError, MemoryError, tokenize.TokenError):
        return None
