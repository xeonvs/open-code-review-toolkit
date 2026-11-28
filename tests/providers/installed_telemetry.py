"""Exercise collection and offline rendering through the installed telemetry CLI."""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
from decimal import Decimal
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

HOST = "synthetic-gitlab.invalid"
PROJECT = 872937
IID = 43862
PROJECT_PATH = "telemetry-fixture/isolated-project"
PROJECT_URL = f"https://{HOST}/{PROJECT_PATH}"
MR_URL = f"{PROJECT_URL}/-/merge_requests/{IID}"
SHA = "fc" * 20
CREATED = "2026-11-03T09:00:00Z"
PUBLISHED = "2026-11-03T10:00:00Z"
MERGED = "2026-11-04T10:00:00Z"
PRIVATE_TEXT = "synthetic-fixture-private-conversation"
PROJECT_MODEL = "openai/synthetic-model"
RUN_MODEL = "openai/synthetic-run-model"
MASKED_MODEL = "private-fixture-model-canary"
AUTHOR = {"id": 9773, "username": "synthetic-mr-author"}
BOT = {"id": 3692, "username": "mr.bot"}


class ReportLinks(HTMLParser):
    """Extract navigable links independently of prose and serialized JSON."""

    def __init__(self) -> None:
        super().__init__()
        self.destinations: list[str] = []
        self.rows: list[tuple[str, ...]] = []
        self.current_row: list[str] | None = None
        self.title = ""
        self.in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self.current_row = []
        if tag == "title":
            self.in_title = True
        if tag == "a" and (href := dict(attrs).get("href")):
            self.destinations.append(href)

    def handle_endtag(self, tag: str) -> None:
        if tag == "tr" and self.current_row is not None:
            self.rows.append(tuple(self.current_row))
            self.current_row = None
        if tag == "title":
            self.in_title = False

    def handle_data(self, data: str) -> None:
        if self.current_row is not None and data.strip():
            self.current_row.append(data.strip())
        if self.in_title:
            self.title += data


def publisher_note(model: str | None = None) -> str:
    """Use the same summary and control markers as the installed GitLab publisher."""

    from ocr_toolkit.posting.formatting import summarize_result
    from ocr_toolkit.posting.payloads import build_marked_note_body
    from ocr_toolkit.posting.workflow import summary_with_run_marker
    from ocr_toolkit.reporting.metadata import format_token_usage_summary
    from ocr_toolkit.result_contract import parse_result_outcome

    item = {"item_id": "reviewed-module"}
    result = {
        "status": "complete",
        "manifest": {
            "operation": "review",
            "schema_version": "ocr.run-manifest/v1",
            "terminal_state": "complete",
            "coverage": {
                "selected": [item],
                "completed": [item],
                "reused": [],
                "failed": [],
                "waived": [],
            },
        },
        "token_usage": {"input_tokens": 134, "output_tokens": 17, "total_tokens": 151},
    }
    usage = format_token_usage_summary(result)
    assert "151 total" in usage
    summary = summarize_result(
        0,
        0,
        0,
        0,
        token_usage_summary=usage,
        review_model=model,
        reviewed_sha=SHA,
        outcome_status="complete",
        coverage_summary=parse_result_outcome(result).coverage_summary,
        emoji=False,
    )
    return build_marked_note_body(summary_with_run_marker(summary, "a" * 32), write_id="b" * 32)


def partial_note() -> str:
    """Render a partial review with private and public DLP decisions from the real producer."""

    from ocr_toolkit.context.dlp import ForbiddenValue
    from ocr_toolkit.posting.formatting import (
        format_publication_dlp_details,
        publication_dlp_signal,
        summarize_result,
    )
    from ocr_toolkit.posting.payloads import build_marked_note_body
    from ocr_toolkit.result_contract import parse_result_outcome
    from ocr_toolkit.review_runner import _publication_projection

    safe = {"path": "src/module.py", "line": 2, "content": "Check the boundary before indexing."}
    first, second = {"item_id": "reviewed"}, {"item_id": "unfinished"}
    payload = {
        "status": "partial",
        "warnings": [],
        "private_context": PRIVATE_TEXT,
        "comments": [safe, {**safe, "content": PRIVATE_TEXT}],
        "manifest": {
            "schema_version": "ocr.run-manifest/v1",
            "operation": "review",
            "terminal_state": "partial",
            "coverage": {
                "selected": [first, second],
                "completed": [first],
                "reused": [],
                "failed": [{**second, "classification": "timeout"}],
                "waived": [],
            },
        },
    }
    projected, receipt, filtered = _publication_projection(
        payload,
        forbidden=(ForbiddenValue(PRIVATE_TEXT, "forge_discussions"),),
        allowed_tools=frozenset(),
    )
    assert filtered and projected["comments"] == [safe]
    summary = summarize_result(
        1,
        1,
        0,
        0,
        comments=[safe],
        suppressed_count=2,
        outcome_status="partial",
        coverage_summary=parse_result_outcome(payload).coverage_summary,
        publication_dlp_details=format_publication_dlp_details(publication_dlp_signal(receipt)),
        emoji=False,
    )
    assert PRIVATE_TEXT not in summary
    return build_marked_note_body(summary)


