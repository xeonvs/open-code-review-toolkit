"""New native exclusion and tool-declaration proof must fail on inconsistent observations."""

from copy import deepcopy
from pathlib import Path

import pytest

from tests.test_ocr_compat import load_script
from tests.test_result_contract import manifest_result


@pytest.fixture
def excluded_result():
    """Build one selected file and a separate non-dispatched exclusion."""
    value = manifest_result("complete", selected=["selected"], completed=["selected"])
    value["manifest"]["coverage"]["selected"][0]["path"] = "example.py"
    value["manifest"]["coverage"]["excluded"] = [
        {"item_id": "excluded", "path": "unknown.data", "exclude_reason": "unsupported_ext"}
    ]
    return value


@pytest.mark.parametrize(
    "defect",
    [
        None,
        "missing",
        "duplicate",
        "overlap",
        "path-overlap",
        "missing-selected-path",
        "wrong-path",
        "wrong-reason",
        "fingerprint",
        "terminal",
    ],
)
def test_exclusions_do_not_widen_or_repair_selected_coverage(excluded_result, defect):
    """Reject inconsistent exclusion identity and terminal partition independently."""
    module = load_script()
    value = deepcopy(excluded_result)
    coverage = value["manifest"]["coverage"]
    item = coverage["excluded"][0]
    if defect == "missing":
        coverage.pop("excluded")
    elif defect == "duplicate":
        coverage["excluded"].append(dict(item))
    elif defect == "overlap":
        item["item_id"] = "selected"
    elif defect == "path-overlap":
        coverage["selected"][0]["path"] = item["path"]
    elif defect == "missing-selected-path":
        coverage["selected"][0].pop("path")
    elif defect == "wrong-path":
        item["path"] = "other.data"
    elif defect == "wrong-reason":
        item["exclude_reason"] = "none"
    elif defect == "fingerprint":
        item["fingerprint"] = "unexpected-source-digest"
    elif defect == "terminal":
        coverage["completed"] = []
    if defect is None:
        module.contracts.exclusions.validate_exclusions(value, {"unknown.data": "unsupported_ext"})
    else:
        with pytest.raises(module.core.CompatibilityError):
            module.contracts.exclusions.validate_exclusions(
                value, {"unknown.data": "unsupported_ext"}
            )


@pytest.mark.parametrize("field", ["excluded_coverage_probe", "tool_declarations_probe"])
def test_live_promotion_requires_each_new_consumed_proof(field):
    """Missing new proof cannot inherit admission from a successful older epoch."""
    from tests.test_ocr_compat import current_contracts

    module = load_script()
    value = current_contracts(module, "1.13.9")
    value.pop(field)
    with pytest.raises(module.core.CompatibilityError, match=field):
        module.contracts._validate_contracts_for_version("1.13.9", value)


def test_native_exclusions_keep_selected_effective_paths_disjoint(tmp_path, qualified_native_ocr):
    """Cross the path/ID partition validator with an actual qualified native result."""
    binary, _version = qualified_native_ocr("OCR_GITLINK_QUALIFY_BINARY")
    module = load_script()
    observed = module.contracts.exclusions.exclusion_probe(Path(binary), tmp_path)
    assert observed == module.contracts.exclusions.EXPECTED


def test_later_round_must_retain_the_same_tool_declarations():
    """A fresh message history does not justify losing previously consumed tools."""
    module = load_script()
    conversation = module.contracts.declarations.DeclarationConversation()
    request = {
        "tools": [
            {"function": {"name": name}} for name in ("file_read", "code_comment", "task_done")
        ]
    }
    conversation(request)
    conversation.index = 4
    request["tools"].append({"function": {"name": "unexpected"}})
    with pytest.raises(module.core.CompatibilityError, match="second review round"):
        conversation(request)


@pytest.mark.parametrize("option", ["--repo", "--resume"])
@pytest.mark.parametrize("attached", [False, True])
def test_native_conveniences_cannot_replace_toolkit_execution_ownership(option, attached):
    """Reject competing repository/session inputs in the shared provider path."""
    from ocr_toolkit import review_runner

    args = [option + "=operator-value"] if attached else [option, "operator-value"]
    with pytest.raises(review_runner.ReviewRunnerError, match="managed by ocr-ci review"):
        review_runner._reject_owned_review_options(args)


def test_registered_reader_cannot_execute_in_restricted_native_grace(
    tmp_path, qualified_native_ocr
):
    """Measure actual execution counts for a registered but unadvertised native read."""
    binary, _version = qualified_native_ocr("OCR_GITLINK_QUALIFY_BINARY")
    module = load_script()
    environment = module.execution._isolated_probe_environment(tmp_path / "git-home")
    repository, base, head = module.execution._synthetic_repo(tmp_path, environment)
    rounds, verdict = module.probes.numeric._effective_max_tools_probe(
        Path(binary),
        repository,
        base,
        head,
        tmp_path,
        value=50,
        expected_diagnostic=None,
        grace_task_done=False,
    )
    assert rounds == 50
    assert verdict == {"completed": False, "limit_warning": True}
