"""Qualification regressions at observed native and recoverable publication boundaries."""

import hashlib
import json
import os
import shutil
import subprocess
from contextlib import nullcontext
from copy import deepcopy
from pathlib import Path

import pytest

from tests.test_ocr_compat import load_script
from tests.test_result_contract import manifest_result


@pytest.mark.parametrize("version", ["1.13.9", "1.13.13"])
def test_probe_local_rejects_readback_versions_before_binary_lookup(version, tmp_path):
    module = load_script()
    result = module.cli.main(
        [
            "probe-local",
            "--binary",
            str(tmp_path / "absent"),
            "--version",
            version,
            "--output",
            str(tmp_path / "evidence"),
        ]
    )
    assert result == 1
    assert not (tmp_path / "evidence").exists()


def test_promotion_rolls_back_new_and_replaced_files_and_can_retry(tmp_path, monkeypatch):
    module = load_script()
    existing = tmp_path / "preflight.py"
    inventory = tmp_path / "handoffs.json"
    fresh = tmp_path / "evidence.json"
    existing.write_bytes(b"old preflight")
    inventory.write_bytes(b"old inventory")
    replace = module.promotion.os.replace

    def fail(source, destination):
        if destination == inventory:
            raise OSError("injected commit failure")
        return replace(source, destination)

    writes = [(fresh, b"evidence"), (existing, b"new preflight"), (inventory, b"new inventory")]
    with monkeypatch.context() as patch:
        patch.setattr(module.promotion.os, "replace", fail)
        with pytest.raises(module.core.CompatibilityError, match="commit promotion"):
            module.promotion._commit_outputs(writes, {fresh})
    assert not fresh.exists()
    assert existing.read_bytes() == b"old preflight"
    assert inventory.read_bytes() == b"old inventory"
    module.promotion._commit_outputs(writes, {fresh})
    assert all(path.read_bytes() == content for path, content in writes)


def test_capabilities_need_observations_for_new_evidence():
    module = load_script()
    sample = module.core.load_json(module.settings.ROOT / "compatibility/evidence/ocr-1.14.2.json")
    sample["schema_version"] = 5
    sample["contracts"]["observations"] = {}
    with pytest.raises(module.core.CompatibilityError, match="missing native handoff observations"):
        module.contracts._validate_evidence_contracts("1.14.2", sample)


def test_verified_binary_identity_is_checked_before_consumer_execution(tmp_path, monkeypatch):
    module = load_script()
    binary = tmp_path / "ocr"
    binary.write_bytes(b"replacement")
    expected = module.core.Asset("ocr", binary.stat().st_size, "0" * 64, "")
    monkeypatch.setattr(module.execution, "_run", lambda *_a, **_kw: pytest.fail("execution"))
    with pytest.raises(module.core.CompatibilityError, match="differs from verified candidate"):
        module.probes.handoffs.consumer_handoffs(binary, "1.14.2", tmp_path, expected)


@pytest.mark.parametrize("code", [-9, 1, 0])
def test_negative_cli_only_classifies_conclusive_rejection(code):
    module = load_script()
    process = subprocess.CompletedProcess([], code, "", "unrecognized diagnostic")
    with pytest.raises(module.core.CompatibilityError) as captured:
        module.numeric._expect_negative_rejection(process, "--max-tools")
    assert isinstance(captured.value, module.core.QualificationContractMismatch) is (code == 0)


def test_recognized_positive_cli_rejection_is_conclusive():
    module = load_script()
    process = subprocess.CompletedProcess(
        [],
        1,
        "",
        "Error: --max-tools must be a non-negative integer (0 means use template default)\n",
    )
    with pytest.raises(module.core.QualificationContractMismatch):
        module.numeric._accepted_numeric_preview(process, flag="--max-tools")


@pytest.mark.parametrize(
    "comment",
    [None, {}, {"path": "failed.py", "line": 2, "content": "Synthetic compatibility finding."}],
)
def test_budget_requires_publishable_finding_on_completed_path(comment):
    module = load_script()
    sample = manifest_result(
        "partial", selected=["done", "other"], completed=["done"], failed=[("other", "budget")]
    )
    for record in sample["manifest"]["coverage"]["selected"]:
        record["path"] = "done.py" if record["item_id"] == "done" else "failed.py"
    sample["comments"] = [comment]
    with pytest.raises(
        module.core.QualificationContractMismatch, match="lost its completed finding"
    ):
        module.numeric._verify_completed_finding(sample, frozenset({"done.py", "failed.py"}))
    sample["comments"] = [
        {"path": "done.py", "line": 2, "content": "Synthetic compatibility finding."}
    ]
    module.numeric._verify_completed_finding(sample, frozenset({"done.py", "failed.py"}))


