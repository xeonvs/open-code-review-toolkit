"""Review-invocation evidence boundary tests."""

from ocr_toolkit.evidence.invocation import InvocationIdentifier, collect_invocation_evidence
from ocr_toolkit.evidence.model import RefRole, TrustClass
from ocr_toolkit.providers.gitlab import invocation_identifiers

SHA = "a" * 40


def test_ci_context_uses_only_bounded_allowlisted_identifiers() -> None:
    """Ignore secrets, URLs, refs, malformed IDs, and arbitrary environment state."""

    identifiers = invocation_identifiers(
        {
            "CI_PROJECT_ID": "123",
            "CI_PIPELINE_ID": " 456 ",
            "CI_JOB_ID": "not-numeric",
            "CI_MERGE_REQUEST_IID": "7",
            "CI_PROJECT_URL": "https://secret.example.invalid/group/project",
            "CI_COMMIT_REF_NAME": "private-branch",
            "OCR_LLM_TOKEN": "secret",
            "ARBITRARY": "ignored",
        }
    )
    assert [(item.field, item.value) for item in identifiers] == [
        ("project_id", "123"),
        ("pipeline_id", "456"),
        ("merge_request_iid", "7"),
    ]
    records = collect_invocation_evidence(identifiers, head_sha=SHA)

    ci_records = [record for record in records if record.kind == "review.ci_context"]
    assert [record.value["field"] for record in ci_records] == [
        "project_id",
        "pipeline_id",
        "merge_request_iid",
    ]
    assert {record.value["value"] for record in ci_records} == {"123", "456", "7"}
    assert {record.ref for record in ci_records} == {RefRole.SHARED}
    assert {record.trust for record in ci_records} == {TrustClass.INVOCATION}
    assert all(record.commit_sha == SHA for record in records)
    serialized = " ".join(str(record.to_dict()) for record in records)
    assert "secret.example.invalid" not in serialized
    assert "private-branch" not in serialized
    assert "secret" not in serialized


def test_installed_tool_versions_are_explicitly_excluded() -> None:
    """Explain intentional runner-state removal instead of silently losing coverage."""

    records = collect_invocation_evidence((), head_sha=SHA)

    assert len(records) == 1
    coverage = records[0]
    assert coverage.kind == "diagnostic.coverage"
    assert coverage.value["surface"] == "installed_tool_versions"
    assert coverage.value["status"] == "intentionally_excluded"
    assert coverage.trust == TrustClass.TOOLKIT


def test_core_rejects_malformed_provider_descriptors() -> None:
    """Prevent future adapters from injecting unbounded names or provenance."""

    records = collect_invocation_evidence(
        (
            InvocationIdentifier("GitLab!", "project_id", "123", "provider:test"),
            InvocationIdentifier("gitlab", "field", "123", "x" * 257),
        ),
        head_sha=SHA,
    )

    assert [record.kind for record in records] == ["diagnostic.coverage"]
