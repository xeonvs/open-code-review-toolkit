"""Source-free command interface and exact expectations for private audit runs."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, NoReturn

from ocr_toolkit.common.filesystem import open_private_parent_directory

from .corpus import capture, cleanup, manifest, read_input, selected_file
from .limits import MAX_HIT_BYTES, MAX_HITS, ExecutionLimits
from .scanner import PROFILE, REASONS, load_run, scan, secret_fingerprint
from .state import DIGEST, AuditError, State, encode, fields

LABELS = frozenset({"expected-protection", "confirmed-benign", "conservative-ambiguity"})


class Parser(argparse.ArgumentParser):
    """Never echo rejected operator arguments or paths into console errors."""

    def error(self, _message: str) -> NoReturn:
        raise AuditError("invalid command arguments; use --help")


def expectations(state: State, corpus_id: str) -> dict[str, dict[str, Any]]:
    """Read exact annotations; absence means untriaged, never an allowlist."""

    try:
        value = fields(state.load("expectations", corpus_id), {"profile", "secret_set", "entries"})
    except FileNotFoundError:
        return {}
    if (
        value["profile"] != PROFILE
        or value["secret_set"] != secret_fingerprint(state)
        or not isinstance(value["entries"], list)
        or len(value["entries"]) > MAX_HITS
    ):
        raise AuditError("invalid annotation population")
    entries: dict[str, dict[str, Any]] = {}
    used = 0
    for entry in value["entries"]:
        fields(entry, {"id", "label", "reason", "detector", "proof"})
        if (
            not isinstance(entry["id"], str)
            or DIGEST.fullmatch(entry["id"]) is None
            or entry["id"] in entries
            or entry["label"] not in LABELS
            or entry["reason"] not in REASONS
            or not isinstance(entry["detector"], str)
            or len(entry["detector"]) > 80
            or any(char not in "abcdefghijklmnopqrstuvwxyz_:-" for char in entry["detector"])
            or type(entry["proof"]) is not bool
        ):
            raise AuditError("invalid exact annotation")
        entries[entry["id"]] = entry
        used += len(encode(entry)) + 1
        if used > MAX_HIT_BYTES:
            raise AuditError("annotation byte limit")
    return entries


def assess(run: dict[str, Any], entries: dict[str, dict[str, Any]]) -> dict[str, int]:
    """Evaluate expectations without skipping a scan or changing runtime policy."""

    hits = {hit["id"]: hit for hit in run["hits"]}
    result = {"untriaged": 0, "benign_rejected": 0, "protection_lost": 0, "changed_reason": 0}
    for identity, hit in hits.items():
        entry = entries.get(identity)
        if entry is None:
            result["untriaged"] += 1
        elif entry["label"] == "confirmed-benign":
            result["benign_rejected"] += 1
        elif any(entry[name] != hit[name] for name in ("reason", "detector", "proof")):
            result["changed_reason"] += 1
    for identity, entry in entries.items():
        if entry["label"] != "confirmed-benign" and identity not in hits:
            result["protection_lost"] += 1
    return result


def annotate(state: State, run_id: str, identities: list[str], label: str) -> int:
    """Assign a reviewed classification to exact rejected units of one complete run."""

    run = load_run(state, run_id)
    if (
        not run["complete"]
        or run["secret_set"] != secret_fingerprint(state)
        or label not in LABELS
        or len(set(identities)) != len(identities)
    ):
        raise AuditError("annotation requires a complete run and exact unique identities")
    hits = {hit["id"]: hit for hit in run["hits"]}
    entries = expectations(state, run["corpus"])
    for identity in identities:
        if identity not in hits:
            raise AuditError("annotation does not identify a rejected unit")
        hit = hits[identity]
        entries[identity] = {
            "id": identity,
            "label": label,
            "reason": hit["reason"],
            "detector": hit["detector"],
            "proof": hit["proof"],
        }
        if len(entries) > MAX_HITS:
            raise AuditError("annotation count limit")
    if sum(len(encode(entry)) + 1 for entry in entries.values()) > MAX_HIT_BYTES:
        raise AuditError("annotation byte limit")
    state.save(
        "expectations",
        run["corpus"],
        {
            "profile": PROFILE,
            "secret_set": run["secret_set"],
            "entries": sorted(entries.values(), key=lambda entry: entry["id"]),
        },
    )
    return len(identities)


def compare(state: State, before_id: str, after_id: str) -> tuple[int, dict[str, Any]]:
    """Compare complete identical populations, including previously passing units."""

    before, after = load_run(state, before_id), load_run(state, after_id)
    if (
        not before["complete"]
        or not after["complete"]
        or any(
            before[name] != after[name]
            for name in ("corpus", "profile", "secret_set", "expected_units")
        )
        or after["secret_set"] != secret_fingerprint(state)
    ):
        raise AuditError("runs are incomplete or incomparable")
    old = {hit["id"]: hit for hit in before["hits"]}
    new = {hit["id"]: hit for hit in after["hits"]}
    entries = expectations(state, before["corpus"])
    decisions = assess(after, entries)
    changed = sum(
        any(old[identity][name] != new[identity][name] for name in ("reason", "detector", "proof"))
        for identity in old.keys() & new.keys()
    )
    unexplained_admissions = sum(identity not in entries for identity in old.keys() - new.keys())
    unreviewed_changes = sum(
        any(old[identity][name] != new[identity][name] for name in ("reason", "detector", "proof"))
        and (
            identity not in entries
            or any(
                entries[identity][name] != new[identity][name]
                for name in ("reason", "detector", "proof")
            )
        )
        for identity in old.keys() & new.keys()
    )
    result = {
        "newly_rejected": len(new.keys() - old.keys()),
        "newly_admitted": len(old.keys() - new.keys()),
        "changed_decisions": changed,
        "unexplained_admissions": unexplained_admissions,
        "unreviewed_changes": unreviewed_changes,
        **decisions,
    }
    informational = {"newly_admitted", "newly_rejected", "changed_decisions"}
    return int(any(result[name] for name in result if name not in informational)), result


def configure_parser(result: argparse.ArgumentParser) -> None:
    """Register the local audit commands in the owning CLI or focused parser."""

    result.add_argument("--state-dir", type=Path, required=True)
    sub = result.add_subparsers(dest="operation", required=True, parser_class=Parser)
    scanning = sub.add_parser("scan", help="capture selected sources or replay a captured corpus")
    selection = scanning.add_mutually_exclusive_group(required=True)
    selection.add_argument("--git-ref")
    selection.add_argument("--files-from0", type=Path)
    selection.add_argument("--stdin", action="store_true")
    selection.add_argument("--snapshot")
    scanning.add_argument("--root", type=Path)
    scanning.add_argument(
        "--metadata-only",
        action="store_true",
        help="bind original file bytes without copying sources",
    )
    scanning.add_argument(
        "--seconds", type=int, default=900, choices=range(1, 86_401), metavar="1..86400"
    )
    scanning.add_argument(
        "--file-seconds", type=int, default=60, choices=range(1, 3601), metavar="1..3600"
    )
    scanning.add_argument(
        "--git-seconds", type=int, default=120, choices=range(1, 3601), metavar="1..3600"
    )
    comparison = sub.add_parser("compare", help="compare two complete runs on the same corpus")
    comparison.add_argument("before")
    comparison.add_argument("after")
    annotation = sub.add_parser(
        "annotate", help="classify exact rejected identities without suppressing scanning"
    )
    annotation.add_argument("run")
    annotation.add_argument("--label", choices=sorted(LABELS), required=True)
    annotation.add_argument("--hit", action="append", required=True)
    removal = sub.add_parser(
        "cleanup", help="delete owned raw source snapshots, retain source-free evidence"
    )
    removal.add_argument("corpus")


def error_result() -> int:
    """Emit one source-free failure at either parser or execution boundary."""

    print('{"error":"audit invalid or incomplete; no source values emitted"}', file=sys.stderr)
    return 2


def run(args: argparse.Namespace) -> int:
    """Return 0 for satisfied complete checks, 1 for triage, 2 for invalid/incomplete."""

    try:
        creating = args.operation == "scan" and not args.snapshot
        with State(args.state_dir, create=creating) as state:
            if args.operation == "scan":
                limits = ExecutionLimits(args.seconds, args.file_seconds, args.git_seconds)
                deadline = time.monotonic() + limits.seconds
                if args.snapshot:
                    if args.root is not None or args.metadata_only:
                        raise AuditError("snapshot replay cannot select an input root")
                    corpus_id = args.snapshot
                elif args.stdin:
                    if args.root is not None or args.metadata_only:
                        raise AuditError("snippet input cannot select an input root")
                    corpus_id = capture(
                        state,
                        snippet=read_input(sys.stdin.buffer.fileno(), deadline=deadline),
                        deadline=deadline,
                    )
                else:
                    paths = None
                    if args.files_from0:
                        parent, name = open_private_parent_directory(args.files_from0, create=False)
                        try:
                            raw = selected_file(parent, name, textual=False)
                        finally:
                            os.close(parent)
                        if not raw.endswith(b"\x00"):
                            raise AuditError("file list must be bounded and NUL-terminated")
                        paths = raw[:-1].decode().split("\x00")
                    corpus_id = capture(
                        state,
                        root=args.root,
                        paths=paths,
                        git_ref=args.git_ref,
                        git_seconds=limits.git_seconds,
                        metadata_only=args.metadata_only,
                        deadline=deadline,
                    )
                run_id, run = scan(state, corpus_id, deadline=deadline, limits=limits)
                decisions = assess(run, expectations(state, corpus_id))
                code = 2 if not run["complete"] else int(any(decisions.values()))
                summary = {
                    "corpus": corpus_id,
                    "run": run_id,
                    "complete": run["complete"],
                    "units": run["units"],
                    "rejections": len(run["hits"]),
                    **decisions,
                }
            elif args.operation == "compare":
                code, summary = compare(state, args.before, args.after)
            elif args.operation == "annotate":
                summary = {"annotated": annotate(state, args.run, args.hit, args.label)}
                code = 0
            else:
                # Revalidate even on an idempotent cleanup, including the signed owner.
                manifest(state, args.corpus)
                cleanup(state, args.corpus)
                summary, code = {"raw_removed": True, "corpus": args.corpus}, 0
        print(json.dumps(summary, sort_keys=True))
        return code
    except (
        AuditError,
        OSError,
        ValueError,
        TypeError,
        KeyError,
        RecursionError,
        MemoryError,
        subprocess.SubprocessError,
    ):
        return error_result()
