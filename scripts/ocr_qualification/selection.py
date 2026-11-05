"""Qualify native file selection, built-in Rules and semantic grouping."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from . import contracts, core, execution, peer, settings


def _semantic_grouping_probe(binary: Path, directory: Path) -> dict[str, object]:
    """Drive a threshold-crossing group through grouping and medium review rounds."""

    root = directory / "semantic-grouping-probe"
    root.mkdir()
    git_env = execution._isolated_probe_environment(root / "git-home")
    repo = root / "review"
    repo.mkdir()
    execution._run(["git", "init", "--initial-branch=main"], cwd=repo, env=git_env)
    execution._run(["git", "config", "user.name", "Synthetic Reviewer"], cwd=repo, env=git_env)
    execution._run(["git", "config", "user.email", "reviewer@example.com"], cwd=repo, env=git_env)
    paths = ("01-first.py", "02-second.py", "03-third.py", "04-fourth.py")
    for path in paths:
        (repo / path).write_text("def value():\n    return 1\n", encoding="utf-8")
    execution._run(["git", "add", *paths], cwd=repo, env=git_env)
    execution._run(["git", "commit", "-m", "grouping baseline"], cwd=repo, env=git_env)
    base = execution._run(["git", "rev-parse", "HEAD"], cwd=repo, env=git_env).strip()
    for path in paths:
        (repo / path).write_text("def value():\n    return 2\n", encoding="utf-8")
    execution._run(["git", "commit", "-am", "group related changes"], cwd=repo, env=git_env)
    head = execution._run(["git", "rev-parse", "HEAD"], cwd=repo, env=git_env).strip()

    from ocr_toolkit.evidence.project import MANDATORY_EVIDENCE_INSTRUCTION

    if settings.PRIOR_FINDING_RECHECK_MARKER not in MANDATORY_EVIDENCE_INSTRUCTION:
        core._fail("toolkit bootstrap lost the multi-round re-check instruction")
    background = root / "bootstrap.md"
    background.write_text(MANDATORY_EVIDENCE_INSTRUCTION, encoding="utf-8")

    env = execution._isolated_probe_environment(root / "review-home")
    with peer._stub_gateway(
        grouping_mode="combined",
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
                "--background-file",
                str(background),
                "--concurrency",
                "1",
            ],
            cwd=repo,
            env=env,
        )
        stages = list(peer._StubHandler.request_stages)
        completion_caps = list(peer._StubHandler.completion_caps)
        grouping_inventories = list(peer._StubHandler.grouping_inventories)
        prior_finding_semantics = set(peer._StubHandler.prior_finding_semantics)
        recheck_instruction_requests = peer._StubHandler.recheck_instruction_requests
    try:
        sample = json.loads(output)
    except json.JSONDecodeError as exc:
        raise core.CompatibilityError("semantic grouping review did not emit JSON") from exc
    if not isinstance(sample, dict):
        core._fail("semantic grouping review emitted an unsupported result object")
    contracts._validate_file_groups(sample.get("groups"), set(paths))
    groups = sample["groups"]
    if (
        len(groups) != 1
        or groups[0].get("label") != "compatibility-group"
        or groups[0].get("files") != list(paths)
    ):
        core._fail("semantic grouping review did not preserve the accepted group")
    if stages != ["grouping", "main", "main", "filter", "main"]:
        core._fail(f"default medium review emitted an unexpected stage sequence: {stages!r}")
    expected_inventory = [
        core.GroupingInventoryEntry(index, "MODIFIED", path, 1, 1)
        for index, path in enumerate(paths)
    ]
    if len(grouping_inventories) != 1:
        core._fail("semantic grouping review emitted an unexpected grouping inventory count")
    peer._require_exact_grouping_inventory(grouping_inventories[0], expected_inventory)
    expected_grouping_cap = 16_384
    if len(completion_caps) != len(stages) or completion_caps[0] != expected_grouping_cap:
        core._fail(
            "semantic grouping review emitted an unexpected grouping completion cap: "
            f"{completion_caps!r}"
        )
    result: dict[str, object] = {
        "default_effort": "medium",
        "filter_requests": 1,
        "grouping_requests": 1,
        "main_requests": 3,
        "result": "passed",
        "review_rounds": 2,
    }
    result["grouping_completion_cap"] = expected_grouping_cap
    if prior_finding_semantics != {"filter_survivors_as_confirmed"}:
        core._fail("multi-round review did not expose the qualified prior-finding semantics")
    if recheck_instruction_requests != 3:
        core._fail("multi-round review did not retain toolkit re-check guidance in every round")
    result["prior_finding_semantics"] = "filter_survivors_as_confirmed"
    result["recheck_instruction_requests"] = recheck_instruction_requests
    result["files"] = len(paths)
    return result


def _csharp_context_probe(binary: Path, directory: Path) -> dict[str, object]:
    """Read unchanged C# project context through actual native file tools."""

    root = directory / "csharp-context-probe"
    root.mkdir()
    git_env = execution._isolated_probe_environment(root / "git-home")
    context = {
        "app/Project.csproj": "<Project><PropertyGroup><TargetFramework>net10.0</TargetFramework><Nullable>enable</Nullable></PropertyGroup></Project>",
        "Directory.Build.props": "<Project><PropertyGroup><LangVersion>14.0</LangVersion></PropertyGroup></Project>",
        "global.json": '{"sdk":{"version":"10.0.100"}}',
    }
    repo, base, head = execution._synthetic_repo(
        root,
        git_env,
        source_path="app/Program.cs",
        baseline="public class Program { public static int Value() => 1; }\n",
        changed="public class Program { public static int Value() => 2; }\n",
        context_files=context,
    )
    env = execution._isolated_probe_environment(root / "review-home")
    expected_context = {
        "app/Project.csproj": (
            "<TargetFramework>net10.0</TargetFramework>",
            "<Nullable>enable</Nullable>",
        ),
        "Directory.Build.props": ("<LangVersion>14.0</LangVersion>",),
        "global.json": ("10.0.100",),
    }
    with peer._stub_gateway(context_reads=expected_context) as gateway_url:
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
        observed = set(peer._StubHandler.observed_context_reads)
        rules_seen = peer._StubHandler.observed_csharp_rules
    try:
        result = json.loads(output)
    except json.JSONDecodeError as exc:
        raise core.CompatibilityError("C# context review did not emit JSON") from exc
    if observed != set(context):
        core._fail(f"native C# context reads were incomplete: {sorted(set(context) - observed)!r}")
    if not rules_seen:
        core._fail("native C# main request omitted the qualified Rules")
    from ocr_toolkit.result_contract import OcrResultContractError, parse_result_outcome

    try:
        outcome = parse_result_outcome(result)
    except OcrResultContractError as exc:
        raise core.CompatibilityError(
            "native C# context review returned an invalid outcome"
        ) from exc
    if outcome.kind != "clean" or outcome.selected_count != 1 or outcome.completed_count != 1:
        core._fail("native C# context review did not complete its exact selected file")
    return {
        "result": "passed",
        "rules_in_main_request": True,
        "context_paths": sorted(context),
        "execution": "read-only-native-tools",
    }


