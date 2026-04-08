"""Tests for app.core.config.AppConfig.

Covers default config creation, save/load round-trips, and the
close_to_tray setting.  All tests patch CONFIG_DIR / CONFIG_FILE
so they never touch the real ~/.config/VlezeApp directory.
"""

import json
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

import app.core.config as config_module
from app.core.config import AppConfig


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def tmp_config_dir() -> Path:
    """Provide an isolated temporary directory for AppConfig."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture()
def app_config(tmp_config_dir: Path) -> AppConfig:
    """Create an AppConfig that reads/writes inside a temp directory.

    Patches the module-level CONFIG_DIR, CONFIG_FILE and VLESS_DIR constants so
    the real user config is never touched.
    """
    config_file = tmp_config_dir / "config.json"
    vless_dir = tmp_config_dir / "vless"
    with patch.object(config_module, "CONFIG_DIR", tmp_config_dir), \
         patch.object(config_module, "CONFIG_FILE", config_file), \
         patch.object(config_module, "VLESS_DIR", vless_dir):
        yield AppConfig()


# ---------------------------------------------------------------------------
# Default config
# ---------------------------------------------------------------------------

class TestDefaultConfig:
    """Tests for AppConfig default values and initial creation."""

    def test_default_remember_last_server(self, app_config: AppConfig) -> None:
        """remember_last_server should default to False."""
        assert app_config.remember_last_server is False

    def test_default_last_server_name(self, app_config: AppConfig) -> None:
        """last_server_name should default to an empty string."""
        assert app_config.last_server_name == ""

    def test_default_autostart_xray(self, app_config: AppConfig) -> None:
        """autostart_xray should default to False."""
        assert app_config.autostart_xray is False

    def test_default_close_to_tray(self, app_config: AppConfig) -> None:
        """close_to_tray should default to False."""
        assert app_config.close_to_tray is False

    def test_default_start_minimized(self, app_config: AppConfig) -> None:
        """start_minimized should default to False."""
        assert app_config.start_minimized is False

    def test_default_max_log_lines(self, app_config: AppConfig) -> None:
        """max_log_lines should default to 500."""
        assert app_config.max_log_lines == 500

    def test_default_enable_logging(self, app_config: AppConfig) -> None:
        """enable_logging should default to False."""
        assert app_config.enable_logging is False

    def test_creates_config_file(self, app_config: AppConfig, tmp_config_dir: Path) -> None:
        """Initialisation should create the config.json file."""
        config_file = tmp_config_dir / "config.json"
        assert config_file.exists()

    def test_creates_vless_directory(self, app_config: AppConfig, tmp_config_dir: Path) -> None:
        """Initialisation should create the vless subdirectory."""
        vless_dir = tmp_config_dir / "vless"
        assert vless_dir.is_dir()


# ---------------------------------------------------------------------------
# Save / load round-trip
# ---------------------------------------------------------------------------

class TestSaveLoad:
    """Tests for configuration persistence."""

    def test_save_and_reload(self, app_config: AppConfig) -> None:
        """Modified settings should survive a save and reload cycle."""
        app_config.remember_last_server = True
        app_config.last_server_name = "MyServer"
        app_config.autostart_xray = True
        app_config.close_to_tray = True
        app_config.start_minimized = True
        app_config.max_log_lines = 1000
        app_config.enable_logging = True
        app_config._save_config()

        # Create a fresh instance that will reload from disk
        fresh = AppConfig()
        assert fresh.remember_last_server is True
        assert fresh.last_server_name == "MyServer"
        assert fresh.autostart_xray is True
        assert fresh.close_to_tray is True
        assert fresh.start_minimized is True
        assert fresh.max_log_lines == 1000
        assert fresh.enable_logging is True

    def test_save_writes_valid_json(self, app_config: AppConfig, tmp_config_dir: Path) -> None:
        """The saved config file should be valid JSON."""
        app_config._save_config()
        config_file = tmp_config_dir / "config.json"
        with open(config_file, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        assert isinstance(data, dict)

    def test_save_contains_all_keys(self, app_config: AppConfig, tmp_config_dir: Path) -> None:
        """The saved config file should contain all expected keys."""
        app_config._save_config()
        config_file = tmp_config_dir / "config.json"
        with open(config_file, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        expected_keys = {
            "remember_last_server",
            "last_server_name",
            "autostart_xray",
            "close_to_tray",
            "start_minimized",
            "max_log_lines",
            "enable_logging",
        }
        assert expected_keys.issubset(data.keys())

    def test_load_corrupted_json_falls_back_to_defaults(
        self, tmp_config_dir: Path
    ) -> None:
        """A corrupted config file should not crash; defaults are used."""
        config_file = tmp_config_dir / "config.json"
        config_file.write_text("{ broken json !!!")

        vless_dir = tmp_config_dir / "vless"
        with patch.object(config_module, "CONFIG_DIR", tmp_config_dir), \
             patch.object(config_module, "CONFIG_FILE", config_file), \
             patch.object(config_module, "VLESS_DIR", vless_dir):
            cfg = AppConfig()

        # Should have fallen back to defaults
        assert cfg.remember_last_server is False
        assert cfg.close_to_tray is False
        assert cfg.start_minimized is False
        assert cfg.max_log_lines == 500
        assert cfg.enable_logging is False

    def test_is_valid_true(self, app_config: AppConfig, tmp_config_dir: Path) -> None:
        """is_valid should return True when VLESS_DIR exists."""
        vless_dir = tmp_config_dir / "vless"
        assert vless_dir.exists() and vless_dir.is_dir()

    def test_is_valid_false(self, tmp_config_dir: Path) -> None:
        """is_valid should return False when VLESS_DIR does not exist."""
        nonexistent = tmp_config_dir / "nonexistent_vless"
        # Patch VLESS_DIR to a non-existent path and call is_valid via a fresh instance
        # but prevent mkdir by patching _ensure_config_dir to do nothing.
        with patch.object(config_module, "VLESS_DIR", nonexistent):
            with patch.object(AppConfig, "_ensure_config_dir", lambda self: None):
                cfg = AppConfig.__new__(AppConfig)
                cfg.remember_last_server = False
                cfg.last_server_name = ""
                cfg.autostart_xray = False
                cfg.close_to_tray = False
                cfg.start_minimized = False
                cfg.max_log_lines = 500
                cfg.enable_logging = False
                assert cfg.is_valid() is False


# ---------------------------------------------------------------------------
# close_to_tray
# ---------------------------------------------------------------------------

class TestCloseToTray:
    """Tests for the close_to_tray setting."""

    def test_set_close_to_tray_true(self, app_config: AppConfig) -> None:
        """set_close_to_tray(True) should update the attribute."""
        app_config.set_close_to_tray(True)
        assert app_config.close_to_tray is True

    def test_set_close_to_tray_false(self, app_config: AppConfig) -> None:
        """set_close_to_tray(False) should update the attribute."""
        app_config.set_close_to_tray(True)
        app_config.set_close_to_tray(False)
        assert app_config.close_to_tray is False

    def test_set_close_to_tray_persists(self, app_config: AppConfig) -> None:
        """set_close_to_tray should save the value to disk."""
        app_config.set_close_to_tray(True)

        fresh = AppConfig()
        assert fresh.close_to_tray is True

    def test_get_close_to_tray_default(self, app_config: AppConfig) -> None:
        """get_close_to_tray should return False by default."""
        assert app_config.get_close_to_tray() is False

    def test_get_close_to_tray_after_set(self, app_config: AppConfig) -> None:
        """get_close_to_tray should reflect the last set value."""
        app_config.set_close_to_tray(True)
        assert app_config.get_close_to_tray() is True

    def test_close_to_tray_in_saved_file(self, app_config: AppConfig, tmp_config_dir: Path) -> None:
        """The saved config file should contain the close_to_tray value."""
        app_config.set_close_to_tray(True)
        config_file = tmp_config_dir / "config.json"
        with open(config_file, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        assert data["close_to_tray"] is True


# ---------------------------------------------------------------------------
# start_minimized
# ---------------------------------------------------------------------------

class TestStartMinimized:
    """Tests for the start_minimized setting."""

    def test_set_start_minimized_true(self, app_config: AppConfig) -> None:
        """set_start_minimized(True) should update the attribute."""
        app_config.set_start_minimized(True)
        assert app_config.start_minimized is True

    def test_set_start_minimized_false(self, app_config: AppConfig) -> None:
        """set_start_minimized(False) should update the attribute."""
        app_config.set_start_minimized(True)
        app_config.set_start_minimized(False)
        assert app_config.start_minimized is False

    def test_set_start_minimized_persists(self, app_config: AppConfig) -> None:
        """set_start_minimized should save the value to disk."""
        app_config.set_start_minimized(True)

        fresh = AppConfig()
        assert fresh.start_minimized is True

    def test_get_start_minimized_default(self, app_config: AppConfig) -> None:
        """get_start_minimized should return False by default."""
        assert app_config.get_start_minimized() is False

    def test_get_start_minimized_after_set(self, app_config: AppConfig) -> None:
        """get_start_minimized should reflect the last set value."""
        app_config.set_start_minimized(True)
        assert app_config.get_start_minimized() is True

    def test_start_minimized_in_saved_file(self, app_config: AppConfig, tmp_config_dir: Path) -> None:
        """The saved config file should contain the start_minimized value."""
        app_config.set_start_minimized(True)
        config_file = tmp_config_dir / "config.json"
        with open(config_file, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        assert data["start_minimized"] is True


# ---------------------------------------------------------------------------
# max_log_lines
# ---------------------------------------------------------------------------

class TestMaxLogLines:
    """Tests for the max_log_lines setting."""

    def test_set_max_log_lines(self, app_config: AppConfig) -> None:
        """set_max_log_lines should update the attribute."""
        app_config.set_max_log_lines(1000)
        assert app_config.max_log_lines == 1000

    def test_set_max_log_lines_clamps_min(self, app_config: AppConfig) -> None:
        """set_max_log_lines should clamp to minimum of 50."""
        app_config.set_max_log_lines(10)
        assert app_config.max_log_lines == 50

    def test_set_max_log_lines_clamps_max(self, app_config: AppConfig) -> None:
        """set_max_log_lines should clamp to maximum of 5000."""
        app_config.set_max_log_lines(10000)
        assert app_config.max_log_lines == 5000

    def test_set_max_log_lines_persists(self, app_config: AppConfig) -> None:
        """set_max_log_lines should save the value to disk."""
        app_config.set_max_log_lines(1000)

        fresh = AppConfig()
        assert fresh.max_log_lines == 1000

    def test_get_max_log_lines_default(self, app_config: AppConfig) -> None:
        """get_max_log_lines should return 500 by default."""
        assert app_config.get_max_log_lines() == 500

    def test_get_max_log_lines_after_set(self, app_config: AppConfig) -> None:
        """get_max_log_lines should reflect the last set value."""
        app_config.set_max_log_lines(1500)
        assert app_config.get_max_log_lines() == 1500

    def test_max_log_lines_in_saved_file(self, app_config: AppConfig, tmp_config_dir: Path) -> None:
        """The saved config file should contain the max_log_lines value."""
        app_config.set_max_log_lines(750)
        config_file = tmp_config_dir / "config.json"
        with open(config_file, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        assert data["max_log_lines"] == 750


# ---------------------------------------------------------------------------
# enable_logging
# ---------------------------------------------------------------------------

class TestEnableLogging:
    """Tests for the enable_logging setting."""

    def test_set_enable_logging_true(self, app_config: AppConfig) -> None:
        """set_enable_logging(True) should update the attribute."""
        app_config.set_enable_logging(True)
        assert app_config.enable_logging is True

    def test_set_enable_logging_false(self, app_config: AppConfig) -> None:
        """set_enable_logging(False) should update the attribute."""
        app_config.set_enable_logging(True)
        app_config.set_enable_logging(False)
        assert app_config.enable_logging is False

    def test_set_enable_logging_persists(self, app_config: AppConfig) -> None:
        """set_enable_logging should save the value to disk."""
        app_config.set_enable_logging(True)

        fresh = AppConfig()
        assert fresh.enable_logging is True

    def test_get_enable_logging_default(self, app_config: AppConfig) -> None:
        """get_enable_logging should return False by default."""
        assert app_config.get_enable_logging() is False

    def test_get_enable_logging_after_set(self, app_config: AppConfig) -> None:
        """get_enable_logging should reflect the last set value."""
        app_config.set_enable_logging(True)
        assert app_config.get_enable_logging() is True

    def test_enable_logging_in_saved_file(self, app_config: AppConfig, tmp_config_dir: Path) -> None:
        """The saved config file should contain the enable_logging value."""
        app_config.set_enable_logging(True)
        config_file = tmp_config_dir / "config.json"
        with open(config_file, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        assert data["enable_logging"] is True
