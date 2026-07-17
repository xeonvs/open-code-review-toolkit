"""Changed-file categorization for OCR context."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

from ocr_toolkit.context.ansible import is_root_ansible_playbook

CATEGORY_ORDER = (
    "ansible_playbooks",
    "ocr_integration",
    "ci",
    "dependency_manifests",
    "molecule_tests",
    "systemd_units",
    "containers",
    "shell",
    "ansible_roles",
    "ansible_inventory",
    "templates",
    "terraform_hcl",
    "python",
    "go",
    "php",
    "javascript_typescript",
    "sql",
    "docs",
    "other",
)


DEPENDENCY_MANIFEST_PATTERN = re.compile(
    r"(^|/)(requirements[^/]*\.(?:txt|in)|constraints[^/]*\.(?:txt|in)|requirements/[^/]+\.(?:txt|in)|requirements\.ya?ml|pyproject\.toml|"
    r"poetry\.lock|uv\.lock|Pipfile(\.lock)?|package(-lock)?\.json|pnpm-lock\.yaml|"
    r"yarn\.lock|composer\.(json|lock)|go\.(mod|sum)|Cargo\.(toml|lock)|"
    r"Gemfile(\.lock)?|pom\.xml|build\.gradle(\.kts)?|gradle\.lockfile)$",
    re.I,
)


PYTHON_MANIFEST_PATTERN = re.compile(
    r"(^|/)(requirements[^/]*\.(?:txt|in)|constraints[^/]*\.(?:txt|in)|requirements/[^/]+\.(?:txt|in)|pyproject\.toml|poetry\.lock|uv\.lock|Pipfile(\.lock)?)$",
    re.I,
)


CATEGORY_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "ocr_integration",
        re.compile(r"(^|/)\.opencodereview/", re.I),
    ),
    ("ci", re.compile(r"(^|/)\.gitlab-ci\.ya?ml$|(^|/)\.github/", re.I)),
    (
        "dependency_manifests",
        DEPENDENCY_MANIFEST_PATTERN,
    ),
    (
        "molecule_tests",
        re.compile(r"(^|/)roles/[^/]+/molecule/", re.I),
    ),
    (
        "systemd_units",
        re.compile(
            r"\.(service|timer|socket|device|mount|automount|path|target|slice|swap|scope)$|"
            r"\.(service|timer|socket|device|mount|automount|path|target|slice|swap|scope)\.d/[^/]+\.conf$",
            re.I,
        ),
    ),
    (
        "containers",
        re.compile(
            r"(^|/)(Dockerfile(?:\.[^/]+)?|Containerfile(?:\.[^/]+)?|"
            r"[^/]+\.Dockerfile|docker-compose.*\.ya?ml|compose(?:\.[^/]+)?\.ya?ml)$|"
            r"\.dockerfile$",
            re.I,
        ),
    ),
    ("shell", re.compile(r"(^|/)apb$|\.(sh|bash|zsh)$", re.I)),
    (
        "ansible_roles",
        re.compile(r"(^|/)roles/", re.I),
    ),
    (
        "ansible_inventory",
        re.compile(
            r"(^|/)(inventory|inventories|group_vars|host_vars)(/|$)|"
            r"(^|/)(hosts|inventory)\.(ya?ml|ini|cfg|json)$",
            re.I,
        ),
    ),
    ("templates", re.compile(r"\.(j2|jinja|jinja2|tpl|tmpl)$", re.I)),
    ("terraform_hcl", re.compile(r"\.(tf|tfvars|hcl)$", re.I)),
    ("python", re.compile(r"\.(py|pyi)$", re.I)),
    ("go", re.compile(r"\.go$", re.I)),
    ("php", re.compile(r"\.php$", re.I)),
    ("javascript_typescript", re.compile(r"\.(js|jsx|ts|tsx|mjs|cjs)$", re.I)),
    ("sql", re.compile(r"\.sql$", re.I)),
    ("docs", re.compile(r"\.(md|rst|adoc)$", re.I)),
]


PROVIDER_MANIFEST_PATTERNS: dict[str, re.Pattern[str]] = {
    "ansible": re.compile(r"(^|/)(ansible\.cfg|requirements\.ya?ml|galaxy\.ya?ml)$", re.I),
    "python": PYTHON_MANIFEST_PATTERN,
    "go": re.compile(r"(^|/)go\.(mod|sum)$", re.I),
    "php": re.compile(r"(^|/)composer\.(json|lock)$", re.I),
    "javascript": re.compile(
        r"(^|/)(package\.json|package-lock\.json|pnpm-lock\.yaml|yarn\.lock)$",
        re.I,
    ),
}


def active_context_providers(
    files: Sequence[str], categories: Mapping[str, Sequence[str]]
) -> set[str]:
    """Return generic ecosystem providers activated by changed paths."""

    active_categories = set(categories)
    providers: set[str] = set()
    if active_categories & {
        "ansible_playbooks",
        "ansible_roles",
        "ansible_inventory",
        "molecule_tests",
    }:
        providers.add("ansible")
    if "python" in active_categories:
        providers.add("python")
    if "go" in active_categories:
        providers.add("go")
    if "php" in active_categories:
        providers.add("php")
    if "javascript_typescript" in active_categories:
        providers.add("javascript")
    for file_path in files:
        for provider, pattern in PROVIDER_MANIFEST_PATTERNS.items():
            if pattern.search(file_path):
                providers.add(provider)
    return providers


def categorize_files(files: Sequence[str]) -> dict[str, list[str]]:
    """Categorize changed files by technology or operational area."""

    categorized: dict[str, list[str]] = {}
    for file_path in files:
        matched = False
        if is_root_ansible_playbook(file_path):
            categorized.setdefault("ansible_playbooks", []).append(file_path)
            matched = True
        for category, pattern in CATEGORY_PATTERNS:
            if pattern.search(file_path):
                categorized.setdefault(category, []).append(file_path)
                matched = True
        if not matched:
            categorized.setdefault("other", []).append(file_path)

    return {
        category: categorized[category] for category in CATEGORY_ORDER if category in categorized
    }
