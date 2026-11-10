"""Register bounded, reproducible property-test profiles for the shared suite."""

import hashlib
import json
import os
import platform
from collections.abc import Callable
from pathlib import Path

import pytest
from hypothesis import settings

from ocr_toolkit import preflight

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


@pytest.fixture(scope="session")
def native_candidate_inventory() -> Callable[[str], tuple[str, str] | None]:
    """Verify only the requested opt-in binary, caching successful identities."""

    system = platform.system().lower()
    machine = {"arm64": "arm64", "aarch64": "arm64", "x86_64": "amd64", "AMD64": "amd64"}
    asset_name = f"opencodereview-{system}-{machine.get(platform.machine(), 'unknown')}"
    root = Path(__file__).resolve().parents[1]
    known: dict[str, tuple[str, int]] = {}
    for version in ("1.13.2", "1.13.3", "1.13.4", "1.13.5", "1.13.6", "1.13.7"):
        path = root / "compatibility" / "evidence" / f"ocr-{version}.json"
        for asset in json.loads(path.read_text(encoding="utf-8"))["assets"]:
            if asset["name"] == asset_name:
                known[asset["sha256"]] = (version, asset["size"])
    result: dict[tuple[str, str], tuple[str, str]] = {}

    def select(variable: str) -> tuple[str, str] | None:
        binary = os.environ.get(variable)
        if not binary:
            return None
        key = (variable, binary)
        if key not in result:
            assert Path(binary).stat().st_size in {item[1] for item in known.values()}
            with Path(binary).open("rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
            assert digest in known, "native qualification requires an exact official platform asset"
            result[key] = (binary, known[digest][0])
        return result[key]

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
        assert preflight.validate_ocr_binary(executable=binary, announce=False) == version
        return binary, version

    return select
