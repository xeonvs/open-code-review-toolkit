"""Validate exact nested values for structured policy evidence."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date

from ocr_toolkit.evidence.policy.contracts import (
    MAX_DECISION_TITLE_CHARS,
    MAX_POLICY_VALUE_BYTES,
    MAX_RATIONALE_CHARS,
    policy_value_within_budget,
)
from ocr_toolkit.evidence.policy.guidance import guidance_applicability, guidance_metadata
from ocr_toolkit.evidence.policy.scopes import (
    is_safe_repository_path,
    matches_scope,
    validate_scope,
)


def _exact_mapping(value: object, keys: set[str], label: str) -> Mapping[str, object]:
    """Require one exact mapping shape without extension fields."""

    if not isinstance(value, Mapping) or set(value) != keys:
        raise ValueError(f"{label} fields are invalid")
    return value


def _strings(value: object, *, label: str, limit: int, item_limit: int = 4096) -> None:
    """Validate a bounded string array."""

    if (
        not isinstance(value, (list, tuple))
        or len(value) > limit
        or not all(isinstance(item, str) and len(item) <= item_limit for item in value)
    ):
        raise ValueError(f"{label} must be a bounded string array")


def is_legacy_policy_value(value: object) -> bool:
    """Recognize the exact text-only shape used by schema-v1/v2 stores."""

    return isinstance(value, Mapping) and set(value) == {"text"} and isinstance(value["text"], str)


def validate_policy_record(kind: str, value: object) -> None:
    """Validate one structured policy evidence value."""

    outer = _exact_mapping(value, {"identity", "fact"}, kind)
    if not policy_value_within_budget(outer):
        raise ValueError(f"{kind} exceeds the {MAX_POLICY_VALUE_BYTES}-byte policy budget")
    if not isinstance(outer["identity"], str) or not outer["identity"]:
        raise ValueError(f"{kind} identity is invalid")
    if kind == "repository.accepted_decision":
        fact = _exact_mapping(
            outer["fact"],
            {
                "schema_version",
                "decision_id",
                "title",
                "rationale",
                "scopes",
                "category",
                "owner",
                "review_after",
                "stale",
                "applicability",
                "matched_paths",
            },
            kind,
        )
        if fact["schema_version"] != "repository.accepted-decision/v2":
            raise ValueError("accepted-decision schema version is invalid")
        if fact["decision_id"] != outer["identity"]:
            raise ValueError("accepted-decision identity is inconsistent")
        if (
            not isinstance(fact["title"], str)
            or not 1 <= len(fact["title"]) <= MAX_DECISION_TITLE_CHARS
            or not isinstance(fact["rationale"], str)
            or len(fact["rationale"]) > MAX_RATIONALE_CHARS
        ):
            raise ValueError("accepted-decision text fields are invalid")
        _strings(fact["scopes"], label="accepted-decision scopes", limit=64, item_limit=512)
        _strings(fact["matched_paths"], label="accepted-decision matched paths", limit=64)
        scopes = tuple(fact["scopes"])
        matched_paths = tuple(fact["matched_paths"])
        if not all(is_safe_repository_path(path) for path in matched_paths):
            raise ValueError("accepted-decision matched path is invalid")
        for scope in scopes:
            validate_scope(scope)
        if scopes and any(
            not any(matches_scope(scope, path) for scope in scopes) for path in matched_paths
        ):
            raise ValueError("accepted-decision matched path is outside its scopes")
        if fact["applicability"] in {"invalid", "not_applicable"} and matched_paths:
            raise ValueError("inapplicable accepted decision cannot contain matched paths")
        if fact["applicability"] == "applicable" and scopes and not matched_paths:
            raise ValueError("scoped applicable decision must contain a matched path")
        for key in ("category", "owner"):
            if fact[key] is not None and (
                not isinstance(fact[key], str) or not 1 <= len(fact[key]) <= 512
            ):
                raise ValueError(f"accepted-decision {key} is invalid")
        review_after = fact["review_after"]
        if review_after is not None and (
            not isinstance(review_after, str)
            or date.fromisoformat(review_after).isoformat() != review_after
        ):
            raise ValueError("accepted-decision review_after is invalid")
        if not isinstance(fact["stale"], bool) or fact["applicability"] not in {
            "applicable",
            "not_applicable",
            "invalid",
        }:
            raise ValueError("accepted-decision state is invalid")
        return
    if kind == "repository.guidance":
        fact = _exact_mapping(
            outer["fact"],
            {
                "schema_version",
                "path",
                "document_type",
                "scope",
                "text",
                "applicability",
                "matched_paths",
                "precedence",
            },
            kind,
        )
        if fact["schema_version"] != "repository.guidance/v2" or fact["path"] != outer["identity"]:
            raise ValueError("guidance identity or schema is invalid")
        if not all(
            isinstance(fact[key], str) for key in ("path", "document_type", "scope", "text")
        ) or any(
            len(fact[key]) > limit
            for key, limit in (
                ("path", 4096),
                ("document_type", 64),
                ("scope", 4096),
                ("text", 64_000),
            )
        ):
            raise ValueError("guidance text fields are invalid")
        try:
            document_type, scope, depth, document_order = guidance_metadata(fact["path"])
        except ValueError as exc:
            raise ValueError("guidance path is invalid") from exc
        if fact["document_type"] != document_type or fact["scope"] != scope:
            raise ValueError("guidance document type or scope is inconsistent")
        if fact["applicability"] not in {"applicable", "not_applicable"}:
            raise ValueError("guidance applicability is invalid")
        _strings(fact["matched_paths"], label="guidance matched paths", limit=64)
        matched_paths = tuple(fact["matched_paths"])  # type: ignore[arg-type]
        if not all(is_safe_repository_path(path) for path in matched_paths):
            raise ValueError("guidance matched path is invalid")
        if any(not matches_scope(scope, path) for path in matched_paths):
            raise ValueError("guidance matched path is outside its scope")
        if fact["applicability"] == "not_applicable" and matched_paths:
            raise ValueError("inapplicable guidance cannot contain matched paths")
        if fact["applicability"] == "applicable" and not matched_paths:
            expected_empty_state, _ = guidance_applicability(fact["path"], ())
            if expected_empty_state != "applicable":
                raise ValueError("applicable guidance must contain a matched path")
        precedence = _exact_mapping(
            fact["precedence"], {"depth", "path", "document_order"}, "guidance precedence"
        )
        if (
            not isinstance(precedence["depth"], int)
            or isinstance(precedence["depth"], bool)
            or not isinstance(precedence["document_order"], int)
            or isinstance(precedence["document_order"], bool)
            or precedence["depth"] != depth
            or precedence["document_order"] != document_order
            or precedence["path"] != fact["path"]
        ):
            raise ValueError("guidance precedence is invalid")
        return
    raise ValueError(f"unsupported policy record kind: {kind}")


def validate_policy_applicability(kind: str, value: object, changed_paths: tuple[str, ...]) -> None:
    """Bind persisted applicability to the exact changed-path snapshot identity."""

    outer = _exact_mapping(value, {"identity", "fact"}, kind)
    fact = outer["fact"]
    if not isinstance(fact, Mapping):
        raise ValueError(f"{kind} fact is invalid")
    applicability = fact.get("applicability")
    matched_paths = tuple(fact.get("matched_paths", ()))
    if kind == "repository.guidance":
        path = fact.get("path")
        if not isinstance(path, str):
            raise ValueError("guidance path is invalid")
        expected_state, expected_paths = guidance_applicability(path, changed_paths)
    elif kind == "repository.accepted_decision":
        if applicability == "invalid":
            if matched_paths:
                raise ValueError("invalid accepted decision cannot contain matched paths")
            return
        scopes = tuple(fact.get("scopes", ()))
        expected_paths = tuple(
            path
            for path in changed_paths
            if not scopes or any(matches_scope(scope, path) for scope in scopes)
        )[:64]
        expected_state = (
            "applicable"
            if expected_paths or (not scopes and not changed_paths)
            else "not_applicable"
        )
    else:
        raise ValueError(f"unsupported policy record kind: {kind}")
    if applicability != expected_state or matched_paths != expected_paths:
        raise ValueError(f"{kind} applicability does not match the loaded snapshots")
