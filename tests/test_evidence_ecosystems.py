"""Architecture contracts for bounded ecosystem source adapters."""

from __future__ import annotations

import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[1]
EVIDENCE_ROOT = PROJECT_ROOT / "src/ocr_toolkit/evidence"
ECOSYSTEMS_ROOT = EVIDENCE_ROOT / "ecosystems"


def test_ecosystem_adapters_have_one_closed_package_layout_without_flat_shims() -> None:
    """Keep source parsers below frameworks in one explicit internal package."""

    expected = {
        "__init__.py",
        "ansible/__init__.py",
        "ansible/requirements.py",
        "ansible/topology.py",
        "contracts.py",
        "go.py",
        "javascript.py",
        "php.py",
        "python.py",
    }
    actual = {
        path.relative_to(ECOSYSTEMS_ROOT).as_posix() for path in ECOSYSTEMS_ROOT.rglob("*.py")
    }
    assert actual == expected

    removed_flat_modules = {
        "ansible.py",
        "ansible_requirements.py",
        "composer_manifests.py",
        "go_manifests.py",
        "javascript_manifests.py",
        "manifest_model.py",
        "python_manifests.py",
    }
    assert not any((EVIDENCE_ROOT / name).exists() for name in removed_flat_modules)


def test_ecosystem_adapters_cannot_own_or_call_higher_evidence_layers() -> None:
    """Prevent normalized source adapters from growing I/O or lifecycle ownership."""

    forbidden_imports = {
        "http",
        "importlib",
        "os",
        "requests",
        "socket",
        "subprocess",
        "urllib.error",
        "urllib.request",
    }
    forbidden_evidence_modules = {
        "ocr_toolkit.evidence.collect",
        "ocr_toolkit.evidence.collectors",
        "ocr_toolkit.evidence.frameworks",
        "ocr_toolkit.evidence.infrastructure",
        "ocr_toolkit.evidence.mcp",
        "ocr_toolkit.evidence.repository",
        "ocr_toolkit.evidence.store",
    }
    forbidden_calls = {"__import__", "eval", "exec", "open"}

    for source_path in sorted(ECOSYSTEMS_ROOT.rglob("*.py")):
        tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
        assert ast.get_docstring(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported = {alias.name for alias in node.names}
                assert not imported & forbidden_imports
                assert not imported & forbidden_evidence_modules
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert node.module not in forbidden_imports
                assert not any(
                    node.module == module or node.module.startswith(module + ".")
                    for module in forbidden_evidence_modules
                )
                if node.module == "pathlib":
                    assert {alias.name for alias in node.names} == {"PurePosixPath"}
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in forbidden_calls
