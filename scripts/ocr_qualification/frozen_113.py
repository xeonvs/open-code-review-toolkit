"""Frozen OCR 1.13.0–1.13.5 readback; no live settings, I/O or execution."""

from __future__ import annotations

import copy
from collections.abc import Callable
from typing import Any, NoReturn

REQUIRED_FLAGS = frozenset(
    [
        "--audience",
        "--background-file",
        "--effort",
        "--format",
        "--from",
        "--max-tokens-budget",
        "--max-tools",
        "--preview",
        "--rule",
        "--to",
    ]
)

EXPECTED = {
    "numeric_cli_probe": {
        "grace_rounds": {
            "no_task_done": {"completed": False, "limit_warning": True},
            "task_done": {"completed": True, "limit_warning": True},
        },
        "max_tokens_budget": {
            "cases": {
                "invalid_below": {"effective": None, "input": -1, "outcome": "rejected"},
                "minimum": {"effective": 1, "input": 1, "outcome": "accepted"},
                "omitted": {"effective": "unlimited", "input": None, "outcome": "accepted"},
                "representative": {"effective": 30000, "input": 30000, "outcome": "accepted"},
                "sentinel": {"effective": "unlimited", "input": 0, "outcome": "accepted"},
            },
            "maximum": None,
            "owner": "ocr-cli",
        },
        "max_tools": {
            "cases": {
                "invalid_below": {"effective": None, "input": -1, "outcome": "rejected"},
                "minimum": {"effective": 100, "input": 50, "outcome": "accepted"},
                "minimum_minus_one": {
                    "effective": 100,
                    "input": 49,
                    "outcome": "normalized",
                    "reported_normalization": 50,
                },
                "omitted": {"effective": 100, "input": None, "outcome": "accepted"},
                "representative": {"effective": 101, "input": 101, "outcome": "accepted"},
                "sentinel": {"effective": 100, "input": 0, "outcome": "accepted"},
            },
            "maximum": None,
            "owner": "ocr-template-or-higher-cli",
            "reported_minimum": 50,
        },
        "result": "passed",
    },
    "review_budget_probe": {
        "budget": 30000,
        "completed": 2,
        "failed_budget": 1,
        "grouping_requests": 0,
        "grouping_strategy": "per_file",
        "partial_findings_preserved": True,
        "result": "passed",
        "selected": 3,
    },
    "semantic_grouping_probe": {
        "default_effort": "medium",
        "files": 4,
        "filter_requests": 1,
        "grouping_completion_cap": 16384,
        "grouping_requests": 1,
        "main_requests": 3,
        "prior_finding_semantics": "filter_survivors_as_confirmed",
        "recheck_instruction_requests": 3,
        "result": "passed",
        "review_rounds": 2,
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
        "default_excluded_paths": [
            "src/test/kotlin/scripts/Example.kts",
            "test/parser.ml",
            "src/test_helpers.py",
            "src/WidgetTest.fs",
            "node_modules/example/index.ts",
            "dist/generated.js",
        ],
        "excluded_extensions": [".svh"],
        "extensions": [
            ".cjs",
            ".cxx",
            ".fs",
            ".fsi",
            ".fsx",
            ".glsl",
            ".hlsl",
            ".hxx",
            ".j2",
            ".jinja2",
            ".kts",
            ".metal",
            ".mjs",
            ".ml",
            ".mli",
            ".mm",
            ".nu",
            ".ps1",
            ".psd1",
            ".psm1",
            ".pug",
            ".pyi",
            ".re",
            ".rego",
            ".rei",
            ".sv",
            ".tofu",
            ".v",
            ".vh",
            ".vhd",
            ".vhdl",
            ".wgsl",
        ],
        "m_routing": "matlab_and_objective_c",
        "result": "passed",
        "rule_source": "system_builtin",
        "selected": 32,
    },
    "completion_cap_probe": {
        "explicit": 4096,
        "inherited": 16384,
        "result": "passed",
        "wire_field": "max_completion_tokens",
    },
    "reasoning_effort_probe": {
        "efforts": ["unset", "none", "high"],
        "protocols": ["openai", "openai-responses"],
        "provider_acceptance": "not-tested",
        "responses_siblings_preserved": True,
        "result": "passed",
    },
    "comment_arguments_probe": {
        "comments_per_batch": 2,
        "failure_arguments_preserved": True,
        "intact_cases": ["array", "serialized", "repaired"],
        "repair_warning": True,
        "result": "passed",
        "suspect_batch_rejected": True,
    },
}

EARLY_LANGUAGE = {
    "default_excluded_paths": [
        "src/test/kotlin/scripts/Example.kts",
        "test/parser.ml",
        "src/test_helpers.py",
        "src/WidgetTest.fs",
        "node_modules/example/index.ts",
        "dist/generated.js",
    ],
    "excluded_extensions": [".svh"],
    "extensions": [
        ".cjs",
        ".cxx",
        ".fs",
        ".fsi",
        ".fsx",
        ".hxx",
        ".j2",
        ".jinja2",
        ".kts",
        ".mjs",
        ".ml",
        ".mli",
        ".mm",
        ".ps1",
        ".pug",
        ".pyi",
        ".re",
        ".rego",
        ".rei",
        ".sv",
        ".v",
        ".vh",
        ".vhd",
        ".vhdl",
    ],
    "m_routing": "matlab_and_objective_c",
    "result": "passed",
    "rule_source": "system_builtin",
    "selected": 24,
}


