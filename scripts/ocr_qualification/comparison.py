"""Qualify immutable comparison-side tools through the existing model peer."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import core, execution, peer

TOOLS = ("file_read", "file_find", "code_search")
MARKERS = (
    "COMPARISON_BASE_ONLY",
    "COMPARISON_HEAD_ONLY",
    "COMPARISON_TARGET_ONLY",
    "COMPARISON_WORKTREE_ONLY",
)


@dataclass(frozen=True)
class ToolCase:
    name: str
    arguments: dict[str, Any]
    contains: tuple[str, ...]
    excludes: tuple[str, ...] = ()
    error: bool = False


def validate_side_schema(tools: object) -> None:
    """Require optional closed side selectors on every consumed code tool."""
    if not isinstance(tools, list):
        core._fail("comparison probe did not receive native tool schemas")
    for name in TOOLS:
        matches = [
            item.get("function")
            for item in tools
            if isinstance(item, dict)
            and isinstance(item.get("function"), dict)
            and item["function"].get("name") == name
        ]
        if len(matches) != 1:
            core._fail("comparison probe has missing or ambiguous native tools")
        parameters = matches[0].get("parameters")
        properties = parameters.get("properties") if isinstance(parameters, dict) else None
        side = properties.get("side") if isinstance(properties, dict) else None
        enum = side.get("enum") if isinstance(side, dict) else None
        required = parameters.get("required", []) if isinstance(parameters, dict) else None
        if (
            not isinstance(side, dict)
            or side.get("type") != "string"
            or not isinstance(enum, list)
            or len(enum) != 2
            or any(not isinstance(value, str) for value in enum)
            or set(enum) != {"new", "old"}
            or not isinstance(required, list)
            or "side" in required
        ):
            core._fail("comparison probe received an invalid side selector")


def validate_tool_result(messages: object, case: ToolCase, identity: str) -> None:
    """Bind exact arguments and one result to the actual native tool-call ID."""
    if not isinstance(messages, list):
        core._fail("comparison probe has no native message history")
    calls: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        if message.get("role") == "assistant":
            batch = message.get("tool_calls", [])
            if isinstance(batch, list):
                calls.extend(
                    call for call in batch if isinstance(call, dict) and call.get("id") == identity
                )
        elif message.get("role") == "tool" and message.get("tool_call_id") == identity:
            results.append(message)
    if len(calls) != 1 or len(results) != 1:
        core._fail("comparison probe has missing or duplicate call/result identity")
    function = calls[0].get("function")
    if not isinstance(function, dict) or function.get("name") != case.name:
        core._fail("comparison probe changed a native tool identity")
    try:
        arguments = json.loads(function.get("arguments", ""))
    except (ValueError, TypeError, RecursionError):
        core._fail("comparison probe changed native tool arguments")
    if core.canonical_json(arguments) != core.canonical_json(case.arguments):
        core._fail("comparison probe changed native tool arguments")
    content = results[0].get("content")
    if (
        not isinstance(content, str)
        or any(value not in content for value in case.contains)
        or any(value in content for value in case.excludes)
    ):
        core._fail(f"comparison probe returned the wrong immutable side or rejection: {identity}")


class ComparisonConversation:
    """Issue bounded deterministic tool calls and admit their observed results."""

    def __init__(self, cases: list[ToolCase]) -> None:
        self.cases = cases
        self.index = 0
        self.complete = False
        self.requests = 0

    def __call__(self, request: dict[str, Any]) -> tuple[dict[str, Any], str]:
        self.requests += 1
        if self.requests > len(self.cases) + 2:
            core._fail("comparison probe exceeded its exchange budget")
        if self.index == 0:
            validate_side_schema(request.get("tools"))
        else:
            validate_tool_result(
                request.get("messages"), self.cases[self.index - 1], f"comparison-{self.index - 1}"
            )
        if self.index == len(self.cases):
            self.complete = True
            return {"name": "task_done", "arguments": "{}"}, "comparison-done"
        case = self.cases[self.index]
        identity = f"comparison-{self.index}"
        self.index += 1
        return {"name": case.name, "arguments": json.dumps(case.arguments)}, identity


def comparison_cases(base: str) -> list[ToolCase]:
    """Exercise default/new/old, side-relative paths and malformed selectors."""
    cases: list[ToolCase] = []
    for side in (None, "new", "old"):
        old = side == "old"
        selector = {} if side is None else {"side": side}
        prefix = ("SIDE: old", f"REVISION: {base}") if old else ()
        excluded_prefix = () if old else ("SIDE: old",)
        marker = MARKERS[0 if old else 1]
        excluded_markers = tuple(item for item in MARKERS if item != marker)
        cases.extend(
            [
                ToolCase(
                    "file_read",
                    {"file_path": "shared.txt", **selector},
                    (*prefix, marker),
                    (*excluded_prefix, *excluded_markers),
                ),
                ToolCase(
                    "file_find",
                    {"query_name": "shared.txt", **selector},
                    (*prefix, "shared.txt"),
                    excluded_prefix,
                ),
                ToolCase(
                    "code_search",
                    {"search_text": "COMPARISON_", "file_patterns": ["shared.txt"], **selector},
                    (*prefix, marker),
                    (*excluded_prefix, *excluded_markers),
                ),
            ]
        )
        renamed = "renamed-old.txt" if old else "renamed-new.txt"
        other = "renamed-new.txt" if old else "renamed-old.txt"
        cases.extend(
            [
                ToolCase(
                    "file_read",
                    {"file_path": renamed, **selector},
                    (*prefix, "RENAMED_PAYLOAD"),
                    excluded_prefix,
                ),
                ToolCase(
                    "file_find",
                    {"query_name": "renamed-", **selector},
                    (*prefix, renamed),
                    (*excluded_prefix, other),
                ),
                ToolCase(
                    "code_search",
                    {"search_text": "RENAMED_PAYLOAD", **selector},
                    (*prefix, renamed),
                    (*excluded_prefix, other),
                ),
                ToolCase(
                    "file_read",
                    {"file_path": "deleted-only.txt", **selector},
                    (*prefix, "DELETED_PAYLOAD") if old else ("Error", "deleted-only.txt"),
                    excluded_prefix if old else (*excluded_prefix, "DELETED_PAYLOAD"),
                    error=not old,
                ),
                ToolCase(
                    "file_find",
                    {"query_name": "deleted-only", **selector},
                    (*prefix, "deleted-only.txt") if old else ("// The file was not found",),
                    excluded_prefix if old else (*excluded_prefix, "deleted-only.txt"),
                ),
                ToolCase(
                    "code_search",
                    {"search_text": "DELETED_PAYLOAD", **selector},
                    (*prefix, "deleted-only.txt") if old else ("No matches found",),
                    excluded_prefix if old else (*excluded_prefix, "DELETED_PAYLOAD"),
                ),
            ]
        )
    cases.extend(
        [
            ToolCase(
                "file_read",
                {"file_path": "renamed-new.txt", "side": "old"},
                ("SIDE: old", f"REVISION: {base}", "Error"),
                ("RENAMED_PAYLOAD",),
                error=True,
            ),
            ToolCase(
                "file_read",
                {"file_path": "renamed-old.txt", "side": "new"},
                ("Error",),
                ("SIDE: old", "RENAMED_PAYLOAD"),
                error=True,
            ),
        ]
    )
    arguments = (
        {"file_path": "shared.txt"},
        {"query_name": "shared.txt"},
        {"search_text": "COMPARISON_"},
    )
    for name, fields in zip(TOOLS, arguments, strict=True):
        for side in ("base", None, True, [], {}):
            cases.append(
                ToolCase(
                    name,
                    {**fields, "side": side},
                    ("side must be new or old",),
                    MARKERS,
                    error=True,
                )
            )
    # Reset OCR's independent per-task/tool failure guard between negative cases.
    controls = {
        "file_read": ToolCase(
            "file_read",
            {"file_path": "shared.txt"},
            (MARKERS[1],),
            (MARKERS[0], MARKERS[2], MARKERS[3], "SIDE: old"),
        ),
        "file_find": ToolCase(
            "file_find",
            {"query_name": "renamed-"},
            ("renamed-new.txt",),
            ("renamed-old.txt", "SIDE: old"),
        ),
        "code_search": ToolCase(
            "code_search",
            {"search_text": "COMPARISON_", "file_patterns": ["shared.txt"]},
            (MARKERS[1],),
            (MARKERS[0], MARKERS[2], MARKERS[3], "SIDE: old"),
        ),
    }
    isolated = []
    for case in cases:
        isolated.append(case)
        if case.error:
            isolated.append(controls[case.name])
    return isolated


def comparison_sides_probe(binary: Path, directory: Path) -> dict[str, object]:
    """Read B/H while checkout and worktree deliberately name other content."""
    root = directory / "comparison-sides-probe"
    root.mkdir()
    git_env = execution._isolated_probe_environment(root / "git-home")
    repo, base, _head = execution._synthetic_repo(
        root,
        git_env,
        context_files={
            "shared.txt": MARKERS[0] + "\n",
            "renamed-old.txt": "RENAMED_PAYLOAD\n",
            "deleted-only.txt": "DELETED_PAYLOAD\n",
        },
    )
    (repo / "shared.txt").write_text(MARKERS[1] + "\n", encoding="utf-8")
    execution._run(["git", "mv", "renamed-old.txt", "renamed-new.txt"], cwd=repo, env=git_env)
    execution._run(["git", "rm", "deleted-only.txt"], cwd=repo, env=git_env)
    execution._run(["git", "add", "shared.txt"], cwd=repo, env=git_env)
    execution._run(["git", "commit", "--amend", "--no-edit"], cwd=repo, env=git_env)
    head = execution._run(["git", "rev-parse", "HEAD"], cwd=repo, env=git_env).strip()
    execution._run(["git", "checkout", "-b", "target", base], cwd=repo, env=git_env)
    (repo / "shared.txt").write_text(MARKERS[2] + "\n", encoding="utf-8")
    execution._run(["git", "add", "shared.txt"], cwd=repo, env=git_env)
    execution._run(["git", "commit", "-m", "unreviewed target"], cwd=repo, env=git_env)
    (repo / "shared.txt").write_text(MARKERS[3] + "\n", encoding="utf-8")
    (repo / "staged.txt").write_text("STAGED_PAYLOAD\n", encoding="utf-8")
    execution._run(["git", "add", "staged.txt"], cwd=repo, env=git_env)
    (repo / "untracked.txt").write_text("UNTRACKED_PAYLOAD\n", encoding="utf-8")
    preserved = tuple(
        repo / name
        for name in (
            ".git/HEAD",
            ".git/index",
            "example.py",
            "shared.txt",
            "renamed-old.txt",
            "deleted-only.txt",
            "staged.txt",
            "untracked.txt",
        )
    )
    before = tuple(path.read_bytes() for path in preserved)
    script = ComparisonConversation(comparison_cases(base))
    env = execution._isolated_probe_environment(root / "review-home")
    with peer._stub_gateway(tool_script=script) as url:
        env.update(
            {
                "OCR_LLM_URL": url,
                "OCR_LLM_TOKEN": "synthetic-token",
                "OCR_LLM_MODEL": "synthetic-model",
                "OCR_LLM_PROTOCOL": "openai",
                "OCR_TELEMETRY_ENABLED": "false",
            }
        )
        output = execution._run(
            [
                str(binary),
                "review",
                "--from",
                base,
                "--to",
                head,
                "--effort",
                "low",
                "--concurrency",
                "1",
                "--format",
                "json",
                "--audience",
                "agent",
            ],
            cwd=repo,
            env=env,
        )
    if not script.complete or tuple(path.read_bytes() for path in preserved) != before:
        core._fail("comparison probe was incomplete or changed the checkout")
    from ocr_toolkit.result_contract import OcrResultContractError, parse_result_outcome

    try:
        result = parse_result_outcome(json.loads(output))
    except (ValueError, OcrResultContractError) as exc:
        raise core.CompatibilityError("comparison probe emitted an invalid review outcome") from exc
    if result.kind != "clean" or result.selected_count != 1 or result.completed_count != 1:
        core._fail("comparison probe did not complete its exact selected file")
    return {
        "result": "passed",
        "tools": list(TOOLS),
        "default_side": "new",
        "old_ref": "resolved-base",
        "new_ref": "resolved-head",
        "invalid_sides_rejected": True,
        "renamed_paths": "side-relative",
        "deleted_paths": "old-only",
        "worktree": "preserved",
        "target_tip": "not-used",
    }
