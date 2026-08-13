"""Derive safe applicability and precedence for target guidance documents."""

from __future__ import annotations

from pathlib import PurePosixPath

from ocr_toolkit.evidence.policy.contracts import GuidanceDocument

NESTED_GUIDANCE_NAMES = ("AGENTS.md", "CLAUDE.md")
ROOT_GUIDANCE_PATHS = ("PR_REVIEW.md", ".cursorrules", ".github/copilot-instructions.md")
MAX_MATCHED_PATHS = 64


def is_guidance_path(path: str) -> bool:
    """Return whether a path is a supported global or nested guidance source."""

    return path in ROOT_GUIDANCE_PATHS or PurePosixPath(path).name in NESTED_GUIDANCE_NAMES


def guidance_document(path: str, text: str, changed_paths: tuple[str, ...]) -> GuidanceDocument:
    """Build one target-only guidance record with deterministic applicability."""

    name = PurePosixPath(path).name
    nested = name in NESTED_GUIDANCE_NAMES
    parent = PurePosixPath(path).parent.as_posix()
    directory = "." if parent == "." else parent
    if nested:
        prefix = "" if directory == "." else f"{directory}/"
        matched = tuple(item for item in changed_paths if item.startswith(prefix))[
            :MAX_MATCHED_PATHS
        ]
        scope = "**" if directory == "." else f"{directory}/**"
    else:
        matched = changed_paths[:MAX_MATCHED_PATHS]
        scope = "**"
    applicability = "applicable" if matched or not changed_paths else "not_applicable"
    return GuidanceDocument(
        path=path,
        document_type=name,
        scope=scope,
        text=text,
        applicability=applicability,  # type: ignore[arg-type]
        matched_paths=matched,
        depth=0 if directory == "." else len(directory.split("/")),
        document_order=0 if name == "AGENTS.md" else 1 if name == "CLAUDE.md" else 2,
    )