def fixture_responses(updated: bool) -> dict[str, Any]:
    from ocr_toolkit.posting.formatting import summarize_result
    from ocr_toolkit.posting.payloads import build_marked_note_body

    failed_note = build_marked_note_body(summarize_result(0, 0, 0, 0, outcome_status="failed"))
    canonical = publisher_note()
    publications = (canonical, partial_note(), failed_note, None)
    project_api = f"projects/{PROJECT}"
    mrs: list[dict[str, Any]] = []
    pipelines: list[dict[str, Any]] = []
    responses: dict[str, Any] = {
        "user": {"id": 12895, "username": "operator", "web_url": f"https://{HOST}/operator"},
        "users": [BOT],
        project_api: {"id": PROJECT, "path_with_namespace": PROJECT_PATH, "archived": False},
        f"{project_api}/merge_requests": mrs,
        f"{project_api}/pipelines": pipelines,
    }
    for index, body in enumerate(publications):
        iid, pipeline_id, note_id = IID + index, 1981 + index, 17533 + index
        merged = updated and index == 0
        mr = {
            "iid": iid,
            "project_id": PROJECT,
            "sha": SHA,
            "source_branch": "synthetic-review",
            "created_at": CREATED,
            "updated_at": MERGED if merged else PUBLISHED,
            "merged_at": MERGED if merged else None,
            "closed_at": None,
            "state": "merged" if merged else "opened",
            "draft": False,
            "changes_count": "1",
            "author": AUTHOR,
            "reviewers": [],
        }
        mrs.append(mr)
        mr_api = f"{project_api}/merge_requests/{iid}"
        pipeline = {
            "id": pipeline_id,
            "sha": SHA,
            "ref": f"refs/merge-requests/{iid}/head",
            "source": "merge_request_event",
            "created_at": CREATED,
            "updated_at": PUBLISHED,
        }
        pipelines.append(pipeline)
        threads = []
        if body is not None:
            note = {
                "id": note_id,
                "author": BOT,
                "created_at": PUBLISHED,
                "updated_at": PUBLISHED,
                "body": body,
                "system": False,
                "resolvable": False,
            }
            threads.append({"id": f"bot-{iid}", "notes": [note]})
            responses[f"{mr_api}/notes/{note_id}/award_emoji"] = (
                [{"id": 871, "user": AUTHOR, "name": "thumbsup"}] if index == 0 else []
            )
        if index == 0 or body is None:
            human_copy = {
                "id": 25742 + index,
                "author": AUTHOR,
                "created_at": PUBLISHED,
                "updated_at": PUBLISHED,
                "body": canonical + "\n" + PRIVATE_TEXT,
                "system": False,
                "resolvable": False,
            }
            threads.append({"id": f"human-{iid}", "notes": [human_copy]})
        job = {
            "id": 77633 + index,
            "name": "open_code_review",
            "status": "success" if body else "failed",
            "pipeline": pipeline,
            "created_at": CREATED,
            "started_at": CREATED,
            "finished_at": PUBLISHED,
            "allow_failure": False,
        }
        if body is None:
            job["failure_reason"] = "script_failure"
        responses.update(
            {
                mr_api: mr,
                f"{mr_api}/discussions": threads,
                f"{mr_api}/versions": [
                    {"id": 82744 + index, "head_commit_sha": SHA, "created_at": CREATED}
                ],
                f"{mr_api}/pipelines": [pipeline],
                f"{mr_api}/approvals": {"approved_by": []},
                f"{project_api}/pipelines/{pipeline_id}/jobs": [job],
                f"{project_api}/pipelines/{pipeline_id}/bridges": [],
            }
        )
    return responses


