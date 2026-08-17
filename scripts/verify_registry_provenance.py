#!/usr/bin/env python3
"""Validate PyPI Integrity API publisher and exact artifact subjects."""

from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path
from typing import Any


class ProvenanceError(ValueError):
    """Registry provenance is missing or does not match the expected workflow."""


def verify_provenance(
    payload: dict[str, Any],
    *,
    filename: str,
    digest: str,
    environment: str,
    repository: str,
    workflow: str,
) -> None:
    """Require one GitHub publisher bundle with the exact publish subject."""

    bundles = payload.get("attestation_bundles")
    if payload.get("version") != 1 or not isinstance(bundles, list) or len(bundles) != 1:
        raise ProvenanceError("integrity response must contain one version-1 bundle")
    bundle = bundles[0]
    publisher = bundle.get("publisher") if isinstance(bundle, dict) else None
    expected_publisher = {
        "kind": "GitHub",
        "repository": repository,
        "workflow": workflow,
        "environment": environment,
    }
    if publisher != expected_publisher:
        raise ProvenanceError("integrity publisher does not match the expected workflow")
    attestations = bundle.get("attestations")
    if not isinstance(attestations, list) or not attestations:
        raise ProvenanceError("integrity bundle has no attestations")
    expected_subject = [{"name": filename, "digest": {"sha256": digest}}]
    matched = False
    for attestation in attestations:
        envelope = attestation.get("envelope") if isinstance(attestation, dict) else None
        statement = envelope.get("statement") if isinstance(envelope, dict) else None
        if not isinstance(statement, str):
            continue
        try:
            decoded = json.loads(base64.b64decode(statement, validate=True))
        except (ValueError, json.JSONDecodeError):
            continue
        if (
            isinstance(decoded, dict)
            and decoded.get("_type") == "https://in-toto.io/Statement/v1"
            and decoded.get("subject") == expected_subject
            and decoded.get("predicateType") == "https://docs.pypi.org/attestations/publish/v1"
        ):
            matched = True
    if not matched:
        raise ProvenanceError("integrity bundle has no exact publish-attestation subject")


def main() -> int:
    """CLI entrypoint used after bounded registry provenance downloads."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", required=True, type=Path)
    parser.add_argument("--hashes", required=True, type=Path)
    parser.add_argument("--filename", required=True)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--workflow", required=True)
    args = parser.parse_args()
    payload = json.loads(args.payload.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ProvenanceError("integrity response must be a JSON object")
    hashes = json.loads(args.hashes.read_text(encoding="utf-8"))
    if not isinstance(hashes, dict) or args.filename not in hashes:
        raise ProvenanceError("integrity subject is not in the reviewed artifact set")
    digest = hashes[args.filename]
    if not isinstance(digest, str):
        raise ProvenanceError("integrity subject digest is invalid")
    verify_provenance(
        payload,
        filename=args.filename,
        digest=digest,
        environment=args.environment,
        repository=args.repository,
        workflow=args.workflow,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
