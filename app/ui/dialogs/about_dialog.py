"""
AboutDialog — окно «О программе».

Слева логотип, справа — название, версия и краткое описание.
"""
from __future__ import annotations

import os
from pathlib import Path

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from app.i18n import _

# Версия приложения
APP_VERSION = "0.1.0"

# Пути к логотипам относительно корня проекта
_BASE_DIR = Path(__file__).parent.parent.parent.parent
_LOGO_LIGHT = str(_BASE_DIR / "data" / "logo_light.jpg")
_LOGO_DARK = str(_BASE_DIR / "data" / "logo_dark.jpg")


class AboutDialog(Gtk.Window):
    """Диалог «О программе»."""

    def __init__(self, parent: Gtk.Window) -> None:
        super().__init__(
            title=_("About VlezeApp"),
            transient_for=parent,
            modal=True,
            default_width=420,
            default_height=280,
        )
        self.set_resizable(False)

        # Определяем тему через Adw.StyleManager
        style_manager = Adw.StyleManager.get_default()
        is_dark = style_manager.get_dark()

        logo_path = _LOGO_DARK if is_dark else _LOGO_LIGHT

        # Основной контейер
        main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=24)
        main_box.set_margin_start(24)
        main_box.set_margin_end(24)
        main_box.set_margin_top(24)
        main_box.set_margin_bottom(24)

        # Логотип слева
        logo = Gtk.Picture.new_for_filename(logo_path)
        logo.set_content_fit(Gtk.ContentFit.SCALE_DOWN)
        logo.set_size_request(100, 100)
        logo.set_halign(Gtk.Align.CENTER)
        logo.set_valign(Gtk.Align.START)
        main_box.append(logo)

        # Текст справа
        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        text_box.set_vexpand(True)

        # Название
        title_label = Gtk.Label(label="VlezeApp")
        title_label.set_halign(Gtk.Align.START)
        title_label.add_css_class("title-2")
        text_box.append(title_label)

        # Версия
        version_label = Gtk.Label(label=f"v{APP_VERSION}")
        version_label.set_halign(Gtk.Align.START)
        version_label.add_css_class("dim-label")
        text_box.append(version_label)

        # Описание
        desc_label = Gtk.Label(
            label=_(
                "Desktop VLESS VPN manager built with GTK4/Libadwaita.\n"
                "Parse vless:// links, generate Xray configs, and manage connections."
            )
        )
        desc_label.set_halign(Gtk.Align.START)
        desc_label.set_valign(Gtk.Align.START)
        desc_label.set_wrap(True)
        desc_label.set_max_width_chars(35)
        text_box.append(desc_label)

        main_box.append(text_box)

        self.set_child(main_box)
