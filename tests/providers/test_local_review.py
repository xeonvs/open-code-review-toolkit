"""Standalone provider selection and closed CLI failure contracts."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from ocr_toolkit import cli, preflight, review_runner
from ocr_toolkit.evidence.artifacts import prepare_artifact_directory, repository_artifacts
from ocr_toolkit.reporting.model import failed_report


def test_local_preflight_does_not_validate_gitlab(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []
    monkeypatch.setattr(preflight, "validate_ocr_binary", lambda: seen.append("ocr"))
    monkeypatch.setattr(preflight, "validate_llm_model", lambda: seen.append("llm"))
    monkeypatch.setattr(preflight, "validate_gitlab_access", lambda: pytest.fail("GitLab called"))
    monkeypatch.setattr(
        preflight, "validate_gitlab_review_settings", lambda: pytest.fail("GitLab mode touched")
    )
    assert cli.main(["preflight", "--local"]) == 0
    assert seen == ["ocr", "llm"]


@pytest.mark.parametrize("mode", [None, "auto", "required", "unprotected"])
def test_gitlab_preflight_accepts_detached_identity_and_exact_modes(
    monkeypatch: pytest.MonkeyPatch, mode: str | None
) -> None:
    monkeypatch.setenv("CI_MERGE_REQUEST_EVENT_TYPE", "detached")
    monkeypatch.setenv("CI_COMMIT_SHA", "a" * 40)
    monkeypatch.delenv("CI_MERGE_REQUEST_SOURCE_BRANCH_SHA", raising=False)
    if mode is None:
        monkeypatch.delenv("OCR_GITLAB_TARGET_PROTECTION_MODE", raising=False)
    else:
        monkeypatch.setenv("OCR_GITLAB_TARGET_PROTECTION_MODE", mode)
    preflight.validate_gitlab_review_settings()


@pytest.mark.parametrize(
    ("updates", "message"),
    [
        ({"OCR_GITLAB_TARGET_PROTECTION_MODE": ""}, "must be exactly"),
        ({"OCR_GITLAB_TARGET_PROTECTION_MODE": "AUTO"}, "must be exactly"),
        ({"CI_MERGE_REQUEST_EVENT_TYPE": "merged_result"}, "detached"),
        ({"CI_MERGE_REQUEST_EVENT_TYPE": "merge_train"}, "detached"),
        ({"CI_COMMIT_SHA": "b" * 39}, "full commit SHA"),
        ({"CI_MERGE_REQUEST_SOURCE_BRANCH_SHA": "b" * 40}, "contradicts"),
    ],
)
def test_gitlab_preflight_rejects_unsupported_or_contradictory_identity(
    monkeypatch: pytest.MonkeyPatch, updates: dict[str, str], message: str
) -> None:
    monkeypatch.setenv("CI_MERGE_REQUEST_EVENT_TYPE", "detached")
    monkeypatch.setenv("CI_COMMIT_SHA", "a" * 40)
    monkeypatch.delenv("OCR_GITLAB_TARGET_PROTECTION_MODE", raising=False)
    monkeypatch.delenv("CI_MERGE_REQUEST_SOURCE_BRANCH_SHA", raising=False)
    for name, value in updates.items():
        monkeypatch.setenv(name, value)
    with pytest.raises(preflight.PreflightError, match=message):
        preflight.validate_gitlab_review_settings()


@pytest.mark.parametrize(
    "args",
    [
        ["--format", "text"],
        ["-fsarif"],
        ["-f=text"],
        ["--audience=human"],
        ["--repo", "other"],
        ["--resume=old"],
        ["-Bprivate.md"],
        ["--background", "override"],
    ],
)
def test_local_rejects_competing_inputs_before_artifacts(
    args: list[str], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    result, stderr = tmp_path / "result.json", tmp_path / "stderr.log"
    with pytest.raises(review_runner.ReviewRunnerError):
        review_runner.run_evidence_review(result, stderr, args, local=True)
    output = capsys.readouterr().out
    assert "Review failed" in output and "Stopped at: `configuration`" in output
    assert not result.exists() and not stderr.exists()


def test_local_busy_review_delivers_failure_report_without_touching_active_artifacts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A second local review reports lock contention and preserves the active run."""

    monkeypatch.delenv("OCR_REVIEW_CONTEXT_MODE", raising=False)
    monkeypatch.delenv("OCR_REVIEW_CONTEXT_ADAPTERS_JSON", raising=False)
    monkeypatch.chdir(tmp_path)
    artifacts = repository_artifacts(tmp_path)
    prepare_artifact_directory(artifacts)
    shared_report = tmp_path / "report.md"
    child = (
        "from pathlib import Path\n"
        "from ocr_toolkit import review_runner\n"
        "try:\n"
        "    review_runner.run_evidence_review("
        "Path('loser.json'), Path('loser.log'), [], local=True, report_path=Path('report.md'))\n"
        "except review_runner.ReviewRunnerBusy as exc:\n"
        "    print(str(exc))\n"
        "else:\n"
        "    raise SystemExit('concurrent review unexpectedly proceeded')\n"
    )
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(Path(review_runner.__file__).resolve().parents[1])
    with review_runner.locked_review_run(artifacts):
        artifacts.bootstrap.write_text("active", encoding="utf-8")
        artifacts.bootstrap.chmod(0o600)
        completed = subprocess.run(
            [sys.executable, "-c", child],
            cwd=tmp_path,
            env=environment,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr
        assert "another review is already running" in completed.stdout
        assert "Review failed" in completed.stdout
        assert not shared_report.exists()
        assert artifacts.bootstrap.read_text(encoding="utf-8") == "active"
        assert not (tmp_path / "loser.json").exists()

    def finish(*_args: object, state: review_runner.ReviewRunState, **_kwargs: object) -> int:
        state.report = failed_report("identity")
        return 0

    monkeypatch.setattr(review_runner.local_chatgpt, "auth_mode", lambda *_a, **_kw: "api")
    monkeypatch.setattr(review_runner, "_run_evidence_review", finish)
    assert (
        review_runner.run_evidence_review(
            tmp_path / "winner.json",
            tmp_path / "winner.log",
            [],
            local=True,
            report_path=shared_report,
        )
        == 0
    )
    assert "Review failed" in shared_report.read_text(encoding="utf-8")


def test_local_private_retention_reaches_review_and_delivers_failure_report(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The explicit local diagnostic option reaches execution and reports a failure."""

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OCR_REVIEW_CONTEXT_MODE", raising=False)
    monkeypatch.delenv("OCR_REVIEW_CONTEXT_ADAPTERS_JSON", raising=False)
    monkeypatch.setattr(review_runner.local_chatgpt, "auth_mode", lambda *_a, **_kw: "api")
    observed: list[bool] = []

    def finish(
        *_args: object,
        preserve_private_artifacts: bool,
        state: review_runner.ReviewRunState,
        **_kwargs: object,
    ) -> int:
        assert state.local is True
        observed.append(preserve_private_artifacts)
        return 1

    monkeypatch.setattr(review_runner, "_run_evidence_review", finish)
    result = tmp_path / "result.json"
    report = tmp_path / "review.md"
    assert (
        review_runner.run_evidence_review(
            result,
            tmp_path / "stderr.log",
            [],
            local=True,
            preserve_private_artifacts=True,
            report_path=report,
        )
        == 1
    )
    assert observed == [True]
    assert "Review failed" in report.read_text(encoding="utf-8")


def test_explicit_local_ignores_inherited_forge_identity(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CI_PROJECT_ID", "41")
    monkeypatch.setenv("CI_MERGE_REQUEST_IID", "12")
    monkeypatch.setenv("CI_API_V4_URL", "https://forge.example.invalid/api/v4")
    monkeypatch.delenv("OCR_REVIEW_CONTEXT_MODE", raising=False)
    monkeypatch.delenv("OCR_REVIEW_CONTEXT_ADAPTERS_JSON", raising=False)
    monkeypatch.setattr(review_runner, "GitRepositoryReader", lambda _root: object())
    monkeypatch.setattr(
        review_runner, "acquire_review_snapshot", lambda *_a, **_kw: pytest.fail("GitLab called")
    )
    refs = review_runner.ReviewRefs("a" * 40, "b" * 40)
    artifacts = repository_artifacts(tmp_path)
    prepare_artifact_directory(artifacts)
    identity, args = review_runner._prepare_policy_context(refs, [], artifacts, local=True)
    assert identity.source_sha == refs.head
    assert identity.policy_sha == refs.base
    assert identity.target_protection == "local"
    assert identity.mr_author_id is None and identity.context is None
    assert args == []


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("OCR_REVIEW_CONTEXT_MODE", "metadata"),
        ("OCR_REVIEW_CONTEXT_MODE", "enriched"),
        ("OCR_REVIEW_CONTEXT_ADAPTERS_JSON", "[]"),
    ],
)
def test_explicit_unsupported_context_is_not_successful_empty_acquisition(
    name: str, value: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("OCR_REVIEW_CONTEXT_MODE", raising=False)
    monkeypatch.delenv("OCR_REVIEW_CONTEXT_ADAPTERS_JSON", raising=False)
    monkeypatch.setenv(name, value)
    monkeypatch.setattr(
        review_runner, "GitRepositoryReader", lambda _root: pytest.fail("repository read")
    )
    with pytest.raises(review_runner.ReviewRunnerError, match="does not support"):
        review_runner._prepare_policy_context(
            review_runner.ReviewRefs("a" * 40, "b" * 40),
            [],
            repository_artifacts(tmp_path),
            local=True,
        )


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("OCR_REVIEW_CONTEXT_MODE", "metadata"),
        ("OCR_REVIEW_CONTEXT_MODE", "invalid"),
        ("OCR_REVIEW_CONTEXT_ADAPTERS_JSON", "[]"),
    ],
)
def test_local_context_rejected_before_preflight_io_or_review_artifacts(
    name: str,
    value: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv(name, value)
    monkeypatch.setattr(preflight, "validate_ocr_binary", lambda: pytest.fail("binary invoked"))
    monkeypatch.setattr(preflight, "validate_llm_model", lambda: pytest.fail("provider called"))
    monkeypatch.setattr(
        review_runner, "repository_artifacts", lambda: pytest.fail("artifacts prepared")
    )
    assert cli.main(["preflight", "--local"]) == 1
    assert (
        cli.main(
            [
                "review",
                "--local",
                "--result",
                str(tmp_path / "result.json"),
                "--stderr",
                str(tmp_path / "stderr.log"),
            ]
        )
        == 2
    )
    output = capsys.readouterr()
    assert "Stopped at: `configuration`" in output.out
    assert "Traceback" not in output.err


@pytest.mark.parametrize(
    "error_type", (review_runner.RepositoryEvidenceError, review_runner.ShallowAncestryUnavailable)
)
def test_local_invalid_ref_has_closed_identity_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str], error_type
) -> None:
    monkeypatch.chdir(tmp_path)

    def reject_refs(_refs: review_runner.ReviewRefs) -> review_runner.ReviewRefs:
        raise error_type("private repository diagnostic")

    monkeypatch.setattr(review_runner, "_immutable_review_refs", reject_refs)
    assert (
        cli.main(
            [
                "review",
                "--local",
                "--result",
                str(tmp_path / "result.json"),
                "--stderr",
                str(tmp_path / "stderr.log"),
                "--",
                "--commit",
                "missing",
            ]
        )
        == 2
    )
    output = capsys.readouterr()
    assert "Stopped at: `identity`" in output.out
    assert "immutable review range could not be proved" in output.err
    assert "private repository diagnostic" not in output.err + output.out
    assert "Traceback" not in output.err


def test_failed_summary_sinks_do_not_replace_original_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    class BrokenSink:
        def write(self, _value: str) -> int:
            raise BrokenPipeError("closed output")

        def flush(self) -> None:
            pass

    monkeypatch.setattr(sys, "stdout", BrokenSink())
    monkeypatch.setattr(sys, "stderr", BrokenSink())
    with pytest.raises(review_runner.ReviewRunnerError, match="requires --format json"):
        review_runner.run_evidence_review(
            tmp_path / "result.json", tmp_path / "stderr.log", ["--format=text"], local=True
        )
