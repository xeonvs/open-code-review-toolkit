"""Production DLP evaluation in a bounded isolated worker, without target imports."""

from __future__ import annotations

import hashlib
import hmac
import importlib.metadata
import os
import resource
import sys
import time
import unicodedata
import uuid
from pathlib import Path
from typing import Any

from ocr_toolkit.common import redaction
from ocr_toolkit.context import dlp
from ocr_toolkit.context.code_text import TextSink
from ocr_toolkit.context.contracts import TextBudgets
from ocr_toolkit.evidence.opaque_code import SyntaxCache, prove_opaque_code

from .corpus import MAX_FILE, manifest, original_source, read_source, verify_originals
from .limits import MAX_HIT_BYTES, MAX_HITS, ExecutionLimits
from .report import render_report
from .state import DIGEST, MAX_DOCUMENT, AuditError, State, decode, encode, fields
from .worker_process import WorkerFailure, WorkerSession, frame, read_request

PROFILE = "raw-publication+existing-code/1"
ROLES = frozenset({"text", "existing_code"})
REASONS = frozenset({"invalid_text", "limit", "secret", "pii", "laundering", "forbidden"})
FAILURES = frozenset(
    {
        "unsupported_input",
        "scan_deadline",
        "worker_unavailable",
        "worker_timeout",
        "worker_failed",
        "worker_launch",
        "worker_memory",
        "output_budget",
    }
)


class ScanFailure(AuditError):
    """A closed operational diagnosis, never inferred from source or exit text."""

    def __init__(self, reason: str) -> None:
        if reason not in FAILURES:
            raise AuditError("invalid worker failure")
        self.reason = reason
        super().__init__(reason)


def hit_bytes(hit: dict[str, Any]) -> int:
    return len(encode(hit)) + 1


def append_hit(hits: list[dict[str, Any]], hit: dict[str, Any], used: int) -> int:
    """Limit retained records while generating them, before aggregate serialization."""

    size = hit_bytes(hit)
    if len(hits) >= MAX_HITS or used + size > MAX_HIT_BYTES:
        raise ScanFailure("output_budget")
    hits.append(hit)
    return used + size


def mac(key: bytes, *parts: object) -> str:
    """Use the state owner's canonical keyed identity in the isolated worker."""

    return hmac.new(key, encode(parts), hashlib.sha256).hexdigest()


def secret_fingerprint(state: State) -> str:
    """Bind the effective known-secret set without retaining names or raw values."""

    names = set(redaction.SENSITIVE_ENV_NAMES)
    names.update(
        name
        for name, value in os.environ.items()
        if len(value.strip()) >= redaction.MIN_DISCOVERED_SECRET_LENGTH
        and redaction.SECRET_SHAPED_ENV_NAME_RE.search(name)
    )
    return state.mac(
        "secret-set",
        sorted({os.environ[name] for name in names if len(os.environ.get(name, "")) >= 4}),
    )


