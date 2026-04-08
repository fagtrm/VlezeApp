"""
ConfigRow — строка в списке VLESS-конфигураций.

Отображает иконку-флаг, имя сервера, порт, тип и безопасность.
Метод set_connected() подсвечивает активное подключение.
"""
from __future__ import annotations

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, GObject, Gdk

from app.i18n import _

# CSS для warning иконки
_WARNING_CSS = """
    image.warning {
        color: @warning_color;
    }
"""
_warning_applied = False


class ConfigRow(Gtk.ListBoxRow):
    """Строка в списке конфигов."""

    def __init__(self, entry: dict) -> None:
        global _warning_applied
        super().__init__()
        self.entry: dict = entry
        self.set_activatable(True)

        # Применяем CSS для warning один раз
        if not _warning_applied:
            display = Gdk.Display.get_default()
            if display:
                provider = Gtk.CssProvider()
                provider.load_from_string(_WARNING_CSS)
                Gtk.StyleContext.add_provider_for_display(
                    display, provider, Gtk.STYLE_PROVIDER_PRIORITY_USER
                )
                _warning_applied = True

        flag: str = entry.get("icon", "\U0001F310")
        name: str = entry.get("name", _("Unknown"))
        port: str = entry.get("port", "?")
        conn_type: str = entry.get("type", "tcp")
        security: str = entry.get("security", "none")

        # Экранируем спецсимволы для Pango markup
        title_text: str = GLib.markup_escape_text(f"{flag}  {name}", -1)
        subtitle_text: str = GLib.markup_escape_text(f"{port}, {conn_type}, {security}", -1)

        # Оборачиваем ActionRow в Box — это обходит баг GTK4 с grab_focus
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.set_margin_start(6)
        box.set_margin_end(6)
        box.set_margin_top(2)
        box.set_margin_bottom(2)

        self.action_row = Adw.ActionRow()
        self.action_row.set_title(title_text)
        self.action_row.set_subtitle(subtitle_text)

        # Иконка предупреждения (изменённые параметры)
        self.warning_icon: Gtk.Image = Gtk.Image.new_from_icon_name("dialog-warning-symbolic")
        self.warning_icon.set_visible(False)
        self.warning_icon.set_tooltip_text(_("Параметры изменены относительно исходной vless-ссылки"))
        self.warning_icon.add_css_class("warning")
        self.warning_icon.set_margin_end(4)
        self.action_row.add_prefix(self.warning_icon)

        box.append(self.action_row)
        self.set_child(box)

    def set_connected(self, connected: bool) -> None:
        """Выделяет строку зелёным фоном если подключена."""
        if connected:
            self.add_css_class("connected-row")
        else:
            self.remove_css_class("connected-row")

    def set_has_overrides(self, has_overrides: bool) -> None:
        """Показать/скрыть иконку предупреждения."""
        self.warning_icon.set_visible(has_overrides)
