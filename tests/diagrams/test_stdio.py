"""Official SDK and raw stdio peers cross the production isolated MCP server."""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from mcp import Client
from mcp.client.stdio import StdioServerParameters

from ocr_toolkit.diagrams.collector import DiagramCollector
from ocr_toolkit.diagrams.contracts import DiagramError, parse_submission
from ocr_toolkit.diagrams.mcp import DIAGRAM_TOOL_NAME, diagram_tool_definition
from ocr_toolkit.evidence.actions import read_action_receipt
from ocr_toolkit.evidence.artifacts import prepare_artifact_directory, repository_artifacts
from ocr_toolkit.evidence.collect import collect_repository_evidence
from ocr_toolkit.review_range import ReviewRange
from tests.diagrams.support import flow_submission, sequence_submission
from tests.test_evidence_repository import synthetic_repository


def setup(root: Path, base: str, head: str) -> DiagramCollector:
    artifacts = repository_artifacts(root)
    prepare_artifact_directory(artifacts)
    store = collect_repository_evidence(root=root, base_ref=base, head_ref=head, policy_ref=base)
    store.write(artifacts.store)
    collector = DiagramCollector(artifacts.diagram, "c" * 32, ReviewRange(base, head))
    collector.initialize()
    return collector


def bind(payload, review_range: ReviewRange):
    payload.update(base_sha=review_range.base, head_sha=review_range.head)

    def visit(value):
        if isinstance(value, dict):
            if set(value) == {"path", "start_line", "end_line"}:
                value.update(path="changed.txt", start_line=1, end_line=1)
            else:
                for child in value.values():
                    visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(payload)
    return payload


def client(root: Path, collector: DiagramCollector | None) -> Client:
    args = ["-I", "-m", "ocr_toolkit.evidence"]
    if collector is not None:
        args.extend(("--diagram-run-id", collector.run_id))
    return Client(StdioServerParameters(command=sys.executable, args=args, cwd=root), cache=None)


@pytest.mark.parametrize(
    "condition,has_references", [("", False), ("", True), ("supported", False), ("supported", True)]
)
def test_advertised_conditional_reference_contract_matches_parser(condition, has_references):
    payload = flow_submission()
    edge = payload["diagram"]["edges"][0]
    edge["condition"] = condition
    if not has_references:
        edge["references"] = []
    valid = not condition or has_references
    assert Draft202012Validator(diagram_tool_definition()["inputSchema"]).is_valid(payload) == valid
    if valid:
        assert parse_submission(
            payload, expected_range=ReviewRange(payload["base_sha"], payload["head_sha"])
        )
    else:
        with pytest.raises(DiagramError):
            parse_submission(
                payload, expected_range=ReviewRange(payload["base_sha"], payload["head_sha"])
            )


@pytest.mark.parametrize("factory", (flow_submission, sequence_submission))
def test_actual_sdk_output_and_evidence_keep_separate_authority(tmp_path: Path, factory) -> None:
    root, base, head = synthetic_repository(tmp_path)
    collector = setup(root, base, head)
    payload = bind(factory(), collector.review_range)
    definition = diagram_tool_definition()
    Draft202012Validator.check_schema(definition["inputSchema"])
    Draft202012Validator(definition["inputSchema"]).validate(payload)
    metadata_paths = (root / ".git" / "index", root / ".git" / "HEAD", root / "changed.txt")
    before = tuple(path.read_bytes() for path in metadata_paths)
    shadow = root / "ocr_toolkit"
    shadow.mkdir()
    (shadow / "__init__.py").write_text("raise RuntimeError('untrusted shadow imported')\n")

    async def exercise():
        async with asyncio.timeout(15):
            async with client(root, collector) as peer:
                assert peer.protocol_version == "2025-11-25"
                listing = await peer.list_tools()
                assert DIAGRAM_TOOL_NAME in {tool.name for tool in listing.tools}
                pending = await peer.call_tool("ocr_toolkit_evidence", {"action": "summary"})
                assert json.loads(pending.content[0].text)["diagram_output"] == {"state": "pending"}
                response = await peer.call_tool(DIAGRAM_TOOL_NAME, payload)
                assert not response.is_error
                assert json.loads(response.content[0].text) == {"state": "received"}
                summary = await peer.call_tool("ocr_toolkit_evidence", {"action": "summary"})
                assert not summary.is_error
                facts = json.loads(summary.content[0].text)
                assert (facts["base"], facts["head"]) == (base, head)
                assert facts["diagram_output"] == {"state": "received"}
            # OCR starts fresh round conversations; a fresh MCP process sees
            # run-owned collection state without any previous model messages.
            async with client(root, collector) as peer:
                summary = await peer.call_tool("ocr_toolkit_evidence", {"action": "summary"})
                assert json.loads(summary.content[0].text)["diagram_output"] == {
                    "state": "received"
                }

    asyncio.run(exercise())
    assert collector.read().candidate is not None
    actions = read_action_receipt(repository_artifacts(root).action_receipt)
    assert actions["completed"]["summary"] == actions["attempted"]["summary"] == 3
    assert tuple(path.read_bytes() for path in metadata_paths) == before


