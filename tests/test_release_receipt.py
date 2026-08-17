"""Contracts for deterministic stable-release delivery receipts."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "release_receipt.py"
PROVENANCE_SCRIPT = ROOT / "scripts" / "verify_registry_provenance.py"
ISSUE_RECEIPT_SCRIPT = ROOT / "scripts" / "release_issue_receipt.py"
GITHUB_RELEASE_SCRIPT = ROOT / "scripts" / "github_release_api.py"
WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"


def load_script(path: Path, name: str) -> ModuleType:
    """Load one repository script without depending on the working directory."""

    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


receipt = load_script(SCRIPT, "release_receipt_script")
provenance = load_script(PROVENANCE_SCRIPT, "verify_registry_provenance_script")
issue_receipt = load_script(ISSUE_RECEIPT_SCRIPT, "release_issue_receipt_script")
github_release = load_script(GITHUB_RELEASE_SCRIPT, "github_release_api_script")


def build_receipt(**overrides: Any) -> dict[str, Any]:
    """Build one fully valid synthetic receipt by default."""

    values: dict[str, Any] = {
        "version": "0.4.7",
        "tag": "v0.4.7",
        "release_pr": 73,
        "issues": [70, 71],
        "base": "a" * 40,
        "head": "b" * 40,
        "merge": "c" * 40,
        "tree": "d" * 40,
        "run_id": 123,
        "run_attempt": 1,
        "authorized_at": "2026-08-10T10:00:00Z",
        "artifacts": {
            "open_code_review_toolkit-0.4.7.tar.gz": "e" * 64,
            "open_code_review_toolkit-0.4.7-py3-none-any.whl": "f" * 64,
        },
        "python_minors": ["3.12", "3.13", "3.14"],
    }
    values.update(overrides)
    return receipt.build_receipt(**values)


def test_receipt_is_canonical_and_records_only_completed_pre_release_gates() -> None:
    payload = build_receipt()

    assert payload["schema_version"] == "ocr-toolkit.release-receipt/v1"
    assert payload["issues"] == [70, 71]
    assert payload["reviewed"] == {
        "base": "a" * 40,
        "head": "b" * 40,
        "merge": "c" * 40,
        "tree": "d" * 40,
    }
    assert payload["registries"] == {
        "testpypi": {"artifacts": "verified", "provenance": "verified"},
        "pypi": {"artifacts": "verified", "provenance": "verified"},
    }
    assert payload["python_smoke"] == {
        "3.12": "verified",
        "3.13": "verified",
        "3.14": "verified",
    }
    assert payload["github"]["release_assets"] == "pending_self_readback"
    assert "immutable" not in json.dumps(payload).casefold()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("tag", "v0.4.8"),
        ("issues", [71, 70]),
        ("issues", [70, 70]),
        ("head", "not-a-sha"),
        ("authorized_at", "now"),
        ("python_minors", ["3.12", "3.14"]),
    ],
)
def test_receipt_rejects_inconsistent_evidence(field: str, value: object) -> None:
    with pytest.raises(receipt.ReceiptError):
        build_receipt(**{field: value})


def test_supported_python_minors_come_from_canonical_project_metadata() -> None:
    assert receipt.supported_python_minors({"project": {"requires-python": ">=3.12,<3.15"}}) == [
        "3.12",
        "3.13",
        "3.14",
    ]
    with pytest.raises(receipt.ReceiptError):
        receipt.supported_python_minors({"project": {"requires-python": ">=3.12"}})


def test_existing_receipt_recovery_ignores_new_run_but_rejects_delivery_drift() -> None:
    payload = build_receipt(run_id=555, run_attempt=3)
    receipt.validate_receipt(
        payload,
        version="0.4.7",
        tag="v0.4.7",
        release_pr=73,
        issues=[70, 71],
        base="a" * 40,
        head="b" * 40,
        merge="c" * 40,
        tree="d" * 40,
        authorized_at="2026-08-10T10:00:00Z",
        artifacts={
            "open_code_review_toolkit-0.4.7.tar.gz": "e" * 64,
            "open_code_review_toolkit-0.4.7-py3-none-any.whl": "f" * 64,
        },
        python_minors=["3.12", "3.13", "3.14"],
    )

    payload["issues"] = [70]
    with pytest.raises(receipt.ReceiptError, match="issues"):
        receipt.validate_receipt(
            payload,
            version="0.4.7",
            tag="v0.4.7",
            release_pr=73,
            issues=[70, 71],
            base="a" * 40,
            head="b" * 40,
            merge="c" * 40,
            tree="d" * 40,
            authorized_at="2026-08-10T10:00:00Z",
            artifacts={
                "open_code_review_toolkit-0.4.7.tar.gz": "e" * 64,
                "open_code_review_toolkit-0.4.7-py3-none-any.whl": "f" * 64,
            },
            python_minors=["3.12", "3.13", "3.14"],
        )


def test_existing_receipt_rejects_unknown_top_level_and_workflow_fields() -> None:
    common = {
        "version": "0.4.7",
        "tag": "v0.4.7",
        "release_pr": 73,
        "issues": [70, 71],
        "base": "a" * 40,
        "head": "b" * 40,
        "merge": "c" * 40,
        "tree": "d" * 40,
        "authorized_at": "2026-08-10T10:00:00Z",
        "artifacts": {
            "open_code_review_toolkit-0.4.7.tar.gz": "e" * 64,
            "open_code_review_toolkit-0.4.7-py3-none-any.whl": "f" * 64,
        },
        "python_minors": ["3.12", "3.13", "3.14"],
    }
    payload = build_receipt()
    payload["future_claim"] = "verified"
    with pytest.raises(receipt.ReceiptError, match="schema shape"):
        receipt.validate_receipt(payload, **common)

    payload = build_receipt()
    payload["workflow"]["future_identity"] = 1
    with pytest.raises(receipt.ReceiptError, match="workflow identity"):
        receipt.validate_receipt(payload, **common)


def encoded_statement(filename: str, digest: str) -> str:
    """Return one base64 PyPI publish-attestation statement."""

    import base64

    statement = {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": [{"name": filename, "digest": {"sha256": digest}}],
        "predicateType": "https://docs.pypi.org/attestations/publish/v1",
        "predicate": None,
    }
    return base64.b64encode(json.dumps(statement).encode()).decode()


def integrity_payload(
    filename: str, digest: str, *, workflow: str = "release.yml"
) -> dict[str, Any]:
    """Return one minimal registry-authoritative integrity response."""

    return {
        "version": 1,
        "attestation_bundles": [
            {
                "publisher": {
                    "kind": "GitHub",
                    "repository": "synthetic/open-code-review-toolkit",
                    "workflow": workflow,
                    "environment": "pypi-production",
                },
                "attestations": [{"envelope": {"statement": encoded_statement(filename, digest)}}],
            }
        ],
    }


def test_registry_provenance_requires_exact_publisher_and_subject() -> None:
    filename = "package.whl"
    digest = "a" * 64
    payload = integrity_payload(filename, digest)

    provenance.verify_provenance(
        payload,
        filename=filename,
        digest=digest,
        environment="pypi-production",
        repository="synthetic/open-code-review-toolkit",
        workflow="release.yml",
    )

    development = integrity_payload(filename, digest, workflow="testpypi.yml")
    provenance.verify_provenance(
        development,
        filename=filename,
        digest=digest,
        environment="pypi-production",
        repository="synthetic/open-code-review-toolkit",
        workflow="testpypi.yml",
    )
    with pytest.raises(provenance.ProvenanceError, match="publisher"):
        provenance.verify_provenance(
            development,
            filename=filename,
            digest=digest,
            environment="pypi-production",
            repository="synthetic/open-code-review-toolkit",
            workflow="release.yml",
        )

    payload["attestation_bundles"][0]["publisher"]["environment"] = "other"
    with pytest.raises(provenance.ProvenanceError, match="publisher"):
        provenance.verify_provenance(
            payload,
            filename=filename,
            digest=digest,
            environment="pypi-production",
            repository="synthetic/open-code-review-toolkit",
            workflow="release.yml",
        )


def test_registry_provenance_rejects_wrong_digest_and_malformed_statement() -> None:
    filename = "package.whl"
    payload = integrity_payload(filename, "b" * 64)
    with pytest.raises(provenance.ProvenanceError, match="subject"):
        provenance.verify_provenance(
            payload,
            filename=filename,
            digest="a" * 64,
            environment="pypi-production",
            repository="synthetic/open-code-review-toolkit",
            workflow="release.yml",
        )

    payload["attestation_bundles"][0]["attestations"][0]["envelope"]["statement"] = "bad"
    with pytest.raises(provenance.ProvenanceError, match="subject"):
        provenance.verify_provenance(
            payload,
            filename=filename,
            digest="a" * 64,
            environment="pypi-production",
            repository="synthetic/open-code-review-toolkit",
            workflow="release.yml",
        )


def test_issue_receipt_accepts_only_exact_actions_owned_comment_and_closed_state() -> None:
    body = issue_receipt.receipt_body("0.4.7", 70, "a" * 64)
    comment = {
        "body": body,
        "user": {"login": "github-actions[bot]", "id": 41898282, "type": "Bot"},
    }

    assert (
        issue_receipt.issue_state(
            {"number": 70, "state": "open", "state_reason": None}, 70, require_closed=False
        )
        == "open"
    )
    assert (
        issue_receipt.issue_state(
            {"number": 70, "state": "closed", "state_reason": "completed"},
            70,
            require_closed=True,
        )
        == "closed"
    )
    assert body.endswith("\n") and not body.endswith("\n\n")
    assert issue_receipt.comment_state([comment], body, require_comment=True) == "matched"

    forged = {**comment, "user": {"login": "synthetic-user", "id": 7, "type": "User"}}
    with pytest.raises(issue_receipt.IssueReceiptError, match="not uniquely owned"):
        issue_receipt.comment_state([forged], body, require_comment=False)
    with pytest.raises(issue_receipt.IssueReceiptError, match="not uniquely owned"):
        issue_receipt.comment_state([forged], body, require_comment=True)


def test_issue_receipt_rejects_duplicate_wrong_body_or_incompatible_issue_state() -> None:
    body = issue_receipt.receipt_body("0.4.7", 71, "b" * 64)
    comment = {
        "body": body,
        "user": {"login": "github-actions[bot]", "id": 41898282, "type": "Bot"},
    }
    with pytest.raises(issue_receipt.IssueReceiptError, match="not uniquely owned"):
        issue_receipt.comment_state([comment, comment], body, require_comment=True)
    with pytest.raises(issue_receipt.IssueReceiptError, match="body does not match"):
        issue_receipt.comment_state(
            [{**comment, "body": body + " changed"}], body, require_comment=True
        )
    with pytest.raises(issue_receipt.IssueReceiptError, match="incompatible state"):
        issue_receipt.issue_state(
            {"number": 71, "state": "closed", "state_reason": "not_planned"},
            71,
            require_closed=False,
        )
    with pytest.raises(issue_receipt.IssueReceiptError, match="response is invalid"):
        issue_receipt.issue_state(
            {"number": 71, "state": "open", "state_reason": None, "pull_request": {}},
            71,
            require_closed=False,
        )


def test_release_workflow_builds_reads_back_and_recovers_the_receipt() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert workflow.count('python: ["3.12", "3.13", "3.14"]') == 2
    assert "verify_registry_provenance.py" in (
        ROOT / "scripts" / "verify_registry_artifacts.sh"
    ).read_text(encoding="utf-8")
    assert "python scripts/release_receipt.py" in workflow
    assert "python scripts/github_release_api.py ensure" in workflow
    assert "python scripts/github_release_api.py upload" in workflow
    assert "python scripts/github_release_api.py publish" in workflow
    assert '--release-id "${release_id}"' in workflow
    assert 'release upload "${TAG}" dist/*' not in workflow
    assert "--clobber" not in workflow
    assert "bounded_release_download" in workflow
    assert "releases/assets/${asset_id}" in workflow
    assert "application/octet-stream" in workflow
    assert "gh release download" not in workflow
    assert "gh release create" not in workflow
    assert "gh release upload" not in workflow
    assert "gh release edit" not in workflow
    assert "duplicate GitHub Release asset" in workflow
    assert '--validate-existing "${release_dir}/release-receipt.json"' in workflow
    assert 'cmp release-receipt.json "${release_dir}/release-receipt.json"' in workflow
    assert "GITHUB_API_VERSION=2026-03-10" in workflow
    assert ".immutable == true" in workflow
    assert "ocr-toolkit-release-receipt" in ISSUE_RECEIPT_SCRIPT.read_text(encoding="utf-8")
    assert "has too many comments for bounded receipt lookup" in workflow
    assert "cannot accept a receipt within the comment bound" in workflow
    assert "python scripts/release_issue_receipt.py" in workflow
    assert '--body-file "/tmp/issue-${issue}-receipt.md"' in workflow
    assert "release receipt comment is not uniquely owned by GitHub Actions" in (
        ISSUE_RECEIPT_SCRIPT.read_text(encoding="utf-8")
    )
    assert 'if [ "${issue_state}" = open ]; then' in workflow
    assert 'gh issue close "${issue}" --repo "${GITHUB_REPOSITORY}" --reason completed' in workflow
    assert 'state == "closed" and reason == "completed"' in ISSUE_RECEIPT_SCRIPT.read_text(
        encoding="utf-8"
    )
    assert "reset_approvals" not in workflow
    assert "always() && needs.authorize.result == 'success'" in workflow
    assert "needs.verify-pypi.result == 'success'" in workflow


def test_numeric_release_identity_requires_exact_metadata_and_unique_assets() -> None:
    notes = "## 0.5.0\n"
    payload = {
        "id": 91,
        "tag_name": "v0.5.0",
        "target_commitish": "a" * 40,
        "name": "v0.5.0",
        "body": notes,
        "draft": True,
        "prerelease": False,
        "assets": [{"id": 7, "name": "package.whl", "size": 10}],
    }
    validated = github_release.validate_release(
        payload,
        repository="synthetic/toolkit",
        tag="v0.5.0",
        target="a" * 40,
        title="v0.5.0",
        notes=notes,
        require_draft=True,
    )
    assert validated["id"] == 91

    duplicate = {**payload, "assets": [payload["assets"][0], payload["assets"][0]]}
    with pytest.raises(github_release.GitHubReleaseError, match="duplicate"):
        github_release.validate_release(
            duplicate,
            repository="synthetic/toolkit",
            tag="v0.5.0",
            target="a" * 40,
            title="v0.5.0",
            notes=notes,
        )

    with pytest.raises(github_release.GitHubReleaseError, match="metadata"):
        github_release.validate_release(
            {**payload, "target_commitish": "b" * 40},
            repository="synthetic/toolkit",
            tag="v0.5.0",
            target="a" * 40,
            title="v0.5.0",
            notes=notes,
        )


def test_release_ensure_validates_identity_before_any_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject malformed protected identity before release discovery or mutation."""

    requests: list[dict[str, Any]] = []

    def record_request(**kwargs: Any) -> tuple[int, object]:
        requests.append(kwargs)
        return 404, None

    monkeypatch.setattr(github_release, "_request", record_request)

    with pytest.raises(github_release.GitHubReleaseError, match="identity"):
        github_release.ensure_release(
            repository="synthetic/toolkit",
            tag="not-a-release-tag",
            target="a" * 40,
            title="not-a-release-tag",
            notes="synthetic notes\n",
            token="synthetic-token",
        )

    assert requests == []


