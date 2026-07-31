#!/usr/bin/env python3
"""Extract one exact Towncrier release section for GitHub Release notes."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from urllib.parse import urlsplit

REPOSITORY_URL = "https://github.com/xeonvs/open-code-review-toolkit"
STABLE_VERSION = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+")
RELEASE_HEADING = re.compile(r"^## (?P<version>[0-9]+\.[0-9]+\.[0-9]+)(?: - .+)?$", re.MULTILINE)


def _validated_repository_url(repository_url: str) -> str:
    """Return the canonical repository URL after strict public-origin validation."""

    parsed = urlsplit(repository_url)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "github.com"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port is not None
        or parsed.query
        or parsed.fragment
        or parsed.path != "/xeonvs/open-code-review-toolkit"
    ):
        raise ValueError("repository URL is not the canonical toolkit repository")
    return repository_url.rstrip("/")


def release_notes(changelog: str, version: str, repository_url: str = REPOSITORY_URL) -> str:
    """Extract one stable release and append its adjacent comparison URL."""

    if STABLE_VERSION.fullmatch(version) is None:
        raise ValueError(f"invalid stable version: {version}")
    repository = _validated_repository_url(repository_url)
    headings = list(RELEASE_HEADING.finditer(changelog))
    selected_index = next(
        (index for index, match in enumerate(headings) if match.group("version") == version),
        None,
    )
    if selected_index is None:
        raise ValueError(f"CHANGELOG.md has no {version} release section")
    if selected_index + 1 >= len(headings):
        raise ValueError(f"CHANGELOG.md has no previous stable release after {version}")
    match = headings[selected_index]
    previous = headings[selected_index + 1].group("version")
    if previous == version:
        raise ValueError(f"CHANGELOG.md repeats release section {version}")
    end = headings[selected_index + 1].start()
    section = changelog[match.start() : end].strip()
    if not section:
        raise ValueError(f"CHANGELOG.md has an empty {version} release section")
    comparison = f"{repository}/compare/v{previous}...v{version}"
    return f"{section}\n\n**Full Changelog**: {comparison}\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    parser.add_argument("--changelog", type=Path, default=Path("CHANGELOG.md"))
    parser.add_argument("--repository-url", default=REPOSITORY_URL)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(
        release_notes(
            args.changelog.read_text(encoding="utf-8"),
            args.version,
            args.repository_url,
        ),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
