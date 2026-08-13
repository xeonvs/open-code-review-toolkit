"""Derive safe applicability and precedence for target guidance documents."""

from __future__ import annotations

from pathlib import PurePosixPath

from ocr_toolkit.evidence.policy.contracts import GuidanceDocument

NESTED_GUIDANCE_NAMES = ("AGENTS.md", "CLAUDE.md")
ROOT_GUIDANCE_PATHS = ("PR_REVIEW.md", ".cursorrules", ".github/copilot-instructions.md")
MAX_MATCHED_PATHS = 64
MAX_GUIDANCE_TEXT_CHARS = 64_000


def _safe_guidance_path(path: str) -> PurePosixPath:
    """Validate one persisted guidance path without importing Git orchestration."""

    if (
        not path
        or path.startswith("/")
        or "\\" in path
        or any(part in {"", ".", ".."} for part in path.split("/"))
        or any(character == "\x7f" or ord(character) < 32 for character in path)
    ):
        raise ValueError("guidance path must be normalized and repository-relative")
    return PurePosixPath(path)


def is_guidance_path(path: str) -> bool:
    """Return whether a path is a supported global or nested guidance source."""

    try:
        candidate = _safe_guidance_path(path)
    except ValueError:
        return False
    return path in ROOT_GUIDANCE_PATHS or candidate.name in NESTED_GUIDANCE_NAMES


def guidance_metadata(path: str) -> tuple[str, str, int, int]:
    """Return the exact document type, scope, depth, and order for a safe path."""

    candidate = _safe_guidance_path(path)
    if not is_guidance_path(path):
        raise ValueError("path is not a registered guidance source")
    name = candidate.name
    nested = name in NESTED_GUIDANCE_NAMES
    parent = candidate.parent.as_posix()
    directory = "." if parent == "." else parent
    scope = "**" if not nested or directory == "." else f"{directory}/**"
    depth = 0 if not nested or directory == "." else len(directory.split("/"))
    document_order = 0 if name == "AGENTS.md" else 1 if name == "CLAUDE.md" else 2
    return name, scope, depth, document_order


def guidance_document(path: str, text: str, changed_paths: tuple[str, ...]) -> GuidanceDocument:
    """Build one target-only guidance record with deterministic applicability."""

    if len(text) > MAX_GUIDANCE_TEXT_CHARS:
        raise ValueError("guidance text exceeds the policy character budget")
    name, scope, depth, document_order = guidance_metadata(path)
    nested = name in NESTED_GUIDANCE_NAMES
    parent = PurePosixPath(path).parent.as_posix()
    directory = "." if parent == "." else parent
    if nested:
        prefix = "" if directory == "." else f"{directory}/"
        matched = tuple(item for item in changed_paths if item.startswith(prefix))[
            :MAX_MATCHED_PATHS
        ]
    else:
        matched = changed_paths[:MAX_MATCHED_PATHS]
    applicability = (
        "applicable" if matched or (not nested and not changed_paths) else "not_applicable"
    )
    return GuidanceDocument(
        path=path,
        document_type=name,
        scope=scope,
        text=text,
        applicability=applicability,  # type: ignore[arg-type]
        matched_paths=matched,
        depth=depth,
        document_order=document_order,
    )
