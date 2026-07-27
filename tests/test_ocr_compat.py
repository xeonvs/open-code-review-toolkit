"""Contracts for OCR release discovery and compatibility qualification."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from tests.support import PROJECT_ROOT, patched_attr

SCRIPT = PROJECT_ROOT / "scripts" / "ocr_compat.py"
MANIFEST = PROJECT_ROOT / "compatibility" / "ocr-support.json"


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("ocr_compat_test_module", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def release(version: str, *, body: str = "fix: correct parser bug") -> dict[str, Any]:
    return {
        "tag_name": f"v{version}",
        "draft": False,
        "prerelease": False,
        "body": body,
        "published_at": "2026-07-27T00:00:00Z",
    }


def test_committed_manifest_is_valid_and_has_one_tested_baseline() -> None:
    module = load_script()
    manifest = module.load_json(MANIFEST)

    module.validate_manifest(manifest, PROJECT_ROOT)

    assert manifest["recommended_version"] == "1.7.17"
    assert manifest["monitoring_floor"] == "1.7.17"
    assert [(item["version"], item["status"]) for item in manifest["releases"]] == [
        ("1.7.17", "tested")
    ]


def test_manifest_rejects_recommended_candidate(tmp_path: Path) -> None:
    module = load_script()
    manifest = module.load_json(MANIFEST)
    manifest["releases"][0]["status"] = "observed-candidate"

    with pytest.raises(module.CompatibilityError, match="recommended_version"):
        module.validate_manifest(manifest, PROJECT_ROOT)


def test_manifest_rejects_evidence_hash_mismatch() -> None:
    module = load_script()
    manifest = module.load_json(MANIFEST)
    manifest["releases"][0]["evidence_sha256"] = "0" * 64

    with pytest.raises(module.CompatibilityError, match="evidence hash mismatch"):
        module.validate_manifest(manifest, PROJECT_ROOT)


def test_discovery_filters_known_prerelease_and_old_versions() -> None:
    module = load_script()
    manifest = module.load_json(MANIFEST)
    payload = [
        release("1.7.18"),
        release("1.7.17"),
        {**release("1.7.19"), "prerelease": True},
        release("2.0.0", body="breaking: replace result schema"),
        {"tag_name": "nightly", "draft": False, "prerelease": False},
    ]

    with patched_attr(module, "_request_json", lambda _url: payload):
        unseen = module.discover_unseen(manifest)

    assert [item["tag_name"] for item in unseen] == ["v1.7.18", "v2.0.0"]


def test_discovery_pages_until_the_monitoring_floor() -> None:
    module = load_script()
    manifest = module.load_json(MANIFEST)
    first_page = [release("1.7.18")]
    first_page.extend({"draft": True} for _ in range(module.MAX_RELEASES_PER_PAGE - 1))
    second_page = [release("1.7.17")]
    requested: list[str] = []

    def fake_request(url: str) -> list[dict[str, Any]]:
        requested.append(url)
        return first_page if "page=1" in url else second_page

    with patched_attr(module, "_request_json", fake_request):
        unseen = module.discover_unseen(manifest)

    assert [item["tag_name"] for item in unseen] == ["v1.7.18"]
    assert len(requested) == 2


def test_discovery_fails_when_bounded_pages_do_not_reach_floor() -> None:
    module = load_script()
    manifest = module.load_json(MANIFEST)
    page = [release("1.7.18")]
    page.extend({"draft": True} for _ in range(module.MAX_RELEASES_PER_PAGE - 1))

    with patched_attr(module, "_request_json", lambda _url: page):
        with pytest.raises(module.CompatibilityError, match="monitoring floor"):
            module.discover_unseen(manifest)


def test_automatic_safe_policy_is_conservative() -> None:
    module = load_script()

    automatic, reasons = module.classify_candidate(
        baseline="1.7.17",
        version="1.7.18",
        release_notes="fix: correct comment normalization",
        contracts_passed=True,
    )
    breaking, breaking_reasons = module.classify_candidate(
        baseline="1.7.17",
        version="1.7.18",
        release_notes="fix: change JSON schema for comments",
        contracts_passed=True,
    )
    minor, minor_reasons = module.classify_candidate(
        baseline="1.7.17",
        version="1.8.0",
        release_notes="fix: update documentation",
        contracts_passed=True,
    )
    skipped, skipped_reasons = module.classify_candidate(
        baseline="1.7.17",
        version="1.7.19",
        release_notes="fix: update documentation",
        contracts_passed=True,
    )

    assert automatic == "automatic-safe"
    assert reasons
    assert breaking == "human-review-required"
    assert any("material" in reason for reason in breaking_reasons)
    assert minor == "human-review-required"
    assert any("major/minor" in reason for reason in minor_reasons)
    assert skipped == "human-review-required"
    assert any("newer patch" in reason for reason in skipped_reasons)


def test_checksum_file_rejects_traversal_and_duplicates(tmp_path: Path) -> None:
    module = load_script()
    checksum = tmp_path / "sha256sum.txt"
    checksum.write_text(f"{'a' * 64}  ../escape\n", encoding="utf-8")

    with pytest.raises(module.CompatibilityError, match="unsafe or duplicate"):
        module.parse_checksum_file(checksum)


def test_issue_body_uses_stable_marker_and_no_release_notes() -> None:
    module = load_script()
    evidence = {
        "version": "1.7.18",
        "result": "compatible",
        "classification": "human-review-required",
        "classification_reasons": ["release notes contain a material signal"],
    }

    body = module.render_issue(evidence)

    assert "<!-- ocr-compat-candidate:v1.7.18 -->" in body
    assert "Human checklist" in body
    assert "upstream release notes" in body
    assert "<script" not in body


def test_qualification_requires_exact_supported_asset_matrix() -> None:
    module = load_script()
    candidate = release("1.7.18")
    candidate["assets"] = []

    with pytest.raises(module.CompatibilityError, match="assets are missing"):
        module.release_assets(candidate)


def test_manifest_cli_validate() -> None:
    module = load_script()
    assert module.main(["--manifest", str(MANIFEST), "validate"]) == 0


def test_evidence_json_is_canonical() -> None:
    module = load_script()
    payload = module.canonical_json({"z": 1, "a": 2})
    assert payload == b'{\n  "a": 2,\n  "z": 1\n}\n'
    assert json.loads(payload) == {"a": 2, "z": 1}


def test_prepare_update_changes_only_the_mechanical_support_contract(tmp_path: Path) -> None:
    module = load_script()
    root = tmp_path
    (root / "compatibility" / "evidence").mkdir(parents=True)
    (root / "src" / "ocr_toolkit").mkdir(parents=True)
    (root / "examples" / "gitlab").mkdir(parents=True)
    (root / "docs").mkdir(parents=True)
    (root / "changelog.d").mkdir()
    baseline_evidence = PROJECT_ROOT / "compatibility" / "evidence" / "ocr-1.7.17.json"
    (root / "compatibility" / "evidence" / "ocr-1.7.17.json").write_bytes(
        baseline_evidence.read_bytes()
    )
    manifest_path = root / "compatibility" / "ocr-support.json"
    manifest_path.write_bytes(MANIFEST.read_bytes())
    preflight = root / "src" / "ocr_toolkit" / "preflight.py"
    preflight.write_text('EXPECTED_OCR_VERSION = "1.7.17"\n', encoding="utf-8")
    example = root / "examples" / "gitlab" / "ocr-review.gitlab-ci.yml"
    example.write_text(
        'OCR_VERSION: "v1.7.17"\n'
        'OCR_SHA256: "ab2fae81796a00dda292def8261bec2203d03f3909673c08219e7c5df5f4feee"\n',
        encoding="utf-8",
    )
    (root / "README.md").write_text("OCR 1.7.17 baseline\n", encoding="utf-8")
    (root / "docs" / "gitlab.md").write_text("Pin v1.7.17 in GitLab.\n", encoding="utf-8")
    (root / "docs" / "security.md").write_text("Verify OCR 1.7.17.\n", encoding="utf-8")
    assets = json.loads(baseline_evidence.read_text(encoding="utf-8"))["assets"]
    assets = [dict(asset) for asset in assets]
    for asset in assets:
        asset["sha256"] = "a" * 64
    evidence = {
        "schema_version": 1,
        "upstream_repository": module.UPSTREAM_REPOSITORY,
        "version": "1.7.18",
        "tag": "v1.7.18",
        "published_at": "2026-07-28T00:00:00Z",
        "result": "compatible",
        "classification": "automatic-safe",
        "classification_reasons": ["same-minor patch passed all probes"],
        "assets": assets,
        "contracts": {},
    }
    evidence_path = root / "candidate.json"
    evidence_path.write_bytes(module.canonical_json(evidence))

    changed = module.prepare_update(
        manifest_path=manifest_path,
        evidence=evidence,
        fragment_number=42,
        root=root,
    )

    assert {path.relative_to(root).as_posix() for path in changed} == {
        "compatibility/ocr-support.json",
        "compatibility/evidence/ocr-1.7.18.json",
        "src/ocr_toolkit/preflight.py",
        "examples/gitlab/ocr-review.gitlab-ci.yml",
        "README.md",
        "docs/gitlab.md",
        "docs/security.md",
        "changelog.d/42.feature.md",
    }
    updated = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert updated["recommended_version"] == "1.7.18"
    assert updated["monitoring_floor"] == "1.7.18"
    assert 'EXPECTED_OCR_VERSION = "1.7.18"' in preflight.read_text(encoding="utf-8")
    example_text = example.read_text(encoding="utf-8")
    assert 'OCR_VERSION: "v1.7.18"' in example_text
    assert f'OCR_SHA256: "{"a" * 64}"' in example_text
    assert "1.7.18" in (root / "README.md").read_text(encoding="utf-8")


def test_prepare_update_rejects_human_review_candidate(tmp_path: Path) -> None:
    module = load_script()
    evidence = {"classification": "human-review-required"}

    with pytest.raises(module.CompatibilityError, match="automatic-safe"):
        module.prepare_update(
            manifest_path=MANIFEST,
            evidence=evidence,
            fragment_number=42,
            root=PROJECT_ROOT,
        )
