"""Contracts for OCR release discovery and compatibility qualification."""

from __future__ import annotations

import importlib.util
import json
import sys
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from tests.support import PROJECT_ROOT, patched_attr, patched_env

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


def test_committed_manifest_is_valid_and_has_recommended_tested_baseline() -> None:
    module = load_script()
    manifest = module.load_json(MANIFEST)

    module.validate_manifest(manifest, PROJECT_ROOT)

    assert manifest["recommended_version"] == "1.9.1"
    assert manifest["monitoring_floor"] == "1.9.1"
    assert [(item["version"], item["status"]) for item in manifest["releases"]] == [
        ("1.7.17", "tested"),
        ("1.8.0", "tested"),
        ("1.8.1", "tested"),
        ("1.8.2", "tested"),
        ("1.8.3", "tested"),
        ("1.8.4", "tested"),
        ("1.8.5", "tested"),
        ("1.8.6", "tested"),
        ("1.8.7", "tested"),
        ("1.8.8", "tested"),
        ("1.8.9", "tested"),
        ("1.8.10", "tested"),
        ("1.9.0", "tested"),
        ("1.9.1", "tested"),
    ]


def test_manifest_rejects_recommended_candidate(tmp_path: Path) -> None:
    module = load_script()
    manifest = module.load_json(MANIFEST)
    recommended = next(
        item for item in manifest["releases"] if item["version"] == manifest["recommended_version"]
    )
    recommended["status"] = "observed-candidate"

    with pytest.raises(module.CompatibilityError, match="recommended_version"):
        module.validate_manifest(manifest, PROJECT_ROOT)


def test_manifest_rejects_evidence_hash_mismatch() -> None:
    module = load_script()
    manifest = module.load_json(MANIFEST)
    manifest["releases"][0]["evidence_sha256"] = "0" * 64

    with pytest.raises(module.CompatibilityError, match="evidence hash mismatch"):
        module.validate_manifest(manifest, PROJECT_ROOT)


def test_manifest_rejects_floor_above_recommended() -> None:
    module = load_script()
    manifest = module.load_json(MANIFEST)
    manifest["monitoring_floor"] = "2.0.0"

    with pytest.raises(module.CompatibilityError, match="monitoring_floor"):
        module.validate_manifest(manifest, PROJECT_ROOT)


def test_manifest_rejects_assets_that_differ_from_evidence() -> None:
    module = load_script()
    manifest = module.load_json(MANIFEST)
    manifest["releases"][0]["assets"][0]["sha256"] = "f" * 64

    with pytest.raises(module.CompatibilityError, match="assets disagree"):
        module.validate_manifest(manifest, PROJECT_ROOT)


def test_discovery_filters_known_prerelease_and_old_versions() -> None:
    module = load_script()
    manifest = module.load_json(MANIFEST)
    payload = [
        release("1.8.1"),
        release("1.8.0"),
        {**release("1.8.2"), "prerelease": True},
        release("2.0.0", body="breaking: replace result schema"),
        {"tag_name": "nightly", "draft": False, "prerelease": False},
    ]

    with patched_attr(module, "_request_json", lambda _url: payload):
        unseen = module.discover_unseen(manifest)

    assert [item["tag_name"] for item in unseen] == ["v2.0.0"]


def test_discovery_pages_until_the_monitoring_floor() -> None:
    module = load_script()
    manifest = module.load_json(MANIFEST)
    first_page = [release("1.9.2")]
    first_page.extend({"draft": True} for _ in range(module.MAX_RELEASES_PER_PAGE - 1))
    second_page = [release("1.9.1")]
    requested: list[str] = []

    def fake_request(url: str) -> list[dict[str, Any]]:
        requested.append(url)
        return first_page if "page=1" in url else second_page

    with patched_attr(module, "_request_json", fake_request):
        unseen = module.discover_unseen(manifest)

    assert [item["tag_name"] for item in unseen] == ["v1.9.2"]
    assert len(requested) == 2


def test_discovery_fails_when_bounded_pages_do_not_reach_floor() -> None:
    module = load_script()
    manifest = module.load_json(MANIFEST)
    page = [release("1.9.2")]
    page.extend({"draft": True} for _ in range(module.MAX_RELEASES_PER_PAGE - 1))

    with patched_attr(module, "_request_json", lambda _url: page):
        with pytest.raises(module.CompatibilityError, match="monitoring floor"):
            module.discover_unseen(manifest)


