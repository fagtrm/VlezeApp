"""
ConfigEditDialog — диалог редактирования параметров Xray-конфига.

Позволяет пользователю изменить параметры, сгенерированные из vless-ссылки:
адрес, порт, безопасность, транспорт, SNI, fingerprint, flow и т.д.

Возвращает словарь overrides с изменёнными полями.
"""
from __future__ import annotations

import json
from pathlib import Path

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from app.i18n import _

# Возможные значения для выпадающих списков
SECURITY_OPTIONS = ["none", "tls", "reality"]
NETWORK_OPTIONS = ["tcp", "ws"]
FINGERPRINT_OPTIONS = ["", "chrome", "firefox", "safari", "ios", "edge", "random", "randomized"]
ALPN_OPTIONS = ["", "h2", "http/1.1", "h2,http/1.1"]
FLOW_OPTIONS = ["", "xtls-rprx-vision", "xtls-rprx-vision-udp443"]


class ConfigEditDialog(Gtk.Dialog):
    """Диалог редактирования параметров конфига."""

    def __init__(self, entry: dict, parent: Gtk.Window,
                 overridden_path: Path | None = None) -> None:
        super().__init__()
        self.set_title(_("Настройка конфигурации"))
        self.set_transient_for(parent)
        self.set_modal(True)
        self.set_default_size(500, 600)

        self.entry: dict = entry
        self._overridden_path = overridden_path
        self._on_save: callable | None = None
        self._on_reset: callable | None = None

        # Загружаем базу: из overridden файла если есть, иначе из entry
        if overridden_path and overridden_path.exists():
            try:
                with open(overridden_path, "r", encoding="utf-8") as fh:
                    cfg = json.load(fh)
                    # Извлекаем настройки из первого outbound
                    outbound = cfg.get("outbounds", [{}])[0]
                    vnext = outbound.get("settings", {}).get("vnext", [{}])[0]
                    user = vnext.get("users", [{}])[0]
                    stream = outbound.get("streamSettings", {})

                    self._base = {
                        "host": vnext.get("address", entry.get("host", "")),
                        "port": str(vnext.get("port", entry.get("port", ""))),
                        "type": stream.get("network", entry.get("type", "tcp")),
                        "security": stream.get("security", entry.get("security", "none")),
                        "sni": "",
                        "fp": "",
                        "alpn": "",
                        "flow": user.get("flow", ""),
                        "path": "",
                        "pbk": "",
                        "sid": "",
                    }
                    # TLS
                    tls = stream.get("tlsSettings", {})
                    if tls:
                        self._base["sni"] = tls.get("serverName", "")
                        self._base["fp"] = tls.get("fingerprint", "")
                        self._base["alpn"] = ",".join(tls.get("alpn", [])) if tls.get("alpn") else ""
                    # Reality
                    rel = stream.get("realitySettings", {})
                    if rel:
                        self._base["sni"] = rel.get("serverName", "")
                        self._base["fp"] = rel.get("fingerprint", "")
                        self._base["pbk"] = rel.get("publicKey", "")
                        self._base["sid"] = rel.get("shortId", "")
                    # WS
                    ws = stream.get("wsSettings", {})
                    if ws:
                        self._base["path"] = ws.get("path", "/")
                    # TCP HTTP header
                    tcp = stream.get("tcpSettings", {})
                    if tcp:
                        req = tcp.get("header", {}).get("request", {})
                        self._base["path"] = req.get("path", ["/"])[0] if req.get("path") else "/"
            except Exception:
                self._base = entry
        else:
            self._base = entry

        # ── Контент: PreferencesPage внутри scrolled area ─────────────────
        content_area = self.get_content_area()
        content_area.set_margin_start(12)
        content_area.set_margin_end(12)
        content_area.set_margin_top(12)
        content_area.set_margin_bottom(12)
        content_area.set_spacing(12)

        # ── Кнопки внизу ──────────────────────────────────────────────────
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_box.set_halign(Gtk.Align.END)

        self.reset_btn: Gtk.Button = Gtk.Button.new_with_label(_("По умолчанию"))
        self.reset_btn.add_css_class("destructive-action")
        self.reset_btn.connect("clicked", self._on_reset_clicked)
        btn_box.append(self.reset_btn)

        self.save_btn: Gtk.Button = Gtk.Button.new_with_label(_("Сохранить"))
        self.save_btn.add_css_class("suggested-action")
        self.save_btn.connect("clicked", self._on_save_clicked)
        btn_box.append(self.save_btn)

        content_area.append(btn_box)

        # ── Страница ──────────────────────────────────────────────────────
        page: Adw.PreferencesPage = Adw.PreferencesPage()

        # ── Группа: Подключение ───────────────────────────────────────────
        conn_group: Adw.PreferencesGroup = Adw.PreferencesGroup()
        conn_group.set_title(_("Подключение"))

        self.address_row: Adw.EntryRow = Adw.EntryRow()
        self.address_row.set_title(_("Адрес"))
        self.address_row.set_text(self._base.get("host", ""))
        conn_group.add(self.address_row)

        self.port_row: Adw.EntryRow = Adw.EntryRow()
        self.port_row.set_title(_("Порт"))
        self.port_row.set_text(str(self._base.get("port", "")))
        self.port_row.set_input_purpose(Gtk.InputPurpose.NUMBER)
        conn_group.add(self.port_row)

        self.network_row: Adw.ComboRow = Adw.ComboRow()
        self.network_row.set_title(_("Сеть"))
        self.network_row.set_model(Gtk.StringList.new(NETWORK_OPTIONS))
        current_net = self._base.get("type", "tcp")
        try:
            idx = NETWORK_OPTIONS.index(current_net)
        except ValueError:
            idx = 0
        self.network_row.set_selected(idx)
        conn_group.add(self.network_row)

        page.add(conn_group)

        # ── Группа: Безопасность ──────────────────────────────────────────
        sec_group: Adw.PreferencesGroup = Adw.PreferencesGroup()
        sec_group.set_title(_("Безопасность"))

        self.security_row: Adw.ComboRow = Adw.ComboRow()
        self.security_row.set_title(_("Безопасность"))
        self.security_row.set_model(Gtk.StringList.new(SECURITY_OPTIONS))
        current_sec = self._base.get("security", "none")
        try:
            idx = SECURITY_OPTIONS.index(current_sec)
        except ValueError:
            idx = 0
        self.security_row.set_selected(idx)
        self.security_row.connect("notify::selected", self._on_security_changed)
        sec_group.add(self.security_row)

        self.sni_row: Adw.EntryRow = Adw.EntryRow()
        self.sni_row.set_title(_("SNI"))
        self.sni_row.set_text(self._base.get("sni") or self._base.get("host", ""))
        sec_group.add(self.sni_row)

        self.fp_row: Adw.ComboRow = Adw.ComboRow()
        self.fp_row.set_title(_("Fingerprint"))
        self.fp_row.set_model(Gtk.StringList.new(FINGERPRINT_OPTIONS))
        current_fp = self._base.get("fp", "")
        try:
            idx = FINGERPRINT_OPTIONS.index(current_fp)
        except ValueError:
            idx = 0
        self.fp_row.set_selected(idx)
        sec_group.add(self.fp_row)

        self.alpn_row: Adw.ComboRow = Adw.ComboRow()
        self.alpn_row.set_title(_("ALPN"))
        self.alpn_row.set_model(Gtk.StringList.new(ALPN_OPTIONS))
        current_alpn = self._base.get("alpn", "")
        try:
            idx = ALPN_OPTIONS.index(current_alpn)
        except ValueError:
            idx = 0
        self.alpn_row.set_selected(idx)
        sec_group.add(self.alpn_row)

        self.flow_row: Adw.ComboRow = Adw.ComboRow()
        self.flow_row.set_title(_("Flow"))
        self.flow_row.set_model(Gtk.StringList.new(FLOW_OPTIONS))
        current_flow = self._base.get("flow", "")
        try:
            idx = FLOW_OPTIONS.index(current_flow)
        except ValueError:
            idx = 0
        self.flow_row.set_selected(idx)
        sec_group.add(self.flow_row)

        self.insecure_row: Adw.SwitchRow = Adw.SwitchRow()
        self.insecure_row.set_title(_("Разрешить небезопасные"))
        self.insecure_row.set_subtitle(_("allowInsecure"))
        self.insecure_row.set_active(False)
        sec_group.add(self.insecure_row)

        page.add(sec_group)

        # ── Группа: Reality (скрыта по умолчанию) ─────────────────────────
        self.reality_group: Adw.PreferencesGroup = Adw.PreferencesGroup()
        self.reality_group.set_title(_("Reality"))
        self.reality_group.set_visible(False)

        self.pbk_row: Adw.EntryRow = Adw.EntryRow()
        self.pbk_row.set_title(_("Public Key"))
        self.pbk_row.set_text(self._base.get("pbk", ""))
        self.reality_group.add(self.pbk_row)

        self.sid_row: Adw.EntryRow = Adw.EntryRow()
        self.sid_row.set_title(_("Short ID"))
        self.sid_row.set_text(self._base.get("sid", ""))
        self.reality_group.add(self.sid_row)

        page.add(self.reality_group)

        # ── Группа: Транспорт ─────────────────────────────────────────────
        transport_group: Adw.PreferencesGroup = Adw.PreferencesGroup()
        transport_group.set_title(_("Транспорт"))

        self.path_row: Adw.EntryRow = Adw.EntryRow()
        self.path_row.set_title(_("Путь"))
        self.path_row.set_text(self._base.get("path", "/"))
        transport_group.add(self.path_row)

        self.header_host_row: Adw.EntryRow = Adw.EntryRow()
        self.header_host_row.set_title(_("Host заголовок"))
        self.header_host_row.set_text(self._base.get("host", ""))
        transport_group.add(self.header_host_row)

        page.add(transport_group)

        # Оборачиваем PreferencesPage в ScrolledWindow
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_child(page)
        scrolled.set_vexpand(True)
        content_area.append(scrolled)

        # Инициализация видимости Reality
        self._on_security_changed()

    # ── Обработчики кнопок ────────────────────────────────────────────────

    def set_save_callback(self, callback: callable) -> None:
        """Установить callback для сохранения."""
        self._on_save = callback

    def set_reset_callback(self, callback: callable) -> None:
        """Установить callback для сброса."""
        self._on_reset = callback

    def _on_save_clicked(self, _btn: Gtk.Button) -> None:
        if self._on_save:
            self._on_save()

    def _on_reset_clicked(self, _btn: Gtk.Button) -> None:
        if self._on_reset:
            self._on_reset()

    # ── Обработчики ───────────────────────────────────────────────────────

    def _on_security_changed(self, *args) -> None:
        """Показать/скрыть группу Reality."""
        selected = self.security_row.get_selected()
        security = SECURITY_OPTIONS[selected] if selected < len(SECURITY_OPTIONS) else "none"
        self.reality_group.set_visible(security == "reality")

    # ── Сбор overrides ────────────────────────────────────────────────────

    def get_overrides(self) -> dict[str, str]:
        """Собрать все текущие значения из полей диалога."""
        selected_sec_idx = self.security_row.get_selected()
        selected_net_idx = self.network_row.get_selected()
        selected_fp_idx = self.fp_row.get_selected()
        selected_alpn_idx = self.alpn_row.get_selected()
        selected_flow_idx = self.flow_row.get_selected()

        return {
            "host": self.address_row.get_text().strip(),
            "port": self.port_row.get_text().strip(),
            "type": NETWORK_OPTIONS[selected_net_idx] if selected_net_idx < len(NETWORK_OPTIONS) else "tcp",
            "security": SECURITY_OPTIONS[selected_sec_idx] if selected_sec_idx < len(SECURITY_OPTIONS) else "none",
            "sni": self.sni_row.get_text().strip(),
            "fp": FINGERPRINT_OPTIONS[selected_fp_idx] if selected_fp_idx < len(FINGERPRINT_OPTIONS) else "",
            "alpn": ALPN_OPTIONS[selected_alpn_idx] if selected_alpn_idx < len(ALPN_OPTIONS) else "",
            "flow": FLOW_OPTIONS[selected_flow_idx] if selected_flow_idx < len(FLOW_OPTIONS) else "",
            "path": self.path_row.get_text().strip(),
            "pbk": self.pbk_row.get_text().strip(),
            "sid": self.sid_row.get_text().strip(),
            "header_host": self.header_host_row.get_text().strip(),
            "allow_insecure": str(self.insecure_row.get_active()),
        }

    def reset_to_defaults(self) -> None:
        """Вернуть все поля к значениям из исходной vless-ссылки."""
        self.address_row.set_text(self.entry.get("host", ""))
        self.port_row.set_text(str(self.entry.get("port", "")))
        self.sni_row.set_text(self.entry.get("sni") or self.entry.get("host", ""))
        self.path_row.set_text(self.entry.get("path", "/"))
        self.pbk_row.set_text(self.entry.get("pbk", ""))
        self.sid_row.set_text(self.entry.get("sid", ""))
        self.header_host_row.set_text(self.entry.get("host", ""))
        self.insecure_row.set_active(False)

        # Combo: security
        current_sec = self.entry.get("security", "none")
        try:
            self.security_row.set_selected(SECURITY_OPTIONS.index(current_sec))
        except ValueError:
            self.security_row.set_selected(0)

        # Combo: network
        current_net = self.entry.get("type", "tcp")
        try:
            self.network_row.set_selected(NETWORK_OPTIONS.index(current_net))
        except ValueError:
            self.network_row.set_selected(0)

        # Combo: fingerprint
        current_fp = self.entry.get("fp", "")
        try:
            self.fp_row.set_selected(FINGERPRINT_OPTIONS.index(current_fp))
        except ValueError:
            self.fp_row.set_selected(0)

        # Combo: alpn
        current_alpn = self.entry.get("alpn", "")
        try:
            self.alpn_row.set_selected(ALPN_OPTIONS.index(current_alpn))
        except ValueError:
            self.alpn_row.set_selected(0)

        # Combo: flow
        current_flow = self.entry.get("flow", "")
        try:
            self.flow_row.set_selected(FLOW_OPTIONS.index(current_flow))
        except ValueError:
            self.flow_row.set_selected(0)

        self._on_security_changed()
