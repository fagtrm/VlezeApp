"""Tests for app.core.xray_config.XrayConfigGenerator.

Covers config generation with TLS, Reality, WebSocket transports,
and validates the overall JSON structure (inbounds, outbounds, routing).
"""

import json
import tempfile
from pathlib import Path
from typing import Any

import pytest

from app.core.xray_config import XrayConfigGenerator


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def generator() -> type[XrayConfigGenerator]:
    """Return the XrayConfigGenerator class (all methods are static)."""
    return XrayConfigGenerator


def _base_entry(**overrides: Any) -> dict[str, Any]:
    """Return a minimal vless entry dict suitable for config generation."""
    entry: dict[str, Any] = {
        "id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "host": "proxy.example.com",
        "port": "443",
        "type": "tcp",
        "path": "/",
        "security": "none",
        "alpn": "",
        "sni": "",
        "fp": "chrome",
        "flow": "",
        "pbk": "",
        "sid": "",
        "headerType": "",
        "name": "TestServer",
        "icon": "\U0001F310",
    }
    entry.update(overrides)
    return entry


def _generate_and_load(generator: type[XrayConfigGenerator], entry: dict[str, Any]) -> dict[str, Any]:
    """Generate a config and return the parsed JSON dict."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        out_path = Path(tmp.name)
    generator.generate_config(entry, out_path)
    with open(out_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    out_path.unlink()
    return data


# ---------------------------------------------------------------------------
# Structural tests — always present regardless of transport
# ---------------------------------------------------------------------------

class TestConfigStructure:
    """Validate the top-level structure of every generated config."""

    def test_has_inbounds(self, generator: type[XrayConfigGenerator]) -> None:
        """Generated config must contain an 'inbounds' key with at least one entry."""
        data = _generate_and_load(generator, _base_entry())
        assert "inbounds" in data
        assert isinstance(data["inbounds"], list)
        assert len(data["inbounds"]) >= 2

    def test_has_outbounds(self, generator: type[XrayConfigGenerator]) -> None:
        """Generated config must contain an 'outbounds' key with proxy/direct/block."""
        data = _generate_and_load(generator, _base_entry())
        assert "outbounds" in data
        assert isinstance(data["outbounds"], list)
        tags = [ob["tag"] for ob in data["outbounds"]]
        assert "proxy" in tags
        assert "direct" in tags
        assert "block" in tags

    def test_has_routing(self, generator: type[XrayConfigGenerator]) -> None:
        """Generated config must contain a 'routing' key."""
        data = _generate_and_load(generator, _base_entry())
        assert "routing" in data
        assert "domainStrategy" in data["routing"]
        assert "rules" in data["routing"]

    def test_has_log_section(self, generator: type[XrayConfigGenerator]) -> None:
        """Generated config must contain a 'log' key."""
        data = _generate_and_load(generator, _base_entry())
        assert "log" in data
        assert data["log"]["loglevel"] == "debug"

    def test_socks_inbound(self, generator: type[XrayConfigGenerator]) -> None:
        """The socks inbound should listen on 127.0.0.1:1080."""
        data = _generate_and_load(generator, _base_entry())
        socks = next(ob for ob in data["inbounds"] if ob["tag"] == "socks")
        assert socks["listen"] == "127.0.0.1"
        assert socks["port"] == 1080
        assert socks["protocol"] == "socks"

    def test_http_inbound(self, generator: type[XrayConfigGenerator]) -> None:
        """The http inbound should listen on 127.0.0.1:1081."""
        data = _generate_and_load(generator, _base_entry())
        http = next(ob for ob in data["inbounds"] if ob["tag"] == "http")
        assert http["listen"] == "127.0.0.1"
        assert http["port"] == 1081
        assert http["protocol"] == "http"

    def test_proxy_outbound_uses_vless(self, generator: type[XrayConfigGenerator]) -> None:
        """The proxy outbound must use the vless protocol."""
        data = _generate_and_load(generator, _base_entry())
        proxy = next(ob for ob in data["outbounds"] if ob["tag"] == "proxy")
        assert proxy["protocol"] == "vless"


# ---------------------------------------------------------------------------
# TLS config
# ---------------------------------------------------------------------------

class TestConfigWithTLS:
    """Tests for configs with security=tls."""

    def test_tls_settings_present(self, generator: type[XrayConfigGenerator]) -> None:
        """security=tls should produce tlsSettings in streamSettings."""
        entry = _base_entry(security="tls", sni="cdn.example.com")
        data = _generate_and_load(generator, entry)
        stream = data["outbounds"][0]["streamSettings"]
        assert "tlsSettings" in stream
        assert stream["tlsSettings"]["serverName"] == "cdn.example.com"
        assert stream["tlsSettings"]["allowInsecure"] is False
        assert stream["tlsSettings"]["fingerprint"] == "chrome"

    def test_tls_with_alpn(self, generator: type[XrayConfigGenerator]) -> None:
        """When alpn is set, tlsSettings should include the alpn list."""
        entry = _base_entry(security="tls", alpn="h2")
        data = _generate_and_load(generator, entry)
        tls = data["outbounds"][0]["streamSettings"]["tlsSettings"]
        assert "alpn" in tls
        assert tls["alpn"] == ["h2"]

    def test_tls_sni_falls_back_to_host(self, generator: type[XrayConfigGenerator]) -> None:
        """When sni is empty, serverName should fall back to host."""
        entry = _base_entry(security="tls", sni="", host="direct.example.com")
        data = _generate_and_load(generator, entry)
        tls = data["outbounds"][0]["streamSettings"]["tlsSettings"]
        assert tls["serverName"] == "direct.example.com"


# ---------------------------------------------------------------------------
# Reality config
# ---------------------------------------------------------------------------

class TestConfigWithReality:
    """Tests for configs with security=reality."""

    def test_reality_settings_present(self, generator: type[XrayConfigGenerator]) -> None:
        """security=reality should produce realitySettings in streamSettings."""
        entry = _base_entry(
            security="reality",
            pbk="TestPublicKey1234567890abcdef",
            sid="a1b2c3d4",
            fp="chrome",
            sni="sni.example.com",
        )
        data = _generate_and_load(generator, entry)
        stream = data["outbounds"][0]["streamSettings"]
        assert "realitySettings" in stream

        rl = stream["realitySettings"]
        assert rl["serverName"] == "sni.example.com"
        assert rl["publicKey"] == "TestPublicKey1234567890abcdef"
        assert rl["shortId"] == "a1b2c3d4"
        assert rl["fingerprint"] == "chrome"
        assert rl["show"] is False
        assert rl["spiderX"] == "/"

    def test_reality_sni_falls_back_to_host(self, generator: type[XrayConfigGenerator]) -> None:
        """When sni is empty for reality, serverName should fall back to host."""
        entry = _base_entry(security="reality", sni="", host="fallback.example.com")
        data = _generate_and_load(generator, entry)
        rl = data["outbounds"][0]["streamSettings"]["realitySettings"]
        assert rl["serverName"] == "fallback.example.com"


# ---------------------------------------------------------------------------
# WebSocket config
# ---------------------------------------------------------------------------

class TestConfigWithWebSocket:
    """Tests for configs with type=ws (WebSocket)."""

    def test_ws_settings_present(self, generator: type[XrayConfigGenerator]) -> None:
        """type=ws should produce wsSettings in streamSettings."""
        entry = _base_entry(type="ws", path="/vless-ws", host="ws.example.com")
        data = _generate_and_load(generator, entry)
        stream = data["outbounds"][0]["streamSettings"]
        assert "wsSettings" in stream

        ws = stream["wsSettings"]
        assert ws["path"] == "/vless-ws"
        assert ws["headers"]["Host"] == "ws.example.com"

    def test_ws_default_path(self, generator: type[XrayConfigGenerator]) -> None:
        """WebSocket config without explicit path should default to '/'."""
        entry = _base_entry(type="ws")
        data = _generate_and_load(generator, entry)
        ws = data["outbounds"][0]["streamSettings"]["wsSettings"]
        assert ws["path"] == "/"


# ---------------------------------------------------------------------------
# Flow config
# ---------------------------------------------------------------------------

class TestConfigWithFlow:
    """Tests for flow (xtls-rprx-vision) in TLS and Reality configs."""

    def test_flow_with_tls(self, generator: type[XrayConfigGenerator]) -> None:
        """flow should be set on the user object when security=tls."""
        entry = _base_entry(security="tls", flow="xtls-rprx-vision")
        data = _generate_and_load(generator, entry)
        user = data["outbounds"][0]["settings"]["vnext"][0]["users"][0]
        assert user["flow"] == "xtls-rprx-vision"

    def test_flow_with_reality(self, generator: type[XrayConfigGenerator]) -> None:
        """flow should be set on the user object when security=reality."""
        entry = _base_entry(security="reality", flow="xtls-rprx-vision")
        data = _generate_and_load(generator, entry)
        user = data["outbounds"][0]["settings"]["vnext"][0]["users"][0]
        assert user["flow"] == "xtls-rprx-vision"

    def test_flow_not_set_for_none_security(self, generator: type[XrayConfigGenerator]) -> None:
        """flow should NOT be set when security=none."""
        entry = _base_entry(flow="xtls-rprx-vision", security="none")
        data = _generate_and_load(generator, entry)
        user = data["outbounds"][0]["settings"]["vnext"][0]["users"][0]
        assert "flow" not in user


# ---------------------------------------------------------------------------
# Output path
# ---------------------------------------------------------------------------

class TestOutputPath:
    """Tests for the file-writing behaviour of generate_config."""

    def test_returns_output_path(self, generator: type[XrayConfigGenerator]) -> None:
        """generate_config should return the path it was given."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            out_path = Path(tmp.name)
        result = generator.generate_config(_base_entry(), out_path)
        assert result == out_path
        assert out_path.exists()
        out_path.unlink()

    def test_creates_parent_directories(self, generator: type[XrayConfigGenerator]) -> None:
        """generate_config should create parent directories if they do not exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "sub" / "dir" / "config.json"
            assert not out_path.parent.exists()
            generator.generate_config(_base_entry(), out_path)
            assert out_path.exists()
