"""Read a bounded, run-bound projection of native OCR task and tool records."""

from __future__ import annotations

import json
import os
import re
import stat
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO

from ocr_toolkit.common.filesystem import same_file_identity
from ocr_toolkit.review_range import ReviewRange

TRACE_SCHEMA = "ocr.native-trace/v1"
MAX_TRACE_BYTES = 20_000_000
MAX_SOURCE_BYTES = 32_000_000
MAX_RECORD_BYTES = 4_000_000
MAX_RECORDS = 10_000
MAX_DIRECTORY_ENTRIES = 8
_UUID = re.compile(r"[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}")
_TASKS = frozenset(
    {
        "grouping_task",
        "plan_task",
        "main_task",
        "review_filter_task",
        "re_location_task",
        "memory_compression_task",
    }
)
_ROLES = frozenset({"system", "user", "assistant", "tool", "developer"})


class NativeTraceError(ValueError):
    """The native trace cannot be bound or safely projected."""


@dataclass(frozen=True, slots=True)
class TraceCapture:
    """Keep projected bytes and value-free capture completeness separate."""

    content: bytes
    facts: dict[str, object]


def _unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise NativeTraceError("duplicate native record field")
        result[key] = value
    return result


def _invalid_constant(_value: str) -> None:
    raise NativeTraceError("non-finite native record")


def _private(metadata: os.stat_result, *, directory: bool) -> None:
    valid_type = stat.S_ISDIR(metadata.st_mode) if directory else stat.S_ISREG(metadata.st_mode)
    if (
        not valid_type
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) & 0o077
        or (not directory and metadata.st_nlink != 1)
    ):
        raise NativeTraceError("unsafe native trace source")


def _calls(value: object, *, response: bool = False) -> list[dict[str, object]]:
    """Drop opaque provider replay/extensions; keep public tool arguments."""

    if value is None:
        return []
    if not isinstance(value, list) or len(value) > 128:
        raise NativeTraceError("invalid native tool call list")
    result = []
    for call in value:
        if not isinstance(call, dict):
            raise NativeTraceError("invalid native tool call")
        # OCR persists response calls flattened, unlike calls inside messages.
        function = call if response else call.get("function")
        if (
            not isinstance(function, dict)
            or not isinstance(call.get("id"), str)
            or any(not isinstance(function.get(key), str) for key in ("name", "arguments"))
        ):
            raise NativeTraceError("invalid native tool call fields")
        if not response and call.get("type") != "function":
            raise NativeTraceError("unsupported native tool call type")
        result.append(
            {
                "id": call["id"],
                "type": "function",
                "function": {"name": function["name"], "arguments": function["arguments"]},
            }
        )
    return result


def _messages(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list) or len(value) > 2_048:
        raise NativeTraceError("invalid native message list")
    result = []
    for message in value:
        if (
            not isinstance(message, dict)
            or not isinstance(message.get("role"), str)
            or message["role"] not in _ROLES
        ):
            raise NativeTraceError("invalid native message")
        content = message.get("content")
        if content is not None and not isinstance(content, str):
            # The qualified text-review path uses text messages. Do not copy
            # image URLs, provider-specific objects or unknown replay formats.
            raise NativeTraceError("unsupported native message content")
        item: dict[str, object] = {"role": message["role"], "content": content}
        if "tool_call_id" in message:
            if not isinstance(message["tool_call_id"], str):
                raise NativeTraceError("invalid native tool response identity")
            item["tool_call_id"] = message["tool_call_id"]
        if "tool_calls" in message:
            item["tool_calls"] = _calls(message["tool_calls"])
        result.append(item)
    return result


