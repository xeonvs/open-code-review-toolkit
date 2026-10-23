"""Production Git ancestry and authenticated-snapshot freshness regressions."""

from __future__ import annotations

import os
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from ocr_toolkit.posting import freshness
from ocr_toolkit.providers.gitlab import (
    GitLabMergeRequestLifecycle,
    GitLabMergeRequestStale,
    GitLabMergeRequestTerminal,
    GitLabProviderError,
    GitLabReviewSnapshot,
)
from ocr_toolkit.review_receipt import ReceiptReviewIdentity


def _git(root: Path, *args: str) -> str:
    """Run one synthetic Git operation with signing and inherited overrides disabled."""

    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    environment.update(
        {
            "GIT_AUTHOR_NAME": "Freshness Test",
            "GIT_AUTHOR_EMAIL": "author@example.invalid",
            "GIT_COMMITTER_NAME": "Freshness Test",
            "GIT_COMMITTER_EMAIL": "committer@example.invalid",
        }
    )
    completed = subprocess.run(
        ["git", "-C", str(root), "-c", "commit.gpgsign=false", *args],
        capture_output=True,
        check=True,
        env=environment,
        text=True,
        timeout=15,
    )
    return completed.stdout.strip()


def _commit(root: Path, name: str) -> str:
    """Create one distinct immutable commit on the active synthetic branch."""

    (root / "content.txt").write_text(name, encoding="utf-8")
    _git(root, "add", "content.txt")
    _git(root, "commit", "-qm", name)
    return _git(root, "rev-parse", "HEAD")


def _review_graph(tmp_path: Path) -> tuple[Path, GitLabReviewSnapshot, str, str]:
    """Create separate MR target, source, and protected policy histories."""

    root = tmp_path / "repository"
    root.mkdir()
    _git(root, "init", "-q")
    base = _commit(root, "base")
    _git(root, "switch", "-qc", "topic", base)
    target = _commit(root, "target")
    _git(root, "switch", "-qc", "main", base)
    policy = _commit(root, "policy")
    advanced_policy = _commit(root, "advanced policy")
    _git(root, "switch", "-qc", "rewrite", base)
    rewrite = _commit(root, "independent policy")
    _git(root, "switch", "-qc", "source", base)
    source = _commit(root, "source")
    snapshot = GitLabReviewSnapshot(
        project_id="7",
        merge_request_iid="9",
        source_sha=source,
        target_branch="topic",
        target_sha=target,
        target_protection="unprotected",
        policy_branch="main",
        policy_sha=policy,
        policy_protection="protected",
        protection_mode="auto",
        diff_base_sha=base,
        diff_start_sha=target,
        diff_head_sha=source,
        diff_version_id=12,
        author_id=42,
        context=None,
    )
    assert snapshot.diff_base_sha != snapshot.target_sha
    return root, snapshot, advanced_policy, rewrite


def _receipt(snapshot: GitLabReviewSnapshot) -> ReceiptReviewIdentity:
    """Construct the validated v11 shape consumed by publication."""

    return ReceiptReviewIdentity(
        source_sha=snapshot.source_sha,
        target_sha=snapshot.target_sha,
        target_protection=snapshot.target_protection,
        mr_author_id=snapshot.author_id,
        schema_version=11,
        policy_sha=snapshot.policy_sha,
        project_id=snapshot.project_id,
        merge_request_iid=snapshot.merge_request_iid,
        diff_base_sha=snapshot.diff_base_sha,
        diff_start_sha=snapshot.diff_start_sha,
        diff_head_sha=snapshot.diff_head_sha,
        diff_version_id=snapshot.diff_version_id,
        target_branch=snapshot.target_branch,
        policy_project_id=snapshot.project_id,
        policy_branch=snapshot.policy_branch,
        policy_protection=snapshot.policy_protection,
        protection_mode=snapshot.protection_mode,
        ci_job_id="11",
    )


def _environment(snapshot: GitLabReviewSnapshot) -> dict[str, str]:
    """Represent the detached MR job whose result is being published."""

    return {
        "CI_PROJECT_ID": "7",
        "CI_MERGE_REQUEST_IID": "9",
        "CI_MERGE_REQUEST_EVENT_TYPE": "detached",
        "CI_COMMIT_SHA": snapshot.source_sha,
        "CI_MERGE_REQUEST_DIFF_BASE_SHA": snapshot.diff_base_sha,
        "CI_JOB_ID": "11",
    }


def _live_snapshot(monkeypatch: pytest.MonkeyPatch, snapshot: GitLabReviewSnapshot) -> None:
    """Replace the external GitLab adapter while retaining real local Git reads."""

    def acquire(
        environment: dict[str, str], *, expected_head: str, include_metadata: bool
    ) -> GitLabReviewSnapshot:
        assert environment["CI_PROJECT_ID"] == "7"
        assert environment["CI_MERGE_REQUEST_IID"] == "9"
        assert environment["CI_MERGE_REQUEST_EVENT_TYPE"] == "detached"
        assert expected_head == snapshot.source_sha
        assert include_metadata is False
        return snapshot

    monkeypatch.setattr(freshness, "acquire_review_snapshot", acquire)


