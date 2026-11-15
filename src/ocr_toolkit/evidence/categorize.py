"""Categorize immutable changed paths for typed repository evidence."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence

from ocr_toolkit.evidence.container_paths import is_container_build_file

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
    "csharp",
    "go",
    "php",
    "javascript_typescript",
    "sql",
    "docs",
    "other",
)

DEPENDENCY_MANIFEST_PATTERN = re.compile(
    r"(^|/)(requirements[^/]*\.(?:txt|in)|constraints[^/]*\.(?:txt|in)|"
    r"requirements/[^/]+\.(?:txt|in)|requirements\.ya?ml|pyproject\.toml|"
    r"pylock(?:\.[^/]+)?\.toml|poetry\.lock|uv\.lock|Pipfile(\.lock)?|"
    r"package(-lock)?\.json|"
    r"pnpm-lock\.yaml|yarn\.lock|composer\.(json|lock)|go\.(mod|sum)|"
    r"Cargo\.(toml|lock)|Gemfile(\.lock)?|pom\.xml|build\.gradle(\.kts)?|"
    r"gradle\.lockfile|[^/]+\.(?:csproj|fsproj|vbproj)|Directory\.(?:Build\.(?:props|targets)|Packages\.props)|packages\.lock\.json|global\.json)$",
    re.I,
)

CATEGORY_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("ocr_integration", re.compile(r"(^|/)\.opencodereview/", re.I)),
    ("ci", re.compile(r"(^|/)\.gitlab-ci\.ya?ml$|(^|/)\.github/", re.I)),
    ("dependency_manifests", DEPENDENCY_MANIFEST_PATTERN),
    ("molecule_tests", re.compile(r"(^|/)roles/[^/]+/molecule/", re.I)),
    (
        "systemd_units",
        re.compile(
            r"\.(service|timer|socket|device|mount|automount|path|target|slice|swap|scope)$|"
            r"\.(service|timer|socket|device|mount|automount|path|target|slice|swap|scope)"
            r"\.d/[^/]+\.conf$",
            re.I,
        ),
    ),
    (
        "containers",
        re.compile(
            r"(^|/)(docker-compose.*\.ya?ml|compose(?:\.[^/]+)?\.ya?ml)$",
            re.I,
        ),
    ),
    ("shell", re.compile(r"(^|/)apb$|\.(sh|bash|zsh)$", re.I)),
    ("ansible_roles", re.compile(r"(^|/)roles/", re.I)),
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
    ("csharp", re.compile(r"\.(cs|csx)$", re.I)),
    ("go", re.compile(r"\.go$", re.I)),
    ("php", re.compile(r"\.php$", re.I)),
    ("javascript_typescript", re.compile(r"\.(js|jsx|ts|tsx|mjs|cjs)$", re.I)),
    ("sql", re.compile(r"\.sql$", re.I)),
    ("docs", re.compile(r"\.(md|rst|adoc)$", re.I)),
)


def categorize_paths(
    paths: Sequence[str], *, ansible_playbooks: Iterable[str] = ()
) -> Mapping[str, tuple[str, ...]]:
    """Group normalized changed paths into deterministic review categories."""

    playbooks = set(ansible_playbooks)
    categorized: dict[str, list[str]] = {}
    for path in sorted(set(paths)):
        matched = is_container_build_file(path)
        if matched:
            categorized.setdefault("containers", []).append(path)
        if path in playbooks:
            categorized.setdefault("ansible_playbooks", []).append(path)
            matched = True
        for category, pattern in CATEGORY_PATTERNS:
            if pattern.search(path):
                categorized.setdefault(category, []).append(path)
                matched = True
        if not matched:
            categorized.setdefault("other", []).append(path)
    return {
        category: tuple(categorized[category])
        for category in CATEGORY_ORDER
        if category in categorized
    }