def fake_glab(args: list[str]) -> None:
    if "graphql" in args:
        assert args[:4] == ["api", "--method", "POST", "graphql"]
        fields = dict(value.split("=", 1) for value in args[5::2])
        assert (
            set(fields) == {"query", "fullPath", "iid"}
            and "mutation" not in fields["query"].lower()
        )
        assert fields["fullPath"] == PROJECT_PATH and IID <= int(fields["iid"]) < IID + 4
        print(
            json.dumps(
                {
                    "data": {
                        "project": {
                            "fullPath": PROJECT_PATH,
                            "mergeRequest": {
                                "iid": fields["iid"],
                                "diffStatsSummary": {
                                    "additions": 2,
                                    "deletions": 1,
                                    "fileCount": 1,
                                },
                                "commitCount": 1,
                                "commitsWithoutMergeCommits": {
                                    "pageInfo": {"hasNextPage": False},
                                    "nodes": [{"author": AUTHOR, "committedDate": CREATED}],
                                },
                            },
                        }
                    }
                }
            )
        )
        return
    assert args[:3] == ["api", "--method", "GET"], args
    url = urlsplit(args[-1])
    endpoint = url.path
    assert args[3:-1] in ([], ["--paginate"]), args
    if endpoint == f"projects/{PROJECT}/variables/OCR_LLM_MODEL":
        assert args[3:-1] == [] and parse_qs(url.query) == {"filter[environment_scope]": ["*"]}
        with Path("project-variable-reads").open("a") as requests:
            requests.write("OCR_LLM_MODEL\n")
    responses = json.loads(Path("gitlab-responses.json").read_text(encoding="utf-8"))
    if endpoint not in responses:
        Path("unexpected-request.txt").write_text(endpoint, encoding="utf-8")
        raise AssertionError(endpoint)
    print(json.dumps(responses[endpoint]))
    if (
        endpoint == f"projects/{PROJECT}/pipelines/1981/jobs"
        and "--paginate" in args
        and parse_qs(url.query).get("include_retried") == ["true"]
    ):
        prior = dict(
            responses[endpoint][0],
            id=77300,
            status="failed",
            failure_reason="script_failure",
            finished_at=CREATED,
        )
        print(json.dumps([prior]))


