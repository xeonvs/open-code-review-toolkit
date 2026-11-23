"""Register bounded, reproducible property-test profiles for the shared suite."""

import hashlib
import json
import os
import platform
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from hypothesis import settings

from ocr_toolkit import native_capabilities, preflight

settings.register_profile(
    "ocr-ci", max_examples=100, derandomize=True, database=None, deadline=1000, print_blob=False
)
settings.register_profile("ocr-local", parent=settings.get_profile("ocr-ci"), max_examples=1000)
settings.load_profile("ocr-ci")


@pytest.fixture
def isolated_review_workspace(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Keep CLI-owned locks/artifacts outside the developer's active checkout."""

    # Use a separate directory from tmp_path: output-destination tests assert
    # that rejected invocations leave their output directory completely empty.
    monkeypatch.chdir(tmp_path_factory.mktemp("review-workspace"))


def _native_assets(
    releases: list[dict[str, Any]], asset_name: str, receipt: str | None
) -> dict[str, tuple[str, int]]:
    """Select exactly the workflow receipt when qualifying a new executable."""
    if receipt is not None:
        candidate = json.loads(receipt)
        return {candidate["sha256"]: (candidate["version"], candidate["size"])}
    known: dict[str, tuple[str, int]] = {}
    for release in releases:
        if release["status"] != "tested":
            continue
        for asset in release["assets"]:
            if asset["name"] == asset_name:
                known[asset["sha256"]] = (release["version"], asset["size"])
    return known


@pytest.fixture(scope="session")
def native_candidate_inventory() -> Callable[[str], tuple[str, str] | None]:
    """Verify the selected executable against its platform or candidate asset."""

    system = platform.system().lower()
    machine = {"arm64": "arm64", "aarch64": "arm64", "x86_64": "amd64", "AMD64": "amd64"}
    asset_name = f"opencodereview-{system}-{machine.get(platform.machine(), 'unknown')}"
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "compatibility" / "ocr-support.json").read_text(encoding="utf-8"))
    known = _native_assets(
        manifest["releases"], asset_name, os.environ.get("OCR_QUALIFY_CANDIDATE")
    )

    def select(variable: str) -> tuple[str, str] | None:
        binary = os.environ.get(variable)
        if not binary:
            return None
        with Path(binary).open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
            assert digest in known, "native qualification requires an exact official platform asset"
            version, size = known[digest]
            assert os.fstat(stream.fileno()).st_size == size, (
                "native asset size differs from receipt"
            )
        return binary, version

    return select


@pytest.fixture
def qualified_native_ocr(
    native_candidate_inventory: Callable[[str], tuple[str, str] | None],
    monkeypatch: pytest.MonkeyPatch,
) -> Callable[[str], tuple[str, str]]:
    """Admit a verified candidate only inside opt-in tests, before public promotion."""

    def select(variable: str) -> tuple[str, str]:
        candidate = native_candidate_inventory(variable)
        if candidate is None:
            pytest.skip(f"set {variable} to an official checksum-verified OCR executable")
        binary, version = candidate
        monkeypatch.setattr(
            preflight, "SUPPORTED_OCR_VERSIONS", (*preflight.SUPPORTED_OCR_VERSIONS, version)
        )
        assert preflight.validate_ocr_binary(executable=binary, announce=False) == version, (
            "native executable version differs from receipt"
        )
        if os.environ.get("OCR_QUALIFY_CANDIDATE"):
            monkeypatch.setitem(
                native_capabilities._QUALIFIED_HANDOFFS,
                version,
                frozenset({"diagram_output", "gitlink_projection"}),
            )
        return binary, version

    return select