def test_unchanged_review_accepts_diff_base_distinct_from_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The current MR diff base B is independent of the target tip T."""

    root, snapshot, _advanced, _rewrite = _review_graph(tmp_path)
    identity = _receipt(snapshot)
    _live_snapshot(monkeypatch, snapshot)

    result = freshness.validate_review_freshness(_environment(snapshot), identity, root)

    assert result == freshness.ReviewFreshnessResult(snapshot.policy_sha, False)
    assert identity.policy_sha == snapshot.policy_sha


@pytest.mark.parametrize("review_job,current_job", (("12", "11"), ("11", "12"), ("11", "")))
def test_other_job_handoff_is_rejected_before_provider_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    review_job: str,
    current_job: str,
) -> None:
    """A later review of the same B/H/T/P cannot become this job's result."""

    root, snapshot, _advanced, _rewrite = _review_graph(tmp_path)
    environment = _environment(snapshot)
    if current_job:
        environment["CI_JOB_ID"] = current_job
    else:
        del environment["CI_JOB_ID"]
    identity = replace(_receipt(snapshot), ci_job_id=review_job)
    monkeypatch.setattr(
        freshness,
        "acquire_review_snapshot",
        lambda *_args, **_kwargs: pytest.fail("provider contacted for another job's result"),
    )

    with pytest.raises(freshness.ReviewFreshnessStale) as caught:
        freshness.validate_review_freshness(environment, identity, root)

    assert caught.value.reason == "invocation_changed"


def test_policy_only_fast_forward_preserves_reviewed_policy_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Accept same protected authority after real ancestry proof without moving P."""

    root, snapshot, advanced, _rewrite = _review_graph(tmp_path)
    identity = _receipt(snapshot)
    _live_snapshot(monkeypatch, replace(snapshot, policy_sha=advanced))

    result = freshness.validate_review_freshness(_environment(snapshot), identity, root)

    assert result == freshness.ReviewFreshnessResult(advanced, True)
    assert identity.policy_sha == snapshot.policy_sha


def test_policy_rewrite_is_stale(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Reject a same-named protected branch whose new tip is not descended from P."""

    root, snapshot, _advanced, rewrite = _review_graph(tmp_path)
    _live_snapshot(monkeypatch, replace(snapshot, policy_sha=rewrite))

    with pytest.raises(freshness.ReviewFreshnessStale) as caught:
        freshness.validate_review_freshness(_environment(snapshot), _receipt(snapshot), root)

    assert caught.value.reason == "policy_rewritten"


@pytest.mark.parametrize(
    ("changed", "reason"),
    [
        ({"project_id": "8"}, "invocation_changed"),
        ({"merge_request_iid": "10"}, "invocation_changed"),
        ({"author_id": 43}, "invocation_changed"),
        ({"diff_base_sha": "a" * 40}, "diff_changed"),
        ({"diff_version_id": 13}, "diff_changed"),
        ({"target_sha": "a" * 40}, "target_changed"),
        ({"target_branch": "other"}, "target_changed"),
        ({"target_protection": "protected"}, "target_changed"),
        ({"policy_branch": "other"}, "authority_changed"),
        ({"policy_protection": "unprotected"}, "authority_changed"),
        ({"protection_mode": "required"}, "authority_changed"),
    ],
)
def test_live_code_and_authority_drift_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    changed: dict[str, object],
    reason: str,
) -> None:
    """Revalidation catches target, default/protection, and diff movement."""

    root, snapshot, _advanced, _rewrite = _review_graph(tmp_path)
    _live_snapshot(monkeypatch, replace(snapshot, **changed))

    with pytest.raises(freshness.ReviewFreshnessStale) as caught:
        freshness.validate_review_freshness(_environment(snapshot), _receipt(snapshot), root)

    assert caught.value.reason == reason


