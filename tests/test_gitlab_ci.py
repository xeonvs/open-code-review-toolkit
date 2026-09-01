"""Bounded GitLab acquisition for provider-neutral same-revision CI evidence."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from ocr_toolkit.context.ci_outcomes import CIOutcomeSnapshot
from ocr_toolkit.context.policy import parse_policy
from ocr_toolkit.providers import gitlab_ci
from ocr_toolkit.providers.gitlab import GitLabProviderError
from tests.test_context_policy import ci_policy_value, encoded_policy

HEAD = "a" * 40
NOW = 1_800_000_000
ENVIRONMENT = {
    "CI_API_V4_URL": "https://gitlab.example.invalid/api/v4",
    "CI_PROJECT_ID": "7",
    "CI_PIPELINE_ID": "10",
    "GITLAB_API_TOKEN": "not-a-real-token",
}


def _job(
    name: str,
    *,
    pipeline_id: int,
    status: str = "success",
    allow_failure: bool = False,
    finished_at: str = "2027-01-15T08:00:00Z",
    job_id: int | None = None,
) -> dict[str, object]:
    """Build one minimal GitLab-style job response."""

    return {
        "id": pipeline_id * 100 if job_id is None else job_id,
        "name": name,
        "status": status,
        "allow_failure": allow_failure,
        "finished_at": finished_at,
        "pipeline": {"id": pipeline_id, "sha": HEAD},
        "web_url": "https://gitlab.example.invalid/private/job",
        "runner": {"description": "private-runner"},
        "user": {"username": "private-user"},
    }


def _reader(
    pipelines: list[dict[str, object]], jobs: dict[int, list[dict[str, object]]]
) -> Callable[..., tuple[object, bool]]:
    """Return only controlled provider pages for a unit boundary test."""

    def read(url: str, _token: str, *, deadline: float) -> tuple[object, bool]:
        assert deadline > 0
        if "/jobs?" not in url:
            return pipelines, False
        pipeline_id = int(url.split("/pipelines/", 1)[1].split("/", 1)[0])
        return jobs[pipeline_id], False

    return read


def test_gitlab_ci_admits_only_exact_scoped_current_and_same_revision_outcomes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Normalize safe status/provenance while dropping raw provider identities."""

    pipelines = [{"id": 10, "sha": HEAD}, {"id": 11, "sha": HEAD}]
    jobs = {
        10: [_job("package", pipeline_id=10)],
        11: [_job("functional-tests", pipeline_id=11)],
    }
    monkeypatch.setattr(gitlab_ci, "_read_page", _reader(pipelines, jobs))
    policy = parse_policy(encoded_policy(ci_policy_value())).ci_outcomes
    assert policy is not None

    snapshot, _digest = gitlab_ci._raw_snapshot(
        ENVIRONMENT,
        project_id="7",
        source_sha=HEAD,
        policy=policy,
        now=NOW,
        deadline=NOW,
    )

    assert snapshot.state == "complete"
    assert [(record.check, record.origin, record.status) for record in snapshot.records] == [
        ("functional-tests", "same_revision_pipeline", "passed"),
        ("package", "current_pipeline", "passed"),
    ]
    assert all(isinstance(record.path_prefixes, tuple) for record in snapshot.records)
    assert all("private" not in record.digest for record in snapshot.records)


def test_gitlab_ci_rejects_wrong_revision_and_ambiguous_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fail closed for a provider SHA mismatch and repeated exact check identity."""

    policy = parse_policy(encoded_policy(ci_policy_value())).ci_outcomes
    assert policy is not None
    monkeypatch.setattr(
        gitlab_ci,
        "_read_page",
        _reader([{"id": 10, "sha": "b" * 40}], {10: []}),
    )
    with pytest.raises(GitLabProviderError, match="reviewed head"):
        gitlab_ci._raw_snapshot(
            ENVIRONMENT,
            project_id="7",
            source_sha=HEAD,
            policy=policy,
            now=NOW,
            deadline=NOW,
        )

    duplicate = _job("functional-tests", pipeline_id=10)
    monkeypatch.setattr(
        gitlab_ci,
        "_read_page",
        _reader([{"id": 10, "sha": HEAD}], {10: [duplicate, dict(duplicate)]}),
    )
    snapshot, _digest = gitlab_ci._raw_snapshot(
        ENVIRONMENT,
        project_id="7",
        source_sha=HEAD,
        policy=policy,
        now=NOW,
        deadline=NOW,
    )
    assert snapshot.state == "partial"
    assert all(record.check != "functional-tests" for record in snapshot.records)
    assert snapshot.invalid >= 1


def test_gitlab_ci_selects_newest_unambiguous_retry_and_ignores_unrequested_names(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Use the newest requested retry without letting unrelated names degrade evidence."""

    policy = parse_policy(encoded_policy(ci_policy_value())).ci_outcomes
    assert policy is not None
    jobs = {
        10: [
            _job("x" * 1024, pipeline_id=10),
            _job(
                "functional-tests",
                pipeline_id=10,
                status="failed",
                finished_at="2027-01-15T07:59:00Z",
                job_id=1001,
            ),
            _job("functional-tests", pipeline_id=10, job_id=1002),
            _job("package", pipeline_id=10),
        ]
    }
    monkeypatch.setattr(
        gitlab_ci,
        "_read_page",
        _reader([{"id": 10, "sha": HEAD}], jobs),
    )

    snapshot, _digest = gitlab_ci._raw_snapshot(
        ENVIRONMENT,
        project_id="7",
        source_sha=HEAD,
        policy=policy,
        now=NOW,
        deadline=NOW,
    )

    assert snapshot.state == "complete"
    assert {record.check: record.status for record in snapshot.records} == {
        "functional-tests": "passed",
        "package": "passed",
    }


