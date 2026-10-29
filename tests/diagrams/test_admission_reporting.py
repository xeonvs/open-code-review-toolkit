"""Source/DLP admission and pure presentation of whole optional diagrams."""

from dataclasses import replace
from subprocess import TimeoutExpired

import pytest

from ocr_toolkit.context.dlp import ForbiddenMatcher
from ocr_toolkit.diagrams.admission import admit_diagram
from ocr_toolkit.diagrams.collector import CollectorSnapshot
from ocr_toolkit.diagrams.contracts import parse_submission
from ocr_toolkit.reporting.diagram import (
    diagram_mermaid,
    diagram_section,
    prepare_diagram_section,
    range_details,
)
from tests.diagrams.support import REVIEW_RANGE, flow_submission, sequence_submission


def admitted(payload, *, source="line one\nline two\nline three\n", enabled=True, forbidden=()):
    candidate = parse_submission(payload, expected_range=REVIEW_RANGE)
    return admit_diagram(
        "local",
        CollectorSnapshot(1, 1000, "none", candidate),
        review_range=REVIEW_RANGE,
        output_calls=1,
        read_source=lambda _path: source,
        forbidden_matcher=ForbiddenMatcher.compile(forbidden),
        dlp_enabled=enabled,
    )


@pytest.mark.parametrize(
    "factory,header", ((flow_submission, "flowchart LR"), (sequence_submission, "sequenceDiagram"))
)
def test_admitted_variants_have_only_mermaid_without_textual_source_listing(
    factory, header: str
) -> None:
    result = admitted(factory())
    assert result.state == "generated" and result.submission is not None
    diagram = result.submission.diagram
    assert diagram is not None
    mermaid = diagram_mermaid(diagram)
    assert mermaid.startswith(header)
    expanded, collapsed = diagram_section(result), diagram_section(result, collapsed=True)
    assert "```mermaid\n" in expanded and "Text equivalent:" not in expanded
    assert "app.py:L1" not in expanded and "\n- " not in expanded
    assert "may omit routes" in expanded and "do not prove behavior" in expanded
    assert collapsed.startswith("<details><summary>Change flow</summary>\n\n")
    assert collapsed.endswith("\n\n</details>")
    assert mermaid in collapsed and "Text equivalent:" not in collapsed
    assert "app.py:L1" not in collapsed and "\n- " not in collapsed


@pytest.mark.parametrize(
    "text",
    (
        "version < 2020.1.10",
        "date < 2020-01-01",
        "version >= 2026.10.19",
        "IP 192.0.2.123",
        "network 192.0.2.128/25",
        "Decimal('123456789.1234')",
        "'login_password': '{{ service_password }}'",
        '"login_password": ""',
        "if a < b and c > d",
    ),
)
def test_technical_conditions_survive_the_whole_admission_boundary(text: str) -> None:
    payload = flow_submission()
    payload["diagram"]["edges"][0]["condition"] = text
    result = admitted(payload)
    assert result.state == "generated"
    assert diagram_mermaid(result.submission.diagram) in diagram_section(result)


@pytest.mark.parametrize(
    "sensitive",
    (
        "Call +1 202 555 0142",
        "person@example.invalid",
        'login_password: "synthetic-secret"',
        "person&#64;example.invalid",
    ),
)
@pytest.mark.parametrize("field", ("label", "condition"))
def test_source_reference_never_exempts_sensitive_label_or_necessary_condition(
    sensitive: str, field: str
) -> None:
    payload = flow_submission()
    target = payload["diagram"]["nodes"][0] if field == "label" else payload["diagram"]["edges"][0]
    target[field] = "version < 2020.1.10; " + sensitive
    # The exact same sensitive content exists in the referenced code. Source
    # proof must not convert it into permission to publish a copied secret/PII.
    result = admitted(payload, source=target[field] + "\nmore\nmore\n")
    assert result.state == "omitted-invalid" and result.reason == "dlp"
    assert result.submission is None and diagram_section(result) == ""


@pytest.mark.parametrize(
    "label",
    (
        "<b>hidden</b>",
        "&lt;b&gt;hidden&lt;/b&gt;",
        "%%{init:unsafe}%%",
        "&#10;new line",
        "&#x202e;hidden",
    ),
)
@pytest.mark.parametrize("enabled", (False, True))
def test_raw_markup_directives_and_encoded_controls_are_never_diagram_syntax(
    label: str, enabled: bool
) -> None:
    payload = flow_submission()
    payload["diagram"]["nodes"][0]["label"] = label
    result = admitted(payload, enabled=enabled)
    assert result.state == "omitted-invalid" and result.reason == "invalid"


