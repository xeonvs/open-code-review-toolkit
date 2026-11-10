"""Validate versioned OCR evidence, support metadata and closed outcome shapes."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import ocr_compat_history as history

from . import core, settings


def _numeric_contract_for_version(version: str) -> dict[str, object]:
    """Select required grace verdicts without changing frozen numeric defaults."""

    _require_live_qualification_version(version)
    contract = dict(settings.CURRENT_NUMERIC_CLI_CONTRACT)
    contract["grace_rounds"] = {
        "task_done": {"completed": True, "limit_warning": True},
        "no_task_done": {"completed": False, "limit_warning": True},
    }
    return contract


def _validate_current_contracts(value: object, version: str) -> None:
    """Require the live consumed contract epoch selected for one candidate version."""

    _require_live_qualification_version(version)
    if not isinstance(value, dict):
        core._fail("current qualification contracts are missing")
    flags = value.get("required_review_flags")
    capabilities = value.get("optional_capabilities")
    if (
        not isinstance(flags, list)
        or not all(isinstance(flag, str) for flag in flags)
        or not settings.REQUIRED_REVIEW_FLAGS.issubset(flags)
        or not isinstance(capabilities, list)
        or not all(isinstance(capability, str) for capability in capabilities)
        or not {"review_effort", "semantic_grouping"}.issubset(capabilities)
    ):
        core._fail("current qualification omitted required CLI capabilities")
    language_paths = _language_rules_for_version(version)
    extensions = sorted({Path(path).suffix for path in language_paths if Path(path).suffix})
    expected = {
        "numeric_cli_probe": _numeric_contract_for_version(version),
        "review_budget_probe": {
            "budget": 30_000,
            "completed": 2,
            "failed_budget": 1,
            "partial_findings_preserved": True,
            "result": "passed",
            "selected": 3,
            "grouping_requests": 0,
            "grouping_strategy": "per_file",
        },
        "semantic_grouping_probe": {
            "default_effort": "medium",
            "filter_requests": 1,
            "grouping_requests": 1,
            "main_requests": 3,
            "result": "passed",
            "review_rounds": 2,
            "grouping_completion_cap": 16_384,
            "files": 4,
            "prior_finding_semantics": "filter_survivors_as_confirmed",
            "recheck_instruction_requests": 3,
        },
        "small_change_grouping_probe": {
            "grouping_requests": 0,
            "high_churn": "per_file",
            "low_churn": "bundle_all",
            "result": "passed",
            "single_file": "per_file",
            "threshold_files": 4,
        },
        "provider_directory_preview_probe": {
            "result": "passed",
            "tracked_provider_directory": "reported",
        },
        "language_rule_probe": {
            "excluded_extensions": [".svh"],
            "default_excluded_paths": list(_default_excluded_paths_for_version(version)),
            "extensions": extensions,
            "result": "passed",
            "rule_source": "system_builtin",
            "selected": len(language_paths),
            "m_routing": "matlab_and_objective_c",
            "paths": sorted(_language_rules_for_version(version)),
            "excluded_paths": list(_language_negative_paths_for_version(version)),
            "rule_documents": ["clojure", "csharp", "starlark"],
            "default_rule_paths": list(settings.DEFAULT_RULE_CONTROL_PATHS),
        },
        "completion_cap_probe": {
            "explicit": 4_096,
            "inherited": 16_384,
            "result": "passed",
            "wire_field": "max_completion_tokens",
        },
        "reasoning_effort_probe": {
            "result": "passed",
            "protocols": ["openai", "openai-responses"],
            "efforts": ["unset", "none", "high"],
            "responses_siblings_preserved": True,
            "provider_acceptance": "not-tested",
        },
        "stream_override_probe": {
            "result": "passed",
            "protocols": ["openai", "openai-responses", "anthropic"],
            "explicit_false": "preserved",
            "non_boolean": "omitted",
            "unset": "omitted",
            "provider_acceptance": "not-tested",
        },
        "csharp_context_probe": {
            "result": "passed",
            "rules_in_main_request": True,
            "context_paths": ["Directory.Build.props", "app/Project.csproj", "global.json"],
            "execution": "read-only-native-tools",
        },
        "clojure_context_probe": {
            "result": "passed",
            "rules_in_main_request": True,
            "context_paths": ["deps.edn"],
            "execution": "read-only-native-tools",
        },
        "comment_arguments_probe": {
            "result": "passed",
            "intact_cases": ["array", "serialized", "repaired"],
            "comments_per_batch": 2,
            "suspect_batch_rejected": True,
            "failure_arguments_preserved": True,
            "repair_warning": True,
        },
    }
    for name, contract in expected.items():
        if value.get(name) != contract:
            core._fail(f"current qualification contract disagrees: {name}")
    if value.get("version_probe") != "passed" or value.get("preview_probe") != {
        "format": "json",
        "path": "example.py",
        "result": "passed",
        "session_store_created": False,
    }:
        core._fail("current qualification omitted version or isolated JSON preview proof")
    result = value.get("result_contract_probe")
    if (
        not isinstance(result, dict)
        or result.get("result") != "passed"
        or result.get("manifest_schema") != "ocr.run-manifest/v1"
        or result.get("normalized_outcome") != "clean"
    ):
        core._fail("current qualification omitted the review-result contract")


def _validate_contracts_for_version(version: str, contracts: Any) -> None:
    """Validate observed contracts against the epoch owned by the candidate version."""

    version_tuple = core._version(version)
    if version_tuple < history.HISTORICAL_CUTOFF:
        history.validate_contracts(version, version_tuple, {"contracts": contracts}, core._fail)
    else:
        _validate_current_contracts(contracts, version)


def _validate_evidence_contracts(version: str, evidence: dict[str, Any]) -> None:
    """Select the frozen or live qualification epoch from the candidate version."""

    _validate_contracts_for_version(version, evidence.get("contracts"))


def _language_rules_for_version(version: str) -> dict[str, str]:
    """Return live probe paths for the frozen or current candidate epoch."""

    _require_live_qualification_version(version)
    rules = dict(settings.CURRENT_LANGUAGE_RULES)
    return rules


def _language_negative_paths_for_version(version: str) -> tuple[str, ...]:
    """Keep next-epoch languages observable as negative controls."""

    _require_live_qualification_version(version)
    paths = ["rtl/include.svh", "nested/BUILD.bak"]
    return tuple(paths)


def _default_excluded_paths_for_version(version: str) -> tuple[str, ...]:
    """Return the exact built-in test exclusions owned by one OCR epoch."""

    _require_live_qualification_version(version)
    return settings.CURRENT_DEFAULT_EXCLUDED_PATHS


def _rolling_runtime_support(version: str) -> dict[str, object]:
    """Return the three-line runtime policy for one qualified recommendation."""

    major, minor, _patch = core._version(version)
    if minor < 2:
        core._fail("rolling runtime support requires two preceding minor lines")
    return {
        "deprecated_lines": [f"{major}.{minor - 2}"],
        "qualified_patches_only": True,
        "rejected_before": f"{major}.{minor - 2}.0",
        "supported_lines": [f"{major}.{minor - 1}", f"{major}.{minor}"],
    }


def qualified_runtime_versions(manifest: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Project exact supported and deprecated patches from tested evidence."""

    policy = manifest.get("runtime_support")
    releases = manifest.get("releases")
    if not isinstance(policy, dict) or not isinstance(releases, list):
        core._fail("runtime support requires a policy and release inventory")
    supported_lines = policy.get("supported_lines")
    deprecated_lines = policy.get("deprecated_lines")
    if not isinstance(supported_lines, list) or not isinstance(deprecated_lines, list):
        core._fail("runtime support lines must be lists")
    supported_set = set(supported_lines)
    deprecated_set = set(deprecated_lines)
    supported: list[str] = []
    deprecated: list[str] = []
    for entry in releases:
        if not isinstance(entry, dict) or entry.get("status") != "tested":
            continue
        version = entry.get("version")
        if not isinstance(version, str):
            continue
        major, minor, _patch = core._version(version)
        line = f"{major}.{minor}"
        if line in supported_set:
            supported.append(version)
        elif line in deprecated_set:
            deprecated.append(version)
    supported.sort(key=core._version)
    deprecated.sort(key=core._version)
    return supported, deprecated


