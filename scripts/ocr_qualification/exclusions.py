"""Qualify native exclusion metadata without widening selected coverage."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import core, execution, peer

EXPECTED = {
    "result": "passed",
    "reasons": ["binary", "default_path", "deleted", "unsupported_ext"],
    "identity": "path-and-item-id",
    "excluded_fingerprints": False,
    "selected_partition_preserved": True,
    "excluded_selected_overlap": False,
    "range": "explicit-immutable",
}


def validate_exclusions(result: dict[str, Any], expected: dict[str, str]) -> None:
    """Bind every exclusion to selection while preserving the terminal denominator."""
    from ocr_toolkit.result_contract import OcrResultContractError, parse_result_outcome

    try:
        outcome = parse_result_outcome(result)
    except OcrResultContractError as exc:
        raise core.CompatibilityError("exclusion probe lost the terminal partition") from exc
    if outcome.kind != "clean":
        core._fail("excluded files changed the selected terminal outcome")
    manifest = result.get("manifest", {})
    coverage = manifest.get("coverage", {})
    excluded = coverage.get("excluded")
    if not isinstance(excluded, list) or len(excluded) != len(expected):
        core._fail("exclusion probe omitted changed selection exclusions")
    observed: dict[str, str] = {}
    identities: set[str] = set()
    selected = {item["item_id"] for item in coverage["selected"]}
    selected_paths: set[str] = set()
    for item in coverage["selected"]:
        path = item.get("path")
        if not isinstance(path, str) or not path:
            core._fail("exclusion probe lost selected path identity")
        selected_paths.add(path)
    for item in excluded:
        if not isinstance(item, dict):
            core._fail("exclusion probe returned a malformed item")
        identity = item.get("item_id")
        path = item.get("path")
        reason = item.get("exclude_reason")
        if (
            not isinstance(identity, str)
            or not identity
            or identity in identities
            or identity in selected
            or not isinstance(path, str)
            or path in selected_paths
            or path in observed
            or expected.get(path) != reason
            or "fingerprint" in item
        ):
            core._fail("exclusion probe lost selection identity or disjointness")
        identities.add(identity)
        observed[path] = reason
    if observed != expected:
        core._fail("exclusion probe disagrees with preview reasons")


def exclusion_probe(binary: Path, directory: Path) -> dict[str, object]:
    """Cross preview and JSON review using real changed, deleted and binary files."""
    root = directory / "exclusions-probe"
    root.mkdir()
    env = execution._isolated_probe_environment(root / "git-home")
    repo, base, _ = execution._synthetic_repo(
        root,
        env,
        context_files={
            "deleted.py": "removed = True\n",
            "unknown.unsupported": "first\n",
            "example_test.py": "first = True\n",
            "binary.py": "first = True\n",
        },
    )
    (repo / "deleted.py").unlink()
    (repo / "unknown.unsupported").write_text("second\n")
    (repo / "example_test.py").write_text("second = True\n")
    (repo / "binary.py").write_bytes(b"second\x00binary\n")
    execution._run(["git", "add", "-A"], cwd=repo, env=env)
    execution._run(["git", "commit", "-m", "selection exclusions"], cwd=repo, env=env)
    head = execution._run(["git", "rev-parse", "HEAD"], cwd=repo, env=env).strip()
    args = [str(binary), "review", "--from", base, "--to", head, "--format", "json"]
    preview = json.loads(execution._run([*args, "--preview"], cwd=repo, env=env))
    expected = {
        "deleted.py": "deleted",
        "unknown.unsupported": "unsupported_ext",
        "example_test.py": "default_path",
        "binary.py": "binary",
    }
    observed = {
        item["path"]: item.get("exclude_reason")
        for item in preview.get("files", [])
        if item.get("path") in expected
    }
    if observed != expected:
        core._fail(f"exclusion preview fixture disagrees: {observed!r}")
    with peer._stub_gateway() as url:
        env.update(
            OCR_LLM_URL=url,
            OCR_LLM_TOKEN="synthetic-token",
            OCR_LLM_MODEL="synthetic-model",
            OCR_LLM_PROTOCOL="openai",
            OCR_TELEMETRY_ENABLED="false",
        )
        result = json.loads(
            execution._run([*args, "--audience", "agent", "--concurrency", "1"], cwd=repo, env=env)
        )
    from ocr_toolkit.review_range import ReviewRange, admit_native_range

    admit_native_range(result, ReviewRange(base, head))
    validate_exclusions(result, expected)
    return dict(EXPECTED)
