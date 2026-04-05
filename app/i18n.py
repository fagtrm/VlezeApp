"""
Интернационализация VlezeApp.

Использование в модулях:
    from app.i18n import _, ngettext

Компиляция переводов:
    bash scripts/compile_locale.sh
"""
from __future__ import annotations
import gettext
import locale
from pathlib import Path

_DOMAIN = "vlezeapp"
_LOCALE_DIR = Path(__file__).parent.parent / "locale"


def _init() -> tuple:
    try:
        locale.setlocale(locale.LC_ALL, "")
    except locale.Error:
        pass

    t = gettext.translation(
        _DOMAIN,
        localedir=str(_LOCALE_DIR),
        fallback=True,  # при отсутствии .mo возвращает оригинальный msgid
    )
    return t.gettext, t.ngettext


_: gettext.GNUTranslations.gettext
ngettext: gettext.GNUTranslations.ngettext

_, ngettext = _init()