def test_qualification_matrix_uses_adjacent_predecessors() -> None:
    module = load_script()
    manifest = module.load_json(MANIFEST)
    manifest["recommended_version"] = "1.8.6"

    matrix = module.qualification_matrix(manifest, [release("1.8.8"), release("1.8.7")])

    assert matrix == {
        "include": [
            {
                "comparison_version": "1.8.6",
                "tag": "v1.8.7",
                "tested_baseline_version": "1.8.6",
            },
            {
                "comparison_version": "1.8.7",
                "tag": "v1.8.8",
                "tested_baseline_version": "1.8.6",
            },
        ]
    }


def test_qualification_matrix_preserves_a_release_gap_for_human_review() -> None:
    module = load_script()
    manifest = module.load_json(MANIFEST)
    manifest["recommended_version"] = "1.8.6"

    matrix = module.qualification_matrix(manifest, [release("1.8.8")])

    assert matrix["include"][0]["comparison_version"] == "1.8.6"


def test_qualification_matrix_accepts_the_next_manual_patch() -> None:
    module = load_script()
    manifest = module.load_json(MANIFEST)

    matrix = module.qualification_matrix(manifest, [release("1.9.2")])

    assert matrix == {
        "include": [
            {
                "comparison_version": "1.9.1",
                "tag": "v1.9.2",
                "tested_baseline_version": "1.9.1",
            }
        ]
    }


def test_qualification_matrix_rejects_duplicate_releases() -> None:
    module = load_script()
    manifest = module.load_json(MANIFEST)

    with pytest.raises(module.CompatibilityError, match="duplicate version"):
        module.qualification_matrix(manifest, [release("1.8.9"), release("1.8.9")])


