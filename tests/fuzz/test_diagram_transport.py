"""Every bounded JSON output call is accounted for, including malformed Unicode."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from hypothesis import given
from hypothesis import strategies as st

from ocr_toolkit.diagrams.collector import DiagramCollector
from ocr_toolkit.diagrams.mcp import DIAGRAM_TOOL_NAME
from ocr_toolkit.evidence.mcp import handle_request
from tests.diagrams.support import REVIEW_RANGE, flow_submission, sequence_submission
from tests.fuzz.strategies import json_values
from tests.test_evidence_mcp import _store


@given(st.one_of(json_values(), st.just(flow_submission()), st.just(sequence_submission())))
def test_all_wire_representations_count_even_when_the_candidate_is_invalid(
    arguments: object,
) -> None:
    with TemporaryDirectory(prefix="ocr-diagram-property-") as directory:
        collector = DiagramCollector(
            Path(directory).resolve() / "diagram.json", "c" * 32, REVIEW_RANGE
        )
        collector.initialize()
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": DIAGRAM_TOOL_NAME, "arguments": arguments},
        }
        wire = json.dumps(request, ensure_ascii=True).encode("utf-8")
        response = handle_request(
            _store(), request, diagram_collector=collector, request_bytes=len(wire)
        )
        assert response is not None and "error" not in response
        assert response["result"].get("isError") is not True
        snapshot = collector.read()
        assert snapshot.submissions == 1 and snapshot.input_bytes == len(wire)
