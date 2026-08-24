"""Single-owner contract for supported environment inputs and exact defaults."""

from __future__ import annotations

import ast
import re

import pytest

from ocr_toolkit import configure, mcp_config, preflight
from ocr_toolkit.common.language import resolve_review_language
from ocr_toolkit.common.redaction import SENSITIVE_ENV_NAMES
from ocr_toolkit.context.adapters import parse_adapter_config
from ocr_toolkit.evidence.review_context import parse_review_context_mode
from ocr_toolkit.ocr_result import max_result_bytes
from ocr_toolkit.posting import settings
from tests.support import PROJECT_ROOT

RUNTIME_DEFAULTS = {
    "OCR_LLM_URL": "None",
    "OCR_LLM_TOKEN": "None",
    "OCR_LLM_MODEL": "None",
    "OCR_LLM_PROTOCOL": "openai",
    "OCR_LLM_AUTH_HEADER": "Authorization",
    "OCR_LLM_EXTRA_HEADERS": "Empty object",
    "OCR_LLM_EXTRA_BODY": "Unset",
    "OCR_ANTHROPIC_DISABLE_THINKING": "false",
    "OCR_REVIEW_LANGUAGE": "English",
    "OCR_LLM_VALIDATE_MODEL": "false",
    "OCR_LLM_MODELS_URL": "Derived from `OCR_LLM_URL`",
    "OCR_LLM_ALLOWED_MODELS": "Empty list",
    "OCR_TELEMETRY_ENABLED": "false",
    "OCR_TELEMETRY_CONTENT_LOGGING": "false",
    "OCR_TELEMETRY_EXPORTER": "Empty string",
    "OCR_TELEMETRY_OTLP_ENDPOINT": "Unset",
    "OCR_REVIEW_CONTEXT_MODE": "off",
    "OCR_REVIEW_CONTEXT_ADAPTERS_JSON": "Empty list",
    "OCR_MCP_SERVERS_JSON": "Empty object",
    "OCR_MCP_REPLACE": "false",
    "OCR_POST_MODE": "draft",
    "OCR_STRICT_POSTING": "false",
    "OCR_POST_EMOJI": "true",
    "OCR_POST_BADGES": "text",
    "OCR_AUTO_APPROVE": "true",
    "OCR_MAX_POST_COMMENTS": "50",
    "OCR_MAX_RESULT_BYTES": "2000000",
    "OCR_POST_ERROR_DETAILS": "Unset (disabled)",
    "OCR_EXIT_CODE": "0",
}

GITLAB_DEFAULTS = {
    "GITLAB_API_TOKEN": "None",
    "CI_API_V4_URL": "Derived as `${CI_SERVER_URL}/api/v4`",
    "CI_SERVER_URL": "`https://gitlab.com` in posting only",
    "CI_PROJECT_ID": "None",
    "CI_MERGE_REQUEST_IID": "None",
    "CI_MERGE_REQUEST_SOURCE_BRANCH_SHA": (
        "Falls back to `CI_COMMIT_SHA` only where explicitly documented"
    ),
    "CI_MERGE_REQUEST_DIFF_BASE_SHA": "None",
    "CI_COMMIT_SHA": "None",
    "CI_PIPELINE_ID": "Omitted",
    "CI_JOB_ID": "Omitted",
    "CI_PIPELINE_SOURCE": "None",
}

EXAMPLE_DEFAULTS = {
    "OCR_VERSION": "v1.9.10",
    "OCR_SHA256": "359e5bafda1438a47ef389399f4994350e1016371eac1dc17a2c428acb228e6c",
    "OCR_TOOLKIT_VERSION": "0.7.1",
    "OCR_TOOLKIT_CHECKSUMS_URL": "Release URL derived from `OCR_TOOLKIT_VERSION`",
    "OCR_TOOLKIT_WHEEL": "open_code_review_toolkit-${OCR_TOOLKIT_VERSION}-py3-none-any.whl",
    "OCR_TOOLKIT_WHEEL_SHA256": "Matching value from `SHA256SUMS`",
    "OCR_MAX_TOOLS": "30",
    "OCR_MAX_TOKENS_BUDGET": "0",
}

