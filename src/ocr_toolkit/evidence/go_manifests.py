"""Parse bounded Go module declarations and checksums into normalized facts."""

from __future__ import annotations

from ocr_toolkit.evidence.manifest_model import (
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

    body, separator, comment = raw.partition("//")
    return body.strip(), comment.strip() if separator else None


def _replacement_fact(body: str) -> ManifestFact | None:
    """Parse one replace directive, including local replacements without versions."""

    source, separator, target = body.partition("=>")
    if not separator:
        return None
    source_parts = source.split()
    target_parts = target.split()
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
            module_path = directive_body
            facts.append(
                ManifestFact(
                    "repository.manifest",
                    "go",
                    "module",
                    {"name": directive_body, "manifest_type": "go.module"},
                )
            )
        elif directive in {"go", "toolchain"} and directive_body:
            facts.append(
                ManifestFact(
                    "runtime.declared",
                    "go",
                    directive,
                    {
                        "name": directive,
                        "constraint": directive_body,
                        "source": "go.mod",
                    },
                )
            )
        elif directive == "require":
            parts = directive_body.split()
            if len(parts) == 2:
                scope = "indirect" if comment == "indirect" else "direct"
                facts.append(_module_fact("dependency.declared", parts[0], parts[1], scope))
        elif directive == "replace":
            if (fact := _replacement_fact(directive_body)) is not None:
                facts.append(fact)
        elif directive == "exclude":
            parts = directive_body.split()
            if len(parts) == 2:
                facts.append(_module_fact("dependency.declared", parts[0], parts[1], "exclude"))
        elif directive == "tool" and directive_body:
            facts.append(
                ManifestFact(
                    "dependency.declared",
                    "go",
                    f"tool:{directive_body}",
                    {"name": directive_body, "scope": "tool"},
                )
            )
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
