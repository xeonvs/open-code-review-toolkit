#!/usr/bin/env python3
"""Validate one merged release pull request and emit constrained workflow outputs."""

from __future__ import annotations

import argparse
import base64
import json
import re
from pathlib import Path
from typing import Any

COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
VERSION_RE = re.compile(r"^[0-9]+(?:\.[0-9]+)+$")
RELEASE_METADATA_SCHEMA = "ocr-toolkit.release-authorization/v1"


class AuthorizationError(ValueError):
    """The pull request does not authorize a stable release."""


def _full_commit(value: Any, field: str) -> str:
    """Return one validated full lowercase commit SHA."""

    if not isinstance(value, str) or not COMMIT_RE.fullmatch(value):
        raise AuthorizationError(f"{field} is not a full lowercase SHA")
    return value


def _commit_metadata(
    payload: dict[str, Any], expected_sha: str, field: str
) -> tuple[str, list[str]]:
    """Return a validated tree SHA and parent list from one GitHub commit payload."""

    if _full_commit(payload.get("sha"), f"{field} commit") != expected_sha:
        raise AuthorizationError(f"{field} commit response does not match the pull request")
    commit = payload.get("commit")
    if not isinstance(commit, dict):
        raise AuthorizationError(f"{field} commit is missing metadata")
    tree = commit.get("tree")
    if not isinstance(tree, dict):
        raise AuthorizationError(f"{field} commit is missing tree metadata")
    tree_sha = _full_commit(tree.get("sha"), f"{field} tree")
    raw_parents = payload.get("parents")
    if not isinstance(raw_parents, list):
        raise AuthorizationError(f"{field} commit is missing parent metadata")
    parents: list[str] = []
    for index, parent in enumerate(raw_parents):
        if not isinstance(parent, dict):
            raise AuthorizationError(f"{field} parent {index} is malformed")
        parents.append(_full_commit(parent.get("sha"), f"{field} parent {index}"))
    return tree_sha, parents


def _release_metadata(payload: dict[str, Any], version: str) -> tuple[int, ...]:
    """Validate tracked release authorization metadata and return issue IDs."""

    if payload.get("schema_version") != RELEASE_METADATA_SCHEMA:
        raise AuthorizationError("release metadata schema is unsupported")
    if payload.get("version") != version:
        raise AuthorizationError("release metadata version does not match the release branch")
    issues = payload.get("issues")
    if (
        not isinstance(issues, list)
        or not issues
        or any(
            isinstance(issue, bool) or not isinstance(issue, int) or issue <= 0 for issue in issues
        )
        or len(set(issues)) != len(issues)
        or issues != sorted(issues)
    ):
        raise AuthorizationError("release metadata issues must be unique sorted positive integers")
    return tuple(issues)


def _release_metadata_contents(payload: dict[str, Any]) -> dict[str, Any]:
    """Decode one exact-ref GitHub Contents API response within a small bound."""

    content = payload.get("content")
    size = payload.get("size")
    if (
        payload.get("type") != "file"
        or payload.get("name") != ".release-metadata.json"
        or payload.get("path") != ".release-metadata.json"
        or payload.get("encoding") != "base64"
        or isinstance(size, bool)
        or not isinstance(size, int)
        or size <= 0
        or size > 4096
        or not isinstance(content, str)
    ):
        raise AuthorizationError("release metadata contents response is malformed")
    compact_content = "".join(content.split())
    try:
        raw = base64.b64decode(compact_content, validate=True)
    except ValueError as exc:
        raise AuthorizationError("release metadata contents response is malformed") from exc
    if len(raw) != size:
        raise AuthorizationError("release metadata contents size does not match")
    try:
        metadata = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AuthorizationError("release metadata contents are not valid JSON") from exc
    if not isinstance(metadata, dict):
        raise AuthorizationError("release metadata must be a JSON object")
    return metadata


def _required_checks(ruleset: dict[str, Any]) -> dict[tuple[str, int], None]:
    """Return the effective main-branch required check contexts and apps."""

    rules = ruleset.get("rules")
    if not isinstance(rules, list):
        raise AuthorizationError("effective main rules are missing")
    status_rules = [
        rule
        for rule in rules
        if isinstance(rule, dict) and rule.get("type") == "required_status_checks"
    ]
    if not status_rules:
        raise AuthorizationError("main ruleset has no required status checks")
    required: dict[tuple[str, int], None] = {}
    for rule in status_rules:
        parameters = rule.get("parameters")
        checks = parameters.get("required_status_checks") if isinstance(parameters, dict) else None
        if not isinstance(checks, list):
            raise AuthorizationError("required status check list is malformed")
        if parameters.get("strict_required_status_checks_policy") is not True:
            raise AuthorizationError("main required checks must use strict base synchronization")
        for item in checks:
            if not isinstance(item, dict):
                raise AuthorizationError("required status check is malformed")
            context = item.get("context")
            integration_id = item.get("integration_id")
            if (
                not isinstance(context, str)
                or not context
                or isinstance(integration_id, bool)
                or not isinstance(integration_id, int)
                or integration_id <= 0
            ):
                raise AuthorizationError("required status check identity is malformed")
            identity = (context, integration_id)
            if identity in required:
                raise AuthorizationError("required status check identity is duplicated")
            required[identity] = None
    if not required:
        raise AuthorizationError("main ruleset has no required status checks")
    return required


