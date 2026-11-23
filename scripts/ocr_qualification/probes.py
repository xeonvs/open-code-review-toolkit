"""Compose candidate-owned contract observations from real OCR probes."""

from __future__ import annotations

import json
import os
import re
import stat
from pathlib import Path
from typing import Any

from . import (
    comments as comment_checks,
)
from . import contracts as contract_rules
from . import (
    core,
    execution,
    handoffs,
    numeric,
    peer,
    selection,
    settings,
    wire_controls,
)


def _result_object(output: str, *, reason: str) -> dict[str, Any]:
    try:
        value = json.loads(output)
    except json.JSONDecodeError as exc:
        raise core.QualificationContractMismatch(
            "candidate did not emit JSON", reason=reason
        ) from exc
    if not isinstance(value, dict):
        raise core.QualificationContractMismatch(
            "candidate did not emit a JSON object", reason=reason
        )
    return value


def _fixture_selection(output: str) -> bool:
    payload = _result_object(output, reason="invalid-preview")
    files = payload.get("files")
    if not isinstance(files, list) or any(not isinstance(item, dict) for item in files):
        raise core.QualificationContractMismatch(
            "invalid preview inventory", reason="invalid-preview"
        )
    matches = [item for item in files if item.get("path") == "example.py"]
    if len(matches) != 1 or not isinstance(matches[0].get("will_review"), bool):
        raise core.QualificationContractMismatch(
            "preview lost the changed file", reason="invalid-preview"
        )
    return matches[0]["will_review"]


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
    flags = set(re.findall(r"^\s+(?:-\w, )?(--[a-z0-9-]+)(?:\s|$)", help_output, re.M))
    missing = sorted(settings.REQUIRED_REVIEW_FLAGS - flags)
    if missing:
        raise core.QualificationContractMismatch(
            f"missing CLI flags: {missing}", reason="cli-contract"
        )
    preview_home = directory / "preview-home"
    preview_env = execution._isolated_probe_environment(preview_home)
    preview_command = [str(binary), "review", "--from", base, "--to", head, "--preview"]
    preview_command.extend(["--format", "json"])
    preview = execution._run(preview_command, cwd=repo, env=preview_env)
    if not _fixture_selection(preview):
        raise core.QualificationContractMismatch(
            "preview excluded the changed file", reason="invalid-preview"
        )
    if os.path.lexists(preview_home / ".opencodereview" / "sessions"):
        raise core.QualificationContractMismatch(
            "candidate preview created a review session store", reason="invalid-preview"
        )

    user_rules = directory / "user-rules.json"
    user_rules.write_bytes(core.canonical_json({"exclude": ["example.py"]}))
    excluded = execution._run(
        [*preview_command, "--rule", str(user_rules)], cwd=repo, env=preview_env
    )
    if _fixture_selection(excluded):
        raise core.QualificationContractMismatch("user exclusion ignored", reason="invalid-preview")

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
    sample = _result_object(result_output, reason="invalid-result")
    try:
        optional_capabilities = contract_rules.detect_optional_capabilities(help_output, sample)
    except core.CompatibilityError as exc:
        raise core.QualificationContractMismatch(str(exc), reason="invalid-result") from exc
    from ocr_toolkit.result_contract import OcrResultContractError, parse_result_outcome

    try:
        outcome = parse_result_outcome(sample)
    except OcrResultContractError as exc:
        raise core.QualificationContractMismatch(
            "invalid review result", reason="invalid-result"
        ) from exc
    if outcome.kind != "clean":
        raise core.QualificationContractMismatch(
            "synthetic clean review failed", reason="invalid-result"
        )
    comments = sample.get("comments")
    if not isinstance(comments, list) or len(comments) != 1 or not isinstance(comments[0], dict):
        raise core.QualificationContractMismatch(
            "candidate full review did not emit the synthetic comment", reason="invalid-result"
        )
    from ocr_toolkit.review_range import ReviewRange, admit_native_range

    try:
        if admit_native_range(sample, ReviewRange(base, head)) is None:
            raise OcrResultContractError("missing native range")
    except OcrResultContractError as exc:
        raise core.QualificationContractMismatch(
            "result range mismatch", reason="range-contract"
        ) from exc
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
        raise core.QualificationContractMismatch(
            "posting rejected the synthetic finding", reason="publication-contract"
        )
    token_summary = format_token_usage_summary(sample)
    if not token_summary or "total" not in token_summary:
        raise core.QualificationContractMismatch(
            "toolkit token summary rejected the candidate result", reason="publication-contract"
        )
    if not format_tool_calls_summary(sample.get("tool_calls")):
        raise core.QualificationContractMismatch(
            "toolkit tool-call summary rejected the candidate result", reason="publication-contract"
        )
    if "Synthetic private compatibility reasoning." in rendered:
        raise core.QualificationContractMismatch(
            "toolkit posting consumer exposed private thinking", reason="publication-contract"
        )
    demonstrated = handoffs.consumer_handoffs(binary, version, directory)
    if handoffs.chatgpt_auth_handoff(binary, repo, base, head, directory):
        demonstrated.append("chatgpt_auth")
    if "--analysis" in flags:
        from ocr_toolkit.review_analysis import admit_analysis

        with peer._stub_gateway() as gateway:
            env["OCR_LLM_URL"] = gateway
            combined = _result_object(
                execution._run(
                    [
                        str(binary),
                        "review",
                        "--from",
                        base,
                        "--to",
                        head,
                        "--analysis",
                        "--analysis-max-tokens-budget",
                        "10000",
                        "--format",
                        "json",
                        "--audience",
                        "agent",
                        "--concurrency",
                        "1",
                    ],
                    cwd=repo,
                    env=env,
                ),
                reason="analysis-contract",
            )
        meta = combined.get("analysis_meta")
        if not isinstance(meta, dict):
            raise core.QualificationContractMismatch(
                "advertised Analysis did not emit report metadata", reason="analysis-contract"
            )
        observations = meta.get("observation_ids")
        citations = meta.get("cited_observation_ids")
        try:
            admitted = admit_analysis(combined, requested=True, forbidden=())
            combined_outcome = parse_result_outcome(combined)
        except ValueError as exc:
            raise core.QualificationContractMismatch(
                "toolkit rejected combined Analysis result", reason="analysis-contract"
            ) from exc
        if (
            admitted is not None
            and admitted.get("status") == "completed"
            and admitted.get("declared_completion") == "partial"
            and isinstance(markdown := admitted.get("markdown"), str)
            and "The example return value changed." in markdown
            and isinstance(observations, list)
            and isinstance(citations, list)
            and bool(citations)
            and all(citation in observations for citation in citations)
            and admitted.get("usage")
            and combined_outcome.kind == "clean"
        ):
            demonstrated.append("analysis")
        else:
            raise core.QualificationContractMismatch(
                "advertised Analysis did not complete the controlled report exchange",
                reason="analysis-contract",
            )

    budget = numeric._budget_result_probe(binary, directory)
    numeric_cli = numeric._numeric_cli_probe(binary, repo, base, head, directory)
    cap = numeric._completion_cap_probe(binary, directory)
    effort = numeric._reasoning_effort_probe(binary, directory)
    stream = wire_controls.stream_override_probe(binary, directory)
    comment_arguments = comment_checks._comment_arguments_probe(binary, directory)
    contracts = {
        "checks": {
            "identity": "passed",
            "range_preview": "passed",
            "user_exclusion": "passed",
            "review_result": "passed",
            "publication": "passed",
            "budget_partial": "passed",
            "numeric_controls": "passed",
            "provider_controls": "passed",
            "mcp": "passed",
        },
        "native_handoffs": sorted(demonstrated),
        "optional_capabilities": optional_capabilities,
        "observations": {
            "builtin_selection": selection._language_rule_probe(binary, version, directory),
            "budget": budget,
            "numeric_cli": numeric_cli,
            "completion_cap": cap,
            "reasoning_effort": effort,
            "stream_override": stream,
            "comment_arguments": comment_arguments,
        },
    }
    contract_rules._validate_contracts_for_version(version, contracts)
    return contracts
