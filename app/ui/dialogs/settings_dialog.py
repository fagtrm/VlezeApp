"""
SettingsDialog — диалог настроек приложения.

Поля:
    - remember_last_server
    - autostart_xray
    - close_to_tray

Методы:
    get_remember_last_server() -> bool
    get_autostart_xray()       -> bool
    get_close_to_tray()        -> bool
"""
from __future__ import annotations

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from app.i18n import _


class SettingsDialog(Adw.PreferencesDialog):
    """Диалог настроек приложения."""

    def __init__(self, app_config, parent: Gtk.Window) -> None:
        super().__init__()
        self.set_title(_("Settings"))
        self.app_config = app_config

        # ── Группа: Основные ──────────────────────────────────────────────
        general_group: Adw.PreferencesGroup = Adw.PreferencesGroup()
        general_group.set_title(_("General"))

        # Чекбокс: запоминать последний сервер
        self.remember_row: Adw.SwitchRow = Adw.SwitchRow()
        self.remember_row.set_title(_("Remember last selected server"))
        self.remember_row.set_active(app_config.remember_last_server)
        general_group.add(self.remember_row)

        # Чекбокс: автозапуск xray
        self.autostart_row: Adw.SwitchRow = Adw.SwitchRow()
        self.autostart_row.set_title(_("Launch xray immediately after app start"))
        self.autostart_row.set_subtitle(_("If a server is selected"))
        self.autostart_row.set_active(app_config.autostart_xray)
        general_group.add(self.autostart_row)

        # Чекбокс: закрытие сворачивает в трей
        self.close_to_tray_row: Adw.SwitchRow = Adw.SwitchRow()
        self.close_to_tray_row.set_title(_("Close minimizes to tray"))
        self.close_to_tray_row.set_subtitle(_("When closing the window, it hides to the system tray"))
        self.close_to_tray_row.set_active(app_config.close_to_tray)
        general_group.add(self.close_to_tray_row)

        # ── Страница ──────────────────────────────────────────────────────
        page: Adw.PreferencesPage = Adw.PreferencesPage()
        page.add(general_group)
        self.add(page)

    # ── Публичный API ─────────────────────────────────────────────────────

    def get_remember_last_server(self) -> bool:
        return self.remember_row.get_active()

    def get_autostart_xray(self) -> bool:
        return self.autostart_row.get_active()

    def get_close_to_tray(self) -> bool:
        return self.close_to_tray_row.get_active()
