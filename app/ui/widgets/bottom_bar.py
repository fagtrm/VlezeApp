"""
BottomBar — нижняя панель с кнопкой Старт/Стоп.

Одна кнопка-переключатель, меняющая вид и текст
в зависимости от состояния xray-процесса.
"""
from __future__ import annotations

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from app.i18n import _


class BottomBar(Gtk.Box):
    """Нижняя панель Старт/Стоп — одна кнопка."""

    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.set_margin_start(24)
        self.set_margin_end(24)
        self.set_margin_top(6)
        self.set_margin_bottom(6)
        self.add_css_class("toolbar")

        self.is_running: bool = False

        self.toggle_btn: Gtk.Button = Gtk.Button.new_with_label("\u25b6 " + _("Start"))
        self.toggle_btn.add_css_class("suggested-action")
        self.toggle_btn.set_hexpand(True)
        self.toggle_btn.set_sensitive(False)
        self.append(self.toggle_btn)

    def set_config_selected(self, selected: bool) -> None:
        """Активирует кнопку если конфиг выбран."""
        if not self.is_running:
            self.toggle_btn.set_sensitive(selected)

    def set_running(self, running: bool) -> None:
        """Обновляет состояние кнопки."""
        self.is_running = running
        if running:
            self.toggle_btn.set_label("\u23f9 " + _("Stop"))
            self.toggle_btn.remove_css_class("suggested-action")
            self.toggle_btn.add_css_class("destructive-action")
            self.toggle_btn.set_sensitive(True)
        else:
            self.toggle_btn.set_label("\u25b6 " + _("Start"))
            self.toggle_btn.remove_css_class("destructive-action")
            self.toggle_btn.add_css_class("suggested-action")
            self.toggle_btn.set_sensitive(True)
