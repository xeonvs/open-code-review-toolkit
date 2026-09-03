"""Security and lifecycle tests for count-only evidence action receipts."""

from __future__ import annotations

import json
import os
import stat
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pytest

from ocr_toolkit.evidence.actions import MAX_ACTION_CALLS, read_action_receipt, record_action


def _valid_receipt_payload() -> dict[str, object]:
    return {
        "schema_version": "ocr.evidence-action-receipt/v3",
        "actions": {
            "attempted": {
                "summary": 1,
                "list": 0,
                "get": 0,
                "search": 0,
                "coverage": 0,
                "unattributed": 0,
            },
            "completed": {
                "summary": 1,
                "list": 0,
                "get": 0,
                "search": 0,
                "coverage": 0,
            },
        },
    }


def _record_repeated_actions(path: str, action: str, count: int) -> None:
    """Exercise the production lock from an independent worker process."""

    for _ in range(count):
        record_action(Path(path), action)
        record_action(Path(path), action, completed=True)


def test_action_receipt_is_closed_atomic_private_and_count_only(tmp_path: Path) -> None:
    path = tmp_path / "actions.json"
    for action in ("summary", "list", "get", "search", "coverage", "list"):
        record_action(path, action)
        record_action(path, action, completed=True)

    assert read_action_receipt(path) == {
        "attempted": {
            "summary": 1,
            "list": 2,
            "get": 1,
            "search": 1,
            "coverage": 1,
            "unattributed": 0,
        },
        "completed": {"summary": 1, "list": 2, "get": 1, "search": 1, "coverage": 1},
    }
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    raw = path.read_text(encoding="utf-8")
    assert set(json.loads(raw)) == {"schema_version", "actions"}
    assert "arguments" not in raw and "record" not in raw and "path" not in raw


