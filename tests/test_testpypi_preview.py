"""Regression tests for deterministic TestPyPI and PyPI publication."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts" / "testpypi_preview.py"
PROJECT_ROOT = SCRIPT.parents[1]
WORKFLOW = PROJECT_ROOT / ".github" / "workflows" / "testpypi.yml"
RELEASE_WORKFLOW = PROJECT_ROOT / ".github" / "workflows" / "release.yml"
BUILD_WORKFLOW = PROJECT_ROOT / ".github" / "workflows" / "build.yml"
GITLAB_EXAMPLE = PROJECT_ROOT / "examples" / "gitlab" / "ocr-review.gitlab-ci.yml"
DEPENDENCY_REVIEW_WORKFLOW = PROJECT_ROOT / ".github" / "workflows" / "dependency-review.yml"
REGISTRY_VERIFY = PROJECT_ROOT / "scripts" / "verify_registry_artifacts.sh"


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


def payload(hashes: dict[str, str]) -> dict[str, Any]:
    return {
        "files": [
            {
                "filename": filename,
                "hashes": {"sha256": digest},
                "url": f"https://test-files.pythonhosted.org/packages/synthetic/{filename}",
                "provenance": (
                    "https://test.pypi.org/integrity/open-code-review-toolkit/"
                    f"0.1.0a3/{filename}/provenance"
                ),
            }
            for filename, digest in hashes.items()
        ]
    }


def test_run_number_maps_directly_to_development_version() -> None:
    assert preview.development_version(1, "0.2.0") == "0.2.0.dev1"
    assert preview.development_version(41, "0.2.0") == "0.2.0.dev41"
    with pytest.raises(preview.PreviewError):
        preview.development_version(0, "0.2.0")
    with pytest.raises(preview.PreviewError):
        preview.development_version(1, "0.2.0rc1")
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


def test_stable_release_ignores_existing_development_versions() -> None:
    hashes = expected_hashes("0.2.0")
    development = payload(expected_hashes("0.2.0.dev7"))

    assert preview.classify_index(development, "0.2.0", hashes) == "publish"


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
        item["provenance"] = item["provenance"].replace("test.pypi.org", "pypi.org")
    assert (
        len(preview.artifact_manifest(production, "0.1.0a3", hashes, preview.PYPI_ARTIFACT_HOST))
        == 2
    )
    wrong_hashes = dict(hashes)
    wrong_hashes[next(iter(wrong_hashes))] = "f" * 64
    with pytest.raises(preview.PreviewError):
        preview.artifact_manifest(production, "0.1.0a3", wrong_hashes, preview.PYPI_ARTIFACT_HOST)

    forged_provenance = payload(hashes)
    forged_provenance["files"][0]["provenance"] = (
        "https://test.pypi.org/integrity/open-code-review-toolkit/0.1.0a30/"
        "open_code_review_toolkit-0.1.0a3-py3-none-any.whl/provenance"
    )
    with pytest.raises(preview.PreviewError, match="provenance URL"):
        preview.artifact_manifest(forged_provenance, "0.1.0a3")

    malformed_provenance = payload(hashes)
    malformed_provenance["files"][0]["provenance"] = (
        "https://test.pypi.org:invalid/integrity/open-code-review-toolkit/"
        "0.1.0a3/open_code_review_toolkit-0.1.0a3-py3-none-any.whl/provenance"
    )
    with pytest.raises(preview.PreviewError, match="invalid registry URL"):
        preview.artifact_manifest(malformed_provenance, "0.1.0a3")


def test_workflow_automates_one_idempotent_development_build_per_main_run() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "workflow_dispatch:" not in workflow
    assert "  push:\n    branches: [main]" in workflow
    assert "${GITHUB_RUN_NUMBER}" in workflow
    assert "development-version" in workflow
    assert workflow.count("testpypi-development-distributions") == 3
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
    assert "scripts/install_local_artifact.py" in workflow
    assert "--index-url" not in workflow
    assert "python -m build --no-isolation" in workflow


def test_gitlab_example_uses_pinned_bounded_stable_wheel_install() -> None:
    example = GITLAB_EXAMPLE.read_text(encoding="utf-8")
    wheel_name = "open_code_review_toolkit-0.1.0-py3-none-any.whl"

    assert "releases/download/v0.1.0/SHA256SUMS" in example
    assert wheel_name in example
    assert "--require-hashes --no-deps --only-binary=:all:" in example
    assert "--retries 3 --timeout 10" in example
    assert "--retry 3 --retry-delay 2 --retry-connrefused" in example
    assert "--connect-timeout 10 --max-time 120" in example
    assert "--proto '=https' --proto-redir '=https'" in example
    assert "sha256sum --check --strict" in example
    assert f"pip install --no-deps /tmp/{wheel_name}" in example


def test_production_release_verifies_reviewed_registry_artifacts() -> None:
    workflow = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    verifier = REGISTRY_VERIFY.read_text(encoding="utf-8")

    assert "artifact-hashes.json" in workflow
    assert "SHA256SUMS" in workflow
    assert "SETUPTOOLS_SCM_PRETEND_VERSION" in workflow
    assert "SOURCE_DATE_EPOCH" in workflow
    assert "attestations: true" in workflow
    assert workflow.count("verify_registry_artifacts.sh") == 2
    assert workflow.count('python: ["3.12", "3.13", "3.14"]') == 2
    assert "release_exists=false" in workflow
    assert "authenticated 200,404" in workflow
    assert "release_is_draft=$(jq -r .draft" in workflow
    assert "existing GitHub Release metadata does not match" in workflow
    assert workflow.count("timeout-minutes:") == 8
    assert workflow.count("--max-filesize 10485760") >= 1
    assert "--retry 3 --retry-delay 2 --retry-connrefused" in verifier
    assert "--connect-timeout 10 --max-time 120" in verifier
    assert verifier.count("--max-filesize 10485760") == 2
    assert "--max-filesize 1048576" in verifier
    assert "--proto '=https' --proto-redir '=https'" in verifier
    assert "sha256sum --check --strict" in verifier
    assert "verify_registry_provenance.py" in verifier
    assert "application/vnd.pypi.integrity.v1+json" in verifier
    assert '"${destination}"/*.whl' in verifier
    assert "scripts/install_local_artifact.py" in verifier
    assert "--require-hashes" in (PROJECT_ROOT / "scripts/install_local_artifact.py").read_text(
        encoding="utf-8"
    )
    assert "pip install --no-deps --index-url" not in verifier
    assert '"open-code-review-toolkit==${VERSION}"' not in workflow


def test_distribution_build_is_a_bounded_pull_request_gate() -> None:
    workflow = BUILD_WORKFLOW.read_text(encoding="utf-8")
    pull_request_block = workflow.split("  pull_request:", 1)[1].split("  push:", 1)[0]

    assert "pull_request:" in workflow
    assert "branches: [main]" in workflow
    assert "paths:" not in pull_request_block
    assert '"scripts/install_local_artifact.py"' in workflow
    assert "timeout-minutes: 15" in workflow
    assert "python -m build --no-isolation" in workflow
    assert workflow.count("pip install --no-deps") == 1
    assert "scripts/install_local_artifact.py" in workflow


def test_ci_matrix_covers_supported_python_minors_and_os_boundaries() -> None:
    workflow = (PROJECT_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert workflow.count('python: "3.12"') == 2
    assert workflow.count('python: "3.13"') == 1
    assert workflow.count('python: "3.14"') == 2
    for unsupported in ("3.10", "3.11", "3.15"):
        assert f'python: "{unsupported}"' not in workflow


def test_required_dependency_review_runs_for_every_pull_request() -> None:
    workflow = DEPENDENCY_REVIEW_WORKFLOW.read_text(encoding="utf-8")
    pull_request_block = workflow.split("  pull_request:", 1)[1].split("\n\npermissions:", 1)[0]

    assert "paths:" not in pull_request_block
    assert "paths-ignore:" not in pull_request_block
