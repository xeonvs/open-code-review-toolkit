"""Adjacent OCR epoch changes must not reinterpret already published evidence."""

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from copy import deepcopy

import pytest

from ocr_toolkit.preflight import RECOMMENDED_OCR_VERSION
from tests.support import PROJECT_ROOT
from tests.test_ocr_compat import current_contracts, load_script


def test_1135_frozen_readback_does_not_follow_new_live_inputs(monkeypatch):
    module = load_script()
    evidence = module.core.load_json(PROJECT_ROOT / "compatibility/evidence/ocr-1.13.5.json")
    original = deepcopy(evidence)
    monkeypatch.setattr(module.settings, "CURRENT_LANGUAGE_RULES", {"new/Program.cs": "**/*.cs"})
    monkeypatch.setattr(module.settings, "CURRENT_NUMERIC_CLI_CONTRACT", {})
    monkeypatch.setattr(module.settings, "CURRENT_DEFAULT_EXCLUDED_PATHS", ())

    module.contracts._validate_evidence_contracts("1.13.5", evidence)
    assert evidence == original


@pytest.mark.parametrize("arguments", [("--help",), ("validate",)])
def test_metadata_cli_does_not_import_runtime_packages(tmp_path, arguments):
    (tmp_path / "ocr_toolkit.py").write_text(
        'raise AssertionError("metadata command imported the runtime")\n'
    )
    environment = dict(os.environ, PYTHONPATH=str(tmp_path), PYTHONDONTWRITEBYTECODE="1")
    completed = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts/ocr_compat.py"), *arguments],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stderr
    assert "metadata command imported the runtime" not in completed.stderr


def test_1135_fresh_execution_is_refused_before_a_probe():
    module = load_script()
    with pytest.raises(module.core.CompatibilityError, match="frozen readback-only"):
        module.contracts._require_live_qualification_version("1.13.5")


def test_current_live_selection_retains_csharp_and_nested_starlark():
    module = load_script()
    rules = module.contracts._language_rules_for_version(RECOMMENDED_OCR_VERSION)
    assert rules["app/src/Program.cs"] == "**/*.cs"
    for path in ("bazel/rules.bzl", "bazel/defs.bazel", "bazel/config.star"):
        assert rules[path] == "**/*.{bzl,bazel,star}"
    for path in ("BUILD", "WORKSPACE", "nested/BUILD", "nested/WORKSPACE"):
        assert rules[path] == "**/{BUILD,WORKSPACE}"


@pytest.mark.parametrize("field", ["csharp_context_probe", "stream_override_probe"])
def test_1136_missing_consumed_proof_cannot_be_promoted(field):
    module = load_script()
    observed = current_contracts(module, "1.13.6")
    observed.pop(field)
    with pytest.raises(module.core.CompatibilityError, match=field):
        module.contracts._validate_contracts_for_version("1.13.6", observed)


def test_extensionless_selection_has_paths_without_invented_extensions():
    module = load_script()
    observed = current_contracts(module, "1.13.6")["language_rule_probe"]
    assert "" not in observed["extensions"]
    assert {"BUILD", "WORKSPACE", "nested/BUILD", "nested/WORKSPACE"}.issubset(observed["paths"])
    assert observed["selected"] == len(observed["paths"])
    assert len(observed["extensions"]) < observed["selected"]


@pytest.mark.parametrize(
    "defect",
    [
        None,
        "wrong-tool",
        "wrong-path",
        "wrong-id",
        "wrong-role",
        "missing-value",
        "duplicate-id",
        "bad-arguments",
    ],
)
def test_context_observation_requires_the_actual_file_read(defect):
    module = load_script()
    call = {
        "id": "context-1",
        "function": {
            "name": "file_read",
            "arguments": json.dumps({"file_path": "app/Project.csproj"}),
        },
    }
    response = {
        "role": "tool",
        "tool_call_id": "context-1",
        "content": "framework=net10.0; nullable=enable",
    }
    if defect == "wrong-tool":
        call["function"]["name"] = "file_read_diff"
    elif defect == "wrong-path":
        call["function"]["arguments"] = '{"file_path":"elsewhere.xml"}'
    elif defect == "wrong-id":
        response["tool_call_id"] = "unknown"
    elif defect == "wrong-role":
        response["role"] = "user"
    elif defect == "missing-value":
        response["content"] = "framework=net10.0"
    elif defect == "bad-arguments":
        call["function"]["arguments"] = "{"
    calls = [call, deepcopy(call)] if defect == "duplicate-id" else [call]
    observed = module.peer.context_read_observations(
        [{"role": "assistant", "tool_calls": calls}, response],
        {"app/Project.csproj": ("framework=net10.0", "nullable=enable")},
    )
    assert observed == ({"app/Project.csproj"} if defect is None else set())


def test_stream_capture_keeps_only_bounded_control_metadata():
    module = load_script()
    with module.peer._stub_gateway(capture_controls=True) as url:
        request = urllib.request.Request(
            url + "/messages",
            data=json.dumps(
                {
                    "stream": False,
                    "messages": [{"role": "user", "content": "synthetic omitted body"}],
                }
            ).encode(),
            headers={"Content-Type": "application/json"},
        )
        with pytest.raises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(request, timeout=5)
        try:
            assert caught.value.code == 400
        finally:
            caught.value.close()
        assert module.peer._StubHandler.control_requests == [
            {
                "path": "/v1/messages",
                "stream_present": True,
                "stream_boolean": False,
                "stream_options_present": False,
            }
        ]


@pytest.mark.parametrize("arguments", ("{", "[]", '{"file_path":"elsewhere.xml"}'))
def test_invalid_first_read_still_consumes_its_call_identity(arguments):
    module = load_script()
    observed = module.peer.context_read_observations(
        [
            {
                "role": "assistant",
                "tool_calls": [
                    {"id": "same", "function": {"name": "file_read", "arguments": arguments}},
                    {
                        "id": "same",
                        "function": {
                            "name": "file_read",
                            "arguments": '{"file_path":"app/Project.csproj"}',
                        },
                    },
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "same",
                "content": "framework=net10.0; nullable=enable",
            },
        ],
        {"app/Project.csproj": ("framework=net10.0", "nullable=enable")},
    )
    assert not observed