def test_automatic_safe_policy_is_conservative() -> None:
    module = load_script()

    automatic, reasons = module.classify_candidate(
        comparison_version="1.7.17",
        version="1.7.18",
        release_notes="fix: correct comment normalization",
        contracts_passed=True,
    )
    breaking, breaking_reasons = module.classify_candidate(
        comparison_version="1.7.17",
        version="1.7.18",
        release_notes="fix: change JSON schema for comments",
        contracts_passed=True,
    )
    minor, minor_reasons = module.classify_candidate(
        comparison_version="1.7.17",
        version="1.8.0",
        release_notes="fix: update documentation",
        contracts_passed=True,
    )
    skipped, skipped_reasons = module.classify_candidate(
        comparison_version="1.7.17",
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


@pytest.mark.parametrize(
    ("previous", "candidate", "expected"),
    [
        ((1, 8, 10), (1, 8, 11), "patch"),
        ((1, 8, 10), (1, 9, 0), "minor"),
        ((1, 9, 9), (2, 0, 0), "major"),
        ((1, 8, 10), (1, 9, 1), None),
        ((1, 8, 10), (1, 10, 0), None),
        ((1, 8, 10), (2, 0, 1), None),
        ((1, 8, 10), (1, 8, 10), None),
    ],
)
def test_release_transition_accepts_only_adjacent_semver_steps(
    previous: tuple[int, int, int],
    candidate: tuple[int, int, int],
    expected: str | None,
) -> None:
    module = load_script()

    assert module._release_transition(previous, candidate) == expected


def test_checksum_file_rejects_traversal_and_duplicates(tmp_path: Path) -> None:
    module = load_script()
    checksum = tmp_path / "sha256sum.txt"
    checksum.write_text(f"{'a' * 64}  ../escape\n", encoding="utf-8")

    with pytest.raises(module.CompatibilityError, match="unsafe or duplicate"):
        module.parse_checksum_file(checksum)


def test_probe_environment_ignores_operator_ocr_and_git_configuration(
    tmp_path: Path,
) -> None:
    module = load_script()
    home = tmp_path / "probe-home"

    with patched_env(
        GIT_DIR="/tmp/untrusted-git-dir",
        GIT_CONFIG_COUNT="1",
        OCR_CONFIG_PATH="/tmp/operator-config.json",
        OCR_LLM_PROVIDER="operator-provider",
    ):
        env = module._isolated_probe_environment(home)

    assert env["HOME"] == str(home)
    assert env["XDG_CONFIG_HOME"] == str(home / ".config")
    assert env["GIT_CONFIG_GLOBAL"] == module.os.devnull
    assert env["GIT_CONFIG_SYSTEM"] == module.os.devnull
    assert env["PATH"].split(module.os.pathsep)[0] == str(
        Path(module.shutil.which("git") or "").parent
    )
    assert env["TMPDIR"] == str(home / "tmp")
    assert not any(key.startswith("OCR_") for key in env)
    assert not any(
        key.startswith("GIT_")
        for key in env
        if key not in {"GIT_CONFIG_GLOBAL", "GIT_CONFIG_SYSTEM"}
    )
    assert home.stat().st_mode & 0o777 == 0o700
    assert (home / "tmp").stat().st_mode & 0o777 == 0o700


def test_issue_body_uses_stable_marker_and_safe_release_changes() -> None:
    module = load_script()
    evidence = {
        "version": "1.7.18",
        "result": "compatible",
        "classification": "human-review-required",
        "classification_reasons": ["release notes contain a material signal"],
        "comparison_version": "1.7.17",
        "tested_baseline_version": "1.7.16",
        "release_changes": module.release_changes_excerpt(
            "fix parser output\n<script>alert(1)</script>\n```escape"
        ),
    }

    body = module.render_issue(evidence)

    assert "<!-- ocr-compat-candidate:v1.7.18 -->" in body
    assert "Human checklist" in body
    assert "Upstream release changes" in body
    assert "fix parser output" in body
    assert "<script" not in body
    assert "```escape" not in body
    assert "/compare/v1.7.17...v1.7.18" in body
    assert "current tested baseline: `v1.7.16`" in body


def test_optional_capabilities_validate_additive_llm_identity() -> None:
    module = load_script()

    capabilities = module.detect_optional_capabilities(
        "review --model MODEL --provider PROVIDER",
        {"llm": {"model": "synthetic-model", "provider": "synthetic-provider"}},
    )

    assert capabilities == [
        "llm_result_identity",
        "per_run_model_override",
        "per_run_provider_override",
    ]
    with pytest.raises(module.CompatibilityError, match="LLM model identity"):
        module.detect_optional_capabilities("review", {"llm": {"model": ""}})


def test_complete_chain_requires_every_release_to_be_automatic_safe() -> None:
    module = load_script()
    manifest = module.load_json(MANIFEST)
    manifest["recommended_version"] = "1.8.6"

    def evidence(version: str, comparison: str, classification: str) -> dict[str, Any]:
        return {
            "schema_version": 2,
            "version": version,
            "result": "compatible",
            "classification": classification,
            "comparison_version": comparison,
            "tested_baseline_version": "1.8.6",
        }

    automatic = module.assess_automatic_chain(
        manifest,
        [
            evidence("1.8.8", "1.8.7", "automatic-safe"),
            evidence("1.8.7", "1.8.6", "automatic-safe"),
        ],
    )
    mixed = module.assess_automatic_chain(
        manifest,
        [
            evidence("1.8.7", "1.8.6", "human-review-required"),
            evidence("1.8.8", "1.8.7", "automatic-safe"),
        ],
    )
    gapped = module.assess_automatic_chain(
        manifest,
        [evidence("1.8.8", "1.8.6", "human-review-required")],
    )

    assert automatic["classification"] == "automatic-safe"
    assert automatic["target_version"] == "1.8.8"
    assert mixed["classification"] == "human-review-required"
    assert gapped["classification"] == "human-review-required"
    assert gapped["automatic_blockers"] == ["non-contiguous release sequence"]


def test_release_changes_excerpt_is_bounded() -> None:
    module = load_script()

    excerpt = module.release_changes_excerpt("x" * (module.MAX_RELEASE_CHANGES_CHARS + 10))

    assert len(excerpt) <= module.MAX_RELEASE_CHANGES_CHARS + 40
    assert excerpt.endswith("[release notes excerpt truncated]")


def test_exact_issue_lookup_uses_direct_bounded_listing() -> None:
    module = load_script()
    marker = "<!-- ocr-compat-candidate:v1.8.4 -->"
    requested: list[str] = []

    def request(url: str, **_kwargs: Any) -> list[dict[str, Any]]:
        requested.append(url)
        return [
            {"number": 47, "body": "other"},
            {"number": 48, "body": marker},
            {"number": 99, "body": marker, "pull_request": {}},
        ]

    with patched_attr(module, "_issue_api_request", request):
        assert module.find_qualification_issue("synthetic/repository", marker) == 48

    assert requested == [
        "https://api.github.com/repos/synthetic/repository/issues?state=all&per_page=100&page=1"
    ]


def test_exact_issue_lookup_fails_closed_on_existing_duplicates() -> None:
    module = load_script()
    marker = "<!-- ocr-compat-candidate:v1.8.4 -->"

    with (
        patched_attr(
            module,
            "_issue_api_request",
            lambda _url, **_kwargs: [
                {"number": 47, "body": marker},
                {"number": 48, "body": marker},
            ],
        ),
        pytest.raises(module.CompatibilityError, match="#47, #48"),
    ):
        module.find_qualification_issue("synthetic/repository", marker)


def test_exact_issue_lookup_ignores_closed_labeled_duplicate_archives() -> None:
    module = load_script()
    marker = "<!-- ocr-compat-candidate:v1.8.4 -->"

    with patched_attr(
        module,
        "_issue_api_request",
        lambda _url, **_kwargs: [
            {
                "number": 47,
                "body": marker,
                "state": "closed",
                "labels": [{"name": "duplicate"}, {"name": "dependencies"}],
            },
            {"number": 48, "body": marker, "state": "open", "labels": []},
        ],
    ):
        assert module.find_qualification_issue("synthetic/repository", marker) == 48


def test_issue_upsert_updates_the_canonical_issue() -> None:
    module = load_script()
    calls: list[tuple[str, str, dict[str, Any] | None]] = []
    evidence = {
        "version": "1.8.4",
        "result": "compatible",
        "classification": "automatic-safe",
        "classification_reasons": ["maintenance-only"],
        "release_changes": "fix: synthetic parser correction",
    }

    def request(
        url: str, *, method: str = "GET", payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        calls.append((url, method, payload))
        return {"number": 48}

    with (
        patched_attr(module, "find_qualification_issue", lambda _repo, _marker: 48),
        patched_attr(module, "_issue_api_request", request),
    ):
        number = module.upsert_qualification_issue(
            repository="synthetic/repository",
            evidence=evidence,
            run_url="https://github.com/synthetic/repository/actions/runs/123",
        )

    assert number == 48
    assert calls[0][1] == "PATCH"
    assert calls[0][2] is not None
    assert calls[0][2]["state"] == "open"
    assert "fix: synthetic parser correction" in calls[0][2]["body"]


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


def test_metadata_request_scopes_github_token_to_api_origin() -> None:
    module = load_script()
    captured: dict[str, Any] = {}

    class Response:
        headers = {"Content-Length": "2"}

        def __enter__(self) -> Response:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self, _limit: int) -> bytes:
            return b"{}"

    class Opener:
        def open(self, request: Any, *, timeout: int) -> Response:
            captured["request"] = request
            captured["timeout"] = timeout
            return Response()

    with (
        patched_attr(module, "METADATA_OPENER", Opener()),
        patched_env(GITHUB_TOKEN="synthetic-github-token"),
    ):
        assert module._request_json(f"{module.UPSTREAM_API}/releases") == {}

    request = captured["request"]
    assert request.get_header("Authorization") == "Bearer synthetic-github-token"
    assert request.get_header("X-github-api-version") == "2022-11-28"
    assert captured["timeout"] == module.HTTP_TIMEOUT_SECONDS


def test_metadata_request_rejects_non_github_origin_before_authentication() -> None:
    module = load_script()

    with (
        patched_env(GITHUB_TOKEN="synthetic-github-token"),
        pytest.raises(module.CompatibilityError, match="outside the allowed GitHub API origin"),
    ):
        module._request_json("https://downloads.example.invalid/releases")


def test_asset_download_never_uses_github_api_token(tmp_path: Path) -> None:
    module = load_script()
    captured: dict[str, Any] = {}

    class Response:
        headers = {"Content-Length": "3"}

        def __init__(self) -> None:
            self.read_once = False

        def __enter__(self) -> Response:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self, _size: int) -> bytes:
            if captured.get("read"):
                return b""
            captured["read"] = True
            return b"ocr"

        def geturl(self) -> str:
            return (
                "https://release-assets.githubusercontent.com/github-production-release-asset/"
                "synthetic?sig=bounded"
            )

    @contextmanager
    def fake_urlopen(request: Any, *, timeout: int) -> Any:
        captured["request"] = request
        captured["timeout"] = timeout
        yield Response()

    digest = module.hashlib.sha256(b"ocr").hexdigest()
    asset = module.Asset(
        name="opencodereview-linux-amd64",
        size=3,
        sha256=digest,
        url=(
            "https://github.com/alibaba/open-code-review/releases/download/"
            "v1.8.2/opencodereview-linux-amd64"
        ),
    )
    with (
        patched_attr(module.urllib.request, "urlopen", fake_urlopen),
        patched_env(GITHUB_TOKEN="synthetic-github-token"),
    ):
        assert module._download(asset, tmp_path).read_bytes() == b"ocr"

    request = captured["request"]
    assert request.get_header("Authorization") is None
    assert request.get_header("User-agent") == module.USER_AGENT


