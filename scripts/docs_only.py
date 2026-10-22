"""Classify an exact Git range for the narrow documentation-only CI path."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
from pathlib import Path

_SHA = re.compile(r"[0-9a-fA-F]{40}\Z")
_ROOT_MARKDOWN = frozenset(
    {"README.md", "CONTRIBUTING.md", "CODE_OF_CONDUCT.md", "SECURITY.md", "PLANS.md", "ROADMAP.md"}
)
_INTERNAL_WORKFLOWS = frozenset(
    {
        ".github/workflows/ci.yml",
        ".github/workflows/release.yml",
        ".github/workflows/site-release-notify.yml",
        ".github/workflows/testpypi.yml",
    }
)


def documentation_path(path: str) -> bool:
    """Only explicit Markdown documentation paths qualify."""
    return path in _ROOT_MARKDOWN or (path.startswith("docs/") and path.endswith(".md"))


def _changed_paths(base: str, head: str) -> list[str] | None:
    """Return exact simple-path changes, or no decision for uncertain Git evidence."""
    if not _SHA.fullmatch(base) or not _SHA.fullmatch(head):
        return None
    try:
        changed = subprocess.run(
            [
                "git",
                "diff",
                "--no-ext-diff",
                "--find-renames",
                "--name-status",
                "-z",
                base,
                head,
                "--",
            ],
            check=True,
            capture_output=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    fields = [field for field in changed.split(b"\0") if field]
    if len(fields) % 2:
        return None
    paths: list[str] = []
    for status, path in zip(fields[::2], fields[1::2], strict=True):
        if status not in {b"A", b"M", b"D"}:
            return None
        try:
            paths.append(path.decode("utf-8"))
        except UnicodeDecodeError:
            return None
    return paths


def docs_only(base: str, head: str) -> bool:
    """Return true only for a nonempty exact range of allowed documentation paths."""
    paths = _changed_paths(base, head)
    return bool(paths) and all(documentation_path(path) for path in paths)


def development_only_path(path: str) -> bool:
    """Name closed internal paths that cannot change the published package runtime."""
    return (
        documentation_path(path)
        or path in _INTERNAL_WORKFLOWS
        or path == "scripts/docs_only.py"
        or (path.startswith("tests/") and path.endswith(".py"))
    )


def development_only(base: str, head: str) -> bool:
    """Skip dev publication only for a nonempty internal-only main-push range."""
    paths = _changed_paths(base, head)
    return bool(paths) and all(development_only_path(path) for path in paths)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--development", action="store_true")
    args = parser.parse_args()
    key = "development_only" if args.development else "docs_only"
    eligible = development_only if args.development else docs_only
    value = "true" if eligible(args.base, args.head) else "false"
    print(f"{key}={value}")
    if output := os.environ.get("GITHUB_OUTPUT"):
        with Path(output).open("a", encoding="utf-8") as stream:
            stream.write(f"{key}={value}\n")


if __name__ == "__main__":
    main()