def test_release_ensure_checks_the_first_page_beyond_its_listing_bound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fail closed on page six after five full bounded release pages."""

    endpoints: list[str] = []

    def fake_request(**kwargs: Any) -> tuple[int, object]:
        endpoint = kwargs["endpoint"]
        endpoints.append(endpoint)
        if "/releases/tags/" in endpoint:
            return 404, None
        if endpoint.endswith("/releases?per_page=100&page=6"):
            return 200, [{"tag_name": "v0.4.9"}]
        if "per_page=100" in endpoint:
            return 200, [{"tag_name": f"v0.0.{index}"} for index in range(100)]
        pytest.fail(f"unexpected release request: {endpoint}")

    monkeypatch.setattr(github_release, "_request", fake_request)

    with pytest.raises(github_release.GitHubReleaseError, match="page bound"):
        github_release.ensure_release(
            repository="synthetic/toolkit",
            tag="v0.5.0",
            target="a" * 40,
            title="v0.5.0",
            notes="synthetic notes\n",
            token="synthetic-token",
        )

    assert endpoints[-1] == "/repos/synthetic/toolkit/releases?per_page=100&page=6"
    assert not any(endpoint == "/repos/synthetic/toolkit/releases" for endpoint in endpoints)


def test_issue_receipt_json_read_is_bound_to_one_descriptor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Prevent a post-validation pathname swap from changing issue evidence."""

    evidence = tmp_path / "issue.json"
    replacement = tmp_path / "replacement.json"
    original = {"number": 76, "state": "open", "state_reason": None}
    changed = {"number": 99, "state": "closed", "state_reason": "completed"}
    evidence.write_text(json.dumps(original), encoding="utf-8")
    replacement.write_text(json.dumps(changed), encoding="utf-8")
    real_fstat = os.fstat
    swapped = False

    def swap_path() -> None:
        nonlocal swapped
        if not swapped:
            os.replace(replacement, evidence)
            swapped = True

    def racing_fstat(descriptor: int) -> os.stat_result:
        metadata = real_fstat(descriptor)
        swap_path()
        return metadata

    monkeypatch.setattr(issue_receipt.os, "fstat", racing_fstat)
    monkeypatch.setattr(
        Path,
        "read_bytes",
        lambda *_args, **_kwargs: pytest.fail("issue evidence reopened by pathname"),
    )

    assert issue_receipt.load_json(evidence, max_bytes=1024) == original