def test_asset_download_retries_timeout_and_resets_partial_file(tmp_path: Path) -> None:
    module = load_script()
    calls = 0

    class Response:
        headers = {"Content-Length": "3"}

        def __init__(self, *, fail_midstream: bool) -> None:
            self.fail_midstream = fail_midstream
            self.read_count = 0

        def __enter__(self) -> Response:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self, _size: int) -> bytes:
            self.read_count += 1
            if self.fail_midstream and self.read_count == 1:
                return b"o"
            if self.fail_midstream:
                raise TimeoutError("synthetic midstream timeout")
            if self.read_count > 1:
                return b""
            return b"ocr"

        def geturl(self) -> str:
            return "https://release-assets.githubusercontent.com/synthetic"

    def flaky_urlopen(request: Any, *, timeout: int) -> Response:
        nonlocal calls
        calls += 1
        return Response(fail_midstream=calls == 1)

    asset = module.Asset(
        name="opencodereview-linux-amd64",
        size=3,
        sha256=module.hashlib.sha256(b"ocr").hexdigest(),
        url=(
            "https://github.com/alibaba/open-code-review/releases/download/"
            "v1.8.5/opencodereview-linux-amd64"
        ),
    )
    with (
        patched_attr(module.urllib.request, "urlopen", flaky_urlopen),
        patched_attr(module.time, "sleep", lambda _seconds: None),
    ):
        destination = module._download(asset, tmp_path)

    assert destination.read_bytes() == b"ocr"
    assert calls == 2


