"""
Configuration store for VlezeApp.

Manages the collection of saved VLESS server configurations stored
as JSON files on disk.  Handles loading, adding entries, and
directory changes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.i18n import _


class ConfigStore:
    """Stores and manages VLESS configuration files on disk.

    Each configuration file is a JSON object with an "entries" key
    containing a list of parsed VLESS server entries.

    Attributes:
        vless_dir: The directory where configuration JSON files live.
        configs: The currently loaded list of configuration dicts.
    """

    def __init__(self, vless_dir: Path) -> None:
        """Initialise the store and load existing configurations.

        Args:
            vless_dir: Path to the directory containing config JSON files.
        """
        self.vless_dir: Path = vless_dir
        self.configs: list[dict[str, Any]] = []
        self._load_configs()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load_configs(self) -> None:
        """Load all *.json files from the vless directory that contain
        an "entries" key.
        """
        self.configs = []
        if not self.vless_dir.exists():
            return

        for json_file in sorted(self.vless_dir.glob("*.json")):
            try:
                with open(json_file, "r", encoding="utf-8") as fh:
                    data: dict[str, Any] = json.load(fh)
                    if "entries" in data:
                        self.configs.append({
                            "path": json_file,
                            "name": json_file.stem,
                            "data": data,
                        })
            except (json.JSONDecodeError, KeyError):
                continue

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_entries(self, entries: list[dict[str, Any]], config_name: str) -> Path:
        """Add parsed VLESS entries to a configuration file.

        Creates a new file or appends to an existing one.  Entry numbers
        are auto-assigned sequentially.

        Args:
            entries: List of parsed VLESS entry dictionaries.
            config_name: Base name for the configuration file (without .json).

        Returns:
            The path to the written configuration file.
        """
        config_path = self.vless_dir / f"{config_name}.json"

        existing_data: dict[str, Any] = {"entries": []}
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as fh:
                    existing_data = json.load(fh)
            except json.JSONDecodeError:
                existing_data = {"entries": []}

        start_num = len(existing_data["entries"]) + 1
        for i, entry in enumerate(entries):
            entry["num"] = start_num + i
            existing_data["entries"].append(entry)

        with open(config_path, "w", encoding="utf-8") as fh:
            json.dump(existing_data, fh, indent=2, ensure_ascii=False)

        self._load_configs()
        return config_path

    def get_configs(self) -> list[dict[str, Any]]:
        """Return the list of loaded configurations."""
        return self.configs

    def set_vless_dir(self, path: Path) -> None:
        """Change the configurations directory and reload.

        Args:
            path: The new directory path.
        """
        self.vless_dir = path
        self._load_configs()

    def delete_config(self, config_name: str) -> bool:
        """Delete a configuration file by name.

        Args:
            config_name: Name of the config (without .json extension).

        Returns:
            True if the file was deleted, False if it did not exist.
        """
        config_path = self.vless_dir / f"{config_name}.json"
        if config_path.exists():
            config_path.unlink()
            self._load_configs()
            return True
        return False
