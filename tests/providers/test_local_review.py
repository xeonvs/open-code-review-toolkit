"""Standalone provider selection and closed CLI failure contracts."""

import sys
from pathlib import Path

import pytest

from ocr_toolkit import cli, preflight, review_runner
from ocr_toolkit.evidence.artifacts import prepare_artifact_directory, repository_artifacts


def test_local_preflight_does_not_validate_gitlab(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []
    monkeypatch.setattr(preflight, "validate_ocr_binary", lambda: seen.append("ocr"))
    monkeypatch.setattr(preflight, "validate_llm_model", lambda: seen.append("llm"))
    monkeypatch.setattr(preflight, "validate_gitlab_access", lambda: pytest.fail("GitLab called"))
    assert cli.main(["preflight", "--local"]) == 0
    assert seen == ["ocr", "llm"]


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


def test_local_invalid_ref_has_closed_identity_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)

    def reject_refs(_refs: review_runner.ReviewRefs) -> review_runner.ReviewRefs:
        raise review_runner.RepositoryEvidenceError("private repository diagnostic")

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
    assert "immutable review refs could not be resolved" in output.err
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