def test_asset_download_bounds_transient_retries(tmp_path: Path) -> None:
    module = load_script()
    calls = 0

    def timed_out_urlopen(request: Any, *, timeout: int) -> None:
        nonlocal calls
        calls += 1
        raise TimeoutError("synthetic timeout")

    asset = module.Asset(
        name="opencodereview-linux-amd64",
        size=3,
        sha256=module.hashlib.sha256(b"ocr").hexdigest(),
        url=(
            "https://github.com/alibaba/open-code-review/releases/download/"
            "v1.8.5/opencodereview-linux-amd64"
        ),
    )
    with (
        patched_attr(module.urllib.request, "urlopen", timed_out_urlopen),
        patched_attr(module.time, "sleep", lambda _seconds: None),
        pytest.raises(module.CompatibilityError, match="after 3 attempts"),
    ):
        module._download(asset, tmp_path)

    assert calls == module.DOWNLOAD_ATTEMPTS


def test_asset_download_does_not_retry_not_found(tmp_path: Path) -> None:
    module = load_script()
    calls = 0

    def not_found_urlopen(request: Any, *, timeout: int) -> None:
        nonlocal calls
        calls += 1
        raise module.urllib.error.HTTPError(
            request.full_url,
            404,
            "synthetic not found",
            hdrs=None,
            fp=None,
        )

    asset = module.Asset(
        name="opencodereview-linux-amd64",
        size=3,
        sha256=module.hashlib.sha256(b"ocr").hexdigest(),
        url=(
            "https://github.com/alibaba/open-code-review/releases/download/"
            "v1.8.5/opencodereview-linux-amd64"
        ),
    )
    with (
        patched_attr(module.urllib.request, "urlopen", not_found_urlopen),
        pytest.raises(module.CompatibilityError, match="cannot download"),
    ):
        module._download(asset, tmp_path)

    assert calls == 1


