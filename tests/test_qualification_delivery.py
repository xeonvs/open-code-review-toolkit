"""Qualification lookup enforces authorship before privileged issue reuse."""

import json
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import pytest

from tests.test_ocr_compat import MANIFEST, load_script, release

VERSION = "1.13.5"
MARKER = f"<!-- ocr-compat-candidate:v{VERSION} -->"
OWNER = {"login": "synthetic", "id": 17, "type": "User"}
ACTIONS = {"login": "github-actions[bot]", "id": 41898282, "type": "Bot"}
OUTSIDER = {"login": "contributor", "id": 19, "type": "User"}


@pytest.mark.parametrize("expected_count, present", [(1, []), (1, [0]), (2, [1]), (2, [0, 1])])
def test_assess_downloaded_layouts(tmp_path, expected_count, present):
    module = load_script()
    manifest = {"recommended_version": "1.13.8"}
    tags = ["v1.13.9", "v1.13.10"][:expected_count]
    matrix = module.assets.qualification_matrix(manifest, [{"tag_name": tag} for tag in tags])
    if not present:
        (tmp_path / "checkout.txt").write_text("a" * 40)
    for index in present:
        entry = matrix["include"][index]
        candidate = tmp_path if len(present) == 1 else tmp_path / f"ocr-compatibility-{tags[index]}"
        candidate.mkdir(exist_ok=True)
        (candidate / "checkout.txt").write_text("a" * 40)
        status = module.contracts.qualification_status(
            **entry, result="incompatible", reason="invalid-result", phase="contracts"
        )
        (candidate / "status.json").write_bytes(module.core.canonical_json(status))
        (candidate / "incompatibility.json").write_bytes(
            module.core.canonical_json(incompatible_receipt(status))
        )
    result = module.delivery.assess_matrix(manifest, matrix, tmp_path, "a" * 40)
    assert result["classification"] == (
        "incompatible" if len(present) == expected_count else "incomplete"
    )
    for index, tag in enumerate(tags):
        assert result["outcomes"][tag] == (
            "incompatible (invalid-result)"
            if index in present
            else "missing or inconsistent qualification artifact"
        )


def upsert(module, issues, *, failed=False):
    calls = []

    def request(url, *, method="GET", payload=None):
        calls.append((url, method, payload))
        if method == "GET":
            return deepcopy(issues)
        return {"number": 50 if method == "POST" else int(url.rsplit("/", 1)[1])}

    if failed:
        record = {
            "status": module.contracts.qualification_status(
                tag=f"v{VERSION}",
                comparison_version="1.13.4",
                tested_baseline_version="1.13.4",
                result="failed",
                phase="contracts",
                reason="contract-probe-failed",
            )
        }
    else:
        record = {
            "evidence": {
                "version": VERSION,
                "result": "compatible",
                "classification": "automatic-safe",
                "classification_reasons": [],
            }
        }
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(module.delivery, "_issue_api_request", request)
        number = module.delivery.upsert_qualification_issue(
            repository="synthetic/repository",
            run_url="https://github.com/synthetic/repository/actions/runs/123",
            **record,
        )
    return number, calls


@pytest.mark.parametrize("failed", [False, True])
def test_outsider_marker_cannot_authorize_patch_or_preempt_canonical_lookup(failed):
    module = load_script()
    outsider = {"number": 9, "body": MARKER, "user": OUTSIDER}
    number, calls = upsert(module, [outsider], failed=failed)
    assert number == 50 and calls[-1][1] == "POST"
    owner = {"number": 48, "body": MARKER, "user": OWNER, "state": "closed"}
    number, calls = upsert(module, [outsider, owner], failed=failed)
    assert number == 48 and calls[-1][1] == "PATCH"
    assert calls[-1][2]["state"] == "open"


@pytest.mark.parametrize("author", [OWNER, OWNER | {"login": "SYNTHETIC"}, ACTIONS])
@pytest.mark.parametrize("suffix", ["", "\nbody", "\r\nbody"])
def test_exact_owner_or_actions_header_preserves_legitimate_reuse(author, suffix):
    number, calls = upsert(load_script(), [{"number": 48, "body": MARKER + suffix, "user": author}])
    assert number == 48 and calls[-1][1] == "PATCH"


