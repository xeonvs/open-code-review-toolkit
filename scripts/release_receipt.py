#!/usr/bin/env python3
"""Build and validate the deterministic stable-release delivery receipt."""

from __future__ import annotations

import argparse
import json
import re
import tomllib
from pathlib import Path
from typing import Any

SCHEMA = "ocr-toolkit.release-receipt/v1"
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
VERSION_RE = re.compile(r"^[0-9]+(?:\.[0-9]+)+$")


class ReceiptError(ValueError):
    """Release evidence is incomplete or internally inconsistent."""


def supported_python_minors(pyproject: dict[str, Any]) -> list[str]:
    """Return the contiguous supported minor range from canonical project metadata."""

    project = pyproject.get("project")
    requires = project.get("requires-python") if isinstance(project, dict) else None
    match = re.fullmatch(r">=3\.(\d+),<3\.(\d+)", str(requires or ""))
    if match is None:
        raise ReceiptError("requires-python must be a contiguous >=3.X,<3.Y range")
    lower, upper = (int(value) for value in match.groups())
    if lower >= upper or upper - lower > 10:
        raise ReceiptError("requires-python minor range is invalid")
    return [f"3.{minor}" for minor in range(lower, upper)]


def load_hashes(path: Path) -> dict[str, str]:
    """Load the exact two-distribution SHA-256 mapping."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(payload, dict)
        or len(payload) != 2
        or not all(
            isinstance(name, str) and isinstance(digest, str) and HASH_RE.fullmatch(digest)
            for name, digest in payload.items()
        )
    ):
        raise ReceiptError("artifact hashes must contain exactly two SHA-256 entries")
    return dict(sorted(payload.items()))


def build_receipt(
    *,
    version: str,
    tag: str,
    release_pr: int,
    issues: list[int],
    base: str,
    head: str,
    merge: str,
    tree: str,
    run_id: int,
    run_attempt: int,
    authorized_at: str,
    artifacts: dict[str, str],
    python_minors: list[str],
) -> dict[str, Any]:
    """Return one canonical receipt after all pre-Release gates succeeded."""

    commits = {"base": base, "head": head, "merge": merge, "tree": tree}
    if not VERSION_RE.fullmatch(version) or tag != f"v{version}":
        raise ReceiptError("release version and tag are inconsistent")
    if any(not COMMIT_RE.fullmatch(value) for value in commits.values()):
        raise ReceiptError("release commit/tree identities must be full lowercase SHAs")
    if (
        release_pr <= 0
        or run_id <= 0
        or run_attempt <= 0
        or issues != sorted(set(issues))
        or not issues
        or any(
            isinstance(issue, bool) or not isinstance(issue, int) or issue <= 0 for issue in issues
        )
    ):
        raise ReceiptError("release PR, run, or issue identity is invalid")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", authorized_at):
        raise ReceiptError("release authorization timestamp must be UTC")
    expected_artifacts = {
        f"open_code_review_toolkit-{version}-py3-none-any.whl",
        f"open_code_review_toolkit-{version}.tar.gz",
    }
    if set(artifacts) != expected_artifacts or any(
        not HASH_RE.fullmatch(digest) for digest in artifacts.values()
    ):
        raise ReceiptError("artifact hashes are invalid")
    parsed_python: list[int] = []
    for value in python_minors:
        match = re.fullmatch(r"3\.(\d+)", value)
        if match is None:
            raise ReceiptError("supported Python receipt is invalid")
        parsed_python.append(int(match.group(1)))
    if (
        not parsed_python
        or parsed_python != sorted(set(parsed_python))
        or parsed_python != list(range(parsed_python[0], parsed_python[-1] + 1))
    ):
        raise ReceiptError("supported Python receipt is invalid")

    return {
        "schema_version": SCHEMA,
        "version": version,
        "tag": tag,
        "release_pr": release_pr,
        "issues": issues,
        "reviewed": commits,
        "workflow": {"run_id": run_id, "run_attempt": run_attempt},
        # The merged release PR is the human authorization event. Using that
        # immutable GitHub timestamp keeps receipt creation deterministic on recovery.
        "authorized_at": authorized_at,
        "artifacts": artifacts,
        "registries": {
            "testpypi": {"artifacts": "verified", "provenance": "verified"},
            "pypi": {"artifacts": "verified", "provenance": "verified"},
        },
        "github": {
            "artifact_attestations": "verified",
            "annotated_tag_target": merge,
            "release_assets": "pending_self_readback",
        },
        "python_smoke": {minor: "verified" for minor in python_minors},
    }


def validate_receipt(
    payload: dict[str, Any],
    *,
    version: str,
    tag: str,
    release_pr: int,
    issues: list[int],
    base: str,
    head: str,
    merge: str,
    tree: str,
    authorized_at: str,
    artifacts: dict[str, str],
    python_minors: list[str],
) -> None:
    """Validate an immutable prior-run receipt against current recovery evidence."""

    expected = build_receipt(
        version=version,
        tag=tag,
        release_pr=release_pr,
        issues=issues,
        base=base,
        head=head,
        merge=merge,
        tree=tree,
        run_id=1,
        run_attempt=1,
        authorized_at=authorized_at,
        artifacts=artifacts,
        python_minors=python_minors,
    )
    for key in (
        "schema_version",
        "version",
        "tag",
        "release_pr",
        "issues",
        "reviewed",
        "artifacts",
        "registries",
        "github",
        "python_smoke",
    ):
        if payload.get(key) != expected[key]:
            raise ReceiptError(f"existing release receipt field {key!r} does not match")
    workflow = payload.get("workflow")
    if not isinstance(workflow, dict):
        raise ReceiptError("existing release receipt workflow identity is invalid")
    run_id = workflow.get("run_id")
    run_attempt = workflow.get("run_attempt")
    if (
        isinstance(run_id, bool)
        or not isinstance(run_id, int)
        or run_id <= 0
        or isinstance(run_attempt, bool)
        or not isinstance(run_attempt, int)
        or run_attempt <= 0
    ):
        raise ReceiptError("existing release receipt workflow identity is invalid")
    if payload.get("authorized_at") != expected["authorized_at"]:
        raise ReceiptError("existing release receipt authorization timestamp does not match")


def main() -> int:
    """CLI entrypoint for the stable release workflow."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate-existing", type=Path)
    parser.add_argument("--version", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--release-pr", required=True, type=int)
    parser.add_argument("--issues", required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--merge", required=True)
    parser.add_argument("--tree", required=True)
    parser.add_argument("--run-id", type=int)
    parser.add_argument("--run-attempt", type=int)
    parser.add_argument("--authorized-at", required=True)
    parser.add_argument("--hashes", required=True, type=Path)
    parser.add_argument("--pyproject", default=Path("pyproject.toml"), type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    issues = [int(value) for value in args.issues.split(",") if value]
    pyproject = tomllib.loads(args.pyproject.read_text(encoding="utf-8"))
    common: dict[str, Any] = {
        "version": args.version,
        "tag": args.tag,
        "release_pr": args.release_pr,
        "issues": issues,
        "base": args.base,
        "head": args.head,
        "merge": args.merge,
        "tree": args.tree,
        "authorized_at": args.authorized_at,
        "artifacts": load_hashes(args.hashes),
        "python_minors": supported_python_minors(pyproject),
    }
    if args.validate_existing is not None:
        payload = json.loads(args.validate_existing.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ReceiptError("existing release receipt must be a JSON object")
        validate_receipt(payload, **common)
        return 0
    if args.run_id is None or args.run_attempt is None or args.output is None:
        raise ReceiptError("receipt creation requires run identity and output")
    receipt = build_receipt(
        **common,
        run_id=args.run_id,
        run_attempt=args.run_attempt,
    )
    args.output.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
