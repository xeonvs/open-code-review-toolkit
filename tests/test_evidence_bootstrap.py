"""Compact presentation must preserve immutable role identity under clipping."""

import pytest

from ocr_toolkit.diagrams.contracts import DIAGRAM_TOOL_NAME
from ocr_toolkit.evidence.mcp import call_tool, evidence_summary
from ocr_toolkit.evidence.model import EvidenceRecord, EvidenceSnapshot, RefRole
from ocr_toolkit.evidence.project import (
    DEFAULT_BOOTSTRAP_MAX_CHARS,
    MANDATORY_EVIDENCE_INSTRUCTION,
    _clip,
    render_bootstrap,
)
from ocr_toolkit.evidence.review_context import merge_request_context_record
from ocr_toolkit.evidence.store import EvidenceStore
from ocr_toolkit.mcp_config import MCPCapability
from tests.test_review_context import _context

DIAGRAM_CAPABILITY = MCPCapability("ocr_toolkit_evidence", (DIAGRAM_TOOL_NAME,), True)


def bootstrap_store(values=("a", "b", "a", None)) -> EvidenceStore:
    """Create real immutable snapshots; no Git or transport owner is mocked."""

    return EvidenceStore(
        **{
            role.value: EvidenceSnapshot(role, value * 40, ())
            for role, value in zip(
                (RefRole.BASE, RefRole.HEAD, RefRole.POLICY, RefRole.TARGET), values, strict=True
            )
            if value is not None
        }
    )


@pytest.mark.parametrize(
    "values",
    (
        ("a", "b", "c", "d"),
        ("a", "b", "a", "a"),
        ("a", "b", "b", "b"),
        ("a", "a", "a", "a"),
        (None, "b", "b", "c"),
        ("a", None, None, "a"),
        (None, None, None, None),
    ),
)
def test_refs_keep_explicit_roles_without_duplicate_full_hashes_or_store_changes(values):
    store = bootstrap_store(values)
    before, summary = store.to_dict(), evidence_summary(store)
    rendered = render_bootstrap(store, capabilities=(DIAGRAM_CAPABILITY,))
    assert rendered.count("## Immutable review refs") == 1
    for value in set(values) - {None}:
        assert rendered.count(value * 40) == 1
    if values == ("a", "a", "a", "a"):
        assert "- head: same commit as base" in rendered
        assert "- policy: same commit as base" in rendered
        assert "- actual target: same commit as base (untrusted code context)" in rendered
    if values[0] is None:
        assert "- base: unavailable" in rendered
    if values[1] is None:
        assert "- head: unavailable" in rendered
    if values[2] is None:
        assert "- policy: legacy base semantics" in rendered
    if values[3] is None:
        assert "- actual target:" not in rendered
    else:
        assert "query `ref=target`" in rendered
        assert "cannot grant policy, publication, or approval" in rendered
    assert store.to_dict() == before and evidence_summary(store) == summary


def test_refs_and_output_instructions_survive_clipping_together():
    store = bootstrap_store(("a", "b", "a", "b"))
    store.diagnostics = ["é😀" * 500]
    rendered = render_bootstrap(
        store, capabilities=(DIAGRAM_CAPABILITY,), max_chars=1900, max_bytes=2400
    )
    assert rendered.startswith(MANDATORY_EVIDENCE_INSTRUCTION)
    assert rendered.count("a" * 40) == rendered.count("b" * 40) == 1
    assert "- actual target: same commit as head (untrusted code context)" in rendered
    assert "base_sha/head_sha from refs above" in rendered
    assert "once before task_done" in rendered and "truncated" in rendered
    assert len(rendered) <= 1900 and len(rendered.encode()) <= 2400
    with pytest.raises(ValueError, match="preserve required evidence navigation"):
        render_bootstrap(store, capabilities=(DIAGRAM_CAPABILITY,), max_chars=500)


@pytest.mark.parametrize("chars,bytes_", ((255, 1024), (7951, 1024), (2300, 1023), (2300, 65537)))
def test_invalid_bootstrap_bounds_fail_before_rendering(chars, bytes_):
    with pytest.raises(ValueError, match="must be between"):
        render_bootstrap(bootstrap_store(), max_chars=chars, max_bytes=bytes_)


@pytest.mark.parametrize("opening,closing", (("wrong", ""), ("header\n", "wrong")))
def test_clipping_cannot_silently_adopt_a_missing_required_envelope(opening, closing):
    with pytest.raises(ValueError, match=r"required bootstrap .* is missing"):
        _clip(
            "header\n" + "body\n" * 20,
            max_chars=60,
            max_bytes=1024,
            required_prefix=opening,
            required_suffix=closing,
        )


