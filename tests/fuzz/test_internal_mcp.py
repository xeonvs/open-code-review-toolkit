"""Hostile JSON-RPC and tool arguments must keep the internal evidence peer usable."""

import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from hypothesis import given
from hypothesis import strategies as st

from ocr_toolkit.evidence.mcp import MAX_REQUEST_BYTES, MAX_RESPONSE_BYTES, handle_request, serve
from tests.fuzz.strategies import json_values
from tests.test_evidence_mcp import _store


@given(
    st.sampled_from(("ping", "initialize", "tools/list", "tools/call", "unknown")),
    json_values(),
    json_values(),
)
def test_request_variations_produce_bounded_utf8_json_responses(method, request_id, params) -> None:
    response = handle_request(
        _store(), {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
    )
    assert response is not None
    wire = json.dumps(response, ensure_ascii=False, allow_nan=False).encode()
    assert len(wire) <= 64_000 and json.loads(wire) == response


@given(
    st.sampled_from(
        ("ocr_toolkit_evidence", "ocr_toolkit_evidence_search", "ocr_toolkit_evidence_coverage")
    ),
    json_values(),
)
def test_nested_tool_arguments_never_break_later_evidence_summary(name, arguments) -> None:
    store = _store()
    response = handle_request(
        store,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        },
    )
    assert response is not None and json.dumps(response, ensure_ascii=False).encode()
    summary = handle_request(
        store,
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "ocr_toolkit_evidence", "arguments": {"action": "summary"}},
        },
    )
    assert summary["result"].get("isError") is not True


@given(
    st.sampled_from(
        (
            0,
            1,
            MAX_REQUEST_BYTES - 100,
            MAX_REQUEST_BYTES - 80,
            MAX_REQUEST_BYTES - 40,
            MAX_REQUEST_BYTES,
            MAX_REQUEST_BYTES + 1,
        )
    ),
    st.sampled_from(("x", "é", "😀")),
    st.sampled_from(("ping", "unknown", "tools/list")),
)
def test_wire_and_response_byte_limits_hold_with_large_multibyte_correlation_ids(
    count, character, method
) -> None:
    request = {"jsonrpc": "2.0", "id": character * count, "method": method}
    ping = {"jsonrpc": "2.0", "id": 2, "method": "ping"}
    incoming = io.StringIO(json.dumps(request, ensure_ascii=False) + "\n" + json.dumps(ping) + "\n")
    outgoing = io.StringIO()
    with TemporaryDirectory(prefix="ocr-mcp-frame-") as directory:
        target = Path(directory) / "evidence.json"
        _store().write(target)
        assert serve(target, incoming, outgoing) == 0
    lines = outgoing.getvalue().splitlines()
    assert len(lines) == 2 and all(len(line.encode()) <= MAX_RESPONSE_BYTES for line in lines)
    assert json.loads(lines[1])["id"] == 2 and json.loads(lines[1])["result"] == {}
