"""Resolve the exact GitLab bot and project observation scope."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

from ocr_toolkit.review_model import admitted_model

from ..links import project_path
from .facts import actor, identity, timestamp
from .transport import CollectionError, GitLabClient, RequestError, RequestTimeout, ResponseError

MAX_PROJECTS = 100
BOT = re.compile(r"[A-Za-z0-9_.-]{1,128}")
MODEL_VARIABLE = "OCR_LLM_MODEL"


def _project(client: GitLabClient, selector: str) -> dict[str, Any]:
    """Verify the returned project against its requested numeric or path identity."""

    if not re.fullmatch(r"[1-9][0-9]{0,18}", selector) and project_path(selector) is None:
        raise CollectionError("Specify a GitLab project ID or namespace/project path.")
    payload = client.get(f"projects/{quote(selector, safe='')}")
    project_id = identity(payload.get("id")) if isinstance(payload, dict) else None
    path = project_path(payload.get("path_with_namespace")) if isinstance(payload, dict) else None
    if (
        project_id is None
        or path is None
        or (
            str(project_id) != selector
            if selector.isdecimal()
            else path.casefold() != selector.casefold()
        )
        or type(payload.get("archived")) is not bool
    ):
        raise CollectionError("Cannot verify a project in the selected GitLab scope.")
    return {
        "id": project_id,
        "name": path,
        "path": path,
        "archived": payload["archived"],
        "web_url": client.web_url(payload.get("web_url"), path),
        "access": "complete",
    }


def resolve_bot(client: GitLabClient, username: str) -> int:
    """Resolve an exact selected account on the bound GitLab host."""

    if BOT.fullmatch(username) is None:
        raise CollectionError("Specify a GitLab bot username.")
    users = client.pages("users", query={"username": username})
    matches = [actor(user) for user in users if user.get("username") == username]
    if len(matches) != 1 or (user_id := matches[0]) is None:
        raise CollectionError("Cannot verify the selected GitLab bot account.")
    return user_id


def current_project_model(client: GitLabClient, project_id: int) -> tuple[str | None, str | None]:
    """Read only the visible, unprotected wildcard project model for cost estimates."""

    try:
        response = client.get(
            f"projects/{project_id}/variables/{MODEL_VARIABLE}",
            query={"filter[environment_scope]": "*"},
        )
    except (RequestTimeout, ResponseError):
        return None, None
    except RequestError as exc:
        if (
            exc.status is None
            or exc.status in {400, 401, 403, 404, 409, 429}
            or 500 <= exc.status <= 599
        ):
            return None, None
        raise
    if (
        not isinstance(response, dict)
        or response.get("key") != MODEL_VARIABLE
        or response.get("environment_scope") != "*"
        or response.get("variable_type") != "env_var"
        or any(response.get(flag) is not False for flag in ("hidden", "masked", "protected"))
        or response.get("masked_and_hidden", False) is not False
    ):
        return None, None
    value = admitted_model(response.get("value"))
    if value is None:
        return None, None
    return value, timestamp(datetime.now(UTC).isoformat())


def selected_projects(
    client: GitLabClient, selectors: list[str], bot_id: int, previous: dict[str, Any] | None
) -> tuple[list[dict[str, Any]], str]:
    """Freeze the prior project set for updates and authorize every project read."""

    if previous is not None:
        prior_projects = {project["id"]: project for project in previous["projects"]}
        prior_ids = set(prior_projects)
        chosen = selectors or [str(value) for value in sorted(prior_ids)]
        discovery = previous["scope"]["discovery"]
    elif selectors:
        prior_projects = {}
        prior_ids = None
        chosen = selectors
        discovery = "explicit"
    else:
        prior_projects = {}
        prior_ids = None
        discovery = "bot_contributions"
        contributions = client.pages(
            f"users/{bot_id}/contributed_projects", query={"simple": "true"}
        )
        project_ids = {identity(project.get("id")) for project in contributions}
        if None in project_ids:
            raise CollectionError("GitLab returned invalid contributed project identities.")
        chosen = sorted(str(value) for value in project_ids)
    if not chosen or len(chosen) > MAX_PROJECTS:
        raise CollectionError("The selected GitLab project scope is empty or exceeds its limit.")
    projects: dict[int, dict[str, Any]] = {}
    for selector in dict.fromkeys(chosen):
        try:
            project = _project(client, selector)
        except RequestError as exc:
            prior = prior_projects.get(int(selector)) if selector.isdecimal() else None
            if exc.status not in {403, 404} or prior is None:
                raise
            project = {**prior, "access": "unavailable"}
        projects[project["id"]] = project
    if prior_ids is not None and set(projects) != prior_ids:
        raise CollectionError("The update must retain the saved GitLab project scope.")
    return sorted(projects.values(), key=lambda project: project["path"]), discovery