@pytest.mark.parametrize(
    "author",
    [
        None,
        [],
        {},
        OUTSIDER,
        ACTIONS | {"id": 1},
        ACTIONS | {"id": 41898282.0},
        ACTIONS | {"type": "User"},
        OWNER | {"type": "Bot"},
        {"login": 7, "id": 17, "type": "User"},
    ],
)
def test_malformed_or_unrelated_authors_do_not_gain_issue_authority(author):
    issue = {"number": 9, "body": MARKER, "user": author, "author_association": "MEMBER"}
    number, calls = upsert(load_script(), [issue])
    assert number == 50 and calls[-1][1] == "POST"


@pytest.mark.parametrize(
    "body",
    [
        "quoted\n" + MARKER,
        "> " + MARKER,
        "```text\n" + MARKER + "\n```",
        MARKER + " suffix",
        "prefix " + MARKER,
    ],
)
def test_marker_mentions_cannot_claim_an_owner_issue(body):
    number, calls = upsert(load_script(), [{"number": 9, "body": body, "user": OWNER}])
    assert number == 50 and calls[-1][1] == "POST"


def incompatible_receipt(status):
    return {
        "schema": "ocr.incompatibility/v1",
        "status": status,
        "executable": {"name": "opencodereview-linux-amd64", "size": 32, "sha256": "a" * 64},
    }


def test_matrix_binds_each_terminal_status_to_its_candidate(tmp_path: Path) -> None:
    module = load_script()
    manifest = {"recommended_version": "1.13.8"}
    matrix = module.assets.qualification_matrix(manifest, [release("1.13.9"), release("1.13.10")])
    head = "a" * 40
    for entry in matrix["include"]:
        tag = entry["tag"]
        candidate = tmp_path / f"ocr-compatibility-{tag}"
        candidate.mkdir()
        (candidate / "checkout.txt").write_text(head + "\n")
        status = module.contracts.qualification_status(
            **entry, result="incompatible", reason="invalid-result", phase="contracts"
        )
        (candidate / "status.json").write_bytes(module.core.canonical_json(status))
        (candidate / "incompatibility.json").write_bytes(
            module.core.canonical_json(incompatible_receipt(status))
        )
        assert "invalid-result" in module.delivery.render_workflow_failure_issue(status, "test")
    assess = module.delivery.assess_matrix
    assert assess(manifest, matrix, tmp_path, head)["classification"] == "incompatible"
    assert assess(manifest, matrix, tmp_path, "b" * 40)["classification"] == "incomplete"

    def duplicate_markers(_url, **kwargs):
        assert not kwargs
        marker = "<!-- ocr-compat-candidate:v1.13.9 -->"
        return [{"number": number, "body": marker, "user": OWNER} for number in (47, 48)]

    with pytest.MonkeyPatch.context() as patch:

        def requests(url, **kwargs):
            if kwargs.get("method") == "POST":
                return {"number": 49}
            return duplicate_markers(url, **kwargs)

        patch.setattr(module.delivery, "_issue_api_request", requests)
        result = assess(
            manifest,
            matrix,
            tmp_path,
            head,
            issue_repository="synthetic/repository",
            run_url="https://github.com/synthetic/repository/actions/runs/123",
        )
        assert result["classification"] == "incomplete"
        assert "#47, #48" in result["outcomes"]["v1.13.9"]
        assert result["outcomes"]["v1.13.10"] == "incompatible (invalid-result)"
    status_path = tmp_path / "ocr-compatibility-v1.13.10" / "status.json"
    original = module.core.load_json(status_path)
    for invalid in (
        dict(original, comparison_version="1.13.8"),
        dict(original, version="1.13.9"),
        dict(original, phase="artifact", reason="artifact-verification-failed", result="failed"),
    ):
        status_path.write_bytes(module.core.canonical_json(invalid))
        result = assess(manifest, matrix, tmp_path, head)
        assert result["classification"] == "incomplete"
        assert result["outcomes"]["v1.13.9"] == "incompatible (invalid-result)"
    status_path.unlink()
    assert assess(manifest, matrix, tmp_path, head)["classification"] == "incomplete"
    (tmp_path / "ocr-compatibility-v9.9.9").mkdir()
    with pytest.raises(module.core.CompatibilityError, match="unexpected candidate"):
        assess(manifest, matrix, tmp_path, head)


