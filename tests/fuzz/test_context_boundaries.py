"""Opaque handle isolation, cursor bindings and atomic hostile context readback."""

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ocr_toolkit.context.mcp import ContextMCPError, _cursor, _offset, call_context_tool
from ocr_toolkit.context.store import ContextStore, ContextStoreError
from tests.fuzz.strategies import json_values
from tests.test_context_store import (
    POLICY_DIGEST,
    RUN_ID,
    ci_pending,
    commit,
    pending,
    remediation_pending,
)


@given(st.integers(1, 8), st.integers(100, 199))
def test_valid_context_records_round_trip_with_unique_handles_and_current_lifetime(count, now):
    with TemporaryDirectory(prefix="ocr-context-roundtrip-") as directory:
        target = Path(directory) / "context.json"
        counter = iter(range(1, count + 1))
        stored = commit(
            target,
            records=[pending(canonical_object=f"synthetic-{index}") for index in range(count)],
            token_bytes=lambda size: next(counter).to_bytes(size, "big"),
        )
        loaded = ContextStore.read(
            target, expected_run_id=RUN_ID, expected_policy_digest=POLICY_DIGEST, now=now
        )
        assert (
            loaded.records == stored.records
            and len({record.handle for record in loaded.records}) == count
        )
        assert all(
            loaded.get(record.handle, run_id=RUN_ID, policy_digest=POLICY_DIGEST, now=now) == record
            for record in loaded.records
        )


@given(st.sampled_from(("valid", "run", "policy", "handle", "before", "expired")))
def test_minted_handles_cannot_cross_run_policy_or_lifetime(binding) -> None:
    with TemporaryDirectory(prefix="ocr-context-handles-") as directory:
        store = commit(Path(directory) / "context.json")
        handle = store.records[0].handle
        if binding == "handle":
            handle = handle[:5] + ("A" if handle[5] != "A" else "B") + handle[6:]
        parameters = {
            "run_id": RUN_ID if binding != "run" else "different_run",
            "policy_digest": POLICY_DIGEST if binding != "policy" else "b" * 64,
            "now": 99 if binding == "before" else 200 if binding == "expired" else 150,
        }
        if binding == "valid":
            assert store.get(handle, **parameters) == store.records[0]
        else:
            with pytest.raises(ContextStoreError):
                store.get(handle, **parameters)


@given(st.integers(0, 1000), st.binary(min_size=8, max_size=8), st.binary(min_size=8, max_size=8))
def test_cursors_round_trip_and_cannot_cross_query_or_record_set(offset, query, records) -> None:
    query_key, records_key = query.hex(), records.hex()
    cursor = _cursor(offset, query_key, records_key)
    assert _offset(cursor, query_key, records_key) == offset
    for other_query, other_records in (("different", records_key), (query_key, "different")):
        with pytest.raises(ContextMCPError):
            _offset(cursor, other_query, other_records)


@given(st.sampled_from(("context_list", "context_get")), json_values())
def test_malformed_context_tool_arguments_have_a_closed_error(name, arguments) -> None:
    with TemporaryDirectory(prefix="ocr-context-mcp-") as directory:
        store = commit(Path(directory) / "context.json")
        try:
            response = call_context_tool(store, name, arguments, now=150)
        except ContextMCPError:
            return
        assert json.loads(response["content"][0]["text"])


FIELDS = (
    ("schema_version",),
    ("completeness",),
    ("created_at",),
    ("expiry",),
    ("records",),
    *(
        ("records", 0, field)
        for field in (
            "handle",
            "source",
            "resource_class",
            "descriptor",
            "mutable",
            "expiry",
            "projections",
        )
    ),
    ("records", 0, "projections", "model"),
)


CI_FIELDS = tuple(
    ("records", 0, "projections", "model", "ci_outcome", field)
    for field in ("status", "revision", "check", "requirement", "scope", "origin", "completed_at")
)
REMEDIATION_FIELDS = (
    *(
        ("records", 0, "projections", "model", "remediation_thread", field)
        for field in ("anchor_state", "completeness", "replies", "counts")
    ),
    *(
        ("records", 0, "projections", "model", "remediation_thread", "replies", 0, field)
        for field in ("author_class", "text", "order", "created_at", "updated_at")
    ),
)


@given(st.data(), json_values(), st.sampled_from(("issue", "remediation", "ci")))
def test_context_readback_validates_hostile_fields_even_with_recomputed_digest(
    data, value, kind
) -> None:
    path = data.draw(
        st.sampled_from(
            FIELDS
            + (
                CI_FIELDS
                if kind == "ci"
                else REMEDIATION_FIELDS
                if kind == "remediation"
                else (("records", 0, "projections", "model", "text"),)
            )
        )
    )
    with TemporaryDirectory(prefix="ocr-context-readback-") as directory:
        target = Path(directory) / "context.json"
        options = (
            {}
            if kind == "issue"
            else {"records": [ci_pending() if kind == "ci" else remediation_pending()]}
        )
        commit(target, **options)
        document = json.loads(target.read_text())
        parent = document
        for part in path[:-1]:
            parent = parent[part]
        parent[path[-1]] = value
        body = {key: item for key, item in document.items() if key != "digest"}
        try:
            canonical = (
                json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
            ).encode()
        except UnicodeError:
            document["digest"] = "0" * 64
        else:
            document["digest"] = hashlib.sha256(canonical).hexdigest()
        target.write_text(json.dumps(document, ensure_ascii=True))
        try:
            loaded = ContextStore.read(
                target, expected_run_id=RUN_ID, expected_policy_digest=POLICY_DIGEST, now=150
            )
        except ContextStoreError:
            return
        assert loaded.run_id == RUN_ID and loaded.policy_digest == POLICY_DIGEST
        assert all(record.expiry <= loaded.expiry for record in loaded.records)
