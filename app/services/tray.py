"""
Системный трей для VlezeApp через D-Bus StatusNotifierItem (SNI).

Протоколы:
  org.kde.StatusNotifierItem  — иконка в трее (путь /StatusNotifierItem)
  com.canonical.dbusmenu      — контекстное меню (путь /StatusNotifierMenu)

Работает на KDE Plasma, GNOME (AppIndicator extension), XFCE, i3/sway и др.
Не зависит от GTK3 / AyatanaAppIndicator.
"""
from __future__ import annotations

import os
from typing import TYPE_CHECKING

import gi
gi.require_version("Gio", "2.0")
gi.require_version("GLib", "2.0")
from gi.repository import Gio, GLib

from app.i18n import _

if TYPE_CHECKING:
    from gi.repository import Gtk

# ── D-Bus пути ────────────────────────────────────────────────────────────────

# Watcher ожидает объект на /StatusNotifierItem — это соглашение протокола.
_SNI_PATH    = "/StatusNotifierItem"
_MENU_PATH   = "/StatusNotifierMenu"
_SNI_IFACE   = "org.kde.StatusNotifierItem"
_MENU_IFACE  = "com.canonical.dbusmenu"
_WATCHER     = "org.kde.StatusNotifierWatcher"
_WATCHER_OBJ = "/StatusNotifierWatcher"

# ── XML-интроспекция ──────────────────────────────────────────────────────────

_SNI_XML = """\
<node>
  <interface name="org.kde.StatusNotifierItem">
    <method name="Activate">
      <arg direction="in" type="i" name="x"/>
      <arg direction="in" type="i" name="y"/>
    </method>
    <method name="SecondaryActivate">
      <arg direction="in" type="i" name="x"/>
      <arg direction="in" type="i" name="y"/>
    </method>
    <method name="Scroll">
      <arg direction="in" type="i" name="delta"/>
      <arg direction="in" type="s" name="orientation"/>
    </method>
    <method name="ContextMenu">
      <arg direction="in" type="i" name="x"/>
      <arg direction="in" type="i" name="y"/>
    </method>
    <property name="Category"   type="s"            access="read"/>
    <property name="Id"         type="s"            access="read"/>
    <property name="Title"      type="s"            access="read"/>
    <property name="Status"     type="s"            access="read"/>
    <property name="IconName"   type="s"            access="read"/>
    <property name="ToolTip"    type="(sa(iiay)ss)" access="read"/>
    <property name="Menu"       type="o"            access="read"/>
    <property name="ItemIsMenu" type="b"            access="read"/>
    <signal name="NewTitle"/>
    <signal name="NewIcon"/>
    <signal name="NewToolTip"/>
    <signal name="NewStatus">
      <arg type="s" name="status"/>
    </signal>
  </interface>
</node>"""

_MENU_XML = """\
<node>
  <interface name="com.canonical.dbusmenu">
    <method name="GetLayout">
      <arg direction="in"  type="i"          name="parentId"/>
      <arg direction="in"  type="i"          name="recursionDepth"/>
      <arg direction="in"  type="as"         name="propertyNames"/>
      <arg direction="out" type="u"          name="revision"/>
      <arg direction="out" type="(ia{sv}av)" name="layout"/>
    </method>
    <method name="GetGroupProperties">
      <arg direction="in"  type="ai"        name="ids"/>
      <arg direction="in"  type="as"        name="propertyNames"/>
      <arg direction="out" type="a(ia{sv})" name="properties"/>
    </method>
    <method name="Event">
      <arg direction="in" type="i"  name="id"/>
      <arg direction="in" type="s"  name="eventId"/>
      <arg direction="in" type="v"  name="data"/>
      <arg direction="in" type="u"  name="timestamp"/>
    </method>
    <method name="EventGroup">
      <arg direction="in"  type="a(isvu)" name="events"/>
      <arg direction="out" type="ai"      name="idErrors"/>
    </method>
    <method name="AboutToShow">
      <arg direction="in"  type="i" name="id"/>
      <arg direction="out" type="b" name="needUpdate"/>
    </method>
    <method name="AboutToShowGroup">
      <arg direction="in"  type="ai" name="ids"/>
      <arg direction="out" type="ai" name="updatesNeeded"/>
      <arg direction="out" type="ai" name="idErrors"/>
    </method>
    <signal name="LayoutUpdated">
      <arg type="u" name="revision"/>
      <arg type="i" name="parent"/>
    </signal>
    <signal name="ItemsPropertiesUpdated">
      <arg type="a(ia{sv})" name="updatedProps"/>
      <arg type="a(ias)"    name="removedProps"/>
    </signal>
  </interface>
</node>"""

# ── Хелперы GVariant ──────────────────────────────────────────────────────────

def _v(type_str: str, value) -> GLib.Variant:
    return GLib.Variant(type_str, value)


