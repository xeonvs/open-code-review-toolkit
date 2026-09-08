"""Cross installed CLI, immutable Git and real stdio MCP with a synthetic OCR peer."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def rpc(process: subprocess.Popen[str], request: dict[str, Any]) -> dict[str, Any]:
    """Exchange a single request with the real installed evidence server."""

    assert process.stdin is not None and process.stdout is not None
    process.stdin.write(json.dumps(request) + "\n")
    process.stdin.flush()
    response = json.loads(process.stdout.readline())
    assert response.get("id") == request["id"] and "error" not in response, response
    return response["result"]


def peer(mode: str) -> int:
    """Stand in for OCR only; evidence and action attribution remain real."""

    if "--preview" in sys.argv:
        return 0
    config = json.loads((Path.home() / ".opencodereview" / "config.json").read_text())
    server = config["mcp_servers"]["ocr_toolkit_evidence"]
    if mode == "verified":
        process = subprocess.Popen(
            [server["command"], *server["args"]],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            rpc(
                process,
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "synthetic-review-peer", "version": "1"},
                    },
                },
            )
            registry = rpc(process, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
            assert "ocr_toolkit_evidence" in {tool["name"] for tool in registry["tools"]}
            summary = rpc(
                process,
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {"name": "ocr_toolkit_evidence", "arguments": {"action": "summary"}},
                },
            )
            assert summary.get("isError") is not True
        finally:
            process.communicate(timeout=10)
            assert process.returncode == 0
    external = config["mcp_servers"]["synthetic_context"]
    process = subprocess.Popen(
        [external["command"], *external["args"]],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        response = rpc(
            process,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "synthetic_lookup", "arguments": {}},
            },
        )
        assert response == {"content": [{"type": "text", "text": "Synthetic context."}]}
    finally:
        process.communicate(timeout=10)
        assert process.returncode == 0
    print(
        json.dumps(
            {
                "status": "success",
                "comments": [{"path": "app.py", "line": 1, "content": "Check the boundary."}],
                "warnings": [],
                "tool_calls": {
                    "total": 2,
                    "by_tool": {"ocr_toolkit_evidence": 1, "synthetic_lookup": 1},
                },
            }
        )
    )
    return 0


def external_server() -> int:
    """Serve one optional operator-owned synthetic context tool over stdio."""

    for line in sys.stdin:
        request = json.loads(line)
        assert request["method"] == "tools/call"
        assert request["params"] == {"name": "synthetic_lookup", "arguments": {}}
        print(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": request["id"],
                    "result": {"content": [{"type": "text", "text": "Synthetic context."}]},
                }
            ),
            flush=True,
        )
    return 0


def main(root: Path, cli: Path) -> int:
    """Exercise admission and forged-usage rejection without a live model call."""

    root.mkdir(mode=0o700)
    repository = root / "repository"
    repository.mkdir()
    binary_directory = root / "bin"
    binary_directory.mkdir()
    git = shutil.which("git")
    assert git is not None

    def git_run(*args: str) -> str:
        return subprocess.run(
            [git, *args], cwd=repository, check=True, capture_output=True, text=True, timeout=20
        ).stdout.strip()

    git_run("init", "-q")
    git_run("config", "user.name", "Synthetic")
    git_run("config", "user.email", "synthetic@example.invalid")
    shadow = repository / "ocr_toolkit"
    shadow.mkdir()
    (shadow / "__init__.py").write_text("raise RuntimeError('repository shadow imported')\n")
    (repository / "app.py").write_text("VALUE = 1\n")
    git_run("add", "app.py", "ocr_toolkit/__init__.py")
    git_run("-c", "commit.gpgsign=false", "commit", "-qm", "base")
    (repository / "app.py").write_text("VALUE = 2\n")
    git_run("-c", "commit.gpgsign=false", "commit", "-qam", "head")
    head = git_run("rev-parse", "HEAD")
    environment = {
        **os.environ,
        "HOME": str(root / "operator-home"),
        "PATH": os.pathsep.join((str(binary_directory), os.environ["PATH"])),
        "CI": "true",
        "GITHUB_ACTIONS": "true",
        "CI_PROJECT_ID": "41",
        "CI_MERGE_REQUEST_IID": "12",
        "CI_API_V4_URL": "https://forge.example.invalid/api/v4",
        "OCR_LLM_MODEL": "openai/synthetic-model",
        "OCR_LLM_PROTOCOL": "openai",
        "OCR_LLM_TOKEN": "synthetic-provider-token",
        "OCR_LLM_URL": "https://provider.example.invalid/v1",
        "OCR_MCP_SERVERS_JSON": json.dumps(
            {
                "synthetic_context": {
                    "type": "stdio",
                    "command": sys.executable,
                    "args": ["-I", __file__, "--external"],
                    "tools": ["synthetic_lookup"],
                }
            }
        ),
    }
    for mode in ("verified", "forged"):
        launcher = binary_directory / "ocr"
        launcher.write_text(
            "#!/bin/sh\nexec "
            + " ".join(
                shlex.quote(value) for value in (sys.executable, "-I", __file__, "--peer", mode)
            )
            + ' "$@"\n'
        )
        launcher.chmod(0o700)
        result = root / f"{mode}.json"
        stderr = root / f"{mode}.stderr"
        completed = subprocess.run(
            [
                str(cli),
                "review",
                "--local",
                "--result",
                str(result),
                "--stderr",
                str(stderr),
                "--",
                "--commit",
                head,
            ],
            cwd=repository,
            env=environment,
            capture_output=True,
            text=True,
            timeout=45,
        )
        if mode == "verified":
            assert completed.returncode == 0, completed.stderr
            payload = json.loads(result.read_text())
            assert "_ocr_toolkit" not in payload
            assert "Check the boundary." in completed.stdout
            assert "ocr_toolkit_evidence" in completed.stdout
            assert "synthetic_context" in completed.stdout
            assert head in completed.stdout
            assert result.stat().st_mode & 0o777 == 0o600
        else:
            assert completed.returncode == 2, completed.stderr
            assert "Review failed" in completed.stdout
            assert "Stopped at: `mcp-use`" in completed.stdout
            assert "Check the boundary." not in completed.stdout
            assert not result.exists()
        assert "Traceback" not in completed.stderr
        markdown = Path(str(result) + ".md")
        assert markdown.read_text() == completed.stdout
        assert markdown.stat().st_mode & 0o777 == 0o600
        assert not (repository / ".review-context" / "evidence.json").exists()
        assert not (repository / ".review-context" / "evidence-actions.json").exists()
    print(
        json.dumps({"verified": True, "forged_usage_rejected": True, "ci_identity_ignored": True})
    )
    return 0


if __name__ == "__main__":
    if sys.argv[1] == "--external":
        raise SystemExit(external_server())
    if sys.argv[1] == "--peer":
        raise SystemExit(peer(sys.argv[2]))
    raise SystemExit(main(Path(sys.argv[1]), Path(sys.argv[2])))
