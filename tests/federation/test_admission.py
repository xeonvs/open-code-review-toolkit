"""Bounded validator and nested argument authorization through their production owners."""

import pytest

from ocr_toolkit.context.dlp import ForbiddenMatcher
from ocr_toolkit.federation import FederationError, ToolPolicy
from ocr_toolkit.federation.admission import arguments, compile_schema

MATCHER = ForbiddenMatcher.compile(())


@pytest.mark.parametrize(
    "schema",
    [
        {"type": "object", "$ref": "https://synthetic.invalid/schema"},
        {"type": "object", "properties": {"value": {"type": "string", "pattern": "(a+)+$"}}},
        {
            "type": "object",
            "properties": {"value": {"type": "string", "x-mcp-header": "X-Authority"}},
        },
        {"type": "object", "$schema": "https://synthetic.invalid/draft"},
        {"type": "object", "properties": {str(i): {} for i in range(65)}},
        {"type": "object", "anyOf": [{}] * 9},
    ],
)
def test_unsupported_schema_constraints_are_rejected(schema: object) -> None:
    with pytest.raises(FederationError, match="schema_invalid"):
        compile_schema(schema, MATCHER)


def test_nested_origins_and_dlp_are_independent_of_schema() -> None:
    validator = compile_schema({"type": "object"}, MATCHER)
    policy = ToolPolicy(
        "lookup", "synthetic__lookup", resource_origins=("https://synthetic.invalid",)
    )
    values = {"nested": [{"link": "https://synthetic.invalid/document"}]}
    assert arguments(values, policy, validator, MATCHER)[0] == values
    for url in (
        "https://foreign.invalid/document",
        "http://synthetic.invalid",
        "//synthetic.invalid",
        "ftp://synthetic.invalid",
        "https://user@synthetic.invalid",
    ):
        with pytest.raises(FederationError, match="origin_denied"):
            arguments({"nested": [{"link": url}]}, policy, validator, MATCHER)
    with pytest.raises(FederationError, match="dlp_rejected"):
        arguments(
            {"nested": ["controlled protected phrase"]},
            policy,
            validator,
            ForbiddenMatcher.compile(("controlled protected phrase",)),
        )


def test_deep_and_oversized_arguments_fail_before_validation_work() -> None:
    validator = compile_schema({"type": "object"}, MATCHER)
    value = {"leaf": "controlled"}
    for _ in range(17):
        value = {"nested": value}
    with pytest.raises(FederationError, match="oversized"):
        arguments(value, ToolPolicy("echo", "synthetic__echo"), validator, MATCHER)
    with pytest.raises(FederationError, match="oversized"):
        arguments({"text": "x" * 32768}, ToolPolicy("echo", "synthetic__echo"), validator, MATCHER)