def test_retained_qualification_checks_current_asset_identity_before_replay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_script()
    version = "1.13.11"
    source = MANIFEST.parent / "evidence" / f"ocr-{version}.json"
    retained = module.core.load_json(source)
    manifest = {
        "recommended_version": retained["tested_baseline_version"],
        "releases": [
            {"version": version, "evidence_sha256": sha256(source.read_bytes()).hexdigest()}
        ],
    }
    candidate = release(version)
    candidate["assets"] = [
        {
            "name": asset["name"],
            "size": asset["size"],
            "digest": "sha256:" + asset["sha256"],
            "browser_download_url": (
                f"https://github.com/alibaba/open-code-review/releases/download/v{version}/"
                + asset["name"]
            ),
        }
        for asset in retained["assets"]
    ]
    monkeypatch.setattr(
        module.assets, "_download", lambda *_: pytest.fail("replay began a native download")
    )
    output = tmp_path / "evidence.json"
    module.qualification.qualify_release(candidate, manifest, output)
    assert output.read_bytes() == source.read_bytes()

    tampered = tmp_path / "compatibility" / "evidence" / source.name
    tampered.parent.mkdir(parents=True)
    tampered.write_bytes(
        module.core.canonical_json(retained | {"classification": "automatic-safe"})
    )
    assert tampered.read_bytes() != source.read_bytes()
    with pytest.raises(module.core.QualificationStageError, match="manifest digest"):
        module.qualification.qualify_release(candidate, manifest, output, root=tmp_path)
    monkeypatch.setattr(module.assets, "_request_json", lambda _url: candidate)
    executable = next(
        asset for asset in retained["assets"] if asset["name"] == "opencodereview-linux-amd64"
    )
    module.assets.verify_disposition_asset(candidate["tag_name"], executable)
    with pytest.raises(module.core.CompatibilityError, match="executable changed"):
        module.assets.verify_disposition_asset(
            candidate["tag_name"], executable | {"size": executable["size"] + 1}
        )
    candidate["assets"][0]["size"] += 1
    output.unlink()
    with pytest.raises(module.core.QualificationStageError, match="release assets"):
        module.qualification.qualify_release(candidate, manifest, output)
    assert not output.exists()


