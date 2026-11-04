"""Cli boundary failures preserve bounded delivery and prior reviewer state."""

import pytest

from ocr_toolkit.posting import gitlab
from tests.support import gitlab_config


@pytest.mark.parametrize("phase", ["initial", "readback"])
def test_terminal_advisory_provider_failure_cannot_report_a_success(monkeypatch, phase):
    from ocr_toolkit.posting import workflow
    from ocr_toolkit.providers.gitlab import GitLabProviderError
    from tests.test_terminal_merge_request import terminal_status

    def fail(*args):
        raise GitLabProviderError("unavailable")

    monkeypatch.setattr(workflow, "current_merge_request_lifecycle", fail)
    monkeypatch.setattr(
        gitlab,
        "post_note",
        lambda *args, **kwargs: pytest.fail("unconfirmed lifecycle reached write"),
    )
    if phase == "initial":
        assert workflow.post_pre_execution_status(gitlab_config(), terminal_status()) == 1
    else:
        assert workflow.terminal_status_exit(gitlab_config(), "a" * 40, posting_succeeded=True) == 1


@pytest.mark.parametrize(
    "strict,state,succeeded,expected",
    [
        (False, "opened", True, 1),
        (True, "closed", True, 1),
        (True, "merged", False, 1),
        (False, "merged", False, 0),
    ],
)
def test_terminal_advisory_respects_reopen_and_strict_delivery_constraints(
    monkeypatch, strict, state, succeeded, expected
):
    from ocr_toolkit.posting import workflow
    from ocr_toolkit.providers.gitlab import GitLabMergeRequestLifecycle

    monkeypatch.setattr(workflow, "strict_posting", lambda: strict)
    monkeypatch.setattr(
        workflow,
        "current_merge_request_lifecycle",
        lambda *args: GitLabMergeRequestLifecycle("1", "2", "a" * 40, state),
    )
    assert (
        workflow.terminal_status_exit(gitlab_config(), "a" * 40, posting_succeeded=succeeded)
        == expected
    )


@pytest.mark.parametrize("previous", [None, [17, 18]])
def test_uncertain_terminal_note_snapshot_does_not_authorize_an_upsert(monkeypatch, previous):
    from ocr_toolkit.posting import workflow
    from ocr_toolkit.providers.gitlab import GitLabMergeRequestLifecycle
    from tests.test_terminal_merge_request import terminal_status

    monkeypatch.setattr(
        workflow,
        "current_merge_request_lifecycle",
        lambda *args: GitLabMergeRequestLifecycle("1", "2", "a" * 40, "merged"),
    )
    monkeypatch.setattr(workflow, "collect_terminal_status_note_ids", lambda *args: previous)
    monkeypatch.setattr(workflow, "strict_posting", lambda: True)
    monkeypatch.setattr(
        gitlab,
        "post_note",
        lambda *args, **kwargs: pytest.fail("ambiguous snapshot reached create"),
    )
    monkeypatch.setattr(
        workflow,
        "update_plain_note",
        lambda *args, **kwargs: pytest.fail("ambiguous snapshot reached update"),
    )
    assert workflow.post_pre_execution_status(gitlab_config(), terminal_status()) == 1


@pytest.mark.parametrize(
    "case", ["missing", "array", "scalar", "malformed", "duplicate", "oversize"]
)
def test_cli_hostile_or_missing_result_is_job_only_and_never_reaches_delivery(
    tmp_path, monkeypatch, case
):
    from ocr_toolkit import ocr_result
    from ocr_toolkit.posting import workflow

    result = tmp_path / "result.json"
    stderr = tmp_path / "stderr.log"
    stderr.write_text("private process diagnostics")
    values = {
        "array": "[]",
        "scalar": "7",
        "malformed": "{broken",
        "duplicate": '{"comments":[],"comments":[]}',
        "oversize": '{"comments":[],"padding":"' + ("x" * 100) + '"}',
    }
    if case != "missing":
        result.write_text(values[case])
        result.chmod(0o600)
    if case == "oversize":
        monkeypatch.setattr(ocr_result, "max_result_bytes", lambda: 16)
    monkeypatch.setattr(workflow, "ocr_exit_code", lambda: 0)
    monkeypatch.setattr(workflow, "load_gitlab_config", gitlab_config)
    monkeypatch.setattr(
        workflow, "post_results", lambda *args: pytest.fail("unadmitted artifact reached delivery")
    )
    monkeypatch.setattr(
        gitlab,
        "api_request",
        lambda *args, **kwargs: pytest.fail("job-only failure reached provider"),
    )
    monkeypatch.setenv("OCR_REVIEW_DIAGRAM_MODE", "off")
    for key in (
        "CI_COMMIT_SHA",
        "CI_MERGE_REQUEST_SOURCE_BRANCH_SHA",
        "CI_MERGE_REQUEST_DIFF_BASE_SHA",
    ):
        monkeypatch.delenv(key, raising=False)
    assert workflow.main([str(result), str(stderr)]) == 1


@pytest.mark.parametrize("case", ["mode", "config", "actor"])
def test_cli_rejects_missing_delivery_authority_before_artifact_acquisition(monkeypatch, case):
    from dataclasses import replace

    from ocr_toolkit.posting import workflow

    monkeypatch.setattr(workflow, "ocr_exit_code", lambda: 0)
    monkeypatch.setenv("OCR_REVIEW_DIAGRAM_MODE", "invalid" if case == "mode" else "off")
    monkeypatch.setattr(
        workflow,
        "load_gitlab_config",
        lambda: (
            None
            if case == "config"
            else replace(gitlab_config(), current_user_id=None)
            if case == "actor"
            else gitlab_config()
        ),
    )
    monkeypatch.setattr(
        workflow,
        "load_ocr_result",
        lambda *args: pytest.fail("invalid delivery authority reached artifact read"),
    )
    assert workflow.main([]) == 1


def test_verified_terminal_status_identity_cannot_be_rebound_to_another_target(monkeypatch):
    from dataclasses import replace

    from ocr_toolkit.posting import workflow
    from tests.test_terminal_merge_request import terminal_status

    monkeypatch.setattr(
        workflow,
        "current_merge_request_lifecycle",
        lambda *args: pytest.fail("foreign identity reached lookup"),
    )
    assert (
        workflow.post_terminal_merge_request_status(
            gitlab_config(), replace(terminal_status(), project_id="other")
        )
        == 1
    )
