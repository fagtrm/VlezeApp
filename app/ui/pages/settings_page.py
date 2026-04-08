"""
SettingsPage — страница настроек приложения.

Поля:
    - remember_last_server
    - autostart_xray
    - close_to_tray
    - start_minimized

Методы:
    get_remember_last_server() -> bool
    get_autostart_xray()       -> bool
    get_close_to_tray()        -> bool
    get_start_minimized()      -> bool
"""
from __future__ import annotations

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gio", "2.0")
from gi.repository import Gtk, Adw, Gio, GObject

from app.i18n import _


class SettingsPage(Gtk.Box):
    """Страница настроек приложения."""

    __gsignals__ = {
        "settings-saved": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, app_config) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_start(24)
        self.set_margin_end(24)
        self.set_margin_top(24)
        self.set_margin_bottom(24)
        self.app_config = app_config

        # Заголовок
        title: Gtk.Label = Gtk.Label(label=_("Settings"))
        title.set_halign(Gtk.Align.START)
        title.add_css_class("title-1")
        self.append(title)

        # ── Группа: Основные ──────────────────────────────────────────────
        general_group: Adw.PreferencesGroup = Adw.PreferencesGroup()
        general_group.set_title(_("General"))
        general_group.set_hexpand(True)

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

        # Чекбокс: запуск свёрнутым в трей
        self.start_minimized_row: Adw.SwitchRow = Adw.SwitchRow()
        self.start_minimized_row.set_title(_("Start minimized to tray"))
        self.start_minimized_row.set_subtitle(_("Application will start hidden in the system tray"))
        self.start_minimized_row.set_active(app_config.start_minimized)
        general_group.add(self.start_minimized_row)

        # Спиннер: максимальное количество строк логов
        self.max_log_lines_row: Adw.SpinRow = Adw.SpinRow(
            adjustment=Gtk.Adjustment.new(
                app_config.max_log_lines, 50, 5000, 50, 100, 0
            )
        )
        self.max_log_lines_row.set_title(_("Maximum log lines"))
        self.max_log_lines_row.set_subtitle(_("Number of recent log lines kept in memory"))
        general_group.add(self.max_log_lines_row)

        # Чекбокс: включить логирование
        self.enable_logging_row: Adw.SwitchRow = Adw.SwitchRow()
        self.enable_logging_row.set_title(_("Enable xray logging"))
        self.enable_logging_row.set_subtitle(_("Write xray output to log file with rotation"))
        self.enable_logging_row.set_active(app_config.enable_logging)
        general_group.add(self.enable_logging_row)

        self.append(general_group)

        # Кнопка сохранения
        save_btn: Gtk.Button = Gtk.Button.new_with_label(_("Save"))
        save_btn.add_css_class("suggested-action")
        save_btn.set_halign(Gtk.Align.START)
        save_btn.set_margin_top(12)
        save_btn.connect("clicked", self._on_save)
        self.append(save_btn)

    # ── Внутренние обработчики ────────────────────────────────────────────

    def _on_save(self, btn: Gtk.Button) -> None:
        """Сохранить настройки."""
        self.app_config.remember_last_server = self.get_remember_last_server()
        self.app_config.autostart_xray = self.get_autostart_xray()
        self.app_config.close_to_tray = self.get_close_to_tray()
        self.app_config.start_minimized = self.get_start_minimized()
        self.app_config.max_log_lines = self.get_max_log_lines()
        self.app_config.enable_logging = self.get_enable_logging()
        self.app_config._save_config()
        self.emit("settings-saved")

    # ── Публичный API ─────────────────────────────────────────────────────

    def get_remember_last_server(self) -> bool:
        return self.remember_row.get_active()

    def get_autostart_xray(self) -> bool:
        return self.autostart_row.get_active()

    def get_close_to_tray(self) -> bool:
        return self.close_to_tray_row.get_active()

    def get_start_minimized(self) -> bool:
        return self.start_minimized_row.get_active()

    def get_max_log_lines(self) -> int:
        return int(self.max_log_lines_row.get_value())

    def get_enable_logging(self) -> bool:
        return self.enable_logging_row.get_active()
