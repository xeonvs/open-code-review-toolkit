"""Exercise target policy through one clean installed toolkit artifact."""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any


def _git(binary: str, repository: Path, *arguments: str) -> str:
    """Run one deterministic Git command in the owned synthetic repository."""

    completed = subprocess.run(
        [binary, *arguments],
        cwd=repository,
        check=True,
        text=True,
        capture_output=True,
    )
    return completed.stdout.strip()


def _write(repository: Path, path: str, content: str) -> None:
    """Write one synthetic repository file with its parent directories."""

    target = repository / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def _rpc(process: subprocess.Popen[str], request: dict[str, Any]) -> dict[str, Any]:
    """Exchange one newline-delimited JSON-RPC request with the installed MCP."""

    assert process.stdin is not None and process.stdout is not None
    process.stdin.write(json.dumps(request, separators=(",", ":")) + "\n")
    process.stdin.flush()
    line = process.stdout.readline()
    assert line, request
    response = json.loads(line)
    assert response.get("id") == request.get("id"), response
    assert "error" not in response, response
    return response


def _tool_payload(response: dict[str, Any]) -> dict[str, Any]:
    """Decode the one bounded text result returned by the evidence tool."""

    result = response["result"]
    assert result.get("isError") is not True
    blocks = result["content"]
    assert len(blocks) == 1 and blocks[0]["type"] == "text"
    return json.loads(blocks[0]["text"])


