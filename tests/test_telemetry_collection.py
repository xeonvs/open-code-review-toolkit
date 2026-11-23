"""Exercise GitLab collection against a controlled glab executable."""

from __future__ import annotations

import json
import shlex
import sys
from pathlib import Path
from typing import Any

import pytest

from ocr_toolkit.posting.formatting import summarize_result
from ocr_toolkit.posting.markers import build_marker
from ocr_toolkit.posting.payloads import build_marked_note_body
from ocr_toolkit.posting.workflow import summary_with_run_marker
from ocr_toolkit.telemetry.collection import CollectionError, collect, transport
from ocr_toolkit.telemetry.collection.attempts import correlate
from ocr_toolkit.telemetry.collection.discussions import _notes
from ocr_toolkit.telemetry.collection.facts import timestamp
from ocr_toolkit.telemetry.collection.scope import current_project_model
from ocr_toolkit.telemetry.collection.transport import GitLabClient
from ocr_toolkit.telemetry.links import web_location

HOST = "synthetic-forge.example.invalid"
BOT = "synthetic-bot"
START, END = "2026-11-01", "2026-11-02"
BASE, HEAD = "1" * 40, "2" * 40
OLD_NOTE, CURRENT_NOTE, UNRELATED_NOTE = 21, 22, 23
CREATED = "2026-11-02T23:45:00Z"
PUBLISHED = "2026-11-02T23:56:00Z"
MODEL_ENDPOINT = "projects/5/variables/OCR_LLM_MODEL"
TOKEN_USAGE = "- Token usage: 15 total (input: 9, output: 6)"
MODEL_VARIABLE = {
    "key": "OCR_LLM_MODEL",
    "environment_scope": "*",
    "variable_type": "env_var",
    "protected": False,
    "masked": False,
    "hidden": False,
    "value": "openai/synthetic-model",
}


