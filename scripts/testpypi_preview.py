#!/usr/bin/env python3
"""Deterministic development versioning and PEP 691 release checks."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

PACKAGE = "open-code-review-toolkit"
DIST_PREFIX = "open_code_review_toolkit"
DEFAULT_NEXT_VERSION_FILE = Path(".next-version")
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
VERSION_RE = re.compile(
    r"^(?:[1-9][0-9]*!)?[0-9]+(?:\.[0-9]+)+"
    r"(?:(?:a|b|rc)[0-9]+)?(?:\.post[0-9]+)?(?:\.dev[0-9]+)?$"
)
ARTIFACT_HOST = "test-files.pythonhosted.org"
PYPI_ARTIFACT_HOST = "files.pythonhosted.org"
ALLOWED_ARTIFACT_HOSTS = frozenset({ARTIFACT_HOST, PYPI_ARTIFACT_HOST})


class PreviewError(ValueError):
    """The requested preview state is invalid or conflicts with TestPyPI."""


def development_version(run_number: int, next_version: str) -> str:
    """Map one immutable workflow run number to a development version."""

    if run_number < 1:
        raise PreviewError(f"workflow run number must be positive; got {run_number}")
    if not VERSION_RE.fullmatch(next_version) or any(
        marker in next_version for marker in ("a", "b", "rc", "post", "dev")
    ):
        raise PreviewError(f"next version must be a canonical final release: {next_version}")
    return f"{next_version}.dev{run_number}"


def expected_filenames(version: str) -> dict[str, str]:
    """Return the exact universal wheel and sdist names for a release."""

    if not VERSION_RE.fullmatch(version):
        raise PreviewError(f"unsupported release version: {version}")
    filename_version = re.sub(r"[^A-Za-z0-9.]+", "_", version)
    return {
        f"{DIST_PREFIX}-{filename_version}-py3-none-any.whl": "wheel",
        f"{DIST_PREFIX}-{filename_version}.tar.gz": "sdist",
    }


def _validate_local_hashes(version: str, expected_hashes: dict[str, str]) -> None:
    names = expected_filenames(version)
    if set(expected_hashes) != set(names) or not all(
        SHA256_RE.fullmatch(digest) for digest in expected_hashes.values()
    ):
        raise PreviewError("local build does not contain the exact SHA-256 artifact set")


def classify_index(payload: dict[str, Any], version: str, expected_hashes: dict[str, str]) -> str:
    """Return publish/already-published or fail on a conflicting artifact set."""

    names = expected_filenames(version)
    _validate_local_hashes(version, expected_hashes)

    files = payload.get("files")
    if not isinstance(files, list):
        raise PreviewError("PEP 691 response field 'files' must be a list")

    found: dict[str, str] = {}
    for item in files:
        if not isinstance(item, dict):
            raise PreviewError("PEP 691 file entries must be objects")
        filename = item.get("filename")
        if not isinstance(filename, str):
            continue
        version_prefix = f"{DIST_PREFIX}-{version}"
        if filename not in names:
            suffix = filename.removeprefix(version_prefix)
            if suffix != filename and suffix.startswith("-"):
                raise PreviewError(f"unexpected TestPyPI artifact for {version}: {filename}")
            continue
        hashes = item.get("hashes")
        digest = hashes.get("sha256") if isinstance(hashes, dict) else None
        if not isinstance(digest, str) or not digest:
            raise PreviewError(f"{filename} has no SHA-256 digest")
        if filename in found:
            raise PreviewError(f"duplicate TestPyPI artifact: {filename}")
        found[filename] = digest

    if not found:
        return "publish"
    if set(found) != set(names):
        missing = sorted(set(names) - set(found))
        raise PreviewError(f"partial TestPyPI release for {version}; missing {missing}")
    mismatches = [
        filename for filename, digest in found.items() if expected_hashes.get(filename) != digest
    ]
    if mismatches:
        raise PreviewError(f"TestPyPI SHA-256 mismatch for {sorted(mismatches)}")
    return "already-published"


def artifact_manifest(
    payload: dict[str, Any],
    version: str,
    expected_hashes: dict[str, str] | None = None,
    artifact_host: str = ARTIFACT_HOST,
    provenance_host: str | None = None,
) -> list[dict[str, str]]:
    """Return validated immutable download metadata for one complete release."""

    if artifact_host not in ALLOWED_ARTIFACT_HOSTS:
        raise PreviewError(f"unsupported artifact host: {artifact_host}")
    expected_provenance_host = provenance_host or (
        "pypi.org" if artifact_host == PYPI_ARTIFACT_HOST else "test.pypi.org"
    )
    if expected_provenance_host not in {"pypi.org", "test.pypi.org"}:
        raise PreviewError(f"unsupported provenance host: {expected_provenance_host}")
    if expected_hashes is not None:
        _validate_local_hashes(version, expected_hashes)
    names = expected_filenames(version)
    files = payload.get("files")
    if not isinstance(files, list):
        raise PreviewError("PEP 691 response field 'files' must be a list")

    manifest: dict[str, dict[str, str]] = {}
    for item in files:
        if not isinstance(item, dict) or item.get("filename") not in names:
            continue
        filename = item["filename"]
        hashes = item.get("hashes")
        digest = hashes.get("sha256") if isinstance(hashes, dict) else None
        url = item.get("url")
        provenance_url = item.get("provenance")
        if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            raise PreviewError(f"{filename} has no valid SHA-256 digest")
        if not isinstance(url, str):
            raise PreviewError(f"{filename} has no download URL")
        if not isinstance(provenance_url, str):
            raise PreviewError(f"{filename} has no provenance URL")
        parsed = urlsplit(url)
        provenance = urlsplit(provenance_url)
        try:
            port = parsed.port
            provenance_port = provenance.port
        except ValueError as exc:
            raise PreviewError(f"{filename} has an invalid registry URL") from exc
        if (
            parsed.scheme != "https"
            or parsed.hostname != artifact_host
            or port not in (None, 443)
            or parsed.username is not None
            or parsed.password is not None
            or parsed.fragment
            or any(ord(character) <= 0x20 or ord(character) == 0x7F for character in url)
            or Path(parsed.path).name != filename
        ):
            raise PreviewError(f"{filename} has an untrusted download URL")
        expected_provenance_path = f"/integrity/{PACKAGE}/{version}/{filename}/provenance"
        if (
            provenance.scheme != "https"
            or provenance.hostname != expected_provenance_host
            or provenance_port not in (None, 443)
            or provenance.username is not None
            or provenance.password is not None
            or provenance.query
            or provenance.fragment
            or any(ord(character) <= 0x20 or ord(character) == 0x7F for character in provenance_url)
            or provenance.path != expected_provenance_path
        ):
            raise PreviewError(f"{filename} has an untrusted provenance URL")
        if expected_hashes is not None and digest != expected_hashes[filename]:
            raise PreviewError(f"published SHA-256 mismatch for {filename}")
        if filename in manifest:
            raise PreviewError(f"duplicate TestPyPI artifact: {filename}")
        manifest[filename] = {
            "filename": filename,
            "sha256": digest,
            "url": url,
            "provenance": provenance_url,
        }

    if set(manifest) != set(names):
        raise PreviewError(f"TestPyPI release {version} is incomplete")
    return [manifest[filename] for filename in sorted(manifest)]


def load_hashes(path: Path) -> dict[str, str]:
    """Load a filename-to-SHA-256 mapping generated by the build job."""

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not all(
        isinstance(key, str) and isinstance(value, str) for key, value in data.items()
    ):
        raise PreviewError("artifact hash file must be a string mapping")
    return data


def main() -> int:
    """CLI entrypoint used by the TestPyPI workflow."""

    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    version_parser = subparsers.add_parser("development-version")
    version_parser.add_argument("--run-number", required=True, type=int)
    version_parser.add_argument("--next-version-file", type=Path, default=DEFAULT_NEXT_VERSION_FILE)

    check_parser = subparsers.add_parser("check-index")
    check_parser.add_argument("--version", required=True)
    check_parser.add_argument("--index-json", required=True, type=Path)
    check_parser.add_argument("--hashes-json", required=True, type=Path)

    manifest_parser = subparsers.add_parser("artifact-manifest")
    manifest_parser.add_argument("--version", required=True)
    manifest_parser.add_argument("--index-json", required=True, type=Path)
    manifest_parser.add_argument("--hashes-json", type=Path)
    manifest_parser.add_argument(
        "--artifact-host", choices=sorted(ALLOWED_ARTIFACT_HOSTS), default=ARTIFACT_HOST
    )

    args = parser.parse_args()
    try:
        if args.command == "development-version":
            next_version = args.next_version_file.read_text(encoding="utf-8").strip()
            print(development_version(args.run_number, next_version))
        elif args.command == "check-index":
            payload = json.loads(args.index_json.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise PreviewError("PEP 691 response must be a JSON object")
            print(classify_index(payload, args.version, load_hashes(args.hashes_json)))
        else:
            payload = json.loads(args.index_json.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise PreviewError("PEP 691 response must be a JSON object")
            hashes = load_hashes(args.hashes_json) if args.hashes_json else None
            print(
                json.dumps(
                    artifact_manifest(payload, args.version, hashes, args.artifact_host),
                    sort_keys=True,
                )
            )
    except (OSError, json.JSONDecodeError, PreviewError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
