"""Qualify native comment repair, anchors and failure serialization."""

from __future__ import annotations

import json
from pathlib import Path

from . import core, execution, peer


def _comment_arguments_probe(binary: Path, directory: Path) -> dict[str, object]:
    """Cross OCR's real parser and failure serialization using a deterministic gateway."""

    from ocr_toolkit.review_runner import _tool_failure_telemetry

    root = directory / "comment-arguments-probe"
    root.mkdir()
    repo, base, head = execution._synthetic_repo(
        root, execution._isolated_probe_environment(root / "git-home")
    )
    for mode in ("array", "serialized", "repaired", "rejected"):
        env = execution._isolated_probe_environment(root / f"{mode}-home")
        with peer._stub_gateway(comment_mode=mode) as gateway:
            env.update(
                {
                    "OCR_LLM_URL": gateway,
                    "OCR_LLM_TOKEN": "synthetic-token",
                    "OCR_LLM_MODEL": "synthetic-model",
                    "OCR_LLM_PROTOCOL": "openai",
                    "OCR_TELEMETRY_ENABLED": "false",
                }
            )
            raw = execution._run(
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
                    "--effort",
                    "low",
                    "--no-filter",
                ],
                cwd=repo,
                env=env,
            )
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise core.CompatibilityError(
                f"comment arguments {mode}: review did not emit JSON"
            ) from exc
        if not isinstance(payload, dict):
            core._fail(f"comment arguments {mode}: review result must be an object")
        comments = payload.get("comments")
        warnings = payload.get("warnings", [])
        if (
            not isinstance(comments, list)
            or not all(isinstance(comment, dict) for comment in comments)
            or not isinstance(warnings, list)
        ):
            core._fail(f"comment arguments {mode}: invalid result shape")
        if mode == "rejected":
            calls = payload.get("tool_calls", {})
            if not isinstance(calls, dict):
                core._fail("comment arguments rejection emitted invalid tool-call evidence")
            telemetry = _tool_failure_telemetry(calls)
            details = calls.get("failure_details", [])
            if (
                comments
                or not telemetry.valid
                or telemetry.failed != 1
                or not isinstance(details, list)
                or len(details) != 1
                or not isinstance(details[0], dict)
                or details[0].get("arguments") != peer._comment_probe_arguments(mode, "example.py")
            ):
                core._fail("comment arguments rejection lost its closed failure evidence")
        else:
            expected = peer._comment_probe_records("example.py")
            actual = [{key: comment.get(key) for key in expected[0]} for comment in comments]
            if sorted(actual, key=lambda item: str(item["content"])) != expected:
                core._fail(f"comment arguments {mode}: changed or lost comment fields")
            if any(comment.get("start_line") != 2 for comment in comments):
                core._fail(f"comment arguments {mode}: lost deterministic anchors")
        repaired = [
            item
            for item in warnings
            if isinstance(item, dict) and item.get("type") == "comment_args_repaired"
        ]
        if len(repaired) != int(mode == "repaired"):
            core._fail(f"comment arguments {mode}: wrong repair warning state")
    return {
        "result": "passed",
        "intact_cases": ["array", "serialized", "repaired"],
        "comments_per_batch": 2,
        "suspect_batch_rejected": True,
        "failure_arguments_preserved": True,
        "repair_warning": True,
    }
