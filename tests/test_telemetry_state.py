"""Real privacy, failure recovery, catalog and locale boundaries for local telemetry."""

import os
from http.client import IncompleteRead

import pytest

from ocr_toolkit.telemetry import prices
from ocr_toolkit.telemetry.cli import _language
from ocr_toolkit.telemetry.metrics.cost import estimated_cost
from ocr_toolkit.telemetry.state import (
    SNAPSHOT,
    TelemetryError,
    private_directory,
    read_snapshot,
    save_report,
    save_snapshot,
)


def _snapshot():
    return {
        "scope": {
            "start": "2026-11-01",
            "end": "2026-11-23",
            "discovery": "explicit",
            "bot": "mr.bot",
            "bot_id": 1,
            "host": "git.example",
            "base_path": "",
            "job_names": ["open_code_review"],
            "updated_at": "2026-11-23T00:00:00Z",
        },
        "rolling_end": False,
        "costs_enabled": False,
        "projects": [],
        "records": [],
    }


def test_snapshot_and_render_are_published_atomically(tmp_path, monkeypatch):
    root = tmp_path.resolve() / "private"
    initial = _snapshot()
    with private_directory(root, create=True) as fd:
        save_snapshot(fd, initial)
        original = read_snapshot(fd)
        with pytest.raises(TelemetryError, match="busy"), private_directory(root, create=False):
            pass
        name = save_report(fd, "<html></html>", {}, "ru")
        assert all(p.stat().st_mode & 0o777 == 0o600 for p in (root / name).iterdir())
        assert (root / name).stat().st_mode & 0o777 == 0o700

        def fail(*args, **kwargs):
            raise OSError("simulated interruption")

        monkeypatch.setattr(os, "replace", fail)
        with pytest.raises(OSError):
            save_snapshot(fd, {**initial, "extra": 1})
        assert read_snapshot(fd) == original
        monkeypatch.setattr(os, "rename", fail)
        with pytest.raises(OSError):
            save_report(fd, "<html></html>", {}, "ru")
        assert set(os.listdir(fd)) == {name, SNAPSHOT}


def test_private_directory_refuses_git_worktree_ancestors_and_links(tmp_path):
    root = tmp_path.resolve()
    work = root / "work"
    work.mkdir()
    (work / ".git").write_text("gitdir: fixture")
    link = root / "link"
    link.symlink_to(work, target_is_directory=True)
    for path in (work / "reports", link / "reports", root / "other" / ".." / "work"):
        with pytest.raises((OSError, ValueError)), private_directory(path, create=True):
            pass
    assert not (work / "reports").exists()
    with pytest.raises(TelemetryError, match="worktree"), private_directory(work, create=False):
        pass
    private_target = root / "private-target"
    private_target.mkdir(mode=0o700)
    private_link = root / "private-link"
    private_link.symlink_to(private_target, target_is_directory=True)
    with (
        pytest.raises((OSError, ValueError)),
        private_directory(private_link / "reports", create=True),
    ):
        pass
    assert not (private_target / "reports").exists()
    shared = root / "shared"
    shared.mkdir()
    shared.chmod(0o755)
    with pytest.raises(TelemetryError, match="0700"), private_directory(shared, create=True):
        pass


def test_render_rolls_back_if_staging_open_fails(tmp_path, monkeypatch):
    with private_directory(tmp_path.resolve() / "state", create=True) as fd:

        def unavailable(*args, **kwargs):
            raise OSError("descriptor unavailable")

        monkeypatch.setattr(os, "open", unavailable)
        with pytest.raises(OSError, match="descriptor unavailable"):
            save_report(fd, "content", {}, "en")
        assert os.listdir(fd) == []


