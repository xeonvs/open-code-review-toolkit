"""Internal isolated worker entry point; public operations use ocr-ci dlp-audit."""

import sys

from .scanner import worker

if __name__ == "__main__":
    raise SystemExit(worker() if sys.argv[1:] == ["--worker"] else 2)
