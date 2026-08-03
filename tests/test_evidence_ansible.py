"""Typed immutable Ansible topology collector tests."""

import json
import os
import subprocess
from pathlib import Path

from ocr_toolkit.evidence.ansible import (
    collect_topology,
    selected_role_paths,
    topology_candidate,
    topology_coverage,
)
from ocr_toolkit.evidence.ansible_requirements import parse_galaxy_requirements
from ocr_toolkit.evidence.collect import collect_repository_evidence
from ocr_toolkit.evidence.collectors import MAX_TOPOLOGY_FACTS_PER_KIND
from ocr_toolkit.evidence.mcp import call_tool
from ocr_toolkit.evidence.model import CoverageState


def _mcp_payload(result: dict[str, object]) -> dict[str, object]:
    """Decode the MCP text envelope into its typed JSON payload."""

    content = result["content"]
    assert isinstance(content, list)
    item = content[0]
    assert isinstance(item, dict)
    text = item["text"]
    assert isinstance(text, str)
    payload = json.loads(text)
    assert isinstance(payload, dict)
    return payload


def test_collects_root_playbook_without_misclassifying_generic_yaml() -> None:
    """Require play structure before emitting a root-level playbook fact."""

    playbook = collect_topology("deploy.yml", "- name: Deploy\n  hosts: all\n  tasks: []\n")
    generic = collect_topology("settings.yml", "hosts: example.invalid\nmode: safe\n")

    assert [fact.kind for fact in playbook] == ["ansible.playbook"]
    assert playbook[0].value == {"path": "deploy.yml", "scope": "root"}
    assert generic == ()
    assert topology_candidate("settings.yml")


def test_collects_canonical_role_surfaces_only() -> None:
    """Describe role metadata/defaults/vars without scanning arbitrary role YAML."""

    metadata = collect_topology("roles/api/meta/main.yml", "galaxy_info: {}\n")
    defaults = collect_topology("roles/api/defaults/main.yaml", "port: 8080\n")
    variables = collect_topology("roles/api/vars/main.yml", "runtime_version: 2.0.0\n")

    assert [(fact.kind, fact.identity) for fact in (*metadata, *defaults, *variables)] == [
        ("ansible.role_metadata", "roles/api/meta/main.yml"),
        ("ansible.role_defaults", "roles/api/defaults/main.yaml"),
        ("ansible.role_vars", "roles/api/vars/main.yml"),
    ]
    assert not topology_candidate("roles/api/tasks/main.yml")


def test_playbook_detection_matches_sequence_and_import_contract() -> None:
    """Reject top-level mappings and accept quoted hosts or imported playbooks."""

    assert collect_topology("quoted.yml", "- name: Review\n  'hosts': all\n")
    assert collect_topology("import.yml", "- import_playbook: common.yml\n")
    assert collect_topology("mapping.yml", "hosts: all\ntasks: []\n") == ()


def test_collects_bounded_ini_and_yaml_inventory_groups() -> None:
    """Expose inventory paths and group topology without host-variable contents."""

    ini = collect_topology("inventories/stage/hosts.ini", "[web]\na.invalid\n[db:children]\nweb\n")
    yaml = collect_topology(
        "inventory.yml",
        "all:\n  children:\n    workers:\n      hosts: {}\n    database: {}\n",
    )

    assert {fact.value.get("group") for fact in ini if fact.kind.endswith("group")} == {
        "web",
        "db",
    }
    assert {fact.value.get("group") for fact in yaml if fact.kind.endswith("group")} == {
        "workers",
        "database",
    }
    assert not topology_candidate("inventories/stage/group_vars/all.yml")


def test_dynamic_and_executable_inventory_are_runtime_dependent_without_execution() -> None:
    """Recognize future-compatible source shapes only from bounded static signals."""

    dynamic_text = "plugin: synthetic.dynamic_inventory\ngroup_by: [role]\n"
    dynamic = collect_topology("inventories/stage/dynamic.yml", dynamic_text)
    executable = collect_topology(
        "inventories/stage/source.py",
        "#!/usr/bin/env python3\nraise SystemExit(99)\n",
        executable=True,
    )

    assert dynamic[0].value == {
        "path": "inventories/stage/dynamic.yml",
        "source_type": "dynamic",
        "group_coverage": "runtime-dependent",
    }
    assert executable[0].value["source_type"] == "executable"
    assert topology_coverage("inventories/stage/dynamic.yml", dynamic_text)[2].state is (
        CoverageState.RUNTIME_DEPENDENT
    )
    assert topology_candidate("inventories/stage/source.py", executable=True)


