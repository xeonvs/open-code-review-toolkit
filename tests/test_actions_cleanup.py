"""Policy tests for bounded GitHub Actions storage cleanup."""

from __future__ import annotations

import importlib.util
import sys
import urllib.error
from datetime import UTC, datetime
from types import ModuleType

import pytest

from tests.support import PROJECT_ROOT, patched_attr

SCRIPT = PROJECT_ROOT / "scripts" / "actions_cleanup.py"
WORKFLOW = PROJECT_ROOT / ".github" / "workflows" / "actions-maintenance.yml"


def load_script() -> ModuleType:
    """Load the standalone cleanup script as a test module."""

    spec = importlib.util.spec_from_file_location("actions_cleanup_test_module", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def cache(
    cache_id: int,
    key: str,
    *,
    ref: str = "refs/heads/main",
    accessed: str = "2026-08-01T00:00:00Z",
    size: int = 10,
) -> dict[str, object]:
    """Build a synthetic Actions cache record."""

    return {
        "id": cache_id,
        "key": key,
        "ref": ref,
        "last_accessed_at": accessed,
        "size_in_bytes": size,
    }


def test_cache_plan_keeps_only_current_main_uv_platforms_and_gitleaks() -> None:
    module = load_script()
    caches = [
        cache(1, "setup-uv-linux-current", accessed="2026-08-03T00:00:00Z"),
        cache(2, "setup-uv-linux-old", accessed="2026-08-01T00:00:00Z"),
        cache(3, "setup-uv-darwin-current", accessed="2026-08-02T00:00:00Z"),
        cache(4, "setup-uv-linux-pr", ref="refs/pull/42/merge"),
        cache(5, "codeql-overlay-base-database-python"),
        cache(6, "gitleaks-cache-current", accessed="2026-08-03T00:00:00Z"),
        cache(7, "gitleaks-cache-old", accessed="2026-07-31T00:00:00Z"),
        cache(8, "unowned-cache"),
    ]

    plan = module.plan_cache_cleanup(caches)

    assert {candidate.object_id for candidate in plan} == {2, 4, 5, 7}
    assert sum(candidate.size_bytes for candidate in plan) == 40


def test_artifact_plan_uses_seven_day_handoff_window() -> None:
    module = load_script()
    now = datetime(2026, 8, 3, tzinfo=UTC)
    artifacts = [
        {
            "id": 10,
            "name": "old",
            "created_at": "2026-07-20T00:00:00Z",
            "expired": False,
            "size_in_bytes": 100,
        },
        {
            "id": 11,
            "name": "fresh",
            "created_at": "2026-08-01T00:00:00Z",
            "expired": False,
            "size_in_bytes": 200,
        },
        {
            "id": 12,
            "name": "expired",
            "created_at": "2026-08-02T00:00:00Z",
            "expired": True,
            "size_in_bytes": 300,
        },
    ]

    plan = module.plan_artifact_cleanup(artifacts, now)

    assert [candidate.object_id for candidate in plan] == [10, 12]


def test_log_plan_preserves_release_logs_longer_and_all_run_metadata() -> None:
    module = load_script()
    now = datetime(2026, 8, 3, tzinfo=UTC)
    runs = [
        {
            "id": 20,
            "name": "CI",
            "status": "completed",
            "created_at": "2026-07-10T00:00:00Z",
        },
        {
            "id": 21,
            "name": "Release",
            "status": "completed",
            "created_at": "2026-07-10T00:00:00Z",
        },
        {
            "id": 22,
            "name": "Release",
            "status": "completed",
            "created_at": "2026-06-01T00:00:00Z",
        },
        {
            "id": 23,
            "name": "CI",
            "status": "in_progress",
            "created_at": "2026-06-01T00:00:00Z",
        },
    ]

    plan = module.plan_log_cleanup(runs, now, include_all_old=True)
    scheduled_plan = module.plan_log_cleanup(runs, now)

    assert [candidate.object_id for candidate in plan] == [20, 22]
    assert [candidate.object_id for candidate in scheduled_plan] == [20]
    assert all(candidate.kind == "log" and candidate.size_bytes == 0 for candidate in plan)
    assert module.cleanup_url("synthetic/repository", plan[0]).endswith("/actions/runs/20/logs")


def test_delete_is_idempotent_when_log_archive_is_already_absent() -> None:
    module = load_script()

    class MissingOpener:
        def open(self, request: object, *, timeout: int) -> object:
            raise urllib.error.HTTPError(
                "https://api.github.com/synthetic",
                404,
                "not found",
                {},
                None,
            )

    with patched_attr(module, "API_OPENER", MissingOpener()):
        assert not module._delete(
            "https://api.github.com/repos/synthetic/repository/actions/runs/20/logs",
            "synthetic-token",
        )


def test_cleanup_rejects_control_characters_before_logging_or_deletion() -> None:
    module = load_script()

    with pytest.raises(module.CleanupError, match="control-free"):
        module.plan_cache_cleanup([cache(1, "setup-uv-main\x1b[2J")])


def test_workflow_scopes_actions_write_to_the_cleanup_job() -> None:
    """Keep destructive Actions permission out of the workflow-wide default."""

    workflow = WORKFLOW.read_text(encoding="utf-8")
    top_level, jobs = workflow.split("jobs:\n", 1)
    cleanup_header = jobs.split("    steps:\n", 1)[0]

    assert "permissions:\n  contents: read" in top_level
    assert "actions: write" not in top_level
    assert "permissions:\n      actions: write" in cleanup_header
    assert "contents: read" in cleanup_header
