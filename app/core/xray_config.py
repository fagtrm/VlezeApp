"""
Xray configuration generator for VlezeApp.

Generates the JSON configuration file that xray-core consumes,
translating parsed VLESS entries into the proper inbound/outbound
structure with transport and security settings.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.i18n import _


class XrayConfigGenerator:
    """Generates xray-core JSON configuration files.

    All methods are static -- no instance state is required.
    """

    @staticmethod
    def generate_config(vless_entry: dict[str, Any], output_path: Path) -> Path:
        """Generate an xray configuration file from a VLESS entry.

        Args:
            vless_entry: Dictionary produced by VLESSParser.parse_vless_link().
            output_path: Where to write the generated JSON config.

        Returns:
            The path to the written configuration file.
        """
        sni: str = vless_entry.get("sni") or vless_entry["host"]

        config: dict[str, Any] = {
            "log": {
                "access": "",
                "error": "",
                "loglevel": "debug",
            },
            "inbounds": [
                {
                    "tag": "socks",
                    "port": 1080,
                    "listen": "127.0.0.1",
                    "protocol": "socks",
                    "settings": {
                        "auth": "noauth",
                        "udp": True,
                        "userLevel": 8,
                    },
                    "sniffing": {
                        "enabled": True,
                        "destOverride": ["http", "tls", "quic"],
                    },
                },
                {
                    "tag": "http",
                    "port": 1081,
                    "listen": "127.0.0.1",
                    "protocol": "http",
                    "settings": {
                        "userLevel": 8,
                    },
                },
            ],
            "outbounds": [
                {
                    "tag": "proxy",
                    "protocol": "vless",
                    "settings": {
                        "vnext": [
                            {
                                "address": vless_entry["host"],
                                "port": int(vless_entry["port"]),
                                "users": [
                                    {
                                        "id": vless_entry["id"],
                                        "encryption": "none",
                                        "level": 8,
                                    }
                                ],
                            }
                        ]
                    },
                    "streamSettings": {
                        "network": vless_entry["type"],
                        "security": vless_entry["security"],
                    },
                    "mux": {
                        "enabled": False,
                    },
                },
                {
                    "tag": "direct",
                    "protocol": "freedom",
                    "settings": {},
                },
                {
                    "tag": "block",
                    "protocol": "blackhole",
                    "settings": {},
                },
            ],
            "routing": {
                "domainStrategy": "IPIfNonMatch",
                "rules": [],
            },
        }

        stream: dict[str, Any] = config["outbounds"][0]["streamSettings"]

        # TLS settings
        if vless_entry["security"] == "tls":
            stream["tlsSettings"] = {
                "allowInsecure": False,
                "serverName": sni,
                "fingerprint": "chrome",
            }
            if vless_entry.get("alpn"):
                stream["tlsSettings"]["alpn"] = [vless_entry["alpn"]]

        # Reality settings
        elif vless_entry["security"] == "reality":
            stream["realitySettings"] = {
                "show": False,
                "fingerprint": vless_entry.get("fp", "chrome"),
                "serverName": sni,
                "publicKey": vless_entry.get("pbk", ""),
                "shortId": vless_entry.get("sid", ""),
                "spiderX": "/",
            }

        # WebSocket settings
        if vless_entry["type"] == "ws":
            stream["wsSettings"] = {
                "path": vless_entry.get("path", "/"),
                "headers": {
                    "Host": vless_entry.get("host", sni),
                },
            }

        # TCP with HTTP header伪装
        if vless_entry.get("headerType") == "http":
            stream["tcpSettings"] = {
                "header": {
                    "type": "http",
                    "request": {
                        "path": [vless_entry.get("path", "/")],
                        "headers": {
                            "Host": [vless_entry.get("host", sni)],
                        },
                    },
                },
            }

        # Flow for xtls-rprx-vision
        if vless_entry.get("flow") and vless_entry["security"] in ("tls", "reality"):
            config["outbounds"][0]["settings"]["vnext"][0]["users"][0]["flow"] = vless_entry["flow"]

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(config, fh, indent=2, ensure_ascii=False)

        return output_path
