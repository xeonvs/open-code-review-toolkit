"""Finite local execution settings, independent of scanner comparison identity."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .state import AuditError, fields

MAX_HITS = 80_000
MAX_HIT_BYTES = 24_000_000


@dataclass(frozen=True, slots=True)
class ExecutionLimits:
    """Allow slow hosts more time without increasing input or retained-output bounds."""

    seconds: int = 900
    file_seconds: int = 60
    git_seconds: int = 120

    def __post_init__(self) -> None:
        for name, maximum in (("seconds", 86_400), ("file_seconds", 3600), ("git_seconds", 3600)):
            value = getattr(self, name)
            if type(value) is not int or not 1 <= value <= maximum:
                raise AuditError("invalid execution budget")

    def record(self) -> dict[str, int]:
        return {**asdict(self), "workers": 1}

    @classmethod
    def parse(cls, value: Any) -> ExecutionLimits:
        fields(value, {"seconds", "file_seconds", "git_seconds", "workers"})
        if type(value["workers"]) is not int or value["workers"] != 1:
            raise AuditError("invalid worker population")
        return cls(**{key: value[key] for key in ("seconds", "file_seconds", "git_seconds")})