def scanner_identity() -> str:
    """Identify the actual installed scanner and projection owners, including edits."""

    import ocr_toolkit

    digest = hashlib.sha256()
    digest.update(importlib.metadata.version("open-code-review-toolkit").encode())
    # Static Unicode/grammar data changes detector decisions even when toolkit
    # sources are unchanged. Keep the existing opaque identity/schema, binding
    # all selected interpretation owners and the interpreter Unicode tables.
    for dependency in ("mistune", "regex", "emoji"):
        digest.update(encode((dependency, importlib.metadata.version(dependency))))
    digest.update(encode((sys.implementation.cache_tag, unicodedata.unidata_version)))
    root = Path(ocr_toolkit.__file__).parent
    for path in sorted(root.rglob("*.py")):
        digest.update(str(path.relative_to(root)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _unit_id(key: bytes, corpus: str, item: dict[str, Any], unit: int, role: str) -> str:
    return mac(key, corpus, item["path"], item["digest"], unit, role, PROFILE)


def evaluate(request: dict[str, Any], *, worker_identity: str | None = None) -> dict[str, Any]:
    """Evaluate every whole-file/nonempty-line unit with the production owners."""

    fields(request, {"key", "corpus", "item", "source", "scanner"})
    expected_identity = scanner_identity() if worker_identity is None else worker_identity
    if request["scanner"] != expected_identity:
        raise AuditError("worker scanner identity changed")
    key = bytes.fromhex(request["key"])
    item = request["item"]
    text = request["source"]
    if len(key) != 32 or not isinstance(text, str) or len(text.encode()) > MAX_FILE:
        raise AuditError("invalid worker request")
    budgets = TextBudgets(max_chars=2_000_000, max_bytes=8_000_000, max_lines=100_000)
    lines = text.splitlines()
    units = [
        (0, text),
        *((number, line) for number, line in enumerate(lines, 1) if line.strip()),
    ]
    if len(units) != item["units"]:
        raise AuditError("worker unit population changed")
    hits: list[dict[str, Any]] = []
    used = 0
    proven = 0
    syntax_cache: SyntaxCache = {}
    with dlp.dlp_mode(True):
        for number, value in units:
            raw = dlp.check_text(
                value, budgets=budgets, publication=True, allow_horizontal_tabs=False, enabled=True
            )
            literal = dlp.check_text(
                value,
                budgets=budgets,
                publication=True,
                allow_horizontal_tabs=True,
                sink=TextSink.LITERAL_CODE,
                enabled=True,
            )
            if raw.admitted and literal.admitted:
                # Both sinks were actually checked. Source proof can only relax
                # these checks; no inference from prose to literal code is valid.
                continue
            comment = {
                "path": item["path"],
                "start_line": number or 1,
                "end_line": number or len(lines),
                "content": "",
                "existing_code": value,
            }
            proof = prove_opaque_code(
                comment, item["path"], lambda _path: text, syntax_cache=syntax_cache
            )
            proven += int(proof.existing_verified)
            checked = dlp.check_text(
                value,
                budgets=budgets,
                publication=True,
                allow_horizontal_tabs=True,
                allow_opaque_code=proof.existing_verified,
                code_context=proof.existing_context,
                sink=TextSink.LITERAL_CODE,
                enabled=True,
            )
            from ocr_toolkit import review_runner

            projected, _publication, _filtered = review_runner._publication_projection(
                {"status": "success", "warnings": [], "comments": [comment]},
                forbidden=(),
                allowed_tools=frozenset(),
                code_proof=lambda _comment: proof,
            )
            retained = projected.get("comments", [])
            admitted_code = bool(retained and "existing_code" in retained[0])
            if admitted_code != checked.admitted:
                raise AuditError("code admission and projection disagree")
            for role, decision in (("text", raw), ("existing_code", checked)):
                if not decision.admitted:
                    used = append_hit(
                        hits,
                        {
                            "id": _unit_id(key, request["corpus"], item, number, role),
                            "slot": item["slot"],
                            "unit": number,
                            "role": role,
                            "reason": decision.reason,
                            "detector": decision.detector,
                            "proof": proof.existing_verified,
                        },
                        used,
                    )
    return {"units": len(units), "proven_rejections": proven, "hits": hits}


def _worker_response(raw_request: bytes, *, worker_identity: str | None = None) -> bytes:
    """Keep all source-bearing locals within one request's stack frame."""

    try:
        result = evaluate(decode(raw_request), worker_identity=worker_identity)
        raw = encode(result)
        if len(raw) > MAX_DOCUMENT:
            raise AuditError("worker output limit")
    except (ScanFailure, MemoryError) as exc:
        reason = exc.reason if isinstance(exc, ScanFailure) else "worker_memory"
        raw = encode({"error": reason})
    return raw


def worker() -> int:
    """Process bounded independent frames without retaining source across files."""

    try:
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_DOCUMENT, MAX_DOCUMENT))
        identity = scanner_identity()
        while (raw_request := read_request(sys.stdin.buffer)) is not None:
            if len(raw_request) < 17:
                raise AuditError("missing worker request identity")
            sys.stdout.buffer.write(
                frame(
                    raw_request[:16] + _worker_response(raw_request[16:], worker_identity=identity)
                )
            )
            sys.stdout.buffer.flush()
            del raw_request
        return 0
    except Exception:
        return 2


