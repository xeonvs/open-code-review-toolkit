"""Admission of the model selected by the native review for public telemetry."""

import re

from ocr_toolkit.context.contracts import TextBudgets
from ocr_toolkit.context.dlp import ForbiddenValue, check_text

_MODEL_SLUG = re.compile(
    r"(?:[A-Za-z0-9][A-Za-z0-9_-]*/)?"
    r"[A-Za-z0-9][A-Za-z0-9_-]*(?:\.[A-Za-z0-9_-]+)*"
    r"(?::[A-Za-z0-9][A-Za-z0-9._-]*)?"
)
_CREDENTIAL = re.compile(
    r"(?:^|/)(?:sk-|gh[pousr]_|github_pat_|glpat-|xox[baprs]-|AKIA|ASIA|AIza|hf_)"
    r"|(?:^|[/._:-])(?:private|secret|password|credential|token)(?:$|[/._:-])"
    r"|(?:^|/)[a-f0-9]{32,}(?:$|:)"
    r"|(?:^|/)eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"
    r"|^(?:https?|file|ssh|ftp|mailto|data|javascript):",
    re.IGNORECASE,
)


def model_slug(value: object) -> bool:
    """Recognize the exact bounded public identifier grammar."""
    return (
        isinstance(value, str)
        and len(value) <= 128
        and _MODEL_SLUG.fullmatch(value) is not None
        and not _CREDENTIAL.search(value)
    )


def admitted_model(
    value: object, *, forbidden: tuple[str | ForbiddenValue, ...] = ()
) -> str | None:
    """Omit private context, credentials and model IDs changed by text admission."""
    if not isinstance(value, str) or not model_slug(value):
        return None
    checked = check_text(
        value, budgets=TextBudgets(128, 128, 1), forbidden=forbidden, publication=True, enabled=True
    )
    return value if checked.admitted and checked.text == value else None
