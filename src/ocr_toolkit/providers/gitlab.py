"""Normalize a closed allowlist of non-secret GitLab CI review identifiers."""

from __future__ import annotations

from collections.abc import Mapping

from ocr_toolkit.evidence.invocation import MAX_CI_IDENTIFIER_CHARS, InvocationIdentifier

CI_IDENTIFIER_FIELDS = (
    ("CI_PROJECT_ID", "project_id"),
    ("CI_PIPELINE_ID", "pipeline_id"),
    ("CI_JOB_ID", "job_id"),
    ("CI_MERGE_REQUEST_IID", "merge_request_iid"),
)


def invocation_identifiers(environment: Mapping[str, str]) -> tuple[InvocationIdentifier, ...]:
    """Return only explicitly allowlisted GitLab numeric identifiers."""

    identifiers = []
    for variable, field in CI_IDENTIFIER_FIELDS:
        value = environment.get(variable, "").strip()
        if (
            not value
            or len(value) > MAX_CI_IDENTIFIER_CHARS
            or not value.isascii()
            or not value.isdecimal()
        ):
            continue
        identifiers.append(
            InvocationIdentifier(
                provider="gitlab",
                field=field,
                value=value,
                provenance=f"gitlab.environment:{variable}",
            )
        )
    return tuple(identifiers)