# Immutable 1.13.5 delta; never derive historical readback from live settings.
PATCH_5 = {
    "numeric_cli_probe": {
        "grace_rounds": {
            "no_task_done": {"completed": False, "limit_warning": True},
            "task_done": {"completed": True, "limit_warning": True},
        },
        "max_tokens_budget": {
            "cases": {
                "invalid_below": {"effective": None, "input": -1, "outcome": "rejected"},
                "minimum": {"effective": 1, "input": 1, "outcome": "accepted"},
                "omitted": {"effective": "unlimited", "input": None, "outcome": "accepted"},
                "representative": {"effective": 30000, "input": 30000, "outcome": "accepted"},
                "sentinel": {"effective": "unlimited", "input": 0, "outcome": "accepted"},
            },
            "maximum": None,
            "owner": "ocr-cli",
        },
        "max_tools": {
            "cases": {
                "invalid_below": {"effective": None, "input": -1, "outcome": "rejected"},
                "lower_override": {"effective": 75, "input": 75, "outcome": "accepted"},
                "minimum": {"effective": 50, "input": 50, "outcome": "accepted"},
                "minimum_minus_one": {
                    "effective": 50,
                    "input": 49,
                    "outcome": "normalized",
                    "reported_normalization": 50,
                },
                "omitted": {"effective": 100, "input": None, "outcome": "accepted"},
                "representative": {"effective": 125, "input": 125, "outcome": "accepted"},
                "sentinel": {"effective": 100, "input": 0, "outcome": "accepted"},
                "template_value": {"effective": 100, "input": 100, "outcome": "accepted"},
            },
            "manifest_limit_verified": True,
            "maximum": None,
            "owner": "ocr-cli-or-template-default",
            "reported_minimum": 50,
        },
        "result": "passed",
    },
    "language_rule_probe": {
        "default_excluded_paths": [
            "src/test/kotlin/scripts/Example.kts",
            "test/parser.ml",
            "src/test_helpers.py",
            "src/WidgetTest.fs",
            "node_modules/example/index.ts",
            "dist/generated.js",
        ],
        "excluded_extensions": [".svh"],
        "extensions": [
            ".cjs",
            ".cxx",
            ".ejs",
            ".erb",
            ".fs",
            ".fsi",
            ".fsx",
            ".glsl",
            ".haml",
            ".hlsl",
            ".hxx",
            ".j2",
            ".jinja2",
            ".jsonc",
            ".kts",
            ".liquid",
            ".metal",
            ".mjs",
            ".ml",
            ".mli",
            ".mm",
            ".njk",
            ".nu",
            ".ps1",
            ".psd1",
            ".psm1",
            ".pug",
            ".pyi",
            ".re",
            ".rego",
            ".rei",
            ".scala",
            ".slim",
            ".sv",
            ".tofu",
            ".v",
            ".vh",
            ".vhd",
            ".vhdl",
            ".wgsl",
        ],
        "m_routing": "matlab_and_objective_c",
        "result": "passed",
        "rule_source": "system_builtin",
        "selected": 40,
    },
}


def validate_contracts(
    version: tuple[int, int, int], value: Any, fail: Callable[[str], NoReturn]
) -> None:
    """Apply exactly the consumed pre-override contract without reinterpreting it."""
    if not (1, 13, 0) <= version < (1, 13, 6):
        fail("evidence does not belong to the frozen 1.13 epoch")
    if not isinstance(value, dict):
        fail("historical qualification contracts are missing")
    flags = value.get("required_review_flags")
    capabilities = value.get("optional_capabilities")
    if (
        not isinstance(flags, list)
        or not all(isinstance(flag, str) for flag in flags)
        or not REQUIRED_FLAGS.issubset(flags)
        or not isinstance(capabilities, list)
        or not all(isinstance(capability, str) for capability in capabilities)
        or not {"review_effort", "semantic_grouping"}.issubset(capabilities)
    ):
        fail("historical qualification omitted required CLI capabilities")
    expected = copy.deepcopy(EXPECTED)
    if version == (1, 13, 5):
        expected.update(copy.deepcopy(PATCH_5))
    if version < (1, 13, 2):
        expected["language_rule_probe"] = EARLY_LANGUAGE
    if version == (1, 13, 0):
        expected["numeric_cli_probe"]["grace_rounds"] = {
            "task_done": {"completed": False, "limit_warning": False},
            "no_task_done": {"completed": False, "limit_warning": False},
        }
    for name, contract in expected.items():
        if value.get(name) != contract:
            fail(f"historical qualification contract disagrees: {name}")
    if value.get("version_probe") != "passed" or value.get("preview_probe") != {
        "format": "json",
        "path": "example.py",
        "result": "passed",
        "session_store_created": False,
    }:
        fail("historical qualification omitted isolated version/preview proof")
    result = value.get("result_contract_probe")
    if (
        not isinstance(result, dict)
        or result.get("result") != "passed"
        or result.get("manifest_schema") != "ocr.run-manifest/v1"
        or result.get("normalized_outcome") != "clean"
    ):
        fail("historical qualification omitted the review-result contract")
