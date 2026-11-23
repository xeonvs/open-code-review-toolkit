"""Qualify installed-toolkit native handoffs with their actual local consumers."""

from __future__ import annotations

import hashlib
import json
import stat
import subprocess
import sys
from pathlib import Path
from xml.etree import ElementTree  # nosec B405 - locally generated pytest report

from . import core, execution, settings


def chatgpt_auth_handoff(binary: Path, repo: Path, base: str, head: str, directory: Path) -> bool:
    """Verify native config selection and the empty-store boundary without credentials."""

    env = execution._isolated_probe_environment(directory / "native-auth-home")
    env["OCR_TELEMETRY_ENABLED"] = "false"
    help_output = execution._run([str(binary), "--help"], cwd=repo, env=env)
    if not any(line.split()[:1] == ["auth"] for line in help_output.splitlines()):
        return False
    execution._run([str(binary), "auth", "status", "--provider", "chatgpt"], cwd=repo, env=env)
    for key, value in (("provider", "chatgpt"), ("providers.chatgpt.model", "synthetic-model")):
        execution._run([str(binary), "config", "set", key, value], cwd=repo, env=env)
    result = subprocess.run(  # nosec B603 - checksum-verified local binary
        [
            str(binary),
            "review",
            "--from",
            base,
            "--to",
            head,
            "--format",
            "json",
            "--audience",
            "agent",
        ],
        cwd=repo,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    store = directory / "native-auth-home" / ".opencodereview" / "auth" / "chatgpt"
    lock = store / "session.lock"
    if (
        result.returncode <= 0
        or "ocr auth login --provider chatgpt" not in result.stderr
        or not lock.is_file()
        or any((store / filename).exists() for filename in ("accounts.json", "host.json"))
    ):
        return False
    lock_metadata = lock.lstat()
    return (
        stat.S_ISREG(lock_metadata.st_mode)
        and stat.S_IMODE(lock_metadata.st_mode) == 0o600
        and lock_metadata.st_size == 0
    )


def consumer_handoffs(binary: Path, version: str, directory: Path) -> list[str]:
    """Exercise the verified executable through toolkit gitlink and diagram routes."""

    env = execution._isolated_probe_environment(directory / "consumer-home")
    with binary.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    env.update(
        OCR_GITLINK_QUALIFY_BINARY=str(binary),
        OCR_QUALIFY_CANDIDATE=json.dumps(
            {"version": version, "sha256": digest, "size": binary.stat().st_size}
        ),
        GIT_AUTHOR_NAME="Synthetic Reviewer",
        GIT_COMMITTER_NAME="Synthetic Reviewer",
        GIT_AUTHOR_EMAIL="reviewer@example.com",
        GIT_COMMITTER_EMAIL="reviewer@example.com",
    )
    junit = directory / "handoffs.xml"
    execution._run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-o",
            "addopts=",
            "--junitxml",
            str(junit),
            "tests/test_gitlinks.py::test_installed_ocr_toolkit_local_gitlink_route[updated]",
            "tests/diagrams/test_native.py::test_qualified_native_diagram_handoff_preserves_review_and_checkout[flow]",
        ],
        cwd=settings.ROOT,
        env=env,
    )
    suite = ElementTree.parse(junit).getroot().find("testsuite")  # nosec B314
    if (
        suite is None
        or suite.get("tests") != "2"
        or any(suite.get(key) != "0" for key in ("skipped", "errors", "failures"))
    ):
        core._fail("native consumer tests did not complete both exchanges")
    return ["diagram_output", "gitlink_projection"]
