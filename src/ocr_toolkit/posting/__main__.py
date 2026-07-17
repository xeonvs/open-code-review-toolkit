"""CLI entrypoint for posting OCR results to GitLab."""

from __future__ import annotations

from ocr_toolkit.posting.workflow import main

if __name__ == "__main__":
    raise SystemExit(main())
