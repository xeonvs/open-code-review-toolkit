"""Refresh deployed-version evidence from a complete hosted qualification window."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from . import assets, contracts, core, delivery, promotion, settings


def refresh_receipts(
    manifest_path: Path,
    artifacts: Path,
    head: str,
    *,
    after_tag: str,
    through_tag: str,
) -> list[Path]:
    """Rebind successful same-asset receipts without advancing the release line."""

    root = manifest_path.resolve().parents[1]
    manifest = core.load_json(manifest_path)
    contracts.validate_manifest(manifest, root)
    releases = assets.retained_window(manifest, after_tag=after_tag, through_tag=through_tag)
    matrix = assets.qualification_matrix(manifest, releases, after_tag=after_tag)["include"]
    if (
        not re.fullmatch(r"[a-f0-9]{40}", head)
        or len(matrix) != len(releases) - 1
        or not matrix
        or not artifacts.is_dir()
        or {item.name for item in artifacts.iterdir()}
        != {f"ocr-compatibility-{entry['tag']}" for entry in matrix}
    ):
        core._fail("refresh requires the complete requested candidate artifact window and checkout")

    supported, _ = contracts.qualified_runtime_versions(manifest)
    inventory_path = root / "src" / "ocr_toolkit" / "_qualified_handoffs.json"
    inventory = core.load_json(inventory_path)
    records = {item["version"]: item for item in manifest["releases"]}
    writes: list[tuple[Path, bytes]] = []
    new_receipts: set[Path] = set()
    for entry in matrix:
        tag = entry["tag"]
        version = tag.removeprefix("v")
        if version not in supported:
            core._fail("refresh only accepts currently supported tested versions")
        record = records[version]
        _, observed = delivery._candidate_record(
            artifacts / f"ocr-compatibility-{tag}", entry, head
        )
        if (
            observed is None
            or observed["assets"] != record["assets"]
            or observed.get("published_at") != record["published_at"]
        ):
            core._fail("requalification did not confirm the original release asset identity")
        payload = core.canonical_json(observed)
        record["evidence_sha256"] = hashlib.sha256(payload).hexdigest()
        capabilities = observed["contracts"].get("optional_capabilities", [])
        if (
            not isinstance(capabilities, list)
            or not all(isinstance(item, str) for item in capabilities)
            or not set(capabilities) <= settings.KNOWN_OPTIONAL_CAPABILITIES
            or capabilities != sorted(set(capabilities))
        ):
            core._fail("invalid optional capabilities in requalification")
        if not set(inventory[version]).issubset(observed["contracts"]["native_handoffs"]):
            core._fail("same-asset refresh would remove a qualified native handoff")
        record["capabilities"] = capabilities
        inventory[version] = observed["contracts"]["native_handoffs"]
        record["qualification_checkout"] = head
        record["evidence"] = f"compatibility/evidence/ocr-{version}-{head}.json"
        destination = root / record["evidence"]
        if promotion._generated_destination(destination, payload):
            writes.append((destination, payload))
            new_receipts.add(destination)
    writes.extend(
        [
            (inventory_path, core.canonical_json(inventory)),
            (manifest_path, core.canonical_json(manifest)),
        ]
    )
    changed = [
        (path, data) for path, data in writes if path in new_receipts or path.read_bytes() != data
    ]
    promotion._commit_outputs(changed, new_receipts)
    return [path for path, _ in changed]
