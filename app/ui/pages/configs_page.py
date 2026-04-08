"""
ConfigsPage — страница списка VLESS-конфигураций с табами.

Кнопки загрузки URL и выбора файла, табы конфигураций (до 5),
каждый таб содержит список серверов с подсветкой подключённого.

Методы:
    build_tabs(configs)        — построить табы из списка конфигов.
    get_selected_entry()       — вернуть выбранную запись.
    highlight_connected(entry) — подсветить подключённый сервер.
    get_active_tab_name()      — имя активного таба (config_1 и т.д.).
"""
from __future__ import annotations

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Gio", "2.0")
from gi.repository import Gtk, Gdk, Gio, GObject

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

MAX_CONFIGS = 5


class ConfigsPage(Gtk.Box):
    """Страница списка конфигов с табами."""

    __gsignals__ = {
        "config-deleted": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

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

        # Кнопка фильтра (поиск)
        self.filter_btn: Gtk.Button = Gtk.Button.new_from_icon_name("system-search-symbolic")
        self.filter_btn.set_tooltip_text(_("Filter configs"))
        self.filter_btn.connect("clicked", self._on_filter_toggle)
        load_box.append(self.filter_btn)

        self.append(load_box)

        # ── Поле поиска (скрыто по умолчанию) ─────────────────────────────
        self.search_box: Gtk.Box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.search_box.set_hexpand(True)
        self.search_box.set_visible(False)

        self.search_entry: Gtk.SearchEntry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text(_("Filter by name, e.g. whitelist..."))
        self.search_entry.set_hexpand(True)
        self.search_entry.connect("search-changed", self._on_search_changed)
        self.search_entry.connect("activate", self._on_search_activated)
        self.search_entry.connect("stop-search", self._on_stop_search)
        self.search_box.append(self.search_entry)

        self.append(self.search_box)

        # ── Табы (Notebook) ───────────────────────────────────────────────
        self.notebook: Gtk.Notebook = Gtk.Notebook()
        self.notebook.set_scrollable(True)
        self.notebook.set_show_border(False)
        self.notebook.set_vexpand(True)
        self.notebook.set_hexpand(True)
        self.notebook.show()
        self.append(self.notebook)

        # Пустое состояние (скрыто по умолчанию)
        self.empty_label: Gtk.Label = Gtk.Label(
            label=_("No configs found. Download a base64 file to create a config.")
        )
        self.empty_label.set_opacity(0.5)
        self.empty_label.set_margin_top(40)
        self.empty_label.set_visible(False)
        self.append(self.empty_label)

    # ── Внутренние обработчики ────────────────────────────────────────────

    def _get_listbox_for_page(self, page: Gtk.Widget) -> Gtk.ListBox | None:
        """Найти ListBox внутри страницы таба."""
        if isinstance(page, Gtk.ScrolledWindow):
            child = page.get_child()
            if isinstance(child, Gtk.ListBox):
                return child
            # GTK4 может добавить Gtk.Viewport между ScrolledWindow и ListBox
            if isinstance(child, Gtk.Viewport):
                inner = child.get_child()
                if isinstance(inner, Gtk.ListBox):
                    return inner
        return None

    def _create_tab_label(self, display_name: str, config_name: str) -> Gtk.Box:
        """Создать заголовок таба с кнопкой удаления."""
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)

        label = Gtk.Label(label=display_name)
        label.set_margin_start(4)
        label.set_margin_end(4)
        box.append(label)

        # Кнопка удаления
        del_btn = Gtk.Button.new_from_icon_name("window-close-symbolic")
        del_btn.set_tooltip_text(_("Delete configuration"))
        del_btn.set_has_frame(False)
        del_btn.add_css_class("flat")
        del_btn.set_valign(Gtk.Align.CENTER)
        # Сохраняем имя конфига как Python-атрибут
        del_btn._config_name = config_name  # noqa: SLF001
        del_btn.connect("clicked", self._on_delete_tab)
        box.append(del_btn)

        return box

    def _on_delete_tab(self, btn: Gtk.Button) -> None:
        """Удалить конфигурацию по нажатию кнопки."""
        config_name: str | None = getattr(btn, "_config_name", None)
        if config_name:
            self.emit("config-deleted", config_name)

    # ── Обработчики фильтра ───────────────────────────────────────────────

    def _on_filter_toggle(self, _btn: Gtk.Button) -> None:
        """Показать/скрыть поле поиска."""
        is_visible = self.search_box.get_visible()
        self.search_box.set_visible(not is_visible)
        if not is_visible:
            self.search_entry.grab_focus()
        else:
            self._clear_search_filter()

    def _on_search_changed(self, entry: Gtk.SearchEntry) -> None:
        """Фильтрация при изменении текста поиска."""
        self._apply_filter(entry.get_text())

    def _on_search_activated(self, _entry: Gtk.SearchEntry) -> None:
        """Обработка нажатия Enter в поле поиска."""
        # Выбираем первый видимый результат
        self._select_first_visible()

    def _on_stop_search(self, _entry: Gtk.SearchEntry) -> None:
        """Скрыть поле поиска при нажатии встроенной кнопки очистки."""
        self.search_box.set_visible(False)
        self._clear_search_filter()
        self.search_entry.set_text("")

    def _clear_search_filter(self) -> None:
        """Убрать фильтр со всех строк активного таба."""
        current_page = self.notebook.get_current_page()
        if current_page < 0:
            return

        page = self.notebook.get_nth_page(current_page)
        listbox = self._get_listbox_for_page(page)
        if not listbox:
            return

        row = listbox.get_row_at_index(0)
        while row:
            row.set_visible(True)
            next_idx = row.get_index() + 1
            row = listbox.get_row_at_index(next_idx)

    def _apply_filter(self, query: str) -> None:
        """Применить фильтр к строкам активного таба.

        Фильтрует по имени сервера (entry["name"]).
        """
        current_page = self.notebook.get_current_page()
        if current_page < 0:
            return

        page = self.notebook.get_nth_page(current_page)
        listbox = self._get_listbox_for_page(page)
        if not listbox:
            return

        query_lower = query.lower().strip()

        row = listbox.get_row_at_index(0)
        while row:
            if hasattr(row, "entry"):
                entry_name = row.entry.get("name", "").lower()
                matches = not query_lower or query_lower in entry_name
                row.set_visible(matches)
            else:
                row.set_visible(True)
            next_idx = row.get_index() + 1
            row = listbox.get_row_at_index(next_idx)

    def _select_first_visible(self) -> None:
        """Выбрать первую видимую строку в активном табе."""
        current_page = self.notebook.get_current_page()
        if current_page < 0:
            return

        page = self.notebook.get_nth_page(current_page)
        listbox = self._get_listbox_for_page(page)
        if not listbox:
            return

        row = listbox.get_row_at_index(0)
        while row:
            if row.get_visible():
                listbox.select_row(row)
                return
            next_idx = row.get_index() + 1
            row = listbox.get_row_at_index(next_idx)

    # ── Публичный API ─────────────────────────────────────────────────────

    def build_tabs(self, configs: list[dict]) -> None:
        """Построить табы из списка конфигов.

        Args:
            configs: Список конфигов из ConfigStore.
        """
        # Очищаем все табы
        while self.notebook.get_n_pages() > 0:
            self.notebook.remove_page(0)

        if not configs:
            self.empty_label.set_visible(True)
            self.notebook.set_visible(False)
            return

        self.empty_label.set_visible(False)
        self.notebook.set_visible(True)

        for cfg in configs:
            entries = cfg["data"].get("entries", [])
            config_name = cfg["name"]  # например "config_1"
            display_name = self._format_tab_name(config_name)

            # Создаём ListBox для этого таба
            listbox = Gtk.ListBox()
            listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
            listbox.add_css_class("boxed-list")
            listbox._config_name = config_name  # noqa: SLF001

            for entry in entries:
                row = ConfigRow(entry)
                listbox.append(row)

            # Оборачиваем в ScrolledWindow
            scrolled = Gtk.ScrolledWindow()
            scrolled.set_child(listbox)
            scrolled.set_vexpand(True)

            # Заголовок таба
            tab_label = self._create_tab_label(display_name, config_name)

            # Показываем всё до добавления в notebook
            scrolled.show()
            listbox.show()
            tab_label.show()

            self.notebook.append_page(scrolled, tab_label)

        # Переключаемся на первый таб (если есть страницы)
        if self.notebook.get_n_pages() > 0:
            self.notebook.set_current_page(0)
        self.notebook.show()
        self.notebook.queue_draw()

        # Сбрасываем фильтр при перестроении табов
        self._clear_search_filter()
        self.search_entry.set_text("")
        self.search_box.set_visible(False)

        # Подключаем сигнал переключения таба для сброса фильтра
        self.notebook.connect("switch-page", self._on_tab_switched)

    def _on_tab_switched(self, _notebook: Gtk.Notebook, _page: Gtk.Widget, _page_num: int) -> None:
        """Сбросить фильтр при переключении таба."""
        self._clear_search_filter()
        self.search_entry.set_text("")

    def _format_tab_name(self, config_name: str) -> str:
        """Преобразовать 'config_1' → 'Конфигурация 1'."""
        parts = config_name.rsplit("_", 1)
        if len(parts) == 2 and parts[1].isdigit():
            return _("Configuration {}").format(parts[1])
        return config_name

    def get_selected_entry(self) -> dict | None:
        """Возвращает выбранную запись из активного таба."""
        current_page = self.notebook.get_current_page()
        if current_page < 0:
            return None

        page = self.notebook.get_nth_page(current_page)
        listbox = self._get_listbox_for_page(page)
        if listbox:
            selected = listbox.get_selected_row()
            if selected and hasattr(selected, "entry"):
                return selected.entry
        return None

    def get_active_tab_name(self) -> str | None:
        """Возвращает имя активного конфига (config_1 и т.д.)."""
        current_page = self.notebook.get_current_page()
        if current_page < 0:
            return None

        page = self.notebook.get_nth_page(current_page)
        listbox = self._get_listbox_for_page(page)
        if listbox:
            return getattr(listbox, "_config_name", None)
        return None

    def highlight_connected(self, entry: dict | None) -> None:
        """Подсвечивает подключённую строку зелёным фоном во всех табах."""
        entry_uid = entry.get("uid", "") if entry else ""
        for i in range(self.notebook.get_n_pages()):
            page = self.notebook.get_nth_page(i)
            listbox = self._get_listbox_for_page(page)
            if listbox:
                row = listbox.get_row_at_index(0)
                while row:
                    if hasattr(row, "set_connected"):
                        row_entry = getattr(row, "entry", None)
                        is_match = entry and row_entry and row_entry.get("uid", "") == entry_uid
                        row.set_connected(is_match)
                    next_idx = row.get_index() + 1
                    row = listbox.get_row_at_index(next_idx)

    def can_add_config(self) -> bool:
        """Можно ли добавить ещё один конфиг (лимит MAX_CONFIGS).

        Проверяет по текущему количеству страниц в notebook.
        """
        return self.notebook.get_n_pages() < MAX_CONFIGS

    def get_config_count(self) -> int:
        """Вернуть текущее количество конфигов (страниц)."""
        return self.notebook.get_n_pages()

    def get_config_names(self) -> list[str]:
        """Вернуть список имён конфигов в табах."""
        names: list[str] = []
        for i in range(self.notebook.get_n_pages()):
            page = self.notebook.get_nth_page(i)
            listbox = self._get_listbox_for_page(page)
            if listbox:
                name = getattr(listbox, "_config_name", None)
                if name:
                    names.append(name)
        return names

    def connect_selection_handler(self, callback) -> None:
        """Подключить callback к row-selected во всех табах."""
        for i in range(self.notebook.get_n_pages()):
            page = self.notebook.get_nth_page(i)
            listbox = self._get_listbox_for_page(page)
            if listbox:
                listbox.connect("row-selected", callback)

    def select_entry(self, entry: dict | None) -> None:
        """Найти и выделить строку с данным entry во всех табах."""
        if entry is None:
            return
        target_uid = entry.get("uid", "")
        for i in range(self.notebook.get_n_pages()):
            page = self.notebook.get_nth_page(i)
            listbox = self._get_listbox_for_page(page)
            if not listbox:
                continue
            row = listbox.get_row_at_index(0)
            while row:
                if hasattr(row, "entry") and row.entry.get("uid", "") == target_uid:
                    listbox.select_row(row)
                    return
                next_idx = row.get_index() + 1
                row = listbox.get_row_at_index(next_idx)

    def set_filter_text(self, text: str) -> None:
        """Установить текст фильтра и применить его.

        Args:
            text: Строка для поиска по имени сервера.
        """
        self.search_entry.set_text(text)
        if text and not self.search_box.get_visible():
            self.search_box.set_visible(True)

    def clear_filter(self) -> None:
        """Очистить фильтр поиска."""
        self._clear_search_filter()
        self.search_entry.set_text("")
