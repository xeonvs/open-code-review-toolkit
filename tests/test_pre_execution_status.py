"""Hostile persistence tests for the closed pre-execution outcome."""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path

import pytest

from ocr_toolkit.pre_execution import (
    BACKGROUND_CHARACTER_LIMIT_REASON,
    BACKGROUND_FILE_SIZE_LIMIT_REASON,
    EVIDENCE_PREFLIGHT_STAGE,
    GITLAB_MERGE_REQUEST_TERMINAL,
    MAX_STATUS_BYTES,
    MODEL_NOT_STARTED,
    OCR_PREVIEW_STAGE,
    PROTECTED_POLICY_RULE_PATH_PENDING,
    PROTECTED_TARGET_RULE_PATH_PENDING,
    REVIEW_IDENTITY_UNAVAILABLE,
    REVIEWED_REVISION_NO_LONGER_CURRENT,
    STATUS_SCHEMA,
    UNCLASSIFIED_PREVIEW_DIAGNOSTICS,
    PreExecutionStatus,
    PreExecutionStatusError,
    pre_execution_review_identity,
    read_pre_execution_status,
    write_pre_execution_status,
)

BASE = "a" * 40
SOURCE = "b" * 40
POLICY = "c" * 40


def review_identity() -> dict[str, object]:
    return {
        "project_id": "1",
        "merge_request_iid": "2",
        "mr_author_id": 41,
        "source_sha": SOURCE,
        "diff_base_sha": BASE,
        "diff_start_sha": POLICY,
        "diff_head_sha": SOURCE,
        "diff_version_id": 7,
        "target_branch": "main",
        "target_sha": POLICY,
        "target_protection": "protected",
        "policy_project_id": "1",
        "policy_branch": "main",
        "policy_sha": POLICY,
        "policy_protection": "protected",
        "protection_mode": "auto",
    }


def status() -> PreExecutionStatus:
    return PreExecutionStatus(
        schema_version=STATUS_SCHEMA,
        reason=PROTECTED_TARGET_RULE_PATH_PENDING,
        diff_base_sha=BASE,
        source_sha=SOURCE,
        policy_sha=POLICY,
        review=review_identity(),
    )


def private_directory(tmp_path: Path) -> Path:
    directory = tmp_path / ".review-context"
    directory.mkdir(mode=0o700)
    return directory


def test_pre_execution_status_atomic_round_trip_and_identity_binding(tmp_path: Path) -> None:
    path = private_directory(tmp_path) / "pre-execution-status.json"

    write_pre_execution_status(path, status())

    identity = pre_execution_review_identity(status())
    assert identity is not None
    assert identity.schema_version == 11
    assert identity.target_branch == "main"
    assert identity.policy_sha == POLICY

    assert path.stat().st_mode & 0o777 == 0o600
    assert (
        read_pre_execution_status(
            path,
            expected_diff_base_sha=BASE,
            expected_source_sha=SOURCE,
        )
        == status()
    )
    for base, source_sha in (("d" * 40, SOURCE), (BASE, "d" * 40), ("bad", SOURCE)):
        with pytest.raises(PreExecutionStatusError, match="identity"):
            read_pre_execution_status(
                path,
                expected_diff_base_sha=base,
                expected_source_sha=source_sha,
            )


