"""Tests for app.core.config_store.ConfigStore.

Covers adding entries, reading configs, and changing the config directory.
"""

import json
import tempfile
from pathlib import Path
from typing import Any

import pytest

from app.core.config_store import ConfigStore


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def tmp_vless_dir() -> Path:
    """Provide an empty temporary directory for config files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture()
def store(tmp_vless_dir: Path) -> ConfigStore:
    """Create a ConfigStore backed by a temporary directory."""
    return ConfigStore(tmp_vless_dir)


def _sample_entry(num: int = 1) -> dict[str, Any]:
    """Return a minimal parsed VLESS entry for testing."""
    return {
        "num": num,
        "id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "host": "server.example.com",
        "port": "443",
        "type": "tcp",
        "path": "/",
        "security": "tls",
        "name": "TestServer",
        "icon": "\U0001F310",
    }


# ---------------------------------------------------------------------------
# test_add_entries
# ---------------------------------------------------------------------------

class TestAddEntries:
    """Tests for ConfigStore.add_entries()."""

    def test_add_creates_new_file(self, store: ConfigStore) -> None:
        """Adding entries to a non-existent config should create the file."""
        entries = [_sample_entry(num=1)]
        path = store.add_entries(entries, "myconfig")

        assert path.exists()
        assert path.name == "myconfig.json"

    def test_add_writes_valid_json(self, store: ConfigStore) -> None:
        """The created file should be valid JSON with an 'entries' key."""
        entries = [_sample_entry(num=1)]
        path = store.add_entries(entries, "myconfig")

        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)

        assert "entries" in data
        assert len(data["entries"]) == 1

    def test_add_assigns_numbers(self, store: ConfigStore) -> None:
        """Entries should be assigned sequential num values starting at 1."""
        entries = [_sample_entry(), _sample_entry(), _sample_entry()]
        store.add_entries(entries, "numbered")

        configs = store.get_configs()
        assert len(configs) == 1
        saved_entries = configs[0]["data"]["entries"]
        assert saved_entries[0]["num"] == 1
        assert saved_entries[1]["num"] == 2
        assert saved_entries[2]["num"] == 3

    def test_add_appends_to_existing(self, store: ConfigStore) -> None:
        """Adding entries to an existing config should append, not overwrite."""
        store.add_entries([_sample_entry(num=1)], "shared")
        store.add_entries([_sample_entry(num=2)], "shared")

        configs = store.get_configs()
        assert len(configs) == 1
        saved = configs[0]["data"]["entries"]
        assert len(saved) == 2
        assert saved[0]["num"] == 1
        assert saved[1]["num"] == 2

    def test_add_returns_path(self, store: ConfigStore) -> None:
        """add_entries should return the path to the written file."""
        path = store.add_entries([_sample_entry()], "rettest")
        assert isinstance(path, Path)
        assert path == store.vless_dir / "rettest.json"

    def test_add_multiple_configs(self, store: ConfigStore) -> None:
        """Adding entries under different names should create separate files."""
        store.add_entries([_sample_entry(num=1)], "alpha")
        store.add_entries([_sample_entry(num=1)], "beta")

        configs = store.get_configs()
        assert len(configs) == 2
        names = {c["name"] for c in configs}
        assert names == {"alpha", "beta"}


# ---------------------------------------------------------------------------
# test_get_configs (reading)
# ---------------------------------------------------------------------------

class TestGetConfigs:
    """Tests for ConfigStore.get_configs() / reading configs."""

    def test_empty_directory(self, store: ConfigStore) -> None:
        """An empty vless directory should yield an empty configs list."""
        assert store.get_configs() == []

    def test_reads_existing_json(self, tmp_vless_dir: Path) -> None:
        """A pre-existing JSON file with 'entries' should be loaded."""
        config_file = tmp_vless_dir / "preloaded.json"
        data = {"entries": [{"num": 1, "name": "Preloaded"}]}
        with open(config_file, "w", encoding="utf-8") as fh:
            json.dump(data, fh)

        store = ConfigStore(tmp_vless_dir)
        configs = store.get_configs()

        assert len(configs) == 1
        assert configs[0]["name"] == "preloaded"
        assert configs[0]["path"] == config_file
        assert configs[0]["data"] == data

    def test_ignores_json_without_entries(self, tmp_vless_dir: Path) -> None:
        """JSON files without an 'entries' key should be ignored."""
        config_file = tmp_vless_dir / "not_a_config.json"
        with open(config_file, "w", encoding="utf-8") as fh:
            json.dump({"something": "else"}, fh)

        store = ConfigStore(tmp_vless_dir)
        assert store.get_configs() == []

    def test_ignores_invalid_json(self, tmp_vless_dir: Path) -> None:
        """Corrupted JSON files should be silently skipped."""
        config_file = tmp_vless_dir / "broken.json"
        with open(config_file, "w", encoding="utf-8") as fh:
            fh.write("{ not valid json !!!")

        store = ConfigStore(tmp_vless_dir)
        assert store.get_configs() == []

    def test_non_json_files_ignored(self, tmp_vless_dir: Path) -> None:
        """Non-JSON files in the directory should not be loaded."""
        (tmp_vless_dir / "readme.txt").write_text("hello")
        (tmp_vless_dir / "config.json").write_text(
            json.dumps({"entries": [{"num": 1}]})
        )

        store = ConfigStore(tmp_vless_dir)
        assert len(store.get_configs()) == 1
        assert store.get_configs()[0]["name"] == "config"

    def test_configs_sorted_by_filename(self, tmp_vless_dir: Path) -> None:
        """Configs should be returned sorted by filename."""
        for name in ("charlie", "alpha", "bravo"):
            path = tmp_vless_dir / f"{name}.json"
            with open(path, "w", encoding="utf-8") as fh:
                json.dump({"entries": []}, fh)

        store = ConfigStore(tmp_vless_dir)
        names = [c["name"] for c in store.get_configs()]
        assert names == ["alpha", "bravo", "charlie"]


# ---------------------------------------------------------------------------
# test_set_vless_dir (changing directory)
# ---------------------------------------------------------------------------

class TestSetVlessDir:
    """Tests for ConfigStore.set_vless_dir()."""

    def test_change_directory(self, store: ConfigStore, tmp_vless_dir: Path) -> None:
        """set_vless_dir should update the store's vless_dir attribute."""
        with tempfile.TemporaryDirectory() as new_tmp:
            new_dir = Path(new_tmp)
            store.set_vless_dir(new_dir)
            assert store.vless_dir == new_dir

    def test_reload_on_dir_change(self, store: ConfigStore) -> None:
        """Changing directory should reload configs from the new location."""
        # Add a config to the original directory
        store.add_entries([_sample_entry(num=1)], "original")
        assert len(store.get_configs()) == 1

        # Switch to a fresh empty directory
        with tempfile.TemporaryDirectory() as new_tmp:
            store.set_vless_dir(Path(new_tmp))
            assert store.get_configs() == []

    def test_nonexistent_directory(self, store: ConfigStore) -> None:
        """Setting a non-existent directory should result in empty configs."""
        fake_dir = Path("/tmp/does-not-exist-vlezeapp-test")
        store.set_vless_dir(fake_dir)
        assert store.get_configs() == []
        assert store.vless_dir == fake_dir