DYNAMIC_INPUTS = {
    "Names declared by adapter `env_from`",
    "Names declared by adapter `headers_from`",
    "Names declared by MCP `env_from`",
    "Names declared by MCP `headers_from`",
}

REDACTION_ONLY = {
    "OCR_LLM_AUTH_TOKEN",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
}

REMOVED_PUBLIC_INPUTS = {
    "OCR_GITLAB_BOT_USER_ID",
    "OCR_RUN_HELPER_TESTS",
    "OCR_LLM_SUPPORTS_FUNCTION_CALLING",
    "OCR_LLM_SUPPORTS_REASONING",
    "OCR_CONFIG_PATH",
}

ENVIRONMENT_NAME_RE = re.compile(r"(?:ANTHROPIC|CI|GITLAB|OCR|OPENAI)_[A-Z0-9_]+\Z")


def _display_cell(raw: str) -> str:
    value = raw.strip()
    if value.startswith("`") and value.endswith("`") and value.count("`") == 2:
        return value[1:-1]
    return value


def _table(document: str, heading: str) -> tuple[list[str], dict[str, dict[str, str]]]:
    lines = document.splitlines()
    heading_index = lines.index(f"## {heading}")
    header_index = next(
        index for index in range(heading_index + 1, len(lines)) if lines[index].startswith("|")
    )
    headers = [_display_cell(cell) for cell in lines[header_index].strip("|").split("|")]
    rows: dict[str, dict[str, str]] = {}
    for line in lines[header_index + 2 :]:
        if not line.startswith("|"):
            break
        cells = [_display_cell(cell) for cell in line.strip("|").split("|")]
        assert len(cells) == len(headers)
        key = cells[0]
        assert key not in rows
        rows[key] = dict(zip(headers, cells, strict=True))
    return headers, rows


def _public_contract_text() -> str:
    roots = [PROJECT_ROOT / "src" / "ocr_toolkit", PROJECT_ROOT / "examples", PROJECT_ROOT / "docs"]
    documents = []
    for root in roots:
        for path in root.rglob("*"):
            if (
                not path.is_file()
                or path.suffix not in {".json", ".md", ".py", ".toml", ".yaml", ".yml"}
                or "execution_history" in path.parts
            ):
                continue
            documents.append(path.read_text(encoding="utf-8"))
    return "\n".join(documents)


def _literal_source_environment_names() -> set[str]:
    names: set[str] = set()
    for path in (PROJECT_ROOT / "src" / "ocr_toolkit").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and ENVIRONMENT_NAME_RE.fullmatch(node.value) is not None
            ):
                names.add(node.value)
    return names


def test_documented_environment_tables_are_complete_and_exact() -> None:
    configuration = (PROJECT_ROOT / "docs" / "configuration.md").read_text(encoding="utf-8")
    expected_headers = ["Variable", "Source / owner", "Required", "Exact default", "Behavior"]

    for heading, expected_defaults in (
        ("Toolkit runtime variables", RUNTIME_DEFAULTS),
        ("GitLab and provider variables", GITLAB_DEFAULTS),
        ("Example-local variables", EXAMPLE_DEFAULTS),
    ):
        headers, rows = _table(configuration, heading)
        assert headers == expected_headers
        assert set(rows) == set(expected_defaults)
        assert {name: row["Exact default"] for name, row in rows.items()} == expected_defaults
        assert all(
            row["Source / owner"] and row["Required"] and row["Behavior"] for row in rows.values()
        )

    headers, dynamic_rows = _table(configuration, "Dynamic adapter and MCP inputs")
    assert headers == expected_headers
    assert set(dynamic_rows) == DYNAMIC_INPUTS
    assert all(row["Exact default"] == "None" for row in dynamic_rows.values())

    documented_names = set(RUNTIME_DEFAULTS) | set(GITLAB_DEFAULTS) | set(EXAMPLE_DEFAULTS)
    assert documented_names.isdisjoint(REDACTION_ONLY)
    assert REDACTION_ONLY.issubset(SENSITIVE_ENV_NAMES)
    assert documented_names.isdisjoint(REMOVED_PUBLIC_INPUTS | {"OCR_USE_ANTHROPIC"})