def test_pre_execution_status_rejects_hostile_files_and_closed_schema_changes(
    tmp_path: Path,
) -> None:
    directory = private_directory(tmp_path)
    path = directory / "pre-execution-status.json"
    valid = {
        "schema_version": STATUS_SCHEMA,
        "reason": PROTECTED_TARGET_RULE_PATH_PENDING,
        "diff_base_sha": BASE,
        "source_sha": SOURCE,
        "policy_sha": POLICY,
        "review": review_identity(),
        "stage": EVIDENCE_PREFLIGHT_STAGE,
        "model_execution": MODEL_NOT_STARTED,
        "diagnostic_count": None,
        "actual": None,
        "limit": None,
        "unit": None,
        "provider": None,
        "project_id": None,
        "change_id": None,
        "terminal_state": None,
    }

    variants = (
        {**valid, "schema_version": "ocr.pre-execution-status/v1"},
        {**valid, "stage": "model_review"},
        {**valid, "model_execution": "unknown"},
        {**valid, "diagnostic_count": 1},
        {**valid, "reason": "repository supplied display text"},
        {**valid, "path": ".opencodereview/rules.json"},
        {**valid, "policy_sha": True},
        {**valid, "policy_sha": "0" * 40},
        {**valid, "actual": 8_001},
        {
            **valid,
            "reason": BACKGROUND_CHARACTER_LIMIT_REASON,
            "actual": 8_001,
            "limit": 8_000,
            "unit": "bytes",
        },
        {
            **valid,
            "reason": BACKGROUND_FILE_SIZE_LIMIT_REASON,
            "actual": True,
            "limit": 1,
            "unit": "bytes",
        },
        {
            **valid,
            "reason": BACKGROUND_CHARACTER_LIMIT_REASON,
            "actual": 2_000,
            "limit": 2_000,
            "unit": "characters",
        },
    )
    for payload in variants:
        path.write_text(json.dumps(payload), encoding="utf-8")
        path.chmod(0o600)
        with pytest.raises(PreExecutionStatusError, match=r"fields|review identity"):
            read_pre_execution_status(
                path,
                expected_diff_base_sha=BASE,
                expected_source_sha=SOURCE,
            )

    path.write_text('{"reason":"one","reason":"two"}', encoding="utf-8")
    path.chmod(0o600)
    with pytest.raises(PreExecutionStatusError, match="duplicate"):
        read_pre_execution_status(
            path,
            expected_diff_base_sha=BASE,
            expected_source_sha=SOURCE,
        )

    path.write_bytes(b"x" * (MAX_STATUS_BYTES + 1))
    path.chmod(0o600)
    with pytest.raises(PreExecutionStatusError, match="metadata"):
        read_pre_execution_status(
            path,
            expected_diff_base_sha=BASE,
            expected_source_sha=SOURCE,
        )

    path.write_text(json.dumps(valid), encoding="utf-8")
    path.chmod(0o644)
    with pytest.raises(PreExecutionStatusError, match="metadata"):
        read_pre_execution_status(
            path,
            expected_diff_base_sha=BASE,
            expected_source_sha=SOURCE,
        )

    target = tmp_path / "target"
    target.write_text("preserve", encoding="utf-8")
    path.unlink()
    path.symlink_to(target)
    with pytest.raises(PreExecutionStatusError, match="metadata"):
        read_pre_execution_status(
            path,
            expected_diff_base_sha=BASE,
            expected_source_sha=SOURCE,
        )
    with pytest.raises(PreExecutionStatusError, match="existing"):
        write_pre_execution_status(path, status())
    assert target.read_text(encoding="utf-8") == "preserve"

    path.unlink()
    path.write_text(json.dumps(valid), encoding="utf-8")
    path.chmod(0o600)
    hardlink = directory / "hardlink"
    os.link(path, hardlink)
    with pytest.raises(PreExecutionStatusError, match="metadata"):
        read_pre_execution_status(
            path,
            expected_diff_base_sha=BASE,
            expected_source_sha=SOURCE,
        )


@pytest.mark.parametrize(
    ("reason", "actual", "limit", "unit"),
    [
        (BACKGROUND_CHARACTER_LIMIT_REASON, 8_001, 8_000, "characters"),
        (BACKGROUND_FILE_SIZE_LIMIT_REASON, 1_048_577, 1_048_576, "bytes"),
    ],
)
def test_pre_execution_status_round_trips_closed_background_rejection(
    tmp_path: Path, reason: str, actual: int, limit: int, unit: str
) -> None:
    """Persist only installed-OCR numeric facts without its path or raw diagnostic."""

    path = private_directory(tmp_path) / "pre-execution-status.json"
    expected = PreExecutionStatus(
        schema_version=STATUS_SCHEMA,
        reason=reason,
        diff_base_sha=BASE,
        source_sha=SOURCE,
        policy_sha=POLICY,
        review=review_identity(),
        stage=OCR_PREVIEW_STAGE,
        actual=actual,
        limit=limit,
        unit=unit,
    )

    write_pre_execution_status(path, expected)

    assert (
        read_pre_execution_status(
            path,
            expected_diff_base_sha=BASE,
            expected_source_sha=SOURCE,
        )
        == expected
    )
    serialized = path.read_text(encoding="utf-8")
    assert "background.md" not in serialized
    assert "please provide" not in serialized


