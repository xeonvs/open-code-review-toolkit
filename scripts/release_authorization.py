#!/usr/bin/env python3
"""Validate one merged release pull request and emit constrained workflow outputs."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
VERSION_RE = re.compile(r"^[0-9]+(?:\.[0-9]+)+$")


class AuthorizationError(ValueError):
    """The pull request does not authorize a stable release."""


def authorize_release(
    payload: dict[str, Any],
    repository: str,
    requested_version: str = "",
    requested_commit: str = "",
) -> dict[str, str]:
    """Return safe workflow outputs for one exact repository-owned release merge."""

    base = payload.get("base")
    head = payload.get("head")
    if not isinstance(base, dict) or not isinstance(head, dict):
        raise AuthorizationError("pull request is missing base or head metadata")
    head_repo = head.get("repo")
    if not isinstance(head_repo, dict):
        raise AuthorizationError("pull request is missing head repository metadata")

    branch = head.get("ref")
    title = payload.get("title")
    commit = payload.get("merge_commit_sha")
    number = payload.get("number")
    if payload.get("merged") is not True or not payload.get("merged_at"):
        raise AuthorizationError("pull request is not merged")
    if base.get("ref") != "main":
        raise AuthorizationError("release pull request base must be main")
    if head_repo.get("full_name") != repository:
        raise AuthorizationError("release pull request must come from the same repository")
    if not isinstance(branch, str) or not branch.startswith("release/v"):
        raise AuthorizationError("release pull request branch must start with release/v")
    version = branch.removeprefix("release/v")
    if not VERSION_RE.fullmatch(version):
        raise AuthorizationError("release version must be a final dotted numeric version")
    if title != f"Release v{version}":
        raise AuthorizationError("release pull request title does not match its branch")
    if not isinstance(commit, str) or not COMMIT_RE.fullmatch(commit):
        raise AuthorizationError("release merge commit is not a full lowercase SHA")
    if not isinstance(number, int) or number < 1:
        raise AuthorizationError("release pull request number is invalid")
    if requested_version and requested_version != version:
        raise AuthorizationError("requested version does not match the release pull request")
    if requested_commit and requested_commit != commit:
        raise AuthorizationError("requested commit does not match the release pull request")

    return {
        "approved": "true",
        "branch": branch,
        "commit": commit,
        "pr-number": str(number),
        "title": title,
        "version": version,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pr-json", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--requested-version", default="")
    parser.add_argument("--requested-commit", default="")
    parser.add_argument("--github-output", type=Path, required=True)
    args = parser.parse_args()

    payload = json.loads(args.pr_json.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AuthorizationError("pull request response must be a JSON object")
    outputs = authorize_release(
        payload, args.repository, args.requested_version, args.requested_commit
    )
    with args.github_output.open("a", encoding="utf-8") as output:
        for key, value in outputs.items():
            output.write(f"{key}={value}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
