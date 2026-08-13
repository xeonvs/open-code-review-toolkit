"""Expose the closed static policy provider registry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class PolicyProvider:
    """Declare one pure built-in policy provider without dynamic discovery."""

    name: str
    kind: Literal["repository.accepted_decision", "repository.guidance"]


POLICY_PROVIDERS = (
    PolicyProvider("accepted-decisions", "repository.accepted_decision"),
    PolicyProvider("project-guidance", "repository.guidance"),
)