def project_record(value: dict[str, Any]) -> dict[str, object] | None:
    """Select diagnostic task fields without config, credentials or reasoning payloads."""

    kind = value.get("type")
    if not isinstance(kind, str):
        raise NativeTraceError("invalid native record type")
    if any(not isinstance(value.get(key), str) for key in ("sessionId", "uuid", "timestamp")):
        raise NativeTraceError("invalid native record identity")
    common = ("type", "sessionId", "uuid", "parentUuid", "timestamp")
    result: dict[str, object] = {key: value[key] for key in common if key in value}
    if kind == "session_start":
        if any(
            not isinstance(value.get(key), str)
            for key in ("reviewMode", "diffFrom", "diffTo", "model")
        ):
            raise NativeTraceError("invalid native session header")
        result.update(
            {
                key: value[key]
                for key in ("reviewMode", "diffFrom", "diffTo", "model")
                if key in value
            }
        )
        result["schema_version"] = TRACE_SCHEMA
        return result
    if kind in {"llm_request", "llm_response", "llm_error", "tool_call"}:
        if (
            not isinstance(value.get("taskType"), str)
            or value["taskType"] not in _TASKS
            or not isinstance(value.get("filePath"), str)
        ):
            raise NativeTraceError("invalid native task identity")
        result.update(filePath=value["filePath"], taskType=value["taskType"])
        if kind in {"llm_request", "llm_error"}:
            if type(value.get("request_no")) is not int or value["request_no"] < 0:
                raise NativeTraceError("invalid native request number")
            result["request_no"] = value["request_no"]
            if kind == "llm_request":
                result["messages"] = _messages(value.get("messages"))
            elif not isinstance(value.get("error"), str):
                raise NativeTraceError("invalid native task error")
            else:
                result["error"] = value["error"]
        elif kind == "llm_response":
            if not isinstance(value.get("content"), str):
                raise NativeTraceError("invalid native response text")
            result.update(
                content=value["content"], tool_calls=_calls(value.get("tool_calls"), response=True)
            )
        else:
            if (
                any(
                    not isinstance(value.get(key), str)
                    for key in ("tool_name", "arguments", "result")
                )
                or type(value.get("ok")) is not bool
            ):
                raise NativeTraceError("invalid native tool result")
            result.update({key: value[key] for key in ("tool_name", "arguments", "result", "ok")})
        return result
    if kind == "session_end":
        paths = value.get("files_reviewed")
        if not isinstance(paths, list) or any(not isinstance(path, str) for path in paths):
            raise NativeTraceError("invalid native completion paths")
        if type(value.get("llm_failures")) is not int or value["llm_failures"] < 0:
            raise NativeTraceError("invalid native failure count")
        result.update(files_reviewed=paths, llm_failures=value["llm_failures"])
        return result
    if kind in {"review_item_done", "review_item_failed", "review_item_reused"}:
        for key in ("filePath", "oldPath", "newPath", "fingerprint", "error"):
            if key in value:
                if not isinstance(value[key], str):
                    raise NativeTraceError("invalid native file checkpoint")
                result[key] = value[key]
        return result
    return None