@pytest.mark.parametrize("kind", ["hardlink", "symlink", "shared"])
def test_reject_alias_to_existing_snapshot(tmp_path, kind):
    root = tmp_path.resolve()
    target = root / "target"
    target.write_text("private placeholder")
    target.chmod(0o600)
    directory = root / "state"
    with private_directory(directory, create=True) as fd:
        path = directory / SNAPSHOT
        if kind == "hardlink":
            os.link(target, path)
        elif kind == "symlink":
            path.symlink_to(target)
        else:
            path.write_text("shared")
            path.chmod(0o644)
        with pytest.raises((OSError, TelemetryError)):
            read_snapshot(fd)
        with pytest.raises(TelemetryError):
            save_snapshot(fd, {})
    assert target.read_text() == "private placeholder"


def test_catalog_only_keeps_valid_numeric_rates_and_reuses_provider(monkeypatch):
    for name in tuple(os.environ):
        if name.startswith("OCR_"):
            monkeypatch.delenv(name)
    assert prices.capture_prices() == (None, None)
    monkeypatch.setenv("OCR_LLM_URL", "https://gateway.example/v1/chat/completions")
    monkeypatch.setenv("OCR_LLM_TOKEN", "synthetic-value")
    rates = {"prompt": "0.002", "input_cache_read": "0.0001", "completion": "0.03"}

    def catalog(url, headers):
        assert url == "https://gateway.example/v1/models"
        assert headers == {"Authorization": "Bearer synthetic-value"}
        return {
            "data": [
                None,
                {"id": "missing"},
                {"id": "invalid", "pricing": {**rates, "prompt": "NaN"}},
                {"id": "model", "pricing": {**rates, "private": "private value"}},
                {"id": "provider/legacy/model+variant@stable", "pricing": rates},
            ]
        }

    monkeypatch.setattr(prices, "_request_json", catalog)
    result, captured = prices.capture_prices()
    assert result == {"model": rates, "provider/legacy/model+variant@stable": rates} and captured

    def truncated(*args):
        raise IncompleteRead(b"upstream private text")

    monkeypatch.setattr(prices, "_request_json", truncated)
    assert prices.capture_prices() == (None, None)
    monkeypatch.setattr(prices, "_request_json", lambda *args: {})
    assert prices.capture_prices() == (None, None)


def test_optional_cache_rate_requires_zero_cached_usage():
    catalog = prices.normalized_prices(
        {"data": [{"id": "standard", "pricing": {"prompt": "1", "completion": "2"}}]}
    )
    usage = {"model": "standard", "tokens": {"input": 2, "output": 3, "cached": 0}}
    assert estimated_cost(usage, catalog) == 8
    usage["tokens"]["cached"] = 1
    assert estimated_cost(usage, catalog) is None


def test_catalog_protocol_failure_preserves_previous_snapshot_prices(tmp_path, monkeypatch, capsys):
    import argparse

    from ocr_toolkit.telemetry import cli, collection

    parser = argparse.ArgumentParser()
    cli.configure_parser(parser)
    state = tmp_path.resolve() / "state"
    initial = _snapshot()
    initial.update(
        costs_enabled=True,
        prices={"model": {"prompt": "1", "completion": "2"}},
        prices_at="2026-11-01T00:00:00Z",
    )
    with private_directory(state, create=True) as fd:
        save_snapshot(fd, initial)
    observations = _snapshot()
    observations["projects"] = [{"id": 1}]
    observations["records"] = [
        {
            "project_id": 1,
            "iid": 1,
            "runs": [],
            "reviews": [{"model": "model"}],
            "checkpoints": [],
            "discussions": [],
            "revisions": [],
            "process": {},
            "completeness": {},
            "correlation": {},
            "reactions": {},
        }
    ]
    monkeypatch.setattr(collection, "collect", lambda **kw: observations)
    monkeypatch.setenv("OCR_LLM_URL", "https://gateway.example/v1/chat/completions")
    monkeypatch.setenv("OCR_LLM_TOKEN", "fixture")

    def truncated(*args):
        raise IncompleteRead(b"upstream private text")

    monkeypatch.setattr(prices, "_request_json", truncated)
    args = parser.parse_args(["collect", "--update", "--state-dir", str(state)])
    assert cli.run(args) == 0
    with private_directory(state, create=False) as fd:
        updated = read_snapshot(fd)
    assert updated["prices"] == initial["prices"] and updated["prices_at"] == initial["prices_at"]
    assert "keeping the dated snapshot" in capsys.readouterr().err
    observations["records"][0]["reviews"] = [{"tokens": {"total": 7}}]
    monkeypatch.setattr(cli, "capture_prices", lambda: pytest.fail("no observed model"))
    assert cli.run(args) == 0


