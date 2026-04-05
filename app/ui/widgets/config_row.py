"""
ConfigRow — строка в списке VLESS-конфигураций.

Отображает иконку-флаг, имя сервера, порт, тип и безопасность.
Метод set_connected() подсвечивает активное подключение.
"""
from __future__ import annotations

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib

from app.i18n import _


class ConfigRow(Adw.ActionRow):
    """Строка в списке конфигов."""

    def __init__(self, entry: dict) -> None:
        super().__init__()
        self.entry: dict = entry
        self.set_activatable(True)

        flag: str = entry.get("icon", "\U0001F310")
        name: str = entry.get("name", _("Unknown"))
        port: str = entry.get("port", "?")
        conn_type: str = entry.get("type", "tcp")
        security: str = entry.get("security", "none")

        # Экранируем спецсимволы для Pango markup
        title_text: str = GLib.markup_escape_text(f"{flag}  {name}", -1)
        subtitle_text: str = GLib.markup_escape_text(f"{port}, {conn_type}, {security}", -1)

        self.set_title(title_text)
        self.set_subtitle(subtitle_text)

    def set_connected(self, connected: bool) -> None:
        """Выделяет строку зелёным фоном если подключена."""
        if connected:
            self.add_css_class("connected-row")
        else:
            self.remove_css_class("connected-row")
