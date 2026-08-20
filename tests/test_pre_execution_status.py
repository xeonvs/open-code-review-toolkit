"""Hostile persistence tests for the closed pre-execution outcome."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from ocr_toolkit.pre_execution import (
    MAX_STATUS_BYTES,
    PROTECTED_TARGET_RULE_PATH_PENDING,
    STATUS_SCHEMA,
    PreExecutionStatus,
    PreExecutionStatusError,
    read_pre_execution_status,
    write_pre_execution_status,
)

BASE = "a" * 40
SOURCE = "b" * 40
POLICY = "c" * 40


def status() -> PreExecutionStatus:
    return PreExecutionStatus(
        schema_version=STATUS_SCHEMA,
        reason=PROTECTED_TARGET_RULE_PATH_PENDING,
        diff_base_sha=BASE,
        source_sha=SOURCE,
        policy_sha=POLICY,
    )


def private_directory(tmp_path: Path) -> Path:
    directory = tmp_path / ".review-context"
    directory.mkdir(mode=0o700)
    return directory


def test_pre_execution_status_atomic_round_trip_and_identity_binding(tmp_path: Path) -> None:
    path = private_directory(tmp_path) / "pre-execution-status.json"

    write_pre_execution_status(path, status())

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
    }

    variants = (
        {**valid, "schema_version": "ocr.pre-execution-status/v2"},
        {**valid, "reason": "repository supplied display text"},
        {**valid, "path": ".opencodereview/rules.json"},
        {**valid, "policy_sha": True},
        {**valid, "policy_sha": "0" * 40},
    )
    for payload in variants:
        path.write_text(json.dumps(payload), encoding="utf-8")
        path.chmod(0o600)
        with pytest.raises(PreExecutionStatusError, match="fields"):
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
