"""Hostile persisted v7 budget facts and frozen historical status separation."""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from ocr_toolkit.pre_execution import (
    EVIDENCE_BUDGET_EXCEEDED,
    EVIDENCE_BUDGET_STATUS_SCHEMA,
    GITLINK_STATUS_SCHEMA,
    STATUS_SCHEMA,
    PreExecutionStatusError,
    pre_execution_review_identity,
    read_pre_execution_status,
    write_pre_execution_status,
)
from tests.test_evidence_repository import git
from tests.test_pre_execution_status import BASE, SOURCE, private_directory, review_identity, status


def budget_status():
    """Build one valid closed hard-budget status for hostile-readback tests."""
    return replace(
        status(),
        schema_version=EVIDENCE_BUDGET_STATUS_SCHEMA,
        reason=EVIDENCE_BUDGET_EXCEEDED,
        actual=513,
        limit=512,
        unit="records",
    )


@pytest.mark.parametrize(
    "unit,actual,limit",
    [("records", 100001, 100000), ("bytes", 20000001, 20000000), ("entries", 20001, 20000)],
)
def test_private_v7_roundtrip_and_existing_review_identity(
    tmp_path: Path, unit, actual, limit
) -> None:
    """Round-trip v7 diagnostics without changing the embedded immutable review identity."""
    value = replace(budget_status(), unit=unit, actual=actual, limit=limit)
    path = private_directory(tmp_path) / "status.json"
    write_pre_execution_status(path, value)
    assert (
        read_pre_execution_status(path, expected_diff_base_sha=BASE, expected_source_sha=SOURCE)
        == value
    )
    assert path.stat().st_mode & 0o777 == 0o600
    assert "repository_coverage" not in json.loads(path.read_text())
    assert pre_execution_review_identity(value).schema_version == 11


@pytest.mark.parametrize(
    "field,value",
    [
        ("actual", True),
        ("actual", "513"),
        ("actual", 512),
        ("actual", 100000001),
        ("limit", True),
        ("limit", 0),
        ("limit", 100001),
        ("unit", "paths"),
        ("unit", []),
        ("unit", None),
        ("stage", "ocr_preview"),
        ("reason", "arbitrary private cause"),
        ("model_execution", "started"),
        ("diagnostic_count", 1),
        ("provider", "gitlab"),
        ("project_id", "1"),
        ("change_id", "2"),
        ("terminal_state", "opened"),
        ("repository_coverage", {}),
        ("review", None),
        ("policy_sha", "d" * 40),
        ("schema_version", STATUS_SCHEMA),
        ("schema_version", GITLINK_STATUS_SCHEMA),
    ],
)
def test_hostile_v7_cannot_gain_valid_status_or_downgrade(tmp_path: Path, field, value) -> None:
    """Reject hostile budget fields and unsupported schema reinterpretation."""
    path = private_directory(tmp_path) / "status.json"
    write_pre_execution_status(path, budget_status())
    payload = json.loads(path.read_text())
    payload[field] = value
    path.write_text(json.dumps(payload))
    with pytest.raises(PreExecutionStatusError):
        read_pre_execution_status(path, expected_diff_base_sha=BASE, expected_source_sha=SOURCE)


def test_v7_stale_source_never_passes_hostile_readback(tmp_path: Path) -> None:
    """Keep a budget status bound to the expected immutable source identity."""
    path = private_directory(tmp_path) / "status.json"
    write_pre_execution_status(path, budget_status())
    with pytest.raises(PreExecutionStatusError, match="identity does not match"):
        read_pre_execution_status(path, expected_diff_base_sha=BASE, expected_source_sha="d" * 40)


def test_v7_limits_cannot_exceed_their_resource_ceiling(tmp_path: Path) -> None:
    """Reject diagnostic claims exceeding the actual resource ceiling."""
    value = replace(budget_status(), actual=200001, limit=200000)
    with pytest.raises(PreExecutionStatusError, match="evidence budget"):
        write_pre_execution_status(private_directory(tmp_path) / "status.json", value)


