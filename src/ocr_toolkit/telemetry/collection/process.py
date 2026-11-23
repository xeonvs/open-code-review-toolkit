"""Project scoped GitLab GraphQL process observations without keeping identities."""

from __future__ import annotations

from collections import Counter
from typing import Any

from .facts import actor, timestamp
from .transport import CollectionError, GitLabClient


def _count(value: object) -> int | None:
    """Accept a bounded nonnegative provider counter."""

    return value if type(value) is int and 0 <= value <= 100_000_000 else None


def _username(value: Any) -> str | None:
    """Extract a transient account name for exact commit-role comparison."""

    name = value.get("username") if isinstance(value, dict) else None
    return name.casefold() if isinstance(name, str) and 0 < len(name) <= 128 else None


def read_process(
    client: GitLabClient,
    path: str,
    iid: int,
    mr: dict[str, Any],
    process: dict[str, Any],
    timeline: dict[str, list[str]] | None,
) -> tuple[str, str]:
    """Merge GitLab diff statistics and commit participation into public-safe counts."""

    process.update(
        additions=None,
        deletions=None,
        changed_lines=None,
        commit_count=None,
        commit_authorship_comparable=False,
        non_merge_commits_by_role={},
        non_merge_commits_after_review_by_role={},
        feedback_cycles=None,
        assigned_reviewer_returned_after_change=None,
        author_responded_before_post_review_commit=None,
    )
    try:
        payload = client.process_graphql(path, iid)
    except CollectionError:
        return "unavailable", "unavailable"
    if not isinstance(payload, dict) or payload.get("errors"):
        return "unavailable", "unavailable"
    data = payload.get("data")
    project = data.get("project") if isinstance(data, dict) else None
    if not isinstance(project, dict) or project.get("fullPath") != path:
        return "unavailable", "unavailable"
    response = project.get("mergeRequest")
    if not isinstance(response, dict) or response.get("iid") != str(iid):
        return "unavailable", "unavailable"
    stats = response.get("diffStatsSummary")
    if isinstance(stats, dict):
        additions = _count(stats.get("additions"))
        deletions = _count(stats.get("deletions"))
        files = _count(stats.get("fileCount"))
        process.update(
            additions=additions,
            deletions=deletions,
            changed_lines=additions + deletions
            if additions is not None and deletions is not None
            else None,
        )
        if files is not None:
            process["changed_files"] = files
    process["commit_count"] = _count(response.get("commitCount"))
    commits = response.get("commitsWithoutMergeCommits")
    page = commits.get("pageInfo") if isinstance(commits, dict) else None
    nodes = commits.get("nodes") if isinstance(commits, dict) else None
    if (
        not isinstance(page, dict)
        or page.get("hasNextPage") is not False
        or not isinstance(nodes, list)
        or len(nodes) > 100
        or any(not isinstance(node, dict) for node in nodes)
    ):
        return "partial", "partial"
    mr_author = mr.get("author")
    author = _username(mr_author)
    reviewers = mr.get("reviewers")
    reviewer_scope_complete = isinstance(reviewers, list) and all(
        _username(item) is not None and actor(item) is not None for item in reviewers
    )
    identity_scope_complete = (
        author is not None and actor(mr_author) is not None and reviewer_scope_complete
    )
    assigned = (
        {name for item in reviewers if (name := _username(item)) is not None and name != author}
        if isinstance(reviewers, list)
        else set()
    )
    first_action = process.get("first_assigned_reviewer_action_at")
    roles: Counter[str] = Counter()
    after_review: Counter[str] = Counter()
    commit_times: list[str] = []
    for node in nodes:
        name = _username(node.get("author"))
        role = (
            "mr_author"
            if author and name == author
            else "assigned_reviewer"
            if name in assigned
            else "other_participant"
            if name and author and isinstance(reviewers, list)
            else "unknown"
        )
        roles[role] += 1
        committed = timestamp(node.get("committedDate")) or timestamp(node.get("authoredDate"))
        if committed:
            commit_times.append(committed)
            if first_action and committed > first_action:
                after_review[role] += 1
    first_followup_commit = min(
        (value for value in commit_times if first_action and value > first_action), default=None
    )
    complete_dates = len(commit_times) == len(nodes)
    commits_state = "complete" if complete_dates else "partial"
    graph_state = (
        "complete"
        if all(
            process[key] is not None for key in ("changed_lines", "changed_files", "commit_count")
        )
        and complete_dates
        else "partial"
    )
    if timeline is None or not complete_dates or not identity_scope_complete:
        return graph_state, commits_state
    cycles = 0
    interaction = "waiting"
    reviewer_actions, changes = set(timeline["assigned_review"]), set(commit_times)
    for moment in sorted(reviewer_actions | changes):
        previous = interaction
        if moment in reviewer_actions:
            cycles += int(previous == "changed")
            interaction = "reviewed"
        if moment in changes and previous == "reviewed":
            interaction = "changed"
    process.update(
        commit_authorship_comparable=not roles["unknown"],
        non_merge_commits_by_role=dict(roles),
        non_merge_commits_after_review_by_role=dict(after_review),
        feedback_cycles=cycles,
        assigned_reviewer_returned_after_change=cycles > 0,
        author_responded_before_post_review_commit=bool(
            first_action
            and first_followup_commit
            and any(
                first_action < value < first_followup_commit for value in timeline["author_action"]
            )
        ),
    )
    return graph_state, commits_state
