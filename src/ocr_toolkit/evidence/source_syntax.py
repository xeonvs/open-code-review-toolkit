"""Bounded full-source syntax roles, separate from Git and DLP orchestration."""

from __future__ import annotations

import ast
import builtins
import hashlib
import io
import re
import tokenize
import unicodedata
from bisect import bisect_left, bisect_right
from dataclasses import dataclass, field

from ocr_toolkit.context.code_text import CodeTextContext
from ocr_toolkit.context.dlp.credentials import credential_reference_spans

MAX_SYNTAX_CHARS = 256_000
MAX_SYNTAX_NODES = 30_000
MAX_KEY_SPANS = 4096


def _merged_ranges(spans: list[tuple[int, int]]) -> tuple[tuple[int, int], ...]:
    merged: list[tuple[int, int]] = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1] = merged[-1][0], max(end, merged[-1][1])
        else:
            merged.append((start, end))
    return tuple(merged)


def _relative_spans(
    spans: tuple[tuple[int, int], ...], left: int, right: int
) -> tuple[tuple[int, int], ...]:
    first, last = bisect_left(spans, (left, -1)), bisect_left(spans, (right, -1))
    return tuple((a - left, b - left) for a, b in spans[first:last] if b <= right)


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
class SourceSyntax:
    source: str = field(repr=False)
    line_starts: tuple[int, ...]
    key_spans: tuple[tuple[int, int], ...]
    material_spans: tuple[tuple[int, int], ...]
    operator_spans: tuple[tuple[int, int], ...] = ()

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
        index = bisect_left(self.material_spans, (right, -1))
        material = bool(index and self.material_spans[index - 1][1] > left)
        left += len(selected) - len(selected.lstrip())
        spans = () if material else _relative_spans(self.key_spans, left, left + len(normalized))
        operators = _relative_spans(self.operator_spans, left, left + len(normalized))
        if material and not operators:
            return None
        return CodeTextContext(hashlib.sha256(normalized.encode()).hexdigest(), spans, operators)


def analyze_python_source(source: str) -> SourceSyntax | None:
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
        star_tokens = []
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
            if token.type == tokenize.OP and token.string in {"*", "**"}:
                star_tokens.append(
                    (
                        starts[token.start[0] - 1] + token.start[1],
                        starts[token.end[0] - 1] + token.end[1],
                    )
                )
                if len(star_tokens) > MAX_KEY_SPANS:
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
        # Only actual numeric computation in the qualified full-source AST can
        # prove operator roles. An annotation, quoted string or template cannot.
        blocked: set[int] = set()
        for node in nodes:
            annotation = getattr(node, "annotation", None)
            if isinstance(annotation, ast.AST):
                blocked.add(id(annotation))
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.returns:
                blocked.add(id(node.returns))
            if isinstance(
                node, (ast.JoinedStr, getattr(ast, "TemplateStr", ast.JoinedStr), ast.TypeAlias)
            ):
                blocked.add(id(node))
            blocked.update(id(parameter) for parameter in getattr(node, "type_params", ()))
            if id(node) in blocked:
                blocked.update(id(child) for child in ast.iter_child_nodes(node))
        numeric: set[int] = set()
        for node in reversed(nodes):
            if id(node) in blocked:
                continue
            if (
                (isinstance(node, ast.Constant) and type(node.value) in (int, float))
                or (
                    isinstance(node, ast.UnaryOp)
                    and isinstance(node.op, (ast.UAdd, ast.USub))
                    and id(node.operand) in numeric
                )
                or (
                    isinstance(node, ast.BinOp)
                    and id(node.left) in numeric
                    and id(node.right) in numeric
                )
            ):
                numeric.add(id(node))
        numeric_nodes = [
            node for node in nodes if isinstance(node, ast.BinOp) and id(node) in numeric
        ]
        needed: dict[int, set[int]] = {}
        for node in (*material, *numeric_nodes):
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
        material_spans = _merged_ranges(
            [
                (
                    offsets[node.lineno, node.col_offset],
                    offsets[node.end_lineno, node.end_col_offset],
                )
                for node in material
            ]
        )
        ranges = _merged_ranges(
            [
                (
                    offsets[node.lineno, node.col_offset],
                    offsets[node.end_lineno, node.end_col_offset],
                )
                for node in numeric_nodes
            ]
        )
        operators = []
        for operator_start, operator_end in star_tokens:
            index = bisect_right(ranges, (operator_start, len(source) + 1)) - 1
            if index >= 0 and operator_end <= ranges[index][1]:
                operators.append((operator_start, operator_end))
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
        return SourceSyntax(
            source, tuple(starts), tuple(sorted(spans)), material_spans, tuple(operators)
        )
    except (SyntaxError, ValueError, TypeError, RecursionError, MemoryError, tokenize.TokenError):
        return None


def analyze_configuration_source(source: str) -> SourceSyntax | None:
    """Carry closed configuration roles into exact excerpts of the whole source.

    This does not parse or trust arbitrary YAML, expand templates, or infer a
    framework from a filename. Unknown values/structure retain ordinary checks.
    """

    if len(source) > MAX_SYNTAX_CHARS or any(char in source for char in "\v\f\x85\u2028\u2029"):
        return None
    source = unicodedata.normalize("NFC", source.replace("\r\n", "\n").replace("\r", "\n"))
    spans = credential_reference_spans(source)
    if not spans or len(spans) > MAX_KEY_SPANS:
        return None
    starts = [0]
    for line in source.split("\n")[:-1]:
        starts.append(starts[-1] + len(line) + 1)
    return SourceSyntax(source, tuple(starts), spans, ())
