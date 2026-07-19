"""Regression tests for deterministic automatic TestPyPI previews."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts" / "testpypi_preview.py"
PROJECT_ROOT = SCRIPT.parents[1]
WORKFLOW = PROJECT_ROOT / ".github" / "workflows" / "testpypi.yml"
RELEASE_WORKFLOW = PROJECT_ROOT / ".github" / "workflows" / "release.yml"
GITLAB_EXAMPLE = PROJECT_ROOT / "examples" / "gitlab" / "ocr-review.gitlab-ci.yml"


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("testpypi_preview_script", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


preview = load_script()


def expected_hashes(version: str) -> dict[str, str]:
    return {
        filename: ("a" if kind == "wheel" else "b") * 64
        for filename, kind in preview.expected_filenames(version).items()
    }


def payload(hashes: dict[str, str]) -> dict[str, object]:
    return {
        "files": [
            {
                "filename": filename,
                "hashes": {"sha256": digest},
                "url": f"https://test-files.pythonhosted.org/packages/synthetic/{filename}",
            }
            for filename, digest in hashes.items()
        ]
    }


def test_run_number_maps_directly_to_alpha() -> None:
    assert preview.preview_version(1) == "0.1.0a1"
    assert preview.preview_version(3) == "0.1.0a3"
    assert preview.preview_version(41) == "0.1.0a41"
    with pytest.raises(preview.PreviewError):
        preview.preview_version(0)
    with pytest.raises(preview.PreviewError):
        preview.expected_filenames("0.1.0a3+local")
    assert set(preview.expected_filenames("1.2.3")) == {
        "open_code_review_toolkit-1.2.3-py3-none-any.whl",
        "open_code_review_toolkit-1.2.3.tar.gz",
    }


def test_missing_release_requires_publish() -> None:
    hashes = expected_hashes("0.1.0a3")
    assert preview.classify_index({"files": []}, "0.1.0a3", hashes) == "publish"


def test_matching_release_is_idempotent() -> None:
    hashes = expected_hashes("0.1.0a3")
    assert preview.classify_index(payload(hashes), "0.1.0a3", hashes) == "already-published"


def test_neighbouring_alpha_is_not_mistaken_for_requested_version() -> None:
    hashes = expected_hashes("0.1.0a3")
    neighbouring = payload(expected_hashes("0.1.0a30"))
    assert preview.classify_index(neighbouring, "0.1.0a3", hashes) == "publish"


@pytest.mark.parametrize(
    "published,local",
    [
        ("partial", "exact"),
        ("mismatch", "exact"),
        ("exact", "partial"),
    ],
)
def test_conflicting_release_fails_closed(published: str, local: str) -> None:
    hashes = expected_hashes("0.1.0a3")
    published_hashes = dict(hashes)
    local_hashes = dict(hashes)
    if published == "partial":
        published_hashes.pop(next(iter(published_hashes)))
    elif published == "mismatch":
        published_hashes[next(iter(published_hashes))] = "different"
    if local == "partial":
        local_hashes.pop(next(iter(local_hashes)))

    with pytest.raises(preview.PreviewError):
        preview.classify_index(payload(published_hashes), "0.1.0a3", local_hashes)


def test_artifact_manifest_accepts_only_complete_trusted_release() -> None:
    hashes = expected_hashes("0.1.0a3")
    manifest = preview.artifact_manifest(payload(hashes), "0.1.0a3")
    assert {item["filename"] for item in manifest} == set(hashes)

    untrusted = payload(hashes)
    untrusted["files"][0]["url"] = "https://other.example/package.whl"
    with pytest.raises(preview.PreviewError):
        preview.artifact_manifest(untrusted, "0.1.0a3")

    injected = payload(hashes)
    injected["files"][0]["url"] += "%0A--output%20/tmp/other"
    with pytest.raises(preview.PreviewError):
        preview.artifact_manifest(injected, "0.1.0a3")

    production = payload(hashes)
    for item in production["files"]:
        item["url"] = item["url"].replace("test-files.pythonhosted.org", "files.pythonhosted.org")
    assert (
        len(preview.artifact_manifest(production, "0.1.0a3", hashes, preview.PYPI_ARTIFACT_HOST))
        == 2
    )
    wrong_hashes = dict(hashes)
    wrong_hashes[next(iter(wrong_hashes))] = "f" * 64
    with pytest.raises(preview.PreviewError):
        preview.artifact_manifest(production, "0.1.0a3", wrong_hashes, preview.PYPI_ARTIFACT_HOST)


def test_workflow_automates_one_idempotent_alpha_per_main_run() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "workflow_dispatch:" not in workflow
    assert "  push:\n    branches: [main]" in workflow
    assert "${GITHUB_RUN_NUMBER}" in workflow
    assert workflow.count("testpypi-preview-distributions") == 3
    assert "overwrite: true" in workflow
    assert "needs.build.outputs.publish == 'true'" in workflow
    assert "needs.publish.result == 'skipped'" in workflow


def test_workflow_bounds_and_verifies_every_testpypi_download() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    bounded_curl = "--retry 3 --retry-delay 2 --retry-connrefused"

    assert workflow.count(bounded_curl) == 3
    assert workflow.count("--connect-timeout 10 --max-time 120") == 3
    assert workflow.count("--proto '=https' --proto-redir '=https'") == 3
    assert "sha256sum --check --strict" in workflow
    assert "pip install --no-deps /tmp/testpypi-artifacts/*.whl" in workflow
    assert "pip install --no-deps /tmp/testpypi-artifacts/*.tar.gz" in workflow
    assert "--index-url" not in workflow
    assert "python -m build --no-isolation" in workflow


def test_gitlab_example_uses_pinned_bounded_local_wheel_install() -> None:
    example = GITLAB_EXAMPLE.read_text(encoding="utf-8")
    wheel_name = "open_code_review_toolkit-0.1.0a2-py3-none-any.whl"

    assert "https://test-files.pythonhosted.org/packages/" in example
    assert wheel_name in example
    assert (
        "OCR_TOOLKIT_WHEEL_SHA256: "
        '"d118ba5ecc5cb5027df11588bede6428be87771b87b82c47ccc7f8a08d3de6d8"' in example
    )
    assert "--retry 3 --retry-delay 2 --retry-connrefused" in example
    assert "--connect-timeout 10 --max-time 120" in example
    assert "--proto '=https' --proto-redir '=https'" in example
    assert "sha256sum --check --strict" in example
    assert f"pip install --no-deps /tmp/{wheel_name}" in example


def test_production_release_verifies_reviewed_registry_artifacts() -> None:
    workflow = RELEASE_WORKFLOW.read_text(encoding="utf-8")

    assert "artifact-hashes.json" in workflow
    assert workflow.count("--hashes-json artifact-hashes.json") == 4
    assert workflow.count("--retry 3 --retry-delay 2 --retry-connrefused") == 4
    assert workflow.count("--connect-timeout 10 --max-time 120") == 4
    assert workflow.count("--proto '=https' --proto-redir '=https'") == 4
    assert workflow.count("sha256sum --check --strict") == 2
    assert "pip install --no-deps /tmp/testpypi-artifacts/*.whl" in workflow
    assert "pip install --no-deps /tmp/testpypi-artifacts/*.tar.gz" in workflow
    assert "pip install --no-deps /tmp/pypi-artifacts/*.whl" in workflow
    assert "pip install --no-deps /tmp/pypi-artifacts/*.tar.gz" in workflow
    assert "pip install --no-deps --index-url" not in workflow
    assert '"open-code-review-toolkit==${VERSION}"' not in workflow
