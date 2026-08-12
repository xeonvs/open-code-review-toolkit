"""Package-owned React and TypeScript ecosystem provider declaration."""

from __future__ import annotations

import re

from ocr_toolkit.evidence.frameworks.detection import (
    PackageFrameworkPlugin,
    PackageFrameworkSpec,
    RelatedSpec,
)

_JAVASCRIPT_DECLARATIONS = (re.compile(r"(^|/)package\.json$", re.I),)
_JAVASCRIPT_RESOLUTIONS = (
    re.compile(r"(^|/)(package-lock\.json|yarn\.lock|pnpm-lock\.yaml)$", re.I),
)

REACT_PLUGIN = PackageFrameworkPlugin(
    "react-typescript",
    "javascript",
    (
        PackageFrameworkSpec("react", ("react",)),
        PackageFrameworkSpec("next", ("next",)),
    ),
    related=(
        RelatedSpec("typescript", "language-toolchain", ("typescript",)),
        RelatedSpec("vite", "build-tool", ("vite",)),
    ),
    configuration_patterns=(
        *_JAVASCRIPT_DECLARATIONS,
        *_JAVASCRIPT_RESOLUTIONS,
        re.compile(r"(^|/)tsconfig[^/]*\.json$", re.I),
        re.compile(r"(^|/)(vite|next)\.config\.[^.]+$", re.I),
    ),
)
