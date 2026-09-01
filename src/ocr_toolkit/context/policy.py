"""Parse exact protected-target review-context policy without repository imports."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Callable, Mapping
from pathlib import PurePosixPath
from typing import Any
from urllib.parse import urlsplit

from ocr_toolkit.context.contracts import (
    ACCOUNT_CLASSES,
    POLICY_SCHEMA_V1,
    POLICY_SCHEMA_V2,
    POLICY_SCHEMAS,
    PROJECTION_FIELDS,
    REFERENCE_RESOURCE_CLASSES,
    RETENTION_FIELDS,
    AggregateBudgets,
    CIOutcomeCheckPolicy,
    CIOutcomePolicy,
    ContextContractError,
    ContextPolicy,
    ContextProjections,
    DiscussionPolicy,
    RecognizerPolicy,
    ReferencePolicy,
    RemediationThreadPolicy,
    TextBudgets,
)

POLICY_PATH = ".opencodereview/review-context-policy.json"
MAX_POLICY_BYTES = 64 * 1024
MAX_REFERENCES = 16
NAME_RE = re.compile(r"[a-z][a-z0-9_-]{0,63}\Z")
ISSUE_PREFIX_RE = re.compile(r"[A-Z][A-Z0-9]{0,15}\Z")
MAX_CI_CHECKS = 32


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
        or any(not isinstance(value, str) or value not in ACCOUNT_CLASSES for value in classes)
        or classes != sorted(set(classes))
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


def _remediation_threads(value: object) -> RemediationThreadPolicy:
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
            }
        ),
        label="remediation_threads",
    )
    classes = item.get("account_classes")
    if (
        not isinstance(classes, list)
        or not classes
        or any(not isinstance(value, str) or value not in ACCOUNT_CLASSES for value in classes)
        or classes != sorted(set(classes))
        or "toolkit_bot" in classes
    ):
        raise ContextContractError("remediation_threads.account_classes is invalid")
    return RemediationThreadPolicy(
        required=_boolean(item.get("required"), label="remediation_threads.required"),
        account_classes=tuple(classes),
        include_resolved=_boolean(
            item.get("include_resolved"), label="remediation_threads.include_resolved"
        ),
        include_outdated=_boolean(
            item.get("include_outdated"), label="remediation_threads.include_outdated"
        ),
        max_age_seconds=_integer(
            item.get("max_age_seconds"), minimum=0, maximum=31_536_000, label="remediation age"
        ),
        max_threads=_integer(
            item.get("max_threads"), minimum=1, maximum=100, label="remediation threads"
        ),
        max_replies_per_thread=_integer(
            item.get("max_replies_per_thread"),
            minimum=1,
            maximum=100,
            label="remediation replies",
        ),
        max_items=_integer(
            item.get("max_items"), minimum=2, maximum=500, label="remediation items"
        ),
        budgets=_text_budgets(item.get("budgets"), label="remediation_threads.budgets"),
    )


def normalize_ci_path_prefix(value: object) -> str:
    """Validate one protected repository-relative POSIX path prefix."""

    if (
        not isinstance(value, str)
        or not 1 <= len(value) <= 256
        or "\\" in value
        or "://" in value
        or any(unicodedata.category(character) in {"Cc", "Cf", "Cs"} for character in value)
        or len(value.encode("utf-8")) > 1_024
    ):
        raise ContextContractError("ci_outcomes path prefix is invalid")
    trailing = value.endswith("/")
    path = PurePosixPath(value)
    parts = value.rstrip("/").split("/")
    if path.is_absolute() or any(part in {"", ".", ".."} for part in parts):
        raise ContextContractError("ci_outcomes path prefix is invalid")
    normalized = path.as_posix()
    return f"{normalized}/" if trailing else normalized


def _ci_outcomes(value: object) -> CIOutcomePolicy:
    """Parse exact check names and path scopes from protected policy v3."""

    item = _object(
        value,
        keys=frozenset({"required", "max_age_seconds", "checks"}),
        label="ci_outcomes",
    )
    checks = item.get("checks")
    if not isinstance(checks, list) or not checks or len(checks) > MAX_CI_CHECKS:
        raise ContextContractError("ci_outcomes.checks is invalid")
    parsed: list[CIOutcomeCheckPolicy] = []
    for raw in checks:
        check = _object(
            raw,
            keys=frozenset({"name", "path_prefixes"}),
            label="ci_outcomes check",
        )
        name = check.get("name")
        prefixes = check.get("path_prefixes")
        if (
            not isinstance(name, str)
            or not 1 <= len(name) <= 128
            or "://" in name
            or any(unicodedata.category(character) in {"Cc", "Cf", "Cs"} for character in name)
            or len(name.encode("utf-8")) > 512
            or not isinstance(prefixes, list)
            or not prefixes
            or len(prefixes) > 32
        ):
            raise ContextContractError("ci_outcomes check is invalid")
        normalized = tuple(normalize_ci_path_prefix(prefix) for prefix in prefixes)
        if list(normalized) != sorted(set(normalized)):
            raise ContextContractError("ci_outcomes path prefixes must be sorted and unique")
        parsed.append(CIOutcomeCheckPolicy(name=name, path_prefixes=normalized))
    names = [check.name for check in parsed]
    if names != sorted(set(names)):
        raise ContextContractError("ci_outcomes check names must be sorted and unique")
    required = item.get("required", False)
    max_age_seconds = item.get("max_age_seconds", 86_400)
    return CIOutcomePolicy(
        required=_boolean(required, label="ci_outcomes.required"),
        max_age_seconds=_integer(
            max_age_seconds,
            minimum=60,
            maximum=604_800,
            label="ci_outcomes.max_age_seconds",
        ),
        checks=tuple(parsed),
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
    if not isinstance(resource_class, str) or resource_class not in REFERENCE_RESOURCE_CLASSES:
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
        keys=frozenset(
            {
                "schema_version",
                "budgets",
                "forge_discussions",
                "remediation_threads",
                "ci_outcomes",
                "references",
            }
        ),
        label="context policy",
    )
    schema_version = root.get("schema_version")
    if not isinstance(schema_version, str) or schema_version not in POLICY_SCHEMAS:
        raise ContextContractError("context policy schema version is unsupported")
    if schema_version == POLICY_SCHEMA_V1 and "remediation_threads" in root:
        raise ContextContractError("context policy v1 cannot select remediation threads")
    if schema_version in {POLICY_SCHEMA_V1, POLICY_SCHEMA_V2} and "ci_outcomes" in root:
        raise ContextContractError("context policy v1/v2 cannot select CI outcomes")
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
    remediation = (
        _remediation_threads(root["remediation_threads"]) if "remediation_threads" in root else None
    )
    ci_outcomes = _ci_outcomes(root["ci_outcomes"]) if "ci_outcomes" in root else None
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
    if discussion is None and remediation is None and ci_outcomes is None and not references:
        raise ContextContractError("context policy must select at least one source")
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return ContextPolicy(
        schema_version=str(schema_version),
        budgets=budgets,
        forge_discussions=discussion,
        remediation_threads=remediation,
        ci_outcomes=ci_outcomes,
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
