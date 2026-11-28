"""Classify adjacent candidates and prepare reviewed support updates."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import shutil
import tempfile
from contextlib import ExitStack
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
    if not value:
        return f"{name} = ()"
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
            item.get("schema_version") not in {2, 3, 4, 5}
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


def _generated_destination(path: Path, payload: bytes) -> bool:
    """Preflight every generated output; preserve identical already-placed bytes."""

    if path.is_symlink():
        core._fail(f"generated destination must not be a symlink: {path}")
    if not path.exists():
        return True
    if not path.is_file():
        core._fail(f"generated destination is not a regular file: {path}")
    with path.open("rb") as existing:
        if existing.read(len(payload) + 1) != payload:
            core._fail(f"generated destination already has different content: {path}")
    return False


def _commit_outputs(outputs: list[tuple[Path, bytes]], new: set[Path]) -> None:
    """Stage every write before replacing files, restoring originals on an I/O failure."""

    retained: set[Path] = set()

    def cleanup(directory: Path) -> None:
        if directory not in retained:
            shutil.rmtree(directory, ignore_errors=True)

    with ExitStack() as staging:
        staged: list[tuple[Path, Path, Path | None]] = []
        for path, content in outputs:
            directory = Path(tempfile.mkdtemp(dir=path.parent, prefix=".ocr-promotion-"))
            staging.callback(cleanup, directory)
            replacement = directory / "new"
            replacement.write_bytes(content)
            original = None
            if path not in new and path.exists():
                if path.is_symlink() or not path.is_file():
                    core._fail(f"promotion destination must be a regular file: {path}")
                original = directory / "old"
                os.link(path, original)
                shutil.copymode(path, replacement)
            staged.append((path, replacement, original))

        attempted: list[tuple[Path, Path, Path | None]] = []
        try:
            for path, replacement, original in staged:
                # Journal before the syscall: interruption may follow a successful
                # link/rename before Python executes the next statement.
                attempted.append((path, replacement, original))
                if original is None:
                    os.link(replacement, path)
                else:
                    os.replace(replacement, path)
        except (OSError, KeyboardInterrupt) as exc:
            recovery = []
            for path, replacement, original in reversed(attempted):
                try:
                    if original is None:
                        if path.exists() and path.samefile(replacement):
                            path.unlink()
                    elif not path.exists() or not path.samefile(original):
                        os.replace(original, path)
                except OSError:
                    retained.add(replacement.parent)
                    action = (
                        f"restore {original} to {path}"
                        if original
                        else f"remove {path} after comparing to {replacement}"
                    )
                    recovery.append(action)
            if recovery:
                detail = "promotion rollback incomplete: " + ", ".join(recovery)
                raise core.CompatibilityError(detail) from exc
            if isinstance(exc, KeyboardInterrupt):
                raise
            raise core.CompatibilityError("failed to commit promotion outputs") from exc


def prepare_update(
    *,
    manifest_path: Path,
    evidence: dict[str, Any] | list[dict[str, Any]],
    fragment_number: int,
    human_conclusions: dict[str, str] | None = None,
    incompatible_statuses: list[dict[str, Any]] | None = None,
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
    statuses = [
        contract_rules.validate_incompatible_receipt(status)
        for status in incompatible_statuses or []
    ]
    chain_limit = (
        settings.MAX_RELEASE_PAGES * settings.MAX_RELEASES_PER_PAGE
        if statuses or human_conclusions
        else settings.MAX_QUALIFICATION_CHAIN
    )
    if not evidences or len(evidences) + len(statuses) > chain_limit:
        core._fail("candidate evidence chain must be a non-empty bounded list")
    evidences.sort(key=lambda item: core._version(str(item.get("version", ""))))
    chain = sorted(
        [(item, False) for item in evidences] + [(status, True) for status in statuses],
        key=lambda attempt: core._version(str(attempt[0].get("version", ""))),
    )
    if chain[-1][1]:
        core._fail("candidate chain must end in a compatible release")
    conclusions = human_conclusions or {}
    expected_comparison = old_version
    versions: list[str] = []
    for item, incompatible in chain:
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
        schema_version = item.get("schema_version")
        if not incompatible and transition != "patch" and schema_version not in {2, 3, 4, 5}:
            core._fail("minor and major promotions require chain-aware evidence schema 2 or later")
        expected_result = "incompatible" if incompatible else "compatible"
        if item.get("result") != expected_result:
            core._fail(f"candidate evidence does not qualify {version} as {expected_result}")
        if incompatible or schema_version in {2, 3, 4, 5}:
            if item.get("tested_baseline_version") != old_version:
                core._fail(f"candidate evidence {version} has a stale tested baseline")
            if item.get("comparison_version") != expected_comparison:
                core._fail(f"candidate evidence {version} has a non-adjacent comparison version")
        elif schema_version != 1 or len(chain) != 1:
            core._fail("multi-release promotion requires chain-aware evidence schema 2 or later")
        classification = "human-review-required" if incompatible else item.get("classification")
        conclusion = conclusions.get(version)
        if conclusion is not None and not contract_rules._valid_human_conclusion(conclusion):
            core._fail(f"candidate {version} conclusion must be bounded plain text")
        if classification not in ("human-review-required", "automatic-safe"):
            core._fail(f"candidate evidence {version} has an invalid classification")
        if conclusion is None and (
            classification == "human-review-required" or (statuses and item is chain[-1][0])
        ):
            core._fail(f"human-reviewed candidate {version} requires a bounded conclusion")
        if transition != "patch" and classification != "human-review-required":
            core._fail("minor and major promotions require explicit human review")
        versions.append(version)
        expected_comparison = version
    unknown_conclusions = set(conclusions).difference(versions)
    if unknown_conclusions:
        core._fail("human conclusions may reference only evidence versions in this promotion")

    for item in evidences:
        if item.get("schema_version") not in {3, 4, 5}:
            core._fail("current candidate requires supported evidence schema")
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
    destinations: list[Path] = []
    evidence_payloads: list[bytes] = []
    for item in evidences:
        candidate_version = str(item["version"])
        evidence_name = f"ocr-{candidate_version}.json"
        destination = root / "compatibility" / "evidence" / evidence_name
        payload = core.canonical_json(item)
        destinations.append(destination)
        evidence_payloads.append(payload)
        assets = contract_rules.validate_candidate_assets(item, candidate_version)
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
    for receipt, status in zip(incompatible_statuses or [], statuses, strict=True):
        candidate_version = status["version"]
        evidence_name = f"ocr-{candidate_version}-incompatible.json"
        payload = core.canonical_json(receipt)
        destinations.append(root / "compatibility" / "evidence" / evidence_name)
        evidence_payloads.append(payload)
        releases.append(
            {
                "evidence": f"compatibility/evidence/{evidence_name}",
                "evidence_sha256": hashlib.sha256(payload).hexdigest(),
                "human_conclusion": conclusions[candidate_version].strip(),
                "status": "incompatible",
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
    # The example installs a published toolkit wheel. Its OCR version/checksum
    # must advance with that toolkit pin in the release PR, not before the new
    # runtime support has actually been delivered.
    changelog_dir = root / "changelog.d"
    fragment = changelog_dir / f"{fragment_number}.maintenance.md"
    if statuses:
        excluded = ", ".join(status["version"] for status in statuses)
        fragment_text = (
            f"Target checksum-verified Open Code Review {version}; "
            f"record incompatible releases {excluded}.\n"
        )
    else:
        qualified = version if len(versions) == 1 else f"{versions[0]} through {version}"
        fragment_text = (
            f"Target checksum-verified Open Code Review {version} after qualifying {qualified}.\n"
        )
    outputs = [
        *zip(destinations, evidence_payloads, strict=True),
        (fragment, fragment_text.encode()),
    ]
    pending = [
        (path, payload) for path, payload in outputs if _generated_destination(path, payload)
    ]
    handoff_path = preflight_path.with_name("_qualified_handoffs.json")
    handoff_payload = None
    if core._version(version) >= settings.BEHAVIORAL_EPOCH:
        candidates = {item["version"]: item for item in evidences}
        inventory = {}
        for release in releases:
            release_version = release["version"]
            if release_version in new_supported:
                observed = candidates.get(release_version)
                if observed is None:
                    observed = core.load_json(root / release["evidence"])
                inventory[release_version] = observed["contracts"]["native_handoffs"]
        if handoff_path.is_symlink() or (handoff_path.exists() and not handoff_path.is_file()):
            core._fail("native handoffs destination must be a regular file")
        handoff_payload = core.canonical_json(inventory)

    # Validate every input and transformation before changing the checkout, then
    # write each accepted evidence snapshot together with its linked manifest.
    destinations[0].parent.mkdir(parents=True, exist_ok=True)
    changelog_dir.mkdir(exist_ok=True)
    writes = [
        *pending,
        (preflight_path, preflight.encode("utf-8")),
    ]
    outputs_written = [manifest_path, *destinations, preflight_path, fragment]
    if handoff_payload is not None:
        writes.append((handoff_path, handoff_payload))
        outputs_written.append(handoff_path)
    writes.append((manifest_path, manifest_payload))
    _commit_outputs(writes, {path for path, _ in pending})
    return outputs_written


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