def _validate_check_runs(
    checks_payload: dict[str, Any], ruleset: dict[str, Any], expected_head: str
) -> None:
    """Require one complete exact-app run for every live ruleset context."""

    required = _required_checks(ruleset)
    raw_runs = checks_payload.get("check_runs")
    total_count = checks_payload.get("total_count")
    if (
        not isinstance(raw_runs, list)
        or isinstance(total_count, bool)
        or not isinstance(total_count, int)
        or total_count != len(raw_runs)
        or total_count > 100
    ):
        raise AuthorizationError("check-runs response is malformed")
    matched: dict[tuple[str, int], None] = {}
    for run in raw_runs:
        if not isinstance(run, dict):
            raise AuthorizationError("check-run entry is malformed")
        name = run.get("name")
        app = run.get("app")
        app_id = app.get("id") if isinstance(app, dict) else None
        if not isinstance(name, str) or isinstance(app_id, bool) or not isinstance(app_id, int):
            continue
        identity = (name, app_id)
        if identity not in required:
            continue
        if identity in matched:
            raise AuthorizationError(f"reviewed head has duplicate required check: {identity}")
        if run.get("head_sha") != expected_head:
            raise AuthorizationError(
                f"required check is not bound to the reviewed head: {identity}"
            )
        if run.get("status") != "completed" or run.get("conclusion") != "success":
            raise AuthorizationError(f"reviewed head has unsuccessful required check: {identity}")
        matched[identity] = None
    missing = [identity for identity in required if identity not in matched]
    if missing:
        raise AuthorizationError(f"reviewed head is missing required checks: {missing}")


def authorize_release(
    payload: dict[str, Any],
    repository: str,
    head_commit_payload: dict[str, Any],
    merge_commit_payload: dict[str, Any],
    check_runs_payload: dict[str, Any],
    ruleset_payload: dict[str, Any],
    release_metadata_contents: dict[str, Any],
    requested_version: str = "",
    requested_commit: str = "",
    requested_head: str = "",
    requested_base: str = "",
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
    merged_at = payload.get("merged_at")
    if not isinstance(merged_at, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", merged_at
    ):
        raise AuthorizationError("release merge timestamp is invalid")
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
    commit = _full_commit(commit, "release merge commit")
    base_sha = _full_commit(base.get("sha"), "release base commit")
    head_sha = _full_commit(head.get("sha"), "reviewed release head")
    if not isinstance(number, int) or number < 1:
        raise AuthorizationError("release pull request number is invalid")
    if requested_version and requested_version != version:
        raise AuthorizationError("requested version does not match the release pull request")
    if requested_commit and requested_commit != commit:
        raise AuthorizationError("requested commit does not match the release pull request")
    if requested_head and requested_head != head_sha:
        raise AuthorizationError("requested head does not match the release pull request")
    if requested_base and requested_base != base_sha:
        raise AuthorizationError("requested base does not match the release pull request")

    head_tree, _head_parents = _commit_metadata(head_commit_payload, head_sha, "head")
    merge_tree, merge_parents = _commit_metadata(merge_commit_payload, commit, "merge")
    if merge_tree != head_tree:
        raise AuthorizationError("release merge tree does not match the reviewed head tree")
    if merge_parents != [base_sha]:
        raise AuthorizationError("release merge parent does not match the reviewed base")
    issues = _release_metadata(_release_metadata_contents(release_metadata_contents), version)
    _validate_check_runs(check_runs_payload, ruleset_payload, head_sha)

    return {
        "approved": "true",
        "branch": branch,
        "commit": commit,
        "base": base_sha,
        "head": head_sha,
        "tree": head_tree,
        "issues": ",".join(str(issue) for issue in issues),
        "merged-at": merged_at,
        "pr-number": str(number),
        "title": title,
        "version": version,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pr-json", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--head-commit-json", type=Path, required=True)
    parser.add_argument("--merge-commit-json", type=Path, required=True)
    parser.add_argument("--check-runs-json", type=Path, required=True)
    parser.add_argument("--ruleset-json", type=Path, required=True)
    parser.add_argument("--release-metadata-contents-json", type=Path, required=True)
    parser.add_argument("--requested-version", default="")
    parser.add_argument("--requested-commit", default="")
    parser.add_argument("--requested-head", default="")
    parser.add_argument("--requested-base", default="")
    parser.add_argument("--github-output", type=Path, required=True)
    args = parser.parse_args()

    payload = json.loads(args.pr_json.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AuthorizationError("pull request response must be a JSON object")

    def load_object(path: Path, description: str) -> dict[str, Any]:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise AuthorizationError(f"{description} must be a JSON object")
        return value

    outputs = authorize_release(
        payload,
        args.repository,
        load_object(args.head_commit_json, "head commit response"),
        load_object(args.merge_commit_json, "merge commit response"),
        load_object(args.check_runs_json, "check-runs response"),
        load_object(args.ruleset_json, "ruleset response"),
        load_object(args.release_metadata_contents_json, "release metadata contents response"),
        args.requested_version,
        args.requested_commit,
        args.requested_head,
        args.requested_base,
    )
    with args.github_output.open("a", encoding="utf-8") as output:
        for key, value in outputs.items():
            output.write(f"{key}={value}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
