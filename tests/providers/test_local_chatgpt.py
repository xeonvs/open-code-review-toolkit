"""Local native auth metadata, isolated-home binding, and API separation contracts."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from ocr_toolkit import cli, configure, local_chatgpt, preflight, review_runner
from ocr_toolkit.config_writer import read_ocr_config, write_ocr_config


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep operator provider settings outside every synthetic auth test."""

    for name in tuple(os.environ):
        if name.startswith(("OCR_LLM_", "OCR_ANTHROPIC_")) or name == "OCR_USE_ANTHROPIC":
            monkeypatch.delenv(name)
    monkeypatch.delenv("OCR_REVIEW_CONTEXT_MODE", raising=False)
    monkeypatch.delenv("OCR_REVIEW_CONTEXT_ADAPTERS_JSON", raising=False)


@pytest.fixture
def native_home(tmp_path: Path) -> Path:
    """Create only synthetic native-store shapes; no credential content is needed."""

    home = tmp_path / "operator-home"
    home.mkdir(mode=0o700)
    store = home / ".opencodereview" / "auth" / "chatgpt"
    store.mkdir(mode=0o700, parents=True)
    for name, value in (
        ("accounts.json", {"accounts": []}),
        ("host.json", {"id": "urn:uuid:00000000-0000-4000-8000-000000000001"}),
    ):
        path = store / name
        path.write_text(json.dumps(value), encoding="utf-8")
        path.chmod(0o600)
    return home


def test_chatgpt_configuration_uses_native_provider_and_optional_default_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OCR_LLM_AUTH_MODE", "chatgpt")
    updates = configure.build_config_updates(local=True)
    assert updates["provider"] == "chatgpt"
    assert updates["providers.chatgpt"] == {}
    assert not any(key.startswith("llm.") for key in updates)

    monkeypatch.setenv("OCR_LLM_MODEL", "synthetic-model")
    monkeypatch.setenv("OCR_LLM_REASONING_EFFORT", "high")
    monkeypatch.setenv(
        "OCR_LLM_EXTRA_BODY", '{"text":{"verbosity":"low"},"prompt_cache_key":"synthetic"}'
    )
    entry = configure.build_config_updates(local=True)["providers.chatgpt"]
    assert entry == {
        "model": "synthetic-model",
        "extra_body": {
            "reasoning": {"effort": "high"},
            "text": {"verbosity": "low"},
            "prompt_cache_key": "synthetic",
        },
    }


