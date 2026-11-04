"""Malformed source facts cannot acquire code or syntax interpretation authority."""

from dataclasses import replace

import pytest

from ocr_toolkit.evidence.opaque_code import prove_opaque_code
from ocr_toolkit.evidence.text_contracts import (
    RepositoryTextExcerpt,
    RepositoryTextMetadata,
    SourceReadResult,
    excerpt_from_lines,
    source_lines,
)


def test_bounded_in_memory_excerpt_handles_empty_range_and_transport_overhead():
    assert source_lines("") == ()
    assert excerpt_from_lines((), 1, 1).reason == "range"
    assert excerpt_from_lines(("x",) * 202, 1, 202).reason == "limit"
    assert excerpt_from_lines(("x" * 12_202,), 1, 1).reason == "limit"
    assert excerpt_from_lines(("x" * 12_001,), 1, 1).reason == "limit"
    assert excerpt_from_lines(("x" * 11_999 + "\r",), 1, 1).text is not None


@pytest.mark.parametrize(
    "case,expected",
    [
        ("missing", "unavailable"),
        ("line-count", "line-mismatch"),
        ("no-excerpt", "excerpt-unavailable"),
        ("limit", "excerpt-limit"),
        ("range", "line-mismatch"),
        ("text-type", "unavailable"),
        ("source-type", "unavailable"),
        ("exception", "unavailable"),
    ],
)
def test_invalid_source_fact_branches_never_prove_material(case, expected):
    value = SourceReadResult(
        RepositoryTextMetadata("a" * 40, 5, 1, (RepositoryTextExcerpt(1, 1, "safe"),)), "none"
    )
    if case == "missing":
        value = SourceReadResult(reason="none")
    elif case == "line-count":
        value = replace(value, metadata=replace(value.metadata, line_count=False))
    elif case == "no-excerpt":
        value = replace(value, metadata=replace(value.metadata, excerpts=()))
    elif case in {"limit", "range", "text-type"}:
        piece = RepositoryTextExcerpt(
            1, 1, [] if case == "text-type" else None, "limit" if case == "limit" else "range"
        )
        value = replace(value, metadata=replace(value.metadata, excerpts=(piece,)))
    elif case == "source-type":
        value = replace(value, syntax_source=[])

    def read(*args):
        if case == "exception":
            raise OSError("synthetic failure")
        return value

    proof = prove_opaque_code(
        {"line": 1, "existing_code": "safe"}, "source", read_head_excerpt=read
    )
    assert not proof.existing_verified and proof.source_reason == expected


def test_identity_survives_oversized_optional_syntax_without_parsing_fragment():
    value = SourceReadResult(
        RepositoryTextMetadata("a" * 40, 270_000, 1, (RepositoryTextExcerpt(1, 1, "safe"),)),
        "none",
        "x" * 270_000,
    )
    proof = prove_opaque_code(
        {"line": 1, "existing_code": "safe"}, "source", read_head_excerpt=lambda *args: value
    )
    assert proof.existing_verified and proof.existing_context is None
    assert proof.syntax_reason == "source-limit"
