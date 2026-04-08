"""
Application configuration management for VlezeApp.

Handles reading and writing of the application JSON configuration file,
including paths, preferences, and UI state persistence.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.i18n import _


CONFIG_DIR: Path = Path.home() / ".config" / "VlezeApp"
CONFIG_FILE: Path = CONFIG_DIR / "config.json"
VLESS_DIR: Path = CONFIG_DIR / "vless"


class AppConfig:
    """Reads and writes the application configuration file.

    Attributes:
        remember_last_server: Whether to remember the last selected server.
        last_server_name: Name of the last selected server.
        autostart_xray: Whether to auto-start xray on application launch.
        close_to_tray: Whether closing the window hides it to the system tray.
        start_minimized: Whether to start the application minimized to tray.
    """

    def __init__(self) -> None:
        self.remember_last_server: bool = False
        self.last_server_name: str = ""
        self.autostart_xray: bool = False
        self.close_to_tray: bool = False
        self.start_minimized: bool = False

        self._ensure_config_dir()
        self._load_or_create_config()

    def _ensure_config_dir(self) -> None:
        """Create the configuration and vless directories if they do not exist."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        VLESS_DIR.mkdir(parents=True, exist_ok=True)

    def _load_or_create_config(self) -> None:
        """Load configuration from disk or create a default one."""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as fh:
                    data: dict[str, Any] = json.load(fh)
                    self.remember_last_server = bool(data.get("remember_last_server", False))
                    self.last_server_name = str(data.get("last_server_name", ""))
                    self.autostart_xray = bool(data.get("autostart_xray", False))
                    self.close_to_tray = bool(data.get("close_to_tray", False))
                    self.start_minimized = bool(data.get("start_minimized", False))
            except (json.JSONDecodeError, KeyError):
                self._save_config()
        else:
            self._save_config()

    def _save_config(self) -> None:
        """Persist the current configuration to disk."""
        data: dict[str, Any] = {
            "remember_last_server": self.remember_last_server,
            "last_server_name": self.last_server_name,
            "autostart_xray": self.autostart_xray,
            "close_to_tray": self.close_to_tray,
            "start_minimized": self.start_minimized,
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)

    def is_valid(self) -> bool:
        """Check whether the VLESS directory exists and is a directory."""
        return VLESS_DIR.exists() and VLESS_DIR.is_dir()

    def set_close_to_tray(self, value: bool) -> None:
        """Enable or disable the close-to-tray behaviour."""
        self.close_to_tray = value
        self._save_config()

    def get_close_to_tray(self) -> bool:
        """Return whether the close-to-tray option is enabled."""
        return self.close_to_tray

    def set_start_minimized(self, value: bool) -> None:
        """Enable or disable the start-minimized behaviour."""
        self.start_minimized = value
        self._save_config()

    def get_start_minimized(self) -> bool:
        """Return whether the start-minimized option is enabled."""
        return self.start_minimized