def test_owner_write_mask_and_scope_checked_before_snapshot_replacement(tmp_path):
    with private_directory(tmp_path.resolve() / "state", create=True) as fd:
        previous = os.umask(0o200)
        try:
            snapshot = _snapshot()
            snapshot["scope"]["host"] = ".".join(["a" * 62] * 4) + ":8443"
            save_snapshot(fd, snapshot)
            assert read_snapshot(fd)["scope"] == snapshot["scope"]
            with pytest.raises(TelemetryError):
                save_snapshot(fd, {**snapshot, "rolling_end": "true"})
            assert read_snapshot(fd)["rolling_end"] is False
        finally:
            os.umask(previous)


def test_report_language_cli_precedes_environment(monkeypatch, capsys):
    for value in ("Russian", "ru-RU"):
        monkeypatch.setenv("OCR_REVIEW_LANGUAGE", value)
        assert _language(None) == "ru"
        assert _language(value) == "ru"
        assert _language("en") == "en"
    monkeypatch.setenv("OCR_REVIEW_LANGUAGE", "de-DE")
    assert _language(None) == "en" and "English" in capsys.readouterr().err


@pytest.mark.parametrize(
    "corruption",
    [
        "duplicate",
        "unknown_project",
        "repeated_mr",
        "invalid_number",
        "invalid_date",
        "rolling_end",
        "discovery",
    ],
)
def test_snapshot_scope_checked_before_use(corruption):
    import json

    from ocr_toolkit.telemetry.snapshot import SCHEMA, read_document

    value = {
        **_snapshot(),
        "schema": SCHEMA,
        "projects": [{"id": 1}],
        "records": [],
    }
    if corruption == "duplicate":
        raw = json.dumps(value).replace('"schema":', '"schema":null,"schema":')
    elif corruption == "invalid_number":
        raw = json.dumps({**value, "bad": float("nan")})
    elif corruption == "invalid_date":
        value["scope"]["start"] = "2026-11-24"
        raw = json.dumps(value)
    elif corruption == "rolling_end":
        value["rolling_end"] = "false"
        raw = json.dumps(value)
    elif corruption == "discovery":
        value["scope"]["discovery"] = []
        raw = json.dumps(value)
    else:
        record = {"project_id": 1 if corruption == "repeated_mr" else 2, "iid": 7}
        value["records"] = [record, record] if corruption == "repeated_mr" else [record]
        raw = json.dumps(value)
    with pytest.raises(TelemetryError):
        read_document(raw.encode())


@pytest.mark.parametrize(
    "invalid_model",
    ["https://models.example.invalid/openai/synthetic-model", "glpat-not-a-key"],
)
def test_snapshot_rejects_unsafe_project_model_without_replacing_saved_state(
    tmp_path, invalid_model
):
    """Project model readback enforces the review model grammar with safe diagnostics."""

    project = {
        "id": 1,
        "cost_model": "openai/synthetic-model",
        "cost_model_observed_at": "2026-11-23T00:00:00Z",
    }
    snapshot = {**_snapshot(), "projects": [project], "costs_enabled": True}
    with private_directory(tmp_path.resolve() / "state", create=True) as fd:
        save_snapshot(fd, snapshot)
        baseline = read_snapshot(fd)
        invalid = {**snapshot, "projects": [{**project, "cost_model": invalid_model}]}
        with pytest.raises(TelemetryError, match="Invalid project cost model observation") as error:
            save_snapshot(fd, invalid)
        assert invalid_model not in str(error.value)
        assert read_snapshot(fd) == baseline
