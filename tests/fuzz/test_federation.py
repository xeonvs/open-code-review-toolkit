"""Bounded hostile registries, schemas, arguments, upstream results and wire frames."""

import json
from copy import deepcopy

import mcp_types as types
import pytest
from hypothesis import given
from hypothesis import strategies as st

from ocr_toolkit.context.dlp import ForbiddenMatcher
from ocr_toolkit.federation.admission import arguments, compile_schema, encode, result
from ocr_toolkit.federation.contracts import FederationError, ToolPolicy
from ocr_toolkit.federation.registry import parse_registry
from ocr_toolkit.federation.transport import parse_frame
from ocr_toolkit.reporting.federation import COUNTERS, reconcile, valid_reconciliation
from tests.fuzz.strategies import json_values
from tests.test_review_receipt_v11 import _receipt_v11

MATCHER = ForbiddenMatcher.compile(())
SCHEMA = {
    "type": "object",
    "properties": {"value": {"type": "string", "maxLength": 80}},
    "required": ["value"],
    "additionalProperties": False,
}
REGISTRY = {
    "version": 2,
    "servers": {
        "docs": {
            "transport": {"type": "https", "url": "https://synthetic.invalid/mcp"},
            "tools": {"lookup": {"assurance": "review_read"}},
        }
    },
}
REGISTRY_FIELDS = (
    ("version",),
    ("servers",),
    ("servers", "docs", "transport"),
    ("servers", "docs", "transport", "type"),
    ("servers", "docs", "transport", "url"),
    ("servers", "docs", "tools"),
    ("servers", "docs", "tools", "lookup"),
    ("servers", "docs", "tools", "lookup", "assurance"),
    ("servers", "docs", "headers_from"),
)


@given(st.sampled_from(REGISTRY_FIELDS), json_values(), st.sampled_from(("local", "gitlab_mr")))
def test_nested_registry_mutations_never_escape_the_closed_authority_boundary(
    path, value, profile
) -> None:
    document = deepcopy(REGISTRY)
    parent = document
    for part in path[:-1]:
        parent = parent[part]
    parent[path[-1]] = value
    try:
        admitted = parse_registry(json.dumps(document, ensure_ascii=True), profile=profile)
    except FederationError:
        return
    aliases = [tool.alias for server in admitted.servers for tool in server.tools]
    assert len(aliases) == len(set(aliases)) <= 128
    assert all(server.transport in ("https", "stdio") for server in admitted.servers)
    assert all(
        tool.assurance in ("advisory", "review_read")
        for server in admitted.servers
        for tool in server.tools
    )
    assert profile == "local" or all(server.transport == "https" for server in admitted.servers)


@given(
    st.sampled_from(
        (
            ("type",),
            ("properties",),
            ("properties", "value", "type"),
            ("properties", "value", "maxLength"),
            ("required",),
            ("additionalProperties",),
            ("oneOf",),
            ("$ref",),
        )
    ),
    json_values(),
)
def test_schema_field_variations_compile_or_fail_through_federation_error(path, value) -> None:
    document = deepcopy(SCHEMA)
    parent = document
    for part in path[:-1]:
        parent = parent[part]
    parent[path[-1]] = value
    try:
        validator = compile_schema(document, MATCHER)
        arguments({"value": "safe"}, ToolPolicy("lookup", "docs__lookup"), validator, MATCHER)
    except FederationError:
        return
    assert validator.is_valid({"value": "safe"})


@given(json_values())
def test_nested_arguments_have_finite_canonical_json_or_a_closed_rejection(value) -> None:
    validator = compile_schema({"type": "object"}, MATCHER)
    try:
        admitted, canonical = arguments(
            value, ToolPolicy("lookup", "docs__lookup"), validator, MATCHER
        )
    except FederationError:
        return
    assert isinstance(admitted, dict) and json.loads(canonical) == admitted
    assert len(canonical) <= 32 * 1024


@given(
    st.sampled_from(("https", "http")),
    st.sampled_from(("synthetic.invalid", "foreign.invalid")),
    st.sampled_from(("", ":443", ":444")),
    st.sampled_from(("", "user@", "user:synthetic@")),
)
def test_nested_resource_origins_cannot_gain_authority_by_representation(
    scheme, host, port, user
) -> None:
    url = f"{scheme}://{user}{host}{port}/resource"
    value = {"nested": [{"url": url}]}
    expected = (
        scheme == "https" and host == "synthetic.invalid" and port in ("", ":443") and not user
    )
    policy = ToolPolicy("lookup", "docs__lookup", resource_origins=("https://synthetic.invalid",))
    validator = compile_schema({"type": "object"}, MATCHER)
    if expected:
        assert arguments(value, policy, validator, MATCHER)[0] == value
    else:
        with pytest.raises(FederationError):
            arguments(value, policy, validator, MATCHER)


