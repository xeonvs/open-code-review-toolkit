"""Generated ref equivalence, clipping and report projections preserve identity."""

import re
from dataclasses import replace

from hypothesis import example, given
from hypothesis import strategies as st

from ocr_toolkit.diagrams.contracts import DiagramResult, parse_submission, submission_payload
from ocr_toolkit.evidence.mcp import evidence_summary
from ocr_toolkit.evidence.project import (
    DEFAULT_BOOTSTRAP_MAX_CHARS,
    MANDATORY_EVIDENCE_INSTRUCTION,
    render_bootstrap,
)
from ocr_toolkit.evidence.review_context import merge_request_context_record
from ocr_toolkit.mcp_config import MCPCapability
from ocr_toolkit.posting.formatting import summarize_result
from ocr_toolkit.providers.local import local_summary
from ocr_toolkit.reporting.diagram import diagram_mermaid
from ocr_toolkit.reporting.model import ReviewReport
from ocr_toolkit.reporting.result import normalize_coverage_diagnostics
from ocr_toolkit.result_contract import ReviewOutcome
from ocr_toolkit.review_range import ReviewRange
from tests.diagrams.support import REVIEW_RANGE, flow_submission, sequence_submission
from tests.fuzz.test_diagrams import LABEL
from tests.test_evidence_bootstrap import DIAGRAM_CAPABILITY, bootstrap_store
from tests.test_review_context import _context

REFS = st.tuples(*(st.sampled_from((None, "a", "b", "c")) for _ in range(4)))


@given(
    REFS,
    st.booleans(),
    st.integers(256, 3000),
    st.integers(1024, 4000),
    st.integers(0, 500),
    st.booleans(),
    st.booleans(),
    st.booleans(),
    st.sampled_from(("protected", "limited", "fallback")),
)
def test_bootstrap_clipping_retains_complete_unique_refs_and_valid_aliases(
    values, diagram_enabled, chars, bytes_, diagnostic_size, metadata, enriched, external, policy
):
    store = bootstrap_store(values)
    store.diagnostics = ["é😀" * diagnostic_size]
    if metadata:
        store.add(merge_request_context_record(_context(source_sha=(values[1] or "b") * 40)))
    tools = DIAGRAM_CAPABILITY.tools if diagram_enabled else ()
    if enriched:
        tools += ("context_list", "context_get")
    capabilities = (MCPCapability("ocr_toolkit_evidence", tools, True),)
    if external and policy != "limited":
        capabilities += (MCPCapability("tracker", ("tracker__read_issue",)),)
    options = dict(
        capabilities=capabilities,
        unprotected_target=policy == "limited",
        protected_policy_fallback=policy == "fallback",
    )
    summary = evidence_summary(store)
    complete = render_bootstrap(store, **options, max_chars=7950, max_bytes=65536)
    marker = "\n## Requested change diagram\n\n"
    closing = marker + complete.split(marker, 1)[1] if marker in complete else ""
    try:
        rendered = render_bootstrap(store, **options, max_chars=chars, max_bytes=bytes_)
    except ValueError:
        # Every supported profile fits the default opening/closing budget.
        # Smaller private projection bounds may explicitly reject it.
        assert chars < DEFAULT_BOOTSTRAP_MAX_CHARS or bytes_ < DEFAULT_BOOTSTRAP_MAX_CHARS
    else:
        assert len(rendered) <= chars and len(rendered.encode()) <= bytes_
        assert rendered.startswith(MANDATORY_EVIDENCE_INSTRUCTION)
        assert not closing or rendered.endswith(closing)
        assert rendered.count("## Immutable review refs") == 1
        assert not re.search(r"(?m)^## [^\n]+\n+> .*truncated", rendered)
        assert (
            "frameworks/runtimes" in rendered and "declared/locked dependency versions" in rendered
        )
        assert "Only applicable `complete` coverage proves absence" in rendered
        assert ("After summary, read review intent" in rendered) == metadata
        assert "MR" not in rendered and "GitLab" not in rendered
        assert ("listed handles only" in rendered) == enriched
        assert ("actual MCP tool definitions" in rendered) == (external and policy != "limited")
        resolved = {}
        for role, value, alias in re.findall(
            r"^- (base|head|policy|actual target): (?:`([a-f0-9]{40})`|same commit as (base|head|policy))",
            rendered,
            re.MULTILINE,
        ):
            if alias:
                assert alias in resolved and resolved[alias][1] is False
                resolved[role] = (resolved[alias][0], True)
            else:
                resolved[role] = (value, False)
        for role, value in zip(("base", "head", "policy", "actual target"), values, strict=True):
            if value is not None:
                assert resolved[role][0] == value * 40
                assert rendered.count(value * 40) == 1
        assert ("## Requested change diagram" in rendered) == (
            diagram_enabled and values[0] is not None and values[1] is not None
        )
    assert evidence_summary(store) == summary