def _make_menu_item(
    item_id: int,
    props: dict[str, GLib.Variant],
    children: list[GLib.Variant],
) -> GLib.Variant:
    """Создать элемент меню типа (ia{sv}av)."""
    return GLib.Variant("(ia{sv}av)", (item_id, props, children))


def _item(item_id: int, label: str, icon: str = "") -> GLib.Variant:
    props: dict[str, GLib.Variant] = {
        "label":   _v("s", label),
        "enabled": _v("b", True),
        "visible": _v("b", True),
    }
    if icon:
        props["icon-name"] = _v("s", icon)
    return _make_menu_item(item_id, props, [])


def _separator(item_id: int) -> GLib.Variant:
    return _make_menu_item(
        item_id,
        {"type": _v("s", "separator"), "visible": _v("b", True)},
        [],
    )


# ── Основной класс ────────────────────────────────────────────────────────────

class TrayService:
    """
    SNI-трей для VlezeApp. Создавать после того как окно создано.
    Хранить как атрибут окна (self._tray = TrayService(self, app)).
    """

    def __init__(self, window: "Gtk.Window", app: "Gio.Application") -> None:
        self._window    = window
        self._app       = app
        self._conn: Gio.DBusConnection | None = None
        self._sni_reg   = 0
        self._menu_reg  = 0
        self._menu_rev  = 1
        self._tooltip   = "VlezeApp"

        # Удерживаем event-loop пока трей жив
        self._app.hold()

        Gio.bus_get(Gio.BusType.SESSION, None, self._on_bus_ready, None)

    # ── Подключение к шине ────────────────────────────────────────────────────

    def _on_bus_ready(self, _src, result: Gio.AsyncResult, _data) -> None:
        try:
            self._conn = Gio.bus_get_finish(result)
        except Exception as exc:
            print(f"[tray] bus_get failed: {exc}")
            self._app.release()
            return

        self._register_objects()
        self._request_name()

    def _register_objects(self) -> None:
        sni_node  = Gio.DBusNodeInfo.new_for_xml(_SNI_XML)
        menu_node = Gio.DBusNodeInfo.new_for_xml(_MENU_XML)

        self._sni_reg = self._conn.register_object(
            _SNI_PATH,
            sni_node.interfaces[0],
            self._on_sni_call,
            self._on_sni_get,
            None,
        )
        self._menu_reg = self._conn.register_object(
            _MENU_PATH,
            menu_node.interfaces[0],
            self._on_menu_call,
            None,
            None,
        )

    def _request_name(self) -> None:
        pid  = os.getpid()
        name = f"org.kde.StatusNotifierItem-{pid}-1"
        self._conn.call(
            "org.freedesktop.DBus", "/org/freedesktop/DBus",
            "org.freedesktop.DBus", "RequestName",
            _v("(su)", (name, 0)),
            GLib.VariantType("(u)"),
            Gio.DBusCallFlags.NONE, -1, None,
            self._on_name_ready, None,
        )

    def _on_name_ready(self, _src, result: Gio.AsyncResult, _data) -> None:
        try:
            self._conn.call_finish(result)
        except Exception as exc:
            print(f"[tray] RequestName failed: {exc}")
            return

        pid  = os.getpid()
        name = f"org.kde.StatusNotifierItem-{pid}-1"
        self._conn.call(
            _WATCHER, _WATCHER_OBJ,
            _WATCHER, "RegisterStatusNotifierItem",
            _v("(s)", (name,)), None,
            Gio.DBusCallFlags.NONE, -1, None,
            self._on_registered, None,
        )

    def _on_registered(self, _src, result: Gio.AsyncResult, _data) -> None:
        try:
            self._conn.call_finish(result)
        except Exception as exc:
            print(f"[tray] RegisterStatusNotifierItem failed: {exc}")

    # ── SNI: методы ───────────────────────────────────────────────────────────

    def _on_sni_call(
        self, _conn, _sender, _path, _iface,
        method: str, _params: GLib.Variant,
        inv: Gio.DBusMethodInvocation,
    ) -> None:
        if method in ("Activate", "SecondaryActivate"):
            GLib.idle_add(self._toggle_window)
        # ContextMenu / Scroll — ничего не делаем, но отвечаем
        inv.return_value(GLib.Variant("()", ()))

    # ── SNI: свойства ─────────────────────────────────────────────────────────

    def _on_sni_get(
        self, _conn, _sender, _path, _iface,
        prop: str,
    ) -> GLib.Variant | None:
        match prop:
            case "Category":   return _v("s", "ApplicationStatus")
            case "Id":         return _v("s", "vlezeapp")
            case "Title":      return _v("s", "VlezeApp")
            case "Status":     return _v("s", "Active")
            case "IconName":   return _v("s", "network-vpn-symbolic")
            case "Menu":       return _v("o", _MENU_PATH)
            case "ItemIsMenu": return _v("b", False)
            case "ToolTip":
                return GLib.Variant(
                    "(sa(iiay)ss)",
                    ("", [], "VlezeApp", self._tooltip),
                )
        return None

    # ── DBusMenu: методы ──────────────────────────────────────────────────────

    def _on_menu_call(
        self, _conn, _sender, _path, _iface,
        method: str, params: GLib.Variant,
        inv: Gio.DBusMethodInvocation,
    ) -> None:
        try:
            self._dispatch_menu(method, params, inv)
        except Exception as exc:
            print(f"[tray] menu method {method} error: {exc}")
            inv.return_dbus_error(
                "org.freedesktop.DBus.Error.Failed", str(exc)
            )

    def _dispatch_menu(
        self,
        method: str,
        params: GLib.Variant,
        inv: Gio.DBusMethodInvocation,
    ) -> None:
        if method == "GetLayout":
            layout = self._build_layout()
            inv.return_value(GLib.Variant(
                "(u(ia{sv}av))", (self._menu_rev, layout)
            ))

        elif method == "GetGroupProperties":
            ids    = list(params[0])
            result = [(i, self._item_props(i)) for i in ids
                      if self._item_props(i) is not None]
            inv.return_value(GLib.Variant("(a(ia{sv}))", (result,)))

        elif method == "Event":
            item_id, event_id = int(params[0]), str(params[1])
            if event_id == "clicked":
                GLib.idle_add(self._on_click, item_id)
            inv.return_value(GLib.Variant("()", ()))

        elif method == "EventGroup":
            for ev in list(params[0]):
                if str(ev[1]) == "clicked":
                    GLib.idle_add(self._on_click, int(ev[0]))
            inv.return_value(GLib.Variant("(ai)", ([],)))

        elif method == "AboutToShow":
            inv.return_value(GLib.Variant("(b)", (False,)))

        elif method == "AboutToShowGroup":
            inv.return_value(GLib.Variant("(aiai)", ([], [])))

        else:
            inv.return_dbus_error(
                "org.freedesktop.DBus.Error.UnknownMethod",
                f"Unknown method: {method}",
            )

    # ── Построение меню ───────────────────────────────────────────────────────

    def _build_layout(self) -> tuple:
        """Вернуть корневой элемент меню в виде (id, props, children)."""
        visible    = self._window.is_visible()
        show_label = _("Hide VlezeApp") if visible else _("Show VlezeApp")

        return (
            0,
            {"children-display": _v("s", "submenu")},
            [
                _item(1, show_label, "view-restore-symbolic"),
                _separator(2),
                _item(3, _("Quit"), "application-exit-symbolic"),
            ],
        )

    def _item_props(self, item_id: int) -> dict | None:
        visible = self._window.is_visible()
        match item_id:
            case 0:
                return {"children-display": _v("s", "submenu")}
            case 1:
                label = _("Hide VlezeApp") if visible else _("Show VlezeApp")
                return {
                    "label":     _v("s", label),
                    "enabled":   _v("b", True),
                    "visible":   _v("b", True),
                    "icon-name": _v("s", "view-restore-symbolic"),
                }
            case 2:
                return {
                    "type":    _v("s", "separator"),
                    "visible": _v("b", True),
                }
            case 3:
                return {
                    "label":     _v("s", _("Quit")),
                    "enabled":   _v("b", True),
                    "visible":   _v("b", True),
                    "icon-name": _v("s", "application-exit-symbolic"),
                }
        return None

    # ── Действия ──────────────────────────────────────────────────────────────

    def _on_click(self, item_id: int) -> None:
        if item_id == 1:
            self._toggle_window()
            self._menu_rev += 1   # метка Show/Hide обновится при следующем открытии
        elif item_id == 3:
            self._do_quit()

    def _toggle_window(self) -> None:
        if self._window.is_visible():
            self._window.hide()
        else:
            self._window.present()

    def _do_quit(self) -> None:
        self._cleanup()
        self._app.release()
        self._app.quit()

    # ── Публичный API ─────────────────────────────────────────────────────────

    def set_tooltip(self, text: str) -> None:
        """Обновить подсказку иконки трея."""
        self._tooltip = text
        if self._conn:
            try:
                self._conn.emit_signal(
                    None, _SNI_PATH, _SNI_IFACE, "NewToolTip",
                    GLib.Variant("()", ()),
                )
            except Exception:
                pass

    def shutdown(self) -> None:
        """Убрать иконку при явном выходе из приложения."""
        self._cleanup()
        self._app.release()

    def _cleanup(self) -> None:
        conn = self._conn
        if conn is None:
            return
        if self._sni_reg:
            conn.unregister_object(self._sni_reg)
            self._sni_reg = 0
        if self._menu_reg:
            conn.unregister_object(self._menu_reg)
            self._menu_reg = 0