def test_static_inventory_is_complete_only_for_the_closed_supported_syntax() -> None:
    """Parse common quoted/empty groups and fail closed for malformed or templated YAML."""

    supported = '"web": {}\nall:\n  children:\n    workers: {}\n'
    malformed = "all:\n  children\n    workers: {}\n"
    templated = 'all:\n  children:\n    "{{ generated_group }}": {}\n'

    facts = collect_topology("inventories/stage/hosts.yml", supported)
    groups = {fact.value["group"] for fact in facts if fact.kind.endswith("group")}
    supported_coverage = topology_coverage("inventories/stage/hosts.yml", supported)
    malformed_coverage = topology_coverage("inventories/stage/hosts.yml", malformed)
    templated_coverage = topology_coverage("inventories/stage/hosts.yml", templated)

    assert groups == {"web", "workers"}
    assert supported_coverage is not None
    assert supported_coverage[2].state is CoverageState.COMPLETE
    assert malformed_coverage is not None
    assert malformed_coverage[2].state is not CoverageState.COMPLETE
    assert templated_coverage is not None
    assert templated_coverage[2].state is not CoverageState.COMPLETE


def test_recursive_role_main_selection_matches_ansible_2_17_and_later_contract() -> None:
    """Prefer canonical main files, otherwise traverse supported main directories."""

    paths = (
        "roles/api/defaults/main/base.yml",
        "roles/api/defaults/main/nested/feature.json",
        "roles/api/defaults/main/.hidden.yml",
        "roles/api/defaults/main/backup.yml~",
        "roles/api/defaults/main/unsupported.txt",
        "roles/api/vars/main.yml",
        "roles/api/vars/main/ignored.yml",
    )

    selected = selected_role_paths(paths)

    assert selected == {
        "roles/api/defaults/main/base.yml",
        "roles/api/defaults/main/nested/feature.json",
        "roles/api/vars/main.yml",
    }
    recursive = collect_topology(
        "roles/api/defaults/main/nested/feature.json", '{"feature": true}\n'
    )
    assert recursive[0].kind == "ansible.role_defaults"


def test_recursive_role_fact_limit_degrades_coverage_atomically(tmp_path: Path) -> None:
    """Never claim complete role coverage after bounded positive facts are omitted."""

    environment = {
        "GIT_AUTHOR_NAME": "Synthetic Author",
        "GIT_AUTHOR_EMAIL": "author@example.invalid",
        "GIT_COMMITTER_NAME": "Synthetic Committer",
        "GIT_COMMITTER_EMAIL": "committer@example.invalid",
    }

    def git(*args: str) -> str:
        completed = subprocess.run(
            ["git", "-C", str(tmp_path), *args],
            check=True,
            capture_output=True,
            text=True,
            env=environment,
        )
        return completed.stdout.strip()

    git("init", "-q")
    (tmp_path / "README.md").write_text("synthetic\n", encoding="utf-8")
    git("add", "README.md")
    git("commit", "-qm", "base")
    base = git("rev-parse", "HEAD")
    role_dir = tmp_path / "roles" / "api" / "defaults" / "main"
    role_dir.mkdir(parents=True)
    for index in range(MAX_TOPOLOGY_FACTS_PER_KIND + 1):
        (role_dir / f"{index:03}.yml").write_text(f"synthetic_{index}: true\n", encoding="utf-8")
    git("add", "roles")
    git("commit", "-qm", "large role")
    head = git("rev-parse", "HEAD")

    store = collect_repository_evidence(tmp_path, base_ref=base, head_ref=head)
    role_facts = [
        record
        for record in store.records
        if record.ref.value == "head" and record.kind == "ansible.role_defaults"
    ]
    role_coverage = next(
        item
        for item in store.coverage
        if item.ref.value == "head" and item.domain == "role.defaults"
    )

    assert len(role_facts) == MAX_TOPOLOGY_FACTS_PER_KIND
    assert role_coverage.state is CoverageState.PARTIAL
    assert "topology-fact-limit" in role_coverage.reasons


def test_yaml_inventory_accepts_top_level_groups_and_rejects_metadata_files() -> None:
    inventory = collect_topology(
        "inventories/prod/hosts.yaml",
        "web:\n  hosts:\n    web-01:\n  vars:\n    port: 443\n",
    )

    assert any(
        fact.kind == "ansible.inventory_group" and fact.value["group"] == "web"
        for fact in inventory
    )
    assert not topology_candidate("inventories/prod/README.md")
    assert not topology_candidate("inventories/prod/schema.json")


def test_galaxy_nested_installer_fields_do_not_override_dependency_identity() -> None:
    parsed = parse_galaxy_requirements(
        """
roles:
  - name: synthetic.web
    version: 1.0.0
    options:
      name: malicious.override
      version: 9.9.9
"""
    )

    assert len(parsed.requirements) == 1
    requirement = parsed.requirements[0]
    assert requirement.name == "synthetic.web"
    assert requirement.version == "1.0.0"


def test_inventory_children_use_the_declared_yaml_indentation() -> None:
    """Accept sibling groups at a consistent indentation wider than two spaces."""

    facts = collect_topology(
        "inventory.yml",
        """all:
    children:
        web:
            hosts:
                web-1:
        workers:
            vars:
                queue: default
    vars:
        ignored: true
""",
    )

    assert [fact.identity for fact in facts if fact.kind.endswith("group")] == [
        "inventory.yml:web",
        "inventory.yml:workers",
    ]


