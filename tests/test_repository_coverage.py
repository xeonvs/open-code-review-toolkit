"""Closed v12 partial coverage and v6 no-model status contracts."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

from ocr_toolkit import review_runner
from ocr_toolkit.evidence.gitlink_projection import (
    gitlink_selection_proof,
    make_gitlink_projection,
)
from ocr_toolkit.evidence.gitlinks import plan_gitlink_input
from ocr_toolkit.evidence.repository import GitRepositoryReader, RepositoryEvidenceError
from ocr_toolkit.mcp_config import MCPCapability, MCPComposition
from ocr_toolkit.ocr_result import TOOLKIT_GITLINK_SELECTION_KEY, TOOLKIT_RESULT_KEY
from ocr_toolkit.posting import workflow
from ocr_toolkit.posting.snapshot import BotCommentRefs
from ocr_toolkit.posting.transaction import PostingTransaction
from ocr_toolkit.pre_execution import (
    GITLINK_NO_REVIEWABLE_FILES,
    GITLINK_PREVIEW_UNSUPPORTED,
    GITLINK_PROJECTION_UNQUALIFIED,
    GITLINK_STATUS_SCHEMA,
    OCR_PREVIEW_STAGE,
    STATUS_SCHEMA,
    PreExecutionStatus,
    PreExecutionStatusError,
    pre_execution_review_identity,
    read_pre_execution_status,
    write_pre_execution_status,
)
from ocr_toolkit.providers.local import local_summary
from ocr_toolkit.reporting.model import failed_report
from ocr_toolkit.repository_coverage import (
    GITLINK_PARTIAL_REASON,
    REPOSITORY_COVERAGE_SCHEMA,
    RepositoryCoverageError,
    coverage_from_projection,
    parse_repository_coverage,
)
from ocr_toolkit.result_contract import ReviewOutcome
from ocr_toolkit.review_receipt import (
    automatic_approval_metadata_reason,
    receipt_review_identity,
    toolkit_receipt_is_valid,
)
from tests.support import gitlab_config, native_range_input
from tests.test_gitlinks import _fixture, _gitlink_only_fixture, _mixed_fixture, _move_fixture
from tests.test_result_contract import manifest_result
from tests.test_review_receipt_v11 import _receipt_v11
from tests.test_review_receipt_v13 import CURRENT_RANGE, _receipt_v13
from tests.test_review_runner import (
    BUILTIN_EVIDENCE_TOOLS,
    DEFAULT_IDENTITY,
    SUMMARY_ACTION_COUNTS,
    complete_review_payload,
)


def _coverage(*, state: str = "partial") -> dict[str, object]:
    selected = 1 if state == "partial" else 0
    return {
        "schema_version": REPOSITORY_COVERAGE_SCHEMA,
        "state": state,
        "reason": GITLINK_PARTIAL_REASON,
        "ordinary_changed": 1,
        "ordinary_selected": selected,
        "ordinary_completed": selected,
        "ordinary_excluded": 1 - selected,
        "gitlink_changes": 1,
        "gitlink_added": 0,
        "gitlink_updated": 1,
        "gitlink_deleted": 0,
        "gitlink_moved": 0,
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("reason", "future_reason"),
        ("state", "complete"),
        ("state", []),
        ("state", {}),
        ("ordinary_selected", True),
        ("ordinary_completed", 0),
        ("ordinary_excluded", 1),
        ("gitlink_changes", 0),
        ("gitlink_moved", 1),
    ],
)
def test_repository_coverage_rejects_tampered_closed_fields(field: str, value: object) -> None:
    payload = _coverage()
    payload[field] = value
    with pytest.raises(RepositoryCoverageError):
        parse_repository_coverage(payload, required_state="partial")


def test_effective_coverage_counts_both_endpoints_of_gitlink_move(tmp_path: Path) -> None:
    base, head = _move_fixture(tmp_path)
    reader = GitRepositoryReader(tmp_path)
    plan = plan_gitlink_input(reader, base, head)
    assert plan is not None
    projection = make_gitlink_projection(reader, plan)
    coverage = coverage_from_projection(projection, projection.ordinary_diff, state="partial")
    assert coverage.gitlink_changes == 2
    assert coverage.gitlink_moved == 1
    assert coverage.gitlink_added == coverage.gitlink_deleted == 0
    assert coverage.ordinary_completed == len(projection.ordinary_diff)


def test_v12_receipt_is_valid_but_cannot_approve_or_upgrade_v11() -> None:
    old = _receipt_v11()
    assert toolkit_receipt_is_valid(old)
    assert receipt_review_identity(old).schema_version == 11  # type: ignore[union-attr]

    partial = deepcopy(old)
    partial["schema_version"] = 12
    partial["repository_coverage"] = _coverage()
    assert toolkit_receipt_is_valid(partial)
    assert receipt_review_identity(partial).schema_version == 12  # type: ignore[union-attr]
    assert "submodule pointers were not reviewed" in automatic_approval_metadata_reason(partial)

    missing = deepcopy(partial)
    missing.pop("repository_coverage")
    assert not toolkit_receipt_is_valid(missing)
    old_with_new_field = deepcopy(old)
    old_with_new_field["repository_coverage"] = _coverage()
    assert not toolkit_receipt_is_valid(old_with_new_field)
    malformed = deepcopy(partial)
    malformed["repository_coverage"]["gitlink_changes"] = 2
    assert not toolkit_receipt_is_valid(malformed)


def test_v6_no_model_status_round_trips_without_changing_v5_wire_shape(tmp_path: Path) -> None:
    review = _receipt_v11()["review"]
    status_path = tmp_path / "status.json"
    status = PreExecutionStatus(
        schema_version=GITLINK_STATUS_SCHEMA,
        reason=GITLINK_NO_REVIEWABLE_FILES,
        diff_base_sha=review["diff_base_sha"],
        source_sha=review["source_sha"],
        policy_sha=review["policy_sha"],
        review=review,
        stage=OCR_PREVIEW_STAGE,
        repository_coverage=_coverage(state="not_started"),
    )
    write_pre_execution_status(status_path, status)
    loaded = read_pre_execution_status(
        status_path,
        expected_diff_base_sha=review["diff_base_sha"],
        expected_source_sha=review["source_sha"],
    )
    assert loaded == status
    identity = pre_execution_review_identity(loaded)
    assert identity is not None and identity.schema_version == 12

    legacy = PreExecutionStatus(
        schema_version=STATUS_SCHEMA,
        reason=GITLINK_PREVIEW_UNSUPPORTED,
        diff_base_sha=review["diff_base_sha"],
        source_sha=review["source_sha"],
        policy_sha=review["policy_sha"],
        review=review,
        stage=OCR_PREVIEW_STAGE,
    )
    write_pre_execution_status(status_path, legacy)
    assert "repository_coverage" not in json.loads(status_path.read_text())
    assert (
        read_pre_execution_status(
            status_path,
            expected_diff_base_sha=review["diff_base_sha"],
            expected_source_sha=review["source_sha"],
        )
        == legacy
    )


@pytest.mark.parametrize("schema_version", [[], {}])
def test_v6_status_rejects_unhashable_schema_version(
    tmp_path: Path, schema_version: object
) -> None:
    review = _receipt_v11()["review"]
    path = tmp_path / "status.json"
    status = PreExecutionStatus(
        schema_version=GITLINK_STATUS_SCHEMA,
        reason=GITLINK_NO_REVIEWABLE_FILES,
        diff_base_sha=review["diff_base_sha"],
        source_sha=review["source_sha"],
        policy_sha=review["policy_sha"],
        review=review,
        stage=OCR_PREVIEW_STAGE,
        repository_coverage=_coverage(state="not_started"),
    )
    write_pre_execution_status(path, status)
    payload = json.loads(path.read_text())
    payload["schema_version"] = schema_version
    path.write_text(json.dumps(payload))
    with pytest.raises(PreExecutionStatusError, match="fields are invalid"):
        read_pre_execution_status(
            path,
            expected_diff_base_sha=review["diff_base_sha"],
            expected_source_sha=review["source_sha"],
        )


def test_v6_no_model_status_rejects_wrong_coverage(tmp_path: Path) -> None:
    review = _receipt_v11()["review"]
    status = PreExecutionStatus(
        schema_version=GITLINK_STATUS_SCHEMA,
        reason=GITLINK_NO_REVIEWABLE_FILES,
        diff_base_sha=review["diff_base_sha"],
        source_sha=review["source_sha"],
        policy_sha=review["policy_sha"],
        review=review,
        stage=OCR_PREVIEW_STAGE,
        repository_coverage=_coverage(state="partial"),
    )
    with pytest.raises(PreExecutionStatusError, match="coverage"):
        write_pre_execution_status(tmp_path / "status.json", status)


def test_v6_unqualified_status_has_no_claimed_coverage(tmp_path: Path) -> None:
    review = _receipt_v11()["review"]
    status = PreExecutionStatus(
        schema_version=GITLINK_STATUS_SCHEMA,
        reason=GITLINK_PROJECTION_UNQUALIFIED,
        diff_base_sha=review["diff_base_sha"],
        source_sha=review["source_sha"],
        policy_sha=review["policy_sha"],
        review=review,
        stage=OCR_PREVIEW_STAGE,
    )
    path = tmp_path / "status.json"
    write_pre_execution_status(path, status)
    assert (
        read_pre_execution_status(
            path,
            expected_diff_base_sha=review["diff_base_sha"],
            expected_source_sha=review["source_sha"],
        )
        == status
    )
    with pytest.raises(PreExecutionStatusError, match="coverage"):
        write_pre_execution_status(path, replace(status, repository_coverage=_coverage()))
    with pytest.raises(PreExecutionStatusError, match="identity"):
        write_pre_execution_status(path, replace(status, review=None))


def test_local_report_names_partial_and_no_model_gitlink_coverage() -> None:
    stopped = failed_report(
        "preview",
        repository_coverage=parse_repository_coverage(_coverage(state="not_started")),
    )
    no_model = local_summary(stopped)
    assert "no ordinary files were selected" in no_model
    assert "1 changed gitlink pointer(s) remain unreviewed" in no_model
    assert "coverage and execution usage are unavailable" not in no_model

    partial = replace(
        stopped,
        outcome=ReviewOutcome(status="complete", kind="clean", budget_exceeded=False),
        failure_stage=None,
        repository_coverage=parse_repository_coverage(_coverage()),
    )
    rendered = local_summary(partial)
    assert "Repository coverage: partial" in rendered
    assert "1 of 1 ordinary diff record(s) completed" in rendered
    unqualified = local_summary(failed_report("preview", gitlink_unqualified=True))
    assert "could not be qualified and were not reviewed" in unqualified


def test_post_rebuilds_native_partial_coverage_and_rejects_tampering(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base, head = _fixture(tmp_path, "updated")
    monkeypatch.chdir(tmp_path)
    reader = GitRepositoryReader(tmp_path)
    plan = plan_gitlink_input(reader, base, head)
    assert plan is not None
    projection = make_gitlink_projection(reader, plan)
    item_id, fingerprint = projection.fingerprints[0]
    item = {"item_id": item_id, "path": "main.php", "fingerprint": fingerprint}
    source = hashlib.sha256()
    for field in (item_id, fingerprint):
        raw = field.encode()
        source.update(len(raw).to_bytes(8, "big"))
        source.update(raw)
    result = {
        "status": "complete",
        "comments": [],
        "manifest": {
            "schema_version": "ocr.run-manifest/v1",
            "operation": "review",
            "terminal_state": "complete",
            "input": {
                "mode": "range",
                "requested_from": base,
                "requested_head": head,
                "resolved_base": base,
                "resolved_head": head,
                "exact_range": f"{base}..{head}",
                "source_artifact_sha256": source.hexdigest(),
            },
            "execution": {"ocr_version": "v1.13.3"},
            "coverage": {
                "selected": [item],
                "completed": [item],
                "reused": [],
                "failed": [],
                "waived": [],
            },
        },
        "_ocr_toolkit": {"repository_coverage": _coverage()},
    }
    identity = replace(
        receipt_review_identity(_receipt_v11()),  # type: ignore[arg-type]
        schema_version=12,
        diff_base_sha=base,
        source_sha=head,
    )
    assert workflow.verified_partial_repository_coverage(result, identity).ordinary_completed == 1
    result["_ocr_toolkit"]["repository_coverage"]["ordinary_completed"] = 0
    with pytest.raises(RepositoryEvidenceError, match="coverage"):
        workflow.verified_partial_repository_coverage(result, identity)
    result["_ocr_toolkit"]["repository_coverage"] = _coverage()
    result["manifest"]["coverage"]["selected"] = []
    result["manifest"]["coverage"]["completed"] = []
    result["manifest"]["input"]["source_artifact_sha256"] = hashlib.sha256().hexdigest()
    with pytest.raises(RepositoryEvidenceError, match="selected coverage"):
        workflow.verified_partial_repository_coverage(result, identity)


def test_dlp_filtered_gitlink_review_keeps_safe_finding_and_verifiable_coverage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base, head = _fixture(tmp_path, "updated")
    monkeypatch.chdir(tmp_path)
    reader = GitRepositoryReader(tmp_path)
    plan = plan_gitlink_input(reader, base, head)
    assert plan is not None
    projection = make_gitlink_projection(reader, plan)
    selected = projection.ordinary_diff
    proof = gitlink_selection_proof(projection, selected)
    item_id, fingerprint = projection.fingerprints[0]
    item = {"item_id": item_id, "path": "main.php", "fingerprint": fingerprint}
    payload = complete_review_payload(
        tool_calls={"total": 1, "by_tool": {"ocr_toolkit_evidence": 1}}
    )
    payload["comments"] = [
        {
            "path": "main.php",
            "line": 2,
            "content": "Safe actionable finding.",
            "severity": "medium",
            "category": "bug",
        },
        {
            "path": "main.php",
            "line": 2,
            "content": "synthetic-secret-token must not be published",
            "severity": "medium",
            "category": "bug",
        },
    ]
    manifest = payload["manifest"]
    assert isinstance(manifest, dict)
    manifest["input"] = {
        "mode": "range",
        "requested_from": base,
        "requested_head": head,
        "resolved_base": base,
        "resolved_head": head,
        "exact_range": f"{base}..{head}",
        "source_artifact_sha256": proof["source_artifact_sha256"],
    }
    manifest["execution"] = {"ocr_version": "v1.13.3"}
    manifest["coverage"] = {
        "selected": [item],
        "completed": [item],
        "reused": [],
        "failed": [],
        "waived": [],
    }
    result_path = tmp_path / "result.json"
    result_path.write_text(json.dumps(payload), encoding="utf-8")
    identity = replace(
        DEFAULT_IDENTITY,
        source_sha=head,
        policy_sha=base,
        target_sha=base,
        diff_base_sha=base,
        diff_start_sha=base,
        diff_head_sha=head,
    )
    composition = MCPComposition(
        payload={},
        capabilities=(MCPCapability("ocr_toolkit_evidence", BUILTIN_EVIDENCE_TOOLS, True),),
        external_servers=(),
        secret_values=(),
    )
    _usage, filtered, publication = review_runner._finalize_ocr_result(
        result_path,
        composition,
        identity,
        None,
        SUMMARY_ACTION_COUNTS,
        forbidden=("synthetic-secret-token",),
        projection=projection,
        selected_diff=selected,
    )
    assert filtered and publication["state"] == "publication-filtered"
    result = json.loads(result_path.read_text())
    assert result["status"] == "completed_with_errors"
    assert "manifest" not in result
    assert len(result["comments"]) == 1
    assert result["comments"][0]["content"] == "Safe actionable finding."
    assert "synthetic-secret-token" not in result_path.read_text()
    assert result[TOOLKIT_GITLINK_SELECTION_KEY] == proof
    receipt = result[TOOLKIT_RESULT_KEY]
    assert toolkit_receipt_is_valid(receipt)
    receipt_identity = receipt_review_identity(receipt)
    assert receipt_identity is not None
    assert (
        workflow.verified_partial_repository_coverage(result, receipt_identity).ordinary_completed
        == 1
    )
    assert "publication DLP filtered" in automatic_approval_metadata_reason(receipt)

    for mutation in (
        "missing",
        "item",
        "fingerprint",
        "original",
        "gitlink_comment",
        "unhashable_comment",
    ):
        tampered = deepcopy(result)
        if mutation == "missing":
            tampered.pop(TOOLKIT_GITLINK_SELECTION_KEY)
        elif mutation == "item":
            tampered[TOOLKIT_GITLINK_SELECTION_KEY]["selected_item_ids"] = ["0" * 64]
        elif mutation == "fingerprint":
            tampered[TOOLKIT_GITLINK_SELECTION_KEY]["source_artifact_sha256"] = "0" * 64
        elif mutation == "original":
            tampered[TOOLKIT_RESULT_KEY]["publication"]["original"]["completed"] = 0
        elif mutation == "gitlink_comment":
            tampered["comments"][0]["path"] = "schema"
        else:
            tampered["comments"][0]["path"] = []
        with pytest.raises(RepositoryEvidenceError):
            workflow.verified_partial_repository_coverage(tampered, receipt_identity)


def test_filtered_selection_proof_preserves_native_subset_not_all_ordinary_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base, head = _mixed_fixture(tmp_path)
    monkeypatch.chdir(tmp_path)
    reader = GitRepositoryReader(tmp_path)
    plan = plan_gitlink_input(reader, base, head)
    assert plan is not None
    projection = make_gitlink_projection(reader, plan)
    assert len(projection.ordinary_diff) > 1
    selected = (next(entry for entry in projection.ordinary_diff if entry.status != "D"),)
    coverage = coverage_from_projection(projection, selected, state="partial")
    proof = gitlink_selection_proof(projection, selected)
    result = {
        "status": "completed_with_errors",
        "comments": [{"path": selected[0].path}],
        TOOLKIT_GITLINK_SELECTION_KEY: proof,
        TOOLKIT_RESULT_KEY: {
            "publication": {
                "state": "publication-filtered",
                "original": {
                    "outcome": "clean",
                    "selected": 1,
                    "completed": 1,
                    "reused": 0,
                    "failed": 0,
                    "waived": 0,
                },
            },
            "repository_coverage": coverage.payload(),
        },
    }
    identity = replace(
        receipt_review_identity(_receipt_v11()),  # type: ignore[arg-type]
        schema_version=12,
        diff_base_sha=base,
        source_sha=head,
    )
    actual = workflow.verified_partial_repository_coverage(result, identity)
    assert actual.ordinary_selected == 1
    assert actual.ordinary_excluded == len(projection.ordinary_diff) - 1
    assert selected[0].path not in json.dumps(proof)


def test_post_rechecks_gitlink_only_advisory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base, head = _gitlink_only_fixture(tmp_path)
    monkeypatch.chdir(tmp_path)
    coverage = _coverage(state="not_started")
    coverage["ordinary_changed"] = 0
    coverage["ordinary_excluded"] = 0
    review = dict(_receipt_v11()["review"])
    review.update(
        source_sha=head,
        diff_base_sha=base,
        diff_start_sha=base,
        diff_head_sha=head,
        target_sha=base,
        policy_sha=base,
    )
    status = PreExecutionStatus(
        schema_version=GITLINK_STATUS_SCHEMA,
        reason=GITLINK_NO_REVIEWABLE_FILES,
        diff_base_sha=base,
        source_sha=head,
        policy_sha=base,
        review=review,
        stage=OCR_PREVIEW_STAGE,
        repository_coverage=coverage,
    )
    assert pre_execution_review_identity(status) is not None
    assert workflow.verified_no_model_repository_coverage(status).gitlink_changes == 1
    coverage["gitlink_changes"] = 2
    with pytest.raises(RepositoryEvidenceError, match="coverage"):
        workflow.verified_no_model_repository_coverage(
            replace(status, repository_coverage=coverage)
        )


def test_partial_effective_cleanup_keeps_old_findings_and_discussions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    identity = replace(
        receipt_review_identity(_receipt_v11()),  # type: ignore[arg-type]
        schema_version=14,
    )
    previous = BotCommentRefs(
        plain_note_ids=[11],
        summary_plain_note_ids=[12],
        discussions_to_resolve=["discussion-13"],
    )
    deleted: list[int] = []
    monkeypatch.setattr(workflow, "publication_freshness_or_exit", lambda *_a, **_k: None)
    monkeypatch.setattr(workflow, "current_publication_or_rollback", lambda *_a, **_k: True)
    monkeypatch.setattr(
        workflow.gitlab_api, "delete_plain_note", lambda _config, note: deleted.append(note) or True
    )
    monkeypatch.setattr(
        workflow, "resolve_discussion", lambda *_a: pytest.fail("must preserve old threads")
    )
    assert workflow.finalize_previous_review_state(
        None,  # type: ignore[arg-type]
        previous,
        ReviewOutcome(status="complete", kind="clean", budget_exceeded=False),
        review_identity=identity,
        transaction=PostingTransaction(),
    )
    assert deleted == [12]


def test_partial_post_rejects_unproven_coverage_before_gitlab_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    receipt = _receipt_v13()
    receipt["schema_version"] = 14
    receipt["repository_coverage"] = _coverage()
    assert toolkit_receipt_is_valid(receipt)
    seen = []

    def reject(*_args):
        seen.append("coverage")
        raise RepositoryEvidenceError("synthetic mismatch")

    monkeypatch.setattr(workflow, "verified_partial_repository_coverage", reject)
    monkeypatch.setattr(
        workflow,
        "collect_previous_bot_comment_refs",
        lambda *_args: pytest.fail("GitLab must not be read for unproven coverage"),
    )
    result = manifest_result("complete", selected=["a"], completed=["a"])
    result["manifest"]["input"] = native_range_input(CURRENT_RANGE.base, CURRENT_RANGE.head)
    result["_ocr_toolkit"] = receipt
    assert workflow.post_results(gitlab_config(), result) == 1
    assert seen == ["coverage"]


def test_v12_identity_uses_current_publication_freshness(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    identity = replace(
        receipt_review_identity(_receipt_v11()),  # type: ignore[arg-type]
        schema_version=12,
    )
    seen: list[int] = []
    expected = workflow.ReviewFreshnessResult(identity.policy_sha, False)

    def check(_environment: object, current: object, _root: object) -> object:
        seen.append(current.schema_version)  # type: ignore[attr-defined]
        return expected

    monkeypatch.setattr(workflow, "validate_review_freshness", check)
    assert workflow.validate_posting_review_identity(gitlab_config(), identity) == expected
    assert seen == [12]


@pytest.mark.parametrize("strict", [False, True])
def test_no_model_gitlink_post_is_advisory_with_closed_coverage(
    monkeypatch: pytest.MonkeyPatch, strict: bool
) -> None:
    review = _receipt_v11()["review"]
    status = PreExecutionStatus(
        schema_version=GITLINK_STATUS_SCHEMA,
        reason=GITLINK_NO_REVIEWABLE_FILES,
        diff_base_sha=review["diff_base_sha"],
        source_sha=review["source_sha"],
        policy_sha=review["policy_sha"],
        review=review,
        stage=OCR_PREVIEW_STAGE,
        repository_coverage=_coverage(state="not_started"),
    )
    notes: list[str] = []
    monkeypatch.setattr(workflow, "pre_execution_status_fresh_or_exit", lambda *_a, **_k: None)
    monkeypatch.setattr(
        workflow,
        "verified_no_model_repository_coverage",
        lambda *_a: parse_repository_coverage(_coverage(state="not_started")),
    )
    monkeypatch.setattr(
        workflow,
        "current_merge_request_lifecycle",
        lambda *_a: workflow.GitLabMergeRequestLifecycle("1", "2", status.source_sha, "opened"),
    )
    monkeypatch.setattr(workflow, "collect_previous_bot_comment_refs", lambda *_a: BotCommentRefs())
    monkeypatch.setattr(
        workflow,
        "post_review_note_bounded",
        lambda _config, _title, body, _transaction: notes.append(body) or {"id": 1},
    )
    monkeypatch.setattr(workflow, "finalize_posting", lambda *_a: True)
    monkeypatch.setattr(workflow, "strict_posting", lambda: strict)
    assert workflow.post_pre_execution_status(gitlab_config(), status) == int(strict)
    assert len(notes) == 1
    assert "no ordinary files were selected" in notes[0]
    assert "changed gitlink pointer(s) remain unreviewed" in notes[0]
