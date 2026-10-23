"""Exact v11 policy-authority receipt and historical compatibility tests."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

from ocr_toolkit.posting.approval import evaluate_approval_policy
from ocr_toolkit.posting.settings import BooleanSetting
from ocr_toolkit.result_contract import ReviewOutcome
from ocr_toolkit.review_receipt import (
    AUTO_UNPROTECTED_APPROVAL_REASON,
    UNPROTECTED_APPROVAL_REASON,
    automatic_approval_metadata_reason,
    receipt_review_identity,
    toolkit_receipt_is_valid,
    validated_review_identity,
)
from tests.support import review_receipt_v8


def _receipt_v11(
    *,
    target_protection: str = "protected",
    protection_mode: str = "auto",
    enriched: bool = False,
    external: bool = False,
) -> dict[str, Any]:
    usage = {"ocr_toolkit_evidence": 2 if enriched else 1}
    if external:
        usage["documentation"] = 1
    receipt = review_receipt_v8(
        usage=usage,
        context_tool_usage={"context_get": 1, "context_list": 0} if enriched else None,
    )
    receipt["schema_version"] = 11
    receipt["publication"] = {"schema": "ocr.publication/v2", "state": "passed"}
    receipt["review"] = {
        "source_sha": "a" * 40,
        "diff_base_sha": "c" * 40,
        "diff_start_sha": "d" * 40,
        "diff_head_sha": "a" * 40,
        "diff_version_id": 7,
        "project_id": "1",
        "merge_request_iid": "2",
        "target_branch": "main" if target_protection == "protected" else "development",
        "target_sha": "b" * 40 if target_protection == "protected" else "e" * 40,
        "target_protection": target_protection,
        "policy_project_id": "1",
        "policy_branch": (
            "main"
            if target_protection == "protected" or protection_mode == "auto"
            else "development"
        ),
        "policy_sha": "b" * 40
        if target_protection == "protected" or protection_mode == "auto"
        else "e" * 40,
        "policy_protection": (
            "protected"
            if target_protection == "protected" or protection_mode == "auto"
            else "unprotected"
        ),
        "protection_mode": protection_mode,
        "mr_author_id": 41,
    }
    if external:
        federation = receipt["mcp"]["federation"]["receipt"]
        federation["schema"] = "ocr.federation/v2"
        for entry in federation["tools"].values():
            entry["dlp_gates"] = {
                gate: {
                    reason: 0 for reason in ("forbidden", "invalid_text", "limit", "pii", "secret")
                }
                for gate in ("arguments", "result")
            }
    return receipt


def _clean_outcome() -> ReviewOutcome:
    return ReviewOutcome(
        status="complete",
        kind="clean",
        budget_exceeded=False,
        manifest_present=True,
        selected_count=1,
        completed_count=1,
    )


@pytest.mark.parametrize("protection_mode", ("auto", "required", "unprotected"))
def test_protected_target_v11_binds_independent_diff_and_policy_identities(
    protection_mode: str,
) -> None:
    receipt = _receipt_v11(protection_mode=protection_mode)
    assert toolkit_receipt_is_valid(receipt)
    identity = validated_review_identity(receipt)
    assert identity is not None
    assert identity.schema_version == 11
    assert identity.source_sha == identity.diff_head_sha == "a" * 40
    assert identity.diff_base_sha == "c" * 40
    assert identity.diff_start_sha == "d" * 40
    assert identity.target_sha == identity.policy_sha == "b" * 40
    assert identity.diff_version_id == 7
    assert identity.project_id == identity.policy_project_id == "1"
    assert identity.target_branch == identity.policy_branch == "main"
    assert identity.protection_mode == protection_mode
    assert evaluate_approval_policy(
        BooleanSetting(True), _clean_outcome(), [], [], 0, receipt
    ).eligible


@pytest.mark.parametrize("job_id", ("0", "01", "", 11, None, "a" * 1000))
def test_v11_review_rejects_malformed_optional_ci_job_identity(job_id: object) -> None:
    receipt = _receipt_v11()
    receipt["review"]["ci_job_id"] = job_id
    assert not toolkit_receipt_is_valid(receipt)


def test_v11_review_preserves_valid_ci_job_identity() -> None:
    receipt = _receipt_v11()
    receipt["review"]["ci_job_id"] = "11"
    identity = validated_review_identity(receipt)
    assert identity is not None
    assert identity.ci_job_id == "11"


def test_auto_fallback_uses_protected_policy_capability_but_never_approves() -> None:
    receipt = _receipt_v11(target_protection="unprotected", enriched=True, external=True)
    assert toolkit_receipt_is_valid(receipt)
    identity = validated_review_identity(receipt)
    assert identity is not None
    assert identity.target_branch == "development"
    assert identity.target_sha == "e" * 40
    assert identity.policy_branch == "main"
    assert identity.policy_sha == "b" * 40
    assert identity.policy_protection == "protected"
    assert automatic_approval_metadata_reason(receipt) == AUTO_UNPROTECTED_APPROVAL_REASON
    decision = evaluate_approval_policy(BooleanSetting(True), _clean_outcome(), [], [], 0, receipt)
    assert decision.eligible is False
    assert decision.result.reason == AUTO_UNPROTECTED_APPROVAL_REASON


def test_explicit_unprotected_v11_remains_limited_and_comment_only() -> None:
    receipt = _receipt_v11(target_protection="unprotected", protection_mode="unprotected")
    assert toolkit_receipt_is_valid(receipt)
    assert automatic_approval_metadata_reason(receipt) == UNPROTECTED_APPROVAL_REASON
    for kwargs in ({"enriched": True}, {"external": True}):
        candidate = _receipt_v11(
            target_protection="unprotected", protection_mode="unprotected", **kwargs
        )
        assert not toolkit_receipt_is_valid(candidate)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("source_sha", "f" * 40),
        ("diff_base_sha", "missing"),
        ("diff_start_sha", "0" * 40),
        ("diff_head_sha", "f" * 40),
        ("diff_version_id", 0),
        ("diff_version_id", True),
        ("diff_version_id", "7"),
        ("project_id", "01"),
        ("merge_request_iid", "0"),
        ("policy_project_id", "3"),
        ("policy_branch", "other"),
        ("policy_sha", "f" * 40),
        ("policy_protection", "unprotected"),
        ("target_branch", "../unsafe"),
        ("target_protection", []),
        ("protection_mode", []),
        ("mr_author_id", True),
    ),
)
def test_v11_rejects_hostile_or_contradictory_protected_review_fields(
    field: str, value: Any
) -> None:
    receipt = _receipt_v11()
    receipt["review"][field] = value
    assert receipt_review_identity(receipt) is None
    assert validated_review_identity(receipt) is None
    assert not toolkit_receipt_is_valid(receipt)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("protection_mode", "required"),
        ("policy_project_id", "3"),
        ("policy_branch", "development"),
        ("policy_protection", "unprotected"),
    ),
)
def test_auto_fallback_rejects_mode_and_policy_authority_substitution(
    field: str, value: Any
) -> None:
    receipt = _receipt_v11(target_protection="unprotected")
    receipt["review"][field] = value
    assert not toolkit_receipt_is_valid(receipt)
    assert validated_review_identity(receipt) is None


def test_v11_review_keys_and_federation_version_are_exact() -> None:
    receipt = _receipt_v11(external=True)
    assert toolkit_receipt_is_valid(receipt)
    inserted = deepcopy(receipt)
    inserted["review"]["untrusted_authority"] = "main"
    assert not toolkit_receipt_is_valid(inserted)
    missing = deepcopy(receipt)
    del missing["review"]["diff_base_sha"]
    assert not toolkit_receipt_is_valid(missing)
    old_federation = deepcopy(receipt)
    old_federation["mcp"]["federation"]["receipt"]["schema"] = "ocr.federation/v1"
    assert not toolkit_receipt_is_valid(old_federation)


@pytest.mark.parametrize("schema_version", (9, 10))
def test_historical_receipts_keep_exact_policy_target_binding(schema_version: int) -> None:
    receipt = review_receipt_v8()
    receipt["schema_version"] = schema_version
    if schema_version == 10:
        receipt["publication"] = {"schema": "ocr.publication/v2", "state": "passed"}
    assert toolkit_receipt_is_valid(receipt)
    identity = validated_review_identity(receipt)
    assert identity is not None
    assert identity.schema_version == schema_version
    assert identity.policy_sha == identity.target_sha
    assert identity.diff_base_sha is None
    assert identity.protection_mode is None

    changed = deepcopy(receipt)
    changed["review"]["policy_sha"] = "f" * 40
    assert not toolkit_receipt_is_valid(changed)
    upgraded = deepcopy(receipt)
    upgraded["review"]["diff_base_sha"] = "c" * 40
    assert not toolkit_receipt_is_valid(upgraded)