def _small_change_grouping_probe(binary: Path, directory: Path) -> dict[str, object]:
    """Prove OCR keeps below-threshold grouping local and deterministic."""

    scenarios = (
        ("single_file", ("single.py",), 1, "per_file"),
        ("low_churn", ("first.py", "second.py"), 1, "bundle_all"),
        ("high_churn", ("first.py", "second.py"), 50, "per_file"),
    )
    observed: dict[str, str] = {}
    for name, paths, lines, expected_strategy in scenarios:
        root = directory / f"small-change-{name}"
        root.mkdir()
        git_env = execution._isolated_probe_environment(root / "git-home")
        repo = root / "review"
        repo.mkdir()
        execution._run(["git", "init", "--initial-branch=main"], cwd=repo, env=git_env)
        execution._run(["git", "config", "user.name", "Synthetic Reviewer"], cwd=repo, env=git_env)
        execution._run(
            ["git", "config", "user.email", "reviewer@example.com"], cwd=repo, env=git_env
        )
        for path in paths:
            (repo / path).write_text(
                "def value():\n    return 1\n" + "# baseline\n" * lines,
                encoding="utf-8",
            )
        execution._run(["git", "add", *paths], cwd=repo, env=git_env)
        execution._run(["git", "commit", "-m", "small-change baseline"], cwd=repo, env=git_env)
        base = execution._run(["git", "rev-parse", "HEAD"], cwd=repo, env=git_env).strip()
        for path in paths:
            (repo / path).write_text(
                "def value():\n    return 2\n" + "# changed\n" * lines,
                encoding="utf-8",
            )
        execution._run(["git", "commit", "-am", "small-change update"], cwd=repo, env=git_env)
        head = execution._run(["git", "rev-parse", "HEAD"], cwd=repo, env=git_env).strip()
        env = execution._isolated_probe_environment(root / "review-home")
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
                    "--effort",
                    "low",
                    "--concurrency",
                    "1",
                ],
                cwd=repo,
                env=env,
            )
            request_stages = list(peer._StubHandler.request_stages)
            grouping_inventories = list(peer._StubHandler.grouping_inventories)
        try:
            sample = json.loads(output)
        except json.JSONDecodeError as exc:
            raise core.CompatibilityError("small-change grouping review did not emit JSON") from exc
        if not isinstance(sample, dict):
            core._fail("small-change grouping review emitted an unsupported result object")
        contracts._validate_file_groups(sample.get("groups"), set(paths))
        groups = sample["groups"]
        actual_strategy = "bundle_all" if len(groups) == 1 and len(paths) > 1 else "per_file"
        if (
            actual_strategy != expected_strategy
            or "grouping" in request_stages
            or grouping_inventories
        ):
            core._fail(f"small-change grouping scenario {name} violated its local strategy")
        observed[name] = actual_strategy
    return {
        "grouping_requests": 0,
        "high_churn": observed["high_churn"],
        "low_churn": observed["low_churn"],
        "result": "passed",
        "single_file": observed["single_file"],
        "threshold_files": 4,
    }


