"""Build and summarize the OCR review background Markdown."""

from __future__ import annotations

import argparse
import os
import re
import sys
from collections.abc import Sequence
from typing import Any

from ocr_toolkit.common.language import resolve_review_language
from ocr_toolkit.common.markdown import (
    markdown_code_block,
    markdown_fence_transition,
    open_markdown_fence,
)
from ocr_toolkit.common.redaction import (
    SENSITIVE_NAMED_KEY_PATTERN,
    redact_env_secret_values,
    redact_sensitive,
    redact_url_userinfo,
    redact_url_userinfo_only,
    strip_path_controls,
)
from ocr_toolkit.context import repo as context_repo
from ocr_toolkit.context.ansible import (
    detect_root_ansible_playbooks,
    extract_application_versions,
    extract_inventory_topology,
    is_inventory_topology_file,
    parse_ansible_requirement_version_pins,
    parse_ansible_requirements,
)
from ocr_toolkit.context.categorize import (
    PYTHON_MANIFEST_PATTERN,
    active_context_providers,
    categorize_files,
)
from ocr_toolkit.context.instructions import (
    read_accepted_decisions,
    read_project_instructions,
)
from ocr_toolkit.context.manifests import (
    discover_package_json_paths,
    discover_pyproject_paths,
    parse_composer_json,
    parse_composer_lock,
    parse_go_mod,
    parse_package_json,
    parse_pyproject,
    parse_requirements_txt,
)
from ocr_toolkit.context.planner import ContextSection, render_context, split_markdown_sections
from ocr_toolkit.context.settings import (
    DEFAULT_BACKGROUND_MAX_BYTES,
    DEFAULT_BACKGROUND_MAX_CHARS,
    MAX_BACKGROUND_MAX_BYTES,
    MAX_BACKGROUND_MAX_CHARS,
    getenv_int,
    inline_code,
    string_list_value,
    string_value,
)


def safe_text(value: str) -> str:
    """Redact repository-controlled text before rendering it to context."""

    return redact_sensitive(redact_url_userinfo(value))


def safe_inline_value(value: str) -> str:
    """Return a redacted inline-code value for context output."""

    return inline_code(safe_text(value))


def safe_inline_path(value: str) -> str:
    """Return a Markdown-safe repository path without generic key rewrites."""

    cleaned = redact_env_secret_values(redact_url_userinfo_only(strip_path_controls(value)))
    cleaned = re.sub(
        rf"(?i)(^|[/?&;]|\b)((?:{SENSITIVE_NAMED_KEY_PATTERN})(?:=|[-_:]))"
        r"[^/?&;`\s]+",
        r"\1\2***",
        cleaned,
    )
    cleaned = re.sub(
        r"(?i)(^|/)(?:password|passwd|secret|secrets|token|api[_-]?key|x-api-key|"
        r"auth[_-]?token|access[_-]?token|refresh[_-]?token|private[_-]?token|"
        r"client[_-]?secret|secret[_-]?key|aws[_-]?secret[_-]?access[_-]?key)(?=\.|/|$)",
        r"\1***",
        cleaned,
    )
    cleaned = re.sub(
        r"(?i)(^|/)(?:id_)?(?:rsa|dsa|ecdsa|ed25519)(?=\.|/|$)",
        r"\1***",
        cleaned,
    )
    cleaned = re.sub(
        r"(?i)(^|/)(?:private[_-]?key)(?=\.|/|$)",
        r"\1***",
        cleaned,
    )
    return inline_code(cleaned)


def format_items(items: Sequence[str], limit: int = 80) -> str:
    """Format a bounded markdown bullet list.

    Most dependency/runtime metadata reaches the review background through
    this boundary. Redact URL userinfo here so future manifest parsers do not
    need to remember the same credential-safety rule individually.
    """

    if not items:
        return "- none detected"

    clipped = list(items[:limit])
    lines = [f"- {safe_inline_value(item)}" for item in clipped]
    if len(items) > limit:
        lines.append(f"- ... and {len(items) - limit} more")
    return "\n".join(lines)