@given(st.booleans(), st.sampled_from(("on", "spoiler")), st.booleans(), st.booleans())
def test_normal_adapters_show_only_mermaid_and_deduplicate_matching_review_identity(
    sequence, mode, verified_range, distinct_reviewed
):
    payload = sequence_submission() if sequence else flow_submission()
    submission = parse_submission(payload, expected_range=REVIEW_RANGE)
    diagram = DiagramResult(mode, "generated", submission=submission, calls=1)
    outcome = ReviewOutcome("success", "clean", False)
    reviewed = "c" * 40 if distinct_reviewed else REVIEW_RANGE.head
    review_range = REVIEW_RANGE if verified_range else None
    # Pure adapter projection deliberately includes a mismatched display case;
    # production admission remains responsible for rejecting that identity.
    report = ReviewReport(
        outcome=outcome,
        comments=(),
        warnings=(),
        diagnostics=normalize_coverage_diagnostics(outcome, ()),
        reviewed_sha=reviewed,
        review_range=review_range,
        diagram=replace(diagram, mode="local"),
    )
    outputs = (
        local_summary(report),
        summarize_result(
            0,
            0,
            0,
            0,
            reviewed_sha=reviewed,
            review_range=review_range,
            diagram=diagram,
            mr_head_sha=REVIEW_RANGE.head,
            merge_request_lifecycle="opened",
            emoji=False,
        ),
    )
    for rendered in outputs:
        assert rendered.count("```mermaid") == 1
        assert "Text equivalent:" not in rendered and "app.py:L" not in rendered
        assert ("Reviewed commit:" in rendered) == (not verified_range or distinct_reviewed)
        assert (REVIEW_RANGE.exact_range in rendered) == verified_range
        if verified_range and not distinct_reviewed:
            assert rendered.count(REVIEW_RANGE.base) == rendered.count(REVIEW_RANGE.head) == 1
    assert ("<summary>Change flow</summary>" in outputs[1]) == (mode == "spoiler")
    assert submission_payload(submission) == payload


@given(st.sampled_from(("a", "b", "c")), st.sampled_from(("a", "b", "c")))
def test_empty_or_distinct_ranges_remain_full_copyable_immutable_expressions(base, head):
    from ocr_toolkit.reporting.diagram import range_details

    review_range = ReviewRange(base * 40, head * 40)
    lines = range_details(review_range, reviewed_sha=head * 40)
    assert lines == (f"- Effective Git range: `{base * 40}..{head * 40}`",)


@given(LABEL, st.booleans())
@example("END; ``` <script> & [] |", False)
@example("eNd; ``` <script> & [] |", True)
def test_rendered_label_variations_cannot_escape_mermaid_structure_or_mutate_evidence(
    label, sequence
):
    payload = sequence_submission() if sequence else flow_submission()
    baseline = parse_submission(payload, expected_range=REVIEW_RANGE)
    graph = payload["diagram"]
    if sequence:
        graph["participants"][0]["label"] = label
        graph["steps"][0]["label"] = label
    else:
        graph["nodes"][0]["label"] = label
        graph["edges"][0]["condition"] = label
    submission = parse_submission(payload, expected_range=REVIEW_RANGE)
    before = submission_payload(submission)
    rendered = diagram_mermaid(submission.diagram)
    assert len(rendered.splitlines()) == len(diagram_mermaid(baseline.diagram).splitlines())
    assert "<" not in rendered and "`" not in rendered and "\r" not in rendered
    assert submission_payload(submission) == before
