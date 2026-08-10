"""Tests for stable release pull-request authorization."""

from __future__ import annotations

import base64
import importlib.util
import json
from copy import deepcopy
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts" / "release_authorization.py"
WORKFLOW = Path(__file__).parents[1] / ".github" / "workflows" / "release.yml"
BOUNDED_API = Path(__file__).parents[1] / "scripts" / "bounded_github_api.sh"


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("release_authorization_script", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


release = load_script()


def release_pr() -> dict[str, Any]:
    return {
        "number": 5,
        "merged": True,
        "merged_at": "2026-07-20T10:00:00Z",
        "merge_commit_sha": "a" * 40,
        "title": "Release v0.1.0",
        "base": {"ref": "main", "sha": "b" * 40},
        "head": {
            "ref": "release/v0.1.0",
            "sha": "c" * 40,
            "repo": {"full_name": "example/open-code-review-toolkit"},
        },
    }


def commit_payload(sha: str, tree: str, parents: list[str]) -> dict[str, Any]:
    return {
        "sha": sha,
        "commit": {"tree": {"sha": tree}},
        "parents": [{"sha": parent} for parent in parents],
    }


def ruleset() -> dict[str, Any]:
    return {
        "rules": [
            {
                "type": "required_status_checks",
                "parameters": {
                    "strict_required_status_checks_policy": True,
                    "required_status_checks": [
                        {"context": "quality", "integration_id": 15368},
                        {"context": "CodeQL", "integration_id": 57789},
                    ],
                },
            }
        ],
    }


def check_runs() -> dict[str, Any]:
    return {
        "total_count": 2,
        "check_runs": [
            {
                "name": "quality",
                "conclusion": "success",
                "status": "completed",
                "head_sha": "c" * 40,
                "completed_at": "2026-08-10T10:00:00Z",
                "app": {"id": 15368},
            },
            {
                "name": "CodeQL",
                "conclusion": "success",
                "status": "completed",
                "head_sha": "c" * 40,
                "completed_at": "2026-08-10T10:01:00Z",
                "app": {"id": 57789},
            },
        ],
    }


def release_metadata() -> dict[str, Any]:
    return {
        "schema_version": "ocr-toolkit.release-authorization/v1",
        "version": "0.1.0",
        "issues": [70, 71],
    }


def release_metadata_contents(metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return one bounded GitHub Contents API response."""

    raw = json.dumps(release_metadata() if metadata is None else metadata).encode()
    return {
        "type": "file",
        "name": ".release-metadata.json",
        "path": ".release-metadata.json",
        "encoding": "base64",
        "size": len(raw),
        "content": base64.b64encode(raw).decode(),
    }


def authorize(
    payload: dict[str, Any] | None = None,
    *,
    head: dict[str, Any] | None = None,
    merge: dict[str, Any] | None = None,
    checks: dict[str, Any] | None = None,
    protection: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    requested_version: str = "",
    requested_commit: str = "",
    requested_head: str = "",
) -> dict[str, str]:
    """Call authorization with fully valid synthetic GitHub evidence by default."""

    return release.authorize_release(
        payload or release_pr(),
        "example/open-code-review-toolkit",
        head or commit_payload("c" * 40, "d" * 40, ["e" * 40]),
        merge or commit_payload("a" * 40, "d" * 40, ["b" * 40]),
        checks or check_runs(),
        protection or ruleset(),
        release_metadata_contents(metadata),
        requested_version,
        requested_commit,
        requested_head,
    )


def test_authorizes_exact_same_repository_release_merge() -> None:
    outputs = authorize(
        requested_version="0.1.0",
        requested_commit="a" * 40,
        requested_head="c" * 40,
    )

    assert outputs == {
        "approved": "true",
        "branch": "release/v0.1.0",
        "commit": "a" * 40,
        "base": "b" * 40,
        "head": "c" * 40,
        "tree": "d" * 40,
        "issues": "70,71",
        "merged-at": "2026-07-20T10:00:00Z",
        "pr-number": "5",
        "title": "Release v0.1.0",
        "version": "0.1.0",
    }


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("merged",), False),
        (("base", "ref"), "develop"),
        (("head", "ref"), "feature/release"),
        (("head", "repo", "full_name"), "attacker/fork"),
        (("title",), "Release v9.9.9"),
        (("merge_commit_sha",), "not-a-sha"),
    ],
)
def test_rejects_mismatched_release_metadata(path: tuple[str, ...], value: object) -> None:
    payload = deepcopy(release_pr())
    target = payload
    for part in path[:-1]:
        target = target[part]  # type: ignore[assignment,index]
    target[path[-1]] = value  # type: ignore[index]

    with pytest.raises(release.AuthorizationError):
        authorize(payload)


def test_recovery_inputs_must_match_the_merged_pr() -> None:
    with pytest.raises(release.AuthorizationError, match="requested version"):
        authorize(requested_version="0.2.0")
    with pytest.raises(release.AuthorizationError, match="requested commit"):
        authorize(requested_commit="b" * 40)
    with pytest.raises(release.AuthorizationError, match="requested head"):
        authorize(requested_head="b" * 40)


def test_rejects_tree_parent_and_commit_identity_mismatches() -> None:
    with pytest.raises(release.AuthorizationError, match="merge tree"):
        authorize(merge=commit_payload("a" * 40, "f" * 40, ["b" * 40]))
    with pytest.raises(release.AuthorizationError, match="merge parent"):
        authorize(merge=commit_payload("a" * 40, "d" * 40, ["e" * 40]))
    with pytest.raises(release.AuthorizationError, match="head commit response"):
        authorize(head=commit_payload("f" * 40, "d" * 40, []))


@pytest.mark.parametrize("issues", [[], [71, 70], [70, 70], [70, "71"], [0, 71]])
def test_release_issue_set_is_tracked_unique_and_sorted(issues: list[object]) -> None:
    metadata = release_metadata()
    metadata["issues"] = issues

    with pytest.raises(release.AuthorizationError, match="issues"):
        authorize(metadata=metadata)


def test_release_metadata_must_come_from_one_exact_bounded_contents_response() -> None:
    contents = release_metadata_contents()
    contents["size"] = contents["size"] + 1
    with pytest.raises(release.AuthorizationError, match="size does not match"):
        release.authorize_release(
            release_pr(),
            "example/open-code-review-toolkit",
            commit_payload("c" * 40, "d" * 40, ["e" * 40]),
            commit_payload("a" * 40, "d" * 40, ["b" * 40]),
            check_runs(),
            ruleset(),
            contents,
        )

    contents = release_metadata_contents()
    content = contents["content"]
    contents["content"] = f"{content[:8]}\n{content[8:]}"
    release.authorize_release(
        release_pr(),
        "example/open-code-review-toolkit",
        commit_payload("c" * 40, "d" * 40, ["e" * 40]),
        commit_payload("a" * 40, "d" * 40, ["b" * 40]),
        check_runs(),
        ruleset(),
        contents,
    )

    contents = release_metadata_contents()
    contents["content"] = "not-base64"
    with pytest.raises(release.AuthorizationError, match="contents response is malformed"):
        release.authorize_release(
            release_pr(),
            "example/open-code-review-toolkit",
            commit_payload("c" * 40, "d" * 40, ["e" * 40]),
            commit_payload("a" * 40, "d" * 40, ["b" * 40]),
            check_runs(),
            ruleset(),
            contents,
        )


def test_required_checks_must_succeed_from_the_exact_ruleset_app() -> None:
    missing = check_runs()
    missing["check_runs"] = list(missing["check_runs"])[:1]
    missing["total_count"] = 1
    with pytest.raises(release.AuthorizationError, match="missing required checks"):
        authorize(checks=missing)

    failed = check_runs()
    failed["check_runs"][0]["conclusion"] = "failure"
    with pytest.raises(release.AuthorizationError, match="unsuccessful required check"):
        authorize(checks=failed)

    wrong_app = check_runs()
    wrong_app["check_runs"][0]["app"]["id"] = 999
    with pytest.raises(release.AuthorizationError, match="missing required checks"):
        authorize(checks=wrong_app)


def test_duplicate_or_incomplete_latest_check_response_fails_closed() -> None:
    checks = check_runs()
    checks["check_runs"].append(
        {
            "name": "quality",
            "conclusion": "success",
            "status": "completed",
            "head_sha": "c" * 40,
            "completed_at": "2026-08-10T10:02:00Z",
            "app": {"id": 15368},
        }
    )
    checks["total_count"] = 3
    with pytest.raises(release.AuthorizationError, match="duplicate required check"):
        authorize(checks=checks)

    checks = check_runs()
    checks["total_count"] = 101
    with pytest.raises(release.AuthorizationError, match="response is malformed"):
        authorize(checks=checks)


def test_required_check_and_ruleset_synchronization_are_exact() -> None:
    checks = check_runs()
    checks["check_runs"][0]["head_sha"] = "f" * 40
    with pytest.raises(release.AuthorizationError, match="not bound"):
        authorize(checks=checks)

    checks = check_runs()
    checks["check_runs"][0]["status"] = "in_progress"
    with pytest.raises(release.AuthorizationError, match="unsuccessful"):
        authorize(checks=checks)

    protection = ruleset()
    protection["rules"][0]["parameters"]["strict_required_status_checks_policy"] = False
    with pytest.raises(release.AuthorizationError, match="strict base"):
        authorize(protection=protection)


def test_release_workflow_classifies_ordinary_merges_before_authorization() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "name: classify-release-trigger" in workflow
    assert '[[ "${PR_HEAD_REF}" == release/v* ]]' in workflow
    assert "needs: classify" in workflow
    assert "needs.classify.outputs.release == 'true'" in workflow


def test_release_workflow_keeps_strict_release_authorization() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "python scripts/release_authorization.py" in workflow
    assert "github.event.pull_request.merge_commit_sha || inputs['merge-commit']" in workflow
    assert 'test "${RELEASE_BRANCH}" = "release/v${VERSION}"' in workflow
    assert "repos/${REPOSITORY}/rules/branches/main" in workflow
    assert "commits/${HEAD_SHA}/check-runs?filter=latest&per_page=100" in workflow
    assert "scripts/bounded_github_api.sh" in workflow
    assert "max_bytes=${5:-1048576}" in BOUNDED_API.read_text(encoding="utf-8")
    assert '--max-filesize "${max_bytes}"' in BOUNDED_API.read_text(encoding="utf-8")
    assert "application/octet-stream" in BOUNDED_API.read_text(encoding="utf-8")
    assert "--proto-redir '=https'" in BOUNDED_API.read_text(encoding="utf-8")
    assert "Reading them\n          # anonymously" in workflow
    assert "--head-commit-json" in workflow
    assert "--merge-commit-json" in workflow
    assert "--check-runs-json" in workflow
    assert "--ruleset-json" in workflow
    assert "contents/.release-metadata.json?ref=${MERGE_SHA}" in workflow
    assert "--release-metadata-contents-json /tmp/release-metadata-contents.json" in workflow
    assert "--requested-head" in workflow
    assert "Validate tracked release issues before publication" in workflow
    assert "--validate-issue-only" in workflow
    assert 'test "$(git rev-parse HEAD^{tree})" = "${EXPECTED_TREE}"' in workflow
    assert 'test "$(git rev-parse FETCH_HEAD^{tree})" = "${EXPECTED_TREE}"' in workflow
    assert "github.event.pull_request.merged == true" not in workflow
