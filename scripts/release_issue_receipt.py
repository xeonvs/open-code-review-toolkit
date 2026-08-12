#!/usr/bin/env python3
"""Validate idempotent GitHub issue closure against one release receipt."""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
from pathlib import Path
from typing import Any

BOT_ID = 41898282
BOT_LOGIN = "github-actions[bot]"
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
VERSION_RE = re.compile(r"^[0-9]+(?:\.[0-9]+)+$")


class IssueReceiptError(ValueError):
    """Issue state or its toolkit-owned delivery receipt is inconsistent."""


def receipt_body(version: str, issue: int, receipt_sha: str) -> str:
    """Return the exact stable-delivery receipt comment body."""

    if not VERSION_RE.fullmatch(version) or issue <= 0 or not HASH_RE.fullmatch(receipt_sha):
        raise IssueReceiptError("release receipt identity is invalid")
    marker = f"<!-- ocr-toolkit-release-receipt v={version} issue={issue} -->"
    return (
        f"{marker}\n\nStable v{version} delivery is verified by immutable release asset "
        f"`release-receipt.json` in v{version} (SHA-256 `{receipt_sha}`).\n"
    )


def issue_state(payload: dict[str, Any], issue: int, *, require_closed: bool) -> str:
    """Return one valid tracked-issue state and reject pull requests or wrong closure."""

    if payload.get("number") != issue or "pull_request" in payload:
        raise IssueReceiptError("tracked release issue response is invalid")
    state = payload.get("state")
    reason = payload.get("state_reason")
    if state == "closed" and reason == "completed":
        return state
    if not require_closed and state == "open" and reason is None:
        return state
    raise IssueReceiptError("tracked release issue has an incompatible state")


def comment_state(comments: list[Any], expected_body: str, *, require_comment: bool) -> str:
    """Return whether exactly one GitHub Actions-owned exact receipt exists."""

    marker = expected_body.splitlines()[0]
    marked: list[dict[str, Any]] = []
    for item in comments:
        if not isinstance(item, dict):
            raise IssueReceiptError("issue comment response is malformed")
        body = item.get("body")
        user = item.get("user")
        if isinstance(body, str) and body.startswith(marker):
            marked.append(item)
    if not marked and not require_comment:
        return "missing"
    if len(marked) != 1:
        raise IssueReceiptError("release receipt comment is not uniquely owned by GitHub Actions")
    user = marked[0].get("user")
    if not (
        isinstance(user, dict)
        and user.get("login") == BOT_LOGIN
        and user.get("id") == BOT_ID
        and user.get("type") == "Bot"
    ):
        raise IssueReceiptError("release receipt comment is not uniquely owned by GitHub Actions")
    if marked[0].get("body") != expected_body:
        raise IssueReceiptError("release receipt comment body does not match")
    return "matched"


def load_json(path: Path, *, max_bytes: int) -> Any:
    """Load one bounded regular JSON file through its validated descriptor."""

    flags = os.O_RDONLY
    for name in ("O_CLOEXEC", "O_NOFOLLOW", "O_NONBLOCK", "O_BINARY"):
        flags |= getattr(os, name, 0)
    descriptor = -1
    try:
        path_metadata = os.stat(path, follow_symlinks=False)
        if not stat.S_ISREG(path_metadata.st_mode) or path_metadata.st_nlink != 1:
            raise IssueReceiptError("release issue evidence is unsafe")
        descriptor = os.open(path, flags)
        opened = os.fstat(descriptor)
        if (path_metadata.st_dev, path_metadata.st_ino) != (opened.st_dev, opened.st_ino):
            raise IssueReceiptError("release issue evidence changed while being opened")
        if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1 or opened.st_size > max_bytes:
            raise IssueReceiptError("release issue evidence exceeds its byte limit")
        chunks: list[bytes] = []
        remaining = max_bytes + 1
        while remaining:
            chunk = os.read(descriptor, min(65_536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        payload = b"".join(chunks)
        final = os.fstat(descriptor)
        if (
            len(payload) > max_bytes
            or len(payload) != opened.st_size
            or (opened.st_dev, opened.st_ino, opened.st_mode, opened.st_size)
            != (final.st_dev, final.st_ino, final.st_mode, final.st_size)
            or getattr(opened, "st_mtime_ns", None) != getattr(final, "st_mtime_ns", None)
        ):
            raise IssueReceiptError("release issue evidence changed while being read")
    except IssueReceiptError:
        raise
    except OSError as exc:
        raise IssueReceiptError("release issue evidence is unsafe or unavailable") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    try:
        return json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IssueReceiptError("release issue evidence is not valid JSON") from exc


def main() -> int:
    """CLI entrypoint for the stable release workflow."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--issue-json", type=Path, required=True)
    parser.add_argument("--comments-json", type=Path)
    parser.add_argument("--issue", type=int, required=True)
    parser.add_argument("--version", default="")
    parser.add_argument("--receipt-sha", default="")
    parser.add_argument("--body-output", type=Path)
    parser.add_argument("--validate-issue-only", action="store_true")
    parser.add_argument("--require-comment", action="store_true")
    parser.add_argument("--require-closed", action="store_true")
    args = parser.parse_args()

    raw_issue = load_json(args.issue_json, max_bytes=1048576)
    if not isinstance(raw_issue, dict):
        raise IssueReceiptError("release issue evidence has an invalid top-level shape")
    state = issue_state(raw_issue, args.issue, require_closed=args.require_closed)
    if args.validate_issue_only:
        print(state)
        return 0
    if args.comments_json is None:
        raise IssueReceiptError("release issue comments are required")
    raw_comments = load_json(args.comments_json, max_bytes=6291456)
    if not isinstance(raw_comments, list):
        raise IssueReceiptError("release issue evidence has an invalid top-level shape")
    body = receipt_body(args.version, args.issue, args.receipt_sha)
    comment = comment_state(
        raw_comments,
        body,
        require_comment=args.require_comment,
    )
    if args.body_output is not None:
        args.body_output.write_text(body, encoding="utf-8")
    print(state, comment)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
