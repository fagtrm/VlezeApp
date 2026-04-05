"""
Точка входа VlezeApp.
"""
import sys

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GLib", "2.0")
gi.require_version("Gio", "2.0")

from gi.repository import Adw, Gio

from app.ui.main_window import MainWindow


class VlezeApp(Adw.Application):
    def __init__(self) -> None:
        super().__init__(
            application_id="com.vlezeapp.app",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self.connect("activate", self._on_activate)

    def _on_activate(self, app: "VlezeApp") -> None:
        win = MainWindow(application=app)
        win.enable_tray()
        win.present()


def main() -> int:
    app = VlezeApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
