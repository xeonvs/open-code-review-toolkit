"""Shared composition checks for governed federation registry v2."""

from types import SimpleNamespace
from urllib.parse import quote

import pytest

from ocr_toolkit import mcp_config

REGISTRY = """{
  "version": 2,
  "servers": {
    "docs": {
      "transport": {"type": "https", "url": "https://docs.example.invalid/mcp"},
      "tools": {"read": {"assurance": "review_read"}}
    }
  }
}"""


def test_empty_registry_keeps_mandatory_evidence_mcp(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mcp_config, "read_ocr_config", lambda: {"mcp_servers": {}})
    composition = mcp_config.compose_mcp_servers([])

    assert set(composition.payload) == {mcp_config.BUILTIN_EVIDENCE_SERVER}
    assert composition.capabilities[0].builtin is True
    assert composition.capabilities[0].tools == (
        "ocr_toolkit_evidence",
        "ocr_toolkit_evidence_search",
        "ocr_toolkit_evidence_coverage",
    )


def test_external_registry_requires_ready_gateway_and_preserves_builtin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    servers = mcp_config.parse_mcp_servers(REGISTRY, profile="gitlab_mr")
    monkeypatch.setattr(mcp_config, "read_ocr_config", lambda: {"mcp_servers": {}})
    with pytest.raises(mcp_config.MCPConfigError, match="prepared gateway"):
        mcp_config.compose_mcp_servers(servers, profile="gitlab_mr")

    gateway = SimpleNamespace(
        aliases=("docs__read",),
        ocr_server={"command": "/private/python", "args": ["relay"], "tools": ["docs__read"]},
        secret_values=(),
    )
    composition = mcp_config.compose_mcp_servers(servers, profile="gitlab_mr", gateway=gateway)
    assert set(composition.payload) == {
        mcp_config.BUILTIN_EVIDENCE_SERVER,
        mcp_config.FEDERATION_SERVER,
    }
    assert [cap.server for cap in composition.capabilities] == [
        mcp_config.BUILTIN_EVIDENCE_SERVER,
        "docs",
    ]
    assert composition.capabilities[1].tools == ("docs__read",)


def test_old_direct_inputs_are_rejected_without_echoing_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OCR_MCP_REPLACE", "secret-old-value")
    with pytest.raises(mcp_config.MCPConfigError, match="was removed") as caught:
        mcp_config.parse_mcp_servers(REGISTRY)
    assert "secret-old-value" not in str(caught.value)


def test_inherited_direct_server_cannot_bypass_gateway(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        mcp_config,
        "read_ocr_config",
        lambda: {"mcp_servers": {"unowned": {"type": "remote"}}},
    )
    with pytest.raises(mcp_config.MCPConfigError, match="Inherited direct MCP"):
        mcp_config.compose_mcp_servers([])


@pytest.mark.parametrize("name", ["ocr_toolkit_evidence", "ocr_toolkit_federation"])
def test_registry_rejects_reserved_internal_server_names(name: str) -> None:
    raw = REGISTRY.replace('"docs":', f'"{name}":')
    with pytest.raises(mcp_config.MCPConfigError, match="Invalid governed MCP registry"):
        mcp_config.parse_mcp_servers(raw, profile="gitlab_mr")


def test_apply_and_verify_round_trip_exact_composition(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mcp_config, "read_ocr_config", lambda: {"mcp_servers": {}})
    composition = mcp_config.compose_mcp_servers([])
    written: list[dict[str, object]] = []
    monkeypatch.setattr(mcp_config, "update_ocr_config", lambda update: written.append(update))

    mcp_config.apply_mcp_composition(composition)
    assert written == [{"mcp_servers": composition.payload}]

    monkeypatch.setattr(mcp_config, "read_ocr_config", lambda: {"mcp_servers": composition.payload})
    mcp_config.verify_mcp_composition(composition)
    monkeypatch.setattr(mcp_config, "read_ocr_config", lambda: {"mcp_servers": {}})
    with pytest.raises(mcp_config.MCPConfigError, match="does not match"):
        mcp_config.verify_mcp_composition(composition)


def test_apply_failure_redacts_raw_and_encoded_gateway_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "token/value"
    composition = mcp_config.MCPComposition({}, (), (), (secret,))

    def fail(_update: object) -> None:
        raise mcp_config.OCRConfigError(f"write failed: {secret} {quote(secret, safe='')}")

    monkeypatch.setattr(mcp_config, "update_ocr_config", fail)
    with pytest.raises(mcp_config.MCPConfigError) as caught:
        mcp_config.apply_mcp_composition(composition)
    assert secret not in str(caught.value)
    assert quote(secret, safe="") not in str(caught.value)
    assert "***" in str(caught.value)


def test_configure_validates_registry_but_persists_only_mandatory_server(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("OCR_MCP_SERVERS_JSON", REGISTRY)
    monkeypatch.setattr(mcp_config, "read_ocr_config", lambda: {"mcp_servers": {}})
    written: list[dict[str, object]] = []
    monkeypatch.setattr(mcp_config, "update_ocr_config", lambda update: written.append(update))

    assert mcp_config.configure_mcp_servers() == 0
    output = capsys.readouterr().out
    assert "server=docs tool=docs__read assurance=review_read" in output
    assert "external sessions start at review" in output
    persisted = written[0]["mcp_servers"]
    assert isinstance(persisted, dict)
    assert set(persisted) == {mcp_config.BUILTIN_EVIDENCE_SERVER}


def test_composition_rejects_invalid_profile_and_relative_context_store(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(mcp_config, "read_ocr_config", lambda: {"mcp_servers": {}})
    with pytest.raises(mcp_config.MCPConfigError, match="profile"):
        mcp_config.compose_mcp_servers([], profile="unknown")
    with pytest.raises(mcp_config.MCPConfigError, match="absolute"):
        mcp_config.compose_mcp_servers(
            [],
            context=mcp_config.MCPContextConfig("relative.json", "a" * 32, "b" * 64),
        )
