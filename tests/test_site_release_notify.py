"""Exercise the privileged site-notification gate with synthetic GitHub reads."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

WORKFLOW = Path(__file__).parents[1] / ".github/workflows/site-release-notify.yml"


def _verification_step() -> str:
    jobs = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]
    steps = jobs["notify"]["steps"]
    return next(step["run"] for step in steps if step.get("id") == "release")


def test_site_dispatch_occurs_once_after_read_only_verification() -> None:
    jobs = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]
    steps = jobs["notify"]["steps"]
    assert "--method POST" not in _verification_step()
    dispatch = next(step for step in steps if step.get("name") == "Request site refresh")
    assert dispatch["if"] == "steps.release.outputs.release_tag != ''"
    assert dispatch["run"].count("--method POST") == 1


@pytest.mark.parametrize(
    ("states", "duplicate", "expected_code", "expected_error", "expected_reads", "published"),
    [
        (["in_progress", "success"], False, 0, "", 2, True),
        (["in_progress"] * 6, False, 1, "remained unfinished", 6, False),
        (["failure"], False, 1, "was not successful", 1, False),
        (["skipped"], False, 0, "", 1, False),
        (["invalid"], False, 1, "invalid status", 1, False),
        (["success"], True, 1, "", 1, False),
    ],
)
def test_release_job_readback_is_bounded_and_fail_closed(
    tmp_path: Path,
    states: list[str],
    duplicate: bool,
    expected_code: int,
    expected_error: str,
    expected_reads: int,
    published: bool,
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake_gh = bin_dir / "gh"
    fake_gh.write_text(
        f"#!{sys.executable}\n"
        "import json, os, sys\n"
        "from pathlib import Path\n"
        "root = Path(os.environ['FAKE_STATE_DIR'])\n"
        "request = sys.argv[-1]\n"
        "if request.endswith('/actions/workflows/release.yml'):\n"
        "  value = {'id': 315030204, 'path': '.github/workflows/release.yml', 'state': 'active'}\n"
        "elif '/attempts/1/jobs?' in request:\n"
        "  count_file = root / 'job-reads'\n"
        "  count = int(count_file.read_text()) if count_file.exists() else 0\n"
        "  count_file.write_text(str(count + 1))\n"
        "  states = json.loads(os.environ['FAKE_JOB_STATES'])\n"
        "  state = states[min(count, len(states) - 1)]\n"
        "  status = 'completed' if state in ('success', 'failure', 'skipped') else state\n"
        "  conclusion = state if status == 'completed' else None\n"
        "  value = {'total_count': 1, 'jobs': [{'name': 'publish-github-release', "
        "'status': status, 'conclusion': conclusion}]}\n"
        "  if os.environ['FAKE_DUPLICATE_JOB'] == '1':\n"
        "    value['jobs'].append(value['jobs'][0].copy())\n"
        "    value['total_count'] = 2\n"
        "elif request.endswith('/releases/latest'):\n"
        "  value = {'immutable': True, 'draft': False, 'prerelease': False, "
        "'published_at': '2026-10-22T13:21:49Z', 'tag_name': 'v0.12.1', "
        "'assets': [{'id': 123, 'name': 'release-receipt.json', 'state': 'uploaded', "
        "'size': 100}]}\n"
        "elif request.endswith('/releases/assets/123'):\n"
        "  value = {'schema_version': 'ocr-toolkit.release-receipt/v2', "
        "'tag': 'v0.12.1', 'version': '0.12.1', "
        "'workflow': {'run_id': 39784597413, 'run_attempt': 1}}\n"
        "else:\n"
        "  raise SystemExit('unexpected GitHub request')\n"
        "print(json.dumps(value))\n",
        encoding="utf-8",
    )
    fake_gh.chmod(0o700)
    fake_sleep = bin_dir / "sleep"
    fake_sleep.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    fake_sleep.chmod(0o700)
    output = tmp_path / "github-output"
    environment = {
        **os.environ,
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "FAKE_STATE_DIR": str(tmp_path),
        "FAKE_JOB_STATES": json.dumps(states),
        "FAKE_DUPLICATE_JOB": "1" if duplicate else "0",
        "GH_TOKEN": "synthetic-token",
        "GITHUB_REPOSITORY": "xeonvs/open-code-review-toolkit",
        "SOURCE_RUN_ID": "39784597413",
        "SOURCE_RUN_ATTEMPT": "1",
        "SOURCE_WORKFLOW_ID": "315030204",
        "RUNNER_TEMP": str(tmp_path),
        "GITHUB_OUTPUT": str(output),
    }
    completed = subprocess.run(
        ["bash", "-e", "-o", "pipefail", "-c", _verification_step()],
        cwd=tmp_path,
        env=environment,
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert completed.returncode == expected_code, completed.stderr
    assert expected_error in completed.stderr
    assert int((tmp_path / "job-reads").read_text()) == expected_reads
    assert output.exists() is published
    if published:
        assert output.read_text() == "release_tag=v0.12.1\n"
