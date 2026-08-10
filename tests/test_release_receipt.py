"""Contracts for deterministic stable-release delivery receipts."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "release_receipt.py"
PROVENANCE_SCRIPT = ROOT / "scripts" / "verify_registry_provenance.py"
ISSUE_RECEIPT_SCRIPT = ROOT / "scripts" / "release_issue_receipt.py"
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


def integrity_payload(filename: str, digest: str) -> dict[str, Any]:
    """Return one minimal registry-authoritative integrity response."""

    return {
        "version": 1,
        "attestation_bundles": [
            {
                "publisher": {
                    "kind": "GitHub",
                    "repository": "synthetic/open-code-review-toolkit",
                    "workflow": "release.yml",
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
    )

    payload["attestation_bundles"][0]["publisher"]["environment"] = "other"
    with pytest.raises(provenance.ProvenanceError, match="publisher"):
        provenance.verify_provenance(
            payload,
            filename=filename,
            digest=digest,
            environment="pypi-production",
            repository="synthetic/open-code-review-toolkit",
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
        )

    payload["attestation_bundles"][0]["attestations"][0]["envelope"]["statement"] = "bad"
    with pytest.raises(provenance.ProvenanceError, match="subject"):
        provenance.verify_provenance(
            payload,
            filename=filename,
            digest="a" * 64,
            environment="pypi-production",
            repository="synthetic/open-code-review-toolkit",
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
    assert 'release upload "${TAG}" "${asset}"' in workflow
    assert 'release upload "${TAG}" dist/*' not in workflow
    assert "release upload" in workflow
    assert "--clobber" not in workflow
    assert "bounded_release_download" in workflow
    assert "releases/assets/${asset_id}" in workflow
    assert "application/octet-stream" in workflow
    assert "gh release download" not in workflow
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
