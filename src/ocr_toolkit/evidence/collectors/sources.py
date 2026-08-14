"""Extract bounded cross-ecosystem facts from selected text sources."""

from __future__ import annotations

import re
from pathlib import PurePosixPath

from ocr_toolkit.evidence.ecosystems.contracts import MAX_MANIFEST_ITEMS, ManifestFact

IMAGE_LINE_RE = re.compile(r"^\s*(?:-\s*)?image\s*:\s*['\"]?([^'\"\s#]+)")
CONTEXT_YAML_DIRECTORIES = (
    ".circleci/",
    ".github/workflows/",
    "deploy/",
    "k8s/",
    "kubernetes/",
    "manifests/",
)


def _image_reference(reference: str) -> tuple[str, str | None]:
    """Split an OCI-style reference into stable name and mutable version parts."""

    if "@" in reference:
        name, digest = reference.rsplit("@", 1)
        return name, digest
    slash = reference.rfind("/")
    colon = reference.rfind(":")
    if colon > slash:
        return reference[:colon], reference[colon + 1 :]
    return reference, None


def image_facts(path: str, text: str) -> list[ManifestFact]:
    """Extract bounded exact image references from CI/container YAML lines."""

    kind = (
        "ci.image"
        if PurePosixPath(path).name.casefold().startswith(".gitlab-ci")
        else "container.image"
    )
    facts = []
    for line in text.splitlines():
        match = IMAGE_LINE_RE.match(line)
        if match:
            image = match.group(1)
            name, version = _image_reference(image)
            facts.append(
                ManifestFact(
                    kind,
                    "ci" if kind == "ci.image" else "container",
                    name.casefold(),
                    {"image": image, "name": name, "version": version},
                )
            )
        if len(facts) >= MAX_MANIFEST_ITEMS:
            break
    return facts


def is_context_yaml(path: str, changed: set[str]) -> bool:
    """Select YAML that can affect this review or a known CI/container surface."""

    folded = path.casefold()
    if not folded.endswith((".yml", ".yaml")):
        return False
    name = PurePosixPath(folded).name
    return (
        folded in changed
        or name.startswith((".gitlab-ci", "compose.", "docker-compose."))
        or folded.startswith(CONTEXT_YAML_DIRECTORIES)
    )
