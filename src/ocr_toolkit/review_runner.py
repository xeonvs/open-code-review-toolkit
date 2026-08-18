"""Run Open Code Review with private artifacts and safe CI diagnostics."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from contextlib import ExitStack
from dataclasses import dataclass
from io import BufferedWriter
from pathlib import Path

from ocr_toolkit import mcp_config
from ocr_toolkit.common.redaction import redact_sensitive
from ocr_toolkit.evidence.artifacts import (
    EvidenceArtifacts,
    prepare_artifact_directory,
    remove_private_artifact,
    repository_artifacts,
    write_private_bytes,
    write_private_text,
)
from ocr_toolkit.evidence.collect import collect_repository_evidence
from ocr_toolkit.evidence.invocation import collect_invocation_evidence
from ocr_toolkit.evidence.mcp import TOOL_NAME, call_tool, evidence_summary
from ocr_toolkit.evidence.project import render_bootstrap
from ocr_toolkit.evidence.repository import (
    GitRepositoryReader,
    RepositoryEvidenceError,
    normalize_repo_path,
)
from ocr_toolkit.evidence.review_context import (
    MergeRequestContext,
    ReviewContextModeError,
    merge_request_context_record,
    parse_review_context_mode,
)
from ocr_toolkit.evidence.store import EvidenceStore, EvidenceStoreError
from ocr_toolkit.ocr_result import (
    OcrResultMalformed,
    OcrResultMissing,
    OcrResultTooLarge,
    attach_toolkit_metadata,
)
from ocr_toolkit.providers.gitlab import (
    GitLabProviderError,
    acquire_review_snapshot,
    invocation_identifiers,
    is_merge_request_environment,
)
from ocr_toolkit.result_contract import OcrResultContractError, parse_result_outcome

STDERR_PROBE_BYTES = 64 * 1024
DEFAULT_DIAGNOSTIC_CHARS = 4_000


class ReviewRunnerError(Exception):
    """The local OCR review process could not be started safely."""


@dataclass(frozen=True, slots=True)
class ReviewRefs:
    """Name the immutable base and head refs represented by one OCR review."""

    base: str
    head: str


@dataclass(frozen=True, slots=True)
class ReviewIdentity:
    """Bind immutable review/provider identities to context selection."""

    source_sha: str
    policy_sha: str
    mr_author_id: int | None
    context_mode: str
    context: MergeRequestContext | None

    @property
    def context_state(self) -> str:
        if self.context_mode == "off":
            return "disabled"
        return self.context.state if self.context is not None else "degraded"


def _verify_evidence_mcp(store: EvidenceStore) -> None:
    """Exercise summary, paginated list, and stable-ID get before starting OCR."""

    summary = call_tool(store, {"action": "summary"})
    if summary.get("isError") is True:
        raise ReviewRunnerError("OCR evidence MCP summary self-query failed")
    listed = call_tool(store, {"action": "list", "ref": "head", "page_size": 1})
    if listed.get("isError") is True:
        raise ReviewRunnerError("OCR evidence MCP list self-query failed")
    content = listed.get("content")
    if not isinstance(content, list) or not content or not isinstance(content[0], dict):
        raise ReviewRunnerError("OCR evidence MCP list self-query returned an invalid envelope")
    text = content[0].get("text")
    if not isinstance(text, str):
        raise ReviewRunnerError("OCR evidence MCP list self-query returned invalid text")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ReviewRunnerError("OCR evidence MCP list self-query returned invalid JSON") from exc
    records = payload.get("records") if isinstance(payload, dict) else None
    if not isinstance(records, list):
        raise ReviewRunnerError("OCR evidence MCP list self-query returned invalid records")
    if records:
        record_id = records[0].get("id") if isinstance(records[0], dict) else None
        fetched = call_tool(store, {"action": "get", "id": record_id})
        if fetched.get("isError") is True:
            raise ReviewRunnerError("OCR evidence MCP get self-query failed")


def _review_receipt(
    payload: dict[str, object],
    composition: mcp_config.MCPComposition,
    identity: ReviewIdentity,
) -> dict[str, object]:
    """Return a closed privacy-safe receipt tied to review-time facts."""

    try:
        outcome = parse_result_outcome(payload)
    except OcrResultContractError as exc:
        raise ReviewRunnerError(f"OCR result has an unsupported outcome contract: {exc}") from exc

    tool_calls = payload.get("tool_calls")
    by_tool = tool_calls.get("by_tool") if isinstance(tool_calls, dict) else None
    if outcome.kind == "skipped":
        legacy_message_invalid = (
            not outcome.manifest_present and payload.get("message") != "No supported files changed."
        )
        if (
            legacy_message_invalid
            or payload.get("comments") != []
            or not isinstance(tool_calls, dict)
            or tool_calls.get("total") != 0
            or by_tool != {}
        ):
            raise ReviewRunnerError(
                "OCR skipped result does not match the pinned no-supported-files contract"
            )

    owners = {
        tool: capability.server
        for capability in composition.capabilities
        for tool in capability.tools
    }
    usage: dict[str, int] = {}
    if isinstance(by_tool, dict):
        for tool, count in by_tool.items():
            if (
                isinstance(tool, str)
                and isinstance(count, int)
                and not isinstance(count, bool)
                and count > 0
                and tool in owners
            ):
                owner = owners[tool]
                usage[owner] = usage.get(owner, 0) + count
    evidence_used = usage.get(mcp_config.BUILTIN_EVIDENCE_SERVER, 0) > 0
    if outcome.requires_evidence_mcp and not evidence_used:
        raise ReviewRunnerError(f"OCR review did not call the mandatory {TOOL_NAME} tool")
    capabilities = [
        {
            "server": capability.server,
            "transport": "builtin" if capability.builtin else capability.transport,
            "tools": list(capability.tools),
        }
        for capability in composition.capabilities
    ]
    return {
        "review": {
            "source_sha": identity.source_sha,
            "policy_sha": identity.policy_sha,
            "mr_author_id": identity.mr_author_id,
        },
        "context": {
            "mode": identity.context_mode,
            "state": identity.context_state,
            "classes": ["merge_request_metadata"] if identity.context_mode == "metadata" else [],
        },
        "mcp": {
            "capabilities": capabilities,
            "usage": dict(sorted(usage.items())),
        },
        "evidence": {
            "mandatory": outcome.requires_evidence_mcp,
            "used": evidence_used,
        },
    }


def _record_ocr_result_mcp_usage(
    result_path: Path,
    composition: mcp_config.MCPComposition,
    identity: ReviewIdentity,
) -> dict[str, int]:
    """Verify MCP use and bind the closed review-time receipt to the result."""

    try:
        _payload, metadata = attach_toolkit_metadata(
            result_path,
            lambda payload: _review_receipt(payload, composition, identity),
        )
    except (OcrResultMalformed, OcrResultMissing, OcrResultTooLarge) as exc:
        raise ReviewRunnerError("OCR result is not valid bounded JSON") from exc
    mcp = metadata.get("mcp")
    usage = mcp.get("usage") if isinstance(mcp, dict) else None
    return usage if isinstance(usage, dict) else {}


def _option_values(args: list[str], name: str, short: str | None = None) -> list[str]:
    """Return values for one bounded OCR option form."""

    values: list[str] = []
    index = 0
    while index < len(args):
        argument = args[index]
        if argument == name or (short is not None and argument == short):
            if index + 1 >= len(args) or args[index + 1].startswith("-"):
                raise ReviewRunnerError(f"OCR option {argument} requires a value")
            values.append(args[index + 1])
            index += 2
            continue
        prefix = f"{name}="
        if argument.startswith(prefix):
            value = argument[len(prefix) :]
            if not value:
                raise ReviewRunnerError(f"OCR option {name} requires a value")
            values.append(value)
        index += 1
    return values


def _one_option(args: list[str], name: str, short: str | None = None) -> str | None:
    """Return one unique OCR option value or reject ambiguous duplicates."""

    values = _option_values(args, name, short)
    if len(values) > 1:
        raise ReviewRunnerError(f"OCR option {name} must be provided at most once")
    return values[0] if values else None


def _without_diff_options(args: list[str]) -> list[str]:
    """Return OCR arguments without caller-supplied diff selectors."""

    remaining: list[str] = []
    index = 0
    valued = {"--from", "--to", "--commit", "-c"}
    while index < len(args):
        item = args[index]
        if item in valued:
            index += 2
            continue
        if item.startswith(("--from=", "--to=", "--commit=")):
            index += 1
            continue
        remaining.append(item)
        index += 1
    return remaining


def _review_refs(args: list[str]) -> ReviewRefs:
    """Derive immutable evidence refs from the exact OCR diff arguments."""

    base = _one_option(args, "--from")
    head = _one_option(args, "--to")
    commit = _one_option(args, "--commit", "-c")
    if commit is not None:
        if base is not None or head is not None:
            raise ReviewRunnerError("OCR --commit cannot be combined with --from or --to")
        return ReviewRefs(f"{commit}^", commit)
    if (base is None) != (head is None):
        raise ReviewRunnerError("OCR evidence review requires both --from and --to")
    if base is None or head is None:
        raise ReviewRunnerError(
            "OCR evidence review requires immutable --from/--to refs or --commit"
        )
    return ReviewRefs(base, head)


def _immutable_review_refs(refs: ReviewRefs) -> ReviewRefs:
    """Resolve both OCR and evidence collection to one immutable commit pair."""

    reader = GitRepositoryReader(Path.cwd())
    return ReviewRefs(reader.resolve_commit(refs.base), reader.resolve_commit(refs.head))


def _reject_owned_background(args: list[str]) -> None:
    """Reject caller attempts to replace the toolkit-owned bootstrap file."""

    if _option_values(args, "--background-file"):
        raise ReviewRunnerError(
            "--background-file is managed by ocr-ci review; use --background for extra context"
        )


def _replace_rule_argument(args: list[str], old_value: str, new_value: str) -> list[str]:
    """Replace only the one parsed repository-owned OCR rule argument."""

    replaced: list[str] = []
    index = 0
    matches = 0
    while index < len(args):
        item = args[index]
        if item == "--rule":
            if index + 1 >= len(args):
                raise ReviewRunnerError("OCR option --rule requires a value")
            value = args[index + 1]
            replaced.extend((item, new_value if value == old_value else value))
            matches += value == old_value
            index += 2
            continue
        if item.startswith("--rule="):
            value = item.removeprefix("--rule=")
            replaced.append(f"--rule={new_value}" if value == old_value else item)
            matches += value == old_value
            index += 1
            continue
        replaced.append(item)
        index += 1
    if matches != 1:
        raise ReviewRunnerError("repository-owned OCR rule input is ambiguous")
    return replaced


def _repository_rule_path(value: str, root: Path) -> str | None:
    """Return a normalized in-repository rule path or None for explicit external input."""

    candidate = Path(value)
    if candidate.is_absolute():
        try:
            value = candidate.relative_to(root).as_posix()
        except ValueError:
            return None
    try:
        return normalize_repo_path(value)
    except RepositoryEvidenceError as exc:
        raise ReviewRunnerError("OCR --rule repository path is unsafe") from exc


def _prepare_policy_context(
    refs: ReviewRefs, ocr_args: list[str], artifacts: EvidenceArtifacts
) -> tuple[ReviewIdentity, list[str]]:
    """Capture policy identity and selected context, then materialize rules."""

    try:
        context_mode = parse_review_context_mode(os.environ.get("OCR_REVIEW_CONTEXT_MODE"))
    except ReviewContextModeError as exc:
        raise ReviewRunnerError(str(exc)) from exc
    reader = GitRepositoryReader(Path.cwd())
    context = None
    author_id = None
    if is_merge_request_environment(os.environ):
        snapshot = acquire_review_snapshot(
            os.environ, expected_head=refs.head, include_metadata=context_mode == "metadata"
        )
        reader.fetch_commit(snapshot.target_sha)
        policy_sha = reader.resolve_commit(snapshot.target_sha)
        context = snapshot.context
        author_id = snapshot.author_id
    else:
        if context_mode == "metadata":
            raise ReviewRunnerError("metadata review context requires a GitLab merge request")
        policy_sha = refs.base
    identity = ReviewIdentity(refs.head, policy_sha, author_id, context_mode, context)
    rule = _one_option(ocr_args, "--rule")
    if rule is None:
        remove_private_artifact(artifacts.policy_rules)
        return identity, ocr_args
    repository_path = _repository_rule_path(rule, reader.root)
    if repository_path is None:
        remove_private_artifact(artifacts.policy_rules)
        return identity, ocr_args
    try:
        content = reader.read_blob(policy_sha, repository_path)
    except RepositoryEvidenceError as exc:
        raise ReviewRunnerError("protected-target OCR rule is unavailable or unsafe") from exc
    if content is None:
        raise ReviewRunnerError("protected-target OCR rule does not exist")
    policy_rules = artifacts.policy_rules
    write_private_bytes(policy_rules, content)
    return identity, _replace_rule_argument(ocr_args, rule, str(policy_rules))


def run_evidence_review(result_path: Path, stderr_path: Path, ocr_args: list[str]) -> int:
    """Prepare private evidence and run OCR through the composed MCP context."""

    refs = _immutable_review_refs(_review_refs(ocr_args))
    _reject_owned_background(ocr_args)
    artifacts = repository_artifacts()
    print("OCR evidence preflight: collecting immutable review refs", file=sys.stderr)
    try:
        prepare_artifact_directory(artifacts)
        identity, effective_ocr_args = _prepare_policy_context(refs, ocr_args, artifacts)
        store = collect_repository_evidence(
            base_ref=refs.base, head_ref=refs.head, policy_ref=identity.policy_sha
        )
        head_sha = store.head.commit_sha if store.head else ""
        identifiers = invocation_identifiers(os.environ)
        for record in collect_invocation_evidence(identifiers, head_sha=head_sha):
            if not store.add(record):
                store.add_diagnostic("review invocation evidence was truncated by store limits")
                break
        if identity.context is not None and not store.add(
            merge_request_context_record(identity.context)
        ):
            store.add_diagnostic("merge-request context was truncated by store limits")
        store.write(artifacts.store)
        composition = mcp_config.build_mcp_composition(
            profile="gitlab_mr" if identity.mr_author_id is not None else "local"
        )
        bootstrap = render_bootstrap(store, capabilities=composition.capabilities)
        write_private_text(artifacts.bootstrap, bootstrap)
        mcp_config.apply_mcp_composition(composition)
        mcp_config.verify_mcp_composition(composition)
        summary = evidence_summary(store)
        _verify_evidence_mcp(store)
    except (
        EvidenceStoreError,
        OSError,
        GitLabProviderError,
        RepositoryEvidenceError,
        ValueError,
        mcp_config.MCPConfigError,
    ) as exc:
        raise ReviewRunnerError(
            f"OCR evidence preflight failed: {redact_sensitive(str(exc))}"
        ) from exc
    records = summary.get("records")
    if not isinstance(records, int) or isinstance(records, bool) or records < 0:
        raise ReviewRunnerError("OCR evidence preflight returned an invalid MCP summary")
    print(
        "OCR evidence preflight: ready "
        f"base={summary.get('base')} head={summary.get('head')} records={records} "
        f"mcp_servers={len(composition.capabilities)} "
        f"builtin_tool={TOOL_NAME}",
        file=sys.stderr,
    )
    print(
        "OCR MCP registry: ready "
        f"servers={len(composition.capabilities)} mandatory={TOOL_NAME} self_query=summary",
        file=sys.stderr,
    )
    exit_code = run_review(
        result_path,
        stderr_path,
        [
            "--from",
            refs.base,
            "--to",
            refs.head,
            *_without_diff_options(effective_ocr_args),
            "--background-file",
            str(artifacts.bootstrap),
        ],
    )
    if exit_code == 0:
        usage = _record_ocr_result_mcp_usage(
            result_path,
            composition,
            identity,
        )
        calls = usage.get(mcp_config.BUILTIN_EVIDENCE_SERVER, 0)
        if calls > 0:
            print(
                f"OCR evidence usage: verified tool={TOOL_NAME} calls={calls}",
                file=sys.stderr,
            )
        else:
            print("OCR evidence usage: skipped no-supported-files review", file=sys.stderr)
    return exit_code


def _open_private_artifact(path: Path, label: str) -> BufferedWriter:
    """Open one regular artifact without following a final-component symlink."""

    flags = os.O_CREAT | os.O_WRONLY
    if hasattr(os, "O_NOFOLLOW"):
        # The pre-check gives a clear error; O_NOFOLLOW closes the replacement race
        # between that check and open on platforms that expose the flag.
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_NONBLOCK"):
        # Opening a pre-created FIFO for writing could otherwise block the CI job
        # before the descriptor can be rejected as a non-artifact sink.
        flags |= os.O_NONBLOCK
    descriptor = -1
    try:
        descriptor = os.open(path, flags, 0o600)
        file_stat = os.fstat(descriptor)
        if not stat.S_ISREG(file_stat.st_mode):
            raise ReviewRunnerError(f"private {label} artifact must be a regular file: {path}")
        if file_stat.st_nlink > 1:
            raise ReviewRunnerError(f"private {label} artifact must not have hard links: {path}")
        os.fchmod(descriptor, 0o600)
        # Delay truncation until the descriptor has passed type and link checks.
        os.ftruncate(descriptor, 0)
    except ReviewRunnerError:
        if descriptor >= 0:
            os.close(descriptor)
        raise
    except OSError as exc:
        if descriptor >= 0:
            os.close(descriptor)
        raise ReviewRunnerError(f"could not open private {label} artifact: {exc}") from exc
    return open(descriptor, "wb", closefd=True)


def read_stderr_excerpt(stderr_path: Path, max_chars: int = DEFAULT_DIAGNOSTIC_CHARS) -> str:
    """Read a bounded, redacted excerpt of an OCR stderr artifact."""

    if not stderr_path.exists():
        return ""
    try:
        with stderr_path.open("rb") as handle:
            chunk = handle.read(STDERR_PROBE_BYTES)
    except OSError:
        return ""

    text = chunk.decode("utf-8", errors="replace").strip()
    if not text:
        return ""
    # Redact before truncation so a secret crossing the display boundary is
    # matched against its complete environment value or credential pattern.
    return redact_sensitive(text)[:max_chars]


def run_review(result_path: Path, stderr_path: Path, ocr_args: list[str]) -> int:
    """Execute `ocr review`, retain private artifacts, and report safe failures."""

    if not ocr_args:
        raise ReviewRunnerError("at least one OCR review argument is required after --")
    if result_path.absolute() == stderr_path.absolute():
        raise ReviewRunnerError("result and stderr paths must be different")
    for path, label in ((result_path, "result"), (stderr_path, "stderr")):
        if path.is_symlink():
            raise ReviewRunnerError(f"{label} path must not be a symlink: {path}")
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)

    # Use explicit argv and file descriptors: OCR-controlled output never crosses
    # a shell, while umask 077 keeps both artifacts private on shared runners.
    previous_umask = os.umask(0o077)
    try:
        with ExitStack() as stack:
            result_file = stack.enter_context(_open_private_artifact(result_path, "result"))
            stderr_file = stack.enter_context(_open_private_artifact(stderr_path, "stderr"))
            if os.path.samestat(os.fstat(result_file.fileno()), os.fstat(stderr_file.fileno())):
                raise ReviewRunnerError("result and stderr paths must be different")
            completed = subprocess.run(
                ["ocr", "review", *ocr_args],
                check=False,
                stdin=subprocess.DEVNULL,
                stdout=result_file,
                stderr=stderr_file,
            )
    except OSError as exc:
        raise ReviewRunnerError(f"could not execute OCR: {exc}") from exc
    finally:
        os.umask(previous_umask)

    if completed.returncode != 0:
        print(f"Open Code Review exited with code {completed.returncode}.", file=sys.stderr)
        excerpt = read_stderr_excerpt(stderr_path)
        if excerpt:
            print("Safe OCR stderr excerpt:", file=sys.stderr)
            print(excerpt, file=sys.stderr)
        else:
            print("OCR did not provide a readable stderr diagnostic.", file=sys.stderr)
    return completed.returncode
