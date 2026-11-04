"""Validate OCR support metadata and qualify checksum-pinned upstream candidates."""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path
from typing import Any

from . import assets, core, delivery, probes, promotion, qualification, settings
from . import contracts as contract_rules


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=settings.DEFAULT_MANIFEST)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("validate")
    discover = subparsers.add_parser("discover")
    discover.add_argument("--output", type=Path, required=True)
    discover.add_argument("--through-tag")
    matrix = subparsers.add_parser("build-matrix")
    matrix.add_argument("--releases", type=Path, required=True)
    matrix.add_argument("--output", type=Path, required=True)
    qualify = subparsers.add_parser("qualify")
    qualify.add_argument("--tag", required=True)
    qualify.add_argument("--comparison-version")
    qualify.add_argument("--tested-baseline-version")
    qualify.add_argument("--output", type=Path, required=True)
    qualify.add_argument("--issue-body", type=Path)
    qualify.add_argument("--status-output", type=Path)
    setup_failure = subparsers.add_parser("record-setup-failure")
    setup_failure.add_argument("--tag", required=True)
    setup_failure.add_argument("--comparison-version", required=True)
    setup_failure.add_argument("--tested-baseline-version", required=True)
    setup_failure.add_argument("--status-output", type=Path, required=True)
    assess = subparsers.add_parser("assess-chain")
    assess.add_argument("--evidence", type=Path, action="append", required=True)
    assess.add_argument("--output", type=Path, required=True)
    prepare = subparsers.add_parser("prepare-update")
    prepare.add_argument("--evidence", type=Path, action="append", required=True)
    prepare.add_argument("--human-conclusion", action="append", default=[])
    prepare.add_argument("--fragment-number", type=int, required=True)
    probe_local = subparsers.add_parser("probe-local")
    probe_local.add_argument("--binary", type=Path, required=True)
    probe_local.add_argument("--version", required=True)
    probe_local.add_argument("--output", type=Path, required=True)
    upsert_issue = subparsers.add_parser("upsert-issue")
    upsert_input = upsert_issue.add_mutually_exclusive_group(required=True)
    upsert_input.add_argument("--evidence", type=Path)
    upsert_input.add_argument("--status", type=Path)
    upsert_issue.add_argument("--repository", required=True)
    upsert_issue.add_argument("--run-url", required=True)
    upsert_issue.add_argument("--output-number", type=Path, required=True)
    args = parser.parse_args(argv)
    manifest: dict[str, Any] | None = None

    if args.command == "record-setup-failure":
        status = contract_rules.qualification_status(
            tag=args.tag,
            comparison_version=args.comparison_version,
            tested_baseline_version=args.tested_baseline_version,
            result="failed",
            phase="environment",
            reason="dependency-setup-failed",
        )
        core.write_atomic_bytes(
            args.status_output,
            core.canonical_json(status),
            label="compatibility status",
        )
        return 0

    def finish_issue_upsert(
        *, evidence: dict[str, Any] | None = None, status: dict[str, Any] | None = None
    ) -> int:
        issue_number = delivery.upsert_qualification_issue(
            repository=args.repository,
            evidence=evidence,
            status=status,
            run_url=args.run_url,
        )
        core.write_atomic_bytes(
            args.output_number,
            f"{issue_number}\n".encode(),
            label="qualification issue number",
        )
        print(f"qualification issue: #{issue_number}")
        return 0

    try:
        if args.command == "upsert-issue" and args.status is not None:
            return finish_issue_upsert(status=core.load_json(args.status))
        manifest = core.load_json(args.manifest)
        contract_rules.validate_manifest(manifest, args.manifest.resolve().parents[1])
        if args.command == "validate":
            print("OCR support manifest validated")
            return 0
        if args.command == "discover":
            unseen = assets.discover_unseen(manifest, through_tag=args.through_tag)
            args.output.write_bytes(core.canonical_json({"releases": unseen}))
            print(f"discovered {len(unseen)} unseen stable OCR release(s)")
            return 0
        if args.command == "build-matrix":
            release_payload = core.load_json(args.releases)
            releases = release_payload.get("releases")
            if not isinstance(releases, list):
                core._fail("discovery payload must contain a release list")
            result = assets.qualification_matrix(manifest, releases)
            args.output.write_bytes(core.canonical_json(result))
            print(f"built qualification matrix with {len(result['include'])} release(s)")
            return 0
        if args.command == "assess-chain":
            evidences = [core.load_json(path) for path in args.evidence]
            result = promotion.assess_automatic_chain(manifest, evidences)
            args.output.write_bytes(core.canonical_json(result))
            print(f"assessed OCR chain: {result['classification']}")
            return 0
        if args.command == "prepare-update":
            evidences = [core.load_json(path) for path in args.evidence]
            changed = promotion.prepare_update(
                manifest_path=args.manifest,
                evidence=evidences,
                fragment_number=args.fragment_number,
                human_conclusions=promotion.parse_human_conclusions(args.human_conclusion),
            )
            print("prepared OCR compatibility update:")
            for path in changed:
                print(path.resolve().relative_to(settings.ROOT))
            return 0
        if args.command == "upsert-issue":
            assert args.evidence is not None
            return finish_issue_upsert(evidence=core.load_json(args.evidence))
        if args.command == "probe-local":
            version = args.version.removeprefix("v")
            contract_rules._require_live_qualification_version(version)
            binary = args.binary.resolve(strict=True)
            if not binary.is_file():
                core._fail("local OCR binary must be a regular file")
            with tempfile.TemporaryDirectory(prefix="ocr-local-probe-") as temp_value:
                contracts = probes.run_contracts(binary, version, Path(temp_value))
            receipt = {"contracts": contracts, "result": "compatible", "version": version}
            args.output.write_bytes(core.canonical_json(receipt))
            print(f"local OCR {version} contract probes passed")
            return 0
        try:
            release = assets._request_json(f"{settings.UPSTREAM_API}/releases/tags/{args.tag}")
        except core.CompatibilityError as exc:
            raise core.QualificationStageError(
                str(exc), phase="metadata", reason="metadata-request-failed"
            ) from exc
        if not isinstance(release, dict):
            core._fail("upstream tag response must be an object")
        evidence = qualification.qualify_release(
            release,
            manifest,
            args.output,
            comparison_version=args.comparison_version,
            tested_baseline_version=args.tested_baseline_version,
        )
        if args.issue_body is not None:
            core._qualification_stage(
                "evidence",
                "issue-body-write-failed",
                lambda: core.write_atomic_bytes(
                    args.issue_body,
                    delivery.render_issue(evidence).encode(),
                    label="qualification issue body",
                ),
            )
        if args.status_output is not None:
            status = contract_rules.qualification_status(
                tag=args.tag,
                comparison_version=args.comparison_version or str(manifest["recommended_version"]),
                tested_baseline_version=args.tested_baseline_version
                or str(manifest["recommended_version"]),
                result="compatible",
                phase="complete",
                reason="compatible",
            )
            core._qualification_stage(
                "evidence",
                "status-write-failed",
                lambda: core.write_atomic_bytes(
                    args.status_output,
                    core.canonical_json(status),
                    label="compatibility status",
                ),
            )
        print(f"qualified OCR {evidence['version']}: {evidence['classification']}")
        return 0
    except Exception as exc:
        if args.command != "qualify" and not isinstance(exc, core.CompatibilityError):
            raise
        if args.command == "qualify" and args.status_output is not None:
            phase = exc.phase if isinstance(exc, core.QualificationStageError) else "metadata"
            if isinstance(exc, core.QualificationStageError):
                reason = exc.reason
            elif isinstance(exc, core.CompatibilityError):
                reason = "metadata-invalid"
            else:
                reason = "unexpected-error"
            manifest_version = (
                str(manifest["recommended_version"])
                if isinstance(manifest, dict) and "recommended_version" in manifest
                else ""
            )
            try:
                status = contract_rules.qualification_status(
                    tag=args.tag,
                    comparison_version=args.comparison_version or manifest_version,
                    tested_baseline_version=args.tested_baseline_version or manifest_version,
                    result="failed",
                    phase=phase,
                    reason=reason,
                )
                core.write_atomic_bytes(
                    args.status_output,
                    core.canonical_json(status),
                    label="compatibility status",
                )
            except Exception as status_exc:
                status_detail = (
                    str(status_exc)
                    if isinstance(status_exc, core.CompatibilityError)
                    else f"unexpected {type(status_exc).__name__}"
                )
                print(f"OCR compatibility status write failed: {status_detail}", file=sys.stderr)
        detail = (
            str(exc)
            if isinstance(exc, core.CompatibilityError)
            else f"unexpected {type(exc).__name__}"
        )
        print(f"OCR compatibility qualification failed: {detail}", file=sys.stderr)
        return 1
