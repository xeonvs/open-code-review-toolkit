"""Current range/diagram receipts and explicit historical schema isolation."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

from ocr_toolkit.diagrams.contracts import DiagramResult, parse_submission
from ocr_toolkit.diagrams.mcp import DIAGRAM_TOOL_NAME
from ocr_toolkit.diagrams.persistence import diagram_payload
from ocr_toolkit.posting.approval import evaluate_approval_policy
from ocr_toolkit.posting.settings import BooleanSetting
from ocr_toolkit.review_range import ReviewRange, range_payload
from ocr_toolkit.review_receipt import (
    automatic_approval_metadata_reason,
    receipt_review_identity,
    toolkit_receipt_is_valid,
)
from tests.diagrams.support import flow_submission, sequence_submission
from tests.test_review_receipt_v11 import _clean_outcome, _receipt_v11

CURRENT_RANGE = ReviewRange("c" * 40, "a" * 40)

RECEIPT_ENUM_PATHS = (
    ("context", "mode"),
    ("context", "state"),
    ("context", "per_source", "forge_ci"),
    ("mcp", "capabilities", 0, "transport"),
    ("tool_execution", "state"),
)


def _receipt_v13(
    *, verified: bool = True, diagram: DiagramResult | None = None, **kwargs: Any
) -> dict[str, Any]:
    """Build a current fixture while keeping the frozen v11 fixture unchanged."""

    receipt = _receipt_v11(**kwargs)
    diagram = diagram or DiagramResult("off", "disabled")
    receipt.update(
        schema_version=13,
        range=range_payload(CURRENT_RANGE if verified else None),
        diagram=diagram_payload(diagram),
    )
    if diagram.state not in {"disabled", "unsupported"}:
        receipt["mcp"]["capabilities"][0]["tools"].append(DIAGRAM_TOOL_NAME)
        receipt["mcp"]["usage"]["ocr_toolkit_evidence"] += diagram.calls
    if diagram.failed_calls:
        receipt["tool_execution"] = {"state": "verified", "failed": diagram.failed_calls}
    return receipt


def generated_diagram(*, sequence: bool = False, mode="on") -> DiagramResult:
    payload = sequence_submission() if sequence else flow_submission()
    payload.update(base_sha=CURRENT_RANGE.base, head_sha=CURRENT_RANGE.head)
    return DiagramResult(
        mode,
        "generated",
        submission=parse_submission(payload, expected_range=CURRENT_RANGE),
        calls=1,
    )


@pytest.mark.parametrize("path", RECEIPT_ENUM_PATHS)
@pytest.mark.parametrize("value", ([], {}))
def test_non_string_receipt_enums_are_invalid_without_incidental_type_errors(path, value):
    receipt = _receipt_v13()
    parent = receipt
    for part in path[:-1]:
        parent = parent[part]
    parent[path[-1]] = value
    assert not toolkit_receipt_is_valid(receipt)


@pytest.mark.parametrize(
    "diagram",
    (
        DiagramResult("off", "disabled"),
        DiagramResult("on", "unsupported"),
        DiagramResult("on", "not-generated"),
        DiagramResult("spoiler", "not-applicable", calls=1),
        DiagramResult("on", "omitted-invalid", "invalid", calls=1),
        DiagramResult("on", "omitted-invalid", "unavailable", calls=0),
        DiagramResult("on", "omitted-invalid", "unavailable", calls=1, failed_calls=1),
        generated_diagram(),
        generated_diagram(sequence=True, mode="spoiler"),
    ),
)
def test_every_optional_state_and_output_tool_failure_preserves_clean_approval(
    diagram: DiagramResult,
) -> None:
    receipt = _receipt_v13(diagram=diagram)
    assert toolkit_receipt_is_valid(receipt)
    assert automatic_approval_metadata_reason(receipt) == ""
    assert evaluate_approval_policy(
        BooleanSetting(True), _clean_outcome(), [], [], 0, receipt
    ).eligible


def test_optional_output_failure_does_not_hide_a_failed_evidence_read() -> None:
    diagram = DiagramResult("on", "omitted-invalid", "unavailable", calls=1, failed_calls=1)
    receipt = _receipt_v13(diagram=diagram)
    receipt["tool_execution"]["failed"] = 2
    assert toolkit_receipt_is_valid(receipt)
    assert automatic_approval_metadata_reason(receipt) == "one or more OCR tool calls failed"
    receipt["tool_execution"]["failed"] = 0
    assert not toolkit_receipt_is_valid(receipt)


def test_integrity_checks_precede_a_valid_unprotected_approval_blocker() -> None:
    diagram = DiagramResult("on", "omitted-invalid", "unavailable", calls=1, failed_calls=1)
    receipt = _receipt_v13(diagram=diagram, target_protection="unprotected")
    assert toolkit_receipt_is_valid(receipt)
    receipt["tool_execution"]["failed"] = 0
    assert not toolkit_receipt_is_valid(receipt)


def test_unverified_legacy_range_is_explicit_and_comment_only() -> None:
    receipt = _receipt_v13(verified=False)
    assert toolkit_receipt_is_valid(receipt)
    assert receipt_review_identity(receipt).schema_version == 13
    assert (
        automatic_approval_metadata_reason(receipt)
        == "native review range identity was not verified"
    )


@pytest.mark.parametrize(
    "field,value",
    (
        ("mode", "local"),
        ("mode", []),
        ("state", "unknown"),
        ("state", "disabled"),
        ("reason", "model reason"),
        ("calls", True),
        ("calls", 0),
        ("calls", 9),
        ("failed_calls", True),
        ("failed_calls", 2),
        ("submission", None),
    ),
)
def test_hostile_current_diagram_receipt_is_rejected_atomically(field: str, value: object) -> None:
    receipt = _receipt_v13(diagram=generated_diagram())
    receipt["diagram"][field] = value
    assert not toolkit_receipt_is_valid(receipt)


def test_new_fields_cannot_be_smuggled_into_frozen_historical_receipts() -> None:
    old = _receipt_v11()
    assert toolkit_receipt_is_valid(old)
    for field in ("range", "diagram"):
        corrupted = deepcopy(old)
        corrupted[field] = _receipt_v13()[field]
        assert not toolkit_receipt_is_valid(corrupted)
    current = _receipt_v13()
    current["schema_version"] = 11
    assert not toolkit_receipt_is_valid(current)


def test_current_identity_requires_matching_exact_range_and_canonical_candidate() -> None:
    receipt = _receipt_v13(diagram=generated_diagram())
    for field in ("base_sha", "head_sha", "exact_range"):
        corrupted = deepcopy(receipt)
        corrupted["range"][field] = "e" * 40
        assert not toolkit_receipt_is_valid(corrupted)
    receipt["diagram"]["submission"]["diagram"]["nodes"][0]["label"] += " "
    assert not toolkit_receipt_is_valid(receipt)


def test_unavailable_registration_can_omit_the_capability_but_cannot_hide_calls() -> None:
    receipt = _receipt_v13(diagram=DiagramResult("on", "omitted-invalid", "unavailable"))
    receipt["mcp"]["capabilities"][0]["tools"].remove(DIAGRAM_TOOL_NAME)
    assert toolkit_receipt_is_valid(receipt)
    receipt["diagram"]["calls"] = 1
    assert not toolkit_receipt_is_valid(receipt)


def test_v14_partial_receipt_requires_native_range_proof_and_preserves_v12_readback() -> None:
    from tests.test_repository_coverage import _coverage

    current = _receipt_v13()
    current.update(schema_version=14, repository_coverage=_coverage())
    assert toolkit_receipt_is_valid(current)
    assert "submodule pointers were not reviewed" in automatic_approval_metadata_reason(current)
    current["range"] = range_payload(None)
    assert not toolkit_receipt_is_valid(current)
    old = _receipt_v11()
    old.update(schema_version=12, repository_coverage=_coverage())
    assert toolkit_receipt_is_valid(old)