def format_paths(items: Sequence[str], limit: int = 80) -> str:
    """Format repository paths without generic secret-key rewrites."""

    if not items:
        return "- none detected"

    clipped = list(items[:limit])
    lines = [f"- {safe_inline_path(item)}" for item in clipped]
    if len(items) > limit:
        lines.append(f"- ... and {len(items) - limit} more")
    return "\n".join(lines)


def format_manifest_items(items: Sequence[str], omitted: int = 0, limit: int = 80) -> str:
    """Format manifest items while preserving parser-level omitted counts."""

    if not items:
        if omitted > 0:
            return f"- ... and {omitted} more"
        return "- none detected"

    clipped = list(items[:limit])
    lines = [f"- {safe_inline_value(item)}" for item in clipped]
    total_omitted = max(0, len(items) - len(clipped)) + max(0, omitted)
    if total_omitted:
        lines.append(f"- ... and {total_omitted} more")
    return "\n".join(lines)


def add_section(
    lines: list[str],
    title: str,
    items: Sequence[str],
    limit: int = 80,
    *,
    paths: bool = True,
) -> None:
    """Append a markdown section containing a bounded list."""

    lines.append(f"## {title}")
    formatter = format_paths if paths else format_items
    lines.append(formatter(items, limit=limit))
    lines.append("")


def format_category_summary(categories: dict[str, list[str]], limit: int = 12) -> str:
    """Render changed-file categories as dense, bounded path samples."""

    if not categories:
        return "- none detected"

    lines: list[str] = []
    shown: set[str] = set()
    for category, files in categories.items():
        unique_files = [path for path in files if path not in shown]
        samples = [safe_inline_path(path) for path in unique_files[:limit]]
        omitted = len(unique_files) - len(samples)
        if samples:
            suffix = f"; +{omitted} more" if omitted else ""
            lines.append(f"- {category} ({len(files)}): {', '.join(samples)}{suffix}")
        else:
            lines.append(f"- {category} ({len(files)}): overlaps prior categories")
        shown.update(files)
    return "\n".join(lines)


def limit_text_bytes(text: str, max_bytes: int) -> str:
    """Limit text to a strict UTF-8 byte budget without raising decode errors."""

    if max_bytes <= 0:
        return ""

    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text

    notice = (
        "\n\n## Context truncation notice\n"
        f"- Review background was truncated to {max_bytes} bytes.\n"
    )
    notice_bytes = notice.encode("utf-8")

    if len(notice_bytes) >= max_bytes:
        return notice_bytes[:max_bytes].decode("utf-8", errors="ignore")

    clip_budget = max_bytes - len(notice_bytes)
    clipped = encoded[:clip_budget].decode("utf-8", errors="ignore").rstrip()

    closing_fence = ""
    while True:
        open_fence = open_markdown_fence(clipped)
        next_closing_fence = f"\n{open_fence}" if open_fence is not None else ""
        closing_fence_bytes = next_closing_fence.encode("utf-8")
        if not next_closing_fence:
            closing_fence = ""
            break
        if len(clipped.encode("utf-8")) + len(closing_fence_bytes) + len(notice_bytes) <= max_bytes:
            closing_fence = next_closing_fence
            break

        clip_budget = max(
            0,
            max_bytes - len(notice_bytes) - len(closing_fence_bytes),
        )
        shortened = encoded[:clip_budget].decode("utf-8", errors="ignore").rstrip()
        if shortened == clipped:
            closing_fence = next_closing_fence
            break
        clipped = shortened

    result = clipped + closing_fence + notice

    # Final guard: never exceed the declared byte budget.
    result_bytes = result.encode("utf-8")
    if len(result_bytes) <= max_bytes:
        return result

    return result_bytes[:max_bytes].decode("utf-8", errors="ignore")


