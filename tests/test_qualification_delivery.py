"""Qualification lookup enforces authorship before privileged issue reuse."""

from copy import deepcopy

import pytest

from tests.test_ocr_compat import load_script

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
