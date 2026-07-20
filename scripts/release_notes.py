#!/usr/bin/env python3
"""Extract one exact Towncrier release section for GitHub Release notes."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


def release_notes(changelog: str, version: str) -> str:
    heading = re.compile(rf"^## {re.escape(version)}(?: - .+)?$", re.MULTILINE)
    match = heading.search(changelog)
    if match is None:
        raise ValueError(f"CHANGELOG.md has no {version} release section")
    next_heading = re.search(r"^## \S", changelog[match.end() :], re.MULTILINE)
    end = match.end() + next_heading.start() if next_heading else len(changelog)
    section = changelog[match.start() : end].strip()
    if not section:
        raise ValueError(f"CHANGELOG.md has an empty {version} release section")
    return section + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    parser.add_argument("--changelog", type=Path, default=Path("CHANGELOG.md"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(
        release_notes(args.changelog.read_text(encoding="utf-8"), args.version),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