def test_source_environment_inventory_matches_the_documented_contract() -> None:
    source_names = _literal_source_environment_names()
    # CI_PIPELINE_SOURCE belongs solely to the public example's GitLab rules.
    expected = (
        set(RUNTIME_DEFAULTS)
        | (set(GITLAB_DEFAULTS) - {"CI_PIPELINE_SOURCE"})
        | REDACTION_ONLY
        | {"OCR_USE_ANTHROPIC"}
    )
    assert source_names == expected


def test_runtime_defaults_match_the_documented_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in set(RUNTIME_DEFAULTS) | {"OCR_USE_ANTHROPIC"}:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("OCR_LLM_URL", "https://llm.example.invalid/v1/chat/completions")
    monkeypatch.setenv("OCR_LLM_TOKEN", "unit-test-token")
    monkeypatch.setenv("OCR_LLM_MODEL", "unit-test-model")

    for cached_setting in (
        settings.post_mode,
        settings.post_emoji,
        settings.post_badges,
        settings.auto_approve,
    ):
        cached_setting.cache_clear()
    try:
        updates = configure.build_config_updates()
        assert updates["llm.protocol"] == "openai"
        assert updates["llm.auth_header"] == "Authorization"
        assert updates["telemetry.enabled"] is False
        assert updates["telemetry.content_logging"] is False
        assert "llm.extra_headers" not in updates
        assert "llm.extra_body" not in updates
        assert "telemetry.exporter" not in updates
        assert "telemetry.otlp_endpoint" not in updates
        assert resolve_review_language() == "English"
        assert preflight._models_url() == "https://llm.example.invalid/v1/models"
        assert parse_review_context_mode(None) == "off"
        assert parse_adapter_config(None) == ()
        assert mcp_config.parse_mcp_servers() == []
        assert mcp_config._replace_configured_servers() is False
        assert settings.post_mode() == "draft"
        assert settings.strict_posting() is False
        assert settings.post_emoji() is True
        assert settings.post_badges() == "text"
        assert settings.auto_approve().enabled is True
        assert settings.max_post_comments() == 50
        assert max_result_bytes() == 2_000_000
        assert settings.ocr_exit_code() == 0
    finally:
        for cached_setting in (
            settings.post_mode,
            settings.post_emoji,
            settings.post_badges,
            settings.auto_approve,
        ):
            cached_setting.cache_clear()


def test_removed_and_redaction_only_names_do_not_reenter_public_configuration() -> None:
    public_contract = _public_contract_text()
    for name in REMOVED_PUBLIC_INPUTS:
        assert name not in public_contract

    configuration = (PROJECT_ROOT / "docs" / "configuration.md").read_text(encoding="utf-8")
    _headers, runtime_rows = _table(configuration, "Toolkit runtime variables")
    assert set(runtime_rows).isdisjoint(REDACTION_ONLY)
    assert "OCR_USE_ANTHROPIC" not in runtime_rows


def test_example_local_defaults_match_the_pipeline() -> None:
    workflow = (PROJECT_ROOT / "examples" / "gitlab" / "ocr-review.gitlab-ci.yml").read_text(
        encoding="utf-8"
    )
    for name, value in {
        "OCR_VERSION": "v1.9.10",
        "OCR_SHA256": EXAMPLE_DEFAULTS["OCR_SHA256"],
        "OCR_TOOLKIT_VERSION": "0.7.1",
        "OCR_MAX_TOOLS": "30",
        "OCR_MAX_TOKENS_BUDGET": "0",
    }.items():
        assert f'{name}: "{value}"' in workflow
    assert (
        'export OCR_TOOLKIT_WHEEL="open_code_review_toolkit-${OCR_TOOLKIT_VERSION}-py3-none-any.whl"'
        in workflow
    )
    assert 'export OCR_TOOLKIT_WHEEL_SHA256="$(awk ' in workflow
    assert '--max-tools "${OCR_MAX_TOOLS:-30}"' in workflow