def test_contradictory_live_source_and_protected_policy_movement_are_stale(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reject defensive branches if a forged adapter bypasses provider invariants."""

    root, snapshot, advanced, _rewrite = _review_graph(tmp_path)
    monkeypatch.setattr(
        freshness,
        "acquire_review_snapshot",
        lambda *_args, **_kwargs: replace(snapshot, source_sha="a" * 40),
    )
    with pytest.raises(freshness.ReviewFreshnessStale) as changed_source:
        freshness.validate_review_freshness(_environment(snapshot), _receipt(snapshot), root)
    assert changed_source.value.reason == "source_changed"

    protected = replace(
        snapshot,
        target_protection="protected",
        policy_branch=snapshot.target_branch,
        policy_sha=snapshot.target_sha,
    )
    _live_snapshot(monkeypatch, replace(protected, policy_sha=advanced))
    with pytest.raises(freshness.ReviewFreshnessStale) as moved_authority:
        freshness.validate_review_freshness(_environment(protected), _receipt(protected), root)
    assert moved_authority.value.reason == "authority_changed"


def test_legacy_receipt_and_wrong_invocation_do_not_query_provider(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Avoid guessing historical authority and querying another MR from CI."""

    root, snapshot, _advanced, _rewrite = _review_graph(tmp_path)

    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("provider must not be called")

    monkeypatch.setattr(freshness, "acquire_review_snapshot", forbidden)
    with pytest.raises(freshness.ReviewFreshnessUnavailable) as legacy:
        freshness.validate_review_freshness(
            _environment(snapshot), replace(_receipt(snapshot), schema_version=10), root
        )
    assert legacy.value.reason == "receipt_unavailable"

    with pytest.raises(freshness.ReviewFreshnessStale) as wrong_invocation:
        freshness.validate_review_freshness(
            {**_environment(snapshot), "CI_MERGE_REQUEST_IID": "10"},
            _receipt(snapshot),
            root,
        )
    assert wrong_invocation.value.reason == "invocation_changed"


@pytest.mark.parametrize(
    "environment_change",
    [
        {"CI_MERGE_REQUEST_EVENT_TYPE": "merged_result"},
        {"CI_MERGE_REQUEST_EVENT_TYPE": "merge_train"},
        {"CI_MERGE_REQUEST_EVENT_TYPE": ""},
        {"CI_COMMIT_SHA": "a" * 40},
        {"CI_MERGE_REQUEST_SOURCE_BRANCH_SHA": "a" * 40},
    ],
)
def test_synthetic_or_changed_ci_source_stops_before_provider(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    environment_change: dict[str, str],
) -> None:
    """A valid receipt cannot be replayed from another GitLab pipeline form."""

    root, snapshot, _advanced, _rewrite = _review_graph(tmp_path)

    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("provider must not be called")

    monkeypatch.setattr(freshness, "acquire_review_snapshot", forbidden)
    with pytest.raises(freshness.ReviewFreshnessStale) as caught:
        freshness.validate_review_freshness(
            {**_environment(snapshot), **environment_change}, _receipt(snapshot), root
        )
    assert caught.value.reason == "invocation_changed"


def test_present_ci_diff_base_must_match_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Treat a changed CI merge base as stale without making a provider request."""

    root, snapshot, _advanced, _rewrite = _review_graph(tmp_path)

    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("provider must not be called")

    monkeypatch.setattr(freshness, "acquire_review_snapshot", forbidden)
    with pytest.raises(freshness.ReviewFreshnessStale) as caught:
        freshness.validate_review_freshness(
            {**_environment(snapshot), "CI_MERGE_REQUEST_DIFF_BASE_SHA": "a" * 40},
            _receipt(snapshot),
            root,
        )
    assert caught.value.reason == "diff_changed"


def test_absent_optional_ci_diff_base_uses_authenticated_diff(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Keep authenticated current MR diff validation when CI omits this hint."""

    root, snapshot, _advanced, _rewrite = _review_graph(tmp_path)
    _live_snapshot(monkeypatch, snapshot)
    environment = _environment(snapshot)
    environment.pop("CI_MERGE_REQUEST_DIFF_BASE_SHA")

    result = freshness.validate_review_freshness(environment, _receipt(snapshot), root)

    assert result.policy_advanced is False


def test_provider_stale_unavailable_and_terminal_are_distinct(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Leave terminal routing intact and expose safe stale/unavailable reasons."""

    root, snapshot, _advanced, _rewrite = _review_graph(tmp_path)
    terminal = GitLabMergeRequestTerminal(
        GitLabMergeRequestLifecycle("7", "9", snapshot.source_sha, "merged")
    )
    for error, expected in (
        (GitLabMergeRequestStale("7", "9"), "source_changed"),
        (GitLabProviderError("remote request failed"), "provider_unavailable"),
    ):
        monkeypatch.setattr(
            freshness,
            "acquire_review_snapshot",
            lambda *_args, error=error, **_kwargs: (_ for _ in ()).throw(error),
        )
        with pytest.raises(freshness.ReviewFreshnessError) as caught:
            freshness.validate_review_freshness(_environment(snapshot), _receipt(snapshot), root)
        assert caught.value.reason == expected

    monkeypatch.setattr(
        freshness,
        "acquire_review_snapshot",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(terminal),
    )
    with pytest.raises(GitLabMergeRequestTerminal) as caught_terminal:
        freshness.validate_review_freshness(_environment(snapshot), _receipt(snapshot), root)
    assert caught_terminal.value is terminal


def test_unavailable_git_graph_is_not_accepted_as_fast_forward(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A policy advance needs local proof even when the live branch is protected."""

    root, snapshot, _advanced, _rewrite = _review_graph(tmp_path)
    _live_snapshot(monkeypatch, replace(snapshot, policy_sha="f" * 40))

    with pytest.raises(freshness.ReviewFreshnessUnavailable) as caught:
        freshness.validate_review_freshness(_environment(snapshot), _receipt(snapshot), root)

    assert caught.value.reason == "ancestry_unavailable"