@pytest.mark.parametrize("local", [False, True])
def test_cli_real_git_budget_failure_never_starts_native_review(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys, local: bool
) -> None:
    """Cross real Git collection and prove a hard budget stops before OCR execution."""
    from ocr_toolkit import cli, review_runner
    from ocr_toolkit.evidence import budgets
    from ocr_toolkit.evidence.artifacts import repository_artifacts

    repository = tmp_path / "repository"
    repository.mkdir()
    git(repository, "init", "-q")
    (repository / "file.txt").write_text("base\n")
    git(repository, "add", ".")
    git(repository, "commit", "-qm", "base")
    base = git(repository, "rev-parse", "HEAD")
    (repository / "file.txt").write_text("head\n")
    git(repository, "commit", "-qam", "head")
    head = git(repository, "rev-parse", "HEAD")
    identity = review_identity()
    identity.update(
        source_sha=head,
        diff_base_sha=base,
        diff_head_sha=head,
        diff_start_sha=base,
        policy_sha=base,
        target_sha=base,
    )
    captured = review_runner.ReviewIdentity(**identity, context_mode="off", context=None)
    monkeypatch.chdir(repository)
    monkeypatch.setenv("OCR_LLM_URL", "https://llm.example.invalid/v1")
    monkeypatch.setenv("OCR_LLM_TOKEN", "synthetic-token")
    monkeypatch.setenv("OCR_LLM_MODEL", "synthetic-model")
    monkeypatch.setenv("CI_PROJECT_ID", "1")
    monkeypatch.setenv("CI_MERGE_REQUEST_IID", "2")
    monkeypatch.setenv("CI_COMMIT_SHA", head)
    monkeypatch.setenv("CI_MERGE_REQUEST_DIFF_BASE_SHA", base)
    monkeypatch.setenv("CI_MERGE_REQUEST_EVENT_TYPE", "detached")
    # Only provider authentication is replaced. Git, sizing, status persistence,
    # cleanup and CLI delivery are the actual production owners.
    monkeypatch.setattr(
        review_runner,
        "_prepare_policy_context",
        lambda refs, args, artifacts, **kw: (captured, args),
    )
    monkeypatch.setattr(budgets, "MAX_EVIDENCE_RECORDS", 8)
    monkeypatch.setattr(
        review_runner,
        "_run_background_qualified_review",
        lambda *a, **kw: pytest.fail("native review started after evidence failure"),
    )
    code = cli.main(
        [
            "review",
            *(["--local"] if local else []),
            "--result",
            str(tmp_path / "result.json"),
            "--stderr",
            str(tmp_path / "stderr.log"),
            "--",
            "--from",
            base,
            "--to",
            head,
        ]
    )
    assert code == 2
    output = capsys.readouterr()
    assert "requires at least 11 records; limit 8" in output.err
    artifacts = repository_artifacts(repository)
    assert not artifacts.store.exists()
    if local:
        assert not artifacts.pre_execution_status.exists()
        assert "Stopped at:" in (tmp_path / "result.json.md").read_text()
    else:
        persisted = read_pre_execution_status(
            artifacts.pre_execution_status, expected_diff_base_sha=base, expected_source_sha=head
        )
        assert persisted.schema_version == EVIDENCE_BUDGET_STATUS_SCHEMA
        assert persisted.actual == 11 and persisted.limit == 8


@pytest.mark.parametrize("drift", ["none", "target", "policy", "job"])
def test_budget_note_uses_real_git_freshness_and_preserves_previous_review(
    tmp_path, monkeypatch, drift
):
    """Publish only fresh safe diagnostics while preserving prior findings and approval state."""
    from dataclasses import asdict

    from ocr_toolkit.posting import workflow
    from ocr_toolkit.posting.snapshot import BotCommentRefs
    from ocr_toolkit.providers.gitlab import GitLabMergeRequestLifecycle
    from tests.support import gitlab_config
    from tests.test_posting_freshness import _environment, _live_snapshot, _receipt, _review_graph

    repository, snapshot, advanced, rewrite = _review_graph(tmp_path)
    reviewed = asdict(_receipt(snapshot))
    reviewed.pop("schema_version")
    value = replace(
        budget_status(),
        source_sha=snapshot.source_sha,
        diff_base_sha=snapshot.diff_base_sha,
        policy_sha=snapshot.policy_sha,
        review=reviewed,
    )
    path = private_directory(tmp_path) / "status.json"
    write_pre_execution_status(path, value)
    value = read_pre_execution_status(
        path, expected_diff_base_sha=snapshot.diff_base_sha, expected_source_sha=snapshot.source_sha
    )
    monkeypatch.chdir(repository)
    for name, content in _environment(snapshot).items():
        monkeypatch.setenv(name, content)
    if drift == "target":
        snapshot = replace(snapshot, target_sha=advanced)
    elif drift == "policy":
        snapshot = replace(snapshot, policy_sha=rewrite)
    elif drift == "job":
        monkeypatch.setenv("CI_JOB_ID", "12")
    _live_snapshot(monkeypatch, snapshot)
    monkeypatch.setenv("OCR_STRICT_POSTING", "false")
    previous = BotCommentRefs(plain_note_ids=[101], discussion_note_refs=[("old", 102)])
    notes = []
    monkeypatch.setattr(
        workflow,
        "current_merge_request_lifecycle",
        lambda config, sha: GitLabMergeRequestLifecycle("7", "9", snapshot.source_sha, "opened"),
    )
    monkeypatch.setattr(workflow, "collect_previous_bot_comment_refs", lambda config: previous)
    monkeypatch.setattr(
        workflow,
        "post_review_note_bounded",
        lambda config, title, body, transaction: notes.append((title, body)) or {"id": 200},
    )
    monkeypatch.setattr(workflow, "finalize_posting", lambda config, transaction: True)
    monkeypatch.setattr(
        workflow.gitlab_api,
        "api_request",
        lambda *a, **kw: pytest.fail("unexpected mutation/cleanup outside the diagnostic note"),
    )
    monkeypatch.setattr(
        workflow, "execute_approval", lambda *a, **kw: pytest.fail("approval attempted")
    )
    config = replace(gitlab_config(), project_id="7", merge_request_iid="9")
    assert workflow.post_pre_execution_status(config, value) == (0 if drift == "none" else 1)
    assert len(notes) == (1 if drift == "none" else 0)
    if notes:
        assert "evidence budget" in notes[0][0]
        assert "`513` records" in notes[0][1] and "`512` records" in notes[0][1]
        assert "comments were preserved" in notes[0][1]
    assert previous.plain_note_ids == [101] and previous.discussion_note_refs == [("old", 102)]
