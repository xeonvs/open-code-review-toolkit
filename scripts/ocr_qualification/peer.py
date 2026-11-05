"""Deterministic local model peer and strict synthetic exchange grammar."""

from __future__ import annotations

import contextlib
import http.client
import http.server
import json
import re
import threading
from collections.abc import Iterator
from typing import Any

from . import core, settings


class _StubHandler(http.server.BaseHTTPRequestHandler):
    """Deterministic OpenAI-compatible response sequence for OCR probes."""

    request_count = 0
    tokens_per_request = 2
    grouping_tokens_per_request = 2
    grouping_mode = "singletons"
    grouping_inventories: list[list[core.GroupingInventoryEntry]] = []
    main_mode = "findings"
    comment_mode = "default"
    completion_caps: list[object] = []
    request_stages: list[str] = []
    prior_finding_semantics: set[str] = set()
    recheck_instruction_requests = 0
    capture_reasoning = False
    reasoning_requests: list[dict[str, object]] = []
    reasoning_overflow = False
    capture_controls = False
    control_requests: list[dict[str, object]] = []
    control_overflow = False
    context_reads: dict[str, tuple[str, ...]] = {}
    observed_context_reads: set[str] = set()
    observed_csharp_rules = False

    @staticmethod
    def _message_contents(messages: list[Any]) -> list[str]:
        """Return only text message content from one bounded probe request."""

        return [
            content
            for message in messages
            if isinstance(message, dict) and isinstance((content := message.get("content")), str)
        ]

    @classmethod
    def _grouping_files(cls, messages: list[Any]) -> list[int]:
        """Extract one version-bound grouping inventory and retain structural evidence."""

        entries = parse_grouping_inventory(messages)
        cls.grouping_inventories.append(entries)
        return [entry.index for entry in entries]

    @classmethod
    def _is_grouping_request(cls, messages: list[Any]) -> bool:
        """Distinguish the tool-free grouping task from OCR's tool-free plan task."""

        return any(
            content.startswith(settings.GROUPING_PROMPT_PREFIX)
            and settings.GROUPING_RESPONSE_BOUNDARY in content
            for content in cls._message_contents(messages)
        )

    @classmethod
    def _review_path(cls, messages: list[Any]) -> str | None:
        """Extract the first path from OCR's public review-files XML block."""

        for content in cls._message_contents(messages):
            if match := re.search(r'<file path="([^"\r\n]+)">', content):
                return match.group(1)
        return None

    def do_POST(self) -> None:
        allowed_paths = {"/v1/chat/completions"}
        if type(self).capture_reasoning or type(self).capture_controls:
            allowed_paths.add("/v1/responses")
        if type(self).capture_controls:
            allowed_paths.add("/v1/messages")
        if self.path not in allowed_paths:
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > settings.MAX_HTTP_BYTES:
            self.send_error(400)
            return
        try:
            request = json.loads(self.rfile.read(length))
        except json.JSONDecodeError:
            self.send_error(400)
            return
        if not isinstance(request, dict):
            self.send_error(400)
            return
        if type(self).capture_controls:
            if len(type(self).control_requests) < 32:
                stream = request.get("stream")
                type(self).control_requests.append(
                    {
                        "path": self.path,
                        "stream_present": "stream" in request,
                        "stream_boolean": stream if type(stream) is bool else None,
                        "stream_options_present": "stream_options" in request,
                    }
                )
            else:
                type(self).control_overflow = True
            self.send_error(400, "Synthetic request capture; no model execution")
            return
        if type(self).capture_reasoning:
            reasoning = request.get("reasoning")
            if len(type(self).reasoning_requests) < 32:
                type(self).reasoning_requests.append(
                    {
                        "path": self.path,
                        "root_present": "reasoning_effort" in request,
                        "root_effort": request.get("reasoning_effort"),
                        "nested_present": isinstance(reasoning, dict) and "effort" in reasoning,
                        "nested_effort": reasoning.get("effort")
                        if isinstance(reasoning, dict)
                        else None,
                        "summary": reasoning.get("summary")
                        if isinstance(reasoning, dict)
                        else None,
                    }
                )
            else:
                type(self).reasoning_overflow = True
            self.send_error(400, "Synthetic request capture; no model execution")
            return
        type(self).completion_caps.append(request.get("max_completion_tokens"))
        messages = request.get("messages")
        if not isinstance(messages, list):
            self.send_error(400)
            return
        type(self).request_count += 1
        tools = request.get("tools")
        tool_names: set[str] = set()
        if isinstance(tools, list):
            for tool in tools:
                function = tool.get("function") if isinstance(tool, dict) else None
                if isinstance(function, dict) and isinstance(function.get("name"), str):
                    tool_names.add(function["name"])
        message: dict[str, Any]
        if not tool_names and type(self)._is_grouping_request(messages):
            indices = type(self)._grouping_files(messages)
            if not indices:
                self.send_error(400)
                return
            groups = (
                [{"label": "compatibility-group", "files": indices}]
                if type(self).grouping_mode == "combined"
                else [{"label": str(index), "files": [index]} for index in indices]
            )
            message = {"role": "assistant", "content": json.dumps(groups)}
            finish_reason = "stop"
            stage = "grouping"
        elif not tool_names:
            message = {
                "role": "assistant",
                "content": "Summary: Review the changed code.\n\nIssues\n(none)",
            }
            finish_reason = "stop"
            stage = "plan"
        elif "approve_all_comments" in tool_names:
            message = {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call-filter",
                        "type": "function",
                        "function": {"name": "approve_all_comments", "arguments": "{}"},
                    }
                ],
            }
            finish_reason = "tool_calls"
            stage = "filter"
        else:
            contents = type(self)._message_contents(messages)
            if any(settings.PRIOR_FINDING_RECHECK_MARKER in item for item in contents):
                type(self).recheck_instruction_requests += 1
            if type(self).context_reads:
                type(self).observed_csharp_rules |= any(
                    "#### Nullability and Reference Types" in content for content in contents
                )
                type(self).observed_context_reads.update(
                    context_read_observations(messages, type(self).context_reads)
                )
                remaining = sorted(
                    type(self).context_reads.keys() - type(self).observed_context_reads
                )
                if remaining and type(self).request_count <= 16 and "file_read" in tool_names:
                    function = {
                        "name": "file_read",
                        "arguments": json.dumps(
                            {"file_path": remaining[0], "start_line": 1, "end_line": 20}
                        ),
                    }
                else:
                    function = {"name": "task_done", "arguments": "{}"}
                call_id = f"context-{type(self).request_count}"
                stage = "main"
            elif type(self).main_mode in {"exhaust-tools", "exhaust-tools-incomplete"}:
                if "file_read" in tool_names:
                    function = {
                        "name": "file_read",
                        "arguments": json.dumps(
                            {"file_path": "example.py", "start_line": 1, "end_line": 1}
                        ),
                    }
                    call_id = f"call-read-{type(self).request_count}"
                    stage = "main"
                else:
                    function = {"name": "task_done", "arguments": "{}"}
                    call_id = "call-grace-verdict"
                    stage = "grace"
            else:
                prior_comment = any(
                    isinstance(message, dict)
                    and any(
                        isinstance(call, dict)
                        and isinstance(call.get("function"), dict)
                        and call["function"].get("name") == "code_comment"
                        for call in message.get("tool_calls", [])
                    )
                    for message in messages
                )
                later_round = any("### Previously Confirmed Findings" in item for item in contents)
                if later_round:
                    type(self).prior_finding_semantics.add("filter_survivors_as_confirmed")
                if not prior_comment and not later_round:
                    path = type(self)._review_path(messages)
                    if path is None:
                        self.send_error(400)
                        return
                    arguments = json.dumps(
                        {
                            "comments": [
                                {
                                    "content": "Synthetic compatibility finding.",
                                    "existing_code": "    return 2",
                                    "path": path,
                                    "thinking": "Synthetic private compatibility reasoning.",
                                    "category": "maintainability",
                                    "severity": "low",
                                }
                            ]
                        }
                    )
                    if type(self).comment_mode != "default":
                        arguments = _comment_probe_arguments(type(self).comment_mode, path)
                    function = {"name": "code_comment", "arguments": arguments}
                    call_id = "call-comment"
                else:
                    function = {"name": "task_done", "arguments": "{}"}
                    call_id = "call-done"
                stage = "main"
            message = {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": call_id,
                        "type": "function",
                        "function": function,
                    }
                ],
            }
            finish_reason = "tool_calls"
            if stage == "grace" and type(self).main_mode == "exhaust-tools-incomplete":
                message = {"role": "assistant", "content": "No completion verdict."}
                finish_reason = "stop"
        type(self).request_stages.append(stage)
        usage_tokens = (
            type(self).grouping_tokens_per_request
            if stage == "grouping"
            else type(self).tokens_per_request
        )
        payload = json.dumps(
            {
                "id": f"compat-{type(self).request_count}",
                "object": "chat.completion",
                "model": "synthetic-model",
                "choices": [{"index": 0, "message": message, "finish_reason": finish_reason}],
                "usage": {
                    "prompt_tokens": usage_tokens - 1,
                    "completion_tokens": 1,
                    "total_tokens": usage_tokens,
                },
            }
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)
        self.wfile.flush()
        self.close_connection = True

    def log_message(self, _format: str, *_args: Any) -> None:
        return


