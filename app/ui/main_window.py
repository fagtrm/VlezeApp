"""
MainWindow — главное окно приложения VlezeApp.

Содержит:
    - Боковую навигацию (Dashboard, Configs, Logs)
    - Stack с тремя страницами
    - Нижнюю панель Start/Stop
    - Интеграцию с треем, таймером логов, автозапуском xray
"""
from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, GLib

from app.i18n import _
from app.core.config import AppConfig, CONFIG_DIR, CONFIG_FILE, VLESS_DIR
from app.core.xray_manager import XrayManager
from app.core.xray_config import XrayConfigGenerator
from app.core.ping_checker import PingChecker
from app.core.config_store import ConfigStore
from app.core.vless_parser import VLESSParser
from app.ui.pages import DashboardPage, ConfigsPage, LogPage
from app.ui.widgets import ConfigRow, BottomBar
from app.ui.dialogs import SettingsDialog
from app.services import TrayService, FileDownloader


class MainWindow(Adw.ApplicationWindow):
    """Главное окно приложения VlezeApp."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.set_title("VlezeApp")
        self.set_default_size(900, 600)

        # ── Сервисы ─────────────────────────────────────────────────────
        self.app_config: AppConfig = AppConfig()
        self.xray_manager: XrayManager = XrayManager()
        self.ping_checker: PingChecker = PingChecker()
        self.config_store: ConfigStore | None = None
        self.selected_entry: dict[str, Any] | None = None

        if self.app_config.is_valid():
            self.config_store = ConfigStore(VLESS_DIR)
        else:
            GLib.idle_add(self._show_config_error)

        # ── Страницы ────────────────────────────────────────────────────
        self.dashboard_page: DashboardPage = DashboardPage()
        self.configs_page: ConfigsPage = ConfigsPage()
        self.log_page: LogPage = LogPage()

        # ── Stack страниц ───────────────────────────────────────────────
        self.page_stack: Gtk.Stack = Gtk.Stack()
        self.page_stack.add_named(self.dashboard_page, "dashboard")
        self.page_stack.add_named(self.configs_page, "configs")
        self.page_stack.add_named(self.log_page, "logs")

        # ── Боковая панель ──────────────────────────────────────────────
        self.nav_list: Gtk.ListBox = self._create_sidebar()

        # ── ToolbarView ─────────────────────────────────────────────────
        toolbar_view: Adw.ToolbarView = Adw.ToolbarView()

        # Заголовок
        header: Adw.HeaderBar = Adw.HeaderBar()
        header.set_title_widget(Gtk.Label(label="VlezeApp"))

        # Кнопка настроек
        settings_btn: Gtk.Button = Gtk.Button.new_from_icon_name("emblem-system-symbolic")
        settings_btn.set_tooltip_text(_("Settings"))
        settings_btn.connect("clicked", self._on_settings)
        header.pack_start(settings_btn)

        toolbar_view.add_top_bar(header)

        # ── Основной layout ─────────────────────────────────────────────
        main_box: Gtk.Box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)

        # Sidebar слева
        sidebar_box: Gtk.Box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        sidebar_box.set_size_request(200, -1)
        sidebar_box.append(self.nav_list)
        main_box.append(sidebar_box)

        # Разделитель
        separator: Gtk.Separator = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        main_box.append(separator)

        # Контент
        content_box: Gtk.Box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        content_box.set_hexpand(True)
        content_box.append(self.page_stack)

        self.bottom_bar: BottomBar = BottomBar()
        content_box.append(self.bottom_bar)

        main_box.append(content_box)

        toolbar_view.set_content(main_box)

        self.set_content(toolbar_view)

        # ── Подключение сигналов ────────────────────────────────────────
        self._connect_signals()

        # Выбрать Dashboard по умолчанию
        self.nav_list.select_row(self.dash_row)

        # Восстановить последний выбранный сервер
        if self.app_config.remember_last_server and self.app_config.last_server_name:
            self._select_last_server()

        # Таймер обновления логов и статуса (каждую секунду)
        GLib.timeout_add_seconds(1, self._update_timer)

        # Автозапуск xray если включён
        if self.app_config.autostart_xray and self.app_config.last_server_name:
            GLib.timeout_add_seconds(2, self._autostart_xray)

        # ── Трей ────────────────────────────────────────────────────────
        self._tray: TrayService | None = None
        if self.app_config.close_to_tray:
            self._init_tray()

    # ──────────────────────────────────────────────────────────────────────
    # Боковая панель
    # ──────────────────────────────────────────────────────────────────────

    def _create_sidebar(self) -> Gtk.ListBox:
        """Создаёт боковую панель навигации."""
        nav_list: Gtk.ListBox = Gtk.ListBox()
        nav_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        nav_list.add_css_class("navigation-sidebar")

        # Dashboard row
        self.dash_row = Gtk.ListBoxRow()
        dash_box: Gtk.Box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        dash_box.set_margin_start(8)
        dash_box.set_margin_end(8)
        dash_box.set_margin_top(6)
        dash_box.set_margin_bottom(6)
        dash_icon: Gtk.Image = Gtk.Image.new_from_icon_name("network-wired-symbolic")
        dash_label: Gtk.Label = Gtk.Label(label=_("Dashboard"))
        dash_label.set_halign(Gtk.Align.START)
        dash_box.append(dash_icon)
        dash_box.append(dash_label)
        self.dash_row.set_child(dash_box)
        nav_list.append(self.dash_row)

        # Configs row
        self.config_nav_row = Gtk.ListBoxRow()
        config_box: Gtk.Box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        config_box.set_margin_start(8)
        config_box.set_margin_end(8)
        config_box.set_margin_top(6)
        config_box.set_margin_bottom(6)
        config_icon: Gtk.Image = Gtk.Image.new_from_icon_name("document-properties-symbolic")
        config_label: Gtk.Label = Gtk.Label(label=_("Configurations"))
        config_label.set_halign(Gtk.Align.START)
        config_box.append(config_icon)
        config_box.append(config_label)
        self.config_nav_row.set_child(config_box)
        nav_list.append(self.config_nav_row)

        # Logs row
        self.log_nav_row = Gtk.ListBoxRow()
        log_box: Gtk.Box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        log_box.set_margin_start(8)
        log_box.set_margin_end(8)
        log_box.set_margin_top(6)
        log_box.set_margin_bottom(6)
        log_icon: Gtk.Image = Gtk.Image.new_from_icon_name("utilities-terminal-symbolic")
        log_label: Gtk.Label = Gtk.Label(label=_("Logs"))
        log_label.set_halign(Gtk.Align.START)
        log_box.append(log_icon)
        log_box.append(log_label)
        self.log_nav_row.set_child(log_box)
        nav_list.append(self.log_nav_row)

        return nav_list

    # ──────────────────────────────────────────────────────────────────────
    # Сигналы
    # ──────────────────────────────────────────────────────────────────────

    def _connect_signals(self) -> None:
        """Подключает сигналы UI."""
        self.nav_list.connect("row-selected", self._on_nav_selected)
        self.bottom_bar.toggle_btn.connect("clicked", self._on_toggle)
        self.configs_page.download_btn.connect("clicked", self._on_download)
        self.configs_page.file_btn.connect("clicked", self._on_file_select)
        self.configs_page.config_list.connect("row-selected", self._on_config_selected)
        self.log_page.clear_btn.connect("clicked", self._on_clear_logs)
        self.dashboard_page.ping_btn.connect("clicked", self._on_ping)

    # ──────────────────────────────────────────────────────────────────────
    # Навигация
    # ──────────────────────────────────────────────────────────────────────

    def _on_nav_selected(self, listbox: Gtk.ListBox, row: Gtk.ListBoxRow | None) -> None:
        """Обработка выбора в навигации."""
        if row == self.dash_row:
            self.page_stack.set_visible_child_name("dashboard")
        elif row == self.config_nav_row:
            self.page_stack.set_visible_child_name("configs")
            self._refresh_configs()
        elif row == self.log_nav_row:
            self.page_stack.set_visible_child_name("logs")

    # ──────────────────────────────────────────────────────────────────────
    # Таймер
    # ──────────────────────────────────────────────────────────────────────

    def _update_timer(self) -> bool:
        """Периодическое обновление логов и статуса."""
        # Обновляем логи
        logs: list[str] = self.xray_manager.read_logs()
        if logs:
            self.log_page.update_logs(logs)

        # Проверяем статус xray
        is_running: bool = self.xray_manager.check_status()
        if not is_running and self.bottom_bar.is_running:
            # xray неожиданно остановился
            self.bottom_bar.set_running(False)
            self.dashboard_page.update_status(False)

        return True  # continue timer

    # ──────────────────────────────────────────────────────────────────────
    # Выбор конфига
    # ──────────────────────────────────────────────────────────────────────

    def _on_config_selected(self, listbox: Gtk.ListBox, row: Gtk.ListBoxRow | None) -> None:
        """Обработка выбора конфига."""
        if row and hasattr(row, "entry"):
            self.selected_entry = row.entry
            self.bottom_bar.set_config_selected(True)

            # Сохранить последний сервер
            if self.app_config.remember_last_server:
                self.app_config.last_server_name = row.entry.get("name", "")
                self.app_config._save_config()
        else:
            self.selected_entry = None
            self.bottom_bar.set_config_selected(False)

    # ──────────────────────────────────────────────────────────────────────
    # Старт / Стоп
    # ──────────────────────────────────────────────────────────────────────

    def _on_toggle(self, btn: Gtk.Button) -> None:
        """Переключение Старт/Стоп."""
        if self.bottom_bar.is_running:
            self._on_stop()
        else:
            self._on_start()

    def _on_start(self) -> None:
        """Запуск xray с выбранным конфигом."""
        if not self.selected_entry:
            return

        # Генерируем временный конфиг
        temp_dir: Path = CONFIG_DIR / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_config: Path = temp_dir / "current_config.json"

        try:
            config_path: Path = XrayConfigGenerator.generate_config(
                self.selected_entry, temp_config
            )
            print(_("Конфиг создан: {}").format(config_path))

            success: bool
            message: str
            success, message = self.xray_manager.start(temp_config)

            if success:
                self.bottom_bar.set_running(True)
                config_name: str = self.selected_entry.get("name", _("Unknown"))
                self.dashboard_page.update_status(True, config_name)
                self.configs_page.highlight_connected(self.selected_entry)
                # Переключаемся на дашборд
                self.nav_list.select_row(self.dash_row)
            else:
                self._show_error(
                    _("Не удалось запустить xray: {}\n\nПроверьте логи на странице 'Логи'.")
                    .format(message)
                )
        except Exception as exc:
            import traceback
            error_msg: str = f"{exc}\n\n{traceback.format_exc()}"
            self._show_error(_("Ошибка: {}").format(error_msg))

    def _on_stop(self) -> None:
        """Остановка xray."""
        self.xray_manager.stop()
        self.bottom_bar.set_running(False)
        self.dashboard_page.update_status(False)
        # Сбрасываем пинг
        self.dashboard_page.ping_row.set_subtitle("\u2014")
        self.dashboard_page.ping_icon.set_from_icon_name("view-refresh-symbolic")
        # Сбрасываем выделение
        self.configs_page.highlight_connected(None)

    # ──────────────────────────────────────────────────────────────────────
    # Пинг
    # ──────────────────────────────────────────────────────────────────────

    def _on_ping(self, btn: Gtk.Button) -> None:
        """Ручная проверка пинга."""
        if not self.xray_manager.is_running:
            self._show_error(_("Сначала запустите VPN подключение"))
            return

        btn.set_sensitive(False)
        btn.set_label(_("Checking..."))

        # Выполняем пинг в фоне чтобы не блокировать UI
        def _do_ping() -> None:
            success: bool
            message: str
            success, message = self.ping_checker.ping_via_socks()
            # Обновляем UI в главном потоке
            GLib.idle_add(self._finish_ping, success, message, btn)

        threading.Thread(target=_do_ping, daemon=True).start()

    def _finish_ping(self, success: bool, message: str, btn: Gtk.Button) -> bool:
        """Завершение пинга — обновление UI."""
        self.dashboard_page.update_ping(success, message)
        btn.set_sensitive(True)
        btn.set_label(_("Check ping"))
        return False

    # ──────────────────────────────────────────────────────────────────────
    # Загрузка конфигов
    # ──────────────────────────────────────────────────────────────────────

    def _on_download(self, btn: Gtk.Button) -> None:
        """Загрузка base64 из интернета."""
        url: str = self.configs_page.url_entry.get_text().strip()
        if not url:
            self._show_error(_("Введите URL для загрузки"))
            return

        content: str = FileDownloader.download(url)
        if content:
            self._process_base64_content(content)
        else:
            self._show_error(_("Не удалось загрузить файл. Проверьте URL."))

    def _on_file_select(self, btn: Gtk.Button) -> None:
        """Выбор локального файла."""
        dialog: Gtk.FileDialog = Gtk.FileDialog()
        dialog.set_title(_("Выберите файл с base64 ссылками"))

        # Фильтр
        filter_txt: Gtk.FileFilter = Gtk.FileFilter()
        filter_txt.set_name(_("Text files"))
        filter_txt.add_pattern("*.txt")
        filter_txt.add_pattern("*.b64")
        filter_txt.add_pattern("*.base64")
        dialog.set_default_filter(filter_txt)

        dialog.open(self, None, self._on_file_selected)

    def _on_file_selected(self, dialog: Gtk.FileDialog, result: Gio.AsyncResult) -> None:
        """Обработка выбранного файла."""
        try:
            file: Gio.File = dialog.open_finish(result)
            if file:
                content: str = FileDownloader.read_file(file.get_path())
                if content:
                    self._process_base64_content(content)
        except Exception as exc:
            self._show_error(_("Ошибка чтения файла: {}").format(exc))

    def _process_base64_content(self, content: str) -> None:
        """Обрабатывает base64 содержимое и создаёт конфиг."""
        # Декодируем
        vless_links: list[str] = VLESSParser.decode_base64_links(content)
        if not vless_links:
            self._show_error(_("Не найдено vless:// ссылок в файле"))
            return

        # Парсим ссылки
        entries: list[dict[str, Any]] = []
        for link in vless_links:
            parsed: dict[str, Any] = VLESSParser.parse_vless_link(link)
            entries.append(parsed)

        # Сохраняем в конфиг
        if self.config_store:
            config_name: str = f"config_{len(self.config_store.get_configs()) + 1}"
            config_path: Path = self.config_store.add_entries(entries, config_name)
            print(_("Конфиг сохранён: {}").format(config_path))

            # Обновляем список
            self._refresh_configs()
        else:
            self._show_error(_("Папка vless не настроена. Проверьте конфиг приложения."))

    def _refresh_configs(self) -> None:
        """Обновляет список конфигов."""
        if not self.config_store:
            return

        # Перезагружаем
        self.config_store.set_vless_dir(VLESS_DIR)

        # Собираем все entries из всех конфигов
        all_entries: list[dict[str, Any]] = []
        for cfg in self.config_store.get_configs():
            all_entries.extend(cfg["data"].get("entries", []))

        self.configs_page.populate_configs(all_entries)

    # ──────────────────────────────────────────────────────────────────────
    # Настройки
    # ──────────────────────────────────────────────────────────────────────

    def _on_settings(self, btn: Gtk.Button) -> None:
        """Открыть настройки."""
        dialog: SettingsDialog = SettingsDialog(self.app_config, self)
        dialog.present()

        # Сохранить настройки при закрытии
        dialog.connect("closed", self._on_settings_closed)

    def _on_settings_closed(self, dialog: SettingsDialog) -> None:
        """Обработка закрытия настроек."""
        # Обновить настройки
        self.app_config.remember_last_server = dialog.get_remember_last_server()
        self.app_config.autostart_xray = dialog.get_autostart_xray()
        self.app_config.close_to_tray = dialog.get_close_to_tray()
        self.app_config._save_config()

        # Если папка изменилась — перезагрузить конфиги
        if self.config_store:
            self.config_store.set_vless_dir(VLESS_DIR)
        self._refresh_configs()

        # Обновить трей в зависимости от настройки
        if self.app_config.close_to_tray and self._tray is None:
            self._init_tray()
        elif not self.app_config.close_to_tray and self._tray is not None:
            self._shutdown_tray()

    # ──────────────────────────────────────────────────────────────────────
    # Трей
    # ──────────────────────────────────────────────────────────────────────

    def _init_tray(self) -> None:
        """Инициализировать трей и перехватить закрытие окна."""
        if self._tray is None:
            app: Gio.Application | None = self.get_application()
            if app is not None:
                self._tray = TrayService(self, app)
                # Перехватываем закрытие: прятаться вместо выхода
                self.connect("close-request", self._on_close_request)

    def enable_tray(self) -> None:
        """Включить трей (вызывается извне при изменении настроек)."""
        if self.app_config.close_to_tray and self._tray is None:
            self._init_tray()

    def _shutdown_tray(self) -> None:
        """Отключить трей."""
        if self._tray is not None:
            self._tray.shutdown()
            self._tray = None

    def _on_close_request(self, window: Gtk.Window) -> bool:
        """Обработчик закрытия окна — скрывает в трей вместо закрытия."""
        if self.app_config.close_to_tray:
            self.hide()
            return True  # Отменяем закрытие
        return False  # Позволяем закрытие

    # ──────────────────────────────────────────────────────────────────────
    # Очистка логов
    # ──────────────────────────────────────────────────────────────────────

    def _on_clear_logs(self, btn: Gtk.Button) -> None:
        """Очистка логов."""
        self.log_page.clear()
        self.xray_manager.log_lines = []

    # ──────────────────────────────────────────────────────────────────────
    # Восстановление последнего сервера
    # ──────────────────────────────────────────────────────────────────────

    def _select_last_server(self) -> None:
        """Выбрать последний сохранённый сервер."""
        if not self.config_store:
            return

        # Перезагружаем конфиги
        self.config_store.set_vless_dir(VLESS_DIR)

        # Ищем сервер по имени
        for cfg in self.config_store.get_configs():
            for entry in cfg["data"].get("entries", []):
                if entry.get("name") == self.app_config.last_server_name:
                    self.selected_entry = entry
                    self.bottom_bar.set_config_selected(True)
                    self.dashboard_page.update_status(False, entry["name"])
                    return

    # ──────────────────────────────────────────────────────────────────────
    # Автозапуск
    # ──────────────────────────────────────────────────────────────────────

    def _autostart_xray(self) -> bool:
        """Автозапуск xray после запуска приложения."""
        if self.selected_entry and self.app_config.autostart_xray:
            self._on_start()
        return False  # не повторять

    # ──────────────────────────────────────────────────────────────────────
    # Ошибки
    # ──────────────────────────────────────────────────────────────────────

    def _show_config_error(self) -> None:
        """Показывает ошибку если папка vless не найдена."""
        dialog: Adw.AlertDialog = Adw.AlertDialog()
        dialog.set_heading(_("VLESS configs folder not found"))
        dialog.set_body(
            _("The folder {} does not exist. Create it.").format(VLESS_DIR)
        )
        dialog.add_response("ok", _("Understood"))
        dialog.present(self)

    def _show_error(self, message: str) -> None:
        """Показывает сообщение об ошибке."""
        dialog: Adw.AlertDialog = Adw.AlertDialog()
        dialog.set_heading(_("Error"))
        dialog.set_body(message)
        dialog.add_response("ok", "OK")
        dialog.present(self)
