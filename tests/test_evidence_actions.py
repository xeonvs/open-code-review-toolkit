"""Security and lifecycle tests for count-only evidence action receipts."""

from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest

from ocr_toolkit.evidence.actions import read_action_receipt, record_action


def test_action_receipt_is_closed_atomic_private_and_count_only(tmp_path: Path) -> None:
    path = tmp_path / "actions.json"
    for action in ("summary", "list", "get", "list"):
        record_action(path, action)

    assert read_action_receipt(path) == {"summary": 1, "list": 2, "get": 1}
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    raw = path.read_text(encoding="utf-8")
    assert set(json.loads(raw)) == {"schema_version", "actions"}
    assert "arguments" not in raw and "record" not in raw and "path" not in raw


@pytest.mark.parametrize(
    "content",
    [
        "not-json",
        json.dumps({"schema_version": "ocr.evidence-action-receipt/v1", "actions": {}}),
        json.dumps(
            {
                "schema_version": "ocr.evidence-action-receipt/v1",
                "actions": {"summary": 1, "list": True, "get": 0},
            }
        ),
    ],
)
def test_hostile_action_receipt_is_unavailable_and_never_overwritten(
    tmp_path: Path, content: str
) -> None:
    path = tmp_path / "actions.json"
    path.write_text(content, encoding="utf-8")
    assert read_action_receipt(path) is None
    with pytest.raises(ValueError, match="malformed"):
        record_action(path, "summary")
    assert path.read_text(encoding="utf-8") == content


def test_unknown_action_is_rejected_without_creating_receipt(tmp_path: Path) -> None:
    path = tmp_path / "actions.json"
    with pytest.raises(ValueError, match="closed"):
        record_action(path, "search")
    assert not path.exists()