def test_private_context_copy_omits_whole_diagram_without_projecting_conditions() -> None:
    payload = sequence_submission()
    payload["diagram"]["steps"][1]["branches"][0]["condition"] = (
        "private context requires this path"
    )
    result = admitted(payload, forbidden=("private context requires this path",))
    assert result.state == "omitted-invalid" and result.reason == "dlp"
    assert result.submission is None


@pytest.mark.parametrize(
    "source", (None, "", "one\n", "one\x00\ntwo\nthree\n", "one\u2028two\u2028three")
)
def test_missing_binary_or_out_of_bounds_source_spans_are_not_mechanical_proof(
    source: str | None,
) -> None:
    assert admitted(flow_submission(), source=source).reason == "reference"


def test_source_unavailability_and_timeout_only_omit_the_optional_channel() -> None:
    candidate = parse_submission(flow_submission(), expected_range=REVIEW_RANGE)
    for error in (OSError("unavailable"), ValueError("unsafe"), TimeoutExpired("git", 15)):

        def read(_path):
            raise error

        result = admit_diagram(
            "local",
            CollectorSnapshot(1, 1000, "none", candidate),
            review_range=REVIEW_RANGE,
            output_calls=1,
            read_source=read,
            forbidden_matcher=ForbiddenMatcher.compile(()),
            dlp_enabled=True,
        )
        assert result.reason == "reference"


def test_snapshot_state_native_count_and_range_admission_are_independent() -> None:
    candidate = parse_submission(flow_submission(), expected_range=REVIEW_RANGE)
    snapshot = CollectorSnapshot(1, 1000, "none", candidate)
    options = dict(
        review_range=REVIEW_RANGE,
        output_calls=1,
        read_source=lambda _path: "one\ntwo\nthree\n",
        forbidden_matcher=ForbiddenMatcher.compile(()),
        dlp_enabled=True,
    )
    assert admit_diagram("local", None, **options).reason == "unavailable"
    for reason in ("invalid", "budget", "conflict"):
        assert admit_diagram("local", replace(snapshot, reason=reason), **options).reason == reason
    assert (
        admit_diagram("local", replace(snapshot, submissions=0), **options).reason == "unavailable"
    )
    assert admit_diagram("local", snapshot, **{**options, "review_range": None}).reason == "range"
    assert admit_diagram("local", replace(snapshot, candidate=None), **options).reason == "range"
    empty = CollectorSnapshot(0, 0, "none", None)
    assert admit_diagram("local", empty, **{**options, "output_calls": 0}).state == "not-generated"
    not_applicable = parse_submission(
        {"state": "not-applicable", "base_sha": REVIEW_RANGE.base, "head_sha": REVIEW_RANGE.head},
        expected_range=REVIEW_RANGE,
    )
    assert (
        admit_diagram("local", replace(snapshot, candidate=not_applicable), **options).state
        == "not-applicable"
    )


def test_renderer_owns_identifiers_escaping_and_reserved_tokens() -> None:
    payload = sequence_submission()
    payload["diagram"]["steps"][0]["label"] = 'end; "quoted" # [] →'
    result = admitted(payload)
    assert result.submission is not None and result.submission.diagram is not None
    mermaid = diagram_mermaid(result.submission.diagram)
    assert "participant p0 as API" in mermaid
    assert "#101;nd#59;" in mermaid and "#34;quoted#34;" in mermaid
    assert "#35;" in mermaid and "#91;#93;" in mermaid
    assert "p0->>p1" in mermaid and "p0-->>p1" in mermaid
    assert "else request rejected" in mermaid
    assert mermaid.count("\n    end") == 1 and mermaid.count("\n        end") == 1


def test_report_range_details_never_label_a_legacy_range_as_verified() -> None:
    assert range_details(None) == ("- Effective Git range: unverified",)
    assert range_details(REVIEW_RANGE) == (f"- Effective Git range: `{REVIEW_RANGE.exact_range}`",)


def test_generated_without_a_presentation_remains_an_optional_omission() -> None:
    result = replace(admitted(flow_submission()), submission=None)
    omitted, section, failed = prepare_diagram_section(result)
    assert failed and section == ""
    assert omitted.state == "omitted-invalid" and omitted.reason == "unavailable"
    assert omitted.calls == result.calls
