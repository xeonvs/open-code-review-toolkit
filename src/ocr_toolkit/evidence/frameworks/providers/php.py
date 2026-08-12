"""Package-owned Symfony and Twig provider declaration."""

from __future__ import annotations

import re

from ocr_toolkit.evidence.frameworks.detection import PackageFrameworkPlugin, PackageFrameworkSpec

_COMPOSER_DECLARATIONS = (re.compile(r"(^|/)composer\.json$", re.I),)
_COMPOSER_RESOLUTIONS = (re.compile(r"(^|/)composer\.lock$", re.I),)

SYMFONY_PLUGIN = PackageFrameworkPlugin(
    "symfony-php",
    "php",
    (
        PackageFrameworkSpec("symfony", ("symfony/framework-bundle", "symfony/symfony")),
        PackageFrameworkSpec("twig", ("twig/twig", "symfony/twig-bundle"), "template-engine"),
    ),
    configuration_patterns=(
        *_COMPOSER_DECLARATIONS,
        *_COMPOSER_RESOLUTIONS,
        re.compile(r"(^|/)config/(bundles\.php|packages/|routes(?:\.|/|$))", re.I),
        re.compile(r"\.twig$", re.I),
    ),
)