def test_actual_sdk_can_read_evidence_after_optional_private_io_failure(tmp_path: Path) -> None:
    root, base, head = synthetic_repository(tmp_path)
    collector = setup(root, base, head)
    collector.path.unlink()
    collector.path.mkdir(mode=0o700)

    async def exercise():
        async with asyncio.timeout(15):
            async with client(root, collector) as peer:
                response = await peer.call_tool(
                    DIAGRAM_TOOL_NAME, bind(flow_submission(), collector.review_range)
                )
                assert not response.is_error
                assert json.loads(response.content[0].text)["state"] == "omitted-invalid"
                summary = await peer.call_tool("ocr_toolkit_evidence", {"action": "summary"})
                assert not summary.is_error and "records" in json.loads(summary.content[0].text)
                assert json.loads(summary.content[0].text)["diagram_output"] == {
                    "state": "unavailable"
                }

    asyncio.run(exercise())


def test_disabled_output_is_absent_from_the_real_protocol_inventory(tmp_path: Path) -> None:
    root, base, head = synthetic_repository(tmp_path)
    artifacts = repository_artifacts(root)
    prepare_artifact_directory(artifacts)
    collect_repository_evidence(root=root, base_ref=base, head_ref=head, policy_ref=base).write(
        artifacts.store
    )

    async def exercise():
        async with asyncio.timeout(15):
            async with client(root, None) as peer:
                listing = await peer.list_tools()
                assert DIAGRAM_TOOL_NAME not in {tool.name for tool in listing.tools}
                summary = await peer.call_tool("ocr_toolkit_evidence", {"action": "summary"})
                assert not summary.is_error
                assert "diagram_output" not in json.loads(summary.content[0].text)

    asyncio.run(exercise())
    assert not artifacts.diagram.exists() and not artifacts.diagram_lock.exists()


def test_real_wire_whitespace_counts_toward_the_aggregate_input_limit(tmp_path: Path) -> None:
    root, base, head = synthetic_repository(tmp_path)
    collector = setup(root, base, head)
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": DIAGRAM_TOOL_NAME,
            "arguments": bind(flow_submission(), collector.review_range),
        },
    }
    line = json.dumps(request, separators=(",", ":"))
    line += " " * (50_000 - len(line)) + "\n"
    completed = subprocess.run(
        [sys.executable, "-I", "-m", "ocr_toolkit.evidence", "--diagram-run-id", collector.run_id],
        input=line * 3,
        text=True,
        capture_output=True,
        cwd=root,
        timeout=15,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    responses = [json.loads(value) for value in completed.stdout.splitlines()]
    assert len(responses) == 3 and all("error" not in response for response in responses)
    snapshot = collector.read()
    assert snapshot.reason == "budget" and snapshot.submissions == 3
    assert snapshot.candidate is None and snapshot.input_bytes == 128 * 1024 + 1


def test_invalid_unicode_wire_calls_still_exhaust_the_shared_submission_budget(
    tmp_path: Path,
) -> None:
    root, base, head = synthetic_repository(tmp_path)
    collector = setup(root, base, head)
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": DIAGRAM_TOOL_NAME, "arguments": "\ud800"},
    }
    line = json.dumps(request, ensure_ascii=True) + "\n"
    completed = subprocess.run(
        [sys.executable, "-I", "-m", "ocr_toolkit.evidence", "--diagram-run-id", collector.run_id],
        input=line * 9,
        text=True,
        capture_output=True,
        cwd=root,
        timeout=15,
        check=False,
    )
    assert completed.returncode == 0
    responses = [json.loads(value) for value in completed.stdout.splitlines()]
    assert len(responses) == 9 and all("error" not in response for response in responses)
    snapshot = collector.read()
    assert snapshot.submissions == 9 and snapshot.reason == "budget"
    assert snapshot.candidate is None
