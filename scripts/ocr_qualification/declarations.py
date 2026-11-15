"""Observe per-request native tool admission and capabilities across review rounds."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import comparison, core, execution, peer

EXPECTED = {
    "result": "passed",
    "undeclared_tool": "rejected",
    "declared_read": "executed",
    "later_round": "capabilities-preserved",
    "requests": 6,
}


class DeclarationConversation:
    """Track exact calls, feedback and a fresh second-round context."""

    def __init__(self) -> None:
        """Keep a bounded conversation independent of HTTP handler lifetimes."""
        self.index = 0
        self.tools: set[str] = set()
        self.complete = False
        self.previous: comparison.ToolCase | None = None

    def __call__(self, request: dict[str, Any]) -> tuple[dict[str, Any], str]:
        """Require declared tools on each request before issuing the next exact call."""
        names = {
            item.get("function", {}).get("name")
            for item in request.get("tools", [])
            if isinstance(item, dict)
        }
        if not {"file_read", "code_comment", "task_done"}.issubset(names):
            core._fail("review round lost consumed native tools")
        if "undeclared_qualification_probe" in names or self.index >= 6:
            core._fail("tool declaration probe has an invalid tool inventory or request count")
        if self.index == 0:
            self.tools = names
        elif self.index == 4:
            if names != self.tools:
                core._fail("the second review round changed consumed capabilities")
            messages = request.get("messages")
            if (
                not isinstance(messages, list)
                or not messages
                or not all(
                    isinstance(message, dict)
                    and message.get("role") in {"system", "developer", "user"}
                    for message in messages
                )
                or not any(message.get("role") == "user" for message in messages)
            ):
                core._fail("the second review round did not rebuild fresh message history")
        elif self.previous is not None:
            comparison.validate_tool_result(
                request.get("messages"), self.previous, f"declaration-{self.index - 1}"
            )
        cases = (
            comparison.ToolCase("undeclared_qualification_probe", {}, ("not available",)),
            comparison.ToolCase("file_read", {"file_path": "example.py"}, ("return 2",)),
            comparison.ToolCase(
                "code_comment",
                {
                    "comments": [
                        {
                            "content": "Synthetic declaration finding.",
                            "existing_code": "    return 2",
                            "path": "example.py",
                            "severity": "low",
                            "category": "maintainability",
                        }
                    ]
                },
                (),
            ),
            comparison.ToolCase("task_done", {}, ()),
            comparison.ToolCase("file_read", {"file_path": "example.py"}, ("return 2",)),
            comparison.ToolCase("task_done", {}, ()),
        )
        case = cases[self.index]
        identity = f"declaration-{self.index}"
        self.index += 1
        self.previous = case
        self.complete = self.index == 6
        return {"name": case.name, "arguments": json.dumps(case.arguments)}, identity


def declaration_probe(binary: Path, directory: Path) -> dict[str, object]:
    """Cross actual OCR requests, dispatch rejection, reads and a later review round."""
    root = directory / "declarations-probe"
    root.mkdir()
    env = execution._isolated_probe_environment(root / "git-home")
    repo, base, head = execution._synthetic_repo(root, env)
    conversation = DeclarationConversation()
    with peer._stub_gateway(tool_script=conversation) as url:
        env.update(
            OCR_LLM_URL=url,
            OCR_LLM_TOKEN="synthetic-token",
            OCR_LLM_MODEL="synthetic-model",
            OCR_LLM_PROTOCOL="openai",
            OCR_TELEMETRY_ENABLED="false",
        )
        result = json.loads(
            execution._run(
                [
                    str(binary),
                    "review",
                    "--from",
                    base,
                    "--to",
                    head,
                    "--format",
                    "json",
                    "--audience",
                    "agent",
                    "--concurrency",
                    "1",
                ],
                cwd=repo,
                env=env,
            )
        )
    from ocr_toolkit.result_contract import parse_result_outcome
    from ocr_toolkit.review_range import ReviewRange, admit_native_range

    admit_native_range(result, ReviewRange(base, head))
    if not conversation.complete or parse_result_outcome(result).kind != "clean":
        core._fail("tool declaration probe did not complete both review rounds")
    counts = result.get("tool_calls", {}).get("by_tool", {})
    if counts.get("file_read") != 2 or "undeclared_qualification_probe" in counts:
        core._fail("tool declaration probe dispatched an unavailable tool or lost a read")
    return dict(EXPECTED)