def test_inconclusive_probe_keeps_closed_diagnostic_only():
    module = load_script()
    with pytest.raises(module.core.QualificationStageError) as captured:
        with module.core.probe("comment-arguments"):
            try:
                json.loads("PRIVATE")
            except json.JSONDecodeError as exc:
                raise module.core.CompatibilityError("PRIVATE") from exc
    error = captured.value
    assert error.reason == "contract-probe-failed"
    assert (error.probe, error.category) == ("comment-arguments", "invalid-output")


def test_refresh_requires_same_asset_and_checkout_before_replacing_receipts(tmp_path, monkeypatch):
    module = load_script()
    root = module.settings.ROOT
    shutil.copytree(root / "compatibility", tmp_path / "compatibility")
    inventory = "src/ocr_toolkit/_qualified_handoffs.json"
    (tmp_path / inventory).parent.mkdir(parents=True)
    shutil.copyfile(root / inventory, tmp_path / inventory)
    manifest_path = tmp_path / "compatibility/ocr-support.json"
    original = manifest_path.read_bytes()
    manifest = json.loads(original)
    # Use an already-tested patch, preserving recommendation and other receipts.
    version = "1.14.2"
    previous = "1.14.1"
    head = "a" * 40
    artifacts = tmp_path / "artifacts"
    candidate = artifacts / ("ocr-compatibility-v" + version)
    candidate.mkdir(parents=True)
    evidence_path = tmp_path / f"compatibility/evidence/ocr-{version}.json"
    evidence = json.loads(evidence_path.read_bytes())
    evidence.update(
        schema_version=5,
        tested_baseline_version=manifest["recommended_version"],
        comparison_version=previous,
    )
    evidence["contracts"]["observations"].update(
        comparison_sides={
            "result": "passed",
            "old_ref": "resolved-base",
            "new_ref": "resolved-head",
            "worktree": "preserved",
            "default_side": "new",
            "renamed_paths": "side-relative",
            "deleted_paths": "old-only",
            "target_tip": "not-used",
            "invalid_sides_rejected": True,
            "tools": ["file_read", "file_find", "code_search"],
        },
        native_handoffs={
            "analysis": {"status": "completed", "citations_verified": True},
            "chatgpt_auth": {"login_required": True, "store_admitted": True},
            "diagram_output": {"consumer": "toolkit-local", "rendered": True},
            "gitlink_projection": {"consumer": "toolkit-local", "immutable_range": True},
        },
    )
    status = module.contracts.qualification_status(
        tag=f"v{version}",
        comparison_version=previous,
        tested_baseline_version=manifest["recommended_version"],
        result="compatible",
        phase="complete",
        reason="compatible",
    )
    (candidate / "status.json").write_bytes(module.core.canonical_json(status))
    (candidate / "checkout.txt").write_text(head)
    retained = candidate / "evidence.json"
    retained.write_bytes(module.core.canonical_json(evidence))
    refresh = module.cli.refresh.refresh_receipts
    options = dict(after_tag="v" + previous, through_tag="v" + version)
    with pytest.raises(module.core.CompatibilityError, match="checkout mismatch"):
        refresh(manifest_path, artifacts, "b" * 40, **options)
    assert manifest_path.read_bytes() == original
    changed_digest = deepcopy(evidence)
    changed_digest["assets"][0]["sha256"] = "f" * 64
    retained.write_bytes(module.core.canonical_json(changed_digest))
    with pytest.raises(module.core.CompatibilityError, match="asset identity"):
        refresh(manifest_path, artifacts, head, **options)
    assert manifest_path.read_bytes() == original
    retained.write_bytes(module.core.canonical_json(evidence))
    prior_bytes = evidence_path.read_bytes()
    downgraded = deepcopy(evidence)
    downgraded["contracts"]["native_handoffs"].remove("chatgpt_auth")
    del downgraded["contracts"]["observations"]["native_handoffs"]["chatgpt_auth"]
    retained.write_bytes(module.core.canonical_json(downgraded))
    with pytest.raises(module.core.CompatibilityError, match="remove a qualified"):
        refresh(manifest_path, artifacts, head, **options)
    retained.write_bytes(module.core.canonical_json(evidence))
    replacement_path = evidence_path.with_name(f"ocr-{version}-{head}.json")
    replace = os.replace

    def interrupt_after_install(src, dst):
        replace(src, dst)
        if dst == manifest_path and Path(src).name == "new":
            raise KeyboardInterrupt

    with monkeypatch.context() as patch:
        patch.setattr(os, "replace", interrupt_after_install)
        with pytest.raises(KeyboardInterrupt):
            refresh(manifest_path, artifacts, head, **options)
    module.contracts.validate_manifest(json.loads(manifest_path.read_bytes()), tmp_path)
    assert manifest_path.read_bytes() == original and not replacement_path.exists()
    assert refresh(manifest_path, artifacts, head, **options)
    assert evidence_path.read_bytes() == prior_bytes
    assert replacement_path.read_bytes() == retained.read_bytes()
    refreshed = json.loads(manifest_path.read_bytes())
    assert refreshed["recommended_version"] == manifest["recommended_version"]
    module.contracts.validate_manifest(refreshed, tmp_path)
    assert refresh(manifest_path, artifacts, head, **options) == []


