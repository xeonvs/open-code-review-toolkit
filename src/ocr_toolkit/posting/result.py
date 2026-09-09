"""Posting facade for shared OCR result diagnostics."""

from ocr_toolkit.reporting.result import (
    CoverageDiagnostic,
    CoverageDiagnostics,
    OcrResultMalformed,
    OcrResultMissing,
    OcrResultTooLarge,
    llm_billing_failure_reason,
    load_ocr_result,
    normalize_coverage_diagnostics,
    ocr_warning_text,
)

__all__ = [
    "CoverageDiagnostic",
    "CoverageDiagnostics",
    "OcrResultMalformed",
    "OcrResultMissing",
    "OcrResultTooLarge",
    "llm_billing_failure_reason",
    "load_ocr_result",
    "normalize_coverage_diagnostics",
    "ocr_warning_text",
]