def supervised(
    request: dict[str, Any],
    timeout: float,
    *,
    worker: WorkerSession | None = None,
) -> dict[str, Any]:
    """Exchange one file atomically, reusing only this scan's trusted peer."""

    owner = worker or WorkerSession()
    try:
        result = decode(owner.exchange(encode(request), timeout))
        if isinstance(result, dict) and set(result) == {"error"}:
            raise ScanFailure(result["error"])
        return fields(result, {"units", "proven_rejections", "hits"})
    except WorkerFailure as exc:
        owner.close()
        raise ScanFailure(exc.reason) from exc
    except BaseException:
        owner.close()
        raise
    finally:
        if worker is None:
            owner.close()


def validate_hits(value: Any, *, files: list[dict[str, Any]], units: int) -> list[dict[str, Any]]:
    """Admit only closed, unique and bounded rejection records."""

    if not isinstance(value, list) or len(value) > min(MAX_HITS, 2 * units):
        raise AuditError("invalid hit population")
    known = {item["slot"]: item for item in files}
    identities: set[str] = set()
    used = 0
    for item in value:
        fields(item, {"id", "slot", "unit", "role", "reason", "detector", "proof"})
        if (
            not isinstance(item["id"], str)
            or DIGEST.fullmatch(item["id"]) is None
            or item["id"] in identities
            or item["slot"] not in known
            or type(item["unit"]) is not int
            or not 0 <= item["unit"] <= known[item["slot"]]["lines"]
            or item["role"] not in ROLES
            or item["reason"] not in REASONS
            or not isinstance(item["detector"], str)
            or len(item["detector"]) > 80
            or any(char not in "abcdefghijklmnopqrstuvwxyz_:-" for char in item["detector"])
            or type(item["proof"]) is not bool
        ):
            raise AuditError("invalid rejection record")
        identities.add(item["id"])
        used += hit_bytes(item)
        if used > MAX_HIT_BYTES:
            raise AuditError("invalid rejection byte population")
    return value


def scan(
    state: State,
    corpus_id: str,
    *,
    deadline: float,
    limits: ExecutionLimits | None = None,
) -> tuple[str, dict[str, Any]]:
    """Evaluate one file at a time; capped files never contribute partial passes."""

    limits = limits or ExecutionLimits()
    corpus = manifest(state, corpus_id)
    if corpus["raw_removed"] and corpus["storage"] == "snapshot":
        raise AuditError("raw snapshot was already removed")
    secret_set = secret_fingerprint(state)
    scanner = scanner_identity()
    raw_fd = state.raw_directory(corpus_id) if corpus["storage"] == "snapshot" else -1
    hits: list[dict[str, Any]] = []
    errors = []
    evaluated = proven = used = 0
    stopped: str | None = None
    worker_owner = WorkerSession()
    try:
        if raw_fd < 0:
            verify_originals(state, corpus, deadline=deadline)
        for item in corpus["files"]:
            if item["error"] is not None:
                errors.append({"slot": item["slot"], "reason": "unsupported_input"})
                continue
            if stopped or time.monotonic() >= deadline:
                errors.append({"slot": item["slot"], "reason": stopped or "scan_deadline"})
                continue
            # Do not queue or retain another file's source while a worker is running.
            raw = (
                read_source(state, raw_fd, item)
                if raw_fd >= 0
                else original_source(state, corpus, item)
            )
            request = {
                "key": state.key.hex(),
                "corpus": corpus_id,
                "item": item,
                "source": raw.decode(),
                "scanner": scanner,
            }
            del raw
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                errors.append({"slot": item["slot"], "reason": "scan_deadline"})
                continue
            try:
                result = supervised(
                    request, min(limits.file_seconds, remaining), worker=worker_owner
                )
            except AuditError as exc:
                reason = exc.reason if isinstance(exc, ScanFailure) else "worker_unavailable"
                errors.append({"slot": item["slot"], "reason": reason})
                continue
            finally:
                del request
            if type(result["units"]) is not int or result["units"] != item["units"]:
                raise AuditError("worker returned incomplete population")
            if (
                type(result["proven_rejections"]) is not int
                or not 0 <= result["proven_rejections"] <= result["units"]
            ):
                raise AuditError("invalid worker proof count")
            admitted_hits = validate_hits(result["hits"], files=[item], units=item["units"])
            size = sum(hit_bytes(hit) for hit in admitted_hits)
            if len(hits) + len(admitted_hits) > MAX_HITS or used + size > MAX_HIT_BYTES:
                stopped = "output_budget"
                errors.append({"slot": item["slot"], "reason": stopped})
                continue
            for hit in admitted_hits:
                if hit["id"] != _unit_id(state.key, corpus_id, item, hit["unit"], hit["role"]):
                    raise AuditError("worker returned an unbound rejection identity")
            hits.extend(admitted_hits)
            used += size
            evaluated += result["units"]
            proven += result["proven_rejections"]
        if raw_fd < 0:
            verify_originals(state, corpus, deadline=deadline)
    finally:
        worker_owner.close()
        if raw_fd >= 0:
            os.close(raw_fd)
    if secret_set != secret_fingerprint(state) or scanner != scanner_identity():
        raise AuditError("scanner configuration changed during evaluation")
    run = {
        "corpus": corpus_id,
        "scanner": scanner,
        "profile": PROFILE,
        "secret_set": secret_set,
        "units": evaluated,
        "expected_units": corpus["units"],
        "execution": limits.record(),
        "proven_rejections": proven,
        "complete": not errors and evaluated == corpus["units"],
        "errors": errors,
        "hits": sorted(hits, key=lambda hit: (hit["slot"], hit["unit"], hit["role"])),
    }
    identity = uuid.uuid4().hex
    state.save("run", identity, run)
    state.markdown(identity, render_report(identity, run))
    return identity, run