def main() -> int:
    """Create target policy evidence and query it through an installed MCP process."""

    if len(sys.argv) != 3:
        raise SystemExit("usage: installed_policy_e2e.py REPOSITORY EXPECTED_VERSION")
    repository = Path(sys.argv[1]).resolve()
    expected_version = sys.argv[2]
    home = repository.parent / "home"
    shutil.rmtree(repository, ignore_errors=True)
    shutil.rmtree(home, ignore_errors=True)
    repository.mkdir(parents=True, mode=0o700)
    home.mkdir(mode=0o700)

    # Create the hostile import before loading the toolkit. Isolated mode must
    # resolve the clean installed artifact rather than repository-controlled code.
    _write(
        repository,
        "ocr_toolkit/__init__.py",
        "raise RuntimeError('hostile repository shadow imported')\n",
    )
    os.chdir(repository)
    from ocr_toolkit import __version__, mcp_config
    from ocr_toolkit.evidence.artifacts import (
        prepare_artifact_directory,
        repository_artifacts,
        write_private_text,
    )
    from ocr_toolkit.evidence.collect import collect_repository_evidence
    from ocr_toolkit.evidence.project import render_bootstrap

    assert __version__ == expected_version
    git_binary = shutil.which("git")
    assert git_binary is not None
    _git(git_binary, repository, "init", "-q")
    _git(git_binary, repository, "config", "user.name", "Synthetic")
    _git(git_binary, repository, "config", "user.email", "synthetic@example.invalid")
    _write(repository, ".gitignore", ".review-context/\nocr_toolkit/\n")
    _write(
        repository,
        ".opencodereview/accepted-decisions.md",
        """# Accepted decisions

## Keep bounded retries
- Scope: services/api/**
- Category: reliability
- Owner: synthetic-platform
- Review after: 2099-01-01

The synthetic service deliberately uses one bounded retry.
""",
    )
    _write(repository, "AGENTS.md", "Synthetic root guidance.\n")
    _write(repository, "services/AGENTS.md", "Synthetic service guidance.\n")
    _write(repository, "services/api/AGENTS.md", "Synthetic API guidance.\n")
    _write(repository, "services/api/CLAUDE.md", "Target text that will be changed.\n")
    _write(repository, "services/api/app.py", "RETRIES = 1\n")
    for index in range(260):
        _write(
            repository,
            f"early/templates/page-{index:04}.j2",
            "before={{ value }}\n",
        )
    _write(repository, "late/templates/service.conf.j2", "before={{ port }}\n")
    _git(git_binary, repository, "add", ".")
    _git(git_binary, repository, "commit", "-qm", "target policy")
    base = _git(git_binary, repository, "rev-parse", "HEAD")
    _write(repository, "services/api/app.py", "RETRIES = 2\n")
    _write(repository, "late/templates/service.conf.j2", "after={{ port }}\n")
    _write(
        repository,
        ".opencodereview/accepted-decisions.md",
        """# Accepted decisions

## Source override

This source-only decision must not replace target policy.
""",
    )
    _write(
        repository,
        "services/api/CLAUDE.md",
        "Source-only guidance must be excluded.\n",
    )
    _git(git_binary, repository, "commit", "-qam", "source change")
    head = _git(git_binary, repository, "rev-parse", "HEAD")

    artifacts = repository_artifacts(repository)
    prepare_artifact_directory(artifacts)
    store = collect_repository_evidence(repository, base_ref=base, head_ref=head)
    store.write(artifacts.store)
    composition = mcp_config.compose_mcp_servers([], replace=True)
    write_private_text(
        artifacts.bootstrap,
        render_bootstrap(store, capabilities=composition.capabilities),
    )
    bootstrap = artifacts.bootstrap.read_text(encoding="utf-8")
    assert "keep-bounded-retries" in bootstrap
    assert "services/api/AGENTS.md" in bootstrap
    assert "deliberately uses one bounded retry" not in bootstrap
    assert "Synthetic API guidance" not in bootstrap
    assert "source-override" not in bootstrap
    assert "Source-only guidance" not in bootstrap

    builtin = composition.payload[mcp_config.BUILTIN_EVIDENCE_SERVER]
    assert builtin["tools"] == ["ocr_toolkit_evidence"]
    assert os.path.isabs(str(builtin["command"]))
    assert list(builtin["args"]) == ["-I", "-m", "ocr_toolkit.evidence"]
    process = subprocess.Popen(
        [str(builtin["command"]), *map(str, builtin["args"])],
        cwd=repository,
        env={"HOME": str(home), "PATH": ""},
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    initialized = _rpc(
        process,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "synthetic-client", "version": "1"},
            },
        },
    )
    assert initialized["result"]["serverInfo"] == {
        "name": "open-code-review-toolkit-evidence",
        "version": expected_version,
    }
    assert process.stdin is not None
    process.stdin.write('{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}\n')
    process.stdin.flush()
    tools = _rpc(
        process,
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
    )["result"]["tools"]
    assert len(tools) == 1 and tools[0]["name"] == "ocr_toolkit_evidence"
    assert tools[0]["annotations"] == {
        "readOnlyHint": True,
        "destructiveHint": False,
        "openWorldHint": False,
    }
    request_id = 3

    def call(arguments: dict[str, Any]) -> dict[str, Any]:
        """Call the installed evidence tool and advance its request identity."""

        nonlocal request_id
        response = _rpc(
            process,
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "tools/call",
                "params": {"name": "ocr_toolkit_evidence", "arguments": arguments},
            },
        )
        request_id += 1
        return _tool_payload(response)

    summary = call({"action": "summary"})
    assert summary["base"] == base and summary["head"] == head
    assert summary["schema_version"] == 3
    assert summary["policy"] == {
        "accepted_decisions": 1,
        "guidance_documents": 3,
        "structured_target_records": 4,
        "legacy_text_records": 0,
        "target_only": True,
        "authoritative_for_actions": False,
    }
    decisions = call({"action": "list", "kind": "repository.accepted_decision", "ref": "base"})[
        "records"
    ]
    assert len(decisions) == 1
    decision = decisions[0]
    assert decision["value"]["fact"]["matched_paths"] == [
        "services/api/CLAUDE.md",
        "services/api/app.py",
    ]
    assert "bounded retry" in decision["value"]["fact"]["rationale"]
    assert "source-only decision" not in decision["value"]["fact"]["rationale"]
    assert call({"action": "get", "id": decision["id"]})["record"] == decision
    assert (
        call({"action": "list", "kind": "repository.accepted_decision", "ref": "head"})["records"]
        == []
    )

    guidance = call(
        {
            "action": "list",
            "kind": "repository.guidance",
            "ref": "base",
            "page_size": 50,
        }
    )["records"]
    assert [item["source_path"] for item in guidance] == [
        "AGENTS.md",
        "services/AGENTS.md",
        "services/api/AGENTS.md",
    ]
    assert not any(item["source_path"] == "services/api/CLAUDE.md" for item in guidance)
    nested = guidance[-1]
    assert nested["value"]["fact"]["matched_paths"] == [
        "services/api/CLAUDE.md",
        "services/api/app.py",
    ]
    assert nested["value"]["fact"]["text"] == "Synthetic API guidance.\n"
    assert call({"action": "get", "id": nested["id"]})["record"] == nested
    assert call({"action": "list", "kind": "repository.guidance", "ref": "head"})["records"] == []

    prioritized_templates = call(
        {
            "action": "list",
            "kind": "template.file",
            "component": "late/templates",
            "ref": "head",
        }
    )["records"]
    assert len(prioritized_templates) == 1
    prioritized_template = prioritized_templates[0]
    assert prioritized_template["source_path"] == "late/templates/service.conf.j2"
    assert prioritized_template["component"] == "late/templates"
    assert prioritized_template["provenance"] == "framework plugin:jinja2"
    template_fact = prioritized_template["value"]["fact"]
    assert template_fact["schema_version"] == "repository.template-evidence/v1"
    assert template_fact["plugin"] == "jinja2"
    assert template_fact["engine"] == "jinja2"
    assert template_fact["detection"] == "jinja-extension"
    assert template_fact["rendered_extension"] == ".conf"
    assert template_fact["object_sha"] == _git(
        git_binary, repository, "rev-parse", f"{head}:late/templates/service.conf.j2"
    )

    process.stdin.close()
    assert process.wait(timeout=10) == 0
    assert process.stderr is not None
    assert process.stderr.read() == ""
    assert stat.S_IMODE(artifacts.directory.stat().st_mode) == 0o700
    assert stat.S_IMODE(artifacts.store.stat().st_mode) == 0o600
    assert stat.S_IMODE(artifacts.bootstrap.stat().st_mode) == 0o600
    assert _git(git_binary, repository, "status", "--short") == ""
    print(
        json.dumps(
            {
                "base": base,
                "head": head,
                "installed_version": expected_version,
                "policy": summary["policy"],
                "prioritized_template": {
                    "component": prioritized_template["component"],
                    "detection": prioritized_template["value"]["fact"]["detection"],
                    "engine": prioritized_template["value"]["fact"]["engine"],
                    "provenance": prioritized_template["provenance"],
                    "rendered_extension": prioritized_template["value"]["fact"][
                        "rendered_extension"
                    ],
                },
                "private_modes": True,
                "read_only": True,
                "repository_clean": True,
                "schema_version": 1,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