def _validate_runtime_support(manifest: dict[str, Any], recommended: str) -> None:
    """Validate policy shape separately from discovery and historical evidence."""

    expected = _rolling_runtime_support(recommended)
    policy = manifest.get("runtime_support")
    if not isinstance(policy, dict) or set(policy) != set(expected):
        core._fail("runtime_support must use the closed rolling-window schema")
    if policy != expected:
        core._fail("runtime_support does not match the recommended release line")
    for field in ("supported_lines", "deprecated_lines"):
        lines = policy[field]
        assert isinstance(lines, list)
        if any(
            not isinstance(line, str) or settings.VERSION_LINE_RE.fullmatch(line) is None
            for line in lines
        ):
            core._fail(f"runtime_support {field} contains an invalid version line")
    supported, _deprecated = qualified_runtime_versions(manifest)
    if not supported or supported[-1] != recommended:
        core._fail("runtime_support must resolve the recommendation to an exact tested patch")


def validate_manifest(manifest: dict[str, Any], root: Path = settings.ROOT) -> None:
    """Validate the versioned OCR support contract and evidence linkage."""

    if manifest.get("schema_version") != 2:
        core._fail("manifest schema_version must be 2")
    if manifest.get("upstream_repository") != settings.UPSTREAM_REPOSITORY:
        core._fail(f"manifest upstream_repository must be {settings.UPSTREAM_REPOSITORY}")
    recommended = manifest.get("recommended_version")
    floor = manifest.get("monitoring_floor")
    if not isinstance(recommended, str) or not isinstance(floor, str):
        core._fail("recommended_version and monitoring_floor must be strings")
    core._version(recommended)
    if core._version(floor) > core._version(recommended):
        core._fail("monitoring_floor cannot be newer than recommended_version")
    releases = manifest.get("releases")
    if not isinstance(releases, list) or not releases:
        core._fail("manifest releases must be a non-empty list")
    versions: set[str] = set()
    recommended_found = False
    for entry in releases:
        if not isinstance(entry, dict):
            core._fail("each release entry must be an object")
        version = entry.get("version")
        status = entry.get("status")
        if not isinstance(version, str):
            core._fail("release version must be a string")
        core._version(version)
        if version in versions:
            core._fail(f"duplicate release version: {version}")
        versions.add(version)
        if status not in {"tested", "observed-candidate"}:
            core._fail(f"invalid support status for {version}: {status!r}")
        capabilities = entry.get("capabilities", [])
        if (
            not isinstance(capabilities, list)
            or len(capabilities) > len(settings.KNOWN_OPTIONAL_CAPABILITIES)
            or any(
                capability not in settings.KNOWN_OPTIONAL_CAPABILITIES
                for capability in capabilities
            )
            or capabilities != sorted(set(capabilities))
        ):
            core._fail(f"invalid optional capabilities for {version}")
        if version == recommended:
            if status != "tested":
                core._fail("recommended_version must have tested status")
            recommended_found = True
        assets = entry.get("assets")
        if not isinstance(assets, list) or len(assets) > settings.MAX_ASSETS:
            core._fail(f"{version} assets must be a bounded list")
        asset_names: set[str] = set()
        for asset in assets:
            if not isinstance(asset, dict):
                core._fail(f"{version} asset must be an object")
            name, size, sha256 = asset.get("name"), asset.get("size"), asset.get("sha256")
            if not isinstance(name, str) or name in asset_names or Path(name).name != name:
                core._fail(f"invalid or duplicate asset name for {version}: {name!r}")
            asset_names.add(name)
            if not isinstance(size, int) or size <= 0 or size > settings.MAX_ASSET_BYTES:
                core._fail(f"invalid asset size for {version}/{name}")
            if not isinstance(sha256, str) or settings.SHA256_RE.fullmatch(sha256) is None:
                core._fail(f"invalid SHA-256 for {version}/{name}")
        if asset_names != settings.REQUIRED_ASSETS:
            core._fail(f"{version} asset set does not match the supported upstream matrix")
        evidence_rel = entry.get("evidence")
        evidence_hash = entry.get("evidence_sha256")
        if not isinstance(evidence_rel, str) or not isinstance(evidence_hash, str):
            core._fail(f"{version} evidence path and hash are required")
        evidence_path = (root / evidence_rel).resolve()
        compatibility_root = (root / "compatibility").resolve()
        if not evidence_path.is_relative_to(compatibility_root):
            core._fail(f"{version} evidence path escapes compatibility/")
        try:
            payload = evidence_path.read_bytes()
        except OSError as exc:
            raise core.CompatibilityError(f"cannot read evidence for {version}: {exc}") from exc
        if hashlib.sha256(payload).hexdigest() != evidence_hash:
            core._fail(f"evidence hash mismatch for {version}")
        evidence = core.load_json(evidence_path)
        if evidence.get("version") != version or evidence.get("result") != "compatible":
            core._fail(f"evidence does not qualify {version} as compatible")
        _validate_evidence_contracts(version, evidence)
        evidence_assets = evidence.get("assets")
        if not isinstance(evidence_assets, list):
            core._fail(f"evidence assets are missing for {version}")
        manifest_asset_tuples = sorted(
            (asset["name"], asset["size"], asset["sha256"])
            for asset in assets
            if isinstance(asset, dict)
        )
        evidence_asset_tuples = sorted(
            (asset.get("name"), asset.get("size"), asset.get("sha256"))
            for asset in evidence_assets
            if isinstance(asset, dict)
        )
        if manifest_asset_tuples != evidence_asset_tuples:
            core._fail(f"manifest and evidence assets disagree for {version}")
    if not recommended_found:
        core._fail("recommended_version is missing from releases")
    _validate_runtime_support(manifest, recommended)