def _preview_file_selection(payload: object, path: str) -> tuple[bool, object]:
    """Return one JSON preview file's selected state and closed exclusion reason."""

    if not isinstance(payload, dict):
        core._fail("target-rule preview must be a JSON object")
    files = payload.get("files")
    if not isinstance(files, list):
        core._fail("target-rule preview emitted an invalid file manifest")
    records = [item for item in files if isinstance(item, dict) and item.get("path") == path]
    if len(records) != 1:
        core._fail("target-rule preview did not report the synthetic changed file exactly once")
    return records[0].get("will_review") is True, records[0].get("exclude_reason")


def _selected_preview_paths(payload: object) -> set[str]:
    """Return selected paths from a language preview after validating their shape."""

    if not isinstance(payload, dict):
        core._fail("language preview must be a JSON object")
    files = payload.get("files")
    if not isinstance(files, list):
        core._fail("language preview emitted an invalid file manifest")
    selected: set[str] = set()
    for item in files:
        if not isinstance(item, dict) or item.get("will_review") is not True:
            continue
        path = item.get("path")
        if not isinstance(path, str):
            core._fail("language preview selected a file with an invalid path")
        selected.add(path)
    return selected


def _provider_directory_preview_probe(binary: Path, directory: Path) -> dict[str, object]:
    """Prove the tracked provider-directory preview transition on an exact range."""

    root = directory / "provider-directory-preview"
    root.mkdir()
    git_env = execution._isolated_probe_environment(root / "git-home")
    repo = root / "review"
    repo.mkdir()
    execution._run(["git", "init", "--initial-branch=main"], cwd=repo, env=git_env)
    execution._run(["git", "config", "user.name", "Synthetic Reviewer"], cwd=repo, env=git_env)
    execution._run(["git", "config", "user.email", "reviewer@example.com"], cwd=repo, env=git_env)
    paths = ("src/main.py", "vendor/dependency.py")
    for path in paths:
        target = repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("value = 1\n", encoding="utf-8")
    execution._run(["git", "add", *paths], cwd=repo, env=git_env)
    execution._run(["git", "commit", "-m", "preview baseline"], cwd=repo, env=git_env)
    base = execution._run(["git", "rev-parse", "HEAD"], cwd=repo, env=git_env).strip()
    for path in paths:
        (repo / path).write_text("value = 2\n", encoding="utf-8")
    execution._run(["git", "commit", "-am", "preview changes"], cwd=repo, env=git_env)
    head = execution._run(["git", "rev-parse", "HEAD"], cwd=repo, env=git_env).strip()
    env = execution._isolated_probe_environment(root / "review-home")
    output = execution._run(
        [
            str(binary),
            "review",
            "--from",
            base,
            "--to",
            head,
            "--preview",
            "--format",
            "json",
        ],
        cwd=repo,
        env=env,
    )
    try:
        payload = json.loads(output)
    except json.JSONDecodeError as exc:
        raise core.CompatibilityError("provider-directory preview did not emit JSON") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("files"), list):
        core._fail("provider-directory preview emitted an invalid file manifest")
    file_records = payload["files"]
    if any(
        not isinstance(item, dict) or not isinstance(item.get("path"), str) for item in file_records
    ):
        core._fail("provider-directory preview emitted an invalid file record")
    records = {item["path"]: item for item in file_records}
    selected = records.get("src/main.py")
    if not isinstance(selected, dict) or selected.get("will_review") is not True:
        core._fail("provider-directory preview omitted the reviewable control file")
    expected_paths = set(paths)
    if len(records) != len(file_records) or set(records) != expected_paths:
        core._fail("provider-directory preview changed its exact tracked-file inventory")
    provider_record = records.get("vendor/dependency.py")
    expected_counts = (2, 1, 1)
    observed_counts = (
        payload.get("total_files"),
        payload.get("reviewable_count"),
        payload.get("excluded_count"),
    )
    if (
        not isinstance(provider_record, dict)
        or provider_record.get("will_review") is not False
        or provider_record.get("exclude_reason") != "provider_directory"
    ):
        core._fail("candidate did not report the tracked provider-directory exclusion")
    if observed_counts != expected_counts:
        core._fail("candidate changed provider-directory preview counts")
    expected_churn = 2
    if (
        payload.get("total_insertions") != expected_churn
        or payload.get("total_deletions") != expected_churn
    ):
        core._fail("candidate changed provider-directory preview churn totals")
    return {
        "result": "passed",
        "tracked_provider_directory": "reported",
    }