def build_context() -> str:
    """Build the complete Markdown review background."""

    response_language = resolve_review_language()
    raw_changed = context_repo.changed_files()
    changed_unavailable = raw_changed is None
    changed: list[str] = list(raw_changed) if raw_changed is not None else []
    categories = categorize_files(changed)
    active_categories = set(categories)
    active_providers = active_context_providers(changed, categories)
    ansible_active = "ansible" in active_providers
    python_active = "python" in active_providers
    go_active = "go" in active_providers
    php_active = "php" in active_providers
    javascript_active = "javascript" in active_providers
    versions_active = bool(
        active_categories
        & {
            "ansible_playbooks",
            "ansible_roles",
            "ci",
            "containers",
            "dependency_manifests",
            "go",
            "javascript_typescript",
            "php",
            "python",
            "terraform_hcl",
            "templates",
        }
    )

    ansible_core_paths = (
        context_repo.rel_glob(
            [
                "ansible.cfg",
                "requirements.yml",
                "requirements.yaml",
                "collections/requirements.yml",
                "collections/requirements.yaml",
            ],
            limit=20,
        )
        if ansible_active
        else []
    )
    role_metadata_paths = (
        context_repo.rel_glob(
            [
                "roles/**/meta/main.yml",
                "roles/**/defaults/main.yml",
                "roles/**/vars/main.yml",
            ],
            limit=120,
        )
        if ansible_active
        else []
    )

    ansible_requirements: list[str] = []
    ansible_requirement_versions: list[str] = []
    for req_path in (
        context_repo.rel_glob(
            [
                "requirements.yml",
                "requirements.yaml",
                "collections/requirements.yml",
                "collections/requirements.yaml",
            ],
            limit=20,
        )
        if ansible_active
        else []
    ):
        ansible_requirements.extend(parse_ansible_requirements(context_repo.ROOT / req_path))
        ansible_requirement_versions.extend(
            parse_ansible_requirement_version_pins(context_repo.ROOT / req_path)
        )

    root_playbooks = detect_root_ansible_playbooks() if ansible_active else []
    pyproject_discovery = discover_pyproject_paths(changed) if python_active else None
    pyproject_paths = pyproject_discovery.paths if pyproject_discovery else []
    pyprojects: list[tuple[str, dict[str, Any]]] = [
        (rel, parse_pyproject(context_repo.ROOT / rel)) for rel in pyproject_paths
    ]
    requirements: list[tuple[str, dict[str, Any]]] = []
    root_requirement_paths = [
        path
        for path in (
            "requirements.txt",
            "requirements.in",
            "constraints.txt",
            "constraints.in",
        )
        if python_active and context_repo.path_exists(path)
    ]
    changed_requirements = [
        path
        for path in categories.get("dependency_manifests", [])
        if PYTHON_MANIFEST_PATTERN.search(path) and path.lower().endswith((".in", ".txt"))
    ]
    all_requirement_paths = list(dict.fromkeys([*root_requirement_paths, *changed_requirements]))
    requirement_paths = all_requirement_paths[:30]
    omitted_requirement_paths = max(0, len(all_requirement_paths) - len(requirement_paths))
    for req_path in requirement_paths if python_active else []:
        requirements.append((req_path, parse_requirements_txt(context_repo.ROOT / req_path)))

    go_mod = (
        parse_go_mod(context_repo.ROOT / "go.mod")
        if go_active and context_repo.path_exists("go.mod")
        else {}
    )
    composer_json = (
        parse_composer_json(context_repo.ROOT / "composer.json")
        if php_active and context_repo.path_exists("composer.json")
        else {}
    )
    composer_lock = (
        parse_composer_lock(context_repo.ROOT / "composer.lock")
        if php_active and context_repo.path_exists("composer.lock")
        else {}
    )
    package_json_discovery = discover_package_json_paths(changed) if javascript_active else None
    package_json_paths = package_json_discovery.paths if package_json_discovery else []

    app_versions = (
        extract_application_versions(changed, include_discovered=True)
        + ansible_requirement_versions
        if versions_active
        else []
    )
    manifest_paths = sorted(categories.get("dependency_manifests", []))
    inventory_topology_paths = (
        [
            rel_path
            for rel_path in context_repo.rel_glob_files(
                [
                    "inventory",
                    "inventory.*",
                    "inventory/**/*",
                    "inventories",
                    "inventories/**/*",
                    "**/hosts",
                    "**/hosts.*",
                    "**/inventory",
                    "**/inventory.*",
                ],
                limit=240,
                exclude_dirs=context_repo.DEFAULT_EXCLUDE_DIRS | {".review-context"},
            )
            if is_inventory_topology_file(rel_path)
        ]
        if ansible_active
        else []
    )
    inventory_groups = extract_inventory_topology(inventory_topology_paths)
    # When context_repo.changed_files() failed, do NOT include reviewer guidance or
    # accepted-decisions: we cannot tell whether the current MR is
    # editing them, which would let an MR self-whitelist its own
    # findings. The MR will simply review without those constraints.
    instructions = [] if changed_unavailable else read_project_instructions(changed_paths=changed)

    lines: list[str] = []
    lines.append("# Review Background")
    lines.append("")
    lines.append(f"Response language: {response_language}.")
    lines.append(
        "All user-visible review comments, summaries, warnings and recommendations MUST be written in this response "
        "language. Keep code identifiers, file paths, function names, package names and error names unchanged."
    )
    lines.append("")
    lines.append("Use this context as hard constraints for the review.")
    lines.append(
        "If a suggested API or behavior conflicts with detected runtime, dependency, provider or application versions, "
        "do not suggest it."
    )
    lines.append(
        "If version-specific knowledge is unavailable, state the uncertainty explicitly instead of recommending an "
        "obsolete API."
    )
    lines.append("Review only changed code and directly related context.")
    lines.append("Post only high-confidence findings.")
    lines.append("Do not block the merge request.")
    lines.append("")

    lines.append("## Merge Request")
    lines.append(
        "- Target branch: "
        f"{context_repo.inline_ci_value('CI_MERGE_REQUEST_TARGET_BRANCH_NAME', use_default_branch=True)}"
    )
    lines.append(
        "- Source branch: "
        f"{context_repo.inline_ci_value('CI_MERGE_REQUEST_SOURCE_BRANCH_NAME', fallback_git_args=['branch', '--show-current'])}"
    )
    pipeline_sha = os.environ.get("CI_COMMIT_SHA", "").strip()
    source_sha = os.environ.get("CI_MERGE_REQUEST_SOURCE_BRANCH_SHA", "").strip()
    source_sha_available = bool(source_sha) and set(source_sha) != {"0"}
    if source_sha_available:
        lines.append(f"- Source commit SHA: {inline_code(source_sha)}")
    else:
        lines.append(
            "- Commit SHA: "
            f"{context_repo.inline_ci_value('CI_COMMIT_SHA', fallback_git_args=['rev-parse', 'HEAD'])}"
        )
    if source_sha_available and pipeline_sha and pipeline_sha != source_sha:
        lines.append(
            "- Pipeline commit SHA: "
            f"{inline_code(pipeline_sha)} _(pipeline ref; may be synthetic in merged-result pipelines)_"
        )
    if changed_unavailable:
        lines.append(
            "- Changed files: unavailable; git diff failed, so project instruction files and accepted decisions are "
            "intentionally omitted to avoid MR self-whitelisting."
        )
    else:
        lines.append(f"- Changed files: {len(changed)} detected")
    lines.append("")

    accepted_decisions = (
        "" if changed_unavailable else read_accepted_decisions(changed_paths=changed)
    )
    if accepted_decisions:
        lines.append("## Accepted project decisions")
        lines.append(
            "The following items are intentionally accepted by the project. "
            "Do not raise them as new review findings. If you would normally "
            "comment on one, skip it; if you must acknowledge it, mark it as "
            "an accepted decision and move on."
        )
        lines.append("")
        # Demote the embedded document below `##` so its own headings do not
        # pollute the top-level section count in the stdout summary.
        safe_accepted_decisions = redact_sensitive(redact_url_userinfo(accepted_decisions))
        demoted = re.sub(
            r"(?m)^(#{1,5}) ",
            lambda match: "#" * min(6, len(match.group(1)) + 2) + " ",
            safe_accepted_decisions,
        )
        lines.append(demoted)
        lines.append("")

    lines.append("## Changed files by category")
    if changed_unavailable:
        lines.append(
            "- unavailable: changed-file discovery failed; review should rely on OCR diff input and directly related "
            "repository context instead of treating this as an empty MR."
        )
        lines.append("")
    elif categories:
        lines.append(format_category_summary(categories))
        lines.append("")
    else:
        lines.append("- none detected")
        lines.append("")

    if instructions:
        lines.append("## Project instruction files")
        lines.append(
            "The following bounded excerpts were found in repository instruction files. "
            "Treat them as project guidance, but prefer concrete diff evidence over generic style preferences."
        )
        lines.append("")
        for rel_path, excerpt in instructions:
            lines.append(f"### {safe_inline_path(rel_path)}")
            safe_excerpt = redact_sensitive(redact_url_userinfo(excerpt[:8_000]))
            lines.append(markdown_code_block("markdown", safe_excerpt))
            lines.append("")

    add_section(lines, "Ansible core manifests", ansible_core_paths, limit=20)
    add_section(lines, "Role defaults and metadata files", role_metadata_paths, limit=60)
    add_section(lines, "Detected root Ansible playbook entrypoints", root_playbooks, limit=120)
    add_section(lines, "Ansible inventory topology files", inventory_topology_paths, limit=120)
    add_section(lines, "Ansible inventory groups", inventory_groups, limit=120, paths=False)
    add_section(lines, "Ansible Galaxy requirements", ansible_requirements, limit=100, paths=False)

    ansible_version = context_repo.tool_version("ansible", ["--version"]) if ansible_active else []
    ansible_lint_version = (
        context_repo.tool_version("ansible-lint", ["--version"]) if ansible_active else []
    )
    add_section(lines, "Detected ansible --version", ansible_version, limit=8, paths=False)
    add_section(
        lines,
        "Detected ansible-lint --version",
        ansible_lint_version,
        limit=8,
        paths=False,
    )

    lines.append("## Python context")
    emitted_python_context = False
    for rel_path, pyproject in pyprojects:
        if not pyproject:
            continue
        header_suffix = "" if rel_path == "pyproject.toml" else f" ({safe_inline_path(rel_path)})"
        parse_error = string_value(pyproject.get("parse_error"))
        if parse_error:
            lines.append(
                f"- pyproject.toml parse error{header_suffix}: {safe_inline_value(parse_error)}"
            )
            emitted_python_context = True
            continue

        requires_python = string_value(pyproject.get("requires_python"))
        dependencies = string_list_value(pyproject.get("dependencies"))
        if requires_python:
            lines.append(f"- requires-python{header_suffix}: {safe_inline_value(requires_python)}")
            emitted_python_context = True
        if dependencies:
            lines.append(f"### pyproject dependencies{header_suffix}")
            lines.append(
                format_manifest_items(
                    dependencies,
                    int(pyproject.get("dependencies_omitted") or 0),
                    limit=100,
                )
            )
            emitted_python_context = True
        if not requires_python and not dependencies:
            lines.append(
                f"- pyproject.toml detected{header_suffix}, but no "
                "requires-python/dependencies found"
            )
            emitted_python_context = True
    remaining_requirement_items = 100
    omitted_requirement_groups = omitted_requirement_paths
    for req_path, requirement_data in requirements:
        parse_error = string_value(requirement_data.get("parse_error"))
        if parse_error:
            lines.append(f"### requirements-style dependencies ({safe_inline_path(req_path)})")
            lines.append(f"- parse error: {safe_inline_value(parse_error)}")
        else:
            dependencies = string_list_value(requirement_data.get("dependencies"))
            if remaining_requirement_items <= 0:
                omitted_requirement_groups += 1
                emitted_python_context = True
                continue

            lines.append(f"### requirements-style dependencies ({safe_inline_path(req_path)})")
            visible_dependencies = dependencies[:remaining_requirement_items]
            parser_omitted = int(requirement_data.get("dependencies_omitted") or 0)
            budget_omitted = max(0, len(dependencies) - len(visible_dependencies))
            remaining_requirement_items -= len(visible_dependencies)
            lines.append(
                format_manifest_items(
                    visible_dependencies,
                    parser_omitted + budget_omitted,
                    limit=len(visible_dependencies),
                )
            )
        emitted_python_context = True
    if omitted_requirement_groups:
        lines.append(f"- ... and {omitted_requirement_groups} requirements file(s) omitted")
    if pyproject_discovery and pyproject_discovery.omitted:
        lines.append(f"- ... and {pyproject_discovery.omitted} pyproject manifest(s) omitted")
    if not emitted_python_context:
        lines.append("- none detected")
    lines.append("")

    lines.append("## Go context")
    if go_mod:
        emitted_go_context = False
        parse_error = string_value(go_mod.get("parse_error"))
        go_version = string_value(go_mod.get("go"))
        toolchain = string_value(go_mod.get("toolchain"))
        modules = string_list_value(go_mod.get("modules"))
        if parse_error:
            lines.append(f"- go.mod parse error: {safe_inline_value(parse_error)}")
            emitted_go_context = True
        if go_version:
            lines.append(f"- go version: {safe_inline_value(go_version)}")
            emitted_go_context = True
        if toolchain:
            lines.append(f"- toolchain: {safe_inline_value(toolchain)}")
            emitted_go_context = True
        if modules:
            lines.append("### go.mod modules")
            lines.append(
                format_manifest_items(
                    modules,
                    int(go_mod.get("modules_omitted") or 0),
                    limit=100,
                )
            )
            emitted_go_context = True
        if not emitted_go_context:
            lines.append("- go.mod detected, but no go/toolchain/require entries found")
    else:
        lines.append("- none detected")
    lines.append("")

    lines.append("## PHP context")
    emitted_php_context = False
    if composer_json:
        parse_error = string_value(composer_json.get("parse_error"))
        if parse_error:
            lines.append(f"- composer.json parse error: {safe_inline_value(parse_error)}")
            emitted_php_context = True
        else:
            emitted_composer_json_context = False
            platform = string_list_value(composer_json.get("platform"))
            require = string_list_value(composer_json.get("require"))
            require_dev = string_list_value(composer_json.get("require_dev"))
            if platform:
                lines.append("### composer platform")
                lines.append(
                    format_manifest_items(
                        platform,
                        int(composer_json.get("platform_omitted") or 0),
                        limit=50,
                    )
                )
                emitted_composer_json_context = True
            if require:
                lines.append("### composer require")
                lines.append(
                    format_manifest_items(
                        require,
                        int(composer_json.get("require_omitted") or 0),
                        limit=100,
                    )
                )
                emitted_composer_json_context = True
            if require_dev:
                lines.append("### composer require-dev")
                lines.append(
                    format_manifest_items(
                        require_dev,
                        int(composer_json.get("require_dev_omitted") or 0),
                        limit=100,
                    )
                )
                emitted_composer_json_context = True
            if not emitted_composer_json_context:
                lines.append(
                    "- composer.json detected, but no platform/require/require-dev entries found"
                )
                emitted_composer_json_context = True
            emitted_php_context = emitted_php_context or emitted_composer_json_context
    if composer_lock:
        parse_error = string_value(composer_lock.get("parse_error"))
        packages = string_list_value(composer_lock.get("packages"))
        if parse_error:
            lines.append(f"- composer.lock parse error: {safe_inline_value(parse_error)}")
            emitted_php_context = True
        elif packages:
            lines.append("### composer.lock packages")
            lines.append(
                format_manifest_items(
                    packages,
                    int(composer_lock.get("packages_omitted") or 0),
                    limit=100,
                )
            )
            emitted_php_context = True
        else:
            lines.append("- composer.lock detected, but no package entries found")
            emitted_php_context = True
    if not emitted_php_context:
        lines.append("- none detected")
    lines.append("")

    lines.append("## JavaScript/TypeScript context")
    if package_json_paths:
        for package_json_path in package_json_paths:
            package_json = parse_package_json(context_repo.ROOT / package_json_path)
            lines.append(f"### {safe_inline_path(package_json_path)}")
            parse_error = string_value(package_json.get("parse_error"))
            if parse_error:
                lines.append(f"- parse error: {safe_inline_value(parse_error)}")
                continue

            emitted_package_json_context = False
            engines = string_list_value(package_json.get("engines"))
            dependencies = string_list_value(package_json.get("dependencies"))
            dev_dependencies = string_list_value(package_json.get("dev_dependencies"))
            if engines:
                lines.append("#### engines")
                lines.append(
                    format_manifest_items(
                        engines,
                        int(package_json.get("engines_omitted") or 0),
                        limit=40,
                    )
                )
                emitted_package_json_context = True
            if dependencies:
                lines.append("#### dependencies")
                lines.append(
                    format_manifest_items(
                        dependencies,
                        int(package_json.get("dependencies_omitted") or 0),
                        limit=100,
                    )
                )
                emitted_package_json_context = True
            if dev_dependencies:
                lines.append("#### devDependencies")
                lines.append(
                    format_manifest_items(
                        dev_dependencies,
                        int(package_json.get("dev_dependencies_omitted") or 0),
                        limit=100,
                    )
                )
                emitted_package_json_context = True
            if not emitted_package_json_context:
                lines.append(
                    "- package.json detected, but no engines/dependencies/devDependencies found"
                )
        if package_json_discovery and package_json_discovery.omitted:
            lines.append(
                f"- package.json manifests omitted due to context limit: {package_json_discovery.omitted}"
            )
    else:
        lines.append("- none detected")
    lines.append("")

    if app_versions:
        lines.append("## Application and infrastructure version pins")
        lines.append(
            "Each item identifies its source path and a detected dependency, image, version or ref; URLs are sanitized."
        )
        lines.append(format_items(app_versions, limit=160))
        lines.append("")
    if manifest_paths:
        add_section(
            lines,
            "Detected dependency/runtime manifest files",
            manifest_paths,
            limit=160,
        )

    context = "\n".join(lines).rstrip() + "\n"
    max_bytes = getenv_int(
        "OCR_BACKGROUND_MAX_BYTES",
        DEFAULT_BACKGROUND_MAX_BYTES,
        max_value=MAX_BACKGROUND_MAX_BYTES,
    )
    max_chars = getenv_int(
        "OCR_BACKGROUND_MAX_CHARS",
        DEFAULT_BACKGROUND_MAX_CHARS,
        max_value=MAX_BACKGROUND_MAX_CHARS,
    )
    preamble, sections = split_markdown_sections(context)
    ansible_titles = {
        "Ansible core manifests",
        "Role defaults and metadata files",
        "Detected root Ansible playbook entrypoints",
        "Ansible inventory topology files",
        "Ansible inventory groups",
        "Ansible Galaxy requirements",
        "Detected ansible --version",
        "Detected ansible-lint --version",
    }
    inactive_titles: set[str] = set()
    if not ansible_active:
        inactive_titles.update(ansible_titles)
    if not python_active:
        inactive_titles.add("Python context")
    if not go_active:
        inactive_titles.add("Go context")
    if not php_active:
        inactive_titles.add("PHP context")
    if not javascript_active:
        inactive_titles.add("JavaScript/TypeScript context")
    if not versions_active:
        inactive_titles.update(
            {
                "Application and infrastructure version pins",
                "Detected dependency/runtime manifest files",
            }
        )

    priorities = {
        "Merge Request": 150,
        "Review instructions": 150,
        "Changed files by category": 140,
        "Accepted project decisions": 130,
        "Project instruction files": 120,
        "Python context": 110,
        "Go context": 110,
        "PHP context": 110,
        "JavaScript/TypeScript context": 110,
        "Application and infrastructure version pins": 100,
        "Detected dependency/runtime manifest files": 90,
    }
    selected = [
        ContextSection(
            title=section.title,
            body=section.body,
            priority=priorities.get(section.title, 60),
            minimum_bytes=220 if section.title in priorities else 140,
        )
        for section in sections
        if section.title not in inactive_titles
        and section.body.strip()
        and section.body.strip() != "- none detected"
    ]
    return render_context(preamble, selected, max_bytes, max_chars=max_chars)


