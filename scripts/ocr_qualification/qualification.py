"""Coordinate verified assets, real probes and qualification evidence."""

from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path
from typing import Any

from . import assets as asset_io
from . import contracts as contract_rules
from . import core, delivery, probes, promotion, settings


def qualify_release(
    release: dict[str, Any],
    manifest: dict[str, Any],
    output: Path,
    *,
    comparison_version: str | None = None,
    tested_baseline_version: str | None = None,
) -> dict[str, Any]:
    """Download, verify, execute, and classify one upstream release."""

    def metadata() -> tuple[str, str, list[core.Asset]]:
        tag = release.get("tag_name")
        if not isinstance(tag, str) or settings.VERSION_RE.fullmatch(tag) is None:
            core._fail("candidate tag is not a stable semantic version")
        contract_rules._require_live_qualification_version(tag.removeprefix("v"))
        if os.environ.get("RUNNER_OS") != "Linux":
            core._fail(
                "candidate execution requires a Linux runner; checksum validation is cross-platform"
            )
        return tag, tag.removeprefix("v"), asset_io.release_assets(release)

    tag, version, assets = core._qualification_stage("metadata", "metadata-invalid", metadata)
    with tempfile.TemporaryDirectory(prefix="ocr-compat-") as temp_value:
        temp = Path(temp_value)

        def artifacts() -> dict[str, Path]:
            downloaded = {asset.name: asset_io._download(asset, temp) for asset in assets}
            checksums = asset_io.parse_checksum_file(downloaded["sha256sum.txt"])
            binaries = {
                asset.name: asset.sha256 for asset in assets if asset.name != "sha256sum.txt"
            }
            if checksums != binaries:
                core._fail("upstream checksum file and GitHub asset digests disagree")
            return downloaded

        downloaded = core._qualification_stage(
            "artifact", "artifact-verification-failed", artifacts
        )
        contracts = core._qualification_stage(
            "contracts",
            "contract-probe-failed",
            lambda: probes.run_contracts(downloaded["opencodereview-linux-amd64"], version, temp),
        )
    raw_notes = release.get("body")
    notes = raw_notes if isinstance(raw_notes, str) else ""
    tested_baseline = tested_baseline_version or str(manifest["recommended_version"])
    comparison = comparison_version or tested_baseline
    core._version(tested_baseline)
    core._version(comparison)
    if tested_baseline != manifest["recommended_version"]:
        core._fail("candidate qualification tested baseline is stale")
    if core._version(comparison) < core._version(tested_baseline):
        core._fail("candidate comparison version predates the tested baseline")
    classification, reasons = promotion.classify_candidate(
        comparison_version=comparison,
        version=version,
        release_notes=notes,
        contracts_passed=True,
    )
    evidence = {
        "schema_version": 3,
        "upstream_repository": settings.UPSTREAM_REPOSITORY,
        "version": version,
        "tag": tag,
        "published_at": release.get("published_at"),
        "result": "compatible",
        "classification": classification,
        "classification_reasons": reasons,
        "comparison_version": comparison,
        "tested_baseline_version": tested_baseline,
        "assets": [
            {"name": asset.name, "sha256": asset.sha256, "size": asset.size} for asset in assets
        ],
        "contracts": contracts,
        "release_changes": delivery.release_changes_excerpt(notes),
        "release_notes_sha256": hashlib.sha256(notes.encode()).hexdigest(),
    }

    def write_evidence() -> None:
        core.write_atomic_bytes(
            output, core.canonical_json(evidence), label="compatibility evidence"
        )

    core._qualification_stage("evidence", "evidence-write-failed", write_evidence)
    return evidence