@pytest.mark.parametrize("skipped_version", [None, "1.14.0", "1.14.9"])
def test_behavioral_promotion_preserves_observations_and_packages_exact_handoffs(
    tmp_path: Path, skipped_version: str | None
) -> None:
    module = load_script()
    baseline = "1.13.13"
    version = f"1.14.{1 + int(skipped_version.rsplit('.', 1)[1])}" if skipped_version else "1.14.0"
    compatibility = tmp_path / "compatibility"
    evidence_dir = compatibility / "evidence"
    evidence_dir.mkdir(parents=True)
    source = MANIFEST.parent / "evidence" / f"ocr-{baseline}.json"
    legacy = module.core.load_json(source)
    legacy_bytes = source.read_bytes()
    (evidence_dir / source.name).write_bytes(legacy_bytes)
    manifest_path = compatibility / "ocr-support.json"
    manifest = {
        "schema_version": 2,
        "upstream_repository": module.settings.UPSTREAM_REPOSITORY,
        "recommended_version": baseline,
        "monitoring_floor": baseline,
        "runtime_support": module.contracts._rolling_runtime_support(baseline),
        "releases": [
            {
                "version": baseline,
                "status": "tested",
                "assets": legacy["assets"],
                "evidence": f"compatibility/evidence/{source.name}",
                "evidence_sha256": sha256(legacy_bytes).hexdigest(),
            }
        ],
    }
    manifest_bytes = module.core.canonical_json(manifest)
    manifest_path.write_bytes(manifest_bytes)
    preflight = tmp_path / "src" / "ocr_toolkit" / "preflight.py"
    preflight.parent.mkdir(parents=True)
    preflight.write_text(
        f'RECOMMENDED_OCR_VERSION = "{baseline}"\n'
        f'SUPPORTED_OCR_VERSIONS = ("{baseline}",)\n'
        "DEPRECATED_OCR_VERSIONS = ()\n"
    )
    evidence = {
        **legacy,
        "schema_version": 5,
        "version": version,
        "tag": f"v{version}",
        "comparison_version": skipped_version or baseline,
        "tested_baseline_version": baseline,
        "classification": "human-review-required",
        "contracts": {
            "checks": dict.fromkeys(module.settings.BEHAVIORAL_CHECKS, "passed"),
            "native_handoffs": ["analysis", "diagram_output", "gitlink_projection"],
            "observations": {
                "native_handoffs": {
                    "analysis": {"status": "completed", "citations_verified": True},
                    "diagram_output": {"consumer": "toolkit-local", "rendered": True},
                    "gitlink_projection": {"consumer": "toolkit-local", "immutable_range": True},
                },
                "comparison_sides": legacy["contracts"]["comparison_sides_probe"],
                "builtin_selection": {
                    "selected": ["src/query.sql", "src/kernel.hip"],
                    "rules": {"src/query.sql": {"pattern": "sql/**", "heading": "Query checks"}},
                },
            },
        },
    }
    prepare = module.promotion.prepare_update
    options = {
        "manifest_path": manifest_path,
        "fragment_number": 328,
        "human_conclusions": {version: "Reviewed adjacent native behavior."},
        "root": tmp_path,
    }
    if skipped_version:
        with pytest.raises(module.core.CompatibilityError, match="contiguous release sequence"):
            prepare(evidence=evidence, **options)
        status = module.contracts.qualification_status(
            tag=f"v{skipped_version}",
            comparison_version=baseline,
            tested_baseline_version=baseline,
            result="incompatible",
            phase="contracts",
            reason="analysis-contract",
        )
        wrong = status | {"result": "failed", "reason": "unexpected-error"}
        with pytest.raises(
            module.core.CompatibilityError, match="invalid incompatible executable receipt"
        ):
            prepare(evidence=evidence, incompatible_statuses=[status], **options)
        with pytest.raises(
            module.core.CompatibilityError, match=r"as incompatible|contiguous release sequence"
        ):
            prepare(
                evidence=evidence, incompatible_statuses=[incompatible_receipt(wrong)], **options
            )
        with pytest.raises(
            module.core.CompatibilityError,
            match=r"requires a bounded conclusion|contiguous release sequence",
        ):
            prepare(
                evidence=evidence, incompatible_statuses=[incompatible_receipt(status)], **options
            )
        receipts = []
        previous = baseline
        for n in range(int(skipped_version.rsplit(".", 1)[1]) + 1):
            candidate = f"1.14.{n}"
            status = module.contracts.qualification_status(
                tag=f"v{candidate}",
                comparison_version=previous,
                tested_baseline_version=baseline,
                result="incompatible",
                phase="contracts",
                reason="analysis-contract",
            )
            receipts.append(incompatible_receipt(status))
            options["human_conclusions"][candidate] = "Rejected Analysis contract."
            previous = candidate
        options["incompatible_statuses"] = receipts
        options["human_conclusions"][skipped_version] = "Rejected Analysis contract."
    if skipped_version:
        unclassified = deepcopy(evidence)
        unclassified.pop("classification")
        with pytest.raises(module.core.CompatibilityError, match="invalid classification"):
            prepare(evidence=unclassified, **options)
    broken = deepcopy(evidence)
    broken["contracts"]["checks"].pop("publication")
    with pytest.raises(module.core.CompatibilityError, match="required consumer check"):
        prepare(evidence=broken, **options)
    assert manifest_path.read_bytes() == manifest_bytes
    assert not (evidence_dir / f"ocr-{version}.json").exists()

    prepare(evidence=evidence, **options)
    promoted = module.core.load_json(manifest_path)
    module.contracts.validate_manifest(promoted, tmp_path)
    assert module.contracts.qualified_runtime_versions(promoted) == ([version], [])
    assert module.core.load_json(evidence_dir / f"ocr-{version}.json") == evidence
    assert (evidence_dir / source.name).read_bytes() == legacy_bytes
    if skipped_version:
        rejected = next(item for item in promoted["releases"] if item["version"] == skipped_version)
        assert rejected["status"] == "incompatible"
        retained_status = tmp_path / rejected["evidence"]
        assert module.core.load_json(retained_status) == incompatible_receipt(status)
        retained_status.write_text("{}")
        with pytest.raises(module.core.CompatibilityError, match="evidence hash mismatch"):
            module.contracts.validate_manifest(promoted, tmp_path)
        retained_status.write_bytes(module.core.canonical_json(incompatible_receipt(status)))
    inventory = preflight.with_name("_qualified_handoffs.json")
    assert module.core.load_json(inventory) == {version: evidence["contracts"]["native_handoffs"]}
    inventory.write_text("{}")
    with pytest.raises(module.core.CompatibilityError, match="packaged native handoffs"):
        module.contracts.validate_manifest(promoted, tmp_path)