@contextlib.contextmanager
def _stub_gateway(
    *,
    tokens_per_request: int = 2,
    grouping_tokens_per_request: int = 2,
    grouping_mode: str = "singletons",
    main_mode: str = "findings",
    comment_mode: str = "default",
    capture_reasoning: bool = False,
    capture_controls: bool = False,
    context_reads: dict[str, tuple[str, ...]] | None = None,
) -> Iterator[str]:
    """Serve deterministic responses with configurable real usage accounting."""

    if tokens_per_request < 2 or grouping_tokens_per_request < 2:
        core._fail("stub gateway token usage must be at least two")
    if grouping_mode not in {"singletons", "combined"}:
        core._fail("stub gateway grouping mode is invalid")
    if main_mode not in {"findings", "exhaust-tools", "exhaust-tools-incomplete"}:
        core._fail("stub gateway main mode is invalid")
    _StubHandler.request_count = 0
    _StubHandler.tokens_per_request = tokens_per_request
    _StubHandler.grouping_tokens_per_request = grouping_tokens_per_request
    _StubHandler.grouping_mode = grouping_mode
    _StubHandler.grouping_inventories = []
    _StubHandler.main_mode = main_mode
    if comment_mode not in {"default", "array", "serialized", "repaired", "rejected"}:
        core._fail("stub comment mode is invalid")
    _StubHandler.comment_mode = comment_mode
    _StubHandler.completion_caps = []
    _StubHandler.request_stages = []
    _StubHandler.prior_finding_semantics = set()
    _StubHandler.recheck_instruction_requests = 0
    _StubHandler.capture_reasoning = capture_reasoning
    _StubHandler.reasoning_requests = []
    _StubHandler.reasoning_overflow = False
    _StubHandler.capture_controls = capture_controls
    _StubHandler.control_requests = []
    _StubHandler.control_overflow = False
    _StubHandler.context_reads = dict(context_reads or {})
    _StubHandler.observed_context_reads = set()
    _StubHandler.observed_csharp_rules = False
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _StubHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def context_read_observations(
    messages: list[Any], expected: dict[str, tuple[str, ...]]
) -> set[str]:
    """Bind captured project values to their actual file_read call and path."""

    calls: dict[str, str] = {}
    ambiguous: set[str] = set()
    for message in messages:
        if not isinstance(message, dict) or message.get("role") != "assistant":
            continue
        tools = message.get("tool_calls", [])
        if not isinstance(tools, list):
            continue
        for call in tools:
            if not isinstance(call, dict) or not isinstance(call.get("id"), str):
                continue
            identity = call["id"]
            if identity in calls or identity in ambiguous:
                calls.pop(identity, None)
                ambiguous.add(identity)
                continue
            function = call.get("function")
            if not isinstance(function, dict) or function.get("name") != "file_read":
                ambiguous.add(identity)
                continue
            try:
                args = json.loads(function.get("arguments", ""))
            except (ValueError, TypeError, RecursionError):
                continue
            path = args.get("file_path") if isinstance(args, dict) else None
            if isinstance(path, str) and path in expected:
                calls[identity] = path
    observed = set()
    for message in messages:
        if not isinstance(message, dict) or message.get("role") != "tool":
            continue
        identity = message.get("tool_call_id")
        if not isinstance(identity, str) or identity not in calls:
            continue
        content = message.get("content")
        path = calls[identity]
        if isinstance(content, str) and all(marker in content for marker in expected[path]):
            observed.add(path)
    return observed


