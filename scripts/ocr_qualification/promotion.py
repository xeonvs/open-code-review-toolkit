"""Classify adjacent candidates and prepare reviewed support updates."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any

from . import contracts as contract_rules
from . import core, settings


def classify_candidate(
    *, comparison_version: str, version: str, release_notes: str, contracts_passed: bool
) -> tuple[str, list[str]]:
    """Classify only unambiguous same-minor patches as automatic-safe."""

    base = core._version(comparison_version)
    candidate = core._version(version)
    reasons: list[str] = []
    if candidate[:2] != base[:2] or candidate[2] != base[2] + 1:
        reasons.append("candidate is not a newer patch in the tested major/minor line")
    if not contracts_passed:
        reasons.append("one or more deterministic compatibility probes failed")
    if settings.MATERIAL_NOTES_RE.search(release_notes):
        reasons.append("release notes contain a material or ambiguous compatibility signal")
    if not settings.SAFE_NOTES_RE.search(release_notes):
        reasons.append("release notes do not contain an allowlisted maintenance signal")
    if reasons:
        return "human-review-required", reasons
    return "automatic-safe", ["same-minor patch passed all probes with maintenance-only notes"]


def _replace_exact(text: str, old: str, new: str, *, source: str) -> str:
    count = text.count(old)
    if count != 1:
        core._fail(f"expected exactly one {source} occurrence of {old!r}, found {count}")
    return text.replace(old, new)


def _render_python_constant(name: str, value: str | tuple[str, ...]) -> str:
    """Render one Ruff-stable top-level string or tuple assignment."""

    if isinstance(value, str):
        return f"{name} = {json.dumps(value)}"
    items = "".join(f"    {json.dumps(item)},\n" for item in value)
    return f"{name} = (\n{items})"


def _replace_python_constant(
    text: str,
    name: str,
    old: str | tuple[str, ...],
    new: str | tuple[str, ...],
) -> str:
    """Replace one literal assignment after exact AST ownership validation."""

    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        raise core.CompatibilityError("preflight source is not valid Python") from exc
    matches = [
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id == name
    ]
    if len(matches) != 1:
        core._fail(f"preflight must define exactly one {name} assignment")
    node = matches[0]
    try:
        observed = ast.literal_eval(node.value)
    except (ValueError, TypeError) as exc:
        raise core.CompatibilityError(f"preflight {name} must be a literal") from exc
    if observed != old:
        core._fail(f"preflight {name} does not match the manifest")
    source = ast.get_source_segment(text, node)
    if source is None:
        core._fail(f"preflight {name} source range is unavailable")
    return _replace_exact(
        text,
        source,
        _render_python_constant(name, new),
        source=f"preflight {name}",
    )


def assess_automatic_chain(
    manifest: dict[str, Any], evidences: list[dict[str, Any]]
) -> dict[str, Any]:
    """Validate one observed chain and report whether cumulative automation is safe."""

    if not evidences or len(evidences) > settings.MAX_QUALIFICATION_CHAIN:
        core._fail("candidate evidence chain must be a non-empty bounded list")
    ordered = sorted(evidences, key=lambda item: core._version(str(item.get("version", ""))))
    tested_baseline = str(manifest["recommended_version"])
    comparison = tested_baseline
    versions: list[str] = []
    classifications: list[str] = []
    contiguous = True
    for item in ordered:
        version = item.get("version")
        if not isinstance(version, str) or version in versions:
            core._fail("candidate evidence chain contains an invalid or duplicate version")
        candidate = core._version(version)
        previous = core._version(comparison)
        if candidate[:2] != previous[:2] or candidate[2] != previous[2] + 1:
            contiguous = False
        if (
            item.get("schema_version") not in {2, 3}
            or item.get("tested_baseline_version") != tested_baseline
            or item.get("comparison_version") != comparison
            or item.get("result") != "compatible"
        ):
            core._fail(f"candidate evidence {version} does not match the observed chain contract")
        classification = item.get("classification")
        if classification not in {"automatic-safe", "human-review-required"}:
            core._fail(f"candidate evidence {version} has an invalid classification")
        versions.append(version)
        classifications.append(classification)
        comparison = version
    automatic = contiguous and all(value == "automatic-safe" for value in classifications)
    return {
        "automatic_blockers": ([] if contiguous else ["non-contiguous release sequence"]),
        "classification": "automatic-safe" if automatic else "human-review-required",
        "target_version": versions[-1],
        "tested_baseline_version": tested_baseline,
        "versions": versions,
    }


def prepare_update(
    *,
    manifest_path: Path,
    evidence: dict[str, Any] | list[dict[str, Any]],
    fragment_number: int,
    human_conclusions: dict[str, str] | None = None,
    root: Path = settings.ROOT,
) -> list[Path]:
    """Prepare one cumulative promotion from a validated adjacent evidence chain."""

    if fragment_number <= 0:
        core._fail("fragment_number must be a positive issue number")
    manifest = core.load_json(manifest_path)
    contract_rules.validate_manifest(manifest, root)
    old_version = str(manifest["recommended_version"])
    old_supported, old_deprecated = contract_rules.qualified_runtime_versions(manifest)
    evidences = [evidence] if isinstance(evidence, dict) else list(evidence)
    if not evidences or len(evidences) > settings.MAX_QUALIFICATION_CHAIN:
        core._fail("candidate evidence chain must be a non-empty bounded list")
    evidences.sort(key=lambda item: core._version(str(item.get("version", ""))))
    conclusions = human_conclusions or {}
    expected_comparison = old_version
    versions: list[str] = []
    for item in evidences:
        version = item.get("version")
        if not isinstance(version, str):
            core._fail("candidate evidence version must be a string")
        if version in versions:
            core._fail(f"candidate evidence chain contains duplicate version {version}")
        candidate = core._version(version)
        comparison = core._version(expected_comparison)
        transition = core._release_transition(comparison, candidate)
        if transition is None:
            core._fail("candidate evidence chain is not a contiguous release sequence")
        if transition != "patch" and item.get("schema_version") not in {2, 3}:
            core._fail("minor and major promotions require chain-aware evidence schema 2 or 3")
        if item.get("result") != "compatible":
            core._fail(f"candidate evidence does not qualify {version} as compatible")
        schema_version = item.get("schema_version")
        if schema_version in {2, 3}:
            if item.get("tested_baseline_version") != old_version:
                core._fail(f"candidate evidence {version} has a stale tested baseline")
            if item.get("comparison_version") != expected_comparison:
                core._fail(f"candidate evidence {version} has a non-adjacent comparison version")
        elif schema_version != 1 or len(evidences) != 1:
            core._fail("multi-release promotion requires chain-aware evidence schema 2 or 3")
        classification = item.get("classification")
        conclusion = conclusions.get(version)
        if conclusion is not None and (
            not isinstance(conclusion, str)
            or not conclusion.strip()
            or len(conclusion) > 2_000
            or any(ord(character) < 32 and character not in "\n\t" for character in conclusion)
        ):
            core._fail(f"candidate {version} conclusion must be bounded plain text")
        if classification == "human-review-required":
            if conclusion is None:
                core._fail(f"human-reviewed candidate {version} requires a bounded conclusion")
        elif classification != "automatic-safe":
            core._fail(f"candidate evidence {version} has an invalid classification")
        if transition != "patch" and classification != "human-review-required":
            core._fail("minor and major promotions require explicit human review")
        versions.append(version)
        expected_comparison = version
    unknown_conclusions = set(conclusions).difference(versions)
    if unknown_conclusions:
        core._fail("human conclusions may reference only evidence versions in this promotion")

    for item in evidences:
        if item.get("schema_version") != 3:
            core._fail("current candidate requires evidence schema 3")
        candidate_version = item.get("version")
        if not isinstance(candidate_version, str):
            core._fail("candidate evidence version must be a string")
        contract_rules._validate_evidence_contracts(candidate_version, item)

    version = versions[-1]
    releases = manifest.get("releases")
    assert isinstance(releases, list)
    existing_versions = {str(item.get("version")) for item in releases if isinstance(item, dict)}
    if any(candidate in existing_versions for candidate in versions):
        core._fail("candidate evidence chain overlaps an existing manifest release")
    old_entry = next(
        (
            item
            for item in releases
            if isinstance(item, dict) and item.get("version") == old_version
        ),
        None,
    )
    if old_entry is None:
        core._fail("manifest lost its previous recommended release")
    old_assets = old_entry.get("assets")
    if not isinstance(old_assets, list):
        core._fail("previous recommended release assets are invalid")
    old_linux_asset = next(
        (
            asset
            for asset in old_assets
            if isinstance(asset, dict) and asset.get("name") == "opencodereview-linux-amd64"
        ),
        None,
    )
    if old_linux_asset is None or not isinstance(old_linux_asset.get("sha256"), str):
        core._fail("previous recommended release lacks the Linux amd64 checksum")
    old_linux = old_linux_asset["sha256"]
    destinations: list[Path] = []
    evidence_payloads: list[bytes] = []
    for item in evidences:
        candidate_version = str(item["version"])
        evidence_name = f"ocr-{candidate_version}.json"
        destination = root / "compatibility" / "evidence" / evidence_name
        payload = core.canonical_json(item)
        destinations.append(destination)
        evidence_payloads.append(payload)
        assets = item.get("assets")
        if not isinstance(assets, list) or len(assets) != len(settings.REQUIRED_ASSETS):
            core._fail(
                f"candidate evidence {candidate_version} assets must be the supported matrix"
            )
        asset_names: set[str] = set()
        for asset in assets:
            if not isinstance(asset, dict):
                core._fail(f"candidate evidence {candidate_version} asset must be an object")
            name, size, sha256 = asset.get("name"), asset.get("size"), asset.get("sha256")
            if not isinstance(name, str) or name in asset_names or Path(name).name != name:
                core._fail(f"candidate evidence {candidate_version} asset name is invalid")
            asset_names.add(name)
            if not isinstance(size, int) or size <= 0 or size > settings.MAX_ASSET_BYTES:
                core._fail(f"candidate evidence {candidate_version}/{name} size is invalid")
            if not isinstance(sha256, str) or settings.SHA256_RE.fullmatch(sha256) is None:
                core._fail(f"candidate evidence {candidate_version}/{name} digest is invalid")
        if asset_names != settings.REQUIRED_ASSETS:
            core._fail(f"candidate evidence {candidate_version} asset set is invalid")
        contracts = item.get("contracts")
        capabilities = (
            contracts.get("optional_capabilities", []) if isinstance(contracts, dict) else []
        )
        if (
            not isinstance(capabilities, list)
            or capabilities != sorted(set(capabilities))
            or any(value not in settings.KNOWN_OPTIONAL_CAPABILITIES for value in capabilities)
        ):
            core._fail(f"candidate evidence {candidate_version} capabilities are invalid")
        conclusion = conclusions.get(candidate_version)
        if conclusion is None:
            conclusion = (
                "Machine-qualified same-minor maintenance patch; promotion still requires "
                "protected PR review and release gates."
            )
        releases.append(
            {
                "assets": assets,
                "capabilities": capabilities,
                "evidence": f"compatibility/evidence/{evidence_name}",
                "evidence_sha256": hashlib.sha256(payload).hexdigest(),
                "human_conclusion": conclusion.strip(),
                "published_at": item.get("published_at"),
                "release_url": (
                    f"https://github.com/{settings.UPSTREAM_REPOSITORY}/releases/tag/v{candidate_version}"
                ),
                "status": "tested",
                "version": candidate_version,
            }
        )
    releases.sort(
        key=lambda item: (
            core._version(str(item["version"])) if isinstance(item, dict) else (0, 0, 0)
        )
    )
    manifest["recommended_version"] = version
    manifest["monitoring_floor"] = version
    manifest["runtime_support"] = contract_rules._rolling_runtime_support(version)
    new_supported, new_deprecated = contract_rules.qualified_runtime_versions(manifest)
    manifest_payload = core.canonical_json(manifest)

    preflight_path = root / settings.PREFLIGHT.relative_to(settings.ROOT)
    preflight = preflight_path.read_text(encoding="utf-8")
    preflight = _replace_python_constant(
        preflight,
        "RECOMMENDED_OCR_VERSION",
        old_version,
        version,
    )
    preflight = _replace_python_constant(
        preflight,
        "SUPPORTED_OCR_VERSIONS",
        tuple(old_supported),
        tuple(new_supported),
    )
    preflight = _replace_python_constant(
        preflight,
        "DEPRECATED_OCR_VERSIONS",
        tuple(old_deprecated),
        tuple(new_deprecated),
    )
    final_assets = evidences[-1].get("assets")
    assert isinstance(final_assets, list)
    linux_asset = next(
        (
            asset
            for asset in final_assets
            if isinstance(asset, dict) and asset.get("name") == "opencodereview-linux-amd64"
        ),
        None,
    )
    if linux_asset is None or not isinstance(linux_asset.get("sha256"), str):
        core._fail("candidate evidence lacks the Linux amd64 checksum")
    example_path = root / settings.GITLAB_EXAMPLE.relative_to(settings.ROOT)
    example = example_path.read_text(encoding="utf-8")
    example = _replace_exact(
        example,
        f'OCR_VERSION: "v{old_version}"',
        f'OCR_VERSION: "v{version}"',
        source="example version",
    )
    example = _replace_exact(
        example,
        f'OCR_SHA256: "{old_linux}"',
        f'OCR_SHA256: "{linux_asset["sha256"]}"',
        source="example checksum",
    )
    changelog_dir = root / "changelog.d"
    fragment = changelog_dir / f"{fragment_number}.maintenance.md"
    qualified = version if len(versions) == 1 else f"{versions[0]} through {version}"
    fragment_text = (
        f"Target checksum-verified Open Code Review {version} after qualifying {qualified}.\n"
    )

    # Validate every input and transformation before changing the checkout, then
    # write each accepted evidence snapshot together with its linked manifest.
    destinations[0].parent.mkdir(parents=True, exist_ok=True)
    changelog_dir.mkdir(exist_ok=True)
    for destination, payload in zip(destinations, evidence_payloads, strict=True):
        destination.write_bytes(payload)
    manifest_path.write_bytes(manifest_payload)
    preflight_path.write_text(preflight, encoding="utf-8")
    example_path.write_text(example, encoding="utf-8")
    fragment.write_text(fragment_text, encoding="utf-8")
    return [manifest_path, *destinations, preflight_path, example_path, fragment]


def parse_human_conclusions(values: list[str]) -> dict[str, str]:
    """Parse repeatable VERSION=CONCLUSION CLI values without losing whitespace."""

    conclusions: dict[str, str] = {}
    for value in values:
        version, separator, conclusion = value.partition("=")
        if (
            not separator
            or settings.VERSION_RE.fullmatch(version) is None
            or version in conclusions
        ):
            core._fail("human conclusions must be unique VERSION=CONCLUSION values")
        conclusions[version] = conclusion
    return conclusions