@pytest.mark.skipif(not hasattr(os, "getuid"), reason="POSIX native authentication")
@pytest.mark.parametrize("defect", [None, "directory-mode", "hardlinked-lock"])
def test_native_auth_capability_uses_runtime_store_admission(tmp_path, monkeypatch, defect):
    module = load_script()
    directory = tmp_path.resolve()
    binary = directory / "ocr"

    def status(cmd, **_):
        return "  auth    Authentication\n" if cmd[-1] == "--help" else ""

    def failed_review(cmd, **kwargs):
        store = Path(kwargs["env"]["HOME"]) / ".opencodereview/auth/chatgpt"
        store.mkdir(parents=True, mode=0o755 if defect == "directory-mode" else 0o700)
        store.chmod(0o755 if defect == "directory-mode" else 0o700)
        lock = store / "session.lock"
        lock.touch(mode=0o600)
        if defect == "hardlinked-lock":
            os.link(lock, store / "other.lock")
        return subprocess.CompletedProcess(cmd, 1, "", "ocr auth login --provider chatgpt")

    monkeypatch.setattr(module.execution, "_run", status)
    monkeypatch.setattr(subprocess, "run", failed_review)
    result = module.probes.handoffs.chatgpt_auth_handoff(binary, directory, "a", "b", directory)
    assert result is (defect is None)


def test_explicit_completion_cap_rejects_equal_float_as_provider_mismatch(tmp_path, monkeypatch):
    module = load_script()
    monkeypatch.setattr(module.execution, "_synthetic_repo", lambda *args: (tmp_path, "a", "b"))
    monkeypatch.setattr(module.execution, "_run", lambda *args, **kwargs: "")
    monkeypatch.setattr(module.peer, "_stub_gateway", lambda: nullcontext("http://localhost/v1"))
    monkeypatch.setattr(module.peer._StubHandler, "completion_caps", [4096.0])
    with pytest.raises(module.core.QualificationContractMismatch) as captured:
        module.numeric._completion_cap_probe(tmp_path / "ocr", tmp_path)
    assert captured.value.reason == "provider-contract"


@pytest.mark.parametrize("path", ["foreign.py", ["bad"]])
def test_budget_does_not_trust_self_reported_paths(path):
    module = load_script()
    sample = manifest_result("partial", selected=["done"], completed=["done"])
    sample["manifest"]["coverage"]["selected"][0]["path"] = path
    sample["comments"] = [{"path": path, "line": 2, "content": "Synthetic compatibility finding."}]
    with pytest.raises(module.core.QualificationContractMismatch, match="outside its fixture"):
        module.numeric._verify_completed_finding(sample, frozenset({"done.py"}))