def test_topology_is_queryable_from_the_evidence_mcp(tmp_path: Path) -> None:
    """Carry immutable topology through the store into filtered MCP queries."""

    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    environment.update(
        {
            "GIT_AUTHOR_NAME": "Synthetic Author",
            "GIT_AUTHOR_EMAIL": "author@example.invalid",
            "GIT_COMMITTER_NAME": "Synthetic Committer",
            "GIT_COMMITTER_EMAIL": "committer@example.invalid",
            "GIT_CONFIG_COUNT": "2",
            "GIT_CONFIG_KEY_0": "commit.gpgsign",
            "GIT_CONFIG_VALUE_0": "false",
            "GIT_CONFIG_KEY_1": "core.hooksPath",
            "GIT_CONFIG_VALUE_1": str(tmp_path / "disabled-hooks"),
        }
    )

    def git(*args: str) -> str:
        """Run one synthetic repository command with deterministic identity."""

        completed = subprocess.run(
            ["git", "-C", str(tmp_path), *args],
            check=True,
            capture_output=True,
            text=True,
            env=environment,
        )
        return completed.stdout.strip()

    git("init", "-q")
    (tmp_path / "README.md").write_text("synthetic\n", encoding="utf-8")
    git("add", "README.md")
    git("commit", "-qm", "base")
    base = git("rev-parse", "HEAD")
    (tmp_path / "inventory.yml").write_text(
        "all:\n  children:\n    workers: {}\n", encoding="utf-8"
    )
    git("add", "inventory.yml")
    git("commit", "-qm", "inventory")
    head = git("rev-parse", "HEAD")

    store = collect_repository_evidence(tmp_path, base_ref=base, head_ref=head)
    listed = _mcp_payload(
        call_tool(
            store,
            {"action": "list", "kind": "ansible.inventory_group", "page_size": 10},
        )
    )

    assert listed["returned"] == 1
    item = listed["records"][0]
    assert item["value"]["fact"] == {"path": "inventory.yml", "group": "workers"}
    fetched = _mcp_payload(call_tool(store, {"action": "get", "id": item["id"]}))
    assert fetched["record"] == item
    coverage = _mcp_payload(
        call_tool(
            store,
            {"action": "list", "kind": "repository.evidence_coverage", "ref": "head"},
        )
    )
    coverage_item = next(
        record
        for record in coverage["records"]
        if record["domain"] == "inventory.groups" and record["scope"] == "."
    )
    assert coverage_item["state"] == "complete"


def test_galaxy_requirement_change_is_queryable_from_the_evidence_mcp(
    tmp_path: Path,
) -> None:
    """Carry source-aware Galaxy declarations and semantic deltas through MCP."""

    environment = {
        "GIT_AUTHOR_NAME": "Synthetic Author",
        "GIT_AUTHOR_EMAIL": "author@example.invalid",
        "GIT_COMMITTER_NAME": "Synthetic Committer",
        "GIT_COMMITTER_EMAIL": "committer@example.invalid",
    }

    def git(*args: str) -> str:
        """Run one synthetic repository command with deterministic identity."""

        completed = subprocess.run(
            ["git", "-C", str(tmp_path), *args],
            check=True,
            capture_output=True,
            text=True,
            env=environment,
        )
        return completed.stdout.strip()

    git("init", "-q")
    requirements = tmp_path / "requirements.yml"
    requirements.write_text(
        "collections:\n  - name: synthetic.collection\n    version: 1.0.0\n",
        encoding="utf-8",
    )
    git("add", "requirements.yml")
    git("commit", "-qm", "base")
    base = git("rev-parse", "HEAD")
    requirements.write_text(
        "collections:\n  - name: synthetic.collection\n    version: 2.0.0\n",
        encoding="utf-8",
    )
    git("add", "requirements.yml")
    git("commit", "-qm", "update collection")
    head = git("rev-parse", "HEAD")

    store = collect_repository_evidence(tmp_path, base_ref=base, head_ref=head)
    galaxy_delta = next(
        delta
        for delta in store.deltas
        if delta.kind == "dependency.declared" and delta.component == "ansible"
    )
    listed = _mcp_payload(
        call_tool(
            store,
            {"action": "list", "component": "ansible", "ref": "head"},
        )
    )

    assert galaxy_delta.change == "changed"
    assert galaxy_delta.identity == ("requirements.yml:collection:synthetic.collection")
    assert galaxy_delta.before["version"] == "1.0.0"
    assert galaxy_delta.after["version"] == "2.0.0"
    dependency = next(
        record for record in listed["records"] if record["kind"] == "dependency.declared"
    )
    assert dependency["value"]["fact"]["requirement_type"] == "collection"
    fetched = _mcp_payload(call_tool(store, {"action": "get", "id": dependency["id"]}))
    assert fetched["record"] == dependency