@pytest.mark.parametrize("mismatch", [True, False])
def test_public_qualification_logs_only_closed_contract_results(
    tmp_path, monkeypatch, capsys, mismatch
):
    module = load_script()
    monkeypatch.setattr(module.assets, "_request_json", lambda _url: release("2.0.0"))
    message = "private synthetic model diagnostic"

    def fail(*args, **kwargs):
        if mismatch:
            exc = module.core.QualificationContractMismatch(message, reason="invalid-result")
            exc.verified_executable = incompatible_receipt({})["executable"]
            raise exc
        raise module.core.QualificationStageError(
            message, phase="contracts", reason="unexpected-error"
        )

    monkeypatch.setattr(module.qualification, "qualify_release", fail)
    status = tmp_path / "status.json"
    code = module.cli.main(
        [
            "--manifest",
            str(MANIFEST),
            "qualify",
            "--tag",
            "v2.0.0",
            "--public-log",
            "--output",
            str(tmp_path / "evidence.json"),
            "--status-output",
            str(status),
        ]
    )
    assert code == (0 if mismatch else 1)
    output = capsys.readouterr()
    assert message not in output.out + output.err + status.read_text()
    expected = "incompatible" if mismatch else "failed"
    assert module.core.load_json(status)["result"] == expected
    if mismatch:
        assert module.delivery.load_incompatible_receipt(status) == incompatible_receipt(
            module.core.load_json(status)
        )


def test_candidate_rerun_preserves_previous_incompatible_bundle(tmp_path, monkeypatch, capsys):
    module = load_script()
    version = "1.13.9"
    monkeypatch.setattr(module.assets, "_request_json", lambda _url: release(version))

    def reject(*args, **kwargs):
        exc = module.core.QualificationContractMismatch("synthetic", reason="invalid-result")
        exc.verified_executable = incompatible_receipt({})["executable"]
        raise exc

    monkeypatch.setattr(module.qualification, "qualify_release", reject)

    def run(directory):
        return module.cli.main(
            [
                "qualify",
                "--tag",
                "v" + version,
                "--output",
                str(directory / "evidence.json"),
                "--status-output",
                str(directory / "status.json"),
                "--public-log",
            ]
        )

    assert run(tmp_path) == 0
    previous = module.delivery.load_incompatible_receipt(tmp_path / "status.json")

    def accept(_release, _manifest, output, **kwargs):
        observed = module.core.load_json(
            MANIFEST.parent / "evidence" / ("ocr-" + version + ".json")
        )
        output.write_bytes(module.core.canonical_json(observed))
        return observed

    monkeypatch.setattr(module.qualification, "qualify_release", accept)
    assert run(tmp_path) == 1
    assert "fresh output directory" in capsys.readouterr().err
    assert module.delivery.load_incompatible_receipt(tmp_path / "status.json") == previous
    assert not (tmp_path / "evidence.json").exists()
    retry = tmp_path / "second"
    assert run(retry) == 0
    assert module.core.load_json(retry / "status.json")["result"] == "compatible"
    assert (retry / "evidence.json").is_file() and not (retry / "incompatibility.json").exists()


