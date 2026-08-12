"""Parse bounded Go module declarations and checksums into normalized facts."""

from __future__ import annotations

from ocr_toolkit.evidence.ecosystems.contracts import (
    MAX_MANIFEST_ITEMS,
    ManifestFact,
    ManifestParseResult,
)
from ocr_toolkit.evidence.model import EvidenceValue


def _bounded_result(
    facts: list[ManifestFact], notices: list[str], format_name: str
) -> ManifestParseResult:
    """Cap Go facts and retain one deterministic coverage notice."""

    if len(facts) > MAX_MANIFEST_ITEMS:
        notices.append(f"{format_name} facts were truncated after {MAX_MANIFEST_ITEMS} items")
    return ManifestParseResult(tuple(facts[:MAX_MANIFEST_ITEMS]), tuple(dict.fromkeys(notices)))


def _module_fact(kind: str, path: str, version: str, scope: str) -> ManifestFact:
    """Create one Go module fact with a stable path-and-scope identity."""

    return ManifestFact(
        kind,
        "go",
        f"{scope}:{path}",
        {"name": path, "version": version, "scope": scope},
    )


def _split_go_line(raw: str) -> tuple[str, str | None]:
    """Strip one Go comment and return its body plus the comment text."""

    quote: str | None = None
    escaped = False
    for index, character in enumerate(raw):
        if quote == '"':
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = None
        elif quote == "`":
            if character == quote:
                quote = None
        elif character in {'"', "`"}:
            quote = character
        elif character == "/" and raw[index : index + 2] == "//":
            return raw[:index].strip(), raw[index + 2 :].strip()
    return raw.strip(), None


def _go_tokens(text: str) -> list[str]:
    """Tokenize the bounded go.mod subset while preserving quoted content."""

    tokens: list[str] = []
    current: list[str] = []
    quote: str | None = None
    escaped = False
    index = 0
    while index < len(text):
        character = text[index]
        if quote == '"':
            if escaped:
                current.append(character)
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = None
            else:
                current.append(character)
        elif quote == "`":
            if character == quote:
                quote = None
            else:
                current.append(character)
        elif character in {'"', "`"}:
            quote = character
        elif text[index : index + 2] == "=>":
            if current:
                tokens.append("".join(current))
                current = []
            tokens.append("=>")
            index += 1
        elif character.isspace():
            if current:
                tokens.append("".join(current))
                current = []
        else:
            current.append(character)
        index += 1
    if quote is not None or escaped:
        return []
    if current:
        tokens.append("".join(current))
    return tokens


def _replacement_fact(body: str) -> ManifestFact | None:
    """Parse one replace directive, including local replacements without versions."""

    parts = _go_tokens(body)
    if parts.count("=>") != 1:
        return None
    separator = parts.index("=>")
    source_parts = parts[:separator]
    target_parts = parts[separator + 1 :]
    if len(source_parts) not in {1, 2} or len(target_parts) not in {1, 2}:
        return None
    value: dict[str, EvidenceValue] = {
        "name": source_parts[0],
        "replacement": target_parts[0],
        "scope": "replace",
    }
    if len(source_parts) == 2:
        value["version"] = source_parts[1]
    if len(target_parts) == 2:
        value["replacement_version"] = target_parts[1]
        value["replacement_type"] = "module"
    else:
        value["replacement_type"] = "local"
    return ManifestFact(
        "dependency.declared",
        "go",
        f"replace:{' '.join(source_parts)}",
        value,
    )