def test_prepare_update_promotes_one_reviewed_release_chain(tmp_path: Path) -> None:
    module = load_script()
    root = tmp_path
    (root / "compatibility" / "evidence").mkdir(parents=True)
    (root / "src" / "ocr_toolkit").mkdir(parents=True)
    (root / "examples" / "gitlab").mkdir(parents=True)
    (root / "docs").mkdir(parents=True)
    (root / "changelog.d").mkdir()
    for evidence_name in (
        "ocr-1.7.17.json",
        "ocr-1.8.0.json",
        "ocr-1.8.1.json",
        "ocr-1.8.2.json",
        "ocr-1.8.3.json",
        "ocr-1.8.4.json",
        "ocr-1.8.5.json",
        "ocr-1.8.6.json",
    ):
        baseline_evidence = PROJECT_ROOT / "compatibility" / "evidence" / evidence_name
        (root / "compatibility" / "evidence" / evidence_name).write_bytes(
            baseline_evidence.read_bytes()
        )
    manifest_path = root / "compatibility" / "ocr-support.json"
    synthetic_manifest = module.load_json(MANIFEST)
    synthetic_manifest["monitoring_floor"] = "1.8.6"
    synthetic_manifest["recommended_version"] = "1.8.6"
    synthetic_manifest["releases"] = [
        item
        for item in synthetic_manifest["releases"]
        if module._version(item["version"]) <= (1, 8, 6)
    ]
    manifest_path.write_bytes(module.canonical_json(synthetic_manifest))
    preflight = root / "src" / "ocr_toolkit" / "preflight.py"
    preflight.write_text('EXPECTED_OCR_VERSION = "1.8.6"\n', encoding="utf-8")
    example = root / "examples" / "gitlab" / "ocr-review.gitlab-ci.yml"
    example.write_text(
        'OCR_VERSION: "v1.8.6"\n'
        'OCR_SHA256: "1f2611766a562aee300af75524270de9b99ab2cf5c63bf75a9546ebf809f78a6"\n',
        encoding="utf-8",
    )
    (root / "README.md").write_text("OCR 1.8.6 baseline\n", encoding="utf-8")
    (root / "docs" / "gitlab.md").write_text("Pin v1.8.6 in GitLab.\n", encoding="utf-8")
    (root / "docs" / "security.md").write_text("Verify OCR 1.8.6.\n", encoding="utf-8")
    assets = json.loads(baseline_evidence.read_text(encoding="utf-8"))["assets"]
    assets = [dict(asset) for asset in assets]
    for asset in assets:
        asset["sha256"] = "a" * 64
    evidence_187 = {
        "schema_version": 2,
        "upstream_repository": module.UPSTREAM_REPOSITORY,
        "version": "1.8.7",
        "tag": "v1.8.7",
        "published_at": "2026-07-28T00:00:00Z",
        "result": "compatible",
        "classification": "human-review-required",
        "classification_reasons": ["release notes contain a material signal"],
        "comparison_version": "1.8.6",
        "tested_baseline_version": "1.8.6",
        "assets": assets,
        "contracts": {"optional_capabilities": ["per_run_model_override"]},
    }
    final_assets = [dict(asset) for asset in assets]
    for asset in final_assets:
        asset["sha256"] = "b" * 64
    evidence_188 = {
        **evidence_187,
        "version": "1.8.8",
        "tag": "v1.8.8",
        "comparison_version": "1.8.7",
        "assets": final_assets,
        "contracts": {
            "optional_capabilities": [
                "llm_result_identity",
                "per_run_model_override",
                "per_run_provider_override",
            ]
        },
    }

    changed = module.prepare_update(
        manifest_path=manifest_path,
        evidence=[evidence_188, evidence_187],
        fragment_number=42,
        human_conclusions={
            "1.8.7": "Reviewed provider and result additions; toolkit consumers remain additive.",
            "1.8.8": "Reviewed language allowlist changes; toolkit does not consume them.",
        },
        root=root,
    )

    assert {path.relative_to(root).as_posix() for path in changed} == {
        "compatibility/ocr-support.json",
        "compatibility/evidence/ocr-1.8.7.json",
        "compatibility/evidence/ocr-1.8.8.json",
        "src/ocr_toolkit/preflight.py",
        "examples/gitlab/ocr-review.gitlab-ci.yml",
        "README.md",
        "docs/gitlab.md",
        "docs/security.md",
        "changelog.d/42.feature.md",
    }
    updated = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert updated["recommended_version"] == "1.8.8"
    assert updated["monitoring_floor"] == "1.8.8"
    assert 'EXPECTED_OCR_VERSION = "1.8.8"' in preflight.read_text(encoding="utf-8")
    release_188 = next(item for item in updated["releases"] if item["version"] == "1.8.8")
    assert release_188["capabilities"] == [
        "llm_result_identity",
        "per_run_model_override",
        "per_run_provider_override",
    ]
    example_text = example.read_text(encoding="utf-8")
    assert 'OCR_VERSION: "v1.8.8"' in example_text
    assert f'OCR_SHA256: "{"b" * 64}"' in example_text
    assert "1.8.8" in (root / "README.md").read_text(encoding="utf-8")
    fragment = (root / "changelog.d" / "42.feature.md").read_text(encoding="utf-8")
    assert "1.8.7 through 1.8.8" in fragment