def _target_rule_selection_probe(binary: Path, directory: Path) -> dict[str, object]:
    """Prove the real OCR selector consumes target rules without changing its range."""

    git_env = execution._isolated_probe_environment(directory / "rule-git-home")
    repo = directory / "target-rule-selection"
    repo.mkdir()
    execution._run(["git", "init", "--initial-branch=main"], cwd=repo, env=git_env)
    execution._run(["git", "config", "user.name", "Synthetic Reviewer"], cwd=repo, env=git_env)
    execution._run(["git", "config", "user.email", "reviewer@example.com"], cwd=repo, env=git_env)
    target = repo / "synthetic-template.ocrfixture"
    target.write_text("before={{ value }}\n", encoding="utf-8")
    execution._run(["git", "add", target.name], cwd=repo, env=git_env)
    execution._run(["git", "commit", "-m", "target rule baseline"], cwd=repo, env=git_env)
    base = execution._run(["git", "rev-parse", "HEAD"], cwd=repo, env=git_env).strip()
    target.write_text("after={{ value }}\n", encoding="utf-8")
    execution._run(["git", "commit", "-am", "change synthetic template"], cwd=repo, env=git_env)
    head = execution._run(["git", "rev-parse", "HEAD"], cwd=repo, env=git_env).strip()
    rules = directory / "target-policy-rules.json"
    rules.write_bytes(
        core.canonical_json(
            {
                "exclude": [],
                "include": [f"**/*{target.suffix}"],
                "rules": [
                    {
                        "merge_system_rule": True,
                        "path": f"**/*{target.suffix}",
                        "rule": "Review the synthetic target-policy fixture.",
                    }
                ],
            }
        )
    )

    def preview(home_name: str, *extra: str) -> dict[str, Any]:
        home = directory / home_name
        env = execution._isolated_probe_environment(home)
        command = [
            str(binary),
            "review",
            "--from",
            base,
            "--to",
            head,
            "--preview",
            *extra,
        ]
        command.extend(["--format", "json"])
        output = execution._run(command, cwd=repo, env=env)
        if os.path.lexists(home / ".opencodereview" / "sessions"):
            core._fail("target-rule preview created a review session store")
        try:
            payload = json.loads(output)
        except json.JSONDecodeError as exc:
            raise core.CompatibilityError("target-rule preview did not emit JSON") from exc
        if not isinstance(payload, dict) or not isinstance(payload.get("files"), list):
            core._fail("target-rule preview emitted an invalid file manifest")
        return payload

    without_rules = preview("rule-source-home")
    with_rules = preview("rule-target-home", "--rule", str(rules))

    source_selected, source_reason = _preview_file_selection(without_rules, target.name)
    target_selected, target_reason = _preview_file_selection(with_rules, target.name)
    expected_source_reason = "unsupported_ext"
    if source_selected or source_reason != expected_source_reason:
        core._fail("synthetic file was not excluded before target-rule admission")
    if not target_selected or target_reason not in {None, ""}:
        core._fail("real OCR did not select the synthetic file from target rules")
    return {
        "format": "json",
        "from_to_unchanged": True,
        "path": target.name,
        "result": "passed",
        "source_exclusion": "unsupported_ext",
        "target_selected": True,
    }


