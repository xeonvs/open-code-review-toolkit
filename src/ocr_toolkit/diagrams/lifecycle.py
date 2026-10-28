"""Isolate optional diagram preparation, snapshot and admission failures."""

from __future__ import annotations

import secrets
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ocr_toolkit.context.dlp import ForbiddenMatcher
from ocr_toolkit.diagrams.admission import admit_diagram
from ocr_toolkit.diagrams.collector import CollectorSnapshot, DiagramCollector
from ocr_toolkit.diagrams.contracts import DiagramMode, DiagramResult, diagram_requested
from ocr_toolkit.diagrams.persistence import diagram_payload, parse_diagram_payload
from ocr_toolkit.review_range import ReviewRange


def diagram_warning() -> None:
    """Log a closed notice without rejected content or exception details."""

    try:
        print("OCR diagram unavailable or invalid; review continues without it.", file=sys.stderr)
    except Exception:
        pass


@dataclass(slots=True)
class DiagramExecution:
    """Hold only optional-channel state; the runner owns the overall review."""

    result: DiagramResult
    collector: DiagramCollector | None = None
    snapshot: CollectorSnapshot | None = None

    @classmethod
    def prepare(
        cls,
        mode: DiagramMode,
        *,
        local: bool,
        native_version: str | None,
        review_range: ReviewRange,
        path: Path,
    ) -> DiagramExecution:
        if not diagram_requested(mode, local=local):
            return cls(DiagramResult(mode, "disabled"))
        if native_version != "1.13.3":
            return cls(DiagramResult(mode, "unsupported"))
        execution = cls(DiagramResult(mode, "not-generated"))
        try:
            execution.collector = DiagramCollector(path, secrets.token_hex(16), review_range)
            execution.collector.initialize()
        except Exception:
            execution.collector = None
            execution.result = DiagramResult(mode, "omitted-invalid", "unavailable")
            diagram_warning()
        return execution

    def capture(self) -> None:
        """Read the closed snapshot before the runner cleans the session."""

        if self.collector is None:
            return
        try:
            self.snapshot = self.collector.read()
        except Exception:
            self.snapshot = None
            diagram_warning()

    def unavailable(self) -> None:
        """Disable unavailable output registration while preserving review work."""

        self.collector = None
        self.snapshot = None
        self.result = DiagramResult(self.result.mode, "omitted-invalid", "unavailable")
        diagram_warning()

    def finish(
        self,
        *,
        review_range: ReviewRange | None,
        calls: int,
        failed_calls: int,
        read_source: Callable[[str], str | None],
        forbidden_matcher: ForbiddenMatcher,
        dlp_enabled: bool,
    ) -> DiagramResult:
        if self.collector is None:
            return self.result
        try:
            result = admit_diagram(
                self.result.mode,
                self.snapshot,
                review_range=review_range,
                output_calls=calls,
                read_source=read_source,
                forbidden_matcher=forbidden_matcher,
                dlp_enabled=dlp_enabled,
            )
            if failed_calls:
                result = DiagramResult(
                    result.mode,
                    "omitted-invalid",
                    "unavailable",
                    calls=calls,
                    failed_calls=failed_calls,
                )
            parse_diagram_payload(
                diagram_payload(result), review_range=review_range, local=result.mode == "local"
            )
        except Exception:
            result = DiagramResult(
                self.result.mode,
                "omitted-invalid",
                "unavailable",
                calls=calls,
                failed_calls=failed_calls,
            )
        self.result = result
        if result.state in {"omitted-invalid", "not-generated", "unsupported"}:
            diagram_warning()
        return result