@given(json_values(), st.text(alphabet="safe abcé漢😀012", max_size=40), st.booleans())
def test_upstream_text_and_structured_results_are_atomic_and_drop_transport_metadata(
    structured, text, failed
) -> None:
    value = types.CallToolResult(
        content=[types.TextContent(type="text", text=text)],
        structured_content={"value": structured},
        is_error=failed,
        meta={"server-only": "synthetic metadata"},
    )
    assert value.meta == {"server-only": "synthetic metadata"}
    try:
        admitted = result(value, None, MATCHER)
    except FederationError:
        return
    assert not failed and admitted.is_error is False
    assert admitted.structured_content == {"value": structured}
    assert "server-only" not in encode(admitted.model_dump(by_alias=True)).decode()


@given(
    st.one_of(
        st.binary(max_size=1024),
        json_values().map(lambda value: json.dumps(value, ensure_ascii=True).encode()),
    )
)
def test_hostile_wire_frames_never_leak_incidental_sdk_or_json_exceptions(raw) -> None:
    try:
        frame = parse_frame(raw)
    except FederationError:
        return
    assert frame.message is not None


@given(st.booleans())
def test_boolean_response_ids_cannot_alias_an_integer_request_id(value) -> None:
    raw = json.dumps({"jsonrpc": "2.0", "id": value, "result": {}}).encode()
    with pytest.raises(FederationError):
        parse_frame(raw)


@given(
    st.sampled_from(("local", "gitlab_mr")),
    st.sampled_from(("advisory", "review_read")),
    st.sampled_from(("https://synthetic.invalid/mcp", "https://synthetic.invalid:443/mcp")),
)
def test_valid_registry_profiles_preserve_only_declared_tool_authority(profile, assurance, url):
    document = deepcopy(REGISTRY)
    document["servers"]["docs"]["transport"]["url"] = url
    document["servers"]["docs"]["tools"]["lookup"]["assurance"] = assurance
    admitted = parse_registry(json.dumps(document), profile=profile)
    assert len(admitted.servers) == 1 and len(admitted.servers[0].tools) == 1
    tool = admitted.servers[0].tools[0]
    assert tool.name == "lookup" and tool.assurance == assurance


@given(st.sampled_from(("id", "jsonrpc", "result", "error", "method", "params")), json_values())
def test_seeded_upstream_response_envelopes_parse_or_fail_with_a_closed_error(field, value):
    document = {"jsonrpc": "2.0", "id": 1, "result": {"content": []}}
    document[field] = value
    try:
        frame = parse_frame(json.dumps(document, ensure_ascii=True).encode())
    except FederationError:
        return
    assert frame.message is not None


@given(st.data(), st.tuples(*(st.integers(0, 12) for _ in range(4))), st.booleans())
def test_gateway_reconciliation_conserves_attempts_and_never_upgrades_degraded_runs(
    data, terminal, advisory
):
    seed = _receipt_v11(external=True)["mcp"]["federation"]
    receipt = seed["receipt"]
    alias = next(iter(receipt["tools"]))
    entry = receipt["tools"][alias]
    receipt["tools"] = {alias: entry}
    entry.update({counter: 0 for counter in COUNTERS})
    entry.update(zip(("completed", "denied", "failed", "timed_out"), terminal, strict=True))
    entry["attempted"] = sum(terminal)
    entry["assurance"] = "advisory" if advisory else "review_read"
    rejected = data.draw(st.integers(0, entry["denied"]))
    entry["dlp_rejected"] = rejected
    entry["dlp_gates"]["arguments"]["pii"] = rejected
    entry["oversized"] = data.draw(st.integers(0, entry["denied"] - rejected))
    attempts = data.draw(st.sampled_from((entry["attempted"], entry["attempted"] + 1)))
    reconciled = reconcile(receipt, {alias: attempts}, {alias})
    assert valid_reconciliation(reconciled)
    complete = attempts == entry["attempted"] == entry["completed"] and (
        not attempts or not advisory
    )
    assert (reconciled["state"] == "complete") is complete
    entry["attempted"] += 1
    assert not valid_reconciliation(reconciled)


@given(st.data(), json_values())
def test_hostile_federation_receipt_fields_cannot_bypass_reconciliation(data, value):
    seed = _receipt_v11(external=True)["mcp"]["federation"]
    alias = next(iter(seed["receipt"]["tools"]))
    paths = (
        ("state",),
        ("ocr_attempts",),
        ("ocr_attempts", alias),
        *(("receipt", field) for field in ("schema", "run_id", "state", "cleanup", "tools")),
        *(
            ("receipt", "tools", alias, field)
            for field in (*sorted(COUNTERS), "assurance", "server", "dlp_gates")
        ),
        ("receipt", "tools", alias, "dlp_gates", "arguments", "pii"),
    )
    path = data.draw(st.sampled_from(paths))
    parent = seed
    for part in path[:-1]:
        parent = parent[part]
    parent[path[-1]] = value
    if valid_reconciliation(seed):
        assert reconcile(seed["receipt"], seed["ocr_attempts"], set(seed["ocr_attempts"])) == seed
