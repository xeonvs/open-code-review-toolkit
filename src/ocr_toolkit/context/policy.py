"""Parse exact protected-target review-context policy without repository imports."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Mapping
from typing import Any
from urllib.parse import urlsplit

from ocr_toolkit.context.contracts import (
    ACCOUNT_CLASSES,
    POLICY_SCHEMA,
    PROJECTION_FIELDS,
    RESOURCE_CLASSES,
    RETENTION_FIELDS,
    AggregateBudgets,
    ContextContractError,
    ContextPolicy,
    ContextProjections,
    DiscussionPolicy,
    RecognizerPolicy,
    ReferencePolicy,
    TextBudgets,
)

POLICY_PATH = ".opencodereview/review-context-policy.json"
MAX_POLICY_BYTES = 64 * 1024
MAX_REFERENCES = 16
NAME_RE = re.compile(r"[a-z][a-z0-9_-]{0,63}\Z")
ISSUE_PREFIX_RE = re.compile(r"[A-Z][A-Z0-9]{0,15}\Z")


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContextContractError("context policy contains a duplicate key")
        result[key] = value
    return result


def _object(value: object, *, keys: frozenset[str], label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise ContextContractError(f"{label} must be an object")
    unknown = set(value).difference(keys)
    if unknown:
        raise ContextContractError(f"{label} contains unknown fields")
    return value


def _integer(value: object, *, minimum: int, maximum: int, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not minimum <= value <= maximum:
        raise ContextContractError(f"{label} is outside its closed bound")
    return value


def _boolean(value: object, *, label: str) -> bool:
    if not isinstance(value, bool):
        raise ContextContractError(f"{label} must be boolean")
    return value


def _text_budgets(value: object, *, label: str) -> TextBudgets:
    item = _object(
        value,
        keys=frozenset({"max_chars", "max_bytes", "max_lines"}),
        label=label,
    )
    return TextBudgets(
        max_chars=_integer(item.get("max_chars"), minimum=1, maximum=100_000, label=label),
        max_bytes=_integer(item.get("max_bytes"), minimum=1, maximum=400_000, label=label),
        max_lines=_integer(item.get("max_lines"), minimum=1, maximum=10_000, label=label),
    )


def _projections(value: object, *, label: str) -> ContextProjections:
    item = _object(
        value,
        keys=frozenset({"retrieve", "model", "publish", "retain"}),
        label=label,
    )
    values: dict[str, tuple[str, ...]] = {}
    for name in ("retrieve", "model", "publish", "retain"):
        fields = item.get(name)
        if (
            not isinstance(fields, list)
            or len(fields) > len(PROJECTION_FIELDS)
            or any(not isinstance(field, str) or field not in PROJECTION_FIELDS for field in fields)
            or fields != sorted(set(fields))
        ):
            raise ContextContractError(f"{label}.{name} must be a sorted unique closed list")
        values[name] = tuple(fields)
    retrieved = set(values["retrieve"])
    if any(not set(values[name]).issubset(retrieved) for name in ("model", "publish", "retain")):
        raise ContextContractError(f"{label} later projections must be retrieval subsets")
    if not set(values["retain"]).issubset(RETENTION_FIELDS):
        raise ContextContractError(f"{label}.retain contains non-retainable fields")
    if not values["retrieve"] or not values["model"]:
        raise ContextContractError(f"{label} retrieval and model projections cannot be empty")
    return ContextProjections(**values)


def _discussion(value: object) -> DiscussionPolicy:
    item = _object(
        value,
        keys=frozenset(
            {
                "required",
                "account_classes",
                "include_resolved",
                "include_outdated",
                "max_age_seconds",
                "max_threads",
                "max_replies_per_thread",
                "max_items",
                "budgets",
                "projections",
            }
        ),
        label="forge_discussions",
    )
    classes = item.get("account_classes")
    if (
        not isinstance(classes, list)
        or not classes
        or classes != sorted(set(classes))
        or any(not isinstance(value, str) or value not in ACCOUNT_CLASSES for value in classes)
    ):
        raise ContextContractError("forge_discussions.account_classes is invalid")
    return DiscussionPolicy(
        required=_boolean(item.get("required"), label="forge_discussions.required"),
        account_classes=tuple(classes),
        include_resolved=_boolean(
            item.get("include_resolved"), label="forge_discussions.include_resolved"
        ),
        include_outdated=_boolean(
            item.get("include_outdated"), label="forge_discussions.include_outdated"
        ),
        max_age_seconds=_integer(
            item.get("max_age_seconds"), minimum=0, maximum=31_536_000, label="discussion age"
        ),
        max_threads=_integer(item.get("max_threads"), minimum=1, maximum=100, label="threads"),
        max_replies_per_thread=_integer(
            item.get("max_replies_per_thread"), minimum=1, maximum=100, label="replies"
        ),
        max_items=_integer(item.get("max_items"), minimum=1, maximum=500, label="items"),
        budgets=_text_budgets(item.get("budgets"), label="forge_discussions.budgets"),
        projections=_projections(item.get("projections"), label="forge_discussions.projections"),
    )


def _recognizer(value: object, *, resource_class: str) -> RecognizerPolicy:
    item = _object(
        value,
        keys=frozenset({"type", "prefix", "origin", "path_prefix"}),
        label="reference.recognizer",
    )
    kind = item.get("type")
    if kind == "issue_key":
        prefix = item.get("prefix")
        if (
            resource_class != "issue"
            or not isinstance(prefix, str)
            or ISSUE_PREFIX_RE.fullmatch(prefix) is None
        ):
            raise ContextContractError("issue-key recognizer is invalid")
        if set(item) != {"type", "prefix"}:
            raise ContextContractError("issue-key recognizer contains inapplicable fields")
        return RecognizerPolicy(type=kind, prefix=prefix)
    if kind == "https_url":
        origin, path_prefix = item.get("origin"), item.get("path_prefix")
        if not isinstance(origin, str) or not isinstance(path_prefix, str):
            raise ContextContractError("HTTPS recognizer is invalid")
        try:
            parsed = urlsplit(origin)
            hostname = parsed.hostname
            _port = parsed.port
        except ValueError as exc:
            raise ContextContractError("HTTPS recognizer origin or prefix is unsafe") from exc
        if (
            parsed.scheme != "https"
            or not parsed.netloc
            or hostname is None
            or parsed.netloc.endswith(":")
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
            or not path_prefix.startswith("/")
            or ".." in path_prefix.split("/")
            or len(path_prefix) > 256
        ):
            raise ContextContractError("HTTPS recognizer origin or prefix is unsafe")
        if set(item) != {"type", "origin", "path_prefix"}:
            raise ContextContractError("HTTPS recognizer contains inapplicable fields")
        normalized_origin = f"https://{parsed.netloc.lower()}"
        return RecognizerPolicy(type=kind, origin=normalized_origin, path_prefix=path_prefix)
    if kind == "explicit":
        if set(item) != {"type"}:
            raise ContextContractError("explicit recognizer contains inapplicable fields")
        return RecognizerPolicy(type=kind)
    raise ContextContractError("reference recognizer type is unsupported")


def _reference(value: object) -> ReferencePolicy:
    item = _object(
        value,
        keys=frozenset(
            {
                "adapter",
                "tenant",
                "resource_class",
                "recognizer",
                "required",
                "max_records",
                "max_age_seconds",
                "budgets",
                "projections",
            }
        ),
        label="reference",
    )
    adapter, tenant, resource_class = (
        item.get("adapter"),
        item.get("tenant"),
        item.get("resource_class"),
    )
    if not isinstance(adapter, str) or NAME_RE.fullmatch(adapter) is None:
        raise ContextContractError("reference adapter name is invalid")
    if not isinstance(tenant, str) or NAME_RE.fullmatch(tenant) is None:
        raise ContextContractError("reference tenant alias is invalid")
    if not isinstance(resource_class, str) or resource_class not in RESOURCE_CLASSES:
        raise ContextContractError("reference resource class is invalid")
    return ReferencePolicy(
        adapter=adapter,
        tenant=tenant,
        resource_class=resource_class,
        recognizer=_recognizer(item.get("recognizer"), resource_class=resource_class),
        required=_boolean(item.get("required"), label="reference.required"),
        max_records=_integer(
            item.get("max_records"), minimum=1, maximum=64, label="reference records"
        ),
        max_age_seconds=_integer(
            item.get("max_age_seconds"), minimum=0, maximum=31_536_000, label="reference age"
        ),
        budgets=_text_budgets(item.get("budgets"), label="reference.budgets"),
        projections=_projections(item.get("projections"), label="reference.projections"),
    )


def parse_policy(raw: bytes) -> ContextPolicy:
    """Parse one byte-bounded exact policy and bind its canonical digest."""

    if not raw or len(raw) > MAX_POLICY_BYTES:
        raise ContextContractError("context policy is missing or oversized")
    try:
        text = raw.decode("utf-8", errors="strict")
        payload = json.loads(text, object_pairs_hook=_pairs)
    except UnicodeDecodeError as exc:
        raise ContextContractError("context policy is not valid UTF-8") from exc
    except json.JSONDecodeError as exc:
        raise ContextContractError("context policy is not valid JSON") from exc
    root = _object(
        payload,
        keys=frozenset({"schema_version", "budgets", "forge_discussions", "references"}),
        label="context policy",
    )
    if root.get("schema_version") != POLICY_SCHEMA:
        raise ContextContractError("context policy schema version is unsupported")
    budgets_value = _object(
        root.get("budgets"),
        keys=frozenset({"max_records", "max_chars", "max_bytes", "max_lines", "timeout_ms"}),
        label="budgets",
    )
    budgets = AggregateBudgets(
        max_records=_integer(
            budgets_value.get("max_records"), minimum=1, maximum=128, label="aggregate records"
        ),
        max_chars=_integer(
            budgets_value.get("max_chars"), minimum=1, maximum=500_000, label="aggregate chars"
        ),
        max_bytes=_integer(
            budgets_value.get("max_bytes"), minimum=1, maximum=2_000_000, label="aggregate bytes"
        ),
        max_lines=_integer(
            budgets_value.get("max_lines"), minimum=1, maximum=50_000, label="aggregate lines"
        ),
        timeout_ms=_integer(
            budgets_value.get("timeout_ms"), minimum=100, maximum=120_000, label="aggregate timeout"
        ),
    )
    discussion = _discussion(root["forge_discussions"]) if "forge_discussions" in root else None
    references_value = root.get("references", [])
    if (
        not isinstance(references_value, list)
        or len(references_value) > MAX_REFERENCES
        or any(not isinstance(value, Mapping) for value in references_value)
    ):
        raise ContextContractError("context policy references are invalid")
    references = tuple(_reference(value) for value in references_value)
    identities = [(item.adapter, item.tenant, item.resource_class) for item in references]
    if len(identities) != len(set(identities)):
        raise ContextContractError("context policy references collide")
    if discussion is None and not references:
        raise ContextContractError("context policy must select at least one source")
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return ContextPolicy(
        schema_version=POLICY_SCHEMA,
        budgets=budgets,
        forge_discussions=discussion,
        references=references,
        digest=hashlib.sha256(canonical).hexdigest(),
    )


def load_protected_policy(
    read_blob: Callable[[str, str], bytes],
    *,
    policy_sha: str,
) -> ContextPolicy:
    """Read only the captured protected-target blob through an injected Git owner."""

    if re.fullmatch(r"[0-9a-f]{40,64}", policy_sha) is None:
        raise ContextContractError("protected policy identity is invalid")
    try:
        raw = read_blob(policy_sha, POLICY_PATH)
    except Exception as exc:
        raise ContextContractError("protected context policy is unavailable") from exc
    return parse_policy(raw)