@pytest.mark.parametrize(
    "content",
    [
        "not-json",
        json.dumps(
            {
                "schema_version": "ocr.evidence-action-receipt/v1",
                "actions": {"summary": 1, "list": 0, "get": 0},
            }
        ),
        json.dumps({"schema_version": "ocr.evidence-action-receipt/v2", "actions": {}}),
        json.dumps(
            {
                "schema_version": "ocr.evidence-action-receipt/v3",
                "actions": {
                    "attempted": {
                        "summary": 1,
                        "list": True,
                        "get": 0,
                        "search": 0,
                        "coverage": 0,
                        "unattributed": 0,
                    },
                    "completed": {
                        "summary": 1,
                        "list": 0,
                        "get": 0,
                        "search": 0,
                        "coverage": 0,
                    },
                },
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


@pytest.mark.parametrize(
    ("section", "key", "value"),
    [
        ("attempted", "unattributed", True),
        ("attempted", "search", MAX_ACTION_CALLS + 1),
        ("completed", "summary", 2),
        ("completed", "coverage", -1),
    ],
)
def test_action_receipt_rejects_type_bounds_and_completion_without_attempt(
    tmp_path: Path, section: str, key: str, value: object
) -> None:
    payload = _valid_receipt_payload()
    actions = payload["actions"]
    assert isinstance(actions, dict)
    counts = actions[section]
    assert isinstance(counts, dict)
    counts[key] = value
    path = tmp_path / "actions.json"
    raw = json.dumps(payload)
    path.write_text(raw, encoding="utf-8")

    assert read_action_receipt(path) is None
    with pytest.raises(ValueError, match="malformed"):
        record_action(path, "summary")
    assert path.read_text(encoding="utf-8") == raw


@pytest.mark.parametrize(
    ("section", "key"),
    [
        ("attempted", "unattributed"),
        ("completed", "coverage"),
    ],
)
def test_action_receipt_rejects_missing_or_extra_closed_keys(
    tmp_path: Path, section: str, key: str
) -> None:
    payload = _valid_receipt_payload()
    actions = payload["actions"]
    assert isinstance(actions, dict)
    counts = actions[section]
    assert isinstance(counts, dict)
    counts.pop(key)
    counts["unexpected"] = 0
    path = tmp_path / "actions.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    assert read_action_receipt(path) is None


def test_unknown_action_is_rejected_without_creating_receipt(tmp_path: Path) -> None:
    path = tmp_path / "actions.json"
    with pytest.raises(ValueError, match="closed"):
        record_action(path, "delete")
    assert not path.exists()


def test_action_receipt_serializes_concurrent_completed_calls(tmp_path: Path) -> None:
    path = tmp_path / "actions.json"
    work = [
        (str(path), action, 20)
        for action in ("summary", "list", "get", "search", "coverage")
        for _ in range(4)
    ]

    with ProcessPoolExecutor(max_workers=12) as executor:
        futures = [executor.submit(_record_repeated_actions, *item) for item in work]
        for future in futures:
            future.result()

    assert read_action_receipt(path) == {
        "attempted": {
            "summary": 80,
            "list": 80,
            "get": 80,
            "search": 80,
            "coverage": 80,
            "unattributed": 0,
        },
        "completed": {
            "summary": 80,
            "list": 80,
            "get": 80,
            "search": 80,
            "coverage": 80,
        },
    }
    lock_path = path.with_name(f".{path.name}.lock")
    assert stat.S_IMODE(lock_path.stat().st_mode) == 0o600


@pytest.mark.parametrize("unsafe", ["symlink", "hardlink"])
def test_action_receipt_rejects_unsafe_lock_file(tmp_path: Path, unsafe: str) -> None:
    path = tmp_path / "actions.json"
    lock_path = path.with_name(f".{path.name}.lock")
    target = tmp_path / "outside"
    target.write_text("sentinel", encoding="utf-8")
    if unsafe == "symlink":
        lock_path.symlink_to(target)
    else:
        lock_path.hardlink_to(target)

    with pytest.raises(OSError, match=r"unsafe|symbolic link"):
        record_action(path, "summary")

    assert not path.exists()
    assert target.read_text(encoding="utf-8") == "sentinel"


@pytest.mark.parametrize("unsafe", ["symlink", "hardlink", "fifo", "permissions"])
def test_action_receipt_rejects_unsafe_existing_file(tmp_path: Path, unsafe: str) -> None:
    path = tmp_path / "actions.json"
    target = tmp_path / "outside"
    payload = json.dumps(
        {
            "schema_version": "ocr.evidence-action-receipt/v3",
            "actions": {
                "attempted": {
                    "summary": 1,
                    "list": 0,
                    "get": 0,
                    "search": 0,
                    "coverage": 0,
                    "unattributed": 0,
                },
                "completed": {
                    "summary": 1,
                    "list": 0,
                    "get": 0,
                    "search": 0,
                    "coverage": 0,
                },
            },
        }
    )
    target.write_text(payload, encoding="utf-8")
    if unsafe == "symlink":
        path.symlink_to(target)
    elif unsafe == "hardlink":
        path.hardlink_to(target)
    elif unsafe == "fifo":
        path.unlink(missing_ok=True)
        os.mkfifo(path)
    else:
        path.write_text(payload, encoding="utf-8")
        path.chmod(0o644)

    assert read_action_receipt(path) is None
    with pytest.raises(ValueError, match="malformed"):
        record_action(path, "summary")

    assert target.read_text(encoding="utf-8") == payload


def test_completed_action_requires_a_prior_authenticated_attempt(tmp_path: Path) -> None:
    path = tmp_path / "actions.json"

    with pytest.raises(ValueError, match="authenticated attempt"):
        record_action(path, "summary", completed=True)

    assert not path.exists()


def test_failed_attempt_is_preserved_without_becoming_completed(tmp_path: Path) -> None:
    path = tmp_path / "actions.json"
    record_action(path, "unattributed")
    record_action(path, "get")

    receipt = read_action_receipt(path)
    assert receipt is not None
    assert receipt["attempted"]["unattributed"] == 1
    assert receipt["attempted"]["get"] == 1
    assert sum(receipt["completed"].values()) == 0
