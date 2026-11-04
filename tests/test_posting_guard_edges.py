"""Malformed provider snapshots gate approval and preserve-review decisions."""

from copy import deepcopy

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ocr_toolkit.posting import gitlab
from ocr_toolkit.posting.approval import ApprovalEligibility, ApprovalResult, ApprovalStatus
from tests.fuzz.strategies import json_values
from tests.support import gitlab_config
from tests.test_posting_approval import execute_current_approval

SHA = "a" * 40
ELIGIBLE = ApprovalEligibility(True, ApprovalResult(ApprovalStatus.SKIPPED, "not yet attempted"))


def provider_snapshots():
    return {
        "mr": {
            "sha": SHA,
            "state": "opened",
            "author": {"id": 41},
            "detailed_merge_status": "mergeable",
        },
        "versions": [{"id": 1, "head_commit_sha": SHA, "patch_id_sha": "b" * 40}],
        "approvals": {"approved_by": []},
    }


def install_provider(monkeypatch, snapshots):
    writes = []

    def request(config, endpoint, **kwargs):
        assert kwargs.get("method") == "GET"
        return deepcopy(snapshots["mr" if endpoint == "" else "approvals"])

    monkeypatch.setattr(gitlab, "api_request", request)
    monkeypatch.setattr(
        gitlab, "api_get_paginated", lambda *args, **kwargs: deepcopy(snapshots["versions"])
    )

    def approve(config, sha):
        writes.append(sha)
        return gitlab.GitLabWriteResult("posted")

    monkeypatch.setattr(gitlab, "approve_merge_request", approve)
    return writes


@pytest.mark.parametrize(
    "section,key,value",
    [
        ("mr", None, None),
        ("mr", "sha", []),
        ("mr", "author", []),
        ("mr", "author", {"id": True}),
        ("mr", "author", {"id": 0}),
        ("mr", "detailed_merge_status", None),
        ("mr", "detailed_merge_status", []),
        ("versions", None, []),
        ("versions", None, [None]),
        ("versions", None, [provider_snapshots()["versions"][0] | {"id": True}]),
        ("versions", None, [provider_snapshots()["versions"][0] | {"id": -1}]),
        ("approvals", None, []),
        ("approvals", None, {"approved_by": False}),
        ("approvals", None, {"approved_by": [None]}),
        ("approvals", None, {"approved_by": [{"user": []}]}),
        ("approvals", None, {"approved_by": [{"user": {"id": True}}]}),
        ("approvals", None, {"approved_by": [{"user": {"id": -1}}]}),
    ],
)
def test_malformed_provider_state_preserves_previous_review_without_write(
    monkeypatch, section, key, value
):
    snapshots = provider_snapshots()
    if key is None:
        snapshots[section] = value
    else:
        snapshots[section][key] = value
    writes = install_provider(monkeypatch, snapshots)
    result = execute_current_approval(
        gitlab_config(), ELIGIBLE, SHA, 41, attempts=1, interval_seconds=0
    )
    assert result.result.status != ApprovalStatus.APPROVED
    assert result.preserve_previous_review and writes == []


@given(
    st.one_of(
        st.none(),
        st.booleans(),
        st.integers(),
        st.text(max_size=40),
        st.lists(json_values(), max_size=4),
    )
)
def test_nonobject_approval_json_cannot_reach_a_write(value):
    # Own the temporary monkeypatch per generated example: no shared mutation or
    # a fake provider parser stands in for the production approval adapter.
    with pytest.MonkeyPatch.context() as patch:
        snapshots = provider_snapshots()
        snapshots["approvals"] = value
        writes = install_provider(patch, snapshots)
        result = execute_current_approval(
            gitlab_config(), ELIGIBLE, SHA, 41, attempts=1, interval_seconds=0
        )
        assert result.result.status == ApprovalStatus.FAILED
        assert result.preserve_previous_review and writes == []


@pytest.mark.parametrize("readback_author", [7, 42])
def test_post_write_author_change_is_not_reported_as_success_or_retried(
    monkeypatch, readback_author
):
    snapshots = provider_snapshots()
    writes = install_provider(monkeypatch, snapshots)

    def approve(config, sha):
        writes.append(sha)
        snapshots["mr"]["author"]["id"] = readback_author
        snapshots["approvals"] = {"approved_by": [{"user": {"id": 7}}]}
        return gitlab.GitLabWriteResult("posted")

    monkeypatch.setattr(gitlab, "approve_merge_request", approve)
    result = execute_current_approval(
        gitlab_config(), ELIGIBLE, SHA, 41, attempts=1, interval_seconds=0
    )
    assert result.result.status == ApprovalStatus.FAILED
    assert writes == [SHA]
