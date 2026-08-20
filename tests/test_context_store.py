"""Hostile persistence and opaque-handle contracts for the context store."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from ocr_toolkit.context import store as context_store
from ocr_toolkit.context.store import ContextStore, ContextStoreError, PendingContextRecord

RUN_ID = "synthetic_run_0001"
POLICY_DIGEST = "a" * 64


def pending(
    *, canonical_object: str = "private-object-1", expiry: int = 200
) -> PendingContextRecord:
    text = "Synthetic admitted issue context."
    return PendingContextRecord(
        source="reference:tracker",
        adapter="tracker",
        tenant="engineering",
        canonical_object=canonical_object,
        resource_class="issue",
        descriptor="issue",
        projections={
            "model": {"descriptor": "issue", "text": text},
            "publish": {"descriptor": "issue"},
            "retain": {
                "digest": hashlib.sha256(text.encode()).hexdigest(),
                "expiry": expiry,
                "state": "admitted",
                "version": "v1",
            },
        },
        version="v1",
        digest=hashlib.sha256(text.encode()).hexdigest(),
        mutable=True,
        expiry=expiry,
    )


def commit(path: Path, **kwargs: object) -> ContextStore:
    parameters = {
        "run_id": RUN_ID,
        "policy_digest": POLICY_DIGEST,
        "completeness": {"reference:tracker": "complete"},
        "records": [pending()],
        "created_at": 100,
        "expiry": 200,
        "token_bytes": lambda size: b"x" * size,
    }
    parameters.update(kwargs)
    return ContextStore.commit(path, **parameters)  # type: ignore[arg-type]


def rewrite_hostile_store(path: Path, payload: dict[str, object]) -> None:
    body = dict(payload)
    body.pop("digest", None)
    payload["digest"] = hashlib.sha256(
        (
            json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
        ).encode()
    ).hexdigest()
    path.write_text(json.dumps(payload), encoding="utf-8")
    os.chmod(path, 0o600)


def test_context_store_commits_owner_only_and_resolves_only_minted_handle(tmp_path: Path) -> None:
    path = tmp_path / "context-store.json"
    store = commit(path)
    handle = store.records[0].handle

    assert handle == "ctx1_eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHg"
    assert path.stat().st_mode & 0o777 == 0o600
    assert store.get(handle, run_id=RUN_ID, policy_digest=POLICY_DIGEST, now=150).descriptor == (
        "issue"
    )
    for wrong in ("DEMO-1", "https://example.invalid/1", "ctx1_short"):
        with pytest.raises(ContextStoreError, match="unavailable"):
            store.get(wrong, run_id=RUN_ID, policy_digest=POLICY_DIGEST, now=150)


def test_context_store_rejects_wrong_run_policy_expiry_and_replay(tmp_path: Path) -> None:
    path = tmp_path / "context-store.json"
    store = commit(path)
    handle = store.records[0].handle

    with pytest.raises(ContextStoreError, match="unavailable"):
        store.get(handle, run_id="different_run_001", policy_digest=POLICY_DIGEST, now=150)
    with pytest.raises(ContextStoreError, match="unavailable"):
        store.get(handle, run_id=RUN_ID, policy_digest="b" * 64, now=150)
    with pytest.raises(ContextStoreError, match="unavailable"):
        store.get(handle, run_id=RUN_ID, policy_digest=POLICY_DIGEST, now=200)
    with pytest.raises(ContextStoreError, match="expired"):
        ContextStore.read(
            path,
            expected_run_id=RUN_ID,
            expected_policy_digest=POLICY_DIGEST,
            now=200,
        )
    with pytest.raises(ContextStoreError, match="identity"):
        ContextStore.read(
            path,
            expected_run_id="different_run_001",
            expected_policy_digest=POLICY_DIGEST,
            now=150,
        )

    with pytest.raises(ContextStoreError, match="lifetime"):
        commit(path, expiry=100 + 86_401, records=[pending(expiry=100 + 86_401)])


def test_context_store_rejects_collisions_before_replacing_existing_store(tmp_path: Path) -> None:
    path = tmp_path / "context-store.json"
    original = commit(path)
    original_bytes = path.read_bytes()

    with pytest.raises(ContextStoreError, match="records collide"):
        commit(path, records=[pending(), pending()])
    assert path.read_bytes() == original_bytes
    assert original.records[0].handle

    invalid_projection = pending(canonical_object="private-object-3")
    assert isinstance(invalid_projection.projections["model"], dict)
    invalid_projection.projections["model"]["upstream_id"] = "must-not-survive"
    with pytest.raises(ContextStoreError, match="projection fields"):
        commit(path, records=[invalid_projection])
    assert path.read_bytes() == original_bytes

    with pytest.raises(ContextStoreError, match="record lifetime"):
        commit(path, records=[pending(expiry=100)])
    assert path.read_bytes() == original_bytes

    with pytest.raises(ContextStoreError, match="record lifetime"):
        commit(path, records=[pending(expiry=201)])
    assert path.read_bytes() == original_bytes

    with pytest.raises(ContextStoreError, match="entropy collided"):
        commit(
            path,
            records=[pending(), pending(canonical_object="private-object-2")],
            token_bytes=lambda size: b"z" * size,
        )
    assert path.read_bytes() == original_bytes


def test_context_store_rejects_symlink_hardlink_and_hostile_replace(tmp_path: Path) -> None:
    path = tmp_path / "context-store.json"
    commit(path)

    link = tmp_path / "store-link.json"
    link.symlink_to(path)
    with pytest.raises(ContextStoreError, match="metadata"):
        ContextStore.read(
            link,
            expected_run_id=RUN_ID,
            expected_policy_digest=POLICY_DIGEST,
            now=150,
        )

    hardlink = tmp_path / "store-hardlink.json"
    os.link(path, hardlink)
    with pytest.raises(ContextStoreError, match="metadata"):
        ContextStore.read(
            path,
            expected_run_id=RUN_ID,
            expected_policy_digest=POLICY_DIGEST,
            now=150,
        )
    hardlink.unlink()

    path.write_text('{"schema_version":"ocr.context-store/v1"}', encoding="utf-8")
    os.chmod(path, 0o600)
    with pytest.raises(ContextStoreError):
        ContextStore.read(
            path,
            expected_run_id=RUN_ID,
            expected_policy_digest=POLICY_DIGEST,
            now=150,
        )


def test_context_store_rejects_digest_mismatch_duplicate_keys_and_unsafe_mode(
    tmp_path: Path,
) -> None:
    path = tmp_path / "context-store.json"
    commit(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["records"][0]["descriptor"] = "changed"
    path.write_text(json.dumps(payload), encoding="utf-8")
    os.chmod(path, 0o600)
    with pytest.raises(ContextStoreError, match="digest"):
        ContextStore.read(
            path,
            expected_run_id=RUN_ID,
            expected_policy_digest=POLICY_DIGEST,
            now=150,
        )

    path.write_text('{"run_id":"one","run_id":"two"}', encoding="utf-8")
    os.chmod(path, 0o600)
    with pytest.raises(ContextStoreError, match="duplicate"):
        ContextStore.read(
            path,
            expected_run_id=RUN_ID,
            expected_policy_digest=POLICY_DIGEST,
            now=150,
        )

    commit(path)
    os.chmod(path, 0o644)
    with pytest.raises(ContextStoreError, match="metadata"):
        ContextStore.read(
            path,
            expected_run_id=RUN_ID,
            expected_policy_digest=POLICY_DIGEST,
            now=150,
        )


def test_context_store_rejects_recursive_json_as_closed_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "context-store.json"
    path.write_text("[" * 2_000 + "0" + "]" * 2_000, encoding="utf-8")
    os.chmod(path, 0o600)

    with pytest.raises(ContextStoreError):
        ContextStore.read(
            path,
            expected_run_id=RUN_ID,
            expected_policy_digest=POLICY_DIGEST,
            now=150,
        )

    commit(path)
    monkeypatch.setattr(
        context_store.json,
        "loads",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RecursionError()),
    )
    with pytest.raises(ContextStoreError, match="malformed"):
        ContextStore.read(
            path,
            expected_run_id=RUN_ID,
            expected_policy_digest=POLICY_DIGEST,
            now=150,
        )


def test_context_store_atomic_setup_failure_closes_descriptor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    descriptors: list[int] = []

    def fail_fchmod(descriptor: int, _mode: int) -> None:
        descriptors.append(descriptor)
        raise OSError("synthetic fchmod failure")

    monkeypatch.setattr(context_store.os, "fchmod", fail_fchmod)
    with pytest.raises(OSError, match="synthetic fchmod"):
        context_store._atomic_write(tmp_path / "context-store.json", b"{}\n")

    assert len(descriptors) == 1
    with pytest.raises(OSError):
        os.fstat(descriptors[0])


def test_context_store_hostile_read_revalidates_projection_semantics(tmp_path: Path) -> None:
    path = tmp_path / "context-store.json"
    mutations = (
        lambda record: record["projections"]["model"].update(  # type: ignore[index,union-attr]
            {"text": {"nested": "must-not-reach-model"}}
        ),
        lambda record: record["projections"]["model"].update(  # type: ignore[index,union-attr]
            {"text": "synthetic@example.invalid"}
        ),
        lambda record: record["projections"]["retain"].update(  # type: ignore[index,union-attr]
            {"expiry": 199}
        ),
        lambda record: record.update({"descriptor": "issue\u200b"}),
    )
    for mutate in mutations:
        commit(path)
        payload = json.loads(path.read_text(encoding="utf-8"))
        record = payload["records"][0]
        mutate(record)
        rewrite_hostile_store(path, payload)
        with pytest.raises(ContextStoreError, match=r"projection|identity"):
            ContextStore.read(
                path,
                expected_run_id=RUN_ID,
                expected_policy_digest=POLICY_DIGEST,
                now=150,
            )