def parse_go_mod(text: str) -> ManifestParseResult:
    """Parse go.mod module, runtime, requirements, replacements, and exclusions."""

    facts: list[ManifestFact] = []
    notices: list[str] = []
    block: str | None = None
    module_path: str | None = None
    for raw in text.splitlines():
        line, comment = _split_go_line(raw)
        if not line:
            continue
        if block is not None and line == ")":
            block = None
            continue
        parts = line.split(None, 1)
        keyword = parts[0]
        body = parts[1] if len(parts) == 2 else ""
        if (
            block is None
            and body == "("
            and keyword
            in {
                "require",
                "replace",
                "exclude",
                "retract",
                "tool",
                "ignore",
                "godebug",
            }
        ):
            block = keyword
            continue
        directive = block or keyword
        directive_body = line if block is not None else body
        if directive == "module" and directive_body:
            directive_tokens = _go_tokens(directive_body)
            if len(directive_tokens) != 1:
                notices.append("go.mod skipped a malformed module directive")
                continue
            module_path = directive_tokens[0]
            facts.append(
                ManifestFact(
                    "repository.manifest",
                    "go",
                    "module",
                    {"name": module_path, "manifest_type": "go.module"},
                )
            )
        elif directive in {"go", "toolchain"} and directive_body:
            directive_tokens = _go_tokens(directive_body)
            if len(directive_tokens) != 1:
                notices.append(f"go.mod skipped a malformed {directive} directive")
                continue
            facts.append(
                ManifestFact(
                    "runtime.declared",
                    "go",
                    directive,
                    {
                        "name": directive,
                        "constraint": directive_tokens[0],
                        "source": "go.mod",
                    },
                )
            )
        elif directive == "require":
            parts = _go_tokens(directive_body)
            if len(parts) == 2:
                scope = "indirect" if comment == "indirect" else "direct"
                facts.append(_module_fact("dependency.declared", parts[0], parts[1], scope))
        elif directive == "replace":
            if (fact := _replacement_fact(directive_body)) is not None:
                facts.append(fact)
        elif directive == "exclude":
            parts = _go_tokens(directive_body)
            if len(parts) == 2:
                excluded = _module_fact("dependency.declared", parts[0], parts[1], "exclude")
                facts.append(
                    ManifestFact(
                        excluded.kind,
                        excluded.component,
                        f"{excluded.identity}:{parts[1]}",
                        excluded.value,
                    )
                )
        elif directive == "tool" and directive_body:
            directive_tokens = _go_tokens(directive_body)
            if len(directive_tokens) == 1:
                tool_name = directive_tokens[0]
                facts.append(
                    ManifestFact(
                        "dependency.declared",
                        "go",
                        f"tool:{tool_name}",
                        {"name": tool_name, "scope": "tool"},
                    )
                )
            else:
                notices.append("go.mod skipped a malformed tool directive")
        elif directive == "retract" and directive_body:
            facts.append(
                ManifestFact(
                    "dependency.declared",
                    "go",
                    f"retract:{directive_body}",
                    {
                        "name": module_path or "current-module",
                        "constraint": directive_body,
                        "scope": "retract",
                    },
                )
            )
        elif directive == "ignore" and directive_body:
            facts.append(
                ManifestFact(
                    "repository.manifest",
                    "go",
                    f"ignore:{directive_body}",
                    {"manifest_type": "go.ignore", "path": directive_body},
                )
            )
        elif directive == "godebug" and directive_body:
            setting, separator, value = directive_body.partition("=")
            if separator and setting and value:
                facts.append(
                    ManifestFact(
                        "runtime.declared",
                        "go",
                        f"godebug:{setting}",
                        {
                            "name": f"godebug:{setting}",
                            "constraint": value,
                            "source": "go.mod",
                        },
                    )
                )
        if len(facts) > MAX_MANIFEST_ITEMS:
            break
    return _bounded_result(facts, notices, "go.mod")


def parse_go_sum(text: str) -> ManifestParseResult:
    """Parse go.sum module and go.mod checksums as resolved evidence."""

    facts: list[ManifestFact] = []
    notices: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 3 or not parts[2].startswith("h1:"):
            notices.append("go.sum skipped a malformed checksum line")
            continue
        path, raw_version, checksum = parts
        content = "go.mod" if raw_version.endswith("/go.mod") else "module"
        version = raw_version.removesuffix("/go.mod")
        facts.append(
            ManifestFact(
                "dependency.locked",
                "go",
                f"sum:{path}:{version}:{content}",
                {
                    "name": path,
                    "version": version,
                    "scope": "go.sum",
                    "content": content,
                    "checksum": checksum,
                },
            )
        )
        if len(facts) > MAX_MANIFEST_ITEMS:
            break
    return _bounded_result(facts, notices, "go.sum")
