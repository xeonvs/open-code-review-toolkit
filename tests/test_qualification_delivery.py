"""Qualification lookup enforces authorship before privileged issue reuse."""

from copy import deepcopy
from pathlib import Path

import pytest

from tests.test_ocr_compat import MANIFEST, load_script, release

VERSION = "1.13.5"
MARKER = f"<!-- ocr-compat-candidate:v{VERSION} -->"
OWNER = {"login": "synthetic", "id": 17, "type": "User"}
ACTIONS = {"login": "github-actions[bot]", "id": 41898282, "type": "Bot"}
OUTSIDER = {"login": "contributor", "id": 19, "type": "User"}


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
        assert "invalid-result" in module.delivery.render_workflow_failure_issue(status, "test")
    assess = module.delivery.assess_matrix
    assert assess(manifest, matrix, tmp_path, head)["classification"] == "incompatible"
    assert assess(manifest, matrix, tmp_path, "b" * 40)["classification"] == "incomplete"
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
    manifest = {"recommended_version": retained["tested_baseline_version"]}
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

    candidate["assets"][0]["size"] += 1
    output.unlink()
    with pytest.raises(module.core.QualificationStageError, match="release assets"):
        module.qualification.qualify_release(candidate, manifest, output)
    assert not output.exists()


@pytest.mark.parametrize("mismatch", [True, False])
def test_public_qualification_logs_only_closed_contract_results(
    tmp_path, monkeypatch, capsys, mismatch
):
    module = load_script()
    monkeypatch.setattr(module.assets, "_request_json", lambda _url: release("2.0.0"))
    message = "private synthetic model diagnostic"

    def fail(*args, **kwargs):
        if mismatch:
            raise module.core.QualificationContractMismatch(message, reason="invalid-result")
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