class NativeTraceSource:
    """Pin only this run's private HOME; never search the user's native registration."""

    def __init__(self, home: Path, repository: Path, review_range: ReviewRange) -> None:
        self._descriptor = -1
        self.repository = str(repository.resolve(strict=True))
        self.review_range = review_range
        descriptor = os.open(home, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            _private(os.fstat(descriptor), directory=True)
        except BaseException:
            os.close(descriptor)
            raise
        self._descriptor = descriptor

    def close(self) -> None:
        if self._descriptor >= 0:
            os.close(self._descriptor)
            self._descriptor = -1

    def capture(self, *, max_output_bytes: int = MAX_TRACE_BYTES) -> TraceCapture:
        """Read one unambiguous native session with hard input/output/record caps."""

        if self._descriptor < 0:
            raise NativeTraceError("native trace source is closed")
        if not 1 <= max_output_bytes <= MAX_TRACE_BYTES:
            raise NativeTraceError("invalid native trace output bound")
        with ExitStack() as stack:
            parent = self._descriptor
            encoded = self.repository.lstrip("/\\").replace("/", "-").replace("\\", "-")
            for part in (".opencodereview", "sessions", encoded):
                descriptor = os.open(
                    part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent
                )
                stack.callback(os.close, descriptor)
                _private(os.fstat(descriptor), directory=True)
                parent = descriptor
            names = []
            with os.scandir(parent) as entries:
                for index, entry in enumerate(entries):
                    if index >= MAX_DIRECTORY_ENTRIES:
                        raise NativeTraceError("native session inventory exceeds its bound")
                    if entry.name.endswith(".jsonl") and _UUID.fullmatch(entry.name[:-6]):
                        names.append(entry.name)
                        if len(names) > 1:
                            raise NativeTraceError("native session identity is ambiguous")
            if not names:
                raise FileNotFoundError("native session is unavailable")
            descriptor = os.open(
                names[0], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent
            )
            with os.fdopen(descriptor, "rb") as stream:
                before = os.fstat(stream.fileno())
                _private(before, directory=False)
                capture = self._project(stream, names[0][:-6], max_output_bytes)
                after = os.fstat(stream.fileno())
                _private(after, directory=False)
                named = os.stat(names[0], dir_fd=parent, follow_symlinks=False)
                changed = not same_file_identity(before, named) or (
                    before.st_size,
                    before.st_mtime_ns,
                ) != (after.st_size, after.st_mtime_ns)
                facts = {
                    **capture.facts,
                    "source_bytes_observed": before.st_size,
                    "source_changed": changed,
                }
                if changed:
                    facts["status"] = "degraded"
                return TraceCapture(capture.content, facts)

    def _project(self, stream: BinaryIO, session_id: str, max_output_bytes: int) -> TraceCapture:
        output = bytearray()
        read_bytes = records = retained = 0
        ended = complete = truncated = False
        previous: str | None = None
        identifiers: set[str] = set()
        while records < MAX_RECORDS:
            remaining = MAX_SOURCE_BYTES - read_bytes
            if remaining <= 0:
                truncated = True
                break
            line = stream.readline(min(MAX_RECORD_BYTES, remaining) + 1)
            if not line:
                break
            read_bytes += len(line)
            if len(line) > MAX_RECORD_BYTES or read_bytes > MAX_SOURCE_BYTES:
                truncated = True
                break
            if not line.endswith(b"\n"):
                truncated = True
            records += 1
            try:
                value = json.loads(
                    line.decode("utf-8"),
                    object_pairs_hook=_unique,
                    parse_constant=_invalid_constant,
                )
            except (ValueError, UnicodeError, RecursionError) as exc:
                if records == 1:
                    raise NativeTraceError("native trace header is unavailable") from exc
                break
            if not isinstance(value, dict) or value.get("sessionId") != session_id:
                raise NativeTraceError("native record belongs to another run")
            if records == 1:
                if (
                    value.get("type"),
                    value.get("reviewMode"),
                    value.get("diffFrom"),
                    value.get("diffTo"),
                    value.get("cwd"),
                ) != (
                    "session_start",
                    "range",
                    self.review_range.base,
                    self.review_range.head,
                    self.repository,
                ):
                    raise NativeTraceError("native session is not bound to the requested range")
            elif value.get("type") == "session_start" or ended:
                raise NativeTraceError("native session ordering is invalid")
            identifier = value.get("uuid")
            if (
                not isinstance(identifier, str)
                or _UUID.fullmatch(identifier) is None
                or identifier in identifiers
                or value.get("parentUuid") != previous
            ):
                raise NativeTraceError("native session record chain is invalid")
            previous = identifier
            identifiers.add(identifier)
            ended = value.get("type") == "session_end"
            try:
                projected = project_record(value)
                if projected is None:
                    continue
                encoded = (
                    json.dumps(
                        projected, ensure_ascii=False, separators=(",", ":"), allow_nan=False
                    ).encode("utf-8")
                    + b"\n"
                )
            except (ValueError, TypeError, UnicodeError, RecursionError):
                if records == 1:
                    raise NativeTraceError("native trace header cannot be projected") from None
                continue
            if len(output) + len(encoded) > max_output_bytes:
                truncated = True
                break
            output.extend(encoded)
            retained += 1
            complete = ended
        if records == MAX_RECORDS and stream.read(1):
            truncated = True
        return TraceCapture(
            bytes(output),
            {
                "status": "passed"
                if complete and not truncated and records == retained
                else "degraded",
                "records_observed": records,
                "records_retained": retained,
                "records_omitted": records - retained,
                "session_complete": complete,
                "truncated": truncated,
            },
        )
