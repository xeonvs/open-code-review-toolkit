"""Small provider-neutral policy for outbound forge API request identity."""

from collections.abc import Mapping

DEFAULT_FORGE_API_USER_AGENT = "open-code-review-toolkit-provider/1"
FORGE_API_USER_AGENT_VARIABLE = "OCR_FORGE_API_USER_AGENT"
_UNSET = object()


def resolve_forge_api_user_agent(environment: Mapping[str, str]) -> str:
    """Resolve a bounded printable ASCII agent without exposing invalid input."""

    value = environment.get(FORGE_API_USER_AGENT_VARIABLE, _UNSET)
    if value is _UNSET:
        return DEFAULT_FORGE_API_USER_AGENT
    if (
        not isinstance(value, str)
        or not 1 <= len(value) <= 256
        or any(not 32 <= ord(character) <= 126 for character in value)
        or not value.strip()
    ):
        raise ValueError(
            f"{FORGE_API_USER_AGENT_VARIABLE} must be nonblank printable ASCII (1-256 bytes)"
        )
    return value
