"""Tests for app.core.vless_parser.VLESSParser.

Covers base64 decoding, vless:// link parsing, flag extraction,
and parameter handling (security, type, path, sni, pbk, sid, flow).
"""

import base64
import pytest

from app.core.vless_parser import VLESSParser


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def parser() -> type[VLESSParser]:
    """Return the VLESSParser class (all methods are static)."""
    return VLESSParser


# ---------------------------------------------------------------------------
# Helpers for building test links
# ---------------------------------------------------------------------------

def _make_vless_link(
    uuid: str = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    host: str = "example.com",
    port: str = "443",
    name: str = "TestServer",
    **params: str,
) -> str:
    """Construct a vless:// link from components."""
    query = "&".join(f"{k}={v}" for k, v in params.items())
    fragment = f"#{name}" if name else ""
    if query:
        return f"vless://{uuid}@{host}:{port}?{query}{fragment}"
    return f"vless://{uuid}@{host}:{port}{fragment}"


def _encode_links(links: list[str]) -> str:
    """Encode a list of vless:// links as base64."""
    payload = "\n".join(links)
    return base64.b64encode(payload.encode("utf-8")).decode("ascii")


# ---------------------------------------------------------------------------
# test_decode_base64_links
# ---------------------------------------------------------------------------

class TestDecodeBase64Links:
    """Tests for VLESSParser.decode_base64_links()."""

    def test_decode_single_link(self, parser: type[VLESSParser]) -> None:
        """A single vless:// link encoded in base64 should be decoded."""
        link = _make_vless_link(name="Single")
        encoded = _encode_links([link])
        result = parser.decode_base64_links(encoded)
        assert result == [link]

    def test_decode_multiple_links(self, parser: type[VLESSParser]) -> None:
        """Multiple vless:// links separated by newlines should all be decoded."""
        links = [
            _make_vless_link(host="server1.com", name="Server1"),
            _make_vless_link(host="server2.com", name="Server2"),
        ]
        encoded = _encode_links(links)
        result = parser.decode_base64_links(encoded)
        assert result == links

    def test_decode_ignores_non_vless_lines(self, parser: type[VLESSParser]) -> None:
        """Lines that do not start with vless:// should be filtered out."""
        raw = "vmess://abc\nvless://uuid@host:443#Test\nsome garbage"
        encoded = base64.b64encode(raw.encode("utf-8")).decode("ascii")
        result = parser.decode_base64_links(encoded)
        assert len(result) == 1
        assert result[0].startswith("vless://")

    def test_decode_empty_input(self, parser: type[VLESSParser]) -> None:
        """Empty or whitespace-only input should return an empty list."""
        assert parser.decode_base64_links("") == []
        assert parser.decode_base64_links("   \n  ") == []

    def test_decode_invalid_base64(self, parser: type[VLESSParser]) -> None:
        """Invalid base64 input should return an empty list without raising."""
        result = parser.decode_base64_links("!!!not-valid-base64!!!")
        assert result == []


# ---------------------------------------------------------------------------
# test_parse_vless_link — basic parsing
# ---------------------------------------------------------------------------

class TestParseVlessLink:
    """Tests for VLESSParser.parse_vless_link()."""

    def test_parse_basic_link(self, parser: type[VLESSParser]) -> None:
        """A minimal vless:// link should yield id, host, port, and defaults."""
        link = _make_vless_link(
            uuid="test-uuid-1234",
            host="myserver.example.com",
            port="8443",
            name="MyServer",
        )
        result = parser.parse_vless_link(link)

        assert result["id"] == "test-uuid-1234"
        assert result["host"] == "myserver.example.com"
        assert result["port"] == "8443"
        assert result["name"] == "MyServer"
        assert result["raw_link"] == link

    def test_parse_defaults(self, parser: type[VLESSParser]) -> None:
        """Fields not present in the link should have sensible defaults."""
        link = "vless://uuid@host:443#Name"
        result = parser.parse_vless_link(link)

        assert result["type"] == "tcp"
        assert result["path"] == "/"
        assert result["security"] == "none"
        assert result["alpn"] == ""
        assert result["sni"] == ""
        assert result["fp"] == "chrome"
        assert result["flow"] == ""
        assert result["pbk"] == ""
        assert result["sid"] == ""
        assert result["headerType"] == ""

    def test_parse_no_name(self, parser: type[VLESSParser]) -> None:
        """A link without a fragment should default name to 'Unknown' (or localized equivalent)."""
        link = "vless://uuid@host:443"
        result = parser.parse_vless_link(link)
        # The name is translated via _(), so accept both English and Russian
        assert result["name"] in ("Unknown", "Неизвестно")

    def test_parse_invalid_link(self, parser: type[VLESSParser]) -> None:
        """A link without @ should return defaults with empty id/host."""
        link = "vless://no-at-sign"
        result = parser.parse_vless_link(link)
        assert result["id"] == ""
        assert result["host"] == ""


