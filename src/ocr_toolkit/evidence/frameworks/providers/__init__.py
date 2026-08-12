"""Package-owned built-in framework provider declarations."""

from ocr_toolkit.evidence.frameworks.providers.frontend import REACT_PLUGIN
from ocr_toolkit.evidence.frameworks.providers.go import GO_WEB_PLUGIN
from ocr_toolkit.evidence.frameworks.providers.php import SYMFONY_PLUGIN
from ocr_toolkit.evidence.frameworks.providers.python import JINJA2_PLUGIN

__all__ = ["GO_WEB_PLUGIN", "JINJA2_PLUGIN", "REACT_PLUGIN", "SYMFONY_PLUGIN"]
