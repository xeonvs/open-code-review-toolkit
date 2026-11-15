"""Read bounded MSBuild declarations, never evaluate a build or resolve imports."""

from __future__ import annotations

from dataclasses import dataclass, field
from xml.parsers import expat

from ocr_toolkit.evidence.ecosystems.contracts import (
    MAX_MANIFEST_ITEMS,
    ManifestFact,
    ManifestParseResult,
)
from ocr_toolkit.evidence.model import EvidenceValue

MAX_BYTES = 1_000_000
MAX_DEPTH = 32
MAX_ELEMENTS = 4_096
MAX_ATTRIBUTES = 32
MAX_SCALAR = 4_096
PROPERTIES = {
    "targetframework",
    "targetframeworks",
    "langversion",
    "nullable",
    "managepackageversionscentrally",
}


@dataclass(slots=True)
class _Element:
    """Retain inert XML declaration data within the parser's construction budgets."""

    name: str
    attributes: dict[str, str]
    namespace: str = ""
    children: list[_Element] = field(default_factory=list)
    text: str = ""


def bounded_text(text: str) -> None:
    """Reject oversized inputs before parser allocation; bytes are independent."""

    if len(text) > MAX_BYTES or len(text.encode("utf-8")) > MAX_BYTES:
        raise ValueError(".NET manifest byte limit exceeded")


def _tree(text: str) -> _Element:
    """Build a bounded Project tree while refusing entity expansion and external resolution."""
    bounded_text(text)
    parser = expat.ParserCreate(namespace_separator="}")
    stack: list[_Element] = []
    root: _Element | None = None
    count = 0
    pending_namespaces = 0

    def forbidden(*args: object) -> None:
        """Stop resource-bearing XML features before expansion or external access."""
        raise ValueError("DTD and entities are prohibited in .NET evidence")

    def namespace(prefix: str | None, uri: str | None) -> None:
        """Bound namespace declarations before Expat expands qualified element names."""
        nonlocal pending_namespaces
        pending_namespaces += 1
        if pending_namespaces > MAX_ATTRIBUTES:
            raise ValueError(".NET XML namespace construction limit exceeded")
        if len(prefix or "") > MAX_SCALAR or len(uri or "") > MAX_SCALAR:
            raise ValueError(".NET XML namespace scalar limit exceeded")

    def start(name: str, attributes: dict[str, str]) -> None:
        """Admit an element only after depth, scalar and combined attribute checks pass."""
        nonlocal root, count, pending_namespaces
        count += 1
        if (
            count > MAX_ELEMENTS
            or len(stack) >= MAX_DEPTH
            or len(attributes) + pending_namespaces > MAX_ATTRIBUTES
        ):
            raise ValueError(".NET XML construction limit exceeded")
        pending_namespaces = 0
        if len(name) > MAX_SCALAR or any(
            len(key) > MAX_SCALAR or len(value) > MAX_SCALAR for key, value in attributes.items()
        ):
            raise ValueError(".NET XML scalar limit exceeded")
        namespace, _, local_name = name.rpartition("}")
        node = _Element(local_name or name, attributes, namespace)
        if stack:
            stack[-1].children.append(node)
        else:
            root = node
        stack.append(node)

    def characters(value: str) -> None:
        """Retain bounded scalar text without accumulating an unbounded node buffer."""
        if stack:
            node = stack[-1]
            if len(node.text) + len(value) > MAX_SCALAR:
                raise ValueError(".NET XML text limit exceeded")
            node.text += value

    parser.StartDoctypeDeclHandler = forbidden
    parser.EntityDeclHandler = forbidden
    parser.ExternalEntityRefHandler = forbidden
    parser.StartNamespaceDeclHandler = namespace
    parser.StartElementHandler = start
    parser.EndElementHandler = lambda _name: stack.pop()
    parser.CharacterDataHandler = characters
    try:
        parser.Parse(text, True)
    except expat.ExpatError as exc:
        raise ValueError("invalid .NET XML") from exc
    if root is None or root.name.casefold() != "project":
        raise ValueError(".NET XML requires a Project root")
    return root


