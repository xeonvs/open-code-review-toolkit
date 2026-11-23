"""Parse normalized, content-free telemetry from OCR GitLab publications."""

from .summary import parse_publication

__all__ = ["parse_publication"]
