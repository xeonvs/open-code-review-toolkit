"""Compose candidate-owned contract observations from real OCR probes."""

from __future__ import annotations

import json
import os
import re
import stat
from pathlib import Path
from typing import Any

from . import comments as comment_checks
from . import comparison, core, execution, numeric, peer, selection, settings, wire_controls
from . import contracts as contract_rules


def run_contracts(binary: Path, version: str, directory: Path) -> dict[str, Any]:
    """Run deterministic CLI and JSON-consumer probes against one OCR binary."""

    contract_rules._require_live_qualification_version(version)
    binary.chmod(binary.stat().st_mode | stat.S_IXUSR)
    git_env = execution._isolated_probe_environment(directory / "git-home")
    repo, base, head = execution._synthetic_repo(directory, git_env)
    version_output = execution._run([str(binary), "--version"], cwd=repo, env=git_env)
    if re.search(rf"(?<![0-9.])v?{re.escape(version)}(?![0-9.])", version_output) is None:
        core._fail(f"OCR binary did not report candidate version {version}")
    help_output = execution._run([str(binary), "review", "--help"], cwd=repo, env=git_env)
    required_review_flags = set(settings.REQUIRED_REVIEW_FLAGS)
    missing = sorted(flag for flag in required_review_flags if flag not in help_output)
    if missing:
        core._fail(f"candidate review help is missing required flags: {', '.join(missing)}")
    preview_home = directory / "preview-home"
    preview_env = execution._isolated_probe_environment(preview_home)
    preview_command = [str(binary), "review", "--from", base, "--to", head, "--preview"]
    preview_command.extend(["--format", "json"])
    preview = execution._run(preview_command, cwd=repo, env=preview_env)
    try:
        preview_payload = json.loads(preview)
    except json.JSONDecodeError as exc:
        raise core.CompatibilityError("candidate JSON preview did not emit JSON") from exc
    preview_files = preview_payload.get("files") if isinstance(preview_payload, dict) else None
    if not isinstance(preview_files, list) or not any(
        isinstance(item, dict) and item.get("path") == "example.py" for item in preview_files
    ):
        core._fail("candidate JSON preview did not select the synthetic changed file")
    if os.path.lexists(preview_home / ".opencodereview" / "sessions"):
        core._fail("candidate preview created a review session store")

    review_home = directory / "review-home"
    env = execution._isolated_probe_environment(review_home)
    with peer._stub_gateway() as gateway_url:
        env.update(
            {
                "OCR_LLM_URL": gateway_url,
                "OCR_LLM_TOKEN": "synthetic-token",
                "OCR_LLM_MODEL": "synthetic-model",
                "OCR_LLM_PROTOCOL": "openai",
                "OCR_TELEMETRY_ENABLED": "false",
            }
        )
        result_output = execution._run(
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
        review_stages = list(peer._StubHandler.request_stages)
    try:
        sample = json.loads(result_output)
    except json.JSONDecodeError as exc:
        raise core.CompatibilityError("candidate full review did not emit JSON") from exc
    if not isinstance(sample, dict):
        core._fail("candidate full review emitted an unsupported result object")
    optional_capabilities = contract_rules.detect_optional_capabilities(help_output, sample)
    from ocr_toolkit.result_contract import OcrResultContractError, parse_result_outcome

    try:
        outcome = parse_result_outcome(sample)
    except OcrResultContractError as exc:
        raise core.CompatibilityError(
            f"candidate full review emitted an unsupported result object: {exc}"
        ) from exc
    if outcome.kind != "clean":
        core._fail(f"candidate full review did not complete cleanly: {outcome.kind}")
    comments = sample.get("comments")
    if not isinstance(comments, list) or len(comments) != 1 or not isinstance(comments[0], dict):
        core._fail("candidate full review did not emit the synthetic comment")
    contract_rules._validate_file_groups(sample.get("groups"), {"example.py"})
    if review_stages != ["main", "main", "filter", "main"]:
        core._fail(f"default medium review emitted an unexpected stage sequence: {review_stages!r}")
    sample["future_additive_field"] = {"accepted": True}
    from ocr_toolkit.posting.comments import comment_line
    from ocr_toolkit.posting.formatting import (
        format_inline_comment,
        format_token_usage_summary,
        format_tool_calls_summary,
    )

    comment = comments[0]
    assert isinstance(comment, dict)
    rendered = format_inline_comment(comment)
    if comment_line(comment) != 2 or "Synthetic compatibility finding" not in rendered:
        core._fail("toolkit posting consumer rejected the candidate result contract")
    token_summary = format_token_usage_summary(sample)
    if not token_summary or "total" not in token_summary:
        core._fail("toolkit token summary rejected the candidate result contract")
    if "1 total" not in format_tool_calls_summary(sample.get("tool_calls")):
        core._fail("toolkit tool-call summary rejected the candidate result contract")
    if comment.get("thinking") != "Synthetic private compatibility reasoning.":
        core._fail("candidate did not preserve additive comment thinking")
    if "Synthetic private compatibility reasoning." in rendered:
        core._fail("toolkit posting consumer exposed private comment thinking")
    thinking_probe = {
        "additive_field_preserved": True,
        "posting_exposes_thinking": False,
        "result": "passed",
    }

    contracts: dict[str, Any] = {
        "numeric_cli_probe": numeric._numeric_cli_probe(binary, repo, base, head, directory),
        "optional_capabilities": optional_capabilities,
        "review_budget_probe": numeric._budget_result_probe(binary, directory),
        "target_rule_selection_probe": selection._target_rule_selection_probe(binary, directory),
        "version_probe": "passed",
        "required_review_flags": sorted(required_review_flags),
        "preview_probe": {
            "format": "json",
            "path": "example.py",
            "result": "passed",
            "session_store_created": False,
        },
        "result_contract_probe": {
            "additive_fields_allowed": True,
            "comment_fields": sorted(comment),
            "manifest_schema": ("ocr.run-manifest/v1" if outcome.manifest_present else "legacy"),
            "normalized_outcome": outcome.kind,
            "result": "passed",
        },
    }
    contracts["semantic_grouping_probe"] = selection._semantic_grouping_probe(binary, directory)
    contracts["small_change_grouping_probe"] = selection._small_change_grouping_probe(
        binary, directory
    )
    contracts["provider_directory_preview_probe"] = selection._provider_directory_preview_probe(
        binary, directory
    )
    contracts["language_rule_probe"] = selection._language_rule_probe(binary, version, directory)
    contracts["csharp_context_probe"] = selection._csharp_context_probe(binary, directory)
    contracts["clojure_context_probe"] = selection._clojure_context_probe(binary, directory)
    contracts["comparison_sides_probe"] = comparison.comparison_sides_probe(binary, directory)
    contracts["completion_cap_probe"] = numeric._completion_cap_probe(binary, directory)
    contracts["reasoning_effort_probe"] = numeric._reasoning_effort_probe(binary, directory)
    contracts["stream_override_probe"] = wire_controls.stream_override_probe(binary, directory)
    contracts["comment_arguments_probe"] = comment_checks._comment_arguments_probe(
        binary, directory
    )
    contracts["comment_thinking_probe"] = thinking_probe
    contract_rules._validate_contracts_for_version(version, contracts)
    return contracts
