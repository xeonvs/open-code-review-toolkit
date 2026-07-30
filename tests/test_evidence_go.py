"""Go module, checksum, delta, and MCP evidence tests."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from ocr_toolkit.evidence.collect import collect_repository_evidence
from ocr_toolkit.evidence.collectors import collect_ref_facts, manifest_collector
from ocr_toolkit.evidence.go_manifests import parse_go_mod, parse_go_sum
from ocr_toolkit.evidence.manifest_model import MAX_MANIFEST_ITEMS
from ocr_toolkit.evidence.mcp import handle_request
from ocr_toolkit.evidence.model import RefRole
from ocr_toolkit.evidence.repository import GitRepositoryReader


def _git(root: Path, *args: str) -> str:
    """Run bounded Git commands against one synthetic repository."""

    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        text=True,
        capture_output=True,
    )
    return completed.stdout.strip()


def test_go_mod_preserves_module_runtime_require_replace_and_exclude() -> None:
    """Model direct/indirect requirements and exact replacement semantics."""

    parsed = parse_go_mod(
        """
module example.invalid/team/service

go 1.24.0
toolchain go1.25.2
godebug default=go1.24

require example.invalid/direct v1.2.3
require (
    example.invalid/indirect v2.0.0 // indirect
    example.invalid/also-direct v3.0.0
)

replace example.invalid/direct v1.2.3 => example.invalid/fork v1.2.4
replace (
    example.invalid/local => ../local-copy
)
exclude example.invalid/bad v1.9.0
tool example.invalid/tool/cmd
retract [v1.0.0, v1.0.5]
ignore internal/generated
"""
    )

    by_kind = {
        kind: [fact for fact in parsed.facts if fact.kind == kind]
        for kind in {
            "repository.manifest",
            "runtime.declared",
            "dependency.declared",
        }
    }
    assert by_kind["repository.manifest"][0].value["name"] == ("example.invalid/team/service")
    runtimes = {fact.identity: fact.value for fact in by_kind["runtime.declared"]}
    assert runtimes["go"]["constraint"] == "1.24.0"
    assert runtimes["toolchain"]["constraint"] == "go1.25.2"
    assert runtimes["godebug:default"]["constraint"] == "go1.24"
    declarations = by_kind["dependency.declared"]
    requirements = {
        fact.value["name"]: fact.value
        for fact in declarations
        if fact.value["scope"] in {"direct", "indirect"}
    }
    assert requirements["example.invalid/direct"]["scope"] == "direct"
    assert requirements["example.invalid/indirect"]["scope"] == "indirect"
    replacements = {
        fact.value["name"]: fact.value for fact in declarations if fact.value["scope"] == "replace"
    }
    assert replacements["example.invalid/direct"]["replacement"] == "example.invalid/fork"
    assert replacements["example.invalid/direct"]["replacement_version"] == "v1.2.4"
    assert replacements["example.invalid/local"]["replacement_type"] == "local"
    excluded = next(fact.value for fact in declarations if fact.value["scope"] == "exclude")
    assert excluded["version"] == "v1.9.0"
    assert any(fact.value["scope"] == "tool" for fact in declarations)
    assert any(fact.value["scope"] == "retract" for fact in declarations)
    assert any(
        fact.value.get("manifest_type") == "go.ignore" for fact in by_kind["repository.manifest"]
    )


def test_go_sum_preserves_module_and_go_mod_checksum_pairs() -> None:
    """Keep both module zip and go.mod checksums as resolved facts."""

    parsed = parse_go_sum(
        """
example.invalid/module v1.2.3 h1:synthetic-module
example.invalid/module v1.2.3/go.mod h1:synthetic-modfile
malformed line
"""
    )

    assert [(fact.value["content"], fact.value["checksum"]) for fact in parsed.facts] == [
        ("module", "h1:synthetic-module"),
        ("go.mod", "h1:synthetic-modfile"),
    ]
    assert parsed.notices == ("go.sum skipped a malformed checksum line",)


def test_go_mod_preserves_comment_markers_inside_quoted_tokens() -> None:
    """Treat double slash as a comment only outside interpreted and raw strings."""

    parsed = parse_go_mod(
        """module `example.invalid/team//service`