def test_issue_receipt_cli_writes_the_canonical_terminal_newline(tmp_path: Path) -> None:
    issue = tmp_path / "issue.json"
    comments = tmp_path / "comments.json"
    output = tmp_path / "body.md"
    issue.write_text(json.dumps({"number": 76, "state": "open", "state_reason": None}))
    comments.write_text("[]")
    import subprocess

    completed = subprocess.run(
        [
            sys.executable,
            str(ISSUE_RECEIPT_SCRIPT),
            "--issue-json",
            str(issue),
            "--comments-json",
            str(comments),
            "--issue",
            "76",
            "--version",
            "0.5.0",
            "--receipt-sha",
            "a" * 64,
            "--body-output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert output.read_text() == issue_receipt.receipt_body("0.5.0", 76, "a" * 64)
    assert output.read_bytes().endswith(b".\n")


def test_release_notes_are_read_from_one_open_descriptor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Keep validated release-note bytes bound to the descriptor opened first."""

    notes = tmp_path / "notes.md"
    replacement = tmp_path / "replacement.md"
    original = b"synthetic release notes\n"
    changed = b"substituted release notes\n"
    notes.write_bytes(original)
    replacement.write_bytes(changed)
    real_fstat = os.fstat
    swapped = False

    def swap_path() -> None:
        nonlocal swapped
        if not swapped:
            os.replace(replacement, notes)
            swapped = True

    def racing_fstat(descriptor: int) -> os.stat_result:
        metadata = real_fstat(descriptor)
        swap_path()
        return metadata

    monkeypatch.setattr(github_release.os, "fstat", racing_fstat)
    monkeypatch.setattr(
        Path,
        "read_text",
        lambda *_args, **_kwargs: pytest.fail("release notes reopened by pathname"),
    )

    assert github_release._metadata(notes) == original.decode("utf-8")


def test_release_notes_reject_growth_during_the_descriptor_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reject notes whose byte identity changes after descriptor validation."""

    notes = tmp_path / "notes.md"
    notes.write_bytes(b"bounded notes\n")
    real_fstat = os.fstat
    grown = False

    def grow_file() -> None:
        nonlocal grown
        if not grown:
            with notes.open("ab") as handle:
                handle.write(b"late bytes\n")
            grown = True

    def racing_fstat(descriptor: int) -> os.stat_result:
        metadata = real_fstat(descriptor)
        grow_file()
        return metadata

    monkeypatch.setattr(github_release.os, "fstat", racing_fstat)
    monkeypatch.setattr(
        Path,
        "read_text",
        lambda *_args, **_kwargs: pytest.fail("release notes reopened by pathname"),
    )

    with pytest.raises(github_release.GitHubReleaseError, match="changed while being read"):
        github_release._metadata(notes)


def test_release_notes_reject_symbolic_links(tmp_path: Path) -> None:
    """Do not follow a release-note pathname outside its validated file identity."""

    target = tmp_path / "actual-notes.md"
    target.write_text("synthetic notes\n", encoding="utf-8")
    link = tmp_path / "notes.md"
    link.symlink_to(target.name)

    with pytest.raises(github_release.GitHubReleaseError, match="unsafe"):
        github_release._metadata(link)


def test_release_asset_upload_uses_bytes_from_the_validated_descriptor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Prevent a pathname swap from changing bytes sent to the upload endpoint."""

    asset = tmp_path / "package.whl"
    replacement = tmp_path / "replacement.whl"
    original = b"original-asset"
    changed = b"replaced-asset"
    assert len(original) == len(changed)
    asset.write_bytes(original)
    replacement.write_bytes(changed)
    release = {
        "id": 91,
        "tag_name": "v0.5.0",
        "target_commitish": "a" * 40,
        "name": "v0.5.0",
        "body": "notes\n",
        "draft": True,
        "prerelease": False,
        "assets": [],
    }
    monkeypatch.setattr(github_release, "_read_release", lambda **_kwargs: release)
    real_fstat = os.fstat
    swapped = False
    uploaded_body = b""

    def swap_path() -> None:
        nonlocal swapped
        if not swapped:
            os.replace(replacement, asset)
            swapped = True

    def racing_fstat(descriptor: int) -> os.stat_result:
        metadata = real_fstat(descriptor)
        swap_path()
        return metadata

    def fake_request(**kwargs: Any) -> tuple[int, dict[str, Any]]:
        nonlocal uploaded_body
        uploaded_body = kwargs["body"]
        return 201, {"id": 7, "name": asset.name, "size": len(original)}

    monkeypatch.setattr(github_release.os, "fstat", racing_fstat)
    monkeypatch.setattr(
        Path,
        "read_bytes",
        lambda *_args, **_kwargs: pytest.fail("release asset reopened by pathname"),
    )
    monkeypatch.setattr(github_release, "_request", fake_request)

    github_release.upload_asset(
        repository="synthetic/toolkit",
        release_id=91,
        tag="v0.5.0",
        target="a" * 40,
        title="v0.5.0",
        notes="notes\n",
        asset=asset,
        token="synthetic-token",
    )

    assert uploaded_body == original
