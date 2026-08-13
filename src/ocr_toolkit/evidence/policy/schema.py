"""Validate exact nested values for structured policy evidence."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date


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
    """Validate one schema-v3 structured policy evidence value."""

    outer = _exact_mapping(value, {"identity", "fact"}, kind)
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
            or not 1 <= len(fact["title"]) <= 256
            or not isinstance(fact["rationale"], str)
            or len(fact["rationale"]) > 64_000
        ):
            raise ValueError("accepted-decision text fields are invalid")
        _strings(fact["scopes"], label="accepted-decision scopes", limit=64, item_limit=512)
        _strings(fact["matched_paths"], label="accepted-decision matched paths", limit=64)
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
        if fact["applicability"] not in {"applicable", "not_applicable"}:
            raise ValueError("guidance applicability is invalid")
        _strings(fact["matched_paths"], label="guidance matched paths", limit=64)
        precedence = _exact_mapping(
            fact["precedence"], {"depth", "path", "document_order"}, "guidance precedence"
        )
        if (
            not isinstance(precedence["depth"], int)
            or isinstance(precedence["depth"], bool)
            or not isinstance(precedence["document_order"], int)
            or isinstance(precedence["document_order"], bool)
            or precedence["path"] != fact["path"]
        ):
            raise ValueError("guidance precedence is invalid")
        return
    raise ValueError(f"unsupported policy record kind: {kind}")