def detect_optional_capabilities(help_output: str, sample: dict[str, Any]) -> list[str]:
    """Validate additive OCR identity fields and return observed optional capabilities."""

    optional_capabilities: set[str] = set()
    if "--effort" in help_output:
        optional_capabilities.add("review_effort")
    if "--model" in help_output:
        optional_capabilities.add("per_run_model_override")
    if "--provider" in help_output:
        optional_capabilities.add("per_run_provider_override")
    llm_identity = sample.get("llm")
    if llm_identity is not None:
        if not isinstance(llm_identity, dict):
            core._fail("candidate full review emitted an invalid additive LLM identity")
        model = llm_identity.get("model")
        provider = llm_identity.get("provider")
        if not isinstance(model, str) or not model or len(model) > 500:
            core._fail("candidate full review emitted an invalid additive LLM model identity")
        if provider is not None and (
            not isinstance(provider, str) or not provider or len(provider) > 200
        ):
            core._fail("candidate full review emitted an invalid additive LLM provider identity")
        optional_capabilities.add("llm_result_identity")
    groups = sample.get("groups")
    if groups is not None:
        _validate_file_groups(groups)
        optional_capabilities.add("semantic_grouping")
    return sorted(optional_capabilities)


def _validate_file_groups(value: Any, expected_paths: set[str] | None = None) -> None:
    """Validate bounded additive group metadata without retaining its labels."""

    if not isinstance(value, list) or not value or len(value) > 100:
        core._fail("candidate full review emitted invalid additive file groups")
    observed: list[str] = []
    for group in value:
        if not isinstance(group, dict):
            core._fail("candidate full review emitted an invalid file group")
        label = group.get("label")
        files = group.get("files")
        if (
            not isinstance(label, str)
            or not label
            or len(label) > 500
            or any(ord(character) < 32 for character in label)
            or not isinstance(files, list)
            or not files
            or len(files) > 10
        ):
            core._fail("candidate full review emitted an invalid file group")
        for path in files:
            if (
                not isinstance(path, str)
                or not path
                or len(path) > 1_000
                or any(ord(character) < 32 for character in path)
                or path in observed
            ):
                core._fail("candidate full review emitted an invalid grouped path")
            observed.append(path)
    if expected_paths is not None and set(observed) != expected_paths:
        core._fail("candidate semantic grouping did not cover the expected paths")