@pytest.fixture
def forge(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    """Run the real bounded subprocess transport against synthetic responses."""

    launcher = tmp_path / "glab"
    script = tmp_path / "fixture.py"
    script.write_text(
        """
import json
import os
import sys
import time
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

assert sys.argv[1:3] == ["api", "--method"]
assert "OCR_LLM_TOKEN" not in os.environ
assert "GLAB_DEBUG_HTTP" not in os.environ
directory = Path(__file__).parent
peer = json.loads((directory / "responses.json").read_text())
method = sys.argv[3]
args = sys.argv[4:]
assert "--hostname" not in args
paginate = args[0] == "--paginate"
if paginate:
    args = args[1:]
url = urlsplit(args[0])
if method == "POST":
    assert url.path == "graphql"
    fields = dict(field.split("=", 1) for field in args[2::2])
    assert fields["query"].strip().startswith("query(")
    assert "mutation" not in fields["query"]
    assert fields["fullPath"] in {"example/service", "example/second"}
    assert fields["iid"] == "1"
    key = f"graphql/{fields['fullPath']}"
else:
    assert method == "GET" and len(args) == 1
    key = url.path
with (directory / "requests.jsonl").open("a") as log:
    print(json.dumps([method, key, os.environ.get("GITLAB_HOST"), parse_qs(url.query)]), file=log)
value = peer["responses"][key]
if isinstance(value, dict) and value.get("stalled"):
    time.sleep(1)
if isinstance(value, dict) and value.get("network_failure"):
    print("arbitrary private network diagnostic", file=sys.stderr)
    raise SystemExit(1)
if isinstance(value, dict) and "failure" in value:
    print(f"HTTP {value['failure']} arbitrary private response suffix", file=sys.stderr)
    raise SystemExit(1)
if isinstance(value, dict) and "raw_fixture_output" in value:
    print(value["raw_fixture_output"])
    raise SystemExit(0)
if paginate:
    assert isinstance(value, list)
    midpoint = len(value) // 2
    print(json.dumps(value[:midpoint]))
    print(json.dumps(value[midpoint:]))
else:
    print(json.dumps(value))
""".lstrip(),
        encoding="utf-8",
    )
    launcher.write_text(
        f'#!/bin/sh\nexec {shlex.quote(sys.executable)} -I {shlex.quote(str(script))} "$@"\n',
        encoding="utf-8",
    )
    launcher.chmod(0o700)
    monkeypatch.setenv("PATH", str(tmp_path))
    monkeypatch.setenv("OCR_LLM_TOKEN", "synthetic-private-token")
    monkeypatch.setenv("GLAB_DEBUG_HTTP", "1")
    for name in ("GITLAB_HOST", "GITLAB_URI", "GL_HOST", "GITLAB_URL"):
        monkeypatch.delenv(name, raising=False)
    return tmp_path / "responses.json", tmp_path / "requests.jsonl"


def _note(identifier: int, body: str, *, author: int = 7, **fields: Any) -> dict[str, Any]:
    """Create one provider discussion note with deliberately unretained data."""

    return {
        "id": identifier,
        "author": {"id": author, "username": "synthetic-unretained-user"},
        "body": body,
        "system": False,
        "created_at": PUBLISHED,
        "updated_at": PUBLISHED,
        **fields,
    }


def _responses(
    project_ids: tuple[int, ...] = (5,),
    *,
    token_usage: str = "",
    published_model: str | None = None,
) -> dict[str, Any]:
    """Supply a scoped MR, retry-aware job, discussion, reaction and GraphQL process facts."""

    responses: dict[str, Any] = {
        "user": {"id": 11, "username": "operator", "web_url": f"https://{HOST}/operator"},
        "users": [{"id": 7, "username": BOT}],
        "users/7/contributed_projects": [{"id": project_id} for project_id in project_ids],
    }
    summary = build_marked_note_body(
        summary_with_run_marker(
            summarize_result(
                0, 0, 0, 0, token_usage_summary=token_usage, review_model=published_model
            ),
            "a" * 32,
        )
    )
    for project_id in project_ids:
        project = f"projects/{project_id}"
        endpoint = f"{project}/merge_requests/1"
        path = "example/service" if project_id == 5 else "example/second"
        mr = {
            "iid": 1,
            "project_id": project_id,
            "created_at": CREATED,
            "updated_at": PUBLISHED,
            "sha": HEAD,
            "source_branch": "synthetic-unretained-branch",
            "state": "opened",
            "author": {"id": 40, "username": "synthetic-unretained-author"},
            "reviewers": [{"id": 41, "username": "synthetic-unretained-reviewer"}],
            "title": "Synthetic private MR prose.",
        }
        pipeline = {
            "id": 55,
            "sha": BASE,
            "created_at": "2026-11-02T23:50:00Z",
            "ref": "refs/merge-requests/1/head",
            "source": "merge_request_event",
        }
        reduced_pipeline = {key: pipeline[key] for key in ("id", "sha", "ref")}
        job = {
            "id": 555,
            "name": "review",
            "created_at": "2026-11-02T23:50:30Z",
            "started_at": "2026-11-02T23:51:00Z",
            "finished_at": "2026-11-02T23:58:00Z",
            "status": "success",
            "allow_failure": False,
            "pipeline": {"id": 55, "sha": BASE},
        }
        responses.update(
            {
                project: {"id": project_id, "path_with_namespace": path, "archived": False},
                f"{project}/merge_requests": [mr],
                endpoint: mr,
                f"{project}/pipelines": [pipeline],
                f"{endpoint}/versions": [{"created_at": CREATED, "head_commit_sha": BASE}],
                f"{endpoint}/pipelines": [reduced_pipeline, reduced_pipeline],
                f"{project}/pipelines/55": {**pipeline, "project_id": project_id},
                f"{project}/pipelines/55/jobs": [job, job, {**job, "id": 999, "name": "unrelated"}],
                f"{project}/repository/commits": [{"id": HEAD, "parent_ids": [BASE]}],
                f"{endpoint}/discussions": [
                    {"notes": [_note(OLD_NOTE, summary)]},
                    {"notes": [_note(CURRENT_NOTE, summary)]},
                    {"notes": [_note(CURRENT_NOTE, summary)]},
                    {"notes": [_note(UNRELATED_NOTE, "Synthetic unrelated bot message.")]},
                    {"notes": [_note(24, build_marker("a" * 32), resolvable=True)]},
                    {"notes": [_note(25, build_marker("a" * 32), resolvable=True)]},
                    {"notes": [_note(26, "Synthetic reviewer prose.", author=41, resolvable=True)]},
                ],
                f"{endpoint}/approvals": {"approvals_required": 1, "approved_by": []},
                f"{endpoint}/notes/21/award_emoji": [{"user": {"id": 40}, "name": "private-emoji"}],
                f"{endpoint}/notes/22/award_emoji": [],
                f"{endpoint}/notes/24/award_emoji": [],
                f"{endpoint}/notes/25/award_emoji": [],
                f"{endpoint}/notes/26/award_emoji": [],
                f"graphql/{path}": {
                    "data": {
                        "project": {
                            "fullPath": path,
                            "mergeRequest": {
                                "iid": "1",
                                "diffStatsSummary": {
                                    "additions": 8,
                                    "deletions": 2,
                                    "fileCount": 1,
                                },
                                "commitCount": 1,
                                "commitsWithoutMergeCommits": {
                                    "pageInfo": {"hasNextPage": False},
                                    "nodes": [
                                        {
                                            "author": {"username": "synthetic-unretained-author"},
                                            "committedDate": "2026-11-02T23:57:00Z",
                                        }
                                    ],
                                },
                            },
                        }
                    }
                },
            }
        )
    return responses


def _write(path: Path, responses: dict[str, Any]) -> None:
    """Switch the controlled peer's visible response snapshot for the next collection."""

    path.write_text(json.dumps({"responses": responses}), encoding="utf-8")


def _collect(
    previous: dict[str, Any] | None = None,
    *,
    selected: list[str] | None = None,
    collect_model: bool = False,
) -> dict[str, Any]:
    """Use the fixed inclusive dates and exact chosen job in each synthetic scenario."""

    return collect(
        previous=previous,
        projects=selected or [],
        bot=BOT,
        job_names=["review"],
        start=START,
        end=END,
        collect_model=collect_model,
    )


def test_collect_cost_model_uses_only_exact_project_variable_and_omits_response_fields(forge):
    """Persist the permitted current setting and its UTC observation time only."""

    config, log = forge
    responses = _responses(token_usage=TOKEN_USAGE)
    responses[MODEL_ENDPOINT] = {**MODEL_VARIABLE, "description": "synthetic unretained metadata"}
    _write(config, responses)
    result = _collect(collect_model=True)
    project = result["projects"][0]
    assert project["cost_model"] == MODEL_VARIABLE["value"]
    observed = project["cost_model_observed_at"]
    assert observed == timestamp(observed)
    assert observed >= result["records"][0]["lifecycle_observed_at"]
    assert "synthetic unretained metadata" not in json.dumps(result)
    assert "cost_model" not in result["records"][0]
    requests = [json.loads(line) for line in log.read_text().splitlines()]
    assert [row for row in requests if "/variables" in row[1]] == [
        ["GET", MODEL_ENDPOINT, None, {"filter[environment_scope]": ["*"]}]
    ]

    log.write_text("")
    responses[MODEL_ENDPOINT] = {"failure": 500}
    _write(config, responses)
    disabled = _collect(result, collect_model=False)
    assert "/variables" not in log.read_text()
    assert disabled["projects"][0]["cost_model"] is None
    assert disabled["projects"][0]["cost_model_observed_at"] is None
    assert project["cost_model"] == MODEL_VARIABLE["value"]


@pytest.mark.parametrize(
    "scenario",
    ["empty", "named", "no_usage", "zero_usage", "total_only", "other", "rejected_model"],
)
def test_collect_does_not_read_unneeded_project_model(forge, scenario):
    """Skip a project setting read unless missing publication metadata can be used."""

    config, log = forge
    model = MODEL_VARIABLE["value"] if scenario in {"named", "rejected_model"} else None
    token_usage = {
        "empty": "",
        "named": TOKEN_USAGE,
        "no_usage": "",
        "zero_usage": "- Token usage: 0 total (input: 0, output: 0)",
        "total_only": "- Token usage: 15 total",
        "other": "- Token usage: 17 total (input: 9, output: 6, other: 2)",
        "rejected_model": TOKEN_USAGE,
    }[scenario]
    responses = _responses(token_usage=token_usage, published_model=model)
    if scenario == "empty":
        responses["projects/5/merge_requests"] = []
    elif scenario == "rejected_model":
        for thread in responses["projects/5/merge_requests/1/discussions"]:
            for note in thread["notes"]:
                note["body"] = note["body"].replace(
                    f"`{MODEL_VARIABLE['value']}`",
                    "`https://synthetic.example.invalid/not-a-model`",
                )
    responses[MODEL_ENDPOINT] = MODEL_VARIABLE
    _write(config, responses)
    snapshot = _collect(collect_model=True)
    if scenario == "empty":
        assert not snapshot["records"]
    elif scenario in {"named", "rejected_model"}:
        assert all(
            row.get("model") == model if scenario == "named" else row.get("model_rejected") is True
            for row in snapshot["records"][0]["reviews"]
        )
    assert MODEL_ENDPOINT not in log.read_text()
    assert snapshot["projects"][0]["cost_model"] is None


@pytest.mark.parametrize(
    "response",
    [
        {"failure": 403},
        {"failure": 404},
        {"failure": 400},
        {"failure": 401},
        {"failure": 429},
        {"failure": 503},
        {"network_failure": True},
        {"raw_fixture_output": '{"key":"OCR_LLM_MODEL","key":"OCR_LLM_MODEL"}'},
        [MODEL_VARIABLE],
        {**MODEL_VARIABLE, "environment_scope": "production"},
        {**MODEL_VARIABLE, "key": "SYNTHETIC_UNEXPECTED_KEY"},
        {**MODEL_VARIABLE, "variable_type": "file"},
        {**MODEL_VARIABLE, "masked": True},
        {**MODEL_VARIABLE, "protected": True},
        {**MODEL_VARIABLE, "hidden": True},
        {**MODEL_VARIABLE, "masked_and_hidden": True},
        {key: value for key, value in MODEL_VARIABLE.items() if key != "hidden"},
        {**MODEL_VARIABLE, "protected": 0},
        {**MODEL_VARIABLE, "value": "$OTHER_MODEL"},
        {**MODEL_VARIABLE, "value": "openai/synthetic-model\n"},
        {**MODEL_VARIABLE, "value": "https://models.example.invalid/openai/synthetic-model"},
        {**MODEL_VARIABLE, "value": "glpat-not-a-key"},
    ],
)
def test_unusable_project_variable_yields_no_model_or_timestamp(forge, response):
    """Ignore permission failures, ambiguous records, sensitive flags and noncanonical values."""

    config, _ = forge
    responses = _responses()
    responses[MODEL_ENDPOINT] = response
    _write(config, responses)
    assert current_project_model(GitLabClient(), 5) == (None, None)


def test_project_model_equal_to_configured_secret_is_omitted(forge, monkeypatch):
    """A syntactically valid model shape still crosses credential admission."""

    config, _ = forge
    responses = _responses()
    responses[MODEL_ENDPOINT] = MODEL_VARIABLE
    _write(config, responses)
    monkeypatch.setenv("OCR_LLM_TOKEN", MODEL_VARIABLE["value"])
    assert current_project_model(GitLabClient(), 5) == (None, None)


def test_project_model_timeout_is_optional_but_global_request_limit_is_fatal(
    forge, monkeypatch, capsys
):
    """A request-local timeout leaves model unknown without suppressing the client budget."""

    config, _ = forge
    responses = _responses()
    responses[MODEL_ENDPOINT] = {"stalled": True}
    _write(config, responses)
    client = GitLabClient()
    monkeypatch.setattr(transport, "REQUEST_SECONDS", 0.2)
    assert current_project_model(client, 5) == (None, None)
    assert capsys.readouterr().err == ""
    client.calls = transport.MAX_CALLS
    with pytest.raises(CollectionError, match="request limit was exceeded"):
        current_project_model(client, 5)


def test_update_drops_stale_project_default_when_project_is_no_longer_visible(forge):
    """A historical observation cannot establish the lost project's current model."""

    config, log = forge
    responses = _responses((5, 6), token_usage=TOKEN_USAGE)
    second_endpoint = "projects/6/variables/OCR_LLM_MODEL"
    responses[MODEL_ENDPOINT] = responses[second_endpoint] = MODEL_VARIABLE
    _write(config, responses)
    previous = _collect(collect_model=True)
    responses["projects/6"] = {"failure": 403}
    responses[MODEL_ENDPOINT] = {"failure": 503}
    log.write_text("")
    _write(config, responses)
    updated = _collect(previous, collect_model=True)
    assert second_endpoint not in log.read_text()
    assert MODEL_ENDPOINT in log.read_text()
    assert all(row["cost_model"] == MODEL_VARIABLE["value"] for row in previous["projects"])
    assert all(row["cost_model"] is None for row in updated["projects"])
    assert all(row["cost_model_observed_at"] is None for row in updated["projects"])


def test_collect_binds_scoped_sources_and_leaves_only_normalized_data(forge, capsys):
    """Observe the active self-managed host, scoped requests and privacy-safe state."""

    config, log = forge
    responses = _responses()
    responses["projects/example%2Fservice"] = responses["projects/5"]
    _write(config, responses)
    snapshot = _collect(selected=["example/service"])
    assert snapshot["scope"]["discovery"] == "explicit"
    assert snapshot["scope"]["host"] == HOST and snapshot["scope"]["end"] == END
    assert "inclusive across 1 project(s)" in capsys.readouterr().err
    requests = [json.loads(line) for line in log.read_text().splitlines()]
    assert requests[0][:3] == ["GET", "user", None]
    assert all(request[2] is None for request in requests[1:])
    listing = next(row for row in requests if row[1] == "projects/5/merge_requests")
    assert listing[3]["created_before"] == ["2026-11-03T00:00:00.000000Z"]
    assert sum(row[1] == "projects/5/pipelines/55" for row in requests) == 1
    assert all(
        "award_emoji" not in row[1] or f"/{UNRELATED_NOTE}/" not in row[1] for row in requests
    )
    assert len(snapshot["records"]) == 1
    mr = snapshot["records"][0]
    assert mr["lifecycle_observed_at"] >= snapshot["scope"]["updated_at"]
    assert mr["web_url"] == f"https://{HOST}/example/service/-/merge_requests/1"
    assert len(mr["runs"]) == len(mr["checkpoints"]) == 1 and mr["runs"][0]["success"] is True
    assert len(mr["discussions"]) == 4 and len(mr["reviews"]) == 2
    assert mr["revisions"][0]["non_merge_commits"] == 1
    assert mr["process"]["changed_lines"] == 10
    assert mr["process"]["non_merge_commits_after_review_by_role"] == {"mr_author": 1}
    assert mr["process"]["ocr_repeated_publications"] == 1
    assert mr["reactions"]["author_reactions"] == 1
    serialized = json.dumps(snapshot)
    for private in (BASE, HEAD, "unretained", "private-emoji", "private MR prose", "unrelated"):
        assert private not in serialized


def test_update_keeps_project_scope_edits_history_and_marks_access_loss(forge):
    """Preserve deleted observations, update one note in place, and fail total access loss."""

    config, log = forge
    responses = _responses((5, 6))
    _write(config, responses)
    original = _collect()
    assert original["scope"]["discovery"] == "bot_contributions"
    frozen = json.dumps(original)
    log.write_text("")
    responses["projects/6"] = {"failure": 403}
    responses["projects/5/pipelines/55/jobs"] = {"failure": 404}
    current = build_marked_note_body(summarize_result(0, 0, 0, 0, outcome_status="warning"))
    responses["projects/5/merge_requests/1/discussions"] = [
        {"notes": [_note(CURRENT_NOTE, current, updated_at="2026-11-03T00:00:00Z")]}
    ]
    _write(config, responses)
    updated = _collect(original)
    assert json.dumps(original) == frozen
    assert "contributed_projects" not in log.read_text()
    assert len(updated["projects"]) == 2
    assert {row["id"]: row["access"] for row in updated["projects"]} == {
        5: "complete",
        6: "unavailable",
    }
    mr, lost = updated["records"]
    assert mr["completeness"]["pipelines"] == "unavailable"
    assert mr["runs"] == original["records"][0]["runs"]
    assert len(mr["reviews"]) == 2
    by_note = {review["source_note_id"]: review["outcome"] for review in mr["reviews"]}
    assert by_note == {OLD_NOTE: "complete", CURRENT_NOTE: "complete_with_warnings"}
    assert lost["reviews"] == original["records"][1]["reviews"]
    assert lost["lifecycle_observed_at"] == original["records"][1]["lifecycle_observed_at"]
    assert lost["process"]["latest_meaningful_activity_at"] is None
    assert set(lost["completeness"].values()) == {"unavailable"}
    log.write_text("")
    restored_responses = _responses((5, 6))
    _write(config, restored_responses)
    restored = _collect(updated)
    assert restored["projects"][0]["access"] == "complete"
    assert restored["records"][0]["completeness"]["pipelines"] == "complete"
    assert restored["records"][1]["completeness"]["pipelines"] == "complete"
    reopened_listing = next(
        json.loads(row)
        for row in log.read_text().splitlines()
        if json.loads(row)[1] == "projects/6/merge_requests"
    )
    assert "created_after" in reopened_listing[3] and "updated_after" not in reopened_listing[3]
    responses["projects/5"] = {"failure": 404}
    _write(config, responses)
    with pytest.raises(CollectionError, match="entire saved project scope"):
        _collect(updated)


def test_deleted_sole_refresh_candidate_keeps_accessible_scope(forge):
    """An out-of-period pipeline or deleted saved MR cannot hide accessible projects."""

    config, log = forge
    responses = _responses((5, 6))
    responses["projects/6/merge_requests/1/discussions"] = []
    _write(config, responses)
    previous = _collect()
    log.write_text("")
    responses["projects/5/merge_requests"] = []
    responses["projects/6/merge_requests"] = []
    responses["projects/5/merge_requests/1"] = {"failure": 404}
    responses["projects/5/pipelines"] = [{"ref": "refs/merge-requests/99/head"}]
    responses["projects/6/pipelines"] = []
    _write(config, responses)
    snapshot = _collect(previous)
    assert "merge_requests/99" not in log.read_text()
    assert "projects/6/merge_requests/1" not in log.read_text()
    assert {row["id"]: row["access"] for row in snapshot["projects"]} == {
        5: "partial",
        6: "complete",
    }
    assert set(snapshot["records"][0]["completeness"].values()) == {"unavailable"}
    assert (
        snapshot["records"][0]["lifecycle_observed_at"]
        == previous["records"][0]["lifecycle_observed_at"]
    )
    assert snapshot["records"][1] == previous["records"][1]


def test_incomplete_human_sources_retry_with_no_new_mr_or_bot_activity(forge):
    """Recover approvals and reactions and read dated system approval evidence."""

    config, log = forge
    endpoint = "projects/5/merge_requests/1"
    responses = _responses()
    responses[f"{endpoint}/discussions"] = [
        {"notes": [_note(26, "Synthetic reviewer prose.", author=41, resolvable=True)]},
        {"notes": [_note(27, "approved this merge request", author=41, system=True)]},
        {
            "notes": [
                _note(
                    28, "unapproved this merge request", author=41, system=True, created_at=CREATED
                )
            ]
        },
    ]
    responses[f"{endpoint}/approvals"] = {"failure": 403}
    responses[f"{endpoint}/notes/26/award_emoji"] = {"failure": 403}
    _write(config, responses)
    previous = _collect()
    mr = previous["records"][0]
    assert not mr["reviews"] and not mr["discussions"]
    assert mr["completeness"]["approvals"] == "unavailable"
    assert mr["completeness"]["reactions"] == "partial"
    responses["projects/5/merge_requests"] = []
    responses["projects/5/pipelines"] = []
    responses[f"{endpoint}/approvals"] = {"approved_by": [{"user": {"id": 41}}]}
    responses[f"{endpoint}/notes/26/award_emoji"] = [{"id": 61, "user": {"id": 40}}]
    log.write_text("")
    _write(config, responses)
    mr = _collect(previous)["records"][0]
    assert "pipelines/55/jobs" not in log.read_text()
    assert mr["completeness"]["approvals"] == mr["completeness"]["reactions"] == "complete"
    assert mr["process"]["approval_count"] == 1
    assert mr["process"]["first_approval_at"] == timestamp(PUBLISHED)
    assert mr["reactions"]["author_reactions_to_assigned_review"] == 1


def test_assigned_review_reactions_refresh_with_complete_sources_and_empty_feeds(forge):
    """A reaction on a human thread may change without advancing either incremental feed."""

    config, log = forge
    endpoint = "projects/5/merge_requests/1"
    reactions = f"{endpoint}/notes/26/award_emoji"
    responses = _responses()
    responses[f"{endpoint}/discussions"] = [
        {"notes": [_note(26, "Assigned review.", author=41, resolvable=True)]}
    ]
    _write(config, responses)
    previous = _collect()
    mr = previous["records"][0]
    assert not mr["discussions"] and mr["completeness"]["reactions"] == "complete"
    assert mr["reactions"]["author_reactions_to_assigned_review"] == 0
    responses["projects/5/merge_requests"] = []
    responses["projects/5/pipelines"] = []
    responses[reactions] = [{"id": 71, "user": {"id": 40}}]
    log.write_text("")
    _write(config, responses)
    mr = _collect(previous)["records"][0]
    requests = [json.loads(line) for line in log.read_text().splitlines()]
    listing = next(row[3] for row in requests if row[1] == "projects/5/merge_requests")
    assert listing["created_after"] == ["2026-11-01T00:00:00.000000Z"]
    assert listing["updated_after"]
    assert any(row[1] == reactions for row in requests)
    assert mr["reactions"]["author_reactions_to_assigned_review"] == 1


@pytest.mark.parametrize(
    ("initial_read", "kind", "recoverable"),
    [
        ({"failure": 403}, "ancestry_unavailable", True),
        ({"failure": 404}, "ancestry_unavailable", True),
        ([{"id": HEAD, "parent_ids": []}], "rewritten_or_incomparable", False),
    ],
)
def test_retry_only_recoverable_ancestry_without_other_activity(
    forge, initial_read, kind, recoverable
):
    """A permission gap retries even for terminal jobs, while a root mismatch stays incomparable."""

    config, log = forge
    endpoint = "projects/5/merge_requests/1"
    ancestry = "projects/5/repository/commits"
    responses = _responses()
    responses[f"{endpoint}/discussions"] = []
    responses[ancestry] = initial_read
    _write(config, responses)
    previous = _collect()
    baseline = previous["records"][0]
    assert (
        baseline["completeness"]["pipelines"] == baseline["completeness"]["versions"] == "complete"
    )
    assert baseline["completeness"]["revisions"] == "partial"
    assert baseline["revisions"][0]["change_kind"] == kind
    responses["projects/5/merge_requests"] = []
    responses["projects/5/pipelines"] = []
    responses[ancestry] = [{"id": HEAD, "parent_ids": [BASE]}]
    _write(config, responses)
    log.write_text("")
    mr = _collect(previous)["records"][0]
    assert (ancestry in log.read_text()) is recoverable
    assert mr["completeness"]["revisions"] == ("complete" if recoverable else "partial")
    assert mr["revisions"][0]["comparable"] is recoverable


@pytest.mark.parametrize("reviewers", [None, [{"id": 41}]])
def test_complete_commit_dates_do_not_invent_participant_roles(forge, reviewers):
    """Date evidence can remain complete when the assigned reviewer identities are missing."""

    config, _ = forge
    responses = _responses()
    responses["projects/5/merge_requests/1"]["reviewers"] = reviewers
    _write(config, responses)
    mr = _collect()["records"][0]
    assert mr["completeness"]["commits"] == "complete"
    assert mr["process"]["commit_authorship_comparable"] is False
    assert mr["process"]["non_merge_commits_by_role"] == {}
    assert mr["process"]["feedback_cycles"] is None


@pytest.mark.parametrize("source", ["discussions", "versions"])
def test_incomplete_sources_do_not_turn_open_mr_creation_into_inactivity(forge, source):
    """Even one unavailable activity source leaves the inactivity clock unknown."""

    config, _ = forge
    responses = _responses()
    responses[f"projects/5/merge_requests/1/{source}"] = {"failure": 403}
    _write(config, responses)
    mr = _collect()["records"][0]
    assert mr["completeness"][source] == "unavailable"
    assert mr["created_at"] == timestamp(CREATED)
    assert mr["process"]["latest_meaningful_activity_at"] is None


@pytest.mark.parametrize(("later_review", "cycles"), [(False, 0), (True, 1)])
def test_feedback_cycle_requires_strict_event_order(forge, later_review, cycles):
    """A commit and returning review at one timestamp provide no event order."""

    config, _ = forge
    endpoint = "projects/5/merge_requests/1"
    responses = _responses()
    notes = [
        {"notes": [_note(26, "Initial review.", author=41, resolvable=True)]},
        {
            "notes": [
                _note(27, "Simultaneous review.", author=41, created_at="2026-11-02T23:57:00Z")
            ]
        },
    ]
    if later_review:
        notes.append(
            {"notes": [_note(28, "Later review.", author=41, created_at="2026-11-02T23:58:00Z")]}
        )
    responses[f"{endpoint}/discussions"] = notes
    _write(config, responses)
    assert _collect()["records"][0]["process"]["feedback_cycles"] == cycles


def test_reduced_pipeline_rejects_inconsistent_detail_before_job_read(forge):
    """The MR-scoped ref must match the detail before its jobs become eligible."""

    config, log = forge
    responses = _responses()
    responses["projects/5/pipelines/55"]["ref"] = "refs/merge-requests/99/head"
    _write(config, responses)
    with pytest.raises(CollectionError, match="pipeline details do not match"):
        _collect()
    assert "pipelines/55/jobs" not in log.read_text()


def test_invalid_active_profile_cannot_select_a_foreign_host(forge):
    """Reject credential-containing profile data before any scoped request."""

    config, log = forge
    responses = _responses()
    responses["user"]["web_url"] = "https://private-passphrase@foreign.example.invalid/operator"
    _write(config, responses)
    with pytest.raises(CollectionError, match=r"^Cannot bind the active glab context") as error:
        GitLabClient()
    assert "private-passphrase" not in str(error.value)
    assert len(log.read_text().splitlines()) == 1


def test_mismatched_profile_cannot_redirect_authentication_to_a_new_host(forge, monkeypatch):
    """Accept no remote override of the host selected in the local glab environment."""

    config, log = forge
    monkeypatch.setenv("GITLAB_HOST", HOST)
    responses = _responses()
    responses["user"]["web_url"] = "https://foreign.example.invalid/operator"
    _write(config, responses)
    with pytest.raises(CollectionError, match="does not match the configured glab host"):
        GitLabClient()
    assert [json.loads(line)[:3] for line in log.read_text().splitlines()] == [
        ["GET", "user", HOST]
    ]
    log.write_text("")
    _write(config, _responses())
    client = GitLabClient()
    assert client.get("projects/5")["id"] == 5
    assert [json.loads(line)[:3] for line in log.read_text().splitlines()] == [
        ["GET", "user", HOST],
        ["GET", "projects/5", HOST],
    ]


def test_prefixed_installation_keeps_verified_links_and_rejects_foreign_origin(forge):
    """Retain links from a self-managed instance whose routes start at a subpath."""

    config, _ = forge
    responses = _responses()
    base_path = "/services/gitlab"
    origin = f"https://{HOST}:443"
    responses["user"]["web_url"] = f"{origin}{base_path}/operator"
    project = f"{origin}{base_path}/example/service"
    mr = f"{project}/-/merge_requests/1"
    responses["projects/5"]["web_url"] = project
    responses["projects/5/merge_requests/1"]["web_url"] = mr
    _write(config, responses)
    snapshot = _collect(selected=["5"])
    assert snapshot["scope"]["base_path"] == base_path
    assert snapshot["projects"][0]["web_url"] == project
    assert snapshot["records"][0]["web_url"] == mr
    responses["projects/5/merge_requests/1"]["web_url"] = mr.replace(
        HOST, "foreign.example.invalid"
    )
    _write(config, responses)
    with pytest.raises(CollectionError, match="outside the verified observation scope") as error:
        _collect(snapshot)
    assert "foreign.example.invalid" not in str(error.value)


def test_web_location_rejects_brackets_even_when_parser_reports_a_dns_like_host():
    """A bracketed IPvFuture authority must not compare equal to the approved DNS host."""

    assert web_location("https://v1.Example.invalid:443/services/gitlab") == (
        "v1.example.invalid",
        "/services/gitlab",
    )
    assert web_location("https://[v1.example.invalid]:443/services/gitlab") is None


def test_glab_transport_caps_output_and_uses_closed_failure_diagnostics(forge, monkeypatch):
    """Reject an oversized stream and report only the authenticated HTTP status."""

    config, _ = forge
    responses = _responses()
    responses["projects/5"] = {"private_value": "synthetic-private-output" * 40}
    responses["projects/6"] = {"failure": 403}
    _write(config, responses)
    client = GitLabClient()
    monkeypatch.setattr(transport, "MAX_BYTES", 128)
    with pytest.raises(CollectionError, match="exceeded its byte limit") as error:
        client.get("projects/5")
    assert "synthetic-private-output" not in str(error.value)
    with pytest.raises(
        CollectionError, match=r"^GitLab API request failed \(HTTP 403\)\.$"
    ) as error:
        client.get("projects/6")
    assert "arbitrary private response" not in str(error.value)


def test_conflicting_duplicate_discussion_is_rejected():
    """An identical paginated repeat is safe and a changed copy fails closed."""

    entry = {"notes": [_note(21, "first version")]}
    assert _notes([entry, entry]) == [entry["notes"]]
    with pytest.raises(CollectionError, match="repeated discussion note"):
        _notes([entry, {"notes": [_note(21, "different version")]}])


def test_pre_model_correlation_excludes_unique_but_labels_overlapping_attempts():
    """A retry may become the first reviewed checkpoint after an earlier model stop."""

    start = timestamp("2026-11-02T23:50:00Z")
    finish = timestamp("2026-11-02T23:54:00Z")
    retry = timestamp("2026-11-02T23:59:00Z")
    note_at = timestamp("2026-11-02T23:52:00Z")
    first = {
        "_pipeline_id": 1,
        "status": "success",
        "detached": True,
        "pipeline_created_at": start,
        "created_at": start,
        "started_at": start,
        "review_finished_at": finish,
    }
    review = {"result_kind": "pre_model", "created_at": note_at, "updated_at": note_at}
    later = {**first, "started_at": finish, "review_finished_at": retry}
    runs, checkpoints, counts = correlate([(first, HEAD), (later, HEAD)], [review], "opened", None)
    assert [run["pre_model_stop"] for run in runs] == [True, False]
    assert checkpoints == [
        ({"pipeline_created_at": start, "started_at": finish, "finished_at": retry}, HEAD)
    ]
    assert counts["matched_messages"] == 1
    _, _, counts = correlate([(first, HEAD), (first, HEAD)], [review], "opened", None)
    assert counts["ambiguous_messages"] == 1


def test_terminal_job_requires_independent_publication_to_exclude_revision():
    """A terminal MR timestamp alone does not identify the historical job phase."""

    created = timestamp("2026-11-02T23:50:00Z")
    closed = timestamp("2026-11-02T23:51:00Z")
    started = timestamp("2026-11-02T23:52:00Z")
    posted = timestamp("2026-11-02T23:53:00Z")
    finished = timestamp("2026-11-02T23:54:00Z")
    run = {
        "_pipeline_id": 1,
        "status": "success",
        "detached": True,
        "pipeline_created_at": created,
        "created_at": created,
        "started_at": started,
        "review_finished_at": finished,
    }
    rows, checkpoints, _ = correlate([(run, HEAD)], [], "closed", closed)
    assert len(checkpoints) == 1 and rows[0]["terminal_pre_model"] is False
    terminal = {
        "result_kind": "terminal_lifecycle",
        "terminal_lifecycle": "closed",
        "created_at": posted,
        "updated_at": posted,
    }
    rows, checkpoints, _ = correlate([(run, HEAD)], [terminal], "closed", closed)
    assert not checkpoints and rows[0]["terminal_pre_model"] is True


def test_edited_terminal_publication_uses_only_current_payload_time():
    """An existing terminal note can be updated after another lifecycle transition."""

    created = timestamp("2026-11-02T23:45:00Z")
    first_post = timestamp("2026-11-02T23:50:00Z")
    boundary = timestamp("2026-11-02T23:53:00Z")
    updated = timestamp("2026-11-02T23:56:00Z")
    finished = timestamp("2026-11-02T23:58:00Z")
    first = {
        "_pipeline_id": 1,
        "status": "success",
        "detached": True,
        "pipeline_created_at": created,
        "started_at": created,
        "review_finished_at": boundary,
    }
    second = {
        **first,
        "_pipeline_id": 2,
        "pipeline_created_at": boundary,
        "started_at": boundary,
        "review_finished_at": finished,
    }
    edition = {
        "result_kind": "terminal_lifecycle",
        "terminal_lifecycle": "merged",
        "created_at": first_post,
        "updated_at": updated,
    }
    attempts, checkpoints, _ = correlate(
        [(first, BASE), (second, HEAD)], [edition], "merged", boundary
    )
    assert [run["terminal_pre_model"] for run in attempts] == [False, True]
    assert [sha for _, sha in checkpoints] == [BASE]
