"""Pure static .NET manifest boundaries; acquisition belongs to the Git reader."""

from ocr_toolkit.evidence.ecosystems.dotnet.json import parse_global_json, parse_packages_lock
from ocr_toolkit.evidence.ecosystems.dotnet.xml import parse_msbuild

__all__ = ["parse_global_json", "parse_msbuild", "parse_packages_lock"]
