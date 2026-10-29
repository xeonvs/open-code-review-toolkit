"""Optional collector status cannot change evidence authority or wire limits."""

import json
from pathlib import Path

import pytest

from ocr_toolkit.diagrams.collector import DiagramCollector
from ocr_toolkit.evidence import mcp
from ocr_toolkit.evidence.actions import read_action_receipt
from tests.diagrams.support import REVIEW_RANGE, flow_submission, sequence_submission
from tests.test_evidence_mcp import _store


@pytest.fixture
def collector(tmp_path: Path) -> DiagramCollector:
    directory = tmp_path / "private"
    directory.mkdir(mode=0o700)
    result = DiagramCollector(directory / "diagram.json", "c" * 32, REVIEW_RANGE)
    result.initialize()
    return result


def request(request_id=1):
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "tools/call",
        "params": {"name": mcp.TOOL_NAME, "arguments": {"action": "summary"}},
    }


def summary(collector, **kwargs):
    response = mcp.handle_request(_store(), request(), diagram_collector=collector, **kwargs)
    assert "error" not in response
    return json.loads(response["result"]["content"][0]["text"])


def test_status_tracks_collection_without_exposing_candidate_or_consuming_submissions(collector):
    before = mcp.evidence_summary(_store())
    pending = summary(collector)
    assert pending.pop("diagram_output") == {"state": "pending"}
    assert pending == before and collector.read().submissions == 0
    collector.submit(flow_submission())
    received = summary(collector)
    assert received.pop("diagram_output") == {"state": "received"}
    assert received == before and collector.read().submissions == 1
    collector.submit(sequence_submission())
    conflict = summary(collector)
    assert conflict.pop("diagram_output") == {"state": "omitted-invalid"}
    assert conflict == before and collector.read().reason == "conflict"


@pytest.mark.parametrize("failure", ("missing", "directory", "invalid", "symlink", "hardlink"))
def test_failed_status_read_preserves_evidence(collector, tmp_path, failure):
    collector.path.unlink()
    secret = tmp_path / "operator-secret"
    secret.write_text("SYNTHETIC_NEVER_CAPTURE_FROM_STATUS")
    if failure == "directory":
        collector.path.mkdir(mode=0o700)
    elif failure == "invalid":
        collector.path.write_text("invalid JSON")
        collector.path.chmod(0o600)
    elif failure == "symlink":
        collector.path.symlink_to(secret)
    elif failure == "hardlink":
        collector.path.hardlink_to(secret)
    receipt = tmp_path / "actions.json"
    actual = summary(collector, action_receipt_path=receipt)
    assert actual.pop("diagram_output") == {"state": "unavailable"}
    assert actual == mcp.evidence_summary(_store())
    assert read_action_receipt(receipt)["completed"]["summary"] == 1


def test_status_construction_error_preserves_original_summary(monkeypatch):
    def fail(*_args):
        raise RuntimeError("synthetic optional status failure")

    baseline = mcp.handle_request(_store(), request())
    monkeypatch.setattr(mcp, "diagram_status", fail)
    assert mcp.handle_request(_store(), request(), diagram_output_enabled=True) == baseline


def test_optional_status_cannot_overflow_an_otherwise_valid_wire_response(collector):
    baseline = mcp.handle_request(_store(), request(""))
    overhead = len(json.dumps(baseline, separators=(",", ":"), ensure_ascii=False).encode())
    request_id = "x" * (mcp.MAX_RESPONSE_BYTES - overhead - 8)
    ordinary = mcp.handle_request(_store(), request(request_id))
    actual = mcp.handle_request(_store(), request(request_id), diagram_collector=collector)
    assert actual == ordinary
    assert (
        len(json.dumps(actual, separators=(",", ":"), ensure_ascii=False).encode())
        <= mcp.MAX_RESPONSE_BYTES
    )
    assert collector.read().submissions == 0
