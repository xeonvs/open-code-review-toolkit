"""Semantic legacy-to-evidence parity contract tests."""

from __future__ import annotations

import pytest

from ocr_toolkit.evidence import EvidenceRecord, EvidenceStore, RefRole, TrustClass
from ocr_toolkit.evidence.parity import (
    attach_legacy_projection,
    compare_legacy_projection,
    render_parity_json,
)

SHA = "a" * 40


def _record(kind: str, value: object, provenance: str) -> EvidenceRecord:
    """Build one synthetic head evidence record."""

    return EvidenceRecord(
        kind=kind,
        value=value,  # type: ignore[arg-type]
        source_path="requirements.txt",
        ref=RefRole.HEAD,
        commit_sha=SHA,
        component="repository",
        provenance=provenance,
        trust=(
            TrustClass.DERIVED if provenance.startswith("legacy.") else TrustClass.SOURCE_REPOSITORY
        ),
    )


def test_parity_matches_independently_typed_dependency_and_image() -> None:
    store = EvidenceStore()
    assert store.add(
        _record(
            "repository.context",
            "## Python context\n- requests: 2.32.0\n- image: python:3.13\n",
            "legacy.context_projection",
        )
    )
    assert store.add(
        _record(
            "dependency.declared",
            {
                "identity": "requirements:requests",
                "fact": {"name": "requests", "version": "2.32.0"},
            },
            "typed parser:requirements.txt",
        )
    )
    assert store.add(
        _record(
            "ci.image",
            {"identity": "python:3.13", "fact": {"image": "python:3.13"}},
            "typed parser:.gitlab-ci.yml",
        )
    )

    report = compare_legacy_projection(store)

    assert report.complete
    assert report.comparable == 2
    assert report.matched == 2
    assert '"complete":true' in render_parity_json(store)


def test_parity_reports_missing_fact_and_does_not_count_legacy_reparse() -> None:
    store = EvidenceStore()
    assert store.add(
        _record(
            "repository.context",
            "## Python context\n- requests: 2.32.0\n",
            "legacy.context_projection",
        )
    )
    assert store.add(
        _record(
            "dependency.declared",
            {"identity": "legacy", "fact": {"name": "requests", "version": "2.32.0"}},
            "legacy.dependency_projection",
        )
    )

    report = compare_legacy_projection(store)

    assert not report.complete
    assert report.missing == ("dependency:requests:2.32.0",)


def test_parity_requires_a_nonempty_comparable_fixture() -> None:
    store = EvidenceStore()
    assert store.add(
        _record(
            "repository.context",
            "## Merge Request\n- changed files: 1\n",
            "legacy.context_projection",
        )
    )

    report = compare_legacy_projection(store)

    assert not report.complete
    assert report.missing == ("coverage:no-comparable-legacy-facts",)


def test_legacy_projection_requires_explicit_migration_oracle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = EvidenceStore()
    monkeypatch.setattr(
        "ocr_toolkit.evidence.parity.build_context",
        lambda: "## Python context\n- requests: `2.32.0`\n",
    )

    attach_legacy_projection(store)

    records = [record for record in store.records if record.kind == "repository.context"]
    assert len(records) == 1
    assert records[0].provenance == "legacy.context_projection"