def _language_rule_probe(binary: Path, version: str, directory: Path) -> dict[str, object]:
    """Prove consumed built-in language selection and rule ownership without an LLM."""

    root = directory / "language-rule-probe"
    root.mkdir()
    git_env = execution._isolated_probe_environment(root / "git-home")
    repo = root / "review"
    repo.mkdir()
    execution._run(["git", "init", "--initial-branch=main"], cwd=repo, env=git_env)
    execution._run(["git", "config", "user.name", "Synthetic Reviewer"], cwd=repo, env=git_env)
    execution._run(["git", "config", "user.email", "reviewer@example.com"], cwd=repo, env=git_env)
    exact_patterns = contracts._language_rules_for_version(version)
    qualified_rules = set(exact_patterns)
    supported_paths = tuple(sorted(qualified_rules))
    unsupported_paths = contracts._language_negative_paths_for_version(version)
    default_excluded_paths = contracts._default_excluded_paths_for_version(version)
    paths = tuple(
        sorted(
            {
                *supported_paths,
                *unsupported_paths,
                *default_excluded_paths,
                *settings.DEFAULT_RULE_CONTROL_PATHS,
                *settings.PYTEST_PREFIX_CONTROL_PATHS,
                settings.PYTEST_PREFIX_EXCLUDED_PATH,
            }
        )
    )
    for path in paths:
        target = repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("// baseline\n", encoding="utf-8")
    execution._run(["git", "add", *paths], cwd=repo, env=git_env)
    execution._run(["git", "commit", "-m", "language baseline"], cwd=repo, env=git_env)
    base = execution._run(["git", "rev-parse", "HEAD"], cwd=repo, env=git_env).strip()
    for path in paths:
        (repo / path).write_text("// changed\n", encoding="utf-8")
    execution._run(["git", "commit", "-am", "language changes"], cwd=repo, env=git_env)
    head = execution._run(["git", "rev-parse", "HEAD"], cwd=repo, env=git_env).strip()
    env = execution._isolated_probe_environment(root / "review-home")
    preview = execution._run(
        [
            str(binary),
            "review",
            "--from",
            base,
            "--to",
            head,
            "--preview",
            "--format",
            "json",
        ],
        cwd=repo,
        env=env,
    )
    try:
        payload = json.loads(preview)
    except json.JSONDecodeError as exc:
        raise core.CompatibilityError("language preview did not emit JSON") from exc
    selected = _selected_preview_paths(payload)
    expected_selected = (
        set(supported_paths)
        | set(settings.PYTEST_PREFIX_CONTROL_PATHS)
        | set(settings.DEFAULT_RULE_CONTROL_PATHS)
    )
    if selected != expected_selected:
        missing = sorted(expected_selected - selected)
        unexpected = sorted(selected - expected_selected)
        core._fail(
            "candidate did not select the qualified built-in language set: "
            f"missing={missing!r}, unexpected={unexpected!r}"
        )
    for unsupported_path in unsupported_paths:
        unsupported_selected, unsupported_reason = _preview_file_selection(
            payload, unsupported_path
        )
        if unsupported_selected or unsupported_reason != "unsupported_ext":
            core._fail(f"candidate unexpectedly selected unqualified path {unsupported_path}")
    for path in default_excluded_paths:
        selected_test, reason = _preview_file_selection(payload, path)
        if selected_test or not isinstance(reason, str) or not reason:
            core._fail(f"candidate did not preserve the default test-path exclusion: {path}")
    for path in settings.PYTEST_PREFIX_CONTROL_PATHS:
        selected_control, reason = _preview_file_selection(payload, path)
        if not selected_control or reason not in {None, ""}:
            core._fail(f"candidate overmatched the pytest-prefix exclusion: {path}")
    for path in settings.DEFAULT_RULE_CONTROL_PATHS:
        output = execution._run([str(binary), "rules", "check", path], cwd=repo, env=env)
        if "Source: System built-in\n" not in output or "Pattern: default\n" not in output:
            core._fail("candidate overmatched Starlark Rules onto an ordinary extensionless file")
    rule_documents = set()
    for path in supported_paths:
        output = execution._run([str(binary), "rules", "check", path], cwd=repo, env=env)
        if (
            f"File: {path}\n" not in output
            or "Source: System built-in\n" not in output
            or "Pattern: " not in output
        ):
            core._fail("candidate did not resolve a qualified built-in language rule")
        expected_pattern = exact_patterns.get(path)
        if expected_pattern is not None and f"Pattern: {expected_pattern}\n" not in output:
            core._fail(f"candidate resolved the wrong built-in language rule for {path}")
        if path.endswith(".cs"):
            if (
                "#### Nullability and Reference Types" not in output
                or "#### Async, Tasks, and Cancellation" not in output
            ):
                core._fail("candidate omitted the C# rule document")
            rule_documents.add("csharp")
        elif path in {"BUILD", "WORKSPACE", "nested/BUILD", "nested/WORKSPACE"} or path.endswith(
            (".bzl", ".bazel", ".star")
        ):
            if "# Starlark Code Review Guide" not in output:
                core._fail("candidate omitted the Starlark rule document")
            rule_documents.add("starlark")
    extensions = sorted({Path(path).suffix for path in supported_paths if Path(path).suffix})
    expected_extensions = sorted(
        {Path(path).suffix for path in exact_patterns if Path(path).suffix}
    )
    if extensions != expected_extensions:
        core._fail("language probe paths disagree with the canonical extension projection")
    result: dict[str, object] = {
        "extensions": expected_extensions,
        "excluded_extensions": [".svh"],
        "default_excluded_paths": list(default_excluded_paths),
        "result": "passed",
        "rule_source": "system_builtin",
        "selected": len(supported_paths),
        "paths": list(supported_paths),
        "excluded_paths": list(unsupported_paths),
        "rule_documents": sorted(rule_documents),
        "default_rule_paths": list(settings.DEFAULT_RULE_CONTROL_PATHS),
    }
    for name, source, heading in (
        ("objective.m", "#import <Foundation/Foundation.h>\n", "Objective-C"),
        ("matrix.m", "function y = sample(x)\ny = x + 1;\nend\n", "MATLAB"),
    ):
        (repo / name).write_text(source, encoding="utf-8")
        output = execution._run([str(binary), "rules", "check", name], cwd=repo, env=env)
        if "Pattern: **/*.m\n" not in output or heading not in output:
            core._fail("candidate changed content-dependent .m rule routing")
    mm_output = execution._run(
        [str(binary), "rules", "check", "native/object.mm"], cwd=repo, env=env
    )
    if "Objective-C" not in mm_output:
        core._fail("candidate did not route Objective-C++ to Objective-C rules")
    result["m_routing"] = "matlab_and_objective_c"
    return result