replace example.invalid/quoted => "../local//copy" // local checkout
replace example.invalid/raw => `../raw//copy`
require "example.invalid/team//module" v1.2.3 // indirect
"""
    )

    facts = {fact.identity: fact for fact in parsed.facts}
    assert facts["module"].value["name"] == "example.invalid/team//service"
    assert facts["replace:example.invalid/quoted"].value["replacement"] == "../local//copy"
    assert facts["replace:example.invalid/raw"].value["replacement"] == "../raw//copy"
    assert facts["indirect:example.invalid/team//module"].value["version"] == "v1.2.3"


def test_go_parsers_apply_one_aggregate_bound_with_notice() -> None:
    """Bound module and checksum facts rather than multiplying per directive."""

    go_mod = parse_go_mod(
        "module example.invalid/root\nrequire (\n"
        + "".join(
            f"example.invalid/module-{index:04d} v1.0.0\n"
            for index in range(MAX_MANIFEST_ITEMS + 1)
        )
        + ")\n"
    )
    go_sum = parse_go_sum(
        "".join(
            f"example.invalid/module-{index:04d} v1.0.0 h1:sum-{index}\n"
            for index in range(MAX_MANIFEST_ITEMS + 1)
        )
    )

    assert len(go_mod.facts) == MAX_MANIFEST_ITEMS
    assert go_mod.notices == (f"go.mod facts were truncated after {MAX_MANIFEST_ITEMS} items",)
    assert len(go_sum.facts) == MAX_MANIFEST_ITEMS
    assert go_sum.notices == (f"go.sum facts were truncated after {MAX_MANIFEST_ITEMS} items",)


def test_go_deltas_and_builtin_mcp_preserve_resolved_changes(tmp_path: Path) -> None:
    """Expose Go runtime, declaration, and checksum changes through MCP."""

    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "agent@example.invalid")
    _git(tmp_path, "config", "user.name", "Synthetic Agent")

    def write_state(go_version: str, module_version: str, checksum: str) -> None:
        (tmp_path / "go.mod").write_text(
            "module example.invalid/service\n"
            f"go {go_version}\n"
            f"require example.invalid/demo {module_version}\n",
            encoding="utf-8",
        )
        (tmp_path / "go.sum").write_text(
            f"example.invalid/demo {module_version} h1:{checksum}\n", encoding="utf-8"
        )

    write_state("1.23.0", "v1.0.0", "base")
    _git(tmp_path, "add", "go.mod", "go.sum")
    _git(tmp_path, "commit", "-qm", "base Go evidence")
    base = _git(tmp_path, "rev-parse", "HEAD")
    write_state("1.24.0", "v2.0.0", "head")
    _git(tmp_path, "add", "go.mod", "go.sum")
    _git(tmp_path, "commit", "-qm", "head Go evidence")
    head = _git(tmp_path, "rev-parse", "HEAD")

    store = collect_repository_evidence(tmp_path, base_ref=base, head_ref=head)
    assert {delta.kind for delta in store.deltas} >= {
        "runtime.declared",
        "dependency.declared",
        "dependency.locked",
    }
    requirement_delta = next(delta for delta in store.deltas if delta.kind == "dependency.declared")
    assert requirement_delta.change == "changed"
    assert requirement_delta.before["version"] == "v1.0.0"
    assert requirement_delta.after["version"] == "v2.0.0"

    response = handle_request(
        store,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "ocr_toolkit_evidence",
                "arguments": {"action": "list", "component": "go", "ref": "head"},
            },
        },
    )
    payload = json.loads(response["result"]["content"][0]["text"])
    assert {record["kind"] for record in payload["records"]} >= {
        "repository.manifest",
        "runtime.declared",
        "dependency.declared",
        "dependency.locked",
    }


def test_go_sum_malformed_lines_are_safe_diagnostics(tmp_path: Path) -> None:
    """Retain a bounded safe notice without copying malformed repository text."""

    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "agent@example.invalid")
    _git(tmp_path, "config", "user.name", "Synthetic Agent")
    (tmp_path / "go.sum").write_text("secret malformed payload\n", encoding="utf-8")
    _git(tmp_path, "add", "go.sum")
    _git(tmp_path, "commit", "-qm", "malformed checksum evidence")

    records, diagnostics = collect_ref_facts(
        GitRepositoryReader(tmp_path), _git(tmp_path, "rev-parse", "HEAD"), RefRole.HEAD
    )

    assert {record.kind for record in records} == {"repository.manifest"}
    assert diagnostics == ["head:go.sum: go.sum skipped a malformed checksum line"]
    assert manifest_collector("modules/go.sum").ecosystem == "go"
