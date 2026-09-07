"""Frozen readback checks for already-qualified OCR evidence; never execute binaries."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, NoReturn

HISTORICAL_CUTOFF = (1, 11, 4)

ARCHIVED_NUMERIC_CLI_CONTRACT: dict[str, object] = {
    "max_tokens_budget": {
        "cases": {
            "invalid_below": {"effective": None, "input": -1, "outcome": "rejected"},
            "minimum": {"effective": 1, "input": 1, "outcome": "accepted"},
            "omitted": {"effective": "unlimited", "input": None, "outcome": "accepted"},
            "representative": {"effective": 30_000, "input": 30_000, "outcome": "accepted"},
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
}


def language_extensions(version_tuple: tuple[int, int, int]) -> list[str]:
    """Return the language inventory recorded in the historical evidence epochs."""

    extensions = {".pug", ".sv", ".v", ".vh", ".vhd", ".vhdl"}
    if version_tuple >= (1, 11, 2):
        extensions.update({".cjs", ".cxx", ".hxx", ".mjs"})
    return sorted(extensions)


def validate_contracts(
    version: str,
    version_tuple: tuple[int, int, int],
    evidence: dict[str, Any],
    fail: Callable[[str], NoReturn],
) -> None:
    """Validate old evidence using its original semantics, independent of the live suite."""

    if version_tuple >= HISTORICAL_CUTOFF:
        fail("current evidence cannot use historical validation")
    if version_tuple >= (1, 9, 5):
        contracts = evidence.get("contracts")
        required_flags = (
            contracts.get("required_review_flags") if isinstance(contracts, dict) else None
        )
        budget_probe = contracts.get("review_budget_probe") if isinstance(contracts, dict) else None
        if not isinstance(required_flags, list) or "--max-tokens-budget" not in required_flags:
            fail(f"evidence does not qualify the review budget flag for {version}")
        expected_budget_probe: dict[str, object] = {
            "budget": 30_000,
            "completed": 2,
            "failed_budget": 1,
            "partial_findings_preserved": True,
            "result": "passed",
            "selected": 3,
        }
        if version_tuple >= (1, 11, 1):
            expected_budget_probe.update({"grouping_requests": 0, "grouping_strategy": "per_file"})
        if budget_probe != expected_budget_probe:
            fail(f"evidence does not qualify partial review budget behavior for {version}")
    if version_tuple >= (1, 10, 0):
        contracts = evidence.get("contracts")
        required_flags = (
            contracts.get("required_review_flags") if isinstance(contracts, dict) else None
        )
        capabilities = (
            contracts.get("optional_capabilities") if isinstance(contracts, dict) else None
        )
        if not isinstance(required_flags, list) or "--effort" not in required_flags:
            fail(f"evidence does not qualify the review effort flag for {version}")
        if not isinstance(capabilities, list) or not {
            "review_effort",
            "semantic_grouping",
        }.issubset(capabilities):
            fail(f"evidence does not qualify effort and grouping for {version}")
        expected_grouping_probe = {
            "default_effort": "medium",
            "filter_requests": 1,
            "grouping_requests": 1,
            "main_requests": 3,
            "result": "passed",
            "review_rounds": 2,
        }
        if version_tuple >= (1, 10, 2):
            expected_grouping_probe["grouping_completion_cap"] = 16_384
        if version_tuple >= (1, 11, 1):
            expected_grouping_probe.update(
                {
                    "files": 4,
                    "prior_finding_semantics": "filter_survivors_as_confirmed",
                    "recheck_instruction_requests": 3,
                }
            )
        if contracts.get("semantic_grouping_probe") != expected_grouping_probe:
            fail(f"evidence does not qualify semantic grouping behavior for {version}")
        if version_tuple >= (1, 11, 1) and contracts.get("small_change_grouping_probe") != {
            "grouping_requests": 0,
            "high_churn": "per_file",
            "low_churn": "bundle_all",
            "result": "passed",
            "single_file": "per_file",
            "threshold_files": 4,
        }:
            fail(f"evidence does not qualify small-change grouping behavior for {version}")
        expected_language_probe = {
            "excluded_extensions": [".svh"],
            "extensions": language_extensions(version_tuple),
            "result": "passed",
            "rule_source": "system_builtin",
            "selected": len(language_extensions(version_tuple)),
        }
        if (
            version_tuple >= (1, 11, 1)
            and contracts.get("language_rule_probe") != expected_language_probe
        ):
            fail(f"evidence does not qualify built-in language rules for {version}")
        if contracts.get("completion_cap_probe") != {
            "explicit": 4_096,
            "inherited": 16_384,
            "result": "passed",
            "wire_field": "max_completion_tokens",
        }:
            fail(f"evidence does not qualify the completion cap for {version}")
        if contracts.get("numeric_cli_probe") != ARCHIVED_NUMERIC_CLI_CONTRACT:
            fail(f"evidence does not qualify numeric CLI boundaries for {version}")