@pytest.mark.parametrize(
    "mutation", ["oversize", "deep", "surrogate", "classification", "assets", "checkout", "receipt"]
)
def test_invalid_artifact_preserves_independent_candidate(tmp_path, monkeypatch, mutation):
    module = load_script()
    baseline = "1.13.8"
    versions = ["1.13.9", "1.13.10"]
    manifest = {"recommended_version": baseline}
    matrix = module.assets.qualification_matrix(
        manifest, [release(version) for version in versions]
    )
    for entry in matrix["include"]:
        tag = entry["tag"]
        candidate = tmp_path / f"ocr-compatibility-{tag}"
        candidate.mkdir()
        (candidate / "checkout.txt").write_text("a" * 40)
        if tag == "v1.13.10":
            status = module.contracts.qualification_status(
                **entry, result="incompatible", reason="invalid-result", phase="contracts"
            )
            (candidate / "incompatibility.json").write_bytes(
                module.core.canonical_json(incompatible_receipt(status))
            )
        else:
            status = module.contracts.qualification_status(
                **entry, result="compatible", reason="compatible", phase="complete"
            )
            observed = module.core.load_json(MANIFEST.parent / "evidence" / "ocr-1.13.9.json")
            (candidate / "evidence.json").write_bytes(module.core.canonical_json(observed))
        (candidate / "status.json").write_bytes(module.core.canonical_json(status))
    assert (
        module.delivery.assess_matrix(manifest, matrix, tmp_path, "a" * 40)["classification"]
        == "incompatible"
    )
    first = tmp_path / "ocr-compatibility-v1.13.9"
    if mutation == "oversize":
        (first / "status.json").write_bytes(b" " * 4097)
    elif mutation == "deep":
        (first / "evidence.json").write_bytes(b'{"x":' + b"[" * 3000 + b"]" * 3000 + b"}")
    elif mutation == "surrogate":
        (first / "evidence.json").write_text(
            json.dumps(observed | {"classification_reasons": ["\ud800"]})
        )
    elif mutation == "checkout":
        (first / "checkout.txt").write_text("a" * 40 + " " * 500)
    elif mutation == "receipt":
        (tmp_path / "ocr-compatibility-v1.13.10" / "incompatibility.json").unlink()
    else:
        observed[mutation] = [] if mutation == "assets" else "bogus"
        (first / "evidence.json").write_bytes(module.core.canonical_json(observed))
    published = []

    def upsert(**kwargs):
        record = kwargs["status"] or kwargs["evidence"]
        published.append(record["tag"])
        return 99

    monkeypatch.setattr(module.delivery, "upsert_qualification_issue", upsert)
    result = module.delivery.assess_matrix(
        manifest,
        matrix,
        tmp_path,
        "a" * 40,
        issue_repository="synthetic/test",
        run_url="https://github.com/synthetic/test/actions/runs/8",
    )
    assert published == ["v1.13.9" if mutation == "receipt" else "v1.13.10"]
    assert (
        tmp_path / f"ocr-compatibility-{published[0]}" / "issue-number.txt"
    ).read_text() == "99\n"
    assert result["classification"] == "incomplete"
    assert (
        "missing or inconsistent"
        in result["outcomes"]["v1.13.10" if mutation == "receipt" else "v1.13.9"]
    )
    assert (
        result["outcomes"]["v1.13.9"] == "compatible (compatible)"
        if mutation == "receipt"
        else result["outcomes"]["v1.13.10"] == "incompatible (invalid-result)"
    )


def test_qualification_only_rechecks_retained_candidates_against_current_checkout(tmp_path):
    module = load_script()
    released = tmp_path / "releases.json"
    matrix = tmp_path / "matrix.json"
    assert (
        module.cli.main(
            [
                "discover",
                "--after-tag",
                "v1.13.13",
                "--through-tag",
                "v1.14.2",
                "--qualification-only",
                "--output",
                str(released),
            ]
        )
        == 0
    )
    assert (
        module.cli.main(
            [
                "build-matrix",
                "--after-tag",
                "v1.13.13",
                "--releases",
                str(released),
                "--output",
                str(matrix),
            ]
        )
        == 0
    )
    entries = module.core.load_json(matrix)["include"]
    assert [row["tag"] for row in entries] == ["v1.14.0", "v1.14.1", "v1.14.2"]
    assert [row["comparison_version"] for row in entries] == ["1.13.13", "1.14.0", "1.14.1"]
    assert {row["tested_baseline_version"] for row in entries} == {
        module.core.load_json(MANIFEST)["recommended_version"]
    }