# ---------------------------------------------------------------------------
# test_extract_flag
# ---------------------------------------------------------------------------

class TestExtractFlag:
    """Tests for VLESSParser._extract_flag()."""

    def test_extract_flag_from_name(self, parser: type[VLESSParser]) -> None:
        """A name starting with a flag emoji should return that flag."""
        # DE flag
        name = "\U0001F1E9\U0001F1EA Germany Server"
        assert parser._extract_flag(name) == "\U0001F1E9\U0001F1EA"

    def test_extract_flag_no_flag(self, parser: type[VLESSParser]) -> None:
        """A name without any flag emoji should return the globe emoji."""
        assert parser._extract_flag("Just a name") == "\U0001F310"

    def test_extract_flag_empty_name(self, parser: type[VLESSParser]) -> None:
        """An empty name should return the globe emoji."""
        assert parser._extract_flag("") == "\U0001F310"

    def test_flag_stripped_from_name(self, parser: type[VLESSParser]) -> None:
        """After parsing, the flag should be removed from the name field."""
        link = _make_vless_link(
            name="\U0001F1FA\U0001F1F8 US Server",
        )
        result = parser.parse_vless_link(link)
        assert result["icon"] == "\U0001F1FA\U0001F1F8"
        assert result["name"] == "US Server"


# ---------------------------------------------------------------------------
# test_parse_vless_link — parameters
# ---------------------------------------------------------------------------

class TestParseVlessLinkParameters:
    """Tests for parameter extraction from vless:// links."""

    def test_security_tls(self, parser: type[VLESSParser]) -> None:
        """security=tls should be parsed correctly."""
        link = _make_vless_link(security="tls")
        result = parser.parse_vless_link(link)
        assert result["security"] == "tls"

    def test_security_reality(self, parser: type[VLESSParser]) -> None:
        """security=reality should be parsed correctly."""
        link = _make_vless_link(security="reality")
        result = parser.parse_vless_link(link)
        assert result["security"] == "reality"

    def test_type_websocket(self, parser: type[VLESSParser]) -> None:
        """type=ws should be parsed correctly."""
        link = _make_vless_link(type="ws")
        result = parser.parse_vless_link(link)
        assert result["type"] == "ws"

    def test_path_parameter(self, parser: type[VLESSParser]) -> None:
        """path=/vless should be URL-decoded and stored."""
        link = _make_vless_link(path="%2Fvless%2Fpath")
        result = parser.parse_vless_link(link)
        assert result["path"] == "/vless/path"

    def test_sni_parameter(self, parser: type[VLESSParser]) -> None:
        """sni=cdn.example.com should be parsed."""
        link = _make_vless_link(sni="cdn.example.com")
        result = parser.parse_vless_link(link)
        assert result["sni"] == "cdn.example.com"

    def test_pbk_parameter(self, parser: type[VLESSParser]) -> None:
        """pbk (public key) should be parsed for Reality."""
        link = _make_vless_link(
            security="reality",
            pbk="dHKw5G8Jk7VxMqR3bN0cYfT2aZlUiOpS9eXwQv4mDjE",
        )
        result = parser.parse_vless_link(link)
        assert result["pbk"] == "dHKw5G8Jk7VxMqR3bN0cYfT2aZlUiOpS9eXwQv4mDjE"

    def test_sid_parameter(self, parser: type[VLESSParser]) -> None:
        """sid (short id) should be parsed for Reality."""
        link = _make_vless_link(security="reality", sid="a1b2c3d4")
        result = parser.parse_vless_link(link)
        assert result["sid"] == "a1b2c3d4"

    def test_flow_parameter(self, parser: type[VLESSParser]) -> None:
        """flow=xtls-rprx-vision should be parsed."""
        link = _make_vless_link(flow="xtls-rprx-vision")
        result = parser.parse_vless_link(link)
        assert result["flow"] == "xtls-rprx-vision"

    def test_all_parameters_combined(self, parser: type[VLESSParser]) -> None:
        """A link with many parameters should parse all of them."""
        link = _make_vless_link(
            host="proxy.example.com",
            port="443",
            type="ws",
            path="/vless",
            security="tls",
            sni="cdn.example.com",
            alpn="h2",
            name="FullServer",
        )
        result = parser.parse_vless_link(link)

        assert result["host"] == "proxy.example.com"
        assert result["port"] == "443"
        assert result["type"] == "ws"
        assert result["path"] == "/vless"
        assert result["security"] == "tls"
        assert result["sni"] == "cdn.example.com"
        assert result["alpn"] == "h2"
        assert result["name"] == "FullServer"