def summarize_context(markdown: str, max_bytes: int, max_chars: int | None = None) -> str:
    """Render a one-screen summary of the generated review background.

    The summary is printed to stdout so it shows up in the GitLab job log
    next to `Wrote ...`. It deliberately reports per-section *lines*, not
    contents, so the log stays compact even on large repositories.
    """

    byte_len = len(markdown.encode("utf-8"))
    char_len = len(markdown)
    truncated = (
        "- ... section truncated" in markdown
        or "## Context coverage" in markdown
        or bool(
            re.search(
                r"(?m)\n\n## Context truncation notice\n- Review background was truncated to \d+ bytes\.\n?$",
                markdown,
            )
        )
    )
    byte_pct = (byte_len / max_bytes * 100.0) if max_bytes > 0 else 0.0
    char_pct = (char_len / max_chars * 100.0) if max_chars else None
    est_tokens = char_len // 4

    section_headers: list[tuple[str, int, int]] = []
    open_fence: str | None = None
    offset = 0
    for line in markdown.splitlines(keepends=True):
        open_fence, _ = markdown_fence_transition(line.rstrip("\r\n"), open_fence)

        if open_fence is None:
            header_match = re.match(r"^##\s+([^#].*?)\s*$", line.rstrip("\n"))
            if header_match:
                section_headers.append((header_match.group(1).strip(), offset, offset + len(line)))

        offset += len(line)

    section_lines: list[tuple[str, int]] = []
    for index, (title, header_start, body_start) in enumerate(section_headers):
        # Skip the truncation notice — it is metadata about size, not a
        # content block.
        if title == "Context truncation notice":
            continue
        end = section_headers[index + 1][1] if index + 1 < len(section_headers) else len(markdown)
        body = markdown[body_start:end]
        # Count non-empty lines so a section padded with blanks does not
        # look larger than it is.
        line_count = sum(1 for line in body.splitlines() if line.strip())
        section_lines.append((title, line_count))

    lines = [
        "Review background summary:",
        (
            f"  size: {char_len} chars ({char_pct:.1f} % of {max_chars} limit) / "
            f"{byte_len} bytes ({byte_pct:.1f} % of {max_bytes} limit)"
            if char_pct is not None
            else f"  size: {byte_len} bytes ({byte_pct:.1f} % of {max_bytes} budget) / {char_len} chars"
        ),
        f"  est. tokens: ~{est_tokens} (rough, chars/4)",
        f"  truncated: {'yes' if truncated else 'no'}",
        f"  sections ({len(section_lines)} total, lines):",
    ]
    for title, count in section_lines:
        lines.append(f"    - {title}: {count}")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default=".review-context/dependencies.md",
        help="Output markdown path.",
    )
    args = parser.parse_args(argv)

    output = context_repo.resolve_output_path(args.output)
    if output is None:
        print(
            f"Refusing to write review context outside repository or temp dir: {args.output}",
            file=sys.stderr,
        )
        return 1

    markdown = build_context()

    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(markdown, encoding="utf-8")
    except OSError as exc:
        print(f"Failed to write review context to {output}: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote {output}")
    max_bytes = getenv_int(
        "OCR_BACKGROUND_MAX_BYTES",
        DEFAULT_BACKGROUND_MAX_BYTES,
        max_value=MAX_BACKGROUND_MAX_BYTES,
    )
    max_chars = getenv_int(
        "OCR_BACKGROUND_MAX_CHARS",
        DEFAULT_BACKGROUND_MAX_CHARS,
        max_value=MAX_BACKGROUND_MAX_CHARS,
    )
    print(summarize_context(markdown, max_bytes, max_chars))
    return 0