def _require_live_qualification_version(version: str) -> None:
    """Keep frozen readback epochs outside the forward-only executable suite."""

    if core._version(version) < history.HISTORICAL_CUTOFF:
        floor = ".".join(str(part) for part in history.HISTORICAL_CUTOFF)
        core._fail(
            f"OCR {version} belongs to a frozen readback-only qualification epoch; "
            f"fresh qualification requires OCR {floor} or newer"
        )


def qualification_status(
    *,
    tag: str,
    comparison_version: str,
    tested_baseline_version: str,
    result: str,
    phase: str,
    reason: str,
) -> dict[str, str]:
    """Build the closed public status retained for one qualification attempt."""

    if settings.VERSION_RE.fullmatch(tag) is None:
        core._fail("qualification status tag is invalid")
    version = tag.removeprefix("v")
    comparison = comparison_version.removeprefix("v")
    baseline = tested_baseline_version.removeprefix("v")
    core._version(comparison)
    core._version(baseline)
    if result not in {"compatible", "failed"}:
        core._fail("qualification status result is invalid")
    if phase not in settings.QUALIFICATION_PHASES or reason not in settings.QUALIFICATION_REASONS:
        core._fail("qualification status phase or reason is invalid")
    if (result == "compatible") != (phase == "complete" and reason == "compatible"):
        core._fail("qualification status result is inconsistent")
    if result == "failed" and reason not in settings.QUALIFICATION_FAILURE_REASONS.get(
        phase, frozenset()
    ):
        core._fail("qualification status failure phase and reason are inconsistent")
    return {
        "comparison_version": comparison,
        "phase": phase,
        "reason": reason,
        "result": result,
        "schema": settings.QUALIFICATION_STATUS_SCHEMA,
        "tag": f"v{version}",
        "tested_baseline_version": baseline,
        "version": version,
    }


def validate_qualification_status(value: dict[str, Any]) -> dict[str, str]:
    """Reject any status that contains open-ended or inconsistent public data."""

    expected_keys = {
        "comparison_version",
        "phase",
        "reason",
        "result",
        "schema",
        "tag",
        "tested_baseline_version",
        "version",
    }
    if set(value) != expected_keys or value.get("schema") != settings.QUALIFICATION_STATUS_SCHEMA:
        core._fail("qualification status schema is invalid")
    status = qualification_status(
        tag=value.get("tag") if isinstance(value.get("tag"), str) else "",
        comparison_version=(
            value.get("comparison_version")
            if isinstance(value.get("comparison_version"), str)
            else ""
        ),
        tested_baseline_version=(
            value.get("tested_baseline_version")
            if isinstance(value.get("tested_baseline_version"), str)
            else ""
        ),
        result=value.get("result") if isinstance(value.get("result"), str) else "",
        phase=value.get("phase") if isinstance(value.get("phase"), str) else "",
        reason=value.get("reason") if isinstance(value.get("reason"), str) else "",
    )
    if value.get("version") != status["version"]:
        core._fail("qualification status version is inconsistent")
    return status
