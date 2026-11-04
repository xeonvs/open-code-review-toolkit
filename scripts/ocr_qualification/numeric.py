"""Observe effective OCR numeric controls through real CLI and wire requests."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from . import contracts, core, execution, peer, settings


def _budget_result_probe(binary: Path, directory: Path) -> dict[str, object]:
    """Drive the real OCR review budget gate and validate its partial manifest."""

    git_env = execution._isolated_probe_environment(directory / "budget-git-home")
    repo = directory / "budget-review"
    repo.mkdir()
    execution._run(["git", "init", "--initial-branch=main"], cwd=repo, env=git_env)
    execution._run(["git", "config", "user.name", "Synthetic Reviewer"], cwd=repo, env=git_env)
    execution._run(["git", "config", "user.email", "reviewer@example.com"], cwd=repo, env=git_env)
    paths = ("first.py", "second.py", "third.py")
    for name in paths:
        (repo / name).write_text(
            "def value():\n    return 1\n" + "# baseline\n" * 34,
            encoding="utf-8",
        )
    execution._run(["git", "add", "first.py", "second.py", "third.py"], cwd=repo, env=git_env)
    execution._run(["git", "commit", "-m", "budget baseline"], cwd=repo, env=git_env)
    base = execution._run(["git", "rev-parse", "HEAD"], cwd=repo, env=git_env).strip()
    for name in paths:
        (repo / name).write_text(
            "def value():\n    return 2\n" + "# changed\n" * 34,
            encoding="utf-8",
        )
    execution._run(["git", "commit", "-am", "budget changes"], cwd=repo, env=git_env)
    head = execution._run(["git", "rev-parse", "HEAD"], cwd=repo, env=git_env).strip()

    home = directory / "budget-review-home"
    env = execution._isolated_probe_environment(home)
    with peer._stub_gateway(
        tokens_per_request=20_000,
    ) as gateway_url:
        env.update(
            {
                "OCR_LLM_URL": gateway_url,
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
                "--format",
                "json",
                "--audience",
                "agent",
                "--concurrency",
                "1",
                "--max-tokens-budget",
                "30000",
            ],
            cwd=repo,
            env=env,
        )
        grouping_inventories = list(peer._StubHandler.grouping_inventories)
        request_stages = list(peer._StubHandler.request_stages)
    try:
        sample = json.loads(output)
    except json.JSONDecodeError as exc:
        raise core.CompatibilityError("budget-limited review did not emit JSON") from exc
    if not isinstance(sample, dict):
        core._fail("budget-limited review emitted an unsupported result object")
    summary = sample.get("summary")
    if not isinstance(summary, dict) or summary.get("budget_exceeded") is not True:
        core._fail("budget-limited review omitted summary.budget_exceeded")

    from ocr_toolkit.result_contract import OcrResultContractError, parse_result_outcome

    try:
        outcome = parse_result_outcome(sample)
    except OcrResultContractError as exc:
        raise core.CompatibilityError(
            f"budget-limited review emitted an unsupported result object: {exc}"
        ) from exc
    if (
        outcome.kind != "partial"
        or not outcome.budget_exceeded
        or outcome.selected_count != 3
        or outcome.completed_count != 2
        or outcome.failed_count != 1
        or len(outcome.failed_items) != 1
        or outcome.failed_items[0].classification != "budget"
    ):
        core._fail("real OCR budget gate did not produce the expected partial coverage contract")
    warnings = sample.get("warnings")
    if not isinstance(warnings, list) or not any(
        isinstance(warning, dict) and warning.get("type") == "token_budget_reached"
        for warning in warnings
    ):
        core._fail("budget-limited review omitted the token_budget_reached warning")
    comments = sample.get("comments")
    if not isinstance(comments, list) or len(comments) != 2:
        core._fail("budget-limited review did not preserve its completed finding")
    contracts._validate_file_groups(sample.get("groups"), set(paths))
    groups = sample["groups"]
    if any(len(group.get("files", [])) != 1 for group in groups):
        core._fail("budget-limited review did not preserve per-file group boundaries")
    grouping_requests = request_stages.count("grouping")
    if grouping_requests != 0:
        core._fail("budget-limited review emitted an unexpected grouping request count")
    if grouping_inventories:
        core._fail("budget-limited small-change review unexpectedly emitted a grouping inventory")
    result: dict[str, object] = {
        "budget": 30_000,
        "completed": 2,
        "failed_budget": 1,
        "partial_findings_preserved": True,
        "result": "passed",
        "selected": 3,
    }
    result.update({"grouping_requests": 0, "grouping_strategy": "per_file"})
    return result


def _run_numeric_preview_case(
    binary: Path,
    repo: Path,
    base: str,
    head: str,
    directory: Path,
    *,
    flag: str,
    value: int | None,
) -> subprocess.CompletedProcess[str]:
    """Run one bounded no-model numeric CLI preview and retain diagnostics privately."""

    case_name = "omitted" if value is None else str(value).replace("-", "negative-")
    env = execution._isolated_probe_environment(
        directory / f"numeric-{flag.removeprefix('--')}-{case_name}"
    )
    command = [
        str(binary),
        "review",
        "--from",
        base,
        "--to",
        head,
        "--preview",
        "--format",
        "json",
    ]
    if value is not None:
        command.extend([flag, str(value)])
    try:
        completed = subprocess.run(  # nosec B603
            command,
            cwd=repo,
            env=env,
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise core.CompatibilityError(f"numeric CLI preview failed for {flag}") from exc
    if (
        len(completed.stdout.encode()) > settings.MAX_CLI_PROBE_BYTES
        or len(completed.stderr.encode()) > settings.MAX_CLI_PROBE_BYTES
    ):
        core._fail(f"numeric CLI preview exceeded its output bound for {flag}")
    return completed


def _accepted_numeric_preview(completed: subprocess.CompletedProcess[str], *, flag: str) -> None:
    """Require one clean accepted numeric preview without trusting help text."""

    if completed.returncode != 0 or completed.stderr:
        core._fail(f"candidate {flag} preview did not pass without diagnostics")
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise core.CompatibilityError(f"candidate {flag} preview did not emit JSON") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("files"), list):
        core._fail(f"candidate {flag} preview emitted an invalid file manifest")


def _effective_max_tools_probe(
    binary: Path,
    repo: Path,
    base: str,
    head: str,
    directory: Path,
    *,
    value: int | None,
    expected_diagnostic: re.Pattern[str] | None,
    grace_task_done: bool = True,
) -> tuple[int, dict[str, object]]:
    """Count real OCR main-loop rounds through a deterministic local protocol peer."""

    mode = "exhaust-tools" if grace_task_done else "exhaust-tools-incomplete"
    env = execution._isolated_probe_environment(directory / f"effective-max-tools-{value}-{mode}")
    command = [
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
    ]
    if value is not None:
        command.extend(["--max-tools", str(value)])
    with peer._stub_gateway(main_mode=mode) as gateway_url:
        env.update(
            {
                "OCR_LLM_URL": gateway_url,
                "OCR_LLM_TOKEN": "synthetic-token",
                "OCR_LLM_MODEL": "synthetic-model",
                "OCR_LLM_PROTOCOL": "openai",
                "OCR_TELEMETRY_ENABLED": "false",
            }
        )
        try:
            completed = subprocess.run(  # nosec B603
                command,
                cwd=repo,
                env=env,
                check=False,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise core.CompatibilityError("effective max-tools probe failed") from exc
        stages = tuple(peer._StubHandler.request_stages)
    if (
        len(completed.stdout.encode()) > settings.MAX_CLI_PROBE_BYTES
        or len(completed.stderr.encode()) > settings.MAX_CLI_PROBE_BYTES
    ):
        core._fail("effective max-tools probe exceeded its output bound")
    first_diagnostic = completed.stderr.partition("\n")[0]
    if expected_diagnostic is None:
        if first_diagnostic.startswith("[ocr] --max-tools"):
            core._fail("effective max-tools probe returned an unexpected normalization")
    elif expected_diagnostic.fullmatch(f"{first_diagnostic}\n") is None:
        core._fail("effective max-tools probe did not retain the qualified normalization")
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise core.CompatibilityError("effective max-tools probe did not emit JSON") from exc
    tool_calls = payload.get("tool_calls") if isinstance(payload, dict) else None
    by_tool = tool_calls.get("by_tool") if isinstance(tool_calls, dict) else None
    observed = stages.count("main")
    if (
        completed.returncode not in {0, 1}
        or observed <= 0
        or stages.count("grace") != 1
        or len(stages) != observed + 1
        or not isinstance(by_tool, dict)
        or by_tool.get("file_read") != observed
        or tool_calls.get("total") != observed
    ):
        core._fail("effective max-tools probe returned an inconsistent tool-loop result")
    manifest = payload.get("manifest") if isinstance(payload, dict) else None
    execution_facts = manifest.get("execution") if isinstance(manifest, dict) else None
    if (
        not isinstance(execution_facts, dict)
        or type(execution_facts.get("max_tool_request_times")) is not int
        or execution_facts["max_tool_request_times"] != observed
    ):
        core._fail("effective max-tools manifest limit disagrees with observed rounds")
    from ocr_toolkit.result_contract import OcrResultContractError, parse_result_outcome

    try:
        outcome = parse_result_outcome(payload)
    except OcrResultContractError as exc:
        raise core.CompatibilityError("effective max-tools probe emitted invalid coverage") from exc
    completed_task = outcome.kind == "clean"
    if (
        not outcome.manifest_present
        or outcome.selected_count != 1
        or outcome.reused_count != 0
        or outcome.waived_count != 0
        or outcome.completed_count != int(completed_task)
        or outcome.failed_count != int(not completed_task)
        or completed.returncode != (0 if completed_task else 1)
        or (
            not completed_task
            and (
                outcome.kind != "failed"
                or len(outcome.failed_items) != 1
                or outcome.failed_items[0].classification != "budget"
            )
        )
        or (completed_task and outcome.budget_exceeded)
        or (completed_task and not grace_task_done)
    ):
        core._fail("effective max-tools probe returned inconsistent grace coverage")
    warnings = payload.get("warnings", [])
    if not isinstance(warnings, list) or any(not isinstance(item, dict) for item in warnings):
        core._fail("effective max-tools probe returned invalid warnings")
    limit_warnings = [item for item in warnings if item.get("type") == "review_limit_reached"]
    if len(limit_warnings) > 1:
        core._fail("effective max-tools probe repeated its limit warning")
    if limit_warnings:
        verdict = (
            "the grace round completed the task"
            if completed_task
            else "the grace round did not complete the task"
        )
        message = limit_warnings[0].get("message")
        if not isinstance(message, str) or verdict not in message:
            core._fail("effective max-tools probe returned an inconsistent limit warning")
    if completed_task and any(item.get("type") == "subtask_error" for item in warnings):
        core._fail("effective max-tools probe reported a completed task as failed")
    return observed, {"completed": completed_task, "limit_warning": bool(limit_warnings)}


def _numeric_cli_probe(
    binary: Path, repo: Path, base: str, head: str, directory: Path
) -> dict[str, object]:
    """Qualify closed numeric CLI boundaries and the resulting effective semantics."""

    max_tools_omitted = _run_numeric_preview_case(
        binary, repo, base, head, directory, flag="--max-tools", value=None
    )
    max_tools_sentinel = _run_numeric_preview_case(
        binary, repo, base, head, directory, flag="--max-tools", value=0
    )
    max_tools_invalid = _run_numeric_preview_case(
        binary, repo, base, head, directory, flag="--max-tools", value=-1
    )
    discovery = _run_numeric_preview_case(
        binary, repo, base, head, directory, flag="--max-tools", value=1
    )
    for completed in (max_tools_omitted, max_tools_sentinel):
        _accepted_numeric_preview(completed, flag="--max-tools")
    if (
        max_tools_invalid.returncode == 0
        or settings.MAX_TOOLS_NEGATIVE_RE.fullmatch(max_tools_invalid.stderr) is None
    ):
        core._fail("candidate max-tools negative boundary did not fail closed")
    normalization = settings.MAX_TOOLS_NORMALIZATION_RE.fullmatch(discovery.stderr)
    if discovery.returncode != 0 or normalization is None:
        core._fail("candidate max-tools minimum could not be qualified behaviorally")
    requested, minimum, normalized = (int(value) for value in normalization.groups())
    if requested != 1 or minimum <= 1 or normalized != minimum:
        core._fail("candidate max-tools minimum diagnostic is inconsistent")
    below = minimum - 1
    below_preview = _run_numeric_preview_case(
        binary, repo, base, head, directory, flag="--max-tools", value=below
    )
    below_match = settings.MAX_TOOLS_NORMALIZATION_RE.fullmatch(below_preview.stderr)
    if (
        below_preview.returncode != 0
        or below_match is None
        or tuple(int(value) for value in below_match.groups()) != (below, minimum, minimum)
    ):
        core._fail("candidate max-tools minimum-minus-one boundary is inconsistent")
    minimum_preview = _run_numeric_preview_case(
        binary, repo, base, head, directory, flag="--max-tools", value=minimum
    )
    _accepted_numeric_preview(minimum_preview, flag="--max-tools")
    observed_cases: dict[str, dict[str, object]] = {}
    grace_completion: dict[str, object] | None = None
    for name, requested_value in (
        ("omitted", None),
        ("sentinel", 0),
        ("minimum", minimum),
        ("minimum_minus_one", below),
        ("lower_override", 75),
        ("template_value", 100),
        ("representative", 125),
    ):
        if name in {"lower_override", "template_value", "representative"}:
            _accepted_numeric_preview(
                _run_numeric_preview_case(
                    binary, repo, base, head, directory, flag="--max-tools", value=requested_value
                ),
                flag="--max-tools",
            )
        rounds, verdict = _effective_max_tools_probe(
            binary,
            repo,
            base,
            head,
            directory,
            value=requested_value,
            expected_diagnostic=settings.MAX_TOOLS_NORMALIZATION_RE
            if name == "minimum_minus_one"
            else None,
        )
        if grace_completion is None:
            grace_completion = verdict
        elif verdict != grace_completion:
            core._fail("candidate max-tools grace verdict changed with the numeric boundary")
        if name not in {"omitted", "sentinel"} and rounds != max(minimum, requested_value):
            core._fail("candidate max-tools override was not applied exactly")
        observed_cases[name] = {
            "effective": rounds,
            "input": requested_value,
            "outcome": "normalized" if name == "minimum_minus_one" else "accepted",
        }
        if name == "minimum_minus_one":
            observed_cases[name]["reported_normalization"] = minimum
    template_default = observed_cases["omitted"]["effective"]
    if observed_cases["sentinel"]["effective"] != template_default or template_default < minimum:
        core._fail("candidate max-tools sentinel/default observations disagree")
    observed_cases["invalid_below"] = {"effective": None, "input": -1, "outcome": "rejected"}
    incomplete_rounds, grace_incomplete = _effective_max_tools_probe(
        binary,
        repo,
        base,
        head,
        directory,
        value=minimum,
        expected_diagnostic=None,
        grace_task_done=False,
    )
    if incomplete_rounds != minimum:
        core._fail("candidate max-tools non-completion changed the effective round limit")

    budget_cases: dict[str, subprocess.CompletedProcess[str]] = {
        "omitted": _run_numeric_preview_case(
            binary, repo, base, head, directory, flag="--max-tokens-budget", value=None
        ),
        "sentinel": _run_numeric_preview_case(
            binary, repo, base, head, directory, flag="--max-tokens-budget", value=0
        ),
        "invalid_below": _run_numeric_preview_case(
            binary, repo, base, head, directory, flag="--max-tokens-budget", value=-1
        ),
        "minimum": _run_numeric_preview_case(
            binary, repo, base, head, directory, flag="--max-tokens-budget", value=1
        ),
        "representative": _run_numeric_preview_case(
            binary, repo, base, head, directory, flag="--max-tokens-budget", value=30_000
        ),
    }
    for name in ("omitted", "sentinel", "minimum", "representative"):
        _accepted_numeric_preview(budget_cases[name], flag="--max-tokens-budget")
    if (
        budget_cases["invalid_below"].returncode == 0
        or settings.MAX_TOKENS_BUDGET_NEGATIVE_RE.fullmatch(budget_cases["invalid_below"].stderr)
        is None
    ):
        core._fail("candidate max-tokens-budget negative boundary did not fail closed")
    return {
        "grace_rounds": {"task_done": grace_completion, "no_task_done": grace_incomplete},
        "max_tokens_budget": {
            "cases": {
                "invalid_below": {"effective": None, "input": -1, "outcome": "rejected"},
                "minimum": {"effective": 1, "input": 1, "outcome": "accepted"},
                "omitted": {"effective": "unlimited", "input": None, "outcome": "accepted"},
                "representative": {
                    "effective": 30_000,
                    "input": 30_000,
                    "outcome": "accepted",
                },
                "sentinel": {"effective": "unlimited", "input": 0, "outcome": "accepted"},
            },
            "maximum": None,
            "owner": "ocr-cli",
        },
        "max_tools": {
            "cases": observed_cases,
            "maximum": None,
            "owner": "ocr-cli-or-template-default",
            "reported_minimum": minimum,
            "manifest_limit_verified": True,
        },
        "result": "passed",
    }


def _completion_cap_probe(binary: Path, directory: Path) -> dict[str, object]:
    """Observe the real OCR chat-completions output cap with and without an override."""

    probe_root = directory / "completion-cap-probe"
    probe_root.mkdir()
    git_env = execution._isolated_probe_environment(probe_root / "git-home")
    repo, base, head = execution._synthetic_repo(probe_root, git_env)
    observed: dict[str, int] = {}
    inherited = 16_384
    for label, expected in (("inherited", inherited), ("explicit", 4_096)):
        env = execution._isolated_probe_environment(probe_root / f"{label}-home")
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
            from ocr_toolkit.config_writer import write_ocr_config

            llm_config: dict[str, object] = {
                "auth_token": "synthetic-token",
                "model": "synthetic-model",
                "protocol": "openai",
                "url": gateway_url,
                "use_anthropic": False,
            }
            if label == "explicit":
                llm_config["extra_body"] = {"max_completion_tokens": expected}
            write_ocr_config(
                {"llm": llm_config, "telemetry": {"enabled": False}},
                Path(env["HOME"]) / ".opencodereview" / "config.json",
            )
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
        caps = peer._StubHandler.completion_caps
        if not caps or any(value != expected for value in caps):
            core._fail(f"OCR completion-cap {label} probe expected {expected}, observed {caps!r}")
        observed[label] = expected
    return {
        "explicit": observed["explicit"],
        "inherited": observed["inherited"],
        "result": "passed",
        "wire_field": "max_completion_tokens",
    }


def _reasoning_effort_probe(binary: Path, directory: Path) -> dict[str, object]:
    """Capture real OCR effort fields without claiming provider/model acceptance."""

    from ocr_toolkit.config_writer import write_ocr_config
    from ocr_toolkit.provider_config import request_controls_from_environment

    root = directory / "reasoning-effort-probe"
    root.mkdir()
    git_env = execution._isolated_probe_environment(root / "git-home")
    repo, base, head = execution._synthetic_repo(root, git_env)
    for protocol in ("openai", "openai-responses"):
        for effort in ("", "none", "high"):
            label = effort or "unset"
            env = execution._isolated_probe_environment(root / f"{protocol}-{label}-home")
            settings = {"OCR_LLM_PROTOCOL": protocol, "OCR_LLM_REASONING_EFFORT": effort}
            if protocol == "openai-responses" and effort:
                settings["OCR_LLM_EXTRA_BODY"] = '{"reasoning":{"summary":"auto"}}'
            controls = request_controls_from_environment(settings)
            with peer._stub_gateway(capture_reasoning=True) as gateway_url:
                config: dict[str, object] = {
                    "auth_token": "synthetic-token",
                    "model": "synthetic-model",
                    "protocol": protocol,
                    "url": gateway_url,
                    "use_anthropic": False,
                }
                if controls.extra_body is not None:
                    config["extra_body"] = controls.extra_body
                write_ocr_config(
                    {"llm": config, "telemetry": {"enabled": False}},
                    Path(env["HOME"]) / ".opencodereview" / "config.json",
                )
                try:
                    completed = subprocess.run(  # nosec B603
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
                            "--effort",
                            "low",
                            "--concurrency",
                            "1",
                        ],
                        cwd=repo,
                        env=env,
                        check=False,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=30,
                    )
                except (OSError, subprocess.TimeoutExpired) as exc:
                    raise core.CompatibilityError(
                        f"reasoning wire probe did not finish: {protocol}/{label}"
                    ) from exc
                if completed.returncode < 0:
                    core._fail(f"reasoning wire probe was interrupted: {protocol}/{label}")
                observed = list(peer._StubHandler.reasoning_requests)
                overflow = peer._StubHandler.reasoning_overflow
            if overflow:
                core._fail(
                    f"reasoning wire probe exceeded its request capture limit: {protocol}/{label}"
                )
            if not observed:
                core._fail(f"reasoning wire probe received no request: {protocol}/{label}")
            expected_path = "/v1/chat/completions" if protocol == "openai" else "/v1/responses"
            prefix = "root" if protocol == "openai" else "nested"
            other_prefix = "nested" if protocol == "openai" else "root"
            for request in observed:
                if (
                    request["path"] != expected_path
                    or request[f"{other_prefix}_present"] is not False
                    or request[f"{prefix}_present"] is not bool(effort)
                    or request[f"{prefix}_effort"] != (effort or None)
                    or (protocol == "openai-responses" and effort and request["summary"] != "auto")
                ):
                    core._fail(
                        f"reasoning wire fields differ from configured controls: {protocol}/{label}"
                    )
    return {
        "result": "passed",
        "protocols": ["openai", "openai-responses"],
        "efforts": ["unset", "none", "high"],
        "responses_siblings_preserved": True,
        "provider_acceptance": "not-tested",
    }