def test_prepare_update_rejects_human_review_candidate(tmp_path: Path) -> None:
    module = load_script()
    evidence = {
        "schema_version": 2,
        "version": "1.9.2",
        "result": "compatible",
        "classification": "human-review-required",
        "comparison_version": "1.9.1",
        "tested_baseline_version": "1.9.1",
    }

    with pytest.raises(module.CompatibilityError, match="bounded conclusion"):
        module.prepare_update(
            manifest_path=MANIFEST,
            evidence=evidence,
            fragment_number=42,
            root=PROJECT_ROOT,
        )


def test_prepare_update_requires_human_review_for_minor_transition() -> None:
    module = load_script()
    evidence = {
        "schema_version": 2,
        "version": "1.10.0",
        "result": "compatible",
        "classification": "automatic-safe",
        "comparison_version": "1.9.1",
        "tested_baseline_version": "1.9.1",
    }

    with pytest.raises(module.CompatibilityError, match="explicit human review"):
        module.prepare_update(
            manifest_path=MANIFEST,
            evidence=evidence,
            fragment_number=73,
            root=PROJECT_ROOT,
        )


def test_prepare_update_rejects_nonadjacent_minor_transition() -> None:
    module = load_script()
    evidence = {
        "schema_version": 2,
        "version": "1.11.0",
        "result": "compatible",
        "classification": "human-review-required",
        "comparison_version": "1.9.1",
        "tested_baseline_version": "1.9.1",
    }

    with pytest.raises(module.CompatibilityError, match="contiguous release sequence"):
        module.prepare_update(
            manifest_path=MANIFEST,
            evidence=evidence,
            fragment_number=73,
            human_conclusions={"1.11.0": "Synthetic reviewed conclusion."},
            root=PROJECT_ROOT,
        )


def test_prepare_update_rejects_conclusion_outside_evidence_chain() -> None:
    module = load_script()
    evidence = {
        "schema_version": 2,
        "version": "1.9.2",
        "result": "compatible",
        "classification": "automatic-safe",
        "comparison_version": "1.9.1",
        "tested_baseline_version": "1.9.1",
    }

    with pytest.raises(module.CompatibilityError, match="only evidence versions"):
        module.prepare_update(
            manifest_path=MANIFEST,
            evidence=evidence,
            fragment_number=72,
            human_conclusions={"1.9.3": "Synthetic unrelated conclusion."},
            root=PROJECT_ROOT,
        )


@pytest.mark.parametrize("conclusion", ["", "x" * 2_001, "unsafe\x00text"])
def test_prepare_update_rejects_invalid_optional_reviewed_conclusion(
    conclusion: str,
) -> None:
    module = load_script()
    evidence = {
        "schema_version": 2,
        "version": "1.9.2",
        "result": "compatible",
        "classification": "automatic-safe",
        "comparison_version": "1.9.1",
        "tested_baseline_version": "1.9.1",
    }

    with pytest.raises(module.CompatibilityError, match="bounded plain text"):
        module.prepare_update(
            manifest_path=MANIFEST,
            evidence=evidence,
            fragment_number=72,
            human_conclusions={"1.9.2": conclusion},
            root=PROJECT_ROOT,
        )
