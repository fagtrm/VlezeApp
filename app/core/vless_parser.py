"""
VLESS link parsing module for VlezeApp.

Decodes base64-encoded subscription payloads and parses individual
vless:// URIs into structured dictionaries.
"""

from __future__ import annotations

import base64
import re
from typing import Any
from urllib.parse import parse_qs, unquote

from app.i18n import _


class VLESSParser:
    """Parses vless:// links into structured dictionaries.

    All methods are static -- no instance state is required.
    """

    @staticmethod
    def decode_base64_links(base64_content: str) -> list[str]:
        """Decode base64 content into a list of vless:// links.

        Args:
            base64_content: Base64-encoded string potentially containing
                one or more vless:// links.

        Returns:
            A list of raw vless:// link strings.  Returns an empty list
            on any decoding error.
        """
        try:
            cleaned = base64_content.strip()
            decoded_bytes = base64.b64decode(cleaned)
            decoded_str = decoded_bytes.decode("utf-8", errors="ignore")
            lines = decoded_str.strip().split("\n")
            vless_links = [
                line.strip() for line in lines if line.strip().startswith("vless://")
            ]
            return vless_links
        except Exception as exc:
            print(_("Ошибка декодирования base64: {}").format(exc))
            return []

    @staticmethod
    def parse_vless_link(link: str) -> dict[str, Any]:
        """Parse a single vless:// link into a dictionary.

        Expected format::

            vless://uuid@host:port?type=tcp&path=/&security=tls&alpn=h2#Название

        Args:
            link: The raw vless:// URI string.

        Returns:
            A dictionary with keys: id, host, port, type, path, security,
            alpn, sni, fp, flow, pbk, sid, headerType, name, icon, raw_link.
        """
        result: dict[str, Any] = {
            "id": "",
            "host": "",
            "port": "",
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
            "name": _("Unknown"),
            "icon": "\U0001F310",
            "raw_link": link,
        }

        try:
            without_prefix = link.replace("vless://", "", 1)

            # --- Extract name (after first # following ?) ---
            link_part = without_prefix
            if "#" in without_prefix:
                qmark_pos = without_prefix.find("?")
                if qmark_pos >= 0:
                    hash_pos = without_prefix.find("#", qmark_pos)
                    if hash_pos >= 0:
                        link_part = without_prefix[:hash_pos]
                        name_part = without_prefix[hash_pos + 1:]
                        result["name"] = unquote(name_part.strip())
                else:
                    hash_pos = without_prefix.find("#")
                    if hash_pos >= 0:
                        link_part = without_prefix[:hash_pos]
                        name_part = without_prefix[hash_pos + 1:]
                        result["name"] = unquote(name_part.strip())

            # --- Split uuid@host:port?params ---
            if "@" in link_part:
                uuid_part, host_port_params = link_part.split("@", 1)
                result["id"] = uuid_part
            else:
                return result

            # --- Parse query parameters ---
            if "?" in host_port_params:
                host_port, params_part = host_port_params.split("?", 1)
                params = parse_qs(params_part)
                result["type"] = params.get("type", ["tcp"])[0]
                result["path"] = unquote(params.get("path", ["/"])[0])
                result["security"] = params.get("security", ["none"])[0]
                result["alpn"] = params.get("alpn", [""])[0]
                result["sni"] = params.get("sni", [""])[0]
                result["fp"] = params.get("fp", ["chrome"])[0]
                result["flow"] = params.get("flow", [""])[0]
                result["pbk"] = params.get("pbk", [""])[0]
                result["sid"] = params.get("sid", [""])[0]
                result["headerType"] = params.get("headerType", [""])[0]
            else:
                host_port = host_port_params

            # --- Parse host:port ---
            if ":" in host_port:
                last_colon = host_port.rfind(":")
                result["host"] = host_port[:last_colon]
                result["port"] = host_port[last_colon + 1:]
            else:
                result["host"] = host_port

            # --- Extract flag icon from name ---
            result["icon"] = VLESSParser._extract_flag(result["name"])
            result["name"] = re.sub(
                r"^[\U0001F1E6-\U0001F1FF]{2}\s*", "", result["name"]
            ).strip()
            result["name"] = re.sub(r"^[\s,]+", "", result["name"]).strip()

        except Exception as exc:
            print(_("Ошибка парсинга ссылки: {}").format(exc))

        return result

    @staticmethod
    def _extract_flag(name: str) -> str:
        """Extract the first emoji flag pair from a name string.

        Args:
            name: The server name potentially containing flag emojis.

        Returns:
            A two-character flag emoji, or the globe emoji if none found.
        """
        flag_pattern = re.compile(r"[\U0001F1E6-\U0001F1FF]{2}")
        match = flag_pattern.search(name)
        if match:
            return match.group(0)
        return "\U0001F310"