def parse_grouping_inventory(messages: list[Any]) -> list[core.GroupingInventoryEntry]:
    """Parse the current indexed, status-first inventory without legacy fallbacks."""

    pattern = re.compile(
        r"\[(?P<index>0|[1-9][0-9]{0,2})\] "
        r"(?P<status>ADDED|MODIFIED|DELETED|RENAMED)   "
        r"(?P<path>[^\r\n]{1,1000}) "
        r"\(\+(?P<insertions>0|[1-9][0-9]{0,9})/-(?P<deletions>0|[1-9][0-9]{0,9})\)"
    )

    blocks: list[str] = []
    for content in _StubHandler._message_contents(messages):
        if (
            not content.startswith(settings.GROUPING_PROMPT_PREFIX)
            or settings.GROUPING_RESPONSE_BOUNDARY not in content
        ):
            continue
        inventory, remainder = content[len(settings.GROUPING_PROMPT_PREFIX) :].split(
            settings.GROUPING_RESPONSE_BOUNDARY, 1
        )
        if settings.GROUPING_RESPONSE_BOUNDARY in remainder:
            core._fail("grouping prompt contains duplicate response boundaries")
        blocks.append(inventory)
    if len(blocks) != 1:
        core._fail("grouping prompt must contain exactly one changed-file inventory")

    lines = blocks[0].splitlines()
    if not lines or len(lines) > settings.MAX_GROUPING_INVENTORY_ENTRIES:
        core._fail("grouping inventory has an invalid entry count")
    entries: list[core.GroupingInventoryEntry] = []
    observed_paths: set[str] = set()
    for line in lines:
        match = pattern.fullmatch(line)
        if match is None:
            core._fail("OCR emitted an invalid grouping inventory entry")
        index = int(match.group("index"))
        path = match.group("path")
        insertions = int(match.group("insertions"))
        deletions = int(match.group("deletions"))
        if (
            index != len(entries)
            or len(path) > settings.MAX_GROUPING_PATH_CHARS
            or path in observed_paths
            or insertions > settings.MAX_GROUPING_CHURN
            or deletions > settings.MAX_GROUPING_CHURN
        ):
            core._fail("OCR emitted an invalid grouping inventory value")
        observed_paths.add(path)
        entries.append(
            core.GroupingInventoryEntry(
                index=index,
                status=match.group("status"),
                path=path,
                insertions=insertions,
                deletions=deletions,
            )
        )
    return entries