@pytest.mark.parametrize(
    ("reason", "stage", "policy_sha", "provider", "project_id", "change_id", "count"),
    [
        (
            REVIEWED_REVISION_NO_LONGER_CURRENT,
            EVIDENCE_PREFLIGHT_STAGE,
            None,
            "gitlab",
            "17",
            "23",
            None,
        ),
        (
            UNCLASSIFIED_PREVIEW_DIAGNOSTICS,
            OCR_PREVIEW_STAGE,
            POLICY,
            None,
            None,
            None,
            2,
        ),
    ],
)
def test_pre_execution_status_round_trips_typed_pre_model_failures(
    tmp_path: Path,
    reason: str,
    stage: str,
    policy_sha: str | None,
    provider: str | None,
    project_id: str | None,
    change_id: str | None,
    count: int | None,
) -> None:
    path = private_directory(tmp_path) / "pre-execution-status.json"
    expected = PreExecutionStatus(
        schema_version=STATUS_SCHEMA,
        reason=reason,
        diff_base_sha=BASE,
        source_sha=SOURCE,
        policy_sha=policy_sha,
        review=review_identity() if reason == UNCLASSIFIED_PREVIEW_DIAGNOSTICS else None,
        stage=stage,
        model_execution=MODEL_NOT_STARTED,
        diagnostic_count=count,
        provider=provider,
        project_id=project_id,
        change_id=change_id,
    )
    write_pre_execution_status(path, expected)
    assert (
        read_pre_execution_status(path, expected_diff_base_sha=BASE, expected_source_sha=SOURCE)
        == expected
    )

    serialized = path.read_text(encoding="utf-8")
    assert "private.example.invalid" not in serialized
    assert '"model_execution":"not_started"' in serialized


@pytest.mark.parametrize(
    "reason",
    [PROTECTED_TARGET_RULE_PATH_PENDING, PROTECTED_POLICY_RULE_PATH_PENDING],
)
def test_setup_status_distinguishes_policy_authority(tmp_path: Path, reason: str) -> None:
    path = private_directory(tmp_path) / "pre-execution-status.json"
    expected = PreExecutionStatus(
        schema_version=STATUS_SCHEMA,
        reason=reason,
        diff_base_sha=BASE,
        source_sha=SOURCE,
        policy_sha=POLICY,
        review=review_identity(),
    )
    write_pre_execution_status(path, expected)
    assert (
        read_pre_execution_status(path, expected_diff_base_sha=BASE, expected_source_sha=SOURCE)
        == expected
    )


def test_unavailable_review_identity_is_closed_and_job_scoped(tmp_path: Path) -> None:
    path = private_directory(tmp_path) / "pre-execution-status.json"
    expected = PreExecutionStatus(
        schema_version=STATUS_SCHEMA,
        reason=REVIEW_IDENTITY_UNAVAILABLE,
        diff_base_sha=BASE,
        source_sha=SOURCE,
        policy_sha=None,
    )
    write_pre_execution_status(path, expected)
    assert pre_execution_review_identity(expected) is None
    assert (
        read_pre_execution_status(path, expected_diff_base_sha=BASE, expected_source_sha=SOURCE)
        == expected
    )
    for mutation in (
        {"stage": OCR_PREVIEW_STAGE},
        {"policy_sha": POLICY},
        {"provider": "gitlab"},
        {"project_id": "17"},
        {"diagnostic_count": 1},
        {"reason": "untrusted details"},
        {"review": review_identity()},
    ):
        path.write_text(json.dumps({**asdict(expected), **mutation}), encoding="utf-8")
        path.chmod(0o600)
        with pytest.raises(PreExecutionStatusError, match=r"fields|review identity"):
            read_pre_execution_status(path, expected_diff_base_sha=BASE, expected_source_sha=SOURCE)


@pytest.mark.parametrize(
    "mutation",
    [
        {"review": None},
        {"review": {**review_identity(), "target_branch": "release"}},
        {"review": {**review_identity(), "target_sha": "d" * 40}},
        {"review": {**review_identity(), "diff_base_sha": "d" * 40}},
        {"review": {**review_identity(), "project_id": "17"}},
        {"review": {**review_identity(), "policy_sha": "d" * 40}},
        {"review": {**review_identity(), "unexpected": "field"}},
    ],
)
def test_note_status_rejects_missing_or_malformed_review_tuple(
    tmp_path: Path, mutation: dict[str, object]
) -> None:
    path = private_directory(tmp_path) / "pre-execution-status.json"
    write_pre_execution_status(path, status())
    payload = {**json.loads(path.read_text(encoding="utf-8")), **mutation}
    path.write_text(json.dumps(payload), encoding="utf-8")
    path.chmod(0o600)
    with pytest.raises(PreExecutionStatusError, match="review identity"):
        read_pre_execution_status(path, expected_diff_base_sha=BASE, expected_source_sha=SOURCE)


