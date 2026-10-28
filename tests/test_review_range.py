"""Prove topology and independent native input identity at production boundaries."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from ocr_toolkit import review_runner
from ocr_toolkit.evidence.repository import GitRepositoryReader, RepositoryEvidenceError
from ocr_toolkit.evidence.review_range import resolve_review_range
from ocr_toolkit.mcp_config import MCPCapability, MCPComposition
from ocr_toolkit.result_contract import OcrResultContractError
from ocr_toolkit.review_range import ReviewRange, admit_native_range
from tests.test_evidence_repository import git, synthetic_repository
from tests.test_review_runner import (
    BUILTIN_EVIDENCE_TOOLS,
    DEFAULT_IDENTITY,
    LOCAL_IDENTITY,
    SUMMARY_ACTION_COUNTS,
)

EXPECTED = ReviewRange("a" * 40, "b" * 40)


def native_result(review_range: ReviewRange = EXPECTED) -> dict[str, Any]:
    """A complete native result with deliberately independent input and coverage."""

    return {
        "status": "complete",
        "comments": [],
        "tool_calls": {"total": 1, "by_tool": {"ocr_toolkit_evidence": 1}},
        "manifest": {
            "schema_version": "ocr.run-manifest/v1",
            "operation": "review",
            "terminal_state": "complete",
            "input": {
                "mode": "range",
                "requested_from": review_range.base,
                "requested_head": review_range.head,
                "resolved_base": review_range.base,
                "resolved_head": review_range.head,
                "exact_range": review_range.exact_range,
            },
            "coverage": {
                "selected": [{"item_id": "app.py"}],
                "completed": [{"item_id": "app.py"}],
                "reused": [],
                "failed": [],
                "waived": [],
            },
        },
    }


@pytest.mark.parametrize(
    "field",
    ("mode", "requested_from", "requested_head", "resolved_base", "resolved_head", "exact_range"),
)
@pytest.mark.parametrize("value", (None, False, 40, "", "c" * 40))
def test_complete_coverage_never_substitutes_for_range_identity(field: str, value: object) -> None:
    result = native_result()
    result["manifest"]["input"][field] = value
    with pytest.raises(OcrResultContractError, match=field):
        admit_native_range(result, EXPECTED)
    del result["manifest"]["input"][field]
    with pytest.raises(OcrResultContractError, match=field):
        admit_native_range(result, EXPECTED)


@pytest.mark.parametrize("manifest", (None, [], {}, {"schema_version": "future"}))
def test_present_invalid_manifest_cannot_fall_back_to_legacy(manifest: object) -> None:
    with pytest.raises(OcrResultContractError, match="supported manifest"):
        admit_native_range({"status": "success", "manifest": manifest}, EXPECTED)


def test_operation_input_and_legacy_identity_are_independent_contracts() -> None:
    result = native_result()
    assert admit_native_range(result, EXPECTED) == EXPECTED
    assert admit_native_range({"status": "success"}, EXPECTED) is None
    for operation in (None, "summary", False):
        result["manifest"]["operation"] = operation
        with pytest.raises(OcrResultContractError, match="operation"):
            admit_native_range(result, EXPECTED)
    result["manifest"]["operation"] = "review"
    result["manifest"]["input"] = []
    with pytest.raises(OcrResultContractError, match="input is unavailable"):
        admit_native_range(result, EXPECTED)


@pytest.mark.parametrize(
    "identity", (None, 40, False, "HEAD", "A" * 40, "a" * 39, "a" * 41, "a" * 39 + "\n")
)
def test_immutable_range_rejects_mutable_or_malformed_identities(identity: Any) -> None:
    with pytest.raises(OcrResultContractError, match="immutable"):
        ReviewRange(identity, EXPECTED.head)
    with pytest.raises(OcrResultContractError, match="immutable"):
        ReviewRange(EXPECTED.base, identity)


def test_real_ancestor_equal_and_merge_first_parent_ranges(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, base, head = synthetic_repository(tmp_path)
    reader = GitRepositoryReader(root)
    assert resolve_review_range(reader, base, head) == ReviewRange(base, head)
    assert resolve_review_range(reader, head, head) == ReviewRange(head, head)
    git(root, "checkout", "-qb", "side", base)
    (root / "side.py").write_text("value = 1\n")
    git(root, "add", "side.py")
    git(root, "commit", "-qm", "side")
    side = git(root, "rev-parse", "HEAD")
    git(root, "checkout", "-qb", "mainline", head)
    git(root, "merge", "--no-ff", "-qm", "merge", side)
    merged = git(root, "rev-parse", "HEAD")
    monkeypatch.chdir(root)
    requested = review_runner._review_refs(["--commit", merged])
    resolved = review_runner._immutable_review_refs(requested)
    assert (resolved.base, resolved.head) == (head, merged)


@pytest.mark.parametrize("topology", ("sibling", "unrelated", "reverse", "shallow"))
@pytest.mark.parametrize("local", (False, True))
def test_unsupported_real_range_stops_launcher_before_acquisition(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, topology: str, local: bool
) -> None:
    root, base, head = synthetic_repository(tmp_path)
    requested_base, requested_head = head, base
    if topology == "sibling":
        git(root, "checkout", "-qb", "sibling", base)
        (root / "sibling.py").write_text("value = 1\n")
        git(root, "add", "sibling.py")
        git(root, "commit", "-qm", "sibling")
        requested_head = git(root, "rev-parse", "HEAD")
    elif topology == "unrelated":
        git(root, "checkout", "--orphan", "unrelated")
        git(root, "commit", "--allow-empty", "-qm", "unrelated")
        requested_head = git(root, "rev-parse", "HEAD")
    elif topology == "shallow":
        shallow = tmp_path / "shallow"
        git(tmp_path, "clone", "-q", "--depth=1", f"file://{root}", str(shallow))
        GitRepositoryReader(shallow).fetch_commit(base)
        root = shallow
        requested_base, requested_head = base, head
    monkeypatch.chdir(root)
    monkeypatch.setenv("OCR_LLM_AUTH_MODE", "api-key")
    for name in ("_prepare_policy_context", "collect_repository_evidence", "run_review"):
        monkeypatch.setattr(
            review_runner,
            name,
            lambda *_args, **_kwargs: pytest.fail("range must stop before acquisition/model"),
        )
    message = "shallow repository" if topology == "shallow" else "ancestor"
    with pytest.raises(review_runner.ReviewRunnerError, match=message):
        review_runner.run_evidence_review(
            root / "result.json",
            root / "stderr.log",
            ["--from", requested_base, "--to", requested_head],
            local=local,
        )
    assert not (root / "result.json").exists()


def test_range_resolver_does_not_adopt_replacement_or_grafted_history(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, base, head = synthetic_repository(tmp_path)
    git(root, "replace", head, base)
    monkeypatch.setenv("GIT_NO_REPLACE_OBJECTS", "0")
    assert resolve_review_range(GitRepositoryReader(root), base, head) == ReviewRange(base, head)
    grafts = root / ".git" / "info" / "grafts"
    grafts.write_text(f"{head}\n")
    with pytest.raises(RepositoryEvidenceError, match="grafts"):
        resolve_review_range(GitRepositoryReader(root), base, head)


def test_range_proof_preserves_a_reused_checkout_with_staged_dirty_and_untracked_work(
    tmp_path: Path,
) -> None:
    """The read boundary cannot alter persistent checkout state on either outcome."""

    root, base, head = synthetic_repository(tmp_path)
    changed = root / "changed.txt"
    changed.write_text("staged work\n")
    git(root, "add", "changed.txt")
    changed.write_text("unstaged work\n")
    untracked = root / "untracked.py"
    untracked.write_text("private_work = True\n")
    paths = (changed, untracked, root / ".git" / "index", root / ".git" / "HEAD")
    before = tuple(path.read_bytes() for path in paths)
    reader = GitRepositoryReader(root)
    for _attempt in range(2):
        assert resolve_review_range(reader, base, head) == ReviewRange(base, head)
        with pytest.raises(RepositoryEvidenceError, match="ancestor"):
            resolve_review_range(reader, head, base)
        assert tuple(path.read_bytes() for path in paths) == before


def test_finalizer_rejects_stale_native_identity_before_report_or_persistence(
    tmp_path: Path,
) -> None:
    result = native_result()
    result["manifest"]["input"]["resolved_base"] = "c" * 40
    path = tmp_path / "result.json"
    path.write_text(json.dumps(result))
    composition = MCPComposition(
        {}, (MCPCapability("ocr_toolkit_evidence", BUILTIN_EVIDENCE_TOOLS, True),), (), ()
    )
    with pytest.raises(review_runner.ReviewRunnerError, match="did not prove the review range"):
        review_runner._finalize_ocr_result(
            path,
            composition,
            replace(LOCAL_IDENTITY, source_sha=EXPECTED.head),
            None,
            SUMMARY_ACTION_COUNTS,
            forbidden=(),
            expected_range=EXPECTED,
            report_consumer=lambda _report: pytest.fail("unverified report"),
        )
    assert not path.exists()


@pytest.mark.parametrize("legacy", (False, True))
@pytest.mark.parametrize("local", (False, True))
def test_only_proven_range_reaches_admitted_report(
    tmp_path: Path, legacy: bool, local: bool
) -> None:
    result = native_result()
    if legacy:
        del result["manifest"]
        result["status"] = "success"
    path = tmp_path / "result.json"
    path.write_text(json.dumps(result))
    composition = MCPComposition(
        {}, (MCPCapability("ocr_toolkit_evidence", BUILTIN_EVIDENCE_TOOLS, True),), (), ()
    )
    reports = []
    identity = (
        replace(LOCAL_IDENTITY, source_sha=EXPECTED.head)
        if local
        else replace(
            DEFAULT_IDENTITY,
            source_sha=EXPECTED.head,
            diff_base_sha=EXPECTED.base,
            diff_head_sha=EXPECTED.head,
            target_sha="c" * 40,
            target_branch="integration",
            target_protection="unprotected",
            policy_sha="e" * 40,
        )
    )
    review_runner._finalize_ocr_result(
        path,
        composition,
        identity,
        None,
        SUMMARY_ACTION_COUNTS,
        forbidden=(),
        expected_range=EXPECTED,
        report_consumer=reports.append,
    )
    assert len(reports) == 1
    assert reports[0].review_range == (None if legacy else EXPECTED)
    assert path.is_file()


@pytest.mark.parametrize(
    "identity",
    (
        LOCAL_IDENTITY,
        DEFAULT_IDENTITY,
        replace(
            DEFAULT_IDENTITY,
            source_sha=EXPECTED.head,
            diff_head_sha=EXPECTED.head,
            diff_base_sha="c" * 40,
        ),
    ),
)
def test_finalizer_rejects_execution_owner_identity_disagreement(
    tmp_path: Path, identity: review_runner.ReviewIdentity
) -> None:
    composition = MCPComposition({}, (), (), ())
    with pytest.raises(review_runner.ReviewRunnerError, match="execution identity"):
        review_runner._finalize_ocr_result(
            tmp_path / "absent.json",
            composition,
            identity,
            None,
            forbidden=(),
            expected_range=EXPECTED,
        )
