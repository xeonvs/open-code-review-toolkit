"""Installed wheel and sdist-to-wheel policy/MCP integration contracts."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import stat
import subprocess
import sys
import tarfile
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

from tests.support import PROJECT_ROOT, native_range_input
from tests.test_context_policy import policy_value
from tests.test_gitlab_discussions import note
from tests.test_gitlab_provider import _GitLabHandler, _https_gitlab

HELPER = PROJECT_ROOT / "tests" / "installed_policy_e2e.py"
RUNTIME_SMOKE = PROJECT_ROOT / "scripts" / "installed_runtime_smoke.py"
ARTIFACT_VERSION = "0.0.dev0"


def _check_installed_ci_selector_dlp(
    root: Path, python: Path, cli: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Compare the delivered GitLab review on one range with and without CI context."""

    root.mkdir(mode=0o700)
    repository = root / "repository"
    repository.mkdir()

    def git(*args: str) -> str:
        return _run(["git", *args], cwd=repository).strip()

    git("init", "-q")
    git("config", "user.name", "Synthetic")
    git("config", "user.email", "synthetic@example.invalid")
    (repository / "src").mkdir()
    source = repository / "src" / "sample.py"
    source.write_text("VALUE = 1\n", encoding="utf-8")
    policy_directory = repository / ".opencodereview"
    policy_directory.mkdir()
    policy = policy_value()
    policy["schema_version"] = "ocr.review-context-policy/v4"
    del policy["references"]
    policy["ci_outcomes"] = {"checks": [{"name": "test", "path_prefixes": ["src/"]}]}
    (policy_directory / "review-context-policy.json").write_text(
        json.dumps(policy), encoding="utf-8"
    )
    git("add", ".")
    git("-c", "commit.gpgsign=false", "commit", "-qm", "protected policy")
    base = git("rev-parse", "HEAD")
    source.write_text("VALUE = 2\n", encoding="utf-8")
    git("-c", "commit.gpgsign=false", "commit", "-qam", "source change")
    head = git("rev-parse", "HEAD")

    safe_finding = "Add a test for this value in src/."
    private_diagnostic = "The test covers src/."
    discussion_text = "The private discussion calls for a synthetic audit of this assignment."
    findings = [
        {"path": "src/sample.py", "line": 1, "content": message}
        for message in (safe_finding, discussion_text)
    ]
    model_result = root / "model-result.json"
    model_result.write_text(
        json.dumps(
            {
                "status": "complete",
                "comments": findings,
                "warnings": [],
                "summary": {"test_diagnostic": private_diagnostic},
                "tool_calls": {"total": 1, "by_tool": {"ocr_toolkit_evidence": 1}},
                "manifest": {
                    "schema_version": "ocr.run-manifest/v1",
                    "operation": "review",
                    "terminal_state": "complete",
                    "input": native_range_input(base, head),
                    "coverage": {
                        "selected": [{"item_id": "src/sample.py"}],
                        "completed": [{"item_id": "src/sample.py"}],
                        "reused": [],
                        "failed": [],
                        "waived": [],
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    ocr = root / "ocr"
    ocr.write_text(
        f"#!/bin/sh\nexec {shlex.quote(str(python))} -I - "
        f"{shlex.quote(str(model_result))} \"$@\" <<'PY'\n"
        """import json
import subprocess
import sys
from pathlib import Path

if "--preview" in sys.argv:
    raise SystemExit(0)
from ocr_toolkit import __version__

assert __version__ == "0.0.dev0"
config = json.loads((Path.home() / ".opencodereview" / "config.json").read_text())
server = config["mcp_servers"]["ocr_toolkit_evidence"]
requests = [
    {"id": 1, "method": "initialize", "params": {
        "protocolVersion": "2024-11-05", "capabilities": {},
        "clientInfo": {"name": "synthetic-ci-dlp-peer", "version": "1"},
    }},
    {"id": 2, "method": "tools/call", "params": {
        "name": "ocr_toolkit_evidence", "arguments": {"action": "summary"},
    }},
]
completed = subprocess.run(
    [server["command"], *server["args"]],
    input="".join(json.dumps({"jsonrpc": "2.0", **request}) + "\\n" for request in requests),
    capture_output=True, text=True, check=True, timeout=15,
)
responses = {item["id"]: item for item in map(json.loads, completed.stdout.splitlines())}
assert not responses[2]["result"].get("isError")
print(Path(sys.argv[1]).read_text())
PY
""",
        encoding="utf-8",
    )
    ocr.chmod(0o700)

    finish = datetime.now(UTC).isoformat()
    mr = "/api/v4/projects/7/merge_requests/9"
    original_get = _GitLabHandler.do_GET
    delivered: list[tuple[str, dict]] = []
    with_ci = with_discussion = False

    def respond(peer: _GitLabHandler, payload: object, status: int = 200) -> None:
        data = json.dumps(payload).encode()
        peer.send_response(status)
        peer.send_header("Content-Type", "application/json")
        peer.send_header("Content-Length", str(len(data)))
        peer.end_headers()
        peer.wfile.write(data)

    def get(peer: _GitLabHandler) -> None:
        url = urlsplit(peer.path)
        assert peer.headers["PRIVATE-TOKEN"] == "synthetic-gitlab-test-token"
        if url.path == "/api/v4/projects/7/pipelines":
            assert parse_qs(url.query)["sha"] == [head]
            respond(peer, [{"id": 10, "sha": head}] if with_ci else [])
        elif url.path == "/api/v4/projects/7/pipelines/10/jobs":
            assert with_ci
            respond(
                peer,
                [
                    {
                        "id": 110,
                        "name": "test",
                        "status": "success",
                        "allow_failure": False,
                        "finished_at": finish,
                        "pipeline": {"id": 10, "sha": head},
                    }
                ],
            )
        elif url.path == "/api/v4/user":
            respond(peer, {"id": 99, "username": "OCR_Bot"})
        elif url.path == f"{mr}/notes":
            respond(peer, [])
        elif url.path == f"{mr}/discussions":
            respond(
                peer,
                [
                    {
                        "id": "synthetic-thread",
                        "notes": [
                            {**note(1, discussion_text), "created_at": finish, "updated_at": finish}
                        ],
                    }
                ]
                if with_discussion
                else [],
            )
        else:
            original_get(peer)

    def post(peer: _GitLabHandler) -> None:
        assert peer.headers["PRIVATE-TOKEN"] == "synthetic-gitlab-test-token"
        assert peer.path in {f"{mr}/discussions", f"{mr}/notes"}
        payload = json.loads(peer.rfile.read(int(peer.headers["Content-Length"])))
        delivered.append((peer.path, payload))
        new_id = len(delivered) + 1
        respond(
            peer,
            {"id": f"synthetic-discussion-{new_id}", "notes": [{"id": new_id}]}
            if peer.path.endswith("/discussions")
            else {"id": new_id},
            status=201,
        )

    with monkeypatch.context() as patch:
        patch.setattr(_GitLabHandler, "do_GET", get)
        patch.setattr(_GitLabHandler, "do_POST", post, raising=False)
        with _https_gitlab(
            root / "tls",
            source_sha=head,
            target_sha=base,
            diff_base_sha=base,
            diff_start_sha=base,
        ) as api_url:
            environment = {
                "HOME": str(root),
                "PATH": os.pathsep.join((str(root), os.environ["PATH"])),
                "NO_PROXY": "localhost,127.0.0.1",
                "SSL_CERT_FILE": os.environ["SSL_CERT_FILE"],
                "GITLAB_CI": "true",
                "GITLAB_API_TOKEN": "synthetic-gitlab-test-token",
                "CI_API_V4_URL": api_url,
                "CI_SERVER_URL": api_url.removesuffix("/api/v4"),
                "CI_PROJECT_ID": "7",
                "CI_MERGE_REQUEST_IID": "9",
                "CI_MERGE_REQUEST_EVENT_TYPE": "detached",
                "CI_MERGE_REQUEST_DIFF_BASE_SHA": base,
                "CI_COMMIT_SHA": head,
                "CI_JOB_ID": "11",
                "CI_PIPELINE_ID": "10",
                "OCR_LLM_MODEL": "openai/synthetic-model",
                "OCR_LLM_PROTOCOL": "openai",
                "OCR_LLM_TOKEN": "synthetic-provider-token",
                "OCR_LLM_URL": "https://provider.example.invalid/v1",
                "OCR_POST_MODE": "direct",
                "OCR_REVIEW_CONTEXT_MODE": "enriched",
                "OCR_REVIEW_DIAGRAM_MODE": "off",
                "OCR_STRICT_POSTING": "true",
            }
            for scenario in ("without-ci", "with-ci", "with-protected-discussion"):
                with_ci = scenario != "without-ci"
                with_discussion = scenario == "with-protected-discussion"
                delivered.clear()
                result = root / f"{scenario}.json"
                stderr = root / f"{scenario}.stderr"
                output_args = ["--result", str(result), "--stderr", str(stderr)]
                _run(
                    [
                        str(cli),
                        "review",
                        *output_args,
                        "--",
                        "--from",
                        base,
                        "--to",
                        head,
                        "--format",
                        "json",
                    ],
                    cwd=repository,
                    env=environment,
                )
                raw = result.read_text(encoding="utf-8")
                artifact = json.loads(raw)
                assert stat.S_IMODE(result.stat().st_mode) == 0o600
                metadata = artifact["_ocr_toolkit"]
                assert metadata["review"]["diff_base_sha"] == base
                assert metadata["review"]["source_sha"] == head
                assert metadata["context"]["per_source"]["forge:ci_outcomes"] == (
                    "complete" if with_ci else "partial"
                )
                publication = metadata["publication"]
                _run([str(cli), "post", *output_args], cwd=repository, env=environment)
                inline_bodies = [
                    item["body"] for path, item in delivered if path == f"{mr}/discussions"
                ]
                summary_bodies = [item["body"] for path, item in delivered if path == f"{mr}/notes"]
                assert len(summary_bodies) == 1
                assert len(inline_bodies) == (1 if with_discussion else 2)
                assert safe_finding in inline_bodies[0]
                if with_discussion:
                    assert artifact["comments"] == findings[:1]
                    assert discussion_text not in raw
                    assert discussion_text not in json.dumps(delivered)
                    assert publication["state"] == "publication-filtered"
                    assert publication["retained"] == {"comments": 1, "warnings": 0}
                    assert publication["omitted"] == {"comments": 1, "warnings": 0, "fields": 1}
                    assert publication["reason_counts"]["forbidden"] == 1
                    assert publication["source_attribution"]["counts"]["forge_discussions"] == 1
                    assert publication["source_attribution"]["counts"]["ci_outcomes"] == 0
                    assert (
                        "DLP-admitted subset: 1 finding(s) and 0 warning(s). "
                        "Omitted before posting: 1 finding(s)" in summary_bodies[0]
                    )
                else:
                    assert artifact["comments"] == findings
                    assert artifact["summary"]["test_diagnostic"] == private_diagnostic
                    assert publication == {"schema": "ocr.publication/v2", "state": "passed"}
                    assert "ocr-toolkit-signal" not in summary_bodies[0]
                    assert discussion_text in inline_bodies[1]


def _run(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    timeout: int = 120,
) -> str:
    """Run one bounded integration command and return its standard output."""

    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        check=False,
        text=True,
        capture_output=True,
        timeout=timeout,
    )
    assert completed.returncode == 0, (
        f"command failed ({completed.returncode}): {command!r}\n"
        f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
    )
    return completed.stdout


@pytest.fixture(scope="module")
def installed_artifacts(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path, Path]:
    """Build a direct wheel and a wheel rebuilt from the local source distribution."""

    root = tmp_path_factory.mktemp("installed-policy-artifacts")
    direct = root / "direct"
    source = root / "source"
    rebuilt = root / "rebuilt"
    direct.mkdir()
    source.mkdir()
    rebuilt.mkdir()
    runtime_requirements = root / "runtime-requirements.txt"
    uv_binary = shutil.which("uv")
    assert uv_binary is not None
    _run(
        [
            uv_binary,
            "export",
            "--frozen",
            "--no-default-groups",
            "--no-emit-project",
            "--format",
            "requirements-txt",
            "--output-file",
            str(runtime_requirements),
        ],
        cwd=PROJECT_ROOT,
    )
    environment = dict(os.environ)
    environment.update(
        {
            "SETUPTOOLS_SCM_PRETEND_VERSION": ARTIFACT_VERSION,
            "SOURCE_DATE_EPOCH": _run(
                ["git", "show", "-s", "--format=%ct", "HEAD"], cwd=PROJECT_ROOT
            ).strip(),
        }
    )
    _run(
        [
            sys.executable,
            "-m",
            "build",
            "--no-isolation",
            "--wheel",
            "--outdir",
            str(direct),
        ],
        cwd=PROJECT_ROOT,
        env=environment,
    )
    _run(
        [
            sys.executable,
            "-m",
            "build",
            "--no-isolation",
            "--sdist",
            "--outdir",
            str(source),
        ],
        cwd=PROJECT_ROOT,
        env=environment,
    )
    sdist = next(source.glob("*.tar.gz"))
    extracted = root / "extracted"
    with tarfile.open(sdist, "r:gz") as archive:
        archive.extractall(extracted, filter="data")
    source_root = next(path for path in extracted.iterdir() if path.is_dir())
    _run(
        [
            sys.executable,
            "-m",
            "build",
            "--no-isolation",
            "--wheel",
            "--outdir",
            str(rebuilt),
        ],
        cwd=source_root,
        env=environment,
    )
    return next(direct.glob("*.whl")), next(rebuilt.glob("*.whl")), runtime_requirements


@pytest.fixture(scope="module")
def installed_without_dependencies(
    installed_artifacts: tuple[Path, Path, Path], tmp_path_factory: pytest.TempPathFactory
) -> Path:
    """Share one wheel-only interpreter between read-only missing-dependency probes."""

    uv_binary = shutil.which("uv")
    assert uv_binary is not None
    root = tmp_path_factory.mktemp("missing-runtime-dependencies")
    environment = root / "venv"
    _run(
        [uv_binary, "venv", "--python", sys.executable, "--no-project", str(environment)],
        cwd=root,
    )
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    _run(
        [
            uv_binary,
            "pip",
            "install",
            "--python",
            str(python),
            "--no-deps",
            str(installed_artifacts[0]),
        ],
        cwd=root,
    )
    return python


def test_installation_without_runtime_lock_fails_functional_mcp_probe(
    installed_without_dependencies: Path, tmp_path: Path
) -> None:
    """The historical wheel-only recipe must fail in a clean interpreter."""

    python = installed_without_dependencies
    probe = subprocess.run(
        [str(python), "-I", str(PROJECT_ROOT / "scripts" / "installed_runtime_smoke.py")],
        cwd=tmp_path,
        env={"HOME": str(tmp_path), "PATH": ""},
        check=False,
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert probe.returncode != 0
    assert "No module named 'mcp'" in probe.stderr


def _install_artifact(artifact: Path, requirements: Path, root: Path) -> tuple[Path, Path]:
    uv = shutil.which("uv")
    assert uv is not None
    environment = root / "venv"
    _run([uv, "venv", "--python", sys.executable, "--no-project", str(environment)], cwd=root)
    binary_directory = environment / ("Scripts" if os.name == "nt" else "bin")
    python = binary_directory / ("python.exe" if os.name == "nt" else "python")
    cli = binary_directory / ("ocr-ci.exe" if os.name == "nt" else "ocr-ci")
    _run(
        [
            uv,
            "pip",
            "install",
            "--python",
            str(python),
            "--require-hashes",
            "--only-binary",
            ":all:",
            "--index-url",
            "https://pypi.org/simple",
            "--requirement",
            str(requirements),
        ],
        cwd=root,
    )
    _run([uv, "pip", "install", "--python", str(python), "--no-deps", str(artifact)], cwd=root)
    _run([uv, "pip", "check", "--python", str(python)], cwd=root)
    return python, cli


@pytest.fixture(scope="module")
def installed_wheel(
    installed_artifacts: tuple[Path, Path, Path], tmp_path_factory: pytest.TempPathFactory
) -> tuple[Path, Path]:
    wheel, _, requirements = installed_artifacts
    return _install_artifact(wheel, requirements, tmp_path_factory.mktemp("installed-wheel"))


def test_installed_ci_selectors_preserve_gitlab_findings_and_private_result(
    installed_wheel: tuple[Path, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _check_installed_ci_selector_dlp(tmp_path / "ci-selector-dlp", *installed_wheel, monkeypatch)


def test_installed_wheel_and_sdist_expose_target_policy_through_real_mcp(
    installed_artifacts: tuple[Path, Path, Path],
    installed_wheel: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    """Prove both package paths under hostile imports, private state, and stdio MCP."""

    git_binary = shutil.which("git")
    assert git_binary is not None
    _, rebuilt, requirements = installed_artifacts
    for label in ("wheel", "sdist"):
        root = tmp_path / label
        root.mkdir(mode=0o700)
        python, cli = (
            installed_wheel if label == "wheel" else _install_artifact(rebuilt, requirements, root)
        )
        binary_directory = python.parent
        installed_version = _run(
            [str(python), "-I", "-c", "import ocr_toolkit; print(ocr_toolkit.__version__)"],
            cwd=root,
            env={"HOME": str(root), "PATH": ""},
        ).strip()
        assert installed_version == ARTIFACT_VERSION
        version_text = _run(
            [str(cli), "--version"],
            cwd=root,
            env={"HOME": str(root), "PATH": str(binary_directory)},
        )
        assert version_text.strip() == f"ocr-ci {ARTIFACT_VERSION}"
        help_text = _run(
            [str(cli), "--help"],
            cwd=root,
            env={"HOME": str(root), "PATH": str(binary_directory)},
        )
        assert "review" in help_text and "post" in help_text
        assert "dlp-audit" in help_text
        audit_output = _run(
            [
                str(python),
                "-I",
                str(PROJECT_ROOT / "tests" / "installed_dlp_audit.py"),
                str(cli),
                str(root / "audit"),
            ],
            cwd=root,
            env={"HOME": str(root), "PATH": ""},
            timeout=120,
        )
        assert json.loads(audit_output) == {
            "installed_audit": True,
            "private": True,
            "raw_removed": True,
        }
        config_home = root / "config-home"
        config_environment = {
            "HOME": str(config_home),
            "OCR_LLM_MAX_COMPLETION_TOKENS": "4096",
            "OCR_LLM_MODEL": "openai/gpt-test",
            "OCR_LLM_PROTOCOL": "openai",
            "OCR_LLM_TOKEN": "installed-test-token",
            "OCR_LLM_URL": "https://gateway.example/v1/chat/completions",
            "PATH": str(binary_directory),
        }
        _run([str(cli), "configure"], cwd=root, env=config_environment)
        generated_config = json.loads(
            (config_home / ".opencodereview" / "config.json").read_text(encoding="utf-8")
        )
        assert generated_config["effort"] == "medium"
        assert generated_config["llm"]["url"] == "https://gateway.example/v1"
        assert generated_config["llm"]["extra_body"] == {"max_completion_tokens": 4096}
        protocol_environment = {
            "HOME": str(root / "home"),
            "PATH": os.pathsep.join(
                dict.fromkeys((str(Path(git_binary).parent), "/usr/bin", "/bin"))
            ),
        }
        output = _run(
            [
                str(python),
                "-I",
                str(HELPER),
                str(root / "synthetic-repository"),
                installed_version,
            ],
            cwd=root,
            env=protocol_environment,
        )
        receipt = json.loads(output)
        assert receipt["installed_version"] == ARTIFACT_VERSION
        assert 0 < receipt["bootstrap_chars"] <= 2_300
        assert receipt["bootstrap_truncated"] is False
        assert receipt["base"] != receipt["policy_sha"] != receipt["head"]
        assert receipt["merge_request_context"] == {
            "contract": "review.merge-request-context/v1",
            "records": 1,
            "trust": "invocation",
            "content_role": "untrusted_data",
            "authoritative_for_actions": False,
        }
        assert receipt["policy"] == {
            "accepted_decisions": 1,
            "guidance_documents": 3,
            "structured_target_records": 4,
            "legacy_text_records": 0,
            "target_only": True,
            "authoritative_for_actions": False,
        }
        assert receipt["prioritized_template"] == {
            "component": "late/templates",
            "detection": "jinja-extension",
            "engine": "jinja2",
            "provenance": "framework plugin:jinja2",
            "rendered_extension": ".conf",
        }
        assert receipt["private_modes"] is True
        assert receipt["read_only"] is True
        assert receipt["repository_clean"] is True
        local_output = _run(
            [
                str(python),
                "-I",
                str(PROJECT_ROOT / "tests" / "providers" / "installed_local_review.py"),
                str(root / "local-review"),
                str(cli),
            ],
            cwd=root,
            env=protocol_environment,
            timeout=300,
        )
        assert json.loads(local_output) == {
            "verified": True,
            "forged_usage_rejected": True,
            "ci_identity_ignored": True,
            "debug_parity": True,
            "progress_parity": True,
            "diagrams": True,
        }


def test_installed_runtime_smoke_fails_without_runtime_dependencies(
    installed_without_dependencies: Path, tmp_path: Path
) -> None:
    """Prove the functional smoke detects a wheel installed without its runtime lock."""

    root = tmp_path / "missing-runtime-dependencies"
    root.mkdir(mode=0o700)
    python = installed_without_dependencies
    binary_directory = python.parent
    completed = subprocess.run(
        [str(python), "-I", str(RUNTIME_SMOKE)],
        cwd=root,
        env={"HOME": str(root), "PATH": str(binary_directory)},
        check=False,
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert completed.returncode != 0
    assert "No module named 'mcp'" in completed.stderr
    assert "installed_runtime_smoke" not in completed.stdout
