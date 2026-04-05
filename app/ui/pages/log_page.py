"""
LogPage — страница логов xray.

TextView с моноширинным шрифтом, кнопка очистки.

Методы:
    update_logs(log_lines) — обновить текст логов.
    clear()                — очистить логи.
"""
from __future__ import annotations

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk

from app.i18n import _


class LogPage(Gtk.Box):
    """Страница логов xray."""

    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_margin_start(12)
        self.set_margin_end(12)
        self.set_margin_top(12)
        self.set_margin_bottom(12)

        # ── Заголовок с кнопкой очистки ───────────────────────────────────
        header_box: Gtk.Box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header_box.set_hexpand(True)

        title: Gtk.Label = Gtk.Label(label=_("Xray logs"))
        title.set_halign(Gtk.Align.START)
        title.add_css_class("title-3")
        header_box.append(title)

        header_box.append(Gtk.Label())  # spacer

        self.clear_btn: Gtk.Button = Gtk.Button.new_from_icon_name("edit-clear-all-symbolic")
        self.clear_btn.set_tooltip_text(_("Clear logs"))
        header_box.append(self.clear_btn)

        self.append(header_box)

        # ── Текстовое поле логов ──────────────────────────────────────────
        self.log_buffer: Gtk.TextBuffer = Gtk.TextBuffer()
        self.log_buffer.set_text(_("Logs will appear after starting xray..."))

        self.log_view: Gtk.TextView = Gtk.TextView.new_with_buffer(self.log_buffer)
        self.log_view.set_editable(False)
        self.log_view.set_cursor_visible(False)
        self.log_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.log_view.set_monospace(True)
        self.log_view.set_left_margin(8)
        self.log_view.set_right_margin(8)
        self.log_view.set_top_margin(6)
        self.log_view.set_bottom_margin(6)

        # Моноширинный шрифт через CSS
        css: str = "textview { font-family: monospace; font-size: 11px; }"
        provider: Gtk.CssProvider = Gtk.CssProvider()
        provider.load_from_string(css)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        scrolled: Gtk.ScrolledWindow = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_child(self.log_view)
        self.append(scrolled)

        # Автоскролл
        self.auto_scroll: bool = True

        # Отслеживаем ручную прокрутку
        vadj = scrolled.get_vadjustment()
        vadj.connect("value-changed", self._on_scroll)

    # ── Публичный API ─────────────────────────────────────────────────────

    def update_logs(self, log_lines: list[str]) -> None:
        """Обновляет текст логов."""
        text: str = "\n".join(log_lines) if log_lines else _("Logs are empty...")
        self.log_buffer.set_text(text)

        # Скролл вниз
        if self.auto_scroll:
            end_iter = self.log_buffer.get_end_iter()
            mark = self.log_buffer.create_mark(None, end_iter, False)
            self.log_view.scroll_to_mark(mark, 0.0, True, 0.0, 1.0)

    def clear(self) -> None:
        """Очищает логи."""
        self.log_buffer.set_text("")

    # ── Внутренние методы ─────────────────────────────────────────────────

    def _on_scroll(self, vadj) -> None:
        at_bottom: bool = vadj.get_value() >= vadj.get_upper() - vadj.get_page_size() - 50
        self.auto_scroll = at_bottom
