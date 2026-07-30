"""Contract tests for provider-neutral immutable change categorization."""

from ocr_toolkit.evidence.categorize import categorize_paths


def test_categories_are_deterministic_and_allow_relevant_overlap() -> None:
    """Preserve review-relevant multi-category membership in stable order."""

    categories = categorize_paths(
        [
            "roles/api/templates/app.service.j2",
            "requirements.txt",
            "roles/api/tasks/main.yml",
            "requirements.txt",
        ]
    )

    assert list(categories) == [
        "dependency_manifests",
        "ansible_roles",
        "templates",
    ]
    assert categories["dependency_manifests"] == ("requirements.txt",)
    assert categories["ansible_roles"] == (
        "roles/api/tasks/main.yml",
        "roles/api/templates/app.service.j2",
    )
    assert categories["templates"] == ("roles/api/templates/app.service.j2",)


def test_categories_include_standard_and_named_pylock_manifests() -> None:
    """Keep every supported PEP 751 lock manifest in dependency review scope."""

    categories = categorize_paths(["pylock.toml", "locks/pylock.production.toml"])

    assert categories["dependency_manifests"] == (
        "locks/pylock.production.toml",
        "pylock.toml",
    )


def test_explicit_playbook_category_coexists_with_other_categories() -> None:
    """Keep semantic playbook detection independent from suffix categories."""

    categories = categorize_paths(
        ["playbooks/deploy.yml"], ansible_playbooks=["playbooks/deploy.yml"]
    )

    assert categories == {"ansible_playbooks": ("playbooks/deploy.yml",)}


def test_categories_cover_ci_inventory_and_keep_declared_order() -> None:
    """Preserve legacy review signals through the typed category registry."""

    categories = categorize_paths(
        [
            "README.md",
            ".gitlab-ci.yml",
            "ops/inventory.ini",
            "deploy/hosts.yml",
            "roles/app/tasks/main.yml",
        ]
    )

    assert list(categories) == ["ci", "ansible_roles", "ansible_inventory", "docs"]
    assert categories["ansible_inventory"] == (
        "deploy/hosts.yml",
        "ops/inventory.ini",
    )
