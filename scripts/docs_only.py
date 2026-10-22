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


def documentation_path(path: str) -> bool:
    """Only explicit Markdown documentation paths qualify."""
    return path in _ROOT_MARKDOWN or (path.startswith("docs/") and path.endswith(".md"))


def docs_only(base: str, head: str) -> bool:
    """Return true only for a nonempty exact range of allowed documentation paths."""
    if not _SHA.fullmatch(base) or not _SHA.fullmatch(head):
        raise ValueError("base and head must be full Git commit SHA values")
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
    fields = [field for field in changed.split(b"\0") if field]
    if len(fields) % 2:
        return False
    paths: list[str] = []
    for status, path in zip(fields[::2], fields[1::2], strict=True):
        if status not in {b"A", b"M", b"D"}:
            return False
        try:
            paths.append(path.decode("utf-8"))
        except UnicodeDecodeError:
            return False
    return bool(paths) and all(documentation_path(path) for path in paths)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    args = parser.parse_args()
    value = "true" if docs_only(args.base, args.head) else "false"
    print(f"docs_only={value}")
    if output := os.environ.get("GITHUB_OUTPUT"):
        with Path(output).open("a", encoding="utf-8") as stream:
            stream.write(f"docs_only={value}\n")


if __name__ == "__main__":
    main()
