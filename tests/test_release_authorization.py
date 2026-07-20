"""Tests for stable release pull-request authorization."""

from __future__ import annotations

import importlib.util
from copy import deepcopy
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts" / "release_authorization.py"


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("release_authorization_script", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


release = load_script()


def release_pr() -> dict[str, object]:
    return {
        "number": 5,
        "merged": True,
        "merged_at": "2026-07-20T10:00:00Z",
        "merge_commit_sha": "a" * 40,
        "title": "Release v0.1.0",
        "base": {"ref": "main"},
        "head": {
            "ref": "release/v0.1.0",
            "repo": {"full_name": "example/open-code-review-toolkit"},
        },
    }


def test_authorizes_exact_same_repository_release_merge() -> None:
    outputs = release.authorize_release(
        release_pr(),
        "example/open-code-review-toolkit",
        requested_version="0.1.0",
        requested_commit="a" * 40,
    )

    assert outputs == {
        "approved": "true",
        "branch": "release/v0.1.0",
        "commit": "a" * 40,
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
        release.authorize_release(payload, "example/open-code-review-toolkit")


def test_recovery_inputs_must_match_the_merged_pr() -> None:
    with pytest.raises(release.AuthorizationError, match="requested version"):
        release.authorize_release(
            release_pr(), "example/open-code-review-toolkit", requested_version="0.2.0"
        )
    with pytest.raises(release.AuthorizationError, match="requested commit"):
        release.authorize_release(
            release_pr(), "example/open-code-review-toolkit", requested_commit="b" * 40
        )