def deny_report_network(environment: dict[str, str]) -> tuple[Path, Path]:
    hook = Path.cwd() / "offline-site"
    hook.mkdir()
    (hook / "sitecustomize.py").write_text(
        """import sys
from pathlib import Path
root = Path(__file__).parent
def guard(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.gethostbyname",
                 "socket.gethostbyaddr", "socket.sendto", "socket.sendmsg"}:
        (root / "denied").write_text(event)
        raise RuntimeError("telemetry offline network guard")
sys.addaudithook(guard)
(root / "active").touch()
""",
        encoding="utf-8",
    )
    environment["PYTHONPATH"] = str(hook)
    active, denied = hook / "active", hook / "denied"
    probe = subprocess.run(
        [sys.executable, "-c", "import socket; socket.socket().connect(('127.0.0.1', 9))"],
        env=environment,
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert probe.returncode != 0 and "telemetry offline network guard" in probe.stderr
    assert active.is_file() and denied.read_text() == "socket.connect"
    denied.unlink()
    return active, denied


def main(cli: Path) -> None:
    state = Path.cwd() / "telemetry-state"
    launcher = Path.cwd() / "glab"
    launcher.write_text(
        f"#!/bin/sh\nexec {shlex.quote(sys.executable)} -I "
        f'{shlex.quote(str(Path(__file__).resolve()))} --fake-glab "$@"\n',
        encoding="utf-8",
    )
    launcher.chmod(0o700)
    environment = {**os.environ, "PATH": str(Path.cwd())}

    def invoke(action: str, *options: str, state_dir: Path = state, costs: bool = False) -> str:
        flags = [] if costs else ["--no-costs"]
        result = subprocess.run(
            [str(cli), "telemetry", action, "--state-dir", str(state_dir), *flags, *options],
            env=environment,
            capture_output=True,
            text=True,
            timeout=45,
        )
        error = Path("unexpected-request.txt")
        assert not error.exists(), error.read_text(encoding="utf-8")
        assert result.returncode == 0, (action, result.stderr)
        assert MASKED_MODEL not in result.stdout + result.stderr
        return result.stdout.strip()

    for updated in (False, True):
        responses = Path("gitlab-responses.json")
        responses.write_text(json.dumps(fixture_responses(updated)), encoding="utf-8")
        if updated:
            invoke("collect", "--update")
        else:
            invoke(
                "collect", "--from", "2026-11-01", "--to", "2026-11-20", "--project", str(PROJECT)
            )
        snapshot = json.loads((state / "snapshot.json").read_text(encoding="utf-8"))
        assert snapshot["prices"] is None and snapshot["costs_enabled"] is False
        record, partial, failed, no_note = sorted(snapshot["records"], key=lambda r: r["iid"])
        assert record["state"] == ("merged" if updated else "opened")
        assert len(record["runs"]) == 2
        assert [len(r["reviews"]) for r in (record, partial, failed, no_note)] == [1, 1, 1, 0]
        assert partial["reviews"][0]["outcome"] == "incomplete"
        assert failed["reviews"][0]["outcome"] == "failed"
    reads = Path("project-variable-reads")
    assert not reads.exists()
    priced_state = Path.cwd() / "priced-state"
    for cost_state, value, masked in (
        (priced_state, PROJECT_MODEL, False),
        (Path.cwd() / "masked-state", MASKED_MODEL, True),
        (Path.cwd() / "unsafe-state", f"invalid model\n{MASKED_MODEL}", False),
    ):
        admitted = cost_state == priced_state
        payload = fixture_responses(False)
        project = f"projects/{PROJECT}"
        count = 2 if admitted else 1
        payload[f"{project}/merge_requests"] = payload[f"{project}/merge_requests"][:count]
        if admitted:
            discussions = payload[f"{project}/merge_requests/{IID + 1}/discussions"]
            discussions[0]["notes"][0]["body"] = publisher_note(RUN_MODEL)
        payload[f"{project}/variables/OCR_LLM_MODEL"] = {
            "key": "OCR_LLM_MODEL",
            "environment_scope": "*",
            "variable_type": "env_var",
            "protected": False,
            "hidden": False,
            "masked": masked,
            "value": value,
        }
        responses.write_text(json.dumps(payload), encoding="utf-8")
        invoke(
            "collect",
            "--from",
            "2026-11-01",
            "--to",
            "2026-11-20",
            "--project",
            str(PROJECT),
            costs=True,
            state_dir=cost_state,
        )
        raw = (cost_state / "snapshot.json").read_text()
        assert MASKED_MODEL not in raw and environment["OCR_LLM_TOKEN"] not in raw
        snapshot = json.loads(raw)
        (observed,) = snapshot["projects"]
        assert observed.get("cost_model") == (PROJECT_MODEL if admitted else None)
        assert bool(observed.get("cost_model_observed_at")) == admitted
        assert bool(snapshot["prices"]) == admitted
        models = [mr["reviews"][0].get("model") for mr in snapshot["records"]]
        assert models == ([None, RUN_MODEL] if admitted else [None])
    assert reads.read_text().splitlines() == ["OCR_LLM_MODEL"] * 3
    launcher.unlink()
    responses.unlink()
    sealed_snapshot = (state / "snapshot.json").read_bytes()
    assert PRIVATE_TEXT.encode() not in sealed_snapshot
    reports = []
    active, denied = deny_report_network(environment)
    for lang in ("en", "ru"):
        for anonymous in (False, True):
            flags = ("--anonymize",) if anonymous else ()
            active.unlink()
            path = Path(invoke("report", "--lang", lang, *flags))
            assert active.is_file() and not denied.exists()
            assert path.parent == state and re.fullmatch(f"report-{lang}-[a-f0-9]{{32}}", path.name)
            html = (path / "report.html").read_text(encoding="utf-8")
            raw = (path / "report.json").read_text(encoding="utf-8")
            assert PRIVATE_TEXT not in html + raw
            assert f'lang="{lang}"' in html
            links = ReportLinks()
            links.feed(html)
            labels = (
                (
                    "MR с успешной задачей и последним ошибочным результатом",  # noqa: RUF001
                    "Находки, скрытые ревьюером",
                )
                if lang == "ru"
                else (
                    "Mrs with successful job and latest failed result",
                    "Reviewer suppressed findings",
                )
            )
            assert (labels[0], "1") in links.rows
            assert (labels[1], "2") in links.rows
            assert links.title.strip() and bool(re.search(r"[\u0400-\u04ff]", links.title)) == (
                lang == "ru"
            )
            if anonymous:
                for value in (
                    HOST,
                    PROJECT_PATH,
                    MR_URL,
                    SHA,
                    str(PROJECT),
                    *(str(IID + index) for index in range(4)),
                    AUTHOR["username"],
                ):
                    assert str(value) not in html + raw, value
                assert all(not urlsplit(href).netloc for href in links.destinations)
            else:
                assert all(
                    f"{PROJECT_URL}/-/merge_requests/{IID + i}" in links.destinations
                    for i in range(4)
                )
            reports.append(json.loads(raw))
    assert len(list(state.glob("report-*"))) == 4
    assert (state / "snapshot.json").read_bytes() == sealed_snapshot
    check_aggregates(reports)
    for anonymous in (False, True):
        active.unlink()
        flags = ("--anonymize",) if anonymous else ()
        priced = Path(invoke("report", "--lang", "en", *flags, costs=True, state_dir=priced_state))
        assert active.is_file() and not denied.exists()
        check_priced_report(priced, anonymous)


def check_priced_report(path: Path, anonymous: bool) -> None:
    raw = (path / "report.json").read_text(encoding="utf-8")
    html = (path / "report.html").read_text(encoding="utf-8")
    assert PROJECT_MODEL not in html + raw and MASKED_MODEL not in html + raw
    assert "Estimate based on current project configuration" in html
    report = json.loads(raw)
    technical = report["technical"]
    model_labels = {item["model"] for item in technical["models"]}
    assert len(model_labels) == 2 and "unknown" in model_labels
    assert (RUN_MODEL in html + raw) == (not anonymous)
    assert (RUN_MODEL in model_labels) == (not anonymous)
    cost = technical["cost"]
    sourced = cost["by_source"]["current_project_configuration"]
    assert sourced["model_results"] == 1
    assert (
        sourced["pricing_coverage"]
        == sourced["usage_coverage"]
        == {
            "numerator": 1,
            "denominator": 1,
            "value": 1.0,
        }
    )
    assert Decimal(str(sourced["estimated_usd"])) == Decimal("0.168")
    recorded = cost["by_source"]["publication_model"]
    assert recorded["model_results"] == 1
    assert Decimal(str(recorded["estimated_usd"])) == Decimal("0.336")
    assert Decimal(str(cost["estimated_usd"])) == Decimal("0.504")
    assert report["projects"][0]["technical"]["cost"]["cost_model_observed_at"]


def check_aggregates(reports: list[dict[str, Any]]) -> None:
    expected = {"input": 134, "output": 17, "total": 151}
    for report in reports:
        technical = report["technical"]
        assert technical["observed_publications"] == 3
        assert technical["recognized_publications"] == 3
        assert technical["model_results"] == 3
        assert technical["successful_model_results"] == 1
        assert technical["counts"]["tokens"] == expected
        assert technical["counts"]["coverage"] == {
            "selected": 3,
            "completed": 2,
            "reused": 0,
            "failed": 1,
            "waived": 0,
        }
        assert report["delivery"]["attempts"] == 5
        assert report["delivery"]["successful_attempts"] == 3
        assert report["delivery"]["mrs_with_delivered_review"] == 2
        assert report["delivery"]["mrs_with_successful_job_and_latest_failed_result"] == 1
        assert report["delivery"]["failed_created_attempts"]["numerator"] == 2
        assert report["delivery"]["latest_observed_outcomes"] == {
            "complete": 1,
            "incomplete": 1,
            "failed": 1,
        }
        assert technical["summary"]["reviewer_suppressed_findings"] == 2
        dlp = technical["publication_dlp"]
        assert dlp["states"] == {"publication-filtered": 1}
        assert dlp["omitted"]["comments"] == 1
        assert dlp["reasons"]["forbidden"] == 1
        assert dlp["private_sanitization"]["forbidden"] == 1
        assert dlp["sources"]["forge_discussions"] > 0
        assert report["delivery"]["reaction_snapshot"]["author_reactions"] == 1
        for source in ("discussions", "pipelines", "reactions", "approvals", "process"):
            assert report["source_coverage"][source] == {"complete": 4}, source
        assert report["process"]["change_size"]["lines"]["small"] == 4
        assert "cost" not in technical and "prices_at" not in report["scope"]
        assert report["overview"]["lifecycle"] == {
            "opened": 3,
            "merged": 1,
            "closed": 0,
            "locked": 0,
        }
        for section in (
            "overview",
            "technical",
            "delivery",
            "process",
            "trends",
            "adoption",
            "source_coverage",
        ):
            assert report[section] == reports[0][section], section
        (project,) = report["projects"]
        (reference,) = reports[0]["projects"]
        assert {k: v for k, v in project.items() if k != "project"} == {
            k: v for k, v in reference.items() if k != "project"
        }


if __name__ == "__main__":
    if sys.argv[1] == "--fake-glab":
        fake_glab(sys.argv[2:])
    else:
        main(Path(sys.argv[1]))
