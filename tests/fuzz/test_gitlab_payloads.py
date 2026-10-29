"""Hostile GitLab identity and display fields remain separate bounded projections."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ocr_toolkit.context.ci_outcomes import prepare_ci_outcome_records
from ocr_toolkit.context.policy import parse_policy
from ocr_toolkit.evidence.review_context import (
    normalize_merge_request_context,
    validate_merge_request_context,
)
from ocr_toolkit.providers import gitlab_ci
from ocr_toolkit.providers.gitlab import GitLabProviderError, parse_merge_request_lifecycle
from ocr_toolkit.providers.gitlab_identity import GitLabIdentityError, parse_current_user_identity
from tests.fuzz.strategies import json_values
from tests.test_context_policy import ci_policy_value, encoded_policy
from tests.test_gitlab_ci import ENVIRONMENT, NOW, _job, _reader

HEAD = "a" * 40
LIFECYCLE = {
    "iid": 2,
    "target_project_id": 1,
    "source_project_id": 1,
    "sha": HEAD,
    "state": "opened",
}


@given(st.sampled_from(tuple(LIFECYCLE)), json_values())
def test_lifecycle_field_mutations_cannot_change_requested_identity(field, value) -> None:
    document = {**LIFECYCLE, field: value}
    try:
        admitted = parse_merge_request_lifecycle(
            document, expected_project_id="1", expected_merge_request_iid="2", expected_head=HEAD
        )
    except GitLabProviderError:
        return
    assert (admitted.project_id, admitted.merge_request_iid, admitted.source_sha) == (
        "1",
        "2",
        HEAD,
    )
    assert admitted.state in ("opened", "merged", "closed")


@given(st.sampled_from(("id", "username")), json_values())
def test_authenticated_user_projection_has_no_incidental_type_errors(field, value) -> None:
    try:
        admitted = parse_current_user_identity({"id": 7, "username": "synthetic_bot", field: value})
    except GitLabIdentityError:
        return
    assert type(admitted.user_id) is int and admitted.user_id > 0
    assert isinstance(admitted.username, str)


@given(json_values(), json_values(), json_values(), json_values())
def test_display_metadata_cannot_fabricate_or_change_review_identity(
    title, description, labels, source_branch
) -> None:
    context = normalize_merge_request_context(
        provider="gitlab",
        project_id="1",
        merge_request_iid="2",
        source_sha=HEAD,
        title=title,
        description=description,
        labels=labels,
        source_branch=source_branch,
    )
    projected = context.evidence_value()
    validate_merge_request_context(projected)
    assert (
        context.source_sha == HEAD
        and context.project_id == "1"
        and context.merge_request_iid == "2"
    )


@given(
    st.sampled_from(("id", "name", "status", "allow_failure", "finished_at", "pipeline")),
    json_values(),
    st.booleans(),
)
def test_ci_provider_mutations_remain_bounded_and_project_without_raw_forge_metadata(
    field, value, reverse
):
    policy = parse_policy(encoded_policy(ci_policy_value())).ci_outcomes
    assert policy is not None
    jobs = [_job("functional-tests", pipeline_id=10), _job("package", pipeline_id=10)]
    jobs[0][field] = value
    if reverse:
        jobs.reverse()
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(gitlab_ci, "_read_page", _reader([{"id": 10, "sha": HEAD}], {10: jobs}))
        try:
            snapshot, digest = gitlab_ci._raw_snapshot(
                ENVIRONMENT, project_id="7", source_sha=HEAD, policy=policy, now=NOW, deadline=NOW
            )
        except GitLabProviderError:
            return
    assert len(digest) == 64 and snapshot.state in ("complete", "partial")
    assert len(snapshot.records) <= len(policy.checks)
    pending = prepare_ci_outcome_records(snapshot, policy=policy, now=NOW)
    assert len(pending) <= len(snapshot.records)
    assert all(record.descriptor == "ci_outcome" for record in pending)
    assert all("web_url" not in record.projections["model"] for record in pending)