def test_gitlab_ci_snapshot_digest_is_independent_of_provider_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Do not report mutation when GitLab reorders identical pipelines or jobs."""

    policy = parse_policy(encoded_policy(ci_policy_value())).ci_outcomes
    assert policy is not None
    pipelines = [{"id": 10, "sha": HEAD}, {"id": 11, "sha": HEAD}]
    jobs = {
        10: [_job("package", pipeline_id=10), _job("functional-tests", pipeline_id=10)],
        11: [
            _job(
                "functional-tests",
                pipeline_id=11,
                finished_at="2027-01-15T07:59:00Z",
            ),
            _job(
                "package",
                pipeline_id=11,
                finished_at="2027-01-15T07:59:00Z",
            ),
        ],
    }
    monkeypatch.setattr(gitlab_ci, "_read_page", _reader(pipelines, jobs))
    first, first_digest = gitlab_ci._raw_snapshot(
        ENVIRONMENT,
        project_id="7",
        source_sha=HEAD,
        policy=policy,
        now=NOW,
        deadline=NOW,
    )
    monkeypatch.setattr(
        gitlab_ci,
        "_read_page",
        _reader(
            list(reversed(pipelines)), {key: list(reversed(value)) for key, value in jobs.items()}
        ),
    )
    second, second_digest = gitlab_ci._raw_snapshot(
        ENVIRONMENT,
        project_id="7",
        source_sha=HEAD,
        policy=policy,
        now=NOW,
        deadline=NOW,
    )

    assert second == first
    assert second_digest == first_digest


def test_gitlab_ci_preserves_advisory_and_unknown_without_claiming_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep provider uncertainty closed and distinct from a required pass."""

    policy = parse_policy(encoded_policy(ci_policy_value())).ci_outcomes
    assert policy is not None
    jobs = {
        10: [
            _job("functional-tests", pipeline_id=10, status="new-provider-state"),
            _job("package", pipeline_id=10, allow_failure=True),
        ]
    }
    monkeypatch.setattr(
        gitlab_ci,
        "_read_page",
        _reader([{"id": 10, "sha": HEAD}], jobs),
    )
    snapshot, _digest = gitlab_ci._raw_snapshot(
        ENVIRONMENT,
        project_id="7",
        source_sha=HEAD,
        policy=policy,
        now=NOW,
        deadline=NOW,
    )
    records = {record.check: record for record in snapshot.records}
    assert records["functional-tests"].status == "unknown"
    assert records["package"].requirement == "advisory"


def test_gitlab_ci_marks_pagination_and_stale_results_partial(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Never present truncated discovery or an expired check as complete evidence."""

    policy = parse_policy(encoded_policy(ci_policy_value())).ci_outcomes
    assert policy is not None
    pipelines = [{"id": 10, "sha": HEAD}]
    jobs = {
        10: [
            _job("functional-tests", pipeline_id=10),
            _job("package", pipeline_id=10, finished_at="2026-01-01T00:00:00Z"),
        ]
    }

    def paginated_reader(url: str, _token: str, *, deadline: float) -> tuple[object, bool]:
        assert deadline > 0
        if "/jobs?" not in url:
            return pipelines, True
        return jobs[10], False

    monkeypatch.setattr(gitlab_ci, "_read_page", paginated_reader)
    snapshot, _digest = gitlab_ci._raw_snapshot(
        ENVIRONMENT,
        project_id="7",
        source_sha=HEAD,
        policy=policy,
        now=NOW,
        deadline=NOW,
    )

    assert snapshot.state == "partial"
    assert [record.check for record in snapshot.records] == ["functional-tests"]
    assert snapshot.omitted == 1
    assert snapshot.invalid == 1


def test_gitlab_ci_twice_read_mutation_returns_no_records(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Discard the complete candidate when the bounded provider snapshot changes."""

    policy = parse_policy(encoded_policy(ci_policy_value())).ci_outcomes
    assert policy is not None
    snapshots = iter(
        (
            (CIOutcomeSnapshot("complete", (), 0, 0), "a" * 64),
            (CIOutcomeSnapshot("complete", (), 0, 0), "b" * 64),
        )
    )
    monkeypatch.setattr(gitlab_ci, "_raw_snapshot", lambda *_args, **_kwargs: next(snapshots))

    result = gitlab_ci.acquire_gitlab_ci_outcomes(
        ENVIRONMENT,
        project_id="7",
        source_sha=HEAD,
        policy=policy,
        now=NOW,
    )

    assert result == CIOutcomeSnapshot(state="mutated", records=(), omitted=0, invalid=1)
