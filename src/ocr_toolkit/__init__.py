"""Open Code Review CI helper package and centralized runtime metadata."""

try:
    from ocr_toolkit._version import __version__
except ModuleNotFoundError:
    # Hatch-vcs creates ``_version.py`` for editable/build installs. A raw source
    # checkout must remain importable without introducing another release version.
    __version__ = "0+unknown"

__all__ = ["__version__"]
