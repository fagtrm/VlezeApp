"""
DashboardPage — главная страница со статусом VPN, активным конфигом и пингом.

Методы:
    update_status(is_connected, config_name) — обновить статус подключения.
    update_ping(success, message) — обновить отображение задержки.
"""
from __future__ import annotations

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from app.i18n import _


class DashboardPage(Gtk.Box):
    """Страница Dashboard."""

    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_start(24)
        self.set_margin_end(24)
        self.set_margin_top(24)
        self.set_margin_bottom(24)

        # Статус
        self.status_box: Gtk.Box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.status_box.set_halign(Gtk.Align.FILL)
        self.status_box.set_valign(Gtk.Align.START)
        self.status_box.set_hexpand(True)

        # Карточка статуса
        status_card: Adw.PreferencesGroup = Adw.PreferencesGroup()
        status_card.set_title(_("Status"))

        self.status_row: Adw.ActionRow = Adw.ActionRow()
        self.status_row.set_title(_("State"))
        self.status_row.set_subtitle(_("Not connected"))
        self.status_icon: Gtk.Image = Gtk.Image.new_from_icon_name("network-offline-symbolic")
        self.status_row.add_prefix(self.status_icon)
        status_card.add(self.status_row)

        self.config_row: Adw.ActionRow = Adw.ActionRow()
        self.config_row.set_title(_("Active config"))
        self.config_row.set_subtitle(_("Not selected"))
        config_icon: Gtk.Image = Gtk.Image.new_from_icon_name("document-open-recent-symbolic")
        self.config_row.add_prefix(config_icon)
        status_card.add(self.config_row)

        # Задержка (пинг)
        self.ping_row: Adw.ActionRow = Adw.ActionRow()
        self.ping_row.set_title(_("Latency (ping)"))
        self.ping_row.set_subtitle("\u2014")
        self.ping_icon: Gtk.Image = Gtk.Image.new_from_icon_name("view-refresh-symbolic")
        self.ping_row.add_prefix(self.ping_icon)
        status_card.add(self.ping_row)

        # Кнопка ручного пинга
        self.ping_btn: Gtk.Button = Gtk.Button.new_with_label(_("Check ping"))
        self.ping_btn.set_tooltip_text(_("Check latency via VPN"))
        self.ping_btn.set_halign(Gtk.Align.CENTER)
        self.ping_btn.set_margin_top(6)
        self.ping_btn.set_sensitive(False)
        status_card.add(self.ping_btn)

        self.status_box.append(status_card)
        self.append(self.status_box)

    # ── Публичный API ─────────────────────────────────────────────────────

    def update_status(self, is_connected: bool, config_name: str = "") -> None:
        """Обновляет статус на дашборде."""
        if is_connected:
            self.status_row.set_subtitle(_("Connected"))
            self.status_icon.set_from_icon_name("network-wired-symbolic")
            self.status_icon.add_css_class("success")
            self.ping_btn.set_sensitive(True)
        else:
            self.status_row.set_subtitle(_("Not connected"))
            self.status_icon.set_from_icon_name("network-offline-symbolic")
            self.status_icon.remove_css_class("success")
            self.ping_btn.set_sensitive(False)

        if config_name:
            self.config_row.set_subtitle(config_name)

    def update_ping(self, success: bool, message: str) -> None:
        """Обновляет отображение задержки."""
        self.ping_row.set_subtitle(message)
        if success:
            self.ping_icon.set_from_icon_name("view-refresh-symbolic")
            self.ping_icon.add_css_class("success")
            self.ping_icon.remove_css_class("error")
        else:
            self.ping_icon.set_from_icon_name("view-refresh-symbolic")
            self.ping_icon.add_css_class("error")
            self.ping_icon.remove_css_class("success")