@pytest.mark.parametrize(
    ("reason", "mutations"),
    [
        (
            REVIEWED_REVISION_NO_LONGER_CURRENT,
            [
                {"stage": OCR_PREVIEW_STAGE},
                {"policy_sha": POLICY},
                {"provider": None},
                {"project_id": "017"},
                {"terminal_state": "closed"},
                {"model_execution": "unknown"},
            ],
        ),
        (
            UNCLASSIFIED_PREVIEW_DIAGNOSTICS,
            [
                {"stage": EVIDENCE_PREFLIGHT_STAGE},
                {"diagnostic_count": 0},
                {"diagnostic_count": 1_025},
                {"diagnostic_count": True},
                {"diagnostic_count": None},
                {"actual": 2},
                {"provider": "gitlab"},
            ],
        ),
    ],
)
def test_pre_execution_status_rejects_invalid_typed_failure_tuple(
    tmp_path: Path, reason: str, mutations: list[dict[str, object]]
) -> None:
    path = private_directory(tmp_path) / "pre-execution-status.json"
    base = PreExecutionStatus(
        schema_version=STATUS_SCHEMA,
        reason=reason,
        diff_base_sha=BASE,
        source_sha=SOURCE,
        policy_sha=None if reason == REVIEWED_REVISION_NO_LONGER_CURRENT else POLICY,
        review=review_identity() if reason == UNCLASSIFIED_PREVIEW_DIAGNOSTICS else None,
        stage=EVIDENCE_PREFLIGHT_STAGE
        if reason == REVIEWED_REVISION_NO_LONGER_CURRENT
        else OCR_PREVIEW_STAGE,
        diagnostic_count=None if reason == REVIEWED_REVISION_NO_LONGER_CURRENT else 1,
        provider="gitlab" if reason == REVIEWED_REVISION_NO_LONGER_CURRENT else None,
        project_id="17" if reason == REVIEWED_REVISION_NO_LONGER_CURRENT else None,
        change_id="23" if reason == REVIEWED_REVISION_NO_LONGER_CURRENT else None,
    )
    for mutation in mutations:
        payload = {**asdict(base), **mutation}
        path.write_text(json.dumps(payload), encoding="utf-8")
        path.chmod(0o600)
        with pytest.raises(PreExecutionStatusError, match="fields"):
            read_pre_execution_status(path, expected_diff_base_sha=BASE, expected_source_sha=SOURCE)


@pytest.mark.parametrize("terminal_state", ["merged", "closed"])
def test_pre_execution_status_round_trips_identity_bound_terminal_mr(
    tmp_path: Path, terminal_state: str
) -> None:
    path = private_directory(tmp_path) / "pre-execution-status.json"
    expected = PreExecutionStatus(
        schema_version=STATUS_SCHEMA,
        reason=GITLAB_MERGE_REQUEST_TERMINAL,
        diff_base_sha=BASE,
        source_sha=SOURCE,
        policy_sha=None,
        provider="gitlab",
        project_id="17",
        change_id="23",
        terminal_state=terminal_state,
    )

    write_pre_execution_status(path, expected)

    assert (
        read_pre_execution_status(
            path,
            expected_diff_base_sha=BASE,
            expected_source_sha=SOURCE,
        )
        == expected
    )
    assert '"policy_sha":null' in path.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("provider", "github"),
        ("project_id", "../17"),
        ("project_id", "017"),
        ("project_id", "0"),
        ("change_id", True),
        ("terminal_state", "locked"),
        ("policy_sha", POLICY),
    ],
)
def test_pre_execution_status_rejects_hostile_terminal_identity(
    tmp_path: Path, field: str, value: object
) -> None:
    path = private_directory(tmp_path) / "pre-execution-status.json"
    payload = {
        "schema_version": STATUS_SCHEMA,
        "reason": GITLAB_MERGE_REQUEST_TERMINAL,
        "diff_base_sha": BASE,
        "source_sha": SOURCE,
        "policy_sha": None,
        "review": None,
        "stage": EVIDENCE_PREFLIGHT_STAGE,
        "model_execution": MODEL_NOT_STARTED,
        "diagnostic_count": None,
        "actual": None,
        "limit": None,
        "unit": None,
        "provider": "gitlab",
        "project_id": "17",
        "change_id": "23",
        "terminal_state": "merged",
    }
    payload[field] = value
    path.write_text(json.dumps(payload), encoding="utf-8")
    path.chmod(0o600)

    with pytest.raises(PreExecutionStatusError, match="fields"):
        read_pre_execution_status(
            path,
            expected_diff_base_sha=BASE,
            expected_source_sha=SOURCE,
        )
