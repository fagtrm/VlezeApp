"""
ConfigsPage — страница списка VLESS-конфигураций.

Кнопки загрузки URL и выбора файла, список конфигов с подсветкой
подключённого сервера.

Методы:
    populate_configs(entries)  — заполнить список записями.
    get_selected_entry()       — вернуть выбранную запись.
    highlight_connected(entry) — подсветить подключённый сервер.
"""
from __future__ import annotations

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk

from app.i18n import _
from app.ui.widgets.config_row import ConfigRow

# CSS для выделения подключённой строки
_CONNECTED_CSS = """
    .connected-row {
        background-color: alpha(#4e9a06, 0.25);
    }
    .connected-row:selected {
        background-color: alpha(#4e9a06, 0.45);
    }
"""


class ConfigsPage(Gtk.Box):
    """Страница списка конфигов."""

    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_start(12)
        self.set_margin_end(12)
        self.set_margin_top(12)
        self.set_margin_bottom(12)

        # Применяем CSS для connected-row
        css_provider: Gtk.CssProvider = Gtk.CssProvider()
        css_provider.load_from_string(_CONNECTED_CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css_provider, Gtk.STYLE_PROVIDER_PRIORITY_USER
        )

        # ── Поле загрузки ─────────────────────────────────────────────────
        load_box: Gtk.Box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        load_box.set_hexpand(True)

        self.url_entry: Gtk.Entry = Gtk.Entry()
        self.url_entry.set_placeholder_text(_("Paste a URL to download a base64 config..."))
        self.url_entry.set_hexpand(True)
        load_box.append(self.url_entry)

        # Кнопка загрузки
        self.download_btn: Gtk.Button = Gtk.Button.new_from_icon_name("folder-download-symbolic")
        self.download_btn.set_tooltip_text(_("Download from the internet"))
        load_box.append(self.download_btn)

        # Кнопка выбора файла
        self.file_btn: Gtk.Button = Gtk.Button.new_from_icon_name("list-add-symbolic")
        self.file_btn.set_tooltip_text(_("Select a file from computer"))
        load_box.append(self.file_btn)

        self.append(load_box)

        # ── Список конфигов ───────────────────────────────────────────────
        self.config_list: Gtk.ListBox = Gtk.ListBox()
        self.config_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.config_list.add_css_class("boxed-list")

        scrolled: Gtk.ScrolledWindow = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_child(self.config_list)
        self.append(scrolled)

        # Пустое состояние
        self.empty_label: Gtk.Label = Gtk.Label(
            label=_("No configs found. Download a base64 file to create a config.")
        )
        self.empty_label.set_opacity(0.5)
        self.empty_label.set_margin_top(40)
        self.append(self.empty_label)

    # ── Публичный API ─────────────────────────────────────────────────────

    def populate_configs(self, entries: list[dict]) -> None:
        """Заполняет список конфигов."""
        # Очищаем
        while child := self.config_list.get_row_at_index(0):
            self.config_list.remove(child)

        if not entries:
            self.empty_label.set_visible(True)
            return

        self.empty_label.set_visible(False)

        for entry in entries:
            row: ConfigRow = ConfigRow(entry)
            self.config_list.append(row)

    def get_selected_entry(self) -> dict | None:
        """Возвращает выбранную запись."""
        selected = self.config_list.get_selected_row()
        if selected and hasattr(selected, "entry"):
            return selected.entry
        return None

    def highlight_connected(self, entry: dict | None) -> None:
        """Подсвечивает подключённую строку зелёным фоном."""
        row = self.config_list.get_row_at_index(0)
        while row:
            if hasattr(row, "entry"):
                row.set_connected(row.entry is entry)
            next_idx = row.get_index() + 1
            row = self.config_list.get_row_at_index(next_idx)