def load_run(state: State, identity: str) -> dict[str, Any]:
    """Revalidate a persisted run and its complete population, including passes."""

    run = fields(
        state.load("run", identity),
        {
            "corpus",
            "scanner",
            "profile",
            "secret_set",
            "units",
            "expected_units",
            "execution",
            "proven_rejections",
            "complete",
            "errors",
            "hits",
        },
    )
    ExecutionLimits.parse(run["execution"])
    corpus = manifest(state, run["corpus"])
    if (
        run["profile"] != PROFILE
        or any(
            not isinstance(run[name], str) or DIGEST.fullmatch(run[name]) is None
            for name in ("scanner", "secret_set")
        )
        or type(run["units"]) is not int
        or not 0 <= run["units"] <= corpus["units"]
        or type(run["expected_units"]) is not int
        or run["expected_units"] != corpus["units"]
        or type(run["complete"]) is not bool
        or not isinstance(run["errors"], list)
        or len(run["errors"]) > len(corpus["files"])
        or type(run["proven_rejections"]) is not int
        or not 0 <= run["proven_rejections"] <= run["units"]
    ):
        raise AuditError("invalid audit run")
    known_slots = {item["slot"] for item in corpus["files"]}
    unsupported_slots = {item["slot"] for item in corpus["files"] if item["error"] is not None}
    failed: set[str] = set()
    for error in run["errors"]:
        fields(error, {"slot", "reason"})
        if (
            error["slot"] not in known_slots
            or error["slot"] in failed
            or error["reason"] not in FAILURES
        ):
            raise AuditError("invalid run omission")
        failed.add(error["slot"])
        if (error["slot"] in unsupported_slots) != (error["reason"] == "unsupported_input"):
            raise AuditError("run omission does not match corpus")
    if not unsupported_slots <= failed:
        raise AuditError("run omitted unsupported inputs")
    population = sum(item["units"] for item in corpus["files"] if item["slot"] not in failed)
    if run["units"] != population or run["complete"] != (
        not failed and run["units"] == corpus["units"]
    ):
        raise AuditError("invalid complete population")
    validate_hits(run["hits"], files=corpus["files"], units=run["units"])
    files_by_slot = {item["slot"]: item for item in corpus["files"]}
    for hit in run["hits"]:
        item = files_by_slot[hit["slot"]]
        if hit["slot"] in failed or hit["id"] != _unit_id(
            state.key, run["corpus"], item, hit["unit"], hit["role"]
        ):
            raise AuditError("rejection identity does not match corpus")
    return run
