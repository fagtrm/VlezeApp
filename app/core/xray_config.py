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
    def generate_config(vless_entry: dict[str, Any], output_path: Path,
                        overrides: dict[str, str] | None = None) -> Path:
        """Generate an xray configuration file from a VLESS entry.

        Args:
            vless_entry: Dictionary produced by VLESSParser.parse_vless_link().
            output_path: Where to write the generated JSON config.
            overrides: Optional dict of field overrides to apply on top of
                the parsed vless entry values.

        Returns:
            The path to the written configuration file.
        """
        # Применяем overrides к entry
        entry: dict[str, Any] = dict(vless_entry)
        if overrides:
            for key, value in overrides.items():
                if value:  # не перезаписываем пустыми значениями
                    entry[key] = value

        sni: str = entry.get("sni") or entry["host"]

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
                                "address": entry["host"],
                                "port": int(entry["port"]),
                                "users": [
                                    {
                                        "id": entry["id"],
                                        "encryption": "none",
                                        "level": 8,
                                    }
                                ],
                            }
                        ]
                    },
                    "streamSettings": {
                        "network": entry["type"],
                        "security": entry["security"],
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
        if entry["security"] == "tls":
            stream["tlsSettings"] = {
                "allowInsecure": False,
                "serverName": sni,
                "fingerprint": "chrome",
            }
            if entry.get("alpn"):
                stream["tlsSettings"]["alpn"] = [entry["alpn"]]

        # Reality settings
        elif entry["security"] == "reality":
            stream["realitySettings"] = {
                "show": False,
                "fingerprint": entry.get("fp", "chrome"),
                "serverName": sni,
                "publicKey": entry.get("pbk", ""),
                "shortId": entry.get("sid", ""),
                "spiderX": "/",
            }

        # WebSocket settings
        if entry["type"] == "ws":
            stream["wsSettings"] = {
                "path": entry.get("path", "/"),
                "headers": {
                    "Host": entry.get("host", sni),
                },
            }

        # TCP with HTTP header伪装
        if entry.get("headerType") == "http":
            stream["tcpSettings"] = {
                "header": {
                    "type": "http",
                    "request": {
                        "path": [entry.get("path", "/")],
                        "headers": {
                            "Host": [entry.get("host", sni)],
                        },
                    },
                },
            }

        # Flow for xtls-rprx-vision
        if entry.get("flow") and entry["security"] in ("tls", "reality"):
            config["outbounds"][0]["settings"]["vnext"][0]["users"][0]["flow"] = entry["flow"]

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(config, fh, indent=2, ensure_ascii=False)

        return output_path
