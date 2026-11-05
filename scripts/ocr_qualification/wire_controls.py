"""Observe explicit request controls through actual bounded native HTTP clients."""

from __future__ import annotations

import subprocess
from pathlib import Path

from . import core, execution, peer


def stream_override_probe(binary: Path, directory: Path) -> dict[str, object]:
    """Require false on the wire while rejecting non-boolean streaming requests.

    The controlled peer returns HTTP 400 after bounded metadata capture: no
    real model, credentials, request bodies or model-quality claim is involved.
    Native ChatGPT's provider-owned streaming is qualified by its consumer suite.
    """

    from ocr_toolkit.config_writer import write_ocr_config

    root = directory / "stream-override-probe"
    root.mkdir()
    git_env = execution._isolated_probe_environment(root / "git-home")
    repo, base, head = execution._synthetic_repo(root, git_env)
    protocols = ("openai", "openai-responses", "anthropic")
    for protocol in protocols:
        for label, extra in (
            ("unset", {}),
            ("false", {"stream": False}),
            ("non-boolean", {"stream": "false"}),
        ):
            env = execution._isolated_probe_environment(root / f"{protocol}-{label}-home")
            with peer._stub_gateway(capture_controls=True) as gateway_url:
                config = {
                    "auth_token": "synthetic-token",
                    "model": "synthetic-model",
                    "protocol": protocol,
                    "url": gateway_url.removesuffix("/v1")
                    if protocol == "anthropic"
                    else gateway_url,
                    "use_anthropic": protocol == "anthropic",
                    "extra_body": extra,
                }
                write_ocr_config(
                    {"llm": config, "telemetry": {"enabled": False}},
                    Path(env["HOME"]) / ".opencodereview" / "config.json",
                )
                try:
                    completed = subprocess.run(  # nosec B603
                        [
                            str(binary),
                            "review",
                            "--from",
                            base,
                            "--to",
                            head,
                            "--format",
                            "json",
                            "--audience",
                            "agent",
                            "--effort",
                            "low",
                            "--concurrency",
                            "1",
                        ],
                        cwd=repo,
                        env=env,
                        check=False,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=30,
                    )
                except (OSError, subprocess.TimeoutExpired) as exc:
                    raise core.CompatibilityError(
                        f"stream wire probe did not finish: {protocol}/{label}"
                    ) from exc
                observed = list(peer._StubHandler.control_requests)
                overflow = peer._StubHandler.control_overflow
            expected_path = {
                "openai": "/v1/chat/completions",
                "openai-responses": "/v1/responses",
                "anthropic": "/v1/messages",
            }[protocol]
            if completed.returncode < 0 or overflow or not observed:
                core._fail(f"stream wire probe was incomplete: {protocol}/{label}")
            for request in observed:
                if (
                    request["path"] != expected_path
                    or request["stream_present"] is not (label == "false")
                    or request["stream_boolean"] != (False if label == "false" else None)
                    or request["stream_options_present"] is not False
                ):
                    core._fail(f"stream wire fields disagree: {protocol}/{label}")
    return {
        "result": "passed",
        "protocols": list(protocols),
        "explicit_false": "preserved",
        "non_boolean": "omitted",
        "unset": "omitted",
        "provider_acceptance": "not-tested",
    }
