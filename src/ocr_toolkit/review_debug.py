"""Own bounded private diagnostic artifacts without granting review authority."""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import stat
from collections.abc import Iterable
from pathlib import Path
from typing import Literal, get_args

from ocr_toolkit.common.filesystem import fsync_directory
from ocr_toolkit.reporting.model import FailureStage

DEBUG_SCHEMA = "ocr.toolkit-debug/v1"
MAX_DEBUG_JSON_BYTES = 20_000_000
MAX_DEBUG_STDERR_BYTES = 2_000_000
MAX_DEBUG_JOURNAL_BYTES = 1_000_000
MAX_DEBUG_DECISIONS = 1_000
MAX_DEBUG_TRANSITIONS = 128
DebugStatus = Literal["passed", "failed", "degraded", "not-run"]
ArtifactName = Literal["raw-result.json", "raw-stderr.log", "safe-result.json", "summary.md"]
ARTIFACT_LIMITS: dict[ArtifactName, int] = {
    "raw-result.json": MAX_DEBUG_JSON_BYTES,
    "raw-stderr.log": MAX_DEBUG_STDERR_BYTES,
    "safe-result.json": MAX_DEBUG_JSON_BYTES,
    "summary.md": MAX_DEBUG_JSON_BYTES,
}
_SAFE_PATH_FIELDS = frozenset(
    {
        "comments",
        "warnings",
        "message",
        "manifest",
        "coverage",
        "failed",
        "path",
        "reason",
        "content",
        "existing_code",
        "suggestion_code",
        "line",
        "start_line",
        "end_line",
        "severity",
        "category",
        "tool_calls",
        "by_tool",
        "summary",
        "status",
    }
)
_FACT_KEYS = frozenset(
    {
        "base_sha",
        "head_sha",
        "policy_sha",
        "provider",
        "context_mode",
        "output_format",
        "audience",
        "exit_code",
        "record_count",
        "diagnostic_count",
        "tool_count",
        "server_count",
        "summary_completed",
        "dlp_state",
        "used",
        "selected",
        "completed",
        "failure_count",
        "report_artifact",
        "console",
        "reasoning_effort",
        "reasoning_budget",
        "llm_protocol",
        "review_effort",
        "language",
        "llm_model_sha256",
        "extra_body_present",
        "extra_headers_present",
        "telemetry_enabled",
        "content_logging",
    }
)


