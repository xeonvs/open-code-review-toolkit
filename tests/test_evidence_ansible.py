"""Typed immutable Ansible topology collector tests."""

import json
import subprocess
from pathlib import Path

from ocr_toolkit.evidence.ansible import collect_topology, topology_candidate
from ocr_toolkit.evidence.collect import collect_repository_evidence
from ocr_toolkit.evidence.mcp import call_tool


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


def test_topology_is_queryable_from_the_evidence_mcp(tmp_path: Path) -> None:
    """Carry immutable topology through the store into filtered MCP queries."""

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
