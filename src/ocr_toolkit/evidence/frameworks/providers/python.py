"""Package-owned Jinja2 provider declaration."""

from __future__ import annotations

import re

from ocr_toolkit.evidence.frameworks.detection import PackageFrameworkPlugin, PackageFrameworkSpec

_PYTHON_DECLARATIONS = (re.compile(r"(^|/)(pyproject\.toml|requirements[^/]*\.(txt|in))$", re.I),)
_PYTHON_RESOLUTIONS = (
    re.compile(r"(^|/)(uv\.lock|poetry\.lock|pipfile\.lock|pylock(?:\.[^/]+)?\.toml)$", re.I),
)

JINJA2_PLUGIN = PackageFrameworkPlugin(
    "jinja2",
    "python",
    (PackageFrameworkSpec("jinja2", ("jinja2",), "template-engine"),),
    configuration_patterns=(*_PYTHON_DECLARATIONS, *_PYTHON_RESOLUTIONS),
)