def _require_exact_grouping_inventory(
    observed: list[core.GroupingInventoryEntry],
    expected: list[core.GroupingInventoryEntry],
) -> None:
    """Reject status, churn, path, or ordering drift in one grouping inventory."""

    if observed != expected:
        core._fail("semantic grouping review emitted an unexpected status/churn inventory")


def _comment_probe_records(path: str) -> list[dict[str, str]]:
    """Build a bounded comment batch whose public fields must survive intact."""

    return [
        {
            "content": f'Use "guard" before step {number}.',
            "existing_code": "    return 2",
            "suggestion_code": "    return 3",
            "path": path,
            "severity": "low",
            "category": "bug",
        }
        for number in (1, 2)
    ]


def _comment_probe_arguments(mode: str, path: str) -> str:
    """Serialize controlled correct, recoverable and suspect tool arguments."""

    records = _comment_probe_records(path)
    if mode == "array":
        return json.dumps({"comments": records})
    serialized = json.dumps(records)
    if mode == "repaired":
        serialized = serialized.replace('\\"guard\\"', '"guard"')
    elif mode == "rejected":
        serialized = (
            '[{"content":"Use "guard","existing_code":"    return 2",'
            '"suggestion_code":"    return 3","path":' + json.dumps(path) + "}]"
        )
    return json.dumps({"comments": serialized})
