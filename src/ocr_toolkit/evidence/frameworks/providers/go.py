"""Package-owned Go web framework provider declaration."""

from __future__ import annotations

import re

from ocr_toolkit.evidence.frameworks.detection import (
    PackageFrameworkPlugin,
    PackageFrameworkSpec,
    RelatedSpec,
)

GO_WEB_PLUGIN = PackageFrameworkPlugin(
    "go-web",
    "go",
    (
        PackageFrameworkSpec("echo", ("github.com/labstack/echo/v4",)),
        PackageFrameworkSpec("fiber", ("github.com/gofiber/fiber/v2",)),
    ),
    related=(RelatedSpec("grpc", "rpc-stack", ("google.golang.org/grpc",)),),
    configuration_patterns=(re.compile(r"(^|/)go\.(mod|sum)$", re.I),),
)