def test_failed_rollback_continues_and_keeps_only_unrestored_backups(tmp_path, monkeypatch):
    module = load_script()
    first, second, last = [tmp_path / str(k) for k in range(3)]
    for path in (first, second, last):
        path.write_bytes(b"original")
    replace = os.replace

    def fail(source, target):
        if target == last and Path(source).name == "new":
            raise OSError("original install failure")
        if target == second and Path(source).name == "old":
            raise OSError("injected rollback failure")
        replace(source, target)

    monkeypatch.setattr(os, "replace", fail)
    with pytest.raises(module.core.CompatibilityError, match="rollback incomplete") as error:
        module.promotion._commit_outputs(
            [(path, b"replacement") for path in (first, second, last)], set()
        )
    assert str(error.value.__cause__) == "original install failure"
    (backup,) = list(tmp_path.glob(".ocr-promotion-*/old"))
    assert str(backup) in str(error.value)
    assert backup.read_bytes() == first.read_bytes() == last.read_bytes() == b"original"
    assert second.read_bytes() == b"replacement"


def test_new_or_changed_manifest_entry_cannot_claim_archived_schema_four(tmp_path):
    module = load_script()
    shutil.copytree(module.settings.ROOT / "compatibility", tmp_path / "compatibility")
    manifest_path = tmp_path / "compatibility/ocr-support.json"
    manifest = json.loads(manifest_path.read_bytes())
    row = next(item for item in manifest["releases"] if item["version"] == "1.14.2")
    original = tmp_path / "compatibility/evidence/ocr-1.14.2.json"
    modified = json.loads(original.read_bytes())
    modified["classification_reasons"] = ["synthetic replacement"]
    payload = module.core.canonical_json(modified)
    original.write_bytes(payload)
    row.update(
        evidence_sha256=hashlib.sha256(payload).hexdigest(),
        evidence="compatibility/evidence/ocr-1.14.2.json",
    )
    with pytest.raises(module.core.CompatibilityError, match="behavioral evidence schema 5"):
        module.contracts.validate_manifest(manifest, tmp_path)


@pytest.mark.parametrize("marker, proves_mismatch", [("COMPARISON_BASE_ONLY", True), ("", False)])
def test_comparison_driver_only_classifies_observed_wrong_revision(
    tmp_path, monkeypatch, marker, proves_mismatch
):
    from tests.test_ocr_comparison import history, schemas

    module = load_script()
    binary = tmp_path / "candidate"
    runner = module.execution._run

    def native_or_git(cmd, **kwargs):
        if cmd[0] != str(binary):
            return runner(cmd, **kwargs)
        conversation = module.peer._StubHandler.tool_script
        _, call_id = conversation({"tools": schemas()})
        try:
            conversation({"messages": history(conversation.cases[0], call_id, marker)})
        except module.core.CompatibilityError:
            # Native sees an HTTP failure when the fixture rejects its observation.
            raise module.core.CompatibilityError("controlled peer exited") from None
        pytest.fail("peer accepted wrong content")

    monkeypatch.setattr(module.execution, "_run", native_or_git)
    with pytest.raises(module.core.CompatibilityError) as error:
        module.comparison.comparison_sides_probe(binary, tmp_path)
    assert isinstance(error.value, module.core.QualificationContractMismatch) is proves_mismatch
    if proves_mismatch:
        assert error.value.reason == "range-contract"


@pytest.mark.parametrize(
    "field,value",
    [
        ("target_tip", "used"),
        ("invalid_sides_rejected", False),
        ("renamed_paths", "worktree"),
        ("default_side", "old"),
        ("deleted_paths", "both"),
    ],
)
def test_contradictory_comparison_observation_is_rejected(field, value):
    module = load_script()
    sample = module.core.load_json(module.settings.ROOT / "compatibility/evidence/ocr-1.14.2.json")
    sample["schema_version"] = 5
    observations = sample["contracts"]["observations"]
    observations["native_handoffs"] = {
        "analysis": {"status": "completed", "citations_verified": True},
        "chatgpt_auth": {"login_required": True, "store_admitted": True},
        "diagram_output": {"consumer": "toolkit-local", "rendered": True},
        "gitlink_projection": {"consumer": "toolkit-local", "immutable_range": True},
    }
    prior = module.core.load_json(module.settings.ROOT / "compatibility/evidence/ocr-1.13.13.json")
    observations["comparison_sides"] = prior["contracts"]["comparison_sides_probe"] | {field: value}
    with pytest.raises(module.core.CompatibilityError, match="comparison-side observations"):
        module.contracts._validate_evidence_contracts("1.14.2", sample)