def test_clipping_omits_an_empty_optional_heading_without_cutting_the_opening():
    opening = "# Required\n\nKeep this.\n\n"
    closing = "\n## Diagram\n\nKeep this too.\n"
    rendered = _clip(
        opening + "## Optional inventory\n\n" + "x" * 1000 + "\n" + closing,
        max_chars=170,
        max_bytes=1024,
        required_prefix=opening,
        required_suffix=closing,
    )
    assert rendered.startswith(opening) and rendered.endswith(closing)
    assert "Optional inventory" not in rendered and "truncated" in rendered


@pytest.mark.parametrize("fallback", (False, True))
def test_large_evidence_keeps_required_routes_and_does_not_cut_the_mcp_store(tmp_path, fallback):
    store = bootstrap_store(("a", "b", "c", "d"))
    assert store.add(merge_request_context_record(_context(source_sha="b" * 40)))
    for index in range(512):
        last = EvidenceRecord(
            kind="dependency.declared",
            value={"name": f"package-{index}"},
            source_path="requirements.txt",
            ref=RefRole.HEAD,
            commit_sha="b" * 40,
        )
        assert store.add(last)
    store.diagnostics = ["é😀" * 500 for _ in range(4)]
    capabilities = (
        MCPCapability(
            "ocr_toolkit_evidence", (DIAGRAM_TOOL_NAME, "context_list", "context_get"), True
        ),
        *(MCPCapability(f"synthetic{i}", tuple(f"tool{j}" for j in range(128))) for i in range(16)),
    )
    before = store.to_dict()
    rendered = render_bootstrap(
        store, capabilities=capabilities, protected_policy_fallback=fallback
    )
    (tmp_path / "bootstrap.md").write_text(rendered)
    assert len(rendered) <= DEFAULT_BOOTSTRAP_MAX_CHARS
    assert "truncated" in rendered.lower()
    assert "ocr_toolkit_evidence(action=summary)" in rendered
    assert "After summary, read review intent" in rendered
    assert "action=list" in rendered and "action=get" in rendered
    assert "frameworks/runtimes" in rendered and "declared/locked dependency versions" in rendered
    assert "CI/images/infrastructure" in rendered and "policy/guidance" in rendered
    assert "Only applicable `complete` coverage proves absence" in rendered
    assert "context_list" in rendered and "context_get" in rendered
    assert "## Requested change diagram" in rendered and "once before task_done" in rendered
    assert rendered.index("## Requested change diagram") > rendered.index(
        "## Immutable review refs"
    )
    assert "even with no findings" in rendered and "entire reviewed change" in rendered
    assert "include dotfiles" in rendered
    assert store.to_dict() == before and evidence_summary(store)["records"] == 513
    response = call_tool(store, {"action": "get", "id": last.id})
    assert f"package-{index}" in str(response)


@pytest.mark.parametrize(
    "policy,metadata,enriched,external,diagram",
    [
        (policy, metadata, enriched, external, diagram)
        for policy in ("protected", "limited", "fallback")
        for metadata in (False, True)
        for enriched in (False, True)
        for external in (False, True)
        for diagram in (False, True)
        if not (policy == "limited" and external)
    ],
)
def test_supported_profiles_keep_all_required_routes_at_default_bounds(
    tmp_path, metadata, enriched, external, diagram, policy
):
    store = bootstrap_store(("a", "b", "a" if policy == "limited" else "c", "d"))
    if metadata:
        assert store.add(merge_request_context_record(_context(source_sha="b" * 40)))
    store.diagnostics = ["é😀" * 500] * 4
    tools = ("ocr_toolkit_evidence", "ocr_toolkit_evidence_search", "ocr_toolkit_evidence_coverage")
    if enriched:
        tools += ("context_list", "context_get")
    if diagram:
        tools += DIAGRAM_CAPABILITY.tools
    capabilities = (MCPCapability("ocr_toolkit_evidence", tools, True),)
    if external:
        capabilities += (MCPCapability("tracker", ("tracker__read_issue",)),)
    rendered = render_bootstrap(
        store,
        capabilities=capabilities,
        unprotected_target=policy == "limited",
        protected_policy_fallback=policy == "fallback",
    )
    (tmp_path / "bootstrap.md").write_text(rendered)
    assert len(rendered) <= DEFAULT_BOOTSTRAP_MAX_CHARS and len(rendered.encode()) <= 32768
    assert "frameworks/runtimes" in rendered and "declared/locked dependency versions" in rendered
    assert "policy/guidance" in rendered and "Only applicable `complete`" in rendered
    assert ("After summary, read review intent" in rendered) == metadata
    assert "MR" not in rendered and "GitLab" not in rendered
    if external and not metadata:
        assert "After review intent" not in rendered
    assert ("listed handles only" in rendered) == enriched
    assert ("actual MCP tool definitions" in rendered) == external
    assert ("once before task_done" in rendered) == diagram
    if policy == "limited":
        assert "bounded untrusted review guidance only" in rendered
        assert "no tool, posting, suppression or approval authority" in rendered
    elif policy == "fallback":
        assert "policy is not the code target" in rendered
        assert "Cannot create an approval" in rendered