@pytest.mark.parametrize("mode", ["", " ", "\t\n", "unknown-mode"])
def test_invalid_explicit_auth_mode_never_defaults_to_api(
    mode: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("OCR_LLM_AUTH_MODE", mode)
    monkeypatch.setenv("OCR_LLM_URL", "https://custom.example.invalid/v1")
    monkeypatch.setenv("OCR_LLM_TOKEN", "synthetic-api-secret")
    monkeypatch.setenv("OCR_LLM_MODEL", "synthetic-api-model")
    monkeypatch.setattr(local_chatgpt, "native_store", lambda *_a: pytest.fail("auth touched"))
    monkeypatch.setattr(preflight, "validate_ocr_binary", lambda: pytest.fail("binary touched"))
    with pytest.raises(configure.OCRRuntimeConfigError, match="OCR_LLM_AUTH_MODE"):
        configure.build_config_updates(local=True)
    assert preflight.main(local=True) == 1
    with pytest.raises(review_runner.ReviewRunnerError, match="OCR_LLM_AUTH_MODE"):
        review_runner.run_evidence_review(
            tmp_path / "result.json", tmp_path / "stderr.log", [], local=True
        )


@pytest.mark.parametrize(
    "setting",
    [
        "OCR_LLM_URL",
        "OCR_LLM_TOKEN",
        "OCR_LLM_PROTOCOL",
        "OCR_LLM_AUTH_HEADER",
        "OCR_LLM_EXTRA_HEADERS",
        "OCR_LLM_MODELS_URL",
        "OCR_LLM_ALLOWED_MODELS",
        "OCR_LLM_MAX_COMPLETION_TOKENS",
        "OCR_ANTHROPIC_DISABLE_THINKING",
        "OCR_LLM_VALIDATE_MODEL",
        "OCR_USE_ANTHROPIC",
    ],
)
def test_chatgpt_conflicts_reject_before_any_auth_access(
    setting: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OCR_LLM_AUTH_MODE", "chatgpt")
    monkeypatch.setenv(setting, "synthetic-private-value")
    monkeypatch.setattr(local_chatgpt, "native_store", lambda *_a: pytest.fail("auth touched"))
    with pytest.raises(configure.OCRRuntimeConfigError) as error:
        configure.build_config_updates(local=True)
    assert "synthetic-private-value" not in str(error.value)
    assert cli.main(["preflight", "--local"]) == 1


@pytest.mark.parametrize("body", ['{"max_output_tokens":100}', '{"temperature":0}', "[]"])
def test_chatgpt_rejects_unsupported_body_without_native_acquisition(
    body: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OCR_LLM_AUTH_MODE", "chatgpt")
    monkeypatch.setenv("OCR_LLM_EXTRA_BODY", body)
    with pytest.raises(configure.OCRRuntimeConfigError):
        configure.build_config_updates(local=True)


def test_nonlocal_chatgpt_rejects_before_binary_provider_or_auth_access(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("OCR_LLM_AUTH_MODE", "chatgpt")
    monkeypatch.setenv("CI_PROJECT_ID", "7")
    monkeypatch.setenv("CI_MERGE_REQUEST_IID", "9")
    monkeypatch.setattr(local_chatgpt, "native_store", lambda *_a: pytest.fail("auth touched"))
    monkeypatch.setattr(preflight, "validate_ocr_binary", lambda: pytest.fail("binary touched"))
    monkeypatch.setattr(preflight, "validate_gitlab_access", lambda: pytest.fail("GitLab touched"))
    assert cli.main(["preflight"]) == 1
    assert configure.main() == 1
    with pytest.raises(review_runner.ReviewRunnerError, match="explicit --local"):
        review_runner.run_evidence_review(tmp_path / "result.json", tmp_path / "stderr.log", [])
    assert not (tmp_path / "result.json").exists()


@pytest.mark.parametrize("arguments", [["--provider", "openai"], ["--provider=chatgpt"]])
def test_chatgpt_rejects_caller_provider_override_before_auth_access(
    arguments: list[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("OCR_LLM_AUTH_MODE", "chatgpt")
    monkeypatch.setattr(local_chatgpt, "native_store", lambda *_a: pytest.fail("auth touched"))
    with pytest.raises(review_runner.ReviewRunnerError, match="cannot override"):
        review_runner.run_evidence_review(
            tmp_path / "result.json",
            tmp_path / "stderr.log",
            arguments,
            local=True,
        )


@pytest.mark.parametrize("version", ["1.13.2", "1.13.3"])
def test_chatgpt_preflight_is_structural_only_and_never_calls_status_or_models(
    native_home: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    version: str,
) -> None:
    monkeypatch.setenv("HOME", str(native_home))
    monkeypatch.setenv("OCR_LLM_AUTH_MODE", "chatgpt")
    monkeypatch.setattr(preflight, "validate_ocr_binary", lambda: version)
    monkeypatch.setattr(preflight, "validate_llm_model", lambda: pytest.fail("API model call"))
    monkeypatch.setattr(preflight, "validate_gitlab_access", lambda: pytest.fail("GitLab call"))
    monkeypatch.setattr(local_chatgpt.os, "open", lambda *_a, **_kw: pytest.fail("file bytes read"))
    assert cli.main(["preflight", "--local"]) == 0
    assert (
        "OCR checks account, plan permission, and expiry on actual use" in capsys.readouterr().out
    )


def test_chatgpt_old_binary_rejects_before_native_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OCR_LLM_AUTH_MODE", "chatgpt")
    monkeypatch.setattr(preflight, "validate_ocr_binary", lambda: "1.13.1")
    monkeypatch.setattr(local_chatgpt, "native_store", lambda *_a: pytest.fail("auth touched"))
    assert cli.main(["preflight", "--local"]) == 1


@pytest.mark.parametrize("local", [False, True])
@pytest.mark.parametrize("protocol", ["openai", "openai-responses", "anthropic"])
def test_default_custom_api_survives_existing_native_provider_selection(
    local: bool,
    protocol: str,
    monkeypatch: pytest.MonkeyPatch,
    native_home: Path,
) -> None:
    monkeypatch.setenv("HOME", str(native_home))
    monkeypatch.setenv("OCR_LLM_URL", "https://custom.example.invalid/v1")
    monkeypatch.setenv("OCR_LLM_TOKEN", "synthetic-api-secret")
    monkeypatch.setenv("OCR_LLM_MODEL", "synthetic-api-model")
    monkeypatch.setenv("OCR_LLM_PROTOCOL", protocol)
    monkeypatch.setattr(
        local_chatgpt, "native_store", lambda *_a: pytest.fail("native auth touched")
    )
    write_ocr_config({"provider": "chatgpt", "providers": {"chatgpt": {"model": "old"}}})
    assert configure.main() == 0
    config = read_ocr_config()
    assert config["provider"] == ""
    assert config["llm"]["url"] == "https://custom.example.invalid/v1"
    assert config["llm"]["auth_token"] == "synthetic-api-secret"
    assert config["llm"]["protocol"] == protocol
    seen: list[str] = []
    monkeypatch.setattr(preflight, "validate_ocr_binary", lambda: seen.append("ocr"))
    monkeypatch.setattr(preflight, "validate_gitlab_access", lambda: seen.append("gitlab"))
    monkeypatch.setattr(preflight, "validate_llm_model", lambda: seen.append("api"))
    assert preflight.main(local=local) == 0
    assert seen == (["ocr", "api"] if local else ["ocr", "gitlab", "api"])


@pytest.mark.parametrize(
    "attack",
    [
        "accounts-symlink",
        "host-symlink",
        "lock-symlink",
        "hardlink",
        "file-mode",
        "store-mode",
        "ancestor-mode",
        "ancestor-symlink",
        "oversized",
        "missing-host",
    ],
)
def test_native_store_rejects_hostile_metadata_through_real_filesystem(
    attack: str,
    native_home: Path,
    tmp_path: Path,
) -> None:
    store = native_home / ".opencodereview" / "auth" / "chatgpt"
    accounts = store / "accounts.json"
    if attack.endswith("symlink") and attack != "ancestor-symlink":
        name = {
            "accounts-symlink": "accounts.json",
            "host-symlink": "host.json",
            "lock-symlink": "session.lock",
        }[attack]
        target = tmp_path / "synthetic-target"
        target.write_text("synthetic", encoding="utf-8")
        (store / name).unlink(missing_ok=True)
        (store / name).symlink_to(target)
    elif attack == "hardlink":
        os.link(accounts, tmp_path / "another-name")
    elif attack == "file-mode":
        accounts.chmod(0o644)
    elif attack == "store-mode":
        store.chmod(0o755)
    elif attack == "ancestor-mode":
        (native_home / ".opencodereview").chmod(0o777)
    elif attack == "ancestor-symlink":
        config = native_home / ".opencodereview"
        moved = native_home / "moved-config"
        config.rename(moved)
        config.symlink_to(moved, target_is_directory=True)
    elif attack == "oversized":
        with accounts.open("r+b") as stream:
            stream.truncate(1_000_001)
    else:
        (store / "host.json").unlink()
    with pytest.raises(local_chatgpt.LocalChatGPTError):
        local_chatgpt.native_store({"HOME": str(native_home)})


@pytest.mark.parametrize(
    "home", ["relative-home", "/tmp/../synthetic-home", "/tmp/./synthetic-home", ""]
)
def test_native_store_rejects_nonlexical_home_before_filesystem(home: str) -> None:
    with pytest.raises(local_chatgpt.LocalChatGPTError, match="absolute lexical path"):
        local_chatgpt.native_store({"HOME": home})


def test_private_home_link_preserves_shared_lock_atomic_refresh_and_cleanup(
    native_home: Path,
    tmp_path: Path,
) -> None:
    store = local_chatgpt.native_store({"HOME": str(native_home)})
    session_home = tmp_path / "session-home"
    session_home.mkdir(mode=0o700)
    write_ocr_config(
        {"provider": "chatgpt", "providers": {"chatgpt": {}}},
        session_home / ".opencodereview" / "config.json",
    )
    local_chatgpt.link_native_store(store, session_home)
    linked = session_home / ".opencodereview" / "auth" / "chatgpt"
    assert linked.is_symlink() and linked.resolve() == store
    host_before = (store / "host.json").read_bytes()
    peer = """import fcntl, json, os, sys
from pathlib import Path
store = Path(sys.argv[1])
with (store / 'session.lock').open('a') as lock:
    os.chmod(lock.name, 0o600)
    fcntl.flock(lock, fcntl.LOCK_EX)
    temporary = store / '.write-synthetic'
    temporary.write_text(json.dumps({'accounts': [], 'synthetic_generation': 2}))
    temporary.chmod(0o600)
    os.replace(temporary, store / 'accounts.json')
"""
    completed = subprocess.run(
        [sys.executable, "-I", "-c", peer, str(linked)], capture_output=True, text=True, timeout=10
    )
    assert completed.returncode == 0, completed.stderr
    assert (linked / "session.lock").stat().st_ino == (store / "session.lock").stat().st_ino
    assert json.loads((store / "accounts.json").read_text())["synthetic_generation"] == 2
    shutil.rmtree(session_home)
    assert store.is_dir() and (store / "host.json").read_bytes() == host_before
    assert local_chatgpt.native_store({"HOME": str(native_home)}) == store


def test_local_review_process_receives_native_binding_and_cleans_only_private_home(
    native_home: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cross real caller/files/processes with OCR replaced beyond those boundaries."""

    repository = tmp_path / "review-repository"
    repository.mkdir()
    git = shutil.which("git")
    assert git is not None
    git_environment = {
        "HOME": str(native_home),
        "PATH": os.environ["PATH"],
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
    }
    for command in (
        ["init", "-q"],
        ["config", "user.name", "Synthetic"],
        ["config", "user.email", "synthetic@example.invalid"],
        ["config", "commit.gpgsign", "false"],
    ):
        subprocess.run(
            [git, *command],
            cwd=repository,
            env=git_environment,
            check=True,
            capture_output=True,
            timeout=10,
        )
    source = repository / "example.py"
    for value in (1, 2):
        source.write_text(f"value = {value}\n", encoding="utf-8")
        subprocess.run(
            [git, "add", "example.py"],
            cwd=repository,
            env=git_environment,
            check=True,
            capture_output=True,
            timeout=10,
        )
        subprocess.run(
            [git, "commit", "-qm", "Synthetic change"],
            cwd=repository,
            env=git_environment,
            check=True,
            capture_output=True,
            timeout=10,
        )
    store = local_chatgpt.native_store({"HOME": str(native_home)})
    host_before = (store / "host.json").read_bytes()
    # Existing native user config must never be inherited into the review HOME.
    write_ocr_config(
        {"provider": "other-provider", "untrusted_marker": "inherited"},
        native_home / ".opencodereview" / "config.json",
    )
    marker = tmp_path / "controlled-ocr-observation.json"
    binary_directory = tmp_path / "bin"
    binary_directory.mkdir()
    binary = binary_directory / "ocr"
    peer = f"""#!{sys.executable} -I
import json, os, sys
from pathlib import Path
if sys.argv[1:] == ['--version']:
    print('1.13.2')
    raise SystemExit(0)
home = Path(os.environ['HOME'])
config = json.loads((home / '.opencodereview/config.json').read_text())
store = home / '.opencodereview/auth/chatgpt'
assert config['provider'] == 'chatgpt'
assert config['providers']['chatgpt'] == {{'model': 'synthetic-native-model'}}
assert 'llm' not in config and 'untrusted_marker' not in config
assert store.is_symlink() and str(store.resolve()) == {str(store)!r}
if '--preview' in sys.argv:
    raise SystemExit(0)
marker = Path({str(marker)!r})
marker.write_text(json.dumps({{'home': str(home), 'provider': config['provider']}}))
marker.chmod(0o600)
temporary = store / '.write-synthetic-review'
temporary.write_text(json.dumps({{'accounts': [], 'synthetic_generation': 3}}))
temporary.chmod(0o600)
os.replace(temporary, store / 'accounts.json')
print('Synthetic native auth unavailable; no model request', file=sys.stderr)
raise SystemExit(2)
"""
    binary.write_text(peer, encoding="utf-8")
    binary.chmod(0o700)
    monkeypatch.chdir(repository)
    monkeypatch.setenv("HOME", str(native_home))
    monkeypatch.setenv("PATH", f"{binary_directory}:/usr/bin:/bin")
    monkeypatch.setenv("OCR_LLM_AUTH_MODE", "chatgpt")
    monkeypatch.setenv("OCR_LLM_MODEL", "synthetic-native-model")
    monkeypatch.setenv("OCR_TELEMETRY_ENABLED", "false")
    monkeypatch.delenv("OCR_MCP_SERVERS_JSON", raising=False)
    monkeypatch.delenv("OCR_MCP_REPLACE", raising=False)
    monkeypatch.setattr(
        review_runner, "acquire_review_snapshot", lambda *_a, **_kw: pytest.fail("GitLab called")
    )
    result = review_runner.run_evidence_review(
        tmp_path / "result.json",
        tmp_path / "stderr.log",
        ["--commit", "HEAD"],
        local=True,
    )
    assert result == 2
    observation = json.loads(marker.read_text())
    assert observation["provider"] == "chatgpt"
    assert observation["home"] != str(native_home) and not Path(observation["home"]).exists()
    assert (store / "host.json").read_bytes() == host_before
    assert json.loads((store / "accounts.json").read_text())["synthetic_generation"] == 3
    assert os.environ["HOME"] == str(native_home)
