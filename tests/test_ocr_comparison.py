"""Comparison qualification requires observable identity, content and failures."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from tests.test_ocr_compat import load_script

load_script()
from ocr_qualification.comparison import (
    TOOLS,
    ComparisonConversation,
    ToolCase,
    _comparison_repository,
    comparison_cases,
    comparison_sides_probe,
    validate_side_schema,
    validate_tool_result,
)
from ocr_qualification.core import CompatibilityError


def schemas():
    return [
        {
            "type": "function",
            "function": {
                "name": name,
                "parameters": {
                    "properties": {"side": {"type": "string", "enum": ["old", "new"]}},
                    "required": [],
                },
            },
        }
        for name in TOOLS
    ]


def history(case, identity="comparison-0", content="HEAD_MARKER"):
    return [
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": identity,
                    "type": "function",
                    "function": {"name": case.name, "arguments": json.dumps(case.arguments)},
                }
            ],
        },
        {"role": "tool", "tool_call_id": identity, "content": content},
    ]


def test_side_schema_accepts_equivalent_enum_order():
    validate_side_schema(schemas())


@pytest.mark.parametrize(
    "defect", ("missing", "duplicate", "required", "open", "type", "bad-required", "not-list")
)
def test_side_schema_requires_each_optional_closed_selector(defect):
    value = schemas()
    if defect == "missing":
        value.pop()
    elif defect == "duplicate":
        value.append(deepcopy(value[0]))
    elif defect == "required":
        value[0]["function"]["parameters"]["required"] = ["side"]
    elif defect == "open":
        value[0]["function"]["parameters"]["properties"]["side"]["enum"].append("base")
    elif defect == "type":
        value[0]["function"]["parameters"]["properties"]["side"]["type"] = "object"
    elif defect == "bad-required":
        value[0]["function"]["parameters"]["required"] = "side"
    else:
        value = None
    with pytest.raises(CompatibilityError):
        validate_side_schema(value)


def test_observation_requires_exact_call_arguments_and_actual_tool_result():
    case = ToolCase(
        "file_read", {"file_path": "shared.txt", "side": "new"}, ("HEAD_MARKER",), ("BASE_MARKER",)
    )
    validate_tool_result(history(case), case, "comparison-0")


@pytest.mark.parametrize(
    "defect",
    (
        "no-call",
        "no-result",
        "duplicate-call",
        "duplicate-result",
        "name",
        "path",
        "side",
        "boolean",
        "malformed",
        "echo",
        "wrong-content",
        "forbidden",
        "typed-content",
        "not-list",
    ),
)
def test_unbound_or_inexact_observations_cannot_establish_side_proof(defect):
    case = ToolCase(
        "file_read", {"file_path": "shared.txt", "side": True}, ("HEAD_MARKER",), ("BASE_MARKER",)
    )
    messages = history(case)
    if defect == "no-call":
        messages.pop(0)
    elif defect == "no-result":
        messages.pop()
    elif defect == "duplicate-call":
        messages[0]["tool_calls"].append(deepcopy(messages[0]["tool_calls"][0]))
    elif defect == "duplicate-result":
        messages.append(deepcopy(messages[-1]))
    elif defect == "name":
        messages[0]["tool_calls"][0]["function"]["name"] = "code_search"
    elif defect in {"path", "side", "boolean"}:
        args = {
            **case.arguments,
            {"path": "file_path", "side": "side", "boolean": "side"}[defect]: {
                "path": "other.txt",
                "side": "old",
                "boolean": 1,
            }[defect],
        }
        messages[0]["tool_calls"][0]["function"]["arguments"] = json.dumps(args)
    elif defect == "malformed":
        messages[0]["tool_calls"][0]["function"]["arguments"] = "{"
    elif defect == "echo":
        messages[-1]["role"] = "assistant"
    elif defect == "wrong-content":
        messages[-1]["content"] = "BASE_MARKER"
    elif defect == "forbidden":
        messages[-1]["content"] = "HEAD_MARKER BASE_MARKER"
    elif defect == "typed-content":
        messages[-1]["content"] = ["HEAD_MARKER"]
    else:
        messages = None
    with pytest.raises(CompatibilityError):
        validate_tool_result(messages, case, "comparison-0")


def test_script_cannot_finish_before_observed_result_and_has_an_exchange_bound():
    case = ToolCase("file_read", {"file_path": "shared.txt"}, ("HEAD_MARKER",))
    script = ComparisonConversation([case])
    function, identity = script({"tools": schemas(), "messages": []})
    assert function["name"] == case.name and identity == "comparison-0"
    assert not script.complete
    function, identity = script({"messages": history(case)})
    assert function == {"name": "task_done", "arguments": "{}"}
    assert identity == "comparison-done" and script.complete
    script.requests = 3
    with pytest.raises(CompatibilityError, match="budget"):
        script({"messages": history(case)})


def test_case_matrix_is_noncontradictory_and_covers_each_tool_and_selector_type():
    cases = comparison_cases("a" * 40)
    for case in cases:
        assert not set(case.contains).intersection(case.excludes)
    for name in TOOLS:
        selectors = {
            json.dumps(case.arguments.get("side", "omitted")) for case in cases if case.name == name
        }
        assert selectors >= {'"omitted"', '"new"', '"old"', '"base"', "null", "true", "[]", "{}"}


def test_negative_matrix_isolates_the_native_per_tool_failure_streak():
    cases = comparison_cases("a" * 40)
    assert len(cases) < 80
    for index, case in enumerate(cases):
        if case.error:
            control = cases[index + 1]
            assert control.name == case.name and not control.error
            assert control.arguments.get("side", "new") == "new"


@pytest.mark.parametrize(
    "wrong_name", ("renamed-target.txt", "renamed-worktree.txt", "renamed-untracked.txt")
)
def test_old_find_cannot_admit_checkout_paths_alongside_the_base_result(wrong_name):
    case = next(
        case
        for case in comparison_cases("a" * 40)
        if case.name == "file_find" and case.arguments == {"query_name": "renamed-", "side": "old"}
    )
    actual = "\n".join((*case.contains, wrong_name))
    with pytest.raises(CompatibilityError, match="wrong immutable side"):
        validate_tool_result(history(case, content=actual), case, "comparison-0")


def test_find_fixture_distinguishes_base_head_target_index_and_worktree(tmp_path):
    module = load_script()
    repo, base, head, environment = _comparison_repository(tmp_path)

    def names(*args):
        return set(module.execution._run(["git", *args], cwd=repo, env=environment).splitlines())

    base_names = names("ls-tree", "-r", "--name-only", base)
    head_names = names("ls-tree", "-r", "--name-only", head)
    target_names = names("ls-tree", "-r", "--name-only", "HEAD")
    index_names = names("ls-files")
    worktree_names = {entry.name for entry in repo.iterdir() if entry.is_file()}
    assert base_names & {"renamed-old.txt", "deleted-only.txt"} == {
        "renamed-old.txt",
        "deleted-only.txt",
    }
    assert "renamed-new.txt" in head_names
    assert "renamed-target.txt" in target_names
    assert "renamed-worktree.txt" in index_names
    assert {"renamed-worktree.txt", "renamed-untracked.txt"} <= worktree_names
    assert "renamed-old.txt" not in head_names | target_names | index_names | worktree_names
    assert "deleted-only.txt" not in head_names | target_names | index_names | worktree_names


def test_native_comparison_observes_immutable_sides(tmp_path, qualified_native_ocr):
    binary, version = qualified_native_ocr("OCR_GITLINK_QUALIFY_BINARY")
    module = load_script()
    if module.core._version(version) < module.contracts.history.HISTORICAL_CUTOFF:
        pytest.skip("comparison-side probe belongs to the live qualification epoch")
    observed = comparison_sides_probe(Path(binary), tmp_path)
    assert observed["result"] == "passed"