def parse_msbuild(text: str) -> ManifestParseResult:
    """Keep conditions, alternatives and overrides as declarations with provenance."""

    root = _tree(text)
    facts: list[ManifestFact] = []
    reasons: set[str] = set()

    def add(kind: str, identity: str, value: dict[str, EvidenceValue]) -> None:
        """Reserve the source-state record while capping constructed declaration facts."""
        if len(facts) < MAX_MANIFEST_ITEMS - 1:
            facts.append(ManifestFact(kind, "dotnet", identity, value, source_scoped=True))
        else:
            reasons.add("fact-limit")

    def walk(node: _Element, conditions: tuple[str, ...], location: str, parent: str = "") -> None:
        """Preserve declarations and inherited conditions without evaluating MSBuild."""
        condition = node.attributes.get("Condition")
        conditions = (*conditions, condition) if condition else conditions
        if conditions:
            reasons.add("conditions")
        name = node.name.casefold()
        if node.namespace not in {"", "http://schemas.microsoft.com/developer/msbuild/2003"}:
            reasons.add("unsupported-namespace")
        if (
            (name in PROPERTIES and (parent != "propertygroup" or node.children))
            or (
                name in {"packagereference", "frameworkreference", "packageversion"}
                and parent != "itemgroup"
            )
            or (name == "sdk" and parent != "project")
            or (
                name in {"propertygroup", "itemgroup"}
                and parent not in {"project", "when", "otherwise", "target"}
            )
            or (name == "project" and node is not root)
        ):
            reasons.add("unsupported-structure")
        if name not in PROPERTIES | {
            "project",
            "propertygroup",
            "itemgroup",
            "packagereference",
            "frameworkreference",
            "packageversion",
            "version",
            "versionoverride",
            "sdk",
        }:
            reasons.add("build-evaluation")
        allowed_attributes = {"Condition", "Label"}
        if node is root:
            allowed_attributes.add("Sdk")
        if name in {"packagereference", "frameworkreference", "packageversion"}:
            allowed_attributes.update({"Include", "Update", "Remove", "Version", "VersionOverride"})
        if name == "sdk":
            allowed_attributes.update({"Name", "Version"})
        if set(node.attributes) - allowed_attributes:
            reasons.add("other-attributes")
        if any(
            marker in value
            for value in (node.text, *node.attributes.values())
            for marker in ("$(", "@(", "%(")
        ):
            reasons.add("expressions")
        common: dict[str, EvidenceValue] = {
            "conditions": list(conditions),
            "version_state": "declared",
        }
        if name in PROPERTIES:
            value = node.text.strip()
            add(
                "dotnet.property",
                f"{location}:{name}",
                {
                    **common,
                    "name": node.name,
                    "value": value,
                },
            )
        elif name in {"packagereference", "frameworkreference", "packageversion"}:
            operations = [key for key in ("Include", "Update", "Remove") if key in node.attributes]
            operation = operations[0] if len(operations) == 1 else "unknown"
            package = node.attributes.get(operation, "")
            versions = [node.attributes["Version"]] if "Version" in node.attributes else []
            versions.extend(
                child.text.strip() for child in node.children if child.name.casefold() == "version"
            )
            overrides = (
                [node.attributes["VersionOverride"]] if "VersionOverride" in node.attributes else []
            )
            overrides.extend(
                child.text.strip()
                for child in node.children
                if child.name.casefold() == "versionoverride"
            )
            if (
                operation != "Include"
                or overrides
                or len(versions) > 1
                or any(child.attributes or child.children for child in node.children)
            ):
                reasons.add("item-evaluation")
            if not package:
                reasons.add("missing-item-identity")
            else:
                add(
                    "dotnet.package_version" if name == "packageversion" else "dependency.declared",
                    f"{location}:{name}:{package.casefold()}",
                    {
                        **common,
                        "name": package,
                        "scope": name,
                        "operation": operation,
                        "version": versions[0] if len(versions) == 1 else None,
                        "versions": tuple(versions),
                        "version_overrides": tuple(overrides),
                        "metadata": [
                            {
                                "name": child.name,
                                "value": child.text.strip(),
                                "condition": child.attributes.get("Condition"),
                            }
                            for child in node.children
                        ],
                    },
                )
        sdk = (
            node.attributes.get("Sdk")
            if node is root
            else (node.attributes.get("Name") if name == "sdk" else None)
        )
        if sdk:
            for index, value in enumerate(sdk.split(";")):
                add(
                    "dotnet.sdk",
                    f"{location}:sdk:{index}",
                    {
                        **common,
                        "name": value.strip(),
                        "version": node.attributes.get("Version"),
                    },
                )
        # Unknown declarations may alter automatic discovery or imported values.
        if (
            any(child.name.casefold() not in PROPERTIES for child in node.children)
            and name == "propertygroup"
        ):
            reasons.add("other-properties")
        counts: dict[str, int] = {}
        for child in node.children:
            key = child.name.casefold() + ":" + child.attributes.get("Include", "").casefold()
            index = counts.get(key, 0)
            counts[key] = index + 1
            walk(child, conditions, f"{location}/{key}:{index}", name)

    walk(root, (), "project")
    facts.append(
        ManifestFact(
            "dotnet.source",
            "dotnet",
            "source",
            {
                "interpretation": "runtime-dependent" if reasons else "declared",
                "reasons": tuple(sorted(reasons)),
            },
            source_scoped=True,
        )
    )
    notices = (".NET declarations are partial: " + ", ".join(sorted(reasons)),) if reasons else ()
    if "fact-limit" in reasons:
        notices = (*notices, f".NET facts were truncated after {MAX_MANIFEST_ITEMS} items")
    return ManifestParseResult(tuple(facts), notices, runtime_dependent=bool(reasons))