class DebugBundle:
    """Hold a fresh owner-only directory and observations from real check owners.

    Observations are diagnostic data only. The caller decides execution outcomes;
    no captured result, journal entry or detector observation authorizes admission.
    """

    def __init__(self, directory: Path, *, other_outputs: tuple[Path, ...]) -> None:
        absolute = directory.absolute()
        if any(parent.is_symlink() for parent in (absolute, *absolute.parents)):
            raise ValueError("debug directory must not traverse symlinks")
        resolved = absolute.resolve()
        if any(output.resolve().is_relative_to(resolved) for output in other_outputs):
            raise ValueError("review outputs must be outside the debug directory")
        absolute.mkdir(mode=0o700, parents=True, exist_ok=False)
        self.directory = absolute
        self._descriptor = os.open(absolute, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fchmod(self._descriptor, 0o700)
            self._identity = os.fstat(self._descriptor)
            self._validate_directory()
        except BaseException:
            os.close(self._descriptor)
            self._descriptor = -1
            raise
        self.phases: dict[FailureStage, dict[str, object]] = {
            stage: {"status": "not-run"} for stage in get_args(FailureStage)
        }
        self.artifacts: dict[ArtifactName, dict[str, object]] = {
            name: {"status": "not-run", "limit_bytes": limit}
            for name, limit in ARTIFACT_LIMITS.items()
        }
        self.transitions: list[dict[str, object]] = []
        self.decisions: list[dict[str, object]] = []
        self.omitted_transitions = 0
        self.omitted_decisions = 0

    def _validate_directory(self) -> None:
        current = self.directory.stat(follow_symlinks=False)
        if (
            self._descriptor < 0
            or not os.path.samestat(self._identity, current)
            or not stat.S_ISDIR(current.st_mode)
            or current.st_uid != os.getuid()
            or stat.S_IMODE(current.st_mode) != 0o700
        ):
            raise OSError("debug directory identity or permissions changed")

    def _write(self, name: str, content: bytes) -> None:
        self._validate_directory()
        temporary = ".debug-" + secrets.token_hex(12)
        descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=self._descriptor,
        )
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb") as stream:
                descriptor = -1
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            self._validate_directory()
            os.replace(temporary, name, src_dir_fd=self._descriptor, dst_dir_fd=self._descriptor)
            fsync_directory(self._descriptor)
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            try:
                os.unlink(temporary, dir_fd=self._descriptor)
            except FileNotFoundError:
                pass

    def phase(
        self, stage: FailureStage, status: DebugStatus, *, facts: dict[str, object] | None = None
    ) -> None:
        """Record caller-owned closed facts, never raw exceptions or configuration."""

        if stage not in self.phases or status not in get_args(DebugStatus):
            raise ValueError("unsupported diagnostic phase or status")
        entry: dict[str, object] = {"status": status}
        if facts:
            if set(facts) - _FACT_KEYS or any(
                not (
                    isinstance(value, bool)
                    or (isinstance(value, int) and -1_000_000_000_000 <= value <= 1_000_000_000_000)
                    or (isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_ ()-]{1,64}", value))
                )
                for value in facts.values()
            ):
                raise ValueError("debug facts must use bounded closed fields")
            entry["facts"] = facts.copy()
        self.phases[stage] = entry
        if len(self.transitions) < MAX_DEBUG_TRANSITIONS:
            self.transitions.append({"stage": stage, "status": status})
        else:
            self.omitted_transitions += 1

    def decision(
        self,
        *,
        path: tuple[object, ...],
        action: str,
        reason: str,
        detector: str | None,
        value: object,
    ) -> None:
        """Record a real DLP branch with a value-free correlation fingerprint."""

        if len(self.decisions) >= MAX_DEBUG_DECISIONS:
            self.omitted_decisions += 1
            return
        if any(
            not isinstance(label, str) or re.fullmatch(r"[A-Za-z0-9_:-]{1,64}", label) is None
            for label in (action, reason, detector or "none")
        ):
            raise ValueError("debug decision labels must be closed identifiers")
        safe_path: list[str | int] = []
        for part in path[:16]:
            if (isinstance(part, int) and not isinstance(part, bool)) or (
                isinstance(part, str) and part in _SAFE_PATH_FIELDS
            ):
                safe_path.append(part)
            else:
                encoded_key = str(part).encode("utf-8", errors="backslashreplace")
                safe_path.append("field-" + hashlib.sha256(encoded_key).hexdigest()[:16])
        entry: dict[str, object] = {
            "path": safe_path,
            "path_truncated": len(path) > 16,
            "action": action,
            "reason": reason,
            "detector": detector,
        }
        if isinstance(value, str):
            encoded = value.encode("utf-8", errors="backslashreplace")
            entry.update(
                {
                    "value_type": "string",
                    "characters": len(value),
                    "bytes": len(encoded),
                    "lines": value.count("\n") + 1,
                    "sha256": hashlib.sha256(encoded).hexdigest(),
                }
            )
        else:
            entry["value_type"] = "non-string"
        self.decisions.append(entry)

    def capture(self, name: ArtifactName, source: Path) -> None:
        """Copy a bounded prefix of one regular artifact without following links."""

        limit = ARTIFACT_LIMITS[name]
        descriptor = -1
        source_opened = False
        try:
            descriptor = os.open(source, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            source_opened = True
            before = os.fstat(descriptor)
            if (
                not stat.S_ISREG(before.st_mode)
                or before.st_nlink != 1
                or before.st_uid != os.getuid()
            ):
                raise OSError("unsafe debug capture source")
            with os.fdopen(descriptor, "rb") as stream:
                descriptor = -1
                data = stream.read(limit + 1)
                after = os.fstat(stream.fileno())
            prefix = data[:limit]
            truncated = len(data) > limit
            changed = (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns)
            self._write(name, prefix)
            self.artifacts[name] = {
                "status": "degraded" if truncated or changed else "passed",
                "limit_bytes": limit,
                "captured_bytes": len(prefix),
                "source_bytes_observed": before.st_size,
                "sha256_captured": hashlib.sha256(prefix).hexdigest(),
                "truncated": truncated,
                "source_changed": changed,
            }
        except FileNotFoundError:
            self.artifacts[name] = {
                "status": "unavailable" if source_opened else "missing",
                "limit_bytes": limit,
            }
        except OSError:
            self.artifacts[name] = {"status": "unavailable", "limit_bytes": limit}
        finally:
            if descriptor >= 0:
                os.close(descriptor)

    def flush(self, *, complete: bool = False) -> None:
        """Atomically persist one bounded journal; raw content is never embedded."""

        document = {
            "schema_version": DEBUG_SCHEMA,
            "complete": complete,
            "phases": self.phases,
            "artifacts": self.artifacts,
            "transitions": self.transitions,
            "omitted_transitions": self.omitted_transitions,
            "dlp_decisions": self.decisions,
            "omitted_decisions": self.omitted_decisions,
        }
        content = json.dumps(document, sort_keys=True, ensure_ascii=True).encode("utf-8")
        if len(content) > MAX_DEBUG_JOURNAL_BYTES:
            raise ValueError("debug journal exceeds its byte limit")
        self._write("journal.json", content)

    def capture_parts(self, name: ArtifactName, parts: Iterable[str]) -> None:
        """Retain a bounded rendered summary even when normal delivery is unavailable."""

        limit = ARTIFACT_LIMITS[name]
        data = bytearray()
        for part in parts:
            data.extend(part.encode("utf-8")[: limit + 1 - len(data)])
            if len(data) > limit:
                break
        truncated = len(data) > limit
        prefix = bytes(data[:limit])
        try:
            self._write(name, prefix)
        except OSError:
            self.artifacts[name] = {"status": "unavailable", "limit_bytes": limit}
            return
        self.artifacts[name] = {
            "status": "degraded" if truncated else "passed",
            "limit_bytes": limit,
            "captured_bytes": len(prefix),
            "source_bytes_observed": None if truncated else len(prefix),
            "sha256_captured": hashlib.sha256(prefix).hexdigest(),
            "truncated": truncated,
            "source_changed": False,
        }

    def close(self) -> None:
        """Release the pinned directory descriptor exactly once."""

        if self._descriptor >= 0:
            os.close(self._descriptor)
            self._descriptor = -1
